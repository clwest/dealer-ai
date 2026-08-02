"""Milestone 11 · Increment 5 (SESSION_118) — BeBack admin endpoints.

Three endpoints per ``MILESTONE_11_PLANNING.md`` §7 M11.5 + §1.9:

- ``POST /admin/be-backs/`` — record a customer's promise-to-return.
- ``POST /admin/be-backs/<pk>/mark-returned/`` — promised →
  returned.
- ``POST /admin/be-backs/<pk>/mark-no-show/`` — promised →
  no_show. Also fired automatically by the M11.5 Celery detector;
  this endpoint exists for operator overrides.

All three gated on ``IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership`` (M4 permission class,
matches M11.1-M11.4 posture per §1.9).

Domain-error → HTTP mapping:

- :class:`CrossTenantBeBackError` → 404 (fail-closed).
- :class:`UnknownReasonError` → 400.
- :class:`BeBackAlreadyTerminalError` → 409 (state machine).
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    BE_BACK_REASON_CHOICES,
    BeBack,
    CustomerLead,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.be_backs import (
    BeBackAlreadyTerminalError,
    CrossTenantBeBackError,
    UnknownReasonError,
    mark_no_show,
    mark_returned,
    record_be_back,
)
from .services.tenancy import get_current_dealership


_M115_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_lead_or_404(dealership, lead_id):
    try:
        return CustomerLead.objects.filter(dealership=dealership).get(pk=lead_id)
    except CustomerLead.DoesNotExist:
        return None


def _lookup_be_back_or_404(dealership, pk):
    try:
        return BeBack.objects.filter(dealership=dealership).get(pk=pk)
    except BeBack.DoesNotExist:
        return None


class BeBackCreateRequestSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    promised_at = serializers.DateTimeField()
    promised_reason = serializers.ChoiceField(
        choices=[key for key, _ in BE_BACK_REASON_CHOICES]
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class BeBackReturnedRequestSerializer(serializers.Serializer):
    actual_return_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class BeBackNoShowRequestSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_be_back(be_back: BeBack) -> dict:
    return {
        "id": be_back.pk,
        "lead_id": be_back.lead_id,
        "dealership_id": be_back.dealership_id,
        "promised_at": be_back.promised_at.isoformat(),
        "promised_reason": be_back.promised_reason,
        "actual_return_at": (
            be_back.actual_return_at.isoformat()
            if be_back.actual_return_at
            else None
        ),
        "state": be_back.state,
        "notes": be_back.notes,
        "created_at": be_back.created_at.isoformat(),
        "updated_at": be_back.updated_at.isoformat(),
    }


@api_view(["POST"])
@permission_classes(_M115_PERMS)
def admin_be_back_create(request):
    dealership = get_current_dealership(request)
    serializer = BeBackCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    lead = _lookup_lead_or_404(dealership, data["lead_id"])
    if lead is None:
        return Response(
            {"detail": "Lead not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        be_back = record_be_back(
            dealership=dealership,
            lead=lead,
            promised_at=data["promised_at"],
            promised_reason=data["promised_reason"],
            notes=data.get("notes", ""),
        )
    except CrossTenantBeBackError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except UnknownReasonError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"be_back": _project_be_back(be_back)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M115_PERMS)
def admin_be_back_mark_returned(request, pk: int):
    dealership = get_current_dealership(request)
    be_back = _lookup_be_back_or_404(dealership, pk)
    if be_back is None:
        return Response(
            {"detail": "BeBack not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = BeBackReturnedRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        mark_returned(
            dealership=dealership,
            be_back=be_back,
            actual_return_at=serializer.validated_data.get("actual_return_at"),
            notes=serializer.validated_data.get("notes", ""),
        )
    except BeBackAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    be_back.refresh_from_db()
    return Response(
        {"be_back": _project_be_back(be_back)}, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes(_M115_PERMS)
def admin_be_back_mark_no_show(request, pk: int):
    dealership = get_current_dealership(request)
    be_back = _lookup_be_back_or_404(dealership, pk)
    if be_back is None:
        return Response(
            {"detail": "BeBack not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = BeBackNoShowRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        mark_no_show(
            dealership=dealership,
            be_back=be_back,
            notes=serializer.validated_data.get("notes", ""),
        )
    except BeBackAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    be_back.refresh_from_db()
    return Response(
        {"be_back": _project_be_back(be_back)}, status=status.HTTP_200_OK
    )
