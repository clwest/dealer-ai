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

from .models import GLAccount, JournalEntry
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.accounting import (
    CrossTenantGLAccountError,
    CrossTenantJournalEntryError,
    EmptyJournalEntryError,
    ImmutableJournalEntryError,
    InvalidJournalLineError,
    JournalLineInput,
    TrialBalanceSnapshot,
    UnbalancedJournalEntryError,
    compute_trial_balance,
    detect_cost_posting_failures,
    get_journal_entry,
    list_journal_entries,
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


def _project_trial_balance(snapshot: TrialBalanceSnapshot) -> dict:
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
