---
state: active
date: 2026-07-31
last_session_shipped: SESSION_050
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_051
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 5
next_increment_name: "Acquisition-price safety scrub (pipeline stage 17)"
---

# Next session — SESSION_051 · Milestone 2 · Increment 5 (M2.5 — acquisition-price safety scrub)

> **Milestone 2 · Increment 4b shipped at SESSION_050.**
> `manage.py accrue_floor_plan_interest --dealership=<slug>
> [--as-of=DATE] [--dry-run]` — plan/execute split with
> `AccrualPlan` dataclass (operational-event abstraction).
> Explicit workflow-owned idempotency via
> `reference=f"ACCRUAL:{as_of.isoformat()}"` duplicate check.
> Last-accrual resolution: (1) most recent accrual row, (2)
> purchase_date, (3) skip. Whole-run atomic transaction in live
> mode. 19 focused workflow tests using the M2.4a engine as
> source of truth. Test baseline: 1,606 → **1,625 pass**, 1
> skipped, 0 fail. Zero regressions. `makemigrations --check`
> reports no schema drift.
>
> **Load-bearing decisions locked so far in Milestone 2** (do
> NOT relitigate at M2.5):
>
> - M2.2: `total_investment` excludes `is_estimate=True` rows.
> - M2.3: `days_in_inventory` returns `None` when no acquisition
>   exists.
> - M2.4a: floor-plan interest engine is pure math with 365-day
>   convention, ROUND_HALF_UP, negative principal/APR → ValueError.
> - M2.4b: workflow owns idempotency (duplicate detection via
>   `ACCRUAL:<date>` reference tag); one accrual per
>   (vehicle, as_of); ledger writes only through `add_cost`.
>
> **SESSION_051 opens M2.5 — the acquisition-price safety scrub
> (safety pipeline stage 17).** ONE deliverable. Adds to the
> 16-stage scrub stack; does not modify existing stages.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §1 four-layer
   separation (M2.5 is the safety layer; identity/tenancy/
   permissions/data-scoping stay untouched).
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.5 (acquisition-
   price scrub design memo) + §7.b · M2.5 (scope boundary).
7. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
   § "Exact recommended scope for M2.5" — authoritative scope.
8. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`,
   `SESSION_048_milestone_2_vehicle_read_model.md`,
   `SESSION_047_milestone_2_ledger_service.md`,
   `SESSION_046_milestone_2_schema.md`,
   `SESSION_045_milestone_2_planning.md`.

## What SESSION_051 should do — M2 · Increment 5

Per `MILESTONE_2_PLANNING.md` §1.5 + §7.b · M2.5 and the
SESSION_050 handoff's "Exact recommended scope for M2.5".

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
     § "Exact recommended scope for M2.5" (authoritative
     scope).
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §1.5
     (acquisition-price scrub design memo).
   - `backend/dealer_ai/services/llm_safety.py` FULL — the
     module the scrub joins. Understand:
     - `apply_post_llm_scrubs(text, *, kind)` signature and
       return shape.
     - How each existing scrub is structured
       (`_scrub_indie_prohibited` /
       `_scrub_invented_promotion` /
       `_scrub_invented_appointment`) — the M2.5 scrub mirrors
       this shape.
     - The `_INDIE_PROHIBITED_PATTERNS` /
       `_INVENTED_PROMOTION_PATTERNS` /
       `_INVENTED_APPOINTMENT_PATTERNS` module constants —
       the M2.5 scrub adds an `_ACQUISITION_PRICE_PATTERNS`
       constant of the same shape.
   - `backend/dealer_ai/tests/test_llm_safety.py` (if it
     exists; otherwise the test files that exercise
     `apply_post_llm_scrubs` — grep for it) to understand the
     existing scrub-test conventions.

2. **Design the pattern list** — regex patterns catching
   ledger-leakage phrasing per planning §1.5. The safe
   approach is:
   - Match phrases that clearly indicate internal cost
     ("we paid $X", "our cost was $X", "in it for $X", "we've
     got $X in", "purchase price $X", "acquired for $X",
     "floor plan interest of $X", "recon spent $X",
     "our investment on this piece", "total investment $X").
   - Do NOT match benign price mentions ("priced at $24,900",
     "asking $24,900", "monthly payment ~$450", "$0 down") —
     those are customer-facing figures that MUST remain.
   - Prefer specific-verb patterns over broad "$X mentioned
     near dollar" matches. Ledger leakage is verbal
     ("we paid", "our cost", "invested") — that verbal
     framing is the safer signal than proximity to a dollar
     amount.

3. **Add `_scrub_acquisition_price`** — mirror the shape of
   `_scrub_invented_promotion`. Returns `Tuple[str, bool]`.
   Preserves punctuation/whitespace cleanup like the existing
   scrubs.

4. **Wire into `apply_post_llm_scrubs`** — fires on every
   `kind` (`chat`, `vehicle_ask`, `ad`, `follow_up`). Runs
   AFTER `detect_unsafe_response` (dealer-cost wholesale
   rewrite) — so the existing dealer-cost handler still takes
   precedence when its pattern fires. Runs as a partial scrub
   (not a wholesale rewrite class).

5. **Focused positive AND negative tests** in a new file
   `backend/dealer_ai/tests/test_acquisition_price_scrub.py`:

   **Positive** (scrub fires):
   - Each pattern in the list has at least one positive test
     case with the expected output.
   - Fires on all four `kind` values.

   **Negative** (scrub does NOT fire):
   - "priced at $24,900" — customer-facing sticker.
   - "monthly payment $450" — customer-facing calc.
   - "asking $18,500" — sticker.
   - "$0 down" (already caught by
     `_INVENTED_PROMOTION_PATTERNS` but for a different
     reason; M2.5 scrub does NOT overlap).
   - Plausible chat replies from existing test corpora that
     mention dollar amounts safely.
   - Cross-check: run the M2.5 tests + confirm zero existing
     scrub tests regress.

6. **Verify.**
   - Focused scrub tests pass.
   - `python3 manage.py test dealer_ai` → ≥ 1,625 + M2.5
     additions, 0 fail. **Zero regressions in any chat /
     vehicle_ask / ad / follow_up test.** This is the
     load-bearing safety check for M2.5.
   - `makemigrations --check --dry-run` reports no changes.
   - No touch to any file outside `services/llm_safety.py` and
     the new test file.

7. **Close SESSION_051 with:**
   - Handoff at
     `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`.
   - Overwrite this file with SESSION_052 = M2.6 priority
     (ledger API + permission matrix).

## Explicit non-goals for SESSION_051 (M2 · Increment 5)

- ❌ Do NOT modify any of the pre-existing 16 scrub stages.
  M2.5 ADDS stage 17. If a real edge case surfaces that would
  require modifying an existing scrub, document it as a
  deferred idea; do not touch existing behavior mid-M2.
- ❌ Do NOT change the `apply_post_llm_scrubs` signature or
  return shape. Extension only: a new pattern list + a new
  scrub function + a new branch that gates on `kind`.
- ❌ Do NOT ship any M2.6 scope: no endpoints, no serializers,
  no URLs, no permission composition.
- ❌ Do NOT ship any M2.7 scope: no frontend.
- ❌ Do NOT modify the M2.4a math engine, M2.4b accrual
  command, M2.3 read model, M2.2 service contract, or
  Milestone 1 primitives.
- ❌ Do NOT introduce `expected_gross` (Milestone 3), `Vendor`
  FK (Milestone 4), curtailment tracking (deferred), or
  Celery (Milestone 7).
- ❌ Do NOT scope in a scrub "audit log" that records fires
  (Milestone 8 operational-intelligence concern).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_051 with the read-first list above. Ship
`_scrub_acquisition_price` + `_ACQUISITION_PRICE_PATTERNS` +
branch in `apply_post_llm_scrubs` + focused positive/negative
tests. **Zero regressions in any existing scrub test.**
Nothing else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.5 + §7.b · M2.5
7. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
   (M2.5 authoritative scope)
8. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
9. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
10. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
11. `docs/handoffs/SESSION_046_milestone_2_schema.md`
12. `docs/handoffs/SESSION_045_milestone_2_planning.md`
13. Current source code — new imports available:
    - `dealer_ai.services.payment_engine::daily_floor_plan_interest`.
    - `dealer_ai.services.dealer_config::get_floor_plan_apr`.
    - `dealer_ai.services.vehicle_ledger::add_cost`,
      `record_acquisition`, `compute_totals`, `LedgerTotals`,
      `CrossTenantLedgerError`, `category_group_of`, `ZERO`.
    - `dealer_ai.models.Vehicle`: 10 read-model properties.
    - `dealer_ai.models::VehicleAcquisition`, `VehicleCost`,
      `SOURCE_*` (8), `CATEGORY_*` (26), category groupings.
    - `dealer_ai.models.DealerOnboardingProfile.floor_plan_apr`.
    - `settings.DEALER_AI_FLOOR_PLAN_APR`.
    - `manage.py accrue_floor_plan_interest --dealership=<slug>
      [--as-of=DATE] [--dry-run]`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_050 — M2.4b shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1 through M2.4b.**
- **Frontend (prod):** NONE.
- **Test baseline:** **1,625 pass** (1,606 baseline + 19 new
  M2.4b tests), 1 skipped, 0 fail.
- **DRF defaults + CSRF + endpoint-level permissions:** all as
  documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`
  in `settings.py`, SQLite at
  `backend/db.migration_check.sqlite3` (gitignored). Use with
  `--database=migration_check` for destructive probes.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`. All follow the same
  empty-string-default → resolver-falls-through pattern.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed.
- **Ledger model surface (M2.1):** `VehicleAcquisition`,
  `VehicleCost`, `SOURCE_*` × 8, `CATEGORY_*` × 26.
- **Category groupings (M2.2):** `FLOORING_CATEGORIES` (5),
  `RECON_CATEGORIES` (13), `ADMIN_CATEGORIES` (7),
  `PHOTOGRAPHY_CATEGORIES` (1).
- **Ledger service (M2.2):** `record_acquisition`, `add_cost`,
  `compute_totals`, `category_group_of`, `LedgerTotals`,
  `CrossTenantLedgerError`, `ZERO`.
- **Vehicle read-model (M2.3):** `@cached_property
  ledger_totals` + 9 delegator properties + `days_in_inventory`.
- **Financial engine + APR config (M2.4a):**
  `daily_floor_plan_interest`, `get_floor_plan_apr`,
  `DealerOnboardingProfile.floor_plan_apr`.
- **Accrual command (M2.4b):**
  `manage.py accrue_floor_plan_interest --dealership=<slug>
  [--as-of=DATE] [--dry-run]`. Idempotent via
  `ACCRUAL:<date>` reference tag. Live smoke against dev DB
  (135 vehicles): all correctly skipped for "no acquisition"
  (M2.1 tables are greenfield; demo seeders don't create
  acquisition rows).
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in
  the respective planning + retrospective + handoff docs.
