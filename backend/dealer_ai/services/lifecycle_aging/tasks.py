"""Milestone 7 · Increment 3 (SESSION_090) — aging-per-stage Celery tasks.

Two Celery task shells around the M7.3 aging verb — same shape as the
M7.2 floor-plan tasks module:

1. **``snapshot_stage_ages_for_tenant``** — per-tenant worker.
   Accepts ``dealership_id`` + optional ``snapshot_at_iso``. One row
   per invocation in :class:`JobRunLog`, stamped with the tenant.
2. **``snapshot_stage_ages_for_all_tenants``** — orchestrator. Iterates
   every :class:`Dealership` and enqueues one per-tenant task per
   dealership via ``.delay()``. Under ``CELERY_TASK_ALWAYS_EAGER=True``
   (tests) this is synchronous; in prod each per-tenant invocation
   lands on a worker thread.

**Beat schedule.** The orchestrator is scheduled at 03:00 project-time
daily via ``CELERY_BEAT_SCHEDULE`` in ``dealer_kit/settings.py`` —
one hour after the M7.2 floor-plan accrual job to avoid worker
contention during the same maintenance window.

**Instrumentation.** Both tasks wear the shared
:func:`services.jobs.instrumented_task` decorator. One
:class:`JobRunLog` row per invocation.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.3 +
§7 M7.3.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from ..jobs import instrumented_task

_LOGGER = logging.getLogger("dealer_ai.lifecycle_aging.tasks")


# Task-name constants — importable so callers, tests, and Beat entries
# reference the canonical string exactly once.
SNAPSHOT_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.lifecycle_aging.tasks.snapshot_stage_ages_for_tenant"
)
SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.lifecycle_aging.tasks.snapshot_stage_ages_for_all_tenants"
)


@instrumented_task(name=SNAPSHOT_FOR_TENANT_TASK_NAME)
def snapshot_stage_ages_for_tenant(
    *, dealership_id: int, snapshot_at_iso: Optional[str] = None
) -> dict:
    """Snapshot per-stage aging for one tenant.

    Parameters
    ----------
    dealership_id : int
        Primary key of the :class:`Dealership` to snapshot. Required —
        the wrapping :class:`instrumented_task` decorator uses this
        value to stamp ``JobRunLog.dealership`` for the invocation's
        audit row.
    snapshot_at_iso : str, optional
        Snapshot wall-clock time in ISO-8601 form. ``None`` → the
        verb defaults to ``timezone.now()``. Celery serializes tasks
        with JSON only (M7.1 pin), so we take the ISO string rather
        than a native ``datetime``.

    Returns
    -------
    dict
        JSON-serializable summary — the same
        :class:`SnapshotResult` fields plus ``dealership_id``.
        Consumed by tests + future operator dashboards; the
        ``JobRunLog`` row already carries the run metadata.
    """
    # Deferred imports — the task module is loaded eagerly by Celery
    # autodiscovery at Django boot, so we keep the ORM out of the
    # module-import graph.
    from ...models import Dealership
    from .snapshots import snapshot_stage_ages

    dealership = Dealership.objects.get(pk=dealership_id)
    snapshot_at = (
        dt.datetime.fromisoformat(snapshot_at_iso) if snapshot_at_iso else None
    )

    result = snapshot_stage_ages(dealership, snapshot_at=snapshot_at)

    _LOGGER.info(
        "lifecycle_aging.snapshot completed dealership=%s "
        "stages_with_vehicles=%d rows_written=%d",
        dealership.slug,
        len(result.stages_with_vehicles),
        result.written_count,
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": result.dealership_slug,
        "snapshot_at": result.snapshot_at.isoformat(),
        "rows_written": result.written_count,
        "stages_with_vehicles": list(result.stages_with_vehicles),
    }


@instrumented_task(name=SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME)
def snapshot_stage_ages_for_all_tenants(
    *, snapshot_at_iso: Optional[str] = None
) -> dict:
    """Enqueue per-tenant snapshots for every :class:`Dealership`.

    Runs at 03:00 daily via the M7.3 Beat schedule entry. Fans out
    via ``.delay()`` — synchronous under
    ``CELERY_TASK_ALWAYS_EAGER=True`` (tests); async in prod.

    Parameters
    ----------
    snapshot_at_iso : str, optional
        Passed through to every enqueued per-tenant task. ``None`` →
        each per-tenant task defaults to ``timezone.now()`` at the
        moment IT runs — so in a fan-out with N tenants, snapshot
        times will differ by however long each per-tenant task takes
        to reach the worker. For a coordinated "snapshot at exactly
        this moment" run, callers can pass an explicit
        ``snapshot_at_iso``.

    Returns
    -------
    dict
        JSON-serializable dispatch summary.
    """
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        snapshot_stage_ages_for_tenant.delay(
            dealership_id=pk, snapshot_at_iso=snapshot_at_iso
        )

    _LOGGER.info(
        "lifecycle_aging.snapshot.orchestrator dispatched tenants=%d snapshot_at=%s",
        len(dealership_ids),
        snapshot_at_iso or "now",
    )
    return {
        "dispatched_tenant_count": len(dealership_ids),
        "snapshot_at": snapshot_at_iso or "now",
    }
