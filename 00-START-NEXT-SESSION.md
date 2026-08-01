---
state: active
date: 2026-07-31
last_session_shipped: SESSION_046
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_047
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 2
next_increment_name: "API + service + safety + accrual"
---

# Next session — SESSION_047 · Milestone 2 · Increment 2 (M2.2 — API + service + safety + accrual)

> **Milestone 2 · Increment 1 shipped at SESSION_046.**
> `VehicleAcquisition` + `VehicleCost` models + migrations
> `0012_vehicleacquisition.py` + `0013_vehiclecost.py` + admin
> registrations + 30 focused model tests. Test baseline: 1,466 →
> **1,496 pass**, 1 skipped, 0 fail. Zero regressions. Migrations
> round-trip cleanly against the new `DATABASES["migration_check"]`
> alias (M1 lesson 2 in action).
>
> **SESSION_047 opens M2.2 — the biggest increment of Milestone 2.**
> Three API endpoints + the service layer + the safety-stack scrub +
> the floor-plan-interest accrual command + a new nullable field on
> `DealerOnboardingProfile` + a new env var. Do NOT scope in the
> M2.3 frontend surface (that is SESSION_048).

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
   boundary (in-scope / out-of-scope enumeration).
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every ledger endpoint
   inherits the layer discipline. §1 four-layer separation. §7
   permission composition patterns. §8b: write-path callers MUST
   pass `dealership=` explicitly (`pre_save` autofill is fallback
   only). §8b data-scoping patterns for `.filter(dealership=...)`.
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 — the eight
   lessons. Especially: #4 (layer discipline — the M2.2 scrub is
   the moat's layer; the endpoint permissions are the authorization
   layer; the `.filter(dealership=...)` is the data-scoping layer;
   don't collapse them), #5 (focused permission matrix per
   endpoint), #6 (public/protected route boundaries — every M2.2
   endpoint is `/admin/*` and protected).
6. `docs/roadmap/MILESTONE_2_PLANNING.md` — acceptance contract for
   M2. §7 · M2.2 is SESSION_047's scope boundary.
7. `docs/handoffs/SESSION_046_milestone_2_schema.md` — records the
   M2.1→M2.2 scope-slide (`LedgerTotals` + `compute_totals` +
   Vehicle `@property` methods absorbed into M2.2 per the M2.1
   brief's persistence-only narrowing).
8. `docs/BUSINESS_DOMAIN_MAP.md`, `docs/CAPABILITY_MATRIX.md`,
   `docs/research/*_MAPPING.md`.

## What SESSION_047 should do — M2 · Increment 2

Per `MILESTONE_2_PLANNING.md` §7 · M2.2 plus the scope-slide
absorbed from M2.1 (see SESSION_046 handoff "Deviations"). Nine
originally-M2.2 items + three absorbed-from-M2.1 items = twelve
total deliverables.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/roadmap/MILESTONE_2_PLANNING.md` (full — this is the
     acceptance contract for the whole milestone).
   - `docs/handoffs/SESSION_046_milestone_2_schema.md` (the
     "Deviations" section explains why M2.2's scope grew by
     ~150 LOC).
   - `docs/roadmap/AUTHENTICATION_MODEL.md` §1, §7, §8b.
   - `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons #4,
     #5, #6.
   - `backend/dealer_ai/models.py::VehicleAcquisition` +
     `VehicleCost` + the new constants (canonical imports for
     the service layer).
   - `backend/dealer_ai/permissions.py::IsSalesManagerOrOwnerAtActiveDealership`
     (reused unchanged for every M2.2 endpoint).
   - `backend/dealer_ai/services/tenancy.py::get_current_dealership`
     (called once at the top of every M2.2 view).
   - `backend/dealer_ai/services/llm_safety.py::apply_post_llm_scrubs`
     (the extension seam for the acquisition-price scrub).
   - `backend/dealer_ai/services/payment_engine.py` (the extension
     seam for `daily_floor_plan_interest`).
   - Recent admin endpoint precedent — see how M1 · 4D wired
     `admin_lead_list` / `admin_lead_detail` / `admin_lead_assign`
     in `views.py` (permission composition, tenant resolution,
     queryset scoping). M2.2's three endpoints follow that exact
     pattern.

2. **Build the service layer + computed properties (absorbed from
   M2.1).**
   - `services/vehicle_ledger.py` — new module. Ships:
     - `LedgerTotals` dataclass with the six numbers
       (`total_acquisition_cost`, `total_flooring_cost`,
       `total_recon_cost`, `total_admin_cost`,
       `total_investment`, `projected_gross`,
       `days_in_inventory`).
     - `compute_totals(vehicle, *, dealership) -> LedgerTotals`
       — the ONLY function ready to consume category-set
       groupings.
     - `record_acquisition(vehicle, *, dealership, source,
       purchase_price, purchase_date, ...)` — OneToOne upsert
       semantics (creates or updates the acquisition row).
     - `add_cost(vehicle, *, dealership, category, amount,
       incurred_at, ...)` — creates a new `VehicleCost` row.
   - Every function threads `dealership=` explicitly per
     `AUTHENTICATION_MODEL.md` §8b. Every function refuses
     cross-tenant (raises when `vehicle.dealership_id !=
     dealership.id` — same fail-closed shape as
     `AdminLeadDetailFailsClosedAcrossTenants`).
   - Category-set groupings live in `models.py` alongside the
     individual `CATEGORY_*` constants:
     `FLOORING_CATEGORIES`, `RECON_CATEGORIES`,
     `ADMIN_CATEGORIES`. Or lift into `ledger_categories.py` if
     `models.py` gets crowded — SESSION_047's call.
   - `@property` methods on `Vehicle` (`total_investment`,
     `projected_gross`, category subtotals, `days_in_inventory`)
     delegate to `compute_totals`.

3. **Extend `services/payment_engine.py`.**
   - Add `daily_floor_plan_interest(principal: Decimal, apr:
     Decimal, days_elapsed: int) -> Decimal` — one-line formula
     `principal * (apr / Decimal(365)) * days_elapsed`. Pure,
     no I/O. Handles `apr == 0` → returns 0, negative
     `days_elapsed` → returns 0.
   - Tests: happy path, zero APR, zero days, negative days,
     Decimal precision preservation.

4. **Extend `services/dealer_config.py`.**
   - Add `get_floor_plan_apr(dealership: Optional[Dealership] =
     None) -> Decimal`. Layers: DB
     (`DealerOnboardingProfile.floor_plan_apr` — new field, see
     step 5) → env (`DEALER_AI_FLOOR_PLAN_APR`) → default
     (`Decimal("8.5")` — Copper Canyon baseline per planning
     §1.4).

5. **`DealerOnboardingProfile.floor_plan_apr` field.**
   - Nullable `DecimalField(max_digits=5, decimal_places=2,
     null=True, blank=True)`. Migration `0014` — additive only,
     no data migration (existing rows keep NULL until the
     operator saves the field).
   - Add to the onboarding profile serializer (if there is one
     — check `serializers.py`).
   - Frontend field addition is M2.3 scope, not M2.2.

6. **`settings.py::DEALER_AI_FLOOR_PLAN_APR` env var.**
   - Add alongside `DEALER_AI_DEALER_TYPE` and
     `DEALER_AI_PRIMARY_MAKE` — same pattern as the M1 · 4F
     franchise env-override fix.

7. **Extend `services/llm_safety.py`** — the acquisition-price
   scrub (safety pipeline stage 17).
   - New `_ACQUISITION_PRICE_PATTERNS` regex list catching
     ledger-leakage phrasing per planning §1.5.
   - New `_scrub_acquisition_price(text) -> Tuple[str, bool]`.
   - New branch in `apply_post_llm_scrubs` that fires on every
     `kind` (`chat`, `vehicle_ask`, `ad`, `follow_up`).
   - Positive tests: scrub fires on synthetic ledger-leakage
     strings ("we paid $X at auction", "our cost was $X", "in it
     for $X", etc.).
   - Negative tests: scrub does NOT fire on legitimate strings
     (existing chat replies, safe descriptions like "priced
     under $20,000", any string in the pre-M2 test corpus).

8. **Three admin endpoints** — mirroring the M1 · 4D
   `admin_lead_*` pattern:
   - `GET /api/dealer-ai/admin/vehicles/<stock_number>/ledger/`
     — returns acquisition + costs + `LedgerTotals`.
   - `POST /api/dealer-ai/admin/vehicles/<stock_number>/acquisition/`
     — creates or updates the OneToOne acquisition.
   - `POST /api/dealer-ai/admin/vehicles/<stock_number>/costs/`
     — creates a new cost row.
   - Each: `@api_view` +
     `permission_classes = [IsAuthenticated &
     IsSalesManagerOrOwnerAtActiveDealership]` +
     `dealership = get_current_dealership(request)` at the top
     +
     `.filter(dealership=dealership)` on every queryset.
   - Cross-tenant `stock_number` lookups fail closed (404).
   - Focused permission matrix per endpoint (six cases: unauth,
     wrong-role, wrong-tenant, correct sales_manager, correct
     dealer_owner, advisor → 403).

9. **URL registrations in `dealer_ai/urls.py`.**

10. **Management command
    `manage.py accrue_floor_plan_interest --dealership=<slug>
    [--as-of=YYYY-MM-DD] [--dry-run]`.**
    - Idempotent (re-run same-day is a no-op).
    - Refuses to run without `--dealership`.
    - `--dry-run` never writes.
    - Posts `VehicleCost` rows with
      `category=CATEGORY_FLOOR_PLAN_INTEREST`,
      `reference="ACCRUAL:<as_of>"`.

11. **Verify migrations both ways.**
    - Forward: `python3 manage.py migrate` against dev DB.
    - Round-trip: `manage.py migrate --database=migration_check`
      → `manage.py migrate --database=migration_check dealer_ai
      0013` → `manage.py migrate --database=migration_check`.

12. **Verify full test baseline.**
    - `python3 manage.py test dealer_ai` → ≥ 1,496 + M2.2's new
      tests, zero regressions.
    - Fresh-process smoke of the new env var
      (`DEALER_AI_FLOOR_PLAN_APR=6.25 python3 -c
      "from dealer_ai.services.dealer_config import
      get_floor_plan_apr; print(get_floor_plan_apr())"`) —
      mirror the M1 · 4F pattern.
    - Manual `curl` smoke of the three new endpoints against
      dev DB using `smoke_owner` session.
    - Manual smoke of the accrual command: `--dry-run` shows
      expected counts; live run posts rows; re-run same-day is
      a no-op.

13. **Close SESSION_047 with:**
    - Handoff at
      `docs/handoffs/SESSION_047_milestone_2_api_and_safety.md`.
    - Overwrite this file (`00-START-NEXT-SESSION.md`) with the
      SESSION_048 = M2 · Increment 3 (M2.3) priority per
      `MILESTONE_2_PLANNING.md` §7 · M2.3.

## Explicit non-goals for SESSION_047 (M2 · Increment 2)

- ❌ Do NOT ship any M2.3 scope: no frontend page, no
  `lib/api.ts` additions, no route registration in `main.tsx`,
  no inventory-card ledger link, no §3 compatibility sweep, no
  `CAPABILITY_MATRIX.md` update, no `IMPLEMENTATION_ROADMAP.md`
  §2.1 flip, no retrospective.
- ❌ Do NOT touch the Milestone 1 permission classes. Reuse
  `IsSalesManagerOrOwnerAtActiveDealership` unchanged.
- ❌ Do NOT introduce a `recon_manager` permission class —
  deferred to Milestone 4 (planning §5).
- ❌ Do NOT introduce a `Vendor` FK model — deferred to
  Milestone 4 (planning §5).
- ❌ Do NOT ship `expected_gross` computed property — deferred to
  Milestone 3 (planning §5).
- ❌ Do NOT modify any of the 16 pre-existing safety pipeline
  stages. The acquisition-price scrub ADDS a 17th stage; it does
  not modify the others.
- ❌ Do NOT introduce tenant-scoped uniqueness on
  `Vehicle.stock_number` — still deferred (planning §5).
- ❌ Do NOT scope in the `demo/*` gating decision.
- ❌ Do NOT introduce Celery / async infrastructure — deferred
  to Milestone 7. The accrual command is manual / cron for v1.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_047 with the read-first list above. Ship the twelve
deliverables in step order (service module first — everything else
consumes it — then payment engine + dealer_config extensions,
DealerOnboardingProfile field + migration, settings env var,
llm_safety extension, three endpoints, URLs, accrual command,
verification). No frontend. No M2.1 revisits.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` (acceptance contract;
   §7 · M2.2 boundary + SESSION_046 handoff Deviations)
7. `docs/BUSINESS_DOMAIN_MAP.md`
8. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. Current source code — new imports available:
    - `dealer_ai.models`: `VehicleAcquisition`, `VehicleCost`,
      `SOURCE_*` (8 constants), `ACQUISITION_SOURCE_CHOICES`,
      `CATEGORY_*` (26 constants), `VEHICLE_COST_CATEGORY_CHOICES`.
11. Most recent handoffs (`SESSION_046_milestone_2_schema.md`,
    `SESSION_045_milestone_2_planning.md`,
    `SESSION_044_milestone_1_closeout.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_046 — M2.1 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0013` applied to dev DB. Default `Dealership` row exists
  (`slug='default'`). No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1.**
- **Frontend (prod):** NONE.
- **Test baseline:** **1,496 pass** (1,466 baseline + 30 new
  M2.1 model tests), 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` +
  `TokenAuthentication` installed; `DEFAULT_PERMISSION_CLASSES`
  intentionally unset (locked by
  `test_default_permission_classes_remain_unset`).
- **CSRF trust origins:** localhost:5173, 127.0.0.1:5173,
  localhost:3000, 127.0.0.1:3000 (env-configurable via
  `CSRF_TRUSTED_ORIGINS`).
- **Endpoint-level permission classes shipped:** advisor (4C) +
  admin (4D) surfaces. M2.2's three endpoints will compose
  `IsSalesManagerOrOwnerAtActiveDealership` unchanged.
- **Browser auth endpoints:** `/auth/{login,logout,me}`.
- **Frontend auth primitives:** `lib/authFetch.ts`,
  `lib/auth.ts`, `lib/AuthContext.tsx`,
  `components/RequireAuth.tsx`, `pages/LoginPage.tsx`. Sign-out
  button in the topbar.
- **Public / protected route split** in `src/main.tsx`:
  public = `/`, `/assistant`, `/showroom`, `/embed/assistant`,
  `/login`. Everything else under `<RequireAuth>`. M2.3's new
  ledger route (SESSION_048) lands inside `<RequireAuth>`.
- **Migration-check DB alias** (M1 lesson 2, landed this session):
  `DATABASES["migration_check"]` in `settings.py` — SQLite file at
  `backend/db.migration_check.sqlite3` (gitignored). Invoke with
  `--database=migration_check` for any destructive migration
  probe.
- **Franchise env-override + Copper Canyon defaults verified at
  Milestone 1 close.** `DEALER_AI_DEALER_TYPE` and
  `DEALER_AI_PRIMARY_MAKE` wired through `settings.py` (fix
  landed in SESSION_044). M2.2 will add
  `DEALER_AI_FLOOR_PLAN_APR` alongside them.
- **Dev DB seeded users** (safe to keep): `smoke_owner`
  (`dealer_owner`) + `smoke_advisor` (`advisor`, linked to
  `Salesperson.slug=smoke-advisor-slug`). Password
  `smoke-pass-4e`. Not committed to source. M2.2's endpoint
  smokes will reuse both.
- **Ledger model surface** (new this session, available for
  M2.2 imports):
  - `dealer_ai.models::VehicleAcquisition` (OneToOne with
    Vehicle via `related_name="acquisition"`).
  - `dealer_ai.models::VehicleCost` (FK to Vehicle via
    `related_name="costs"`).
  - `SOURCE_*` × 8 + `ACQUISITION_SOURCE_CHOICES`.
  - `CATEGORY_*` × 26 + `VEHICLE_COST_CATEGORY_CHOICES`.
  - Both models: `dealership` FK NOT NULL from day one +
    `clean()` cross-tenant guard.
- **Category-set groupings** (`FLOORING_CATEGORIES`,
  `RECON_CATEGORIES`, `ADMIN_CATEGORIES`) — **deferred to
  SESSION_047** (M2.2) alongside `services/vehicle_ledger.py`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in the
  respective planning + retrospective docs.
