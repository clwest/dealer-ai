---
title: "SESSION_083 handoff — Milestone 6 · Increment 2 (photo storage extension + gallery service)"
status: historical
type: handoff
date: 2026-08-01
session: 083
milestone: 6
milestone_status: in-progress
increment: 2
increment_status: shipped
commit: 659078f
---

# SESSION_083 — Milestone 6 · Increment 2 (M6.2 — photo storage + gallery service)

## What shipped

The photo storage extension + gallery service layer for the M6
photo-gallery domain. Extended `services/photo_storage.py` with a
vehicle-photo canonical-key vocabulary + a server-side
`store_vehicle_photo` verb + a `put_bytes` method on both adapters.
Created `services/photo_gallery.py` with six public verbs
(`upload_photo`, `set_primary`, `reorder`, `mark_deleted`,
`restore_deleted`, `listing_ready_count`) + four distinct domain
errors. Added `VehiclePhoto.public_id` UUIDField + migration `0019`
(three-step: nullable AddField → RunPython backfill → NOT NULL +
unique AlterField). 39 focused tests (target ~30). **No LLM, no
deterministic rules, no admin endpoints, no frontend, no AI safety-
stack scrub — all deferred to M6.3+.**

Also: **three load-bearing decisions confirmed by the user at
session open** (per M6 §7 lesson 8) before any code was written.

## Session preamble — the three §M6.2 decisions

The M6.2 planning shape referenced three follow-on decisions from
the M6.1 planning doc. All three were presented at session open;
**the user confirmed all three recommended options**:

1. **§1 — Vehicle-photo canonical key shape: Option A.**
   `dealerships/<slug>/vehicles/<stock_number>/photos/<uuid>/original`.
   Mirrors the M3.4 condition-report shape; groups a vehicle's
   entire gallery under one S3 prefix for operator-side inspection;
   `stock_number` as the vehicle segment matches the operator's
   mental model. Rejected Option B (flatter — no vehicle segment,
   harder to inspect) and Option C (integer PK — less human-
   readable).

2. **§2 — `VehiclePhoto.public_id` UUID field: Option A.**
   Added `public_id = UUIDField(default=uuid.uuid4, unique,
   editable=False)` via additive migration `0019`. Mirrors the M3.1
   `ConditionFindingPhoto.public_id` pattern so the M6.5 admin
   endpoints have a tenant-safe external identifier that isn't an
   enumerable integer PK. Deferred from M6.1 per strict planning-
   shape discipline; added at M6.2 as the correct home.

3. **§3 — Listing-ready dimension threshold: Option A.**
   `width_px >= 1024 AND height_px >= 768` (4:3 SD baseline).
   Sensible retail-listing minimum; rejects thumbnails / accidental
   low-res uploads without blocking legitimate landscape photos.
   Module constants exposed as `LISTING_READY_MIN_WIDTH_PX` +
   `LISTING_READY_MIN_HEIGHT_PX`. The `LISTING_READY_PHOTO_COUNT`
   constant (fixed at 8 per §5.b Option C from SESSION_082) sits
   alongside for M6.4 consumption.

No planning amendments were required — the recommended options were
confirmed as-is.

## Migration 0019

`backend/dealer_ai/migrations/0019_vehicle_photo_public_id.py`:

- **Three-step migration** for future-safety:
  1. `AddField` — nullable, non-unique. Existing rows (if any) get
     `public_id=NULL`.
  2. `RunPython` (`_backfill_public_ids`) — walks existing rows
     and assigns a fresh `uuid.uuid4` to each.
  3. `AlterField` — enforces `NOT NULL` + `unique=True`. New rows
     get their default from `uuid.uuid4` (called per-insert).
- **Empty-table path at SESSION_083 open:** step 2 is a no-op
  iterator (M6.1 shipped an empty `dealer_ai_vehiclephoto` table);
  steps 1 + 3 are the only ones that touch the schema.
- **Reversible:** `AlterField` reverse drops constraints; `AddField`
  reverse drops the column entirely. RunPython reverse is a no-op
  (leaving backfilled UUIDs in place is harmless).
- **No M1–M5 substrate touched.** Only `VehiclePhoto` gains one
  column.

## photo_storage.py extension

`backend/dealer_ai/services/photo_storage.py` gains:

- **Model imports** — `VEHICLE_PHOTO_CONTENT_TYPE_CHOICES`,
  `Vehicle`.

- **Constants:**
  - `_VALID_VEHICLE_PHOTO_CONTENT_TYPES` — frozenset of the M6.1
    3-value whitelist (JPEG / PNG / WebP).
  - `_STOCK_NUMBER_PATTERN` — regex `[-a-zA-Z0-9_]+` for the
    stock-number segment (defense-in-depth; `Vehicle.stock_number`
    is a CharField so has no schema-level shape constraint).
  - `_VEHICLE_PHOTO_KEY_PATTERN` — full canonical key regex.
  - `_VEHICLE_PHOTO_KEY_PATTERN_GROUPED` — same with named
    capture groups for `parse_canonical_vehicle_photo_key`.
  - `_VEHICLE_PHOTO_MAX_BYTES = 25 * 1024 * 1024` — soft size
    ceiling.

- **New public functions:**
  - `build_canonical_vehicle_photo_key(*, dealership, vehicle,
    photo_uuid)` — the only entry point that constructs a new
    vehicle-photo key. Validates slug + stock-number + UUID.
  - `parse_canonical_vehicle_photo_key(storage_key)` → `(slug,
    stock_number, uuid.UUID)`. Reverse extraction for the M6.5
    admin API's tenant-defense-in-depth.
  - `store_vehicle_photo(*, dealership, vehicle, photo_uuid, data,
    content_type)` → `(canonical_key, ObjectMetadata)`. Server-
    side bytes write via the adapter's `put_bytes`. Reuses the
    existing `storages["condition_photos"]` FileSystemStorage
    alias — no separate storage alias needed (contract is
    identical; the key alone determines what lives where).

- **New private helpers:**
  - `_validate_vehicle_photo_content_type(content_type)`.
  - `_validate_vehicle_photo_bytes(data)` — size + type check.

- **New adapter method: `put_bytes(*, storage_key, content_type,
  data)`** on both concrete adapters (not on the Protocol —
  structural duck typing at the call site keeps the M3.4 Protocol
  surface stable):
  - `_LocalAdapter.put_bytes` — delegates to the existing
    `store_local_upload` helper (unchanged; the same sidecar-file
    logic FileSystemStorage requires to round-trip content type).
  - `_S3Adapter.put_bytes` — uses boto3 `put_object` with
    `ContentType` bound. Distinct from `generate_upload_url`
    (which returns a presigned PUT URL for browser-direct upload).

`__all__` extended with `build_canonical_vehicle_photo_key`,
`parse_canonical_vehicle_photo_key`, `store_vehicle_photo`.

## photo_gallery.py (new service)

`backend/dealer_ai/services/photo_gallery.py` — six public verbs
per `MILESTONE_6_PLANNING.md` §1.4:

### `upload_photo(vehicle, *, dealership, data, content_type, width_px, height_px, actor=None, sort_order=0, caption="")`

Writes bytes via `photo_storage.store_vehicle_photo`, then persists
the `VehiclePhoto` metadata row. Same fresh `uuid.uuid4` value
seeds both the row's `public_id` and the embedded UUID in the
canonical storage key — the two remain bound even if the storage
layer is later rekeyed. `is_primary` is NOT set here; the operator
uses `set_primary` explicitly.

### `set_primary(photo, *, dealership, actor=None)`

Atomic swap inside `transaction.atomic()` +
`select_for_update()`:

1. Lock current-primary rows on the vehicle (excluding the target).
2. Clear `is_primary` on the locked rows.
3. Set `is_primary=True` on the target.

Enforces "at most one primary per vehicle" without a DB uniqueness
constraint (which would force operator's "swap primary" gesture
into a two-step delete-then-insert dance per M6.1 §1.1). Refuses
if the target photo is marked-deleted.

### `reorder(vehicle, *, dealership, ordered_photo_pks, actor=None)`

Bulk `sort_order` update wrapped in `transaction.atomic`. Rejects
duplicate PKs (silent last-write-wins bug) and any PK that doesn't
belong to the vehicle (cross-tenant defense-in-depth).

### `mark_deleted(photo, *, dealership, actor=None)`

Safer-direction delete: stamps `marked_deleted_at` +
`deleted_by`; also clears `is_primary` (a deleted photo cannot
remain the vehicle's hero). Storage bytes NOT physically removed —
a future reaper (M6.2+ or later) handles that on operator-controlled
cadence.

### `restore_deleted(photo, *, dealership, actor=None)`

Reverse of `mark_deleted`. Does NOT restore the `is_primary`
flag — operator must explicitly re-elect via `set_primary`.

### `listing_ready_count(vehicle, *, dealership)` → int

Counts non-deleted photos meeting the dimension threshold
(`width_px >= LISTING_READY_MIN_WIDTH_PX AND
height_px >= LISTING_READY_MIN_HEIGHT_PX`). Drives the M6.4
`_rule_photography_to_listing` predicate (rule fires when count ≥
`LISTING_READY_PHOTO_COUNT`).

### Module constants

- `LISTING_READY_MIN_WIDTH_PX = 1024`
- `LISTING_READY_MIN_HEIGHT_PX = 768`
- `LISTING_READY_PHOTO_COUNT = 8`

### Four distinct domain errors (per M6 §6 lesson 9)

- **`CrossTenantPhotoError`** — cross-tenant refusal at service
  entry. Maps to HTTP 404 at M6.5.
- **`PhotoValidationError`** — invalid input (non-positive
  dimensions, reorder PK not on vehicle, set-primary on deleted).
  Maps to HTTP 400.
- **`PhotoAlreadyDeletedError`** — mark-deleted refused because
  already marked. Maps to HTTP 409.
- **`PhotoNotDeletedError`** — restore refused because not marked.
  Maps to HTTP 409.

Storage-side errors (`ObjectStorageError`,
`InvalidContentTypeError`, `InvalidStorageKeyError`) propagate up
unchanged — the M6.5 endpoint translates them to HTTP.

## Admin update

`VehiclePhotoAdmin` extended:
- `list_display` prepends `public_id`.
- `search_fields` gains `public_id`.
- `readonly_fields` gains `public_id`.

No other admin changes.

## Tests added

Two new files, 39 focused tests total (target ~30):

- **`test_photo_storage_vehicle.py`** (14 tests):
  - `BuildCanonicalVehiclePhotoKey` (4) — key shape matches
    Option A, invalid slug / stock-number / UUID refused.
  - `ParseCanonicalVehiclePhotoKey` (4) — roundtrip, condition-
    report key shape refused, path-traversal refused, non-string
    input refused.
  - `StoreVehiclePhoto` (5) — returns key + metadata, HEAD-verify
    via adapter.get_object_metadata, invalid content-type
    refused, zero-byte refused, oversize refused.
  - `LocalAdapterPutBytes` (1) — `put_bytes` reuses
    `store_local_upload` sidecar logic and content type round-
    trips via `get_object_metadata`.

- **`test_photo_gallery.py`** (25 tests):
  - `ModuleConstants` (2) — dimension threshold, count threshold.
  - `UploadPhoto` (3) — creates row + persists bytes with
    storage_key matching Option A shape (including `public_id`
    embedded in `storage_key`), cross-tenant refused,
    non-positive dimensions refused.
  - `SetPrimary` (4) — first flip, atomic swap (at-most-one
    invariant), refuses on deleted, cross-tenant refused.
  - `Reorder` (4) — reorder updates sort_order, duplicate PKs
    refused, PK not on this vehicle refused, cross-tenant refused.
  - `MarkDeleted` (4) — stamps timestamp + actor, clears primary
    flag, second mark refused, cross-tenant refused.
  - `RestoreDeleted` (3) — clears fields, does NOT restore
    primary, non-deleted restore refused.
  - `ListingReadyCount` (5) — zero when no photos, counts at/
    above threshold, excludes below, excludes marked-deleted,
    cross-tenant refused.

## Backend baseline

- **Pre-session:** 2,792 pass, 1 skipped, 0 fail.
- **Post-session:** 2,831 pass, 1 skipped, 0 fail.
- Delta: **+39** (39 new M6.2 tests), zero regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `python3 manage.py sqlmigrate dealer_ai 0019` produces expected
  DDL (nullable ADD → RunPython → NOT NULL + UNIQUE alter).

## Frontend baseline

- `npx tsc --noEmit` clean (unchanged — no frontend files touched).
- `npx vite build` clean (unchanged — 605.90 kB bundle).

## Compatibility result

- **Frontend:** untouched. Zero frontend files changed.
- **M1–M5 substrate + M6.1:** every existing model, service,
  permission class, safety-stack scrub, API, and frontend behavior
  unchanged. The 2,792 → 2,831 test delta is +39 M6.2 tests, no
  regressions.
- **Migration graph:** `0018 → 0019` linear, no branches.
- **Tenancy carriers:** 19 (unchanged — M6.2 shipped no new
  models).
- **M3.4 `services/photo_storage.py` primitive:** extended
  additively; every existing M3.4 test (`test_photo_storage.py`
  56 tests) still passes unchanged. `_LocalAdapter.store_local_upload`
  unchanged; `_S3Adapter.put_bytes` is a new method; existing
  `generate_upload_url` / `object_exists` / `generate_read_url` /
  `get_object_metadata` / `delete_object` unchanged.
- **`_TENANT_CARRIER_MODEL_NAMES`:** unchanged at 19.

## Commit hashes

- Session commit: **659078f** (M6 ship commit; populate before overwriting
  `00-START-NEXT-SESSION.md`).

## Exact recommended scope for M6.3

**M6.3 — Listing draft + AI safety scrub.** Create
`services/vehicle_listing.py` with the ~5 public verbs per
`MILESTONE_6_PLANNING.md` §1.4:

- `draft_listing(vehicle, *, dealership, actor)` → `VehicleListing`.
  Invokes the LLM factory + safety stack. Mirrors the M4.5
  `vendor_comm.draft_comm` pattern. Assembles a source bundle
  (Vehicle facts + M2 acquisition/cost data + M3 condition report
  + M4 recon summary + M6.2 photo gallery references) and passes
  it to the LLM. Persists the drafted body + `source_provenance`
  map.
- `approve_listing(listing, *, dealership, actor)` — flips
  `draft → approved`. Persists actor + timestamp.
- `publish_listing(listing, *, dealership, actor)` — flips
  `approved → published`. Persists actor + timestamp. Drives the
  M6.4 `_rule_listing_to_frontline` predicate.
- `unpublish_listing(listing, *, dealership, actor, reason)` —
  flips `published → unpublished`. Persists actor + timestamp +
  reason.
- `regenerate_draft(listing, *, dealership, actor)` — replaces the
  current draft body via a fresh LLM invocation. Refused when
  `status != draft`.

Distinct domain errors:
- `ListingImmutableError` — mutation refused because listing is
  in a terminal state (analogous to M4.5 `VendorCommImmutableError`).
- `ListingScrubDroppedError` — LLM output was refused by the
  safety scrub (mirrors M4.5 `ReconFactScrubDroppedError`).
- `InvalidListingTransitionError` — attempted status transition
  is structurally illegal.
- `CrossTenantListingError` — cross-tenant refusal.

Safety scrub decision (per §5.d planning): reuse existing
M4.5 `_scrub_invented_recon_fact` OR add a new
`_scrub_invented_photo_claim` — decide at M6.3 open as a
load-bearing decision.

Test target: ~40 focused listing-service tests (including scrub-
refused paths). Baseline 2,831 → ~2,871. Zero regressions. Zero
migrations.

**Out of M6.3:**
- No deterministic rule integration — M6.4.
- No admin endpoints — M6.5.
- No frontend — M6.5.
- No customer-chat truthful-language refactor — M6.5.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md`
6. `docs/handoffs/SESSION_083_m6_inc2_photo_gallery.md` (this doc)
7. `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
8. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6 lessons
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
10. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` pain #8 + #9
11. `docs/CAPABILITY_MATRIX.md` §7d M3 photo storage + §7e M4
    vendor-comm drafting

Narrative docs are claims. Rules + research + code are facts.
