---
title: "SESSION_050 handoff — Milestone 2 · Increment 4b (floor-plan accrual workflow)"
status: historical
type: handoff
date: 2026-07-31
session: 050
milestone: 2
milestone_status: in_progress
increment: 4b
increment_status: shipped
commit: 30ff9ee
---

# SESSION_050 — Milestone 2 · Increment 4b (M2.4b — floor-plan accrual workflow)

## What shipped

One thing: the operational workflow that records floor-plan
interest into the vehicle ledger. Consumes the M2.4a math engine +
APR resolver. Zero financial logic in this session — the command
orchestrates, the ledger service persists, the engine calculates.
Three responsibilities, three separate places.

## Command implemented

`python manage.py accrue_floor_plan_interest --dealership=<slug>
[--as-of=YYYY-MM-DD] [--dry-run]` at
`backend/dealer_ai/management/commands/accrue_floor_plan_interest.py`.

**Arguments** (only three, all as-designed):

- `--dealership` (required) — never a "run for all tenants" default.
  Command errors out with a clear message if the slug is unknown.
- `--as-of` (optional) — accrual date in `YYYY-MM-DD`. Defaults to
  `timezone.now().date()`. Malformed value → CommandError with a
  human-readable message.
- `--dry-run` (optional flag) — plan the accrual without posting
  any rows. Prints the same summary the live run would.

**Structure** — plan / execute split:

1. `AccrualPlan` (frozen dataclass) — one plan per vehicle-to-accrue,
   with `vehicle`, `principal`, `apr`, `days_elapsed`, `amount`.
   Today: transient Python object. Tomorrow: could be the shape of
   a persisted `AccrualEvent` row without changing the command's
   user-facing surface.
2. `_plan_accrual(vehicle, dealership, apr, as_of, summary)` —
   pure computation. Runs duplicate detection first, then
   last-accrual-date resolution, then engine call. Returns
   `Optional[AccrualPlan]`. No writes.
3. `_execute(plan, dealership, as_of)` — posts via
   `services.vehicle_ledger.add_cost(...)`. Called only in live
   mode.

**Ledger writes** — exclusively through
`services.vehicle_ledger.add_cost`. Direct `VehicleCost.objects.create`
would bypass the M2.2 cross-tenant guard + `full_clean` invariants;
the command does NOT bypass them.

## Idempotency strategy

**Explicit workflow-layer duplicate detection**, per the SESSION_050
brief.

- Before each plan step, the command queries for a
  `VehicleCost` row with:
  - `vehicle = <this vehicle>`
  - `dealership = <this dealership>`
  - `category = CATEGORY_FLOOR_PLAN_INTEREST`
  - `reference = f"ACCRUAL:{as_of.isoformat()}"`
- If one exists, the vehicle is skipped and counted in
  `skipped_duplicate`. Never creates a duplicate ledger entry.
- The engine's `days_elapsed <= 0 → Decimal("0.00")` short-circuit
  is a secondary defense (belt + suspenders) — it catches the case
  where `last_accrual_date == as_of`, which would produce a
  zero-dollar row that itself would then anchor future duplicate
  detection.

**Load-bearing invariant**: same-day re-runs post ZERO new rows,
always. Locked by
`IdempotencySameDayReRun.test_second_same_day_run_posts_zero_new_rows`
+ `.test_second_same_day_run_reports_duplicate_skip`.

**Reference tag as canonical anchor**: `ACCRUAL:{iso-date}` is the
one-place marker for "this vehicle accrued for this as_of date."
Any future work that adds a dedicated `AccrualEvent` model must
either preserve this reference format or data-migrate every
existing row.

## Last-accrual resolution

Contract locked by
`LastAccrualResolution.test_vehicle_without_acquisition_is_skipped`
+ `.test_first_run_uses_purchase_date_as_last_accrual`:

1. **Most recent floor-plan accrual row** — the row's
   `incurred_at.date()`. Query:
   `VehicleCost.objects.filter(vehicle, dealership,
   category=CATEGORY_FLOOR_PLAN_INTEREST,
   reference__startswith="ACCRUAL:").order_by("-incurred_at")`.
2. **`VehicleAcquisition.purchase_date`** — used the first time
   the command runs on a fresh vehicle.
3. **Skip** — no acquisition = no principal known. Counted in
   `skipped_no_acquisition`. The command never guesses.

## Transaction strategy

**Whole-run atomicity, live-mode only.**

- Live mode wraps the entire per-vehicle loop in one
  `transaction.atomic()`. Any exception raised inside — from
  `add_cost`, from the resolver, or from any planning code that
  touches the DB — rolls back every accrual posted in this run.
  The command exits non-zero; the operator sees the exception.
- Dry-run mode skips the atomic block entirely (no writes → nothing
  to roll back).

**Rationale**: partial state is worse than none for a batch
operation the operator will re-run. A half-committed accrual would
corrupt the duplicate-detection invariant on the next run (some
rows exist with today's reference, others don't; the second run
would top up the missing ones but the operator wouldn't know
about the split).

Locked by `TransactionSafety.test_mid_run_failure_rolls_back_all_prior_accruals`
(patches `add_cost` to raise on the second call and verifies zero
rows survive) + `.test_dry_run_does_not_need_atomic` (patches
`transaction.atomic` and asserts `--dry-run` never calls it).

## Reporting summary

Concise stdout format — printed after every run, live or dry:

```
Floor-plan accrual for dealership '<slug>' (as-of YYYY-MM-DD) [DRY RUN — nothing written]
  Evaluated:  N
  Accrued:    M ($X.XX total)
  Skipped:    K (no acquisition: A, no elapsed days: B, duplicate: C)
```

- `Evaluated` = every vehicle in the dealership (with or without
  acquisition).
- `Accrued` = vehicles that received a new ledger row.
- `Skipped` = sum of the three named reasons; each broken out.
- `Accrued + Skipped = Evaluated` invariant (locked implicitly by
  the summary counters). No verbose per-vehicle logging — this
  command will eventually run under a scheduler and its output is
  what an operator (or a monitoring pipeline) reads.

`[DRY RUN — nothing written]` marker only appears in dry-run mode.

## Operational-event framing

Per the SESSION_050 brief's architectural recommendation: floor-
plan accrual is structured as an operational event, not merely a
generated cost. The command's plan/execute split gives a future
`AccrualEvent` model a natural insertion point:

- Today: `_plan_accrual` returns a Python `AccrualPlan` that the
  command executes in-memory.
- Tomorrow: `_plan_accrual` could return an `AccrualEvent`
  instance that `_execute` persists, then also posts the derived
  `VehicleCost` row via `add_cost`. The command's arguments and
  summary output don't change; only the two private methods do.

## Tests added — 19 new, all passing

`test_accrue_floor_plan_interest_command.py`, 9 classes:

| Class | Tests | Locks |
|-------|-------|-------|
| `ArgumentValidation` | 3 | Dealership required; unknown slug → CommandError; malformed `--as-of` → CommandError |
| `DryRunPurity` | 2 | Zero rows written; summary shows planned Accrued count + [DRY RUN] marker |
| `HappyPath` | 4 | One row per eligible vehicle; posted amounts match engine byte-for-byte (using `daily_floor_plan_interest` as source of truth); rows carry `ACCRUAL:<date>` reference; rows are `is_estimate=False` so M2.2 `total_investment` picks them up |
| `IdempotencySameDayReRun` | 2 | Second same-day run posts zero new rows; summary reports `duplicate: 1` |
| `IncrementalDelta` | 1 | Second run with later `--as-of` posts only the delta days |
| `LastAccrualResolution` | 2 | No-acquisition vehicle is skipped and counted; first run uses purchase_date as last-accrual |
| `CrossTenantSafety` | 2 | Running for A does not touch B; summary reports only the target dealership |
| `SummaryReporting` | 1 | Every summary line label present |
| `TransactionSafety` | 2 | Mid-run failure (mocked `add_cost` raising) rolls back all prior accruals; dry-run does NOT invoke `transaction.atomic` |

Total: 19 tests, 9 classes.

## Backend baseline

- **`python3 manage.py test dealer_ai` → 1,625 pass** (1,606
  baseline + 19 new M2.4b tests), 1 skipped, 0 fail. Zero
  regressions.
- **`makemigrations dealer_ai --check --dry-run` → "No changes
  detected".** Zero schema drift.
- **Live dev-DB smoke passed** — `python3 manage.py
  accrue_floor_plan_interest --dealership=default --dry-run`
  evaluated 135 vehicles, correctly skipped all 135 for "no
  acquisition" (M2.1 tables are greenfield; demo seeders have
  not been updated to create acquisitions yet — that would be
  a separate deferred idea if it becomes friction).

## Compatibility result

Every existing invariant holds. Explicit rechecks:

- **M2.4a financial engine unchanged.**
  `services/payment_engine.py::daily_floor_plan_interest`
  untouched. All 20 M2.4a math tests pass.
- **M2.4a config layer unchanged.**
  `services/dealer_config.py::get_floor_plan_apr` untouched.
  All 17 resolver / field tests pass.
- **M2.2 ledger service unchanged.**
  `services/vehicle_ledger.py` untouched. All 44 tests pass.
- **M2.3 Vehicle read model unchanged.** All 29 tests pass.
- **M2.1 model layer unchanged.** All 30 tests pass.
- **Safety pipeline unchanged** (no changes to `llm_safety.py`).
- **Auth substrate unchanged** (no changes to `permissions.py`,
  `tenancy.py`, `settings.py::REST_FRAMEWORK`).
- **Public routes unchanged.**
- **Frontend untouched.**
- **No new migration** — M2.4b is Python-only (management
  command).

## Files touched this session

**Backend (2 files new):**

- `backend/dealer_ai/management/commands/accrue_floor_plan_interest.py`
  — **new**. 375 lines with docstrings.
- `backend/dealer_ai/tests/test_accrue_floor_plan_interest_command.py`
  — **new**. 19 tests across 9 classes.

**Docs (3 files):**

- `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.4b row →
  SHIPPED with full summary of what landed (idempotency,
  last-accrual resolution, transaction strategy,
  operational-event framing, summary reporting).
- `docs/handoffs/SESSION_050_milestone_2_accrual_command.md` —
  this file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_051 =
  M2.5.

**No changes to:** `services/payment_engine.py`,
`services/dealer_config.py`, `services/vehicle_ledger.py`,
`services/tenancy.py`, `services/llm_safety.py`,
`models.py`, `admin.py`, migrations, `urls.py`, `views.py`,
`permissions.py`, `settings.py`, or any frontend file.

## Exact recommended scope for M2.5 (SESSION_051)

**M2.5 — Acquisition-price safety scrub (safety pipeline stage 17).**
Per `MILESTONE_2_PLANNING.md` §1.5 + §7.b · M2.5. ONE deliverable.

### In scope

1. **`services/llm_safety.py::_scrub_acquisition_price`** — new
   function mirroring the existing
   `_scrub_indie_prohibited` / `_scrub_invented_promotion` /
   `_scrub_invented_appointment` shape:
   - Regex pattern list `_ACQUISITION_PRICE_PATTERNS` catching
     ledger-leakage phrasing per planning §1.5: "we paid $X",
     "our cost was $X", "in it for $X", "we've got $X in",
     "purchase price $X", "acquired for $X", "floor plan
     interest of $X", "recon spent $X on", "our investment on
     this piece", "total investment $X".
   - Each pattern replaces with a safe substitute (e.g.
     "a great value" / deletion / "our current pricing") or
     sets the caller's `dropped_reason` when the pattern is a
     wholesale-rewrite class.

2. **Branch inside `apply_post_llm_scrubs`** — scrub fires on
   EVERY `kind` (`chat`, `vehicle_ask`, `ad`, `follow_up`).
   Ledger leakage is equally wrong everywhere. Runs AFTER the
   existing `detect_unsafe_response` (dealer-cost) check so the
   pre-existing wholesale rewrite still takes precedence when
   its pattern fires first.

3. **Focused positive AND negative tests**:
   - Positive: scrub fires on synthetic ledger-leakage strings.
   - Negative: scrub does NOT fire on legitimate strings — every
     safe phrase in the pre-M2 test corpus, benign price
     mentions like "priced under $20,000", "asking $24,900",
     "monthly payment ~$450", etc.

### Out of scope for M2.5

- API endpoints, serializers, URLs, permission composition
  (M2.6).
- Frontend (M2.7).
- Any modification to the pre-existing 16 scrub stages. M2.5
  ADDS stage 17; does not modify the others.
- `expected_gross` (Milestone 3).
- `Vendor` FK (Milestone 4).
- Bulk-run helper for the accrual command.
- Any change to the M2.4b accrual command (its behavior is
  locked).
- Any modification to `services/vehicle_ledger.py`,
  `services/payment_engine.py`, or `services/dealer_config.py`.

### Verification steps at M2.5 close

- Focused scrub tests pass (positive + negative).
- Full backend suite (target: 1,625 + M2.5 additions). **Zero
  regressions in any chat / vehicle_ask / ad / follow_up test**
  — the new scrub must not rewrite an existing chat reply that
  happens to look like a ledger reference. This is the load-
  bearing safety check for M2.5 — the 16 existing scrubs +
  scrub-stack integration tests are the moat, and M2.5 adds to
  it without disturbing it.
- `makemigrations --check --dry-run` reports no changes.
- No changes to any file outside `services/llm_safety.py` and
  the new test file.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.5
7. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
   (this file — M2.5 authoritative recommended scope)
8. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
9. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
10. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
11. `docs/handoffs/SESSION_046_milestone_2_schema.md`
12. `docs/handoffs/SESSION_045_milestone_2_planning.md`
13. Current source code — new imports available:
    - `dealer_ai.management.commands.accrue_floor_plan_interest`
      (management command; not typically imported, invoked
      via `call_command` in tests).

Planning docs are claims. Rules + research + code are facts.
