---
state: active
date: 2026-08-02
last_session_shipped: SESSION_107
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: in_progress
next_session: SESSION_108
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 3
next_increment_name: "M10.3 — LenderProgram + LenderSubmission entities"
---

# Next session — SESSION_108 · Milestone 10 · Increment 3 (M10.3 — Lender catalog + submission)

> **SESSION_107 shipped M10.2 —**
> `DealStructure` entity substrate +
> M10.2 additive extension of M10.1's
> `CreditApplication`
> (`gross_monthly_income` +
> `existing_monthly_debt` nullable
> Decimals) + `services/f_and_i/deal_structure.py`
> module with six verbs (three pure
> ratio verbs LTV / PTI / DTI + write
> path + tenant-scoped read +
> recompute helper) + second M10
> endpoint (`POST /admin/deal-structures/`)
> + tenancy carrier extension (25 → 26)
> + 55 focused tests. Two design
> questions resolved at session open
> (both as-recommended): §1.2.a
> Option A (income + debt on CA),
> §1.9.a Option A (flat URL pattern).
>
> **Backend baseline: 3,533 pass, 1
> skipped, 0 fail** (was 3,478 at
> SESSION_106 close). Frontend Vitest
> baseline: 34 pass (unchanged; no
> frontend at M10.2). Migrations
> `0001`–`0026`. Tenancy carriers 26.
> DRF admin surface 49.
>
> **Push to `origin/main` for the M10.1
> and M10.2 commits is deferred
> pending explicit user authorization**
> per M9-close convention.
>
> **SESSION_108 opens M10.3 —
> LenderProgram + LenderSubmission
> entities.** Two new tenancy carriers
> (26 → 28). Attach-shape decisions
> for `LenderSubmission` surface at
> session open — likely FK to
> `DealStructure` (the natural parent
> — one deal-structure can be
> submitted to multiple lenders in
> parallel).

## First thing SESSION_108 must do

### 1. Check push authorization for the M10.1 + M10.2 commits

Both M10.1 and M10.2 commits live
locally on `main` only. Verify with
the user:

- Are the commits still local? (`git
  log origin/main..HEAD --oneline` —
  should show two commits.)
- Should they push now? If yes: `git
  push origin main` after explicit
  user "go."

Push is a shared-state action; per
CLAUDE.md safety posture, requires
per-push confirmation independent of
the per-increment authorization that
landed each commit.

### 2. Confirm M10.3 §5-equivalent decisions

Re-read `MILESTONE_10_PLANNING.md`
§1.3 + §5.d at session open. §5.d
already resolved at SESSION_106
(Option C — leave both). New M10.3
questions likely to surface:

- **`LenderSubmission` attach point.**
  FK to `DealStructure` (natural — a
  submission is *of* a deal structure
  to a lender) or nullable FKs to both
  `DealStructure` and `CreditApplication`
  (mirrors M10.1's §5.a Option C
  pattern)?
- **`LenderSubmission.status` vocabulary
  partition.** Planning §1.3 suggests
  four values (`pending` / `approved`
  / `counter` / `declined`). Fixed set
  (mirrors M10.1 §5.b Option A) or
  per-dealership extensible?
- **`LenderProgram` catalog scope.**
  Per-dealership (each dealership
  maintains its own lender list —
  matches §5.d Option C which kept
  the free-text field as notes) or a
  global catalog with per-dealership
  activation flags?
- **`counter_terms` / `approval_terms`
  JSONField shape.** Free-form JSON
  at M10.3 (like M10.2's
  `back_end_products`)? Or a fixed
  key set at the schema layer?

**If any decision surfaces, do NOT
write M10.3 code until it's resolved
with the user.** Amend
`MILESTONE_10_PLANNING.md` §0.a
narrowly per M9 / M10.1 / M10.2 §0.a
precedent before implementation.

### 3. Verify starting state

- `git status` — clean (M10.2 commit
  landed at SESSION_107 close).
- `git log --oneline -3` — top should
  be `Milestone 10 · Increment 2 —
  DealStructure entity … (SESSION_107)`
  or similar.
- `python3 manage.py test dealer_ai` →
  **3,533 pass, 1 skipped, 0 fail.**
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npm test` → **34
  pass**.
- `npx tsc --noEmit` + `npx vite
  build` both clean.
- `redis-cli ping` → `PONG`.

## What M10.3 delivers

Per `MILESTONE_10_PLANNING.md` §7 M10.3
+ §1.3:

- **New `LenderProgram` model +
  migration `0027`.** Per-dealership
  catalog of active lender programs
  (fields: `name`, `contact`,
  `terms_summary`, `is_active`,
  timestamps). Additive alongside
  the M10.1-era free-text
  `DealerOnboardingProfile.subprime_lenders`
  per §5.d Option C — the free-text
  field becomes a notes area.
- **New `LenderSubmission` model.**
  FK to `DealStructure` +
  `LenderProgram`. Fields:
  `submitted_at`, `status`
  (`pending` / `approved` /
  `counter` / `declined`),
  `counter_terms` (JSON),
  `approval_terms` (JSON), `notes`.
- **Tenancy-carrier extensions
  26 → 28** (both new entities).
- **New `services/f_and_i/lender.py`**
  module — sibling to
  `services/f_and_i/credit_application.py`
  and `deal_structure.py`. Catalog
  verbs (record/list programs) +
  submission verbs (record
  submission, update status, list
  by deal-structure).
- **New endpoints** —
  `POST /admin/lender-programs/`,
  `POST /admin/lender-submissions/`,
  and likely `PATCH
  /admin/lender-submissions/<pk>/`
  for status updates. Role-gated on
  the same
  `IsFinanceManagerOrOwnerAtActiveDealership`
  permission class from M10.1.
- **~25 focused tests.**
- **Baseline target 3,533 → ~3,558.**

### Non-goals for M10.3

- ❌ No `Stipulation` / `Contract` /
  `Funding` / `Chargeback` /
  `ComplianceRecord` entities
  (M10.4-M10.7).
- ❌ No operator UI (M10.7).
- ❌ No direct lender-portal
  integrations (deferred per
  IMPLEMENTATION_ROADMAP §Milestone 10
  non-goals).
- ❌ No data migration from the free-
  text `subprime_lenders` field
  (§5.d Option C explicitly left
  both; operators re-populate the
  structured catalog manually).

## What SESSION_108 should do

### Recommended step sequence

0. **Push authorization check** (§1
   above).

1. **Confirm M10.3 §5-equivalent
   decisions with the user** (§2
   above). Do NOT write code until
   every open decision is resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.3 + §5.d + §7 M10.3.
   - `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
     (previous session).
   - `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
     (§5.d origin).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §4 (lender submission workflow).
   - `backend/dealer_ai/models.py::DealStructure`
     + `::CreditApplication` (M10.1-
     M10.2 substrates — attach
     targets).
   - `backend/dealer_ai/services/f_and_i/deal_structure.py`
     (pattern to mirror for
     `lender.py`).
   - `backend/dealer_ai/models.py::DealerOnboardingProfile`
     (find `subprime_lenders` free-
     text field — additive coexists
     with new catalog).

3. **Verify starting state** (§3
   above).

4. **Draft (in order):**
   - `LenderProgram` +
     `LenderSubmission` models +
     migration `0027`.
   - Tenancy carrier additions
     (26 → 28).
   - `services/f_and_i/lender.py`
     module.
   - Endpoints + URLs.
   - ~25 focused tests.

5. **Full-suite verification.** Target
   3,533 → ~3,558.

6. **Ship handoff at
   `docs/handoffs/SESSION_108_m10_inc3_lender.md`.**

7. **Overwrite `00-START-NEXT-SESSION.md`**
   with M10.4 priority.

## Explicit non-goals for SESSION_108

- ❌ Do NOT ship Stipulation / Contract
  / Funding / Chargeback /
  ComplianceRecord entities
  (M10.4-M10.7).
- ❌ Do NOT ship frontend UI (M10.7).
- ❌ Do NOT modify M1-M9 business
  logic. Additive extensions to
  M10.1-M10.2 models are OK per the
  established pattern; behavior
  changes are not.
- ❌ Do NOT force-push or amend the
  M10.1 / M10.2 commits.
- ❌ Do NOT migrate the free-text
  `subprime_lenders` field into the
  new structured catalog (§5.d
  Option C explicitly left both).

## NEXT TASK

Start SESSION_108 with (a) push-
authorization check for M10.1 + M10.2
commits, (b) confirming M10.3 §5-
equivalent decisions with the user,
(c) the read-first list, (d) starting-
state verification, then (e)
`LenderProgram` + `LenderSubmission`
models + `services/f_and_i/lender.py`
+ endpoints + ~25 tests. Target
baseline 3,533 → ~3,558. Ship the
M10.3 handoff.

Backend baseline at SESSION_108 close:
**~3,558 pass**. Frontend baseline:
unchanged (no frontend at M10.3).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
8. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
9. `docs/handoffs/SESSION_105_m9_closeout.md`
10. `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
11. `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy.md`
12. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
13. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
14. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
15. `docs/CAPABILITY_MATRIX.md` §7j
16. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules + research +
code are facts.

---

## Operational state (post-SESSION_107 — M10.2 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0026`. Test baseline:
  **3,533 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 34 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled task
  families registered (unchanged since
  M7).
- **Milestones shipped:** M1 → **M9**
  (SESSION_105 close); M10 in progress
  (SESSION_106 shipped M10.1;
  SESSION_107 shipped M10.2).
- **DRF admin surface:** 49 endpoints
  (M9 47 + M10.1 credit-applications +
  M10.2 deal-structures).
- **Frontend operator routes:** 9
  (unchanged; no frontend at M10.1 /
  M10.2).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4 submodules);
  M9.1 `services/sale/`; M9.2
  `services/delivery/`; M9.3-M9.4
  extended M8 modules; M10.1 added
  `services/f_and_i/` (with
  `credit_application.py`); **M10.2
  extended `services/f_and_i/` with
  `deal_structure.py`** — now two
  submodules in the F&I package.
- **Tenancy carriers:** 26 (M1 six +
  M3 three + M4 six + M5 two + M6 two
  + M7 two + M8 one + M9.1 one — `Sale`
  + M9.2 one — `Delivery` + M10.1 one —
  `CreditApplication` + **M10.2 one —
  `DealStructure`**).
- **Permission classes:** 8 in
  `dealer_ai/permissions.py` (M1 four
  + M4 one + M9 uses M4's + M10.1 one —
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  reused unchanged at M10.2).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:** unchanged.
- **M10.2 substrate (shipped):**
  `DealStructure` entity attaching a
  `CreditApplication` to a `Vehicle`
  with deal-desk math (sale_price /
  down / trade / taxes / fees /
  amount_financed / apr in percent
  units matching payment_engine
  convention / term / monthly_payment
  / back_end_products JSONField) +
  three denormalized ratio outputs
  (LTV / PTI / DTI, all
  Decimal(6,2) nullable) computed
  at write time by the M10.2 service
  verbs. Additive extension to M10.1's
  CreditApplication (nullable
  gross_monthly_income +
  existing_monthly_debt Decimals) so
  PTI / DTI have parent-side inputs.
  M10.1-era rows survive NULL and
  ratio verbs return `None` for them.
- **Milestone 10 next:** M10.3
  `LenderProgram` + `LenderSubmission`
  entities. Verify §5-equivalent
  decisions at session open (attach
  shape, status vocabulary, catalog
  scope, terms-JSON shape). ~25
  tests. Baseline 3,533 → ~3,558.
