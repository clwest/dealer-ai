---
title: "Milestone 16 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_142 → SESSION_144
milestone: 16
milestone_name: "M12 BHPH payment GL post"
related:
  - docs/roadmap/MILESTONE_16_PLANNING.md
  - docs/roadmap/MILESTONE_15_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 16
---

# Milestone 16 — Retrospective

Written at Milestone 16 close (SESSION_144).
Records what was planned, what shipped,
what deviated and why, and lessons carried
forward for Milestone 17 and beyond. Mirrors
the `MILESTONE_15_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_16_PLANNING.md` at SESSION_141
close (drafted at M15.2 per standing user
directive) defined the milestone as the M12
BHPH payment GL post. §5.a Option B locked
at SESSION_142 M16.0 open — every unposted
BhphPayment produces a matching balanced
JournalEntry via an 11:00 project-time daily
Celery-beat detector per M13 §5.d Option C
hybrid posture. M15 shipped the sync-sibling
half (sale booking, operator intent); M16
ships the detector half (BHPH payment
posting, elapsed condition).

**This milestone was deliberately backend-
only**, following the M15 posture. The M14
UI surface (M14.3 journal-entry browser +
M14.2 trial-balance page) surfaces the
resulting entries automatically without
additional frontend work. Zero frontend
increment shipped at M16.

§5.a–§5.f drafted **six load-bearing
planning-time decisions** all flagged
`[NEEDS-DECISION-BEFORE-M16.0]` in the
skeleton. §7 sequenced three increments
(M16.0 planning + M16.1 backend + M16.2
close-out) — matches M15's shape per M15
§6 lesson 8 (backend-only milestones
compact to 2-3 increments).

**Original §7 sequencing shipped verbatim.**
All six SESSION_142 decisions confirmed as-
recommended at M16.0 open (Option B for §5.a
plus Option A for §5.b-§5.f). Additional
implementation-time micro-decisions surfaced
at M16.1 (five) — recorded in §0.a
amendments per M5-M15 precedent. Per M10 §9
those are **implementation-time defaults, not
planning-time decisions**, so they do not
count against the streak. **The streak stands
at 64 planning-time as-recommended M5.1 →
M16.0** — seven consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 + M16)
with every §5 decision confirmed as-
recommended at planning-time open.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M16.0 planning | 142 | `MILESTONE_16_PLANNING.md` expanded from ~330-line skeleton to ~1,010-line active memo. Frontmatter `status: draft` → `status: active`; `milestone_name` set to "M12 BHPH payment GL post"; `sources` list extended with BHPH_OPERATIONS + ACCOUNTING research + M13/M14/M15 planning + retrospectives. Six §5 load-bearing decisions resolved with recommendations + rationale (§5.a Option B + §5.b-§5.f all Option A). §1 business questions expanded to four operator-workflow questions (Q1 GL reflects the payment / Q2 BHPH interest income at the GL / Q3 BHPH Notes Receivable amortizes / Q4 cash flow into GL). §3 deferrals locked at 16 (11 M16-specific + 5 universal). §7 sequenced one code increment + one close-out (three total including planning). **Six §5 decisions confirmed as-recommended** — streak 64 M5.1 → M16.0. | `e909582` |
| M16.1 Backend: BHPH payment GL detector | 143 | Migration `0045_m161_bhph_payment_posted_at.py` (one AddField, matches M13.2's `0044_m132_vehicle_cost_posted_at.py` verbatim shape). New module `services/accounting/bhph_payment.py` (~290 lines) with `detect_unposted_bhph_payments` pure query, `post_bhph_payment_journal` atomic sibling verb (DR 100000 Cash + optional CR 123000 BHPH Notes Receivable + optional CR 430000 BHPH Interest Income per §5.c + §5.e Option A), `post_all_unposted_bhph_payments_for_dealership` orchestrator (return shape matches M13.2 exactly). New `UnexpectedBhphPaymentFeesError(RuntimeError)` broken-invariant guard fires when `applied_to_fees` is non-zero (asserts M12.2 zero-fees invariant; future BhphFee milestone extends this verb). `_lookup_required_account` mirrored verbatim from M13.2 per M15.1 §0.a decision 3. Three account-code constants declared (`CASH_ACCOUNT_CODE`, `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`, `BHPH_INTEREST_INCOME_ACCOUNT_CODE` — first two duplicate `sale_booking.py` per M15.1 posture; third is new to M16.1). Extended `services/accounting/tasks.py` with two `@instrumented_task` functions (`post_bhph_payment_journals_for_dealership` per-tenant + `post_bhph_payment_journals_for_all_tenants` orchestrator) + two new task-name constants. Extended `services/accounting/__init__.py` `__all__` for the new verbs + constant + error class. Added `accounting-bhph-payment-post-daily-11-00` entry in `dealer_kit/settings.py::CELERY_BEAT_SCHEDULE` at `crontab(hour=11, minute=0)` — tenth beat family, next open non-overlapping slot after M13.2's 10:00. Added `BhphPayment.posted_at DateTimeField(null=True, blank=True)` field on the model with docstring referencing §5.d Option A. **30 focused tests** across 9 TestCase classes in new `tests/test_m161_bhph_payment_gl.py`: `DetectUnpostedBhphPaymentsTests` (5) + `PostBhphPaymentJournalHappyPathTests` (7) + `PostBhphPaymentJournalGuardsTests` (6) + `PostAllUnpostedBhphPaymentsOrchestratorTests` (5) + `PostBhphPaymentTaskTests` (3) + `BhphPaymentOrchestratorDispatchTests` (1) + `BhphPaymentBeatScheduleTests` (2) + `TrialBalanceReflectsBhphPaymentsTests` (1). Tenancy carriers 47 (unchanged — BhphPayment gained a column, not a new model). Permission classes 8 (unchanged — zero-drift streak extends to eight consecutive milestones). DRF admin surface 104 (unchanged — no new endpoints; detector is Celery-scheduled). Frontend Vitest 122 (unchanged — no frontend at M16 per §5.f Option A). No new post-LLM scrub stages. **Five §0.a M16.1 micro-decisions recorded** — all as-recommended per M10 §9 (do not count against streak). | `00a5b60` |
| M16.2 Closeout | 144 | Documentation-only per M10.8 / M11.7 / M12.8 / M13.4 / M14.5 / M15.2 precedent. Six close-out docs (this retrospective + capability matrix §7q + implementation roadmap §Milestone 16 SHIPPED entry added + planning doc frontmatter flip `active` → `shipped` + session-start refresh + M17 planning skeleton) + coordinated commit landing all M16.2 docs. **Milestone 16 — M12 BHPH payment GL post — SHIPPED.** | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a
clear re-entry path.

**M16-specific deferrals** (all
from `MILESTONE_16_PLANNING.md`
§3):

1. **Method-aware fund-flow
   routing.** M16 posts DR 100000
   Cash on Hand for every payment
   regardless of `method`. In real
   accounting, ACH lands in Bank
   Operating (110000); debit-card
   payments hit a merchant-clearing
   account before deposit; cash
   sits in the drawer until the
   nightly deposit. Re-entry: a
   deposit-workflow milestone that
   defines the reclassification
   passes.
2. **Late fee GL posting.**
   `BhphPayment.applied_to_fees`
   is always Decimal("0.00") at
   M12.2 (no fee-charging entity
   exists). M16 asserts the fees
   column is zero via
   `UnexpectedBhphPaymentFeesError`
   and doesn't post a fee-income
   line. When a BhphFee entity
   ships, the fee line (CR 440000
   BHPH Late Fee Income — account
   addition needed) can be added
   alongside the interest line.
3. **NSF / reversal handling.**
   ACH failures produce a
   downstream reversal event
   (customer's bank returns the
   draft). M16 does NOT wire NSF
   reversal — a returned payment
   would need a new BhphPayment
   Reversal entity + companion
   `reverse_journal_entry` call.
   Re-entry: a payment-reversal
   milestone modeled on M14.4
   reversal-with-reason pattern.
4. **Payment posting analytics
   on GL entries.** M12.7 shipped
   payment analytics reading
   BhphPayment directly. GL-
   derived reporting (period-
   over-period interest income,
   cash-collected trend) defers
   to a later reporting
   milestone.
5. **BHPH interest accrual
   detector.** M16 posts interest
   INCOME as payments arrive. A
   separate milestone would
   accrue interest RECEIVABLE
   (DR 132000 Accrued Interest
   Receivable — account addition
   needed / CR 430000 BHPH
   Interest Income) at period-
   end for accrual-basis
   accounting. Cash-basis posture
   holds until then.
6. **Deposit / bank
   reconciliation workflow.**
   After M16, 100000 Cash on Hand
   grows monotonically with each
   payment. The operational bank-
   deposit + reconciliation step
   (moving cash from 100000 to
   110000 Bank Operating) is a
   separate milestone. Until then,
   100000 balance is "cash + bank"
   commingled — trial balance is
   still correct, but the two are
   not separated.
7. **Payment-source FK on
   JournalEntry.** No FK from
   JournalEntry to BhphPayment.
   The `description` field
   carries "BHPH payment intake
   — BhphPayment #<pk> against
   note #<pk> (…)" for text-
   based linkage. Operator drill-
   back happens by pk. FK
   addition defers per M15 §3
   item 9 (unified GL-to-source-
   entity linkage milestone).
8. **Charge-off GL wiring.**
   Uncollectible notes eventually
   charge off (DR 550000 Bad
   Debt Expense — account
   addition needed / CR 123000
   BHPH Notes Receivable). M16
   does NOT wire charge-off. Re-
   entry: a BHPH-charge-off
   milestone once the operator
   surface is in place
   (currently no charge-off
   entity exists).
9. **Payment modification /
   deferral GL.** BHPH_OPERATIONS
   §2.5 describes payment
   modifications (skip payments,
   term extensions, deferrals) —
   none of these produce a
   BhphPayment row today. When
   they do, GL treatment
   (deferred interest income
   accrual reclass) is a separate
   milestone.
10. **Cross-run detector
    concurrency guard.** M16's
    detector uses
    `posted_at__isnull=True` for
    idempotency. Two detector
    runs racing on the same
    tenant could theoretically
    double-post if the atomic
    transaction on run N-1 hasn't
    committed when run N starts.
    M13.2 accepts this trade-off
    (Celery beat single-
    dispatcher assumption); M16
    inherits it. Re-entry: row-
    level locking or advisory
    locks if operator evidence
    surfaces double-post pain.
11. **Repossession-inventory
    transfer GL.** BHPH_OPERATIONS
    §6.6 describes post-repo
    processing that moves the
    remaining balance to
    inventory. Not wired at M16.
    Re-entry: repo-inventory
    milestone (M12.6 Repossession
    entity ships but not GL-
    wired).

**Universal deferrals (any
accounting milestone):**

- Payroll (external service).
- W-2 / 1099 generation
  (external service).
- Year-end tax return
  preparation (external CPA).
- GAAP-compliant audited
  financial reporting (out of
  scope for platform v1).
- Direct DMS integration
  (belongs to a future vendor-
  integration milestone).

**Total deferrals at M16 close:
16** (11 M16-specific + 5
universal). Matches M15's 17
within one — the M15 sale-
booking + M16 payment-posting
milestones surface almost
identical downstream deferrals
(reversal, FK linkage, variance
handling, analytics, external-
service scope).

## 4. Deviations from planned scope

Two deviations. Both net-additive.
Zero regressions.

1. **`db_index` on
   `BhphPayment.posted_at`
   dropped** from the §7 M16.1
   deliverable text. The
   canonical §5.d Option A
   language was
   `DateTimeField(null=True)` —
   matches M13.2's shape
   verbatim; the escalation to
   `db_index=True` in the M16
   handoff/session-start
   deliverable text was
   unplanned. Recorded as §0.a
   M16.1 decision 1. Rationale:
   the existing `dealership_id`
   FK index scopes the detector
   query at expected daily
   volumes; write-side index
   cost is not evidence-
   justified. Fix landed in the
   same M16.1 commit that
   shipped the code.
2. **Test count came in 30, at
   the top of the 25-30
   planning target.** Coverage
   proportional to guard count
   — the M16.1 verb has more
   distinct failure modes than
   M15.1 (cross-tenant + three
   different missing-account
   paths depending on which
   line is present + non-zero-
   fees broken-invariant +
   atomic-rollback + happy path
   for 3 branches). Each
   distinct concern got its own
   assertion. Net effect is
   comprehensive coverage
   without redundant parameter
   matrices.

## 5. Compatibility with existing surface

Every M1-M15 endpoint returns the
same shape it did at M15 close.
Every M1-M15 service verb
signature is unchanged (M16 is
purely additive — new module + new
tasks + new beat entry + new
migration column).

Enumerated:

- **M1-M8 endpoints:** unchanged.
- **M9 sale endpoint:** unchanged.
- **M10-M11 endpoints:** unchanged.
- **M12 BhphPayment endpoints:**
  unchanged. `record_payment`
  contract preserved — the new
  `posted_at` column defaults
  null on every write; the
  detector populates it later.
  Existing endpoint tests
  continue to pass.
- **M13 accounting endpoints:**
  unchanged. `admin/accounting/
  trial-balance/` now returns
  more asset-side + revenue-
  side activity as BHPH
  payments accumulate;
  `admin/accounting/journal-
  entries/list/` returns more
  entries.
- **M14 UI surfaces:** unchanged.
  The M14.3 browser now shows
  BHPH-payment entries alongside
  M13.2 cost-accrual entries
  and M15 sale-booking entries;
  the M14.2 trial balance shows
  the running cash-collected /
  interest-income / receivables-
  amortized picture.
- **M15 sale-booking:** unchanged.
  The M15 sync-sibling verb
  continues to fire on every
  `record_sale`; M16's detector
  fires independently on a
  separate schedule and does
  not touch the sale write
  path.
- **Tenancy carriers:** 47
  (unchanged — no new models).
- **Permission classes:** 8
  (unchanged — no new endpoints
  at M16). Zero-drift streak
  extends to **eight consecutive
  milestones** now: M10 + M11 +
  M12 + M13 + M14 + M15 + M16.
- **Migrations:** `0043`–`0045`
  (+1 at M16.1 — one AddField
  for `posted_at`).
- **Celery-beat task families:**
  9 → **10** (+1 at M16.1 —
  new bhph-payment daily entry
  at 11:00).
- **AI safety stack:** 17 scrub
  stages (unchanged — M16 has
  no LLM path).

## 6. Lessons

Six carry into M17+ planning.

1. **The §5-decisions-locked-at-
   open pattern held for a
   seventh milestone.** All six
   §5 decisions at M16.0 open
   confirmed as-recommended,
   matching
   M10/M11/M12/M13/M14/M15
   pattern. **64 planning-time
   as-recommended M5.1 → M16.0**
   across seven consecutive
   milestones now. The framework
   generalizes: BHPH payment
   posting — a detector-shaped
   backend integration
   milestone — resolved with the
   same shape as the sync-
   sibling M15 sale-booking
   milestone.
2. **M13.2's template scales
   almost verbatim to sibling
   detector milestones.** The
   `vehicle_cost.py` module +
   `tasks.py` pair + `CELERY_BEAT_SCHEDULE`
   entry translated to M16.1 with
   only account-code
   substitutions + 2-vs-3 line
   composition logic. The pattern
   (pure query verb + atomic
   sibling verb +
   orchestrator + Celery task
   pair + beat entry) is
   proven for detector-shaped
   GL wiring. Future M17+
   detector milestones (M10
   chargeback reversal, if
   picked; charge-off GL) can
   plan for the same near-
   verbatim mirror.
3. **Duplicating account-code
   constants across accounting
   submodules held up well.**
   M15 §0.a decision 3
   duplicated
   `_lookup_required_account`;
   M16.1 additionally duplicated
   `CASH_ACCOUNT_CODE` +
   `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`.
   The `__init__.py` re-exports
   from one canonical module
   per constant (no collision).
   Each accounting submodule
   stays self-documenting —
   readers of `bhph_payment.py`
   see the codes it uses
   without cross-file lookup.
   Evidence gate for a shared-
   constants module still not
   tripped.
4. **`UnexpectedBhphPaymentFeesError`
   as broken-invariant guard is
   a good pattern for cross-
   milestone integration
   boundaries.** M12.2 keeps
   `applied_to_fees` at zero;
   M16.1 asserts this
   invariant. If a future
   BhphFee milestone violates
   it without extending
   `post_bhph_payment_journal`,
   the orchestrator catches +
   logs + isolates the failure
   per row. The pattern makes
   milestone-to-milestone
   contracts explicit — the
   assertion IS the contract,
   and it fails loud if
   violated.
5. **Zero-drift permission-class
   posture extends to eight
   consecutive milestones.**
   M16 shipped zero endpoints
   (detector is Celery-
   scheduled, not operator-
   visible). Permission-class
   count stays at 8. Same
   lesson from M15 §6 lesson 7;
   the streak extends by one
   milestone. Future GL-wiring
   milestones with detector
   shape (M10 chargeback, if
   detector-shaped; charge-off
   GL) inherit this — no
   endpoint = no permission-
   class churn.
6. **UI-preserving backend-only
   milestones remain compact.**
   M16 shipped in 3 increments
   (planning + backend + close)
   like M15. The M14 UI surface
   continues to absorb new
   journal-entry sources
   automatically without
   additional frontend work.
   Future accounting milestones
   with detector or sibling
   shape can plan for the same
   3-increment structure until
   an operator-visible
   endpoint enters scope
   (which triggers additional
   frontend + endpoint
   increments per M14's shape).

## 7. Streak update

**64 planning-time as-recommended
M5.1 → M16.0.** Seven consecutive
milestones now (M10 + M11 + M12 +
M13 + M14 + M15 + M16) with every
§5 decision confirmed as-
recommended at planning-time open.
§0.a implementation-time micro-
decisions across M16.1 (5 in
total) do not count against the
streak per M10 §9.

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

## 8. What M16 unblocks for M17+

- **The M14 UI surfaces are now
  seeing real BHPH-payment
  data.** Before M16, M14.2
  trial balance showed M13.2
  cost-accrual + M15 sale-
  booking activity but zero
  BHPH payment amortization
  (Notes Receivable grew
  monotonically) and zero BHPH
  interest income. After M16
  every payment amortizes the
  note + recognizes interest
  income visible in the M14
  browser + trial balance.
- **M10 F&I chargeback GL
  reversal — pattern proven
  from both directions.** M15
  shipped sync-sibling; M16
  shipped detector-shape. Both
  posture templates are now
  proven; picking the right
  shape for chargeback (which
  is operator intent per event
  → likely sync-sibling per
  M15 pattern) is straightforward.
  `reverse_journal_entry`
  already ready.
- **Trial-balance materialization
  + monthly close workflow** —
  remains unblocked from M13
  §8. M14.2 could grow an
  `as_of` picker as part of
  this. M16's BHPH activity
  now makes period-over-period
  BHPH interest income + Notes
  Receivable amortization
  reports meaningful.
- **Category-group-aware GL
  mapping** for the M13.2
  detector — remains unblocked
  from M14 §8. M16 didn't
  change this equation.
- **M14 UX polish** (journal-
  entry list filters, `as_of`
  picker, sidebar nav) —
  remains unblocked; operator
  evidence on M15 + M16-
  shipped surfaces now
  starts to accumulate faster
  (two active daily-posting
  streams contributing entries).
- **Sale-side reversal
  workflow.** Unchanged from
  M15 §8. GL side ready;
  operational contract needed.
- **Post-sale VehicleCost
  variance handling.** Unchanged
  from M15 §8. Now that BHPH
  activity is also flowing
  into trial balance, phantom
  Recon WIP balances on sold
  vehicles are more visible
  as a fraction of overall
  balance sheet.
- **Method-aware fund-flow
  routing / deposit-workflow
  milestone.** New M16 unblock.
  M16.3 phantom balance in
  100000 Cash on Hand
  (payments accumulate without
  ever being reclassified to
  110000 Bank Operating) will
  surface operator questions
  about cash vs bank position
  reporting — that operator
  evidence is the trigger for
  the deposit-workflow
  milestone.
- **BhphFee entity + late-fee
  GL posting.** New M16
  unblock. The
  `UnexpectedBhphPaymentFeesError`
  guard makes the contract
  explicit — when operator
  evidence surfaces the need
  for late-fee tracking, the
  BhphFee milestone extends
  `post_bhph_payment_journal`
  with a CR fee-income line
  and removes the guard.
- **NSF / payment-reversal
  workflow.** New M16 unblock.
  ACH failures + returned
  payments produce a real
  downstream event that needs
  both an operational contract
  (what happens to the
  BhphPayment row?) and GL
  wiring (via
  `reverse_journal_entry`).
- **BHPH interest accrual
  detector.** New M16 unblock.
  M16 posts interest income on
  cash-basis (as payments
  arrive). Accrual-basis
  posting (interest RECEIVABLE
  at period-end) is a natural
  follow-on for month-end
  close discipline.
