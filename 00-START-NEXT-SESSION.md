---
state: active
date: 2026-08-02
last_session_shipped: SESSION_136
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
next_session: SESSION_137
next_milestone: 14
next_milestone_name: "Operator UI for accounting substrate"
next_increment: 4
next_increment_name: "M14.4 — Frontend: reversal dialog + cost-posting failure card"
---

# Next session — SESSION_137 · Milestone 14 · Increment 4 (M14.4 — Frontend: reversal dialog + cost-posting failure card)

> **SESSION_136 shipped M14.3 —**
> frontend journal-entry browser +
> detail. Extended `accountingApi.ts`
> with list + detail types + two
> fetchers. New
> `AccountingJournalEntriesPage.tsx`
> (paginated list with reversal-
> linkage badges) +
> `AccountingJournalEntryDetailPage
> .tsx` (header card + lines table
> + Corrections card with disabled
> M14.4 placeholder button). Two
> new routes registered. 24 focused
> Vitest tests (13 list + 11
> detail). Consumes existing M14.1
> list + M13.1 retrieve endpoints.
> Zero backend work. Browser-
> verified (list + reversal detail
> + original detail + not-found
> states).
>
> **Backend baseline: 4,277 pass**
> (unchanged). **Frontend Vitest:
> 89 → 113 pass** (+24). Frontend
> operator routes: 18 → 20 (+2).
> DRF admin surface 104
> (unchanged). Tenancy carriers 47
> (unchanged). Permission classes
> 8 (unchanged). Celery-beat task
> families 9 (unchanged). Zero
> migrations. `tsc --noEmit` clean;
> `vite build` clean.
>
> **Eight M14.3 implementation-
> time micro-decisions recorded**
> in the handoff (Previous/Next
> buttons over numeric page links
> / fixed page_size 25 / reversal
> discriminated via reverses_id
> null-check / client-side line
> totals for display / zero-value
> cells rendered blank / not-found
> detection via error message
> regex / NaN pk short-circuits to
> not-found / Reverse-button
> placeholder disabled + labeled
> "(M14.4)"). All as-recommended
> per M10 §9 — do not count
> against streak.
>
> **Push authorization:** four
> local commits queued (M14.0
> planning + M14.1 backend + M14.2
> frontend trial-balance + M14.3
> frontend browser+detail) pending
> user authorization.
>
> **SESSION_137 opens M14.4 —
> reversal dialog + cost-posting
> failure card.** Wires the M14.3
> placeholder Reverse button to a
> shadcn `<Dialog>` (using the
> existing M13.1 reverse
> endpoint). Adds failure card to
> the M14.2 trial-balance page
> (using the M14.1 failures
> endpoint). No new routes. No
> backend work.

## First thing SESSION_137 must do

### 1. Verify starting state

- `git status` — clean (M14.3
  commit landed at SESSION_136
  close; user authorized push
  when ready).
- `git log --oneline -5` — top
  should be the M14.3 frontend
  commit.
- `python3 manage.py test dealer_ai`
  → **4,277 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **113 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_14_
  PLANNING.md` §7 Increment 4
  (implementation spec).
- `docs/handoffs/SESSION_136_m14_
  inc3_journal_browser.md`
  (previous session).
- `backend/dealer_ai/views_
  accounting.py`
  `admin_journal_entry_reverse` +
  `admin_cost_posting_failures`
  (endpoint contracts to consume).
- `frontend/src/lib/accountingApi
  .ts` (module to extend — do NOT
  rewrite existing fetchers).
- `frontend/src/pages/Accounting
  JournalEntryDetailPage.tsx`
  (Corrections card with disabled
  placeholder button is the
  wiring point).
- `frontend/src/pages/Accounting
  TrialBalancePage.tsx` (extend
  with failure card).
- `frontend/src/components/ui/
  dialog.tsx` +
  `frontend/src/components/ui/
  textarea.tsx` (shadcn
  primitives already installed).

## What M14.4 delivers

Per `MILESTONE_14_PLANNING.md` §7
M14.4:

### Extend accounting API client

1. **`frontend/src/lib/
   accountingApi.ts`** — add:
   - `reverseJournalEntry(pk,
     {reason, posted_at?})`
     calling `POST /admin/
     accounting/journal-entries/
     <pk>/reverse/` (M13.1
     endpoint). Returns the new
     reversal `JournalEntry`.
   - `fetchCostPostingFailures(
     {thresholdHours?})` calling
     `GET /admin/accounting/
     cost-posting-failures/`
     (M14.1 endpoint). Returns
     failures array + count +
     threshold_hours + as_of.
   - TypeScript type for
     `CostPostingFailure` (id +
     vehicle_id + vehicle_stock
     + category + category_
     display + amount + reference
     + vendor + incurred_at +
     created_at + age_in_hours).

### Reversal dialog (wire the M14.3 placeholder)

2. **`frontend/src/pages/
   AccountingJournalEntryDetail
   Page.tsx`** — replace the
   disabled placeholder button
   with a wired shadcn
   `<Dialog>`:
   - Trigger: enabled "Reverse
     this entry" button.
   - Dialog content:
     `<Textarea>` for reason
     (required, min length 1
     after trim, empty-blocked
     client-side matching M13.1
     `ImmutableJournalEntryError`
     409 per §5.e Option A belt+
     suspenders).
   - Optional `posted_at` text
     input (ISO string format;
     defer date picker).
   - Confirm button + Cancel
     button.
   - On success: re-fetch
     detail. Reversal linkage
     panel appears
     automatically (M14.3
     already renders it when
     `reverses_id !== null`).
   - Error handling: display
     backend error message
     inline in the dialog
     (400/404/409 all mapped
     to specific detail
     messages per M13.1 view).

### Cost-posting failure card

3. **`frontend/src/pages/
   AccountingTrialBalancePage
   .tsx`** — add card above or
   below the trial-balance
   card:
   - Fetches
     `fetchCostPostingFailures()`
     alongside the existing
     `fetchTrialBalance()` in
     `Promise.all`.
   - Card hidden entirely when
     `count === 0` (matches
     M14.2 empty-state hiding
     posture for the totals
     footer).
   - When `count > 0`: title
     "Cost-posting failures
     (N)", description
     referencing the M13.2
     detector, table with
     stock + category + amount
     + age_in_hours (or
     age_in_days derived).
   - Uses shadcn
     `<Card variant="outline">`
     or destructive-styled
     accent to signal
     operator attention.

### Vitest coverage (~10 new tests)

4. **Extend
   `AccountingJournalEntryDetail
   Page.test.tsx`** or new
   dialog-specific test file:
   - Reverse dialog opens when
     button clicked.
   - Empty reason disables
     confirm button.
   - Non-empty reason enables
     confirm.
   - Cancel closes dialog
     without POST.
   - Successful POST re-
     fetches detail.
   - Backend error displayed
     in dialog.
5. **Extend
   `AccountingTrialBalancePage
   .test.tsx`** or new:
   - Failure card hidden when
     count=0.
   - Failure card renders
     when count>0.
   - Failure rows show
     vehicle_stock + category
     + amount + age.

### Deltas at M14.4 close

- **Backend baseline:** 4,277
  (unchanged).
- **Frontend Vitest:** 113 →
  ~123 (+10 tests).
- **Frontend operator routes:**
  20 (unchanged — dialog is a
  modal, not a route).
- **DRF admin surface:** 104
  (unchanged).
- **Tenancy carriers:** 47.
- **Permission classes:** 8.
- **Migrations:** none.

## Explicit non-goals for SESSION_137

- ❌ Do NOT add backend
  endpoints (M14.1 shipped
  everything M14.4 needs).
- ❌ Do NOT add a date-picker
  widget to the reversal dialog
  — plain text input at MVP.
- ❌ Do NOT change the M13.2
  detector.
- ❌ Do NOT add `as_of` picker
  to trial-balance (still
  deferred to M15+).
- ❌ Do NOT add category-
  aware GL mapping (deferred
  per M13 retrospective §3
  item 1).
- ❌ Do NOT modify M1-M13
  business logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_137 with (a)
starting-state verification,
(b) the read-first list, then
(c) extending `accountingApi
.ts` with the reversal + failure
fetchers + wiring the M14.3
placeholder button to a shadcn
`<Dialog>` + adding the failure
card to the trial-balance page
+ Vitest per
`MILESTONE_14_PLANNING.md` §7
M14.4. Browser-verify reversal
end-to-end (open dialog → enter
reason → confirm → observe
reversal linkage appear on
detail page). Ship the M14.4
handoff at
`docs/handoffs/SESSION_137_m14_
inc4_reversal_and_failures.md`.

Backend baseline at SESSION_137
close: **4,277 pass** (unchanged).
Frontend baseline: **113 → ~123**
(+10 Vitest tests).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_14_PLANNING.md`
   §7 M14.4
6. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §6 (twelve lessons carry
   into M14)
7. `docs/handoffs/SESSION_136_m14_inc3_journal_browser.md`
   (previous session)
8. `docs/CAPABILITY_MATRIX.md` §7n

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_136 — M14.3 shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0044`. Test baseline:
  **4,277 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 113 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **9
  scheduled task families
  registered**. Next available
  slot: 11:00. No new families
  at M14.
- **Milestones shipped:** M1 →
  **M13**. **M14 in progress**
  (M14.0 planning + M14.1
  backend + M14.2 frontend
  trial-balance + M14.3
  frontend browser+detail
  shipped).
- **DRF admin surface:** **104**
  endpoints (unchanged since
  M14.1).
- **Frontend operator routes:**
  **20** (M14.3 added
  `dealer-ai-accounting/
  journal-entries` +
  `.../journal-entries/:pk`).
  Final projected count at
  M14 close = 20 (M14.4 adds
  no routes; dialog is a
  modal).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:**
  unchanged.
- **Frontend accounting
  surface:** `frontend/src/lib/
  accountingApi.ts` (three
  fetchers: trial balance +
  journal-entry list + journal-
  entry detail; reversal +
  failures land at M14.4).
  Three page components:
  `AccountingTrialBalancePage`
  + `AccountingJournalEntries
  Page` +
  `AccountingJournalEntryDetail
  Page`.
- **Tenancy carriers:** **47**
  (unchanged at M14).
- **Permission classes:** **8**
  (unchanged — zero drift
  extends to six consecutive
  milestones; M14.2 + M14.3
  have no backend surface so
  posture is preserved).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M14 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Accounting substrate:** four
  M13 modules in
  `services/accounting/` +
  M14.1 additions.
- **Milestone 14 next:** M14.4
  reversal dialog + cost-
  posting failure card per
  `MILESTONE_14_PLANNING.md` §7
  Increment 4. One code
  increment + one close-out
  remain after M14.4.
