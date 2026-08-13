---
title: "Milestone 12 — Implementation-Planning Pass"
status: shipped
type: planning-artifact
generated: 2026-08-02
generated_at_session: SESSION_120 (post-M11-closeout)
milestone: 12
milestone_name: "BHPH portfolio operations (v1)"
shipped_at_session: SESSION_128
retrospective: docs/roadmap/MILESTONE_12_RETROSPECTIVE.md
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_11_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_11_PLANNING.md
  - docs/roadmap/MILESTONE_10_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
---

# Milestone 12 — Implementation-Planning Pass

> **Planning-skeleton status.** Drafted at
> M11.7 close per standing user directive
> (M10.8 precedent). Full memo expansion +
> §5 decision surface + §7 sequencing
> refinement land at M12.0 (SESSION_121)
> open. This document exists so
> SESSION_121 opens with a concrete
> starting point rather than a blank page.

## 0. Engineering practices to preserve from M2-M11

Same posture as M11.0. Non-negotiable:

- **Backend-first architecture.** No
  business logic in the frontend.
- **Service ownership.** One authoritative
  write path per operation, per M4-M11.
- **Tenancy discipline.** Every write path
  passes `dealership=` explicitly; the
  pre_save autofill is a safety net.
- **Distinct domain errors → distinct
  HTTP statuses** per M9/M10/M11
  convention (404 cross-tenant, 409
  state-machine / duplicate, 400
  vocab / validation).
- **Load-bearing decisions get user
  review BEFORE code.** Present with
  recommendation + trade-offs; user
  confirms or overrides; record in
  §0.a per M5-M11 precedent.
- **Additive extension over fork.**
  Follow M11.1's `CustomerLead.channel`
  pattern for any additions to existing
  entities.
- **Every M12 test asserting tenant-
  carrier / permission-class / endpoint
  counts uses `>=N`** per M9 §6 lesson
  14 / M10 §6 lesson 12 / M11 §6 lesson
  12. **Vocab-set assertions use exact
  equality** per M11 §6 lesson 18.
- **Read-only surfacer vs state-
  transitioning detector** — pick the
  Celery-beat shape by whether the
  trigger is operator intent or elapsed
  condition per M11 §6 lesson 17.
- **Atomic sibling-service boundary
  crossings** — wrap in
  `@transaction.atomic` + refuse re-
  execution rather than silently
  duplicating per M11 §6 lesson 19.

## 0.a Change log (implementation-time amendments)

Per M5/M6/M7/M8/M9/M10/M11 §9 mandates,
load-bearing planning decisions may need
narrow amendment at implementation time
as substrate reality asserts itself.
Every amendment records the session,
option, and the affected sections.

*(None yet — planning-time only.
Amendments recorded at the top of each
M12 session that requires one.)*

---

## 1. Design memo

### 1.0 The operational questions Milestone 12 must answer

Questions synthesized from
`BHPH_OPERATIONS_MAPPING.md`. Full memo
expansion at M12.0 open; skeleton here.

| # | Question | Research citation |
|---|---|---|
| 1 | **How does the platform originate a BHPH note from a signed M10 Contract when the dealer is the lender?** | BHPH §origination + M10.5 Contract handoff |
| 2 | **What payment-schedule shape supports weekly / biweekly / semi-monthly BHPH cadences?** | BHPH §payment cadence + M2 payment-engine BHPH math (already shipped) |
| 3 | **How does the platform intake a payment (cash / check / debit / ACH) and apply it (fees → interest → principal)?** | BHPH §payment intake + §payment application |
| 4 | **How does the platform detect delinquency + tag escalation buckets?** | BHPH §delinquency detection (aging buckets) |
| 5 | **How does the platform track PTPs (promise-to-pay) + reconcile them against actual payments?** | BHPH §PTP tracking + pain #7 |
| 6 | **How does the platform log collection contacts with FDCPA-compliant documentation?** | BHPH §collections + FDCPA discipline |
| 7 | **How does the platform record repossession events (order → agent → recovery → intake)?** | BHPH §repo workflow + inventory reintake |
| 8 | **How does the platform surface portfolio-level aging + owner reporting?** | BHPH §portfolio activities + pain #10 |
| 9 | **How does the platform hand a repo'd vehicle back into the M2/M4/M5 recon-and-relist pipeline?** | BHPH §post-repo disposition + M2/M4/M5 substrate |

### 1.1 BHPH Note origination + payment schedule

- **Business questions answered.** Q1, Q2.
- **Shape.** New `BhphNote` model.
  OneToOne with M10.5 `Contract` when
  `Contract.contract_type == "bhph"` (new
  vocab member added at M10.5 or M12
  planning-time decision — §5.a). Fields:
  `principal_financed` / `apr` / `term_weeks`
  / `payment_frequency` (weekly /
  biweekly / semi_monthly) / `payment_amount`
  / `first_payment_due` / `default_grace_days`.
  Payment schedule seeded at note create
  via `services/bhph_payments/` verb
  (mirrors M11.4 `start_cadence` +
  `FollowUpTask` seeding pattern).

### 1.2 Payment intake + application

- **Business questions answered.** Q3.
- **Shape.** New `BhphPayment` model
  (FK to `BhphNote` CASCADE). Fields:
  `paid_at` / `amount` / `method`
  (cash / check / debit / ach / other) /
  `applied_to_fees` / `applied_to_interest`
  / `applied_to_principal` (all
  denormalized at write time by the
  payment-application verb). New
  `services/bhph_payments/apply.py`
  with pure `apply_payment(note, amount)`
  → `(fees, interest, principal)` tuple
  (following M2 payment_engine + M9
  pure-verb pattern).

### 1.3 Delinquency detection + aging buckets

- **Business questions answered.** Q4.
- **Shape.** Celery-beat detector at
  08:00 project-time daily (next slot
  after M11.5 07:00). Per-tenant task
  reads active BhphNotes + computes
  days-past-due, tags to bucket vocab
  (`current` / `1_15` / `16_30` /
  `31_60` / `61_90` / `over_90` /
  `charge_off_candidate`). Writes
  denormalized `current_bucket` column
  on BhphNote. **State-transitioning
  detector** per M11 §6 lesson 17 (aging
  is objectively elapsed — matches M11.5
  no-show shape, not M11.4 surfacer
  shape).

### 1.4 PTP (promise-to-pay) tracking

- **Business questions answered.** Q5.
- **Shape.** New `BhphPromiseToPay`
  entity (FK to `BhphNote` CASCADE).
  Fields: `promised_at` / `promised_amount`
  / `promised_reason` (matches M11.5
  BeBack promised_reason pattern —
  fixed vocab) / `actual_payment` FK
  to BhphPayment (nullable — populated
  on reconcile) / `state` (`promised` /
  `kept` / `broken` — mirrors M11.5
  BeBack `promised` → `returned` /
  `no_show` shape). Celery detector
  auto-transitions promised → broken on
  the M11.5 pattern.

### 1.5 Collection contact log + FDCPA scrub

- **Business questions answered.** Q6.
- **Shape.** New `CollectionContact`
  model (FK to `BhphNote` CASCADE).
  Fields: `contacted_at` /
  `contacted_by_user` FK User SET_NULL /
  `channel` (phone / letter / sms /
  email / in_person) / `outcome`
  (contact_made / left_message /
  no_answer / refused_to_speak) /
  `notes`. **New post-LLM scrub layer**:
  `collection-language scrub` — belt-
  and-suspenders against FDCPA-adjacent
  drafted phrasing (deficiency threats,
  harassment-adjacent language,
  false-representation claims). Extends
  existing `services/llm_safety.py`
  scrub stack.

### 1.6 Repossession record

- **Business questions answered.** Q7,
  Q9.
- **Shape.** New `Repossession` model
  (FK to `BhphNote` CASCADE). Fields:
  `ordered_at` / `ordered_by_user` /
  `agent_name` / `recovered_at`
  nullable / `recovery_location` /
  `intake_condition_report_id` FK to
  M3 ConditionReport nullable (populated
  when the vehicle re-enters recon).
  Ties into M4 recon substrate for
  the post-repo relist path.

### 1.7 Portfolio aging + owner reporting

- **Business questions answered.** Q8.
- **Shape.** New `services/bhph_analytics/`
  package. Pure aggregate verbs
  computing portfolio-level metrics
  (bucket counts + dollar amounts,
  cure rate, weighted-average APR,
  weighted-average days-past-due, PTP
  kept ratio). DRF endpoints under
  `/admin/bhph/analytics/*` matching
  the M8 analytics pattern. Frontend
  dashboard at `/dealer-ai-bhph/`
  (new route family).

### 1.8 Post-repo disposition handoff

- **Business questions answered.** Q9.
- **Shape.** Repossession → M4
  ConditionReport → M5 lifecycle
  `frontline` re-entry. No new
  substrate — the existing M3/M4/M5
  pipeline handles once the vehicle
  gets a new stock number (or the
  original number is re-used per
  operator convention — §5 decision).

### 1.9 Operator UI

- **Shape.** New `/dealer-ai-bhph/`
  route family. Pages: portfolio
  dashboard (bucket summary) +
  per-note detail (payment history +
  PTPs + collection log + repo
  status). MVP scope TBD per §5
  decision.

---

## 2. Non-goals (explicit)

- ❌ GPS / starter-interrupt device
  integration (v2 BHPH milestone).
- ❌ Skip-tracing service integration
  (v2).
- ❌ Credit-bureau reporting (Metro 2
  furnisher) (v2).
- ❌ Static-pool cohort analysis (v2).
- ❌ Repo agent dispatch integration
  (v2).
- ❌ Automated deficiency judgment
  paperwork (v2).
- ❌ Modification of M10.5 Contract
  semantics beyond additive
  `contract_type=bhph` vocab member
  (§5.a).
- ❌ M11 deferrals (DealWriteup UI +
  delivery adapters + operator-
  configurable cadence templates +
  auto-cadence-on-BeBack integration +
  named-platform webhook adapters) —
  these belong to a separate M11.x
  follow-up track, not M12.

---

## 3. Compatibility summary

*(To be filled at M12.1 open — after §5
decisions ratify shape. Placeholder rows:)*

- Backend test baseline unchanged at
  M12.0; target delta at M12 close TBD.
- Frontend Vitest baseline unchanged at
  M12.0; target delta TBD.
- M1-M11 substrates preserved.
  Consumption is FK-only + additive
  extensions per the M8 §6 lesson 11 /
  M11 §6 lesson 11 pattern.

---

## 4. Migration path (per-increment)

*(To be filled at each M12.N open. New
migrations `0037`+.)*

---

## 5. Load-bearing decisions requiring user review

Six decisions drafted at M11.7 close;
expansion + recommendations land at
M12.0 (SESSION_121) open.

### 5.a `[NEEDS-DECISION-BEFORE-M12.1]` — Contract type vocab extension

**Question.** Does M12.1 add `bhph` as
a new member of the M10.5 Contract
`contract_type` vocab, or does BHPH
Note origin from a distinct signal
(e.g. `Sale.finance_type == "bhph"`
already shipped at M9.1)?

**Recommendation drafted:** Option A —
BhphNote OneToOne with M10.5 Contract
when the M9 `Sale.finance_type == "bhph"`;
no M10.5 vocab change. Preserves M10.5
byte-for-byte. Recommendation to be
refined at M12.1 open.

### 5.b `[NEEDS-DECISION-BEFORE-M12.1]` — Payment application order

**Question.** Fees → interest →
principal is the industry standard;
does M12.2 make that order
configurable per BhphNote, or is it a
platform-wide constant?

**Recommendation drafted:** Option A —
platform-wide constant at M12; per-
note override deferred until operator
evidence surfaces need.

### 5.c `[NEEDS-DECISION-BEFORE-M12.3]` — Aging bucket vocabulary

**Question.** Fixed 7-value vocab
(`current` / `1_15` / `16_30` /
`31_60` / `61_90` / `over_90` /
`charge_off_candidate`) per §1.3, or
operator-configurable bucket
boundaries?

**Recommendation drafted:** Option A —
fixed vocab (matches M11.1 vocab-set
pattern; per M11 §6 lesson 18 —
vocab additions are planning-level
decisions).

### 5.d `[NEEDS-DECISION-BEFORE-M12.4]` — PTP reconciliation shape

**Question.** Automatic
reconciliation when a BhphPayment
lands within N days of a
BhphPromiseToPay for a matching
amount, or operator-triggered link?

**Recommendation drafted:** Option A —
operator-triggered link (matches
M11.4 §0.a decision 3 posture —
transitions that require judgment
stay operator-triggered).

### 5.e `[NEEDS-DECISION-BEFORE-M12.5]` — Collection contact scrub scope

**Question.** New scrub layer
extending `services/llm_safety.py`
scrub stack, or a dedicated
`services/bhph_scrub/` package?

**Recommendation drafted:** Option A —
extend existing scrub stack.
Preserves the single-authority
posture for post-LLM safety.

### 5.f `[NEEDS-DECISION-BEFORE-M12.7]` — Operator UI scope

**Question.** Full M12.1-M12.7 UI
coverage at M12.7, or MVP scope
matching M11.6 pattern (deferred
DealWriteup precedent)?

**Recommendation drafted:** Option C —
MVP scope. Portfolio dashboard +
per-note detail. Collection contact
UI + repo-order UI can defer to a
follow-on if operator evidence
demands.

### 5.g Test posture

Standard. TestCase for models +
services; APIClient for endpoints;
`override_settings` for grace-period
+ aging-boundary tests (matches
M11.5 detector test posture). Vocab
tests use exact-set equality; growth
lists use `>=`.

---

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 12
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_RETROSPECTIVE.md`
   §6 (nineteen lessons carry into M12)
6. `docs/CAPABILITY_MATRIX.md` §7l
7. `docs/research/BHPH_OPERATIONS_MAPPING.md`
8. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
   (F&I → BHPH handoff)

---

## 7. Sequencing draft

*(Initial draft — user refinement expected
at M12.0 open. Sequence adjustable.)*

### Increment 0 (M12.0) — Planning refinement + first-decision review

**Scope.** SESSION_121. Review §5
decisions with user; refine §7
sequencing if needed. Optional
narrow implementation start.

### Increment 1 (M12.1) — BhphNote origination + payment schedule

**Scope.** BhphNote model + FK to
Contract per §5.a; payment schedule
seeded from principal / APR / term
/ frequency via new
`services/bhph_notes/` package.

**Tests.** ~30 focused (larger —
BHPH math surface, payment schedule
correctness).

### Increment 2 (M12.2) — Payment intake + application

**Scope.** `BhphPayment` model +
`apply_payment` pure verb (fees →
interest → principal) + payment
intake endpoint. Denormalized
allocation columns on BhphPayment
per M9.1 gross_realized pattern.

**Tests.** ~30 focused.

### Increment 3 (M12.3) — Delinquency detection + aging buckets

**Scope.** Celery-beat detector at
08:00 daily per §1.3. Aging bucket
vocab per §5.c. Denormalized
`current_bucket` column on
BhphNote.

**Tests.** ~25 focused (matches
M11.5 detector shape).

### Increment 4 (M12.4) — PTP tracking

**Scope.** `BhphPromiseToPay`
entity + three-verb service
package (mirrors M11.5 BeBack
shape).

**Tests.** ~25 focused.

### Increment 5 (M12.5) — Collection contact log + FDCPA scrub

**Scope.** `CollectionContact`
entity + service package + new
scrub layer per §5.e.

**Tests.** ~25 focused.

### Increment 6 (M12.6) — Repossession + post-repo handoff

**Scope.** `Repossession` entity +
service package + M3/M4/M5
handoff path.

**Tests.** ~20 focused.

### Increment 7 (M12.7) — Portfolio analytics + operator UI

**Scope.** `services/bhph_analytics/`
package + `/dealer-ai-bhph/` route
family per §5.f Option C (MVP).

**Tests.** ~15 backend + ~20
frontend.

### Increment 8 (M12.8) — Closeout

**Scope.** Documentation-only per
M10.8 / M11.7 precedent.
Retrospective + capability matrix
§7m + roadmap flip + planning
frontmatter + session-start
refresh + M13 planning skeleton
+ coordinated commit + push.

---

## 8. Related documents

- `docs/PROJECT_RULES.md`
- `docs/DOC_GOVERNANCE.md`
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 12
- `docs/roadmap/AUTHENTICATION_MODEL.md`
- `docs/roadmap/MILESTONE_11_RETROSPECTIVE.md`
- `docs/roadmap/MILESTONE_11_PLANNING.md`
- `docs/research/BHPH_OPERATIONS_MAPPING.md`
- `docs/CAPABILITY_MATRIX.md` §7l
- Current source code — authoritative.

---

## 9. Load-bearing decisions summary — items requiring user review before M12.N

Every `[NEEDS-DECISION-BEFORE-M12.N]`
in this document, consolidated:

1. **§5.a — Contract type vocab
   extension.** Recommended: Option A
   (no M10.5 vocab change; use M9
   `Sale.finance_type == "bhph"` as
   signal).
2. **§5.b — Payment application
   order.** Recommended: Option A
   (platform-wide constant).
3. **§5.c — Aging bucket vocabulary.**
   Recommended: Option A (fixed 7-value
   vocab).
4. **§5.d — PTP reconciliation shape.**
   Recommended: Option A (operator-
   triggered link).
5. **§5.e — Collection contact scrub
   scope.** Recommended: Option A
   (extend existing scrub stack).
6. **§5.f — Operator UI scope.**
   Recommended: Option C (MVP).

**All six recommendations to be
confirmed at M12.1 open per the M5-M11
recommend-and-approve precedent.** M11
streak stands at 35 planning-time as-
recommended M5.1 → M11.1; M12.1
resolution starts the M12 arc.
