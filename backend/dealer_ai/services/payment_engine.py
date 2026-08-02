"""Realistic-payment estimator.

Standard auto-loan amortization plus a BHPH (buy-here-pay-here) variant
for independent-dealer configurations that carry their own paper.
V1 uses configurable defaults; sales reps will refine numbers during
handoff. Numbers here are guidance, not quotes.

Milestone 2 · Increment 4a adds the pure floor-plan-interest
calculator :func:`daily_floor_plan_interest`. See its docstring for
the load-bearing financial rules (behavior at zero / negative
inputs, rounding, day-count convention, APR unit convention).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal


DEFAULT_APR = 7.49  # %
DEFAULT_TERM_MONTHS = 72
DEFAULT_TAX_RATE = 4.5  # %, generic state sales tax baseline; sales confirms real tax
DEFAULT_FEES = 599.00  # admin/doc fees as a placeholder

# BHPH — buy-here-pay-here — defaults reflect typical in-house indie
# portfolios: shorter term, higher APR, weekly cadence common. Real
# lenders vary; these are guidance for the assistant, refined at
# handoff. Down-payment minimum is portfolio policy, not a math
# constraint — surface as a warning, don't block the estimate.
BHPH_APR_DEFAULT = 21.9  # %, midpoint of typical 18-24% BHPH range
BHPH_TERM_MONTHS_DEFAULT = 30  # months, midpoint of typical 24-36
BHPH_MIN_DOWN_PAYMENT_PCT = 20.0  # % of vehicle price

BHPHCadence = Literal["weekly", "biweekly"]

# Periods per year for each cadence — used to convert APR into a
# per-period rate and to price out how many payments cover the term.
_PERIODS_PER_YEAR: dict[str, float] = {
    "weekly": 52.0,
    "biweekly": 26.0,
}


@dataclass
class PaymentEstimate:
    monthly_payment: float
    total_financed: float
    apr: float
    term_months: int
    down_payment: float
    trade_in_value: float
    taxes: float
    fees: float

    def to_dict(self) -> dict:
        return {
            "monthly_payment": round(self.monthly_payment, 2),
            "total_financed": round(self.total_financed, 2),
            "apr": self.apr,
            "term_months": self.term_months,
            "down_payment": round(self.down_payment, 2),
            "trade_in_value": round(self.trade_in_value, 2),
            "taxes": round(self.taxes, 2),
            "fees": round(self.fees, 2),
        }


def estimate_payment(
    price: Decimal | float,
    *,
    down_payment: float = 0.0,
    trade_in_value: float = 0.0,
    apr: float = DEFAULT_APR,
    term_months: int = DEFAULT_TERM_MONTHS,
    tax_rate: float = DEFAULT_TAX_RATE,
    fees: float = DEFAULT_FEES,
) -> PaymentEstimate:
    price_f = float(price)
    taxes = price_f * (tax_rate / 100.0)
    subtotal = price_f + taxes + fees
    financed = max(0.0, subtotal - down_payment - trade_in_value)

    monthly_rate = (apr / 100.0) / 12.0
    n = max(1, term_months)
    if monthly_rate == 0:
        monthly_payment = financed / n
    else:
        monthly_payment = (
            financed * monthly_rate * (1 + monthly_rate) ** n
        ) / ((1 + monthly_rate) ** n - 1)

    return PaymentEstimate(
        monthly_payment=monthly_payment,
        total_financed=financed,
        apr=apr,
        term_months=term_months,
        down_payment=down_payment,
        trade_in_value=trade_in_value,
        taxes=taxes,
        fees=fees,
    )


@dataclass
class BHPHPaymentEstimate:
    """Deterministic BHPH periodic-payment estimate.

    ``periodic_payment`` is what the buyer pays each week/biweekly.
    ``monthly_equivalent`` is the same amortization schedule expressed
    as a monthly figure so it can appear alongside standard-loan
    quotes for comparison. Both are computed from the same underlying
    total-financed / APR / term inputs.
    """

    periodic_payment: float
    cadence: BHPHCadence
    monthly_equivalent: float
    total_financed: float
    apr: float
    term_months: int
    number_of_payments: int
    down_payment: float
    trade_in_value: float
    taxes: float
    fees: float
    min_down_payment_required: float

    def to_dict(self) -> dict:
        return {
            "periodic_payment": round(self.periodic_payment, 2),
            "cadence": self.cadence,
            "monthly_equivalent": round(self.monthly_equivalent, 2),
            "total_financed": round(self.total_financed, 2),
            "apr": self.apr,
            "term_months": self.term_months,
            "number_of_payments": self.number_of_payments,
            "down_payment": round(self.down_payment, 2),
            "trade_in_value": round(self.trade_in_value, 2),
            "taxes": round(self.taxes, 2),
            "fees": round(self.fees, 2),
            "min_down_payment_required": round(
                self.min_down_payment_required, 2
            ),
        }


def bhph_min_down_payment(
    price: Decimal | float, *, down_pct: float = BHPH_MIN_DOWN_PAYMENT_PCT
) -> float:
    """Portfolio-typical minimum BHPH down payment for a sticker price."""
    return float(price) * (down_pct / 100.0)


def estimate_bhph_payment(
    price: Decimal | float,
    *,
    cadence: BHPHCadence = "weekly",
    down_payment: float = 0.0,
    trade_in_value: float = 0.0,
    apr: float = BHPH_APR_DEFAULT,
    term_months: int = BHPH_TERM_MONTHS_DEFAULT,
    tax_rate: float = DEFAULT_TAX_RATE,
    fees: float = DEFAULT_FEES,
    min_down_pct: float = BHPH_MIN_DOWN_PAYMENT_PCT,
) -> BHPHPaymentEstimate:
    """Amortize a BHPH deal at true periodic cadence (weekly/biweekly).

    Unlike a naive ``monthly / 4.333`` conversion, this runs the
    amortization formula against the actual per-period rate and number
    of periods — matching how BHPH portfolios quote payments in the
    real world.
    """
    if cadence not in _PERIODS_PER_YEAR:
        raise ValueError(f"Unsupported BHPH cadence: {cadence!r}")

    price_f = float(price)
    taxes = price_f * (tax_rate / 100.0)
    subtotal = price_f + taxes + fees
    financed = max(0.0, subtotal - down_payment - trade_in_value)

    periods_per_year = _PERIODS_PER_YEAR[cadence]
    period_rate = (apr / 100.0) / periods_per_year
    n_periods = max(1, int(round(term_months * (periods_per_year / 12.0))))

    if period_rate == 0:
        periodic_payment = financed / n_periods
    else:
        periodic_payment = (
            financed * period_rate * (1 + period_rate) ** n_periods
        ) / ((1 + period_rate) ** n_periods - 1)

    monthly_equivalent = periodic_payment * (periods_per_year / 12.0)

    return BHPHPaymentEstimate(
        periodic_payment=periodic_payment,
        cadence=cadence,
        monthly_equivalent=monthly_equivalent,
        total_financed=financed,
        apr=apr,
        term_months=term_months,
        number_of_payments=n_periods,
        down_payment=down_payment,
        trade_in_value=trade_in_value,
        taxes=taxes,
        fees=fees,
        min_down_payment_required=bhph_min_down_payment(
            price_f, down_pct=min_down_pct
        ),
    )


# ---- Milestone 2 · Increment 4a — floor-plan interest math ---------------
#
# Pure financial engine. Zero DB access, zero Dealership knowledge, zero
# Vehicle knowledge, zero ledger side-effects. Reusable for future
# payoff, curtailment, and lender-balance calculations — the caller
# supplies whichever "principal" is meaningful in context (purchase
# price for v1 accrual per MILESTONE_2_PLANNING §1.4; post-curtailment
# balance later; per-lender payoff later; etc.).
#
# The accrual command that consumes this function is Milestone 2 ·
# Increment 5, NOT this module's concern. Do not tempt-scope-creep a
# "run this over a queryset" helper here.

# Days-per-year convention. 365 chosen over 360 (bankers' method)
# because most modern indie floor-plan lenders quote APR against a
# calendar year and the arithmetic stays intuitive (a 30-day period
# always produces 30/365 of the annual interest). If a future
# integration with a 360-day lender is scoped, add an optional
# ``days_per_year: int = 365`` parameter — the day-count convention
# is documented explicitly here so the addition is a conscious change.
_DAYS_PER_YEAR = Decimal("365")

# Result precision. Every ``daily_floor_plan_interest`` return value
# quantizes to cents so:
#   1. Downstream ``VehicleCost.amount`` (DecimalField(10, 2)) inserts
#      without silent precision loss.
#   2. Repeated accrual runs against the same inputs produce equal
#      outputs (bitwise-comparable Decimals — no float drift).
#   3. Sums of many accruals remain cent-accurate.
# ``ROUND_HALF_UP`` chosen over ``ROUND_HALF_EVEN`` (banker's) because
# it matches consumer expectation for money math and is what most floor-
# plan lenders' statements use. Locked by
# ``test_daily_floor_plan_interest.DecimalPrecisionAndRounding``.
_CENTS = Decimal("0.01")


def daily_floor_plan_interest(
    principal: Decimal,
    apr: Decimal,
    days_elapsed: int,
) -> Decimal:
    """Return the interest accrued on ``principal`` at ``apr`` for
    ``days_elapsed`` days.

    Pure. No I/O. No side effects. No dealership knowledge. Callers
    supply the meaningful principal (purchase price for v1 accrual;
    post-curtailment balance later; per-lender payoff later).

    APR-unit convention: ``apr`` is expressed in **percent units**
    (e.g. ``Decimal("8.5")`` for an 8.5% annual rate) — matching the
    existing :data:`DEFAULT_APR` convention above.

    Day-count convention: 365 (calendar year). See ``_DAYS_PER_YEAR``.

    Formula:

        interest = principal * apr * days_elapsed / 36500

    Multiplication before the single final division preserves Decimal
    precision. Result is quantized to cents (``Decimal("0.01")``) with
    ``ROUND_HALF_UP``.

    Financial rules (locked by tests in
    ``test_daily_floor_plan_interest``):

    - ``apr == 0`` → ``Decimal("0.00")``. Zero rate → zero interest.
    - ``principal == 0`` → ``Decimal("0.00")``. Zero balance → zero
      interest.
    - ``days_elapsed == 0`` → ``Decimal("0.00")``. No time → no
      interest. Also the idempotency escape hatch for accrual commands
      that re-run on the same day.
    - ``days_elapsed < 0`` → ``Decimal("0.00")``. Negative days are
      not a valid accrual scenario; returning zero (rather than
      raising) makes the accrual command idempotent even when a stale
      ``--as-of`` is passed by mistake.
    - ``principal < 0`` → :class:`ValueError`. Negative principal
      would be data corruption (we never *owe* the lender less than
      nothing). Raising loudly is the right shape — silent zero would
      hide the underlying bug.
    - ``apr < 0`` → :class:`ValueError`. Same reasoning as negative
      principal.

    All valid returns are :class:`Decimal` quantized to two decimal
    places.
    """
    if not isinstance(principal, Decimal):
        principal = Decimal(str(principal))
    if not isinstance(apr, Decimal):
        apr = Decimal(str(apr))

    if principal < 0:
        raise ValueError(
            f"principal must be >= 0 (got {principal}); negative "
            "principal is not a valid floor-plan-interest scenario."
        )
    if apr < 0:
        raise ValueError(
            f"apr must be >= 0 (got {apr}); negative APR is not a "
            "valid floor-plan-interest scenario."
        )

    if days_elapsed <= 0 or principal == 0 or apr == 0:
        return Decimal("0.00")

    # Multiply first, divide last, quantize at the end. Preserves as
    # much precision as Decimal allows before the final rounding step.
    # Divide by 100 (percent → decimal fraction) then by days-per-year
    # in one denominator to avoid an extra rounding cycle.
    raw = principal * apr * Decimal(days_elapsed) / (_DAYS_PER_YEAR * Decimal("100"))
    return raw.quantize(_CENTS, rounding=ROUND_HALF_UP)


def affordable_max_price(
    target_monthly: float,
    *,
    down_payment: float = 0.0,
    trade_in_value: float = 0.0,
    apr: float = DEFAULT_APR,
    term_months: int = DEFAULT_TERM_MONTHS,
    tax_rate: float = DEFAULT_TAX_RATE,
    fees: float = DEFAULT_FEES,
) -> float:
    """Reverse calc: rough max sticker price for a target monthly payment."""
    monthly_rate = (apr / 100.0) / 12.0
    n = max(1, term_months)
    if monthly_rate == 0:
        max_financed = target_monthly * n
    else:
        max_financed = target_monthly * ((1 + monthly_rate) ** n - 1) / (
            monthly_rate * (1 + monthly_rate) ** n
        )
    subtotal = max_financed + down_payment + trade_in_value
    price = (subtotal - fees) / (1 + tax_rate / 100.0)
    return max(0.0, price)


# ---- Milestone 12 · Increment 1 — BhphNote amortization ------------------
#
# Pure math for the dealer-as-lender side. Distinct from
# :func:`estimate_bhph_payment` (the customer-shopping estimator that
# consumes sticker price + taxes + fees + down/trade-in). BhphNote
# origination already has the net principal in hand (the M9 Sale row
# ledger settled taxes/fees/down/trade); the note math amortizes that
# principal over ``term_weeks`` at ``apr`` on the chosen cadence.
#
# Adds ``semi_monthly`` (24 periods/year — twice per month, common at
# BHPH portfolios) to the M2 cadence set. Semi-monthly period spacing
# is 15 calendar days — the convention that pairs cleanly with the
# 365/24 ≈ 15.2-day theoretical spacing and matches operator practice
# (1st + 15th style schedules).

BhphNoteFrequency = Literal["weekly", "biweekly", "semi_monthly"]

# Periods per year per cadence. Kept as Decimal so the amortization
# formula stays in Decimal end-to-end (no float promotion).
_BHPH_NOTE_PERIODS_PER_YEAR: dict[str, Decimal] = {
    "weekly": Decimal("52"),
    "biweekly": Decimal("26"),
    "semi_monthly": Decimal("24"),
}

# Days between successive payments. Weekly / biweekly are exact
# calendar spans; semi_monthly is the 15-day convention (see comment
# above).
_BHPH_NOTE_PERIOD_DAYS: dict[str, int] = {
    "weekly": 7,
    "biweekly": 14,
    "semi_monthly": 15,
}


class UnknownBhphFrequencyError(ValueError):
    """Raised when ``payment_frequency`` is not in the M12.1 vocab."""


def _validate_bhph_note_inputs(
    principal: Decimal,
    apr: Decimal,
    term_weeks: int,
    payment_frequency: str,
) -> None:
    if payment_frequency not in _BHPH_NOTE_PERIODS_PER_YEAR:
        raise UnknownBhphFrequencyError(
            f"Unsupported BHPH payment_frequency: {payment_frequency!r}. "
            f"Valid: {sorted(_BHPH_NOTE_PERIODS_PER_YEAR)!r}."
        )
    if principal <= 0:
        raise ValueError(
            f"principal must be > 0 (got {principal}); a zero-principal "
            "BhphNote has no schedule to amortize."
        )
    if apr < 0:
        raise ValueError(
            f"apr must be >= 0 (got {apr}); negative APR is not a valid "
            "BhphNote scenario."
        )
    if term_weeks <= 0:
        raise ValueError(
            f"term_weeks must be > 0 (got {term_weeks}); a zero-term note "
            "cannot amortize."
        )


def bhph_note_number_of_periods(
    term_weeks: int, payment_frequency: BhphNoteFrequency
) -> int:
    """Number of periodic payments for a BhphNote of ``term_weeks`` at
    ``payment_frequency``.

    Weekly = ``term_weeks`` periods. Biweekly = ``term_weeks / 2`` (14-
    day spans). Semi-monthly = ``term_weeks * 24 / 52`` — non-integer
    inputs round half-up to the nearest whole period; operator UI
    should surface the resulting term-in-periods so quoted schedules
    are unambiguous.
    """
    if payment_frequency not in _BHPH_NOTE_PERIODS_PER_YEAR:
        raise UnknownBhphFrequencyError(
            f"Unsupported BHPH payment_frequency: {payment_frequency!r}."
        )
    periods_per_year = _BHPH_NOTE_PERIODS_PER_YEAR[payment_frequency]
    raw = Decimal(term_weeks) * periods_per_year / Decimal("52")
    rounded = raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(1, int(rounded))


def bhph_note_periodic_payment(
    principal: Decimal,
    apr: Decimal,
    term_weeks: int,
    payment_frequency: BhphNoteFrequency,
) -> Decimal:
    """Amortize ``principal`` into a per-period BhphNote payment.

    Pure. No I/O. ``apr`` is percent units (matches
    :data:`DEFAULT_APR` convention). Returns a :class:`Decimal`
    quantized to cents (``ROUND_HALF_UP``) so callers can persist
    the result directly into
    :attr:`dealer_ai.models.BhphNote.payment_amount`
    (DecimalField(8, 2)) without silent precision loss.

    Formula: standard amortization at the per-period rate ``r`` and
    period count ``n``:

        payment = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)

    Zero-APR case degenerates cleanly to ``principal / n``.
    """
    if not isinstance(principal, Decimal):
        principal = Decimal(str(principal))
    if not isinstance(apr, Decimal):
        apr = Decimal(str(apr))
    _validate_bhph_note_inputs(principal, apr, term_weeks, payment_frequency)

    n_periods = bhph_note_number_of_periods(term_weeks, payment_frequency)
    if apr == 0:
        raw = principal / Decimal(n_periods)
        return raw.quantize(_CENTS, rounding=ROUND_HALF_UP)

    periods_per_year = _BHPH_NOTE_PERIODS_PER_YEAR[payment_frequency]
    period_rate = apr / periods_per_year / Decimal("100")
    one_plus_r_pow_n = (Decimal("1") + period_rate) ** n_periods
    numerator = principal * period_rate * one_plus_r_pow_n
    denominator = one_plus_r_pow_n - Decimal("1")
    raw = numerator / denominator
    return raw.quantize(_CENTS, rounding=ROUND_HALF_UP)


def bhph_note_schedule(
    principal: Decimal,
    apr: Decimal,
    term_weeks: int,
    payment_frequency: BhphNoteFrequency,
    first_payment_due: date,
) -> list[tuple[date, Decimal]]:
    """Return the full payment schedule for a BhphNote.

    Pure. Equal-amount installments (matches how BHPH portfolios quote
    a fixed weekly/biweekly/semi-monthly figure to the buyer). Each
    tuple is ``(due_date, amount)`` with dates spaced by
    :data:`_BHPH_NOTE_PERIOD_DAYS` for the cadence.

    The final period may absorb rounding drift when a future payoff
    verb settles the balance; M12.1 returns the quoted-amount
    schedule only. Amortization drift over even a 130-week schedule
    at BHPH APRs is typically < $2 total, and is settled by the
    lender at closeout — not something the operator quotes to the
    buyer.
    """
    if not isinstance(principal, Decimal):
        principal = Decimal(str(principal))
    if not isinstance(apr, Decimal):
        apr = Decimal(str(apr))

    n_periods = bhph_note_number_of_periods(term_weeks, payment_frequency)
    periodic = bhph_note_periodic_payment(
        principal, apr, term_weeks, payment_frequency
    )
    step_days = _BHPH_NOTE_PERIOD_DAYS[payment_frequency]

    schedule: list[tuple[date, Decimal]] = []
    for i in range(n_periods):
        due = first_payment_due + timedelta(days=step_days * i)
        schedule.append((due, periodic))
    return schedule
