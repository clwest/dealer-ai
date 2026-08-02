"""Milestone 11 · Increment 5 (SESSION_118) — BeBack no-show detector.

Two Celery tasks per §5.g.3 Option B (dedicated M11.5 detector, not
spilling into the M11.4 cadence engine):

1. **``detect_no_show_be_backs_for_tenant``** — per-tenant.
   Transitions each :class:`BeBack` with ``state=promised`` and
   ``promised_at + grace_period <= now`` and
   ``actual_return_at is null`` to ``state=no_show``. Returns the
   count of transitions.
2. **``detect_no_show_be_backs_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 07:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py``. Next slot after M11.4 at 06:00,
preserving the M7.2-M11.4 non-overlapping-window pattern.

**Grace period.** Configurable via
``settings.BE_BACK_NO_SHOW_GRACE_HOURS`` (default 4). Set to zero
to transition immediately on promise expiry; increase for lenient
operators.

**Distinct from M11.4.** The M11.4 beat surfacer is read-only; this
one *does* transition state (per §5.g.3 Option B — the no-show
rule is narrow to BeBack itself). Manual override via
:func:`services.be_backs.mark_no_show` is also available at the
endpoint layer for operator control.
"""

from __future__ import annotations

import datetime as dt
import logging

from django.conf import settings
from django.utils import timezone

from ..jobs import instrumented_task


_LOGGER = logging.getLogger("dealer_ai.be_backs.tasks")


DETECT_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.be_backs.tasks."
    "detect_no_show_be_backs_for_tenant"
)
DETECT_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.be_backs.tasks."
    "detect_no_show_be_backs_for_all_tenants"
)


def _grace_hours() -> int:
    """Grace period in hours; falls back to 4 if setting is unset."""
    return int(getattr(settings, "BE_BACK_NO_SHOW_GRACE_HOURS", 4))


@instrumented_task(name=DETECT_FOR_TENANT_TASK_NAME)
def detect_no_show_be_backs_for_tenant(
    *, dealership_id: int
) -> dict:
    """Transition stale promised be-backs to no_show for one tenant."""
    from ...models import (
        BE_BACK_STATE_NO_SHOW,
        BE_BACK_STATE_PROMISED,
        BeBack,
        Dealership,
    )

    dealership = Dealership.objects.get(pk=dealership_id)
    now = timezone.now()
    cutoff = now - dt.timedelta(hours=_grace_hours())

    stale_qs = BeBack.objects.filter(
        dealership=dealership,
        state=BE_BACK_STATE_PROMISED,
        promised_at__lte=cutoff,
        actual_return_at__isnull=True,
    )
    transitioned_ids = list(stale_qs.values_list("pk", flat=True))
    transitioned_count = stale_qs.update(state=BE_BACK_STATE_NO_SHOW)

    _LOGGER.info(
        "be_backs.no_show_detector dealership=%s transitioned=%d "
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
def detect_no_show_be_backs_for_all_tenants() -> dict:
    """Enqueue per-tenant no-show detection for every :class:`Dealership`."""
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        detect_no_show_be_backs_for_tenant.delay(dealership_id=pk)

    _LOGGER.info(
        "be_backs.no_show_detector.orchestrator dispatched tenants=%d",
        len(dealership_ids),
    )
    return {"dispatched_tenant_count": len(dealership_ids)}
