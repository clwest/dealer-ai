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
    LENDER_SUBMISSION_STATUS_CHOICES,
    STIPULATION_STATE_CHOICES,
    STIPULATION_TYPE_CHOICES,
    CreditApplication,
    CustomerLead,
    DealStructure,
    LenderProgram,
    LenderSubmission,
    Sale,
    Stipulation,
    Vehicle,
)
from .permissions import IsFinanceManagerOrOwnerAtActiveDealership
from .services import f_and_i as f_and_i_service
from .services.f_and_i import (
    CrossTenantCreditApplicationError,
    CrossTenantDealStructureError,
    CrossTenantLenderSubmissionError,
    CrossTenantStipulationError,
    DuplicateLenderProgramError,
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
