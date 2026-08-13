---
title: "SESSION_145 handoff — Milestone 17 · Increment 2 (M17.2 — Frontend: as_of picker + snapshot history list)"
status: historical
type: handoff
date: 2026-08-02
session: 145
milestone: 17
milestone_status: in-progress
milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
increment: 2
increment_status: shipped
commit: 4235137
---

# SESSION_145 — Milestone 17 · Increment 2 (M17.2 — Frontend: as_of picker + snapshot history list)

> **Three increments in one session.** M17.0 planning
> (`404605e`) + M17.1 backend (`f217e0d`) +
> M17.1 docs (`bedc615`) + **M17.2 frontend
> (`4235137`)** all landed in SESSION_145 per user
> direction "continue" after each milestone
> increment shipped. M17.3 close-out remains for
> next session.

## What shipped

Frontend-only increment per
`MILESTONE_17_PLANNING.md` §7 M17.2. Extends the
M14.2 `AccountingTrialBalancePage.tsx` in place —
zero new operator routes per §4 test binding.

**One §0.a M17.2 micro-decision recommendation
applied at open** (do not count against streak):

- **Picker uses native `<input type="date">`
  wrapped in the existing shadcn `Input`
  primitive rather than installing shadcn
  `Calendar`.** Rationale: date-only mental
  model per §5.e Option B; no new dependency;
  OS-native picker fully accessible + trivially
  testable via Vitest `change` events; browser
  handles locale automatically. If operator
  evidence surfaces the need for a richer
  picker (multi-month, range, presets), swap
  in shadcn `Calendar` at that time.

## Delivered

**`frontend/src/lib/accountingApi.ts`
extensions** (~100 lines added):

- `fetchTrialBalance(asOf?: string)` — extended
  signature; when `asOf` is supplied,
  URL includes `?as_of=<value>`. Backward-
  compatible with the M14.2 caller.
- `freezeTrialBalance(asOf: string) ->
  Promise<FrozenTrialBalanceSnapshot>` — POST
  `/admin/accounting/trial-balance/snapshots/`.
- `listTrialBalanceSnapshots({page?, pageSize?})`
  — paginated list per M14.1 shape.
- `fetchTrialBalanceSnapshot(pk: number)` —
  detail retrieve.
- New TypeScript types matching M17.1 backend
  projections: `TrialBalanceSnapshotSummary`
  (list projection), `FrozenSnapshotRow`,
  `FrozenTrialBalanceSnapshot` (detail
  projection), `TrialBalanceSnapshotListPage`.

**New component
`frontend/src/components/accounting/TrialBalanceDatePicker.tsx`**
(~85 lines):

- `TrialBalanceDatePicker` — controlled `<input
  type="date">` wrapped in the shadcn `Input`
  primitive with an accessible label.
- Pure helpers `todayIsoDate()` (returns
  `YYYY-MM-DD` for browser today) +
  `dateToEndOfDayIso(dateIso: string)` (converts
  to full ISO timestamp at 23:59:59 local per
  the operational "close of business"
  convention).

**Extended
`frontend/src/pages/AccountingTrialBalancePage.tsx`**
(~500 lines total, +200 net):

- New "Query controls" card at the top: date
  picker + "Freeze this view" button + inline
  success/error banners.
- Live trial-balance card refetches when the
  picker changes (via `useEffect` with
  `asOfDate` dependency).
- Freeze button posts + refreshes snapshot list
  + shows inline success banner ("Frozen —
  snapshot #X recorded for Y"). 409 duplicate
  surfaces as a distinct banner ("A snapshot
  for this exact moment already exists…").
  Generic errors surface with the underlying
  message. Banner clears on next picker
  change.
- New "Prior closes" card below the trial-
  balance table: paginated list of frozen
  snapshots (as_of + who froze + when + is_
  balanced chip). Empty-state UI when
  `total_count === 0`.
- New `FrozenSnapshotDetailCard` rendered
  inline (no new route per §4 binding) when a
  prior-close row is clicked. Renders the
  frozen row values from
  `fetchTrialBalanceSnapshot(pk)` — not the
  live aggregator. Close button dismisses.
- All existing M14.2 functionality preserved
  (cost-posting failures card, dealership-
  slug title, balanced/unbalanced chip,
  loading/error states).

**Extended
`frontend/src/pages/AccountingTrialBalancePage.test.tsx`**:

- 15 M14.2 legacy tests preserved (header
  render, loading state, row rendering, money
  formatting, balanced/unbalanced chip, empty-
  state message updated to match new copy,
  error state, account-type badges, slug in
  title, failures card hide/show, attention
  badge).
- 12 new M17.2 tests: picker renders with
  today default, picker date flows to
  `fetchTrialBalance` as an ISO timestamp,
  refetch on picker change, freeze button
  renders, freeze click posts + shows success
  banner, 409 → duplicate error banner,
  generic error banner, snapshot list refetch
  after freeze, empty snapshot list state
  ("No period closes…"), snapshot list
  renders when non-empty, click loads detail
  via `fetchTrialBalanceSnapshot`, Close
  button dismisses detail, frozen detail
  renders frozen row values, banner clears on
  picker change.

**New
`frontend/src/components/accounting/TrialBalanceDatePicker.test.tsx`**
(6 tests):

- `todayIsoDate` returns browser today in
  `YYYY-MM-DD`.
- `dateToEndOfDayIso` converts to 23:59:59
  local; round-trips through `Date`.
- Component renders as date input with
  supplied value.
- `onChange` fires with new value on native
  change event.
- Disabled prop propagates.
- Custom label prop honoured.

## Baseline delta

**Frontend Vitest: 122 → 140 pass** (+18 tests,
0 regressions). Exceeds the 8-16 planning target
by 2 because I added the picker-helpers test
file (6 tests). **Backend baseline unchanged at
4,363 pass, 1 skipped, 0 fail** (zero backend
changes at M17.2). `tsc --noEmit` clean. `vite
build` clean.

- Migrations 0043-0046 (unchanged).
- Tenancy carriers 49 (unchanged).
- DRF admin surface 107 (unchanged).
- **Frontend operator routes 20 (unchanged —
  extended M14.2 page in place per §4 test
  binding).**
- Permission classes 7 (unchanged — zero-drift
  streak holds at nine consecutive milestones).
- Celery-beat task families 10 (unchanged).

## Streak update

**70 planning-time as-recommended M5.1 → M17.0.**
No change to the streak — M17.2 is
implementation-time work. One implementation-
time §0.a micro-decision applied (native date
input vs shadcn Calendar) without counting per
M10 §9.

## What's next: SESSION_147 M17.3 close-out

Per `MILESTONE_17_PLANNING.md` §7 M17.3:

- `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
  written at M17.3 close.
- `docs/CAPABILITY_MATRIX.md` §7r section
  describing the M17 trial-balance
  materialization + `as_of` picker surface.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 17 SHIPPED entry added.
- Frontmatter flip on
  `docs/roadmap/MILESTONE_17_PLANNING.md`:
  `status: active` → `status: shipped`.
- `docs/roadmap/MILESTONE_18_PLANNING.md`
  skeleton for the M17 §8 unblocked-work
  list.
- `00-START-NEXT-SESSION.md` overwritten with
  M18.0 priority.
- Coordinated commit landing all M17.3 docs
  together.
- **Standing question at M17 close:** review
  whether M18 should be an intentional UI-
  polish milestone (M14 shape) to batch-
  consume Option G + any UX gaps surfaced
  from operator use of M15 + M16 + M17
  surfaces.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_145_m17_inc0_planning.md`
7. `docs/handoffs/SESSION_145_m17_inc1_backend.md`
8. `docs/CAPABILITY_MATRIX.md` §7q
9. `frontend/src/pages/AccountingTrialBalancePage.tsx`
   (M17.2 delivered surface)
10. `backend/dealer_ai/views_accounting.py`
    §M17.1 (endpoint contracts that M17.2
    consumes)
