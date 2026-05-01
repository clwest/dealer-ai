# dealer_ai/services/payment_engine.py

from decimal import Decimal


def estimate_payment(price, down_payment=0, annual_rate=8.9, term_months=72):
    price = Decimal(price)
    down_payment = Decimal(down_payment or 0)

    principal = max(price - down_payment, Decimal("0"))
    monthly_rate = Decimal(str(annual_rate / 100 / 12))

    if monthly_rate == 0:
        return principal / term_months

    payment = principal * (
        monthly_rate * ((1 + monthly_rate) ** term_months)
    ) / (((1 + monthly_rate) ** term_months) - 1)

    return round(payment, 2)