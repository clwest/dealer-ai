---
title: "SESSION_150 handoff — Milestone 18 · Increment 4 (M18.4 — BHPH archetype pack)"
status: historical
type: handoff
date: 2026-08-02
session: 150
milestone: 18
milestone_status: in-progress
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
increment: 4
increment_status: shipped
commit: 42c604d
---

# SESSION_150 — Milestone 18 · Increment 4 (M18.4 — BHPH archetype pack)

## What shipped

Single backend increment per
`MILESTONE_18_PLANNING.md` §7 M18.4.
Third and final archetype pack —
replaces the last remaining M18.1
stub with an atomic `build()` verb
constructing a small BHPH dealership
with an active portfolio + collection
workflow substrate.

**All three archetypes now shipped**
(retail_subprime + floor_planned +
bhph). The demo-store package is
code-complete for archetype
construction; M18.5 layers the
operator-facing surfaces (daily
briefs + TesterFeedback endpoint +
CSV exporter) on top.

**§0.a M18.2 decision 1 continues to
apply** — Chargeback still deferred
to M18.5.

## The M16 detector eligibility anchor

The BHPH archetype seeds ~5 payments
with `posted_at=NULL` within the last
24 hours. Per §5.d Option A the
M16.1 detector filters
`posted_at__isnull=True` and posts
matching rows into the GL on the
next 11:00 cycle. **Testers walking
the accounting-role daily brief at
M18.5 see the trial-balance surface
change after the 11:00 cycle** —
this timing dynamic is the
operational value the BHPH archetype
demonstrates.

The remaining ~135-150 historical
payments have `posted_at` populated
(already-detected), so the M14.2
trial-balance page + M14.3 journal-
entry browser render the portfolio
activity from the moment the tester
logs in.

## Delivered

**`services/demo_store/archetypes/bhph.py`
— full builder** (~810 lines).

- **Fixed inventory + staffing specs**
  — deterministic reset produces
  identical canonical state:
  - `_INVENTORY` — 25 primary
    vehicles ($4k-$12k, 2010-2017,
    reliable-transportation mix,
    `DEMOBH`-VINs).
  - `_STAFF` — 4 (owner + sales
    manager + 2 collectors).
  - `_LEADS` — 10 pipeline leads.
  - `_RECENT_SALES` — 5 recent BHPH
    sales originated via `record_sale`
    + `record_bhph_note`.
  - `_HISTORICAL_NOTE_SPECS` — 25
    older notes with mixed aging
    buckets (current / 30-day past-
    due / 60-day past-due) + mixed
    payment frequencies (weekly +
    biweekly).
  - `_PROMISES` — 3 promise-to-pay
    records covering all three
    states (promised + kept +
    broken).
  - `_COLLECTION_CONTACTS` — 5
    rows across channels (phone,
    SMS, letter) + outcomes
    (contact_made, left_message,
    no_answer).
  - `_REPOSSESSION_NOTE_INDEX` — 1
    recovered repossession target
    (60+ day past-due note).
  - `_FOLLOW_UP_LEADS` — 2 cadences
    (1wk + 24hr).
- **`build()` verb** delegates to nine
  seeders:
  - `_seed_inventory` — 25 vehicles
    + VehicleAcquisition (wholesale
    + auction + private mix
    matching BHPH sourcing) + stage
    bootstrap.
  - `_seed_staff` — 4 Users +
    UserDealershipRole + Salespeople.
  - `_seed_leads` — 10
    CustomerLeads assigned to
    collectors.
  - `_seed_recent_sales` — 5 BHPH
    Sales via `record_sale` (M15
    sync-sibling GL post fires) +
    `record_bhph_note` origination.
  - `_seed_historical_notes` — 25
    additional Sale + BhphNote
    pairs via direct-create.
    Creates 5 extra "historical"
    vehicles (BH-H-01..BH-H-05) to
    absorb the note count over the
    Vehicle.OneToOne(Sale)
    invariant. **Scenario-authored
    posture recorded**: historical
    sales bypass `record_sale` to
    avoid noise in JournalEntry
    (the 5 recent sales already
    exercise M15).
  - `_seed_historical_payments` —
    ~135-150 BhphPayment rows.
    Historical rows have
    `posted_at` populated; ~5
    recent rows (paid_at within
    last 24h) have
    `posted_at=NULL` for M16
    detector eligibility.
  - `_seed_promises` — 3 promise-
    to-pay via `record_promise` +
    `mark_kept` for the kept one
    (links to a real BhphPayment
    via `actual_payment` FK).
  - `_seed_collection_contacts` —
    5 rows via `record_contact`.
  - `_seed_repossession` — 1 order
    + `mark_recovered` transition
    on the past-due note.
  - `_seed_follow_ups` — 2 cadences
    via `start_cadence`.
- Populates `ScenarioSummary` with
  seeded stock numbers + user
  usernames + **six scenario brief
  slugs** including
  `bhph_collector_daily_book`,
  `bhph_promise_followup`, and
  `repo_intake_handoff`.

**Test coverage — 31 focused tests** in
new `tests/test_m184_bhph_archetype.py`:

- **Row-count contract (9):** vehicles
  (25 inventory + 5 historical);
  acquisitions (25 primary only);
  salespeople; notes = 30; payments
  ≥ 100; promises; contacts;
  repossession = 1 recovered; cadences.
- **M16 detector eligibility (3):**
  ≥5 payments with `posted_at=NULL`;
  unposted payments are recent (paid
  within 2 days); historical payments
  (paid >3 days ago) all have
  `posted_at` populated.
- **Cross-domain integrity (5):**
  every note origins from a BHPH
  sale; promise states include all
  three variants (promised + kept +
  broken); kept promise links a
  payment; repossession in same
  tenant; salesperson-user linkage.
- **M15 GL posting (2):** recent
  BHPH sales produce JournalEntry;
  each stock referenced.
- **ScenarioSummary contract (5):**
  type + archetype + all inventory
  stocks + usernames + collector
  slug + repo slug present.
- **Synthetic-only data safety
  (4):** every VIN prefixed
  `DEMOBH`; lead emails + phones;
  seeded User emails.
- **Reset canonical state (2):**
  reset restores note + payment
  counts; repossession state
  survives reset.
- **Builder direct smoke (1).**

**M18.1 test updates** — 3 tests
updated to reflect all archetypes
shipped:

- `test_create_all_shipped_archetypes`
  iterates all three real builders.
- `test_create_subcommand_succeeds_for_shipped_archetype`
  exercises CLI happy path.
- `test_reset_clears_children_and_reseeds_via_real_archetype`
  replaces the "stub raises
  NotImplementedError" test with
  the actual-behavior test.

## Baseline delta

- **Backend: 4,483 → 4,514 pass**, 1
  skipped, 0 fail. **+31 tests, 0
  regressions.** Exceeded 15-20
  planning target by 11 due to M16
  detector + promise-state coverage.
- Migrations 0043-0047 (unchanged).
- Tenancy carriers **50**
  (unchanged).
- DRF admin surface **107**
  (unchanged — feedback POST lands
  at M18.5).
- Frontend Vitest **140** (unchanged
  — no frontend at M18.4).
- Frontend operator routes **20**
  (unchanged).
- Permission classes **7** —
  **zero-drift streak now thirteen
  consecutive milestones** (M10 →
  M18.4).
- Celery-beat task families **10**
  (unchanged).

## Streak update

**77 planning-time as-recommended
M5.1 → M18.0** (unchanged — M18.4
is implementation-time). §0.a
decisions continue to hold (M18.2
Chargeback deferral + M18.1
outbound-send-boundary enumeration
+ M18.2 registry COA seeding +
reverse-order + User cleanup).

## What's next: SESSION_151 M18.5 briefs + feedback endpoint + exporter

Per `MILESTONE_18_PLANNING.md` §7
M18.5:

- **Per-archetype daily brief
  markdown files** in
  `services/demo_store/briefs/`:
  - `retail_subprime/{owner,
    sales_manager, recon,
    accounting}.md`
  - `floor_planned/{owner,
    sales_manager, recon,
    accounting}.md` — with the
    `recon_lead_overrun_intervention`
    brief as centerpiece.
  - `bhph/{owner, sales_manager,
    recon, accounting,
    collector}.md` — with the M16
    detector timing scenario for
    accounting.
  - Each brief follows the standard
    structure: what happened
    before login; what today's
    task is; what's intentionally
    incomplete; which shipped
    capabilities help; what
    successful completion looks
    like; what remains
    discoverable without a guided
    click path.
- **New DRF endpoint** `POST
  /admin/demo-store/feedback/`
  reusing `IsSalesManagerOrOwnerAtActiveDealership`.
  Body: `{tester_name,
  scenario_slug, category, note,
  referenced_route}`. Returns 201
  with the persisted TesterFeedback
  projection.
- **Fill in the
  `export_feedback` CSV writer**
  (M18.1 shipped the scaffold).
- Fix UI defects only per §5.f —
  likely target: a small feedback
  capture form component wired
  into the M14 admin surface.
- Focused tests (~15-20 target)
  in `tests/test_m185_briefs_
  and_feedback.py`.

**Backend baseline target at
M18.5 close:** 4,514 → ~4,529-
4,549 pass. Frontend Vitest: 140
→ ~140-155 pass (only if a
feedback capture form component
lands per §5.f evidence).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`
7. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
8. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
9. `docs/CAPABILITY_MATRIX.md` §7r
10. `backend/dealer_ai/services/demo_store/`
    (complete archetype surface —
    consumed by M18.5 briefs)
