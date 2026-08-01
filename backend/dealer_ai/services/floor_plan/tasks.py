"""Milestone 7 · Increment 2 (SESSION_089) — floor-plan Celery tasks.

Two Celery task shells around the M2 accrual verb:

1. **``accrue_daily_interest_for_tenant``** — per-tenant. Accepts
   ``dealership_id`` + optional ``as_of_iso``. One row per invocation
   in :class:`JobRunLog`, stamped with the tenant. This is the task
   the Beat orchestrator fans out to.
2. **``accrue_daily_interest_for_all_tenants``** — orchestrator.
   Iterates every :class:`Dealership` and enqueues one per-tenant
   invocation via ``.delay()`` (async fan-out in prod; synchronous
   under ``CELERY_TASK_ALWAYS_EAGER=True`` in tests). One row in
   :class:`JobRunLog` for the orchestrator itself, plus one row per
   dispatched tenant.

**Why two tasks instead of one:** cleaner audit trail. If one task
mixed "per-tenant" and "all-tenants" modes via an optional
``dealership_id`` kwarg, the orchestrator invocation's
:class:`JobRunLog` row would carry ``dealership_id=None`` (fallback to
default tenant), which misrepresents the process-wide scope. Two tasks
+ one Beat entry firing the orchestrator = clear semantics at each
level.

**Beat schedule.** The orchestrator is scheduled at 02:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py``. Per-tenant "run time" is therefore 02:00
project-time, not per-tenant local time — v1 accepts this simplification
because (a) the accrual math is time-of-day agnostic (it accrues over
whole calendar days) and (b) a single project-wide entry avoids
per-tenant code-deploy churn as new tenants onboard.

**Instrumentation.** Both tasks wear the shared
:func:`services.jobs.instrumented_task` decorator (SESSION_088). One
:class:`JobRunLog` row per invocation, structured logging on start /
end, ``dealership_id`` kwarg propagation, retry-on-transient-error.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.2 +
§7 M7.2.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Optional

from ..jobs import instrumented_task

_LOGGER = logging.getLogger("dealer_ai.floor_plan.tasks")


# Task-name constants — importable so callers, tests, and Beat entries
# reference the canonical string exactly once. Django-Celery convention
# is "package.module.function"; kept explicit so autodiscovery's task
# registry surface is greppable.
ACCRUE_FOR_TENANT_TASK_NAME = (
    "dealer_ai.services.floor_plan.tasks.accrue_daily_interest_for_tenant"
)
ACCRUE_FOR_ALL_TENANTS_TASK_NAME = (
    "dealer_ai.services.floor_plan.tasks.accrue_daily_interest_for_all_tenants"
)


@instrumented_task(name=ACCRUE_FOR_TENANT_TASK_NAME)
def accrue_daily_interest_for_tenant(
    *, dealership_id: int, as_of_iso: Optional[str] = None
) -> dict:
    """Accrue floor-plan interest for one tenant.

    Parameters
    ----------
    dealership_id : int
        Primary key of the :class:`Dealership` to process. Required —
        the wrapping :class:`instrumented_task` decorator uses this
        value to stamp ``JobRunLog.dealership`` for the invocation's
        audit row.
    as_of_iso : str, optional
        Accrual date in ``YYYY-MM-DD`` form. ``None`` → the service
        verb defaults to today (in ``settings.TIME_ZONE``). Celery
        serializes tasks with JSON only (see M7.1 pins) — passing a
        ``datetime.date`` directly would fail serialization, so we
        take the ISO string.

    Returns
    -------
    dict
        A JSON-serializable summary of the run — the same
        :class:`AccrualSummary` fields the CLI adapter prints, plus
        ``dealership_id``. Consumed by tests + future operator
        dashboards; the ``JobRunLog`` row already carries the run
        metadata, so operators don't strictly need this return value.
    """
    # Deferred imports — the task module is loaded eagerly by Celery
    # autodiscovery at Django boot, so we keep the ORM out of the
    # module-import graph. The imports resolve on first invocation.
    from ...models import Dealership
    from .accrual import accrue_daily_interest

    dealership = Dealership.objects.get(pk=dealership_id)
    as_of = dt.date.fromisoformat(as_of_iso) if as_of_iso else None

    summary = accrue_daily_interest(dealership, as_of=as_of)

    _LOGGER.info(
        "floor_plan.accrual completed dealership=%s vehicles_accrued=%d "
        "total_accrued=%s",
        dealership.slug,
        summary.vehicles_accrued,
        summary.total_accrued,
    )
    # Return a JSON-serializable dict — dataclasses.asdict would work
    # but requires converting Decimal → str explicitly for JSON. Hand-
    # roll it to keep the dependency graph tight.
    return {
        "dealership_id": dealership.pk,
        "dealership_slug": summary.dealership_slug,
        "as_of": summary.as_of.isoformat(),
        "dry_run": summary.dry_run,
        "vehicles_evaluated": summary.vehicles_evaluated,
        "vehicles_accrued": summary.vehicles_accrued,
        "vehicles_skipped": summary.vehicles_skipped,
        "total_accrued": str(summary.total_accrued),
    }


@instrumented_task(name=ACCRUE_FOR_ALL_TENANTS_TASK_NAME)
def accrue_daily_interest_for_all_tenants(
    *, as_of_iso: Optional[str] = None
) -> dict:
    """Enqueue per-tenant accruals for every :class:`Dealership`.

    Runs at 02:00 daily via the M7.2 Beat schedule entry (see
    ``dealer_kit/settings.py``). Fans out via ``.delay()`` — under
    ``CELERY_TASK_ALWAYS_EAGER=True`` (tests) this is synchronous;
    in prod each per-tenant invocation lands on a worker thread.

    Parameters
    ----------
    as_of_iso : str, optional
        Passed through to every enqueued per-tenant task. ``None`` →
        each per-tenant task defaults to today.

    Returns
    -------
    dict
        JSON-serializable dispatch summary. Consumed by tests + future
        operator dashboards.
    """
    from ...models import Dealership

    dealership_ids = list(
        Dealership.objects.values_list("pk", flat=True).order_by("pk")
    )
    for pk in dealership_ids:
        accrue_daily_interest_for_tenant.delay(
            dealership_id=pk, as_of_iso=as_of_iso
        )

    _LOGGER.info(
        "floor_plan.accrual.orchestrator dispatched tenants=%d as_of=%s",
        len(dealership_ids),
        as_of_iso or "today",
    )
    return {
        "dispatched_tenant_count": len(dealership_ids),
        "as_of": as_of_iso or "today",
    }
