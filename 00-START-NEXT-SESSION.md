---
state: active
date: 2026-08-01
last_session_shipped: SESSION_099
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: planning
next_session: SESSION_100
next_milestone: 9
next_milestone_name: "Sale + delivery closure"
next_increment: 1
next_increment_name: "M9.1 — Sale entity + gross_realized"
---

# Next session — SESSION_100 · Milestone 9 · Increment 1 (M9.1 — Sale entity + gross_realized)

> **SESSION_099 shipped M8.6 closeout —
> `MILESTONE_8_RETROSPECTIVE.md` (fifteen
> lessons — one new: verify handoff claims via
> direct inspection) + `CAPABILITY_MATRIX.md`
> §7i + `IMPLEMENTATION_ROADMAP.md` §M8
> SHIPPED header + `MILESTONE_8_PLANNING.md`
> frontmatter flip + `DEALER_KIT_SESSION_START.md`
> refresh (baseline 3,150 → 3,274; frontend 0 →
> 19) + `MILESTONE_9_PLANNING.md` new (per
> standing user directive) + coordinated
> commit `34352ed` landing every M8.1-M8.6
> stage.**
>
> **Push to `origin/main` is deferred pending
> explicit user authorization** — check with
> the user at session open whether the commit
> should push or stay local.
>
> **Backend baseline: 3,274 pass, 1 skipped, 0
> fail.** Frontend Vitest baseline: 19 pass.
> Migrations `0001`–`0022`.
>
> **SESSION_100 opens M9.1 — Sale entity +
> gross_realized.** Three §9 decisions in
> `MILESTONE_9_PLANNING.md` §5 to confirm at
> session open before code lands.

## First thing SESSION_100 must do

### 1. Check push authorization for commit `34352ed`

The M8-close commit lives locally on `main`
only. Verify with the user:

- Is the commit still local? (`git log
  origin/main..HEAD --oneline` — non-empty
  means still local.)
- Should it push now? If yes: `git push
  origin main` after explicit user "go."

Push is a shared-state action; per CLAUDE.md
safety posture, requires per-push confirmation
independent of the per-milestone authorization
that landed the commit.

### 2. Confirm the three §9 decisions in `MILESTONE_9_PLANNING.md`

Recommendations (all Option A):

1. **§5.a Acquisition-buyer provenance
   bundling.** Bundle the M2 buyer-FK
   extension into M9 so Q7 unlocks in the
   same milestone (adds migration `0024` in
   the M9 chain).
2. **§5.b Sale.buyer representation.**
   `Sale.buyer` FK to existing
   `CustomerLead`. Reuses M3-M5 CRM
   substrate.
3. **§5.c Sale finance-type vocabulary.**
   Three initial values: `cash` / `retail` /
   `bhph`. Small vocabulary; extend when
   operator evidence surfaces need.

**Do not write M9.1 code until every
`[NEEDS-DECISION-BEFORE-M9.N]` item is
resolved.** If the user overrides any
decision, amend `MILESTONE_9_PLANNING.md`
§0.a narrowly at session top (per M8 §0.a
precedent — SESSION_095 + SESSION_097
change-log entries) before implementation.

### 3. Verify starting state

- `git status` — should be clean (M8-close
  commit landed at SESSION_099 close).
- `git log --oneline -3` — top should be
  `34352ed Milestone 8 shipped …`.
- `python3 manage.py test dealer_ai` →
  **3,274 pass, 1 skipped, 0 fail.**
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check
  --dry-run` → "No changes detected."
- `cd frontend && npm test` → **19 pass**.
- `npx tsc --noEmit` clean.
- `npx vite build` clean.
- `redis-cli ping` → `PONG`.

## What M9.1 delivers

Per `MILESTONE_9_PLANNING.md` §7 M9.1:

- **New `Sale` model + migration `0023`**
  (fields per §1.1: `buyer` FK — target
  depends on §5.b, `vehicle` FK unique,
  `sale_date`, `sold_price` Decimal,
  `finance_type` from §5.c vocabulary,
  `lender_name` nullable text,
  `gross_realized` Decimal).
- **`services/sale/` package + `computation.py::gross_realized`
  verb** reading M2 `vehicle_ledger.compute_totals(sale.vehicle)`.
  Read-only.
- **First endpoint:**
  `POST /api/dealer-ai/admin/vehicles/<stock>/sale/`.
  Role-gated per the M4-M8 pattern.
- **Tenancy-carrier extension 22 → 23**
  (`Sale`).
- **~30 focused tests.**
- **Baseline target 3,274 → ~3,304.**

If §5.a Option A confirmed, M9.1 may also
land the `VehicleAcquisition.buyer` FK +
migration `0024` alongside (decide at
session open per Sale-FK-first vs
buyer-FK-first sequencing).

### Non-goals for M9.1

- ❌ No `Delivery` model yet (M9.2).
- ❌ No analytics extensions
  (`vehicle_type_profitability`,
  `gross_profit_trend`, `inventory_turn`) —
  M9.3.
- ❌ No frontend / operator UI (M9.5).
- ❌ No F&I / stips / chargebacks (M10).

## What SESSION_100 should do

### Recommended step sequence

0. **Push authorization check** (§1 above).

1. **Confirm the three §9 decisions with the
   user** (§2 above). Do NOT write code
   until every
   `[NEEDS-DECISION-BEFORE-M9.N]` item is
   resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_9_PLANNING.md`
     §1.1 + §1.4 + §5 + §7 M9.1.
   - `docs/handoffs/SESSION_099_m8_closeout.md`
     (previous session).
   - `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md`
     §6 (fifteen lessons carry into M9).
   - `docs/CAPABILITY_MATRIX.md` §7i (M8
     substrate M9 layers on top of).
   - `backend/dealer_ai/models.py::Vehicle`
     (Sale parent).
   - `backend/dealer_ai/models.py::CustomerLead`
     (potential Sale.buyer target — §5.b).
   - `backend/dealer_ai/services/vehicle_ledger.py::compute_totals`
     (the read path `gross_realized` calls
     through).

3. **Verify starting state** (§3 above).

4. **Draft (in order):**
   - `Sale` model + migration `0023` (+
     `VehicleAcquisition.buyer` migration
     `0024` if §5.a Option A).
   - `services/sale/__init__.py` +
     `services/sale/computation.py::gross_realized`
     verb.
   - Tenancy carrier addition.
   - First endpoint + URL.
   - ~30 focused tests.

5. **Full-suite verification.** Target
   3,274 → ~3,304.

6. **Ship handoff at
   `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`.**

7. **Overwrite `00-START-NEXT-SESSION.md`**
   with M9.2 priority.

## Explicit non-goals for SESSION_100

- ❌ Do NOT ship `Delivery` model or
  checklist (M9.2).
- ❌ Do NOT ship analytics extensions
  (M9.3).
- ❌ Do NOT ship frontend UI (M9.5).
- ❌ Do NOT modify M1-M8 business logic.
- ❌ Do NOT force-push or amend the M8-close
  commit `34352ed`.

## NEXT TASK

Start SESSION_100 with (a) push-authorization
check for the M8-close commit, (b) confirming
the three §9 decisions with the user, (c) the
read-first list, (d) starting-state
verification, then (e) `Sale` model + first
endpoint + ~30 tests. Target baseline 3,274 →
~3,304. Ship the M9.1 handoff.

Backend baseline at SESSION_100 close:
**~3,304 pass**. Frontend baseline: unchanged
(no frontend at M9.1).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 9
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_9_PLANNING.md`
6. `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_099_m8_closeout.md`
8. `docs/handoffs/SESSION_098_m8_inc5_operator_ui.md`
9. `docs/handoffs/SESSION_097_m8_inc4_acquisition_frontline_proxies.md`
10. `docs/handoffs/SESSION_096_m8_inc3_aging_sla_patterns.md`
11. `docs/handoffs/SESSION_095_m8_inc2_vendor_performance.md`
12. `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`
13. `docs/roadmap/MILESTONE_8_PLANNING.md` (with §0.a
    SESSION_095 + SESSION_097 amendments; shipped)
14. `docs/CAPABILITY_MATRIX.md` §7i
15. `docs/research/VEHICLE_CENTRIC_PIVOT.md` §Phase 8
16. `docs/research/SALES_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules + research +
code are facts.

---

## Operational state (post-SESSION_099 — M8 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0022`. Test baseline:
  **3,274 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 19 pass** (established
  at M8.5).
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. **4 scheduled task
  families registered** at hourly cadence
  02:00 – 05:00 project-time (unchanged
  from M7).
- **Milestones shipped:** M1 → **M8**
  (SESSION_099 close). M9 planning drafted.
- **DRF admin surface:** 40 endpoints.
- **Frontend operator routes:** 8 (M8.5
  added `/dealer-ai-analytics/`).
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4 submodules) +
  M7.4 verb-extension.
- **Tenancy carriers:** 22 (M1 six + M3
  three + M4 six + M5 two + M6 two + M7
  two + M8 one — `SlaBreachRecord`).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:** unchanged.
- **M8 aggregation surface (shipped +
  wired to UI):** Q1 (recon per source),
  Q2 + Q4 (vendor performance), Q5 + Q9
  (stage aging trend), Q10 (SLA breach
  patterns), Q3 proxy (vehicle-type recon
  cost), Q8 proxy (days at frontline).
  Six aggregations, six endpoints.
- **Milestone 9 next:** M9.1 Sale entity +
  gross_realized. Three §9 decisions to
  confirm at session open. ~30 tests.
  Baseline ~3,274 → ~3,304.
