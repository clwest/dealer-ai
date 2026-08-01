---
title: "SESSION_087 handoff — Milestone 6 · Increment 6 (closeout) + Milestone 7 planning"
status: historical
type: handoff
date: 2026-08-01
session: 087
milestone: 6
milestone_status: shipped
increment: 6
increment_status: shipped
commit: TBD
---

# SESSION_087 — Milestone 6 · Increment 6 (M6.6 — closeout) + M7.0 (planning)

## What shipped

Documentation-only closeout + Milestone 7 planning
artifact + coordinated commit + push of all
M6.1–M6.6 stages per standing user directive.

**M6.6 deliverables (six):**

1. **`docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`** —
   full retrospective mirroring M5 shape (six
   sections: planned scope, what shipped per-increment,
   planning-doc amendments landed inside increments
   [zero for M6], deviations + deferrals,
   compatibility highlights, thirteen lessons — 10
   preserved + 3 new to M6).
2. **`docs/CAPABILITY_MATRIX.md` §7g "Photography +
   listing generation (Milestone 6, shipped)"** —
   enumerates every shipped surface: 2 models + 3
   new services + M3.4 storage extension + M4.5
   safety-stack dispatch extension + 2 rules + 13
   admin/showroom endpoints + 2 UI routes + all
   distinct domain errors + deferrals cataloged.
   Baseline number at top of doc updated 2,124 →
   2,948.
3. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** —
   Milestone 6 marked SHIPPED at SESSION_087 (SESSION
   provenance + test-baseline delta 2,754 → 2,948 +
   deferrals noted + cross-platform syndication
   explicitly out-of-scope per §5.e).
4. **`docs/roadmap/MILESTONE_6_PLANNING.md`
   frontmatter** — `status: draft` → `status:
   shipped` + `shipped_at_session: SESSION_087`
   field.
5. **`docs/DEALER_KIT_SESSION_START.md` refresh** —
   baseline table updated to `2948 passed`; new row
   listing M6 photo + listing surface at a glance;
   also added rows for tenancy carriers (19), DRF
   admin endpoints (34), frontend operator routes
   (7), public endpoints (+1 showroom). Smoke-check
   expectation updated to `2948 passed`.
6. **`docs/roadmap/MILESTONE_7_PLANNING.md`** — created
   per the standing user directive from SESSION_075:
   *"COntinue to 5.2 plan on commiting and pushing
   once we are done with Milestone 5 and created the
   MILESTONE_6_PLANNING.md just let we have in all
   past milestones!"* Full 9-section planning pass in
   the M4/M5/M6 shape. Five `[NEEDS-DECISION-BEFORE-M7.1]`
   items surfaced at §9.

## Backend baseline

- **Pre-session:** 2,948 pass, 1 skipped, 0 fail.
- **Post-session:** 2,948 pass, 1 skipped, 0 fail.
  **No change** — M6.6 is documentation-only.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."

## Frontend baseline

- `npx tsc --noEmit` clean (unchanged).
- `npx vite build` clean (unchanged).

## Commit + push

Per the standing user directive: **after MILESTONE_7
planning ships, commit + push all M6.1–M6.6 stages in
one coordinated push.** This session executes that.

Files staged for the coordinated M6.1–M6.6 push:

- **Backend production (M6.1–M6.5):**
  - `backend/dealer_ai/admin.py` (M6.1 diagnostic
    admin registrations + M6.2 public_id column
    additions).
  - `backend/dealer_ai/models.py` (M6.1 two new
    models + 3+4 vocabularies + M6.2 public_id).
  - `backend/dealer_ai/services/chat_engine.py`
    (M6.5 §5.i tightening helpers +
    CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY).
  - `backend/dealer_ai/services/llm_safety.py`
    (M6.3 `_RECON_COMM_KINDS` dispatch extension).
  - `backend/dealer_ai/services/photo_gallery.py`
    (M6.2 new module).
  - `backend/dealer_ai/services/photo_storage.py`
    (M6.2 vehicle-photo verbs + `put_bytes` on both
    adapters).
  - `backend/dealer_ai/services/tenancy.py` (M6.1
    `_TENANT_CARRIER_MODEL_NAMES` 17 → 19).
  - `backend/dealer_ai/services/vehicle_lifecycle.py`
    (M6.4 filled `_rule_photography_to_listing` +
    added `_rule_listing_to_frontline` + extended
    `suggest_transitions` dispatch).
  - `backend/dealer_ai/services/vehicle_listing.py`
    (M6.3 new module).
  - `backend/dealer_ai/urls.py` (M6.5 13 new URL
    patterns).
  - `backend/dealer_ai/views.py` (M6.5 §5.i refactor
    of `vehicle_detail` + `vehicle_ask`).
  - `backend/dealer_ai/views_listings.py` (M6.5 new).
  - `backend/dealer_ai/views_photos.py` (M6.5 new).
  - `backend/dealer_ai/views_showroom.py` (M6.5 new).
  - `backend/dealer_ai/migrations/0018_vehicle_photo_and_listing.py`
    (M6.1 new).
  - `backend/dealer_ai/migrations/0019_vehicle_photo_public_id.py`
    (M6.2 new).
- **Backend tests (M6.1–M6.5):**
  - `backend/dealer_ai/tests/test_admin_listing_endpoints.py`
    (M6.5 new — 22 tests).
  - `backend/dealer_ai/tests/test_admin_photo_endpoints.py`
    (M6.5 new — 23 tests).
  - `backend/dealer_ai/tests/test_admin_vehicle_ledger.py`
    (M6.5 in-place fixture update — 1 test class
    setUp).
  - `backend/dealer_ai/tests/test_llm_safety_recon_scrub.py`
    (M6.3 in-place update — `_RECON_COMM_KINDS`
    membership check).
  - `backend/dealer_ai/tests/test_m6_tenancy_carriers.py`
    (M6.1 new — 5 tests).
  - `backend/dealer_ai/tests/test_photo_gallery.py`
    (M6.2 new — 25 tests).
  - `backend/dealer_ai/tests/test_photo_storage_vehicle.py`
    (M6.2 new — 14 tests).
  - `backend/dealer_ai/tests/test_showroom_and_truthful_language.py`
    (M6.5 new — 7 tests).
  - `backend/dealer_ai/tests/test_vehicle_assistant.py`
    (M6.5 in-place fixture update — 5 tests updated).
  - `backend/dealer_ai/tests/test_vehicle_lifecycle_bootstrap.py`
    (M6.1 in-place — stale absolute-count assertion
    replaced with delta invariant).
  - `backend/dealer_ai/tests/test_vehicle_lifecycle_rules.py`
    (M6.4 in-place — 3 tests updated + 1 class
    renamed).
  - `backend/dealer_ai/tests/test_vehicle_lifecycle_rules_m6.py`
    (M6.4 new — 24 tests).
  - `backend/dealer_ai/tests/test_vehicle_listing.py`
    (M6.1 new — 14 tests).
  - `backend/dealer_ai/tests/test_vehicle_listing_service.py`
    (M6.3 new — 40 tests).
  - `backend/dealer_ai/tests/test_vehicle_photo.py`
    (M6.1 new — 18 tests).
- **Frontend (M6.5):**
  - `frontend/src/lib/api.ts` (M6.5 16 new fetch
    helpers + typed DTOs).
  - `frontend/src/main.tsx` (M6.5 2 new route
    registrations).
  - `frontend/src/pages/VehicleListingEditorPage.tsx`
    (M6.5 new).
  - `frontend/src/pages/VehiclePhotoGalleryPage.tsx`
    (M6.5 new).
- **Docs (M6.6):**
  - `docs/roadmap/MILESTONE_6_PLANNING.md` (frontmatter
    flip).
  - `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md` (new).
  - `docs/roadmap/MILESTONE_7_PLANNING.md` (new).
  - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` (M6
    SHIPPED, M7 next).
  - `docs/CAPABILITY_MATRIX.md` (§7g new, baseline
    updated).
  - `docs/DEALER_KIT_SESSION_START.md` (baseline
    refresh).
  - `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
    (new).
  - `docs/handoffs/SESSION_083_m6_inc2_photo_gallery.md`
    (new).
  - `docs/handoffs/SESSION_084_m6_inc3_listing_draft.md`
    (new).
  - `docs/handoffs/SESSION_085_m6_inc4_rules.md`
    (new).
  - `docs/handoffs/SESSION_086_m6_inc5_endpoints_ui.md`
    (new).
  - `docs/handoffs/SESSION_087_m6_closeout.md` (this
    doc).
  - `00-START-NEXT-SESSION.md` (M7.1 priority).

## Milestone 6 shipped — summary

- **Sessions:** 082 → 087.
- **Backend tests:** 2,754 → 2,948 (+194 tests, zero
  regressions).
- **Frontend:** clean tsc + vite build; 2 new pages +
  16 new API helpers + 2 new routes.
- **Migrations:** 0017 → 0019 (linear, no branches —
  M6.1 additive + M6.2 3-step public_id backfill).
- **Tenancy carriers:** 17 → 19.
- **DRF admin endpoints:** 21 → 34 (+13 M6.5).
- **Frontend operator routes:** 5 → 7 (+2 M6.5).
- **Public endpoints:** +1 M6.5 showroom.
- **Zero `§0.a` change-log amendments** across
  M6.1–M6.5 — every recommendation confirmed as-is.
  Inverse of M5's eight preamble amendments.
- **§5.d Option A (SESSION_084) — reuse M4.5
  `_scrub_invented_recon_fact`** via one-line
  `_RECON_COMM_KINDS` dispatch extension. No new
  scrub logic.
- **M5.5 §5.i truthful-language refactor** landed
  inline at M6.5 (3 files touched — chat_engine +
  views + tests — within the §4 Option A
  ≤3-files bound). Customer per-vehicle direct-
  access paths now require frontline + published
  listing; batch-query paths continue to use
  frontline-only.
- **Three deferrals cataloged for future
  milestones:** `_scrub_invented_photo_claim`
  (evidence-gated), per-dealer configurable photo-
  count threshold (evidence-gated), `Vehicle.public_id`
  UUID for tenant-safe external URLs
  (product-requirement-gated), cross-platform
  syndication (Milestone 11+), photo re-shoot /
  listing performance analytics (Milestone 8), image
  processing (indefinite), physical-delete reaper
  for tombstoned photos (Milestone 7 — M7.5 in the
  new planning doc).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md` (shipped)
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`
7. `docs/roadmap/MILESTONE_7_PLANNING.md`
8. `docs/handoffs/SESSION_087_m6_closeout.md` (this)
9. `docs/handoffs/SESSION_082_m6_inc1_core_models.md`
   → `SESSION_086_m6_inc5_endpoints_ui.md`
10. `docs/CAPABILITY_MATRIX.md` §7g

Narrative docs are claims. Rules + research + code are facts.
