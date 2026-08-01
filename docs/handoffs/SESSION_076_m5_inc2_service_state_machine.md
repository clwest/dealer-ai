---
title: "SESSION_076 handoff — Milestone 5 · Increment 2 (lifecycle service + state machine)"
status: historical
type: handoff
date: 2026-08-01
session: 076
milestone: 5
milestone_status: in-progress
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_076 — Milestone 5 · Increment 2 (M5.2 — lifecycle service + state machine)

## What shipped

The service layer for the vehicle-lifecycle domain. One new
module (`services/vehicle_lifecycle.py`, ~610 lines) with five
public functions + four distinct domain error classes + module-
level transition table + role-authority map. Two new `Vehicle`
`@property` accessors (`current_stage`, `is_retail_eligible`) —
pure reads, may return `None`/`False` when no stage row exists.
77 focused service tests. **Zero migrations, zero endpoints,
zero deterministic rule bodies (M5.3), zero retail-gating
refactor (M5.5), zero frontend, zero AI role.**

Baseline: 2,576 → **2,653 pass**, 1 skipped, 0 fail. +77 tests,
0 regressions.

## The service module

`backend/dealer_ai/services/vehicle_lifecycle.py`. Follows the
M4.2 recon-service house shape (module docstring citing planning
sections, domain errors at top, cross-tenant helper,
`transaction.atomic()` + `select_for_update()` concurrency
posture, function-local imports where circular reference is a
risk).

### Five public functions

1. **`get_current_stage(vehicle, *, dealership) →
   Optional[VehicleStage]`** — pure read. Returns the existing
   row or `None`. Does NOT bootstrap.

2. **`ensure_current_stage(vehicle, *, dealership, actor=None,
   trigger="bootstrap", initial_stage="incoming") →
   VehicleStage`** — explicit mutating verb. Creates the
   missing stage row and a matching bootstrap
   `VehicleStageEvent` (`from_stage=None`, single
   `timezone.now()` value shared with the stage row so the
   `entered_at`-match invariant is enforceable). Idempotent —
   returns the existing row if present. Uses
   `transaction.atomic()` + `select_for_update()` on the
   parent Vehicle row so concurrent bootstrap calls serialize.

3. **`advance_stage(vehicle, *, dealership, to_stage,
   actor=None, trigger, rule_name="", notes="") →
   VehicleStage`** — the one authoritative transition verb.
   Sequence (inside `transaction.atomic()`):
   1. Cross-tenant guard.
   2. Validate `to_stage` and `trigger` are canonical.
   3. Call `ensure_current_stage(...)` first
      (defense-in-depth for future write paths that forget to
      seed the row).
   4. `select_for_update()` the stage row.
   5. Refuse no-op (`current_stage == to_stage`) with
      `StageAlreadyCurrentError`.
   6. Structural allow-list check via `_ALLOWED_TRANSITIONS` →
      `InvalidStageTransitionError`.
   7. Role authority check via `_STAGE_ROLE_AUTHORITY` (only
      when `actor is not None` — system callers skip this) →
      `UnauthorizedStageTransitionError`.
   8. Update the stage row and append a matching
      `VehicleStageEvent` with the same `entered_at`.

4. **`retail_eligible(vehicle, *, dealership) → bool`** — pure
   read. Returns `False` when no stage row exists (a vehicle
   without a stage row is not retail-eligible). Returns True
   iff `current_stage == VEHICLE_STAGE_FRONTLINE`.

5. **`suggest_transitions(vehicle, *, dealership) →
   list[SuggestedTransition]`** — **stub in M5.2.** Returns
   an empty list. M5.3 fills in the rule bodies per §5.h. The
   `SuggestedTransition` dataclass ships now so M5.4 endpoints
   can type-annotate their response.

### One additional read helper

**`resolve_hold_reserved_return_target(vehicle, *, dealership)
→ Optional[str]`** — walks the event log for the most recent
`VehicleStageEvent` whose `to_stage='hold_reserved'` and
returns its `from_stage` if the resolved value is in
`_RETAIL_PREPARATION_STAGES` (the 8-stage retail pipeline).
Returns `None` when:
- No prior `to_stage='hold_reserved'` event exists.
- The event's `from_stage` is `None` (bootstrap event).
- The event's `from_stage` is an operational-disposition stage
  rather than a retail-preparation stage (the vehicle escaped
  from wholesale_out into hold_reserved — the operator must
  choose a return target explicitly).

**Never parses `notes` free text** per §0.a item 2 — the event
log is the durable record. `notes` is operator commentary, not
structured state.

### Four distinct domain errors

Do NOT overload. Each maps to a different HTTP status at M5.4.

- `CrossTenantLifecycleError(ValueError)` → HTTP 404 (fail-closed).
- `InvalidStageTransitionError(ValueError)` — structural
  illegality → HTTP 409.
- `UnauthorizedStageTransitionError(ValueError)` — role
  refusal → HTTP 403.
- `StageAlreadyCurrentError(ValueError)` — no-op refused →
  HTTP 409.

Locked distinctness by
`DomainErrorsAreDistinct.test_unauthorized_is_not_invalid`.

### Module-level transition table (§5.b)

`_ALLOWED_TRANSITIONS: dict[str, frozenset[str]]` built at
import time via `_build_allowed_transitions()` from three
composable pieces:

1. Retail-preparation forward chain (8 edges):
   `incoming → inspection → recon → qc → detail →
   photography → listing → frontline`, plus the
   `qc → photography` detail-collapse escape.
2. Operational escapes from any retail-preparation stage OR
   from `frontline` → any of the four commercial/disposition
   targets (`hold_reserved`, `wholesale_out`, `company_use`,
   `off_market`).
3. Escape returns: `hold_reserved` → any retail-preparation
   stage (including `frontline`); `wholesale_out` /
   `company_use` / `off_market` → `inspection` only.

**No `frontline → sold` edge, no `sold` source in the table**
(§5.a — sold deferred to M9). Locked by
`AllowedTransitionsStructure.test_no_frontline_to_sold_transition`
+ `test_no_sold_source_in_table`.

### Module-level role authority (§5.f)

`_STAGE_ROLE_AUTHORITY: dict[str, frozenset[str]]`:

- **Retail-preparation targets** (incoming through frontline,
  8 stages): `{dealer_owner, sales_manager, recon_manager}`.
- **Commercial/disposition targets** (hold_reserved,
  wholesale_out, company_use, off_market): `{dealer_owner,
  sales_manager}` only. `recon_manager` NOT authorized.

Locked by
`StageRoleAuthorityStructure.test_commercial_targets_exclude_recon_manager`.

### One design decision resolved during implementation

**`_RETAIL_PREPARATION_STAGES` includes `frontline`.** The
first test-suite run failed on
`test_returns_previous_retail_prep_stage_from_event` — a
frontline vehicle held to `hold_reserved` and then returned
was resolving to `None` rather than `frontline`. Root cause:
`_RETAIL_PREPARATION_STAGES` excluded `frontline` (treated it
as separate). Fix: include `frontline`. The user's §5.a
language calls all 8 stages (incoming through frontline) the
"retail-preparation pipeline"; frontline is the terminal
retail-eligible state within that pipeline. The operational
intent of `hold_reserved → previous stage` is "return to what
the vehicle was doing before the hold" — for a frontline
vehicle, that IS frontline. Locked by
`ResolveHoldReservedReturnTarget.test_returns_previous_retail_prep_stage_from_event`.

The redundant explicit `| {VEHICLE_STAGE_FRONTLINE}` and
`authority[VEHICLE_STAGE_FRONTLINE] = _RETAIL_PREP_ROLES`
statements are left in place for readability — they now assign
the same value the loops assign, but the intent-signalling
value of "frontline is deliberately in this bucket" is worth
the redundancy.

## Vehicle @property accessors

`Vehicle.current_stage` and `Vehicle.is_retail_eligible` added
to `backend/dealer_ai/models.py` immediately after the M4
`has_recon_decisions` property. Function-local imports (M3.3 /
M4.7 pattern). Both are pure reads:

- `current_stage` — delegates to `get_current_stage`; may
  return `None` when no stage row exists.
- `is_retail_eligible` — delegates to `retail_eligible`;
  returns `False` when no stage row exists.

Docstring on `is_retail_eligible` documents the M5.5 refactor
seam and the SESSION_075 anti-pattern ("`is_available` MUST
NOT be used as a manual override for retail gating").

## Tests

One new file, **77 tests**:

`test_vehicle_lifecycle_service.py` — 12 test classes:

- `AllowedTransitionsStructure` (10) — retail-preparation
  forward chain, operational escapes from every retail-prep
  stage, operational escapes from frontline, hold_reserved
  return targets, escape returns, no `frontline → sold`, no
  `sold` source, no disallowed forward shortcut.
- `StageRoleAuthorityStructure` (2) — retail-prep targets
  authorize `recon_manager`; commercial targets exclude
  `recon_manager` and authorize owner + sales_manager only.
- `DomainErrorsAreDistinct` (2) — all subclass `ValueError`;
  `UnauthorizedStageTransitionError` is NOT a subclass of
  `InvalidStageTransitionError` (overloading refused).
- `GetCurrentStagePureRead` (4) — returns None, returns row,
  does not create on first access, cross-tenant refused.
- `RetailEligiblePureRead` (5) — False without stage, True at
  frontline, False elsewhere (including hold_reserved),
  cross-tenant refused.
- `EnsureCurrentStageCreatesWhenAbsent` (4) — creates with
  default `incoming`, matching bootstrap event, custom
  initial_stage, records actor.
- `EnsureCurrentStageIdempotent` (2) — second call returns
  same row, does not create additional event.
- `EnsureCurrentStageValidation` (3) — cross-tenant,
  unknown initial_stage, unknown trigger.
- `AdvanceStageForwardChain` (8) — every forward-chain
  transition succeeds.
- `AdvanceStageOperationalEscapes` (4) — frontline →
  hold_reserved, recon → wholesale_out, frontline →
  company_use, wholesale_out → inspection.
- `AdvanceStageStructuralRefusal` (3) — forward-shortcut
  refused, backwards refused, `sold` refused as unknown.
- `AdvanceStageNoOpRefusal` (1) — StageAlreadyCurrentError.
- `AdvanceStageRoleAuthorityEnforcement` (9) —
  `recon_manager` can do retail-prep but NOT any of the four
  commercial/disposition transitions;
  `sales_manager`/`dealer_owner` can; advisor refused;
  system caller (actor=None) bypasses role check.
- `AdvanceStageCrossTenantRefusal` (1).
- `AdvanceStageAtomicWrites` (3) — stage + event share
  `entered_at`, notes written to both, rule_name written to
  event.
- `AdvanceStageDefenseInDepthSeedsMissingRow` (1) — advance
  on unseeded vehicle seeds `incoming` bootstrap first.
- `ResolveHoldReservedReturnTarget` (5) — None when no
  hold_reserved event, returns previous retail-prep stage,
  ignores notes free text, returns None when from_stage is
  operational, cross-tenant refused.
- `SuggestTransitionsStub` (3) — returns [] in M5.2,
  cross-tenant refused, dataclass shape.
- `VehiclePropertyAccessorsPureReads` (6) — `current_stage`
  None without stage, does not create row on read, returns
  row when present; `is_retail_eligible` False without stage,
  True at frontline, False at off_market.
- `RegressionBoundaries` (1) — advance_stage writes no
  `WorkOrder` or `VehicleCost` rows (M4/M2 substrate
  untouched).

## Backend baseline

- **Pre-session:** 2,576 pass, 1 skipped, 0 fail.
- **Post-session:** 2,653 pass, 1 skipped, 0 fail.
- Delta: +77 tests, 0 regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."

## Compatibility result

- **Frontend:** untouched. Zero frontend files changed.
- **Migrations:** none added; migration graph unchanged at
  `0001–0017`.
- **`Vehicle.is_available`:** unchanged (still a
  `BooleanField`; still populated by whatever set it before
  M5).
- **M1/M2/M3/M4 substrate:** every existing model, service,
  permission class, safety-stack scrub, API, and frontend
  behavior unchanged. The +77 test delta is +77 M5.2 tests,
  not any regressed or refactored existing test.
- **New Vehicle read-model properties:**
  `current_stage`/`is_retail_eligible` land here as pure
  reads. Every downstream consumer that reads them will see
  `None`/`False` on any vehicle that has not been through the
  migration `0017` bootstrap or an explicit
  `ensure_current_stage(...)` call — that is intentional and
  is the M5.5 write-path integration's responsibility to
  address for newly created vehicles.

## Commit hashes

- Session commit: **TBD** (deferred per user directive — commit
  + push happens after Milestone 5 closes AND
  `MILESTONE_6_PLANNING.md` is created).

## Exact recommended scope for M5.3

**M5.3 — Deterministic rule evaluators + suggested transitions.**
Fill in the M5.2 `suggest_transitions(...)` stub with the four
rule bodies from planning §5.h (SESSION_075 refined).

Rule evaluators (all pure functions in
`services/vehicle_lifecycle.py`):

1. `_rule_inspection_to_recon(vehicle, *, dealership) →
   Optional[SuggestedTransition]` — fires when the vehicle's
   latest completed `ConditionReport` has ≥1 finding at
   severity `recommended`, `required`, or `safety`. A
   completed report with **no actionable findings** must NOT
   force recon — return `None` in that case.

2. `_rule_recon_to_qc(vehicle, *, dealership) →
   Optional[SuggestedTransition]` — fires when (a) zero open
   work orders remain AND (b) every `must_do`
   `ReconDecision` for this vehicle is addressed by completed
   `WorkOrder` coverage OR is explicitly resolved by the
   decision contract. Reuse
   `services/recon.py::open_work_orders_for_vehicle` and
   walk the decision table.

3. `_rule_photography_to_listing(vehicle, *, dealership) →
   Optional[SuggestedTransition]` — returns a
   `SuggestedTransition` with `unmet_prerequisites=("M6:
   photo predicate not yet available",)` — a **structured
   unmet prerequisite**, NOT a fake suggestion. Callers
   surface this as a "waiting on X" hint in the UI rather
   than as an active suggestion.

4. **NO `_rule_listing_to_frontline`.** Per §5.h SESSION_075
   refinement, `listing → frontline` is **manual-only in
   M5**. M6 later adds the deterministic published-listing
   rule once `VehicleListing.published` exists. Do NOT ship
   a `price > 0`-only rule — that would claim a deterministic
   gate that cannot be evaluated.

`suggest_transitions(vehicle, *, dealership)` composes every
applicable rule based on the vehicle's current stage:
- `inspection` → `_rule_inspection_to_recon`.
- `recon` → `_rule_recon_to_qc`.
- `photography` → `_rule_photography_to_listing`
  (returns a suggestion with `unmet_prerequisites`, not None).
- Other stages → no rules, return `[]`.

**Tests.** ~40 focused rule tests: each rule fires under
expected conditions; each rule does NOT fire under
non-matching conditions; structured-prerequisite rules return
a well-formed `SuggestedTransition` with `unmet_prerequisites`.

**Boundary.** Test baseline: 2,653 → ~2,693. No migrations.

**Out of M5.3:**

- ❌ No endpoints — M5.4.
- ❌ No retail-gating query refactor — M5.5.
- ❌ No frontend — M5.6.
- ❌ No auto-application. Rules stay suggestions the operator
  explicitly accepts via M5.4 endpoint.
- ❌ No `listing → frontline` rule. M5's truthful v1 is
  manual-only.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — as amended at
   SESSION_075 (§0.a change-log + §1.6 + §5.a–§5.i + §7 + §9)
6. `docs/handoffs/SESSION_076_m5_inc2_service_state_machine.md`
   (this doc)
7. `docs/handoffs/SESSION_075_m5_inc1_core_models.md`
8. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 + §8
9. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6
10. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md` §"Workflow /
    state-machine changes" + Phase 4
12. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` §6

Narrative docs are claims. Rules + research + code are facts.
