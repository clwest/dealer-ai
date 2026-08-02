"""Milestone 12 · Increment 4 (SESSION_124) — broken-PTP detector tasks.

Two Celery tasks mirroring the M11.5 no-show detector shape:

1. **``detect_broken_promises_for_dealership``** — per-tenant.
   Transitions each :class:`BhphPromiseToPay` with
   ``state=promised`` and ``promised_at + grace_period <= now`` and
   ``actual_payment is null`` to ``state=broken``. Returns the
   count of transitions.
2. **``detect_broken_promises_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 09:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py`` — next slot after M12.3 08:00.

**Grace period.** Configurable via
``settings.BHPH_PTP_BROKEN_GRACE_HOURS`` (default 24). One day
after the promised date is a reasonable minimum before flagging
broken; operators can tighten via env per §0.a M12.4 decision 3.

**State-transitioning per M11 §6 lesson 17.** The passage of the
grace period is objectively elapsed (calendar math), so auto-
transition matches the M11.5 no-show and M12.3 delinquency
posture. Distinct from operator-intent transitions like M11.4
follow-up task completion.
"""

from __future__ import annotations

import datetime as dt
import logging

from django.conf import settings
from django.utils import timezone

from ..jobs import instrumented_task


_LOGGER = logging.getLogger("dealer_ai.bhph_promises.tasks")


DETECT_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.bhph_promises.tasks."
    "detect_broken_promises_for_dealership"
)
DETECT_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.bhph_promises.tasks."
    "detect_broken_promises_for_all_tenants"
)


def _grace_hours() -> int:
    """Grace period in hours; falls back to 24 if setting is unset."""
    return int(getattr(settings, "BHPH_PTP_BROKEN_GRACE_HOURS", 24))


@instrumented_task(name=DETECT_FOR_TENANT_TASK_NAME)
def detect_broken_promises_for_dealership(
    *, dealership_id: int
) -> dict:
    """Transition stale promised PTPs to broken for one tenant."""
    from ...models import (
        BHPH_PROMISE_STATE_BROKEN,
        BHPH_PROMISE_STATE_PROMISED,
        BhphPromiseToPay,
        Dealership,
    )

    dealership = Dealership.objects.get(pk=dealership_id)
    now = timezone.now()
    cutoff = now - dt.timedelta(hours=_grace_hours())

    stale_qs = BhphPromiseToPay.objects.filter(
        dealership=dealership,
        state=BHPH_PROMISE_STATE_PROMISED,
        promised_at__lte=cutoff,
        actual_payment__isnull=True,
    )
    transitioned_ids = list(stale_qs.values_list("pk", flat=True))
    transitioned_count = stale_qs.update(state=BHPH_PROMISE_STATE_BROKEN)

    _LOGGER.info(
        "bhph_promises.broken_detector dealership=%s transitioned=%d "
        "grace_hours=%d as_of=%s",
        dealership.slug,
        transitioned_count,
        _grace_hours(),
        now.isoformat(),
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": dealership.slug,
        "as_of": now.isoformat(),
        "grace_hours": _grace_hours(),
        "transitioned_count": transitioned_count,
        "transitioned_ids": transitioned_ids,
    }


@instrumented_task(name=DETECT_FOR_ALL_TENANTS_TASK_NAME)
def detect_broken_promises_for_all_tenants() -> dict:
    """Enqueue per-tenant broken-PTP detection for every :class:`Dealership`."""
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        detect_broken_promises_for_dealership.delay(dealership_id=pk)

    _LOGGER.info(
        "bhph_promises.broken_detector.orchestrator dispatched tenants=%d",
        len(dealership_ids),
    )
    return {"dispatched_tenant_count": len(dealership_ids)}
