---
state: active
date: 2026-08-01
last_session_shipped: SESSION_087
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: planning
next_session: SESSION_088
next_milestone: 7
next_milestone_name: "Async infrastructure"
next_increment: 1
next_increment_name: "M7.1 — Celery + Redis infrastructure"
---

# Next session — SESSION_088 · Milestone 7 · Increment 1 (M7.1 — Celery + Redis + observability)

> **SESSION_087 shipped M6 closeout + M7 planning +
> coordinated commit + push.** All M6.1–M6.6 stages
> committed and pushed to origin/main in one
> coordinated push per user directive.
>
> **Backend baseline: 2,948 pass, 1 skipped, 0 fail**
> (unchanged — M6.6 was documentation-only). Frontend
> `tsc --noEmit` + `vite build` clean.
>
> **SESSION_088 opens M7.1 — Celery + Redis
> infrastructure + observability substrate.** Django
> Celery app wiring + `django-celery-beat` scheduler
> + `@instrumented_task` decorator + `JobRunLog`
> model + migration `0020`. **NO scheduled job
> bodies yet** — infrastructure only. Job bodies
> land in M7.2–M7.5.

## First thing SESSION_088 must do — CONFIRM THE FIVE §9 DECISIONS

Before any code lands, the user needs to confirm (or
override) five load-bearing decisions from
`MILESTONE_7_PLANNING.md` §9:

1. **§5.a — Broker choice.** Recommendation: **Option
   A (Redis)** per VCP mandate.
2. **§5.b — Task queue framework.** Recommendation:
   **Option A (Celery)** per VCP mandate.
3. **§5.c — Aging snapshot strategy.** Recommendation:
   **Option A** (persist snapshots via new
   `StageAgingSnapshot` model + scheduled job).
4. **§5.d — Photo retention threshold.**
   Recommendation: **Option A** (fixed 30 days for
   v1; per-dealer configurability deferred).
5. **§5.e — Job-run observability substrate.**
   Recommendation: **Option A** (new `JobRunLog`
   Django model).

**Do not write M7.1 code until these are confirmed or
overridden.** If the user overrides any decision,
amend `MILESTONE_7_PLANNING.md` narrowly at session
top (per SESSION_075 precedent — §0.a change-log
entry) before implementation.

## What M7.1 delivers

**Infrastructure only.** No scheduled job bodies.

### Celery app + broker wiring

- **New `backend/dealer_kit/celery.py`** — Celery app
  instance, autodiscovery for `services/**/tasks.py`
  modules, Beat schedule import.
- **New `backend/dealer_kit/__init__.py` extension** —
  ensure Celery app loads with Django (per Django-
  Celery docs pattern).
- **Settings additions:**
  - `CELERY_BROKER_URL` from
    `settings.REDIS_URL` env var (default
    `redis://localhost:6379/0`).
  - `CELERY_RESULT_BACKEND` same.
  - `CELERY_TASK_ALWAYS_EAGER = _is_running_tests()`
    (test-only synchronous mode — mirrors M5.5
    signal-registration pattern).
  - `CELERY_BEAT_SCHEDULE = {}` (empty for M7.1;
    filled per-increment).
- **`requirements.txt`:** `celery[redis]`,
  `django-celery-beat`, `redis`.

### `@instrumented_task` decorator

Shared decorator that wraps every Celery task with
uniform:

- Structured log on start (task name + args + kwargs).
- Structured log on end (duration + status).
- `JobRunLog` model write on both success + failure.
- Retry-on-transient-error policy (network / DB
  deadlock → retry with exponential backoff, max 3).
- Fail-fast-on-programming-error (raise + log).

### `JobRunLog` model + migration `0020`

Per §5.e Option A user-confirmed. Fields:

- `id` (BigAutoField).
- `task_name` (CharField).
- `status` (`started` / `succeeded` / `failed` /
  `retried`).
- `started_at`, `ended_at` (DateTimeField).
- `duration_ms` (PositiveIntegerField nullable).
- `error_message` (TextField blank — nonblank on
  failure).
- `args_summary` (CharField max_length=255 —
  truncated repr of args + kwargs for audit; NOT
  the full payload, which may contain sensitive
  data).
- `dealership` FK (nullable — jobs may or may not
  be tenant-scoped).
- Cross-tenant `clean()` when `dealership` is
  populated + the task-side context implies a
  tenant.

Extended `_TENANT_CARRIER_MODEL_NAMES` 19 → 20 if
`JobRunLog` is tenant-scoped (probably yes —
per-tenant job history is useful for M8 dashboards).

### Non-goals for M7.1

- ❌ No scheduled job bodies (M7.2–M7.5).
- ❌ No Beat schedule entries (empty schedule).
- ❌ No operator UI for job history (deferred; log
  inspection acceptable for v1 per roadmap).
- ❌ No Prometheus integration (Option B deferred).

## What SESSION_088 should do

### Recommended step sequence

0. **Confirm the five §9 decisions with the user.**
   Do NOT write code until every
   `[NEEDS-DECISION-BEFORE-M7.1]` item is resolved.

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_7_PLANNING.md` — §1.1,
     §1.7, §5.a–§5.e, §7 M7.1.
   - `docs/handoffs/SESSION_087_m6_closeout.md`
     (this session).
   - `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md` §6
     lessons (M6 lessons carry into M7).
   - `backend/dealer_kit/settings.py` — where the
     Celery config lands.
   - `backend/dealer_ai/apps.py` — test-only signal
     pattern to mirror for
     `_is_running_tests()`.
   - `backend/dealer_ai/models.py` — VehicleStage
     shape as template for `JobRunLog`.

2. **Verify starting state.**
   - `git status` clean (M6.1–M6.6 committed +
     pushed at SESSION_087 close).
   - `python3 manage.py test dealer_ai` → **2,948
     pass, 1 skipped, 0 fail.**
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check
     --dry-run` → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.
   - **New:** `redis-cli ping` returns `PONG` (or
     start Redis via `brew services start redis` /
     `docker run redis`).

3. **Install Celery + Redis deps.**

4. **Wire Celery app + settings.**

5. **Draft `@instrumented_task` decorator + JobRunLog
   model + migration `0020`.**

6. **Extend `_TENANT_CARRIER_MODEL_NAMES`** (if
   JobRunLog is tenant-scoped per §5.e resolution).

7. **Write ~30 focused tests.**

8. **Full-suite verification.** Target 2,948 → ~2,978.
   Zero regressions.

9. **Ship handoff at
   `docs/handoffs/SESSION_088_m7_inc1_infra.md`.**

10. **Overwrite `00-START-NEXT-SESSION.md`** with
    M7.2 priority (floor-plan interest accrual).

## Explicit non-goals for SESSION_088

- ❌ Do NOT write scheduled job bodies — M7.2–M7.5.
- ❌ Do NOT add Beat schedule entries — M7.2+.
- ❌ Do NOT build a job-history UI — deferred.
- ❌ Do NOT integrate Prometheus — deferred (§5.e
  Option B).
- ❌ Do NOT modify any M1–M6 substrate beyond
  additive settings extension.

## NEXT TASK

Start SESSION_088 with (a) confirming the five §9
decisions with the user, (b) the read-first list, then
(c) wiring Celery + Redis + `@instrumented_task` +
`JobRunLog`. ~30 focused tests. Target baseline
2,948 → ~2,978. Ship the M7.1 handoff.

Backend baseline at SESSION_088 close: **~2,978 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 7
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_7_PLANNING.md`
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_087_m6_closeout.md`
8. `docs/roadmap/MILESTONE_6_PLANNING.md` (shipped)
9. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 6
11. `docs/CAPABILITY_MATRIX.md` §7g M6 photo + listing
    (M7.5 reaper reuses M6.2 primitives)

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_087 — Milestone 6 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0019`. Test baseline: **2,948 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  + `vite build` clean.
- **Frontend (prod):** NONE.
- **Milestones shipped:** M1 → M6. Milestone 7
  planning drafted.
- **DRF admin surface:** 34 endpoints (21 pre-M6 +
  13 M6.5).
- **Frontend operator routes:** 7 (5 pre-M6 + 2
  M6.5).
- **Public endpoints:** +1 M6.5 showroom.
- **Service surface:** M6 added
  `services/photo_gallery.py` + `services/vehicle_listing.py`
  + extended `services/photo_storage.py` +
  `services/llm_safety.py` +
  `services/vehicle_lifecycle.py` +
  `services/chat_engine.py`.
- **Vehicle read-model:** 4 `@property` accessors
  (unchanged).
- **Tenancy carriers:** 19.
- **`Vehicle.is_available`:** unchanged per §5.e
  Option D.
- **Customer-facing filtering (two-tier gate):**
  batch-query `customer_visible_vehicles()`
  (frontline-only); per-vehicle direct-access
  `customer_lookup_visible_vehicle_by_id/stock`
  (frontline + published listing).
- **AI safety stack:** M4.5 recon-fact scrub fires
  on 3 kinds (`vendor_comm`, `parts_order`,
  `vehicle_listing`).
- **Deterministic rules:** `suggest_transitions`
  composition dispatches at 4 stages (inspection,
  recon, photography, listing).
- **Milestone 7 next:** async infrastructure —
  Celery + Redis + `@instrumented_task` +
  JobRunLog + 4 scheduled job bodies (floor-plan
  interest accrual, aging snapshots, vendor SLA
  warnings, photo tombstone reaper).
