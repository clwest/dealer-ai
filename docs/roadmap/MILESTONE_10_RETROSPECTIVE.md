---
title: "Milestone 10 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-02
sessions: SESSION_106 → SESSION_113
milestone: 10
milestone_name: "Finance (F&I) deal desk"
related:
  - docs/roadmap/MILESTONE_10_PLANNING.md
  - docs/roadmap/MILESTONE_9_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 10
---

# Milestone 10 — Retrospective

Written at Milestone 10 close (SESSION_113).
Records what was planned, what shipped, what
deviated and why, and lessons carried forward
for Milestone 11 and beyond. Mirrors the
`MILESTONE_9_RETROSPECTIVE.md` structure.

## 1. Planned scope

`MILESTONE_10_PLANNING.md` at SESSION_105
defined the milestone as the F&I deal-desk
substrate: intake through funding, per FINANCE
§workflow (credit-app → deal structure →
lender submission → stip-chase → contract →
funding → post-funding chargebacks). §1.0
named nine operational questions synthesized
from `FINANCE_DEPARTMENT_MAPPING.md` (§1.1
credit-app data + §3 deal structure + §4
lender programs + §1.9 stipulations + §5
contract + funding + §5.7 chargebacks + §6
compliance + §6.9 retention).

§1.1–§1.9 followed with nine design memos
(CreditApplication, DealStructure,
LenderProgram + LenderSubmission, Stipulation,
Contract + BEPA, FundingPacket + FundingStatus,
Chargeback, ComplianceRecord, dashboard
endpoint surface). §5.a–§5.d drafted four
load-bearing decisions **all flagged
`[NEEDS-DECISION-BEFORE-M10.N]`** — plus the
§1.5 / §1.6 / §1.7 / §1.8 memos each carried
additional design questions the planning doc
explicitly deferred to session open. §7
sequenced eight increments (M10.1–M10.8).

**Original §7 sequencing shipped verbatim.**
The four SESSION_106 decisions confirmed as-
recommended (Option C / A / B / C). Then each
implementation session (SESSION_107 →
SESSION_112) opened with additional §5-
equivalent decisions surfaced from the design
memos — **twenty-nine load-bearing decisions
total** across the seven implementation
sessions, **all confirmed as-recommended by
the user** (a "streak" pattern that became a
signature of this milestone). **Eight §0.a
change-log amendments landed inside
increments** — one per implementation
session, each recording the decisions
resolved at that session's open plus any
substrate observations.

## 2. What actually shipped

Every §3 compatibility item verified true;
details in the annotated checklist at
`MILESTONE_10_PLANNING.md` §3 (this doc
enumerates below).

| Increment | Session | Shipped surface | Commit |
|---|---|---|---|
| M10.0 planning | 105 | `MILESTONE_10_PLANNING.md` (600+ lines) resolving zero load-bearing decisions and leaving four for user review at M10.1 open + additional design questions across §1.2 / §1.3 / §1.5 / §1.6 / §1.7 / §1.8 (deferred to per-session opens) | (in M9 close commit `b806dd1`) |
| M10.1 CreditApplication entity + retention discipline | 106 | New `CreditApplication` model + migration `0025_credit_application_entity` (nullable FKs to both `CustomerLead` (SET_NULL) and `Sale` (SET_NULL) per §5.a Option C; `applicant_full_name` + optional `applicant_ssn_last4` + `source_format` (`paper` / `tablet` / `online_prequal`) + `status` (`received` / `submitted` / `withdrawn`) + `captured_at` DateTime + `retention_expires_at` DateTime denormalized at write from `captured_at + CREDIT_APP_RETENTION_YEARS` (7 years per FINANCE §6.9) + `notes`). Model-layer `clean()`: attach-shape (≥1 parent) + cross-tenant guards on both parent FKs. **Retention clock locked at the model layer per §5.e** — `CreditApplication.delete()` refuses when `timezone.now() < retention_expires_at`, raising `CreditApplicationRetentionActiveError`. No `force=` escape hatch. New `services/f_and_i/` package with first submodule `credit_application.py` (`compute_retention_expires_at(captured_at)` pure verb using `dateutil.relativedelta` for leap-year-safe arithmetic + `record_credit_application(...)` transactional + `get_credit_application(pk, dealership)` tenant-scoped read). New `IsFinanceManagerOrOwnerAtActiveDealership` permission class in `permissions.py` (grants `f_and_i_manager` + `dealer_owner`; documents non-grant of `sales_manager` per compliance separation per FINANCE §6.4). First M10 endpoint `POST /api/dealer-ai/admin/credit-applications/` in new `views_f_and_i.py`. Tenancy-carrier extension 24 → 25. **Four §5 decisions confirmed as-recommended at session open** (§5.a Option C nullable both parents, §5.b Option A fixed 5-value stip vocab, §5.c Option B additive `net_realized` verb, §5.d Option C keep both lender fields). 52 focused tests | `50504eb` |
| M10.2 DealStructure entity + LTV/PTI/DTI | 107 | New `DealStructure` model + additive M10.1 CA extension (`gross_monthly_income` + `existing_monthly_debt` nullable Decimal columns) + migration `0026_deal_structure_entity`. FKs to `CreditApplication` CASCADE + `Vehicle` CASCADE (both mandatory per §1.2). Fields: sale_price / down_payment / trade_allowance / trade_payoff / taxes / fees / amount_financed / apr (percent units matching `payment_engine` convention) / term_months / monthly_payment / back_end_products JSONField + three denormalized ratio outputs (`ltv_pct` / `pti_pct` / `dti_pct` Decimal(6,2) nullable). New `services/f_and_i/deal_structure.py` with six verbs: three pure ratio verbs (`loan_to_value` always computable; `payment_to_income` returns `None` when income NULL; `debt_to_income` returns `None` when income or existing_debt NULL) + `record_deal_structure` transactional (computes ratios pre-save) + `get_deal_structure` tenant-scoped read + `recompute_ratios` for after-edit refresh. Second M10 endpoint `POST /admin/deal-structures/` (flat URL pattern per §1.9.a Option A). Tenancy-carrier extension 25 → 26. **Two §1.2 decisions confirmed at session open** (§1.2.a Option A income + debt on CA additive extension; §1.9.a Option A flat URL). 55 focused tests. **Fixed M10.1 tenant-carrier `==25` assertion → `>=25` + membership check** (see §4 lesson 12 note). | `b7c9bf3` |
| M10.3 LenderProgram + LenderSubmission | 108 | New `LenderProgram` model (per-dealership catalog; unique `(dealership, name)`; `is_active` soft-delete pattern) + new `LenderSubmission` model (mandatory FK to `DealStructure` CASCADE per §1.3.a Option A; FK to `LenderProgram` **PROTECT** — new pattern for this project) + migration `0027_lender_entities`. Fixed 4-value `status` vocab per §1.3.b Option A (`pending` default / `approved` / `counter` / `declined`). Free-form JSON `counter_terms` + `approval_terms` per §1.3.d Option A. New `services/f_and_i/lender.py` — six verbs including typed `DuplicateLenderProgramError` (409 on unique-constraint violation, matches M9.1 `SaleAlreadyExistsError` pattern). Three new endpoints (POST program + POST submission + PATCH submission for status updates). Tenancy carriers 26 → 28 (both entities). **Four §1.3 decisions confirmed at session open** (all Option A/B). 53 focused tests | `19c5519` |
| M10.4 Stipulation tracking | 109 | New `Stipulation` model + migration `0028_stipulation_entity`. Mandatory FK to `LenderSubmission` CASCADE per §1.4.a Option A. FK to `settings.AUTH_USER_MODEL` `documented_by` nullable SET_NULL per §1.4.c Option A (audit trail). Fixed 5-value `stip_type` vocab per §5.b Option A (from SESSION_106). Fixed 3-value `state` vocab per §1.4.b Option A (`open` default / `cleared` / `waived`). `cleared_at` auto-populated by service on first cleared/waived transition; reset to NULL on transition back to open (operator error correction). Photo/document evidence deferred to M10.7 per §1.4.d Option A. New `services/f_and_i/stipulation.py` with four verbs including `update_stipulation_state` any-to-any transition. Two new endpoints (POST + PATCH); **PATCH sources `documented_by` from `request.user` server-side** — new audit-trail pattern that removes a class of "wrong user" bugs. Tenancy carrier 28 → 29. **Four §1.4 decisions confirmed at session open** (all Option A). 35 focused tests | `e9d311f` |
| M10.5 Contract + BEPA + Funding | 110 | Three new entities in one increment (**largest single M10 sketch**): `Contract` (FK to `DealStructure` CASCADE per §1.5.c Option A; three-state machine `unsigned` default → `signed` → optional `voided` per §1.5.b Option A; Reg Z disclosure fields per FINANCE §6.1) + `BackEndProductAgreement` (FK to Contract per §1.5.a Option B — per-product rows enable M10.6 per-product chargeback attribution; fixed 6-value `product_type` vocab per §1.5.d Option A; optional per-product structural fields per FINANCE §4.3-§4.5) + `Funding` (OneToOne to Contract per §1.6.a Option C — single Funding entity, no persisted FundingPacket; state machine `pending_funding` default → `funded` → `chargedback` vocab shipped now for M10.6). Migration `0029_contract_funding`. Two new service modules: `services/f_and_i/contract.py` (six verbs) + `services/f_and_i/funding.py` (three verbs). **New pattern: two-verb transition** (`sign_contract` / `void_contract`, `record_funding` / `mark_funded`) rather than generic state updater — auto-populated timestamps are business facts, not side effects. Sign-after-void refused (409). Five new endpoints. Tenancy carriers 29 → 32 (three new). **Five §1.5 + §1.6 decisions confirmed at session open** (§1.5.a Option B / §1.6.a Option C / §1.5.b Option A / §1.5.c Option A / §1.5.d Option A). 42 focused tests | `0729a7d` |
| M10.6 Chargeback + net_realized | 111 | New `Chargeback` model + additive BEPA cancellation-field extension (`cancelled_at` + `cancellation_amount` nullable per §1.7.c Option A) + migration `0030_chargeback_and_bepa_cancellation`. Nullable FKs to both `Contract` and `BackEndProductAgreement` (both CASCADE) per §1.7.a Option A (mirrors M10.1 §5.a Option C). Fixed 5+1 `chargeback_type` vocab per §1.7.b Option B (FINANCE §5.7 five triggers + `other` fallback). Audit trail via `recorded_by` FK to User SET_NULL sourced from `request.user` per §1.7.e Option A. New `services/f_and_i/chargeback.py` — three verbs. **`record_chargeback` introduces atomic cross-model side effects** — one transaction, one Chargeback insert + one Funding auto-transition (deal-level types only per §1.7.f Option A) + one BEPA auto-populate (product_cancellation only). `net_realized(sale)` additive verb per §5.c Option B (SESSION_106) — no M9 schema change; attribution via Contract → DealStructure → Vehicle path unioned with BEPA-only chargebacks; distinct pk set prevents double-counting. One new endpoint. Tenancy carrier 32 → 33. **Six §1.7 decisions confirmed at session open** (all Option A/B as-recommended). 36 focused tests | `bd68548` |
| M10.7 ComplianceRecord + operator UI | 112 | New `ComplianceRecord` model (OneToOne to Contract CASCADE per §1.8.a Option A — matches FINANCE §6.9 deal-jacket alignment) + additive URL extensions on Stipulation (`evidence_url`) + BEPA (`product_agreement_url`) per §1.8.c Option C + migration `0031_compliance_record_and_evidence_urls`. Single-entity typed-columns model per §1.8.b Option A — seven typed columns covering FINANCE §6.1-§6.9 concerns (Reg Z / OFAC + `ofac_hit` bool / Red Flags + `red_flags_notes` / Privacy / Safeguards / Adverse Action + `adverse_action_reason` / Retention denormalized from parent CA) + `deal_jacket_url` external document reference. **No upload plumbing at M10.7** per §1.8.c Option C — URL fields only; full Cloudinary/S3 wiring is a discrete post-M10 initiative. New `services/f_and_i/compliance.py` with four verbs: `record_compliance` (auto-populates retention from parent CA) + `update_compliance` (targeted save with **field-whitelist**, new pattern) + `get_compliance` + `deal_jacket_summary(contract)` (pure aggregate bundling all related entities for the operator UI). Four new backend endpoints. **First F&I operator UI** at `/dealer-ai-f-and-i/` per §1.8.e Option A (new route family). Two-tab MVP per §1.8.d Option A: `DealerFandIDeals.tsx` (filterable deals-in-progress list) + `DealerFandICompliance.tsx` (per-deal compliance-audit view with seven mark-timestamp actions + related stipulations + chargebacks + funding state). New `fAndIApi.ts` client + `ClipboardCheck` nav entry. Tenancy carrier 33 → 34. **Six §1.8 decisions confirmed at session open** (Options A / A / C / C / A / A). 31 backend + 17 frontend focused tests. **Split-close ratified** per §1.8.f Option A — M10.8 is documentation-only | `5d91e22` |
| M10.8 closeout | 113 | This retrospective + `CAPABILITY_MATRIX.md` §7k + `IMPLEMENTATION_ROADMAP.md` §M10 SHIPPED flip + `MILESTONE_10_PLANNING.md` frontmatter flip + `DEALER_KIT_SESSION_START.md` refresh + `MILESTONE_11_PLANNING.md` created per standing user directive. Coordinated commit + user-authorized batch push of all M10.1-M10.8 stages | (TBD this session) |

## 3. Planning-doc amendments landed inside increments

**Seven `§0.a` change-log amendments were
required inside M10.1–M10.7**, all surfaced at
increment open before code landed. This is
above M9's five amendments. The signal, again,
is not "planning quality dropped" — every M10
amendment was a design decision the planning
doc explicitly deferred to session open,
resolved with user confirmation before code
landed. This is the planning discipline
working exactly as designed.

1. **SESSION_106 M10.1 open — four §5
   decisions confirmed as-recommended.** §5.a
   Option C (CreditApplication attach shape:
   nullable FKs to both `CustomerLead` and
   `Sale`; at least one required via
   `clean()`). §5.b Option A (fixed 5-value
   stip vocabulary — deferred to M10.4 for
   use). §5.c Option B (additive
   `net_realized` verb, no M9 schema change).
   §5.d Option C (leave both — structured
   `LenderProgram` catalog additive alongside
   existing free-text
   `DealerOnboardingProfile.subprime_lenders`).

2. **SESSION_107 M10.2 open — two §1.2 + §1.9
   decisions confirmed as-recommended.**
   §1.2.a Option A (income + existing-debt
   capture on M10.1 CA as additive nullable
   Decimal columns per M8 §6 lesson 11
   additive-extension pattern). §1.9.a Option
   A (flat `/admin/deal-structures/` URL
   pattern matching M10.1's shipped shape
   rather than the planning-time
   `/admin/f-and-i/deal-structures/`
   grouping).

3. **SESSION_108 M10.3 open — four §1.3
   decisions confirmed as-recommended.**
   §1.3.a Option A (mandatory FK to
   DealStructure). §1.3.b Option A (fixed
   4-value status). §1.3.c Option A (per-
   dealership catalog). §1.3.d Option A
   (free-form JSON terms; vocabulary emerges
   at M10.7 compliance layer if evidence
   surfaces).

4. **SESSION_109 M10.4 open — four §1.4
   decisions confirmed as-recommended.**
   §1.4.a Option A (mandatory FK to
   LenderSubmission). §1.4.b Option A (fixed
   3-value state). §1.4.c Option A
   (`documented_by` User FK SET_NULL for
   audit trail; sourced server-side from
   `request.user`). §1.4.d Option A (defer
   photo/document evidence to M10.7 —
   confirmed at M10.7 open as URL fields
   only).

5. **SESSION_110 M10.5 open — five §1.5 +
   §1.6 decisions confirmed as-recommended.**
   §1.5.a Option B (separate
   BackEndProductAgreement entity — enables
   M10.6 per-product chargeback attribution).
   §1.6.a Option C (single `Funding` entity,
   no persisted FundingPacket — packet is a
   view over Contract + Stipulation + related
   rows). §1.5.b Option A (three-state
   contract). §1.5.c Option A (FK to
   DealStructure only). §1.5.d Option A (fixed
   6-value product_type vocab).

6. **SESSION_111 M10.6 open — six §1.7
   decisions confirmed as-recommended.**
   §1.7.a Option A (nullable both parents,
   mirrors M10.1 §5.a Option C). §1.7.b
   Option B (5+1 vocab with `other`). §1.7.c
   Option A (additive BEPA cancellation
   fields). §1.7.d Option A (verb in
   `services/f_and_i/chargeback.py`, avoids
   cross-service import from
   `services/analytics/`). §1.7.e Option A
   (full audit trail with `recorded_by`
   FK). §1.7.f Option A (deal-level auto-
   transition Funding to `chargedback`;
   `product_cancellation` and `other`
   explicitly excluded — matches FINANCE
   §5.7 semantics).

7. **SESSION_112 M10.7 open — six §1.8
   decisions confirmed as-recommended.**
   §1.8.a Option A (OneToOne per Contract —
   FINANCE §6.9 deal-jacket alignment).
   §1.8.b Option A (single-entity typed-
   columns model over per-concern rows).
   §1.8.c Option C (URL fields for external
   document references, no upload plumbing).
   §1.8.d Option C (two-tab MVP — deals list
   + per-deal compliance audit; full 7-step
   operator workflow via existing per-vehicle
   drill-downs). §1.8.e Option A (new
   `/dealer-ai-f-and-i/` route family).
   §1.8.f Option A (split M10.7 impl / M10.8
   close-out per M9-close SESSION_105
   pattern).

## 4. Deviations

**Accepted improvements** (all landed inside
increments):

1. **Combined migration `0026`** — the plan
   projected the DealStructure model as its
   own migration. M10.2's additive
   CreditApplication extension bundled with
   the DealStructure CreateModel in one
   atomic migration. Cleaner than two-
   migration path: one reverse operation,
   one atomic delivery. §0.a SESSION_107
   amended.

2. **Combined migration `0030`** — same
   pattern at M10.6: BEPA cancellation-
   fields AddField × 2 + Chargeback
   CreateModel in one atomic migration.
   §0.a SESSION_111 amended.

3. **Combined migration `0031`** — same
   pattern at M10.7: Stipulation +
   BackEndProductAgreement URL AddField × 2
   + ComplianceRecord CreateModel in one
   atomic migration. §0.a SESSION_112
   amended.

4. **Two-verb transition pattern
   (M10.5+)** — `sign_contract` /
   `void_contract` and `record_funding` /
   `mark_funded` shipped as distinct
   service verbs rather than a generic
   `update_state`. Auto-populated
   timestamps (`signed_at` / `voided_at` /
   `funded_at`) are business facts, not
   arbitrary state-change side effects.
   The M10.4 stipulation
   `update_stipulation_state` generic
   pattern was preserved for the case
   where transitions are semantically
   equivalent (open ↔ cleared ↔ waived).
   Both patterns are valid; choose based
   on whether the timestamp is a
   business fact or a mechanical side
   effect.

5. **Atomic cross-model side effects
   (M10.6)** — `record_chargeback` ships
   with two atomic side effects (Funding
   auto-transition + BEPA auto-populate)
   in one `transaction.atomic` block.
   Prior service verbs had at most
   single-row side effects; M10.6
   introduced multi-model atomicity.
   `skip_funding_transition=True` kwarg
   for edge cases (partial reversal,
   operator override).

6. **URL fields over upload plumbing
   (M10.7)** — the planning doc left
   photo/document storage open through
   M10.4 + M10.5, deferred to M10.7.
   M10.7 §1.8.c Option C shipped nullable
   URL fields for external document
   references (Google Drive / DMS) rather
   than full Cloudinary/S3 upload
   infrastructure. Captures operator
   reality (docs live in existing shared
   systems) without adding significant
   substrate. Full upload plumbing
   remains a post-M10 initiative if
   evidence demands.

7. **Two-tab MVP over full 7-step UI
   (M10.7)** — the planning doc §1.9
   sketched a full F&I workflow surface;
   M10.7 §1.8.d Option C shipped a
   narrower two-tab MVP (deals list +
   per-deal compliance audit). Serves
   FINANCE §7.6 pain-point directly.
   Full 7-step workflow operates via
   existing per-vehicle drill-downs from
   M9.5.

**Deferrals cataloged** (not dropped;
scheduled for follow-up increments or
future milestones):

- **Photo / document upload plumbing** —
  deferred to post-M10 per M10.4 §1.4.d
  Option A + M10.5 non-goal + M10.7
  §1.8.c Option C. Candidate for M11.
- **Full F&I operator UI (7-step
  workflow)** — M10.7 shipped a two-tab
  MVP per §1.8.d Option A. Full CRUD
  UIs across credit-apps / deal
  structures / lender submissions /
  stips / chargebacks operate via
  admin API endpoints; dedicated
  frontend surfaces land later if
  operator evidence surfaces need.
- **Server-side pagination on deals
  list** — M10.7 ships 100-row server
  cap; client-side pagination. Add
  server-side pagination in M11+ if
  operator evidence demands.
- **Compliance-record close-out
  automation for voided contracts** —
  M10.7 leaves voided contracts with
  their compliance rows as historical
  records; no automatic close-out
  logic.
- **`resync_retention` verb on
  ComplianceRecord** — M10.7
  denormalizes `retention_expires_at`
  from parent CreditApplication at
  ComplianceRecord create time. If CA
  retention is later extended (legal
  hold, rule change), the denorm
  becomes stale. Add a resync verb
  post-M10 if evidence demands.
- **Bureau-response integration** —
  M10.2 `existing_monthly_debt` is
  operator-entered from the bureau
  report; direct bureau-portal
  integration deferred beyond M10.
- **Lender-portal integrations** —
  planning §scope-boundary explicit
  non-goal.
- **DMS write-back integrations** —
  planning §scope-boundary explicit
  non-goal.
- **BHPH portfolio + collections** —
  Milestone 12 substrate.
- **Accounting integration** — future
  milestone.
- **`AnalyticsCache` materialization
  layer** — carry-forward from M8. No
  M10 endpoint produced latency
  evidence justifying materialization.

**No planned scope dropped** in the sense
of a shipped-but-broken feature or
silently-missing invariant. Every deferral
recorded with a clear re-entry path.

## 5. Compatibility

Every §3 compatibility row verified true
with inline evidence at
`MILESTONE_10_PLANNING.md` §3.

- **Backend test baseline:** **3,730 pass**,
  1 skipped, 0 fail at SESSION_112 close.
  Delta: **+304 tests** over M9 close
  baseline (3,426 → 3,730); 0
  regressions.
- **Frontend test baseline:** **51 pass**
  at SESSION_112 close (was 34 at M9
  close; +17 exactly per M10.7 plan).
- **M2 ledger substrate byte-for-byte
  preserved.** M9.1 `Sale.gross_realized`
  computation unchanged; M10.6
  `net_realized` verb is additive per §5.c
  Option B (no M9 schema change).
- **M4 WorkOrder substrate preserved.**
  Not touched.
- **M5 lifecycle preserved.** Not
  touched.
- **M8 aggregation surface preserved.**
  Not touched.
- **M9.1 Sale substrate preserved.**
  `Sale.buyer` FK / `Sale.gross_realized`
  denormalized column / `Sale.finance_type`
  vocabulary all unchanged. M10 read paths
  attach via new FKs; no M9 write paths
  modified.
- **M9.2 Delivery substrate preserved.**
  Not touched.
- **Additive M10.1 CA extension (M10.2).**
  Two nullable Decimal columns
  (`gross_monthly_income`,
  `existing_monthly_debt`) added at M10.2
  via migration `0026`. M10.1-era rows
  survive NULL; PTI / DTI ratio verbs
  return `None` for them.
- **Additive M10.5 BEPA extension (M10.6).**
  Two nullable columns (`cancelled_at`,
  `cancellation_amount`) added at M10.6
  via migration `0030`. M10.5-era rows
  survive NULL.
- **Additive M10.4 Stipulation extension
  + M10.5 BEPA extension (M10.7).** URL
  fields (`evidence_url`,
  `product_agreement_url`) added at M10.7
  via migration `0031`. Both blank by
  default.
- **Tenancy carriers 24 → 34.** M10.1
  added `CreditApplication` (25), M10.2
  added `DealStructure` (26), M10.3
  added `LenderProgram` (27) +
  `LenderSubmission` (28), M10.4 added
  `Stipulation` (29), M10.5 added
  `Contract` (30) +
  `BackEndProductAgreement` (31) +
  `Funding` (32), M10.6 added
  `Chargeback` (33), M10.7 added
  `ComplianceRecord` (34). Same
  `pre_save` autofill safety net as
  M1-M9 carriers.
- **DRF admin surface 47 → 64.** 17 new
  endpoints across M10.1-M10.7 (M10.1 1
  + M10.2 1 + M10.3 3 + M10.4 2 + M10.5
  5 + M10.6 1 + M10.7 4). All role-
  gated on the M10.1
  `IsFinanceManagerOrOwnerAtActiveDealership`
  permission class (reused unchanged at
  M10.2-M10.7 — zero permission-class
  drift across the F&I surface).
- **Frontend operator routes 9 → 11.**
  Two new routes at M10.7
  (`dealer-ai-f-and-i` +
  `dealer-ai-f-and-i/:contract_id/compliance`).
- **First F&I frontend surface.** M10.7
  ships the two-tab MVP under
  `/dealer-ai-f-and-i/`. Existing M9.5
  analytics tab + per-vehicle sale page
  render unchanged after M10.7.
- **`tsc --noEmit` + `vite build` clean**
  at every M10 session close.
- **`makemigrations --check --dry-run`
  clean** after M10.1 (`0025`), M10.2
  (`0026`), M10.3 (`0027`), M10.4
  (`0028`), M10.5 (`0029`), M10.6
  (`0030`), M10.7 (`0031`). M10.8
  shipped no schema changes.
- **`services/f_and_i/` package
  completeness.** Seven submodules by
  M10.7 close: `credit_application.py`
  (M10.1) + `deal_structure.py` (M10.2)
  + `lender.py` (M10.3) +
  `stipulation.py` (M10.4) +
  `contract.py` + `funding.py` (M10.5) +
  `chargeback.py` (M10.6) +
  `compliance.py` (M10.7). Complete F&I
  service surface for the M10 scope.

## 6. Lessons

Nineteen lessons carried forward for
Milestone 11 and beyond. Sixteen inherit
from M9 §6 with M10 evidence; three are
new to M10.

1. **Increment discipline.** Every M10
   sub-increment shipped independently
   verifiable in one session. Every
   session opened with load-bearing
   decisions confirmed by the user
   before code landed. Twenty-nine
   decisions across seven implementation
   sessions, all resolved at session
   open. Carry-forward.

2. **Backend-first architecture;
   frontend never owns business rules.**
   M10.1–M10.6 shipped zero frontend.
   M10.7 wired the two-tab MVP as a
   pure consumer of the M10 admin
   endpoint surface. `documented_by` /
   `recorded_by` FK values sourced
   server-side from `request.user` at
   the endpoint layer, not client body
   — new audit-trail pattern that
   removes a class of "wrong user"
   bugs. Carry-forward.

3. **Provider-neutral boundaries.** No
   new provider dependencies added by
   M10. `dateutil.relativedelta` used
   at M10.1 for leap-year-safe
   arithmetic on the 7-year retention
   window — Django transitive
   dependency, already installed.
   Reused recharts (M8.5) for any new
   charts (none needed at M10). No new
   LLM integration in M10. Carry-forward.

4. **Service ownership — one
   authoritative write path per
   operation.** Seven service modules
   under `services/f_and_i/`, each
   owning its entity's writes. The
   endpoint layer is thin translation.
   No business logic in views.
   Carry-forward.

5. **Local vs production parity.** M10
   shipped no new runtime dependencies.
   Same test-mode gates as M8/M9 apply.
   Carry-forward.

6. **Honest verification reporting.**
   Every M10 endpoint carries a role-
   gate matrix test. `net_realized`
   verb distinguishes "no chargebacks"
   (returns `sale.gross_realized`
   unchanged) from "chargebacks sum to
   zero" (subtracts zero). PTI / DTI
   ratio verbs return `None` when
   inputs missing rather than 0.
   Carry-forward.

7. **Storage-first / safer-direction
   deletion.** M10.1's
   `CreditApplication.delete()` refuses
   unexpired records at the model
   layer per §5.e — no service-only
   guard, no `force=` escape hatch.
   Model-layer enforcement of the
   retention invariant. Carry-forward.

8. **Load-bearing decisions get user
   review BEFORE code.** M10's core
   pattern. **Twenty-nine load-bearing
   decisions across seven
   implementation sessions**, every
   one resolved at session open before
   code landed. Zero mid-implementation
   churn. Carry-forward.

9. **Distinct domain errors → distinct
   behaviors.** M10 endpoints return
   400 for malformed args + unknown
   vocabulary values + missing-both-
   parents, 404 for missing / cross-
   tenant references, 409 for
   duplicates (SaleAlreadyExists,
   DuplicateLenderProgram,
   FundingAlreadyExists,
   ContractAlreadyVoided,
   ComplianceAlreadyExists). Six
   distinct 409-emitting error classes
   across M10 service modules.
   Carry-forward.

10. **Read-model properties are pure
    reads.** Preserved. `deal_jacket_summary(contract)`
    at M10.7 aggregates related
    entities into a dict for the
    operator UI — pure verb, no
    mutation. All M10 ratio verbs +
    `net_realized` verb pure.

11. **Additive extension over fork.**
    M10.2 added additive CA columns
    without modifying M10.1's model or
    tests. M10.6 added additive BEPA
    columns without modifying M10.5.
    M10.7 added additive URL fields on
    Stipulation + BEPA without
    modifying prior tests. Textbook
    additive extension. Carry-forward.

12. **Prior-increment count assertions
    use `>=` not `==`.** M10.1's
    tenant-carrier test asserted
    `==25`; M10.2's carrier add broke
    it. Fixed at M10.2 close by
    loosening to `>=25` + membership
    check. **Saved a feedback memory
    at SESSION_107** so future
    increments don't repeat the trap.
    The `>=` pattern is now project
    posture — every M10.2-M10.7 test
    used `>=N` for its carrier count.
    Carry-forward from M9 lesson 14
    reinforced by M10 evidence.

13. **Two-tier customer-visibility
    gate.** Not exercised in M10
    (all endpoints admin-scoped).
    Preserved.

14. **Verify handoff / planning
    claims via direct inspection
    before acting.** Applied at M10.6
    open when reviewing the FINANCE
    §5.7 chargeback types before
    proposing the vocabulary; applied
    at M10.7 open when reviewing the
    FINANCE §6.1-§6.9 concerns before
    proposing the typed-columns model.
    Carry-forward from M9 lesson 15
    with M10 evidence.

15. **Substrate-gap pushback is a
    productive session-open pattern**
    (M9-new). Not exercised at M10
    proper — the planning doc's
    deferred design questions (surfaced
    at each session open) served the
    same function as substrate-gap
    pushback in M9. The pattern
    generalizes: when the planning
    doc leaves a design question
    open, the correct action at
    session open is to surface it
    with recommendations + trade-offs
    before code lands. **This is the
    plan-open pushback pattern.**
    Carry-forward.

16. **[NEW] Streak-pattern
    confidence.** Every M10 session
    resolved every open decision as-
    recommended (Option A/B/C
    matching my recommendation).
    Twenty-nine consecutive
    "confirmed as-recommended"
    resolutions. The pattern isn't
    proof of correctness — it's a
    signal that the recommendations
    were well-scoped and the user's
    planning framework worked. If a
    future recommendation gets
    reopened by the user, the value
    is in the pushback — the answer
    isn't wrong until reviewed. The
    default should be to present
    recommendations with reasoning +
    trade-offs and expect the user
    to reopen when their context
    disagrees. **The streak is not
    the goal; the trust is.**

17. **[NEW] Two-verb transition
    pattern for distinct-audit-
    trail moments.** M10.5's
    `sign_contract` / `void_contract`
    and `record_funding` /
    `mark_funded` shipped as
    distinct verbs rather than a
    generic `update_state`. Auto-
    populated timestamps are
    business facts, not arbitrary
    side effects. **Contrast M10.4's
    `update_stipulation_state`
    generic pattern** — preserved
    for the case where transitions
    are semantically equivalent
    (open ↔ cleared ↔ waived). Both
    patterns are valid; choose
    based on whether the timestamp
    is a business fact or a
    mechanical side effect.
    Carry-forward.

18. **[NEW] Atomic cross-model side
    effects with opt-out kwarg.**
    M10.6's `record_chargeback`
    introduced multi-model
    atomicity — one transaction,
    one Chargeback insert + one
    Funding auto-transition (deal-
    level types only) + one BEPA
    auto-populate (product_
    cancellation only). Prior
    service verbs had at most
    single-row side effects.
    `skip_funding_transition=True`
    kwarg for edge cases. The
    pattern generalizes to any
    verb that must coordinate
    writes across sibling entities
    to preserve a business
    invariant. **Design goal is
    "one operator action = one
    atomic write" from the
    operator's mental model.**
    Carry-forward.

19. **Field-whitelist for partial-
    update verbs** (M10.7
    `compliance.py::update_compliance`).
    `_UPDATABLE_FIELDS` frozenset
    protects against typos and
    misplaced kwargs. Any future
    partial-update service verb
    should adopt the same shape.
    Carry-forward as a project
    convention.
