---
title: "SESSION_057 handoff — Milestone 3 · Increment 2 (condition-report service layer)"
status: historical
type: handoff
date: 2026-07-31
session: 057
milestone: 3
milestone_status: in-progress
increment: 2
increment_status: shipped
commit: 0c98f2e
---

# SESSION_057 — Milestone 3 · Increment 2 (M3.2 — condition-report service layer)

## What shipped

The deterministic business layer for structured condition
reports. One authoritative write path per operation; every
public function threads `dealership=` explicitly and calls
`full_clean()` before save; fail-closed cross-tenant guards at
every entry; completed reports are immutable; `estimated_cost`
is documentation-only at the service layer.

Seven public functions plus two domain error classes plus 61
focused tests. No models touched. No migrations. No API. No
frontend. No storage. No photo functions. No `Vehicle`
`@property` accessors. No AI.

Also: one **reviewed refinement** to the M3.2 planning contract —
adding `dealership=` to `complete_report`, `add_finding`,
`update_finding`, `delete_finding` (the planning contract named
it only on `create_report` and the two `latest_*` accessors).
Rationale: uniform security posture, every call site must state
tenant intent explicitly. This is a tightening; no user-visible
surface exists yet.

## Read-first pass performed

Per the start-here doc's recommended sequence, read in order:

1. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.2 detail + §3
   business-layer invariants (cross-tenant error shape,
   `complete_report` transition rules, `add_finding` /
   `update_finding` / `delete_finding` gating).
2. `docs/handoffs/SESSION_056_m3_inc1_core_models.md` — the
   M3.1 shipped-surface manifest + the UUID-identity planning
   refinement rationale.
3. `backend/dealer_ai/services/vehicle_ledger.py` (full 476
   lines) — the M2.2 service pattern M3.2 mirrors.
   `CrossTenantLedgerError` shape,
   `_assert_same_tenant(vehicle, dealership)` helper, `full_clean()`
   call ordering, explicit-`dealership=` kwarg discipline,
   `__all__` re-export.
4. `backend/dealer_ai/tests/test_vehicle_ledger.py` (partial —
   the `CategoryGroupings`, `CrossTenantGuards`,
   `RecordAcquisitionUpsert`, `AddCostImmutable` classes) —
   the service-tests shape M3.2 mirrors.
5. `backend/dealer_ai/models.py` M3.1 surface — module-level
   enum constants (`CONDITION_CATEGORY_CHOICES`,
   `CONDITION_SEVERITY_CHOICES`,
   `CONDITION_REPORT_STATUS_CHOICES`), model classes, `clean`
   invariants.

## The reviewed refinement

`MILESTONE_3_PLANNING.md` §7 M3.2 lists these signatures:

- `create_report(vehicle, *, dealership, ...)` — has `dealership=`.
- `complete_report(report)` — no `dealership=`.
- `add_finding(report, *, category, ...)` — no `dealership=`.
- `update_finding(finding, **kwargs)` — no `dealership=`.
- `delete_finding(finding)` — no `dealership=`.
- `latest_condition_report(vehicle, *, dealership)` — has it.
- `latest_completed_condition_report(vehicle, *, dealership)` —
  has it.

SESSION_057 spec (in the user prompt) says:

> Every public service entry must:
> - accept explicit `dealership=`
> - verify the parent Vehicle or Report belongs to that dealership
> - fail closed on cross-tenant access
> - never rely on the pre-save tenancy autofill as the primary path

This tightens the planning contract. As shipped, **every one of
the seven public functions takes `dealership=` explicitly.** The
service module's docstring records this as a tightening-not-
divergence and cites the reason. The M3.2 planning-entry
annotation (§7 M3.2 "Shipped surface") records the same.

Callers that were going to hit the pre-tightening signature had
no chance to — M3.6 is where the endpoints land; no user-visible
surface exists yet.

## Concrete deliverables

### Service module (`backend/dealer_ai/services/condition_report.py`)

567 lines. Structure mirrors `services/vehicle_ledger.py`:

**Domain errors (both subclass `ValueError`).**

- `CrossTenantConditionReportError` — raised at the entry of
  every function when the caller's `dealership` argument does
  not match the target Vehicle / Report / Finding.
- `ConditionReportImmutableError` — raised when a caller
  attempts to edit, add findings to, complete, or delete
  findings from a report whose `status` is already `complete`.
  Distinct class so M3.6 can map to HTTP 409 Conflict
  specifically.

**Tenant-guard helpers (private).**

- `_assert_vehicle_tenant(vehicle, dealership)` — for
  `create_report` and both `latest_*`.
- `_assert_report_tenant(report, dealership)` — for
  `complete_report`. Verifies BOTH `report.dealership` AND
  `report.vehicle.dealership` (belt + suspenders across the
  denormalized carrier and the ground-truth vehicle tenant).
- `_assert_finding_tenant(finding, dealership)` — for
  `add_finding` (via the report), `update_finding`,
  `delete_finding`. Verifies BOTH `finding.dealership` AND
  `finding.report.vehicle.dealership` per SESSION_057 spec.

**Immutability helper (private).**

- `_refresh_and_assert_draft(report, operation)` — refreshes
  the report from DB and raises
  `ConditionReportImmutableError` when status is not `draft`.
  Narrow race handling for stale in-memory instances.

**Public functions (7).**

- `create_report(vehicle, *, dealership, authored_by=None,
  inspector_name, inspected_at, mileage_at_inspection,
  notes="")` — always creates in `status="draft"` with
  `completed_at=None`. Distinct provenance: `authored_by`
  (FK, nullable) is who typed the report; `inspector_name`
  (required CharField) is who physically inspected the
  vehicle. Full-clean before save.
- `complete_report(report, *, dealership)` — one-way draft →
  complete. Sets `completed_at = timezone.now()` atomically
  with the status change. Refreshes from DB then rejects
  non-draft (via `ConditionReportImmutableError`). Full-clean
  before save.
- `add_finding(report, *, dealership, category, severity,
  description, estimated_cost=None, notes="")` — validates
  `category` and `severity` against
  `_VALID_CATEGORY_KEYS` / `_VALID_SEVERITY_KEYS` (frozensets
  built from the model-layer choice tuples) before touching
  DB. Refuses when parent report is complete. `estimated_cost`
  never posts to `VehicleCost`.
- `update_finding(finding, *, dealership, **updates)` —
  whitelist of updatable fields: `category`, `severity`,
  `description`, `estimated_cost`, `notes`. Attempting any
  other field (including `report`, `dealership`, `id`,
  `dealership_id`, unknown keys) raises `ValueError` with a
  message listing the allowed set. `category` and `severity`
  are re-validated on change. Refuses when parent report is
  complete.
- `delete_finding(finding, *, dealership)` — deletes only
  from a draft report. Returns `None`. Callers that need the
  deleted finding's fields should read them before calling.
- `latest_condition_report(vehicle, *, dealership)` — most
  recent report of any status; deterministic ordering
  `(-inspected_at, -created_at)`; returns `None` on empty
  state; no writes; no caching.
- `latest_completed_condition_report(vehicle, *, dealership)`
  — same shape as above, filtered to `status="complete"`.

**`__all__` re-exports** `ValidationError` alongside the domain
errors + functions, so callers do not have to reach into
Django internals to catch model-clean errors surfaced through
the service.

### Tests (`backend/dealer_ai/tests/test_condition_report_service.py`)

61 tests across thirteen classes:

- `CrossTenantGuards` (8 tests) — one per public function
  plus `ValueError`-subclass identity assertion.
- `CreateReportSemantics` (5 tests) — always draft,
  completed_at null at birth, distinct provenance,
  authored_by optional, multiple reports per vehicle.
- `CompleteReportSemantics` (5 tests) — transition, returned
  instance equals persisted, double-complete raises,
  immutable-error is `ValueError`, `completed_at` never
  shifts on second-attempt refusal.
- `AddFindingSemantics` (6 tests) — draft-only, invalid
  category / severity raise plain `ValueError` (not the
  cross-tenant subclass), `estimated_cost` optional, empty
  description raises `ValidationError` via `full_clean`.
- `UpdateFindingSemantics` (9 tests) — whitelist accepted,
  re-parenting / re-scoping / unknown / id manipulation
  refused, category / severity re-validated, completed-report
  refuses, no-op update permitted.
- `DeleteFindingSemantics` (2 tests) — draft delete works,
  completed refuses + row still present.
- `CompletedReportImmutability` (4 tests) — composite: every
  mutation type raises after complete.
- `EstimatedCostRemainsInformational` (3 tests) — service
  ops (add, update, complete-with-findings) never create a
  `VehicleCost` row.
- `LatestConditionReportAccessor` (5 tests) — empty state,
  single, ordering by `inspected_at`, draft-newest returned,
  cross-tenant not returned.
- `LatestCompletedConditionReportAccessor` (5 tests) — empty
  state, only-drafts returns None, single complete, skips
  newer draft, returns newest complete when multiple.
- `DeterministicReads` (2 tests) — five consecutive calls
  return identical PKs for both accessors.
- `FullCleanFiresBeforeSave` (2 tests) — observable evidence
  the service invokes `full_clean` (completed_at set on
  complete; empty description raises `ValidationError`).
- `TransactionBehavior` (4 tests) — refusals leave no
  partial state (cross-tenant create, immutable add,
  invalid category, immutable update).
- `RecommendedSeverityUsable` (1 test) — every canonical
  severity value accepted; catches drift if a future edit
  adds a severity to the enum but forgets to sync the
  service constant.

## Verification evidence

- `python3 manage.py test dealer_ai` → **1,874 tests, 1
  skipped, 0 fail** (up from 1,813; +61 new tests).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."

## Compatibility

Preserved unchanged:

- All M1 tenancy substrate — no changes to `Dealership`,
  `_TENANT_CARRIER_MODEL_NAMES`, `get_default_dealership`,
  `get_current_dealership`, `get_active_membership`.
- All M1 identity + authentication — no changes to
  `DEFAULT_PERMISSION_CLASSES`, `SessionAuthentication`,
  `TokenAuthentication`, `/auth/*` endpoints, CSRF.
- All M1 · 4D + M2.6 endpoint-level permissions — no
  changes to `dealer_ai/permissions.py`.
- Safety stack — no changes to `services/llm_safety.py` or
  any pre / post-LLM guard. No new scrub in M3.
- Customer-facing surfaces — no changes; condition-report
  data never enters chat or per-vehicle Q&A contexts
  (nothing to regress).
- M2 ledger substrate — `services/vehicle_ledger.py`,
  `Vehicle.ledger_totals`, `VehicleCost` immutability, M2.5
  scrub, M2.6 admin ledger endpoints, M2.7 operator UI all
  unchanged. `ConditionFinding.estimated_cost` verified
  (three tests) to never post to `VehicleCost` via any M3.2
  service operation.
- Dealer identity resolution — `get_dealer_name()` /
  `get_dealer_profile()` / `get_floor_plan_apr()`
  unchanged.
- Frontend — no changes made this session.
- Storage — no `django-storages`, no `boto3`, no `AWS_*`
  env, no `MEDIA_ROOT` writes.

## Explicitly out of scope for M3.2 (deferred, unchanged)

- ❌ Vehicle `@property` accessors — M3.3.
- ❌ Storage abstraction (`django-storages`, presigned URLs)
  — M3.4.
- ❌ Upload flow (`request_photo_upload`, `attach_photo`,
  `delete_photo`) — M3.5. **No photo service functions
  shipped in M3.2** — the storage backend they depend on
  doesn't exist yet.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ `update_report` function — M3.2 planning contract
  locks 7 functions; adding an eighth would invent a
  surface not committed to the planning artifact. M3.6 will
  re-open the question if operator evidence surfaces a case
  that add/update/delete-finding + complete cannot cover.
- ❌ Reopen workflow — deliberately absent per M3.2 design
  ("no reverse transition; author a new report instead").

## Files changed

- New: `backend/dealer_ai/services/condition_report.py`
  (567 lines — module docstring, two domain errors, three
  private helpers, seven public functions, `__all__`).
- New: `backend/dealer_ai/tests/test_condition_report_service.py`
  (1,047 lines — 61 tests across 13 classes).
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.2
  entry annotated with SHIPPED manifest.
- New: `docs/handoffs/SESSION_057_m3_inc2_service_layer.md`
  — this handoff.
- Modified: `00-START-NEXT-SESSION.md` overwritten with
  SESSION_058 = M3.3 priority.

No modifications to `models.py`, `admin.py`,
`services/tenancy.py`, `services/vehicle_ledger.py`,
`services/llm_safety.py`, `permissions.py`, any migration,
`requirements.txt`, or any frontend file.

## Recommended exact scope for SESSION_058 (M3.3 — Vehicle read-model extension)

Per `MILESTONE_3_PLANNING.md` §7 M3.3 (locked at SESSION_055;
unchanged):

**Scope.** Two `@property` accessors on `Vehicle` in
`backend/dealer_ai/models.py`, each delegating to the
`services/condition_report.py` functions this session
shipped:

- `latest_condition_report` — returns most recent report of
  any status (or `None`) via
  `services.condition_report.latest_condition_report(
      self, dealership=self.dealership)`.
- `latest_completed_condition_report` — returns most recent
  report with `status="complete"` (or `None`) via
  `services.condition_report.latest_completed_condition_report(
      self, dealership=self.dealership)`.

**No `@cached_property` in v1** — the M2.3 `ledger_totals`
cached-property pattern is proven for read-heavy repeated-
access data. M3's report accessors are lighter — the operator
UI reads at most both once per page load. If subsequent
operator UI work reveals repeated access, promote to
`@cached_property` at that moment; do not preemptively cache.

**Tests target.** ~15 focused tests covering: no reports
returns None, one draft returned by `latest_condition_report`
but None by `latest_completed_condition_report`, one complete
returned by both, multiple mixed returns most-recent per
accessor, cross-tenant vehicles never leak through,
`assertNumQueries(1)` verification per property access.

**Boundary.** Test baseline: 1,874 → ~1,889 pass. No
migrations. No API. No frontend.

**Explicit non-goals for M3.3.**

- ❌ Do NOT introduce `@cached_property` in v1.
- ❌ Do NOT add any other `@property` beyond the two named
  accessors.
- ❌ Do NOT touch the M3.2 service module or the M3.1
  models beyond adding the two property accessors on
  `Vehicle`.
- ❌ Do NOT add API endpoints, frontend, storage, or photo
  functions.

## Anchors that win on conflict for SESSION_058

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the property
   accessors read from the tenant substrate (via the
   Vehicle's own `dealership_id`).
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — the acceptance
   contract. §7 M3.1 and §7 M3.2 now annotated SHIPPED.
   §7 M3.3 is the sub-scope for the next session.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.3 (shape
   template — the M2 Vehicle read-model extension).
8. `docs/research/RECON_MAPPING.md` §2 + §12 +
   `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 2.
9. `docs/CAPABILITY_MATRIX.md`.
10. Most recent handoffs (this file,
    `SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

## Operational state (post-SESSION_057)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,874 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. M3 recon is in-store workflow.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session (no frontend edits).
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged this session; `npx tsc
  --noEmit` clean; `npx vite build` clean.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.2, so no round-trip re-run needed.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. Unchanged this session. M3.4
  will add the optional `AWS_*` set.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (so far):** M3.0 planning
  (SESSION_055) + M3.1 core models (SESSION_056) + M3.2
  service layer (SESSION_057 — this session). Remaining
  M3.3–M3.8 queued for SESSION_058–SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 + M3
  planning + M3.1 + M3.2 is recorded in the respective
  planning + retrospective + handoff docs. No new deferrals
  surfaced this session that don't fit existing docs.
