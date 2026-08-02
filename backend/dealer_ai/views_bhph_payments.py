"""Milestone 12 · Increment 2 (SESSION_122) — BhphPayment admin endpoints.

Two endpoints per ``MILESTONE_12_PLANNING.md`` §7 M12.2:

- ``POST /admin/bhph-notes/<pk>/payments/`` — intake a payment.
  Computes allocation via the pure :func:`allocate_payment` verb
  and persists.
- ``GET  /admin/bhph-notes/<pk>/payments/`` — list all payments
  for the note (tenant-scoped).

Both gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``
(M4 permission class, matches M12.1 posture).

Domain-error → HTTP mapping:

- :class:`CrossTenantBhphPaymentError` → 404 (fail-closed).
- :class:`UnknownPaymentMethodError` → 400.
- :class:`OverpaymentError` → 400 (refund / reversal deferred).
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    BHPH_PAYMENT_METHOD_CHOICES,
    BhphNote,
    BhphPayment,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.bhph_payments import (
    CrossTenantBhphPaymentError,
    OverpaymentError,
    list_payments,
    record_payment,
)
from .services.bhph_payments.bhph_payment import UnknownPaymentMethodError
from .services.tenancy import get_current_dealership


_M122_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_note_or_404(dealership, note_pk):
    try:
        return BhphNote.objects.filter(dealership=dealership).get(pk=note_pk)
    except BhphNote.DoesNotExist:
        return None


class BhphPaymentCreateRequestSerializer(serializers.Serializer):
    paid_at = serializers.DateTimeField()
    amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=Decimal("0.01")
    )
    method = serializers.ChoiceField(
        choices=[key for key, _ in BHPH_PAYMENT_METHOD_CHOICES]
    )


def _project_payment(payment: BhphPayment) -> dict:
    return {
        "id": payment.pk,
        "note_id": payment.note_id,
        "dealership_id": payment.dealership_id,
        "paid_at": payment.paid_at.isoformat(),
        "amount": str(payment.amount),
        "method": payment.method,
        "applied_to_fees": str(payment.applied_to_fees),
        "applied_to_interest": str(payment.applied_to_interest),
        "applied_to_principal": str(payment.applied_to_principal),
        "created_at": payment.created_at.isoformat(),
        "updated_at": payment.updated_at.isoformat(),
    }


@api_view(["POST"])
@permission_classes(_M122_PERMS)
def admin_bhph_payment_create(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = BhphPaymentCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        payment = record_payment(
            dealership=dealership,
            note=note,
            paid_at=data["paid_at"],
            amount=data["amount"],
            method=data["method"],
        )
    except CrossTenantBhphPaymentError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except UnknownPaymentMethodError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except OverpaymentError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"bhph_payment": _project_payment(payment)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M122_PERMS)
def admin_bhph_payment_list(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    payments = list_payments(dealership=dealership, note=note)
    return Response(
        {
            "count": len(payments),
            "results": [_project_payment(p) for p in payments],
        },
        status=status.HTTP_200_OK,
    )
