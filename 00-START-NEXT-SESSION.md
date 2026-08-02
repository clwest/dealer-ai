---
state: active
date: 2026-08-02
last_session_shipped: SESSION_118
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
milestone_11_status: in_progress
next_session: SESSION_119
next_milestone: 11
next_milestone_name: "Sales-side non-chat channels + customer-journey completeness"
next_increment: 6
next_increment_name: "M11.6 — Operator UI (first M11 frontend increment)"
---

# Next session — SESSION_119 · Milestone 11 · Increment 6 (M11.6 — Operator UI)

> **SESSION_118 shipped M11.5 —**
> new `BeBack` entity + three-verb
> service + two-task Celery no-show
> detector wired into Beat at 07:00
> daily + three DRF endpoints + 29
> focused tests (target ~25). Three
> §5.g decisions recorded in §0.a
> (Options A / A / B). Streak still
> **35 as-recommended M5.1 →
> M11.1**.
>
> **Backend baseline: 3,858 → 3,887
> (+29, zero regressions).**
> Frontend baseline: **51**
> (unchanged; M11.5 backend-only).
> Migrations `0001`–`0036`. DRF
> admin surface **77 → 80**.
> Tenancy carriers **38 → 39**.
> Celery-beat task families **5 →
> 6**. Permission classes **8**
> (unchanged). M11 backend
> substrate now complete —
> **M11.6 is the first frontend
> increment in M11**.

## First thing SESSION_119 must do

### 1. Confirm §5.f Option C still fits + pick a UI scope

Per `MILESTONE_11_PLANNING.md`
§0.a (M11.1 amendment), **§5.f
Option C** — MVP substrate at
M11.1; extended UI in a follow-
on increment — was confirmed at
SESSION_114 open. M11.6 is that
follow-on.

Three implementation-time
scoping decisions surface at
M11.6 open. Record in §0.a per
M11.3-M11.5 precedent:

- **§5.f.1 — Route family.**
  Options revisit: (a) extend
  `/dealer-ai-leads/` with tabs
  vs (b) new
  `/dealer-ai-sales/` route
  family vs (c) minimal drop-in
  additions to the existing
  leads page. **Recommendation:
  Option B** (new
  `/dealer-ai-sales/`) — five
  new backend surfaces (channel
  intake, test-drive log, deal
  writeup, follow-up queue,
  be-back queue) is enough to
  warrant a distinct route
  family rather than tab-
  cramming a single page.
- **§5.f.2 — MVP surface
  scope.** Which of the five
  backend surfaces ship in the
  M11.6 MVP? **Recommendation:**
  channel filter on the leads
  list + test-drive log +
  follow-up task work-queue +
  be-back list. Deal writeup +
  approval + handoff is
  deferred to a follow-on
  because the handoff flow
  touches F&I integration and
  needs a distinct UX pass.
- **§5.f.3 — Vitest test
  target.** Target ~15 focused
  Vitest tests per §7 M11.6
  ("~15 backend + ~25
  frontend" — inverted here
  because backend is done).
  Backend delta expected at 0
  (frontend-only increment).

### 2. Verify starting state

- `git status` clean (M11.5
  commit landed at SESSION_118
  close).
- `git log --oneline -3` — top
  should be the M11.5 commit.
- `python3 manage.py test dealer_ai`
  → **3,887 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **51 pass**.
- `npx tsc --noEmit` clean.
- `npx vite build` clean.

## What M11.6 delivers

Per `MILESTONE_11_PLANNING.md`
§1.8 + §5.f Option C + §7 M11.6
(assuming the recommendations
above are accepted):

- **New route family**
  `/dealer-ai-sales/` with
  four routes:
  - `/dealer-ai-sales/leads`
    — channel-filtered lead
    list.
  - `/dealer-ai-sales/test-drives`
    — test-drive log (per-
    salesperson + date range).
  - `/dealer-ai-sales/follow-ups`
    — task work-queue (defaults
    to "due today, pending").
  - `/dealer-ai-sales/be-backs`
    — be-back list with state
    filter.
- **API client extensions in
  `frontend/src/api/`** for the
  new DRF surfaces (channel
  intake, test-drive create,
  follow-up cadence + task
  transitions, be-back
  transitions).
- **Shared table + filter
  components** matching the
  existing shadcn patterns
  (see `/dealer-ai-f-and-i/`
  M10.7 precedent).
- **~15 focused Vitest tests**
  covering API-client
  serialization, filter state,
  optimistic transitions.
- **Frontend baseline target
  51 → ~66** (+15).
- **Backend baseline: no
  change** (3,887).

### Non-goals for M11.6

- ❌ No modification of M1-M11.5
  backend business logic.
- ❌ No new backend endpoints —
  frontend consumes existing
  M11.1-M11.5 DRF surface.
- ❌ No DealWriteup UI at
  M11.6 (deferred — F&I
  handoff needs distinct UX
  pass).
- ❌ No delivery-adapter UI
  (SMS/email drafting +
  sending is deferred; the
  follow-up work-queue is
  view-only aside from
  transitions).
- ❌ No M12 planning at M11.6
  (that lands at M11.7
  closeout).

## What SESSION_119 should do

### Recommended step sequence

1. **Confirm the three §5.f
   recommendations** + record
   in §0.a.

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_11_PLANNING.md`
     §1.8 + §5.f + §7 M11.6.
   - `docs/handoffs/SESSION_118_m11_inc5_be_back.md`
     (previous session).
   - `frontend/src/pages/DealerAiFAndI*`
     (M10.7 first F&I route
     family — mirror the
     shadcn table pattern).
   - `frontend/src/api/fAndIApi.ts`
     (M10.7 API client — mirror
     the fetch pattern).
   - `frontend/src/routes.ts`
     (existing route
     registration).
   - The five new DRF
     endpoints' response shapes
     (each session's handoff
     documents the projection).

3. **Verify starting state**
   (§2 above).

4. **Draft (in order):**
   - `frontend/src/api/salesApi.ts`
     (new module wrapping the
     five M11.1-M11.5 DRF
     surfaces).
   - `frontend/src/pages/DealerAiSalesLeads.tsx`
     (channel filter + list).
   - `frontend/src/pages/DealerAiSalesTestDrives.tsx`.
   - `frontend/src/pages/DealerAiSalesFollowUps.tsx`
     (work-queue with
     complete / skip
     transitions).
   - `frontend/src/pages/DealerAiSalesBeBacks.tsx`.
   - Route registration.
   - ~15 Vitest tests.

5. **Frontend suite
   verification.** Target 51 →
   ~66.

6. **Backend regression
   check.** Baseline should
   still be 3,887.

7. **Ship handoff at
   `docs/handoffs/SESSION_119_m11_inc6_operator_ui.md`.**

8. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M11.7 priority
   (closeout — docs +
   coordinated commit +
   M12 planning skeleton).

## Explicit non-goals for SESSION_119

- ❌ Do NOT ship M11.7 (closeout)
  scope.
- ❌ Do NOT modify M1-M11.5
  backend logic.
- ❌ Do NOT force-push or amend
  the M11.1-M11.5 commits.

## NEXT TASK

Start SESSION_119 with (a)
confirming the three §5.f
recommendations, (b) the read-
first list, (c) starting-state
verification, then (d) build
the new `/dealer-ai-sales/`
route family + four pages +
salesApi client + ~15 Vitest
tests. Frontend baseline
target 51 → ~66. Backend
baseline unchanged. Ship the
M11.6 handoff.

Frontend baseline at
SESSION_119 close: **~66
pass**. Backend baseline:
**3,887 pass** (unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 11
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_11_PLANNING.md`
   (§0.a M11.1 + M11.3 + M11.4
   + M11.5 amendments)
6. `docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_118_m11_inc5_be_back.md`
   (this session's close)
8. `docs/handoffs/SESSION_117_m11_inc4_follow_up_cadence.md`
9. `docs/handoffs/SESSION_116_m11_inc3_deal_writeup.md`
10. `docs/handoffs/SESSION_115_m11_inc2_test_drive.md`
11. `docs/handoffs/SESSION_114_m11_inc1_channel_intake.md`
12. `docs/CAPABILITY_MATRIX.md` §7k
13. `docs/research/SALES_DEPARTMENT_MAPPING.md`

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_118 — M11.5 SHIPPED, backend M11 substrate COMPLETE)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0036`. Test baseline:
  **3,887 pass**, 1 skipped, 0
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
  DatabaseScheduler. **6
  scheduled task families
  registered** (M7.2-M7.5 at
  02:00-05:00 + M11.4 at
  06:00 + M11.5 at 07:00).
- **Milestones shipped:** M1 →
  **M10**. M11 in progress
  (M11.1-M11.5 shipped; M11
  backend substrate COMPLETE;
  M11.6 UI + M11.7 closeout
  remain).
- **DRF admin surface:** **80**
  (77 + M11.5's three BeBack
  endpoints).
- **Frontend operator routes:**
  **11** (unchanged; M11.5
  backend-only; M11.6 will
  add the sales route family).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` +
  `services/leads/` (M11.1) +
  `services/test_drives/`
  (M11.2) + `services/deal_writeups/`
  (M11.3) + `services/follow_ups/`
  (M11.4) + `services/be_backs/`
  (M11.5).
- **Tenancy carriers:** **39**
  (M11.5 added BeBack).
- **Permission classes:** **8**
  (unchanged).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:**
  unchanged.
- **Deterministic rules:**
  unchanged.
- **`CustomerLead.channel`:** 5+1
  vocab (M11.1).
- **Webhook adapter registry:**
  `{"generic": ...}` (M11.1;
  extensible).
- **`TestDrive` FK shape:**
  mandatory both (M11.2).
- **`DealWriteup` handoff:**
  approve → hand_off_to_fandi
  auto-creates M10.1 CA
  (M11.3, idempotent).
- **`FollowUp*` shape:** two-
  entity + 6 fixed templates
  + operator-triggered
  transitions (M11.4).
- **`BeBack` shape:** mandatory
  lead FK (no vehicle FK) +
  4+1 reason vocab + 3-state
  machine + M11.5 no-show
  detector at 07:00 daily
  (grace period configurable
  via `BE_BACK_NO_SHOW_GRACE_HOURS`,
  default 4).
- **Milestone 11 next:** M11.6
  Operator UI (first M11
  frontend increment). New
  `/dealer-ai-sales/` route
  family with four pages
  consuming the M11.1-M11.5
  backend surface. ~15 Vitest
  tests. Frontend baseline
  51 → ~66. Backend baseline
  unchanged.
