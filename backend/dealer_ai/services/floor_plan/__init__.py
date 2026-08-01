"""Milestone 7 · Increment 2 (SESSION_089) — floor-plan orchestration.

Owns the scheduled floor-plan interest accrual workflow. Extracts the
M2 ``accrue_floor_plan_interest`` management command's body per M4-M6
lesson 4 (service ownership — one authoritative write path per
operation). The management command becomes a thin CLI wrapper around
:func:`accrue_daily_interest`.

**Why a new package instead of extending ``vehicle_ledger.py``:** the
ledger service is deliberately scoped to pure ledger primitives
(``add_cost``, ``record_acquisition``, ``compute_totals``). Its own
module docstring calls out: *"Milestone 2 · Increment 4 lands the
math helper + management command"* — the accrual orchestration is
explicitly outside its charter. Growing ``vehicle_ledger.py`` with a
scheduled-job orchestrator would violate the module's stated scope
and mix two levels of abstraction.

**Public surface:**

- :func:`accrue_daily_interest` — per-tenant service verb (verb).
- :class:`AccrualPlan` — one planned accrual (data).
- :class:`AccrualSummary` — execution summary (data).

**Not re-exported here:**

- The Celery task shells (:mod:`.tasks`) — callers that want the
  Celery task import it directly from ``services.floor_plan.tasks``.
  Keeping the tasks module out of the package __init__ keeps import
  cycles at bay when the task module (which imports the decorator
  from ``services.jobs``) is loaded via Celery autodiscovery.
"""

from __future__ import annotations

from .accrual import (
    AccrualPlan,
    AccrualSummary,
    accrue_daily_interest,
)

__all__ = (
    "AccrualPlan",
    "AccrualSummary",
    "accrue_daily_interest",
)
