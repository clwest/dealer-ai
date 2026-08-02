---
title: "Milestone 14 — Operator UI for accounting substrate"
status: active
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_132 (skeleton) → SESSION_133 (expansion)
milestone: 14
milestone_name: "Operator UI for accounting substrate"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_13_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_13_PLANNING.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
---

# Milestone 14 — Operator UI for accounting substrate

> **Planning memo — active.** Drafted as
> skeleton at M13.4 close per standing user
> directive (M10.8 / M11.7 / M12.8 / M13.4
> precedent). **Expanded at SESSION_133
> M14.0 open** once §5.a target selection
> confirmed **Option D — Operator UI for the
> M13 accounting substrate**. All six §5
> load-bearing decisions confirmed as-
> recommended at session open.
>
> M13 shipped the accounting reconciliation
> core (GL substrate + M2 cost detector +
> trial-balance aggregator) backend-only per
> M13 §5.f Option C. M14 layers the operator
> UI over that substrate: journal-entry
> browser + trial-balance render + reversal-
> with-reason dialog + cost-posting failure
> surfacing. Two new backend endpoints
> support the browser + failure surface;
> the M13.1 + M13.3 endpoints already ship
> the underlying data contract.

## 0. Engineering practices to preserve from M2-M13

Same posture as M13.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend. UI
  work at M14 is pure projection over
  the M13.1 + M13.3 admin endpoints
  plus two new query endpoints at
  M14.1 (list + failures).
- **Service ownership.** One authoritative
  write path per operation. M14 adds
  no new write verbs — reversal
  continues to route through the M13.1
  `reverse_journal_entry` service verb
  via the existing `POST admin/
  accounting/journal-entries/<pk>/
  reverse/` endpoint.
- **Tenancy discipline.** Every read
  path passes `dealership=` explicitly
  via `get_current_dealership(request)`
  per the M9-M13 endpoint pattern.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M13 convention
  (404 cross-tenant, 409 state-machine
  / duplicate, 400 vocab / validation).
  New M14.1 endpoints are read-only —
  404 for missing / cross-tenant is
  the primary status boundary.
- **Load-bearing decisions get user
  review BEFORE code.** All six §5
  decisions surfaced with
  recommendation + trade-offs at
  SESSION_133 open; user confirmed;
  recorded in §0.a per M5-M13
  precedent.
- **Additive extension over fork.**
  M14.1 endpoints are new URL entries
  in the same `urls.py`, new view
  functions in `views_accounting.py`.
  No changes to existing endpoint
  shapes.
- **Every M14 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9-M13
  growth-only-list lesson. Vocab-set
  assertions use exact equality per
  M11 / M12 / M13 fixed-vocab lesson.
- **Read-only surfacer vs state-
  transitioning detector** — M14 is
  entirely read-only (list + query +
  render). No Celery-beat task
  families added.
- **Atomic sibling-service boundary
  crossings** — not applicable at M14
  (no new write paths).
- **Denormalize at write; recompute in
  detectors.** M14.1 failure endpoint
  is a pure query over `VehicleCost`
  (`posted_at__isnull=True AND
  is_estimate=False AND created_at
  <= now - 24h`) — recompute posture
  matches M13.3.
- **Split pure verbs from write
  verbs.** M14.1 adds two pure query
  verbs (`list_journal_entries` +
  `detect_cost_posting_failures`)
  matching M12 / M13 posture.
- **Zero-drift permission-class
  posture.** Every M14 endpoint
  reuses
  `IsSalesManagerOrOwnerAtActiveDealership`
  per the streak-preservation lesson
  from M13 §6 lesson 12. Zero drift
  through a sixth consecutive
  milestone (M10 + M11 + M12 + M13 +
  M14).
- **Frozen dataclass output for
  aggregators.** Not applicable at
  M14 (no new aggregators — reuses
  M13.3 `TrialBalanceSnapshot`).
- **Zero-portfolio semantics as first-
  class response state.** M14.1 list
  endpoint returns an empty-array
  response for tenants with no
  postings (not 404). Cost-posting
  failure endpoint returns an empty
  array when zero VehicleCosts meet
  the age threshold (not 404).
- **Money on the wire is Decimal-as-
  string** per M9.5 / M10.1 / M12
  BHPH / M13.1 + M13.3 convention.
  Frontend renders with locale-
  appropriate formatting; backend
  never emits floats. Confirmed at
  §5.c.
- **Frontend Vitest discipline.**
  Every new page adds Vitest
  coverage matching M11 / M12
  precedent. Reversal-dialog
  coverage includes empty-reason
  client validation + success re-
  load paths.

### 0.a Change log — resolved decisions

**SESSION_133 M14.0 open (2026-08-02) —
six planning-time decisions confirmed:**

1. **§5.a Option A confirmed.** M14
   scope = all four M13-retrospective
   §3 item 4 UI surfaces: journal-entry
   browser + trial-balance render +
   reversal-with-reason dialog + cost-
   posting failure surfacing. Rationale
   drafted in §5.a below.
2. **§5.b Option B confirmed.** M14.1
   ships a filter-less journal-entry
   list endpoint (page + ordering
   only); filters land at M15+ per
   operator evidence. Matches M12.7
   per-metric-endpoint precedent.
3. **§5.c Option A confirmed.**
   Decimal-as-string on the wire
   preserved — already shipped in
   `views_accounting.py:94-96,269-271`
   at M13. Zero deviation cost.
4. **§5.d Option A confirmed.** New
   top-level route group
   `dealer-ai-accounting/*`. Three
   new routes at M14.2 + M14.3
   (trial-balance + journal-entries
   list + journal-entries detail).
   Matches M12 BHPH `dealer-ai-bhph/*`
   grouping precedent.
5. **§5.e Option A confirmed.**
   Reversal is a shadcn `<Dialog>` on
   the journal-entry detail page.
   Reason textarea required, empty-
   reason blocked client-side matching
   M13.1 serializer 400 (belt +
   suspenders per M13 §6 lesson 9).
6. **§5.f Option A confirmed.**
   Vitest coverage for every new
   page. Frontend baseline 78 →
   projected ~113 at M14 close
   (+35 across M14.2 + M14.3 +
   M14.4).

Streak update at M14.0 open: **53
planning-time as-recommended M5.1 →
M14.0** (47 M5.1→M13.0 + 6 M14.0).
Five consecutive milestones now (M10
+ M11 + M12 + M13 + M14).

## 1. Business questions this milestone answers

Per `ACCOUNTING_DEPARTMENT_MAPPING.md`
and the M13.4 retrospective §3 item 4
gap list, M14 answers four operator
workflow questions the M13 substrate
made possible but did not yet surface:

| # | Operator question | M14 answer surface | Backend anchor |
|---|---|---|---|
| Q1 | "What did the M13.2 detector post overnight?" | Journal-entry browser page — list view, most recent first. | New M14.1 list endpoint + existing M13.1 retrieve. |
| Q2 | "Where does the ledger stand right now?" | Trial-balance render page — per-account totals + grand totals + balanced-flag chip. | Existing M13.3 `compute_trial_balance` endpoint. |
| Q3 | "How do I fix a mis-posted entry?" | Reversal dialog on the detail page — reason textarea, optional posted_at, atomic reversal linking back to the original. | Existing M13.1 `reverse_journal_entry` endpoint. |
| Q4 | "Are any recon costs stuck un-posted?" | Cost-posting failure card on the trial-balance page — count + list of `VehicleCost` rows the M13.2 detector couldn't post. | New M14.1 failures endpoint. |

Five accounting-adjacent questions
from the M13 planning §1 nine-question
list remain **explicitly out of scope**
for M14 (see §3):

- Q3 chasing funding, Q5 chasing
  titles, Q6 floor-plan reconciliation
  vs lender statements, Q7 unapplied
  cash, Q9 monthly close +
  P&L / balance sheet derivatives.

These require additional backend
substrate that M13 did not ship;
Option D §5.a scope is deliberately
UI-only over the substrate M13
already delivered.

## 2. What existing primitives extend

**Backend (M13 substrate — no changes):**

- `services.accounting.get_journal_entry`
  (M13.1) — the browser detail page
  reads via the existing
  `GET admin/accounting/journal-entries/
  <pk>/` endpoint. No changes.
- `services.accounting.reverse_journal_entry`
  (M13.1) — the reversal dialog
  routes through the existing
  `POST admin/accounting/journal-entries/
  <pk>/reverse/` endpoint. No changes
  to the service verb or endpoint.
- `services.accounting.compute_trial_balance`
  (M13.3) — the render page reads
  via the existing `GET admin/
  accounting/trial-balance/` endpoint.
  No changes.
- `JournalEntry` + `JournalEntryLine`
  (M13.1) — read-only projection at
  M14.1 list endpoint. No model
  changes.
- `VehicleCost.posted_at` (M13.2
  additive column) — read-only
  projection at M14.1 failures
  endpoint. No model changes.

**Backend (M14.1 new — additive):**

- New pure query verb
  `list_journal_entries(dealership,
  page=1, page_size=25)` in
  `services/accounting/journal.py`.
- New pure query verb
  `detect_cost_posting_failures(
  dealership, now=None, threshold_
  hours=24)` in
  `services/accounting/vehicle_cost.py`.
- Two new DRF admin endpoints in
  `views_accounting.py`:
  `GET admin/accounting/journal-
  entries/list/` +
  `GET admin/accounting/cost-posting-
  failures/`.
- Both reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  (permission class count stays at 8).

**Frontend (new — additive):**

- New `frontend/src/lib/accountingApi.ts`
  API client module. Follows the M12
  `bhphApi.ts` pattern for module
  organization + Decimal-as-string
  handling.
- New route group `dealer-ai-
  accounting/*` under the operator
  layout in `main.tsx`.
- Three new page components:
  `AccountingTrialBalancePage.tsx` +
  `AccountingJournalEntriesPage.tsx` +
  `AccountingJournalEntryDetailPage.tsx`.
- shadcn primitives already installed:
  `<Card>` + `<Table>` + `<Dialog>` +
  `<Button>` + `<Badge>` +
  `<Textarea>`. No new shadcn
  primitives required.

## 3. What's NOT in this milestone (deferrals)

**Deferred to future milestones** (M15+
or beyond):

1. **Journal-entry list filters** (date
   range, posted_by, reversal-only,
   description search). M14.1 ships
   filter-less list per §5.b Option B.
   Filter surface layers at M15+ when
   operator evidence names specific
   filter needs. `TrialBalanceSnapshot`
   entity is not deferred here — see
   deferral 4 below.
2. **`as_of` picker on trial-balance
   page.** M14.2 ships trial-balance
   render at `now()` only. Operator
   date-picker for historical
   snapshots defers to M15+ (belongs
   with monthly-close workflow slice).
3. **Journal-entry manual create UI.**
   The M13.1 `POST admin/accounting/
   journal-entries/` endpoint ships,
   but manual UI for adjusting entries
   defers to M15+ (belongs with
   period-close workflow — accountants
   post adjusting entries at month
   end, not ad-hoc).
4. **`TrialBalanceSnapshot`
   materialization + monthly close
   workflow.** Deferred per M13
   retrospective §3 item 2. M13.3
   pure recompute serves M14 render
   needs; snapshot materialization is
   an M15+ workflow slice.
5. **Period-comparison verbs** (delta
   between two `as_of` snapshots).
   Defers with the M15+ close
   workflow.
6. **CSV / spreadsheet export** for
   trial-balance and journal-entry
   list. JSON payload + rendered
   table only at M14. Export defers
   per M12.7 precedent.
7. **Category-group-aware GL
   mapping** for the M13.2 detector.
   M13 retrospective §3 item 1.
   Deferred pending operator
   evidence of miscoding pain.
8. **Per-dealer COA overrides UI.**
   M13 retrospective §3 item 3.
   Deferred pending operator
   evidence.
9. **`post_save` signal auto-
   seeding COA for new dealerships.**
   M13 retrospective §3 item 5.
   Deferred pending onboarding-
   surface trigger point definition.
10. **M9 sale-booking GL post** (Q1
    of M13 retrospective §8). This
    is a substrate-consuming write-
    path milestone, not a UI
    milestone. Layers at M15+ per
    §5.d Option C hybrid trigger
    posture named in M13.
11. **M10 F&I chargeback GL
    reversal** (Q2 of M13
    retrospective §8). Deferred
    with M15+ write-path work.
12. **M12 BHPH payment GL post** (Q3
    of M13 retrospective §8).
    Deferred with M15+ write-path
    work.

**Universal / cross-milestone
deferrals** (regardless of target):

13. **Payroll** (external service).
14. **W-2 / 1099 generation**
    (external service).
15. **Year-end tax return
    preparation** (external CPA).
16. **GAAP-compliant audited
    financial reporting** (out of
    scope for platform v1).
17. **Direct DMS integration**
    (belongs to a future vendor-
    integration milestone).

## 4. Load-bearing decisions to resolve

Six decisions surfaced at SESSION_133
M14.0 open. All six confirmed as-
recommended — recorded in §0.a change
log above. Full recommendations +
rationale preserved below for future
readers.

### 5.a `[RESOLVED-AT-M14.0]` — Milestone scope

**Question.** Which of the M13
retrospective §3 item 4 UI surfaces
ship in M14?

- **Option A** — All four surfaces
  (journal-entry browser + trial-
  balance render + reversal-with-
  reason dialog + cost-posting
  failure surfacing). Full M14
  milestone.
- **Option B** — Trial-balance
  render + journal-entry browser
  only. Reversal + cost-posting
  failure defer to M15+.
- **Option C** — Trial-balance
  render only (single page, no
  drilldown).

**Recommendation drafted → confirmed
Option A.** Rationale: (1) UI-only
milestones want breadth over depth —
half a substrate operator surface is
worse than none; (2) reversal +
browser share the same detail page
(browser row → detail → reverse
button), so the marginal cost of the
dialog is small; (3) cost-posting
failure surfacing is a small addition
once the browser exists (both consume
the M14.1 endpoint family). Full
substrate becomes operator-usable in
one milestone.

### 5.b `[RESOLVED-AT-M14.0]` — Journal-entry list endpoint shape

**Question.** The browser needs a list
endpoint; no list endpoint exists at
M13 close (M13.1 shipped
create + reverse + retrieve-by-pk
only).

- **Option A** — Add `GET admin/
  accounting/journal-entries/list/`
  with `?page=` + `?from=`/`?to=`/
  `?posted_by=`/`?reverses_id__isnull=`
  filters, paginated. Full filter
  surface at M14.1.
- **Option B** — Add the list endpoint
  without filters (page + ordering
  only); filters land per-evidence at
  M15+.
- **Option C** — No list endpoint;
  browser hits trial-balance rows +
  drills to per-entry retrieve. No
  M14.1 backend work.

**Recommendation drafted → confirmed
Option B.** Rationale: (1) M12.7
precedent — ship the endpoint minimal,
add filters when operator evidence
names them; (2) avoids the M13 §6
lesson 2 trap of adding unproven
surface; (3) Option C is a non-starter
because trial balance is aggregate
and cannot surface unposted-recent-
first ordering an operator needs
during the daily "what did the
detector do overnight" review.

### 5.c `[RESOLVED-AT-M14.0]` — Money-on-the-wire format

**Question.** How does money render on
the wire for M14 endpoints?

- **Option A** — Decimal-as-string
  (matches M9.5 / M10.1 / M12 BHPH /
  M13.1 + M13.3 convention already in
  place).
- **Option B** — Number on the wire;
  format frontend-side.

**Recommendation drafted → confirmed
Option A.** Rationale: **already
shipped** at `views_accounting.py:94-
96, 269-271`. Preserving the
convention is zero-cost; deviating
breaks the M9→M13 pattern. New M14.1
endpoints match the existing
projection helpers.

### 5.d `[RESOLVED-AT-M14.0]` — Route + navigation placement

**Question.** Where do the three new
frontend routes live?

- **Option A** — Top-level route group
  `dealer-ai-accounting/*` (three
  routes: `trial-balance` +
  `journal-entries` +
  `journal-entries/:pk`). New
  "Accounting" nav group.
- **Option B** — Nest under existing
  "Admin" group (`dealer-ai-admin/
  accounting/...`).
- **Option C** — Under analytics
  (`dealer-ai-analytics/accounting`).

**Recommendation drafted → confirmed
Option A.** Rationale: (1) accounting
is a first-class operator domain
(research anchor
`ACCOUNTING_DEPARTMENT_MAPPING.md`);
(2) matches M12 BHPH pattern
(`dealer-ai-bhph/*` is its own group);
(3) trial-balance + journal-entry
browser grow into period comparison +
adjusting entries + close workflow at
M15+ — a dedicated group scales.

### 5.e `[RESOLVED-AT-M14.0]` — Reversal UX

**Question.** How does the reversal
UX surface on the detail page?

- **Option A** — Reversal is a shadcn
  `<Dialog>` on the detail page:
  reason textarea (required, non-
  blank enforced client-side matching
  M13.1 serializer 400), optional
  `posted_at`, confirm button.
  Success re-loads the detail view
  showing the reversal linkage.
- **Option B** — Reversal is a
  separate route (`journal-entries/
  <pk>/reverse`) with a full form
  page.
- **Option C** — Reversal is inline
  on the detail page (no dialog, no
  confirmation gesture).

**Recommendation drafted → confirmed
Option A.** Rationale: (1) reversal
is a low-frequency destructive-
adjacent action — a dialog forces a
deliberate confirmation gesture; (2)
matches shadcn `<Dialog>` primitive
already installed; (3) full route
(B) is heavier without payoff;
inline (C) risks accidental
reversals.

### 5.f `[RESOLVED-AT-M14.0]` — Test coverage posture

**Question.** What Vitest coverage
ships with M14 frontend increments?

- **Option A** — Vitest tests for
  every new page (trial-balance
  render, browser list, detail,
  reversal dialog). Match M11 / M12
  frontend-test discipline.
- **Option B** — Vitest for browser +
  detail only; trial-balance is
  read-only render, skip.
- **Option C** — No new Vitest tests;
  rely on manual QA + backend tests.

**Recommendation drafted → confirmed
Option A.** Rationale: (1) frontend
Vitest baseline is 78 pass today —
every M11 / M12 frontend increment
added tests; (2) reversal dialog
especially warrants test coverage
(empty-reason client validation,
success re-load, dialog close on
cancel); (3) skipping tests here
would be the first regression of
frontend-test discipline since it
started at M11.

## 5. Sequencing draft

Sequenced at SESSION_133 M14.0 open.
Six increments (five code + one
close-out). Historical M13 shipped
four; M12 shipped eight; M11 shipped
seven. M14's smaller code footprint
reflects that most of the substrate
was delivered at M13 — this milestone
is projection + one small backend
increment.

### Increment 0 (M14.0) — Planning refinement + decision review

**Session.** SESSION_133 (this
session).

**Scope.** Confirm §5 decisions with
user; expand this planning skeleton
into a full memo; refine §7
sequencing. Six §5 decisions
confirmed as-recommended (see §0.a).

**Backend baseline change:** none
(planning only).
**Frontend baseline change:** none.

### Increment 1 (M14.1) — Backend: list + failure endpoints

**Session.** SESSION_134.

**Scope.** Two new pure query verbs
+ two new DRF admin endpoints.

- New verb `list_journal_entries(
  dealership, page=1, page_size=25)`
  in `services/accounting/journal.py`.
  Ordering: `-posted_at` (most
  recent first). Returns list +
  total count + pagination
  metadata. No filters (§5.b Option
  B).
- New verb
  `detect_cost_posting_failures(
  dealership, now=None,
  threshold_hours=24)` in
  `services/accounting/vehicle_cost
  .py`. Query: `VehicleCost.
  objects.filter(vehicle__dealership
  =dealership, posted_at__isnull=
  True, is_estimate=False,
  created_at__lte=now-threshold)`.
  Returns list of unposted
  VehicleCosts older than the
  threshold (one detector-run
  boundary).
- New endpoint `GET admin/
  accounting/journal-entries/list/`
  in `views_accounting.py` with
  `?page=` + `?page_size=` query
  params. Reuses
  `IsSalesManagerOrOwnerAtActive
  Dealership`. Empty-list response
  for zero-portfolio tenants (not
  404).
- New endpoint `GET admin/
  accounting/cost-posting-failures/`
  with optional
  `?threshold_hours=<int>` query
  param (default 24). Same
  permission class. Empty-list
  response for zero-failure
  tenants.
- Decimal-as-string on all money
  fields (§5.c Option A).

**Test target.** ~15-20 focused
tests (~10 service + ~5-10
endpoint). Both endpoints exercise
tenancy guards, empty-state
semantics, and pagination /
threshold defaults.

**Backend baseline change:** 4,240
→ ~4,255 (+15 tests).
**Frontend baseline change:** none.
**DRF admin surface change:** 102 →
104 (+2).
**Tenancy carriers:** 47
(unchanged).
**Permission classes:** 8
(unchanged — zero-drift streak
extends to six consecutive
milestones at M14 close).
**Migrations:** none (no schema
changes).

### Increment 2 (M14.2) — Frontend: trial-balance render page

**Session.** SESSION_135.

**Scope.** New route
`dealer-ai-accounting/trial-balance`
+ new page
`AccountingTrialBalancePage.tsx` +
new `accountingApi.ts` module.

- New `frontend/src/lib/
  accountingApi.ts` with
  `fetchTrialBalance()` +
  TypeScript types for
  `TrialBalanceSnapshot` +
  `TrialBalanceRow`.
  Decimal-as-string preserved.
- New `frontend/src/pages/
  AccountingTrialBalancePage.tsx`
  rendering per-account rows in a
  shadcn `<Table>`, grand totals
  in a `<Card>` footer, and an
  `is_balanced` chip using shadcn
  `<Badge>`.
- Route registration in
  `main.tsx` under a new
  "Accounting" nav group per §5.d
  Option A.
- Empty-state UI: friendly
  "no postings yet" message for
  zero-portfolio tenants (matches
  M12.7 empty-portfolio posture).

**Test target.** ~10 Vitest
covering render (rows present,
totals present, balanced chip
correct), empty-state, and error
loading.

**Backend baseline change:** none.
**Frontend baseline change:** 78 →
~88 (+10 tests).
**Frontend operator routes:** 17 →
18 (+1).

### Increment 3 (M14.3) — Frontend: journal-entry browser + detail

**Session.** SESSION_136.

**Scope.** Two new routes
`dealer-ai-accounting/journal-
entries` +
`dealer-ai-accounting/journal-
entries/:pk` + two new pages.

- Extend `accountingApi.ts` with
  `fetchJournalEntries({page,
  pageSize})` +
  `fetchJournalEntry(pk)` + full
  TypeScript type surface for
  `JournalEntry` +
  `JournalEntryLine` responses.
- New `AccountingJournalEntries
  Page.tsx` — paginated list using
  shadcn `<Table>` + shadcn
  `<Pagination>`. Columns:
  posted_at + description +
  posted_by + total (sum of
  debits) + reversal-of-link (if
  `reverses_id`). Row click →
  detail route.
- New `AccountingJournalEntry
  DetailPage.tsx` — header block
  (metadata) + lines table (per-
  line account + debit + credit +
  memo) + reversal-linkage panel
  (if entry was reversed OR is a
  reversal). "Reverse this entry"
  button placeholder — dialog
  wires at M14.4.

**Test target.** ~15 Vitest
covering list render + pagination
+ empty-state + detail render +
reversal-linkage display + row-
click navigation.

**Backend baseline change:** none.
**Frontend baseline change:** ~88
→ ~103 (+15 tests).
**Frontend operator routes:** 18
→ 20 (+2).

### Increment 4 (M14.4) — Frontend: reversal dialog + cost-posting failure card

**Session.** SESSION_137.

**Scope.** Wire the M14.3 reversal
button to a shadcn `<Dialog>` +
add cost-posting failure card to
the trial-balance page.

- Extend `accountingApi.ts` with
  `reverseJournalEntry(pk,
  {reason, posted_at?})` +
  `fetchCostPostingFailures({
  thresholdHours?})`.
- Reversal dialog on detail page:
  shadcn `<Dialog>` with
  `<Textarea>` for reason
  (required, empty-blocked
  client-side matching M13.1
  serializer 400 per §5.e Option
  A belt+suspenders), optional
  `posted_at` (defer date picker
  to future — text input at MVP),
  confirm/cancel buttons. Success
  → re-fetch detail → show
  reversal linkage.
- Cost-posting failure card on
  the trial-balance page:
  displays count + top-N
  unposted VehicleCost rows
  (vehicle stock, category,
  amount, age-in-days). Empty
  state hidden entirely when
  zero failures.

**Test target.** ~10 Vitest
covering reversal dialog (empty-
reason blocked, success re-load,
cancel closes without POST) +
cost-posting failure card
(rendered when failures exist,
hidden when zero).

**Backend baseline change:** none.
**Frontend baseline change:** ~103
→ ~113 (+10 tests).
**Frontend operator routes:** 20
(unchanged — dialog is a modal,
not a route).

### Increment 5 (M14.5) — Close-out

**Session.** SESSION_138.

**Scope.** Documentation-only per
M10.8 / M11.7 / M12.8 / M13.4
precedent. Six close-out docs
matching M13.4 shape:

1. `docs/roadmap/MILESTONE_14_
   RETROSPECTIVE.md` — new.
2. `docs/CAPABILITY_MATRIX.md`
   §7o (M14 shipped surface) —
   append.
3. `docs/roadmap/IMPLEMENTATION_
   ROADMAP.md` §Milestone 14
   flip to shipped — edit.
4. `MILESTONE_14_PLANNING.md`
   frontmatter status flip
   `active` → `shipped` — edit.
5. `00-START-NEXT-SESSION.md`
   refresh with M15.0 priority —
   overwrite.
6. `MILESTONE_15_PLANNING.md`
   skeleton per standing user
   directive — new.

Coordinated commit landing all
close-out docs.

**Backend baseline change:** none.
**Frontend baseline change:** none.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §6 (twelve lessons carry
   into M14) + §8 (M13 unblocked
   work)
6. `docs/CAPABILITY_MATRIX.md` §7n
7. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

*Active memo. Expanded from skeleton
at SESSION_133 M14.0 open. §5
decisions locked (six as-
recommended). §7 sequencing locks
five code increments + one close-out.
Flip to `shipped` at M14.5.*
