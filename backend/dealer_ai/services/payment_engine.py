"""Realistic-payment estimator.

Standard auto-loan amortization. V1 uses configurable defaults; sales reps
will refine numbers during handoff. Numbers here are guidance, not quotes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


DEFAULT_APR = 7.49  # %
DEFAULT_TERM_MONTHS = 72
DEFAULT_TAX_RATE = 4.5  # %, generic Oklahoma sales tax baseline; sales confirms real tax
DEFAULT_FEES = 599.00  # admin/doc fees as a placeholder


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
