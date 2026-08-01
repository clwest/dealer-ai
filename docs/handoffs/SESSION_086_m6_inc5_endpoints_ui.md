---
title: "SESSION_086 handoff — Milestone 6 · Increment 5 (admin API + operator UI + truthful customer language)"
status: historical
type: handoff
date: 2026-08-01
session: 086
milestone: 6
milestone_status: in-progress
increment: 5
increment_status: shipped
commit: 659078f
---

# SESSION_086 — Milestone 6 · Increment 5 (M6.5 — endpoints + UI + §5.i refactor)

## What shipped

The largest M6 increment — three coordinated workstreams:

- **Admin API (13 endpoints)** — photo (6) + listing (6) + public
  showroom (1). Two new view modules (`views_photos.py`,
  `views_listings.py`, `views_showroom.py`) + URL wiring.
- **Operator UI (2 pages)** — `/dealer-ai-inventory/:stock/photos`
  + `/dealer-ai-inventory/:stock/listing`. Follows M5.6
  `VehicleLifecyclePage` pattern; API helpers added to
  `lib/api.ts`.
- **Customer-chat truthful-language refactor (M5.5 §5.i deferral
  landed)** — extended `services/chat_engine.py` with
  `customer_lookup_visible_vehicle_by_id` +
  `customer_lookup_visible_vehicle_by_stock` helpers. Refactored
  `vehicle_detail` + `vehicle_ask` in `views.py`. Non-retail
  vehicles now return the truthful copy per §5.i.

**52 focused new tests** (23 photo endpoints + 22 listing endpoints
+ 7 showroom + truthful-language). Baseline 2,896 → 2,948. **6
existing tests updated in-place** to reflect the tightened
customer-visibility contract (fixtures now publish a listing for
customer-facing endpoint tests).

**Load-bearing decisions confirmed at session open (all A/A/A/A/A):**

1. §1 — nested URL shape `/api/dealer-ai/admin/vehicles/<stock>/photos/`
   + `/api/dealer-ai/admin/vehicle-photos/<uuid:public_id>/`. Uses
   `stock_number` (not integer PK) to match the M2/M3/M4/M5 admin
   surfaces.
2. §2 — public showroom URL segment `stock_number`
   (`/api/dealer-ai/showroom/vehicles/<stock_number>/`).
3. §3 — two operator UI routes (photos + listing).
4. §4 — customer-chat refactor landed inline (bounded scope: 3
   files touched — `services/chat_engine.py`, `views.py`, tests).
5. §5 — shipped as one increment; net M6.5 backend tests came in at
   52 (under the ~70 split threshold).

No planning amendments required — the recommendations were
confirmed as-is.

## Admin endpoints

### views_photos.py (new file, 6 endpoints)

Per SESSION_086 §1 Option A URL shape. Uses
`IsReconManagerSalesManagerOrOwnerAtActiveDealership` (M4.6). Per-
tenant isolation via `photo_gallery.CrossTenantPhotoError` → 404.
Multipart uploads use `@parser_classes([MultiPartParser, FormParser])`
per M3.5 precedent.

- `GET  /admin/vehicles/<stock>/photos/` — list (includes marked-
  deleted; UI splits active vs. deleted panels).
- `POST /admin/vehicles/<stock>/photos/upload/` — multipart form.
  Returns 201 + projected `VehiclePhoto` metadata.
- `POST /admin/vehicles/<stock>/photos/reorder/` — accepts ordered
  list of `public_id`s (endpoint resolves to pks internally).
- `POST /admin/vehicle-photos/<uuid:public_id>/set-primary/`.
- `DELETE /admin/vehicle-photos/<uuid:public_id>/` — safer-direction
  (stamps `marked_deleted_at` + `deleted_by`).
- `POST /admin/vehicle-photos/<uuid:public_id>/restore/`.

Domain-error mapping:

- `CrossTenantPhotoError` → 404 (fail-closed).
- `PhotoValidationError` / `InvalidStorageKeyError` → 400.
- `PhotoAlreadyDeletedError` / `PhotoNotDeletedError` → 409.
- `InvalidContentTypeError` → **415** (unsupported media type — the
  M6.1 3-value whitelist).
- `ObjectStorageError` → **502** (backend fault).
- Generic `ValueError` → 400.

Response projection includes a short-lived signed read URL (15
min via `photo_storage._get_default_adapter().generate_read_url`)
so the UI renders thumbnails without a second URL request. Local-
mode returns marker strings the UI detects via prefix.

### views_listings.py (new file, 6 endpoints)

Per SESSION_086 §1 URL shape. Same permission class as photos.
Listings are OneToOne with Vehicle so no per-listing external
identifier is needed at the URL layer.

- `GET  /admin/vehicles/<stock>/listing/` — read (returns
  `{"listing": null}` when none exists — UI renders the "Draft
  with AI" affordance).
- `POST /admin/vehicles/<stock>/listing/draft/` — invokes
  `services.vehicle_listing.draft_listing`. Returns 201.
- `POST /admin/vehicles/<stock>/listing/regenerate/`.
- `POST /admin/vehicles/<stock>/listing/approve/`.
- `POST /admin/vehicles/<stock>/listing/publish/`.
- `POST /admin/vehicles/<stock>/listing/unpublish/` — body:
  `{"reason": "..."}` (nonblank required per M6.3 service
  contract).

Domain-error mapping (per M6.3 SESSION_084 handoff):

- `CrossTenantListingError` → 404.
- `InvalidListingTransitionError` / `ListingImmutableError` → 409.
- `ListingScrubDroppedError` / `EmptyListingDraftError` → **422**
  (unprocessable entity — AI safety refused or LLM empty).
- `ValueError` → 400.

### views_showroom.py (new file, 1 endpoint)

Per SESSION_086 §2 Option A URL segment. Uses `AllowAny` — the
retail gate IS the authorization.

- `GET /showroom/vehicles/<stock_number>/` — public. Returns
  vehicle + published listing + primary photo URL + gallery (up
  to 20 non-deleted photos with signed read URLs).

Retail gate (per §5.i):
`customer_lookup_visible_vehicle_by_stock(stock_number)` requires
BOTH `stage=frontline` AND `VehicleListing.status='published'`.
Missing / non-visible vehicles surface as HTTP 404 with the
truthful `CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY` per §5.i.

Response deliberately excludes internal cost / margin fields —
locked by the `test_body_never_exposes_price_data` test.

## services/chat_engine.py extension

Two new module-level helpers + one canonical constant:

- **`CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY`** — the exact SESSION_075
  §5.i language: `"That vehicle is not currently available for
  retail."` Test-locked.
- **`customer_lookup_visible_vehicle_by_id(vehicle_id)`** — returns
  the Vehicle iff visible via `customer_visible_vehicles()` (M5.5
  frontline gate) AND has a published listing. Otherwise `None`.
- **`customer_lookup_visible_vehicle_by_stock(stock_number)`** — same
  gate, keyed by stock_number. Used by the M6.5 showroom endpoint.

Rationale for the stricter gate at per-vehicle lookup (vs.
`customer_visible_vehicles` which stays frontline-only): a vehicle
at frontline without a published listing is still-in-preparation.
Exposing it via a stock-specific direct-access URL would leak
operational readiness before the operator has signed off on
customer-facing copy. The chat matched-vehicles / search / lever-
flex surfaces continue to use `customer_visible_vehicles`
(frontline-only) because those are batch-query surfaces where the
listing check would over-filter.

## views.py refactor (§5.i landing)

Two customer-facing endpoints tightened:

- **`vehicle_detail(request, vehicle_id)`** — now uses
  `customer_lookup_visible_vehicle_by_id`. Returns HTTP 404 +
  `CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY` for non-retail vehicles.
- **`vehicle_ask(request, vehicle_id)`** — same refactor.

**Effective change:** customers with a stock-specific URL (from a
marketing link, stale search result, embed page) hitting a vehicle
that's in-recon / not-yet-listed / on-hold now see the truthful
"not currently available for retail" copy rather than payment
estimates + Q&A on an operationally-unready vehicle. No leakage of
stage / recon / ETA / vendor / expected-ready-date.

## URL wiring

`backend/dealer_ai/urls.py` gained 13 new URL patterns organized
under three comment banners (photo endpoints, listing endpoints,
public showroom).

## Frontend

### lib/api.ts extension

Added TypeScript types + fetch helpers for all 13 endpoints:

- **Photo types:** `VehiclePhotoContentType`, `VehiclePhotoActor`,
  `VehiclePhotoDTO`, `VehiclePhotoListResponse`,
  `VehiclePhotoUploadFields`.
- **Photo helpers:** `fetchVehiclePhotos`, `uploadVehiclePhoto`,
  `reorderVehiclePhotos`, `setPrimaryVehiclePhoto`,
  `markDeletedVehiclePhoto`, `restoreVehiclePhoto`.
- **Listing types:** `VehicleListingStatus`, `VehicleListingDTO`,
  `VehicleListingReadResponse`.
- **Listing helpers:** `fetchVehicleListing`, `draftVehicleListing`,
  `regenerateVehicleListing`, `approveVehicleListing`,
  `publishVehicleListing`, `unpublishVehicleListing`.

### Two new operator pages

- **`VehiclePhotoGalleryPage.tsx`** — three panels: active gallery
  (grid with set-primary + delete controls), upload form (with
  client-side image-dimension probe), recently-deleted panel (with
  restore). Role-gated to recon_manager / sales_manager /
  dealer_owner. Detailed 400/403/404/409/415/502 error UX.
- **`VehicleListingEditorPage.tsx`** — status badge + provenance
  timestamps + listing body view + action buttons per current
  status. Draft: regenerate + approve. Approved: publish.
  Published: unpublish (requires reason). Unpublished: terminal
  state with operator advisory.

### Route wiring

`frontend/src/main.tsx` gains two routes under the RequireAuth
gate:

- `/dealer-ai-inventory/:stock/photos` → `VehiclePhotoGalleryPage`.
- `/dealer-ai-inventory/:stock/listing` → `VehicleListingEditorPage`.

## Tests

Three new backend test files, 52 new tests:

### test_admin_photo_endpoints.py (23 tests)

- Permission matrix (3): unauth refused, advisor forbidden,
  sales_manager admitted.
- List endpoint (4): empty gallery, projected shape, includes
  marked-deleted, cross-tenant 404.
- Upload endpoint (4): creates photo, rejects missing dimensions,
  rejects unsupported content type (415), cross-tenant 404.
- Reorder endpoint (3): applies new positions, rejects foreign
  public_id, rejects empty list.
- Set-primary endpoint (4): flips flag, atomic swap invariant,
  refuses on deleted, unknown public_id 404.
- Delete/restore endpoints (5): stamps marked_deleted, double-
  delete 409, restore reverses, non-deleted restore 409,
  cross-tenant 404.

### test_admin_listing_endpoints.py (22 tests)

- Permission matrix (3).
- Read endpoint (3): no listing → null, existing returned,
  cross-tenant 404.
- Draft endpoint (5): creates listing, when-exists 409,
  scrub-dropped 422, empty LLM 422, cross-tenant 404.
- Lifecycle endpoints (11): regenerate replaces body, approve
  flips, publish flips, publish-on-draft 409, unpublish requires
  reason (400), full-lifecycle walk, regenerate-on-approved 409,
  approve-on-missing 404.

Uses `MockLLMProvider` via `patch("...get_llm_provider", return_value=...)`
so tests never hit Ollama / OpenAI.

### test_showroom_and_truthful_language.py (7 tests)

- Showroom endpoint (6): frontline + published → 200, nonexistent
  → truthful 404, frontline without listing → truthful 404,
  frontline with draft → truthful 404, non-frontline → truthful
  404, response never exposes cost data.
- Truthful customer-language (3): vehicle_detail non-retail →
  truthful 404, vehicle_detail retail → 200, truthful copy exact
  wording locked, vehicle_ask non-retail → truthful 404.

### Existing tests updated (6 tests)

Three test classes needed fixture updates because their vehicles
weren't customer-visible under the tightened gate:

- **`test_vehicle_assistant.VehicleDetailEndpointTests`** (2 tests)
  — added `_make_customer_visible(vehicle)` helper to publish a
  listing fixture.
- **`test_vehicle_assistant.VehicleAskEndpointTests`** (3 tests) —
  same fixture update.
- **`test_admin_vehicle_ledger.PublicSurfacesNeverExposeLedgerData`**
  (1 test) — setUp now publishes a listing so the ledger-leakage
  security check can reach the 200 path.

Net M6.5-related test delta: **+52 new** (0 regressions after
in-place fixture updates).

## Backend baseline

- **Pre-session:** 2,896 pass, 1 skipped, 0 fail.
- **Post-session:** 2,948 pass, 1 skipped, 0 fail.
- Delta: **+52** (52 new M6.5 tests; 6 existing tests updated
  in-place for the tightened customer-visibility contract, no net
  count change from those). Zero regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected." Zero new migrations.

## Frontend baseline

- `npx tsc --noEmit` clean (2 new pages + `lib/api.ts` extension +
  main.tsx route wiring).
- `npx vite build` clean (bundle 605.90 kB → ~610 kB — small
  bump from the two new pages + API helpers).

## Compatibility result

- **Frontend:** 2 new pages, extended API helpers, 2 new routes.
  No existing pages modified.
- **M1–M5 substrate + M6.1–M6.4:** every existing model, service,
  permission class, safety-stack scrub, and API unchanged. The
  6 in-place test fixture updates are additive (added a published-
  listing seed to test setUp; no test logic changed beyond that).
- **Migration graph:** unchanged at `0019` (M6.5 is
  endpoint / UI / refactor only).
- **Tenancy carriers:** unchanged at 19.
- **DRF admin surface:** 21 → **34** endpoints (+13 M6.5).
- **Frontend operator routes:** 5 → **7** (+2 M6.5).
- **Public endpoints:** +1 (showroom).
- **Service surface:** M6.5 added 3 view modules; extended
  `chat_engine.py` (2 new helpers + 1 constant); refactored 2
  customer-facing endpoints in `views.py`.

## Commit hashes

- Session commit: **659078f** (M6 ship commit; populate before overwriting
  `00-START-NEXT-SESSION.md`).

## Exact recommended scope for M6.6

**M6.6 — Closeout.** Documentation-only; no code changes.

- `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md` — full retro
  mirroring M5 shape (six sections: planned scope, per-increment
  ship notes, planning-doc amendments landed inside increments,
  deviations + deferrals, compatibility highlights, ten lessons).
- `docs/CAPABILITY_MATRIX.md §7g "Photography + listing
  generation (Milestone 6, shipped)"` — enumerate every shipped
  surface: 2 new models + 3 new services (`photo_gallery`,
  `vehicle_listing`, `showroom` chat-engine extensions) + 13 new
  admin/showroom endpoints + 2 new operator routes + 5 photo
  content-type + 4 listing status + M4.5 scrub dispatch
  extension.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — Milestone 6 marked
  SHIPPED at SESSION_087 (SESSION provenance + test-baseline delta
  2,754 → ~2,948).
- `docs/roadmap/MILESTONE_6_PLANNING.md` frontmatter — `status:
  draft` → `status: shipped` + `shipped_at_session: SESSION_087`.
- `docs/DEALER_KIT_SESSION_START.md` refresh — baseline table
  updated to `2948 passed`; new row listing M6 photo + listing
  surface at a glance.
- `docs/roadmap/MILESTONE_7_PLANNING.md` — per the standing user
  directive from SESSION_075 (create planning doc at each
  milestone close). Follow the M5/M6 shape.
- **Commit + push per user directive** — all M6.1–M6.6 stages
  committed and pushed together (mirrors M5 close pattern).

Test target: **zero new tests** (documentation-only closeout).
Baseline stays 2,948. Zero migrations.

**Out of M6.6:**
- No code changes.
- No new feature work.
- No new AI role.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md`
6. `docs/handoffs/SESSION_086_m6_inc5_endpoints_ui.md` (this doc)
7. `docs/handoffs/SESSION_085_m6_inc4_rules.md`
8. `docs/handoffs/SESSION_084_m6_inc3_listing_draft.md`
9. `docs/handoffs/SESSION_083_m6_inc2_photo_gallery.md`
10. `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
11. `docs/roadmap/MILESTONE_5_PLANNING.md` §5.i (M5.5 deferral
    M6.5 landed)
12. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
13. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` pain #8 + #9

Narrative docs are claims. Rules + research + code are facts.
