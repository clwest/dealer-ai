---
title: "SESSION_085 handoff — Milestone 6 · Increment 4 (deterministic rule integration)"
status: historical
type: handoff
date: 2026-08-01
session: 085
milestone: 6
milestone_status: in-progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_085 — Milestone 6 · Increment 4 (M6.4 — deterministic rule integration)

## What shipped

The M5.3 `_rule_photography_to_listing` stub filled with the real
photo-count predicate (consuming M6.2's
`photo_gallery.listing_ready_count`). A new
`_rule_listing_to_frontline` rule reading
`VehicleListing.status='published' AND Vehicle.price > 0` (consuming
M6.3's `VehicleListing` state). `suggest_transitions` composition
dispatch extended to include the `listing` stage. Three M5.3 tests
updated in-place to reflect the M6.4 predicate replacements + one
class renamed. 24 focused new tests + 3 M5.3 test updates. **No
admin endpoints, no frontend, no customer-chat refactor, no new
migrations, no new domain errors, no new AI role — all deferred to
M6.5+.**

**No load-bearing decisions required at session open.** Per the
SESSION_084 handoff, both predicates were fully specified from
prior sessions:

- Photo count threshold: 8 (SESSION_082 §5.b Option C).
- Photo dimension threshold: `1024x768` (SESSION_083 §3 Option A,
  applied inside `listing_ready_count`).
- `_rule_listing_to_frontline` predicate: `status='published' AND
  price > 0` (M6.3 §1.7 planning).

## Rule updates in services/vehicle_lifecycle.py

### `_rule_photography_to_listing` (filled — replaces M5.3 stub)

**Behavior change:** was a permanent structured unmet-prereq
("M6 not yet shipped"); now reads
`photo_gallery.listing_ready_count(vehicle, dealership)` and:

- Returns an **active** `SuggestedTransition` (empty
  `unmet_prerequisites`) when `count >= LISTING_READY_PHOTO_COUNT`
  (which is 8). Evidence: `"Vehicle has N listing-ready photo(s)
  (threshold: 8)."`
- Returns a **structured unmet** `SuggestedTransition` when count is
  below threshold. `unmet_prerequisites=("Need N more listing-ready
  photo(s) (current: X / 8).",)`

**Signature parity preserved.** Still returns
`SuggestedTransition` (never `None`) — matches the M5.3 stub
contract; the M5.4 endpoint + M5.6 UI shape is unchanged.

### `_rule_listing_to_frontline` (new — M6.4 addition)

Reads `VehicleListing` (filter by vehicle, take first — OneToOne so
at most one) and `Vehicle.price`. Both conditions checked
independently so each failing condition surfaces as its own
`unmet_prerequisites` entry:

- No `VehicleListing` row → "No VehicleListing exists yet — draft
  + approve + publish via services/vehicle_listing.py."
- Listing exists but `status != 'published'` → "Listing status is
  <status!r>; must be 'published'..."
- `price` is `None` or `<= 0` → "Vehicle.price is <price>; must be
  > 0..."

Active when BOTH conditions met. Evidence: `"Listing is published;
Vehicle.price is $<price>. Vehicle is ready for the frontline."`

**Structural safeguard preserved.** A `price > 0` alone (with no
published listing) does NOT fire an active suggestion — the guard
against a naive "price-only" rule (per prior M5 discipline) remains
via the two-condition unmet-check.

### `suggest_transitions` dispatch extension

Added one `elif` branch:

```python
elif stage.current_stage == VEHICLE_STAGE_LISTING:
    suggestions.append(
        _rule_listing_to_frontline(vehicle, dealership=dealership)
    )
```

Composition remains **suggestion-only** — no auto-application. The
M5.4 endpoint accepts suggestions via an explicit operator gesture
(unchanged).

## M5.3 test file updates

Three tests in `test_vehicle_lifecycle_rules.py` naturally staled
when the M6.4 predicates replaced the M5.3 stubs. Updated in-place:

1. **`test_prerequisite_mentions_m6`** →
   **`test_prerequisite_names_photo_count`**. The M5.3 stub
   language cited "M6 not shipped"; the M6.4 predicate cites the
   count shortfall. Test now asserts "listing-ready" + "8" appear
   in the unmet-prereq evidence.

2. **`test_listing_stage_returns_empty`** →
   **`test_listing_stage_composes_listing_to_frontline`**. The M5
   invariant was "listing stage returns no rule"; M6.4 explicitly
   removed that invariant. Test now asserts the new rule dispatch
   returns one SuggestedTransition targeting frontline.

3. **`NoListingToFrontlineRuleEverFires`** class →
   **`NoPriceOnlyListingToFrontlineRuleEverFires`** class. The
   original class locked the M5 "no rule at listing stage" invariant
   which M6.4 removed. The renamed class preserves the still-valid
   guard: `price > 0` with no published listing must NOT fire an
   active suggestion. The M6.4 rule's two-condition structure
   satisfies this guard.

Additive-only otherwise — no other M5.3 tests touched.

## Tests added

One new file, 24 focused new tests (target ~25):

- **`test_vehicle_lifecycle_rules_m6.py`** (24 tests):
  - `RulePhotographyToListingActive` (5) — fires at threshold,
    fires above, active target/rule_name, active evidence names
    count + threshold, cross-tenant refused.
  - `RulePhotographyToListingUnmet` (5) — zero photos returns
    unmet, below threshold returns unmet, low-res photos (below
    dimension threshold) don't count, marked-deleted photos don't
    count, unmet evidence names shortfall.
  - `RuleListingToFrontlineActive` (4) — fires when published +
    price, active evidence includes price, cross-tenant refused,
    returns SuggestedTransition type.
  - `RuleListingToFrontlineUnmet` (6) — no listing returns unmet,
    draft/approved/unpublished each return unmet, zero price
    returns unmet, both conditions missing returns two unmets.
  - `SuggestTransitionsM6Composition` (4) — photography stage
    dispatches to photo rule (active), listing stage dispatches to
    frontline rule (active), full lifecycle walk generates correct
    per-stage suggestions, frontline stage still returns empty.

Total M6.4-related test delta: +24 new + 3 in-place updates + 1
class rename = **+24 net new tests**.

## Backend baseline

- **Pre-session:** 2,872 pass, 1 skipped, 0 fail.
- **Post-session:** 2,896 pass, 1 skipped, 0 fail.
- Delta: **+24** (all new M6.4 tests; M5.3 test updates were
  in-place edits, not net-new tests). Zero regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- No new migrations — M6.4 is service-only.

## Frontend baseline

- `npx tsc --noEmit` clean (unchanged — no frontend files touched).
- `npx vite build` clean (unchanged — 605.90 kB bundle).

## Compatibility result

- **Frontend:** untouched.
- **M1–M5 substrate + M6.1 + M6.2 + M6.3:** unchanged. The
  2,872 → 2,896 test delta is +24 M6.4 rule tests, no regressions.
- **Migration graph:** unchanged at `0019` (M6.4 is service-only).
- **Tenancy carriers:** unchanged at 19.
- **AI safety stack:** unchanged from SESSION_084 (recon-fact scrub
  still fires on the 3-kind dispatch).
- **`_rule_photography_to_listing` signature:** unchanged (still
  returns `SuggestedTransition`, never `None`). Only the behavior
  changed — from permanent unmet-stub to real predicate evaluation.
- **`suggest_transitions` signature:** unchanged. Only the internal
  dispatch composition changed (one new `elif` branch).

## Commit hashes

- Session commit: **TBD** (populate at close before overwriting
  `00-START-NEXT-SESSION.md`).

## Exact recommended scope for M6.5

**M6.5 — Admin API + operator UI + truthful customer language.**
The final feature increment before M6.6 closeout. Combines three
distinct workstreams into one increment per planning §7 M6.5:

### Admin endpoints (per §1.5 endpoint plan)

- **Photo endpoints** (via M6.2 `services/photo_gallery.py`):
  - `POST /api/admin/vehicles/<pk>/photos` — upload.
  - `GET /api/admin/vehicles/<pk>/photos` — list gallery.
  - `POST /api/admin/vehicle-photos/<public_id>/set-primary`.
  - `PATCH /api/admin/vehicles/<pk>/photos/reorder`.
  - `DELETE /api/admin/vehicle-photos/<public_id>` (safer-direction).
  - `POST /api/admin/vehicle-photos/<public_id>/restore`.
- **Listing endpoints** (via M6.3 `services/vehicle_listing.py`):
  - `POST /api/admin/vehicles/<pk>/listing/draft`.
  - `POST /api/admin/vehicles/<pk>/listing/regenerate`.
  - `POST /api/admin/vehicles/<pk>/listing/approve`.
  - `POST /api/admin/vehicles/<pk>/listing/publish`.
  - `POST /api/admin/vehicles/<pk>/listing/unpublish`.
- **Showroom endpoint (public)**:
  - `GET /showroom/vehicles/<pk>` — returns Vehicle + published
    listing body + primary photo URL. Only vehicles with
    `stage=frontline` AND published listing are visible.

### Operator UI (per §1.6)

- Route `/dealer-ai-inventory/:stock/photos` — photo gallery grid
  with upload / reorder / set-primary / delete / restore controls.
- Route `/dealer-ai-inventory/:stock/listing` — draft-view + edit +
  approve + publish + unpublish controls.
- Extracted components in `components/photos/` +
  `components/listing/`.

### Customer-chat truthful-language refactor (§1.5 — M5.5 §5.i
deferral)

Refactor `services/chat_engine.py` stock-specific customer lookup
path. When a customer asks about a vehicle whose lifecycle stage is
not `frontline` OR whose `VehicleListing.status != 'published'`,
return the truthful copy per §5.i: *"That vehicle is not currently
available for retail."* Do NOT expose stage / recon details / ETA /
vendor / expected-ready-date.

If locating the exact `chat_engine.py` path requires more
investigation than fits an increment, defer AGAIN and document
clearly.

### Test target

~50 focused endpoint + UI + language-scrub tests. Baseline
2,896 → ~2,946. Zero regressions. Zero migrations expected.

**Out of M6.5:**

- No cross-platform push (Facebook Marketplace / AutoTrader) —
  Milestone 11+.
- No photo re-shoot analytics — Milestone 8.
- No listing performance analytics — Milestone 8.
- No image processing (crop / brighten / thumbnail) — deferred
  indefinitely.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md`
6. `docs/handoffs/SESSION_085_m6_inc4_rules.md` (this doc)
7. `docs/handoffs/SESSION_084_m6_inc3_listing_draft.md`
8. `docs/handoffs/SESSION_083_m6_inc2_photo_gallery.md`
9. `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
10. `docs/roadmap/MILESTONE_5_PLANNING.md` §5.h (M5.3 stubs M6.4
    filled)
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
12. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` pain #8 + #9

Narrative docs are claims. Rules + research + code are facts.
