---
title: "Milestone 8 — Implementation-Planning Pass"
status: shipped
shipped_at_session: SESSION_099
type: planning-artifact
generated: 2026-08-01
generated_at_session: SESSION_093 (post-M7-closeout)
milestone: 8
milestone_name: "Operational intelligence"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_7_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_7_PLANNING.md
  - docs/roadmap/MILESTONE_6_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/RECON_MAPPING.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
---

# Milestone 8 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 8
(Operational intelligence). Every implementation
increment cites back here for scope, invariants, and
refinement provenance. Mirrors the shape M3 / M4 / M5 /
M6 / M7 planning docs proved out.

**Business objective (from `IMPLEMENTATION_ROADMAP.md`
§Milestone 8).** Answer the questions the research
corpus explicitly names: which auctions produce the
highest recon costs, which vendors finish fastest,
which vehicle types produce the highest profit, which
repairs are consistently underestimated, aging trends
per stage, gross-profit trends, buyer estimate accuracy
over time.

**VCP mandate.** *"No ML required. These are SQL
aggregations."* — M8 is the aggregation + surfacing
layer over M2-M7 substrate.

**Zero implementation this session.** Planning artifact
only. SESSION_094 opens M8.1.

---

## 0.a Change log (implementation-time amendments)

Per M5/M6/M7 §9 mandates, load-bearing planning
decisions may need narrow amendment at
implementation time as substrate reality asserts
itself. Every amendment records the session,
option, and the affected sections.

### SESSION_097 (M8.4 open) — Q1 already shipped; Q3 → proxy

- **Amendment 1 — Q1 scope reallocation.** §7 M8.4
  originally listed "Q1 + Q3 + Q8." **Q1
  (`recon_cost_per_source`) already shipped at
  M8.1** as the analytics substrate proof-of-
  concept (see SESSION_094 handoff). Revised M8.4
  scope: **Q3 + Q8 only.**
- **Trigger.** M8.1 needed a first aggregation to
  land alongside the `services/analytics/` package
  + first endpoint. Q1 was the simplest fit
  (single-table aggregate over M2 substrate). The
  planning doc's original §7 sequencing (Q1 at
  M8.4) predated that decision.
- **Effect on §7 M8.4 scope.** Test target: ~25 →
  **~20**. Baseline projection: 3,247 → **~3,267**.
- **Amendment 2 — Q3 substrate gap → ship proxy.**
  §1.2 spec'd Q3 as "which vehicle types produce
  the highest **profit**?" — true profit requires
  sale-side data (M9 substrate not yet shipped).
- **Decision.** **Option A — ship a proxy.** New
  verb `vehicle_type_recon_cost(dealership, *,
  window_start=None, window_end=None)`. Rows carry
  `(make, model)` discriminator + `vehicle_count`
  + `total_recon_cost` + `mean_recon_cost`.
  Filtered to `RECON_CATEGORIES + is_estimate=False`.
  Naming is deliberate — the verb is honest about
  the substrate ("recon cost per type") rather
  than claiming "profitability" it cannot yet
  compute.
- **Rejected: Option B** (defer Q3 to M9) — leaves
  M8.4 unbalanced with one aggregation only.
- **Rejected: Option C** (broader "total cost per
  type" summing recon + acquisition + admin) —
  mixes recon signal (dealer-controlled) with
  acquisition signal (market-driven); dilutes
  the actionable indicator.
- **Q3 M9 re-entry path.** When M9 Sale substrate
  ships, a new `vehicle_type_profitability` verb
  can land alongside this one (row extends with
  `total_sale_gross` + `mean_gross_pct`) OR
  replace it (row rename + shape extension).
  Either way no callers break.

### SESSION_095 (M8.2 open) — Q7 deferred

- **Amendment.** §1.8 (buyer-estimate-accuracy
  aggregation, Q7) is **deferred from M8.2** to a
  later increment or milestone.
- **Trigger.** §1.8 assumes acquisition-buyer
  provenance ("buyer_user_id") exists on the M2
  ledger. **It does not.** `VehicleAcquisition` has
  no `buyer` FK. `VehicleAcquisition.buyer_fees` is
  an auction-house buyer's-premium *fee* (Decimal),
  not a person. `WorkOrder.assignee` /
  `approved_by` / `started_by` / `completed_by`
  are in-house recon roles, not acquisition
  decision-makers.
- **Decision.** **Option A — defer Q7.** Q7 lands
  once acquisition-buyer provenance ships as a
  targeted M2 additive extension (its own planning
  session, its own increment).
- **Rejected: Option B** (add buyer FK + migration
  `0023` now) — violates M8.2 "no new models, no
  new migrations" scope bound set in the
  SESSION_094 handoff. Historical rows would
  populate NULL and the aggregation would return
  misleading data until backfilled.
- **Rejected: Option C** (use
  `VehicleCost.created_by` as a proxy for buyer)
  — semantically wrong: `created_by` is the
  data-entry person, not the acquisition
  decision-maker. Violates PROJECT_RULES.md #3
  (research → architecture → implementation chain).
- **Effect on §7 M8.2 scope.**
  - Ships: `vendor_performance` (Q2 + Q4). One
    aggregation, one endpoint.
  - Does NOT ship at M8.2:
    `buyer_estimate_accuracy` (Q7).
  - Test target: ~25 → **~15**.
  - Baseline projection: 3,192 → **~3,207** (was
    ~3,217).
- **Q7 re-entry path.** When acquisition-buyer
  provenance ships (dedicated planning session +
  M2 additive extension), Q7 can land as a
  standalone increment in whatever milestone that
  provenance surfaces in. Nothing about M8.2's
  code shape blocks a future Q7 addition.

---

## 0. Engineering practices to preserve from M2-M7

Synthesized from the six prior retrospectives. Every
practice below is a load-bearing constraint on M8.

1. **Increment discipline** (M2-M7 §6 lesson 1). Each
   M8 sub-increment ships independently verifiable in
   one session.

2. **Backend-first architecture; frontend never owns
   business rules** (M4-M7 §6 lesson 2). M8 will
   ship dashboards but every aggregation lives in a
   service module; the frontend renders values it
   receives from a DRF endpoint.

3. **Provider-neutral boundaries** (M4-M7 §6 lesson 3).
   Aggregation queries stay in Django ORM; if
   PostgreSQL-only window functions are attractive for
   an aggregation, evaluate the ORM equivalent first
   and fall back only with justification.

4. **Service ownership — one authoritative write /
   read path per operation** (M4-M7 §6 lesson 4).
   Every M8 aggregation lives behind a service verb;
   the DRF endpoint does query-arg parsing + JSON
   projection only.

5. **Local vs production parity** (M4-M7 §6 lesson 5).
   M8 aggregations run identically in dev + prod.
   Test suite exercises the real SQL against the test
   DB (no query mocks).

6. **Honest verification reporting** (M4-M7 §6 lesson
   6). If an aggregation returns no data (empty
   tenant, no rows in the window), the response
   distinguishes "empty" from "not computed" from
   "failed."

7. **Storage-first / safer-direction deletion** (M3-M7
   §6 lesson 7). M8 is read-only over M2-M7 substrate;
   no delete paths. But if any aggregation writes
   materialized rows (e.g. a `DashboardCache` table),
   those follow the pattern.

8. **Load-bearing decisions get user review BEFORE
   code** (M5-M7 §6 lesson 8). Every M8
   `[NEEDS-DECISION-BEFORE-M8.1]` item requires user
   confirmation at session open before implementation.

9. **Distinct domain errors → distinct HTTP status
   codes** (M5-M7 §6 lesson 9). M8 dashboards return
   proper error shapes for empty / unauthorized /
   invalid-arg cases.

10. **Read-model properties are pure reads** (M5-M7
    §6 lesson 10). M8 aggregations are the ultimate
    "pure read" — no side effects, no writes to
    source data.

11. **Additive extension over fork** (M6-M7 §6 lesson
    11). M8 aggregations extend the M2-M7 substrate
    read-only; no model or service modifications.

12. **Zero-planning-amendment sessions are a signal**
    (M6-M7 §6 lesson 12). Aim for clean decisions
    surfaced at planning time.

13. **Two-tier customer-visibility gate** (M6-M7 §6
    lesson 13). M8 dashboards are operator-facing;
    the batch/direct-access split does not directly
    apply, but the *permission-gate discipline* does
    (role-scoped views).

14. **Prior-increment count assertions should use
    `>=`, not `==`** (M7 §6 lesson 14). New at M7.
    Applies to every M8 test that asserts on carrier
    counts, endpoint counts, dashboard-widget counts.

---

## 1. Design memo

### 1.0 The operational questions Milestone 8 must answer

Ten questions synthesized from the research corpus.
These are the acceptance test for whether the milestone
shipped the right thing.

| # | Question | Research citation |
|---|---|---|
| 1 | **Which auctions produce the highest recon costs?** | INVENTORY §"To Ownership" — gross performance per source |
| 2 | **Which vendors finish fastest? Which cost the most?** | RECON §"To Ownership" — cost + turn-time discipline |
| 3 | **Which vehicle types produce the highest profit?** | INVENTORY §"To Ownership" — gross performance per source |
| 4 | **Which repairs are consistently underestimated?** | RECON §"To Ownership" — cost discipline; buyer estimate accuracy |
| 5 | **What are the aging trends per stage over the last N months?** | RECON §pain #7 + #12; M7.3 snapshots feed this |
| 6 | **What are gross-profit trends over time?** | SALES §"To Ownership" — realized-vs-projected gross |
| 7 | **What is buyer estimate accuracy over time?** | INVENTORY §"To Ownership" — estimate variance |
| 8 | **What is the inventory turn / days-to-sale?** | INVENTORY §"To Ownership" — inventory turn |
| 9 | **Which lifecycle stages consistently exceed target dwell time?** | RECON §pain #7 + #12; M7.3 snapshots |
| 10 | **What SLA-breach patterns emerged over the last N days?** | M7.4 log records feed this |

**Questions Milestone 8 does NOT answer** (deliberate):

- Q: *Predictive ML — "what will this vehicle sell for?"* —
  VCP explicitly rules ML out of M8.
- Q: *External BI-tool exports* — deferred; if operators
  need CSV export, add later.
- Q: *Portfolio-level BHPH analytics (delinquency, cure,
  charge-off)* — depends on Milestone 12 BHPH substrate.
  M8 v1 excludes.
- Q: *Sale-side realized gross* — depends on Milestone 9
  Sale substrate. M8 v1 excludes.
- Q: *Real-time dashboards (sub-minute refresh)* —
  aggregations refresh on-demand or via M7 Beat entries;
  no live-updating widgets.

### 1.1 Aggregation service substrate

- **Business questions answered.** Precondition for
  Q1-Q10.
- **Shape.** New `services/analytics/` package. One
  submodule per domain: `acquisition.py` (Q1, Q3),
  `recon.py` (Q2, Q4, Q7), `lifecycle_aging.py` (Q5,
  Q9), `sla_breaches.py` (Q10), `inventory_turn.py`
  (Q8), `gross_profit.py` (Q6). Each submodule exports
  named verbs returning dataclass rows.
- **Test posture.** Every aggregation exercised
  against a synthetic-fixture test DB. No SQL mocks.

### 1.2 Recon-cost-per-auction aggregation (Q1)

- **Business question answered.** Q1.
- **Citation.** INVENTORY §"To Ownership".
- **Substrate.** M2 `VehicleCost` (recon categories) +
  M4 `WorkOrder.actual_cost` + acquisition source
  provenance.
- **Shape.** `services/analytics/acquisition.py::recon_cost_per_source(dealership, *, window_start=None, window_end=None) -> list[SourcePerformanceRow]`.
  Rows carry source name, vehicle count, total recon
  cost, mean recon cost per vehicle.

### 1.3 Vendor performance aggregation (Q2, Q4)

- **Business question answered.** Q2, Q4.
- **Citation.** RECON §"To Ownership".
- **Substrate.** M4 `WorkOrder` + M4 `Vendor` + M2
  `VehicleCost`.
- **Shape.** `services/analytics/recon.py::vendor_performance(dealership, *, window_start=None, window_end=None) -> list[VendorPerformanceRow]`.
  Rows carry vendor name, completed count, mean days
  (approved → completed), estimated-vs-actual cost
  variance %, over-budget count.

### 1.4 Aging trend aggregation (Q5, Q9)

- **Business question answered.** Q5, Q9.
- **Citation.** RECON §pain #7 + #12.
- **Substrate.** **M7.3 `StageAgingSnapshot`** — the
  M7 milestone's payoff. M8 reads snapshots; does not
  recompute.
- **Shape.** `services/analytics/lifecycle_aging.py::stage_aging_trend(dealership, stage, *, window_days=30) -> list[AgingTrendPoint]`.
  Rows carry snapshot_at, p50, p90, vehicle_count.
  Time-series input for the dashboard's per-stage
  trend chart.

### 1.5 SLA-breach pattern aggregation (Q10)

- **Business question answered.** Q10.
- **Citation.** RECON §pain #12; M7.4 log substrate.
- **Substrate.** **M7.4 log records + `JobRunLog`** —
  M8 reads structured log fields. May introduce a
  materialized `SlaBreachRecord` table if log-aggregation
  is too fragile for a dashboard.
- **Shape.** `services/analytics/sla_breaches.py::breach_patterns(dealership, *, window_days=30) -> BreachPatternReport`.
  Report carries top-N vendors by breach count, top-N
  breach kinds, average breach_days.
- **Load-bearing decision:** log-scraping vs
  materialized table. See §5.

### 1.6 Gross-profit trend aggregation (Q6) — DEFERRED

- **Business question answered.** Q6.
- **Substrate.** Depends on Milestone 9 Sale model —
  no substrate exists at M8 time.
- **Shape.** **Defer to Milestone 9** — cite this
  planning doc as intended home.

### 1.7 Inventory-turn aggregation (Q8)

- **Business question answered.** Q8.
- **Citation.** INVENTORY §"To Ownership".
- **Substrate.** M5 `VehicleStageEvent` (entry to
  `frontline`) + M9 Sale model (deferred) OR
  `VehicleStage.current_stage='sold'` (also M9).
- **Shape.** **Partial for M8 v1** — inventory-turn
  requires sale-side substrate. M8 v1 ships "average
  days at `frontline`" (via M7.3 snapshots) as a
  proxy; true inventory-turn defers to M9.

### 1.8 Buyer-estimate-accuracy aggregation (Q7)

- **Business question answered.** Q7.
- **Citation.** RECON §"To Ownership".
- **Substrate.** M4 `WorkOrder.estimated_cost` vs
  `actual_cost` + acquisition buyer provenance (M2
  ledger).
- **Shape.** `services/analytics/recon.py::buyer_estimate_accuracy(dealership, buyer_user_id, *, window_days=90) -> BuyerAccuracyRow`.
  Row carries buyer name, WO count, mean absolute
  variance %, +/- bias.

### 1.9 Dashboard endpoint surface

- **Shape.** DRF endpoints per aggregation, all under
  `/api/dealer-ai/admin/analytics/`. Role-gated via
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  admission + service-layer tenant-scoping.
- **Response shape.** Dataclass rows serialized as
  JSON arrays. Query args parse into
  `window_start`/`window_end`/`window_days`.
- **Load-bearing decision:** compute-on-request vs
  M7-Beat-driven materialization. See §5.

### 1.10 Operator UI

- **Shape.** New route `/dealer-ai-analytics/` with
  N tabs (Q1-Q10 = ~7 dashboards in M8 v1). Each tab
  is a table + optional simple chart (recharts /
  chart.js). Role-gated on the frontend as a UX
  convenience; server-side is authoritative.

---

## 2. Migration impact review

*(Skeleton — filled in at M8.1 planning close.)*

| # | Existing surface | Location | M8 impact |
|---|---|---|---|
| 1 | Django settings | `backend/dealer_kit/settings.py` | Possibly additive (analytics-cache TTL constants if compute-on-request too slow). |
| 2 | `services/analytics/` (NEW package) | greenfield | New package with 6 submodules. |
| 3 | `_TENANT_CARRIER_MODEL_NAMES` | 21 at M7 close | Additive (potentially) if any materialization tables ship. Decide at §5. |
| 4 | `views_analytics.py` (NEW) | greenfield | New DRF view module + N endpoints per §1.9. |
| 5 | Frontend `pages/AnalyticsPage.tsx` (NEW) | greenfield | New route + N tab components. |
| ... | ... | ... | ... |

Row count locks at M8.1 during planning + implementation.

---

## 3. Compatibility checklist

*(Skeleton — filled in at M8.1.)*

M8 ships with this checklist verified true; evidence
recorded inline at milestone close.

### M1–M7 invariants Milestone 8 must not regress

- [ ] Every existing service module untouched except
  for additive extension.
- [ ] Every existing model unchanged.
- [ ] Every existing test passes at 3,150 baseline.
- [ ] `Vehicle.is_available` unchanged.
- [ ] M5 lifecycle transitions unchanged.
- [ ] M6 photo + listing surface unchanged.
- [ ] M7 Beat entries + JobRunLog surface unchanged.
- [ ] Frontend `tsc --noEmit` + `vite build` clean.

### New invariants Milestone 8 introduces

- [ ] Every analytics endpoint enforces role admission
  + service-layer tenant-scoping (never leak
  cross-tenant data via a query-arg escape).
- [ ] Aggregations return empty arrays for empty
  tenants (not 500).
- [ ] Response projections deliberately exclude
  internal cost/margin fields from customer-facing
  surfaces (M8 endpoints are operator-only, but the
  discipline stays).

---

## 4. Reusable primitives review

- **M2 ledger** (`services/vehicle_ledger.py::compute_totals`)
  — direct read for gross-cost aggregations.
- **M4 WorkOrder + Vendor** — direct read for vendor
  performance + buyer estimate accuracy.
- **M5 `VehicleStage` + `VehicleStageEvent`** — direct
  read for aging + inventory-turn proxies.
- **M7.3 `StageAgingSnapshot`** — the pre-aggregated
  aging data M8's aging-trend widgets read.
- **M7.4 log records** — pattern-mining source for
  SLA-breach dashboards.
- **`JobRunLog`** — direct read for
  "did aggregation refresh?" operator confidence.

---

## 5. Scope discipline + load-bearing decisions

### 5.a `[NEEDS-DECISION-BEFORE-M8.1]` — Compute strategy

**Question.** Compute-on-request or M7-Beat-driven
materialization?

**Options.**
- **Option A** — compute-on-request. Every dashboard
  request runs its aggregation query. Simpler; slower
  for large tenants.
- **Option B** — M7-Beat-driven materialization. A
  new Beat entry per aggregation refreshes a
  `AnalyticsCache` table nightly. Faster reads;
  larger M8 scope + one new model per aggregation.
- **Option C** — hybrid: compute-on-request for v1,
  materialize when operator evidence surfaces
  latency pain.

**Recommended for user review:** **Option C** (hybrid).
Ship compute-on-request first; observe. Add
materialization as an M7 Beat entry only if evidence
justifies the extra substrate.

### 5.b `[NEEDS-DECISION-BEFORE-M8.1]` — SLA-breach data source

**Question.** Log-scrape or materialized breach records?

**Options.**
- **Option A** — read M7.4 `logging.WARNING` records
  from the log stream. Requires log-aggregation
  substrate (structlog / journald / CloudWatch — not
  in the stack today).
- **Option B** — introduce a new `SlaBreachRecord`
  model + migration `0022`. M7.4 verb writes to it
  in addition to the log stream. M8 reads the table.

**Recommended for user review:** **Option B** — the
log stream is not queryable today. Adding a
`SlaBreachRecord` model is a small additive extension
that unlocks the M8 dashboard cleanly.

### 5.c `[NEEDS-DECISION-BEFORE-M8.1]` — Chart library

**Question.** recharts / chart.js / Chart.js React /
none-yet?

**Options.**
- **Option A** — recharts. React-native charting;
  small; familiar API.
- **Option B** — Chart.js via `react-chartjs-2`.
  Larger; more chart types.
- **Option C** — no charts for v1; tables + trend
  arrows / sparklines from a lightweight helper.

**Recommended for user review:** **Option A** (recharts)
— smallest bundle addition; sufficient for M8 v1
line/bar chart needs. Complex visualization can wait
for operator evidence.

### 5.d `[NEEDS-DECISION-BEFORE-M8.1]` — Increment count

**Question.** Ship M8 as five increments (per
aggregation family) or seven (per question)?

**Options.**
- **Option A** — five increments (M8.1 = infra +
  aggregation service package + first endpoint; M8.2 =
  recon vendor performance + buyer accuracy; M8.3 =
  aging trends + SLA patterns; M8.4 = acquisition
  source + inventory-turn proxy; M8.5 = UI + M8.6 =
  closeout).
- **Option B** — seven increments (one per Q).

**Recommended for user review:** **Option A** — five
mirrors M7's six-increment shape (one closeout).
Seven inflates coordination overhead for no gain.

### 5.e Test posture

Aggregation tests use TestCase (transactional). No
mocks over SQL. Load-scale tests deferred until
performance evidence surfaces need.

---

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 8
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md` §6
   (lessons carry into M8)
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md` §6
7. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Current source code — authoritative.

Planning docs are claims. Rules + research + code are
facts.

---

## 7. Increment sequencing

Six increments (mirrors M7 shape). Sequencing
recommendation per §5.d Option A.

### Increment 1 (M8.1) — Analytics infrastructure + first aggregation

**Scope.** New `services/analytics/` package with
substrate module + one aggregation submodule +
`views_analytics.py` + first endpoint. `AnalyticsCache`
model deferred (§5.a Option C hybrid). If §5.b Option
B confirmed: `SlaBreachRecord` model + migration `0022`
+ M7.4 verb extension to write to it.

**Tests.** ~30 focused tests.

**Boundary.** Baseline 3,150 → ~3,180.

### Increment 2 (M8.2) — Vendor + buyer performance aggregations

**Scope (as amended SESSION_095 open — see §0.a).**
Q2 + Q4 aggregation only (`vendor_performance`).
One endpoint + role-gate. **Q7
(`buyer_estimate_accuracy`) deferred** — depends
on M2 acquisition-buyer provenance not yet
shipped.

**Tests.** ~15 focused. Baseline ~3,192 → ~3,207.

### Increment 3 (M8.3) — Aging + SLA aggregations

**Scope.** Q5 + Q9 + Q10 aggregations
(`stage_aging_trend`, `breach_patterns`). Reads M7.3
snapshots + M7.4 (log or `SlaBreachRecord` per §5.b).

**Tests.** ~25 focused. Baseline ~3,205 → ~3,230.

### Increment 4 (M8.4) — Acquisition + inventory-turn proxies

**Scope (as amended SESSION_097 open — see §0.a).**
Q3 + Q8 aggregations only
(`vehicle_type_recon_cost`,
`days_at_frontline_proxy`). **Q1
(`recon_cost_per_source`) already shipped at
M8.1.** Q3 ships as a proxy — true profitability
depends on M9 Sale substrate not yet shipped.

**Tests.** ~20 focused. Baseline ~3,247 → ~3,267.

### Increment 5 (M8.5) — Operator UI

**Scope.** New route `/dealer-ai-analytics/` with N
tabs (Q1-Q10 minus Q6 deferred). Role-gated. recharts
per §5.c Option A.

**Tests.** ~15 frontend + ~10 backend endpoint-shape.
Baseline ~3,255 → ~3,280.

### Increment 6 (M8.6) — Closeout

**Scope.** Documentation-only. §3 compatibility sweep,
retrospective, capability matrix §7i, roadmap flip,
planning frontmatter, session-start refresh,
`MILESTONE_9_PLANNING.md` per standing user directive,
commit + push.

---

## 8. Related documents

- `docs/PROJECT_RULES.md`
- `docs/DOC_GOVERNANCE.md`
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 8
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md` (M7
  lessons — carry into M8)
- `docs/research/VEHICLE_CENTRIC_PIVOT.md`
  §"Operational intelligence (long-term)"
- `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
  §"To Ownership / Owner"
- `docs/research/RECON_MAPPING.md` §"To Ownership"
- `docs/CAPABILITY_MATRIX.md` — the shipped-state
  surface M8 layers on top of.
- Current source code — authoritative.

---

## 9. Load-bearing decisions summary — items requiring user review before M8.1

Every `[NEEDS-DECISION-BEFORE-M8.1]` in this document,
consolidated:

1. **§5.a — Compute strategy.** Recommended:
   Option C (hybrid — compute-on-request v1,
   materialize when evidence).
2. **§5.b — SLA-breach data source.** Recommended:
   Option B (new `SlaBreachRecord` model + M7.4 verb
   extension).
3. **§5.c — Chart library.** Recommended: Option A
   (recharts).
4. **§5.d — Increment count.** Recommended: Option A
   (five aggregation increments + one closeout).

Every other §5.e decision is chosen by the planning
doc. Decisions marked `[NEEDS-DECISION-BEFORE-M8.1]`
are the ones the user should confirm at the top of
SESSION_094 before code lands — same discipline as
M5/M6/M7 §9 mandates.
