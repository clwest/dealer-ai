"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive admin endpoint.

One endpoint at M11.2:

- ``POST /admin/test-drives/`` — create a TestDrive record.

Gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``
(M4 permission class reused, matches M11.1 posture per §1.9). The
salesperson-writes-their-own-drive path (advisor role gate) is
deferred to a follow-on — at M11.2 the sales manager / dealer owner
enters drives on behalf of their team as the operator-substrate
posture.

Domain-error → HTTP mapping:

- :class:`CrossTenantTestDriveError` → 404 (fail-closed; never leak
  cross-tenant existence).
- Missing lead / vehicle in tenant → 404.
- Serializer validation error → 400.

Thin translation layer — no business logic. All logic lives in
:mod:`services.test_drives`.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CustomerLead, TestDrive, Vehicle
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.tenancy import get_current_dealership
from .services.test_drives import (
    CrossTenantTestDriveError,
    record_test_drive,
)


_M112_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


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


class TestDriveCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/test-drives/``."""

    lead_id = serializers.IntegerField()
    vehicle_id = serializers.IntegerField()
    driven_at = serializers.DateTimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )
    route_notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    customer_reaction = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    objections_captured = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    next_action = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_test_drive(drive: TestDrive) -> dict:
    return {
        "id": drive.pk,
        "lead_id": drive.lead_id,
        "vehicle_id": drive.vehicle_id,
        "dealership_id": drive.dealership_id,
        "driven_by_user_id": drive.driven_by_user_id,
        "driven_at": drive.driven_at.isoformat(),
        "duration_minutes": drive.duration_minutes,
        "route_notes": drive.route_notes,
        "customer_reaction": drive.customer_reaction,
        "objections_captured": list(drive.objections_captured or []),
        "next_action": drive.next_action,
        "created_at": drive.created_at.isoformat(),
        "updated_at": drive.updated_at.isoformat(),
    }


@api_view(["GET"])
@permission_classes(_M112_PERMS)
def admin_test_drive_list(request):
    """GET: list test drives for the caller's tenant.

    Added at M11.6 (SESSION_119) per §0.a M11.6 addendum — the M11.6
    operator UI needs a list surface. Thin QuerySet wrapper with three
    optional filters:

    - ``lead_id`` — narrow to a specific lead.
    - ``vehicle_id`` — narrow to a specific vehicle.
    - ``driven_since`` — ISO datetime; ``driven_at__gte=<value>``.

    Cap at 100 rows (matches M10.7 admin list convention). Ordering
    matches Meta (``-driven_at``).
    """
    dealership = get_current_dealership(request)
    qs = TestDrive.objects.filter(dealership=dealership)

    raw_lead = request.query_params.get("lead_id")
    if raw_lead:
        try:
            qs = qs.filter(lead_id=int(raw_lead))
        except (TypeError, ValueError):
            pass

    raw_vehicle = request.query_params.get("vehicle_id")
    if raw_vehicle:
        try:
            qs = qs.filter(vehicle_id=int(raw_vehicle))
        except (TypeError, ValueError):
            pass

    raw_since = request.query_params.get("driven_since")
    if raw_since:
        try:
            parsed = serializers.DateTimeField().to_internal_value(raw_since)
            qs = qs.filter(driven_at__gte=parsed)
        except serializers.ValidationError:
            pass

    rows = list(qs[:100])
    return Response(
        {
            "count": len(rows),
            "results": [_project_test_drive(td) for td in rows],
        }
    )


@api_view(["POST"])
@permission_classes(_M112_PERMS)
def admin_test_drive_create(request):
    """POST: create a TestDrive.

    ``lead_id`` + ``vehicle_id`` are mandatory (§5.c Option A). A
    cross-tenant reference on either FK surfaces as 404, same fail-
    closed shape as M9.1 / M10.1 / M11.1 referral.
    """
    dealership = get_current_dealership(request)

    serializer = TestDriveCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    lead = _lookup_lead_or_404(dealership, data["lead_id"])
    if lead is None:
        return Response(
            {"detail": "Lead not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    vehicle = _lookup_vehicle_or_404(dealership, data["vehicle_id"])
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    service_kwargs = dict(
        dealership=dealership,
        lead=lead,
        vehicle=vehicle,
        driven_by_user=request.user if request.user.is_authenticated else None,
        duration_minutes=data.get("duration_minutes"),
        route_notes=data.get("route_notes", ""),
        customer_reaction=data.get("customer_reaction", ""),
        objections_captured=data.get("objections_captured") or [],
        next_action=data.get("next_action", ""),
    )
    if data.get("driven_at") is not None:
        service_kwargs["driven_at"] = data["driven_at"]

    try:
        drive = record_test_drive(**service_kwargs)
    except CrossTenantTestDriveError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {"test_drive": _project_test_drive(drive)},
        status=status.HTTP_201_CREATED,
    )
