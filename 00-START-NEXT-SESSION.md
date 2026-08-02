---
state: active
date: 2026-08-02
last_session_shipped: SESSION_110
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
next_session: SESSION_111
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 6
next_increment_name: "M10.6 — Chargeback + net_realized verb"
---

# Next session — SESSION_111 · Milestone 10 · Increment 6 (M10.6 — Chargeback + net_realized)

> **SESSION_110 shipped M10.5 —**
> `Contract` + `BackEndProductAgreement`
> + `Funding` entities +
> `services/f_and_i/contract.py`
> (six verbs) +
> `services/f_and_i/funding.py`
> (three verbs) + five new
> endpoints + tenancy carrier
> extensions (29 → 32) + 42 focused
> tests. Five design questions
> resolved at session open (all as-
> recommended): §1.5.a Option B
> (separate BEPA entity), §1.6.a
> Option C (single Funding, no
> Packet), §1.5.b Option A (three-
> state Contract), §1.5.c Option A
> (FK to DealStructure), §1.5.d
> Option A (fixed product vocab).
>
> **Backend baseline: 3,663 pass,
> 1 skipped, 0 fail** (was 3,621
> at SESSION_109 close). Frontend
> Vitest baseline: 34 pass
> (unchanged; no frontend at
> M10.5). Migrations `0001`–`0029`.
> Tenancy carriers 32. DRF admin
> surface 59.
>
> **Push to `origin/main` for the
> M10.1 + M10.2 + M10.3 + M10.4 +
> M10.5 commits is deferred
> pending explicit user
> authorization** per M9-close
> convention. Five commits
> pending.
>
> **SESSION_111 opens M10.6 —
> Chargeback + net_realized.**
> §5.c Option B from SESSION_106
> already ratified the additive
> `net_realized` verb (no M9
> schema change).

## First thing SESSION_111 must do

### 1. Check push authorization for M10.1-M10.5 commits

Five M10 commits live locally on
`main` only. Verify with the user:

- `git log origin/main..HEAD
  --oneline` — should show five
  commits.
- Should they push now? Consider
  batching at M10 close (matches
  M9-close SESSION_105 pattern)
  or pushing incrementally.

### 2. Confirm M10.6 §5-equivalent decisions

Re-read `MILESTONE_10_PLANNING.md`
§1.7 + §5.c at session open.
Questions likely to surface:

- **Chargeback attach point.** FK
  to `Contract` (deal-level
  chargeback: FPD / early payoff
  / repossession) or FK to
  `BackEndProductAgreement`
  (per-product cancellation:
  VSC / GAP)? Or nullable FKs
  to both (mirrors M10.1 §5.a
  Option C — attach to whichever
  entity generated the event)?
- **Chargeback type vocabulary.**
  Fixed set from FINANCE §5.7?
  `first_payment_default` /
  `early_payoff` /
  `product_cancellation` /
  `repossession` /
  `deal_unwind`?
- **BEPA cancellation-fields
  additive extension.** Add
  `cancelled_at` +
  `cancellation_amount` to
  `BackEndProductAgreement` via
  migration `0030` (same
  additive-extension pattern
  used at M10.2 for M10.1 CA
  income fields).
- **`net_realized` verb shape /
  location.** Extend
  `services/analytics/`
  (from M8) or add to
  `services/f_and_i/computation.py`
  (new module) or land as a
  Sale-model method?
- **Chargeback timestamps + audit
  trail.** `chargeback_date`
  (business date) +
  `recorded_at` (auto row insert)
  + `recorded_by` User FK for
  audit trail (mirrors M10.4
  `documented_by` pattern)?
- **Automatic Funding state
  transition.** Should recording
  a Chargeback that references a
  Contract's Funding transition
  that Funding to `chargedback`
  state atomically?

**If any decision surfaces, do
NOT write M10.6 code until it's
resolved with the user.** Amend
`MILESTONE_10_PLANNING.md` §0.a
narrowly per prior precedent.

### 3. Verify starting state

- `git status` — clean.
- `git log --oneline -3` — top
  should be `Milestone 10 ·
  Increment 5 — Contract +
  BackEndProductAgreement +
  Funding entities (SESSION_110)`
  or similar.
- `python3 manage.py test dealer_ai`
  → **3,663 pass, 1 skipped, 0
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

## What M10.6 delivers

Per `MILESTONE_10_PLANNING.md` §7
M10.6 + §5.c:

- **New `Chargeback` model +
  migration `0030`.** Attach
  shape per §5-equivalent
  decision. Fields: `chargeback_type`
  from fixed vocab per FINANCE
  §5.7, `chargeback_date`,
  `chargeback_amount` Decimal,
  optional `recorded_by` User
  FK (SET_NULL), optional notes.
- **Additive extension of
  `BackEndProductAgreement`
  from M10.5** — add
  `cancelled_at` DateTime
  nullable + `cancellation_amount`
  Decimal nullable. Bundled into
  migration `0030` (additive
  pattern from M10.2's
  extension of M10.1 CA).
- **Tenancy-carrier extension
  32 → 33.**
- **New `services/f_and_i/chargeback.py`**
  module — record_chargeback +
  `net_realized(sale)` verb per
  §5.c Option B (additive
  alongside M9.1
  `Sale.gross_realized`; no M9
  schema change).
- **New endpoints** —
  `POST /admin/chargebacks/`
  and possibly `PATCH
  /admin/back-end-products/<pk>/`
  for cancellation-field
  updates.
- **~20 focused tests.**
- **Baseline target 3,663 →
  ~3,683.**

### Non-goals for M10.6

- ❌ No `ComplianceRecord` or
  operator UI (M10.7).
- ❌ No frontend UI (M10.7).
- ❌ No modification to M9.1
  `Sale.gross_realized` semantics
  or column — per §5.c Option
  B, additive verb only.
- ❌ No reversal-of-commission
  posting (out of scope; that's
  a payroll workflow, not F&I).
- ❌ No lender chargeback-portal
  integration (deferred beyond
  M10).

## What SESSION_111 should do

### Recommended step sequence

0. **Push authorization check**
   (§1 above).

1. **Confirm M10.6 §5-equivalent
   decisions with the user** (§2
   above). Do NOT write code
   until every open decision is
   resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.7 + §5.c + §7 M10.6.
   - `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`
     (previous session).
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
   - `backend/dealer_ai/models.py::Sale`
     (M9.1 substrate for
     `net_realized` computation).

3. **Verify starting state** (§3
   above).

4. **Draft (in order):**
   - `Chargeback` model +
     additive BEPA extension +
     migration `0030`.
   - Tenancy carrier extension.
   - `services/f_and_i/chargeback.py`
     with record + `net_realized`
     verb.
   - Endpoints + URLs.
   - ~20 focused tests.

5. **Full-suite verification.**
   Target 3,663 → ~3,683.

6. **Ship handoff at
   `docs/handoffs/SESSION_111_m10_inc6_chargeback.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M10.7 (compliance +
   operator UI) priority.

## Explicit non-goals for SESSION_111

- ❌ Do NOT ship ComplianceRecord
  or operator UI (M10.7).
- ❌ Do NOT ship frontend UI
  (M10.7).
- ❌ Do NOT modify M1-M9 or
  M10.1-M10.5 business logic.
- ❌ Do NOT force-push or amend
  the M10.1-M10.5 commits.
- ❌ Do NOT touch
  `Sale.gross_realized` column
  or write-time computation
  (§5.c Option B — additive
  verb only).

## NEXT TASK

Start SESSION_111 with (a) push-
authorization check for M10.1-
M10.5 commits, (b) confirming
M10.6 §5-equivalent decisions
with the user (~5-6 questions
expected), (c) the read-first
list, (d) starting-state
verification, then (e)
`Chargeback` model + additive
BEPA extension +
`services/f_and_i/chargeback.py`
(record + `net_realized`) +
endpoints + ~20 tests. Target
baseline 3,663 → ~3,683. Ship
the M10.6 handoff.

Backend baseline at SESSION_111
close: **~3,683 pass**. Frontend
baseline: unchanged (no frontend
at M10.6).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`
8. `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`
9. `docs/handoffs/SESSION_108_m10_inc3_lender.md`
10. `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
11. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
12. `docs/handoffs/SESSION_105_m9_closeout.md`
13. `docs/CAPABILITY_MATRIX.md` §7j
14. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_110 — M10.5 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0029`. Test baseline:
  **3,663 pass**, 1 skipped, 0
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
  M10.4; SESSION_110 M10.5).
- **DRF admin surface:** 59
  endpoints (M9 47 + M10.1 CA
  + M10.2 deal-structures +
  M10.3 lender-programs /
  submissions POST + PATCH +
  M10.4 stipulations POST +
  PATCH + M10.5 contracts POST
  + PATCH + BEPA POST + funding
  POST + PATCH).
- **Frontend operator routes:** 9
  (unchanged; no frontend at
  M10.1-M10.5).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4
  submodules); M9.1
  `services/sale/`; M9.2
  `services/delivery/`; M9.3-
  M9.4 extended M8; M10.1
  added `services/f_and_i/`
  with `credit_application.py`;
  M10.2 extended with
  `deal_structure.py`; M10.3
  extended with `lender.py`;
  M10.4 extended with
  `stipulation.py`; **M10.5
  extended with `contract.py`
  + `funding.py`** — now six
  submodules in the F&I
  package.
- **Tenancy carriers:** 32 (M1
  six + M3 three + M4 six + M5
  two + M6 two + M7 two + M8
  one + M9.1 one — `Sale` +
  M9.2 one — `Delivery` +
  M10.1 one — `CreditApplication`
  + M10.2 one — `DealStructure`
  + M10.3 two — `LenderProgram`
  + `LenderSubmission` + M10.4
  one — `Stipulation` + **M10.5
  three — `Contract` +
  `BackEndProductAgreement` +
  `Funding`**).
- **Permission classes:** 8 in
  `dealer_ai/permissions.py`
  (M1 four + M4 one + M9 uses
  M4's + M10.1 one —
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  reused unchanged at M10.2-
  M10.5).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:**
  unchanged.
- **M10.5 substrate (shipped):**
  `Contract` entity attached to
  `DealStructure` (CASCADE) with
  three-value state machine
  (`unsigned` default →
  `signed` → optional `voided`).
  Two-verb transition pattern
  (`sign_contract` /
  `void_contract`) with
  auto-populated timestamps.
  Sign after void refused (409).
  `BackEndProductAgreement`
  per-product row on Contract
  (CASCADE) with fixed 6-value
  `product_type` vocab.
  Optional structural fields
  per product type.
  Cancellation fields deferred
  to M10.6. `Funding` OneToOne
  to Contract with state
  machine (`pending_funding`
  default → `funded` →
  `chargedback` vocab-only
  until M10.6). `mark_funded`
  verb auto-populates
  `funded_at` + records actual
  `funding_amount`.
- **Milestone 10 next:** M10.6
  `Chargeback` entity +
  additive BEPA cancellation
  fields + `net_realized`
  verb. Verify §5-equivalent
  decisions at session open
  (5-6 questions expected —
  attach point, type vocab,
  BEPA extension, verb
  location, timestamps,
  Funding state auto-transition).
  ~20 tests. Baseline 3,663 →
  ~3,683.
