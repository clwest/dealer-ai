---
title: "SESSION_118 handoff — Milestone 11 · Increment 5 (M11.5 — BeBack tracking + no-show auto-scheduling)"
status: historical
type: handoff
date: 2026-08-02
session: 118
milestone: 11
milestone_status: in_progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_118 — Milestone 11 · Increment 5 (M11.5 — BeBack tracking + no-show auto-scheduling)

## What shipped

New `BeBack` entity capturing the
customer's promise-to-return per
SALES §step 15 (pain #15 —
be-backs are the largest single
source of eventual sales at
mature stores). Three-verb
service package
`services/be_backs/` (record /
mark_returned / mark_no_show).
Two-task Celery no-show detector
wired into Beat at 07:00
project-time daily. Three DRF
admin endpoints under
`admin/be-backs/`. New tenancy
carrier (38 → 39). **29 focused
tests** (target ~25).

Three §5.g items surfaced at
M11.5 open (§1.5 was outlined
at M11.1 planning but not put
to a §5 vote). All three
resolved with the recommended
option and recorded in
`MILESTONE_11_PLANNING.md`
§0.a:

- **§5.g.1 Option A** — mandatory
  `lead` FK, no `vehicle` FK.
- **§5.g.2 Option A** — fixed 4+1
  reason vocab (test_drive /
  bring_co_signer /
  bring_trade_in / other).
- **§5.g.3 Option B** — dedicated
  M11.5 Celery detector (not
  spilling into the M11.4
  cadence engine).

Streak still 35 as-recommended
(planning-time only; §5.g items
were implementation-time defaults
per M11.3 / M11.4 precedent).

## Deliverables

### 1. Model — `dealer_ai/models.py` (appended)

- **Reason constants** (4+1):
  `BE_BACK_REASON_*` +
  `_CHOICES`.
- **State constants** (3):
  `BE_BACK_STATE_PROMISED`
  (default) / `_RETURNED` /
  `_NO_SHOW` + `_CHOICES`.
- **`BeBack` model.**
  - `dealership` FK CASCADE.
  - `lead` FK to `CustomerLead`
    CASCADE (mandatory; no
    Vehicle FK per §5.g.1).
  - `promised_at` DateTimeField.
  - `promised_reason` CharField
    choices.
  - `actual_return_at` nullable
    DateTimeField.
  - `state` CharField choices
    default `promised`.
  - `notes` TextField.
  - Cross-tenant `clean()` on
    `lead`.
  - Meta ordering `-promised_at`.

### 2. Migration — `dealer_ai/migrations/0036_m115_be_back_entity.py`

- Single `CreateModel` for
  BeBack.
- Docstring cites §1.5 + §5.g
  A/A/B + carrier extension
  (38 → 39).

### 3. Tenancy carrier extension — `dealer_ai/services/tenancy.py`

- `"BeBack"` added to
  `_TENANT_CARRIER_MODEL_NAMES`
  (38 → 39).

### 4. Service package — `dealer_ai/services/be_backs/`

- `__init__.py` — re-exports
  three verbs + three domain
  errors.
- `be_back.py`:
  - `record_be_back(...)` —
    cross-tenant guard + reason
    vocab guard.
  - `mark_returned(...)` —
    promised → returned;
    defaults `actual_return_at`
    to now; terminal → 409.
  - `mark_no_show(...)` —
    promised → no_show; leaves
    `actual_return_at` null by
    definition; terminal → 409.
- `tasks.py`:
  - `detect_no_show_be_backs_for_tenant(...)`
    — auto-transitions stale
    promised → no_show for one
    tenant.
  - `detect_no_show_be_backs_for_all_tenants(...)`
    — orchestrator.
  - Both wear
    `@instrumented_task`.
- Three domain errors:
  `CrossTenantBeBackError`,
  `UnknownReasonError`,
  `BeBackAlreadyTerminalError`.

### 5. Settings — `dealer_kit/settings.py`

- New Beat entry
  `"be-back-no-show-detector-daily-07-00"`
  at `crontab(hour=7, minute=0)`.
- New setting
  `BE_BACK_NO_SHOW_GRACE_HOURS`
  (env-overridable; default 4).
- **Scheduled task families:
  5 → 6**.

### 6. View module — `dealer_ai/views_be_backs.py`

- Three endpoints:
  - `admin_be_back_create`
    (POST /admin/be-backs/)
  - `admin_be_back_mark_returned`
    (POST /admin/be-backs/:pk/mark-returned/)
  - `admin_be_back_mark_no_show`
    (POST /admin/be-backs/:pk/mark-no-show/)
- All three gated on
  `IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership`
  (M4 class reused).
- Domain-error mapping:
  cross-tenant → 404, unknown
  reason → 400, terminal → 409,
  missing → 404, serializer
  → 400.

### 7. URL routes — `dealer_ai/urls.py`

Three new patterns under
`admin/be-backs/`.

### 8. Tests — four new files, 29 focused tests

- `test_m115_be_back_model.py`
  (6 tests) — defaults +
  ordering + cross-tenant
  clean + CASCADE + reason
  vocab exact-set + state
  vocab exact-set.
- `test_m115_be_back_service.py`
  (9 tests) — record (3:
  happy, cross-tenant,
  unknown reason), mark_returned
  (3: happy, cross-tenant,
  terminal), mark_no_show (3:
  happy, cross-tenant,
  terminal).
- `test_m115_be_back_endpoint.py`
  (9 tests) — auth (2), happy
  create (1 + response shape),
  create errors (2), transitions
  (4: returned happy, no_show
  happy, terminal 409,
  nonexistent 404).
- `test_m115_be_back_detector.py`
  (5 tests) — transitions
  stale, respects grace
  period, excludes returned,
  excludes already-no_show
  (idempotent), orchestrator
  dispatches per tenant.

## Compatibility

- Backend baseline: **3,858 →
  3,887** (+29, target ~25).
  Zero regressions.
- Frontend baseline: **51**
  (unchanged; M11.5 backend-
  only).
- Migrations `0001`–`0036`.
- Tenancy carriers **39** (38
  → 39 for BeBack).
- Permission classes **8**
  (unchanged; reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`).
- DRF admin surface: **77 →
  80** (+3 M11.5 endpoints).
- Frontend operator routes:
  **11** (unchanged).
- **Celery-beat task families:
  5 → 6**.

## Governance / posture notes

- **Detector transitions state,
  surfacer does not.** The
  M11.5 detector is the first
  M11 Celery task that mutates
  state — deliberate contrast
  with the M11.4 read-only
  surfacer. Rationale: the
  promise is the customer's
  (auto-tracked); task
  completion is the operator's
  intent (operator-only). The
  no-show state simply
  reflects an elapsed grace
  period, no operator judgment
  involved.
- **Grace period configurable.**
  `BE_BACK_NO_SHOW_GRACE_HOURS`
  defaults to 4 hours (matches
  operator reality that a
  customer a few hours late
  isn't yet a no-show). Set
  via env or settings override.
- **Manual override available.**
  `mark_no_show` verb + endpoint
  exists in parallel with the
  detector — operator can
  manually mark no-show before
  the grace period elapses
  (customer called to cancel,
  for instance).
- **No auto-cadence integration.**
  §5.g.3 Option B was chosen
  over Option A (auto-start a
  M11.4 FollowUpCadence on
  BeBack create) to keep the
  M11.5 state machine narrow.
  A follow-on can wire BeBack
  → cadence integration when
  operator evidence names the
  specific cadence template to
  attach.
- **Reuse over invention** —
  M4 permission class, M7
  Celery substrate, M11.1-M11.4
  service-package layout all
  reused. No new permission
  class. No new instrumentation
  helper.
- **Test posture** — 29 focused
  tests including full detector
  coverage. `override_settings`
  used to lock the grace period
  at test time so the test does
  not depend on env state.
- **Streak update** — no
  planning-time §5 decisions
  surfaced at M11.5
  implementation. §5.g items
  were implementation-time
  defaults per M11.3 / M11.4
  precedent. Streak stands at
  **35 as-recommended M5.1 →
  M11.1**.

## Non-goals honored

- ❌ No frontend at M11.5
  (§5.f Option C — MVP
  substrate; extended UI at
  M11.6).
- ❌ No modification of M1-M11.4
  business logic.
- ❌ No auto-cadence integration
  on BeBack create (§5.g.3
  chose Option B for narrow
  state-machine scope).
- ❌ No SMS/email delivery for
  no-show notifications
  (delivery adapters are a
  follow-on).
- ❌ No `reopen` verb for
  terminal be-backs (matches
  M11.4 posture; deferred).
- ❌ No `vehicle` FK on BeBack
  (§5.g.1 Option A — be-backs
  are about returning to the
  store, not a specific unit).

## What's next

**SESSION_119 opens M11.6 —
Operator UI** per §7 M11.6 —
the **first frontend increment
in M11**. Per §5.f Option C
(user-confirmed at M11.1) the
UI ships as MVP polish on the
substrate that M11.1-M11.5
delivered. Model shape is
frozen; frontend consumes the
existing DRF surface.

**Backend baseline at
SESSION_119 open: 3,887 pass.**
Frontend baseline: **51**
(will grow — target TBD at
M11.6 open).

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 + M11.3 + M11.4
   + M11.5 amendments)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`
   (previous session)
8. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
9. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
10. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
11. `docs/CAPABILITY_MATRIX.md` §7k
12. `docs/research/SALES_DEPARTMENT_MAPPING.md`
    §workflow step 15 + pain 15
