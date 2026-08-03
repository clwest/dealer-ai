---
state: active
date: 2026-08-02
last_session_shipped: SESSION_157
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
milestone_19_status: in-progress
next_session: SESSION_158
next_milestone: 19
next_milestone_name: "Founding Dealer Pilot Onboarding"
next_increment: 5
next_increment_name: "M19.5 — Playbook doc + first end-to-end dry-run"
---

# Next session — SESSION_158 · Milestone 19 · Increment 5 (M19.5 — Playbook + dry-run)

> **SESSION_157 shipped M19.4 —**
> deferred pilot inventory-import
> endpoint + full frontend admin
> surface. Fifth endpoint
> `POST /admin/pilots/<slug>/inventory/import/`
> (multipart CSV, DRF `FileField`).
> New `<PilotOnboardingSection>`
> component (~530 lines) embedded in
> `DealerAdmin.tsx` — list, create
> form, checklist stepper, CSV upload
> with rejected-rows details,
> terminate confirmation. Two §0.a
> M19.4 implementation-time decisions
> recorded — `FileField` overlay + no
> new operator route (extend `/dealer-
> ai-admin` in place). Two discovered
> implementation gaps fixed as part
> of the increment: multipart parser
> registration and bytes-mode
> `UploadedFile` handling in the M19.2
> wrapper's `_read_csv_rows` helper.
>
> **Backend baseline: 4,659 → 4,669
> pass** (+10 tests, 0 regressions).
> **Frontend Vitest: 140 → 153 pass**
> (+13 tests, 0 regressions).
> Migrations `0043`–`0048` (unchanged).
> Tenancy carriers 52 (unchanged).
> DRF admin surface **112 → 113**
> (+1 inventory-import endpoint).
> Frontend operator routes 20
> (unchanged per §0.a M19.4 decision
> 2). Permission classes 7 (unchanged
> — zero-drift streak now **eighteen
> consecutive milestones** M10 →
> M19.4). Celery-beat task families
> 10 (unchanged).
>
> **SESSION_158 opens M19.5 —
> playbook + first end-to-end
> dry-run.** Ships the operator
> reference doc walking Chris
> through a fresh pilot from
> prospect intake to readiness_
> confirmed + a dry-run test
> exercising every M19.1-M19.4 verb
> and endpoint. Single mixed
> doc + test increment;
> ~5-10 focused tests.

## First thing SESSION_158 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M19.4 commit.
- `python3 manage.py test dealer_ai`
  → **4,669 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Surface §0.a M19.5 micro-decisions

Two candidate micro-decisions likely
at open:

1. **Dry-run as test vs management
   command.** Options:
   (a) Django TestCase in
   `tests/test_m195_pilot_dry_run.py`
   — atomic, part of the suite;
   (b) Django management command
   `manage.py pilot_dry_run` +
   thin smoke test — usable as an
   operator diagnostic.
   **Recommendation:** (a) TestCase.
   The dry-run's value is codified
   contract verification across
   M19.1-M19.4; TestCase gives us
   that + CI signal. A management
   command layer can ship later if
   Chris wants an operator smoke
   button.
2. **Playbook screenshot posture.**
   Options:
   (a) embed literal screenshots
   captured from a local dev run;
   (b) narrate step-by-step with
   selector labels only (no
   images); (c) both.
   **Recommendation:** (b) — text +
   selector labels. Screenshots
   go stale immediately as UI
   iterates; textual step
   descriptions with
   `data-testid` references stay
   in sync with the code.

Present both briefly at open;
expect confirm-as-recommended per
the 85-milestone streak posture.
Record as §0.a M19.5 amendments.

## What M19.5 delivers

Per `MILESTONE_19_PLANNING.md` §7
M19.5:

### Doc

- **New:**
  `docs/PILOT_ONBOARDING_PLAYBOOK.md`
  — narrative step-by-step
  operator reference. Covers:
  - Pre-conversion (demo →
    prospect qualification).
  - `POST /admin/pilots/create/`
    walk-through with expected
    outcomes.
  - Each of the seven checklist
    steps: what Chris does IRL,
    what the checklist advance
    call posts, what to check
    after.
  - CSV upload workflow +
    interpreting rejected-row
    surfacing.
  - Readiness confirmation as
    the final gate.
  - Terminate playbook (archive
    for post-mortem, cleanup for
    PII-remove).
  - Links to
    `PILOT_INVENTORY_TEMPLATE.md`
    + `MILESTONE_19_PLANNING.md`
    + relevant handoff pointers.

### Dry-run test

- **New:**
  `tests/test_m195_pilot_dry_run.py`
  — a single end-to-end scenario
  driving:
  - `create_pilot_dealership` →
    verify pilot + checklist + auto-
    fired `dealership_created` step.
  - Each of the six remaining
    checklist steps via `advance_step`
    (in `PILOT_ONBOARDING_STEP_ORDER`
    order), asserting `is_ready`
    flips only on
    `readiness_confirmed`.
  - `import_pilot_inventory` with a
    small CSV (accepted + rejected
    rows).
  - `list_pilot_dealerships`
    surfacing the created pilot.
  - `terminate_pilot(mode='archive')`
    — verify pilot leaves the active
    list but child rows survive.
- Auxiliary tests (~4-9):
  - Prospects state machine E2E
    (prospect → qualified →
    converted).
  - Endpoint E2E: hit each of the
    five M19.3+M19.4 admin
    endpoints in sequence.
  - Zero-drift assertions
    (`>=` 113 endpoint, no new
    permission class,
    `>=` 52 carriers).

### Non-goals for M19.5

- ❌ No new backend business
  logic.
- ❌ No new frontend components.
- ❌ No new migrations.
- ❌ No new tenancy carriers.
- ❌ No new permission classes.

## Backend baseline target

**4,669 → ~4,674-4,679 pass**
(+5-10 tests, 0 regressions).
Frontend Vitest: 153 (unchanged
— no frontend at M19.5).

## Explicit non-goals for SESSION_158

- ❌ Do NOT modify M1-M19.4
  business logic.
- ❌ Do NOT force-push or amend
  earlier commits.

## NEXT TASK

Start SESSION_158 with (a)
surfacing the two §0.a M19.5
micro-decisions (dry-run as
TestCase vs management command
+ playbook screenshot posture)
with the user, (b) starting-
state verification, (c)
authoring the playbook doc +
dry-run test per §7 M19.5.
Ship the M19.5 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_157_m19_inc4_frontend_and_import_endpoint.md`
   (this session's handoff)
7. `docs/PILOT_INVENTORY_TEMPLATE.md`
8. `docs/CAPABILITY_MATRIX.md` §7s
9. `backend/dealer_ai/services/pilot_onboarding/`
10. `backend/dealer_ai/views_pilot_onboarding.py`
11. `frontend/src/components/pilots/PilotOnboardingSection.tsx`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_157 — M19.4 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,669 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  M18. M19 in progress: M19.0
  planning + M19.1 substrate +
  M19.2 inventory import + M19.3
  endpoints + M19.4 frontend +
  import endpoint shipped. M19.5
  playbook + dry-run next
  (SESSION_158).
- **DRF admin surface:** **113**
  endpoints (108 → 112 at M19.3;
  112 → 113 at M19.4).
- **Frontend operator routes:**
  **20** — unchanged through M19
  per §0.a M19.4 decision 2.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (seven modules) +
  `services/demo_store/` (ten
  modules including briefs
  package) +
  `services/pilot_onboarding/`
  (six modules; M19.2 wrapper
  extended at M19.4 to accept
  bytes-mode `UploadedFile`
  streams). New at M19.4:
  `frontend/src/components/pilots/PilotOnboardingSection.tsx`.
- **Frontend accounting
  surface:** unchanged from
  M17.
- **Tenancy carriers:**
  **52** (unchanged at M19.4).
- **Permission classes:**
  **7 actual** — zero-drift
  streak **eighteen consecutive
  milestones** (M10 → M19.4).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 19 status:**
  M19.0 planning SHIPPED
  (SESSION_153). M19.1
  substrate SHIPPED
  (SESSION_154). M19.2
  inventory import SHIPPED
  (SESSION_155). M19.3
  endpoints SHIPPED
  (SESSION_156). M19.4
  frontend + import endpoint
  SHIPPED (SESSION_157).
  M19.5 playbook + dry-run
  next (SESSION_158). M19.6
  close-out to follow.
