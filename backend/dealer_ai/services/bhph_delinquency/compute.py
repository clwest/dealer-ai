"""Milestone 12 · Increment 3 (SESSION_123) — delinquency math.

Pure. No I/O. No DB access. No Dealership knowledge, no BhphNote row
reads inside the bucket verb — callers supply the raw inputs. The DB-
facing orchestration lives in :mod:`services.bhph_delinquency.tasks`.

Aging boundaries per MILESTONE_12_PLANNING.md §1.3 + §5.c Option A
(fixed 7-value vocab). §0.a M12.3 open decision 1 (as-recommended):
``days_past_due`` measured from the earliest unpaid scheduled due
date (not from grace expiry) — matches BHPH portfolio reporting
convention.

Charge-off threshold: 120 days. Industry-standard breakpoint at
which a note is a candidate for portfolio charge-off. The
transition to actual charged-off is M12.5+ operator scope (§7 M12.3
non-goal) — this bucket is a flag, not a state.
"""

from __future__ import annotations

import datetime as dt

from ...models import (
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_16_30,
    BHPH_AGING_BUCKET_31_60,
    BHPH_AGING_BUCKET_61_90,
    BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_AGING_BUCKET_OVER_90,
)
from ..payment_engine import (
    UnknownBhphFrequencyError,
    _BHPH_NOTE_PERIOD_DAYS,  # noqa: PLC2701 — same-package helper
)


# Industry-standard charge-off threshold. Locked here so future
# adjustments are conscious. Any change requires a §5.c re-decision.
_CHARGE_OFF_DAYS = 120


def bucket_for_days(days_past_due: int) -> str:
    """Map a non-negative day count to the 7-value aging vocab.

    Boundaries per §5.c Option A:

    - 0 → current
    - 1..15 → 1_15
    - 16..30 → 16_30
    - 31..60 → 31_60
    - 61..90 → 61_90
    - 91..119 → over_90
    - 120+ → charge_off_candidate

    Negative inputs collapse to current (past-payment-date clamp;
    callers should have already returned 0 for on-time notes).
    """
    if days_past_due <= 0:
        return BHPH_AGING_BUCKET_CURRENT
    if days_past_due <= 15:
        return BHPH_AGING_BUCKET_1_15
    if days_past_due <= 30:
        return BHPH_AGING_BUCKET_16_30
    if days_past_due <= 60:
        return BHPH_AGING_BUCKET_31_60
    if days_past_due <= 90:
        return BHPH_AGING_BUCKET_61_90
    if days_past_due < _CHARGE_OFF_DAYS:
        return BHPH_AGING_BUCKET_OVER_90
    return BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE


def next_expected_due(
    first_payment_due: dt.date,
    payment_frequency: str,
    payments_made: int,
) -> dt.date:
    """Next expected due date given ``payments_made`` completed so far.

    Pure. Uses M12.1 cadence-to-period-days mapping (weekly=7,
    biweekly=14, semi_monthly=15).

    ``payments_made == 0`` returns ``first_payment_due`` itself (the
    first installment is the next expected). Callers that want to
    check whether a note is fully paid must do so before calling
    this verb — it will happily project past the schedule tail.
    """
    if payment_frequency not in _BHPH_NOTE_PERIOD_DAYS:
        raise UnknownBhphFrequencyError(
            f"Unsupported BHPH payment_frequency: {payment_frequency!r}."
        )
    if payments_made < 0:
        raise ValueError(
            f"payments_made must be >= 0 (got {payments_made})."
        )
    step_days = _BHPH_NOTE_PERIOD_DAYS[payment_frequency]
    return first_payment_due + dt.timedelta(days=step_days * payments_made)


def days_past_due_for(
    *,
    next_expected: dt.date,
    grace_days: int,
    as_of: dt.date,
) -> int:
    """Days past ``next_expected``, respecting the grace period.

    Returns 0 when ``as_of`` is on-or-before ``next_expected +
    grace_days`` (on time or within grace). Otherwise returns
    ``(as_of - next_expected).days`` — aging clock starts from the
    original scheduled date, not from grace expiry. This matches
    BHPH portfolio reporting convention (§0.a M12.3 decision 1).

    Negative ``grace_days`` treated as 0 (defensive — no valid
    negative-grace scenario).
    """
    effective_grace = max(0, grace_days)
    grace_expires = next_expected + dt.timedelta(days=effective_grace)
    if as_of <= grace_expires:
        return 0
    delta = (as_of - next_expected).days
    return max(0, delta)
