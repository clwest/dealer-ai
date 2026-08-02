---
state: active
date: 2026-08-02
last_session_shipped: SESSION_106
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
next_session: SESSION_107
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 2
next_increment_name: "M10.2 — DealStructure entity + LTV / PTI / DTI ratio computation"
---

# Next session — SESSION_107 · Milestone 10 · Increment 2 (M10.2 — DealStructure entity)

> **SESSION_106 shipped M10.1 —**
> `CreditApplication` entity substrate +
> migration `0025` + `services/f_and_i/`
> package (three verbs) + new
> `IsFinanceManagerOrOwnerAtActiveDealership`
> permission class + first M10 endpoint
> (`POST /admin/credit-applications/`) +
> tenancy carrier extension (24 → 25) +
> 52 focused tests. All four
> `[NEEDS-DECISION-BEFORE-M10.N]` items
> resolved at session open (all four as-
> recommended; §5.a Option C, §5.b
> Option A, §5.c Option B, §5.d Option C).
> Retention clock locked at the model
> layer per §5.e —
> `CreditApplication.delete()` refuses
> unexpired records.
>
> **Backend baseline: 3,478 pass, 1
> skipped, 0 fail** (was 3,426 at
> SESSION_105 close). Frontend Vitest
> baseline: 34 pass (unchanged; no
> frontend at M10.1). Migrations
> `0001`–`0025`. Tenancy carriers 25.
> DRF admin surface 48.
>
> **Push to `origin/main` for the M10.1
> commit is deferred pending explicit
> user authorization** per M9-close
> convention.
>
> **SESSION_107 opens M10.2 —
> DealStructure entity + LTV / PTI /
> DTI ratio computation.** No `[NEEDS-
> DECISION-BEFORE-M10.N]` items are
> flagged for M10.2 in the planning
> doc today — verify at session open.

## First thing SESSION_107 must do

### 1. Check push authorization for the M10.1 commit

The M10.1 commit lives locally on `main`
only. Verify with the user:

- Is the commit still local? (`git log
  origin/main..HEAD --oneline` — non-empty
  means still local.)
- Should it push now? If yes: `git push
  origin main` after explicit user "go."

Push is a shared-state action; per
CLAUDE.md safety posture, requires per-
push confirmation independent of the per-
increment authorization that landed the
commit. Matches SESSION_105 M9-close /
SESSION_100 M8-close push flow.

### 2. Confirm any M10.2 §5 decisions

Re-read `MILESTONE_10_PLANNING.md` §5 at
session open. Today no
`[NEEDS-DECISION-BEFORE-M10.2]` marker is
present in the planning doc for M10.2,
but the design memo (§1.2) may surface
issues on close read (which entity
DealStructure attaches to — CreditApplication
or Sale? ratio storage — denormalized
columns or verb-computed on read?).

**If any decision surfaces, do NOT write
M10.2 code until it's resolved with the
user.** Amend `MILESTONE_10_PLANNING.md`
§0.a narrowly at session top per M10.1 /
M5-M9 §0.a precedent before implementation.

### 3. Verify starting state

- `git status` — clean (M10.1 commit
  landed at SESSION_106 close).
- `git log --oneline -3` — top should be
  `Milestone 10 · Increment 1 —
  CreditApplication entity … (SESSION_106)`
  or similar.
- `python3 manage.py test dealer_ai` →
  **3,478 pass, 1 skipped, 0 fail.**
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npm test` → **34
  pass**.
- `npx tsc --noEmit` + `npx vite build`
  both clean.
- `redis-cli ping` → `PONG`.

## What M10.2 delivers

Per `MILESTONE_10_PLANNING.md` §7 M10.2:

- **New `DealStructure` model +
  migration `0026`.** Attaches to a
  `CreditApplication` (or `Sale` — TBD
  at session open) with the deal-desk
  math: cash-down / trade-in / financed-
  amount / term / rate / monthly-
  payment (composed from the existing
  `services.payment_engine`
  standard-APR + BHPH math).
- **New `services/f_and_i/deal_structure.py`**
  module — sibling to
  `services/f_and_i/credit_application.py`
  from M10.1. Ratio verbs:
  `loan_to_value(deal)`,
  `payment_to_income(deal)`,
  `debt_to_income(deal)`. Reuses
  `services/payment_engine` for
  monthly-payment math (deterministic
  math substrate is unchanged).
- **Tenancy-carrier extension 25 → 26**
  (`DealStructure`).
- **Endpoint** shape TBD at session open
  (attach path depends on §5-equivalent
  decision).
- **~30 focused tests.**
- **Baseline target 3,478 → ~3,508.**

### Non-goals for M10.2

- ❌ No `LenderProgram` /
  `LenderSubmission` yet (M10.3).
- ❌ No `Stipulation` / `Contract` /
  `Funding` / `Chargeback` /
  `ComplianceRecord` entities
  (M10.4-M10.7).
- ❌ No operator UI (M10.7).
- ❌ No changes to
  `services/payment_engine` — the M2
  math substrate stays as-is (M10.2
  composes with it).

## What SESSION_107 should do

### Recommended step sequence

0. **Push authorization check** (§1
   above).

1. **Confirm M10.2 §5 decisions with
   the user** (§2 above). Do NOT write
   code until every
   `[NEEDS-DECISION-BEFORE-M10.N]` item
   is resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.2 + §7 M10.2.
   - `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
     (previous session).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §3 (deal structure math).
   - `backend/dealer_ai/services/payment_engine.py`
     (existing standard-APR + BHPH
     math to compose with).
   - `backend/dealer_ai/models.py::CreditApplication`
     (M10.1 substrate — the likely
     attach target for
     `DealStructure`).
   - `backend/dealer_ai/models.py::Sale`
     (alternate attach target — see
     §5-equivalent decision at M10.2
     open).
   - `backend/dealer_ai/services/f_and_i/credit_application.py`
     (pattern to mirror for
     `deal_structure.py`).

3. **Verify starting state** (§3 above).

4. **Draft (in order):**
   - `DealStructure` model +
     migration `0026` (per §5-
     equivalent decision).
   - Ratio verbs
     (`services/f_and_i/deal_structure.py`).
   - Tenancy carrier addition.
   - Endpoint + URL.
   - ~30 focused tests.

5. **Full-suite verification.** Target
   3,478 → ~3,508.

6. **Ship handoff at
   `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`.**

7. **Overwrite `00-START-NEXT-SESSION.md`**
   with M10.3 priority.

## Explicit non-goals for SESSION_107

- ❌ Do NOT ship LenderProgram /
  LenderSubmission / Stipulation /
  Contract / Funding / Chargeback /
  ComplianceRecord entities (M10.3-M10.7).
- ❌ Do NOT ship frontend UI (M10.7).
- ❌ Do NOT modify M1-M9 business logic.
- ❌ Do NOT force-push or amend the M10.1
  commit.

## NEXT TASK

Start SESSION_107 with (a) push-
authorization check for the M10.1 commit,
(b) confirming any surfaced M10.2 §5
decisions with the user, (c) the read-
first list, (d) starting-state
verification, then (e) `DealStructure`
model + ratio verbs + endpoint + ~30
tests. Target baseline 3,478 → ~3,508.
Ship the M10.2 handoff.

Backend baseline at SESSION_107 close:
**~3,508 pass**. Frontend baseline:
unchanged (no frontend at M10.2).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
8. `docs/handoffs/SESSION_105_m9_closeout.md`
9. `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
10. `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy.md`
11. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
12. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
13. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
14. `docs/CAPABILITY_MATRIX.md` §7j
15. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules + research +
code are facts.

---

## Operational state (post-SESSION_106 — M10.1 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0025`. Test baseline:
  **3,478 pass**, 1 skipped, 0 fail.
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
  (SESSION_106 shipped M10.1).
- **DRF admin surface:** 48 endpoints
  (M9 47 + M10.1 `POST
  /admin/credit-applications/`).
- **Frontend operator routes:** 9
  (unchanged; no frontend at M10.1).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4 submodules);
  M9.1 `services/sale/`; M9.2
  `services/delivery/`; M9.3 added
  `services/analytics/gross_profit.py`;
  M9.4 extended `services/analytics/recon.py`
  with Q7 buyer-estimate-accuracy verb;
  **M10.1 added `services/f_and_i/`
  (one submodule so far —
  `credit_application.py`)**.
- **Tenancy carriers:** 25 (M1 six +
  M3 three + M4 six + M5 two + M6 two
  + M7 two + M8 one + M9.1 one — `Sale`
  + M9.2 one — `Delivery` + **M10.1
  one — `CreditApplication`**).
- **Permission classes:** 8 in
  `dealer_ai/permissions.py` (M1 four +
  M4 one + M9 uses M4's + **M10.1 one —
  `IsFinanceManagerOrOwnerAtActiveDealership`**).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:** unchanged.
- **M10.1 substrate (shipped):**
  `CreditApplication` entity with
  attach shape (nullable FKs to both
  `CustomerLead` and `Sale` per §5.a
  Option C), retention clock at the
  model layer (`captured_at + 7
  years`; `.delete()` refuses
  unexpired records per §5.e),
  minimal PII surface (full-SSN
  handling deferred until M10.7
  Safeguards Rule technical-controls
  layer).
- **Milestone 10 next:** M10.2
  `DealStructure` entity + LTV / PTI /
  DTI ratio computation. Verify §5-
  equivalent decisions at session
  open. ~30 tests. Baseline 3,478 →
  ~3,508.
