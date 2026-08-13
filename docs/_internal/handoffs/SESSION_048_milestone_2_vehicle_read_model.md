---
title: "SESSION_048 handoff — Milestone 2 · Increment 3 (Vehicle ledger read model)"
status: historical
type: handoff
date: 2026-07-31
session: 048
milestone: 2
milestone_status: in_progress
increment: 3
increment_status: shipped
commit: e25ab4d
---

# SESSION_048 — Milestone 2 · Increment 3 (M2.3 — Vehicle ledger read model)

## What shipped

One thing: the `Vehicle` model became a thin read-model over the
ledger. Nine per-total `@property` accessors + `days_in_inventory`
+ `@cached_property ledger_totals` — all delegating to
`services/vehicle_ledger.compute_totals`. No business logic in
`Vehicle`. No duplicated math. No new migrations. No API. No
frontend. No safety-stack changes. No changes to the M2.2
`total_investment` semantic contract.

### Properties added to `Vehicle`

**One cached backing store:**

- `@cached_property ledger_totals` — delegates to
  `services.vehicle_ledger.compute_totals(self, dealership=self.dealership)`.
  Runs exactly one lookup per Vehicle instance; every downstream
  property reads a field off the cached `LedgerTotals`.

**Nine delegator properties (all thin one-liners):**

- `total_investment` → `LedgerTotals.total_investment`
- `projected_total_investment` → `LedgerTotals.projected_total_investment`
- `acquisition_total` → `LedgerTotals.acquisition_total`
- `actual_cost_total` → `LedgerTotals.actual_cost_total`
- `estimated_cost_total` → `LedgerTotals.estimated_cost_total`
- `flooring_total` → `LedgerTotals.flooring_total`
- `recon_total` → `LedgerTotals.recon_total`
- `administrative_total` → `LedgerTotals.administrative_total`
- `photography_total` → `LedgerTotals.photography_total`

**One temporal metric (`@property`, not routed through
`ledger_totals`):**

- `days_in_inventory` — returns `today - acquisition.purchase_date`
  in whole days when an acquisition exists, `None` otherwise.
  Uses `django.utils.timezone.now().date()` for "today" (respects
  `settings.TIME_ZONE`). Clamps a future `purchase_date` to `0`
  (surfaces data-entry error without breaking aging math).

**Load-bearing fallback decision for `days_in_inventory`:**
returns `None` when no acquisition exists. The alternative — a
fallback to `Vehicle.imported_at` — was **rejected** because for a
dealer onboarded with existing inventory, `imported_at` is when
the row hit our DB, not when the vehicle physically arrived on
the lot. A misleading fallback would produce wrong aging buckets
in the ledger UI (M2.7) and wrong curtailment planning in the
accrual command (M2.4). `None` forces the operator to record the
acquisition — a documented invariant of Milestone 2's ledger
model. See the `days_in_inventory` docstring in
`backend/dealer_ai/models.py`.

### Caching strategy

**One `@cached_property`, one lookup, many reads.**

- First access to any of the nine per-total properties triggers
  `ledger_totals` → `compute_totals` → seven queries (see
  breakdown below).
- Every subsequent per-total read on the same instance costs
  zero queries.
- `days_in_inventory` and `ledger_totals` both access
  `vehicle.acquisition`. Django's OneToOne reverse-accessor
  cache means whichever runs first primes the other's
  acquisition access; the second is free.
- Cache invalidation: writes made *after* a `ledger_totals`
  read on the same instance are NOT reflected. Callers must
  refetch or `del vehicle.ledger_totals`. In the
  request/response cycle each request builds a fresh instance,
  so this is a docs-only concern for library callers.

### Query verification (assertNumQueries)

Locked by `CachedPropertyRunsOnce` (5 tests):

- **First `ledger_totals` read: 7 queries.** Breakdown:
  1. Lazy Dealership load (`vehicle.dealership` — Django only
     stores `dealership_id` on Vehicle fetch, so the related
     row loads on first attribute access).
  2. Acquisition lookup (`_acquisition_total` in the service).
  3. Flooring aggregate (`SUM(amount) WHERE category IN
     FLOORING_CATEGORIES AND NOT is_estimate`).
  4. Recon aggregate.
  5. Admin aggregate.
  6. Photography aggregate.
  7. Estimate aggregate across all categories.
- **Second `ledger_totals` read: 0 queries.**
- **Nine per-total reads after priming: 0 queries.**
- **First property read on a fresh instance: 7 queries, then 0
  for every subsequent per-total read.**
- **Cache is per-instance, not per-class:** two distinct Vehicle
  instances each get their own primed cache.

If a future optimization drops the +1 Dealership lazy-load (e.g.
by refactoring `compute_totals` to accept `dealership_id: int`
instead of a Dealership instance), the "7" numbers above drop to
"6." That refactor is intentionally NOT in M2.3 scope — the M2.2
service contract is preserved verbatim.

### N+1 preview for future list pages

M2.6 will introduce API endpoints; M2.7 will introduce an
inventory ledger UI. Both may render totals across many vehicles.
The naive implementation (loop over vehicles, read
`total_investment` on each) would produce
`N × 7 = O(N)` queries per page — a real N+1.

**Not fixed in M2.3.** Documented instead. Options for the M2.6 /
M2.7 sessions:

- List views render summary rows using a bulk aggregate query
  (`VehicleCost.objects.filter(...).values("vehicle_id").annotate(Sum("amount"))`)
  rather than looping through property accesses.
- Add a `Vehicle.objects.with_ledger_totals()` custom queryset
  method (deferred; M2.7 concern).
- Detail views (one Vehicle) are unaffected — one page = one
  vehicle = 7 queries once, 0 for every read after.

Documenting rather than premature-optimizing per the SESSION_048
brief.

## Tests added — 29 new, all passing

- `PropertyDelegatesToLedgerService` (10 tests) — locks the
  delegation contract for each of the 10 read properties
  (including `ledger_totals` itself). Every property matches the
  underlying `compute_totals` output field-for-field.
- `CachedPropertyRunsOnce` (5 tests) — `assertNumQueries`
  invariants above.
- `ReadModelHandlesEmptyStates` (1 test) — bare vehicle returns
  `ZERO` on every property, never `None`.
- `ReadModelReflectsMixedLedger` (1 test) — actual vs. estimated
  semantic survives the read model.
- `ReadModelHandlesReversingEntry` (2 tests) — negative
  reversing row collapses the net through the read model.
- `DaysInInventoryTemporalMetric` (4 tests) — no acquisition →
  `None`; recent acquisition → positive days (with a small
  midnight-crossing tolerance); today → 0; future date → 0
  (clamped).
- `DaysInInventoryUsesOneToOneCache` (1 test) — reading
  `days_in_inventory` after `ledger_totals` primes zero
  additional queries.
- `VehicleReadModelTenantIsolation` (4 tests) — normal reads,
  two-tenant data isolation (A's costs don't appear in B's
  totals), no ambient-state lookup, service-layer
  `CrossTenantLedgerError` still fires when someone bypasses
  the read model.
- `PropertiesAreSideEffectFree` (1 test) — reading any property
  creates zero rows (no lazy acquisition upsert).

Total: 29 tests, 8 classes.

## Backend baseline

- **`python3 manage.py test dealer_ai` → 1,569 pass** (1,540
  baseline + 29 new M2.3 tests), 1 skipped, 0 fail. Zero
  regressions.
- **`makemigrations dealer_ai --check --dry-run` → "No changes
  detected in app 'dealer_ai'".** Zero schema drift.

## Compatibility result

Every Milestone 1 invariant + every M2.1 + M2.2 invariant holds.
Explicit rechecks:

- Safety pipeline unchanged (no changes to `services/llm_safety.py`).
- Auth substrate unchanged (no changes to `permissions.py`,
  `services/tenancy.py`, `settings.py::REST_FRAMEWORK`).
- Payment engine unchanged.
- Public routes unchanged (no new endpoints; `/`, `/assistant`,
  `/showroom`, `/embed/assistant`, `/login` still resolve without
  a session).
- `services/vehicle_ledger.py` M2.2 contract preserved verbatim.
- `LedgerTotals` shape unchanged (still 9 frozen fields).
- `total_investment` semantic contract preserved (excludes
  `is_estimate=True`).
- Frontend untouched.

## Documentation updates

Per the SESSION_048 brief:

- `docs/roadmap/MILESTONE_2_PLANNING.md` §1.3 gained a brief
  annotation clarifying the Vehicle-as-read-model / service-as-
  business-layer separation. §7.b M2.3 row updated with
  "SHIPPED at SESSION_048" + summary of what shipped.
- No new documentation created (per brief).

## Files touched this session

**Backend (1 file modified, 1 file new):**

- `backend/dealer_ai/models.py` — added imports (`cached_property`,
  `Optional`, `date`, `timezone`) and the `Vehicle` read-model
  properties. 10 new `@property` accessors + 1 `@cached_property`
  + 1 helper (`_purchase_date_or_none`). No changes to any
  existing field, model, migration, or constant.
- `backend/dealer_ai/tests/test_vehicle_computed_properties.py` —
  **new file**, 29 tests across 8 classes.

**Docs (3 files):**

- `docs/roadmap/MILESTONE_2_PLANNING.md` — §1.3 read/write layer
  annotation + §7.b M2.3 row marked SHIPPED.
- `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md` —
  this file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_049 =
  M2.4.

**No changes to:** `services/vehicle_ledger.py`, `admin.py`,
migrations, urls.py, views.py, settings.py, permissions.py,
tenancy.py, llm_safety.py, payment_engine.py, dealer_config.py,
or any frontend file.

## Exact recommended scope for M2.4 (SESSION_049)

**M2.4 — Floor-plan math, APR configuration, and accrual
command.** Per `MILESTONE_2_PLANNING.md` §7.b · M2.4. Do NOT
scope in M2.5 (safety scrub), M2.6 (API), M2.7 (UI), or M2.8
(closeout).

### In scope

1. **`services/payment_engine.py::daily_floor_plan_interest`**
   — a pure helper. Signature:
   `daily_floor_plan_interest(principal: Decimal, apr: Decimal,
   days_elapsed: int) -> Decimal`. One-line formula:
   `principal * (apr / Decimal("365")) * days_elapsed`.
   Handles:
   - `apr == 0` → returns `Decimal("0")`.
   - Negative `days_elapsed` → returns `Decimal("0")`.
   - Preserves Decimal precision (no float coercion).

2. **`services/dealer_config.py::get_floor_plan_apr`** — new
   layered resolver:
   `get_floor_plan_apr(dealership: Optional[Dealership] = None)
   -> Decimal`. Layers, in priority order:
   - `DealerOnboardingProfile.floor_plan_apr` (new field, see
     item 3) when non-null and > 0.
   - `settings.DEALER_AI_FLOOR_PLAN_APR` (env-driven, see item
     5) when non-empty.
   - `Decimal("8.5")` — Copper Canyon baseline per planning §1.4.

3. **`DealerOnboardingProfile.floor_plan_apr`** — new nullable
   field. `DecimalField(max_digits=5, decimal_places=2,
   null=True, blank=True)`. Migration `0014` — additive only,
   no data migration (existing rows keep `NULL`; the resolver
   in item 2 falls through to env → default when null).

4. **`DealerOnboardingProfile` admin + serializer** —
   whichever surfaces expose it, adds the field. Frontend
   input is NOT M2.4 scope (that's M2.7).

5. **`settings.py::DEALER_AI_FLOOR_PLAN_APR`** env var — one
   line, following the M1 · 4F pattern that wired
   `DEALER_AI_DEALER_TYPE` and `DEALER_AI_PRIMARY_MAKE`.

6. **`manage.py accrue_floor_plan_interest`** management
   command:
   - Required: `--dealership <slug>` (never a "run for all
     tenants" default — one call, one tenant).
   - Optional: `--as-of YYYY-MM-DD` (defaults to
     `timezone.now().date()`).
   - Optional: `--dry-run` (never writes; prints the summary).
   - For each vehicle in the tenant with a
     `VehicleAcquisition`:
     - Find the last `VehicleCost` row with
       `category='floor_plan_interest'` and
       `reference` starting with `"ACCRUAL:"`; take its
       `incurred_at.date()` as the last accrual date. If none,
       use `purchase_date`.
     - Compute `days_elapsed = as_of - last_date`. If `<= 0`,
       skip (idempotent).
     - Compute `interest = daily_floor_plan_interest(
       purchase_price, apr, days_elapsed)`.
       Principal = `purchase_price` for v1 (curtailment
       tracking is deferred — see planning §5).
     - Post a `VehicleCost` row via
       `services.vehicle_ledger.add_cost(...)` with
       `category=CATEGORY_FLOOR_PLAN_INTEREST`,
       `reference=f"ACCRUAL:{as_of.isoformat()}"`,
       `is_estimate=False`,
       `notes` describing the accrual math.
   - Uses `services.vehicle_ledger.add_cost` — NOT direct
     `VehicleCost.objects.create` — to preserve the write-path
     discipline (cross-tenant guard + full_clean).

### Focused tests for M2.4

- `daily_floor_plan_interest`: happy path with a known dollar
  value (e.g. principal=$18,500, apr=8.5%, days=30 → verify
  hand-computed); apr=0 → $0; days=0 → $0; days=-5 → $0;
  Decimal precision preserved.
- `get_floor_plan_apr`: DB layer wins when set; env layer wins
  when DB is null; default falls through when both are null.
- Migration `0014` applies + rolls back cleanly against
  `--database=migration_check`.
- `accrue_floor_plan_interest`: dry-run posts nothing; first
  run posts N rows (one per vehicle with an acquisition);
  second run with same `--as-of` is a no-op (skips because
  days_elapsed = 0); no `--dealership` → command errors out
  with clear message.

### Out of scope for M2.4

- Acquisition-price safety scrub (M2.5).
- API endpoints, serializers, URLs, permission composition
  (M2.6).
- Frontend (M2.7).
- Curtailment tracking / automation (planning §5 deferral —
  requires floor-plan-lender integration or async infra,
  neither in scope until M7).
- Async scheduling / Celery for the accrual command
  (Milestone 7).
- Cost update / delete workflows (planning §5 deferral).
- `expected_gross` (Milestone 3).
- `Vendor` FK (Milestone 4).

### Verification steps at M2.4 close

- Focused payment-engine / config-resolver / management-command
  tests pass.
- Migration `0014` round-trip against `--database=migration_check`.
- Full backend suite passes (target: 1,569 + M2.4 additions).
- Fresh-process smoke of `DEALER_AI_FLOOR_PLAN_APR` env-override
  (mirrors the M1 · 4F pattern):
  `DEALER_AI_FLOOR_PLAN_APR=6.25 python3 -c "..."`.
- Manual smoke of the accrual command: `--dry-run` shows
  expected counts; live run posts rows; re-run same-day is a
  no-op.
- No changes to `services/vehicle_ledger.py` M2.2 contract
  beyond potentially wiring an accrual-run callsite.
- No changes to Vehicle read model (M2.3 contract preserved).

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.4
7. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
   (this file — the M2.3 shipped surface + M2.4 recommended
   scope + the days_in_inventory `None`-when-no-acquisition
   contract)
8. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
   (the load-bearing `total_investment` semantic contract that
   M2.3's read model preserves and M2.4 must not violate)
9. `docs/handoffs/SESSION_046_milestone_2_schema.md`
10. `docs/handoffs/SESSION_045_milestone_2_planning.md`
11. Current source code — new imports available:
    - `dealer_ai.models::Vehicle`: `ledger_totals`,
      `total_investment`, `projected_total_investment`,
      `acquisition_total`, `actual_cost_total`,
      `estimated_cost_total`, `flooring_total`, `recon_total`,
      `administrative_total`, `photography_total`,
      `days_in_inventory`.

Planning docs are claims. Rules + research + code are facts.
