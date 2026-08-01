---
title: "SESSION_060 handoff — Milestone 3 · Increment 5 (photo attachment workflow)"
status: historical
type: handoff
date: 2026-07-31
session: 060
milestone: 3
milestone_status: in-progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_060 — Milestone 3 · Increment 5 (M3.5 — photo attachment workflow)

## What shipped

Three new public service functions in
`services/condition_report.py` (`request_photo_upload`,
`attach_photo`, `delete_photo`) plus five new storage
primitives in `services/photo_storage.py`
(`ObjectMetadata`, `get_object_metadata`,
`parse_canonical_key`, `delete_object`, `store_local_upload`)
plus five new domain errors. 58 focused tests. Zero real
network. Zero new migrations, models, admin, API, frontend,
or AI.

**M3.4 → M3.5 handshake contract implemented as spec'd.** The
service refuses to attach a photo based on a Boolean HEAD
alone — `attach_photo` HEAD-fetches the actual
`ObjectMetadata` and verifies `content_type` + `size_bytes`
against the client-declared values. Missing object →
`PhotoNotYetUploadedError`. Any metadata drift →
`PhotoMetadataMismatchError`.

Full backend suite: **1,998 pass, 1 skipped, 0 fail**
(baseline 1,940 → +58; 0 regressions).

## The M3.5 refinements (per SESSION_060 spec)

1. **`object_exists` alone is NOT sufficient for attach.**
   New primitive `get_object_metadata(storage_key) ->
   ObjectMetadata` returns `content_type`, `size_bytes`,
   `exists`. `attach_photo` runs five verifications before
   creating the row.
2. **Storage-first delete strategy.** `delete_photo` deletes
   the storage object first; already-missing = idempotent
   success; real provider failure retains the DB row and
   raises `ObjectStorageError`.
3. **Canonical key parsing lives in `photo_storage.py`.** New
   `parse_canonical_key(storage_key) -> (slug, uuid)`. No
   regex or string-slicing in `condition_report.py`. No
   `boto3` / `storages` imports in `condition_report.py`.
4. **Duplicate `storage_key` → predictable domain error.**
   Pre-save `.exists()` check raises
   `PhotoAlreadyAttachedError` — surfaces a stable API
   contract instead of leaking Django's `ValidationError`
   from `validate_unique`.
5. **`store_local_upload` is dev-only + narrow.** Enforces
   canonical key, MIME whitelist, 25 MB size ceiling. Raises
   `LocalUploadNotAvailableError` in S3 mode.
6. **No API / view / multipart endpoint in M3.5.** HTTP
   transport is M3.6.

## Read-first pass performed

1. `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.5 detail +
   §1.5 handshake contract ("photo rows represent attached
   objects, never upload intentions").
2. `docs/handoffs/SESSION_059_m3_inc4_storage.md` — the M3.4
   surface M3.5 binds against.
3. `backend/dealer_ai/services/photo_storage.py` — every M3.4
   function signature + adapter shape + local URL marker
   contract.
4. `backend/dealer_ai/services/condition_report.py` — M3.2
   patterns (fail-closed cross-tenant guard,
   `_refresh_and_assert_draft`, `full_clean` before save,
   `dealership=` on every function).
5. `backend/dealer_ai/tests/test_condition_report_service.py`
   — test-file shape.

## Concrete deliverables

### Storage service extensions (`services/photo_storage.py`)

**New public surface:**

- `ObjectMetadata` (frozen dataclass) — `content_type`,
  `size_bytes`, `exists`. Provider-neutral HEAD result. `etag`
  intentionally excluded from the public contract (S3 has it,
  FS does not; if a future caller needs checksums that's a
  separate design memo).
- `get_object_metadata(storage_key: str) -> ObjectMetadata`
  — HEAD via adapter; missing object returns `exists=False`
  (no exception); backend fault raises `ObjectStorageError`.
- `parse_canonical_key(storage_key: str) -> tuple[str,
  uuid.UUID]` — the single place condition-report code
  touches the key format. Uses a named-group version of the
  canonical regex; raises `InvalidStorageKeyError` on any
  mismatch.
- `delete_object(storage_key: str) -> None` — idempotent on
  missing; raises `ObjectStorageError` on real backend fault.
- `store_local_upload(*, storage_key, content_type, data:
  bytes) -> ObjectMetadata` — dev-only writer. Enforces
  canonical key, MIME whitelist, 25 MB size ceiling, non-empty
  bytes. Raises `LocalUploadNotAvailableError` when the active
  adapter is `_S3Adapter`.
- `LocalUploadNotAvailableError(RuntimeError)` — new domain
  error; distinct from `ObjectStorageError` (backend fault)
  so callers can distinguish routing bugs from storage
  failures.

**Adapter protocol extensions:**

- `_PhotoStorageAdapter` protocol adds `get_object_metadata`
  and `delete_object`.
- `_LocalAdapter` implements both plus a local-only
  `store_local_upload`. Uses a per-key
  `<key>.content-type` sidecar file to round-trip MIME (Django's
  `FileSystemStorage` doesn't record content type on disk).
- `_S3Adapter` implements `get_object_metadata` via
  `head_object` (parses `ContentType` + `ContentLength`) and
  `delete_object` via `delete_object` (idempotent on 404,
  wraps `AccessDenied` + `BotoCoreError` in
  `ObjectStorageError`).

### Service extensions (`services/condition_report.py`)

**New public functions:**

- `request_photo_upload(finding, *, dealership, content_type,
  uploaded_by=None) -> UploadTarget` — validates cross-tenant
  (finding chain), refreshes + asserts parent report is
  draft, generates fresh `uuid.uuid4()`, calls
  `photo_storage.generate_upload_target`. **Does NOT create a
  row.** `uploaded_by` accepted for M3.6 request-context wiring
  but has no v1 effect (the row lands later in `attach_photo`).
- `attach_photo(finding, *, dealership, storage_key,
  content_type, size_bytes, caption="", uploaded_by=None) ->
  ConditionFindingPhoto` — five verifications: cross-tenant,
  draft-parent, canonical shape, key-namespace-matches-tenant,
  actual-metadata-matches-declared. Pre-save duplicate check
  raises `PhotoAlreadyAttachedError`. `full_clean()` before
  `save()`. `uploaded_by` persisted on row for provenance.
- `delete_photo(photo, *, dealership) -> None` — storage-
  first strategy: `photo_storage.delete_object(...)` runs
  first; if it raises `ObjectStorageError`, the DB row is
  retained and the error bubbles up. Only after storage
  succeeds (or object confirmed absent) does the row get
  dropped.

**New domain errors (all subclass `ValueError`):**

- `PhotoNotYetUploadedError` — HEAD reports missing object at
  attach time. Distinct from `ObjectStorageError` (real
  backend fault). Callers (M3.6 API) map to HTTP 409 Conflict.
- `PhotoMetadataMismatchError` — actual `size_bytes` or
  `content_type` differs from client-declared. Distinct from
  `PhotoNotYetUploadedError` so callers can surface a specific
  "upload landed but drift detected" message.
- `PhotoAlreadyAttachedError` — a
  `ConditionFindingPhoto` row already exists for the given
  `storage_key`. Predictable domain error; callers map to
  HTTP 409 without string-matching Django's
  `ValidationError.message_dict` keys.

**New private helper:**

- `_assert_photo_tenant(photo, dealership)` — verifies the
  photo's denormalized `dealership_id` + delegates to
  `_assert_finding_tenant` for the finding → report → vehicle
  chain.

### Tests

**`backend/dealer_ai/tests/test_condition_report_photos.py`
— 29 tests across 4 classes:**

- `RequestPhotoUpload` (7) — returns `UploadTarget` (local
  marker), no row persisted, completed report rejected,
  cross-tenant rejected, all 4 content types accepted, invalid
  content type rejected, fresh key per call.
- `AttachPhoto` (12) — happy path (row + public_id from key),
  `uploaded_by` preserved, missing object raises
  `PhotoNotYetUploadedError`, size mismatch raises
  `PhotoMetadataMismatchError`, content_type mismatch raises
  same, malformed key rejected, cross-tenant key (valid shape
  but wrong slug) rejected, cross-tenant finding rejected,
  completed report rejected, duplicate attach raises
  `PhotoAlreadyAttachedError`, no row created on missing
  object failure, no row created on size mismatch, UUID
  extracted via `parse_canonical_key`.
- `DeletePhoto` (6) — draft delete removes row + object,
  completed rejected, cross-tenant rejected, missing storage
  idempotent, provider failure retains row, storage delete
  precedes row delete (verified with tracked-call-order patch).
- `EstimatedCostStillNoOp` (3) — composite invariant: with a
  finding carrying `estimated_cost=100.00`,
  `request_photo_upload`, `attach_photo`, and `delete_photo`
  all create ZERO `VehicleCost` rows. Locks the M3.1 model-
  layer + M3.2 service-layer + M3.5 photo-layer invariant.

**`backend/dealer_ai/tests/test_photo_storage.py` — +29 tests
across 6 new classes (baseline 46 → 75):**

- `ParseCanonicalKey` (7) — canonical shape, alternate tenant,
  malformed, path-traversal, missing suffix, non-string,
  returns `uuid.UUID` (not string).
- `GetObjectMetadataLocal` (3) — missing returns
  `exists=False`, store→metadata roundtrip reflects declared
  content type + size, invalid key rejected before backend.
- `GetObjectMetadataS3` (3) — HEAD success parses
  `ContentType` + `ContentLength`, 404 returns
  `exists=False`, `AccessDenied` raises `ObjectStorageError`.
- `DeleteObjectLocal` (3) — missing is no-op, delete after
  store removes object + sidecar, invalid key rejected.
- `DeleteObjectS3` (3) — normal delete calls boto with
  bucket + key, 404 is idempotent success, `AccessDenied`
  raises `ObjectStorageError`.
- `StoreLocalUpload` (8) — valid write, invalid key /
  invalid MIME / non-bytes / zero-byte / over-ceiling
  rejected, replaces previous at same key, raises
  `LocalUploadNotAvailableError` in S3 mode.
- `ObjectMetadataDataclass` (2) — fields populated,
  frozen + immutable.

## Verification evidence

- `python3 manage.py test dealer_ai` → **1,998 tests, 1
  skipped, 0 fail** (up from 1,940; +58 new tests).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."
- **No `boto3` or `storages` import in
  `services/condition_report.py`** (verified via `grep`).
  All provider-specific behavior remains inside adapters
  behind `photo_storage.py`.
- No network calls in any test — verified by construction:
  all S3 tests inject a `MagicMock` via
  `_S3Adapter._boto3_client` patch; local tests write to
  `MEDIA_ROOT/condition-photos` (filesystem).

## Compatibility

Preserved unchanged (production code):

- M1 tenancy substrate.
- M1 identity + authentication.
- M1 · 4D + M2.6 endpoint-level permissions.
- Safety stack.
- Customer-facing surfaces.
- M2 ledger substrate (`estimated_cost` still never touches
  `VehicleCost` — locked by three new tests with photos
  present).
- M3.1 model surface + migration `0015` + admin.
- M3.2 service module — no signature changes; three new
  functions added at end of file.
- M3.3 Vehicle `@property` accessors.
- M3.4 storage service — public API preserved; four new
  functions + one dataclass + one error added.
- Dealer identity resolution.
- Frontend — no changes.
- Requirements — no changes.

Modified (this session):

- `services/photo_storage.py` — additive extensions.
- `services/condition_report.py` — additive extensions.
- Two test files (one extended, one new).

## Explicitly out of scope for M3.5 (deferred, unchanged)

- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ Modifications to `ConditionFindingPhoto` model shape.
- ❌ Image processing / thumbnails / EXIF stripping.
- ❌ Public galleries / read-only sharing routes.
- ❌ Report completion API surface (still M3.6).
- ❌ Cross-photo repair for the three deferred M3.4-era
  400-expected test methods — separate scope decision.
- ❌ WorkOrders or VehicleCost integration.
- ❌ Generalized attachment framework — M3.5 ships only
  `ConditionFindingPhoto` behavior.

## Files changed

- Modified: `backend/dealer_ai/services/photo_storage.py`.
- Modified: `backend/dealer_ai/services/condition_report.py`.
- Modified: `backend/dealer_ai/tests/test_photo_storage.py`
  (+29 tests, 46 → 75 total).
- New: `backend/dealer_ai/tests/test_condition_report_photos.py`
  (29 tests).
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.5
  annotated SHIPPED with six refinements.
- New: `docs/handoffs/SESSION_060_m3_inc5_upload_flow.md` —
  this handoff.
- Modified: `00-START-NEXT-SESSION.md` overwritten with
  SESSION_061 = M3.6 priority.

No modifications to any model, admin, migration, view,
frontend, `services/vehicle_ledger.py`, `services/tenancy.py`,
`services/llm_safety.py`, `services/dealer_config.py`,
`permissions.py`, or `requirements.txt`.

## Recommended exact scope for SESSION_061 (M3.6 — Admin API + permission matrix)

Per `MILESTONE_3_PLANNING.md` §7 M3.6, adapted to the M3.5
shipped surface:

**Scope.**

- Eight admin endpoints under
  `/api/dealer-ai/admin/vehicles/<stock_number>/…` per the
  planning contract:
  - `GET .../condition-report/latest/` — returns latest
    report (any status) with findings + photos (signed read
    URLs); 404 if none.
  - `POST .../condition-reports/` — create draft report.
  - `POST .../condition-reports/<report_id>/complete/` —
    transition draft → complete.
  - `POST .../condition-reports/<report_id>/findings/` —
    add finding to draft.
  - `PATCH .../findings/<finding_id>/` — update finding
    on draft.
  - `DELETE .../findings/<finding_id>/` — delete finding
    from draft.
  - `POST .../findings/<finding_id>/photos/request-upload/`
    — issue a presigned upload target.
  - `POST .../findings/<finding_id>/photos/` — attach a
    photo after upload completes.
  - `DELETE .../photos/<public_id>/` — delete a photo (path
    uses `public_id`, NOT `storage_key`).
- Plus a local-mode upload receiver endpoint
  (`POST .../findings/<finding_id>/photos/local-upload/`)
  when the storage adapter is `_LocalAdapter` — accepts
  multipart body, calls `photo_storage.store_local_upload`.
  In S3 mode this endpoint should 404 or 501.
- Every endpoint composes
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`
  (M1 · 4D pattern, reused verbatim).
- Every endpoint calls `dealership =
  get_current_dealership(request)` once at top and threads
  it into every service call.
- Cross-tenant `stock_number` / `report_id` / `finding_id` /
  `public_id` lookups fail closed (404).
- Full permission matrix per endpoint (unauth 401,
  wrong-role 403, wrong-tenant 404, correct owner 200,
  correct sales_manager 200 — 5 cases minimum per endpoint).
- Domain-error → HTTP-status mapping table:
  - `CrossTenantConditionReportError` → 404 (never leak
    whether the resource exists cross-tenant).
  - `ConditionReportImmutableError` → 409 Conflict.
  - `PhotoNotYetUploadedError` → 409.
  - `PhotoMetadataMismatchError` → 409.
  - `PhotoAlreadyAttachedError` → 409.
  - `InvalidStorageKeyError` → 400.
  - `InvalidContentTypeError` → 400.
  - `InvalidTTLError` → 400.
  - `ObjectStorageError` → 502 (upstream backend fault).
  - `ValidationError` → 400.

**Tests.** ~80 focused endpoint tests: full permission
matrix per endpoint + happy-path business flows + domain-
error mapping + signed-URL generation for reads. Target
baseline delta: 1,998 → ~2,080.

**Explicit non-goals for M3.6.**

- ❌ Frontend — M3.7.
- ❌ AI role.
- ❌ Modifications to any M3.1–M3.5 model or service beyond
  wiring endpoints (no signature changes).
- ❌ Modifications to `services/tenancy.py`,
  `services/llm_safety.py`, or any pre / post-LLM guard.
- ❌ Repairing the three deferred M3.4-era 400-expected
  tests unless they block the increment.

## Anchors that win on conflict for SESSION_061

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M3.6
   endpoint inherits the four-layer separation; M3.6 is the
   layer-2 (authorization) + layer-1 (identity) wiring for
   the M3.1–M3.5 stack.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4, M3.5 now annotated SHIPPED. §7 M3.6 is the
   sub-scope for the next session.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `docs/research/RECON_MAPPING.md` §2.5 + §13.1.
8. `docs/CAPABILITY_MATRIX.md`.
9. Most recent handoffs (this file,
   `SESSION_059_m3_inc4_storage.md`,
   `SESSION_058_m3_inc3_read_model.md`,
   `SESSION_057_m3_inc2_service_layer.md`,
   `SESSION_056_m3_inc1_core_models.md`,
   `SESSION_055_milestone_3_planning.md`).

## Operational state (post-SESSION_060)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists.
  Test baseline: **1,998 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active.
- **Frontend (local):** Vite on `:5173`. Unchanged.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.5.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`, `AWS_STORAGE_BUCKET_NAME`,
  `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`,
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `AWS_S3_CUSTOM_DOMAIN`. Unchanged this session.
- **New runtime primitives (M3.5):**
  `services/condition_report`:
  `request_photo_upload`, `attach_photo`, `delete_photo`,
  `PhotoNotYetUploadedError`,
  `PhotoMetadataMismatchError`,
  `PhotoAlreadyAttachedError`.
  `services/photo_storage`: `ObjectMetadata`,
  `get_object_metadata`, `parse_canonical_key`,
  `delete_object`, `store_local_upload`,
  `LocalUploadNotAvailableError`.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning (SESSION_055) + M3.1 core models (SESSION_056) +
  M3.2 service layer (SESSION_057) + M3.3 Vehicle
  read-model (SESSION_058) + M3.4 storage abstraction
  (SESSION_059) + M3.5 photo workflow (SESSION_060 — this
  session). Remaining M3.6–M3.8 queued for SESSION_061 —
  SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Deferred test-hardening for three companion
  400-expected tests in
  `test_salesperson_and_assignment.py` (surfaced at M3.4
  compat patch) noted in the SESSION_059 handoff and
  approved by the user as deferred; may repair opportunistically
  in a future test-hardening session.
