---
title: "SESSION_137 handoff — Milestone 14 · Increment 4 (M14.4 — Frontend: reversal dialog + cost-posting failure card)"
status: historical
type: handoff
date: 2026-08-02
session: 137
milestone: 14
milestone_status: in-progress
milestone_name: "Operator UI for accounting substrate"
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_137 — Milestone 14 · Increment 4 (M14.4 — Frontend: reversal dialog + cost-posting failure card)

## What shipped

Final code increment of M14. Wired
the M14.3 placeholder Reverse button
to a shadcn `<Dialog>` + added the
cost-posting failure card to the
trial-balance page. Zero backend
work. Zero new routes.

### API client (extended)

1. **`frontend/src/lib/accountingApi
   .ts`** — added:
   - `reverseJournalEntry(pk,
     {reason, posted_at?})` calling
     `POST /admin/accounting/
     journal-entries/<pk>/reverse/`
     via `authPostJSON` (CSRF token
     attached automatically by
     `authFetch`). Returns the new
     reversal `JournalEntry`.
   - `ReverseJournalEntryPayload`
     type.
   - `CostPostingFailure` type (id +
     vehicle_id + vehicle_stock +
     category + category_display +
     amount + reference + vendor +
     incurred_at + created_at +
     age_in_hours).
   - `CostPostingFailuresResponse`
     type (failures[] + count +
     threshold_hours + as_of).
   - `fetchCostPostingFailures({
     thresholdHours?})` calling `GET
     /admin/accounting/cost-posting-
     failures/`.
   - Import of `authPostJSON`
     alongside `authGetJSON` at the
     top.

### Reversal dialog (wired into detail page)

2. **`frontend/src/pages/
   AccountingJournalEntryDetailPage
   .tsx`** — replaced the disabled
   placeholder button with a working
   `ReverseEntryDialog` subcomponent:
   - Trigger: enabled `<Button
     variant="outline" size="sm">
     Reverse this entry</Button>`.
   - Dialog content: shadcn `<Dialog>`
     with header (title "Reverse
     journal entry #N" + description
     referencing M13.1 §5.c Option
     A) + body (Reason `<Textarea>`
     with `aria-required` +
     `aria-invalid` on blank; optional
     `posted_at` text input) + footer
     (Cancel + Confirm reversal
     buttons).
   - Confirm button disabled when
     `reason.trim().length === 0` —
     matches M13.1 serializer 400
     (belt+suspenders per §5.e Option
     A).
   - Submitting state: Confirm shows
     "Posting…", Cancel disabled.
   - Success: closes dialog, resets
     form, triggers detail re-fetch
     via a `reloadTick` state + a
     new dependency on
     `useEffect([pk, reloadTick])`.
     Post-reload, the reversal
     linkage renders correctly on
     the newly-posted reversal entry
     (verified in browser).
   - Error: displays inline
     `<p role="alert">` with the
     backend error message; dialog
     stays open so operator can
     retry / edit / cancel.
   - onOpenChange handler resets the
     form when the dialog closes
     (matches the reset() pattern
     used in Cancel handler).

### Cost-posting failure card

3. **`frontend/src/pages/
   AccountingTrialBalancePage.tsx`**
   — added `CostPostingFailuresCard`
   subcomponent + wired into page
   render:
   - Now fetches trial balance +
     failures in `Promise.all` so
     both requests fire in parallel
     and the page renders in a
     single paint.
   - Card renders **only when
     `failures.length > 0`**
     (zero-noise posture — no "0
     failures" banner per §0.a M14.4
     decision 3).
   - Card styled with
     `border-destructive/40` +
     destructive-colored title +
     "Attention" badge for operator
     salience.
   - Table columns: Vehicle stock +
     Category + Amount + Age (hrs)
     + Reference. Right-aligned
     tabular-nums on numeric
     columns.
   - Description text names the
     M13.2 detector and its 10:00
     project-time cadence — grounds
     the operator's understanding
     of when the queue will drain.

### Vitest coverage (+9 tests, 113 → 122)

4. **Extended
   `AccountingJournalEntryDetailPage
   .test.tsx`** — replaced the
   "disabled placeholder" test with
   7 new dialog tests:
   - Enabled trigger button.
   - Dialog opens on trigger click
     (heading appears).
   - Confirm disabled when reason
     blank.
   - Confirm enabled once reason
     populated.
   - Successful POST → dialog
     closes + detail re-fetched
     (fetchJournalEntry called
     ≥2 times).
   - Backend error displayed inline
     via `role="alert"`; dialog
     stays open.
   - Cancel does not POST.
5. **Extended
   `AccountingTrialBalancePage
   .test.tsx`** — added
   `fetchCostPostingFailures` mock
   + 3 new failure-card tests:
   - Card hidden when count=0.
   - Card renders rows when count>0.
   - "Attention" badge present when
     count>0.

## Deltas at SESSION_137 close

- **Backend baseline:** 4,277
  (unchanged — frontend-only
  increment).
- **Frontend Vitest:** 113 → **122
  pass** (+9; target was ~10).
- **Frontend operator routes:** 20
  (unchanged — dialog is a modal,
  not a route).
- **DRF admin surface:** 104
  (unchanged).
- **Tenancy carriers:** 47
  (unchanged).
- **Permission classes:** 8
  (unchanged — every M14 endpoint
  path continues to reuse
  `IsSalesManagerOrOwnerAtActive
  Dealership`).
- **Celery-beat task families:** 9
  (unchanged — M14 has no
  detectors).
- **Migrations:** none.
- **`tsc --noEmit`:** clean.
- **`vite build`:** clean.

## Browser verification

Started dev servers, logged in as
`smoke_owner` (sales_manager
role). Seeded one target journal
entry (#6 — "M14.4 demo — reverse
me", $7,777.00 sale) + one
cost-posting failure (48h old
VehicleCost with reference
"M14.4-FAILURE").

**Trial-balance page failure
card:**
- Failure card renders at top
  above trial balance.
- Count in title (4 total —
  seeded 1 + 3 pre-existing test
  data).
- "Attention" destructive badge.
- Table shows vehicle_stock,
  category display, amount
  (formatted USD, including
  negative row rendering
  "-$50.00"), age_in_hours (48
  for the seed), and reference.

**Reversal dialog end-to-end
(entry #6):**
- Trigger button "Reverse this
  entry" enabled.
- Dialog opens with proper title
  "Reverse journal entry #6".
- Reason textarea shows
  `aria-invalid=true` when blank;
  Confirm button disabled.
- Typed reason "Wrong amount —
  operator entered $7,777 instead
  of $8,777"; Confirm enabled.
- Clicked Confirm → dialog
  closed cleanly, detail page
  re-fetched.
- Navigated to list: new entry
  #7 present with description
  "Reversal of #6: M14.4 demo —
  reverse me", posted_by
  "smoke_owner" (correctly
  captured from the request user
  by the M13.1 endpoint), amount
  $7,777.00, "Reversal of #6"
  badge.
- Original #6 continues to show
  "Original" badge in the list.

**Console:** 0 unexpected
errors, 0 warnings.

Seeded data cleaned up post-
verification (reversal deleted
before original per PROTECT FK
constraint; failure cost + demo
vehicle deleted).

## Implementation-time micro-decisions

Per M10 §9 — recorded but do NOT
count against the M14 planning-
time as-recommended streak (which
stands at 53 M5.1→M14.0).

1. **`reloadTick` counter drives
   detail re-fetch.** Simpler than
   invalidating a react-query
   cache (which the project doesn't
   use here) or manually calling
   the fetcher again. `useEffect([
   pk, reloadTick])` triggers on
   both the URL change AND the
   post-reversal reload.
2. **Dialog form resets on both
   Cancel click AND onOpenChange
   close.** A dialog can be
   dismissed via escape / overlay
   click / X button in addition to
   explicit Cancel; centralizing
   the reset in `onOpenChange`
   avoids state leaks between
   openings.
3. **Cost-posting failure card is
   hidden entirely at count=0.**
   Zero-noise posture — the trial-
   balance page should not carry
   an empty "no failures" banner
   as background chrome. Matches
   the M14.2 grand-totals footer
   posture (hidden when zero
   rows).
4. **Both fetchers fire in
   `Promise.all` on the trial-
   balance page.** Single-paint
   render posture. Failures
   endpoint failing would take
   down the whole page; acceptable
   trade at MVP because both
   endpoints share the same
   permission class + the same
   underlying accounting substrate
   readiness (if one is broken,
   the other is likely also
   broken).
5. **Reason validation uses
   `reason.trim().length === 0`.**
   Matches M13.1 serializer
   validation which strips
   whitespace via
   `serializers.CharField` +
   service-verb
   `(reason or "").strip()`
   check. Client-side trim keeps
   the belt+suspenders posture
   symmetric.
6. **`posted_at` accepts free-text
   ISO8601, not a date picker.**
   Matches the planning §7 M14.4
   scope ("defer date picker to
   future — text input at MVP").
   Blank input omitted from
   payload so the backend
   defaults to `timezone.now()`.
7. **Backend error rendered
   verbatim via `role="alert"`.**
   The M13.1 endpoint returns
   `{detail: "..."}` for 400/404/
   409; the ApiError message
   wraps that as "API request
   failed (400): ...". Displaying
   verbatim gives the operator
   the actual status +
   explanation rather than
   losing the specificity.
   Operator-facing polish
   (parsing the detail out) can
   layer later if evidence
   surfaces the need.
8. **Failure-card table uses
   `age_in_hours`, not derived
   days.** Simpler; the M14.1
   endpoint already ships the
   hours count. Age-in-days
   conversion adds arithmetic
   without gain for a value
   operators can eyeball
   directly (48 hrs = 2 days).
9. **flaky test converted to
   `findByText`.** The line-render
   test in
   AccountingJournalEntryDetail
   Page.test.tsx became flaky
   after M14.4 (extra state
   updates from the dialog
   subcomponent added a render
   microtask). `findByText`
   waits for the element to
   appear; `getByText` was
   racing with the re-render.

## Files touched

Modified:

1. `frontend/src/lib/accountingApi
   .ts` — added reversal +
   failures fetchers + types +
   `authPostJSON` import.
2. `frontend/src/pages/Accounting
   JournalEntryDetailPage.tsx` —
   replaced placeholder button
   with `<ReverseEntryDialog>`
   subcomponent + added
   `reloadTick` state + new
   dialog / textarea imports.
3. `frontend/src/pages/Accounting
   TrialBalancePage.tsx` — added
   `CostPostingFailuresCard`
   subcomponent + parallel
   `Promise.all` fetch + new
   failures import.
4. `frontend/src/pages/Accounting
   JournalEntryDetailPage.test
   .tsx` — added `reverseJournal
   Entry` mock + 7 new dialog
   tests; converted 1 flaky test
   to `findByText`.
5. `frontend/src/pages/Accounting
   TrialBalancePage.test.tsx` —
   added `fetchCostPostingFailures`
   mock + 3 new failure-card
   tests.

Created:

6. `docs/handoffs/SESSION_137_m14_
   inc4_reversal_and_failures.md`
   — this handoff.

## Verifications passed at SESSION_137 close

- `python3 manage.py test
  dealer_ai` → **4,277 pass, 1
  skipped, 0 fail** (unchanged
  — frontend-only increment).
- `npm test` → **122 pass** (was
  113; +9 Vitest tests).
- `npx tsc --noEmit` clean.
- `npx vite build` clean.
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- Browser E2E: reversal dialog
  → POST → new reversal entry
  appears in list with correct
  linkage. Failure card renders
  atop trial balance with real
  data. Zero unexpected console
  errors.

## What SESSION_138 (M14.5) picks up

Per `MILESTONE_14_PLANNING.md` §7
Increment 5 — close-out:

- `docs/roadmap/MILESTONE_14_
  RETROSPECTIVE.md` — new.
  Structure per M13.4 template.
- `docs/CAPABILITY_MATRIX.md`
  §7o — append the M14 shipped
  surface.
- `docs/roadmap/IMPLEMENTATION_
  ROADMAP.md` §Milestone 14 —
  flip planning → shipped.
- `docs/roadmap/MILESTONE_14_
  PLANNING.md` — frontmatter
  `status: active` → `status:
  shipped`.
- `00-START-NEXT-SESSION.md` —
  overwrite with M15.0 priority.
- `docs/roadmap/MILESTONE_15_
  PLANNING.md` — new skeleton
  per standing user directive.
- Coordinated commit landing
  all close-out docs.

**Explicit non-goals at
M14.5:**

- ❌ No code changes.
- ❌ No backend work.
- ❌ No new tests.

## Push authorization

Five local commits queued
(M14.0 planning + M14.1 backend
+ M14.2 trial-balance page +
M14.3 browser+detail + M14.4
reversal+failures) pending
user authorization at
SESSION_137 close.

## Anchors for SESSION_138

1. `docs/roadmap/MILESTONE_14_
   PLANNING.md` §7 M14.5
   (close-out spec).
2. `docs/roadmap/MILESTONE_13_
   RETROSPECTIVE.md` (template
   to mirror for the M14
   retrospective).
3. `docs/roadmap/MILESTONE_14_
   PLANNING.md` (source for the
   retrospective's "planned"
   sections).
4. `docs/handoffs/SESSION_133_
   m14_inc0_planning.md` +
   `SESSION_134_m14_inc1_list_
   and_failures.md` +
   `SESSION_135_m14_inc2_trial_
   balance_page.md` +
   `SESSION_136_m14_inc3_journal_
   browser.md` + this handoff
   (source for "what shipped" /
   "deviations" content).
5. `docs/CAPABILITY_MATRIX.md`
   §7n (the M13 append point;
   §7o mirrors that structure).
6. `docs/roadmap/IMPLEMENTATION_
   ROADMAP.md` §Milestone 14
   (planning-status entry to
   flip).
