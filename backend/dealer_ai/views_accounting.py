"""Milestone 13 · Increment 1 (SESSION_129) — accounting endpoints.

Three endpoints per ``MILESTONE_13_PLANNING.md`` §7 M13.1:

- ``POST /admin/accounting/journal-entries/`` — post a balanced
  JournalEntry.
- ``POST /admin/accounting/journal-entries/<pk>/reverse/`` —
  post the reversal.
- ``GET  /admin/accounting/journal-entries/<pk>/`` — retrieve.

Gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``
per M12 posture continuity (permission-class count stays at 8, zero
drift — the M12 retrospective §6 lesson tracked this discipline).

Domain-error → HTTP mapping (asserted in
``tests/test_m131_accounting_endpoint.py``):

- :class:`EmptyJournalEntryError` → 400.
- :class:`InvalidJournalLineError` → 400.
- :class:`UnbalancedJournalEntryError` → 400.
- :class:`CrossTenantGLAccountError` → 404 (fail-closed).
- :class:`CrossTenantJournalEntryError` → 404 (fail-closed).
- :class:`ImmutableJournalEntryError` → 409 (empty-reason reversal).
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    GLAccount,
    JournalEntry,
    JournalEntryTemplate,
    TrialBalanceSnapshot,
    TrialBalanceSnapshotRow,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.accounting import (
    CrossTenantGLAccountError,
    CrossTenantJournalEntryError,
    DuplicateJournalEntryTemplateNameError,
    DuplicateTrialBalanceSnapshotError,
    EmptyJournalEntryError,
    EmptyJournalEntryTemplateError,
    ImmutableJournalEntryError,
    InvalidJournalLineError,
    InvalidJournalEntryTemplateLineError,
    JournalLineInput,
    TemplateLineInput,
    TrialBalanceComputation,
    UnbalancedJournalEntryError,
    UnbalancedJournalEntryTemplateError,
    compute_trial_balance,
    create_journal_entry_template,
    detect_cost_posting_failures,
    freeze_trial_balance,
    get_journal_entry,
    get_journal_entry_template,
    get_trial_balance_snapshot,
    list_journal_entries,
    list_journal_entry_templates,
    list_trial_balance_snapshots,
    post_journal_entry,
    reverse_journal_entry,
)
from .services.tenancy import get_current_dealership


_M131_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


class JournalLineSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    debit = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
    )
    credit = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
    )
    memo = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class JournalEntryCreateRequestSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=500)
    posted_at = serializers.DateTimeField(required=False, allow_null=True)
    lines = JournalLineSerializer(many=True)


class JournalEntryReverseRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)
    posted_at = serializers.DateTimeField(required=False, allow_null=True)


def _project_line(line) -> dict:
    return {
        "id": line.pk,
        "account_id": line.account_id,
        "account_code": line.account.code,
        "debit": str(line.debit),
        "credit": str(line.credit),
        "memo": line.memo,
    }


def _project_entry(entry: JournalEntry) -> dict:
    return {
        "id": entry.pk,
        "dealership_id": entry.dealership_id,
        "description": entry.description,
        "posted_at": entry.posted_at.isoformat(),
        "posted_by_user_id": entry.posted_by_user_id,
        "reverses_id": entry.reverses_id,
        "reason": entry.reason,
        "created_at": entry.created_at.isoformat(),
        "lines": [_project_line(line) for line in entry.lines.all()],
    }


def _resolve_lines(dealership, raw_lines):
    """Map serialized line dicts → :class:`JournalLineInput` instances.

    Fails-closed on any missing / cross-tenant account by raising the
    service-layer :class:`CrossTenantGLAccountError` (the endpoint
    handler maps to 404 without confirming existence).
    """
    resolved: list[JournalLineInput] = []
    account_ids = [raw["account_id"] for raw in raw_lines]
    accounts_by_id = {
        acct.pk: acct
        for acct in GLAccount.objects.filter(
            dealership=dealership, pk__in=account_ids
        )
    }
    for raw in raw_lines:
        account = accounts_by_id.get(raw["account_id"])
        if account is None:
            raise CrossTenantGLAccountError(
                f"GLAccount {raw['account_id']} not found in tenant."
            )
        resolved.append(
            JournalLineInput(
                account=account,
                debit=raw.get("debit", Decimal("0.00")),
                credit=raw.get("credit", Decimal("0.00")),
                memo=raw.get("memo", ""),
            )
        )
    return resolved


@api_view(["POST"])
@permission_classes(_M131_PERMS)
def admin_journal_entry_create(request):
    dealership = get_current_dealership(request)
    serializer = JournalEntryCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        lines = _resolve_lines(dealership, data["lines"])
    except CrossTenantGLAccountError:
        return Response(
            {"detail": "GLAccount not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except (InvalidOperation, KeyError):
        return Response(
            {"detail": "Invalid line payload."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        entry = post_journal_entry(
            dealership=dealership,
            description=data["description"],
            lines=lines,
            posted_at=data.get("posted_at"),
            posted_by_user=(
                request.user if request.user.is_authenticated else None
            ),
        )
    except (
        EmptyJournalEntryError,
        InvalidJournalLineError,
        UnbalancedJournalEntryError,
    ) as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except CrossTenantGLAccountError:
        return Response(
            {"detail": "GLAccount not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"journal_entry": _project_entry(entry)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M131_PERMS)
def admin_journal_entry_reverse(request, pk: int):
    dealership = get_current_dealership(request)
    entry = get_journal_entry(pk=pk, dealership=dealership)
    if entry is None:
        return Response(
            {"detail": "JournalEntry not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = JournalEntryReverseRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        reversal = reverse_journal_entry(
            dealership=dealership,
            entry=entry,
            reason=serializer.validated_data["reason"],
            posted_at=serializer.validated_data.get("posted_at"),
            posted_by_user=(
                request.user if request.user.is_authenticated else None
            ),
        )
    except CrossTenantJournalEntryError:
        return Response(
            {"detail": "JournalEntry not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except ImmutableJournalEntryError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    return Response(
        {"journal_entry": _project_entry(reversal)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_journal_entry_retrieve(request, pk: int):
    dealership = get_current_dealership(request)
    entry = get_journal_entry(pk=pk, dealership=dealership)
    if entry is None:
        return Response(
            {"detail": "JournalEntry not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"journal_entry": _project_entry(entry)},
        status=status.HTTP_200_OK,
    )


# --- Milestone 13 · Increment 3 (SESSION_131) — trial-balance snapshot -------


class TrialBalanceQuerySerializer(serializers.Serializer):
    as_of = serializers.DateTimeField(required=False, allow_null=True)


def _project_trial_balance(snapshot: TrialBalanceComputation) -> dict:
    return {
        "dealership_id": snapshot.dealership_id,
        "dealership_slug": snapshot.dealership_slug,
        "as_of": snapshot.as_of.isoformat(),
        "total_debits": str(snapshot.total_debits),
        "total_credits": str(snapshot.total_credits),
        "is_balanced": snapshot.is_balanced,
        "rows": [
            {
                "account_code": row.account_code,
                "account_name": row.account_name,
                "account_type": row.account_type,
                "debit_total": str(row.debit_total),
                "credit_total": str(row.credit_total),
                "natural_balance": str(row.natural_balance),
            }
            for row in snapshot.rows
        ],
    }


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_trial_balance(request):
    """GET /admin/accounting/trial-balance/[?as_of=<ISO8601>]

    Returns the tenant's trial-balance snapshot at ``as_of`` (default
    now). Empty balanced snapshot for a fresh dealership with no
    postings per §0.a M13.3 decision 5 zero-portfolio semantics.
    Reuses ``IsSalesManagerOrOwnerAtActiveDealership`` per §0.a
    M13.3 decision 3 zero-drift posture.
    """
    dealership = get_current_dealership(request)
    query = TrialBalanceQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    snapshot = compute_trial_balance(
        dealership=dealership,
        as_of=query.validated_data.get("as_of"),
    )
    return Response(
        {"trial_balance": _project_trial_balance(snapshot)},
        status=status.HTTP_200_OK,
    )


# --- Milestone 14 · Increment 1 (SESSION_134) — list + failures endpoints ----
#
# Per MILESTONE_14_PLANNING.md §7 M14.1. Two new read-only endpoints
# feeding the M14.2-M14.4 operator UI. Both reuse
# ``IsSalesManagerOrOwnerAtActiveDealership`` (permission-class count
# stays at 8 — zero drift extends to a sixth consecutive milestone).
# Money-on-the-wire is Decimal-as-string per §5.c Option A.


class JournalEntryListQuerySerializer(serializers.Serializer):
    """Query-param validator for the journal-entry list endpoint.

    ``page_size`` capped at 100 to bound worst-case query size.
    """

    page = serializers.IntegerField(
        min_value=1, required=False, default=1
    )
    page_size = serializers.IntegerField(
        min_value=1, max_value=100, required=False, default=25
    )


def _project_list_entry(entry: JournalEntry) -> dict:
    """Compact projection for the list view.

    Omits per-line detail (loaded by the detail retrieve endpoint) but
    includes the ``total_debit`` annotation added by
    :func:`list_journal_entries` so the operator UI can render an
    "amount" column without N+1 line queries.
    """
    return {
        "id": entry.pk,
        "description": entry.description,
        "posted_at": entry.posted_at.isoformat(),
        "posted_by_user_id": entry.posted_by_user_id,
        "posted_by_username": (
            entry.posted_by_user.username
            if entry.posted_by_user_id
            else None
        ),
        "reverses_id": entry.reverses_id,
        "reason": entry.reason,
        # Sum() aggregation drops trailing zeros; quantize to money shape
        # (2dp) so the wire matches every other M13 accounting endpoint
        # per §5.c Option A Decimal-as-string convention.
        "total_debit": str(entry.total_debit.quantize(Decimal("0.01"))),
    }


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_journal_entry_list(request):
    """GET /admin/accounting/journal-entries/list/[?page=&page_size=]

    Paginated, recent-first (``-posted_at, -id``). No filters at
    M14.1 per §5.b Option B — filters land at M15+ per operator
    evidence. Empty-list response for zero-portfolio tenants (not
    404) per M13.3 lesson 8 zero-portfolio semantics.
    """
    dealership = get_current_dealership(request)
    query = JournalEntryListQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    page = list_journal_entries(
        dealership=dealership,
        page=query.validated_data["page"],
        page_size=query.validated_data["page_size"],
    )
    return Response(
        {
            "journal_entries": {
                "entries": [
                    _project_list_entry(e) for e in page.entries
                ],
                "total_count": page.total_count,
                "page": page.page,
                "page_size": page.page_size,
            }
        },
        status=status.HTTP_200_OK,
    )


class CostPostingFailuresQuerySerializer(serializers.Serializer):
    """Query-param validator for the cost-posting-failures endpoint.

    ``threshold_hours`` bounded to 8760 (one year) to avoid runaway
    queries; default 24h matches one M13.2 detector-run boundary
    (the detector runs at 10:00 project-time daily, so a row older
    than 24h that isn't posted has already missed at least one run).
    """

    threshold_hours = serializers.IntegerField(
        min_value=1, max_value=8760, required=False, default=24
    )


def _project_failure(cost, now) -> dict:
    """Projection for one unposted VehicleCost row.

    ``age_in_hours`` is computed at projection time from
    ``now - created_at`` — the endpoint captures ``now`` once so
    every failure in the response uses the same reference moment.
    """
    age_seconds = (now - cost.created_at).total_seconds()
    age_in_hours = int(age_seconds // 3600)
    return {
        "id": cost.pk,
        "vehicle_id": cost.vehicle_id,
        "vehicle_stock": (
            cost.vehicle.stock_number if cost.vehicle_id else None
        ),
        "category": cost.category,
        "category_display": cost.get_category_display(),
        "amount": str(cost.amount),
        "reference": cost.reference,
        "vendor": cost.vendor,
        "incurred_at": cost.incurred_at.isoformat(),
        "created_at": cost.created_at.isoformat(),
        "age_in_hours": age_in_hours,
    }


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_cost_posting_failures(request):
    """GET /admin/accounting/cost-posting-failures/[?threshold_hours=]

    Returns unposted, non-estimate VehicleCost rows older than the
    threshold — costs the M13.2 detector should have posted but
    didn't (typically :class:`MissingDefaultAccountError` or another
    broken invariant surfaced in
    :func:`post_all_unposted_costs_for_dealership` logging). Empty
    list for zero-failure tenants (not 404).
    """
    dealership = get_current_dealership(request)
    query = CostPostingFailuresQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    threshold_hours = query.validated_data["threshold_hours"]
    now = timezone.now()
    failures = list(
        detect_cost_posting_failures(
            dealership=dealership,
            now=now,
            threshold_hours=threshold_hours,
        )
    )
    return Response(
        {
            "cost_posting_failures": {
                "failures": [_project_failure(c, now) for c in failures],
                "count": len(failures),
                "threshold_hours": threshold_hours,
                "as_of": now.isoformat(),
            }
        },
        status=status.HTTP_200_OK,
    )


# --- Milestone 17 · Increment 1 (SESSION_145) — trial-balance snapshots ------
#
# Per MILESTONE_17_PLANNING.md §7 M17.1 + §5.a-§5.f. Three endpoints
# (POST freeze, GET list, GET detail) all reusing
# ``IsSalesManagerOrOwnerAtActiveDealership`` (permission-class count
# stays at 8 — zero-drift streak extends to nine consecutive
# milestones). Money-on-the-wire is Decimal-as-string per M9-M16
# convention.


class TrialBalanceSnapshotCreateRequestSerializer(serializers.Serializer):
    """Body validator for POST /admin/accounting/trial-balance/snapshots/.

    ``as_of`` is required — the operator picker sends the moment they
    want to freeze. No default (unlike the GET trial-balance endpoint,
    which defaults to ``timezone.now()``) — freezing "right now"
    should be an explicit operator choice per §5.c Option A.
    """

    as_of = serializers.DateTimeField(required=True)


class TrialBalanceSnapshotListQuerySerializer(serializers.Serializer):
    """Query-param validator for the snapshot list endpoint.

    Same pagination shape as M14.1 journal-entry list.
    """

    page = serializers.IntegerField(
        min_value=1, required=False, default=1
    )
    page_size = serializers.IntegerField(
        min_value=1, max_value=100, required=False, default=25
    )


def _project_snapshot_summary(snapshot: TrialBalanceSnapshot) -> dict:
    """Compact projection for the list view.

    Omits per-row detail (loaded by the detail retrieve endpoint) but
    includes the balance totals + is_balanced chip so the M17.2 UI
    can render the list without per-row queries.
    """
    return {
        "id": snapshot.pk,
        "as_of": snapshot.as_of.isoformat(),
        "total_debits": str(snapshot.total_debits),
        "total_credits": str(snapshot.total_credits),
        "is_balanced": snapshot.is_balanced,
        "created_at": snapshot.created_at.isoformat(),
        "created_by_user_id": snapshot.created_by_id,
        "created_by_username": (
            snapshot.created_by.username
            if snapshot.created_by_id
            else None
        ),
    }


def _project_snapshot_row(row: TrialBalanceSnapshotRow) -> dict:
    return {
        "account_code": row.account_code,
        "account_name": row.account_name,
        "account_type": row.account_type,
        "debit_total": str(row.debit_total),
        "credit_total": str(row.credit_total),
        "natural_balance": str(row.natural_balance),
    }


def _project_snapshot_detail(snapshot: TrialBalanceSnapshot) -> dict:
    """Full projection for the detail retrieve endpoint.

    Includes frozen per-account rows via the ``rows`` reverse-FK
    manager (ordered by ``account_code`` per
    :class:`TrialBalanceSnapshotRow.Meta.ordering`).
    """
    summary = _project_snapshot_summary(snapshot)
    summary["rows"] = [
        _project_snapshot_row(r) for r in snapshot.rows.all()
    ]
    return summary


@api_view(["POST"])
@permission_classes(_M131_PERMS)
def admin_trial_balance_snapshot_create(request):
    """POST /admin/accounting/trial-balance/snapshots/

    Freeze a durable trial-balance snapshot for the operator's tenant
    at the requested ``as_of``. Sync-sibling verb per §5.c Option A.

    Body: ``{"as_of": "<ISO8601>"}``.

    - 201 with full snapshot projection (header + frozen rows).
    - 400 on missing / invalid ``as_of``.
    - 409 on duplicate ``(dealership, as_of)`` per §5.d Option A.
    - 403 on non-permitted role.
    """
    dealership = get_current_dealership(request)
    body = TrialBalanceSnapshotCreateRequestSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    try:
        snapshot = freeze_trial_balance(
            dealership=dealership,
            as_of=body.validated_data["as_of"],
            actor=request.user if request.user.is_authenticated else None,
        )
    except DuplicateTrialBalanceSnapshotError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(
        {"trial_balance_snapshot": _project_snapshot_detail(snapshot)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_trial_balance_snapshot_list(request):
    """GET /admin/accounting/trial-balance/snapshots/[?page=&page_size=]

    Paginated, recent-first (``-as_of, -created_at``). Empty-list
    response for zero-portfolio tenants (not 404) per M13.3 lesson
    8 zero-portfolio semantics.
    """
    dealership = get_current_dealership(request)
    query = TrialBalanceSnapshotListQuerySerializer(
        data=request.query_params
    )
    query.is_valid(raise_exception=True)
    page = list_trial_balance_snapshots(
        dealership=dealership,
        page=query.validated_data["page"],
        page_size=query.validated_data["page_size"],
    )
    return Response(
        {
            "trial_balance_snapshots": {
                "snapshots": [
                    _project_snapshot_summary(s) for s in page.snapshots
                ],
                "total_count": page.total_count,
                "page": page.page,
                "page_size": page.page_size,
            }
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_trial_balance_snapshot_retrieve(request, pk: int):
    """GET /admin/accounting/trial-balance/snapshots/<int:pk>/

    Detail retrieve. Returns the full frozen row set for one
    snapshot. Cross-tenant or missing pk returns 404 per fail-closed
    posture.
    """
    dealership = get_current_dealership(request)
    snapshot = get_trial_balance_snapshot(
        dealership=dealership, snapshot_id=pk
    )
    if snapshot is None:
        return Response(
            {"detail": f"TrialBalanceSnapshot #{pk} not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"trial_balance_snapshot": _project_snapshot_detail(snapshot)},
        status=status.HTTP_200_OK,
    )


# --- Milestone 27 · Increment 1 (SESSION_192) — GLAccount list substrate ------
#
# Per MILESTONE_27_PLANNING.md §5.b M27.1. Reuses
# ``IsSalesManagerOrOwnerAtActiveDealership`` — zero-drift
# permission-class streak extends across a further increment.
#
# Shared accounting infrastructure. Immediate consumer is the M27.2
# JE-create dialog picker; future consumers include recurring
# journals, adjustments, budget uploads, statement reconciliation,
# F&I chargebacks, and period-open workflows. Every future accounting
# workflow that needs GLAccount selection reuses this substrate.


@api_view(["GET"])
@permission_classes(_M131_PERMS)
def admin_gl_account_list(request):
    """GET /admin/accounting/gl-accounts/

    Returns the active chart of accounts for the current tenant,
    sorted by ``code`` ascending. Includes zero-balance accounts
    (unlike the trial balance, which activity-filters via aggregation
    over posted JournalEntryLines).

    Filters ``is_active=True`` by default — the ``is_active`` flag is
    the operator-facing soft-hide mechanism per the M13.1 GLAccount
    model contract, so inactive accounts must never surface in a
    create-workflow picker. If a future consumer needs to expose
    inactive accounts (e.g., historical-review UI), extend with a
    ``?include_inactive=true`` query parameter at that time rather
    than changing the default posture.

    Response envelope follows the M14.1 ``cost_posting_failures``
    precedent (unpaginated-collection wrapper
    ``{<resource_plural>: {<items_key>: [...]}}``).
    """
    dealership = get_current_dealership(request)
    accounts = GLAccount.objects.filter(
        dealership=dealership, is_active=True
    ).order_by("code")
    return Response(
        {
            "gl_accounts": {
                "accounts": [
                    {
                        "id": acct.pk,
                        "code": acct.code,
                        "name": acct.name,
                        "type": acct.account_type,
                    }
                    for acct in accounts
                ],
            }
        },
        status=status.HTTP_200_OK,
    )


# --- Milestone 28 · Increment 1 (SESSION_195) — journal-entry templates ------
#
# Two verbs under one URL per MILESTONE_28_PLANNING.md §5.b M28.1:
#
# - POST /admin/accounting/journal-entry-templates/  — create a template.
# - GET  /admin/accounting/journal-entry-templates/  — list active templates.
#
# Both reuse _M131_PERMS — zero-drift permission-class streak preserved
# at 27 → 28 intended. Endpoint envelope follows the gl-accounts /
# journal-entry precedents.
#
# Domain-error → HTTP mapping (asserted in
# test_m28_journal_entry_template_endpoint.py):
#
# - EmptyJournalEntryTemplateError            → 400
# - InvalidJournalEntryTemplateLineError      → 400
# - UnbalancedJournalEntryTemplateError       → 400
# - DuplicateJournalEntryTemplateNameError    → 409
# - CrossTenantGLAccountError                 → 404 (fail-closed)


class JournalEntryTemplateLineSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    side = serializers.ChoiceField(choices=[("debit", "debit"), ("credit", "credit")])
    # At M28 amount is required non-null; future variable-amount work
    # will allow null. Kept as a DecimalField for consistent parsing +
    # Decimal-as-string wire posture (matches JournalEntryLine).
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    memo = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class JournalEntryTemplateCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=500)
    lines = JournalEntryTemplateLineSerializer(many=True)


def _project_template_line(line) -> dict:
    return {
        "id": line.pk,
        "account_id": line.account_id,
        "account_code": line.account.code,
        "side": line.side,
        "amount": str(line.amount) if line.amount is not None else None,
        "memo": line.memo,
        "ordering": line.ordering,
    }


def _project_template(template: JournalEntryTemplate) -> dict:
    lines = list(template.lines.select_related("account").all())
    return {
        "id": template.pk,
        "dealership_id": template.dealership_id,
        "name": template.name,
        "description": template.description,
        "is_active": template.is_active,
        "line_count": len(lines),
        "lines": [_project_template_line(line) for line in lines],
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


def _resolve_template_lines(dealership, raw_lines):
    """Map serialized template-line dicts → :class:`TemplateLineInput`.

    Fails-closed on any missing / cross-tenant account by raising
    :class:`CrossTenantGLAccountError` (endpoint maps to 404).
    """
    account_ids = [raw["account_id"] for raw in raw_lines]
    accounts_by_id = {
        acct.pk: acct
        for acct in GLAccount.objects.filter(
            dealership=dealership, pk__in=account_ids
        )
    }
    resolved: list[TemplateLineInput] = []
    for idx, raw in enumerate(raw_lines):
        account = accounts_by_id.get(raw["account_id"])
        if account is None:
            raise CrossTenantGLAccountError(
                f"GLAccount {raw['account_id']} not found in tenant."
            )
        resolved.append(
            TemplateLineInput(
                account=account,
                side=raw["side"],
                amount=raw["amount"],
                memo=raw.get("memo", ""),
                ordering=idx,
            )
        )
    return resolved


@api_view(["GET", "POST"])
@permission_classes(_M131_PERMS)
def admin_journal_entry_template_list_or_create(request):
    """GET / POST /admin/accounting/journal-entry-templates/

    GET returns the active templates for the current tenant, ordered
    by name, with full line breakdown per response envelope. POST
    creates a template + its lines atomically.
    """
    dealership = get_current_dealership(request)

    if request.method == "GET":
        templates = list_journal_entry_templates(dealership=dealership)
        return Response(
            {
                "journal_entry_templates": {
                    "templates": [
                        _project_template(tmpl) for tmpl in templates
                    ],
                }
            },
            status=status.HTTP_200_OK,
        )

    serializer = JournalEntryTemplateCreateRequestSerializer(
        data=request.data
    )
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        lines = _resolve_template_lines(dealership, data["lines"])
    except CrossTenantGLAccountError:
        return Response(
            {"detail": "GLAccount not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        template = create_journal_entry_template(
            dealership=dealership,
            name=data["name"],
            description=data["description"],
            lines=lines,
        )
    except (
        EmptyJournalEntryTemplateError,
        InvalidJournalEntryTemplateLineError,
        UnbalancedJournalEntryTemplateError,
    ) as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except CrossTenantGLAccountError:
        return Response(
            {"detail": "GLAccount not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except DuplicateJournalEntryTemplateNameError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )

    return Response(
        {"journal_entry_template": _project_template(template)},
        status=status.HTTP_201_CREATED,
    )
