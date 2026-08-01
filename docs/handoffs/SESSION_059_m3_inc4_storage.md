---
title: "SESSION_059 handoff — Milestone 3 · Increment 4 (provider-neutral photo storage abstraction)"
status: historical
type: handoff
date: 2026-07-31
session: 059
milestone: 3
milestone_status: in-progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_059 — Milestone 3 · Increment 4 (M3.4 — provider-neutral photo storage)

## What shipped

`backend/dealer_ai/services/photo_storage.py` — one provider-
neutral service module (four public functions + one dataclass +
four domain errors), a dedicated `condition_photos` alias in
`STORAGES`, and `django-storages[s3]==1.14.6` in
`requirements.txt`. 46 focused tests exercise the local + S3
adapters with zero real network access.

Plus two minimal compat patches triggered by the M3.4 `pip
install`: a transitive `httpx<0.28` pin (to keep `openai==1.30.5`
working after the venv re-resolve), and a swap from
`content_type="application/json"` to `format="json"` in four M1/M2
test methods that had a latent DRF-serialization bug.

Full backend suite: **1,940 pass, 1 skipped, 0 fail** (baseline
1,894 → +46 new M3.4 tests; zero regressions).

Six factual refinements landed vs. the original scope text —
all reviewed at the top of SESSION_059 per the user's spec.
Preserved the original planning text and annotated the shipped
reality; see planning §7 M3.4 SHIPPED annotation and the six
numbered refinements below.

## The six reviewed refinements

1. **`STORAGES` dict replaces legacy `DEFAULT_FILE_STORAGE`.**
   Django 5.0.6 supports the modern `STORAGES` dict; that's
   what shipped.
2. **Dedicated `condition_photos` alias.** The `default` alias
   is unchanged so unrelated file fields (any future
   `FileField`) never inherit condition-report storage
   semantics silently. `DealerOnboardingProfile.logo` is a
   `CharField` URL — no `FileField` migration risk today, but
   the alias establishes the pattern.
3. **Caller does NOT supply `storage_key` on upload.** The
   service computes canonical keys from `dealership` +
   `photo_uuid` internally — closes the path-traversal seam.
   Key shape: `dealerships/<slug>/condition-findings/<uuid>/original`.
   Every segment regex-validated. `object_exists` and
   `generate_read_url` re-validate any caller-supplied
   `storage_key` before touching the backend.
4. **Presigned PUT with `Content-Type` binding. Size verification
   deferred to M3.5 HEAD.** Documented honestly in the module
   docstring: presigned PUT does NOT enforce upload size; a
   client can upload a 1 GB object under a 500-byte declared
   size. M3.5's `attach_photo` will HEAD-verify.
5. **Local dev URL contract is explicit non-production.** No
   pretending `MEDIA_URL` is signed. Local adapter returns URLs
   prefixed with `LOCAL_UPLOAD_URL_MARKER` /
   `LOCAL_READ_URL_MARKER` (non-URL schemes). M3.5's upload
   flow will detect the prefix and route to a Django-side
   helper; M3.5 or M3.7 will detect the read marker and
   generate its own authenticated route.
6. **No `moto` — dependency injection + `mock.patch` +
   `botocore` client stubs.** Adapter auto-selection tested
   via `override_settings`; adapter behavior tested via
   `mock.patch` of `_S3Adapter._boto3_client` and
   `_get_default_adapter`. Zero network calls in tests.

## Read-first pass performed

Per the start-here doc's recommended sequence, read in order:

1. `docs/roadmap/MILESTONE_3_PLANNING.md` §5.a (three-option
   analysis — Option A won) + §7 M3.4 (increment scope) + §1.4
   (storage-story design memo) + §1.5 (photo model design
   notes; specifically "content-type whitelist enforced at URL
   issuance" and "photo rows represent attached objects, never
   upload intentions" — the latter is the M3.4 → M3.5
   handshake contract).
2. `docs/handoffs/SESSION_058_m3_inc3_read_model.md` — what
   M3.3 shipped and where M3.4 sits in the sequence.
3. Environment probe:
   - `python3 -c "import django; print(django.get_version())"`
     → **5.0.6** → drives the `STORAGES`-vs-`DEFAULT_FILE_STORAGE`
     choice (STORAGES).
   - `python3 -c "import storages; print(storages.__version__)"`
     → 1.14.6 already installed locally (via shared venv);
     pinned in requirements at that version.
   - `python3 -c "import boto3"` → 1.37.19 installed (pulled
     transitively via `django-storages[s3]`).
4. `backend/dealer_kit/settings.py` — confirmed no
   `STORAGES` declaration yet + `MEDIA_URL` / `MEDIA_ROOT`
   already set.
5. `backend/dealer_kit/prod_settings.py` — confirmed
   `STORAGES` already declared with `default` +
   `staticfiles`; needs to preserve `condition_photos` from
   dev when overlaying.
6. `backend/dealer_ai/models.py::DealerOnboardingProfile.logo_url`
   — confirmed `CharField` (URL string), NOT `FileField` — no
   silent migration risk on the `default` alias.
7. `backend/dealer_ai/models.py::CONDITION_PHOTO_CONTENT_TYPE_CHOICES`
   — the four MIME values `photo_storage.py` enforces.
8. `backend/requirements.txt` — confirmed no existing
   `django-storages` or `httpx` pin.

## Testing strategy decision (no `moto`)

Per SESSION_059 spec, evaluated whether existing tools suffice
before adding a testing dependency. They do:

- **Adapter auto-selection** tested via `override_settings` on
  `STORAGES["condition_photos"]["BACKEND"]`.
- **`_S3Adapter` behavior** tested via `mock.patch` of the
  private `_boto3_client()` factory (returns a `MagicMock`
  boto3 client — `generate_presigned_url` is client-side and
  needs no network; `head_object` is patched per test with
  `side_effect` for the 404 / NoSuchKey / AccessDenied paths).
- **Public function delegation** tested via `mock.patch` on
  `_get_default_adapter()` — keeps the public API clean of
  test seams.
- **`_LocalAdapter`** tested against Django's
  `storages["condition_photos"]` alias which resolves to
  `FileSystemStorage` under `MEDIA_ROOT/condition-photos` in
  dev / test.

No `moto` dependency added. Zero real S3 network access in
tests.

## Concrete deliverables

### Service module (`backend/dealer_ai/services/photo_storage.py`)

~530 lines. Structure mirrors `services/vehicle_ledger.py` and
`services/condition_report.py`:

**Module-level constants:**

- `_MAX_TTL_SECONDS = 900` — 15-minute security ceiling.
- `_DEFAULT_TTL_SECONDS = 900` — safe path = default path.
- `_VALID_CONTENT_TYPES` — `frozenset` built from
  `CONDITION_PHOTO_CONTENT_TYPE_CHOICES` (zero-drift guard).
- `_SLUG_PATTERN` — `re.compile(r"^[-a-zA-Z0-9_]+$")`.
- `_KEY_PATTERN` — full canonical key regex, matches
  `dealerships/<slug>/condition-findings/<uuid>/original`.
- `LOCAL_UPLOAD_URL_MARKER` / `LOCAL_READ_URL_MARKER` —
  exported marker prefixes (non-URL schemes).

**Domain errors (four, all subclass `ValueError` /
`RuntimeError`):**

- `InvalidStorageKeyError(ValueError)` — malformed key or
  invalid inputs to `build_canonical_key`.
- `InvalidContentTypeError(ValueError)` — non-whitelisted MIME.
- `InvalidTTLError(ValueError)` — TTL ≤ 0 or > 900.
- `ObjectStorageError(RuntimeError)` — backend faults (network,
  credentials, permissions).

**`UploadTarget` dataclass (frozen):**

- `method` (str — `"PUT"` in v1).
- `upload_url` (str — real presigned URL in prod; local
  marker in dev).
- `storage_key` (str — the canonical key).
- `required_headers` (Mapping[str, str] — includes
  `Content-Type` bound to the value passed to
  `generate_upload_target`).
- `expires_at` (`datetime` — timezone-aware).

**Adapter protocol + implementations:**

- `_PhotoStorageAdapter` — `Protocol` with three methods.
- `_LocalAdapter` — dev / test; returns marker URLs;
  filesystem-backed `object_exists` via `storages["condition_photos"].exists()`.
- `_S3Adapter` — production; uses `boto3.client("s3")`
  directly. Reads bucket / region / endpoint from
  `settings.STORAGES["condition_photos"]["OPTIONS"]`.
  Credentials come from the standard AWS SDK credential chain
  — never touched directly by this module.

**Adapter factory:**

- `_get_default_adapter()` — reads
  `settings.STORAGES["condition_photos"]["BACKEND"]` and
  returns `_S3Adapter()` when the backend is
  `storages.backends.s3.S3Storage`, else `_LocalAdapter()`.

**Public API (four functions):**

- `build_canonical_key(*, dealership, photo_uuid) -> str` —
  single source of truth for the key shape.
- `generate_upload_target(*, dealership, photo_uuid,
  content_type, ttl_seconds=900) -> UploadTarget` — validates
  all inputs, computes the key, delegates to the adapter.
- `object_exists(storage_key: str) -> bool` — re-validates the
  key against `_KEY_PATTERN`; delegates to the adapter.
  Returns `False` for missing objects; raises
  `ObjectStorageError` for backend faults.
- `generate_read_url(*, storage_key, ttl_seconds=900) -> str`
  — same validation shape; short-lived signed read URL.

`__all__` re-exports the domain errors, dataclass, markers,
and functions.

### Settings additions

**`backend/dealer_kit/settings.py`** — appended a header
comment block naming every new `AWS_*` env var, then the
`STORAGES` dict with env-driven `condition_photos` alias:

- Env-driven switch: `AWS_STORAGE_BUCKET_NAME` present →
  `S3Storage` with `default_acl=None`, `querystring_auth=True`,
  `file_overwrite=False`. Unset → `FileSystemStorage` under
  `MEDIA_ROOT/condition-photos`.
- `default` alias unchanged (FileSystemStorage — protects any
  future non-condition-photo file field).
- `staticfiles` alias unchanged from Django default.

**`backend/dealer_kit/prod_settings.py`** — `from .settings
import ... STORAGES`; then spread-merges the base dict with a
WhiteNoise `staticfiles` override:

```python
STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

This preserves the `condition_photos` env-switch active in
prod (any operator setting `AWS_STORAGE_BUCKET_NAME` on Render
env → S3 mode; unset → still FileSystemStorage, which is
Render-appropriate for demo data).

### Requirements additions

**`backend/requirements.txt`** — two additions:

- `django-storages[s3]==1.14.6` — pinned to match the
  already-installed version; pulls `boto3` transitively.
- `httpx<0.28` — transitive-dep pin explained in the
  compatibility patches section below.

### Tests (`backend/dealer_ai/tests/test_photo_storage.py`)

~570 lines, **46 tests** across nine classes:

- `AdapterAutoSelection` (2) — local FS backend → `_LocalAdapter`;
  S3 backend via `override_settings` → `_S3Adapter`.
- `CanonicalKeyBuilder` (7) — shape, tenant namespacing, UUID
  string acceptance + canonical roundtrip, invalid UUID
  rejection, None rejection, `..`-path-traversal on slug
  rejected, forward-slash-in-slug rejected.
- `ContentTypeWhitelist` (5) — 4 canonical MIMEs accepted,
  zero-drift guard vs model constant, `application/octet-stream`
  rejected, `image/svg+xml` explicitly rejected (SVG can embed
  JavaScript), empty string rejected.
- `TTLValidation` (8) — default = 900, at-max accepted, over-max
  rejected, zero / negative rejected, float rejected, bool
  rejected (Python `True` is a subclass of `int` — explicit
  guard), `expires_at` timezone-aware, `generate_read_url` TTL
  over-max rejected.
- `StorageKeyValidationOnRead` (6) — `..`-traversal, arbitrary
  key, missing UUID segment, missing suffix, forged key
  rejected; adapter never touched on invalid input (mocked
  adapter's methods assert `not_called()`).
- `UploadTargetShape` (3) — all fields populated, frozen +
  immutable, no raw AWS credentials in response repr.
- `LocalAdapter` (3) — upload marker returned, read marker
  returned, `object_exists` returns `False` for missing file.
- `S3Adapter` (7) — PUT with bound Content-Type, GET signing,
  HEAD success / 404 / NoSuchKey / AccessDenied paths,
  presigned-URL `BotoCoreError` wrapped as
  `ObjectStorageError`.
- `PublicApiDelegation` (5) — `generate_upload_target`
  delegates with internally-built key, `object_exists`
  delegates, `generate_read_url` delegates, content-type
  validation short-circuits before adapter touch.

## Compatibility patches surfaced by the M3.4 pip install

The `pip install -r requirements.txt` (required to pick up
`django-storages[s3]`) also re-resolved several transitive
dependencies. Two of those re-resolves surfaced pre-existing
latent bugs — fixed as minimal-scope compat patches:

### Patch 1 — `httpx<0.28` pin

- **Symptom:** two admin-endpoint tests
  (`test_admin_endpoints_auth.AdminLeadHandoffAuth.test_dealer_owner_at_active_tenant_is_authorized`
  and `test_sales_manager_at_active_tenant_is_authorized`)
  errored with `TypeError: Client.__init__() got an unexpected
  keyword argument 'proxies'`.
- **Root cause:** `openai==1.30.5` (the currently-pinned
  OpenAI SDK) passes `proxies` to `httpx.Client.__init__`,
  which `httpx>=0.28` (released after openai 1.30.5) removed.
  openai's own constraint is `httpx<1,>=0.23.0`; pip's
  resolver picks the highest satisfying (0.28.x) if nothing
  else pins it.
- **Fix:** append `httpx<0.28` to `backend/requirements.txt`
  with a header comment naming the openai version, the missing
  kwarg, and the SESSION_059 context. No code change.

### Patch 2 — four M1/M2 test methods, `content_type="application/json"` → `format="json"`

- **Symptom:** four tests
  (`test_salesperson_and_assignment.AssignmentEndpointTests.test_assign_sets_assigned_to_and_assigned_at`,
  `test_unassign_with_null_clears_fields`,
  `test_reassign_overwrites_cleanly`,
  `test_handoff_and_reset.AdminLeadHandoffEndpointTests.test_mark_handed_off_flag_flips`)
  failed with `AssertionError: 400 != 200` and response
  content `{"detail":"JSON parse error - Expecting property
  name enclosed in double quotes: line 1 column 2 (char 1)"}`.
- **Root cause:** DRF's `APIRequestFactory._encode_data`
  treats an explicit `content_type` argument as "raw payload"
  — it calls `force_bytes(data)` on the dict, producing
  Python's dict-repr (single quotes) rather than JSON. This
  behavior is different from Django's own `RequestFactory`
  (which `json.dumps` a dict when `content_type ==
  "application/json"`), but DRF's override wins in
  `APIClient`'s MRO. The tests were sending Python-dict-repr
  bodies that the DRF view rejected at the parser.
- **Reproducibility:** verified the failures reproduce at
  the pristine M3.3-close commit (`a733253`) with M3.4 code
  fully stashed — proves the pip install exposed a pre-
  existing latent bug, not that M3.4 introduced anything.
- **Fix:** swap `content_type="application/json"` →
  `format="json"` in the four affected test methods. This
  invokes DRF's JSONRenderer, which properly serializes the
  dict body. **No production behavior change** — the wire
  contract now matches the tests' original intent (well-
  formed JSON).
- **Scope discipline:** the three companion tests in
  `test_salesperson_and_assignment.py` (400-expected paths:
  `test_assign_to_inactive_advisor_returns_400`,
  `test_assign_unknown_salesperson_returns_400`,
  `test_assign_unknown_lead_returns_404`) were left
  unchanged this session. Their assertions pass under both
  the buggy and correct body shapes (the endpoint returns
  400 for a JSON parse error and for a business-reason
  failure alike); fixing them properly is a separate scope
  decision.

## Verification evidence

- `python3 manage.py test dealer_ai` → **1,940 tests, 1
  skipped, 0 fail** (up from 1,894; +46 new M3.4 tests, 0
  regressions).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."
- Test file count zero-network-calls audit: every S3 call in
  `test_photo_storage.py` goes through a `MagicMock`
  `_boto3_client` — verified by inspection.

## Compatibility

Preserved unchanged (production code):

- All M1 tenancy substrate.
- All M1 identity + authentication.
- All M1 · 4D + M2.6 endpoint-level permissions.
- Safety stack.
- Customer-facing surfaces.
- M2 ledger substrate.
- M3.1 model surface + migration `0015` + admin.
- M3.2 service module (`services/condition_report.py`).
- M3.3 Vehicle `@property` accessors.
- Dealer identity resolution.
- Frontend — no changes.

Modified (this session):

- `settings.py` / `prod_settings.py` — added `condition_photos`
  alias to `STORAGES`; every other setting unchanged.
- `requirements.txt` — two additions (`django-storages[s3]`,
  `httpx<0.28`); no removals or upgrades.
- Two test files (M1/M2 test-code compat patches; no
  production behavior change).

## Explicitly out of scope for M3.4 (deferred, unchanged)

- ❌ `ConditionFindingPhoto` upload flow
  (`request_photo_upload`, `attach_photo`, `delete_photo`) —
  M3.5.
- ❌ Any model or migration change to
  `ConditionFindingPhoto` — M3.1 shipped that; M3.4 only
  ships the storage adapter.
- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ AI role — never in M3.
- ❌ Extending `services/condition_report.py` — M3.5.
- ❌ Onboarding logo migration to a `FileField` — M3
  planning §5.a explicitly deferred this.
- ❌ Fixing the three companion 400-expected tests in
  `test_salesperson_and_assignment.py` — separate scope
  decision.

## Files changed

- Modified: `backend/requirements.txt` —
  `django-storages[s3]==1.14.6` + `httpx<0.28`.
- Modified: `backend/dealer_kit/settings.py` — `STORAGES`
  dict with `condition_photos` alias.
- Modified: `backend/dealer_kit/prod_settings.py` —
  `STORAGES` spread-merge to preserve the alias.
- New: `backend/dealer_ai/services/photo_storage.py`
  (~530 lines).
- New: `backend/dealer_ai/tests/test_photo_storage.py`
  (~570 lines, 46 tests).
- Modified: `backend/dealer_ai/tests/test_salesperson_and_assignment.py`
  — 3 test methods compat patch.
- Modified: `backend/dealer_ai/tests/test_handoff_and_reset.py`
  — 1 test method compat patch.
- Modified: `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.4
  annotated SHIPPED with the full manifest + refinements +
  compat patches.
- New: `docs/handoffs/SESSION_059_m3_inc4_storage.md` — this
  handoff.
- Modified: `00-START-NEXT-SESSION.md` overwritten with
  SESSION_060 = M3.5 priority.

No modifications to any model, admin, migration, service (other
than the new `photo_storage.py` module), permissions,
`views.py`, or any frontend file.

## Recommended exact scope for SESSION_060 (M3.5 — photo attachment workflow)

Per `MILESTONE_3_PLANNING.md` §7 M3.5, adapted to the M3.4
shipped surface:

**Scope.**

- Extend `backend/dealer_ai/services/condition_report.py`
  with the photo-attachment functions the M3.4 storage
  module now supports:
  - `request_photo_upload(finding, *, dealership,
    content_type, uploaded_by=None) -> UploadTarget` —
    validates parent report is `draft` (via
    `_refresh_and_assert_draft`); validates content type;
    generates a fresh `photo_uuid`; calls
    `photo_storage.generate_upload_target(...)`; returns
    the `UploadTarget`. **Does NOT persist a
    `ConditionFindingPhoto` row** — the row is created only
    after HEAD verification (see planning §1.5 "photo rows
    represent attached objects, never upload intentions"
    design note).
  - `attach_photo(finding, *, dealership, storage_key,
    content_type, size_bytes, caption="", uploaded_by=None)
    -> ConditionFindingPhoto` — HEAD-verifies the object
    exists at `storage_key` via
    `photo_storage.object_exists(...)`; refuses on missing
    object (raises `ConditionReportImmutableError` or a new
    `PhotoNotYetUploadedError`); creates the row with the
    UUID that maps to the storage_key.
  - `delete_photo(photo, *, dealership) -> None` — refuses
    when parent report is complete; deletes the row (best-
    effort delete on the storage object; row is source of
    truth).
  - Two new domain errors as needed:
    `PhotoNotYetUploadedError`, `PhotoDeletionError`.
- Extend `_TENANT_CARRIER_MODEL_NAMES` — no, it already
  covers `ConditionFindingPhoto` (M3.1).
- Extend `dealer_ai/admin.py` — no; M3.1 already shipped the
  admin registration.
- Extend M3.4's `_LocalAdapter` with a Django-side upload
  helper that accepts direct bytes when the M3.5 upload
  workflow detects the `LOCAL_UPLOAD_URL_MARKER` prefix.
  This is the "local dev download route deferred to M3.5"
  option chosen at M3.4.

**Tests.** ~35 focused service tests: create-then-attach
flow, HEAD-verification refusal on missing object,
cross-tenant guards, finding-must-be-draft on all three
functions, `estimated_cost`-still-never-touches-VehicleCost
composite check with photos present, local-mode upload
helper produces a real `ConditionFindingPhoto` row.

**Boundary.** Test baseline: 1,940 → ~1,975. No new
migrations. No API. No frontend.

**Explicit non-goals for M3.5.**

- ❌ API endpoints — M3.6.
- ❌ Frontend — M3.7.
- ❌ Any modification to M3.1 model shape.
- ❌ Any modification to M3.4 storage module beyond adding
  the local-mode upload helper.
- ❌ Image processing / thumbnails / EXIF stripping.
- ❌ AI role.

## Anchors that win on conflict for SESSION_060

1. `docs/PROJECT_RULES.md`.
2. `docs/DOC_GOVERNANCE.md`.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 3.
4. `docs/roadmap/AUTHENTICATION_MODEL.md`.
5. `docs/roadmap/MILESTONE_3_PLANNING.md` — §7 M3.1, M3.2,
   M3.3, M3.4 now annotated SHIPPED. §7 M3.5 is the sub-scope
   for the next session. §1.5 photo model design notes
   (particularly "photo rows represent attached objects, never
   upload intentions") are the M3.4 → M3.5 handshake contract.
6. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
7. `docs/research/RECON_MAPPING.md` §2.5 + §13.1.
8. `docs/CAPABILITY_MATRIX.md`.
9. Most recent handoffs (this file,
   `SESSION_058_m3_inc3_read_model.md`,
   `SESSION_057_m3_inc2_service_layer.md`,
   `SESSION_056_m3_inc1_core_models.md`,
   `SESSION_055_milestone_3_planning.md`).

## Operational state (post-SESSION_059)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015` applied. Default `Dealership` row exists.
  Test baseline: **1,940 pass**, 1 skipped, 0 fail.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session.
- **Frontend (prod):** NONE.
- **Frontend build:** unchanged.
- **DRF defaults + CSRF + endpoint-level permissions:** all
  unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
  No new migration in M3.4.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR` (unchanged) + **new (all
  optional)**: `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`,
  `AWS_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_S3_CUSTOM_DOMAIN`.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
- **Milestone 3 shipped surface (so far):** M3.0 planning
  (SESSION_055) + M3.1 core models (SESSION_056) + M3.2
  service layer (SESSION_057) + M3.3 Vehicle read-model
  (SESSION_058) + M3.4 storage abstraction (SESSION_059 —
  this session). Remaining M3.5–M3.8 queued for
  SESSION_060 – SESSION_063.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred idea recorded in the respective
  planning + retrospective + handoff docs. No new deferrals
  surfaced this session that don't fit existing docs.
