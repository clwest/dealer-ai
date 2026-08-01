---
state: active
date: 2026-07-31
last_session_shipped: SESSION_060
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: in-progress
next_session: SESSION_061
next_milestone: 3
next_milestone_name: "Structured condition report"
next_increment: 6
next_increment_name: "M3.6 — Condition-report admin API + permission matrix"
---

# Next session — SESSION_061 · Milestone 3 · Increment 6 (M3.6 — admin API + permission matrix)

> **Milestone 3 · Increment 5 (M3.5) shipped at SESSION_060.**
> The photo attachment workflow (`request_photo_upload`,
> `attach_photo` with five-verification path, `delete_photo`
> with storage-first strategy) is live. Storage service extended
> with `ObjectMetadata` / `get_object_metadata` /
> `parse_canonical_key` / `delete_object` / `store_local_upload`.
> 58 focused tests. See
> `docs/handoffs/SESSION_060_m3_inc5_upload_flow.md`.
>
> **SESSION_061 opens M3.6 = the HTTP transport layer that binds
> M3.1–M3.5 to authenticated admin endpoints.** Nine endpoints
> under `/api/dealer-ai/admin/vehicles/<stock_number>/…`, plus
> a local-mode upload receiver. Every endpoint composes
> `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
> Domain errors from M3.2 / M3.4 / M3.5 map to specific HTTP
> statuses. **No frontend — that's M3.7.**

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every endpoint
   inherits the four-layer separation. M3.6 is the layer-1
   (identity) + layer-2 (authorization) wiring for the
   M3.1–M3.5 stack.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4, M3.5 now annotated SHIPPED. §7 M3.6 is the
   sub-scope for this session.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons —
   lesson 3 (one authoritative write path per operation)
   applies to endpoint construction.
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.6 (admin
   ledger endpoints) — the shape M3.6 mirrors.

## What M3.6 delivers (per `MILESTONE_3_PLANNING.md` §7 M3.6)

Nine HTTP endpoints + one local-mode upload receiver + a
full permission matrix locked by tests.

**In scope — endpoints (all under
`/api/dealer-ai/admin/vehicles/<stock_number>/…`):**

- `GET .../condition-report/latest/` — return latest report
  (any status) + all findings + all photos with signed read
  URLs; 404 if none.
- `POST .../condition-reports/` — create a draft report.
- `POST .../condition-reports/<report_id>/complete/` —
  draft → complete transition.
- `POST .../condition-reports/<report_id>/findings/` — add
  finding to draft.
- `PATCH .../findings/<finding_id>/` — update finding on
  draft.
- `DELETE .../findings/<finding_id>/` — delete finding from
  draft.
- `POST .../findings/<finding_id>/photos/request-upload/` —
  issue a presigned upload target.
- `POST .../findings/<finding_id>/photos/` — attach a photo
  after upload completes.
- `DELETE .../photos/<public_id>/` — delete a photo. Path
  uses `public_id`, NOT `storage_key` (per M3.1 refinement:
  `public_id` is durable external identity).

**Plus:** a local-mode upload receiver
`POST .../findings/<finding_id>/photos/local-upload/` that
accepts multipart body + calls
`photo_storage.store_local_upload`. Available only when the
`condition_photos` adapter is `_LocalAdapter`; returns 404 or
501 in S3 mode.

**Authorization contract per endpoint.** Every endpoint
composes `[IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership]` (M1 · 4D pattern,
reused verbatim). Every view calls `dealership =
get_current_dealership(request)` once at the top and threads
`dealership=dealership` into every service call. Cross-tenant
`stock_number` / `report_id` / `finding_id` / `public_id`
lookups fail closed with 404.

**Domain-error → HTTP-status mapping (must be locked by
tests):**

- `CrossTenantConditionReportError` → 404 (never leak
  whether the resource exists in another tenant).
- `ConditionReportImmutableError` → 409 Conflict.
- `PhotoNotYetUploadedError` → 409.
- `PhotoMetadataMismatchError` → 409.
- `PhotoAlreadyAttachedError` → 409.
- `InvalidStorageKeyError` → 400.
- `InvalidContentTypeError` → 400.
- `InvalidTTLError` → 400.
- `ObjectStorageError` → 502 Bad Gateway (upstream backend
  fault).
- `django.core.exceptions.ValidationError` → 400 with
  `message_dict` serialized to JSON.

**Explicitly out of scope (deferred to later increments):**

- ❌ Frontend — M3.7.
- ❌ AI role.
- ❌ Any modification to M3.1 models, migrations, admin.
- ❌ Any modification to M3.2–M3.5 service signatures.
- ❌ Modifications to `services/tenancy.py`,
  `services/llm_safety.py`, `services/vehicle_ledger.py`.
- ❌ New non-condition-report endpoints or middleware.
- ❌ Repairing the three deferred M3.4-era 400-expected
  tests in `test_salesperson_and_assignment.py` (unless
  they block M3.6).

## What SESSION_061 should do

### Recommended step sequence

1. **Read first (in this order — one pass, do not skim):**
   - `docs/roadmap/MILESTONE_3_PLANNING.md` §7 M3.6 detail +
     §1.6 (operator UI surface — even though UI is M3.7, the
     API shape M3.6 ships supports what M3.7 will consume) +
     §3 endpoint-layer invariants.
   - `docs/handoffs/SESSION_060_m3_inc5_upload_flow.md` —
     M3.5 shipped-surface manifest + domain errors.
   - `backend/dealer_ai/services/condition_report.py` — every
     public function signature (10 total: 7 M3.2 + 3 M3.5).
   - `backend/dealer_ai/services/photo_storage.py` —
     `generate_read_url` (for signed read URLs in the
     `GET latest/` response) + `store_local_upload` (for
     the local-mode receiver).
   - `backend/dealer_ai/permissions.py` — the
     `IsSalesManagerOrOwnerAtActiveDealership` class M3.6
     composes.
   - `backend/dealer_ai/views.py::admin_vehicle_ledger` and
     surrounding M2.6 endpoint examples — the shape M3.6
     mirrors.
   - `backend/dealer_ai/tests/test_admin_vehicle_ledger.py`
     — the test-file shape M3.6 mirrors (permission matrix
     across 5 role/tenant combinations).

2. **Verify starting state.**
   - `git status` — clean (or pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **1,998 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py showmigrations dealer_ai` →
     migrations current through `0015_condition_report`.

3. **Wire endpoints in `views.py`.** Add 10 view functions
   (9 endpoints + local-mode receiver) at the end of the
   file. Each is a `@api_view + @permission_classes` +
   thin body that resolves `dealership` and calls the M3.5
   service, catching domain errors + mapping to HTTP status.

4. **Wire URLs in `urls.py`.** Add 10 URL patterns under the
   existing admin URL prefix.

5. **No migration.** M3.6 is pure Python.

6. **Write focused endpoint tests.** New file
   `backend/dealer_ai/tests/test_admin_condition_report.py`.
   Target ~80 tests: full permission matrix per endpoint (5
   role/tenant cases minimum), happy-path business flows,
   domain-error → HTTP-status mapping, cross-tenant
   404-closed, signed-URL generation for reads.

7. **Full suite + baseline.** ~2,080 pass (1,998 + ~80),
   1 skipped, 0 fail.

8. **Close SESSION_061 with:**
   - Views + URLs + focused tests committed.
   - Handoff at
     `docs/handoffs/SESSION_061_m3_inc6_admin_api.md`.
   - Overwrite this file with SESSION_062 = M3.7 (operator
     UI) priority.
   - Planning §7 M3.6 annotated `SHIPPED at SESSION_061`.

## Explicit non-goals for SESSION_061

- ❌ Do NOT add any frontend file.
- ❌ Do NOT modify any M3.1 model, migration, or admin
  registration.
- ❌ Do NOT modify M3.2–M3.5 service signatures.
- ❌ Do NOT touch `services/vehicle_ledger.py`,
  `services/tenancy.py`, `services/llm_safety.py`, or any
  pre / post-LLM guard.
- ❌ Do NOT reopen M2 semantic contracts.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT let tests hit real S3 — reuse M3.4 / M3.5 mock
  patterns.
- ❌ Do NOT commit any real `AWS_*` or `OPENAI_API_KEY`.

## NEXT TASK

Start SESSION_061 with the read-first list above. Ship the
9 admin endpoints + local-mode upload receiver + full
permission matrix + domain-error → HTTP mapping + ~80
focused endpoint tests. Do NOT ship the frontend.

Test baseline at SESSION_061 close: 1,998 → ~2,080.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1–M3.5
   SHIPPED; §7 M3.6 is the sub-scope this session ships.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 (lessons)
7. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b M2.6 (admin
   endpoint shape template)
8. `docs/research/RECON_MAPPING.md` §2.5 + §12
9. `docs/CAPABILITY_MATRIX.md`
10. Most recent handoffs
    (`SESSION_060_m3_inc5_upload_flow.md`,
    `SESSION_059_m3_inc4_storage.md`,
    `SESSION_058_m3_inc3_read_model.md`,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_060 — M3.5 photo workflow shipped)

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
- **Env-override surface:** dealer identity vars +
  `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`,
  `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN`.
  Unchanged this session.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (in-progress):** M3.0
  planning + M3.1 core models + M3.2 service layer + M3.3
  Vehicle read-model + M3.4 storage abstraction + M3.5
  photo workflow (SESSION_060 — this session). Remaining
  M3.6–M3.8 queued for SESSION_061 – SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
