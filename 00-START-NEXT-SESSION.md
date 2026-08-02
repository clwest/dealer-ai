---
state: active
date: 2026-08-02
last_session_shipped: SESSION_105
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: planning
next_session: SESSION_106
next_milestone: 10
next_milestone_name: "Finance (F&I) deal desk"
next_increment: 1
next_increment_name: "M10.1 — CreditApplication entity + retention discipline"
---

# Next session — SESSION_106 · Milestone 10 · Increment 1 (M10.1 — CreditApplication entity)

> **SESSION_105 shipped M9.6 closeout —**
> `MILESTONE_9_RETROSPECTIVE.md` (sixteen
> lessons — one new: substrate-gap pushback
> as a productive session-open pattern) +
> `CAPABILITY_MATRIX.md` §7j + roadmap flip
> + planning frontmatter flip + session-
> start refresh (baseline 3,274 → 3,426
> backend, 19 → 34 frontend) +
> `MILESTONE_10_PLANNING.md` new (per
> standing user directive) + coordinated
> commit landing every M9.1–M9.6 stage.
>
> **Push to `origin/main` is deferred
> pending explicit user authorization** —
> check with the user at session open
> whether the commit should push or stay
> local.
>
> **Backend baseline: 3,426 pass, 1
> skipped, 0 fail.** Frontend Vitest
> baseline: 34 pass. Migrations
> `0001`–`0024`.
>
> **SESSION_106 opens M10.1 —
> CreditApplication entity + retention
> discipline.** Four §5 decisions in
> `MILESTONE_10_PLANNING.md` §5 to
> confirm at session open before code
> lands.

## First thing SESSION_106 must do

### 1. Check push authorization for the M9-close commit

The M9-close commit lives locally on `main`
only. Verify with the user:

- Is the commit still local? (`git log
  origin/main..HEAD --oneline` — non-empty
  means still local.)
- Should it push now? If yes: `git push
  origin main` after explicit user "go."

Push is a shared-state action; per
CLAUDE.md safety posture, requires per-push
confirmation independent of the per-
milestone authorization that landed the
commit. Matches SESSION_100 M8-close-commit
push flow.

### 2. Confirm the four §5 decisions in `MILESTONE_10_PLANNING.md`

Recommendations (drawn from §9):

1. **§5.a — CreditApplication attach
   point.** Recommendation TBD; will
   surface at session open after re-
   reading FINANCE §workflow.
2. **§5.b — Stipulation vocabulary
   partition.** Option A (small fixed
   set: proof of income / insurance /
   residence / references / other).
3. **§5.c — Chargeback impact on
   `Sale.gross_realized`.** Option B
   (additive `net_realized` verb; no
   M9 schema change). Follows M8 §6
   lesson 11 additive-extension
   pattern.
4. **§5.d — Onboarding lender
   migration.** Option C (leave both;
   the structured
   `LenderProgram` catalog is
   additive alongside the free-text
   `subprime_lenders` field).

**Do not write M10.1 code until every
`[NEEDS-DECISION-BEFORE-M10.N]` item is
resolved.** If the user overrides any
decision, amend
`MILESTONE_10_PLANNING.md` §0.a narrowly
at session top (per M5-M9 §0.a
precedent) before implementation.

### 3. Verify starting state

- `git status` — clean (M9-close commit
  landed at SESSION_105 close).
- `git log --oneline -3` — top should be
  `Milestone 9 shipped — sale + delivery
  closure (SESSION_100-105)` or similar.
- `python3 manage.py test dealer_ai` →
  **3,426 pass, 1 skipped, 0 fail.**
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npm test` → **34
  pass**.
- `npx tsc --noEmit` + `npx vite build`
  both clean.
- `redis-cli ping` → `PONG`.

## What M10.1 delivers

Per `MILESTONE_10_PLANNING.md` §7 M10.1:

- **New `CreditApplication` model +
  migration `0025`** attached per §5.a
  decision. Legal retention clock at
  the model layer (created_at +
  retention_expires_at computed from
  policy constants; `delete()` refuses
  unexpired records at the model
  layer, not the service layer).
- **New `services/f_and_i/` package** +
  first verbs (`record_credit_application`
  + read verb + retention-clock verb).
- **Tenancy-carrier extension 24 → 25**
  (`CreditApplication`).
- **New permission class**
  `IsFinanceManagerOrOwnerAtActiveDealership`
  in `permissions.py` — `f_and_i_manager`
  role already exists in M1
  `ROLE_CHOICES`; the permission class
  composes with `IsAuthenticated` per
  the M4-M9 pattern.
- **First endpoint**
  `POST /api/dealer-ai/admin/credit-applications/`
  or a per-lead / per-sale nested path
  depending on §5.a decision. Role-
  gated on the new permission class.
- **~30 focused tests.**
- **Baseline target 3,426 → ~3,456.**

### Non-goals for M10.1

- ❌ No `DealStructure` yet (M10.2).
- ❌ No lender / stip / contract /
  funding / chargeback entities
  (M10.3-M10.7).
- ❌ No operator UI (M10.7).
- ❌ No direct lender-portal
  integrations (deferred per
  IMPLEMENTATION_ROADMAP §Milestone 10
  non-goals).

## What SESSION_106 should do

### Recommended step sequence

0. **Push authorization check** (§1
   above).

1. **Confirm the four §5 decisions with
   the user** (§2 above). Do NOT write
   code until every
   `[NEEDS-DECISION-BEFORE-M10.N]` item
   is resolved.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_10_PLANNING.md`
     §1.1 + §1.8 + §5 + §7 M10.1.
   - `docs/handoffs/SESSION_105_m9_closeout.md`
     (previous session).
   - `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
     §6 (sixteen lessons carry into
     M10).
   - `docs/CAPABILITY_MATRIX.md` §7j
     (M9 substrate M10 layers on top
     of).
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
     §workflow + §compliance + pains
     #1 / #4 / #6 / #7 / #9.
   - `backend/dealer_ai/models.py::CustomerLead`
     (potential CreditApplication
     attach target — §5.a).
   - `backend/dealer_ai/models.py::Sale`
     (M9.1 substrate for chargeback
     plumbing — §5.c).
   - `backend/dealer_ai/permissions.py`
     (add `IsFinanceManagerOrOwnerAtActiveDealership`).

3. **Verify starting state** (§3 above).

4. **Draft (in order):**
   - `CreditApplication` model +
     migration `0025` (per §5.a
     decision).
   - Retention-clock enforcement at
     the model layer.
   - `services/f_and_i/__init__.py` +
     first verbs.
   - Tenancy carrier addition.
   - New permission class.
   - First endpoint + URL.
   - ~30 focused tests.

5. **Full-suite verification.** Target
   3,426 → ~3,456.

6. **Ship handoff at
   `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`.**

7. **Overwrite `00-START-NEXT-SESSION.md`**
   with M10.2 priority.

## Explicit non-goals for SESSION_106

- ❌ Do NOT ship DealStructure /
  LenderProgram / LenderSubmission /
  Stipulation / Contract / Funding /
  Chargeback / ComplianceRecord
  entities (M10.2-M10.7).
- ❌ Do NOT ship frontend UI (M10.7).
- ❌ Do NOT modify M1-M9 business logic.
- ❌ Do NOT force-push or amend the
  M9-close commit.

## NEXT TASK

Start SESSION_106 with (a) push-
authorization check for the M9-close
commit, (b) confirming the four §5
decisions with the user, (c) the read-
first list, (d) starting-state
verification, then (e) `CreditApplication`
model + retention-clock enforcement +
first endpoint + ~30 tests. Target
baseline 3,426 → ~3,456. Ship the M10.1
handoff.

Backend baseline at SESSION_106 close:
**~3,456 pass**. Frontend baseline:
unchanged (no frontend at M10.1).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 10
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_10_PLANNING.md`
6. `docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_105_m9_closeout.md`
8. `docs/handoffs/SESSION_104_m9_inc5_operator_ui.md`
9. `docs/handoffs/SESSION_103_m9_inc4_buyer_accuracy.md`
10. `docs/handoffs/SESSION_102_m9_inc3_analytics_extensions.md`
11. `docs/handoffs/SESSION_101_m9_inc2_delivery.md`
12. `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`
13. `docs/CAPABILITY_MATRIX.md` §7j
14. `docs/research/FINANCE_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules + research +
code are facts.

---

## Operational state (post-SESSION_105 — M9 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0024`. Test baseline:
  **3,426 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 34 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 + Redis
  6.4.0 + `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled task
  families registered (unchanged from
  M7).
- **Milestones shipped:** M1 → **M9**
  (SESSION_105 close). M10 planning
  drafted.
- **DRF admin surface:** 47 endpoints.
- **Frontend operator routes:** 9 (M9.5
  added `dealer-ai-inventory/:stock/sale`).
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** M8 added
  `services/analytics/` (4 submodules);
  M9.1 `services/sale/`; M9.2
  `services/delivery/`; M9.3 added
  `services/analytics/gross_profit.py`
  submodule + extended M8.4 modules with
  true-verb siblings; M9.4 extended
  `services/analytics/recon.py` with Q7
  buyer-estimate-accuracy verb.
- **Tenancy carriers:** 24 (M1 six + M3
  three + M4 six + M5 two + M6 two + M7
  two + M8 one + M9.1 one — `Sale` +
  M9.2 one — `Delivery`).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:** unchanged.
- **M9 aggregation + workflow surface
  (shipped + wired to UI):** Sale entity
  with `gross_realized` denormalized at
  write, Delivery entity with 5-item
  checklist + verify-insurance,
  `VehicleAcquisition.buyer` FK
  (nullable) enabling Q7. Q3 true / Q6
  gross-profit trend / Q7 buyer
  accuracy / Q8 true inventory turn.
  Fifth operator UI tab **Realized
  Gross** + new per-vehicle Sale +
  Delivery page.
- **Milestone 10 next:** M10.1
  CreditApplication + retention
  discipline. Four §5 decisions to
  confirm at session open. ~30 tests.
  Baseline 3,426 → ~3,456.
