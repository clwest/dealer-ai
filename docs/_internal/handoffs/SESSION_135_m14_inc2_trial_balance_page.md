---
title: "SESSION_135 handoff — Milestone 14 · Increment 2 (M14.2 — Frontend: trial-balance render page)"
status: historical
type: handoff
date: 2026-08-02
session: 135
milestone: 14
milestone_status: in-progress
milestone_name: "Operator UI for accounting substrate"
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_135 — Milestone 14 · Increment 2 (M14.2 — Frontend: trial-balance render page)

## What shipped

First frontend increment of M14. New
`accountingApi.ts` client module + new
`AccountingTrialBalancePage.tsx`
component + new operator route +
Vitest coverage. Zero backend work.
Consumes the existing M13.3 endpoint
`GET admin/accounting/trial-balance/`.

### API client (1 new file)

1. **`frontend/src/lib/accountingApi.ts`**
   — new. Exports `fetchTrialBalance()`
   plus TypeScript type surface for
   `TrialBalanceSnapshot` +
   `TrialBalanceRow` + `GLAccountType`
   union (`asset | liability | equity
   | revenue | expense`). Comments
   name every M13.1 + M13.3 + M14.1
   endpoint the module will grow to
   consume across M14.3 / M14.4 (M14.2
   only wires the trial-balance
   fetcher — additional fetchers land
   as their increments ship).
   Decimal-as-string preserved per
   §5.c Option A.

### Page component (1 new file)

2. **`frontend/src/pages/
   AccountingTrialBalancePage.tsx`**
   — new. Renders the trial-balance
   snapshot as:
   - Header block (h1 + description).
   - Card with title + as-of
     timestamp + balanced/unbalanced
     chip.
   - Per-account table (account_code
     + name + type badge + debits +
     credits + natural balance).
     Numbers use `Intl.NumberFormat`
     with `en-US` currency locale
     and `tabular-nums` CSS for
     right-aligned column readability.
   - Footer with grand debits +
     grand credits (rendered only
     when rows exist).
   - Empty-state UI: "No postings
     yet. Once journal entries are
     posted (via the M13.2 cost-
     reconciliation detector or any
     future sale-booking / payment
     GL post), account balances will
     appear here."
   - Loading + error states via the
     M11 / M12 `useEffect` +
     cancellation-flag pattern
     (matches
     `DealerAiBhphPortfolio.tsx`
     posture).

### Route registration (1 edit)

3. **`frontend/src/main.tsx`** —
   added `AccountingTrialBalancePage`
   import + registered route
   `dealer-ai-accounting/trial-
   balance` under `RequireAuth`. Per
   §5.d Option A this is the first
   route of the new
   `dealer-ai-accounting/*` group.
   Additional group members
   (journal-entries + detail) land
   at M14.3.

### Vitest coverage (1 new file, 11 tests)

4. **`frontend/src/pages/
   AccountingTrialBalancePage.test.tsx`**
   — new. Uses `vi.mock` on
   `@/lib/accountingApi` to stub
   `fetchTrialBalance`. 11 focused
   tests:
   - renders the h1 header (role
     query to disambiguate from card
     title).
   - shows loading spinner before
     fetch resolves.
   - renders every account row (4
     accounts).
   - formats money with locale
     currency ($1,250.00 shape).
   - renders "Balanced" chip when
     `is_balanced=true`.
   - renders "Unbalanced" chip when
     `is_balanced=false`.
   - shows empty-state message when
     `rows: []`.
   - hides totals footer when rows
     is empty.
   - renders error message on fetch
     rejection.
   - renders account-type badges
     per row.
   - renders dealership slug in
     card title.

## Deltas at SESSION_135 close

- **Backend baseline:** 4,277
  (unchanged — frontend-only
  increment).
- **Frontend Vitest baseline:** 78 →
  **89 pass** (+11 tests, target was
  ~10; overshoot by 1 for role-based
  header disambiguation).
- **Frontend operator routes:** 17 →
  **18** (+1 —
  `dealer-ai-accounting/trial-
  balance`).
- **DRF admin surface:** 104
  (unchanged).
- **Tenancy carriers:** 47
  (unchanged).
- **Permission classes:** 8
  (unchanged).
- **Migrations:** none.
- **`tsc --noEmit`:** clean.
- **`vite build`:** clean (~1.9s,
  ~1.1MB bundle / ~303kB gzip —
  pre-existing chunk-size warning
  unchanged since M2.7).

## Browser verification

Started dev servers (Django on 8001,
Vite on 5173), logged in as
`smoke_owner`, navigated to
`/dealer-ai-accounting/trial-balance`:

- **Empty-state render (zero
  postings):** balanced chip shown,
  "No postings yet" message
  rendered, no table + no footer as
  designed.
- **Populated render:** seeded two
  journal entries (a $12,500 demo
  sale + $875.50 recon accrual),
  reloaded page. Rendered 4
  accounts (Cash / Recon WIP / A/P
  Trade / Vehicle Sales), currency
  formatted correctly, totals
  $13,375.50 debits + $13,375.50
  credits, "Balanced" chip.
- **Console:** 0 errors, 0
  warnings.
- **Route gating:** direct visit to
  `/dealer-ai-accounting/trial-
  balance` while unauthenticated
  redirected to
  `/login?next=/dealer-ai-
  accounting/trial-balance`
  (RequireAuth working).

Seeded demo journal entries cleaned
up post-verification so the dev DB
returns to the M13-shipped state.

## Implementation-time micro-decisions

Per M10 §9 — recorded but do NOT
count against the M14 planning-time
as-recommended streak (which stands
at 53 M5.1→M14.0).

1. **No sidebar entry added at
   M14.2.** The App.tsx `NAV_ITEMS`
   array holds 10 primary operator
   surfaces (Overview / Live
   Assistant / Inventory / Leads /
   Coaching / Admin / Team /
   Analytics / F&I / Setup). Neither
   BHPH (M12) nor Sales (M11)
   operator surfaces got sidebar
   entries — the pattern is "primary
   nav is limited; secondary
   surfaces navigated to via URL or
   cross-links from primary pages."
   Kept M14.2 consistent with M12
   posture. **Follow-up
   consideration:** a future
   "navigation refactor" increment
   could add sidebar entries for
   accounting + BHPH + sales as
   their surfaces mature. Not
   deferred formally because it's
   not part of any current
   milestone scope.
2. **Header disambiguated via role
   query in Vitest.** `getByText(/
   Trial Balance/i)` matched both
   the `<h1>` and the `<CardTitle>`
   containing "Trial Balance" —
   ambiguity resolved via
   `getByRole("heading", { level: 1,
   name: ... })`. More semantic +
   more resilient to layout tweaks.
3. **`account_type` rendered as
   shadcn `<Badge variant="outline">`
   per row** rather than plain text.
   Improves scanning readability
   (five distinct account types
   would otherwise be indistinguish-
   able in a busy table). Matches
   the M12 BHPH portfolio bucket-
   label posture.
4. **Grand-totals footer conditional
   on `rows.length > 0`.** Empty
   trial balance shows only the
   empty-state message + balanced
   chip — no zero-value totals row.
   Cleaner empty state; totals
   footer is only meaningful when
   there's something to total.
5. **`Intl.NumberFormat` with
   `en-US` currency locale.** Matches
   M12 BHPH `formatMoney` posture.
   `tabular-nums` CSS class applied
   to numeric columns for
   consistent right-alignment.
6. **`as_of` timestamp formatted
   via
   `Date.toLocaleString("en-US")`
   with short month + 2-digit hour/
   minute.** Human-readable format;
   passes through raw ISO string on
   parse failure as fallback.
7. **Empty-state message references
   the M13.2 detector by name.**
   Grounds the empty state in what
   the operator can actually do to
   populate it — the M13.2 detector
   runs at 10:00 daily and
   auto-posts unposted VehicleCost
   rows. Alternative "no data"
   messages don't tell the operator
   why the page is empty or when it
   will populate.

## Files touched

Created:

1. `frontend/src/lib/accountingApi
   .ts` — 60 lines.
2. `frontend/src/pages/Accounting
   TrialBalancePage.tsx` — 200
   lines.
3. `frontend/src/pages/Accounting
   TrialBalancePage.test.tsx` — 220
   lines.
4. `docs/handoffs/SESSION_135_m14_
   inc2_trial_balance_page.md` —
   this handoff.

Modified:

5. `frontend/src/main.tsx` —
   `AccountingTrialBalancePage`
   import + new route registration
   with comment block referencing
   §5.d Option A.

## Verifications passed at SESSION_135 close

- `python3 manage.py test dealer_ai`
  → **4,277 pass, 1 skipped, 0
  fail** (unchanged — frontend-only
  increment).
- `npm test` → **89 pass** (was 78;
  +11 Vitest tests).
- `npx tsc --noEmit` clean.
- `npx vite build` clean.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- Browser verification passed
  (empty + populated + error +
  auth-gate states all render
  correctly; zero console
  errors/warnings).

## What SESSION_136 (M14.3) picks up

Per `MILESTONE_14_PLANNING.md` §7
Increment 3:

- Extend `frontend/src/lib/
  accountingApi.ts` with
  `fetchJournalEntries({page,
  pageSize})` (M14.1 endpoint) +
  `fetchJournalEntry(pk)` (M13.1
  endpoint) + full TypeScript types
  for `JournalEntry` +
  `JournalEntryLine` + list
  response shape.
- Create `AccountingJournalEntries
  Page.tsx` — paginated list
  (shadcn `<Table>` + pagination
  controls). Columns: posted_at +
  description + posted_by + total
  (using `total_debit` from M14.1
  list projection) + reversal-of-
  link (if `reverses_id`).
- Create `AccountingJournalEntry
  DetailPage.tsx` — header block +
  lines table + reversal-linkage
  panel + "Reverse this entry"
  placeholder button (dialog wires
  at M14.4).
- Register two new routes:
  `dealer-ai-accounting/journal-
  entries` + `journal-entries/:pk`.
- Vitest coverage target ~15
  tests. Frontend baseline 89 →
  ~104.

**Explicit non-goals at M14.3:**

- ❌ No backend work.
- ❌ No reversal dialog wiring
  (M14.4).
- ❌ No cost-posting failure card
  (M14.4).
- ❌ No `as_of` picker on trial-
  balance (deferred to M15+).

## Push authorization

Three local commits queued (M14.0
planning + M14.1 backend + M14.2
frontend trial-balance) pending
user authorization at SESSION_135
close.

## Anchors for SESSION_136

1. `docs/roadmap/MILESTONE_14_
   PLANNING.md` §7 M14.3
   (implementation spec).
2. `docs/handoffs/SESSION_135_m14_
   inc2_trial_balance_page.md`
   (this handoff).
3. `frontend/src/pages/Accounting
   TrialBalancePage.tsx` (page
   pattern to mirror for
   list + detail).
4. `frontend/src/lib/accountingApi
   .ts` (module to extend).
5. `backend/dealer_ai/views_
   accounting.py`
   `admin_journal_entry_list` +
   `_project_list_entry` +
   `admin_journal_entry_retrieve` +
   `_project_entry` (endpoint
   contracts + response shapes to
   consume).
6. `frontend/src/pages/DealerAi
   BhphPortfolio.tsx` (analog: list
   page with pagination-ish table
   consuming admin endpoints).
7. `frontend/src/pages/DealerAi
   BhphNoteDetail.tsx` (analog:
   detail page pattern).
