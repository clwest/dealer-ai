---
title: "SESSION_058 handoff — Milestone 3 · Increment 3 (Vehicle condition-report read-model)"
status: historical
type: handoff
date: 2026-07-31
session: 058
milestone: 3
milestone_status: in-progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_058 — Milestone 3 · Increment 3 (M3.3 — Vehicle read-model extension)

## What shipped

Two `@property` accessors on the `Vehicle` model, each a one-line
delegator to the M3.2 service functions. Callers holding a
`Vehicle` instance can now ask "what is the current inspection
state of this stock number?" without knowing that
`ConditionReport` exists as a distinct row.

Plus 20 focused tests (target was ~15) that lock the delegation
contract, tenant isolation, and — critically — the query
behavior invariant: exactly 1 query per property access when
the caller has prefetched the dealership FK, and 2 queries for
two consecutive reads (the observable *absence* of caching).

No models added. No migrations. No service module changes. No
admin. No API. No frontend. No storage. No AI.

## Read-first pass performed

Per the start-here doc's recommended sequence, read in order:

1. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.3 detail +
   §1.3 Vehicle-read-model-extension design memo.
2. `docs/handoffs/SESSION_057_m3_inc2_service_layer.md` —
   shipped-surface manifest for the M3.2 service functions
   the new properties delegate to.
3. `backend/dealer_ai/services/condition_report.py` —
   specifically the `latest_condition_report` and
   `latest_completed_condition_report` signatures the
   properties delegate to (`(vehicle, *, dealership)`).
4. `backend/dealer_ai/models.py::Vehicle` — read the class
   to see the M2.3 `ledger_totals` `@cached_property`
   pattern, the M2.3 read-model comment header, and the
   existing function-local-import guard against import
   cycles (line 194–198).

## Concrete deliverables

### Vehicle model additions (`backend/dealer_ai/models.py`)

85 additive lines (0 deletions), appended at the end of the
`Vehicle` class body (before `class ChatSession`). Structure:

- **Comment-block header** — labels this as "Milestone 3 ·
  Increment 3 — Vehicle-as-condition-report-read-model,"
  restates the layer contract (Vehicle = read model / service
  = business layer), documents the no-caching rationale, and
  cross-references `MILESTONE_3_PLANNING.md` §1.3 + §7 M3.3.
- **`Vehicle.latest_condition_report`** (`@property`) — one-
  line delegator:
  ```python
  return latest_condition_report(self, dealership=self.dealership)
  ```
  Any status. Deterministic ordering inherited from the
  service function. Tenant resolves from `self.dealership`.
- **`Vehicle.latest_completed_condition_report`** (`@property`)
  — same shape, filtered to `status="complete"` by the
  underlying service.

### Import-cycle resolution

`services/condition_report.py` imports `ConditionReport`,
`ConditionFinding`, `Vehicle`, `Dealership`, and enum
constants from `..models`. A top-of-module import from
`models.py` back to the service would cycle at Python import
time (the partially-initialized `models` module would be
returned to the service, missing the not-yet-defined classes).

Each property uses a **function-local import** inside its
body — same pattern already established in `Vehicle.ledger_totals`
(M2.3) at line 194–198 and used throughout
`services/tenancy.py`. The first property has a code comment
naming the cycle it avoids and cross-referencing the
`ledger_totals` precedent; the second property has a shorter
"see above" comment.

Per SESSION_058 spec: "Do not restructure modules merely to
eliminate one local import." The function-local import is the
house style; no restructuring was performed.

### Query behavior

Locked by two `assertNumQueries` tests:

- **`assertNumQueries(1)` per property access when
  dealership is prefetched.** Production callers should
  fetch vehicles via `.select_related('dealership')` so the
  tenant FK is in memory; under that shape, each property
  adds exactly one `ConditionReport` lookup query. If a
  future edit introduces a hidden query (e.g. a
  cross-tenant recheck against the `Dealership` table), the
  test fails immediately.
- **`assertNumQueries(2)` for two consecutive reads on the
  same instance.** This is the observable *absence* of
  caching. If a future edit promotes either property to
  `@cached_property`, the assertion fails and forces the
  promotion to be deliberate rather than accidental.

Note on the natural query profile: without
`.select_related('dealership')` the FK access itself fires
an additional query (`self.dealership` returns a lazy FK).
The tests exercise the prefetched shape to isolate the
property's own cost from the caller's fetch strategy.

### Tests

`backend/dealer_ai/tests/test_vehicle_condition_report_properties.py`
— **20 tests** across three classes:

- **`LatestConditionReport`** (8 tests):
  - `test_returns_none_when_no_reports_exist`
  - `test_returns_the_only_draft_report`
  - `test_returns_the_only_completed_report`
  - `test_returns_newest_when_multiple_drafts_exist`
  - `test_returns_newest_when_multiple_completes_exist`
  - `test_mixed_state_returns_newest_regardless_of_status`
    — older complete + newer draft returns the draft.
  - `test_tenant_isolation_never_leaks_cross_tenant_reports`
    — cross-tenant vehicles' reports never surface.
  - `test_deterministic_across_repeated_reads` — 5
    consecutive property reads return identical PKs.

- **`LatestCompletedConditionReport`** (6 tests):
  - `test_returns_none_when_no_completed_reports_exist`
    (vehicle has only a draft).
  - `test_returns_none_when_vehicle_has_no_reports_at_all`.
  - `test_ignores_drafts_returns_older_complete` — the
    key filter-vs-latest distinction. Older complete
    surfaces even when a newer draft exists.
  - `test_returns_newest_completed_when_multiple_exist`.
  - `test_tenant_isolation_never_leaks_cross_tenant_reports`.
  - `test_deterministic_across_repeated_reads`.

- **`VehicleContract`** (6 tests):
  - `test_latest_condition_report_delegates_to_service` —
    mocks
    `dealer_ai.services.condition_report.latest_condition_report`
    with `unittest.mock.patch`; asserts one-call-only + call
    args `(vehicle, dealership=vehicle.dealership)`; asserts
    return-value passthrough via `assertIs(result, sentinel)`.
  - `test_latest_completed_condition_report_delegates_to_service`
    — same shape for the completed accessor.
  - `test_property_read_does_not_mutate_vehicle` — reads
    both properties; asserts `Vehicle.updated_at` byte-
    identical before and after (proves no hidden writes /
    side effects).
  - `test_latest_condition_report_costs_exactly_one_query_when_dealership_prefetched`
    — `assertNumQueries(1)`.
  - `test_latest_completed_condition_report_costs_exactly_one_query_when_dealership_prefetched`
    — `assertNumQueries(1)`.
  - `test_no_caching_repeated_reads_hit_db_every_time` —
    `assertNumQueries(2)` for two consecutive reads.

## Verification evidence

- `python3 manage.py test dealer_ai` → **1,894 tests, 1
  skipped, 0 fail** (up from 1,874; +20 new tests).
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
  any pre / post-LLM guard.
- Customer-facing surfaces — no changes.
- M2 ledger substrate — `services/vehicle_ledger.py`,
  `Vehicle.ledger_totals`, `VehicleCost` immutability,
  M2.5 scrub, M2.6 admin ledger endpoints, M2.7 operator
  UI all unchanged.
- M3.1 model surface — `ConditionReport`,
  `ConditionFinding`, `ConditionFindingPhoto`, migration
  `0015`, admin registrations all unchanged.
- M3.2 service module — `services/condition_report.py`
  unchanged; only new callers (the two new properties).
- Frontend — no changes.
- Storage — no changes; no `django-storages`, no `boto3`.

## Explicitly out of scope for M3.3 (deferred, unchanged)

- ❌ `@cached_property` — v1 is uncached. Promote with
  evidence in a later milestone if repeated-access surfaces.
- ❌ Any additional `@property` on `Vehicle` beyond the
  two named accessors (`finding_count_by_severity`,
  `most_recent_inspection_date`, `open_finding_count`,
  `condition_score`, `estimated_recon_total`, `photo_count`,
  `completion_percentage`, `report_age`, etc. — all
  deferred to M3.7 if UI surfaces the need).
- ❌ Storage abstraction — M3.4.
- ❌ Upload flow — M3.5.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.

## Files changed

- Modified: `backend/dealer_ai/models.py` — 85 additive lines
  (comment header + two `@property` methods with function-
  local imports). No deletions.
- New: `backend/dealer_ai/tests/test_vehicle_condition_report_properties.py`
  — 20 tests across 3 classes.
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.3
  entry annotated with SHIPPED manifest.
- New: `docs/handoffs/SESSION_058_m3_inc3_read_model.md` —
  this handoff.
- Modified: `00-START-NEXT-SESSION.md` overwritten with
  SESSION_059 = M3.4 priority.

No modifications to `admin.py`, `services/*.py` (any file),
`permissions.py`, any migration, `requirements.txt`, or any
frontend file.

## Recommended exact scope for SESSION_059 (M3.4 — Storage story)

Per `MILESTONE_3_PLANNING.md` §7 M3.4 (locked at SESSION_055;
unchanged). This is the load-bearing pre-implementation
decision that Milestone 3 planning §5.a resolved as Option A
— storage abstraction ships as its own increment BEFORE
`ConditionFindingPhoto` upload flow (M3.5) so M3.5 has a real
dependency to bind against.

**Scope.**

- `django-storages[s3]` added to `backend/requirements.txt`
  (pulls `boto3` transitively). No version bumps on any
  existing package.
- `backend/dealer_kit/settings.py::DEFAULT_FILE_STORAGE` —
  env-driven selection: `AWS_STORAGE_BUCKET_NAME` present →
  `storages.backends.s3.S3Storage`; else → Django's default
  `FileSystemStorage`. This preserves dev / test isolation
  (unset env means zero S3 network access from tests).
- New module `backend/dealer_ai/services/photo_storage.py`
  with the three functions the M3.5 upload flow will bind to:
  - `generate_upload_url(*, storage_key, content_type,
    dealership) -> dict` — returns
    `{upload_url, storage_key, expires_at, method}`;
    content-type whitelist enforced at the URL boundary; TTL
    ≤ 900 seconds.
  - `object_exists(storage_key: str) -> bool` — HEAD
    verification. Used by M3.5's `attach_photo` to reject
    metadata for objects that don't actually exist.
  - `generate_read_url(*, storage_key, ttl_seconds=900) ->
    str` — short-TTL signed read URL. No permanent public
    URLs (condition photos may show identifying details;
    warranty-defense value depends on the store controlling
    access).
- Env-var documentation in the settings module header
  comment: `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`,
  `AWS_S3_ENDPOINT_URL` (for S3-compatible providers),
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `AWS_S3_CUSTOM_DOMAIN` (CDN). All optional; unset = local
  `FileSystemStorage` fall-through.
- ~25 focused tests: content-type whitelist enforcement
  (non-image raises `ValueError`), TTL cap (never > 900),
  URL includes the storage key, dev / test fall-through to
  `FileSystemStorage` when env unset. Tests use `moto` or an
  S3-compatible mock — **zero real network access**.

**Boundary.** Test baseline: 1,894 → ~1,919. One new
dependency. No new models. No API. No frontend.

**Explicit non-goals for M3.4.**

- ❌ Do NOT add the `ConditionFindingPhoto` upload flow —
  that is M3.5. The M3.1 model exists; the service functions
  that use it land in M3.5.
- ❌ Do NOT modify any existing model or service beyond
  adding the new `photo_storage.py` module.
- ❌ Do NOT add any API endpoint — M3.6.
- ❌ Do NOT touch the M2 ledger substrate or the safety
  stack.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT let tests hit real S3 — use `moto` or fixtures.

## Anchors that win on conflict for SESSION_059

1. `docs/PROJECT_RULES.md` — six governance rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md`.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, §7
   M3.2, §7 M3.3 now annotated SHIPPED. §7 M3.4 is the
   sub-scope for the next session. **§5.a — the load-
   bearing storage decision (Option A) — is the design
   memo M3.4 implements verbatim.**
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b — for the
   "one dependency, well-scoped" precedent M3.4 follows.
8. `docs/research/RECON_MAPPING.md` §2.5 (photos in
   condition reporting) + §13.1 (warranty exposure —
   condition documentation is the legal record) +
   `VEHICLE_CENTRIC_PIVOT.md` "Technical debt to pay down
   FIRST" item 3.
9. `docs/CAPABILITY_MATRIX.md`.
10. Most recent handoffs (this file,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

## Operational state (post-SESSION_058)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists
  (`slug='default'`). No pending migrations. Test baseline:
  **1,894 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged this session; `npx tsc
  --noEmit` clean; `npx vite build` clean.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.3; last verified clean-slate
  round-trip was SESSION_056.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. Unchanged this session. M3.4
  will add the optional `AWS_*` set.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (so far):** M3.0 planning
  (SESSION_055) + M3.1 core models (SESSION_056) + M3.2
  service layer (SESSION_057) + M3.3 Vehicle read-model
  (SESSION_058 — this session). Remaining M3.4–M3.8 queued
  for SESSION_059–SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea from Milestones 1 + 2 + M3
  planning + M3.1 + M3.2 + M3.3 is recorded in the
  respective planning + retrospective + handoff docs. No
  new deferrals surfaced this session that don't fit
  existing docs.
