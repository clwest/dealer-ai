---
title: "SESSION_134 handoff — Milestone 14 · Increment 1 (M14.1 — Backend: list + failure endpoints)"
status: historical
type: handoff
date: 2026-08-02
session: 134
milestone: 14
milestone_status: in-progress
milestone_name: "Operator UI for accounting substrate"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_134 — Milestone 14 · Increment 1 (M14.1 — Backend: list + failure endpoints)

## What shipped

Two new pure query verbs + two new DRF
admin endpoints in `services/accounting/`
and `views_accounting.py`. Read-only.
Zero schema changes. Zero new tenancy
carriers. Zero permission-class drift
(sixth consecutive milestone reusing
`IsSalesManagerOrOwnerAtActiveDealership`).

### Service verbs (2 new)

1. **`list_journal_entries(dealership,
   page=1, page_size=25) →
   JournalEntryListPage`** in
   `services/accounting/journal.py`.
   Paginated, tenant-scoped, ordered
   `-posted_at, -id` (recent-first with
   stable secondary key). Each returned
   entry carries a `.total_debit`
   annotation (sum of line debits) so
   the endpoint projection avoids
   per-row N+1 queries.
   `select_related("posted_by_user")`
   keeps username access single-query.
   **No filters** per §5.b Option B —
   filter surface layers at M15+ per
   operator evidence.

2. **`detect_cost_posting_failures(
   dealership, now=None,
   threshold_hours=24) →
   QuerySet[VehicleCost]`** in
   `services/accounting/vehicle_cost.py`.
   Same filter as `detect_unposted_costs`
   plus `created_at__lte=now-threshold`.
   Default 24h == one M13.2 detector-run
   boundary. `select_related("vehicle")`
   for stock-number projection.
   `order_by("created_at", "id")` —
   oldest failures surface first.

### DRF admin endpoints (2 new)

3. **`GET admin/accounting/
   journal-entries/list/`
   [?page=&page_size=]**.
   `page_size` capped at 100 to bound
   worst-case query size. Empty-list
   response for zero-portfolio tenants
   (not 404) per M13.3 §6 lesson 8
   zero-portfolio semantics. Decimal-
   as-string on `total_debit` field
   (quantized to 2dp — `Sum` drops
   trailing zeros; quantize preserves
   the M9-M13 wire convention).

4. **`GET admin/accounting/
   cost-posting-failures/
   [?threshold_hours=]`**.
   `threshold_hours` bounded to 8760
   (one year) to avoid runaway queries.
   `age_in_hours` computed at projection
   time from a captured `now` reference
   so every failure in one response
   uses the same moment.

### Frozen dataclass added (1 new)

5. **`JournalEntryListPage`** in
   `services/accounting/journal.py`.
   Tuple of entries + total_count +
   page + page_size. Matches M13.3
   `TrialBalanceSnapshot` posture per
   M13 §6 lesson 7.

### URL entries (2 new)

6. Both endpoints registered in
   `dealer_ai/urls.py` under the M13.1
   accounting URL block. Named
   `admin-journal-entry-list` +
   `admin-cost-posting-failures`.

### Package exports

7. `services/accounting/__init__.py`
   `__all__` extended with
   `JournalEntryListPage` +
   `detect_cost_posting_failures` +
   `list_journal_entries`.

### Tests (4 new files, 37 focused tests)

8. `test_m141_journal_entry_list_service.py`
   (9 tests): empty portfolio → empty
   page, recent-first ordering, stable
   secondary key, pagination, total_debit
   annotation, includes reversals,
   tenancy scoping, page-beyond-range,
   frozen dataclass output.
9. `test_m141_journal_entry_list_endpoint.py`
   (8 tests): 200 empty, projected rows,
   pagination via query params, invalid
   page → 400, invalid page_size → 400,
   auth required, advisor forbidden,
   cross-tenant scoping, row shape
   projection.
10. `test_m141_cost_posting_failures_service.py`
    (9 tests): empty queryset, includes
    old unposted non-estimate, excludes
    recent, excludes estimates, excludes
    posted, custom threshold_hours,
    oldest-first ordering, tenancy
    scoping, default `now` uses
    `timezone.now()`.
11. `test_m141_cost_posting_failures_endpoint.py`
    (11 tests): 200 empty, projected
    rows with age_in_hours, custom
    threshold_hours query param, invalid
    threshold (0) → 400, threshold over
    max → 400, excludes estimates, auth
    required, advisor forbidden, cross-
    tenant scoping, failure row shape.

**Target was ~15-20 focused tests (~10
service + ~5-10 endpoint); shipped 37**
across four files. The overshoot came
from routine boundary coverage
(pagination edges, threshold bounds,
projection shapes) rather than scope
creep — every test asserts on the M14.1
contract surface. Per M13.2 precedent
(target ~25, shipped 26) overshoot is
fine when the coverage stays on scope.

## Deltas at SESSION_134 close

- **Backend baseline:** 4,240 → **4,277
  pass** (+37 tests). 1 skipped, 0
  fail. Full suite ran in 122s.
- **Frontend baseline:** 78 (unchanged
  — backend-only increment).
- **DRF admin surface:** 102 → **104**
  (+2 endpoints).
- **Tenancy carriers:** 47 (unchanged —
  no new models).
- **Permission classes:** 8 (unchanged
  — zero drift extends to six
  consecutive milestones: M10 + M11 +
  M12 + M13 + M14.1).
- **Celery-beat task families:** 9
  (unchanged — read-only increment).
- **Migrations:** none (no schema
  changes).

## Files touched

Modified:

1. `backend/dealer_ai/services/
   accounting/journal.py` — added
   `JournalEntryListPage` frozen
   dataclass + `list_journal_entries`
   verb + `django.db.models` imports
   (DecimalField / Sum / Value /
   Coalesce).
2. `backend/dealer_ai/services/
   accounting/vehicle_cost.py` —
   added `detect_cost_posting_failures`
   verb.
3. `backend/dealer_ai/services/
   accounting/__init__.py` —
   exports.
4. `backend/dealer_ai/views_
   accounting.py` — added
   `admin_journal_entry_list` +
   `admin_cost_posting_failures`
   endpoint handlers with
   serializers + projection helpers
   + `django.utils.timezone` import.
5. `backend/dealer_ai/urls.py` —
   two new URL entries under the
   M13.1 accounting block.

Created:

6. `backend/dealer_ai/tests/
   test_m141_journal_entry_list_
   service.py` — 9 tests.
7. `backend/dealer_ai/tests/
   test_m141_journal_entry_list_
   endpoint.py` — 8 tests.
8. `backend/dealer_ai/tests/
   test_m141_cost_posting_failures_
   service.py` — 9 tests.
9. `backend/dealer_ai/tests/
   test_m141_cost_posting_failures_
   endpoint.py` — 11 tests.
10. `docs/handoffs/SESSION_134_m14_
    inc1_list_and_failures.md` —
    this handoff.

## Implementation-time micro-decisions

Per M10 §9 precedent, implementation-
time micro-decisions are recorded here
+ in the planning doc §0.a but do NOT
count against the M14 planning-time
as-recommended streak (which stands at
53 M5.1→M14.0).

1. **`total_debit` quantized at
   projection time.** `Sum("lines__
   debit")` returns Decimal without
   trailing zeros ("100" not "100.00");
   quantize to 2dp in the projection
   helper preserves the M9-M13
   Decimal-as-string wire convention.
   Alternative was to force via
   `output_field=DecimalField(...)`
   but the Coalesce wrapper already
   sets that; the drop is in the SUM
   result. Quantize at projection is
   the minimal fix.
2. **`age_in_hours` uses `int(seconds
   // 3600)` at projection.** No
   `relativedelta` or dateutil
   dependency. The endpoint captures
   `now` once so every row in one
   response uses the same reference
   moment — avoids age-drift across
   the projection loop for large
   failure lists.
3. **`page_size` cap = 100.**
   Reasonable operator page size;
   bounded to avoid runaway
   `qs[0:MAX_INT]` slices. `page_size
   > 100` returns 400.
4. **`threshold_hours` cap = 8760**
   (one year). Operator use case is
   surfacing 24-72h stalls; a year is
   plenty of headroom without allowing
   silly inputs like 999999.
5. **List endpoint URL is `/list/`
   suffix** (not root
   `journal-entries/`). The root path
   is POST (create) per M13.1; adding
   GET at the same URL would create a
   method-overload endpoint. Explicit
   `/list/` suffix matches the M12.7
   BHPH `admin/bhph-notes/list/`
   precedent.
6. **`page` beyond total_count
   returns empty entries + valid
   metadata**, not 404. Matches
   zero-portfolio semantics — a
   pagination edge case is not a
   missing resource.
7. **Reversal entries appear in the
   list.** They're just JournalEntry
   rows with `reverses_id` populated;
   the browser will surface the
   linkage. No filter to exclude
   them (would break audit trail
   review).

## Verifications passed at SESSION_134 close

- `python3 manage.py test dealer_ai`
  → **4,277 pass, 1 skipped, 0 fail**
  in 122s.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- Four new test files pass in
  isolation (37/37 in 1.5s).

## What SESSION_135 (M14.2) picks up

Per `MILESTONE_14_PLANNING.md` §7
Increment 2:

- Add new frontend route
  `dealer-ai-accounting/trial-balance`
  under the operator layout in
  `frontend/src/main.tsx`.
- Create new
  `frontend/src/lib/accountingApi.ts`
  with `fetchTrialBalance()` +
  TypeScript types for
  `TrialBalanceSnapshot` +
  `TrialBalanceRow`. Decimal-as-string
  handling per §5.c Option A.
- Create new
  `frontend/src/pages/
  AccountingTrialBalancePage.tsx`
  rendering per-account rows in a
  shadcn `<Table>`, grand totals in a
  `<Card>` footer, `is_balanced` chip
  using shadcn `<Badge>`. Empty-state
  "no postings yet" UI for zero-
  portfolio tenants.
- New Vitest coverage target: ~10
  tests. Frontend baseline 78 → ~88.
- Consumes existing M13.3 endpoint
  `GET admin/accounting/trial-balance/`
  (no additional backend work at
  M14.2).

**Explicit non-goals at M14.2:**

- ❌ No backend work (M14.1 shipped
  the backend surface M14.2-M14.4
  need).
- ❌ No `as_of` picker on the trial-
  balance page (deferred per §3
  deferral 2 — belongs with M15+
  close workflow).
- ❌ No journal-entry browser (M14.3).
- ❌ No reversal dialog (M14.4).
- ❌ No cost-posting failure card
  yet (M14.4).

## Push authorization

One local commit (M14.1 backend
substrate + tests + handoff + session-
start refresh) pending user
authorization at SESSION_134 close.

## Anchors for SESSION_135

1. `docs/roadmap/MILESTONE_14_
   PLANNING.md` §7 M14.2
   (implementation spec).
2. `docs/handoffs/SESSION_134_m14_
   inc1_list_and_failures.md` (this
   handoff).
3. `frontend/src/pages/DealerAiBhph
   Portfolio.tsx` (analog: list-view
   page consuming admin endpoints).
4. `frontend/src/lib/bhphApi.ts`
   (analog: API client module with
   Decimal-as-string handling).
5. `frontend/src/main.tsx` (route
   registration — add new
   `dealer-ai-accounting/*` group).
6. `backend/dealer_ai/views_
   accounting.py` `admin_trial_
   balance` (endpoint contract to
   consume).
