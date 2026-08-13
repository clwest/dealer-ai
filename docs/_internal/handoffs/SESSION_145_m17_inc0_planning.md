---
title: "SESSION_145 handoff — Milestone 17 · Increment 0 (M17.0 — planning refinement)"
status: historical
type: handoff
date: 2026-08-02
session: 145
milestone: 17
milestone_status: in-progress
milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_145 — Milestone 17 · Increment 0 (M17.0 — planning refinement)

## What shipped

Planning-only session per the M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 / M15.0
/ M16.0 precedent. Full memo expansion
+ all six §5 load-bearing decisions
resolved at open. **§5.a → Option E
confirmed** (Trial-balance
materialization + `as_of` picker
named as the M17 target — monthly-
close v1, bundled per the M16.2-close
directive). **§5.b–§5.f all confirmed
as-recommended.** Streak extends to
**70 planning-time as-recommended
M5.1 → M17.0** across eight
consecutive milestones now (M10 +
M11 + M12 + M13 + M14 + M15 + M16 +
M17).

**Backend baseline unchanged:** 4,326
pass, 1 skipped, 0 fail (verified at
session open). **Frontend Vitest
baseline unchanged:** 122 pass.
Migrations `0043`–`0045` (unchanged).
Tenancy carriers 47 (unchanged).
DRF admin surface 104 (unchanged).
Frontend operator routes 20
(unchanged). Permission classes 8
(unchanged). Celery-beat task
families 10 (unchanged — M17 does
not introduce a beat entry per §5.c
Option A sync-sibling shape).

## Load-bearing decisions confirmed at M17.0 open

Six decisions per M10.0 / M11.0 /
M12.0 / M13.0 / M14.0 / M15.0 /
M16.0 precedent. All confirmed as-
recommended.

**§5.a — Milestone target selection.**
Option E — Trial-balance
materialization + `as_of` picker
(monthly-close v1). Rationale:
substrate 90% ready (M13.3
`compute_trial_balance` already
accepts `as_of`; M14.2 already
renders it); M16 BHPH activity
makes period-over-period reports
meaningful; sync-sibling pattern
proven (M15.1); bundle at M16.2
close established the entity +
picker as one operator-usable
slice.

**§5.b — Snapshot storage shape.**
Option B — header
(`TrialBalanceSnapshot`) + child
rows (`TrialBalanceSnapshotRow`),
per-account rows frozen at freeze
time. Rationale: materialization
without immutable per-account rows
is not materialization —
recomputing at read defeats the
value proposition (would let
backdated entries change the
historical view).

**§5.c — Freeze trigger shape.**
Option A — sync-sibling verb
`freeze_trial_balance(*,
dealership, as_of, actor)` behind
a POST endpoint. Rationale:
freezing is operator intent
("declare close for period X"),
not elapsed condition. Mirrors
M15.1 sale-booking shape verbatim.

**§5.d — Uniqueness constraint.**
Option A —
`unique_together=(dealership,
as_of)`; second POST at same
instant raises
`DuplicateTrialBalanceSnapshotError`
→ 409. Rationale: an `as_of`
timestamp uniquely identifies "the
trial balance at this exact
moment"; double-freeze is a UI
double-click bug worth surfacing
loud.

**§5.e — Picker granularity.**
Option B — date-only picker in UI;
server treats emitted value as
`YYYY-MM-DD 23:59:59` in tenant TZ.
Rationale: operator mental model is
calendar dates ("close of business
May 31"); time-of-day picker can
layer on if operator evidence
surfaces the need. Server contract
is time-aware; the granularity
constraint is a UI choice.

**§5.f — Backdated-entry policy.**
Option A — snapshot rows are
immutable; backdated entries do
NOT re-materialize existing
snapshots. Rationale: immutability
is the whole value proposition;
"closed means closed." Discrepancy
between frozen close and current
live comes into scope at a later
period-close audit milestone (§3
item 1).

## Streak

**70 planning-time as-recommended
M5.1 → M17.0.** Eight consecutive
milestones now (M10 + M11 + M12 +
M13 + M14 + M15 + M16 + M17) with
every §5 decision confirmed as-
recommended at planning-time open.

Three implementation-time §0.a
micro-decisions surfaced for M17.1
(do not count against streak per
M10 §9):

1. Naming collision between the
   new `TrialBalanceSnapshot`
   Django model and the existing
   `TrialBalanceSnapshot` frozen
   dataclass in `snapshot.py` —
   recommendation to rename the
   dataclass to
   `TrialBalanceComputation` + the
   child dataclass to
   `TrialBalanceComputationRow`
   at M17.1.
2. Frontend picker default value —
   recommendation "today" (matches
   current live-view behavior).
3. Snapshot detail endpoint URL
   shape — recommendation pk
   (canonical identifier).

## What's next: SESSION_146 M17.1 backend

Per `MILESTONE_17_PLANNING.md` §7
M17.1:

- Migration `0046_m171_trial_
  balance_snapshot.py` — two new
  models (`TrialBalanceSnapshot`
  header + `TrialBalanceSnapshotRow`
  child) per §5.b Option B. `Meta.
  unique_together=(('dealership',
  'as_of'),)` per §5.d Option A.
- Rename existing
  `TrialBalanceSnapshot` frozen
  dataclass in `snapshot.py` →
  `TrialBalanceComputation`; update
  all call sites in the same commit.
- New `services/accounting/trial_
  balance_close.py` module with
  three verbs
  (`freeze_trial_balance` sync
  sibling per §5.c Option A;
  `list_trial_balance_snapshots`
  paginated; `get_trial_balance_
  snapshot` detail retrieve).
- New
  `DuplicateTrialBalanceSnapshotError`
  domain exception mapped to 409.
- Three new DRF admin endpoints:
  POST snapshots (freeze), GET
  list, GET detail. All reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  (zero-drift streak extends to
  nine consecutive milestones).
- ~30-40 focused tests in
  `tests/test_m171_trial_balance_
  materialization.py`.
- Tenancy carriers 47 → 49
  (`>=` per lesson). DRF admin
  surface 104 → 107 (`>=` per
  lesson). Permission classes 8
  (unchanged). Celery-beat task
  families 10 (unchanged — no
  beat entry at M17 per §5.c
  Option A).
- No frontend changes at M17.1
  (frontend delta at M17.2).

**Backend baseline target at
M17.1 close:** 4,326 → ~4,356-
4,366 pass. **Frontend Vitest
unchanged:** 122 pass.

## What lands at M17.2 (SESSION_147)

- Extend
  `frontend/src/lib/accountingApi.ts`
  with `fetchTrialBalance(asOf?)`
  + `freezeTrialBalance` +
  `listTrialBalanceSnapshots` +
  `fetchTrialBalanceSnapshot` +
  new TypeScript types.
- Install shadcn `Calendar` if not
  present; new
  `TrialBalanceDatePicker`
  component (date-only per §5.e
  Option B; default today per
  §0.a M17.1 note).
- Extend
  `AccountingTrialBalancePage.tsx`
  in place with the date picker
  + "Freeze this view" button +
  "Prior closes" list + inline
  detail view.
- New Vitest coverage for the
  picker, freeze flow, list,
  detail. **Frontend Vitest
  target:** 122 → ~130-138
  pass.
- Zero backend changes at M17.2.

## What lands at M17.3 (SESSION_148)

- Retrospective + capability
  matrix §7r + roadmap flip +
  M18 planning skeleton +
  session-start refresh +
  coordinated commit landing
  all M17.3 docs.
- **Standing question at M17
  close:** review whether M18
  should be an intentional UI-
  polish milestone (M14 shape)
  to batch-consume Option G +
  any UX gaps surfaced from
  operator use of M15 + M16
  + M17 surfaces.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
   (this session's expansion target)
6. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
   §6 + §8
7. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §6 (M15.1 sync-sibling template)
8. `docs/roadmap/MILESTONE_14_PLANNING.md`
   §3 deferral 2 (M14.2 `as_of`
   picker deferred to monthly-close
   slice — that slice is M17)
9. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5 M13.3 (pure recompute posture
   M17 preserves)
10. `docs/CAPABILITY_MATRIX.md` §7q
