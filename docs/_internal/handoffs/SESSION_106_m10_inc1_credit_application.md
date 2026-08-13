---
title: "SESSION_106 handoff — Milestone 10 · Increment 1 (M10.1 — CreditApplication entity + retention discipline)"
status: historical
type: handoff
date: 2026-08-02
session: 106
milestone: 10
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: 50504eb
---

# SESSION_106 — Milestone 10 · Increment 1 (M10.1 — CreditApplication entity + retention discipline)

## What shipped

`CreditApplication` entity substrate +
`services/f_and_i/` package
(`record_credit_application` write path +
`get_credit_application` tenant-scoped read
+ `compute_retention_expires_at` pure verb)
+ new `IsFinanceManagerOrOwnerAtActiveDealership`
permission class + first M10 DRF endpoint
(`POST /admin/credit-applications/`) +
tenancy carrier extension (24 → 25) + 52
focused tests. All four
`[NEEDS-DECISION-BEFORE-M10.N]` items from
`MILESTONE_10_PLANNING.md` §9 confirmed at
session open (all four as-recommended;
§5.a resolved from TBD in favor of
Option C).

**Load-bearing decisions confirmed at
session open (recorded in
`MILESTONE_10_PLANNING.md` §0.a):**

1. **§5.a — CreditApplication attach
   point:** Option C — nullable FKs to both
   `CustomerLead` and `Sale`. Credit apps
   intake at lead time (`lead` FK set,
   `sale` FK null); on close the `sale` FK
   is set (`lead` FK preserved). Prevents
   re-orphaning if the operational anchor
   moves from lead to sale.
2. **§5.b — Stipulation vocabulary
   partition:** Option A — small fixed set
   (`proof_of_income`, `proof_of_insurance`,
   `proof_of_residence`, `references`,
   `other`). Extends when operator
   evidence surfaces need.
3. **§5.c — Chargeback impact on
   `Sale.gross_realized`:** Option B —
   zero M9 schema change; a new
   `services/f_and_i/computation.py::net_realized(sale)`
   verb will sit alongside M9.1's
   `gross_realized` when M10.7 lands.
   Follows M8 §6 lesson 11 additive-
   extension pattern.
4. **§5.d — Onboarding lender migration:**
   Option C — zero data loss; the
   structured `LenderProgram` catalog
   (M10.3) is additive alongside the
   existing free-text
   `DealerOnboardingProfile.subprime_lenders`
   field; the free-text field becomes a
   notes area.

**M10.1 deliverables (seven):**

1. **New `CreditApplication` model +
   migration `0025`**
   (`0025_credit_application_entity`).
   Fields (per §5.a Option C + §5.e):
   `dealership` FK CASCADE, `lead` FK
   `CustomerLead` SET_NULL nullable, `sale`
   FK `Sale` SET_NULL nullable,
   `applicant_full_name` CharField(255),
   `applicant_ssn_last4` CharField(4)
   blank, `source_format` from
   `CREDIT_APP_FORMAT_CHOICES` (`paper` /
   `tablet` / `online_prequal`), `status`
   from `CREDIT_APP_STATUS_CHOICES`
   (`received` / `submitted` / `withdrawn`,
   default `received`), `captured_at`
   datetime (retention-clock start),
   `retention_expires_at` datetime
   (denormalized at write from
   `captured_at + CREDIT_APP_RETENTION_YEARS`),
   `notes` TextField, `created_at` /
   `updated_at`. Ordering (`-captured_at`,
   `-created_at`).
2. **Retention clock locked at the model
   layer per §5.e.**
   `CreditApplication.delete()` refuses
   when `timezone.now() <
   retention_expires_at`, raising
   `CreditApplicationRetentionActiveError`.
   No `force=True` escape hatch — if
   operators need to purge an unexpired
   record for a specific compliance
   reason (state privacy-law request),
   that surface lands as a discrete verb
   in M10.7, not here.
3. **Model-layer `clean()` invariants.**
   Three: (a) at least one of `lead` /
   `sale` set (§5.a Option C), (b) `lead`
   dealership matches, (c) `sale`
   dealership matches. Belt + suspenders
   with the service-layer
   `CrossTenantCreditApplicationError`.
4. **Tenancy carrier extension 24 → 25.**
   `_TENANT_CARRIER_MODEL_NAMES` extended
   with `"CreditApplication"`. The M10.1
   service writes `dealership` explicitly
   on every row; the autofill signal is
   the safety net for callers that
   bypass the service.
5. **New `services/f_and_i/` package** —
   `__init__.py` facade re-exporting the
   verbs +
   `credit_application.py::compute_retention_expires_at(captured_at)`
   (pure verb; uses
   `dateutil.relativedelta` so leap-year
   arithmetic is well-defined) +
   `record_credit_application(...)`
   (transactional write path; refuses
   cross-tenant parents +
   attach-shape violations +
   unknown vocabulary values) +
   `get_credit_application(pk,
   dealership=...)` (pure read verb;
   returns `None` for unknown /
   cross-tenant pk, never raises,
   never leaks).
6. **New `IsFinanceManagerOrOwnerAtActiveDealership`
   permission class** in
   `dealer_ai/permissions.py`. Composes
   with `IsAuthenticated`. Grants:
   `f_and_i_manager`, `dealer_owner`.
   Explicit non-grants (documented in
   the docstring): `sales_manager`
   (distinct compliance obligations),
   `recon_manager`, `advisor`, `porter`,
   `collections`. `collections` may
   become a grant at M10.6 chargeback
   reconciliation — deferred until
   operator evidence surfaces need.
7. **First M10 endpoint** — `POST
   /api/dealer-ai/admin/credit-applications/`
   (URL name
   `admin-credit-application-create`) in
   new `views_f_and_i.py`. Role-gated on
   `_M101_PERMS = [IsAuthenticated &
   IsFinanceManagerOrOwnerAtActiveDealership]`.
   Domain-error → HTTP mapping mirrors
   M9.1:
   `CrossTenantCreditApplicationError` →
   404 (never leak cross-tenant
   existence); `ValueError` → 400.
   Request body:
   `applicant_full_name`,
   `source_format`, at least one of
   `lead_id` / `sale_id`, optional
   `applicant_ssn_last4`, `status`,
   `captured_at`, `notes`. Response:
   `{"credit_application": {...}}` with
   ISO-formatted datetimes.

**52 focused tests across three files:**

- **`test_m101_credit_application_model.py`
  (23 tests)** — field defaults, choice
  vocabulary, ordering, cross-tenant
  clean guards, attach-shape clean guard,
  retention `.delete()` refusal + expired-
  window allow, SET_NULL behavior on both
  parents, tenant-carrier list membership,
  autofill signal on missing `dealership=`.
- **`test_m101_credit_application_service.py`
  (16 tests)** — `compute_retention_expires_at`
  (7-year math + leap-day handling +
  purity), `record_credit_application`
  (happy paths for lead-only / sale-only
  / both + explicit-captured-at path +
  rejection paths for missing parents /
  cross-tenant lead / cross-tenant sale /
  unknown source_format / unknown status),
  `get_credit_application` (tenant-scoped
  hit + unknown pk None + cross-tenant pk
  None).
- **`test_m101_credit_application_endpoint.py`
  (13 tests)** — auth matrix (401/403
  anon, 403 no-membership, 403 for every
  non-grant role, 201 for f_and_i_manager
  + dealer_owner), happy paths for lead-
  only / sale-only / explicit status,
  400 on missing parent / unknown lead /
  invalid source_format / missing name,
  cross-tenant lead / sale → 404 (never
  leak) + no persistence on the
  cross-tenant failure path.

**Test baseline:** `3,426 → 3,478 pass, 1
skipped, 0 fail`. (Planning §7 M10.1
projected ~30 tests; shipped 52 —
overshoot covers the attach-shape ×
retention × cross-tenant matrix
completely instead of sampling.)

## Explicit non-goals for M10.1 (deferred to M10.2+)

- ❌ `DealStructure` entity + LTV / PTI /
  DTI ratio math (M10.2).
- ❌ `LenderProgram` + `LenderSubmission`
  entities (M10.3).
- ❌ `Stipulation` model + lifecycle verbs
  (M10.4).
- ❌ `Contract` + `FundingPacket` +
  `FundingStatus` entities (M10.5).
- ❌ `Chargeback` + `net_realized` verb
  (M10.6).
- ❌ `ComplianceRecord` entity +
  `/dealer-ai-f-and-i/` operator UI
  (M10.7).
- ❌ Full SSN / DOB / driver's-license
  storage — deferred until the M10.7
  Safeguards Rule technical-controls
  layer (encryption at rest, access
  logging, field-level ACLs per FINANCE
  §6.4). Storing full SSN before that
  layer ships would violate the
  Safeguards Rule; the M10.1 schema is
  intentionally narrow (applicant_full_name
  + optional last-4 only) so M10.1
  cannot become a compliance-debt
  substrate.
- ❌ `adverse_action` / `approved` /
  `declined` status values — those are
  per-lender state and belong to
  `LenderSubmission` at M10.3, not
  per-app state at M10.1.
- ❌ Frontend UI (M10.7).

## Reality check

- **Backend baseline:** `3,478 pass, 1
  skipped, 0 fail` (was `3,426 pass, 1
  skipped, 0 fail` at SESSION_105 close).
- **Migrations:** `0001`–`0025` (added
  `0025_credit_application_entity`).
- **Tenancy carriers:** 24 → 25 (added
  `CreditApplication`).
- **DRF admin surface:** 47 → 48 (added
  `POST /admin/credit-applications/`).
- **Frontend baseline:** unchanged (34
  pass); no frontend at M10.1.
- **`git status`:** clean pending the
  M10.1 commit.
- **`git log --oneline -3` (post-M10.1
  commit):** `Milestone 10 · Increment 1
  — CreditApplication entity …
  (SESSION_106)` on top.
- **Django check:** clean (0 issues).
- **`makemigrations --check --dry-run`:**
  "No changes detected."

## What SESSION_107 (M10.2) opens with

Per `MILESTONE_10_PLANNING.md` §7 M10.2:
**DealStructure entity + ratio computation
(LTV / PTI / DTI).**

Recommended step sequence for SESSION_107:

1. Confirm the M10.2 §5 decisions (if any
   surface at session open — none flagged
   in planning today).
2. Read first:
   - `MILESTONE_10_PLANNING.md` §1.2 +
     §7 M10.2.
   - `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
     (this file).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §3 (deal structure math) +
     `§3.2` payment engine reuse notes.
   - `backend/dealer_ai/services/payment_engine.py`
     (existing standard-APR + BHPH
     math to compose with).
   - `backend/dealer_ai/models.py::CreditApplication`
     (M10.1 substrate to attach
     `DealStructure` to).
3. Verify starting state:
   `python3 manage.py test dealer_ai`
   → `3,478 pass, 1 skipped, 0 fail`.
4. Draft (in order): `DealStructure`
   model + migration `0026`, tenancy
   carrier extension 25 → 26, service
   package `services/f_and_i/deal_structure.py`
   with ratio verbs (LTV / PTI / DTI) +
   endpoint `POST
   /admin/credit-applications/<int:pk>/deal-structure/`
   or similar per §5.a-equivalent
   decision at M10.2 open, ~30 tests.
5. Full-suite verification. Target
   3,478 → ~3,508.
6. Ship handoff
   `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`.
7. Overwrite `00-START-NEXT-SESSION.md`
   with M10.3 priority.

## Commit

Local only. Push to `origin/main`
deferred per M9-close convention —
per-increment push authorization
requested at session open. Message:

```
Milestone 10 · Increment 1 — CreditApplication entity + retention discipline (SESSION_106)

M10.1 ships the credit-app intake substrate for the F&I workflow:

- New CreditApplication model + migration 0025 (nullable FKs to
  both CustomerLead and Sale per §5.a Option C; retention clock
  denormalized at write from captured_at + 7 years).
- Retention clock locked at the model layer per §5.e —
  `.delete()` refuses unexpired records with
  CreditApplicationRetentionActiveError. No escape hatch.
- Model clean() enforces attach-shape (≥1 parent) + cross-tenant
  guards on both parent FKs.
- Tenancy carrier extension 24 → 25.
- New services/f_and_i/ package —
  compute_retention_expires_at (pure), record_credit_application
  (transactional), get_credit_application (tenant-scoped read).
- New IsFinanceManagerOrOwnerAtActiveDealership permission class
  in permissions.py. Grants f_and_i_manager + dealer_owner;
  documents non-grants (sales_manager separate for compliance).
- First M10 endpoint — POST /api/dealer-ai/admin/credit-applications/.
- 52 focused tests. Baseline 3,426 → 3,478 pass.

Four §5 decisions confirmed at session open (all as-recommended):
§5.a Option C, §5.b Option A, §5.c Option B, §5.d Option C.
```

## Deferred / observations for M10.2+

- The `f_and_i_manager` role has existed
  in `ROLE_CHOICES` since M1 but had no
  permission class until M10.1. Any
  M10.2+ endpoint that reuses the new
  permission class automatically respects
  the role split.
- The service surface `services/f_and_i/`
  has one module today
  (`credit_application.py`); M10.2-M10.7
  will add sibling modules
  (`deal_structure.py`, `lender.py`,
  `stipulation.py`, `contract.py`,
  `funding.py`, `chargeback.py`). Same
  layout pattern as `services/analytics/`
  from M8.
- `applicant_ssn_last4` is plain-text at
  rest at M10.1 — deliberately last-4
  only, per the Safeguards Rule
  posture called out in the docstring.
  When M10.7 ships the technical-controls
  layer, the schema extension for full
  SSN (encrypted, access-logged, field-
  level ACLs) is additive; the M10.1
  last-4 column stays as an operator
  quick-lookup index.
- Nothing in M10.1 required amending M1-M9
  behavior. `Sale`, `CustomerLead`, and
  `Vehicle` are consumed via FK only; no
  cascade shape or existing service verb
  was modified.
