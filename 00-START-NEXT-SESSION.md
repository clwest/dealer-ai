---
state: active
date: 2026-08-02
last_session_shipped: SESSION_117
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
next_session: SESSION_118
next_milestone: 11
next_milestone_name: "Sales-side non-chat channels + customer-journey completeness"
next_increment: 5
next_increment_name: "M11.5 — BeBack tracking + no-show auto-scheduling"
---

# Next session — SESSION_118 · Milestone 11 · Increment 5 (M11.5 — BeBack tracking + no-show auto-scheduling)

> **SESSION_117 shipped M11.4 —**
> two-entity follow-up scheduling
> substrate (`FollowUpCadence` +
> `FollowUpTask`) + four-verb
> `services/follow_ups/` package +
> two-task Celery orchestrator
> wired into Beat at 06:00 daily +
> five DRF admin endpoints + 44
> focused tests (target ~30). Two
> new tenancy carriers (36 → 38).
> Three implementation-time micro-
> decisions recorded in §0.a
> (fixed template constants,
> DatabaseScheduler overlay,
> operator-triggered state
> transitions only).
>
> **Backend baseline: 3,814 → 3,858
> (+44, zero regressions).**
> Frontend baseline: **51**
> (unchanged; M11.4 backend-only).
> Migrations `0001`–`0035`. DRF
> admin surface **72 → 77**.
> Tenancy carriers **36 → 38**.
> Celery-beat task families **4 →
> 5**. Permission classes **8**
> (unchanged). Streak still **35
> as-recommended M5.1 → M11.1**
> (planning-time only).

## First thing SESSION_118 must do

### 1. Resolve M11.5 `[NEEDS-DECISION]` items

Per `MILESTONE_11_PLANNING.md`
§1.5, **no specific §5 decision
was recorded for BeBack at M11.1
open** — the shape was outlined
but not put to a §5 vote. Surface
the following as a §5.g equivalent
and record recommendations in
§0.a before coding:

- **§5.g.1 — BeBack attach shape.**
  Mandatory FK to CustomerLead
  (matches M11.4 pattern) + no FK
  to Vehicle (be-back is about
  returning to the store, not
  necessarily the same vehicle).
  Recommendation: **Option A**
  (mandatory lead FK, no vehicle
  FK).
- **§5.g.2 — Reason vocabulary.**
  Fixed 4+1 vocab per §1.5:
  `test_drive` / `bring_co_signer`
  / `bring_trade_in` / `other`.
  Recommendation: **Option A**
  (matches M11.1 pattern).
- **§5.g.3 — No-show auto-
  scheduling integration.**
  Options: (a) BeBack creation
  auto-starts an M11.4
  FollowUpCadence targeting the
  promise date, (b) BeBack keeps
  its own `follow_up_scheduled_at`
  nullable column with a dedicated
  M11.5 Celery-beat detector that
  transitions state to `no_show`
  when `promised_at + grace
  period` passes without
  `actual_return_at`. Both are
  defensible. Recommendation:
  **Option B** (dedicated M11.5
  Celery detector) — keeps the
  no-show state-transition rule
  narrow to BeBack rather than
  spilling into the general
  M11.4 cadence engine.

Record all three recommendations
in §0.a as SESSION_118 M11.5
amendment before writing code.

### 2. Verify starting state

- `git status` clean (M11.4
  commit landed at SESSION_117
  close).
- `git log --oneline -3` — top
  should be the M11.4 commit.
- `python3 manage.py test dealer_ai`
  → **3,858 pass, 1 skipped, 0
  fail**.
- `python3 manage.py check`
  clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `redis-cli ping` → `PONG`.

## What M11.5 delivers

Per `MILESTONE_11_PLANNING.md`
§1.5 + §7 M11.5 (assuming the
§5.g recommendations above are
accepted):

- **New `BeBack` model.**
  - `dealership` FK CASCADE
    (tenancy carrier; extend
    38 → 39).
  - `lead` FK to `CustomerLead`
    CASCADE (mandatory per §5.g.1).
  - `promised_at` DateTimeField
    (when the customer said
    they'd return).
  - `promised_reason` CharField
    with 4+1 vocab per §5.g.2.
  - `actual_return_at` nullable
    DateTimeField.
  - `state` CharField vocab:
    `promised` (default) /
    `returned` / `no_show`.
  - `notes` TextField.
- **New `services/be_backs/`
  package** (mirrors M11.1-
  M11.4 layout).
- **Verbs (three):**
  - `record_be_back(lead,
    promised_at, promised_reason)`.
  - `mark_returned(be_back,
    actual_return_at)` —
    `promised` → `returned`.
  - `mark_no_show(be_back)` —
    used by the Celery
    detector when the promise
    date passes; also usable
    manually.
- **New Celery-beat entry** at
  07:00 project-time daily
  (next slot after M11.4 at
  06:00). Detector task
  transitions `promised` →
  `no_show` when `promised_at +
  grace_period` <= now + no
  `actual_return_at`. Grace
  period configurable via
  settings (default 4 hours).
- **Endpoints (three):**
  - `POST /admin/be-backs/`
  - `POST /admin/be-backs/<pk>/mark-returned/`
  - `POST /admin/be-backs/<pk>/mark-no-show/`
- **~25 focused tests** across
  model / service / endpoint /
  beat detector files.
- **Baseline target 3,858 →
  ~3,883.**

### Non-goals for M11.5

- ❌ No frontend at M11.5
  (M11.6).
- ❌ No modification of M1-M11.4
  business logic.
- ❌ No automatic BeBack
  creation from lead activity
  (operator-triggered only —
  matches M11.4 posture).
- ❌ No auto-start of a M11.4
  FollowUpCadence on BeBack
  create (per §5.g.3 Option B
  recommendation — the
  M11.5 detector owns the
  no-show state machine
  narrowly).

## What SESSION_118 should do

### Recommended step sequence

1. **Confirm the three §5.g
   recommendations above** and
   record in §0.a per M11.3 /
   M11.4 precedent.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     §1.5 + §7 M11.5.
   - `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`
     (previous session).
   - `docs/research/SALES_DEPARTMENT_MAPPING.md`
     §workflow step 15 (be-back
     management) + §pain 15.
   - `backend/dealer_ai/services/follow_ups/tasks.py`
     (M11.4 Celery pattern to
     mirror).
   - `backend/dealer_kit/settings.py::CELERY_BEAT_SCHEDULE`
     (next slot).

3. **Verify starting state**
   (§2 above).

4. **Draft (in order):**
   - `BeBack` model + tenancy
     carrier (38 → 39).
   - Migration `0036`.
   - `services/be_backs/`
     package with three verbs.
   - `services/be_backs/tasks.py`
     — no-show detector +
     orchestrator.
   - Beat entry in settings.
   - `views_be_backs.py` +
     endpoints.
   - URL routes.
   - ~25 focused tests
     including beat detector
     coverage (grace-period +
     already-returned + not-
     yet-promised cases).

5. **Full-suite verification.**
   Target 3,858 → ~3,883.

6. **Ship handoff at
   `docs/handoffs/SESSION_118_m11_inc5_be_back.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M11.6 priority
   (Operator UI).

## Explicit non-goals for SESSION_118

- ❌ Do NOT ship M11.6-M11.7
  scope.
- ❌ Do NOT modify M1-M11.4
  business logic.
- ❌ Do NOT force-push or amend
  the M11.1-M11.4 commits.

## NEXT TASK

Start SESSION_118 with (a)
confirming the three §5.g
recommendations + recording in
§0.a, (b) the read-first list,
(c) starting-state verification,
then (d) `BeBack` model +
tenancy carrier extension (38 →
39) + migration + service
package with three verbs +
Celery detector + Beat entry
at 07:00 + endpoints + ~25
tests. Target baseline 3,858
→ ~3,883. Ship the M11.5
handoff.

Backend baseline at SESSION_118
close: **~3,883 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 + M11.3 + M11.4
   amendments)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`
   (this session's close)
8. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
9. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
10. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
11. `docs/CAPABILITY_MATRIX.md` §7k
12. `docs/research/SALES_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_117 — M11.4 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0035`. Test baseline:
  **3,858 pass**, 1 skipped, 0
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
  DatabaseScheduler. **5
  scheduled task families
  registered** (M7.2-M7.5 at
  02:00-05:00 + M11.4 at
  06:00).
- **Milestones shipped:** M1 →
  **M10**. M11 in progress
  (M11.1 + M11.2 + M11.3 +
  M11.4 shipped).
- **DRF admin surface:** **77**
  (72 + M11.4's five follow-up
  endpoints).
- **Frontend operator routes:**
  **11** (unchanged; M11.4
  backend-only).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` +
  `services/leads/` (M11.1) +
  `services/test_drives/`
  (M11.2) + `services/deal_writeups/`
  (M11.3) + `services/follow_ups/`
  (M11.4).
- **Tenancy carriers:** **38**
  (36 → 38 for FollowUpCadence
  + FollowUpTask).
- **Permission classes:** **8**
  (unchanged).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  unchanged.
- **Deterministic rules:**
  unchanged.
- **`CustomerLead.channel`:** 5+1
  vocab; historical rows
  backfilled to `chat` (M11.1
  migration).
- **Webhook adapter registry:**
  `{"generic": ...}` (M11.1;
  extensible).
- **`TestDrive` FK shape:**
  mandatory both `CustomerLead`
  + `Vehicle` (M11.2).
- **`DealWriteup` handoff flow:**
  approve → hand_off_to_fandi
  auto-creates M10.1 CA
  (M11.3). Idempotent per
  writeup.
- **`FollowUp*` shape:** two
  entities per §5.d Option A.
  Six fixed template constants
  with per-template offset
  schedules. Operator-triggered
  state transitions only.
  Beat surfacer read-only at
  06:00 daily.
- **Milestone 11 next:** M11.5
  BeBack tracking + no-show
  auto-scheduling. New tenancy
  carrier (38 → 39). New
  Celery-beat entry at 07:00.
  ~25 tests. Baseline 3,858
  → ~3,883.
