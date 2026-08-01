---
title: "SESSION_061 handoff — Milestone 3 · Increment 6A (condition-report admin API — core surface)"
status: historical
type: handoff
date: 2026-07-31
session: 061
milestone: 3
milestone_status: in-progress
increment: 6A
increment_status: shipped
commit: TBD
---

# SESSION_061 — Milestone 3 · Increment 6A (M3.6A — core condition-report admin API)

## What shipped

Six HTTP endpoints wiring the M3.1–M3.5 stack to the admin
authorization layer. Report + finding lifecycle only — photo
endpoints (M3.6B) queued for SESSION_062 per SESSION_061 spec
"increment discipline takes precedence over session-number
convenience."

Full backend suite: **2,067 pass, 1 skipped, 0 fail** (baseline
1,998 → +69; 0 regressions).

## Scope decision — M3.6 split into A + B

The original M3.6 planning entry listed 10 endpoints
(6 report + 3 photo + 1 local-upload receiver). Shipping all
10 in one session would produce ~110 tests with meaningful
verification overhead. Per SESSION_061 pushback, split into:

- **M3.6A (this session)** — 6 core report endpoints.
- **M3.6B (SESSION_062)** — 4 photo endpoints (request-upload,
  attach, delete, local-mode receiver).

Same governance / permission composition / error-mapping
contracts apply to both halves. `MILESTONE_3_PLANNING.md` §7
M3.6 now carries the split with M3.6A annotated SHIPPED and
M3.6B queued.

## Endpoints shipped (6)

All under `/api/dealer-ai/admin/vehicles/<stock_number>/…`,
composing `[IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership]`. Every view resolves
`dealership = get_current_dealership(request)` once, scopes
lookups explicitly, passes `dealership=` into every service
call.

- **`GET .../condition-report/latest/`** — returns
  `{vehicle, report}`; `report` is null on empty state.
  Findings + photos included in projection.
- **`POST .../condition-reports/`** — create draft. Returns 201.
- **`POST .../condition-reports/<report_id>/complete/`** —
  draft → complete. 200 on success, 409 on double-complete.
- **`POST .../condition-reports/<report_id>/findings/`** —
  add finding. 201 on success.
- **`PATCH .../findings/<finding_id>/`** — update finding
  (shared URL with DELETE).
- **`DELETE .../findings/<finding_id>/`** — delete finding
  (shared view function dispatches on method).

## Response contracts

**Report projection** (`_project_report`):

```
{
  "id": int,
  "status": "draft" | "complete",
  "status_display": "Draft" | "Complete",
  "inspector_name": str,
  "inspected_at": iso datetime str,
  "mileage_at_inspection": int,
  "completed_at": iso datetime str | null,
  "notes": str,
  "authored_by": username str | null,
  "created_at": iso datetime,
  "updated_at": iso datetime,
  "findings": [<finding projection>...]
}
```

**Finding projection** (`_project_finding`):

```
{
  "id": int,
  "category": str,               # canonical value
  "category_display": str,       # friendly label
  "severity": str,               # canonical value
  "severity_display": str,       # friendly label
  "description": str,
  "estimated_cost": "165.00" | null,   # 2-decimal string
  "notes": str,
  "created_at": iso datetime,
  "updated_at": iso datetime,
  "photos": [<photo projection>...]
}
```

**Photo projection** (`_project_photo`):

```
{
  "public_id": uuid str,     # NOT storage_key
  "content_type": str,
  "size_bytes": int,
  "caption": str,
  "uploaded_by": username str | null,
  "created_at": iso datetime,
  "signed_read_url": str,    # short-lived (900s cap)
  "read_url_expires_at": iso datetime
}
```

**Vehicle header** — reuses M2.6
`VehicleLedgerHeaderSerializer` (stock_number, vin, year,
make, model, trim, price, display_name).

**Money-string discipline** — `estimated_cost` uses the M2.6
`_money_str` / `_LEDGER_CENTS` `Decimal.quantize` pattern so
JavaScript `Number` cannot silently truncate precision.

## Tenant and permission behavior

**Permission matrix (5 cases per endpoint):**

1. Unauthenticated → 401/403.
2. Authenticated, no dealership role → 403.
3. Authenticated, advisor role only → 403.
4. Authenticated, porter role only → 403.
5. Sales manager at active tenant → 200/201/204.
6. Dealer owner at active tenant → 200/201/204.

**Cross-tenant data scoping (all 6 endpoints):**

- `stock_number` from another dealership → 404 (never 403 —
  never leak whether the resource exists in another tenant).
- `report_id` belonging to another dealership → 404.
- `finding_id` belonging to another dealership → 404.

**Server-owned fields (spoofing protection):**

- `dealership` — resolved from `get_current_dealership`;
  client-supplied values silently ignored.
- `authored_by` — set to `request.user`; client cannot forge.
- `status` — always `draft` at create; only
  `complete_report` transitions.
- `completed_at` — set atomically by the service; NULL at
  create.

## Error mapping (locked by tests)

| Exception | HTTP | Note |
|---|---|---|
| `CrossTenantConditionReportError` | 404 | Never leak cross-tenant existence |
| `ConditionReportImmutableError` | 409 | Completed-report edit refusal |
| `ValueError` (service) | 400 | Invalid category / severity / forbidden field |
| `ValidationError` (full_clean) | 400 | Model-layer invariant |
| Nonexistent vehicle / report / finding | 404 | Same shape as cross-tenant (no leak) |

Photo-specific errors (`PhotoNotYetUploadedError`,
`PhotoMetadataMismatchError`, `PhotoAlreadyAttachedError`,
`ObjectStorageError`) will be wired in M3.6B when the photo
endpoints ship.

## Local-upload behavior

**Not shipped in M3.6A.** The local-mode multipart receiver
is part of M3.6B per the spec's recommendation
("route may exist in all environments; local adapter active →
accepts multipart upload; S3 adapter active → return 404
rather than 501" — deferred to M3.6B with the rest of the
photo transport).

## Upload-authorization binding — honest limitation

M3.6A ships no photo endpoints, so the upload-intent-binding
question doesn't arise this session. **M3.6B will need to
address it honestly** — the SESSION_060 handoff already
documented that presigned URLs authorize an upload but persist
no intent record. The current mitigation (attach through the
finding-specific route + verify key namespace + verify UUID
not already attached) is sufficient for M3 v1; persistent
`UploadIntent` binding remains deferred unless implementation
evidence proves it is required now. **No `UploadIntent`
model shipped or planned in M3.**

## Tests added (69 total across 12 classes)

- **Permission matrix (30 tests)**: 6 endpoints × 5 outcomes
  each. Shared `_AuthMatrixBase` mixin subclassed per endpoint
  (`LatestReportAuth`, `CreateReportAuth`,
  `CompleteReportAuth`, `AddFindingAuth`, `UpdateFindingAuth`,
  `DeleteFindingAuth`). Reuses `_auth_helpers.make_user` +
  `make_membership`.
- **`ReadLatestBusinessFlow`** (6): empty state → null report,
  draft in projection, findings + photos included, latest
  ordering, unknown vehicle → 404, estimated_cost null
  serialization.
- **`CreateReportBusinessFlow`** (6): happy path (201),
  authored_by NOT spoofable, status/completed_at NOT
  spoofable, dealership NOT spoofable, required-field →
  400, unknown vehicle → 404.
- **`CompleteReportBusinessFlow`** (3): transition returns
  projection, double-complete → 409, cross-tenant report_id
  → 404.
- **`AddFindingBusinessFlow`** (5): happy path (201), invalid
  category → 400, invalid severity → 400, completed report
  → 409, no VehicleCost side effect.
- **`UpdateFindingBusinessFlow`** (3): happy path, no-op
  permitted, completed report → 409.
- **`DeleteFindingBusinessFlow`** (2): 204 on success + row
  removed, completed report → 409.
- **`CrossTenantDataScoping`** (5): every endpoint's cross-
  tenant lookup fails closed with 404.
- **`NoStorageKeyLeakage`** (2): read + create responses
  contain no `storage_key`, `bucket`, `aws_access_key_id`,
  or `aws_secret` substring.
- **`PublicSurfacesNeverExposeConditionReports`** (1):
  `salespeople-list` response contains no condition-report
  keywords.

## Query behavior

`GET .../condition-report/latest/` baseline: **4 queries**:

1. Vehicle lookup (`.filter(dealership=).get(stock_number=)`).
2. Latest report via
   `.filter(vehicle=, dealership=).order_by(...).first()`.
3. Findings prefetch (`prefetch_related("findings")`).
4. Photos prefetch (`prefetch_related("findings__photos")`).

Plus:
- Zero additional queries for `authored_by` (`select_related`)
  or `photos.uploaded_by` (nested prefetch).
- Zero DB or network calls for `photo_storage.generate_read_url`
  — presigned URL is client-side.

No N+1 per finding or photo. If a future edit surfaces
regression (e.g. removing the `prefetch_related`), the
`_project_photo` per-photo loop would fire additional queries
— but the query cost isn't currently locked with
`assertNumQueries` in the endpoint tests. Consider adding as
part of a query-hardening pass in a later session.

Create / complete / add-finding / update-finding endpoints
refetch the mutated row with prefetches so the returned
projection populates from the related-object cache. Cost:
~3–5 queries per write, dominated by the refetch.

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,067 tests, 1
  skipped, 0 fail** (up from 1,998; +69 new tests).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."
- **No frontend files changed** — verified by git status.
- **No storage_key leakage** — locked by
  `NoStorageKeyLeakage` (2 tests).
- **No public-surface condition-report leakage** — locked by
  `PublicSurfacesNeverExposeConditionReports` (1 test).
- **Zero real S3 or network access in tests** — reuses M3.4 /
  M3.5 local-adapter patterns.
- `DEFAULT_PERMISSION_CLASSES` remains unset (M1 · 4B
  invariant unchanged).

## Compatibility

Preserved unchanged (production code):

- All M1 tenancy substrate.
- All M1 identity + authentication.
- All M1 · 4D + M2.6 endpoint-level permissions —
  `IsSalesManagerOrOwnerAtActiveDealership` reused verbatim.
- Safety stack — no new scrub, no changes to any pre / post-
  LLM guard.
- Customer-facing surfaces.
- M2 ledger substrate.
- M3.1 model surface.
- M3.2 service module — no signature changes; used verbatim.
- M3.3 Vehicle `@property` accessors.
- M3.4 storage service — `generate_read_url` used verbatim in
  photo projections.
- M3.5 photo service — no changes; will be wired in M3.6B.
- Dealer identity resolution.
- Requirements — no changes.
- Frontend — no changes.

Modified (this session, additive-only):

- `dealer_ai/serializers.py` — 3 new request-serializer
  classes.
- `dealer_ai/views.py` — 5 new view functions + 3 projection
  helpers + 3 lookup helpers.
- `dealer_ai/urls.py` — 5 new URL patterns.

## Explicitly out of scope for M3.6A (queued or deferred)

- **QUEUED for M3.6B (SESSION_062):**
  - Photo `POST .../findings/<finding_id>/photos/request-upload/`
  - Photo `POST .../findings/<finding_id>/photos/`
  - Photo `DELETE .../photos/<public_id>/`
  - Local-mode `POST .../findings/<finding_id>/photos/local-upload/`
  - Domain-error mapping extensions for photo-specific errors.

- **DEFERRED to later increments or DEFERRED_IDEAS pile:**
  - Frontend — M3.7.
  - AI role — never in M3.
  - Report scoring / completion percentage.
  - WorkOrders / Vendor integration.
  - Image processing (thumbnails, EXIF stripping).
  - Public photo routes.
  - Upload-intent persistence
    (no `UploadIntent` model).
  - Generalized attachment framework.
  - Recon-manager permission role (M4).
  - Repair for 3 deferred M3.4-era 400-expected tests in
    `test_salesperson_and_assignment.py`.

## Files changed

- Modified: `backend/dealer_ai/serializers.py` — added
  `ConditionReportCreateRequestSerializer`,
  `ConditionFindingCreateRequestSerializer`,
  `ConditionFindingUpdateRequestSerializer` + M3.1 choice-
  constant imports.
- Modified: `backend/dealer_ai/views.py` — added 5 view
  functions (`admin_condition_report_latest`,
  `admin_condition_report_create`,
  `admin_condition_report_complete`,
  `admin_condition_finding_create`,
  `admin_condition_finding_detail`), 3 projection helpers
  (`_project_photo`, `_project_finding`, `_project_report`),
  3 lookup helpers, imports for `condition_report_service`
  + `photo_storage_service` + M3.2 domain errors.
- Modified: `backend/dealer_ai/urls.py` — 5 new URL patterns.
- New: `backend/dealer_ai/tests/test_admin_condition_report.py`
  (~740 lines, 69 tests).
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.6
  entry — split into M3.6A (SHIPPED annotation) + M3.6B
  (queued entry).
- New: `docs/handoffs/SESSION_061_m3_inc6a_admin_api.md` —
  this handoff.
- Modified: `00-START-NEXT-SESSION.md` overwritten with
  SESSION_062 = M3.6B priority.

No modifications to any model, migration, admin,
`services/condition_report.py`, `services/photo_storage.py`,
`services/vehicle_ledger.py`, `services/tenancy.py`,
`services/llm_safety.py`, `services/dealer_config.py`,
`permissions.py`, `requirements.txt`, or any frontend file.

## Recommended exact scope for SESSION_062 (M3.6B — photo API + local receiver)

Per `MILESTONE_3_PLANNING.md` §7 M3.6B (added at
SESSION_061):

**Scope.** Four endpoints:

- `POST .../findings/<finding_id>/photos/request-upload/` —
  wraps `condition_report_service.request_photo_upload`.
  Returns `{upload_target: {method, upload_url,
  storage_key, required_headers, expires_at}}`. Body
  accepts `content_type` only; server generates the UUID.
  Note: `storage_key` in the upload-target response is the
  narrow exception to the "never expose storage_key" rule
  — the client needs it to hand back to `attach_photo`.
- `POST .../findings/<finding_id>/photos/` — wraps
  `condition_report_service.attach_photo`. Body: `storage_key`,
  `content_type`, `size_bytes`, `caption` (optional).
  Returns `{photo: <projection>}` with 201.
- `DELETE .../photos/<public_id>/` — wraps
  `condition_report_service.delete_photo`. Path uses
  `public_id`, NOT `storage_key`. Lookup: tenant-scoped +
  finding-report-vehicle-chain-scoped. 204 on success.
- `POST .../findings/<finding_id>/photos/local-upload/` —
  local-mode multipart receiver. **Returns 404 in S3 mode**
  (do NOT advertise dev-only surface). When local adapter
  active, calls `photo_storage.store_local_upload`. Does
  NOT create the `ConditionFindingPhoto` row — the normal
  attach endpoint still performs metadata verification.

**Domain-error mapping extensions** — add to the M3.6A table:

- `PhotoNotYetUploadedError` → 409.
- `PhotoMetadataMismatchError` → 409.
- `PhotoAlreadyAttachedError` → 409.
- `InvalidStorageKeyError` → 400.
- `InvalidContentTypeError` → 400.
- `InvalidTTLError` → 400.
- `ObjectStorageError` → 502.
- `LocalUploadNotAvailableError` → 404 (dev-only surface
  hidden in S3 mode).

**Tests target.** ~40 focused endpoint tests. Baseline
2,067 → ~2,107. No frontend. No migrations. No AI.

**Explicit non-goals for M3.6B.**

- ❌ Frontend — M3.7.
- ❌ Modifications to M3.5 service signatures.
- ❌ New serializers beyond photo-request-upload +
  photo-attach input validators.
- ❌ Public photo routes.
- ❌ Repair for 3 deferred 400-expected tests.

## Anchors that win on conflict for SESSION_062

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M3.6B
   endpoint inherits the four-layer separation.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4, M3.5, M3.6A now annotated SHIPPED. §7 M3.6B
   is the sub-scope for the next session.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `docs/research/RECON_MAPPING.md` §2.5 + §13.1.
8. `docs/CAPABILITY_MATRIX.md`.
9. Most recent handoffs (this file,
   `SESSION_060_m3_inc5_upload_flow.md`,
   `SESSION_059_m3_inc4_storage.md`,
   `SESSION_058_m3_inc3_read_model.md`,
   `SESSION_057_m3_inc2_service_layer.md`,
   `SESSION_056_m3_inc1_core_models.md`,
   `SESSION_055_milestone_3_planning.md`).

## Operational state (post-SESSION_061)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists.
  Test baseline: **2,067 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` —
  NOT active.
- **Frontend (local):** Vite on `:5173`. Unchanged.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.6A.
- **Env-override surface:** unchanged.
- **New runtime primitives (M3.6A):** 6 admin endpoints
  under `/api/dealer-ai/admin/vehicles/<stock_number>/…`
  (condition-report core surface); 3 request serializers;
  3 dict-builder projections; 3 lookup helpers.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning + M3.1 core models + M3.2 service layer + M3.3
  Vehicle read-model + M3.4 storage abstraction + M3.5
  photo workflow + M3.6A core admin API (SESSION_061 —
  this session). Remaining: M3.6B (photo endpoints) +
  M3.7 (UI) + M3.8 (closeout) queued for
  SESSION_062 – SESSION_064.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Deferred test-hardening for three companion
  400-expected tests in
  `test_salesperson_and_assignment.py` remains noted in
  SESSION_059 handoff. No new deferrals surfaced this
  session that don't fit existing docs.
