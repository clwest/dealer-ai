---
state: active
date: 2026-07-31
last_session_shipped: SESSION_051
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_052
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 6
next_increment_name: "Ledger API + permission matrix"
---

# Next session — SESSION_052 · Milestone 2 · Increment 6 (M2.6 — ledger API + permission matrix)

> **Milestone 2 · Increment 5 shipped at SESSION_051.**
> `_scrub_acquisition_price` + 12 verbal-framing patterns +
> branch in `apply_post_llm_scrubs` firing on every `kind`. 71
> focused tests: positive per phrase family, variants, multiple
> leakages in one response, every kind, coherent remainder,
> broad negative corpus covering asking price / monthly payment
> / trade / budget / warranty / etc., precedence tests locking
> that existing wholesale rewrites still fire first, public
> signature stability, zero DB queries. Test baseline: 1,625 →
> **1,696 pass**, 1 skipped, 0 fail. Zero regressions in any
> existing chat / vehicle_ask / ad / follow_up test.
> `makemigrations --check` reports no schema drift.
>
> **Load-bearing decisions locked so far in Milestone 2** (do
> NOT relitigate at M2.6):
>
> - M2.2: `total_investment` excludes `is_estimate=True` rows.
> - M2.3: `days_in_inventory` returns `None` when no acquisition
>   exists.
> - M2.4a: floor-plan engine is pure math; 365-day year;
>   ROUND_HALF_UP; negative principal/APR → ValueError.
> - M2.4b: workflow owns idempotency via `ACCRUAL:<date>`
>   reference tag; ledger writes only through `add_cost`.
> - M2.5: `acquisition_price` scrub joins the always-runs
>   section of `apply_post_llm_scrubs`; runs AFTER
>   `detect_unsafe_response` (dealer-cost wholesale rewrite
>   wins first); verbal-framing patterns anchored on
>   cost-ownership signals, never generic dollar detection.
>
> **SESSION_052 opens M2.6 — the ledger API + permission
> matrix.** Three admin endpoints under
> `/api/dealer-ai/admin/vehicles/<stock_number>/`. Reuses
> Milestone 1 · Increment 4D permission classes unchanged.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every ledger
   endpoint inherits the four-layer separation. §1 (identity /
   tenancy / permissions / data-scoping). §7 (composition
   patterns for admin endpoints). §8b (write-path explicit
   `dealership=` rule).
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons —
   #4 layer discipline, #5 focused permission matrix.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.6.
7. `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
   — authoritative M2.6 recommended scope.
8. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`,
   `SESSION_049_milestone_2_financial_math.md`,
   `SESSION_048_milestone_2_vehicle_read_model.md`,
   `SESSION_047_milestone_2_ledger_service.md`,
   `SESSION_046_milestone_2_schema.md`,
   `SESSION_045_milestone_2_planning.md`.

## What SESSION_052 should do — M2 · Increment 6

Per `MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.6 and the
SESSION_051 handoff's "Exact recommended scope for M2.6".

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
     § "Exact recommended scope for M2.6" (authoritative scope).
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 (operator
     ledger UI surface — the API shape lives here).
   - `docs/roadmap/AUTHENTICATION_MODEL.md` §1, §7, §8b.
   - `backend/dealer_ai/permissions.py::IsSalesManagerOrOwnerAtActiveDealership`
     — the composed class M2.6 endpoints will reuse unchanged.
   - `backend/dealer_ai/services/tenancy.py::get_current_dealership`
     — called once at the top of every view per §8b.
   - `backend/dealer_ai/services/vehicle_ledger.py` — the
     three service functions the endpoints wrap
     (`record_acquisition`, `add_cost`, `compute_totals`).
   - `backend/dealer_ai/views.py::admin_lead_list` /
     `admin_lead_detail` / `admin_lead_assign` — the M1 · 4D
     admin endpoint pattern M2.6 mirrors.
   - `backend/dealer_ai/serializers.py` — check existing
     serializer conventions (or plain dict projections) before
     picking a shape.
   - `backend/dealer_ai/tests/test_admin_endpoints_auth.py` —
     the M1 · 4D permission-matrix test shape M2.6 mirrors.

2. **Ship three endpoints in `views.py`:**
   - `admin_vehicle_ledger` (GET) — returns
     `{acquisition, costs, totals, days_in_inventory}`.
   - `admin_vehicle_acquisition_upsert` (POST) — wraps
     `record_acquisition`.
   - `admin_vehicle_cost_create` (POST) — wraps `add_cost`.
   - Each: `@api_view(['GET'|'POST'])` +
     `permission_classes=[IsAuthenticated &
     IsSalesManagerOrOwnerAtActiveDealership]` +
     `dealership = get_current_dealership(request)` at the top
     + `Vehicle.objects.filter(dealership=dealership).get(
     stock_number=<url_kwarg>)` for the target lookup.

3. **Ship serializer/dict projections** (SESSION_052 decides
   the shape). Whichever picks, keep it consistent with the
   read-model contract from M2.3.

4. **Register URLs** in `dealer_ai/urls.py` under the
   `/admin/` prefix.

5. **Focused six-case permission matrix per endpoint**:
   - Unauth → 401.
   - Advisor at same dealership → 403.
   - Advisor at wrong dealership → 403.
   - Sales_manager at same dealership → 200.
   - Dealer_owner at same dealership → 200.
   - Cross-tenant stock_number → 404 (fail closed).

6. **Verify.**
   - Focused permission-matrix tests pass.
   - `python3 manage.py test dealer_ai` → ≥ 1,696 + M2.6
     additions, 0 fail.
   - `makemigrations --check --dry-run` reports no changes.
   - Manual `curl` smoke: use `smoke_owner` session cookie to
     hit all three endpoints against dev DB.
   - No touch to any file outside `views.py`, `urls.py`,
     `serializers.py`, and new test file.

7. **Close SESSION_052 with:**
   - Handoff at
     `docs/handoffs/SESSION_052_milestone_2_ledger_api.md`.
   - Overwrite this file with SESSION_053 = M2.7 priority
     (operator ledger UI).

## Explicit non-goals for SESSION_052 (M2 · Increment 6)

- ❌ Do NOT ship any M2.7 scope: no frontend, no
  `lib/api.ts` additions, no route registration in `main.tsx`,
  no inventory-card ledger link.
- ❌ Do NOT ship M2.8 (milestone verification + closeout).
- ❌ Do NOT modify any Milestone 1 or Milestone 2 permission
  class. Reuse `IsSalesManagerOrOwnerAtActiveDealership`
  unchanged.
- ❌ Do NOT introduce a `recon_manager` permission class —
  deferred to Milestone 4.
- ❌ Do NOT bypass the ledger service. Endpoints wrap
  `record_acquisition` and `add_cost` — never
  `VehicleAcquisition.objects.create()` or
  `VehicleCost.objects.create()` directly. Preserves the
  cross-tenant guard + `full_clean` invariants.
- ❌ Do NOT change `services/vehicle_ledger.py` contract
  beyond adding tests. If a serializer decision requires a new
  service function, evaluate whether it belongs in M2.6 or
  should be a service extension in its own increment.
- ❌ Do NOT modify the M2.5 scrub or any pre-existing scrub.
- ❌ Do NOT introduce new migrations. M2.6 is pure Python +
  URL + view work.
- ❌ Do NOT introduce `expected_gross` (M3), `Vendor` FK (M4),
  or curtailment tracking (deferred).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_052 with the read-first list above. Ship the
three admin ledger endpoints + serializer projections + URLs +
focused permission-matrix tests. Nothing else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.6
7. `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
   (M2.6 authoritative scope)
8. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
9. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
10. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
11. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
12. `docs/handoffs/SESSION_046_milestone_2_schema.md`
13. `docs/handoffs/SESSION_045_milestone_2_planning.md`
14. Current source code — everything shipped in M2.1–M2.5 is
    available as documented in the handoffs. M2.6 introduces
    NO new imports; it composes existing service + permission +
    tenancy primitives.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_051 — M2.5 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1 through M2.5.**
- **Frontend (prod):** NONE.
- **Test baseline:** **1,696 pass** (1,625 baseline + 71 new
  M2.5 tests), 1 skipped, 0 fail.
- **DRF defaults + CSRF + endpoint-level permissions:** all as
  documented in `AUTHENTICATION_MODEL.md`. Unchanged.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed.
- **Ledger model surface (M2.1):** `VehicleAcquisition`,
  `VehicleCost`, `SOURCE_*` × 8, `CATEGORY_*` × 26.
- **Category groupings (M2.2):** `FLOORING_CATEGORIES` (5),
  `RECON_CATEGORIES` (13), `ADMIN_CATEGORIES` (7),
  `PHOTOGRAPHY_CATEGORIES` (1).
- **Ledger service (M2.2):** `record_acquisition`,
  `add_cost`, `compute_totals`, `category_group_of`,
  `LedgerTotals`, `CrossTenantLedgerError`, `ZERO`.
- **Vehicle read-model (M2.3):** `@cached_property
  ledger_totals` + 9 delegator properties +
  `days_in_inventory`.
- **Financial engine + APR config (M2.4a):**
  `daily_floor_plan_interest`, `get_floor_plan_apr`,
  `DealerOnboardingProfile.floor_plan_apr`.
- **Accrual command (M2.4b):**
  `manage.py accrue_floor_plan_interest --dealership=<slug>
  [--as-of=DATE] [--dry-run]`.
- **Safety pipeline (M2.5 addition):** `acquisition_price`
  scrub joins the always-runs section of
  `apply_post_llm_scrubs`. Fires on every `kind`. Runs AFTER
  `detect_unsafe_response` (wholesale-rewrite precedence
  preserved). Text-only, zero DB access.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in the
  respective planning + retrospective + handoff docs.
