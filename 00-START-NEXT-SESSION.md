---
state: active
date: 2026-08-02
last_session_shipped: SESSION_141
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
milestone_16_status: planning
next_session: SESSION_142
next_milestone: 16
next_milestone_name: "TBD — user names target at SESSION_142 open"
next_increment: 0
next_increment_name: "M16.0 — Planning refinement + target selection"
---

# Next session — SESSION_142 · Milestone 16 · Increment 0 (M16.0 — Planning refinement + target selection)

> **SESSION_141 shipped M15.2 —**
> six close-out docs (retrospective +
> capability matrix §7p + roadmap
> §Milestone 15 SHIPPED entry added +
> planning frontmatter flip +
> session-start refresh + M16 planning
> skeleton) + one coordinated commit.
> **Milestone 15 — M9 sale-booking
> GL post — SHIPPED.**
>
> **M15 close totals:** one new
> module in `services/accounting/`
> (`sale_booking.py`) with one atomic
> sibling-service verb. Extended
> `record_sale` + `views_sale.py` +
> `_auth_helpers.make_dealership`.
> Patched `test_m9_sale_computation.py`
> inline. Zero new backend entities.
> Zero migrations. Zero new endpoints.
> Zero permission-class drift (seven
> consecutive milestones now). Zero
> frontend changes. **Six planning-
> time §5 decisions confirmed as-
> recommended at M15.0 open** —
> streak extends to **58 planning-
> time as-recommended M5.1 → M15.0**
> across six consecutive milestones
> (M10 + M11 + M12 + M13 + M14 +
> M15). Nine §0.a implementation-
> time micro-decisions at M15.1 also
> all as-recommended (do not count
> against streak per M10 §9).
>
> **Backend baseline: 4,296 pass, 1
> skipped, 0 fail** (+19 tests
> across M15, 0 regressions).
> **Frontend Vitest baseline: 122
> pass** (unchanged — no frontend at
> M15). Migrations `0043`–`0044`
> (unchanged). Tenancy carriers 47
> (unchanged). DRF admin surface 104
> (unchanged). Frontend operator
> routes 20 (unchanged).
>
> **SESSION_142 opens M16.0 —
> planning refinement + target
> selection.** Per
> `MILESTONE_16_PLANNING.md` (draft
> planning skeleton written at M15.2
> close per standing user directive).
> **§5.a is the load-bearing
> decision** — user names the M16
> target at session open, drawing
> from the M15 retrospective §8
> unblocked-work list + the still-
> valid M14 §8 items.

## First thing SESSION_142 must do

### 1. Name the M16 target milestone

`IMPLEMENTATION_ROADMAP.md`
§Milestone sequence ends at
Milestone 15. **M16 target is not
predetermined** — user names it at
session open based on operational
evidence + business priority.

Candidate targets drawn from
`MILESTONE_15_RETROSPECTIVE.md` §8
+ `MILESTONE_14_RETROSPECTIVE.md`
§8 — surfaced without recommendation
because target selection is a
business-priority call, not a
technical recommendation:

- **Option A** — M10 F&I chargeback
  GL reversal. Substrate ready;
  M15 proved out the sync-sibling
  pattern that M10 chargeback
  would follow. Every recorded
  chargeback posts a matching
  reversal JournalEntry via
  `services/accounting/reverse_journal_entry`.
- **Option B** — M12 BHPH payment
  GL post. Detector at 11:00
  project-time daily (next open
  slot after M13.2 10:00). Every
  unposted BhphPayment produces a
  matching journal entry. Detector-
  half of the M13 §5.d Option C
  hybrid; M15 shipped the sync
  half.
- **Option C** — Trial-balance
  materialization + monthly close
  workflow. `TrialBalanceSnapshot`
  entity + freeze verb over the
  M13.3 pure recompute aggregator.
  The M14 trial-balance page could
  grow an `as_of` picker as part
  of this.
- **Option D** — Category-group-
  aware GL mapping for the M13.2
  detector. Now that M14.4's
  failure card gives operators
  visibility into detector misses
  AND M15 sales activity
  accumulates in Recon WIP,
  miscoding evidence is available.
- **Option E** — M14 UX polish
  (journal-entry list filters +
  `as_of` picker + sidebar nav
  entry for accounting). Layers
  atop the M14 shipped surface as
  operator evidence surfaces the
  need — and M15 sale-booking
  activity now makes that operator
  evidence real.
- **Option F** — Cost-of-sale
  variance handling. Post-sale
  VehicleCost rows currently
  create phantom Recon WIP
  balances for sold vehicles; a
  category-aware mapping or a
  redirect-to-COGS approach clears
  the phantoms.
- **Option G** — Sale-reversal
  workflow. Operational contract
  definition + GL wiring via
  `reverse_journal_entry`.
- **Option H** — Non-accounting
  target user names at open based
  on operational evidence not
  visible in the M15 / M14
  retrospectives.

Once the target is confirmed,
expand `MILESTONE_16_PLANNING.md`
§1 (business questions) + §5
(load-bearing decisions) + §7
(sequencing) into a full memo.

### 2. Verify starting state

- `git status` — clean (M15.2
  commit landed at SESSION_141
  close; user authorization on
  push).
- `git log --oneline -5` — top
  should be a coordinated M15.2
  docs commit.
- `git log origin/main..HEAD
  --oneline` — three commits
  ahead (M15.0 + M15.1 + M15.2)
  pending push authorization.
- `python3 manage.py test dealer_ai`
  → **4,296 pass, 1 skipped, 0
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

## What M16.0 delivers

Per `MILESTONE_16_PLANNING.md` §5
M16.0:

- Full expansion of the planning
  skeleton written at M15.2.
- User names the M16 target
  milestone (§5.a).
- Additional §5 decisions surface
  once target is confirmed (§5.b-
  §5.f expected — historical §5
  counts have been 6 for M10 /
  M11 / M12 / M13 / M14 / M15).
- §7 sequencing lands after §5
  decisions are locked.
- §0.a change log records the
  target selection + all §5
  confirmations.

**No code at M16.0.** Planning-
only session. Backend baseline
stays at 4,296 pass. Frontend
Vitest stays at 122.

## What SESSION_142 should do

### Recommended step sequence

1. **Confirm the M16 target with
   the user** (§1 above).

2. **Read first (in order):**
   - `docs/roadmap/MILESTONE_16_PLANNING.md`
     (this session's expansion
     target).
   - `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
     §6 (eight lessons carry into
     M16) + §8 (unblocked work).
   - `docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`
     §8 (M14 unblocked work —
     still mostly valid after M15).
   - `docs/handoffs/SESSION_141_m15_close.md`
     (previous session).
   - `docs/CAPABILITY_MATRIX.md`
     §7p (M15 shipped surface).
   - Target-specific research doc
     (per the confirmed §5.a
     option).

3. **Verify starting state** (§2
   above).

4. **Draft §1 (business
   questions) + §5 (load-bearing
   decisions) + §7 (sequencing)**
   in `MILESTONE_16_PLANNING.md`.

5. **Ship handoff at
   `docs/handoffs/SESSION_142_m16_inc0_planning.md`.**

6. **Overwrite
   `00-START-NEXT-SESSION.md`**
   with M16.1 priority (first
   implementation increment for
   the confirmed target).

## Explicit non-goals for SESSION_142

- ❌ Do NOT ship M16.1+ code.
- ❌ Do NOT modify M1-M15
  business logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_142 with (a) naming
the M16 target with the user
(candidates in §1 above; user
picks based on operational
evidence + business priority),
(b) the read-first list, (c)
starting-state verification, then
(d) expanding
`MILESTONE_16_PLANNING.md` §1 +
§5 + §7 into a full memo. Ship
the M16.0 handoff.

Backend baseline at SESSION_142
close: **4,296 pass** (unchanged
— planning-only). Frontend
baseline: **122 pass**
(unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_16_PLANNING.md`
6. `docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_141_m15_close.md`
   (this session's close)
8. `docs/handoffs/SESSION_140_m15_inc1_backend.md`
9. `docs/CAPABILITY_MATRIX.md` §7p
10. Target-specific research
    (per §5.a confirmed at
    SESSION_142 open).

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_141 — M15 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0044`. Test baseline:
  **4,296 pass**, 1 skipped, 0
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
  DatabaseScheduler. **9
  scheduled task families
  registered** (unchanged at
  M15 — sale booking is
  operator intent, not detector-
  shaped). Next available slot:
  11:00 (open for M12 BHPH
  payment detector if picked at
  M16.0).
- **Milestones shipped:** M1 →
  **M15** (SESSION_141 close).
  M16 planning drafted.
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
  accounting/` (five modules:
  `default_coa.py` +
  `journal.py` + `snapshot.py`
  + `vehicle_cost.py` + new
  `sale_booking.py`)**.
- **Frontend accounting
  surface:** `frontend/src/lib/
  accountingApi.ts` with 4
  fetchers + 1 mutator + three
  page components (unchanged at
  M15 — M15 is backend-only).
- **Tenancy carriers:** **47**
  (unchanged at M15).
- **Permission classes:** **8**
  (unchanged — zero-drift
  streak extends to seven
  consecutive milestones now:
  M10 + M11 + M12 + M13 + M14
  + M15).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M15 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 16 next:** M16.0
  planning refinement + target
  selection. User names target
  at session open from the M15
  §8 unblocked-work list. M16.1
  implementation deferred to
  post-planning session.
