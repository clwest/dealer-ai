---
state: active
date: 2026-08-02
last_session_shipped: SESSION_160
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
next_session: SESSION_161
next_milestone: 20
next_milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
next_increment: 1
next_increment_name: "M20.1 — Framework substrate + canonical pilot onboarding journey"
---

# Next session — SESSION_161 · Milestone 20 · Increment 1 (M20.1 — framework substrate + canonical pilot onboarding journey)

> **Milestone 20 opened at SESSION_160.**
> Target selection ratified against the
> nine-candidate list from M19
> retrospective §9. **§5.a Candidate J
> confirmed** — Operational Journey
> Validation via Playwright acceptance
> testing, upgraded scope. User-
> proposed **Candidate W folded into
> Candidate J** per DOC_GOVERNANCE.md §2
> (prefer updating authoritative
> documents over creating parallel
> versions); J's authoritative brief
> upgraded with W's explicit non-goals
> + why-M20 rationale + per-journey
> operational contract. Milestone name:
> **"Operational Journey Validation
> (Playwright acceptance testing)."**
>
> **§5.b–§5.h all confirmed as-
> recommended.** Playwright +
> `@playwright/test` + TypeScript; top-
> level `acceptance/` workspace with
> its own `package.json`; reuse of the
> M18/M19 seed substrate with
> idempotent per-journey delta seed
> commands; storage-state authentication
> fixtures generated through the real
> UI; Playwright-managed backend/
> frontend lifecycle via `webServer`;
> dedicated GitHub Actions acceptance
> job with pilot-critical vs full-suite
> tiering + artifact capture; increment
> sequencing Option C (framework +
> canonical journey in M20.1, journeys
> 2-per-increment thereafter).
>
> **Planning-time as-recommended streak
> extends 85 → 86** across eleven
> consecutive milestones (M10 → M20).
>
> **Guiding principle established.** The
> Playwright suite is an operational
> acceptance contract, not a UI
> automation project. Every journey
> validates business outcomes through
> the real application using
> deterministic seeded state. If a
> journey passes, the conclusion is
> that a dealership employee can
> successfully perform that operational
> workflow — not merely that buttons
> were clicked successfully. **Governs
> every M20 implementation-time
> decision.**

## First thing SESSION_161 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top should
  be the M20.0 close-out commit.
- `python3 manage.py test dealer_ai`
  → **4,679 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Scaffold the `acceptance/` workspace

Per `MILESTONE_20_PLANNING.md` §7
M20.1:

- New top-level `acceptance/`
  directory sibling to `backend/` and
  `frontend/`.
- `acceptance/package.json` with
  `@playwright/test` + TypeScript
  devDeps only (isolated from
  frontend runtime bundle).
- `acceptance/playwright.config.ts`
  with:
  - `webServer` array for backend
    (`cd ../backend && python3
    manage.py runserver 0.0.0.0:8101`
    against a dedicated test DB) +
    frontend (`vite preview` in CI,
    `vite dev` locally).
  - `reuseExistingServer: true`
    locally; `false` in CI.
  - Project definitions: `setup`
    (auth setup project) + one per
    persona (`owner`,
    `sales_manager`, `advisor`,
    `recon_manager`,
    `office_manager`,
    `bhph_collector`,
    `platform_operator`).
  - Reporter config: HTML
    (always) + list.
  - Artifact config: `trace:
    'on-first-retry'`, `video:
    'retain-on-failure'`,
    `screenshot: 'only-on-failure'`.
  - Tag filter support for
    `@pilot-critical`.
- `acceptance/tsconfig.json`
  mirroring frontend TS conventions
  where applicable.
- `acceptance/.gitignore` covering
  `.auth/`, `playwright-report/`,
  `test-results/`, `node_modules/`.
- `acceptance/README.md` — one-page
  contributor onboarding.

### 3. Build the support layer

- `acceptance/support/auth/` — auth
  setup project logs each persona in
  via the real UI, saves storage
  state to
  `acceptance/.auth/{persona}.json`.
- `acceptance/support/seed/` —
  helper to invoke a Django
  management command from a
  Playwright test (spawn `python3
  manage.py <cmd>` against the test
  DB, propagate stdout/stderr on
  failure).
- `acceptance/support/assertions/`
  — first business-outcome
  assertion helpers used by the
  pilot onboarding journey (assert
  prospect state transition,
  checklist step completion,
  dealership `is_ready` flag).

### 4. Ship the canonical pilot onboarding journey

- `dealer_ai/management/commands/seed_journey_pilot_onboarding.py`
  — idempotent seed of a `qualified`
  `PilotProspect` ready to convert.
  Composes existing service verbs
  (no parallel write paths).
  ~5–10 focused backend tests
  covering idempotency + tenant
  scoping.
- `acceptance/journeys/pilot/onboarding.spec.ts`
  — canonical journey walking the
  M19.4 pilot admin surface end-to-
  end:
  1. Operator navigates to the M19.4
     pilot admin section.
  2. Selects the seeded prospect.
  3. Converts prospect →
     dealership via the admin form.
  4. Advances the checklist steps
     through `readiness_confirmed`.
  5. Journey asserts business
     outcomes at each step (prospect
     state transitions, checklist
     step completions, dealership
     `is_ready=True` at the end).
  Tagged `@pilot-critical`.

### 5. Wire up CI

- `.github/workflows/acceptance.yml`
  — new job triggered on
  `pull_request` + `push` to `main`.
- Installs Node + Python + Chromium.
- Runs the M18 + M19 seed commands
  against the test DB.
- Runs Playwright with tag filter:
  `--grep '@pilot-critical'` on PR;
  no filter on `main`.
- Uploads HTML report + traces +
  videos on failure.

### 6. Ship the M20.1 handoff

- `docs/handoffs/SESSION_161_m20_inc1_framework.md`.
- Coordinated commit per M19.1 /
  M18.1 pattern.

## Non-goals for SESSION_161

- ❌ Do NOT ship any journey beyond
  the canonical pilot onboarding
  journey — M20.2–M20.4 land the
  other five.
- ❌ Do NOT modify any existing
  backend service verb, endpoint,
  or migration.
- ❌ Do NOT modify any existing
  frontend route or component
  (except in the rare case where
  the canonical journey exposes a
  selector-stability defect that
  must be fixed to write a durable
  assertion — surface as §0.a).
- ❌ Do NOT introduce Docker /
  Docker Compose.
- ❌ Do NOT add screenshot
  comparison or pixel-perfect
  visual regression.
- ❌ Do NOT force-push or amend
  earlier commits.

## Baseline expected at close

- **Backend:** 4,679 →
  ~4,684–4,689 pass (delta command
  tests).
- **Frontend Vitest:** 153
  (unchanged).
- **Migrations:** unchanged
  `0001`–`0048`.
- **Tenancy carriers:** unchanged at
  52.
- **Permission classes:** unchanged
  at 7 (zero-drift streak still
  intact at nineteen consecutive
  milestones; extends to twenty at
  M20.5 close).
- **DRF admin surface:** unchanged
  at 113.
- **Frontend operator routes:**
  unchanged at 20.
- **Acceptance suite:** **1
  journey passing on `main` CI +
  PR (pilot onboarding, tagged
  `@pilot-critical`).**

## NEXT TASK

Start SESSION_161 with (a) starting-
state verification, (b) scaffold the
top-level `acceptance/` workspace
with Playwright config +
tsconfig + gitignore + README, (c)
build the support layer (auth
setup, seed invocation, business-
outcome assertions), (d) ship the
canonical pilot onboarding journey
+ its seed delta command + backend
tests, (e) wire the GitHub Actions
acceptance job with pilot-critical
tag filter, (f) ship the M20.1
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (this milestone's active memo)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin — the
   authoritative brief M20 upgraded)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 + §9 (accounting slot
   preserved as M21 standing
   question)
8. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface — the
   substrate M20 validates)
9. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
   (this milestone's planning
   handoff)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_160 — Milestone 20 opened at planning)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0048`.
  Test baseline: **4,679 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance (local):** NOT YET
  SCAFFOLDED. M20.1 scaffolds the
  workspace + ships the canonical
  pilot onboarding journey.
- **Acceptance (CI):** NOT YET
  WIRED. M20.1 adds the GitHub
  Actions job.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled
  task families registered**.
- **Milestones shipped:** M1 →
  **M19**. M20 in-progress (M20.0
  planning shipped; M20.1–M20.5
  pending).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** complete
  `services/f_and_i/` (M10) + five
  M11 packages + seven M12 packages
  + `services/accounting/` (seven
  modules) + `services/demo_store/`
  (ten modules) +
  `services/pilot_onboarding/` (six
  modules). No M20 service surface
  changes.
- **Frontend surfaces:**
  `<PilotOnboardingSection>`
  embedded in `/dealer-ai-admin`
  since M19.4. No M20 frontend
  surface changes.
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
  PROGRESS. M20.0 planning shipped
  at SESSION_160; M20.1 framework +
  canonical journey next at
  SESSION_161. Five increments
  remaining (M20.1–M20.5) per §7
  sequencing.
- **Planning-time streak:** **86
  as-recommended M5.1 → M20.0**
  across eleven consecutive
  milestones.
- **Guiding principle for M20
  implementation:** business
  outcomes through real UI on
  deterministic seeded state; not
  UI automation.
