---
title: "SESSION_107 handoff — Milestone 10 · Increment 2 (M10.2 — DealStructure entity + ratio computation)"
status: historical
type: handoff
date: 2026-08-02
session: 107
milestone: 10
milestone_status: in_progress
increment: 2
increment_status: shipped
commit: b7c9bf3
---

# SESSION_107 — Milestone 10 · Increment 2 (M10.2 — DealStructure entity + LTV/PTI/DTI ratio computation)

## What shipped

`DealStructure` entity substrate + M10.2
extension of M10.1's `CreditApplication`
(additive `gross_monthly_income` +
`existing_monthly_debt` nullable Decimal
columns) + `services/f_and_i/deal_structure.py`
module with three pure ratio verbs (LTV /
PTI / DTI) + write path with ratio-at-
write denormalization + recompute helper
+ tenant-scoped read verb + second M10
DRF endpoint (`POST /admin/deal-structures/`)
+ tenancy carrier extension (25 → 26) +
55 focused tests. Two design questions
that the planning-time §1.2 memo did NOT
resolve surfaced at session open and were
confirmed with the user (both as-
recommended); `MILESTONE_10_PLANNING.md`
§0.a amended.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§1.2.a — income + existing-debt
   capture for PTI / DTI ratios:**
   Option A — extend M10.1's
   `CreditApplication` with two
   nullable Decimal columns
   (`gross_monthly_income`,
   `existing_monthly_debt`). Additive-
   extension pattern (M8 §6 lesson 11)
   preserves M10.1 business logic; old
   rows carry NULL and PTI / DTI ratio
   verbs return `None` for them.
   Migration `0026` combines the two
   new CreditApplication columns + the
   new `DealStructure` model in one
   atomic delivery.
2. **§1.9.a — endpoint URL shape:**
   Option A — flat
   `/admin/deal-structures/` matching
   M10.1's `/admin/credit-applications/`
   pattern and the platform-wide M1-M9
   flat resource-naming convention.
   Deferred: if `/admin/f-and-i/`
   grouping matters later, rename-
   with-redirect at M10.7.

**M10.2 deliverables (seven):**

1. **New `DealStructure` model +
   migration `0026`**
   (`0026_deal_structure_entity`).
   Fields per §1.2: FK to
   `CreditApplication` CASCADE
   (mandatory), FK to `Vehicle`
   CASCADE (mandatory), `sale_price` /
   `down_payment` / `trade_allowance` /
   `trade_payoff` / `taxes` / `fees`
   Decimal(10,2), `amount_financed`
   Decimal(10,2), `apr` Decimal(6,4)
   in **percent units** (matches
   `services.payment_engine`
   convention — `DEFAULT_APR = 7.49  # %`),
   `term_months` PositiveIntegerField,
   `monthly_payment` Decimal(10,2),
   `back_end_products` JSONField
   default list (vocabulary partitioning
   deferred to M10.5 Contract), and
   three denormalized ratio outputs
   (`ltv_pct` / `pti_pct` / `dti_pct`)
   Decimal(6,2) nullable. Ordering
   `-created_at`. Model-layer `clean()`
   cross-tenant guards on both
   `credit_application` and `vehicle`
   FKs.
2. **Additive CreditApplication
   extension (§1.2.a Option A).**
   `gross_monthly_income` +
   `existing_monthly_debt` nullable
   Decimal(10,2). Shipped in same
   migration `0026`. M10.1-era rows
   land NULL and the ratio verbs
   return `None` — zero business-
   logic change to M10.1 code paths.
3. **Tenancy-carrier extension 25 → 26.**
   `_TENANT_CARRIER_MODEL_NAMES`
   extended with `"DealStructure"`.
   M10.2 service writes `dealership`
   explicitly on every row; autofill
   signal is the safety net for
   callers that bypass the service.
4. **New `services/f_and_i/deal_structure.py`
   module** — six verbs:
   - `loan_to_value(deal)` — pure.
     `(amount_financed / sale_price)
     × 100`, quantized to 2 decimal
     places, ROUND_HALF_UP. Returns
     `None` when `sale_price ≤ 0`.
   - `payment_to_income(deal)` — pure.
     `(monthly_payment /
     gross_monthly_income) × 100`.
     Returns `None` when income is
     NULL or ≤ 0.
   - `debt_to_income(deal)` — pure.
     `((existing_monthly_debt +
     monthly_payment) /
     gross_monthly_income) × 100` per
     FINANCE §3.6 (numerator includes
     the proposed new loan payment).
     Returns `None` when income NULL,
     income ≤ 0, or existing_debt NULL.
   - `record_deal_structure(...)` —
     transactional. Refuses cross-
     tenant CA / vehicle
     (`CrossTenantDealStructureError`)
     and non-positive sale_price /
     amount_financed / monthly_payment
     / term / negative APR
     (`ValueError`). Computes all
     three ratios pre-save so the
     denormalized columns land in the
     same INSERT.
   - `get_deal_structure(pk,
     dealership)` — pure read. Tenant-
     scoped. Returns `None` for
     unknown / cross-tenant pk. Never
     raises, never leaks.
   - `recompute_ratios(deal)` —
     refreshes the three ratio columns
     after operator edits (either to
     the deal or the parent CA's
     income/debt). Persists via
     targeted
     `.save(update_fields=...)`.
5. **`services/f_and_i/__init__.py`
   facade** — extended to re-export
   the six new M10.2 verbs +
   `CrossTenantDealStructureError`
   alongside the M10.1 exports.
   Existing M10.1 imports unchanged.
6. **Second M10 endpoint** — `POST
   /api/dealer-ai/admin/deal-structures/`
   (URL name
   `admin-deal-structure-create`) in
   `views_f_and_i.py`. Role-gated on
   the same `_M101_PERMS` composition
   (`IsAuthenticated &
   IsFinanceManagerOrOwnerAtActiveDealership`)
   introduced at M10.1 — the
   permission class is reusable across
   every M10 admin endpoint without
   modification. Domain-error → HTTP
   mapping mirrors M9.1 / M10.1:
   `CrossTenantDealStructureError` →
   404 (never leak cross-tenant
   existence); `ValueError` → 400.
   Request body:
   `credit_application_id` +
   `vehicle_stock` + the deal-desk
   math fields; optional
   `back_end_products`. Response:
   `{"deal_structure": {...}}` with
   stringified Decimals and null-
   serialization for NULL ratios.
7. **URL wired at
   `/api/dealer-ai/admin/deal-structures/`**
   — flat pattern per §1.9.a Option A.
   Mounted immediately after the M10.1
   credit-application URL to keep the
   M10 admin section together.

**55 focused tests across three files:**

- **`test_m102_deal_structure_model.py`
  (16 tests)** — field defaults +
  Decimal precision, JSONField
  round-trip, ordering, `clean()`
  cross-tenant guards, CASCADE on
  parent delete (both parents;
  CreditApplication delete-cascade
  requires expiring retention first
  per M10.1 §5.e), tenant-carrier
  list membership + count (25 → 26),
  additive M10.1 columns default
  NULL + accept Decimals.
- **`test_m102_deal_structure_service.py`
  (25 tests)** — LTV (at par / below /
  over-par negative-equity / zero
  sale_price / quantization half-up),
  PTI (standard / income NULL /
  income zero / existing-debt
  irrelevant to PTI), DTI (standard /
  income NULL / debt NULL / this-
  deal-payment in numerator / zero
  case), `record_deal_structure`
  (all-three-ratios with income /
  LTV-only without income / optional
  fields persist / cross-tenant CA /
  cross-tenant vehicle / non-positive
  sale_price / zero term / negative
  APR), `get_deal_structure` (tenant
  hit / unknown pk None / cross-
  tenant pk None), `recompute_ratios`
  (initial NULL / recompute after
  income capture populates PTI /
  recompute after both captured
  populates DTI).
- **`test_m102_deal_structure_endpoint.py`
  (14 tests)** — auth (401/403 anon /
  advisor 403 / sales_manager 403 /
  f_and_i_manager 201 / dealer_owner
  201), happy paths (all-ratios /
  null-serialized-ratios / back_end_products
  round-trip), 404 on unknown CA /
  unknown vehicle, 400 on missing
  required field / zero sale_price,
  cross-tenant CA / vehicle → 404 +
  no persistence.

**Test baseline:** `3,478 → 3,533 pass,
1 skipped, 0 fail`. (Planning §7 M10.2
projected ~30 tests; shipped 55 —
overshoot covers the ratio matrix
completely including quantization
edges and the CreditApplication-
additive-columns coverage.)

## Explicit non-goals for M10.2 (deferred to M10.3+)

- ❌ `LenderProgram` + `LenderSubmission`
  entities (M10.3).
- ❌ `Stipulation` model + lifecycle
  verbs (M10.4).
- ❌ `Contract` + `FundingPacket` +
  `FundingStatus` entities (M10.5).
- ❌ `Chargeback` + `net_realized` verb
  (M10.6).
- ❌ `ComplianceRecord` entity +
  `/dealer-ai-f-and-i/` operator UI
  (M10.7).
- ❌ Validation of operator-entered
  `monthly_payment` against
  `services.payment_engine`
  computation — the operator enters
  what the lender's approval terms
  say; the payment engine is for
  what-if scenarios pre-submission.
  Storing as-entered is correct.
- ❌ Bureau-response integration —
  `existing_monthly_debt` is
  operator-entered from the bureau
  report at M10.2. Direct bureau-
  portal integration is deferred
  beyond M10.
- ❌ Frontend UI (M10.7).

## Reality check

- **Backend baseline:** `3,533 pass, 1
  skipped, 0 fail` (was `3,478 pass, 1
  skipped, 0 fail` at SESSION_106 close).
- **Migrations:** `0001`–`0026` (added
  `0026_deal_structure_entity` — three
  operations: two AddField on
  CreditApplication + one CreateModel
  for DealStructure).
- **Tenancy carriers:** 25 → 26 (added
  `DealStructure`).
- **DRF admin surface:** 48 → 49 (added
  `POST /admin/deal-structures/`).
- **Frontend baseline:** unchanged (34
  pass); no frontend at M10.2.
- **`git status`:** clean pending the
  M10.2 commit.
- **`git log --oneline -3` (post-M10.2
  commit):** `Milestone 10 · Increment 2
  — DealStructure entity …
  (SESSION_107)` on top.
- **Django check:** clean (0 issues).
- **`makemigrations --check --dry-run`:**
  "No changes detected."

## What SESSION_108 (M10.3) opens with

Per `MILESTONE_10_PLANNING.md` §7 M10.3:
**LenderProgram + LenderSubmission
entities.** §5.d Option C already
confirmed at SESSION_106 (leave both:
structured `LenderProgram` catalog
additive alongside existing free-text
`DealerOnboardingProfile.subprime_lenders`
field).

Recommended step sequence for SESSION_108:

1. Push-authorization check for the
   M10.2 commit.
2. Confirm any M10.3 §5-equivalent
   decisions (attach shape for
   `LenderSubmission` — DealStructure
   or CreditApplication?; approval /
   counter / declined vocabulary
   partitioning; per-dealership
   catalog scope for `LenderProgram`).
3. Read first:
   - `MILESTONE_10_PLANNING.md` §1.3 +
     §7 M10.3.
   - `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
     (this file).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §4 (lender submission workflow).
   - `backend/dealer_ai/models.py::DealStructure`
     + `::CreditApplication` (M10.1-
     M10.2 substrates).
   - `backend/dealer_ai/services/f_and_i/deal_structure.py`
     (pattern to mirror for
     `lender.py` verbs).
4. Verify starting state:
   `python3 manage.py test dealer_ai`
   → `3,533 pass, 1 skipped, 0 fail`.
5. Draft: `LenderProgram` + `LenderSubmission`
   models + migration `0027`, tenancy
   carrier extensions 26 → 28 (two new
   carriers), `services/f_and_i/lender.py`
   with catalog + submission verbs,
   endpoints, ~25 focused tests.
6. Full-suite verification. Target
   3,533 → ~3,558.
7. Ship handoff
   `docs/handoffs/SESSION_108_m10_inc3_lender.md`.
8. Overwrite `00-START-NEXT-SESSION.md`
   with M10.4 priority.

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention —
per-increment push authorization
requested at session open. Message:

```
Milestone 10 · Increment 2 — DealStructure entity + LTV/PTI/DTI ratio computation (SESSION_107)

M10.2 ships the deal-desk substrate for the F&I workflow:

- New DealStructure model + migration 0026. FKs to
  CreditApplication + Vehicle (both CASCADE, both mandatory).
  Fields per §1.2: sale price / down / trade / taxes / fees /
  amount_financed / apr (percent units matching payment_engine
  convention) / term / monthly_payment / back_end_products
  (JSONField) + three denormalized ratio outputs (ltv_pct /
  pti_pct / dti_pct, all nullable).
- Additive CreditApplication extension per §1.2.a Option A —
  two nullable Decimal columns (gross_monthly_income,
  existing_monthly_debt) bundled into migration 0026. Zero M10.1
  business-logic change; old rows survive NULL.
- Tenancy carrier extension 25 → 26.
- New services/f_and_i/deal_structure.py — six verbs. Three
  pure ratio verbs (LTV / PTI / DTI) that return None when
  inputs are NULL or non-positive; transactional
  record_deal_structure that computes ratios pre-save;
  tenant-scoped get_deal_structure; recompute_ratios for
  after-edit refresh.
- Second M10 endpoint — POST /admin/deal-structures/ (flat URL
  per §1.9.a Option A). Reuses M10.1's
  IsFinanceManagerOrOwnerAtActiveDealership permission class.
- 55 focused tests. Baseline 3,478 → 3,533 pass.

Two design questions resolved at session open (both as-
recommended): §1.2.a Option A (income + debt on CA), §1.9.a
Option A (flat URL pattern).
```

## Deferred / observations for M10.3+

- The `services/f_and_i/` package now
  has two modules
  (`credit_application.py`,
  `deal_structure.py`). Same
  facade-and-sibling-modules shape as
  `services/analytics/` from M8.
  M10.3-M10.7 will add
  `lender.py`, `stipulation.py`,
  `contract.py`, `funding.py`,
  `chargeback.py`.
- Ratio storage uses `Decimal(6,2)` —
  supports up to `9999.99%` LTV /
  PTI / DTI. Real-world subprime
  over-financed deals hit 140% LTV;
  future asset-recovery scenarios
  could push higher. If any dashboard
  filter ever needs sub-hundredth
  precision, the M10.7 compliance
  layer can add a schema extension.
- `recompute_ratios` is currently not
  called anywhere in the write path.
  Operator-driven flows that edit the
  parent CA's income (e.g. an
  updated bureau pull) or the deal-
  structure's monthly_payment will
  need to call it explicitly. M10.3+
  endpoints for updating those
  fields should compose with the
  recompute verb.
- `back_end_products` remains free-
  form JSON at M10.2. The M10.5
  Contract entity is the natural
  place to lock the vocabulary (VSC /
  GAP / paint-and-fabric / etc.) as
  operator evidence surfaces need.
- Nothing in M10.2 required amending
  M1-M9 behavior. The CreditApplication
  extension is additive (nullable
  columns, no default value, no data
  backfill).
