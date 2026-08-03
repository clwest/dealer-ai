---
state: active
date: 2026-08-02
last_session_shipped: SESSION_163
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
next_session: SESSION_164
next_milestone: 20
next_milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
next_increment: 4
next_increment_name: "M20.4 — BHPH collections workflow journey"
---

# Next session — SESSION_164 · Milestone 20 · Increment 4 (M20.4 — BHPH collections workflow)

> **M20.3 shipped at SESSION_163.** Two
> back-office journeys added: recon
> workflow + office/accounting workflow.
> New persona: `recon_manager`. Office
> journey reuses the existing `owner`
> persona (dealer_owner is sufficient
> for M13/M14/M17 accounting endpoints).
> Two new seed delta commands + **20**
> backend tests. Two new assertion
> helpers (recon + accounting).
>
> **Local acceptance dry-run:
> 10 passed (16.4s)** — 5 setup steps +
> 5 journeys. Framework is proven end-
> to-end across four distinct persona
> workflows on the shipped M1–M19 UI.
>
> **Backend baseline:** 4,721 → **4,741
> pass** (+20). Frontend Vitest: **153
> pass** (unchanged). Zero drift on
> migrations (0048), tenancy carriers
> (52), permission classes (7 —
> zero-drift streak intact at nineteen),
> DRF admin (113), frontend routes
> (20).
>
> **Four §0.a M20.3 decisions** captured
> implementation-time choices: (1)
> accounting journey reuses `owner`
> persona; (2) recon seed uses direct
> ORM object creation matching the
> established test-fixture pattern; (3)
> API response envelopes need
> unwrapping in helpers; (4) recon
> journey UI settle signal via
> reconsideration button.
>
> **SESSION_164 opens M20.4** — the BHPH
> collections workflow journey. This
> is a standalone journey exercising
> M12 promise-to-pay + repossession
> lifecycle. **Scope caveat: verify
> shipped frontend UI first before
> designing the full journey. If some
> steps of the promise-to-pay →
> broken-promise → repossession-
> initiation flow don't have shipped
> UI, narrow the journey scope + record
> as §0.a decisions.**

## First thing SESSION_164 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top should
  be the M20.3 shipped commit.
- `python3 manage.py test dealer_ai`
  → **4,741 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Confirm acceptance suite still green

Local dry-run before adding M20.4:

```bash
cd acceptance
rm -f ../backend/db.acceptance.sqlite3
rm -rf .auth playwright-report test-results
mkdir -p .auth
npm test
```

Expect **10 passed**. If red, fix
before layering M20.4 code.

### 3. Explore the BHPH collections surface

Before authoring the seed + journey,
map the shipped surfaces:

- Which routes render BHPH collections?
  Check `frontend/src/pages/` for
  `DealerAiBhphNoteDetail`,
  `DealerAiBhphNotes`, etc.
- Which components render:
  - The BHPH notes list?
  - Note detail with payment history?
  - Recording a promise-to-pay?
  - Marking a promise-to-pay as
    kept or broken?
  - Initiating repossession?
- Backend endpoints in `views.py`
  or `views_bhph*.py`.
- Service verbs in
  `services/bhph_*/` — signatures
  for `record_promise_to_pay`,
  `mark_promise_broken`,
  `initiate_repossession`.
- ROLE_* constant gating access
  (probably `ROLE_COLLECTIONS`
  per M12 auth).

**Verify shipped UI coverage** for
every step the M20 planning §5.h
lists ("promise-to-pay → broken
promise → repossession initiation").
Any missing UI narrows the journey
scope to what's actually clickable.

### 4. Ship the BHPH seed delta command + backend tests

`seed_journey_bhph_collections_workflow.py`:
- Provisions the `acceptance-bhph-
  collector` user with
  `ROLE_COLLECTIONS` (or the
  closest available role) at the
  default dealership.
- Plants a BHPH note with a
  payment coming due today +
  (optionally) a promise-to-pay
  ready to be broken.
- Idempotent + `--reset`.
- ~5-10 focused backend tests.

### 5. Ship the BHPH journey spec

`acceptance/journeys/bhph/collections_workflow.spec.ts`:
- BHPH collector lands on the
  collections surface.
- Reviews the day's book.
- Records a promise-to-pay (if UI
  shipped).
- Marks a broken promise (if UI
  shipped).
- Initiates repossession on a
  broken promise (if UI shipped).
- Business-outcome assertions
  target the M12 BHPH admin API
  surface.

Scope any step down or defer per
§0.a if the UI isn't shipped.

### 6. Extend personas + auth setup

New persona: `bhph_collector` in
`personas.ts`. Extend
`login.setup.ts` with the setup
step + register the new seed in
`SEED_COMMANDS`. Add project entry
in `playwright.config.ts`.

### 7. Extend assertion helpers

Add
`acceptance/support/assertions/bhph.ts`
with business-outcome assertion
helpers for promise-to-pay state +
repossession initiation.

### 8. Ship the M20.4 handoff

- `docs/handoffs/SESSION_164_m20_inc4_bhph_journey.md`.
- Coordinated commit per the M20.1/
  M20.2/M20.3 pattern.

## Non-goals for SESSION_164

- ❌ Do NOT modify any existing
  backend service verb, endpoint,
  or migration.
- ❌ Do NOT modify any existing
  frontend route or component
  (except selector-stability fixes
  surfaced by the M20.3 or M20.4
  dry-run, recorded as §0.a).
- ❌ Do NOT add screenshot
  comparison or pixel-perfect
  visual regression.
- ❌ Do NOT ship journeys beyond
  the BHPH journey (M20.5 is
  close-out).
- ❌ Do NOT force-push, amend, or
  push to origin (M20.5 close is
  when the coordinated push
  happens).

## Baseline expected at close

- **Backend:** 4,741 → ~4,750-4,760
  pass (M20.4 seed command tests).
- **Frontend Vitest:** 153
  (unchanged).
- **Migrations:** unchanged
  `0001`–`0048`.
- **Tenancy carriers:** unchanged
  at 52.
- **Permission classes:** unchanged
  at 7 (zero-drift streak still
  intact at nineteen; extends to
  twenty at M20.5 close).
- **DRF admin surface:** unchanged
  at 113.
- **Frontend operator routes:**
  unchanged at 20.
- **Acceptance suite:** **6
  journeys** (pilot onboarding +
  owner morning review + sales
  manager daily startup + recon
  workflow + office/accounting
  workflow + BHPH collections
  workflow). Pilot-critical subset
  unchanged at **2**.

## NEXT TASK

Start SESSION_164 with (a) starting-
state verification, (b) confirm
acceptance suite still green with
10 passing journeys, (c) explore
the BHPH collections shipped
surface + narrow scope where UI
missing, (d) ship the BHPH seed
delta command + backend tests, (e)
ship the BHPH journey spec + new
persona + assertion helpers, (f)
ship the M20.4 handoff.

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
8. `docs/handoffs/SESSION_163_m20_inc3_backoffice_journeys.md`
   (M20.3 shipped)
9. `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`
   (M20.2 shipped)
10. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
    (M20.1 framework substrate)
11. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
    (M20.0 planning close)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_163 — M20.3 shipped)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0048`.
  Test baseline: **4,741 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):**
  Playwright 1.49 + TS 5.6
  operational; **five journeys**
  green end-to-end (pilot
  onboarding + owner morning
  review + sales manager daily
  startup + recon workflow +
  office/accounting workflow).
  Full dry-run: **10 passed in
  16.4s**.
- **Acceptance (CI):** wired via
  `.github/workflows/acceptance.yml`.
  First actual CI run pending the
  M20.5 push.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled
  task families registered**.
- **Milestones shipped:** M1 →
  **M19**. M20 in-progress (M20.0
  + M20.1 + M20.2 + M20.3 shipped;
  M20.4–M20.5 pending).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all M1–M19
  packages unchanged. M20 adds no
  service verbs. Five management
  commands
  (`seed_journey_pilot_onboarding`
  + `seed_journey_owner_morning_review`
  + `seed_journey_sales_manager_daily_startup`
  + `seed_journey_recon_workflow`
  + `seed_journey_office_accounting_workflow`).
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
  framework + M20.2 dashboard
  journeys + M20.3 back-office
  journeys shipped. Two increments
  remaining (M20.4 BHPH + M20.5
  close-out) per §7 sequencing.
- **Planning-time streak:** **86
  as-recommended M5.1 → M20.0**
  across eleven consecutive
  milestones.
- **Acceptance-suite journeys:** 5
  authored (pilot onboarding [
  `@pilot-critical`] + owner
  morning review [`@pilot-critical`]
  + sales manager daily startup +
  recon workflow + office/
  accounting workflow).
- **Guiding principle for M20
  implementation:** business
  outcomes through real UI on
  deterministic seeded state; not
  UI automation.
