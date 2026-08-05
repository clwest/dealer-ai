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

from typing import Optional

from django.utils.dateparse import parse_datetime
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    BEPA_TYPE_CHOICES,
    CHARGEBACK_TYPE_CHOICES,
    CONTRACT_TYPE_CHOICES,
    CREDIT_APP_FORMAT_CHOICES,
    CREDIT_APP_STATUS_CHOICES,
    LENDER_SUBMISSION_STATUS_CHOICES,
    STIPULATION_STATE_CHOICES,
    STIPULATION_TYPE_CHOICES,
    BackEndProductAgreement,
    Chargeback,
    ComplianceRecord,
    Contract,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Funding,
    LenderProgram,
    LenderSubmission,
    Sale,
    Stipulation,
    Vehicle,
)
from .permissions import IsFinanceManagerOrOwnerAtActiveDealership
from .services import f_and_i as f_and_i_service
from .services.f_and_i import (
    ComplianceAlreadyExistsError,
    ContractAlreadyVoidedError,
    CrossTenantChargebackError,
    CrossTenantComplianceError,
    CrossTenantContractError,
    CrossTenantCreditApplicationError,
    CrossTenantDealStructureError,
    CrossTenantFundingError,
    CrossTenantLenderSubmissionError,
    CrossTenantStipulationError,
    DuplicateLenderProgramError,
    FundingAlreadyExistsError,
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
# Milestone 32 · Increment 1 (SESSION_207) — F&I intake list endpoint.
#
# GET /admin/credit-applications/ — F&I intake queue read.
#
# Per MILESTONE_32_PLANNING.md §5.b D3. First F&I-role-gated list
# endpoint (approve/handoff-adjacent surface finally has an F&I-
# side receiver). Fail-explicit query validation — invalid values
# return 400 with a clear message rather than silently unfiltering.
# `intake=false` explicitly rejected — reserved-and-unavailable in
# M32 to preserve semantic clarity; use `has_contract=true` (or
# similar) in a future milestone if the "already-contracted" filter
# surfaces evidence.
#
# Projection includes writeup-context fields via the D9-revised²
# nullable OneToOneField backpointer added at M32.1 — deterministic
# pairing at query time; no text-parsing of `notes`.
# ---------------------------------------------------------------------------


def _project_writeup_context(app: CreditApplication) -> dict:
    """Milestone 32 · Increment 1 — nested writeup-context projection.

    When ``app.deal_writeup`` is populated (hand-off-created CA per
    M11.3 + M32.1), returns the four-square terms + attribution
    fields the F&I intake row needs to render inline. When NULL
    (direct-create CA via M10.1 or historical row), returns None so
    the endpoint can emit ``writeup_context: null`` truthfully.
    """
    writeup = app.deal_writeup
    if writeup is None:
        return None  # type: ignore[return-value]
    lead = writeup.lead
    vehicle = writeup.vehicle
    return {
        "deal_writeup_id": writeup.pk,
        "written_up_by_user_id": writeup.written_up_by_user_id,
        "sales_manager_approved_by_user_id": (
            writeup.sales_manager_approved_by_user_id
        ),
        "handed_off_to_fandi_at": (
            writeup.handed_off_to_fandi_at.isoformat()
            if writeup.handed_off_to_fandi_at
            else None
        ),
        "lead": {
            "id": lead.pk,
            "name": lead.name,
            "phone": lead.phone,
            "email": lead.email,
        },
        "vehicle": {
            "id": vehicle.pk,
            "stock_number": vehicle.stock_number,
            "year": vehicle.year,
            "make": vehicle.make,
            "model": vehicle.model,
        },
        "terms": {
            "vehicle_price": (
                str(writeup.vehicle_price)
                if writeup.vehicle_price is not None
                else None
            ),
            "trade_allowance": (
                str(writeup.trade_allowance)
                if writeup.trade_allowance is not None
                else None
            ),
            "down_payment": (
                str(writeup.down_payment)
                if writeup.down_payment is not None
                else None
            ),
            "monthly_payment_target": (
                str(writeup.monthly_payment_target)
                if writeup.monthly_payment_target is not None
                else None
            ),
            "term_months_target": writeup.term_months_target,
            "apr_target": (
                str(writeup.apr_target)
                if writeup.apr_target is not None
                else None
            ),
        },
    }


def _project_credit_application_with_writeup(app: CreditApplication) -> dict:
    """M32.1 + M33.1 projection: base CA projection + writeup context
    + derived DealStructure status fields.

    Extends :func:`_project_credit_application` (M10.1) with:

    - ``writeup_context`` (M32.1) — nested object or ``None`` when
      the CA has no ``deal_writeup`` backpointer (direct-create or
      historical row).
    - ``has_deal_structure`` (M33.1) — Boolean derived from the
      tenant-scoped ``Exists`` annotation set by
      :func:`services.f_and_i.list_credit_applications`. Drives
      the M33 intake-row chip ("Incoming" when ``False``;
      "In progress" when ``True``).
    - ``latest_deal_structure_id`` (M33.1) — nullable int derived
      from the deterministic ``("-created_at", "-pk")`` subquery
      set by :func:`services.f_and_i.list_credit_applications`.
      Populated with the latest DealStructure pk when
      ``has_deal_structure`` is ``True``; ``None`` when
      ``False``. Drives the M33 "Open structure" action which
      fetches the full row via ``GET /admin/deal-structures/<pk>/``.

    Per ``MILESTONE_33_PLANNING.md`` §5.b D1 + D3.
    """
    base = _project_credit_application(app)
    base["writeup_context"] = _project_writeup_context(app)
    base["has_deal_structure"] = app.has_deal_structure
    base["latest_deal_structure_id"] = app.latest_deal_structure_id
    return base


_VALID_INTAKE_VALUES = frozenset(["true"])


@api_view(["GET"])
@permission_classes(_M101_PERMS)
def admin_credit_application_list(request):
    """GET: F&I intake queue (M32.1 read).

    Fail-explicit filter validation per D3:

    - Missing filter param → normal unfiltered behavior.
    - Valid filter value → apply filter.
    - Invalid value → 400 Bad Request with clear message.

    Filter allowlists:
    - ``intake`` — accepts only ``true`` (case-sensitive). Any
      other value (including ``false``, ``1``, ``yes``, ``TRUE``,
      empty) returns 400. When present as ``true``, filters to
      CAs where no downstream Contract exists (pre-contract
      incoming queue).
    - ``lead_id`` — integer; malformed returns 400.
    - ``since`` — ISO-8601 datetime string; malformed returns 400.
    """
    dealership = get_current_dealership(request)

    # D3 fail-explicit `intake` validation.
    intake_raw = request.query_params.get("intake")
    intake = False
    if intake_raw is not None:
        if intake_raw not in _VALID_INTAKE_VALUES:
            return Response(
                {
                    "detail": (
                        f"Invalid value for intake: {intake_raw!r}. "
                        "Expected: true (or omit)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        intake = True

    # D3 fail-explicit `lead_id` validation.
    lead_id_raw = request.query_params.get("lead_id")
    lead: Optional[CustomerLead] = None
    if lead_id_raw is not None:
        try:
            lead_id = int(lead_id_raw)
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": (
                        f"Invalid value for lead_id: {lead_id_raw!r}. "
                        "Expected integer (or omit)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        lead = _lookup_lead_or_404(dealership, lead_id)
        if lead is None:
            return Response(
                {"credit_applications": []}, status=status.HTTP_200_OK
            )

    # D3 fail-explicit `since` validation.
    since_raw = request.query_params.get("since")
    since = None
    if since_raw is not None:
        parsed = parse_datetime(since_raw)
        if parsed is None:
            return Response(
                {
                    "detail": (
                        f"Invalid value for since: {since_raw!r}. "
                        "Expected ISO-8601 datetime (or omit)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        since = parsed

    apps = f_and_i_service.list_credit_applications(
        dealership=dealership, intake=intake, lead=lead, since=since
    )
    return Response(
        {
            "credit_applications": [
                _project_credit_application_with_writeup(a) for a in apps
            ]
        },
        status=status.HTTP_200_OK,
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


# ---------------------------------------------------------------------------
# Milestone 33 · Increment 1 (SESSION_211) — DealStructure read endpoint.
#
# GET /admin/deal-structures/<int:pk>/ — single-row tenant-scoped read.
# Per MILESTONE_33_PLANNING.md §5.b D2. Thin wrapper on the shipped
# M10.2 service verb ``get_deal_structure``; reuses the shipped
# ``_project_deal_structure`` projection verbatim. Read-only —
# activation-vocabulary-asymmetry per M31 lesson w; no PATCH, no
# DELETE. Same permission composition as M10.2 (``_M101_PERMS``).
# Cross-tenant surfaces as 404 (never leak existence).
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes(_M101_PERMS)
def admin_deal_structure_read(request, pk):
    """GET: single DealStructure (M33.1 read).

    Tenant-scoped via shipped
    :func:`services.f_and_i.get_deal_structure`. Returns 404 on
    unknown or cross-tenant pk (never leaks — matches
    M9.1 / M10.1 / M10.2 fail-closed shape).

    Read-only. No PATCH, no DELETE — activation-vocabulary-
    asymmetry per M31 lesson w. Iteration UX (creating a second
    structure for a CA already In progress) explicitly deferred
    per ``MILESTONE_33_PLANNING.md`` §5.h.

    Response shape matches :func:`_project_deal_structure` verbatim
    — 13 stored fields + three nullable ratios + timestamps. Ratios
    surface as stringified Decimals when populated, ``null`` when
    NULL (M10.1-era CA without income captured).
    """
    dealership = get_current_dealership(request)
    deal = f_and_i_service.get_deal_structure(pk, dealership=dealership)
    if deal is None:
        return Response(
            {"detail": "Deal structure not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"deal_structure": _project_deal_structure(deal)},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 3 (SESSION_108) — Lender admin endpoints.
# ---------------------------------------------------------------------------
#
# Three endpoints:
#   - POST /admin/lender-programs/         — create catalog entry
#   - POST /admin/lender-submissions/      — record a submission
#   - PATCH /admin/lender-submissions/<pk>/ — update status + terms
#
# All three share the M10.1 permission composition (``_M101_PERMS``).
# Flat URL shape per §1.9.a Option A (established at SESSION_107).


def _lookup_deal_structure_or_404(dealership, deal_structure_id):
    try:
        return DealStructure.objects.filter(dealership=dealership).get(
            pk=deal_structure_id
        )
    except DealStructure.DoesNotExist:
        return None


def _lookup_lender_program_or_404(dealership, lender_program_id):
    try:
        return LenderProgram.objects.filter(dealership=dealership).get(
            pk=lender_program_id
        )
    except LenderProgram.DoesNotExist:
        return None


def _lookup_lender_submission_or_404(dealership, pk):
    try:
        return LenderSubmission.objects.filter(dealership=dealership).get(pk=pk)
    except LenderSubmission.DoesNotExist:
        return None


def _project_lender_program(program: LenderProgram) -> dict:
    return {
        "id": program.pk,
        "name": program.name,
        "contact": program.contact,
        "terms_summary": program.terms_summary,
        "is_active": program.is_active,
        "created_at": program.created_at.isoformat(),
        "updated_at": program.updated_at.isoformat(),
    }


def _project_lender_submission(submission: LenderSubmission) -> dict:
    return {
        "id": submission.pk,
        "deal_structure_id": submission.deal_structure_id,
        "lender_program_id": submission.lender_program_id,
        "lender_program_name": submission.lender_program.name,
        "submitted_at": submission.submitted_at.isoformat(),
        "status": submission.status,
        "counter_terms": submission.counter_terms,
        "approval_terms": submission.approval_terms,
        "notes": submission.notes,
        "created_at": submission.created_at.isoformat(),
        "updated_at": submission.updated_at.isoformat(),
    }


class LenderProgramCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/lender-programs/``."""

    name = serializers.CharField(max_length=255)
    contact = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
    terms_summary = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    is_active = serializers.BooleanField(required=False, default=True)


class LenderSubmissionCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/lender-submissions/``."""

    deal_structure_id = serializers.IntegerField()
    lender_program_id = serializers.IntegerField()
    submitted_at = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=[key for key, _ in LENDER_SUBMISSION_STATUS_CHOICES],
        required=False,
    )
    counter_terms = serializers.DictField(required=False, default=dict)
    approval_terms = serializers.DictField(required=False, default=dict)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class LenderSubmissionUpdateRequestSerializer(serializers.Serializer):
    """Request shape for ``PATCH /admin/lender-submissions/<pk>/``.

    ``status`` is required (the PATCH always changes status; terms
    / notes are optional).
    """

    status = serializers.ChoiceField(
        choices=[key for key, _ in LENDER_SUBMISSION_STATUS_CHOICES]
    )
    counter_terms = serializers.DictField(required=False)
    approval_terms = serializers.DictField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_lender_program_create(request):
    """POST: create a LenderProgram (M10.3 catalog surface).

    Duplicate ``(dealership, name)`` surfaces as 409 Conflict via
    :class:`DuplicateLenderProgramError` — matches the M9.1
    :class:`SaleAlreadyExistsError` → 409 pattern.
    """
    dealership = get_current_dealership(request)

    serializer = LenderProgramCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        program = f_and_i_service.record_lender_program(
            dealership=dealership,
            name=data["name"],
            contact=data.get("contact", ""),
            terms_summary=data.get("terms_summary", ""),
            is_active=data.get("is_active", True),
        )
    except DuplicateLenderProgramError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {"lender_program": _project_lender_program(program)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_lender_submission_create(request):
    """POST: create a LenderSubmission (M10.3 submission surface).

    Cross-tenant deal_structure or lender_program surfaces as 404,
    same fail-closed shape as M9.1 / M10.1 / M10.2.
    """
    dealership = get_current_dealership(request)

    serializer = LenderSubmissionCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    deal_structure = _lookup_deal_structure_or_404(
        dealership, data["deal_structure_id"]
    )
    if deal_structure is None:
        return Response(
            {"detail": "Deal structure not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    lender_program = _lookup_lender_program_or_404(
        dealership, data["lender_program_id"]
    )
    if lender_program is None:
        return Response(
            {"detail": "Lender program not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    service_kwargs = dict(
        dealership=dealership,
        deal_structure=deal_structure,
        lender_program=lender_program,
        counter_terms=data.get("counter_terms") or {},
        approval_terms=data.get("approval_terms") or {},
        notes=data.get("notes", ""),
    )
    if "status" in data:
        service_kwargs["status"] = data["status"]
    if data.get("submitted_at") is not None:
        service_kwargs["submitted_at"] = data["submitted_at"]

    try:
        submission = f_and_i_service.record_lender_submission(**service_kwargs)
    except CrossTenantLenderSubmissionError:
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
        {"lender_submission": _project_lender_submission(submission)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes(_M101_PERMS)
def admin_lender_submission_update(request, pk):
    """PATCH: update a LenderSubmission status (+ optional terms /
    notes).

    Cross-tenant pk surfaces as 404. Unknown status → 400.
    """
    dealership = get_current_dealership(request)

    submission = _lookup_lender_submission_or_404(dealership, pk)
    if submission is None:
        return Response(
            {"detail": "Lender submission not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = LenderSubmissionUpdateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    update_kwargs = dict(new_status=data["status"])
    if "counter_terms" in data:
        update_kwargs["counter_terms"] = data["counter_terms"]
    if "approval_terms" in data:
        update_kwargs["approval_terms"] = data["approval_terms"]
    if "notes" in data:
        update_kwargs["notes"] = data["notes"]

    try:
        submission = f_and_i_service.update_lender_submission_status(
            submission, **update_kwargs
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"lender_submission": _project_lender_submission(submission)},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 4 (SESSION_109) — Stipulation admin endpoints.
# ---------------------------------------------------------------------------
#
# Two endpoints:
#   - POST /admin/stipulations/         — create (state=open)
#   - PATCH /admin/stipulations/<pk>/   — update state + docs
#
# Same permission composition + flat URL pattern as M10.1-M10.3.


def _lookup_stipulation_or_404(dealership, pk):
    try:
        return Stipulation.objects.filter(dealership=dealership).get(pk=pk)
    except Stipulation.DoesNotExist:
        return None


def _lookup_lender_submission_by_pk_or_404(dealership, submission_id):
    try:
        return LenderSubmission.objects.filter(dealership=dealership).get(
            pk=submission_id
        )
    except LenderSubmission.DoesNotExist:
        return None


def _project_stipulation(stip: Stipulation) -> dict:
    return {
        "id": stip.pk,
        "lender_submission_id": stip.lender_submission_id,
        "stip_type": stip.stip_type,
        "state": stip.state,
        "documented_by_id": stip.documented_by_id,
        "cleared_at": (
            stip.cleared_at.isoformat() if stip.cleared_at is not None else None
        ),
        "notes": stip.notes,
        "created_at": stip.created_at.isoformat(),
        "updated_at": stip.updated_at.isoformat(),
    }


class StipulationCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/stipulations/``."""

    lender_submission_id = serializers.IntegerField()
    stip_type = serializers.ChoiceField(
        choices=[key for key, _ in STIPULATION_TYPE_CHOICES]
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class StipulationUpdateRequestSerializer(serializers.Serializer):
    """Request shape for ``PATCH /admin/stipulations/<pk>/``.

    ``state`` is required — the PATCH always transitions state.
    Notes optional. ``documented_by`` is inferred from the
    authenticated ``request.user`` at the view layer (not passed
    in the request body).
    """

    state = serializers.ChoiceField(
        choices=[key for key, _ in STIPULATION_STATE_CHOICES]
    )
    notes = serializers.CharField(required=False, allow_blank=True)


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_stipulation_create(request):
    """POST: create a Stipulation (initial state ``open``).

    Cross-tenant lender_submission surfaces as 404. Unknown
    stip_type → 400.
    """
    dealership = get_current_dealership(request)

    serializer = StipulationCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    submission = _lookup_lender_submission_by_pk_or_404(
        dealership, data["lender_submission_id"]
    )
    if submission is None:
        return Response(
            {"detail": "Lender submission not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        stip = f_and_i_service.record_stipulation(
            dealership=dealership,
            lender_submission=submission,
            stip_type=data["stip_type"],
            notes=data.get("notes", ""),
        )
    except CrossTenantStipulationError:
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
        {"stipulation": _project_stipulation(stip)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes(_M101_PERMS)
def admin_stipulation_update(request, pk):
    """PATCH: update stipulation state (+ optional notes).

    ``documented_by`` is populated from ``request.user`` — the
    F&I manager clearing the stip is captured for audit trail.
    Unknown / cross-tenant pk → 404. Unknown state → 400.
    """
    dealership = get_current_dealership(request)

    stip = _lookup_stipulation_or_404(dealership, pk)
    if stip is None:
        return Response(
            {"detail": "Stipulation not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = StipulationUpdateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # ``documented_by`` sourced from the authenticated user — the
    # F&I manager clearing the stip is the natural audit-trail
    # attribution. On a back-transition to ``open`` we still pass
    # request.user so the FK stays populated (the previous
    # documenter is preserved as historical record via the
    # service layer's None-vs-omitted distinction — passing an
    # explicit user always sets, never clears).
    update_kwargs = dict(
        new_state=data["state"],
        documented_by=request.user,
    )
    if "notes" in data:
        update_kwargs["notes"] = data["notes"]

    try:
        stip = f_and_i_service.update_stipulation_state(stip, **update_kwargs)
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"stipulation": _project_stipulation(stip)},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 5 (SESSION_110) — Contract + BEPA + Funding.
# ---------------------------------------------------------------------------
#
# Five endpoints:
#   - POST /admin/contracts/           — create (state=unsigned)
#   - PATCH /admin/contracts/<pk>/     — sign OR void via ``action`` field
#   - POST /admin/back-end-products/   — attach product to contract
#   - POST /admin/funding/             — create funding (state=pending)
#   - PATCH /admin/funding/<pk>/       — mark_funded (transitions + amount)


def _lookup_contract_or_404(dealership, pk):
    try:
        return Contract.objects.filter(dealership=dealership).get(pk=pk)
    except Contract.DoesNotExist:
        return None


def _lookup_funding_or_404(dealership, pk):
    try:
        return Funding.objects.filter(dealership=dealership).get(pk=pk)
    except Funding.DoesNotExist:
        return None


def _project_contract(contract: Contract) -> dict:
    return {
        "id": contract.pk,
        "deal_structure_id": contract.deal_structure_id,
        "contract_type": contract.contract_type,
        "state": contract.state,
        "signer_name": contract.signer_name,
        "signed_at": (
            contract.signed_at.isoformat()
            if contract.signed_at is not None
            else None
        ),
        "financed_amount": str(contract.financed_amount),
        "total_of_payments": str(contract.total_of_payments),
        "finance_charge": str(contract.finance_charge),
        "apr_disclosure": str(contract.apr_disclosure),
        "first_payment_date": (
            contract.first_payment_date.isoformat()
            if contract.first_payment_date is not None
            else None
        ),
        "voided_at": (
            contract.voided_at.isoformat()
            if contract.voided_at is not None
            else None
        ),
        "voided_reason": contract.voided_reason,
        "notes": contract.notes,
        "created_at": contract.created_at.isoformat(),
        "updated_at": contract.updated_at.isoformat(),
    }


def _project_back_end_product(bepa: BackEndProductAgreement) -> dict:
    return {
        "id": bepa.pk,
        "contract_id": bepa.contract_id,
        "product_type": bepa.product_type,
        "provider": bepa.provider,
        "cost": str(bepa.cost),
        "retail_price": str(bepa.retail_price),
        "term_months": bepa.term_months,
        "mileage_limit": bepa.mileage_limit,
        "deductible": (
            str(bepa.deductible) if bepa.deductible is not None else None
        ),
        "notes": bepa.notes,
        "created_at": bepa.created_at.isoformat(),
        "updated_at": bepa.updated_at.isoformat(),
    }


def _project_funding(funding: Funding) -> dict:
    return {
        "id": funding.pk,
        "contract_id": funding.contract_id,
        "state": funding.state,
        "submitted_to_lender_at": (
            funding.submitted_to_lender_at.isoformat()
            if funding.submitted_to_lender_at is not None
            else None
        ),
        "funded_at": (
            funding.funded_at.isoformat()
            if funding.funded_at is not None
            else None
        ),
        "funding_amount": (
            str(funding.funding_amount)
            if funding.funding_amount is not None
            else None
        ),
        "notes": funding.notes,
        "created_at": funding.created_at.isoformat(),
        "updated_at": funding.updated_at.isoformat(),
    }


class ContractCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/contracts/``."""

    deal_structure_id = serializers.IntegerField()
    contract_type = serializers.ChoiceField(
        choices=[key for key, _ in CONTRACT_TYPE_CHOICES]
    )
    signer_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
    financed_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    total_of_payments = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    finance_charge = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default="0.00"
    )
    apr_disclosure = serializers.DecimalField(
        max_digits=6, decimal_places=4, required=False, default="0.0000"
    )
    first_payment_date = serializers.DateField(
        required=False, allow_null=True
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class ContractUpdateRequestSerializer(serializers.Serializer):
    """Request shape for ``PATCH /admin/contracts/<pk>/``.

    ``action`` selects the transition — ``sign`` or ``void``.
    Distinct action verbs rather than a generic state updater
    to mirror the service-layer :func:`sign_contract` /
    :func:`void_contract` split.
    """

    action = serializers.ChoiceField(choices=("sign", "void"))
    signer_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    voided_reason = serializers.CharField(
        required=False, allow_blank=True
    )


class BackEndProductCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/back-end-products/``."""

    contract_id = serializers.IntegerField()
    product_type = serializers.ChoiceField(
        choices=[key for key, _ in BEPA_TYPE_CHOICES]
    )
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    retail_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    provider = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
    term_months = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    mileage_limit = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    deductible = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class FundingCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/funding/``."""

    contract_id = serializers.IntegerField()
    submitted_to_lender_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class FundingUpdateRequestSerializer(serializers.Serializer):
    """Request shape for ``PATCH /admin/funding/<pk>/`` — mark funded.

    Only supports the mark-funded transition at M10.5 (M10.6 will
    add a chargedback transition).
    """

    action = serializers.ChoiceField(choices=("mark_funded",))
    funding_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    funded_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_contract_create(request):
    """POST: create a Contract (initial state ``unsigned``).

    Cross-tenant deal_structure → 404. Unknown contract_type → 400.
    """
    dealership = get_current_dealership(request)

    serializer = ContractCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    deal_structure = _lookup_deal_structure_or_404(
        dealership, data["deal_structure_id"]
    )
    if deal_structure is None:
        return Response(
            {"detail": "Deal structure not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        contract = f_and_i_service.record_contract(
            dealership=dealership,
            deal_structure=deal_structure,
            contract_type=data["contract_type"],
            signer_name=data.get("signer_name", ""),
            financed_amount=data.get("financed_amount"),
            total_of_payments=data.get("total_of_payments"),
            finance_charge=data.get("finance_charge"),
            apr_disclosure=data.get("apr_disclosure"),
            first_payment_date=data.get("first_payment_date"),
            notes=data.get("notes", ""),
        )
    except CrossTenantContractError:
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
        {"contract": _project_contract(contract)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes(_M101_PERMS)
def admin_contract_update(request, pk):
    """PATCH: sign or void a Contract.

    ``action=sign`` transitions to signed + auto-populates
    ``signed_at``. ``action=void`` transitions to voided +
    auto-populates ``voided_at`` + records
    ``voided_reason``. Signing an already-voided contract →
    409 Conflict per
    :class:`ContractAlreadyVoidedError`.
    """
    dealership = get_current_dealership(request)

    contract = _lookup_contract_or_404(dealership, pk)
    if contract is None:
        return Response(
            {"detail": "Contract not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ContractUpdateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        if data["action"] == "sign":
            contract = f_and_i_service.sign_contract(
                contract,
                signer_name=data.get("signer_name"),
            )
        else:  # action == "void"
            contract = f_and_i_service.void_contract(
                contract,
                voided_reason=data.get("voided_reason", ""),
            )
    except ContractAlreadyVoidedError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"contract": _project_contract(contract)},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_back_end_product_create(request):
    """POST: attach a BackEndProductAgreement to a Contract.

    Cross-tenant contract → 404. Unknown product_type → 400.
    """
    dealership = get_current_dealership(request)

    serializer = BackEndProductCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    contract = _lookup_contract_or_404(dealership, data["contract_id"])
    if contract is None:
        return Response(
            {"detail": "Contract not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        bepa = f_and_i_service.record_back_end_product(
            dealership=dealership,
            contract=contract,
            product_type=data["product_type"],
            cost=data["cost"],
            retail_price=data["retail_price"],
            provider=data.get("provider", ""),
            term_months=data.get("term_months"),
            mileage_limit=data.get("mileage_limit"),
            deductible=data.get("deductible"),
            notes=data.get("notes", ""),
        )
    except CrossTenantContractError:
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
        {"back_end_product": _project_back_end_product(bepa)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_funding_create(request):
    """POST: create a Funding row for a Contract (initial state
    ``pending_funding``).

    Cross-tenant contract → 404. Duplicate Funding for the same
    contract → 409 Conflict per
    :class:`FundingAlreadyExistsError`.
    """
    dealership = get_current_dealership(request)

    serializer = FundingCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    contract = _lookup_contract_or_404(dealership, data["contract_id"])
    if contract is None:
        return Response(
            {"detail": "Contract not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        funding = f_and_i_service.record_funding(
            dealership=dealership,
            contract=contract,
            submitted_to_lender_at=data.get("submitted_to_lender_at"),
            notes=data.get("notes", ""),
        )
    except CrossTenantFundingError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except FundingAlreadyExistsError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {"funding": _project_funding(funding)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes(_M101_PERMS)
def admin_funding_update(request, pk):
    """PATCH: mark_funded (only transition supported at M10.5).

    Requires ``funding_amount`` in the body. Unknown /
    cross-tenant pk → 404.
    """
    dealership = get_current_dealership(request)

    funding = _lookup_funding_or_404(dealership, pk)
    if funding is None:
        return Response(
            {"detail": "Funding not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = FundingUpdateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        funding = f_and_i_service.mark_funded(
            funding,
            funding_amount=data["funding_amount"],
            funded_at=data.get("funded_at"),
            notes=data.get("notes"),
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"funding": _project_funding(funding)},
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 6 (SESSION_111) — Chargeback admin endpoint.
# ---------------------------------------------------------------------------
#
# One endpoint:
#   - POST /admin/chargebacks/  — record chargeback (with atomic
#                                 side effects: Funding auto-transition
#                                 for deal-level types, BEPA
#                                 cancellation-field auto-populate for
#                                 product-cancellation type)
#
# ``recorded_by`` sourced from ``request.user`` server-side per the
# M10.4 audit-trail pattern — the endpoint doesn't accept it in
# the request body.


def _project_chargeback(chargeback: Chargeback) -> dict:
    return {
        "id": chargeback.pk,
        "contract_id": chargeback.contract_id,
        "bepa_id": chargeback.bepa_id,
        "chargeback_type": chargeback.chargeback_type,
        "chargeback_date": chargeback.chargeback_date.isoformat(),
        "chargeback_amount": str(chargeback.chargeback_amount),
        "recorded_by_id": chargeback.recorded_by_id,
        "notes": chargeback.notes,
        "created_at": chargeback.created_at.isoformat(),
        "updated_at": chargeback.updated_at.isoformat(),
    }


class ChargebackCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/chargebacks/``.

    Requires at least one of ``contract_id`` or ``bepa_id`` per
    §1.7.a Option A. Validation-time check in the view (the
    serializer accepts both nullable to allow either).
    """

    chargeback_type = serializers.ChoiceField(
        choices=[key for key, _ in CHARGEBACK_TYPE_CHOICES]
    )
    chargeback_date = serializers.DateField()
    chargeback_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    contract_id = serializers.IntegerField(required=False, allow_null=True)
    bepa_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    skip_funding_transition = serializers.BooleanField(
        required=False, default=False
    )


def _lookup_bepa_or_404(dealership, pk):
    try:
        return BackEndProductAgreement.objects.filter(
            dealership=dealership
        ).get(pk=pk)
    except BackEndProductAgreement.DoesNotExist:
        return None


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_chargeback_create(request):
    """POST: record a Chargeback with atomic side effects.

    Requires at least one of ``contract_id`` or ``bepa_id``.
    Cross-tenant contract / bepa → 404 (never leak). Unknown
    chargeback_type → 400. Missing both parent IDs → 400.

    Two atomic side effects (per §1.7.f + §1.7.c):

    1. Deal-level chargebacks (FPD / early_payoff / repossession
       / deal_unwind) auto-transition the resolved Contract's
       Funding to ``chargedback``. Bypass with
       ``skip_funding_transition=True``.
    2. ``product_cancellation`` chargebacks with ``bepa_id``
       auto-populate the BEPA's ``cancelled_at`` +
       ``cancellation_amount`` columns.

    ``recorded_by`` is sourced from ``request.user`` server-
    side per the M10.4 audit-trail pattern.
    """
    dealership = get_current_dealership(request)

    serializer = ChargebackCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    if data.get("contract_id") is None and data.get("bepa_id") is None:
        return Response(
            {
                "detail": (
                    "At least one of contract_id or bepa_id is required."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    contract = None
    if data.get("contract_id") is not None:
        contract = _lookup_contract_or_404(dealership, data["contract_id"])
        if contract is None:
            return Response(
                {"detail": "Contract not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    bepa = None
    if data.get("bepa_id") is not None:
        bepa = _lookup_bepa_or_404(dealership, data["bepa_id"])
        if bepa is None:
            return Response(
                {"detail": "Back-end product agreement not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    try:
        chargeback = f_and_i_service.record_chargeback(
            dealership=dealership,
            chargeback_type=data["chargeback_type"],
            chargeback_date=data["chargeback_date"],
            chargeback_amount=data["chargeback_amount"],
            contract=contract,
            bepa=bepa,
            recorded_by=request.user,
            notes=data.get("notes", ""),
            skip_funding_transition=data.get(
                "skip_funding_transition", False
            ),
        )
    except CrossTenantChargebackError:
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
        {"chargeback": _project_chargeback(chargeback)},
        status=status.HTTP_201_CREATED,
    )


# ---------------------------------------------------------------------------
# Milestone 10 · Increment 7 (SESSION_112) — Compliance + deal-jacket API.
# ---------------------------------------------------------------------------
#
# Four endpoints:
#   - GET  /admin/f-and-i/deals/             — deals-in-progress list (M10.7 UI tab 1)
#   - POST /admin/compliance-records/        — create (OneToOne per contract)
#   - PATCH /admin/compliance-records/<pk>/  — update any typed columns
#   - GET  /admin/deal-jackets/<int:contract_pk>/  — aggregated compliance-audit view
#
# `/dealer-ai-f-and-i/` frontend consumes these four.


def _lookup_compliance_or_404(dealership, pk):
    try:
        return ComplianceRecord.objects.filter(dealership=dealership).get(pk=pk)
    except ComplianceRecord.DoesNotExist:
        return None


def _project_compliance(compliance: ComplianceRecord) -> dict:
    def _iso(dt_value):
        return dt_value.isoformat() if dt_value is not None else None

    return {
        "id": compliance.pk,
        "contract_id": compliance.contract_id,
        "reg_z_disclosed_at": _iso(compliance.reg_z_disclosed_at),
        "ofac_checked_at": _iso(compliance.ofac_checked_at),
        "ofac_hit": compliance.ofac_hit,
        "red_flags_reviewed_at": _iso(compliance.red_flags_reviewed_at),
        "red_flags_notes": compliance.red_flags_notes,
        "privacy_notice_delivered_at": _iso(
            compliance.privacy_notice_delivered_at
        ),
        "safeguards_audit_at": _iso(compliance.safeguards_audit_at),
        "adverse_action_sent_at": _iso(compliance.adverse_action_sent_at),
        "adverse_action_reason": compliance.adverse_action_reason,
        "retention_expires_at": _iso(compliance.retention_expires_at),
        "deal_jacket_url": compliance.deal_jacket_url,
        "notes": compliance.notes,
        "created_at": compliance.created_at.isoformat(),
        "updated_at": compliance.updated_at.isoformat(),
    }


class ComplianceCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/compliance-records/``."""

    contract_id = serializers.IntegerField()
    deal_jacket_url = serializers.URLField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class ComplianceUpdateRequestSerializer(serializers.Serializer):
    """Request shape for ``PATCH /admin/compliance-records/<pk>/``.

    Every field optional — the operator PATCHes just the columns
    they're updating. Unspecified fields are preserved.
    """

    reg_z_disclosed_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    ofac_checked_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    ofac_hit = serializers.BooleanField(required=False)
    red_flags_reviewed_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    red_flags_notes = serializers.CharField(
        required=False, allow_blank=True
    )
    privacy_notice_delivered_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    safeguards_audit_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    adverse_action_sent_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    adverse_action_reason = serializers.CharField(
        required=False, allow_blank=True
    )
    deal_jacket_url = serializers.URLField(
        required=False, allow_blank=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


@api_view(["POST"])
@permission_classes(_M101_PERMS)
def admin_compliance_create(request):
    """POST: create a ComplianceRecord for a contract.

    Duplicate (contract already has a ComplianceRecord via
    OneToOne) → 409 Conflict per
    :class:`ComplianceAlreadyExistsError`. Cross-tenant
    contract → 404 (never leak).
    """
    dealership = get_current_dealership(request)

    serializer = ComplianceCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    contract = _lookup_contract_or_404(dealership, data["contract_id"])
    if contract is None:
        return Response(
            {"detail": "Contract not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        compliance = f_and_i_service.record_compliance(
            dealership=dealership,
            contract=contract,
            deal_jacket_url=data.get("deal_jacket_url", ""),
            notes=data.get("notes", ""),
        )
    except CrossTenantComplianceError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ComplianceAlreadyExistsError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(
        {"compliance": _project_compliance(compliance)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes(_M101_PERMS)
def admin_compliance_update(request, pk):
    """PATCH: update any subset of compliance columns.

    Unknown / cross-tenant pk → 404. Unknown field → 400 via
    the service verb's field-whitelist enforcement.
    """
    dealership = get_current_dealership(request)

    compliance = _lookup_compliance_or_404(dealership, pk)
    if compliance is None:
        return Response(
            {"detail": "Compliance record not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ComplianceUpdateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    # Only pass fields the client actually supplied — the
    # service verb preserves unspecified fields.
    field_kwargs = {
        name: value
        for name, value in serializer.validated_data.items()
    }

    try:
        compliance = f_and_i_service.update_compliance(
            compliance, **field_kwargs
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"compliance": _project_compliance(compliance)},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes(_M101_PERMS)
def admin_deal_jacket_read(request, contract_pk):
    """GET: aggregated deal-jacket summary for a contract.

    Powers the operator UI's per-deal compliance-audit view.
    Cross-tenant contract → 404.
    """
    dealership = get_current_dealership(request)

    contract = _lookup_contract_or_404(dealership, contract_pk)
    if contract is None:
        return Response(
            {"detail": "Contract not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    summary = f_and_i_service.deal_jacket_summary(contract)
    return Response({"deal_jacket": summary})


@api_view(["GET"])
@permission_classes(_M101_PERMS)
def admin_f_and_i_deals_list(request):
    """GET: deals-in-progress list for the F&I operator dashboard.

    Returns contracts scoped to the caller's dealership with a
    projection suitable for the deals list view. Supports basic
    filtering via query params:

    - ``state`` — Contract.state (unsigned / signed / voided).
    - ``funding_state`` — Funding.state (pending_funding / funded / chargedback).
    - ``has_chargebacks`` — "true" filters to contracts with
      at least one Chargeback.

    Ordering is ``-created_at``. No pagination at M10.7 — the
    operator UI paginates client-side. Add server-side
    pagination in M11+ if operator evidence surfaces need.
    """
    dealership = get_current_dealership(request)

    qs = Contract.objects.filter(dealership=dealership).select_related(
        "deal_structure__vehicle", "funding"
    )

    state_filter = request.query_params.get("state")
    if state_filter:
        qs = qs.filter(state=state_filter)

    funding_filter = request.query_params.get("funding_state")
    if funding_filter:
        qs = qs.filter(funding__state=funding_filter)

    has_chargebacks = request.query_params.get("has_chargebacks", "").lower()
    if has_chargebacks == "true":
        qs = qs.filter(chargebacks__isnull=False).distinct()

    deals = []
    for contract in qs.order_by("-created_at")[:100]:
        funding = getattr(contract, "funding", None)
        deals.append(
            {
                "contract_id": contract.pk,
                "contract_state": contract.state,
                "contract_type": contract.contract_type,
                "signed_at": (
                    contract.signed_at.isoformat()
                    if contract.signed_at is not None
                    else None
                ),
                "voided_at": (
                    contract.voided_at.isoformat()
                    if contract.voided_at is not None
                    else None
                ),
                "vehicle_stock": contract.deal_structure.vehicle.stock_number,
                "funding_state": funding.state if funding is not None else None,
                "funding_amount": (
                    str(funding.funding_amount)
                    if funding is not None
                    and funding.funding_amount is not None
                    else None
                ),
                "chargeback_count": contract.chargebacks.count(),
            }
        )

    return Response({"deals": deals})
