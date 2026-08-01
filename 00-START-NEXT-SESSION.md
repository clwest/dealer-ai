---
state: active
date: 2026-07-31
last_session_shipped: SESSION_061
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: in-progress
next_session: SESSION_062
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: "6B"
next_increment_name: "M3.6B — Condition-report photo API + local-mode receiver"
---

# Next session — SESSION_062 · Milestone 3 · Increment 6B (M3.6B — photo API + local receiver)

> **Milestone 3 · Increment 6A (M3.6A) shipped at SESSION_061.**
> The core condition-report admin API is live: 6 endpoints
> (GET latest, POST create, POST complete, POST add-finding,
> PATCH/DELETE finding via shared view) with full permission
> matrix + domain-error mapping + no-storage_key-leakage +
> spoofing protection on authored_by / status / completed_at /
> dealership. 69 focused tests. See
> `docs/handoffs/SESSION_061_m3_inc6a_admin_api.md`.
>
> **SESSION_062 opens M3.6B = the 4 photo endpoints.** Photo
> request-upload, attach, delete, plus the local-mode
> multipart receiver. Extends the M3.6A error-mapping table
> with photo-specific errors. **Same governance / permission
> composition / response projections as M3.6A** — this session
> is largely mechanical wiring of the M3.5 photo service to
> HTTP.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md`.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4, M3.5, M3.6A now annotated SHIPPED. §7 M3.6B
   is the sub-scope for this session.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.

## What M3.6B delivers (per `MILESTONE_3_PLANNING.md` §7 M3.6B)

Four HTTP endpoints continuing the M3.6A pattern.

**In scope — endpoints:**

- `POST admin/vehicles/<stock_number>/findings/<finding_id>/photos/request-upload/`
  — wraps `condition_report_service.request_photo_upload`.
  Body: `{content_type}`. Returns
  `{upload_target: {method, upload_url, storage_key,
  required_headers, expires_at}}`. **Note:** `storage_key`
  appears in this specific response as the narrow exception
  — the client needs it to hand back to `attach_photo`.
  Every OTHER response omits `storage_key`.
- `POST admin/vehicles/<stock_number>/findings/<finding_id>/photos/`
  — wraps `condition_report_service.attach_photo`. Body:
  `{storage_key, content_type, size_bytes, caption?}`.
  Returns `{photo: <projection>}` with 201.
- `DELETE admin/vehicles/<stock_number>/photos/<uuid:public_id>/`
  — wraps `condition_report_service.delete_photo`.
  **Path uses `public_id`, NOT `storage_key`.** Lookup:
  tenant-scoped + finding-report-vehicle-chain-scoped. 204
  on success.
- `POST admin/vehicles/<stock_number>/findings/<finding_id>/photos/local-upload/`
  — local-mode multipart upload receiver. **Returns 404 in
  S3 mode (do NOT advertise dev-only surface).** When local
  adapter active, accepts multipart body, validates content
  type + enforces 25 MB ceiling, calls
  `photo_storage.store_local_upload`. **Does NOT create the
  `ConditionFindingPhoto` row** — the normal attach endpoint
  still performs metadata verification and persistence.

**Domain-error mapping — extensions to the M3.6A table:**

- `PhotoNotYetUploadedError` → 409.
- `PhotoMetadataMismatchError` → 409.
- `PhotoAlreadyAttachedError` → 409.
- `InvalidStorageKeyError` → 400.
- `InvalidContentTypeError` → 400.
- `InvalidTTLError` → 400.
- `ObjectStorageError` → 502.
- `LocalUploadNotAvailableError` → 404 (dev-only surface
  intentionally hidden in S3 mode).

**Explicitly out of scope (deferred to later increments):**

- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ Modifications to M3.5 service signatures.
- ❌ New serializers beyond photo-request-upload +
  photo-attach input validators (upload-target response is
  a dict-builder, matching M3.6A photo projection pattern).
- ❌ Public photo routes.
- ❌ Modifications to M3.6A endpoints (their projections
  already handle the photo array — nothing to backfill).
- ❌ Repair for 3 deferred M3.4-era 400-expected tests in
  `test_salesperson_and_assignment.py`.

## What SESSION_062 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.6B entry
     (added at SESSION_061).
   - `docs/handoffs/SESSION_061_m3_inc6a_admin_api.md` — the
     M3.6A shape M3.6B mirrors.
   - `docs/handoffs/SESSION_060_m3_inc5_upload_flow.md` —
     the M3.5 photo service M3.6B wraps.
   - `backend/dealer_ai/services/condition_report.py` —
     `request_photo_upload`, `attach_photo`, `delete_photo`
     signatures + their domain errors.
   - `backend/dealer_ai/services/photo_storage.py` —
     `store_local_upload` + `LocalUploadNotAvailableError`
     for the local-mode receiver.
   - `backend/dealer_ai/views.py` — M3.6A view patterns
     (lookup helpers, dealership resolution, error mapping).
     M3.6B additions follow the same shape.

2. **Verify starting state.**
   - `git status` — clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,067 pass, 1
     skipped, 0 fail**.

3. **Add request serializers** in `serializers.py`:
   - `PhotoRequestUploadSerializer` (content_type only).
   - `PhotoAttachSerializer` (storage_key, content_type,
     size_bytes, caption).
   - No new serializer needed for local-upload receiver
     (parses multipart directly).

4. **Add photo projection helper** in `views.py`. **Wait —
   this already exists** (`_project_photo` shipped in
   M3.6A). Reuse.

5. **Add 4 view functions in `views.py`:**
   - `admin_condition_photo_request_upload` (POST).
   - `admin_condition_photo_attach` (POST).
   - `admin_condition_photo_delete` (DELETE).
   - `admin_condition_photo_local_upload_receiver` (POST).

6. **Add lookup helper** in `views.py`:
   - `_lookup_photo_or_404(dealership, vehicle, public_id)`
     — traverses `finding__report__vehicle` to enforce the
     vehicle scope on delete.

7. **Wire 4 URL patterns** in `urls.py`.

8. **Import extensions in `views.py`:**
   - From `condition_report`: `PhotoNotYetUploadedError`,
     `PhotoMetadataMismatchError`,
     `PhotoAlreadyAttachedError`.
   - From `photo_storage`: `InvalidStorageKeyError`,
     `InvalidContentTypeError`, `InvalidTTLError`,
     `ObjectStorageError`, `LocalUploadNotAvailableError`,
     `store_local_upload`.

9. **No migration.** M3.6B is pure Python.

10. **Write focused tests.** Extend
    `test_admin_condition_report.py` OR add a companion
    file (decide based on file size — the current file is
    ~740 lines; adding ~40 more tests keeps it under 1200
    which is acceptable).

11. **Full suite + baseline.** ~2,107 pass (2,067 + ~40),
    1 skipped, 0 fail.

12. **Close SESSION_062 with:**
    - 4 view functions + URLs + focused tests committed.
    - Handoff at
      `docs/handoffs/SESSION_062_m3_inc6b_photo_api.md`.
    - Overwrite this file with SESSION_063 = M3.7 (UI)
      priority.
    - Planning §7 M3.6B annotated `SHIPPED at SESSION_062`.

## Explicit non-goals for SESSION_062

- ❌ Do NOT add any frontend file.
- ❌ Do NOT modify M3.1 models, migrations, or admin.
- ❌ Do NOT modify M3.2–M3.5 service signatures.
- ❌ Do NOT modify M3.6A endpoints, projections, or lookup
  helpers.
- ❌ Do NOT introduce an `UploadIntent` model (deferred per
  M3 spec).
- ❌ Do NOT create a production-looking local-upload
  endpoint that exists meaningfully in S3 mode (returns 404
  in S3 per spec).
- ❌ Do NOT let tests hit real S3.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT commit any real `AWS_*` or `OPENAI_API_KEY`.

## NEXT TASK

Start SESSION_062 with the read-first list above. Ship the 4
photo endpoints + local-mode receiver + ~40 focused tests.
Do NOT ship frontend.

Test baseline at SESSION_062 close: 2,067 → ~2,107.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4, M3.5, M3.6A SHIPPED; §7 M3.6B is the
   sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/research/RECON_MAPPING.md` §2.5 + §13.1
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs
   (`SESSION_061_m3_inc6a_admin_api.md`,
   `SESSION_060_m3_inc5_upload_flow.md`,
   `SESSION_059_m3_inc4_storage.md`,
   `SESSION_058_m3_inc3_read_model.md`,
   `SESSION_057_m3_inc2_service_layer.md`,
   `SESSION_056_m3_inc1_core_models.md`,
   `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_061 — M3.6A core admin API shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists.
  Test baseline: **2,067 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active.
- **Frontend (local):** Vite on `:5173`. Unchanged.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.6A.
- **Env-override surface:** unchanged this session.
- **New runtime primitives (M3.6A):** 6 admin endpoints
  under `/api/dealer-ai/admin/vehicles/<stock_number>/…`;
  3 request serializers; 3 dict-builder projection helpers;
  3 tenant-scoped lookup helpers.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning + M3.1 core models + M3.2 service layer + M3.3
  Vehicle read-model + M3.4 storage abstraction + M3.5
  photo workflow + M3.6A core admin API (SESSION_061 —
  this session). M3.6B (photo endpoints) + M3.7 (UI) +
  M3.8 (closeout) queued for SESSION_062 – SESSION_064.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
