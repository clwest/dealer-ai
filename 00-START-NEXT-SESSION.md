---
state: active
date: 2026-08-02
last_session_shipped: SESSION_162
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
next_session: SESSION_163
next_milestone: 20
next_milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
next_increment: 3
next_increment_name: "M20.3 — Recon workflow + office/accounting workflow journeys"
---

# Next session — SESSION_163 · Milestone 20 · Increment 3 (M20.3 — recon workflow + office/accounting workflow)

> **M20.2 shipped at SESSION_162.** Two
> new dashboard-centric journeys layered
> onto the M20.1 framework: **owner
> morning review** (tagged
> `@pilot-critical`) + **sales manager
> daily startup**. Two new personas
> (`owner` + `sales_manager`) with real-
> UI login + per-persona storage state.
> Two new seed delta commands +27
> backend tests. Two new dashboard
> business-outcome assertion helpers.
>
> **First M20.1 dry-run happened at
> SESSION_162 open** — surfaced two
> framework-substrate defects that were
> resolved as §0.a M20.2 decisions
> (import.meta.dirname portability + vite
> `--host 127.0.0.1` bind) before layering
> M20.2 code. Two additional §0.a
> decisions captured selector-strategy
> adjustments for the dashboard journeys
> (LeadDetailModal is a plain fixed
> div, not a Radix Dialog; CardTitle is
> a `<div>`, not a semantic heading;
> assignment lives on `/dealer-ai-admin`,
> not the read-only `/dealer-ai-leads`).
>
> **Local acceptance dry-run: 7 passed
> (12.6s)** — 4 setup steps + 3
> journeys. Framework is proven end-to-
> end against the shipped M1–M19 UI.
>
> **Backend baseline:** 4,694 → **4,721
> pass** (+27). Frontend Vitest: **153
> pass** (unchanged). Zero drift on
> migrations (0048), tenancy carriers
> (52), permission classes (7 — zero-
> drift streak intact at nineteen),
> DRF admin (113), frontend routes
> (20).
>
> **SESSION_163 opens M20.3** — two
> operator back-office journeys: recon
> workflow + office/accounting workflow.
> Neither is tagged `@pilot-critical`
> — both run only in the full-suite
> CI on `main` push.

## First thing SESSION_163 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top should
  be the M20.2 shipped commit.
- `python3 manage.py test dealer_ai`
  → **4,721 pass, 1 skipped, 0 fail**.
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

Local acceptance dry-run before
adding M20.3 code:

```bash
cd acceptance
rm -f ../backend/db.acceptance.sqlite3
rm -rf .auth
npm test
```

Expect **7 passed**. If red, fix
before layering M20.3 code.

### 3. Explore the recon + accounting surfaces

Before authoring seeds + journeys, map
the shipped surfaces:

- **Recon workflow** — the operator-
  facing recon UI. Check
  `frontend/src/pages/` for recon-
  related routes; backend
  `services/recon/` verbs; existing
  seed patterns for
  `VehicleAcquisition` /
  `ReconDecision` / vendor dispatch.
- **Office/accounting workflow** —
  end-of-day trial balance surface.
  Check `services/accounting/`
  package, particularly the M17.1
  trial-balance-snapshot endpoints;
  frontend routes at `/dealer-ai-
  accounting/*` or similar.

Both journeys should exercise real
UI paths + validate business outcomes
via the M17.1 + M11 admin API
surfaces.

### 4. Ship two seed delta commands + backend tests

- `dealer_ai/management/commands/seed_journey_recon_workflow.py`
  — plants a fresh
  `VehicleAcquisition` awaiting a
  condition report on a demo/pilot
  dealership. Idempotent via a
  fixture-tag or stable stock
  number.
- `dealer_ai/management/commands/seed_journey_office_accounting_workflow.py`
  — advances yesterday's accounting
  to a state where an end-of-day
  trial balance query is meaningful
  (or plants a specific
  `JournalEntry` fixture).
- Backend tests (~10-20 focused):
  fresh-run provisioning +
  idempotency + `--reset` + tenant
  scoping.

### 5. Ship two journey specs

- `acceptance/journeys/recon/workflow.spec.ts`
  — receive a new acquisition,
  author the condition report,
  advance ReconDecision, dispatch
  to vendor, mark work complete.
  Assertions via recon admin API.
- `acceptance/journeys/office/accounting_workflow.spec.ts`
  — end-of-day trial balance
  review, `as_of` picker
  manipulation, drill into a
  specific posting. Assertions
  via M17.1 trial balance
  snapshot API.

### 6. Extend personas + auth setup

Two new personas:
- `recon_manager` —
  `acceptance-recon-manager` user
  with `recon_manager` role at
  the default dealership. Post-
  login lands at whichever recon
  page is the entry point.
- `office_manager` —
  `acceptance-office-manager`
  user with `office_manager` (or
  the closest available) role.
  Post-login lands at the
  accounting entry point.

Extend `personas.ts`,
`login.setup.ts` (add two setup
steps + register seed commands
in the SEED_COMMANDS list),
`playwright.config.ts` (add two
project entries).

### 7. Extend assertion helpers

Add
`acceptance/support/assertions/recon.ts`
and
`acceptance/support/assertions/accounting.ts`
as needed with business-outcome
assertion helpers.

### 8. Ship the M20.3 handoff

- `docs/handoffs/SESSION_163_m20_inc3_backoffice_journeys.md`.
- Coordinated commit per M19.1 /
  M20.1 / M20.2 pattern.

## Non-goals for SESSION_163

- ❌ Do NOT modify any existing
  backend service verb, endpoint,
  or migration.
- ❌ Do NOT modify any existing
  frontend route or component
  (except selector-stability fixes
  surfaced by the M20.2 or M20.3
  dry-run, recorded as §0.a).
- ❌ Do NOT add screenshot
  comparison or pixel-perfect
  visual regression.
- ❌ Do NOT ship journeys beyond
  the two M20.3 targets — BHPH
  collections is M20.4.
- ❌ Do NOT force-push, amend, or
  push to origin (M20.5 close is
  when the coordinated push
  happens).

## Baseline expected at close

- **Backend:** 4,721 → ~4,731-4,741
  pass (M20.3 seed command tests).
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
- **Acceptance suite:** **5
  journeys** (pilot onboarding +
  owner morning review + sales
  manager daily startup + recon
  workflow + office/accounting
  workflow). Pilot-critical
  subset unchanged at **2**.

## NEXT TASK

Start SESSION_163 with (a) starting-
state verification, (b) confirm
acceptance suite still green with
7 passing journeys, (c) explore the
recon + accounting shipped
surfaces, (d) ship two seed delta
commands + backend tests, (e) ship
two journey specs + two new
personas + assertion helpers, (f)
ship the M20.3 handoff.

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
8. `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`
   (M20.2 shipped)
9. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
   (M20.1 framework substrate)
10. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
    (M20.0 planning close)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_162 — M20.2 shipped)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0048`.
  Test baseline: **4,721 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):**
  Playwright 1.49 + TS 5.6
  operational; three journeys
  green end-to-end (pilot
  onboarding + owner morning
  review + sales manager daily
  startup). Full dry-run: **7
  passed in 12.6s**.
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
  + M20.1 + M20.2 shipped; M20.3–
  M20.5 pending).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all M1–M19
  packages unchanged. M20 adds no
  service verbs. Three management
  commands
  (`seed_journey_pilot_onboarding`
  + `seed_journey_owner_morning_review`
  + `seed_journey_sales_manager_daily_startup`).
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
  journeys shipped. Three
  increments remaining (M20.3 back-
  office + M20.4 BHPH + M20.5
  close-out) per §7 sequencing.
- **Planning-time streak:** **86
  as-recommended M5.1 → M20.0**
  across eleven consecutive
  milestones.
- **Acceptance-suite journeys:** 3
  authored (pilot onboarding [
  `@pilot-critical`] + owner
  morning review [`@pilot-critical`]
  + sales manager daily startup).
- **Guiding principle for M20
  implementation:** business
  outcomes through real UI on
  deterministic seeded state; not
  UI automation.
