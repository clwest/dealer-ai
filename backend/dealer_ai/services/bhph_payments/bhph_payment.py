"""Milestone 12 · Increment 2 (SESSION_122) — BhphPayment write + list verbs.

Two verbs per §7 M12.2 + §5.b Option A. See package ``__init__`` for
the domain-error → HTTP mapping contract.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from ...models import (
    BHPH_PAYMENT_METHOD_CHOICES,
    BhphNote,
    BhphPayment,
    Dealership,
)
from .apply import (
    allocate_payment,
    interest_owed_for_period,
    outstanding_balance,
)


_VALID_METHODS = {key for key, _ in BHPH_PAYMENT_METHOD_CHOICES}


class CrossTenantBhphPaymentError(Exception):
    """Raised when a BhphPayment write names a note in another tenant."""


class UnknownPaymentMethodError(Exception):
    """Raised when ``method`` is not in the 4+1 vocab."""


def _principal_paid_to_date(note: BhphNote) -> Decimal:
    """Sum of ``applied_to_principal`` across prior payments for ``note``.

    Returns Decimal("0.00") when the note has no payments yet.
    """
    total = (
        BhphPayment.objects.filter(note=note).aggregate(
            total=Sum("applied_to_principal")
        )["total"]
    )
    return total if total is not None else Decimal("0.00")


def record_payment(
    *,
    dealership: Dealership,
    note: BhphNote,
    paid_at: dt.datetime,
    amount: Decimal,
    method: str,
) -> BhphPayment:
    """Intake a payment against ``note`` and persist with allocation.

    Reads prior BhphPayment rows to compute outstanding principal,
    then delegates to the pure :func:`allocate_payment` verb for the
    fees / interest / principal split. Persists in a
    ``transaction.atomic`` block so a concurrent second
    ``record_payment`` on the same note observes a serialized view
    of the balance.

    Refuses:

    - Cross-tenant note (:class:`CrossTenantBhphPaymentError` — 404).
    - Unknown ``method`` (:class:`UnknownPaymentMethodError` — 400).
    - Overpayment (:class:`services.bhph_payments.OverpaymentError`
      — 400, raised by the allocation verb).
    """
    if note.dealership_id != dealership.id:
        raise CrossTenantBhphPaymentError(
            f"BhphNote {note.pk} belongs to another tenant."
        )
    if method not in _VALID_METHODS:
        raise UnknownPaymentMethodError(
            f"Unknown method={method!r}. Valid: {sorted(_VALID_METHODS)!r}."
        )

    amount_dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))

    with transaction.atomic():
        principal_paid = _principal_paid_to_date(note)
        balance_now = outstanding_balance(
            note.principal_financed, principal_paid
        )
        interest = interest_owed_for_period(
            balance_now, note.apr, note.payment_frequency
        )
        allocation = allocate_payment(
            amount_dec,
            outstanding_balance_now=balance_now,
            interest_owed=interest,
            # No fee-charging entity at M12.2 — see §7 M12.2 non-goals.
            outstanding_fees=Decimal("0.00"),
        )
        return BhphPayment.objects.create(
            dealership=dealership,
            note=note,
            paid_at=paid_at,
            amount=amount_dec,
            method=method,
            applied_to_fees=allocation.fees,
            applied_to_interest=allocation.interest,
            applied_to_principal=allocation.principal,
        )


def list_payments(
    *, dealership: Dealership, note: BhphNote
) -> list[BhphPayment]:
    """Tenant-scoped list of payments for ``note``.

    Cross-tenant note returns an empty list (fail-closed). Ordering
    matches ``Meta`` (``-paid_at``, ``-created_at``).
    """
    if note.dealership_id != dealership.id:
        return []
    return list(BhphPayment.objects.filter(note=note))
