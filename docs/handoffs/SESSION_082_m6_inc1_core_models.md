---
title: "SESSION_082 handoff — Milestone 6 · Increment 1 (core photo + listing persistence)"
status: historical
type: handoff
date: 2026-08-01
session: 082
milestone: 6
milestone_status: in-progress
increment: 1
increment_status: shipped
commit: 659078f
---

# SESSION_082 — Milestone 6 · Increment 1 (M6.1 — core persistence)

## What shipped

The persistence layer for the vehicle-photo-gallery +
vehicle-listing domain. Two new models (`VehiclePhoto`,
`VehicleListing`), migration `0018` (pure additive
`CreateModel` — no data migration), two module-level
enum vocabularies (3 content-type values for
`VehiclePhoto` + 4 status values for `VehicleListing`),
cross-tenant `clean()` guards on both models, tenancy-
carrier registration extended from 17 → 19, two new
admin registrations (diagnostic-only, no
transition-authoring paths), and 39 focused tests
(target ~35). **No service module, no upload flow, no
state transitions, no rules, no endpoints, no
frontend, no AI role.**

Also: **three load-bearing decisions confirmed by the
user at session open** (per M6 §7 lesson 8) before any
code was written.

## Session preamble — the three §9 decisions

Per `MILESTONE_6_PLANNING.md` §9, three
`[NEEDS-DECISION-BEFORE-M6.1]` items required user
confirmation before implementation. The user
**confirmed all three recommended options** at session
open:

1. **§5.a — `VehicleListing` status vocabulary: Option A.**
   Four states — `draft` / `approved` / `published` /
   `unpublished`. Mirrors M4.5 vendor-comm shape;
   preserves the explicit approve gesture ("AI drafts,
   human approves, human publishes").

2. **§5.b — Listing-ready photo count threshold: Option C.**
   Fixed at 8 for v1; per-dealer configurability via
   `DealerOnboardingProfile.listing_ready_photo_count`
   deferred to a future increment. Threshold is not
   yet consumed by any M6.1 code — it becomes the
   M6.4 rule predicate. Ship a sensible default; add
   configurability when operator evidence surfaces
   need.

3. **§5.c — Photo storage layer reuse: Option A.**
   Extend M3.4's `services/photo_storage.py` with a
   new `store_vehicle_photo(...)` verb (deferred to
   M6.2 implementation). M6.1 persistence layer is
   storage-agnostic — the model owns `storage_key` as
   a CharField and does not know which backend
   populates it.

No planning amendments were required — the recommended
options were confirmed as-is. No `§0.a change-log`
entry needed.

## Final content-type + status vocabularies

Three canonical MIME values shipped in M6.1 (module-
level constants in `backend/dealer_ai/models.py`):

- `VEHICLE_PHOTO_CONTENT_TYPE_JPEG = "image/jpeg"`
- `VEHICLE_PHOTO_CONTENT_TYPE_PNG = "image/png"`
- `VEHICLE_PHOTO_CONTENT_TYPE_WEBP = "image/webp"`

Choices tuple: `VEHICLE_PHOTO_CONTENT_TYPE_CHOICES` (3
entries). **HEIC deliberately absent** — unlike M3.1
`CONDITION_PHOTO_CONTENT_TYPE_CHOICES` (which includes
HEIC), vehicle photos are customer-facing marketing
content served via the M6.5 showroom endpoint, and
HEIC has poor cross-browser support.

Four canonical listing statuses per §5.a Option A:

- `VEHICLE_LISTING_STATUS_DRAFT = "draft"`
- `VEHICLE_LISTING_STATUS_APPROVED = "approved"`
- `VEHICLE_LISTING_STATUS_PUBLISHED = "published"`
- `VEHICLE_LISTING_STATUS_UNPUBLISHED = "unpublished"`

Choices tuple: `VEHICLE_LISTING_STATUS_CHOICES` (4
entries). **`archived` deliberately absent** — the
Option C 5-state vocabulary was rejected in favor of
the 4-state shape.

## Models shipped

`backend/dealer_ai/models.py` gains two models:

### `VehiclePhoto` (many-per-Vehicle)

Fields:
- `vehicle` — ForeignKey(Vehicle, CASCADE,
  related_name="photos").
- `dealership` — ForeignKey(Dealership, CASCADE, NOT
  NULL, related_name="vehicle_photos").
- `storage_key` — CharField(max_length=512, unique).
  The M6.2 photo storage extension produces this key;
  every row corresponds to a distinct stored object.
- `content_type` — CharField(max_length=32,
  choices=VEHICLE_PHOTO_CONTENT_TYPE_CHOICES).
- `width_px` — PositiveIntegerField (captured at
  upload time).
- `height_px` — PositiveIntegerField.
- `sort_order` — IntegerField(default=0). Operator-
  controlled gallery ordering. Integer (not positive)
  so a "push to top" gesture can use negative values
  without renumbering the whole gallery.
- `is_primary` — BooleanField(default=False). "One
  primary per vehicle" is a M6.2 service-layer
  invariant, NOT a DB uniqueness constraint (per
  §1.1 — DB uniqueness would force operator's "swap
  primary" gesture into a two-step delete-then-
  insert dance).
- `caption` — CharField(max_length=255, blank).
- `uploaded_by` — ForeignKey(AUTH_USER_MODEL,
  SET_NULL, nullable). Historical rows survive user
  deletion.
- `uploaded_at` — DateTimeField(auto_now_add).
- `marked_deleted_at` — DateTimeField(null, blank).
  **Safer-direction deletion** per M6 §7 lesson 7 —
  the M6.2 delete gesture stamps this rather than
  removing the row.
- `deleted_by` — ForeignKey(AUTH_USER_MODEL,
  SET_NULL, nullable). Records the operator who
  initiated the safer-direction delete.
- `updated_at` — DateTimeField(auto_now).

`Meta.ordering = ("sort_order", "uploaded_at")` — sort
order first (operator-controlled), uploaded_at as
deterministic tiebreaker within a sort_order band.

`clean()` — cross-tenant guard: `dealership` matches
`vehicle.dealership`. Mirrors `VehicleStage.clean` and
`ConditionFindingPhoto.clean`.

**No `is_listing_ready` field.** The M6.4 rule
`_rule_photography_to_listing` computes readiness from
`width_px` + `height_px` at query time — a stored
boolean would risk drift from actual dimensions.
Predicate lives in the M6.4 service, not the
persistence layer.

### `VehicleListing` (OneToOne with Vehicle)

Fields:
- `vehicle` — OneToOneField(Vehicle, CASCADE,
  related_name="listing").
- `dealership` — ForeignKey(Dealership, CASCADE, NOT
  NULL, related_name="vehicle_listings").
- `status` — CharField(max_length=16,
  choices=VEHICLE_LISTING_STATUS_CHOICES,
  default=VEHICLE_LISTING_STATUS_DRAFT).
- `title` — CharField(max_length=255, blank).
- `body` — TextField(blank). AI-drafted listing copy
  (scrubbed by the M6.3 safety stack before
  persistence).
- `source_provenance` — JSONField(default=dict, blank).
  Mirrors M4.5 `VendorCommunication.source_provenance`
  shape.
- `drafted_by` — ForeignKey(AUTH_USER_MODEL,
  SET_NULL, nullable).
- `drafted_at` — DateTimeField(null, blank).
- `approved_by` — ForeignKey(AUTH_USER_MODEL,
  SET_NULL, nullable).
- `approved_at` — DateTimeField(null, blank).
- `published_by` — ForeignKey(AUTH_USER_MODEL,
  SET_NULL, nullable).
- `published_at` — DateTimeField(null, blank). Drives
  the M6.4 `_rule_listing_to_frontline` predicate.
- `unpublished_by` — ForeignKey(AUTH_USER_MODEL,
  SET_NULL, nullable).
- `unpublished_at` — DateTimeField(null, blank).
- `unpublished_reason` — CharField(max_length=255,
  blank).
- `created_at`, `updated_at` — auto.

`Meta.ordering = ("-updated_at",)`.

`clean()` — cross-tenant guard mirroring
`VehicleStage.clean`.

**Persistence is neutral about state transitions.**
Unlike `VendorCommunication` (which enforces a
per-status invariant matrix in `clean()`), M6.1
enforces only cross-tenant guard + enum-membership.
The `draft → approved → published → unpublished`
state machine + required actor pairings live in the
M6.3 service. Rationale: the M6.3 service is the
single write path (per M6 §0 lesson 4 — service
ownership), and duplicating invariants at persistence
would fork the enforcement.

**`Vehicle.price` stays on Vehicle** (planning §1.2).
Listing body reflects the current price at draft
time; the price itself is the vehicle's identity.

## Verified tenancy-carrier count

Pre-M6.1 count read from source
(`backend/dealer_ai/services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`):
**17** entries (M1 six + M3 three + M4 six + M5 two).

Post-M6.1 count: **19** entries (added `VehiclePhoto`,
`VehicleListing`). Test coverage:

- `test_m6_tenancy_carriers.TenancyCarriersExtended.test_carrier_count_is_nineteen`
  asserts the current count.
- `test_m6_tenancy_carriers.TenancyCarriersExtended.test_new_carriers_present`
  asserts VehiclePhoto + VehicleListing are members.
- `test_m6_tenancy_carriers.TenancyCarriersExtended.test_prior_carriers_preserved`
  asserts every M1–M5 carrier still present
  (additive-only invariant).
- `test_m6_tenancy_carriers.TenancyAutofillWiredForVehiclePhoto`
  smoke-tests pre_save autofill on VehiclePhoto.
- `test_m6_tenancy_carriers.TenancyAutofillWiredForVehicleListing`
  smoke-tests pre_save autofill on VehicleListing.

**M5.1 test refactor.** The
`test_vehicle_lifecycle_bootstrap.TenancyCarriersExtended.test_carrier_count_is_seventeen`
test naturally stales as the tuple grows. Removed the
absolute count check (covered by M6.1's
`test_carrier_count_is_nineteen`) and kept the M5.1
delta check (`test_new_carriers_include_stage_and_event`).
Net effect: -1 stale absolute-count test, +5 M6.1
tenancy tests.

## Migration 0018

`backend/dealer_ai/migrations/0018_vehicle_photo_and_listing.py`:

- Creates both tables (`VehicleListing`,
  `VehiclePhoto`).
- **Pure additive CreateModel operations.** No data
  migration — unlike M5.1's `0017` which bootstrapped
  a stage row for every existing Vehicle, M6.1 has no
  existing rows to seed. Photos and listings don't
  exist until the M6.2 / M6.3 services author them.
  The M6.4 rules correctly return "no photos yet" /
  "no listing yet" for missing rows.
- **Empty-database safe** — no data to touch.
- **Reversible** — schema drop reverses cleanly. No
  RunPython inverse required.
- **No M1–M5 substrate touched** — every prior model,
  index, constraint, service, permission, safety-
  stack scrub, endpoint, and frontend behavior
  unchanged.

`sqlmigrate 0018` produces expected DDL (two tables +
nine indexes on FK columns).

## Admin behavior

`backend/dealer_ai/admin.py` gains two registrations:

- `VehiclePhotoAdmin` — diagnostic list/search on
  vehicle stock, sort order, primary flag, content
  type, dimensions, marked-deleted timestamp,
  dealership. Autocomplete on `vehicle` /
  `dealership` / `uploaded_by` / `deleted_by`.
  `uploaded_at` / `updated_at` read-only. Standard
  delete permission (M6.2 service is the primary
  write path; admin is for emergency corrections).
- `VehicleListingAdmin` — diagnostic list/search on
  vehicle stock, status, title, all four transition
  timestamps, dealership. Autocomplete on all six
  FKs. `created_at` / `updated_at` read-only.
  Standard delete permission.

Neither admin surface exposes an upload/reorder/
delete/draft/publish authoring path. Those belong to
M6.2 (photo gallery service) + M6.3 (listing service)
+ M6.5 (admin endpoints).

## Tests added

Three new files, 39 focused tests total (target ~35):

- **`test_vehicle_photo.py`** (18 tests):
  - `VehiclePhotoContentTypeVocabulary` (2) — 3
    canonical MIME values, HEIC deliberately absent.
  - `VehiclePhotoCreate` (4) — round-trip all fields,
    defaults, invalid content_type rejected,
    uploaded_by nullable + SET_NULL on user delete.
  - `VehiclePhotoManyPerVehicle` (2) — multiple
    photos per vehicle allowed, cascade on vehicle
    delete.
  - `VehiclePhotoDealershipRequired` (1) — NOT NULL
    at schema level.
  - `VehiclePhotoCrossTenantClean` (2) — matching
    passes, mismatched raises.
  - `VehiclePhotoStorageKeyUnique` (1) — duplicate
    key raises IntegrityError.
  - `VehiclePhotoSaferDirectionDeletion` (2) —
    marking deleted preserves row; deleted_by
    SET_NULL on user delete.
  - `VehiclePhotoIsPrimaryDefault` (1) — defaults
    False.
  - `VehiclePhotoOrderingAndStr` (3) — ordering
    tuple, str shape with primary + deleted markers.

- **`test_vehicle_listing.py`** (14 tests):
  - `VehicleListingStatusVocabulary` (2) — 4
    canonical statuses, `archived` deliberately
    absent.
  - `VehicleListingCreate` (4) — round-trip all
    fields, defaults, status defaults to draft,
    invalid status rejected, actor FKs nullable +
    SET_NULL.
  - `VehicleListingOneToOneEnforcement` (2) — second
    listing raises IntegrityError, reverse accessor
    works.
  - `VehicleListingDealershipRequired` (1) — NOT
    NULL at schema level.
  - `VehicleListingCrossTenantClean` (2) — matching
    passes, mismatched raises.
  - `VehicleListingCascadeOnVehicleDelete` (1) —
    listing removed on vehicle delete.
  - `VehicleListingUnpublishedReasonOptional` (1) —
    reason field captured when provided.
  - `VehicleListingOrderingAndStr` (2) — ordering
    tuple, str shape.

- **`test_m6_tenancy_carriers.py`** (5 tests) —
  three-part carrier extension check + two autofill
  smoke tests (per shape above).

## Backend baseline

- **Pre-session:** 2,754 pass, 1 skipped, 0 fail.
- **Post-session:** 2,792 pass, 1 skipped, 0 fail.
- Delta: **+38** (39 new M6.1 tests, −1 stale M5.1
  absolute-count assertion), zero regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `python3 manage.py sqlmigrate dealer_ai 0018`
  produces expected DDL (two `CREATE TABLE` + nine
  index `CREATE`s).

## Frontend baseline

- `npx tsc --noEmit` clean (unchanged — no frontend
  files touched).
- `npx vite build` clean (unchanged — 605.90 kB bundle).

## Compatibility result

- **Frontend:** untouched. Zero frontend files changed.
- **M1–M5 substrate:** every existing model, service,
  permission class, safety-stack scrub, API, and
  frontend behavior unchanged. The 2,754 → 2,792 test
  delta is +39 M6.1 tests minus 1 stale absolute-count
  assertion.
- **Migration graph:** `0017 → 0018` linear, no
  branches, no merged migrations.
- **Tenancy carriers:** 17 → 19 (additive; every
  prior carrier preserved).

## Commit hashes

- Session commit: **659078f** (M6 ship commit; populate before
  overwriting `00-START-NEXT-SESSION.md`).

## Exact recommended scope for M6.2

**M6.2 — Photo storage integration.** Extend
`services/photo_storage.py` with a new
`store_vehicle_photo(...)` verb (per §5.c Option A —
user-confirmed). Create
`services/photo_gallery.py` with the ~6 public verbs
listed in §1.4:

- `upload_photo(vehicle, *, dealership, bytes,
  content_type, actor, sort_order=0, caption="")` →
  `VehiclePhoto`. Delegates to
  `photo_storage.store_vehicle_photo` for the object
  write, then persists the `VehiclePhoto` metadata
  row atomically.
- `set_primary(photo, *, dealership, actor)` — flips
  the previous primary to False and the new primary
  to True inside a single transaction. Enforces "at
  most one primary per vehicle" per §1.1.
- `reorder(vehicle, *, dealership, ordered_photo_pks,
  actor)` — bulk-updates `sort_order` per the
  supplied list.
- `mark_deleted(photo, *, dealership, actor)` —
  stamps `marked_deleted_at` + `deleted_by`.
  Safer-direction deletion per M6 §7 lesson 7.
- `restore_deleted(photo, *, dealership, actor)` —
  clears `marked_deleted_at` + `deleted_by`.
- `listing_ready_count(vehicle, *, dealership)` →
  int. Filters `marked_deleted_at=None` and applies
  the readiness predicate (dimensions ≥ threshold —
  exact predicate is a M6.2 load-bearing decision).

Domain errors (distinct classes per M6 §6 lesson 9):

- `PhotoStorageError` — the M3.4
  `ObjectStorageError` propagates up.
- `PhotoValidationError` — content-type / dimensions
  / size validation refusal.
- `PrimaryPhotoConflictError` (optional — if
  transaction-scoped enforcement is preferred over
  atomic swap) — for cross-service diagnostic
  clarity.

Concurrency posture: `transaction.atomic()` +
`select_for_update()` for the `set_primary` swap
(mirrors M4.2 WorkOrder precedent).

Test target: ~30 focused storage + gallery-service
tests. Baseline 2,792 → ~2,822. Zero regressions.
Zero migrations.

**Out of M6.2:**

- No LLM integration — M6.3.
- No deterministic rule integration — M6.4.
- No admin endpoints — M6.5.
- No frontend — M6.5.
- No AI safety-stack scrub extensions — M6.3.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md` — as
   confirmed at SESSION_082 (§9 items 1–3 confirmed
   as recommended)
6. `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
   (this doc)
7. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6
   lessons
8. `docs/handoffs/SESSION_081_m5_closeout.md`
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
10. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    pain #8 + #9
11. `docs/CAPABILITY_MATRIX.md` §7d M3 photo storage +
    §7e M4 vendor-comm drafting

Narrative docs are claims. Rules + research + code are
facts.
