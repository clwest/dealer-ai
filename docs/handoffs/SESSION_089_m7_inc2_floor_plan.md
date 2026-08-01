---
title: "SESSION_089 handoff — Milestone 7 · Increment 2 (floor-plan interest accrual job)"
status: historical
type: handoff
date: 2026-08-01
session: 089
milestone: 7
milestone_status: in-progress
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_089 — Milestone 7 · Increment 2 (M7.2 — floor-plan accrual job)

## What shipped

The first scheduled job body under the M7.1 Celery
substrate. The M2
`accrue_floor_plan_interest` management command's
orchestration body extracted to a new
`services/floor_plan/` package, two Celery task shells
(per-tenant worker + all-tenants orchestrator), a Beat
schedule entry firing the orchestrator at 02:00
project-time daily, and 27 focused tests. **No new
models, no new migrations.** The M2 CLI surface
(`--dealership` / `--as-of` / `--dry-run`) is preserved
verbatim — the command is now a thin CLI adapter around
the new service verb.

Also: **zero planning amendments needed** — M7.2 had no
`[NEEDS-DECISION-BEFORE-M7.2]` items in
`MILESTONE_7_PLANNING.md` §9, per the M7.1 handoff
closeout. Implementation proceeded directly from §1.2 +
§7 M7.2. One implementation-time decision (documented
below) was the service-verb seam.

## Session preamble — one implementation seam decision

Per M7 §7 lesson 4 (service ownership — one
authoritative write path per operation), M7.2 had to
decide where the extracted verb lives:

- **Option A — Extend `services/vehicle_ledger.py`.**
  Rejected. The ledger service's own module docstring
  is explicit: *"Milestone 2 · Increment 4 lands the
  math helper + management command"* — the accrual
  orchestration is deliberately outside its charter.
- **Chosen: new `services/floor_plan/` package.** The
  package's `accrual.py` owns the verb + dataclasses;
  `tasks.py` owns the Celery shells; `__init__.py`
  re-exports the public surface. Consistent with the
  M7 §1.1 seam ("New jobs land in
  `services/<domain>/tasks.py`") and sets the pattern
  for M7.3–M7.5.

## New files (M7.2)

1. **`backend/dealer_ai/services/floor_plan/__init__.py`**
   — package facade. Re-exports `accrue_daily_interest`,
   `AccrualPlan`, `AccrualSummary`. Does NOT re-export
   the task module (import-cycle discipline: tasks
   pull the decorator from `services.jobs`, which is
   loaded eagerly by Celery autodiscovery at Django
   boot).

2. **`backend/dealer_ai/services/floor_plan/accrual.py`**
   — the extracted verb (`accrue_daily_interest`), the
   `AccrualPlan` frozen dataclass, and the
   `AccrualSummary` dataclass. The M2 command body
   moved verbatim (zero business-logic changes) — only
   `self.` method calls became module-level helper
   functions. Locked contracts (duplicate detection
   FIRST, whole-run atomicity in live mode, last-
   accrual-date resolution priority, ledger-service
   ownership) all preserved.

3. **`backend/dealer_ai/services/floor_plan/tasks.py`**
   — two `@instrumented_task`-wrapped Celery tasks:
   - `accrue_daily_interest_for_tenant(*, dealership_id,
     as_of_iso=None)` — per-tenant work. One
     `JobRunLog` row per invocation, stamped with
     `dealership_id`. Returns a JSON-safe dict for
     debug / dashboards.
   - `accrue_daily_interest_for_all_tenants(*,
     as_of_iso=None)` — orchestrator. Enqueues one
     per-tenant task per `Dealership` via `.delay()`.
     One `JobRunLog` row for the orchestrator; one
     more per per-tenant dispatch.
   Task-name constants (`ACCRUE_FOR_TENANT_TASK_NAME`,
   `ACCRUE_FOR_ALL_TENANTS_TASK_NAME`) exported so
   callers / Beat entries / tests reference the
   dotted names exactly once.

4. **`backend/dealer_ai/tests/test_m7_floor_plan_verb.py`**
   — 12 tests. Verb interface (`AccrualSummary` return
   shape, `dry_run` posts nothing, live mode posts
   rows, `as_of=None` defaults to today, explicit
   `as_of` honored, same-day idempotency, cross-tenant
   isolation, dataclass re-exports).

5. **`backend/dealer_ai/tests/test_m7_floor_plan_tasks.py`**
   — 15 tests. Task registration by dotted name,
   per-tenant task posts rows + returns JSON dict,
   `JobRunLog` row created with tenant stamp,
   `as_of_iso` kwarg handling, orchestrator fans out
   to all tenants, orchestrator writes its own +
   per-dispatch `JobRunLog` rows, Beat entry
   registered with the expected 02:00 crontab, M2 CLI
   regression check.

## Modified files (M7.2)

1. **`backend/dealer_ai/management/commands/accrue_floor_plan_interest.py`**
   — rewritten as a thin CLI adapter. The
   orchestration body moved to
   `services/floor_plan/accrual.py`. The command now
   owns: argparse, tenant resolution, `--as-of`
   parsing, stdout formatting via
   `AccrualSummary.format()`. That's it. Reduced from
   419 to 137 lines. **CLI surface preserved verbatim
   — every existing M2 test still passes.**

2. **`backend/dealer_kit/settings.py`** — appended one
   `CELERY_BEAT_SCHEDULE` entry:
   `"floor-plan-accrual-daily-02-00"` targets the
   orchestrator at `crontab(hour=2, minute=0)`.
   Added `from celery.schedules import crontab` at
   the block top.

3. **`backend/dealer_ai/tests/test_accrue_floor_plan_interest_command.py`**
   — updated two `mock.patch` targets from
   `dealer_ai.management.commands.accrue_floor_plan_interest.add_cost`
   (and `.transaction.atomic`) to their new home
   `dealer_ai.services.floor_plan.accrual.add_cost`
   (and `.transaction.atomic`). Everything else in the
   19-test M2 suite untouched.

4. **`backend/dealer_ai/tests/test_m7_celery_app.py`**
   — replaced the M7.1 "empty schedule" assertion with
   two shape-based assertions (dict-typed container +
   required keys on every registered entry). Prior
   milestone tests should NOT hard-code the exact
   count of Beat entries; each increment's own test
   module owns its entry's shape assertions. Pattern
   mirrors SESSION_088's M6-tenancy relaxation.

## Verification

- **Backend tests:** 3,010 → **3,038 pass**, 1 skipped,
  0 fail. **+28 tests** (target ~20 — task/verb
  coverage warranted the extra 8 assertions).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **Frontend `npx tsc --noEmit`:** clean.
- **Frontend `npx vite build`:** clean.
- **Celery task registration:** both M7.2 tasks appear
  in `celery_app.tasks` under their dotted names.
- **Beat entry registered:** `floor-plan-accrual-daily-02-00`
  targets the orchestrator with `crontab(0 2 * * *)`.

## Design decisions worth flagging

**Two tasks, not one.** A single task could accept an
optional `dealership_id` and switch between per-tenant
and all-tenants modes internally. Rejected because the
orchestrator's `JobRunLog` row would then have
`dealership_id=None` (fallback to default via the
tenancy autofill signal) — misrepresenting the actual
process-wide scope. Two tasks + separate `JobRunLog`
rows = clean audit semantics at each level (M7 §7
lesson 6, honest verification reporting).

**Fan-out via `.delay()`, not synchronous iteration.**
The orchestrator enqueues each per-tenant invocation
via `.delay()` — under `CELERY_TASK_ALWAYS_EAGER=True`
(tests) this is synchronous; in prod each per-tenant
task lands on a worker thread for parallel processing.
The pattern also means an exception in one tenant's
per-tenant task does NOT abort the orchestrator's
fan-out for the remaining tenants (Celery isolates
failures at task boundaries).

**JSON-serializable return dict, not `AccrualSummary`
directly.** The per-tenant task returns a hand-rolled
dict rather than `dataclasses.asdict(summary)`.
Rationale: `AccrualSummary` contains a `Decimal`
(`total_accrued`) which JSON does not serialize
natively — the hand-rolled dict casts it to `str`
explicitly. Locks the JSON-only Celery serialization
posture from M7.1.

**`as_of_iso` (str), not `as_of` (date).** Celery's
JSON-only serialization rejects Python `date` objects
— the task shell takes the ISO string and parses it
inside the task body. The service verb still accepts
a native `date`; only the task shell speaks ISO.

**02:00 project-time, not per-tenant local time.**
Per-tenant local time is deferred for v1. Rationale:
(a) the accrual math is time-of-day agnostic — it
accrues over whole calendar days regardless of the
task's actual firing minute, and (b) a per-tenant
schedule would require either N Beat entries (fragile,
requires code-deploy churn as tenants onboard) or a
`django-celery-beat` per-tenant DB row (larger scope
than M7.2 warrants). A single project-wide entry at
02:00 America/Chicago accrues every tenant once per
calendar day — the intended semantics.

**M2 CLI surface preserved verbatim.** The command's
argparse contract (`--dealership` / `--as-of` /
`--dry-run`) is byte-for-byte identical to the M2
shipping state. Every existing M2 test in
`test_accrue_floor_plan_interest_command.py` still
passes with only two `mock.patch` target updates
(the module the patch points at moved, but the
patch semantics are unchanged). This is the M4-M6
lesson 11 posture (additive extension, not fork).

**Package facade omits the task module.** The
`services/floor_plan/__init__.py` re-exports the verb
+ dataclasses but does NOT re-export the task module.
Reason: the task module imports the M7.1 decorator
from `services.jobs`, which is fine on its own — but
if `__init__.py` re-exported the tasks, then importing
`services.floor_plan` at Django boot (e.g. from
`services.tenancy`'s app-registry lookup) would
cascade into `services.jobs`, and any future import
cycle involving `services.tenancy` and job registration
would be harder to unpick. Keeping tasks strictly
outside the package facade preserves import-order
flexibility for M7.3-M7.5.

## Non-goals — deferred to later increments

- ❌ No new models (`StageAgingSnapshot` is M7.3).
- ❌ No new migrations (M7.2 is body-only).
- ❌ No changes to the accrual math — moved verbatim.
- ❌ No vendor SLA warnings (M7.4).
- ❌ No photo tombstone reaper (M7.5).
- ❌ No operator UI for job history — deferred (log
  inspection acceptable for v1 per roadmap).
- ❌ No per-tenant local-time scheduling — deferred
  (see design decisions above).
- ❌ No `django_celery_beat.PeriodicTask` DB-row
  registration for the Beat entry — the entry lives in
  the code-first `CELERY_BEAT_SCHEDULE` dict. Operators
  who want to edit the schedule via Django admin can
  do so after boot; DB rows layer on top of the code
  entries via the DatabaseScheduler.

## What's next — SESSION_090 (M7.3)

New `StageAgingSnapshot` model + migration `0021`.
`services/lifecycle_aging.py::snapshot_stage_ages`
verb + Celery task. Beat schedule entry. Target ~25
tests. Baseline 3,038 → ~3,063.

Read-first list at SESSION_090 open:

- `docs/roadmap/MILESTONE_7_PLANNING.md` §1.3, §7 M7.3.
- `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
  (this handoff).
- `backend/dealer_ai/models.py::VehicleStage` +
  `VehicleStageEvent` — the M5 substrate feeding the
  aging snapshot job.
- `backend/dealer_ai/services/vehicle_lifecycle.py` —
  where lifecycle-adjacent reads probably live.
- `backend/dealer_ai/services/jobs/instrumentation.py`
  — the decorator M7.3 tasks will wear.
- `backend/dealer_ai/services/floor_plan/` — the M7.2
  package as the pattern template.

## Anchors that win on conflict (unchanged from SESSION_088)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 7
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_7_PLANNING.md`
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
8. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
9. `docs/handoffs/SESSION_087_m6_closeout.md`
10. `docs/roadmap/MILESTONE_6_PLANNING.md` (shipped)
11. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6
12. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 6
13. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §pain #10 (the operational pain M7.2 solves)

Planning docs are claims. Rules + research + code are
facts.
