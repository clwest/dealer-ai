---
title: "SESSION_095 handoff — Milestone 8 · Increment 2 (M8.2 — vendor performance aggregation)"
status: historical
type: handoff
date: 2026-08-01
session: 095
milestone: 8
milestone_status: in_progress
increment: 2
increment_status: shipped
commit: 34352ed
---

# SESSION_095 — Milestone 8 · Increment 2 (M8.2 — vendor performance aggregation)

## What shipped

Vendor performance aggregation (Q2 + Q4) +
`views_analytics` extension + one new DRF endpoint +
24 focused tests. Q7 (`buyer_estimate_accuracy`)
**deferred** at session open per §0.a amendment.

**One `[IMPLEMENTATION-TIME-DECISION]` confirmed at
session open (Option A — defer Q7):**

- **Trigger.** `MILESTONE_8_PLANNING.md` §1.8
  assumes acquisition-buyer provenance
  (`buyer_user_id`) exists on the M2 ledger. It
  does not. `VehicleAcquisition.buyer_fees` is an
  auction-house buyer's-premium *fee* (Decimal),
  not a person. No FK to a buyer anywhere in
  M1–M7 schema.
- **Confirmed option A — defer.** Q7 re-enters as a
  standalone increment when acquisition-buyer
  provenance ships (its own planning + M2 additive
  extension session).
- **Rejected B** (add buyer FK + migration `0023`
  now) — violates M8.2 "no new models, no new
  migrations" scope bound.
- **Rejected C** (proxy on `VehicleCost.created_by`)
  — semantically wrong; violates PROJECT_RULES.md
  #3.

**M8.2 deliverables (five):**

1. **`MILESTONE_8_PLANNING.md` §0.a change-log
   entry.** New section documenting the
   SESSION_095 Q7-deferral amendment (option
   chosen + rejections + effect on §7 M8.2
   scope + Q7 re-entry path). §7 M8.2 scope
   line updated to reflect the reduced surface
   (~15 tests, ~3,192 → ~3,207 baseline
   projection).
2. **New `services/analytics/recon.py`** —
   `vendor_performance(dealership, *, window_start=None, window_end=None) -> list[VendorPerformanceRow]`.
   Row carries `vendor_slug` + `vendor_name` +
   `completed_count` + `mean_completion_days`
   (nullable, whole days, clock-skew-clamped) +
   `mean_variance_pct` (nullable Decimal, mean-
   absolute-percent quantized to 2dp) +
   `over_budget_count` (int). Filters:
   `status=completed AND venue=outsourced AND
   vendor IS NOT NULL`. Window on
   `completed_at.date()`. Sorted by
   `completed_count` desc, tiebreak on slug.
   Read-only. Aggregation runs in Python via a
   private `_VendorState` accumulator — keeps
   "when do we skip this WO?" branches readable
   without SQL `COALESCE` gymnastics.
3. **`services/analytics/__init__.py` extended** —
   re-exports `VendorPerformanceRow` +
   `vendor_performance`. Docstring notes Q7 is
   deferred (points at §0.a).
4. **`views_analytics.py` extended** — new
   `admin_analytics_vendor_performance` DRF
   endpoint. Composes the same
   `IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership`
   perms tuple as M8.1. Query args `window_start`
   / `window_end` (ISO date). Reuses the
   `_parse_iso_date_or_none` helper landed at M8.1.
   Response `{"rows": [...]}` with stringified
   Decimals; `mean_completion_days` /
   `mean_variance_pct` render as JSON `null` when
   the underlying WO subset produced no data.
5. **New URL** —
   `/api/dealer-ai/admin/analytics/vendor-performance/`
   named `admin-analytics-vendor-performance`.

**24 focused tests across 2 new files (target
was ~15, exceeded because the shape-level auth
check adds ~5 assertions on the endpoint):**

- `test_m8_analytics_vendor_performance_verb.py`
  (13 tests) — empty tenant, in-progress WO
  exclusion, in-house WO exclusion, mean-
  completion-days averaging, missing approved_at
  → nullable mean, clock-skew clamp to 0,
  variance % mean-absolute, variance
  exclusion cases (null / zero estimated / null
  actual), over-budget authorized-cap semantics,
  multi-vendor sort by count desc, tiebreak on
  slug, cross-tenant isolation, window bounds
  inclusive.
- `test_m8_analytics_vendor_performance_endpoint.py`
  (11 tests) — unauth, advisor forbidden, three
  allowed roles (recon_manager / sales_manager /
  dealer_owner), empty tenant, full response
  shape (all six fields), null-metrics render as
  JSON `null`, window_start query arg, malformed
  date → 400, cross-tenant.

## Verification

- **Backend tests:** **3,216 pass**, 1 skipped, 0
  fail (baseline 3,192 → 3,216 = **+24 tests**).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check
  --dry-run`:** "No changes detected" — M8.2 shipped
  zero migrations, matching the planning-doc scope
  bound.
- **Frontend `npx tsc --noEmit`:** clean (unchanged;
  no frontend at M8.2).
- **Frontend `npx vite build`:** clean.

## Compatibility with M1-M8.1

- **M1 (auth):** none touched. Endpoint composes the
  same permissions class as M8.1.
- **M2 (ledger):** none touched.
- **M3 (condition reports):** none touched.
- **M4 (recon):** read-only. Aggregation reads
  `WorkOrder` filtered to completed + outsourced +
  vendor-non-null.
- **M5 (lifecycle):** none touched.
- **M6 (photo / listing):** none touched.
- **M7 (async):** none touched.
- **M8.1 (analytics infra):** additive extension
  only. The `services/analytics/` package facade +
  `views_analytics.py` module + URL prefix are
  reused verbatim; nothing about M8.2 required
  changes to M8.1 shape.

## Frontend

None. M8.2 is backend-only per planning §7 M8.2 +
§5.c (recharts deferred to M8.5).

## Coordinated commit + push

Deferred to M8.6 closeout per the SESSION_087 /
SESSION_093 / SESSION_094 precedent.

## What's next — SESSION_096 (M8.3)

**Aging + SLA-breach pattern aggregations** (Q5 +
Q9 + Q10) per `MILESTONE_8_PLANNING.md` §7 M8.3:

- `services/analytics/lifecycle_aging.py::stage_aging_trend(dealership, stage, *, window_days=30)`
  — reads M7.3 `StageAgingSnapshot`. Returns
  time-series (snapshot_at, p50, p90,
  vehicle_count).
- `services/analytics/sla_breaches.py::breach_patterns(dealership, *, window_days=30)`
  — reads M8.1 `SlaBreachRecord` (the M7.4 log
  substrate that M8.1 materialized). Report
  carries top-N vendors by breach count, top-N
  breach kinds, average breach_days.
- Two new DRF endpoints under the M8.1 URL prefix.
- ~25 focused tests. Baseline **3,216 → ~3,241**.

No new models, no new migrations at M8.3 — both
verbs read M7.3 + M8.1 substrate.

Read-first list at SESSION_096 open:

- `docs/roadmap/MILESTONE_8_PLANNING.md` §1.4 +
  §1.5 + §7 M8.3.
- `docs/handoffs/SESSION_095_m8_inc2_vendor_performance.md`
  (this handoff).
- `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`
  (for the M8.1 pattern that M8.3 mirrors).
- `backend/dealer_ai/services/analytics/recon.py`
  (M8.2 pattern M8.3 mirrors).
- `backend/dealer_ai/models.py::StageAgingSnapshot`
  (M7.3 substrate M8.3 reads).
- `backend/dealer_ai/models.py::SlaBreachRecord`
  (M8.1 substrate M8.3 reads).
- `backend/dealer_ai/services/lifecycle_aging/snapshots.py`
  (M7.3 verb whose output M8.3 aggregates).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_8_PLANNING.md` (with
   §0.a SESSION_095 amendment)
6. `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_095_m8_inc2_vendor_performance.md`
   (this handoff)
8. `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`
9. `docs/handoffs/SESSION_093_m7_closeout.md`
10. `docs/handoffs/SESSION_092_m7_inc5_photo_reaper.md`
11. `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
12. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
13. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
14. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
15. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
16. `docs/research/RECON_MAPPING.md` §"To Ownership"

Planning docs are claims. Rules + research + code
are facts.
