"""Milestone 12 · Increment 3 (SESSION_123) — delinquency detection package.

Two verb layers per ``MILESTONE_12_PLANNING.md`` §7 M12.3 + §5.c
Option A (fixed 7-value aging vocab locked at SESSION_121 open) +
§0.a M12.3 micro-decisions (all as-recommended):

- **Pure math** — :mod:`compute`:
  - :func:`bucket_for_days` — maps ``days_past_due`` (int) to the
    7-value vocab.
  - :func:`next_expected_due` — cadence-aware next-due date given
    payments made so far.
  - :func:`days_past_due_for` — grace-respecting date arithmetic.

- **State-transitioning detector** — :mod:`tasks`:
  - :func:`detect_delinquencies_for_dealership` — per-tenant task.
    Recomputes ``current_bucket`` + ``days_past_due`` on every
    active BhphNote for one dealership. Idempotent within a run.
  - :func:`detect_delinquencies_for_all_tenants` — orchestrator.
    Enqueues one per-tenant invocation per :class:`Dealership`.

**Beat schedule.** The orchestrator runs at 08:00
``settings.TIME_ZONE`` daily via ``CELERY_BEAT_SCHEDULE`` in
``dealer_kit/settings.py`` — next slot after M11.5 07:00.

**State-transitioning per M11 §6 lesson 17.** Aging is objectively
elapsed (calendar math), so the detector auto-writes the derived
bucket without operator intent — same shape as the M11.5 no-show
detector. Distinct from the M11.4 read-only surfacer.
"""

from __future__ import annotations

from .compute import (
    bucket_for_days,
    days_past_due_for,
    next_expected_due,
)
from .tasks import (
    detect_delinquencies_for_all_tenants,
    detect_delinquencies_for_dealership,
)

__all__ = [
    "bucket_for_days",
    "days_past_due_for",
    "detect_delinquencies_for_all_tenants",
    "detect_delinquencies_for_dealership",
    "next_expected_due",
]
