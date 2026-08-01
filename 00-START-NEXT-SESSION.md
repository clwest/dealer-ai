---
state: active
date: 2026-07-31
last_session_shipped: SESSION_052
milestone_1_status: shipped
milestone_2_status: in_progress
next_session: SESSION_053
next_milestone: 2
next_milestone_name: "Vehicle investment ledger"
next_increment: 7
next_increment_name: "Operator ledger UI"
---

# Next session — SESSION_053 · Milestone 2 · Increment 7 (M2.7 — operator ledger UI)

> **Milestone 2 · Increment 6 shipped at SESSION_052.**
> Three admin ledger endpoints under
> `/api/dealer-ai/admin/vehicles/<stock_number>/…` — `ledger/`
> (GET), `acquisition/` (POST upsert), `costs/` (POST create).
> Permission composition
> `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`
> (M1 · 4D class reused unchanged). All writes route through the
> ledger service. 57 focused tests including full permission
> matrix, JSON contract stability locks, deterministic cost
> ordering (`incurred_at` ASC, pk tie-break), immutable-routes
> (PUT/PATCH/DELETE → 405), `created_by` cannot be spoofed, and
> **security verification that no ledger keywords leak into any
> public endpoint**. Test baseline: 1,696 → **1,753 pass**, 1
> skipped, 0 fail. Zero regressions. No schema drift.
>
> **JSON contract locked for M2.7 to consume** — every money
> field is a two-decimal-place string; costs come back
> chronological ASC; `created_by` is username string or `null`;
> `acquisition` is a projection object or `null`;
> `days_in_inventory` is int or `null`.
>
> **SESSION_053 opens M2.7 — the operator ledger UI.**
> Frontend-only session. Consumes the M2.6 JSON contract without
> reshaping the backend.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 —
   scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §2c — frontend auth
   primitives. Every M2.7 fetch goes through `authFetch`; the
   ledger page lives inside `<RequireAuth>`.
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lesson 6 —
   public/protected route boundary must remain explicit; the
   ledger page is protected.
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.7.
7. `docs/handoffs/SESSION_052_milestone_2_ledger_api.md` — the
   authoritative M2.7 recommended scope + full M2.6 JSON
   contract the UI consumes verbatim.
8. Earlier M2 handoffs (`SESSION_045` – `SESSION_051`).

## What SESSION_053 should do — M2 · Increment 7

Per `MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.7 and the
SESSION_052 handoff's "Exact recommended scope for M2.7".

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_052_milestone_2_ledger_api.md`
     § "Exact recommended scope for M2.7" — authoritative
     scope + the JSON contract to consume.
   - `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 — UI design
     memo.
   - `docs/roadmap/AUTHENTICATION_MODEL.md` §2c — frontend
     auth primitives.
   - `frontend/src/lib/authFetch.ts`, `frontend/src/lib/api.ts`,
     `frontend/src/lib/AuthContext.tsx`,
     `frontend/src/components/RequireAuth.tsx`,
     `frontend/src/pages/LoginPage.tsx` — existing operator-side
     fetch + auth primitives to reuse.
   - `frontend/src/main.tsx` — route registration file.
   - The existing inventory list page (grep for
     `/dealer-ai-inventory` in `frontend/src/pages/`) — the
     "Ledger" link is added there.
   - `frontend/tailwind.config.js` + `frontend/src/index.css` —
     confirm the shadcn/ui bridge is stable (no v3→v4 drift).
     Use `brand.*` tokens for headers/totals, shadcn tokens
     for chrome (dialogs, tables, inputs).

2. **Add three `lib/api.ts` helpers** wrapping M2.6 endpoints:
   - `fetchVehicleLedger(stock: string) → LedgerResponse`
   - `upsertVehicleAcquisition(stock, body) → AcquisitionResponse`
   - `createVehicleCost(stock, body) → CostResponse`
   All via `authFetch` (session cookies, CSRF-protected).
   Type the payloads to match the JSON contract in the
   SESSION_052 handoff.

3. **Register the new route** in `main.tsx`:
   ```
   <Route path="/dealer-ai-inventory/:stock/ledger"
          element={<VehicleLedgerPage />} />
   ```
   Inside `<RequireAuth>` — the public/protected split from
   M1 · 4E stays intact.

4. **Build `VehicleLedgerPage.tsx`** per planning §1.6:
   - Header: `{Year} {Make} {Model} #{stock_number}` + three-
     number bar: **In it for $X · Asking $Y · Projected gross $Z**.
   - `days_in_inventory` badge, color-coded per aging bucket
     (0–30 green, 31–60 yellow, 61–90 orange, 91+ red; `null`
     → "Record acquisition" pill).
   - Acquisition card — read-only display + "Edit" toggle to
     an inline form (POST `.../acquisition/`).
   - Cost ledger table — chronological rows: category /
     vendor / amount / incurred_at / notes / is_estimate flag
     / created_by.
   - "Add cost" inline form (POST `.../costs/`).
   - Category totals block (four rows: flooring, recon, admin,
     photography).

5. **Role-based show/hide on write forms** via `useAuth()`:
   `hasRole('sales_manager') || hasRole('dealer_owner')`
   controls whether "Add cost" / "Edit acquisition" render.
   Belt-and-suspenders on the server-side 403 (matches M1 ·
   4E pattern).

6. **Inventory list card** — add a "Ledger" link on each row
   that navigates to `/dealer-ai-inventory/:stock/ledger`.

7. **Verify.**
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.
   - Manual browser smokes:
     - Login as `smoke_owner` → inventory list → click
       "Ledger" on a card → see ledger → add a cost → see
       totals update.
     - Login as advisor → navigate to a ledger URL directly
       → see 403 UI (not `/login` redirect).
     - Anonymous → navigate to ledger URL → redirect to
       `/login?next=...`.
   - Backend suite unchanged: 1,753 pass. (M2.7 is
     frontend-only.)

8. **Close SESSION_053 with:**
   - Handoff at
     `docs/handoffs/SESSION_053_milestone_2_ledger_ui.md`.
   - Overwrite this file with SESSION_054 = M2.8 priority
     (milestone verification + closeout retrospective).

## Explicit non-goals for SESSION_053 (M2 · Increment 7)

- ❌ Do NOT ship M2.8 (milestone verification + closeout
  retrospective).
- ❌ Do NOT touch any backend file. If the JSON contract needs
  reshaping, stop and reopen M2.6 as a separate increment.
- ❌ Do NOT introduce a bulk inventory-list optimization —
  deferred per M2.3 handoff N+1 preview.
- ❌ Do NOT ship update/delete cost operations. v1 corrections
  are reversing rows.
- ❌ Do NOT introduce role-specific chrome beyond the write-
  form show/hide (planning §5 defers per-role UI polish).
- ❌ Do NOT introduce charts / visualizations. Numbers only
  for v1.
- ❌ Do NOT introduce recon-manager role in the UI (deferred
  to Milestone 4).
- ❌ Do NOT fold in `floor_plan_apr` Setup UI unless the
  ledger page genuinely needs to expose it in v1 (evaluate
  and document; if unclear, defer).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or credentials.

## NEXT TASK

Start SESSION_053 with the read-first list above. Ship the
three `lib/api.ts` helpers + `VehicleLedgerPage.tsx` + route
registration + inventory-card "Ledger" link + role-based
show/hide on write forms. Nothing else.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.7
7. `docs/handoffs/SESSION_052_milestone_2_ledger_api.md`
   (M2.7 authoritative scope + full JSON contract)
8. `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
9. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
10. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
11. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
12. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
13. `docs/handoffs/SESSION_046_milestone_2_schema.md`
14. `docs/handoffs/SESSION_045_milestone_2_planning.md`
15. Current source code — the M2.6 three admin endpoints and
    their JSON contract.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_052 — M2.6 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0014` applied. No pending migrations.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 2 does not require prod either.
- **Frontend (local):** Vite on `:5173`. Auth flow wired
  end-to-end. **NOT touched in M2.1 through M2.6.** M2.7 is
  the first frontend session in Milestone 2.
- **Frontend (prod):** NONE.
- **Test baseline:** **1,753 pass** (1,696 baseline + 57 new
  M2.6 tests), 1 skipped, 0 fail.
- **DRF defaults + CSRF + endpoint-level permissions:** all as
  documented in `AUTHENTICATION_MODEL.md`. Unchanged.
  M2.6 confirmed `DEFAULT_PERMISSION_CLASSES` still unset.
- **Migration-check DB alias:** `DATABASES["migration_check"]`.
- **Env-override surface:** `DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
  `DEALER_AI_FLOOR_PLAN_APR`.
- **Dev DB seeded users:** `smoke_owner` (dealer_owner) +
  `smoke_advisor` (advisor). Password `smoke-pass-4e`. Not
  committed. M2.7 browser smokes reuse both.
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
- **Safety pipeline (M2.5):** `acquisition_price` scrub in
  `apply_post_llm_scrubs`, fires on every kind, runs AFTER
  `detect_unsafe_response`.
- **Admin API (M2.6):** Three tenant-scoped endpoints under
  `/api/dealer-ai/admin/vehicles/<stock_number>/` — `ledger/`
  (GET), `acquisition/` (POST), `costs/` (POST). Full JSON
  contract locked by tests. Permission composition
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`
  (M1 · 4D class reused). All writes through the ledger
  service. Cross-tenant + nonexistent stock_number both → 404.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Every deferred idea from Milestones 1 + 2 is recorded in
  the respective planning + retrospective + handoff docs.
