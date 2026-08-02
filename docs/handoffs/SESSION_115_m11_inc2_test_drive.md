---
title: "SESSION_115 handoff — Milestone 11 · Increment 2 (M11.2 — TestDrive entity + service + endpoint)"
status: historical
type: handoff
date: 2026-08-02
session: 115
milestone: 11
milestone_status: in_progress
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_115 — Milestone 11 · Increment 2 (M11.2 — TestDrive entity + service + endpoint)

## What shipped

New `TestDrive` entity capturing the
demonstration / test-drive step of
the sales workflow per SALES §step
6. One new model, one migration, one
tenancy carrier extension (34 → 35),
one new `services/test_drives/`
package with a single write verb,
one new `views_test_drives.py`
module with a single DRF endpoint,
one URL route, and 23 focused tests
(target ~20).

The §5.c attach-shape decision
(Option A — mandatory FK to both
`CustomerLead` + `Vehicle`) was
already confirmed at SESSION_114
open and recorded in
`MILESTONE_11_PLANNING.md` §0.a; no
new load-bearing decisions surfaced
at implementation time.

## Deliverables

### 1. Model — `dealer_ai/models.py` (+ appended)

- New `TestDrive` model.
  - `dealership` FK CASCADE
    (tenancy carrier).
  - `lead` FK to `CustomerLead`
    CASCADE (mandatory).
  - `vehicle` FK to `Vehicle`
    CASCADE (mandatory).
  - `driven_by_user` FK to
    `settings.AUTH_USER_MODEL`
    SET_NULL (salesperson who
    accompanied — preserves the
    historical record when a
    user is deleted).
  - `driven_at` DateTimeField.
  - `duration_minutes`
    PositiveIntegerField
    (nullable).
  - `route_notes`,
    `customer_reaction`,
    `next_action` TextField
    (blank OK, default "").
  - `objections_captured`
    JSONField default=list —
    free-list at M11.2; a
    structured vocabulary lookup
    is a M12 candidate.
  - `clean()` cross-tenant guard
    on both `lead` + `vehicle`
    FKs. Belt (model) + suspenders
    (service).
  - Meta `ordering = ["-driven_at"]`.
  - Docstring cites §1.2 + §5.c
    Option A + SALES §step 6.

### 2. Migration — `dealer_ai/migrations/0033_m112_test_drive_entity.py`

- Single `CreateModel` for TestDrive.
- Migration docstring documents §1.2
  + §5.c Option A + carrier
  extension (34 → 35).

### 3. Tenancy carrier extension — `dealer_ai/services/tenancy.py`

- `"TestDrive"` added to
  `_TENANT_CARRIER_MODEL_NAMES`
  (34 → 35). Comment cites
  SESSION_115 + §1.2 + §5.c
  Option A.

### 4. Service package — `dealer_ai/services/test_drives/`

- `__init__.py` — re-exports the
  verb + domain error.
- `test_drive.py`:
  - `record_test_drive(...)` —
    enforces both mandatory FKs
    with cross-tenant guards;
    writes `dealership` explicitly;
    defaults `driven_at` to
    `timezone.now()` when omitted.
  - `CrossTenantTestDriveError`
    exception (fail-closed →
    404 at endpoint layer).

### 5. View module — `dealer_ai/views_test_drives.py`

- `admin_test_drive_create` —
  `POST /admin/test-drives/`.
- `TestDriveCreateRequestSerializer`
  — required `lead_id` + `vehicle_id`;
  optional `driven_at` +
  `duration_minutes` + notes fields
  + `objections_captured` list.
- Gated on `IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership`
  (M4 permission class reused,
  matches M11.1 posture per §1.9).
- Cross-tenant lookup → 404 (fail-
  closed); `CrossTenantTestDriveError`
  → 404; serializer → 400.
- Auto-populates `driven_by_user`
  from `request.user`.
- `_project_test_drive()` response
  shape matches the M10.1
  projection pattern.

### 6. URL route — `dealer_ai/urls.py`

- `admin/test-drives/` →
  `admin-test-drive-create`.

### 7. Tests — three new files, 23 focused tests

- `test_m112_test_drive_model.py`
  (7 tests) — defaults, ordering,
  cross-tenant `clean()` for lead
  + vehicle, CASCADE on lead +
  vehicle delete, SET_NULL on
  user delete.
- `test_m112_test_drive_service.py`
  (5 tests) — full-field write,
  minimal write defaults `driven_at`
  to now, objections JSON
  roundtrip, cross-tenant lead +
  vehicle raise.
- `test_m112_test_drive_endpoint.py`
  (11 tests) — auth gates (4:
  unauth, no membership, advisor,
  f_and_i_manager), happy paths
  (2: sales_manager + response
  shape, dealer_owner), error
  mapping (5: missing lead_id /
  vehicle_id / nonexistent lead /
  cross-tenant lead / cross-tenant
  vehicle).

## Compatibility

- Backend baseline: **3,758 →
  3,781** (+23, target ~20).
  Zero regressions.
- Frontend baseline: **51**
  (unchanged; M11.2 is backend-
  only per §7 non-goal).
- Migrations `0001`–`0033`.
- Tenancy carriers **35** (34 →
  35 for TestDrive).
- Permission classes **8**
  (unchanged; reused M4
  `IsSalesManagerOrOwnerAtActiveDealership`).
- DRF admin surface: **68 → 69**
  (+1 M11.2 endpoint).
- Frontend operator routes: **11**
  (unchanged).
- No M1-M11.1 model / service
  changes.

## Governance / posture notes

- **Mandatory-both attach shape**
  matches the operator reality
  the plan documented: the
  salesperson creates a lead at
  handshake before the drive.
  Relaxation to nullable is a
  future-milestone decision only
  if the "vehicle demo without a
  specific customer" case
  surfaces from operator
  evidence.
- **CASCADE on both parents**
  is defensive (neither
  `CustomerLead` nor `Vehicle`
  supports normal deletion in
  the current workflow — soft-
  null via `is_active` /
  `is_available`).
- **SET_NULL on
  `driven_by_user`** preserves
  the historical drive record
  when a user is deleted /
  deactivated, matching the
  same rationale as
  `Salesperson.user` at M1.4A.
- **Objection vocabulary is
  free-list at M11.2** — no
  structured lookup yet. A
  vocabulary table lands when
  analytics need it (M12
  candidate).
- **Reuse over invention** —
  M4's
  `IsSalesManagerOrOwnerAtActiveDealership`
  reused unchanged. No new
  permission class. Same
  posture as M11.1.
- **Test posture** — 23 focused
  tests, all against real DB
  round-trips (no mocks) per the
  MEMORY-tracked feedback
  "integration tests must hit a
  real database, not mocks".
- **Streak update** — no new §5
  decisions surfaced at M11.2
  implementation time; the M10
  streak stands at 35
  as-recommended M5.1 → M11.1
  open.

## Non-goals honored

- ❌ No `DealWriteup` (M11.3).
- ❌ No cadence orchestration
  (M11.4).
- ❌ No be-back (M11.5).
- ❌ No frontend at M11.2
  (§5.f Option C — MVP
  substrate; extended UI at
  M11.6).
- ❌ No modification of M1-M11.1
  business logic.
- ❌ No listing-platform
  outbound syndication.
- ❌ No structured objection
  vocabulary materialized to a
  separate table (JSON list
  suffices; lookup table
  deferred to M12 if analytics
  need it).
- ❌ No advisor-role write path
  (salespersons enter drives
  via the sales-manager surface
  at M11.2; direct advisor
  write is a follow-on
  decision).

## What's next

**SESSION_116 opens M11.3 —
DealWriteup entity + F&I handoff
action** per §7 M11.3. Model
shape confirmed at M11.1 open
(§5.e Option A — server-side
auto-CA-creation on handoff).

**Backend baseline at
SESSION_116 open: 3,781 pass.**
Frontend baseline unchanged.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 amendment carrying
   §5.c Option A)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
   (previous session)
8. `docs/CAPABILITY_MATRIX.md` §7k
9. `docs/research/SALES_DEPARTMENT_MAPPING.md`
   §workflow step 6
