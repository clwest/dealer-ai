---
title: "SESSION_102 handoff — Milestone 9 · Increment 3 (M9.3 — analytics extensions)"
status: historical
type: handoff
date: 2026-08-02
session: 102
milestone: 9
milestone_status: in_progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_102 — Milestone 9 · Increment 3 (M9.3 — Q3 + Q6 + Q8 analytics extensions)

## What shipped

Three read-only aggregation verbs unlocking
the three M8 deferrals (Q3 true, Q6 gross-
profit trend, Q8 true inventory turn) + three
DRF endpoints + smoke tests locking the M8.4
proxy shapes. No new user decisions required
at session open — plan §1.5 was fully
specified at planning-time close.

**M9.3 deliverables (six):**

1. **Q3 —
   `services.analytics.acquisition::vehicle_type_profitability`**
   (new sibling of M8.4
   `vehicle_type_recon_cost`). Groups by
   `(Vehicle.make, Vehicle.model)`. Row
   shape: `sold_count`, `total_sale_gross`,
   `total_sold_price`, `mean_gross_pct`
   (mean of per-vehicle margin %,
   equal-weighted). Reads M9.1
   `Sale.gross_realized` denormalized
   column — no per-row ledger
   recomputation.
2. **Q6 — new
   `services/analytics/gross_profit.py`
   module + `gross_profit_trend` verb**.
   Daily-bucket time series over
   `Sale.sale_date` + `Sale.gross_realized`.
   Sparse series (dates with zero sales
   omitted). Returns `list[GrossProfitPoint]`.
3. **Q8 —
   `services.analytics.lifecycle_aging::inventory_turn`**
   (new sibling of M8.4
   `days_at_frontline_proxy`). Reads
   `VehicleStageEvent` (earliest frontline
   entry per vehicle) + `Sale.sale_date`.
   Computes per-vehicle days-to-sale and
   returns `InventoryTurnReport` summary
   (sold_count, mean, p50, p90, min, max).
   Nearest-rank percentile method.
4. **Three DRF endpoints under
   `/api/dealer-ai/admin/analytics/`:**
   - `vehicle-type-profitability/` (GET,
     window_start + window_end args).
   - `gross-profit-trend/` (GET,
     window_days arg, default 90).
   - `inventory-turn/` (GET, window_days
     arg, default 90).
   - All role-gated on
     `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
     per M8 pattern.
5. **Analytics facade re-export** —
   `services/analytics/__init__.py`
   extended with three new verbs + three
   new dataclasses.
6. **32 focused tests** in single file
   `test_m9_analytics_extensions.py`:
   - Q3 verb (6): empty / groups by type
     / sort order / mean-pct semantics /
     window filter / cross-tenant.
   - Q6 verb (5): empty / date buckets /
     ordering / window-days filter /
     cross-tenant.
   - Q8 verb (7): empty / single vehicle
     / multi-vehicle percentiles / skips
     no-frontline vehicles / earliest-entry
     rule / window-days filter / cross-
     tenant.
   - Endpoint auth matrix (3): unauth /
     advisor / dealer_owner.
   - Endpoint behavior (7): response
     shapes × 3 + empty IT / three
     malformed-arg 400s.
   - Cross-tenant endpoint (2): VTP + IT.
   - M8.4 proxy smoke (2):
     `vehicle_type_recon_cost` shape +
     `days_at_frontline_proxy` shape
     unchanged after M9.3.

**Implementation-time notes** (recorded
in `MILESTONE_9_PLANNING.md` §0.a):

- **Q3 row shape** — Sale-centric fields
  chosen over literally extending M8.4's
  `VehicleTypeReconCostRow`. The two
  verbs answer different operational
  questions (prep cost vs profit); a
  merged row would conflate aggregation
  universes.
- **`mean_gross_pct` semantics** — mean
  of per-vehicle margin percentages,
  equal-weighted. Callers wanting
  revenue-weighted margin compute
  `total_sale_gross / total_sold_price`
  from the row.
- **Q8 reference-point** — earliest
  frontline event (not latest re-entry).
  Bounced-back vehicles keep the
  original clock.
- **`gross_profit_trend` quantize** —
  Django's `Sum` returns unquantized
  Decimal for single-row aggregations
  (e.g. `Decimal("2000")`). Added
  explicit `.quantize(Decimal("0.01"))`
  in the verb so the JSON wire shape
  matches M8 sibling projections
  (`"2000.00"`).
- **Test-only frontline bootstrap
  awareness** —
  `dealer_ai/tests/__init__.py` auto-
  creates a frontline VehicleStageEvent
  on every Vehicle save. M9.3's
  `test_skips_sold_vehicles_without_frontline_event`
  deletes the bootstrap event post-
  seed to actually simulate the
  data-quality gap the verb docstring
  describes.

## Test baseline

- **Backend:** 3,362 → **3,394 pass**, 1
  skipped, 0 fail (+32 M9.3 tests exactly).
- **Frontend Vitest:** unchanged at 19
  pass (no frontend at M9.3 per plan
  non-goals).
- **`manage.py check`:** clean.
- **`manage.py makemigrations --check
  --dry-run`:** "No changes detected"
  (no schema changes at M9.3).

## Migrations

`0001` – **`0024`** (unchanged from M9.2 —
M9.3 is verb + endpoint only, no schema).

## Files touched (M9.3 scope)

**Backend (added):**

- `backend/dealer_ai/services/analytics/gross_profit.py`
  (~130 lines — new module + Q6 verb).
- `backend/dealer_ai/tests/test_m9_analytics_extensions.py`
  (~580 lines, 32 tests).

**Backend (modified):**

- `backend/dealer_ai/services/analytics/acquisition.py`
  — added `VehicleTypeProfitabilityRow`
  dataclass + `vehicle_type_profitability`
  verb below M8.4 proxy (per M8 §6 lesson
  11 additive extension).
- `backend/dealer_ai/services/analytics/lifecycle_aging.py`
  — added `InventoryTurnReport`
  dataclass + `_percentile` helper +
  `inventory_turn` verb below M8.4 proxy.
- `backend/dealer_ai/services/analytics/__init__.py`
  — facade extended with three new
  imports + `__all__` extended.
- `backend/dealer_ai/views_analytics.py`
  — three new projection helpers + three
  new endpoint handlers + docstring
  updates.
- `backend/dealer_ai/urls.py` — three new
  route registrations under
  `admin/analytics/`.

**Docs (modified):**

- `docs/roadmap/MILESTONE_9_PLANNING.md`
  §0.a — SESSION_102 amendment recording
  implementation-time notes (Q3 row shape,
  mean_pct semantics, earliest-frontline
  reference, quantize fix, test-only
  signal awareness).
- `00-START-NEXT-SESSION.md` — overwritten
  with M9.4 priority (Q7 buyer estimate +
  LeadVehicleInterest annotation).

## What SESSION_102 confirmed vs deferred

**Ready to consume at M9.5 UI:**

- Q3 true profitability rows.
- Q6 daily gross-profit series.
- Q8 true inventory-turn summary.
- Both M8.4 proxy verbs remain callable
  (per M8 §6 lesson 11) — the M8.5
  operator UI's existing tabs continue to
  render M8.4 data unchanged.

**Deferred to M9.4+ per plan §7
non-goals:**

- Q7 `buyer_estimate_accuracy` verb +
  endpoint (M9.4) — substrate landed at
  M9.1 (`VehicleAcquisition.buyer` FK
  nullable).
- `LeadVehicleInterest.stage_at_interest`
  extension (M9.4).
- Frontend operator UI extension (M9.5).
- F&I / stips / chargebacks (M10).

## Push authorization state

- Working tree at session close: still
  dirty (bundling per M8 precedent).
  Twelve M9.1 files + eight M9.2 files +
  seven M9.3 files uncommitted (plus this
  handoff + the start-next overwrite).
- `main` is up to date with
  `origin/main` (last pushed commit
  `4923997`).
- **The M9.1 + M9.2 + M9.3 changes are
  UNCOMMITTED at handoff write time.**
  Coordinated M9 commit ships at M9.6
  per the SESSION_101 open decision.

## Fifteen M8 lessons applied at M9.3

- **Lesson 4 — one authoritative
  read/write path.** Each verb owns one
  question; the M8.4 proxies stay valid
  callers of their existing question
  ("what did we spend?"), the M9.3 verbs
  own the true question ("what did we
  earn?"). No verb overloading.
- **Lesson 8 — pure verbs that never
  mutate.** All three M9.3 verbs are pure
  reads. `vehicle_type_profitability`
  reads `Sale.gross_realized`
  denormalized column instead of
  recomputing via
  `services.sale.gross_realized` — the
  M9.1 denormalization decision
  specifically enabled single-query
  aggregation.
- **Lesson 11 — additive extension over
  rewrite.** M8.4 proxy verbs
  (`vehicle_type_recon_cost`,
  `days_at_frontline_proxy`) still
  ship at M9.3 with identical shapes.
  Two smoke tests
  (`M84ProxyStillWorksAfterM93Tests`)
  lock this contract.
- **Lesson 13 — window-arg parity across
  siblings.** Q3 uses
  `window_start`/`window_end` (matches
  M8.1/M8.2/M8.4 date-window verbs);
  Q6 + Q8 use `window_days` (matches
  M8.3 `stage_aging_trend` + M8.4
  `days_at_frontline_proxy`). Chose
  parity with the aggregation shape
  each verb most closely resembles.
- **Lesson 15 — verify claims via
  direct inspection.** SESSION_102
  opened with a re-read of
  `SESSION_101_m9_inc2_delivery.md` +
  `git status` to confirm M9.1+M9.2
  uncommitted per bundle strategy.

## What SESSION_103 (M9.4) should do

Per `MILESTONE_9_PLANNING.md` §7 M9.4:

1. **Read first:**
   `MILESTONE_9_PLANNING.md` §1.3
   (LeadVehicleInterest annotation) +
   §1.5 Q7 spec + §7 M9.4;
   `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
   (previous session);
   `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
   (M9.1 shipped the `VehicleAcquisition.buyer`
   FK substrate Q7 reads);
   `models.py::VehicleAcquisition` (buyer
   FK ships at M9.1 nullable);
   `models.py::LeadVehicleInterest`
   (through-model between CustomerLead +
   Vehicle — receives `stage_at_interest`);
   `services/analytics/recon.py` (Q7's
   sibling module — Q2 + Q4 already
   there).
2. **Verify starting state:** M9.1 + M9.2
   + M9.3 uncommitted (expected per
   bundle); `manage.py test dealer_ai`
   → **3,394 pass**; `check` +
   migrations clean.
3. **Confirm one open item at session
   open** (if any): whether
   `stage_at_interest` should backfill
   for existing rows or only populate
   forward from M9.4 close. Planning
   §1.3 has this as an implementation-
   time choice; recommend forward-only
   (aligns with the M2 buyer-FK NULL-
   for-historical pattern the M9.1
   handoff established).
4. **Draft (in order):**
   - New verb
     `services/analytics/recon.py::buyer_estimate_accuracy(dealership,
     buyer_user_id, *, window_days=90)
     -> BuyerAccuracyRow` per M8
     planning §1.8 (deferred spec).
   - New DRF endpoint under
     `admin/analytics/buyer-estimate-accuracy/`.
   - `LeadVehicleInterest.stage_at_interest`
     field addition + migration `0025`.
     Populated by the M3-M5 write path
     via denormalization at
     interest-write time.
   - ~20 focused tests.
5. **Baseline projection:** 3,394 →
   **~3,414**.
6. **Ship handoff at
   `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy_and_annotation.md`.**

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 9
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_9_PLANNING.md` (with §0.a
   SESSION_100 + SESSION_101 + SESSION_102 amendments)
6. `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md` §6
   (fifteen lessons carry into M9)
7. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
8. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
9. `docs/handoffs/SESSION_099_m8_closeout.md`
10. `docs/handoffs/SESSION_097_m8_inc4_acquisition_frontline_proxies.md`
11. `docs/CAPABILITY_MATRIX.md` §7i
12. `docs/research/VEHICLE_CENTRIC_PIVOT.md` §Phase 8
13. Current source code — authoritative.

Planning docs are claims. Rules + research
+ code are facts.
