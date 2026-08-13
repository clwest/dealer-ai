---
title: "Milestone 18 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_146 → SESSION_152
milestone: 18
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
related:
  - docs/roadmap/MILESTONE_18_PLANNING.md
  - docs/roadmap/MILESTONE_17_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 18
---

# Milestone 18 — Retrospective

Written at Milestone 18 close (SESSION_152).
Records what was planned, what shipped, what
deviated and why, and lessons carried forward
for Milestone 19 and beyond. Mirrors the
`MILESTONE_17_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_18_PLANNING.md` at SESSION_145 close
(drafted at M17.3 per standing user directive)
defined the milestone as **the first non-
accounting target since M12**: validation
infrastructure enabling founder-led pilot
testing with experienced independent-dealer
operators.

**§5.a Option O locked at SESSION_146 M18.0
open** with the milestone name **"Demo Store
Simulation + Pilot Validation Readiness."**
Rationale: the platform now has a broad
verified capability surface through M17;
another isolated accounting extension has
diminishing marginal value without validation
that the existing surface actually resonates
with real independent-dealer operators.

§5.b-§5.g drafted **seven load-bearing
planning-time decisions** — one more than the
historical six per milestone, reflecting the
mixed architecture / ownership / representation
/ safety scope. §7 sequenced seven increments
(M18.0 planning + M18.1 substrate + M18.2
retail_subprime + M18.3 floor_planned + M18.4
bhph + M18.5 briefs/feedback + M18.6 close-
out).

**Original §7 sequencing shipped verbatim.**
All seven SESSION_146 planning-time decisions
confirmed as-recommended at M18.0 open. §0.a
implementation-time micro-decisions surfaced
at M18.1 + M18.2 (five total) — recorded in
§0.a amendments per M5-M17 precedent. Per M10
§9 those are **implementation-time defaults,
not planning-time decisions**, so they do not
count against the streak. **The streak stands
at 77 planning-time as-recommended M5.1 →
M18.0** — nine consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 + M16 +
M17 + M18) with every §5 decision confirmed
as-recommended at planning-time open.

## 2. What actually shipped

Every §3 compatibility item verified true;
enumeration below.

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M18.0 planning | 146 | `MILESTONE_18_PLANNING.md` expanded from ~450-line skeleton to ~2,050-line active memo. Frontmatter `status: draft` → `status: active`; `milestone_name` set. All seven §5 decisions resolved (Option O + Option A × 6): §5.a target selection, §5.b `Dealership.is_demo` + `demo_archetype` in normal tenancy model, §5.c `services/demo_store/` package + management command + belt-and-suspenders `NonDemoResetError`, §5.d Python builder classes per archetype, §5.e `TesterFeedback` model + endpoint + CSV exporter, §5.f UI-correction boundary (only workflow-blocking or materially misleading), §5.g synthetic-only data safety with outbound-send-boundary guard toolkit. §1 seven business questions; §2 primitives to extend; §3 12 M18-specific + 11 universal = 23 deferrals; §7 seven-increment sequencing. **Seven §5 decisions confirmed as-recommended** — streak 77 M5.1 → M18.0. | `469bc9e` |
| M18.1 Substrate | 147 | Migration `0047_m181_demo_store_substrate.py` — `Dealership.is_demo` BooleanField + `demo_archetype` CharField(choices) + `TesterFeedback` CreateModel. Bundled per M13.1 `accounting_substrate` precedent. **Vocab constants** for archetype + feedback categories. **New `services/demo_store/` package** (nine modules): `errors.py` (`NonDemoResetError`), `outbound_guard.py` (`SuppressedOutbound` + `is_demo_dealership` + `suppress_if_demo` toolkit), `scenario_summary.py`, `synthetic_names.py` (40-name roster), `synthetic_data.py` (`DEMO`-prefixed VINs + `555-01xx` NANP phones + `.example` TLD emails), `registry.py` (`create_demo_store` / `reset_demo_store` / `list_demo_stores` with belt-and-suspenders guard), `archetypes/base.py` ABC + three stub builders. **Register `TesterFeedback` in `_TENANT_CARRIER_MODEL_NAMES`** (49 → 50). **New `demo_store` management command** with `create` / `reset` / `list` / `export_feedback` subcommands. **Test helper `make_demo_dealership`.** 53 focused tests including outbound-egress scanner. **One §0.a M18.1 implementation-time decision recorded** — outbound-send-boundary enumeration finding (preliminary M18.0 list was aspirational; only the two LLM providers currently egress; scanner test enforces guard-by-construction contract for future adapters; LLM providers allowlisted with documented rationale). | `fe9a19a` |
| M18.1 docs | 147 | `SESSION_146_m18_inc0_planning.md` + `SESSION_147_m18_inc1_backend_substrate.md` handoffs; session-start refresh. | `4c82f71` |
| M18.2 Retail/subprime archetype | 148 | `services/demo_store/archetypes/retail_subprime.py` (~750 lines). 20 vehicles ($8k-$18k, `DEMORS`-VINs) + 4 salespeople + 15 leads + 5 sales (1 BHPH firing M15 sync-sibling) + 3 in-recon vehicles with full ConditionReport + ReconDecision + WorkOrder + parts + VehicleCost + stage progression + 1 shared demo Vendor + 2 sub-prime CreditApplications + 1 follow-up cadence (3 tasks). ScenarioSummary populated. 33 focused tests. **Three §0.a M18.2 decisions recorded**: (1) Chargeback deferred to M18.5 (substrate chain too heavy for scope); (2) registry seeds M13.1 default COA on both create + reset (corrects M18.1 omission; M15 sale-booking needs it); (3) `_delete_demo_store_children` iterates carriers in **reverse** order for PROTECT FKs + deletes demo-owned Users so rebuild doesn't collide on `username` unique constraint. Two M18.1 stub-guard tests updated to reference `floor_planned` (still stub at this point). | `a7eb65e` |
| M18.2 docs | 148 | `SESSION_148_m18_inc2_retail_subprime_archetype.md` handoff; session-start refresh. | `ee64e25` |
| M18.3 Floor-planned archetype | 149 | `services/demo_store/archetypes/floor_planned.py` (~750 lines). 40 vehicles ($12k-$35k, Ford/Chevy/RAM/Toyota, `DEMOFP`-VINs) + 6 salespeople (owner + sales manager + 4 advisors) + 25 leads + 4 shared Vendors (mechanical/body/glass/detail) + 10 sales (8 retail-finance + 2 cash) + **5 in-recon vehicles including the $825 F-150 XLT SuperCrew overrun anchor** (`WorkOrder.authorized_cost=$600` vs `actual_cost=$1,425`; VehicleCost sum reconciles to $1,425; 2 VendorCommunication rows walking outbound approval + inbound narrative log documenting the escalation) + 3 CreditApplications + 3 follow-up cadences (7+ tasks) + 3 BeBacks (promised/returned/promised). 34 focused tests including 4 dedicated to overrun scenario visibility. M18.1 stub-guard tests updated to reference `bhph` (last remaining stub). | `aa6343f` |
| M18.3 docs | 149 | `SESSION_149_m18_inc3_floor_planned_archetype.md` handoff; session-start refresh. | `2dec5d6` |
| M18.4 BHPH archetype | 150 | `services/demo_store/archetypes/bhph.py` (~810 lines). 25 primary vehicles ($4k-$12k, `DEMOBH`-VINs) + 5 additional historical vehicles + 4 salespeople (owner + sales manager + 2 collectors) + 10 pipeline leads + 5 recent BHPH Sales via `record_sale` + `record_bhph_note` (M15 sync-sibling GL fires) + 25 historical BhphNotes (direct-create per scenario-authored posture) + **~135-150 BhphPayment rows across the portfolio, with ~5 unposted (`posted_at=NULL`) within the last 24 hours as M16.1 detector-eligibility anchor** + 3 BhphPromiseToPay covering all three states (promised + kept-with-linked-BhphPayment + broken) + 5 CollectionContact rows across channels + 1 recovered Repossession + 2 follow-up cadences. 31 focused tests including 3 dedicated to M16 detector eligibility + 5 to cross-domain integrity. **All three archetypes now shipped.** Three M18.1 stub-guard tests re-purposed to exercise all-archetypes-shipped happy paths. | `42c604d` |
| M18.4 docs | 150 | `SESSION_150_m18_inc4_bhph_archetype.md` handoff; session-start refresh. | `e18e84a` |
| M18.5 Briefs + feedback endpoint | 151 | **13 hand-written daily briefs** in `services/demo_store/briefs/` following the standard six-marker structure: `retail_subprime/` (owner/sales_manager/recon/accounting), `floor_planned/` (owner/sales_manager/**recon [$1,425 overrun intervention]**/accounting), `bhph/` (owner/sales_manager/recon/**accounting [M16 detector timing story]**/**collector [promise-to-pay + CollectionContact + repossession chain]**). Brief loader (`list_briefs` + `get_brief` + `Brief` frozen dataclass + `BriefNotFoundError`). New `views_demo_store.py` with **POST `/admin/demo-store/feedback/`** endpoint reusing `IsSalesManagerOrOwnerAtActiveDealership` (zero-drift streak extends to fourteen consecutive milestones); non-demo dealership rejected 403; body validated by DRF serializer + category vocab check. URL registered — **DRF admin surface 107 → 108**. CSV export end-to-end verified via management command. 24 focused tests including brief-content-shape matrix + endpoint guards + tenant scoping + CSV E2E. **No frontend at M18.5** — feedback capture UI deferred per §5.f evidence-driven boundary. | `957a7ba` |
| M18.5 docs | 151 | `SESSION_151_m18_inc5_briefs_and_feedback.md` handoff; session-start refresh. | `6b6c3a5` |
| M18.6 Close-out | 152 | Documentation-only per M10.8 / M11.7 / M12.8 / M13.4 / M14.5 / M15.2 / M16.2 / M17.3 precedent. Six close-out docs (this retrospective + capability matrix §7s + implementation roadmap §Milestone 18 SHIPPED entry + planning doc frontmatter flip + M19 planning skeleton + session-start refresh) + coordinated commit landing all M18.6 docs. **Milestone 18 — Demo Store Simulation + Pilot Validation Readiness — SHIPPED.** | (this commit) |

## 3. What was NOT shipped (deferred, not dropped)

Every deferral recorded with a clear re-entry
path.

**M18-specific deferrals** (all from
`MILESTONE_18_PLANNING.md` §3):

1. **Public self-serve demo signup.** Testers
   are hand-provisioned by Chris (or a
   delegated tester wrangler) via the
   `demo_store` CLI. A public signup path
   defers to a hosted-demo milestone.
2. **Production deployment solely for this
   milestone.** Local + staging (if
   available) is sufficient for founder-led
   validation.
3. **Full customer onboarding automation.**
   Real pilot customer onboarding is a
   separate initiative that follows M18
   validation.
4. **Product tours and walkthrough overlays.**
   Scenarios are text briefs, not in-product
   tours.
5. **Broad clickstream analytics.**
   `TesterFeedback` captures structured
   observations; general behavioral
   analytics defers.
6. **Session recording.** No video / DOM
   replay.
7. **Generic whole-platform UI polish.** §5.f
   Option A locked; only workflow-blocking
   or materially misleading defects belong
   in M18. Broader polish records via
   `TesterFeedback` for a later dedicated
   milestone.
8. **Fake stubs for unfinished capabilities.**
   Scenarios use only shipped behavior.
9. **Outbound email / SMS to real
   destinations.** §5.g Option A scanner
   test enforces the guard-by-construction
   contract; the two LLM providers are on
   a documented allowlist (see §4 deviation
   1 below).
10. **DMS / lender / bank / auction / bureau /
    payment / accounting-provider
    integrations.** Explicit non-goal.
11. **Pricing logic, billing, subscriptions,
    contracts.** Not part of the platform
    at v1.
12. **Conversion of testers into real-data
    pilot stores.** Follows validation and
    receives its own onboarding scope.

**Implementation-time additions to the
deferral list**:

13. **Chargeback substrate** per §0.a M18.2
    decision 1. The substrate chain
    (DealStructure → Contract → Funding →
    BackEndProductAgreement → Chargeback) is
    4-5 additional entities with distinct
    service verbs. Deferred throughout M18.2
    through M18.5. The accounting daily
    briefs in retail_subprime + floor_planned
    mention the deferral explicitly.
    **Re-entry**: a dedicated F&I chargeback
    scenario milestone if operator evidence
    surfaces the demand — or a permanent
    non-goal if tester feedback names it a
    low priority.
14. **Demo-store-aware LLM cost caps** per
    §0.a M18.1 decision 1. The M18.1
    outbound-scanner allowlists
    `openai_provider.py` + `ollama.py` on the
    grounds that rerouting to `MockLLMProvider`
    is a behavior change with UX implications
    (scenarios exercising the vehicle
    assistant against demo inventory would
    lose real LLM output). A future decision
    to cap tokens / route to a smaller
    model for demo dealerships remains
    unblocked.
15. **Feedback capture UI form.** §5.f
    Option A locked "workflow-blocking or
    materially misleading" as the only
    threshold for UI corrections at M18. No
    scenario brief was blocked by the
    absence of an in-product feedback form
    — testers use the CLI + endpoint via
    curl / Postman / a small script.
    Re-entry: layer on an existing admin
    page in a future UX-polish milestone if
    operator evidence surfaces the need.

**Universal deferrals (any platform
milestone):**

- Payroll (external service).
- W-2 / 1099 generation (external service).
- Year-end tax return preparation (external
  CPA).
- GAAP-compliant audited financial reporting
  (out of scope for platform v1).
- Direct DMS integration (belongs to a
  future vendor-integration milestone).
- Real inventory-feed integrations
  (Manheim / ADESA / ACV).
- Bilingual UI.
- Payment processing / e-sign / DMS write-
  back.
- Multi-tenant SaaS shell (billing / org).
- Predictive ML on operational data.
- SSO / MFA on top of M1 auth.

**Total deferrals at M18 close: 26** (15
M18-specific + 11 universal). Higher than
M17's 17 because M18's scope is deliberately
narrow (validation substrate, not generic-
purpose demo infrastructure).

## 4. Deviations from planned scope

Six deviations. All net-additive. Zero
regressions.

1. **Outbound-send-boundary enumeration
   finding** (§0.a M18.1 decision 1). The
   preliminary M18.0 planning list named
   six candidate egress verbs (M11.4 follow-
   up delivery, M12.5 collection dispatch,
   M10 F&I lender-portal adapters, M10
   compliance / bureau pulls, chat outbound
   routing, M9 test-drive delivery
   reminders). Verified at M18.1 open by
   grepping for `requests.`, `httpx.`,
   `smtplib.`, `django.core.mail`, and
   vendor SDK imports — **only the two LLM
   providers currently egress**. The
   preliminary list was aspirational (verbs
   that would need guards *if/when* they
   ship). M18.1 shipped a **scanner test
   that fails loud** if any future
   `services/` verb egresses without the
   guard, plus a documented allowlist for
   the two LLM providers with rationale.
   Net-additive: the guard-by-construction
   contract is stronger with the scanner
   than it would have been with the
   preliminary hand-list.
2. **Registry COA seeding correction** (§0.a
   M18.2 decision 2). The M18.1 substrate
   shipped `create_demo_store` +
   `reset_demo_store` without calling
   `seed_default_coa`. The retail_subprime
   archetype's first sale attempt at M18.2
   surfaced the omission
   (`MissingDefaultAccountError`). Corrected
   at M18.2 by calling
   `seed_default_coa(dealership)` inside
   both create and reset. Belt-and-
   suspenders precedent — mirrors the
   `_auth_helpers.make_dealership` posture.
3. **Reset ordering + demo-owned-User
   cleanup** (§0.a M18.2 decision 3). The
   M18.1
   `_delete_demo_store_children` iterated
   `_TENANT_CARRIER_MODEL_NAMES` in insertion
   order and left seeded Users behind. First
   reset attempt at M18.2 hit
   `ProtectedError` on `JournalEntryLine ↔
   GLAccount` PROTECT FKs. Corrected by
   iterating in **reverse** order (child-
   before-parent) + explicitly deleting
   Users whose only memberships are at this
   dealership so the next build doesn't
   collide on `username` unique constraint.
4. **Chargeback deferral** (§0.a M18.2
   decision 1). Recorded above as a
   deferral not a deviation.
5. **Recon-overrun scenario shipped richer
   than planned.** M18 planning §7 M18.3
   named "1 with a documented $600+
   overrun" as the recon-lead centerpiece.
   Actual delivery shipped **two
   VendorCommunication rows walking through
   the escalation** (outbound approval-sent
   + inbound narrative-log) — the M4.5
   substrate wasn't in the preliminary
   list, but its inclusion made the scenario
   materially better (the M18.5 recon brief
   references the vendor comms history
   directly).
6. **Endpoint count grew — first time at
   M18.** M18.5 added one endpoint (POST
   `/admin/demo-store/feedback/`),
   growing the DRF admin surface **107 →
   108**. This is the first M18 endpoint
   addition. Every prior M18 increment kept
   the endpoint count static. The
   permission-class posture stayed zero-
   drift (reuses
   `IsSalesManagerOrOwnerAtActiveDealership`
   per the streak).

## 5. Compatibility with existing surface

Every M1-M17 endpoint returns the same
shape it did at M17 close. Every M1-M17
service verb signature is unchanged. M18
is purely additive:

- **M1-M17 endpoints:** unchanged.
- **M18.5 POST
  `/admin/demo-store/feedback/`:** new; no
  interference with existing surface.
- **M13.1 accounting endpoints:** unchanged.
  The `create_demo_store` verb calls
  `seed_default_coa` internally which uses
  the same M13.1 seeder every test helper
  uses.
- **M14 UI surfaces:** unchanged. Testers
  use the same M14.2 / M14.3 / etc.
  routes real operators would.
- **M15 sale-booking:** unchanged. Every
  archetype exercises the M15 sync-sibling
  path via `record_sale` (retail_subprime
  fires 1 M15 entry for the BHPH sale;
  floor_planned fires 10 for the retail-
  finance + cash mix; bhph fires 5 for the
  recent BHPH sales).
- **M16 BHPH payment posting:** unchanged.
  The bhph archetype seeds ~5 unposted
  payments; the M16.1 detector runs at
  11:00 as it always has and posts them
  into the GL on next cycle.
- **M17 trial-balance materialization +
  `as_of` picker:** unchanged. The
  accounting daily briefs reference the
  M17 surface.
- **Internal service package additions:**
  `services/demo_store/` is new at M18.
  Zero touches to `services/f_and_i/`,
  `services/accounting/`,
  `services/bhph_*/`,
  `services/collection_contacts/`,
  `services/follow_ups/`, or any other
  M1-M17 package. Each archetype builder
  *consumes* the shipped service verbs
  (`record_sale`, `record_bhph_note`,
  `record_payment`, `record_promise`,
  `mark_kept`, `record_contact`,
  `record_repossession`, `mark_recovered`,
  `record_credit_application`,
  `start_cadence`) but never modifies
  them.
- **Tenancy carriers:** 49 → **50** (+1
  at M18.1: `TesterFeedback`).
- **Permission classes:** **7 actual**
  (unchanged). **Zero-drift streak
  extends to fourteen consecutive
  milestones** (M10 → M18.5).
- **Migrations:** `0043`–`0046` → `0043`–
  `0047` (+1 at M18.1 —
  `0047_m181_demo_store_substrate.py`
  bundling two `AddField` on `Dealership`
  + `CreateModel` for `TesterFeedback`).
- **Celery-beat task families:** 10
  (unchanged — no beat entry at M18).
- **AI safety stack:** 17 scrub stages
  (unchanged — M18 has no LLM path).

## 6. Lessons

Seven carry into M19+ planning.

1. **The §5-decisions-locked-at-open
   pattern held for a ninth milestone.** All
   seven §5 decisions at M18.0 open
   confirmed as-recommended. **77
   planning-time as-recommended M5.1 →
   M18.0** across nine consecutive
   milestones. Even the first non-accounting
   milestone since M12 — with a broader
   architecture / ownership / representation
   / safety scope than any prior milestone
   — resolved cleanly at the seven-decision
   surface. Future milestones can plan for
   6-8 §5 decisions depending on scope
   breadth.

2. **Coherence contract is the load-bearing
   commitment for validation infrastructure.**
   §Store-story coherence in the M18 brief
   said "seeded records must tell connected
   operational stories" — no Faker-style
   random population. The archetype builders
   spent significant lines *not* on writing
   more code but on tying seeded rows
   together (VehicleCost sums that reconcile
   with WorkOrder actual_cost;
   BhphPromiseToPay records that link to
   real BhphPayment rows via `mark_kept`;
   VehicleStageEvent progressions that walk
   the operational timeline). The M18.2 +
   M18.3 + M18.4 cross-domain integrity
   tests captured the contract explicitly.
   Future validation milestones (if any)
   should adopt the same discipline.

3. **Scanner tests are the right shape for
   guard-by-construction contracts.** The
   M18.1 outbound-egress scanner test
   greps `services/**/*.py` for
   `requests.`, `httpx.`, `smtplib.`, and
   `django.core.mail` imports; asserts each
   match is either behind the guard toolkit
   or on a documented allowlist. This is
   more robust than either (a) requiring
   every new adapter to remember the guard
   or (b) trying to intercept egress at the
   network layer. The scanner is simple,
   fast (runs in <0.1s), and fails loud
   when violated. **Any future contract
   that says "every X must Y" should
   consider a scanner test as the enforcement
   mechanism.**

4. **Belt-and-suspenders guards continue to
   pay off.** M18.1 introduced
   `NonDemoResetError` + `assert dealership
   .is_demo` at write-verb top. The pattern
   mirrors M15.1 / M16.1 / M17.1 broken-
   invariant guards. Two independent checks
   for the same invariant means a future
   refactor accidentally weakening one
   doesn't compromise the invariant. The
   registry COA seeding correction at M18.2
   was surfaced quickly because the
   `record_sale` path had its own
   `MissingDefaultAccountError` guard —
   without which the omission would have
   silently persisted.

5. **A 40-name synthetic roster is enough
   for four archetypes.** The
   `SYNTHETIC_NAMES` roster at 40 entries
   with modulo-wrap indexing serves 20-40
   vehicles + 4-6 salespeople + 10-25 leads
   + 5 recent buyers + 25 historical
   buyers per archetype without repetition
   feeling forced. Future archetypes can
   safely reuse the same roster; if
   collision emerges as a scenario concern,
   the growth-only-list posture allows
   appending new names without breaking
   deterministic indexing.

6. **Markdown briefs + file-system loader
   is simpler than a briefs DB model.** M18
   planning left the briefs delivery shape
   open at §7 M18.5. The implementation
   chose markdown files loaded at request
   time — no DB model, no migration, no
   admin surface. This is right for content
   that doesn't change per-tenant. If a
   future need arises to let operators
   customize briefs per demo dealership,
   the DB model can layer on top; today
   the simpler shape is sufficient.

7. **Zero-drift permission-class posture
   extends to fourteen consecutive
   milestones.** M18 added exactly one
   endpoint (M18.5 POST
   `/admin/demo-store/feedback/`) reusing
   `IsSalesManagerOrOwnerAtActiveDealership`.
   The streak (M10 → M18.5) confirms the
   platform's authorization surface has
   converged to a stable set of seven
   classes. Future milestones should
   default to reusing the existing set
   before considering new classes.

## 7. Streak update

**77 planning-time as-recommended M5.1 →
M18.0.** Nine consecutive milestones now
(M10 + M11 + M12 + M13 + M14 + M15 + M16 +
M17 + M18) with every §5 decision
confirmed as-recommended at planning-time
open. §0.a implementation-time micro-
decisions across M18.1 + M18.2 (five in
total: outbound-send-boundary enumeration,
Chargeback deferral, registry COA seeding,
reverse-order carrier deletion, demo-owned-
User cleanup) do not count against the
streak per M10 §9.

The pattern that held:

1. Draft the §5 recommendations at planning
   close of the *previous* milestone.
2. Confirm at the next milestone's opening
   session.
3. Amend §0.a as micro-decisions surface
   per implementation session.
4. Never re-vote a §5 decision mid-
   milestone — file the amendment as §0.a
   instead.

## 8. What M18 unblocks for M19+

The M18 shipped surface is validation
infrastructure. Its unlocks are
**empirical** — the substrate exists so
Chris can conduct founder-led tester
sessions and produce real operator
evidence to inform M19+ target selection.

**What's now unblocked by having demo
stores + briefs + feedback capture:**

- **Tester feedback ingestion.** Chris can
  hand demo stores to prospective pilot
  customers, watch them work through the
  briefs, and capture their observations
  via the M18.5 POST endpoint. The CSV
  exporter turns that into a review-ready
  artifact.
- **Willingness-to-pay signal.** The
  `willingness_to_pay` feedback category
  is the direct commercial signal the M18
  brief called out. When testers submit
  feedback in that category, Chris has a
  named commercial datum.
- **UX-polish backlog.** The M18.5 §5.f
  boundary parked "broader UI polish" for
  a later milestone. Tester feedback that
  concentrates on UX concerns builds the
  case for a dedicated UI-polish
  milestone.
- **F&I chargeback scenario.** The §0.a
  M18.2 decision 1 Chargeback deferral
  remains ready to un-defer if tester
  feedback surfaces the demand.
- **LLM cost caps for demo stores.** The
  §0.a M18.1 decision 1 LLM guard
  deferral remains ready to activate if
  tester usage burns significant tokens
  against synthetic inventory.

**Still-valid unblocked-work items from
earlier milestones** (per M17 §8):

- **Period-close comparison view / audit**
  (M17 §8). Trial-balance materialization
  is durable; comparison UI layers on top.
- **Financial-reports substrate (P&L,
  balance sheet).**
- **CSV / PDF export of frozen
  snapshots.**
- **Auto-freeze on schedule.**
- **Reopen / unfreeze workflow.**
- **M10 F&I chargeback GL reversal**
  (proven from three directions now).
- **NSF / payment-reversal workflow.**
- **Category-group-aware GL mapping for
  M13.2 detector.**
- **M14 UX polish (JE filters + sidebar
  nav)** — the `as_of` picker portion
  already shipped at M17.2.
- **Sale-reversal workflow.**
- **Post-sale VehicleCost variance
  handling.**
- **Deposit / bank reconciliation
  workflow.**
- **Method-aware fund-flow routing.**
- **BhphFee entity + late-fee GL
  posting.**
- **BHPH interest accrual detector
  (accrual-basis).**

## 9. Standing question — is M19 the "process real tester feedback" milestone?

Per M17 §9 the standing question was
"should M18 be an intentional UI-polish
milestone?" M18's answer was no —
validation infrastructure came first. The
M17 recommendation to "carry the question
forward but NOT preemptively lock" held.

**Standing question for M19 close:**
review at the end of M19 whether the
M18-produced tester feedback has actually
landed. If it has, M19 or M20 should be
the "process real tester feedback"
milestone — a scoped implementation
increment (or increments) driven by
what real operators surfaced. If tester
sessions haven't happened yet at M19
close, the question carries forward.

**Recommendation to bring to M19.0
open:** do not preemptively lock M19 as
the tester-feedback processing
milestone. M19 target selection should
follow the standard business-priority
pattern at M19.0 open. The candidates
from M18 planning §1 remain unblocked;
plus:

- **New candidate: process tester
  feedback (T)** — implement the two
  or three highest-signal items from
  the M18.5 CSV export. Scope depends
  on volume + quality of feedback.
- **New candidate: hosted-demo
  substrate (U)** — public self-serve
  demo signup + tester-tracking
  dashboard. Deferred at M18 per §3.
  Re-entry gated on Chris's
  willingness to hand demo stores to
  operators he doesn't already know.
- **New candidate: pilot-customer
  onboarding (V)** — real-data
  onboarding for testers who convert.
  Deferred at M18 per §3.

If no tester feedback has landed by
M19.0 open — because Chris hasn't yet
run tester sessions or has run one and
is still processing — the question
carries forward. M19 target selection
still follows business-priority; the
tester-feedback candidate is on the
list but doesn't get preemptive
priority.
