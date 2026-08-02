---
state: active
date: 2026-08-02
last_session_shipped: SESSION_145
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
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: planning
next_session: SESSION_146
next_milestone: 18
next_milestone_name: "TBD — user names target at SESSION_146 open"
next_increment: 0
next_increment_name: "M18.0 — Planning refinement + target selection"
---

# Next session — SESSION_146 · Milestone 18 · Increment 0 (M18.0 — Planning refinement + target selection)

> **SESSION_145 shipped all four M17
> increments —** M17.0 planning + M17.1
> backend + M17.2 frontend + **M17.3
> close-out**. Six close-out docs
> (retrospective + capability matrix §7r
> + roadmap flip + planning frontmatter
> flip + M18 skeleton + session-start
> refresh) + coordinated commit landing
> all M17.3 docs. **Milestone 17 — Trial-
> balance materialization + `as_of`
> picker (monthly-close v1) — SHIPPED.**
>
> **M17 close totals:** two new tenant-
> carrier models (`TrialBalanceSnapshot`
> header + `TrialBalanceSnapshotRow`
> child; count 47 → 49). One additive
> migration (`0046` — two `CreateModel` +
> two `AddConstraint`). One new module
> in `services/accounting/`
> (`trial_balance_close.py`) with three
> verbs + `DuplicateTrialBalanceSnapshotError`.
> Three new endpoints (POST freeze +
> GET list + GET detail; DRF admin
> surface 104 → 107). Frontend: new
> `TrialBalanceDatePicker` component +
> extended `AccountingTrialBalancePage`
> in place (Query controls card + Prior
> closes card + inline detail card).
> 37 focused backend tests + 18
> frontend tests. Zero frontend-route
> additions (page extended in place per
> §4 test binding). Zero Celery-beat
> additions (no beat entry per §5.c
> Option A sync-sibling shape). **Six
> §5 decisions confirmed as-recommended
> at M17.0 open** — streak extends to
> **70 planning-time as-recommended
> M5.1 → M17.0 across eight
> consecutive milestones** now (M10 +
> M11 + M12 + M13 + M14 + M15 + M16 +
> M17). Four §0.a implementation-time
> micro-decisions across M17.1 + M17.2
> (dataclass rename, detail URL shape,
> picker default deferral, native
> `<input type="date">` over shadcn
> `Calendar`) do not count against the
> streak per M10 §9. **Permission-
> class count corrected** at M17.1 —
> 7 actual (6 `Is*` + `ReadOnly`), not
> the "8" the M16 retrospective doc
> stated. Zero-drift streak now nine
> consecutive milestones (M10 → M17).
>
> **Backend baseline: 4,326 → 4,363
> pass**, 1 skipped, 0 fail (+37 tests
> at M17.1, zero regressions).
> **Frontend Vitest baseline: 122 →
> 140 pass** (+18 tests at M17.2).
> Migrations `0043`–`0046` (+1 at
> M17.1). Tenancy carriers 47 → **49**.
> DRF admin surface 104 → **107**.
> Frontend operator routes **20**
> (unchanged). Celery-beat task
> families **10** (unchanged).
>
> **SESSION_146 opens M18.0 — planning
> refinement + target selection.** Per
> `MILESTONE_18_PLANNING.md` (draft
> planning skeleton written at M17.3
> close per standing user directive).
> **§5.a is the load-bearing decision**
> — user names the M18 target at
> session open, drawing from the M17
> retrospective §8 unblocked-work list
> + the still-partly-valid M16 §8
> items + the standing question from
> M17 §9 (UI-polish milestone?).

## First thing SESSION_146 must do

### 1. Name the M18 target milestone

`IMPLEMENTATION_ROADMAP.md` §Milestone
sequence ends at Milestone 17. **M18
target is not predetermined** — user
names it at session open based on
operational evidence + business
priority.

Candidate targets drawn from
`MILESTONE_17_RETROSPECTIVE.md` §8 +
`MILESTONE_16_RETROSPECTIVE.md` §8 —
surfaced without recommendation
because target selection is a
business-priority call, not a
technical recommendation:

- **Option A** — M10 F&I chargeback GL
  reversal.
- **Option B** — BhphFee entity +
  late-fee GL posting.
- **Option C** — Deposit / bank
  reconciliation workflow.
- **Option D** — NSF / payment-
  reversal workflow.
- **Option E** — Period-close
  comparison view / audit. Directly
  unblocked by M17 materialization.
- **Option F** — Financial-reports
  substrate (P&L, balance sheet).
  Layers on trial-balance
  materialization.
- **Option G** — CSV / PDF export of
  frozen snapshots.
- **Option H** — Auto-freeze on
  schedule.
- **Option I** — Reopen / unfreeze
  workflow.
- **Option J** — Category-group-aware
  GL mapping for M13.2 detector.
- **Option K** — M14 UX polish (JE
  filters + sidebar nav; `as_of`
  picker portion shipped at M17.2).
- **Option L** — Cost-of-sale
  variance handling.
- **Option M** — Sale-reversal
  workflow.
- **Option N** — BHPH interest accrual
  detector (accrual-basis).
- **Option O** — Non-accounting
  target user names at open based on
  operational evidence not visible in
  M15 / M16 / M17 retrospectives.

**Standing question from M17 §9:**
should M18 be an intentional UI-polish
milestone (M14 shape)? M17's
recommendation was to carry the
question forward but not preemptively
lock M18. If operator evidence +
backlog density name UI polish as the
highest-value slot, M18 becomes the UX
polish milestone (Option K); otherwise
the remaining polish (JE filters +
sidebar nav) can layer as a sub-
increment on a backend milestone that
touches the M14.3 page.

Once the target is confirmed, expand
`MILESTONE_18_PLANNING.md` §1
(business questions) + §5 (load-
bearing decisions) + §7 (sequencing)
into a full memo.

### 2. Verify starting state

- `git status` — clean.
- `git log --oneline -10` — top
  should be the M17.3 close-out
  commit.
- `python3 manage.py test dealer_ai`
  → **4,363 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **140 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

## What M18.0 delivers

Per `MILESTONE_18_PLANNING.md` §5
M18.0:

- Full expansion of the planning
  skeleton written at M17.3.
- User names the M18 target milestone
  (§5.a).
- Additional §5 decisions surface once
  target is confirmed (§5.b-§5.f
  expected — historical §5 counts have
  been 6 for M10 / M11 / M12 / M13 /
  M14 / M15 / M16 / M17).
- §7 sequencing lands after §5
  decisions are locked.
- §0.a change log records the target
  selection + all §5 confirmations.

**No code at M18.0.** Planning-only
session. Backend baseline stays at
4,363 pass. Frontend Vitest stays at
140.

## What SESSION_146 should do

### Recommended step sequence

1. **Confirm the M18 target with the
   user** (§1 above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_18_PLANNING.md`
     (this session's expansion
     target).
   - `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
     §6 (six lessons carry into M18)
     + §8 (unblocked work) + §9
     (standing question).
   - `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
     §8 (partly still valid).
   - `docs/handoffs/SESSION_145_m17_inc3_close.md`
     (previous session's close).
   - `docs/CAPABILITY_MATRIX.md` §7r
     (M17 shipped surface).
   - Target-specific research doc
     (per the confirmed §5.a option).

3. **Verify starting state** (§2
   above).

4. **Draft §1 (business questions) +
   §5 (load-bearing decisions) + §7
   (sequencing)** in
   `MILESTONE_18_PLANNING.md`.

5. **Ship handoff at
   `docs/handoffs/SESSION_146_m18_inc0_planning.md`.**

6. **Overwrite
   `00-START-NEXT-SESSION.md`** with
   M18.1 priority (first implementation
   increment for the confirmed target).

## Explicit non-goals for SESSION_146

- ❌ Do NOT ship M18.1+ code.
- ❌ Do NOT modify M1-M17 business
  logic.
- ❌ Do NOT force-push or amend any
  earlier commits.

## NEXT TASK

Start SESSION_146 with (a) naming the
M18 target with the user (candidates
in §1 above; user picks based on
operational evidence + business
priority + the M17 §9 UI-polish
standing question), (b) the read-
first list, (c) starting-state
verification, then (d) expanding
`MILESTONE_18_PLANNING.md` §1 + §5 +
§7 into a full memo. Ship the M18.0
handoff.

Backend baseline at SESSION_146
close: **4,363 pass** (unchanged —
planning-only). Frontend baseline:
**140 pass** (unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_145_m17_inc3_close.md`
   (this session's close)
8. `docs/CAPABILITY_MATRIX.md` §7r
9. Target-specific research (per
   §5.a confirmed at SESSION_146
   open).

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_145 — M17 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0046`.
  Test baseline: **4,363 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` + `vite
  build` clean. **Vitest baseline:
  140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 + `django-celery-beat`
  2.8.1 DatabaseScheduler. **10
  scheduled task families
  registered** (unchanged at M17 —
  no beat entry per §5.c Option A).
  Next open slot for a future
  detector is 12:00.
- **Milestones shipped:** M1 →
  **M17** (SESSION_145 close). M18
  planning drafted.
- **DRF admin surface:** **107**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) + five
  M11 packages + seven M12 packages
  + **`services/accounting/` (seven
  modules: `default_coa.py` +
  `journal.py` + `snapshot.py` +
  `vehicle_cost.py` + `sale_booking.py`
  + `bhph_payment.py` +
  `trial_balance_close.py`)**.
- **Frontend accounting surface:**
  `frontend/src/lib/accountingApi.ts`
  with 8 fetchers + 2 mutators (M13
  + M14 + M17 combined) + four page
  components + `TrialBalanceDatePicker`
  component.
- **Tenancy carriers:** **49**
  (unchanged since M17.1).
- **Permission classes:** **7
  actual** (`IsAdvisorForSlug`,
  `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`,
  `IsDealerOwnerAtActiveDealership`,
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  `ReadOnly`). **Zero-drift streak:
  nine consecutive milestones**
  (M10 → M17). Prior narrative doc
  "8" was a miscount — corrected at
  M17.1 handoff + M17
  retrospective §4.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M17 has no
  LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 18 next:** M18.0
  planning refinement + target
  selection. User names target at
  session open from the M17 §8 +
  M16 §8 unblocked-work lists +
  the M17 §9 UI-polish standing
  question. M18.1 implementation
  deferred to post-planning
  session.
