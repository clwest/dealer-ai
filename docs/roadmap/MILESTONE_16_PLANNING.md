---
title: "Milestone 16 — M12 BHPH payment GL post"
status: shipped
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_141 (skeleton), SESSION_142 (expansion)
shipped_at_session: SESSION_144
retrospective: docs/roadmap/MILESTONE_16_RETROSPECTIVE.md
milestone: 16
milestone_name: "M12 BHPH payment GL post"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_15_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_15_PLANNING.md
  - docs/roadmap/MILESTONE_14_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_13_PLANNING.md
  - docs/roadmap/MILESTONE_13_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
---

# Milestone 16 — M12 BHPH payment GL post

> **Active planning memo.** Expanded at
> M16.0 (SESSION_142) from the skeleton
> drafted at M15.2 close. §5.a Option B
> locked at SESSION_142 open — every
> unposted BhphPayment produces a matching
> JournalEntry via a Celery-beat detector
> at 11:00 project-time daily, next open
> slot after M13.2's 10:00. Per M13 §5.d
> Option C hybrid posture (BHPH payment
> posting is elapsed condition — detector-
> shaped; sale booking was operator intent
> and shipped sync-sibling at M15).
>
> M14.3 journal-entry browser surfaces the
> resulting entries automatically. **No M16
> frontend increment** — backend-only per
> §5.f.

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
  sibling-service** — pick the shape by
  whether the trigger is operator intent
  (sync sibling per M13 §5.d Option C +
  M15.1 proof), elapsed condition
  (detector per M11-M14 precedent),
  or read-only enumeration (verb per
  M13.3 / M14.1 precedent). **M16 is
  detector-shaped** per §5.b Option A —
  BhphPayment intake is operator
  intent, but the GL post is an
  elapsed-condition consequence of that
  intake (matches operational end-of-day
  cash-reconciliation rhythm per
  BHPH_OPERATIONS §3.10).
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another (per M12
  §6 lesson 11, M13.2, M14, M15 §6
  lesson 2). Nested atomic is a no-op
  inside an existing transaction.
- **Denormalize at write; recompute in
  detectors; refresh AFTER sibling
  writes if the denormalized value
  depends on them.** Per M12 §6 lesson
  4 / M13.2 / M14 posture / M15 §6
  lesson 6. **M16 introduces
  `BhphPayment.posted_at`** denormalized
  by the detector post per M13.2
  template.
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 / M13.1
  / M14.1 posture. **`detect_unposted_
  bhph_payments`** (pure query) sits
  alongside `post_bhph_payment_journal`
  (atomic write).
- **Detector idempotency within runs
  AND across runs.** Per M12 §6 lesson
  8 / M13.2 posture. `posted_at__isnull
  =True` filter gives cross-run
  idempotency naturally.
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  (or an existing composition) by
  default (seven consecutive milestones
  now, per M15 §6 lesson 7). **M16
  adds no endpoints** — detector-shaped
  work is fired by Celery beat, not by
  operator-visible endpoint.
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson 15
  / M13.3 / M14.1 posture. **Detector
  return summary follows M13.2's
  `dict[str, Any]` shape** — matches
  the existing orchestrator return
  contract exactly.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8 / M14 lesson 6. **Zero-
  unposted-payments tenants return a
  summary with `posted_count=0`, no
  404.**
- **Money on the wire is Decimal-as-
  string** per M9.5 / M10.1 / M12
  BHPH / M13 / M14 / M15 convention.
- **Zero-noise render posture for
  count-based cards.** Per M14 §6
  lesson 6. **N/A at M16 — no
  frontend.**
- **Client-side validation matches
  server-side validation with matching
  trim posture.** Per M14 §6 lesson 5.
  **N/A at M16 — no frontend.**
- **Browser E2E verification per
  frontend increment.** Per M14 §6
  lesson 4. **N/A at M16.**
- **Frontend Vitest discipline.** Per
  M11 / M12 / M14 precedent. **N/A at
  M16.**
- **Test-fixture invariants match
  migration invariants.** Per M15 §6
  lesson 3. **`make_dealership` already
  seeds default COA** at M15.1 —
  the required accounts
  (100000 / 123000 / 430000) are all
  present for tests that use the
  helper.

### 0.a Change log — resolved decisions

*Populated at M16.0 open (this session)
and per-increment as §0.a amendments.*

**SESSION_142 M16.0 open (2026-08-02):**

- **§5.a → Option B confirmed.** User
  named M12 BHPH payment GL post as
  the M16 target. Detector-shape per
  M13 §5.d Option C hybrid; closes
  the detector half after M15 shipped
  the sync half.
- **§5.b → Option A confirmed as-
  recommended.** Detector-shape at
  11:00 project-time daily, next open
  slot after M13.2's 10:00 — matches
  BHPH_OPERATIONS §3.10 end-of-day
  cash-reconciliation rhythm and
  extends the 02:00-10:00 non-
  overlapping window pattern by one
  hour.
- **§5.c → Option A confirmed as-
  recommended.** Uniform DR to
  100000 Cash on Hand regardless of
  `method`. Method-aware fund-flow
  routing (cash → 100000, ACH →
  110000 Bank Operating, etc.)
  defers pending deposit-workflow
  milestone evidence.
- **§5.d → Option A confirmed as-
  recommended.** Add
  `BhphPayment.posted_at`
  DateTimeField(null=True) via one
  migration. Detector filters
  `posted_at__isnull=True` for cross-
  run idempotency per M13.2 template.
  FK to JournalEntry defers per M15
  §3 item 9 posture.
- **§5.e → Option A confirmed as-
  recommended.** Zero-interest
  payments skip the interest line
  (post 2-line entry: DR Cash / CR
  Notes Receivable); zero-principal
  payments skip the principal line
  (post: DR Cash / CR Interest
  Income). Both-zero payments are
  architecturally impossible
  (`allocate_payment` refuses zero-
  total amounts upstream). Matches
  M15 §5.c Option A zero-cost
  posture.
- **§5.f → Option A confirmed as-
  recommended.** No M16 frontend
  increment; M14.3 journal-entry
  browser surfaces the new entries
  automatically.
- **Streak extends to 64 planning-
  time as-recommended M5.1 → M16.0.**
  Seven consecutive milestones now
  (M10 + M11 + M12 + M13 + M14 + M15
  + M16). All six §5 decisions at
  M16.0 open confirmed as-recommended.

**SESSION_143 M16.1 close (2026-08-02):**

*Five implementation-time micro-
decisions. All as-recommended per
M10 §9 (do not count against
planning-time streak).*

1. **`db_index` dropped on
   `BhphPayment.posted_at`** —
   matches M13.2's
   `VehicleCost.posted_at` shape
   verbatim; existing
   `dealership_id` FK index
   scopes the detector query at
   expected daily volumes and
   the write-side index cost is
   not justified by evidence.
2. **`_lookup_required_account`
   duplicated verbatim** in the
   BHPH-payment module — mirrors
   M15.1 §0.a decision 3 posture
   (evidence gate for a shared-
   helper refactor not tripped).
3. **`CrossTenantGLAccountError`
   reused for cross-tenant
   BhphPayment check** — matches
   M13.2 + M15.1 cross-tenant
   posture; same fail-closed 404.
4. **`UnexpectedBhphPaymentFeesError`
   as `RuntimeError` subclass**
   — broken-invariant signal, not
   user-input error. Matches
   `MissingDefaultAccountError`
   + `UnmappedFinanceTypeError`
   posture; fires when a future
   BhphFee milestone populates
   `applied_to_fees` without
   extending this verb first.
5. **Local account-code
   constants** in the BHPH-
   payment module — duplicates
   `CASH_ACCOUNT_CODE` +
   `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`
   from `sale_booking.py`
   (accepted per M15.1 posture);
   declares new
   `BHPH_INTEREST_INCOME_ACCOUNT_CODE`.
   `__init__.py` re-exports the
   new constant only (avoids
   name collision with
   `sale_booking`'s existing
   exports).

**M16.1 delta:** 4,296 → **4,326
pass** (+30 tests, 0 regressions).
Frontend Vitest: 122 (unchanged).
Migrations 0043-0044 → **0043-
0045** (+1). Tenancy carriers 47
(unchanged — BhphPayment gained a
column, not a new model). DRF
admin surface 104 (unchanged).
Frontend operator routes 20
(unchanged). Permission classes 8
(unchanged — zero-drift streak
extends to **eight consecutive
milestones** now: M10 + M11 + M12
+ M13 + M14 + M15 + M16). Celery-
beat task families 9 → **10**
(new bhph-payment daily entry at
11:00).

## 1. Business questions this milestone answers

Four operator-workflow questions,
each tied to a specific BHPH-payment
or accounting surface. Every question
was unanswerable before M16 (M12.2
shipped BhphPayment intake with
principal / interest / fees split
denormalization; M13 shipped the GL
substrate; M14 shipped the UI to
view it — but no wire connects
`record_payment` to `post_journal_
entry`).

### Q1. When a BHPH customer pays, does the GL reflect it?

**Before M16:** No. `record_payment`
writes the BhphPayment row +
populates the split columns. No
corresponding journal entry is
posted. Cash received doesn't appear
in the trial balance; the note
receivable balance doesn't decrease.

**After M16:** Yes. Every unposted
BhphPayment is picked up by the
11:00 detector and posts a matching
balanced JournalEntry via
`services/accounting/post_journal_
entry`. The M14.2 trial balance
renders the running BHPH-payment
activity daily (within one detector
cycle of the operator recording the
payment).

### Q2. What's the running BHPH interest income picture at the GL level?

**Before M16:** Not tracked at the GL
level. `BhphPayment.applied_to_
interest` carries the split at the
row level, but the GL side is empty.
A period-end trial balance shows zero
BHPH interest income regardless of
collection activity.

**After M16:** Every payment credits
**430000 BHPH Interest Income** for
`applied_to_interest`. Trial balance
430000 reflects the sum of collected
interest for the period. This is the
first non-zero BHPH interest revenue
signal the platform emits at the GL.

### Q3. Does the BHPH Notes Receivable balance amortize correctly?

**Before M16:** No. M15 sale-booking
DRs **123000 BHPH Notes Receivable**
for the full note balance at sale
time. Nothing ever CRs it. The
account grows monotonically with
each BHPH sale and never amortizes.

**After M16:** Yes. Every payment
CRs **123000** for
`applied_to_principal`. The account
balance amortizes down to zero over
the life of each note, matching the
operator's mental model of "note
receivable outstanding" per
BHPH_OPERATIONS §5.1 portfolio
composition.

### Q4. Does the cash side of the payment flow into the GL?

**Before M16:** No. Operator records
the payment in the platform;
separately deposits cash / receives
ACH / etc. Neither side lands in
the GL. Reconciliation between the
BhphPayment table and the actual
cash flow requires manual work.

**After M16:** Yes. Every payment
DRs **100000 Cash on Hand** for the
full payment `amount`. Method-aware
routing (cash vs ACH vs debit)
defers per §5.c Option A — the
deposit-workflow reclassification
(cash → bank, merchant-clearing →
bank) is a separate milestone. But
the aggregate cash-in signal is now
in the GL.

## 2. What existing primitives extend

M16 is another poster child for
"additive extension over fork"
(M11.1 / M12.3 / M13.2 / M14.1 /
M15.1 pattern). One new module +
one Celery-beat family + one small
migration.

- **`services/accounting/post_journal_entry`**
  — the M13.1 atomic sibling
  target. Consumes `JournalLineInput`
  tuples; enforces balanced
  double-entry + fail-closed cross-
  tenant. Zero API changes needed.
- **`services/accounting/vehicle_
  cost.py`** — the M13.2 template.
  New `services/accounting/bhph_
  payment.py` mirrors its shape
  verbatim (`detect_unposted_bhph_
  payments`, `post_bhph_payment_
  journal`, `post_all_unposted_
  bhph_payments_for_dealership`
  orchestrator).
- **`services/accounting/tasks.py`**
  — extends with two new Celery
  tasks (`post_bhph_payment_
  journals_for_dealership` +
  `post_bhph_payment_journals_for_
  all_tenants`) mirroring the M13.2
  pair.
- **`BhphPayment` model** — gains
  one new nullable `posted_at`
  DateTimeField via a single
  migration. Denormalized by the
  detector on successful post per
  M13.2's `VehicleCost.posted_at`
  template.
- **Default COA** — all three
  required accounts already seeded
  per M13.1 migration `0043`:
  100000 Cash on Hand, 123000 BHPH
  Notes Receivable, 430000 BHPH
  Interest Income.
- **`services/accounting/vehicle_
  cost._lookup_required_account`**
  — template for M16's account
  lookup (raises `MissingDefaultAccountError`).
  Duplicated verbatim per M15.1
  §0.a decision 3 (evidence gate
  for a shared-helper refactor not
  tripped).
- **`_auth_helpers.make_dealership`**
  — already seeds default COA per
  M15.1 §0.a decision 8. All M16
  tests using the helper have the
  required accounts.
- **M14.3 journal-entry browser** —
  surfaces the new BHPH-payment
  entries automatically with
  descriptive `description`
  ("BHPH payment #<pk> for note
  #<pk>") + line memos. Zero UI
  changes needed.
- **M14.2 trial balance page** —
  renders the new 100000 / 123000
  / 430000 activity. Zero UI
  changes needed.

## 3. What's NOT in this milestone (deferrals)

Every deferral has a clear re-entry
path. **Eleven M16-specific + five
universal = 16 deferrals**, matching
M15's deferral density.

**M16-specific deferrals:**

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
   passes (cash → bank,
   merchant clearing → bank, ACH →
   bank).
2. **Late fee GL posting.**
   `BhphPayment.applied_to_fees`
   is always Decimal("0.00") at
   M12.2 (no fee-charging entity
   exists). M16 asserts the fees
   column is zero and doesn't post
   a fee-income line. When a
   BhphFee entity ships in a
   future milestone, the fee line
   (CR 440000 BHPH Late Fee Income
   — account addition needed) can
   be added alongside the interest
   line.
3. **NSF / reversal handling.**
   ACH failures produce a
   downstream reversal event
   (customer's bank returns the
   draft). M16 does NOT wire NSF
   reversal — a returned payment
   would need a new `BhphPayment
   Reversal` entity + companion
   `reverse_journal_entry` call.
   Re-entry: a payment-reversal
   milestone modeled on M14.4
   reversal-with-reason pattern.
4. **Payment posting analytics on
   GL entries.** M12.7 shipped
   payment analytics reading
   BhphPayment directly. GL-
   derived reporting (period-over-
   period interest income, cash-
   collected trend) defers to a
   later reporting milestone.
5. **BHPH interest accrual detector.**
   M16 posts interest INCOME as
   payments arrive. A separate
   milestone would accrue interest
   RECEIVABLE (DR 132000 Accrued
   Interest Receivable / CR 430000
   BHPH Interest Income) at
   period-end for accrual-basis
   accounting. Cash-basis
   posture holds until then.
6. **Deposit / bank reconciliation
   workflow.** After M16, 100000
   Cash on Hand grows monotonically
   with each payment. The operational
   bank-deposit + reconciliation
   step (moving cash from 100000
   to 110000 Bank Operating) is a
   separate milestone. Until then,
   100000 balance is "cash + bank"
   commingled — trial balance is
   still correct, but the two are
   not separated.
7. **Payment-source FK on
   JournalEntry.** No FK from
   JournalEntry to BhphPayment.
   The `description` field carries
   "BHPH payment #<pk> for note
   #<pk>" for text-based linkage.
   Operator drill-back happens by
   pk. FK addition defers per M15
   §3 item 9 (unified GL-to-source
   linkage milestone).
8. **Charge-off GL wiring.**
   Uncollectible notes eventually
   charge off (DR 550000 Bad Debt
   Expense — account addition
   needed / CR 123000 BHPH Notes
   Receivable). M16 does NOT wire
   charge-off. Re-entry: a BHPH-
   charge-off milestone once the
   operator surface is in place
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
    detector uses `posted_at__isnull
    =True` for idempotency. Two
    detector runs racing on the
    same tenant could
    theoretically double-post if
    the atomic transaction on run
    N-1 hasn't committed when run
    N starts. M13.2 accepts this
    trade-off (Celery beat single-
    dispatcher assumption); M16
    inherits it. Re-entry:
    row-level locking or advisory
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

**Universal deferrals (any accounting
milestone):**

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

- **M12.2 `test_m122_bhph_payment_
  model.py` + `test_m122_bhph_
  payment_service.py`** —
  `BhphPayment` model + `record_
  payment` verb tests. M16 adds
  a `posted_at` nullable field
  (default null) — existing
  tests continue to pass; new
  tests assert `posted_at` is
  None on write and populated
  after detector run.
- **M12.2 `test_m122_bhph_payment_
  allocation.py`** — `allocate_
  payment` contract tests.
  Unchanged — M16 doesn't touch
  allocation.
- **M12.2 `test_m122_bhph_payment_
  endpoint.py`** — endpoint
  tests. Unchanged — no endpoint
  changes at M16.
- **M13.1 `test_m131_accounting.py`**
  — `post_journal_entry` contract
  tests. M16 exercises the same
  verb; contract tests continue
  to hold.
- **M13.2 `test_m132_cost_
  reconciliation.py`** — the
  M13.2 detector pattern that
  M16 mirrors. Contract holds
  independently; the tests
  document the template.
- **M14.1 `test_m141_accounting_
  list_endpoint.py`** — journal-
  entry list endpoint. M16 posts
  more entries; the list endpoint
  must return them; no contract
  change.
- **Tenancy carrier count test**
  — M16 adds zero new models
  (BhphPayment gains a column,
  not a new model). `>=47`
  continues to hold.
- **Permission-class count test**
  — M16 adds zero new endpoints.
  `=8` continues to hold (zero-
  drift streak extends to eight
  consecutive milestones).

## 5. Load-bearing decisions

Six decisions. **All six confirmed
as-recommended at SESSION_142 M16.0
open.** Streak extends to 64
planning-time as-recommended M5.1 →
M16.0 (seven consecutive milestones
now).

### 5.a `[RESOLVED at SESSION_142 open]` — Milestone target selection

**Question.** Which candidate from
the M15 retrospective §8 unblocked-
work list defines M16 scope?

**Decision.** **Option B — M12 BHPH
payment GL post.** User named at
SESSION_142 open.

**Rationale.** (1) Closes the M13
§5.d Option C hybrid architecturally
— M15 shipped the sync-sibling half
(sale booking, operator intent);
M16 ships the detector half (BHPH
payment posting, elapsed condition).
(2) Substrate 100% ready — every
required primitive shipped in prior
milestones (BhphPayment entity at
M12.2; post_journal_entry at M13.1;
required COA accounts at M13.1;
M14 UI at M14). (3) Pattern reuse
is near-total — M13.2's `vehicle_
cost.py` module + tasks.py +
CELERY_BEAT_SCHEDULE entry translates
almost verbatim to M16 (different
source entity, different accounts,
same posture). (4) Zero-UI M14
surface picks up new entries
automatically. (5) 11:00 project-
time is the next open Celery slot,
extending the 02:00-10:00 non-
overlapping window pattern by one
hour. (6) High-frequency operational
value — BHPH dealers process daily
payments; every one is currently
invisible to the GL.

### 5.b `[RESOLVED at SESSION_142 open]` — Detector shape and schedule slot

**Question.** How does M16 fire the
GL post? Sync-sibling inside
`record_payment` per M15 pattern,
or detector-shaped per M13.2
pattern?

- **Option A** — detector at 11:00
  project-time daily, next open
  slot after M13.2's 10:00. Per
  M13 §5.d Option C hybrid
  categorization (M15 §8 explicitly
  named this as detector-shaped).
  Follows M13.2's `post_all_
  unposted_costs_for_dealership`
  orchestrator template.
- **Option B** — sync-sibling
  inside `record_payment`. Same
  pattern as M15.1. Each payment
  posts to the GL immediately in
  the same atomic transaction.
- **Option C** — hourly detector
  instead of daily. Would give
  faster feedback on trial-balance
  BHPH activity.

**Recommendation drafted.** **Option A.**
Rationale: (1) M13 §5.d Option C
hybrid explicitly categorized BHPH
payment posting as detector-shaped;
M15 §8 named it as such. Following
the pre-committed architectural
decision. (2) Matches BHPH_OPERATIONS
§3.10 end-of-day cash-reconciliation
rhythm — the daily batch mirrors
the operational cadence. (3)
Failure isolation — one bad payment
row does not block the operator's
next intake (M13.2 pattern:
`post_all_unposted_costs_for_
dealership` catches per-row
failures + continues). Sync-sibling
(Option B) would either roll back
the payment intake or leak orphan
payments if the GL post fails. (4)
11:00 is the next open slot; the
non-overlapping window pattern
(02:00-10:00) continues cleanly.
(5) Option C (hourly) is
premature optimization — daily
matches operator rhythm and
M14.2 trial-balance workflow.
Detector cadence can shorten
later if operator evidence
demands.

### 5.c `[RESOLVED at SESSION_142 open]` — Cash-side account mapping (uniform vs method-aware)

**Question.** How does M16 choose
which asset account to debit for
the cash side of each payment?

- **Option A** — uniform DR to
  100000 Cash on Hand regardless
  of `method`. Method-aware
  routing defers.
- **Option B** — method-aware
  routing from day 1:
  `cash` → 100000 Cash on Hand;
  `ach` → 110000 Bank Operating;
  `debit` → 110000 Bank Operating
  (or 111000 Merchant Clearing —
  account addition needed);
  `check` → 100000 Cash on Hand;
  `other` → 100000 Cash on Hand.
- **Option C** — uniform DR to a
  new 111000 Undeposited Funds
  account. Requires COA extension.
  Reconciliation workflow moves
  balances to 100000/110000 later.

**Recommendation drafted.** **Option A.**
Rationale: (1) Matches M13.2's
uniform-mapping posture (§0.a M13.2
decision 2) — deferred category-
aware routing pending operator
evidence. (2) Method-aware routing
(Option B) implicitly encodes a
deposit-workflow assumption
(when does cash land in the bank?)
that belongs to a separate
milestone. Doing it here would be
scope creep. (3) Trial balance
stays correct at the aggregate
"cash" level (100000 = cash +
undeposited); the split defers to
the deposit-workflow milestone.
(4) Option C requires a COA
addition; deferring the COA
extension until the deposit-
workflow milestone keeps M16 as a
zero-COA-change milestone. (5)
`SALE_FINANCE_TYPE_CASH` at M15
posts DR 100000 already; M16
maintains the same account for
BHPH payment cash side —
consistent operator mental model.

### 5.d `[RESOLVED at SESSION_142 open]` — Detector idempotency signal

**Question.** How does the detector
know which BhphPayment rows are
unposted?

- **Option A** — add
  `BhphPayment.posted_at`
  DateTimeField(null=True) via
  one migration. Detector filters
  `posted_at__isnull=True`.
  Matches M13.2's `VehicleCost.
  posted_at` verbatim.
- **Option B** — no schema change.
  Detector queries "is there a
  JournalEntry with description
  matching this payment?" as the
  idempotency signal. Slower
  (join or subquery per detector
  run) + fragile (description
  format becomes a load-bearing
  contract).
- **Option C** — add BOTH
  `posted_at` and FK to
  JournalEntry. Cleanest end-
  state but M15 §3 item 9
  explicitly deferred FK-to-
  source-entity linkage pending
  operator drill-back evidence.

**Recommendation drafted.** **Option A.**
Rationale: (1) Matches M13.2's
proven pattern verbatim. Zero
novelty. (2) Migration is a single
`AddField` — one file, zero data
migration needed (all existing
rows default null, become
detector-eligible on next run
per §5.h posture below). (3)
Option C is more schema than
current evidence justifies; the
FK addition should wait until a
unified GL-to-source-entity
milestone (per M15 §3 item 9).
(4) Option B ties the description
format to correctness, which is
brittle — a well-meaning edit to
description could silently
double-post. (5) Test-fixture
invariants per M15 §6 lesson 3
already lean on structural fields
(migrations seed COA); adding
`posted_at` continues that
posture.

### 5.e `[RESOLVED at SESSION_142 open]` — Zero-amount line handling

**Question.** BhphPayment carries
three denormalized split columns:
`applied_to_fees` / `applied_to_
interest` / `applied_to_principal`.
At M12.2 the fees column is always
zero. Early payoffs can produce
`applied_to_interest == 0`;
interest-only payments can produce
`applied_to_principal == 0`. What
happens when a line would be zero?

- **Option A** — skip the zero
  line entirely. A payment with
  interest=0 posts a 2-line entry
  (DR Cash / CR Notes Receivable
  only); a payment with
  principal=0 posts a 2-line
  entry (DR Cash / CR Interest
  Income only). Fees always
  skipped at M16 per §3 item 2
  deferral.
- **Option B** — post a 3-line
  entry with zero on the zero
  side. M13.1's
  `InvalidJournalLineError`
  rejects both-zero lines, so
  this is architecturally
  impossible.
- **Option C** — reject the
  payment posting when any split
  is zero. Would force operator
  to reject early payoffs or
  interest-only payments.

**Recommendation drafted.** **Option A.**
Rationale: (1) Option B is
architecturally impossible per
M13.1. (2) Option C would reject
legitimate operational payments —
early payoffs happen
(BHPH_OPERATIONS §2.7) and
interest-only payments happen
(§9.13). (3) Skipping zero lines
preserves the balanced double-
entry invariant with fewer lines
(DR Cash for the payment amount;
CR the non-zero component). (4)
Matches M15 §5.c Option A zero-
cost posture — skip the pair,
log warning if unexpected.
Interest-zero on non-early
payoffs is worth a debug log;
interest-zero on early payoff
is normal. (5) Both-zero
payments are architecturally
impossible upstream —
`allocate_payment` refuses
zero-amount payments (M12.2
`OverpaymentError` shape
implicitly covers this via
the outstanding-balance check).

### 5.f `[RESOLVED at SESSION_142 open]` — Operator UI at M16

**Question.** Does M16 ship any
new frontend surface?

- **Option A** — no UI at M16;
  M14.3 journal-entry browser
  surfaces the new entries
  automatically.
- **Option B** — add a "GL post
  status" column on the M12.2
  BHPH payment list endpoint.
- **Option C** — extend M14.3
  with a "BHPH payment #X" filter
  or drill-back link.

**Recommendation drafted.** **Option A.**
Rationale: (1) Matches M15 §5.f
Option A posture (backend-only
when UI substrate already
surfaces result). (2) M14.3
renders the new entries with
descriptive `description` field
("BHPH payment #<pk> for note
#<pk>") + line memos — operator
can find BHPH-payment entries
by scrolling or search-by-
description today. (3) UI polish
(filter, drill-back, list column)
is the shape of the M14 UX
polish candidate (Option E from
the M16 skeleton §1); folding it
into M16 would violate Project
Rule 4 scope discipline. (4)
M14.3 was designed to be the
audit-trail surface for any
JournalEntry regardless of
source — same reasoning as M15
§5.f validated at M15.2.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
   §6 (eight lessons carry into M16) +
   §8 (M15 unblocked work — BHPH
   payment detector explicitly named)
6. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5.d Option C hybrid GL-posting
   trigger shape — M16 exercises the
   detector half
7. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §2 (M13.2 template that M16
   mirrors)
8. `docs/CAPABILITY_MATRIX.md` §7p
9. `docs/research/BHPH_OPERATIONS_MAPPING.md`
   §3 (payment operations),
   §3.10 (daily payment posting
   rhythm), §11.5 (BHPH ↔
   accounting dependencies)
10. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
    §1.1 (chart of accounts —
    100000 / 123000 / 430000)

## 7. Sequencing

**One code increment + one close-
out + one planning (this one) =
three total.** Matches M15's shape
per M15 §6 lesson 8 (backend-only
milestones compact to 2-3
increments).

### Increment 0 (M16.0) — Planning refinement + decision review

**Scope.** SESSION_142 (this
session). Target selection (§5.a)
confirmed at open; §5.b-§5.f
drafted with recommendations for
user confirmation before M16.1
code. Full memo expansion (this
document). Handoff at
`docs/handoffs/SESSION_142_m16_
inc0_planning.md`.

**Deliverable.**
- This planning memo, expanded
  from the M15.2 skeleton.
- §0.a change log with §5.a
  resolved + §5.b-§5.f pending
  confirmation → resolved.
- Session handoff.
- `00-START-NEXT-SESSION.md`
  overwritten with M16.1
  priority.

**Backend baseline unchanged:**
4,296 pass, 1 skipped, 0 fail.
Frontend Vitest unchanged: 122
pass.

### Increment 1 (M16.1) — Backend: BHPH payment GL detector

**Scope.** Next session. Single
backend increment. All M16 write-
path work lands here.

**Deliverable.**
- Migration `0045_m161_bhph_
  payment_posted_at.py` adding
  `BhphPayment.posted_at
  DateTimeField(null=True,
  blank=True)` per §5.d Option A.
  No `db_index` — matches M13.2's
  `VehicleCost.posted_at` shape
  verbatim; the existing
  `dealership_id` FK index scopes
  the detector query and expected
  daily volume doesn't justify the
  write-side index cost.
- New `services/accounting/bhph_
  payment.py` module mirroring
  `vehicle_cost.py` shape:
  - `detect_unposted_bhph_
    payments(*, dealership) ->
    QuerySet[BhphPayment]` — pure
    query, no writes.
  - `post_bhph_payment_journal(
    *, dealership, bhph_payment,
    posted_at=None) ->
    BhphPayment` — atomic sibling
    verb. Composes 2- or 3-line
    JournalEntry per §5.c Option
    A (DR 100000 Cash) + §5.e
    Option A (CR 430000 Interest
    Income if non-zero interest;
    CR 123000 BHPH Notes
    Receivable if non-zero
    principal; fees always
    skipped per §3 item 2).
  - `post_all_unposted_bhph_
    payments_for_dealership(*,
    dealership, now=None) ->
    dict[str, Any]` — orchestrator
    matching M13.2's return
    shape exactly.
- Extend `services/accounting/
  tasks.py` with two new Celery
  tasks:
  - `post_bhph_payment_journals_
    for_dealership(*,
    dealership_id) -> dict`.
  - `post_bhph_payment_journals_
    for_all_tenants() -> dict`.
- Add `bhph-payment-post-daily-
  11-00` entry to
  `CELERY_BEAT_SCHEDULE` in
  `dealer_kit/settings.py` at
  `crontab(hour=11, minute=0)`.
- Extend `services/accounting/
  __init__.py` `__all__` for the
  new verbs + constants + any new
  error class.
- Focused tests (~25-30 target)
  in new `tests/test_m161_bhph_
  payment_gl.py`:
  - `detect_unposted_bhph_
    payments` returns correct
    rows (posted_at IS NULL only,
    tenant-scoped, ordered).
  - `post_bhph_payment_journal`
    happy path: balanced entry,
    correct 3 lines for
    principal+interest payment.
  - Zero-interest payment: 2-line
    entry (DR Cash / CR Notes
    Rcv), Interest Income line
    skipped.
  - Zero-principal (interest-
    only) payment: 2-line entry
    (DR Cash / CR Interest
    Income).
  - `posted_at` denormalized on
    success.
  - Cross-tenant BhphPayment
    raises `CrossTenantGLAccountError`
    → 404 shape (fail-closed).
  - Missing account raises
    `MissingDefaultAccountError`.
  - Fees column non-zero raises
    a broken-invariant error
    (asserts the M12 zero-fees
    assumption).
  - Orchestrator posts all
    unposted rows for one tenant.
  - Orchestrator per-row failure
    isolation (one bad row does
    not block the rest).
  - Idempotency: second run
    posts nothing.
  - Celery task `post_bhph_
    payment_journals_for_
    dealership` calls the
    orchestrator.
  - Celery task `post_bhph_
    payment_journals_for_all_
    tenants` enqueues per-tenant
    tasks.
  - Beat schedule registration
    test (mirrors M13.2 test).
  - Trial balance reflects new
    entries.
- No new endpoints.
- No new permission classes.
- No new post-LLM scrub stages.
- Tenancy carriers: 47 (unchanged
  — BhphPayment gains a column,
  not a new model).
- Permission classes: 8 (unchanged
  — no endpoint changes).
- DRF admin surface: 104
  (unchanged).
- Celery-beat task families:
  9 → 10 (new bhph-payment daily
  entry at 11:00).

**Backend baseline target:**
4,296 → ~4,321-4,326 pass (+25-
30 tests, 0 regressions).
Frontend Vitest: unchanged.

### Increment 2 (M16.2) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7q + roadmap
flip + M17 planning skeleton per
standing user directive (M10.8 /
M11.7 / M12.8 / M13.4 / M14.5 /
M15.2 precedent).

**Deliverable.**
- `docs/roadmap/MILESTONE_16_
  RETROSPECTIVE.md` written at
  M16.2 close.
- `docs/CAPABILITY_MATRIX.md`
  §7q section describing the M16
  BHPH-payment GL-post surface.
- `docs/roadmap/IMPLEMENTATION_
  ROADMAP.md` §Milestone 16
  SHIPPED entry added.
- Frontmatter flip on this doc:
  `status: active` → `status:
  shipped`.
- `docs/roadmap/MILESTONE_17_
  PLANNING.md` skeleton for the
  M16 §8 unblocked-work list.
- `00-START-NEXT-SESSION.md`
  overwritten with M17.0
  priority.
- Coordinated commit landing all
  M16.2 docs together.

**Backend baseline at M16 close:**
~4,321-4,326 pass (M16.1 delta
sustained; no code changes at
M16.2).

---

*Full memo. All six §5 decisions
confirmed as-recommended at SESSION_142
M16.0 open. M16.1 code shipped at
SESSION_143. M16 SHIPPED at
SESSION_144 M16.2 close.*

## Closing note (M16.2)

Milestone 16 shipped at SESSION_144
per the M10.8 / M11.7 / M12.8 /
M13.4 / M14.5 / M15.2 close-out
precedent. Three increments (M16.0
planning + M16.1 backend + M16.2
close-out) — matching M15's shape
per M15 §6 lesson 8 (backend-only
milestones compact to 3
increments).

**Backend delta:** 4,296 → **4,326
pass**, 1 skipped, 0 fail (+30
tests, zero regressions — exactly
the top of the 25-30 planning
target). **Frontend Vitest: 122
pass** (unchanged — no frontend at
M16 per §5.f Option A). **One
migration shipped at M16.1**
(`0045_m161_bhph_payment_posted_at`
— one AddField for detector
idempotency). DRF admin surface
104 (unchanged). Frontend operator
routes 20 (unchanged). Tenancy
carriers 47 (unchanged —
BhphPayment gained a column, not
a new model). Permission classes
8 (unchanged — zero-drift streak
extends to **eight consecutive
milestones**: M10 + M11 + M12 +
M13 + M14 + M15 + M16). Celery-
beat task families 9 → **10**
(new bhph-payment daily entry at
11:00 project-time).

**Streak update:** 64 planning-
time as-recommended M5.1 → M16.0.
Seven consecutive milestones with
every §5 decision confirmed as-
recommended at planning-time open.
Five §0.a M16.1 micro-decisions do
not count against the streak per
M10 §9.

Cross-links:

- Delivery record → `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
- Shipped surface → `docs/CAPABILITY_MATRIX.md` §7q
- Roadmap entry → `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 16
- Session handoffs → `docs/handoffs/SESSION_142_m16_inc0_planning.md`
  · `docs/handoffs/SESSION_143_m16_inc1_backend.md`
  · `docs/handoffs/SESSION_144_m16_close.md`
