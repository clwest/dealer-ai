---
title: "Milestone 16 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_141 (post-M15-closeout)
milestone: 16
milestone_name: "TBD — user names target at SESSION_142 open"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_15_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_15_PLANNING.md
  - docs/roadmap/MILESTONE_14_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
---

# Milestone 16 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M15.2 close per standing user directive
> (M10.8 / M11.7 / M12.8 / M13.4 / M14.5 /
> M15.2 precedent). **M16 target milestone
> is TBD.** `IMPLEMENTATION_ROADMAP.md`
> §Milestone sequence ends at Milestone 15
> — the user names the M16 target at
> SESSION_142 M16.0 open, drawing from the
> M15 retrospective §8 unblocked-work list
> and any operational-evidence changes
> since M15 close.
>
> Full memo expansion + §5 decision surface
> + §7 sequencing refinement land at M16.0
> (SESSION_142) open. This document exists
> so SESSION_142 opens with a concrete
> starting point rather than a blank page.

## 0. Engineering practices to preserve from M2-M15

Same posture as M15.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M15 convention
  (404 cross-tenant, 409 state-machine /
  duplicate, 400 vocab / validation, 500
  broken-invariant `RuntimeError`
  subclasses per M15.1 §0.a decision 5).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in §0.a
  per M5-M15 precedent.
- **Additive extension over fork.**
  Follow M11.1 / M12.3 / M13.2 / M14.1 /
  M15.1 pattern for any additions to
  existing entities or verbs.
- **Every M16 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9-M15
  growth-only-list lesson. **Vocab-set
  assertions use exact equality** per
  M11 / M12 / M13 / M14 / M15 fixed-
  vocab lesson.
- **Read-only surfacer vs state-
  transitioning detector vs sync
  sibling-service** — pick the shape
  by whether the trigger is operator
  intent (sync sibling per M13 §5.d
  Option C + M15.1 proof), elapsed
  condition (detector per M11-M14
  precedent), or read-only enumeration
  (verb per M13.3 / M14.1 precedent).
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another (per M12
  §6 lesson 11, M13.2, M14, and M15
  §6 lesson 2). Nested atomic is a
  no-op inside an existing transaction.
- **Denormalize at write; recompute in
  detectors; refresh AFTER sibling
  writes if the denormalized value
  depends on them.** Per M12 §6 lesson
  4 / M13.2 / M14 posture / M15 §6
  lesson 6 (`gross_realized` refresh
  after cost flush).
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 / M13.1
  / M14.1 posture.
- **Detector idempotency within runs.**
  Per M12 §6 lesson 8 / M13.2 posture.
- **Idempotency short-circuit BEFORE
  sibling writes.** Per M15 pattern —
  duplicate detection short-circuits
  before any GL work fires, so a
  retry never double-posts.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  (or the composed
  `IsReconManagerSalesManagerOrOwnerAt
  ActiveDealership`) by default (seven
  consecutive milestones now, per M15
  §6 lesson 7).
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson 15
  / M13.3 / M14.1 posture.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8 / M14 lesson 6.
- **Money on the wire is Decimal-as-
  string** per M9.5 / M10.1 / M12
  BHPH / M13 / M14 / M15 convention.
- **Zero-noise render posture for
  count-based cards.** Per M14 §6
  lesson 6.
- **Client-side validation matches
  server-side validation with matching
  trim posture.** Per M14 §6 lesson 5.
- **Browser E2E verification per
  frontend increment.** Per M14 §6
  lesson 4.
- **Frontend Vitest discipline.** Per
  M11 / M12 / M14 precedent.
- **Test-fixture invariants match
  migration invariants.** Per M15 §6
  lesson 3 — if a migration seeds
  per-tenant data, the shared
  `make_dealership` helper should
  seed too.

### 0.a Change log — resolved decisions

*(Populated at M16.0 open + per-
increment as §0.a amendments.)*

## 1. Business questions this milestone might answer

*Draft skeleton — user selects the M16
target at SESSION_142 open. The M15
retrospective §8 lists the substrates
M15 unblocked or left open; the M14
§8 list also remains valid (most
still unaddressed after M15):*

| # | Candidate M16 target | Anchor |
|---|---|---|
| A | **M10 F&I chargeback GL reversal** — chargebacks are already reversal-shaped in the operational surface. Substrate ready; M15 proved out the sync-sibling pattern that M10 chargeback would follow. Every recorded chargeback posts a matching reversal JournalEntry via `services/accounting/reverse_journal_entry`. | M13 retrospective §8 + M14 §8 + M15 §8 + M15 §6 lesson 2 |
| B | **M12 BHPH payment GL post** — detector at 11:00 project-time daily (next open slot after M13.2 10:00). Every unposted BhphPayment produces a matching journal entry. Same posture as M13.2 M2 cost detector. Detector-half of the M13 §5.d Option C hybrid; M15 shipped the sync half. | M13 retrospective §8 + M14 §8 + M15 §8 |
| C | **Trial-balance materialization + monthly close workflow** — `TrialBalanceSnapshot` entity + freeze verb over the M13.3 pure recompute aggregator. Enables period-over-period comparisons that pure recompute cannot. The M14.2 trial-balance page could grow an `as_of` picker as part of this. | M13 retrospective §3 item 2 + M14 §3 deferral 7 + M15 §8 |
| D | **Category-group-aware GL mapping** for the M13.2 detector. Now that M14.4's failure card gives operators visibility into detector misses AND M15 sales activity accumulates in Recon WIP, miscoding evidence is available. Flooring → floor-plan accounts, admin → rent/ad, etc. | M13 retrospective §3 item 1 + M14 §8 + M15 §8 |
| E | **M14 UX polish** — journal-entry list filters (date range, posted_by, reversal-only, description search) + `as_of` picker on trial-balance + sidebar nav entry for accounting. Layers atop the M14 shipped surface as operator evidence surfaces the need — and M15 sale-booking activity now makes that operator evidence real. | M14 retrospective §3 items 1 + 2 + 4 + M15 §8 |
| F | **Cost-of-sale variance handling.** M15 §3 item 11 deferred this pending operator evidence. Post-sale VehicleCost rows currently create phantom Recon WIP balances for sold vehicles; a category-aware mapping or a redirect-to-COGS approach clears the phantoms. | M15 §3 item 11 + M15 §8 |
| G | **Sale-reversal workflow.** M15 §3 item 8 deferred pending an operational contract definition. The GL side (`reverse_journal_entry`) is ready; the operational side (what happens to the Sale row, the Vehicle status, downstream M9.3 analytics) needs a spec. | M15 §3 item 8 + M15 §8 |
| H | **Non-accounting target** user names at open based on operational evidence not visible in the M15 / M14 retrospectives. | — |

## 2. What existing primitives extend

*Draft skeleton per candidate M16
targets.*

- M13.1 `services/accounting/
  post_journal_entry` is the atomic
  sibling target for candidates A + B.
- M13.1 `reverse_journal_entry` is
  the atomic sibling target for
  candidates A + G.
- M13.3 `compute_trial_balance` +
  M14.1 `list_journal_entries` are
  the source-of-truth verbs for
  candidate C materialization + E
  filters.
- M13.1 / M13.3 / M14.1 admin
  endpoints are the data source for
  candidate E UX polish.
- M15.1 `services/accounting/
  sale_booking.post_sale_booking_journal`
  is the pattern template for
  candidates A + B — a new sibling
  module per M15.1 shape.
- M15.1 `record_sale` extension
  pattern (nested `@transaction.atomic`
  + sibling call + optional
  `posted_by_user` kwarg) is the
  template for M10 chargeback and
  M12 payment write-path extensions.
- M13.2 `post_all_unposted_costs_
  for_dealership` orchestrator is
  the template for candidate B
  detector; same posture also
  supports candidate D category-
  group mapping.
- M14.4 `CostPostingFailuresCard`
  is the surface that surfaces
  candidate D evidence.

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton — locks at M16.0
open based on user selection of the
M16 target.*

Universal deferrals (regardless of
target):

- Payroll (external service).
- W-2 / 1099 generation (external
  service).
- Year-end tax return preparation
  (external CPA).
- GAAP-compliant audited financial
  reporting (out of scope for
  platform v1).
- Direct DMS integration (belongs
  to a future vendor-integration
  milestone).

## 4. What existing tests bind

*Populated at M16.0 open per M15
§4 pattern.*

## 5. Load-bearing decisions to resolve

*Draft skeleton. Full decision
surface lands at M16.0 open after
user names the M16 target.*

### 5.a `[NEEDS-DECISION-BEFORE-M16.0]` — Milestone target selection

**Question.** Which of the candidate
M16 targets (§1 above) defines M16
scope?

**Recommendation drafted.** *Awaits
user input at SESSION_142 open.* The
M15 retrospective §8 unblocked-work
list is the primary anchor; the M14
retrospective §8 remains valid;
operator evidence since M15 close
may reshape priorities.

Options (from §1 above):

- **Option A** — M10 F&I chargeback GL reversal.
- **Option B** — M12 BHPH payment GL post.
- **Option C** — Trial-balance materialization + monthly close.
- **Option D** — Category-group-aware GL mapping.
- **Option E** — M14 UX polish.
- **Option F** — Cost-of-sale variance handling.
- **Option G** — Sale-reversal workflow.
- **Option H** — Non-accounting target
  (user-named at open).

### 5.b–5.f `[NEEDS-DECISION-BEFORE-M16.0]`

*Additional load-bearing decisions
land at M16.0 open, shaped by the
§5.a target selection. Historical
§5 counts have been 6 for M10 /
M11 / M12 / M13 / M14 / M15; expect
4-8 for M16 depending on target
complexity.*

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §6 (eight lessons carry into M16) +
   §8 (M15 unblocked work)
6. `docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`
   §8 (M14 unblocked work — still
   mostly valid after M15)
7. `docs/CAPABILITY_MATRIX.md` §7p
8. Domain-specific research doc per
   the M16 target selected at §5.a.

## 7. Sequencing draft

*Initial draft — user refinement
expected at M16.0 open once §5.a
target is confirmed.*

### Increment 0 (M16.0) — Planning refinement + decision review

**Scope.** SESSION_142. Confirm §5
decisions with user; expand this
skeleton into a full memo; refine
§7 sequencing.

### Increments 1..N (M16.1..M16.N-1) — implementation

*Increment structure locks at M16.0
based on the confirmed target.
Historical M15 shipped one code +
closeout (three total including
M15.0 planning) per backend-only
scope. M14 shipped four code +
closeout (six total). M12 shipped
eight. Complexity-appropriate scope
discipline holds — small complete
increments per Project Rule 4.*

### Increment N (M16.N) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7q + roadmap
flip + M17 planning skeleton per
standing user directive.

---

*Draft-only. Full expansion at
SESSION_142 (M16.0) open with the
user.*
