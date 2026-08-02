---
state: active
date: 2026-08-02
last_session_shipped: SESSION_148
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: in-progress
next_session: SESSION_149
next_milestone: 18
next_milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
next_increment: 3
next_increment_name: "M18.3 — Floor-planned archetype pack"
---

# Next session — SESSION_149 · Milestone 18 · Increment 3 (M18.3 — Floor-planned archetype pack)

> **SESSION_148 shipped M18.2 —** the
> retail/subprime archetype pack.
> `RetailSubprimeArchetypeBuilder.build()`
> now atomically constructs a coherent
> operational story across 20 vehicles, 4
> salespeople, 15 leads, 5 sales (1 BHPH
> firing M15 sync-sibling GL post), 3
> recon-in-progress vehicles with full
> ConditionReport + WorkOrder + Vendor +
> VehicleCost + stage progression, 2 sub-
> prime CreditApplications, and 1 follow-
> up cadence (auto-creating 3 tasks).
>
> **Three §0.a M18.2 decisions recorded:**
> (1) Chargeback deferred to M18.5 (~5
> more entities needed; better home in a
> dedicated F&I scenario brief). (2)
> Registry now seeds M13.1 default COA on
> both create + reset (M15 sale-booking
> requires it). (3) `_delete_demo_store_children`
> iterates carriers in reverse order
> (child-before-parent for PROTECT FKs)
> and deletes demo-owned Users so the
> next build doesn't collide on
> username unique constraint.
>
> **Backend baseline: 4,416 → 4,449
> pass** (+33 tests, 0 regressions).
> Frontend Vitest 140 (unchanged).
> Migrations 0043-0047 (unchanged).
> Tenancy carriers 50 (unchanged). DRF
> admin surface 107 (unchanged). Frontend
> operator routes 20 (unchanged).
> Permission classes 7 — **zero-drift
> streak eleven consecutive
> milestones** (M10 → M18.2). Celery-
> beat task families 10 (unchanged).
>
> **SESSION_149 opens M18.3 — floor-
> planned archetype pack.** Replace the
> stub in
> `services/demo_store/archetypes/floor_planned.py`
> with an atomic `build()` verb
> constructing a mid-size independent
> dealer story with auction floor-plan
> lender + outside-recon vendor
> relationships + a **documented
> recon-overrun scenario** for the recon-
> lead role.

## First thing SESSION_149 must do

### 1. Verify starting state

- `git status` — clean (M18.2 commit
  `a7eb65e` landed at SESSION_148 close).
- `git log --oneline -3` — top should be
  `a7eb65e` (M18.2 retail_subprime).
- `python3 manage.py test dealer_ai`
  → **4,449 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` → **140
  pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_18_PLANNING.md`
  §7 M18.3.
- `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`.
- `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
  (pattern template — floor_planned
  follows the same shape with different
  specs).
- `backend/dealer_ai/tests/test_m182_retail_subprime_archetype.py`
  (test template).
- `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
  §floor-planned patterns.
- `docs/research/RECON_MAPPING.md`
  §outside-recon workflows + overrun
  scenarios.

## What M18.3 delivers

Per `MILESTONE_18_PLANNING.md` §7 M18.3:

### Floor-planned archetype builder

Replace stub in
`services/demo_store/archetypes/floor_planned.py`
with `FloorPlannedArchetypeBuilder`
whose `build()` verb atomically
constructs:

- **~40 vehicles** ($12k-$35k; 2016-2022;
  Ford / Chevy / RAM / Toyota heavy;
  used + a few CPO simulations).
  Synthetic `DEMOFP`-prefixed VINs.
- **6 salespeople** (owner + sales
  manager + 4 advisors).
- **Sales pipeline**: ~25 active leads;
  ~10 recent Sales (mostly retail-
  finance; 1-2 cash).
- **Recon activity**: 5 in-recon
  vehicles including **1 with a
  documented $600+ recon overrun** —
  cost basis vs current recon spend
  should tell the operational story
  the recon-lead scenario brief will
  reference at M18.5 (WorkOrder
  authorized_cost vs actual_cost
  divergence).
- **Vendor relationships**: 4 active
  Vendors covering distinct
  categories (mechanical, body, glass,
  detail). Recent VendorCommunication
  rows on the vendor with the overrun
  scenario.
- **Follow-up cadences**: 3-4
  cadences with BeBack rows attached
  to some.

### Coherence contract enforcement

Same as M18.2: cross-domain integrity
across VehicleCost sums, stage
progression, credit-app references,
etc. **No random Faker-style
population.**

### `ScenarioSummary` return

Populate with the seeded stock numbers
+ user usernames + scenario brief
slugs (owner_capacity_check /
sales_manager_pipeline_review /
recon_lead_overrun_intervention /
office_accounting_close /
floor_plan_curtailment_review /
etc.).

### UI-correction discipline per §5.f

Fix UI defects only when they block a
scenario brief OR display materially
incorrect information. Every landed UI
correction commits with the scenario it
unblocks in the message.

### Focused tests (~15-20 target)

`tests/test_m183_floor_planned_archetype.py`
following the M18.2 test template:

- Row-count contract per specs.
- Cross-domain integrity (VehicleCost
  sums + stage progression +
  CreditApp references + Vendor reuse
  across work orders).
- **Recon overrun scenario visibility**:
  the target WorkOrder's `authorized_cost`
  vs `actual_cost` should show the
  $600+ divergence; the target
  vehicle's VehicleCost total should
  exceed its acquisition cost basis
  by the overrun amount.
- M15 sync-sibling GL posting fires
  for each Sale.
- Reset restores canonical starting
  state.
- `ScenarioSummary` shape.
- Synthetic-only data (VIN prefix,
  phone, email, name roster).

### Non-goals for M18.3

- ❌ No BHPH archetype (M18.4).
- ❌ No daily briefs (M18.5).
- ❌ No TesterFeedback POST endpoint
  (M18.5).
- ❌ No Chargeback substrate (deferred
  per §0.a M18.2 decision 1).
- ❌ No frontend changes.
- ❌ No new Celery-beat entries.
- ❌ No new permission classes.
- ❌ No new operator routes.

### Backend baseline target

**4,449 → ~4,464-4,484 pass** (+15-20
tests, 0 regressions). Frontend Vitest:
140 (unchanged).

## Explicit non-goals for SESSION_149

- ❌ Do NOT ship M18.4+ archetype packs
  in the same session.
- ❌ Do NOT modify M1-M17 business
  logic (except UI-correction discipline
  per §5.f Option A).
- ❌ Do NOT force-push or amend any
  earlier commits.

## NEXT TASK

Start SESSION_149 with (a) starting-
state verification, (b) reading M18
planning §7 M18.3 + M18.2 handoff +
retail_subprime.py as pattern
template, (c) building the floor-
planned archetype builder + tests.
Ship the M18.3 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
   (pattern template freshly shipped)
7. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
8. `docs/CAPABILITY_MATRIX.md` §7r
9. `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
   (M18.3 mirrors this shape with
   different specs)
10. `backend/dealer_ai/tests/test_m182_retail_subprime_archetype.py`
    (test template)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_148 — M18.2 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0047`. Test baseline:
  **4,449 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled task
  families**.
- **Milestones shipped:** M1 → M17. M18
  in progress: M18.0 planning + M18.1
  backend substrate + M18.2 retail/
  subprime archetype pack shipped. M18.3
  floor-planned archetype next
  (SESSION_149).
- **DRF admin surface:** **107**
  endpoints. Grows to 108 at M18.5
  (feedback POST).
- **Frontend operator routes:** **20**
  (unchanged through M18).
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) + five M11
  packages + seven M12 packages +
  `services/accounting/` (seven modules)
  + `services/demo_store/` (nine
  modules) with **RetailSubprimeArchetypeBuilder
  now fully implemented; two archetype
  stubs remain** (floor_planned +
  bhph).
- **Frontend accounting surface:**
  unchanged from M17.
- **Tenancy carriers:** **50**.
- **Permission classes:** **7 actual**
  — **zero-drift streak eleven
  consecutive milestones** (M10 → M18.2).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages
  (unchanged — M18 has no LLM path).
- **Deterministic rules:** unchanged.
- **Milestone 18 status:** M18.0
  planning + M18.1 substrate + M18.2
  retail/subprime archetype SHIPPED.
  **M18.3 floor-planned archetype next**
  (SESSION_149). M18.4 BHPH, M18.5
  briefs + feedback endpoint, M18.6
  close-out to follow.
