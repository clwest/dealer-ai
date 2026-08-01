---
title: "SESSION_047 handoff — Milestone 2 · Increment 2 (ledger business service)"
status: historical
type: handoff
date: 2026-07-31
session: 047
milestone: 2
milestone_status: in_progress
increment: 2
increment_status: shipped
commit: 0d40b6b
---

# SESSION_047 — Milestone 2 · Increment 2 (M2.2 — ledger business service)

## What shipped

One thing: the deterministic business layer that answers *"how
much money is in stock #NNN right now, actual vs. estimated?"* for
any vehicle. Pure Python — no schema drift, no migrations, no API,
no frontend, no safety-stack changes, no floor-plan math, no
config changes.

### 1. `services/vehicle_ledger.py` — the canonical ledger service

- `record_acquisition(vehicle, *, dealership, source,
  purchase_price, purchase_date, …) -> Tuple[VehicleAcquisition,
  bool]`. Upsert semantics: first call creates and returns
  `(instance, True)`; every subsequent call for the same vehicle
  updates the same row and returns `(instance, False)`. Contract
  matches Django's `get_or_create` / `update_or_create` so callers
  do not have to learn a new one. Locked by
  `RecordAcquisitionUpsert` (4 tests).
- `add_cost(vehicle, *, dealership, category, amount,
  incurred_at, …) -> VehicleCost`. Immutable post — every call
  creates exactly one new row. No update / delete behavior.
  Corrections happen via reversing rows (negative amount,
  reference pointing at original), matching accounting practice
  (`ACCOUNTING_DEPARTMENT_MAPPING.md` §2.11). Locked by
  `AddCostImmutable` (5 tests).
- `compute_totals(vehicle, *, dealership) -> LedgerTotals`.
  Deterministic per-category + aggregate rollup, four
  category-scoped SQL aggregates + one acquisition lookup.
  Zero-cost / zero-acquisition vehicles get `ZERO` (Decimal) for
  every field, never `None`.
- `category_group_of(category) -> Optional[str]`. Convenience
  classifier returning `"flooring"` / `"recon"` /
  `"administrative"` / `"photography"` / `None`. Keeps the
  partition logic in one authoritative place for future
  serializer / UI reuse.
- `CrossTenantLedgerError(ValueError)`. Fail-closed on every
  public function's entry when
  `vehicle.dealership_id != dealership.pk`. Belt; the model
  layer's `clean()` cross-tenant guard is the suspenders.
- `ZERO = Decimal("0.00")` — module-level canonical zero (imported
  by tests and future consumers).

### 2. `LedgerTotals` dataclass — the semantic contract

Frozen `@dataclass(frozen=True)` with nine fields, every one a
`Decimal`:

```
acquisition_total, flooring_total, recon_total,
administrative_total, photography_total,
actual_cost_total, estimated_cost_total,
total_investment, projected_total_investment
```

**Load-bearing semantic decision** — *estimated spend is NOT
invested money*:

- `total_investment` = `acquisition_total + actual_cost_total`
  (money the store has actually committed). *Excludes* rows
  where `is_estimate=True`.
- `estimated_cost_total` = sum of every `VehicleCost.amount`
  across every category where `is_estimate=True`. Money projected
  but not yet committed (open work orders, planned repairs).
- `projected_total_investment` = `total_investment +
  estimated_cost_total`. Useful for pricing decisions.

Rationale (documented in the module docstring and locked by
`ComputeTotalsActualVsEstimated` — 5 tests): labeling estimated
spending as sunk cost would mislead operators at disposition time.
The `is_estimate` field exists on `VehicleCost` precisely because
this distinction matters at decision time.

The planning doc §1.3 originally left `total_investment`'s
handling of estimates ambiguous — this session's brief resolved
that ambiguity per the user's recommendation, and the resolution
is now the recorded contract.

### 3. Category groupings in `models.py`

Four module-level tuples added alongside the individual
`CATEGORY_*` constants:

- `FLOORING_CATEGORIES` (5): floor_plan_interest, floor_plan_fees,
  curtailment, wire_fees, banking_fees.
- `RECON_CATEGORIES` (13): parts, mechanical_labor, tires, brakes,
  battery, oil_service, diagnostics, glass, body_work, paint,
  upholstery, wheel_repair, detail.
- `ADMIN_CATEGORIES` (7): fuel, listing_fees,
  advertising_allocation, registration, title_work, shipping,
  misc_dealer_expenses.
- `PHOTOGRAPHY_CATEGORIES` (1): photography.

**Exhaustive + non-overlapping partition.** Every canonical
category appears in exactly one grouping — locked by
`CategoryGroupings.test_every_canonical_category_appears_in_exactly_one_group`
and `CategoryGroupings.test_groups_do_not_overlap`. Photography
kept separate from admin so the Milestone 6 photography surface
can distinguish "shot for listing" from "shot for damage
documentation" without recategorizing historical rows.

### 4. Deterministic financial tests — 44 new, all passing

Hand-verified dollar values throughout. Zero reliance on endpoint
or frontend tests to prove arithmetic — the ledger's numbers are
proven at this layer:

| Class | Tests | What it locks |
|-------|-------|---------------|
| `CategoryGroupings` | 3 | Exhaustive + non-overlapping partition; group counts (5/13/7/1) |
| `CategoryGroupOf` | 5 | Classifier outputs match the partition; unknown → None |
| `CrossTenantGuards` | 4 | All three public functions fail closed on wrong dealership; `CrossTenantLedgerError` is a `ValueError` subclass |
| `RecordAcquisitionUpsert` | 4 | (instance, True) on create; (instance, False) on update; never a second row; fee defaults are ZERO |
| `AddCostImmutable` | 5 | One row per call; invalid category → ValueError before DB; created_by attached; signed amounts permitted; full_clean runs |
| `ComputeTotalsAcquisitionOnly` | 3 | Hand-verified $19,475 = $18,000 + $500 + $0 + $850 + $125; cost rollups zero |
| `ComputeTotalsMultipleCategories` | 4 | Hand-verified $21,030 = $19,475 acq + ($250 flooring + $910 recon + $245 admin + $150 photo) |
| `ComputeTotalsActualVsEstimated` | 5 | `total_investment=$15,800` excludes estimates; `estimated_cost_total=$1,400`; `projected=$17,200` includes them; estimated recon rows never leak into `recon_total` |
| `ComputeTotalsReversingEntry` | 3 | $500 - $500 = $0 net; both rows survive; no ledger mutation |
| `ComputeTotalsZeroDollarEntry` | 2 | $0 rows persist without blowing up aggregations |
| `ComputeTotalsEmptyStates` | 3 | No-acquisition → ZERO; no-costs → ZERO; every field is Decimal, never None |
| `ComputeTotalsDecimalPrecision` | 3 | 100 × $0.01 = exactly $1.00 (no float drift); LedgerTotals is frozen; two calls return equal instances |

Total: 44 tests, 12 classes.

## Verification results

- **`python3 manage.py test dealer_ai` → 1,540 pass** (1,496
  baseline + 44 new ledger service tests), 1 skipped, 0 fail.
  Zero regressions.
- **`python3 manage.py makemigrations dealer_ai --check
  --dry-run` → "No changes detected in app 'dealer_ai'".**
  Confirms this session added zero schema drift.
- **Safety pipeline unchanged.** Every scrub test in the 1,496
  baseline passes. The acquisition-price scrub is Milestone 2 ·
  Increment 5, not this session.
- **Auth substrate unchanged.** No changes to
  `dealer_ai/permissions.py` or `services/tenancy.py`.
- **Public surfaces unchanged.** No new endpoints. Customer chat
  (`/chat/*`, `/vehicles/<id>/ask/`), branding
  (`/onboarding/profile/` GET, `/salespeople/`), and public
  routes (`/`, `/assistant`, `/showroom`, `/embed/assistant`,
  `/login`) untouched.

## Planning-document annotation

Per the SESSION_047 brief, `docs/roadmap/MILESTONE_2_PLANNING.md`
§7 was annotated (not rewritten) to record the refined
implementation sequence:

- §7.a preserves the original 3-increment plan (M2.1 / M2.2 /
  M2.3) verbatim as historical record.
- §7.b is the new eight-increment sequence
  (M2.1 through M2.8) reflecting the SESSION_047 course-
  correction. M2.1 (models) shipped; M2.2 (this session's
  service layer) shipped; M2.3–M2.8 are the remaining
  small-increment breakdown recommended by the SESSION_047
  brief.

Reasoning captured inline: the previously-proposed 12-deliverable
M2.2 would have combined ledger business logic, Vehicle computed
properties, API surfaces, permissions, tenant scoping,
acquisition-price safety, floor-plan math, floor-plan
configuration, and accrual command behavior into a single session.
That would have undone the increment discipline that made
Milestone 1 successful. Deferred work is now redistributed into
small increments, not accumulated into one large session.

## Files touched this session

**Backend (2 files modified, 2 files new):**

- `backend/dealer_ai/models.py` — added `FLOORING_CATEGORIES`,
  `RECON_CATEGORIES`, `ADMIN_CATEGORIES`,
  `PHOTOGRAPHY_CATEGORIES` module-level tuples. No changes to any
  existing constant or model.
- `backend/dealer_ai/services/vehicle_ledger.py` — **new module**.
  435 lines including docstrings.
- `backend/dealer_ai/tests/test_vehicle_ledger.py` — **new file**.
  44 tests across 12 classes.

**Docs (3 files):**

- `docs/roadmap/MILESTONE_2_PLANNING.md` — §7 annotated with
  §7.a (original 3-increment plan preserved) and §7.b (refined
  8-increment sequence).
- `docs/handoffs/SESSION_047_milestone_2_ledger_service.md` —
  this file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_048 =
  M2.3.

**No changes to:** admin.py, migrations, urls.py, views.py,
settings.py, permissions.py, tenancy.py, llm_safety.py,
payment_engine.py, dealer_config.py, or any frontend file.

## Exact recommended scope for M2.3 (SESSION_048)

**M2.3 — Vehicle computed properties.** Nothing more.

### In scope

1. Add `@property` methods to `Vehicle` that delegate to
   `services/vehicle_ledger.compute_totals`:
   - `total_investment` → `LedgerTotals.total_investment`.
   - `projected_total_investment` →
     `LedgerTotals.projected_total_investment`.
   - `actual_cost_total`, `estimated_cost_total`.
   - `acquisition_total`, `flooring_total`, `recon_total`,
     `administrative_total`, `photography_total`.
   - `days_in_inventory` — days elapsed between
     `acquisition.purchase_date` (or the earlier of it and
     `imported_at`) and today. Returns `None` (or `0`, decide
     during implementation) when there is no acquisition record.

2. **Tenant scoping decision to make in M2.3.** The properties
   delegate to `compute_totals(vehicle, *, dealership=...)`
   which currently requires an explicit dealership. Two shapes
   to choose between:
   - **Property calls resolve `dealership` from
     `vehicle.dealership`** — simplest; the property "borrows"
     the vehicle's own tenant. Cross-tenant leaks are impossible
     because the vehicle IS in its dealership by construction.
   - **Properties raise if called outside a service-layer
     context** — stricter; forces callers to use the service
     directly. Probably over-engineered for M2.3.

   Recommendation: pick the first shape. Document the choice in
   the SESSION_048 handoff and lock the "vehicle borrows its own
   tenant" behavior with a test.

3. Focused property tests: one per property, with a mix of
   populated / empty vehicles. Reuse the M2.2 `_make_vehicle`
   fixture pattern. Prove the properties match
   `compute_totals` output for the same vehicle.

### Out of scope for M2.3

- API endpoints (M2.6).
- Serializers (M2.6).
- Frontend (M2.7).
- `expected_gross` (deferred to Milestone 3 — planning §5).
- `daily_floor_plan_interest`, `get_floor_plan_apr`,
  `DealerOnboardingProfile.floor_plan_apr`,
  `DEALER_AI_FLOOR_PLAN_APR`, accrual command — all M2.4.
- Acquisition-price scrub — M2.5.
- Any migration.

### Verification steps at M2.3 close

- Focused property tests pass.
- Full backend suite passes (target: 1,540 + M2.3 additions).
- `makemigrations --check --dry-run` reports no changes.
- No touch to Milestone 1 permission classes, tenancy resolvers,
  safety stack, or public routes.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (as-shipped
   increment sequence)
7. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
   (this file — the M2.2→M2.3 boundary + the
   `total_investment` semantic contract)
8. `docs/handoffs/SESSION_046_milestone_2_schema.md`
9. `docs/handoffs/SESSION_045_milestone_2_planning.md`
10. Current source code — new imports available:
    - `dealer_ai.models`: `FLOORING_CATEGORIES`,
      `RECON_CATEGORIES`, `ADMIN_CATEGORIES`,
      `PHOTOGRAPHY_CATEGORIES`.
    - `dealer_ai.services.vehicle_ledger`: `LedgerTotals`,
      `ZERO`, `CrossTenantLedgerError`, `record_acquisition`,
      `add_cost`, `compute_totals`, `category_group_of`.

Planning docs are claims. Rules + research + code are facts.
