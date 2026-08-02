---
state: active
date: 2026-08-02
last_session_shipped: SESSION_145
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
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: in-progress
next_session: SESSION_146
next_milestone: 17
next_milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
next_increment: 2
next_increment_name: "M17.2 — Frontend: as_of picker + snapshot history list"
---

# Next session — SESSION_146 · Milestone 17 · Increment 2 (M17.2 — Frontend: as_of picker + snapshot history list)

> **SESSION_145 shipped TWO increments —**
> M17.0 planning + M17.1 backend. Per
> user direction "commit this and
> continue" after M17.0 landed, the
> M17.1 backend was also completed
> and committed in the same session
> (`f217e0d`). Full
> `MILESTONE_17_PLANNING.md` §7 M17.1
> deliverable landed: migration
> `0046_m171_trial_balance_snapshot.py`
> (two CreateModel + two
> UniqueConstraint), new
> `services/accounting/trial_balance_close.py`
> module (three verbs +
> `DuplicateTrialBalanceSnapshotError`),
> three DRF admin endpoints, tenancy
> carrier registration for two new
> models, and 37 focused tests. **All
> three M17.1 §0.a micro-decision
> recommendations applied** (dataclass
> rename, detail URL shape, picker
> default deferral).
>
> **Backend baseline: 4,326 → 4,363
> pass, 1 skipped, 0 fail** (+37 tests,
> zero regressions — in the 30-40
> planning target range). **Frontend
> Vitest baseline: 122 pass**
> (unchanged — no frontend at M17.1).
> Migrations 0043-0045 → **0043-0046**
> (+1). Tenancy carriers 47 → **49**
> (`TrialBalanceSnapshot` +
> `TrialBalanceSnapshotRow`). DRF
> admin surface 104 → **107**
> (freeze / list / detail).
> Frontend operator routes 20
> (unchanged — M14.2 page extends in
> place at M17.2). Permission classes
> 7 actual (see doc note in M17.1
> handoff — M16 retrospective's "8"
> was a miscount). **Zero-drift
> streak extends to nine consecutive
> milestones** (M10 + M11 + M12 + M13
> + M14 + M15 + M16 + M17.1). Celery-
> beat task families 10 (unchanged —
> no beat entry per §5.c Option A
> sync-sibling shape).
>
> **SESSION_146 opens M17.2 —
> frontend `as_of` picker + freeze
> button + snapshot history list.**
> Extends `AccountingTrialBalancePage.tsx`
> in place. Zero backend changes.

## First thing SESSION_146 must do

### 1. Verify starting state

- `git status` — clean (M17.1 commit
  `f217e0d` landed at SESSION_145
  close).
- `git log --oneline -5` — top three
  should be `f217e0d` (M17.1
  backend), `404605e` (M17.0
  planning), `9e832a1` (M16.2
  addendum).
- `python3 manage.py test dealer_ai`
  → **4,363 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **122 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_17_PLANNING.md`
  §7 M17.2 (frontend increment
  scope).
- `docs/handoffs/SESSION_145_m17_inc1_backend.md`
  (backend surface just shipped).
- `frontend/src/pages/AccountingTrialBalancePage.tsx`
  (extension target — 68-line
  current implementation).
- `frontend/src/lib/accountingApi.ts`
  (extension target for new
  fetchers + mutator).
- `backend/dealer_ai/views_accounting.py`
  §M17.1 section (contract for the
  three new endpoints).

## What M17.2 delivers

Per `MILESTONE_17_PLANNING.md` §7
M17.2:

### Frontend api layer

Extend
`frontend/src/lib/accountingApi.ts`:

- `fetchTrialBalance(asOf?: string):
  Promise<TrialBalanceSnapshot>` —
  when `asOf` supplied, include
  `?as_of=<value>` in URL. Backward-
  compatible.
- `freezeTrialBalance(asOf: string):
  Promise<FrozenTrialBalanceSnapshot>`
  — POST /admin/accounting/trial-
  balance/snapshots/.
- `listTrialBalanceSnapshots(page?:
  number, pageSize?: number):
  Promise<{snapshots:
  TrialBalanceSnapshotSummary[],
  total_count: number, page: number,
  page_size: number}>` — GET
  /admin/accounting/trial-balance/
  snapshots/list/.
- `fetchTrialBalanceSnapshot(pk:
  number):
  Promise<FrozenTrialBalanceSnapshot>`
  — GET /admin/accounting/trial-
  balance/snapshots/<pk>/.
- New TypeScript types:
  `TrialBalanceSnapshotSummary`
  (matches list projection),
  `FrozenTrialBalanceSnapshot`
  (matches detail projection),
  `FrozenSnapshotRow`.

### Frontend components

- Install shadcn `Calendar` primitive
  via `npx shadcn add calendar` if
  not present.
- New
  `frontend/src/components/accounting/TrialBalanceDatePicker.tsx`
  — date-only picker (§5.e Option B).
  Default: **today** (§0.a M17.1
  decision 2).

### Frontend page extension

Extend
`frontend/src/pages/AccountingTrialBalancePage.tsx`
in place (do NOT create a parallel
page):

- Date picker at the top of the
  card. Change handler refetches
  via `fetchTrialBalance(asOf)`.
- "Freeze this view" button below
  the totals. Click → POST +
  toast on success + toast on 409
  duplicate.
- "Prior closes" section below the
  trial-balance table: list of
  frozen snapshots (as_of + who
  froze + when + is_balanced chip),
  pagination via M14.1 pattern.
  Click-through to detail (rendered
  inline in-page; no new route per
  M17.2 §4 test-binding).

### Tests

Update
`AccountingTrialBalancePage.test.tsx`:

- Date picker default is today.
- Date change triggers refetch with
  `?as_of=`.
- "Freeze this view" button posts +
  shows toast on 201 + shows error
  toast on 409.
- Snapshot list renders, paginates,
  clicks through to detail.
- Frozen detail view shows frozen
  rows (not live rows).

### Frontend baseline target

**Frontend Vitest: 122 → ~130-138
pass** (+8-16 tests, zero
regressions). Backend baseline
unchanged at **4,363 pass**.

## Explicit non-goals for SESSION_146

- ❌ Do NOT ship M17.3 close-out
  docs.
- ❌ Do NOT modify backend business
  logic (M17.1 backend contract is
  frozen).
- ❌ Do NOT add a new frontend
  route (extend M14.2 page in
  place per §4 test binding).
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_146 with (a) starting-
state verification, (b) reading M17
planning §7 M17.2 + M17.1 backend
handoff, (c) extending
`accountingApi.ts` + creating
`TrialBalanceDatePicker` + extending
`AccountingTrialBalancePage.tsx` +
extending the page tests. Ship the
M17.2 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_145_m17_inc1_backend.md`
   (backend surface freshly shipped)
7. `docs/handoffs/SESSION_145_m17_inc0_planning.md`
   (M17.0 planning close)
8. `docs/CAPABILITY_MATRIX.md` §7q
9. `backend/dealer_ai/views_accounting.py`
   §M17.1 section (endpoint
   contracts — three
   `admin_trial_balance_snapshot_*`
   views)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_145 — M17.1 SHIPPED, M17.2 next)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0046`. Test baseline:
  **4,363 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 122 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered** (unchanged at
  M17.1 — no beat entry per §5.c
  Option A). Next open slot for
  a future detector is 12:00.
- **Milestones shipped:** M1 →
  M16. M17 in progress: M17.0
  planning + M17.1 backend
  shipped at SESSION_145.
- **DRF admin surface:** **107**
  endpoints (104 → 107 at M17.1:
  POST freeze + GET list + GET
  detail).
- **Frontend operator routes:**
  **20** (unchanged — M14.2 page
  extends in place at M17.2).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (**seven modules
  now**: `default_coa.py` +
  `journal.py` + `snapshot.py`
  + `vehicle_cost.py` +
  `sale_booking.py` +
  `bhph_payment.py` +
  **`trial_balance_close.py`**).
- **Frontend accounting
  surface:** `frontend/src/lib/
  accountingApi.ts` with 4
  fetchers + 1 mutator + three
  page components. **Extended
  at M17.2** with
  `freezeTrialBalance` +
  `listTrialBalanceSnapshots` +
  `fetchTrialBalanceSnapshot`
  + new types +
  `TrialBalanceDatePicker`
  component.
- **Tenancy carriers:** **49**
  (47 → 49 at M17.1:
  TrialBalanceSnapshot +
  TrialBalanceSnapshotRow).
- **Permission classes:** **7
  actual** (`IsAdvisorForSlug`,
  `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`,
  `IsDealerOwnerAtActiveDealership`,
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  `ReadOnly`). Zero-drift streak
  extends to **nine consecutive
  milestones** (M10 → M17.1).
  **Prior narrative doc "8" was
  a miscount** — see M17.1
  handoff § doc note.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M17 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 17 status:**
  M17.0 planning SHIPPED +
  M17.1 backend SHIPPED at
  SESSION_145. **M17.2 frontend
  next** (SESSION_146). M17.3
  close-out follows.
