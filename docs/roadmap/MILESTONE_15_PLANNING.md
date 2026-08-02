---
title: "Milestone 15 — M9 sale-booking GL post"
status: shipped
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_138 (skeleton), SESSION_139 (expansion)
shipped_at_session: SESSION_141
retrospective: docs/roadmap/MILESTONE_15_RETROSPECTIVE.md
milestone: 15
milestone_name: "M9 sale-booking GL post"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_14_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_14_PLANNING.md
  - docs/roadmap/MILESTONE_13_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_13_PLANNING.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
---

# Milestone 15 — M9 sale-booking GL post

> **Active planning memo.** Expanded at
> M15.0 (SESSION_139) from the skeleton
> drafted at M14.5 close. §5.a Option A
> locked at SESSION_139 open — every sold
> vehicle produces a matching JournalEntry
> via a sync `@transaction.atomic` sibling-
> service call inside
> `services/sale/record_sale`. Per M13 §5.d
> Option C hybrid posture (sale booking is
> operator intent — synchronous;
> M2 cost accrual + M12 BHPH payment
> posting remain detector-shaped for
> elapsed-condition triggers).
>
> M14.3 journal-entry browser surfaces the
> resulting entries automatically with
> `posted_by_username` populated from the
> sale-booking user. **No M15 frontend
> increment** — backend-only per §5.f.

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
  **M15 is neither — it's synchronous
  sibling-service.** Per M13 §5.d.
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` when one
  service verb calls another (per M12
  §6 lesson 11 and M13.2 / M14 sibling-
  package validation of the pattern).
  **`record_sale` is already atomic;
  the new sibling-service calls
  inherit that transaction.**
- **Denormalize at write; recompute in
  detectors.** Per M12 §6 lesson 4 /
  M13.2 / M14 posture. **Sale-booking
  posts at write time; no denormalized
  `posted_at` on Sale — the presence of
  a JournalEntry with `Sale of stock
  #X` in the description is the audit
  trail.**
- **Split pure verbs from write
  verbs.** Per M12 §6 lesson 3 / M13.1
  / M14.1 posture.
- **Detector idempotency within runs.**
  Per M12 §6 lesson 8 / M13.2 posture.
  **M15 is not a detector — idempotency
  is enforced by the existing M9
  `SaleAlreadyExistsError` guard which
  short-circuits before the GL post
  is attempted.**
- **Zero-drift permission-class
  posture.** Reuse
  `IsSalesManagerOrOwnerAtActiveDealership`
  by default (six consecutive
  milestones now, per M14 §6 lesson
  10). **M15 adds no endpoints —
  posting is triggered from the
  existing `views_sale.py` create
  endpoint.**
- **Frozen dataclass output for
  aggregators.** Per M12 §6 lesson 15
  / M13.3 / M14.1 posture.
- **Zero-portfolio semantics as first-
  class response state.** Per M13 §6
  lesson 8 / M14 lesson 6.
- **Money on the wire is Decimal-as-
  string** per M9.5 / M10.1 / M12
  BHPH / M13 / M14 convention.
- **Zero-noise render posture for
  count-based cards.** Per M14 §6
  lesson 6.
- **Client-side validation matches
  server-side validation with matching
  trim posture.** Per M14 §6 lesson 5.
- **Browser E2E verification per
  frontend increment.** Per M14 §6
  lesson 4. **M15 has no frontend
  increment — this lesson binds on
  the next UI milestone.**
- **Frontend Vitest discipline.** Per
  M11 / M12 / M14 precedent. **N/A at
  M15.**

### 0.a Change log — resolved decisions

*Populated at M15.0 open (this session)
and per-increment as §0.a amendments.*

**SESSION_139 M15.0 open (2026-08-02):**

- **§5.a → Option A confirmed.** User
  named M9 sale-booking GL post as the
  M15 target. M13 retrospective §8
  primary anchor; sale-booking is the
  highest-frequency operational write
  path that the M14 UI already surfaces
  with zero additional frontend work.
- **§5.b → Option A confirmed as-
  recommended.** Finance-type-aware
  three-way branch (cash → 100000;
  retail → 120000; bhph → 123000).
- **§5.c → Option A confirmed as-
  recommended.** Zero-total-investment
  sales skip the COGS/Recon-WIP pair,
  post revenue-only, log a warning.
- **§5.d → Option A confirmed as-
  recommended.** Un-posted VehicleCost
  rows for the sold vehicle flush
  synchronously inside `record_sale`
  via `post_vehicle_cost_journal`
  before the sale-booking journal
  posts.
- **§5.e → Option A confirmed as-
  recommended.** Post-sale VehicleCost
  rows continue to post to Recon WIP
  per M13.2; phantom balance accepted
  as §3 item 11 deferral pending
  operator evidence.
- **§5.f → Option A confirmed as-
  recommended.** No M15 frontend
  increment; M14.3 journal-entry
  browser surfaces the new entries
  automatically.
- **Streak extends to 58 planning-
  time as-recommended M5.1 → M15.0.**
  Six consecutive milestones now (M10
  + M11 + M12 + M13 + M14 + M15). All
  six §5 decisions at M15.0 open
  confirmed as-recommended.

**SESSION_140 M15.1 close (2026-08-02):**

*Nine implementation-time micro-
decisions. All as-recommended per
M10 §9 (do not count against
planning-time streak).*

1. **Zero-value COGS pair skipped
   via `> Decimal("0.00")` guard**
   — handles negative-total-
   investment edge via explicit
   `else` warn-log branch.
2. **Un-posted-cost flush uses
   `detect_unposted_costs(...).filter(vehicle=vehicle)`**
   — reuses M13.2's tenant-scoped
   filter rather than adding a
   per-vehicle detector verb.
3. **`_lookup_required_account`
   duplicated in the sale-booking
   module** — mirrors M13.2
   verbatim; not promoted to a
   shared helper (evidence gate
   not tripped).
4. **`CrossTenantGLAccountError`
   reused for cross-tenant Sale
   check** — matches M13.2
   VehicleCost cross-tenant
   posture; same fail-closed 404.
5. **`UnmappedFinanceTypeError`
   as `RuntimeError` subclass**
   — broken-invariant signal, not
   user-input error (matches
   `MissingDefaultAccountError`
   posture).
6. **`gross_realized` refreshed
   AFTER the cost flush** — so
   the denormalized value on the
   Sale row matches the COGS
   line the sale-booking journal
   posts.
7. **JournalEntry description
   text carries `Sale #<pk> of
   stock <stock>
   (<finance_type_display>)`** —
   operator drill-back at M14.3
   browser without an FK
   addition (§3 item 9 deferral
   held).
8. **`_auth_helpers.make_dealership`
   extended to seed default
   COA** — brings test
   dealerships in line with the
   M13.1 migration invariant.
9. **`test_m9_sale_computation.py`
   patched inline** (four
   `Dealership.objects.create`
   calls + `seed_default_coa`
   import) rather than migrated
   to `make_dealership` — keeps
   file's slug conventions
   stable.

**M15.1 delta:** 4,277 → **4,296
pass** (+19 tests, 0 regressions).
Frontend Vitest: 122 (unchanged).
Migrations: 0043-0044 (unchanged).
Tenancy carriers 47 (unchanged).
DRF admin surface 104 (unchanged).
Frontend operator routes 20
(unchanged). Permission classes 8
(unchanged — zero-drift streak
extends to seven consecutive
milestones).

## 1. Business questions this milestone answers

Four operator-workflow questions, each
tied to a specific accounting or M9-
sale surface. Every question was
unanswerable before M15 (M9 shipped the
Sale entity + `gross_realized`
denormalization; M13 shipped the GL
substrate; M14 shipped the UI to view
it — but no code wire connects
`record_sale` to `post_journal_entry`).

### Q1. When a sale closes, does the GL reflect it?

**Before M15:** No. `record_sale`
writes the Sale row + populates
`gross_realized`. No corresponding
journal entry is posted. The trial
balance is stale relative to the
sales pipeline.

**After M15:** Yes. Every successful
`record_sale` call synchronously
posts a matching balanced
JournalEntry via
`services/accounting/post_journal_entry`.
The M14.2 trial balance renders the
current sales activity in real time
(within the same request that recorded
the sale).

### Q2. Which receivable did we book against?

**Before M15:** Not tracked at the GL
level. `Sale.finance_type` and
`Sale.lender_name` carry the info at
the operational entity level, but the
CIT / Cash / BHPH Notes Receivable
schedules the accounting department
needs are absent.

**After M15:** The revenue-side debit
posts against the finance-type-appropriate
receivable account:

- `cash` → **100000 Cash on Hand**
- `retail` → **120000 Contracts in Transit**
- `bhph` → **123000 BHPH Notes Receivable**

The M14.3 journal-entry detail page
surfaces the account codes + names
per line, so operators can drill from
the sale to the specific receivable
row.

### Q3. What's the running gross-profit picture at the GL level?

**Before M15:** `Sale.gross_realized`
is denormalized on the row and
aggregated by M9.3 analytics. But the
GL side (Revenue - COGS) is empty. A
period-end trial balance shows zero
revenue and zero COGS regardless of
sales activity.

**After M15:** Every sale posts
matching **400000 Vehicle Sales — Retail**
credit for `sold_price` and **500000
Cost of Vehicle Sales — Retail** debit
for `total_investment`. Trial-balance
gross profit (Revenue - COGS) matches
the sum of `Sale.gross_realized` for
the period, within Recon WIP
reclassification timing (see §5.e
below).

### Q4. Does the sale properly clear the vehicle's Recon WIP balance?

**Before M15:** No. M13.2 detector posts
every VehicleCost row as DR 122000 Recon
WIP / CR 200000 A/P Trade. Nothing ever
clears Recon WIP. The account grows
unboundedly.

**After M15:** Yes. Every sale posts
matching **CR 122000 Recon WIP** for
the vehicle's `total_investment`,
zeroing that vehicle's contribution to
the account. Ongoing balance in Recon
WIP represents only in-flight (unsold)
vehicles per §5.e Option A resolution.

## 2. What existing primitives extend

Sale-booking GL post is the poster
child for "additive extension over
fork" (M11.1 / M12.3 / M13.2 / M14.1
pattern). Zero new entities. Zero
migrations.

- **`services/sale/record_sale`** —
  the write path that gains one
  sibling-service call to
  `services/accounting/post_journal_entry`.
  Already `@transaction.atomic` (line
  128 of `computation.py`); the GL
  post inherits that transaction.
- **`services/accounting/post_journal_entry`**
  — the M13.1 atomic sibling target.
  Consumes `JournalLineInput` tuples
  with `debit` / `credit` /
  `account` / `memo`; enforces
  balanced double-entry + fail-closed
  cross-tenant account references.
  Zero API changes needed.
- **`services/accounting/vehicle_cost.post_vehicle_cost_journal`**
  — invoked per un-posted VehicleCost
  row for this vehicle at sale time
  per §5.e Option A resolution. The
  sibling-service call inside a
  sibling-service call is legal
  (nested `@transaction.atomic` is a
  no-op inside an existing
  transaction).
- **`services/vehicle_ledger.compute_totals`**
  — already invoked by `record_sale`
  to compute `gross_realized`.
  Returns `LedgerTotals` with
  `total_investment` — the same
  value that becomes the COGS-side
  amount.
- **Default COA seeded per Dealership
  by M13.1 migration `0043`.** All
  five accounts M15 uses (100000 /
  120000 / 122000 / 123000 / 400000 /
  500000) exist for every tenant.
  `services/accounting/vehicle_cost._lookup_required_account`
  is the template for M15's account
  resolution (raises
  `MissingDefaultAccountError` if an
  account is inactive or absent).
- **M14.3 journal-entry browser** —
  surfaces the new sale-booking
  entries with `posted_by_username`
  populated from the sale-booking
  operator. Zero UI changes needed.
- **M14.2 trial balance page** —
  renders the new revenue + COGS
  activity in real time. Zero UI
  changes needed.

## 3. What's NOT in this milestone (deferrals)

Every deferral has a clear re-entry
path. **Twelve M15-specific + five
universal = 17 deferrals**, matching
M14's deferral density.

**M15-specific deferrals:**

1. **Sales-tax posting.** Real dealer
   accounting posts sales tax as a
   separate CR 220000 Sales Tax
   Payable line. Sale entity has no
   `sales_tax_amount` field. Re-entry:
   Sale entity extension + follow-on
   M15+ increment. Not blocked by
   M15.
2. **Trade-in accounting.** Trade
   allowance offsets receivable + adds
   inventory (net-of-payoff if
   negative equity). Sale entity has
   no trade FK. Re-entry: Sale entity
   extension + M9 trade increment
   (already deferred at M9).
3. **F&I product revenue.** VSC / GAP
   / T&W etc. produce commission
   revenue at time of sale + reserve-
   receivable posting. M10 F&I entity
   exists but is not GL-wired yet
   (that's the M10-chargeback-reversal
   candidate deferred as separate
   milestone).
4. **Doc fee revenue.** Would be
   another CR 4xxxxx revenue account.
   Sale entity has no `doc_fee` field.
   Re-entry: Sale entity extension.
5. **Reserve receivable at sale.**
   Upfront reserve income is booked at
   sale in real dealer accounting
   (against 130000 A/R Reserve
   Receivable + CR 420000 F&I Reserve
   Income). Blocked on Sale-side F&I
   detail. M10 F&I + reserve module
   milestone.
6. **BHPH interest income accrual.**
   BHPH sale posts DR 123000 BHPH
   Notes Receivable for the full
   note balance; interest accrual is
   a separate elapsed-condition
   detector, matching M12.3 posture.
   Re-entry: separate M15+ BHPH
   interest-accrual detector
   milestone.
7. **Wholesale sale variant.** Sale
   entity's `finance_type` vocab is
   `{cash, retail, bhph}` — no
   wholesale. Wholesale sales would
   post against **410000 Vehicle
   Sales — Wholesale**. Re-entry:
   `SALE_FINANCE_TYPE_WHOLESALE`
   vocab extension per M11 §6 lesson
   18 fixed-vocab posture.
8. **Sale-reversal workflow.** M14.4
   ships reversal for JournalEntry.
   Sale entity has no reversal
   contract yet — deleting a Sale
   would orphan the GL entry. M15
   does NOT wire a sale-side
   reversal. Re-entry: separate
   sale-cancellation milestone that
   defines the operational contract
   first, then wires the GL
   reversal via
   `services/accounting/reverse_journal_entry`.
9. **Deal-jacket linkage.** No FK
   from JournalEntry to Sale. The
   `description` field carries
   "Sale of stock #X" for text-based
   linkage. Operator finds the Sale
   by stock number. FK addition
   defers to a later "GL-to-source-
   entity linkage" milestone when
   operator evidence names the
   drill-down pain.
10. **Contracts-in-Transit funding
    workflow.** M15 posts DR CIT for
    retail sales at booking. The
    matching "DR Cash / CR CIT" entry
    at funding time is a separate
    workflow (funded-check receipt).
    Belongs to a payments-inbound
    milestone.
11. **Cost-of-sale variance
    handling.** Real dealer accounting
    tracks per-deal cost variance
    (recon-cost adjustments after
    the sale posts). M15's COGS line
    uses the ledger snapshot at sale
    time. Post-sale VehicleCost rows
    for that vehicle would still post
    to Recon WIP via M13.2 —
    creating a phantom balance. Per
    §5.e Option A trade-off; operator
    evidence gates the variance-
    handling milestone.
12. **Sale-booking analytics on GL
    entries.** M9.3 aggregates
    `Sale.gross_realized`. M15's
    trial-balance / journal-entry
    surfaces are analytics-adjacent
    but not analytics-native. GL-
    derived reporting (period-over-
    period revenue trends, COGS
    ratios) defers to a later
    reporting milestone.

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

- **M9 `test_m9_sale_computation.py`**
  — `record_sale` tests. Every test
  path must continue to pass. GL
  post is a new side effect; tests
  that assert Sale row shape
  continue to hold; new tests assert
  the co-created JournalEntry
  shape.
- **M13.1 `test_m131_accounting.py`**
  — `post_journal_entry` contract
  tests. M15 exercises the same
  verb; contract tests continue to
  hold.
- **M13.2 `test_m132_cost_reconciliation.py`**
  — `post_vehicle_cost_journal`
  contract tests. M15's per-vehicle
  cost-flush (§5.e Option A) reuses
  this verb; contract tests
  continue to hold.
- **M14.1 `test_m141_accounting_list_endpoint.py`
  + `test_m141_cost_posting_failures*.py`**
  — endpoint tests. M15 posts more
  entries; the list endpoint must
  return them; no contract change.
- **Tenancy carrier count test** —
  M15 adds zero new models. `>=47`
  continues to hold.
- **Permission-class count test** —
  M15 adds zero new endpoints /
  reuses the M9 Sale endpoint
  perm class. `=8` continues to
  hold (zero-drift streak extends
  to seven consecutive milestones).

## 5. Load-bearing decisions

Six decisions. **All six confirmed as-
recommended at SESSION_139 M15.0 open.**
Streak extends to 58 planning-time as-
recommended M5.1 → M15.0 (six
consecutive milestones now).

### 5.a `[RESOLVED at SESSION_139 open]` — Milestone target selection

**Question.** Which candidate from the
M14 retrospective §8 unblocked-work
list defines M15 scope?

**Decision.** **Option A — M9 sale-
booking GL post.** User named at
SESSION_139 open.

**Rationale.** Sale booking is the
highest-frequency operational write
path in the platform. Wiring it to
the GL substrate is the single
change that flips the trial balance
from "reflects only M2 cost accrual"
to "reflects the full retail
operation." The M14 UI surfaces the
resulting entries with zero
additional frontend work — every M15
line of code produces immediate
operator-visible value.

### 5.b `[RESOLVED at SESSION_139 open]` — Finance-type → receivable account mapping

**Question.** How does M15 choose
which receivable-side debit account
to use for the revenue-side line?

- **Option A** — finance-type-aware
  from day 1: three-way branch
  (cash → 100000 Cash on Hand;
  retail → 120000 Contracts in
  Transit; bhph → 123000 BHPH Notes
  Receivable).
- **Option B** — uniform: all sales
  post to 120000 Contracts in
  Transit; a follow-on reclass
  workflow moves entries to Cash /
  BHPH Notes as funding arrives.
  Mirrors the M13.2 uniform-mapping
  posture.
- **Option C** — cash + retail post
  to 120000 CIT; BHPH posts to
  123000 (three-way collapsed to
  two).

**Recommendation drafted.** **Option A.**
Rationale: (1) `SALE_FINANCE_TYPE_CHOICES`
is a fixed vocab (three values); the
three-way branch is 3 lines, not a
combinatorial explosion. (2) The
M13.2 uniform-mapping decision was
driven by open-vocab VehicleCost
categories — that reason doesn't
apply here. (3) A cash sale posting
to CIT would be misleading; cash was
already received, not "in transit."
(4) Deferring to a reclass workflow
adds a whole second write path;
picking the right account at write
time is simpler.

### 5.c `[RESOLVED at SESSION_139 open]` — Cost-side treatment for zero-total-investment sales

**Question.** What happens when a
Vehicle's `total_investment` is `$0.00`
(no VehicleCost rows recorded) at
`record_sale` time?

- **Option A** — skip the COGS +
  Recon-WIP pair entirely; post only
  the revenue-side pair (DR
  receivable / CR revenue). Log
  a warning so the miss is
  observable.
- **Option B** — reject the sale
  with a new `MissingCostBasisError`
  (409). Force operator to fix
  data-quality before booking.
- **Option C** — post a $0.00 COGS
  pair anyway (would fail the M13.1
  `InvalidJournalLineError` — both-
  zero lines are rejected).

**Recommendation drafted.** **Option A.**
Rationale: (1) M13.1 forbids zero-
value lines, so Option C is
architecturally impossible. (2)
Option B blocks the operator on a
data-quality problem that isn't
sale-blocking; the sale is a real
event even if we haven't tracked
acquisition cost yet. (3) A logged
warning is discoverable via
`grep dealer_ai.accounting` — sufficient
signal until a dedicated data-quality
surface emerges. (4) Trial balance
correctness holds — sale revenue
posts, COGS is understated by the
missing cost basis, but that's the
same signal that would exist if the
cost row was recorded later. Operator
can post a manual adjusting entry
via a future correction workflow.

### 5.d `[RESOLVED at SESSION_139 open]` — Un-posted VehicleCost rows at sale time

**Question.** M13.2 posts VehicleCost
rows daily at 10:00. What if a sale
fires when some of the vehicle's
VehicleCost rows are unposted? COGS
would clear amounts from Recon WIP
that haven't been posted there yet
— leaving Recon WIP temporarily
negative for this vehicle.

- **Option A** — flush unposted
  VehicleCost rows for this vehicle
  synchronously inside `record_sale`
  before the sale-booking journal
  posts. Iterate
  `VehicleCost.objects.filter(
  vehicle=vehicle, posted_at__isnull=True,
  is_estimate=False)` and call
  `post_vehicle_cost_journal` on
  each. Same transaction —
  everything commits or nothing does.
- **Option B** — post the sale-
  booking journal regardless. Let
  Recon WIP go transiently negative
  for this vehicle until the M13.2
  10:00 detector catches up.
  Trial balance is briefly
  misleading.
- **Option C** — refuse the sale
  if any unposted VehicleCost rows
  exist for this vehicle. Force the
  operator to wait for M13.2 or to
  trigger a manual detector run.

**Recommendation drafted.** **Option A.**
Rationale: (1) Keeps trial balance
always internally consistent — a
sale never leaves the GL in a state
where Recon WIP is negative because
of timing. (2) The verb already
exists (`post_vehicle_cost_journal`);
this is 3-4 lines of loop code
inside `record_sale`. (3) `record_sale`
is already `@transaction.atomic`;
the nested calls inherit the
transaction — either the sale +
every prerequisite cost post commit,
or nothing does. (4) Option B is
correct-eventually but wrong-now
(operators would see negative Recon
WIP in the M14.2 trial balance
between sale and next detector run).
(5) Option C blocks the operator on
a background job that they can't
easily kick.

### 5.e `[RESOLVED at SESSION_139 open]` — Post-sale VehicleCost rows for sold vehicle

**Question.** After a sale posts,
someone records a new VehicleCost
for that same vehicle (e.g. a
delayed detail-shop invoice). The
M13.2 detector will post it DR
122000 Recon WIP / CR 200000 A/P
Trade. But that vehicle already
cleared its Recon WIP contribution
at sale. New posting creates a
phantom Recon WIP balance for a
sold vehicle.

- **Option A** — accept the phantom
  balance at M15. Note as a §3
  deferral. Cost-of-sale variance
  handling is a future milestone.
  Operator evidence will name the
  pain when it becomes real.
- **Option B** — block VehicleCost
  writes against sold vehicles at
  M15. Force operator to post an
  adjustment somewhere else.
- **Option C** — automatically
  route post-sale VehicleCost rows
  to a different account
  (500000 COGS instead of 122000
  Recon WIP). Would need M13.2
  detector modification.

**Recommendation drafted.** **Option A.**
Rationale: (1) Discipline —
Project Rule 4 (Scope Discipline).
COGS variance handling is a real
accounting workflow but the pain
isn't demonstrated yet. (2) Option
B would break existing operational
flows (detail-shop invoices land
after sale routinely). (3) Option C
modifies M13.2 — that's a scope
expansion into another milestone's
substrate. (4) The phantom balance
is discoverable in trial balance;
operator evidence will surface the
priority when someone asks "why
is Recon WIP off?" (5) Deferred
to §3 item 11 with an explicit
re-entry path.

### 5.f `[RESOLVED at SESSION_139 open]` — Operator UI at M15

**Question.** Does M15 ship any new
frontend surface?

- **Option A** — no UI at M15;
  M14.3 journal-entry browser
  surfaces the new entries
  automatically.
- **Option B** — add a "GL post
  status" column on a hypothetical
  sales-list page.
- **Option C** — extend M14.3 with
  a "Sale of stock #X" filter or
  drill-back link.

**Recommendation drafted.** **Option A.**
Rationale: (1) Matches M13 §5.f
Option C posture (backend-only when
UI substrate already surfaces
result). (2) M14.3 renders the new
entries with `posted_by_username`
populated + descriptive
`description` field — operator can
find sale-booking entries by
scrolling or search-by-description
today. (3) UI polish (filter,
drill-back, sales-list column) is
the shape of the M14 UX polish
candidate (§1 Option F above);
folding it into M15 would violate
Project Rule 4 scope discipline.
(4) M14.3 was designed to be the
audit-trail surface for any
JournalEntry regardless of source.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`
   §6 (ten lessons carry into M15) +
   §8 (M14 unblocked work)
6. `docs/roadmap/MILESTONE_13_PLANNING.md`
   §5.d (Option C hybrid GL-posting
   trigger shape — M15 exercises the
   sync half)
7. `docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`
   §8 (M13 unblocked work)
8. `docs/CAPABILITY_MATRIX.md` §7o
9. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
   §3.5 (Contracts in Transit /
   funding workflow) + §3.13 (sales
   tax accounting deferred at §3
   item 1)
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`
    (M9 write path context)

## 7. Sequencing

**Three code increments + one close-
out + one planning (this one) = five
total.** Complexity-appropriate per
Project Rule 4.

### Increment 0 (M15.0) — Planning refinement + decision review

**Scope.** SESSION_139 (this session).
Target selection (§5.a) confirmed at
open; §5.b–§5.f drafted with
recommendations for user confirmation
before M15.1 code. Full memo
expansion (this document). Handoff
at `docs/handoffs/SESSION_139_m15_inc0_planning.md`.

**Deliverable.**
- This planning memo, expanded from
  the M14.5 skeleton.
- §0.a change log with §5.a
  resolved + §5.b–§5.f pending
  confirmation.
- Session handoff.
- `00-START-NEXT-SESSION.md`
  overwritten with M15.1 priority.

**Backend baseline unchanged:** 4,277
pass, 1 skipped, 0 fail. Frontend
Vitest unchanged: 122 pass.

### Increment 1 (M15.1) — Backend: sale-booking GL post

**Scope.** SESSION_140. Single
backend increment. All M15 write-
path work lands here.

**Deliverable.**
- New `services/accounting/sale_booking.py`
  module with one atomic verb:
  `post_sale_booking_journal(*, dealership,
  sale, posted_by_user=None) -> JournalEntry`.
  Composes the finance-type-aware
  receivable line + revenue line +
  COGS line + Recon-WIP-clear line.
  Sibling-service call to
  `post_journal_entry`.
- Modify `services/sale/computation.record_sale`
  to (a) flush any un-posted
  VehicleCost rows for the vehicle
  via `post_vehicle_cost_journal`
  per §5.d Option A, (b) call
  `post_sale_booking_journal` per
  §5.b Option A finance-type
  mapping, (c) handle §5.c Option A
  zero-cost case (skip COGS pair +
  log warning).
- Modify `views_sale.py` `create`
  endpoint to pass `request.user`
  through to `record_sale` so
  `posted_by_user` propagates to
  the JournalEntry.
- New account-lookup helpers in
  the sale-booking module mirroring
  M13.2's `_lookup_required_account`
  pattern for the receivable /
  revenue / COGS accounts.
- Extended `services/accounting/__init__.py`
  `__all__` for the new verb.
- Focused tests (~25-30 target):
  cash / retail / BHPH finance-type
  branches produce correct
  accounts; balanced double-entry;
  cross-tenant guard; zero-cost
  path (Option A skip); un-posted-
  cost flush (Option A); missing
  account raises
  `MissingDefaultAccountError`;
  `posted_by_user` propagation from
  view; sale + cost + booking all
  commit atomically; sale rollback
  rolls back the GL post; idempotency
  via `SaleAlreadyExistsError`
  short-circuits before GL post.
- No new endpoints.
- No new migrations.
- No new post-LLM scrub stages.
- Tenancy carriers: 47 (unchanged).
- Permission classes: 8 (unchanged).
- DRF admin surface: 104 (unchanged).

**Backend baseline target:** ~4,302-
4,307 pass (+25-30 tests, 0
regressions). Frontend Vitest:
unchanged.

### Increment 2 (M15.2) — Close-out

**Scope.** Docs. Retrospective +
capability matrix §7p + roadmap flip
+ M16 planning skeleton per standing
user directive (M10.8 / M11.7 /
M12.8 / M13.4 / M14.5 precedent).

**Deliverable.**
- `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
  written at M15.2 close.
- `docs/CAPABILITY_MATRIX.md` §7p
  section describing the M15 GL-
  post surface.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 15 SHIPPED entry added.
- Frontmatter flip on this doc:
  `status: active` → `status: shipped`.
- `docs/roadmap/MILESTONE_16_PLANNING.md`
  skeleton for the M15 §8 unblocked-
  work list.
- `00-START-NEXT-SESSION.md`
  overwritten with M16.0 priority.
- Coordinated commit landing all
  M15.2 docs together.

**Backend baseline at M15 close:**
~4,302-4,307 pass (M15.1 delta
sustained; no code changes at
M15.2).

---

*Full memo. All six §5 decisions
confirmed as-recommended at SESSION_139
M15.0 open. M15.1 code shipped at
SESSION_140. M15 SHIPPED at
SESSION_141 M15.2 close.*

## Closing note (M15.2)

Milestone 15 shipped at SESSION_141
per the M10.8 / M11.7 / M12.8 / M13.4
/ M14.5 close-out precedent. Three
increments (M15.0 planning + M15.1
backend + M15.2 close-out) — smaller
surface than M14's six per backend-
only scope, matching M15 §6 lesson 8.

**Backend delta:** 4,277 → **4,296
pass**, 1 skipped, 0 fail (+19 tests,
zero regressions). **Frontend Vitest:
122 pass** (unchanged — no frontend at
M15 per §5.f Option A). **Zero
migrations shipped at any M15
increment.** DRF admin surface 104
(unchanged). Frontend operator routes
20 (unchanged). Tenancy carriers 47
(unchanged). Permission classes 8
(unchanged — zero-drift streak
extends to seven consecutive
milestones: M10 + M11 + M12 + M13 +
M14 + M15). Celery-beat task families
9 (unchanged — sale booking is
operator intent, not detector-
shaped).

**Streak update:** 58 planning-time
as-recommended M5.1 → M15.0. Six
consecutive milestones with every
§5 decision confirmed as-
recommended at planning-time open.
Nine §0.a M15.1 micro-decisions do
not count against the streak per
M10 §9.

Cross-links:

- Delivery record → `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
- Shipped surface → `docs/CAPABILITY_MATRIX.md` §7p
- Roadmap entry → `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 15
- Session handoffs → `docs/handoffs/SESSION_139_m15_inc0_planning.md`
  · `docs/handoffs/SESSION_140_m15_inc1_backend.md`
  · `docs/handoffs/SESSION_141_m15_close.md`
