---
state: active
date: 2026-08-02
last_session_shipped: SESSION_133
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: in-progress
next_session: SESSION_134
next_milestone: 14
next_milestone_name: "Operator UI for accounting substrate"
next_increment: 1
next_increment_name: "M14.1 — Backend: journal-entry list + cost-posting failure endpoints"
---

# Next session — SESSION_134 · Milestone 14 · Increment 1 (M14.1 — Backend: list + failure endpoints)

> **SESSION_133 shipped M14.0 —**
> planning-only. Expanded
> `MILESTONE_14_PLANNING.md` from
> skeleton to active memo. **M14
> target locked: Option D — Operator
> UI for the M13 accounting
> substrate.** All six §5 load-
> bearing decisions confirmed as-
> recommended at session open (§5.a
> Option A four-surface scope +
> §5.b Option B filter-less list +
> §5.c Option A Decimal-as-string +
> §5.d Option A dedicated
> `dealer-ai-accounting/*` nav
> group + §5.e Option A shadcn
> `<Dialog>` reversal + §5.f
> Option A Vitest coverage for
> every new page). **Streak: 53
> planning-time as-recommended M5.1
> → M14.0** across five consecutive
> milestones now (M10 + M11 + M12 +
> M13 + M14).
>
> §7 locks six increments (five
> code + one close-out): M14.1
> backend endpoints → M14.2
> frontend trial-balance render →
> M14.3 frontend journal-entry
> browser + detail → M14.4
> frontend reversal dialog + cost-
> posting failure card → M14.5
> close-out. Projected M14 close
> totals: backend 4,240 → ~4,255
> (+15); frontend Vitest 78 →
> ~113 (+35); DRF admin surface
> 102 → 104 (+2); frontend
> operator routes 17 → 20 (+3);
> tenancy carriers 47 (unchanged);
> permission classes 8 (unchanged
> — zero-drift streak to six
> consecutive milestones);
> Celery-beat task families 9
> (unchanged — read-only
> milestone); zero migrations.
>
> **Backend baseline: 4,240 pass,
> 1 skipped, 0 fail** (unchanged
> — planning-only session).
> **Frontend Vitest baseline: 78
> pass** (unchanged).
>
> **Push authorization:** one
> local commit (M14.0 planning +
> handoff + session-start refresh)
> pending user authorization at
> SESSION_133 close. Doc-only
> commit — push can execute
> immediately once authorized (no
> test-suite dependency).
>
> **SESSION_134 opens M14.1 —
> backend list + failure
> endpoints.** Two new pure query
> verbs + two new DRF admin
> endpoints. Read-only. No schema
> changes. Full spec in
> `MILESTONE_14_PLANNING.md` §7
> Increment 1.

## First thing SESSION_134 must do

### 1. Verify starting state

- `git status` — clean (M14.0
  commit landed at SESSION_133
  close; user authorized push).
- `git log --oneline -5` — top
  should be the M14.0 planning
  commit or similar.
- `git log origin/main..HEAD
  --oneline` — **empty** (M14.0
  commit pushed).
- `python3 manage.py test dealer_ai`
  → **4,240 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` → **78
  pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_14_
  PLANNING.md` §7 Increment 1
  (implementation spec).
- `docs/roadmap/MILESTONE_13_
  RETROSPECTIVE.md` §6 (twelve
  lessons carry into M14).
- `docs/handoffs/SESSION_133_m14
  _inc0_planning.md` (previous
  session).
- `backend/dealer_ai/views_
  accounting.py` (M13.1 + M13.3
  endpoint patterns to mirror).
- `backend/dealer_ai/services/
  accounting/journal.py` (M13.1
  verbs — extend with list verb).
- `backend/dealer_ai/services/
  accounting/vehicle_cost.py`
  (M13.2 detector — extend with
  failure query verb).

## What M14.1 delivers

Per `MILESTONE_14_PLANNING.md` §7
M14.1:

### Backend service verbs (2 new)

1. **`list_journal_entries(
   dealership, page=1,
   page_size=25)`** in
   `services/accounting/journal.py`.
   - Ordering: `-posted_at` (most
     recent first).
   - Returns list + total count +
     pagination metadata.
   - **No filters** at M14.1 per
     §5.b Option B. Filter
     surface layers at M15+ per
     operator evidence.
   - Tenancy-scoped: filter on
     `dealership=` and
     `lines__account__dealership=`
     for cross-tenant guards.

2. **`detect_cost_posting_failures(
   dealership, now=None,
   threshold_hours=24)`** in
   `services/accounting/vehicle_
   cost.py`.
   - Query filter:
     `posted_at__isnull=True AND
     is_estimate=False AND
     created_at__lte=now-
     threshold`.
   - Threshold default 24h (one
     detector-run boundary; the
     M13.2 detector runs at
     10:00 daily).
   - Returns list of unposted
     `VehicleCost` rows older
     than the threshold.

### Backend admin endpoints (2 new)

3. **`GET admin/accounting/
   journal-entries/list/`** in
   `views_accounting.py`.
   - Query params: `?page=` +
     `?page_size=` (both
     optional, defaults 1 and
     25).
   - Reuses
     `IsSalesManagerOrOwnerAt
     ActiveDealership`.
   - Empty-list response for
     zero-portfolio tenants
     (not 404) per zero-
     portfolio semantics
     (M13.3 lesson 8).
   - Decimal-as-string on all
     money fields per §5.c
     Option A.

4. **`GET admin/accounting/
   cost-posting-failures/`** in
   `views_accounting.py`.
   - Query param: optional
     `?threshold_hours=<int>`
     (default 24).
   - Same permission class.
   - Empty-list response for
     zero-failure tenants.
   - Projects VehicleCost →
     dict with fields: id +
     vehicle_stock +
     category_group + amount +
     is_estimate +
     created_at + age_in_hours.

### URL entries (2 new)

5. Add both endpoints to
   `backend/dealer_ai/urls.py`
   under the M13.1 accounting
   URL block.

### Tests (~15-20 focused)

6. Add tests in
   `backend/dealer_ai/tests/`
   matching M13.1 + M13.3
   naming (e.g.
   `test_m141_accounting_
   list_endpoint.py` +
   `test_m141_cost_posting_
   failures_endpoint.py` +
   service verb tests).
7. Test coverage areas:
   - List: pagination, ordering
     (recent-first), tenancy
     guard (no cross-tenant
     leakage), empty-state
     (zero postings → empty
     list not 404), permission
     denial (401/403 without
     role).
   - Failures: threshold
     default 24h, custom
     threshold, tenancy guard,
     empty-state, estimate
     exclusion, posted-cost
     exclusion (posted_at NOT
     NULL), age-in-hours
     projection.

### Deltas at M14.1 close

- **Backend baseline:** 4,240 →
  ~4,255 (+15 tests).
- **Frontend baseline:** 78
  (unchanged — backend-only
  increment).
- **DRF admin surface:** 102 →
  104 (+2).
- **Tenancy carriers:** 47
  (unchanged — no new models).
- **Permission classes:** 8
  (unchanged — zero-drift streak
  continues).
- **Celery-beat task families:**
  9 (unchanged — no detectors
  added).
- **Migrations:** none (no
  schema changes).

## Explicit non-goals for SESSION_134

- ❌ Do NOT ship frontend work
  (starts at M14.2).
- ❌ Do NOT add filter surface
  to the list endpoint (§5.b
  Option B locks filter-less
  MVP).
- ❌ Do NOT add new write verbs
  (M14 is entirely read-only).
- ❌ Do NOT add new tenancy
  carriers.
- ❌ Do NOT add new permission
  classes.
- ❌ Do NOT add schema changes /
  migrations.
- ❌ Do NOT modify M1-M13
  business logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_134 with (a)
starting-state verification, (b)
the read-first list, then (c)
implementing the two service
verbs + two admin endpoints per
`MILESTONE_14_PLANNING.md` §7
M14.1 with matching test
coverage. Ship the M14.1 handoff
at `docs/handoffs/SESSION_134_
m14_inc1_list_and_failures.md`.

Backend baseline at SESSION_134
close: **~4,255 pass** (was 4,240
at M14.0). Frontend baseline
unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_14_PLANNING.md`
   §7 M14.1
6. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §6 (twelve lessons carry
   into M14)
7. `docs/handoffs/SESSION_133_m14_inc0_planning.md`
   (previous session)
8. `docs/CAPABILITY_MATRIX.md` §7n
9. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_133 — M14.0 shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0044`. Test baseline:
  **4,240 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 78 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **9
  scheduled task families
  registered** (M7.2 02:00 →
  M13.2 10:00). Next available
  slot: 11:00. No new families
  at M14 (read-only milestone).
- **Milestones shipped:** M1 →
  **M13**. **M14 in progress**
  (M14.0 planning shipped
  SESSION_133).
- **DRF admin surface:** **102**
  endpoints. Projected 104 at
  M14.1 close.
- **Frontend operator routes:**
  **17** (unchanged — M14
  frontend starts at M14.2).
  Projected 20 at M14 close.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (M13 — four
  modules; two verbs additive
  at M14.1).
- **Tenancy carriers:** **47**
  (unchanged at M14 — no new
  models).
- **Permission classes:** **8**
  (unchanged — projected zero
  drift through M14 close per
  §0 practices).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M14 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Accounting substrate:** four
  M13 modules in
  `services/accounting/`.
  Extended at M14.1 with two
  new pure query verbs
  (list_journal_entries in
  `journal.py` +
  detect_cost_posting_failures
  in `vehicle_cost.py`).
- **Milestone 14 next:** M14.1
  backend list + failures
  endpoints per
  `MILESTONE_14_PLANNING.md` §7
  Increment 1. Five code
  increments + one close-out
  remain.
