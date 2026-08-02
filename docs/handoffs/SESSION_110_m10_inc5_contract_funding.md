---
title: "SESSION_110 handoff — Milestone 10 · Increment 5 (M10.5 — Contract + BackEndProductAgreement + Funding)"
status: historical
type: handoff
date: 2026-08-02
session: 110
milestone: 10
milestone_status: in_progress
increment: 5
increment_status: shipped
commit: 0729a7d
---

# SESSION_110 — Milestone 10 · Increment 5 (M10.5 — Contract + BackEndProductAgreement + Funding)

## What shipped

Three new F&I entities substrate for the
contract-signing → funding workflow +
two new service modules
(`services/f_and_i/contract.py` +
`services/f_and_i/funding.py`) with
nine verbs + five new DRF endpoints
(Contract create + PATCH sign/void,
BackEndProductAgreement create,
Funding create + PATCH mark_funded)
+ tenancy carrier extensions (29 →
32) + 42 focused tests. Five design
questions surfaced at session open
and were confirmed with the user
(all as-recommended);
`MILESTONE_10_PLANNING.md` §0.a
amended.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§1.5.a — Contract entity split:
   Option B.** Two entities:
   `Contract` + separate
   `BackEndProductAgreement`. Per-
   product rows unlock M10.6 per-
   product chargeback attribution
   per FINANCE §5.7 without a
   schema migration + backfill.
2. **§1.6.a — FundingPacket vs
   FundingStatus entity boundary:
   Option C.** Single `Funding`
   entity with state machine only.
   Packet as persisted entity
   would over-engineer M10.5;
   FINANCE §5.1 shows the packet
   is a per-submission view over
   Contract + Stipulation + related
   rows, materializable at M10.7.
3. **§1.5.b — Contract state
   machine: Option A.** Three
   states: `unsigned` (default) →
   `signed` → optional `voided`.
   `voided` preserves audit trail
   for FINANCE §5.8 deal unwinds.
   Two distinct service verbs
   (`sign_contract` /
   `void_contract`) rather than a
   generic state updater.
4. **§1.5.c — Contract attach
   point: Option A.** Mandatory FK
   to `DealStructure` (CASCADE)
   only. Cash contracts have a
   DealStructure but no
   LenderSubmission; operators
   navigate
   `DealStructure.lender_submissions`
   for financed deals.
5. **§1.5.d — Product-agreement
   vocabulary: Option A.**
   Structured `BackEndProductAgreement`
   entity with fixed
   `product_type` vocabulary
   (`vsc` / `gap` / `t_and_w` /
   `prepaid_maint` / `appearance`
   / `other`) matching M10.1
   §5.b + M10.3 §1.3.b + M10.4
   §5.b fixed-vocab precedent.

**M10.5 deliverables (six):**

1. **Three new models + migration
   `0029`.**
   - `Contract` — FK to
     `DealStructure` CASCADE
     (mandatory). Fields:
     `contract_type` (RISC /
     lease / cash), `state`
     (unsigned default / signed /
     voided), `signer_name`,
     `signed_at`, four Reg Z
     disclosure fields
     (`financed_amount` /
     `total_of_payments` /
     `finance_charge` /
     `apr_disclosure` per
     FINANCE §6.1),
     `first_payment_date`,
     `voided_at` +
     `voided_reason`.
   - `BackEndProductAgreement` —
     FK to `Contract` CASCADE.
     Fields per FINANCE §4.3-§4.5:
     `product_type` from fixed
     6-value vocab, `provider`
     (free-text at M10.5), `cost`
     + `retail_price` (base
     at-write economics), optional
     `term_months` /
     `mileage_limit` /
     `deductible` per-product-
     type. Cancellation fields
     deferred to M10.6.
   - `Funding` — OneToOne to
     `Contract` CASCADE (business
     invariant: one funding per
     contract; unwinds require a
     new Contract row per FINANCE
     §5.8). State machine:
     `pending_funding` default →
     `funded` → optional
     `chargedback` (M10.6 wires
     transition; vocabulary
     shipped now to avoid
     migration then).
     `submitted_to_lender_at`,
     `funded_at`, `funding_amount`
     (nullable — populated on
     mark-funded transition;
     may differ from
     `Contract.financed_amount`
     per FINANCE §2.4 lender
     discount fees).
2. **Tenancy carrier extensions
   29 → 32** (all three
   entities).
3. **New `services/f_and_i/contract.py`**
   — six verbs:
   - `record_contract(...)` —
     transactional. Creates in
     `unsigned` state. Cross-
     tenant + unknown-vocab
     rejection.
   - `sign_contract(contract,
     signer_name=..., signed_at=...)`
     — state transition. Auto-
     populates `signed_at` on
     first transition; preserves
     on subsequent. Refuses if
     contract is `voided`
     (`ContractAlreadyVoidedError`
     → 409). Per FINANCE §5.8
     unwind pattern, voided
     contracts require a new
     Contract row.
   - `void_contract(contract,
     voided_reason=..., voided_at=...)`
     — state transition. Auto-
     populates `voided_at` +
     records operator-provided
     `voided_reason`. Preserves
     `signed_at` (both moments
     are distinct historical
     events).
   - `record_back_end_product(...)`
     — transactional. Attaches
     BEPA to contract. Cross-
     tenant + unknown-vocab
     rejection.
   - `get_contract(pk, dealership)`
     — pure read, tenant-scoped.
   - `list_products_for_contract(contract)`
     — pure read. FK filter.
4. **New `services/f_and_i/funding.py`**
   — three verbs:
   - `record_funding(dealership,
     contract, submitted_to_lender_at=...,
     notes=...)` — transactional.
     Creates in `pending_funding`
     state. Cross-tenant +
     duplicate-Funding rejection
     (`FundingAlreadyExistsError`
     → 409).
   - `mark_funded(funding,
     funding_amount=..., funded_at=...,
     notes=...)` — state
     transition. Auto-populates
     `funded_at` on first
     transition + records
     `funding_amount`. Preserves
     `funded_at` on subsequent.
   - `get_funding(pk,
     dealership)` — pure read,
     tenant-scoped.
5. **`services/f_and_i/__init__.py`
   facade** — extended to re-
   export the nine new M10.5
   verbs + typed errors alongside
   M10.1-M10.4 exports.
6. **Five new endpoints.** All
   role-gated on
   `_M101_PERMS`. Domain-error
   mapping:
   - `POST /admin/contracts/`
     (name:
     `admin-contract-create`).
     Cross-tenant deal → 404;
     unknown contract_type → 400.
   - `PATCH /admin/contracts/<pk>/`
     (name:
     `admin-contract-update`).
     `action` field: `sign` or
     `void`. Sign after void →
     409 Conflict.
   - `POST /admin/back-end-products/`
     (name:
     `admin-back-end-product-create`).
     Cross-tenant contract → 404;
     unknown product_type → 400.
   - `POST /admin/funding/`
     (name:
     `admin-funding-create`).
     Cross-tenant contract → 404;
     duplicate Funding → 409
     Conflict.
   - `PATCH /admin/funding/<pk>/`
     (name:
     `admin-funding-update`).
     `action=mark_funded` +
     `funding_amount` required.
     M10.6 will add
     `action=mark_chargedback`.

**42 focused tests in one file:**

- **Model** (11 tests): field
  defaults + all vocab values +
  cross-tenant clean +
  CASCADE / OneToOne + tenancy
  carriers (three separate
  assertions).
- **Service** (18 tests):
  Contract (record happy + cross-
  tenant + unknown type + sign
  populates timestamp + sign
  preserves original + sign
  after void raises + void
  populates timestamp + tenant
  get); BEPA (record VSC + cross-
  tenant + unknown type + list);
  Funding (record + cross-tenant
  + duplicate raises + mark_funded
  populates + tenant get).
- **Endpoint** (13 tests):
  Contract (create 201 + cross-
  tenant 404 + PATCH sign 200 +
  PATCH void 200 + PATCH sign-
  after-void 409); BEPA (create
  201 + cross-tenant 404);
  Funding (create 201 + duplicate
  409 + PATCH mark_funded 200 +
  unknown pk 404).

**Test baseline:** `3,621 → 3,663
pass, 1 skipped, 0 fail`. (Planning
§7 M10.5 projected ~25 tests;
shipped 42 — same overshoot
pattern as M10.1-M10.4. Larger
absolute test count reflects the
three-entity increment scope.)

## Explicit non-goals for M10.5 (deferred to M10.6+)

- ❌ `Chargeback` entity + per-
  product chargeback attribution
  (M10.6). BEPA already has the
  per-product-row schema shape
  M10.6 will need.
- ❌ `mark_chargedback` funding
  transition (M10.6). Vocabulary
  is shipped in
  `FUNDING_STATE_CHOICES` at
  M10.5; only the transition
  verb is deferred.
- ❌ `BackEndProductAgreement.cancelled_at`
  + `cancellation_amount` fields
  (M10.6). Add additively via
  migration when Chargeback
  entity lands.
- ❌ `net_realized` verb on Sale
  (M10.6). Additive alongside
  M9.1 `gross_realized` per
  §5.c Option B (SESSION_106).
- ❌ `ComplianceRecord` +
  operator UI (M10.7).
- ❌ Contract state-transition
  constraints beyond
  sign-after-void refusal. Any
  transition rules land at M10.7
  compliance if evidence
  surfaces.
- ❌ Reg Z field validation /
  recomputation. Platform
  memorializes what's on the
  signed paper — it does not
  recompute. Cross-field
  consistency lands at M10.7
  if evidence surfaces.
- ❌ Document / e-signature
  storage plumbing (M10.7).

## Reality check

- **Backend baseline:** `3,663 pass,
  1 skipped, 0 fail` (was `3,621`
  at SESSION_109 close).
- **Migrations:** `0001`–`0029`
  (added `0029_contract_funding`
  — three CreateModel operations).
- **Tenancy carriers:** 29 → 32
  (added `Contract` +
  `BackEndProductAgreement` +
  `Funding`).
- **DRF admin surface:** 54 → 59
  (added five M10.5 endpoints).
- **Frontend baseline:** unchanged
  (34 pass); no frontend at M10.5.
- **`git status`:** clean pending
  the M10.5 commit.
- **Django check:** clean (0
  issues).
- **`makemigrations --check
  --dry-run`:** "No changes
  detected."

## What SESSION_111 (M10.6) opens with

Per `MILESTONE_10_PLANNING.md` §7
M10.6 + §5.c (SESSION_106):
**Chargeback entity + net_realized
verb + BackEndProductAgreement
cancellation fields.** §5.c Option
B already ratified at SESSION_106
(additive `net_realized` verb; no
M9 schema change on
`Sale.gross_realized`).

Design questions likely to surface
at session open:

- **Chargeback attach point.** FK
  to `Contract` (deal-level
  chargeback per FINANCE §5.7
  FPD / early payoff) or to
  `BackEndProductAgreement`
  (per-product chargeback per
  FINANCE §5.7 VSC / GAP
  cancellation)? Or nullable
  FKs to both (mirrors M10.1
  §5.a Option C pattern —
  chargeback attaches to
  whichever entity generated
  the event)?
- **Chargeback type vocabulary.**
  Fixed set from FINANCE §5.7
  (`first_payment_default` /
  `early_payoff` /
  `product_cancellation` /
  `repossession` /
  `deal_unwind`)?
- **BackEndProductAgreement
  cancellation-fields additive
  extension.** Add
  `cancelled_at` +
  `cancellation_amount` to
  BEPA via migration `0030`
  (same additive-extension
  pattern as M10.2's income
  columns on M10.1 CA).
- **`net_realized` verb shape.**
  Extend `services/analytics/`
  (M8) or add to
  `services/f_and_i/computation.py`
  (new module)? Or land it as
  a Sale-model method?
- **Chargeback timestamp fields.**
  `chargeback_date` (business
  date) + `recorded_at` (row
  insert time)? Add
  `recorded_by` User FK for
  audit trail (mirrors M10.4
  `documented_by` pattern)?

Recommended step sequence for SESSION_111:

1. Push-authorization check for
   M10.1-M10.5 commits (five
   pending push per M9-close
   convention).
2. Confirm M10.6 §5-equivalent
   decisions.
3. Read first:
   - `MILESTONE_10_PLANNING.md`
     §1.7 + §5.c + §7 M10.6.
   - `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`
     (this file).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §5.7 chargebacks + §4.3
     VSC cancellation.
   - `backend/dealer_ai/models.py::Contract`
     + `::BackEndProductAgreement`
     + `::Funding` (M10.5
     substrates).
   - `backend/dealer_ai/services/f_and_i/contract.py`
     + `.../funding.py` (patterns
     to mirror).
4. Verify starting state:
   `python3 manage.py test dealer_ai`
   → `3,663 pass, 1 skipped, 0
   fail`.
5. Draft: `Chargeback` model +
   migration `0030` (with BEPA
   cancellation fields), tenancy
   carrier 32 → 33,
   `services/f_and_i/chargeback.py`
   with verbs + `net_realized`,
   endpoints, ~20 focused tests.
6. Full-suite verification.
   Target 3,663 → ~3,683.
7. Ship handoff
   `docs/handoffs/SESSION_111_m10_inc6_chargeback.md`.
8. Overwrite
   `00-START-NEXT-SESSION.md` with
   M10.7 priority.

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention.
Message:

```
Milestone 10 · Increment 5 — Contract + BackEndProductAgreement + Funding entities (SESSION_110)

M10.5 ships the contract-signing → funding substrate for the F&I
workflow:

- New Contract model + migration 0029. Mandatory FK to
  DealStructure (CASCADE). Three-value state machine (unsigned
  default → signed → voided). Reg Z disclosure fields per FINANCE
  §6.1. Sign after void refused (409) — per FINANCE §5.8 unwind
  pattern.
- New BackEndProductAgreement model. FK to Contract (CASCADE).
  Fixed 6-value product_type vocab per FINANCE §4.3-§4.5. Optional
  structural fields (term_months / mileage_limit / deductible)
  per product type. Cancellation fields deferred to M10.6.
- New Funding model. OneToOne to Contract (CASCADE). State
  machine (pending_funding default → funded → chargedback wired
  at M10.6). funding_amount populated on mark_funded transition.
- Tenancy carrier extensions 29 → 32.
- New services/f_and_i/contract.py + funding.py — nine verbs
  total. Two-verb transition pattern (sign_contract /
  void_contract, record_funding / mark_funded) rather than
  generic state updater — auto-populated timestamps are
  business facts, not side effects.
- Five new endpoints — all reuse M10.1's
  IsFinanceManagerOrOwnerAtActiveDealership. POST contract +
  PATCH sign/void (409 sign-after-void); POST BEPA; POST
  funding (409 duplicate); PATCH funding mark_funded.
- 42 focused tests. Baseline 3,621 → 3,663 pass.

Five §1.5+§1.6 decisions resolved at session open (all as-
recommended): §1.5.a Option B (separate BEPA entity for M10.6
chargeback attribution), §1.6.a Option C (single Funding, no
persisted Packet), §1.5.b Option A (three-state contract),
§1.5.c Option A (FK to DealStructure only), §1.5.d Option A
(fixed product_type vocab).
```

## Deferred / observations for M10.6+

- `services/f_and_i/` now has five
  submodules
  (`credit_application.py`,
  `deal_structure.py`, `lender.py`,
  `stipulation.py`, `contract.py`,
  `funding.py`). M10.6-M10.7 will
  add `chargeback.py`,
  `compliance.py`.
- The two-verb transition pattern
  (`sign_contract` vs
  `void_contract`, `record_funding`
  vs `mark_funded`) is worth
  preserving for M10.6
  Chargeback (`record_chargeback`
  as a distinct action verb rather
  than a generic state-mutator on
  Funding). The M10.4 stipulation
  `update_stipulation_state`
  generic pattern is fine when
  transitions are semantically
  equivalent; the M10.5 pattern
  is better when they're
  semantically distinct
  (signing ≠ voiding; recording
  funding ≠ marking funded).
- BEPA's cancellation fields
  (`cancelled_at`,
  `cancellation_amount`) will land
  additively in M10.6 migration
  `0030`. The additive-extension
  pattern used in M10.2 for M10.1
  CA income fields is exactly the
  right shape.
- Funding's `chargedback` state
  is in the vocabulary today but
  no verb transitions to it —
  M10.6's Chargeback creation
  verb should also transition
  the associated Funding to
  `chargedback` atomically.
- The two-service-module split
  (contract.py + funding.py) is
  the right shape given the
  distinct workflows. M10.6
  chargeback.py will need to
  touch both (chargeback affects
  funding state + attributes to
  BEPA row) — cross-module
  coordination via the facade
  `__init__.py` re-exports.
- Nothing in M10.5 required
  amending M1-M9 or M10.1-M10.4
  behavior. Consumption is FK-
  only.
