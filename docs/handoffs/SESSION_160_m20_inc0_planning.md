---
title: "SESSION_160 handoff — Milestone 20 · Increment 0 (M20.0 — planning refinement)"
status: historical
type: handoff
date: 2026-08-02
session: 160
milestone: 20
milestone_status: in-progress
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_160 — Milestone 20 · Increment 0 (M20.0 — planning refinement)

## What shipped

Planning-only session per the M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 / M15.0 /
M16.0 / M17.0 / M18.0 / M19.0 precedent.
Full memo expansion + all **eight** §5
load-bearing decisions resolved at open.

**Candidate W folded into Candidate J**
per DOC_GOVERNANCE.md §2 at M20.0 open.
Candidate W as user-proposed was
functionally identical to Candidate J
(already documented in M19
retrospective §9); the governance-clean
move was to upgrade J's authoritative
brief with W's additional refinements
(explicit non-goals + why-M20 rationale
+ per-journey operational contract)
rather than introduce a parallel
candidate.

**§5.a → Candidate J confirmed** —
Operational Journey Validation via
Playwright acceptance testing, upgraded
scope. Milestone name: **"Operational
Journey Validation (Playwright
acceptance testing)."** User named at
SESSION_160 M20.0 open. All other
candidates deferred with re-entry paths
preserved per discovery rule.

**§5.b–§5.h all confirmed as-recommended.**
Streak extends to **86 planning-time as-
recommended M5.1 → M20.0** across **eleven
consecutive milestones now** (M10 + M11
+ M12 + M13 + M14 + M15 + M16 + M17 +
M18 + M19 + M20).

**Guiding principle established.** The
Playwright suite is an operational
acceptance contract, not a UI
automation project. Every journey
validates business outcomes through the
real application using deterministic
seeded state. If a journey passes, the
conclusion is that a dealership
employee can successfully perform that
operational workflow — not merely that
buttons were clicked successfully.
Governs every §5 decision, every
increment scope call, every review of a
proposed journey addition, and every
debate about flakiness resolution.

**Backend baseline unchanged:** 4,679
pass, 1 skipped, 0 fail (verified at
session open). **Frontend Vitest
baseline unchanged:** 153 pass.
Migrations `0001`–`0048` (unchanged).
Tenancy carriers 52 (unchanged — M20
adds no tenancy carriers). DRF admin
surface 113 (unchanged — M20 adds no
endpoints). Frontend operator routes
20 (unchanged — M20 adds no routes).
Permission classes 7 (unchanged —
zero-drift streak intact at nineteen
consecutive milestones; M20 extends
to twenty at close). Celery-beat task
families 10 (unchanged — M20 has no
beat entry).

## Load-bearing decisions confirmed at M20.0 open

Eight decisions per M10.0 / M11.0 /
M12.0 / M13.0 / M14.0 / M15.0 / M16.0 /
M17.0 / M18.0 / M19.0 precedent. All
confirmed as-recommended.

**§5.a — Milestone target selection.**
Candidate J — Operational Journey
Validation (Playwright acceptance
testing), upgraded scope. Milestone
name: "Operational Journey Validation
(Playwright acceptance testing)."
M18 shipped realistic demo
dealerships; M19 shipped repeatable
pilot onboarding. M20 establishes the
executable operational contract that
every future milestone extends.
Candidate A (accounting) preserved as
standing M21 question per discovery
rule.

**§5.b — Test framework + runner.**
Option A — Playwright +
`@playwright/test` + TypeScript. Named
in Candidate J's brief; matches
frontend TS stack; native trace viewer
+ auto-wait + parallelism + browser
matrix (Chromium / Firefox / WebKit)
with no add-on dependencies.

**§5.c — Repository layout for the
acceptance suite.** Option C — top-
level `acceptance/` workspace sibling
to `backend/` and `frontend/`, with
its own `package.json`. Journey files
organized by persona under
`acceptance/journeys/`; shared helpers
under `acceptance/support/`;
Playwright config at
`acceptance/playwright.config.ts`.

**§5.d — Seed data strategy.** Option
B — reuse M18 demo-store + M19 pilot
seed as the base; each journey has an
idempotent per-journey delta seed via
a Django management command
(`seed_journey_owner_morning_review`
etc.). Delta commands live in
`dealer_ai/management/commands/`.

**§5.e — Authentication + session
strategy.** Option B — Playwright
storage-state fixtures. One auth setup
project logs each persona in via the
real UI, saves storage state, and
subsequent journey projects reuse.
Personas: `owner`, `sales_manager`,
`advisor`, `recon_manager`,
`office_manager`, `bhph_collector`,
`platform_operator`. Storage-state
files at
`acceptance/.auth/{persona}.json`,
gitignored, regenerated each run.

**§5.f — Server lifecycle for the
suite.** Option A — Playwright
`webServer` config launches both
backend (dedicated port `:8101`,
dedicated test DB) and frontend
(`vite preview` in CI, `vite dev`
locally) and waits for readiness.
`reuseExistingServer: true` locally;
`false` in CI.

**§5.g — CI integration + artifact
posture.** Option A — dedicated
GitHub Actions acceptance job. Tiered
execution: pilot-critical subset
(`@pilot-critical` tag) on every PR
(~90s target); full six-journey suite
on `main` push (~5–8 min target).
Artifacts on failure: HTML report
(always), trace
(`trace: 'on-first-retry'`), video
(`video: 'retain-on-failure'`),
screenshot. Uploaded to the GitHub
Actions run.

**§5.h — Milestone completion contract
+ increment sequencing.** Option C —
M20.1 framework substrate + canonical
pilot onboarding journey; subsequent
increments bundle journeys 2-per-
increment. Six increments total.
Milestone completion contract: all
six journeys pass on `main` CI;
pilot-critical subset passes on PR;
HTML report + trace artifacts
confirmed in GitHub Actions run;
retrospective §9 records standing
M21 question.

## Streak

**86 planning-time as-recommended
M5.1 → M20.0.** Eleven consecutive
milestones now (M10 + M11 + M12 + M13
+ M14 + M15 + M16 + M17 + M18 + M19 +
M20) with every §5 decision confirmed
as-recommended at planning-time open.

Historical §5 counts:
- M10 through M17: 6 decisions each
  = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- Total across ten milestones (M10-
  M20): 48 + 7 + 8 + 8 = **71 §5
  decisions**.

The "86 planning-time as-recommended
M5.1 → M20.0" counter accumulates
across the full tracked history from
M5.1. The eleven consecutive
milestones (M10 → M20) carries the
"as-recommended per milestone open"
invariant without a single deviation.

## What's next: SESSION_161 M20.1 framework substrate + canonical pilot onboarding journey

Per `MILESTONE_20_PLANNING.md` §7
M20.1:

- New top-level `acceptance/`
  workspace with `package.json`,
  `playwright.config.ts`,
  `tsconfig.json`, `.gitignore`,
  `README.md`.
- `acceptance/support/auth/`,
  `acceptance/support/seed/`,
  `acceptance/support/assertions/`
  helpers.
- `dealer_ai/management/commands/seed_journey_pilot_onboarding.py`
  — idempotent seed of a `qualified`
  `PilotProspect` ready to convert.
  ~5-10 focused backend tests
  covering idempotency + tenant
  scoping.
- `acceptance/journeys/pilot/onboarding.spec.ts`
  — canonical journey walking the
  M19.4 pilot admin surface end-to-
  end, asserting business outcomes at
  each step (prospect state
  transitions, checklist completions,
  dealership `is_ready=True` at the
  end). Tagged `@pilot-critical`.
- `.github/workflows/acceptance.yml`
  — new job triggered on
  `pull_request` + `push` to `main`.
  Installs Node + Python + Chromium;
  runs M18 + M19 seed commands; runs
  Playwright with tag filter
  (`--grep '@pilot-critical'` on PR;
  no filter on `main`); uploads
  artifacts on failure.

**Backend baseline target at M20.1
close:** 4,679 → ~4,684-4,689 pass
(delta command tests). Frontend
Vitest: 153 (unchanged). Acceptance
suite: **1 journey passing on `main`
CI + PR**.

## What lands at M20.2 (SESSION_162)

Two dashboard-centric journeys:

- `seed_journey_owner_morning_review`
  + backend tests.
- `seed_journey_sales_manager_daily_startup`
  + backend tests.
- `acceptance/journeys/owner/morning_review.spec.ts`
  (tagged `@pilot-critical`).
- `acceptance/journeys/sales_manager/daily_startup.spec.ts`.

Acceptance baseline target: **3
journeys**. Pilot-critical subset:
**2**.

## What lands at M20.3 (SESSION_163)

Two operator back-office journeys:

- `seed_journey_recon_workflow` +
  tests.
- `seed_journey_office_accounting_workflow`
  + tests.
- `acceptance/journeys/recon/workflow.spec.ts`.
- `acceptance/journeys/office/accounting_workflow.spec.ts`.

Acceptance baseline target: **5
journeys**.

## What lands at M20.4 (SESSION_164)

BHPH collections standalone journey:

- `seed_journey_bhph_collections_workflow`
  + tests.
- `acceptance/journeys/bhph/collections_workflow.spec.ts`.
- Business-outcome assertion helpers
  for the promise-to-pay + broken-
  promise + repossession-initiation
  contract.

Acceptance baseline target: **6
journeys — full suite authored**.

## What lands at M20.5 (SESSION_165)

Close-out:
- Full-suite CI validation (verify
  ~5–8 min target on `main`; ~90s
  target on PR pilot-critical).
- Confirm artifact upload via
  intentional dry-run failure.
- `docs/CAPABILITY_MATRIX.md` §7u
  (M20 shipped surface).
- `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
  with §9 standing M21 question (is
  M21 the return-to-accounting
  milestone?).
- `docs/roadmap/MILESTONE_21_PLANNING.md`
  skeleton (status: draft).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M20 shipped status.
- Coordinated close-out commit per
  M18.6 / M19.6 pattern.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (this session's expansion target)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin — the
   authoritative brief M20 upgraded)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 + §9 (accounting slot
   designation preserved as M21
   standing question)
8. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface — the
   substrate M20 validates)
