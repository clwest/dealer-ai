"""Milestone 4 · Increment 2 — recon service layer.

The one place all recon decisions and work-order state transitions
happen. Answers the M4 business questions for a vehicle at the
business-logic layer:

- *"Which findings has the dealership decided to fix (must / should /
  won't do)?"* — :func:`record_decision`.
- *"What work is authorized for this vehicle?"* —
  :func:`create_work_order` + :func:`approve_work_order`.
- *"Which findings does each work order address?"* —
  :func:`attach_findings` / :func:`detach_finding`.
- *"What is the current state of each work order?"* —
  :func:`start_work_order` / :func:`complete_work_order` /
  :func:`cancel_work_order`.
- *"What work is open on this vehicle right now?"* —
  :func:`open_work_orders_for_vehicle` (backing the
  ``Vehicle.open_work_orders`` @property).
- *"Has the recon manager decided the plan yet?"* —
  :func:`has_recon_decisions_for_vehicle` (backing
  ``Vehicle.has_recon_decisions``).

The service writes and reads WorkOrder, ReconDecision, and
WorkOrderFinding rows, and — as of M4.3 — posts auto-minted
:class:`VehicleCost` rows via
:func:`services.vehicle_ledger.add_cost` at the approve /
revise-estimate / complete / cancel transitions. The reference-key
vocabulary is locked at planning §5.e (five families:
``estimate:<seq>``, ``estimate_reversal:<seq>``,
``completion_estimate_reversal``, ``estimate_reversal:cancel``,
``actual``). Every helper is idempotent via reference lookup so
transition replay is safe. The service does NOT:
- Own :class:`WorkOrderPart` transitions (add/order/receive/
  install/return). Parts service lands in M4.4.
- Draft or send :class:`VendorCommunication` rows. Vendor comm
  drafting + `_scrub_invented_recon_fact` land in M4.5.
- Expose HTTP endpoints or enforce permissions — M4.6.
- Compute front-line-ready or aging metrics — M5 / M8.
- Sanitize or produce any LLM output.

Layer discipline (per :doc:`AUTHENTICATION_MODEL.md` §1):

- **Identity + authorization** — view layer. Not this module.
- **Data-scoping** — this module. Every public function accepts an
  explicit ``dealership`` kwarg and refuses to touch rows in any
  other tenant. This is the belt; the M4.1 model layer's
  ``clean()`` guards are the suspenders.
- **Business semantics** — this module. State transitions,
  attach/detach gating, decision-reconsideration policy, and
  approval invariants are locked here and tested.

Semantic decisions locked here:

- **State machine (per planning §5.c).** Allowed transitions:
  ``draft → approved``, ``draft → cancelled``,
  ``approved → approved`` (idempotent re-approve for cost/date
  refinement), ``approved → in_progress``, ``approved →
  cancelled``, ``in_progress → completed``, ``in_progress →
  cancelled``. Terminal: ``completed``, ``cancelled``. No
  ``approved → completed`` direct path (planning §5.c does not
  list it; explicit start is required before completion). No
  re-open in v1.

- **Decision reconsideration (SESSION_067 policy).**
  :func:`record_decision` is an intentional upsert while no
  linked work order has left ``draft`` state. Rationale: recon
  managers legitimately reconsider the ``must_do`` vs
  ``should_do`` line after seeing quotes come back or budget
  constraints tighten. Once ANY linked ``WorkOrder`` has moved
  past ``draft``, the decision is locked — changing it after work
  has been authorized would corrupt the audit trail of *what was
  decided when the work was ordered*. Refusal raises
  :class:`ReconImmutableError`.

- **Approval requires at least one linked finding.** Draft →
  approved refuses when ``work_order.finding_links.count() == 0``.
  Rationale: planning §1.4 frames WorkOrders as the execution
  side of the finding → decision → work chain. A no-finding
  approval would break Q1 back-traceability (RECON §3.7). If
  operational evidence surfaces a legitimate no-finding recon
  job (e.g. routine detail on a front-line-ready unit), the rule
  is a service-layer concern that can be relaxed with a planning
  annotation — no schema change required.

- **`approve → approve` idempotent re-approve.** Refreshes
  ``approved_at`` (audit trail: "most recently re-approved at
  time X"), permits ``authorized_cost`` update, and **preserves
  the original `approved_by`** — the first-time approver is the
  historical fact. If a different user needs to record approval,
  they cancel and recreate.

- **Complete requires nonnegative `actual_cost`.** Negative
  amounts on the ledger side are for reversing entries (M4.3),
  not for actual work-order completions. A negative actual would
  indicate the vendor paid the dealership, which is out of
  scope.

- **Cancel requires nonblank reason once WO has been approved
  or started.** Cancelling a draft is cheap (nothing was
  authorized); cancelling an approved or in-progress WO has
  operational consequences (a vendor was told the work was
  authorized) and deserves an explicit reason string for the
  audit trail.

- **QC verification is NOT claimed by completion.** Per the
  ``MILESTONE_4_PLANNING.md`` §1.0.QC-GAP annotation
  (SESSION_067), ``WorkOrder.completed_at`` proves *when work
  was marked complete*, not *whether it was verified*. This
  service does not accept a ``qc_verified=`` parameter and does
  not populate any QC field.

- **`full_clean()` before every save.** Surfaces the M4.1 model-
  layer cross-tenant guards and structural invariants
  (outsourced-requires-vendor; vendor-tenant match; WOF
  cross-vehicle refusal) as :class:`ValidationError` before the
  row hits the DB.

- **Domain errors are the public contract.** Callers see
  :class:`CrossTenantReconError` / :class:`ReconImmutableError`
  / :class:`InvalidReconTransitionError` /
  :class:`IncompleteConditionReportError`. Raw ``ValidationError``
  or ``IntegrityError`` never surface as normal service
  contracts — the service catches and re-raises where the
  translation is meaningful.

Concurrency posture:

- State transitions use ``transaction.atomic()`` + ``select_for_update()``
  on the target WorkOrder row so two concurrent approve /
  complete calls cannot both succeed against the same row and
  produce contradictory provenance.
- ``refresh_from_db()`` runs inside the transaction so the
  from-state check sees committed data, not the caller's stale
  in-memory copy.
- Attach findings runs inside ``transaction.atomic()`` so an
  invalid finding in the middle of the batch does not leave a
  partial attachment set behind.
- No distributed-locking framework is introduced — Django's
  row-level lock via ``select_for_update`` is sufficient for the
  single-DB deployment M4 targets. If M8+ introduces
  cross-service coordination, revisit.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Sequence

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from ..models import (
    CATEGORY_BODY_WORK,
    CATEGORY_BRAKES,
    CATEGORY_DIAGNOSTICS,
    CATEGORY_GLASS,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_MISC_DEALER_EXPENSES,
    CATEGORY_OIL_SERVICE,
    CATEGORY_PAINT,
    CATEGORY_TIRES,
    CATEGORY_UPHOLSTERY,
    CONDITION_CATEGORY_ACCESSORIES,
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_COSMETIC,
    CONDITION_CATEGORY_ELECTRICAL,
    CONDITION_CATEGORY_FLUIDS,
    CONDITION_CATEGORY_GLASS,
    CONDITION_CATEGORY_INTERIOR,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_MISSING,
    CONDITION_CATEGORY_OTHER,
    CONDITION_CATEGORY_SAFETY,
    CONDITION_CATEGORY_TIRES,
    CONDITION_REPORT_STATUS_COMPLETE,
    ConditionFinding,
    Dealership,
    RECON_DECISION_TIER_CHOICES,
    ReconDecision,
    Vehicle,
    VehicleCost,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WorkOrder,
    WorkOrderFinding,
)
from .condition_report import (
    latest_completed_condition_report as _latest_completed_condition_report,
)
from .vehicle_ledger import add_cost as _add_cost

_VALID_RECON_DECISION_TIER_KEYS = frozenset(
    key for key, _ in RECON_DECISION_TIER_CHOICES
)

# Set of statuses considered "non-terminal" for the open-work-orders
# filter and the cancel-source check. Kept module-level so tests can
# import it and lock the exact vocabulary.
_OPEN_STATUSES = frozenset(
    {
        WORK_ORDER_STATUS_DRAFT,
        WORK_ORDER_STATUS_APPROVED,
        WORK_ORDER_STATUS_IN_PROGRESS,
    }
)

# Statuses that lock a ReconDecision (planning §5.c + SESSION_067
# reconsideration policy). Any linked WorkOrder in one of these
# states means the decision is history and cannot be updated.
_DECISION_LOCKING_WORK_ORDER_STATUSES = frozenset(
    {
        WORK_ORDER_STATUS_APPROVED,
        WORK_ORDER_STATUS_IN_PROGRESS,
        WORK_ORDER_STATUS_COMPLETED,
        WORK_ORDER_STATUS_CANCELLED,
    }
)


# ----------------------------------------------------------------------------
# Milestone 4 · Increment 3 (SESSION_068) — ledger integration.
# ----------------------------------------------------------------------------

# Reference-key vocabulary — five families, locked at planning §5.e
# (SESSION_066 refinement). Every auto-minted VehicleCost row this
# module posts carries a reference matching exactly one of these
# format strings. Idempotency is enforced by looking up the resolved
# reference before posting: repeated calls for the same key skip.
#
# The five families let idempotency distinguish "we already reversed
# on completion" from "we reversed during a mid-life revision" from
# "we reversed on cancellation" without ambiguity.
WORKORDER_LEDGER_REF_ESTIMATE = "WORKORDER:{wo_id}:estimate:{seq}"
WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL = (
    "WORKORDER:{wo_id}:estimate_reversal:{seq}"
)
WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL = (
    "WORKORDER:{wo_id}:completion_estimate_reversal"
)
WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL = (
    "WORKORDER:{wo_id}:estimate_reversal:cancel"
)
WORKORDER_LEDGER_REF_ACTUAL = "WORKORDER:{wo_id}:actual"


# WorkOrder.category (12 M3 finding categories) → VehicleCost.category
# (26 M2 expense categories). The two vocabularies serve different
# purposes — the finding side answers "what kind of defect?"; the
# ledger side answers "what kind of expense?" — so a one-way mapping
# is required at posting time.
#
# Chosen mapping (SESSION_068; documented at planning §5.e mapping
# note). Ambiguous rows (COSMETIC could be PAINT or BODY_WORK;
# SAFETY could be BRAKES or TIRES) default to the most common
# real-world outcome:
#
# - MECHANICAL → MECHANICAL_LABOR — engine / drivetrain fault
#   diagnostics turn into shop labor.
# - COSMETIC → PAINT — cosmetic findings are dominated by chip /
#   scratch / blend jobs (paint), not full body panel work.
# - BODY → BODY_WORK — panel dent / structural findings.
# - GLASS → GLASS — direct one-to-one.
# - TIRES → TIRES — direct one-to-one.
# - INTERIOR → UPHOLSTERY — seat tear / dash crack / carpet
#   restoration.
# - FLUIDS → OIL_SERVICE — fluid findings in inspection are
#   dominated by oil / coolant / transmission service.
# - ELECTRICAL → DIAGNOSTICS — electrical faults start with a
#   diagnostic charge; labor to fix follows as a separate
#   MECHANICAL_LABOR line if the shop bills that way.
# - SAFETY → BRAKES — safety findings are most commonly
#   brake-related. Tire safety would come in as TIRES on its own.
# - ACCESSORIES → MISC_DEALER_EXPENSES — key fobs, floor mats,
#   trim clips.
# - MISSING → MISC_DEALER_EXPENSES — replacement of missing items
#   (owner's manual, second key).
# - OTHER → MISC_DEALER_EXPENSES — the escape hatch.
#
# This is a policy call — operational evidence may motivate a
# revision in M8 (once cost-variance dashboards make the
# category-mapping consequences visible).
_WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY = {
    CONDITION_CATEGORY_MECHANICAL: CATEGORY_MECHANICAL_LABOR,
    CONDITION_CATEGORY_COSMETIC: CATEGORY_PAINT,
    CONDITION_CATEGORY_BODY: CATEGORY_BODY_WORK,
    CONDITION_CATEGORY_GLASS: CATEGORY_GLASS,
    CONDITION_CATEGORY_TIRES: CATEGORY_TIRES,
    CONDITION_CATEGORY_INTERIOR: CATEGORY_UPHOLSTERY,
    CONDITION_CATEGORY_FLUIDS: CATEGORY_OIL_SERVICE,
    CONDITION_CATEGORY_ELECTRICAL: CATEGORY_DIAGNOSTICS,
    CONDITION_CATEGORY_SAFETY: CATEGORY_BRAKES,
    CONDITION_CATEGORY_ACCESSORIES: CATEGORY_MISC_DEALER_EXPENSES,
    CONDITION_CATEGORY_MISSING: CATEGORY_MISC_DEALER_EXPENSES,
    CONDITION_CATEGORY_OTHER: CATEGORY_MISC_DEALER_EXPENSES,
}


_ZERO = Decimal("0.00")


# ---- Domain errors --------------------------------------------------------


class CrossTenantReconError(ValueError):
    """Raised when a recon service function is called with a
    ``dealership`` that does not match the target Vehicle,
    ConditionFinding, WorkOrder, WorkOrderFinding, or Vendor.

    Subclasses :class:`ValueError` so callers that catch
    ``ValueError`` still work. Mirrors
    :class:`CrossTenantConditionReportError` /
    :class:`CrossTenantLedgerError` from M2 / M3.

    Model-layer ``clean()`` cross-tenant guards on the six M4.1
    models are the suspenders — this service-layer guard is the
    belt. Do not remove either.
    """


class ReconImmutableError(ValueError):
    """Raised when a caller attempts to change a decision or
    work-order state that policy locks.

    Two current use sites:

    - :func:`record_decision` when the caller tries to update a
      decision whose linked WorkOrder has left ``draft`` (a
      linked approved / in_progress / completed / cancelled WO
      locks the decision — see SESSION_067 reconsideration
      policy in the module docstring).
    - Would-be re-open flows on terminal WorkOrders (planning
      §5.c: no reopen in v1; the caller should create a new WO
      instead).

    Distinct from :class:`InvalidReconTransitionError` so the
    M4.6 API layer can distinguish "the requested change is
    forbidden because of prior downstream state" (409 Conflict)
    from "the transition is illegal for this from-state"
    (also 409, but with a different remediation message).
    """


class InvalidReconTransitionError(ValueError):
    """Raised when a state transition is attempted from a
    from-state that the M4.2 state machine does not permit.

    Distinct from :class:`ReconImmutableError` for the reason
    given there. The message includes the current status and
    the attempted transition name so operators can understand
    the refusal without reading the source.

    Also raised at approval time when the WorkOrder has no
    linked findings — the transition is refused because the
    WorkOrder's business preconditions are not met, which is a
    kind of illegal-transition case.
    """


class IncompleteConditionReportError(ValueError):
    """Raised by :func:`record_decision` and :func:`attach_findings`
    when a target ConditionFinding belongs to a report whose
    ``status`` is not ``complete``.

    Decisions and work-order finding-links can only be recorded
    against inspection observations that have been signed off —
    draft-report findings are still editable / deletable, and
    recording downstream decisions against them would corrupt the
    historical truth of what the inspector actually saw.

    Distinct from :class:`ReconImmutableError` (which locks
    already-recorded decisions) and
    :class:`InvalidReconTransitionError` (which refuses illegal
    WO state moves).
    """


# ---- Cross-tenant guards --------------------------------------------------


def _assert_vehicle_tenant(vehicle: Vehicle, dealership: Dealership) -> None:
    """Raise :class:`CrossTenantReconError` when the target
    vehicle does not belong to the caller's dealership."""
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantReconError(
            f"Vehicle #{vehicle.stock_number} belongs to dealership "
            f"{vehicle.dealership_id}, not {dealership.pk}. Recon "
            "reads and writes MUST match the tenant that owns the "
            "vehicle (AUTHENTICATION_MODEL.md §1 layer 4)."
        )


def _assert_finding_tenant(
    finding: ConditionFinding, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantReconError` when the target
    finding's report or parent vehicle does not belong to the
    caller's dealership.

    Verifies both the denormalized ``finding.dealership`` and the
    ground-truth ``finding.report.vehicle.dealership``. Either
    drift is a cross-tenant leak.
    """
    if finding.dealership_id != dealership.pk:
        raise CrossTenantReconError(
            f"ConditionFinding #{finding.pk} belongs to dealership "
            f"{finding.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )
    parent_dealership_id = getattr(
        getattr(finding.report, "vehicle", None), "dealership_id", None
    )
    if parent_dealership_id is not None and parent_dealership_id != dealership.pk:
        raise CrossTenantReconError(
            f"ConditionFinding #{finding.pk} references vehicle in "
            f"dealership {parent_dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )


def _assert_work_order_tenant(
    work_order: WorkOrder, dealership: Dealership
) -> None:
    """Raise :class:`CrossTenantReconError` when the target
    WorkOrder or its parent vehicle does not belong to the
    caller's dealership."""
    if work_order.dealership_id != dealership.pk:
        raise CrossTenantReconError(
            f"WorkOrder #{work_order.pk} belongs to dealership "
            f"{work_order.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )
    parent_dealership_id = getattr(work_order.vehicle, "dealership_id", None)
    if parent_dealership_id is not None and parent_dealership_id != dealership.pk:
        raise CrossTenantReconError(
            f"WorkOrder #{work_order.pk} references vehicle in "
            f"dealership {parent_dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )


# ---- Record decision ------------------------------------------------------


def record_decision(
    finding: ConditionFinding,
    *,
    dealership: Dealership,
    tier: str,
    decided_by=None,
    decided_at=None,
    notes: str = "",
) -> ReconDecision:
    """Record or update the recon decision for a finding.

    **Upsert-while-not-yet-authorized policy (SESSION_067).**
    Recon managers legitimately reconsider must_do / should_do /
    wont_do before quotes come back and before work is authorized.
    Once ANY linked WorkOrder has left draft state (approved,
    in_progress, completed, cancelled), the decision is locked as
    part of the audit trail — attempts to change it raise
    :class:`ReconImmutableError`.

    Preconditions:

    - Parent report status must be ``complete`` (raises
      :class:`IncompleteConditionReportError` otherwise). Draft
      reports have editable findings; recording decisions against
      those would drift when the finding is later edited or
      deleted.
    - Tenant chain must match (raises
      :class:`CrossTenantReconError`).
    - ``tier`` must be one of the canonical
      :data:`RECON_DECISION_TIER_CHOICES` keys (raises
      :class:`ValueError`).

    Behavior:

    - No existing decision → creates one. ``decided_at`` defaults
      to :func:`django.utils.timezone.now`.
    - Existing decision + no non-draft linked WO → updates the
      row's ``tier`` / ``decided_by`` / ``decided_at`` / ``notes``.
      Preserves the ``id``, ``created_at``, and the reverse
      OneToOne accessor so callers holding refs stay valid.
    - Existing decision + ≥1 non-draft linked WO → raises
      :class:`ReconImmutableError`.

    Does NOT create WorkOrders as a side effect (planning §5.a
    Option B — the plan is emergent from decisions + WOs; the
    two are separate operator gestures).
    """
    _assert_finding_tenant(finding, dealership)
    if finding.report.status != CONDITION_REPORT_STATUS_COMPLETE:
        raise IncompleteConditionReportError(
            f"Cannot record decision on ConditionFinding #{finding.pk}: "
            f"parent ConditionReport #{finding.report_id} status is "
            f"{finding.report.status!r}. Decisions may only be recorded "
            "against completed inspection reports."
        )
    if tier not in _VALID_RECON_DECISION_TIER_KEYS:
        raise ValueError(
            f"Unknown ReconDecision tier: {tier!r}. Valid tiers live in "
            "``dealer_ai.models.RECON_DECISION_TIER_CHOICES``."
        )

    decided_at_final = decided_at if decided_at is not None else timezone.now()

    with transaction.atomic():
        existing = (
            ReconDecision.objects.select_for_update()
            .filter(finding=finding)
            .first()
        )
        if existing is None:
            decision = ReconDecision(
                finding=finding,
                dealership=dealership,
                tier=tier,
                decided_by=decided_by,
                decided_at=decided_at_final,
                notes=notes,
            )
            decision.full_clean()
            decision.save()
            return decision

        # Existing decision — check whether any linked WorkOrder has
        # left draft state. If so, the decision is locked.
        if WorkOrderFinding.objects.filter(
            finding=finding,
            work_order__status__in=_DECISION_LOCKING_WORK_ORDER_STATUSES,
        ).exists():
            raise ReconImmutableError(
                f"Cannot update ReconDecision on ConditionFinding "
                f"#{finding.pk}: at least one linked WorkOrder has left "
                "draft state (approved / in_progress / completed / "
                "cancelled). The decision is locked as part of the "
                "audit trail. To change course, cancel the linked "
                "WorkOrder(s) and record a new decision against a new "
                "finding."
            )

        existing.tier = tier
        existing.decided_by = decided_by
        existing.decided_at = decided_at_final
        existing.notes = notes
        existing.full_clean()
        existing.save()
        return existing


# ---- Create work order ----------------------------------------------------


def create_work_order(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    category: str,
    venue: str,
    vendor=None,
    assignee=None,
    estimated_cost=None,
    estimated_completion_date=None,
    notes: str = "",
) -> WorkOrder:
    """Create a new WorkOrder in ``status='draft'``.

    Always creates in draft. Rejects any attempt to supply a
    non-draft status or any transition-provenance field (approved_at,
    started_at, completed_at, cancelled_at, and their _by pairs) —
    those live on the transition functions.

    Structural invariants delegated to the M4.1 model's
    :meth:`WorkOrder.clean`:

    - ``dealership`` matches ``vehicle.dealership`` (cross-tenant
      guard).
    - ``venue == 'outsourced'`` requires a Vendor.
    - Vendor's ``dealership`` matches (cross-tenant vendor guard).

    ``estimated_cost`` is a documentation-only field at this stage.
    It becomes ledger-side in M4.3 via
    ``add_cost(is_estimate=True, ...)`` at approval time.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    if vendor is not None and vendor.dealership_id != dealership.pk:
        raise CrossTenantReconError(
            f"Vendor #{vendor.pk} belongs to dealership "
            f"{vendor.dealership_id}, not {dealership.pk} "
            "(AUTHENTICATION_MODEL.md §1 layer 4)."
        )

    wo = WorkOrder(
        vehicle=vehicle,
        dealership=dealership,
        category=category,
        venue=venue,
        vendor=vendor,
        assignee=assignee,
        status=WORK_ORDER_STATUS_DRAFT,
        estimated_cost=estimated_cost,
        estimated_completion_date=estimated_completion_date,
        notes=notes,
    )
    try:
        wo.full_clean()
    except ValidationError as exc:
        # Re-raise structural validation errors as domain errors
        # where the translation carries meaning. Outsourced-without-
        # vendor is a business rule violation, not a form-level
        # "please fill in this field" case.
        raise InvalidReconTransitionError(
            f"WorkOrder creation refused: {exc.message_dict!r}"
        ) from exc
    wo.save()
    return wo


# ---- Attach / detach findings ---------------------------------------------


def attach_findings(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    finding_ids: Sequence[int],
) -> list[WorkOrderFinding]:
    """Link one or more ConditionFindings to a draft WorkOrder.

    Batch-atomic: either every requested link is created (or was
    already present), or none are created. A single invalid
    finding in the batch aborts the entire operation and leaves
    the through table untouched.

    Preconditions verified for **every** finding in the input list
    before any write happens:

    - Finding belongs to the same dealership as the WorkOrder
      (raises :class:`CrossTenantReconError`).
    - Finding's parent report is ``complete`` (raises
      :class:`IncompleteConditionReportError`).
    - Finding's parent Vehicle matches the WorkOrder's Vehicle
      (raises :class:`InvalidReconTransitionError` — cross-vehicle
      links are structurally prohibited).

    Preconditions on the WorkOrder:

    - Status must be ``draft`` — attach/detach is a plan-time
      operation. Raises :class:`InvalidReconTransitionError`
      otherwise.

    Duplicate handling:

    - Duplicate finding IDs in the input list are deduplicated
      silently before validation (an operator UI double-click
      submitting the same finding twice is not an error).
    - Finding IDs that already have a link (from a prior call)
      are skipped silently — only missing rows are created.
    - Return value is a list of the actual link rows for the
      requested findings, ordered deterministically by
      ``finding_id`` so callers get a stable render order.
    """
    _assert_work_order_tenant(work_order, dealership)

    # Deduplicate input while preserving deterministic order.
    unique_ids = sorted({int(fid) for fid in finding_ids})
    if not unique_ids:
        return []

    with transaction.atomic():
        wo = (
            WorkOrder.objects.select_for_update()
            .select_related("vehicle")
            .get(pk=work_order.pk)
        )
        if wo.status != WORK_ORDER_STATUS_DRAFT:
            raise InvalidReconTransitionError(
                f"Cannot attach findings to WorkOrder #{wo.pk}: status "
                f"is {wo.status!r}. Attach/detach is a draft-only "
                "operation. To modify the finding set of an approved "
                "WorkOrder, cancel it and create a new one."
            )

        # Pull all requested findings in one query; missing IDs are
        # a caller error (cross-tenant guard also catches them by
        # dealership mismatch, but a stale ID from a deleted finding
        # is a distinct case).
        findings_by_id = {
            f.pk: f
            for f in ConditionFinding.objects.select_related(
                "report", "report__vehicle"
            ).filter(pk__in=unique_ids)
        }
        missing = [fid for fid in unique_ids if fid not in findings_by_id]
        if missing:
            raise InvalidReconTransitionError(
                f"attach_findings: ConditionFinding ID(s) {missing} do "
                "not exist. No links were created."
            )

        # Validate all findings before writing anything.
        for fid in unique_ids:
            finding = findings_by_id[fid]
            _assert_finding_tenant(finding, dealership)
            if finding.report.status != CONDITION_REPORT_STATUS_COMPLETE:
                raise IncompleteConditionReportError(
                    f"attach_findings: ConditionFinding #{fid} belongs "
                    f"to ConditionReport #{finding.report_id} which is "
                    f"in status {finding.report.status!r}. Findings can "
                    "only be linked from completed inspection reports."
                )
            if finding.report.vehicle_id != wo.vehicle_id:
                raise InvalidReconTransitionError(
                    f"attach_findings: ConditionFinding #{fid} belongs "
                    f"to Vehicle #{finding.report.vehicle_id}, not "
                    f"WorkOrder's Vehicle #{wo.vehicle_id}. Cross-"
                    "vehicle links are not permitted (planning §1.4)."
                )

        # Look up existing links so we only create missing rows.
        existing_ids = set(
            WorkOrderFinding.objects.filter(
                work_order=wo, finding_id__in=unique_ids
            ).values_list("finding_id", flat=True)
        )
        to_create_ids = [fid for fid in unique_ids if fid not in existing_ids]

        created: list[WorkOrderFinding] = []
        for fid in to_create_ids:
            link = WorkOrderFinding(
                work_order=wo,
                finding=findings_by_id[fid],
                dealership=dealership,
            )
            link.full_clean()
            try:
                link.save()
            except IntegrityError:
                # Racy re-attach — another call just created this
                # link. The goal state is achieved either way; move
                # on so the caller sees the link in the returned set.
                pass
            created.append(link)

        # Return the deterministic set of link rows for the
        # requested findings (both freshly created and previously
        # existing).
        return list(
            WorkOrderFinding.objects.filter(
                work_order=wo, finding_id__in=unique_ids
            ).order_by("finding_id")
        )


def detach_finding(
    work_order: WorkOrder,
    finding: ConditionFinding,
    *,
    dealership: Dealership,
) -> None:
    """Remove the link between a WorkOrder and a ConditionFinding.

    Draft-only per planning §1.4 workflow rule: once the WorkOrder
    has been approved, its finding set is part of the authorized
    scope and the through-table row is history.

    Raises :class:`InvalidReconTransitionError` when the link
    does not exist, so the caller can distinguish "already
    detached" (which is not necessarily an error at their level)
    from "cannot detach". Alternative "silent no-op if link is
    already gone" was considered and rejected — callers explicitly
    invoking detach should hear back if the operation was a no-op.
    """
    _assert_work_order_tenant(work_order, dealership)
    _assert_finding_tenant(finding, dealership)

    with transaction.atomic():
        wo = WorkOrder.objects.select_for_update().get(pk=work_order.pk)
        if wo.status != WORK_ORDER_STATUS_DRAFT:
            raise InvalidReconTransitionError(
                f"Cannot detach finding from WorkOrder #{wo.pk}: status "
                f"is {wo.status!r}. Detach is a draft-only operation."
            )
        deleted, _ = WorkOrderFinding.objects.filter(
            work_order=wo, finding=finding
        ).delete()
        if deleted == 0:
            raise InvalidReconTransitionError(
                f"detach_finding: no WorkOrderFinding link exists for "
                f"WorkOrder #{wo.pk} and ConditionFinding #{finding.pk}."
            )


# ---- Transition helpers ---------------------------------------------------


def _load_for_transition(work_order: WorkOrder) -> WorkOrder:
    """``SELECT ... FOR UPDATE`` the WorkOrder row inside the
    caller's transaction so the from-state check sees committed
    data and no other transaction can flip the status underneath
    the transition.

    The caller is responsible for wrapping in
    ``transaction.atomic()``. This helper only performs the lock
    + fresh read.
    """
    return WorkOrder.objects.select_for_update().get(pk=work_order.pk)


# ---- Ledger integration (M4.3) --------------------------------------------


def _ledger_category_for(work_order: WorkOrder) -> str:
    """Map ``WorkOrder.category`` to the VehicleCost category the
    ledger row is posted under. See
    :data:`_WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY` for the full
    mapping table + rationale."""
    return _WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY[work_order.category]


def _vendor_snapshot(work_order: WorkOrder) -> str:
    """Return the vendor-name snapshot for the ``VehicleCost.vendor``
    free-text field. Planning §5.b Option C locks the invariant:
    the name at posting time is the immutable snapshot; a later
    vendor rename does not rewrite historical rows."""
    return work_order.vendor.name if work_order.vendor is not None else ""


def _outstanding_estimate_amount(work_order: WorkOrder) -> Decimal:
    """Return the current signed sum of every estimate + reversal
    row previously posted for ``work_order``.

    All families that carry ``is_estimate=True`` contribute:
    ``estimate:<seq>`` (positive), ``estimate_reversal:<seq>``
    (negative), ``completion_estimate_reversal`` (negative), and
    ``estimate_reversal:cancel`` (negative). The ``actual`` family
    is ``is_estimate=False`` and does not contribute.

    Returns :data:`_ZERO` when no estimate rows have been posted
    (avoids Django's aggregate-returns-``None`` case)."""
    prefix = f"WORKORDER:{work_order.pk}:"
    result = (
        VehicleCost.objects.filter(
            vehicle=work_order.vehicle,
            dealership=work_order.dealership,
            is_estimate=True,
            reference__startswith=prefix,
        )
        .aggregate(total=Sum("amount"))
        .get("total")
    )
    return result if result is not None else _ZERO


def _next_estimate_seq(work_order: WorkOrder) -> int:
    """Return the next sequential number for an estimate posting.

    Reads all existing ``WORKORDER:{wo.pk}:estimate:*`` references
    and returns ``max(seq) + 1``. Starts at 1 for a WorkOrder with
    no prior estimate."""
    prefix = f"WORKORDER:{work_order.pk}:estimate:"
    existing = VehicleCost.objects.filter(
        reference__startswith=prefix,
        dealership=work_order.dealership,
    ).values_list("reference", flat=True)
    max_seq = 0
    for ref in existing:
        # Reference format is ``WORKORDER:<pk>:estimate:<seq>``.
        # Skip ``estimate_reversal:*`` — the prefix filter above
        # matches ``estimate:`` exactly so reversal rows never
        # appear in this iterator.
        try:
            seq = int(ref.rsplit(":", 1)[-1])
        except (ValueError, IndexError):
            continue
        if seq > max_seq:
            max_seq = seq
    return max_seq + 1


def _post_estimate(
    work_order: WorkOrder, *, seq: int, actor=None
) -> Optional[VehicleCost]:
    """Post an initial or revised estimate row.

    Idempotent — if the resolved reference already exists, returns
    ``None`` without a second insert. Returns ``None`` also when
    ``work_order.estimated_cost`` is ``None`` (nothing to estimate).
    """
    if work_order.estimated_cost is None:
        return None
    reference = WORKORDER_LEDGER_REF_ESTIMATE.format(
        wo_id=work_order.pk, seq=seq
    )
    if VehicleCost.objects.filter(reference=reference).exists():
        return None
    return _add_cost(
        work_order.vehicle,
        dealership=work_order.dealership,
        category=_ledger_category_for(work_order),
        amount=work_order.estimated_cost,
        incurred_at=timezone.now(),
        vendor=_vendor_snapshot(work_order),
        reference=reference,
        is_estimate=True,
        created_by=actor,
    )


def _post_estimate_reversal(
    work_order: WorkOrder, *, outstanding_amount: Decimal, seq: int, actor=None
) -> Optional[VehicleCost]:
    """Post a mid-life estimate-reversal row (matches a prior
    ``estimate:<seq>``). Called from :func:`revise_estimate`.

    Idempotent — returns ``None`` if the resolved reference already
    exists. Returns ``None`` when ``outstanding_amount`` is zero
    (nothing to reverse)."""
    if outstanding_amount == _ZERO:
        return None
    reference = WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL.format(
        wo_id=work_order.pk, seq=seq
    )
    if VehicleCost.objects.filter(reference=reference).exists():
        return None
    return _add_cost(
        work_order.vehicle,
        dealership=work_order.dealership,
        category=_ledger_category_for(work_order),
        amount=-outstanding_amount,
        incurred_at=timezone.now(),
        vendor=_vendor_snapshot(work_order),
        reference=reference,
        is_estimate=True,
        created_by=actor,
    )


def _post_completion_reversal(
    work_order: WorkOrder, *, outstanding_amount: Decimal, actor=None
) -> Optional[VehicleCost]:
    """Post the one-shot completion-time estimate reversal that
    retires the outstanding estimate atomically with the actual
    (SESSION_066 refinement — see planning §5.e). Called only from
    :func:`complete_work_order`.

    Idempotent via the one-shot reference; returns ``None`` on
    replay. Returns ``None`` when ``outstanding_amount`` is zero
    (WorkOrder had no outstanding estimate — a legitimate case for
    WOs completed without a prior estimate)."""
    if outstanding_amount == _ZERO:
        return None
    reference = WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL.format(
        wo_id=work_order.pk
    )
    if VehicleCost.objects.filter(reference=reference).exists():
        return None
    return _add_cost(
        work_order.vehicle,
        dealership=work_order.dealership,
        category=_ledger_category_for(work_order),
        amount=-outstanding_amount,
        incurred_at=timezone.now(),
        vendor=_vendor_snapshot(work_order),
        reference=reference,
        is_estimate=True,
        created_by=actor,
    )


def _post_cancel_reversal(
    work_order: WorkOrder, *, outstanding_amount: Decimal, actor=None
) -> Optional[VehicleCost]:
    """Post the cancellation-time estimate reversal. Called only
    from :func:`cancel_work_order`. Preserves any partial actual
    row posted before cancellation — it represents work truly
    performed and stays on the ledger."""
    if outstanding_amount == _ZERO:
        return None
    reference = WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL.format(
        wo_id=work_order.pk
    )
    if VehicleCost.objects.filter(reference=reference).exists():
        return None
    return _add_cost(
        work_order.vehicle,
        dealership=work_order.dealership,
        category=_ledger_category_for(work_order),
        amount=-outstanding_amount,
        incurred_at=timezone.now(),
        vendor=_vendor_snapshot(work_order),
        reference=reference,
        is_estimate=True,
        created_by=actor,
    )


def _post_actual(
    work_order: WorkOrder, *, actor=None
) -> Optional[VehicleCost]:
    """Post the actual-cost row on WorkOrder completion. Called
    only from :func:`complete_work_order` (inside the same
    ``transaction.atomic()`` block as :func:`_post_completion_reversal`
    so a mid-completion crash leaves the ledger untouched).

    Idempotent via the ``actual`` reference; returns ``None`` on
    replay. Uses the WorkOrder's ``actual_completion_date`` for
    ``incurred_at`` if set; falls back to ``now()`` otherwise
    (should never happen — ``complete_work_order`` sets the date
    unconditionally)."""
    reference = WORKORDER_LEDGER_REF_ACTUAL.format(wo_id=work_order.pk)
    if VehicleCost.objects.filter(reference=reference).exists():
        return None
    if work_order.actual_completion_date is not None:
        incurred_at = timezone.make_aware(
            timezone.datetime.combine(
                work_order.actual_completion_date,
                timezone.datetime.min.time(),
            ),
            timezone.get_current_timezone(),
        )
    else:
        incurred_at = timezone.now()
    return _add_cost(
        work_order.vehicle,
        dealership=work_order.dealership,
        category=_ledger_category_for(work_order),
        amount=work_order.actual_cost,
        incurred_at=incurred_at,
        vendor=_vendor_snapshot(work_order),
        reference=reference,
        is_estimate=False,
        created_by=actor,
    )


# ---- Approve --------------------------------------------------------------


def approve_work_order(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    approved_by,
    authorized_cost=None,
) -> WorkOrder:
    """Transition a draft WorkOrder to approved.

    Preconditions:

    - ``work_order.status == 'draft'`` (or ``'approved'`` for the
      idempotent re-approve path — see below).
    - At least one linked finding
      (``work_order.finding_links.count() >= 1``). No-finding
      approvals are refused per module-docstring "Approval requires
      at least one linked finding" policy. Raises
      :class:`InvalidReconTransitionError` otherwise.
    - Structural M4.1 clean guards (outsourced-requires-vendor,
      vendor-tenant match) surface via ``full_clean()``.

    Effects on the draft → approved path:

    - Sets ``status='approved'``.
    - Sets ``approved_by`` to the supplied user.
    - Sets ``approved_at = timezone.now()``.
    - Sets ``authorized_cost`` if supplied.
    - **Posts an estimate row** via :func:`_post_estimate` when
      ``estimated_cost`` is non-null (M4.3). Reference key
      ``WORKORDER:<id>:estimate:1``. Idempotent via reference
      lookup — a race that produces two entries to this branch
      for the same WO writes at most one estimate.

    Effects on the approved → approved idempotent re-approve path:

    - Refreshes ``approved_at`` (audit trail).
    - **Preserves the original `approved_by`** — the first-time
      approver is the historical fact.
    - Updates ``authorized_cost`` if supplied.
    - Does **not** post an estimate revision. Estimate revisions
      go through :func:`revise_estimate` — a separate operator
      gesture with distinct audit semantics.

    Rejects every other from-state as :class:`InvalidReconTransitionError`.
    """
    _assert_work_order_tenant(work_order, dealership)

    with transaction.atomic():
        wo = _load_for_transition(work_order)

        if wo.status == WORK_ORDER_STATUS_APPROVED:
            # Idempotent re-approve — refresh audit timestamp,
            # preserve original approver, permit authorized_cost
            # update. Does NOT post estimate revision; call
            # ``revise_estimate`` for that.
            wo.approved_at = timezone.now()
            if authorized_cost is not None:
                wo.authorized_cost = authorized_cost
            wo.full_clean()
            wo.save()
            return wo

        if wo.status != WORK_ORDER_STATUS_DRAFT:
            raise InvalidReconTransitionError(
                f"Cannot approve WorkOrder #{wo.pk}: current status is "
                f"{wo.status!r}. Approval is allowed only from 'draft' "
                "(first-time) or 'approved' (idempotent refinement)."
            )

        if wo.finding_links.count() == 0:
            raise InvalidReconTransitionError(
                f"Cannot approve WorkOrder #{wo.pk}: no ConditionFinding "
                "links exist. WorkOrders must reference at least one "
                "finding (planning §1.4 back-traceability). Call "
                "``attach_findings`` before approving."
            )

        wo.status = WORK_ORDER_STATUS_APPROVED
        wo.approved_by = approved_by
        wo.approved_at = timezone.now()
        if authorized_cost is not None:
            wo.authorized_cost = authorized_cost
        wo.full_clean()
        wo.save()

        # Post the initial estimate row (M4.3). Inside the same
        # transaction so a mid-approve crash leaves neither the
        # WorkOrder row nor the ledger row. ``_post_estimate``
        # returns None when ``estimated_cost`` is null (nothing
        # to estimate) — WorkOrders without an estimate approve
        # cleanly and post no ledger row.
        _post_estimate(wo, seq=_next_estimate_seq(wo), actor=approved_by)

        return wo


# ---- Revise estimate (M4.3) -----------------------------------------------


def revise_estimate(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    new_estimated_cost: Decimal,
    revised_by=None,
) -> WorkOrder:
    """Revise the estimated cost on an already-approved WorkOrder.

    Separate operator gesture from re-approval per M4.3 semantic:
    approval is about *authorizing* the work; estimate revision is
    about *re-pricing* it after new information (a vendor quote
    came back higher, parts turned out to be back-ordered at a
    premium, etc.). Both keep the WorkOrder in ``approved`` status;
    the WO does not fall back to ``draft`` when the estimate
    changes.

    Preconditions:

    - Current status must be ``approved``. Raises
      :class:`InvalidReconTransitionError` from any other
      state — an in_progress WO's next number is the actual, not a
      re-estimate; a draft WO has never posted an estimate to
      revise.
    - ``new_estimated_cost`` must be nonnegative Decimal (raises
      :class:`ValueError` on negative). A nonzero revision is
      required to change anything; passing the same value is a
      no-op that returns the WO unchanged.

    Effects:

    - Posts an estimate reversal for the current outstanding
      amount under ``WORKORDER:<id>:estimate_reversal:<seq>``
      where ``seq`` matches the estimate being reversed.
    - Posts a new estimate under
      ``WORKORDER:<id>:estimate:<seq+1>``.
    - Updates ``work_order.estimated_cost`` to the new value.
    - Both ledger posts happen inside the same
      ``transaction.atomic()`` block so a mid-revision crash
      leaves the ledger untouched.

    Idempotent — a repeated call with the same
    ``new_estimated_cost`` passes through as a no-op (the outstanding
    already matches the new value).
    """
    _assert_work_order_tenant(work_order, dealership)

    new_estimated_cost = Decimal(new_estimated_cost)
    if new_estimated_cost < 0:
        raise ValueError(
            f"revise_estimate: new_estimated_cost must be nonnegative "
            f"(got {new_estimated_cost}). Negative amounts are for "
            "reversing entries and are not accepted as an estimate."
        )

    with transaction.atomic():
        wo = _load_for_transition(work_order)
        if wo.status != WORK_ORDER_STATUS_APPROVED:
            raise InvalidReconTransitionError(
                f"Cannot revise estimate on WorkOrder #{wo.pk}: "
                f"current status is {wo.status!r}. Estimate revision "
                "is allowed only from 'approved'."
            )

        outstanding = _outstanding_estimate_amount(wo)
        if outstanding == new_estimated_cost:
            # Nothing to change. Idempotent no-op.
            return wo

        # Post reversal for whatever was outstanding, using the
        # sequence of the estimate being reversed. Then post the
        # new estimate at the next sequence.
        next_seq = _next_estimate_seq(wo)
        # The reversal seq matches the estimate being reversed —
        # i.e., the max existing seq (which is ``next_seq - 1``).
        # Guard against the edge case where nothing was ever
        # posted: outstanding == 0 handles it via the helper.
        reversal_seq = max(next_seq - 1, 1)
        _post_estimate_reversal(
            wo,
            outstanding_amount=outstanding,
            seq=reversal_seq,
            actor=revised_by,
        )

        wo.estimated_cost = new_estimated_cost
        wo.full_clean()
        wo.save()

        _post_estimate(wo, seq=next_seq, actor=revised_by)
        return wo


# ---- Start ----------------------------------------------------------------


def start_work_order(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    started_by,
) -> WorkOrder:
    """Transition an approved WorkOrder to in_progress.

    One-way (planning §5.c): approved → in_progress only. Repeated
    starts on an already-in_progress WO raise
    :class:`InvalidReconTransitionError`. Sets ``started_by`` +
    ``started_at`` exactly once.

    Preserves ``approved_by`` / ``approved_at`` — the earlier
    provenance is history.

    Does **not** post any ledger row (M4.3).
    """
    _assert_work_order_tenant(work_order, dealership)

    with transaction.atomic():
        wo = _load_for_transition(work_order)
        if wo.status != WORK_ORDER_STATUS_APPROVED:
            raise InvalidReconTransitionError(
                f"Cannot start WorkOrder #{wo.pk}: current status is "
                f"{wo.status!r}. Start is allowed only from 'approved'."
            )
        wo.status = WORK_ORDER_STATUS_IN_PROGRESS
        wo.started_by = started_by
        wo.started_at = timezone.now()
        wo.full_clean()
        wo.save()
        return wo


# ---- Complete -------------------------------------------------------------


def complete_work_order(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    completed_by,
    actual_cost,
    actual_completion_date=None,
) -> WorkOrder:
    """Transition an in-progress WorkOrder to completed.

    Preconditions:

    - Current status is ``in_progress`` (planning §5.c does not
      list ``approved → completed`` as a direct transition; an
      explicit start is required). Raises
      :class:`InvalidReconTransitionError` otherwise.
    - ``actual_cost`` is supplied and nonnegative. Negative costs
      are for reversing entries (M4.3), not for actual work
      completions. Raises :class:`ValueError` on negative or
      missing.

    Effects:

    - Sets ``status='completed'``.
    - Sets ``actual_cost = Decimal(actual_cost)``.
    - Sets ``actual_completion_date`` to the supplied value or
      today's date if omitted.
    - Sets ``completed_by`` + ``completed_at``.
    - Preserves ``approved_by`` / ``approved_at`` /
      ``started_by`` / ``started_at`` — earlier provenance is
      history.
    - **Posts the completion-time estimate reversal + the actual
      cost row** atomically inside the same
      ``transaction.atomic()`` block as the WorkOrder save
      (M4.3). The reversal retires any outstanding estimate;
      the actual carries the final cost. After the transaction
      commits, the net estimate contribution for the WO is
      ``Decimal("0.00")`` and ``projected_total_investment``
      no longer double-counts the completed WO (SESSION_066
      refinement — planning §5.e).
    - Does **not** claim QC verification. Per the SESSION_067
      QC-GAP annotation in ``MILESTONE_4_PLANNING.md`` §1.0,
      completion timestamps prove *when work was marked complete*,
      not *whether it was verified*. There is no ``qc_verified``
      parameter and no QC field is set. A future increment may
      add a ``QcVerification`` model or fields (see Path A / B
      in the QC-GAP annotation); until then, do not infer
      verification from completion.
    """
    _assert_work_order_tenant(work_order, dealership)

    if actual_cost is None:
        raise ValueError(
            "complete_work_order: actual_cost is required. Negative "
            "amounts are reserved for M4.3 reversing entries; supply "
            "a nonnegative Decimal for the actual completion cost."
        )
    actual_cost_decimal = Decimal(actual_cost)
    if actual_cost_decimal < 0:
        raise ValueError(
            f"complete_work_order: actual_cost must be nonnegative "
            f"(got {actual_cost_decimal}). Negative amounts are for "
            "M4.3 reversing entries."
        )

    with transaction.atomic():
        wo = _load_for_transition(work_order)
        if wo.status != WORK_ORDER_STATUS_IN_PROGRESS:
            raise InvalidReconTransitionError(
                f"Cannot complete WorkOrder #{wo.pk}: current status "
                f"is {wo.status!r}. Completion is allowed only from "
                "'in_progress'. Call ``start_work_order`` first if "
                "the WO is still 'approved'."
            )
        wo.status = WORK_ORDER_STATUS_COMPLETED
        wo.actual_cost = actual_cost_decimal
        wo.actual_completion_date = (
            actual_completion_date
            if actual_completion_date is not None
            else timezone.now().date()
        )
        wo.completed_by = completed_by
        wo.completed_at = timezone.now()
        wo.full_clean()
        wo.save()

        # Ledger: atomically post the completion-time estimate
        # reversal + the actual cost row. Both inside the same
        # ``transaction.atomic()`` block as the WorkOrder save so
        # a mid-completion crash leaves the ledger untouched
        # (SESSION_066 refinement — planning §5.e). Both helpers
        # are idempotent via reference lookup so replay is safe.
        outstanding = _outstanding_estimate_amount(wo)
        _post_completion_reversal(
            wo, outstanding_amount=outstanding, actor=completed_by
        )
        _post_actual(wo, actor=completed_by)

        return wo


# ---- Cancel ---------------------------------------------------------------


def cancel_work_order(
    work_order: WorkOrder,
    *,
    dealership: Dealership,
    cancelled_by,
    cancellation_reason: str = "",
) -> WorkOrder:
    """Transition a nonterminal WorkOrder to cancelled.

    Allowed from ``draft``, ``approved``, and ``in_progress``.
    Raises :class:`InvalidReconTransitionError` from ``completed``
    or ``cancelled`` — terminal states are terminal.

    ``cancellation_reason`` requirements (SESSION_067 policy):

    - ``draft → cancelled`` — reason optional. Cancelling a draft
      costs nothing operationally.
    - ``approved / in_progress → cancelled`` — nonblank reason
      required. A vendor was told the work was authorized (or
      started); the audit trail deserves the operator's stated
      reason. Raises :class:`ValueError` if the reason is blank
      or whitespace-only.

    Effects:

    - Sets ``status='cancelled'``.
    - Sets ``cancelled_by`` + ``cancelled_at``.
    - Sets ``cancellation_reason``.
    - Preserves all earlier provenance (approved / started /
      completed pairs remain untouched — a cancelled-after-start
      WO retains its start actor and timestamp so the timeline
      is legible).
    - **Reverses any outstanding estimate** via
      :func:`_post_cancel_reversal` (M4.3). Preserves any
      partial actual row posted before cancel (they represent
      work truly performed and stay on the ledger). Idempotent
      via reference lookup.
    """
    _assert_work_order_tenant(work_order, dealership)

    with transaction.atomic():
        wo = _load_for_transition(work_order)
        if wo.status not in _OPEN_STATUSES:
            raise InvalidReconTransitionError(
                f"Cannot cancel WorkOrder #{wo.pk}: current status is "
                f"{wo.status!r}. Cancellation is allowed only from "
                "nonterminal states (draft / approved / in_progress)."
            )
        if wo.status in {
            WORK_ORDER_STATUS_APPROVED,
            WORK_ORDER_STATUS_IN_PROGRESS,
        }:
            if not (cancellation_reason or "").strip():
                raise ValueError(
                    f"cancel_work_order: cancellation_reason is required "
                    f"when cancelling from status {wo.status!r}. A "
                    "nonblank reason must be supplied for the audit "
                    "trail once work has been authorized."
                )

        wo.status = WORK_ORDER_STATUS_CANCELLED
        wo.cancelled_by = cancelled_by
        wo.cancelled_at = timezone.now()
        wo.cancellation_reason = cancellation_reason
        wo.full_clean()
        wo.save()

        # Ledger: reverse any outstanding estimate. Preserves any
        # partial actual posted before cancellation (M4 v1 does not
        # have a partial-actual path, but the invariant is
        # documented at planning §5.e so a future partial-completion
        # workflow can rely on it). Idempotent via reference lookup.
        outstanding = _outstanding_estimate_amount(wo)
        _post_cancel_reversal(
            wo, outstanding_amount=outstanding, actor=cancelled_by
        )

        return wo


# ---- Vehicle read helpers -------------------------------------------------


def open_work_orders_for_vehicle(
    vehicle: Vehicle, *, dealership: Dealership
):
    """Return a queryset of open WorkOrder rows for ``vehicle``.

    "Open" means ``status`` is one of ``draft``, ``approved``, or
    ``in_progress`` — terminal states are excluded. Deterministic
    ordering by ``-created_at`` matches the M4.1 model's
    ``Meta.ordering`` so the M4.7 operator UI renders in a stable
    order.

    Backing implementation for :attr:`Vehicle.open_work_orders`
    (planning §1.7).
    """
    _assert_vehicle_tenant(vehicle, dealership)
    return (
        WorkOrder.objects.filter(vehicle=vehicle, dealership=dealership)
        .filter(status__in=_OPEN_STATUSES)
        .order_by("-created_at")
    )


def has_recon_decisions_for_vehicle(
    vehicle: Vehicle, *, dealership: Dealership
) -> bool:
    """Return ``True`` iff ``vehicle`` has a latest completed
    condition report AND at least one recon decision has been
    recorded against a finding on that report.

    Cheap: uses ``.exists()`` — does not load any Finding or
    ReconDecision instance into memory. Backing implementation
    for :attr:`Vehicle.has_recon_decisions` (planning §1.7).
    """
    _assert_vehicle_tenant(vehicle, dealership)
    latest = _latest_completed_condition_report(vehicle, dealership=dealership)
    if latest is None:
        return False
    return ReconDecision.objects.filter(
        finding__report=latest, dealership=dealership
    ).exists()
