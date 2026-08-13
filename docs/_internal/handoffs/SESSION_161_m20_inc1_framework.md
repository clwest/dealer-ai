---
title: "SESSION_161 handoff — Milestone 20 · Increment 1 (M20.1 — framework substrate + canonical pilot onboarding journey)"
status: historical
type: handoff
date: 2026-08-02
session: 161
milestone: 20
milestone_status: in-progress
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_161 — Milestone 20 · Increment 1 (M20.1 — framework substrate + canonical pilot onboarding journey)

## What shipped

The M20 tooling substrate + the highest-
signal canonical journey. Per M20
planning §7 M20.1 + §5.b–§5.h.

**New top-level `acceptance/` workspace**
sibling to `backend/` and `frontend/`
per §5.c Option C:

- `acceptance/package.json` — Playwright
  1.49 + TypeScript 5.6 devDeps only.
- `acceptance/playwright.config.ts` —
  `webServer` array launching backend
  (`:8101` with `M20_ACCEPTANCE_DB=1`
  opting into isolated SQLite test DB
  at `backend/db.acceptance.sqlite3`)
  + frontend (`vite dev` locally,
  `vite build && vite preview` in CI),
  `setup` project + `platform_operator`
  project reusing storage-state from
  `.auth/platform_operator.json`,
  HTML + list + github reporters,
  artifact config (trace on-first-retry,
  video retain-on-failure, screenshot
  only-on-failure), `@pilot-critical`
  tag support.
- `acceptance/tsconfig.json` —
  strict TS with `@support/*` path
  alias.
- `acceptance/.gitignore` — covers
  `.auth/`, `playwright-report/`,
  `test-results/`, `node_modules/`.
- `acceptance/README.md` — one-page
  contributor onboarding.

**Support layer** per §5.d + §5.e:

- `acceptance/support/auth/personas.ts`
  — persona registry (M20.1 ships
  one: `platform_operator`).
- `acceptance/support/auth/login.setup.ts`
  — setup project that (a) runs the
  M20.1 seed delta command, then (b)
  logs the `platform_operator`
  persona in via the real UI at
  `/login` (fills `#login-username`
  + `#login-password`, clicks the
  Sign in button), and saves
  storage state.
- `acceptance/support/seed/invoke.ts`
  — helper to spawn `python3 manage.py
  <cmd>` against the acceptance DB
  and propagate stderr on failure.
- `acceptance/support/assertions/pilot.ts`
  — business-outcome assertion helpers
  (`expectPilotExists`,
  `expectStepCompleted`,
  `expectPilotReady`) that read the
  M19.3 admin API surface. Also
  exports `PILOT_ONBOARDING_STEP_ORDER`
  matching the seven M19 §5.f step
  slugs.

**Backend seed delta command** per §5.d
Option B:

- `dealer_ai/management/commands/seed_journey_pilot_onboarding.py`
  — provisions the `acceptance-operator`
  user (with `sales_manager` role at
  the default dealership so the
  persona can reach `/dealer-ai-admin`),
  the `acceptance-pilot-owner` user
  (nominated as `owner_username`
  when the journey creates the pilot),
  and a `qualified` `PilotProspect`
  ("Acceptance Motors") ready for
  conversion. Composes existing
  service verbs (`create_prospect`
  + `advance_prospect_state`) — no
  parallel write paths. Idempotent
  via `get_or_create` on stable
  usernames + `contact_email` for
  the prospect. `--reset` flag wipes
  the seeded prospect + clears
  memberships then re-seeds.

**Backend tests** for the seed command:
15 focused tests in
`dealer_ai/tests/test_m201_seed_journey_pilot_onboarding.py`
covering fresh-run provisioning,
idempotency (users, prospect, role
membership all deduped on second
invocation), `--reset` behavior
(deletes prospect, clears
memberships, preserves users,
re-seeds a fresh qualified prospect),
tenant scoping (prospect has no
dealership FK; operator role scoped
to default dealership only), and
terminal-recovery (if the prior
prospect is `declined`/`converted`,
the seed creates a fresh row per
M19 §5.b design).

**Settings extension** (§0.a
M20.1 micro-decision): added
`M20_ACCEPTANCE_DB=1` env branch to
`backend/dealer_kit/settings.py` that
points the default DB at
`backend/db.acceptance.sqlite3`
(gitignored). Matches the M2.1
`migration_check` DB alias pattern —
isolated SQLite file, additive to
existing settings, no impact on dev
or production DB paths.

**Canonical journey spec** per §5.h
Option C:

- `acceptance/journeys/pilot/onboarding.spec.ts`
  — tagged `@pilot-critical`. Six-step
  journey walking the M19.5 playbook:
  land on `/dealer-ai-admin`, fill
  the Create pilot form, submit,
  verify pilot appears with
  `dealership_created` auto-fired,
  open detail panel, advance each
  remaining checklist step through
  `readiness_confirmed`, verify
  `is_ready=true` at close via the
  M19.3 admin API + verify the
  "Ready" badge appears on the pilot
  row. Business-outcome assertions
  target service state, not DOM
  state.

**GitHub Actions CI job** per §5.g
Option A:

- `.github/workflows/acceptance.yml`
  — new job triggered on
  `pull_request` + `push` to `main`.
  Sets up Python 3.12 + Node 20 +
  installs backend + frontend +
  acceptance deps; caches Playwright
  Chromium browser install; runs
  Playwright with
  `--grep '@pilot-critical'` on PR
  and no filter on `main`. Uploads
  HTML report + traces + videos as
  artifacts on failure or
  cancellation (14-day retention).

## Verification

**Backend baseline (post-M20.1):**
4,679 → **4,694 pass** (+15 seed
command tests), 1 skipped, 0 fail.
Frontend Vitest baseline
unchanged: **153 pass**. `tsc
--noEmit` clean. `manage.py check`
clean. `makemigrations --check
--dry-run` → "No changes detected."

**Zero drift:**
- Migrations unchanged at
  `0001`–`0048`.
- Tenancy carriers unchanged at
  **52**.
- Permission classes unchanged at
  **7** (zero-drift streak intact
  at nineteen consecutive
  milestones; extends to twenty
  at M20.5 close).
- DRF admin surface unchanged at
  **113**.
- Frontend operator routes
  unchanged at **20**.
- No existing backend service
  verb, endpoint, migration, or
  frontend route modified.

**Acceptance suite:** one journey
authored (pilot onboarding), tagged
`@pilot-critical`. Full end-to-end
Playwright execution deferred to
CI first run (or local `cd
acceptance && npm install && npx
playwright install chromium && npm
test`). The journey has NOT been
executed in-session — the M20.1
substrate is code-complete but the
first green run happens either in
CI on the M20.1 PR or in a manual
local execution.

## §0.a — Implementation-time decisions

**M20.1 decision 1 — isolated
acceptance DB via env flag.**
Playwright `webServer` sets
`M20_ACCEPTANCE_DB=1`; settings.py
branches to
`db.acceptance.sqlite3`. Matches
the M2.1 `migration_check` DB
alias pattern; additive to
existing settings; no impact on
dev or production DB paths.

**M20.1 decision 2 — Playwright
worker parallelism.** Set
`workers: 1` +
`fullyParallel: false`.
Rationale: journey seeds mutate
shared DB state; serialization
is the safer default until we
have a per-journey DB reset
pattern. Revisit in M20.5 if
suite time exceeds the 5–8 min
target.

**M20.1 decision 3 — auth setup
via real UI, not test-only
endpoint.** Per §5.e Option B
already-decided; the setup
project uses `page.goto('/login')`
+ form fill + submit. Storage
state saved to
`.auth/platform_operator.json`
(gitignored). No test-only
authentication code path is
introduced.

## What's next: SESSION_162 M20.2

Per `MILESTONE_20_PLANNING.md` §7
M20.2 — two dashboard-centric
journeys sharing fixtures:

- `seed_journey_owner_morning_review`
  + backend tests (~5–10).
- `seed_journey_sales_manager_daily_startup`
  + backend tests (~5–10).
- `acceptance/journeys/owner/morning_review.spec.ts`
  — tagged `@pilot-critical`.
- `acceptance/journeys/sales_manager/daily_startup.spec.ts`.
- Business-outcome assertion
  helpers extended as needed
  (`support/assertions/dashboard.ts`).
- `owner` + `sales_manager`
  personas added to
  `support/auth/personas.ts` +
  new project entries in
  `playwright.config.ts`.

**Acceptance baseline target at
M20.2 close:** **3 journeys**
(pilot onboarding + owner morning
review + sales manager daily
startup). Pilot-critical subset
now 2 (pilot onboarding + owner
morning review). Backend baseline
~4,694 → ~4,704.

## What lands at M20.3 (SESSION_163)

Two operator back-office journeys:

- `seed_journey_recon_workflow`
  + tests.
- `seed_journey_office_accounting_workflow`
  + tests.
- Journey specs for both.
- `recon_manager` +
  `office_manager` personas.

## What lands at M20.4 (SESSION_164)

BHPH collections journey +
seed + tests + `bhph_collector`
persona.

## What lands at M20.5 (SESSION_165)

Close-out: CI hardening +
retrospective + capability
matrix §7u + roadmap flip +
M21 skeleton + coordinated
close-out commit.

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
8. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
   (M20.0 planning close)
