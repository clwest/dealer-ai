---
title: "SESSION_084 handoff — Milestone 6 · Increment 3 (listing draft + AI safety scrub)"
status: historical
type: handoff
date: 2026-08-01
session: 084
milestone: 6
milestone_status: in-progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_084 — Milestone 6 · Increment 3 (M6.3 — listing draft + AI safety scrub)

## What shipped

The vehicle-listing drafting service — the M6 counterpart to M4.5
vendor-comm drafting. Created `services/vehicle_listing.py` with five
public verbs (`draft_listing`, `regenerate_draft`, `approve_listing`,
`publish_listing`, `unpublish_listing`) + five distinct domain-error
classes + source-bundle assembly + LLM factory integration + M4.5
safety-stack scrub reuse via dispatch extension. Extended
`services/llm_safety.py::_RECON_COMM_KINDS` to include
`"vehicle_listing"` (one-line dispatch addition; no new scrub logic).
Updated one M4.5 test to reflect the extended dispatch. 40 focused
tests (target ~40). **No deterministic rules, no admin endpoints, no
frontend, no customer-chat refactor — all deferred to M6.4+.**

Also: **one load-bearing decision confirmed by the user at session
open** (per M6 §7 lesson 8) before any code was written.

## Session preamble — the one §5.d decision

Per `MILESTONE_6_PLANNING.md` §5.d, one
`[NEEDS-DECISION-BEFORE-M6.3]`-adjacent item required user
confirmation before implementation. The user **confirmed the
recommended option**:

**§5.d — Listing-copy AI safety scrub: Option A.** Reuse the existing
M4.5 `_scrub_invented_recon_fact` scrub. No new scrub function, no
new scrub logic. Listing copy that fabricates recon-related claims
(fake finding IDs, invented part numbers, fabricated dollar amounts,
made-up ISO dates) gets caught by the same guard M4.5 already ships.
Rejected Option B (dedicated `_scrub_invented_photo_claim` scrub —
larger scope, deferred pending operator evidence) and Option C
(defer with formal §5.d amendment — same code as A with extra
narrative overhead).

Implementation refinement: to keep the audit-log semantics clean
(rather than passing `kind='vendor_comm'` on a vehicle-listing
draft), extended `services/llm_safety.py::_RECON_COMM_KINDS` from
`{"vendor_comm", "parts_order"}` to
`{"vendor_comm", "parts_order", "vehicle_listing"}` — a one-line
dispatch addition that keeps the scrub logic itself unchanged. Not
a new scrub; the safety-stack recon-fact scrub simply now fires on
one more kind. Documented inline in `llm_safety.py` with a comment
referencing SESSION_084 §5.d Option A.

No planning amendments beyond this dispatch clarification were
required — the recommendation was confirmed as-is.

## services/vehicle_listing.py (new module)

`backend/dealer_ai/services/vehicle_listing.py` — five public verbs
mirroring the M4.5 `services/vendor_comm.py` draft/approve/send
shape (all invoked with keyword-only `dealership=` for cross-tenant
defense-in-depth):

### `draft_listing(vehicle, *, dealership, drafted_by, provider=None)` → `VehicleListing`

Three-step pattern:

1. **Source bundle assembly** — `_build_source_bundle(vehicle)`
   assembles Vehicle facts (stock, year, make, model, trim, mileage,
   VIN last 6, body style, condition, description) + latest
   completed `ConditionReport` + its findings + M6.2 photo counts
   (`total`, `listing_ready`, `primary_public_id`). Scrub-
   compatibility stubs (`authorized_cost=None`, `parts_needed=[]`,
   `estimated_completion_date=None`) preserve the recon-fact scrub's
   valid-facts lookup shape.
2. **LLM invocation** — `_build_llm_messages(source_bundle)` renders
   a strict prompt: no pricing (operator adds separately), no
   internal-detail leakage (findings / work orders / recon tiers),
   no invented specs, no APR/rate/financing language, no
   promotion/discount claims, no photo-URL references. Prompts the
   LLM to draft 2-4 short paragraphs of descriptive prose.
3. **Safety scrub** — `apply_post_llm_scrubs(raw, kind='vehicle_listing',
   recon_source_bundle=source_bundle)`. The M4.5
   `_scrub_invented_recon_fact` fires on the new
   `"vehicle_listing"` kind (dispatch extension per §5.d Option A),
   validating any finding IDs / part numbers / dollar amounts / ISO
   dates against the source bundle. Wholesale-rewrite signals
   (`dealer_cost_safety`, negotiation, handoff phrasing) surface as
   `ListingScrubDroppedError`; empty output surfaces as
   `EmptyListingDraftError`. **Neither error persists a row.**

Persists a `VehicleListing` at `status='draft'` with `drafted_by` +
`drafted_at` + `source_provenance` (source bundle + scrubs_fired +
LLM provider name).

**Refuses if a listing already exists** for the vehicle (any status)
with `ListingImmutableError`. Callers use `regenerate_draft` to
replace an existing draft.

### `regenerate_draft(listing, *, dealership, drafted_by, provider=None)` → `VehicleListing`

Replaces the current draft body via a fresh LLM invocation. Refused
when `status != 'draft'` (`ListingImmutableError`). Overwrites
`body` + `source_provenance` + `drafted_by` + `drafted_at`. Keeps
`title` (operator-authored) unchanged. Wrapped in
`transaction.atomic()` + `select_for_update()`.

### `approve_listing(listing, *, dealership, approved_by)` → `VehicleListing`

Flips `draft → approved`. Refused otherwise with
`InvalidListingTransitionError`. Sets `approved_by` + `approved_at`.

### `publish_listing(listing, *, dealership, published_by)` → `VehicleListing`

Flips `approved → published`. Refused otherwise with
`InvalidListingTransitionError`. Sets `published_by` +
`published_at`. **Drives the M6.4 `_rule_listing_to_frontline`
predicate.**

Publish semantics per planning §5.e: `published` means "visible to
customers on the M6.5 `/showroom` endpoint." M6 v1 does NOT push to
Facebook Marketplace / AutoTrader / etc.

### `unpublish_listing(listing, *, dealership, unpublished_by, reason)` → `VehicleListing`

Flips `published → unpublished`. Refused otherwise. **`reason`
required** — nonblank operator explanation (raises `ValueError`
if empty). Truncated at 255 chars (matches `unpublished_reason`
CharField `max_length`).

### Five distinct domain errors (per M6 §6 lesson 9)

- **`CrossTenantListingError`** → HTTP 404.
- **`InvalidListingTransitionError`** → HTTP 409 (structural
  from/to illegality).
- **`ListingImmutableError`** → HTTP 409 (operation forbidden by
  current state — draft_listing when exists, regenerate_draft on
  non-draft).
- **`ListingScrubDroppedError`** → HTTP 422 (LLM output rejected
  by safety stack).
- **`EmptyListingDraftError`** → HTTP 422 (LLM returned empty).

`InvalidListingTransitionError` and `ListingImmutableError` are
distinct classes even though they both map to HTTP 409 — the M6.5
endpoint layer surfaces distinct remediation messages ("cannot
publish a draft; approve it first" vs. "a listing already exists;
use regenerate_draft").

## llm_safety.py extension (one-line dispatch)

`backend/dealer_ai/services/llm_safety.py::_RECON_COMM_KINDS`
extended from `{"vendor_comm", "parts_order"}` to
`{"vendor_comm", "parts_order", "vehicle_listing"}`. Documented
inline with a comment referencing SESSION_084 §5.d Option A user-
confirmed. **No scrub logic changed** — the recon-fact scrub
already existed; extending the dispatch simply enables it for a new
kind.

## Tests added

One new file, 40 focused tests total (target ~40):

- **`test_vehicle_listing_service.py`** (40 tests):
  - `DraftListing` (7) — creates row at draft, persists body,
    provenance, drafted_by / drafted_at, cross-tenant refused,
    refused when listing exists, provider param defaults to None.
  - `DraftEmptyOrScrubbed` (2) — empty LLM output raises
    `EmptyListingDraftError` (no row persisted); wholesale-rewrite
    signal (via `detect_unsafe_response`) raises
    `ListingScrubDroppedError` (no row persisted).
  - `ScrubIntegration` (3) — invented `Finding #9999` stripped,
    invented `$500` stripped, `vehicle_listing` present in
    `_RECON_COMM_KINDS`.
  - `SourceBundle` (3) — vehicle facts present, findings from
    latest completed report present, photo counts present
    (total + listing_ready via `photo_gallery.listing_ready_count`).
  - `RegenerateDraft` (5) — replaces body, updates drafted_by /
    drafted_at, refused on approved, cross-tenant refused,
    preserves operator title.
  - `ApproveListing` (4) — flips to approved, persists actor +
    timestamp, refused on non-draft, cross-tenant refused.
  - `PublishListing` (5) — flips to published, persists actor +
    timestamp, refused on non-approved, refused on draft (cannot
    skip approve), cross-tenant refused.
  - `UnpublishListing` (6) — flips to unpublished, persists actor +
    timestamp + reason, refused on non-published, refused on empty
    reason, reason truncated at 255, cross-tenant refused.
  - `ErrorHierarchy` (2) — all errors subclass ValueError, five
    classes are distinct.
  - `FullLifecycle` (2) — full ladder walk
    (draft→approved→published→unpublished), no direct re-draft
    after unpublish (locks the current guard).
  - `ModuleSurface` (1) — five public verbs exposed.

**Plus one M4.5 test file update** (`test_llm_safety_recon_scrub.py`):
- `ReconCommKindsMembership.test_recon_comm_kinds_exact_membership`
  updated to expect the 3-element set (was 2). Added new sibling
  test `test_m45_recon_comm_kinds_still_members` verifying the M4.5
  additions (`vendor_comm`, `parts_order`) are preserved (additive-
  only invariant).

## Backend baseline

- **Pre-session:** 2,831 pass, 1 skipped, 0 fail.
- **Post-session:** 2,872 pass, 1 skipped, 0 fail.
- Delta: **+41** (40 new M6.3 tests + 1 new M4.5 preservation
  test), zero regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- No new migrations — M6.3 is service-only.

## Frontend baseline

- `npx tsc --noEmit` clean (unchanged — no frontend files touched).
- `npx vite build` clean (unchanged — 605.90 kB bundle).

## Compatibility result

- **Frontend:** untouched. Zero frontend files changed.
- **M1–M5 substrate + M6.1 + M6.2:** every existing model, service,
  permission class, safety-stack scrub, API, and frontend behavior
  unchanged. The 2,831 → 2,872 test delta is +41 (40 new + 1 new
  preservation), no regressions.
- **Migration graph:** unchanged at `0019` (M6.3 is service-only).
- **Tenancy carriers:** unchanged at 19.
- **M4.5 `services/vendor_comm.py`:** untouched.
- **`_RECON_COMM_KINDS`:** additive extension — every M4.5 caller
  (`kind='vendor_comm'`, `kind='parts_order'`) continues to trigger
  the same scrub with the same shape.

## Commit hashes

- Session commit: **TBD** (populate at close before overwriting
  `00-START-NEXT-SESSION.md`).

## Exact recommended scope for M6.4

**M6.4 — Deterministic rule integration.** Fill in the M5.3
`_rule_photography_to_listing` stub with the real photo-count
predicate. Add new `_rule_listing_to_frontline` rule reading
`VehicleListing.status='published' AND Vehicle.price > 0`. Extend
`services/vehicle_lifecycle.py::suggest_transitions` composition to
dispatch both rules at their respective stages.

Rule predicates (per `MILESTONE_6_PLANNING.md` §1.7):

- **`_rule_photography_to_listing`** — fires when
  `photo_gallery.listing_ready_count(vehicle, dealership) >=
  photo_gallery.LISTING_READY_PHOTO_COUNT` (which is 8 per §5.b
  Option C user-confirmed at SESSION_082). Consumed by the
  suggested-transitions panel; operator confirms manually.
- **`_rule_listing_to_frontline`** — fires when
  `VehicleListing.status == 'published' AND Vehicle.price > 0`.
  Consumed by the suggested-transitions panel; operator confirms
  manually.

Both rules land in `services/vehicle_lifecycle.py` alongside the
existing M5.3 rules — extending the composition dispatch.

Test target: ~25 focused rule tests. Baseline 2,872 → ~2,897.
Zero regressions. Zero migrations.

**Out of M6.4:**
- No admin endpoints — M6.5.
- No frontend — M6.5.
- No customer-chat truthful-language refactor — M6.5.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md`
6. `docs/handoffs/SESSION_084_m6_inc3_listing_draft.md` (this doc)
7. `docs/handoffs/SESSION_083_m6_inc2_photo_gallery.md`
8. `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
9. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6 lessons
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
11. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` pain #8
12. `docs/CAPABILITY_MATRIX.md` §7e M4 vendor-comm drafting
    (M6.3 reused the M4.5 draft/approve/send pattern)

Narrative docs are claims. Rules + research + code are facts.
