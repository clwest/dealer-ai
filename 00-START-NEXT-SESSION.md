---
state: active
date: 2026-07-31
last_session_shipped: SESSION_049
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_050
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 4b
next_increment_name: "Floor-plan accrual command"
---

# Next session — SESSION_050 · Milestone 2 · Increment 4b (M2.4b — floor-plan accrual command)

> **Milestone 2 · Increment 4a shipped at SESSION_049.**
> `daily_floor_plan_interest` pure math engine, layered
> `get_floor_plan_apr` resolver (DB → env → 8.5% default),
> `DealerOnboardingProfile.floor_plan_apr` nullable field +
> migration `0014`, `DEALER_AI_FLOOR_PLAN_APR` env override.
> 37 hand-verified financial + resolver tests. Test baseline:
> 1,569 → **1,606 pass**, 1 skipped, 0 fail. Zero regressions.
> Migration `0014` round-trips clean. Fresh-process env-override
> smoke verified.
>
> **Load-bearing financial rules locked at M2.4a:**
> APR/principal/days-zero → `Decimal("0.00")`; negative days →
> `0.00` (idempotency escape hatch); negative principal /
> negative APR → `ValueError`; 365-day year; ROUND_HALF_UP;
> APR in percent units. Do NOT relitigate at M2.4b.
>
> **SESSION_050 opens M2.4b — the accrual command.** One
> `manage.py accrue_floor_plan_interest` command that consumes
> the M2.4a math + config to post `VehicleCost` rows via
> `services.vehicle_ledger.add_cost`. Nothing else.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
   boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — layer discipline
   (§8b explicit-dealership rule — accrual command must pass
   `dealership=` explicitly through every call, not rely on
   `pre_save` autofill).
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.4b —
   SESSION_050's scope boundary.
7. `docs/handoffs/SESSION_049_milestone_2_financial_math.md` —
   authoritative recommended scope for M2.4b + the M2.4a engine
   contract the command consumes.
8. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
   (M2.3 read-model contract).
9. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
   (M2.2 service — the accrual command posts through
   `add_cost` and MUST NOT bypass it).
10. `docs/handoffs/SESSION_046_milestone_2_schema.md`,
    `SESSION_045_milestone_2_planning.md`.

## What SESSION_050 should do — M2 · Increment 4b

Per `MILESTONE_2_PLANNING.md` §7.b · M2.4b and
`SESSION_049_milestone_2_financial_math.md` "Exact recommended
scope for M2.4b". ONE deliverable + focused tests.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
     § "Exact recommended scope for M2.4b" — authoritative
     scope + engine contract the command consumes.
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §1.4 (accrual
     mechanism design memo).
   - `backend/dealer_ai/services/payment_engine.py::daily_floor_plan_interest`
     — the pure math function the command wraps.
   - `backend/dealer_ai/services/dealer_config.py::get_floor_plan_apr`
     — the APR source the command uses per-tenant.
   - `backend/dealer_ai/services/vehicle_ledger.py::add_cost` —
     the write path the command MUST use (never
     `VehicleCost.objects.create` directly — preserves
     cross-tenant guard + full_clean).
   - `backend/dealer_ai/models.py::CATEGORY_FLOOR_PLAN_INTEREST`
     — the category constant for posted rows.
   - Any existing management command in
     `backend/dealer_ai/management/commands/` for pattern
     precedent. If the directory doesn't exist yet, create it
     with `__init__.py`.

2. **Create the command file** at
   `backend/dealer_ai/management/commands/accrue_floor_plan_interest.py`.
   Django's `BaseCommand` pattern:
   - `add_arguments`: `--dealership` (required),
     `--as-of` (optional, defaults to today),
     `--dry-run` (flag).
   - `handle`:
     - Resolve dealership (fail loudly on unknown slug — command
       error, not silent).
     - Resolve `as_of` (defaults to `timezone.now().date()`).
     - Resolve `apr = get_floor_plan_apr(dealership)`.
     - Iterate over `Vehicle.objects.filter(dealership=dealership)`
       that have a `VehicleAcquisition` (either
       `select_related('acquisition')` and filter in Python, or
       `.filter(acquisition__isnull=False)`).
     - Per vehicle:
       - Find last accrual date (per M2.4a handoff §"Exact
         recommended scope").
       - `days_elapsed = (as_of - last_accrual_date).days`.
       - `interest = daily_floor_plan_interest(purchase_price,
         apr, days_elapsed)`.
       - If `interest > 0` and not `--dry-run`, post via
         `add_cost(...)`.
     - Print a summary line: N vehicles processed, M rows
       posted, X total dollars.
   - Handle `--dry-run` by NEVER calling `add_cost` — print the
     summary showing what would happen.

3. **Focused tests** at
   `backend/dealer_ai/tests/test_accrue_floor_plan_interest_command.py`.
   Use Django's `call_command` helper. Tests per M2.4a handoff
   § "Focused tests" + a few more:
   - `--dealership` required (missing → error).
   - Dry-run purity (posts zero rows).
   - Happy path (fresh tenant, N vehicles with acquisitions →
     N accrual rows).
   - Idempotency (re-run same `--as-of` → zero new rows).
   - Incremental delta (later `--as-of` → only new days
     accrued).
   - Vehicles without acquisition are skipped.
   - Cross-tenant safety (rows post only to specified
     dealership).
   - Command uses the engine (posted amounts match
     `daily_floor_plan_interest` output).

4. **Verify.**
   - Focused command tests pass.
   - `python3 manage.py test dealer_ai` → ≥ 1,606 + M2.4b
     additions, 0 fail.
   - `makemigrations dealer_ai --check --dry-run` reports no
     changes.
   - Manual smoke: seed a couple of vehicles with acquisitions,
     run `--dry-run` (see the count), run live (see rows
     posted), run same day (no-op), run next day (delta).
   - No changes to M2.4a math engine, M2.3 read model, M2.2
     service contract, or any Milestone 1 primitive.

5. **Close SESSION_050 with:**
   - Handoff at
     `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`.
   - Overwrite this file with SESSION_051 = M2.5 priority
     (acquisition-price safety scrub).

## Explicit non-goals for SESSION_050 (M2 · Increment 4b)

- ❌ Do NOT ship any M2.5 scope: no `_scrub_acquisition_price`,
  no changes to `services/llm_safety.py`.
- ❌ Do NOT ship any M2.6 scope: no endpoints, no serializers,
  no URLs, no permissions.
- ❌ Do NOT ship any M2.7 scope: no frontend.
- ❌ Do NOT modify `services/payment_engine.py::daily_floor_plan_interest`
  or its financial rules. The M2.4a engine contract is locked.
  If a real edge case surfaces, document it as a deferred idea;
  do not change the engine mid-M2.
- ❌ Do NOT bypass `services.vehicle_ledger.add_cost`. Direct
  `VehicleCost.objects.create` in the command would defeat the
  cross-tenant guard + full_clean invariants.
- ❌ Do NOT introduce curtailment logic (planning §5 deferral —
  M2.4b uses `purchase_price` as principal for v1).
- ❌ Do NOT introduce Celery / async scheduling — deferred to
  Milestone 7. The command is manual/cron for v1.
- ❌ Do NOT scope in a `--all-tenants` flag. One command
  invocation, one tenant.
- ❌ Do NOT modify any Milestone 1 or Milestone 2 permission
  class, authentication class, or tenancy resolver.
- ❌ Do NOT introduce a `Vendor` FK model (Milestone 4).
- ❌ Do NOT introduce `expected_gross` (Milestone 3).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_050 with the read-first list above. Ship the
`accrue_floor_plan_interest` management command + focused
tests. Nothing else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.4b
7. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
   (M2.4b authoritative scope + M2.4a engine contract)
8. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
9. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
10. `docs/handoffs/SESSION_046_milestone_2_schema.md`
11. `docs/handoffs/SESSION_045_milestone_2_planning.md`
12. Current source code — new imports available:
    - `dealer_ai.services.payment_engine::daily_floor_plan_interest`
      (pure math engine).
    - `dealer_ai.services.dealer_config::get_floor_plan_apr`
      (layered DB → env → 8.5% default).
    - `dealer_ai.models.DealerOnboardingProfile.floor_plan_apr`
      (nullable Decimal per-tenant field).
    - `settings.DEALER_AI_FLOOR_PLAN_APR` (env override).
    - `dealer_ai.services.vehicle_ledger::add_cost` (the write
      path the command MUST use — never bypass).
    - `dealer_ai.models::CATEGORY_FLOOR_PLAN_INTEREST` (category
      for posted rows).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_049 — M2.4a shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1 through M2.4a.** The
  `floor_plan_apr` field is persisted at the DB layer + reachable
  via the resolver, but the Setup UI has NOT been extended yet
  (M2.7 concern).
- **Frontend (prod):** NONE.
- **Test baseline:** **1,606 pass** (1,569 baseline + 37 new
  M2.4a tests), 1 skipped, 0 fail.
- **DRF defaults + CSRF + endpoint-level permissions:** all as
  documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`
  in `settings.py`, SQLite at
  `backend/db.migration_check.sqlite3` (gitignored). Use with
  `--database=migration_check` for destructive probes.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`, and
  **now** `DEALER_AI_FLOOR_PLAN_APR`. All follow the same
  empty-string-default → resolver-falls-through pattern.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed. M2.6 endpoint smokes reuse both.
- **Ledger model surface (M2.1):** `VehicleAcquisition`,
  `VehicleCost`, `SOURCE_*` × 8, `CATEGORY_*` × 26.
- **Category groupings (M2.2):** `FLOORING_CATEGORIES` (5),
  `RECON_CATEGORIES` (13), `ADMIN_CATEGORIES` (7),
  `PHOTOGRAPHY_CATEGORIES` (1).
- **Ledger service surface (M2.2):** `record_acquisition`,
  `add_cost`, `compute_totals`, `category_group_of`,
  `CrossTenantLedgerError`, `LedgerTotals`, `ZERO`.
- **Vehicle read-model (M2.3):** `@cached_property
  ledger_totals` + 9 delegator `@property` accessors +
  `days_in_inventory`. First read = 7 queries; subsequent = 0.
- **Financial engine + APR config (M2.4a):**
  `daily_floor_plan_interest(principal, apr, days) -> Decimal`
  (pure). `get_floor_plan_apr(dealership) -> Decimal` (layered
  resolver). `DealerOnboardingProfile.floor_plan_apr` nullable
  field. `DEALER_AI_FLOOR_PLAN_APR` env var.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in the
  respective planning + retrospective + handoff docs.
