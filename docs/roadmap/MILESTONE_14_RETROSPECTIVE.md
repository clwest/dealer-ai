---
title: "Milestone 14 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_133 → SESSION_138
milestone: 14
milestone_name: "Operator UI for accounting substrate"
related:
  - docs/roadmap/MILESTONE_14_PLANNING.md
  - docs/roadmap/MILESTONE_13_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 14
---

# Milestone 14 — Retrospective

Written at Milestone 14 close (SESSION_138).
Records what was planned, what shipped,
what deviated and why, and lessons carried
forward for Milestone 15 and beyond.
Mirrors the `MILESTONE_13_RETROSPECTIVE.md`
structure.

## 1. Planned scope

`MILESTONE_14_PLANNING.md` at SESSION_132
close (drafted at M13.4 per standing user
directive) defined the milestone as the
operator UI for the M13 accounting
substrate. §5.a Option A locked all four
UI surfaces named in the M13 retrospective
§3 item 4 as in-scope: journal-entry
browser + trial-balance render + reversal-
with-reason dialog + cost-posting failure
surfacing.

**This milestone was deliberately UI-
biased**, not a substrate expansion. M13
shipped the accounting reconciliation
core backend-only per M13 §5.f Option C;
M14 layers the operator UI over that
substrate so real accounting workflows
become operator-usable. The only backend
work shipped is two small additive query
verbs at M14.1 (journal-entry list +
cost-posting failure surfacer) — both
consumed by the M14.2–M14.4 UI, both
zero-drift to the M13 substrate.

§5.a–§5.f drafted **six load-bearing
planning-time decisions** all flagged
`[NEEDS-DECISION-BEFORE-M14.0]`. §7
sequenced six increments (M14.0 planning
+ M14.1 backend + M14.2–M14.4 frontend +
M14.5 close-out).

**Original §7 sequencing shipped verbatim.**
The six SESSION_133 decisions confirmed as-
recommended at M14.0 open (Options A / B /
A / A / A / A). Additional implementation-
time micro-decisions surfaced at M14.1
(seven) + M14.2 (seven) + M14.3 (eight) +
M14.4 (nine) — recorded in §0.a
amendments per the M5-M13 precedent. Per
M10 §9 those are **implementation-time
defaults, not planning-time decisions**,
so they do not count against the streak.
**The streak stands at 53 planning-time
as-recommended M5.1 → M14.0** — five
consecutive milestones now (M10 + M11 +
M12 + M13 + M14) with every §5 decision
confirmed as-recommended at planning-time
open.

## 2. What actually shipped

Every §3 compatibility item verified
true; enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M14.0 planning | 133 | `MILESTONE_14_PLANNING.md` expanded from skeleton (~260 lines) to active memo (~877 lines). Frontmatter `status: draft` → `status: active`; `milestone_name` set to "Operator UI for accounting substrate". Six §5 load-bearing decisions resolved with recommendations + rationale. §1 business questions expanded to four operator workflow questions (Q1 browser / Q2 render / Q3 reversal / Q4 failure surfacing). §3 deferrals locked at 17 (12 M14-specific + 5 universal). §7 sequenced five code increments + one close-out. **Six §5 decisions confirmed as-recommended** — streak 53 M5.1→M14.0. | `0c77f7e` |
| M14.1 Backend: list + failure endpoints | 134 | Two new pure query verbs + two new DRF admin endpoints. `list_journal_entries(dealership, page=1, page_size=25) → JournalEntryListPage` in `services/accounting/journal.py` — paginated, `-posted_at, -id` ordering, `total_debit` annotation via SUM+Coalesce, `select_related("posted_by_user")` for username access. **No filters at M14.1** per §5.b Option B — filter surface layers at M15+ per operator evidence. `detect_cost_posting_failures(dealership, now=None, threshold_hours=24) → QuerySet[VehicleCost]` in `services/accounting/vehicle_cost.py` — same filter as `detect_unposted_costs` plus `created_at__lte=now-threshold`. Default 24h == one M13.2 detector-run boundary. New `JournalEntryListPage` frozen dataclass matching M13.3 `TrialBalanceSnapshot` posture per M13 §6 lesson 7. Two new admin endpoints in `views_accounting.py`: `GET admin/accounting/journal-entries/list/[?page=&page_size=]` (`page_size` capped at 100) + `GET admin/accounting/cost-posting-failures/[?threshold_hours=]` (`threshold_hours` capped at 8760). Both reuse `IsSalesManagerOrOwnerAtActiveDealership` (permission-class drift: zero — sixth consecutive milestone). Empty-list responses for zero-portfolio / zero-failure tenants (not 404). Decimal-as-string on all money fields with `.quantize(Decimal("0.01"))` on `total_debit` (Sum drops trailing zeros; quantize preserves the M9-M13 wire convention). URL entries in `dealer_ai/urls.py`. `services/accounting/__init__.py` `__all__` extended. **37 focused tests** across four new files (target ~15-20; overshoot on boundary coverage): 9 list-service + 8 list-endpoint + 9 failures-service + 11 failures-endpoint. Tenancy scoping, empty-state semantics, pagination edges, threshold defaults, projection shapes, permission denial all covered. Tenancy carrier 47 (unchanged — no new models). DRF admin surface 102 → 104 (+2). Frontend baseline 78 (unchanged — backend-only). No schema changes / no migrations. **Seven §0.a M14.1 micro-decisions recorded** — all as-recommended per M10 §9 (do not count against streak). | `4d1e3f3` |
| M14.2 Frontend: trial-balance render page | 135 | First frontend increment of M14. New `frontend/src/lib/accountingApi.ts` module with `fetchTrialBalance()` + `TrialBalanceSnapshot` / `TrialBalanceRow` / `GLAccountType` TypeScript types. Decimal-as-string preserved per §5.c Option A. New `AccountingTrialBalancePage.tsx` — h1 header + card with as-of timestamp + shadcn `<Badge>` balanced/unbalanced chip + per-account table (code/name/type-badge/debits/credits/natural-balance) + grand-totals footer (conditional on `rows>0`) + empty-state message referencing the M13.2 detector. `Intl.NumberFormat` `en-US` currency + `tabular-nums` for right-aligned numeric columns. Loading + error states via the M11/M12 `useEffect` + cancellation-flag pattern. New route `dealer-ai-accounting/trial-balance` under `RequireAuth` — first route of the new `dealer-ai-accounting/*` group per §5.d Option A. **11 focused Vitest tests** (target ~10; overshoot by 1 for role-based header disambiguation): loading, populated render, currency formatting, balanced/unbalanced chip, empty state, hidden footer, error state, account-type badges, dealership slug. Browser E2E verified (empty + populated states with 2 seeded demo entries totaling $13,375.50 + auth-gate redirect all render correctly). Backend baseline 4,277 (unchanged). Frontend Vitest 78 → 89 (+11). Frontend operator routes 17 → 18 (+1). `tsc --noEmit` + `vite build` clean. **Seven §0.a M14.2 micro-decisions recorded**. | `4b74d09` |
| M14.3 Frontend: journal-entry browser + detail | 136 | Two new frontend pages + two new routes + extended API client. Extended `accountingApi.ts` with `JournalEntryListEntry` + `JournalEntryListPage` + `JournalEntryLine` + `JournalEntry` types + `fetchJournalEntries({page, pageSize})` + `fetchJournalEntry(pk)`. New `AccountingJournalEntriesPage.tsx` — paginated list (Previous/Next buttons, disabled at boundaries) + reversal-linkage badges (destructive "Reversal of #X" vs outline "Original") + row-level View links + empty-state message + count/page metadata. New `AccountingJournalEntryDetailPage.tsx` — back link + header card (metadata + Reversal reason meta row rendered only on reversals) + lines table (zero-value cells blank, per-entry line totals computed client-side for display) + Corrections card with disabled "Reverse this entry (M14.4)" placeholder button. Not-found state via error-message regex; NaN pk short-circuits without API call. Two new routes `dealer-ai-accounting/journal-entries` + `journal-entries/:pk` under `RequireAuth`. **24 focused Vitest tests** across two new spec files (13 list + 11 detail; target ~15, overshoot on pagination + reversal-linkage coverage). Browser E2E verified: seeded 2 originals + 1 reversal; list renders recent-first with badges + disabled pagination for single-page; reversal detail (#5) shows swapped debit/credit + reason; original detail (#3) shows no reason row + correct orientation; not-found route renders "Journal entry not found." Zero unexpected console errors. Backend baseline 4,277 (unchanged). Frontend Vitest 89 → 113 (+24). Frontend operator routes 18 → 20 (+2). `tsc --noEmit` + `vite build` clean. **Eight §0.a M14.3 micro-decisions recorded**. | `2c8ed30` |
| M14.4 Frontend: reversal dialog + cost-posting failure card | 137 | Final code increment of M14. Extended `accountingApi.ts` with `reverseJournalEntry(pk, {reason, posted_at?})` via `authPostJSON` (CSRF auto-attached) + `fetchCostPostingFailures({thresholdHours?})` + `ReverseJournalEntryPayload` / `CostPostingFailure` / `CostPostingFailuresResponse` types. Wired the M14.3 placeholder Reverse button to a shadcn `<Dialog>`: `ReverseEntryDialog` subcomponent with reason `<Textarea>` (`aria-required` + `aria-invalid` on blank; trim-based validation matching M13.1 serializer 400 per §5.e Option A belt+suspenders), optional `posted_at` text input (defer date picker), Cancel + Confirm reversal buttons (Confirm disabled when reason blank; "Posting…" during submit). Success closes dialog + resets form + triggers detail re-fetch via `reloadTick` state on `useEffect([pk, reloadTick])`. Error rendered inline via `role="alert"` without closing dialog. Added `CostPostingFailuresCard` subcomponent to the trial-balance page — both fetchers fire in `Promise.all` for single-paint render; card rendered **only when `failures.length > 0`** per zero-noise posture. Styled with `border-destructive/40` + destructive-colored title + "Attention" badge; table of unposted VehicleCosts >24h old with vehicle_stock + category + amount + age_in_hours + reference. **9 focused Vitest tests** (target ~10): 7 dialog tests (enabled trigger, opens on click, blank-reason blocks Confirm, populated-reason enables, successful POST re-fetches, backend error inline, Cancel doesn't POST) + 3 failure-card tests (hidden at count=0, renders rows at count>0, Attention badge). One flaky pre-existing test converted from `getByText` to `findByText` (extra render microtask from dialog subcomponent caused a race). Browser E2E verified: typed reason "Wrong amount — operator entered $7,777 instead of $8,777", confirmed, dialog closed, navigated to list, new reversal entry #7 present with `posted_by=smoke_owner` (request user correctly captured by M13.1 endpoint) + matching $7,777.00 amount + "Reversal of #6" badge. Failure card renders atop trial balance with 4 failures (seeded + 3 pre-existing test data). Zero unexpected console errors. Backend baseline 4,277 (unchanged). Frontend Vitest 113 → 122 (+9). Frontend operator routes 20 (unchanged — dialog is a modal). `tsc --noEmit` + `vite build` clean. **Nine §0.a M14.4 micro-decisions recorded**. | `fc4e4a1` |
| M14.5 Closeout | 138 | Documentation-only per M10.8 / M11.7 / M12.8 / M13.4 precedent. Six close-out docs (this retrospective + capability matrix §7o + implementation roadmap §Milestone 14 SHIPPED entry added + planning doc frontmatter flip `active` → `shipped` + session-start refresh + M15 planning skeleton) + coordinated commit landing all M14.5 docs. **Milestone 14 — Operator UI for accounting substrate — SHIPPED.** | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a
clear re-entry path.

**In-milestone deferrals:**

1. **Journal-entry list filters**
   (date range, posted_by,
   reversal-only, description
   search). M14.1 ships filter-less
   list per §5.b Option B. Filter
   surface layers at M15+ per
   operator evidence.
2. **`as_of` picker on trial-
   balance page.** M14.2 ships
   render at `now()` only. Operator
   date-picker for historical
   snapshots defers to M15+
   (belongs with monthly-close
   workflow slice).
3. **Journal-entry manual create
   UI.** The M13.1 POST create
   endpoint ships, but manual UI
   for adjusting entries defers to
   M15+ (belongs with period-close
   workflow — accountants post
   adjusting entries at month end,
   not ad-hoc).
4. **Sidebar nav entry for
   accounting.** Every M14 page is
   reachable only by direct URL or
   cross-links from other
   accounting pages. Matches the
   M11/M12 pattern (Sales / BHPH
   also have no sidebar entries).
   A future "navigation refactor"
   increment could add sidebar
   entries for accounting + BHPH +
   sales as their surfaces
   mature.
5. **Date-picker widget on
   reversal dialog `posted_at`
   input.** M14.4 ships plain text
   input; date-picker component
   defers.
6. **Category-group-aware GL
   mapping** for the M13.2
   detector. Deferred pending
   operator evidence of miscoding
   pain.

**Explicit M14 scope-boundary
deferrals** (per
`MILESTONE_14_PLANNING.md` §3):

7. **`TrialBalanceSnapshot`
   materialization + monthly close
   workflow.** M13.3 pure recompute
   serves M14 render needs;
   snapshot materialization is an
   M15+ workflow slice.
8. **Period-comparison verbs**
   (delta between two `as_of`
   snapshots). Defers with M15+
   close workflow.
9. **CSV / spreadsheet export**
   for trial-balance and journal-
   entry list. JSON payload +
   rendered table only at M14.
10. **Per-dealer COA overrides
    UI.** Deferred pending
    operator evidence.
11. **`post_save` signal auto-
    seeding COA for new
    dealerships.** Deferred
    pending onboarding-surface
    trigger point definition.
12. **M9 sale-booking GL post**
    (Q1 of M13 retrospective §8).
    Substrate-consuming write-
    path milestone, not a UI
    milestone. Layers at M15+ per
    §5.d Option C hybrid trigger
    posture named in M13.
13. **M10 F&I chargeback GL
    reversal** (Q2 of M13
    retrospective §8). Deferred
    with M15+ write-path work.
14. **M12 BHPH payment GL post**
    (Q3 of M13 retrospective §8).
    Deferred with M15+ write-path
    work.

**Universal / cross-milestone
deferrals** (regardless of
target):

15. **Payroll / W-2 / 1099** —
    external-service scope
    boundary.
16. **GAAP-compliant audited
    financial reporting** — out
    of scope for platform v1.
17. **Direct DMS integration**
    — belongs to a future vendor-
    integration milestone.
18. **Year-end tax return
    preparation** — external CPA.

## 4. Deviations from plan

**Zero deviations from planned §7
sequencing.** Every M14.N shipped
in the order the planning doc
named. Every
`[NEEDS-DECISION-BEFORE-M14.N]`
item was resolved at the correct
increment open.

**Zero in-milestone addenda.**
M13 had zero addenda; M12 had
one (M12.7 `admin_bhph_note_list`).
M14 shipped exactly the endpoints
+ pages + routes named in the
planning doc — two at M14.1,
three pages + three routes across
M14.2–M14.4 (dialog is a modal
not a route).

**One in-milestone contract
correction** — the `total_debit`
projection returned unformatted
Decimal from Django's `Sum`
aggregation ("100" not "100.00");
fixed by quantizing to 2dp at the
projection helper. Preserves the
M9-M13 Decimal-as-string wire
convention. Caught during M14.1
implementation via the endpoint
test suite before commit.

**One flaky pre-existing test
converted from `getByText` to
`findByText`** at M14.4 close.
The `AccountingJournalEntryDetail
Page.test.tsx` line-render test
started racing with a render
microtask introduced by the new
dialog subcomponent. `findByText`
auto-waits; `getByText` was
hitting the loading state
momentarily.

## 5. Compatibility

**Zero regressions across every
M14 increment.** Every existing
test at M13 close still passes at
M14 close. Every M1-M13 endpoint
still returns the same shape it
did at M13 close.

- M1 chat funnel untouched.
- M2 payment engine untouched.
- M3 ConditionReport untouched.
- M4 recon substrate untouched.
- M5 lifecycle untouched.
- M6 listings untouched.
- M7 async substrate untouched.
- M8 analytics untouched.
- M9 Sale untouched.
- M10 F&I untouched.
- M11 sales-side channels +
  customer journey — untouched.
- M12 BHPH portfolio — untouched.
- M13 accounting substrate —
  extended additively at M14.1.
  `services/accounting/journal.py`
  gained `list_journal_entries`
  verb + `JournalEntryListPage`
  frozen dataclass;
  `services/accounting/vehicle_
  cost.py` gained `detect_cost_
  posting_failures` verb. Every
  M13 verb + M13 endpoint returns
  the same shape it did at M13
  close.

**Post-LLM safety stack: 17
scrub stages (unchanged).** M14
has no LLM path — the operator
UI is entirely deterministic
projection over M13.1 + M13.3 +
M14.1 endpoints.

**Permission classes: 8
(unchanged).** Every M14.1
endpoint reuses the M4
`IsSalesManagerOrOwnerAtActive
Dealership` class. Zero
permission-class drift across
M14.1 backend work — extends the
streak to **six consecutive
milestones** (M10 + M11 + M12 +
M13 + M14). M14.2–M14.4 have no
new backend surface so the
posture is preserved by
construction.

## 6. Lessons

Ten carry into M15+ planning.

1. **The §5-decisions-locked-at-
   open pattern held for a fifth
   milestone.** All six §5
   decisions at M14.0 open
   confirmed as-recommended,
   matching M10/M11/M12/M13
   pattern. **53 planning-time
   as-recommended M5.1 → M14.0**
   across five consecutive
   milestones now. The framework
   works for milestones with
   substantially different
   ownership surfaces — UI-only
   milestones are as amenable to
   the pattern as backend-only
   and mixed milestones.
2. **§0.a implementation-time
   micro-decisions continue to be
   load-bearing.** M14.1 surfaced
   7, M14.2 surfaced 7, M14.3
   surfaced 8, M14.4 surfaced 9.
   Total 31 micro-decisions
   across four M14 code
   increments. All recorded as-
   recommended, all locked into
   the planning doc §0.a. Per
   M10 §9 these don't count
   against the streak, but they
   DO define the shape of the
   implementation.
3. **UI-only milestones need
   substantially more micro-
   decisions than backend-only
   ones.** M14 shipped 31 §0.a
   micro-decisions across four
   code increments (~7.75 per
   increment). M13 shipped 11
   across two implementation
   increments (~5.5 per). The
   delta reflects genuine UI
   surface area — every render
   choice (badge variant,
   currency format, empty-state
   copy, disabled-button label)
   is a decision that would
   surface at review if not
   defended. Future UI-heavy
   milestones should plan for
   comparable §0.a density.
4. **Browser E2E verification
   catches issues Vitest cannot.**
   Every M14.2 / M14.3 / M14.4
   close ran Playwright against
   live dev servers. Caught:
   `total_debit` projection
   quantize gap (M14.1 backend
   caught this via endpoint test,
   but a browser view of the
   populated table would also
   have surfaced it); reversal
   dialog end-to-end (creates the
   correct reversal entry with
   correct `posted_by`
   attribution); failure card
   rendering with real detector-
   miss data. Manual Playwright
   pass per code increment is
   the right cadence for UI
   milestones.
5. **Client-side validation
   matches server-side validation
   via matching the trim
   posture.** The reversal
   dialog's reason field uses
   `reason.trim().length === 0`
   to disable Confirm, matching
   the M13.1 service verb's
   `(reason or "").strip()`
   check. Belt+suspenders per
   §5.e Option A — the client
   prevents the request, the
   server rejects the request if
   the client is bypassed. Match
   the trim posture symmetrically
   or the belt and suspenders
   disagree on edge cases (all-
   whitespace reason).
6. **Zero-noise render posture
   for count-based cards.** The
   M14.4 cost-posting failure
   card hides entirely at
   `count=0` rather than
   showing a "no failures"
   banner. Matches M14.2 grand-
   totals footer posture (hidden
   at zero rows). Operators
   should not have to visually
   parse "no results" chrome as
   background noise; render only
   when there's signal.
7. **`Promise.all` parallel
   fetch is the right posture
   when two endpoints share
   permission + tenancy
   substrate.** M14.4 fetches
   trial balance + failures in
   parallel — single paint,
   fewer roundtrips. Trade-off:
   if either endpoint fails,
   both go down. Acceptable at
   MVP because both consume the
   M13.1 + M14.1 accounting
   surface which shares a single
   permission class and tenancy
   resolver. Would not apply
   across unrelated substrates.
8. **Frontend re-fetch via
   `reloadTick` state is
   simpler than react-query for
   this scale.** The M14.4
   reversal dialog uses a
   `reloadTick` counter as a
   `useEffect` dependency to
   trigger detail re-fetch on
   success. Project doesn't use
   react-query here; a full
   query-cache layer would be
   over-engineering for the
   size of the accounting
   surface. If future modules
   grow beyond ~5 fetchers with
   shared cache needs, revisit.
9. **Verbatim `ApiError`
   render is honest error
   surfacing at MVP.** M14.4
   reversal dialog renders
   backend `{detail: "..."}`
   errors as-is via
   `role="alert"`. Operators
   see the actual HTTP status +
   backend message. Parsing
   into user-friendlier
   language can layer if
   evidence surfaces the need;
   verbatim gives the
   specificity that operator
   feedback needs to file a
   useful bug report.
10. **Zero-drift permission-
    class posture extends to
    six consecutive
    milestones.** Every M10 +
    M11 + M12 + M13 + M14
    endpoint reused M4's
    `IsSalesManagerOrOwnerAt
    ActiveDealership`. Permission-
    class count stays at 8. Same
    lesson from M13 §6 lesson
    12; the streak just extends
    by one milestone. Future
    reconciliation / reporting /
    admin milestones should
    default to reusing the
    existing permission class
    unless the endpoint surface
    genuinely requires a
    distinct authorization
    model.

## 7. Streak update

**53 planning-time as-recommended
M5.1 → M14.0.** Five consecutive
milestones now (M10 + M11 + M12 +
M13 + M14) with every §5 decision
confirmed as-recommended at
planning-time open. §0.a
implementation-time micro-
decisions across M14.1–M14.4 (31
in total) do not count against
the streak per M10 §9.

The pattern that held:

1. Draft the §5 recommendations
   at planning close of the
   *previous* milestone.
2. Confirm at the next
   milestone's opening session.
3. Amend §0.a as micro-decisions
   surface per implementation
   session.
4. Never re-vote a §5 decision
   mid-milestone — file the
   amendment as §0.a instead.

Next planning cycle at M15 open
will test whether the pattern
holds against whatever surface
comes next.

## 8. What M14 unblocks for M15+

- **Real accounting workflows are
  operator-usable.** Before M14,
  the M13 substrate could only be
  observed via `manage.py shell`
  or curl. After M14, a sales-
  manager / owner role at any
  dealership can view the trial
  balance, browse journal
  entries, drill into detail,
  reverse mis-posted entries,
  and see cost-posting failures
  — all from the operator UI.
  This makes the M15+ decision
  about which write-path GL
  slice to ship next
  substantially better-informed
  (operators can now say what
  they wish they could see /
  do).
- **M9 sale-booking GL post
  substrate is ready** — the
  operator UI to *view* the
  resulting journal entries is
  now in place. When M15+ wires
  `services/sale/record_sale`
  to `services/accounting/
  post_journal_entry`, the new
  entries will appear in the
  M14.3 browser automatically
  with `posted_by_username`
  populated from the sale-
  booking user.
- **M10 F&I chargeback GL
  reversal** and **M12 BHPH
  payment GL post** — same
  posture as M9 above. Both
  produce journal entries the
  M14 UI will surface without
  additional frontend work.
- **Cost-posting failure
  triage** — the M14.4 failure
  card gives operators
  visibility into M13.2
  detector misses. Root-cause
  categories (missing/inactive
  COA account, permission
  drift, category-vocab drift)
  can be layered as filter
  variants at M15+ once
  operator evidence names the
  common failure modes.
- **Category-group-aware GL
  mapping** for the M13.2
  detector is unblocked — the
  failure card gives operators
  a signal for miscoding pain,
  which is the evidence gate
  that decision-2's fixed-
  vocab deferral was waiting
  for.
- **Monthly close workflow**
  is unblocked from the UI
  side — operators can now
  visually confirm balanced-
  trial-balance state, which
  is the closing-condition
  the workflow will need to
  surface.
