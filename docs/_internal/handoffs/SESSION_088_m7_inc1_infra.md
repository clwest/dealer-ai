---
title: "SESSION_088 handoff — Milestone 7 · Increment 1 (Celery + Redis + observability substrate)"
status: historical
type: handoff
date: 2026-08-01
session: 088
milestone: 7
milestone_status: in-progress
increment: 1
increment_status: shipped
commit: 6ea221d
---

# SESSION_088 — Milestone 7 · Increment 1 (M7.1 — async infrastructure)

## What shipped

The async-infrastructure substrate: Celery app wiring,
Redis broker + result backend, Django-Celery Beat
DB-backed scheduler, the shared `@instrumented_task`
decorator, a `JobRunLog` Django model + migration
`0020`, and 62 focused tests (target ~30).
**Infrastructure only — zero scheduled job bodies, zero
Beat schedule entries.** Job bodies land in M7.2–M7.5.

Also: **five load-bearing decisions confirmed by the
user at session open** (per M7 §7 lesson 8) before any
code was written.

## Session preamble — the five §9 decisions

Per `MILESTONE_7_PLANNING.md` §9, five
`[NEEDS-DECISION-BEFORE-M7.1]` items required user
confirmation before implementation. The user
**confirmed all five recommended options** at session
open ("confirm all five"):

1. **§5.a — Broker: Option A (Redis).** Simple, well-
   supported, minimal ops overhead. VCP mandate.
2. **§5.b — Task queue: Option A (Celery).** Most
   mature Python task queue; well-integrated with
   Django; `django-celery-beat` provides scheduler.
   VCP mandate.
3. **§5.c — Aging snapshot strategy: Option A**
   (persist snapshots via new `StageAgingSnapshot`
   model + scheduled job — deferred to M7.3
   implementation).
4. **§5.d — Photo retention threshold: Option A**
   (fixed 30 days for v1; per-dealer configurability
   deferred — consumed by M7.5 reaper).
5. **§5.e — Job-run observability: Option A** (new
   `JobRunLog` Django model — shipped this
   increment).

No planning amendments were required — the recommended
options were confirmed as-is. No `§0.a change-log`
entry needed.

## New files (M7.1)

1. **`backend/dealer_kit/celery.py`** — module-level
   `celery.Celery("dealer_kit")` app instance.
   `config_from_object("django.conf:settings",
   namespace="CELERY")` binds every `CELERY_*` key
   from Django settings. `autodiscover_tasks()`
   invoked (no tasks registered yet).

2. **`backend/dealer_kit/__init__.py`** — exposes
   `celery_app` at project-package load time (Celery-
   Django integration pattern — imported by
   `manage.py` / `wsgi.py` on Django boot).

3. **`backend/dealer_ai/services/jobs/__init__.py`** —
   package hosting the job-runtime helpers. Public
   surface: `instrumented_task`.

4. **`backend/dealer_ai/services/jobs/instrumentation.py`**
   — the `@instrumented_task` decorator. Wraps
   `@celery.shared_task` with structured logging on
   start / end, `JobRunLog` row creation on start +
   in-place update on end, retry-on-transient-error
   (`ConnectionError`, `TimeoutError`, `OSError` — max
   3 attempts, exponential backoff, jitter), and
   `dealership_id` kwarg propagation to the audit row.

5. **`backend/dealer_ai/migrations/0020_job_run_log.py`**
   — single `CreateModel` operation. Reverse is
   `DeleteModel` (safe — no FK reverse dependencies at
   M7.1 close).

6. **`backend/dealer_ai/tests/test_m7_tenancy_carriers.py`**
   — 5 tests. Locks the 19 → 20 tuple extension +
   autofill wiring for `JobRunLog`.

7. **`backend/dealer_ai/tests/test_m7_celery_app.py`**
   — 11 tests. Locks app name, config binding, test
   posture (`ALWAYS_EAGER=True`), empty Beat schedule,
   DB scheduler, timezone alignment, JSON-only
   serialization.

8. **`backend/dealer_ai/tests/test_m7_job_run_log_model.py`**
   — 16 tests. Field shape, status vocabulary, Meta
   ordering + composite index, string repr, ORM
   round-trip, `SET_NULL` on tenant delete.

9. **`backend/dealer_ai/tests/test_m7_instrumented_task.py`**
   — 30 tests. Single-row-per-invocation, status
   transitions, duration, args_summary truncation,
   dealership_id propagation, return value passthrough,
   exception re-raise, retry-policy classification,
   helper truncation math, Celery registration.

## Modified files (M7.1)

1. **`backend/requirements.txt`** — pinned
   `celery[redis]==5.5.3`, `django-celery-beat==2.8.1`,
   `redis==6.4.0` (all three already installed —
   pinning documents the compatible versions).

2. **`backend/dealer_ai/models.py`** — appended
   `JOB_RUN_STATUS_*` constants, `JOB_RUN_STATUS_CHOICES`
   tuple, and the `JobRunLog` model class. No M1–M6
   model touched.

3. **`backend/dealer_kit/settings.py`** — added
   `django_celery_beat` to `INSTALLED_APPS`; added the
   M7.1 Celery configuration block (`REDIS_URL`,
   `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`,
   `_is_running_tests()`, `CELERY_TASK_ALWAYS_EAGER`,
   `CELERY_TASK_EAGER_PROPAGATES`,
   `CELERY_BEAT_SCHEDULE = {}`,
   `CELERY_BEAT_SCHEDULER`, `CELERY_TIMEZONE`,
   `CELERY_ENABLE_UTC`, `CELERY_TASK_SERIALIZER`,
   `CELERY_RESULT_SERIALIZER`, `CELERY_ACCEPT_CONTENT`).

4. **`backend/dealer_ai/services/tenancy.py`** —
   extended `_TENANT_CARRIER_MODEL_NAMES` 19 → 20 by
   appending `"JobRunLog"` with an explanatory
   comment.

5. **`backend/dealer_ai/tests/test_m6_tenancy_carriers.py`**
   — relaxed the exact-count assertion from `== 19` to
   `>= 19` (renamed `test_carrier_count_is_nineteen`
   → `test_carrier_count_at_least_nineteen`). The
   exact current count is asserted in
   `test_m7_tenancy_carriers.py::test_carrier_count_is_twenty`.
   Future milestones extending the tuple no longer
   need to update the M6.1 test — a pattern worth
   propagating to future milestones.

## Verification

- **Backend tests:** 2,948 → **3,010 pass**, 1 skipped,
  0 fail. **+62 tests** (target ~30 — decorator
  behavior warranted more thorough coverage).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`python3 manage.py migrate --database=migration_check`:**
  0020 applies cleanly.
- **Frontend `npx tsc --noEmit`:** clean.
- **Frontend `npx vite build`:** clean (chunk-size
  warning pre-existing, not from M7.1).
- **Redis smoke test:** `redis-cli ping` → `PONG`.

## Design decisions worth flagging

**`args_summary` truncation strategy.** The
`JobRunLog.args_summary` field is a
`CharField(max_length=255)`. The decorator truncates
via `_truncate` **before** the DB rejects — so a task
called with a giant string argument produces a
readable-but-bounded audit row instead of a save-time
crash. Truncation marker is `"..."` (last three chars
of the returned string when truncation fired). Full
payload lives on the broker until result expiry; if
forensic replay is ever needed, that's the source.

**`SET_NULL` on `dealership` FK.** Deleting a tenant
must NOT cascade and destroy audit history. Mirrors
the M5.1 `entered_by` / M6.2 `uploaded_by` / M6.3
`drafted_by` pattern.

**`error_message` on failure, blank on success.** The
decorator writes a truncated `repr(exc)` on failure
(max 4000 chars for the summary — well above the
practical exception-repr length) and leaves it blank
on success. Full traceback goes to the structured log
stream via `logger.exception`.

**Composite index `(task_name, -started_at)`.** The M8
dashboard's primary query pattern will be "most-recent
run of task X" — the composite index makes that an
index scan instead of a full-table scan. Sized for the
expected M7.2–M7.5 volume (single-digit tasks × single-
digit tenants × single-digit invocations per day —
still well within a single-node Postgres for years).

**Retry set contains transient errors only.** The
decorator's default `autoretry_for` tuple contains
`ConnectionError`, `TimeoutError`, `OSError` —
transient failures where a retry can plausibly
succeed. Programming errors (`ValueError`,
`TypeError`, `AttributeError`, `AssertionError`) are
deliberately absent — those are bugs and must fail
loud per M4–M6 lesson 6 ("no silent-swallow of
exceptions"). Retry cap is 3 with exponential backoff
(max 600s) + jitter — the jitter avoids a thundering-
herd on transient-outage recovery.

**Test posture: `EAGER_PROPAGATES=True`.** The default
Celery eager mode wraps task exceptions in
`EagerResult.failed=True` — worse for test signal
than a raised exception. Setting
`CELERY_TASK_EAGER_PROPAGATES=True` (also gated on the
test runner) restores raise-through-the-caller
semantics so `self.assertRaises(...)` in tests works
naturally.

**Redis mode of ops.** Local dev: `redis-server --daemonize yes`
(no brew services dependency — the `brew services list`
command is currently broken due to a stop_timeout
issue on the M-series homebrew). Prod: env-driven
`REDIS_URL` points at a managed Redis (Upstash / AWS
ElastiCache / DO Managed Redis). No code change
required — the settings binding reads from env
already.

## Non-goals — deferred to later increments

- ❌ No scheduled job bodies — M7.2 (floor-plan
  interest accrual), M7.3 (aging snapshots), M7.4
  (vendor SLA warnings), M7.5 (photo tombstone
  reaper).
- ❌ No Beat schedule entries — appended per increment
  in M7.2+.
- ❌ No operator UI for job history — deferred (log
  inspection acceptable for v1 per roadmap; a Django
  admin registration for `JobRunLog` is a later
  addition and does not require a service module).
- ❌ No Prometheus integration — deferred per §5.e
  Option B (additive decorator can wrap the model
  write when the deploy stack grows a Prometheus
  scrape target).
- ❌ No `StageAgingSnapshot` model — that's M7.3's
  scope per §5.c Option A.

## What's next — SESSION_089 (M7.2)

Move the M2 `accrue_floor_plan_interest` management-
command body to a service verb + wrap in an
`@instrumented_task`. Add the first Beat schedule
entry. Target ~20 tests. Baseline 3,010 → ~3,030.

Read-first list at SESSION_089 open:

- `docs/roadmap/MILESTONE_7_PLANNING.md` §1.2, §7 M7.2.
- `docs/handoffs/SESSION_088_m7_inc1_infra.md` (this
  handoff).
- `backend/dealer_ai/management/commands/accrue_floor_plan_interest.py`
  — the existing command whose body becomes the M7.2
  service verb.
- `backend/dealer_ai/services/vehicle_ledger.py` —
  where the service verb likely lands (or a new
  `services/floor_plan.py` — decide at M7.2 open per
  §1.2 seam).
- `backend/dealer_ai/services/jobs/instrumentation.py`
  — the decorator M7.2 tasks will wear.
- `backend/dealer_ai/tests/test_accrue_floor_plan_interest_command.py`
  — existing test coverage to extend / mirror.

## Anchors that win on conflict (unchanged from SESSION_087)

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

Planning docs are claims. Rules + research + code are
facts.
