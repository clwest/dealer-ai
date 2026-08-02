---
title: "Milestone 18 — Demo Store Simulation + Pilot Validation Readiness"
status: active
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_145 (skeleton), SESSION_146 (expansion)
milestone: 18
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_17_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_17_PLANNING.md
  - docs/roadmap/MILESTONE_16_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/INDEPENDENT_DEALER_PIVOT.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
  - docs/research/RECON_MAPPING.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
---

# Milestone 18 — Demo Store Simulation + Pilot Validation Readiness

> **Active planning memo.** Expanded at
> SESSION_146 M18.0 open from the skeleton
> drafted at M17.3 close. §5.a Option O
> confirmed at open — the first **non-
> accounting** milestone target since M12.
> The platform now has a broad verified
> capability surface through M17; the
> highest-value next slot is not another
> isolated accounting extension but proving
> that experienced independent-dealer
> operators can enter a believable store,
> recognize their normal operating world,
> work through a realistic day using
> shipped capabilities, and provide
> actionable product + commercial
> feedback.
>
> **This milestone is a validation-
> infrastructure milestone, not a demo-data
> milestone.** The distinction is load-
> bearing. Generic Faker-style seed data
> creates volume without operational
> meaning. What tester validation requires
> is **coherent cross-domain business
> stories** — a vehicle whose recon
> overrun reconciles across acquisition
> record, investment ledger, condition
> findings, work orders, lifecycle stage,
> projected gross, accounting activity,
> and any recommendation surface that
> already consumes those records. Every
> primary scenario defines what happened
> before login, what the operator needs
> to accomplish today, what information
> is intentionally incomplete or
> problematic, which shipped capabilities
> should help, what successful completion
> looks like, and what must remain
> discoverable without a guided click
> path.
>
> **Seven load-bearing decisions** —
> §5.a target selection + §5.b-§5.g on
> architecture, ownership, scenario shape,
> feedback capture, UI-correction
> boundary, and data safety. **All seven
> confirmed as-recommended at SESSION_146
> M18.0 open** — streak extends to **77
> planning-time as-recommended M5.1 →
> M18.0 across nine consecutive
> milestones** (M10 + M11 + M12 + M13 +
> M14 + M15 + M16 + M17 + M18).

## 0. Engineering practices to preserve from M2-M17

Same posture as M17.0. Non-negotiable:

- **Backend-first architecture.** Demo
  store construction is a backend
  operation; no business logic in the
  frontend. Frontend consumes the demo
  stores via the same routes real
  operators would use.
- **Service ownership.** One
  authoritative write path per
  operation. New
  `services/demo_store/` package is
  the ONLY entry point for demo-store
  creation, reset, and export.
- **Tenancy discipline.** Demo
  dealerships live in the normal
  `Dealership` model per §5.b Option A
  — they are Dealerships with
  `is_demo=True` and a
  `demo_archetype` string. Every
  existing tenancy carrier stays
  tenancy-scoped without exception.
  No parallel model, no parallel
  auth path.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M17
  convention. **M18.1 introduces
  `NonDemoResetError(RuntimeError)` —
  broken-invariant guard fired if any
  demo-store write path is called
  against a `Dealership` where
  `is_demo=False`.** Follows the M15.1
  / M16.1 / M17.1 broken-invariant-
  guard-as-contract pattern.
- **Load-bearing decisions get user
  review BEFORE code.** All seven §5
  decisions confirmed at SESSION_146
  open. Any additional decisions
  surface as §0.a implementation-time
  amendments.
- **Additive extension over fork.**
  `Dealership` gains `is_demo` +
  `demo_archetype` columns via one
  additive migration — the existing
  model is not forked. Existing seeds
  (`seed_copper_canyon_demo`,
  `seed_copper_canyon_scenarios`,
  `seed_demo_scenarios`,
  `seed_demo_vehicles`,
  `seed_phase3_demo`,
  `seed_phase4_demo`) remain in the
  tree as historical references but
  are not extended — the new
  `demo_store` command supersedes
  them.
- **Every M18 test asserting tenant-
  carrier / permission-class /
  endpoint counts uses `>=N`** per
  M9-M17 growth-only-list lesson.
  **Vocab-set + permission-class-set
  assertions use exact equality** per
  M11-M17 fixed-vocab lesson. The
  `DEMO_ARCHETYPE_CHOICES` vocab
  (`retail_subprime`, `floor_planned`,
  `bhph`) is a fixed vocab; exact-set
  assertion at test time.
- **Read-only surfacer vs state-
  transitioning detector vs sync
  sibling-service** — M18 introduces
  **operator-triggered management
  commands** as a new shape. These
  are sync operations (operator runs
  `demo_store create`), not
  detectors. Each scenario builder
  wraps in `@transaction.atomic` so
  a partial demo store is
  architecturally impossible.
- **Atomic scenario builders.**
  Every archetype's `build(dealership)`
  verb wraps in
  `@transaction.atomic` per M12 §6
  lesson 11. Partial demo stores are
  architecturally impossible.
- **Denormalize at write; recompute
  in detectors; refresh AFTER
  sibling writes.** Demo scenario
  seeding respects every existing
  denormalization contract — a
  seeded Sale populates the same
  denorm fields the M15 sale-booking
  path would.
- **Split pure verbs from write
  verbs.** Scenario builders are
  write verbs; scenario summarizers
  (which return `ScenarioSummary`
  frozen dataclasses for tester-
  brief consumption) are pure.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default for the new
  `TesterFeedback` POST endpoint
  (§5.e). **Nine consecutive
  milestones now** per M17 §6
  lesson 5. M18 must not add a new
  permission class.
- **Broken-invariant guards as
  cross-milestone contracts.** Per
  M17 §6 lesson 4. M18.1 introduces
  `NonDemoResetError` as the
  contract that the demo-store
  reset path only ever runs against
  demo dealerships; violation fires
  loud (RuntimeError, not
  ValueError — signals a
  programming bug, not caller
  input).
- **Naming discipline** per M17 §6
  lesson 3. The new `TesterFeedback`
  model earns the durable name;
  scenario summaries are frozen
  dataclasses named
  `ScenarioSummary`.
- **`IntegrityError` → domain
  exception at service boundary**
  per M17 §6 lesson 4 pattern
  available for scenario builders
  that use `unique_together`
  constraints on seeded rows.
- **Zero-portfolio semantics.** A
  freshly-created demo dealership
  (before any scenario builder has
  run) is a valid state — the
  `list_demo_stores` verb returns
  an empty scenario list without
  erroring.
- **Money on the wire is Decimal-
  as-string** per M9-M17
  convention. Seeded financial
  values (Sale.sold_price,
  VehicleCost.amount,
  BhphNote.principal_financed,
  BhphPayment.amount, etc.) use
  precise Decimal literals in the
  archetype modules.
- **In-place page extension over
  new route** per M17 §6 lesson 6.
  M18 introduces **zero new
  frontend operator routes.**
  Testers use the same M14 /
  M6.5 / M12 routes real operators
  would. If a scenario brief
  requires operator UI access to
  the demo-store list or the
  TesterFeedback capture form,
  that layers as an in-place
  extension to an existing admin
  page (evidence-triggered at
  M18.5 per §5.f).
- **Native browser primitives +
  shadcn `Input` wrapper as the
  default** per M17 §6 lesson 5.
  Any M18 frontend surface
  (TesterFeedback capture form if
  it surfaces at M18.5) uses
  native primitives before
  escalating to purpose-built
  shadcn.
- **Test-fixture invariants
  match migration invariants.**
  Per M15 §6 lesson 3 + M16.1 +
  M17.1 verified —
  `make_dealership` seeds default
  COA. **M18 tests use a new
  `make_demo_dealership(archetype)`
  helper** in
  `tests/_auth_helpers.py` that
  wraps `make_dealership` +
  sets `is_demo=True` +
  `demo_archetype=<value>`.

### 0.a Change log — resolved decisions

**SESSION_146 M18.0 open (2026-08-02):**

- **§5.a → Option O confirmed at
  open.** User named at
  SESSION_146 open — non-accounting
  target. Milestone name: **"Demo
  Store Simulation + Pilot
  Validation Readiness."** The
  first non-accounting milestone
  target since M12; validation
  infrastructure to enable
  founder-led pilot testing with
  experienced independent-dealer
  operators.
- **§5.b → Option A confirmed as-
  recommended.** Add
  `Dealership.is_demo
  BooleanField(default=False)` +
  `Dealership.demo_archetype
  CharField(choices=DEMO_ARCHETYPE_CHOICES,
  blank=True)` with fixed vocab
  (`retail_subprime`,
  `floor_planned`, `bhph`, blank).
  One additive migration (`0047`
  — two `AddField`). All existing
  tenancy paths work unchanged.
- **§5.c → Option A confirmed as-
  recommended.** New
  `services/demo_store/` package
  + one management command
  `python manage.py demo_store
  {create|reset|list|export_feedback}
  --archetype <name> --slug
  <name>`. Belt-and-suspenders
  guard: raise
  `NonDemoResetError(RuntimeError)`
  if any write path receives a
  `Dealership` where
  `is_demo=False`; also `assert
  dealership.is_demo` at top of
  every write verb.
- **§5.d → Option A confirmed as-
  recommended.** Python builder
  classes in
  `services/demo_store/archetypes/{retail_subprime,floor_planned,bhph}.py`.
  Each archetype exposes a
  `build(dealership) ->
  ScenarioSummary` atomic verb.
  Scenarios are code, versioned
  like code.
- **§5.e → Option A confirmed as-
  recommended.** New
  `TesterFeedback` model
  (`dealership` FK CASCADE,
  `tester_name`, `scenario_slug`,
  `category`, `note`,
  `referenced_route`,
  `created_at`) + one POST
  endpoint + management-command
  exporter (`python manage.py
  demo_store export_feedback
  --dealership <slug> --since
  <date>` → CSV). Tenancy carrier
  49 → **50**.
- **§5.f → Option A confirmed as-
  recommended.** Explicit UI-
  correction boundary: only
  workflow-blocking or materially
  misleading defects belong in
  M18. Everything else recorded
  via §5.e for a later dedicated
  UX-polish milestone. Every M18.x
  UI correction records the
  specific blocking scenario in
  its commit message + M18
  retrospective §4 deviations.
- **§5.g → Option A confirmed as-
  recommended.** Unmistakably
  synthetic data everywhere:
  `DEMO`-prefixed VINs (never
  valid decodable); fixed
  pseudonym roster in
  `services/demo_store/synthetic_names.py`
  (never Faker); `555-01xx` NANP
  reserved-for-fiction phones;
  `@demo.dealer-ai.example`
  emails (IANA-reserved TLD); SSN
  / payment credentials never
  populated. **Outbound-send
  guard**: enumerate existing
  send-boundary verbs at M18.1
  planning + wrap each with
  early `if dealership.is_demo:
  log_and_noop()` check.
- **§7 sequencing → seven-
  increment shape confirmed as-
  recommended.** M18.0 planning
  + M18.1 substrate (schema +
  service package + guards +
  TesterFeedback + send-boundary
  enumeration) + M18.2 retail /
  subprime pack + M18.3 floor-
  planned pack + M18.4 BHPH pack
  + M18.5 role briefs +
  feedback endpoint + exporter +
  M18.6 close-out. Combine
  increments if implementation
  evidence shows a smaller
  complete shape; do not split
  merely to match this draft.
- **Streak extends to 77
  planning-time as-recommended
  M5.1 → M18.0.** Nine
  consecutive milestones now
  (M10 + M11 + M12 + M13 + M14
  + M15 + M16 + M17 + M18).
  All seven §5 decisions
  confirmed as-recommended.
  Historical §5 counts have been
  6 per milestone; M18 at seven
  reflects the mixed
  architecture / ownership /
  representation / safety scope.

## 1. Business questions this milestone answers

Seven operator-workflow / validation
questions, each tied to a demonstrated-
capability boundary the platform
crosses at M18. Every question was
unanswerable before M18 — the
platform has capability surface but
no validation substrate for pilot-
testing that surface with real
prospective customers.

### Q1. Can an experienced independent-dealer operator recognize a believable store?

**Before M18:** No. The default
`Dealership` seeded by migrations is
Copper Canyon Auto — a single, well-
formed indie persona that
demonstrates the platform's shape.
But there is no set of *variations*
that reflect the range of independent
dealerships an experienced operator
recognizes: no small retail /
subprime store, no growing floor-
planned store with outside recon, no
BHPH portfolio operation. A tester
sees Copper Canyon and can't verify
"my store would look like this
because…"

**After M18:** Yes. Three archetypes
seed distinct, coherent demo stores:
retail/subprime, floor-planned/recon-
heavy, and BHPH. Each demo store's
inventory, staffing, vehicles-in-
recon, sales pipeline, accounting
activity, and (where applicable)
BHPH portfolio align with the
archetype in the way an experienced
operator would recognize the
"shape" of that kind of dealership.

### Q2. Can a tester execute a "day in the dealership" without hand-holding?

**Before M18:** No. Even with
Copper Canyon seeded, there is no
structured scenario brief that says
"you're the sales manager, three
leads landed overnight, the F-150
you were going to write up is
sitting in recon with a $600
overrun; here's what you need to
do today." Testers can poke around
routes but cannot verify a
workflow.

**After M18:** Yes. Each archetype
ships **five role-specific daily
briefs** at M18.5 (owner, sales
manager, recon lead, office /
accounting, and BHPH collector
where applicable). Each brief
defines what happened before login,
what the operator needs to
accomplish today, what information
is intentionally incomplete or
problematic, which shipped
capabilities should help, what
successful completion looks like,
and what must remain discoverable
without a guided click path.

### Q3. Can Chris (or a delegated tester wrangler) capture structured tester feedback without invasive tools?

**Before M18:** No. Chris can take
notes on paper or in a doc, but
there's no way for testers to
submit feedback tied to a specific
scenario + dealership + role
without external tooling. Notes get
lost. Categories get inconsistent.
Willingness-to-pay signals get
mixed with UX complaints.

**After M18:** Yes. `TesterFeedback`
model + POST endpoint + CSV
exporter. Each observation is
tagged with tester name, scenario
slug, category (`confusion` / `bug`
/ `feature_request` /
`value_statement` /
`willingness_to_pay`), free-text
note, and (optionally) the route
where the observation was made.
Export via `python manage.py
demo_store export_feedback --
dealership <slug> --since <date>`
→ CSV for review + follow-up.

### Q4. Can each tester start from a known state?

**Before M18:** No. Existing seeds
are idempotent-by-stock-number but
don't include a full-store reset.
A previous tester's edits to a
Sale, BhphPayment, or ChatSession
persist into the next tester's
session. Comparing "what did each
tester see" is impossible.

**After M18:** Yes. `python
manage.py demo_store reset --slug
<name>` restores the archetype's
canonical starting state
atomically. Reset **hard-refuses**
if `Dealership.is_demo=False` via
the `NonDemoResetError` guard.
Belt-and-suspenders: service-layer
`assert dealership.is_demo` at
top of every write verb.

### Q5. Is it safe to hand demo stores to real operators without risking real-world side effects?

**Before M18:** No formalized
guarantee. Some outbound-send
verbs (email, SMS, external API
adapters) exist but there is no
demo-store-wide guard preventing
them from firing against real
destinations if a tester
inadvertently triggers a send-
shaped workflow.

**After M18:** Yes. §5.g Option
A locks: DEMO-prefixed VINs;
fixed pseudonym roster; `555-
01xx` NANP fiction phones;
`@demo.dealer-ai.example` emails
(IANA-reserved `.example` TLD
never routes); SSNs + payment
credentials never populated; and
an enumerated **outbound-send
guard** wraps every existing
send-boundary verb with early
`if dealership.is_demo:
log_and_noop()`. Three
independent safety layers.

### Q6. Do the seeded stories preserve operational coherence across shipped capabilities?

**Before M18:** No. Existing seeds
populate specific tables (Vehicle,
ChatSession) without ensuring the
cross-domain consistency operators
expect. A demo Vehicle exists but
has no matching VehicleCost history,
no ReconDecision, no WorkOrder,
no VehicleStageEvent — so the M2
Vehicle Investment Ledger reads
$0 and the M5 lifecycle view reads
"unknown stage."

**After M18:** Yes. Each archetype's
scenario builders construct **cross-
domain stories.** A recon-overrun
vehicle in the floor-planned
archetype has: an
`AcquisitionRecord` (auction / whole-
sale purchase); a `VehicleCost`
history (parts + labor + recon
sub-vendor invoices); `ConditionReport`
+ `ConditionFinding` rows tied to
the initial pre-recon inspection;
`WorkOrder` + `WorkOrderPart` +
`WorkOrderFinding` rows tying
findings to remediation; a
`ReconDecision` linking the
overrun to a decision made against
projected gross; `VehicleStageEvent`
progression through acquisition →
recon → retail-ready; and (if
applicable) a `Sale` +
`SaleBookingJournalEntry` posted
via M15 sync sibling. The
operational story reads
consistently across every M2-M17
surface that touches the vehicle.

### Q7. Can M18 be shipped without opening any new operator-facing route?

**Before M18:** N/A.

**After M18:** Yes. Testers use
the same M1-M17 routes real
operators would. Zero new
operator routes at M18. The
`TesterFeedback` POST endpoint is
an admin-surface endpoint (not
an operator route in the 20-
count) reachable via a role-
gated form; the demo-store
management commands run
server-side. If a scenario brief
requires operator UI access to
list demo stores or capture
feedback, that layers as an
in-place extension to an
existing admin page (evidence-
triggered at M18.5 per §5.f
boundary).

## 2. What existing primitives extend

M18 is deliberately "additive over
existing surface" per §0. The
platform's shipped capability
surface is the leverage; M18 wraps
it in validation infrastructure.

### Persistence + tenancy

- **`Dealership` model.** Gains
  two nullable-safe additive
  columns per §5.b Option A:
  `is_demo` BooleanField default
  False + `demo_archetype`
  CharField(choices=CHOICES,
  blank=True). Existing rows
  default `is_demo=False`; no
  data migration needed.
- **`_TENANT_CARRIER_MODEL_NAMES`
  in `services/tenancy.py`.**
  Extended by one for
  `TesterFeedback`. Count 49 →
  **50**.
- **`_auth_helpers.make_dealership`.**
  Gains a companion
  `make_demo_dealership(archetype,
  slug)` helper that wraps
  `make_dealership` + sets
  `is_demo=True` +
  `demo_archetype=<value>` for
  M18.1+ test fixtures.

### Seed / management-command shape

- **Existing `management/commands/seed_*.py`
  commands.** Historical references
  documenting seed-shape patterns.
  **Not extended at M18** — the
  `demo_store` command supersedes
  them. The old commands stay
  in-tree for archaeological
  purposes.
- **`services/inventory_import.py`.**
  The inventory-upsert pattern
  used by `import_inventory` and
  `seed_copper_canyon_demo` — a
  clean idempotency template for
  the new archetype builders.

### Shipped capability surface (consumed by scenarios)

Every archetype constructs
scenarios that exercise the
shipped surface. Enumeration
below for reference; the archetype
modules at M18.2-M18.4 pull rows
into coherent stories.

- **M1** tenancy + roles +
  `Salesperson` + `Dealership`
  identity.
- **M2** Vehicle Investment
  Ledger (`VehicleCost`,
  `VehicleAcquisition`).
- **M3** Structured condition
  report (`ConditionReport`,
  `ConditionFinding`).
- **M4** Recon automation
  (`ReconDecision`, `WorkOrder`,
  `WorkOrderPart`, `Vendor`).
- **M5** Vehicle lifecycle
  stages (`VehicleStage`,
  `VehicleStageEvent`).
- **M6** Photography + listing
  generation (`VehiclePhoto`,
  `VehicleListing`).
- **M7** Async infrastructure
  (`JobRunLog`,
  `StageAgingSnapshot`).
- **M8** Operational
  intelligence surfaces.
- **M9** Sale + delivery closure
  (`Sale`, `Delivery`).
- **M10** F&I deal desk
  (`CreditApplication`,
  `Lender`, `Stipulation`,
  `Chargeback`, `Compliance`).
- **M11** Sales-side non-chat
  channels + customer journey
  (`FollowUpCadence`,
  `FollowUpTask`, `BeBack`).
- **M12** BHPH portfolio
  operations (`BhphNote`,
  `BhphPayment`,
  `BhphPromiseToPay`,
  `CollectionContact`,
  `Repossession`).
- **M13** Accounting substrate
  (`GLAccount`, `JournalEntry`,
  `JournalEntryLine`).
- **M14** Operator UI for
  accounting substrate (routes
  consumed).
- **M15** M9 sale-booking GL
  post (auto-fires when
  scenario seeds a Sale).
- **M16** M12 BHPH payment GL
  post (11:00 detector — beat
  entry; scenario timing
  ensures payments precede
  next detector run).
- **M17** Trial-balance
  materialization + `as_of`
  picker (freeze verb
  exercised by owner-role
  scenario briefs).

### Send-boundary verbs (enumerated at M18.1)

M18.1 planning enumerates every
existing verb that sends outbound
(email, SMS, API call to lender /
bureau / integrator / accounting-
provider) and wraps each with the
`if dealership.is_demo:
log_and_noop()` guard. Preliminary
list (verified at M18.1 open):

- **Follow-up cadence** — M11.4
  scheduled cadence dispatch
  (email + SMS).
- **BHPH collection** — M12.5
  collection-contact dispatch
  (email + SMS).
- **F&I lender-portal adapters**
  — M10 credit-application
  dispatch (external API stubs
  at v1, but real integrations
  will layer on this same
  boundary).
- **Compliance / bureau pulls**
  — M10 credit-bureau pull
  adapters (stubs at v1).
- **Chat outbound** — M6 /
  M11 outbound assistant
  messages that route to email
  / SMS if operator inbox is
  offline.
- **Test-drive scheduling** —
  M9 delivery reminders.

## 3. What's NOT in this milestone (deferrals)

Every deferral recorded with a
clear re-entry path. **Twelve
M18-specific + eleven universal =
23 deferrals.** Higher than
recent milestones because M18's
scope is deliberately narrow
(validation substrate, not
generic-purpose demo
infrastructure).

**M18-specific deferrals:**

1. **Public self-serve demo
   signup.** Testers are hand-
   provisioned by Chris (or a
   delegated tester wrangler)
   using the `demo_store` CLI.
   A public signup path
   defers to a hosted-demo
   milestone.
2. **Production deployment
   solely for this milestone.**
   Local + staging (if
   available) is sufficient for
   founder-led validation.
   Prod deployment defers per
   `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §5 architectural note.
3. **Full customer onboarding
   automation.** Onboarding
   real pilot customers into
   real-data stores is a
   separate initiative that
   follows M18 validation.
   Re-entry: pilot-onboarding
   milestone.
4. **Product tours and
   walkthrough overlays.**
   Scenarios are text briefs,
   not in-product tours. In-
   product guidance defers to
   a later UX milestone.
5. **Broad clickstream
   analytics.** `TesterFeedback`
   captures structured
   observations; general
   behavioral analytics
   defers. No third-party
   analytics SDK added.
6. **Session recording.** No
   video / DOM replay. Explicit
   non-goal per §5.e Option A.
7. **Generic whole-platform UI
   polish.** §5.f Option A
   locks: only workflow-
   blocking or materially
   misleading defects belong
   in M18. Broader polish
   records via `TesterFeedback`
   for a later dedicated
   milestone.
8. **Fake stubs for unfinished
   capabilities.** Scenarios
   must use only shipped
   behavior. If a scenario
   brief needs an unfinished
   integration, the brief is
   deferred (not the
   integration faked). Honesty
   about the capability
   boundary is more valuable
   than apparent
   completeness.
9. **Outbound email / SMS to
   real destinations.** §5.g
   Option A guard ensures
   every send-boundary verb
   checks `is_demo` and no-
   ops. Real destinations
   defer to the pilot-
   onboarding milestone.
10. **DMS / lender / bank /
    auction / bureau /
    payment / accounting-
    provider integrations.**
    Explicit non-goal per the
    milestone brief. Adapter
    stubs remain as they are
    at M17; scenarios do not
    exercise them.
11. **Pricing logic, billing,
    subscriptions, contracts.**
    Not part of the platform
    at v1. Defer to a
    commercial-shell milestone.
12. **Conversion of testers
    into real-data pilot
    stores.** That follows
    validation and receives
    its own implementation /
    onboarding scope. M18
    delivers the validation
    substrate; the conversion
    substrate is separate.

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

- **M1 tenancy carrier count
  test.** M18 adds one new
  tenanted model
  (`TesterFeedback`). Count
  49 → 50. `>=50` after M18.1.
- **Permission-class count
  test.** M18 adds zero new
  endpoints requiring new
  permission classes. All new
  endpoints reuse
  `IsSalesManagerOrOwnerAtActiveDealership`.
  **Zero-drift streak extends
  to ten consecutive
  milestones** (M10 → M18).
- **Endpoint count.** DRF
  admin surface 107 → 108
  (+1 for POST
  `/admin/demo-store/feedback/`).
  `>=108` after M18.5.
- **Migration count.**
  `0043`-`0046` → `0043`-
  `0048` (+1 at M18.1 for
  `Dealership.is_demo` +
  `demo_archetype` and +1 at
  M18.5 for `TesterFeedback`).
- **Frontend operator route
  count.** 20 (unchanged —
  M18 adds no operator
  routes per §5.f + Q7).
- **Celery-beat task
  families.** 10 (unchanged
  — M18 has no beat entry).
- **`services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`**
  — extended by one for
  `TesterFeedback`. Existing
  autofill signal wires the
  new model at
  `AppConfig.ready`.
- **`_auth_helpers.make_dealership`**
  — unchanged; new
  `make_demo_dealership`
  helper wraps it. Existing
  callers continue to work.
- **M16.1 `test_m161_bhph_payment_gl.py`**
  — the BHPH archetype's
  scenario builders produce
  `BhphPayment` rows that
  M16 detector will post
  overnight. Existing tests
  unaffected; scenario
  timing ensures payments
  are posted before the
  tester logs in.
- **M15.1 `test_m151_sale_booking.py`**
  — scenario builders that
  produce `Sale` rows
  trigger the M15 sync-
  sibling GL post via the
  same `record_sale` path
  real operators use.
- **M17.1 `test_m171_trial_balance_materialization.py`**
  — scenario briefs for
  owner + accounting roles
  exercise the M17.2
  frontend picker + freeze
  button + prior closes
  list.

## 5. Load-bearing decisions

Seven decisions. **All seven
confirmed as-recommended at
SESSION_146 M18.0 open.** Streak
extends to **77 planning-time as-
recommended M5.1 → M18.0** (nine
consecutive milestones now).
Historical §5 counts have been 6
per milestone; M18 at seven
reflects the mixed architecture /
ownership / representation /
safety scope.

### 5.a `[RESOLVED at SESSION_146 open]` — Milestone target selection

**Question.** Which candidate
from the M17 retrospective §8 +
M16 §8 unblocked-work list
defines M18 scope? Per M17 §9
standing question, is M18 an
intentional UI-polish milestone?

**Decision.** **Option O — non-
accounting target.** Milestone
name: **"Demo Store Simulation +
Pilot Validation Readiness."**
User named at SESSION_146 open.

**Rationale.** (1) The platform
now has a broad verified
capability surface through M17;
another isolated accounting
extension has diminishing
marginal value without validation
that the existing capability
surface actually resonates with
real independent-dealer
operators. (2) Founder-led
validation is what unlocks the
first commercial signals
(willingness-to-pay, requested
workflows, priority ordering).
(3) Answering M17 §9 standing
question: M18 is not the UX-
polish milestone — UI polish
records via `TesterFeedback` for
a later dedicated milestone with
real operator evidence. (4)
Testers Chris already knows in
the car business may become the
first pilot customers; this
milestone gives him the
infrastructure to have those
conversations without ad-hoc
plumbing. (5) The three
archetypes (retail/subprime,
floor-planned/recon-heavy, BHPH)
cover the operational shape range
of independent dealerships an
experienced operator would
recognize.

### 5.b `[RESOLVED at SESSION_146 open]` — Demo architecture (isolation mechanism)

**Question.** Do demo dealerships
live in the normal tenancy model
with an explicit designation, or
use another isolation mechanism?

- **Option A** — Add
  `Dealership.is_demo
  BooleanField(default=False)` +
  `Dealership.demo_archetype
  CharField(choices=DEMO_ARCHETYPE_CHOICES,
  blank=True)`. All existing
  tenancy paths continue to
  work. The flag gates
  seed/reset entry points; the
  archetype string gates
  scenario-pack targeting. One
  additive migration (`0047`
  — two `AddField`).
- **Option B** — Separate
  `DemoDealership` model.
- **Option C** — `slug`-prefix
  convention (`demo-*`) without
  a flag.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Preserves the
"one authoritative tenancy
model" invariant. (2) Guards
attach to a real column, not a
naming convention — a `slug`
rename can't break the guard.
(3) Option B forks the tenancy
discipline and creates parallel
authorization paths; every
existing tenant-check would
need a "…or DemoDealership"
branch. (4) The
`demo_archetype` vocab is a
fixed set (`retail_subprime` /
`floor_planned` / `bhph` /
blank); add-only per the
growth-only-list lesson. (5)
Migration is trivially additive
(two `AddField`, zero data
migration needed).

### 5.c `[RESOLVED at SESSION_146 open]` — Seed/reset ownership

**Question.** Where does the
authoritative path for scenario
creation and reset live?

- **Option A** — New
  `services/demo_store/`
  package + one management
  command `python manage.py
  demo_store {create|reset|list|export_feedback}
  --archetype <name> --slug
  <name>`. Service layer
  holds all logic; the command
  is the operator entry
  point. Every scenario
  builder wraps in
  `@transaction.atomic`.
  Reset raises
  `NonDemoResetError(RuntimeError)`
  if `Dealership.is_demo=False`
  + `assert dealership.is_demo`
  at top of every write verb.
- **Option B** — Django admin
  action wired directly.
- **Option C** — DRF endpoint
  for reset.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Belt-and-
suspenders guard —
`NonDemoResetError`
`RuntimeError` subclass +
`assert` at write-verb top
means a demo-store reset
against a non-demo dealership
is architecturally impossible.
(2) Management command is
scriptable, auditable, and
runs server-side without
network exposure. (3) Option
B ties reset to admin
permissions and makes
scripting harder. (4) Option
C exposes reset over network
before pilot-onboarding
infrastructure is ready —
premature attack surface.
(5) `services/demo_store/`
mirrors the shape of every
other M15+ service package
(`services/accounting/`
etc.) — familiar directory
structure.

### 5.d `[RESOLVED at SESSION_146 open]` — Scenario representation

**Question.** Are scenario
definitions versioned Python
fixtures/builders, structured
JSON/YAML specifications, or
a hybrid?

- **Option A** — Python
  builder classes in
  `services/demo_store/archetypes/{retail_subprime,floor_planned,bhph}.py`.
  Each archetype exposes a
  `build(dealership) ->
  ScenarioSummary` atomic
  verb constructing a
  coherent story. Type-
  checked, importable,
  testable, refactor-safe.
- **Option B** — JSON/YAML
  scenario specs loaded by a
  generic runner.
- **Option C** — Hybrid:
  JSON/YAML for headline
  attributes + Python for
  cross-domain relationships.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Cross-
domain relational integrity
(Sale ← VehicleCost ←
WorkOrder ← Vendor ←
ReconDecision) can't be
expressed cleanly in a
static spec — every seeded
Sale's `total_investment`
depends on VehicleCost sums
which depend on WorkOrder
allocations which depend on
Vendor + ReconDecision
routing. (2) Scenarios are
code, reviewed like code,
versioned like code —
refactors touch the same
tools as the rest of the
codebase. (3) Option C's
JSON+Python boundary is
inherently leaky — the
JSON schema and Python
builder always drift. (4)
Existing seed shapes
(`seed_copper_canyon_demo.py`)
already follow the Python-
builder pattern; M18 is
factoring the pattern
properly, not inventing
new mechanics. (5)
`ScenarioSummary` frozen
dataclass returned by
`build()` names the stock
numbers + lead IDs + user
usernames the tester will
use — an explicit "here's
what you got" contract
consumed by the daily
briefs.

### 5.e `[RESOLVED at SESSION_146 open]` — Tester feedback capture

**Question.** What is the
smallest useful feedback
mechanism?

- **Option A** — New
  `TesterFeedback` model
  (`dealership` FK CASCADE,
  `tester_name`,
  `scenario_slug`, `category`
  — one of `confusion` /
  `bug` / `feature_request` /
  `value_statement` /
  `willingness_to_pay`,
  `note`, `referenced_route`,
  `created_at`) + one POST
  endpoint + management-
  command exporter.
- **Option B** — Structured
  markdown files per session,
  checked into repo.
- **Option C** — Third-party
  feedback SaaS.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) One new
model, one endpoint, one
exporter — the minimum
mechanism that supports
structured tester feedback
+ export. (2) Option B
doesn't scale beyond Chris;
testers can't POST to a
markdown file. (3) Option C
violates the "no invasive
recording" clause +
introduces external
dependency + costs. (4)
`TesterFeedback.dealership`
FK CASCADE scopes to the
demo store — reset the
demo store, feedback goes
with it (or export first).
(5) Feedback categories
are a fixed vocab — exact-
set assertion at test time.
(6) Endpoint reuses
`IsSalesManagerOrOwnerAtActiveDealership`
per zero-drift lesson.

### 5.f `[RESOLVED at SESSION_146 open]` — UI correction boundary

**Question.** What UI
corrections belong in M18,
and what defers to a later
dedicated milestone?

- **Option A** — Explicit
  criteria: a UI defect
  belongs in M18 iff **(a)**
  it blocks a scenario brief
  from completing end-to-end
  via normal product routes
  OR **(b)** it displays
  materially incorrect
  information (wrong dealer
  name/branding, mismatched
  totals, stale
  `is_available`).
  Everything else recorded
  via §5.e for a later UX-
  polish milestone. Every
  M18.x UI correction
  records the specific
  scenario brief it unblocks
  in the retrospective §4.
- **Option B** — Zero UI
  corrections at M18.
- **Option C** — Broad "if
  you see something, fix
  it" latitude.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Explicit
criteria give the boundary
a defensible edge — the
retrospective can audit
every landed correction
against the criteria. (2)
Option B is too restrictive
if some corrections are
unavoidable to make
scenarios operable; the
alternative is deferring
scenarios instead of
fixing UI, which
undermines the milestone
goal. (3) Option C is
scope creep — turns M18
into a whole-platform UI
polish milestone. (4) The
scope-receipt log (every
correction cites its
blocking scenario) makes
the boundary
auditable without adding
process overhead. (5)
Matches M14 posture where
UX polish was scoped to
demonstrable operator-
evidence needs.

### 5.g `[RESOLVED at SESSION_146 open]` — Data realism and safety

**Question.** How does M18
ensure demo data is
unmistakably synthetic +
send-boundary verbs are
safely intercepted?

- **Option A** — Unmistakably
  synthetic:
  - **VINs:** 17-char strings
    prefixed `"DEMO"` +
    archetype code (2 chars)
    + 11 hex chars. Never a
    valid decodable VIN.
  - **Names:** fixed
    pseudonym roster in
    `services/demo_store/synthetic_names.py`
    (~40 pseudonyms). Never
    Faker.
  - **Phone:** `555-01xx`
    per NANP reserved-for-
    fiction block.
  - **Emails:**
    `<name>@demo.dealer-ai.example`
    — IANA-reserved
    `.example` TLD never
    routes.
  - **SSNs / payment
    credentials:** never
    populated. Scenarios
    avoid fields that
    require them; if a
    shipped capability
    demands one, the field
    stays blank.
  - **Outbound-send guard:**
    enumerate existing send-
    boundary verbs in M18.1
    planning + wrap each
    with early `if
    dealership.is_demo:
    log_and_noop()`.
- **Option B** — Faker-
  generated data.
- **Option C** — Real
  dealership data
  anonymized.

**Recommendation drafted.**
**Option A.**

**Rationale.** (1) Three
independent safety layers
— synthetic-format
convention + IANA-reserved
TLD + NANP fiction phones
each independently prevent
accidental real-world side
effects; layered together
they're belt-and-suspenders-
and-parachute. (2) Option
B: Faker occasionally
emits near-real values
(real ZIP+phone combos;
valid-format SSNs) — one
misplaced value could
trigger a real bureau
pull or a real SMS. (3)
Option C: anonymization
is hard; risk of
accidental leak.
Prospective testers may
know the real dealership
whose data was
anonymized. (4) The
outbound-send guard is
the load-bearing layer
— even if a synthetic
value passes through, the
guard prevents an
outbound send from
firing against real
destinations. (5)
Enumerating existing
send-boundary verbs at
M18.1 planning ensures
the guard is complete
before scenarios rely on
it.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   §6 (six lessons carry into M18) +
   §8 + §9 (M17 standing question
   resolved at M18.0 as
   non-UI-polish target)
6. `docs/CAPABILITY_MATRIX.md` §7r
   (M17 shipped surface — the
   substrate M18 scenarios
   consume via M17-shipped routes)
7. `docs/research/INDEPENDENT_DEALER_PIVOT.md`
   (the persona shape the three
   archetypes reflect)
8. `docs/research/SALES_DEPARTMENT_MAPPING.md`
   §retail + subprime motion
9. `docs/research/BHPH_OPERATIONS_MAPPING.md`
   §portfolio operations
10. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §floor-planned patterns
11. `docs/research/RECON_MAPPING.md`
    §outside-recon workflows

## 7. Sequencing

**Seven increments total.** Confirmed
as-recommended per §0.a. Combine
increments if implementation
evidence shows a smaller complete
shape; do not split merely to
match this draft.

### Increment 0 (M18.0) — Planning refinement + decision review

**Scope.** SESSION_146 (this
session). §5.a Option O confirmed
at open; §5.b-§5.g drafted with
recommendations for user
confirmation before M18.1 code.
Full memo expansion (this
document).

**Deliverable.**
- This planning memo, expanded
  from the M17.3 skeleton.
- §0.a change log with all
  seven §5 decisions resolved.
- Session handoff at
  `docs/handoffs/SESSION_146_m18_inc0_planning.md`.
- `00-START-NEXT-SESSION.md`
  overwritten with M18.1
  priority.

**Backend baseline unchanged:**
4,363 pass, 1 skipped, 0 fail.
Frontend Vitest unchanged: 140
pass.

### Increment 1 (M18.1) — Substrate: schema + service package + guards + TesterFeedback + send-boundary enumeration

**Scope.** SESSION_147. Single
backend increment. All M18
substrate lands here.

**Deliverable.**
- Migration `0047_m181_dealership_
  demo_flags.py` adding
  `Dealership.is_demo
  BooleanField(default=False)` +
  `Dealership.demo_archetype
  CharField(choices=DEMO_ARCHETYPE_CHOICES,
  blank=True, max_length=32)`
  per §5.b Option A. Additive-
  only; zero data migration.
- New model constants
  `DEMO_ARCHETYPE_RETAIL_SUBPRIME`
  / `DEMO_ARCHETYPE_FLOOR_PLANNED`
  / `DEMO_ARCHETYPE_BHPH` +
  `DEMO_ARCHETYPE_CHOICES`
  tuple in `models.py`.
- Migration `0048_m181_tester_
  feedback.py` adding
  `TesterFeedback` model per
  §5.e Option A: `dealership`
  FK CASCADE, `tester_name`
  CharField(64), `scenario_slug`
  CharField(64),
  `category`
  CharField(max_length=32,
  choices=TESTER_FEEDBACK_CATEGORY_CHOICES),
  `note` TextField, `referenced_route`
  CharField(max_length=255,
  blank=True), `created_at`
  auto_now_add.
- Register `TesterFeedback` in
  `_TENANT_CARRIER_MODEL_NAMES`
  in `services/tenancy.py`.
  Count 49 → 50.
- New package
  `services/demo_store/`:
  - `services/demo_store/__init__.py`
    with `__all__` exports.
  - `services/demo_store/errors.py`
    — `NonDemoResetError(RuntimeError)`
    domain exception per §5.c
    Option A.
  - `services/demo_store/synthetic_names.py`
    — fixed pseudonym roster
    (~40 pseudonyms per §5.g
    Option A). Fixed-vocab per
    the growth-only-list
    lesson: assertion-safe
    exact-set at test time.
  - `services/demo_store/synthetic_data.py`
    — helpers for
    `synthetic_vin(archetype,
    index)`,
    `synthetic_phone(index)`,
    `synthetic_email(name)`
    per §5.g Option A.
  - `services/demo_store/scenario_summary.py`
    — `ScenarioSummary` frozen
    dataclass (fields:
    `archetype`, `dealership_id`,
    `dealership_slug`,
    `seeded_stock_numbers`,
    `seeded_user_usernames`,
    `seeded_scenario_slugs`,
    `notes`).
  - `services/demo_store/registry.py`
    — `create_demo_store(*,
    slug, archetype, name=None,
    actor=None)` +
    `reset_demo_store(*,
    dealership, actor=None)` +
    `list_demo_stores() ->
    list[Dealership]`. All
    wrap in `@transaction.atomic`;
    `reset_demo_store` raises
    `NonDemoResetError` if
    `Dealership.is_demo=False`
    + `assert dealership.is_demo`
    at top of write path.
  - `services/demo_store/archetypes/__init__.py`
    — dispatcher mapping
    archetype string to builder
    module.
  - `services/demo_store/archetypes/base.py`
    — `ArchetypeBuilder` ABC
    with `build(dealership)
    -> ScenarioSummary`
    signature.
  - **Archetype-module stubs
    only at M18.1**
    (`retail_subprime.py`,
    `floor_planned.py`,
    `bhph.py`) that raise
    `NotImplementedError`
    until M18.2-M18.4 fill
    them in.
- New management command
  `dealer_ai/management/commands/demo_store.py`
  with subcommands
  `create` / `reset` / `list`
  / `export_feedback`. All
  subcommands dispatch to the
  service package.
- **Enumerate + guard outbound-
  send-boundary verbs.** M18.1
  planning at session open
  produces the complete list;
  the M18.1 commit wraps each
  with early
  `if dealership.is_demo:
  log_and_noop()` guard.
  Preliminary set per §2:
  follow-up cadence dispatch,
  BHPH collection dispatch,
  F&I lender-portal adapters,
  compliance / bureau pulls,
  chat outbound routing,
  test-drive delivery
  reminders.
- `_auth_helpers.make_dealership`
  companion
  `make_demo_dealership(archetype,
  slug)` helper for M18+
  tests.
- **Focused tests (~30-40
  target)** in new
  `tests/test_m181_demo_store_
  substrate.py`:
  - `Dealership.is_demo` +
    `demo_archetype` defaults
    on existing rows.
  - `DEMO_ARCHETYPE_CHOICES`
    exact-set equality
    (fixed-vocab lesson).
  - `TesterFeedback` model
    contract + tenancy
    autofill.
  - `create_demo_store` happy
    path + duplicate-slug
    (409 shape per M12
    `unique_together` posture).
  - `reset_demo_store` happy
    path.
  - `reset_demo_store` raises
    `NonDemoResetError` when
    `Dealership.is_demo=False`.
  - `assert dealership.is_demo`
    fires when write-path
    guard bypassed via mock
    (`RuntimeError`).
  - `list_demo_stores` returns
    only `is_demo=True` rows.
  - `synthetic_vin` produces
    17-char string prefixed
    `DEMO<archetype-code>`.
  - `synthetic_phone` produces
    `555-01xx` NANP.
  - `synthetic_email` produces
    `@demo.dealer-ai.example`.
  - Outbound-send-boundary
    guards no-op on demo
    dealerships (per-verb
    tests as evidence-
    justified).
  - `TESTER_FEEDBACK_CATEGORY_CHOICES`
    exact-set equality.
  - Tenancy carrier count
    47 (M16) → **50** at
    M18.1 (`>=` assertion
    per lesson).
  - Permission-class set
    equality unchanged (zero-
    drift streak ten
    consecutive milestones).
  - Endpoint count 107
    (unchanged at M18.1 — the
    `TesterFeedback` POST
    endpoint lands at M18.5).
- Zero frontend changes.
- Zero new post-LLM scrub
  stages.
- Zero new Celery-beat
  entries.

**Backend baseline target:**
4,363 → ~4,393-4,403 pass (+30-
40 tests, 0 regressions).
Frontend Vitest: 140 (unchanged
at M18.1).

### Increment 2 (M18.2) — Retail/subprime archetype pack

**Scope.** SESSION_148.
`services/demo_store/archetypes/retail_subprime.py`
fills in the ABC. Small used-car
lot; low volume; heavy sub-
prime lender usage; walk-in
buyers; cash-and-carry mix.

**Deliverable.**
- `retail_subprime.build(dealership)`
  atomic verb constructing:
  - ~20 vehicles (used only;
    $8k-$18k price band;
    2013-2019 model years;
    mixed makes).
  - 4 salespeople (sales
    manager + 3 advisors).
  - Sales pipeline: ~15
    active leads across
    stages; ~5 recent Sales
    (cash + retail-finance
    mix); 1 BHPH Sale
    exercising the M15
    sync-sibling GL post.
  - Recon activity: 3 in-
    recon vehicles with
    VehicleCost history +
    ConditionFindings +
    WorkOrders.
  - F&I: 2 recent
    CreditApplication rows
    with sub-prime lender
    routing; 1 Chargeback
    for M18 audit visibility.
  - Follow-up cadences: 4
    scheduled tasks
    (guarded by outbound-
    send guard).
- Fix UI defects only per
  §5.f Option A — blocking
  or materially misleading.
  Each fix commits with the
  scenario it unblocks in
  the message.
- Focused tests
  (~15-20 target) in
  `tests/test_m182_retail_
  subprime_archetype.py`
  asserting build produces
  the documented row counts,
  cross-domain integrity
  (VehicleCost sums, GL
  entries, lifecycle stages),
  and reset restores
  canonical state.

**Backend baseline target:**
~4,393-4,403 → ~4,408-4,423
pass (+15-20 tests, 0
regressions). Frontend Vitest:
unchanged.

### Increment 3 (M18.3) — Floor-planned archetype pack

**Scope.** SESSION_149.
`services/demo_store/archetypes/floor_planned.py`.
Mid-size independent; auction
floor-plan lender; outside-
recon vendor relationships;
active recon overrun scenario
for the recon lead role.

**Deliverable.**
- `floor_planned.build(dealership)`
  atomic verb constructing:
  - ~40 vehicles (used +
    a few CPO simulations;
    $12k-$35k; 2016-2022;
    Ford / Chevy / RAM /
    Toyota heavy).
  - 6 salespeople (owner +
    sales manager + 4
    advisors).
  - Sales pipeline: ~25
    active leads; ~10 recent
    Sales.
  - Recon activity: 5 in-
    recon vehicles including
    **1 with a documented
    $600+ overrun** (the
    recon-lead scenario
    brief).
  - Vendor relationships: 4
    active vendors + recent
    VendorCommunication rows.
  - Follow-up cadences +
    BeBack rows.
- Fix UI defects only per
  §5.f.
- Focused tests
  (~15-20 target) in
  `tests/test_m183_floor_
  planned_archetype.py`.

**Backend baseline target:**
~4,408-4,423 → ~4,423-4,443
pass. Frontend Vitest:
unchanged.

### Increment 4 (M18.4) — BHPH archetype pack

**Scope.** SESSION_150.
`services/demo_store/archetypes/bhph.py`.
Small BHPH dealership; active
portfolio of ~30 notes; weekly
and biweekly payment
frequencies; recent NSF +
promise-to-pay activity;
collector role central to
daily workflow.

**Deliverable.**
- `bhph.build(dealership)`
  atomic verb constructing:
  - ~25 vehicles (used only;
    $4k-$12k price band —
    the BHPH mental model;
    2010-2017; higher
    mileage).
  - 4 salespeople (owner +
    sales manager + 2
    collectors).
  - BHPH portfolio: ~30
    active BhphNotes across
    aging buckets; ~150
    BhphPayment rows
    (historical + recent);
    3 BhphPromiseToPay in
    various states; 5
    CollectionContact
    records; 1 Repossession
    (recovered).
  - Sales pipeline: ~10
    active leads; ~5 recent
    BHPH Sales exercising
    M12.1 note creation +
    M15 sync-sibling GL
    post.
  - Recent payments (paid
    ≤ 24 hours ago) so the
    11:00 M16 detector
    posts them into the GL
    for the accounting
    role's trial-balance
    view.
- Fix UI defects only per
  §5.f.
- Focused tests
  (~15-20 target) in
  `tests/test_m184_bhph_
  archetype.py`.

**Backend baseline target:**
~4,423-4,443 → ~4,438-4,463
pass. Frontend Vitest:
unchanged.

### Increment 5 (M18.5) — Role-based daily briefs + feedback endpoint + exporter

**Scope.** SESSION_151. Role
briefs across all three
archetypes + operator-facing
feedback capture endpoint +
CSV exporter.

**Deliverable.**
- `services/demo_store/briefs/`
  package with per-archetype
  daily-brief markdown files:
  - `retail_subprime/owner.md`,
    `sales_manager.md`,
    `recon.md`, `accounting.md`
    (BHPH-collector.md omitted
    — this archetype does not
    run BHPH).
  - `floor_planned/*` (five
    briefs including
    BHPH-collector.md only
    if the archetype seeds
    a small BHPH sub-book;
    else omitted).
  - `bhph/*` (five briefs
    including BHPH-collector).
- Each brief follows the
  standard structure per the
  milestone brief: what
  happened before login;
  what the operator needs to
  accomplish today; what
  information is intentionally
  incomplete or problematic;
  which shipped capabilities
  should help; what successful
  completion looks like; what
  must remain discoverable
  without a guided click
  path.
- New DRF admin endpoint
  `POST /admin/demo-store/feedback/`
  reusing
  `IsSalesManagerOrOwnerAtActiveDealership`
  (zero-drift streak extends
  to ten consecutive
  milestones). Body:
  `{"tester_name", "scenario_slug",
  "category", "note",
  "referenced_route"}`.
  Returns 201 with the
  persisted `TesterFeedback`
  projection.
- `demo_store export_feedback`
  subcommand: writes CSV to
  stdout or `--out <path>`.
  Columns: id, dealership_slug,
  tester_name, scenario_slug,
  category, note,
  referenced_route,
  created_at.
- Fix UI defects only per
  §5.f — likely target if
  needed: adding a
  "TesterFeedback" capture
  form component consumable
  from within a demo
  dealership. In-place
  extension per M17 §6
  lesson 6; **no new
  operator route.**
- Focused tests (~15-20
  target) in
  `tests/test_m185_briefs_
  and_feedback.py`:
  briefs load per
  archetype; POST endpoint
  201 happy path; 400
  invalid category; 403
  non-permitted role;
  export CSV shape.

**Backend baseline target:**
~4,438-4,463 → ~4,453-4,483
pass. Frontend Vitest: 140
→ ~140-155 pass (only if a
feedback capture form
component lands per §5.f
evidence).

### Increment 6 (M18.6) — Close-out

**Scope.** SESSION_152. Docs.
Retrospective + capability
matrix §7s + roadmap flip +
M19 planning skeleton per
standing user directive.

**Deliverable.**
- `docs/roadmap/MILESTONE_18_
  RETROSPECTIVE.md` written
  at M18.6 close.
- `docs/CAPABILITY_MATRIX.md`
  §7s section describing
  the M18 demo-store
  simulation + pilot-
  validation-readiness
  surface.
- `docs/roadmap/IMPLEMENTATION_
  ROADMAP.md` §Milestone 18
  SHIPPED entry added.
- Frontmatter flip on this
  doc: `status: active` →
  `status: shipped`.
- `docs/roadmap/MILESTONE_19_
  PLANNING.md` skeleton for
  the M18 §8 unblocked-
  work list.
- `00-START-NEXT-SESSION.md`
  overwritten with M19.0
  priority.
- Coordinated commit
  landing all M18.6 docs
  together.

**Backend baseline at M18
close:** ~4,453-4,483 pass
(M18.5 delta sustained; no
code changes at M18.6).
**Frontend Vitest at M18
close:** matches M18.5
target.

---

*Full memo. All seven §5
decisions confirmed as-
recommended at SESSION_146
M18.0 open.*
