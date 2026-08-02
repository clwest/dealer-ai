---
state: active
date: 2026-08-02
last_session_shipped: SESSION_109
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
next_session: SESSION_110
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 5
next_increment_name: "M10.5 — Contract + FundingPacket + FundingStatus entities"
---

# Next session — SESSION_110 · Milestone 10 · Increment 5 (M10.5 — Contract + Funding)

> **SESSION_109 shipped M10.4 —**
> `Stipulation` entity attached to
> `LenderSubmission` (CASCADE) +
> `documented_by` FK to
> `settings.AUTH_USER_MODEL`
> (nullable, SET_NULL) +
> `services/f_and_i/stipulation.py`
> module (four verbs) + two new
> endpoints (`POST /admin/stipulations/`,
> `PATCH /admin/stipulations/<pk>/`) +
> tenancy carrier extension (28 → 29)
> + 35 focused tests. Four design
> questions resolved at session open
> (all as-recommended, all Option A):
> §1.4.a (mandatory FK to
> LenderSubmission), §1.4.b (fixed
> 3-value state), §1.4.c
> (documented_by as User FK
> SET_NULL), §1.4.d (defer photo
> evidence to M10.7).
>
> **Backend baseline: 3,621 pass, 1
> skipped, 0 fail** (was 3,586 at
> SESSION_108 close). Frontend
> Vitest baseline: 34 pass
> (unchanged; no frontend at M10.4).
> Migrations `0001`–`0028`. Tenancy
> carriers 29. DRF admin surface
> 54.
>
> **Push to `origin/main` for M10.1
> + M10.2 + M10.3 + M10.4 commits
> is deferred pending explicit user
> authorization** per M9-close
> convention. Four commits
> pending.
>
> **SESSION_110 opens M10.5 —
> Contract + FundingPacket +
> FundingStatus entities.** This
> is the **largest single M10
> increment sketch** (three
> entities in one session). Expect
> five design decisions to surface
> at session open.

## First thing SESSION_110 must do

### 1. Check push authorization for the M10.1-M10.4 commits

Four M10 commits live locally on
`main` only. Verify with the user:

- `git log origin/main..HEAD
  --oneline` — should show four
  commits.
- Should they push now? Consider
  batching at M10 close (matches
  M9-close SESSION_105 pattern) or
  pushing incrementally.

### 2. Confirm M10.5 §5-equivalent decisions

Re-read `MILESTONE_10_PLANNING.md`
§1.5 + §1.6 + §7 M10.5 at session
open. Questions likely to surface:

- **Contract entity split.** One
  `Contract` model (with a
  `contract_type` vocabulary
  covering RISC / lease / cash),
  or separate `Contract` (RISC)
  + `BackEndProductAgreement`
  (per-product VSC / GAP
  agreement) entities?
- **FundingPacket vs FundingStatus.**
  Planning §1.6 sketches both.
  Are they one entity (a
  FundingRecord with packet-
  assembly fields + status fields)
  or two (FundingPacket = docs
  assembled; FundingStatus = has
  the lender funded yet)?
- **Contract state machine.**
  `unsigned` → `signed` → …?
  What are the terminal /
  intermediate states? Does
  `re-signed` need to be its own
  state or is that captured by
  editing an existing signed
  Contract row (with an audit
  trail)?
- **Contract attach point.** FK
  to `DealStructure` (the version
  that was signed) or
  `LenderSubmission` (the
  approved terms that were
  contracted)? Or both?
- **Product-agreement vocabulary
  (VSC / GAP / paint & fabric /
  etc.).** Structured now (fixed
  set matching M9.1 finance-
  type / M10.1 stip-type
  precedents) or free-form JSON
  (mirroring M10.2's
  `back_end_products` and M10.3's
  `counter_terms`)?

**If any decision surfaces, do
NOT write M10.5 code until it's
resolved with the user.** Amend
`MILESTONE_10_PLANNING.md` §0.a
narrowly per prior precedent.

### 3. Verify starting state

- `git status` — clean (M10.4
  commit landed at SESSION_109
  close).
- `git log --oneline -3` — top
  should be `Milestone 10 ·
  Increment 4 — Stipulation
  tracking (SESSION_109)` or
  similar.
- `python3 manage.py test dealer_ai`
  → **3,621 pass, 1 skipped, 0
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

## What M10.5 delivers

Per `MILESTONE_10_PLANNING.md` §7
M10.5:

- **New `Contract` model +
  migration `0029`.** Attached
  to `DealStructure` (or per §5
  decision). Fields per §1.5:
  `contract_type` (RISC / lease
  / cash), `signed_at` DateTime
  nullable, `signed_by` FK
  User nullable SET_NULL,
  `financed_amount` +
  `total_of_payments` +
  `finance_charge` Decimals,
  `apr_disclosure` TextField
  (regulatory disclosure), 
  `first_payment_date` Date
  nullable, `back_end_products`
  JSONField (or FK entity per
  §5 decision).
- **New `FundingPacket` +
  `FundingStatus` entities** (or
  single unified entity per §5
  decision).
- **Tenancy-carrier extensions
  29 → ~32** (three or two new
  carriers depending on §5.b
  decision).
- **New `services/f_and_i/contract.py`**
  + **`services/f_and_i/funding.py`**
  modules — sibling to M10.1-
  M10.4 modules.
- **New endpoints** — POST /
  PATCH for each entity.
- **~25 focused tests.**
- **Baseline target 3,621 →
  ~3,646.**

### Non-goals for M10.5

- ❌ No `Chargeback` /
  `net_realized` verb (M10.6).
- ❌ No `ComplianceRecord` /
  operator UI (M10.7).
- ❌ No direct lender-portal
  funding integrations (deferred
  beyond M10).
- ❌ No document / e-signature
  storage plumbing (M10.7
  compliance layer).

## What SESSION_110 should do

### Recommended step sequence

0. **Push authorization check** (§1
   above).

1. **Confirm M10.5 §5-equivalent
   decisions with the user** (§2
   above). Do NOT write code
   until every open decision is
   resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.5 + §1.6 + §7 M10.5.
   - `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`
     (previous session).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §5 (contract), §6 (funding),
     §4.3-§4.5 (back-end products
     — VSC / GAP / tire &
     wheel).
   - `backend/dealer_ai/models.py::DealStructure`
     (M10.2 substrate — likely
     Contract attach target).
   - `backend/dealer_ai/models.py::Stipulation`
     + services/stipulation.py
     (pattern to mirror for
     Contract state machine +
     signed_at auto-populate).

3. **Verify starting state** (§3
   above).

4. **Draft (in order — bundle
   depends on §5 decisions):**
   - `Contract` +
     `FundingPacket` +
     `FundingStatus` models +
     migration `0029` (or
     narrower per §5 decisions).
   - Tenancy carrier additions.
   - Two new service modules.
   - Endpoints + URLs.
   - ~25 focused tests.

5. **Full-suite verification.**
   Target 3,621 → ~3,646.

6. **Ship handoff at
   `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M10.6 priority.

## Explicit non-goals for SESSION_110

- ❌ Do NOT ship Chargeback /
  ComplianceRecord entities
  (M10.6-M10.7).
- ❌ Do NOT ship frontend UI
  (M10.7).
- ❌ Do NOT modify M1-M9 or M10.1-
  M10.4 business logic.
- ❌ Do NOT force-push or amend
  the M10.1-M10.4 commits.
- ❌ Do NOT ship document / e-
  signature storage plumbing
  (M10.7).

## NEXT TASK

Start SESSION_110 with (a) push-
authorization check for M10.1-
M10.4 commits, (b) confirming
M10.5 §5-equivalent decisions
with the user (~5 questions
expected), (c) the read-first
list, (d) starting-state
verification, then (e) three
new models + two service modules
+ endpoints + ~25 tests. Target
baseline 3,621 → ~3,646. Ship
the M10.5 handoff.

Backend baseline at SESSION_110
close: **~3,646 pass**. Frontend
baseline: unchanged (no frontend
at M10.5).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`
8. `docs/handoffs/SESSION_108_m10_inc3_lender.md`
9. `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
10. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
11. `docs/handoffs/SESSION_105_m9_closeout.md`
12. `docs/CAPABILITY_MATRIX.md` §7j
13. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_109 — M10.4 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0028`. Test baseline:
  **3,621 pass**, 1 skipped, 0
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
  **M9** (SESSION_105 close); M10
  in progress (SESSION_106 M10.1;
  SESSION_107 M10.2; SESSION_108
  M10.3; SESSION_109 M10.4).
- **DRF admin surface:** 54
  endpoints (M9 47 + M10.1
  credit-applications + M10.2
  deal-structures + M10.3
  lender-programs / lender-
  submissions POST + PATCH +
  M10.4 stipulations POST +
  PATCH).
- **Frontend operator routes:** 9
  (unchanged; no frontend at
  M10.1-M10.4).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4
  submodules); M9.1
  `services/sale/`; M9.2
  `services/delivery/`; M9.3-
  M9.4 extended M8 modules;
  M10.1 added
  `services/f_and_i/` with
  `credit_application.py`;
  M10.2 extended with
  `deal_structure.py`; M10.3
  extended with `lender.py`;
  **M10.4 extended with
  `stipulation.py`** — now four
  submodules in the F&I
  package.
- **Tenancy carriers:** 29 (M1
  six + M3 three + M4 six + M5
  two + M6 two + M7 two + M8
  one + M9.1 one — `Sale` +
  M9.2 one — `Delivery` +
  M10.1 one — `CreditApplication`
  + M10.2 one — `DealStructure`
  + M10.3 two — `LenderProgram`
  + `LenderSubmission` + **M10.4
  one — `Stipulation`**).
- **Permission classes:** 8 in
  `dealer_ai/permissions.py`
  (M1 four + M4 one + M9 uses
  M4's + M10.1 one —
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  reused unchanged at M10.2 /
  M10.3 / M10.4).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:**
  unchanged.
- **M10.4 substrate (shipped):**
  `Stipulation` entity attached
  to `LenderSubmission` (CASCADE)
  with fixed 5-value
  `stip_type` vocabulary (M10.1
  §5.b Option A) and fixed
  3-value `state` vocabulary
  (`open` default / `cleared` /
  `waived`). `documented_by`
  FK to User (nullable,
  SET_NULL) for audit trail.
  `cleared_at` auto-populated by
  the service on first
  transition to
  cleared/waived; reset to
  NULL on transition back to
  open. Any-to-any state
  transition allowed. Two
  endpoints; PATCH sources
  `documented_by` from
  `request.user` server-side.
- **Milestone 10 next:** M10.5
  `Contract` + `FundingPacket` +
  `FundingStatus` entities (or
  subset per §5-equivalent
  decisions surfacing at
  session open). Verify design
  questions at session open
  (5 expected — contract split,
  packet vs status entity
  boundary, state machine,
  attach point, product-
  agreement vocabulary
  structure). ~25 tests.
  Baseline 3,621 → ~3,646.
