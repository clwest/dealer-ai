---
title: "SESSION_094 handoff — Milestone 8 · Increment 1 (M8.1 — analytics infra + first aggregation)"
status: historical
type: handoff
date: 2026-08-01
session: 094
milestone: 8
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: <pending-user-authorization>
---

# SESSION_094 — Milestone 8 · Increment 1 (M8.1 — analytics infra + first aggregation)

## What shipped

Analytics infrastructure + Q1 aggregation
(`recon_cost_per_source`) + SLA-breach
materialization substrate + M7.4 verb extension +
one first-DRF-endpoint + 42 focused tests. All four
`[NEEDS-DECISION-BEFORE-M8.1]` items from
`MILESTONE_8_PLANNING.md` §9 confirmed at session
open (all four as-recommended).

**Load-bearing decisions confirmed at session open:**

1. **§5.a — Compute strategy:** Option C (hybrid) —
   compute-on-request for v1, materialize when
   operator evidence surfaces latency pain.
2. **§5.b — SLA-breach data source:** Option B —
   `SlaBreachRecord` model + migration `0022` + M7.4
   verb extension.
3. **§5.c — Chart library:** Option A (recharts) —
   deferred to M8.5 (no frontend at M8.1).
4. **§5.d — Increment count:** Option A — five
   aggregation increments + one closeout.

**M8.1 deliverables (six):**

1. **New `SlaBreachRecord` model + migration `0022`**
   — fields per plan (`dealership` FK CASCADE,
   `work_order` FK CASCADE, `kind` from breach-kind
   vocabulary, `breach_days`, `detected_at`
   DateTimeField indexed, `detected_at_date`
   DateField for uniqueness, `vehicle_stock`,
   `vendor_name`). Composite index
   `(dealership, kind, -detected_at)`
   (`sbr_tenant_kind_time_idx`). Unique constraint on
   `(work_order, kind, detected_at_date)`
   (`sbr_wo_kind_date_uq`) — anchors the M7.4 daily-
   scan idempotency at the DB level.
2. **Tenancy-carrier extension 21 → 22.**
   `_TENANT_CARRIER_MODEL_NAMES` extended with
   `"SlaBreachRecord"`. No parent-tenant relation
   (unlike VehiclePhoto ⇐ Vehicle) — the M7.4 verb-
   extension writes `dealership` explicitly; the
   autofill signal is a safety net only.
3. **M7.4 verb extension** —
   `detect_sla_breaches` now writes an
   `SlaBreachRecord` per detected breach in addition
   to the `logging.WARNING` record. `get_or_create`
   on `(work_order, kind, detected_at_date=as_of)`
   makes same-day re-runs no-op — DB unique
   constraint + verb-level idempotency both hold.
   Log warning contract preserved verbatim (tests
   assert both persist).
4. **New `services/analytics/` package** —
   `__init__.py` facade re-exporting the aggregation
   verbs + `acquisition.py::recon_cost_per_source`
   (Q1). Reads M2 `VehicleAcquisition.source` + M2
   `VehicleCost` filtered to `RECON_CATEGORIES`
   (excludes flooring / admin / photography) +
   `is_estimate=False` (committed spend only).
   Returns list of `SourcePerformanceRow` frozen
   dataclasses (source key + display + vehicle_count +
   total_recon_cost + mean_recon_cost quantized to 2dp).
   Sorted by total desc, deterministic tiebreak on
   source key. Cross-tenant strict; window filter
   inclusive.
5. **New `views_analytics.py` + first URL** —
   `admin_analytics_recon_cost_per_source` DRF
   endpoint at
   `/api/dealer-ai/admin/analytics/recon-cost-per-source/`.
   Composes
   `IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership`
   per §1.9. Query args `window_start` /
   `window_end` (ISO date). Malformed dates → 400.
   Response `{"rows": [...]}` with stringified
   Decimals.
6. **42 focused tests across 4 new files**
   (target ~30 exceeded because the auth-matrix
   coverage naturally lands more assertions):
   - `test_m8_sla_breach_record_model.py` (8 tests)
     — shape, ordering, uniqueness constraint, kind
     bypass, date bypass, tenancy-carrier ≥22.
   - `test_m8_vendor_sla_persistence.py` (8 tests)
     — in_progress + approved_stale breach
     persistence, idempotency, different-day, cross-
     tenant, log preservation, empty tenant, no-
     breach.
   - `test_m8_analytics_recon_cost_per_source_verb.py`
     (10 tests) — empty tenant, no-acquisition
     skip, category exclusions, estimate exclusion,
     reversal-row subtraction, multi-vehicle
     aggregation, multi-source sort, cross-tenant,
     window bounds, mean quantization.
   - `test_m8_analytics_endpoint.py` (16 tests) —
     unauth, no-membership, four disallowed roles
     (advisor / porter / f_and_i_manager / collections),
     three allowed roles (recon_manager /
     sales_manager / dealer_owner), empty tenant,
     response shape, window_start / window_end
     query args, malformed date → 400 (×2), cross-
     tenant, sort order.

**One test-relaxation fix (M7 §6 lesson 14 codified):**
`test_m7_stage_aging_model.py::TenantCarrierExtension::test_carrier_count_is_twenty_one`
asserted `len == 21` at M7.3 shipping time. M8.1's
extension to 22 exposed the pattern retrospective §6
lesson 14 predicted. Renamed to
`test_carrier_count_at_least_twenty_one`, switched
`assertEqual` → `assertGreaterEqual`, updated the
docstring to name the pattern. Future milestone
extensions to 23+ won't need to re-edit this test.

## Verification

- **Backend tests:** **3,192 pass**, 1 skipped, 0
  fail (baseline 3,150 → 3,192 = **+42 tests**).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check
  --dry-run`:** "No changes detected."
- **Frontend `npx tsc --noEmit`:** clean (unchanged;
  no frontend at M8.1).
- **Frontend `npx vite build`:** clean (bundle
  618.74 kB / 164.27 kB gzip — chunk-size warning
  pre-existing, not M8.1-attributable).

## Compatibility with M1-M7

- **M1 (auth):** none touched. Endpoint composes
  existing `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  from `permissions.py`.
- **M2 (ledger):** read-only. Analytics verb reads
  `VehicleAcquisition.source` + `VehicleCost`
  filtered to `RECON_CATEGORIES`; the M2 category-
  partition constants are the source of truth.
- **M3 (condition reports):** none touched.
- **M4 (recon):** read-only for aggregation.
  `WorkOrder` FK'd by the new `SlaBreachRecord`
  model as a CASCADE parent — WO deletion (rare;
  the M4 model has no public DELETE surface)
  cascades to breach rows.
- **M5 (lifecycle):** none touched.
- **M6 (photo / listing):** none touched.
- **M7 (async):** additive extension only.
  `services/vendor_sla/detection.py::detect_sla_breaches`
  gained a persistence side effect but the return
  shape (`SlaBreachReport`) is unchanged; every
  existing M7.4 test still passes. `JobRunLog` row
  cadence is unchanged (the wrapping
  `@instrumented_task` decorator still writes one
  row per invocation).

## Frontend

None. M8.1 is backend-only per planning §7 M8.1 +
§5.c (recharts deferred to M8.5). `useBrand()` and
the operator sidebar are untouched.

## Coordinated commit + push

**Deferred to M8.6 closeout** per the standing user
directive (M6 close SESSION_087 + M7 close
SESSION_093 precedent). M8.1's diff will land as one
commit inside the coordinated M8 close push once
M8.2-M8.6 finish. Individual per-increment
authorization is not required; the increment ships
here in-repo and the M8-close push consolidates.

The `commit:` field above will be updated with the
actual hash when the M8-close commit is prepared.

## What's next — SESSION_095 (M8.2)

**Vendor + buyer performance aggregations** (Q2 + Q4
+ Q7) per `MILESTONE_8_PLANNING.md` §7 M8.2:

- `services/analytics/recon.py::vendor_performance`
  — vendor name, completed count, mean days
  (approved → completed), estimated-vs-actual cost
  variance %, over-budget count.
- `services/analytics/recon.py::buyer_estimate_accuracy`
  — buyer name, WO count, mean absolute variance %,
  +/- bias.
- Two new DRF endpoints under the M8.1 URL prefix.
- ~25 focused tests. Baseline **~3,192 → ~3,217**.

No new models, no new migrations at M8.2 (verbs
read M4 `WorkOrder` + M2 `VehicleCost` +
acquisition-buyer provenance from the M2 ledger).
`AnalyticsCache` model still deferred per §5.a
Option C hybrid.

Read-first list at SESSION_095 open:

- `docs/roadmap/MILESTONE_8_PLANNING.md` §1.3 +
  §1.8 + §7 M8.2.
- `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`
  (this handoff).
- `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md` §6
  (14 lessons — carry into M8; lesson 14 already
  codified into M8.1 test-relaxation posture).
- `backend/dealer_ai/services/analytics/acquisition.py`
  (M8.1 substrate M8.2 mirrors).
- `backend/dealer_ai/views_analytics.py` (M8.1
  endpoint pattern M8.2 mirrors).
- `backend/dealer_ai/models.py::WorkOrder` (the
  substrate M8.2 aggregates).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_8_PLANNING.md`
6. `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`
   (this handoff)
8. `docs/handoffs/SESSION_093_m7_closeout.md`
9. `docs/handoffs/SESSION_092_m7_inc5_photo_reaper.md`
10. `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
11. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
12. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
13. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
14. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
15. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §"To Ownership"

Planning docs are claims. Rules + research + code
are facts.
