---
title: "Milestone 17 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_144 (post-M16-closeout)
milestone: 17
milestone_name: "TBD — user names target at SESSION_145 open"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_16_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_16_PLANNING.md
  - docs/roadmap/MILESTONE_15_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
---

# Milestone 17 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M16.2 close per standing user directive
> (M10.8 / M11.7 / M12.8 / M13.4 / M14.5 /
> M15.2 / M16.2 precedent). **M17 target
> milestone is TBD.**
> `IMPLEMENTATION_ROADMAP.md` §Milestone
> sequence ends at Milestone 16 — the user
> names the M17 target at SESSION_145 M17.0
> open, drawing from the M16 retrospective
> §8 unblocked-work list, the still-valid
> M15 §8 items, and any operational-evidence
> changes since M16 close.
>
> Full memo expansion + §5 decision surface
> + §7 sequencing refinement land at M17.0
> (SESSION_145) open. This document exists
> so SESSION_145 opens with a concrete
> starting point rather than a blank page.
>
> **M16.2-close refinements (2026-08-02):**
> - **Option E bundled** to include the
>   `as_of` picker on M14.2 trial-balance
>   (previously listed as a sub-item of
>   Option G UX polish). The picker is the
>   operator UI for a materialized snapshot;
>   they ship together as monthly-close v1.
> - **Option G reduced** accordingly to
>   journal-entry list filters + sidebar
>   nav entry (the two remaining UX-polish
>   sub-items).
> - **Standing question for M17 close:**
>   review at the end of M17 whether M18
>   or M19 should be an intentional UI-
>   polish milestone (M14 shape) to
>   batch-consume Option G + any UX gaps
>   surfaced from operator use of M15 +
>   M16 + M17-shipped surfaces. Backend-
>   only milestones consistently generate
>   more UI/workflow deferrals than they
>   consume; an occasional UI-focused
>   milestone drains the backlog en
>   masse (per M14's shape as validated
>   against the M13 UI backlog).

## 0. Engineering practices to preserve from M2-M16

Same posture as M16.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M16 convention
  (404 cross-tenant, 409 state-machine /
  duplicate, 400 vocab / validation, 500
  broken-invariant `RuntimeError`
  subclasses per M15.1 + M16.1 posture).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in §0.a
  per M5-M16 precedent.
- **Additive extension over fork.**
  Follow M11.1 / M12.3 / M13.2 / M14.1 /
  M15.1 / M16.1 pattern for any additions
  to existing entities or verbs.
- **Every M17 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9-M16
  growth-only-list lesson. **Vocab-set
  assertions use exact equality** per
  M11 / M12 / M13 / M14 / M15 / M16
  fixed-vocab lesson.
- **Read-only surfacer vs state-
  transitioning detector vs sync
  sibling-service** — pick the shape by
  whether the trigger is operator intent
  (sync sibling per M13 §5.d Option C +
  M15.1 proof), elapsed condition
  (detector per M11-M14 precedent + M16.1
  proof), or read-only enumeration (verb
  per M13.3 / M14.1 precedent).
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another (per M12
  §6 lesson 11, M13.2, M14, M15 §6
  lesson 2, M16.1 verified). Nested
  atomic is a no-op inside an existing
  transaction.
- **Denormalize at write; recompute in
  detectors; refresh AFTER sibling
  writes if the denormalized value
  depends on them.** Per M12 §6 lesson
  4 / M13.2 / M14 posture / M15 §6
  lesson 6 / M16.1 `posted_at` pattern.
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 / M13.1
  / M14.1 / M16.1 posture (`detect_*`
  vs `post_*`).
- **Detector idempotency within runs
  AND across runs.** Per M12 §6 lesson
  8 / M13.2 / M16.1 posture.
  `posted_at__isnull=True` filter is
  the proven cross-run idempotency
  signal for detector milestones.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  (or an existing composition) by
  default (**eight consecutive
  milestones** now per M16 §6 lesson 5).
- **Broken-invariant guards as
  cross-milestone contracts.** Per
  M16 §6 lesson 4 — an assertion
  that a downstream milestone's
  entity hasn't drifted from its
  documented invariant IS the
  contract. Fires loud if
  violated. Pattern examples:
  `MissingDefaultAccountError`
  (M13.2 + M15.1 + M16.1),
  `UnmappedFinanceTypeError`
  (M15.1),
  `UnexpectedBhphPaymentFeesError`
  (M16.1).
- **Duplicate account-code constants
  across accounting submodules.** Per
  M15.1 + M16.1 posture (M16 §6
  lesson 3). Each submodule self-
  documents its account use;
  `__init__.py` re-exports one
  canonical origin per constant.
  Evidence gate for a shared-
  constants module still not tripped.
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson 15
  / M13.3 / M14.1 posture.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8 / M14 lesson 6 / M16.1
  detector zero-payments case.
- **Money on the wire is Decimal-as-
  string** per M9.5 / M10.1 / M12
  BHPH / M13 / M14 / M15 / M16
  convention.
- **Test-fixture invariants match
  migration invariants.** Per M15 §6
  lesson 3 / M16.1 verified —
  `make_dealership` seeds default
  COA, so every M13+ accounting
  test uses the helper for tenant
  setup.

### 0.a Change log — resolved decisions

*(Populated at M17.0 open + per-
increment as §0.a amendments.)*

## 1. Business questions this milestone might answer

*Draft skeleton — user selects the M17
target at SESSION_145 open. The M16
retrospective §8 lists the substrates
M16 unblocked or left open; the M15 §8
list also remains valid (most still
unaddressed after M16):*

| # | Candidate M17 target | Anchor |
|---|---|---|
| A | **M10 F&I chargeback GL reversal** — pattern proven from both directions now (M15 sync-sibling + M16 detector). Chargeback semantics — reverse-shaped operational event → likely sync-sibling per M15 pattern. `reverse_journal_entry` already ready. | M15 §8 + M16 §8 + M13 §5.d + M14 §8 |
| B | **BhphFee entity + late-fee GL posting** — M16.1's `UnexpectedBhphPaymentFeesError` makes the contract explicit. When the BhphFee entity ships, extend `post_bhph_payment_journal` with a CR fee-income line (440000 BHPH Late Fee Income — new account) and remove the guard. Blocked on operator evidence naming the late-fee tracking priority. | M16 §8 + M16 §3 item 2 |
| C | **Deposit / bank reconciliation workflow** — M16's phantom 100000 Cash on Hand balance (payments accumulate without ever being reclassified to 110000 Bank Operating) will surface operator questions about cash vs bank position reporting. Method-aware fund-flow routing (M16 §3 item 1) is the substrate half; the reclassification workflow is the operational half. | M16 §8 + M16 §3 item 1 + M16 §3 item 6 |
| D | **NSF / payment-reversal workflow** — ACH failures + returned payments need both operational contract (what happens to the BhphPayment row?) and GL wiring (via `reverse_journal_entry`). Same shape as sale-reversal but with a real operator-driven trigger (bank returns the draft). | M16 §8 + M16 §3 item 3 |
| E | **Trial-balance materialization + `as_of` picker (monthly-close v1)** — bundled at M16.2 close per user directive. `TrialBalanceSnapshot` entity + freeze verb over the M13.3 pure recompute aggregator (backend), plus the `as_of` picker on the M14.2 trial-balance page (frontend). Bundled because the picker IS the operator UI for a materialized snapshot — without the picker, the entity has no consumer; without the entity, the picker has nothing to query. Together they form the smallest complete operator-usable slice of monthly-close workflow. M16's BHPH activity now makes period-over-period reports meaningful (interest income + Notes Receivable amortization). | M15 §8 + M16 §8 |
| F | **Category-group-aware GL mapping** for the M13.2 detector — remains unblocked. M14.4's failure card + M15 sale activity + M16 payment activity all accumulate miscoding evidence. | M14 §8 + M15 §8 + M16 §8 |
| G | **M14 UX polish** (journal-entry list filters + sidebar nav entry for accounting) — layers atop the shipped surface. Operator evidence on M15 + M16-shipped surfaces now starts to accumulate faster (two active daily-posting streams). **`as_of` picker moved to Option E per M16.2-close bundling directive.** | M14 §8 + M15 §8 + M16 §8 |
| H | **Cost-of-sale variance handling** — M15 §3 item 11 deferral. Post-sale VehicleCost phantom balances more visible now that BHPH activity also flows into trial balance. | M15 §3 item 11 + M16 §8 |
| I | **Sale-reversal workflow** — M15 §3 item 8 deferral. GL side ready; operational contract needed. | M15 §3 item 8 + M16 §8 |
| J | **BHPH interest accrual detector (accrual-basis)** — M16 is cash-basis. Period-end accrual (DR 132000 Accrued Interest Receivable — new account / CR 430000 BHPH Interest Income) is a natural follow-on for month-end close discipline. | M16 §8 + M16 §3 item 5 |
| K | **Non-accounting target** user names at open based on operational evidence not visible in the M16 / M15 retrospectives. | — |

## 2. What existing primitives extend

*Draft skeleton per candidate M17
targets.*

- M13.1 `services/accounting/
  post_journal_entry` is the atomic
  sibling target for candidates A + B
  + C + J.
- M13.1 `reverse_journal_entry` is the
  atomic sibling target for candidates
  A + D + I.
- M13.3 `compute_trial_balance` +
  M14.1 `list_journal_entries` are the
  source-of-truth verbs for candidate
  E materialization + G filters.
- M13.1 / M13.3 / M14.1 admin
  endpoints are the data source for
  candidate G UX polish.
- M15.1 `services/accounting/
  sale_booking.post_sale_booking_journal`
  is the pattern template for the
  sync-sibling half — candidates A
  (chargeback reversal is likely
  sync-sibling) + I (sale-reversal).
- M16.1 `services/accounting/
  bhph_payment.post_all_unposted_bhph_
  payments_for_dealership` is the
  pattern template for the detector
  half — candidates J (interest
  accrual detector) + potentially D
  (if payment-reversal batched at
  end-of-day).
- M13.2 `post_all_unposted_costs_for_
  dealership` + M16.1 `post_all_
  unposted_bhph_payments_for_
  dealership` orchestrators are the
  templates for candidate F category-
  group mapping.
- M14.4 `CostPostingFailuresCard` is
  the surface that surfaces candidate
  F evidence.
- M16.1 `UnexpectedBhphPaymentFeesError`
  guard shows the contract-assertion
  pattern for candidate B (removing
  the guard is part of the BhphFee
  milestone deliverable).

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton — locks at M17.0
open based on user selection of the
M17 target.*

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

*Populated at M17.0 open per M16
§4 pattern.*

## 5. Load-bearing decisions to resolve

*Draft skeleton. Full decision
surface lands at M17.0 open after
user names the M17 target.*

### 5.a `[NEEDS-DECISION-BEFORE-M17.0]` — Milestone target selection

**Question.** Which of the candidate
M17 targets (§1 above) defines M17
scope?

**Recommendation drafted.** *Awaits
user input at SESSION_145 open.* The
M16 retrospective §8 unblocked-work
list is the primary anchor; the M15
retrospective §8 remains valid;
operator evidence since M16 close
may reshape priorities.

Options (from §1 above):

- **Option A** — M10 F&I chargeback GL reversal.
- **Option B** — BhphFee entity + late-fee GL posting.
- **Option C** — Deposit / bank reconciliation workflow.
- **Option D** — NSF / payment-reversal workflow.
- **Option E** — Trial-balance materialization + `as_of`
  picker (monthly-close v1) — bundled at M16.2 close.
- **Option F** — Category-group-aware GL mapping.
- **Option G** — M14 UX polish (JE filters + sidebar nav;
  `as_of` picker moved to E).
- **Option H** — Cost-of-sale variance handling.
- **Option I** — Sale-reversal workflow.
- **Option J** — BHPH interest accrual detector.
- **Option K** — Non-accounting target
  (user-named at open).

### 5.b–5.f `[NEEDS-DECISION-BEFORE-M17.0]`

*Additional load-bearing decisions
land at M17.0 open, shaped by the
§5.a target selection. Historical
§5 counts have been 6 for M10 /
M11 / M12 / M13 / M14 / M15 / M16;
expect 4-8 for M17 depending on
target complexity.*

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
   §6 (six lessons carry into M17) +
   §8 (M16 unblocked work)
6. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §8 (M15 unblocked work — still
   mostly valid after M16)
7. `docs/CAPABILITY_MATRIX.md` §7q
8. Domain-specific research doc per
   the M17 target selected at §5.a.

## 7. Sequencing draft

*Initial draft — user refinement
expected at M17.0 open once §5.a
target is confirmed.*

### Increment 0 (M17.0) — Planning refinement + decision review

**Scope.** SESSION_145. Confirm §5
decisions with user; expand this
skeleton into a full memo; refine
§7 sequencing.

### Increments 1..N (M17.1..M17.N-1) — implementation

*Increment structure locks at M17.0
based on the confirmed target.
Historical M15 + M16 each shipped
one code + closeout (three total
including planning) per backend-
only scope. M14 shipped four code +
closeout (six total). M12 shipped
eight. Complexity-appropriate scope
discipline holds — small complete
increments per Project Rule 4.
**Option E (bundled) would likely
be 4-5 increments** (planning +
backend entity/verb + backend
detector or freeze verb + frontend
picker + close-out) given its
mixed backend+frontend scope.
Other options remain 3-increment
backend-only.*

### Increment N (M17.N) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7r + roadmap
flip + M18 planning skeleton per
standing user directive.

---

*Draft-only. Full expansion at
SESSION_145 (M17.0) open with the
user.*
