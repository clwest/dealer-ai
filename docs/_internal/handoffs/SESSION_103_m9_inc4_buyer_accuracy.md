---
title: "SESSION_103 handoff — Milestone 9 · Increment 4 (M9.4 — Q7 buyer estimate accuracy)"
status: historical
type: handoff
date: 2026-08-02
session: 103
milestone: 9
milestone_status: in_progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_103 — Milestone 9 · Increment 4 (M9.4 — Q7 buyer estimate accuracy)

## What shipped

Q7 (`buyer_estimate_accuracy`) verb +
DRF endpoint. This closes the M8.2
deferral — the Q7 substrate
(`VehicleAcquisition.buyer` FK) shipped
at M9.1 and M9.4 now consumes it. The
`LeadVehicleInterest.stage_at_interest`
annotation half of M9.4 is **deferred**
to its own future increment: the plan
assumed a through-model that doesn't
exist, and creating it is scope creep
per PROJECT_RULES.md #4 + #5.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_9_PLANNING.md` §0.a
SESSION_103 entry):**

1. **§1.3 annotation deferred (Option
   2 — user-confirmed).** The Q7 half
   ships alone at M9.4; the
   `LeadVehicleInterest`-through-model
   work waits for its own dedicated
   planning session or a milestone
   where through-model creation is
   independently justified.
2. **§1.3 backfill posture: moot.**
   Because the annotation itself
   defers, the backfill posture
   question (Option A forward-only vs
   B/C historical reconstruction)
   surfaces at that future session,
   not this one.

**M9.4 deliverables (three):**

1. **Q7 —
   `services.analytics.recon::buyer_estimate_accuracy`**.
   Reads M9.1
   `VehicleAcquisition.buyer` FK to
   attribute each `WorkOrder` to the
   buyer whose acquisition brought the
   parent Vehicle in. Aggregates
   completed WOs with both non-null
   costs and a positive estimate.
   Returns
   `list[BuyerAccuracyRow]` sorted by
   `mean_absolute_variance_pct` asc
   (most accurate first). Supports an
   optional `buyer_user_id` filter to
   recover the single-buyer shape.
2. **New DRF endpoint** `GET
   /api/dealer-ai/admin/analytics/buyer-estimate-accuracy/`.
   Query args: `window_days` (default
   90), `buyer_user_id` (optional).
   Role-gated per M8 pattern.
3. **20 focused tests** in
   `test_m9_buyer_estimate_accuracy.py`:
   - 12 verb tests: empty / variance-
     and-bias math / display fallback /
     positive-bias underestimator /
     negative-bias overestimator /
     NULL-buyer excluded / in-flight WO
     excluded / zero-estimate excluded
     / multi-buyer ranking / filter
     arg / window / cross-tenant.
   - 8 endpoint tests: response shape /
     buyer filter / two 400s / auth /
     advisor 403 / owner 200 /
     cross-tenant no leak.

**Implementation-time notes** (recorded
in `MILESTONE_9_PLANNING.md` §0.a):

- **Deviation from M8 §1.8 spec.** M8
  planning specified single-buyer
  return (`-> BuyerAccuracyRow`). M9.4
  ships list-returning
  (`-> list[BuyerAccuracyRow]`) to
  match dashboard needs (rank all
  buyers in one call). Filtering by
  `buyer_user_id` recovers the
  single-buyer shape (0 or 1 rows).
- **NULL-buyer acquisitions excluded**
  from the aggregation. Historical
  rows written before M9.1 have no
  buyer provenance; treating them as
  an anonymous "unknown buyer" bucket
  would be misleading. This matches
  the M9.1 handoff's stated Q7 posture.
- **Window semantics.** `window_days`
  filters `VehicleAcquisition.purchase_date`
  (the buyer's activity window), not
  WO completion date. A buyer whose
  acquisitions predate the window is
  excluded even if their WOs completed
  recently — the buyer's decisions
  live at acquisition time.
- **Substrate gap discovery.** Plan
  §1.3 assumed `LeadVehicleInterest`
  existed as a through-model. It
  does not — `CustomerLead.interested_vehicles`
  is a plain `ManyToManyField(Vehicle)`
  backed by an implicit Django table.
  Creating the through-model + data
  migration + sweeping ~5 call sites
  in views.py / serializers.py /
  admin.py to switch from `add()` to
  `.through.objects.create(...)` is
  a full increment's scope, not part
  of M9.4.

## Test baseline

- **Backend:** 3,394 → **3,414 pass**,
  1 skipped, 0 fail (+20 M9.4 tests
  exactly).
- **Frontend Vitest:** unchanged at 19
  pass (no frontend at M9.4).
- **`manage.py check`:** clean.
- **`manage.py makemigrations --check
  --dry-run`:** "No changes detected"
  (no schema changes at M9.4).

## Migrations

`0001` – **`0024`** (unchanged from M9.2;
M9.3 + M9.4 were verb + endpoint only).

## Files touched (M9.4 scope)

**Backend (added):**

- `backend/dealer_ai/tests/test_m9_buyer_estimate_accuracy.py`
  (~330 lines, 20 tests).

**Backend (modified):**

- `backend/dealer_ai/services/analytics/recon.py`
  — added `BuyerAccuracyRow` dataclass +
  `_BuyerAccum` internal accumulator +
  `_buyer_display_for` helper +
  `buyer_estimate_accuracy` verb below
  M8.2 `vendor_performance`. Extended
  module docstring with M9.4 provenance
  and Q7 substrate journey narrative.
- `backend/dealer_ai/services/analytics/__init__.py`
  — facade extended with `BuyerAccuracyRow`
  + `buyer_estimate_accuracy` in imports
  and `__all__`.
- `backend/dealer_ai/views_analytics.py`
  — new `_project_buyer_accuracy_row`
  projection + `admin_analytics_buyer_estimate_accuracy`
  endpoint handler.
- `backend/dealer_ai/urls.py` — new
  `admin/analytics/buyer-estimate-accuracy/`
  route.

**Docs (modified):**

- `docs/roadmap/MILESTONE_9_PLANNING.md`
  §0.a — SESSION_103 amendment
  recording (a) §1.3 annotation
  deferral (Option 2) + (b) verb
  return-shape deviation (list
  instead of single row).
- `00-START-NEXT-SESSION.md` —
  overwritten with M9.5 priority
  (operator UI extension).

## What SESSION_103 confirmed vs deferred

**Ready to consume at M9.5 UI:**

- Q7 rows callable per-buyer or
  ranked across all buyers.
- Combined with M9.3's Q3 / Q6 / Q8
  outputs, the operator dashboard has
  the full "true analytics" surface
  M8 could only proxy.

**Deferred:**

- `LeadVehicleInterest.stage_at_interest`
  annotation — requires through-model
  creation (its own increment /
  planning session).
- Frontend operator UI extension
  (M9.5).
- F&I / stips / chargebacks (M10).

## Push authorization state

- Working tree at session close: still
  dirty (bundling per M8 precedent).
  All M9.1 + M9.2 + M9.3 + M9.4 files
  uncommitted (plus this handoff + the
  start-next overwrite).
- `main` is up to date with
  `origin/main` (last pushed commit
  `4923997`).
- **The M9.1 + M9.2 + M9.3 + M9.4
  changes are UNCOMMITTED at handoff
  write time.** Coordinated M9 commit
  ships at M9.6 per the SESSION_101
  open decision.

## Fifteen M8 lessons applied at M9.4

- **Lesson 3 — pushback on planning
  gaps.** Substrate check at session
  open surfaced the
  `LeadVehicleInterest`-doesn't-exist
  gap that plan §1.3 assumed away.
  Rather than papering over with a
  scope-creep migration or a JSONField
  hack, this session paused, escalated
  the tradeoff to the user, and shipped
  only the Q7 half of M9.4 that the
  real substrate supports.
- **Lesson 4 — one authoritative
  read/write path.** Q7 verb is pure
  read; endpoint is thin translation.
  All variance math lives in
  `_BuyerAccum`.
- **Lesson 11 — additive extension
  over rewrite.** No existing verbs
  touched. `services/analytics/recon.py`
  gains a sibling verb alongside
  `vendor_performance`.
- **Lesson 13 — window-arg parity.**
  `buyer_estimate_accuracy` uses
  `window_days` (matches M8.3 +
  M8.4 + M9.3 aggregation-family
  convention).
- **Lesson 15 — verify claims via
  direct inspection.** SESSION_103
  opened with `grep LeadVehicleInterest`
  — the search found nothing in the
  models. This is the exact "verify
  handoff/planning claims via direct
  inspection" pattern M8 §6 lesson 15
  codifies.

## What SESSION_104 (M9.5) should do

Per `MILESTONE_9_PLANNING.md` §1.7 +
§7 M9.5:

1. **Read first:**
   `MILESTONE_9_PLANNING.md` §1.7 + §7
   M9.5; SESSION_098 handoff (M8.5
   operator UI — the fifth tab layers
   onto this page); this handoff;
   `frontend/src/pages/DealerAnalyticsPage.tsx`
   + `frontend/src/components/analytics/`
   + `frontend/src/lib/analyticsApi.ts`
   (all M8.5 shipped surfaces the
   fifth tab extends).
2. **Verify starting state:** M9.1 +
   M9.2 + M9.3 + M9.4 uncommitted
   (expected per bundle);
   `manage.py test dealer_ai` →
   **3,414 pass**; frontend Vitest
   19 pass; `check` + migrations
   clean.
3. **Draft (in order):**
   - Fifth `AnalyticsSection` tab
     **Realized Gross** wrapping the
     Q3 / Q6 / Q8 endpoints.
   - Optional Q7 buyer rank surface
     (may land as its own tab or as
     part of the Realized Gross tab
     — decide at implementation-time).
   - Sale + Delivery operator UI
     (Vehicle-detail sub-tab or
     dedicated page — plan §1.7
     leaves this as an
     implementation-time decision).
   - ~15 frontend Vitest + ~10
     backend endpoint-shape lock
     tests.
4. **Baseline projections:**
   - Backend 3,414 → **~3,424**
     (backend shape locks only).
   - Frontend Vitest 19 → **~34**.
5. **Ship handoff at
   `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`.**
6. **Overwrite `00-START-NEXT-SESSION.md`**
   with M9.6 priority (closeout).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 9
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_9_PLANNING.md` (with §0.a
   SESSION_100 + SESSION_101 + SESSION_102 +
   SESSION_103 amendments)
6. `docs/roadmap/MILESTONE_8_PLANNING.md` §1.8 (Q7 deferred spec now
   shipped at M9.4)
7. `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md` §6
   (fifteen lessons carry into M9)
8. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
9. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
10. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
11. `docs/CAPABILITY_MATRIX.md` §7i
12. Current source code — authoritative.

Planning docs are claims. Rules + research
+ code are facts.
