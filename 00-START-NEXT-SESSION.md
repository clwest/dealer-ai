---
state: active
date: 2026-08-01
last_session_shipped: SESSION_093
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: planning
next_session: SESSION_094
next_milestone: 8
next_milestone_name: "Operational intelligence"
next_increment: 1
next_increment_name: "M8.1 — Analytics infra + first aggregation"
---

# Next session — SESSION_094 · Milestone 8 · Increment 1 (M8.1 — analytics infra + first aggregation)

> **SESSION_093 shipped M7.6 closeout + M8 planning +
> incorporated the user's global Freedom-Ford →
> Dealer-OS rename + fixed one pre-existing test-suite
> case-mismatch bug the rename exposed.** All M7.1–M7.6
> stages ready for a coordinated commit + push to
> `origin/main` — pending user authorization.
>
> **Backend baseline: 3,150 pass, 1 skipped, 0 fail**
> (unchanged from SESSION_092 — M7.6 was docs-only
> plus the 4 case-fix edits in `test_post_llm_safety.py`).
> Frontend `tsc --noEmit` + `vite build` clean.
>
> **SESSION_094 opens M8.1 — analytics infrastructure +
> first aggregation.** New `services/analytics/`
> package + `views_analytics.py` + first endpoint.
> Possibly a new `SlaBreachRecord` model + migration
> `0022` + M7.4 verb extension (depending on §5.b
> confirmation). ~30 tests. Baseline 3,150 → ~3,180.

## First thing SESSION_094 must do — CONFIRM THE FOUR §9 DECISIONS

Before any code lands, the user needs to confirm (or
override) four load-bearing decisions from
`MILESTONE_8_PLANNING.md` §9:

1. **§5.a — Compute strategy.** Recommendation:
   **Option C (hybrid)** — compute-on-request for v1,
   materialize when operator evidence surfaces
   latency pain.
2. **§5.b — SLA-breach data source.** Recommendation:
   **Option B** (new `SlaBreachRecord` model +
   migration `0022` + M7.4 verb extension to write
   into it). Option A (log-scrape) requires
   log-aggregation substrate the stack does not have.
3. **§5.c — Chart library.** Recommendation:
   **Option A** (recharts) — smallest bundle
   addition; sufficient for M8 v1 needs.
4. **§5.d — Increment count.** Recommendation:
   **Option A** — five aggregation increments + one
   closeout (mirrors M7's six-increment shape).

**Do not write M8.1 code until these are confirmed or
overridden.** If the user overrides any decision,
amend `MILESTONE_8_PLANNING.md` narrowly at session
top (per SESSION_075 precedent — §0.a change-log
entry) before implementation.

## What M8.1 delivers

**Infrastructure + one aggregation.** Scope depends on
§5.b confirmation:

### If §5.b = Option B (SlaBreachRecord model)

- **New `SlaBreachRecord` model + migration `0022`**
  (fields: `dealership` FK CASCADE, `work_order` FK
  CASCADE, `kind` from breach-kind vocabulary,
  `breach_days`, `detected_at` DateTimeField indexed,
  `vehicle_stock`, `vendor_name`). Composite index
  `(dealership, kind, -detected_at)`.
- **M7.4 verb extension** — `detect_sla_breaches` now
  writes a `SlaBreachRecord` row per breach IN
  ADDITION to the log warning. Idempotent per
  `(work_order, kind, detected_at.date())`.
- **Tenancy-carrier extension 21 → 22.**

### Regardless of §5.b

- **New `services/analytics/` package** — `__init__.py`
  facade + first-aggregation submodule (probably
  `acquisition.py::recon_cost_per_source` per §1.2,
  simplest starting point).
- **New `views_analytics.py`** with the first DRF
  endpoint. Role-gated via
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`.
- **~30 focused tests.**

### Non-goals for M8.1

- ❌ No frontend / operator UI (M8.5).
- ❌ No additional aggregations (M8.2 – M8.4).
- ❌ No `AnalyticsCache` model (deferred per §5.a
  Option C hybrid).
- ❌ No Chart library dependency added (M8.5).
- ❌ No Prometheus / external observability (§5.e
  deferral carries from M7).

## What SESSION_094 should do

### Recommended step sequence

0. **Confirm the four §9 decisions with the user.**
   Do NOT write code until every
   `[NEEDS-DECISION-BEFORE-M8.1]` item is resolved.

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_8_PLANNING.md` §5 + §7
     M8.1.
   - `docs/handoffs/SESSION_093_m7_closeout.md`
     (previous session).
   - `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md` §6
     (14 lessons carry into M8).
   - `docs/CAPABILITY_MATRIX.md` §7h (M7 substrate).
   - `backend/dealer_ai/services/vendor_sla/detection.py`
     (the verb §5.b Option B extends).
   - `backend/dealer_ai/services/vehicle_ledger.py` +
     `services/floor_plan/accrual.py` (the ledger +
     accrual substrate M8.1's first aggregation reads).

2. **Verify starting state.**
   - `git status` — should show the M7.1-M7.6
     coordinated commit landed (if user authorized the
     push during SESSION_093 close) OR the cumulative
     M7.1-M7.6 uncommitted diff still present.
   - `python3 manage.py test dealer_ai` → **3,150
     pass, 1 skipped, 0 fail.**
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check
     --dry-run` → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.
   - `redis-cli ping` → `PONG`.

3. **Draft (in order):**
   - If §5.b Option B: `SlaBreachRecord` model +
     migration `0022` + tenancy-carrier extension
     21 → 22 + M7.4 verb extension.
   - `services/analytics/__init__.py` +
     `services/analytics/acquisition.py::recon_cost_per_source`
     verb.
   - `views_analytics.py` + first URL pattern.
   - ~30 focused tests.

4. **Full-suite verification.** Target 3,150 →
   ~3,180.

5. **Ship handoff at
   `docs/handoffs/SESSION_094_m8_inc1_analytics_infra.md`.**

6. **Overwrite `00-START-NEXT-SESSION.md`** with M8.2
   priority.

## Explicit non-goals for SESSION_094

- ❌ Do NOT ship additional aggregations (M8.2–M8.4).
- ❌ Do NOT ship frontend UI (M8.5).
- ❌ Do NOT add chart library dependency yet.
- ❌ Do NOT modify M7 Beat schedule (no new entries).
- ❌ Do NOT modify M1–M7 business logic beyond the
  M7.4 verb extension if §5.b Option B confirmed.

## NEXT TASK

Start SESSION_094 with (a) confirming the four §9
decisions with the user, (b) the read-first list, then
(c) analytics substrate + first aggregation + ~30
tests. Target baseline 3,150 → ~3,180. Ship the M8.1
handoff.

Backend baseline at SESSION_094 close: **~3,180 pass**.
Frontend baseline: unchanged (no frontend at M8.1).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 8
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_8_PLANNING.md`
6. `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_093_m7_closeout.md`
8. `docs/handoffs/SESSION_092_m7_inc5_photo_reaper.md`
9. `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
10. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
11. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
12. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
13. `docs/handoffs/SESSION_087_m6_closeout.md`
14. `docs/research/VEHICLE_CENTRIC_PIVOT.md`

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_093 — M7 fully SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0021`. Test baseline: **3,150 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  + `vite build` clean.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DB scheduler. **4
  scheduled task families registered** at hourly
  cadence 02:00 – 05:00 project-time.
- **Milestones shipped:** M1 → **M7** (M7.6 closeout
  shipped this session). M8 planning drafted.
- **DRF admin surface:** 34 endpoints.
- **Frontend operator routes:** 7.
- **Public endpoints:** +1 M6.5 showroom.
- **Service surface:** M7 added 4 new service packages
  (`services/jobs/`, `services/floor_plan/`,
  `services/lifecycle_aging/`, `services/vendor_sla/`)
  + restructured `services/photo_gallery.py` into a
  package + extended `services/photo_storage.py` with
  `delete_vehicle_photo_object` sibling.
- **Tenancy carriers:** 21 (M1 six + M3 three + M4
  six + M5 two + M6 two + M7 two).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:** unchanged.
- **Milestone 8 next:** M8.1 analytics infrastructure
  + first aggregation (four §9 decisions to confirm,
  ~30 tests, possibly one new model + migration `0022`).
