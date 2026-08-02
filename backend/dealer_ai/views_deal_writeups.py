"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup admin endpoints.

Three endpoints per ``MILESTONE_11_PLANNING.md`` §7 M11.3:

- ``POST /admin/deal-writeups/`` — create.
- ``POST /admin/deal-writeups/<pk>/approve/`` — sales-manager
  approval.
- ``POST /admin/deal-writeups/<pk>/hand-off/`` — F&I handoff.
  Server-side auto-creates a matching :class:`CreditApplication`
  per §5.e Option A.

All three gated on ``IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership`` (M4 permission class
reused, same posture as M11.1 / M11.2 per §1.9).

Domain-error → HTTP mapping:

- :class:`CrossTenantDealWriteupError` → 404 (fail-closed).
- :class:`WriteupNotApprovedError` → 409 (state machine).
- :class:`WriteupAlreadyHandedOffError` → 409 (idempotency).
- Missing writeup / lead / vehicle in tenant → 404.
- Serializer validation error → 400.

Thin translation layer — no business logic. All logic lives in
:mod:`services.deal_writeups`.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CreditApplication,
    CustomerLead,
    DealWriteup,
    Vehicle,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.deal_writeups import (
    CrossTenantDealWriteupError,
    WriteupAlreadyHandedOffError,
    WriteupNotApprovedError,
    approve_deal_writeup,
    hand_off_to_fandi,
    record_deal_writeup,
)
from .services.tenancy import get_current_dealership


_M113_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_lead_or_404(dealership, lead_id):
    try:
        return CustomerLead.objects.filter(dealership=dealership).get(pk=lead_id)
    except CustomerLead.DoesNotExist:
        return None


def _lookup_vehicle_or_404(dealership, vehicle_id):
    try:
        return Vehicle.objects.filter(dealership=dealership).get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return None


def _lookup_writeup_or_404(dealership, pk):
    try:
        return DealWriteup.objects.filter(dealership=dealership).get(pk=pk)
    except DealWriteup.DoesNotExist:
        return None


class DealWriteupCreateRequestSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    vehicle_id = serializers.IntegerField()
    write_up_at = serializers.DateTimeField(required=False, allow_null=True)
    vehicle_price = serializers.DecimalField(
        required=False, allow_null=True, max_digits=10, decimal_places=2
    )
    trade_allowance = serializers.DecimalField(
        required=False, allow_null=True, max_digits=10, decimal_places=2
    )
    down_payment = serializers.DecimalField(
        required=False, allow_null=True, max_digits=10, decimal_places=2
    )
    monthly_payment_target = serializers.DecimalField(
        required=False, allow_null=True, max_digits=8, decimal_places=2
    )
    term_months_target = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    apr_target = serializers.DecimalField(
        required=False, allow_null=True, max_digits=5, decimal_places=2
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class DealWriteupApproveRequestSerializer(serializers.Serializer):
    """Empty body. Approver identity is `request.user`, timestamp is now."""


class DealWriteupHandoffRequestSerializer(serializers.Serializer):
    """Optional ``source_format`` override on the auto-created CA."""

    source_format = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_writeup(writeup: DealWriteup) -> dict:
    return {
        "id": writeup.pk,
        "lead_id": writeup.lead_id,
        "vehicle_id": writeup.vehicle_id,
        "dealership_id": writeup.dealership_id,
        "vehicle_price": _dec_or_none(writeup.vehicle_price),
        "trade_allowance": _dec_or_none(writeup.trade_allowance),
        "down_payment": _dec_or_none(writeup.down_payment),
        "monthly_payment_target": _dec_or_none(writeup.monthly_payment_target),
        "term_months_target": writeup.term_months_target,
        "apr_target": _dec_or_none(writeup.apr_target),
        "write_up_at": writeup.write_up_at.isoformat(),
        "written_up_by_user_id": writeup.written_up_by_user_id,
        "sales_manager_approved_at": (
            writeup.sales_manager_approved_at.isoformat()
            if writeup.sales_manager_approved_at
            else None
        ),
        "sales_manager_approved_by_user_id": (
            writeup.sales_manager_approved_by_user_id
        ),
        "handed_off_to_fandi_at": (
            writeup.handed_off_to_fandi_at.isoformat()
            if writeup.handed_off_to_fandi_at
            else None
        ),
        "notes": writeup.notes,
        "created_at": writeup.created_at.isoformat(),
        "updated_at": writeup.updated_at.isoformat(),
    }


def _project_credit_application_minimal(app: CreditApplication) -> dict:
    return {
        "id": app.pk,
        "lead_id": app.lead_id,
        "source_format": app.source_format,
        "captured_at": app.captured_at.isoformat(),
    }


def _dec_or_none(value):
    return str(value) if value is not None else None


@api_view(["POST"])
@permission_classes(_M113_PERMS)
def admin_deal_writeup_create(request):
    dealership = get_current_dealership(request)
    serializer = DealWriteupCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)

    lead = _lookup_lead_or_404(dealership, data.pop("lead_id"))
    if lead is None:
        return Response(
            {"detail": "Lead not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    vehicle = _lookup_vehicle_or_404(dealership, data.pop("vehicle_id"))
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        writeup = record_deal_writeup(
            dealership=dealership,
            lead=lead,
            vehicle=vehicle,
            written_up_by_user=(
                request.user if request.user.is_authenticated else None
            ),
            **{k: v for k, v in data.items() if k != "write_up_at"},
            write_up_at=data.get("write_up_at"),
        )
    except CrossTenantDealWriteupError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {"deal_writeup": _project_writeup(writeup)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M113_PERMS)
def admin_deal_writeup_approve(request, pk: int):
    dealership = get_current_dealership(request)
    writeup = _lookup_writeup_or_404(dealership, pk)
    if writeup is None:
        return Response(
            {"detail": "Deal writeup not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    approve_deal_writeup(writeup=writeup, approved_by_user=request.user)
    writeup.refresh_from_db()
    return Response(
        {"deal_writeup": _project_writeup(writeup)},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(_M113_PERMS)
def admin_deal_writeup_hand_off(request, pk: int):
    dealership = get_current_dealership(request)
    writeup = _lookup_writeup_or_404(dealership, pk)
    if writeup is None:
        return Response(
            {"detail": "Deal writeup not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = DealWriteupHandoffRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    source_format = (serializer.validated_data.get("source_format") or "").strip()

    kwargs: dict = {"writeup": writeup}
    if source_format:
        kwargs["source_format"] = source_format

    try:
        writeup, credit_app = hand_off_to_fandi(**kwargs)
    except WriteupNotApprovedError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    except WriteupAlreadyHandedOffError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {
            "deal_writeup": _project_writeup(writeup),
            "credit_application": _project_credit_application_minimal(credit_app),
        },
        status=status.HTTP_201_CREATED,
    )
