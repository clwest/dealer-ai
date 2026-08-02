"""Milestone 12 · Increment 4 (SESSION_124) — BhphPromiseToPay endpoints.

Four endpoints per ``MILESTONE_12_PLANNING.md`` §7 M12.4:

- ``POST /admin/bhph-notes/<pk>/promises/`` — record a PTP.
- ``GET  /admin/bhph-notes/<pk>/promises/list/`` — list per-note.
- ``POST /admin/bhph-promises/<pk>/mark-kept/`` — operator-triggered
  reconciliation per §5.d Option A. Accepts ``bhph_payment_id``.
- ``POST /admin/bhph-promises/<pk>/mark-broken/`` — operator
  override (detector auto-fires; this exists for manual control).

All gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``.

Domain-error → HTTP mapping:

- :class:`CrossTenantBhphPromiseError` → 404 (fail-closed).
- :class:`UnknownReasonError` → 400.
- :class:`CrossPromisePaymentError` → 400.
- :class:`PromiseAlreadyTerminalError` → 409 (state machine).
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
    BHPH_PROMISE_REASON_CHOICES,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.bhph_promises import (
    CrossPromisePaymentError,
    CrossTenantBhphPromiseError,
    PromiseAlreadyTerminalError,
    UnknownReasonError,
    mark_broken,
    mark_kept,
    record_promise,
)
from .services.tenancy import get_current_dealership


_M124_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_note_or_404(dealership, note_pk):
    try:
        return BhphNote.objects.filter(dealership=dealership).get(pk=note_pk)
    except BhphNote.DoesNotExist:
        return None


def _lookup_promise_or_404(dealership, pk):
    try:
        return BhphPromiseToPay.objects.filter(dealership=dealership).get(pk=pk)
    except BhphPromiseToPay.DoesNotExist:
        return None


def _lookup_payment_or_404(dealership, pk):
    try:
        return BhphPayment.objects.filter(dealership=dealership).get(pk=pk)
    except BhphPayment.DoesNotExist:
        return None


class PromiseCreateRequestSerializer(serializers.Serializer):
    promised_at = serializers.DateTimeField()
    promised_amount = serializers.DecimalField(
        max_digits=8, decimal_places=2, min_value=Decimal("0.01")
    )
    promised_reason = serializers.ChoiceField(
        choices=[key for key, _ in BHPH_PROMISE_REASON_CHOICES]
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class PromiseKeptRequestSerializer(serializers.Serializer):
    bhph_payment_id = serializers.IntegerField()
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class PromiseBrokenRequestSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_promise(promise: BhphPromiseToPay) -> dict:
    return {
        "id": promise.pk,
        "note_id": promise.note_id,
        "dealership_id": promise.dealership_id,
        "promised_at": promise.promised_at.isoformat(),
        "promised_amount": str(promise.promised_amount),
        "promised_reason": promise.promised_reason,
        "actual_payment_id": promise.actual_payment_id,
        "state": promise.state,
        "notes": promise.notes,
        "created_at": promise.created_at.isoformat(),
        "updated_at": promise.updated_at.isoformat(),
    }


@api_view(["POST"])
@permission_classes(_M124_PERMS)
def admin_bhph_promise_create(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PromiseCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        promise = record_promise(
            dealership=dealership,
            note=note,
            promised_at=data["promised_at"],
            promised_amount=data["promised_amount"],
            promised_reason=data["promised_reason"],
            notes=data.get("notes", ""),
        )
    except CrossTenantBhphPromiseError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except UnknownReasonError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"bhph_promise": _project_promise(promise)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M124_PERMS)
def admin_bhph_promise_list(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    promises = list(
        BhphPromiseToPay.objects.filter(dealership=dealership, note=note)
    )
    return Response(
        {
            "count": len(promises),
            "results": [_project_promise(p) for p in promises],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(_M124_PERMS)
def admin_bhph_promise_mark_kept(request, pk: int):
    dealership = get_current_dealership(request)
    promise = _lookup_promise_or_404(dealership, pk)
    if promise is None:
        return Response(
            {"detail": "BhphPromiseToPay not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = PromiseKeptRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payment = _lookup_payment_or_404(
        dealership, serializer.validated_data["bhph_payment_id"]
    )
    if payment is None:
        return Response(
            {"detail": "BhphPayment not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        mark_kept(
            dealership=dealership,
            promise=promise,
            payment=payment,
            notes=serializer.validated_data.get("notes", ""),
        )
    except CrossPromisePaymentError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except PromiseAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    promise.refresh_from_db()
    return Response(
        {"bhph_promise": _project_promise(promise)}, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes(_M124_PERMS)
def admin_bhph_promise_mark_broken(request, pk: int):
    dealership = get_current_dealership(request)
    promise = _lookup_promise_or_404(dealership, pk)
    if promise is None:
        return Response(
            {"detail": "BhphPromiseToPay not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = PromiseBrokenRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        mark_broken(
            dealership=dealership,
            promise=promise,
            notes=serializer.validated_data.get("notes", ""),
        )
    except PromiseAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    promise.refresh_from_db()
    return Response(
        {"bhph_promise": _project_promise(promise)}, status=status.HTTP_200_OK
    )
