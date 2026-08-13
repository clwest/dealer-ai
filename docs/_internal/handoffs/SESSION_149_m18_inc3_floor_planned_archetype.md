---
title: "SESSION_149 handoff — Milestone 18 · Increment 3 (M18.3 — Floor-planned archetype pack)"
status: historical
type: handoff
date: 2026-08-02
session: 149
milestone: 18
milestone_status: in-progress
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
increment: 3
increment_status: shipped
commit: aa6343f
---

# SESSION_149 — Milestone 18 · Increment 3 (M18.3 — Floor-planned archetype pack)

## What shipped

Single backend increment per
`MILESTONE_18_PLANNING.md` §7 M18.3.
Second of three archetype pack
increments — replaces the M18.1
`FloorPlannedArchetypeBuilder` stub
with an atomic `build()` verb
anchored on a **documented recon
overrun scenario**.

**§0.a M18.2 decision 1 continues to
apply** — Chargeback still deferred
to M18.5.

## Delivered

**`services/demo_store/archetypes/floor_planned.py`
— full builder** (~750 lines).

- **Fixed inventory + staffing specs**
  (`_INVENTORY`, `_STAFF`, `_LEADS`,
  `_SALES`, `_RECON_TARGETS`,
  `_VENDORS`, `_CREDIT_APPS`,
  `_FOLLOW_UP_LEADS`, `_BE_BACKS`) —
  deterministic so `reset_demo_store`
  yields identical canonical state.
- **`build()` verb** delegates to nine
  seeders:
  - `_seed_inventory` — 40 Vehicles
    ($12k-$35k, 2016-2022, Ford /
    Chevy / RAM / Toyota heavy,
    `DEMOFP`-prefixed VINs) +
    VehicleAcquisition (auction-heavy
    per the persona) + lifecycle
    stage bootstrap.
  - `_seed_staff` — 6 Users +
    UserDealershipRole (dealer owner +
    sales manager + 4 advisors) +
    Salespeople linked to Users.
  - `_seed_leads` — 25 CustomerLeads
    across urgency × channel mix
    (walk-in / chat / listing form /
    phone).
  - `_seed_vendors` — 4 shared
    Vendors: sunset-mechanical (owns
    every recon WO), riverside-body-
    paint, clearview-glass, elite-
    detail-bay.
  - `_seed_recon` — 5 in-recon
    vehicles with full ConditionReport
    + 2 findings + must-do + should-
    do ReconDecisions + WorkOrder +
    2 WorkOrderParts + 3-event stage
    progression. **First recon target
    is the documented overrun
    anchor:** transmission failure
    scenario with
    `authorized_cost=$600` vs
    `actual_cost=$1,425` ($825
    overrun) + 3 VehicleCost rows
    summing to $1,425 + 2
    VendorCommunication rows
    (outbound approval-sent + inbound
    narrative-log documenting the
    escalation).
  - `_seed_sales` — 10 Sales via
    `record_sale` service verb (fires
    M15.1 sync-sibling GL post; 8
    retail-finance across 3 lenders +
    2 cash).
  - `_seed_credit_applications` — 3
    CreditApplications via
    `record_credit_application`
    (paper + tablet mix).
  - `_seed_follow_ups` — 3 cadences
    (2 × 1wk + 1 × 24hr) auto-
    creating 7+ FollowUpTask rows.
  - `_seed_be_backs` — 3 BeBack rows
    (test-drive promised +
    bring-co-signer returned +
    bring-trade-in promised).
- Populates `ScenarioSummary` with
  seeded stock numbers + user
  usernames + **six scenario slugs**
  including `recon_lead_overrun_intervention`
  for the M18.5 daily briefs.

**Test coverage — 34 focused tests** in
new
`tests/test_m183_floor_planned_archetype.py`:

- **Row-count contract (10 tests):**
  vehicles match spec; acquisitions
  match vehicles; salespeople; leads =
  pipeline + Sale buyers; sales;
  recon vehicles have full story;
  vendors; credit apps; follow-up
  cadences + ≥7 tasks; be-backs.
- **Recon overrun scenario
  visibility (4 tests):** the anchor
  WorkOrder's `actual_cost -
  authorized_cost ≥ $600`; the
  VehicleCost sum reconciles with
  `actual_cost`; VendorCommunication
  history documents the escalation
  ("$1,425" appears in the narrative
  log); non-anchor recon WOs have
  no `actual_cost` (mid-work).
- **Cross-domain integrity (6):**
  every Sale has same-tenant buyer;
  every CreditApp references same-
  tenant Sale; recon vehicles have
  3-event stage progression; all
  recon WOs share the mechanical
  vendor; WorkOrderFinding +
  WorkOrderPart rows present; every
  Salesperson has User linkage.
- **M15 GL post verification (2):**
  JournalEntry count ≥ Sale count;
  each Sale's stock number appears
  in an M9-sale-booking entry.
- **ScenarioSummary contract (5):**
  type + archetype + dealership_id +
  slug + stock numbers + usernames +
  overrun scenario slug present.
- **Synthetic-only data safety (4):**
  every VIN prefixed `DEMOFP`; every
  lead email `@demo.dealer-ai.example`;
  every lead phone `555-01xx`; every
  seeded User email `@demo.dealer-ai.example`.
- **Reset canonical state (2):**
  reset restores canonical row
  counts + clears rogue rows;
  overrun scenario survives reset.
- **Builder direct smoke (1).**

**M18.1 test updates** — 2 tests that
referenced `floor_planned` as a stub
now reference `bhph` (last remaining
stub until M18.4):

- `test_create_fails_when_archetype_still_a_stub`
- `test_create_subcommand_surfaces_stub_error`

## Baseline delta

- **Backend: 4,449 → 4,483 pass**, 1
  skipped, 0 fail. **+34 tests, 0
  regressions.** Exceeded 15-20
  planning target by 14 due to
  overrun scenario coverage.
- Migrations 0043-0047 (unchanged at
  M18.3).
- Tenancy carriers **50** (unchanged).
- DRF admin surface **107**
  (unchanged — feedback POST lands at
  M18.5).
- Frontend Vitest **140** (unchanged
  — no frontend at M18.3).
- Frontend operator routes **20**
  (unchanged).
- Permission classes **7** —
  **zero-drift streak now twelve
  consecutive milestones** (M10 →
  M18.3).
- Celery-beat task families **10**
  (unchanged).

## Streak update

**77 planning-time as-recommended
M5.1 → M18.0** (unchanged — M18.3 is
implementation-time). §0.a M18.2
decision 1 (Chargeback deferral)
continues to apply through M18.3.

## What's next: SESSION_150 M18.4 BHPH archetype pack

Per `MILESTONE_18_PLANNING.md` §7
M18.4:

- Replace stub in
  `services/demo_store/archetypes/bhph.py`
  with the atomic `build()` verb.
- Small BHPH dealership; active
  portfolio of ~30 notes; weekly and
  biweekly payment frequencies;
  recent NSF + promise-to-pay
  activity; collector role central
  to daily workflow.
- ~25 vehicles ($4k-$12k, used
  only, 2010-2017, higher mileage).
- 4 salespeople (owner + sales
  manager + 2 collectors).
- BHPH portfolio: ~30 active
  BhphNotes across aging buckets;
  ~150 BhphPayment rows (historical
  + recent); 3 BhphPromiseToPay in
  various states; 5 CollectionContact
  records; 1 Repossession (recovered).
- Sales pipeline: ~10 active leads;
  ~5 recent BHPH Sales exercising
  M12.1 note creation + M15 sync-
  sibling GL post.
- Recent payments (paid ≤ 24 hours
  ago) so the 11:00 M16 detector
  posts them into the GL for the
  accounting role's trial-balance
  view.
- Fix UI defects only per §5.f.
- Focused tests (~15-20 target) in
  `tests/test_m184_bhph_archetype.py`.

**Backend baseline target at M18.4
close:** 4,483 → ~4,498-4,518 pass.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
7. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
8. `docs/CAPABILITY_MATRIX.md` §7r
9. `backend/dealer_ai/services/demo_store/archetypes/floor_planned.py`
   (pattern template for M18.4)
10. `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
    (M15 sync-sibling reference)
