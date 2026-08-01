---
title: "SESSION_090 handoff — Milestone 7 · Increment 3 (aging-per-stage snapshot job)"
status: historical
type: handoff
date: 2026-08-01
session: 090
milestone: 7
milestone_status: in-progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_090 — Milestone 7 · Increment 3 (M7.3 — aging snapshot job)

## What shipped

The second scheduled job body under the M7.1 substrate.
A new tenant-scoped `StageAgingSnapshot` model (M7.3 §5.c
Option A output substrate), migration `0021`, a new
`services/lifecycle_aging/` package containing the pure
verb + two Celery task shells, a Beat schedule entry at
03:00 project-time daily (one hour after the M7.2 entry
to avoid worker contention), and 49 focused tests
(target ~25 — verb-level percentile math + task-level
audit coverage warranted the extra 24 assertions).

Also: **zero planning amendments needed** — M7.3 had no
`[NEEDS-DECISION-BEFORE-M7.3]` items in
`MILESTONE_7_PLANNING.md` (§5.c Option A was resolved at
SESSION_088 open). Implementation proceeded directly
from §1.3 + §7 M7.3.

## New files (M7.3)

1. **`backend/dealer_ai/migrations/0021_stage_aging_snapshot.py`**
   — single `CreateModel` operation. Reverse is
   `DeleteModel` (safe — no FK reverse dependencies at
   M7.3 close). Applied cleanly against
   `migration_check` DB.

2. **`backend/dealer_ai/services/lifecycle_aging/__init__.py`**
   — package facade. Re-exports `snapshot_stage_ages`,
   `SnapshotResult`, `StagePercentiles`. Tasks kept out
   of the facade for the same import-cycle discipline
   documented in the M7.2 handoff.

3. **`backend/dealer_ai/services/lifecycle_aging/snapshots.py`**
   — the verb (`snapshot_stage_ages`), the
   `SnapshotResult` dataclass, the `StagePercentiles`
   intermediate frozen dataclass, and the internal
   nearest-rank percentile math (`_nearest_rank_percentile`,
   `_compute_stage_percentiles`).

4. **`backend/dealer_ai/services/lifecycle_aging/tasks.py`**
   — two `@instrumented_task`-wrapped Celery tasks
   mirroring the M7.2 pattern:
   - `snapshot_stage_ages_for_tenant(*, dealership_id,
     snapshot_at_iso=None)` — per-tenant. One
     `JobRunLog` row per invocation, stamped with
     `dealership_id`. Returns JSON-safe dict.
   - `snapshot_stage_ages_for_all_tenants(*,
     snapshot_at_iso=None)` — orchestrator. Iterates
     every `Dealership`, enqueues per-tenant via
     `.delay()`.

5. **`backend/dealer_ai/tests/test_m7_stage_aging_model.py`**
   — 9 tests. Field shape + tenant-carrier 20 → 21 +
   Meta ordering / composite index + `__str__` + autofill
   wiring.

6. **`backend/dealer_ai/tests/test_m7_stage_aging_verb.py`**
   — 24 tests. Empty tenant, per-stage row emission,
   nearest-rank percentile math on singleton / two-
   element / ten-element distributions, days-in-stage
   clamp on future `entered_at`, `snapshot_at` defaults
   + explicit stamping, cross-tenant isolation, atomic
   rollback on `bulk_create` failure, dataclass re-exports,
   helper contract coverage for
   `_nearest_rank_percentile` +
   `_compute_stage_percentiles`.

7. **`backend/dealer_ai/tests/test_m7_stage_aging_tasks.py`**
   — 16 tests. Task registration by dotted name,
   per-tenant task writes snapshot + JSON-safe dict +
   `JobRunLog` with tenant stamp, `snapshot_at_iso`
   handling, orchestrator fans out to all tenants +
   writes its own + per-dispatch `JobRunLog`, Beat
   entry registered at 03:00 daily, Beat entry
   ordering constraint (after M7.2 accrual).

## Modified files (M7.3)

1. **`backend/dealer_ai/models.py`** — appended
   `StageAgingSnapshot` class. No M1–M7.2 model
   touched.

2. **`backend/dealer_ai/services/tenancy.py`** —
   extended `_TENANT_CARRIER_MODEL_NAMES` 20 → 21 by
   appending `"StageAgingSnapshot"` with an
   explanatory comment mirroring the M7.1 `JobRunLog`
   entry.

3. **`backend/dealer_kit/settings.py`** — appended
   the `"stage-aging-snapshot-daily-03-00"` entry to
   `CELERY_BEAT_SCHEDULE`, targeting the orchestrator
   at `crontab(hour=3, minute=0)`.

4. **`backend/dealer_ai/tests/test_m7_tenancy_carriers.py`**
   — relaxed the exact-count assertion from `== 20` to
   `>= 20` (renamed `test_carrier_count_is_twenty` →
   `test_carrier_count_at_least_twenty`). The exact
   current count is asserted in
   `test_m7_stage_aging_model.py::test_carrier_count_is_twenty_one`.
   Pattern mirrors SESSION_088 (M6 relaxation) and
   SESSION_089 (Beat-schedule shape assertion).

## Verification

- **Backend tests:** 3,038 → **3,087 pass**, 1 skipped,
  0 fail. **+49 tests** (target ~25).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`python3 manage.py migrate --database=migration_check`:**
  0021 applies cleanly.
- **Frontend `npx tsc --noEmit`:** clean.
- **Frontend `npx vite build`:** clean.
- **Celery task registration:** both M7.3 tasks appear
  in `celery_app.tasks` under their dotted names.
- **Beat entries registered:** M7.2 at `0 2 * * *` and
  M7.3 at `0 3 * * *`.

## Design decisions worth flagging

**Nearest-rank percentiles, not linear-interpolation.**
`_nearest_rank_percentile` uses
`sorted_values[ceil(p * N) - 1]` — the classical
nearest-rank method. Rationale: for a "long tail" M8
dashboard signal, nearest-rank preserves the actual
worst-case values in the distribution rather than
smoothing them. For a two-element distribution
`[3, 30]`, `p90=30` (the actual worst); linear
interpolation would return `27.3` — cleaner-looking but
misleading. The verb writes `PositiveIntegerField`
values so any interpolation-produced float would need
rounding anyway.

**Days-in-stage clamps to zero on future `entered_at`.**
Clock skew / a mis-seeded future date would produce a
negative `.days` — a `PositiveIntegerField` write would
crash. The verb uses `max(0, delta.days)` to keep the
row writable and log a "0 days in stage" reading. The
alternative (raise on negative delta) would abort the
whole snapshot for one bad row — worse than clamping.

**Whole-run atomicity via `transaction.atomic`
wrapping the `bulk_create`.** Mirrors the M7.2 verb.
Partial state is worse than none for a
dashboard-feeding job the operator will re-run.
Locked by
`VerbBulkWriteIsAtomic::test_bulk_create_failure_rolls_back_all_rows`.

**`.values(...)` for the current-stage read.** The
verb uses `.values("current_stage", "entered_at")`
rather than materializing full `VehicleStage`
instances. For a tenant with thousands of vehicles the
`.values()` path skips the ORM-instance overhead and
yields dictionaries the math helper consumes directly.
Cheap, standard Django pattern.

**Stages with zero vehicles produce no rows.** The M8
dashboard reads "absent stage" as "no vehicles here
right now." Alternative (write a zero-count row per
stage) would inflate the table by 12× per snapshot
without adding information — the M8 aggregate query
would filter them out anyway.

**Empty tenant returns `SnapshotResult(written=[])`,
not `None`.** Consumers always get a valid result
object; absence is signaled by the empty list, not by
sentinel None. Consistent with M7.2's
`AccrualSummary` shape.

**Beat entry at 03:00, one hour after M7.2.**
Isolates the two scheduled jobs to separate worker
windows. The aging job scans every `VehicleStage`
row per tenant (read-heavy); the accrual job posts
ledger rows (write-heavy). Concurrent execution on
one Celery worker instance would starve the aging
job of DB connections during accrual's atomic
block. Chosen 03:00 rather than 04:00 or later
because the M8 dashboards should surface today's
aging figures during operator business hours.

**Snapshot time defaults, not exact-coordination
mode.** The orchestrator passes `snapshot_at_iso=None`
to every enqueued per-tenant task. Under fan-out this
means each per-tenant task stamps its own snapshot
time when IT runs — so times drift by however long
each worker takes to reach the task. Rationale: the
M8 dashboards bucket by `date`, not by
second-precision timestamp, so exact coordination is
not necessary. Callers that DO need exact-coordinated
snapshots (e.g. a "snapshot every tenant at this
exact moment" backfill) can pass an explicit
`snapshot_at_iso`.

**Package facade omits `tasks`.** Same discipline as
M7.2 — `services/lifecycle_aging/__init__.py`
re-exports the verb + dataclasses but not
`tasks`. Callers that need the Celery tasks import
from `services.lifecycle_aging.tasks` directly.
Keeps import cycles at bay when M7.1
`services.jobs` is loaded eagerly by Celery
autodiscovery.

## Non-goals — deferred to later increments

- ❌ No M8 aggregation over historical snapshots — the
  M7.3 substrate is the input to M8, not the output.
- ❌ No operator UI for the snapshot dashboard —
  deferred to M8.
- ❌ No aging alerts / threshold-based notifications —
  M7.4 owns vendor SLA warnings (a different alert
  substrate); dashboard-driven alerts land in M8+.
- ❌ No `VehicleStageEvent`-based "time-in-previous-
  stage" analytics — the M7.3 verb reads the current
  `VehicleStage.entered_at` only. Historical stage
  transit analytics are M8.
- ❌ No compute-on-read alternate path — the persist
  strategy is authoritative per §5.c Option A.
- ❌ No per-tenant snapshot-frequency configuration —
  every tenant runs on the shared 03:00 Beat entry.
- ❌ No vendor SLA warnings (M7.4).
- ❌ No photo tombstone reaper (M7.5).

## What's next — SESSION_091 (M7.4)

Vendor SLA warning job. New
`services/vendor_sla/detection.py::detect_sla_breaches`
verb + Celery task. Emits WARNING-level structured
logs identifying WorkOrders past SLA. **No new
models** — the substrate is the M4 `WorkOrder`. Beat
schedule entry. Target ~20 tests. Baseline 3,087 →
~3,107.

Read-first list at SESSION_091 open:

- `docs/roadmap/MILESTONE_7_PLANNING.md` §1.4, §7 M7.4.
- `docs/handoffs/SESSION_090_m7_inc3_aging.md` (this
  handoff).
- `backend/dealer_ai/models.py::WorkOrder` — the M4
  substrate M7.4 reads.
- `backend/dealer_ai/services/recon.py` — where recon
  reads live.
- `backend/dealer_ai/services/lifecycle_aging/` — the
  M7.3 package as the layout template.
- `backend/dealer_ai/services/jobs/instrumentation.py`
  — the decorator M7.4 tasks will wear.

## Anchors that win on conflict (unchanged from SESSION_089)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 7
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_7_PLANNING.md`
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
8. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
9. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
10. `docs/handoffs/SESSION_087_m6_closeout.md`
11. `docs/roadmap/MILESTONE_6_PLANNING.md` (shipped)
12. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6
13. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 6
14. `docs/research/RECON_MAPPING.md` §pain #7 + #12
    (the operational pain M7.3 solves)

Planning docs are claims. Rules + research + code are
facts.
