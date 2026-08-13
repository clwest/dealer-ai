---
title: "SESSION_046 handoff — Milestone 2 · Increment 1 (core ledger models)"
status: historical
type: handoff
date: 2026-07-31
session: 046
milestone: 2
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: 795fee4
---

# SESSION_046 — Milestone 2 · Increment 1 (M2.1 — core ledger models)

## What shipped

Two greenfield models, two additive migrations, admin registrations,
a dedicated migration-verification DB alias per M1 lesson 2, and 30
focused model-level tests. The persistence layer for the Vehicle
Investment Ledger. **No business logic yet** — service functions,
computed Vehicle properties, the accrual command, endpoints,
serializers, views, permissions, safety-stack changes, and the
operator UI all remain deferred to Increment 2 / Increment 3 as
scoped by the planning artifact + this session's brief.

### 1. `VehicleAcquisition` — the buying event

- OneToOne with `Vehicle` (related_name=`acquisition`).
- `dealership` FK NOT NULL from day one (greenfield — no backfill
  required, mirrors the M1 · Increment 3 pattern for the six
  original carriers).
- Fields per planning §1.1: `source` (8-value enum),
  `source_detail`, `purchase_price`, `purchase_date`,
  `buyer_fees`, `arbitration_fees`, `transportation_cost`,
  `title_acquisition_cost`, `notes`, timestamps.
- Module-level source constants (`SOURCE_AUCTION`, `SOURCE_TRADE`,
  `SOURCE_WHOLESALE`, `SOURCE_PRIVATE`, `SOURCE_OFF_LEASE`,
  `SOURCE_RENTAL`, `SOURCE_REPO`, `SOURCE_FLEET`) +
  `ACQUISITION_SOURCE_CHOICES` tuple — mirrors the `ROLE_*`
  pattern established in Increment 4A.
- `clean()` cross-tenant guard: raises `ValidationError` if
  `acquisition.dealership_id != vehicle.dealership_id`.
- `Meta.ordering = ("-purchase_date", "-created_at")` — newest
  acquisitions surface first.
- `__str__` includes stock number + human source label for admin
  readability.

Migration `0012_vehicleacquisition.py` — depends on `0011`, single
`CreateModel` operation, additive only.

### 2. `VehicleCost` — post-acquisition cost rows

- FK to `Vehicle` (related_name=`costs`).
- `dealership` FK NOT NULL from day one.
- Fields per planning §1.2: `category` (26-value enum), `amount`
  (signed Decimal — negative permitted for the reversal pattern),
  `incurred_at`, `vendor` (free text until Milestone 4 introduces
  the `Vendor` FK), `reference`, `notes`, `is_estimate`,
  `created_by` (nullable, SET_NULL), timestamps.
- **26 category constants**, one per line-item category enumerated
  by VCP §Investment ledger scope + cross-checked against
  ACCOUNTING §2.5–§2.10:
  - Flooring (5): floor_plan_interest, floor_plan_fees,
    curtailment, wire_fees, banking_fees.
  - Reconditioning (13): parts, mechanical_labor, tires, brakes,
    battery, oil_service, diagnostics, glass, body_work, paint,
    upholstery, wheel_repair, detail.
  - Administrative (7): fuel, listing_fees,
    advertising_allocation, registration, title_work, shipping,
    misc_dealer_expenses.
  - Photography (1): photography (separate from recon so M6
    photography can distinguish "shot for listing" from "shot for
    damage doc" without recategorizing).
- `VEHICLE_COST_CATEGORY_CHOICES` tuple built from the constants.
- Category-set groupings (`FLOORING_CATEGORIES` /
  `RECON_CATEGORIES` / `ADMIN_CATEGORIES`) intentionally NOT
  shipped in M2.1 — they're consumed by
  `services/vehicle_ledger.compute_totals` which is Increment 2.
  Keeping them out of the persistence layer tightens the scope
  boundary the user's SESSION_046 brief drew.
- `clean()` cross-tenant guard — same shape as
  `VehicleAcquisition.clean()`.
- `Meta.ordering = ("-incurred_at", "-created_at")` — newest cost
  surfaces first.
- `__str__` includes category, amount, and stock number.

Migration `0013_vehiclecost.py` — depends on `0012` and
`AUTH_USER_MODEL`, single `CreateModel` operation, additive only.

### 3. Admin registrations

`VehicleAcquisitionAdmin` and `VehicleCostAdmin` in
`backend/dealer_ai/admin.py`. Read-mostly ModelAdmin surfaces with
list_display, list_filter, search_fields, autocomplete_fields
following the existing `VehicleAdmin` / `CustomerLeadAdmin`
patterns. These are for internal debugging + emergency corrections;
the primary operator surface ships in M2.3 (the
`/dealer-ai-inventory/:stock/ledger` page).

### 4. `DATABASES["migration_check"]` alias (M1 lesson 2)

Added to `backend/dealer_kit/settings.py`. SQLite file at
`backend/db.migration_check.sqlite3`, gitignored. Reserved
exclusively for destructive migration probes — invoked with
`python3 manage.py migrate --database=migration_check ...`.

This closes the M1 retrospective §6 lesson 2 gap: SESSION_038
wiped ~200 rows of dev demo data verifying `migrate zero → migrate`
against the live dev DB. Every future migration-verification run
uses the isolated alias instead. Used in this session's
verification steps (below); every subsequent M2 increment inherits
it without rework.

### 5. Test coverage — 30 new tests, all passing

- `test_vehicle_acquisition.py` — 14 tests across 8 test classes:
  `SourceChoicesVocabulary`, `VehicleAcquisitionCreate` (3 tests),
  `OneToOneUniqueness`, `DealershipRequired` (2 tests),
  `CrossTenantClean` (2 tests), `CascadeOnVehicleDelete`,
  `ReverseRelation` (2 tests), `OrderingContract`,
  `StringRepresentation`.
- `test_vehicle_cost.py` — 16 tests across 9 test classes:
  `CategoryVocabulary`, `VehicleCostCreate` (5 tests),
  `DealershipRequired` (2 tests), `CrossTenantClean` (2 tests),
  `CascadeOnVehicleDelete`, `CreatedBySetNullOnUserDelete`,
  `ReverseRelation` (2 tests), `OrderingContract`,
  `StringRepresentation`.

Category-vocabulary tests both include a
`len(keys) == N` assertion so any silent addition/removal of a
canonical value forces a roadmap conversation — same shape as the
M1 · Increment 4A test
`test_role_choices_contain_exactly_seven_canonical_values`.

### 6. Verification results

- **`python3 manage.py test dealer_ai` → 1,496 pass** (1,466 baseline
  + 30 new), 1 skipped, 0 fail. Zero regressions across the
  pre-M2.1 suite.
- **Migration round-trip against `--database=migration_check`:**
  `migrate` (clean forward through 0013) → `migrate dealer_ai 0011`
  (rollback 0013 + 0012 unapplied cleanly) → `migrate` (forward
  again, 0012 + 0013 re-apply cleanly). All zero warnings, zero
  errors.
- **Dev DB (`db.sqlite3`) is now at 0013.** Applied via
  `python3 manage.py migrate dealer_ai` after test runs. No data
  loss — greenfield tables mean no existing rows to backfill.
- **No frontend changes** — M2.1 is backend-only. `npx tsc
  --noEmit` and `npx vite build` not run; the frontend was
  untouched.

## Deviations from the planning document

One legitimate deviation, documented here per user brief step
"Documentation":

**Planning `MILESTONE_2_PLANNING.md` §7 · M2.1 originally scoped
in** `services/vehicle_ledger.py` (with `LedgerTotals` dataclass
and `compute_totals` function) plus computed `@property` methods on
`Vehicle` (`total_investment`, `projected_gross`, etc.).

**SESSION_046 brief narrowed** M2.1 to "the persistence layer" only
— explicitly excluding "services/vehicle_ledger.py" and "computed
Vehicle properties" (see the brief's "Explicitly Out of Scope"
list).

**Followed the brief.** The service module and computed properties
land in Increment 2, alongside the API endpoints that consume
them. This is a cleaner separation: M2.1 is pure schema, M2.2 is
schema-consuming business logic. The planning document has NOT
been amended — the deviation is documented here and will be
addressed by M2.2 which now inherits both the API+service work
originally scoped for M2.2 plus the `LedgerTotals` +
`compute_totals` + Vehicle `@property` work originally scoped for
M2.1. M2.2 grew by ~150 LOC as a result; it remains a single
session's worth of work because the vast majority of M2.2's scope
(three endpoints, safety-stack scrub, accrual command, permission
matrices, focused tests) was always the increment's substance.

The category-set groupings (`FLOORING_CATEGORIES`,
`RECON_CATEGORIES`, `ADMIN_CATEGORIES`) are also deferred to M2.2
for the same "no business logic in the persistence layer" reason
— they exist only to serve `compute_totals`, which is now M2.2
scope.

## What SESSION_046 did NOT do

Per the user brief's explicit "Out of Scope":

- ❌ `services/vehicle_ledger.py` — deferred to M2.2.
- ❌ Computed Vehicle properties (`total_investment`,
  `projected_gross`, category subtotals, `days_in_inventory`) —
  deferred to M2.2.
- ❌ `services/payment_engine.py` changes
  (`daily_floor_plan_interest`) — deferred to M2.2.
- ❌ Floor-plan-interest accrual management command — deferred to
  M2.2.
- ❌ `services/dealer_config.py::get_floor_plan_apr` — deferred to
  M2.2.
- ❌ `DealerOnboardingProfile.floor_plan_apr` field + migration
  `0014` — deferred to M2.2.
- ❌ `settings.py::DEALER_AI_FLOOR_PLAN_APR` env var — deferred to
  M2.2.
- ❌ Any endpoint / serializer / view / permission composition —
  deferred to M2.2.
- ❌ Any frontend — deferred to M2.3.
- ❌ `services/llm_safety.py` acquisition-price scrub — deferred to
  M2.2.
- ❌ Operator UI — deferred to M2.3.

## Files touched this session

**Backend (5 files):**

- `backend/dealer_ai/models.py` — added SOURCE constants,
  `VehicleAcquisition` model, CATEGORY constants,
  `VehicleCost` model. `ValidationError` import added.
- `backend/dealer_ai/admin.py` — imported both new models,
  registered `VehicleAcquisitionAdmin` and `VehicleCostAdmin`.
- `backend/dealer_ai/migrations/0012_vehicleacquisition.py` — new,
  autogenerated by `makemigrations dealer_ai --name vehicleacquisition`.
- `backend/dealer_ai/migrations/0013_vehiclecost.py` — new,
  autogenerated by `makemigrations dealer_ai --name vehiclecost`.
- `backend/dealer_kit/settings.py` — added
  `DATABASES["migration_check"]` alias per M1 lesson 2.

**Backend tests (2 new files):**

- `backend/dealer_ai/tests/test_vehicle_acquisition.py` — 14
  tests, 8 classes.
- `backend/dealer_ai/tests/test_vehicle_cost.py` — 16 tests, 9
  classes.

**Infrastructure (1 file):**

- `.gitignore` — added `db.migration_check.sqlite3` entry.

**Docs (2 files):**

- `docs/handoffs/SESSION_046_milestone_2_schema.md` — this file.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_047 =
  M2.2 priority.

No changes to any Milestone 1 code, any existing test, any
existing frontend file, or any existing documentation file. The
planning document is untouched (per user brief).

## What the next session should do

**SESSION_047 = Milestone 2 · Increment 2 (M2.2 — API + service +
safety + accrual).**

Per `MILESTONE_2_PLANNING.md` §7 · M2.2, plus the M2.1→M2.2
scope-slide documented in "Deviations" above. M2.2 now ships:

**Originally in M2.2:**

1. `services/vehicle_ledger.py::record_acquisition(vehicle, ..., *,
   dealership)` + `add_cost(vehicle, category, amount, ..., *,
   dealership)`.
2. Three admin endpoints under
   `/api/dealer-ai/admin/vehicles/<stock_number>/{ledger,acquisition,costs}/`.
3. Permission composition:
   `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`
   on all three. Focused six-case permission matrix per endpoint.
4. `services/dealer_config.py::get_floor_plan_apr` resolver (DB →
   env → default).
5. `DealerOnboardingProfile.floor_plan_apr` field + migration
   `0014` (nullable, additive).
6. `settings.py::DEALER_AI_FLOOR_PLAN_APR` env var.
7. `services/payment_engine.py::daily_floor_plan_interest`
   helper + tests.
8. `services/llm_safety.py::_scrub_acquisition_price` +
   `_ACQUISITION_PRICE_PATTERNS` block + branch in
   `apply_post_llm_scrubs`. Positive + negative test coverage.
9. `manage.py accrue_floor_plan_interest --dealership=<slug>
   [--as-of=YYYY-MM-DD] [--dry-run]` management command + tests
   (idempotency, dry-run purity, tenant-required guard).

**Absorbed from M2.1 (see Deviations above):**

10. `services/vehicle_ledger.py::LedgerTotals` dataclass +
    `compute_totals(vehicle, *, dealership) -> LedgerTotals`.
11. Category-set groupings (`FLOORING_CATEGORIES`,
    `RECON_CATEGORIES`, `ADMIN_CATEGORIES`) in `models.py` (or a
    new `ledger_categories.py` — Increment 2's call).
12. Computed `@property` methods on `Vehicle`:
    `total_acquisition_cost`, `total_flooring_cost`,
    `total_recon_cost`, `total_admin_cost`, `total_investment`,
    `projected_gross`, `days_in_inventory`.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md` (§1 layer separation,
   §8b explicit-dealership rule)
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` (acceptance contract for
   M2; §7 M2.2 scope boundary + this handoff's Deviations section)
7. `docs/BUSINESS_DOMAIN_MAP.md`
8. `docs/research/*_MAPPING.md` + `VEHICLE_CENTRIC_PIVOT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. Current source code — new imports available:
    - `dealer_ai.models`: `VehicleAcquisition`, `VehicleCost`,
      `SOURCE_*` (8 constants), `ACQUISITION_SOURCE_CHOICES`,
      `CATEGORY_*` (26 constants), `VEHICLE_COST_CATEGORY_CHOICES`.
11. Most recent handoffs:
    - `SESSION_046_milestone_2_schema.md` (this file)
    - `SESSION_045_milestone_2_planning.md`
    - `SESSION_044_milestone_1_closeout.md`

Planning docs are claims. Rules + research + code are facts.
