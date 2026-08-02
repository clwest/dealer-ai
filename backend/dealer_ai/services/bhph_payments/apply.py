"""Milestone 12 · Increment 2 (SESSION_122) — payment allocation math.

Pure. No I/O. No DB access. No Dealership knowledge, no BhphNote row
reads inside the split verb itself — callers supply the current
outstanding balance, the accrued interest owed for this period, and
any outstanding fees. This keeps allocate_payment testable in
isolation and lets :func:`record_payment` handle the DB-facing balance
recomputation independently.

Application order per MILESTONE_12_PLANNING.md §5.b Option A
(user-confirmed at SESSION_121 open — platform-wide constant):

    fees → interest → principal

Fees always zero at M12.2 (no fee-charging entity exists yet).
Column preserved so a future late-fee / NSF-fee entity can plug in
without a schema change.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import NamedTuple

from ..payment_engine import (
    UnknownBhphFrequencyError,
    _BHPH_NOTE_PERIODS_PER_YEAR,  # noqa: PLC2701 — same-package helper
)


_CENTS = Decimal("0.01")


class OverpaymentError(Exception):
    """Payment exceeds ``outstanding_balance + interest_owed + outstanding_fees``.

    Refunds / reversals are M12+ scope decisions (see
    MILESTONE_12_PLANNING.md §7 M12.2 non-goals). Silent absorption
    would corrupt payoff math; raising surfaces the anomaly for
    operator judgment.
    """


class PaymentAllocation(NamedTuple):
    """(fees, interest, principal) split of a payment amount.

    All three components sum to the original payment amount
    (Decimal-exact). Each is quantized to cents (ROUND_HALF_UP)
    matching the ``BhphPayment`` schema.
    """

    fees: Decimal
    interest: Decimal
    principal: Decimal


def _as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def interest_owed_for_period(
    outstanding_balance_now: Decimal,
    apr: Decimal,
    payment_frequency: str,
) -> Decimal:
    """Compute the interest that accrues on ``outstanding_balance_now``
    over one period at ``apr`` for ``payment_frequency``.

    Pure. Same cadence-to-rate math as the M12.1
    :func:`services.payment_engine.bhph_note_periodic_payment` verb:

        period_rate = apr / periods_per_year / 100
        interest = outstanding_balance * period_rate

    Result quantized to cents (ROUND_HALF_UP).
    """
    if payment_frequency not in _BHPH_NOTE_PERIODS_PER_YEAR:
        raise UnknownBhphFrequencyError(
            f"Unsupported BHPH payment_frequency: {payment_frequency!r}."
        )
    balance = _as_decimal(outstanding_balance_now)
    apr_dec = _as_decimal(apr)
    if balance <= 0 or apr_dec == 0:
        return Decimal("0.00")
    periods_per_year = _BHPH_NOTE_PERIODS_PER_YEAR[payment_frequency]
    period_rate = apr_dec / periods_per_year / Decimal("100")
    raw = balance * period_rate
    return raw.quantize(_CENTS, rounding=ROUND_HALF_UP)


def allocate_payment(
    amount: Decimal,
    *,
    outstanding_balance_now: Decimal,
    interest_owed: Decimal,
    outstanding_fees: Decimal = Decimal("0.00"),
) -> PaymentAllocation:
    """Split ``amount`` into (fees, interest, principal) per §5.b.

    Pure. Application order platform-wide constant:

        1. fees      = min(amount, outstanding_fees)
        2. interest  = min(remainder, interest_owed)
        3. principal = remainder  (up to outstanding_balance_now)

    If the remainder after fees + interest exceeds
    ``outstanding_balance_now``, raises :class:`OverpaymentError`.

    All three returned values sum to ``amount`` exactly (Decimal —
    no float drift). Each is quantized to cents (ROUND_HALF_UP).
    """
    amount_dec = _as_decimal(amount).quantize(_CENTS, rounding=ROUND_HALF_UP)
    balance_dec = _as_decimal(outstanding_balance_now)
    interest_dec = _as_decimal(interest_owed)
    fees_available = _as_decimal(outstanding_fees)

    if amount_dec <= 0:
        raise ValueError(
            f"amount must be > 0 (got {amount_dec}); a zero-amount "
            "payment has no allocation to compute."
        )
    if balance_dec < 0:
        raise ValueError(
            f"outstanding_balance_now must be >= 0 (got {balance_dec})."
        )
    if interest_dec < 0:
        raise ValueError(
            f"interest_owed must be >= 0 (got {interest_dec})."
        )
    if fees_available < 0:
        raise ValueError(
            f"outstanding_fees must be >= 0 (got {fees_available})."
        )

    remaining = amount_dec

    fees = min(remaining, fees_available).quantize(_CENTS, rounding=ROUND_HALF_UP)
    remaining -= fees

    interest = min(remaining, interest_dec).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )
    remaining -= interest

    if remaining > balance_dec:
        raise OverpaymentError(
            f"Payment {amount_dec} exceeds outstanding "
            f"({fees_available} fees + {interest_dec} interest + "
            f"{balance_dec} principal). Refund / reversal deferred "
            "beyond M12."
        )

    principal = remaining.quantize(_CENTS, rounding=ROUND_HALF_UP)
    return PaymentAllocation(fees=fees, interest=interest, principal=principal)


def outstanding_balance(
    principal_financed: Decimal, principal_paid_to_date: Decimal
) -> Decimal:
    """Remaining principal on a BhphNote after prior payments.

    Pure. Callers query the DB for ``principal_paid_to_date`` (sum of
    ``applied_to_principal`` across prior BhphPayment rows for the
    note); this verb reduces to Decimal subtraction. Split out as a
    named function so tests can lock the sign / edge cases without
    plumbing DB fixtures.
    """
    balance = _as_decimal(principal_financed) - _as_decimal(
        principal_paid_to_date
    )
    if balance < 0:
        return Decimal("0.00")
    return balance.quantize(_CENTS, rounding=ROUND_HALF_UP)
