---
state: active
date: 2026-07-31
last_session_shipped: SESSION_048
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_049
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 4
next_increment_name: "Floor-plan math, APR configuration, and accrual command"
---

# Next session — SESSION_049 · Milestone 2 · Increment 4 (M2.4 — floor-plan math + APR + accrual command)

> **Milestone 2 · Increment 3 shipped at SESSION_048.**
> `Vehicle` became the ledger read model — nine `@property`
> delegators + `@cached_property ledger_totals` +
> `days_in_inventory`. All aggregation stays in the service
> layer; Vehicle is a thin convenience API. 29 focused tests
> including `assertNumQueries` verification: first read = 7
> queries, subsequent reads = 0. Test baseline: 1,540 →
> **1,569 pass**, 1 skipped, 0 fail. Zero regressions.
> `makemigrations --check` reports no schema drift.
>
> **The load-bearing decisions locked so far:**
>
> - M2.2: `total_investment` excludes `is_estimate=True` rows.
> - M2.3: `days_in_inventory` returns `None` when no acquisition
>   exists (no misleading fallback to `imported_at`).
>
> Do NOT relitigate either in M2.4.
>
> **SESSION_049 opens M2.4 — floor-plan math, APR configuration,
> and accrual command.** One helper in payment_engine + one
> layered resolver in dealer_config + one nullable field in
> onboarding profile + one env var + one management command.
> Nothing else.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
   boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — layer discipline
   (§1 four-layer separation, §8b explicit-dealership rule).
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons —
   still binding.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.4 —
   SESSION_049's scope boundary.
7. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
   — records the M2.3 shipped surface + M2.4 exact recommended
   scope.
8. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
   (M2.2 semantic contract).
9. `docs/handoffs/SESSION_046_milestone_2_schema.md`,
   `SESSION_045_milestone_2_planning.md`.

## What SESSION_049 should do — M2 · Increment 4

Per `MILESTONE_2_PLANNING.md` §7.b · M2.4 and the "Exact
recommended scope for M2.4" section of
`SESSION_048_milestone_2_vehicle_read_model.md`.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
     (§ "Exact recommended scope for M2.4" — this is the
     authoritative scope for SESSION_049).
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §1.4 (accrual
     mechanism design memo) + §7.b · M2.4.
   - `backend/dealer_ai/services/payment_engine.py` — the
     extension seam. New helper mirrors existing pattern of
     small pure functions.
   - `backend/dealer_ai/services/dealer_config.py` — the
     resolver seam. New `get_floor_plan_apr` mirrors existing
     `get_dealer_name` / `get_dealer_profile` shape.
   - `backend/dealer_ai/services/vehicle_ledger.py::add_cost` —
     the accrual command posts through this function (never
     `VehicleCost.objects.create` directly).
   - `backend/dealer_ai/models.py::DealerOnboardingProfile` —
     the target of the new nullable `floor_plan_apr` field +
     migration `0014`.
   - `backend/dealer_kit/settings.py` — where the
     `DEALER_AI_FLOOR_PLAN_APR` env var wires in (mirror the
     M1 · 4F fix pattern that wired `DEALER_AI_DEALER_TYPE`).

2. **Ship `daily_floor_plan_interest` in `payment_engine.py`.**
   Pure function, tests locking apr=0 / days=0 / negative-days
   / Decimal precision cases.

3. **Ship `DealerOnboardingProfile.floor_plan_apr` field +
   migration `0014`.** Nullable, additive only, no data
   migration.
   - Verify round-trip against `--database=migration_check`.

4. **Ship `get_floor_plan_apr` resolver in
   `dealer_config.py`.** DB → env → default (`Decimal("8.5")`).
   Tests locking each layer.

5. **Wire `DEALER_AI_FLOOR_PLAN_APR` in `settings.py`.** One
   line + fresh-process env-override smoke.

6. **Ship `accrue_floor_plan_interest` management command.**
   - `--dealership <slug>` required.
   - `--as-of YYYY-MM-DD` optional (defaults to today).
   - `--dry-run` optional (never writes).
   - Idempotent: re-run same-day → skip (days_elapsed=0).
   - Posts through
     `services.vehicle_ledger.add_cost(...,
     category=CATEGORY_FLOOR_PLAN_INTEREST,
     reference=f"ACCRUAL:{as_of.isoformat()}", is_estimate=False)`.
   - Focused tests: dry-run purity, tenant-required guard,
     idempotency.

7. **Verify.**
   - Focused tests pass.
   - `python3 manage.py test dealer_ai` → ≥ 1,569 + M2.4
     additions, 0 fail.
   - Migration `0014` round-trip against
     `--database=migration_check`.
   - Fresh-process env-override smoke.
   - Manual accrual smoke: `--dry-run` shows counts; live run
     posts rows; re-run same-day no-op.
   - No touch to Vehicle read model, LedgerTotals, service
     contract, permissions, or frontend.

8. **Close SESSION_049 with:**
   - Handoff at
     `docs/handoffs/SESSION_049_milestone_2_floor_plan_accrual.md`.
   - Overwrite this file with SESSION_050 = M2.5 priority
     (acquisition-price safety scrub) per
     `MILESTONE_2_PLANNING.md` §7.b · M2.5.

## Explicit non-goals for SESSION_049 (M2 · Increment 4)

- ❌ Do NOT ship any M2.5 scope: no `_scrub_acquisition_price`,
  no changes to `services/llm_safety.py`.
- ❌ Do NOT ship any M2.6 scope: no endpoints, no serializers,
  no URL registrations, no permission composition.
- ❌ Do NOT ship any M2.7 scope: no frontend (including no
  `floor_plan_apr` field in the onboarding UI — that ships in
  M2.7).
- ❌ Do NOT modify the M2.2 service contract or the M2.3 read
  model. Extending `payment_engine` and adding a resolver in
  `dealer_config` are additive; do not touch `services/vehicle_ledger.py`
  beyond calling `add_cost` from the accrual command.
- ❌ Do NOT introduce curtailment tracking or automation
  (planning §5 deferral — requires floor-plan-lender integration
  or async).
- ❌ Do NOT introduce Celery / async infrastructure — deferred
  to Milestone 7. The accrual command is manual/cron for v1.
- ❌ Do NOT introduce a `Vendor` FK model (Milestone 4).
- ❌ Do NOT introduce `expected_gross` (Milestone 3).
- ❌ Do NOT modify any Milestone 1 permission class,
  authentication class, or tenancy resolver.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.
- ❌ Do NOT combine two increments to "save time" — increment
  discipline is what made Milestone 1 successful.

## NEXT TASK

Start SESSION_049 with the read-first list above. Ship the five
M2.4 deliverables in step order (helper first, then field +
migration, then resolver, then env var, then command). Focused
tests, migration round-trip, full suite verification. Nothing
else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b (M2.4 row)
7. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
   (M2.4 authoritative recommended scope)
8. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
9. `docs/handoffs/SESSION_046_milestone_2_schema.md`
10. `docs/handoffs/SESSION_045_milestone_2_planning.md`
11. Current source code — new imports available:
    - `dealer_ai.models`: `FLOORING_CATEGORIES`,
      `RECON_CATEGORIES`, `ADMIN_CATEGORIES`,
      `PHOTOGRAPHY_CATEGORIES`.
    - `dealer_ai.services.vehicle_ledger`: `LedgerTotals`,
      `ZERO`, `CrossTenantLedgerError`, `record_acquisition`,
      `add_cost`, `compute_totals`, `category_group_of`.
    - `dealer_ai.models.Vehicle`: 10 read-model properties
      (`ledger_totals`, `total_investment`, `days_in_inventory`,
      etc.).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_048 — M2.3 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0013` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1 through M2.3.**
- **Frontend (prod):** NONE.
- **Test baseline:** **1,569 pass** (1,540 baseline + 29 new
  M2.3 read-model tests), 1 skipped, 0 fail.
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
- **Category groupings (M2.2):** `FLOORING_CATEGORIES` (5),
  `RECON_CATEGORIES` (13), `ADMIN_CATEGORIES` (7),
  `PHOTOGRAPHY_CATEGORIES` (1). Exhaustive + non-overlapping.
- **Ledger service surface (M2.2):** `record_acquisition`
  (upsert), `add_cost` (immutable), `compute_totals`
  (deterministic), `category_group_of`, `CrossTenantLedgerError`,
  `LedgerTotals` (frozen 9-field dataclass), `ZERO`.
- **Vehicle read-model (M2.3):** `@cached_property
  ledger_totals` + 9 delegator `@property` accessors +
  `days_in_inventory` (temporal). First read = 7 queries;
  subsequent reads = 0.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in the
  respective planning + retrospective + handoff docs.
