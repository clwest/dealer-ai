---
title: "Milestone 12 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_121 → SESSION_128
milestone: 12
milestone_name: "BHPH portfolio operations (v1)"
related:
  - docs/roadmap/MILESTONE_12_PLANNING.md
  - docs/roadmap/MILESTONE_11_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 12
---

# Milestone 12 — Retrospective

Written at Milestone 12 close (SESSION_128).
Records what was planned, what shipped, what
deviated and why, and lessons carried forward
for Milestone 13 and beyond. Mirrors the
`MILESTONE_11_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_12_PLANNING.md` at SESSION_120
close defined the milestone as the BHPH
portfolio operations substrate: for dealers
with `bhph_enabled=True`, manage the in-
house lending business after the deal funds
— payment intake, delinquency detection,
collection contact logging, promise-to-pay
tracking, repossession coordination,
portfolio-level owner reporting. §1.0 named
nine operational questions synthesized from
`BHPH_OPERATIONS_MAPPING.md` (§workflow +
§payment cadence + §delinquency + §PTP +
§collections + §repo workflow + §portfolio
activities + pains #1 / #2 / #4 / #7 / #10).

§1.1–§1.9 followed with nine design memos
(BhphNote origination, payment intake +
application, delinquency detection + aging
buckets, PTP tracking, collection contact
log + FDCPA scrub, repossession record +
post-repo handoff, portfolio analytics +
owner reporting, post-repo disposition
handoff, operator UI). §5.a–§5.f drafted
six load-bearing decisions **all flagged
`[NEEDS-DECISION-BEFORE-M12.N]`**. §7
sequenced eight increments (M12.1–M12.8).

**Original §7 sequencing shipped verbatim.**
The six SESSION_121 decisions confirmed as-
recommended at M12.1 open (Options
A / A / A / A / A / C). Additional
implementation-time micro-decisions surfaced
at M12.3 / M12.4 / M12.5 / M12.6 / M12.7
open and were recorded in §0.a amendments
per the M5-M11 precedent — but per M10 §9
those are **implementation-time defaults,
not planning-time decisions**, so they do
not count against the streak. **The streak
is 41 planning-time as-recommended M5.1 →
M12.1 open** — the framework held across
three milestones now.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M12.0 planning | 120 | `MILESTONE_12_PLANNING.md` (draft at M11.7 close) resolving zero load-bearing decisions and leaving six for user review at M12.1 open + additional design questions across §1.1–§1.9 (deferred to per-session opens) | (in M11.7 close commit `b072ced`) |
| M12.1 BhphNote origination + payment schedule | 121 | New `BhphNote` model + migration `0037_m121_bhph_note_entity`. OneToOne FK to `Sale` (CASCADE) where `Sale.finance_type == "bhph"` per §5.a Option A — preserves M10.5 Contract byte-for-byte, no new `contract_type` vocab member. Fields per §1.1: `principal_financed` Decimal(10,2) + `apr` Decimal(5,2) + `term_weeks` PositiveInteger + `payment_frequency` CharField (3-value vocab: `weekly` / `biweekly` / `semi_monthly`) + `payment_amount` Decimal(8,2) denormalized at write + `first_payment_due` Date + `default_grace_days` PositiveInteger default 5. Cross-tenant `clean()` guard on `sale` + non-BHPH sale rejection. **Three new pure verbs added to `services/payment_engine.py`** — `bhph_note_periodic_payment` / `bhph_note_schedule` / `bhph_note_number_of_periods` — adding `semi_monthly` cadence to the M2 cadence set. Customer-shopping `estimate_bhph_payment` untouched. New `services/bhph_notes/` package with three verbs: `record_bhph_note` (computes payment_amount via pure verb) + `get_bhph_note` (tenant-scoped read) + `get_payment_schedule` (pure verb returning list of `(due_date, amount)` tuples). Three domain errors: `CrossTenantBhphNoteError` (404) / `NonBhphSaleError` (400) / `DuplicateBhphNoteError` (409). Two DRF admin endpoints under `admin/bhph-notes/` (POST create + GET retrieve with inline schedule). Tenancy carrier 39 → 40. 49 focused tests. **Six §5 decisions confirmed as-recommended at session open** (§5.a Option A no vocab change; §5.b Option A platform-wide constant application order; §5.c Option A fixed 7-value aging vocab — recorded for M12.3; §5.d Option A operator-triggered PTP reconciliation — recorded for M12.4; §5.e Option A extend existing scrub stack — recorded for M12.5; §5.f Option C MVP UI at M12.7). | `TBD` |
| M12.2 BhphPayment intake + application | 122 | New `BhphPayment` model + migration `0038_m122_bhph_payment_entity`. Mandatory FK to `BhphNote` (CASCADE). Fields per §1.2: `paid_at` DateTime + `amount` Decimal(8,2) + `method` CharField (5-value vocab: `cash` / `check` / `debit` / `ach` / `other`) + `applied_to_fees` / `applied_to_interest` / `applied_to_principal` (all Decimal(8,2) denormalized at write time by the allocation verb). Cross-tenant `clean()` guard on `note`. New `services/bhph_payments/` package split into two files: `apply.py` (pure allocation math — no DB access) + `bhph_payment.py` (DB-facing write + list verbs). Pure verbs: `allocate_payment(amount, outstanding_balance_now, interest_owed, outstanding_fees=Decimal("0"))` → `PaymentAllocation(fees, interest, principal)` NamedTuple; `interest_owed_for_period(balance, apr, freq)`; `outstanding_balance(principal_financed, principal_paid)`. Write verbs: `record_payment(dealership, note, paid_at, amount, method)` `@transaction.atomic` reads prior payments + computes balance + calls allocation verb + persists; `list_payments(dealership, note)` tenant-scoped read. **Application order per §5.b Option A: platform-wide constant fees → interest → principal.** Fees always zero at M12.2 (no fee-charging entity); column preserved for future M12.5+ late-fee entity. Two domain errors: `CrossTenantBhphPaymentError` (404) / `OverpaymentError` (400 — refund/reversal deferred beyond M12). Two DRF endpoints nested under `admin/bhph-notes/<pk>/payments/`. Tenancy carrier 40 → 41. 42 focused tests. **No new §5 decisions** — §5.b Option A locked at M12.1 open. | `TBD` |
| M12.3 Delinquency detection + aging buckets | 123 | **Additive column extension** to `BhphNote` (no new entity) + migration `0039_m123_bhph_note_aging_columns`. Two new columns: `current_bucket` CharField (7-value aging vocab default `current`) + `days_past_due` PositiveInteger default 0. Aging vocab per §5.c Option A: fixed 7-value set with `120`-day charge-off threshold (`current` / `1_15` / `16_30` / `31_60` / `61_90` / `over_90` / `charge_off_candidate`). New `services/bhph_delinquency/` package split into two files: `compute.py` (three pure verbs) + `tasks.py` (Celery detector + orchestrator). Pure verbs: `bucket_for_days(days_past_due)` → aging vocab string; `next_expected_due(first_payment_due, payment_frequency, payments_made)` cadence-aware projection using M12.1's `_BHPH_NOTE_PERIOD_DAYS` mapping (weekly=7 / biweekly=14 / semi_monthly=15); `days_past_due_for(next_expected, grace_days, as_of)` grace-respecting arithmetic (aging measured from scheduled due date after grace expires per §0.a M12.3 decision 1). **State-transitioning Celery detector** at 08:00 project-time daily (next slot after M11.5 07:00). Per-tenant task recomputes `current_bucket` + `days_past_due` on every active BhphNote for one dealership; only writes when derived value differs from stored value (idempotent within run). Fully-paid short-circuit — `outstanding_balance == 0` OR `payments_made >= term_periods` → `current`, 0. 38 focused tests. **Three §0.a M12.3 micro-decisions recorded** (aging measured from scheduled due after grace / new-note column defaults / detector idempotency scope) — all as-recommended per M10 §9 precedent, don't count against streak. | `TBD` |
| M12.4 PTP promise-to-pay tracking | 124 | New `BhphPromiseToPay` model + migration `0040_m124_bhph_promise_to_pay`. Mandatory FK to `BhphNote` (CASCADE). Fields per §1.4: `promised_at` DateTime + `promised_amount` Decimal(8,2) + `promised_reason` CharField (3+1 vocab per §0.a decision 1: `paycheck` / `tax_refund` / `family_help` / `other`) + `actual_payment` FK to `BhphPayment` SET_NULL (populated on reconcile) + `state` CharField (3-value machine: `promised` / `kept` / `broken`) + `notes` TextField. Cross-tenant `clean()` on `note` + `actual_payment`. State machine mirrors M11.5 BeBack shape (promised → kept / broken; terminal states final). New `services/bhph_promises/` package with three verbs mirroring M11.5: `record_promise` / `mark_kept(promise, payment)` (operator-triggered per §5.d Option A — requires BhphPayment reference; verb enforces same-tenant + same-note) / `mark_broken(promise)`. **State-transitioning Celery detector** at 09:00 project-time daily (next slot after M12.3 08:00). Grace period `BHPH_PTP_BROKEN_GRACE_HOURS` env default 24. Four domain errors: `CrossTenantBhphPromiseError` (404) / `UnknownReasonError` (400) / `CrossPromisePaymentError` (400) / `PromiseAlreadyTerminalError` (409). Four DRF endpoints (2 nested + 2 top-level for state transitions). Tenancy carrier 41 → 42. Celery-beat task families 7 → 8. 34 focused tests. **Four §0.a M12.4 micro-decisions recorded** (PTP-specific reason vocab / detector cadence / grace period / operator-triggered reconciliation) — all as-recommended. | `TBD` |
| M12.5 Collection contact log + FDCPA scrub | 125 | New `CollectionContact` model + migration `0041_m125_collection_contact`. Mandatory FK to `BhphNote` (CASCADE). Fields per §1.5: `contacted_at` DateTime + `contacted_by_user` FK to `settings.AUTH_USER_MODEL` (SET_NULL — mirrors PhotoAsset.uploaded_by rationale) + `channel` CharField (5-value vocab: `phone` / `letter` / `sms` / `email` / `in_person`) + `outcome` CharField (4-value vocab: `contact_made` / `left_message` / `no_answer` / `refused_to_speak`) + `notes` TextField. Cross-tenant `clean()` on `note`. New `services/collection_contacts/` package with `record_contact` + `list_contacts` verbs. Three domain errors: `CrossTenantContactError` (404) / `UnknownChannelError` (400) / `UnknownOutcomeError` (400). Endpoint auto-populates `contacted_by_user` with `request.user` — operators don't identify manually. **Extended `services/llm_safety.py`** — new `_scrub_collection_language` stage under `kind="collection_contact"` per §5.e Option A. Three-category pattern list: (1) **deficiency threats** — credit-bureau leverage / lawsuit threats / wage garnishment softened; jail/arrest threats removed; (2) **harassment-adjacent** — employer/workplace/neighbor/family contact threats removed; repeated-contact pressure softened; (3) **false-representation** — attorney/police/court/credit-bureau impersonation removed. Log-and-replace posture matches M2 partial-scrub pattern. No dealer-type gating — FDCPA applies equally at independent and franchise BHPH portfolios. Two DRF endpoints nested under `admin/bhph-notes/<pk>/contacts/`. Tenancy carrier 42 → 43. Post-LLM scrub layers 16 → 17. 38 focused tests. **Five §0.a M12.5 micro-decisions recorded** — all as-recommended. | `TBD` |
| M12.6 Repossession record + post-repo handoff | 126 | New `Repossession` model + migration `0042_m126_repossession`. Mandatory FK to `BhphNote` (CASCADE). Fields per §1.6 + §0.a M12.6 decisions: `ordered_at` DateTime + `ordered_by_user` FK User SET_NULL + `agent_name` CharField (free text at MVP — RepoAgent entity defers to M12+) + `recovered_at` nullable DateTime + `recovery_location` CharField + `intake_condition_report` FK to `ConditionReport` (SET_NULL per §0.a decision 3 — historical evidence survives report deletion) + `state` CharField (3-value linear machine: `ordered` / `recovered` / `re_intaked`). Cross-tenant `clean()` on `note` + `intake_condition_report`. **Three-state linear machine** (not branching) — vehicle must be recovered before it can be re-intaked; skip-transition `ordered → re_intaked` refused. New `services/repossessions/` package with three verbs: `record_repossession` / `mark_recovered(pk, recovered_at, location)` (defaults `recovered_at` to now) / `mark_re_intaked(pk, condition_report)` (requires ConditionReport reference — the vehicle re-entering the M4 recon substrate as a fresh inspection). Four domain errors: `CrossTenantRepossessionError` (404) / `CrossTenantConditionReportError` (400) / `RepossessionAlreadyTerminalError` (409) / `InvalidStateTransitionError` (409). Four DRF endpoints (2 nested + 2 top-level for state transitions). **No M4 recon-lifecycle modifications** — post-repo handoff writes fresh ConditionReport via existing M3/M4/M5 pipeline. Tenancy carrier 43 → 44. 30 focused tests. **Five §0.a M12.6 micro-decisions recorded** — all as-recommended. | `TBD` |
| M12.7 Portfolio analytics + operator UI MVP | 127 | First cross-stack M12 increment. **Five pure aggregate verbs** in new `services/bhph_analytics/` package (`compute.py`): `bucket_histogram(dealership)` → fixed-order 7-row tuple of `BucketHistogramRow(bucket, note_count, principal_total)` (zeros for empty buckets); `cure_rate(dealership)` → snapshot MVP interpretation `current_bucket_count / total_notes` (time-windowed cure rate defers until M12+ time-series storage per §0.a decision 1); `weighted_average_apr(dealership)` → `sum(principal * apr) / sum(principal)`; `weighted_average_days_past_due(dealership)` → `sum(principal * days_past_due) / sum(principal)`; `ptp_kept_ratio(dealership)` → `kept / (kept + broken)` (open promises excluded from denominator). All verbs return `None` for empty portfolios / undefined denominators. Bundled via `portfolio_summary(dealership)` → `BhphAnalyticsSummary` frozen dataclass. **Single summary endpoint** at `GET /admin/bhph/analytics/summary/` per §0.a decision 2 (per-metric endpoints defer). **M12.7 addendum: new `GET /admin/bhph-notes/list/`** — companion list endpoint added so the portfolio dashboard can browse notes; matches M11.6 admin list convention (capped at 100 rows). **New `/dealer-ai-bhph/` frontend route family** with two MVP pages: `DealerAiBhphPortfolio.tsx` (dashboard with four metric cards + aging histogram + notes table) + `DealerAiBhphNoteDetail.tsx` (composes M12.1-M12.6 read endpoints via `Promise.all`; renders loan terms + payments + promises + contacts + repossessions in cards with empty states). New `frontend/src/lib/bhphApi.ts` wrapping every M12.1-M12.7 read verb. **Contact-create + repo-order UI deferred** per §5.f Option C — backend endpoints already ship (M12.5 + M12.6), so the follow-on can add just React code. 24 backend + 11 Vitest tests (target ~25 + ~10). Backend baseline 4,126 → 4,150; frontend baseline 67 → 78. DRF admin surface 96 → 98. Frontend operator routes 15 → 17. Zero migrations. Zero tenancy carrier changes. **Five §0.a M12.7 micro-decisions recorded** — all as-recommended. | `TBD` |
| M12.8 Closeout | 128 | Documentation-only per M10.8 / M11.7 precedent. Six close-out docs (this retrospective + capability matrix §7m + implementation roadmap §Milestone 12 flip + planning doc frontmatter flip + session-start refresh + M13 planning skeleton) + coordinated commit landing all M12.8 docs. **Milestone 12 — BHPH portfolio operations (v1) — SHIPPED.** Batch push of eight local commits (M12.1 through M12.8) queued for user authorization. | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a clear
re-entry path.

**In-milestone deferrals:**

1. **Collection-contact create UI (M12.7
   deferred).** M12.5 shipped the backend
   substrate (record verb + two endpoints
   + collection-language scrub); M12.7 UI
   omitted per §5.f Option C MVP scoping.
   `bhphApi.ts` includes `listCollectionContacts`
   for the detail-page read path;
   create-verb typing lands in the follow-
   on. Sub-milestone candidate.
2. **Repo-order create UI (M12.7
   deferred).** M12.6 shipped the backend
   substrate (three verbs + four
   endpoints); M12.7 UI omitted per §5.f
   Option C. `bhphApi.ts` includes
   `listRepossessions` for the detail read
   path.
3. **DealWriteup UI (M11 deferral
   carried forward).** M11.3 shipped the
   backend substrate; UI still deferred at
   M12 close because the handoff flow
   spans sales-manager + F&I-manager
   personas. Not touched at M12.
4. **Delivery adapters for follow-up /
   be-back / PTP notifications.** M11 +
   M12 detectors + surfacers count / log
   / transition state; none dispatch SMS
   / email / phone. Twilio / SendGrid /
   voice integration is a separate
   substrate.

**Explicit M12 scope-boundary
deferrals** (per
`IMPLEMENTATION_ROADMAP.md`
§Milestone 12 out-of-scope):

5. **GPS / starter-interrupt device
   integration** — deferred to M12+ v2.
   Requires vendor SDK bindings +
   compliance review.
6. **Skip-tracing service integration**
   (TLO / LocatePlus). Deferred to M12+
   v2. Compliance-sensitive.
7. **Credit-bureau reporting (Metro 2
   furnisher)** — deferred. Requires
   Metro 2 XML furnisher + credit-
   bureau enrollment.
8. **Static-pool cohort analysis** —
   deferred. Requires time-series
   snapshot storage (see item 11).
9. **Automated deficiency-judgment
   paperwork** — deferred. Legal
   template drafting + jurisdiction-
   specific compliance.
10. **Repo agent dispatch integration**
    — deferred. M12.6 `agent_name` is
    free text; a first-class
    `RepoAgent` entity + dispatch
    substrate defers until operator
    evidence.

**Milestone-adjacent deferrals** (surfaced
during M12.7 planning):

11. **Time-series snapshot storage for
    portfolio analytics** — every M12.7
    metric is currently a live snapshot.
    True cure-rate (delinquent → current
    transitions across a window), aging-
    trend charts, and static-pool
    analysis all require historical
    bucket state. A `BhphAgingSnapshot`
    entity + M12+ nightly write from
    the M12.3 detector is the natural
    substrate; defers until operator
    evidence names the specific chart /
    metric that needs it.
12. **Full FDCPA classifier** — M12.5
    ships a pattern-based scrub with
    three category-specific fixed
    phrase lists. A full LLM-classifier
    scrub layer defers beyond M12 —
    the pattern-based version catches
    the most common problematic
    phrasings without introducing
    false-positive risk (locked by
    `test_neutral_reminder_passes_through_unchanged`).
13. **`reopen` verb for terminal PTPs
    / repossessions** — terminal
    states are final at M12; un-do
    path defers to operator evidence.
    Matches M11.5 posture.
14. **Per-metric analytics endpoints
    + CSV export** — M12.7 ships a
    single summary endpoint per §0.a
    decision 2. Per-metric endpoints
    (`GET .../cure-rate/`, `GET
    .../weighted-apr/`, etc) defer
    until operator evidence surfaces
    need. JSON payload only at MVP.

## 4. Deviations from plan

**Zero deviations from planned §7
sequencing.** Every M12.N shipped in the
order the planning doc named. Every
`[NEEDS-DECISION-BEFORE-M12.N]` item was
resolved at the correct increment open.

**One in-milestone addendum** — the M12.7
`admin_bhph_note_list` endpoint was added
at implementation time as a companion to
the existing M12.1 retrieve endpoint.
Rationale: the M12.7 portfolio dashboard
needs a browsable list of notes; the
alternative of client-side enumeration
via retrieve calls is worse for both
tenant safety and payload size. Recorded
in §7 M12.7 close as "M12.7 addendum" not
a §5 vote change.

**One in-milestone technical detail** —
the M12.3 `_patch_today` frozen-time test
pattern needed to return a real aware
`datetime` (not a shim object) because
`patch("...timezone.now")` mutates the
shared `django.utils.timezone` module.
The shim approach leaked into `auto_now`
DateTimeField writes and caused test
failures. Locked as the working pattern
for future date-sensitive detector tests.

**Two mid-increment test-count corrections**
recorded in the M12.7 flow — bucket
labels and APR values render in multiple
places (metric card + note rows), so
`getByText(...)` matches were switched
to `getAllByText(...)` with
`.length > 0` checks. Frontend testing
convention going forward: use
`getAllByText` for text that appears in
both aggregate metric displays AND
per-row data displays.

## 5. Compatibility

**Zero regressions across every M12
increment.** Every existing test at M11
close still passes at M12 close. Every
M1-M11 endpoint still returns the same
shape it did at M11 close.

- M1 chat funnel untouched.
- M2 payment engine — customer-shopping
  `estimate_bhph_payment` untouched; M12.1
  added *new* verbs
  (`bhph_note_periodic_payment` /
  `bhph_note_schedule` /
  `bhph_note_number_of_periods`) that
  consume the shared `_BHPH_NOTE_PERIOD_DAYS`
  mapping but don't modify the estimator.
  `daily_floor_plan_interest` untouched.
- M3 ConditionReport — untouched. M12.6
  Repossession attaches via a new SET_NULL
  FK on `intake_condition_report`; no
  ConditionReport model changes.
- M4 recon substrate — untouched. Post-
  repo handoff writes a fresh
  ConditionReport via the existing M3
  endpoints; no lifecycle-state
  modifications.
- M5 lifecycle — untouched.
- M6 listings — untouched.
- M7 async substrate — extended (added two
  new Celery-beat task families: M12.3
  aging detector at 08:00 + M12.4 broken-
  PTP detector at 09:00). Existing M7.2-
  M7.5 tasks untouched.
- M8 analytics — untouched. M12.7 added a
  *sibling* analytics package
  (`services/bhph_analytics/`) matching
  the M8 pure-verb pattern; no M8 code
  paths modified.
- M9 Sale — untouched. M12.1 BhphNote
  attaches via OneToOne FK on `sale`; no
  Sale model changes.
- M10 F&I — untouched. M10.5 Contract
  preserved byte-for-byte per §5.a
  Option A; no `contract_type` vocab
  member added.
- M11 sales-side channels + customer
  journey — untouched. Every M11 endpoint
  still returns the same shape.

**Post-LLM safety stack extended**, not
modified. M12.5 added a new
`_scrub_collection_language` stage under
`kind="collection_contact"`; the 16
existing scrub stages (M1-M6 + M4.5 +
M11) are unchanged.

**Permission classes: 8 (unchanged).**
Every M12 endpoint reuses the M4
`IsSalesManagerOrOwnerAtActiveDealership`
class. Zero permission-class drift
across seven M12 implementation
increments.

## 6. Lessons

Nineteen carry into M13+ planning.

1. **The §5-decisions-locked-at-open
   pattern held for a third milestone.**
   All six §5 decisions at M12.1 open
   confirmed as-recommended, matching M10
   / M11 pattern. 41 planning-time as-
   recommended M5.1 → M12.1 open. The
   framework works for milestones with
   substantial cross-entity dependencies
   (M12 has five new entities, all
   interdependent via BhphNote).
2. **§0.a implementation-time
   micro-decisions are load-bearing.**
   M12.3 / M12.4 / M12.5 / M12.6 / M12.7
   each surfaced 3–5 micro-decisions at
   session open. All recorded as-
   recommended, all locked into the
   planning doc §0.a. Per M10 §9 these
   don't count against the streak, but
   they DO define the shape of the
   implementation — future retrospectives
   should cite §0.a as heavily as §5.
3. **Split pure verbs from write verbs
   scales.** M12.1
   (`bhph_note_periodic_payment` vs
   `record_bhph_note`), M12.2
   (`allocate_payment` vs
   `record_payment`), M12.3
   (`bucket_for_days` /
   `next_expected_due` /
   `days_past_due_for` vs detector task),
   M12.7 (five aggregation verbs vs
   summary endpoint) all use the same
   posture. Pure verbs are
   `SimpleTestCase`-testable; DB-facing
   verbs are `TestCase`-testable; the
   split lets each layer's tests stay
   focused.
4. **Denormalize at write time; recompute
   in the detector.** M12.1
   `payment_amount`, M12.2
   `applied_to_fees` /
   `applied_to_interest` /
   `applied_to_principal`, M12.3
   `current_bucket` / `days_past_due` all
   follow the M9.1 `gross_realized`
   pattern. Downstream reads never
   recompute; the M12.3 detector
   recomputes and denormalizes at a
   scheduled interval. Trade-off: writes
   are more expensive; reads are much
   cheaper.
5. **State machines want linear vs
   branching classification.** M11.5
   BeBack (`promised → returned /
   no_show`) and M12.4 BhphPromiseToPay
   (`promised → kept / broken`) are
   *branching* — the operator picks the
   terminal state based on what
   happened. M12.6 Repossession
   (`ordered → recovered → re_intaked`)
   is *linear* — physical reality
   requires an ordering. The
   `InvalidStateTransitionError` (409)
   was added for the linear case; the
   branching cases only needed
   `AlreadyTerminalError` (409). Future
   state machines should classify at
   planning time.
6. **State-transitioning vs read-only
   Celery task distinction (from M11 §6
   lesson 17) held.** M12.3 aging
   detector is state-transitioning
   (aging is objectively-elapsed
   calendar math); M12.4 broken-PTP
   detector is state-transitioning
   (grace period is objectively
   elapsed). Both auto-write derived
   state without operator intent. No
   M12 task was a surfacer — everything
   M12 tracks has an objective trigger.
7. **08:00 → 09:00 non-overlapping-
   window slot pattern held.** M12.3
   at 08:00 (after M11.5 07:00), M12.4
   at 09:00 (after M12.3 08:00). Eight
   scheduled task families now across
   02:00 → 09:00. The next Celery task
   family lands at 10:00 by
   convention.
8. **Idempotent-within-run detector
   posture works.** Both M12.3 and
   M12.4 detectors use bulk-update
   (`stale_qs.update(...)`) or write-
   if-changed (`if new != stored:
   note.save(...)`). Re-runs on the
   same day produce identical output.
   Locked by `test_detector_is_idempotent_within_run`
   and `test_excludes_already_broken_idempotency`.
9. **Grace period as env var, not
   entity field.** M11.5
   `BE_BACK_NO_SHOW_GRACE_HOURS` and
   M12.4 `BHPH_PTP_BROKEN_GRACE_HOURS`
   both live in
   `dealer_kit/settings.py`. Operator-
   configurable-per-tenant grace
   periods defer until operator
   evidence names the need. `os.getenv`
   default keeps the dev-time flip
   trivial.
10. **`SET_NULL` on historical-evidence
    FKs.** M12.4
    `actual_payment` SET_NULL, M12.5
    `contacted_by_user` SET_NULL, M12.6
    `intake_condition_report` SET_NULL,
    `ordered_by_user` SET_NULL. The
    audit record survives cascading
    deletions. Consistent with the M2
    `VehicleCost.created_by` +
    `PhotoAsset.uploaded_by` posture.
    Distinct from operational-linkage
    FKs which use CASCADE.
11. **Post-LLM scrub extension over new
    package.** §5.e Option A (extend
    `services/llm_safety.py` with a new
    stage) over Option B (new
    `services/bhph_scrub/` package).
    Single-authority posture for post-
    LLM safety — one entry point
    (`apply_post_llm_scrubs`), one kind
    dispatch. Nine `kind` values now.
12. **Log-and-replace scrub posture
    (from M2 `default_assumption` +
    `internal_directive`) held for
    M12.5.** The operator sees
    neutralized copy + a
    `scrubs_fired` log entry.
    Blocking-the-whole-draft was
    rejected (§0.a M12.5 decision 5)
    because it hides the near-miss
    from operator awareness.
13. **Fixed-list pattern scrubs beat
    LLM classifiers at MVP.** M12.5's
    three-category fixed-phrase list
    is deliberately narrow. Full
    FDCPA classifier defers beyond
    M12 — false positives on neutral
    collection copy would be worse
    than uncaught edge cases. Test
    coverage: 12 category tests + 1
    neutral-passthrough test + 3
    kind-gating tests.
14. **Text-only kind gating.** M12.5's
    `_scrub_collection_language` fires
    only when `kind="collection_contact"`.
    Other kinds (`chat`, `vehicle_ask`,
    `ad`, `follow_up`, `vendor_comm`,
    `parts_order`, `vehicle_listing`)
    are unaffected. Test:
    `test_non_collection_kind_leaves_language_untouched`.
15. **Frozen dataclass for aggregation
    output.** M12.7's
    `BhphAnalyticsSummary` +
    `BucketHistogramRow` follow the M8
    `GrossProfitPoint` +
    `SourcePerformanceRow` pattern.
    Immutable output; callers project
    into serialized shape.
16. **Zero-portfolio semantics matter.**
    Every M12.7 weighted-average verb
    returns `None` (not zero) when the
    portfolio has zero notes. The
    endpoint ships `None` verbatim;
    the frontend renders em-dash. "0%
    APR" and "no notes to compute an
    APR for" are distinct.
17. **Compose, don't bundle** (from
    §0.a M12.7 decision 4). Detail
    page fetches five separate
    endpoints via `Promise.all`
    rather than adding a bundle
    endpoint. Each backend endpoint
    stays focused; frontend
    composition costs a single
    render-blocking round trip.
18. **`getAllByText` for text that
    appears in metric + row displays.**
    Portfolio bucket labels and APR
    values render in both places.
    `getByText` fails when the same
    text appears multiple times;
    `getAllByText` with
    `.length > 0` is the working
    pattern. Recorded for future
    dashboard-page tests.
19. **In-milestone addendum endpoints
    are OK when scoped tight.** M12.7
    `admin_bhph_note_list` was added
    at implementation time; documented
    at §7 M12.7 close as an addendum
    with the same permission class,
    same tenant-scoping, same list-cap
    convention as M11.6 addenda. Not
    a §5 vote change. Future
    milestones can use the same
    posture for browsability
    addendums.

## 7. Streak update

**41 planning-time as-recommended M5.1 →
M12.1.** Three consecutive milestones now
(M10 + M11 + M12) with every §5 decision
confirmed as-recommended at planning-time
open. §0.a implementation-time micro-
decisions across M12.3–M12.7 do not
count against the streak per M10 §9.

The pattern that held:

1. Draft the §5 recommendations at
   planning close of the *previous*
   milestone.
2. Confirm at the next milestone's
   opening session.
3. Amend §0.a as micro-decisions
   surface per implementation session.
4. Never re-vote a §5 decision mid-
   milestone — file the amendment as
   §0.a instead.

Next planning cycle at M13 open will
test whether the pattern holds against
an accounting-reconciliation substrate
(which has different ownership +
integration constraints than the sales
+ portfolio milestones).
