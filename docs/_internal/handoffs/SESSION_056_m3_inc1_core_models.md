---
title: "SESSION_056 handoff — Milestone 3 · Increment 1 (core condition-report models)"
status: historical
type: handoff
date: 2026-07-31
session: 056
milestone: 3
milestone_status: in-progress
increment: 1
increment_status: shipped
commit: 2e89913
---

# SESSION_056 — Milestone 3 · Increment 1 (M3.1 — core condition-report models)

## What shipped

The persistence layer for structured condition reports.
Three new models (`ConditionReport`, `ConditionFinding`,
`ConditionFindingPhoto`), migration `0015`, four module-level
enum sets, cross-tenant `clean()` guards on all three models,
one new `completed_at` ↔ `status` invariant on
`ConditionReport`, tenancy-carrier registration extended from
6 → 9, admin registrations, 60 focused tests. No service layer.
No storage. No API. No frontend. No AI.

Also: one narrow **planning-doc refinement** to
`MILESTONE_3_PLANNING.md` §1.5 + §3 — reviewed and approved at
the top of the session — adopted a UUID public-identity model
for `ConditionFindingPhoto` (durable external identity distinct
from the internal `storage_key`) and locked the "photo rows
represent successfully attached objects, never upload
intentions" invariant so `storage_key` remains required and
unique at the schema level.

## Session preamble — the push-back

The user's initial SESSION_056 prompt included a spec that
diverged from `MILESTONE_3_PLANNING.md` §1.1 / §1.2 / §1.5 in
ways that would have silently dropped RECON §2.4 research-cited
fields (`inspector_name`, `mileage_at_inspection`),
introduced un-planned fields (`title`, `filename`,
`display_order`, `completed_by`, `started_at`), and weakened
the `storage_key` invariant. Per CLAUDE.md's "AI is expected
to push back when framing looks wrong" rule and start-here
governance rule §5 (planning doc §1.1/§1.2/§1.5 lock the
field shapes), the session paused and enumerated the
divergences before writing code. The user reviewed the
divergence table and chose **Path C — merged spec** with one
refinement (`storage_key` stays required + unique; UUID is
added as separate public identity; photo rows created only
after upload confirmation). Implementation proceeded from
there.

## Read-first pass performed

Per the start-here doc's recommended sequence, read in order:

1. `docs/roadmap/MILESTONE_3_PLANNING.md` §1 (design memo,
   including §1.0 questions, §1.1 ConditionReport, §1.2
   ConditionFinding, §1.5 ConditionFindingPhoto), §2
   (migration impact — 18 rows), §3 (compatibility checklist),
   §7 M3.1 (increment scope).
2. `backend/dealer_ai/models.py` — reread `VehicleAcquisition`
   (lines 685–787) + `VehicleCost` (lines 925–1028) as the
   persistence-layer template M3.1 mirrors, especially the
   `clean()` cross-tenant guards.
3. `backend/dealer_ai/services/tenancy.py` — reread
   `_TENANT_CARRIER_MODEL_NAMES` tuple (line 260) + the
   `_auto_attach_default_dealership` pre_save handler
   (line 270).
4. `backend/dealer_ai/admin.py` — reread `VehicleAcquisitionAdmin`
   / `VehicleCostAdmin` shape.
5. `backend/dealer_ai/tests/test_vehicle_acquisition.py` (full)
   and `test_dealership.py::WritePathFallback` (lines 226–277)
   for the test-file shape M3.1 mirrors.
6. `00-START-NEXT-SESSION.md` — the SESSION_055-authored
   priority document for SESSION_056.
7. Prior-session handoff `SESSION_055_milestone_3_planning.md`
   for the storage decision + increment sequence.

## The planning-doc refinement

The `MILESTONE_3_PLANNING.md` edits are narrow and were
reviewed by the user before code was written. They are
recorded as an *explicit reviewed refinement*, not silent
drift:

1. **§1.5 Fields list — added `public_id`.** UUIDField, unique,
   `default=uuid.uuid4`, `editable=False`. Cited in
   docstring as the durable public identity that external
   references (URL segments, API payloads, log lines,
   cross-milestone attachments) bind to.
2. **§1.5 storage_key clarification.** Text updated to name
   the field as an "internal storage locator" (not a public
   identifier) and to note that population happens after the
   upload has been verified as landed.
3. **§1.5 new design note — "public identity is a UUID, not
   the storage key."** Explains why the identity/locator split
   was worth adding. Cites SESSION_056 as the point of
   introduction.
4. **§1.5 new design note — "photo rows represent attached
   objects, never upload intentions."** Explains how the M3.5
   presigned-upload flow will keep the prospective key
   transient (outside the model layer) until verification,
   then create the row. Consequence documented: no null-guard
   branches for "row exists but object doesn't" leak into read
   paths.
5. **§3 checklist rows adjusted.** `storage_key` row
   annotated as "internal storage locator only." A new
   `public_id` invariant row added: unique at schema, is the
   durable external identity, `storage_key` must not be
   exposed as a public identifier.

Unrelated planning sections were not touched.

## Concrete deliverables

### Models (`backend/dealer_ai/models.py`)

Appended after `UserDealershipRole` following the M2 append
convention.

- **`ConditionReport`** — 10 fields.
  - `vehicle` (FK CASCADE, related_name `condition_reports`).
  - `dealership` (FK CASCADE, related_name
    `condition_reports`).
  - `authored_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL, `related_name="+"`).
  - `inspector_name` (CharField 255, required per RECON §2.4).
  - `inspected_at` (DateTimeField, required per RECON §2.4).
  - `mileage_at_inspection` (PositiveIntegerField, required
    per RECON §2.4).
  - `status` (CharField 16, choices from
    `CONDITION_REPORT_STATUS_CHOICES`, default `draft`).
  - `completed_at` (DateTimeField, nullable).
  - `notes` (TextField, blank, default "").
  - Timestamps (`created_at`, `updated_at`).
  - `Meta.ordering = ("-inspected_at", "-created_at")`.
  - `clean()` enforces two invariants: cross-tenant guard +
    `completed_at` NULL iff status draft; set iff status
    complete.

- **`ConditionFinding`** — 8 fields.
  - `report` (FK CASCADE, related_name `findings`).
  - `dealership` (FK CASCADE, related_name
    `condition_findings`).
  - `category` (CharField 32, choices from
    `CONDITION_CATEGORY_CHOICES`).
  - `severity` (CharField 16, choices from
    `CONDITION_SEVERITY_CHOICES`).
  - `description` (TextField, required — RECON §2.6
    prohibits AI authorship).
  - `estimated_cost` (Decimal `max_digits=10, decimal_places=2`,
    nullable). Documentation only — locked by
    `EstimatedCostDoesNotPostToVehicleCost` test.
  - `notes` (TextField, blank, default "").
  - Timestamps.
  - `Meta.ordering = ("severity", "category", "created_at")`.
  - `clean()` enforces cross-tenant guard via
    `report.vehicle.dealership`.

- **`ConditionFindingPhoto`** — 9 fields.
  - `public_id` (UUIDField `default=uuid.uuid4`, unique,
    `editable=False`) — durable public identity.
  - `finding` (FK CASCADE, related_name `photos`).
  - `dealership` (FK CASCADE, related_name
    `condition_finding_photos`).
  - `storage_key` (CharField 512, required, unique) —
    internal locator only; never exposed publicly.
  - `content_type` (CharField 32, choices from
    `CONDITION_PHOTO_CONTENT_TYPE_CHOICES`).
  - `size_bytes` (PositiveIntegerField).
  - `caption` (CharField 255, blank, default "").
  - `uploaded_by` (FK to `AUTH_USER_MODEL`, nullable
    SET_NULL, `related_name="+"`).
  - `created_at` (only — planning §1.5 spec, no updated_at
    since M3.5 will treat photo rows as immutable after
    attachment).
  - `Meta.ordering = ("created_at",)`.
  - `clean()` enforces cross-tenant guard via
    `finding.report.vehicle.dealership`.
  - `__str__` surfaces `public_id` + `finding_id`,
    intentionally excludes `storage_key`.

### Enums (`backend/dealer_ai/models.py`)

Four module-level constant sets, mirroring
`VEHICLE_COST_CATEGORY_CHOICES` pattern:

- `CONDITION_REPORT_STATUS_CHOICES` — 2 values: `draft`,
  `complete`.
- `CONDITION_SEVERITY_CHOICES` — 4 values in escalation
  order: `advisory`, `recommended`, `required`, `safety`.
- `CONDITION_CATEGORY_CHOICES` — 12 values flat: eleven from
  RECON §2.1 + `other` escape hatch.
- `CONDITION_PHOTO_CONTENT_TYPE_CHOICES` — 4 values:
  `image/jpeg`, `image/png`, `image/heic`, `image/webp`.

Each constant name is exported (imported by tests + admin +
M3.2 service module which will land at SESSION_057).

### Migration

- `backend/dealer_ai/migrations/0015_condition_report.py` —
  Django-generated, no hand-edits required. Creates all
  three models + the `report` FK on `ConditionFinding`
  (added after `ConditionReport` create in the migration
  ordering). No schema drift beyond `0015`.
- Round-tripped clean-slate against
  `DATABASES["migration_check"]` per M1 lesson 2: all 15
  `dealer_ai` migrations apply forward without error from
  an empty schema.

### Tenancy carrier extension

- `backend/dealer_ai/services/tenancy.py`
  `_TENANT_CARRIER_MODEL_NAMES` extended from 6 → 9. Comment
  added tying the extension to `MILESTONE_3_PLANNING.md` §2
  row 2.

### Admin registrations

- `ConditionReportAdmin` — list_display / list_filter /
  search_fields / autocomplete_fields / readonly_fields
  mirroring `VehicleAcquisitionAdmin` shape.
- `ConditionFindingAdmin` — filters on `severity` + `category`
  for "what's safety-critical vs advisory?" query.
- `ConditionFindingPhotoAdmin` — `public_id` displayed as
  identity, `storage_key` searchable but not surfaced as
  identity.

### Tests

- `backend/dealer_ai/tests/test_condition_report.py` — 17
  tests: status vocabulary (2 values), all-fields round-trip,
  default status is `draft`, `authored_by` optional +
  SET_NULL on user delete, choices validation, four
  `completed_at` invariant tests (draft+null / complete+set
  pass; draft+set / complete+null raise), dealership NOT
  NULL, vehicle required, cross-tenant clean guard (match /
  mismatch), cascade on vehicle delete, reverse relations
  (`vehicle.condition_reports`, `dealership.condition_reports`),
  ordering, `__str__`.
- `backend/dealer_ai/tests/test_condition_finding.py` — 20
  tests: category vocabulary (12 canonical values),
  severity vocabulary (4 canonical, escalation-order
  preserved), all-fields round-trip, `estimated_cost`
  optional, invalid category / severity / empty description
  raise, `EstimatedCostDoesNotPostToVehicleCost` (locks
  the planning §1.2 invariant), dealership NOT NULL, report
  required, cross-tenant clean guard (match / mismatch),
  cascade on report delete + cascade through vehicle delete,
  reverse relation (`report.findings`), ordering by severity,
  `__str__`.
- `backend/dealer_ai/tests/test_condition_finding_photo.py` —
  20 tests: content-type whitelist vocabulary (4 canonical
  values), all-fields round-trip, non-whitelisted content
  type raises, caption defaults empty, five `public_id`
  identity tests (auto-generated, unique across photos,
  independent of storage_key, unique constraint at schema
  level, survives refetch), storage_key uniqueness at schema
  + NOT NULL, dealership NOT NULL, `uploaded_by` optional +
  SET_NULL on user delete, cross-tenant clean guard, cascade
  on finding delete, reverse relation (`finding.photos`),
  ordering by `created_at`, `__str__` (includes public_id +
  finding pk; excludes storage_key).
- `backend/dealer_ai/tests/test_dealership.py` —
  `WritePathFallback` extended with 3 autofill tests, one
  per new carrier.

## Verification evidence

- `python3 manage.py test dealer_ai` → **1,813 tests, 1
  skipped, 0 fail** (up from 1,753; +60 new tests).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- Clean-slate `migration_check` round-trip: `rm
  db.migration_check.sqlite3 && python3 manage.py migrate
  --database=migration_check` applies all 15 `dealer_ai`
  migrations forward without error.
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."

## Compatibility (Milestone 2 and Milestone 1 substrate)

Preserved unchanged:

- Tenancy substrate — no `Dealership` field changes; every
  existing tenant-carrying model still has `dealership` NOT
  NULL; `get_default_dealership` / `get_current_dealership`
  / `get_active_membership` unchanged in signature.
- Identity + authentication — no `DEFAULT_PERMISSION_CLASSES`
  change; auth endpoints unchanged; CSRF still enforced.
- Existing endpoint-level permissions — no changes to
  `dealer_ai/permissions.py`.
- Safety stack — no changes to `services/llm_safety.py`;
  M2.5 `acquisition_price` scrub unchanged; no new scrub in
  M3.
- Customer-facing surfaces — no changes; condition-report
  data never enters any customer chat context (nothing to
  regress).
- M2 ledger substrate — `services/vehicle_ledger.py`,
  `Vehicle.ledger_totals`, `VehicleCost` immutability,
  M2.5 scrub, M2.6 admin ledger endpoints, M2.7 operator
  UI all unchanged. `ConditionFinding.estimated_cost` never
  posts to `VehicleCost` (locked by test).
- Dealer identity resolution — `get_dealer_name()` /
  `get_dealer_profile()` / `get_floor_plan_apr()`
  unchanged.
- Frontend contracts — no changes made in this session
  (M3 frontend is deferred to M3.7).

## Explicitly out of scope for M3.1 (deferred to specific
increments, unchanged)

- ❌ Service module (`services/condition_report.py`) — M3.2.
- ❌ Vehicle `@property` accessors — M3.3.
- ❌ Storage abstraction (`django-storages`, presigned URLs)
  — M3.4.
- ❌ Upload flow (`request_photo_upload`, `attach_photo`,
  `delete_photo`) — M3.5.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3 (VCP §Phase 2 invariant).

## Files changed

- `backend/dealer_ai/models.py` — added enums + three models
  at end (append after `UserDealershipRole`).
- `backend/dealer_ai/services/tenancy.py` — extended
  `_TENANT_CARRIER_MODEL_NAMES` tuple.
- `backend/dealer_ai/admin.py` — added three admin
  registrations + updated `from .models import` list.
- `backend/dealer_ai/migrations/0015_condition_report.py` —
  new file.
- `backend/dealer_ai/tests/test_condition_report.py` — new file.
- `backend/dealer_ai/tests/test_condition_finding.py` — new file.
- `backend/dealer_ai/tests/test_condition_finding_photo.py` —
  new file.
- `backend/dealer_ai/tests/test_dealership.py` — extended
  `WritePathFallback` with 3 autofill tests.
- `docs/roadmap/MILESTONE_3_PLANNING.md` — narrow §1.5 + §3
  amendment (UUID public identity + storage_key clarifications
  + two design notes); §7 M3.1 entry annotated with SHIPPED
  manifest.
- `docs/handoffs/SESSION_056_m3_inc1_core_models.md` — this
  handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_057
  = M3.2 priority.

## Recommended exact scope for SESSION_057 (M3.2 — service layer)

Per `MILESTONE_3_PLANNING.md` §7 M3.2 (locked at SESSION_055;
unchanged by this session):

**Scope.** `backend/dealer_ai/services/condition_report.py`
with these exported functions, each threading `dealership=`
explicitly per `AUTHENTICATION_MODEL.md` §8b:

- `create_report(vehicle, *, dealership, authored_by,
  inspector_name, inspected_at, mileage_at_inspection,
  notes="") -> ConditionReport` — always creates in
  `status="draft"`.
- `complete_report(report) -> ConditionReport` — one-way
  transition draft → complete; sets `completed_at`; raises
  on `complete → *`.
- `add_finding(report, *, category, severity, description,
  estimated_cost=None, notes="") -> ConditionFinding` —
  refuses when `report.status == "complete"`.
- `update_finding(finding, **kwargs) -> ConditionFinding` —
  refuses when parent report is complete.
- `delete_finding(finding) -> None` — refuses when parent
  report is complete.
- `latest_condition_report(vehicle, *, dealership) ->
  Optional[ConditionReport]` — deterministic ordering.
- `latest_completed_condition_report(vehicle, *, dealership)
  -> Optional[ConditionReport]` — filter to
  `status="complete"`.
- `CrossTenantConditionReportError(ValueError)` — fail-closed
  guard on every function (same shape as
  `CrossTenantLedgerError`).

Every function must call `full_clean()` before save (per
retrospective §6 lesson 4). Every function must raise the
cross-tenant error at entry — mismatched `dealership=` against
`vehicle.dealership` or `report.dealership` short-circuits
before touching the ORM.

**Tests target.** ~50 focused service tests. Baseline delta:
1,813 → ~1,863.

**Explicit non-goals for M3.2.**

- ❌ Do NOT touch storage abstraction — M3.4.
- ❌ Do NOT add `@property` methods on `Vehicle` — M3.3.
- ❌ Do NOT write any API endpoint — M3.6.
- ❌ Do NOT ship any photo upload / attach / delete function
  — those wait for M3.4 storage story then M3.5.
- ❌ Do NOT modify the M3.1 model shape unless a test
  reveals a real defect (in which case: raise as a scope
  question first, do not silently patch).

## Anchors that win on conflict for SESSION_057

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every service
   entry point inherits the tenancy + authorization
   substrate.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract. §1.1 / §1.2 / §1.5 lock field shapes (now
   annotated for M3.1 shipped). §7 M3.2 locks service
   signatures.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.2 entry
   (the shape M3.2 mirrors — extracted service module with
   fail-closed cross-tenant guard).
8. `docs/research/RECON_MAPPING.md` §2 + §3.1 for
   business-truth grounding.
9. `docs/CAPABILITY_MATRIX.md`.
10. Most recent handoffs (this file +
    `SESSION_055_milestone_3_planning.md`).

## Operational state (post-SESSION_056)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,813 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` —
  NOT active. M3 recon is in-store workflow; prod not
  required.
- **Frontend (local):** Vite on `:5173`. Auth flow wired.
  M2.7 operator ledger page at
  `/dealer-ai-inventory/:stock/ledger` shipped. Route
  `/dealer-ai-inventory/:stock/condition-report` will land
  M3.7.
- **Frontend (prod):** NONE.
- **Frontend build:** `npx tsc --noEmit` unchanged (no
  frontend edits this session); `npx vite build` unchanged.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  Reset + re-applied clean this session; forward path from
  empty schema through `0015_condition_report` verified.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR` — unchanged this session. M3.4
  will add the `AWS_*` set.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (so far):** M3.0 planning
  (SESSION_055) + M3.1 core models (this session). Remaining
  M3.2–M3.8 queued for SESSION_057–SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. No new deferrals surfaced this session that don't
  fit existing planning docs.
