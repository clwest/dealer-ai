"""Milestone 4 · Increment 6 — admin API for the recon subsystem.

Every endpoint here composes
:class:`IsAuthenticated` &
:class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
per planning §5.f. Advisor / porter / f_and_i_manager /
collections all receive 403.

Endpoints delegate entirely to :mod:`services.recon` and
:mod:`services.vendor_comm`. No business logic lives here — this
module is thin translation between HTTP and the service surface.

Domain-error → HTTP status mapping (SESSION_071 locked):

- ``CrossTenantReconError`` / ``CrossTenantVendorCommError`` → 404
  (never leak whether the resource exists across tenants).
- ``ReconImmutableError`` / ``VendorCommImmutableError`` /
  ``InvalidReconTransitionError`` /
  ``IncompleteConditionReportError`` → 409 Conflict.
- ``ReconFactScrubDroppedError`` → 422 Unprocessable (operator
  should review + retry).
- ``EmptyDraftError`` → 502 Bad Gateway (LLM upstream returned
  nothing usable).
- ``ValueError`` (invalid vocabulary / structural) → 400.

Tenant scoping: every endpoint resolves ``dealership`` via
:func:`services.tenancy.get_current_dealership` and passes it
explicitly into service calls. Cross-tenant lookups (URL kwarg
references a resource owned by another dealership) surface as
404 rather than 403, matching the M2.6 / M3.6 fail-closed
pattern.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CONDITION_CATEGORY_CHOICES,
    ConditionFinding,
    Vehicle,
    VENDOR_COMMUNICATION_CHANNEL_CHOICES,
    VENDOR_COMMUNICATION_DIRECTION_CHOICES,
    VENDOR_COMMUNICATION_KIND_CHOICES,
    Vendor,
    VendorCommunication,
    WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
    WORK_ORDER_PART_STATUS_CHOICES,
    WORK_ORDER_VENUE_CHOICES,
    WorkOrder,
    WorkOrderPart,
    RECON_DECISION_TIER_CHOICES,
    ReconDecision,
)
from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services import recon as recon_service
from .services import vendor_comm as vendor_comm_service
from .services.condition_report import (
    latest_completed_condition_report,
)
from .services.recon import (
    CrossTenantReconError,
    IncompleteConditionReportError,
    InvalidReconTransitionError,
    ReconImmutableError,
)
from .services.tenancy import get_current_dealership
from .services.vendor_comm import (
    CrossTenantVendorCommError,
    EmptyDraftError,
    ReconFactScrubDroppedError,
    VendorCommImmutableError,
)


_M46_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]


# ============================================================================
# Lookup helpers (tenant-scoped; 404 on cross-tenant + nonexistent)
# ============================================================================


def _lookup_vehicle_or_404(dealership, stock_number):
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _lookup_vendor_or_404(dealership, slug):
    try:
        return Vendor.objects.filter(dealership=dealership).get(slug=slug)
    except Vendor.DoesNotExist:
        return None


def _lookup_work_order_or_404(dealership, wo_id):
    try:
        return (
            WorkOrder.objects.filter(dealership=dealership)
            .select_related("vehicle", "vendor")
            .get(pk=wo_id)
        )
    except WorkOrder.DoesNotExist:
        return None


def _lookup_finding_or_404(dealership, vehicle, finding_id):
    try:
        return ConditionFinding.objects.filter(
            dealership=dealership, report__vehicle=vehicle
        ).get(pk=finding_id)
    except ConditionFinding.DoesNotExist:
        return None


def _lookup_part_or_404(dealership, part_id):
    try:
        return (
            WorkOrderPart.objects.filter(dealership=dealership)
            .select_related("work_order", "work_order__vehicle")
            .get(pk=part_id)
        )
    except WorkOrderPart.DoesNotExist:
        return None


def _lookup_comm_or_404(dealership, comm_id):
    try:
        return (
            VendorCommunication.objects.filter(dealership=dealership)
            .select_related("vendor", "work_order")
            .get(pk=comm_id)
        )
    except VendorCommunication.DoesNotExist:
        return None


def _lookup_user_at_dealership_or_none(dealership, user_id):
    """Return a User who has any :class:`UserDealershipRole` at
    ``dealership``, or None. Prevents cross-tenant user references
    (an operator at Dealership A cannot assign a WO to a user at
    Dealership B)."""
    from .models import UserDealershipRole

    role = (
        UserDealershipRole.objects.filter(
            user_id=user_id, dealership=dealership
        )
        .select_related("user")
        .first()
    )
    return role.user if role is not None else None


# ============================================================================
# Response projections
# ============================================================================


def _project_vendor(vendor: Vendor) -> dict:
    return {
        "id": vendor.pk,
        "slug": vendor.slug,
        "name": vendor.name,
        "categories": vendor.categories or [],
        "phone": vendor.phone,
        "email": vendor.email,
        "notes": vendor.notes,
        "is_active": vendor.is_active,
        "created_at": vendor.created_at,
        "updated_at": vendor.updated_at,
    }


def _project_finding_link(link) -> dict:
    return {
        "finding_id": link.finding_id,
        "category": link.finding.category,
        "severity": link.finding.severity,
        "description": link.finding.description,
    }


def _project_part(part: WorkOrderPart) -> dict:
    return {
        "id": part.pk,
        "work_order_id": part.work_order_id,
        "name": part.name,
        "description": part.description,
        "part_number": part.part_number,
        "quantity": part.quantity,
        "unit_cost": (
            str(part.unit_cost) if part.unit_cost is not None else None
        ),
        "status": part.status,
        "source_type": part.source_type,
        "source_name": part.source_name,
        "ordered_at": part.ordered_at,
        "received_at": part.received_at,
        "installed_at": part.installed_at,
        "returned_at": part.returned_at,
        "notes": part.notes,
        "created_at": part.created_at,
        "updated_at": part.updated_at,
    }


def _project_work_order(wo: WorkOrder) -> dict:
    return {
        "id": wo.pk,
        "vehicle_stock_number": wo.vehicle.stock_number,
        "category": wo.category,
        "venue": wo.venue,
        "vendor": (
            {"id": wo.vendor_id, "slug": wo.vendor.slug, "name": wo.vendor.name}
            if wo.vendor_id is not None
            else None
        ),
        "assignee_username": (
            wo.assignee.username if wo.assignee_id is not None else None
        ),
        "status": wo.status,
        "estimated_cost": (
            str(wo.estimated_cost) if wo.estimated_cost is not None else None
        ),
        "authorized_cost": (
            str(wo.authorized_cost) if wo.authorized_cost is not None else None
        ),
        "actual_cost": (
            str(wo.actual_cost) if wo.actual_cost is not None else None
        ),
        "estimated_completion_date": wo.estimated_completion_date,
        "actual_completion_date": wo.actual_completion_date,
        "notes": wo.notes,
        "approved_by": (
            wo.approved_by.username if wo.approved_by_id is not None else None
        ),
        "approved_at": wo.approved_at,
        "started_by": (
            wo.started_by.username if wo.started_by_id is not None else None
        ),
        "started_at": wo.started_at,
        "completed_by": (
            wo.completed_by.username if wo.completed_by_id is not None else None
        ),
        "completed_at": wo.completed_at,
        "cancelled_by": (
            wo.cancelled_by.username if wo.cancelled_by_id is not None else None
        ),
        "cancelled_at": wo.cancelled_at,
        "cancellation_reason": wo.cancellation_reason,
        "created_at": wo.created_at,
        "updated_at": wo.updated_at,
        "findings": [
            _project_finding_link(link)
            for link in wo.finding_links.select_related("finding").all()
        ],
        "parts": [_project_part(p) for p in wo.parts.all()],
    }


def _project_comm(comm: VendorCommunication) -> dict:
    return {
        "id": comm.pk,
        "kind": comm.kind,
        "channel": comm.channel,
        "direction": comm.direction,
        "status": comm.status,
        "vendor": (
            {"id": comm.vendor_id, "slug": comm.vendor.slug, "name": comm.vendor.name}
            if comm.vendor_id is not None
            else None
        ),
        "work_order_id": comm.work_order_id,
        "draft_content": comm.draft_content,
        "sent_content": comm.sent_content,
        "source_provenance": comm.source_provenance or {},
        "notes": comm.notes,
        "drafted_by": (
            comm.drafted_by.username if comm.drafted_by_id is not None else None
        ),
        "drafted_at": comm.drafted_at,
        "approved_by": (
            comm.approved_by.username if comm.approved_by_id is not None else None
        ),
        "approved_at": comm.approved_at,
        "sent_by": (
            comm.sent_by.username if comm.sent_by_id is not None else None
        ),
        "sent_at": comm.sent_at,
        "created_at": comm.created_at,
        "updated_at": comm.updated_at,
    }


def _project_recon_decision(decision: ReconDecision) -> dict:
    return {
        "id": decision.pk,
        "finding_id": decision.finding_id,
        "tier": decision.tier,
        "notes": decision.notes,
        "decided_by": (
            decision.decided_by.username
            if decision.decided_by_id is not None
            else None
        ),
        "decided_at": decision.decided_at,
        "created_at": decision.created_at,
        "updated_at": decision.updated_at,
    }


# ============================================================================
# Domain-error → HTTP mapping (locked at planning §7 M4.6)
# ============================================================================


def _map_service_error(exc: Exception) -> Response:
    """Translate a service-layer domain error into an appropriate
    DRF response. Every M4.6 endpoint routes its service calls
    through a try/except that funnels here."""
    if isinstance(exc, (CrossTenantReconError, CrossTenantVendorCommError)):
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(
        exc,
        (
            ReconImmutableError,
            VendorCommImmutableError,
            InvalidReconTransitionError,
            IncompleteConditionReportError,
        ),
    ):
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    if isinstance(exc, ReconFactScrubDroppedError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if isinstance(exc, EmptyDraftError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    # ValueError catches invalid vocabulary + structural bad input.
    if isinstance(exc, ValueError):
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    raise exc  # unknown — re-raise so it becomes a 500


# ============================================================================
# Request serializers
# ============================================================================


class VendorCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=64)
    categories = serializers.ListField(
        child=serializers.ChoiceField(choices=CONDITION_CATEGORY_CHOICES),
        required=False,
        default=list,
    )
    phone = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    email = serializers.EmailField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    is_active = serializers.BooleanField(required=False, default=True)


class VendorUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    categories = serializers.ListField(
        child=serializers.ChoiceField(choices=CONDITION_CATEGORY_CHOICES),
        required=False,
    )
    phone = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class ReconDecisionCreateRequestSerializer(serializers.Serializer):
    tier = serializers.ChoiceField(choices=RECON_DECISION_TIER_CHOICES)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class WorkOrderCreateRequestSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CONDITION_CATEGORY_CHOICES)
    venue = serializers.ChoiceField(choices=WORK_ORDER_VENUE_CHOICES)
    vendor_slug = serializers.SlugField(required=False, allow_null=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)
    estimated_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        default=None,
    )
    estimated_completion_date = serializers.DateField(
        required=False, allow_null=True, default=None
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class WorkOrderApproveRequestSerializer(serializers.Serializer):
    authorized_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        default=None,
    )


class WorkOrderCompleteRequestSerializer(serializers.Serializer):
    actual_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    actual_completion_date = serializers.DateField(
        required=False, allow_null=True, default=None
    )


class WorkOrderCancelRequestSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class WorkOrderPatchRequestSerializer(serializers.Serializer):
    """PATCH on WorkOrder — currently supports revise-estimate only.
    Additional whitelisted patches (notes, estimated_completion_date)
    can be added additively without changing this serializer's
    shape."""

    new_estimated_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )


class WorkOrderFindingsAttachRequestSerializer(serializers.Serializer):
    finding_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
    )


class WorkOrderPartCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    part_number = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )
    quantity = serializers.IntegerField(min_value=1, default=1)
    unit_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        default=None,
    )
    source_type = serializers.ChoiceField(
        choices=WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
        default="in_stock",
    )
    source_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class WorkOrderPartPatchRequestSerializer(serializers.Serializer):
    """PATCH on WorkOrderPart — either whitelist-update fields OR a
    status transition. Supplying ``new_status`` alone triggers a
    transition; supplying whitelist fields triggers an update.
    Mixing both in one request is rejected (400) to keep the
    intent explicit."""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    part_number = serializers.CharField(
        max_length=128, required=False, allow_blank=True
    )
    quantity = serializers.IntegerField(min_value=1, required=False)
    unit_cost = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    source_type = serializers.ChoiceField(
        choices=WORK_ORDER_PART_SOURCE_TYPE_CHOICES, required=False
    )
    source_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    new_status = serializers.ChoiceField(
        choices=WORK_ORDER_PART_STATUS_CHOICES, required=False
    )


class VendorCommDraftRequestSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=VENDOR_COMMUNICATION_KIND_CHOICES
    )
    channel = serializers.ChoiceField(
        choices=VENDOR_COMMUNICATION_CHANNEL_CHOICES
    )
    direction = serializers.ChoiceField(
        choices=VENDOR_COMMUNICATION_DIRECTION_CHOICES,
        default="outbound",
    )
    extra_notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class VendorCommMarkSentRequestSerializer(serializers.Serializer):
    sent_content = serializers.CharField(
        required=False, allow_blank=False, allow_null=True, default=None
    )


class VendorCommLogRequestSerializer(serializers.Serializer):
    work_order_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, default=None
    )
    kind = serializers.ChoiceField(
        choices=VENDOR_COMMUNICATION_KIND_CHOICES
    )
    channel = serializers.ChoiceField(
        choices=VENDOR_COMMUNICATION_CHANNEL_CHOICES
    )
    direction = serializers.ChoiceField(
        choices=VENDOR_COMMUNICATION_DIRECTION_CHOICES
    )
    body = serializers.CharField()


# ============================================================================
# Vendor CRUD
# ============================================================================


@api_view(["GET", "POST"])
@permission_classes(_M46_PERMS)
def admin_vendor_list(request):
    """List all vendors for the active dealership, or create one."""
    dealership = get_current_dealership(request)

    if request.method == "GET":
        vendors = Vendor.objects.filter(dealership=dealership).order_by("name")
        return Response(
            {"vendors": [_project_vendor(v) for v in vendors]}
        )

    serializer = VendorCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    vendor = Vendor(dealership=dealership, **data)
    try:
        vendor.full_clean()
    except Exception as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        vendor.save()
    except Exception as exc:
        # Unique-slug-per-dealership etc. surface as IntegrityError.
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    return Response(
        {"vendor": _project_vendor(vendor)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH"])
@permission_classes(_M46_PERMS)
def admin_vendor_detail(request, slug):
    """Retrieve or patch a vendor. No DELETE surface — PROTECT
    contract from planning §5.b; deactivate via ``is_active=False``
    patch instead."""
    dealership = get_current_dealership(request)
    vendor = _lookup_vendor_or_404(dealership, slug)
    if vendor is None:
        return Response(
            {"detail": "Vendor not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.method == "GET":
        return Response({"vendor": _project_vendor(vendor)})

    serializer = VendorUpdateRequestSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    for field, value in serializer.validated_data.items():
        setattr(vendor, field, value)
    try:
        vendor.full_clean()
        vendor.save()
    except Exception as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response({"vendor": _project_vendor(vendor)})


# ============================================================================
# Recon dashboard
# ============================================================================


@api_view(["GET"])
@permission_classes(_M46_PERMS)
def admin_recon_dashboard(request, stock_number):
    """Return the recon dashboard payload for a vehicle:
    latest completed condition report + decisions + WorkOrders +
    parts + comms."""
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    latest_report = latest_completed_condition_report(
        vehicle, dealership=dealership
    )
    report_projection: Optional[dict] = None
    decisions_by_finding: dict[int, dict] = {}
    if latest_report is not None:
        findings = list(
            latest_report.findings.select_related(
                "recon_decision__decided_by"
            ).all()
        )
        for finding in findings:
            try:
                decision = finding.recon_decision
                decisions_by_finding[finding.pk] = _project_recon_decision(
                    decision
                )
            except ReconDecision.DoesNotExist:
                pass
        report_projection = {
            "id": latest_report.pk,
            "inspected_at": latest_report.inspected_at,
            "inspector_name": latest_report.inspector_name,
            "mileage_at_inspection": latest_report.mileage_at_inspection,
            "completed_at": latest_report.completed_at,
            "findings": [
                {
                    "id": f.pk,
                    "category": f.category,
                    "severity": f.severity,
                    "description": f.description,
                    "estimated_cost": (
                        str(f.estimated_cost)
                        if f.estimated_cost is not None
                        else None
                    ),
                    "decision": decisions_by_finding.get(f.pk),
                }
                for f in findings
            ],
        }

    work_orders = (
        WorkOrder.objects.filter(vehicle=vehicle, dealership=dealership)
        .select_related("vendor", "assignee")
        .prefetch_related("finding_links__finding", "parts")
        .order_by("-created_at")
    )
    comms = (
        VendorCommunication.objects.filter(
            dealership=dealership, work_order__vehicle=vehicle
        )
        .select_related("vendor", "work_order", "drafted_by")
        .order_by("-created_at")
    )
    return Response(
        {
            "vehicle": {
                "stock_number": vehicle.stock_number,
                "year": vehicle.year,
                "model": vehicle.model,
            },
            "latest_condition_report": report_projection,
            "work_orders": [_project_work_order(wo) for wo in work_orders],
            "communications": [_project_comm(c) for c in comms],
        }
    )


# ============================================================================
# ReconDecision
# ============================================================================


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_recon_decision_create(request, stock_number, finding_id):
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    finding = _lookup_finding_or_404(dealership, vehicle, finding_id)
    if finding is None:
        return Response(
            {"detail": "Finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ReconDecisionCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        decision = recon_service.record_decision(
            finding,
            dealership=dealership,
            tier=serializer.validated_data["tier"],
            decided_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(
        {"decision": _project_recon_decision(decision)},
        status=status.HTTP_201_CREATED,
    )


# ============================================================================
# WorkOrder lifecycle
# ============================================================================


def _resolve_vendor_arg(dealership, vendor_slug):
    if not vendor_slug:
        return None, None
    vendor = _lookup_vendor_or_404(dealership, vendor_slug)
    if vendor is None:
        return None, Response(
            {"detail": "Vendor not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return vendor, None


def _resolve_assignee_arg(dealership, assignee_id):
    if not assignee_id:
        return None, None
    user = _lookup_user_at_dealership_or_none(dealership, assignee_id)
    if user is None:
        return None, Response(
            {"detail": "Assignee not found at this dealership."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return user, None


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_create(request, stock_number):
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = WorkOrderCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    vendor, err = _resolve_vendor_arg(dealership, data.get("vendor_slug"))
    if err is not None:
        return err
    assignee, err = _resolve_assignee_arg(dealership, data.get("assignee_id"))
    if err is not None:
        return err

    try:
        wo = recon_service.create_work_order(
            vehicle,
            dealership=dealership,
            category=data["category"],
            venue=data["venue"],
            vendor=vendor,
            assignee=assignee,
            estimated_cost=data.get("estimated_cost"),
            estimated_completion_date=data.get("estimated_completion_date"),
            notes=data.get("notes", ""),
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response(
        {"work_order": _project_work_order(wo)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_approve(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WorkOrderApproveRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        wo = recon_service.approve_work_order(
            wo,
            dealership=dealership,
            approved_by=request.user,
            authorized_cost=serializer.validated_data.get("authorized_cost"),
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_start(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        wo = recon_service.start_work_order(
            wo, dealership=dealership, started_by=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_complete(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WorkOrderCompleteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        wo = recon_service.complete_work_order(
            wo,
            dealership=dealership,
            completed_by=request.user,
            actual_cost=serializer.validated_data["actual_cost"],
            actual_completion_date=serializer.validated_data.get(
                "actual_completion_date"
            ),
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_cancel(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WorkOrderCancelRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        wo = recon_service.cancel_work_order(
            wo,
            dealership=dealership,
            cancelled_by=request.user,
            cancellation_reason=serializer.validated_data.get(
                "cancellation_reason", ""
            ),
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["PATCH"])
@permission_classes(_M46_PERMS)
def admin_work_order_patch(request, wo_id):
    """PATCH — currently supports revise-estimate via
    ``new_estimated_cost``."""
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WorkOrderPatchRequestSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if "new_estimated_cost" not in data:
        return Response(
            {"detail": "PATCH requires new_estimated_cost."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        wo = recon_service.revise_estimate(
            wo,
            dealership=dealership,
            new_estimated_cost=data["new_estimated_cost"],
            revised_by=request.user,
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_attach_findings(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WorkOrderFindingsAttachRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        recon_service.attach_findings(
            wo,
            dealership=dealership,
            finding_ids=serializer.validated_data["finding_ids"],
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["DELETE"])
@permission_classes(_M46_PERMS)
def admin_work_order_detach_finding(request, wo_id, finding_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    finding = _lookup_finding_or_404(dealership, wo.vehicle, finding_id)
    if finding is None:
        return Response(
            {"detail": "Finding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        recon_service.detach_finding(
            wo, finding, dealership=dealership
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# Parts
# ============================================================================


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_part_create(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = WorkOrderPartCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        part = recon_service.add_part(
            wo,
            dealership=dealership,
            **serializer.validated_data,
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(
        {"part": _project_part(part)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes(_M46_PERMS)
def admin_part_detail(request, part_id):
    dealership = get_current_dealership(request)
    part = _lookup_part_or_404(dealership, part_id)
    if part is None:
        return Response(
            {"detail": "Part not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.method == "DELETE":
        try:
            recon_service.delete_part(part, dealership=dealership)
        except Exception as exc:
            return _map_service_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = WorkOrderPartPatchRequestSerializer(
        data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    new_status = data.pop("new_status", None)
    # Mixing update + transition in one request is ambiguous —
    # force the caller to make one request per intent.
    if new_status is not None and data:
        return Response(
            {
                "detail": (
                    "Mixing whitelist update fields with new_status "
                    "in a single PATCH is not supported. Send one "
                    "request per intent."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        if new_status is not None:
            part = recon_service.transition_part_status(
                part,
                dealership=dealership,
                new_status=new_status,
                actor=request.user,
            )
        elif data:
            part = recon_service.update_part(
                part, dealership=dealership, **data
            )
        else:
            return Response(
                {"detail": "Empty PATCH body."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except Exception as exc:
        return _map_service_error(exc)
    return Response({"part": _project_part(part)})


# ============================================================================
# Vendor communications
# ============================================================================


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_comm_draft(request, wo_id):
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = VendorCommDraftRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        comm = vendor_comm_service.draft_communication(
            wo,
            dealership=dealership,
            drafted_by=request.user,
            kind=data["kind"],
            channel=data["channel"],
            direction=data.get("direction", "outbound"),
            extra_notes=data.get("extra_notes", ""),
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(
        {"communication": _project_comm(comm)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_comm_approve(request, comm_id):
    dealership = get_current_dealership(request)
    comm = _lookup_comm_or_404(dealership, comm_id)
    if comm is None:
        return Response(
            {"detail": "Communication not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        comm = vendor_comm_service.approve_communication(
            comm, dealership=dealership, approved_by=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response({"communication": _project_comm(comm)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_comm_mark_sent(request, comm_id):
    dealership = get_current_dealership(request)
    comm = _lookup_comm_or_404(dealership, comm_id)
    if comm is None:
        return Response(
            {"detail": "Communication not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = VendorCommMarkSentRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        comm = vendor_comm_service.mark_sent(
            comm,
            dealership=dealership,
            sent_by=request.user,
            sent_content=serializer.validated_data.get("sent_content"),
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response({"communication": _project_comm(comm)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_comm_log(request):
    dealership = get_current_dealership(request)
    serializer = VendorCommLogRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    work_order = None
    if data.get("work_order_id") is not None:
        work_order = _lookup_work_order_or_404(
            dealership, data["work_order_id"]
        )
        if work_order is None:
            return Response(
                {"detail": "Work order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    try:
        comm = vendor_comm_service.log_communication(
            work_order,
            dealership=dealership,
            logged_by=request.user,
            kind=data["kind"],
            channel=data["channel"],
            direction=data["direction"],
            body=data["body"],
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(
        {"communication": _project_comm(comm)},
        status=status.HTTP_201_CREATED,
    )
