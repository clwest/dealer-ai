"""Milestone 5 · Increment 2 — vehicle-lifecycle service layer.

The one place all vehicle-stage transitions and lifecycle bootstrapping
happen. Answers the M5 business questions at the business-logic layer:

- *"What stage is this vehicle in right now?"* —
  :func:`get_current_stage` (pure read; may return ``None``).
- *"Is this vehicle currently retail-eligible?"* —
  :func:`retail_eligible` (pure read; ``False`` when no stage row
  exists).
- *"Move this vehicle to a new stage; record who authorized it and
  why."* — :func:`advance_stage`.
- *"Make sure this vehicle has a stage row; if none exists, seed
  one."* — :func:`ensure_current_stage` (explicit mutating op).
- *"Which transitions could fire automatically right now?"* —
  :func:`suggest_transitions` (signature only in M5.2 — every rule
  returns ``None`` until M5.3 lands the rule bodies).
- *"When returning from ``hold_reserved``, what was the previous
  retail-preparation stage?"* —
  :func:`resolve_hold_reserved_return_target` (walks the event log,
  never parses ``notes`` free text).

The service writes ``VehicleStage`` and ``VehicleStageEvent`` rows.
It does NOT:

- Draft or send any AI content (no LLM integration).
- Expose HTTP endpoints or enforce DRF permissions — M5.4.
- Refactor retail-side queries — M5.5.
- Touch any frontend — M5.6.
- Ship deterministic rule bodies — M5.3 fills
  :func:`suggest_transitions`.

Layer discipline (per :doc:`AUTHENTICATION_MODEL.md` §1):

- **Identity + tenant resolution** — view layer.
- **DRF permission (broad admission)** — M5.4 endpoint permission
  classes admit the request or return 403.
- **Data-scoping** — this module. Every public function accepts an
  explicit ``dealership`` kwarg and refuses to touch rows in any
  other tenant. Belt to the M5.1 model layer's ``clean()``
  suspenders.
- **Per-transition role authority** — this module. Fine-grained
  role gating happens HERE (raises
  :class:`UnauthorizedStageTransitionError`), not at the DRF
  permission layer, so the same endpoint can admit
  ``recon_manager`` for retail-prep transitions but refuse the
  same user's attempt to move a vehicle into ``hold_reserved`` /
  ``wholesale_out`` / ``company_use`` / ``off_market``.
- **Business semantics** — this module. Transition table
  membership, no-op refusal, cross-tenant refusal, and atomic
  stage + event writes are locked here and tested.

Semantic decisions locked here (per
``MILESTONE_5_PLANNING.md`` §5.b + §5.f, SESSION_075 refined):

- **No hidden writes from Vehicle read-model properties**
  (SESSION_075 §0.a item 6). :func:`get_current_stage` and
  :func:`retail_eligible` are pure reads; they never bootstrap.
  The mutating side lives in :func:`ensure_current_stage` — an
  explicit verb callers invoke deliberately (migration bootstrap,
  future write-path integration in M5.5).

- **Every allowed transition is manual in M5** (per §5.h
  SESSION_075 refinement). ``listing → frontline`` is manual-only
  in M5; M6 later adds the deterministic published-listing rule
  once ``VehicleListing.published`` exists. Deterministic rules
  for ``inspection → recon`` and ``recon → qc`` land at M5.3 as
  *suggestions* the operator explicitly accepts via the M5.4
  endpoint. No auto-application in M5.

- **Distinct domain errors — DO NOT overload.** The four errors
  map to four different HTTP status codes at the M5.4 endpoint
  layer:
  - :class:`CrossTenantLifecycleError` → 404 (fail-closed).
  - :class:`InvalidStageTransitionError` → 409 (structurally
    illegal from/to per the allowed table).
  - :class:`UnauthorizedStageTransitionError` → 403 (valid
    transition attempted by the wrong role).
  - :class:`StageAlreadyCurrentError` → 409 (no-op refused so
    callers can distinguish "already there" from "moved").

- **``hold_reserved → previous stage`` reads the event log**
  (SESSION_075 §0.a item 2). :func:`resolve_hold_reserved_return_target`
  walks the most recent ``VehicleStageEvent`` whose
  ``to_stage=="hold_reserved"`` and returns its ``from_stage``.
  It NEVER parses ``notes`` free text — the durable record is
  the event log.

- **No auto-transition on M4 substrate writes.** The service
  never subscribes to ``post_save`` signals on ``WorkOrder`` or
  ``ConditionReport`` — per §5.h Option A for M5 v1, all
  deterministic rules are on-demand only via
  :func:`suggest_transitions`.

- **``advance_stage`` calls ``ensure_current_stage`` first inside
  the transaction.** Defense-in-depth: if a future write path
  introduces a Vehicle without seeding a stage row, the very next
  ``advance_stage`` call still works (creates a fresh
  ``incoming`` stage + bootstrap event, then transitions from
  there). The transition table's from-side then determines
  whether the requested ``to_stage`` is reachable.

Concurrency posture:

- ``advance_stage`` uses ``transaction.atomic()`` +
  ``select_for_update()`` on the target ``VehicleStage`` row so
  two concurrent transitions cannot both succeed against the
  same row and produce contradictory current-stage state.
- ``ensure_current_stage`` runs its create-if-missing check
  inside ``transaction.atomic()`` + ``select_for_update()`` on
  the paired Vehicle row so two concurrent bootstrap calls
  cannot both insert a stage row (the second one sees the first
  and returns it).
- No distributed-locking framework is introduced — Django's
  row-level lock via ``select_for_update`` is sufficient for the
  single-DB deployment M5 targets, mirroring the M4.2 recon
  service concurrency posture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from django.db import transaction
from django.db.models import Exists, OuterRef, QuerySet
from django.utils import timezone

from ..models import (
    CONDITION_SEVERITY_RECOMMENDED,
    CONDITION_SEVERITY_REQUIRED,
    CONDITION_SEVERITY_SAFETY,
    Dealership,
    RECON_DECISION_TIER_MUST_DO,
    ROLE_DEALER_OWNER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    UserDealershipRole,
    VEHICLE_STAGE_CHOICES,
    VEHICLE_STAGE_COMPANY_USE,
    VEHICLE_STAGE_DETAIL,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_HOLD_RESERVED,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_LISTING,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_PHOTOGRAPHY,
    VEHICLE_STAGE_QC,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    VEHICLE_STAGE_TRIGGER_CHOICES,
    VEHICLE_STAGE_WHOLESALE_OUT,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
    WORK_ORDER_STATUS_COMPLETED,
    WorkOrderFinding,
)


_VALID_STAGE_KEYS = frozenset(key for key, _ in VEHICLE_STAGE_CHOICES)
_VALID_TRIGGER_KEYS = frozenset(key for key, _ in VEHICLE_STAGE_TRIGGER_CHOICES)


# ----------------------------------------------------------------------------
# Transition table — MILESTONE_5_PLANNING.md §5.b (SESSION_075 refined).
#
# Retail-preparation forward chain + operational escapes from any
# non-terminal retail stage (including frontline) + escape returns.
# Every transition is manually advanceable; deterministic
# suggestions for a subset are added in M5.3 without changing the
# structural allow-list here.
#
# ``sold`` deliberately absent per §5.a — M9 adds it alongside the
# ``Sale`` model.
# ----------------------------------------------------------------------------

# Retail pipeline — the 8 stages the user calls "retail-preparation
# pipeline" in §5.a (7 preparation stages + frontline as the terminal
# retail-eligible state). Named ``_RETAIL_PREPARATION_STAGES`` for
# continuity with §5.b language ("previous retail-preparation stage"),
# but the set includes ``frontline`` because a vehicle held (via
# ``frontline → hold_reserved``) should resolve its return target to
# ``frontline`` — the operator's intent is "return the vehicle to
# what it was doing before the hold."
_RETAIL_PREPARATION_STAGES = frozenset(
    {
        VEHICLE_STAGE_INCOMING,
        VEHICLE_STAGE_INSPECTION,
        VEHICLE_STAGE_RECON,
        VEHICLE_STAGE_QC,
        VEHICLE_STAGE_DETAIL,
        VEHICLE_STAGE_PHOTOGRAPHY,
        VEHICLE_STAGE_LISTING,
        VEHICLE_STAGE_FRONTLINE,
    }
)

# Operational-disposition target stages (§5.f — gated to owner + sales
# manager only; recon_manager cannot transition into any of them).
_COMMERCIAL_DISPOSITION_STAGES = frozenset(
    {
        VEHICLE_STAGE_HOLD_RESERVED,
        VEHICLE_STAGE_WHOLESALE_OUT,
        VEHICLE_STAGE_COMPANY_USE,
        VEHICLE_STAGE_OFF_MARKET,
    }
)


def _build_allowed_transitions() -> dict[str, frozenset[str]]:
    """Assemble the full transition table from the three per-§5.b
    building blocks. Kept as a module-init function so the table is
    testable end-to-end (a change to the taxonomy would surface in
    the assertion set)."""
    table: dict[str, set[str]] = {}

    # Retail-preparation forward chain.
    forward_chain = [
        (VEHICLE_STAGE_INCOMING, VEHICLE_STAGE_INSPECTION),
        (VEHICLE_STAGE_INSPECTION, VEHICLE_STAGE_RECON),
        (VEHICLE_STAGE_RECON, VEHICLE_STAGE_QC),
        (VEHICLE_STAGE_QC, VEHICLE_STAGE_DETAIL),
        (VEHICLE_STAGE_QC, VEHICLE_STAGE_PHOTOGRAPHY),  # detail-collapse
        (VEHICLE_STAGE_DETAIL, VEHICLE_STAGE_PHOTOGRAPHY),
        (VEHICLE_STAGE_PHOTOGRAPHY, VEHICLE_STAGE_LISTING),
        (VEHICLE_STAGE_LISTING, VEHICLE_STAGE_FRONTLINE),
    ]
    for src, tgt in forward_chain:
        table.setdefault(src, set()).add(tgt)

    # Operational escapes from any retail-preparation stage AND from
    # frontline (§5.b — post-frontline operational transitions).
    escape_sources = _RETAIL_PREPARATION_STAGES | {VEHICLE_STAGE_FRONTLINE}
    for src in escape_sources:
        for tgt in _COMMERCIAL_DISPOSITION_STAGES:
            table.setdefault(src, set()).add(tgt)

    # Escape returns.
    # hold_reserved returns are dynamic — the target is the previous
    # retail-preparation stage resolved from the event log. Encode a
    # permissive allow-list at the structural layer: any
    # retail-preparation stage is a legal return target from
    # hold_reserved.
    for tgt in _RETAIL_PREPARATION_STAGES:
        table.setdefault(VEHICLE_STAGE_HOLD_RESERVED, set()).add(tgt)

    # Fixed returns: the three operational disposals that resume via
    # inspection.
    for src in (
        VEHICLE_STAGE_WHOLESALE_OUT,
        VEHICLE_STAGE_COMPANY_USE,
        VEHICLE_STAGE_OFF_MARKET,
    ):
        table.setdefault(src, set()).add(VEHICLE_STAGE_INSPECTION)

    return {src: frozenset(tgts) for src, tgts in table.items()}


_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = _build_allowed_transitions()


# ----------------------------------------------------------------------------
# Role authority — MILESTONE_5_PLANNING.md §5.f (SESSION_075 refined).
#
# Per target stage: the set of roles authorized to move a vehicle
# INTO that stage. When ``advance_stage`` is called with a
# non-``None`` actor, the actor must hold at least one of the
# authorized roles at the specified dealership; otherwise
# :class:`UnauthorizedStageTransitionError` is raised.
#
# When ``actor`` is ``None`` (system callers — rule / import /
# bootstrap triggers), the role check is skipped. The trigger
# vocabulary partitions authority responsibility: ``manual``
# triggers always carry an operator actor; system triggers do not.
# ----------------------------------------------------------------------------

_RETAIL_PREP_ROLES = frozenset(
    {ROLE_DEALER_OWNER, ROLE_SALES_MANAGER, ROLE_RECON_MANAGER}
)
_COMMERCIAL_ROLES = frozenset(
    {ROLE_DEALER_OWNER, ROLE_SALES_MANAGER}
)


def _build_stage_role_authority() -> dict[str, frozenset[str]]:
    """Per-target-stage authorized-role sets."""
    authority: dict[str, frozenset[str]] = {}
    # Retail-preparation targets — recon_manager may participate.
    for tgt in _RETAIL_PREPARATION_STAGES:
        authority[tgt] = _RETAIL_PREP_ROLES
    # frontline is retail-preparation-adjacent (the last step in the
    # forward chain); recon_manager may promote a vehicle to frontline
    # after QC + photography + listing complete.
    authority[VEHICLE_STAGE_FRONTLINE] = _RETAIL_PREP_ROLES
    # Commercial/disposition targets — owner + sales_manager only.
    for tgt in _COMMERCIAL_DISPOSITION_STAGES:
        authority[tgt] = _COMMERCIAL_ROLES
    return authority


_STAGE_ROLE_AUTHORITY: dict[str, frozenset[str]] = _build_stage_role_authority()


# ----------------------------------------------------------------------------
# Domain errors — four distinct classes per SESSION_075 §0.a item 5.
# Do NOT overload; each maps to a different HTTP status at M5.4.
# ----------------------------------------------------------------------------


class CrossTenantLifecycleError(ValueError):
    """Raised when a lifecycle service function is called with a
    ``dealership`` that does not match the target Vehicle or
    VehicleStage row.

    Subclasses :class:`ValueError` so callers catching ``ValueError``
    still work. Mirrors :class:`CrossTenantReconError` from M4.2.

    Maps to HTTP 404 at the M5.4 endpoint layer (fail-closed — a
    cross-tenant caller learns the vehicle "does not exist" from
    their perspective).
    """


class InvalidStageTransitionError(ValueError):
    """Raised when a transition is attempted from a from-state that
    the M5.2 state machine does not permit as an allowed target.

    Distinct from :class:`UnauthorizedStageTransitionError`: this is
    the *structural* illegality (the transition is disallowed for
    every role). The message includes the current stage and the
    attempted target so operators can understand the refusal without
    reading the source.

    Maps to HTTP 409 at the M5.4 endpoint layer.
    """


class UnauthorizedStageTransitionError(ValueError):
    """Raised when a structurally-legal transition is attempted by an
    actor who does not hold an authorizing role at the specified
    dealership.

    Distinct from :class:`InvalidStageTransitionError` per
    SESSION_075 §0.a item 5: this is a *role* refusal (the
    transition itself is allowed for some other role — e.g.
    ``sales_manager`` can move to ``hold_reserved`` but
    ``recon_manager`` cannot). Overloading the two errors would
    conflate two different remediation paths for the caller.

    Maps to HTTP 403 at the M5.4 endpoint layer.
    """


class StageAlreadyCurrentError(ValueError):
    """Raised when :func:`advance_stage` is called with
    ``to_stage`` equal to the vehicle's current stage.

    Refusing the no-op explicitly (rather than silently succeeding)
    lets the caller distinguish "already there" from "moved" —
    both are potentially valid outcomes, but the caller often
    wants to react differently (e.g. don't double-log a
    notification).

    Maps to HTTP 409 at the M5.4 endpoint layer.
    """


# ----------------------------------------------------------------------------
# Cross-tenant guard — model-layer ``clean()`` is the suspenders;
# this guard is the belt.
# ----------------------------------------------------------------------------


def _assert_vehicle_tenant(vehicle: Vehicle, dealership: Dealership) -> None:
    """Raise :class:`CrossTenantLifecycleError` when the target
    vehicle does not belong to the caller's dealership."""
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantLifecycleError(
            f"Vehicle #{vehicle.stock_number} belongs to dealership "
            f"{vehicle.dealership_id}, not {dealership.pk}. Lifecycle "
            "reads and writes MUST match the tenant that owns the "
            "vehicle (AUTHENTICATION_MODEL.md §1 layer 4)."
        )


# ----------------------------------------------------------------------------
# Suggested transition — the record type :func:`suggest_transitions`
# returns. Rule bodies (M5.3) build these; the M5.4 endpoint
# serializes them; the M5.6 UI renders them as one-click accept
# buttons.
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class SuggestedTransition:
    """One deterministic-rule suggestion for a vehicle's next stage.

    Fields:

    - ``to_stage`` — the target stage the rule proposes.
    - ``rule_name`` — the specific rule that fired (used as
      ``VehicleStageEvent.rule_name`` on accept). E.g.
      ``"inspection_to_recon"``.
    - ``evidence`` — human-readable summary of why the rule fired
      (used as ``VehicleStageEvent.notes`` seed on accept).
    - ``unmet_prerequisites`` — non-empty ONLY for rules that
      cannot be evaluated yet (e.g. ``photography → listing``
      pending M6 photo predicate per §5.h SESSION_075). Callers
      surface these as structured "waiting on X" hints in the UI
      rather than as active suggestions.
    """

    to_stage: str
    rule_name: str
    evidence: str
    unmet_prerequisites: tuple[str, ...] = field(default_factory=tuple)


# ----------------------------------------------------------------------------
# Public API — read side.
# ----------------------------------------------------------------------------


def get_current_stage(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[VehicleStage]:
    """Return the vehicle's :class:`VehicleStage` row, or ``None``.

    **Pure read.** Does NOT create a stage row if none exists —
    per SESSION_075 §0.a item 6 (no hidden writes from read-model
    contract). Callers who need a stage row to definitely exist
    call :func:`ensure_current_stage` explicitly.

    Raises :class:`CrossTenantLifecycleError` when the vehicle does
    not belong to the caller's dealership.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    return VehicleStage.objects.filter(vehicle=vehicle).first()


def annotate_retail_eligible(qs: QuerySet) -> QuerySet:
    """Annotate a :class:`Vehicle` queryset with a
    ``_lifecycle_retail_eligible`` boolean via a ``VehicleStage``
    join.

    The annotation is ``True`` iff the vehicle has a
    ``VehicleStage`` row with ``current_stage='frontline'``.
    Missing stage rows → ``False`` (a vehicle without a stage row
    is not retail-eligible per SESSION_075 §5.e Option D + §0.a
    item 6).

    **Annotation name.** The annotation is deliberately named
    ``_lifecycle_retail_eligible`` (with the leading underscore
    and ``lifecycle`` prefix) to avoid a name collision with the
    ``Vehicle.is_retail_eligible`` ``@property`` accessor (M5.2).
    Django populates queryset annotations onto the model instance
    via ``setattr``, which fails for read-only properties. The
    property is the caller-facing API; the annotation is the
    queryset-scan implementation.

    Callers use the annotation to swap retail-side ``is_available``
    filters for stage-based ones without joining the stage table
    manually:

        annotate_retail_eligible(Vehicle.objects.all()).filter(
            _lifecycle_retail_eligible=True
        )

    Introduced at M5.5 (SESSION_079) as the shared implementation
    behind ``services/chat_engine.py::customer_visible_vehicles``
    and any other retail-side consumer. Prefer this helper over
    rolling your own subquery — one implementation means one
    behavior.
    """
    frontline_exists = VehicleStage.objects.filter(
        vehicle=OuterRef("pk"),
        current_stage=VEHICLE_STAGE_FRONTLINE,
    )
    return qs.annotate(_lifecycle_retail_eligible=Exists(frontline_exists))


def retail_eligible(
    vehicle: Vehicle, *, dealership: Dealership
) -> bool:
    """Return True iff the vehicle's current stage is ``frontline``.

    **Pure read.** Returns ``False`` when no stage row exists — a
    vehicle without a stage row is not retail-eligible (and never
    will be until either the M5.5 write-path integration or an
    explicit :func:`ensure_current_stage` call seeds one, followed
    by the retail-preparation pipeline advancing it to
    ``frontline``).

    Raises :class:`CrossTenantLifecycleError` when the vehicle does
    not belong to the caller's dealership.
    """
    stage = get_current_stage(vehicle, dealership=dealership)
    if stage is None:
        return False
    return stage.current_stage == VEHICLE_STAGE_FRONTLINE


def resolve_hold_reserved_return_target(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[str]:
    """Return the retail-preparation stage the vehicle was in
    immediately before entering ``hold_reserved``, or ``None``.

    Reads the event log — walks the most recent
    :class:`VehicleStageEvent` whose ``to_stage='hold_reserved'``
    and returns its ``from_stage`` if the resolved value is a
    retail-preparation stage. NEVER parses ``notes`` free text
    (per §0.a item 2 — the event log is the durable record).

    Returns ``None`` when:

    - No prior ``to_stage='hold_reserved'`` event exists (the
      vehicle isn't in hold_reserved, or was migrated in as
      hold_reserved without an origin).
    - The resolved ``from_stage`` is ``None`` (bootstrap event).
    - The resolved ``from_stage`` is itself an operational-
      disposition stage rather than a retail-preparation stage
      (the vehicle "escaped from wholesale_out into hold_reserved"
      — the operator must choose a return target explicitly, not
      re-enter an operational stage).

    Callers (M5.4 endpoint, M5.6 UI) invoke this to compute the
    default target for a hold_reserved return; if it returns
    ``None`` the UI presents the full allowed-target list for
    manual selection.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    latest = (
        VehicleStageEvent.objects.filter(
            vehicle=vehicle,
            to_stage=VEHICLE_STAGE_HOLD_RESERVED,
        )
        .order_by("-entered_at", "-created_at")
        .first()
    )
    if latest is None:
        return None
    if latest.from_stage is None:
        return None
    if latest.from_stage not in _RETAIL_PREPARATION_STAGES:
        return None
    return latest.from_stage


# ----------------------------------------------------------------------------
# Deterministic rule evaluators — Milestone 5 · Increment 3 (SESSION_077).
# Per MILESTONE_5_PLANNING.md §5.h (SESSION_075 refined).
#
# Rules stay **suggestions only** — no auto-application in M5. The M5.4
# endpoint accepts suggestions via an explicit operator gesture. The
# rule bodies here are pure functions; they read M3 + M4 substrate but
# never write.
#
# M6.4 (SESSION_085) added ``_rule_listing_to_frontline`` — fires when
# ``VehicleListing.status='published' AND Vehicle.price > 0``. The
# published-listing predicate replaces the M5 "manual-only" gate per
# §5.h SESSION_075 refined + M6.4 planning. No ``price > 0``-only
# rule ships (which would claim a gate the system could not evaluate);
# the ``published`` half of the predicate is now available via the
# M6.3 ``services/vehicle_listing.py`` state machine.
# ----------------------------------------------------------------------------

# Severity levels that count as "actionable work required" for the
# inspection → recon rule. Advisory findings alone do NOT force recon
# (per §5.h — a completed report with no actionable findings must NOT
# be forced into recon).
_ACTIONABLE_SEVERITIES = frozenset(
    {
        CONDITION_SEVERITY_RECOMMENDED,
        CONDITION_SEVERITY_REQUIRED,
        CONDITION_SEVERITY_SAFETY,
    }
)


def _rule_inspection_to_recon(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[SuggestedTransition]:
    """Suggest ``inspection → recon`` when the vehicle's latest
    completed :class:`ConditionReport` has ≥1 finding at severity
    ``recommended``, ``required``, or ``safety``.

    Returns ``None`` when:

    - No completed report exists (the inspector hasn't signed off
      yet). The operator has a manual path — mark the report
      complete first, then re-evaluate.
    - The latest completed report has zero findings at actionable
      severities. **Do NOT force recon** — the operator has an
      allowed manual path directly to the ``qc`` stage or
      elsewhere per the §5.b transition table.

    Reads via ``services/condition_report.py::latest_completed_condition_report``
    to avoid circular imports. Emits :class:`CrossTenantLifecycleError`
    for cross-tenant misuse (does not delegate the error type to the
    substrate helper).
    """
    _assert_vehicle_tenant(vehicle, dealership)

    from .condition_report import latest_completed_condition_report

    report = latest_completed_condition_report(vehicle, dealership=dealership)
    if report is None:
        return None
    actionable = list(
        report.findings.filter(severity__in=_ACTIONABLE_SEVERITIES)
    )
    if not actionable:
        return None

    # Evidence string: brief tally so the operator understands why the
    # rule suggested recon without opening the full report.
    counts: dict[str, int] = {}
    for finding in actionable:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    parts = [
        f"{count} {severity}"
        for severity, count in sorted(counts.items())
    ]
    evidence = (
        f"Completed inspection has {len(actionable)} actionable "
        f"finding(s): {', '.join(parts)}."
    )
    return SuggestedTransition(
        to_stage=VEHICLE_STAGE_RECON,
        rule_name="inspection_to_recon",
        evidence=evidence,
    )


def _rule_recon_to_qc(
    vehicle: Vehicle, *, dealership: Dealership
) -> Optional[SuggestedTransition]:
    """Suggest ``recon → qc`` when BOTH of:

    a. Zero open work orders remain on the vehicle. Reads
       ``services/recon.py::open_work_orders_for_vehicle`` — "open"
       is ``status in {draft, approved, in_progress}``.
    b. Every ``must_do`` :class:`ReconDecision` for this vehicle's
       latest completed condition report is addressed by at least
       one completed :class:`WorkOrder`. A ``must_do`` decision
       with no completed WO coverage means promised work has not
       yet been done — the vehicle is NOT ready for QC even if the
       WO queue is technically empty.

    Returns ``None`` when either precondition fails. Never fires
    when the vehicle has no completed condition report.

    Callers who want a fine-grained "why did the rule refuse?"
    surface should split the check themselves; this function
    returns a single boolean-shaped answer via
    ``Optional[SuggestedTransition]``.

    Emits :class:`CrossTenantLifecycleError` for cross-tenant
    misuse.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    from .condition_report import latest_completed_condition_report
    from .recon import open_work_orders_for_vehicle

    open_wos = open_work_orders_for_vehicle(vehicle, dealership=dealership)
    if open_wos.exists():
        return None

    report = latest_completed_condition_report(vehicle, dealership=dealership)
    if report is None:
        # No inspection sign-off — no basis to conclude recon is
        # ready. Refuse rather than falsely suggest QC.
        return None

    # Check every must_do decision on the report's findings has at
    # least one completed WorkOrder covering it.
    must_do_findings = report.findings.filter(
        recon_decision__tier=RECON_DECISION_TIER_MUST_DO
    )
    unresolved_ids: list[int] = []
    for finding in must_do_findings:
        covered = WorkOrderFinding.objects.filter(
            finding=finding,
            work_order__status=WORK_ORDER_STATUS_COMPLETED,
            dealership=dealership,
        ).exists()
        if not covered:
            unresolved_ids.append(finding.pk)

    if unresolved_ids:
        return None

    must_do_count = must_do_findings.count()
    if must_do_count > 0:
        evidence = (
            f"All {must_do_count} must_do decision(s) covered by "
            "completed work orders; no open WOs remain."
        )
    else:
        evidence = (
            "No must_do decisions to resolve; no open WOs remain."
        )
    return SuggestedTransition(
        to_stage=VEHICLE_STAGE_QC,
        rule_name="recon_to_qc",
        evidence=evidence,
    )


def _rule_photography_to_listing(
    vehicle: Vehicle, *, dealership: Dealership
) -> SuggestedTransition:
    """Suggest ``photography → listing`` when the vehicle has ≥
    :data:`photo_gallery.LISTING_READY_PHOTO_COUNT` listing-ready
    photos.

    Per SESSION_082 §5.b Option C (user-confirmed): the count
    threshold is fixed at 8 for v1; per-dealer configurability via
    ``DealerOnboardingProfile`` is deferred to a future increment.
    Per SESSION_083 §3 Option A (user-confirmed): the dimension
    threshold (``width_px >= 1024 AND height_px >= 768``) is applied
    inside :func:`photo_gallery.listing_ready_count`.

    **ALWAYS returns a SuggestedTransition** (never ``None`` — matches
    the M5.3 stub contract for signature parity):

    - Active suggestion when
      ``listing_ready_count(vehicle) >= LISTING_READY_PHOTO_COUNT``.
      ``unmet_prerequisites`` is an empty tuple; the M5.4 endpoint /
      M5.6 UI renders as a one-click accept button.
    - Structured unmet-prerequisite when count is below threshold.
      ``unmet_prerequisites`` describes exactly how many more
      listing-ready photos are needed so the operator can act.

    Emits :class:`CrossTenantLifecycleError` for cross-tenant misuse.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    from .photo_gallery import LISTING_READY_PHOTO_COUNT, listing_ready_count

    count = listing_ready_count(vehicle, dealership=dealership)
    threshold = LISTING_READY_PHOTO_COUNT

    if count >= threshold:
        return SuggestedTransition(
            to_stage=VEHICLE_STAGE_LISTING,
            rule_name="photography_to_listing",
            evidence=(
                f"Vehicle has {count} listing-ready photo(s) "
                f"(threshold: {threshold})."
            ),
        )
    return SuggestedTransition(
        to_stage=VEHICLE_STAGE_LISTING,
        rule_name="photography_to_listing",
        evidence=(
            f"Vehicle has {count} listing-ready photo(s); "
            f"threshold is {threshold}."
        ),
        unmet_prerequisites=(
            f"Need {threshold - count} more listing-ready photo(s) "
            f"(current: {count} / {threshold}).",
        ),
    )


def _rule_listing_to_frontline(
    vehicle: Vehicle, *, dealership: Dealership
) -> SuggestedTransition:
    """Suggest ``listing → frontline`` when BOTH:

    a. A :class:`VehicleListing` exists for the vehicle AND
       ``status == 'published'`` (per M6.3
       :func:`services.vehicle_listing.publish_listing`).
    b. ``Vehicle.price > 0`` (the vehicle has a listable price).

    Per SESSION_083 M6.3 handoff + M6.4 §1.7 planning: this rule
    replaces the M5 "manual-only" gate now that the ``published``
    half of the predicate is deterministic. No ``price > 0``-only
    rule (which would claim a gate the system could not evaluate)
    — both halves are required.

    **ALWAYS returns a SuggestedTransition** (never ``None``):

    - Active suggestion when both preconditions met.
      ``unmet_prerequisites`` is an empty tuple; the M5.4 endpoint /
      M5.6 UI renders as a one-click accept button.
    - Structured unmet-prerequisite otherwise. Each failing
      condition (no listing, listing not published, price ≤ 0)
      surfaces as its own entry so the operator can act on the
      specific blocker.

    Emits :class:`CrossTenantLifecycleError` for cross-tenant misuse.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    from ..models import VEHICLE_LISTING_STATUS_PUBLISHED, VehicleListing

    listing = VehicleListing.objects.filter(vehicle=vehicle).first()
    price = vehicle.price

    unmet: list[str] = []
    if listing is None:
        unmet.append(
            "No VehicleListing exists yet — draft + approve + publish "
            "via services/vehicle_listing.py."
        )
    elif listing.status != VEHICLE_LISTING_STATUS_PUBLISHED:
        unmet.append(
            f"Listing status is {listing.status!r}; must be "
            "'published' — advance via approve_listing + "
            "publish_listing."
        )
    if price is None or price <= 0:
        unmet.append(
            f"Vehicle.price is {price!r}; must be > 0 for frontline "
            "eligibility."
        )

    if not unmet:
        return SuggestedTransition(
            to_stage=VEHICLE_STAGE_FRONTLINE,
            rule_name="listing_to_frontline",
            evidence=(
                f"Listing is published; Vehicle.price is ${price}. "
                "Vehicle is ready for the frontline."
            ),
        )
    return SuggestedTransition(
        to_stage=VEHICLE_STAGE_FRONTLINE,
        rule_name="listing_to_frontline",
        evidence="Listing → frontline prerequisites not yet met.",
        unmet_prerequisites=tuple(unmet),
    )


def suggest_transitions(
    vehicle: Vehicle, *, dealership: Dealership
) -> list[SuggestedTransition]:
    """Return the list of deterministic-rule suggestions currently
    applicable to this vehicle.

    Composes the applicable rule based on the vehicle's current
    stage (per MILESTONE_5_PLANNING.md §5.h SESSION_075 refined +
    M6.4 SESSION_085 extension):

    - ``inspection`` → :func:`_rule_inspection_to_recon` (may
      return ``None``).
    - ``recon`` → :func:`_rule_recon_to_qc` (may return ``None``).
    - ``photography`` → :func:`_rule_photography_to_listing`
      (always returns a :class:`SuggestedTransition`; active when
      photo count is at threshold, structured unmet-prereq when
      below).
    - ``listing`` → :func:`_rule_listing_to_frontline`
      (always returns a :class:`SuggestedTransition`; active when
      listing is published and price > 0, structured unmet-prereq
      per failing condition otherwise).
    - All other stages → no rules; returns ``[]``.

    Returns ``[]`` when the vehicle has no stage row.

    Raises :class:`CrossTenantLifecycleError` when the vehicle
    does not belong to the caller's dealership.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    stage = get_current_stage(vehicle, dealership=dealership)
    if stage is None:
        return []

    suggestions: list[SuggestedTransition] = []
    if stage.current_stage == VEHICLE_STAGE_INSPECTION:
        candidate = _rule_inspection_to_recon(vehicle, dealership=dealership)
        if candidate is not None:
            suggestions.append(candidate)
    elif stage.current_stage == VEHICLE_STAGE_RECON:
        candidate = _rule_recon_to_qc(vehicle, dealership=dealership)
        if candidate is not None:
            suggestions.append(candidate)
    elif stage.current_stage == VEHICLE_STAGE_PHOTOGRAPHY:
        # Always returns a SuggestedTransition — active or unmet.
        suggestions.append(
            _rule_photography_to_listing(vehicle, dealership=dealership)
        )
    elif stage.current_stage == VEHICLE_STAGE_LISTING:
        # M6.4 addition — always returns a SuggestedTransition
        # (active or unmet).
        suggestions.append(
            _rule_listing_to_frontline(vehicle, dealership=dealership)
        )
    return suggestions


# ----------------------------------------------------------------------------
# Public API — write side.
# ----------------------------------------------------------------------------


def ensure_current_stage(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    actor=None,
    trigger: str = VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    initial_stage: str = VEHICLE_STAGE_INCOMING,
) -> VehicleStage:
    """Return the vehicle's :class:`VehicleStage` row, creating one
    if none exists.

    **Explicit mutating op.** This is the ONE verb that creates a
    stage row from nothing. Property reads must not invoke it
    implicitly (per SESSION_075 §0.a item 6). Callers who want
    only to read call :func:`get_current_stage`.

    Behavior:

    - Existing stage row → returned as-is (idempotent).
    - No stage row → creates one with
      ``current_stage=initial_stage`` (default
      ``VEHICLE_STAGE_INCOMING``) and a matching bootstrap
      :class:`VehicleStageEvent` (``from_stage=None``,
      matching ``entered_at``, ``by=actor``).

    Parameters:

    - ``initial_stage`` — the stage to seed with. Defaults to
      ``incoming``; the M5.5 write-path integration may pass a
      different value when explicitly seeding a specific state.
    - ``trigger`` — the trigger recorded on both the stage and
      the paired bootstrap event. Defaults to ``"bootstrap"``.
    - ``actor`` — recorded as ``VehicleStage.entered_by`` and
      ``VehicleStageEvent.by``. Nullable — bootstrap-triggered
      creations typically have no actor.

    Concurrency:

    - Wrapped in ``transaction.atomic()`` + ``select_for_update()``
      on the paired Vehicle row so two concurrent bootstrap calls
      cannot both insert a stage row. The second call sees the
      first's insert and returns it.

    Raises :class:`CrossTenantLifecycleError` when the vehicle
    does not belong to the caller's dealership. Raises
    :class:`ValueError` for unknown ``initial_stage`` or unknown
    ``trigger``.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    if initial_stage not in _VALID_STAGE_KEYS:
        raise ValueError(
            f"ensure_current_stage: unknown initial_stage {initial_stage!r}. "
            "Valid stages live in "
            "``dealer_ai.models.VEHICLE_STAGE_CHOICES``."
        )
    if trigger not in _VALID_TRIGGER_KEYS:
        raise ValueError(
            f"ensure_current_stage: unknown trigger {trigger!r}. Valid "
            "triggers live in "
            "``dealer_ai.models.VEHICLE_STAGE_TRIGGER_CHOICES``."
        )

    with transaction.atomic():
        # Lock the parent Vehicle row so concurrent
        # ensure_current_stage calls serialize behind the lock.
        Vehicle.objects.select_for_update().get(pk=vehicle.pk)

        existing = VehicleStage.objects.filter(vehicle=vehicle).first()
        if existing is not None:
            return existing

        now = timezone.now()
        stage = VehicleStage(
            vehicle=vehicle,
            dealership=dealership,
            current_stage=initial_stage,
            entered_at=now,
            entered_by=actor,
            trigger=trigger,
            last_transition_note="",
        )
        stage.full_clean()
        stage.save()

        # Matching bootstrap event — one .now() value shared with the
        # stage row so the event/stage entered_at-match invariant is
        # enforceable (mirrors migration 0017 bootstrap contract).
        event = VehicleStageEvent(
            vehicle=vehicle,
            dealership=dealership,
            from_stage=None,
            to_stage=initial_stage,
            entered_at=now,
            by=actor,
            trigger=trigger,
            rule_name="",
            notes="",
        )
        event.full_clean()
        event.save()

        return stage


def advance_stage(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    to_stage: str,
    actor=None,
    trigger: str,
    rule_name: str = "",
    notes: str = "",
) -> VehicleStage:
    """Move the vehicle to ``to_stage``; record who authorized it.

    The ONE authoritative transition verb. Writes both the
    :class:`VehicleStage` update AND a matching
    :class:`VehicleStageEvent` row atomically inside a
    ``transaction.atomic()`` block.

    Sequence:

    1. Cross-tenant guard on the vehicle.
    2. Validate ``to_stage`` and ``trigger`` are canonical values.
    3. Inside ``transaction.atomic()``:
       a. ``ensure_current_stage(vehicle, dealership=dealership,
          actor=actor)`` (defense-in-depth — creates ``incoming``
          + bootstrap event if the vehicle has no stage row yet).
       b. ``select_for_update()`` the stage row.
       c. Refuse no-op (``current_stage == to_stage``) with
          :class:`StageAlreadyCurrentError`.
       d. Refuse structurally illegal transition with
          :class:`InvalidStageTransitionError`.
       e. If ``actor is not None``, check role authority against
          the target; refuse with
          :class:`UnauthorizedStageTransitionError` when the
          actor holds no authorizing role.
       f. Update the stage row: ``current_stage``, ``entered_at``,
          ``entered_by``, ``trigger``, ``last_transition_note``.
       g. Append a :class:`VehicleStageEvent` with matching
          ``from_stage`` / ``to_stage`` / ``entered_at`` (single
          ``.now()`` value shared with the stage row).

    Parameters:

    - ``to_stage`` — must be a canonical stage from
      :data:`VEHICLE_STAGE_CHOICES`.
    - ``actor`` — the user requesting the transition. Nullable
      only for system callers (``trigger`` in ``{rule, import,
      bootstrap}`` typically has no operator). When ``None``, the
      role check is skipped.
    - ``trigger`` — must be a canonical trigger from
      :data:`VEHICLE_STAGE_TRIGGER_CHOICES`. Required (no
      default — every advance_stage caller must be explicit).
    - ``rule_name`` — populated when ``trigger='rule'``; blank
      otherwise. The persistence layer permits blank; the M5.3
      rule apply flow will populate it.
    - ``notes`` — operator-supplied reason (for manual
      transitions) or evidence summary (for rule transitions).
      Written to both ``VehicleStage.last_transition_note`` and
      ``VehicleStageEvent.notes``.

    Raises:

    - :class:`CrossTenantLifecycleError` — cross-tenant vehicle.
    - :class:`ValueError` — unknown ``to_stage`` or ``trigger``.
    - :class:`InvalidStageTransitionError` — structurally illegal
      from → to per :data:`_ALLOWED_TRANSITIONS`.
    - :class:`UnauthorizedStageTransitionError` — actor holds no
      authorizing role for ``to_stage`` (only when ``actor`` is
      not ``None``).
    - :class:`StageAlreadyCurrentError` — no-op refused.
    """
    _assert_vehicle_tenant(vehicle, dealership)

    if to_stage not in _VALID_STAGE_KEYS:
        raise ValueError(
            f"advance_stage: unknown to_stage {to_stage!r}. Valid stages "
            "live in ``dealer_ai.models.VEHICLE_STAGE_CHOICES``."
        )
    if trigger not in _VALID_TRIGGER_KEYS:
        raise ValueError(
            f"advance_stage: unknown trigger {trigger!r}. Valid triggers "
            "live in ``dealer_ai.models.VEHICLE_STAGE_TRIGGER_CHOICES``."
        )

    with transaction.atomic():
        # Defense-in-depth: ensure the vehicle has a stage row
        # before the transition (a future write path that forgets
        # to seed the row won't leave advance_stage without a
        # from-state).
        ensure_current_stage(
            vehicle,
            dealership=dealership,
            actor=actor,
        )

        stage = VehicleStage.objects.select_for_update().get(vehicle=vehicle)

        # No-op refusal — the caller likely wants to know they
        # didn't move.
        if stage.current_stage == to_stage:
            raise StageAlreadyCurrentError(
                f"Vehicle #{vehicle.stock_number} is already at "
                f"{to_stage!r}. Repeated transitions to the same stage "
                "are refused so callers can distinguish 'already there' "
                "from 'moved'."
            )

        # Structural allow-list check.
        allowed_targets = _ALLOWED_TRANSITIONS.get(stage.current_stage, frozenset())
        if to_stage not in allowed_targets:
            raise InvalidStageTransitionError(
                f"Cannot transition Vehicle #{vehicle.stock_number} from "
                f"{stage.current_stage!r} to {to_stage!r}. Allowed "
                f"targets from {stage.current_stage!r}: "
                f"{sorted(allowed_targets)}. See "
                "MILESTONE_5_PLANNING.md §5.b for the full table."
            )

        # Role authority check — skipped for system callers.
        if actor is not None:
            authorized_roles = _STAGE_ROLE_AUTHORITY.get(to_stage, frozenset())
            has_role = UserDealershipRole.objects.filter(
                user=actor,
                dealership=dealership,
                role__in=list(authorized_roles),
            ).exists()
            if not has_role:
                raise UnauthorizedStageTransitionError(
                    f"Actor {actor} is not authorized to transition "
                    f"Vehicle #{vehicle.stock_number} into "
                    f"{to_stage!r}. Authorized roles for this target: "
                    f"{sorted(authorized_roles)}. See "
                    "MILESTONE_5_PLANNING.md §5.f."
                )

        # Apply the transition. Single .now() value shared by the
        # stage update and the event insert so the "event's
        # entered_at equals stage's entered_at" invariant is
        # enforceable in tests (a second .now() call would drift by
        # microseconds).
        now = timezone.now()
        from_stage_value = stage.current_stage

        stage.current_stage = to_stage
        stage.entered_at = now
        stage.entered_by = actor
        stage.trigger = trigger
        stage.last_transition_note = notes
        stage.full_clean()
        stage.save()

        event = VehicleStageEvent(
            vehicle=vehicle,
            dealership=dealership,
            from_stage=from_stage_value,
            to_stage=to_stage,
            entered_at=now,
            by=actor,
            trigger=trigger,
            rule_name=rule_name,
            notes=notes,
        )
        event.full_clean()
        event.save()

        return stage
