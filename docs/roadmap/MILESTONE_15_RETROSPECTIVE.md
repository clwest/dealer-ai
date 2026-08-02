---
title: "Milestone 15 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_139 → SESSION_141
milestone: 15
milestone_name: "M9 sale-booking GL post"
related:
  - docs/roadmap/MILESTONE_15_PLANNING.md
  - docs/roadmap/MILESTONE_14_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 15
---

# Milestone 15 — Retrospective

Written at Milestone 15 close (SESSION_141).
Records what was planned, what shipped,
what deviated and why, and lessons carried
forward for Milestone 16 and beyond. Mirrors
the `MILESTONE_14_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_15_PLANNING.md` at SESSION_138
close (drafted at M14.5 per standing user
directive) defined the milestone as the M9
sale-booking GL post. §5.a Option A locked
the sync `@transaction.atomic` sibling-
service call inside `services/sale/record_sale`
per M13 §5.d Option C hybrid posture. Every
sold vehicle produces a matching balanced
JournalEntry via `services/accounting/post_journal_entry`.

**This milestone was deliberately backend-
only**, not a UI expansion. The M14 UI
surface (M14.3 journal-entry browser + M14.2
trial-balance page) surfaces the resulting
entries automatically without additional
frontend work. Zero frontend increment shipped
at M15.

§5.a–§5.f drafted **six load-bearing
planning-time decisions** all flagged
`[NEEDS-DECISION-BEFORE-M15.1]`. §7 sequenced
three increments (M15.0 planning + M15.1
backend + M15.2 close-out) — smaller surface
than M14's five per backend-only scope.

**Original §7 sequencing shipped verbatim.**
The six SESSION_139 decisions confirmed as-
recommended at M15.0 open (all Options A).
Additional implementation-time micro-decisions
surfaced at M15.1 (nine) — recorded in §0.a
amendments per M5-M14 precedent. Per M10 §9
those are **implementation-time defaults, not
planning-time decisions**, so they do not
count against the streak. **The streak stands
at 58 planning-time as-recommended M5.1 →
M15.0** — six consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15) with
every §5 decision confirmed as-recommended at
planning-time open.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M15.0 planning | 139 | `MILESTONE_15_PLANNING.md` expanded from skeleton (~305 lines) to active memo (~635 lines). Frontmatter `status: draft` → `status: active`; `milestone_name` set to "M9 sale-booking GL post". Six §5 load-bearing decisions resolved with recommendations + rationale. §1 business questions expanded to four operator-workflow questions (Q1 does the GL reflect the sale / Q2 which receivable / Q3 gross-profit at the GL / Q4 Recon WIP clear). §3 deferrals locked at 17 (12 M15-specific + 5 universal). §7 sequenced two code increments + one close-out. **Six §5 decisions confirmed as-recommended** — streak 58 M5.1→M15.0. | `ce511a2` |
| M15.1 Backend: sale-booking GL post | 140 | New module `services/accounting/sale_booking.py` with `post_sale_booking_journal(*, dealership, sale, posted_by_user=None) -> JournalEntry` atomic sibling-service verb. Composes finance-type-aware receivable line (§5.b Option A: cash → 100000 Cash on Hand; retail → 120000 Contracts in Transit; bhph → 123000 BHPH Notes Receivable) + revenue line (400000 Vehicle Sales — Retail) + COGS line (500000 Cost of Vehicle Sales — Retail) + Recon-WIP-clear line (122000 Recon Work in Process for `total_investment`). Delegates to `post_journal_entry` for balanced double-entry write. Six new account-code constants exported. New `UnmappedFinanceTypeError(RuntimeError)` for broken-invariant signal on unmapped finance-types. `_lookup_required_account` helper mirroring M13.2 verbatim. `_resolve_receivable_account` helper picking the account by finance-type. Extended `services/sale/computation.record_sale` with (a) `posted_by_user=None` kwarg (default preserves existing call sites), (b) per-vehicle un-posted VehicleCost flush per §5.d Option A (iterates `detect_unposted_costs(dealership=...).filter(vehicle=vehicle)` and calls `post_vehicle_cost_journal` on each — same atomic transaction), (c) refreshes `gross_realized` AFTER the flush so denormalized value matches COGS-line snapshot, (d) sibling call to `post_sale_booking_journal`. Zero-total-investment path per §5.c Option A: revenue-pair posts only + warning logged via `logging.getLogger("dealer_ai.accounting.sale_booking")`. Extended `views_sale.admin_sale_create` to pass `request.user` through as `posted_by_user=request.user`. Extended `services/accounting/__init__.py` `__all__` for the new verb + constants + error class. Extended `tests/_auth_helpers.make_dealership` to seed default COA (brings test dealerships in line with M13.1 migration invariant). Patched `tests/test_m9_sale_computation.py` inline with `seed_default_coa` for four in-file `Dealership.objects.create` call sites. **19 focused tests** across 9 TestCase classes in new `tests/test_m151_sale_booking.py` (target ~25-30; shipped 19 with comparable coverage — each finance-type branch is one test rather than three parameterized variants). Tenancy carrier 47 (unchanged — no new models). Permission classes 8 (unchanged — zero-drift streak extends to seven consecutive milestones). DRF admin surface 104 (unchanged — no new endpoints; sale-booking is a side effect of M9's existing create endpoint). Frontend Vitest 122 (unchanged — no frontend at M15 per §5.f Option A). No new post-LLM scrub stages. **Nine §0.a M15.1 micro-decisions recorded** — all as-recommended per M10 §9 (do not count against streak). | `2a50354` |
| M15.2 Closeout | 141 | Documentation-only per M10.8 / M11.7 / M12.8 / M13.4 / M14.5 precedent. Six close-out docs (this retrospective + capability matrix §7p + implementation roadmap §Milestone 15 SHIPPED entry added + planning doc frontmatter flip `active` → `shipped` + session-start refresh + M16 planning skeleton) + coordinated commit landing all M15.2 docs. **Milestone 15 — M9 sale-booking GL post — SHIPPED.** | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a
clear re-entry path.

**M15-specific deferrals** (all
from `MILESTONE_15_PLANNING.md`
§3):

1. **Sales-tax posting.** Real
   dealer accounting posts sales
   tax as a separate CR 220000
   Sales Tax Payable line. Sale
   entity has no `sales_tax_amount`
   field. Re-entry: Sale entity
   extension + follow-on M15+
   increment.
2. **Trade-in accounting.** Trade
   allowance offsets receivable +
   adds inventory (net-of-payoff
   if negative equity). Sale
   entity has no trade FK. Re-
   entry: Sale entity extension +
   M9 trade increment.
3. **F&I product revenue.**
   VSC / GAP / T&W etc. produce
   commission revenue at time of
   sale + reserve-receivable
   posting. M10 F&I entity exists
   but is not GL-wired yet (that's
   the M10-chargeback-reversal
   candidate).
4. **Doc fee revenue.** Would be
   another CR 4xxxxx revenue
   account. Sale entity has no
   `doc_fee` field. Re-entry: Sale
   entity extension.
5. **Reserve receivable at sale.**
   Upfront reserve income is
   booked at sale in real dealer
   accounting. Blocked on Sale-
   side F&I detail.
6. **BHPH interest income
   accrual.** BHPH sale posts DR
   123000 BHPH Notes Receivable
   for the full note balance;
   interest accrual is a separate
   elapsed-condition detector,
   matching M12.3 posture.
7. **Wholesale sale variant.**
   Sale entity's `finance_type`
   vocab is `{cash, retail,
   bhph}` — no wholesale.
   Wholesale sales would post
   against **410000 Vehicle Sales
   — Wholesale**. Re-entry:
   `SALE_FINANCE_TYPE_WHOLESALE`
   vocab extension per M11 §6
   lesson 18 fixed-vocab posture.
8. **Sale-reversal workflow.**
   M14.4 ships reversal for
   JournalEntry. Sale entity has
   no reversal contract yet —
   deleting a Sale would orphan
   the GL entry. M15 does NOT
   wire a sale-side reversal.
9. **Deal-jacket linkage.** No FK
   from JournalEntry to Sale. The
   `description` field carries
   "Sale of stock #X" for text-
   based linkage. Operator finds
   the Sale by stock number. FK
   addition defers to a later "GL-
   to-source-entity linkage"
   milestone.
10. **Contracts-in-Transit funding
    workflow.** M15 posts DR CIT
    for retail sales at booking.
    The matching "DR Cash / CR
    CIT" entry at funding time is
    a separate workflow (funded-
    check receipt). Belongs to a
    payments-inbound milestone.
11. **Cost-of-sale variance
    handling.** Post-sale
    VehicleCost rows for that
    vehicle would still post to
    Recon WIP via M13.2 — creating
    a phantom balance. Per §5.e
    Option A trade-off; operator
    evidence gates the variance-
    handling milestone.
12. **Sale-booking analytics on
    GL entries.** M9.3 aggregates
    `Sale.gross_realized`. M15's
    trial-balance / journal-entry
    surfaces are analytics-
    adjacent but not analytics-
    native. GL-derived reporting
    (period-over-period revenue
    trends, COGS ratios) defers
    to a later reporting
    milestone.

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

**Total deferrals at M15 close:
17** (12 M15-specific + 5
universal). Matches M14's 17.

## 4. Deviations from planned scope

Three deviations. All net-additive.
Zero regressions.

1. **Test count came in 19, not
   target 25-30.** Coverage
   equivalent per structural
   choice: each finance-type
   branch is one test rather
   than three parameterized
   variants; balanced-double-
   entry, cross-tenant, missing-
   account, unmapped-finance,
   posted-by, atomic rollback,
   and idempotency each covered
   with a single assertion per
   concern. Zero-cost path
   covered by two tests
   (skip-COGS + revenue-only-
   balances) instead of a
   parameter matrix. Net effect
   is a smaller, faster test
   file with the same behavior
   coverage.
2. **`make_dealership` helper
   extension** — un-planned at
   §7 M15.1 scope but surfaced
   immediately when M9 sale-
   computation tests started
   failing on `MissingDefaultAccountError`.
   Extending the shared fixture
   helper was the surgical fix
   — one line change vs. per-
   test setUp edits across the
   endpoint test suite. §0.a
   M15.1 decision 8.
3. **`test_m9_sale_computation.py`
   inline patches** — patched
   four in-file
   `Dealership.objects.create`
   call sites (two setUps + two
   in-test) rather than
   migrating the file to
   `make_dealership`. Preserves
   slug conventions + per-test
   isolation the file was
   originally written around.
   §0.a M15.1 decision 9.

## 5. Compatibility with existing surface

Every M1-M14 endpoint returns the
same shape it did at M14 close.
Every M1-M14 service verb
signature is unchanged (only
additive: `record_sale` gained
one optional kwarg with a
backward-compatible default).

Enumerated:

- **M1-M8 endpoints:** unchanged.
- **M9 sale endpoint** — accepts
  the same request body shape;
  returns the same response body
  shape; POST now has a side
  effect (GL post + optional
  cost-flush) that fails-atomic
  if the GL post fails. Existing
  callers see the same success
  response.
- **M9 `record_sale` service
  verb** — new optional
  `posted_by_user` kwarg; default
  `None` preserves every
  existing call site. No return-
  shape change.
- **M10-M12 endpoints:** unchanged.
- **M13 accounting endpoints:**
  unchanged. `admin/accounting/
  trial-balance/` now returns
  more revenue + COGS activity;
  `admin/accounting/journal-
  entries/list/` returns more
  entries.
- **M14 UI surfaces:** unchanged.
  The M14.3 browser now shows
  sale-booking entries alongside
  M13.2 cost-accrual entries;
  the M14.2 trial balance shows
  the running gross-profit
  picture at the GL level.
- **Tenancy carriers:** 47
  (unchanged — no new models).
- **Permission classes:** 8
  (unchanged — reused
  `IsSalesManagerOrOwnerAt
  ActiveDealership` via
  `IsReconManagerSalesManagerOr
  OwnerAtActiveDealership`
  composition at the M9
  endpoint).
- **Migrations:** `0043`–`0044`
  (unchanged — zero schema
  changes at M15).
- **Celery-beat task families:**
  9 (unchanged — sale booking
  is operator intent, not
  detector-shaped).
- **AI safety stack:** 17 scrub
  stages (unchanged — M15 has
  no LLM path).

## 6. Lessons

Eight carry into M16+ planning.

1. **The §5-decisions-locked-at-
   open pattern held for a sixth
   milestone.** All six §5
   decisions at M15.0 open
   confirmed as-recommended,
   matching M10/M11/M12/M13/M14
   pattern. **58 planning-time
   as-recommended M5.1 → M15.0**
   across six consecutive
   milestones now. The framework
   works for milestones with
   substantially different
   ownership surfaces — a
   backend-only integration
   milestone (M15) is as amenable
   to the pattern as UI-only
   (M14), mixed (M13), and
   substrate-focused (M12).
2. **The sync sibling-service
   posture per M13 §5.d Option
   C hybrid works as designed.**
   `record_sale`'s existing
   `@transaction.atomic` block
   absorbs the cost-flush loop
   + sale-booking journal call
   as nested sibling-service
   calls with zero extra
   ceremony. Nested
   `@transaction.atomic` is a
   no-op inside an existing
   transaction; either every
   prerequisite cost + the
   sale-booking entry commit,
   or nothing does. The atomic-
   sibling-boundary pattern
   from M12 §6 lesson 11
   generalizes to nested-atomic
   calls trivially.
3. **Test-fixture invariant
   drift is a real cost.** M15.1
   surfaced that the M13.1
   migration seeded COA for
   every dealership at apply
   time, but test dealerships
   created via `Dealership.objects.create`
   in-test bypass migrations.
   The invariant "every
   Dealership has full default
   COA" held in production but
   not in tests. Extending
   `make_dealership` to seed
   COA on creation brings tests
   in line with production —
   the shared fixture helper is
   the right place to encode
   invariants that migrations
   enforce at deploy time. Any
   future migration that seeds
   per-tenant data should
   consider whether the shared
   test-fixture helper needs a
   matching update.
4. **Additive extension over
   fork worked cleanly.** The
   sale-booking module reuses
   `_lookup_required_account`
   verbatim from M13.2 (not
   promoted to a shared helper
   — evidence gate for a
   refactor not tripped per
   §0.a M15.1 decision 3).
   `record_sale`'s existing
   contract (four kwargs +
   Vehicle first-positional)
   extended by one optional
   kwarg. Zero call sites
   needed updates. The M11.1 /
   M12.3 / M13.2 / M14.1
   pattern generalizes to
   cross-package sibling
   integration.
5. **The zero-cost path is a
   real operational case.** §5.c
   Option A (skip COGS pair,
   post revenue-only + warning
   log) covers vehicles with
   incomplete cost tracking —
   which is a data-quality
   problem, not a sale-blocking
   problem. Refusing the sale
   (§5.c Option B) would block
   operators on tracking gaps
   that pre-date the sale event.
   Trial balance is correct-
   for-what-we-know; a future
   data-quality surface can
   surface the missing basis.
6. **`gross_realized` refresh
   after the cost flush was
   necessary.** §0.a M15.1
   decision 6. Before-flush read
   would leak stale
   `total_investment` for sales
   where §5.d Option A posted
   new costs during the write.
   Denormalized values must
   read from the same snapshot
   the co-posted GL entry uses.
   Future denormalized fields
   in mixed-write paths should
   place their read AFTER any
   sibling-service writes that
   affect them.
7. **Zero-drift permission-class
   posture extends to seven
   consecutive milestones.**
   Every M10 + M11 + M12 + M13 +
   M14 + M15 endpoint reused
   M4's `IsSalesManagerOrOwnerAt
   ActiveDealership` (M15 via
   the composed
   `IsReconManagerSalesManagerOr
   OwnerAtActiveDealership` on
   the pre-existing M9 endpoint
   — no new endpoint added).
   Permission-class count stays
   at 8. Same lesson from M14
   §6 lesson 10; the streak
   extends by one milestone.
   Future write-path GL wiring
   (M10 chargeback, M12 BHPH
   payment) should default to
   reusing the existing endpoint's
   permission class.
8. **UI-preserving backend
   milestones can be surprisingly
   compact.** M15 shipped in 3
   increments (planning +
   backend + close) versus M14's
   6 (planning + 4 code + close).
   The M14 UI was designed as
   the audit-trail surface for
   any JournalEntry regardless
   of source, and M15
   demonstrated that assumption
   held. Backend-only milestones
   that leverage prior UI
   surfaces should plan for 2-3
   increments rather than 5-6.

## 7. Streak update

**58 planning-time as-recommended
M5.1 → M15.0.** Six consecutive
milestones now (M10 + M11 + M12 +
M13 + M14 + M15) with every §5
decision confirmed as-recommended
at planning-time open. §0.a
implementation-time micro-
decisions across M15.1 (9 in
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

## 8. What M15 unblocks for M16+

- **The M14 UI surfaces are now
  seeing real sale data.** Before
  M15, M14.2 trial balance showed
  only M13.2 cost-accrual activity
  in Recon WIP + A/P Trade; M14.3
  journal-entry browser showed
  only cost-accrual entries. After
  M15 every sold vehicle produces
  a matching entry visible in the
  browser + trial balance
  reflecting the full retail
  operation. Operator evidence
  on M15-shipped surfaces will
  drive the M14 UX polish
  candidate (filter surface, `as_of`
  picker, sidebar nav) whenever
  it's picked up.
- **M10 F&I chargeback GL
  reversal — substrate ready +
  proven pattern.** M15
  demonstrated the sync sibling-
  service posture for M9;
  chargebacks are already
  reversal-shaped in the
  operational surface + can reuse
  `reverse_journal_entry`
  directly. Blocks less because
  M15 proved out the pattern.
- **M12 BHPH payment GL post —
  detector-shape ready.** M13
  §5.d Option C hybrid puts BHPH
  payment posting in the detector
  half. Same posture as M13.2
  cost detector (11:00 project-
  time daily is the next open
  slot after M13.2's 10:00). M15
  did not touch this — it
  remains open work.
- **Category-group-aware GL
  mapping** for the M13.2
  detector — remains unblocked
  from M14 §8. M15 didn't
  change this equation.
- **Trial-balance materialization
  + monthly close workflow** —
  remains unblocked from M13 §8.
  M14.2 could grow an `as_of`
  picker as part of this.
- **M14 UX polish** (journal-
  entry list filters, `as_of`
  picker, sidebar nav) — remains
  unblocked; operator evidence
  on M15-shipped surfaces now
  starts to accumulate.
- **Sale-side reversal workflow.**
  M15 §3 item 8 deferred this
  pending an operational contract
  definition. The GL side
  (`reverse_journal_entry`) is
  ready; the operational side
  (what happens to the Sale row,
  the Vehicle status, downstream
  M9.3 analytics) still needs a
  spec.
- **Post-sale VehicleCost
  variance handling.** §3 item
  11 deferred pending operator
  evidence. M15's phantom-
  balance choice will surface
  operator questions when a
  sold-vehicle Recon WIP
  balance shows up in the M14.2
  trial balance; that operator
  evidence is the trigger for
  the variance-handling
  milestone.
