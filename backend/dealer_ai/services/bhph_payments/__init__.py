"""Milestone 12 · Increment 2 (SESSION_122) — BhphPayment service package.

Two verbs per ``MILESTONE_12_PLANNING.md`` §7 M12.2 + §5.b Option A
(locked at SESSION_121 open):

- :func:`allocate_payment` — pure verb. Splits a payment amount into
  ``(fees, interest, principal)`` per the platform-wide constant
  application order (fees → interest → principal). No DB access.
- :func:`record_payment` — write verb. Computes outstanding balance
  from the note + prior payments, calls :func:`allocate_payment`,
  persists the row with denormalized allocation columns.

Domain errors:

- :class:`CrossTenantBhphPaymentError` — 404 at endpoint layer.
- :class:`OverpaymentError` — 400. Payment amount exceeds
  ``outstanding_balance + interest_owed + outstanding_fees``.
  Refund / reversal is a M12+ decision; silent absorption is
  refused.
"""

from __future__ import annotations

from .apply import (
    OverpaymentError,
    PaymentAllocation,
    allocate_payment,
    interest_owed_for_period,
    outstanding_balance,
)
from .bhph_payment import (
    CrossTenantBhphPaymentError,
    list_payments,
    record_payment,
)

__all__ = [
    "CrossTenantBhphPaymentError",
    "OverpaymentError",
    "PaymentAllocation",
    "allocate_payment",
    "interest_owed_for_period",
    "list_payments",
    "outstanding_balance",
    "record_payment",
]
