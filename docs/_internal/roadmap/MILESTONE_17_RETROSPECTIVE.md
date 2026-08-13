---
title: "Milestone 17 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_145
milestone: 17
milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
related:
  - docs/roadmap/MILESTONE_17_PLANNING.md
  - docs/roadmap/MILESTONE_16_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 17
---

# Milestone 17 — Retrospective

Written at Milestone 17 close (SESSION_145).
Records what was planned, what shipped, what
deviated and why, and lessons carried forward
for Milestone 18 and beyond. Mirrors the
`MILESTONE_16_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_17_PLANNING.md` at SESSION_144 close
(drafted at M16.2 per standing user directive)
defined the milestone as the bundled Trial-
balance materialization + `as_of` picker
(monthly-close v1). §5.a Option E locked at
SESSION_145 M17.0 open — a durable
`TrialBalanceSnapshot` entity + operator UI
picker ship together as the smallest complete
operator-usable slice of monthly-close
workflow.

**This milestone was deliberately mixed
backend+frontend**, unlike the two prior
backend-only milestones (M15 sync-sibling +
M16 detector). The frontend layer is essential
to the value proposition — without the picker,
operators can only freeze "now"; without the
entity, the picker has nothing durable to
record. §5.b Option B (header + child rows) +
§5.c Option A (sync-sibling freeze verb) +
§5.d Option A (`unique_together=(dealership,
as_of)` → 409) + §5.e Option B (date-only
picker) + §5.f Option A (snapshot rows
immutable) round out the six load-bearing
decisions.

§5.a–§5.f drafted **six load-bearing planning-
time decisions** all flagged `[NEEDS-DECISION-
BEFORE-M17.0]` in the skeleton. §7 sequenced
four increments (M17.0 planning + M17.1
backend + M17.2 frontend + M17.3 close-out) —
matches the anticipated shape for a mixed-scope
milestone.

**Original §7 sequencing shipped verbatim.**
All six SESSION_145 planning-time decisions
confirmed as-recommended at M17.0 open (Option
E for §5.a plus Option A / B / A / A / B / A
for §5.b-§5.f). Four §0.a implementation-time
micro-decisions surfaced at M17.1 + M17.2
(dataclass rename, detail URL shape, picker
default deferral, native `<input type="date">`
in place of shadcn `Calendar`) — recorded in
§0.a amendments per M5-M16 precedent. Per M10
§9 those are **implementation-time defaults,
not planning-time decisions**, so they do not
count against the streak. **The streak stands
at 70 planning-time as-recommended M5.1 →
M17.0** — eight consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 + M16 +
M17) with every §5 decision confirmed as-
recommended at planning-time open.

**Sessions collapsed.** Per user direction
"continue" after each M17 increment landed,
all four increments shipped in **one calendar
session (SESSION_145)** rather than
distributing across SESSION_145 through
SESSION_148 as originally sequenced. Session
numbering reflects calendar sessions, not
planning-sequence positions.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M17.0 planning | 145 | `MILESTONE_17_PLANNING.md` expanded from ~390-line skeleton to ~1,050-line active memo. Frontmatter `status: draft` → `status: active`; `milestone_name` set to "Trial-balance materialization + as_of picker (monthly-close v1)"; `sources` list extended with ACCOUNTING research + M13/M14/M15/M16 planning + retrospectives. Six §5 load-bearing decisions resolved with recommendations + rationale (§5.a Option E + §5.b Option B + §5.c Option A + §5.d Option A + §5.e Option B + §5.f Option A). §1 business questions expanded to four operator-workflow questions (Q1 freeze stable across backdated entries / Q2 arbitrary historical date query / Q3 prior-close history / Q4 live aggregator unchanged). §3 deferrals locked at 17 (12 M17-specific + 5 universal). §7 sequenced two code increments (backend + frontend) + one close-out (four total including planning). **Six §5 decisions confirmed as-recommended** — streak 70 M5.1 → M17.0. Three §0.a M17.1 micro-decision recommendations surfaced for resolution at M17.1 open. | `404605e` |
| M17.1 Backend: TrialBalanceSnapshot entity + freeze verb + endpoints | 145 | Migration `0046_m171_trial_balance_snapshot.py` (two `CreateModel` operations + two `AddConstraint` operations — zero data migration). Rename `TrialBalanceSnapshot` dataclass → `TrialBalanceComputation` + `TrialBalanceRow` → `TrialBalanceComputationRow` in `services/accounting/snapshot.py` (frees the "snapshot" name for the durable Django model per §0.a M17.1 decision 1). Update all call sites in the same commit (`services/accounting/__init__.py`, `views_accounting.py`, `tests/test_m133_trial_balance_service.py`). New module `services/accounting/trial_balance_close.py` (~190 lines) with three verbs: `freeze_trial_balance` atomic sync-sibling verb (calls `compute_trial_balance` internally, materializes header + child rows via `bulk_create`, catches `IntegrityError` on `unique_together` violation + re-raises as `DuplicateTrialBalanceSnapshotError`) + `list_trial_balance_snapshots` paginated per M14.1 pattern + `get_trial_balance_snapshot` tenant-scoped retrieve. Two new Django models in `models.py`: `TrialBalanceSnapshot` (header: `dealership`, `as_of`, `total_debits`, `total_credits`, `is_balanced`, `created_by` FK to User nullable, `created_at`; `Meta.unique_together = (('dealership', 'as_of'),)`) + `TrialBalanceSnapshotRow` (child: `dealership`, `snapshot` FK CASCADE, `account_code`, `account_name`, `account_type` using `GL_ACCOUNT_TYPE_CHOICES`, `debit_total`, `credit_total`, `natural_balance`; `Meta.unique_together = (('snapshot', 'account_code'),)`). New `DuplicateTrialBalanceSnapshotError(ValueError)` domain exception (409 mapping). Extended `services/accounting/__init__.py` `__all__` for the new symbols. Three new DRF admin endpoints in `views_accounting.py` reusing `IsSalesManagerOrOwnerAtActiveDealership`: POST `/admin/accounting/trial-balance/snapshots/` (freeze; body `{"as_of": "<ISO8601>"}`; 201 with full projection; 400 on missing/invalid; 409 on duplicate; 403 non-permitted role), GET `/admin/accounting/trial-balance/snapshots/list/` (paginated; `?page=&page_size=`; compact summaries), GET `/admin/accounting/trial-balance/snapshots/<int:pk>/` (detail; full frozen rows; 404 on cross-tenant per fail-closed posture). Tenancy carriers 47 → 49 (added TrialBalanceSnapshot + TrialBalanceSnapshotRow to `_TENANT_CARRIER_MODEL_NAMES`). Permission classes 7 (unchanged — zero-drift streak extends to nine consecutive milestones now, actual count corrected from prior narrative doc's "8"). DRF admin surface 104 → 107 (+3). Frontend Vitest 122 (unchanged — no frontend at M17.1 per §7). No new post-LLM scrub stages. **Four §0.a M17.1 micro-decisions recorded** — all as-recommended per M10 §9 (do not count against streak). **37 focused tests** across 12 TestCase classes in new `tests/test_m171_trial_balance_materialization.py`. | `f217e0d` |
| M17.1 docs | 145 | `SESSION_145_m17_inc0_planning.md` + `SESSION_145_m17_inc1_backend.md` handoffs; `00-START-NEXT-SESSION.md` refreshed for M17.2. Documented the M16 retrospective's "8 permission classes" miscount vs the actual 7 (6 `Is*` + `ReadOnly`). | `bedc615` |
| M17.2 Frontend: as_of picker + snapshot history list | 145 | `frontend/src/lib/accountingApi.ts` extended (~100 lines): new `fetchTrialBalance(asOf?)` signature (backward-compatible) + `freezeTrialBalance` + `listTrialBalanceSnapshots` + `fetchTrialBalanceSnapshot` + new TypeScript types (`TrialBalanceSnapshotSummary`, `FrozenSnapshotRow`, `FrozenTrialBalanceSnapshot`, `TrialBalanceSnapshotListPage`). New component `frontend/src/components/accounting/TrialBalanceDatePicker.tsx` (~85 lines): controlled native `<input type="date">` wrapped in shadcn `Input` primitive + pure helpers `todayIsoDate()` + `dateToEndOfDayIso()`. Extended `frontend/src/pages/AccountingTrialBalancePage.tsx` (~500 lines total, +200 net): new "Query controls" card with date picker + "Freeze this view" button + inline success/409/generic error banners; live trial-balance card refetches on picker change via `useEffect` `asOfDate` dependency; new "Prior closes" card with paginated snapshot list (empty-state UI when zero); new `FrozenSnapshotDetailCard` rendered inline (no new route per §4 test binding) on row click with Close button and frozen row values. **Frontend Vitest: 122 → 140 pass** (+18 tests, 0 regressions). Zero backend changes. Zero migration. Frontend operator routes 20 (unchanged — M14.2 page extended in place). **One §0.a M17.2 micro-decision recorded** — native `<input type="date">` in place of shadcn `Calendar` install (as-recommended per M10 §9). | `4235137` |
| M17.2 docs | 145 | `SESSION_145_m17_inc2_frontend.md` handoff. `00-START-NEXT-SESSION.md` refreshed for M17.3. | `dc064cf` |
| M17.3 Close-out | 145 | Documentation-only per M10.8 / M11.7 / M12.8 / M13.4 / M14.5 / M15.2 / M16.2 precedent. Six close-out docs (this retrospective + capability matrix §7r + implementation roadmap §Milestone 17 SHIPPED entry added + planning doc frontmatter flip `active` → `shipped` + M18 planning skeleton + session-start refresh) + coordinated commit landing all M17.3 docs. **Milestone 17 — Trial-balance materialization + as_of picker (monthly-close v1) — SHIPPED.** | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a clear re-entry
path.

**M17-specific deferrals** (all from
`MILESTONE_17_PLANNING.md` §3):

1. **Backdated-entry discrepancy surface.**
   §5.f Option A locks snapshots as immutable.
   When a backdated JournalEntry lands with
   `posted_at <= X` for an already-frozen
   snapshot at `X`, the frozen rows do not
   change but the live aggregate does. A
   "your frozen close no longer matches live"
   comparison view defers to a later period-
   close audit milestone. Re-entry: surfaces
   when operator evidence names the
   reconciliation pain.
2. **Auto-freeze on schedule.** §5.c Option A
   locks freeze as operator intent. Celery-
   beat auto-freeze at month-end would require
   answering "which timezone?" and "what if
   operator hasn't finalized adjustments?"
   Re-entry: a monthly-close automation
   milestone once operator rhythm evidence
   accumulates.
3. **Reopen / unfreeze workflow.** §5.f
   Option A snapshots are immutable at M17.
   Operators who realize a close was
   premature have no unfreeze path — they
   must freeze a new snapshot at a later
   moment. Re-entry: period-close reopen
   milestone with audit-log semantics.
4. **Period comparison view.** Rendering two
   frozen snapshots side-by-side ("May close
   vs June close", variance per account)
   defers. The list + detail endpoints ship
   at M17.1; the comparison UI would layer on
   top. Re-entry: a financial-reports
   milestone.
5. **Frozen snapshot as CSV / PDF export.**
   Operators may want to export closed months
   for auditor / CPA handoff. Defers to a
   reporting milestone. Detail endpoint ships
   in JSON at M17.1; export layers on top.
6. **Time-of-day picker.** §5.e Option B
   locks the picker at date-only. A time-of-
   day picker (for intra-day closes) defers.
   Re-entry: extend the picker component in
   place; server contract is already time-
   aware.
7. **Tenant timezone configuration.** M17
   assumes the dealership's timezone from
   the request context (Django `TIME_ZONE`).
   Per-dealership timezone configuration
   defers to a tenancy milestone.
8. **Freezing arbitrary future dates.** M17
   accepts any `as_of` value the picker
   emits, including future dates. Future
   dates produce a snapshot equivalent to
   `as_of=timezone.now()`. Technically valid
   but operationally weird; defers until
   evidence surfaces the need for a guard.
9. **Snapshot-source FK on comparison /
   audit trails.** No FK from downstream
   period-comparison entities back to
   snapshots (no downstream entities yet).
   Defer per M15 §3 item 9 posture.
10. **Snapshot immutability enforced at DB
    level.** M17 relies on service-layer
    discipline (`freeze_trial_balance` is
    the only write path). DB-level
    enforcement (e.g. a trigger rejecting
    UPDATE on `TrialBalanceSnapshotRow`)
    defers until evidence surfaces data-
    integrity risk.
11. **Materialized aggregate reports (P&L,
    balance sheet).** Trial balance is the
    raw substrate; P&L and balance-sheet
    reports layer on top. Defers to a
    financial-reports milestone.
12. **Snapshot detail versioning.** COA
    rename after freeze — frozen row stores
    `account_code` + `account_name` at
    freeze time. A "rename history"
    reconciliation view defers.

**Universal deferrals (any accounting
milestone):**

- Payroll (external service).
- W-2 / 1099 generation (external service).
- Year-end tax return preparation (external
  CPA).
- GAAP-compliant audited financial reporting
  (out of scope for platform v1).
- Direct DMS integration (belongs to a future
  vendor-integration milestone).

**Total deferrals at M17 close: 17** (12 M17-
specific + 5 universal). Matches M16's
deferral density within one — mixed
backend+frontend scope surfaces essentially
the same downstream deferral count as
backend-only sale-booking / payment-posting
milestones.

## 4. Deviations from planned scope

Three deviations. All net-additive. Zero
regressions.

1. **Sessions collapsed 145-148 → 145.** The
   planning skeleton at M16.2 sequenced M17
   across four calendar sessions (M17.0 at
   145, M17.1 at 146, M17.2 at 147, M17.3
   at 148). Per user direction "continue"
   after each increment landed, all four
   collapsed into SESSION_145. Session
   numbering reflects calendar sessions, not
   planning-sequence positions. Handoffs
   are preserved distinct
   (`SESSION_145_m17_inc0_planning.md` +
   `_inc1_backend` + `_inc2_frontend` +
   `_inc3_close` alongside) so downstream
   readers can still reconstruct the
   increment boundaries.
2. **Permission-class count correction.**
   The M16 retrospective + prior narrative
   docs recorded the permission-class count
   as "8." The actual count in
   `dealer_ai/permissions.py` is 7 (6
   starting with `Is*` + `ReadOnly`).
   Discovered at M17.1 when the
   zero-drift assertion test failed against
   the exact-count expectation. **The
   corrective test in M17.1 uses set
   equality on the class names**, not a
   raw count — captures the zero-drift
   invariant more robustly and prevents
   future miscounts. Historical narrative
   docs are preserved as-written per doc
   governance rule 5 (immutable historical
   records); the corrected count is
   documented at M17.1's handoff § doc note
   + this retrospective + M18 planning
   forward. Nine-milestone zero-drift streak
   holds against the corrected baseline.
3. **Native `<input type="date">` in place
   of shadcn `Calendar`.** M17 planning §7
   M17.2 named `npx shadcn add calendar` as
   an install step if the primitive wasn't
   present. At M17.2 open, the §0.a
   micro-decision surfaced the alternative:
   wrap the native date input in the
   existing shadcn `Input` primitive
   instead. Rationale: date-only mental
   model per §5.e Option B; no new
   dependency; OS-native picker fully
   accessible + trivially testable via
   Vitest `change` events; browser handles
   locale automatically. Recorded as §0.a
   M17.2 micro-decision — as-recommended
   per M10 §9 (does not count against
   streak). If operator evidence surfaces
   the need for a richer picker (multi-
   month, range, presets), swap in shadcn
   `Calendar` at that time.

## 5. Compatibility with existing surface

Every M1-M16 endpoint returns the same shape
it did at M16 close. Every M1-M16 service
verb signature is unchanged (M17 is purely
additive — new module + new models + new
endpoints; the only edits to existing files
are the additive extension of
`services/accounting/__init__.py` `__all__`,
`views_accounting.py` imports + views,
`urls.py` route additions, and the
`TrialBalanceSnapshot` → `TrialBalanceComputation`
dataclass rename which is confined to internal
callers).

Enumerated:

- **M1-M8 endpoints:** unchanged.
- **M9 sale endpoint:** unchanged.
- **M10-M12 endpoints:** unchanged.
- **M13.1 journal-entry endpoints:**
  unchanged.
- **M13.3 trial-balance endpoint:**
  unchanged. The endpoint already accepted
  `?as_of=` per M13.3 §0.a decision 4;
  M17.2 starts sending it on user input
  from the frontend. Endpoint contract
  preserved; a frontend that never sends
  the param continues to work.
- **M14.1 endpoints:** unchanged (list +
  cost-posting failures).
- **M14 UI surfaces:** the M14.3 journal-
  entry browser is unchanged; the M14.2
  trial-balance page is extended in place
  (new picker + freeze button + Prior closes
  card + inline detail). The M14.2 render
  contract is preserved — the same table
  shape + is_balanced chip + totals card
  render as before, with the new picker /
  freeze / history layered above and below.
- **M15 sale-booking:** unchanged.
- **M16 BHPH payment posting:** unchanged.
  The 11:00 detector continues to fire on
  its own schedule; M17 does not touch the
  BHPH write path.
- **Internal dataclass rename:** the
  `TrialBalanceSnapshot` frozen dataclass in
  `services/accounting/snapshot.py` renamed
  to `TrialBalanceComputation`. Every
  reader in the codebase updated in the
  same M17.1 commit. External API surface
  unaffected — the wire projection uses
  the same keys.
- **Tenancy carriers:** 47 → **49** (added
  `TrialBalanceSnapshot` +
  `TrialBalanceSnapshotRow`).
- **Permission classes:** **7 actual**
  (corrected from prior narrative doc's
  "8"). **Zero drift at M17.1 + M17.2** —
  no new permission classes; all three
  M17.1 endpoints reuse
  `IsSalesManagerOrOwnerAtActiveDealership`.
  Streak extends to **nine consecutive
  milestones**: M10 + M11 + M12 + M13 +
  M14 + M15 + M16 + M17.1 + M17.2 no
  class change.
- **Migrations:** `0043`–`0046` (+1 at
  M17.1 — two CreateModel + two
  AddConstraint in one migration).
- **Celery-beat task families:** 10
  (unchanged — no beat entry at M17 per
  §5.c Option A sync-sibling shape).
- **AI safety stack:** 17 scrub stages
  (unchanged — M17 has no LLM path).

## 6. Lessons

Six carry into M18+ planning.

1. **The §5-decisions-locked-at-open pattern
   held for an eighth milestone.** All six
   §5 decisions at M17.0 open confirmed as-
   recommended, matching
   M10/M11/M12/M13/M14/M15/M16 pattern.
   **70 planning-time as-recommended M5.1 →
   M17.0** across eight consecutive
   milestones now. Even the first mixed
   backend+frontend milestone since M14
   resolved cleanly at the six-decision
   surface. The framework generalizes across
   backend-only detector milestones,
   backend-only sibling milestones, and
   mixed-scope monthly-close milestones.

2. **Bundling entity + operator UI as one
   milestone is the right shape when neither
   half stands alone.** M17 explicitly folded
   `as_of` picker into Option E at M16.2
   close, converting what would have been two
   separate milestones (a materialization
   backend + a UX polish frontend) into one
   coherent operator-usable slice. Rationale
   validated at delivery: without the picker,
   the materialization has no operator
   consumer; without the materialization, the
   picker has nothing durable to record. The
   pattern applies to any "backend substrate
   + operator UI" pair where the value
   proposition requires both. Future
   candidates: comparison view + variance
   report backend (period-close audit
   milestone).

3. **Naming discipline pays for itself
   quickly.** The `TrialBalanceSnapshot`
   dataclass → `TrialBalanceComputation`
   rename at M17.1 was a §0.a micro-decision
   that took ~5 minutes to execute and
   prevented a persistent identifier
   collision between the transient
   computation and the durable materialized
   entity. Free the load-bearing name for
   the durable / user-facing concept; give
   the transient the descriptive name. If
   the codebase already had 20 downstream
   consumers of `TrialBalanceSnapshot`, the
   rename would have been more expensive
   but still worthwhile — the alternative
   (both types share a name, disambiguated
   by import path) is confusing to every
   future reader.

4. **`IntegrityError` → domain exception at
   the service boundary is a clean 409
   pattern.** M17.1's
   `freeze_trial_balance` wraps the
   `.create()` call in `try/except
   IntegrityError` and re-raises as
   `DuplicateTrialBalanceSnapshotError`.
   The `unique_together` constraint at the
   DB layer is the authoritative guard; the
   service-layer catch translates the raw
   DB error into a domain-meaningful signal
   that the endpoint layer maps to 409.
   This is a cleaner 409 shape than trying
   to pre-check existence (which has TOCTOU
   race conditions) and cleaner than
   surfacing the raw `IntegrityError` at
   the endpoint (which leaks DB
   implementation into the API contract).
   Future milestones with `unique_together`
   guards should follow the same pattern:
   catch at the service boundary, re-raise
   as a named domain exception, map to 409.

5. **Native browser primitives beat shadcn
   installs when the mental model is simple.**
   M17.2 planned `npx shadcn add calendar`
   but the §0.a micro-decision at M17.2 open
   swapped in a native `<input type="date">`
   wrapped in the existing shadcn `Input`
   primitive. Delivery cost was lower (no
   new dep install, no new component to
   maintain), test cost was lower (Vitest
   `change` events on a native input just
   work), and accessibility was higher (OS-
   native picker respects screen readers +
   locale). The right shape for "give me an
   ISO date" is a date input; the shadcn
   `Calendar` primitive earns its complexity
   only when the UX requires date ranges,
   multi-month views, or presets. Future
   milestones should default to native
   primitives + shadcn `Input` wrapper for
   simple form fields; escalate to purpose-
   built shadcn primitives only when
   evidence justifies.

6. **In-place page extension keeps the
   frontend route table stable.** M17.2
   extended `AccountingTrialBalancePage.tsx`
   with three new UI sections (Query
   controls card, Prior closes card, inline
   detail card) but shipped **zero new
   operator routes** — the M14.2 page
   grew four cards deep rather than
   splitting into separate routes.
   Rationale: the picker + freeze + prior
   closes + detail are all one workflow
   (the operator asks "what did the trial
   balance look like on May 31, and can I
   compare that to the current view?"), and
   the workflow is served best by a single
   page. Route bloat is a real cost —
   more routes = more nav decisions, more
   entry points, more state to preserve
   across navigation. Future accounting UX
   should default to in-place extension of
   the existing pages; new routes earn
   their complexity only when the workflow
   truly diverges.

## 7. Streak update

**70 planning-time as-recommended M5.1 →
M17.0.** Eight consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 + M16 +
M17) with every §5 decision confirmed as-
recommended at planning-time open. §0.a
implementation-time micro-decisions across
M17.1 + M17.2 (4 total: dataclass rename,
detail URL shape, picker default deferral,
native date input) do not count against the
streak per M10 §9.

The pattern that held:

1. Draft the §5 recommendations at planning
   close of the *previous* milestone.
2. Confirm at the next milestone's opening
   session.
3. Amend §0.a as micro-decisions surface per
   implementation session.
4. Never re-vote a §5 decision mid-milestone
   — file the amendment as §0.a instead.

## 8. What M17 unblocks for M18+

- **Monthly-close comparison view / period-
  close audit** is now unblocked. §5.f
  Option A immutable snapshots gave M17 a
  clean shape but left the "your frozen
  close no longer matches live" comparison
  view for a later milestone. The
  substrate is there (frozen snapshots +
  live aggregator + endpoint contracts);
  the comparison UI layers on top.
- **Financial-reports substrate (P&L,
  balance sheet) is unblocked.** Trial-
  balance materialization at M17 is the
  raw substrate; P&L and balance-sheet
  reports group accounts on top of frozen
  or live trial-balance data. Blocks on
  operator evidence naming the report
  priority.
- **CSV / PDF export of frozen snapshots
  is unblocked.** Detail endpoint ships
  JSON at M17.1; export layers on top for
  auditor / CPA handoff.
- **Auto-freeze on schedule.** Operator
  rhythm evidence from M17 usage will
  inform whether Celery-beat monthly-end
  auto-freeze is worth the operational
  contract complexity (timezone
  configuration, "have adjustments been
  finalized?" question).
- **Reopen / unfreeze workflow.**
  Operators who freeze prematurely have
  no unfreeze path today. Re-entry needs
  audit-log semantics (who, when, why,
  what changed).
- **M10 F&I chargeback GL reversal —
  pattern proven from three directions
  now.** M15 sync-sibling + M16 detector
  + M17 sync-sibling with
  `unique_together` guard. Chargeback
  is sync-sibling shape (operator intent
  per event); the `reverse_journal_entry`
  substrate is ready.
- **NSF / payment-reversal workflow.**
  Unchanged from M16 §8. GL side ready;
  operational contract needed.
- **Category-group-aware GL mapping** for
  the M13.2 detector — unchanged from
  M14/M15/M16 §8.
- **M14 UX polish** (journal-entry list
  filters, sidebar nav) — the `as_of`
  picker portion is now shipped at M17.2.
  Remaining polish (JE filters +
  sidebar nav) is a strong candidate for
  a batched UI-focused M18 or M19 per the
  M16.2 standing question.
- **Sale-side reversal workflow.**
  Unchanged from M15 §8. GL side ready;
  operational contract needed.
- **Post-sale VehicleCost variance
  handling.** Unchanged from M15 §8.
  Phantom Recon WIP balances on sold
  vehicles more visible in period-over-
  period comparison views.
- **Deposit / bank reconciliation
  workflow.** Unchanged from M16 §8.
  Trial-balance materialization now
  makes the 100000 Cash on Hand vs
  110000 Bank Operating separation more
  visible across period closes.
- **Method-aware fund-flow routing.**
  Unchanged from M16 §8.
- **BhphFee entity + late-fee GL posting.**
  Unchanged from M16 §8.
- **BHPH interest accrual detector
  (accrual-basis).** Unchanged from M16
  §8.

## 9. Standing question — is M18 (or M19) the right slot for an intentional UI-polish milestone?

Per `MILESTONE_17_PLANNING.md` §M16.2-close
refinement standing question:

> **Standing question for M17 close:** review
> at the end of M17 whether M18 or M19 should
> be an intentional UI-polish milestone (M14
> shape) to batch-consume Option G + any UX
> gaps surfaced from operator use of M15 +
> M16 + M17-shipped surfaces. Backend-only
> milestones consistently generate more
> UI/workflow deferrals than they consume; an
> occasional UI-focused milestone drains the
> backlog en masse (per M14's shape as
> validated against the M13 UI backlog).

**Signal accumulated during M17:**

- Option G reduced at M16.2-close bundling
  (`as_of` picker moved to Option E; only
  JE filters + sidebar nav remain in
  Option G).
- M17.2 extended M14.2 in place without
  needing a new route — the "in-place
  extension" pattern held. Option G's JE
  filters could follow the same pattern
  (extend `AccountingJournalEntryListPage`
  in place with filter controls) without
  demanding a full UI-focused milestone.
- Zero new UX-polish-shaped deferrals
  surfaced during M17 delivery. The
  operator-usable surface at M17 close
  is coherent + complete for the
  monthly-close v1 workflow.

**Recommendation to bring to M18.0 open:**
carry the standing question forward but
**do not preemptively lock M18 as a UI-
polish milestone.** M18 target selection
should follow the standard business-
priority pattern at M18.0 open. If
operator evidence + backlog density name
UI polish as the highest-value slot at
that time, M18 becomes the UX polish
milestone; otherwise Option G / JE filters
can layer as a sub-increment on a
backend milestone that touches the M14.3
page (per M14's compact "M14.4 UX polish"
sub-increment pattern within a larger
milestone).
