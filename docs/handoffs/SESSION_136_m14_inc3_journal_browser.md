---
title: "SESSION_136 handoff — Milestone 14 · Increment 3 (M14.3 — Frontend: journal-entry browser + detail)"
status: historical
type: handoff
date: 2026-08-02
session: 136
milestone: 14
milestone_status: in-progress
milestone_name: "Operator UI for accounting substrate"
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_136 — Milestone 14 · Increment 3 (M14.3 — Frontend: journal-entry browser + detail)

## What shipped

Two new frontend pages + two new
routes + extended API client. Zero
backend work. Consumes the M14.1
list endpoint + the M13.1 retrieve
endpoint.

### API client (extended)

1. **`frontend/src/lib/
   accountingApi.ts`** — added:
   - `JournalEntryListEntry` type
     (list projection: id +
     description + posted_at +
     posted_by_user_id +
     posted_by_username +
     reverses_id + reason +
     total_debit).
   - `JournalEntryListPage` type
     (entries[] + total_count +
     page + page_size).
   - `JournalEntryLine` type (id +
     account_id + account_code +
     debit + credit + memo).
   - `JournalEntry` type (detail
     projection: id + dealership_id
     + description + posted_at +
     posted_by_user_id +
     reverses_id + reason +
     created_at + lines[]).
   - `fetchJournalEntries({page,
     pageSize})` calling `GET
     /admin/accounting/journal-
     entries/list/` with
     URLSearchParams building.
   - `fetchJournalEntry(pk)`
     calling `GET /admin/
     accounting/journal-entries/
     <pk>/`.
   - Decimal-as-string preserved
     on `total_debit` + `debit` +
     `credit`.

### List page (new file)

2. **`frontend/src/pages/
   AccountingJournalEntriesPage
   .tsx`** — paginated browser:
   - Header block (h1 +
     description).
   - Card with title "N entries"
     + description "Page X of Y".
   - Table columns: ID + Posted
     + Description + Posted by +
     Total (debits) + Kind +
     Detail.
   - Kind column: shadcn `<Badge
     variant="destructive">
     Reversal of #X</Badge>` for
     reversals, `<Badge
     variant="outline">Original
     </Badge>` for originals.
   - Detail column: React Router
     `<Link>` to
     `/dealer-ai-accounting/
     journal-entries/<id>`.
   - Empty-state message
     referencing the M13.2
     detector.
   - Footer with "Showing X–Y of
     N" range + Previous/Next
     buttons. Both disabled at
     boundaries (page=1 → prev
     off; page=totalPages →
     next off).
   - Loading + error states via
     the M11/M12 useEffect +
     cancellation-flag pattern.
   - useState `page` triggers
     re-fetch via useEffect
     dependency.
   - Default `pageSize=25`
     matches M14.1 backend
     default.

### Detail page (new file)

3. **`frontend/src/pages/
   AccountingJournalEntryDetail
   Page.tsx`**:
   - useParams reads `:pk` from
     URL; `NaN` → immediate
     not-found state without
     API call.
   - Header block: back link
     "← Back to journal entries"
     + h1 "Journal Entry #N".
   - **Header card**: title =
     description, description =
     "Posted <formatted
     timestamp>", trailing
     Badge (destructive
     "Reversal of #X" OR outline
     "Original entry"). Meta
     rows: Entry ID, Posted by
     user, Row created,
     Reversal reason (rendered
     ONLY when
     `reverses_id !== null`).
   - **Lines card**: table with
     account_code + debit +
     credit + memo columns.
     Zero-value cell rendered
     blank (not "$0.00") so the
     debit-or-credit posture is
     visually obvious. Total
     debits + credits computed
     client-side and shown in
     the card description.
   - **Corrections card**:
     disabled `<Button>
     Reverse this entry (M14.4)
     </Button>` with a
     description referencing
     M13.1 §5.c Option A
     immutability + naming the
     M14.4 dialog as the
     landing point.
   - Not-found state:
     lightweight paragraph
     "Journal entry not found."
     Triggered by API error
     matching /not found/i or
     /404/.
   - Generic error state for
     other failures.

### Routes (2 new)

4. **`frontend/src/main.tsx`** —
   registered:
   - `dealer-ai-accounting/
     journal-entries` →
     `AccountingJournalEntries
     Page`.
   - `dealer-ai-accounting/
     journal-entries/:pk` →
     `AccountingJournalEntry
     DetailPage`.
   Both nested under
   `RequireAuth` alongside the
   M14.2 trial-balance route.

### Vitest coverage (2 new files, 24 tests)

5. **`AccountingJournalEntriesPage
   .test.tsx`** — 13 tests: h1
   header via role query, row
   rendering with formatted
   totals, count + page
   metadata, username display,
   null username → em-dash,
   reversal badge, original
   badge, empty-state message,
   View link href points at
   detail, Next click advances
   page + refetches, Previous
   disabled on page 1, Next
   disabled when total=page,
   error state on fetch
   rejection.
6. **`AccountingJournalEntry
   DetailPage.test.tsx`** — 11
   tests: h1 with entry ID,
   description in header card,
   line rows with formatted
   debits/credits, "Original
   entry" badge, reversal
   badge + reason for reversal
   entries, back link href,
   disabled Reverse button
   present, posted_by_user_id
   render, em-dash for null
   posted_by_user_id,
   not-found state on 404-ish
   errors, generic error state
   for other failures.

## Deltas at SESSION_136 close

- **Backend baseline:** 4,277
  (unchanged — frontend-only
  increment).
- **Frontend Vitest:** 89 →
  **113 pass** (+24 tests;
  target was ~15, overshoot
  came from thorough pagination
  + reversal-linkage coverage
  that would otherwise regress
  silently).
- **Frontend operator routes:**
  18 → **20** (+2:
  `journal-entries` +
  `journal-entries/:pk`).
- **DRF admin surface:** 104
  (unchanged).
- **Tenancy carriers:** 47
  (unchanged).
- **Permission classes:** 8
  (unchanged).
- **Migrations:** none.
- **`tsc --noEmit`:** clean.
- **`vite build`:** clean
  (~2.0s, ~1.1MB bundle /
  ~304kB gzip — pre-existing
  chunk-size warning unchanged).

## Browser verification

Started dev servers (Django on
8001, Vite on 5173) as
`smoke_owner` (sales_manager
role). Seeded three demo
journal entries (two originals
+ one reversal of one of the
originals via
`services.accounting.reverse_
journal_entry`). Verified in
browser:

- **List page (`/dealer-ai-
  accounting/journal-entries`):**
  - "3 entries · Page 1 of 1"
    header.
  - Rows rendered recent-first
    (#5 reversal, #4 original,
    #3 original — matches the
    `-posted_at, -id` backend
    ordering).
  - Reversal row shows
    "Reversal of #3" badge
    (destructive variant); its
    description reads
    "Reversal of #3: M14.3
    demo sale" (matches the
    M13.1
    `reverse_journal_entry`
    description shape).
  - Originals show "Original"
    outline badge.
  - Currency formatted
    ($9,500.00, $325.00).
  - "Showing 1–3 of 3" +
    both pagination buttons
    disabled (single-page
    result).
  - View links point at the
    correct detail route.
- **Detail page — reversal
  (#5):**
  - h1 "Journal Entry #5".
  - Back link works.
  - Header card: description
    "Reversal of #3: M14.3
    demo sale", "Reversal of
    #3" badge, "Reversal
    reason" meta row shows
    the operator's stated
    reason ("Operator mispost
    — reversed for M14.3
    demo").
  - Lines table: correct
    debit/credit swap (100000
    credit $9,500.00, 400000
    debit $9,500.00 — the
    reversal inverts the
    original's sides). Memos
    prefixed "Reversal:".
  - Corrections card:
    disabled "Reverse this
    entry (M14.4)" button
    with M14.4 hint text.
- **Detail page — original
  (#3):**
  - "Original entry" badge
    (outline variant).
  - No "Reversal reason" meta
    row (correctly hidden for
    originals).
  - Lines table with correct
    original debit/credit
    orientation.
- **Not-found state
  (`.../journal-entries/
  99999`):**
  - "Journal entry not found."
    paragraph rendered.
  - Two 404s in console
    (React StrictMode double-
    invokes effects in dev —
    expected).
- **Console:** 0 unexpected
  errors, 0 warnings on
  populated pages.

Seeded demo entries + the
reversal cleaned up
post-verification (reversal
deleted before originals to
respect the M13.1
`reverses`
`on_delete=PROTECT`
constraint).

## Implementation-time micro-decisions

Per M10 §9 — recorded but do
NOT count against the M14
planning-time as-recommended
streak (which stands at 53
M5.1→M14.0).

1. **Pagination controls are
   Previous/Next buttons, not
   numeric page links.** Simpler
   MVP; matches "small complete
   increments" (Rule 4). Numeric
   page links can layer if the
   operator needs to jump to
   specific pages once the
   catalog grows large enough
   to matter.
2. **`page_size` fixed at 25
   client-side.** The backend
   accepts up to 100 but MVP
   ships with a single sensible
   default. Operator-controlled
   page-size selector defers
   until evidence names the
   need.
3. **Reversal detection via
   `reverses_id !== null`.** No
   status/type enum on the
   backend — the presence of
   `reverses_id` is the only
   signal. Both list + detail
   pages use the same
   discriminant.
4. **Detail page computes
   line totals client-side.**
   Backend returns per-line
   `debit`/`credit` strings; a
   Number-based sum in the
   description text is
   sufficient for display. The
   authoritative sum lives in
   the trial balance
   aggregator (M13.3) — this
   client sum is display-only.
5. **Zero-value line cells
   rendered blank, not
   "$0.00".** Debit-or-credit
   posture is clearer when
   only the non-zero side has
   a value. Matches accounting
   convention (ledger paper
   never shows $0.00 zeros).
6. **Not-found detection via
   error message regex** (`/not
   found/i` or `/404/`).
   `authFetch` throws typed
   errors but doesn't currently
   expose the HTTP status code
   directly; matching on the
   message keeps the fix
   localized without changing
   the shared helper. A future
   `authFetch` improvement
   could expose `.status` on
   thrown errors and swap this
   for an exact check.
7. **`NaN` pk (bad URL param)
   short-circuits to not-found
   without an API call.**
   Defensive — prevents the
   backend from receiving
   garbage requests when an
   operator manually mangles
   the URL bar.
8. **Reverse-button placeholder
   is disabled + labeled
   "Reverse this entry
   (M14.4)".** Explicit forward
   reference tells operators
   the feature is coming
   without hiding it entirely.
   The Corrections card
   description names the exact
   milestone increment.

## Files touched

Created:

1. `frontend/src/pages/
   AccountingJournalEntriesPage
   .tsx` — 195 lines.
2. `frontend/src/pages/
   AccountingJournalEntryDetail
   Page.tsx` — 235 lines.
3. `frontend/src/pages/
   AccountingJournalEntriesPage
   .test.tsx` — 200 lines.
4. `frontend/src/pages/
   AccountingJournalEntryDetail
   Page.test.tsx` — 190 lines.
5. `docs/handoffs/SESSION_136_
   m14_inc3_journal_browser.md`
   — this handoff.

Modified:

6. `frontend/src/lib/
   accountingApi.ts` — added
   list + detail types +
   fetchers.
7. `frontend/src/main.tsx` —
   two new imports + two new
   route registrations with
   comment block.

## Verifications passed at SESSION_136 close

- `python3 manage.py test
  dealer_ai` → **4,277 pass, 1
  skipped, 0 fail** (unchanged
  — frontend-only increment).
- `npm test` → **113 pass**
  (was 89; +24 Vitest tests).
- `npx tsc --noEmit` clean.
- `npx vite build` clean.
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- Browser verification passed
  (list + reversal detail +
  original detail + not-found
  all render correctly).

## What SESSION_137 (M14.4) picks up

Per `MILESTONE_14_PLANNING.md`
§7 Increment 4:

- Extend `frontend/src/lib/
  accountingApi.ts` with:
  - `reverseJournalEntry(pk,
    {reason, posted_at?})`
    calling `POST /admin/
    accounting/journal-
    entries/<pk>/reverse/`
    (M13.1 endpoint).
  - `fetchCostPostingFailures(
    {thresholdHours?})`
    calling `GET /admin/
    accounting/cost-posting-
    failures/` (M14.1
    endpoint).
- Wire the M14.3 "Reverse this
  entry (M14.4)" placeholder
  button to a shadcn `<Dialog>`:
  - `<Textarea>` for reason
    (required, empty-blocked
    client-side matching M13.1
    serializer 400 per §5.e
    Option A belt+suspenders).
  - Optional `posted_at` text
    input (defer date picker
    to future).
  - Confirm + Cancel buttons.
  - On success: re-fetch
    detail → reversal linkage
    panel appears (the M14.3
    detail page already
    renders this correctly
    when `reverses_id` is
    populated — see verified
    reversal #5 browser
    behavior).
- Add cost-posting failure
  card to the trial-balance
  page:
  - Displays count + top-N
    unposted VehicleCost rows.
  - Fields per row: vehicle
    stock + category + amount
    + age_in_days (derived
    from `age_in_hours`).
  - Card hidden entirely
    when `count=0`.
- Vitest coverage: ~10 new
  tests. Frontend baseline
  113 → ~123.

**Explicit non-goals at
M14.4:**

- ❌ No backend work.
- ❌ No cost-category-aware
  GL mapping (deferred per
  M13 retrospective §3 item
  1).
- ❌ No `as_of` picker on
  trial-balance (still
  deferred to M15+).
- ❌ No date-picker widget
  on reversal dialog — text
  input at MVP.

## Push authorization

Four local commits queued
(M14.0 planning + M14.1
backend + M14.2 frontend
trial-balance + M14.3 frontend
browser+detail) pending user
authorization at SESSION_136
close.

## Anchors for SESSION_137

1. `docs/roadmap/MILESTONE_14_
   PLANNING.md` §7 M14.4
   (implementation spec).
2. `docs/handoffs/SESSION_136_
   m14_inc3_journal_browser.md`
   (this handoff).
3. `frontend/src/pages/
   AccountingJournalEntryDetail
   Page.tsx` (the placeholder
   button + Corrections card
   that M14.4 wires).
4. `frontend/src/pages/
   AccountingTrialBalancePage
   .tsx` (page to extend with
   cost-posting failure card).
5. `frontend/src/lib/
   accountingApi.ts` (module to
   extend with reversal +
   failures fetchers).
6. `frontend/src/components/
   ui/dialog.tsx` +
   `textarea.tsx` (shadcn
   primitives to consume).
7. `backend/dealer_ai/views_
   accounting.py`
   `admin_journal_entry_reverse`
   + `admin_cost_posting_
   failures` (endpoint
   contracts to consume).
