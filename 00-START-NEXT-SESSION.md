---
state: active
date: 2026-08-02
last_session_shipped: SESSION_113
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: planning
next_session: SESSION_114
next_milestone: 11
next_milestone_name: "Sales-side non-chat channels + customer-journey completeness"
next_increment: 1
next_increment_name: "M11.1 — Channel intake + CustomerLead extension"
---

# Next session — SESSION_114 · Milestone 11 · Increment 1 (M11.1 — Channel intake + CustomerLead extension)

> **SESSION_113 shipped M10.8 —**
> six close-out docs (retrospective +
> capability matrix §7k + roadmap flip +
> planning frontmatter flip + session-
> start refresh + M11 planning skeleton)
> + one coordinated commit landing every
> M10.1–M10.7 stage. **Milestone 10 —
> F&I deal desk — SHIPPED.**
>
> **M10 close totals:** ten new entities
> across seven implementation sessions
> (CreditApplication + DealStructure +
> LenderProgram + LenderSubmission +
> Stipulation + Contract +
> BackEndProductAgreement + Funding +
> Chargeback + ComplianceRecord) + one
> complete new `services/f_and_i/`
> package (seven submodules) + one new
> permission class (reused unchanged
> M10.2-M10.7) + 17 new DRF admin
> endpoints + first F&I frontend
> surface at `/dealer-ai-f-and-i/`.
> **29 load-bearing decisions resolved
> across 7 implementation sessions —
> all as-recommended by the user**
> (streak-pattern signal per M10 §6
> lesson 16).
>
> **Backend baseline: 3,730 pass, 1
> skipped, 0 fail** (was 3,426 at
> M9 close — +304 tests, 0
> regressions). **Frontend Vitest
> baseline: 51 pass** (was 34 — +17
> at M10.7). Migrations `0001`–`0031`.
> Tenancy carriers 34. DRF admin
> surface 64. Frontend operator
> routes 11.
>
> **Push authorization:** M10 close
> commit + all 7 M10 implementation
> commits will be pushed as a batch
> after user authorization at
> SESSION_113 close.
>
> **SESSION_114 opens M11.1 —
> Channel intake + CustomerLead
> extension.** Per
> `MILESTONE_11_PLANNING.md` (draft
> planning skeleton written at
> M10.8 close per standing user
> directive). Six §5 decisions to
> confirm at session open.

## First thing SESSION_114 must do

### 1. Confirm the six §5 decisions in `MILESTONE_11_PLANNING.md`

The M11 planning skeleton drafted at
M10.8 close carries six load-bearing
decisions. All six recommendations
follow the M10 pattern (twenty-nine
consecutive as-recommended
resolutions).

Recommendations (drawn from
`MILESTONE_11_PLANNING.md` §9):

1. **§5.a — CustomerLead.channel field
   + vocabulary.** Option A (additive
   with historical-row backfill to
   `chat`).
2. **§5.b — Listing-platform webhook
   shape.** Option A (one generic
   webhook + adapter dispatch).
3. **§5.c — TestDrive attach shape.**
   Option A (mandatory FK to both
   CustomerLead + Vehicle).
4. **§5.d — FollowUpCadence + Task
   shape.** Option A (two entities;
   task rows queryable).
5. **§5.e — DealWriteup →
   CreditApplication flow.** Option A
   (auto-create CA from handoff
   action).
6. **§5.f — Operator UI scope.**
   Option C (MVP — ship substrate;
   extended UI in a follow-on).

**Do not write M11.1 code until every
`[NEEDS-DECISION-BEFORE-M11.N]` item is
resolved.** Any user override → amend
`MILESTONE_11_PLANNING.md` §0.a
narrowly at session top (per M5-M10
§0.a precedent) before implementation.

### 2. Verify starting state

- `git status` — clean (M10.8 commit
  landed at SESSION_113 close;
  batch push authorized + executed).
- `git log --oneline -3` — top
  should be `Milestone 10 shipped —
  F&I deal desk (SESSION_106-113)`
  or similar.
- `git log origin/main..HEAD
  --oneline` — **empty** (all M10
  commits pushed).
- `python3 manage.py test dealer_ai`
  → **3,730 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **51 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `npx tsc --noEmit` + `npx vite
  build` both clean.
- `redis-cli ping` → `PONG`.

## What M11.1 delivers

Per `MILESTONE_11_PLANNING.md` §7
M11.1:

- **Additive `CustomerLead.channel`
  field** — CharField with fixed
  5+1 vocab (`chat` default /
  `walk_in` / `phone` /
  `listing_form` / `referral` /
  `other`) + data migration
  backfilling historical rows to
  `chat`. Per §5.a Option A.
- **Per-channel POST endpoints:**
  - `POST /admin/leads/walk-in/`
  - `POST /admin/leads/phone/`
  - `POST /admin/leads/referral/`
    (with `referrer_lead_id` for
    attribution)
  - **`POST /admin/leads/webhook/`**
    generic webhook + adapter
    dispatch shape per §5.b Option
    A. First adapter TBD (Autotrader
    / Cars.com / Facebook
    Marketplace / etc. — pick the
    one operator evidence names
    first).
- **`CustomerLead.referrer` FK**
  (nullable, SET_NULL) for referral
  attribution per §1.6.
- **New `services/leads/`
  package** (or extend existing
  `services/lead_service.py`) with
  channel-specific write verbs.
- **~25 focused tests.**
- **Baseline target 3,730 →
  ~3,755.**

### Non-goals for M11.1

- ❌ No `TestDrive` (M11.2).
- ❌ No `DealWriteup` (M11.3).
- ❌ No cadence orchestration
  (M11.4).
- ❌ No be-back (M11.5).
- ❌ No frontend at M11.1 (M11.6).
- ❌ No modification of M1-M10
  business logic.
- ❌ No listing-platform outbound
  syndication.

## What SESSION_114 should do

### Recommended step sequence

1. **Confirm the six §5 decisions
   with the user** (§1 above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     §1.1 + §1.6 + §5.a + §5.b +
     §7 M11.1.
   - `docs/handoffs/SESSION_113_m10_close.md`
     (previous session).
   - `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
     §6 (nineteen lessons carry
     into M11).
   - `docs/research/SALES_DEPARTMENT_MAPPING.md`
     §lead acquisition + workflow.
   - `backend/dealer_ai/models.py::CustomerLead`
     (target of additive `channel`
     + `referrer` extension).
   - `backend/dealer_ai/services/lead_service.py`
     (existing lead-service pattern
     to extend or fork per §5).

3. **Verify starting state** (§2
   above).

4. **Draft (in order):**
   - `CustomerLead.channel` field +
     data migration + `referrer` FK.
   - Per-channel POST endpoints.
   - Generic webhook endpoint +
     first adapter module.
   - `services/leads/` package
     extensions (or extend existing).
   - ~25 focused tests.

5. **Full-suite verification.**
   Target 3,730 → ~3,755.

6. **Ship handoff at
   `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M11.2 priority.

## Explicit non-goals for SESSION_114

- ❌ Do NOT ship M11.2-M11.7 scope
  (TestDrive, DealWriteup,
  cadence, be-back, UI,
  closeout).
- ❌ Do NOT modify M1-M10 business
  logic.
- ❌ Do NOT force-push or amend
  the M10 commits.

## NEXT TASK

Start SESSION_114 with (a)
confirming the six §5 decisions
with the user (all recommendations
per M10 pattern), (b) the read-
first list, (c) starting-state
verification, then (d)
`CustomerLead.channel` +
`referrer` additive extension +
per-channel endpoints + generic
webhook + first adapter module +
~25 tests. Target baseline
3,730 → ~3,755. Ship the M11.1
handoff.

Backend baseline at SESSION_114
close: **~3,755 pass**. Frontend
baseline: unchanged (no frontend
at M11.1).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_113_m10_close.md` (this session's close)
8. `docs/handoffs/SESSION_112_m10_inc7_compliance_ui.md`
9. `docs/handoffs/SESSION_111_m10_inc6_chargeback.md`
10. `docs/handoffs/SESSION_110_m10_inc5_contract_funding.md`
11. `docs/handoffs/SESSION_109_m10_inc4_stipulation.md`
12. `docs/handoffs/SESSION_108_m10_inc3_lender.md`
13. `docs/handoffs/SESSION_107_m10_inc2_deal_structure.md`
14. `docs/handoffs/SESSION_106_m10_inc1_credit_application.md`
15. `docs/CAPABILITY_MATRIX.md` §7k
16. `docs/research/SALES_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_113 — M10 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0031`. Test baseline:
  **3,730 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 51 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. 4 scheduled
  task families registered
  (unchanged since M7).
- **Milestones shipped:** M1 →
  **M10** (SESSION_113 close).
  M11 planning drafted.
- **DRF admin surface:** 64
  endpoints.
- **Frontend operator routes:**
  11.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` package
  with seven submodules
  (credit_application, deal_structure,
  lender, stipulation, contract,
  funding, chargeback, compliance).
- **Tenancy carriers:** 34.
- **Permission classes:** 8
  (M10.1's
  `IsFinanceManagerOrOwnerAtActiveDealership`
  reused unchanged M10.2-M10.7).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** unchanged.
- **Deterministic rules:**
  unchanged.
- **Milestone 11 next:** M11.1
  channel intake +
  `CustomerLead.channel` +
  `referrer` additive extension +
  per-channel endpoints +
  generic webhook. Verify six
  §5 decisions at session open.
  ~25 tests. Baseline 3,730 →
  ~3,755.
