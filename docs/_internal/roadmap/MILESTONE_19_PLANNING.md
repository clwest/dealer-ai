---
title: "Milestone 19 — Founding Dealer Pilot Onboarding"
status: shipped
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_152 (skeleton), SESSION_153 (expansion)
shipped_at_session: SESSION_159
shipped_date: 2026-08-02
milestone: 19
milestone_name: "Founding Dealer Pilot Onboarding"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_18_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_18_PLANNING.md
  - docs/roadmap/MILESTONE_17_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/INDEPENDENT_DEALER_PIVOT.md
---

# Milestone 19 — Founding Dealer Pilot Onboarding

> **Active planning memo.** Expanded at
> SESSION_153 M19.0 open from the skeleton
> drafted at M18.6 close. §5.a Option V
> confirmed at open — pilot-customer
> onboarding, targeting the founder-led
> conversion path from a successful demo
> session to a real-store pilot.
>
> **M19 is the empirical follow-on to M18.**
> M18 shipped validation infrastructure
> (three archetypes + 13 daily briefs +
> feedback capture). M19 builds the
> **controlled conversion path** so a
> dealer who completes a demo and says "I
> want to try this with my store" can be
> onboarded without ad hoc database work,
> code edits, or an undefined process.
>
> **This is a non-accounting target** —
> the second since M12. Unlike M18, M19
> touches every layer (schema + service
> package + endpoints + frontend +
> playbook doc) but is explicitly
> **not** a broad UX-polish or new-
> capability milestone. The scope is
> narrowly the pilot conversion + safety
> substrate.
>
> **Eight load-bearing decisions** —
> §5.a target + §5.b through §5.h on
> eligibility, tenancy separation,
> creation service, inventory import,
> capability enablement + checklist,
> outbound posture, and termination +
> consulting boundary. **All eight
> confirmed as-recommended at SESSION_153
> M19.0 open** — streak extends to **85
> planning-time as-recommended M5.1 →
> M19.0 across ten consecutive
> milestones** (M10 + M11 + M12 + M13 +
> M14 + M15 + M16 + M17 + M18 + M19).
> Historical §5 counts have been 6-7;
> M19 at eight reflects the pilot-
> onboarding scope's breadth (fourteen
> planning topics compressed into eight
> decisions).

## 0. Engineering practices to preserve from M2-M18

Same posture as M18.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend. The
  M19.4 pilot admin surface is
  configuration UI over service verbs;
  no client-side pilot lifecycle logic.
- **Service ownership.** One
  authoritative write path per operation.
  New `services/pilot_onboarding/`
  package is the ONLY entry point for
  pilot dealership creation +
  termination + checklist advancement.
- **Tenancy discipline.** Every write
  path passes `dealership=` explicitly;
  the pre_save autofill is a safety net.
  M19 adds `is_pilot` alongside
  `is_demo` — every tenant carrier stays
  tenancy-scoped without exception. No
  parallel model, no parallel auth path.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M18 convention
  (404 cross-tenant, 409 state-machine
  / duplicate, 400 vocab / validation,
  500 broken-invariant `RuntimeError`
  subclasses per M15.1 + M16.1 + M17.1
  + M18.1 posture).
  **M19.1 introduces new domain
  exceptions**:
  - `PilotAlreadyExistsError` — 409
    when a slug collides with an
    existing pilot (or demo, or live)
    dealership.
  - `NonPilotTerminationError` — 500
    if `terminate_pilot` is called
    against a non-pilot dealership
    (broken-invariant).
  - `PilotReadinessNotConfirmedError`
    — 409 if a caller tries to
    activate a pilot before all
    checklist steps are complete.
- **Load-bearing decisions get user
  review BEFORE code.** All eight §5
  decisions confirmed at SESSION_153
  M19.0 open. Any implementation-time
  micro-decisions surface as §0.a
  amendments.
- **Additive extension over fork.**
  `Dealership` gains three additive
  columns (`is_pilot` + `terminated_at`
  + `termination_reason`) via one
  migration bundling the M19.1 schema
  additions. Existing model not forked.
  Existing seeds preserved.
- **Every M19 test asserting tenant-
  carrier / permission-class /
  endpoint counts uses `>=N`** per
  M9-M18 growth-only-list lesson.
  **Vocab-set + permission-class-set
  assertions use exact equality** per
  M11-M18 fixed-vocab lesson.
- **Read-only surfacer vs state-
  transitioning detector vs sync
  sibling-service** — pilot creation
  + termination are operator intent
  (sync sibling per M13 §5.d Option C
  + M15.1 / M17.1 / M18.1 proof);
  checklist step advance is sync
  sibling. No detectors at M19.
- **Atomic sibling-service boundary
  crossings.** `create_pilot_dealership`
  wraps Dealership create + COA seed +
  UserDealershipRole + Profile
  population in `@transaction.atomic`.
  Partial pilot creation is
  architecturally impossible.
- **Denormalize at write; recompute
  in detectors; refresh AFTER sibling
  writes.** Per M12 / M13.2 / M14 /
  M15 / M16.1 / M17.1 / M18 pattern.
- **Split pure verbs from write
  verbs.** `list_pilot_dealerships` +
  `list_pilot_prospects` are pure
  reads; `create_pilot_dealership` +
  `advance_checklist_step` +
  `terminate_pilot` are write verbs.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  AND
  `IsDealerOwnerAtActiveDealership`
  by default. **Fourteen consecutive
  milestones now** per M18 §6 lesson
  7. M19 endpoints must not add a
  new permission class.
- **Broken-invariant guards as
  cross-milestone contracts.** Per
  M17 §6 lesson 4 + M18 §6 lesson 4.
  M19.1 introduces
  `NonPilotTerminationError` and
  `PilotReadinessNotConfirmedError`
  as broken-invariant guards.
- **Duplicate constants across
  submodules** per M15.1 + M16.1 +
  M17.1 + M18.1 posture — but M19
  doesn't introduce new account
  codes (§3 item 8).
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson
  15 / M13.3 / M14.1 / M17.1 / M18
  (`ScenarioSummary`) posture. M19
  introduces `PilotInventoryImportResult`
  frozen dataclass returned by the
  M19.2 CSV import verb.
- **Naming discipline** per M17 §6
  lesson 3. Durable entities earn
  clear names: `PilotProspect` (pre-
  pilot tracking), `PilotOnboardingChecklist`
  + `PilotOnboardingStep` (progress
  tracking).
- **`IntegrityError` → domain
  exception at service boundary** per
  M17 §6 lesson 4 + M18 §6 lesson 4.
  `create_pilot_dealership` catches
  `IntegrityError` on slug collision
  + re-raises as
  `PilotAlreadyExistsError`.
- **Zero-portfolio semantics.** A
  freshly-created pilot dealership
  (before any inventory imported) is
  a valid state — `list_pilot_dealerships`
  returns it with an empty inventory
  count; the M19.4 admin surface
  shows the pilot with a "no
  inventory yet" empty state.
- **Money on the wire is Decimal-
  as-string** per M9-M18 convention.
  Pilot inventory import validates
  price fields as Decimal.
- **Test-fixture invariants match
  migration invariants.** Per M15
  §6 lesson 3 + M16.1 + M17.1 +
  M18.1 verified. **M19 tests use a
  new `make_pilot_dealership(...)`
  helper** in
  `tests/_auth_helpers.py` that
  wraps `make_dealership` + sets
  `is_pilot=True` + populates
  minimal `DealerOnboardingProfile`
  fields.
- **In-place page extension over
  new route** per M17 §6 lesson 6.
  M19.4 pilot admin surface
  extends an existing admin route
  in place. Frontend operator
  routes stay at **20**.
- **Native browser primitives +
  shadcn `Input` wrapper as the
  default** per M17 §6 lesson 5.
  M19.4 form fields use native
  inputs wrapped in shadcn
  primitives.
- **Coherence contract per M18 §6
  lesson 2** — the checklist steps
  + PilotProspect fields must tell
  a connected onboarding story;
  Chris's playbook references them
  by name.
- **Scanner tests for guard-by-
  construction contracts** per M18
  §6 lesson 3. The M18.1
  outbound-egress scanner extends
  to cover pilot dealerships via
  the new
  `is_synthetic_tenant()` helper
  (§5.g).
- **Belt-and-suspenders guards** per
  M17 §6 lesson 4 + M18 §6 lesson 4.
  M19.1 `terminate_pilot` raises
  `NonPilotTerminationError` + asserts
  `dealership.is_pilot` at write-
  verb top.

### 0.a Change log — resolved decisions

**SESSION_153 M19.0 open (2026-08-02):**

- **§5.a → Option V confirmed at
  open.** User named — pilot-
  customer onboarding. Milestone
  name: **"Founding Dealer Pilot
  Onboarding."** Tester sessions
  have not happened since M18 close,
  so Option T (process tester
  feedback) stays deferred for a
  future milestone. Option V builds
  the controlled conversion path
  from demo → pilot so testers who
  commit have a place to land.
- **§5.b → Option C confirmed as-
  recommended.** Hybrid `PilotProspect`
  entity with structured note fields
  (`dealer_type`, `bhph_enabled`,
  `estimated_inventory_size`,
  `contact_source`, `chris_notes`)
  + operator-owned `eligibility_state`
  state machine (`prospect` →
  `qualified` → `converted` OR →
  `declined`). Structured enough for
  post-pilot pattern analysis; loose
  enough that Chris isn't fighting a
  rigid gating verb during the first
  pilots.
- **§5.c → Option A confirmed as-
  recommended.** Add
  `Dealership.is_pilot
  BooleanField(default=False)`
  mirroring M18's `is_demo` shape.
  Preserves the M18 `is_demo`
  invariant (no data migration on
  existing seeded rows). New
  `is_synthetic_tenant(dealership)
  -> bool` helper (`is_demo or
  is_pilot`) extends the M18.1
  outbound guard.
- **§5.d → Option A confirmed as-
  recommended.** New
  `services/pilot_onboarding/`
  package with `create_pilot_dealership(*,
  slug, name, owner_user,
  profile_kwargs) -> Dealership`
  atomic verb. Sibling to
  `services/demo_store/registry`.
  Both packages consume shared
  M13.1 `seed_default_coa` + M1
  `UserDealershipRole` primitives.
- **§5.e → Option A confirmed as-
  recommended.** Extend M6.3
  substrate with
  `PilotInventoryImportResult`
  frozen dataclass. Per-row
  accepted/rejected + errors. **No
  silent defaulting for dirty data**
  — Chris hand-cleans rejected rows.
  Documented pilot template in
  `docs/PILOT_INVENTORY_TEMPLATE.md`
  ships at M19.5.
- **§5.f → Option A confirmed as-
  recommended.** Capability gating
  reads existing
  `DealerOnboardingProfile` fields.
  New `PilotOnboardingChecklist`
  (one per pilot; CASCADE FK) +
  `PilotOnboardingStep` (many;
  fixed vocab: `dealership_created`,
  `profile_configured`,
  `owner_user_added`,
  `staff_users_added`,
  `inventory_imported`,
  `capabilities_enabled`,
  `readiness_confirmed`). Tenancy
  carriers 50 → **52** (+2 for
  the two new checklist entities;
  `PilotProspect` from §5.b lands
  as tenancy carrier **53** —
  though PilotProspect is scoped
  to Chris's operator surface,
  not a specific dealer tenant;
  see §5.b write-up for the FK
  posture).
- **§5.g → Option A confirmed as-
  recommended.** Extend the M18.1
  outbound guard to include
  pilots. `is_synthetic_tenant()`
  wraps `is_demo or is_pilot`.
  **All outbound suppressed by
  default for pilots.** Per-verb
  opt-in gated on future code
  review. Documented in the M19.5
  playbook.
- **§5.h → Option A confirmed as-
  recommended.** New
  `terminate_pilot(*, dealership,
  reason, actor, mode) ->
  Dealership` atomic verb. Two
  additive `Dealership` columns:
  `terminated_at` +
  `termination_reason`. `mode='archive'`
  preserves child rows; `mode='cleanup'`
  cascades reverse-order per
  M18.2 pattern. Boundary policy
  documented in
  `docs/PILOT_ONBOARDING_PLAYBOOK.md`
  at M19.5.
- **§7 sequencing → seven-
  increment shape confirmed as-
  recommended.** M19.0 planning +
  M19.1 substrate + M19.2 CSV
  import + M19.3 endpoints + M19.4
  frontend + M19.5 playbook +
  end-to-end dry run + M19.6
  close-out.
- **Streak extends to 85
  planning-time as-recommended
  M5.1 → M19.0.** Ten consecutive
  milestones now (M10 + M11 +
  M12 + M13 + M14 + M15 + M16 +
  M17 + M18 + M19). All eight
  §5 decisions confirmed as-
  recommended. Historical §5
  counts have been 6-7; M19 at
  eight reflects the pilot-
  onboarding scope's breadth.

## 1. Business questions this milestone answers

Six operator-workflow / commercial-
readiness questions, each tied to
the pilot conversion path. Every
question was unanswerable before
M19 (M18 shipped demo infrastructure
but no conversion path).

### Q1. Can Chris convert a demo tester into a real pilot dealer without ad hoc database work?

**Before M19:** No. Converting a
committed tester would require Chris
to open Django admin, create a
Dealership row, seed the default
COA manually, add a `UserDealershipRole`,
populate `DealerOnboardingProfile`
by hand, and hope no invariants got
missed. Every conversion would be a
one-off — un-reviewable, un-
repeatable, and prone to breaking
the tenancy or authorization
contracts.

**After M19:** Yes. `create_pilot_dealership(*,
slug, name, owner_user, profile_kwargs)`
atomic verb + the M19.4 admin form.
One command creates the Dealership
+ seeds the COA + attaches the
owner + populates the profile in
one transaction. Chris fills the
form; the service verb ensures the
invariants hold.

### Q2. Can Chris safely ingest a pilot dealer's initial inventory?

**Before M19:** Only via one-off
scripts or manual admin entry. The
M6.3 inventory import substrate
exists but was scoped for
franchise-style feeds with clean
data. A pilot dealer's spreadsheet
export might have missing prices,
inconsistent stock numbers, or
unfamiliar make/model combinations.

**After M19:** Yes. The M19.2
extension of the M6.3 substrate
adds a `PilotInventoryImportResult`
frozen dataclass carrying per-row
accepted / rejected + errors. Chris
uploads the dealer's spreadsheet;
the verb reports which rows landed
and why others didn't. Dirty rows
are surfaced explicitly for
hand-cleanup — no silent
defaulting. Chris re-imports after
cleaning.

### Q3. Can Chris avoid demo data crossing into a pilot store?

**Before M19:** The M18.1
`is_demo` flag distinguishes demo
dealerships. But nothing prevents
Chris (or a future refactor)
from accidentally copying
synthetic demo customers, sales,
or notes into a live pilot
store during onboarding.

**After M19:** Yes. The
`is_pilot` flag distinguishes
pilot dealerships. The
`create_pilot_dealership` verb
never touches the demo-store
scenario builders. The
`is_synthetic_tenant()` helper
extends the M18.1 outbound guard
so pilots inherit the "no
outbound to real destinations
without explicit code-reviewed
opt-in" posture. Terminating a
pilot with `mode='cleanup'`
preserves the Dealership row's
audit trail (via `terminated_at`
+ `termination_reason`) without
leaking customer PII into
post-mortem review.

### Q4. Can Chris track pilot onboarding progress + know when a pilot is ready to run?

**Before M19:** No. Onboarding
progress was Chris's mental model.
Whether a pilot was "ready" was a
subjective call. No audit trail.

**After M19:** Yes.
`PilotOnboardingChecklist` +
`PilotOnboardingStep` capture the
seven-step onboarding sequence.
`readiness_confirmed` is the
explicit sign-off step Chris
advances only after every prior
step is complete. Pilot dealer
operator access is gated on
`is_ready=True`.

### Q5. Can Chris gate shipped capabilities per pilot store's shape?

**Before M19:** Partially.
`DealerOnboardingProfile` fields
(`dealer_type`, `bhph_enabled`,
etc.) already exist. But the
capability-conditional gating
logic wasn't consistently applied
across the shipped surface for
non-BHPH stores.

**After M19:** Yes. M19.1 codifies
which capabilities are conditional
on which profile fields. The
`capabilities_enabled` checklist
step records Chris's explicit
per-pilot enablement decisions.
A non-BHPH pilot dealer never
sees the M12 BHPH portfolio
surfaces; a non-floor-planned
dealer never sees the M6 floor-
plan interest accrual.

### Q6. Can Chris terminate a failed pilot cleanly?

**Before M19:** No. Terminating a
pilot would require Chris to
manually decide whether to
delete rows, disable operator
access, preserve audit trail, or
some combination. No structured
process.

**After M19:** Yes. `terminate_pilot(*,
dealership, reason, actor, mode)`
verb captures the termination
decision. `mode='archive'`
preserves child rows for post-
mortem review; `mode='cleanup'`
cascades reverse-order per M18.2
pattern (child-before-parent for
PROTECT FKs; demo-owned Users
cleared). Termination reason +
timestamp captured on the
Dealership row for audit trail.

## 2. What existing primitives extend

M19 continues the "additive
extension over fork" pattern
(M11.1 / M12.3 / M13.2 / M14.1 /
M15.1 / M16.1 / M17.1 / M18.1).
One new package, one migration,
four new endpoints, one new
frontend admin surface extension,
two new markdown docs, and
extensions to two existing
guard helpers.

### Persistence + tenancy

- **`Dealership` model.** Gains
  three nullable-safe additive
  columns per §5.c Option A +
  §5.h Option A: `is_pilot`
  BooleanField default False +
  `terminated_at`
  DateTimeField(null=True,
  blank=True) +
  `termination_reason`
  TextField(blank=True,
  default=""). Existing rows
  default `is_pilot=False`; no
  data migration needed.
- **`_TENANT_CARRIER_MODEL_NAMES`
  in `services/tenancy.py`.**
  Extended by three for
  `PilotProspect`,
  `PilotOnboardingChecklist`,
  `PilotOnboardingStep`. Count
  50 → **53**.
- **`_auth_helpers.make_dealership`.**
  Gains a companion
  `make_pilot_dealership(...)`
  helper that wraps
  `make_dealership` + sets
  `is_pilot=True` + populates
  minimal
  `DealerOnboardingProfile`
  fields for M19+ test
  fixtures.
- **M18.1 `is_demo_dealership()`
  helper** in
  `services/demo_store/outbound_guard.py`
  — extended to cover pilots via
  new `is_synthetic_tenant()`
  helper: `is_demo or is_pilot`.
  The M18.1 outbound scanner
  test continues to enforce
  guard-by-construction; the
  new helper is a drop-in
  extension.

### Service package additions

- **New
  `services/pilot_onboarding/`
  package** mirroring the M18.1
  `services/demo_store/`
  posture:
  - `errors.py` —
    `PilotAlreadyExistsError`,
    `NonPilotTerminationError`,
    `PilotReadinessNotConfirmedError`.
  - `registry.py` —
    `create_pilot_dealership`,
    `list_pilot_dealerships`,
    `terminate_pilot`.
  - `prospects.py` —
    `create_prospect`,
    `advance_prospect_state`,
    `list_prospects`.
  - `checklist.py` —
    `create_checklist`
    (auto-fires from
    `create_pilot_dealership`),
    `advance_step`,
    `is_pilot_ready(dealership)`.
  - `inventory_import.py` —
    `PilotInventoryImportResult`
    frozen dataclass +
    `import_pilot_inventory`
    verb (extends M6.3
    substrate).
  - `__init__.py` — public API
    `__all__`.

### Consumed but not modified

- **M13.1 `seed_default_coa`** —
  called by
  `create_pilot_dealership`
  atomically after Dealership
  creation. Unchanged.
- **M1
  `UserDealershipRole`** — new
  membership row created for
  the pilot owner. Unchanged.
- **M0/M31
  `DealerOnboardingProfile`** —
  populated from
  `profile_kwargs` during
  pilot creation. Field set
  unchanged.
- **M6.3
  `services/inventory_import`
  substrate** — extended with
  `PilotInventoryImportResult`
  return shape; existing verb
  posture preserved for
  franchise-feed use.
- **M18.1 outbound-egress
  scanner test** — continues to
  enforce the guard-by-
  construction contract; the
  new `is_synthetic_tenant()`
  helper is a drop-in
  extension.

## 3. What's NOT in this milestone (deferrals)

Every deferral recorded with a
clear re-entry path. **Ten M19-
specific + eleven universal = 21
deferrals.** Slightly fewer than
M18's 26 because M19's scope is
more focused (pilot conversion
path, not a broad validation
substrate).

**M19-specific deferrals:**

1. **Public self-serve demo
   signup.** Pilots remain
   founder-led; testers are
   hand-provisioned by Chris.
   A public signup path (Option
   U from M18 §8) defers to a
   hosted-demo milestone.
2. **Billing / subscription
   implementation.** Pilots
   don't pay yet — the
   commercial signal is
   captured via M18.5
   `TesterFeedback` +
   post-pilot review. Billing
   infrastructure defers to a
   future commercial-shell
   milestone.
3. **Automatic conversion of
   demo records into pilot
   records.** No synthetic
   customers / deals /
   accounting entries /
   inventory land in a pilot
   store. Explicit non-goal
   per user brief.
4. **Real SSN / bureau / bank-
   account / payment-card /
   lender-credential intake
   unless a shipped capability
   already has a reviewed
   compliant storage path.**
   Pilot dealers use their
   existing external tools
   for credit apps + bank
   deposits + payment
   processing during M19.
5. **DMS integration.**
   Explicit non-goal.
6. **Broad enablement of every
   shipped capability per
   pilot.** Only capabilities
   matching the pilot's
   `DealerOnboardingProfile`
   are surfaced.
7. **Public feedback capture
   endpoint for pilot
   dealers.** Pilots use the
   M18.5 `TesterFeedback`
   endpoint; no separate
   pilot-only feedback
   surface at M19.
8. **New account codes for
   pilot-specific accounting
   scenarios.** M13.1 default
   COA is sufficient; if a
   pilot's book demands new
   codes, that surfaces as an
   M19.5 playbook gap and
   defers to a follow-on
   milestone.
9. **Multi-pilot dashboards /
   comparison surfaces.** M19
   supports one pilot at a
   time from the operator
   surface's perspective; if
   Chris runs three parallel
   pilots, the surface treats
   each independently.
10. **Programmatic pilot
    onboarding via CI or
    external system.** Chris
    is in the loop for every
    pilot creation +
    checklist advance at M19.

**Universal deferrals (any
platform milestone):**

- Payroll (external service).
- W-2 / 1099 generation
  (external service).
- Year-end tax return
  preparation (external CPA).
- GAAP-compliant audited
  financial reporting (out of
  scope for platform v1).
- Direct DMS integration
  (belongs to a future
  vendor-integration
  milestone).
- Real inventory-feed
  integrations
  (Manheim / ADESA / ACV).
- Bilingual UI.
- Payment processing / e-
  sign / DMS write-back.
- Multi-tenant SaaS shell
  (billing / org).
- Predictive ML on
  operational data.
- SSO / MFA on top of M1
  auth.

## 4. What existing tests bind

- **M18 tenancy carrier count
  test** — currently `>=50`.
  M19 adds three new tenanted
  models (`PilotProspect`,
  `PilotOnboardingChecklist`,
  `PilotOnboardingStep`);
  count moves to **>=53**.
  Assertion uses `>=` per
  M9-M18 growth-only-list
  lesson.
- **Permission-class count
  test** — M19 adds zero new
  endpoints requiring new
  permission classes.
  Endpoints reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  and
  `IsDealerOwnerAtActiveDealership`.
  **Zero-drift streak extends
  to fifteen consecutive
  milestones** (M10 → M19).
- **Endpoint count** — DRF
  admin surface 108 → 112
  (+4 at M19.3: pilot
  create + list + checklist
  step advance + terminate).
  Assertion uses `>=` per
  lesson.
- **Migration count** —
  `0043`-`0047` → `0043`-
  `0048` (+1 at M19.1
  bundling all M19 schema
  additions).
- **Frontend operator route
  count** — 20 (unchanged —
  M19.4 extends an existing
  admin route in place per
  M17 §6 lesson 6).
- **Celery-beat task
  families** — 10 (unchanged
  — M19 has no beat entry).
- **M18.1 outbound-egress
  scanner test** — continues
  to hold. The
  `is_synthetic_tenant()`
  helper is a drop-in
  extension of
  `is_demo_dealership()`;
  the scanner allowlist is
  unchanged.
- **`_auth_helpers.make_dealership`**
  — unchanged; new
  `make_pilot_dealership`
  helper wraps it. Existing
  callers continue to work.

## 5. Load-bearing decisions

Eight decisions. **All eight
confirmed as-recommended at
SESSION_153 M19.0 open.** Streak
extends to **85 planning-time
as-recommended M5.1 → M19.0**
(ten consecutive milestones now).
Historical §5 counts have been
6-7 per milestone; M19 at eight
reflects the pilot-onboarding
scope's breadth (fourteen
planning topics compressed into
eight decisions).

### 5.a `[RESOLVED at SESSION_153 open]` — Milestone target selection

**Question.** Which candidate
from the M18 §8 unblocks + M17
§8 still-valid list defines M19
scope? Are tester sessions the
primary planning input?

**Decision.** **Option V — pilot-
customer onboarding.** Milestone
name: **"Founding Dealer Pilot
Onboarding."** User named at
SESSION_153 M19.0 open. Tester
sessions have not happened since
M18 close, so Option T (process
tester feedback) stays deferred.
Option V builds the controlled
conversion path from demo → pilot
so testers who commit have a
place to land.

**Rationale.** (1) M18 shipped
validation infrastructure; the
natural follow-on is the
conversion path so committed
testers can be onboarded. (2)
Founder-led pilots at M19
preserve Chris's operator
observation posture — he sees
every onboarding first-hand,
which surfaces the workflow
mismatches + support burden + data
cleanup needs that M20+ scoping
depends on. (3) Public self-
serve signup (Option U) is
premature until pilot workflow
is proven. (4) Real-data
onboarding without the M19
substrate would be an ad-hoc
one-off — un-reviewable, un-
repeatable, prone to breaking
tenancy or authorization
contracts. (5) The scope is
narrowly the pilot conversion +
safety substrate; M19 is
explicitly not a broad UX-polish
or new-capability milestone.

### 5.b `[RESOLVED at SESSION_153 open]` — Pilot eligibility + conversion criteria

**Question.** How does a demo
tester become a pilot candidate?

- **Option A** — Formal criteria
  doc + gating service verb
  `is_pilot_eligible(intake)`.
  Rigid.
- **Option B** — Informal
  `PilotProspect` entity Chris
  fills per candidate. No
  automated gating.
- **Option C** — Hybrid:
  `PilotProspect` entity with
  structured note fields
  (`dealer_type`,
  `bhph_enabled`,
  `estimated_inventory_size`,
  `contact_source`,
  `chris_notes`) + operator-
  owned `eligibility_state`
  state machine (`prospect` →
  `qualified` → `converted` OR
  → `declined`).

**Recommendation drafted.**
**Option C.**

**Rationale.** (1) Structured
enough to capture the pilot-
selection signal for later post-
pilot pattern analysis. (2)
Loose enough that Chris isn't
fighting a rigid gating verb
during the first few pilots
when the criteria are still
being discovered. (3)
State machine gives audit trail
(who was declined; who
converted); note fields give
context (why the operator made
each call). (4) If patterns
emerge later, a
`is_pilot_eligible(prospect)`
verb can layer on the entity
without a schema change. (5)
Matches the M12.4
`BhphPromiseToPay` state machine
posture (initial state +
operator-triggered terminal
transitions).

**PilotProspect field set:**
- `contact_name` CharField(64).
- `contact_email` EmailField.
- `contact_phone` CharField(64,
  blank).
- `dealer_business_name`
  CharField(255).
- `dealer_type` CharField(32,
  choices=`DEALER_TYPE_CHOICES`
  matching existing profile
  vocab).
- `bhph_enabled` BooleanField.
- `estimated_inventory_size`
  PositiveIntegerField(null).
- `contact_source` CharField(64,
  blank) — how did Chris meet
  them.
- `eligibility_state`
  CharField(32,
  choices=(prospect / qualified
  / converted / declined),
  default=prospect).
- `chris_notes` TextField(blank).
- `created_at` auto_now_add.
- `updated_at` auto_now.

**Tenancy posture.** No FK to
`Dealership` — `PilotProspect`
is scoped to Chris's operator
surface, not a specific
dealership tenant. Optional FK
to a pilot Dealership added when
`eligibility_state` advances to
`converted`.

### 5.c `[RESOLVED at SESSION_153 open]` — Tenancy type designation

**Question.** How does the
schema distinguish demo
dealerships, pilot dealerships,
and live production dealerships?

- **Option A** — Add
  `Dealership.is_pilot
  BooleanField(default=False)`
  mirroring M18's `is_demo`.
  Live = both flags False.
  Guards write `is_demo or
  is_pilot`.
- **Option B** — Replace both
  flags with `tenant_type
  CharField(choices=('demo',
  'pilot', 'live'))`. Data
  migration back-fills existing
  `is_demo=True` rows.
- **Option C** — Only `is_pilot`
  flag; incompatible with future
  expansion.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Preserves
the M18 `is_demo` invariant
(no data migration on existing
seeded rows). (2) One
additive column matching
M18.1's pattern. (3)
Introduces an
`is_synthetic_tenant(dealership)
-> bool` helper that the M18.1
outbound guard reuses verbatim.
(4) Trade-off: two boolean
fields for a three-state
concept is slightly redundant
vs a single choice field, but
the M18 pattern is proven,
mutable-vocab risk is real
(adding `staging` /
`training` / `archived` later
would still work with
booleans; would require
migrations with a choice
field), and the diff is
smaller. (5) The guard reads
naturally in code:
`if is_synthetic_tenant(dealership):
suppress_outbound()`.

### 5.d `[RESOLVED at SESSION_153 open]` — Pilot dealership creation service

**Question.** What is the
authoritative write path for
creating a pilot dealership?

- **Option A** — New
  `services/pilot_onboarding/`
  package with
  `create_pilot_dealership(*,
  slug, name, owner_user,
  profile_kwargs) ->
  Dealership` atomic verb.
- **Option B** — Reuse the
  demo-store registry with a
  pilot flag. Rejected:
  archetype builders don't
  apply.
- **Option C** — Manual admin
  steps. Not scriptable.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) New service
package sibling to
`services/demo_store/`. (2)
Atomic — Dealership create +
COA seed + owner membership +
profile populate happen in one
transaction. Partial pilot
creation is architecturally
impossible. (3) Explicit
ownership contract — the
`owner_user` argument names the
`dealer_owner` role holder at
creation time. (4) Both
packages consume shared M13.1
`seed_default_coa` + M1
`UserDealershipRole`
primitives without touching
them. (5) Mirrors M18.1's
`registry.py` posture.

**Auto-fires
`PilotOnboardingChecklist`** on
creation (per §5.f Option A) so
Chris always has a canonical
checklist row from step 1.

### 5.e `[RESOLVED at SESSION_153 open]` — Inventory import + dirty-data handling

**Question.** How does the pilot
dealer's initial inventory get
into the system?

- **Option A** — Extend the M6.3
  substrate with a new
  `import_pilot_inventory(*,
  dealership, csv_source)` verb
  returning
  `PilotInventoryImportResult`
  frozen dataclass (per-row
  accepted / rejected + errors).
  New
  `docs/PILOT_INVENTORY_TEMPLATE.md`
  documenting required columns +
  acceptable values + example
  row. Ships at M19.5.
- **Option B** — Manual entry
  only. Too slow.
- **Option C** — Build a new
  spreadsheet-template flow.
  Reinvents M6.3.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Extends the
proven M6.3 substrate. (2)
`PilotInventoryImportResult`
frozen dataclass surfaces
per-row outcomes so Chris can
see exactly which rows landed
and why others didn't. (3) **No
silent defaulting for dirty
data** — surfaces operator-
decision needs explicitly.
Chris hand-cleans rejected rows
and re-imports. (4) Template
doc gives dealers a clear
spreadsheet shape to export from
their existing tools. (5)
Alternative frozen dataclass
fields: `accepted_rows: tuple[Vehicle,
...]` + `rejected_rows:
tuple[tuple[dict, str], ...]`
(dict is the raw row; str is
the reason). Callers project
into serialized shape at the
endpoint layer.

### 5.f `[RESOLVED at SESSION_153 open]` — Capability enablement + onboarding checklist + readiness

**Question.** How are shipped
capabilities gated by pilot store
shape, and how is onboarding
progress tracked?

- **Option A** — Capability
  gating reads existing
  `DealerOnboardingProfile`
  fields (`dealer_type`,
  `bhph_enabled`,
  `subprime_lenders`,
  `floor_plan_lender`,
  `warranty_offering`,
  `credit_range_served`,
  `makes_carried`). New
  `PilotOnboardingChecklist`
  (one per pilot; CASCADE FK)
  + `PilotOnboardingStep` (many
  per checklist; fixed vocab
  step slugs). Per-step
  `completed_at` + optional
  `notes` + top-level `is_ready`
  boolean gates operator surface
  access.
- **Option B** — New
  `CapabilityFlag(dealership,
  capability_name)` entity.
  Over-generalizes.
- **Option C** — Markdown
  checklist Chris fills in per
  pilot. Doesn't scale.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Profile-
driven capability gating
consumes existing substrate.
(2) Checklist entity gives an
audit trail + queryable
progress. (3) Explicit
`readiness_confirmed` step
Chris signs off on before the
pilot is considered live. (4)
`is_ready=True` gates the
pilot dealer's operator
surface access — until Chris
confirms readiness, the pilot
owner can't log into their
own store. (5) Adds two
entities (`PilotOnboardingChecklist`
+ `PilotOnboardingStep`).

**Fixed-vocab step slugs
(growth-only per M9-M18
lesson):**
- `dealership_created`
- `profile_configured`
- `owner_user_added`
- `staff_users_added`
- `inventory_imported`
- `capabilities_enabled`
- `readiness_confirmed`

Exact-set assertion at test
time.

### 5.g `[RESOLVED at SESSION_153 open]` — Outbound integration posture during pilot

**Question.** During pilot, what
fires outbound to real
destinations?

- **Option A** — Extend the
  M18.1 outbound guard to
  include pilots via a new
  `is_synthetic_tenant(dealership)
  -> bool` helper (`is_demo or
  is_pilot`). **All outbound
  suppressed by default for
  pilots.** Per-verb opt-in
  gated on future code review.
- **Option B** — Pilots behave
  as production for outbound.
  Rejected: risks unreviewed
  adapters sending to real
  customers.
- **Option C** — Hybrid opt-in
  per verb per pilot. More
  flexible but more surface to
  reason about.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) All
outbound suppressed during M19
pilots by default. The dealer
runs their real customer
communications through their
existing personal channels
(email, phone). (2) The
platform's outbound path
activates via later opt-in
milestones once each specific
adapter gets code-reviewed for
real-world use. (3) Trade-off:
the pilot dealer's day-to-day
is not fully "live" — they
don't get platform-driven
customer messaging. But at
M19 the goal is proving the
operator workflow, not
automating customer touch.
(4) Documented explicitly in
the M19.5 playbook —
`PILOT_ONBOARDING_PLAYBOOK.md`
§Outbound safety posture
during pilot. (5) The M18.1
outbound-egress scanner test
continues to enforce guard-
by-construction; the new
helper is a drop-in
extension.

**Implementation:** rename
`is_demo_dealership(dealership)`
in `outbound_guard.py` →
`is_synthetic_tenant(dealership)`;
add a `is_pilot_dealership(dealership)`
companion for callers that
care about the distinction;
preserve `is_demo_dealership()`
as a deprecated alias for the
transition period (delete at
M20+ if unused).

### 5.h `[RESOLVED at SESSION_153 open]` — Pilot termination + software-vs-consulting boundary

**Question.** How does a pilot
end, and what defines the
boundary between software
onboarding (M19 scope) and
custom consulting (out of
scope)?

- **Option A** —
  `terminate_pilot(*,
  dealership, reason, actor,
  mode) -> Dealership` atomic
  verb. Two additive
  `Dealership` columns:
  `terminated_at` +
  `termination_reason`. Sets
  `is_pilot=False` + populates
  the timestamps.
  `mode='archive'` preserves
  child rows for post-mortem;
  `mode='cleanup'` cascades
  reverse-order per M18.2
  pattern. Boundary policy
  documented in
  `docs/PILOT_ONBOARDING_PLAYBOOK.md`.
- **Option B** — Hard-delete
  only. No audit trail.
- **Option C** — Soft-delete
  only. Undecidable later.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Structured
termination with reason +
timestamp gives audit trail
for post-mortem review. (2)
`mode='archive'` preserves the
customer data for review;
`mode='cleanup'` cascades
reverse-order per M18.2's
proven pattern (child-before-
parent for PROTECT FKs; demo-
owned Users cleared for
username-collision safety).
Chris chooses at termination
time based on whether post-
mortem is planned. (3)
Boundary policy documented
explicitly: **software
onboarding covers everything
the shipped surface supports
via configuration or standard
imports; anything requiring
code changes for a specific
dealer is custom consulting,
out of M19 scope.** (4)
`terminate_pilot` raises
`NonPilotTerminationError`
(RuntimeError) if called
against a non-pilot
Dealership — belt-and-
suspenders + `assert
dealership.is_pilot` at
write-verb top. (5) Preserves
the M18.2 broken-invariant-
guard pattern
(`NonDemoResetError`).

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §6 (seven lessons carry
   into M19) + §8 (M18
   unblocks) + §9 (standing
   question)
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   §8 (M17 unblocked work —
   still mostly valid after
   M18 for candidates other
   than the ones now shipped)
7. `docs/CAPABILITY_MATRIX.md`
   §7s (M18 shipped surface —
   the demo substrate M19
   converts from)
8. `docs/research/INDEPENDENT_DEALER_PIVOT.md`
   (persona shape informing
   pilot criteria)

## 7. Sequencing

**Seven increments total.**
Confirmed as-recommended per
§0.a. Combine increments if
implementation evidence shows
a smaller complete shape;
do not split merely to match
this draft.

### Increment 0 (M19.0) — Planning refinement + decision review

**Scope.** SESSION_153 (this
session). §5.a Option V
confirmed at open; §5.b-§5.h
drafted with recommendations
for user confirmation before
M19.1 code. Full memo
expansion (this document).

**Deliverable.**
- This planning memo, expanded
  from the M18.6 skeleton.
- §0.a change log with all
  eight §5 decisions resolved.
- Session handoff at
  `docs/handoffs/SESSION_153_m19_inc0_planning.md`.
- `00-START-NEXT-SESSION.md`
  overwritten with M19.1
  priority.

**Backend baseline unchanged:**
4,538 pass, 1 skipped, 0 fail.
Frontend Vitest unchanged: 140
pass.

### Increment 1 (M19.1) — Backend substrate: schema + service package + guards

**Scope.** Next session. Single
backend increment. All M19
substrate lands here.

**Deliverable.**
- Migration
  `0048_m191_pilot_substrate.py`
  bundling:
  - `AddField Dealership.is_pilot`
    BooleanField(default=False).
  - `AddField
    Dealership.terminated_at`
    DateTimeField(null=True,
    blank=True).
  - `AddField
    Dealership.termination_reason`
    TextField(blank=True,
    default="").
  - `CreateModel PilotProspect`
    per §5.b field set (no
    dealership FK; scoped to
    Chris's operator surface).
  - `CreateModel
    PilotOnboardingChecklist`
    (dealership FK CASCADE,
    is_ready BooleanField,
    created_at, updated_at).
  - `CreateModel
    PilotOnboardingStep`
    (checklist FK CASCADE,
    dealership FK CASCADE,
    step_slug CharField
    choices, completed_at
    DateTimeField null, notes
    TextField blank, created_at).
    `Meta.unique_together =
    (('checklist',
    'step_slug'),)`.
- Vocab constants in
  `models.py`:
  `PILOT_PROSPECT_STATE_*` +
  `PILOT_PROSPECT_STATE_CHOICES`;
  `PILOT_ONBOARDING_STEP_*`
  slugs +
  `PILOT_ONBOARDING_STEP_CHOICES`.
- Register `PilotProspect` +
  `PilotOnboardingChecklist` +
  `PilotOnboardingStep` in
  `_TENANT_CARRIER_MODEL_NAMES`
  in `services/tenancy.py`.
  Count 50 → **53**.
  (`PilotProspect` is scoped
  to the operator surface but
  still gets the pre_save
  autofill safety net; it
  autofills the default
  dealership if a caller
  bypasses the service and
  forgets `dealership=`. The
  autofill signal fires
  regardless of whether the
  model has an explicit
  dealership FK — the
  registration is defensive.)
  Wait — actually `PilotProspect`
  has no `dealership` FK by
  §5.b design, so it can't be
  a tenancy carrier in the
  autofill sense. Correction:
  register only
  `PilotOnboardingChecklist` +
  `PilotOnboardingStep`
  (dealership FK CASCADE);
  `PilotProspect` gets a
  companion registration
  posture TBD at M19.1 open
  as a §0.a micro-decision
  (probable outcome: exempt
  from the autofill signal;
  the model manages tenancy
  scope via the operator-
  visible admin filter). Count
  50 → **52** at M19.1;
  PilotProspect count may
  add +1 as an §0.a decision.
- New package
  `services/pilot_onboarding/`:
  - `__init__.py` with
    `__all__` exports.
  - `errors.py`:
    `PilotAlreadyExistsError`,
    `NonPilotTerminationError`,
    `PilotReadinessNotConfirmedError`.
  - `registry.py`:
    - `create_pilot_dealership(*,
      slug, name, owner_user,
      profile_kwargs) ->
      Dealership` — atomic per
      §5.d Option A. Catches
      `IntegrityError` on slug
      + re-raises as
      `PilotAlreadyExistsError`.
      Auto-fires
      `PilotOnboardingChecklist`
      per §5.f.
    - `list_pilot_dealerships()
      -> list[Dealership]` —
      pure read (is_pilot=True,
      not terminated).
    - `terminate_pilot(*,
      dealership, reason,
      actor, mode) ->
      Dealership` — atomic per
      §5.h Option A. Raises
      `NonPilotTerminationError`
      if `is_pilot=False`;
      belt-and-suspenders
      `assert dealership.is_pilot`
      at top.
  - `prospects.py`:
    `create_prospect(...)`,
    `advance_prospect_state(*,
    prospect, new_state)`,
    `list_prospects() ->
    list[PilotProspect]`.
  - `checklist.py`:
    `create_checklist(*,
    dealership) ->
    PilotOnboardingChecklist`
    (called by
    `create_pilot_dealership`),
    `advance_step(*, checklist,
    step_slug, notes='') ->
    PilotOnboardingStep` (raises
    `PilotReadinessNotConfirmedError`
    if trying to advance
    `readiness_confirmed` before
    all prior steps),
    `is_pilot_ready(dealership)
    -> bool`.
  - `inventory_import.py`:
    - `PilotInventoryImportResult`
      frozen dataclass
      (accepted_rows,
      rejected_rows).
    - `import_pilot_inventory(*,
      dealership, csv_source) ->
      PilotInventoryImportResult`
      — extends M6.3 substrate.
    - (M19.1 stub only; full
      implementation ships at
      M19.2.)
- Extend M18.1
  `services/demo_store/outbound_guard.py`:
  - Add `is_pilot_dealership(dealership)
    -> bool`.
  - Add `is_synthetic_tenant(dealership)
    -> bool` (`is_demo or
    is_pilot`).
  - Preserve
    `is_demo_dealership()` as
    deprecated alias.
  - Update `suppress_if_demo`
    → `suppress_if_synthetic`
    (or add companion) —
    settles at M19.1 open as
    a §0.a micro-decision.
- `_auth_helpers.make_pilot_dealership(*,
  slug, name, owner_user_kwargs,
  profile_kwargs)` companion
  helper.
- **Focused tests (~40-50
  target)** in new
  `tests/test_m191_pilot_substrate.py`:
  - `Dealership.is_pilot` +
    `terminated_at` +
    `termination_reason`
    defaults.
  - `PILOT_PROSPECT_STATE_CHOICES`
    exact-set equality.
  - `PILOT_ONBOARDING_STEP_CHOICES`
    exact-set equality.
  - `PilotProspect` model
    create + state advance.
  - `PilotOnboardingChecklist`
    + `PilotOnboardingStep`
    unique_together.
  - `create_pilot_dealership`
    happy path (Dealership +
    COA + owner membership +
    profile + auto-fired
    checklist all commit).
  - Slug collision raises
    `PilotAlreadyExistsError`.
  - `create_pilot_dealership`
    with existing demo slug
    also raises.
  - `list_pilot_dealerships`
    returns only
    `is_pilot=True,
    terminated_at=NULL`.
  - `terminate_pilot`
    happy path both modes
    (`archive` + `cleanup`).
  - `terminate_pilot` raises
    `NonPilotTerminationError`
    on non-pilot Dealership.
  - `assert dealership.is_pilot`
    guard fires on bypass mock.
  - `advance_step` happy path.
  - `advance_step` raises
    `PilotReadinessNotConfirmedError`
    when advancing
    `readiness_confirmed`
    before prior steps
    complete.
  - `is_pilot_ready` returns
    True only when checklist
    complete.
  - `is_synthetic_tenant`
    returns True for demo,
    pilot, and both; False
    for live.
  - `is_pilot_dealership`
    isolated helper.
  - Outbound-egress scanner
    test continues to hold
    with the extended helper.
  - Tenancy carrier count
    52 (or 53 depending on
    the PilotProspect §0.a
    micro-decision at M19.1
    open) — `>=` assertion.
  - Permission-class set
    equality unchanged
    (zero-drift streak
    fifteen consecutive
    milestones after M19.1
    if no new endpoint at
    M19.1).
  - Endpoint count 108
    (unchanged at M19.1;
    endpoints ship at
    M19.3).

**Backend baseline target:**
4,538 → ~4,578-4,588 pass
(+40-50 tests, 0 regressions).
Frontend Vitest: 140
(unchanged).

### Increment 2 (M19.2) — Inventory import + validation

**Scope.** Session after M19.1.
Backend increment focused on
the CSV inventory import verb
+ validation contract.

**Deliverable.**
- Fill in
  `services/pilot_onboarding/inventory_import.py::import_pilot_inventory`
  stub from M19.1.
- Extend the M6.3
  `services/inventory_import`
  substrate as needed
  (additive; no fork).
- Validation contract per row:
  - Required columns present.
  - `stock_number` unique
    within tenant.
  - `year` int + in reasonable
    range.
  - `make` + `model` + `price`
    present.
  - Numeric fields parseable.
  - Boolean fields parseable.
- Rejected rows returned with
  per-row error message.
- Focused tests (~15-25
  target) in
  `tests/test_m192_pilot_inventory_import.py`.

**Backend baseline target:**
~4,578-4,588 → ~4,593-4,613
pass. Frontend Vitest:
unchanged.

### Increment 3 (M19.3) — DRF endpoints

**Scope.** Session after M19.2.
Four new admin endpoints.

**Deliverable.**
- New `views_pilot_onboarding.py`
  module with four handlers:
  - `POST
    /admin/pilot-onboarding/dealerships/`
    — create pilot dealership.
    Body validated by DRF
    serializer. Returns 201.
    Reuses
    `IsSalesManagerOrOwnerAtActiveDealership`.
  - `GET
    /admin/pilot-onboarding/dealerships/list/`
    — list pilots. Paginated
    per M14.1 pattern.
  - `POST
    /admin/pilot-onboarding/dealerships/<int:pk>/checklist/advance/`
    — advance checklist step.
    Body: `{ "step_slug":
    ..., "notes": "..." }`.
    Returns 201 with checklist
    projection.
  - `POST
    /admin/pilot-onboarding/dealerships/<int:pk>/terminate/`
    — terminate pilot. Body:
    `{ "reason": ...,
    "mode": "archive|cleanup"
    }`. Returns 201.
- URL registrations. DRF admin
  surface 108 → **112** (+4).
- Zero-drift permission-class
  streak extends to **fifteen
  consecutive milestones**.
- Focused tests (~20-30
  target) in
  `tests/test_m193_pilot_endpoints.py`.

**Backend baseline target:**
~4,593-4,613 → ~4,613-4,643
pass.

### Increment 4 (M19.4) — Frontend: pilot admin surface

**Scope.** Session after M19.3.
Extends an existing admin
route in place per M17 §6
lesson 6. Frontend operator
routes stay at **20**.

**Deliverable.**
- Extend
  `frontend/src/lib/pilotOnboardingApi.ts`
  (new file) with fetchers +
  mutators for the M19.3
  endpoints.
- New TypeScript types
  matching backend
  projections.
- Extend an existing admin
  page (probably the manager
  dashboard) with a pilot
  admin section: list, click-
  through to detail, create
  form, checklist advance
  button, terminate action
  with mode + reason inputs.
- New Vitest coverage for
  the pilot admin surface.
- Frontend Vitest target:
  140 → ~150-165 pass.

### Increment 5 (M19.5) — Playbook + template + end-to-end dry-run

**Scope.** Session after M19.4.
Documentation + end-to-end
validation.

**Deliverable.**
- `docs/PILOT_ONBOARDING_PLAYBOOK.md`
  (new file):
  - Introduction — what a
    pilot is at M19.
  - Pilot eligibility criteria
    (Chris's operator
    guidance).
  - Onboarding sequence
    walkthrough per checklist
    step.
  - Outbound safety posture
    during pilot (§5.g).
  - Data handling for dirty
    imports (§5.e).
  - Software onboarding vs
    custom consulting boundary
    (§5.h).
  - Rollback / termination
    procedure (§5.h).
  - First-pilot-specific
    notes.
- `docs/PILOT_INVENTORY_TEMPLATE.md`
  (new file):
  - Required columns.
  - Acceptable values.
  - Example row.
  - Common dirty-data patterns
    + how they surface as
    validation errors.
- **First end-to-end dry-run**:
  Chris runs the whole
  pipeline against a synthetic
  pilot prospect using the
  M19.4 admin surface. Notes
  any gaps as `TesterFeedback`
  entries (using the M18.5
  endpoint against a demo
  dealership).
- Fix UI defects only per
  §5.f evidence gate (M18.5
  precedent).
- Zero backend changes at
  M19.5 unless dry-run
  surfaces a workflow-
  blocking defect.

### Increment 6 (M19.6) — Close-out

**Scope.** Docs. Retrospective
+ capability matrix §7t +
roadmap flip + M20 planning
skeleton per standing user
directive (M10.8 / M11.7 /
M12.8 / M13.4 / M14.5 / M15.2
/ M16.2 / M17.3 / M18.6
precedent).

**Deliverable.**
- `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
  written at M19.6 close.
- `docs/CAPABILITY_MATRIX.md`
  §7t section describing the
  M19 shipped surface.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 19 SHIPPED entry.
- Frontmatter flip on this
  doc: `status: active` →
  `status: shipped`.
- `docs/roadmap/MILESTONE_20_PLANNING.md`
  skeleton per standing
  directive.
- `00-START-NEXT-SESSION.md`
  overwritten with M20.0
  priority.
- Coordinated commit landing
  all M19.6 docs together.

**Backend baseline at M19
close:** M19.5 baseline
sustained; no code changes at
M19.6.

---

*Full memo. All eight §5
decisions confirmed as-
recommended at SESSION_153
M19.0 open.*
