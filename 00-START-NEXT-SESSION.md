---
state: active
date: 2026-08-02
last_session_shipped: SESSION_114
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
next_session: SESSION_115
next_milestone: 11
next_milestone_name: "Sales-side non-chat channels + customer-journey completeness"
next_increment: 2
next_increment_name: "M11.2 — TestDrive entity + service + endpoint"
---

# Next session — SESSION_115 · Milestone 11 · Increment 2 (M11.2 — TestDrive entity + service + endpoint)

> **SESSION_114 shipped M11.1 —**
> additive `CustomerLead.channel` +
> `referrer` FK + data-migration
> backfill + `services/leads/`
> package with four write verbs
> (walk_in / phone / referral /
> webhook) + `webhook_adapters/`
> registry with one `generic`
> adapter + four DRF admin
> endpoints + 28 focused tests
> (target ~25). **Six §5 planning
> decisions confirmed as-recommended
> at session open — M10 streak → 35
> consecutive M5.1 → M11.1.**
>
> **Backend baseline: 3,730 → 3,758
> (+28, zero regressions).**
> Frontend baseline: **51**
> (unchanged; M11.1 is backend-
> only). Migrations `0001`–`0032`.
> DRF admin surface **64 → 68**.
> Tenancy carriers **34** (unchanged
> — `CustomerLead` was already a
> carrier). Permission classes **8**
> (unchanged — reused
> `IsSalesManagerOrOwnerAtActiveDealership`
> from M4).

## First thing SESSION_115 must do

### 1. Confirm the §5 decision for M11.2 was already recorded

Per `MILESTONE_11_PLANNING.md`
§0.a (M11.1 amendment), **§5.c
Option A** (TestDrive mandatory
FK to both `CustomerLead` +
`Vehicle`) was confirmed at
SESSION_114 open. No new
decisions block M11.2.

If any planning-time §5.c re-
opening is needed at
implementation time (e.g. the
"vehicle demonstration without a
specific lead in hand" edge
case surfaces as a real
operational reality), amend
§0.a narrowly per M5-M10
precedent before writing M11.2
code.

### 2. Verify starting state

- `git status` — clean (M11.1
  commit landed at SESSION_114
  close; push authorization
  batched).
- `git log --oneline -3` — top
  should be M11.1 commit or
  SESSION_113 hash-fixup commit.
- `python3 manage.py test dealer_ai`
  → **3,758 pass, 1 skipped, 0
  fail**.
- `python3 manage.py check`
  clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `redis-cli ping` → `PONG`.

## What M11.2 delivers

Per `MILESTONE_11_PLANNING.md`
§1.2 + §7 M11.2:

- **New `TestDrive` model.**
  - `dealership` FK CASCADE
    (tenancy carrier; extend
    `_TENANT_CARRIER_MODEL_NAMES`
    34 → 35).
  - `lead` FK to `CustomerLead`
    CASCADE (mandatory per §5.c
    Option A).
  - `vehicle` FK to `Vehicle`
    CASCADE (mandatory per §5.c
    Option A).
  - `driven_at` DateTimeField.
  - `driven_by_user` FK to User
    SET_NULL (salesperson who
    accompanied).
  - `duration_minutes`
    PositiveIntegerField (nullable).
  - `route_notes` TextField
    (blank OK).
  - `customer_reaction` TextField
    (blank OK).
  - `objections_captured`
    JSONField default=list
    (structured objection
    vocabulary — vocabulary set
    emerges from SALES §5).
  - `next_action` TextField
    (blank OK).
  - `created_at` / `updated_at`.
- **New `services/test_drives/`
  package** (or a single-module
  `services/test_drive.py`; the
  M4 service pattern is
  per-domain package, so package
  form is preferred for
  consistency with the
  `services/leads/` pattern
  shipped at M11.1).
- **`record_test_drive(...)`**
  write verb. Enforces both FKs
  (mandatory), writes
  `dealership` explicitly.
  Cross-tenant lead / vehicle
  raises
  `CrossTenantTestDriveError`
  (fail-closed → 404 at the
  endpoint layer).
- **`POST /admin/test-drives/`**
  endpoint. Gated on
  `IsSalesManagerOrOwnerAtActiveDealership`
  per §1.9. (Consider whether
  advisors should also write —
  test-drive attendance is a
  salesperson activity; if yes,
  compose with `IsAdvisor*` or
  introduce
  `IsSalespersonOrHigherAtActiveDealership`
  per §1.9 hint.)
- **~20 focused tests** across
  model / service / endpoint
  files (M10 pattern:
  `test_m112_test_drive_model.py`
  / `test_m112_test_drive_service.py`
  / `test_m112_test_drive_endpoint.py`).
- **Baseline target 3,758 →
  ~3,778.**

### Non-goals for M11.2

- ❌ No `DealWriteup` (M11.3).
- ❌ No cadence orchestration
  (M11.4).
- ❌ No be-back (M11.5).
- ❌ No frontend at M11.2
  (M11.6).
- ❌ No modification of M1-M11
  business logic.
- ❌ No objection-vocabulary
  materialization to a separate
  table (JSON list is fine at
  M11.2; a lookup table lands
  when analytics need it —
  M12 candidate).

## What SESSION_115 should do

### Recommended step sequence

1. **Confirm M11.2 §5.c is
   already resolved** (§1
   above). If a new
   `[NEEDS-DECISION]` surfaces
   at planning time (e.g.
   permission-class expansion
   for salespeople), record in
   §0.a before coding.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     §1.2 + §5.c + §7 M11.2.
   - `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
     (previous session).
   - `docs/research/SALES_DEPARTMENT_MAPPING.md`
     §workflow step 6 (test drive)
     + §5 (objection vocabulary).
   - `backend/dealer_ai/models.py::CustomerLead`
     + `Vehicle`.
   - `backend/dealer_ai/services/leads/`
     (M11.1 verb pattern to
     mirror).
   - `backend/dealer_ai/services/tenancy.py`
     (`_TENANT_CARRIER_MODEL_NAMES`
     extension point).

3. **Verify starting state**
   (§2 above).

4. **Draft (in order):**
   - `TestDrive` model + tenancy
     carrier registration.
   - Migration `0033`.
   - `services/test_drives/`
     package + `record_test_drive`
     verb + `CrossTenantTestDriveError`.
   - `views_test_drives.py` +
     serializer + endpoint.
   - URL route
     `admin/test-drives/`.
   - ~20 focused tests.

5. **Full-suite verification.**
   Target 3,758 → ~3,778.

6. **Ship handoff at
   `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M11.3 priority
   (DealWriteup + F&I handoff).

## Explicit non-goals for SESSION_115

- ❌ Do NOT ship M11.3-M11.7
  scope.
- ❌ Do NOT modify M1-M11
  business logic.
- ❌ Do NOT force-push or amend
  the M11.1 commits.

## NEXT TASK

Start SESSION_115 with (a)
verifying §5.c is already
resolved (M11.1 recorded it in
§0.a), (b) the read-first list,
(c) starting-state verification,
then (d) `TestDrive` model +
tenancy carrier extension (34 →
35) + migration + service
package + endpoint + ~20 tests.
Target baseline 3,758 → ~3,778.
Ship the M11.2 handoff.

Backend baseline at SESSION_115
close: **~3,778 pass**.
Frontend baseline: unchanged
(no frontend at M11.2).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 amendment)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
   (this session's close)
8. `docs/handoffs/SESSION_113_m10_close.md`
9. `docs/CAPABILITY_MATRIX.md` §7k
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_114 — M11.1 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0032`. Test baseline:
  **3,758 pass**, 1 skipped, 0
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
  (unchanged since M7).
- **Milestones shipped:** M1 →
  **M10**. M11 in progress
  (M11.1 shipped SESSION_114).
- **DRF admin surface:** **68**
  (64 + M11.1's four channel
  endpoints).
- **Frontend operator routes:**
  **11** (unchanged; M11.1
  backend-only).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` package
  (M10 close) + new
  `services/leads/` package
  (M11.1) with two submodules
  (channel_intake +
  webhook_adapters).
- **Tenancy carriers:** **34**
  (unchanged; M11.1 extended
  `CustomerLead` in place).
- **Permission classes:** **8**
  (unchanged; M11.1 reused
  `IsSalesManagerOrOwnerAtActiveDealership`
  from M4).
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
  backfilled to `chat` via
  M11.1 migration.
- **Webhook adapter registry:**
  `{"generic": ...}` at
  M11.1; extensible via sibling
  modules under
  `services/leads/webhook_adapters/`.
- **Milestone 11 next:** M11.2
  `TestDrive` entity + service +
  endpoint. Verify §5.c
  Option A resolution already
  recorded. ~20 tests. Baseline
  3,758 → ~3,778.
