---
title: "SESSION_104 handoff — Milestone 9 · Increment 5 (M9.5 — Operator UI extension)"
status: historical
type: handoff
date: 2026-08-02
session: 104
milestone: 9
milestone_status: in_progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_104 — Milestone 9 · Increment 5 (M9.5 — Operator UI extension)

## What shipped

Fifth **Realized Gross** tab on
`/dealer-ai-analytics/` wrapping the M9.3
+ M9.4 aggregation surface
(Q3 / Q6 / Q7 / Q8) + new
`VehicleSalePage` at
`dealer-ai-inventory/:stock/sale/` for
per-vehicle Sale + Delivery workflow. Two
GET dispatch additions on the M9.1/M9.2
write endpoints unblock the page's read
path. 27 new tests total (12 backend
shape-lock + 15 frontend Vitest).

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_9_PLANNING.md` §0.a SESSION_104
entry):**

1. **Decision A — Q7 placement:
   Option A confirmed.** Q7
   buyer-accuracy rank surface bundles
   into the fifth "Realized Gross"
   tab. Both Q3 + Q7 answer "who
   produced the profit?" — grouping
   keeps the operator's mental model
   tight.
2. **Decision B — Sale + Delivery UI:
   Option A confirmed** (per-vehicle
   dedicated page pattern). The
   codebase does not have a unified
   "vehicle-detail page with sub-tabs";
   every per-vehicle feature ships as
   its own route
   (`.../:stock/ledger`,
   `.../:stock/recon`, etc.). M9.5
   adds `.../:stock/sale/`.

**Substrate-gap #2 surfaced + resolved
(implementation-time):** the M9.1/M9.2
write endpoints had no GET companions,
which the M9.5 read-first page needs.
User confirmed **Option A** — add GET
dispatch to the existing URLs via
`@api_view(["GET", "POST"])`. Preserves
URL names + existing tests; ~50 backend
lines.

**M9.5 deliverables (six):**

1. **Fifth `AnalyticsSection` tab
   Realized Gross** on
   `/dealer-ai-analytics/`. Four
   sub-sections:
   - Q3 vehicle-type profitability
     (table).
   - Q6 gross-profit trend (line
     chart, sparse per-day series).
   - Q8 true inventory-turn (summary
     card with sold_count + mean +
     p50/p90/min/max).
   - Q7 per-buyer estimate accuracy
     rank (table).
2. **`frontend/src/lib/analyticsApi.ts`
   extended** with four new hooks +
   `formatShortDate` helper +
   dataclass mirror types. Existing
   M8 hooks + `formatMoney` /
   `formatPercent` reused.
3. **New `frontend/src/lib/saleApi.ts`
   module** — Sale + Delivery API
   client. Exports `createSale`,
   `readSale`, `createDelivery`,
   `readDelivery`, `updateDelivery`
   + type definitions. Local
   `isApi404` helper maps 404 →
   null return for the read hooks
   (natural "not created yet"
   shape).
4. **New `frontend/src/pages/VehicleSalePage.tsx`**
   at route
   `dealer-ai-inventory/:stock/sale/`.
   Three main render states: no
   Sale (create form) → Sale + no
   Delivery (start-delivery
   button) → Sale + Delivery
   (checklist toggle + verify-
   insurance). Role gate via
   `hasRole(...WRITE_ROLES)`
   (recon_manager / sales_manager
   / dealer_owner) for write
   affordance display; backend is
   authoritative.
5. **Backend GET dispatch additions**
   on M9.1 + M9.2 write endpoints
   via `@api_view(["GET", "POST"])`
   method-multiplex. Two helper
   functions: `_lookup_sale_or_404`
   + `_lookup_delivery_by_vehicle`.
   URL names preserved
   (`admin-sale-create`,
   `admin-delivery-create`); all
   existing M9.1/M9.2 tests
   continue to pass.
6. **27 new tests:**
   - `test_m9_read_endpoints.py`
     (12 backend): GET sale
     200/404/cross-tenant + auth
     matrix; GET delivery
     200/404/no-sale/cross-tenant;
     POST still works after
     method-dispatch.
   - `RealizedGrossTab.test.tsx`
     (7 Vitest): loading state,
     Q3/Q6/Q7/Q8 rendering paths,
     empty-state, forbidden banner.
   - `VehicleSalePage.test.tsx`
     (7 Vitest): loading, no-Sale
     create form, Sale+no-Delivery
     summary, Sale+Delivery
     checklist, toggle click,
     verify-insurance click, error
     state.
   - `DealerAnalyticsPage.test.tsx`
     (+1 Vitest): "renders all
     five tab triggers" test
     updated + new realized-gross
     hash-honor test.

## Test baseline

- **Backend:** 3,414 → **3,426 pass**,
  1 skipped, 0 fail (+12 M9.5 shape-lock
  tests exactly).
- **Frontend Vitest:** 19 → **34 pass**
  (+15 exactly per plan).
- **`manage.py check`:** clean.
- **`manage.py makemigrations --check
  --dry-run`:** "No changes detected"
  (no schema changes at M9.5).
- **`npx tsc --noEmit`:** clean.
- **`npx vite build`:** clean (bundle
  size warning unchanged — was already
  >500 kB pre-M9.5; not M9.5 delta).

## Migrations

`0001` – **`0024`** (unchanged since M9.2).

## Files touched (M9.5 scope)

**Backend (modified):**

- `backend/dealer_ai/views_sale.py` —
  `admin_sale_create` decorator changed
  to `@api_view(["GET", "POST"])`;
  added `_lookup_sale_or_404` helper +
  GET dispatch branch.
- `backend/dealer_ai/views_delivery.py`
  — `admin_delivery_create` decorator
  changed to `@api_view(["GET",
  "POST"])`; added
  `_lookup_delivery_by_vehicle`
  helper + GET dispatch branch.
- `backend/dealer_ai/urls.py` — URL
  comment updated to note GET dispatch
  (route + name unchanged).

**Backend (added):**

- `backend/dealer_ai/tests/test_m9_read_endpoints.py`
  (~180 lines, 12 shape-lock tests).

**Frontend (modified):**

- `frontend/src/lib/analyticsApi.ts` —
  4 new hooks + type definitions +
  `formatShortDate` helper for the
  sparse-series x-axis.
- `frontend/src/pages/DealerAnalyticsPage.tsx`
  — 5th tab wired in.
- `frontend/src/main.tsx` — new route
  `dealer-ai-inventory/:stock/sale`.
- `frontend/src/pages/DealerAnalyticsPage.test.tsx`
  — 5-tab assertion + realized-gross
  hash-honor test.

**Frontend (added):**

- `frontend/src/lib/saleApi.ts` (~140
  lines) — Sale + Delivery API client.
- `frontend/src/components/analytics/RealizedGrossTab.tsx`
  (~360 lines) — 4 sub-sections.
- `frontend/src/components/analytics/RealizedGrossTab.test.tsx`
  (~220 lines, 7 tests).
- `frontend/src/pages/VehicleSalePage.tsx`
  (~380 lines).
- `frontend/src/pages/VehicleSalePage.test.tsx`
  (~200 lines, 7 tests).

**Docs (modified):**

- `docs/roadmap/MILESTONE_9_PLANNING.md`
  §0.a — SESSION_104 amendment
  recording (a) UI Decisions A + B
  both Option A, (b) substrate-gap #2
  GET-dispatch resolution
  (Option A user-confirmed), (c)
  actual delivery vs planning.
- `00-START-NEXT-SESSION.md` —
  overwritten with M9.6 closeout
  priority.

## What SESSION_104 confirmed vs deferred

**M9 substrate now complete + wired:**

- Q3/Q6/Q7/Q8 aggregations visible
  in the operator UI's fifth tab.
- Sale + Delivery workflow reachable
  from a Vehicle-scoped page with
  full CRUD via API.

**Still deferred (from prior sessions):**

- `LeadVehicleInterest.stage_at_interest`
  annotation — through-model doesn't
  exist; scope creep to create
  (SESSION_103 §0.a).
- F&I / stips / chargebacks (M10).
- Portfolio-level BHPH analytics
  (M12).
- DMS write-back integrations.

## Push authorization state

- Working tree at session close: still
  dirty (bundling per M8 precedent).
  All M9.1–M9.5 files uncommitted (plus
  this handoff + start-next overwrite).
- `main` up to date with `origin/main`
  (last pushed commit `4923997`).
- **Coordinated M9 commit ships at M9.6
  per SESSION_101 open decision.**

## Fifteen M8 lessons applied at M9.5

- **Lesson 2 — backend-first
  architecture; frontend never owns
  business rules.** Every dollar +
  percent figure travels as a
  string on the wire and stays a
  string in the frontend. The Q7
  buyer-rank ordering is set by the
  backend verb; the UI just renders
  the returned order. Every write
  action delegates to the M9.1/M9.2
  service verbs via the endpoint.
- **Lesson 3 — pushback on planning
  gaps.** Session-open substrate
  check surfaced two gaps: the
  Vehicle-detail sub-tab shape
  (planning-time imprecision — the
  codebase actually uses per-vehicle
  dedicated pages) and the missing
  GET companions to M9.1/M9.2
  writes. Both surfaced to the user
  before code landed.
- **Lesson 4 — one authoritative
  read/write path.** Endpoint GET
  dispatch reuses the existing
  `_lookup_vehicle_or_404` +
  `get_current_dealership` primitives
  from the POST branch.
- **Lesson 11 — additive extension.**
  M9.5 makes no schema changes and
  breaks no M1–M9.4 tests. Every
  M9.1/M9.2 test that hit the write
  endpoints continues to pass after
  the method-multiplex refactor.
- **Lesson 13 — additive extension
  preserves URL names.** Both
  `admin-sale-create` and
  `admin-delivery-create` URL names
  are unchanged after GET dispatch
  addition — the write path still
  works with the same reverse()
  calls in every M9.1/M9.2 test.

## What SESSION_105 (M9.6) should do

Per `MILESTONE_9_PLANNING.md` §7 M9.6
(closeout, per M6/M7/M8 pattern):

1. **Read first:**
   `MILESTONE_9_PLANNING.md` §7 M9.6
   + full §0.a change-log; this
   handoff + all prior M9 handoffs
   (SESSION_100–SESSION_104);
   `MILESTONE_8_RETROSPECTIVE.md` §6
   (fifteen lessons + one new
   candidate from M9 substrate-gap
   pushback pattern);
   `MILESTONE_8_PLANNING.md` (for
   the closeout doc-shape
   precedent).
2. **Verify starting state:** M9.1–
   M9.5 uncommitted; backend
   **3,426 pass**; frontend **34
   pass**; check + migrations clean.
3. **Draft (in order):**
   - **`MILESTONE_9_RETROSPECTIVE.md`**
     — synthesize fifteen carry-over
     lessons + at least one new
     M9-specific lesson (candidates:
     "planning-time substrate
     assumption verification"
     surfaced twice at M9.4 +
     M9.5; "GET dispatch via method-
     multiplex" as an additive-
     extension pattern; "sparse
     time-series omit-vs-fill
     decision"; "denormalization at
     write time enables
     single-query aggregation").
   - **`CAPABILITY_MATRIX.md` §7j**
     — new §7j subsection for M9.
   - **`IMPLEMENTATION_ROADMAP.md`
     §M9 shipped** header.
   - **`MILESTONE_9_PLANNING.md`
     frontmatter flip** to `status:
     shipped`.
   - **`DEALER_KIT_SESSION_START.md`
     refresh** with M9-shipped
     numbers.
   - **`MILESTONE_10_PLANNING.md`**
     (new — per standing
     end-of-milestone directive).
4. **Coordinated commit** covering
   every M9.1–M9.6 file (per M8
   `34352ed` precedent). Message
   template:
   `"Milestone 9 shipped — sale + delivery closure (SESSION_100–105)"`.
5. **Push authorization check** —
   confirm with the user before
   pushing.
6. **Ship handoff at
   `docs/handoffs/SESSION_105_m9_closeout.md`.**

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 9
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_9_PLANNING.md` (with §0.a
   SESSION_100 + SESSION_101 + SESSION_102 +
   SESSION_103 + SESSION_104 amendments)
6. `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md` §6
   (fifteen lessons carry into M9)
7. `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy.md`
8. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
9. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
10. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
11. `docs/handoffs/SESSION_098_m8_inc5_operator_ui.md`
12. `docs/CAPABILITY_MATRIX.md` §7i
13. Current source code — authoritative.

Planning docs are claims. Rules + research
+ code are facts.
