"""Milestone 11 · Increment 4 (SESSION_117) — follow-up beat orchestrator.

Two Celery tasks around the M11.4 follow-up substrate, mirroring the
M7.2 floor-plan / M7.3 aging / M7.4 SLA / M7.5 tombstone pattern:

1. **``surface_due_follow_up_tasks_for_tenant``** — per-tenant.
   Accepts ``dealership_id``. Counts + logs pending
   :class:`FollowUpTask` rows whose ``due_at <= now()`` for the
   tenant's active cadences. Does **not** transition state (per
   SESSION_117 §0.a M11.4 decision 3 — operator-triggered only).
2. **``surface_due_follow_up_tasks_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 06:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py``. Next slot after the M7.2-M7.5 chain
(02:00-05:00), preserving the non-overlapping-window pattern.

**Why surfacing but not delivering.** The M11.4 substrate captures
the schedule + operator work-queue. Actual outbound delivery (SMS,
email) is deferred — the follow-on will subscribe to the surfaced-
count / JobRunLog and dispatch via a delivery adapter. Splitting
scheduling from delivery keeps the M11.4 test surface tight (no
external I/O mocks needed).
"""

from __future__ import annotations

import logging

from django.utils import timezone

from ..jobs import instrumented_task


_LOGGER = logging.getLogger("dealer_ai.follow_ups.tasks")


SURFACE_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.follow_ups.tasks."
    "surface_due_follow_up_tasks_for_tenant"
)
SURFACE_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.follow_ups.tasks."
    "surface_due_follow_up_tasks_for_all_tenants"
)


@instrumented_task(name=SURFACE_FOR_TENANT_TASK_NAME)
def surface_due_follow_up_tasks_for_tenant(
    *, dealership_id: int
) -> dict:
    """Log the count of due pending tasks for one tenant.

    Read-only — no state transitions. See module docstring for the
    rationale (SESSION_117 §0.a M11.4 decision 3).
    """
    from ...models import (
        FOLLOW_UP_TASK_STATE_PENDING,
        Dealership,
        FollowUpTask,
    )

    dealership = Dealership.objects.get(pk=dealership_id)
    now = timezone.now()
    due_qs = FollowUpTask.objects.filter(
        dealership=dealership,
        state=FOLLOW_UP_TASK_STATE_PENDING,
        due_at__lte=now,
        cadence__is_active=True,
    )
    due_count = due_qs.count()
    _LOGGER.info(
        "follow_ups.surface dealership=%s due_count=%d as_of=%s",
        dealership.slug,
        due_count,
        now.isoformat(),
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": dealership.slug,
        "as_of": now.isoformat(),
        "due_count": due_count,
    }


@instrumented_task(name=SURFACE_FOR_ALL_TENANTS_TASK_NAME)
def surface_due_follow_up_tasks_for_all_tenants() -> dict:
    """Enqueue per-tenant surfacing for every :class:`Dealership`."""
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        surface_due_follow_up_tasks_for_tenant.delay(dealership_id=pk)

    _LOGGER.info(
        "follow_ups.surface.orchestrator dispatched tenants=%d",
        len(dealership_ids),
    )
    return {"dispatched_tenant_count": len(dealership_ids)}
