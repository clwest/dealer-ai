---
state: active
date: 2026-07-31
last_session_shipped: SESSION_045
milestone_1_status: shipped
milestone_2_status: planning_complete
next_session: SESSION_046
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 1
next_increment_name: "Schema + model layer"
---

# Next session — SESSION_046 · Milestone 2 · Increment 1 (M2.1 — schema + model layer)

> **Milestone 2 planning pass shipped at SESSION_045.** The full
> planning artifact is at `docs/roadmap/MILESTONE_2_PLANNING.md`.
> Read it end-to-end before writing any code. It is the acceptance
> contract for the entire milestone.
>
> **SESSION_046 opens Milestone 2 implementation with Increment 1.**
> M2.1 lands the schema (two new models) + the service-layer
> skeleton + `@property` accessors on `Vehicle`. **No API, no views,
> no scrub, no accrual command, no frontend.** Those all land in
> M2.2 (SESSION_047) and M2.3.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
   boundary (in-scope / out-of-scope enumeration).
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every new ledger row
   inherits the tenancy + authorization substrate. §8b in
   particular: write-path callers MUST pass `dealership=` explicitly;
   `pre_save` autofill is a fallback safety net, not the primary
   path.
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 — the eight
   lessons the retrospective codified. Every one applies to M2:
   migration sequencing, dedicated migration-check DB alias,
   pre-save fallback vs. primary write path, layer discipline,
   focused test matrices, public/protected route boundaries,
   CSRF trust origins, `@ensure_csrf_cookie` pattern.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` — the acceptance
   contract for Milestone 2. §3 is the acceptance checklist;
   §7 · M2.1 is the scope boundary for SESSION_046 specifically.
7. `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference.
8. `docs/CAPABILITY_MATRIX.md` — what already exists.

## What SESSION_046 should do — M2 · Increment 1

Per `MILESTONE_2_PLANNING.md` §7 · M2.1. Mirror the shape of
SESSION_037 (M1 · Increment 1, tenancy foundation) — small
increment, schema + models only, model-level tests, no API yet.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/roadmap/MILESTONE_2_PLANNING.md` — full read; this is
     the acceptance contract.
   - `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
     (skim; the ones that matter for M2.1 are #1 migration
     sequencing, #2 dedicated migration-check DB alias, #4 layer
     discipline).
   - `backend/dealer_ai/models.py::Vehicle` + `Dealership` +
     `ROLE_*` constants (the shape M2.1's new models emulate).
   - `backend/dealer_ai/services/tenancy.py` (write-path pattern:
     what an M2.1 new model's `pre_save` autofill registration
     looks like, if we choose to register — §7 · M2.1 does not
     require it because ledger writes always thread `dealership=`
     explicitly, but the option is on the table).
   - `backend/dealer_ai/migrations/0011_userdealershiprole_and_salesperson_user.py`
     (the most recent schema migration — pattern for how M2's
     `0012` and `0013` are shaped).

2. **Set up the migration-check DB alias.** Per M1 lesson #2, add
   `DATABASES["migration_check"]` to `backend/dealer_kit/settings.py`
   (dev-only, SQLite is fine) *before* running any destructive
   migration verification. Document it in the SESSION_046 handoff.

3. **Model + migration `0012` — `VehicleAcquisition`.** Per
   `MILESTONE_2_PLANNING.md` §1.1. OneToOne with `Vehicle`,
   `dealership` FK NOT NULL from day one (greenfield —
   no backfill required). Enumerated `source` choices:
   `auction`, `trade`, `wholesale`, `private`, `off_lease`,
   `rental`, `repo`, `fleet`. Model-level tests: field
   validation, `source` choices enforcement, OneToOne uniqueness,
   `dealership` required, cascade on Vehicle delete.

4. **Model + migration `0013` — `VehicleCost`.** Per
   `MILESTONE_2_PLANNING.md` §1.2. FK to `Vehicle`, `dealership`
   FK NOT NULL. Module-level category constants block (mirroring
   `ROLE_*`). Model-level tests: category choices enforcement,
   `dealership` required, `is_estimate` flag, `created_by`
   nullable + SET_NULL.

5. **`services/vehicle_ledger.py` skeleton.** `LedgerTotals`
   dataclass with the six numbers. `compute_totals(vehicle, *,
   dealership) -> LedgerTotals` — the *only* function implemented
   in M2.1. Explicitly refuses cross-tenant reads (`vehicle.dealership_id
   != dealership.id` → raise). Threads `dealership=` explicitly
   per `AUTHENTICATION_MODEL.md` §8b.

6. **Computed `@property` methods on `Vehicle`.** Per
   `MILESTONE_2_PLANNING.md` §1.3:
   `total_acquisition_cost`, `total_flooring_cost`,
   `total_recon_cost`, `total_admin_cost`, `total_investment`,
   `projected_gross`, `days_in_inventory`. Each delegates to
   `services/vehicle_ledger.compute_totals` for the underlying
   aggregation. No `expected_gross` (deferred per §5).

7. **Django admin registration.** Both new models. Read-mostly,
   for internal debugging. Not the primary operator surface (that
   ships in M2.3).

8. **Model-level test coverage.** Every field constraint, every
   choices enum, every OneToOne uniqueness constraint, every
   cascade behavior. **No API tests, no view tests, no scrub
   tests, no accrual tests.** Those all belong to M2.2/M2.3.

9. **Verify migrations both ways.**
   - Forward: `python3 manage.py migrate` against dev DB — clean.
   - Round-trip: against `DATABASES["migration_check"]` (fresh),
     `manage.py migrate dealer_ai zero` → `manage.py migrate`
     — clean. Every migration in `0001`–`0013` applies in order.
   - Test baseline: `python3 manage.py test dealer_ai` → ≥ 1,466
     + M2.1's new model tests, zero regressions.

10. **Close SESSION_046 with:**
    - Migrations `0012` + `0013` committed.
    - Handoff at `docs/handoffs/SESSION_046_milestone_2_schema.md`.
    - Overwrite this file (`00-START-NEXT-SESSION.md`) with the
      SESSION_047 = M2 · Increment 2 (M2.2) priority per
      `MILESTONE_2_PLANNING.md` §7 · M2.2.

## Explicit non-goals for SESSION_046 (M2 · Increment 1)

- ❌ Do NOT ship any of the M2.2 scope: no API endpoints, no
  service functions beyond `compute_totals`, no
  `record_acquisition` / `add_cost`, no `_scrub_acquisition_price`,
  no `daily_floor_plan_interest`, no accrual management command,
  no `DealerOnboardingProfile.floor_plan_apr` field, no
  `DEALER_AI_FLOOR_PLAN_APR` env var.
- ❌ Do NOT ship any of the M2.3 scope: no frontend page, no
  `authFetch` calls, no route registration, no inventory-card
  link, no §3 compatibility sweep, no `CAPABILITY_MATRIX.md`
  update, no `IMPLEMENTATION_ROADMAP.md` §2.1 flip, no
  retrospective.
- ❌ Do NOT scope in the deferred items from
  `MILESTONE_2_PLANNING.md` §5. Every one is deferred to a
  named milestone; folding them into M2.1 would violate the
  Discovery Rule.
- ❌ Do NOT touch the 16-stage safety pipeline. Stage 17
  (acquisition-price scrub) lands in M2.2, not M2.1.
- ❌ Do NOT touch `services/payment_engine.py`. The
  `daily_floor_plan_interest` helper lands in M2.2.
- ❌ Do NOT touch the Milestone 1 permission classes. M2 reuses
  `IsSalesManagerOrOwnerAtActiveDealership` unchanged; M2.1 does
  not even reach the endpoint layer.
- ❌ Do NOT introduce tenant-scoped uniqueness on
  `Vehicle.stock_number` (still deferred from Milestone 1 §5;
  planning artifact §5 keeps it deferred).
- ❌ Do NOT introduce a `Vendor` FK (deferred to Milestone 4;
  planning artifact §5).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_046 with the read-first list above. Ship
`VehicleAcquisition` + `VehicleCost` + `services/vehicle_ledger.py`
skeleton + `Vehicle` `@property` accessors + migrations
`0012` and `0013` + admin registration + model-level tests.
No API, no scrub, no accrual, no frontend.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` (acceptance contract)
7. `docs/BUSINESS_DOMAIN_MAP.md`
8. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. Current source code (`backend/dealer_ai/models.py`,
    `backend/dealer_ai/services/tenancy.py`,
    `backend/dealer_ai/services/llm_safety.py`,
    `backend/dealer_ai/services/payment_engine.py`,
    `backend/dealer_ai/permissions.py`).
11. Most recent handoffs (`SESSION_045_milestone_2_planning.md`,
    `SESSION_044_milestone_1_closeout.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_045 — planning-only session)

Unchanged from SESSION_044 close (this session did not touch code
or configuration):

- **Backend (local):** Django on `:8001`. Migrations `0001`–`0011`
  applied; `authtoken` migrations applied. Default `Dealership`
  row exists (`slug='default'`). No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,466 pass, 1 skipped, 0 fail — unchanged
  from SESSION_044.
- **DRF defaults:** `SessionAuthentication` +
  `TokenAuthentication` installed; `DEFAULT_PERMISSION_CLASSES`
  intentionally unset (locked by
  `test_default_permission_classes_remain_unset`).
- **CSRF trust origins:** localhost:5173, 127.0.0.1:5173,
  localhost:3000, 127.0.0.1:3000 (env-configurable via
  `CSRF_TRUSTED_ORIGINS`).
- **Endpoint-level permission classes shipped:** advisor (4C) +
  admin (4D) surfaces. M2's ledger endpoints (SESSION_047)
  compose `IsSalesManagerOrOwnerAtActiveDealership` unchanged.
- **Browser auth endpoints:** `/auth/{login,logout,me}`.
- **Frontend auth primitives:** `lib/authFetch.ts`, `lib/auth.ts`,
  `lib/AuthContext.tsx`, `components/RequireAuth.tsx`,
  `pages/LoginPage.tsx`. Sign-out button in the topbar.
- **Public / protected route split** in `src/main.tsx`:
  public = `/`, `/assistant`, `/showroom`, `/embed/assistant`,
  `/login`. Everything else is under `RequireAuth`. M2's new
  ledger route (SESSION_048) lands inside `RequireAuth`.
- **Franchise env-override + Copper Canyon defaults verified at
  Milestone 1 close.** `DEALER_AI_DEALER_TYPE` and
  `DEALER_AI_PRIMARY_MAKE` wired through `settings.py` (fix
  landed in SESSION_044). M2 will add
  `DEALER_AI_FLOOR_PLAN_APR` alongside them in SESSION_047.
- **Dev DB seeded users** (safe to keep): `smoke_owner`
  (`dealer_owner`) + `smoke_advisor` (`advisor`, linked to
  `Salesperson.slug=smoke-advisor-slug`). Password
  `smoke-pass-4e`. Not committed to source. M2's browser smokes
  will reuse both.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in the
  respective planning + retrospective docs.
