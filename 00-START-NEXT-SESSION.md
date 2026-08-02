---
state: active
date: 2026-08-02
last_session_shipped: SESSION_147
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
next_session: SESSION_148
next_milestone: 18
next_milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
next_increment: 2
next_increment_name: "M18.2 — Retail/subprime archetype pack"
---

# Next session — SESSION_148 · Milestone 18 · Increment 2 (M18.2 — Retail/subprime archetype pack)

> **SESSION_147 shipped M18.1 —** backend
> substrate. Migration `0047`
> (`Dealership.is_demo` +
> `demo_archetype` + `TesterFeedback`).
> New `services/demo_store/` package
> (nine modules) with belt-and-suspenders
> guards + synthetic-data helpers +
> outbound-send-boundary toolkit +
> archetype dispatcher + stubs. New
> `demo_store` management command. Test
> helper `make_demo_dealership`. 53
> focused tests including the outbound-
> egress scanner test. **§0.a M18.1
> decision 1 recorded** — outbound-send-
> boundary enumeration revealed the
> preliminary list was aspirational; only
> the two LLM providers currently egress
> and are on a documented allowlist.
> Demo-aware LLM router deferred.
>
> **Backend baseline: 4,363 → 4,416
> pass** (+53 tests, 0 regressions).
> **Frontend Vitest baseline: 140 pass**
> (unchanged — no frontend at M18.1).
> Migrations `0043`–`0047` (+1 at M18.1).
> Tenancy carriers 49 → **50**
> (TesterFeedback). DRF admin surface
> 107 (unchanged — feedback POST lands
> at M18.5). Frontend operator routes
> 20 (unchanged — M18 introduces zero
> new operator routes per §5.f + Q7).
> Permission classes 7 — **zero-drift
> streak now ten consecutive
> milestones** (M10 → M18.1). Celery-
> beat task families 10 (unchanged —
> no beat entry at M18).
>
> **SESSION_148 opens M18.2 — retail/
> subprime archetype pack.** Replace the
> M18.1 stub in
> `services/demo_store/archetypes/retail_subprime.py`
> with an atomic `build()` verb that
> constructs a coherent operational story
> across the shipped M1-M17 surface.

## First thing SESSION_148 must do

### 1. Verify starting state

- `git status` — clean (M18.1 commit
  `fe9a19a` landed at SESSION_147 close).
- `git log --oneline -3` — top should be
  `fe9a19a` (M18.1 substrate).
- `python3 manage.py test dealer_ai`
  → **4,416 pass, 1 skipped, 0 fail**.
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
  §7 M18.2 (retail/subprime scope) +
  §Store-story coherence (the
  operational-story contract).
- `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
  (substrate freshly shipped).
- `docs/research/INDEPENDENT_DEALER_PIVOT.md`
  (retail/subprime persona shape).
- `docs/research/SALES_DEPARTMENT_MAPPING.md`
  §retail + subprime motion.
- `backend/dealer_ai/services/demo_store/`
  (substrate the archetype builds on).
- `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
  (the stub file to replace).

## What M18.2 delivers

Per `MILESTONE_18_PLANNING.md` §7 M18.2:

### Retail/subprime archetype builder

Replace the stub in
`services/demo_store/archetypes/retail_subprime.py`
with a `RetailSubprimeArchetypeBuilder`
whose `build(dealership)` verb atomically
constructs a coherent operational story:

- **~20 vehicles** (used only; $8k-$18k
  price band; 2013-2019 model years;
  mixed makes appropriate to a small
  used-car lot). Use `synthetic_vin(archetype,
  index)` for VINs.
- **4 salespeople** (sales manager +
  3 advisors) with `synthetic_email` +
  `synthetic_phone` per §5.g.
- **Sales pipeline**: ~15 active leads
  across pipeline stages; ~5 recent
  Sales (cash + retail-finance mix); 1
  BHPH Sale that exercises the M15
  sync-sibling GL post (verifies the
  demo store's accounting activity
  reads correctly).
- **Recon activity**: 3 in-recon
  vehicles with:
  - VehicleCost history (parts + labor
    + sub-vendor invoices);
  - ConditionReport + ConditionFinding
    rows tied to pre-recon inspection;
  - WorkOrder + WorkOrderPart +
    WorkOrderFinding rows tying
    findings to remediation.
- **F&I**: 2 recent CreditApplication
  rows with sub-prime lender routing;
  1 Chargeback for M18 audit
  visibility.
- **Follow-up cadences**: 4 scheduled
  FollowUpTask rows. These are
  surfaced-only per M11.4 posture —
  no outbound send infrastructure to
  guard against yet.

### Coherence contract enforcement

Per `MILESTONE_18_PLANNING.md` §1 Q6 +
§Store-story coherence: the seeded
records must tell connected operational
stories. Every seeded Sale's
`total_investment` must reconcile with
its VehicleCost sums; every recon-in-
progress vehicle's Stage progression
must be self-consistent with its
WorkOrder timeline; every
CreditApplication must reference the
Sale it belongs to. **Random Faker-
style row population is prohibited.**

### `ScenarioSummary` return

Populate the returned `ScenarioSummary`
with the seeded stock numbers + user
usernames + scenario brief slugs (for
M18.5 briefs to reference).

### UI-correction discipline per §5.f

Fix UI defects only when they block a
scenario brief from completing end-to-
end via normal product routes OR
display materially incorrect information.
Everything else records via
`TesterFeedback` for a later dedicated
UX-polish milestone. Every landed UI
correction commits with the specific
scenario brief it unblocks in the
commit message.

### Focused tests (~15-20 target)

`tests/test_m182_retail_subprime_archetype.py`:

- Builder produces the documented row
  counts (~20 vehicles, 4 salespeople,
  ~15 leads, ~5 sales, 3 recon-in-
  progress, 2 credit apps, 1 chargeback,
  4 follow-ups).
- Cross-domain integrity: VehicleCost
  sums reconcile with Sale
  `total_investment`; VehicleStageEvent
  progression is self-consistent;
  CreditApplication references a Sale.
- GL entries: seeded Sale rows fire
  M15 sync-sibling; frozen trial-
  balance reflects the archetype's
  aggregate activity.
- Reset via `reset_demo_store()`
  restores the canonical starting
  state (row counts + specific stock
  numbers stable).
- `ScenarioSummary` contract: fields
  populated per §5.d Option A shape.
- Synthetic-data-only: no seeded row
  has a real-format VIN /
  real-routable phone / real-domain
  email.

### Non-goals for M18.2

- ❌ No floor-planned archetype (M18.3).
- ❌ No BHPH archetype (M18.4).
- ❌ No daily briefs (M18.5).
- ❌ No TesterFeedback POST endpoint
  (M18.5).
- ❌ No frontend changes.
- ❌ No new Celery-beat entries.
- ❌ No new permission classes.
- ❌ No new operator routes.

### Backend baseline target

**4,416 → ~4,431-4,436 pass** (+15-20
tests, 0 regressions). Frontend Vitest:
140 (unchanged).

## Explicit non-goals for SESSION_148

- ❌ Do NOT ship M18.3+ archetype packs
  in the same session.
- ❌ Do NOT modify M1-M17 business
  logic (except UI-correction discipline
  per §5.f Option A).
- ❌ Do NOT force-push or amend any
  earlier commits.

## NEXT TASK

Start SESSION_148 with (a) starting-
state verification, (b) reading M18
planning §7 M18.2 + M18.1 substrate
handoff + persona research, (c) building
the retail/subprime archetype builder +
tests. Ship the M18.2 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
   (substrate freshly shipped)
7. `docs/handoffs/SESSION_146_m18_inc0_planning.md`
   (M18.0 planning close)
8. `docs/CAPABILITY_MATRIX.md` §7r
9. `backend/dealer_ai/services/demo_store/`
   (the substrate the archetype consumes)
10. `docs/research/INDEPENDENT_DEALER_PIVOT.md`
    +
    `docs/research/SALES_DEPARTMENT_MAPPING.md`
    (persona shape)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_147 — M18.1 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0047`. Test baseline:
  **4,416 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled task
  families registered**. Next open slot for
  a future detector is 12:00.
- **Milestones shipped:** M1 → M17. M18 in
  progress: M18.0 planning + M18.1 backend
  substrate shipped at SESSION_146 +
  SESSION_147. M18.2 retail/subprime
  archetype next (SESSION_148).
- **DRF admin surface:** **107** endpoints.
  Grows to 108 at M18.5 (feedback POST).
- **Frontend operator routes:** **20** —
  remains unchanged through M18 per §5.f +
  Q7.
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) + five M11
  packages + seven M12 packages +
  `services/accounting/` (seven modules) +
  **`services/demo_store/` (nine modules)**
  new at M18.1.
- **Frontend accounting surface:**
  `frontend/src/lib/accountingApi.ts` with
  8 fetchers + 2 mutators + four page
  components + `TrialBalanceDatePicker`
  component.
- **Tenancy carriers:** **50** (49 → 50
  at M18.1: TesterFeedback).
- **Permission classes:** **7 actual** —
  **zero-drift streak ten consecutive
  milestones** (M10 → M18.1).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages
  (unchanged — M18 has no LLM path).
- **Deterministic rules:** unchanged.
- **Milestone 18 status:** M18.0 planning
  + M18.1 substrate SHIPPED. **M18.2
  retail/subprime archetype next**
  (SESSION_148). M18.3 floor-planned,
  M18.4 BHPH, M18.5 briefs + feedback
  endpoint, M18.6 close-out to follow.
