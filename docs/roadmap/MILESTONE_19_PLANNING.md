---
title: "Milestone 19 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_152 (post-M18-closeout)
milestone: 19
milestone_name: "TBD — user names target at SESSION_153 open"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_18_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_18_PLANNING.md
  - docs/roadmap/MILESTONE_17_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
---

# Milestone 19 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M18.6 close per standing user directive
> (M10.8 / M11.7 / M12.8 / M13.4 / M14.5 /
> M15.2 / M16.2 / M17.3 / M18.6 precedent).
> **M19 target milestone is TBD.**
> `IMPLEMENTATION_ROADMAP.md` §Milestone
> sequence ends at Milestone 18 — the user
> names the M19 target at SESSION_153 M19.0
> open.
>
> **Distinctive shape at M19.0:** M18
> shipped **validation infrastructure**.
> The M19 target should be informed by
> **tester feedback** — real operator
> observations from founder-led pilot
> sessions that used the M18 demo stores +
> daily briefs. If Chris has run tester
> sessions by M19.0 open, the M18.5 CSV
> export becomes primary planning input.
> If not, the question carries per M18 §9
> standing question.
>
> Full memo expansion + §5 decision surface
> + §7 sequencing refinement land at M19.0
> (SESSION_153) open.

## 0. Engineering practices to preserve from M2-M18

Same posture as M18.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct HTTP
  statuses** per M9-M18 convention (404
  cross-tenant, 409 state-machine /
  duplicate, 400 vocab / validation, 500
  broken-invariant `RuntimeError`
  subclasses per M15.1 + M16.1 + M17.1 +
  M18.1 posture).
- **Load-bearing decisions get user review
  BEFORE code.** Present with recommendation
  + trade-offs; user confirms or overrides;
  record in §0.a per M5-M18 precedent.
- **Additive extension over fork.** Follow
  M11.1 / M12.3 / M13.2 / M14.1 / M15.1 /
  M16.1 / M17.1 / M18.1 pattern.
- **Every M19 test asserting tenant-carrier
  / permission-class / endpoint counts uses
  `>=N`** per M9-M18 growth-only-list
  lesson. **Vocab-set + permission-class-set
  assertions use exact equality** per
  M11-M18 fixed-vocab lesson.
- **Read-only surfacer vs state-transitioning
  detector vs sync sibling-service** — pick
  the shape by trigger: operator intent (sync
  sibling per M13 §5.d Option C + M15.1 +
  M17.1 proof), elapsed condition (detector
  per M11-M14 + M16.1 proof), read-only
  enumeration (verb per M13.3 / M14.1 /
  M17.1 precedent).
- **Atomic sibling-service boundary
  crossings.**
- **Denormalize at write; recompute in
  detectors; refresh AFTER sibling writes.**
- **Split pure verbs from write verbs.**
- **Zero-drift permission-class posture.**
  Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default. **Fourteen consecutive
  milestones now** per M18 §6 lesson 7.
- **Broken-invariant guards as cross-
  milestone contracts.** Per M17 §6 lesson
  4 + M18 §6 lesson 4.
- **Naming discipline** per M17 §6 lesson 3.
- **`IntegrityError` → domain exception at
  service boundary** per M17 §6 lesson 4.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8 / M14 lesson 6 / M16.1 / M17.1
  / M18.4 zero-portfolio archetype freeze.
- **Money on the wire is Decimal-as-
  string** per M9-M18 convention.
- **Test-fixture invariants match
  migration invariants.** Per M15 §6
  lesson 3 + M16.1 + M17.1 + M18.1
  verified.
- **In-place page extension over new
  route** per M17 §6 lesson 6. Frontend
  operator routes stay at 20 unless the
  workflow truly diverges.
- **Native browser primitives + shadcn
  `Input` wrapper as the default** per
  M17 §6 lesson 5.
- **Coherence contract per M18 §6 lesson
  2** — if M19 introduces new persisted
  entities that participate in scenario
  briefs, those entities should tell
  connected operational stories with
  existing entities.
- **Scanner tests for guard-by-
  construction contracts** per M18 §6
  lesson 3.
- **Belt-and-suspenders guards** per
  M17 §6 lesson 4 + M18 §6 lesson 4.

### 0.a Change log — resolved decisions

*(Populated at M19.0 open + per-increment
as §0.a amendments.)*

## 1. Business questions this milestone might answer

*Draft skeleton — user selects the M19
target at SESSION_153 open. The M18
retrospective §8 lists what M18
unblocked; the M17 §8 list also
remains valid (most items still open):*

| # | Candidate M19 target | Anchor |
|---|---|---|
| **T** | **Process real tester feedback** — implement the two or three highest-signal items from the M18.5 CSV export. Scope depends on volume + quality of feedback. **Primary candidate if Chris has run tester sessions by M19.0 open.** | M18 §9 standing question |
| U | Hosted-demo substrate — public self-serve demo signup + tester-tracking dashboard. Deferred at M18 §3 item 1. | M18 §3 item 1 |
| V | Pilot-customer onboarding — real-data onboarding for testers who convert. Deferred at M18 §3 item 12. | M18 §3 item 12 |
| A | M10 F&I chargeback GL reversal — pattern proven from three directions now (M15 sync-sibling + M16 detector + M17 sync-sibling with unique guard). | M15 §8 + M16 §8 + M17 §8 + M18 §8 |
| B | BhphFee entity + late-fee GL posting — M16.1's `UnexpectedBhphPaymentFeesError` guard makes the contract explicit. | M16 §8 + M17 §8 + M18 §8 |
| C | Deposit / bank reconciliation workflow — method-aware fund-flow + Cash-on-Hand → Bank reclass. M16's phantom 100000 Cash on Hand growth + M17's period-close visibility together sharpen the pain. | M16 §8 + M17 §8 + M18 §8 |
| D | NSF / payment-reversal workflow — operator-triggered ACH-return reversal via `reverse_journal_entry`. | M16 §8 + M17 §8 + M18 §8 |
| E | Period-close comparison view / audit — directly unblocked by M17 materialization. Frozen vs live comparison + variance UI. | M17 §8 + M18 §8 |
| F | Financial-reports substrate (P&L, balance sheet) — layers on M17 materialization. | M17 §8 + M18 §8 |
| G | CSV / PDF export of frozen snapshots — for auditor / CPA handoff. | M17 §8 + M18 §8 |
| H | Auto-freeze on schedule — Celery-beat monthly-end. | M17 §8 + M18 §8 |
| I | Reopen / unfreeze workflow — needs audit-log semantics. | M17 §8 + M18 §8 |
| J | Category-group-aware GL mapping — fixes M13.2 detector miscoding. | M14 §8 + M15 §8 + M16 §8 + M17 §8 + M18 §8 |
| K | M14 UX polish (JE filters + sidebar nav) — `as_of` picker portion shipped at M17.2. | M14 §8 + M15 §8 + M16 §8 + M17 §8 + M18 §8 |
| L | Cost-of-sale variance handling. | M15 §3 item 11 + M17 §8 + M18 §8 |
| M | Sale-reversal workflow — GL side ready; operational contract needed. | M15 §3 item 8 + M17 §8 + M18 §8 |
| N | BHPH interest accrual detector (accrual-basis) — month-end close primitive. | M16 §8 + M17 §8 + M18 §8 |
| O | **Non-accounting target** — user names at open based on operational evidence or tester feedback not visible in prior retrospectives. | — |

## 2. What existing primitives extend

*Draft skeleton per candidate M19 targets.*

Most candidates layer on M13-M17 accounting
substrate + M11-M12 CRM/BHPH substrate.
Option T (tester-feedback processing) is
distinct — its "extends" list is
determined at M19.0 by what feedback
categories dominate.

Common extension points:

- M13.1 `services/accounting/post_journal_entry`
  — the atomic sibling target for A + B +
  C + N.
- M13.1 `reverse_journal_entry` — the
  atomic sibling target for A + D + M.
- M13.3 `compute_trial_balance` + M17.1
  frozen snapshots — the source of truth
  for E + F + G.
- M14.1 `list_journal_entries` — the
  source of truth for K JE filters.
- M17.1 `services/accounting/trial_balance_close`
  — pattern template for E period-close
  comparison + F financial reports.
- M15.1 `services/accounting/sale_booking`
  — pattern template for A + M sync-
  sibling shape.
- M16.1
  `services/accounting/bhph_payment` —
  pattern template for D (if batched) + N
  detector-shaped.
- M18.1 `services/demo_store/` — the
  validation substrate that produced the
  tester feedback. Option T consumes the
  feedback export.
- Existing scenario briefs at
  `services/demo_store/briefs/` — any
  Option T scope may layer as new brief
  content or in-brief scenario
  refinements.

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton — locks at M19.0 open based
on user selection of the M19 target.*

Universal deferrals (regardless of target):

- Payroll (external service).
- W-2 / 1099 generation (external service).
- Year-end tax return preparation (external
  CPA).
- GAAP-compliant audited financial reporting
  (out of scope for platform v1).
- Direct DMS integration (belongs to a
  future vendor-integration milestone).

## 4. What existing tests bind

*Populated at M19.0 open per M17 §4 + M18
§4 pattern.*

## 5. Load-bearing decisions to resolve

*Draft skeleton. Full decision surface
lands at M19.0 open after user names the
M19 target.*

### 5.a `[NEEDS-DECISION-BEFORE-M19.0]` — Milestone target selection

**Question.** Which of the candidate M19
targets (§1 above) defines M19 scope?
Does tester feedback exist to inform the
decision?

**Recommendation drafted.** *Awaits user
input at SESSION_153 open.* If tester
feedback has landed via M18.5 CSV
export, Option T is the primary
candidate — scope depends on which
feedback categories dominate. If tester
sessions haven't yet happened, target
selection follows the standard
business-priority pattern from the M17
+ M18 §8 unblocked-work lists.

Options (from §1 above): T (tester
feedback processing) + U (hosted-demo)
+ V (pilot-customer onboarding) + A
through N (still-valid accounting
candidates from M17 §8) + O (non-
accounting user-named at open).

### 5.b–5.f `[NEEDS-DECISION-BEFORE-M19.0]`

*Additional load-bearing decisions land
at M19.0 open, shaped by the §5.a target
selection. Historical §5 counts have been
6 for M10 / M11 / M12 / M13 / M14 / M15 /
M16 / M17; M18 was 7. Expect 4-8 for M19
depending on target complexity.*

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §6 (seven lessons carry into M19) +
   §8 (M18 unblocks) + §9 (standing
   question).
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   §8 (M17 unblocked work — still mostly
   valid after M18).
7. `docs/CAPABILITY_MATRIX.md` §7s (M18
   shipped surface — the validation
   substrate that produced the tester
   feedback if any lands).
8. **Tester feedback CSV** (from M18.5
   `demo_store export_feedback`) —
   authoritative source if tester
   sessions have happened.
9. Domain-specific research doc per the
   M19 target selected at §5.a.

## 7. Sequencing draft

*Initial draft — user refinement expected
at M19.0 open once §5.a target is
confirmed.*

### Increment 0 (M19.0) — Planning refinement + decision review

**Scope.** SESSION_153. Confirm §5
decisions with user; expand this
skeleton into a full memo; refine §7
sequencing.

### Increments 1..N (M19.1..M19.N-1) — implementation

*Increment structure locks at M19.0
based on the confirmed target.
Historical M15 + M16 each shipped one
code + closeout (three total including
planning) per backend-only scope. M17
shipped two code + closeout (four
total) per mixed backend+frontend
scope. M18 shipped six code + closeout
(seven total) per broad
validation-infrastructure scope. M19
sequencing depends on target
complexity.*

### Increment N (M19.N) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7t + roadmap flip +
M20 planning skeleton per standing user
directive.

---

*Draft-only. Full expansion at SESSION_153
(M19.0) open with the user.*
