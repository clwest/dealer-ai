---
title: "Milestone 8 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-01
sessions: SESSION_094 → SESSION_099
milestone: 8
milestone_name: "Operational intelligence"
related:
  - docs/roadmap/MILESTONE_8_PLANNING.md
  - docs/roadmap/MILESTONE_7_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 8
---

# Milestone 8 — Retrospective

Written at Milestone 8 close (SESSION_099). Records
what was planned, what shipped, what deviated and
why, and lessons carried forward for Milestone 9.
Mirrors the `MILESTONE_7_RETROSPECTIVE.md`
structure.

## 1. Planned scope

`MILESTONE_8_PLANNING.md` at SESSION_093 defined
the milestone as answering the ten operational
questions synthesized from the research corpus
(INVENTORY §"To Ownership" + RECON §"To Ownership"
+ VCP §"Operational intelligence"). Q1 → Q10 as
enumerated in §1.0 of the planning doc, with Q6
(gross-profit trend) noted as depending on
Milestone 9 Sale substrate and Q8 (inventory
turn) noted as requiring a proxy pending that
same substrate.

§1 followed with ten aggregation entries + one
dashboard-endpoint entry + one operator-UI
entry. §2 skeleton enumerated existing surfaces
M8 touched. §3 defined the compatibility
checklist. §5.a-§5.e drafted five load-bearing
decisions — **four flagged
`[NEEDS-DECISION-BEFORE-M8.1]`** requiring user
review before code landed. §7 sequenced six
increments (M8.1-M8.6).

**Original §7 sequencing (M8.1 → M8.6) shipped
verbatim.** All four §9 decisions confirmed
as-is at SESSION_094 open (compute-on-request
hybrid / `SlaBreachRecord` model / recharts /
five-aggregation shape). **Two `§0.a` change-log
amendments landed inside increments** — Q7
deferral at SESSION_095 open and Q1 scope
reallocation + Q3 proxy at SESSION_097 open.
Both were substrate-gap decisions the planning
doc did not have visibility into at draft time.

## 2. What actually shipped

Every §3 compatibility item verified true;
details in the annotated checklist at
`MILESTONE_8_PLANNING.md` §3.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M8.0 planning | 093 | `MILESTONE_8_PLANNING.md` (552 lines) resolving zero load-bearing decisions and leaving four for user review at M8.1 open | `6ea221d` |
| M8.1 analytics infra + Q1 | 094 | New `SlaBreachRecord` model + migration `0022` (`(dealership, kind, -detected_at)` composite index + `(work_order, kind, detected_at_date)` unique constraint anchoring M7.4 daily-scan idempotency). Tenancy-carrier extension 21 → 22. M7.4 `detect_sla_breaches` verb-extension writes `SlaBreachRecord` per breach via `get_or_create` (log warning contract preserved). New `services/analytics/` package (`__init__.py` facade + `acquisition.py::recon_cost_per_source` verb — Q1). `views_analytics.py` module + first endpoint at `/api/dealer-ai/admin/analytics/recon-cost-per-source/` (role-gated on `IsReconManagerSalesManagerOrOwnerAtActiveDealership`). Query-arg helper `_parse_iso_date_or_none`. **Four §9 decisions confirmed as-recommended at session open** (compute-on-request hybrid, `SlaBreachRecord` model, recharts deferred to M8.5, five-aggregation shape). One M7.3 test relaxed in-place (`test_carrier_count_is_twenty_one` → `test_carrier_count_at_least_twenty_one`) codifying M7 §6 lesson 14. 42 focused tests | `34352ed` |
| M8.2 vendor performance | 095 | New `services/analytics/recon.py` with `vendor_performance` verb (Q2 + Q4). Row carries vendor_slug + vendor_name + completed_count + mean_completion_days (nullable, clock-skew-clamped) + mean_variance_pct (nullable Decimal, mean-absolute-percent quantized to 2dp) + over_budget_count. Filters `status=completed AND venue=outsourced AND vendor IS NOT NULL`. Window on `completed_at.date()`. Sort by count desc + slug asc. Aggregation runs in a private `_VendorState` accumulator — keeps "when do we skip this WO?" branches readable without SQL COALESCE gymnastics. `views_analytics.py` extended with `admin_analytics_vendor_performance` endpoint. **First `§0.a` amendment landed at session open** — Q7 (`buyer_estimate_accuracy`) deferred: the planning doc assumed acquisition-buyer provenance ("`buyer_user_id`") exists on the M2 ledger; direct inspection shows no such FK anywhere. Q7 re-entry deferred to a future increment when buyer-provenance schema ships. 24 focused tests | `34352ed` |
| M8.3 aging + SLA patterns | 096 | New `services/analytics/lifecycle_aging.py::stage_aging_trend` (Q5 + Q9) — time-series of `snapshot_at` + `vehicle_count` + `p50_days` + `p90_days` from M7.3 `StageAgingSnapshot` filtered to `(dealership, stage, window)`. Unknown `stage` raises `ValueError` (endpoint → 400) rather than silent-empty. New `services/analytics/sla_breaches.py::breach_patterns` (Q10) — `BreachPatternReport` with `total_breach_count` + `average_breach_days` (nullable Decimal 2dp) + `top_vendors_by_breach_count` (top-5, name-tiebreak) + `breaches_by_kind` (every kind observed). Two new endpoints. New shared helper `_parse_positive_int_or_default` for `window_days` parsing. No new models. 31 focused tests | `34352ed` |
| M8.4 acquisition + frontline proxies | 097 | New `services/analytics/acquisition.py::vehicle_type_recon_cost` (Q3 proxy) — rows grouped by `(make, model)` with `vehicle_count` + `total_recon_cost` + `mean_recon_cost` (2dp quantized). Same shape as Q1's `SourcePerformanceRow`. New `services/analytics/lifecycle_aging.py::days_at_frontline_proxy` (Q8 proxy) — window mean p50 / p90 + latest_vehicle_count + latest_snapshot_at. Empty window → every derived field `None`. Two new endpoints. **Two `§0.a` amendments landed at session open** — (1) Q1 scope reallocation (Q1 already shipped at M8.1 as the substrate proof-of-concept; M8.4 real scope is Q3 + Q8); (2) Q3 substrate gap → ship proxy (Option A), naming honest (`vehicle_type_recon_cost` not `vehicle_type_profitability`). 27 focused tests | `34352ed` |
| M8.5 operator UI + Vitest infra | 098 | New `/dealer-ai-analytics/` route + four-tab operator page (Acquisition & Recon Cost / Vendor Performance / Lifecycle Aging / SLA Breach Patterns). Tab-state persisted via URL hash. `frontend/src/lib/analyticsApi.ts` (6 endpoint wrappers + 3 display helpers: `formatMoney`, `formatPercent`, `formatSnapshotAt`). Five new components under `src/components/analytics/` (shared `AnalyticsSection` load-state shell + 4 tab bodies). Sidebar nav item "Analytics" with `BarChart3` lucide icon. Data-fetching pattern matches the existing 17-page convention (plain `useEffect + useState + authFetch`). **Frontend test framework introduced from scratch** — `vitest` + `@vitest/coverage-v8` + `jsdom` + `@testing-library/react` + `@testing-library/jest-dom` + `@testing-library/user-event`. New `vitest.config.ts` + `src/test/setup.ts` + `npm test` / `npm run test:watch` scripts. Prior handoff wrongly claimed "Vitest already the M6 baseline" + "React Query per tab" — both caught by direct `package.json` inspection before install ran (see M8 lesson 15 below). recharts `^3.10.1` installed (bundle 618 kB → 1,069 kB / 293 kB gzip — expected). 19 focused Vitest tests (new baseline — project had zero frontend tests before this session). **Three session-open decisions confirmed as-recommended** (4-tab grouping, per-tab fetch, Vitest). Backend unchanged | `34352ed` |
| M8.6 closeout | 099 | This retrospective + `CAPABILITY_MATRIX.md` §7i + `IMPLEMENTATION_ROADMAP.md` §Milestone 8 flip + `MILESTONE_8_PLANNING.md` frontmatter flip + `DEALER_KIT_SESSION_START.md` refresh + `MILESTONE_9_PLANNING.md` created per standing user directive. Coordinated commit + user-authorized push of all M8.1-M8.6 stages | `34352ed` |

## 3. Planning-doc amendments landed inside increments

**Two `§0.a` change-log amendments were required inside
M8.1-M8.5**, both surfaced at increment open before code
landed. This inverts M7's zero-amendment posture but the
signal is different — every M8 amendment was a
substrate-gap the planning doc could not have
anticipated without prior implementation, not a
misjudged design.

1. **SESSION_095 M8.2 open — Q7 deferred.** Planning
   §1.8 spec'd `buyer_estimate_accuracy(dealership,
   buyer_user_id, ...)` reading "acquisition buyer
   provenance (M2 ledger)." Direct inspection at
   session open: no buyer FK anywhere in M1-M7
   schema. `VehicleAcquisition.buyer_fees` is a
   Decimal (auction-house buyer's-premium fee),
   not a person. Confirmed deferral (Option A) —
   Q7 lands when acquisition-buyer provenance
   ships. Rejected: adding FK now (breaks M8.2
   "no new models" scope bound) + `created_by`
   proxy (semantically wrong — data-entry person,
   not decision-maker).

2. **SESSION_097 M8.4 open — Q1 reallocated + Q3
   → proxy.** Two related amendments:
   (a) §7 M8.4 originally listed "Q1 + Q3 + Q8";
   Q1 already shipped at M8.1 as the substrate
   proof-of-concept — revised M8.4 scope Q3 + Q8
   only.
   (b) §1.2 spec'd Q3 as "which vehicle types
   produce the highest **profit**?" — true
   profit requires M9 Sale substrate. Confirmed
   proxy (Option A): new verb
   `vehicle_type_recon_cost` grouped by
   `(make, model)`. Naming deliberately honest —
   the M9 rewrite path can add
   `vehicle_type_profitability` alongside
   without disturbing this verb's callers.

**Three implementation-time seam decisions** were
surfaced + confirmed at session opens without
requiring planning amendments because the planning
doc left them deliberately open (or the SESSION_098
handoff had front-loaded them):

1. **SESSION_098 M8.5 open — dashboard grouping.**
   Chose Option A (4 tabs — Acquisition & Recon
   Cost, Vendor Performance, Lifecycle Aging,
   SLA Breach Patterns) over 7 tabs (one per
   aggregation).

2. **SESSION_098 M8.5 open — data-fetching
   pattern.** Chose Option A (plain
   `useEffect + useState + authFetch` matching
   the existing 17-page convention) over
   introducing React Query.

3. **SESSION_098 M8.5 open — frontend test
   framework.** Chose Option A (install Vitest +
   testing-library from scratch) over
   Playwright-happy-path or skip-tests. The
   project had zero frontend tests before this
   decision.

## 4. Deviations

**Accepted improvements** (all landed inside
increments):

1. **SESSION_094 M7.3 test relaxation** — the
   `test_carrier_count_is_twenty_one` absolute-
   count assertion naturally staled when M8.1
   extended `_TENANT_CARRIER_MODEL_NAMES` 21 →
   22. Relaxed to
   `test_carrier_count_at_least_twenty_one`
   (`>=` not `==`). Codifies M7 §6 lesson 14
   at every future prior-milestone floor.

2. **SESSION_098 M8.5 handoff-correction
   surfacing.** Prior handoff (SESSION_097)
   asserted two frontend facts that were wrong:
   (a) "Vitest already the M6 baseline" — actually
   no test framework in `devDependencies`, only
   Playwright installed but never wired; (b)
   "React Query per tab" — actually no
   `@tanstack/react-query` in the project. Both
   caught by direct `frontend/package.json`
   inspection before the "install recharts" step
   ran. Neither delayed shipping; both are
   documented in the SESSION_098 handoff's
   "corrections surfaced" block and codified as
   M8 lesson 15 below.

3. **M7.4 verb additive extension.** The M8.1
   verb-extension writing `SlaBreachRecord` rows
   preserved every M7.4 test (log warnings still
   emit; every prior contract holds). Model of
   the M4-M6 lesson-11 "additive extension over
   fork" applied to a service verb.

**Deferrals cataloged** (not dropped; scheduled
for follow-up increments or future milestones):

- **Q6 gross-profit trend** — planning §1.6
  explicitly cites Milestone 9 as intended home
  (no Sale substrate at M8 time). Enters M9
  scope alongside the Sale model itself.
- **Q7 buyer estimate accuracy** — deferred at
  SESSION_095 open per §0.a amendment. Re-enters
  as a standalone increment when acquisition-
  buyer provenance schema ships (dedicated
  planning session + M2 additive extension).
- **True inventory turn (Q8)** — M8.4 shipped
  days-at-frontline proxy pending M9 Sale
  substrate. True inventory-turn (days from
  acquisition to sale) lands at M9.
- **True vehicle-type profitability (Q3)** —
  M8.4 shipped recon-cost proxy pending M9 Sale
  substrate. True profitability (recon cost vs
  realized gross per type) lands at M9.
- **`AnalyticsCache` materialization layer** —
  §5.a Option C hybrid: compute-on-request v1,
  materialize when operator evidence surfaces
  latency pain. No M8 endpoint has yet produced
  that evidence.
- **External BI-tool exports** — planning §1.0
  explicit non-goal. If operators need CSV,
  add later.
- **Portfolio-level BHPH analytics** — depends
  on Milestone 12 BHPH substrate.
- **Predictive ML** — VCP explicitly rules ML
  out of M8.
- **Real-time dashboards** — planning §1.0
  explicit non-goal. Aggregations refresh
  on-demand.
- **Playwright end-to-end tests for the
  analytics UI** — Vitest render tests shipped
  at M8.5; Playwright happy-path deferred.
  Playwright is installed but never wired to a
  test file.

**No planned scope dropped** in the sense of a
shipped-but-broken feature or silently-missing
invariant.

## 5. Compatibility

Every §3 compatibility row verified true with
inline evidence at `MILESTONE_8_PLANNING.md` §3.

- **Backend test baseline:** **3,274 pass**, 1
  skipped, 0 fail at SESSION_098. Delta: **+124
  tests** over M7 close baseline (3,150 → 3,274);
  0 regressions after the M7.3-carrier-count
  test relaxation at M8.1 open.
- **Frontend test baseline:** **19 pass** (new
  — project had zero frontend tests before
  M8.5).
- **`Vehicle.is_available` schema + values
  unchanged.**
- **M2 ledger substrate byte-for-byte
  preserved.** M8 verbs read
  `VehicleAcquisition` + `VehicleCost` +
  `Vehicle` (make/model) via `.values()`; no
  ledger primitive touched.
- **M3-M6 substrate preserved.** No API
  changes.
- **M7 async substrate preserved.** M7.4 verb
  extended additively (persistence side effect
  via `get_or_create`; every prior contract
  holds). All four Beat schedule entries
  unchanged; `JobRunLog` write cadence
  unchanged.
- **Tenancy carriers 21 → 22.** M8.1 added
  `SlaBreachRecord`. Same `pre_save` autofill
  safety net as M1-M7 carriers.
- **DRF admin surface 34 → 40.** Six new
  analytics endpoints — all under
  `/api/dealer-ai/admin/analytics/`, all role-
  gated on the same
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  class from M4.
- **Frontend operator routes 7 → 8.** One new
  route: `/dealer-ai-analytics/`.
- **Frontend deps added at M8.5:** `recharts`
  (production), `vitest` +
  `@vitest/coverage-v8` + `jsdom` +
  `@testing-library/react` +
  `@testing-library/jest-dom` +
  `@testing-library/user-event` (dev). Bundle
  618 kB → 1,069 kB (293 kB gzip) — expected
  for recharts.
- **`tsc --noEmit` + `vite build` clean** at
  every M8 session close.
- **`makemigrations --check --dry-run` clean**
  after M8.1 (migration `0022`) and every
  subsequent session.

## 6. Lessons

Fifteen lessons carried forward for Milestone 9
and beyond. Fourteen inherit from M7 §6 with M8
evidence; one is new to M8.

1. **Increment discipline.** Every M8 sub-
   increment shipped independently verifiable in
   one session. Every session opened with load-
   bearing decisions confirmed by the user
   before code landed. Carry-forward from M7
   §6 lesson 1.

2. **Backend-first architecture; frontend never
   owns business rules.** M8.1-M8.4 shipped
   zero frontend. M8.5 wired the UI as a pure
   consumer of the already-shipped endpoint
   surface. The frontend role-gate is a UX
   convenience; server-side is authoritative.
   Carry-forward from M7 §6 lesson 2.

3. **Provider-neutral boundaries.** No new
   provider dependencies added by M8
   aggregations. Analytics runs against the
   already-shipped M2/M4/M7 substrate. recharts
   is a UI library, not a provider. Carry-
   forward from M7 §6 lesson 3.

4. **Service ownership — one authoritative
   write path per operation.** M8.1's
   `SlaBreachRecord` write path is the M7.4
   verb-extension only; no other code writes
   to that table. Q3 + Q8 proxies read but
   never mutate substrate. Carry-forward from
   M7 §6 lesson 4.

5. **Local vs production parity.** M8 shipped
   no new runtime dependencies (recharts is
   build-time). Same test-mode gates as M7
   apply. Carry-forward from M7 §6 lesson 5.

6. **Honest verification reporting.** Every M8
   endpoint carries a role-gate matrix test.
   Verbs distinguish "no signal" (`null` /
   empty list) from "average is zero." M8.1
   verb-extension idempotency verified at both
   the DB constraint level and the
   `get_or_create` call level. Carry-forward
   from M7 §6 lesson 6.

7. **Storage-first / safer-direction deletion.**
   Not exercised in M8 (no deletion paths
   added). Carry-forward from M7 §6 lesson 7 in
   its unexercised form.

8. **Load-bearing decisions get user review
   BEFORE code.** Every M8 session opened with
   required decisions surfaced to the user
   before code landed. Two required §0.a
   amendments (SESSION_095 + SESSION_097) but
   both surfaced at session open — neither
   caused mid-implementation churn. Carry-
   forward from M7 §6 lesson 8, with the M8
   nuance that even substrate-gap decisions
   that the planning doc could not have
   anticipated should be surfaced at the
   session opening.

9. **Distinct domain errors → distinct
   behaviors.** M8 endpoints return 400 for
   malformed query args, 401/403 for auth
   failures, 200 with empty payload for "no
   signal" states. `ValueError` from the verb
   (unknown stage) → 400. Carry-forward from
   M7 §6 lesson 9 in its HTTP form.

10. **Read-model properties are pure reads.**
    Preserved. M8 verbs read via `.values()` /
    `.aggregate()`; every aggregation is
    a module-level function with no side
    effects (except the M8.1 verb-extension,
    which is deliberately additive persistence).

11. **Additive extension over fork.** M8.1
    verb-extension is a textbook example
    (persistence side effect added; existing
    return shape + log-emit contract preserved
    verbatim). M8.2-M8.4 aggregations landed
    inside existing analytics-package modules
    (`acquisition.py` grew Q3 alongside Q1;
    `lifecycle_aging.py` grew Q8 alongside
    Q5+Q9). No fork. Carry-forward from M7 §6
    lesson 11.

12. **Zero-planning-amendment sessions are a
    signal — with a nuance.** M8 required
    two §0.a amendments (M8.2 + M8.4). Both
    were substrate-gap discoveries — the
    planning doc drafted at SESSION_093 could
    not know that `VehicleAcquisition.buyer`
    doesn't exist without direct inspection.
    The nuance for M9 planning: substrate
    assumptions in a planning doc need explicit
    "verified against current schema at
    planning time" annotations, or the
    downstream increments carry the discovery
    cost. Carry-forward from M7 §6 lesson 12
    with amendment.

13. **Two-tier customer-visibility gate.** Not
    exercised in M8 (all endpoints are admin-
    scoped). Preserved for future milestones.
    Carry-forward from M7 §6 lesson 13.

14. **Prior-increment count assertions should
    use `>=`, not `==`.** M8.1 applied this
    at session open to the M7.3 carrier-count
    test. Zero subsequent M8 test-relaxations
    required (the pattern is now the
    established default). Carry-forward from
    M7 §6 lesson 14 — the pattern is now
    project posture, not an M7-specific
    finding.

15. **[NEW] Verify handoff claims about
    project-state via direct inspection
    before acting.** SESSION_097 handoff
    asserted two frontend facts that were
    wrong ("Vitest already the M6 baseline"
    + "React Query per tab"). Both caught at
    SESSION_098 open by reading
    `frontend/package.json` before the
    install command ran. Neither delayed
    shipping; both would have caused wrong
    tooling installs + a partial rollback.
    **The rule:** handoff assertions about
    project-state (installed deps, existing
    tests, framework baselines) are
    hypotheses to verify, not facts to
    consume. Ten seconds of `cat package.json`
    or `grep -r` beats a wrong install every
    time. New at M8.

---

*Written by the SESSION_099 (M8.6) closeout
pass.*
