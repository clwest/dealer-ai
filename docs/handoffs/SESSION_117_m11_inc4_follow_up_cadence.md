---
title: "SESSION_117 handoff — Milestone 11 · Increment 4 (M11.4 — FollowUpCadence + FollowUpTask + Celery-beat scheduling)"
status: historical
type: handoff
date: 2026-08-02
session: 117
milestone: 11
milestone_status: in_progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_117 — Milestone 11 · Increment 4 (M11.4 — FollowUpCadence + FollowUpTask + Celery-beat scheduling)

## What shipped

Two-entity follow-up scheduling
substrate per §5.d Option A:
`FollowUpCadence` header (one per
lead per template) + `FollowUpTask`
rows (the scheduled contact
points). Four-verb service package
`services/follow_ups/` (start /
complete / skip / pause). Two-task
Celery orchestrator wired into
Beat at 06:00 project-time daily
(next slot after M7.5). Five DRF
admin endpoints under
`admin/follow-up-*/`. Two new
tenancy carriers (36 → 38). **44
focused tests** (target ~30).

§5.d was already confirmed at
SESSION_114 open. **Three
implementation-time micro-
decisions recorded in
`MILESTONE_11_PLANNING.md` §0.a**
(planning-time streak stays 35;
implementation-time defaults
don't count per M10 §9):

1. **Cadence templates: fixed
   constants** (`FOLLOW_UP_TEMPLATE_*`),
   matching M11.1's vocab-set
   pattern.
2. **Beat schedule: code-first
   bootstrap +
   DatabaseScheduler overlay**
   — matches M7.2-M7.5 posture.
3. **Task auto-skip: operator-
   triggered only** — the beat
   surfacer counts + logs due
   tasks but never mutates
   state.

## Deliverables

### 1. Model — `dealer_ai/models.py` (appended)

- **Constants:** six
  `FOLLOW_UP_TEMPLATE_*` values
  + `FOLLOW_UP_TEMPLATE_CHOICES`
  + `FOLLOW_UP_TEMPLATE_OFFSETS`
  (dict[template → tuple of
  day offsets from cadence
  start]).
- **Task state constants:**
  `FOLLOW_UP_TASK_STATE_PENDING`
  / `_COMPLETED` / `_SKIPPED`
  + `_CHOICES`.
- **`FollowUpCadence` model.**
  - `dealership` FK CASCADE.
  - `lead` FK to `CustomerLead`
    CASCADE.
  - `template` CharField choices.
  - `started_at` DateTimeField.
  - `is_active` BooleanField
    default True.
  - Cross-tenant `clean()` on
    `lead`.
  - Ordering `-started_at`.
- **`FollowUpTask` model.**
  - `dealership` FK CASCADE.
  - `cadence` FK CASCADE.
  - `due_at` DateTimeField
    (db_index=True).
  - `state` CharField choices
    default pending.
  - `completed_by_user` FK to
    User SET_NULL.
  - `completed_at` nullable
    DateTimeField.
  - `notes` TextField.
  - Cross-tenant `clean()` on
    `cadence`.
  - Ordering `due_at`.

### 2. Migration — `dealer_ai/migrations/0035_m114_follow_up_cadence_and_task.py`

- Two `CreateModel` operations
  (FollowUpCadence + FollowUpTask).
- Docstring cites §1.4 + §5.d +
  carrier extension (36 → 38).

### 3. Tenancy carrier extension — `dealer_ai/services/tenancy.py`

- `"FollowUpCadence"` +
  `"FollowUpTask"` added to
  `_TENANT_CARRIER_MODEL_NAMES`
  (36 → 38).

### 4. Service package — `dealer_ai/services/follow_ups/`

- `__init__.py` — re-exports
  four verbs + five domain
  errors.
- `cadence.py`:
  - `start_cadence(...)` —
    `@transaction.atomic`;
    creates cadence + seeds
    tasks from
    `FOLLOW_UP_TEMPLATE_OFFSETS`
    dict; refuses cross-tenant
    lead / unknown template /
    duplicate active (per lead,
    template).
  - `complete_task(...)` /
    `skip_task(...)` — pending
    → terminal; refuse re-
    transition.
  - `pause_cadence(...)` —
    idempotent flip
    `is_active=False`; refuses
    cross-tenant.
- `tasks.py`:
  - `surface_due_follow_up_tasks_for_tenant(...)`
    — per-tenant counter (does
    not mutate state).
  - `surface_due_follow_up_tasks_for_all_tenants(...)`
    — orchestrator (dispatches
    per-tenant via `.delay()`).
  - Both wear
    `@instrumented_task` per
    M7.1 pattern.
- Five domain errors:
  `CrossTenantCadenceError`,
  `CrossTenantTaskError`,
  `DuplicateActiveCadenceError`,
  `UnknownTemplateError`,
  `TaskAlreadyTerminalError`.

### 5. Beat schedule — `dealer_kit/settings.py`

- New entry
  `"follow-up-task-surface-daily-06-00"`
  in `CELERY_BEAT_SCHEDULE`
  targeting
  `surface_due_follow_up_tasks_for_all_tenants`
  at `crontab(hour=6,
  minute=0)`. Positioned one
  hour after M7.5 (tombstone
  reaper).
- **Scheduled task families: 4
  → 5.**

### 6. View module — `dealer_ai/views_follow_ups.py`

- Five endpoints:
  - `admin_follow_up_cadence_create`
    (POST /admin/follow-up-cadences/)
  - `admin_follow_up_cadence_pause`
    (POST /admin/follow-up-cadences/:pk/pause/)
  - `admin_follow_up_task_list`
    (GET /admin/follow-up-tasks/
    + `state` / `due_before` /
    `limit` filters)
  - `admin_follow_up_task_complete`
    (POST /admin/follow-up-tasks/:pk/complete/)
  - `admin_follow_up_task_skip`
    (POST /admin/follow-up-tasks/:pk/skip/)
- All five gated on
  `IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership`
  (M4 permission class reused).
- Domain-error mapping:
  cross-tenant → 404, duplicate
  → 409, unknown template →
  400, terminal task → 409,
  missing → 404, serializer
  → 400.

### 7. URL routes — `dealer_ai/urls.py`

Five new patterns under
`admin/follow-up-cadences/` +
`admin/follow-up-tasks/`.

### 8. Tests — four new files, 44 focused tests

- `test_m114_follow_up_model.py`
  (10 tests) — cadence
  defaults + ordering + cross-
  tenant clean + CASCADE +
  task defaults + ordering +
  clean + CASCADE + SET_NULL
  + template-vocab exact set +
  offset-schedule sanity.
- `test_m114_follow_up_service.py`
  (14 tests) — start × 6
  (happy + all-templates seed
  + cross-tenant + unknown +
  duplicate + pause-then-
  start), transition × 4
  (complete + skip + terminal
  + cross-tenant), pause × 3
  (flip + idempotent + cross-
  tenant).
- `test_m114_follow_up_endpoint.py`
  (15 tests) — auth (2:
  unauth, advisor), happy (2:
  sales_manager + response
  shape, dealer_owner), error
  (3: cross-tenant, duplicate,
  invalid template), pause
  (2: happy, nonexistent),
  transitions (3: complete,
  skip, terminal 409), task
  list (3: default, state
  filter, due_before filter).
- `test_m114_follow_up_beat.py`
  (5 tests) — per-tenant
  counts only due pending,
  read-only (doesn't mutate),
  excludes paused, excludes
  completed, orchestrator
  dispatches per tenant.

## Compatibility

- Backend baseline: **3,814 →
  3,858** (+44, target ~30).
  Zero regressions.
- Frontend baseline: **51**
  (unchanged; M11.4 backend-
  only).
- Migrations `0001`–`0035`.
- Tenancy carriers **38** (36
  → 38 for
  FollowUpCadence +
  FollowUpTask).
- Permission classes **8**
  (unchanged; reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`).
- DRF admin surface: **72 →
  77** (+5 M11.4 endpoints).
- Frontend operator routes: **11**
  (unchanged).
- **Celery-beat task families:
  4 → 5**.

## Governance / posture notes

- **Split scheduling from
  delivery.** The M11.4 beat
  surfacer is read-only —
  counts + logs due tasks but
  never sends SMS / email / any
  outbound. Delivery adapters
  land in a follow-on
  increment and subscribe to
  the surfaced-count or read
  the task-list endpoint. Keeps
  the M11.4 test surface tight
  (no external I/O mocks
  needed).
- **State transitions are
  operator-triggered only** per
  §0.a M11.4 decision 3. Auto-
  skip (after N days past
  `due_at`) would be a separate
  planning decision needing
  operator input on the N
  default; not shipped.
- **Duplicate-active guard on
  cadence start** prevents two
  overlapping schedules for the
  same (lead, template) pair.
  Pause the existing cadence to
  start a new one; historical
  (paused / completed) cadences
  don't block.
- **Terminal-task refusal on
  re-transition.** Once a task
  is completed or skipped, re-
  calling the verb raises
  `TaskAlreadyTerminalError`
  (409). Silent overwrite
  would erase operator intent
  (who marked it, when,
  completed vs skipped). A
  future ``reopen_task`` verb
  can add the un-do path when
  the operator UI surfaces the
  need.
- **Beat orchestrator matches
  M7.2 pattern.** Two tasks
  (per-tenant + orchestrator),
  both `@instrumented_task`,
  orchestrator fans out via
  `.delay()`, JobRunLog rows
  per invocation, non-
  overlapping maintenance
  windows across M7.2-M11.4.
- **Reuse over invention** —
  M4 permission class reused,
  M7 Celery substrate reused,
  M11.1/11.2/11.3 service-
  package layout mirrored.
- **Test posture** — 44
  focused tests including
  full beat-integration
  coverage (
  `CELERY_TASK_ALWAYS_EAGER`
  makes orchestrator dispatch
  synchronous per M7.1
  posture — no separate worker
  needed).

## Non-goals honored

- ❌ No be-back (M11.5).
- ❌ No frontend at M11.4
  (§5.f Option C — MVP
  substrate; extended UI at
  M11.6).
- ❌ No modification of M1-M11.3
  business logic.
- ❌ No auto-skip of stale
  tasks (deferred).
- ❌ No SMS / email delivery
  (delivery adapters are a
  follow-on).
- ❌ No `reopen_task` verb
  (deferred until operator UI
  surfaces need).
- ❌ No operator-configurable
  cadence templates (fixed
  constants at M11.4).

## What's next

**SESSION_118 opens M11.5 —
BeBack tracking** per §7
M11.5. Model shape TBD at
M11.5 open — no §5 decision
was recorded specifically for
be-backs at M11.1 open, so
review §1.5 + surface a
narrow `[NEEDS-DECISION-BEFORE-M11.5]`
for the state-machine +
Celery-beat re-contact
integration.

**Backend baseline at
SESSION_118 open: 3,858
pass.** Frontend baseline
unchanged.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 + M11.3 + M11.4
   amendments)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
   (previous session)
8. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
9. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
10. `docs/CAPABILITY_MATRIX.md` §7k
11. `docs/research/SALES_DEPARTMENT_MAPPING.md`
    §workflow steps 12-15
