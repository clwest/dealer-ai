---
title: "Milestone 17 — Trial-balance materialization + as_of picker (monthly-close v1)"
status: active
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_144 (skeleton), SESSION_145 (expansion)
milestone: 17
milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_16_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_16_PLANNING.md
  - docs/roadmap/MILESTONE_15_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_14_PLANNING.md
  - docs/roadmap/MILESTONE_14_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_13_PLANNING.md
  - docs/roadmap/MILESTONE_13_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
---

# Milestone 17 — Trial-balance materialization + as_of picker (monthly-close v1)

> **Active planning memo.** Expanded at
> M17.0 (SESSION_145) from the skeleton
> drafted at M16.2 close. §5.a Option E
> confirmed at SESSION_145 open — bundled
> trial-balance materialization + `as_of`
> picker as the smallest complete operator-
> usable slice of monthly-close workflow.
>
> **This milestone is mixed backend+frontend**
> unlike M15/M16 (backend-only). Materializing
> the trial balance requires a new entity +
> a sync-sibling freeze verb; the operator
> UI to select which `as_of` moment to freeze
> (or query the M13.3 live aggregator against)
> is the whole point of the milestone —
> without the picker, operators can only
> freeze "now"; without the entity, the
> picker has nothing durable to record.
>
> **Substrate is 90% ready.** The M13.3
> `compute_trial_balance(dealership, as_of)`
> verb already accepts an `as_of` parameter
> and returns a fully-formed `TrialBalance`
> aggregate. The M14.2 trial-balance page
> already renders that aggregate. What's
> missing: the persistence layer for frozen
> snapshots + the operator UI to pick a
> historical date + the endpoints between
> them. The M15.1 sale-booking sync-sibling
> pattern is the template for the freeze
> verb.

## 0. Engineering practices to preserve from M2-M16

Same posture as M16.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend. The
  M17.2 date picker is a controlled
  input that sends an ISO timestamp to
  the backend; no client-side
  aggregation.
- **Service ownership.** One
  authoritative write path per
  operation.
  `freeze_trial_balance` is the only
  way `TrialBalanceSnapshot` rows come
  into existence at M17.
- **Tenancy discipline.** Every write
  path passes `dealership=` explicitly;
  the pre_save autofill is a safety
  net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M16 convention
  (404 cross-tenant, 409 state-machine
  / duplicate, 400 vocab / validation,
  500 broken-invariant `RuntimeError`
  subclasses per M15.1 + M16.1
  posture).
  **M17.1 introduces
  `DuplicateTrialBalanceSnapshotError`
  → 409** per the `unique_together`
  constraint (§5.d Option A).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in §0.a
  per M5-M16 precedent.
- **Additive extension over fork.**
  M13.3 `compute_trial_balance` is
  called verbatim from the new
  `freeze_trial_balance` verb; the
  M14.2 page extends in place with a
  date-picker component. No fork,
  no parallel implementation.
- **Every M17 test asserting tenant-
  carrier / permission-class /
  endpoint counts uses `>=N`** per
  M9-M16 growth-only-list lesson.
  **Vocab-set assertions use exact
  equality** per M11-M16 fixed-vocab
  lesson.
- **Read-only surfacer vs state-
  transitioning detector vs sync
  sibling-service** — pick the shape
  by whether the trigger is operator
  intent (sync sibling per M13 §5.d
  Option C + M15.1 + M17 proof),
  elapsed condition (detector per
  M11-M14 + M16.1 proof), or read-
  only enumeration (verb per M13.3
  / M14.1 precedent). **M17 is
  sync-sibling** per §5.c Option A —
  freezing a trial balance is
  operator intent ("declare close
  for period X"), not elapsed
  condition.
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another. The
  freeze verb writes header + child
  rows atomically: partial snapshots
  are impossible.
- **Denormalize at write; recompute
  in detectors; refresh AFTER
  sibling writes.** Per M12 §6
  lesson 4 / M13.2 / M14 / M15 §6
  lesson 6 / M16.1 pattern. Frozen
  row totals denormalize the
  aggregate; live queries recompute
  via M13.3.
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 /
  M13.1 / M14.1 / M16.1 posture.
  M17.1 keeps
  `compute_trial_balance` pure (no
  changes); the freeze verb is
  the write path.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default. **Eight consecutive
  milestones now** per M16 §6
  lesson 5. M17 must not add a
  new permission class — the
  freeze / list / detail
  endpoints reuse the M13.3
  permission set.
- **Broken-invariant guards as
  cross-milestone contracts.** Per
  M16 §6 lesson 4. If the frozen
  snapshot's `total_debits !=
  total_credits`, that's a broken
  invariant fired loud — the
  M13.1 `UnbalancedJournalEntryError`
  guard prevents unbalanced entries
  from existing, so any unbalanced
  snapshot means data integrity is
  broken elsewhere.
- **Duplicate account-code constants
  across accounting submodules.**
  Per M15.1 + M16.1 posture — but
  M17 doesn't introduce new account
  codes (§3 item 5).
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson
  15 / M13.3 / M14.1 posture. The
  existing `TrialBalanceSnapshot`
  dataclass in `snapshot.py` is
  the return type of
  `compute_trial_balance`.
  **Naming collision resolution**
  is a §0.a M17.1 micro-decision
  (see §0.a below).
- **Zero-portfolio semantics as
  first-class response state.**
  Per M13 §6 lesson 8 / M14 lesson
  6 / M16.1. A dealership with
  zero postings CAN be frozen —
  the resulting snapshot has
  `rows=[]`, balanced totals of
  zero, and is a valid record of
  "no activity through this date".
- **Money on the wire is Decimal-
  as-string** per M9.5 / M10.1 /
  M12 BHPH / M13-M16 convention.
- **Test-fixture invariants match
  migration invariants.** Per M15
  §6 lesson 3 + M16.1 verified.

### 0.a Change log — resolved decisions

**SESSION_145 M17.0 open (2026-08-02):**

- **§5.a → Option E confirmed at open.**
  User named at SESSION_145 open —
  Trial-balance materialization +
  `as_of` picker (monthly-close v1).
  Bundled per M16.2-close directive
  (the entity + picker ship together
  as the smallest complete operator-
  usable slice of monthly-close
  workflow).
- **§5.b → Option B confirmed as-
  recommended.** `TrialBalanceSnapshot`
  header model + `TrialBalanceSnapshotRow`
  child model. Per-account rows
  frozen at freeze time; recomputing
  at read defeats the purpose of
  materialization (would let
  backdated entries change the
  historical view).
- **§5.c → Option A confirmed as-
  recommended.** Sync-sibling verb
  `freeze_trial_balance` behind a
  POST endpoint. Operator intent
  ("declare close for period X"),
  not elapsed condition. Mirrors
  M15.1 sale-booking shape.
- **§5.d → Option A confirmed as-
  recommended.**
  `unique_together=(dealership,
  as_of)`; second POST at same
  instant raises
  `DuplicateTrialBalanceSnapshotError`
  → 409.
- **§5.e → Option B confirmed as-
  recommended.** Date-only picker
  in UI; server accepts full ISO
  on the wire. Operator mental
  model is calendar dates ("close
  of business May 31"). Time-of-
  day picker defers pending
  operator evidence.
- **§5.f → Option A confirmed as-
  recommended.** Snapshots
  immutable — backdated entries do
  not re-materialize existing
  snapshots. Discrepancy visible
  in a later comparison view (out
  of scope for M17). Immutability
  is the value proposition.
- **Streak extends to 70 planning-
  time as-recommended M5.1 →
  M17.0.** Eight consecutive
  milestones now (M10 + M11 +
  M12 + M13 + M14 + M15 + M16 +
  M17). All six §5 decisions at
  M17.0 open confirmed as-
  recommended.
- **Implementation-time §0.a
  micro-decisions to surface at
  M17.1 open** (do not count
  against streak per M10 §9):
  - Naming collision between the
    new `TrialBalanceSnapshot`
    Django model and the existing
    `TrialBalanceSnapshot` frozen
    dataclass in `snapshot.py`.
    Recommendation: rename the
    dataclass to
    `TrialBalanceComputation` +
    the child dataclass to
    `TrialBalanceComputationRow`
    in the same M17.1 commit that
    introduces the model.
    Rationale: the durable
    persisted entity earns the
    "snapshot" name; the transient
    computation gets clearly
    labeled as such.
  - Frontend picker default value
    (today vs empty vs last
    frozen snapshot's `as_of`).
    Recommendation: today (matches
    the current live view
    behavior; least surprising).
  - Snapshot detail endpoint URL
    shape — `/admin/accounting/
    trial-balance/snapshots/<pk>/`
    vs `/admin/accounting/trial-
    balance/snapshots/<as_of>/`.
    Recommendation: pk (the pk is
    the canonical identifier;
    `as_of` is a queryable
    attribute).

## 1. Business questions this milestone answers

Four operator-workflow questions, each
tied to the trial-balance surface. Every
question was unanswerable before M17
(M13.3 shipped the live aggregator;
M14.2 shipped the render page — but
no persistence layer and no operator
UI to pick `as_of`).

### Q1. Can operators freeze a period-close trial-balance view that stays stable when backdated entries arrive later?

**Before M17:** No. `compute_trial_balance(as_of=X)`
recomputes every call. A backdated
JournalEntry with `posted_at <= X` (e.g.
an operator corrects a misdated M13.2
detector entry after month-end)
silently changes the historical trial
balance. The reported May close on
June 1 is not the same as the reported
May close on June 15 if any backdated
entry lands in between.

**After M17:** Yes.
`freeze_trial_balance(dealership,
as_of, actor)` materializes the M13.3
aggregate to
`TrialBalanceSnapshot` header +
`TrialBalanceSnapshotRow` children.
The frozen rows are immutable per §5.f
Option A. Backdated entries continue to
affect the *live* trial balance (via
M13.3), but they do NOT change the
frozen record. The month-end close for
May can now be a durable, referable
artifact.

### Q2. Can operators query the trial balance as of an arbitrary historical date from the UI?

**Before M17:** No. Frontend
`fetchTrialBalance()` sends no
`as_of` param and always fetches
`as_of=timezone.now()` server-side.
The M13.3 endpoint already accepts
`?as_of=<ISO8601>` but nothing calls
it that way.

**After M17:** Yes. The M14.2 page
gains a date picker (§5.e Option B —
date-only in UI, defaulting to
today). Operator selects any past
date; the frontend sends
`?as_of=<YYYY-MM-DD>T23:59:59<tz-
offset>`; the live aggregator returns
the trial balance as of that moment.

### Q3. Can operators see the history of prior period closes?

**Before M17:** No. No entity records
prior period closes; no endpoint
lists them. Operators wanting to
compare "May close" against "June
close" have no durable record of
either.

**After M17:** Yes.
`GET /admin/accounting/trial-balance/
snapshots/` lists all frozen
snapshots for the tenant (paginated
per M14.1 pattern);
`GET /admin/accounting/trial-
balance/snapshots/<pk>/` returns the
full frozen row set for one
snapshot. The M14.2 page grows a
"Prior closes" section listing
recent snapshots + click-through to
the detail view.

### Q4. Does the M13.3 live aggregator still work unchanged?

**Before M17:** M13.3 aggregator is
the only trial-balance path — used
by the live view.

**After M17:** Yes.
`compute_trial_balance` is unchanged
(pure recompute per M13.3 §0.a
decision 2). The new
`freeze_trial_balance` verb *calls*
it internally, then materializes
the result. The live path is
preserved for real-time queries; the
frozen path is for durable closes.
Two consumers, one aggregator.

## 2. What existing primitives extend

M17 continues the "additive extension
over fork" pattern (M11.1 / M12.3 /
M13.2 / M14.1 / M15.1 / M16.1). One
new module extending
`services/accounting/`, two new models,
three new endpoints, one frontend page
extension, one new small component.

- **`services/accounting/snapshot.py::compute_trial_balance`**
  — unchanged. The new freeze verb
  calls it internally with the
  operator's `as_of`, then persists
  the result. **Pure recompute
  posture per M13.3 §0.a decision 2
  is preserved** — the entity
  materialization is a strictly
  additive layer on top.
- **`TrialBalanceSnapshot` frozen
  dataclass** in `snapshot.py` —
  renamed to `TrialBalanceComputation`
  at M17.1 (see §0.a). Callers in
  `views_accounting.py` +
  `tests/test_m133_trial_balance_*`
  update to the new name in the
  same commit.
- **`services/accounting/journal.py::post_journal_entry`**
  — no changes. Freeze operation
  doesn't post journal entries; it
  reads them via M13.3.
- **`views_accounting.py::admin_trial_balance`**
  — no changes. The GET endpoint
  already accepts `?as_of=` per
  M13.3.
- **`admin/accounting/trial-balance/`
  endpoint** — no changes. Frontend
  starts sending `?as_of=` on user
  input at M17.2.
- **`frontend/src/lib/accountingApi.ts::fetchTrialBalance`**
  — extended signature:
  `fetchTrialBalance(asOf?: string):
  Promise<TrialBalanceSnapshot>`.
  When `asOf` is supplied, it flows
  into the URL query. Backward-
  compatible (call sites without
  the arg keep working; but there
  is only one call site at M17.2).
- **`frontend/src/pages/AccountingTrialBalancePage.tsx`**
  — extended in place with the
  date picker + snapshot-history
  section. No parallel page.
- **shadcn `Calendar` /
  `DatePicker` component** — added
  via the shadcn CLI at M17.2 if
  not already present. Follows
  M14 UX conventions.
- **`_auth_helpers.make_dealership`**
  — already seeds default COA per
  M15.1 §0.a decision 8; all M17
  tests using the helper have
  the substrate needed.

## 3. What's NOT in this milestone (deferrals)

Every deferral has a clear re-entry
path. **Twelve M17-specific + five
universal = 17 deferrals**, matching
M15/M16's density.

**M17-specific deferrals:**

1. **Backdated-entry discrepancy
   surface.** §5.f Option A locks
   snapshots as immutable. When a
   backdated JournalEntry lands
   with `posted_at <= X` for
   already-frozen snapshot at `X`,
   the frozen rows do not change,
   but the live aggregate does. A
   "your frozen close no longer
   matches live" comparison view
   is deferred to a later
   milestone (candidate name:
   period-close audit). Re-entry:
   surfaces when operator evidence
   names the reconciliation pain.
2. **Auto-freeze on schedule.** §5.c
   Option A locks freeze as
   operator intent. A Celery-beat
   auto-freeze at month-end
   (e.g. `crontab(day_of_month=1,
   hour=1, minute=0)`) would be a
   natural add-on but requires
   answering "which timezone?"
   and "what if operator hasn't
   finalized month-end
   adjustments?" — both are
   operational contract questions
   the platform doesn't yet
   answer. Re-entry: a monthly-
   close automation milestone
   once operator rhythm evidence
   accumulates.
3. **Reopen / unfreeze workflow.**
   §5.f Option A snapshots are
   immutable at M17. Operators
   who realize a close was
   premature have no
   "unfreeze" path — they must
   freeze a new snapshot at a
   later moment. Explicit
   unfreeze / reopen is deferred
   to a later milestone (would
   need audit-log semantics —
   who reopened, when, why,
   what changed). Re-entry:
   period-close reopen
   milestone.
4. **Period comparison view.**
   Rendering two frozen
   snapshots side-by-side
   ("May close vs June close",
   variance per account) is
   deferred. The list + detail
   endpoints ship at M17.1;
   the comparison UI would
   layer on top. Re-entry: a
   financial-reports milestone.
5. **Frozen snapshot as CSV / PDF
   export.** Operators may want
   to export closed months for
   auditor / CPA handoff. Deferred
   to a reporting milestone. The
   detail endpoint ships in JSON
   at M17.1; export layers on top.
6. **Time-of-day picker.** §5.e
   Option B locks the picker at
   date-only. A time-of-day
   picker (for intra-day
   closes) defers until
   operator evidence surfaces
   the need. Re-entry: extend
   the picker component in
   place; server contract is
   already time-aware.
7. **Tenant timezone
   configuration.** M17 assumes
   the dealership's timezone
   from the request context
   (Django's `TIME_ZONE`
   setting). Per-dealership
   timezone configuration (for
   multi-timezone rollouts) is
   deferred to a tenancy
   milestone. At M17-scale
   (single project timezone),
   `America/Denver` /
   `America/Phoenix` is
   sufficient.
8. **Freezing arbitrary future
   dates.** M17 accepts any
   `as_of` value the picker
   emits — including future
   dates. Future dates produce
   a snapshot equivalent to
   `as_of=timezone.now()`
   (since no entries can be
   posted-in-the-future). This
   is technically valid but
   operationally weird;
   deferred as a §5-scope
   question until operator
   evidence surfaces the need
   for a guard.
9. **Snapshot-source FK on
   comparison / audit trails.**
   No FK from downstream
   period-comparison entities
   back to snapshots (there
   are no downstream entities
   yet). Defer per M15 §3
   item 9 posture.
10. **Snapshot immutability
    enforced at DB level.**
    M17 relies on service-
    layer discipline
    (`freeze_trial_balance` is
    the only write path) to
    preserve immutability. DB-
    level enforcement (e.g. a
    trigger rejecting UPDATE
    on `TrialBalanceSnapshotRow`)
    is deferred until operator
    evidence surfaces
    data-integrity risk.
11. **Materialized aggregate
    reports (P&L, balance
    sheet).** Trial balance is
    the raw substrate; P&L and
    balance-sheet reports layer
    on top by grouping
    accounts. Deferred to a
    financial-reports
    milestone. Trial-balance
    materialization at M17 is
    the prerequisite; the
    consumer reports come
    later.
12. **Snapshot detail versioning.**
    If the COA changes between
    freeze and read (e.g. an
    account is renamed at
    M18+), the frozen row
    stores `account_code` and
    `account_name` at freeze
    time. Re-render displays
    those historical values.
    A "rename history"
    reconciliation view is
    deferred.

**Universal deferrals (any accounting
milestone):**

- Payroll (external service).
- W-2 / 1099 generation (external
  service).
- Year-end tax return preparation
  (external CPA).
- GAAP-compliant audited financial
  reporting (out of scope for
  platform v1).
- Direct DMS integration (belongs
  to a future vendor-integration
  milestone).

## 4. What existing tests bind

- **M13.3 `test_m133_trial_balance_service.py`**
  — `compute_trial_balance` contract
  tests. M17 preserves the verb
  unchanged. Existing tests continue
  to pass verbatim. Import of the
  dataclass name may need updating
  if the rename to
  `TrialBalanceComputation` lands
  (per §0.a M17.1 note).
- **M13.3 `test_m133_trial_balance_endpoint.py`**
  — GET endpoint tests. Existing
  tests unchanged (no endpoint
  contract change; the frontend
  starts sending `?as_of=` but
  the endpoint already accepts
  it).
- **M14.1 `test_m141_accounting_list_endpoint.py`**
  — journal-entry list. Unchanged.
- **`AccountingTrialBalancePage.test.tsx`**
  (frontend Vitest) — existing
  render tests. Updated in the
  M17.2 commit to cover the new
  picker + snapshot-history
  section.
- **Tenancy carrier count test**
  — M17 adds two new tenanted
  models (`TrialBalanceSnapshot`,
  `TrialBalanceSnapshotRow`).
  Count moves from 47 → 49.
  Assertion uses `>=` per M9-M16
  growth-only-list lesson.
- **Permission-class count test**
  — M17 adds three new endpoints
  reusing
  `IsSalesManagerOrOwnerAtActiveDealership`.
  Class count stays at 8. Zero-
  drift streak extends to nine
  consecutive milestones. Vocab-
  set assertion continues to
  use exact equality.
- **Endpoint count** — DRF admin
  surface 104 → 107 (+3: POST
  snapshots, GET snapshot list,
  GET snapshot detail). Assertion
  uses `>=` per lesson.
- **Frontend operator route
  count** — 20 (unchanged; the
  M14.2 trial-balance page
  extends in place, no new
  route).

## 5. Load-bearing decisions

Six decisions. **All six confirmed
as-recommended at SESSION_145 M17.0
open.** Streak extends to **70
planning-time as-recommended M5.1 →
M17.0** (eight consecutive milestones
now).

### 5.a `[RESOLVED at SESSION_145 open]` — Milestone target selection

**Question.** Which candidate from
the M16 retrospective §8 unblocked-
work list defines M17 scope?

**Decision.** **Option E — Trial-
balance materialization + `as_of`
picker (monthly-close v1).** User
named at SESSION_145 open.

**Rationale.** (1) M16.2 close
bundled Option E explicitly — the
entity and picker are two halves of
one operator-usable slice
(materialization without a picker
has no consumer; picker without
materialization has nothing durable
to record). (2) Substrate is 90%
ready — M13.3
`compute_trial_balance` already
accepts `as_of`; M14.2 already
renders the aggregate. The only
missing pieces are persistence +
operator UI. (3) M16's BHPH
activity now makes period-over-
period reports meaningful (interest
income + Notes Receivable
amortization) — the operational
timing is right. (4) Sync-sibling
shape is proven (M15.1 template)
and matches the operator-intent
trigger. (5) Mixed backend+
frontend scope is the natural
next step after two backend-only
milestones (M15/M16) — the
frontend surface has accumulated
enough of a picker gap that
addressing it now is high value.
(6) No new account codes needed;
no new permission classes; the
delta stays clean.

### 5.b `[RESOLVED at SESSION_145 open]` — Snapshot storage shape

**Question.** How is a frozen trial
balance persisted?

- **Option A** — header only
  (`TrialBalanceSnapshot`:
  `dealership`, `as_of`,
  `total_debits`, `total_credits`,
  `is_balanced`,
  `created_by`, `created_at`).
  Rows recomputed from
  `JournalEntryLine` at read time
  via the M13.3 aggregator with
  `as_of=snapshot.as_of`.
- **Option B** — header +
  `TrialBalanceSnapshotRow`
  child (`snapshot`, `account_code`,
  `account_name`, `account_type`,
  `debit_total`, `credit_total`,
  `natural_balance`). Rows frozen
  at freeze time; read serves
  materialized values.
- **Option C** — header + JSONB
  column carrying the full row
  list. One row per snapshot;
  no separate child table.
  Schema-less, easier to
  denormalize, harder to query
  per-account.

**Recommendation drafted.** **Option B.**
Rationale: (1) Materialization
without immutability of the per-
account rows is not
materialization — Option A would
let backdated entries change the
historical view (defeats the
value proposition per §5.f).
(2) Option C works but sacrifices
queryability — "what was 123000
BHPH Notes Receivable's balance
on May 31?" needs a JSON path
extraction, whereas the child
table permits standard SQL. (3)
Child table is small — one row
per COA account per snapshot;
COA has ~15-30 accounts today;
even at 100 snapshots that's a
few thousand rows. (4) Matches
the shape of every other
accounting entity we've shipped
(JournalEntry + JournalEntryLine
is header+child). Consistent
mental model. (5) Frozen row
values are exactly what the
M14.2 render already expects
(one row per account with
totals) — the projection layer
is near-verbatim reuse.

### 5.c `[RESOLVED at SESSION_145 open]` — Freeze trigger shape

**Question.** How does a snapshot
come into existence?

- **Option A** — sync-sibling verb
  `freeze_trial_balance(*, dealership,
  as_of, actor) -> TrialBalanceSnapshot`
  behind a POST endpoint. Operator
  clicks "Freeze this view" in
  M14.2; frontend sends POST with
  the current `as_of`; verb
  materializes.
- **Option B** — Celery-beat
  auto-freeze at month-end.
  E.g. `crontab(day_of_month=1,
  hour=1, minute=0)` freezes the
  prior month's close for every
  tenant.
- **Option C** — hybrid: operator
  can freeze manually via POST,
  and a monthly detector also
  auto-freezes if no snapshot
  exists for the prior month.

**Recommendation drafted.** **Option A.**
Rationale: (1) Freezing is
operator intent ("this is the
close for period X"), not
elapsed condition. M13 §5.d
Option C hybrid categorization
places this shape squarely as
sync-sibling per the M15.1
proof. (2) Auto-freeze (Option B)
requires answering "which
timezone?" and "what if operator
hasn't finalized adjustments?"
— both are operational contract
questions the platform doesn't
yet answer. Defer per §3 item 2.
(3) Option C hybrid is
premature — sync-sibling ships
the operator-usable surface;
auto-freeze can layer on top
once the manual workflow has
run for a few real closes. (4)
Mirrors M15.1's shape verbatim
(module structure, atomic
posture, verb signature) —
zero novelty in the freeze
implementation.

### 5.d `[RESOLVED at SESSION_145 open]` — Uniqueness constraint on (dealership, as_of)

**Question.** Can two snapshots
exist for the same tenant with the
exact same `as_of`?

- **Option A** —
  `unique_together=(dealership,
  as_of)` (or `UniqueConstraint`).
  Second POST at same instant
  raises
  `DuplicateTrialBalanceSnapshotError`
  → 409.
- **Option B** — allow multiple.
  Every freeze creates a new
  record; operator queries "most
  recent" via `ORDER BY
  created_at DESC LIMIT 1`.
- **Option C** — unique per
  (dealership, `as_of` truncated
  to date). Two snapshots on the
  same date are impossible;
  finer granularity (multiple
  times per day) impossible.

**Recommendation drafted.** **Option A.**
Rationale: (1) An `as_of`
timestamp uniquely identifies "the
trial balance at this exact
moment." Two snapshots at the
same moment is either a UI
double-click bug or an
operational mistake — either
way, surfacing as a 409 gives
the operator explicit feedback.
(2) Option B allows silent
duplicates + forces every query
to answer "which one do I
want?" — worst of both worlds.
(3) Option C conflates two
concerns: uniqueness (a data-
integrity property) and
granularity (a UI concern per
§5.e). Better to keep them
separate — the picker restricts
granularity to date at the UI
level (§5.e Option B); the DB
constraint is precise-timestamp
uniqueness. (4) Matches
M12.2's
`BhphNote.unique_together=('dealership',
'note_number')` posture —
dealer-scoped unique constraint
per business-meaningful natural
key.

### 5.e `[RESOLVED at SESSION_145 open]` — Picker granularity

**Question.** What granularity
does the M14.2 date picker
expose?

- **Option A** — full date+time
  picker. Operator can freeze
  the trial balance as of any
  precise moment.
- **Option B** — date-only
  picker; server treats the
  emitted value as
  `YYYY-MM-DD 23:59:59` in the
  tenant timezone.
- **Option C** — three
  presets ("today", "end of
  last month", "end of last
  year") without free-form
  input.

**Recommendation drafted.** **Option B.**
Rationale: (1) Operator mental
model is calendar dates —
"close of business May 31,"
not "close at 5:47 PM on May
31." Matching the mental model
reduces UI friction. (2)
Option A surfaces precision
that operators rarely need;
the extra time control is
noise 95% of the time. (3)
Option C is too rigid —
operators occasionally want
to freeze mid-month for
audit / lender / vehicle-
finance rate resets. Free-
form date preserves this. (4)
Server contract is time-
aware (M13.3 accepts full
ISO), so the picker's
constraint is a UI-layer
choice; a future time-of-day
picker can layer on without
schema changes. (5) End-of-
day = 23:59:59 tenant-local
matches the operational
convention of "reports as of
end-of-business."

### 5.f `[RESOLVED at SESSION_145 open]` — Backdated-entry policy

**Question.** When journal entries
land with `posted_at` earlier
than an already-frozen snapshot's
`as_of`, does the snapshot re-
materialize?

- **Option A** — snapshot rows
  are immutable. Backdated
  entries continue to affect the
  live aggregate (via M13.3),
  but do NOT touch the frozen
  rows. Discrepancy visible in
  a later comparison view (out
  of scope for M17).
- **Option B** — re-freeze
  automatically on backdate.
  Every backdated JournalEntry
  triggers re-materialization
  of any snapshot with
  `as_of >= entry.posted_at`.
  Expensive; invalidates
  immutability.
- **Option C** — mark
  affected snapshots as
  "stale" via a boolean;
  operator re-freezes manually.
  Preserves the current row
  values but signals that they
  no longer match live.

**Recommendation drafted.** **Option A.**
Rationale: (1) Immutability is
the whole value proposition —
the frozen record IS "what we
reported at close." A backdated
correction should not silently
rewrite history. (2) Option B
is architecturally corrosive —
if the snapshot can change
after freeze, why freeze at
all? Live aggregator (M13.3)
already answers "current state
as of X." (3) Option C is a
middle ground but adds a
boolean without giving
operators a resolution
workflow (there's no
comparison view + no reopen
verb). The stale flag would
mostly be noise. (4) The
right long-term shape is a
period-close audit
milestone that shows "what
was reported vs what live
now shows" side-by-side (see
§3 item 1). M17's immutable
posture is the substrate;
the audit view layers on
later. (5) Cheapest to
implement + easiest to
explain to operators ("closed
means closed").

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
   §6 (six lessons carry into M17) +
   §8 (M16 unblocked work — trial-
   balance materialization explicitly
   named)
6. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §6 (M15.1 sync-sibling template)
   + §8 (M15 unblocked work)
7. `docs/roadmap/MILESTONE_14_PLANNING.md`
   §3 deferral 2 (M14.2 `as_of`
   picker deferred to a monthly-
   close slice — that slice is M17)
8. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5 M13.3 (pure recompute posture
   that M17 preserves + materialization
   layer bolts on top)
9. `docs/CAPABILITY_MATRIX.md` §7q
10. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
    §1.1 (chart of accounts — no
    additions at M17), §2.4 (period-
    close operational rhythm)

## 7. Sequencing

**Two code increments + one close-out
+ one planning (this one) = four
total.** Mixed backend+frontend scope
per §5.a Option E bundling. Compare
to M15/M16 (three total, backend-only)
+ M14 (six total for the largest
mixed-scope milestone).

### Increment 0 (M17.0) — Planning refinement + decision review

**Scope.** SESSION_145 (this session).
Target selection (§5.a) confirmed at
open; §5.b-§5.f drafted with
recommendations for user confirmation
before M17.1 code. Full memo
expansion (this document). Handoff
at `docs/handoffs/SESSION_145_m17_
inc0_planning.md`.

**Deliverable.**
- This planning memo, expanded from
  the M16.2 skeleton.
- §0.a change log with all six §5
  decisions resolved.
- Session handoff.
- `00-START-NEXT-SESSION.md`
  overwritten with M17.1 priority.

**Backend baseline unchanged:** 4,326
pass, 1 skipped, 0 fail. Frontend
Vitest unchanged: 122 pass.

### Increment 1 (M17.1) — Backend: TrialBalanceSnapshot entity + freeze verb + endpoints

**Scope.** Next session. Single
backend increment covering all
M17 write-path + read-path work.

**Deliverable.**
- Migration `0046_m171_trial_
  balance_snapshot.py` adding two
  new models per §5.b Option B:
  - `TrialBalanceSnapshot`
    (header): `dealership` FK,
    `as_of` DateTimeField,
    `total_debits` /
    `total_credits`
    DecimalField(14, 2),
    `is_balanced` BooleanField,
    `created_by` FK to User
    (nullable — operator-triggered
    freeze), `created_at`
    auto_now_add. `Meta.unique_
    together = (('dealership',
    'as_of'),)` per §5.d Option A.
  - `TrialBalanceSnapshotRow`
    (child): `snapshot` FK to
    TrialBalanceSnapshot (CASCADE),
    `account_code` CharField,
    `account_name` CharField,
    `account_type` CharField
    (using `GL_ACCOUNT_TYPE_*`
    vocab), `debit_total` /
    `credit_total` /
    `natural_balance`
    DecimalField(14, 2).
    `Meta.unique_together =
    (('snapshot',
    'account_code'),)` +
    `Meta.ordering = ('account_
    code',)`.
- Rename existing
  `TrialBalanceSnapshot` frozen
  dataclass in `snapshot.py` →
  `TrialBalanceComputation`;
  rename `TrialBalanceRow` →
  `TrialBalanceComputationRow`.
  Update every call site
  (`views_accounting.py`,
  `tests/test_m133_trial_balance_
  service.py`,
  `services/accounting/__init__.py`
  `__all__`). Per §0.a M17.1
  naming decision.
- New `services/accounting/
  trial_balance_close.py` module:
  - `freeze_trial_balance(*,
    dealership, as_of, actor) ->
    TrialBalanceSnapshot` —
    atomic sync-sibling verb.
    Calls `compute_trial_balance`
    with the `as_of`; creates
    header row + child rows in
    one transaction. Raises
    `DuplicateTrialBalanceSnapshotError`
    (409) if `unique_together`
    violated. Raises
    `CrossTenantGLAccountError`
    (404) if `dealership`
    context doesn't match the
    request tenant (per M15.1 +
    M16.1 pattern).
  - `list_trial_balance_snapshots(*,
    dealership, page=1,
    page_size=25) -> dict` —
    paginated list per M14.1
    pattern.
  - `get_trial_balance_snapshot(*,
    dealership, snapshot_id) ->
    TrialBalanceSnapshot | None`
    — detail retrieve, tenant-
    scoped, returns None on
    cross-tenant.
- New
  `DuplicateTrialBalanceSnapshotError`
  domain exception. 409 mapping.
- Extend `services/accounting/
  __init__.py` `__all__` with
  the new verbs + models +
  error class.
- Three new DRF admin endpoints
  in `views_accounting.py`:
  - `POST /admin/accounting/
    trial-balance/snapshots/` —
    freeze. Body: `{ "as_of":
    "<ISO8601>" }`. Returns
    201 with the frozen
    snapshot projection. Reuses
    `IsSalesManagerOrOwnerAtActiveDealership`.
  - `GET /admin/accounting/
    trial-balance/snapshots/`
    — list. Query: `?page=&
    page_size=`. Returns
    `{"snapshots": [...],
    "page": N, "page_size":
    N, "total": N}`.
  - `GET /admin/accounting/
    trial-balance/snapshots/
    <int:pk>/` — detail.
    Returns full frozen row
    set. 404 on cross-tenant
    per fail-closed posture.
- Focused tests (~30-40
  target) in new `tests/
  test_m171_trial_balance_
  materialization.py`:
  - `freeze_trial_balance`
    happy path: creates header
    + N child rows.
  - Zero-portfolio freeze:
    header row created, zero
    children, balanced.
  - `unique_together` violation
    raises
    `DuplicateTrialBalanceSnapshotError`.
  - Cross-tenant raises
    `CrossTenantGLAccountError`.
  - Atomic: partial write
    impossible (mock a child-
    row failure, header rolls
    back).
  - Frozen rows snapshot the
    account name (later COA
    rename does not affect
    the frozen row).
  - Backdated entry does NOT
    change frozen rows
    (asserts §5.f Option A).
  - `list_trial_balance_snapshots`
    pagination + tenancy
    isolation.
  - `get_trial_balance_snapshot`
    detail returns frozen
    rows; None on cross-
    tenant.
  - POST endpoint: 201,
    happy path.
  - POST endpoint: 409 on
    duplicate `as_of`.
  - POST endpoint: 400 on
    missing/invalid `as_of`
    param.
  - POST endpoint: 403 on
    non-permitted role.
  - GET list endpoint:
    pagination shape.
  - GET detail endpoint:
    tenancy isolation +
    404 on cross-tenant.
  - Tenancy carrier count
    47 → 49 (`>=` per
    lesson).
  - Permission class count
    unchanged at 8 (zero-
    drift streak extends to
    nine).
  - Endpoint count 104 →
    107 (`>=` per lesson).
- No new post-LLM scrub
  stages.
- No new Celery-beat
  entries.

**Backend baseline target:** 4,326
→ ~4,356-4,366 pass (+30-40 tests,
0 regressions). Frontend Vitest:
122 (unchanged at M17.1 — frontend
delta at M17.2).

### Increment 2 (M17.2) — Frontend: as_of picker + snapshot history list

**Scope.** Session after M17.1.
Single frontend increment.
Extends the M14.2 page in place.

**Deliverable.**
- Extend
  `frontend/src/lib/accountingApi.ts`:
  - `fetchTrialBalance(asOf?:
    string)`. When `asOf`
    supplied, includes
    `?as_of=<value>` in URL.
  - `freezeTrialBalance(asOf:
    string): Promise<TrialBalanceSnapshot>`
    → POST /admin/accounting/
    trial-balance/snapshots/.
  - `listTrialBalanceSnapshots(page?:
    number)`.
  - `fetchTrialBalanceSnapshot(pk:
    number)`.
  - New TypeScript types
    matching backend
    projections
    (`TrialBalanceSnapshotSummary`,
    `FrozenTrialBalanceSnapshot`,
    `FrozenSnapshotRow`).
- Install shadcn `Calendar`
  primitive via `npx shadcn
  add calendar` if not present.
  Wrap in a
  `TrialBalanceDatePicker`
  component in
  `frontend/src/components/
  accounting/` (date-only per
  §5.e Option B; default
  today per §0.a M17.1 note).
- Extend
  `frontend/src/pages/AccountingTrialBalancePage.tsx`:
  - Add date picker at the
    top of the card.
  - On date change: refetch
    via `fetchTrialBalance(asOf)`.
  - Add "Freeze this view"
    button. On click: POST +
    show toast + refetch
    snapshot list.
  - Add "Prior closes"
    section below the trial-
    balance table: list of
    snapshots (as_of + who
    froze + when + is_balanced
    chip), pagination via M14.1
    pattern. Click-through to
    detail via
    `/admin/accounting/
    trial-balance/snapshots/
    <pk>/` (rendered inline
    in-page, not new route
    per §4).
- Update
  `AccountingTrialBalancePage.test.tsx`
  with new coverage:
  - Date picker default is
    today.
  - Date change triggers
    refetch with `?as_of=`.
  - "Freeze this view" button
    posts + shows toast on
    success + shows error
    toast on 409.
  - Snapshot list renders,
    paginates, clicks through
    to detail.
  - Frozen snapshot detail
    view shows frozen rows
    (not live rows).
- Zero backend changes.
- Zero migration.
- Frontend operator route
  count unchanged at 20 (M14.2
  page extends in place).

**Backend baseline unchanged:**
~4,356-4,366 pass (M17.1 delta
sustained). **Frontend Vitest
target:** 122 → ~130-138 pass
(+8-16 tests, 0 regressions).

### Increment 3 (M17.3) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7r + roadmap
flip + M18 planning skeleton per
standing user directive (M10.8 /
M11.7 / M12.8 / M13.4 / M14.5 /
M15.2 / M16.2 precedent).

**Deliverable.**
- `docs/roadmap/MILESTONE_17_
  RETROSPECTIVE.md` written at
  M17.3 close.
- `docs/CAPABILITY_MATRIX.md`
  §7r section describing the
  M17 trial-balance
  materialization + `as_of`
  picker surface.
- `docs/roadmap/IMPLEMENTATION_
  ROADMAP.md` §Milestone 17
  SHIPPED entry added.
- Frontmatter flip on this
  doc: `status: active` →
  `status: shipped`.
- `docs/roadmap/MILESTONE_18_
  PLANNING.md` skeleton for
  the M17 §8 unblocked-work
  list.
- `00-START-NEXT-SESSION.md`
  overwritten with M18.0
  priority.
- Coordinated commit landing
  all M17.3 docs together.
- **Standing question at M17
  close:** review whether
  M18 should be an
  intentional UI-polish
  milestone (M14 shape) to
  batch-consume Option G +
  any UX gaps surfaced from
  operator use of M15 + M16
  + M17 surfaces. Bundle
  candidate to bring to the
  user at M17 close.

**Backend baseline at M17
close:** ~4,356-4,366 pass
(M17.1 delta sustained; no
code changes at M17.3).
**Frontend Vitest at M17
close:** ~130-138 pass (M17.2
delta sustained).

---

*Full memo. All six §5 decisions
confirmed as-recommended at
SESSION_145 M17.0 open.*
