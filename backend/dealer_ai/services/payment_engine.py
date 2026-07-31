"""Realistic-payment estimator.

Standard auto-loan amortization plus a BHPH (buy-here-pay-here) variant
for independent-dealer configurations that carry their own paper.
V1 uses configurable defaults; sales reps will refine numbers during
handoff. Numbers here are guidance, not quotes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
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
