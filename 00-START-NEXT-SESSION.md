---
state: active
date: 2026-08-02
last_session_shipped: SESSION_111
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
next_session: SESSION_112
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 7
next_increment_name: "M10.7 — ComplianceRecord + operator UI"
---

# Next session — SESSION_112 · Milestone 10 · Increment 7 (M10.7 — ComplianceRecord + operator UI)

> **SESSION_111 shipped M10.6 —**
> `Chargeback` entity (nullable FKs
> to Contract + BEPA per §5.a
> Option C pattern) + additive
> `BackEndProductAgreement`
> cancellation-field extension
> (`cancelled_at` +
> `cancellation_amount`) +
> `services/f_and_i/chargeback.py`
> module (three verbs: record with
> two atomic side effects,
> `net_realized(sale)` per §5.c
> Option B, get) + one new endpoint
> + tenancy carrier extension
> (32 → 33) + 36 focused tests.
> Six design questions resolved
> at session open (all as-
> recommended): §1.7.a Option A
> (nullable both parents), §1.7.b
> Option B (5+1 vocab), §1.7.c
> Option A (additive BEPA
> extension), §1.7.d Option A
> (verb in f_and_i), §1.7.e
> Option A (full audit trail),
> §1.7.f Option A (deal-level
> auto-transition Funding).
>
> **Backend baseline: 3,699 pass,
> 1 skipped, 0 fail** (was 3,663
> at SESSION_110 close). Frontend
> Vitest baseline: 34 pass
> (unchanged; no frontend at
> M10.6). Migrations
> `0001`–`0030`. Tenancy carriers
> 33. DRF admin surface 60.
>
> **Push to `origin/main` for the
> M10.1 + M10.2 + M10.3 + M10.4 +
> M10.5 + M10.6 commits is
> deferred pending explicit user
> authorization** per M9-close
> convention. Six commits
> pending.
>
> **SESSION_112 opens M10.7 —
> ComplianceRecord + operator
> UI.** This is the M10 closer.
> Largest single-session scope
> in M10 (compliance model +
> back-end wiring + full new
> frontend surface for the
> deal-jacket browser + stip-
> chase board + funding-status
> view + chargeback
> reconciliation). Six design
> decisions expected at open.

## First thing SESSION_112 must do

### 1. Check push authorization for M10.1-M10.6 commits

Six M10 commits live locally on
`main` only. Verify with the user:

- `git log origin/main..HEAD
  --oneline` — should show six
  commits.
- Should they push now? Recommend
  batching at M10 close (matches
  M9-close SESSION_105 pattern):
  ship M10.7 + M10.8 close-out,
  then push all seven M10
  commits together with the
  close-out.

### 2. Confirm M10.7 §5-equivalent decisions

Re-read `MILESTONE_10_PLANNING.md`
§1.8 + §7 M10.7 + §7 M10.8 at
session open. Questions likely to
surface (large surface — M10.7
is the M10 close-out):

- **ComplianceRecord attach
  shape.** One-per-DealStructure
  (deal-level compliance) vs
  one-per-Contract (contract-
  level) vs one-per-Sale?
- **Per-concern vs single-entity
  compliance model** (planning
  §1.8 explicitly deferred to
  M10.7). Options: single
  `ComplianceRecord` with a JSON
  blob of concerns; per-concern
  rows (`RetentionRecord`,
  `PrivacyNoticeRecord`,
  `AdverseActionRecord`,
  `RedFlagsCheckRecord`,
  `SafeguardsAuditRecord`); or
  hybrid (ComplianceRecord as
  parent + typed subclass rows).
- **Photo / document storage
  plumbing.** M10.4 §1.4.d +
  M10.5 §1.6.a resolutions
  deferred storage plumbing to
  M10.7. Ship now (Cloudinary/S3
  wiring + presigned URLs +
  MIME validation + retention
  discipline) or defer as
  beyond-M10 scope?
- **Operator UI scope.** Full
  workflow (credit-app intake →
  deal desking → lender
  submission → stip-chase →
  contract signing → funding →
  chargeback reconciliation) or
  narrower MVP (just deal-jacket
  browser + stip-chase board)?
- **Frontend test surface.**
  ~25 Vitest tests per planning
  §7 M10.7. Extend the M9.5
  Operator UI framework
  (`/dealer-ai-inventory/*` +
  `/dealer-ai-realized-gross`)
  as `/dealer-ai-f-and-i/` sub-
  routes, or ship as a distinct
  route family?
- **M10.7 vs M10.8 ordering.**
  Standard M10 close (planning
  §7 M10.8 = documentation
  closeout, retrospective,
  M11 planning skeleton). Would
  M10.7 combine implementation
  + closeout, or split into
  two sessions?

**If any decision surfaces, do
NOT write M10.7 code until it's
resolved with the user.** Amend
`MILESTONE_10_PLANNING.md` §0.a
narrowly per prior precedent.

### 3. Verify starting state

- `git status` — clean.
- `git log --oneline -3` — top
  should be `Milestone 10 ·
  Increment 6 — Chargeback +
  net_realized (SESSION_111)`
  or similar.
- `python3 manage.py test dealer_ai`
  → **3,699 pass, 1 skipped, 0
  fail.**
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npm test` →
  **34 pass**.
- `npx tsc --noEmit` + `npx vite
  build` both clean.
- `redis-cli ping` → `PONG`.

## What M10.7 delivers

Per `MILESTONE_10_PLANNING.md` §7
M10.7:

- **New `ComplianceRecord` entity
  (or per-concern rows)** +
  migration `0031`.
- **Tenancy-carrier extension
  33 → ~34** (or more if per-
  concern model chosen).
- **New `services/f_and_i/compliance.py`**
  module.
- **New DRF endpoints** — deal-
  jacket assembly + compliance-
  record CRUD.
- **New frontend routes** under
  `/dealer-ai-f-and-i/` (or the
  chosen namespace):
  - Deal-jacket browser
  - Stip-chase board
  - Funding-status view
  - Chargeback reconciliation
- **~20 backend tests +
  ~25 frontend Vitest tests.**
- **Baseline target 3,699 →
  ~3,720 backend + 34 → ~60
  frontend.**

### Non-goals for M10.7

- ❌ No frontend beyond the
  operator surface (customer-
  facing F&I is a distinct
  workflow).
- ❌ No lender-portal
  integrations (deferred
  beyond M10).
- ❌ No BHPH-specific
  accounting (M11+ scope per
  `IMPLEMENTATION_ROADMAP` §M10
  non-goals).
- ❌ No document / e-signature
  storage if deferred at
  session open.

## What SESSION_112 should do

### Recommended step sequence

0. **Push authorization check**
   (§1 above).

1. **Confirm M10.7 §5-equivalent
   decisions with the user** (§2
   above). Six questions
   expected — largest decision
   surface in M10.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.8 + §7 M10.7 + §7 M10.8.
   - `docs/handoffs/SESSION_111_m10_inc6_chargeback.md`
     (previous session).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §6 compliance sections
     (§6.1-§6.9).
   - `backend/dealer_ai/models.py::Chargeback`
     + M10.1-M10.5 substrates.
   - `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
     (M9.5 operator UI pattern
     to mirror for frontend
     routes).
   - `frontend/src/routes/*.tsx`
     — existing operator UI
     shape.

3. **Verify starting state** (§3
   above).

4. **Draft (in order — bundle
   depends on §5 decisions):**
   - `ComplianceRecord` model(s)
     + migration `0031`.
   - Tenancy carrier extension.
   - `services/f_and_i/compliance.py`.
   - Backend endpoints + URLs.
   - Frontend routes + components
     + tests.
   - ~20 backend + ~25 frontend
     tests.

5. **Full-suite verification.**
   Target 3,699 → ~3,720
   backend + 34 → ~60 frontend.

6. **Ship handoff at
   `docs/handoffs/SESSION_112_m10_inc7_compliance_ui.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with either M10.8 close-out
   (if split) or M11 (if M10.8
   bundles into this session).

## Explicit non-goals for SESSION_112

- ❌ Do NOT ship M11+ scope.
- ❌ Do NOT modify M1-M9 or
  M10.1-M10.6 business logic.
- ❌ Do NOT force-push or amend
  the M10.1-M10.6 commits.

## NEXT TASK

Start SESSION_112 with (a) push-
authorization check for M10.1-
M10.6 commits, (b) confirming
M10.7 §5-equivalent decisions
with the user (~6 questions
expected — largest surface of
M10), (c) the read-first list,
(d) starting-state
verification, then (e)
`ComplianceRecord` model(s) +
`services/f_and_i/compliance.py`
+ backend endpoints + full
`/dealer-ai-f-and-i/` frontend
route family + ~20 backend +
~25 frontend tests. Target
baseline 3,699 → ~3,720
backend + 34 → ~60 frontend.
Ship the M10.7 handoff.

Backend baseline at SESSION_112
close: **~3,720 pass**. Frontend
baseline: **~60 pass** (M10.7
adds the first F&I frontend
surface).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_111_m10_inc6_chargeback.md`
8. `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`
9. `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`
10. `docs/handoffs/SESSION_108_m10_inc3_lender.md`
11. `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
12. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
13. `docs/handoffs/SESSION_105_m9_closeout.md`
14. `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
15. `docs/CAPABILITY_MATRIX.md` §7j
16. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_111 — M10.6 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0030`. Test baseline:
  **3,699 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 34 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled
  task families registered
  (unchanged since M7).
- **Milestones shipped:** M1 →
  **M9** (SESSION_105 close);
  M10 in progress (SESSION_106
  M10.1; SESSION_107 M10.2;
  SESSION_108 M10.3; SESSION_109
  M10.4; SESSION_110 M10.5;
  SESSION_111 M10.6).
- **DRF admin surface:** 60
  endpoints.
- **Frontend operator routes:** 9
  (unchanged; no frontend at
  M10.1-M10.6).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4
  submodules); M9.1
  `services/sale/`; M9.2
  `services/delivery/`; M9.3-
  M9.4 extended M8; M10.1 added
  `services/f_and_i/` with
  `credit_application.py`;
  M10.2 extended with
  `deal_structure.py`; M10.3
  extended with `lender.py`;
  M10.4 extended with
  `stipulation.py`; M10.5
  extended with `contract.py`
  + `funding.py`; **M10.6
  extended with `chargeback.py`**
  — now seven submodules in
  the F&I package.
- **Tenancy carriers:** 33 (M1
  six + M3 three + M4 six + M5
  two + M6 two + M7 two + M8
  one + M9.1 one + M9.2 one +
  M10.1 one + M10.2 one + M10.3
  two + M10.4 one + M10.5 three
  + **M10.6 one — `Chargeback`**).
- **Permission classes:** 8 in
  `dealer_ai/permissions.py`
  (M1 four + M4 one + M9 uses
  M4's + M10.1 one —
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  reused unchanged at M10.2-
  M10.6).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:**
  unchanged.
- **M10.6 substrate (shipped):**
  `Chargeback` entity with
  nullable FKs to Contract +
  BackEndProductAgreement (both
  CASCADE) per §5.a Option C
  pattern. Fixed 5+1
  `chargeback_type` vocab per
  FINANCE §5.7. Audit trail
  via `recorded_by` FK (User
  SET_NULL) sourced from
  `request.user` server-side.
  Additive `cancelled_at` +
  `cancellation_amount`
  columns on M10.5's BEPA
  (auto-populated by chargeback
  verb for
  `product_cancellation` type).
  `record_chargeback` verb with
  two atomic side effects:
  deal-level chargebacks auto-
  transition Funding to
  `chargedback`;
  `product_cancellation`
  chargebacks auto-populate
  BEPA cancellation columns.
  `skip_funding_transition=True`
  kwarg for edge cases. Pure
  `net_realized(sale)` aggregate
  per §5.c Option B — no M9
  schema change.
- **Milestone 10 next:** M10.7
  `ComplianceRecord` (or per-
  concern rows) + `/dealer-ai-
  f-and-i/` operator UI. Verify
  §5-equivalent decisions at
  session open (6 questions
  expected — largest surface of
  M10). ~20 backend + ~25
  frontend tests. Baseline
  3,699 → ~3,720 backend +
  34 → ~60 frontend.
