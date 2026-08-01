"""Milestone 7 · Increment 4 (SESSION_091) — vendor SLA Celery tasks.

Two Celery task shells around the M7.4 detection verb — same shape as
the M7.2 floor-plan tasks + M7.3 aging tasks modules:

1. **``detect_sla_breaches_for_tenant``** — per-tenant. Accepts
   ``dealership_id`` + optional ``as_of_iso``. One row per invocation
   in :class:`JobRunLog`, stamped with the tenant.
2. **``detect_sla_breaches_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues per-tenant tasks
   via ``.delay()``.

**Beat schedule.** The orchestrator is scheduled at 04:00 project-time
daily via ``CELERY_BEAT_SCHEDULE`` in ``dealer_kit/settings.py`` —
one hour after the M7.3 aging snapshot job. Continues the non-
overlapping window pattern established at M7.2 (02:00) and M7.3
(03:00) so the three job families do not contend for Celery workers
during the same maintenance window.

**Instrumentation.** Both tasks wear the shared
:func:`services.jobs.instrumented_task` decorator. One
:class:`JobRunLog` row per invocation.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.4 +
§7 M7.4.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from ..jobs import instrumented_task

_LOGGER = logging.getLogger("dealer_ai.vendor_sla.tasks")


# Task-name constants — importable so callers, tests, and Beat entries
# reference the canonical string exactly once.
DETECT_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.vendor_sla.tasks.detect_sla_breaches_for_tenant"
)
DETECT_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.vendor_sla.tasks.detect_sla_breaches_for_all_tenants"
)


@instrumented_task(name=DETECT_FOR_TENANT_TASK_NAME)
def detect_sla_breaches_for_tenant(
    *, dealership_id: int, as_of_iso: Optional[str] = None
) -> dict:
    """Scan one tenant's outsourced WorkOrders for SLA breaches.

    Parameters
    ----------
    dealership_id : int
        Primary key of the :class:`Dealership` to scan. Required —
        the wrapping :class:`instrumented_task` decorator uses this
        value to stamp ``JobRunLog.dealership``.
    as_of_iso : str, optional
        Reference date in ``YYYY-MM-DD`` form. ``None`` → the verb
        defaults to today. Celery serializes tasks JSON-only, so we
        take the ISO string.

    Returns
    -------
    dict
        JSON-serializable summary. Consumed by tests + future
        operator dashboards.
    """
    from ...models import Dealership
    from .detection import detect_sla_breaches

    dealership = Dealership.objects.get(pk=dealership_id)
    as_of = dt.date.fromisoformat(as_of_iso) if as_of_iso else None

    report = detect_sla_breaches(dealership, as_of=as_of)

    _LOGGER.info(
        "vendor_sla.scan completed dealership=%s breach_count=%d "
        "in_progress_past_eta=%d approved_stale=%d",
        dealership.slug,
        report.breach_count,
        report.in_progress_past_eta_count,
        report.approved_stale_count,
    )
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": report.dealership_slug,
        "as_of": report.as_of.isoformat(),
        "breach_count": report.breach_count,
        "in_progress_past_eta_count": report.in_progress_past_eta_count,
        "approved_stale_count": report.approved_stale_count,
        # Flat list of work_order_ids so downstream consumers can join
        # against the operator UI without re-scanning WorkOrder rows.
        # Small — even a large dealer's breach set is dozens of items,
        # not thousands.
        "breach_work_order_ids": [b.work_order_id for b in report.breaches],
    }


@instrumented_task(name=DETECT_FOR_ALL_TENANTS_TASK_NAME)
def detect_sla_breaches_for_all_tenants(
    *, as_of_iso: Optional[str] = None
) -> dict:
    """Enqueue per-tenant SLA scans for every :class:`Dealership`.

    Runs at 04:00 daily via the M7.4 Beat schedule entry. Fans out
    via ``.delay()`` — synchronous under
    ``CELERY_TASK_ALWAYS_EAGER=True`` (tests); async in prod.
    """
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        detect_sla_breaches_for_tenant.delay(
            dealership_id=pk, as_of_iso=as_of_iso
        )

    _LOGGER.info(
        "vendor_sla.scan.orchestrator dispatched tenants=%d as_of=%s",
        len(dealership_ids),
        as_of_iso or "today",
    )
    return {
        "dispatched_tenant_count": len(dealership_ids),
        "as_of": as_of_iso or "today",
    }
