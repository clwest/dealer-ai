---
title: "Milestone 18 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_145 (post-M17-closeout)
milestone: 18
milestone_name: "TBD — user names target at SESSION_146 open"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_17_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_17_PLANNING.md
  - docs/roadmap/MILESTONE_16_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
---

# Milestone 18 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at M17.3
> close per standing user directive (M10.8 /
> M11.7 / M12.8 / M13.4 / M14.5 / M15.2 / M16.2
> / M17.3 precedent). **M18 target milestone is
> TBD.** `IMPLEMENTATION_ROADMAP.md` §Milestone
> sequence ends at Milestone 17 — the user
> names the M18 target at SESSION_146 M18.0
> open, drawing from the M17 retrospective §8
> unblocked-work list, the still-valid M16 §8
> items, and any operational-evidence changes
> since M17 close.
>
> Full memo expansion + §5 decision surface +
> §7 sequencing refinement land at M18.0
> (SESSION_146) open. This document exists so
> SESSION_146 opens with a concrete starting
> point rather than a blank page.
>
> **Standing question carried forward from M17
> close** (`MILESTONE_17_RETROSPECTIVE.md` §9):
> is M18 or M19 the right slot for an
> intentional UI-polish milestone? M17's
> recommendation was to carry the question
> forward but NOT preemptively lock M18 as a
> UI-polish milestone — target selection at
> M18.0 should follow the standard business-
> priority pattern. If operator evidence +
> backlog density name UI polish as the
> highest-value slot at M18.0 open, M18
> becomes the UX polish milestone; otherwise
> Option G / JE filters can layer as a sub-
> increment on a backend milestone that
> touches the M14.3 page (per M14's compact
> "M14.4 UX polish" sub-increment pattern).

## 0. Engineering practices to preserve from M2-M17

Same posture as M17.0. Non-negotiable:

- **Backend-first architecture.** No business
  logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct HTTP
  statuses** per M9-M17 convention (404
  cross-tenant, 409 state-machine / duplicate,
  400 vocab / validation, 500 broken-invariant
  `RuntimeError` subclasses per M15.1 + M16.1
  + M17.1 posture; new-at-M17:
  `DuplicateTrialBalanceSnapshotError`
  demonstrated the `IntegrityError` →
  domain-exception → 409 pattern at the
  service boundary).
- **Load-bearing decisions get user review
  BEFORE code.** Present with recommendation
  + trade-offs; user confirms or overrides;
  record in §0.a per M5-M17 precedent.
- **Additive extension over fork.** Follow
  M11.1 / M12.3 / M13.2 / M14.1 / M15.1 /
  M16.1 / M17.1 pattern for any additions to
  existing entities or verbs.
- **Every M18 test asserting tenant-carrier /
  permission-class / endpoint counts uses
  `>=N`** per M9-M17 growth-only-list lesson.
  **Vocab-set + permission-class-set
  assertions use exact equality** per
  M11-M17 fixed-vocab lesson (M17.1 corrected
  the prior narrative doc's permission-class
  miscount and pinned the actual set for
  future zero-drift enforcement).
- **Read-only surfacer vs state-transitioning
  detector vs sync sibling-service** — pick
  the shape by trigger: operator intent
  (sync sibling per M13 §5.d Option C +
  M15.1 + M17.1 proof), elapsed condition
  (detector per M11-M14 + M16.1 proof),
  read-only enumeration (verb per M13.3 /
  M14.1 / M17.1 precedent).
- **Atomic sibling-service boundary
  crossings** — wrap in `@transaction.atomic`.
- **Denormalize at write; recompute in
  detectors; refresh AFTER sibling writes.**
- **Split pure verbs from write verbs.**
- **Zero-drift permission-class posture.**
  Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default. **Nine consecutive milestones
  now** per M17 §6 lesson 5. M18 must not
  add a new permission class without
  evidence justification.
- **Broken-invariant guards as cross-
  milestone contracts.** Per M16 §6 lesson 4
  + M17.1
  `DuplicateTrialBalanceSnapshotError`.
  Pattern examples:
  `MissingDefaultAccountError`,
  `UnmappedFinanceTypeError`,
  `UnexpectedBhphPaymentFeesError`,
  `DuplicateTrialBalanceSnapshotError`.
- **Duplicate account-code constants across
  accounting submodules** per M15.1 + M16.1
  + M17.1 posture. Evidence gate for a
  shared-constants module still not tripped.
- **Frozen dataclass output for aggregators.**
  Per M12 §6 lesson 15 / M13.3 / M14.1 /
  M17.1 (`TrialBalanceSnapshotListPage`).
- **Naming discipline** per M17 §6 lesson 3.
  When a durable persisted entity + a
  transient computation share a natural
  name, the durable entity earns the load-
  bearing name; the transient gets the
  descriptive name (e.g. M17's
  `TrialBalanceSnapshot` model +
  `TrialBalanceComputation` dataclass).
- **`IntegrityError` → domain exception at
  service boundary** per M17 §6 lesson 4.
  Wrap `.create()` in `try/except
  IntegrityError`; re-raise as a named
  domain exception; endpoint maps to 409.
- **Zero-portfolio semantics as first-class
  response state.** Per M13 §6 lesson 8 /
  M14 lesson 6 / M16.1 / M17.1.
- **Money on the wire is Decimal-as-string**
  per M9-M17 convention.
- **Test-fixture invariants match migration
  invariants.** Per M15 §6 lesson 3 + M16.1
  + M17.1 verified — `make_dealership`
  seeds default COA.
- **In-place page extension over new route**
  per M17 §6 lesson 6. Frontend operator
  routes stay at 20 unless the workflow
  truly diverges.
- **Native browser primitives + shadcn
  `Input` wrapper as the default** per M17
  §6 lesson 5. Escalate to purpose-built
  shadcn primitives only when evidence
  justifies (multi-month, range, presets).

### 0.a Change log — resolved decisions

*(Populated at M18.0 open + per-increment
as §0.a amendments.)*

## 1. Business questions this milestone might answer

*Draft skeleton — user selects the M18 target
at SESSION_146 open. The M17 retrospective §8
lists the substrates M17 unblocked or left
open; the M16 §8 list also remains largely
valid (most items still unaddressed after M17
except the trial-balance materialization +
`as_of` picker portion just shipped):*

| # | Candidate M18 target | Anchor |
|---|---|---|
| A | **M10 F&I chargeback GL reversal** — pattern proven from three directions now (M15 sync-sibling + M16 detector + M17 sync-sibling with unique guard). Chargeback semantics — operator-triggered event → sync-sibling per M15 pattern. `reverse_journal_entry` already ready. | M15 §8 + M16 §8 + M17 §8 |
| B | **BhphFee entity + late-fee GL posting** — M16.1's `UnexpectedBhphPaymentFeesError` guard makes the contract explicit. When BhphFee ships, extend `post_bhph_payment_journal` with a fee-income line + remove the guard. | M16 §8 + M17 §8 |
| C | **Deposit / bank reconciliation workflow** — M16's phantom 100000 Cash on Hand growth + M17's period-close visibility together sharpen the reclassification pain. Method-aware fund-flow routing is the substrate half; the reclassification workflow is the operational half. | M16 §8 + M17 §8 |
| D | **NSF / payment-reversal workflow** — ACH failures + returned payments need operational contract + GL wiring via `reverse_journal_entry`. | M16 §8 + M17 §8 |
| E | **Period-close comparison view / audit** — M17 §8 explicitly named this. Now that snapshots are durable + immutable, the "your frozen close no longer matches live" comparison view is the natural next slice. Substrate ready; the comparison UI + variance report layer on top. | M17 §8 |
| F | **Financial-reports substrate (P&L, balance sheet)** — trial-balance materialization at M17 is the raw substrate. P&L and balance-sheet reports group accounts on top. Layers cleanly on frozen or live trial-balance data. | M17 §8 |
| G | **CSV / PDF export of frozen snapshots** — for auditor / CPA handoff. Detail endpoint returns JSON at M17.1; export is a projection layer. | M17 §8 |
| H | **Auto-freeze on schedule** — M17 §5.c Option A locked sync-sibling. Auto-freeze at month-end requires timezone configuration + "have adjustments been finalized?" contract. Operator rhythm evidence from M17 usage may inform. | M17 §8 |
| I | **Reopen / unfreeze workflow** — operators who freeze prematurely have no path today. Needs audit-log semantics (who, when, why, what changed). | M17 §8 |
| J | **Category-group-aware GL mapping** for the M13.2 detector — remains unblocked. Miscoding evidence continues to accumulate across three daily-posting streams. | M14 §8 + M15 §8 + M16 §8 + M17 §8 |
| K | **M14 UX polish** (journal-entry list filters + sidebar nav) — the `as_of` picker portion shipped at M17.2. Remaining polish (JE filters + sidebar nav) can be batched here per M17 §9 standing question — OR layered as a sub-increment on a backend milestone that touches the M14.3 page. | M14 §8 + M15 §8 + M16 §8 + M17 §8 + M17 §9 |
| L | **Cost-of-sale variance handling** — M15 §3 item 11 deferral. Post-sale VehicleCost phantom balances more visible after M17 period-close comparison. | M15 §3 item 11 + M17 §8 |
| M | **Sale-reversal workflow** — M15 §3 item 8 deferral. GL side ready; operational contract needed. | M15 §3 item 8 + M17 §8 |
| N | **BHPH interest accrual detector (accrual-basis)** — M16 is cash-basis. Period-end accrual is a natural follow-on now that period-close materialization exists at M17. | M16 §8 + M17 §8 |
| O | **Non-accounting target** user names at open based on operational evidence not visible in M15 / M16 / M17 retrospectives. | — |

## 2. What existing primitives extend

*Draft skeleton per candidate M18 targets.*

- M13.1 `services/accounting/post_journal_entry` is the
  atomic sibling target for candidates A + B + C + N.
- M13.1 `reverse_journal_entry` is the atomic sibling
  target for candidates A + D + M.
- M13.3 `compute_trial_balance` + M17.1 frozen snapshots
  are the source-of-truth for candidates E + F + G.
- M14.1 `list_journal_entries` is the source-of-truth
  for candidate K (JE filters).
- M17.1 `services/accounting/trial_balance_close` is the
  pattern template for candidates E + F (both extend the
  frozen-snapshot surface).
- M15.1 `services/accounting/sale_booking` is the
  pattern template for sync-sibling candidates A + M.
- M16.1 `services/accounting/bhph_payment` is the pattern
  template for detector candidates D (if batched) + N.
- M13.2 `post_all_unposted_costs_for_dealership` + M16.1
  `post_all_unposted_bhph_payments_for_dealership`
  orchestrators are the templates for candidate J.
- M14.4 `CostPostingFailuresCard` is the surface that
  surfaces candidate J evidence.
- M14.2 `AccountingTrialBalancePage` (extended at M17.2)
  is the extension target for candidate E period-close
  comparison view (in-place per M17 §6 lesson 6).
- shadcn `Input` + native browser primitives (per M17 §6
  lesson 5) are the default for form fields on new UI.

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton — locks at M18.0 open based on
user selection of the M18 target.*

Universal deferrals (regardless of target):

- Payroll (external service).
- W-2 / 1099 generation (external service).
- Year-end tax return preparation (external
  CPA).
- GAAP-compliant audited financial reporting
  (out of scope for platform v1).
- Direct DMS integration (belongs to a future
  vendor-integration milestone).

## 4. What existing tests bind

*Populated at M18.0 open per M17 §4 pattern.*

## 5. Load-bearing decisions to resolve

*Draft skeleton. Full decision surface lands at
M18.0 open after user names the M18 target.*

### 5.a `[NEEDS-DECISION-BEFORE-M18.0]` — Milestone target selection

**Question.** Which of the candidate M18
targets (§1 above) defines M18 scope?

**Recommendation drafted.** *Awaits user input
at SESSION_146 open.* The M17 retrospective §8
unblocked-work list is the primary anchor; the
M16 §8 remains partly valid (items other than
the trial-balance / `as_of` portion just
shipped); operator evidence since M17 close
may reshape priorities. **Standing question
from M17 §9 also carries** — should M18 be an
intentional UI-polish milestone?

Options (from §1 above):

- **Option A** — M10 F&I chargeback GL reversal.
- **Option B** — BhphFee entity + late-fee GL posting.
- **Option C** — Deposit / bank reconciliation workflow.
- **Option D** — NSF / payment-reversal workflow.
- **Option E** — Period-close comparison view / audit.
- **Option F** — Financial-reports substrate (P&L, balance sheet).
- **Option G** — CSV / PDF export of frozen snapshots.
- **Option H** — Auto-freeze on schedule.
- **Option I** — Reopen / unfreeze workflow.
- **Option J** — Category-group-aware GL mapping.
- **Option K** — M14 UX polish (JE filters + sidebar nav).
- **Option L** — Cost-of-sale variance handling.
- **Option M** — Sale-reversal workflow.
- **Option N** — BHPH interest accrual detector (accrual-basis).
- **Option O** — Non-accounting target (user-named at open).

### 5.b–5.f `[NEEDS-DECISION-BEFORE-M18.0]`

*Additional load-bearing decisions land at
M18.0 open, shaped by the §5.a target selection.
Historical §5 counts have been 6 for M10 / M11 /
M12 / M13 / M14 / M15 / M16 / M17; expect
4-8 for M18 depending on target complexity.*

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   §6 (six lessons carry into M18) + §8
   (M17 unblocked work) + §9 (standing
   question)
6. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
   §8 (M16 unblocked work — still partly
   valid after M17)
7. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §8
8. `docs/CAPABILITY_MATRIX.md` §7r
9. Domain-specific research doc per the M18
   target selected at §5.a.

## 7. Sequencing draft

*Initial draft — user refinement expected at
M18.0 open once §5.a target is confirmed.*

### Increment 0 (M18.0) — Planning refinement + decision review

**Scope.** SESSION_146. Confirm §5 decisions
with user; expand this skeleton into a full
memo; refine §7 sequencing.

### Increments 1..N (M18.1..M18.N-1) — implementation

*Increment structure locks at M18.0 based on
the confirmed target. Historical M15 + M16
each shipped one code + closeout (three total
including planning) per backend-only scope.
M17 shipped two code + closeout (four total)
per mixed backend+frontend scope. M14 shipped
four code + closeout (six total). M12 shipped
eight. Complexity-appropriate scope discipline
holds — small complete increments per Project
Rule 4.*

### Increment N (M18.N) — Close-out

**Scope.** Docs. Retrospective + capability
matrix §7s + roadmap flip + M19 planning
skeleton per standing user directive.

---

*Draft-only. Full expansion at SESSION_146
(M18.0) open with the user.*
