"""Milestone 7 · Increment 5 (SESSION_092) — photo tombstone reaper tasks.

Two Celery task shells around the M7.5 reaper verb — same shape as the
M7.2 floor-plan / M7.3 aging / M7.4 vendor-SLA task modules:

1. **``reap_tombstoned_photos_for_tenant``** — per-tenant. Accepts
   ``dealership_id`` + optional ``as_of_iso``. One ``JobRunLog`` row
   per invocation, stamped with the tenant.
2. **``reap_tombstoned_photos_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues per-tenant tasks
   via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 05:00 project-time
daily via ``CELERY_BEAT_SCHEDULE`` in ``dealer_kit/settings.py`` —
one hour after the M7.4 vendor-SLA scan. Continues the non-overlapping
window pattern established at M7.2/M7.3/M7.4 (02:00 / 03:00 / 04:00).

**Instrumentation.** Both tasks wear the shared
:func:`services.jobs.instrumented_task` decorator.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.5 +
§7 M7.5.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from ..jobs import instrumented_task

_LOGGER = logging.getLogger("dealer_ai.photo_gallery.tasks")


# Task-name constants — importable so callers, tests, and Beat entries
# reference the canonical string exactly once.
REAP_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.photo_gallery.tasks.reap_tombstoned_photos_for_tenant"
)
REAP_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.photo_gallery.tasks.reap_tombstoned_photos_for_all_tenants"
)


@instrumented_task(name=REAP_FOR_TENANT_TASK_NAME)
def reap_tombstoned_photos_for_tenant(
    *, dealership_id: int, as_of_iso: Optional[str] = None
) -> dict:
    """Physically delete tombstoned photos for one tenant.

    Parameters
    ----------
    dealership_id : int
        Primary key of the :class:`Dealership`. Required — the
        wrapping :class:`instrumented_task` decorator uses this value
        to stamp ``JobRunLog.dealership``.
    as_of_iso : str, optional
        Reference timestamp in ISO-8601 form. ``None`` → the verb
        defaults to ``timezone.now()``. Celery serializes tasks
        JSON-only (M7.1 pin), so we take the ISO string.

    Returns
    -------
    dict
        JSON-serializable summary. Consumed by tests + future operator
        dashboards.
    """
    from ...models import Dealership
    from .reaper import reap_tombstoned_photos

    dealership = Dealership.objects.get(pk=dealership_id)
    as_of = dt.datetime.fromisoformat(as_of_iso) if as_of_iso else None

    result = reap_tombstoned_photos(dealership, as_of=as_of)

    _LOGGER.info(
        "photo_reaper.task completed dealership=%s candidates=%d "
        "deleted=%d storage_failed=%d",
        dealership.slug,
        result.candidates,
        result.deleted,
        result.storage_failed,
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": result.dealership_slug,
        "as_of": result.as_of.isoformat(),
        "candidates": result.candidates,
        "deleted": result.deleted,
        "storage_failed": result.storage_failed,
        # Flat PK lists — small even for a busy dealer (dozens of
        # tombstoned photos per day, not thousands).
        "deleted_photo_ids": list(result.deleted_photo_ids),
        "storage_failed_photo_ids": list(result.storage_failed_photo_ids),
    }


@instrumented_task(name=REAP_FOR_ALL_TENANTS_TASK_NAME)
def reap_tombstoned_photos_for_all_tenants(
    *, as_of_iso: Optional[str] = None
) -> dict:
    """Enqueue per-tenant reaper runs for every :class:`Dealership`.

    Runs at 05:00 daily via the M7.5 Beat schedule entry. Fans out via
    ``.delay()`` — synchronous under ``CELERY_TASK_ALWAYS_EAGER=True``
    (tests); async in prod.
    """
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        reap_tombstoned_photos_for_tenant.delay(
            dealership_id=pk, as_of_iso=as_of_iso
        )

    _LOGGER.info(
        "photo_reaper.orchestrator dispatched tenants=%d as_of=%s",
        len(dealership_ids),
        as_of_iso or "now",
    )
    return {
        "dispatched_tenant_count": len(dealership_ids),
        "as_of": as_of_iso or "now",
    }
