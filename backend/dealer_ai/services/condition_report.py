"""Milestone 3 · Increment 2 — condition-report service layer.

The one place all condition-report state transitions happen. Answers
the Milestone 3 business questions for any vehicle:

- *"What is the latest inspection record for this stock number?"*
- *"Who is authoring the current draft?"*
- *"What findings have been recorded?"*
- *"Is the report finished, or still being written?"*

The service is deliberately narrow. It writes and reads. It does not:

- Expose HTTP endpoints (Milestone 3 · Increment 6).
- Enforce permissions (Milestone 3 · Increment 6 — the DRF permission
  layer, distinct from this layer's cross-tenant guard; see
  ``docs/roadmap/AUTHENTICATION_MODEL.md`` §1 four-layer separation).
- Compute properties on ``Vehicle`` (Milestone 3 · Increment 3 lands
  the ``@property`` accessors that delegate to
  :func:`latest_condition_report` and
  :func:`latest_completed_condition_report`).
- Issue presigned upload URLs, verify uploaded objects, or attach /
  delete photos (Milestone 3 · Increment 4 lands the storage
  abstraction; Milestone 3 · Increment 5 lands the upload flow).
- Sanitize or produce any LLM output — Milestone 3 is deliberately
  AI-free per ``VEHICLE_CENTRIC_PIVOT.md`` §Phase 2.

Layer discipline (see ``AUTHENTICATION_MODEL.md`` §1):

- **Identity + authorization** — the view layer. Not this module.
- **Data-scoping** — this module. Every function accepts an
  explicit ``dealership`` kwarg and refuses to touch rows in any
  other tenant. This is the defense-in-depth belt; the model
  layer's ``clean()`` cross-tenant guard is the suspenders.
- **Business semantics** — this module. Whether a completed report
  can be edited is a business decision this module makes and
  locks with tests. See :class:`ConditionReportImmutableError`.

Semantic decisions locked here:

- ``draft → complete`` is one-way. No ``reopen`` in v1. If an
  operator needs to add a missed finding after completing, they
  author a **new** report. Rationale: matches the M2 immutable-
  cost-row pattern (retrospective §6 lesson 5) — once the report
  is the "record of inspection," subsequent edits corrupt the
  historical truth of what the inspector knew at inspection time.
- ``ConditionFinding.estimated_cost`` is documentation only. It
  MUST NOT touch ``VehicleCost``, ``services/vehicle_ledger.py``,
  or any M2 financial write path. The M4 recon-automation
  milestone owns the findings → work order → cost flow.

Service-contract tightening vs. planning contract (SESSION_057):

The ``MILESTONE_3_PLANNING.md`` §7 M3.2 signatures name
``dealership=`` only on ``create_report`` and the two ``latest_*``
functions. This module adds ``dealership=`` to **every** public
function (including ``complete_report``, ``add_finding``,
``update_finding``, ``delete_finding``) so the security posture is
uniform: every call site must state its tenant intent explicitly,
and the service refuses to touch a report or finding whose
denormalized ``dealership`` disagrees with what the caller
declared. This is a *tightening*, not a divergence — it does not
change what shipped surfaces expose (there are none yet; M3.6
lands the endpoints). Documented for the future in the SESSION_057
handoff.

Deferred (do NOT add in M3.2):

- Photo functions (``request_photo_upload``, ``attach_photo``,
  ``delete_photo``) — M3.5, after M3.4 lands storage.
- Vehicle ``@property`` accessors — M3.3.
- Update-report function — the M3.2 planning contract locks seven
  functions; adding an eighth (``update_report``) would invent
  a surface not committed to the planning artifact. The M3.6 API
  layer will re-open the question if operator evidence surfaces
  a case that add/update/delete-finding + complete cannot cover.
- Reopen workflow — deliberately absent; see semantic decision
  above.
"""

from __future__ import annotations

from typing import Any, Optional

from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import (
    CONDITION_CATEGORY_CHOICES,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_REPORT_STATUS_DRAFT,
    CONDITION_SEVERITY_CHOICES,
    ConditionFinding,
    ConditionReport,
    Dealership,
    Vehicle,
)


_VALID_CATEGORY_KEYS = frozenset(key for key, _ in CONDITION_CATEGORY_CHOICES)
_VALID_SEVERITY_KEYS = frozenset(key for key, _ in CONDITION_SEVERITY_CHOICES)

# Whitelist of fields ``update_finding`` may set. ``report`` and
# ``dealership`` are deliberately excluded — re-parenting or
# re-scoping a finding is not an editing operation, it is a
# semantic-level move that would need its own service function.
# ``id``, ``created_at``, ``updated_at`` are managed by the ORM.
_UPDATE_FINDING_ALLOWED_FIELDS = frozenset(
    {"category", "severity", "description", "estimated_cost", "notes"}
)


# ---- Domain errors --------------------------------------------------------


class CrossTenantConditionReportError(ValueError):
    """Raised when a condition-report service function is called with
    a ``dealership`` that does not match the target ``Vehicle``,
    ``ConditionReport``, or ``ConditionFinding``.

    Subclasses :class:`ValueError` so callers that catch
    ``ValueError`` (test code, generic error handlers) still work.
    Named specifically so log lines and API responses can identify
    the failure mode without string-matching an error message.

    This is the *service-layer* defense against cross-tenant access.
    The *model layer* (``ConditionReport.clean`` /
    ``ConditionFinding.clean`` / ``ConditionFindingPhoto.clean``)
    is the second line — belt + suspenders. Do not remove either.

    Shape matches ``CrossTenantLedgerError`` from
    ``services/vehicle_ledger.py`` so callers that already know the
    M2 pattern do not have to learn a new one.
    """


class ConditionReportImmutableError(ValueError):
    """Raised when a caller attempts to edit, add findings to,
    complete, or delete findings from a report whose ``status`` is
    already ``complete``.

    Subclasses :class:`ValueError`; distinct from
    :class:`CrossTenantConditionReportError` so the M3.6 API layer
    can map this to HTTP 409 Conflict ("the resource is in a state
    that forbids the requested edit") while cross-tenant maps to
    HTTP 404 or 403 (never leak whether the resource exists).

    Distinct from the model layer's ``clean()`` ``completed_at`` ↔
    ``status`` invariant, which guards against inconsistent field
    combinations. This error guards against a *transition* — the
    row is internally consistent, but the requested operation
    would corrupt the historical truth of a completed inspection.
    """


# ---- Cross-tenant guards --------------------------------------------------


def _assert_vehicle_tenant(vehicle: Vehicle, dealership: Dealership) -> None:
    """Raise :class:`CrossTenantConditionReportError` when the target
    vehicle does not belong to the caller's dealership.

    Runs at the entry of every service function that operates on a
    :class:`Vehicle` directly (``create_report``, ``latest_*``).
    """
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantConditionReportError(
            f"Vehicle #{vehicle.stock_number} belongs to dealership "
            f"{vehicle.dealership_id}, not {dealership.pk}. "
            "Condition-report writes and reads MUST match the tenant "
            "that owns the vehicle "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )


def _assert_report_tenant(
    report: ConditionReport, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantConditionReportError` when the target
    report does not belong to the caller's dealership.

    Verifies both ``report.dealership`` and
    ``report.vehicle.dealership`` (the denormalized carrier and the
    parent Vehicle) — either mismatch is a cross-tenant access
    attempt and fails closed.
    """
    if report.dealership_id != dealership.pk:
        raise CrossTenantConditionReportError(
            f"ConditionReport #{report.pk} belongs to dealership "
            f"{report.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )
    # The report's parent Vehicle is the ground-truth tenant; the
    # denormalized ``report.dealership`` should always match, but if
    # a direct ORM write drifted the two, this check catches it
    # before the mutation propagates.
    if report.vehicle.dealership_id != dealership.pk:
        raise CrossTenantConditionReportError(
            f"ConditionReport #{report.pk} references vehicle "
            f"#{report.vehicle.stock_number} which belongs to "
            f"dealership {report.vehicle.dealership_id}, not "
            f"{dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )


def _assert_finding_tenant(
    finding: ConditionFinding, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantConditionReportError` when the target
    finding's report or parent vehicle does not belong to the
    caller's dealership.

    Verifies both:

    - ``finding.report.dealership == dealership``
    - ``finding.report.vehicle.dealership == dealership``

    Per SESSION_057 spec, findings check *both* — the denormalized
    carrier plus the ground-truth vehicle tenant — because a
    finding sits two FK hops away from the vehicle and either drift
    is a cross-tenant leak.
    """
    if finding.dealership_id != dealership.pk:
        raise CrossTenantConditionReportError(
            f"ConditionFinding #{finding.pk} belongs to dealership "
            f"{finding.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )
    _assert_report_tenant(finding.report, dealership)


# ---- Immutability guard ---------------------------------------------------


def _refresh_and_assert_draft(
    report: ConditionReport, operation: str
) -> None:
    """Refresh the report from the DB and raise
    :class:`ConditionReportImmutableError` when its status is not
    ``draft``.

    The refresh handles the narrow race where a caller holds an
    in-memory draft instance while another process transitions the
    same row to ``complete``. The refresh cost (one query) is worth
    the correctness win; if the DB says the report is complete,
    every write operation refuses.
    """
    report.refresh_from_db()
    if report.status != CONDITION_REPORT_STATUS_DRAFT:
        raise ConditionReportImmutableError(
            f"Cannot {operation}: ConditionReport #{report.pk} "
            f"status is {report.status!r}. Completed reports are "
            "immutable. To capture new findings, author a new report."
        )


# ---- Create ---------------------------------------------------------------


def create_report(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    authored_by=None,
    inspector_name: str,
    inspected_at,
    mileage_at_inspection: int,
    notes: str = "",
) -> ConditionReport:
    """Create a new condition report for ``vehicle`` in ``draft`` status.

    Always creates in ``status="draft"``. ``completed_at`` is left
    NULL. To finish the report, call :func:`complete_report`.

    Every call creates a new :class:`ConditionReport` row —
    Vehicle is *many-per*, not OneToOne, so the same vehicle can be
    re-inspected across its lifetime (arrival, post-recon,
    pre-frontline, owner walkthrough per RECON §7.5).

    The ``authored_by`` (FK to the user who typed the report) and
    ``inspector_name`` (free-text name of the person who physically
    inspected the vehicle) fields are distinct on purpose — a
    service writer may transcribe a paper inspection performed by
    a mechanic (RECON §2.4). ``inspector_name`` is required;
    ``authored_by`` is optional (nullable + SET_NULL so seed /
    management-command writes without a request-scoped user don't
    require a synthetic user account).

    Every write path:

    - Refuses cross-tenant writes at entry
      (:class:`CrossTenantConditionReportError`).
    - Passes ``dealership=`` explicitly per
      ``AUTHENTICATION_MODEL.md`` §8b (does not rely on the
      ``pre_save`` autofill signal).
    - Runs ``full_clean()`` before saving — surfaces the model's
      ``clean()`` cross-tenant guard, the ``completed_at`` ↔
      ``status`` invariant, and field-shape validation before
      hitting the DB.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    report = ConditionReport(
        vehicle=vehicle,
        dealership=dealership,
        authored_by=authored_by,
        inspector_name=inspector_name,
        inspected_at=inspected_at,
        mileage_at_inspection=mileage_at_inspection,
        status=CONDITION_REPORT_STATUS_DRAFT,
        completed_at=None,
        notes=notes,
    )
    report.full_clean()
    report.save()
    return report


# ---- Complete -------------------------------------------------------------


def complete_report(
    report: ConditionReport, *, dealership: Dealership
) -> ConditionReport:
    """Transition ``report`` from ``draft`` to ``complete``.

    One-way. Sets ``completed_at`` to the current time
    (:func:`django.utils.timezone.now`) atomically with the status
    change. Raises :class:`ConditionReportImmutableError` when the
    report is already complete.

    There is no reverse transition. If an operator needs to add a
    missed finding after completing, they author a **new** report.
    This preserves the historical truth of what the inspector knew
    at inspection time (retrospective §6 lesson 5).

    Refuses cross-tenant writes at entry via
    :func:`_assert_report_tenant`.
    """
    _assert_report_tenant(report, dealership)
    _refresh_and_assert_draft(report, operation="complete report")

    report.status = CONDITION_REPORT_STATUS_COMPLETE
    report.completed_at = timezone.now()
    report.full_clean()
    report.save()
    return report


# ---- Finding CRUD (gated by report status) --------------------------------


def add_finding(
    report: ConditionReport,
    *,
    dealership: Dealership,
    category: str,
    severity: str,
    description: str,
    estimated_cost=None,
    notes: str = "",
) -> ConditionFinding:
    """Append a new finding to a draft report.

    Refuses when ``report.status == "complete"`` — completed reports
    are immutable, and their finding set is part of that
    immutability (retrospective §6 lesson 5 applied to inspection
    history).

    Validates ``category`` and ``severity`` against the canonical
    vocabularies before touching the DB — raises :class:`ValueError`
    with a message pointing at the constant list. This is earlier
    than the model's ``choices=`` validation and uses a
    service-appropriate exception type.

    ``estimated_cost`` is documentation only. It MUST NOT create or
    modify a ``VehicleCost`` row, MUST NOT enter
    ``services/vehicle_ledger.compute_totals``, and MUST NOT
    influence ``projected_total_investment``. The M4 recon-
    automation milestone owns the findings → work-order → cost
    flow. Enforced at both the model layer (see
    ``test_condition_finding.EstimatedCostDoesNotPostToVehicleCost``)
    and the service layer (see the corresponding assertion in
    ``test_condition_report_service``).
    """
    _assert_report_tenant(report, dealership)
    _refresh_and_assert_draft(report, operation="add finding")

    if category not in _VALID_CATEGORY_KEYS:
        raise ValueError(
            f"Unknown ConditionFinding category: {category!r}. Valid "
            f"categories live in "
            f"``dealer_ai.models.CONDITION_CATEGORY_CHOICES``."
        )
    if severity not in _VALID_SEVERITY_KEYS:
        raise ValueError(
            f"Unknown ConditionFinding severity: {severity!r}. Valid "
            f"severities live in "
            f"``dealer_ai.models.CONDITION_SEVERITY_CHOICES``."
        )

    finding = ConditionFinding(
        report=report,
        dealership=dealership,
        category=category,
        severity=severity,
        description=description,
        estimated_cost=estimated_cost,
        notes=notes,
    )
    finding.full_clean()
    finding.save()
    return finding


def update_finding(
    finding: ConditionFinding,
    *,
    dealership: Dealership,
    **updates: Any,
) -> ConditionFinding:
    """Update a whitelisted subset of fields on a finding.

    Whitelist:

    - ``category`` — re-validated against the canonical vocabulary.
    - ``severity`` — re-validated against the canonical vocabulary.
    - ``description`` — the human's words; RECON §2.6 prohibits AI
      authorship.
    - ``estimated_cost`` — documentation only (see
      :func:`add_finding`).
    - ``notes`` — free text.

    Attempting to update any other field (``report``, ``dealership``,
    ``id``, ``created_at``, ``updated_at``, unknown keys) raises
    :class:`ValueError`. Re-parenting or re-scoping is not an
    editing operation; if operator evidence surfaces a real need for
    "move this finding to a different report" or "reassign this
    finding to a different tenant," that is a separate service
    function with its own design memo.

    Refuses when the parent report is complete.
    """
    _assert_finding_tenant(finding, dealership)
    _refresh_and_assert_draft(finding.report, operation="update finding")

    unknown = set(updates.keys()) - _UPDATE_FINDING_ALLOWED_FIELDS
    if unknown:
        raise ValueError(
            f"Cannot update forbidden or unknown ConditionFinding "
            f"field(s): {sorted(unknown)!r}. Allowed fields: "
            f"{sorted(_UPDATE_FINDING_ALLOWED_FIELDS)!r}."
        )

    if "category" in updates and updates["category"] not in _VALID_CATEGORY_KEYS:
        raise ValueError(
            f"Unknown ConditionFinding category: "
            f"{updates['category']!r}. Valid categories live in "
            f"``dealer_ai.models.CONDITION_CATEGORY_CHOICES``."
        )
    if "severity" in updates and updates["severity"] not in _VALID_SEVERITY_KEYS:
        raise ValueError(
            f"Unknown ConditionFinding severity: "
            f"{updates['severity']!r}. Valid severities live in "
            f"``dealer_ai.models.CONDITION_SEVERITY_CHOICES``."
        )

    for field_name, value in updates.items():
        setattr(finding, field_name, value)

    finding.full_clean()
    finding.save()
    return finding


def delete_finding(
    finding: ConditionFinding, *, dealership: Dealership
) -> None:
    """Delete a finding from a draft report.

    Refuses when the parent report is complete — completed reports
    are immutable, and that includes the finding set.

    Returns ``None`` on success; raises on refusal. Callers that
    need the deleted finding's fields for downstream logging should
    read them before calling.
    """
    _assert_finding_tenant(finding, dealership)
    _refresh_and_assert_draft(finding.report, operation="delete finding")

    finding.delete()


# ---- Reads ---------------------------------------------------------------


def latest_condition_report(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[ConditionReport]:
    """Return the most recent :class:`ConditionReport` for ``vehicle``,
    or ``None``.

    Any status — draft or complete. Deterministic ordering matches
    ``ConditionReport.Meta.ordering = ("-inspected_at",
    "-created_at")``: the physically-most-recent inspection wins;
    ties break to the most-recently-created row.

    Refuses cross-tenant reads at entry
    (:class:`CrossTenantConditionReportError`). No writes. No
    caching in v1 — repeated calls hit the DB every time. If M3.3
    (Vehicle ``@property`` accessors) or M3.7 (operator UI)
    surfaces read-heavy access patterns, revisit with
    ``@cached_property``; do not preemptively cache.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    return (
        ConditionReport.objects.filter(
            vehicle=vehicle, dealership=dealership
        )
        .order_by("-inspected_at", "-created_at")
        .first()
    )


def latest_completed_condition_report(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[ConditionReport]:
    """Return the most recent *complete* :class:`ConditionReport` for
    ``vehicle``, or ``None``.

    Filters to ``status="complete"`` — the accessor future callers
    (M4 recon plan drafting, M3.7 operator UI "inspected on
    YYYY-MM-DD" badge) hit most often, because a draft report has
    not been signed off yet.

    Same ordering + cross-tenant + no-caching contract as
    :func:`latest_condition_report`.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    return (
        ConditionReport.objects.filter(
            vehicle=vehicle,
            dealership=dealership,
            status=CONDITION_REPORT_STATUS_COMPLETE,
        )
        .order_by("-inspected_at", "-created_at")
        .first()
    )


# Kept as a defensive re-export so callers do not have to reach into
# the Django internals just to catch model-clean errors from
# ``full_clean()``.
__all__ = [
    "ConditionReportImmutableError",
    "CrossTenantConditionReportError",
    "ValidationError",
    "add_finding",
    "complete_report",
    "create_report",
    "delete_finding",
    "latest_completed_condition_report",
    "latest_condition_report",
    "update_finding",
]
