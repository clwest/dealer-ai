---
state: active
date: 2026-08-02
last_session_shipped: SESSION_149
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
next_session: SESSION_150
next_milestone: 18
next_milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
next_increment: 4
next_increment_name: "M18.4 — BHPH archetype pack"
---

# Next session — SESSION_150 · Milestone 18 · Increment 4 (M18.4 — BHPH archetype pack)

> **SESSION_149 shipped M18.3 —** the
> floor-planned archetype pack.
> `FloorPlannedArchetypeBuilder.build()`
> now atomically constructs 40 vehicles
> + 6 salespeople + 25 leads + 10 sales
> (all firing M15 sync-sibling GL post)
> + 5 recon-in-progress vehicles
> including **the documented $825 recon
> overrun anchor** (WorkOrder
> authorized_cost=$600 vs actual_cost=
> $1,425 + VendorCommunication history
> documenting the escalation) + 4
> shared Vendors + 3 CreditApplications
> + 3 FollowUpCadences (7+ tasks) + 3
> BeBacks.
>
> **§0.a M18.2 decision 1 continues to
> apply** — Chargeback still deferred
> to M18.5.
>
> **Backend baseline: 4,449 → 4,483
> pass** (+34 tests, 0 regressions).
> Frontend Vitest 140 (unchanged).
> Migrations 0043-0047 (unchanged).
> Tenancy carriers 50 (unchanged). DRF
> admin surface 107 (unchanged).
> Frontend operator routes 20
> (unchanged). Permission classes 7 —
> **zero-drift streak twelve
> consecutive milestones** (M10 →
> M18.3). Celery-beat task families 10
> (unchanged).
>
> **SESSION_150 opens M18.4 — BHPH
> archetype pack.** Replace the stub
> in
> `services/demo_store/archetypes/bhph.py`
> with an atomic `build()` verb
> constructing a small BHPH
> dealership with an active portfolio
> of ~30 notes, ~150 payment history,
> promise-to-pay + collection-
> contact + repossession rows, all
> synthetic-safe.

## First thing SESSION_150 must do

### 1. Verify starting state

- `git status` — clean (M18.3 commit
  `aa6343f` landed at SESSION_149
  close).
- `git log --oneline -3` — top
  should be `aa6343f` (M18.3
  floor_planned) preceded by the
  M18.3 docs (not yet committed —
  land in the M18.3 handoff
  commit).
- `python3 manage.py test dealer_ai`
  → **4,483 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **140 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_18_PLANNING.md`
  §7 M18.4.
- `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`.
- `backend/dealer_ai/services/demo_store/archetypes/floor_planned.py`
  (pattern template).
- `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
  (M12 BhphNote origination reference).
- `docs/research/BHPH_OPERATIONS_MAPPING.md`
  §portfolio operations + payment
  frequency + collection workflow.

## What M18.4 delivers

Per `MILESTONE_18_PLANNING.md` §7 M18.4:

### BHPH archetype builder

Replace stub in
`services/demo_store/archetypes/bhph.py`
with `BhphArchetypeBuilder` whose
`build()` verb atomically constructs:

- **~25 vehicles** ($4k-$12k; used
  only; 2010-2017; higher mileage,
  reliable transportation). Synthetic
  `DEMOBH`-prefixed VINs.
- **4 salespeople** (owner + sales
  manager + 2 collectors).
- **BHPH portfolio (~30 active
  notes):**
  - BhphNotes across aging buckets
    (fresh, current, 30-day past-
    due, 60-day past-due) using
    weekly + biweekly payment
    frequencies.
  - **~150 BhphPayment rows** —
    historical + recent. Recent
    payments (paid within the last
    24 hours) will be picked up by
    the M16 detector at 11:00 project-
    time daily so the trial-balance
    surface reads correctly.
  - **3 BhphPromiseToPay** rows in
    various states (promised /
    kept / broken).
  - **5 CollectionContact** records
    across channels.
  - **1 Repossession** (recovered
    state).
- **Sales pipeline**: ~10 active
  leads; ~5 recent BHPH Sales
  (exercising M12.1 note origination
  + M15 sync-sibling GL post).
- **Follow-up cadences** on some
  leads.

### Coherence contract enforcement

Same as M18.2 / M18.3: cross-domain
integrity — every BhphNote origins
from a BHPH Sale; payment history
sums reconcile with note balances;
promise-to-pay states are
internally consistent. **No random
Faker-style population.**

### `ScenarioSummary` return

Populate with seeded stock numbers +
user usernames + scenario brief
slugs (`bhph_collector_daily_book` /
`bhph_promise_followup` /
`owner_portfolio_health` /
`office_accounting_close` /
`repo_intake_handoff` /
`nsf_response_workflow`).

### UI-correction discipline per §5.f

Fix UI defects only when they block
a scenario brief OR display
materially incorrect information.
Every landed correction commits
with the specific scenario in the
message.

### Focused tests (~15-20 target)

`tests/test_m184_bhph_archetype.py`
following the M18.3 template:

- Row-count contract per specs.
- Cross-domain integrity: every
  BhphNote origins from a BHPH
  Sale; payment allocation sums
  reconcile; promise-to-pay states
  consistent; Repossession
  references a BhphNote.
- **M16 detector eligibility**:
  recent payments (paid_at within
  last 24h) have `posted_at=NULL`
  so the M16.1 11:00 detector
  picks them up on next run;
  historical payments have
  `posted_at` populated.
- M15 sync-sibling GL post fires
  for each BHPH Sale.
- Reset restores canonical state.
- ScenarioSummary shape.
- Synthetic-only data
  (`DEMOBH` VIN, `555-01` phones,
  `.example` emails).

### Non-goals for M18.4

- ❌ No daily briefs (M18.5).
- ❌ No TesterFeedback POST endpoint
  (M18.5).
- ❌ No Chargeback substrate (still
  deferred per §0.a M18.2 decision
  1).
- ❌ No frontend changes.
- ❌ No new Celery-beat entries.
- ❌ No new permission classes.
- ❌ No new operator routes.

### Backend baseline target

**4,483 → ~4,498-4,518 pass** (+15-
20 tests, 0 regressions).

## Explicit non-goals for SESSION_150

- ❌ Do NOT ship M18.5+ code in the
  same session.
- ❌ Do NOT modify M1-M17 business
  logic (except UI-correction
  discipline per §5.f).
- ❌ Do NOT force-push or amend any
  earlier commits.

## NEXT TASK

Start SESSION_150 with (a) starting-
state verification, (b) reading
M18.4 scope + floor_planned pattern
template + retail_subprime BHPH
reference, (c) building the BHPH
archetype builder + tests. Ship the
M18.4 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`
   (pattern template freshly shipped)
7. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
   (BHPH sale reference)
8. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
9. `docs/CAPABILITY_MATRIX.md` §7r
10. `docs/research/BHPH_OPERATIONS_MAPPING.md`
    §portfolio operations + payment
    rhythm

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_149 — M18.3 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0047`. Test baseline:
  **4,483 pass**, 1 skipped, 0 fail.
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
  in progress: M18.0 + M18.1 + M18.2 +
  M18.3 shipped. **M18.4 BHPH archetype
  next** (SESSION_150).
- **DRF admin surface:** **107**.
- **Frontend operator routes:** **20**.
- **Public endpoints:** +1 M6.5 showroom.
- **Service surface:** complete
  `services/f_and_i/` (M10) + five M11 +
  seven M12 + `services/accounting/`
  (seven) + `services/demo_store/`
  (nine) with **retail_subprime +
  floor_planned archetypes fully
  implemented; bhph is the last
  remaining stub**.
- **Tenancy carriers:** **50**.
- **Permission classes:** **7 actual**
  — **zero-drift streak twelve
  consecutive milestones** (M10 →
  M18.3).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages
  (unchanged — M18 has no LLM path).
- **Deterministic rules:** unchanged.
- **Milestone 18 status:** M18.0
  planning + M18.1 substrate + M18.2
  retail/subprime + M18.3 floor-planned
  SHIPPED. **M18.4 BHPH next**
  (SESSION_150). M18.5 briefs +
  feedback endpoint, M18.6 close-out
  to follow.
