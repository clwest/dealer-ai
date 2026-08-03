---
title: "Milestone 20 — Operational Journey Validation (Playwright acceptance testing)"
status: active
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_159 (skeleton), SESSION_160 (expansion)
milestone: 20
milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_19_PLANNING.md
  - docs/roadmap/MILESTONE_19_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_18_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
---

# Milestone 20 — Operational Journey Validation (Playwright acceptance testing)

> **Active planning memo.** Expanded at
> SESSION_160 M20.0 open from the
> skeleton drafted at M19.6 close.
> §5.a Candidate J confirmed at open —
> Operational Journey Validation via
> Playwright acceptance testing,
> upgraded scope (non-goals + why-M20
> rationale + per-journey operational
> contract). Candidate W folded into J
> per DOC_GOVERNANCE.md §2 (prefer
> updating authoritative documents
> over creating parallel versions).
>
> **M20 is a tooling-axis milestone.**
> M18 shipped realistic demo
> dealerships. M19 shipped repeatable
> pilot onboarding. M20 establishes
> the **executable operational
> contract** that every future
> milestone extends — durable
> Playwright acceptance suites
> executing real dealership workflows
> through the shipped UI against
> deterministic seeded state.
>
> **This is not a domain milestone.**
> M20 introduces zero new tenancy
> carriers, zero new migrations, zero
> new permission classes, zero new
> DRF endpoints, and zero new frontend
> routes. The change surface is a new
> top-level `acceptance/` workspace,
> a Playwright config, per-journey
> seed delta management commands, and
> a dedicated GitHub Actions
> acceptance job. The zero-drift
> permission-class streak extends
> **nineteen → twenty** consecutive
> milestones.
>
> **Eight load-bearing decisions** —
> §5.a target + §5.b framework +
> §5.c layout + §5.d seed strategy +
> §5.e authentication + §5.f server
> lifecycle + §5.g CI + §5.h
> completion contract + increment
> sequencing. **All eight confirmed
> as-recommended at SESSION_160 M20.0
> open** — streak extends to **86
> planning-time as-recommended M5.1
> → M20.0 across eleven consecutive
> milestones now** (M10 + M11 + M12
> + M13 + M14 + M15 + M16 + M17 +
> M18 + M19 + M20).

## Guiding principle (Candidate J contract)

The Playwright suite is an
**operational acceptance contract**,
not a UI automation project. Every
journey validates business outcomes
through the real application using
deterministic seeded state. If a
journey passes, the conclusion is
that a dealership employee can
successfully perform that
operational workflow — **not merely
that buttons were clicked
successfully.**

This principle governs every §5
decision, every increment scope
call, every review of a proposed
journey addition, and every debate
about test flakiness resolution.
Assertions target business state
(a lead is assigned, a payment is
posted, an inventory row is
imported, a pilot advances to
`readiness_confirmed`), not DOM
state.

## 0. Engineering practices to preserve from M2–M19

Same posture as M19.0 except where
noted. Non-negotiable:

- **Backend-first architecture.**
  No business logic in the
  acceptance suite. Seed delta
  commands live in
  `dealer_ai/management/commands/`
  and go through service verbs;
  the Playwright suite never
  reaches into the ORM directly.
- **Service ownership.** Seed
  delta commands compose existing
  service verbs — no parallel
  write paths for journey setup.
  If a journey needs state that
  no service verb produces, that
  is either a missing capability
  (surface via §0.a) or a
  legitimate test fixture (via
  existing `_auth_helpers`
  patterns).
- **Tenancy discipline.** Every
  seed delta command scopes its
  writes with `dealership=`
  explicitly. Playwright suites
  target demo/pilot tenants
  only; **no acceptance journey
  targets a live production
  tenant.**
- **Load-bearing decisions get
  user review BEFORE code.** All
  eight §5 decisions confirmed at
  SESSION_160 M20.0 open. Any
  implementation-time micro-
  decisions surface as §0.a
  amendments.
- **Additive extension over
  fork.** M20 does not modify
  existing seed commands, does
  not modify existing service
  verbs, does not modify existing
  endpoints. The new surface is
  the `acceptance/` workspace +
  per-journey delta seed commands
  + CI job. Every extension is
  additive.
- **Zero-drift permission-class
  posture.** M20 endpoint use is
  read-only through the real UI
  as the authenticated persona
  cookie; no new permission class,
  no changes to existing
  permission classes. Streak
  extends **nineteen → twenty**
  consecutive milestones (M10 →
  M20).
- **Every M20 assertion of
  shipped-surface counts uses
  `>=`** per M9–M19 growth-only-
  list lesson (M18.5 retrospective
  §6 lesson 5). Journey counts
  are exact-equality (six journeys
  is the M20 shape); shipped-
  surface counts (endpoints,
  routes, permission classes,
  tenancy carriers, migrations)
  stay `>=`.
- **In-place page extension over
  new route** per M17 §6 lesson 6
  + M19.4 posture. M20 adds zero
  frontend routes; all journeys
  target already-shipped surfaces.
- **Naming discipline** per M17
  §6 lesson 3. Durable journey
  files carry operator-facing
  names:
  `acceptance/journeys/owner/morning_review.spec.ts`,
  `acceptance/journeys/pilot/onboarding.spec.ts`,
  etc.
- **Journey isolation.** Each
  journey is independently
  runnable, independently
  reseedable, and independently
  debuggable. No journey depends
  on the state left by another
  journey.
- **Fail-loud contract.** Journey
  test names identify the
  operational workflow (not the
  clicked element). Failure
  messages target the business
  outcome that failed (not the
  selector that didn't resolve).
  Screenshots + traces attach on
  failure per §5.g.

### 0.a Change log — resolved decisions

**SESSION_160 M20.0 open (2026-08-02):**

- **Candidate W → folded into
  Candidate J** per
  DOC_GOVERNANCE.md §2. J
  authoritative brief upgraded
  with W's non-goals + why-M20
  rationale + per-journey
  operational contract.
- **§5.a → Candidate J confirmed
  at open.** User named —
  Operational Journey Validation
  via Playwright acceptance
  testing. Milestone name:
  **"Operational Journey
  Validation (Playwright
  acceptance testing)."** All
  other candidates deferred with
  re-entry paths preserved per
  discovery rule.
- **§5.b → Option A confirmed as-
  recommended.** Playwright +
  `@playwright/test` +
  TypeScript. Named in Candidate
  J's brief; matches frontend
  TS stack; native trace viewer
  + auto-wait + parallelism +
  browser matrix (Chromium /
  Firefox / WebKit) with no
  add-on dependencies.
- **§5.c → Option C confirmed as-
  recommended.** Top-level
  `acceptance/` workspace
  sibling to `backend/` and
  `frontend/`, with its own
  `package.json`. Journey files
  organized by persona under
  `acceptance/journeys/`; shared
  helpers under
  `acceptance/support/`;
  Playwright config at
  `acceptance/playwright.config.ts`.
- **§5.d → Option B confirmed as-
  recommended.** Reuse M18 demo-
  store + M19 pilot seed as the
  base; each journey has an
  optional idempotent per-
  journey delta seed via a
  Django management command
  (`seed_journey_owner_morning_review`
  etc.). Delta commands live in
  `dealer_ai/management/commands/`.
- **§5.e → Option B confirmed as-
  recommended.** Playwright
  storage-state fixtures — one
  auth setup project logs each
  persona in via the real UI,
  saves storage state, and
  subsequent journey projects
  reuse. Personas:
  `owner`, `sales_manager`,
  `advisor`, `recon_manager`,
  `office_manager`,
  `bhph_collector`,
  `platform_operator`. Storage-
  state files at
  `acceptance/.auth/{persona}.json`,
  gitignored, regenerated by
  the setup project each run.
- **§5.f → Option A confirmed as-
  recommended.** Playwright
  `webServer` config launches
  both backend (dedicated port,
  dedicated test DB) and
  frontend (`vite preview` in
  CI, `vite dev` locally) and
  waits for readiness.
  `reuseExistingServer: true`
  locally; `false` in CI.
- **§5.g → Option A confirmed as-
  recommended.** Dedicated
  GitHub Actions acceptance job.
  Tiered execution: pilot-
  critical subset
  (`@pilot-critical` tag) on
  every PR (~90s target); full
  six-journey suite on `main`
  push (~5–8 min target).
  Artifacts on failure: HTML
  report always, trace
  (`trace: 'on-first-retry'`),
  video (`video: 'retain-on-
  failure'`), screenshot.
  Uploaded to the GitHub Actions
  run.
- **§5.h → Option C confirmed as-
  recommended.** M20.1
  framework substrate + canonical
  pilot onboarding journey.
  Subsequent increments bundle
  journeys 2-per-increment.
  Milestone completion contract:
  all six journeys pass on
  `main` CI; pilot-critical
  subset passes on PR; HTML
  report + trace artifacts
  confirmed in GitHub Actions
  run; retrospective §9 records
  standing M21 question.
- **§7 sequencing → six-increment
  shape confirmed as-recommended.**
  M20.0 planning + M20.1
  framework + canonical pilot
  onboarding journey + M20.2
  owner morning review + sales
  manager daily startup + M20.3
  recon + office/accounting +
  M20.4 BHPH collections +
  M20.5 CI hardening + close-
  out.
- **Streak extends to 86
  planning-time as-recommended
  M5.1 → M20.0.** Eleven
  consecutive milestones now
  (M10 → M20).

## 1. Business questions this milestone answers

Five operator-workflow validation
questions, each tied to the
executable-acceptance-contract
posture. Every question was
unanswerable before M20 (M18 shipped
demo dealerships and M19 shipped
pilot onboarding, but no automated
guarantee that a real employee could
execute either through the real UI).

### Q1. Can Chris (or any future contributor) prove that a shipped operational workflow still works end-to-end after a code change?

**Before M20:** Not systematically.
Unit and integration tests confirm
that individual verbs + endpoints
behave; frontend Vitest confirms
that components render and hook
logic is correct. But no automated
test proves that an owner can log
in, land on the dashboard, and see
yesterday's pipeline + realized
gross without something breaking
along the way. Regression detection
depends on human exploratory
testing between milestones — a
scaling anti-pattern that will fail
as the surface area grows.

**After M20:** Yes. Six operational
journeys execute the six
representative daily workflows end-
to-end through the real UI on every
`main` push, with the pilot-critical
subset (owner morning review + pilot
onboarding) running on every PR.
A workflow regression fails a CI
job; the developer sees a trace and
a screenshot that name the exact
business outcome that broke.

### Q2. Can a new contributor understand what "the platform does" by reading executable code, not just prose?

**Before M20:** Partially. The
capability matrix and research
corpus describe capabilities in
prose. The unit-test suite proves
that verbs return the right shape.
But the connective tissue — "here
is how an owner actually uses this
in a normal day" — lives only in
Chris's head and in the M18 demo
briefs.

**After M20:** Yes. Each journey
spec is a readable operational
walk-through. A new contributor
reading
`acceptance/journeys/owner/morning_review.spec.ts`
sees precisely which pages an
owner visits in what order and
what business state confirms each
step. Journey files become the
narrative source of truth for
"what does the platform actually
do?"

### Q3. Can the pilot onboarding playbook (M19.5) be validated as executable, not just documented?

**Before M20:** No. The playbook
is a markdown document. Chris
follows it manually; deviations
depend on his memory. Whether
the playbook still matches the
shipped M19.4 admin surface after
future frontend changes is an
open question that only Chris's
next dry-run can answer.

**After M20:** Yes. The M20.1
canonical pilot onboarding
journey codifies the M19.5
playbook as an executable
contract. A UI or endpoint
change that breaks the playbook
fails the journey on the next
PR. The playbook and the
journey stay coherent by
construction (per M18 §6 lesson
2 — coherence contract).

### Q4. Can operational surface areas that Chris rarely exercises during dry-runs be caught by CI when they regress?

**Before M20:** Not reliably.
Chris exercises the BHPH
collections surface during M19
dry-runs but not on every
milestone. The office/accounting
trial-balance surface has not
been touched since M18. A silent
regression in either would go
undetected until an operator
surfaced it — a slow, costly
detection loop.

**After M20:** Yes. Every daily
operational surface has a
representative journey. BHPH
collections + office/accounting
have dedicated M20.3–M20.4
journeys. A regression on any
surfaces on the next `main`
push.

### Q5. Can Chris hand off M21+ implementation work to a contributor without risking undetected workflow damage?

**Before M20:** No. Chris is the
only reviewer who reliably
catches "this endpoint change
broke the owner's morning-review
click path" because he holds the
operational context in his head.
Handing off implementation
requires either full-context
handoff or accepting workflow-
regression risk.

**After M20:** Yes. The
acceptance suite is the workflow-
regression detector. A
contributor's PR that breaks a
journey fails CI visibly.
Handoff risk drops to "did the
contributor extend the suite
when they shipped new operator-
facing behavior?" — a reviewable
question rather than a hidden
one.

## 2. What existing primitives extend

M20 continues the "additive
extension over fork" pattern
(M11.1 / M12.3 / M13.2 / M14.1 /
M15.1 / M16.1 / M17.1 / M18.1 /
M19.1). One new workspace, one
Playwright config, one new CI job,
six new journey specs, per-journey
seed delta commands. No changes to
backend service surface, no changes
to migrations, no changes to
existing management commands.

### New surface — top-level workspace

- **`acceptance/` (new top-level
  workspace).** Sibling to
  `backend/` and `frontend/` per
  §5.c. Contents:
  - `package.json` — Playwright
    + TypeScript devDeps only;
    isolated from frontend
    runtime bundle.
  - `playwright.config.ts` —
    project definitions (auth
    setup + one per persona),
    `webServer` config, reporter
    config, artifact config,
    tag filters.
  - `tsconfig.json` — TS
    settings mirroring frontend
    conventions where
    applicable.
  - `journeys/{persona}/` —
    journey specs organized by
    persona:
    `owner/morning_review.spec.ts`,
    `sales_manager/daily_startup.spec.ts`,
    `recon/workflow.spec.ts`,
    `office/accounting_workflow.spec.ts`,
    `bhph/collections_workflow.spec.ts`,
    `pilot/onboarding.spec.ts`.
  - `support/` — shared helpers:
    `auth/` (storage-state
    orchestration), `seed/`
    (management-command
    invocation helpers),
    `assertions/` (business-
    outcome assertion helpers),
    `selectors/` (persona-
    stable selector patterns).
  - `.auth/` — gitignored;
    storage-state files
    regenerated per suite run.
  - `.gitignore` — covers
    `.auth/`,
    `playwright-report/`,
    `test-results/`, and
    `node_modules/`.
  - `README.md` — one-page
    contributor onboarding:
    how to run locally, how to
    add a new journey, how to
    interpret CI failures.

### New surface — per-journey seed deltas

Per §5.d Option B. Idempotent
management commands scoped
narrowly to the state each
journey needs on top of the M18
demo + M19 pilot base:

- `seed_journey_owner_morning_review`
  — plants an overnight lead +
  scheduled showing + one
  contract in the pipeline for
  the default demo tenant.
- `seed_journey_sales_manager_daily_startup`
  — plants three overnight
  leads + an assigned advisor
  queue + a be-back due today.
- `seed_journey_recon_workflow`
  — plants a fresh acquisition
  awaiting a condition report.
- `seed_journey_office_accounting_workflow`
  — advances yesterday's
  accounting to a state where
  an end-of-day trial balance
  is meaningful.
- `seed_journey_bhph_collections_workflow`
  — plants a note with a
  payment coming due and a
  broken promise-to-pay ready
  for repossession initiation.
- `seed_journey_pilot_onboarding`
  — plants a
  `PilotProspect` in
  `qualified` state ready to
  be converted via the M19.4
  admin surface.

Every delta command:
- Composes existing service
  verbs (no parallel write
  paths).
- Is idempotent — running
  twice leaves the same
  state.
- Reports the tenant it
  seeded so the journey can
  assert against a stable
  target.

### New surface — CI job

Per §5.g Option A. GitHub
Actions job at
`.github/workflows/acceptance.yml`:
- Triggers on `pull_request`
  + `push` to `main`.
- Sets up Node + Python +
  Chromium.
- Runs the M18 + M19 seed
  commands.
- Runs the applicable
  Playwright project set
  (pilot-critical on PR;
  full suite on `main`).
- Uploads HTML report +
  traces + videos on
  failure.

### Consumed but not modified

- **All shipped M1–M19 service
  verbs.** Journey seed deltas
  invoke them; journeys
  exercise them through the
  UI. No modifications.
- **All shipped M1–M19
  endpoints.** Journeys hit
  them through the UI. No
  modifications.
- **All shipped frontend
  routes.** Journeys visit
  them. No modifications;
  frontend operator routes
  stay at **20**.
- **M18 + M19 seed commands.**
  Journeys assume the M18 demo
  + M19 pilot seed has been
  loaded. No modifications.
- **M18.1 outbound guard.**
  Acceptance-run tenants are
  demo + pilot only, so
  outbound suppression already
  applies. No modifications.

## 3. What's NOT in this milestone (deferrals)

Every deferral recorded with a
clear re-entry path. **Twelve M20-
specific + eleven universal = 23
deferrals.**

**M20-specific deferrals:**

1. **Screenshot / pixel-perfect
   visual regression testing.**
   Explicit non-goal per Candidate
   J's non-goals list. If visual
   regression becomes a real
   operator pain point, that
   surfaces as a future milestone
   candidate (probable name:
   Candidate V — visual
   regression) with its own
   tooling axis debate.
2. **Broad UI redesign.**
   Explicit non-goal. UX friction
   discovered during Playwright
   authoring feeds Candidate P
   (onboarding UX polish); it
   does not land in M20.
3. **Cosmetic UX polish.**
   Explicit non-goal per
   Candidate J. Same re-entry
   path as deferral 2 — feeds
   Candidate P.
4. **Replacement of unit or
   integration tests.**
   Explicit non-goal. Playwright
   is additive to the existing
   test contract; no existing
   test is deleted or replaced
   by an acceptance journey.
5. **Unrelated dealership
   capabilities.** Explicit
   non-goal. M20 ships zero new
   operator-facing capabilities;
   every journey exercises
   already-shipped M1–M19
   surface only.
6. **Playwright tests against a
   real staging DB with a real
   pilot dealer.** That is
   Candidate L. M20 targets
   demo + pilot tenants in the
   Playwright-managed test DB
   only; staging validation
   defers to Candidate L.
7. **Cross-browser matrix
   beyond Chromium in CI.**
   Chromium-only in CI to keep
   PR time bounded; Firefox +
   WebKit run locally via
   `--project=firefox` /
   `--project=webkit` and are
   available for pre-merge
   validation. Full cross-
   browser CI matrix defers
   pending observed browser-
   specific regression evidence.
8. **Mobile / responsive
   viewport journeys.** All
   M20 journeys target desktop
   viewport (Chris's operator
   posture). Mobile/responsive
   defers to a future mobile-
   readiness milestone.
9. **Performance / load
   testing via Playwright.**
   Explicit non-goal; the
   contract is operational
   correctness, not throughput.
   Performance testing would
   be a separate future
   milestone with a separate
   tool choice debate.
10. **Third-party integration
    stubs / mocks in journeys.**
    All outbound integration
    is already suppressed for
    demo + pilot tenants via
    the M18.1 outbound guard;
    no additional stubbing is
    needed at M20. If a future
    journey needs a mocked
    external response, that
    surfaces as an §0.a
    amendment.
11. **Automatic journey
    generation from user
    telemetry.** Explicit non-
    goal; every journey is
    hand-authored so the
    business-outcome
    assertions are meaningful.
12. **Nightly-cron acceptance
    runs.** The `main` push
    trigger is sufficient; a
    nightly cron adds noise
    without new signal
    unless the tree changes
    between pushes (which is
    detectable by other means).
    Defers pending observed
    need.

**Universal deferrals (any
platform milestone):**

- Payroll (external service).
- W-2 / 1099 generation
  (external service).
- Year-end tax return
  preparation (external CPA).
- GAAP-compliant audited
  financial reporting (out of
  scope for platform v1).
- Direct DMS integration
  (belongs to a future
  vendor-integration milestone).
- Real inventory-feed
  integrations
  (Manheim / ADESA / ACV).
- Bilingual UI.
- Payment processing / e-sign
  / DMS write-back.
- Multi-tenant SaaS shell
  (billing / org).
- Predictive ML on
  operational data.
- SSO / MFA on top of M1 auth.

## 4. What existing tests bind

M20 introduces zero new backend
migrations, zero new tenancy
carriers, zero new permission
classes, zero new endpoints. The
existing `>=` counting tests all
stay satisfied.

- **Backend test baseline.** M20
  is expected to leave the
  backend baseline unchanged at
  **4,679 pass, 1 skipped, 0
  fail** through M20.1–M20.4.
  M20.5 may add a small number
  of backend tests covering the
  new seed delta management
  commands (idempotency
  guarantees, tenant scoping)
  — target **~10–20** new
  backend tests by M20 close.
- **Frontend Vitest baseline.**
  M20 leaves the frontend
  Vitest baseline unchanged at
  **153 pass** through the
  entire milestone. The
  acceptance suite is a
  separate test surface; it
  does not extend Vitest.
- **Migrations.** Unchanged
  through M20 close at
  `0001`–`0048`.
- **Tenancy carriers.**
  Unchanged at **52**.
- **Permission classes.**
  Unchanged at **7 actual**.
  Zero-drift streak extends
  **nineteen → twenty**
  consecutive milestones
  (M10 → M20).
- **DRF admin surface.**
  Unchanged at **113**.
- **Frontend operator
  routes.** Unchanged at
  **20**.
- **Celery-beat task
  families.** Unchanged at
  **10**.

**New M20 test surface (separate
from backend + frontend
baselines):**

- **Acceptance suite:** six
  Playwright journey specs by
  milestone close. Pilot-
  critical tag applies to
  M20.1 (pilot onboarding)
  and M20.2 (owner morning
  review). Full-suite
  execution target: passing
  on `main` at M20.5 close.

## 5. Load-bearing decisions

Eight decisions. **All eight
confirmed as-recommended at
SESSION_160 M20.0 open.** Streak
extends to **86 planning-time as-
recommended M5.1 → M20.0**
(eleven consecutive milestones
now).

### 5.a `[RESOLVED at SESSION_160 open]` — Milestone target selection

**Question.** Which candidate from
the M19 §9 nine-candidate list
(carry-forwards T, U + M18 §8
Candidate A + M19 new P, L, M +
M18.1 §0.a D + M18.2 §0.a C + M19.6
§0.a J) defines M20 scope?

**Decision.** **Candidate J —
Operational Journey Validation
via Playwright acceptance
testing, upgraded scope.**
Milestone name: **"Operational
Journey Validation (Playwright
acceptance testing)."** User
named at SESSION_160 M20.0 open.
Candidate W (user-proposed at
M20.0) folded into Candidate J
per DOC_GOVERNANCE.md §2; J
authoritative brief upgraded
with W's non-goals + why-M20
rationale + per-journey
operational contract.

**Rationale.** (1) J is
unblocked — its dependencies
are entirely M1–M19 shipped
surface. (2) Every gated
candidate (T, L, U, P, M)
requires an external signal
(tester sessions, first live
pilot, willingness to open
demo to strangers, observed
onboarding friction, second
operator) that has not
arrived; picking a gated
candidate risks an M20 with
no substrate to work on. (3)
J produces durable substrate
every subsequent milestone
extends — the executable
operational contract makes
every future milestone
measurably safer. (4) M18 +
M19 established the substrate
(realistic demo dealerships +
repeatable pilot onboarding);
the platform now has enough
operator-facing surface area
for end-to-end journey
validation to be meaningful.
(5) Candidate A (accounting)
is the strongest alternative
but three consecutive
milestones diverging from
M18 §8's accounting
designation risks ossifying
the divergence — this is
recorded as the standing M21
question, preserving A as a
re-entry path per the
discovery rule (defer, never
discard). (6) Candidates D, C
remain deferred pending
evidence (token burn on demo
tenants, operator F&I
chargeback demand) that has
not surfaced.

### 5.b `[RESOLVED at SESSION_160 open]` — Test framework + runner

**Question.** Which end-to-end
framework backs the acceptance
suite?

- **Option A** — Playwright
  (`@playwright/test`),
  TypeScript.
- **Option B** — Cypress,
  JavaScript / TypeScript.
- **Option C** — Selenium
  WebDriver via Python
  (Django-native).

**Decision. Option A —
Playwright + `@playwright/test`
+ TypeScript** confirmed as-
recommended.

**Rationale.** (1) Named in
Candidate J's authoritative
brief; already ratified by
§5.a. (2) TypeScript matches
the frontend stack (Vite +
React + TS) — no new language
surface introduced. (3) Native
trace viewer + auto-wait +
parallelism + browser matrix
(Chromium / Firefox / WebKit)
with zero add-on dependencies.
(4) `webServer` config
integrates with the existing
Vite + Django local-dev
pattern with no infrastructure
changes (see §5.f). (5)
Cypress adds an iframe
execution model that
complicates cross-origin and
file-upload journeys (the
M19.4 inventory-import
journey uses file uploads).
(6) Selenium-Python would
require duplicating the
frontend's TS-fluent selector
patterns in a second language,
doubling maintenance burden.

### 5.c `[RESOLVED at SESSION_160 open]` — Repository layout for the acceptance suite

**Question.** Where does the
acceptance suite live in the
tree?

- **Option A** — `frontend/e2e/`
  (frontend workspace-owned).
- **Option B** —
  `backend/tests/acceptance/`
  (Django test-tree extension).
- **Option C** — Top-level
  `acceptance/` sibling to
  `backend/` and `frontend/`,
  with its own `package.json`.

**Decision. Option C — top-
level `acceptance/` workspace**
confirmed as-recommended.

**Rationale.** (1) Journeys
span both frontend (real UI)
and backend (seed commands +
assertion of DB state).
Placing under either workspace
implies false ownership. (2) A
top-level `acceptance/` matches
the split-monorepo pattern
already established by
`backend/` + `frontend/`. (3)
Its own `package.json` isolates
Playwright's dependency tree
from the frontend runtime
bundle (Playwright is heavy
and dev-only for the suite).
(4) Journey files organized by
persona (`owner`,
`sales_manager`, `recon`,
`office`, `bhph`, `pilot`).
(5) Shared helpers in
`acceptance/support/` (auth
fixtures, seed invocation, UI
helpers, business-outcome
assertions). (6) CI config +
Playwright config at
`acceptance/playwright.config.ts`
— one canonical entry point.

### 5.d `[RESOLVED at SESSION_160 open]` — Seed data strategy

**Question.** How does each
journey arrive at a known
starting state?

- **Option A** — Django JSON
  fixtures per journey
  (`loaddata journey_owner_morning.json`).
- **Option B** — Reuse the M18
  demo-store seed + M19 pilot
  seed as the base; each
  journey has an optional per-
  journey delta seed via a
  Django management command.
- **Option C** — Fully
  programmatic seeding via ORM
  calls inside `test.beforeEach`
  hooks.

**Decision. Option B — reuse
existing seed substrate +
idempotent per-journey delta
commands** confirmed as-
recommended.

**Rationale.** (1) Preserves
M18/M19 substrate as the
primary seed contract
(`seed_demo_stores`,
`seed_pilot_prospects`) — no
parallel fixture surface to
maintain. (2) Delta commands
apply narrow, journey-specific
state on top of the shared
base. (3) Each journey remains
independent + rerunnable — the
delta command is idempotent
and can be invoked between
test runs. (4) Fixtures
(Option A) drift silently as
models evolve; management
commands break loudly at
import time. (5) Programmatic
seeding inside test hooks
(Option C) creates a hidden
ORM dependency inside the
acceptance suite, violating
the guiding principle's
"real UI + seeded state"
contract. (6) Delta commands
live in
`dealer_ai/management/commands/seed_journey_*.py`
— same location + convention
as existing seeders.

### 5.e `[RESOLVED at SESSION_160 open]` — Authentication + session strategy

**Question.** How does
Playwright authenticate as the
correct persona for each
journey?

- **Option A** — Full UI-driven
  login inside every test's
  setup.
- **Option B** — Playwright
  storage-state fixtures — one
  auth setup project logs each
  persona in via the real UI,
  saves storage state, and
  subsequent journey projects
  reuse.
- **Option C** — Test-only
  backend endpoint that mints
  session cookies without UI
  login.

**Decision. Option B — storage-
state fixtures with a persona
setup project** confirmed as-
recommended.

**Rationale.** (1) Canonical
Playwright pattern; documented
+ widely supported. (2) Every
journey still executes through
the real UI post-login — the
guiding principle is preserved.
(3) Login happens once per
persona per suite run — faster
CI, less flakiness. (4) Test-
only endpoints (Option C)
create an authentication code
path that doesn't exist in
production, introducing a
divergence risk that
acceptance testing is
explicitly meant to prevent.
(5) Personas: `owner`,
`sales_manager`, `advisor`,
`recon_manager`,
`office_manager`,
`bhph_collector`,
`platform_operator` (for
pilot journeys). (6) Storage-
state files live at
`acceptance/.auth/{persona}.json`
— gitignored; regenerated by
the setup project on every
run.

### 5.f `[RESOLVED at SESSION_160 open]` — Server lifecycle for the suite

**Question.** How do the Django
backend + Vite frontend get
started for the suite?

- **Option A** — Playwright
  `webServer` config launches
  both services and waits for
  readiness.
- **Option B** — Docker Compose
  stack booted before Playwright
  runs.
- **Option C** — Assume services
  are already running
  (developer starts manually).

**Decision. Option A —
Playwright `webServer` with
both services declared**
confirmed as-recommended.

**Rationale.** (1) Zero new
infrastructure — no Docker
Compose file to maintain. (2)
`webServer.reuseExistingServer:
true` in dev + `false` in CI
gives the right ergonomics for
both environments. (3) Backend
spins up on a dedicated test
port (`:8101`) with a
dedicated SQLite test DB, so
the acceptance suite never
touches the dev DB. (4)
Frontend runs `vite preview`
against a production-mode
build in CI (catches build-
only regressions); `vite dev`
locally (faster iteration).
(5) Docker Compose (Option B)
adds a Docker requirement to
CI + local development that
no other part of the project
has today. (6) The `webServer`
config lives inside
`playwright.config.ts`
alongside the browser +
project config — one source
of truth.

### 5.g `[RESOLVED at SESSION_160 open]` — CI integration + artifact posture

**Question.** Where does the
acceptance suite run in CI,
and what artifacts get
produced?

- **Option A** — New GitHub
  Actions job on every PR:
  pilot-critical subset
  always, full suite on `main`
  push.
- **Option B** — Local-only for
  M20; CI integration deferred
  to a future milestone.
- **Option C** — Add to the
  existing backend/frontend CI
  job — one monolithic run per
  PR.

**Decision. Option A —
dedicated job, tiered by PR-
critical vs full** confirmed
as-recommended.

**Rationale.** (1) An
operational contract that
only runs locally is not an
operational contract — it's a
developer preference. (2)
Tiered execution keeps PR
feedback fast: `pilot-critical`
tag on the two most-load-
bearing journeys (owner
morning review + pilot
onboarding) runs on every PR
(~90s target); full six-
journey suite runs on `main`
push (~5–8 min target). (3)
Journey tagging pattern:
`test.describe('Owner morning
review', { tag:
'@pilot-critical' }, ...)`.
(4) Artifacts on failure:
Playwright HTML report
(always), trace
(`trace: 'on-first-retry'`),
video (`video: 'retain-on-
failure'`), screenshot on
failure. (5) Artifacts
uploaded to the GitHub
Actions run for post-mortem
— CI-suitable per Candidate
J's contract. (6) Isolating
the job avoids blocking the
existing unit/integration
jobs when acceptance failures
surface — those jobs still
pass or fail independently,
preserving diagnostic clarity.

### 5.h `[RESOLVED at SESSION_160 open]` — Milestone completion contract + increment sequencing

**Question.** What does "M20 is
shipped" mean, and how are
increments sequenced?

- **Option A** — Ship all six
  journeys in one increment.
- **Option B** — Framework
  substrate only in M20.1;
  each journey in its own
  subsequent increment (six
  increments after M20.1).
- **Option C** — Framework
  substrate + one canonical
  journey in M20.1; subsequent
  increments bundle journeys
  2-per-increment.

**Decision. Option C — framework
+ canonical pilot onboarding
journey in M20.1; subsequent
increments bundle journeys
2-per-increment** confirmed as-
recommended.

**Rationale.** (1) Preserves
Rule 4 (scope discipline —
small complete increments).
(2) M20.1 canonical journey =
**pilot onboarding** —
freshest substrate, most-
documented playbook (M19.5),
most operator-observable, and
exercises both frontend admin
surface and backend endpoints
in one journey. Highest-
signal validation of the
framework itself. (3)
Sequencing after M20.1: M20.2
(owner morning review + sales
manager daily startup — both
dashboard-centric, share
fixtures); M20.3 (recon
workflow + office/accounting
workflow — both operator
back-office); M20.4 (BHPH
collections workflow —
standalone, exercises M12
promise-to-pay + repossession
lifecycle); M20.5 (CI
hardening + close-out +
retrospective). (4) Six total
increments matches M19's
pattern (six increments
across SESSION_153 → 159).
(5) Milestone completion
contract: all six journeys
pass in CI on `main`; pilot-
critical subset passes on
PR; HTML report + trace
artifacts confirmed in the
GitHub Actions run;
retrospective §9 records
the standing question for
M21. (6) The framework-alone
alternative (Option B) risks
landing infrastructure with
no proven operational
contract; the ship-all-at-
once alternative (Option A)
risks a 6-journey debug
marathon at close-out.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin — the
   authoritative brief M20 upgraded)
6. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 + §9 (accounting slot
   designation preserved as M21
   standing question)
7. `docs/CAPABILITY_MATRIX.md`
   §7t (M19 shipped surface —
   the substrate M20 validates)

## 7. Sequencing

**Six increments total.** Confirmed
as-recommended per §0.a §5.h.
Combine increments if
implementation evidence shows a
smaller complete shape; do not
split merely to match this draft.

### Increment 0 (M20.0) — Planning refinement + decision review

**Scope.** SESSION_160 (this
session). §5.a Candidate J
confirmed at open; §5.b–§5.h
drafted with recommendations
for user confirmation before
M20.1 code. Candidate W folded
into Candidate J per
DOC_GOVERNANCE.md §2. Full
memo expansion (this document).

**Deliverable.**
- This planning memo, expanded
  from the M19.6 skeleton.
- §0.a change log with all
  eight §5 decisions resolved.
- Session handoff at
  `docs/handoffs/SESSION_160_m20_inc0_planning.md`.
- `00-START-NEXT-SESSION.md`
  overwritten with M20.1
  priority.

**Backend baseline unchanged:**
4,679 pass, 1 skipped, 0 fail.
Frontend Vitest unchanged: 153
pass.

### Increment 1 (M20.1) — Framework substrate + canonical pilot onboarding journey

**Scope.** Next session
(SESSION_161). Land the M20
tooling substrate + the highest-
signal canonical journey.

**Deliverable.**
- New top-level `acceptance/`
  workspace:
  - `package.json` with
    `@playwright/test` +
    TypeScript devDeps.
  - `playwright.config.ts`
    with `webServer` config
    for backend
    (`manage.py runserver
    0.0.0.0:8101`) + frontend
    (`npm run preview` or
    `npm run dev`), project
    definitions (`setup` +
    one per persona), reporter
    config, artifact config,
    tag filter for
    `@pilot-critical`.
  - `tsconfig.json`.
  - `.gitignore` covering
    `.auth/`,
    `playwright-report/`,
    `test-results/`,
    `node_modules/`.
  - `README.md` — one-page
    contributor onboarding.
- `acceptance/support/auth/`
  — auth setup project logs
  each persona in via the
  real UI, saves storage
  state to
  `acceptance/.auth/{persona}.json`.
- `acceptance/support/seed/`
  — helper to invoke a Django
  management command from a
  Playwright test.
- `acceptance/support/assertions/`
  — first two business-outcome
  assertion helpers (used by
  the pilot onboarding
  journey).
- `dealer_ai/management/commands/seed_journey_pilot_onboarding.py`
  — idempotent seed of a
  `qualified` PilotProspect
  ready to convert; ~5-10
  focused backend tests
  covering idempotency +
  tenant scoping.
- `acceptance/journeys/pilot/onboarding.spec.ts`
  — the canonical journey:
  operator navigates to the
  M19.4 pilot admin section,
  selects the seeded prospect,
  advances the checklist steps
  through readiness_confirmed,
  and the journey asserts
  business outcomes at each
  step (prospect state
  transitions, checklist step
  completions, dealership
  `is_ready=True` at the end).
  Tagged `@pilot-critical`.
- `.github/workflows/acceptance.yml`
  — new job triggered on
  `pull_request` +
  `push` to `main`;
  installs Node + Python +
  Chromium; runs M18 + M19
  seed commands; runs
  Playwright with tag filter
  (`--grep '@pilot-critical'`
  on PR; no filter on `main`);
  uploads HTML report + traces
  + videos on failure.

**Backend baseline target at
M20.1 close:** 4,679 →
~4,684-4,689 pass (delta
command tests). Frontend
Vitest: 153 (unchanged).
Acceptance suite: **1
journey passing on `main` CI +
PR**.

### Increment 2 (M20.2) — Owner morning review + sales manager daily startup

**Scope.** SESSION_162. Two
dashboard-centric journeys
sharing fixtures.

**Deliverable.**
- `seed_journey_owner_morning_review`
  + backend tests
  (idempotency + tenant
  scoping).
- `seed_journey_sales_manager_daily_startup`
  + backend tests.
- `acceptance/journeys/owner/morning_review.spec.ts`
  — tagged `@pilot-critical`.
- `acceptance/journeys/sales_manager/daily_startup.spec.ts`.
- Business-outcome assertion
  helpers extended as needed.

**Acceptance baseline target
at M20.2 close:** **3
journeys** (pilot onboarding +
owner morning review + sales
manager daily startup). Pilot-
critical subset now 2 (pilot
onboarding + owner morning
review). Backend baseline
~4,689 → ~4,699 (delta
command tests).

### Increment 3 (M20.3) — Recon workflow + office/accounting workflow

**Scope.** SESSION_163. Two
operator back-office journeys.

**Deliverable.**
- `seed_journey_recon_workflow`
  + backend tests.
- `seed_journey_office_accounting_workflow`
  + backend tests.
- `acceptance/journeys/recon/workflow.spec.ts`.
- `acceptance/journeys/office/accounting_workflow.spec.ts`.

**Acceptance baseline target
at M20.3 close:** **5
journeys**. Backend baseline
~4,699 → ~4,709.

### Increment 4 (M20.4) — BHPH collections workflow

**Scope.** SESSION_164.
Standalone journey — exercises
M12 promise-to-pay +
repossession lifecycle.

**Deliverable.**
- `seed_journey_bhph_collections_workflow`
  + backend tests.
- `acceptance/journeys/bhph/collections_workflow.spec.ts`.
- Business-outcome assertion
  helpers for the promise-to-
  pay + broken-promise +
  repossession-initiation
  contract.

**Acceptance baseline target
at M20.4 close:** **6
journeys — full suite
authored**. Backend baseline
~4,709 → ~4,714.

### Increment 5 (M20.5) — CI hardening + retrospective + close-out

**Scope.** SESSION_165. Full-
suite CI validation + close-
out documentation +
capability matrix update +
retrospective + M21 skeleton.

**Deliverable.**
- CI job hardening:
  - Verify full-suite
    execution on `main` push
    stays within the ~5–8 min
    target; adjust parallelism
    if needed.
  - Verify pilot-critical PR
    execution stays within
    ~90s target.
  - Confirm artifact upload
    on failure via at least
    one intentionally-
    failing dry-run.
- `docs/CAPABILITY_MATRIX.md`
  §7u — M20 shipped surface:
  new `acceptance/` workspace
  + six journeys + CI job +
  six seed delta commands.
- `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
  covering lessons learned,
  what shipped, deferrals
  reviewed, §9 standing
  question for M21 (is M21
  the return-to-accounting
  milestone? — Candidate A
  preserved as re-entry
  path per discovery rule).
- `docs/roadmap/MILESTONE_21_PLANNING.md`
  skeleton drafted (status:
  draft) with candidate list
  refreshed from M20
  retrospective §9 +
  remaining M19 candidates.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M20 shipped
  status.
- Session handoff at
  `docs/handoffs/SESSION_165_m20_inc5_close.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for SESSION_166 /
  M21.0.
- Coordinated close-out
  commit per M18.6 / M19.6
  pattern.

**Backend baseline target at
M20.5 close:** ~4,714 pass.
Frontend Vitest: 153
(unchanged). Acceptance
suite: **6 journeys passing
on `main` CI + 2 passing on
PR**. Migrations unchanged
`0001`–`0048`. Tenancy
carriers unchanged at 52.
Permission classes unchanged
at 7 (zero-drift streak
nineteen → **twenty**
consecutive milestones).
Frontend operator routes
unchanged at 20.
