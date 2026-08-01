---
title: "SESSION_075 handoff — Milestone 5 · Increment 1 (core lifecycle persistence)"
status: historical
type: handoff
date: 2026-08-01
session: 075
milestone: 5
milestone_status: in-progress
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_075 — Milestone 5 · Increment 1 (M5.1 — core lifecycle persistence)

## What shipped

The persistence layer for the vehicle-lifecycle-stage
domain. Two new models (`VehicleStage`,
`VehicleStageEvent`), migration `0017` with a bootstrap
data-migration step, two module-level enum vocabularies
(12 stage values + 4 trigger values), cross-tenant
`clean()` guards on both models, tenancy-carrier
registration extended from 15 → 17, two new admin
registrations (the event admin is add- and delete-locked
to preserve the append-only history invariant), and 58
focused tests. **No service module, no state transitions,
no Vehicle `@property` accessors, no retail-gating
refactor, no deterministic rules, no endpoints, no
frontend, no AI role.**

Also: **narrow planning amendments** to
`MILESTONE_5_PLANNING.md` — reviewed and approved at the
top of the session — resolving every
`[NEEDS-DECISION-BEFORE-M5.1]` marker plus a
load-bearing architectural refinement (no hidden writes
from Vehicle read-model properties) that the original
planning shape would have violated.

## Session preamble — the planning amendments

The user opened the session with a comprehensive review
of the four `[NEEDS-DECISION-BEFORE-M5.1]` items plus
additional refinements that had to land before M5.1 code
was written. Each amendment landed in-place in
`MILESTONE_5_PLANNING.md` (§0.a change-log summary + §1.6
+ §5.a + §5.b + §5.c + §5.e + §5.f + §5.h + §5.i + §7
M5.1 + §7 M5.2 + §9 status flip). Frontmatter gained
`amended_at_session: SESSION_075`; `status:` stays
`draft` (flips to `shipped` at M5.7 per §7).

The eight amendments:

1. **§5.a stage enum — Modified Option C.** 12 stages
   (retail-preparation pipeline `incoming → inspection →
   recon → qc → detail → photography → listing →
   frontline` + operational categories `wholesale_out`,
   `hold_reserved`, `company_use`, `off_market`).
   Modifications from the original recommendation:
   - **`sold` deferred entirely to M9.** No enum
     constant, no `VEHICLE_STAGE_SOLD` symbol, no
     blocked transition stub. Shipping a state the
     service always rejects would be dishonest. M9
     adds `sold` alongside the `Sale` model.
   - **`company_use` added as a distinct disposition**
     — not truthfully equivalent to `off_market` per
     INVENTORY §6.5.
   - **`hold_reserved` used consistently** everywhere.
   - **`detail` kept distinct** in v1.

2. **§5.b transition table — approved with two
   refinements.** (a) `hold_reserved → previous stage`
   resolves the prior stage by reading the most recent
   `VehicleStageEvent` whose `to_stage=="hold_reserved"`
   and using its `from_stage`, **NOT** by parsing
   free-text `notes`. The event log is the durable
   record. (b) Post-frontline operational transitions
   (`frontline → hold_reserved / off_market /
   wholesale_out / company_use`) are explicitly allowed.
   No `frontline → sold` transition in M5.

3. **§5.c bootstrap — Option C affirmed; both rows
   required.** Migration `0017` MUST create BOTH a
   `VehicleStage` AND a matching bootstrap
   `VehicleStageEvent` for every existing Vehicle
   (`from_stage=None`, `trigger='bootstrap'`, matching
   `entered_at`, explicit `dealership`). Skipping the
   event would leave a Vehicle whose current stage has
   no corresponding event, silently violating the
   "every stage the vehicle occupies has an event"
   invariant M5.2 aging analytics relies on.

4. **§5.e `Vehicle.is_available` — Option D without
   premature removal date.** Keep intact as
   backwards-compat field. Add `is_retail_eligible` as
   authoritative predicate. Refactor known retail
   consumers at M5.5 (customer chat, stock-specific
   customer vehicle lookup, inventory search, public
   showroom). Deprecation note: *"retain until every
   known consumer has migrated and a repository-wide
   audit proves removal safe."* NOT scheduled for M9
   or any specific milestone.
   **Anti-pattern locked out:** `is_available` MUST NOT
   remain a manual override for retail gating —
   customer-facing eligibility comes from lifecycle
   stage alone. The M5.5 refactor is the enforcement
   point.

5. **§5.f role permission matrix — refined.** Reuse
   existing permission classes (no new broad lifecycle
   class). Recon-adjacent transitions may be performed
   by dealer_owner + sales_manager + recon_manager.
   Commercial/disposition transitions (`hold_reserved`,
   `wholesale_out`, `company_use`, `off_market`) may
   be performed only by dealer_owner + sales_manager.
   `recon_manager` may NOT transition into any of the
   four commercial/disposition stages — parts delays
   remain represented by M4 `WorkOrderPart` blocker
   data while the vehicle stays in its honest recon
   stage. Introduce a distinct
   `UnauthorizedStageTransitionError` for role
   refusals (maps to HTTP 403). Do NOT overload
   `InvalidStageTransitionError` (structural from/to
   illegality → HTTP 409).

6. **§1.6 no-hidden-writes refinement.** The prior
   planning sketch had `Vehicle.current_stage`
   delegating to `get_current_stage` which lazily
   bootstrapped a missing row. That violates the M2–M4
   side-effect-free Vehicle-read-model discipline. The
   M5.2 contract splits:
   - `get_current_stage(...) → Optional[VehicleStage]`
     — pure read.
   - `ensure_current_stage(...) → VehicleStage` —
     explicit mutating op; creates a missing stage row
     and a matching bootstrap `VehicleStageEvent`.
   - `Vehicle.current_stage` — delegates to the pure
     read function; may return `None`.
   - `Vehicle.is_retail_eligible` — pure read; returns
     `False` when no stage row exists.
   - `advance_stage(...)` may call
     `ensure_current_stage(...)` inside its
     transaction as a defense-in-depth safety net.
   The Vehicle `@property` accessors land in M5.2
   alongside the service, **not in M5.1**. Migration
   `0017` bootstraps every existing Vehicle. New
   Vehicle creation paths land in M5.5 as explicit
   `ensure_current_stage(...)` calls (not a pre-save
   signal, not a property-read side effect).

7. **§5.h rule evaluator refinements.** M5.3 rules
   remain suggestions only. `inspection → recon` fires
   only when a completed report has actionable findings
   per the final severity vocabulary. `recon → qc`
   requires every `must_do` decision addressed by
   completed WO coverage or explicitly resolved.
   `photography → listing` returns structured unmet
   prerequisite (not a fake suggestion) pending M6.
   `listing → frontline` is **manual-only in M5**; M6
   later adds the deterministic published-listing rule
   once `VehicleListing.published` exists.

8. **§5.i truthful customer language.** Approved
   phrasing for a stock-specific non-frontline lookup:
   *"That vehicle is not currently available for
   retail."* Do not expose internal stage, recon
   details, completion estimate, vendor status, or
   expected-ready date.

## Final stage + trigger vocabularies

Twelve stages shipped in M5.1 (module-level constants in
`backend/dealer_ai/models.py`):

- Retail-preparation pipeline (8): `VEHICLE_STAGE_INCOMING`,
  `VEHICLE_STAGE_INSPECTION`, `VEHICLE_STAGE_RECON`,
  `VEHICLE_STAGE_QC`, `VEHICLE_STAGE_DETAIL`,
  `VEHICLE_STAGE_PHOTOGRAPHY`, `VEHICLE_STAGE_LISTING`,
  `VEHICLE_STAGE_FRONTLINE`.
- Operational categories (4): `VEHICLE_STAGE_WHOLESALE_OUT`,
  `VEHICLE_STAGE_HOLD_RESERVED`, `VEHICLE_STAGE_COMPANY_USE`,
  `VEHICLE_STAGE_OFF_MARKET`.

Four triggers: `VEHICLE_STAGE_TRIGGER_MANUAL`,
`VEHICLE_STAGE_TRIGGER_RULE`,
`VEHICLE_STAGE_TRIGGER_IMPORT`,
`VEHICLE_STAGE_TRIGGER_BOOTSTRAP`.

Choice tuples: `VEHICLE_STAGE_CHOICES` (12 entries),
`VEHICLE_STAGE_TRIGGER_CHOICES` (4 entries).

`sold` deliberately absent.

## Models shipped

`backend/dealer_ai/models.py` gains two models:

### `VehicleStage` (OneToOne with Vehicle)

Fields:
- `vehicle` — OneToOneField(Vehicle, CASCADE,
  related_name="stage").
- `dealership` — ForeignKey(Dealership, CASCADE, NOT
  NULL, related_name="vehicle_stages").
- `current_stage` — CharField(max_length=32,
  choices=VEHICLE_STAGE_CHOICES).
- `entered_at` — DateTimeField (service stamps at
  transition time; migration stamps at bootstrap).
- `entered_by` — ForeignKey(AUTH_USER_MODEL, SET_NULL,
  nullable).
- `trigger` — CharField(max_length=16,
  choices=VEHICLE_STAGE_TRIGGER_CHOICES).
- `last_transition_note` — TextField(blank).
- `created_at`, `updated_at` — auto.

`Meta.ordering = ("-updated_at",)`.

`clean()` — cross-tenant guard: `dealership` matches
`vehicle.dealership`. Mirrors `WorkOrder.clean` and
`ReconDecision.clean`.

**No side effects on save.** `save()` does NOT create a
`VehicleStageEvent` row. Event creation is an explicit
service-layer concern (M5.2 `advance_stage` writes both
rows atomically).

### `VehicleStageEvent` (many-per-Vehicle)

Fields:
- `vehicle` — ForeignKey(Vehicle, CASCADE,
  related_name="stage_events").
- `dealership` — ForeignKey(Dealership, CASCADE, NOT
  NULL, related_name="vehicle_stage_events").
- `from_stage` — CharField(max_length=32,
  choices=VEHICLE_STAGE_CHOICES, nullable) — legitimate
  ONLY for bootstrap events at the M5.2 service layer.
- `to_stage` — CharField(max_length=32,
  choices=VEHICLE_STAGE_CHOICES, NOT NULL).
- `entered_at` — DateTimeField.
- `by` — ForeignKey(AUTH_USER_MODEL, SET_NULL,
  nullable).
- `trigger` — CharField(max_length=16,
  choices=VEHICLE_STAGE_TRIGGER_CHOICES).
- `rule_name` — CharField(max_length=128, blank) —
  non-blank when `trigger='rule'` is a service-layer
  invariant.
- `notes` — TextField(blank).
- `created_at` — auto (distinct from `entered_at`).

`Meta.ordering = ("-entered_at", "-created_at")`.

`clean()` — cross-tenant guard mirroring `VehicleStage.clean`.

**Append-only history.** Django technically permits row
updates; the M5.1 admin surface disables both add and
delete on this model, and the M5.1 test suite locks the
"creating an event does NOT mutate the paired current
stage" invariant. The M5.2 service will refuse to
expose an event-update surface.

## Verified tenancy-carrier count

Pre-M5.1 count read from source
(`backend/dealer_ai/services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`):
**15** entries (Vehicle, Salesperson, ChatSession,
ChatMessage, CustomerLead, DealerOnboardingProfile,
ConditionReport, ConditionFinding,
ConditionFindingPhoto, Vendor, ReconDecision, WorkOrder,
WorkOrderFinding, WorkOrderPart, VendorCommunication).

Post-M5.1 count: **17** entries (added `VehicleStage`,
`VehicleStageEvent`). Test coverage:
`test_vehicle_lifecycle_bootstrap.TenancyCarriersExtended`
asserts the count is 17, the new carriers are present,
and every prior carrier is preserved.
`test_vehicle_lifecycle_bootstrap.TenancyAutofillWiredForNewCarriers`
smoke-tests the pre_save autofill wires cleanly for both
new models.

The planning doc's earlier "15/16" wording was
inconsistent — the source-of-truth count was 15 both in
the tuple and in the comment describing it. Amendment §7
M5.1 (in the planning doc) reads 15 → 17.

## Bootstrap migration results

`backend/dealer_ai/migrations/0017_vehicle_lifecycle_persistence.py`:

- Creates both tables (`VehicleStage`, `VehicleStageEvent`).
- Runs the `bootstrap_vehicle_stages` `RunPython` op:
  for every existing Vehicle, inserts one `VehicleStage`
  (`current_stage='frontline'` if
  `Vehicle.is_available=True` else `'off_market'`;
  `trigger='bootstrap'`; `entered_by=None`) AND one
  matching `VehicleStageEvent` (`from_stage=None`;
  `to_stage=<matching>`; `entered_at=<same instant>`;
  `by=None`; `trigger='bootstrap'`; `rule_name=""`;
  `notes=""`). Explicit `dealership` from parent Vehicle
  on both rows (not the pre_save safety net).
- **Idempotent** — skips vehicles that already have a
  stage row. Re-invoking is a no-op past the initial
  bootstrap.
- **Empty-database safe** — no Vehicles → no writes.
- **Reversible** — `unbootstrap_vehicle_stages` deletes
  every `trigger='bootstrap'` stage + event row. The
  subsequent `CreateModel` reverse drops the tables
  entirely.
- **`Vehicle.is_available` untouched** in both
  directions.
- **Single `timezone.now()` value per Vehicle** so the
  event/stage `entered_at`-match invariant is
  enforceable in tests (a second `.now()` call would
  drift by microseconds).

`sqlmigrate 0017` produces expected DDL (two tables +
five indexes on the FK columns) followed by the
`RunPython` marker.

Test coverage of bootstrap behavior lives in
`test_vehicle_lifecycle_bootstrap.py` — 15 tests
covering all 13 invariants listed in the module
docstring: available→frontline, unavailable→off_market,
one stage per Vehicle, one bootstrap event per Vehicle,
event `to_stage` matches stage, event `from_stage`
NULL, matching `entered_at`, matching `dealership`,
empty-DB safety, idempotency, `Vehicle.is_available`
unchanged, reverse cleanup, roundtrip stability.

## Admin behavior

`backend/dealer_ai/admin.py` gains two registrations:

- `VehicleStageAdmin` — diagnostic list/search on
  vehicle stock, current stage, trigger, dealership.
  Autocomplete on `vehicle`/`dealership`/`entered_by`.
  `created_at`/`updated_at` read-only. **No delete
  restriction** (stage rows can be deleted via
  cascade-on-vehicle-delete; direct admin delete is
  permitted).
- `VehicleStageEventAdmin` — append-only display.
  `has_add_permission` returns False (events are
  appended by the M5.2 service, not the admin form).
  `has_delete_permission` returns False (append-only
  history — refusing delete keeps the timeline honest).
  Every field is `readonly` in the change form.

Neither admin surface exposes a transition-authoring
path. That belongs to the M5.4 admin API.

## Tests added

Three new files, 58 focused tests total:

- **`test_vehicle_stage.py`** (18 tests) —
  `VehicleStageChoicesVocabulary` (5),
  `VehicleStageTriggerVocabulary` (1),
  `VehicleStageCreate` (5),
  `VehicleStageOneToOneEnforcement` (2),
  `VehicleStageDealershipRequired` (1),
  `VehicleStageCrossTenantClean` (2),
  `VehicleStageCascadeOnVehicleDelete` (1),
  `VehicleStageNoSideEffectsOnSave` (2),
  `VehicleStageOrderingAndStr` (2). Covers the twelve
  stage choices (including explicit tests that `sold`
  is not shipped, `hold_reserved` is used consistently
  not `hold`, `company_use` is distinct from
  `off_market`, `detail` distinct from `qc`), the four
  triggers, OneToOne enforcement, cross-tenant guard,
  cascade behavior, and the load-bearing "no side
  effects on save" contract (creating or updating a
  `VehicleStage` never auto-creates a
  `VehicleStageEvent`).

- **`test_vehicle_stage_event.py`** (15 tests) —
  `VehicleStageEventCreate` (7),
  `VehicleStageEventAppendable` (1),
  `VehicleStageEventDealershipRequired` (1),
  `VehicleStageEventCrossTenantClean` (2),
  `VehicleStageEventCascadeOnVehicleDelete` (1),
  `VehicleStageEventOrderingAndStr` (3),
  `VehicleStageEventDoesNotMutateCurrentStage` (1).
  Covers appendability (multiple events per vehicle),
  bootstrap-only `from_stage=None` semantics, NOT-NULL
  `to_stage`, cross-tenant guard, cascade, ordering
  (most-recent first), and the load-bearing "creating
  an event does NOT mutate the paired stage's
  `current_stage`" contract.

- **`test_vehicle_lifecycle_bootstrap.py`** (25 tests) —
  Ten test classes covering the 13 bootstrap
  invariants + tenancy-carrier extension + autofill
  safety net. Uses direct invocation of the migration's
  `bootstrap_vehicle_stages` / `unbootstrap_vehicle_stages`
  functions against `django.apps.apps` so tests seed
  Vehicles in setUp and then bootstrap idempotently.

## Backend baseline

- **Pre-session:** 2,518 pass, 1 skipped, 0 fail.
- **Post-session:** 2,576 pass, 1 skipped, 0 fail.
- Delta: +58 tests, 0 regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `python3 manage.py sqlmigrate dealer_ai 0017`
  produces expected DDL (two `CREATE TABLE` + five
  index `CREATE`s).

## Compatibility result

- **Frontend:** untouched. Zero frontend files changed
  (`git status` confirms only backend files + planning
  doc + handoff modified).
- **`Vehicle.is_available`:** schema and values
  unchanged (locked by
  `BootstrapMigrationDoesNotAlterVehicleIsAvailable`).
- **M1/M2/M3/M4 substrate:** every existing model,
  service, permission class, safety-stack scrub, API,
  and frontend behavior unchanged. The 2,518 → 2,576
  test delta is +58 M5.1 tests, not any regressed or
  refactored existing test.
- **Migration graph:** `0016 → 0017` linear, no
  branches, no merged migrations.
- **Tenancy carriers:** 15 → 17 (additive; every prior
  carrier preserved).

## Commit hashes

- Session commit: **TBD** (populate at close before
  overwriting `00-START-NEXT-SESSION.md`).

## Exact recommended scope for M5.2

**M5.2 — Lifecycle service + state machine.** Create
`backend/dealer_ai/services/vehicle_lifecycle.py`. Add
two Vehicle `@property` accessors. Land the four
distinct domain errors.

Service functions (per §1.6 + §7 M5.2 refinements —
no hidden writes from read paths):

- `get_current_stage(vehicle, *, dealership) →
  Optional[VehicleStage]` — pure read. Returns the
  existing row or `None`. Does NOT bootstrap.
- `ensure_current_stage(vehicle, *, dealership,
  actor=None, trigger="bootstrap") → VehicleStage` —
  explicit mutating op. Creates the missing stage row
  and a matching bootstrap `VehicleStageEvent`
  (`from_stage=None`). Idempotent — returns the
  existing row if present.
- `advance_stage(vehicle, *, dealership, to_stage,
  actor=None, trigger, rule_name="", notes="") →
  VehicleStage` — the one authoritative transition
  verb. Calls `ensure_current_stage(...)` first inside
  the transaction (defense-in-depth safety net).
  Validates from→to against the allowed table (§5.b)
  and actor's role authority against the target (§5.f).
  Writes `VehicleStage` update + `VehicleStageEvent`
  row atomically. Uses `transaction.atomic()` +
  `select_for_update()`.
- `retail_eligible(vehicle, *, dealership) → bool` —
  pure read. Returns `False` when no stage row exists.
  Returns True iff `current_stage == VEHICLE_STAGE_FRONTLINE`.
- `suggest_transitions(vehicle, *, dealership) →
  list[SuggestedTransition]` — stub in M5.2; rule
  bodies land in M5.3.

Vehicle `@property` accessors (added in M5.2 alongside
the service — deferred out of M5.1 per §1.6):

- `Vehicle.current_stage` — function-local import;
  delegates to `get_current_stage`; may return `None`.
- `Vehicle.is_retail_eligible` — function-local
  import; delegates to `retail_eligible`; returns
  `False` when no stage row exists.

Domain errors (four distinct classes; do NOT overload):

- `CrossTenantLifecycleError(ValueError)` — cross-tenant
  refusal at service entry. Maps to HTTP 404 at M5.4.
- `InvalidStageTransitionError(ValueError)` —
  structurally illegal from/to per the allowed table.
  Maps to HTTP 409.
- `UnauthorizedStageTransitionError(ValueError)` —
  valid transition attempted by the wrong role per
  §5.f. Maps to HTTP 403. **Distinct from
  `InvalidStageTransitionError`** — SESSION_075
  refinement.
- `StageAlreadyCurrentError(ValueError)` — no-op
  transition refused so callers can distinguish
  "already there" from "moved". Maps to HTTP 409.

Concurrency posture: `transaction.atomic()` +
`select_for_update()` per M4.2 WorkOrder precedent.

Test target: ~50 focused service tests. Baseline
2,576 → ~2,626. Zero regressions. Zero migrations.

**Out of M5.2:**

- No deterministic rule bodies — M5.3 owns
  `_rule_inspection_to_recon`,
  `_rule_recon_to_qc`, `_rule_photography_to_listing`
  (structured unmet prerequisite), and confirmation
  that `listing → frontline` remains manual-only in M5.
- No endpoints — M5.4.
- No retail-gating query refactor — M5.5.
- No frontend — M5.6.
- No Vehicle write-path integration (creating a new
  Vehicle should not auto-seed a stage row via
  pre_save signal; the write-path calls
  `ensure_current_stage(...)` explicitly at M5.5).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — as amended
   at SESSION_075 (§0.a change-log + §1.6 + §5.a-§5.i +
   §7 + §9)
6. `docs/handoffs/SESSION_075_m5_inc1_core_models.md`
   (this doc)
7. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 + §8
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
    §"Data-model changes" + Phase 4
11. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` §6

Narrative docs are claims. Rules + research + code are
facts.
