---
state: active
date: 2026-08-02
last_session_shipped: SESSION_161
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
milestone_20_status: in-progress
next_session: SESSION_162
next_milestone: 20
next_milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
next_increment: 2
next_increment_name: "M20.2 — Owner morning review + sales manager daily startup journeys"
---

# Next session — SESSION_162 · Milestone 20 · Increment 2 (M20.2 — owner morning review + sales manager daily startup)

> **M20.1 shipped at SESSION_161.**
> Top-level `acceptance/` workspace
> stood up with Playwright 1.49 +
> TypeScript 5.6; support layer (auth
> setup via real UI, seed invocation,
> business-outcome assertions);
> `seed_journey_pilot_onboarding`
> management command (+15 backend
> tests, all green); canonical pilot
> onboarding journey spec tagged
> `@pilot-critical`; new GitHub
> Actions `acceptance` workflow with
> tiered execution (pilot-critical on
> PR, full suite on `main`). Settings
> extended with `M20_ACCEPTANCE_DB=1`
> branch for isolated SQLite test DB
> at `backend/db.acceptance.sqlite3`
> (gitignored, matches M2.1
> migration_check pattern).
>
> **Backend baseline:** 4,679 →
> **4,694 pass** (+15). Frontend
> Vitest: **153 pass** (unchanged).
> Zero drift on migrations (0048),
> tenancy carriers (52), permission
> classes (7 — zero-drift streak
> intact at nineteen), DRF admin
> (113), frontend routes (20).
>
> **SESSION_162 opens M20.2** — two
> dashboard-centric journeys sharing
> fixtures. Owner morning review
> tagged `@pilot-critical`; sales
> manager daily startup unaugmented
> (runs only in full-suite CI on
> `main`).
>
> **Guiding principle stays in
> effect.** The Playwright suite is
> an operational acceptance contract,
> not a UI automation project. Every
> journey validates business outcomes
> through the real application using
> deterministic seeded state.

## First thing SESSION_162 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top should
  be the M20.1 shipped commit.
- `python3 manage.py test dealer_ai`
  → **4,694 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. First-time M20.1 acceptance dry-run (recommended)

Before layering M20.2 journeys, run
the M20.1 canonical journey once
locally to confirm the framework is
green:

```bash
cd acceptance
npm install
npx playwright install chromium
npm run test:pilot-critical
```

If the run fails, resolve before
proceeding — do NOT layer M20.2 on
top of a broken framework. Any
selector-stability issues surfaced
by the first run should be resolved
either in the journey spec (if the
selector was wrong) or in the
frontend (if the selector is
missing or unstable) with a §0.a
amendment.

### 3. Add M20.2 personas

Extend `acceptance/support/auth/personas.ts`
with two new personas:

- `owner` — dealer-owner role at the
  default demo dealership (uses M18
  demo seed).
- `sales_manager` — sales-manager
  role at the default demo
  dealership.

Add new project entries to
`playwright.config.ts` per persona,
each depending on the `setup`
project (which extends the auth
setup to include the two new
personas).

### 4. Ship the two seed delta commands

Per `MILESTONE_20_PLANNING.md` §7
M20.2:

- `dealer_ai/management/commands/seed_journey_owner_morning_review.py`
  — idempotent seed of an overnight
  lead + a scheduled showing + one
  contract in the pipeline for the
  demo dealership.
- `dealer_ai/management/commands/seed_journey_sales_manager_daily_startup.py`
  — three overnight leads +
  assigned advisor queue + a
  be-back due today.

Compose existing service verbs; no
parallel write paths. Idempotent
via stable identifiers. Match the
M20.1 seed's `--reset` posture.

### 5. Ship the two journey specs

- `acceptance/journeys/owner/morning_review.spec.ts`
  — tagged `@pilot-critical`.
  Owner lands on the dashboard,
  scans yesterday's pipeline +
  realized gross + upcoming
  showings, drills into the top
  lead. Business-outcome
  assertions target the dashboard
  aggregators + lead detail
  service state, not DOM state.
- `acceptance/journeys/sales_manager/daily_startup.spec.ts`
  — sales manager reviews overnight
  leads, assigns to advisors,
  checks the follow-up cadence
  queue, marks a be-back handled.
  Business-outcome assertions
  target assignment state + queue
  state.

### 6. Extend the assertion helpers

Add `acceptance/support/assertions/dashboard.ts`
(or similar) with helpers for the
new business outcomes (lead
assignment, cadence queue state,
be-back handling).

### 7. Backend tests + verification

- Add ~10 backend tests covering
  the two new seed delta commands
  (fresh-run + idempotency + reset
  + tenant scoping).
- Backend baseline target: 4,694 →
  ~4,704.
- Frontend Vitest: 153 (unchanged).

### 8. Ship the M20.2 handoff

- `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`.
- Coordinated commit per M19.1 /
  M20.1 pattern.

## Non-goals for SESSION_162

- ❌ Do NOT modify any existing
  backend service verb, endpoint,
  or migration.
- ❌ Do NOT modify any existing
  frontend route or component
  (except selector-stability fixes
  surfaced by the first M20.1
  dry-run — record as §0.a).
- ❌ Do NOT add screenshot
  comparison or pixel-perfect
  visual regression.
- ❌ Do NOT ship journeys beyond
  the two M20.2 targets — recon
  + office/accounting are M20.3;
  BHPH collections is M20.4.
- ❌ Do NOT force-push or amend
  earlier commits.

## Baseline expected at close

- **Backend:** 4,694 → ~4,704 pass
  (M20.2 seed command tests).
- **Frontend Vitest:** 153
  (unchanged).
- **Migrations:** unchanged
  `0001`–`0048`.
- **Tenancy carriers:** unchanged at
  52.
- **Permission classes:** unchanged
  at 7 (zero-drift streak still
  intact at nineteen; extends to
  twenty at M20.5 close).
- **DRF admin surface:** unchanged
  at 113.
- **Frontend operator routes:**
  unchanged at 20.
- **Acceptance suite:** **3
  journeys** (pilot onboarding +
  owner morning review + sales
  manager daily startup). Pilot-
  critical subset: **2** (pilot
  onboarding + owner morning
  review).

## NEXT TASK

Start SESSION_162 with (a) starting-
state verification, (b) first-time
M20.1 dry-run locally to confirm
framework green, (c) extend
personas + auth setup with `owner`
+ `sales_manager`, (d) ship two
seed delta commands + backend
tests, (e) ship two journey specs,
(f) extend assertion helpers, (g)
ship the M20.2 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (this milestone's active memo)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin)
7. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface — the
   substrate M20 validates)
8. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
   (M20.1 shipped)
9. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
   (M20.0 planning close)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_161 — M20.1 shipped)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0048`.
  Test baseline: **4,694 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):**
  STOOD UP. `acceptance/` with
  Playwright 1.49 + TS 5.6.
  Support layer + one journey
  (pilot onboarding) + one seed
  delta command shipped. First
  local run pending SESSION_162.
- **Acceptance (CI):** WIRED. New
  `.github/workflows/acceptance.yml`
  triggers on PR + `main` push;
  pilot-critical subset on PR, full
  suite on `main`. First actual run
  happens on next push.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled
  task families registered**.
- **Milestones shipped:** M1 →
  **M19**. M20 in-progress (M20.0
  + M20.1 shipped; M20.2–M20.5
  pending).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all M1–M19
  packages unchanged. M20 adds no
  service verbs. New management
  command
  `seed_journey_pilot_onboarding`.
- **Frontend surfaces:** unchanged
  since M19.4.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **nineteen consecutive
  milestones** (M10 → M19.5).
  Extends to **twenty** at M20.5
  close.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 20 status:** IN
  PROGRESS. M20.0 planning + M20.1
  framework substrate + canonical
  journey shipped. Four increments
  remaining (M20.2–M20.5) per §7
  sequencing.
- **Planning-time streak:** **86
  as-recommended M5.1 → M20.0**
  across eleven consecutive
  milestones.
- **Acceptance-suite journeys:** 1
  authored (pilot onboarding,
  tagged `@pilot-critical`). Full
  local + CI green pending
  SESSION_162 dry-run + first CI
  push.
- **Guiding principle for M20
  implementation:** business
  outcomes through real UI on
  deterministic seeded state; not
  UI automation.
