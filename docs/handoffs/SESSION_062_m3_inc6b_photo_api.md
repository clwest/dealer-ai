---
title: "SESSION_062 handoff — Milestone 3 · Increment 6B (photo API + local-upload receiver)"
status: historical
type: handoff
date: 2026-07-31
session: 062
milestone: 3
milestone_status: in-progress
increment: 6B
increment_status: shipped
commit: TBD
---

# SESSION_062 — Milestone 3 · Increment 6B (M3.6B — photo API + local-upload receiver)

## What shipped

Four HTTP endpoints wiring M3.5 photo service to the admin API,
completing the M3.6 split that started at SESSION_061:

- `POST .../findings/<finding_id>/photos/request-upload/` —
  authorizes an upload (returns `UploadTarget`;
  `storage_key` is the narrow exception here).
- `POST .../findings/<finding_id>/photos/` — attaches after
  HEAD-verified metadata check; returns photo projection with
  `storage_key` ABSENT.
- `DELETE .../photos/<uuid:public_id>/` — path uses `public_id`
  (Django UUID converter); `storage_key` never touches URL
  routing; storage-first delete strategy preserved.
- `POST .../findings/<finding_id>/photos/local-upload/` —
  multipart receiver; returns 404 in S3 mode (does not
  advertise dev-only surface); does NOT create the row (attach
  still runs the five-verification path).

Full backend suite: **2,124 pass, 1 skipped, 0 fail**
(baseline 2,067 → +57 M3.6B tests; 0 regressions).

## Endpoints shipped (4)

All under `/api/dealer-ai/admin/vehicles/<stock_number>/…`,
composing `[IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership]` (same permission
class as M3.6A). Same dealership-resolution + explicit-
scoping + service-delegation pattern.

## Upload contract

`UploadTarget` projection (`_upload_target_response`):

```json
{
  "method": "PUT",
  "upload_url": str,            # local marker OR real presigned URL
  "storage_key": str,           # ONLY exposed here
  "required_headers": {"Content-Type": "image/..."},
  "expires_at": iso datetime
}
```

**`storage_key` invariant**: appears ONLY in this response.
Locked by 5 negative tests (`StorageKeyLeakageNegative`
class) covering attach response, latest-report response,
finding update response, delete response (204 empty body),
and the positive assertion that request-upload IS the only
place.

## Projection contract

Photo projection reuses M3.6A `_project_photo`:

```json
{
  "public_id": uuid str,
  "content_type": str,
  "size_bytes": int,
  "caption": str,
  "uploaded_by": username str | null,
  "created_at": iso datetime,
  "signed_read_url": str,       # short-TTL, adapter-generated
  "read_url_expires_at": iso datetime
}
```

**Never exposed:** `storage_key`, bucket name, adapter type,
provider identity, AWS credentials, canonical path detail,
filesystem paths.

## Permission behavior

Reused M3.6A `_AuthMatrixBase` mixin. Every photo endpoint
tested against 5 outcomes: anonymous, no-role, advisor-only,
porter-only, sales_manager + dealer_owner (both authorized).
Local-upload endpoint covered via business-flow class rather
than matrix subclass (multipart is awkward in the shared mixin).

Cross-tenant lookups fail closed with 404 across all four
endpoints:

- Attach: cross-tenant storage_key (valid canonical shape but
  wrong slug) → 404. Never leaks that the key belongs to a
  different tenant.
- Delete: cross-tenant `public_id` → 404. Never leaks
  existence in another tenant.
- Local upload: cross-tenant storage_key → 404.

## Local upload behavior

- **Local mode active**: accepts multipart with `file`,
  `storage_key`, `content_type` fields. Validates canonical
  key shape + dealership namespace. Calls
  `photo_storage.store_local_upload` which enforces MIME
  whitelist + 25 MB ceiling + non-empty. Returns 201 with
  `{stored_metadata: {content_type, size_bytes, exists}}`.
- **S3 mode active**: returns **404** (not 501). Do NOT
  advertise the dev-only surface in production.
  Implementation: `store_local_upload` raises
  `LocalUploadNotAvailableError`; view catches → 404.
- **Behaves exactly like S3 upload from the workflow's
  perspective**: request → upload → attach → verify → row.
  Local receiver does NOT create the
  `ConditionFindingPhoto` row.

## Error mapping (locked by tests)

| Exception | HTTP |
|---|---|
| `CrossTenantConditionReportError` | 404 |
| `ConditionReportImmutableError` | 409 |
| `PhotoNotYetUploadedError` | 409 |
| `PhotoMetadataMismatchError` | 409 |
| `PhotoAlreadyAttachedError` | 409 |
| `InvalidStorageKeyError` | 400 |
| `InvalidContentTypeError` | 400 |
| `InvalidTTLError` | 400 |
| `ObjectStorageError` | 502 (sanitized detail) |
| `LocalUploadNotAvailableError` | 404 (hides dev surface) |

**Provider exception text never leaks** — locked by
`test_provider_error_message_does_not_leak_details` which
asserts that a `ObjectStorageError` carrying "boto3
InternalServerError: bucket=super-secret-bucket" produces a
response with none of `bucket`, `super-secret-bucket`, or
`boto3` in the body.

## Query behavior

- `request-upload`: 3 queries (vehicle + finding + report
  refresh in `_refresh_and_assert_draft`). Zero DB / network
  for URL signing (`generate_presigned_url` is client-side).
- `attach`: 4 queries baseline (vehicle + finding + report
  refresh + duplicate-check `exists()`) + 1 HEAD via adapter
  (local: filesystem; S3: mocked in tests, real
  `head_object` in prod) + 1 save + 1 refetch with
  `select_related('uploaded_by')`.
- `delete`: 3 queries (vehicle + photo + report refresh) +
  1 storage-side `delete_object` (idempotent) + 1 row delete.
- `local-upload`: 3 queries (vehicle + finding + report
  refresh) + 1 filesystem write via storage backend.

No hidden managers. No cached signed URLs (`_project_photo`
generates fresh URL per response — TTL discipline).

## Tests added (57 across 6 classes)

- Permission matrix (18): `RequestUploadAuth` (6),
  `AttachAuth` (6), `DeleteAuth` (6). Reuses M3.6A
  `_AuthMatrixBase`.
- `RequestUploadFlow` (6): valid MIME, invalid MIME, missing
  content_type, no row created, TTL cap, completed report.
- `AttachFlow` (10): success + projection, storage_key
  absent, duplicate → 409, missing object → 409, size
  mismatch → 409, content_type mismatch → 409, malformed
  key → 400, cross-tenant key → 404, completed report → 409,
  no row on missing.
- `DeleteFlow` (7): 204 + row removed, completed → 409,
  cross-tenant → 404, unknown public_id → 404, provider
  failure → 502 + row retained, provider error sanitized,
  missing storage idempotent.
- `LocalUploadFlow` (11): local mode accepts, attach still
  required, S3 mode 404, missing file / storage_key /
  content_type → 400, arbitrary key → 400, cross-tenant key
  → 404, empty upload → 400, oversized → 400, invalid MIME
  → 400.
- `StorageKeyLeakageNegative` (5): attach / latest-report /
  finding update responses omit storage_key, delete
  response empty, request-upload IS the only place (positive
  completion of the invariant).

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,124 tests, 1
  skipped, 0 fail** (+57, 0 regressions).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `python3 manage.py check` → clean.
- **Zero frontend changes** — git status confirms.
- **Zero real network** — every S3 test uses mocked
  `_boto3_client`; local tests hit filesystem only.
- **Zero storage_key leakage** — 5 explicit negative tests +
  M3.6A's `NoStorageKeyLeakage` class still passes.

## Compatibility

All M1–M3.6A contracts preserved unchanged. Modified files
(this session, all additive):

- `dealer_ai/serializers.py` — 2 new request serializers.
- `dealer_ai/views.py` — 4 new view functions + 2 helpers.
- `dealer_ai/urls.py` — 4 new URL patterns.

No model / migration / admin / service / permissions /
requirements / frontend changes.

## Files changed

- Modified: `backend/dealer_ai/serializers.py`.
- Modified: `backend/dealer_ai/views.py`.
- Modified: `backend/dealer_ai/urls.py`.
- New: `backend/dealer_ai/tests/test_admin_condition_report_photos.py`.
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.6B
  annotated SHIPPED.
- New: `docs/handoffs/SESSION_062_m3_inc6b_photo_api.md` —
  this handoff.
- Modified: `00-START-NEXT-SESSION.md` — SESSION_063 = M3.7
  (frontend UI).

## Recommended exact scope for SESSION_063 (M3.7 — operator UI)

Per `MILESTONE_3_PLANNING.md` §7 M3.7 (locked at
SESSION_055; unchanged):

**Scope.**

- New React route `/dealer-ai-inventory/:stock/condition-report`
  registered inside `<RequireAuth>` in `frontend/src/main.tsx`.
- New typed API helpers in `frontend/src/lib/api.ts` for the
  ten M3.6 endpoints (all via `authFetch`).
- New page `frontend/src/pages/VehicleConditionReportPage.tsx`
  wiring:
  - Vehicle header (reuses M2.7 header component if
    extractable).
  - Report state (`draft` vs `complete` badge, inspector +
    date + mileage).
  - Findings list (grouped by severity ladder).
  - Draft-only edit affordances gated by
    `useAuth().hasRole('sales_manager') ||
    hasRole('dealer_owner')`.
  - Photo upload flow using presigned PUT for S3 mode or
    the local receiver in dev.
- New "Condition report" button on the operator inventory
  card (next to M2.7's "Ledger" button). NOT on public
  `/showroom`.

**Tests target.** Vitest / React Testing Library — component
render tests + role-gated affordance tests. Backend baseline
unchanged (2,124). Frontend test count depends on the
existing frontend test infrastructure.

**Explicit non-goals for M3.7.**

- ❌ No new backend endpoints — M3.6 is complete.
- ❌ No AI role.
- ❌ No image processing.
- ❌ No public / customer surfaces.

## Anchors that win on conflict for SESSION_063

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md`.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1–M3.6B
   now SHIPPED; §7 M3.7 is the sub-scope for the next
   session. §1.6 operator UI design memo.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `CLAUDE.md` frontend-stack notes (Tailwind v3, shadcn/ui
   bridge, brand.* tokens, no v4-only variants).
8. Most recent handoffs (this file, `SESSION_061`,
   `SESSION_060`, `SESSION_059`, `SESSION_058`,
   `SESSION_057`, `SESSION_056`, `SESSION_055`).

## Operational state (post-SESSION_062)

- **Backend (local):** Django on `:8001`. Migrations
  through `0015`. Test baseline: **2,124 pass**, 1 skipped,
  0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Env-override surface:** unchanged.
- **New runtime primitives (M3.6B):** 4 admin endpoints +
  2 request serializers + 1 lookup helper + 1 upload-target
  projection.
- **Milestone 3 shipped surface:** M3.0 planning + M3.1
  models + M3.2 service + M3.3 read-model + M3.4 storage +
  M3.5 photo workflow + M3.6A core admin API + M3.6B photo
  API (SESSION_062 — this session). Remaining: M3.7 (UI)
  + M3.8 (closeout) queued for SESSION_063 – SESSION_064.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
