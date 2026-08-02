"""Milestone 12 · Increment 3 (SESSION_123) — delinquency detector tasks.

Two Celery tasks matching the M11.5 no-show detector shape:

1. **``detect_delinquencies_for_dealership``** — per-tenant.
   Recomputes ``current_bucket`` + ``days_past_due`` on every
   :class:`BhphNote` for one dealership. Idempotent within a run:
   only writes when the derived value differs from the stored
   value. Returns the count of rows touched + a bucket histogram.
2. **``detect_delinquencies_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 08:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py``. Next slot after M11.5 07:00, preserving
the M7.2-M11.5 non-overlapping-window pattern.

**State-transitioning per M11 §6 lesson 17.** Aging is objectively
elapsed (calendar math), so the detector auto-writes derived state.
Same shape as the M11.5 no-show detector — the distinction from
the M11.4 read-only surfacer is deliberate.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from ..jobs import instrumented_task


_LOGGER = logging.getLogger("dealer_ai.bhph_delinquency.tasks")


DETECT_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.bhph_delinquency.tasks."
    "detect_delinquencies_for_dealership"
)
DETECT_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.bhph_delinquency.tasks."
    "detect_delinquencies_for_all_tenants"
)


@instrumented_task(name=DETECT_FOR_TENANT_TASK_NAME)
def detect_delinquencies_for_dealership(
    *, dealership_id: int
) -> dict[str, Any]:
    """Recompute aging + bucket for every BhphNote at one dealership."""
    from ...models import (
        BHPH_AGING_BUCKET_CURRENT,
        BhphNote,
        BhphPayment,
        Dealership,
    )
    from ..bhph_payments.apply import outstanding_balance
    from ..payment_engine import bhph_note_number_of_periods
    from .compute import (
        bucket_for_days,
        days_past_due_for,
        next_expected_due,
    )

    dealership = Dealership.objects.get(pk=dealership_id)
    today = timezone.now().date()

    bucket_histogram: dict[str, int] = defaultdict(int)
    transitioned_count = 0
    transitioned_pks: list[int] = []

    for note in BhphNote.objects.filter(dealership=dealership):
        payments_agg = BhphPayment.objects.filter(note=note).aggregate(
            payments_count=Count("id"),
            principal_sum=Sum("applied_to_principal"),
        )
        payments_made: int = payments_agg["payments_count"] or 0
        principal_paid: Decimal = (
            payments_agg["principal_sum"] or Decimal("0.00")
        )
        balance = outstanding_balance(
            note.principal_financed, principal_paid
        )
        term_periods = bhph_note_number_of_periods(
            note.term_weeks, note.payment_frequency
        )

        if balance == 0 or payments_made >= term_periods:
            new_bucket = BHPH_AGING_BUCKET_CURRENT
            new_days_past_due = 0
        else:
            projected_next = next_expected_due(
                note.first_payment_due,
                note.payment_frequency,
                payments_made,
            )
            new_days_past_due = days_past_due_for(
                next_expected=projected_next,
                grace_days=note.default_grace_days,
                as_of=today,
            )
            new_bucket = bucket_for_days(new_days_past_due)

        bucket_histogram[new_bucket] += 1

        if (
            note.current_bucket != new_bucket
            or note.days_past_due != new_days_past_due
        ):
            note.current_bucket = new_bucket
            note.days_past_due = new_days_past_due
            note.save(
                update_fields=[
                    "current_bucket",
                    "days_past_due",
                    "updated_at",
                ]
            )
            transitioned_count += 1
            transitioned_pks.append(note.pk)

    _LOGGER.info(
        "bhph_delinquency.detector dealership=%s notes_touched=%d "
        "buckets=%s as_of=%s",
        dealership.slug,
        transitioned_count,
        dict(bucket_histogram),
        today.isoformat(),
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": dealership.slug,
        "as_of": today.isoformat(),
        "transitioned_count": transitioned_count,
        "transitioned_ids": transitioned_pks,
        "bucket_histogram": dict(bucket_histogram),
    }


@instrumented_task(name=DETECT_FOR_ALL_TENANTS_TASK_NAME)
def detect_delinquencies_for_all_tenants() -> dict[str, Any]:
    """Enqueue per-tenant delinquency detection for every :class:`Dealership`."""
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        detect_delinquencies_for_dealership.delay(dealership_id=pk)

    _LOGGER.info(
        "bhph_delinquency.detector.orchestrator dispatched tenants=%d",
        len(dealership_ids),
    )
    return {"dispatched_tenant_count": len(dealership_ids)}
