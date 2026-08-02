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
next_increment: 1
next_increment_name: "M17.1 — Backend: TrialBalanceSnapshot entity + freeze verb + endpoints"
---

# Next session — SESSION_146 · Milestone 17 · Increment 1 (M17.1 — Backend: TrialBalanceSnapshot entity + freeze verb + endpoints)

> **SESSION_145 shipped M17.0 —**
> full memo expansion for
> `MILESTONE_17_PLANNING.md` (draft
> skeleton → active memo, 4-
> increment sequencing, six §5
> decisions resolved). **§5.a
> Option E confirmed** — Trial-
> balance materialization + `as_of`
> picker (monthly-close v1),
> bundled per M16.2-close
> directive. **§5.b–§5.f all
> confirmed as-recommended.**
> Streak extends to **70 planning-
> time as-recommended M5.1 →
> M17.0** across **eight
> consecutive milestones now**
> (M10 + M11 + M12 + M13 + M14 +
> M15 + M16 + M17). Three §0.a
> M17.1 micro-decision
> recommendations surfaced for
> resolution at M17.1 open (do
> not count against streak per
> M10 §9).
>
> **Backend baseline: 4,326 pass,
> 1 skipped, 0 fail** (unchanged
> — planning-only session).
> **Frontend Vitest baseline: 122
> pass** (unchanged). Migrations
> `0043`–`0045` (unchanged).
> Tenancy carriers 47 (unchanged).
> DRF admin surface 104
> (unchanged). Frontend operator
> routes 20 (unchanged).
> Permission classes 8
> (unchanged — zero-drift streak
> holds at eight consecutive
> milestones). Celery-beat task
> families 10 (unchanged — M17
> does not introduce a beat
> entry per §5.c Option A sync-
> sibling shape).
>
> **SESSION_146 opens M17.1 —
> backend entity + freeze verb
> + three endpoints.** Per
> `MILESTONE_17_PLANNING.md` §7
> M17.1. Single backend
> increment covering all M17
> write-path + read-path work.

## First thing SESSION_146 must do

### 1. Confirm the three §0.a M17.1 micro-decision recommendations

Recorded at M17.0 close:

1. **Naming collision resolution.**
   The new `TrialBalanceSnapshot`
   Django model collides with the
   existing `TrialBalanceSnapshot`
   frozen dataclass in
   `services/accounting/snapshot.py`.
   **Recommendation: rename the
   dataclass to
   `TrialBalanceComputation`** +
   the child dataclass
   `TrialBalanceRow` →
   `TrialBalanceComputationRow`
   in the same M17.1 commit that
   introduces the model. Update
   every call site
   (`views_accounting.py`,
   `tests/test_m133_trial_balance_*`,
   `services/accounting/__init__.py`
   `__all__`). Rationale: the
   durable persisted entity
   earns the "snapshot" name;
   the transient computation
   gets clearly labeled as such.
2. **Frontend picker default
   value** (for M17.2 sequencing
   reference).
   **Recommendation: today**
   — matches current live-view
   behavior; least surprising.
3. **Snapshot detail endpoint
   URL shape.**
   **Recommendation: `/admin/
   accounting/trial-balance/
   snapshots/<int:pk>/`** —
   pk is the canonical
   identifier; `as_of` is a
   queryable attribute.

### 2. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M17.0 planning
  commit.
- `python3 manage.py test dealer_ai`
  → **4,326 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **122 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

## What M17.1 delivers

Per `MILESTONE_17_PLANNING.md` §7
M17.1:

### Backend

- **Migration `0046_m171_trial_
  balance_snapshot.py`** adding
  two new models:
  - `TrialBalanceSnapshot`
    (header): `dealership` FK,
    `as_of` DateTimeField,
    `total_debits` /
    `total_credits`
    DecimalField(14, 2),
    `is_balanced` BooleanField,
    `created_by` FK to User
    (nullable), `created_at`
    auto_now_add.
    `Meta.unique_together =
    (('dealership', 'as_of'),)`
    per §5.d Option A.
  - `TrialBalanceSnapshotRow`
    (child): `snapshot` FK
    (CASCADE), `account_code`,
    `account_name`,
    `account_type` (using
    `GL_ACCOUNT_TYPE_*` vocab),
    `debit_total`,
    `credit_total`,
    `natural_balance`.
    `Meta.unique_together =
    (('snapshot',
    'account_code'),)` +
    `Meta.ordering =
    ('account_code',)`.
- **Rename existing
  `TrialBalanceSnapshot` frozen
  dataclass** in
  `snapshot.py` →
  `TrialBalanceComputation`
  (per §0.a M17.1 decision 1).
  Rename `TrialBalanceRow` →
  `TrialBalanceComputationRow`.
  Update every call site.
- **New
  `services/accounting/trial_
  balance_close.py` module:**
  - `freeze_trial_balance(*,
    dealership, as_of, actor)
    -> TrialBalanceSnapshot`
    — atomic sync-sibling
    verb per §5.c Option A.
    Calls
    `compute_trial_balance`;
    materializes header + rows
    in one transaction. Raises
    `DuplicateTrialBalanceSnapshotError`
    (409) or
    `CrossTenantGLAccountError`
    (404).
  - `list_trial_balance_snapshots(*,
    dealership, page=1,
    page_size=25) -> dict` —
    paginated per M14.1
    pattern.
  - `get_trial_balance_snapshot(*,
    dealership, snapshot_id)
    -> TrialBalanceSnapshot |
    None` — tenant-scoped
    retrieve.
- **New
  `DuplicateTrialBalanceSnapshotError`**
  domain exception → 409
  mapping.
- **Extend `__init__.py`
  `__all__`** with new verbs,
  models, error class.
- **Three new DRF admin
  endpoints in
  `views_accounting.py`:**
  - `POST /admin/accounting/
    trial-balance/snapshots/`
    — freeze. Body: `{
    "as_of": "<ISO8601>" }`.
    201 with projection.
  - `GET /admin/accounting/
    trial-balance/snapshots/`
    — paginated list.
  - `GET /admin/accounting/
    trial-balance/snapshots/
    <int:pk>/` — detail
    (per §0.a M17.1 decision
    3).
  - All reuse
    `IsSalesManagerOrOwnerAtActiveDealership`
    (zero-drift streak
    extends to nine
    consecutive milestones).

### Tests

**~30-40 focused tests** in new
`tests/test_m171_trial_balance_
materialization.py` per §7 M17.1:

- Freeze happy path (header +
  child rows).
- Zero-portfolio freeze (empty
  rows, balanced totals, valid
  record).
- `unique_together` violation
  raises
  `DuplicateTrialBalanceSnapshotError`.
- Cross-tenant raises
  `CrossTenantGLAccountError`.
- Atomic: partial write
  impossible.
- Frozen rows snapshot the
  account name (COA rename
  post-freeze doesn't affect
  the frozen row).
- Backdated entry does NOT
  change frozen rows (asserts
  §5.f Option A).
- List pagination + tenancy
  isolation.
- Detail retrieve + 404 on
  cross-tenant.
- POST endpoint: 201, 409, 400,
  403.
- GET list + detail endpoint
  contracts.
- Tenancy carrier count 47 →
  49 (`>=`).
- Permission class count
  unchanged at 8 (vocab-set
  equality).
- Endpoint count 104 → 107
  (`>=`).

### Non-goals for M17.1

- ❌ No frontend changes.
- ❌ No Celery-beat entries
  (§5.c Option A sync-sibling).
- ❌ No new account codes.
- ❌ No new post-LLM scrub
  stages.

## Backend baseline target

**4,326 → ~4,356-4,366 pass**
(+30-40 tests, 0 regressions).
Frontend Vitest: 122 (unchanged
— M17.2 delta).

## Explicit non-goals for SESSION_146

- ❌ Do NOT ship M17.2 frontend
  code.
- ❌ Do NOT modify M1-M16
  business logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_146 with (a)
confirming the three §0.a M17.1
micro-decision recommendations,
(b) starting-state verification,
(c) building migration + models
+ verbs + endpoints + tests
per §7 M17.1. Ship the M17.1
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
   (active memo)
6. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
7. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §6 (M15.1 sync-sibling
   template that M17.1 mirrors)
8. `docs/handoffs/SESSION_145_m17_inc0_planning.md`
   (this session's handoff)
9. `docs/CAPABILITY_MATRIX.md` §7q

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_145 — M17.0 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0045`. Test baseline:
  **4,326 pass**, 1 skipped, 0
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
  M17.0 — no beat entry per
  §5.c Option A). Next open
  slot for a future detector
  is 12:00.
- **Milestones shipped:** M1 →
  M16 (SESSION_144 close). M17
  planning shipped at
  SESSION_145 M17.0.
- **DRF admin surface:** **104**
  endpoints (three new POST/GET
  land at M17.1 → 107).
- **Frontend operator routes:**
  **20** (unchanged at M17 —
  M14.2 page extends in place).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (six modules
  today: `default_coa.py` +
  `journal.py` + `snapshot.py`
  + `vehicle_cost.py` +
  `sale_booking.py` +
  `bhph_payment.py`; **seventh
  module `trial_balance_close.py`
  lands at M17.1**).
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
- **Tenancy carriers:** **47**
  (unchanged at M17.0 — moves
  to 49 at M17.1).
- **Permission classes:** **8**
  (unchanged — zero-drift streak
  extends to **eight consecutive
  milestones** now; ninth after
  M17.1 as no new class ships).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M17 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 17 status:** M17.0
  planning SHIPPED (SESSION_145).
  M17.1 backend implementation
  next (SESSION_146). M17.2
  frontend picker + snapshot
  history at SESSION_147. M17.3
  close-out at SESSION_148.
