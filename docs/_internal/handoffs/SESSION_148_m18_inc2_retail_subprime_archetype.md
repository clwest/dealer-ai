---
title: "SESSION_148 handoff — Milestone 18 · Increment 2 (M18.2 — Retail/subprime archetype pack)"
status: historical
type: handoff
date: 2026-08-02
session: 148
milestone: 18
milestone_status: in-progress
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
increment: 2
increment_status: shipped
commit: a7eb65e
---

# SESSION_148 — Milestone 18 · Increment 2 (M18.2 — Retail/subprime archetype pack)

## What shipped

Single backend increment per
`MILESTONE_18_PLANNING.md` §7 M18.2. First
of three archetype pack increments —
replaces the M18.1
`RetailSubprimeArchetypeBuilder` stub with
an atomic `build()` verb constructing a
coherent operational story across the
shipped M1-M17 surface.

**Three §0.a M18.2 implementation-time
decisions recorded** (do not count against
planning-time streak per M10 §9):

1. **Chargeback deferred to M18.5.**
   Chargeback substrate chain
   (`DealStructure` → `Contract` →
   `Funding` → `BackEndProductAgreement` →
   `Chargeback`) is 4-5 additional
   entities with distinct service verbs.
   Deferring keeps M18.2 focused on the
   core retail/subprime persona; a
   dedicated "F&I chargeback event"
   scenario brief at M18.5 is a natural
   home for it.
2. **Registry seeds the M13.1 default
   COA.** Both `create_demo_store` and
   `reset_demo_store` now call
   `seed_default_coa(dealership)` after
   creating/refreshing the demo
   Dealership. Every Dealership must have
   the default chart of accounts for M15+
   sale-booking GL post to succeed.
   Corrects an M18.1 substrate omission
   surfaced by the first retail/subprime
   build attempt.
3. **Reverse-order + demo-owned-User
   cleanup on reset.**
   `_delete_demo_store_children` now
   iterates `_TENANT_CARRIER_MODEL_NAMES`
   in **reverse** order so PROTECT FKs
   satisfy (e.g. `JournalEntryLine.account`
   PROTECT vs `GLAccount`); also deletes
   Users whose only memberships are at
   this dealership so the next build
   doesn't collide on the `username`
   unique constraint. Users with
   memberships elsewhere are preserved.

## Delivered

**`services/demo_store/archetypes/retail_subprime.py`
— full builder** (~750 lines) replacing
the M18.1 stub.

- **Fixed inventory + staffing specs.**
  Deterministic tuples (`_INVENTORY`,
  `_STAFF`, `_LEADS`, `_SALES`,
  `_RECON_TARGETS`, `_CREDIT_APPS`,
  `_FOLLOW_UP_LEADS`) so `reset_demo_store`
  yields identical canonical starting
  state on every reset.
- **`RetailSubprimeArchetypeBuilder.build()`**
  atomic verb (delegated to via registry's
  `@transaction.atomic`). Asserts
  `dealership.is_demo=True` at top
  (belt-and-suspenders per §5.c). Calls
  seven private seeders:
  - `_seed_inventory` — 20 Vehicles ($8k-
    $18k, used, 2013-2019 mixed makes with
    synthetic `DEMORS`-prefixed VINs) +
    VehicleAcquisition (auction / trade /
    private mix) + `ensure_current_stage`
    for lifecycle bootstrap (idempotent
    in both test + prod modes).
  - `_seed_staff` — 4 Django Users +
    UserDealershipRole memberships +
    Salespeople with `user` link
    populated. Synthetic email + phone
    per §5.g.
  - `_seed_leads` — 15 CustomerLeads
    across urgency × channel mix (some
    assigned to salespeople, some
    unassigned).
  - `_seed_recon` — 3 in-recon vehicles
    with full operational story:
    VehicleStage flipped to `recon` +
    3-event progression
    (`incoming → inspection → recon`);
    completed ConditionReport with 2
    ConditionFindings; must-do
    ReconDecision per finding; outsourced
    WorkOrder to a shared demo Vendor
    with `approved_at` + `started_at`
    populated; 2 WorkOrderParts + 1
    WorkOrderFinding link; 4
    VehicleCost rows (parts + labor +
    tires + detail) already-GL-posted
    (`posted_at` populated).
  - `_seed_sales` — 5 recent Sales via
    `record_sale` service verb (fires
    M15.1 sync-sibling GL post): 2
    cash + 2 retail-finance + 1 BHPH.
    Each Sale gets a buyer CustomerLead
    + a matching acquisition-basis
    VehicleCost row so the M15
    sale-booking journal has a
    non-zero COGS to clear.
  - `_seed_credit_applications` — 2
    CreditApplication rows via
    `record_credit_application` service
    verb, attached to the retail-
    finance Sales, with sub-prime
    lender routing documented in
    `notes`.
  - `_seed_follow_ups` — 1 follow-up
    cadence via `start_cadence` service
    verb (1wk template auto-creates 3
    FollowUpTask rows at 1/3/7 day
    offsets).
- **Populates `ScenarioSummary`** with
  seeded stock numbers + user usernames +
  six scenario brief slugs consumed by
  M18.5 daily briefs (`owner_daily_snapshot`
  / `sales_manager_morning_pipeline` /
  `advisor_walk_in_workup` /
  `recon_lead_finish_line` /
  `office_accounting_close` /
  `subprime_credit_app_intake`).

**`services/demo_store/registry.py` extensions:**

- `create_demo_store` + `reset_demo_store`
  now call `seed_default_coa(dealership)`
  after Dealership creation / child
  cleanup.
- `_delete_demo_store_children` iterates
  `_TENANT_CARRIER_MODEL_NAMES` in
  **reverse** order (child-before-parent
  for PROTECT FKs) + deletes demo-owned
  Users after tenancy carriers cleared.

**Test coverage — 33 focused tests** in
new
`tests/test_m182_retail_subprime_archetype.py`:

- Row-count contract (11 tests):
  vehicles match spec; acquisitions
  match vehicles; salespeople match spec;
  leads = pipeline leads + Sale buyers;
  sales match spec; BhphNote count
  matches BHPH Sales; recon vehicles
  have ConditionReports; ≥2 findings +
  ≥2 decisions per recon vehicle;
  WorkOrder + parts + findings present;
  credit apps match spec; follow-up
  cadence + tasks present.
- Cross-domain integrity (6 tests):
  every Sale has same-tenant buyer;
  every CreditApp references same-tenant
  Sale; recon vehicles have coherent
  3-event stage progression; recon
  VehicleCost sums reconcile with
  documented spend; shared outsourced
  Vendor reused across recon targets;
  every Salesperson has User linkage.
- M15 sync-sibling GL post verification
  (2 tests): JournalEntry rows exist
  post-build; each Sale's descriptions
  references its stock number.
- `ScenarioSummary` contract (6 tests):
  type + archetype + dealership_id +
  stock numbers + user usernames +
  scenario slugs populated.
- Synthetic-only data safety (4 tests):
  every VIN prefixed `DEMORS`; every
  lead email uses `@demo.dealer-ai.example`;
  every lead phone uses `555-01xx` NANP;
  every seeded User email uses
  `@demo.dealer-ai.example`.
- Reset canonical state (2 tests): reset
  restores canonical row counts + clears
  rogue rows; Dealership pk stable.
- Builder direct-instantiation smoke (1
  test).

**M18.1 test updates:** two tests in
`tests/test_m181_demo_store_substrate.py`
updated to reference `floor_planned`
(still a stub) instead of
`retail_subprime` (now real):
`test_create_fails_when_archetype_still_a_stub`
+ `test_create_subcommand_surfaces_stub_error`.

## Baseline delta

- **Backend: 4,416 → 4,449 pass**, 1
  skipped, 0 fail. **+33 tests, 0
  regressions.** Exceeded 15-20 planning
  target by 13 due to cross-domain
  integrity coverage.
- Migrations 0043-0047 (unchanged at
  M18.2).
- Tenancy carriers **50** (unchanged).
- DRF admin surface **107** (unchanged —
  feedback POST lands at M18.5).
- Frontend Vitest **140** (unchanged —
  no frontend at M18.2).
- Frontend operator routes **20**
  (unchanged).
- Permission classes **7** — **zero-drift
  streak now eleven consecutive
  milestones** (M10 → M18.2).
- Celery-beat task families **10**
  (unchanged).

## Streak update

**77 planning-time as-recommended M5.1 →
M18.0** (unchanged — M18.2 is
implementation-time). Three §0.a M18.2
implementation-time decisions recorded
(Chargeback deferral, COA seeding in
registry, reverse-order + user cleanup
on reset).

## What's next: SESSION_149 M18.3 floor-planned archetype pack

Per `MILESTONE_18_PLANNING.md` §7 M18.3:

- Replace stub in
  `services/demo_store/archetypes/floor_planned.py`
  with the atomic `build()` verb.
- Mid-size independent; auction floor-
  plan lender; outside-recon vendor
  relationships; active recon overrun
  scenario for the recon lead role.
- ~40 vehicles ($12k-$35k, used + a few
  CPO simulations, 2016-2022, Ford /
  Chevy / RAM / Toyota heavy).
- 6 salespeople (owner + sales manager +
  4 advisors).
- Sales pipeline: ~25 active leads; ~10
  recent Sales.
- Recon activity: 5 in-recon vehicles
  including **1 with a documented $600+
  overrun** (the recon-lead scenario
  brief centerpiece).
- Vendor relationships: 4 active vendors
  + recent VendorCommunication rows.
- Follow-up cadences + BeBack rows.
- Fix UI defects only per §5.f.
- Focused tests (~15-20 target) in
  `tests/test_m183_floor_planned_archetype.py`.

**Backend baseline target at M18.3
close:** 4,449 → ~4,464-4,484 pass.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
7. `docs/handoffs/SESSION_146_m18_inc0_planning.md`
8. `docs/CAPABILITY_MATRIX.md` §7r
9. `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
   (pattern template for M18.3/M18.4)
10. `backend/dealer_ai/tests/test_m182_retail_subprime_archetype.py`
    (test-coverage template)
