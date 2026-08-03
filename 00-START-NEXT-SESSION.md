---
state: active
date: 2026-08-03
last_session_shipped: SESSION_168
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
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: in-progress
next_session: SESSION_169
next_milestone: 21
next_milestone_name: "Operational Surface Completion"
next_increment: 3
next_increment_name: "M21.3 — Be-back CREATE + Follow-up cadence CONFIG + journey extensions"
---

# Next session — SESSION_169 · Milestone 21 · Increment 3 (M21.3 — Be-back CREATE + Follow-up cadence CONFIG)

> **Milestone 21.2 shipped at
> SESSION_168** — first M21 anchor
> implementation. Seven BHPH write
> endpoints now reachable through
> the operator UI (previously
> curl-only). Seven new components
> attached to
> `DealerAiBhphNoteDetail.tsx`;
> seven new `bhphApi.ts` write
> wrappers; extended seed with
> M21.2 fixtures; re-expanded
> acceptance journey covers all 7
> endpoints end-to-end.
>
> **Backend:** 4,755 → 4,758 pass.
> **Frontend Vitest:** 153 → 171
> pass (+18 new tests).
> **Acceptance suite:** 6 journeys
> (BHPH re-expanded from read-only
> to full write coverage; verified
> locally 7/7 pass).
>
> **SESSION_169 opens M21.3 — the
> second anchor implementation
> combined with the M21-conditional
> cadence-CONFIG scope.** Three
> endpoints across two feature
> areas: be-back CREATE (1) +
> follow-up cadence CONFIG (2).
> Combined into one increment per
> M21.0 §5.h Option B size
> discipline.

## First thing SESSION_169 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M21.2 commit.
- `python3 manage.py test dealer_ai`
  → **4,758 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **171 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Ship the missing `salesApi.ts` component consumers

The `createBeBack`, `createCadence`,
and `pauseCadence` wrappers already
exist in `frontend/src/lib/salesApi.ts`
— they're wrapper-only per the M21.1
audit. **This increment adds the
component-level consumers.**

**Attach location decision surfaces
at M21.3 open** (per §5.e Option C):

- `RecordBeBackForm` — attach to
  `DealerAiSalesBeBacks.tsx`
  (adjacent to the existing queue
  table + row actions). Fields:
  `lead_id` (numeric input or lead
  picker), `promised_at` (datetime),
  `promised_reason` enum, `notes`.
- `CreateCadenceForm` +
  `PauseCadenceButton` — attach to
  `DealerAiSalesFollowUps.tsx` in a
  new cadence-config panel, OR
  create an adjacent
  `DealerAiSalesCadences.tsx`
  page-embedded panel — decide at
  session open based on component
  fit.

Follow the M21.2 pattern: forms
under `frontend/src/components/sales/`
(or continue the `bhph/` pattern
scaled to sales); wire into the
target page with optimistic merges
into the returned projection.

### 3. Ship Vitest coverage

Same shape as M21.2 tests:
- Submit path (happy path posts
  correct payload).
- Validation path (required
  fields).
- Error path (backend 400 / 409
  / 404 rendered as human-readable
  messages).
- Button handler tests (confirm
  dialogs, disabled states).

Target Vitest baseline movement:
171 → ~183-188 (roughly +12-17
new tests for 3-4 new components).

### 4. Extend seed(s) + backend tests

Extend
`seed_journey_sales_manager_daily_startup`
to plant state supporting the
new UI:
- A candidate `Lead` for the be-
  back CREATE form (already
  seeded — verify).
- A cadence template for the
  pause action (if not already
  seeded — the seeded state may
  already include a cadence
  from prior increments; check
  first).
- A follow-up task in a state
  where the cadence pause is
  meaningful.

Backend tests: idempotency +
tenant scoping per the M20.2
seed test pattern.

**Decision at M21.3 open** (per
§5.e Option C): if cadence
config has a temporally-distinct
workflow, ship a NEW seed
command
`seed_journey_sales_manager_cadence_config`
+ a NEW journey. If cadence
lives naturally within daily-
startup, extend the existing
seed + journey.

### 5. Extend or add the acceptance journey

**Path A — Extend
`acceptance/journeys/sales_manager/daily_startup.spec.ts`.**
Add three sub-steps at the end
of the current journey:
- Record a be-back via form →
  assert new row appears.
- Create a cadence via form →
  assert cadence surfaces.
- Pause the seeded cadence via
  button → assert paused state.

**Path B — Add a new journey
file
`acceptance/journeys/sales_manager/cadence_config.spec.ts`.**
Preferred if the cadence-
management workflow is
temporally separate from daily
startup (e.g. weekly admin
task vs. morning triage).

Assertions target business
state via the M11.4 admin API
— not DOM state.

### 6. Ship the M21.3 handoff + refresh entry point

- `docs/handoffs/SESSION_169_m21_inc3_be_back_cadence.md`.
- Refresh
  `00-START-NEXT-SESSION.md`
  for SESSION_170 / M21.5
  close-out.
- **Do NOT push** — M21
  coordinated push happens at
  M21 close (SESSION_170) per
  M18.6 / M19.6 / M20.5.

## Non-goals for SESSION_169

- ❌ Do NOT modify any backend
  service verb — every M21.3
  UI attaches to an existing
  verb via an existing
  endpoint.
- ❌ Do NOT add or modify any
  DRF endpoint.
- ❌ Do NOT add new frontend
  routes. Attach to
  `DealerAiSalesBeBacks.tsx` +
  `DealerAiSalesFollowUps.tsx`
  (or attach cadence config
  in-place, no new route).
- ❌ Do NOT modify M1–M21.2
  shipped surface.
- ❌ Do NOT bundle any
  additional `defer-candidate-
  O2` scope items — M21.4 was
  skipped by scope-lock at
  §0.a M21.1.
- ❌ Do NOT force-push or
  amend earlier commits (M21
  coordinated push at close).

## Baseline expected at close

- **Backend:** ~4,770-4,780
  pass.
- **Frontend Vitest:** ~183-188
  pass.
- **Acceptance suite:** 6
  journeys (extended) or 7 (if
  cadence gets its own).
- **Migrations, tenancy,
  permissions, routes:**
  unchanged.

## NEXT TASK

Start SESSION_169 with (a)
starting-state verification, (b)
component-attachment location
decisions (be-back + cadence
config), (c) ship components +
wrappers-are-already-there
consumers, (d) Vitest coverage,
(e) seed extension + backend
tests, (f) journey extension or
addition, (g) ship the M21.3
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (active — §0.a M21.1 scope
   lock recorded)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
7. `docs/handoffs/SESSION_168_m21_inc2_bhph_write.md`
   (M21.2 shipped)
8. `docs/handoffs/SESSION_167_m21_inc1_audit.md`
9. `docs/CAPABILITY_MATRIX.md` §7u

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_168 — Milestone 21 · Increment 2 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,758 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 171 pass** (up from
  153 at M21.1 close; +18 M21.2
  component tests).
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational. **Six
  journeys** — BHPH re-expanded
  from M20.4 read-only to full
  write coverage; other five
  unchanged. M21.2 journey
  verified locally 7/7 pass
  (846ms).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`
  — last green run predates
  M21 commits (M20-close). M21
  coordinated push at M21
  close (SESSION_170) will
  trigger the first M21 CI
  run.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M20**. **M21 in progress
  (M21.0 + M21.1 + M21.2
  shipped locally).**
- **DRF admin surface:** 113
  endpoints (unchanged — M21.2
  adds zero endpoints).
- **Frontend operator routes:**
  20 (unchanged — M21.2 attaches
  in-place to
  `DealerAiBhphNoteDetail.tsx`).
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M20 packages unchanged.
  M21 adds zero service verbs.
- **Frontend surfaces:** M12.7
  collector dashboard now
  extended with write-side
  panels (7 new components
  under
  `frontend/src/components/bhph/`).
- **Tenancy carriers:** 52
  (unchanged).
- **Permission classes:** 7
  actual — zero-drift streak
  twenty consecutive milestones
  (M10 → M20). M21 targets
  extension to twenty-one at
  close.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 21 status:** IN
  PROGRESS. M21.0 (planning) +
  M21.1 (audit + scope lock) +
  M21.2 (BHPH write-side UI +
  journey extension) shipped
  locally. Three commits ahead
  of `origin/main`; coordinated
  push at M21.5 close per
  M18/M19/M20 cadence.
- **Audit tooling:**
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  operator-invoked. Rerun after
  M21.3 to reflect further
  coverage gains (be-back +
  cadence config transitioning
  from `wrapper-only` to
  `covered`).
- **Planning-time streak:**
  **87 as-recommended M5.1 →
  M21.0** across twelve
  consecutive milestones (M10 →
  M21). No new §5 decisions in
  M21.2 or M21.3 (execution
  sessions); streak preserved.
- **DoD amendment (formalized
  at M21.0 §5.f Option B):**
  every future customer-facing
  milestone must add or update
  at least one Playwright
  operational journey, or
  explicitly document in §3 why
  no journey change is
  required. M21.2 satisfies via
  the re-expanded BHPH
  collections journey.
- **Governing contract
  (Candidate O):** every M21
  shipped surface maps to an
  already-shipped backend
  capability, closes a missing
  operator-facing UI, adds or
  extends a Playwright
  operational journey, and is
  not generic UX polish.
