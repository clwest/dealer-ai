---
title: "SESSION_097 handoff — Milestone 8 · Increment 4 (M8.4 — vehicle-type + frontline proxies)"
status: historical
type: handoff
date: 2026-08-01
session: 097
milestone: 8
milestone_status: in_progress
increment: 4
increment_status: shipped
commit: 34352ed
---

# SESSION_097 — Milestone 8 · Increment 4 (M8.4 — vehicle-type recon cost + days-at-frontline proxy)

## What shipped

Two read-only proxy aggregations rooted in M2
`Vehicle` + `VehicleCost` and M7.3
`StageAgingSnapshot` + two new DRF endpoints + 27
focused tests. No new models, no new migrations, no
schema changes. Planning-doc §0.a amended with two
new entries.

**One `[IMPLEMENTATION-TIME-DECISION]` confirmed at
session open (Option A — Q3 proxy):**

- **Trigger.** §1.2 spec'd Q3 as "which vehicle
  types produce the highest **profit**?" — true
  profit requires M9 Sale substrate. Same class of
  gap as Q7's buyer-provenance at M8.2.
- **Confirmed A — ship a proxy.** New verb
  `vehicle_type_recon_cost(dealership, *,
  window_start=None, window_end=None)`. Row
  discriminator `(make, model)`; row shape mirrors
  M8.1 Q1 (`SourcePerformanceRow`) — one row per
  type with `vehicle_count` + `total_recon_cost`
  + `mean_recon_cost` (2dp quantized). Naming is
  deliberate — the verb name says what it
  actually computes ("recon cost per type"), not
  the aspirational "profitability."
- **Rejected B** (defer Q3 to M9) — leaves M8.4
  unbalanced with one aggregation only.
- **Rejected C** (broader "total cost per type"
  summing recon + acquisition + admin) — mixes
  dealer-controlled recon signal with
  market-driven acquisition signal.

**Two `MILESTONE_8_PLANNING.md` §0.a amendments
landed (both at session open):**

1. **Q1 scope reallocation.** §7 M8.4 originally
   listed "Q1 + Q3 + Q8." Q1 already shipped at
   M8.1 as the analytics substrate proof-of-concept
   (see SESSION_094 handoff). Revised M8.4 scope:
   **Q3 + Q8 only.**
2. **Q3 substrate gap → ship proxy.** As above.

**M8.4 deliverables (six):**

1. **`services/analytics/acquisition.py` extended**
   — new `vehicle_type_recon_cost` verb + new
   `VehicleTypeReconCostRow` dataclass. Reads M2
   `VehicleCost` (RECON_CATEGORIES only,
   is_estimate=False) grouped by `Vehicle.model` +
   `Vehicle.make`. Window filter on
   `incurred_at.date()`. Sort by
   `total_recon_cost` desc, tiebreak on
   `(make, model)` asc. Module docstring updated
   to describe both Q1 (M8.1) and Q3 (M8.4).
2. **`services/analytics/lifecycle_aging.py`
   extended** — new `days_at_frontline_proxy`
   verb + new `DaysAtFrontlineReport` dataclass.
   Reads M7.3 `StageAgingSnapshot` filtered to
   `stage='frontline'` + window. Returns
   snapshot_count, mean_p50_days, mean_p90_days
   (both 2dp Decimal), latest_vehicle_count,
   latest_snapshot_at. Empty window → every
   derived field `None` (distinct from "average
   is zero"). Module docstring updated.
3. **`services/analytics/__init__.py` extended** —
   re-exports the two new verbs +
   `VehicleTypeReconCostRow` +
   `DaysAtFrontlineReport`. Docstring notes Q6
   deferred to M9 alongside the existing Q7
   deferral pointer.
4. **`views_analytics.py` extended** — two new
   endpoints + two new projection helpers.
   - **`admin_analytics_vehicle_type_recon_cost`**
     at
     `/api/dealer-ai/admin/analytics/vehicle-type-recon-cost/`.
     Query args mirror M8.1 Q1 (window_start /
     window_end ISO dates, malformed → 400).
     Response `{"rows": [...]}` with stringified
     Decimals.
   - **`admin_analytics_days_at_frontline_proxy`**
     at
     `/api/dealer-ai/admin/analytics/days-at-frontline-proxy/`.
     Query arg `window_days` (positive int,
     default 30). Response
     `{"window_days": int, "report": {...}}` with
     JSON `null` for every empty-window field.
5. **Two new URLs** — `vehicle-type-recon-cost/` +
   `days-at-frontline-proxy/`.
6. **27 focused tests across 4 new files (target
   was ~20 — exceeded because the shape-level
   auth plus per-verb behavior coverage
   naturally lands more):**
   - `test_m8_analytics_vehicle_type_recon_cost_verb.py`
     (8 tests) — empty tenant, category
     exclusions, estimate exclusion, reversal
     subtraction, multi-vehicle aggregation,
     multi-type sort + (make, model) tiebreak,
     cross-tenant, window bounds.
   - `test_m8_analytics_days_at_frontline_proxy_verb.py`
     (6 tests) — empty window null-fields,
     stage isolation, mean across window, latest
     fields, window exclusion, cross-tenant.
   - `test_m8_analytics_vehicle_type_recon_cost_endpoint.py`
     (6 tests) — unauth, advisor forbidden,
     recon manager allowed, empty tenant rows,
     response row shape, cross-tenant.
   - `test_m8_analytics_days_at_frontline_proxy_endpoint.py`
     (7 tests) — unauth, advisor forbidden,
     recon manager allowed, empty window null
     fields, response report shape, window_days
     applied, malformed window_days → 400.

## Verification

- **Backend tests:** **3,274 pass**, 1 skipped, 0
  fail (baseline 3,247 → 3,274 = **+27 tests**).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check
  --dry-run`:** "No changes detected" — matches
  the planning-doc scope bound.
- **Frontend `npx tsc --noEmit`:** clean
  (unchanged; no frontend at M8.4).
- **Frontend `npx vite build`:** clean.

## Compatibility with M1-M8.3

- **M1 (auth):** none touched. Same permission
  class as M8.1/M8.2/M8.3.
- **M2 (ledger):** read-only. Q3 verb reads
  `Vehicle` + `VehicleCost` filtered to
  `RECON_CATEGORIES + is_estimate=False`.
- **M3-M6:** none touched.
- **M7 (async):** none touched. Q8 verb reads
  M7.3 `StageAgingSnapshot` via `.values()`.
- **M8.1-M8.3 (analytics infra + prior
  aggregations):** additive extension only. Both
  M8.4 verbs land in existing modules
  (`acquisition.py` for Q3 alongside Q1;
  `lifecycle_aging.py` for Q8 alongside Q5+Q9).

## Frontend

None. M8.4 is backend-only per planning §7 M8.4
+ §5.c (recharts deferred to M8.5).

## Coordinated commit + push

Deferred to M8.6 closeout.

## What's next — SESSION_098 (M8.5)

**Operator UI + recharts** per
`MILESTONE_8_PLANNING.md` §7 M8.5. **First frontend
work since M6.** All aggregation substrate (Q1 +
Q2 + Q4 + Q5 + Q9 + Q10 + Q3 proxy + Q8 proxy) is
shipped and callable — M8.5 wires the dashboard.

- **New route** `/dealer-ai-analytics/` with N tabs
  (one per aggregation). N candidates: 7 shipped
  aggregations grouped into ~3-4 dashboard views
  (Recon spend / Vendor performance / Aging & SLA
  / Vehicle types). **Grouping is an implementation-
  time decision** to surface at session open.
- **recharts** dependency added per §5.c Option A
  (user-confirmed at SESSION_094 open).
- Role-gated on frontend as UX convenience;
  server-side is authoritative.
- ~15 frontend tests + ~10 backend endpoint-shape
  tests (endpoint shape already fully locked at
  M8.1-M8.4, so the ~10 backend delta is likely a
  new "GET the dashboard payload" wrapper endpoint
  if one lands, or coverage of any missing corner
  cases — decide at session open).
- Baseline **3,274 → ~3,300** on the backend side.
  Frontend test count is a new baseline (Vitest
  suite grows).

Read-first list at SESSION_098 open:

- `docs/roadmap/MILESTONE_8_PLANNING.md` §1.9 +
  §1.10 + §7 M8.5.
- `docs/handoffs/SESSION_097_m8_inc4_acquisition_frontline_proxies.md`
  (this handoff).
- **All M8.1–M8.4 handoffs** for the endpoint
  surface: SESSION_094 (Q1 endpoint),
  SESSION_095 (Q2+Q4), SESSION_096 (Q5+Q9+Q10),
  this handoff (Q3+Q8).
- `backend/dealer_ai/views_analytics.py` — the
  full endpoint surface M8.5 consumes.
- `frontend/src/` — the pre-M6 frontend shape
  (Tailwind v3 + shadcn/ui bridge; radix-nova
  preset). See CLAUDE.md "Frontend stack notes"
  section for the v3/v4 bridge caveats.
- `frontend/package.json` — for the recharts
  install target.

**Implementation-time decisions to surface at
SESSION_098 open:**

1. **Dashboard grouping** — 7 shipped
   aggregations into how many tabs? Recommend
   ~3-4: (a) Acquisition & Recon Cost (Q1 + Q3),
   (b) Vendor Performance (Q2 + Q4), (c)
   Lifecycle Aging (Q5 + Q8 + Q9), (d) SLA
   Breach Patterns (Q10).
2. **Server-side aggregator endpoint?** — should
   M8.5 add a single `GET /admin/analytics/dashboard/`
   endpoint that returns all rollups in one
   request (reduces frontend request-storm), or
   let the frontend fetch per-tab? Recommend
   per-tab (matches current endpoint surface;
   `React.useQuery` per tab; keeps the server
   simple).
3. **Frontend test framework** — Vitest is
   already installed (M6 tests use it). Confirm
   no new framework dependency.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_8_PLANNING.md` (with
   §0.a SESSION_095 + SESSION_097 amendments)
6. `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_097_m8_inc4_acquisition_frontline_proxies.md`
   (this handoff)
8. `docs/handoffs/SESSION_096_m8_inc3_aging_sla_patterns.md`
9. `docs/handoffs/SESSION_095_m8_inc2_vendor_performance.md`
10. `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`
11. `docs/handoffs/SESSION_093_m7_closeout.md`
12. `docs/handoffs/SESSION_092_m7_inc5_photo_reaper.md`
13. `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
14. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
15. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
16. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
17. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
18. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §"To Ownership"
19. `docs/research/RECON_MAPPING.md` §"To Ownership"

Planning docs are claims. Rules + research + code
are facts.
