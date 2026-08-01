---
title: "SESSION_077 handoff — Milestone 5 · Increment 3 (deterministic rule evaluators)"
status: historical
type: handoff
date: 2026-08-01
session: 077
milestone: 5
milestone_status: in-progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_077 — Milestone 5 · Increment 3 (M5.3 — deterministic rule evaluators)

## What shipped

Three rule evaluators in
`services/vehicle_lifecycle.py` + rewrite of the M5.2
`suggest_transitions(...)` stub to compose them. 41 focused
rule tests. **Zero migrations, zero endpoints, zero
retail-gating refactor, zero frontend, zero AI role.**

Baseline: 2,653 → **2,694 pass**, 1 skipped, 0 fail. +41 tests,
0 regressions.

## Rule evaluators

### `_rule_inspection_to_recon(vehicle, *, dealership)`

Fires when the vehicle's latest completed `ConditionReport`
has ≥1 finding at severity in `{recommended, required,
safety}`. Returns `None` when:
- No completed report exists.
- The completed report has zero actionable findings (§5.h —
  a completed report with only advisory findings must NOT be
  forced into recon).

Evidence string enumerates the actionable count by severity
so the operator understands why recon is suggested without
opening the full report (e.g. `"Completed inspection has 2
actionable finding(s): 1 required, 1 safety."`).

### `_rule_recon_to_qc(vehicle, *, dealership)`

Fires when BOTH:
1. Zero open work orders remain
   (`Vehicle.open_work_orders.exists() == False`).
2. Every `must_do` `ReconDecision` for this vehicle's latest
   completed condition report is addressed by a completed
   `WorkOrder` (`WorkOrderFinding` link where
   `work_order.status='completed'`).

Returns `None` when either precondition fails, when no
completed report exists (no basis to conclude recon is
done), or when a `must_do` decision has only draft /
approved / in_progress / cancelled coverage (cancelled ≠
completed — the promised work never actually happened).

`should_do` and `wont_do` decisions do NOT block QC — only
`must_do` requires completed coverage. This mirrors the
SESSION_067 recon policy where `should_do` is a
prioritization signal, not a commitment.

### `_rule_photography_to_listing(vehicle, *, dealership)`

**Always returns a structured unmet prerequisite — never
`None`.** Per §5.h SESSION_075 refined: the M6 photo
predicate isn't shipped yet, so the rule cannot be evaluated.
Returns a `SuggestedTransition` with:
- `to_stage = VEHICLE_STAGE_LISTING`
- `rule_name = "photography_to_listing"`
- `evidence = "M6 photo predicate not yet available..."`
- `unmet_prerequisites = ("M6: VehiclePhoto.count ≥ N
  predicate not yet shipped.",)`

Callers (M5.4 endpoint / M5.6 UI) surface this as a
truthful "waiting on X" hint rather than as an active accept
button or silence.

## `suggest_transitions` composition

Rewritten from the M5.2 empty-list stub to dispatch by the
vehicle's current stage:

- `inspection` → call `_rule_inspection_to_recon` (may
  return `None` → no suggestion).
- `recon` → call `_rule_recon_to_qc` (may return `None`).
- `photography` → always append the structured prerequisite
  from `_rule_photography_to_listing`.
- All other stages (`incoming`, `qc`, `detail`, `listing`,
  `frontline`, `wholesale_out`, `hold_reserved`,
  `company_use`, `off_market`) → return `[]`.

Returns `[]` when the vehicle has no stage row (a vehicle
without a stage row has no basis for suggestions).

## No `listing → frontline` rule

Per §5.h SESSION_075 refined. `listing → frontline` is
**manual-only in M5**. `price > 0` alone is insufficient
once listing publication matters. M6 later adds the
deterministic published-listing rule once
`VehicleListing.published` exists.

**Locked by `NoListingToFrontlineRuleEverFires.test_composition_at_listing_never_suggests_frontline`** —
future edits that silently add a `listing → frontline` rule
will fail this test.

## Contract refinement: rule functions raise CrossTenantLifecycleError

The initial draft delegated the cross-tenant check to the
substrate helpers (`latest_completed_condition_report`,
`open_work_orders_for_vehicle`), which raise their own error
types (`CrossTenantConditionReportError`,
`CrossTenantReconError`). Test failures on
`RuleReconToQcCrossTenant.test_cross_tenant_refused` and
`RuleInspectionToReconCrossTenant.test_cross_tenant_refused`
surfaced the inconsistency.

Fix: added explicit `_assert_vehicle_tenant(vehicle,
dealership)` at the top of each rule function so the
lifecycle module raises lifecycle errors consistently.
Belt-and-suspenders — the substrate reads still do their
own tenant checks (redundant but harmless).

## Tests

One new file, **41 tests**:

`test_vehicle_lifecycle_rules.py`:

- `RuleInspectionToReconFires` (4) — fires on required
  severity, on safety severity, on recommended severity;
  evidence enumerates actionable count.
- `RuleInspectionToReconRefuses` (4) — no completed report,
  draft report, completed empty report, completed report
  with only advisory findings.
- `RuleInspectionToReconCrossTenant` (1).
- `RuleReconToQcFires` (3) — no must_do + no open WOs,
  must_do addressed by completed WO, should_do decision
  without WO (should_do doesn't block).
- `RuleReconToQcRefuses` (9) — open draft/approved/in_progress
  WOs block (three tests); completed WO alone doesn't block;
  cancelled WO doesn't block; must_do without any WO;
  must_do with only draft WO; must_do with only cancelled
  WO; no completed report.
- `RuleReconToQcCrossTenant` (1).
- `RulePhotographyToListingAlwaysReturnsPrerequisite` (5) —
  returns SuggestedTransition (not None), target is
  `listing`, rule_name matches, unmet_prerequisites populated,
  mentions M6.
- `SuggestTransitionsCompositionByStage` (12) — no stage row
  returns empty; inspection stage composes fire or empty;
  recon stage composes fire or empty; photography always
  returns prerequisite; every other stage returns empty
  (incoming, qc, detail, listing, frontline, off_market).
- `SuggestTransitionsCrossTenant` (1).
- `NoListingToFrontlineRuleEverFires` (1) — locks §5.h
  invariant.

## Backend baseline

- **Pre-session:** 2,653 pass, 1 skipped, 0 fail.
- **Post-session:** 2,694 pass, 1 skipped, 0 fail.
- Delta: +41 tests, 0 regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."

## Compatibility result

- **Frontend:** untouched.
- **Migrations:** none added; graph unchanged at `0001–0017`.
- **`Vehicle.is_available`:** unchanged.
- **M1–M4 substrate:** rule evaluators READ substrate
  (`latest_completed_condition_report`,
  `open_work_orders_for_vehicle`, `Vehicle.open_work_orders`,
  `Vehicle.has_recon_decisions`, `ReconDecision`,
  `WorkOrderFinding`); they never write. The +41 test delta
  is +41 M5.3 tests, not any regressed existing test.
- **M5.2 service functions:** unchanged in signature; only
  `suggest_transitions` body swapped from `return []` stub
  to composition. M5.2 tests that seeded a vehicle at
  `inspection` with no completed report still pass — the
  new inspection_to_recon rule returns None in that case,
  so composition still yields `[]`.

## Commit hashes

- Session commit: **TBD** (deferred per user directive —
  commit + push happens after M5.7 closes AND
  `MILESTONE_6_PLANNING.md` is created).

## Exact recommended scope for M5.4

**M5.4 — Admin API + permission matrix.** Add DRF endpoints
under `/api/dealer-ai/admin/vehicles/<stock_number>/lifecycle/`
that wrap the M5.2 + M5.3 service surface. First code that
users interact with (via the M5.6 UI, which lands after
M5.5 retail-gating).

### Endpoints (three)

1. **`GET .../lifecycle/`** — dashboard. Returns:
   - Current stage (via `get_current_stage`; response
     handles the `None` case truthfully).
   - Recent event log (last N events via
     `Vehicle.stage_events`).
   - Suggested transitions (via
     `suggest_transitions(...)` — the M5.3 composition).
   - Return-target hint for hold_reserved vehicles (via
     `resolve_hold_reserved_return_target`).

2. **`POST .../lifecycle/transition/`** — apply a manual
   transition. Body: `to_stage`, `notes`. Calls
   `advance_stage(...)` with
   `trigger=VEHICLE_STAGE_TRIGGER_MANUAL`, `actor=request.user`.

3. **`POST .../lifecycle/transition/rule/`** — accept a
   suggested (rule-triggered) transition. Body: `rule_name`.
   Re-evaluates `suggest_transitions` at apply time and
   refuses (409) if the specific rule no longer fires (the
   predicate has flipped since the operator saw it in the
   dashboard). Calls `advance_stage(...)` with
   `trigger=VEHICLE_STAGE_TRIGGER_RULE`, `rule_name=<matched>`,
   `actor=request.user`.

### Permission classes (per §5.f)

Reuse existing:
- **Retail-preparation transitions AND the GET surfaces:**
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6).
- **Commercial/disposition transitions:**
  `IsSalesManagerOrOwnerAtActiveDealership` (M2.6).

The DRF permission layer admits the endpoint. The M5.2
service's `advance_stage` enforces per-transition role
authority and raises `UnauthorizedStageTransitionError`
(HTTP 403) for a `recon_manager` attempting a commercial
transition.

### Domain-error → HTTP mapping

- `CrossTenantLifecycleError` → 404.
- `InvalidStageTransitionError` → 409.
- `UnauthorizedStageTransitionError` → 403.
- `StageAlreadyCurrentError` → 409.
- `ValueError` → 400.

### Tests

~40 focused endpoint tests: permission matrix per endpoint
(representative subset — the classes are uniform, so full
enumeration is unnecessary), business flows (successful
transition writes stage + event; suggested-transition
accept succeeds; suggestion re-evaluation refuses on
flipped predicate), domain-error mapping, cross-tenant
fail-closed 404s.

**Boundary.** Test baseline: 2,694 → ~2,734. No migrations.

**Out of M5.4:**

- ❌ Retail-gating query refactor — M5.5.
- ❌ Frontend — M5.6.
- ❌ No auto-application of rules.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — as amended at
   SESSION_075 (§0.a + §1.6 + §5.a–§5.i + §7 + §9)
6. `docs/handoffs/SESSION_077_m5_inc3_deterministic_rules.md`
   (this doc)
7. `docs/handoffs/SESSION_076_m5_inc2_service_state_machine.md`
8. `docs/handoffs/SESSION_075_m5_inc1_core_models.md`
9. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 + §8
10. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
12. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`

Narrative docs are claims. Rules + research + code are facts.
