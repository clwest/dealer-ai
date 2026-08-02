---
title: "Milestone 9 — Implementation-Planning Pass"
status: shipped
type: planning-artifact
generated: 2026-08-01
generated_at_session: SESSION_099 (post-M8-closeout)
shipped_at_session: SESSION_105
milestone: 9
milestone_name: "Sale + delivery closure"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_8_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_8_PLANNING.md
  - docs/roadmap/MILESTONE_7_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/RECON_MAPPING.md
---

# Milestone 9 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 9
(Sale + delivery closure). Every implementation
increment cites back here for scope, invariants,
and refinement provenance. Mirrors the shape
M3 / M4 / M5 / M6 / M7 / M8 planning docs
proved out.

**Business objective (from `IMPLEMENTATION_ROADMAP.md`
§Milestone 9).** Close the loop between the vehicle
side and the customer side. When a Vehicle
transitions to sold, the CRM side activates.
Realized gross is tied back to projected gross
so the merchandising cycle can be measured
end-to-end. Delivery preparation is coordinated
(checklist, temp tag, insurance, walkthrough).

**VCP mandate.** Phase 8 of the vehicle-centric
pivot. The Sale substrate unlocks three deferred
M8 analytics questions — Q3 (true vehicle-type
profitability), Q6 (gross-profit trend), Q8
(true inventory-turn / days-to-sale) — plus Q7
if the acquisition-buyer FK ships alongside.

**Zero implementation this session.** Planning
artifact only. SESSION_100 opens M9.1.

---

## 0. Engineering practices to preserve from M2-M8

Synthesized from the seven prior retrospectives.
Every practice below is a load-bearing constraint
on M9.

*(Mirrors the M8 §0 structure; the fifteen M8
lessons in `MILESTONE_8_RETROSPECTIVE.md` §6
carry forward with M9 evidence expected.)*

---

## 0.a Change log (implementation-time amendments)

Per M5/M6/M7/M8 §9 mandates, load-bearing
planning decisions may need narrow amendment at
implementation time as substrate reality asserts
itself. Every amendment records the session,
option, and the affected sections.

### SESSION_100 (M9.1 open) — §5.a / §5.b / §5.c confirmed (all Option A)

- **Amendment.** All three §9 load-bearing
  decisions confirmed by the user at
  SESSION_100 open (all Option A). No spec
  changes — the recommended path becomes the
  ratified path.
- **§5.a — Acquisition-buyer provenance
  bundling: Option A.** M2
  `VehicleAcquisition.buyer` FK ships in M9
  alongside `Sale`. Django's `makemigrations`
  combined both changes into a single M9.1
  migration `0023_sale_entity_and_buyer_fk`
  (planning had projected `0024` — combining
  is cleaner: one atomic delivery, one
  reverse operation). Unlocks Q7
  (`buyer_estimate_accuracy`) in the same
  milestone rather than a follow-on.
- **§5.b — Sale.buyer representation:
  Option A.** `Sale.buyer` is FK to
  existing `CustomerLead` (M3-M5 CRM
  substrate reused).
- **§5.c — Sale finance-type vocabulary:
  Option A.** Three initial values:
  `cash` / `retail` / `bhph`. Additional
  values (`lease`, `wholesale_out`,
  `internal_transfer`, `wholesale_disposal`)
  land when operator evidence surfaces
  need.
- **Sequencing decision** (M9.1
  implementation-time): **combined into
  single migration**. Django ordered
  operations as (a) AddField
  `VehicleAcquisition.buyer`, then (b)
  CreateModel `Sale`. Both ship in M9.1
  atomically. No M2 code path changes at
  M9.1 close — Q7 verb + endpoint land at
  M9.4 per §7.
- **Effect on §7 M9.1 scope.**
  - Ships: `Sale` model + `gross_realized`
    verb + first endpoint (`POST /admin/vehicles/<stock>/sale/`)
    + tenancy carrier 22→23 +
    `VehicleAcquisition.buyer` FK.
  - Test target: ~30 (unchanged; adds
    ~3-5 focused tests for the
    additive-buyer-FK migration on top of
    the Sale-substrate tests).
  - Baseline projection: 3,274 → **~3,304**
    (unchanged from planning).

### SESSION_101 (M9.2 open) — §1.2 Delivery-OneToOne confirmed (Option A) + M9 commit strategy (bundle)

- **Amendment (§1.2 open question).** The
  Delivery-OneToOne question surfaced in
  the SESSION_100 handoff (three options —
  mandatory OneToOne / nullable OneToOne /
  no OneToOne) resolves to **Option A —
  mandatory OneToOne**. `Delivery.sale`
  is a NOT NULL OneToOne FK to `Sale`.
- **Interpretation clarification.**
  "Mandatory OneToOne" means the DB
  invariant "every Delivery row references
  a Sale". It does **not** mean automatic
  Delivery creation on Sale write —
  Delivery is created via the explicit
  M9.2 endpoint (`POST /admin/vehicles/<stock>/delivery/`)
  after Sale creation. This preserves the
  M9.1 boundary (no post_save signal on
  `Sale`; no coupling change in
  :func:`services.sale.record_sale`) while
  matching the SALES §delivery-workflow
  research assumption that every sale
  eventually transitions through delivery.
- **Cash-and-carry.** No special-case
  handling. The `checklist` JSON just
  ships with fewer items marked True at
  Delivery-create time (`temp_tag`,
  `insurance_verified`, `customer_walkthrough`
  can all be True on the first PATCH).
- **M9 commit strategy.** **Bundle**
  per M7/M8 precedent. M9.1 changes
  remain uncommitted; the M9.6 closeout
  will ship one coordinated commit for
  all of M9.1-M9.6. Working tree stays
  dirty across session boundaries — this
  is the established M8 pattern
  (SESSION_099 landed commit `34352ed`
  covering M8.1-M8.6).
- **Effect on §7 M9.2 scope.**
  - Ships: `Delivery` model + migration
    `0024` + `services/delivery/` package
    (write verb + checklist update verb +
    insurance verification verb) +
    tenancy carrier 23→24 + endpoints
    (POST create + PATCH update).
  - Test target: ~25 (unchanged from
    planning).
  - Baseline projection: 3,320 →
    **~3,345** (unchanged from planning).

### SESSION_102 (M9.3 open) — analytics extensions shipped

- **No new user decisions.** Plan
  §1.5 was fully specified at planning-time
  close; SESSION_102 executed against it
  directly.
- **Implementation-time notes.**
  - **Q3 `vehicle_type_profitability`
    row shape.** Chose Sale-centric shape
    (`sold_count`, `total_sale_gross`,
    `total_sold_price`, `mean_gross_pct`)
    rather than literally extending M8.4's
    `VehicleTypeReconCostRow` — the two
    verbs answer different questions (M8.4:
    "prep cost per type", M9.3: "profit
    per type"). Composing them into one row
    would conflate the two aggregation
    universes.
  - **`mean_gross_pct` semantics.** Mean
    of per-vehicle margin percentages
    (equal-weighted). Callers wanting
    revenue-weighted margin compute
    `total_sale_gross / total_sold_price`
    from the row.
  - **Q8 `inventory_turn` reference-point.**
    Uses the *earliest* frontline
    `VehicleStageEvent` per vehicle (not
    latest re-entry). A vehicle that
    bounced back to recon then returned to
    frontline is still "the same inventory
    item" for turn-measurement purposes.
  - **Test-only signal awareness.**
    `dealer_ai/tests/__init__.py`
    auto-bootstraps a `frontline`
    VehicleStageEvent on every Vehicle
    save. M9.3's `test_skips_sold_vehicles_without_frontline_event`
    deletes the bootstrap event
    post-seed to simulate the data-
    quality gap the verb docstring
    describes.
  - **Sparse gross-profit series.**
    `gross_profit_trend` returns one
    point per date that had at least
    one sale — dates with zero sales
    are omitted. Dense series (one
    point per calendar day, zero-filled)
    lands later if operator evidence
    surfaces need.
- **Effect on §7 M9.3 scope.**
  - Ships: three verbs
    (`vehicle_type_profitability`,
    `gross_profit_trend`,
    `inventory_turn`) + three DRF
    endpoints + smoke tests locking the
    M8.4-proxy shapes.
  - Test target: ~25 → actual 32
    (verb + endpoint + M8.4-proxy
    smoke). Slightly over plan due to
    per-verb error-path coverage.
  - Baseline projection: 3,362 →
    **actual 3,394** (unchanged
    from planning bracket).

### SESSION_103 (M9.4 open) — §1.3 annotation deferred (substrate gap)

- **Amendment (§1.3 open question).**
  `LeadVehicleInterest.stage_at_interest`
  annotation is **deferred from M9.4** to
  a later increment or its own planning
  session.
- **Trigger.** §1.3 assumes
  `LeadVehicleInterest` exists as a
  through-model on the
  `CustomerLead.interested_vehicles`
  M2M relationship. **It does not.**
  The current schema uses a plain
  `ManyToManyField(Vehicle)` on
  `CustomerLead`, backed by the
  implicit Django-generated table
  `dealer_ai_customerlead_interested_vehicles`
  (no `created_at`, no through-model,
  no domain-model class to extend).
- **Decision.** **Option 2 (user-
  confirmed at SESSION_103 open) —
  ship Q7 only at M9.4.**
  Q7 (`buyer_estimate_accuracy`) does
  not depend on `LeadVehicleInterest`
  at all — it reads
  `VehicleAcquisition.buyer` +
  `Sale.gross_realized`. The annotation
  is independent scope.
- **Rejected — Option 1** (create
  through-model + data migrate at
  M9.4). Substantial scope creep: adds
  a data migration to convert the
  implicit M2M table into an explicit
  through-model with `created_at` +
  `stage_at_interest`, plus sweeps of
  ~5 call sites in `views.py` /
  `serializers.py` / `admin.py` to
  switch from plain `add()` to
  explicit `.through.objects.create(...)`.
  Violates PROJECT_RULES.md #4 (scope
  discipline) for a single increment.
- **Rejected — Option 3** (JSONField
  hack on `CustomerLead`). Loses
  per-vehicle granularity; hard to
  query.
- **Re-entry path.** The annotation
  can land in whatever milestone
  through-model creation is
  independently justified — most
  likely M11+ if the CRM tightens up,
  or its own dedicated increment with
  its own planning session. Nothing
  about M9.4's Q7 code shape blocks a
  future annotation addition.
- **Effect on §7 M9.4 scope.**
  - Ships: `buyer_estimate_accuracy`
    verb + one DRF endpoint.
  - Does NOT ship at M9.4:
    `LeadVehicleInterest.stage_at_interest`
    field + write-path integration +
    through-model migration.
  - Test target: ~20 → **~10-12**
    (Q7 verb + endpoint only; no
    annotation tests).
  - Baseline projection: 3,394 →
    **~3,406** (was ~3,414).
- **Also confirmed:** the §1.3 backfill
  posture question (Option A forward-
  only vs Option B/C historical
  reconstruction) is **moot** — the
  annotation itself is deferred. When
  the through-model lands in its own
  session, the backfill posture
  decision surfaces then.

### SESSION_104 (M9.5 open) — §1.7 UI decisions confirmed (both Option A)

- **No new backend changes at M9.5.**
  UI-only increment consuming the M8
  + M9 aggregation endpoints and the
  M9.1/M9.2 Sale + Delivery admin API.
- **Decision A — Q7 placement:
  Option A confirmed.** Q7
  buyer-accuracy rank surface bundles
  into the fifth "Realized Gross"
  tab alongside Q3 vehicle-type
  profitability. Both answer "who
  produced the profit?" — grouping
  keeps the operator's mental model
  tight.
- **Decision B — Sale + Delivery UI:
  Option A confirmed** (per-vehicle
  page pattern). Interpretation
  clarified: the M8.5 codebase does
  NOT have a unified "vehicle-detail
  page with sub-tabs" — every
  per-vehicle feature lives at its
  own dedicated route
  (`dealer-ai-inventory/:stock/ledger`,
  `.../:stock/condition-report`,
  `.../:stock/recon`,
  `.../:stock/lifecycle`,
  `.../:stock/photos`,
  `.../:stock/listing`). M9.5 adds
  `dealer-ai-inventory/:stock/sale/`
  matching the same shape (new
  `VehicleSalePage.tsx`). "Sub-tab"
  in the planning-time wording was
  imprecise — the actual codebase
  pattern is dedicated per-feature
  pages, not sub-tabs.
- **Effect on §7 M9.5 scope.**
  - Ships: fifth `AnalyticsSection`
    tab **Realized Gross** wrapping
    Q3 / Q6 / Q7 / Q8; new
    `saleApi.ts` client; new
    `VehicleSalePage.tsx` at
    `dealer-ai-inventory/:stock/sale/`;
    route registration in
    `main.tsx`.
  - Test target: ~15 frontend
    Vitest + ~10 backend endpoint-
    shape locks.
  - Baseline projection: backend
    3,414 → **~3,424**; frontend
    19 → **~34**.
- **Substrate-gap #2 (implementation-
  time).** M9.5 opened before the GET
  companions to the M9.1/M9.2 write
  endpoints existed. Ships **Option A
  (user-confirmed)** — add GET
  dispatch to the same URL as POST
  via `@api_view(["GET", "POST"])`
  method-multiplex. Preserves URL
  names (`admin-sale-create`,
  `admin-delivery-create`) so existing
  tests + docs stay green. Adds two
  `_lookup_*_or_404` helpers +
  method-branch bodies (~50 backend
  lines). Rejected — separate
  `admin-sale-read` URL (URL sprawl)
  and write-only UI (broken UX after
  page reload).
- **Actual delivery vs planning.**
  - Backend +12 shape-lock tests
    (target ~10, slightly over
    because GET × 2 endpoints ×
    auth-matrix rows landed as
    exhaustive coverage). Final
    3,414 → **3,426**.
  - Frontend +15 tests exactly on
    plan (RealizedGrossTab 7 +
    VehicleSalePage 7 +
    DealerAnalyticsPage +1
    realized-gross hash-honor test).
    Final 19 → **34**.

---

## 1. Design memo

### 1.0 The operational questions Milestone 9 must answer

Six questions synthesized from research corpus +
the M8 deferrals it resolves.

| # | Question | Research citation |
|---|---|---|
| 1 | **When a Vehicle is sold, how does its CRM record activate?** | SALES §customer journey — deal → delivery → follow-up |
| 2 | **What are the pieces of a delivery workflow — checklist, temp tag, insurance, customer walkthrough — and how are they tracked to completion?** | SALES §delivery workflow |
| 3 | **What is realized gross vs projected gross per sold vehicle?** | INVENTORY §"To Ownership" + M2 total-investment substrate + M8 Q6 deferral |
| 4 | **What is buyer estimate accuracy over time?** (M8 Q7 deferred pending acquisition-buyer provenance) | RECON §"To Ownership" + M8 §0.a SESSION_095 deferral |
| 5 | **What is true vehicle-type profitability?** (M8 Q3 proxy replaced by real profit calc) | INVENTORY §"To Ownership" + M8 §0.a SESSION_097 proxy note |
| 6 | **What is true inventory turn / days-to-sale?** (M8 Q8 proxy replaced by real turn calc) | INVENTORY §"To Ownership" + M8 §1.7 proxy note |

**Questions Milestone 9 does NOT answer**
(deliberate):

- **F&I deal-desk workflow** — Milestone 10
  substrate (stips, funding, chargebacks).
- **DMS write-back integrations** — planning
  §scope-boundary explicit non-goal.
- **State e-filing integrations** — same.
- **Sales-tax computation** — belongs to
  Accounting track.
- **Portfolio-level BHPH analytics** — depends
  on Milestone 12 BHPH substrate.
- **F&I stip aging alerts** — Milestone 7 §1
  cited these as a future async job family;
  substrate is M10.

### 1.1 Sale entity

- **Business questions answered.** Q1, Q3
  precondition.
- **Shape.** New `Sale` model with fields per
  `IMPLEMENTATION_ROADMAP.md` §Milestone 9
  gap list: `buyer` (FK — nullable if buyer
  representation lands separately), `vehicle`
  FK to `Vehicle` (unique — one Sale per
  Vehicle), `sale_date`, `sold_price` Decimal,
  `finance_type` from a small vocabulary
  (`cash` / `retail` / `bhph`),
  `lender_name` (nullable text; FK if a
  Lender entity emerges), `gross_realized`
  Decimal computed against M2 total
  investment.
- **Test posture.** Standard: TestCase +
  cross-tenant guards + M4-M8 authorization
  matrix.

### 1.2 Delivery entity

- **Business questions answered.** Q2.
- **Shape.** New `Delivery` model with `sale`
  FK OneToOne, `delivery_date`, `checklist`
  JSON field (initial vocabulary
  `detail_booked`, `fueled`, `temp_tag`,
  `insurance_verified`, `customer_walkthrough`),
  `temp_tag_number`, `insurance_verified` +
  `insurance_verified_at`, `notes`.
- **Test posture.** Standard.

### 1.3 LeadVehicleInterest annotation

- **Business questions answered.** Q1 (context
  for what stage the vehicle was at when the
  customer became interested).
- **Shape.** Extend the existing
  `LeadVehicleInterest` through-model with a
  `stage_at_interest` field capturing the
  M5 `VehicleStage.current_stage` at
  interest-write time. Populated by the
  existing write path via denormalization.

### 1.4 gross_realized computation

- **Business questions answered.** Q3, Q5.
- **Shape.** `services/sale/computation.py::gross_realized(sale)
  -> Decimal` reading M2 `vehicle_ledger.compute_totals(sale.vehicle)`
  and subtracting `total_investment` from
  `sold_price`. Read-only; never mutates the
  ledger.

### 1.5 Analytics extensions unlocking M8 deferrals

- **Q3 true vehicle-type profitability.** New
  `services/analytics/acquisition.py::vehicle_type_profitability(dealership, *, window_start=None, window_end=None) -> list[VehicleTypeProfitabilityRow]`.
  Row extends the M8.4 shape with
  `total_sale_gross` + `mean_gross_pct`.
  Callers of the M8.4 proxy
  (`vehicle_type_recon_cost`) continue to
  work; this is a new sibling verb, not a
  rewrite (per M8 §6 lesson 11 additive
  extension).
- **Q6 gross-profit trend.** New
  `services/analytics/gross_profit.py::gross_profit_trend(dealership, *, window_days=90) -> list[GrossProfitPoint]`.
  Time-series over `Sale.sale_date` +
  `gross_realized`.
- **Q7 buyer estimate accuracy.**
  **Depends on the acquisition-buyer
  provenance decision** (see §5.a below).
  If Option A confirmed, new
  `services/analytics/recon.py::buyer_estimate_accuracy(dealership, buyer_user_id, *, window_days=90) -> BuyerAccuracyRow`
  matching the M8 planning §1.8 spec.
- **Q8 true inventory turn.** New
  `services/analytics/lifecycle_aging.py::inventory_turn(dealership, *, window_days=90) -> list[InventoryTurnRow]`.
  Reads M5 `VehicleStageEvent` (entry to
  frontline) + `Sale.sale_date` per vehicle;
  emits days-to-sale distribution. Callers
  of the M8.4 proxy
  (`days_at_frontline_proxy`) continue to
  work.

### 1.6 Dashboard endpoint surface

- **Shape.** New DRF endpoints under
  `/api/dealer-ai/admin/analytics/` for the
  three unlocked aggregations:
  `vehicle-type-profitability/`,
  `gross-profit-trend/`, `inventory-turn/`.
  Q7 endpoint depends on §5.a. All role-
  gated on
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  per M8 pattern.

### 1.7 Operator UI extension

- **Shape.** Extend the M8.5
  `/dealer-ai-analytics/` page with a fifth
  tab **Realized Gross** (Q3 true + Q6 trend
  + Q8 true) plus updates to existing tabs
  to surface true-vs-proxy where applicable.
  A "Sales" operator UI (list of Sale +
  Delivery rows per Vehicle) also enters
  scope — decide at M9.n whether it lands
  as a Vehicle-detail sub-tab or a
  dedicated page.

---

## 2. Migration impact review

*(Skeleton — filled in at M9.1 planning close.)*

| # | Existing surface | Location | M9 impact |
|---|---|---|---|
| 1 | `LeadVehicleInterest` | `backend/dealer_ai/models.py` | Additive extension: `stage_at_interest` field + migration `0023`. |
| 2 | `_TENANT_CARRIER_MODEL_NAMES` | 22 at M8 close | Additive: `Sale` + `Delivery` (+ possibly `LeadVehicleInterest` if not already covered). 22 → 24 or 25. |
| 3 | `views_analytics.py` | 40 endpoints at M8 close | Additive: 3-4 new endpoints per §1.6. |
| 4 | `frontend/src/pages/DealerAnalyticsPage.tsx` | 4 tabs at M8.5 | Additive: fifth tab (Realized Gross). |

---

## 3. Compatibility checklist

*(Skeleton — filled in per-increment as M9.1-M9.N
plan.)*

- **M1 (auth):** untouched. Same
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  gate.
- **M2 (ledger):** read-only from
  `gross_realized`. Never mutates ledger
  totals.
- **M3-M7 substrate:** untouched.
- **M8 analytics:** additive extension only.
  Existing M8.4 proxies (`vehicle_type_recon_cost`,
  `days_at_frontline_proxy`) continue to
  work as-is; new true-profit / true-turn
  verbs land alongside per M8 §6 lesson 11.
  The four existing M8.5 dashboard tabs
  continue to render M8.1-M8.4 data
  unchanged.
- **Frontend Vitest baseline:** grows
  additively — new tab tests land alongside
  M8.5's 19 tests.

---

## 5. Scope discipline + load-bearing decisions

### 5.a `[NEEDS-DECISION-BEFORE-M9.N]` — Acquisition-buyer provenance

**Question.** Does M9 also ship the M2 `VehicleAcquisition.buyer`
FK that M8's Q7 needed (and deferred)?

**Options.**

- **Option A** — bundle the M2 buyer-FK
  extension into M9 alongside Sale +
  Delivery. Unlocks Q7 in the same milestone.
  Adds migration `0024` (or an M9 chained
  migration).
- **Option B** — keep Q7 out of M9.
  Buyer-provenance lands in a dedicated
  future increment. M9 ships true-profit +
  true-turn + gross-trend only.

**Recommended for user review:** **Option
A** — the M8.4 handoff already documented
this as the Q7 re-entry path. Bundling
means one migration + one M9 delivery moment
instead of two.

### 5.b `[NEEDS-DECISION-BEFORE-M9.N]` — Sale.buyer representation

**Question.** Is `Sale.buyer` an FK to an
existing `CustomerLead` (the M3-M5 CRM shape)
or a new `Buyer` entity, or free text pending
a proper CRM shape?

**Options.**

- **Option A** — `Sale.buyer` is FK to
  `CustomerLead`. Reuses the M3-M5 CRM
  substrate. `Buyer` entity deferred.
- **Option B** — new `Buyer` model + FK.
  Enables buyer analytics across sales (not
  possible from `CustomerLead` alone).
- **Option C** — free text on `Sale` for
  now, `Buyer` entity deferred until a CRM
  overhaul.

**Recommended for user review:** **Option
A** — reuses existing substrate; matches
M9's "close the loop" framing where the
buyer already exists as a `CustomerLead`.
Option B is out-of-scope creep for M9;
Option C is a data-quality regression.

### 5.c `[NEEDS-DECISION-BEFORE-M9.N]` — Sale finance-type vocabulary

**Question.** What are the initial values
for `Sale.finance_type`?

**Options.**

- **Option A** — three values: `cash` /
  `retail` / `bhph`. Matches the M8 planning
  §1.6 catalog.
- **Option B** — extend to add `lease`,
  `wholesale_out`, `internal_transfer`,
  `wholesale_disposal`.

**Recommended for user review:** **Option
A** — small vocabulary; extensions land
when operator evidence surfaces need.

### 5.d Test posture

Sale + Delivery tests use TestCase
(transactional). Cross-tenant guards on
every write. Analytics extensions follow
the M8 test-file pattern (verb tests +
endpoint tests per verb).

---

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 9
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md` §6
   (fifteen lessons carry into M9)
6. `docs/roadmap/MILESTONE_8_PLANNING.md`
   (with §0.a SESSION_095 + SESSION_097
   amendments — Q7 deferral + Q3 proxy)
7. `docs/CAPABILITY_MATRIX.md` §7i
8. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
   §Phase 8
9. `docs/research/SALES_DEPARTMENT_MAPPING.md`
10. Current source code — authoritative.

Planning docs are claims. Rules + research +
code are facts.

---

## 7. Increment sequencing

*(Skeleton — filled in at planning-time close.
Likely five increments per M6/M7/M8 pattern.
Draft:)*

### Increment 1 (M9.1) — Sale entity + `gross_realized`

**Scope.** New `Sale` model + migration
`0023`. `services/sale/` package + `gross_realized`
verb. First endpoint: `POST /api/dealer-ai/admin/vehicles/<stock>/sale/`.
Tenancy-carrier extension.

**Tests.** ~30 focused.

### Increment 2 (M9.2) — Delivery entity + checklist

**Scope.** `Delivery` model + migration
`0024` (or `0025` if §5.a Option A confirmed
extends M2 buyer FK first). Delivery
service verbs + endpoint. Tenancy-carrier
extension.

**Tests.** ~25 focused.

### Increment 3 (M9.3) — Q3 + Q6 + Q8 analytics extensions

**Scope.** True `vehicle_type_profitability`
+ `gross_profit_trend` + `inventory_turn`
verbs + three endpoints. Existing M8.4
proxies preserved.

**Tests.** ~25 focused.

### Increment 4 (M9.4) — Q7 (if §5.a Option A) + LeadVehicleInterest annotation

**Scope.** If §5.a Option A confirmed:
`VehicleAcquisition.buyer` FK +
`buyer_estimate_accuracy` verb + endpoint.
`LeadVehicleInterest.stage_at_interest`
extension.

**Tests.** ~20 focused (depends on §5.a).

### Increment 5 (M9.5) — Operator UI extension

**Scope.** Fifth tab "Realized Gross" on
`/dealer-ai-analytics/`. Sale + Delivery
operator UI (list on Vehicle detail; sale-
create form on Vehicle detail). ~15
frontend Vitest tests + ~10 backend endpoint
shape.

### Increment 6 (M9.6) — Closeout

**Scope.** Documentation-only.
Retrospective, capability matrix §7j,
roadmap flip, planning frontmatter,
session-start refresh,
`MILESTONE_10_PLANNING.md` per standing
user directive, coordinated commit + push.

---

## 8. Related documents

- `docs/PROJECT_RULES.md`
- `docs/DOC_GOVERNANCE.md`
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 9
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md`
- `docs/roadmap/MILESTONE_8_PLANNING.md`
- `docs/research/VEHICLE_CENTRIC_PIVOT.md`
  §Phase 8
- `docs/research/SALES_DEPARTMENT_MAPPING.md`
  §customer journey + §delivery workflow
- `docs/CAPABILITY_MATRIX.md` §7i
- Current source code — authoritative.

---

## 9. Load-bearing decisions summary — items requiring user review before M9.N

Every `[NEEDS-DECISION-BEFORE-M9.N]` in this
document, consolidated:

1. **§5.a — Acquisition-buyer provenance
   bundling.** Recommended: Option A (bundle
   into M9).
2. **§5.b — Sale.buyer representation.**
   Recommended: Option A (FK to
   `CustomerLead`).
3. **§5.c — Sale finance-type vocabulary.**
   Recommended: Option A (three values:
   `cash` / `retail` / `bhph`).

Decisions surface at the top of the M9
session that would first act on them —
same discipline as M5/M6/M7/M8 §9 mandates.
