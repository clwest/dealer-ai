---
state: active
date: 2026-08-02
last_session_shipped: SESSION_144
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
milestone_17_status: planning
next_session: SESSION_145
next_milestone: 17
next_milestone_name: "TBD — user names target at SESSION_145 open"
next_increment: 0
next_increment_name: "M17.0 — Planning refinement + target selection"
---

# Next session — SESSION_145 · Milestone 17 · Increment 0 (M17.0 — Planning refinement + target selection)

> **SESSION_144 shipped M16.2 —**
> six close-out docs (retrospective +
> capability matrix §7q + roadmap
> §Milestone 16 SHIPPED entry added +
> planning frontmatter flip +
> session-start refresh + M17
> planning skeleton) + one coordinated
> commit. **Milestone 16 — M12 BHPH
> payment GL post — SHIPPED.**
>
> **M16 close totals:** one new
> module in `services/accounting/`
> (`bhph_payment.py`) with three
> verbs. Extended `services/
> accounting/tasks.py` + `__init__.py`
> + `settings.py` beat schedule. One
> additive migration
> (`0045_m161_bhph_payment_posted_at`
> — one AddField). One model
> field addition. 30 focused tests.
> Zero new endpoints. Zero permission-
> class drift (eight consecutive
> milestones now). Zero frontend
> changes. **Six planning-time §5
> decisions confirmed as-recommended
> at M16.0 open** — streak extends
> to **64 planning-time as-
> recommended M5.1 → M16.0** across
> **seven consecutive milestones now**
> (M10 + M11 + M12 + M13 + M14 +
> M15 + M16). Five §0.a
> implementation-time micro-decisions
> at M16.1 also all as-recommended
> (do not count against streak per
> M10 §9).
>
> **Backend baseline: 4,326 pass, 1
> skipped, 0 fail** (+30 tests
> across M16, 0 regressions).
> **Frontend Vitest baseline: 122
> pass** (unchanged — no frontend at
> M16). Migrations `0043`–`0045`
> (+1 at M16.1). Tenancy carriers
> 47 (unchanged). DRF admin surface
> 104 (unchanged). Frontend operator
> routes 20 (unchanged). Celery-beat
> task families 9 → **10** (new
> bhph-payment daily entry at 11:00).
>
> **SESSION_145 opens M17.0 —
> planning refinement + target
> selection.** Per
> `MILESTONE_17_PLANNING.md` (draft
> planning skeleton written at M16.2
> close per standing user directive).
> **§5.a is the load-bearing
> decision** — user names the M17
> target at session open, drawing
> from the M16 retrospective §8
> unblocked-work list + the still-
> valid M15 §8 items.

## First thing SESSION_145 must do

### 1. Name the M17 target milestone

`IMPLEMENTATION_ROADMAP.md`
§Milestone sequence ends at
Milestone 16. **M17 target is not
predetermined** — user names it at
session open based on operational
evidence + business priority.

Candidate targets drawn from
`MILESTONE_16_RETROSPECTIVE.md` §8
+ `MILESTONE_15_RETROSPECTIVE.md`
§8 — surfaced without recommendation
because target selection is a
business-priority call, not a
technical recommendation:

- **Option A** — M10 F&I chargeback
  GL reversal. Both patterns proven
  now (M15 sync-sibling + M16
  detector). Chargeback is likely
  sync-sibling per M15 pattern.
  `reverse_journal_entry` ready.
- **Option B** — BhphFee entity +
  late-fee GL posting. M16.1's
  `UnexpectedBhphPaymentFeesError`
  guard makes the contract explicit;
  BhphFee milestone extends
  `post_bhph_payment_journal` with
  a fee-income line + removes the
  guard.
- **Option C** — Deposit / bank
  reconciliation workflow. M16's
  phantom 100000 Cash on Hand
  balance surfaces the operator
  need. Method-aware fund-flow
  routing is the substrate half.
- **Option D** — NSF / payment-
  reversal workflow. ACH failures
  + returned payments need
  operational contract + GL wiring
  via `reverse_journal_entry`.
- **Option E** — Trial-balance
  materialization + `as_of`
  picker (monthly-close v1).
  **Bundled at M16.2 close** —
  entity + picker ship together
  as the smallest complete
  operator-usable slice of
  monthly close. M16's BHPH
  activity now makes period-
  over-period reports meaningful.
  Likely 4-5 increments given
  mixed backend+frontend scope.
- **Option F** — Category-group-
  aware GL mapping for the M13.2
  detector. Miscoding evidence
  now accumulates across three
  daily-posting streams.
- **Option G** — M14 UX polish
  (JE filters + sidebar nav;
  `as_of` picker moved to E per
  M16.2-close bundling). Operator
  evidence accumulates faster
  post-M16.
- **Option H** — Cost-of-sale
  variance handling. Post-sale
  VehicleCost phantom balances
  more visible now.
- **Option I** — Sale-reversal
  workflow. Operational contract
  needed.
- **Option J** — BHPH interest
  accrual detector (accrual-
  basis). Cash-basis at M16;
  accrual for month-end close.
- **Option K** — Non-accounting
  target user names at open
  based on operational evidence
  not visible in M15 / M16
  retrospectives.

Once the target is confirmed,
expand `MILESTONE_17_PLANNING.md`
§1 (business questions) + §5
(load-bearing decisions) + §7
(sequencing) into a full memo.

### 2. Verify starting state

- `git status` — clean (M16.2
  commit landed at SESSION_144
  close; user authorization on
  push).
- `git log --oneline -5` — top
  should be a coordinated M16.2
  docs commit.
- `python3 manage.py test dealer_ai`
  → **4,326 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **122 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

## What M17.0 delivers

Per `MILESTONE_17_PLANNING.md` §5
M17.0:

- Full expansion of the planning
  skeleton written at M16.2.
- User names the M17 target
  milestone (§5.a).
- Additional §5 decisions surface
  once target is confirmed (§5.b-
  §5.f expected — historical §5
  counts have been 6 for M10 /
  M11 / M12 / M13 / M14 / M15 /
  M16).
- §7 sequencing lands after §5
  decisions are locked.
- §0.a change log records the
  target selection + all §5
  confirmations.

**No code at M17.0.** Planning-
only session. Backend baseline
stays at 4,326 pass. Frontend
Vitest stays at 122.

## What SESSION_145 should do

### Recommended step sequence

1. **Confirm the M17 target with
   the user** (§1 above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_17_PLANNING.md`
     (this session's expansion
     target).
   - `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
     §6 (six lessons carry into
     M17) + §8 (unblocked work).
   - `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
     §8 (M15 unblocked work —
     still mostly valid after
     M16).
   - `docs/handoffs/SESSION_144_m16_close.md`
     (previous session).
   - `docs/CAPABILITY_MATRIX.md`
     §7q (M16 shipped surface).
   - Target-specific research doc
     (per the confirmed §5.a
     option).

3. **Verify starting state** (§2
   above).

4. **Draft §1 (business
   questions) + §5 (load-bearing
   decisions) + §7 (sequencing)**
   in `MILESTONE_17_PLANNING.md`.

5. **Ship handoff at
   `docs/handoffs/SESSION_145_m17_inc0_planning.md`.**

6. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M17.1 priority (first
   implementation increment for
   the confirmed target).

## Explicit non-goals for SESSION_145

- ❌ Do NOT ship M17.1+ code.
- ❌ Do NOT modify M1-M16
  business logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_145 with (a) naming
the M17 target with the user
(candidates in §1 above; user
picks based on operational
evidence + business priority),
(b) the read-first list, (c)
starting-state verification, then
(d) expanding
`MILESTONE_17_PLANNING.md` §1 +
§5 + §7 into a full memo. Ship
the M17.0 handoff.

Backend baseline at SESSION_145
close: **4,326 pass** (unchanged
— planning-only). Frontend
baseline: **122 pass**
(unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
6. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_144_m16_close.md`
   (this session's close)
8. `docs/handoffs/SESSION_143_m16_inc1_backend.md`
9. `docs/CAPABILITY_MATRIX.md` §7q
10. Target-specific research
    (per §5.a confirmed at
    SESSION_145 open).

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_144 — M16 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0045`. Test baseline:
  **4,326 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 122 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered** (M16.1 added the
  11:00 BHPH-payment entry;
  next open slot: 12:00 for a
  future M17+ detector if
  picked).
- **Milestones shipped:** M1 →
  **M16** (SESSION_144 close).
  M17 planning drafted.
- **DRF admin surface:** **104**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + **`services/
  accounting/` (six modules:
  `default_coa.py` + `journal.py`
  + `snapshot.py` + `vehicle_
  cost.py` + `sale_booking.py`
  + `bhph_payment.py`)**.
- **Frontend accounting
  surface:** `frontend/src/lib/
  accountingApi.ts` with 4
  fetchers + 1 mutator + three
  page components (unchanged at
  M16 — backend-only per §5.f
  Option A).
- **Tenancy carriers:** **47**
  (unchanged at M16).
- **Permission classes:** **8**
  (unchanged — zero-drift
  streak extends to **eight
  consecutive milestones** now:
  M10 + M11 + M12 + M13 + M14
  + M15 + M16).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M16 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 17 next:** M17.0
  planning refinement + target
  selection. User names target
  at session open from the M16
  §8 unblocked-work list. M17.1
  implementation deferred to
  post-planning session.
