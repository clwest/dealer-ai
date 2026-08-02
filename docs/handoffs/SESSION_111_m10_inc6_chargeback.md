---
title: "SESSION_111 handoff — Milestone 10 · Increment 6 (M10.6 — Chargeback + net_realized)"
status: historical
type: handoff
date: 2026-08-02
session: 111
milestone: 10
milestone_status: in_progress
increment: 6
increment_status: shipped
commit: TBD
---

# SESSION_111 — Milestone 10 · Increment 6 (M10.6 — Chargeback + net_realized)

## What shipped

`Chargeback` entity + additive
`BackEndProductAgreement` cancellation-
field extension + new
`services/f_and_i/chargeback.py` module
with three verbs (record + net_realized
+ get) + one new DRF endpoint
(`POST /admin/chargebacks/`) + tenancy
carrier extension (32 → 33) + 36
focused tests. Six design questions
surfaced at session open and were
confirmed with the user (all as-
recommended); `MILESTONE_10_PLANNING.md`
§0.a amended.

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§1.7.a — Chargeback attach
   point: Option A.** Nullable FKs
   to both `Contract` and
   `BackEndProductAgreement`. At
   least one required via clean().
   Mirrors M10.1 §5.a Option C
   precedent. Product-cancellation
   chargebacks conceptually attach
   to both — the contract's funding
   is adjusted AND the specific
   BEPA's commission is pro-rated.
2. **§1.7.b — Chargeback type
   vocabulary: Option B.** 5+1
   fixed set: FINANCE §5.7's five
   triggers plus `other` fallback.
   Consistent with prior vocab
   decisions across M10.
3. **§1.7.c — BEPA cancellation-
   fields additive extension:
   Option A.** Add `cancelled_at`
   DateTime nullable +
   `cancellation_amount`
   Decimal(10,2) nullable to
   `BackEndProductAgreement` via
   migration `0030`. Same
   additive-extension pattern used
   at M10.2 for M10.1 CA income
   fields. Populated by the
   chargeback verb when
   `chargeback_type=product_cancellation`
   and `bepa` FK set.
4. **§1.7.d — `net_realized` verb
   location: Option A.**
   `services/f_and_i/chargeback.py`.
   Colocates with chargeback
   aggregation logic. Avoids
   cross-service imports.
5. **§1.7.e — Chargeback
   timestamps + audit trail:
   Option A.** Three fields:
   `chargeback_date` (operator-
   provided business date),
   `created_at` (auto row insert),
   `recorded_by` FK to
   `settings.AUTH_USER_MODEL`
   nullable SET_NULL. Sourced
   from `request.user` at the
   endpoint per M10.4 server-
   side audit-trail pattern.
6. **§1.7.f — Automatic Funding
   state transition on chargeback:
   Option A.** Yes for deal-level
   chargebacks (four types:
   `first_payment_default` /
   `early_payoff` /
   `repossession` /
   `deal_unwind`) — auto-
   transition Funding to
   `chargedback` atomically. No
   for `product_cancellation`
   (product cancel reduces
   commission but leaves the deal
   funded). No for `other`
   (safer default). Optional
   `skip_funding_transition=True`
   service kwarg for edge cases.

**M10.6 deliverables (five):**

1. **New `Chargeback` model +
   additive BEPA extension +
   migration `0030`.** Migration
   ships three operations: two
   `AddField` on
   `BackEndProductAgreement`
   (`cancelled_at` +
   `cancellation_amount`, both
   nullable) + one `CreateModel`
   for `Chargeback`. Chargeback
   fields: nullable FKs to
   Contract + BEPA both CASCADE
   (clean() requires at least one),
   `chargeback_type` from fixed
   6-value vocab, `chargeback_date`
   operator-provided, `chargeback_amount`
   Decimal(10,2) positive,
   `recorded_by` FK to User
   SET_NULL, `notes`. Ordering
   `(-chargeback_date, -created_at)`.
2. **Tenancy carrier extension
   32 → 33.**
3. **New `services/f_and_i/chargeback.py`
   module** — three verbs:
   - `record_chargeback(...)` —
     transactional with two atomic
     side effects. Deal-level
     types auto-transition
     Funding to `chargedback`;
     product_cancellation +
     bepa auto-populate BEPA
     cancellation fields.
     `skip_funding_transition=True`
     kwarg bypasses the Funding
     side effect for edge cases.
   - `net_realized(sale)` — pure
     aggregate per §5.c Option B.
     Returns `sale.gross_realized
     - sum(chargebacks)`.
     Attribution via Contract →
     DealStructure → Vehicle;
     also picks up BEPA-only
     chargebacks whose parent
     Contract targets the same
     Vehicle. Q-based union with
     pk-set dedup prevents
     double-counting when both
     FKs point to matching
     parents.
   - `get_chargeback(pk,
     dealership)` — pure read,
     tenant-scoped.
4. **`services/f_and_i/__init__.py`
   facade** — extended to re-
   export the three new M10.6
   verbs + `CrossTenantChargebackError`
   alongside M10.1-M10.5 exports.
5. **One new endpoint** —
   `POST /api/dealer-ai/admin/chargebacks/`
   (name:
   `admin-chargeback-create`).
   Role-gated on the same
   `_M101_PERMS` composition.
   `recorded_by` sourced from
   `request.user` server-side.
   `skip_funding_transition` in
   the request body when needed.
   Domain-error mapping:
   `CrossTenantChargebackError` →
   404; `ValueError` (missing
   both parents, unknown type)
   → 400.

**36 focused tests in one file:**

- **Model** (9 tests): all six
  types accepted, clean guards
  (both null / contract only /
  bepa only / cross-tenant
  contract / cross-tenant bepa),
  `DEAL_LEVEL_CHARGEBACK_TYPES`
  sanity, BEPA extension defaults
  to NULL, tenancy carrier
  membership.
- **Service** (12 tests):
  `record_chargeback` — neither
  parent + cross-tenant contract
  + cross-tenant bepa + unknown
  type + FPD auto-transitions
  Funding + deal_unwind
  transitions + product_cancellation
  doesn't transition + `other`
  doesn't transition +
  `skip_funding_transition` kwarg
  suppresses + product_cancellation
  populates BEPA + BEPA-only
  chargeback populates BEPA +
  FPD without BEPA doesn't touch
  BEPA.
- **`net_realized`** (6 tests):
  baseline no chargebacks +
  single deal chargeback
  subtracts + product cancel
  subtracts (once even with
  both FKs) + multiple sums +
  BEPA-only still attributed +
  cross-tenant excluded.
- **`get_chargeback`** (3 tests):
  tenant hit + cross-tenant None
  + unknown None.
- **Endpoint** (6 tests): create
  deal 201 + Funding transition
  visible + missing both parents
  400 + cross-tenant contract 404
  + unknown type 400 +
  product_cancellation populates
  BEPA leaves Funding funded +
  skip kwarg leaves Funding
  funded.

**Test baseline:** `3,663 → 3,699
pass, 1 skipped, 0 fail`. (Planning
§7 M10.6 projected ~20 tests;
shipped 36 — same overshoot pattern
as M10.1-M10.5.)

## Explicit non-goals for M10.6 (deferred to M10.7)

- ❌ `ComplianceRecord` entity +
  operator UI (M10.7).
- ❌ Frontend UI (M10.7).
- ❌ Manual PATCH endpoint to
  update a Chargeback after
  creation. Chargebacks are
  audit-trail rows — record
  errors are corrected by
  recording a corrective
  chargeback, not by editing
  the original.
- ❌ Reversal-of-commission
  posting to payroll (out of
  scope; that's a payroll
  workflow).
- ❌ Lender chargeback-portal
  integration (deferred beyond
  M10).
- ❌ Modification of
  `Sale.gross_realized` semantics
  or column (§5.c Option B —
  additive verb only).
- ❌ Auto-refund of
  down_payment / trade equity
  on deal_unwind (out of scope
  at M10.6; those cash flows
  land at accounting-integration
  time, not F&I).

## Reality check

- **Backend baseline:** `3,699
  pass, 1 skipped, 0 fail` (was
  `3,663` at SESSION_110 close).
- **Migrations:** `0001`–`0030`
  (added
  `0030_chargeback_and_bepa_cancellation`
  — three operations: two
  AddField on BEPA + one
  CreateModel).
- **Tenancy carriers:** 32 → 33
  (added `Chargeback`).
- **DRF admin surface:** 59 → 60
  (added POST /admin/chargebacks/).
- **Frontend baseline:** unchanged
  (34 pass); no frontend at M10.6.
- **`git status`:** clean pending
  the M10.6 commit.
- **Django check:** clean (0
  issues).
- **`makemigrations --check
  --dry-run`:** "No changes
  detected."

## What SESSION_112 (M10.7) opens with

Per `MILESTONE_10_PLANNING.md` §7
M10.7: **ComplianceRecord entity +
`/dealer-ai-f-and-i/` operator UI.**
This is the M10 closer — the
biggest single-session scope of
the milestone (compliance model +
back-end wiring + a full new
frontend surface).

Design questions likely to surface
at session open:

- **ComplianceRecord attach shape.**
  One-per-DealStructure (deal-
  level compliance) vs one-per-
  Contract (contract-level) vs
  one-per-Sale?
- **Per-concern vs single-entity
  compliance model** (planning
  §1.8 defers this — decide now).
  Options: single `ComplianceRecord`
  with a JSON blob of concerns,
  or per-concern rows
  (`RetentionRecord` /
  `PrivacyNoticeRecord` /
  `AdverseActionRecord` / etc.).
- **Photo / document storage
  plumbing.** M10.4 §1.4.d and
  M10.5 §1.6.a resolutions
  deferred storage plumbing to
  M10.7. Ship Cloudinary/S3
  wiring + presigned URLs +
  MIME validation now? Or defer
  again as beyond-M10 scope?
- **Operator UI scope.** Full
  seven-panel workflow (credit
  app intake → deal desking →
  lender submission → stipulation
  chase → contract signing →
  funding → chargeback
  reconciliation)? Or narrower
  MVP (just the deal-jacket
  browser + stip-chase board)?
- **Frontend test surface.** ~25
  Vitest tests per planning
  §7 M10.7. Extend the M9.5
  Operator UI framework, or
  ship as a distinct route
  family?
- **M10.7 closeout ordering.**
  Standard M10 close (planning
  §7 M10.8 = documentation
  closeout, retrospective,
  M11 planning skeleton). Would
  M10.7 combine implementation
  + closeout, or split into
  two sessions?

Recommended step sequence for SESSION_112:

1. Push-authorization check for
   M10.1-M10.6 commits (six
   pending push per M9-close
   convention).
2. Confirm M10.7 §5-equivalent
   decisions (5-6 questions
   expected, largest surface of
   the milestone).
3. Read first:
   - `MILESTONE_10_PLANNING.md`
     §1.8 + §7 M10.7 + §7 M10.8.
   - `docs/handoffs/SESSION_111_m10_inc6_chargeback.md`
     (this file).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §6 compliance sections
     (§6.1-§6.9).
   - `backend/dealer_ai/models.py::Chargeback`
     + M10.1-M10.5 substrates.
   - `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
     (M9.5 operator UI pattern
     to mirror).
4. Verify starting state:
   `python3 manage.py test dealer_ai`
   → `3,699 pass, 1 skipped, 0
   fail`; `cd frontend && npm
   test` → `34 pass`.
5. Draft the largest-scope M10
   session (implementation +
   possibly the M10.8 close).
6. Full-suite verification.
   Target 3,699 → ~3,720 backend
   + 34 → ~60 frontend.
7. Ship handoff.
8. Overwrite start-here with
   M10.8 (if split) or M11
   (if bundled).

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention.
Message:

```
Milestone 10 · Increment 6 — Chargeback + net_realized (SESSION_111)

M10.6 ships the chargeback substrate + net_realized aggregate for
the F&I workflow:

- New Chargeback model + migration 0030 (three operations: two
  BEPA AddField for cancelled_at + cancellation_amount, one
  Chargeback CreateModel). Nullable FKs to both Contract (CASCADE)
  and BackEndProductAgreement (CASCADE) per §1.7.a Option A;
  clean() requires at least one. Fixed 5+1 chargeback_type vocab
  per §1.7.b Option B. Audit-trail via recorded_by FK to User
  (SET_NULL) sourced from request.user server-side.
- Additive BEPA extension per §1.7.c Option A — cancelled_at +
  cancellation_amount nullable columns bundled into migration
  0030. Same additive-extension pattern used at M10.2 for M10.1
  CA income fields.
- Tenancy carrier extension 32 → 33.
- New services/f_and_i/chargeback.py — three verbs.
  record_chargeback (transactional with two atomic side effects:
  deal-level types auto-transition Funding to chargedback;
  product_cancellation + bepa auto-populates BEPA cancellation
  fields). net_realized(sale) additive verb per §5.c Option B (no
  M9 schema change) — attribution via Contract → DealStructure →
  Vehicle path unioned with BEPA-only chargebacks; distinct pk
  set prevents double-counting. get_chargeback tenant-scoped
  read.
- One new endpoint — POST /admin/chargebacks/ (409-less; all
  domain errors → 404 or 400). recorded_by sourced from
  request.user per M10.4 audit-trail pattern.
- 36 focused tests. Baseline 3,663 → 3,699 pass.

Six §1.7 decisions resolved at session open (all as-recommended):
§1.7.a Option A (nullable both parents), §1.7.b Option B (5+1
vocab), §1.7.c Option A (additive BEPA extension), §1.7.d Option
A (verb in f_and_i module), §1.7.e Option A (full audit-trail
timestamps + recorded_by), §1.7.f Option A (deal-level auto-
transition Funding; product_cancellation and other don't).
```

## Deferred / observations for M10.7+

- `services/f_and_i/` now has six
  submodules
  (`credit_application.py`,
  `deal_structure.py`, `lender.py`,
  `stipulation.py`, `contract.py`,
  `funding.py`, `chargeback.py`).
  M10.7 will add `compliance.py`.
- The **atomic-side-effects
  pattern** in
  `record_chargeback` (transactional
  write + Funding auto-transition
  + BEPA auto-populate all in one
  `transaction.atomic`) is a new
  shape for this project. Prior
  service verbs had at most one
  side effect (M10.5
  `sign_contract` auto-populates
  `signed_at` on the same row).
  M10.6 introduces cross-model
  side effects — the M10.7
  ComplianceRecord verbs may
  need the same pattern.
- The **skip_transition kwarg
  pattern** (`skip_funding_transition=True`)
  is worth preserving for M10.7
  compliance-record scenarios
  where operator override
  matters. Same shape as
  `notes` optional-preserve
  from M10.4 stipulation.
- The **distinct-pk-set dedup
  pattern** in `net_realized`
  (extract pks first, then
  aggregate) is a defensive
  shape for future aggregate
  verbs that union across
  Q-object filters. M9.3
  gross_profit trend verbs
  used a simpler Sum aggregation
  because they had a single FK
  path; M10.6 needed the pk-set
  path because chargebacks have
  two attribution routes.
- Nothing in M10.6 required
  amending M1-M9 or M10.1-M10.5
  business logic. Consumption
  is FK-only + additive BEPA
  extension.
