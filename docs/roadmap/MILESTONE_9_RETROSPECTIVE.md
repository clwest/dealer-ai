---
title: "Milestone 9 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_100 → SESSION_105
milestone: 9
milestone_name: "Sale + delivery closure"
related:
  - docs/roadmap/MILESTONE_9_PLANNING.md
  - docs/roadmap/MILESTONE_8_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 9
---

# Milestone 9 — Retrospective

Written at Milestone 9 close (SESSION_105). Records
what was planned, what shipped, what deviated and
why, and lessons carried forward for Milestone 10.
Mirrors the `MILESTONE_8_RETROSPECTIVE.md`
structure.

## 1. Planned scope

`MILESTONE_9_PLANNING.md` at SESSION_099 defined
the milestone as closing the loop between the
vehicle side and the customer side: when a Vehicle
transitions to sold, the CRM record activates,
realized gross ties back to projected gross, and
delivery preparation is coordinated. §1.0 named
six operational questions synthesized from
SALES §customer-journey + §delivery-workflow +
INVENTORY §"To Ownership" + the four M8
deferrals (Q3 true profitability, Q6 gross-profit
trend, Q7 buyer-estimate accuracy, Q8 true
inventory turn).

§1.1–§1.7 followed with seven design memos
(Sale entity, Delivery entity, LeadVehicleInterest
annotation, gross_realized computation, three
analytics extensions, dashboard endpoint surface,
operator UI extension). §5.a–§5.c drafted three
load-bearing decisions **all flagged
`[NEEDS-DECISION-BEFORE-M9.N]`**. §7 sequenced six
increments (M9.1–M9.6).

**Original §7 sequencing shipped verbatim.** All
three §5 decisions confirmed as-recommended
(Option A × 3) at SESSION_100 open. **Five §0.a
change-log amendments landed inside increments**
— one recording the SESSION_100 sequencing
decision (combined migration `0023`), one
recording the SESSION_101 Delivery-OneToOne
interpretation clarification (mandatory OneToOne
= NOT NULL, not auto-creation), one recording the
SESSION_102 implementation notes (Q3 row shape,
`mean_gross_pct` semantics, earliest-frontline
reference, quantize fix), one recording the
SESSION_103 `LeadVehicleInterest` annotation
deferral (substrate gap — through-model doesn't
exist), and one recording the SESSION_104 UI
decisions (both Option A) + the second substrate
gap (M9.1/M9.2 had no GET companions; resolved
as `@api_view(["GET", "POST"])` method-multiplex).

## 2. What actually shipped

Every §3 compatibility item verified true;
details in the annotated checklist at
`MILESTONE_9_PLANNING.md` §3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M9.0 planning | 099 | `MILESTONE_9_PLANNING.md` (462 lines) resolving zero load-bearing decisions and leaving three for user review at M9.1 open | (in M8 close commit `34352ed`) |
| M9.1 Sale entity + gross_realized | 100 | New `Sale` model + migration `0023_sale_entity_and_buyer_fk` (fields: `dealership` FK CASCADE, `vehicle` OneToOne CASCADE, `buyer` FK `CustomerLead` SET_NULL nullable, `sale_date`, `sold_price` Decimal, `finance_type` from `SALE_FINANCE_TYPE_CHOICES` (`cash`/`retail`/`bhph`), `lender_name` optional, `gross_realized` Decimal denormalized at write). Same migration adds `VehicleAcquisition.buyer` FK to `AUTH_USER_MODEL` SET_NULL nullable (M2 additive extension per §5.a Option A) — Django's `makemigrations` combined the two changes into one atomic migration (planning had projected two). New `services/sale/` package (`computation.py::gross_realized(sale) -> Decimal` pure read verb + `record_sale(...)` transactional write with `CrossTenantSaleError` / `SaleAlreadyExistsError`). First DRF endpoint `POST /api/dealer-ai/admin/vehicles/<stock>/sale/` in new `views_sale.py`. Tenancy-carrier extension 22 → 23. **Three §5 decisions confirmed as-recommended at session open** (§5.a bundle buyer FK, §5.b Sale.buyer→CustomerLead, §5.c three finance-type values). 46 focused tests | (pending — bundled per SESSION_101 decision) |
| M9.2 Delivery entity + checklist | 101 | New `Delivery` model + migration `0024_delivery_entity` (fields: `dealership` FK CASCADE, `sale` OneToOne CASCADE mandatory per §1.2 Option A, `delivery_date` nullable, `checklist` JSONField defaulting to `_default_delivery_checklist()` (five M9.2 keys defaulted False), `temp_tag_number`, `insurance_verified` BooleanField, `insurance_verified_at` DateTimeField nullable, `notes`). Vocabulary constants (`DELIVERY_CHECKLIST_DETAIL_BOOKED` / `_FUELED` / `_TEMP_TAG` / `_INSURANCE_VERIFIED` / `_CUSTOMER_WALKTHROUGH`) at module level. New `services/delivery/` package (`workflow.py::record_delivery` transactional write + `update_checklist_item` toggle + `verify_insurance` atomic column-and-key mutation with idempotency; four error types — `CrossTenantDeliveryError` / `DeliveryAlreadyExistsError` / `SaleNotFoundForDeliveryError` / `UnknownChecklistKeyError`). Two new endpoints: `POST /admin/vehicles/<stock>/delivery/` (create) and `PATCH /admin/deliveries/<id>/` (update). Tenancy-carrier extension 23 → 24. **§1.2 Option A confirmed at session open** — interpretation clarified: mandatory OneToOne means the DB invariant "every Delivery references a Sale," NOT automatic Delivery creation on Sale write. This preserves the M9.1 boundary — no `post_save` signal on `Sale`, no coupling change in `services.sale.record_sale`. **M9 commit strategy confirmed: bundle at M9.6 per M7/M8 precedent.** 42 focused tests | (pending — bundled) |
| M9.3 Q3 + Q6 + Q8 analytics extensions | 102 | New verb `services/analytics/acquisition.py::vehicle_type_profitability(dealership, *, window_start=None, window_end=None) -> list[VehicleTypeProfitabilityRow]` (row: `make` + `model` + `sold_count` + `total_sale_gross` + `total_sold_price` + `mean_gross_pct`). New module `services/analytics/gross_profit.py::gross_profit_trend(dealership, *, window_days=90) -> list[GrossProfitPoint]` (sparse daily-bucket time series over `Sale.sale_date` + `Sale.gross_realized`). New verb `services/analytics/lifecycle_aging.py::inventory_turn(dealership, *, window_days=90) -> InventoryTurnReport` (report: `sold_count` + `mean_days` + `p50_days` + `p90_days` + `min_days` + `max_days`; reads earliest `VehicleStageEvent` with `to_stage=frontline` per sold vehicle; nearest-rank percentile method). Three new endpoints under `admin/analytics/` (`vehicle-type-profitability/`, `gross-profit-trend/`, `inventory-turn/`). M8.4 proxy verbs (`vehicle_type_recon_cost`, `days_at_frontline_proxy`) preserved with two smoke tests locking their shapes unchanged. **No new §5 decisions** (plan §1.5 fully specified at planning close). Implementation-time note: Q3 shipped with Sale-centric row shape rather than literally extending M8.4's `VehicleTypeReconCostRow` — the two verbs answer different questions (prep cost vs profit). 32 focused tests | (pending — bundled) |
| M9.4 Q7 buyer estimate accuracy | 103 | New verb `services/analytics/recon.py::buyer_estimate_accuracy(dealership, *, window_days=90, buyer_user_id=None) -> list[BuyerAccuracyRow]` (row: `buyer_user_id` + `buyer_display` + `vehicle_count` + `work_order_count` + `mean_absolute_variance_pct` + `bias_pct`). Reads M9.1 `VehicleAcquisition.buyer` FK (substrate landed at M9.1) to attribute completed `WorkOrder` variance to the buyer whose acquisition brought the vehicle in. NULL-buyer acquisitions excluded (historical rows have no provenance). Window semantics: filters `VehicleAcquisition.purchase_date` (buyer's activity window), not WO completion date. Deviation from M8 §1.8 spec (single-row → list-returning) recorded in §0.a. New DRF endpoint `GET admin/analytics/buyer-estimate-accuracy/` with optional `buyer_user_id` query arg. **`LeadVehicleInterest.stage_at_interest` annotation deferred** (substrate-gap pushback per §0.a SESSION_103 — through-model doesn't exist; scope creep to create). 20 focused tests | (pending — bundled) |
| M9.5 Operator UI extension | 104 | Fifth **Realized Gross** tab on `/dealer-ai-analytics/` wrapping Q3/Q6/Q7/Q8 via new `RealizedGrossTab.tsx` component (4 sub-sections: profitability table, gross-profit line chart, inventory-turn summary card, buyer-accuracy rank). `frontend/src/lib/analyticsApi.ts` extended with 4 new hooks (`fetchVehicleTypeProfitability`, `fetchGrossProfitTrend`, `fetchInventoryTurn`, `fetchBuyerEstimateAccuracy`) + `formatShortDate` helper. New `frontend/src/lib/saleApi.ts` (create/read/update Sale + Delivery) with local `isApi404` helper mapping 404 → null return. New `VehicleSalePage.tsx` at route `dealer-ai-inventory/:stock/sale/` (three render states: no-Sale create-form → Sale-no-Delivery start-button → Sale+Delivery checklist toggle + verify-insurance). **Backend GET dispatch additions** on M9.1/M9.2 write endpoints via `@api_view(["GET", "POST"])` method-multiplex — preserves URL names (`admin-sale-create`, `admin-delivery-create`) so every M9.1/M9.2 test continues to pass. Two `_lookup_*` helpers added. **§1.7 Decisions A + B both Option A confirmed at session open** (Q7 bundles into Realized Gross tab; Sale+Delivery = per-vehicle page). **Substrate-gap #2 resolution** (M9.1/M9.2 had no GET companions) confirmed Option A method-multiplex. 12 backend shape-lock tests + 15 frontend Vitest tests | (pending — bundled) |
| M9.6 closeout | 105 | This retrospective + `CAPABILITY_MATRIX.md` §7j + `IMPLEMENTATION_ROADMAP.md` §M9 SHIPPED flip + `MILESTONE_9_PLANNING.md` frontmatter flip + `DEALER_KIT_SESSION_START.md` refresh + `MILESTONE_10_PLANNING.md` created per standing user directive. Coordinated commit + user-authorized push of all M9.1-M9.6 stages | (TBD this session) |

## 3. Planning-doc amendments landed inside increments

**Five `§0.a` change-log amendments were required
inside M9.1–M9.5**, all surfaced at increment
open before code landed. This is above M8's two
amendments; the signal, however, is the same —
every M9 amendment was a substrate-gap or
implementation-time seam the planning doc could
not have anticipated without direct code
inspection, not a misjudged design.

1. **SESSION_100 M9.1 open — §5 decisions
   confirmed + sequencing clarified.** All three
   §5 decisions confirmed as-recommended (Option
   A × 3). Django's `makemigrations` combined
   the `Sale` model + `VehicleAcquisition.buyer`
   FK into one migration (`0023_sale_entity_and_buyer_fk`)
   — cleaner than the two-migration path
   (`0023` + `0024`) the plan had projected. §0.a
   narrowly amended to record this.

2. **SESSION_101 M9.2 open — §1.2 Delivery-
   OneToOne interpretation clarified + M9 commit
   strategy.** Option A confirmed
   (mandatory OneToOne), but interpretation
   clarified: "mandatory" means the DB invariant
   "every Delivery references a Sale," NOT
   automatic Delivery creation on Sale write.
   Preserves the M9.1 boundary. Same amendment
   confirmed bundle-at-M9.6 commit strategy per
   M7/M8 precedent.

3. **SESSION_102 M9.3 open — implementation-time
   notes.** No new user decisions (plan §1.5
   fully specified). Recorded four
   implementation-time interpretation choices:
   Q3 row shape (Sale-centric rather than
   literally extending M8.4), `mean_gross_pct`
   semantics (equal-weighted mean of per-vehicle
   margins), Q8 reference-point (earliest
   frontline event), `gross_profit_trend`
   quantize (single-row Django `Sum` returns
   unquantized Decimal — added explicit
   `.quantize(Decimal("0.01"))`).

4. **SESSION_103 M9.4 open —
   `LeadVehicleInterest` annotation deferred.**
   Planning §1.3 spec'd
   `LeadVehicleInterest.stage_at_interest` on a
   through-model. Direct inspection at session
   open: no through-model exists —
   `CustomerLead.interested_vehicles` is a
   plain `ManyToManyField(Vehicle)` backed by
   the implicit Django-generated table. Ships
   Option 2 (user-confirmed) — Q7 alone at
   M9.4; annotation deferred to a future
   increment when through-model creation is
   independently justified. Rejected: Option 1
   (create through-model + data migration + ~5
   call-site sweep — full increment's scope)
   and Option 3 (JSONField hack — loses
   per-vehicle granularity).

5. **SESSION_104 M9.5 open — UI decisions +
   substrate-gap #2 resolution.** Two UI
   decisions confirmed as-recommended (§1.7
   Decision A: Q7 bundles into Realized Gross
   tab; Decision B: Sale+Delivery lands as a
   per-vehicle dedicated page matching the
   existing `dealer-ai-inventory/:stock/<feature>`
   route pattern — the codebase does not have
   a unified vehicle-detail sub-tab shell).
   Substrate-gap #2 surfaced: M9.1/M9.2 shipped
   write-only endpoints; the M9.5 read-first
   page needs GET companions. Ships Option A
   (user-confirmed): `@api_view(["GET", "POST"])`
   method-multiplex on the existing URLs.
   Preserves URL names + every M9.1/M9.2 test.

## 4. Deviations

**Accepted improvements** (all landed inside
increments):

1. **Combined migration `0023`** — the plan
   projected two migrations
   (`0023_sale_entity` + `0024_buyer_fk`).
   Django's `makemigrations` combined both
   changes into one atomic migration. Cleaner
   than the two-migration path: one reverse
   operation, one atomic delivery. §0.a
   amended.

2. **`buyer_estimate_accuracy` list-return
   shape.** M8 §1.8 spec'd a single-row return
   type (`-> BuyerAccuracyRow`). M9.4 ships
   list-returning (`-> list[BuyerAccuracyRow]`)
   to match the dashboard's need to rank all
   buyers by accuracy in one call. Filtering
   by `buyer_user_id` recovers the single-buyer
   shape (0 or 1 rows). §0.a amended.

3. **Method-multiplex GET dispatch on existing
   write URLs.** The M9.1/M9.2 URLs originally
   dispatched `POST` only. M9.5 added `GET`
   dispatch via `@api_view(["GET", "POST"])`
   on the same URLs. Preserves URL names —
   every existing M9.1/M9.2 test continues to
   pass. Alternative rejected: separate
   `/read/` sub-URLs (fragmentation).

4. **GET dispatch tests exceed target.** M9.5
   planned ~10 backend endpoint-shape locks;
   shipped 12. Difference is exhaustive
   coverage of the auth matrix on both new
   GET paths (unauthenticated + advisor
   forbidden + owner allowed × 2 endpoints).

**Deferrals cataloged** (not dropped;
scheduled for follow-up increments or future
milestones):

- **`LeadVehicleInterest.stage_at_interest`
  annotation** — deferred at SESSION_103 open
  per §0.a amendment. Requires
  `LeadVehicleInterest` through-model
  creation (its own increment or planning
  session). Nothing about M9's Q7 code shape
  blocks a future annotation addition.
- **Sale/Delivery cross-vehicle list views**
  — plan §1.7 offered as Option B/C for the
  UI shape. M9.5 chose Option A (per-vehicle
  dedicated page). Cross-vehicle Sale +
  Delivery lists (e.g. "all sales in the
  last 7 days") land later if operator
  evidence surfaces need.
- **Dense gross-profit series** —
  `gross_profit_trend` ships sparse (dates
  with zero sales omitted). Dense-fill (one
  point per calendar day, zero-filled) lands
  later if operator evidence surfaces need.
- **`Vehicle.is_available` flip on delivery
  completion** — M9.2 did not modify M1
  `Vehicle.is_available`. Whether delivery
  completion should flip retail availability
  is deferred; today the field stays
  operator-controlled.
- **`AnalyticsCache` materialization layer**
  — carry-forward from M8. No M9 endpoint
  produced latency evidence justifying
  materialization.
- **DMS write-back integrations** — planning
  §scope-boundary explicit non-goal.
- **State e-filing integrations** — same.
- **Sales-tax computation** — belongs to
  Accounting track.
- **Portfolio-level BHPH analytics** —
  depends on Milestone 12 BHPH substrate.
- **F&I / stips / chargebacks** — Milestone
  10 substrate.

**No planned scope dropped** in the sense of a
shipped-but-broken feature or silently-missing
invariant. The `LeadVehicleInterest` annotation
was deferred with a clear re-entry path
recorded.

## 5. Compatibility

Every §3 compatibility row verified true with
inline evidence at `MILESTONE_9_PLANNING.md` §3.

- **Backend test baseline:** **3,426 pass**, 1
  skipped, 0 fail at SESSION_104 close.
  Delta: **+152 tests** over M8 close baseline
  (3,274 → 3,426); 0 regressions.
- **Frontend test baseline:** **34 pass** at
  SESSION_104 close (was 19 at M8 close;
  +15 exactly per plan).
- **M2 ledger substrate byte-for-byte
  preserved.** M9.1 `gross_realized` verb
  reads
  `vehicle_ledger.compute_totals(sale.vehicle)`
  via the existing public read path;
  `total_investment` = acquisition +
  actual costs (estimates excluded per M2
  semantic).
- **M4 WorkOrder substrate preserved.** Q7
  reads `estimated_cost` / `actual_cost`
  via existing fields; no schema change.
- **M5 lifecycle preserved.** Q8 reads
  `VehicleStageEvent.entered_at` +
  `to_stage=frontline`; no schema or
  service-layer change.
- **M8 aggregation surface preserved.**
  M8.4 proxy verbs (`vehicle_type_recon_cost`,
  `days_at_frontline_proxy`) still return
  their original shapes at M9 close — two
  smoke tests in
  `test_m9_analytics_extensions.py` lock this
  contract (`M84ProxyStillWorksAfterM93Tests`).
- **M1/M9.1 additive FK.**
  `VehicleAcquisition.buyer` shipped at M9.1
  nullable; historical acquisition rows carry
  NULL. Q7 excludes NULL rows from the
  aggregation rather than treating them as
  an anonymous bucket.
- **Tenancy carriers 22 → 24.** M9.1 added
  `Sale` (23), M9.2 added `Delivery` (24).
  Same `pre_save` autofill safety net as
  M1–M8 carriers.
- **DRF admin surface 40 → 47.** Seven new
  endpoints — one M9.1 Sale POST (with GET
  dispatch added at M9.5), two M9.2 Delivery
  (POST + PATCH; POST also GET-dispatched at
  M9.5), three M9.3 analytics extensions,
  one M9.4 Q7 endpoint. All role-gated on
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`.
- **Frontend operator routes 8 → 9.** One
  new route: `dealer-ai-inventory/:stock/sale`.
- **Fifth analytics tab added additively.**
  Existing M8.5 four tabs render M8.1–M8.4
  data unchanged after M9.5.
- **`tsc --noEmit` + `vite build` clean** at
  every M9 session close.
- **`makemigrations --check --dry-run` clean**
  after M9.2 (migration `0024`) and every
  subsequent session (M9.3–M9.6 shipped no
  schema changes).

## 6. Lessons

Sixteen lessons carried forward for Milestone
10 and beyond. Fifteen inherit from M8 §6 with
M9 evidence; one is new to M9.

1. **Increment discipline.** Every M9 sub-
   increment shipped independently verifiable
   in one session. Every session opened with
   load-bearing decisions confirmed by the
   user before code landed. Carry-forward.

2. **Backend-first architecture; frontend
   never owns business rules.** M9.1–M9.4
   shipped zero frontend. M9.5 wired the UI
   as a pure consumer of the M8 + M9
   endpoint surface. Every dollar + percent
   figure travels as a string on the wire
   and stays a string in the frontend.
   `formatMoney` / `formatPercent` /
   `formatShortDate` are display-only. The
   frontend role-gate is UX convenience;
   backend is authoritative. Carry-forward.

3. **Provider-neutral boundaries.** No new
   provider dependencies added by M9.
   Reused recharts (M8.5) for the new
   line/summary chart. No new LLM
   integration in M9. Carry-forward.

4. **Service ownership — one authoritative
   write path per operation.** M9.1
   `record_sale` owns Sale writes; M9.2
   `record_delivery` / `update_checklist_item`
   / `verify_insurance` own Delivery writes;
   the endpoint layer is thin translation.
   No business logic in views. Carry-forward.

5. **Local vs production parity.** M9 shipped
   no new runtime dependencies. Same test-
   mode gates as M8 apply. Carry-forward.

6. **Honest verification reporting.** Every
   M9 endpoint carries a role-gate matrix
   test. Verbs distinguish "no signal"
   (`None` field / empty list) from
   "distribution happens to be zero." M9.2
   `verify_insurance` locked idempotent —
   second call preserves original
   timestamp. Carry-forward.

7. **Storage-first / safer-direction
   deletion.** Not exercised in M9 (no
   deletion paths added). Carry-forward.

8. **Load-bearing decisions get user review
   BEFORE code.** Every M9 session opened
   with required decisions surfaced to the
   user before code landed. Five §0.a
   amendments (M9.1 × 1 sequencing, M9.2 ×
   1 interpretation, M9.3 × 1 implementation
   notes, M9.4 × 1 deferral, M9.5 × 1
   substrate-gap resolution) — all landed at
   session open. Zero mid-implementation
   churn. Carry-forward.

9. **Distinct domain errors → distinct
   behaviors.** M9 endpoints return 400 for
   malformed args + unknown checklist keys,
   404 for missing / cross-tenant vehicles
   or deliveries, 409 for duplicate Sale /
   Delivery + workflow-order failures
   (SaleNotFoundForDeliveryError). Four
   distinct error classes per M9.1 + M9.2
   service module. Carry-forward.

10. **Read-model properties are pure reads.**
    Preserved. M9 `gross_realized` verb is
    pure; M9.3 aggregation verbs are pure;
    M9.4 Q7 is pure. `Sale.gross_realized`
    denormalized column populated at write
    time by `record_sale` — the pure
    `gross_realized(sale)` verb re-derives
    from ledger on demand for correctness
    verification.

11. **Additive extension over fork.** M9.3
    added true `vehicle_type_profitability`
    +  `inventory_turn` verbs alongside the
    M8.4 proxy verbs — two smoke tests
    (`M84ProxyStillWorksAfterM93Tests`) lock
    the proxies' unchanged shapes. M9.5
    added GET dispatch to the M9.1/M9.2
    URLs without renaming or replacing —
    every write-path test continues to pass.
    Textbook additive extension. Carry-
    forward.

12. **Zero-planning-amendment sessions are
    a signal — with the M8 nuance
    amplified.** M9 required five §0.a
    amendments (up from M8's two). The
    signal is not "planning quality
    dropped" — every M9 amendment was a
    substrate-gap or implementation-time
    seam surfaced at session open by direct
    code inspection. The lesson: substrate
    assumptions in planning docs
    (especially "X exists as a through-
    model" or "X endpoint supports GET")
    need explicit "verified against current
    schema at planning time" annotations,
    or the downstream increments carry the
    discovery cost. Carry-forward from M8
    §6 lesson 12 amended.

13. **Two-tier customer-visibility gate.**
    Not exercised in M9 (all endpoints
    admin-scoped). Preserved.

14. **Prior-increment count assertions use
    `>=` not `==`.** M9.1 + M9.2 tests
    used `>=23` and `>=24` for tenancy
    carrier counts. The pattern is now
    project posture. Zero test-relaxations
    required at any M9 session open.

15. **Verify handoff / planning claims via
    direct inspection before acting.**
    Applied twice at M9: SESSION_103 opened
    with a `grep LeadVehicleInterest` that
    surfaced the substrate gap the planning
    doc assumed away; SESSION_104 checked
    the M9.1/M9.2 endpoint file and found
    no GET dispatch, surfacing substrate-
    gap #2. Both gaps caught at session
    open, both resolved with user
    confirmation before code landed.
    Carry-forward from M8 lesson 15 with
    M9 evidence — this is the exact
    pattern the M8 lesson codified.

16. **[NEW] Substrate-gap pushback is a
    productive session-open pattern.** M9
    hit two substrate gaps (both surfaced
    at session open). In both cases, the
    right response was to pause code, tell
    the user what shipped vs. what the
    plan assumed, offer explicit options
    (Option 1 = do the scope creep, Option
    2 = defer with re-entry path, Option 3
    = hack) with a recommendation, and
    wait for user confirmation. Both
    conversations resolved in a single
    turn. The alternative (silently
    picking one and shipping) would have
    either created scope creep the plan
    didn't authorize (Option 1 in
    SESSION_103; separate `/read/` URLs in
    SESSION_104) or shipped a degraded
    feature (Option 3 hacks). The rule:
    when a planning-time substrate
    assumption fails direct inspection,
    the correct action is
    plan-scoped-pushback with explicit
    trade-offs, not a silent workaround.
    **This is the M9-specific new lesson.**
    New at M9.

---

*Written by the SESSION_105 (M9.6)
closeout pass.*
