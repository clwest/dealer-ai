---
title: "Milestone 10 — Implementation-Planning Pass"
status: draft
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_105 (post-M9-closeout)
milestone: 10
milestone_name: "Finance (F&I) deal desk"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_9_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_9_PLANNING.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
---

# Milestone 10 — Implementation-Planning Pass

**Purpose.** Acceptance contract for Milestone 10
(Finance (F&I) deal desk). Every implementation
increment cites back here for scope, invariants,
and refinement provenance. Mirrors the shape M3 /
M4 / M5 / M6 / M7 / M8 / M9 planning docs proved
out.

**Business objective (from `IMPLEMENTATION_ROADMAP.md`
§Milestone 10).** Support F&I workflow from
customer commit through funding. Reduce stip-chase
pain, chargeback reconciliation lag, and per-deal
jacket incompleteness. Every step in the F&I
process serves one of two questions: *Will a
lender approve this customer on this vehicle at
terms that work? Can the deal be delivered clean?*

**Research anchors.** `FINANCE_DEPARTMENT_MAPPING.md`
§workflow (credit-app intake → deal structure →
lender submission → approval / counter → stips →
contract → funding → post-funding chargebacks) +
§compliance (retention 2–7 years; adverse-action;
privacy; safeguards; red flags) + pains #1 (data
re-entry across ≥7 systems), #4 (stip creep), #6
(lender programs held in memory), #7 (15–40 open
deals with various stip states tracked in F&I
manager's head), #9 (chargeback exposure lag).

**Zero implementation this session.** Planning
artifact only. SESSION_106 opens M10.1.

---

## 0. Engineering practices to preserve from M2-M9

Synthesized from the eight prior retrospectives.
Every practice below is a load-bearing constraint
on M10.

*(Mirrors the M9 §0 structure; the sixteen M9
lessons in `MILESTONE_9_RETROSPECTIVE.md` §6
carry forward with M10 evidence expected.)*

Two lessons will get exercised particularly hard
at M10 because F&I data is uniquely sensitive:

- **Lesson 8 — load-bearing decisions get user
  review BEFORE code.** M10 has the largest
  design surface of any milestone so far
  (credit apps, deal structure math, lender
  panel, stip vocabulary, funding packet
  shape, chargeback reconciliation). Every
  §5 decision must surface at increment open,
  not silently at implementation time.
- **Lesson 16 — substrate-gap pushback is a
  productive session-open pattern.** New at
  M9. F&I depends on M1 auth (customer credit
  data is the most sensitive doc in the
  building), M9.1 Sale (chargeback reversal
  target), M2 ledger (commission math
  substrate). Any planning-time assumption
  about these substrates that fails direct
  inspection triggers plan-scoped pushback.

---

## 0.a Change log (implementation-time amendments)

Per M5/M6/M7/M8/M9 §9 mandates, load-bearing
planning decisions may need narrow amendment at
implementation time as substrate reality asserts
itself. Every amendment records the session,
option, and the affected sections.

### SESSION_106 (M10.1 open) — §5.a / §5.b / §5.c / §5.d confirmed

- **Amendment.** All four §5 load-bearing
  decisions confirmed by the user at
  SESSION_106 open. No spec changes — the
  recommended path becomes the ratified
  path (§5.a resolved from TBD in favor of
  Option C after FINANCE §workflow re-read).
- **§5.a — CreditApplication attach point:
  Option C.** Nullable FKs to both
  `CustomerLead` **and** `Sale`. Credit
  apps intake at lead time (Lead FK set,
  Sale FK null); on close, the Sale FK is
  set (Lead FK preserved). Matches FINANCE
  §workflow (credit-app intake precedes
  deal structure and sale close) and
  prevents re-orphaning if the operational
  anchor moves from lead to sale.
- **§5.b — Stipulation vocabulary:
  Option A.** Small fixed set: `proof_of_income`
  / `proof_of_insurance` / `proof_of_residence`
  / `references` / `other`. Extend when
  operator evidence surfaces need. Matches
  M9.1 finance-type precedent (`cash` /
  `retail` / `bhph`).
- **§5.c — Chargeback impact on
  `Sale.gross_realized`: Option B.** Zero
  M9 schema change. A new verb
  `services/f_and_i/computation.py::net_realized(sale)`
  will sit alongside M9.1's
  `gross_realized` when M10.7 lands.
  Follows M8 §6 lesson 11 additive-
  extension pattern.
- **§5.d — Onboarding lender migration:
  Option C.** Zero data loss. The
  structured `LenderProgram` catalog
  (M10.3) is additive alongside the
  existing free-text
  `DealerOnboardingProfile.subprime_lenders`
  field; the free-text field becomes a
  notes area.
- **Effect on §7 M10.1 scope.**
  - Ships (unchanged): `CreditApplication`
    model + migration `0025` + retention
    clock at the model layer +
    `services/f_and_i/` package (with
    `record_credit_application` + read
    verb + retention-clock verb) +
    tenancy carrier 24 → 25 + new
    permission class
    `IsFinanceManagerOrOwnerAtActiveDealership`
    + first endpoint + ~30 tests.
  - Attach shape (§5.a=C): `lead` FK
    nullable, `sale` FK nullable. At least
    one required at write time (model-
    layer `clean()`).
  - Non-goals unchanged (M10.2-M10.7
    deferred).

---

## 1. Design memo

### 1.0 The operational questions Milestone 10 must answer

Nine questions synthesized from
`FINANCE_DEPARTMENT_MAPPING.md`:

| # | Question | Research citation |
|---|---|---|
| 1 | **What credit-app data do we capture, and how do we retain it under legal safeguards?** | FINANCE §compliance (retention 2–7 years) + §workflow (credit-app intake) |
| 2 | **What deal-structure math surface does F&I need — LTV / PTI / DTI / affordable-payment gates?** | FINANCE §workflow (deal structure) + existing §3.2 payment-math primitive |
| 3 | **How does the platform track which lenders each deal was submitted to and their status?** | FINANCE pain #6 (lender programs in memory) + §workflow (lender submission → approval / counter) |
| 4 | **How does the platform track stipulations per deal, per lender, over time?** | FINANCE pain #4 (stip creep) + pain #7 (open-deals stip-state in memory) |
| 5 | **How does the platform capture the signed contract (RISC) + product agreements?** | FINANCE §workflow (contract) |
| 6 | **How does the platform assemble a funding packet + track funding status?** | FINANCE §workflow (funding) |
| 7 | **How does the platform reconcile post-funding chargebacks back to commission?** | FINANCE pain #9 (chargeback exposure lag) + §workflow (post-funding) |
| 8 | **How does the platform enforce retention + adverse-action + red-flags compliance?** | FINANCE §compliance |
| 9 | **How does the platform surface deal state to sales manager + dealer owner without re-entry?** | FINANCE pain #1 (data re-entry across ≥7 systems) |

**Questions Milestone 10 does NOT answer**
(deliberate):

- **Direct lender-portal integrations** —
  IMPLEMENTATION_ROADMAP §Milestone 10 explicit
  non-goal (belongs to a future vendor-
  integration milestone).
- **E-contracting provider integration** — same.
- **Automated bureau pull integration** — same
  (belongs to a compliance-heavy future
  milestone).
- **Sales-tax computation** — belongs to
  Accounting track.
- **DMS write-back** — carry-forward non-goal
  from M9.
- **Portfolio-level BHPH analytics** — depends
  on Milestone 12 BHPH substrate.

### 1.1 CreditApplication entity

- **Business questions answered.** Q1, Q8.
- **Shape.** New `CreditApplication` model
  attached to a `CustomerLead` (or possibly
  `Sale` — decide at planning close). Fields
  minimally include applicant identity,
  employment, income, residence, monthly-
  obligations summary, requested vehicle,
  requested finance-type. Legal retention
  clock (`created_at` + `retention_expires_at`
  computed from policy constants) at the
  persistence layer.
- **Test posture.** Standard: TestCase +
  cross-tenant guards + M4-M9 authorization
  matrix. **Retention field is a load-bearing
  invariant** — locked at the model layer,
  not at the service layer.

### 1.2 DealStructure entity

- **Business questions answered.** Q2, Q9.
- **Shape.** New `DealStructure` model linking
  a `CreditApplication` to a `Vehicle`.
  Fields: `sale_price`, `down_payment`,
  `trade_allowance`, `trade_payoff`, `taxes`,
  `fees`, `amount_financed`, `apr`, `term_months`,
  `monthly_payment`, `back_end_products`
  (JSON — VSC / GAP / etc.), `ltv_pct`,
  `pti_pct`, `dti_pct`. `services/f_and_i/`
  computes the ratios; the model stores the
  results as denormalized fields for query-
  ability. Extends the existing §3.2
  `payment_engine` primitive (which today
  handles standard-APR + BHPH weekly/biweekly).

### 1.3 LenderProgram + LenderSubmission entities

- **Business questions answered.** Q3, Q6.
- **Shape.** New `LenderProgram` model
  (per-dealership catalog of active lender
  programs; extends the onboarding
  `subprime_lenders` free-text field into
  structured data — decide at planning
  close whether to migrate the existing
  field or run both). New `LenderSubmission`
  model linking a `DealStructure` to a
  `LenderProgram` with `submitted_at`,
  `status` (`pending` / `approved` /
  `counter` / `declined`), `counter_terms`
  (JSON), `approval_terms` (JSON), `notes`.

### 1.4 Stipulation tracking

- **Business questions answered.** Q4, Q9.
- **Shape.** New `Stipulation` model attached
  to a `LenderSubmission`. Fields:
  `stip_type` (from a vocabulary — proof of
  income, proof of insurance, proof of
  residence, references, etc.), `state`
  (`open` / `cleared` / `waived`),
  `documented_by`, `cleared_at`, `notes`.
  Vocabulary partitioning is a load-bearing
  §5 decision (see below).

### 1.5 Contract + product-agreement records

- **Business questions answered.** Q5, Q8.
- **Shape.** New `Contract` model attached
  to a `DealStructure` capturing the signed
  RISC + optional back-end products. Fields:
  `contract_type` (RISC / lease / cash),
  `signed_at`, `signed_by`, `financed_amount`,
  `total_of_payments`, `finance_charge`,
  `apr_disclosure` (regulatory-mandated
  disclosure text), `first_payment_date`.

### 1.6 Funding entities

- **Business questions answered.** Q6, Q9.
- **Shape.** New `FundingPacket` +
  `FundingStatus` entities. Packet assembles
  the docs required by the lender at
  funding time (RISC copy, stips cleared,
  title status, etc.). Status tracks
  `submitted_to_lender_at`, `funded_at`,
  `funding_amount`.

### 1.7 Chargeback record + commission reversal

- **Business questions answered.** Q7.
- **Shape.** New `Chargeback` model attached
  to a `Contract`. Fields: `chargeback_type`
  (product-cancellation / early-payoff /
  contract-rewrite), `chargeback_date`,
  `chargeback_amount`, `commission_reversal`
  (Decimal — computed from the M9.1
  `Sale.gross_realized` via a new verb).
  Requires modification to M9.1
  `gross_realized` semantics: today the
  denormalized column is populated at Sale
  write; M10.7 needs to write chargeback
  events that adjust the effective realized
  gross without corrupting the historical
  write value. **Decide at planning close
  whether to (a) add a `net_realized` field
  on Sale, or (b) compute chargeback-
  adjusted gross on-demand via a new verb.**

### 1.8 Compliance record

- **Business questions answered.** Q8.
- **Shape.** Per-deal compliance record
  covering retention clock, adverse-action
  timestamps, privacy-notice acknowledgment,
  safeguards audit trail, red-flags checks.
  Structure TBD — a single `ComplianceRecord`
  entity vs. per-concern models. Decide at
  planning close.

### 1.9 Dashboard endpoint surface

- **Shape.** New DRF endpoints under
  `/api/dealer-ai/admin/f-and-i/` for the
  M10 entities. Role-gated on a new
  `IsFinanceManagerOrOwnerAtActiveDealership`
  permission class (must add to `permissions.py`
  — `f_and_i_manager` role already exists in
  M1 `ROLE_CHOICES`). Decide at planning
  close whether other roles (sales_manager,
  dealer_owner) also read.

### 1.10 Operator UI

- **Shape.** New route
  `/dealer-ai-f-and-i/` — deal-jacket
  browser + funding-status board + stip-
  chase surface + chargeback-reconciliation
  view. Extensive; likely splits into
  multiple pages.

---

## 2. Migration impact review

*(Skeleton — filled in at M10.1 planning close.)*

| # | Existing surface | Location | M10 impact |
|---|---|---|---|
| 1 | `_TENANT_CARRIER_MODEL_NAMES` | 24 at M9 close | Additive: `CreditApplication`, `DealStructure`, `LenderProgram`, `LenderSubmission`, `Stipulation`, `Contract`, `FundingPacket`, `FundingStatus`, `Chargeback`, `ComplianceRecord`. 24 → ~34 depending on decomposition. |
| 2 | `services/analytics/` | 6 aggregations at M9 close | Additive: F&I dashboards (funded-deals count, stip-cycle time, chargeback rate). |
| 3 | Frontend operator routes | 9 at M9 close | Additive: at least `/dealer-ai-f-and-i/` (may split). |
| 4 | `Sale.gross_realized` semantics | denormalized at M9.1 write | **Possibly modified per §1.7 decision** — chargeback events adjust effective gross. Decide additive `net_realized` field vs. new `net_realized` verb. |

---

## 3. Compatibility checklist

*(Skeleton — filled in per-increment as M10.1-M10.N
plan.)*

- **M1 (auth):** required. New
  `IsFinanceManagerOrOwnerAtActiveDealership`
  gate. Retention clocks respected at the
  service layer.
- **M2 (ledger):** read-only.
- **M3-M8 substrate:** untouched.
- **M9 substrate:** additive extension only
  per §1.7 decision. Existing `Sale` +
  `Delivery` continue to work as-is.

---

## 5. Scope discipline + load-bearing decisions

### 5.a `[NEEDS-DECISION-BEFORE-M10.N]` — CreditApplication attach point

**Question.** Does `CreditApplication` attach
to `CustomerLead` (the M3-M5 CRM substrate) or
to `Sale` (the M9.1 substrate)?

**Options.**

- **Option A** — attach to `CustomerLead`.
  Credit apps precede sale close; the lead is
  the operational anchor at credit-app time.
- **Option B** — attach to `Sale`. Only sold
  deals get credit apps in the system; every
  other credit app is out-of-band.
- **Option C** — nullable FK to both. Credit
  app can attach to lead early and gain a
  Sale reference at close.

**Recommended for user review at M10.1 open:**
TBD — will surface after re-reading FINANCE §workflow.

### 5.b `[NEEDS-DECISION-BEFORE-M10.N]` — Stipulation vocabulary partition

**Question.** Is the stipulation vocabulary a
small fixed set (proof of income / insurance /
residence / references / other) or an
extensible tuple per dealership?

**Options.**

- **Option A** — small fixed set (5-8 values).
  Simple; matches M9.1 finance-type
  precedent.
- **Option B** — per-dealership extensible.
  Every stip becomes a per-tenant catalog
  row; requires a `StipulationType` model.

**Recommended for user review:** Option A —
start small, extend when operator evidence
surfaces need.

### 5.c `[NEEDS-DECISION-BEFORE-M10.N]` — Chargeback impact on `Sale.gross_realized`

**Question.** How does M10.7 chargeback
reconciliation affect M9.1's denormalized
`Sale.gross_realized` column?

**Options.**

- **Option A** — add a `net_realized` field
  on `Sale` (denormalized at write time as
  equal to `gross_realized`; chargeback
  events adjust it). Two columns tell the
  story: what we made at sale, what we
  kept after chargebacks.
- **Option B** — leave `gross_realized`
  unchanged (the original as-sold value);
  compute chargeback-adjusted gross via a
  new verb. Zero schema impact on M9.
- **Option C** — replace `gross_realized`
  with `net_realized` (renamed). Breaks
  M9.3 analytics queries.

**Recommended for user review:** Option B —
zero M9 disturbance; a new verb
(`services/f_and_i/computation.py::net_realized(sale)`)
sits alongside M9.1's
`gross_realized`. Follows the M8 §6 lesson
11 additive-extension pattern.

### 5.d `[NEEDS-DECISION-BEFORE-M10.N]` — Onboarding profile lender migration

**Question.** Does M10.3 migrate the existing
`DealerOnboardingProfile.subprime_lenders`
free-text field into structured
`LenderProgram` rows?

**Options.**

- **Option A** — data migration + drop the
  free-text field.
- **Option B** — leave the free-text field;
  operators re-populate lenders in the new
  M10.3 surface.
- **Option C** — leave both; the free-text
  field becomes a "notes" area alongside
  the structured catalog.

**Recommended for user review:** Option C —
zero data loss; the structured catalog is
additive.

### 5.e Test posture

Standard. TestCase for models + services;
APIClient for endpoints. Every write path
gated on
`IsFinanceManagerOrOwnerAtActiveDealership`.
**Retention clocks locked at the model
layer** — a service-only enforcement lets
callers bypass; the model refuses
`delete()` on unexpired records.

---

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md` §6
   (sixteen lessons carry into M10)
6. `docs/CAPABILITY_MATRIX.md` §7j
7. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
   §workflow + §compliance + pains #1 / #4 /
   #6 / #7 / #9
8. Current source code — authoritative.

Planning docs are claims. Rules + research +
code are facts.

---

## 7. Increment sequencing

*(Skeleton — refined at planning-time close.
Likely six or seven increments.)*

### Increment 1 (M10.1) — CreditApplication entity + retention discipline

**Scope.** New `CreditApplication` model +
migration. Model-layer retention clock. First
endpoint scaffolding. Tenancy-carrier
extension.

**Tests.** ~30 focused.

### Increment 2 (M10.2) — DealStructure entity + ratio computation

**Scope.** New `DealStructure` model + verb
package + LTV / PTI / DTI math. Reuses
§3.2 `payment_engine` for monthly-payment
math.

**Tests.** ~30 focused.

### Increment 3 (M10.3) — LenderProgram + LenderSubmission entities

**Scope.** New `LenderProgram` +
`LenderSubmission` models. Onboarding
profile lender integration per §5.d
decision.

**Tests.** ~25 focused.

### Increment 4 (M10.4) — Stipulation tracking

**Scope.** New `Stipulation` model per §5.b
vocabulary decision. Stip-lifecycle verbs.

**Tests.** ~20 focused.

### Increment 5 (M10.5) — Contract + Funding entities

**Scope.** New `Contract` +
`FundingPacket` + `FundingStatus`
entities. Funding-packet assembly verb.

**Tests.** ~25 focused.

### Increment 6 (M10.6) — Chargeback + commission reversal

**Scope.** New `Chargeback` model + `net_realized`
verb (per §5.c Option B). Reconciliation
back to M9.1 `Sale`.

**Tests.** ~20 focused.

### Increment 7 (M10.7) — Compliance record + operator UI

**Scope.** `ComplianceRecord` entity. New
`/dealer-ai-f-and-i/` operator UI (deal-
jacket browser + stip-chase board +
funding-status view + chargeback
reconciliation).

**Tests.** ~20 backend + ~25 frontend
Vitest.

### Increment 8 (M10.8) — Closeout

**Scope.** Documentation-only.
Retrospective, capability matrix §7k,
roadmap flip, planning frontmatter,
session-start refresh,
`MILESTONE_11_PLANNING.md` per standing
user directive, coordinated commit + push.

---

## 8. Related documents

- `docs/PROJECT_RULES.md`
- `docs/DOC_GOVERNANCE.md`
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 10
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
- `docs/roadmap/MILESTONE_9_PLANNING.md`
- `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
- `docs/CAPABILITY_MATRIX.md` §7j
- Current source code — authoritative.

---

## 9. Load-bearing decisions summary — items requiring user review before M10.N

Every `[NEEDS-DECISION-BEFORE-M10.N]` in this
document, consolidated:

1. **§5.a — CreditApplication attach point.**
   Recommendation TBD at M10.1 open.
2. **§5.b — Stipulation vocabulary partition.**
   Recommended: Option A (small fixed set).
3. **§5.c — Chargeback impact on
   `Sale.gross_realized`.** Recommended:
   Option B (additive `net_realized` verb;
   no M9 schema change).
4. **§5.d — Onboarding lender migration.**
   Recommended: Option C (leave both).

Decisions surface at the top of the M10
session that would first act on them —
same discipline as M5/M6/M7/M8/M9 §9
mandates.
