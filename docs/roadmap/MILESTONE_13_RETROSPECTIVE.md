---
title: "Milestone 13 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_129 → SESSION_132
milestone: 13
milestone_name: "Accounting reconciliation core (v1)"
related:
  - docs/roadmap/MILESTONE_13_PLANNING.md
  - docs/roadmap/MILESTONE_12_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 13
---

# Milestone 13 — Retrospective

Written at Milestone 13 close (SESSION_132).
Records what was planned, what shipped, what
deviated and why, and lessons carried forward
for Milestone 14 and beyond. Mirrors the
`MILESTONE_12_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_13_PLANNING.md` at SESSION_128
close (drafted at M12.8 per standing user
directive) defined the milestone as the
accounting reconciliation core: establish the
ledger truth layer so every operational event
on the platform produces a matching
accounting entry. §1 named **nine
operational business questions** synthesized
from `ACCOUNTING_DEPARTMENT_MAPPING.md`
(three-way reconciliation without POs,
chasing funding, chasing titles, reconciling
vendor payments, duplicate data entry across
≥7 systems, unapplied cash, schedule to
control-account reconciliation, floor plan
schedule reconciliation, monthly close +
trial balance).

**This milestone was deliberately structured
to be incremental.** Per
`IMPLEMENTATION_ROADMAP.md` §Milestone 13, a
single monolithic accounting milestone would
violate Scope Discipline (Project Rule 4).
The remaining eight questions layer onto
M14+ or into ongoing operational milestones
as those surfaces ship.

§5.a–§5.f drafted **six load-bearing
planning-time decisions** all flagged
`[NEEDS-DECISION-BEFORE-M13.0]`. §7
sequenced four increments (M13.1–M13.4).

**Original §7 sequencing shipped verbatim.**
The six SESSION_129 decisions confirmed as-
recommended at M13.0 open (Options
A / B / A / C / A / C). Additional
implementation-time micro-decisions surfaced
at M13.2 (six) and M13.3 (five) opens and
were recorded in §0.a amendments per the
M5-M12 precedent — but per M10 §9 those are
**implementation-time defaults, not
planning-time decisions**, so they do not
count against the streak. **The streak is 47
planning-time as-recommended M5.1 → M13.0
open** — the framework held across four
milestones now (M10 + M11 + M12 + M13).

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M13.0 planning | 128–129 | `MILESTONE_13_PLANNING.md` (draft at M12.8 close) resolving zero load-bearing decisions and leaving six for user review at M13.0 open. Six confirmed as-recommended at SESSION_129 open. | (in M12.8 close commit `fb3e718` + SESSION_129 header) |
| M13.1 GL substrate: chart of accounts + immutable journal entries | 129 | Three new entities (`GLAccount` + `JournalEntry` + `JournalEntryLine`) + migration `0043_m131_accounting_substrate` (schema + RunPython seed step, self-contained via `apps.get_model`). Immutable journal entries per §5.c Option A — corrections happen via reversing entries, not edits. Absence of an `update_journal_entry` verb is the enforcement mechanism. Self-FK for reversal chain with PROTECT to preserve audit trail. Line-level cross-tenant guard on both `entry` and `account`. New `services/accounting/` package (three files: `__init__.py` + `default_coa.py` + `journal.py`). Three verbs: `post_journal_entry` (atomic write refusing empty / malformed / unbalanced / cross-tenant lines) + `reverse_journal_entry` (atomic write of reversal; empty-reason rejection) + `get_journal_entry` (tenant-scoped read). Six domain errors: `EmptyJournalEntryError` / `InvalidJournalLineError` / `UnbalancedJournalEntryError` (400) / `CrossTenantGLAccountError` / `CrossTenantJournalEntryError` (404) / `ImmutableJournalEntryError` (409). `JournalLineInput` frozen dataclass for line-input shape. **Platform-shipped default COA** per §5.b Option A: 24 accounts organized per ACCOUNTING §1.1 NADA-style chart (1-series assets 8, 2-series liabilities 4, 3-series equity 2, 4-series revenue 4, 5-series cost of sales 2, 6/7/8/9-series expense 4). Migration RunPython seeds every existing Dealership at apply time. `seed_default_coa(dealership)` verb is idempotent via `get_or_create` for future dealership creation (no `pre_save` signal wiring per §0.a — explicit call defers to M14+). Three DRF admin endpoints under `admin/accounting/journal-entries/` (POST create + POST `<pk>/reverse` + GET `<pk>`). Gated on `IsSalesManagerOrOwnerAtActiveDealership` per M12 continuity. Tenancy carrier 44 → 47 (+3). DRF admin surface 98 → 101 (+3). **~40 focused tests target hit at +44** (5 GLAccount model + 8 JournalEntry model + 19 accounting service + 12 endpoint). Backend 4,150 → 4,194. **Six §5 decisions confirmed as-recommended at session open** (§5.a Option A substrate + Q1 slice; §5.b Option B platform-shipped default COA; §5.c Option A immutable + reversing; §5.d Option C hybrid trigger; §5.e Option A `services/accounting/` package; §5.f Option C no UI at M13). | `5b9c0ef` |
| M13.2 M2 cost reconciliation detector | 130 | Ninth Celery-beat task family at 10:00 project-time daily. Additive `VehicleCost.posted_at` DateTimeField (nullable) + migration `0044_m132_vehicle_cost_posted_at`. New `services/accounting/vehicle_cost.py` module with three verbs: `detect_unposted_costs(dealership)` pure query (filter `posted_at__isnull=True AND is_estimate=False`) + `post_vehicle_cost_journal(dealership, vehicle_cost, posted_at=None)` `@transaction.atomic` sibling-service verb (per M12 §6 lesson 11 pattern) + `post_all_unposted_costs_for_dealership(dealership, now=None)` orchestrator. **Uniform GL mapping per §0.a M13.2 decision 2**: every eligible VehicleCost → DR `122000` Recon WIP + CR `200000` A/P Trade (positive amount); DR A/P + CR Recon WIP (negative amount — correction row with sides swapped per §0.a M13.2 decision 5). Category-group-aware mapping (flooring → floor-plan accounts, admin → rent/ad, etc.) defers to a later increment per fixed-vocab posture. New `services/accounting/tasks.py` with `post_vehicle_cost_journals_for_dealership` per-tenant task + `post_vehicle_cost_journals_for_all_tenants` orchestrator matching M11.5 / M12.3 / M12.4 detector shape. Beat schedule entry `accounting-vehicle-cost-post-daily-10-00` in `dealer_kit/settings.py` (next slot after M12.4 09:00). New `MissingDefaultAccountError` (broken-invariant signal — fires only when a required default COA account is missing/inactive for a tenant; orchestrator catches + logs + counts as `failed_count` without halting). Estimates skipped per §0.a M13.2 decision 4 — flip to committed triggers next-run posting via still-NULL `posted_at`. Zero-amount rows rejected inside atomic block by M13.1 `InvalidJournalLineError` guard (no partial state). Tenancy carrier 47 (unchanged — additive M2 extension only). Celery-beat task families 8 → 9. **~25 focused tests target hit at +26** (19 service + 7 tasks). Backend 4,194 → 4,220. **Six §0.a M13.2 micro-decisions recorded** (denormalize-at-write posted_at / uniform mapping / 10:00 slot / skip estimates / swap-sides for negatives / isnull+non-estimate filter idempotency) — all as-recommended per M10 §9 precedent, don't count against streak. | `1f7c260` |
| M13.3 Trial-balance snapshot | 131 | New `services/accounting/snapshot.py` module. Two frozen dataclasses per M12 §6 lesson 15 pattern: `TrialBalanceRow` (per-account: `account_code` + `account_name` + `account_type` + `debit_total` + `credit_total` + `natural_balance`) + `TrialBalanceSnapshot` (`dealership_id` + `dealership_slug` + `as_of` + tuple of rows + grand totals + `is_balanced` flag). **Pure recompute per §0.a M13.3 decision 2** — no `TrialBalanceSnapshot` entity at M13.3; materialization defers until M14+ close-workflow evidence names the need. `compute_trial_balance(dealership, as_of=None)` verb aggregates `JournalEntryLine` rows for the tenant where parent `JournalEntry.posted_at <= as_of` (default `timezone.now()`), groups by account via single SELECT with GROUP BY (no N+1), computes per-account totals + grand totals + `is_balanced` = `total_debits == total_credits`. Natural-balance signs use fixed-set membership: `GL_NORMAL_BALANCE_DEBIT_TYPES = frozenset({asset, expense})` returns `debit - credit`; credit-normal types return `credit - debit`. **Zero-portfolio semantics per §0.a M13.3 decision 5**: fresh dealership post-M13.1 seed returns empty balanced snapshot (`rows=()`, totals `0.00`, `is_balanced=True`) — not 404. New GET endpoint `admin-trial-balance` under `admin/accounting/trial-balance/` with optional `?as_of=<ISO8601>` query parameter. Reuses `IsSalesManagerOrOwnerAtActiveDealership` per §0.a M13.3 decision 3 (zero-drift permission-class posture holds for a fifth consecutive milestone). No migration. Tenancy carrier 47 (unchanged — aggregate-only). DRF admin surface 101 → 102. **~20 focused tests target hit exactly at +20** (12 service + 8 endpoint). Backend 4,220 → 4,240. **Five §0.a M13.3 micro-decisions recorded** (frozen dataclass output / pure recompute no snapshot entity / reuse permission class / optional as_of / empty balanced zero-portfolio semantics) — all as-recommended. | `e655512` |
| M13.4 Closeout | 132 | Documentation-only per M10.8 / M11.7 / M12.8 precedent. Six close-out docs (this retrospective + capability matrix §7n + implementation roadmap §Milestone 13 flip + planning doc frontmatter flip + session-start refresh + M14 planning skeleton) + coordinated commit landing all M13.4 docs. **Milestone 13 — Accounting reconciliation core (v1) — SHIPPED.** Batch push of four local commits (M13.1 through M13.4) queued for user authorization. | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a clear
re-entry path.

**In-milestone deferrals:**

1. **Category-group-aware GL mapping**
   (deferred). M13.2 ships uniform DR
   Recon WIP / CR A/P Trade for every
   VehicleCost regardless of category.
   Flooring categories should ideally
   post to `210000` Floor Plan Payable
   and `900000` Interest Expense — Floor
   Plan; admin categories should post
   to `600000` Advertising / `800000`
   Rent / etc. Defers per §0.a M13.2
   decision 2 fixed-vocab posture —
   layers in as a future increment when
   the reporting need names the
   specific miscoding pain.
2. **Trial-balance snapshot
   materialization** (deferred). M13.3
   ships pure recompute (`compute_trial_balance`
   re-aggregates every call). A
   `TrialBalanceSnapshot` entity + M14+
   monthly-close verb that materializes
   a frozen period-end view is the
   natural substrate for period-over-
   period comparisons. Defers per §0.a
   M13.3 decision 2 until close-
   workflow evidence surfaces need.
3. **Per-dealer COA overrides**
   (deferred). M13.1 ships platform-
   default COA loaded via migration
   RunPython. Per-dealer overrides
   (add / rename / hide accounts via
   operator UI) defer to M14+ per §5.b
   Option A. The `is_active` field on
   `GLAccount` supports soft-hiding
   accounts as a partial workaround
   until the full override surface
   lands.
4. **Operator UI for M13 substrate**
   (deferred). Per §5.f Option C the
   entire M13 milestone ships backend-
   only. Trial-balance render, journal-
   entry browser, reversal-with-reason
   dialog, and cost-posting failure
   surfacing all defer to M14. Admin
   endpoints already ship (M13.1 +
   M13.3), so the follow-on can add
   just React code.
5. **`post_save` signal auto-seeding
   new dealerships** (deferred).
   `seed_default_coa(dealership)` is
   idempotent and callable but not
   wired into any signal. New
   dealerships created via admin form
   or management command require an
   explicit seeder call. Defers per
   §0.a until M14+ operator UI /
   dealer-onboarding surface names
   the auto-seeding trigger point.

**Explicit M13 scope-boundary
deferrals** (per
`IMPLEMENTATION_ROADMAP.md`
§Milestone 13 out-of-scope + §5.a
Option A slice boundary):

6. **M9 sale-booking GL post** —
   deferred per §5.a Option A (Q1
   was the M13 slice; Q2 M9 sale-
   booking layers on later). §5.d
   Option C hybrid trigger locks in
   sync GL post inside `record_sale`
   as the target shape when this
   ships.
7. **M10 F&I chargeback GL reversal**
   — deferred (Q4 in the §1 nine-
   question list). Chargeback rows
   already carry the info needed for
   the reversal entry; the substrate
   is ready.
8. **M12 BHPH payment GL post** —
   deferred (Q7). Per §5.d Option C
   the trigger shape when this ships
   is a detector (elapsed condition,
   not operator intent).
9. **M4 vendor invoice → A/P
   reconciliation** — deferred (Q4
   in the nine-question list).
10. **Title-arrival tracking** —
    deferred (Q5).
11. **Floor-plan reconciliation vs
    lender statements** — deferred
    (Q6). Requires vendor / lender
    statement ingestion.
12. **Bank reconciliation surface**
    — deferred.
13. **Contracts-in-transit schedule**
    — deferred (Q3).
14. **Monthly close workflow +
    adjusting entries + P&L / balance
    sheet derivatives** — deferred
    (Q9). Trial balance is the raw
    substrate M13.3 ships; higher-
    level reports layer at M14+.
15. **Payroll / W-2 / 1099** —
    external-service scope
    boundary per
    `IMPLEMENTATION_ROADMAP.md`
    §Milestone 13.
16. **GAAP-compliant audited
    financial reporting** — out of
    scope for platform v1.
17. **Direct DMS integration** —
    belongs to a future vendor-
    integration milestone.

**Milestone-adjacent deferrals**:

18. **CSV / spreadsheet export for
    trial-balance snapshots** —
    JSON payload only at MVP.
    Defers per M12.7 per-metric-
    endpoint precedent.
19. **Period-comparison verbs**
    (delta between two `as_of`
    snapshots) — defers alongside
    the M14+ close-workflow slice.
20. **Balance-sheet / P&L
    derivatives** — trial balance
    is the raw substrate. Higher-
    level reports layer at M14+.

## 4. Deviations from plan

**Zero deviations from planned §7
sequencing.** Every M13.N shipped in
the order the planning doc named.
Every `[NEEDS-DECISION-BEFORE-M13.N]`
item was resolved at the correct
increment open.

**Zero in-milestone addenda.** M12
had one addendum (M12.7
`admin_bhph_note_list`). M13 shipped
the endpoints named in the planning
doc — three at M13.1, one at M13.3,
nothing else.

**One in-milestone contract
correction** — the `ImmutableJournalEntryError`
409 path exercised via the endpoint
turned out to be unreachable through
DRF (blank-reason input triggers
serializer 400 first). Documented the
layered behavior in the endpoint
test comments and kept the service-
level test covering the 409 path
directly. Belt (DRF) + suspenders
(service verb) posture preserved.

## 5. Compatibility

**Zero regressions across every M13
increment.** Every existing test at
M12 close still passes at M13 close.
Every M1-M12 endpoint still returns
the same shape it did at M12 close.

- M1 chat funnel untouched.
- M2 payment engine untouched.
  M13.2 added `VehicleCost.posted_at`
  as an additive nullable column;
  the existing `VehicleCost`
  ordering / str / clean behavior
  is unchanged.
- M3 ConditionReport untouched.
- M4 recon substrate untouched.
- M5 lifecycle untouched.
- M6 listings untouched.
- M7 async substrate — extended
  (M13.2 added one Celery-beat task
  family at 10:00 project-time
  daily). Existing M7.2-M12.4 tasks
  untouched.
- M8 analytics — untouched. M13
  added a *sibling* accounting
  package (`services/accounting/`)
  independent from the M8 analytics
  package.
- M9 Sale — untouched. M13.2
  detector reads `Vehicle` via
  `VehicleCost.vehicle`; no Sale
  model changes.
- M10 F&I — untouched.
- M11 sales-side channels +
  customer journey — untouched.
- M12 BHPH portfolio — untouched.
  M13.1 GL substrate is a sibling
  to M12; no M12 code paths
  modified.

**Post-LLM safety stack: 17 scrub
stages (unchanged).** M13 has no
LLM path; the substrate is entirely
deterministic double-entry math.

**Permission classes: 8 (unchanged).**
Every M13 endpoint reuses the M4
`IsSalesManagerOrOwnerAtActiveDealership`
class. Zero permission-class drift
across four M13 implementation
increments — extends the streak to
five consecutive milestones (M10 +
M11 + M12 + M13.1 + M13.2 + M13.3).

## 6. Lessons

Twelve carry into M14+ planning.

1. **The §5-decisions-locked-at-open
   pattern held for a fourth
   milestone.** All six §5 decisions
   at M13.0 open confirmed as-
   recommended, matching M10 / M11 /
   M12 pattern. 47 planning-time as-
   recommended M5.1 → M13.0 open. The
   framework works for milestones with
   substantially different ownership
   surfaces than the operational
   milestones that preceded it —
   accounting is the *reconciliation
   layer* for M2 / M4 / M9 / M10 /
   M12, not a new operational domain
   of its own, and the planning-time
   discipline held.
2. **§0.a implementation-time
   micro-decisions continue to be
   load-bearing.** M13.2 surfaced 6,
   M13.3 surfaced 5. All recorded as-
   recommended, all locked into the
   planning doc §0.a. Per M10 §9
   these don't count against the
   streak, but they DO define the
   shape of the implementation.
3. **The incremental-slice structure
   (§Milestone 13) is the right
   pattern for reconciliation
   milestones.** A monolithic
   "accounting" milestone would have
   violated Scope Discipline. M13
   shipped substrate + one slice
   (M2 cost reconciliation) + one
   substrate-consuming aggregate
   (trial balance) in three code
   increments totaling ~90 tests.
   Remaining eight slices layer onto
   M14+ or into ongoing operational
   milestones as those surfaces
   ship. Future reconciliation-
   layer milestones (audit trail,
   compliance reporting, tax
   filing) should follow the same
   pattern.
4. **Immutability enforced by
   absence-of-verb is stronger than
   assertion.** `services.accounting`
   has no `update_journal_entry`
   verb, and this is the enforcement
   mechanism for §5.c Option A. A
   future maintainer adding one
   would need to justify why the
   absence was wrong (not merely
   why the addition is convenient).
   Same posture as M9's absence of
   `unsell_vehicle`.
5. **Uniform GL mapping is the right
   MVP posture for detector-driven
   posts.** M13.2 posts every
   VehicleCost against the same two
   accounts. Category-aware mapping
   (flooring → floor-plan accounts,
   etc.) is easy to add later once
   operator evidence names the
   reporting need. Adding it
   prematurely burns modeling
   capacity against uncertain
   requirements. The service verb
   signature stays stable; only the
   internal debit/credit selection
   changes.
6. **Migration RunPython that reads
   from a service module is
   self-contained via
   `apps.get_model`.** M13.1
   `_seed_default_coa` imports
   `DEFAULT_COA` from
   `services.accounting.default_coa`
   for the source-of-truth tuple,
   but writes rows via the
   historical model. This lets the
   migration stay valid across
   future model changes (renames,
   column additions) without an
   amendment. Preferable to
   inlining the fixture in the
   migration (would drift out of
   sync with the service module).
7. **Frozen dataclass output scales
   from M8 analytics to M13.3
   trial balance.** Same pattern:
   immutable output, callers
   project into serialized shape,
   `tuple` on collection fields
   reinforces immutability. New
   aggregate verbs at M14+ should
   default to this shape.
8. **Zero-portfolio semantics matter
   in read-side surfaces too.**
   M13.3's empty balanced snapshot
   for a fresh dealership mirrors
   M12.7's `None` for zero-note
   portfolios. A 404 would surprise
   operators; an empty valid
   response is honest.
9. **Belt (DRF serializer) +
   suspenders (service verb)
   sometimes creates unreachable
   endpoint paths.** M13.1's
   `ImmutableJournalEntryError`
   409 for empty-reason reversal
   is caught by DRF serializer
   400 first. The service test
   exercises the 409 path
   directly; the endpoint test
   documents the layered
   behavior. Don't remove the
   suspender just because the
   belt is doing its job — the
   service verb might be called
   from a non-endpoint context
   (management command, future
   endpoint that skips DRF, etc.).
10. **Sibling-service atomic
    crossings work exactly as M12
    §6 lesson 11 promised.** M13.2's
    `post_vehicle_cost_journal`
    wraps a call into M13.1's
    `post_journal_entry` in
    `@transaction.atomic` and
    denormalizes `posted_at` on
    the source row inside the same
    block. Either both sides
    commit or neither does. No
    partial state. First cross-
    milestone service-package
    invocation and the pattern
    held.
11. **Additive nullable column
    extensions are the safe
    default for detector-driven
    denormalization.** M13.2's
    `VehicleCost.posted_at` is
    nullable — every existing row
    starts at NULL and gets
    processed by the first
    detector run. No data
    migration needed. Same
    posture as M12.3's aging
    columns (though those were
    typed as PositiveInteger
    default 0 rather than
    nullable).
12. **Zero-drift permission-class
    posture extends to five
    consecutive milestones.**
    Every M10 + M11 + M12 + M13
    endpoint reused M4's
    `IsSalesManagerOrOwnerAtActiveDealership`.
    Permission-class count stays
    at 8. This is a milestone-
    level lesson — future
    reconciliation / reporting /
    admin milestones should
    default to reusing the
    existing permission class
    unless the endpoint surface
    genuinely requires a distinct
    authorization model.

## 7. Streak update

**47 planning-time as-recommended
M5.1 → M13.0.** Four consecutive
milestones now (M10 + M11 + M12 +
M13) with every §5 decision
confirmed as-recommended at
planning-time open. §0.a
implementation-time micro-decisions
across M13.2 + M13.3 (11 in total)
do not count against the streak
per M10 §9.

The pattern that held:

1. Draft the §5 recommendations at
   planning close of the *previous*
   milestone.
2. Confirm at the next milestone's
   opening session.
3. Amend §0.a as micro-decisions
   surface per implementation session.
4. Never re-vote a §5 decision mid-
   milestone — file the amendment
   as §0.a instead.

Next planning cycle at M14 open
will test whether the pattern
holds against whatever surface
comes next.

## 8. What M13 unblocks for M14+

- **M9 sale-booking GL post** —
  substrate ready. `services/
  accounting/post_journal_entry`
  is the atomic sibling-service
  target per §5.d Option C hybrid
  posture (sync inside
  `record_sale`).
- **M10 F&I chargeback GL
  reversal** — substrate ready.
  Existing chargeback rows
  already carry the info needed
  for the reversal entry.
- **M12 BHPH payment GL post** —
  substrate ready. Per §5.d
  Option C the trigger shape is
  a detector (elapsed
  condition, not operator
  intent) matching M12.3 /
  M12.4 / M13.2 pattern.
- **Trial-balance materialization
  + monthly close workflow** —
  M13.3 pure-recompute verb is
  the source-of-truth aggregator;
  a `TrialBalanceSnapshot` entity
  at M14+ can freeze period-end
  views over the same aggregator.
- **Operator UI** — M13.1 and
  M13.3 admin endpoints are the
  data source. React work
  begins from a fully-tested
  backend contract.
