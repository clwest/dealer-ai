---
state: active
date: 2026-08-02
last_session_shipped: SESSION_116
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
milestone_11_status: in_progress
next_session: SESSION_117
next_milestone: 11
next_milestone_name: "Sales-side non-chat channels + customer-journey completeness"
next_increment: 4
next_increment_name: "M11.4 — FollowUpCadence + FollowUpTask + Celery-beat scheduling"
---

# Next session — SESSION_117 · Milestone 11 · Increment 4 (M11.4 — FollowUpCadence + FollowUpTask + Celery-beat scheduling)

> **SESSION_116 shipped M11.3 —**
> new `DealWriteup` entity + tenancy
> carrier (35 → 36) +
> `services/deal_writeups/` package
> with three verbs (`record` /
> `approve` / `hand_off_to_fandi`) +
> three DRF endpoints under
> `admin/deal-writeups/` + 33
> focused tests (target ~25). The
> handoff verb server-side auto-
> creates a matching M10.1
> CreditApplication per §5.e
> Option A; two implementation-time
> micro-decisions recorded in
> `MILESTONE_11_PLANNING.md` §0.a
> (default `source_format`
> `tablet`; four-square terms
> summarized into CA `notes`).
>
> **Backend baseline: 3,781 → 3,814
> (+33, zero regressions).**
> Frontend baseline: **51**
> (unchanged; M11.3 backend-only).
> Migrations `0001`–`0034`. DRF
> admin surface **69 → 72**.
> Tenancy carriers **35 → 36**.
> Permission classes **8**
> (unchanged — reused M4
> `IsSalesManagerOrOwnerAtActiveDealership`).
> Streak still **35 as-recommended
> M5.1 → M11.1** (planning-time
> decisions only; implementation-
> time micro-decisions don't
> count against it per M10 §9).

## First thing SESSION_117 must do

### 1. Confirm §5.d Option A still fits

Per `MILESTONE_11_PLANNING.md`
§0.a (M11.1 amendment), **§5.d
Option A** (two-entity model —
`FollowUpCadence` header +
`FollowUpTask` rows, queryable
individually) was confirmed at
SESSION_114 open. No new
planning decisions block M11.4.

M11.4 is the first M11 increment
that touches the Celery-beat
substrate (M7). At implementation
time three micro-decisions are
likely to surface — record any
of them in §0.a per the M11.3
precedent:

- **Cadence templates.** The plan
  names six named schedules
  (`24hr`, `1wk`, `30day`,
  `90day`, `6mo`, `1yr`). Are
  these fixed constants
  (LEAD_CADENCE_TEMPLATES) or
  operator-configurable rows?
  Default: fixed constants
  matching the M11.1 vocab-set
  pattern (planning-decision-
  worthy; expand later if
  needed).
- **Celery-beat schedule
  ownership.** Beat schedules
  can be Python-code
  (`CELERY_BEAT_SCHEDULE`) or
  DB-backed
  (`DatabaseScheduler`, already
  configured per M7).
  Recommendation: use the
  existing DatabaseScheduler +
  per-lead schedule rows so
  runtime schedule mutations
  don't require a redeploy.
- **Task state transitions.**
  `pending` → `completed` /
  `skipped` — is `skipped`
  operator-triggered only, or
  auto-triggered after N days
  past `due_at`? Default:
  operator-triggered only at
  M11.4; auto-skip is a
  separate follow-on decision.

### 2. Verify starting state

- `git status` clean (M11.3
  commit landed at SESSION_116
  close).
- `git log --oneline -3` — top
  should be the M11.3 commit.
- `python3 manage.py test dealer_ai`
  → **3,814 pass, 1 skipped, 0
  fail**.
- `python3 manage.py check`
  clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `redis-cli ping` → `PONG`.

## What M11.4 delivers

Per `MILESTONE_11_PLANNING.md`
§1.4 + §5.d + §7 M11.4:

- **New `FollowUpCadence` model.**
  - `dealership` FK CASCADE
    (tenancy carrier; extend
    36 → 37).
  - `lead` FK to `CustomerLead`
    CASCADE.
  - `template` CharField with
    fixed vocab (`24hr` / `1wk`
    / `30day` / `90day` / `6mo`
    / `1yr` — see decision
    surface above).
  - `started_at` datetime.
  - `is_active` boolean (paused
    when lead closes / opts
    out).
- **New `FollowUpTask` model.**
  - `dealership` FK CASCADE
    (tenancy carrier; extend
    37 → 38).
  - `cadence` FK to
    `FollowUpCadence` CASCADE.
  - `due_at` DateTimeField
    indexed.
  - `state` CharField vocab
    `pending` / `completed` /
    `skipped`.
  - `completed_by_user` FK to
    User SET_NULL.
  - `notes` TextField.
- **Celery-beat scheduling.**
  On `FollowUpCadence` create,
  the M7 substrate seeds
  `FollowUpTask` rows at the
  template's offsets. A M7
  Celery-beat entry runs
  daily to surface tasks with
  `due_at <= now()` +
  `state=pending` to the
  operator queue (or fire the
  M3.3 `services/follow_up.py`
  drafting pattern, if the
  planning decision is auto-
  drafting).
- **New `services/follow_ups/`
  package** (mirrors M11.1 /
  M11.2 / M11.3 layout).
- **Verbs (three or four):**
  - `start_cadence(lead,
    template)` — creates the
    cadence + seeds tasks.
  - `complete_task(task,
    completed_by_user)` — sets
    state=completed.
  - `skip_task(task,
    completed_by_user)` — sets
    state=skipped.
  - `pause_cadence(cadence)` —
    sets is_active=False (halts
    future beat surfacing).
- **Endpoints (four):**
  - `POST /admin/follow-up-cadences/`
  - `POST /admin/follow-up-tasks/<pk>/complete/`
  - `POST /admin/follow-up-tasks/<pk>/skip/`
  - `POST /admin/follow-up-cadences/<pk>/pause/`
  - (optional GET) `GET /admin/follow-up-tasks/`
    with `?due_before=` filter
    for operator queue.
- **~30 focused tests** across
  model / service / endpoint /
  Celery-beat integration
  files (per §5.g "larger —
  includes Celery-beat schedule
  locking").
- **Baseline target 3,814 →
  ~3,844.**

### Non-goals for M11.4

- ❌ No be-back (M11.5).
- ❌ No frontend at M11.4
  (M11.6).
- ❌ No modification of M1-M11.3
  business logic.
- ❌ No auto-skip of stale tasks
  (deferred decision — M11.4
  is operator-triggered only).
- ❌ No SMS / email delivery
  (drafting via M3.3
  `services/follow_up.py`
  suffices at M11.4; delivery
  is a follow-on integration).

## What SESSION_117 should do

### Recommended step sequence

1. **Confirm §5.d + record any
   implementation-time micro-
   decisions in §0.a**
   (candidates above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     §1.4 + §5.d + §7 M11.4.
   - `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
     (previous session).
   - `docs/research/SALES_DEPARTMENT_MAPPING.md`
     §workflow steps 12-15
     (follow-up) + §pains 1, 2,
     15, 16.
   - `backend/dealer_ai/services/follow_up.py`
     (M3.3 drafting pattern —
     M11.4 adds scheduling on
     top).
   - `backend/dealer_ai/services/deal_writeups/`
     (M11.3 verb pattern to
     mirror).
   - `backend/dealer_freedom/celery.py`
     + `backend/dealer_ai/services/jobs/`
     (M7 Celery substrate).
   - Existing Celery-beat
     schedule config (four
     scheduled task families
     since M7).

3. **Verify starting state**
   (§2 above).

4. **Draft (in order):**
   - `FollowUpCadence` +
     `FollowUpTask` models +
     tenancy carrier extension
     (36 → 38).
   - Migration `0035`.
   - `services/follow_ups/`
     package with four verbs.
   - Celery-beat entry for
     daily task surfacing.
   - `views_follow_ups.py` +
     endpoints.
   - URL routes.
   - ~30 focused tests
     (including Celery-beat
     schedule-locking test).

5. **Full-suite verification.**
   Target 3,814 → ~3,844.

6. **Ship handoff at
   `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M11.5 priority
   (BeBack tracking).

## Explicit non-goals for SESSION_117

- ❌ Do NOT ship M11.5-M11.7
  scope.
- ❌ Do NOT modify M1-M11.3
  business logic.
- ❌ Do NOT force-push or amend
  the M11.1 / M11.2 / M11.3
  commits.

## NEXT TASK

Start SESSION_117 with (a)
verifying §5.d Option A still
fits + recording any
implementation-time micro-
decisions in §0.a, (b) the
read-first list, (c) starting-
state verification, then (d)
`FollowUpCadence` +
`FollowUpTask` models +
tenancy carrier extension (36 →
38) + migration + service
package with four verbs +
Celery-beat entry + endpoints +
~30 tests including Celery-beat
schedule-locking coverage.
Target baseline 3,814 → ~3,844.
Ship the M11.4 handoff.

Backend baseline at SESSION_117
close: **~3,844 pass**.
Frontend baseline: unchanged
(no frontend at M11.4).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 + M11.3
   amendments)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
   (this session's close)
8. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
9. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
10. `docs/CAPABILITY_MATRIX.md` §7k
11. `docs/research/SALES_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_116 — M11.3 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0034`. Test baseline:
  **3,814 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 51 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled
  task families registered
  (M11.4 will add a fifth).
- **Milestones shipped:** M1 →
  **M10**. M11 in progress
  (M11.1 + M11.2 + M11.3
  shipped).
- **DRF admin surface:** **72**
  (69 + M11.3's three
  DealWriteup endpoints).
- **Frontend operator routes:**
  **11** (unchanged; M11.3
  backend-only).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` package +
  `services/leads/` (M11.1) +
  `services/test_drives/`
  (M11.2) + `services/deal_writeups/`
  (M11.3).
- **Tenancy carriers:** **36**
  (35 → 36 for DealWriteup).
- **Permission classes:** **8**
  (unchanged).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  unchanged.
- **Deterministic rules:**
  unchanged.
- **`CustomerLead.channel`:** 5+1
  vocab (chat / walk_in / phone
  / listing_form / referral /
  other); historical rows
  backfilled to `chat` (M11.1
  migration).
- **Webhook adapter registry:**
  `{"generic": ...}` (M11.1;
  extensible).
- **`TestDrive` FK shape:**
  mandatory both `CustomerLead`
  + `Vehicle` (M11.2 §5.c
  Option A).
- **`DealWriteup` handoff flow:**
  approve → hand_off_to_fandi
  auto-creates M10.1
  CreditApplication (M11.3
  §5.e Option A). Idempotent
  per writeup (refuses re-
  handoff via
  `WriteupAlreadyHandedOffError`).
- **Milestone 11 next:** M11.4
  `FollowUpCadence` +
  `FollowUpTask` + Celery-beat
  scheduling. Two new tenancy
  carriers (36 → 38). ~30
  tests. Baseline 3,814 →
  ~3,844.
