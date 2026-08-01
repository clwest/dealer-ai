---
title: "Milestone 6 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-01
sessions: SESSION_082 → SESSION_087
milestone: 6
milestone_name: "Photography + listing generation"
related:
  - docs/roadmap/MILESTONE_6_PLANNING.md
  - docs/roadmap/MILESTONE_5_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 6
---

# Milestone 6 — Retrospective

Written at Milestone 6 close (SESSION_087). Records what
was planned, what shipped, what deviated and why, and
lessons carried forward for Milestone 7. Mirrors the
`MILESTONE_5_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_6_PLANNING.md` at SESSION_081 defined the
milestone as answering nine operational questions from
VCP Phase 5 + `INVENTORY_ACQUISITION_MAPPING.md` pains
#8 + #9 + `RECON_MAPPING.md` §photography + §listing
prep. The questions cover: *what photos exist for this
vehicle, what is the primary hero, how many listing-
ready photos does this vehicle have, which photos are
marked for safer-direction deletion, what listing copy
has the AI drafted, has the operator approved and
published the listing, when was the listing published
(M8 aging seam), what is the truthful "not yet listed"
language when a customer asks about a non-frontline
vehicle, and how does the operator SEE the photo
gallery + listing draft in the UI?*

§1 followed with seven design-memo entries covering both
models (`VehiclePhoto`, `VehicleListing`), the photo
storage layer, two new services (`services/photo_gallery.py`,
`services/vehicle_listing.py`), the customer-chat
truthful-language refactor (M5.5 §5.i deferral), the
operator UI, and the M5.3 rule stubs to fill.

§2 enumerated existing surfaces M6 touched with required
work. §3 defined the compatibility checklist. §5.a-§5.f
drafted six load-bearing decisions — **three flagged
`[NEEDS-DECISION-BEFORE-M6.1]`** requiring user review
before code landed. §7 sequenced six increments (M6.1-M6.6).

**Original §7 sequencing (M6.1 → M6.6) shipped verbatim.**
Each of the six sessions opened with the required
load-bearing decisions confirmed by the user before any
code landed. All planning recommendations were
confirmed as-is at each session open; **no §0.a
change-log amendments were required inside M6.1-M6.5.**

## 2. What actually shipped

Every §3 compatibility item verified true; details in
the annotated checklist at `MILESTONE_6_PLANNING.md` §3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M6.0 planning | 081 | `MILESTONE_6_PLANNING.md` (638 lines) resolving three load-bearing decisions and leaving three for user review | `5c040ab` |
| M6.1 core persistence | 082 | Two models (`VehiclePhoto`, `VehicleListing`) + migration `0018` (pure additive `CreateModel`; no data migration — M6 has no rows to bootstrap) + admin registrations + 3 photo content-type constants + 4 listing status constants + cross-tenant `clean()` guards + `_TENANT_CARRIER_MODEL_NAMES` extended 17 → 19 + 39 focused tests. **Three §9 decisions confirmed at session open (all A/C/A):** §5.a Option A (4-state listing vocabulary), §5.b Option C (fixed at 8 for v1), §5.c Option A (extend M3.4 storage). One M5.1 test refactored in-place (`test_carrier_count_is_seventeen` stale absolute-count assertion removed, covered by M6.1 tenancy tests) | TBD |
| M6.2 photo storage + gallery | 083 | Extended `services/photo_storage.py` (`build_canonical_vehicle_photo_key`, `parse_canonical_vehicle_photo_key`, `store_vehicle_photo` module-level + `put_bytes` on both `_LocalAdapter` and `_S3Adapter`). Created `services/photo_gallery.py` with 6 verbs (`upload_photo`, `set_primary` atomic swap, `reorder`, `mark_deleted`, `restore_deleted`, `listing_ready_count`) + 4 distinct domain errors (`CrossTenantPhotoError`, `PhotoValidationError`, `PhotoAlreadyDeletedError`, `PhotoNotDeletedError`) + 3 module constants (`LISTING_READY_MIN_WIDTH_PX=1024`, `LISTING_READY_MIN_HEIGHT_PX=768`, `LISTING_READY_PHOTO_COUNT=8`). Added `VehiclePhoto.public_id` UUIDField + migration `0019` (three-step: nullable AddField → RunPython backfill → NOT NULL + unique AlterField). 39 focused tests. **Three §M6.2 decisions confirmed at session open (all A):** §1 canonical key shape `dealerships/<slug>/vehicles/<stock>/photos/<uuid>/original`, §2 add `public_id`, §3 dimension threshold 1024×768 | TBD |
| M6.3 listing draft + AI scrub | 084 | Created `services/vehicle_listing.py` (~600 lines) with 5 verbs (`draft_listing`, `regenerate_draft`, `approve_listing`, `publish_listing`, `unpublish_listing`) + 5 distinct domain errors (`CrossTenantListingError` → 404, `InvalidListingTransitionError` → 409, `ListingImmutableError` → 409, `ListingScrubDroppedError` → 422, `EmptyListingDraftError` → 422). Extended `services/llm_safety.py::_RECON_COMM_KINDS` frozenset 2 → 3 (added `"vehicle_listing"`) — one-line dispatch addition, no new scrub logic per §5.d Option A user-confirmed. Source bundle assembly: Vehicle + latest completed condition report + M6.2 photo counts. LLM prompt pins boundaries: no pricing, no internal-detail leakage, no invented specs, no APR/rate language. 40 focused tests + 1 M4.5 preservation test update | TBD |
| M6.4 rule integration | 085 | Filled the M5.3 `_rule_photography_to_listing` stub with the real photo-count predicate (via `photo_gallery.listing_ready_count`) — active when count ≥ 8; structured unmet-prereq with shortfall count otherwise. Added new `_rule_listing_to_frontline` rule reading `VehicleListing.status='published' AND Vehicle.price > 0` — always returns SuggestedTransition; per-condition unmet-prereq. Extended `suggest_transitions` composition dispatch (one new `elif` branch for LISTING stage). 24 focused new tests + 3 M5.3 tests updated in-place (one class renamed to preserve the still-valid "no price-only rule" guard). **No load-bearing decisions required** — both predicates fully specified from SESSION_082 §5.b + SESSION_083 §3 confirmations | TBD |
| M6.5 endpoints + UI + §5.i | 086 | 3 new backend view modules (`views_photos.py`, `views_listings.py`, `views_showroom.py`) + 13 new URL patterns (6 photo admin + 6 listing admin + 1 public showroom `GET /showroom/vehicles/<stock_number>/`). Domain-error → HTTP mapping including 415 (unsupported content-type), 422 (AI scrub refused), 502 (storage backend fault). Extended `services/chat_engine.py` with `customer_lookup_visible_vehicle_by_id/stock` helpers + `CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY` constant — the M5.5 §5.i deferral landed inline (3 files: chat_engine + views + tests). Refactored `vehicle_detail` + `vehicle_ask` in `views.py`. 2 new operator UI pages (`VehiclePhotoGalleryPage.tsx`, `VehicleListingEditorPage.tsx`) + extended `lib/api.ts` (16 new fetch helpers + typed DTOs) + 2 new routes in `main.tsx`. 52 focused new tests + 6 existing tests updated in-place for tightened customer-visibility contract. **Five §M6.5 decisions confirmed at session open (all A):** URL shape, showroom by stock_number, two operator routes, §5.i inline within 3-files bound, single increment (52 tests under 70-split threshold) | TBD |
| M6.6 closeout | 087 | This retrospective + `CAPABILITY_MATRIX.md` §7g + `IMPLEMENTATION_ROADMAP.md` M6-shipped-M7-promoted + `MILESTONE_6_PLANNING.md` frontmatter flip + `DEALER_KIT_SESSION_START.md` refresh + `MILESTONE_7_PLANNING.md` created per standing user directive. Coordinated commit + push of all M6.1-M6.6 stages | TBD |

## 3. Planning-doc amendments landed inside increments

**Zero `§0.a` change-log amendments were required inside
M6.1-M6.5.** Every load-bearing decision surfaced at
each session open was resolved with the user's
confirmation of the recommended option — no override
required and therefore no amendment. This is a notable
inversion from M5's eight preamble amendments and
reflects M6's tighter planning-artifact discipline.

Two small planning-shape refinements landed but did NOT
require §0.a entries because they were within the
planning-doc's own extension slots:

1. **§5.d dispatch clarification (SESSION_084).** The
   §5.d recommendation (reuse M4.5 `_scrub_invented_recon_fact`)
   was implemented by adding `"vehicle_listing"` to the
   `_RECON_COMM_KINDS` frozenset in
   `services/llm_safety.py`. This is a one-line
   dispatch addition, not new scrub logic. Documented
   inline in `llm_safety.py` with a comment
   referencing SESSION_084 §5.d Option A. Not a
   planning amendment — the planning §5.d explicitly
   said "reuse" and the dispatch is the mechanism.

2. **M6.2 module constants (SESSION_083).** The
   dimension threshold (`LISTING_READY_MIN_WIDTH_PX=1024`,
   `LISTING_READY_MIN_HEIGHT_PX=768`) landed as module
   constants in `services/photo_gallery.py` per §3
   Option A user-confirmed. The `LISTING_READY_PHOTO_COUNT=8`
   constant sits alongside per §5.b Option C
   (SESSION_082 confirmed). All three constants are
   embedded in the service module — no planning-doc
   change required.

## 4. Deviations

**Accepted improvements** (all landed inside
increments, all reviewed by user first):

1. **SESSION_082 M5.1 test refactor** — the
   `test_carrier_count_is_seventeen` absolute-count
   assertion naturally staled when M6.1 extended
   `_TENANT_CARRIER_MODEL_NAMES` 17 → 19. Removed the
   absolute-count check (covered by M6.1's
   `test_carrier_count_is_nineteen`) and kept the M5.1
   delta check (`test_new_carriers_include_stage_and_event`).
2. **SESSION_083 `_LocalAdapter.put_bytes` reuse of
   `store_local_upload`** — instead of duplicating the
   sidecar-file logic, `put_bytes` delegates to the
   existing `store_local_upload` helper. Keeps behavior
   identical; adds one dispatch method.
3. **SESSION_084 dispatch extension for the
   listing-copy scrub** — extended
   `_RECON_COMM_KINDS` frozenset rather than passing
   `kind='vendor_comm'` on a vehicle-listing draft
   (which would have lied in the audit log). One-line
   dispatch addition; no scrub logic changed.
4. **SESSION_085 class rename `NoListingToFrontlineRuleEverFires`
   → `NoPriceOnlyListingToFrontlineRuleEverFires`** —
   the M5 invariant was "no rule at listing stage
   ever fires"; M6.4 explicitly removed that invariant
   but preserved a related valid guard (no
   `price > 0`-only rule). Renamed to reflect the
   preserved constraint.
5. **SESSION_086 in-place fixture updates (6 tests
   across 3 test classes)** — the M6.5 tightening of
   `vehicle_detail` / `vehicle_ask` required a
   published listing on customer-facing test fixtures.
   Added `_make_customer_visible(vehicle)` helper in
   `test_vehicle_assistant.py` + explicit
   `VehicleListing.objects.create(...)` in
   `test_admin_vehicle_ledger.py`'s
   `PublicSurfacesNeverExposeLedgerData.setUp`.

**Deferrals cataloged** (not dropped; scheduled for
follow-up increments or future milestones):

- **§5.d `_scrub_invented_photo_claim` (M6.3
  Option B)** — Option A shipped (reuse recon-fact
  scrub). A dedicated `_scrub_invented_photo_claim`
  would require photo-content-aware validation logic;
  deferred pending operator evidence that fabricated
  photo-verifiable claims surface in practice.
- **§5.b per-dealer `DealerOnboardingProfile.listing_ready_photo_count`
  field (M6.1 Option B)** — Option C shipped (fixed
  at 8 for v1). Per-dealer configurability deferred
  pending operator evidence that the 8-photo default
  is wrong for enough dealers to justify the schema
  change + onboarding-form extension.
- **`Vehicle.public_id` UUID for tenant-safe external
  URLs (M6.5 §2 Option C)** — Option A shipped
  (`stock_number` in URLs). Adding `Vehicle.public_id`
  would enable enumeration-resistant customer-facing
  URLs; deferred pending observed abuse or product
  requirement.
- **Cross-platform listing syndication (Facebook
  Marketplace / AutoTrader / Cars.com / CarGurus)** —
  explicitly out-of-scope per M6 planning §5.e
  (publish = local showroom only). Vendor
  integrations named for Milestone 11+.
- **Photo re-shoot analytics + listing performance
  analytics** — Milestone 8 (operational intelligence
  aggregations).
- **Image processing (crop, brighten, thumbnail
  generation, EXIF stripping)** — deferred
  indefinitely; operator uploads what the operator
  uploads.
- **Physical-delete reaper for tombstoned photos** —
  safer-direction deletion is shipped; the eventual
  physical-delete reaper (probably in Milestone 7's
  async infrastructure) is deferred.

**No planned scope dropped** in the sense of a
shipped-but-broken feature or silently-missing
invariant.

## 5. Compatibility

Every §3 compatibility row verified true with inline
evidence at `MILESTONE_6_PLANNING.md` §3. Test baseline:
**2,948 pass, 1 skipped, 0 fail** at SESSION_086.
Delta: +194 tests over M5 close baseline (2,754 →
2,948); 0 regressions after in-place fixture updates
in M6.4 (3 tests) and M6.5 (6 tests).

Highlights:

- **Zero regressions** across M1–M5 test suites. All
  pre-M6 chat / vehicle-ask / ad-copy / follow-up /
  ledger / condition-report / recon / lifecycle tests
  continue to pass.
- **`Vehicle.is_available` schema + values unchanged.**
  §5.e Option D SESSION_075 refined preserved.
- **M2 ledger substrate byte-for-byte preserved.**
  `services/vehicle_ledger.py` API unchanged.
- **M3 substrate preserved.**
  `services/condition_report.py` API unchanged. M3.4
  `services/photo_storage.py` extended additively
  (new `put_bytes` method + new vehicle-photo verbs;
  existing condition-report methods untouched).
- **M4 substrate preserved.** `services/recon.py` +
  `services/vendor_comm.py` APIs unchanged. M4.5
  `_scrub_invented_recon_fact` scrub logic unchanged
  — only the `_RECON_COMM_KINDS` dispatch gained one
  kind.
- **M5 substrate preserved.**
  `services/vehicle_lifecycle.py` extended additively
  (M6.4 added one rule and filled one stub; the M5
  transition table + role authority + advance_stage
  service are unchanged).
- **Customer-facing filtering funnels through
  `customer_visible_vehicles()` (frontline gate,
  unchanged) + M6.5 tightening via
  `customer_lookup_visible_vehicle_by_id/stock`
  (frontline + published listing) — the tighter gate
  applies only at the stock-specific per-vehicle
  lookup path (`vehicle_detail`, `vehicle_ask`,
  showroom endpoint); batch-query surfaces (chat
  matched-vehicles, inventory search, lever-flex)
  continue to use the frontline-only gate to avoid
  over-filtering.**

## 6. Lessons

Ten lessons carried forward for Milestone 7 and beyond.
Seven inherit unchanged from M2 §6 + M3 §6 + M4 §6 +
M5 §6 with M6 evidence; three are new to M6.

1. **Increment discipline.** Each M6 sub-increment
   shipped independently verifiable in one session.
   Every session opened with load-bearing decisions
   confirmed (or overridden) by the user before code
   landed. Carry-forward from M5 §6 lesson 1.

2. **Backend-first architecture; frontend never owns
   business rules.** M6.5's two operator pages are
   thin orchestrators around the 12 M6.5 admin
   endpoints. Every write affordance is gated
   server-side by
   `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
   (DRF admission) + M6.2 / M6.3 service-layer per-
   operation cross-tenant guards
   (`CrossTenantPhotoError` /
   `CrossTenantListingError` → HTTP 404). The
   frontend role-gate is a UX convenience, not the
   authoritative rule. Carry-forward from M5 §6
   lesson 2.

3. **Provider-neutral boundaries.** M6.3 introduced
   AI-drafted listing copy via the same LLM factory
   the M4.5 vendor-comm draft uses. M6.2 photo
   storage extends the M3.4 provider-neutral adapter
   layer with a new `put_bytes` method on both
   `_LocalAdapter` (delegates to
   `store_local_upload`) and `_S3Adapter` (fresh
   `boto3 put_object`). No provider-specific
   coupling in the model or endpoint layer.
   Carry-forward from M5 §6 lesson 3.

4. **Service ownership — one authoritative write
   path per operation.** Every M6.5 endpoint
   delegates to `services/photo_gallery.py` or
   `services/vehicle_listing.py`. The endpoints do
   URL/serializer/error-mapping work only;
   business logic lives in the services. Cross-
   tenant guards live in the services; DRF
   permission classes are the coarse admission
   layer. Carry-forward from M5 §6 lesson 4.

5. **Local vs production parity.** Every M6 code
   path walks the same shape in tests as in
   production. The M3.4 photo storage layer's
   local/S3 adapter split extends to the new
   `put_bytes` method — local mode delegates to the
   existing sidecar-file `store_local_upload`;
   production uses boto3 `put_object`. Test doubles
   (`MockLLMProvider` via `patch("...get_llm_provider")`)
   keep the M6.3 listing tests off Ollama /
   OpenAI while exercising the real safety-stack
   scrub. Carry-forward from M5 §6 lesson 5.

6. **Honest verification reporting.** The M6.4
   `_rule_photography_to_listing` rule and the new
   `_rule_listing_to_frontline` rule ALWAYS return a
   `SuggestedTransition` — either active or
   structured unmet-prereq with per-condition
   evidence. Operators see exactly what's blocking a
   transition; no fake suggestions, no silent
   omissions. The M5.5 §5.i deferral landed inline
   at M6.5 with the truthful copy: "That vehicle is
   not currently available for retail." — no
   internal-state leakage. Carry-forward from M5 §6
   lesson 6.

7. **Storage-first / safer-direction deletion.** M6.2
   `photo_gallery.mark_deleted` stamps
   `marked_deleted_at` + `deleted_by` and clears
   `is_primary` — the row and storage bytes survive
   for a future physical-delete reaper (deferred to
   M7 or later). The M6.5 admin API surfaces this
   via `DELETE` + `POST /restore/` pair; the
   operator UI renders active and recently-deleted
   panels separately. Carry-forward from M3 §6
   lesson 7.

8. **Load-bearing decisions get user review BEFORE
   code.** Preserved from M5 §6 lesson 8. Every M6
   session opened with the required
   `[NEEDS-DECISION-BEFORE-M6.N]` items surfaced to
   the user before code landed. **Every
   recommendation was confirmed as-is** — the
   inversion from M5's eight preamble amendments to
   M6's zero-amendments reflects tighter planning
   discipline at M6.0 (SESSION_081) and cleaner
   per-session decision surface. Carry-forward.

9. **Distinct domain errors → distinct HTTP status
   codes.** M6.2 shipped 4 distinct photo errors
   (Cross → 404, Validation → 400, AlreadyDeleted →
   409, NotDeleted → 409). M6.3 shipped 5 distinct
   listing errors (Cross → 404,
   InvalidTransition → 409, Immutable → 409,
   ScrubDropped → 422, EmptyDraft → 422). M6.5
   added 2 more HTTP status codes to the platform's
   mapping (415 unsupported media type,
   502 backend fault). Every error class → one
   HTTP status → one remediation path. Preserved
   from M5 §6 lesson 9. Carry-forward.

10. **Read-model properties are pure reads.**
    Preserved from M5 §6 lesson 10. M6 added no
    new Vehicle `@property` accessors. When M6.5
    needed a "customer lookup by id, retail-gated"
    read path, it landed as a module-level helper
    (`customer_lookup_visible_vehicle_by_id`) rather
    than as a Vehicle property — same rationale:
    hidden writes are forbidden and helper
    functions make the boundary explicit. Carry-
    forward.

11. **[NEW] Additive extension over fork.** M6.2's
    `services/photo_storage.py` extension added a new
    canonical key vocabulary + a new `store_vehicle_photo`
    verb + a new `put_bytes` method on both existing
    adapters — without disturbing any M3.4 caller. M6.3's
    `services/llm_safety.py::_RECON_COMM_KINDS`
    extension added one element to the frozenset —
    dispatch-only, no scrub logic touched. M6.4's
    `services/vehicle_lifecycle.py` extension filled
    one M5.3 stub and added one new rule alongside the
    existing composition dispatch — no signatures
    changed. **Every future milestone that touches an
    existing service should default to additive
    extension; forking a service is a load-bearing
    decision that requires justification.**

12. **[NEW] Zero-planning-amendment sessions are a
    signal of good planning-doc discipline.** M6.1
    through M6.5 shipped without a single `§0.a`
    change-log amendment. Every user-facing decision
    was framed clearly enough at planning time
    (SESSION_081) that at each session open the
    recommendations could be confirmed as-is. This is
    the inverse of M5 (eight amendments) and
    validates the M4/M5-refined planning-doc shape.
    **Future milestone-planning sessions should aim
    for zero-amendment increments as a signal that
    decisions were surfaced cleanly.**

13. **[NEW] Per-vehicle direct-access paths need a
    tighter customer-visibility gate than batch-
    query paths.** M6.5 §5.i landed the split:
    `customer_visible_vehicles()` (frontline-only,
    unchanged) governs chat matched-vehicles /
    search / lever-flex batch queries;
    `customer_lookup_visible_vehicle_by_id/stock`
    (frontline + published listing) governs
    per-vehicle stock-specific direct-access
    (`vehicle_detail`, `vehicle_ask`, showroom
    endpoint). A vehicle at frontline WITHOUT a
    published listing is still-in-preparation;
    exposing it via direct-access URL would leak
    operational readiness before the operator has
    signed off on customer-facing copy. **Every
    future customer-facing surface should
    distinguish "batch retrieval" gate from
    "direct-access by identifier" gate.**
