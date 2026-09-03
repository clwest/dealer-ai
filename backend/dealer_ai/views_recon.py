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

from django.db.models import Case, IntegerField, Value, When
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CONDITION_CATEGORY_CHOICES,
    ConditionFinding,
    Vehicle,
    VehicleCost,
    VENDOR_COMMUNICATION_CHANNEL_CHOICES,
    VENDOR_COMMUNICATION_DIRECTION_CHOICES,
    VENDOR_COMMUNICATION_KIND_CHOICES,
    Vendor,
    VendorCommunication,
    WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
    WORK_ORDER_PART_STATUS_CHOICES,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_CHOICES,
    WorkOrder,
    WorkOrderPart,
    RECON_DECISION_TIER_CHOICES,
    ReconDecision,
)
from .permissions import (
    IsDealerOwnerAtActiveDealership,
    IsReconManagerSalesManagerOrOwnerAtActiveDealership,
    IsSalesManagerOrOwnerAtActiveDealership,
)
from .services import recon as recon_service
from .services import recon_budget as recon_budget_service
from .services import vehicle_lifecycle as lifecycle_service
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
from .services.recon_budget import (
    BudgetCheckError,
    CrossTenantRateCardError,
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
_OWNER_ONLY_PERMS = [IsAuthenticated & IsDealerOwnerAtActiveDealership]
# Send-to-wholesale needs sales_manager or owner authority — the
# same set that gates every commercial-disposition stage in the
# lifecycle service (owner + sales_manager per M5 §5.f).
_WHOLESALE_PERMS = [
    IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership
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
        # SESSION_228.1 — linked Vendor when outside_vendor source_name
        # matched a store record.
        "vendor": (
            {
                "id": part.vendor_id,
                "slug": part.vendor.slug,
                "name": part.vendor.name,
            }
            if part.vendor_id is not None
            else None
        ),
        "ordered_at": part.ordered_at,
        "received_at": part.received_at,
        "installed_at": part.installed_at,
        "returned_at": part.returned_at,
        "notes": part.notes,
        "created_at": part.created_at,
        "updated_at": part.updated_at,
    }


def _project_ledger_row(cost: VehicleCost) -> dict:
    return {
        "id": cost.pk,
        "category": cost.category,
        "amount": str(cost.amount),
        "reference": cost.reference,
        "notes": cost.notes,
        "is_estimate": cost.is_estimate,
        "vendor": cost.vendor,
        "incurred_at": cost.incurred_at,
        "created_at": cost.created_at,
    }


def _project_estimate_revision(revision) -> dict:
    return {
        "id": revision.pk,
        "from_amount": (
            str(revision.from_amount)
            if revision.from_amount is not None
            else None
        ),
        "to_amount": str(revision.to_amount),
        "reason": revision.reason,
        "revised_by": (
            revision.revised_by.username
            if revision.revised_by_id is not None
            else None
        ),
        "revised_at": revision.revised_at,
    }


def _project_budget_override(override) -> dict:
    """SESSION_228.1 — surface each per-vehicle recon-budget override
    on the WO projection so a manager reading the card sees WHY the
    cap moved and by how much."""
    return {
        "id": override.pk,
        "amount": str(override.amount),
        "reason": override.reason,
        "granted_by": (
            override.granted_by.username
            if override.granted_by_id is not None
            else None
        ),
        "granted_at": override.granted_at,
    }


def _project_work_order(wo: WorkOrder) -> dict:
    # Ledger rows this WO has posted (all five families:
    # estimate:<seq>, estimate_reversal:<seq>,
    # completion_estimate_reversal, estimate_reversal:cancel, actual).
    # SESSION_227 — the recon page reads this directly to render the
    # estimate → actual story on completed cards.
    ledger_rows = (
        VehicleCost.objects.filter(
            vehicle=wo.vehicle,
            dealership=wo.dealership,
            reference__startswith=f"WORKORDER:{wo.pk}:",
        )
        .order_by("created_at")
    )
    revisions = wo.estimate_revisions.select_related("revised_by").all()
    # SESSION_228.1 — per-vehicle recon-budget overrides, additive.
    # Every card that reads a WO on this car surfaces the override
    # history so the auto-authorization / queue notes have context.
    overrides = wo.vehicle.recon_budget_overrides.select_related(
        "granted_by"
    ).order_by("-granted_at")
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
        "ledger_rows": [_project_ledger_row(c) for c in ledger_rows],
        "estimate_revisions": [
            _project_estimate_revision(r) for r in revisions
        ],
        "budget_overrides": [
            _project_budget_override(o) for o in overrides
        ],
        # SESSION_228 Part 1b — parts roll into the WO's money.
        # Frontend reads these to render "Labor $X + Parts $Y =
        # $Total" on every card without recomputing.
        "parts_estimate": str(recon_budget_service.parts_estimate(wo)),
        "parts_actual": str(recon_budget_service.parts_actual(wo)),
        "total_estimate": str(recon_budget_service.wo_estimate_total(wo)),
        "total_actual": str(recon_budget_service.wo_actual_total(wo)),
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
    if isinstance(
        exc,
        (
            CrossTenantReconError,
            CrossTenantVendorCommError,
            CrossTenantRateCardError,
        ),
    ):
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, BudgetCheckError):
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
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
    reason = serializers.CharField(
        required=False, allow_blank=False, trim_whitespace=True
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
    # SESSION_227 — the recon page is finding-centric. For each
    # finding we need the ID of its LIVE work order (draft /
    # approved / in_progress) so the UI can render one job card
    # per finding without a second round trip.
    live_wo_by_finding: dict[int, int] = {}
    if latest_report is not None:
        findings = list(
            latest_report.findings.select_related(
                "recon_decision__decided_by",
                "discovered_on_work_order",
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
        finding_ids = [f.pk for f in findings]
        if finding_ids:
            live_links = (
                WorkOrder.objects.filter(
                    dealership=dealership,
                    finding_links__finding_id__in=finding_ids,
                    status__in=(
                        WORK_ORDER_STATUS_DRAFT,
                        WORK_ORDER_STATUS_APPROVED,
                        WORK_ORDER_STATUS_IN_PROGRESS,
                    ),
                )
                .values_list(
                    "finding_links__finding_id", "pk"
                )
            )
            for finding_id, wo_id in live_links:
                # Idempotent — take the first live WO per finding
                # (dashboard ordering already puts newest open first).
                live_wo_by_finding.setdefault(finding_id, wo_id)
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
                    "work_order_id": live_wo_by_finding.get(f.pk),
                    "discovered_during_work": f.discovered_during_work,
                    "discovered_on_work_order_id": (
                        f.discovered_on_work_order_id
                    ),
                    # SESSION_228.1 — surface the rate-card link on
                    # findings so the frontend can render "(from LOF
                    # rate card)" or link back to the sheet.
                    "rate_card_item_id": f.rate_card_item_id,
                }
                for f in findings
            ],
        }

    # Open work (draft / approved / in_progress) sorts ahead of
    # terminal work (completed / cancelled), so the recon page opens
    # on the row a manager actually needs to act on — the awaiting-
    # authorization draft is the whole point of the recon-gate pitch.
    # -created_at breaks ties within each priority band so the newest
    # open WO leads, and the newest terminal WO leads its own group.
    # Kept in the queryset (not the frontend) so any client reading
    # this endpoint gets the same truth.
    open_wo_status = (
        WORK_ORDER_STATUS_DRAFT,
        WORK_ORDER_STATUS_APPROVED,
        WORK_ORDER_STATUS_IN_PROGRESS,
    )
    work_orders = (
        WorkOrder.objects.filter(vehicle=vehicle, dealership=dealership)
        .select_related("vendor", "assignee")
        .prefetch_related("finding_links__finding", "parts")
        .annotate(
            _status_priority=Case(
                When(status__in=open_wo_status, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("_status_priority", "-created_at")
    )
    comms = (
        VendorCommunication.objects.filter(
            dealership=dealership, work_order__vehicle=vehicle
        )
        .select_related("vendor", "work_order", "drafted_by")
        .order_by("-created_at")
    )
    # SESSION_228.1 — the page needs to show "$409 of $1,800 used"
    # per car, so budget + spend go in the top-level payload.
    # Both are `None` for `per_job` stores or budget-mode stores with
    # no cap filled in — the frontend renders the numbers only when
    # both are set.
    budget = recon_budget_service.recon_budget_for(
        vehicle, dealership=dealership
    )
    spend = recon_budget_service.recon_spend_for(
        vehicle, dealership=dealership
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
            # SESSION_229 Part 3 — both fields already quantize to
            # two places at the service layer; the string cast here
            # is the last stop before the wire.
            "recon_budget": str(budget) if budget is not None else None,
            "recon_spend": str(spend),
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
    if "reason" not in data or not (data.get("reason") or "").strip():
        return Response(
            {"detail": "PATCH requires a nonblank reason."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        wo = recon_service.revise_estimate(
            wo,
            dealership=dealership,
            new_estimated_cost=data["new_estimated_cost"],
            reason=data["reason"],
            revised_by=request.user,
        )
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_work_order_from_finding(request, stock_number, finding_id):
    """Create (or return the existing live) draft WorkOrder for one
    finding, in one call. Pre-fills category / estimated_cost /
    description from the finding, links the finding to the WO, all
    in one transaction. SESSION_227 — recon-one-card."""
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
    try:
        wo = recon_service.create_work_order_from_finding(
            finding,
            dealership=dealership,
            created_by=request.user,
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
def admin_recon_create_must_do_work_orders(request, stock_number):
    """For each must-do finding on the vehicle's latest completed
    report that has no live WO, create a draft WO from it. Returns
    the list of resulting WOs (freshly created or already live).
    SESSION_227 — one click, no re-typing."""
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        wos = recon_service.create_work_orders_for_all_must_dos(
            vehicle,
            dealership=dealership,
            created_by=request.user,
        )
    except Exception as exc:
        return _map_service_error(exc)
    refreshed = [
        _lookup_work_order_or_404(dealership, wo.pk) for wo in wos
    ]
    return Response(
        {"work_orders": [_project_work_order(w) for w in refreshed]},
        status=status.HTTP_201_CREATED,
    )


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


# ============================================================================
# SESSION_228 — recon budget + rate card + needs-authorization queue
# ============================================================================


def _project_rate_card_item(item) -> dict:
    return {
        "id": item.pk,
        "name": item.name,
        "work_order_category": item.work_order_category,
        "flat_price": str(item.flat_price),
        "variant": item.variant,
        "retail_default": item.retail_default,
        "active": item.active,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _project_settings(profile) -> dict:
    if profile is None:
        return {
            "recon_authorization_mode": "per_job",
            "recon_budget_default": None,
            "recon_budget_bands": [],
        }
    return {
        "recon_authorization_mode": profile.recon_authorization_mode,
        "recon_budget_default": (
            str(profile.recon_budget_default)
            if profile.recon_budget_default is not None
            else None
        ),
        "recon_budget_bands": list(profile.recon_budget_bands or []),
    }


class ReconSettingsUpdateRequestSerializer(serializers.Serializer):
    recon_authorization_mode = serializers.ChoiceField(
        choices=[("per_job", "Per job"), ("budget", "Budget")],
        required=False,
    )
    recon_budget_default = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
    )
    recon_budget_bands = serializers.ListField(
        child=serializers.DictField(), required=False
    )


class RateCardCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    work_order_category = serializers.ChoiceField(
        choices=CONDITION_CATEGORY_CHOICES
    )
    flat_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    variant = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )
    retail_default = serializers.BooleanField(required=False, default=False)
    active = serializers.BooleanField(required=False, default=True)


class RateCardUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128, required=False)
    work_order_category = serializers.ChoiceField(
        choices=CONDITION_CATEGORY_CHOICES, required=False
    )
    flat_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
    )
    variant = serializers.CharField(
        max_length=64, required=False, allow_blank=True
    )
    retail_default = serializers.BooleanField(required=False)
    active = serializers.BooleanField(required=False)


class AuthorizeWithOverrideRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1)


class SendToWholesaleRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1)


# ---- Store settings (owner only) ------------------------------------------


@api_view(["GET", "PATCH"])
@permission_classes(_OWNER_ONLY_PERMS)
def admin_recon_settings(request):
    """Read or update the store's recon authorization + budget
    settings. Owner-only, matches the sensitivity of every other
    store-shape decision (dealer_type, floor_plan_apr etc.)."""
    dealership = get_current_dealership(request)
    from .models import DealerOnboardingProfile
    profile = recon_budget_service._store_profile(dealership)
    if request.method == "GET":
        return Response({"settings": _project_settings(profile)})
    serializer = ReconSettingsUpdateRequestSerializer(
        data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if profile is None:
        profile = DealerOnboardingProfile.objects.create(
            dealership=dealership,
            recon_authorization_mode=data.get(
                "recon_authorization_mode", "per_job"
            ),
        )
    for field in (
        "recon_authorization_mode",
        "recon_budget_default",
        "recon_budget_bands",
    ):
        if field in data:
            setattr(profile, field, data[field])
    profile.full_clean()
    profile.save()
    return Response({"settings": _project_settings(profile)})


# ---- Rate card (owner + recon manager) ------------------------------------


@api_view(["GET", "POST"])
@permission_classes(_M46_PERMS)
def admin_rate_card_list(request):
    dealership = get_current_dealership(request)
    if request.method == "GET":
        include_inactive = request.query_params.get("include_inactive") == "1"
        items = recon_budget_service.list_rate_card_items(
            dealership, active_only=not include_inactive
        )
        return Response(
            {"items": [_project_rate_card_item(i) for i in items]}
        )
    serializer = RateCardCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        item = recon_budget_service.create_rate_card_item(
            dealership, **serializer.validated_data
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(
        {"item": _project_rate_card_item(item)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes(_M46_PERMS)
def admin_rate_card_detail(request, item_id):
    from .models import ReconRateCard
    dealership = get_current_dealership(request)
    try:
        item = ReconRateCard.objects.filter(dealership=dealership).get(
            pk=item_id
        )
    except ReconRateCard.DoesNotExist:
        return Response(
            {"detail": "Rate card item not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if request.method == "DELETE":
        try:
            recon_budget_service.deactivate_rate_card_item(
                item, dealership=dealership
            )
        except Exception as exc:
            return _map_service_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = RateCardUpdateRequestSerializer(
        data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    try:
        item = recon_budget_service.update_rate_card_item(
            item, dealership=dealership, **serializer.validated_data
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response({"item": _project_rate_card_item(item)})


# ---- Needs-authorization queue --------------------------------------------


@api_view(["GET"])
@permission_classes(_M46_PERMS)
def admin_recon_needs_authorization_queue(request):
    """Cross-lot queue of draft WOs with linked findings — the
    exception queue behind the budget-gate pitch. Each row carries
    its overage so the manager can triage in the browser.

    SESSION_229 Part 6 — the row now also carries ``prior_spend``
    (already committed on the car) and vehicle year/make/model +
    acquisition_total + asking_price so a manager can answer "is
    this car worth $1,670?" without a second round trip.
    """
    dealership = get_current_dealership(request)
    queue = recon_budget_service.needs_authorization_queue(dealership)
    payload = []
    for wo in queue:
        overage = recon_budget_service.overage_for(
            wo, dealership=dealership
        )
        budget = recon_budget_service.recon_budget_for(
            wo.vehicle, dealership=dealership
        )
        prior_spend = recon_budget_service.recon_spend_for(
            wo.vehicle, dealership=dealership, exclude_wo=wo
        )
        # SESSION_229 Part 6b — the queue queryset select_related's
        # ``vehicle__acquisition`` so this touches the prefetched
        # row rather than triggering a per-vehicle query.
        acquisition_total = _acquisition_cash_total(wo.vehicle)
        payload.append(
            {
                "work_order": _project_work_order(wo),
                "overage": str(overage),
                "budget": str(budget) if budget is not None else None,
                "prior_spend": str(prior_spend),
                "vehicle": {
                    "stock_number": wo.vehicle.stock_number,
                    "year": wo.vehicle.year,
                    "make": wo.vehicle.make,
                    "model": wo.vehicle.model,
                    "trim": wo.vehicle.trim,
                    "acquisition_total": str(acquisition_total),
                    "asking_price": str(wo.vehicle.price),
                },
            }
        )
    return Response({"queue": payload})


def _acquisition_cash_total(vehicle) -> Decimal:
    """Sum of every cash line on the vehicle's acquisition row, or
    zero when no acquisition exists yet. Reads the OneToOne
    accessor directly so a prefetched ``vehicle__acquisition`` on
    the caller's queryset stays out of the N+1 path."""
    try:
        acq = vehicle.acquisition
    except Exception:  # VehicleAcquisition.DoesNotExist
        return Decimal("0.00")
    return (
        Decimal(acq.purchase_price)
        + Decimal(acq.buyer_fees)
        + Decimal(acq.arbitration_fees)
        + Decimal(acq.transportation_cost)
        + Decimal(acq.title_acquisition_cost)
    ).quantize(Decimal("0.01"))


# ---- Authorize with override (per-vehicle budget raise) -------------------


@api_view(["POST"])
@permission_classes(_M46_PERMS)
def admin_authorize_with_override(request, wo_id):
    """Authorize a queued WO by raising its car's budget by the
    overage. Non-blank reason required — the whole point of
    :class:`VehicleReconBudgetOverride` is the audit trail."""
    dealership = get_current_dealership(request)
    wo = _lookup_work_order_or_404(dealership, wo_id)
    if wo is None:
        return Response(
            {"detail": "Work order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = AuthorizeWithOverrideRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reason = serializer.validated_data["reason"]
    overage = recon_budget_service.overage_for(wo, dealership=dealership)
    try:
        if overage > 0:
            recon_budget_service.record_budget_override(
                wo.vehicle,
                dealership=dealership,
                amount=overage,
                reason=reason,
                granted_by=request.user,
            )
        recon_service.approve_work_order(
            wo, dealership=dealership, approved_by=request.user
        )
        # SESSION_229 Part 4 — the "needs authorization:" queued
        # prefix used to survive override authorize, so an
        # Approved chip and an amber queued note appeared on the
        # same card. Strip in the backend so the stored note stops
        # lying too — any other reader (queue, ledger, exports)
        # gets the corrected note.
        wo.refresh_from_db()
        stripped = recon_budget_service.strip_queued_note_prefix(wo.notes)
        if stripped != wo.notes:
            wo.notes = stripped
            wo.save(update_fields=["notes", "updated_at"])
    except Exception as exc:
        return _map_service_error(exc)
    wo = _lookup_work_order_or_404(dealership, wo.pk)
    return Response({"work_order": _project_work_order(wo)})


# ---- Send to wholesale (owner / sales manager) ----------------------------


@api_view(["POST"])
@permission_classes(_WHOLESALE_PERMS)
def admin_send_vehicle_to_wholesale(request, stock_number):
    """Cancel every open WO on the vehicle with the operator's
    reason, then advance the vehicle to ``wholesale_out``.
    Prior spend stays on the ledger (Chris's "the board warned
    you" demo beat)."""
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = SendToWholesaleRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reason = serializer.validated_data["reason"]
    try:
        open_wos = WorkOrder.objects.filter(
            vehicle=vehicle,
            dealership=dealership,
            status__in=(
                WORK_ORDER_STATUS_DRAFT,
                WORK_ORDER_STATUS_APPROVED,
                WORK_ORDER_STATUS_IN_PROGRESS,
            ),
        )
        for wo in open_wos:
            recon_service.cancel_work_order(
                wo,
                dealership=dealership,
                cancelled_by=request.user,
                cancellation_reason=reason,
            )
        lifecycle_service.ensure_current_stage(
            vehicle, dealership=dealership, actor=request.user
        )
        lifecycle_service.advance_stage(
            vehicle,
            dealership=dealership,
            to_stage="wholesale_out",
            trigger="manual",
            actor=request.user,
            notes=reason,
        )
    except lifecycle_service.CrossTenantLifecycleError:
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except lifecycle_service.UnauthorizedStageTransitionError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN
        )
    except (
        lifecycle_service.InvalidStageTransitionError,
        lifecycle_service.StageAlreadyCurrentError,
    ) as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except Exception as exc:
        return _map_service_error(exc)
    return Response(
        {
            "vehicle_stock_number": vehicle.stock_number,
            "new_stage": "wholesale_out",
        }
    )
