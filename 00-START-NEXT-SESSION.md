---
state: active
date: 2026-08-02
last_session_shipped: SESSION_152
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
milestone_18_status: shipped
milestone_19_status: planning
next_session: SESSION_153
next_milestone: 19
next_milestone_name: "TBD — user names target at SESSION_153 open"
next_increment: 0
next_increment_name: "M19.0 — Planning refinement + target selection"
---

# Next session — SESSION_153 · Milestone 19 · Increment 0 (M19.0 — Planning refinement + target selection)

> **SESSION_152 shipped M18.6 —** the
> Milestone 18 close-out. Six close-out
> artifacts + one coordinated commit
> landing all M18.6 docs together.
> **Milestone 18 — Demo Store Simulation
> + Pilot Validation Readiness —
> SHIPPED.**
>
> **M18 close totals:** three archetype
> builders (retail_subprime +
> floor_planned + bhph) + 13 daily
> briefs + POST feedback endpoint +
> CSV exporter. **175 backend tests
> across all M18 increments** (M17
> close 4,363 → M18 close **4,538
> pass**). One new tenant carrier
> (`TesterFeedback`; 49 → **50**).
> One additive migration (`0047_m181_
> demo_store_substrate.py`). Two
> additive `Dealership` columns
> (`is_demo` + `demo_archetype`). One
> new endpoint (POST
> `/admin/demo-store/feedback/`; DRF
> admin surface 107 → **108**). Zero
> new operator routes. Zero new
> permission classes — **zero-drift
> streak fourteen consecutive
> milestones** (M10 → M18.5).
> Seven §5 decisions confirmed as-
> recommended at M18.0 open; five
> §0.a implementation-time micro-
> decisions across M18.1 + M18.2 do
> not count against the streak per
> M10 §9.
>
> **Backend baseline: 4,538 pass**,
> 1 skipped, 0 fail. **Frontend
> Vitest baseline: 140 pass**. All
> unchanged since M18.5 (M18.6 is
> docs-only). Migrations
> `0043`–`0047`. Tenancy carriers
> **50**. DRF admin surface **108**.
> Frontend operator routes 20.
> Permission classes 7. Celery-beat
> task families 10.
>
> **SESSION_153 opens M19.0 —
> planning refinement + target
> selection.** Per
> `MILESTONE_19_PLANNING.md` (draft
> skeleton written at M18.6 close per
> standing user directive). **§5.a is
> the load-bearing decision** — user
> names the M19 target at session
> open. **Distinctive at M19.0:**
> if Chris has run tester sessions
> using the M18 demo stores + daily
> briefs, the M18.5 CSV export
> becomes primary planning input.

## First thing SESSION_153 must do

### 1. Name the M19 target milestone

`IMPLEMENTATION_ROADMAP.md` §Milestone
sequence ends at Milestone 18. **M19
target is not predetermined** — user
names it at session open based on
operational evidence + business
priority + **tester feedback if any
has landed via the M18 pilot
sessions**.

Candidate targets drawn from
`MILESTONE_18_RETROSPECTIVE.md` §8
+ `MILESTONE_17_RETROSPECTIVE.md` §8
(still-valid unblocked-work items):

- **Option T — Process tester
  feedback.** **Primary candidate if
  M18-shipped demo stores have been
  used by real testers.** Scope
  depends on volume + quality of
  feedback captured via the M18.5
  POST endpoint + CSV export.
- **Option U — Hosted-demo
  substrate.** Public self-serve
  demo signup + tester-tracking
  dashboard. Deferred at M18 §3.
- **Option V — Pilot-customer
  onboarding.** Real-data onboarding
  for testers who convert. Deferred
  at M18 §3.
- **Option A** — M10 F&I chargeback
  GL reversal.
- **Option B** — BhphFee entity +
  late-fee GL posting.
- **Option C** — Deposit / bank
  reconciliation workflow.
- **Option D** — NSF / payment-
  reversal workflow.
- **Option E** — Period-close
  comparison view / audit.
- **Option F** — Financial-reports
  substrate (P&L, balance sheet).
- **Option G** — CSV / PDF export of
  frozen snapshots.
- **Option H** — Auto-freeze on
  schedule.
- **Option I** — Reopen / unfreeze
  workflow.
- **Option J** — Category-group-
  aware GL mapping for M13.2
  detector.
- **Option K** — M14 UX polish
  (JE filters + sidebar nav).
- **Option L** — Cost-of-sale
  variance handling.
- **Option M** — Sale-reversal
  workflow.
- **Option N** — BHPH interest
  accrual detector (accrual-basis).
- **Option O** — Non-accounting
  target user names at open based
  on operational evidence not
  visible in prior retrospectives.

**M18 §9 standing question:**
recommendation was to carry the
question forward but NOT preemptively
lock M19 as tester-feedback
processing. Target selection at
M19.0 should follow the standard
business-priority pattern. If
tester feedback has landed with
volume and quality that names
Option T, M19 becomes T. If not,
target selection falls back to
business-priority ranking from the
candidate list.

Once the target is confirmed,
expand `MILESTONE_19_PLANNING.md`
§1 + §5 + §7 into a full memo.

### 2. Verify starting state

- `git status` — clean.
- `git log --oneline -10` — top
  should be the M18.6 close-out
  commit.
- `python3 manage.py test dealer_ai`
  → **4,538 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **140 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

## What M19.0 delivers

Per `MILESTONE_19_PLANNING.md` §5
M19.0:

- Full expansion of the planning
  skeleton written at M18.6.
- User names the M19 target
  milestone (§5.a).
- Additional §5 decisions surface
  once target is confirmed
  (§5.b-§5.f expected — historical
  §5 counts have been 6 for M10 /
  M11 / M12 / M13 / M14 / M15 /
  M16 / M17 and 7 for M18).
- §7 sequencing lands after §5
  decisions are locked.
- §0.a change log records the
  target selection + all §5
  confirmations.

**No code at M19.0.** Planning-
only session. Backend baseline
stays at 4,538 pass. Frontend
Vitest stays at 140.

## What SESSION_153 should do

### Recommended step sequence

1. **Ask about tester sessions.** Has
   Chris used the M18 demo stores +
   daily briefs with real operators
   since M18 close? If yes: pull the
   M18.5 CSV export as input. If no:
   note this in §0.a and proceed to
   business-priority ranking.

2. **Confirm the M19 target with
   the user** (§1 above).

3. **Read first (in order):**
   - `docs/roadmap/MILESTONE_19_PLANNING.md`
     (this session's expansion
     target).
   - `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
     §6 (seven lessons carry into
     M19) + §8 (M18 unblocks) + §9
     (standing question).
   - `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
     §8 (M17 unblocked work —
     still mostly valid after M18).
   - `docs/handoffs/SESSION_152_m18_inc6_close.md`
     (previous session).
   - `docs/CAPABILITY_MATRIX.md` §7s
     (M18 shipped surface).
   - Target-specific research /
     tester-feedback CSV per §5.a
     confirmed at open.

4. **Verify starting state** (§2
   above).

5. **Draft §1 (business questions)
   + §5 (load-bearing decisions) +
   §7 (sequencing)** in
   `MILESTONE_19_PLANNING.md`.

6. **Ship handoff at
   `docs/handoffs/SESSION_153_m19_inc0_planning.md`.**

7. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M19.1 priority (first
   implementation increment for
   the confirmed target).

## Explicit non-goals for SESSION_153

- ❌ Do NOT ship M19.1+ code.
- ❌ Do NOT modify M1-M18 business
  logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_153 with (a)
checking whether tester feedback
has landed since M18 close and
if so pulling the M18.5 CSV
export as planning input, (b)
naming the M19 target with the
user (candidates in §1 above),
(c) the read-first list, (d)
starting-state verification, then
(e) expanding
`MILESTONE_19_PLANNING.md` §1 +
§5 + §7 into a full memo. Ship
the M19.0 handoff.

Backend baseline at SESSION_153
close: **4,538 pass** (unchanged
— planning-only). Frontend
baseline: **140 pass**
(unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
6. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_152_m18_inc6_close.md`
   (this session's close)
8. `docs/CAPABILITY_MATRIX.md` §7s
9. **Tester feedback CSV** (from
   M18.5 `demo_store
   export_feedback`) if any
   tester sessions have
   happened.
10. Target-specific research (per
    §5.a confirmed at SESSION_153
    open).

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_152 — M18 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0047`. Test baseline:
  **4,538 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M18** (SESSION_152 close).
  M19 planning drafted.
- **DRF admin surface:** **108**
  endpoints (feedback POST
  landed at M18.5).
- **Frontend operator routes:**
  **20** (unchanged through M18
  — testers use existing routes).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/accounting/`
  (seven modules) +
  **`services/demo_store/` (ten
  modules including briefs
  package)**.
- **Frontend accounting surface:**
  unchanged from M17.
- **Tenancy carriers:** **50**
  (unchanged since M18.1).
- **Permission classes:** **7
  actual** — **zero-drift streak
  fourteen consecutive milestones**
  (M10 → M18.5).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M18 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 19 next:** M19.0
  planning refinement + target
  selection. User names target
  at session open — with tester
  feedback (if it exists) as
  primary planning input.
