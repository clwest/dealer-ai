---
title: "Milestone 5 — Implementation-Planning Pass"
status: shipped
type: planning-artifact
generated: 2026-08-01
generated_at_session: SESSION_074 (pre-implementation)
amended_at_session: SESSION_075 (§9 decisions confirmed + no-hidden-writes refinement)
amended_at: 2026-08-01
shipped_at_session: SESSION_081 (M5.7 closeout)
milestone: 5
milestone_name: "Vehicle lifecycle stages + retail gating"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_4_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_4_PLANNING.md
  - docs/roadmap/MILESTONE_3_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_2_RETROSPECTIVE.md
  - docs/BUSINESS_DOMAIN_MAP.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/RECON_MAPPING.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
---

# Milestone 5 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 5 (Vehicle
lifecycle stages + retail gating). Every implementation
increment cites back here for scope, invariants, and
refinement provenance. Mirrors the shape
`MILESTONE_3_PLANNING.md` (SESSION_055) and
`MILESTONE_4_PLANNING.md` (SESSION_065) proved out.

**Business objective (from
`IMPLEMENTATION_ROADMAP.md` §Milestone 5).** Distinguish
"in inventory" from "actually retail-eligible" at the data
layer, so the retail chat only surfaces vehicles that are
truly front-line ready and so aging can be tracked per
stage.

**Zero implementation this session.** Planning artifact
only. SESSION_075 opens M5.1.

---

## 0.a SESSION_075 amendments (2026-08-01)

The four `[NEEDS-DECISION-BEFORE-M5.1]` items were
resolved at the top of SESSION_075 with the following
narrow amendments. Every downstream section (§1.6, §5.a,
§5.b, §5.c, §5.e, §5.f, §5.h, §5.i, §7, §9) was updated
in-place; this block is the change-log entry.

1. **§5.a stage enum — Modified Option C (12 stages,
   `sold` deferred entirely to M9, `company_use` added
   as distinct disposition, `hold_reserved` used
   consistently, `detail` kept distinct in v1).** Do
   not ship an enum value the service will always
   reject. `frontline → sold` is deferred to M9
   alongside the `Sale` model.

2. **§5.b transition table — approved with two
   refinements.** (a) The `hold_reserved → previous
   stage` return resolves the prior stage by reading
   the most recent `VehicleStageEvent` whose
   `to_stage == "hold_reserved"` and using its
   `from_stage`, not by parsing free-text notes. (b)
   Post-frontline operational transitions are
   explicitly allowed: `frontline →
   hold_reserved/off_market/wholesale_out/company_use`.
   There is no `frontline → sold` transition in M5.

3. **§5.c bootstrap — Option C affirmed.** Migration
   `0017` must create BOTH the `VehicleStage` row AND
   a matching bootstrap `VehicleStageEvent` for every
   existing `Vehicle` (`from_stage=None`,
   `trigger='bootstrap'`, matching `entered_at`,
   explicit `dealership`). Not just the current-state
   row.

4. **§5.e `Vehicle.is_available` — Option D affirmed
   without a premature M9 removal date.** Keep intact
   as backwards-compat field. Add
   `is_retail_eligible` as authoritative predicate.
   Refactor known retail consumers in M5.5 (customer
   chat, stock-specific customer vehicle lookup,
   inventory search, public showroom). Document as
   *deprecated for retail exposure; retain until
   every known consumer has migrated and a
   repository-wide audit proves removal safe*.
   `is_available` MUST NOT remain a manual override
   for retail gating — customer-facing eligibility
   comes from lifecycle stage alone.

5. **§5.f role matrix — refined.** Reuse existing
   permission classes (no new broad lifecycle class).
   Recon-adjacent transitions may be performed by
   dealer_owner + sales_manager + recon_manager.
   Commercial/disposition transitions
   (`hold_reserved`, `wholesale_out`, `company_use`,
   `off_market`) may be performed only by
   dealer_owner + sales_manager. `recon_manager` may
   NOT transition into any of the four
   commercial/disposition stages (parts delays are
   represented by M4 `WorkOrderPart` blocker data —
   the vehicle stays in its honest recon stage).
   Introduce a distinct `UnauthorizedStageTransitionError`
   for role refusals (maps to HTTP 403). Do NOT
   overload `InvalidStageTransitionError` (structural
   from/to illegality → 409).

6. **§1.6 architectural refinement — no hidden writes
   from Vehicle properties.** The prior planning
   sketch of `Vehicle.current_stage` delegating to
   `get_current_stage` (which lazily bootstrapped a
   missing row) violates the M2–M4 side-effect-free
   Vehicle-read-model discipline. The M5.2 contract
   splits:
   - `get_current_stage(vehicle, *, dealership)` —
     pure read; returns the existing `VehicleStage`
     or `None`.
   - `ensure_current_stage(vehicle, *, dealership,
     actor=None, trigger="bootstrap")` — explicit
     mutating op; creates the missing stage row and
     a bootstrap `VehicleStageEvent`.
   - `Vehicle.current_stage` — delegates to the pure
     read function; may return `None`.
   - `Vehicle.is_retail_eligible` — pure read;
     returns `False` when no stage row exists.
   - `advance_stage(...)` may call
     `ensure_current_stage(...)` inside its
     transaction before transitioning.
   Migration `0017` creates stage rows for every
   existing Vehicle, so missing rows should occur
   only through an incomplete or future write path.
   New Vehicle creation paths must be explicitly
   updated (in the M5.5 write-path integration
   before retail gating switches) so newly created
   vehicles receive `incoming` — do NOT rely on a
   property read or a generic pre-save signal.

7. **§5.h rule evaluator refinements.** M5.3 rules
   remain suggestions only (no auto-application in
   M5). `inspection → recon` fires when a completed
   `ConditionReport` has ≥1 finding requiring work
   per the final severity vocabulary; a completed
   report with no actionable findings must NOT be
   forced into recon (an explicit path toward
   qc/detail is allowed per the transition table).
   `recon → qc` requires zero open work orders AND
   every `must_do` `ReconDecision` addressed by
   completed `WorkOrder` coverage or explicitly
   resolved by the decision contract. `photography →
   listing` is unavailable until M6 provides the
   photo predicate; return a structured unmet
   prerequisite, NOT a fake suggestion. `listing →
   frontline` is **manual-only in M5**; M6 later
   adds the deterministic published-listing rule
   once `VehicleListing.published` exists. Do NOT
   claim a deterministic published-listing gate
   that cannot be evaluated.

8. **§5.i retail-gating strictness — hard block
   affirmed with truthful customer language.** A
   customer-facing request for a specific
   non-frontline stock number must NOT falsely say
   the dealership does not possess the vehicle.
   Truthful semantics: *"That vehicle is not
   currently available for retail."* Do not expose
   its internal stage, recon details, completion
   estimate, vendor status, or expected-ready date.
   The retrieval filter remains a hard block; this
   is only a customer-language clarification.

The frontmatter `status:` remains `draft` (flips to
`shipped` at M5.7 per §7). Every §5.a-§5.i sub-heading
has been updated in-place with **RESOLVED (SESSION_075)**
banners citing this change-log entry.

---

## 0. Engineering practices to preserve from M2 + M3 + M4

Synthesized from `MILESTONE_2_RETROSPECTIVE.md` §6 (six
lessons), `MILESTONE_3_RETROSPECTIVE.md` §6 (ten lessons),
and `MILESTONE_4_RETROSPECTIVE.md` §6 (ten lessons — seven
inherited + three new to M4). Carry-forward set for M5:

1. **Increment discipline.** Each M5 sub-increment ships
   independently verifiable in one session. If a proposed
   increment cannot be described in one sentence with one
   locked invariant, split it. M3.6 A/B split and the M4.2
   "no ledger stubs" pushback are the load-bearing
   precedents.
2. **Backend-first architecture; frontend never owns
   business rules.** M5 stage transitions live in
   `services/vehicle_lifecycle.py` (new). Any UI affordance
   that appears to gate a transition is UX only — the
   server is authoritative. Same discipline as M4.7.
3. **Provider-neutral boundaries.** M5 has no AI role in
   v1 (per VCP Phase 4 — "flip `search_vehicles` to require
   `stage='frontline'`" is a data + gating milestone, not
   an AI milestone). If a future increment adds AI-drafted
   stage-transition suggestions, they route through the
   shared safety stack via a new `kind="stage_suggestion"`
   dispatch.
4. **Service ownership — one authoritative write path per
   operation.** Every M5 endpoint delegates to
   `services/vehicle_lifecycle.py`; no endpoint calls
   `VehicleStage.objects.update()` or
   `VehicleStageEvent.objects.create()` directly.
5. **Local vs production parity.** Every M5 external
   dependency (there are none in v1 — stage state is
   pure DB) has a local-mode substitute if introduced.
   Same posture as M2 – M4.
6. **Honest verification reporting.** M5 will inherit the
   §1.0.QC-GAP discipline from M4: if the planning
   artifact claims a stage transition means something
   operationally, the shipped surface must actually
   deliver that meaning; otherwise renegotiate the claim
   in a §*.*-GAP annotation.
7. **Storage-first / safer-direction deletion.** M5 does
   not touch storage. If any M5 delete flow surfaces
   (bulk stage cleanup, retire off-market units), it
   follows the M3.5 pattern — safer direction first.
8. **Document implementation refinements immediately.**
   Every reviewed refinement lands in the per-increment
   SHIPPED annotation; the retro synthesizes, does not
   archaeologize. M4 landed 10 refinements this way; M5
   should be at parity.
9. **Compat patches must be honest.** Latent bugs
   surfaced by M5 work get fixed with explicit user-visible
   documentation, not silent absorption.
10. **Avoid architectural drift.** Do not adopt a
    heavyweight state-machine framework (django-fsm,
    transitions) — VCP §"Workflow / state-machine changes"
    explicitly recommends a thin service module. M4.2
    proved the pattern with the WorkOrder state machine
    (7 allowed transitions, no FSM library, ~55 focused
    service tests locking every branch).

---

## 1. Design memo

**Rule from M4 §1: start with the operational questions,
not the models.** Every entry below answers *what
operational question does this subsystem answer?* first,
then *which primitive does it extend?* and *what does it
leave untouched?*

### 1.0 The operational questions Milestone 5 must answer

Twelve questions synthesized from the research corpus
(`INVENTORY_ACQUISITION_MAPPING.md` §6 + §15 +
`RECON_MAPPING.md` §14 + `VEHICLE_CENTRIC_PIVOT.md` Phase
4). These are the acceptance test for whether the
milestone shipped the right thing.

| # | Question | Research citation |
|---|---|---|
| 1 | **What stage is this vehicle in right now?** | `INVENTORY_ACQUISITION_MAPPING.md` §6.1–§6.7 seven categories |
| 2 | **Is this vehicle truly retail-eligible?** (front-line ready) | VCP Phase 4 "flip `search_vehicles` to require `stage='frontline'`" + INVENTORY §6.1 criteria |
| 3 | **When did the vehicle enter its current stage?** (aging per stage) | INVENTORY §1.4 economics of holding + RECON pain #12 recon-ETA mismatch |
| 4 | **What was the full stage history for this vehicle?** (audit trail) | VCP §"Every stage transition — from/to/by/trigger/notes — logged to `VehicleStageEvent`" |
| 5 | **Who authorized each stage transition, and via what trigger?** (manual vs deterministic-rule) | VCP §Deterministic transitions + §Manual transitions |
| 6 | **Which stage transitions should the system suggest based on M4 recon completion?** (system-suggested auto-transitions) | VCP §Deterministic transitions bullet list |
| 7 | **Should an operator be allowed to override a system-suggested transition?** (manual override with logged reason) | VCP §"Manual transitions ... and any override. All logged" |
| 8 | **Which vehicles are aging past healthy thresholds in a given stage?** (bottleneck detection) | INVENTORY §15.2 aging in recon + RECON §14 blockers |
| 9 | **How does the retail chat's inventory retrieval change?** (surface only `stage='frontline'` units) | VCP Phase 4 §"Flip `search_vehicles`" |
| 10 | **What happens to `Vehicle.is_available` — does it retire, refactor, or coexist?** | M1 shipped `is_available` as too-coarse proxy; VCP calls out the transition to computed lifecycle |
| 11 | **What role can transition a stage?** (permission matrix) | Inherited from M1 · 4A role list; M4 · 5.f matrix template |
| 12 | **How does the operator SEE a vehicle's stage + history in the UI?** (M5 frontend surface) | M3.7 + M4.7 operator-UI precedent |

Questions 1-2 belong to the **`VehicleStage`** subsystem
(§1.1). Question 3-4 belong to the **`VehicleStageEvent`**
subsystem (§1.2). Questions 5-7 belong to the
**`services/vehicle_lifecycle.py`** state-transition
service (§1.3). Question 8 is deferred to M8 (operational
intelligence) with the data-generation seam locked here.
Question 9 belongs to the **retail-gating refactor**
(§1.4). Question 10 is the **`is_available`
disposition** load-bearing decision (§5.e). Question 11
belongs to the **permission matrix** (§5.f). Question 12
belongs to the **frontend UI** subsystem (§1.5).

**Questions Milestone 5 does NOT answer** (deliberate,
per `IMPLEMENTATION_ROADMAP.md` §Milestone 5 scope
boundary and VCP Phase 4 non-goals):

- Q: *How long has this vehicle been in the current stage
  compared to peers?* (aging analytics) — Milestone 8
  aggregates the raw `entered_at` data M5 records.
- Q: *Which vehicles need attention right now?* (bottleneck
  warnings) — Milestone 7 async infrastructure. M5
  generates the data; M7 raises the alerts.
- Q: *What should we do about a stuck vehicle?* (action
  recommendations) — Milestone 8 pattern extension.
- Q: *Is this vehicle listed on our website?* (listing
  publish state) — Milestone 6 photography + listing.
  M5's `listing → frontline` transition rule reads
  `Vehicle.price > 0` (already available at M1) but does
  NOT read a listing-published flag until M6 ships the
  `VehicleListing` model.
- Q: *Does this vehicle have current photos?* (photo
  threshold gate) — Milestone 6. M5 exposes the seam
  (a `photography → listing` transition rule that reads a
  `VehiclePhoto.count ≥ N` predicate) but the M6 gate
  itself is deferred until M6 ships the photo gallery.
- Q: *Is this vehicle sold?* — Milestone 9 sale + delivery.
  The `frontline → sold` transition is documented per VCP
  but M5 does NOT ship the `sold` state until M9 lands the
  `Sale` model. See §5.a decision below.

### 1.1 Vehicle stage — `VehicleStage` (OneToOne with Vehicle)

- **Business questions answered.** Q1 + Q2 (via a
  computed `is_retail_eligible` predicate).
- **Citation.** VCP §"Data-model changes (net-new
  models)": `VehicleStage` (1:1 Vehicle) — current stage
  (enum), entered_at. INVENTORY §6 categorization.
- **Fields (planning shape — final in M5.1).**
  - `vehicle` (OneToOne to `Vehicle`,
    `on_delete=CASCADE`; vehicle deletion removes the
    stage row).
  - `dealership` (FK NOT NULL from day one; denormalized
    tenancy carrier — same rationale as every M2/M3/M4
    model).
  - `current_stage` (CharField choices — see §5.a for the
    enum vocabulary decision).
  - `entered_at` (DateTimeField — when the vehicle
    entered its current stage; drives per-stage aging in
    M8).
  - `entered_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL — historical rows survive user deletion).
  - `trigger` (CharField choices: `manual`, `rule`,
    `import`, `bootstrap` — see §5.b state-machine
    trigger enum).
  - `last_transition_note` (TextField blank — the
    operator-supplied reason for the last transition, if
    any; the full audit trail lives on the event log).
  - Standard timestamps.
- **Extend.** OneToOne on `Vehicle`. Zero changes to the
  `Vehicle` model itself — `VehicleStage` sits alongside
  the way `VehicleAcquisition` sits alongside from M2.
- **Leave untouched.** `Vehicle.is_available` field —
  see §5.e disposition decision.

### 1.2 Stage-event log — `VehicleStageEvent` (many-per-Vehicle)

- **Business questions answered.** Q3 (entered_at
  per-stage historical), Q4 (full audit trail), Q5
  (who/what/why per transition).
- **Citation.** VCP §"Data-model changes":
  `VehicleStageEvent` — vehicle FK, from_stage,
  to_stage, entered_at, by (user), trigger
  (manual/deterministic-rule), notes.
- **Fields.**
  - `vehicle` (FK CASCADE — vehicle removal removes the
    orphan event log; the vehicle no longer exists to
    audit).
  - `dealership` (FK NOT NULL from day one).
  - `from_stage` (CharField choices — see §5.a; nullable
    ONLY for the bootstrap event that establishes the
    initial stage; every subsequent event has a
    from_stage).
  - `to_stage` (CharField choices; NOT NULL).
  - `entered_at` (DateTimeField — when the transition
    happened; may differ from `created_at` if the operator
    records a backdated transition).
  - `by` (FK to `AUTH_USER_MODEL`, nullable SET_NULL).
  - `trigger` (CharField choices matching `VehicleStage.trigger`).
  - `rule_name` (CharField blank — when `trigger='rule'`,
    which specific rule fired; e.g.
    `"recon_all_must_do_complete"`).
  - `notes` (TextField blank — the operator's reason for
    a `manual` transition, or the rule's evidence
    summary for a `rule` transition, or the import
    payload's stage-source annotation for
    `trigger='import'`).
  - `created_at` (auto_now_add; distinct from
    `entered_at`).
- **Extend.** New reverse relation on `Vehicle.stage_events`
  (via FK) so read-model queries can walk the timeline.
- **Leave untouched.** Nothing.

### 1.3 Stage-transition service — `services/vehicle_lifecycle.py`

- **Business questions answered.** Q5 + Q6 + Q7.
- **Citation.** VCP §"Workflow / state-machine changes":
  "Recommendation: don't adopt a heavyweight framework
  (django-fsm, transitions). Use a **thin service
  module** — `services/vehicle_lifecycle.py` — with pure
  functions like `advance_stage(vehicle, to_stage, actor,
  reason)`."
- **Shape (planning — final signatures in M5.2).** New
  module `backend/dealer_ai/services/vehicle_lifecycle.py`
  with:
  - `get_current_stage(vehicle, *, dealership) ->
    VehicleStage`. Returns the vehicle's stage row;
    creates a bootstrap row (default stage — see §5.c)
    if none exists. Idempotent.
  - `advance_stage(vehicle, *, dealership, to_stage,
    actor=None, trigger, rule_name="", notes="") ->
    VehicleStage`. The one authoritative transition
    verb. Validates the from → to transition against the
    allowed table (§5.b). Writes both a `VehicleStage`
    update (in-place) and a `VehicleStageEvent` row
    (audit trail). Uses `transaction.atomic()` +
    `select_for_update()` per M4.2 concurrency pattern.
  - `suggest_transitions(vehicle, *, dealership) ->
    list[SuggestedTransition]`. Read-only predicate
    evaluation — walks the deterministic-rule table and
    returns which transitions the M4 recon substrate +
    M1 vehicle data currently satisfy. Callers (M5.4
    admin endpoint + M5.5 operator UI + a possible M5.6
    scheduled scanner) invoke it separately from
    `advance_stage`; suggestion is a suggestion.
  - `retail_eligible(vehicle, *, dealership) -> bool`.
    Convenience predicate — returns True iff
    `get_current_stage().current_stage == "frontline"`.
    Used by the retail-gating refactor (§1.4).
  - Domain errors: `CrossTenantLifecycleError` (ValueError
    subclass), `InvalidStageTransitionError` (ValueError
    subclass — rejected from → to per the allowed table),
    `StageAlreadyCurrentError` (ValueError subclass —
    idempotent no-op refused as an error surface so
    caller distinguishes "already there" from "moved").
- **Extend.** New tenancy resolver call (`get_current_dealership`
  inside the M5.4 endpoints; explicit `dealership=` on
  every service function per M4.2 posture).
- **Leave untouched.** No changes to `services/recon.py`
  or `services/vendor_comm.py` or
  `services/condition_report.py` — M5 reads M4 substrate,
  never writes it.

### 1.4 Retail-gating refactor — chat + inventory-search + operator inventory list

- **Business question answered.** Q9 (retail chat surfaces
  only frontline units).
- **Citation.** VCP Phase 4: "Flip `search_vehicles` to
  require `stage='frontline'`."
- **Shape.** One-line change in
  `services/chat_engine.py::_available_vehicles_queryset`
  (currently filters on `is_available=True`; refactors
  to filter on `stage='frontline'`). Same shape in
  `services/inventory_search.py::search_vehicles` if it
  duplicates the filter. Also touches:
  - `services/chat_engine.py::_vehicle_ask_target` (if
    it independently filters on `is_available`).
  - Public `/showroom` endpoint (currently exposes all
    `is_available=True` vehicles; refactors to expose
    all `stage='frontline'`).
  - Operator inventory list (`/dealer-ai-inventory` +
    the M2.7 / M3.7 / M4.7 cards) — operator can see
    non-frontline vehicles (they need to work on them);
    the change is retail-side only.
- **Extend.** Two new `@property` accessors on `Vehicle`:
  - `Vehicle.current_stage` — one-line delegation to
    `services.vehicle_lifecycle.get_current_stage`
    (function-local import, M2.3 pattern).
  - `Vehicle.is_retail_eligible` — one-line delegation to
    `services.vehicle_lifecycle.retail_eligible`.
- **Leave untouched.** `Vehicle.is_available` field —
  see §5.e disposition decision.

### 1.5 Operator lifecycle UI

- **Business question answered.** Q12 (operator sees
  vehicle stage + history).
- **Citation.** M3.7 + M4.7 operator-UI precedent.
- **Shape.** Route
  `/dealer-ai-inventory/:stock/lifecycle` inside
  `<RequireAuth>`. Page + small extracted components:
  - `VehicleLifecyclePage.tsx` (top-level container).
  - `components/lifecycle/StageBadge.tsx` — reusable
    stage pill (mirrors `WorkOrderStatusBadge` from M4.7).
  - `components/lifecycle/StageTimeline.tsx` — vertical
    timeline of every `VehicleStageEvent` for the vehicle.
  - `components/lifecycle/SuggestedTransitionsPanel.tsx`
    — renders `suggest_transitions()` output as a list
    of one-click "advance to X" buttons (write-role
    only).
  - `components/lifecycle/ManualTransitionForm.tsx` —
    dropdown to any allowed target stage + reason
    textarea (write-role only).
- **Extend.** New route + typed API helpers in
  `frontend/src/lib/api.ts`. "Lifecycle" button on the
  operator inventory card (beside Ledger / Condition
  Report / Recon buttons).
- **Leave untouched.** No changes to M2.7 / M3.7 / M4.7
  pages.

### 1.6 Vehicle read-model extension

- **Business question answered.** Q1 + Q2 aggregated at
  the vehicle level ("what stage right now?", "retail-
  eligible?").
- **Citation.** M2.3 / M3.3 / M4.7 Vehicle-as-read-model
  precedents; §0.a item 6 (no-hidden-writes refinement,
  SESSION_075).
- **Shape.** Two additional `@property` accessors on
  `Vehicle`, delegating to **pure-read** lifecycle
  helpers (no side effects on read):
  - `current_stage` — delegates to
    `get_current_stage(self, dealership=self.dealership)`;
    returns the existing `VehicleStage` row or `None`.
    Does NOT lazily bootstrap.
  - `is_retail_eligible` — delegates to
    `retail_eligible(self, dealership=self.dealership)`;
    returns `False` when no stage row exists.
- **Mutating side of the contract lives in the service,
  not the property.** `ensure_current_stage(vehicle, *,
  dealership, actor=None, trigger="bootstrap")` is the
  one explicit mutating verb that creates a missing
  `VehicleStage` row + a corresponding bootstrap
  `VehicleStageEvent`. Callers use it deliberately:
  - Migration `0017` bootstraps every existing Vehicle
    (see §5.c).
  - `advance_stage(...)` calls
    `ensure_current_stage(...)` inside its
    `transaction.atomic()` block before evaluating the
    transition — a defense-in-depth safety net if a
    write path introduced in a future increment
    forgets to seed the row.
  - The M5.5 Vehicle write-path integration seeds a
    stage row at `incoming` for every newly created
    Vehicle. This is an **explicit call**, not a
    pre-save signal or a property-read side effect.
- **What M5 does NOT add.** No aging computed property
  (M8). No stage-history summary property (M8 / operator
  timeline UI). No "next suggested transition" property
  (the M5.4 endpoint is the surface; a property would
  suggest we invoke on every render). No implicit
  bootstrap from `@property` reads (SESSION_075 refined
  contract; would violate the side-effect-free
  Vehicle-read-model discipline established M2–M4).

### 1.7 What Milestone 5 enables for future milestones

- **Milestone 6 (Photography + listing generation).** M5's
  `photography → listing` transition rule seam consumes
  M6's `VehiclePhoto.count` gate. M5 ships the transition
  hook; M6 provides the predicate.
- **Milestone 7 (Async infrastructure).** M5's per-stage
  `entered_at` timestamps are the input data for aging
  warnings — a Celery task queries "vehicles in stage X
  longer than Y" and raises. M5 generates; M7 warns.
- **Milestone 8 (Operational intelligence).** Aging-per-
  stage dashboards, bottleneck detection, per-stage
  throughput metrics all read the M5 `VehicleStageEvent`
  timeline as source. M5 records the raw events; M8
  aggregates.
- **Milestone 9 (Sale + delivery).** M9 adds the `sold`
  stage (or extends the stage vocabulary if we defer
  `sold` until then per §5.a). M5's transition table has
  the `frontline → sold` row commented out / stubbed;
  M9 fills it in when the `Sale` model exists.
- **Milestone 11+ (Sales-side non-chat channels).** M11
  read paths that surface inventory to third-party
  channels (email blasts, Facebook Marketplace) reuse
  `is_retail_eligible` as the gating predicate.

---

## 2. Migration impact review

Every existing surface Milestone 5 touches, with the
concrete work required. Same shape as
`MILESTONE_4_PLANNING.md` §2 (22 rows).

| # | Existing surface | Location | M5 impact | Required work |
|---|---|---|---|---|
| 1 | `Vehicle` model | `dealer_ai/models.py::Vehicle` | **Additive relationships only.** New reverse `stage` OneToOne (from `VehicleStage`). New reverse `stage_events` FK (from `VehicleStageEvent`). Two new `@property` accessors on `Vehicle` in M5.3 (`current_stage`, `is_retail_eligible`) — delegates to service, no field changes. `is_available` field stays intact per §5.e. | None on `Vehicle` itself. Service layer in M5.2. Property additions in M5.3 (bundled with the service). |
| 2 | `services/chat_engine.py::_available_vehicles_queryset` | `services/chat_engine.py:3116` and callers | **Retail-gating refactor** — filter switches from `is_available=True` to `stage='frontline'` (or an equivalent computed predicate per §5.e). Ripple: existing tests that seed `is_available=True` without a stage row will fail until fixtures update; the M5.6 refactor session ships fixture updates alongside the query change. | Ship in M5.6 as a coordinated change: fixture updates in `_tenancy_helpers.py` + query change + ~30 test updates. |
| 3 | `services/inventory_search.py::search_vehicles` | `services/inventory_search.py` | **Same retail-gating refactor as row 2.** If the module duplicates the `is_available` filter, both flip in the M5.6 change. | Ship in M5.6. |
| 4 | `views.py::public_showroom` / `PublicShowroomPage.tsx` | `views.py` + frontend | **Retail-gating refactor.** Public `/showroom` surfaces only `stage='frontline'`. | Ship in M5.6. |
| 5 | Operator inventory list (`InventoryPreviewPage.tsx`) | `frontend/src/pages/InventoryPreviewPage.tsx` | **Additive.** Operator sees every vehicle regardless of stage. Add a stage badge on each card (extracted `StageBadge` component). Add a "Lifecycle" button next to Ledger/Condition Report/Recon. | Ship in M5.7. |
| 6 | `services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES` | Existing tuple (15 entries at M4 close) | **Additive.** Two new tenant carriers (`VehicleStage`, `VehicleStageEvent`) register with the `pre_save` autofill signal. | Extend tuple in M5.1 (15 → 17). Test coverage extends existing `WritePathFallback.*` matrix. |
| 7 | `dealer_ai/permissions.py` | Existing role classes | **Additive iff M5 needs a new permission class.** See §5.f decision. Two options: (a) reuse `IsSalesManagerOrOwnerAtActiveDealership` if lifecycle admin is manager+owner only; (b) reuse `IsReconManagerSalesManagerOrOwnerAtActiveDealership` if recon_manager can also transition; (c) new class if a different role composition is warranted. Recommend (b). | Ship in M5.4 alongside the endpoints. |
| 8 | `services/audit.py` | (currently minimal; VCP §"`services/audit.py`" flags this for extension) | **Additive iff M5 introduces a dedicated audit log surface.** For M5 v1 the `VehicleStageEvent` model IS the audit log; no `services/audit.py` extension needed. If a future milestone consolidates audit trails, revisit. | None v1. |
| 9 | Customer-facing chat surfaces | `services/chat_engine.py`, `views.py::chat_start` / `chat_message` / `vehicle_ask` | **Retail-gating refactor consequences.** Customer chat still calls `search_vehicles` / `_available_vehicles_queryset`; the underlying filter change is transparent to the chat orchestrator. Customer messaging phrasing may need adjustment IF "available" was a customer-facing term (verify — likely internal). | Verify at M5.6 fixture-and-query change. |
| 10 | Public branding endpoints | `views.py::onboarding_profile` (GET), `views.py::salespeople_list` (public) | **Zero impact.** No branding endpoint reads stage. | None. |
| 11 | Django admin | `admin.py` | **Additive.** Two new admin registrations mirroring M4.1 admin shape. | Ship in M5.1 alongside the models. |
| 12 | `settings.py` | `dealer_kit/settings.py` | **Zero impact.** M5 introduces no env vars in v1. | None. |
| 13 | `requirements.txt` | `backend/requirements.txt` | **Zero impact.** No FSM library adopted per §5.d + carry-forward lesson 10. | None. |
| 14 | Frontend `main.tsx` (route registration) | `frontend/src/main.tsx` | **Additive.** Register `/dealer-ai-inventory/:stock/lifecycle` inside `<RequireAuth>`. Sits alongside M2.7 ledger + M3.7 condition-report + M4.7 recon routes. | Ship in M5.7. |
| 15 | Frontend `lib/api.ts` | `frontend/src/lib/api.ts` | **Additive.** New typed helpers for M5.4 admin endpoints. All via `authFetch`. Zero change to existing helpers. | Ship in M5.7. |
| 16 | Frontend `pages/` | `frontend/src/pages/` | **Additive.** New `VehicleLifecyclePage.tsx` + small extracted components. | Ship in M5.7. |
| 17 | Operator inventory card | `frontend/src/pages/InventoryPreviewPage.tsx` | **Additive.** New "Lifecycle" button + stage badge on each card. | Ship in M5.7. |
| 18 | `services/dealer_config.py` | `services/dealer_config.py` | **Additive iff per-dealer stage thresholds** (e.g. "photography → listing when photos ≥ N" — N is per-dealer). Recommend deferring to M6 when the photo gate becomes real. | None v1. |
| 19 | Existing test suite | `dealer_ai/tests/*.py` | **Additive.** M5 tests use existing helpers (`_auth_helpers.py`, `_tenancy_helpers.py`). No new fixture framework. Test-fixture updates for `is_available` callers land at M5.6 alongside the retail-gating query change. | Ship inside each M5 increment. |
| 20 | Prod deployment | Render Blueprint | **Deferred per M4 §5.j.** M5 is still in-store workflow; no new prod surface. | None v1. |
| 21 | M4 substrate | `services/recon.py`, `services/vendor_comm.py`, models `Vendor` / `ReconDecision` / `WorkOrder` / etc. | **Zero impact.** M5 reads M4 (for the deterministic transition rules that consult `Vehicle.open_work_orders` + `Vehicle.has_recon_decisions`) but never writes M4 data. | None. |
| 22 | M3 substrate | Condition-report models + service + storage + admin API + UI | **Zero impact.** M5 reads `Vehicle.latest_completed_condition_report` for the `inspection → recon` deterministic rule but never mutates M3 data. | None. |

---

## 3. Compatibility checklist

**Milestone 5 ships with this checklist verified true;
evidence recorded inline at milestone close.** Original
invariants preserved from M1 + M2 + M3 + M4; each row
cites the test class, code location, or runtime probe
that locks it. Mirrors the shape M2.8 / M3.8 / M4.9
established.

### Milestone 1 + 2 + 3 + 4 invariants Milestone 5 must not regress

Tenancy substrate:
- [ ] `Dealership` model + migration `0007` unchanged.
- [ ] Every existing tenant-carrying model still has
  `dealership` FK NOT NULL.
- [ ] `services/tenancy.py::get_default_dealership` /
  `get_current_dealership` / `get_active_membership`
  unchanged in signature and contract.
- [ ] M5 tenant carriers (`VehicleStage`,
  `VehicleStageEvent`) register with the `pre_save`
  autofill signal (16 → 17 total).
- [ ] Every new M5 tenant-carrying model has `dealership`
  FK NOT NULL from day one.

Identity + authentication:
- [ ] `DEFAULT_PERMISSION_CLASSES` remains **unset**.
- [ ] `SessionAuthentication` + `TokenAuthentication`
  still installed.
- [ ] `/auth/{login,logout,me}` endpoints unchanged.
- [ ] CSRF still enforced on authenticated mutations.

M1 · 4D + M2.6 + M3.6 + M4.6 permissions:
- [ ] All existing admin endpoints authorized by their
  M1-M4 permission classes unchanged.
- [ ] Cross-tenant pk lookups on all admin endpoints
  still fail closed (404).

Customer-facing surfaces:
- [ ] Public branding renders unauthenticated.
- [ ] Customer chat unchanged in orchestration flow
  (retrieval-filter change is internal).
- [ ] Per-vehicle Q&A unchanged in orchestration flow.
- [ ] No lifecycle event log data appears in any
  customer-facing surface response body.

Safety stack (the moat):
- [ ] All 8 pre-LLM guards fire in existing order.
- [ ] All post-LLM scrubs (including M4.5
  `invented_recon_fact`) unchanged in behavior.
- [ ] Every dollar figure in customer chat still comes
  from `services/payment_engine.py`.

M2 ledger substrate:
- [ ] `services/vehicle_ledger.py` API unchanged in
  signature.
- [ ] `Vehicle.ledger_totals` + delegators unchanged.
- [ ] `VehicleCost` immutability unchanged.
- [ ] `total_investment` semantic contract unchanged.

M3 substrate:
- [ ] `services/condition_report.py` API unchanged.
- [ ] `Vehicle.latest_condition_report` /
  `latest_completed_condition_report` unchanged.
- [ ] `services/photo_storage.py` API unchanged.
- [ ] Completed condition reports remain immutable
  (`ConditionReportImmutableError`).
- [ ] `ConditionFinding.estimated_cost` still
  documentation-only.
- [ ] M3.6A/B admin API + M3.7 operator UI unchanged.

M4 substrate:
- [ ] `services/recon.py` API unchanged in signature
  (M5 reads the two `Vehicle` read-model @property
  accessors + the two service read helpers; never
  writes).
- [ ] `services/vendor_comm.py` API unchanged.
- [ ] `Vehicle.open_work_orders` +
  `Vehicle.has_recon_decisions` @property accessors
  unchanged.
- [ ] `services/llm_safety.py::_scrub_invented_recon_fact`
  unchanged; `apply_post_llm_scrubs(recon_source_bundle=)`
  contract unchanged.
- [ ] M4.6 admin API + M4.7 operator UI unchanged (M5
  frontend adds a new page; M4 pages untouched).
- [ ] `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  permission class unchanged (M5 either reuses or
  composes a new class per §5.f; existing class untouched).

Dealer identity resolution:
- [ ] `get_dealer_name()` + `get_dealer_profile()` +
  `get_floor_plan_apr()` still resolve DB → env →
  default.

Frontend contracts:
- [ ] `useBrand()` + `useDealerProfile()` still resolve
  unauthenticated.
- [ ] `brand.*` Tailwind tokens unchanged.
- [ ] `authFetch` / `AuthContext` / `RequireAuth` /
  `LoginPage` unchanged in contract.
- [ ] `npx tsc --noEmit` clean.
- [ ] `npx vite build` clean.

Test baseline:
- [ ] `python3 manage.py test dealer_ai` → **2,518
  pass** or greater; 1 skipped, 0 fail.
- [ ] No test suppressed with `@skip` to make the
  baseline pass.

### New invariants Milestone 5 introduces

Model-layer:
- [ ] `VehicleStage` is OneToOne with `Vehicle`;
  cascade on vehicle delete.
- [ ] `VehicleStage.current_stage` validated at model
  layer via `choices=` (see §5.a enum decision).
- [ ] `VehicleStage.trigger` validated at model layer
  via `choices=` (see §5.b trigger enum).
- [ ] `VehicleStage` cross-tenant `clean()` guard:
  `dealership` matches `vehicle.dealership`.
- [ ] `VehicleStageEvent` cascade on vehicle delete.
- [ ] `VehicleStageEvent.to_stage` NOT NULL; validated
  via `choices=`.
- [ ] `VehicleStageEvent.from_stage` nullable only for
  the bootstrap event; every subsequent event has a
  non-null from_stage. Enforced at the service layer
  (not model layer, because "bootstrap" is
  service-recognized).
- [ ] `VehicleStageEvent` cross-tenant `clean()` guard
  matching the M4 pattern.

Business-layer:
- [ ] `services/vehicle_lifecycle.py::get_current_stage`
  creates a bootstrap `VehicleStage` row when none
  exists (idempotent — repeat calls return the same
  row).
- [ ] `advance_stage` refuses cross-tenant writes at
  entry.
- [ ] `advance_stage` validates the from → to transition
  against the allowed table (§5.b); illegal transitions
  raise `InvalidStageTransitionError`.
- [ ] `advance_stage` refuses when
  `current_stage == to_stage` (raises
  `StageAlreadyCurrentError`) so callers can distinguish
  no-op from progress.
- [ ] Every `advance_stage` call writes both the
  `VehicleStage` update and a `VehicleStageEvent` row
  atomically inside a `transaction.atomic()` block.
- [ ] `suggest_transitions` is READ-ONLY — never writes
  a `VehicleStage` or `VehicleStageEvent` row. Callers
  who want to act on a suggestion invoke `advance_stage`
  separately.
- [ ] `retail_eligible` is a pure read predicate;
  returns `True` iff `current_stage == "frontline"`.
- [ ] No M5 service function ever creates a
  `WorkOrder`, `VehicleCost`, `ConditionReport`, or
  `ConditionFinding` row — M5 reads M2 + M3 + M4
  substrate only.

Retail-gating refactor:
- [ ] `search_vehicles` filters on stage (per §5.e
  decision) instead of / in addition to `is_available`.
- [ ] `_available_vehicles_queryset` in
  `services/chat_engine.py` uses the same filter.
- [ ] Public `/showroom` endpoint surfaces only
  frontline vehicles.
- [ ] Customer chat cannot recommend a vehicle whose
  current stage is not `frontline`.

Endpoint-layer:
- [ ] Every new M5 admin endpoint composes the
  permission class chosen at §5.f.
- [ ] Every new endpoint calls
  `dealership = get_current_dealership(request)` once
  at top.
- [ ] Every new endpoint's queryset carries explicit
  `.filter(dealership=dealership)`.
- [ ] Cross-tenant `stock_number` / `stage_event_id`
  lookups fail closed (404).

Frontend:
- [ ] Lifecycle page is inside `<RequireAuth>`.
- [ ] Lifecycle page fetch calls use `authFetch`.
- [ ] Anonymous navigation redirects to `/login?next=…`.
- [ ] No stage-event data appears in any customer-facing
  surface.
- [ ] "Lifecycle" button on operator inventory cards
  but NOT on public `/showroom`.
- [ ] Stage badge visually distinct across every stage
  (not merely color; icon + text per M4.7 discipline).
- [ ] Manual-transition affordances gated on role per
  §5.f.

---

## 4. Reusable primitives review

Primitives from `IMPLEMENTATION_ROADMAP.md` §3 cited by
Milestone 5. All should be **extended or directly reused**,
not paralleled.

### §3.5 Vehicle model + inventory identity

- **Reused unchanged.** `VehicleStage.vehicle` OneToOne
  FK; new `Vehicle.current_stage` /
  `Vehicle.is_retail_eligible` `@property` accessors
  mirror M2.3 / M3.3 / M4.7 pattern.

### §3.9 Dealer identity resolver — `services/dealer_config.py`

- **Reused unchanged.** No per-dealer stage-threshold
  field yet — M6 photography introduces the first real
  threshold need. If M5 discovers a per-dealer stage
  policy need (e.g. some indies skip photography entirely
  and go directly from qc to listing), a
  `stage_policy` field could land on
  `DealerOnboardingProfile` — but recommend NOT adding
  in M5 v1; wait for the second consumer.

### Directly reused (no extension) — `services/tenancy.py`

- `_TENANT_CARRIER_MODEL_NAMES` extended 15 → 17 in
  M5.1 (add two carriers). Handler shape unchanged.
- `get_current_dealership(request)` unchanged.
- Every M5 endpoint uses this resolver + explicit
  `dealership=` threading, same as M4.6.

### Directly reused (no extension) — `dealer_ai/permissions.py`

- Per §5.f decision, either reuse
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6) or compose a new class. Existing classes
  untouched either way.

### Directly reused (no extension) — M4 recon substrate

- `Vehicle.open_work_orders` — the deterministic
  `recon → qc` transition rule reads this. When
  `open_work_orders.count() == 0` AND filtered by
  `WorkOrderFinding.finding.severity in
  {"must_do", "safety"}` is empty, the rule fires.
- `Vehicle.has_recon_decisions` — the deterministic
  `inspection → recon` transition rule may read this
  (or read `latest_completed_condition_report.findings`
  directly).
- `services/recon.py::open_work_orders_for_vehicle` and
  `has_recon_decisions_for_vehicle` — M5's rule
  predicates call these directly when the caller has an
  explicit dealership handle (endpoint context).

### Directly reused (no extension) — M3 condition-report substrate

- `Vehicle.latest_completed_condition_report` — the
  deterministic `inspection → recon` transition rule
  reads this. When the vehicle has a completed report
  with ≥1 finding of severity `recommended` or higher,
  the rule fires.

### Directly reused (no extension) — M2 ledger substrate

- M5 does NOT read the ledger. Aging-per-stage is M8
  scope; M5 records the raw `entered_at` timestamps
  M8 will aggregate.

### Genuinely greenfield in Milestone 5

- **`services/vehicle_lifecycle.py`** — new service
  module (design in M5.2). Owns: `VehicleStage` writes,
  `VehicleStageEvent` writes, deterministic-rule
  evaluation, retail-eligibility predicate.
- **`VehicleStage` + `VehicleStageEvent` models + migration
  `0017`** — new persistence layer (M5.1).
- **Two new Django admin registrations** for the M5.1
  models.
- **Stage-transition rule evaluators** — deterministic
  predicates locked at planning §5.b + implemented as
  pure functions in M5.2.
- **Retail-gating refactor** in M5.6 — one-line change
  to the vehicle-search filter, coordinated with
  fixture updates for ~30 downstream tests.

---

## 5. Scope discipline + deferrals

### 5.a Load-bearing decision — Stage enum vocabulary

**Question.** Which set of stages does M5 v1 ship? The
INVENTORY §6 taxonomy names seven categories (front-line
ready, in recon, incoming, wholesale-out, company use,
hold/reserved, off-market). VCP §"Deterministic
transitions" implies more granular sub-stages
(`inspection`, `recon`, `qc`, `photography`, `listing`,
`frontline`, `sold`). Which enum do we adopt?

**Options.**

- **Option A — INVENTORY 7-value taxonomy verbatim:**
  `frontline`, `in_recon`, `incoming`, `wholesale_out`,
  `company_use`, `hold_reserved`, `off_market`.
- **Option B — VCP fine-grained pipeline:** `incoming`,
  `inspection`, `recon`, `qc`, `detail`, `photography`,
  `listing`, `frontline`, `wholesale_out`, `hold`,
  `off_market`, `sold`.
- **Option C — hybrid**: adopt VCP's fine-grained
  pipeline for the retail-preparation pipeline
  (`incoming → inspection → recon → qc → detail →
  photography → listing → frontline`) plus INVENTORY's
  operational categorization terminals (`wholesale_out`,
  `hold`, `off_market`, `sold`). Total 12 stages.

**RESOLVED (SESSION_075) — Modified Option C.** The 12-
stage enum ships in M5.1 as follows:

Retail-preparation pipeline (8 stages):
- `incoming`
- `inspection`
- `recon`
- `qc`
- `detail`
- `photography`
- `listing`
- `frontline`

Operational categories (4 stages):
- `wholesale_out`
- `hold_reserved`
- `company_use`
- `off_market`

Modifications from the original recommendation:

- **`sold` is deferred entirely to M9.** No enum
  constant, no `VEHICLE_STAGE_SOLD` symbol, no blocked
  transition stub in M5. An enum value is a shipped
  state even if the service always rejects transitions
  into it; shipping a state the service refuses is
  dishonest. When M9 lands the `Sale` model and sale
  provenance, M9 will add `sold` to the enum and add
  the `frontline → sold` transition.
- **`company_use` is added as a distinct disposition.**
  Not truthfully equivalent to `off_market`; per
  `INVENTORY_ACQUISITION_MAPPING.md` §6.5 the two
  represent operationally distinct decisions (courtesy
  loaner / dealer-driven inventory vs. removed from
  active availability with no near-term return
  planned).
- **`hold_reserved` used consistently everywhere** in
  code, tests, docs. Do not alternate with the shorter
  `hold` label.
- **`detail` kept distinct in v1.** RECON §4.6 and
  §7.4 treat detail as its own workflow step in some
  stores but bundled with QC in others. Per-dealer
  policy is a future concern; ship v1 with `detail`
  distinct and let operators skip it via manual
  `qc → photography` if their store bundles.

Load-bearing consequences:
- `photography → listing` requires a photo threshold —
  the M6 predicate. M5.3 must return a **structured
  unmet prerequisite** for this transition, not a
  fake suggestion (see §5.h refinement).
- `listing → frontline` is **manual-only in M5**. The
  M5.3 rule evaluator does NOT ship a deterministic
  `listing → frontline` rule; `price > 0` alone is
  insufficient once listing publication matters. M6
  later adds the deterministic rule when
  `VehicleListing.published` exists (§5.h).

### 5.b Load-bearing decision — Allowed transition table + trigger enum

**Question.** Given Option C from §5.a, which
transitions are permitted? Which fire deterministically?

**RESOLVED (SESSION_075) — allowed transitions.**

Retail-preparation forward chain (each transition is
manually advanceable; the ones marked *deterministic
suggestion* also surface via `suggest_transitions()`
per §5.h refinement):
- `incoming → inspection` (manual — indicates vehicle
  physically arrived; or auto via a hypothetical M8
  arrival scanner).
- `inspection → recon` — *deterministic suggestion*
  when a completed `ConditionReport` has ≥1 finding
  requiring work per the final severity vocabulary
  (`recommended` / `required` / `safety`). A completed
  report with **no actionable findings** must NOT be
  forced into recon; the operator is instead offered a
  manual path per the transition table below.
- `recon → qc` — *deterministic suggestion* when
  (a) zero open work orders remain AND (b) every
  `must_do` `ReconDecision` for this vehicle is
  addressed by completed `WorkOrder` coverage or is
  explicitly resolved by the decision contract.
- `qc → detail` — manual (operator confirms QC passed).
- `qc → photography` — manual (operator bundles
  detail with QC — the "detail collapse" escape
  hatch per §5.a).
- `detail → photography` — manual (operator confirms
  detail complete).
- `photography → listing` — no deterministic suggestion
  in M5; the M5.3 evaluator returns a **structured
  unmet prerequisite** ("M6 photo predicate not yet
  available") per §5.h. Manual advancement is
  permitted.
- `listing → frontline` — **manual-only in M5** per
  §5.a. No deterministic suggestion. M6 later adds
  the deterministic published-listing rule when
  `VehicleListing.published` exists.

Operational-disposition escapes (manual only; permitted
from any non-terminal retail-preparation stage —
`incoming`, `inspection`, `recon`, `qc`, `detail`,
`photography`, `listing` — AND from `frontline`):
- `<any retail-preparation or frontline> → wholesale_out`
  — manual with required reason.
- `<any retail-preparation or frontline> → hold_reserved`
  — manual with required reason.
- `<any retail-preparation or frontline> → company_use`
  — manual with required reason.
- `<any retail-preparation or frontline> → off_market`
  — manual with required reason.

Escape returns (any operational-category stage back to
retail-preparation; always manual):
- `hold_reserved → <previous retail-preparation stage>`
  — manual. The service resolves the prior stage by
  reading the most recent `VehicleStageEvent` whose
  `to_stage == "hold_reserved"` and using its
  `from_stage` as the return target. If no valid prior
  retail-preparation stage exists (or the resolved
  `from_stage` is itself operational), the operator
  must explicitly choose an allowed target. **The
  prior stage is NOT stored in `notes` free text** —
  the event log is the durable record.
- `wholesale_out → inspection` — manual (wholesale
  cancelled, unit returns to retail pipeline).
- `company_use → inspection` — manual (company use
  concluded, unit returns to retail pipeline).
- `off_market → inspection` — manual (issue resolved,
  unit returns to retail pipeline).

Terminal:
- `frontline → sold` — **NOT SHIPPED IN M5** per §5.a
  (SESSION_075). No enum value, no service stub, no
  transition entry. M9 introduces `sold` alongside the
  `Sale` model.

Operational escapes (any nonterminal-retail stage →
operational category; always manual):
- `<any nonterminal-retail> → wholesale_out` — manual
  with required reason.
- `<any nonterminal-retail> → hold_reserved` — manual
  with required reason.
- `<any> → off_market` — manual with required reason.

Escape returns (any operational-category stage back to
retail-preparation; always manual):
- `hold_reserved → <previous retail-preparation stage>`
  — manual; system records the previous stage in
  `VehicleStageEvent.notes` for one-click return.
- `wholesale_out → inspection` — manual (wholesale
  cancelled, unit returns to retail pipeline).
- `off_market → inspection` — manual (issue resolved).

Terminal:
- `frontline → sold` — deferred to M9 per §5.a; enum
  value present but transition raises "M9 not shipped"
  error.

**Trigger enum (RESOLVED SESSION_075):** `manual`,
`rule`, `import`, `bootstrap`.

- `manual` = operator initiated.
- `rule` = deterministic rule fired + operator confirmed
  (via suggested-transitions panel). Any event with
  `trigger='rule'` should carry a non-blank
  `rule_name`; the invariant is enforced by the M5.2
  service, not at the persistence layer (documented in
  §1.2 and in the M5.1 model docstring so future edits
  don't split the invariant).
- `import` = seeded from an external import (bulk
  upload, DMS sync).
- `bootstrap` = the initial `VehicleStage` row created
  by `ensure_current_stage()` when no row exists — or
  by the `0017` data migration. `from_stage=None` on
  `VehicleStageEvent` is legitimate ONLY for
  `trigger='bootstrap'`; the M5.2 service enforces
  this, not the persistence layer (documented in the
  M5.1 model docstring).

### 5.c Load-bearing decision — Bootstrap stage for existing vehicles

**Question.** When M5.1 migration `0017` runs against
existing dev / prod data, what stage does every existing
`Vehicle` land in?

**Options.**

- **Option A — All `frontline` by default.** Preserves
  M1 semantics (every `Vehicle.is_available=True` today
  is treated as retail-eligible in the chat). Data
  migration in `0017` inserts a `VehicleStage` row for
  every existing vehicle with `current_stage='frontline'`,
  `entered_at=<now>`, `trigger='bootstrap'`. Existing
  `is_available=False` vehicles get `stage='off_market'`.
- **Option B — Lazy bootstrap.** Migration inserts no
  rows. `get_current_stage` creates the bootstrap row on
  first read. Simpler migration; deferred cost per
  vehicle.
- **Option C — All `frontline` but only for
  `is_available=True`; `is_available=False` becomes
  `off_market`; new vehicles created after M5.1 default
  to `incoming` per §5.c decision.

**RESOLVED (SESSION_075) — Option C affirmed.**
Rationale: preserves the M1 chat behavior for currently-
available vehicles (they stay retail-eligible on the
switch-over); currently-unavailable vehicles are
declared `off_market` (a manual reclassification path
exists via `off_market → inspection`); new vehicles
default to `incoming` because the retail preparation
pipeline is the correct default for a newly-acquired
unit.

Migration `0017` MUST create **two rows per existing
Vehicle**, not just the stage row:

1. **`VehicleStage`** — `current_stage='frontline'` if
   `Vehicle.is_available=True` else
   `current_stage='off_market'`. `entered_at=now()`.
   `trigger='bootstrap'`. `entered_by=None`. Explicit
   `dealership` from the parent Vehicle.
2. **Matching `VehicleStageEvent`** —
   `to_stage=<matching current_stage>`,
   `from_stage=None`, `entered_at=` same value as the
   stage row (not merely "close"; use one `timezone.now()`
   value for both rows in the migration to keep the
   invariant enforceable in tests). `trigger='bootstrap'`.
   `by=None`. Explicit `dealership` from the parent
   Vehicle.

Both rows share `trigger='bootstrap'` and matching
timestamps; the event row establishes the audit-trail
provenance ("this Vehicle entered its initial stage via
the bootstrap migration"). Skipping the event row would
leave a Vehicle whose current stage has no corresponding
event and would silently violate the "every stage the
vehicle occupies has an event" invariant M5.2 relies on
for aging analytics later.

New Vehicles created **after** M5.1 are NOT handled by
the persistence layer in this increment — no pre-save
signal, no bootstrap-on-read side effect (per §1.6
refinement). The Vehicle write-path integration lands
in M5.5 alongside the retail-gating refactor and
explicitly calls `ensure_current_stage(...,
trigger='...')` for every code path that creates a new
Vehicle.

### 5.d Load-bearing decision — State-machine implementation approach

**Question.** Adopt a state-machine library (`django-fsm`,
`transitions`) or hand-code the transition table?

**Options.**

- **Option A — `django-fsm`:** industry-standard; state
  transitions become model methods with `@transition`
  decorators.
- **Option B — hand-coded transition table + pure
  functions:** the M4.2 WorkOrder state machine pattern
  (7 transitions, no library, ~55 tests locking every
  branch).

**Chosen: Option B.** Per VCP §"Workflow / state-machine
changes" explicit recommendation, and per M4 §6 lesson
10 (avoid architectural drift). The M4 state machine
proves testable + maintainable without a library; M5's
larger transition table (~15+ allowed transitions) is
still within the range where hand-coded is superior.
Test discipline is the contract, not a library.

### 5.e Load-bearing decision — `Vehicle.is_available` disposition

**Question.** What happens to the M1 `Vehicle.is_available`
boolean when `VehicleStage` lands?

**Options.**

- **Option A — Remove `is_available` in M5.1
  migration.** Chat / search code refactors to
  `stage='frontline'` filter in a coordinated change.
  Risk: any code path that reads `is_available` and
  isn't updated silently breaks. Locked by test suite.
- **Option B — Keep `is_available` as a shim that
  reflects `current_stage == 'frontline'`.** Convert to
  a `@property` computed from stage. All existing
  `is_available=True` code continues to work.
  Downside: two ways to express the same predicate =
  drift risk.
- **Option C — Keep `is_available` as a
  manually-settable override.** Operator can force a
  vehicle unavailable regardless of stage (temporary
  removal for photography reshoot etc.). Downside:
  breaks the single-source-of-truth promise M5 is
  supposed to establish.
- **Option D — Keep `is_available` as-is (backwards-
  compatible field) but add `is_retail_eligible` as the
  new authoritative predicate.** Refactor
  chat/search/showroom to `is_retail_eligible` in M5.6;
  leave `is_available` for downstream consumers that
  haven't migrated yet (M6/M7/M8 can migrate as they
  land). Downside: two-track state until every consumer
  migrates.

**RESOLVED (SESSION_075) — Option D affirmed, without a
premature removal date.**

`Vehicle.is_available` stays as-is for backwards
compatibility. `Vehicle.is_retail_eligible` (§1.6) is
introduced as the new authoritative predicate for
customer-facing inventory exposure. The M5.5 refactor
migrates the known retail consumers:

- customer chat inventory retrieval
  (`services/chat_engine.py::_available_vehicles_queryset`)
- stock-specific customer vehicle lookup
  (`services/chat_engine.py::_vehicle_ask_target`)
- inventory search
  (`services/inventory_search.py::search_vehicles`)
- public showroom endpoint (`views.py`)

Downstream consumers that are NOT retail exposure
(admin surfaces, internal reports, seed scripts) may
continue reading `is_available` — no forced migration.

**Deprecation note (goes in the M5.1
`Vehicle.is_available` docstring, updated by whichever
increment first touches Vehicle):** *"Deprecated for
retail exposure. Retain until every known consumer has
migrated and a repository-wide audit proves removal
safe."* Do **not** schedule removal for M9 (or any
specific future milestone) — the removal date will be
set by a dedicated audit pass once every downstream
consumer has been enumerated.

**Anti-pattern locked out:** `is_available` MUST NOT
remain a manual override for retail gating. The M1
behavior where an operator could "flip is_available to
False" as a temporary removal is deprecated by M5;
customer-facing eligibility comes from lifecycle stage
alone. If the operator needs to temporarily withhold a
frontline vehicle, the correct action is a
`frontline → hold_reserved` transition (§5.b), not an
`is_available=False` flip. The M5.5 refactor is the
enforcement point.

### 5.f Load-bearing decision — Role permission matrix

**Question.** Which existing roles can transition a stage,
and via which surfaces?

**Existing roles** (all shipped in M1 · 4A):
`dealer_owner`, `sales_manager`, `recon_manager`,
`f_and_i_manager`, `collections`, `advisor`, `porter`.

**RESOLVED (SESSION_075) — refined matrix.**

| M5 surface | dealer_owner | sales_manager | recon_manager | f_and_i_manager | collections | advisor | porter |
|---|---|---|---|---|---|---|---|
| GET lifecycle dashboard (vehicle) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST manual transition (retail-preparation chain) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| POST manual transition (→ hold_reserved) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| POST manual transition (→ wholesale_out) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| POST manual transition (→ company_use) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| POST manual transition (→ off_market) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| POST manual transition (frontline → operational) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| GET suggested transitions | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

**Refinement rationale (SESSION_075).** The prior draft
authorized `recon_manager` to mark `hold_reserved` on
the argument that "recon manager needs to pause a unit
for parts back-order." Reject that framing:
`hold_reserved` is a **sales/customer inventory
commitment** (a specific customer has requested a
hold), not a parts-delay status. Parts delays remain
represented by M4 `WorkOrderPart` blocker data
(`status='backordered'` etc.) while the vehicle stays
in its honest recon stage — the recon manager does not
need to move the vehicle out of recon to signal "waiting
on parts." All four commercial/disposition transitions
(`hold_reserved`, `wholesale_out`, `company_use`,
`off_market`) are gated to `dealer_owner` +
`sales_manager` only.

**Permission class approach — reuse; no new broad
lifecycle class.**

- **Retail-preparation transitions AND the GET surfaces**
  — reuse `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6). The DRF permission layer admits the endpoint.
- **Commercial/disposition transitions** — reuse
  `IsSalesManagerOrOwnerAtActiveDealership` (M2.6). The
  DRF permission layer admits the endpoint.
- **Per-transition role refusal is enforced at the
  service layer.** M5.2's `advance_stage` accepts an
  `actor` and checks role authority against the target
  stage; a `recon_manager` attempting
  `frontline → hold_reserved` raises the new
  `UnauthorizedStageTransitionError`.

**Distinct domain errors (SESSION_075 refinement):**

- `InvalidStageTransitionError` — structurally illegal
  from/to (e.g. `incoming → frontline` skipping the
  pipeline). Maps to HTTP 409.
- `UnauthorizedStageTransitionError` — valid transition
  attempted by the wrong role (e.g. `recon_manager`
  attempting `→ hold_reserved`). Maps to HTTP 403.
- `StageAlreadyCurrentError` — no-op transition
  refused. Maps to HTTP 409.
- `CrossTenantLifecycleError` — cross-tenant refusal.
  Maps to HTTP 404 (fail-closed).

Overloading `InvalidStageTransitionError` for both
structural illegality and role refusal is explicitly
rejected — the two failures have different HTTP
mappings and different remediation paths for the
caller. The M5.2 service is the enforcement point;
M5.4 endpoints just re-raise with the correct HTTP
status code.

### 5.g Load-bearing decision — Aging measurement scope

**Question.** Does M5 v1 measure aging per stage, or
only record the raw `entered_at` for future M8
aggregation?

**Options.**

- **Option A — Ship aging in M5.** Include a
  `days_in_current_stage` property on `Vehicle`; expose
  in the dashboard endpoint.
- **Option B — Ship raw timestamps only.** `entered_at`
  is on `VehicleStage`; the M5.4 endpoint returns
  `entered_at` and lets the frontend compute display
  aging. M8 aggregates historical events for real
  analytics.

**Chosen: Option B.** Per §1.7 (M8 is where aging
analytics land) and per M4 §6 lesson 10 (don't
generalize prematurely). The raw data is the
contract; the M5.5 operator UI can display "in stage
since X (Y days)" without a backend property.

### 5.h Load-bearing decision — Deterministic-rule execution model

**Question.** When do the deterministic transition rules
run? Options:

- **Option A — On-demand only.** `suggest_transitions`
  is the only trigger; the operator sees the suggestion
  in the UI and clicks to accept.
- **Option B — Post-write hook.** After every
  `WorkOrder.status` change (M4.2 completion,
  cancellation), `services/vehicle_lifecycle.py` is
  invoked to re-evaluate suggestions. If a suggestion
  now fires, auto-apply the transition (with
  `trigger='rule'`).
- **Option C — Scheduled scanner.** A Celery task
  (M7) runs every N minutes, evaluates suggestions
  across all vehicles, applies auto-transitions.

**Chosen: Option A for M5 v1.** Rationale: on-demand
suggestion + explicit operator click is the safest
policy. Post-write hooks risk transitioning a vehicle
the operator wasn't ready to promote (e.g. a WO
completed but the operator hasn't verified QC yet).
Scheduled scanners require M7 async infrastructure
(not yet). If operator evidence surfaces the need for
auto-apply, revisit in M7 or later.

**REFINED (SESSION_075) — per-rule boundaries.** The
M5.3 rule evaluators must remain suggestions only. No
auto-application in M5. Individual rule contracts:

- **`inspection → recon`** — fires when a completed
  `ConditionReport` exists AND at least one
  `ConditionFinding` requires work per the final
  severity vocabulary (`recommended`, `required`, or
  `safety`). A completed report with **no actionable
  findings** must NOT be forced into recon — the
  operator gets a manual path toward `qc` (via the
  explicit `qc → detail`/`qc → photography` transitions
  in §5.b) or another allowed target from the
  transition table, not a false recon suggestion.
- **`recon → qc`** — does NOT test only "zero open
  work orders." Also requires every `must_do`
  `ReconDecision` for this vehicle is addressed by
  completed `WorkOrder` coverage OR is explicitly
  resolved through the decision contract. A vehicle
  with an unresolved `must_do` decision and no active
  work order is NOT ready for QC.
- **`photography → listing`** — unavailable until M6
  provides the photo predicate. M5.3 returns a
  **structured unmet prerequisite** describing what
  M6 will provide, NOT a fake suggestion. Manual
  advancement is still permitted (per §5.b).
- **`listing → frontline`** — **manual-only in M5.**
  `price > 0` alone is insufficient once listing
  publication matters. Until M6 provides
  `VehicleListing.published`, either the rule is
  unavailable (structured prerequisite) or the truthful
  v1 rule is manual-only. **Chosen: manual-only.** Do
  not claim a deterministic published-listing gate
  that cannot be evaluated. M6 adds the deterministic
  rule.

Option B is documented as a **planned deferred**
extension: `services/vehicle_lifecycle.py` will expose a
`_evaluate_and_apply_all_rules(vehicle)` helper that
the M7 async layer can call from a Celery task, but the
helper is NOT wired into `advance_stage` calls in M5 v1.

### 5.i Load-bearing decision — Retail-gating strictness

**Question.** How strict is the retail chat's "front-line
only" filter?

**Options.**

- **Option A — Hard block.** Non-frontline units NEVER
  appear in retail chat retrieval. Customer asking about
  a specific stock# that's in recon receives "we don't
  have that vehicle available" — semantically true even
  if physically present.
- **Option B — Soft block with disclosure.** Non-
  frontline units appear with a warning ("currently in
  our reconditioning process; typically ready in ~N
  days"). Sales team can still discuss with the customer.
- **Option C — Configurable per-dealer.** Hard block by
  default; per-dealer override.

**Chosen: Option A for M5 v1.** Rationale: VCP Phase 4
is explicit ("Flip `search_vehicles` to require
`stage='frontline'`"). Soft-block introduces UX
ambiguity + the "in ~N days" number is a promise the
system cannot keep (see RECON pain #12). Sales team who
need to preview upcoming inventory use the operator
inventory list (which shows every vehicle regardless of
stage); customer chat gets the truthful "front-line
only" filter.

**REFINED (SESSION_075) — truthful customer language.**
A customer-facing request for a specific non-frontline
stock number must NOT falsely say the dealership does
not possess the vehicle. The retrieval filter is still
a hard block; this is a language clarification for the
customer-facing chat response when a specific stock
number lookup hits a non-frontline unit:

- **Approved phrasing:** *"That vehicle is not
  currently available for retail."*
- **Prohibited:** exposing the internal stage
  (`"currently in recon"`), recon details, completion
  estimate, vendor status, or expected-ready date.

The safety-stack scrub layer (`services/llm_safety.py`)
already enforces the M4.5 no-invented-recon-fact
contract; the M5.6 customer chat refactor adds a
truthful "not currently available for retail" fallback
copy for stock-specific misses instead of the M1
"we don't have that vehicle" response.

**Deferred:** Option C configurability lands in M6 or
later IF operator evidence surfaces the need. For M5
v1, the hard block is a single-line change with a
per-dealer toggle deferred until real evidence.

### 5.j Load-bearing decision — First-live-prod deployment

**Question.** Same shape as M4 §5.j. M5 introduces the
retail-gating change that customer-facing chat depends
on; does prod deployment happen inside M5, as a
separate pre-pilot increment, or when a real pilot
store is identified?

**Chosen: prod deployment is a separate concern deferred
outside M5** (same rationale as M4 §5.j).

Every M5 workflow ships operator-verifiable against the
local stack. The retail-gating change is coordinated at
M5.6 with test-fixture updates; no live traffic depends
on it before a pilot pilot store engages.

### 5.k Load-bearing decision — Backdated transitions

**Question.** Can an operator record a stage transition
that happened at some prior time (e.g. "the vehicle
actually entered recon last Tuesday; I'm only entering
it now")?

**Options.**

- **Option A — No backdating.** `entered_at` = `now()`
  always. Simple and honest.
- **Option B — Backdating with permission.**
  `dealer_owner` + `sales_manager` can supply an
  `entered_at` earlier than `now()`; other roles cannot.
- **Option C — Backdating always.** Any role that can
  transition can supply `entered_at`.

**Chosen: Option A for M5 v1.** Rationale: honesty
(the timeline reflects when the operator actually
recorded the transition; if a store needs true
backdating, the operator writes it in `notes`).
Backdating opens audit-trail correctness questions
(does the M8 aging metric use `entered_at` or
`created_at`?). Option B / C deferred; if operational
evidence surfaces, add later.

---

## 6. Anchors that win on conflict

If this planning doc disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win.
2. `docs/DOC_GOVERNANCE.md` — the doc governance wins.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5 —
   the roadmap wins on scope questions.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth
   model wins on identity / tenancy / permission
   questions.
5. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 lessons
   — the lessons win on engineering-process questions.
6. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 lessons
   — same weight.
7. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
   — same weight.
8. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4 +
   `INVENTORY_ACQUISITION_MAPPING.md` §6 — the research
   wins on business-truth questions.
9. `docs/CAPABILITY_MATRIX.md` — the matrix wins on
   "what does the software actually do today?" questions.
10. Current source code — the code wins on "what does
    the software actually do today?" questions.

Planning docs are claims. Rules + research + code are
facts.

---

## 7. Increment sequencing

The design memo (§1) describes *what* Milestone 5
delivers. This section records *how* the work is sliced
into per-session increments so each session ends with
the app deployable and the test baseline healthy.

Mirrors the shape `MILESTONE_3_PLANNING.md` §7 +
`MILESTONE_4_PLANNING.md` §7 proved out. **Six
increments** (smaller than M4's nine because the M5
scope is narrower — one new service module + two new
models + one thin frontend page + one retail-gating
refactor). Increment discipline inherited from M4 retro
§6 lesson 1.

### Increment 1 (M5.1) — Core persistence

**Scope (REFINED SESSION_075).** Two new models
(`VehicleStage`, `VehicleStageEvent`) + migration
`0017` (with bootstrap data migration) + admin
registrations + module-level enum constants
(`VEHICLE_STAGE_CHOICES` — 12 values per §5.a
Modified Option C; `VEHICLE_STAGE_TRIGGER_CHOICES` — 4
values per §5.b) + cross-tenant `clean()` guards on
both models + `_TENANT_CARRIER_MODEL_NAMES` tuple
extended 15 → 17. Data migration in `0017` bootstraps
BOTH a `VehicleStage` row AND a matching
`VehicleStageEvent` row for every existing `Vehicle`
per §5.c Option C (existing `is_available=True` →
`frontline`; `is_available=False` → `off_market`;
event has `from_stage=None`, `trigger='bootstrap'`,
`entered_at` matching the stage row's `entered_at`,
`by=None`).

**Not in M5.1 (deferred to M5.2 per §1.6 refinement):**

- No `services/vehicle_lifecycle.py` module.
- No `get_current_stage` / `ensure_current_stage` /
  `advance_stage` / `retail_eligible` /
  `suggest_transitions` functions.
- No `Vehicle.current_stage` or
  `Vehicle.is_retail_eligible` `@property` accessors.
- No transition validation in `VehicleStage.clean()`
  or `VehicleStageEvent.clean()` — persistence layer
  is neutral; the state machine lives in M5.2.
- No auto-event creation from `VehicleStage.save()`.
- No pre-save signal that creates a stage row on new
  Vehicle creation — that write-path integration lands
  in M5.5 as explicit calls.
- No domain errors — those land with the M5.2 service
  (`CrossTenantLifecycleError`,
  `InvalidStageTransitionError`,
  `UnauthorizedStageTransitionError` per §5.f,
  `StageAlreadyCurrentError`).

**Admin surface (M5.1).** Diagnostic only. Both admin
registrations show `current_stage` visible,
`vehicle`/`dealership` searchable, events readable.
Do NOT add transition actions. Where existing admin
conventions permit read-only event fields for
append-only history, use them.

**Tests.** ~40 focused model + migration tests:
schema (dealership FK NOT NULL, choices validation,
OneToOne cascade), all 12 stage choices and all 4
trigger choices exercised, cross-tenant `clean()`
guards, tenancy-carrier registration extends 15 →
17, deterministic ordering, string representations,
no side effects on save (VehicleStage.save() creates
no event; VehicleStageEvent creation does not mutate
current stage), append-only history invariant (event
creation is the only supported way to record history
even though Django technically permits row updates),
bootstrap data migration verifies: available →
frontline, unavailable → off_market, one stage per
Vehicle, one bootstrap event per Vehicle, event
`from_stage` null, event `to_stage` matches stage,
matching `entered_at` values, matching `dealership`
values, empty database safe, rollback + reapply via
`migration_check`, `Vehicle.is_available` schema and
values unchanged.

**Boundary.** Test baseline: 2,518 → ~2,558.

**Invariant locked.** Every M5 persistence-layer
invariant from §3 model-layer subsection is testable at
commit.

### Increment 2 (M5.2) — Lifecycle service + state machine

**Scope (REFINED SESSION_075).**
`services/vehicle_lifecycle.py` module with the
following split per §1.6 (no hidden writes from
read-model properties):

- `get_current_stage(vehicle, *, dealership) →
  Optional[VehicleStage]` — **pure read.** Returns the
  existing `VehicleStage` row or `None`. Does NOT
  bootstrap.
- `ensure_current_stage(vehicle, *, dealership,
  actor=None, trigger="bootstrap") → VehicleStage` —
  **explicit mutating op.** Creates the missing stage
  row and a matching bootstrap `VehicleStageEvent`
  (`from_stage=None`). Idempotent — returns the
  existing row if present. This is the ONE verb that
  creates a stage from nothing; property reads must not
  invoke it implicitly.
- `advance_stage(vehicle, *, dealership, to_stage,
  actor=None, trigger, rule_name="", notes="") →
  VehicleStage` — the one authoritative transition
  verb. Calls `ensure_current_stage(...)` first inside
  its transaction (defense-in-depth for future write
  paths that forget to seed the row). Then validates
  from → to against the allowed table (§5.b) and
  actor's role authority against the target (§5.f).
  Writes `VehicleStage` update + `VehicleStageEvent` row
  atomically. Uses `transaction.atomic()` +
  `select_for_update()`.
- `retail_eligible(vehicle, *, dealership) → bool` —
  **pure read.** Returns `False` when no stage row
  exists (does NOT bootstrap). Returns True iff the
  current stage is `frontline`.
- `suggest_transitions(vehicle, *, dealership) →
  list[SuggestedTransition]` — read-only predicate
  evaluation. Walks the deterministic-rule table.
- Two `@property` accessors added to `Vehicle` in this
  increment (M5.2, alongside the service — not M5.1):
  `current_stage` (delegates to `get_current_stage`;
  may return `None`), `is_retail_eligible` (delegates
  to `retail_eligible`; returns `False` when no stage
  row exists). Function-local imports per M3.3
  pattern.
- `retail_eligible(vehicle, *, dealership) → bool` —
  convenience predicate.
- Domain errors: `CrossTenantLifecycleError`,
  `InvalidStageTransitionError`,
  `StageAlreadyCurrentError`.
- Two `@property` accessors on `Vehicle`:
  `current_stage`, `is_retail_eligible` (function-local
  imports per M3.3 pattern).

**No ledger / recon writes.** `services/recon.py` and
`services/vehicle_ledger.py` untouched. The transition
rules READ M2 + M3 + M4 substrate; they never write.

**Tests.** ~50 focused service tests: bootstrap
idempotency; every allowed transition succeeds; every
disallowed transition raises; state-already-current
raises; `suggest_transitions` fires expected rules under
fixture conditions; `retail_eligible` returns True/False
correctly; no writes to M2/M3/M4 substrate.

**Boundary.** Test baseline: ~2,558 → ~2,608. No
migrations.

**Invariant locked.** Every M5 business-layer invariant
from §3.

### Increment 3 (M5.3) — Deterministic rule evaluators + suggested transitions

**Scope.** Fill in every deterministic rule from §5.b
in `services/vehicle_lifecycle.py`:

- `_rule_inspection_to_recon(vehicle, *, dealership) →
  Optional[SuggestedTransition]` — reads
  `Vehicle.latest_completed_condition_report`; fires
  when ≥1 finding at `recommended` or higher.
- `_rule_recon_to_qc(vehicle, *, dealership) →
  Optional[SuggestedTransition]` — reads
  `Vehicle.open_work_orders`; fires when no open WOs
  linked to a `must_do` or `safety` finding remain.
- `_rule_photography_to_listing(vehicle, *, dealership)
  → Optional[SuggestedTransition]` — **stubbed** per
  §5.a; returns None until M6 photo count exists.
- `_rule_listing_to_frontline(vehicle, *, dealership) →
  Optional[SuggestedTransition]` — reads
  `Vehicle.price`; fires when `price > 0`. The
  `VehicleListing.published` check is a **stubbed**
  additional predicate that returns True until M6
  ships the listing model.

`suggest_transitions` composes every applicable rule
based on the vehicle's current stage.

**Tests.** ~40 focused rule tests: each rule fires
under expected conditions; each rule does not fire
under non-matching conditions; stubbed rules always
return None (M5.3) or the M6-provided predicate value
(post-M6).

**Boundary.** Test baseline: ~2,608 → ~2,648. No
migrations.

**Invariant locked.** Every deterministic-rule
predicate.

### Increment 4 (M5.4) — Admin API + permission matrix

**Scope.** Admin endpoints under
`/api/dealer-ai/admin/vehicles/<stock_number>/lifecycle/`:

- `GET .../lifecycle/` — dashboard: current stage +
  event log + suggested transitions.
- `POST .../lifecycle/transition/` — apply a manual
  transition. Body: `to_stage`, `notes`.
- `POST .../lifecycle/transition/rule/` — accept a
  suggested (rule-triggered) transition. Body:
  `rule_name`. The service re-evaluates the rule at
  apply time and refuses if the predicate has flipped.

Permission classes per §5.f matrix. Domain-error → HTTP
mapping (REFINED SESSION_075 — role refusal is now a
distinct error):
- `CrossTenantLifecycleError` → 404.
- `InvalidStageTransitionError` (structurally illegal
  from/to) → 409.
- `UnauthorizedStageTransitionError` (valid transition
  attempted by the wrong role) → 403.
- `StageAlreadyCurrentError` → 409.
- `ValueError` → 400.

**Tests.** ~40 focused endpoint tests: permission
matrix per endpoint (representative subset; the
permission class is uniform), business flows,
domain-error mapping, cross-tenant fail-closed 404s.

**Boundary.** Test baseline: ~2,648 → ~2,688. No
migrations.

**Invariant locked.** Every M5 endpoint-layer invariant
from §3.

### Increment 5 (M5.5) — Retail-gating refactor + fixture updates

**Scope.** Coordinated change across
`services/chat_engine.py` +
`services/inventory_search.py` + public `/showroom`
endpoint + M1/M2/M3/M4 test fixtures.

Per §5.e Option D: **add** `is_retail_eligible` as the
authoritative predicate; keep `is_available` intact for
backwards compatibility. The retail-side surfaces
refactor to the new predicate:

- `services/chat_engine.py::_available_vehicles_queryset`
  filters on `is_retail_eligible=True` (via a computed
  subquery joining `VehicleStage.current_stage='frontline'`).
- `services/inventory_search.py::search_vehicles` same
  filter.
- Public `/showroom` endpoint same filter.

**Fixture updates.** Existing test fixtures that create
a `Vehicle` and expect it to appear in customer chat
must now also seed a `VehicleStage` row at
`current_stage='frontline'`. New helper in
`_tenancy_helpers.py`:
`bootstrap_stage(vehicle, stage='frontline')` that
inserts a stage row + returns the vehicle.

**Tests.** ~30 focused tests: retail-side surfaces
return only frontline vehicles; non-frontline vehicles
never appear in customer chat / search / showroom;
`is_available=True` alone is NOT sufficient (a vehicle
with `is_available=True` but `stage=in_recon` is not
retail-eligible); existing `is_available` code paths
continue to function for non-retail consumers.

**Boundary.** Test baseline: ~2,688 → ~2,718. **~30
existing test fixtures update** to include stage
bootstrap; the exact count locks at the increment.
Any test that fails only because it lacked a stage
row is a fixture bug, not a regression.

**Invariant locked.** Every M5 retail-gating invariant
from §3.

### Increment 6 (M5.6) — Operator lifecycle UI

**Scope.** Frontend surface:

- Route `/dealer-ai-inventory/:stock/lifecycle` inside
  `<RequireAuth>` in `main.tsx`.
- `frontend/src/pages/VehicleLifecyclePage.tsx` (~400
  lines target — extract components per M4.7
  discipline).
- Small extracted components in
  `frontend/src/components/lifecycle/`:
  - `StageBadge` (reusable pill; mirrors
    `WorkOrderStatusBadge`).
  - `StageTimeline` (vertical timeline of every
    `VehicleStageEvent`).
  - `SuggestedTransitionsPanel` (renders
    `suggest_transitions()` as one-click buttons).
  - `ManualTransitionForm` (dropdown + reason
    textarea).
- Typed API helpers in `lib/api.ts` for every M5.4
  endpoint.
- "Lifecycle" button on operator inventory card
  (beside M2.7 "Ledger" + M3.7 "Condition Report" +
  M4.7 "Recon").
- Stage badge on each inventory card.
- Role gating (per §5.f; write affordances gated to
  `recon_manager` + `sales_manager` + `dealer_owner`).
- Distinct 400 / 401 / 403 / 404 / 409 UX.

**Verification.** `npx tsc --noEmit` clean; `npx vite
build` clean. Backend baseline unchanged. Manual browser
walkthrough deferred to operator first-live-use per M3.7
+ M4.7 honesty precedent.

**Boundary.** Frontend files only. Backend baseline
~2,718 unchanged.

**Invariant locked.** Every frontend invariant from §3.

### Increment 7 (M5.7) — Verification + closeout

**Scope.** Documentation-only session mirroring M3.8 /
M4.9:

- §3 compatibility sweep with evidence citations.
- `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` (mirror
  M4 retro shape).
- `docs/CAPABILITY_MATRIX.md` §7f "Vehicle lifecycle
  stages (Milestone 5, shipped)".
- `IMPLEMENTATION_ROADMAP.md` §M5 marked SHIPPED; §M6
  promoted.
- Frontmatter flip on THIS planning doc:
  `status: shipped`.
- Overwrite `00-START-NEXT-SESSION.md` with M6.0
  priority.

**Boundary.** No code. Backend baseline unchanged.

---

## 8. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/DOC_GOVERNANCE.md` — documentation rules.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
  — scope contract.
- `docs/roadmap/AUTHENTICATION_MODEL.md` — auth
  substrate.
- `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` — §8 M5
  bootstrap notes; §6 lessons.
- `docs/roadmap/MILESTONE_4_PLANNING.md` — shape
  template (M4's 8-section shape mirrored here); §5.f
  permission-matrix pattern reused.
- `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — §6
  lessons.
- `docs/roadmap/MILESTONE_3_PLANNING.md` — shape
  template.
- `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — §6
  lessons.
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` — Phase 4
  (retail-gating), §"Workflow / state-machine changes"
  (thin-service-module recommendation), §"Data-model
  changes" (`VehicleStage` + `VehicleStageEvent`
  shapes).
- `docs/research/INVENTORY_ACQUISITION_MAPPING.md` — §6
  (seven-category taxonomy); §1.4 (economics of
  holding); §15 (recon aging pain).
- `docs/research/RECON_MAPPING.md` — pain #12
  (recon ETA mismatch); §14 (blockers).
- `docs/research/SALES_DEPARTMENT_MAPPING.md` — Sales
  pain #4 (waiting on recon).
- `docs/CAPABILITY_MATRIX.md` — §7d M3 condition-
  report + §7e M4 recon-automation surfaces M5 reads.
- Current source code — authoritative for what M5 is
  building against.

---

## 9. Load-bearing decisions summary — RESOLVED at SESSION_075

Every `[NEEDS-DECISION-BEFORE-M5.1]` in this document
was resolved by the user at SESSION_075 opening. Full
text of each amendment is in §0.a. Consolidated status:

1. **§5.a — Stage enum vocabulary.** **RESOLVED.**
   Modified Option C: 12 stages (retail-preparation
   pipeline `incoming → inspection → recon → qc →
   detail → photography → listing → frontline` +
   operational categories `wholesale_out`,
   `hold_reserved`, `company_use`, `off_market`).
   `sold` deferred entirely to M9 (no enum constant, no
   stub). `company_use` added as distinct disposition
   (not truthfully equivalent to `off_market`). `detail`
   kept distinct in v1. `hold_reserved` used
   consistently everywhere.

2. **§5.b — Allowed transition table.** **RESOLVED.**
   Table as drafted, plus two refinements: (a) escape
   returns from `hold_reserved` resolve the prior stage
   via the last event's `from_stage`, not free-text
   `notes`. (b) Post-frontline operational transitions
   (`frontline → hold_reserved / off_market /
   wholesale_out / company_use`) are explicitly
   allowed. There is no `frontline → sold` transition
   in M5.

3. **§5.e — `Vehicle.is_available` disposition.**
   **RESOLVED.** Option D without a premature removal
   date. `is_available` retained as backwards-compat
   field; `is_retail_eligible` becomes the
   authoritative predicate. Deprecation note: *"retain
   until every known consumer has migrated and a
   repository-wide audit proves removal safe."* NOT
   scheduled for M9 or any specific milestone.
   `is_available` MUST NOT remain a manual override
   for retail gating — customer-facing eligibility
   comes from lifecycle stage alone (M5.5 enforcement
   point).

4. **§5.f — Role permission matrix.** **RESOLVED.**
   Reuse existing permission classes (no new broad
   lifecycle class). Recon-adjacent transitions may be
   performed by dealer_owner + sales_manager +
   recon_manager. Commercial/disposition transitions
   (`hold_reserved`, `wholesale_out`, `company_use`,
   `off_market`) may be performed only by dealer_owner
   + sales_manager. `recon_manager` may NOT transition
   into any of the four commercial/disposition stages —
   parts delays are represented by M4 `WorkOrderPart`
   blocker data while the vehicle stays in its honest
   recon stage. Introduce a distinct
   `UnauthorizedStageTransitionError` for role
   refusals (maps to HTTP 403); do NOT overload
   `InvalidStageTransitionError` (structural
   from/to illegality → HTTP 409).

**Additional refinements (SESSION_075, not from the
four consolidated decisions but load-bearing for M5.1):**

5. **§1.6 — no hidden writes from Vehicle properties.**
   M5.2 contract splits `get_current_stage` (pure
   read; may return `None`) from `ensure_current_stage`
   (explicit mutating op). `Vehicle.current_stage` /
   `Vehicle.is_retail_eligible` land in M5.2 alongside
   the service, NOT in M5.1. Migration `0017` bootstraps
   every existing Vehicle. New Vehicle creation paths
   land in M5.5 as explicit `ensure_current_stage`
   calls.

6. **§5.c — bootstrap must create BOTH stage AND
   event.** Migration `0017` inserts one
   `VehicleStage` AND one matching bootstrap
   `VehicleStageEvent` (`from_stage=None`,
   `trigger='bootstrap'`, matching timestamps,
   explicit dealership) for every existing Vehicle.

7. **§5.h — rule evaluator refinements.**
   `inspection → recon` fires only when a completed
   report has actionable findings per the final
   severity vocabulary. `recon → qc` requires every
   `must_do` decision addressed by completed WO
   coverage or explicitly resolved. `photography →
   listing` returns structured unmet prerequisite (not
   a fake suggestion) pending M6. `listing → frontline`
   is **manual-only in M5**; M6 later adds the
   deterministic published-listing rule.

8. **§5.i — truthful customer language.** Approved
   phrasing for a stock-specific non-frontline lookup:
   *"That vehicle is not currently available for
   retail."* Do not expose internal stage, recon
   details, completion estimate, vendor status, or
   expected-ready date.

Every other §5.a – §5.k decision is either **chosen**
by the planning doc (with rationale) or deferred to a
future milestone (with a home cited).
