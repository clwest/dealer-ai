---
title: "SESSION_049 handoff — Milestone 2 · Increment 4a (financial mathematics foundation)"
status: historical
type: handoff
date: 2026-07-31
session: 049
milestone: 2
milestone_status: in_progress
increment: 4a
increment_status: shipped
commit: f8cd0b2
---

# SESSION_049 — Milestone 2 · Increment 4a (M2.4a — financial mathematics foundation)

## What shipped

Four things — the deterministic financial engine + its
configuration layer. **No ledger posting. No management command.
No operational workflow.** The engine can now calculate floor-plan
interest correctly; wiring it into a batch accrual is Increment 4b
(SESSION_050).

### 1. `services/payment_engine.py::daily_floor_plan_interest`

Pure. No I/O. No side effects. No dealership knowledge, no
Vehicle knowledge, no ledger writes.

```python
def daily_floor_plan_interest(
    principal: Decimal,
    apr: Decimal,
    days_elapsed: int,
) -> Decimal:
    ...
```

**Load-bearing financial rules** (documented in the function
docstring and locked by tests in
`test_daily_floor_plan_interest.py`):

| Input state | Return |
|-------------|--------|
| `apr == 0` | `Decimal("0.00")` |
| `principal == 0` | `Decimal("0.00")` |
| `days_elapsed == 0` | `Decimal("0.00")` (idempotency escape hatch — accrual command's same-day re-run) |
| `days_elapsed < 0` | `Decimal("0.00")` (stale `--as-of` is a documented no-op, not a crash) |
| `principal < 0` | `ValueError` (data corruption signal) |
| `apr < 0` | `ValueError` (data corruption signal) |
| valid inputs | `Decimal` quantized to 2 places, `ROUND_HALF_UP` |

**APR-unit convention:** percent units (`Decimal("8.5")` = 8.5%
annual) — matches existing `DEFAULT_APR = 7.49` in
`payment_engine.py`.

**Day-count convention:** 365 (calendar year), documented in
`_DAYS_PER_YEAR`. A 30-day period always produces 30/365 of the
annual interest — no leap-year adjustment, no bankers' 360-day
year. If a future integration with a 360-day lender lands, add
an optional `days_per_year` parameter — the convention lock
above forces that to be a conscious change.

**Rounding:** `ROUND_HALF_UP` (matches consumer expectation for
money and how most floor-plan-lender statements print interest).
Divergence from banker's rounding (`ROUND_HALF_EVEN`) is
documented in the `_CENTS` module-level constant and locked by
`DecimalPrecisionAndRounding.test_round_half_up_pushes_the_five_up`.

**Formula:**

```
raw = principal * apr * days_elapsed / (365 * 100)
result = raw.quantize(Decimal("0.01"), ROUND_HALF_UP)
```

Multiply-then-single-divide preserves Decimal precision before
the final rounding step.

**Type coercion:** non-Decimal numeric inputs (`int`, `float`)
are coerced via `Decimal(str(value))` before comparison —
prevents float→Decimal precision loss.

### 2. `DealerOnboardingProfile.floor_plan_apr` + migration `0014`

Nullable `DecimalField(max_digits=5, decimal_places=2, null=True,
blank=True)`. Additive migration only. No data migration
(existing profiles keep `NULL`; the resolver falls through to
env / default when null).

**Field-level range validation deliberately NOT added.** Range
enforcement lives in the accrual engine (which raises
`ValueError` on negative APR). Field stays permissive so future
operator-facing forms can accept incrementally-entered values
without validator friction. Locked by
`FloorPlanAprFieldShape.test_field_has_no_min_max_validators`.

### 3. `services/dealer_config.py::get_floor_plan_apr`

```python
def get_floor_plan_apr(
    dealership: Optional["Dealership"] = None,
) -> Decimal:
    ...
```

Layered resolution — DB → env → default. Mirrors
`get_dealer_name` / `get_dealer_profile` shape:

1. `DealerOnboardingProfile.floor_plan_apr` (per-tenant, when
   non-null).
2. `settings.DEALER_AI_FLOOR_PLAN_APR` env override (coerced
   via `Decimal(env_value)`; silent fall-through on unparseable
   values).
3. `Decimal("8.5")` — Copper Canyon baseline per planning §1.4.

**DB beats env** — unlike `get_dealer_name` (where env beats
DB). Documented in the resolver docstring: env is a fallback
for dealerships without a saved profile, not a global master
switch. Locked by
`FloorPlanAprResolutionOrder.test_db_beats_env_when_both_set`.

**Silent fall-through on invalid env values** — matches the
M1 · 4F `DEALER_AI_DEALER_TYPE` pattern. A bad env value NEVER
crashes the resolver; it falls through to the next layer. A
future observability pass may want to log the event; deferred
to Milestone 8.

### 4. `settings.py::DEALER_AI_FLOOR_PLAN_APR` env var

One line, following the M1 · 4F pattern. Empty-string default →
resolver falls through to next layer. Fresh-process smoke
verified:

```
$ DEALER_AI_FLOOR_PLAN_APR=6.25 python3 -c "..."
resolved apr = 6.25
```

## Mathematical rules

Every rule intentionally chosen and covered by tests. Not a side
effect of implicit Decimal behavior:

| Concern | Rule | Test class |
|---------|------|-----------|
| APR unit | Percent (matches existing convention) | `HandVerifiedFinancialMath` |
| Day count | 365 (calendar year, no leap adjustment) | `LeapYearNeutrality` + `test_full_year_365_days` |
| Rounding | `ROUND_HALF_UP` at 2 decimal places | `DecimalPrecisionAndRounding` |
| Zero returns | `Decimal("0.00")` (canonical shape with -2 exponent) | `ZeroAndEdgeInputs` |
| Negative days | `0.00` (no-op) | `ZeroAndEdgeInputs.test_negative_days_returns_zero` |
| Negative principal | `ValueError` | `InvalidInputs.test_negative_principal_raises_value_error` |
| Negative APR | `ValueError` | `InvalidInputs.test_negative_apr_raises_value_error` |
| Determinism | Same inputs → equal Decimals | `DecimalPrecisionAndRounding.test_result_is_deterministic_across_repeated_calls` |
| Principal is generic | Engine accepts arbitrary principal (purchase price / payoff / curtailment balance) | `PrincipalIsGeneric` |
| Type coercion | int / float coerce via `Decimal(str(value))` | `TypeCoercion` |

Hand-verified accrual values (independently verifiable with a
calculator):

- **1 day, $18,500 at 8.5% APR** → `$4.31` (raw 4.30821917808..., HALF_UP → 4.31)
- **30 days, $18,500 at 8.5% APR** → `$129.25` (raw 129.24657534..., HALF_UP → 129.25)
- **90 days (curtailment window), $18,500 at 8.5% APR** → `$387.74` (raw 387.73972602..., HALF_UP → 387.74)
- **1 day, $10,000 at 12% APR** → `$3.29` (raw 3.28767123..., HALF_UP → 3.29)
- **365 days, $10,000 at 10% APR** → exactly `$1,000.00` (locks the 365-day convention)
- **7 days, $500 at 5% APR** → `$0.48` (raw 0.47945205..., HALF_UP → 0.48)

## Tests added — 37 new, all passing

`test_daily_floor_plan_interest.py` — 20 tests, 7 classes:

- `HandVerifiedFinancialMath` (6) — the load-bearing calculator-
  verified accruals above.
- `ZeroAndEdgeInputs` (5) — zero-return behavior + canonical
  Decimal shape for zero returns.
- `InvalidInputs` (3) — negative principal / APR raise;
  principal check runs first for deterministic error attribution.
- `DecimalPrecisionAndRounding` (4) — Decimal type / 2-place
  quantize / ROUND_HALF_UP / determinism.
- `LeapYearNeutrality` (1) — 30 days is 30 days.
- `PrincipalIsGeneric` (1) — engine accepts arbitrary principal
  (documents the scope-discipline decision to keep the engine
  reusable for future payoff / curtailment / lender-balance
  math).
- `TypeCoercion` (2) — int / float inputs coerce safely.

`test_floor_plan_apr_resolver.py` — 17 tests, 3 classes:

- `FloorPlanAprResolutionOrder` (5) — DB > env > default
  precedence; DB null falls through even when profile exists;
  DB beats env when both set.
- `FloorPlanAprEnvHandling` (5) — env coercion, empty →
  fallthrough, unparseable → silent fallthrough, whitespace
  strip, `env=0` returned verbatim.
- `FloorPlanAprFieldShape` (5) — nullable at schema level,
  Decimal(5, 2) precision, no data-migration friction, accepts
  Decimal value, no MinValueValidator (range enforcement stays
  in the accrual engine).

## Backend baseline

- **`python3 manage.py test dealer_ai` → 1,606 pass** (1,569
  baseline + 37 new M2.4a tests), 1 skipped, 0 fail. Zero
  regressions.
- Migration `0014` round-trip against `--database=migration_check`:
  forward clean → rollback (0014 unapplies cleanly) → forward
  again clean.
- Dev DB now at `0014`.
- Fresh-process env-override smoke passed
  (`DEALER_AI_FLOOR_PLAN_APR=6.25` → resolver returns `6.25`).

## Compatibility result

Every existing invariant holds. Explicit rechecks:

- **Existing ledger calculations unchanged.**
  `services/vehicle_ledger.py` untouched. M2.2 tests (44 tests)
  and M2.3 tests (29 tests) all pass unchanged.
- **Payment engine existing helpers unchanged.**
  `estimate_payment`, `estimate_bhph_payment`,
  `affordable_max_price`, `bhph_min_down_payment` all preserved
  byte-for-byte.
- **Existing dealer_config resolvers unchanged.**
  `get_dealer_name`, `get_dealer_profile`,
  `_load_onboarding_profile` all preserved. `get_floor_plan_apr`
  is a new sibling.
- **Safety pipeline unchanged.**
- **Auth substrate unchanged.**
- **Vehicle read model unchanged.** M2.3's nine `@property`
  accessors + `days_in_inventory` still delegate correctly.
- **Public routes unchanged.**
- **Frontend untouched.**

## Files touched this session

**Backend (4 files modified, 3 files new):**

- `backend/dealer_ai/services/payment_engine.py` — added imports
  (`ROUND_HALF_UP`), module constants (`_DAYS_PER_YEAR`,
  `_CENTS`), and `daily_floor_plan_interest`. No changes to
  existing functions.
- `backend/dealer_ai/models.py` — added
  `DealerOnboardingProfile.floor_plan_apr` nullable Decimal
  field. No other changes.
- `backend/dealer_ai/services/dealer_config.py` — added imports
  (`Decimal`, `InvalidOperation`), `_FALLBACK_FLOOR_PLAN_APR`
  constant, and `get_floor_plan_apr` resolver. No changes to
  existing resolvers.
- `backend/dealer_kit/settings.py` — added
  `DEALER_AI_FLOOR_PLAN_APR` env var line (M1 · 4F pattern).
- `backend/dealer_ai/migrations/0014_onboardingprofile_floor_plan_apr.py`
  — **new**, autogenerated by makemigrations.
- `backend/dealer_ai/tests/test_daily_floor_plan_interest.py` —
  **new**, 20 tests across 7 classes.
- `backend/dealer_ai/tests/test_floor_plan_apr_resolver.py` —
  **new**, 17 tests across 3 classes.

**Docs (3 files):**

- `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b — M2.4 row split
  into M2.4a (SHIPPED — this session) + M2.4b (NEXT —
  accrual command). Rationale for the split documented inline.
- `docs/handoffs/SESSION_049_milestone_2_financial_math.md` —
  this file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_050 =
  M2.4b.

**No changes to:** `services/vehicle_ledger.py`,
`services/llm_safety.py`, `services/tenancy.py`, `admin.py`,
`urls.py`, `views.py`, `permissions.py`, or any frontend file.

## Exact recommended scope for M2.4b (SESSION_050)

**M2.4b — Floor-plan accrual command.** ONE deliverable. Do NOT
scope in M2.5 (safety scrub), M2.6 (API), M2.7 (UI), or M2.8
(closeout).

### In scope

1. **`manage.py accrue_floor_plan_interest` management command**:
   - Required: `--dealership <slug>` (never a "run for all
     tenants" default).
   - Optional: `--as-of YYYY-MM-DD` (defaults to
     `timezone.now().date()`).
   - Optional: `--dry-run` (never writes; prints the summary).
   - For each vehicle in the tenant that has a
     `VehicleAcquisition` (no acquisition = no principal known
     = skip):
     - Find the last `VehicleCost` row with
       `category=CATEGORY_FLOOR_PLAN_INTEREST` and `reference`
       starting with `"ACCRUAL:"`. Take its `incurred_at.date()`
       as `last_accrual_date`. If no prior accrual row exists,
       use `acquisition.purchase_date`.
     - Compute `days_elapsed = as_of - last_accrual_date`.
       (`daily_floor_plan_interest` returns `0.00` if
       `days_elapsed <= 0`, so the command can safely call the
       engine even when there's nothing to accrue — idempotency
       falls out of the engine's contract.)
     - Compute `interest = daily_floor_plan_interest(
       purchase_price, apr, days_elapsed)`. **Principal =
       `acquisition.purchase_price` for v1** — curtailment
       tracking is deferred per planning §5.
     - If `interest > 0` and not `--dry-run`, post a
       `VehicleCost` row via
       `services.vehicle_ledger.add_cost(...)` with
       `category=CATEGORY_FLOOR_PLAN_INTEREST`,
       `reference=f"ACCRUAL:{as_of.isoformat()}"`,
       `is_estimate=False`, `notes` describing the accrual math
       (principal, apr, days_elapsed).
     - **Uses `services.vehicle_ledger.add_cost` — NOT direct
       `VehicleCost.objects.create`.** Preserves the cross-
       tenant guard and `full_clean` invariants of the M2.2
       service.

2. **Focused tests** (new file
   `test_accrue_floor_plan_interest_command.py`):
   - Tenant-required guard: no `--dealership` → command exits
     non-zero with clear error.
   - Dry-run purity: `--dry-run` posts zero rows even when
     accrual would normally happen.
   - Happy path: fresh tenant with N vehicles → N accrual rows
     posted (one per vehicle with an acquisition).
   - Idempotency: same `--as-of` re-run → zero new rows (the
     `days_elapsed=0` short-circuit in
     `daily_floor_plan_interest`).
   - Later `--as-of`: incremental delta only (rows posted only
     for the additional days).
   - Vehicles without an acquisition are skipped (no principal
     known).
   - Cross-tenant safety: rows post only to the specified
     dealership; other tenants' vehicles untouched.
   - Uses the M2.4a engine — verify by patching / assertion
     that `daily_floor_plan_interest` is the source of the
     posted `amount`.

### Out of scope for M2.4b

- Acquisition-price safety scrub (M2.5).
- API endpoints, serializers, URLs, permission composition
  (M2.6).
- Frontend, including the `floor_plan_apr` input in the Setup
  UI (M2.7).
- Curtailment tracking / principal-after-curtailment (planning
  §5 deferral).
- Celery / async scheduling (Milestone 7).
- `expected_gross` (Milestone 3).
- `Vendor` FK (Milestone 4).

### Verification steps at M2.4b close

- Focused command tests pass.
- Full backend suite passes (target: 1,606 + M2.4b additions).
- `makemigrations --check --dry-run` reports no changes (M2.4b
  is Python only, no schema drift).
- Manual smoke: `--dry-run` shows expected posting summary;
  live run posts rows; re-run same-day is a no-op.
- No touch to M2.4a math engine, M2.3 read model, M2.2 service
  contract, or any Milestone 1 primitive.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.4a (SHIPPED)
   + §7.b · M2.4b (NEXT)
7. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
   (this file)
8. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
9. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
10. `docs/handoffs/SESSION_046_milestone_2_schema.md`
11. `docs/handoffs/SESSION_045_milestone_2_planning.md`
12. Current source code — new imports available:
    - `dealer_ai.services.payment_engine::daily_floor_plan_interest`.
    - `dealer_ai.services.dealer_config::get_floor_plan_apr`.
    - `dealer_ai.models.DealerOnboardingProfile.floor_plan_apr`.
    - `settings.DEALER_AI_FLOOR_PLAN_APR`.

Planning docs are claims. Rules + research + code are facts.
