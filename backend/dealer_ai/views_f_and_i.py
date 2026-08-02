"""Milestone 10 · Increment 1 (SESSION_106) — admin API for the F&I subsystem.

One endpoint at M10.1. Composes :class:`IsAuthenticated` &
:class:`IsFinanceManagerOrOwnerAtActiveDealership` per
``MILESTONE_10_PLANNING.md`` §7 M10.1 (mirrors the M4-M9 pattern
with the F&I-specific permission class introduced in M10.1).
``f_and_i_manager`` and ``dealer_owner`` at the active dealership
pass; every other role receives 403.

Delegates entirely to :mod:`services.f_and_i`. No business logic
lives here — thin translation between HTTP and the service surface.

Domain-error → HTTP status mapping (matches M4-M9 conventions):

- :class:`CrossTenantCreditApplicationError` → 404 (never leak
  whether the resource exists across tenants).
- :class:`ValueError` (attach-shape violation, unknown
  ``source_format``, unknown ``status``) → 400.

Tenant scoping: every endpoint resolves ``dealership`` via
:func:`services.tenancy.get_current_dealership` and passes it
explicitly into service calls. Cross-tenant lookups (URL kwarg
references a lead or sale owned by another dealership) surface as
404 rather than 403, matching the M2.6 / M3.6 / M4.6 / M9.1
fail-closed pattern.

The M10.2-M10.7 endpoints (deal-desk, lender submission, stipulation
tracking, contract, funding, chargeback) will land in this module
as sibling view functions — same pattern as :mod:`views_recon` /
:mod:`views_sale`.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CREDIT_APP_FORMAT_CHOICES,
    CREDIT_APP_STATUS_CHOICES,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Sale,
    Vehicle,
)
from .permissions import IsFinanceManagerOrOwnerAtActiveDealership
from .services import f_and_i as f_and_i_service
from .services.f_and_i import (
    CrossTenantCreditApplicationError,
    CrossTenantDealStructureError,
)
from .services.tenancy import get_current_dealership


_M101_PERMS = [
    IsAuthenticated & IsFinanceManagerOrOwnerAtActiveDealership
]


def _lookup_lead_or_404(dealership, lead_id):
    try:
        return CustomerLead.objects.filter(dealership=dealership).get(
            pk=lead_id
        )
    except CustomerLead.DoesNotExist:
        return None


def _lookup_sale_or_404(dealership, sale_id):
    try:
        return Sale.objects.filter(dealership=dealership).get(pk=sale_id)
    except Sale.DoesNotExist:
        return None


def _project_credit_application(app: CreditApplication) -> dict:
    return {
        "id": app.pk,
        "lead_id": app.lead_id,
        "sale_id": app.sale_id,
        "applicant_full_name": app.applicant_full_name,
        "applicant_ssn_last4": app.applicant_ssn_last4,
        "source_format": app.source_format,
        "status": app.status,
        "captured_at": app.captured_at.isoformat(),
        "retention_expires_at": app.retention_expires_at.isoformat(),
        "notes": app.notes,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
    }


class CreditApplicationCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/credit-applications/``."""

    applicant_full_name = serializers.CharField(max_length=255)
    source_format = serializers.ChoiceField(
        choices=[key for key, _ in CREDIT_APP_FORMAT_CHOICES]
    )
    lead_id = serializers.IntegerField(required=False, allow_null=True)
    sale_id = serializers.IntegerField(required=False, allow_null=True)
    applicant_ssn_last4 = serializers.CharField(
        required=False, allow_blank=True, max_length=4, default=""
    )
    status = serializers.ChoiceField(
        choices=[key for key, _ in CREDIT_APP_STATUS_CHOICES],
        required=False,
    )
    captured_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_credit_application_create(request):
    """POST: create a CreditApplication (M10.1 write path).

    At least one of ``lead_id`` / ``sale_id`` must be provided in
    the request body (§5.a Option C). Cross-tenant references
    (lead or sale belongs to another dealership) surface as 404,
    same fail-closed shape as M9.1. Retention clock is populated
    on the server from ``captured_at`` (defaulting to now) — the
    client cannot set ``retention_expires_at`` directly.
    """
    dealership = get_current_dealership(request)

    serializer = CreditApplicationCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    lead = None
    if data.get("lead_id") is not None:
        lead = _lookup_lead_or_404(dealership, data["lead_id"])
        if lead is None:
            return Response(
                {"detail": "Lead not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    sale = None
    if data.get("sale_id") is not None:
        sale = _lookup_sale_or_404(dealership, data["sale_id"])
        if sale is None:
            return Response(
                {"detail": "Sale not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Build kwargs for the service verb. Only pass optional fields
    # when the client provided them so the verb's own defaults
    # apply (``status`` defaults to ``received``; ``captured_at``
    # defaults to ``timezone.now()``).
    service_kwargs = dict(
        dealership=dealership,
        applicant_full_name=data["applicant_full_name"],
        source_format=data["source_format"],
        lead=lead,
        sale=sale,
        applicant_ssn_last4=data.get("applicant_ssn_last4", ""),
        notes=data.get("notes", ""),
    )
    if "status" in data:
        service_kwargs["status"] = data["status"]
    if data.get("captured_at") is not None:
        service_kwargs["captured_at"] = data["captured_at"]

    try:
        app = f_and_i_service.record_credit_application(**service_kwargs)
    except CrossTenantCreditApplicationError:
        # Never leak cross-tenant existence. Same fail-closed shape
        # as M2.6 / M3.6 / M4.6 / M9.1.
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"credit_application": _project_credit_application(app)},
        status=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 2 (SESSION_107) — DealStructure admin endpoint.
# ---------------------------------------------------------------------------
#
# Same permission composition as the M10.1 credit-application endpoint
# above (``_M101_PERMS``). Flat URL shape (``/admin/deal-structures/``)
# per §1.9.a Option A (user-confirmed at SESSION_107 open, recorded
# in §0.a) — matches the M10.1 credit-application URL pattern and the
# platform-wide M1-M9 flat resource-naming convention.


def _lookup_credit_application_or_404(dealership, credit_application_id):
    try:
        return CreditApplication.objects.filter(dealership=dealership).get(
            pk=credit_application_id
        )
    except CreditApplication.DoesNotExist:
        return None


def _lookup_vehicle_by_stock_or_404(dealership, stock_number):
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _project_deal_structure(deal: DealStructure) -> dict:
    return {
        "id": deal.pk,
        "credit_application_id": deal.credit_application_id,
        "vehicle_stock": deal.vehicle.stock_number,
        "sale_price": str(deal.sale_price),
        "down_payment": str(deal.down_payment),
        "trade_allowance": str(deal.trade_allowance),
        "trade_payoff": str(deal.trade_payoff),
        "taxes": str(deal.taxes),
        "fees": str(deal.fees),
        "amount_financed": str(deal.amount_financed),
        "apr": str(deal.apr),
        "term_months": deal.term_months,
        "monthly_payment": str(deal.monthly_payment),
        "back_end_products": deal.back_end_products,
        # Ratios may be None (M10.1-era CA without income captured).
        # Serialize as string when present, null when absent — matches
        # the M9.1 Sale.gross_realized shape (stringified Decimal).
        "ltv_pct": str(deal.ltv_pct) if deal.ltv_pct is not None else None,
        "pti_pct": str(deal.pti_pct) if deal.pti_pct is not None else None,
        "dti_pct": str(deal.dti_pct) if deal.dti_pct is not None else None,
        "created_at": deal.created_at.isoformat(),
        "updated_at": deal.updated_at.isoformat(),
    }


class DealStructureCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/deal-structures/``."""

    credit_application_id = serializers.IntegerField()
    vehicle_stock = serializers.CharField(max_length=64)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    amount_financed = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    apr = serializers.DecimalField(max_digits=6, decimal_places=4)
    term_months = serializers.IntegerField(min_value=1)
    monthly_payment = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    down_payment = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    trade_allowance = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    trade_payoff = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    taxes = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    fees = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    back_end_products = serializers.ListField(
        child=serializers.DictField(), required=False, default=list
    )


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_deal_structure_create(request):
    """POST: create a DealStructure (M10.2 write path).

    Requires ``credit_application_id`` + ``vehicle_stock`` plus the
    deal-desk math fields. Cross-tenant references (CA or vehicle
    belongs to another dealership) surface as 404, same fail-closed
    shape as M9.1 / M10.1. Ratios (LTV / PTI / DTI) are computed
    server-side and returned in the response — the client cannot
    submit them directly (they're always denormalized outputs).
    """
    dealership = get_current_dealership(request)

    serializer = DealStructureCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    credit_application = _lookup_credit_application_or_404(
        dealership, data["credit_application_id"]
    )
    if credit_application is None:
        return Response(
            {"detail": "Credit application not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    vehicle = _lookup_vehicle_by_stock_or_404(dealership, data["vehicle_stock"])
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        deal = f_and_i_service.record_deal_structure(
            dealership=dealership,
            credit_application=credit_application,
            vehicle=vehicle,
            sale_price=data["sale_price"],
            amount_financed=data["amount_financed"],
            apr=data["apr"],
            term_months=data["term_months"],
            monthly_payment=data["monthly_payment"],
            down_payment=data.get("down_payment"),
            trade_allowance=data.get("trade_allowance"),
            trade_payoff=data.get("trade_payoff"),
            taxes=data.get("taxes"),
            fees=data.get("fees"),
            back_end_products=data.get("back_end_products"),
        )
    except CrossTenantDealStructureError:
        # Never leak cross-tenant existence. Same fail-closed shape
        # as M2.6 / M3.6 / M4.6 / M9.1 / M10.1.
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"deal_structure": _project_deal_structure(deal)},
        status=status.HTTP_201_CREATED,
    )
