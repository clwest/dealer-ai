---
title: "Milestone 7 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-01
sessions: SESSION_088 → SESSION_093
milestone: 7
milestone_name: "Async infrastructure"
related:
  - docs/roadmap/MILESTONE_7_PLANNING.md
  - docs/roadmap/MILESTONE_6_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 7
---

# Milestone 7 — Retrospective

Written at Milestone 7 close (SESSION_093). Records what
was planned, what shipped, what deviated and why, and
lessons carried forward for Milestone 8. Mirrors the
`MILESTONE_6_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_7_PLANNING.md` at SESSION_087 defined the
milestone as answering six operational questions from
`INVENTORY_ACQUISITION_MAPPING.md` pain #10 +
`RECON_MAPPING.md` pains #7 + #12 +
`BHPH_OPERATIONS_MAPPING.md` pain #2 + VCP Phase 6. The
questions cover: *how does floor-plan interest accrue
automatically each day, how does aging-per-stage
refresh on a schedule so the operator sees vehicles
stuck for N days, how do vendor SLA warnings fire when
a WorkOrder has been in status X longer than Y days,
how do photo-derived jobs (M6.2 tombstoned-photo
physical-delete reaper) run, how does BHPH payment
reminder cadence run (deferred to M12 — no substrate
at M7 time), and how does the operator see whether a
scheduled job ran / when / with what outcome?*

§1 followed with seven design-memo entries covering the
task-queue + scheduler substrate, four scheduled jobs
(floor-plan accrual, aging snapshot, vendor SLA,
photo tombstone reaper), the deferred BHPH reminder
job, and the cross-cutting job-observability
substrate.

§2 skeleton enumerated existing surfaces M7 touched
with required work. §3 defined the compatibility
checklist. §5.a-§5.f drafted six load-bearing
decisions — **five flagged
`[NEEDS-DECISION-BEFORE-M7.1]`** requiring user review
before code landed. §7 sequenced six increments
(M7.1-M7.6).

**Original §7 sequencing (M7.1 → M7.6) shipped
verbatim.** All five §9 decisions confirmed as-is at
SESSION_088 open (Redis / Celery / persist snapshots
/ 30-day retention / JobRunLog model). **No §0.a
change-log amendments were required inside M7.1-M7.5.**

## 2. What actually shipped

Every §3 compatibility item verified true; details in
the annotated checklist at `MILESTONE_7_PLANNING.md`
§3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M7.0 planning | 087 | `MILESTONE_7_PLANNING.md` (636 lines) resolving one load-bearing decision (photo reaper deferred to M7 per §1.5) and leaving five for user review | `659078f` |
| M7.1 Celery + Redis + observability | 088 | `dealer_kit/celery.py` app instance + `__init__.py` extension + settings block (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ALWAYS_EAGER` gated on test-runner detection, `CELERY_BEAT_SCHEDULE = {}` starting empty, `CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"`, `CELERY_TIMEZONE = TIME_ZONE`, JSON-only serialization pins). `celery[redis]==5.5.3` + `django-celery-beat==2.8.1` + `redis==6.4.0` pinned. New `services/jobs/instrumentation.py::@instrumented_task` decorator + `INSTRUMENTED_TRANSIENT_ERRORS` tuple (ConnectionError / TimeoutError / OSError). New `JobRunLog` model + migration `0020` (single `CreateModel`; composite `(task_name, -started_at)` index). `_TENANT_CARRIER_MODEL_NAMES` extended 19 → 20. 62 focused tests. **Five §9 decisions confirmed at session open (all A):** §5.a Redis, §5.b Celery, §5.c persist snapshots, §5.d 30-day retention, §5.e JobRunLog. One M6.1 test relaxed in-place (`test_carrier_count_is_nineteen` → `test_carrier_count_at_least_nineteen`) — count assertions at prior-milestone floors should use `>=` not `==` | TBD |
| M7.2 floor-plan accrual | 089 | New `services/floor_plan/` package (`__init__.py` facade + `accrual.py` verb with M2 command orchestration body extracted verbatim + `tasks.py` with per-tenant worker + all-tenants orchestrator). M2 `accrue_floor_plan_interest` command rewritten as 137-line CLI adapter (from 419 lines). Beat entry `"floor-plan-accrual-daily-02-00"` at 02:00 project-time. `_scrub_invented_recon_fact` unchanged (M7.2 is orchestration-only). 27 focused new tests + 2 M2 command tests updated in-place (mock.patch target updates only — patch semantics unchanged). One M7.1 test relaxed in-place (`test_beat_schedule_is_empty_dict` → shape-based `test_beat_schedule_is_dict_typed` + `test_beat_schedule_entries_have_required_shape`) — same lesson as M6 test relaxation. **No §9 decisions to confirm** — planning §1.2 fully specified the shape. **One implementation-time seam decision confirmed at open:** new package under `services/floor_plan/` (extends charter cleanly) not extension of `services/vehicle_ledger.py` (which explicitly scopes itself to pure ledger primitives) | TBD |
| M7.3 aging snapshot | 090 | New `StageAgingSnapshot` model + migration `0021` (single `CreateModel`; composite `(dealership, stage, -snapshot_at)` index). New `services/lifecycle_aging/` package (`__init__.py` + `snapshots.py` with verb + `StagePercentiles` frozen dataclass + `SnapshotResult` + nearest-rank percentile math + `_compute_stage_percentiles` helper + `_nearest_rank_percentile` helper + days-in-stage clamp on future `entered_at` + `.values()` read for fleet-scale efficiency + `transaction.atomic()` wrapping `bulk_create`). Two Celery tasks + Beat entry at 03:00 project-time. `_TENANT_CARRIER_MODEL_NAMES` extended 20 → 21. 49 focused new tests. **No §9 decisions** — §5.c Option A resolved at SESSION_088 open. One M7.1 test relaxed in-place (`test_carrier_count_is_twenty` → `test_carrier_count_at_least_twenty`) — same lesson | TBD |
| M7.4 vendor SLA warnings | 091 | New `services/vendor_sla/` package (`__init__.py` + `detection.py` with `detect_sla_breaches` verb + `SlaBreach` + `SlaBreachReport` dataclasses + `_classify_in_progress` + `_classify_approved` rule branches + rule-precedence in dispatcher + three locked policy constants + `BREACH_KIND_*` constants). Two Celery tasks + Beat entry at 04:00 project-time. **Read-only verb** — emits `logging.WARNING` records per breach; no DB writes beyond the `JobRunLog` audit row. **Query-level `venue='outsourced'` + `status__in=(approved, in_progress)`** narrowing so terminal / draft / in-house rows never reach Python. 34 focused new tests. **No §9 decisions** — three implementation-time thresholds confirmed at open (all recommendations): `APPROVED_STALE_THRESHOLD_DAYS=7`, `IN_PROGRESS_ETA_GRACE_DAYS=0`, scope `venue='outsourced'` only | TBD |
| M7.5 photo tombstone reaper | 092 | Restructured `services/photo_gallery.py` → `services/photo_gallery/__init__.py` via `git mv` + two relative-import bumps (zero business-logic changes; 112 downstream tests verified unchanged). New `reaper.py` module with `reap_tombstoned_photos` verb + `ReaperResult` dataclass + `PHOTO_RETENTION_DAYS = 30` constant + storage-first delete pattern + iteration-level failure isolation. New `tasks.py` with per-tenant + orchestrator Celery tasks + Beat entry at 05:00 project-time. Extended `services/photo_storage.py` with sibling `delete_vehicle_photo_object` + `_validate_vehicle_photo_storage_key` (M6.2 substrate gap discovered — existing `delete_object` only validated M3.4 condition-report shape). 29 focused new tests. **No §9 decisions** — §5.d Option A resolved at SESSION_088 open. **One implementation-time seam decision confirmed at open:** Option B (restructure to package) not Option A (flat + sibling tasks module) — consistent with M7.2/M7.3/M7.4 pattern; zero-breaking verified against 7 downstream import sites | TBD |
| M7.6 closeout | 093 | This retrospective + `CAPABILITY_MATRIX.md` §7h + `IMPLEMENTATION_ROADMAP.md` §Milestone 7 flip + `MILESTONE_7_PLANNING.md` frontmatter flip + `DEALER_KIT_SESSION_START.md` refresh + `MILESTONE_8_PLANNING.md` created per standing user directive. Coordinated commit + push of all M7.1-M7.6 stages | TBD |

## 3. Planning-doc amendments landed inside increments

**Zero `§0.a` change-log amendments were required inside
M7.1-M7.5.** Every load-bearing decision surfaced at
each session open was resolved with the user's
confirmation of the recommended option — no override
required and therefore no amendment. This maintains the
M6-established discipline (M6 also had zero amendments
after M5's eight).

Two implementation-time seam decisions were surfaced +
confirmed at session opens without requiring planning
amendments because the planning doc left them
deliberately open:

1. **SESSION_089 M7.2 verb-seam.** Planning §1.2
   allowed either extension of `services/vehicle_ledger.py`
   or a new `services/floor_plan/` package. Chose the
   package per the M4-M6 lesson-4 service-ownership
   discipline + `vehicle_ledger.py`'s own explicit
   scope charter.

2. **SESSION_092 M7.5 package restructure.** Planning
   §1.5 phrasing ("`services/photo_gallery/tasks.py`
   as a sibling module") implicitly required a package,
   but M6.2 had shipped `photo_gallery` as a flat
   `.py` module. Chose Option B (restructure to
   package) after verifying zero-breaking against
   7 downstream import sites. Consistent with
   M7.2/M7.3/M7.4.

Three implementation-time policy thresholds were
surfaced + confirmed at SESSION_091 open without
requiring planning amendments because planning §1.4
explicitly left the numeric values to implementation:

1. **`APPROVED_STALE_THRESHOLD_DAYS = 7`** —
   §1.4 phrased "approved-stale > N days" without
   pinning N.
2. **`IN_PROGRESS_ETA_GRACE_DAYS = 0`** — §1.4 phrased
   "past ETA" without pinning grace.
3. **Scope `venue='outsourced'` only** — §1.4 title
   said "vendor SLA warnings" implying outsourced
   but the rules were `venue`-agnostic. In-house
   delays deemed a separate operational problem
   (dispatch / capacity).

## 4. Deviations

**Accepted improvements** (all landed inside
increments, all reviewed by user first or surfaced
explicitly in commits):

1. **SESSION_088 M6.1 test relaxation** — the
   `test_carrier_count_is_nineteen` absolute-count
   assertion naturally staled when M7.1 extended
   `_TENANT_CARRIER_MODEL_NAMES` 19 → 20. Relaxed to
   `test_carrier_count_at_least_nineteen` (`>=` not
   `==`). Established the "prior increment tests
   should use floor-count `>=`" pattern that recurred
   across M7.

2. **SESSION_089 M7.1 test relaxation** — the
   `test_beat_schedule_is_empty_dict` assertion staled
   when M7.2 added the floor-plan Beat entry. Replaced
   with two shape-based assertions
   (`test_beat_schedule_is_dict_typed` +
   `test_beat_schedule_entries_have_required_shape`).
   Same pattern as SESSION_088's M6.1 relaxation.

3. **SESSION_089 M2 command extraction** — the M2
   `accrue_floor_plan_interest` command body (419
   lines) moved verbatim to
   `services/floor_plan/accrual.py`. The management
   command became a 137-line CLI adapter. **CLI
   surface preserved verbatim** — every existing M2
   test still passed with only two `mock.patch` target
   updates (patch semantics unchanged, only the module
   path moved). Model of the M4-M6 lesson-11 "additive
   extension over fork" applied to a refactor.

4. **SESSION_090 M7.1 test relaxation** — the
   `test_carrier_count_is_twenty` assertion staled
   when M7.3 extended `_TENANT_CARRIER_MODEL_NAMES`
   20 → 21. Same floor-count relaxation.

5. **SESSION_092 photo_gallery package restructure**
   — moved `services/photo_gallery.py` →
   `services/photo_gallery/__init__.py` via `git mv`
   + two relative-import bumps. Zero business-logic
   changes; verified against 7 downstream import
   sites + 112 existing tests. Enabled the M7.5
   `reaper.py` + `tasks.py` siblings to live inside
   the same package namespace as the M6.2 verbs.

6. **SESSION_092 `photo_storage.delete_vehicle_photo_object`**
   — discovered mid-implementation that the M6.2
   substrate never added a delete function for M6.2
   vehicle-photo keys (the M3.4 `delete_object`
   validates against `_KEY_PATTERN` — condition-report
   shape only). Added sibling `delete_vehicle_photo_object`
   + `_validate_vehicle_photo_storage_key`. Consistent
   with the existing M3.4/M6.2 `build_canonical_key` /
   `build_canonical_vehicle_photo_key` split and the
   `parse_canonical_key` / `parse_canonical_vehicle_photo_key`
   split.

**Deferrals cataloged** (not dropped; scheduled for
follow-up increments or future milestones):

- **§1.6 BHPH payment reminder cadence** — no BHPH
  substrate exists at M7 time. Deferred to
  Milestone 12 (BHPH module). Planning doc explicitly
  cites this as the intended home.
- **Per-dealer `photo_retention_days`** (§5.d Option
  C) — Option A shipped (fixed at 30 days). Per-dealer
  configurability deferred pending operator evidence
  that 30 is wrong for enough dealers.
- **Per-dealer vendor-SLA thresholds** — deferred per
  M7.4 preamble. Extension shape documented in
  `services/vendor_sla/detection.py`.
- **In-house tech-delay detection** — M7.4 explicitly
  scoped to `venue='outsourced'`. In-house delays are
  a dispatch / capacity problem, not a vendor-pressure
  problem. Later job if operator evidence surfaces.
- **Prometheus counters** (§5.e Option B) — Option A
  shipped (JobRunLog model). Prometheus integration
  can be added as an additive decorator wrapping the
  model write when the deploy stack grows a scrape
  target.
- **Job-history operator UI** — deferred; log
  inspection + Django admin `JobRunLog` are acceptable
  for v1. M8 dashboards will surface these.
- **Multi-worker autoscaling / complex workflow DAGs**
  — explicitly out-of-scope per M7 planning §1.
- **`_scrub_invented_photo_claim`** — M6 deferral
  carried forward (not an M7 substrate).
- **Notification channels (email / SMS / phone)** —
  M7.4 explicitly out-of-scope. Milestone 11+.
- **Historical aging aggregation** — M7.3 writes
  snapshots; M8 aggregates them.

**No planned scope dropped** in the sense of a
shipped-but-broken feature or silently-missing
invariant.

## 5. Compatibility

Every §3 compatibility row verified true with inline
evidence at `MILESTONE_7_PLANNING.md` §3. Test baseline:
**3,150 pass, 1 skipped, 0 fail** at SESSION_092.
Delta: +202 tests over M6 close baseline (2,948 →
3,150); 0 regressions after in-place fixture updates
in M7.2 (2 mock.patch targets), M7.1 test relaxations
in M7.2 + M7.3 (2 count assertions + 1 shape
assertion).

Highlights:

- **Zero regressions** across M1–M6 test suites. Every
  pre-M7 chat / vehicle-ask / ad-copy / follow-up /
  ledger / condition-report / recon / lifecycle /
  photo-gallery / listing test continues to pass.
- **`Vehicle.is_available` schema + values unchanged.**
- **M2 ledger substrate byte-for-byte preserved.**
  `services/vehicle_ledger.py` API unchanged; M7.2
  extracted the M2 accrual command body to a service
  verb without touching ledger primitives.
- **M3 / M4 / M5 substrate preserved.** No API changes.
- **M6 photo-gallery service preserved** through the
  `.py` → `/__init__.py` package restructure — every
  M6.2 verb signature identical, every M6.2 constant
  identical. Two relative-import bumps only.
- **M6.2 photo-storage service extended additively**
  — new `delete_vehicle_photo_object` +
  `_validate_vehicle_photo_storage_key` alongside the
  existing M3.4 `delete_object` /
  `_validate_storage_key`. Neither existing function
  touched.
- **Tenancy carriers 19 → 21.** M7.1 added
  `JobRunLog`; M7.3 added `StageAgingSnapshot`. Same
  `pre_save` autofill safety net as M1-M6 carriers.
- **DRF admin surface unchanged.** M7 shipped no new
  endpoints — the async substrate is background-only
  per §1.
- **Frontend operator routes unchanged.** M7 shipped
  no frontend — Beat scheduler is background-only.
- **Four Beat schedule entries wired** at hourly
  cadence 02:00 / 03:00 / 04:00 / 05:00 project-time.
  Non-overlapping windows so operator triage is
  straightforward when one job family starts failing.

## 6. Lessons

Fourteen lessons carried forward for Milestone 8 and
beyond. Thirteen inherit from M6 §6 with M7 evidence;
one is new to M7.

1. **Increment discipline.** Each M7 sub-increment
   shipped independently verifiable in one session.
   Every session opened with load-bearing decisions
   (or implementation-time thresholds) confirmed by
   the user before code landed. Carry-forward from
   M6 §6 lesson 1.

2. **Backend-first architecture; frontend never owns
   business rules.** M7 shipped no frontend at all.
   The four scheduled job families are pure
   background-runtime, invisible to the operator until
   M8 dashboards land. Carry-forward from M6 §6 lesson
   2.

3. **Provider-neutral boundaries.** Celery is
   abstracted behind the `@instrumented_task`
   decorator — job authors do not import from
   `celery` directly. Broker + result backend read
   from `settings.REDIS_URL` (env-configurable, no
   code change to move to managed Redis in prod).
   `django-celery-beat`'s DatabaseScheduler layers on
   top of the code-first `CELERY_BEAT_SCHEDULE` dict
   so schedules can be edited via Django admin
   without a deploy. Carry-forward from M6 §6 lesson
   3.

4. **Service ownership — one authoritative write
   path per operation.** Every scheduled job body
   delegates to a service verb; the Celery task shell
   does registration + retry + logging only. The M2
   accrual verb moved from a management command body
   into `services/floor_plan/accrual.py` verbatim so
   the command + task + any future ad-hoc caller
   all take the same code path. Carry-forward from M6
   §6 lesson 4.

5. **Local vs production parity.** Dev + prod both
   run Celery + Redis. Tests never depend on a
   running broker — `CELERY_TASK_ALWAYS_EAGER=True`
   gated on `_is_running_tests()` (mirrors the M5.5
   test-only signal precedent) runs every
   `@instrumented_task` synchronously in the caller's
   transaction. Carry-forward from M6 §6 lesson 5.

6. **Honest verification reporting.** Every
   `@instrumented_task` writes a `JobRunLog` row on
   start AND on end. Success ends at `succeeded`;
   failure ends at `failed` with a truncated
   `error_message`; retry ends at `retried`. No
   silent-swallow of exceptions — the wrapper
   re-raises after logging. Retry policy is explicit
   per task; the default
   (`INSTRUMENTED_TRANSIENT_ERRORS = (ConnectionError,
   TimeoutError, OSError)`) retries transient
   failures but propagates programming errors fast.
   Carry-forward from M6 §6 lesson 6.

7. **Storage-first / safer-direction deletion.** The
   M7.5 photo tombstone reaper deletes bytes BEFORE
   the row (M3.5 pattern). Iteration-level failure
   isolation — a storage failure on one candidate
   leaves the row + logs the error + increments the
   counter; the remaining batch continues. Carry-
   forward from M6 §6 lesson 7 with the operational
   lesson-11 addition: for housekeeping jobs, partial
   progress is BETTER than none (opposite of M7.2's
   whole-run atomicity where partial state is
   worse).

8. **Load-bearing decisions get user review BEFORE
   code.** Every M7 session opened with the required
   decisions surfaced to the user before code landed.
   Every recommendation was confirmed as-is — zero
   `§0.a` change-log amendments across the whole
   milestone (matches M6, inverts M5's eight). Even
   implementation-time policy thresholds (M7.4's three
   numbers) and seam questions (M7.2 + M7.5) surfaced
   at session open, not mid-implementation.
   Carry-forward from M6 §6 lesson 8.

9. **Distinct domain errors → distinct behaviors.**
   M7 shipped no HTTP endpoints, so the M4/M5/M6
   "distinct domain errors → distinct HTTP status
   codes" specialization narrows to "distinct
   task-body behaviors": `INSTRUMENTED_TRANSIENT_ERRORS`
   trigger retry; programming errors fail fast;
   `ObjectStorageError` in the reaper leaves the row
   intact for retry. Carry-forward from M6 §6 lesson
   9 in its background-runtime form.

10. **Read-model properties are pure reads.**
    Preserved from M6 §6 lesson 10. M7 added no new
    Vehicle `@property` accessors. The M7.3 verb
    reads `VehicleStage.entered_at` directly via
    `.values()` for fleet-scale efficiency —
    module-level function, no side effects, no
    hidden writes.

11. **Additive extension over fork.** M7.2 extracted
    the M2 accrual command body into a new service
    package but preserved the M2 CLI surface verbatim
    (`--dealership` / `--as-of` / `--dry-run`
    identical). M7.5 restructured `photo_gallery`
    from module to package but preserved every M6.2
    verb + constant. M7.5 extended `photo_storage`
    with a sibling delete function rather than
    loosening the existing one. The
    `delete_vehicle_photo_object` addition is a
    textbook example of extending a service without
    touching existing callers. Carry-forward from M6
    §6 lesson 11.

12. **Zero-planning-amendment sessions are a signal.**
    M7.1-M7.5 shipped without a single `§0.a`
    change-log amendment. Every user-facing decision
    was framed clearly enough at planning time
    (SESSION_087 M7.0) that at each session open the
    recommendations could be confirmed as-is. Even
    the two mid-M7 implementation-time decisions
    (M7.2 seam + M7.5 seam) fit within planning-doc
    slots (`§1.2` and `§1.5` both left them open).
    **Future milestone-planning sessions should
    continue aiming for zero-amendment increments
    as a signal of good planning-doc discipline.**
    Carry-forward from M6 §6 lesson 12.

13. **Two-tier customer-visibility gate.** M6.5's
    batch-query-vs-direct-access split preserved
    across M7 — the M7.3 aging snapshot reads via
    `.values()` (batch pattern) whereas the M7.4
    SLA classifier reads per-WO with
    `select_related("vehicle", "vendor")` (direct-
    access pattern). Neither is customer-facing, but
    the batch/direct-access mental separation
    surfaces even in background jobs. Carry-forward
    from M6 §6 lesson 13.

14. **[NEW] Prior-increment count assertions should
    use `>=`, not `==`.** M7 saw three separate
    test-relaxation edits (M6.1 tenancy count at
    SESSION_088, M7.1 Beat-schedule-empty at
    SESSION_089, M7.1 tenancy count at SESSION_090)
    where an earlier increment's exact-count
    assertion staled when a later increment
    legitimately extended the count. The correct
    pattern is: each increment's count assertion
    should use `>=` at the milestone-shape floor;
    the exact-count invariant is owned by that
    increment's own test at its shipping time. When
    the next milestone extends further, its own
    test locks the new exact count and no prior
    test needs editing. **Future milestone-planning
    sessions should establish this posture at
    milestone-open** so the "prior increment tests
    need in-place relaxation" chore does not recur.
    New at M7.
