---
title: "Milestone 14 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_132 (post-M13-closeout)
milestone: 14
milestone_name: "TBD — user names target at SESSION_133 open"
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

# Milestone 14 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M13.4 close per standing user directive
> (M10.8 / M11.7 / M12.8 / M13.4
> precedent). **M14 target milestone is
> TBD.** `IMPLEMENTATION_ROADMAP.md`
> §Milestone sequence ends at Milestone
> 13 — the user names the M14 target at
> SESSION_133 M14.0 open, drawing from the
> M13 retrospective §8 unblocked-work list
> and any operational-evidence changes since
> M13 close.
>
> Full memo expansion + §5 decision surface
> + §7 sequencing refinement land at M14.0
> (SESSION_133) open. This document exists
> so SESSION_133 opens with a concrete
> starting point rather than a blank page.

## 0. Engineering practices to preserve from M2-M13

Same posture as M13.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M13 convention
  (404 cross-tenant, 409 state-machine /
  duplicate, 400 vocab / validation).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in §0.a
  per M5-M13 precedent.
- **Additive extension over fork.**
  Follow M11.1 / M12.3 / M13.2 pattern
  for any additions to existing entities.
- **Every M14 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9-M13
  growth-only-list lesson. **Vocab-set
  assertions use exact equality** per
  M11 / M12 / M13 fixed-vocab lesson.
- **Read-only surfacer vs state-
  transitioning detector** — pick the
  Celery-beat shape by whether the
  trigger is operator intent or
  elapsed condition per M11-M13
  lesson.
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another (per M12
  §6 lesson 11 and M13.2 sibling-
  package validation of the pattern).
- **Denormalize at write; recompute in
  detectors.** Per M12 §6 lesson 4 /
  M13.2 posture.
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 / M13.1
  posture.
- **Detector idempotency within runs.**
  Per M12 §6 lesson 8 / M13.2 posture.
- **Zero-drift permission-class posture.**
  Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default (five consecutive
  milestones now, per M13 §6 lesson 12).
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson 15 /
  M13.3 posture.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8.

### 0.a Change log — resolved decisions

*(Populated at M14.0 open + per-
increment as §0.a amendments.)*

## 1. Business questions this milestone might answer

*Draft skeleton — user selects the M14
target at SESSION_133 open. The M13
retrospective §8 lists five substrates
M13 unblocked, any of which is a
candidate M14 target:*

| # | Candidate M14 target | Anchor |
|---|---|---|
| A | **M9 sale-booking GL post** — sync inside `record_sale` per §5.d Option C hybrid posture. Every sold vehicle produces a matching JournalEntry via `services.accounting.post_journal_entry`. | M13 retrospective §8 + M13 §5.d Option C |
| B | **M12 BHPH payment GL post** — detector at 11:00 project-time daily (next open slot after M13.2 10:00). Every unposted BhphPayment produces a matching journal entry. Same posture as M13.2 M2 cost detector. | M13 retrospective §8 + M13 §5.d Option C |
| C | **M10 F&I chargeback GL reversal** — chargebacks are already reversal-shaped in the operational surface; substrate readiness is complete. | M13 retrospective §8 |
| D | **Operator UI for M13 substrate** — journal-entry browser, trial-balance render, reversal-with-reason dialog, cost-posting failure surfacing. React work over the M13.1 + M13.3 endpoints already shipped. Per M13 §5.f Option C the entire M13 milestone shipped backend-only; UI was deferred to M14. | M13 retrospective §3 item 4 + M13 §5.f Option C |
| E | **Trial-balance materialization + monthly close workflow** — `TrialBalanceSnapshot` entity + M14+ monthly-close verb that freezes period-end views. Enables period-over-period comparisons that pure recompute cannot. | M13 retrospective §3 item 2 + §8 |

Non-accounting candidates may also
emerge at M14.0 open — operator
evidence since M13 close may name a
different surface as more urgent.

## 2. What existing primitives extend

*Draft skeleton per candidate M14
targets.*

- M13.1 `services/accounting/post_journal_entry`
  is the atomic sibling-service target
  for candidates A + B + C.
- M13.3 `compute_trial_balance` is the
  source-of-truth aggregator for
  candidate E.
- M13.1 / M13.3 admin endpoints are
  the data source for candidate D.
- M9 `services/sale/record_sale`,
  M10 `services/f_and_i/record_chargeback`,
  M12 `services/bhph_payments/record_payment`
  are the write paths that would
  gain sibling GL-posting calls for
  candidates A / C / B.
- M12.3 / M12.4 / M13.2 Celery-beat
  detector shapes are the template
  for candidate B (elapsed-condition
  detector at 11:00 slot).

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton — locks at M14.0 open
based on user selection of the M14
target.*

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

## 4. Load-bearing decisions to resolve

*Draft skeleton. Full decision
surface lands at M14.0 open after
user names the M14 target.*

### 5.a `[NEEDS-DECISION-BEFORE-M14.0]` — Milestone target selection

**Question.** Which of the candidate
M14 targets (§1 above) defines M14
scope?

**Recommendation drafted.** *Awaits
user input at SESSION_133 open.* The
retrospective §8 unblocked-work list
is the primary anchor; operator
evidence since M13 close may reshape
priorities.

Options (from §1 above):

- **Option A** — M9 sale-booking GL post.
- **Option B** — M12 BHPH payment GL post.
- **Option C** — M10 F&I chargeback GL reversal.
- **Option D** — Operator UI for M13 substrate.
- **Option E** — Trial-balance materialization.
- **Option F** — Non-accounting target
  (user-named at open).

### 5.b–5.f `[NEEDS-DECISION-BEFORE-M14.0]`

*Additional load-bearing decisions land
at M14.0 open, shaped by the §5.a target
selection. Historical §5 counts have been
6 for M10 / M11 / M12 / M13; expect 4-8
for M14 depending on target complexity.*

## 5. Sequencing draft

*Initial draft — user refinement
expected at M14.0 open once §5.a
target is confirmed.*

### Increment 0 (M14.0) — Planning refinement + decision review

**Scope.** SESSION_133. Confirm §5
decisions with user; expand this
skeleton into a full memo; refine §7
sequencing.

### Increments 1..N (M14.1..M14.N-1) — implementation

*Increment structure locks at M14.0
based on the confirmed target.
Historical M13 shipped four
increments (substrate + slice +
aggregate + closeout); M12 shipped
eight; M11 shipped seven.
Complexity-appropriate scope
discipline holds — small complete
increments per Project Rule 4.*

### Increment N (M14.N) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7o + roadmap
flip + M15 planning skeleton per
standing user directive.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §6 (twelve lessons carry into
   M14) + §8 (M13 unblocked work)
6. `docs/CAPABILITY_MATRIX.md` §7n
7. Domain-specific research doc per
   the M14 target selected at
   §5.a.

---

*Draft-only. Full expansion at
SESSION_133 (M14.0) open with the
user.*
