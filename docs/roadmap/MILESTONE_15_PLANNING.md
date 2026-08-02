---
title: "Milestone 15 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_138 (post-M14-closeout)
milestone: 15
milestone_name: "TBD — user names target at SESSION_139 open"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_14_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_14_PLANNING.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
---

# Milestone 15 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M14.5 close per standing user directive
> (M10.8 / M11.7 / M12.8 / M13.4 / M14.5
> precedent). **M15 target milestone is
> TBD.** `IMPLEMENTATION_ROADMAP.md`
> §Milestone sequence ends at Milestone 14
> — the user names the M15 target at
> SESSION_139 M15.0 open, drawing from the
> M14 retrospective §8 unblocked-work list
> and any operational-evidence changes
> since M14 close.
>
> Full memo expansion + §5 decision surface
> + §7 sequencing refinement land at M15.0
> (SESSION_139) open. This document exists
> so SESSION_139 opens with a concrete
> starting point rather than a blank page.

## 0. Engineering practices to preserve from M2-M14

Same posture as M14.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9-M14 convention
  (404 cross-tenant, 409 state-machine /
  duplicate, 400 vocab / validation).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in §0.a
  per M5-M14 precedent.
- **Additive extension over fork.**
  Follow M11.1 / M12.3 / M13.2 / M14.1
  pattern for any additions to existing
  entities.
- **Every M15 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9-M14
  growth-only-list lesson. **Vocab-set
  assertions use exact equality** per
  M11 / M12 / M13 / M14 fixed-vocab
  lesson.
- **Read-only surfacer vs state-
  transitioning detector** — pick the
  Celery-beat shape by whether the
  trigger is operator intent or
  elapsed condition per M11-M14 lesson.
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another (per M12
  §6 lesson 11 and M13.2 / M14 sibling-
  package validation of the pattern).
- **Denormalize at write; recompute in
  detectors.** Per M12 §6 lesson 4 /
  M13.2 / M14 posture.
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 / M13.1
  / M14.1 posture.
- **Detector idempotency within runs.**
  Per M12 §6 lesson 8 / M13.2 posture.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default (six consecutive
  milestones now, per M14 §6 lesson
  10).
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson 15
  / M13.3 / M14.1 posture.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8 / M14 lesson 6.
- **Money on the wire is Decimal-as-
  string** per M9.5 / M10.1 / M12
  BHPH / M13 / M14 convention. Quantize
  Sum-annotation results to 2dp per
  M14.1 lesson.
- **Zero-noise render posture for
  count-based cards.** Per M14 §6
  lesson 6 — hide entirely at
  `count=0` rather than showing empty
  chrome.
- **Client-side validation matches
  server-side validation with matching
  trim posture.** Per M14 §6 lesson 5
  belt+suspenders symmetric on all-
  whitespace edge cases.
- **Browser E2E verification per
  frontend increment.** Per M14 §6
  lesson 4 — manual Playwright pass
  catches issues Vitest cannot.
- **Frontend Vitest discipline.** Per
  M11 / M12 / M14 precedent. Every
  new page adds Vitest coverage.

### 0.a Change log — resolved decisions

*(Populated at M15.0 open + per-
increment as §0.a amendments.)*

## 1. Business questions this milestone might answer

*Draft skeleton — user selects the M15
target at SESSION_139 open. The M14
retrospective §8 lists five substrates
M14 unblocked, any of which is a
candidate M15 target. The M13
retrospective §8 also remains valid
(most of its unblocked-work list is
still unaddressed after M14):*

| # | Candidate M15 target | Anchor |
|---|---|---|
| A | **M9 sale-booking GL post** — sync sibling-service call inside `services/sale/record_sale` per M13 §5.d Option C hybrid posture. Every sold vehicle produces a matching JournalEntry via `services.accounting.post_journal_entry`. The M14 UI will surface the resulting entries automatically. | M13 retrospective §8 + M13 §5.d Option C + M14 retrospective §8 |
| B | **M12 BHPH payment GL post** — detector at 11:00 project-time daily (next open slot after M13.2 10:00). Every unposted BhphPayment produces a matching journal entry. Same posture as M13.2 M2 cost detector. | M13 retrospective §8 + M13 §5.d Option C |
| C | **M10 F&I chargeback GL reversal** — chargebacks are already reversal-shaped in the operational surface; substrate readiness is complete. | M13 retrospective §8 |
| D | **Trial-balance materialization + monthly close workflow** — `TrialBalanceSnapshot` entity + M15+ monthly-close verb that freezes period-end views over the M13.3 pure recompute aggregator. Enables period-over-period comparisons that pure recompute cannot. The M14 trial-balance page could grow an `as_of` picker as part of this. | M13 retrospective §3 item 2 + §8 + M14 §3 deferral 7 |
| E | **Category-group-aware GL mapping** for the M13.2 detector. Now that the M14.4 failure card gives operators visibility into detector misses, evidence for the specific miscoding pain is available. Flooring → floor-plan accounts, admin → rent/ad, etc. | M13 retrospective §3 item 1 + M14 retrospective §8 |
| F | **M14 UX polish** — journal-entry list filters (date range, posted_by, reversal-only, description search) + `as_of` picker on trial-balance + sidebar nav entry for accounting. Layers atop the M14 shipped surface as operator evidence surfaces the need. | M14 retrospective §3 items 1 + 2 + 4 |
| G | **Non-accounting target** user names at open based on operational evidence not visible in the M14 retrospective. | — |

## 2. What existing primitives extend

*Draft skeleton per candidate M15
targets.*

- M13.1 `services/accounting/
  post_journal_entry` is the atomic
  sibling-service target for
  candidates A + B + C.
- M13.3 `compute_trial_balance` +
  M14.1 `list_journal_entries` are
  the source-of-truth verbs for
  candidate D materialization + F
  filters.
- M13.1 / M13.3 / M14.1 admin
  endpoints are the data source for
  candidate F UX polish.
- M9 `services/sale/record_sale`,
  M10 `services/f_and_i/
  record_chargeback`, M12
  `services/bhph_payments/
  record_payment` are the write
  paths that would gain sibling GL-
  posting calls for candidates A /
  C / B.
- M13.2 `post_all_unposted_costs_
  for_dealership` orchestrator is
  the template for candidate B
  detector; the same posture also
  supports candidate E category-
  group mapping (internal debit/
  credit selection changes; verb
  signature stays stable).
- M14.4 `CostPostingFailuresCard`
  is the surface that surfaces
  candidate E evidence (which
  categories miscode most often).

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton — locks at M15.0 open
based on user selection of the M15
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
surface lands at M15.0 open after
user names the M15 target.*

### 5.a `[NEEDS-DECISION-BEFORE-M15.0]` — Milestone target selection

**Question.** Which of the candidate
M15 targets (§1 above) defines M15
scope?

**Recommendation drafted.** *Awaits
user input at SESSION_139 open.* The
M14 retrospective §8 unblocked-work
list is the primary anchor; the M13
retrospective §8 remains valid;
operator evidence since M14 close may
reshape priorities.

Options (from §1 above):

- **Option A** — M9 sale-booking GL post.
- **Option B** — M12 BHPH payment GL post.
- **Option C** — M10 F&I chargeback GL reversal.
- **Option D** — Trial-balance materialization + monthly close.
- **Option E** — Category-group-aware GL mapping.
- **Option F** — M14 UX polish.
- **Option G** — Non-accounting target
  (user-named at open).

### 5.b–5.f `[NEEDS-DECISION-BEFORE-M15.0]`

*Additional load-bearing decisions land
at M15.0 open, shaped by the §5.a
target selection. Historical §5 counts
have been 6 for M10 / M11 / M12 / M13
/ M14; expect 4-8 for M15 depending
on target complexity.*

## 5. Sequencing draft

*Initial draft — user refinement
expected at M15.0 open once §5.a
target is confirmed.*

### Increment 0 (M15.0) — Planning refinement + decision review

**Scope.** SESSION_139. Confirm §5
decisions with user; expand this
skeleton into a full memo; refine §7
sequencing.

### Increments 1..N (M15.1..M15.N-1) — implementation

*Increment structure locks at M15.0
based on the confirmed target.
Historical M14 shipped six increments
(one backend + three frontend + one
close-out, plus M14.0 planning); M13
shipped four code + closeout; M12
shipped eight. Complexity-appropriate
scope discipline holds — small
complete increments per Project Rule
4.*

### Increment N (M15.N) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7p + roadmap
flip + M16 planning skeleton per
standing user directive.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`
   §6 (ten lessons carry into M15) +
   §8 (M14 unblocked work)
6. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §8 (M13 unblocked work — most
   still valid after M14)
7. `docs/CAPABILITY_MATRIX.md` §7o
8. Domain-specific research doc per
   the M15 target selected at §5.a.

---

*Draft-only. Full expansion at
SESSION_139 (M15.0) open with the
user.*
