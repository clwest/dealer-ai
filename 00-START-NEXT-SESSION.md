---
state: active
date: 2026-07-31
last_session_shipped: SESSION_047
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_048
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 3
next_increment_name: "Vehicle computed properties"
---

# Next session — SESSION_048 · Milestone 2 · Increment 3 (M2.3 — Vehicle computed properties)

> **Milestone 2 · Increment 2 shipped at SESSION_047.**
> `services/vehicle_ledger.py` (record_acquisition upsert,
> immutable add_cost, deterministic compute_totals,
> LedgerTotals dataclass, CrossTenantLedgerError guard,
> category_group_of classifier). Category groupings
> (FLOORING/RECON/ADMIN/PHOTOGRAPHY) added to models.py. 44
> deterministic financial tests with hand-verified dollar
> values. Test baseline: 1,496 → **1,540 pass**, 1 skipped, 0
> fail. Zero regressions. `makemigrations --check` reports no
> schema drift.
>
> **The load-bearing semantic decision** locked at M2.2:
> `total_investment` = acquisition + actual costs, *excluding*
> `is_estimate=True` rows. Estimated spend lives in
> `estimated_cost_total`. `projected_total_investment` sums
> both. Do NOT relitigate this at M2.3 — it is the recorded
> contract every downstream milestone inherits.
>
> **SESSION_048 opens M2.3 — Vehicle computed properties.**
> Add `@property` accessors on `Vehicle` that delegate to
> `compute_totals`. Nothing else.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
   boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — layer discipline
   (§1 four-layer separation, §8b explicit-dealership rule).
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons —
   still binding.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (as-shipped
   increment sequence — see M2.3 row for SESSION_048's boundary).
7. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
   — records the M2.2 shipped surface + the load-bearing
   `total_investment` semantic contract + the recommended M2.3
   scope.
8. `docs/handoffs/SESSION_046_milestone_2_schema.md`,
   `SESSION_045_milestone_2_planning.md`.

## What SESSION_048 should do — M2 · Increment 3

Per `MILESTONE_2_PLANNING.md` §7.b · M2.3 and
`SESSION_047_milestone_2_ledger_service.md` "Exact recommended
scope for M2.3". Small increment, `@property` methods only.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
     (full — records the semantic contract M2.3's properties
     must delegate to).
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (M2.3 row).
   - `backend/dealer_ai/services/vehicle_ledger.py` (full — the
     properties delegate to `compute_totals`; understand
     `LedgerTotals` field by field).
   - `backend/dealer_ai/models.py::Vehicle` (existing shape).

2. **Decide the tenant-resolution shape for `@property` calls.**
   `compute_totals(vehicle, *, dealership)` currently requires
   an explicit dealership. Two shapes to choose between:
   - **Property calls resolve `dealership` from
     `vehicle.dealership`** (recommended). Simplest; the
     property borrows the vehicle's own tenant. Cross-tenant
     leaks are impossible because the vehicle IS in its
     dealership by construction.
   - Properties raise if called outside a service context.
     Probably over-engineered for M2.3.

   Recommend adopting the first shape. Document the choice in
   the SESSION_048 handoff and lock the "vehicle borrows its
   own tenant" behavior with a test.

3. **Add `@property` methods to `Vehicle`** in
   `backend/dealer_ai/models.py`. Each delegates to
   `services/vehicle_ledger.compute_totals(self, dealership=self.dealership)`.
   Because computing totals runs four SQL aggregates, cache the
   result *per property-access* — options:
   - Compute once per attribute access (simple; caller decides
     whether to hold a reference).
   - Memoize on the instance via `functools.cached_property`
     (invalidates on new instance, safe within one request).

   Recommend `cached_property` for the totals lookup + property
   accessors that read individual fields off the cached result.
   Shape:

   ```python
   from functools import cached_property
   from .services.vehicle_ledger import compute_totals

   @cached_property
   def ledger_totals(self):
       return compute_totals(self, dealership=self.dealership)

   @property
   def total_investment(self):
       return self.ledger_totals.total_investment
   ```

   Ship these properties (mapped to the nine LedgerTotals
   fields): `total_investment`, `projected_total_investment`,
   `actual_cost_total`, `estimated_cost_total`,
   `acquisition_total`, `flooring_total`, `recon_total`,
   `administrative_total`, `photography_total`.

4. **Add `days_in_inventory` property.** Days elapsed between
   `acquisition.purchase_date` (or `imported_at` as a fallback,
   or the earlier of the two if both exist — SESSION_048's
   call) and today. Returns `None` for vehicles with neither
   date, or a sensible sentinel — decide during implementation.

5. **Focused property tests.** New file
   `backend/dealer_ai/tests/test_vehicle_computed_properties.py`.
   Test each property:
   - Populated vehicle (acquisition + a couple of costs) returns
     the expected `Decimal`.
   - Empty vehicle returns `ZERO` (or `None` for
     `days_in_inventory`).
   - Cross-tenant read is impossible (the property delegates
     with `vehicle.dealership`; contrived test proves the
     property never returns another tenant's data even if a
     caller constructs a vehicle instance with a mismatched
     `dealership_id` in memory).
   - `cached_property` works — repeated property access returns
     the same instance without re-hitting the DB (verifiable
     via `assertNumQueries`).

6. **Verify.**
   - Focused property tests pass.
   - `python3 manage.py test dealer_ai` → ≥ 1,540 + M2.3
     additions, 0 fail.
   - `python3 manage.py makemigrations dealer_ai --check
     --dry-run` reports no changes (M2.3 is Python only, no
     schema drift).
   - No touch to `dealer_ai/permissions.py`,
     `services/tenancy.py`, `services/llm_safety.py`,
     `services/payment_engine.py`,
     `services/dealer_config.py`, or any frontend file.

7. **Close SESSION_048 with:**
   - Handoff at
     `docs/handoffs/SESSION_048_milestone_2_vehicle_properties.md`.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with the
     SESSION_049 = M2.4 priority (floor-plan math, APR
     configuration, accrual command) per
     `MILESTONE_2_PLANNING.md` §7.b · M2.4.

## Explicit non-goals for SESSION_048 (M2 · Increment 3)

- ❌ Do NOT ship any M2.4 scope: no
  `daily_floor_plan_interest`, no `get_floor_plan_apr`, no
  `DealerOnboardingProfile.floor_plan_apr` field, no
  `DEALER_AI_FLOOR_PLAN_APR` env var, no `accrue_floor_plan_interest`
  management command.
- ❌ Do NOT ship any M2.5 scope: no
  `_scrub_acquisition_price`, no changes to
  `services/llm_safety.py`.
- ❌ Do NOT ship any M2.6 scope: no endpoints, no serializers,
  no URL registrations, no permission composition.
- ❌ Do NOT ship any M2.7 scope: no frontend.
- ❌ Do NOT touch the M2.2 semantic contract (estimates
  excluded from `total_investment`). If the property naming
  invites clarification, add docstrings; do NOT change the
  math.
- ❌ Do NOT introduce `expected_gross` (deferred to Milestone 3
  — planning §5).
- ❌ Do NOT introduce a `Vendor` FK model (deferred to Milestone
  4 — planning §5).
- ❌ Do NOT modify any Milestone 1 permission class,
  authentication class, or tenancy resolver.
- ❌ Do NOT generate any migration.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_048 with the read-first list above. Ship the
`@property` accessors on `Vehicle` that delegate to
`compute_totals`. Include `days_in_inventory`. Add focused
property tests. Verify no schema drift, no regressions. Nothing
else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (as-shipped
   sequence — M2.3 row is SESSION_048's boundary)
7. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
8. `docs/handoffs/SESSION_046_milestone_2_schema.md`
9. `docs/handoffs/SESSION_045_milestone_2_planning.md`
10. Current source code — new imports available:
    - `dealer_ai.models`: `FLOORING_CATEGORIES`,
      `RECON_CATEGORIES`, `ADMIN_CATEGORIES`,
      `PHOTOGRAPHY_CATEGORIES`.
    - `dealer_ai.services.vehicle_ledger`: `LedgerTotals`,
      `ZERO`, `CrossTenantLedgerError`, `record_acquisition`,
      `add_cost`, `compute_totals`, `category_group_of`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_047 — M2.2 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0013` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1 or M2.2.**
- **Frontend (prod):** NONE.
- **Test baseline:** **1,540 pass** (1,496 baseline + 44 new
  M2.2 ledger service tests), 1 skipped, 0 fail.
- **DRF defaults + CSRF + endpoint-level permissions:** all as
  documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`
  in `settings.py`, SQLite at
  `backend/db.migration_check.sqlite3` (gitignored). Use with
  `--database=migration_check` for destructive probes.
- **Franchise env-override** verified at Milestone 1 close.
  `DEALER_AI_DEALER_TYPE` + `DEALER_AI_PRIMARY_MAKE` wired
  through `settings.py`. M2.4 will add
  `DEALER_AI_FLOOR_PLAN_APR` alongside them.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed. M2.6 endpoint smokes reuse both.
- **Ledger model surface (M2.1):**
  - `dealer_ai.models::VehicleAcquisition` (OneToOne with
    Vehicle via `related_name="acquisition"`).
  - `dealer_ai.models::VehicleCost` (FK to Vehicle via
    `related_name="costs"`).
  - Both: `dealership` FK NOT NULL, `clean()` cross-tenant guard.
  - `SOURCE_*` × 8 + `ACQUISITION_SOURCE_CHOICES`.
  - `CATEGORY_*` × 26 + `VEHICLE_COST_CATEGORY_CHOICES`.
- **Category groupings (M2.2):**
  - `FLOORING_CATEGORIES` (5), `RECON_CATEGORIES` (13),
    `ADMIN_CATEGORIES` (7), `PHOTOGRAPHY_CATEGORIES` (1).
    Exhaustive + non-overlapping. Locked by tests.
- **Ledger service surface (M2.2):**
  - `dealer_ai.services.vehicle_ledger::record_acquisition`
    (upsert, returns `(instance, created)`).
  - `add_cost` (immutable, one row per call).
  - `compute_totals` (deterministic `LedgerTotals` rollup).
  - `category_group_of` (classifier).
  - `CrossTenantLedgerError` (ValueError subclass, fail-closed).
  - `LedgerTotals` dataclass (frozen, 9 Decimal fields).
  - `ZERO = Decimal("0.00")` canonical zero.
  - **Load-bearing:** `total_investment` excludes
    `is_estimate=True` rows; `estimated_cost_total` isolates
    them; `projected_total_investment` = sum of both.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in the
  respective planning + retrospective + handoff docs.
