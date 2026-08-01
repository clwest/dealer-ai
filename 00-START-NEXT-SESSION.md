---
state: active
date: 2026-07-31
last_session_shipped: SESSION_059
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: in-progress
next_session: SESSION_060
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: 5
next_increment_name: "M3.5 — Condition-finding photo upload & attachment workflow"
---

# Next session — SESSION_060 · Milestone 3 · Increment 5 (M3.5 — photo upload & attachment workflow)

> **Milestone 3 · Increment 4 (M3.4) shipped at SESSION_059.**
> `services/photo_storage.py` (provider-neutral, PUT-based
> presign, canonical dealership-namespaced keys,
> `LOCAL_UPLOAD_URL_MARKER` / `LOCAL_READ_URL_MARKER` for dev)
> is live. `STORAGES` dict configured with dedicated
> `condition_photos` alias (env-driven S3 vs FileSystemStorage).
> 46 focused tests exercise both adapters with zero network.
> Two compat patches also landed (`httpx<0.28` transitive pin +
> four test-only `format="json"` fixes). See
> `docs/handoffs/SESSION_059_m3_inc4_storage.md`.
>
> **SESSION_060 opens M3.5 = the service functions that bind
> against M3.4 to create, HEAD-verify, attach, and delete
> `ConditionFindingPhoto` rows.** Extends
> `services/condition_report.py`. **The M3.4 → M3.5 handshake
> contract** (planning §1.5 design note): photo rows are
> created only AFTER `photo_storage.object_exists(...)` HEAD-
> verifies the object landed. No half-attached rows in the DB.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M3.5 service
   entry threads `dealership=` explicitly (M3.2 pattern).
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2, M3.3,
   M3.4 now annotated SHIPPED. §7 M3.5 is the sub-scope this
   session ships. **§1.5 design notes ("public identity is a
   UUID," "photo rows represent attached objects, never upload
   intentions") are the load-bearing M3.4 → M3.5 handshake
   contract.**
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 — lesson 3
   (one authoritative write path per operation) applies to
   the new photo functions.
7. `docs/research/RECON_MAPPING.md` §2.5 (photos in condition
   reporting) + §13.1 (warranty exposure — condition
   documentation is the legal record).

## What M3.5 delivers (per `MILESTONE_3_PLANNING.md` §7 M3.5)

Three new public functions in
`backend/dealer_ai/services/condition_report.py`, plus a
Django-side upload helper for the local dev/test flow.

**In scope:**

- `request_photo_upload(finding, *, dealership, content_type,
  uploaded_by=None) -> photo_storage.UploadTarget` — validates
  parent report is `draft` via `_refresh_and_assert_draft`;
  validates `content_type` (M3.4's whitelist enforces it too,
  but reject early with a clear message); generates a fresh
  `photo_uuid = uuid.uuid4()`; calls
  `photo_storage.generate_upload_target(dealership=dealership,
  photo_uuid=photo_uuid, content_type=content_type)`; returns
  the `UploadTarget`. **DOES NOT create a
  `ConditionFindingPhoto` row.**
- `attach_photo(finding, *, dealership, storage_key,
  content_type, size_bytes, caption="", uploaded_by=None)
  -> ConditionFindingPhoto` — HEAD-verifies the object exists
  at `storage_key` via `photo_storage.object_exists(...)`;
  extracts `photo_uuid` from the canonical key (or accepts it
  as a separate arg — decide at implementation time based on
  what the M3.6 API contract will pass); creates the row with
  `full_clean()` before `save()`. Cross-tenant guard runs at
  entry.
- `delete_photo(photo, *, dealership) -> None` — refuses when
  parent report is complete; deletes the row (source of
  truth); best-effort delete on the storage object via a new
  `photo_storage.delete_object(...)` helper (may need to add
  in M3.4 or leave as `TODO(M3.5)` — decide at implementation
  time).
- Two new domain errors (as needed):
  - `PhotoNotYetUploadedError(ValueError)` — `attach_photo`
    called before the client has PUT bytes to the presigned
    URL. Distinct from `ObjectStorageError` (backend fault)
    and `InvalidStorageKeyError` (malformed key).
  - `PhotoDeletionError(ValueError)` if a storage-side
    delete fails and the row was already gone — probably
    not needed in v1; add only if a failure mode surfaces.
- Django-side upload helper for local dev: extend
  `_LocalAdapter` in `services/photo_storage.py` (or add a
  companion `services/photo_storage_local_upload.py`) with a
  function that accepts direct bytes and writes them to
  `storages["condition_photos"]` under the canonical key. The
  M3.6 upload endpoint (later increment) will invoke this
  when it detects the `LOCAL_UPLOAD_URL_MARKER` prefix in the
  presigned "URL." For M3.5, ship the helper + tests; the
  endpoint that calls it lands with M3.6.

**Explicitly out of scope (deferred to specific later
increments):**

- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ Modifications to `ConditionFindingPhoto` model shape.
- ❌ Modifications to M3.4 storage service beyond adding
  `delete_object` if needed + the local-upload helper.
- ❌ Image processing (thumbnails, EXIF stripping,
  resizing).
- ❌ Public galleries or read-only sharing routes.

## What SESSION_060 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.5 detail +
     §1.5 design notes (both refinements land in the M3.5
     workflow).
   - `docs/handoffs/SESSION_059_m3_inc4_storage.md` — the
     M3.4 storage service shape M3.5 consumes.
   - `backend/dealer_ai/services/photo_storage.py` — every
     M3.4 public function signature.
   - `backend/dealer_ai/services/condition_report.py` — the
     M3.2 module M3.5 extends. Especially the
     `_refresh_and_assert_draft` helper, the cross-tenant
     guard pattern, and `add_finding` for the shape M3.5's
     photo functions mirror.
   - `backend/dealer_ai/tests/test_condition_report_service.py`
     — the test-file shape M3.5 mirrors.

2. **Verify starting state.**
   - `git status` — clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **1,940 pass, 1
     skipped, 0 fail**.
   - `python3 -c "import boto3; print(boto3.__version__)"`
     → 1.37.19 (already installed via M3.4).
   - `python3 -c "import storages"` → 1.14.6 (already
     installed).

3. **Author the three photo functions** in
   `services/condition_report.py`. Follow the M3.2 shape
   (fail-closed cross-tenant guard at entry, `full_clean()`
   before save, `_refresh_and_assert_draft` on mutations).
   Import from `services/photo_storage` at the top of the
   file (no cycle — `photo_storage.py` does not import from
   `condition_report.py`).

4. **Author the local-mode upload helper** in
   `services/photo_storage.py` (or a companion file). Accepts
   direct bytes; writes to `storages["condition_photos"]`
   under a canonical key. Add a corresponding test class.

5. **Write focused tests.** Add to
   `tests/test_condition_report_service.py` (or a new file
   `tests/test_condition_report_photos.py` if it grows large).
   Target ~35 tests: request-then-attach happy path,
   HEAD-verification refusal on missing object, cross-tenant
   on all three, finding-must-be-draft on all three,
   `estimated_cost`-still-never-touches-VehicleCost composite
   check with photos present, local-mode upload helper roundtrip.

6. **No migration.** M3.5 is pure Python. Confirm.

7. **Full suite + baseline.** ~1,975 pass (1,940 + ~35),
   1 skipped, 0 fail.

8. **Close SESSION_060 with:**
   - Service extension + local-upload helper + focused tests
     committed.
   - Handoff at
     `docs/handoffs/SESSION_060_m3_inc5_upload_flow.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     SESSION_061 = M3.6 (API endpoints) priority.
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.5 entry
     annotated in-place with `SHIPPED at SESSION_060` +
     shipped-surface manifest.

## Explicit non-goals for SESSION_060

- ❌ Do NOT add API endpoints — M3.6.
- ❌ Do NOT add frontend — M3.7.
- ❌ Do NOT modify `ConditionFindingPhoto` model, migration,
  or admin.
- ❌ Do NOT introduce image processing, thumbnails, EXIF
  stripping.
- ❌ Do NOT modify `services/vehicle_ledger.py`,
  `services/llm_safety.py`, `services/tenancy.py`,
  `services/dealer_config.py`, or `permissions.py`.
- ❌ Do NOT modify M3.1 models, M3.2 non-photo service
  functions, M3.3 Vehicle properties, or M3.4 core storage
  API beyond adding `delete_object` and the local-upload
  helper if needed.
- ❌ Do NOT let tests hit real S3 — use the M3.4 mock
  patterns (`_get_default_adapter` patch, `_boto3_client`
  patch).
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT commit any real `AWS_*` or `OPENAI_API_KEY`.

## NEXT TASK

Start SESSION_060 with the read-first list above. Ship
`request_photo_upload` + `attach_photo` + `delete_photo` in
`services/condition_report.py`, plus a local-mode upload
helper in `services/photo_storage.py` (or companion), plus
~35 focused tests. Do NOT ship the API, frontend, or image
processing.

Test baseline at SESSION_060 close: 1,940 → ~1,975.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4 SHIPPED; §7 M3.5 is the sub-scope this
   session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/research/RECON_MAPPING.md` §2.5 + §13.1
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs
   (`SESSION_059_m3_inc4_storage.md`,
   `SESSION_058_m3_inc3_read_model.md`,
   `SESSION_057_m3_inc2_service_layer.md`,
   `SESSION_056_m3_inc1_core_models.md`,
   `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_059 — M3.4 storage abstraction shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists.
  Test baseline: **1,940 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged this session.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.4.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR` **plus new (all optional)**:
  `AWS_STORAGE_BUCKET_NAME` (presence triggers S3 mode),
  `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`,
  `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or IAM
  role in prod), `AWS_S3_CUSTOM_DOMAIN` (CDN in front of
  the bucket).
- **New settings surface:** `settings.STORAGES["condition_photos"]`
  alias — env-driven S3 vs FileSystemStorage.
- **New runtime primitives:**
  `services/photo_storage.py::UploadTarget`,
  `build_canonical_key`, `generate_upload_target`,
  `object_exists`, `generate_read_url`,
  `LOCAL_UPLOAD_URL_MARKER`, `LOCAL_READ_URL_MARKER`, four
  domain errors.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning + M3.1 core models + M3.2 service layer +
  M3.3 Vehicle read-model + M3.4 storage abstraction
  (SESSION_059 — this session). M3.5–M3.8 queued for
  SESSION_060 – SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
