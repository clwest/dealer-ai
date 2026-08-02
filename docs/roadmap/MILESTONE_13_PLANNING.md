---
title: "Milestone 13 — Implementation-Planning Pass"
status: shipped
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_128 (post-M12-closeout)
milestone: 13
milestone_name: "Accounting reconciliation core (v1)"
shipped_at_session: SESSION_132
retrospective: docs/roadmap/MILESTONE_13_RETROSPECTIVE.md
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_12_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_12_PLANNING.md
  - docs/roadmap/MILESTONE_11_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
---

# Milestone 13 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M12.8 close per standing user directive
> (M10.8 / M11.7 precedent). Full memo
> expansion + §5 decision surface + §7
> sequencing refinement land at M13.0
> (SESSION_129) open. This document exists
> so SESSION_129 opens with a concrete
> starting point rather than a blank page.
>
> **This milestone is deliberately
> structured to be incremental** — a single
> monolithic "accounting" milestone would
> violate Scope Discipline per Project
> Rule 4. The IMPLEMENTATION_ROADMAP.md
> §Milestone 13 already flags this: "in
> practice this milestone is a *series of
> smaller milestones layered onto
> Milestones 2, 4, 9, 10, 12* as those
> surfaces ship." M13.0 open with the user
> will resolve which slice ships first.

## 0. Engineering practices to preserve from M2-M12

Same posture as M12.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9/M10/M11/M12
  convention (404 cross-tenant, 409
  state-machine / duplicate, 400
  vocab / validation).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in §0.a
  per M5-M12 precedent.
- **Additive extension over fork.**
  Follow M11.1 / M12.3 pattern for any
  additions to existing entities.
- **Every M13 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9 §6 lesson
  14 / M10 §6 lesson 12 / M11 §6
  lesson 12 / M12 §6 lesson 8.
  **Vocab-set assertions use exact
  equality** per M11 §6 lesson 18 /
  M12 §6 lesson 3.
- **Read-only surfacer vs state-
  transitioning detector** — pick the
  Celery-beat shape by whether the
  trigger is operator intent or elapsed
  condition per M11 §6 lesson 17 / M12
  §6 lesson 6.
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another
  (e.g. M13 GL-posting from M2 /
  M4 / M9 / M10 / M12 write paths).
- **Denormalize at write; recompute
  in detectors.** Per M12 §6 lesson 4.
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3.
- **Detector idempotency within
  runs.** Per M12 §6 lesson 8.

### 0.a Change log — resolved decisions

**SESSION_129 open (M13.0) —
six §5 decisions confirmed as-
recommended by the user.** Streak
extends to **47 planning-time as-
recommended M5.1 → M13.0**
(M12.1 six + M13.0 six =
41 + 6 = 47).

| # | Decision | Resolution |
|---|---|---|
| §5.a | Milestone slice selection (load-bearing) | **Option A** — substrate (GLAccount + JournalEntry) + Q1 (M2 cost reconciliation) as the first slice. M13.2 = M2 reconciliation; M13.3 = trial-balance snapshot; M13.4 = closeout. |
| §5.b | GL chart-of-accounts source | **Option B** — platform-shipped default COA (auto-dealer industry-standard, per ACCOUNTING §1.1 NADA / dealer-standard chart); per-dealer overrides defer to M14+. |
| §5.c | Journal entry immutability | **Option A** — immutable + reversing entries. Every correction is a new posting. |
| §5.d | GL-posting trigger shape | **Option C** — hybrid: sync `@transaction.atomic` for M9 sale-booking (operator intent), detector for M2 cost accrual + M12 payment posting (elapsed condition). |
| §5.e | Substrate location | **Option A** — new `services/accounting/` package inside `dealer_ai/`. Mirrors every M2-M12 service-package posture. |
| §5.f | Operator UI scope at M13 | **Option C** — no UI at M13 (backend-only). Operator UI defers to M14 once substrate is stable. |

**SESSION_130 open (M13.2) — six
implementation-time micro-decisions
confirmed as-recommended by the
user.** Per M10/M11/M12 §0.a
precedent, these do not count against
the planning-time streak (which
stands at 47 M5.1 → M13.0).

| # | Decision | Resolution |
|---|---|---|
| M13.2 · 1 | `VehicleCost.posted_at` posture | Denormalize at write — detector sets `posted_at` after successful GL post (M12 §6 lesson 4 pattern). |
| M13.2 · 2 | GLAccount mapping strategy | Uniform mapping for M13.2: every eligible VehicleCost → DR `122000` Recon WIP + CR `200000` A/P Trade. Category-group-aware mapping (flooring / admin / photography) defers to a later increment per fixed-vocab posture. |
| M13.2 · 3 | Detector schedule slot | 10:00 project-time daily (ninth Celery-beat family after M12.4 at 09:00; extends the 02:00–09:00 slot pattern). |
| M13.2 · 4 | `is_estimate=True` posture | Skip. Estimates are speculative WO allocations that may change; when an estimate flips to committed the still-NULL `posted_at` picks it up on the next detector run. |
| M13.2 · 5 | Negative-amount correction posture | Post with sides swapped — negative `amount` means DR A/P Trade + CR Recon WIP (reverses typical direction). Preserves accrual accuracy per VehicleCost §1.6 design note. |
| M13.2 · 6 | Idempotency posture | Per-row `@transaction.atomic` around GL post + `posted_at` update (sibling-service crossing per M12 §6 lesson 11). Filter `posted_at__isnull=True, is_estimate=False` gives cross-run idempotency. |

**SESSION_131 open (M13.3) — five
implementation-time micro-decisions
confirmed as-recommended by the
user.** Per M10-M13.2 §0.a precedent
these do not count against the
planning-time streak (still 47 M5.1
→ M13.0).

| # | Decision | Resolution |
|---|---|---|
| M13.3 · 1 | Snapshot verb output shape | Frozen dataclass (`TrialBalanceRow` + `TrialBalanceSnapshot`) per M12 §6 lesson 15 pattern. Matches every M8 / M12.7 aggregate return shape. |
| M13.3 · 2 | Caching posture | Pure recompute at M13.3; no `TrialBalanceSnapshot` entity. Materialization defers until M14+ operator evidence names the close-workflow need. |
| M13.3 · 3 | Endpoint gating | Reuse `IsSalesManagerOrOwnerAtActiveDealership` — zero-drift posture (permission classes stay at 8 across four consecutive milestones). |
| M13.3 · 4 | `as_of` parameter | Optional (default `timezone.now()`). Includes JournalEntry rows whose `posted_at <= as_of`. Matches M12.7 analytics posture. |
| M13.3 · 5 | Zero-portfolio semantics | Empty balanced snapshot (`rows=[]`, `total_debits=0`, `total_credits=0`, `is_balanced=True`) — not 404. A fresh dealership post-M13.1 seed is a valid trial-balance state, not an error. |

*(Per-increment §0.a amendments
appended below as implementation
sessions surface micro-decisions.)*

## 1. Business questions this milestone answers

*Draft skeleton. Full memos land at
M13.0 open.*

| # | Question | Research anchor |
|---|---|---|
| 1 | **How does the platform reconcile M2 vehicle cost accumulation with a GL cost-of-inventory control account?** | ACCOUNTING §"Accounting is the reconciliation layer that validates every operational event." + pain #1 (three-way reconciliation without POs) |
| 2 | **How does the platform post an M9 Sale + M10 Contract to the GL as a deal-booking journal entry?** | ACCOUNTING §"When the DMS is right, accounting is right." + pain #2 (chasing funding) |
| 3 | **How does the platform track contracts-in-transit (funded-pending deals) and clear them on funding receipt?** | ACCOUNTING pain #2 + FINANCE §funding |
| 4 | **How does the platform reconcile M4 work-order approvals + M4.5 vendor comms with vendor invoice + AP journal?** | ACCOUNTING pain #4 (reconciling vendor payments) + pain #1 |
| 5 | **How does the platform track title arrival + aging + storage against inventory records?** | ACCOUNTING pain #3 (chasing titles) |
| 6 | **How does the platform reconcile M2 floor-plan interest accrual with lender statements?** | ACCOUNTING §floor plan reconciliation |
| 7 | **How does the platform track M12 BHPH payment receipts against a control account + surface unapplied cash?** | ACCOUNTING pain #8 (unapplied cash) + M12 |
| 8 | **How does the platform reconcile schedule (subledger) balances with GL control accounts and surface breaks?** | ACCOUNTING pain #9 + pain #10 |
| 9 | **How does the platform support a monthly close workflow (adjusting entries, trial balance snapshot)?** | ACCOUNTING §monthly close |

**These nine questions do not all belong
in a single milestone.** Per §5.a below,
M13.0 open will select the slice(s) to
ship at M13. Remaining slices layer onto
M14+ or into ongoing operational
milestones per the IMPLEMENTATION_ROADMAP
§Milestone 13 incremental structure.

## 2. What existing primitives extend

*Draft skeleton.*

- M2 payment engine + floor-plan
  accrual (already produces per-
  vehicle cost + interest journals).
- M4 work-order verbs (already
  produce vendor-approval events).
- M4.5 vendor-comm scrub (already
  drafts invoice-adjacent comms).
- M9 Sale + `gross_realized`
  denormalization (already produces
  deal-booking triggers).
- M10 Contract + F&I chargeback
  (already produces commission-
  reversal triggers).
- M12 BhphNote + BhphPayment
  (already produces payment-receipt
  events).
- Existing `services/analytics/`
  patterns for portfolio-level
  aggregations (M13 close might
  reuse the same posture for
  trial-balance snapshots).

## 3. What's NOT in this milestone (deferrals)

*Draft skeleton per
IMPLEMENTATION_ROADMAP §5 explicit non-
goals.*

- Payroll (external service).
- W-2 / 1099 generation (external
  service).
- Year-end tax return preparation
  (external CPA).
- GAAP-compliant audited financial
  reporting (out of scope for
  platform v1).
- Direct DMS integration (belongs to
  a future vendor-integration
  milestone).

## 4. Load-bearing decisions to resolve

*Draft skeleton. Full decision surface
lands at M13.0 open.*

### 5.a `[NEEDS-DECISION-BEFORE-M13.0]` — Milestone slice selection

**Question.** Which of the nine
business questions above define M13
scope? Per IMPLEMENTATION_ROADMAP §M13,
the milestone is structured to be
incremental. Options:

- **Option A** — M13 delivers the
  reconciliation-substrate common
  layer (GL account model + journal
  entry model + subledger interface)
  + Q1 (M2 cost reconciliation) as
  the first slice. Subsequent
  slices (Q2 / Q3 / …) layer onto
  M14+.
- **Option B** — M13 delivers a
  narrower single-question slice
  (e.g. Q7 M12 BHPH receipts →
  control account only). The
  substrate lands with the slice;
  the pattern generalizes at M14+.
- **Option C** — M13 delivers a
  fatter slice covering Q1 + Q2 +
  Q3 (M2/M9/M10 reconciliation
  triangle). Larger scope, higher
  risk of Rule 4 scope-creep.

**Recommendation drafted.** Option A —
substrate + Q1 (M2 cost
reconciliation) as the first slice.
Rationale: (1) the substrate is
generalizable and unblocks every
subsequent slice; (2) Q1 is the
lowest-risk anchor because M2 is
the most-mature operational surface;
(3) matches M12's pattern of
extending payment_engine + adding
new packages rather than remodeling
existing entities.

### 5.b `[NEEDS-DECISION-BEFORE-M13.0]` — GL chart-of-accounts source

**Question.** Where does the chart of
accounts come from?

- **Option A** — dealer-configurable
  via new `GLAccount` entity + admin
  CRUD. Every dealership owns its
  chart.
- **Option B** — platform-shipped
  default chart (industry-standard
  auto-dealer COA). Per-dealer
  overrides land at M14+.
- **Option C** — hybrid: platform
  ships defaults; dealer can
  override per-account.

**Recommendation drafted.** Option B
(defaults ship). Rationale: (1)
matches the M11 vocab-set pattern
(fixed initial vocab; extensions on
operator evidence); (2) reduces M13
onboarding friction; (3) avoids
premature abstraction. Per-dealer
overrides at M14+ when operator
evidence surfaces need.

### 5.c `[NEEDS-DECISION-BEFORE-M13.0]` — Journal entry immutability

**Question.** Once posted, can a
journal entry be edited?

- **Option A** — immutable. Any
  correction requires a *reversing*
  journal entry + a *replacement*
  entry. Full audit trail.
- **Option B** — mutable but
  version-tracked (`JournalEntry` +
  `JournalEntryRevision`).
- **Option C** — mutable within
  the current period; immutable
  after month-end close.

**Recommendation drafted.** Option A
(immutable + reversing entries).
Rationale: (1) matches every real
double-entry accounting system; (2)
simplifies audit; (3) avoids
temporal-mutability edge cases at
period boundaries.

### 5.d `[NEEDS-DECISION-BEFORE-M13.0]` — GL-posting trigger shape

**Question.** How do M2/M9/M10/M12
write paths trigger GL posting?

- **Option A** — synchronous
  `@transaction.atomic` sibling-
  service call inside the M9 /
  M10 / M12 write verb (e.g.
  `record_sale` also calls
  `post_journal_entry`).
- **Option B** — Celery-beat
  detector that scans for un-
  posted operational events at
  a scheduled interval and
  batch-posts.
- **Option C** — hybrid: sync
  for M9 sale-booking (blocking
  the close is a real cost);
  detector for M2 cost accrual +
  M12 payment posting (lower-
  urgency batches).

**Recommendation drafted.** Option C
(hybrid). Rationale: (1) Sale
booking is operator-intent; must be
synchronous. (2) Cost accrual + BHPH
payment posting are elapsed-
condition; detector pattern matches
M12.3 posture. Reduces M13
implementation surface.

### 5.e `[NEEDS-DECISION-BEFORE-M13.0]` — Substrate location

**Question.** Where does the
reconciliation substrate live?

- **Option A** — new `services/
  accounting/` package.
- **Option B** — new
  `dealer_ai/accounting/` app
  (separate Django app).
- **Option C** — new sibling app
  `dealer_kit/accounting/`
  (separate from `dealer_ai/`
  for future extraction).

**Recommendation drafted.** Option A
(`services/accounting/` package
inside `dealer_ai/`). Rationale: (1)
matches every M2-M12 service package
posture; (2) avoids premature app
extraction; (3) preserves the
single-app tenancy carrier surface.

### 5.f `[NEEDS-DECISION-BEFORE-M13.0]` — Operator UI scope

**Question.** What UI ships at M13?

- **Option A** — full trial-balance
  + schedule dashboard at M13.
- **Option B** — MVP: single
  reconciliation-status card per
  reconciled surface (e.g.
  "M2 cost accrual: X un-posted
  events, oldest 3 days").
- **Option C** — no UI at M13
  (backend-only); operator
  consumes via admin endpoints.

**Recommendation drafted.** Option C
(no UI). Rationale: (1) matches the
M11.3 posture (backend substrate
first, UI in a later increment); (2)
M13 is already a large planning
surface; (3) operator UI defers to
M14 once the substrate is stable.

## 5. Sequencing draft

*Initial draft — user refinement
expected at M13.0 open. Assumes §5.a
Option A (substrate + Q1) confirmed.*

### Increment 0 (M13.0) — Planning refinement + decision review

**Scope.** SESSION_129. Review §5
decisions with user; refine §7
sequencing if needed.

### Increment 1 (M13.1) — GL substrate: chart of accounts + journal entry model

**Scope.** New `services/accounting/`
package. `GLAccount` model + fixed
default COA fixture (auto-dealer
industry-standard). `JournalEntry` +
`JournalEntryLine` models (immutable
per §5.c Option A). Three verbs:
`post_journal_entry(dealership,
lines, description)` +
`reverse_journal_entry(pk, reason)`
(atomic write of the reversal) +
`get_journal_entry(pk, dealership)`.
Cross-tenant guards. Tenancy carrier
+3 (GLAccount + JournalEntry +
JournalEntryLine). ~40 focused
tests.

### Increment 2 (M13.2) — M2 cost reconciliation

**Scope.** Detector task at 10:00
project-time daily (next slot after
M12.4 09:00). Scans unposted
`VehicleCost` rows + posts
corresponding journal entries via
M13.1 verbs. `VehicleCost.posted_at`
denormalized column (additive
extension). Migration for the
column addition. ~25 focused tests.

### Increment 3 (M13.3) — Trial-balance snapshot

**Scope.** New `services/accounting/
snapshot.py` with pure aggregate
verbs computing account balances at
a point in time. GET endpoint for
the trial balance. ~20 tests.

### Increment 4 (M13.4) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7n + roadmap
flip + M14 planning skeleton per
standing user directive.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 13
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
   §6 (nineteen lessons carry
   into M13)
6. `docs/CAPABILITY_MATRIX.md` §7m
7. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
8. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

---

*Draft-only. Full expansion at
SESSION_129 (M13.0) open with the
user.*
