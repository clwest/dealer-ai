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
milestone_17_status: in-progress
next_session: SESSION_146
next_milestone: 17
next_milestone_name: "Trial-balance materialization + as_of picker (monthly-close v1)"
next_increment: 3
next_increment_name: "M17.3 — Close-out (retrospective + capability matrix + roadmap flip + M18 skeleton)"
---

# Next session — SESSION_146 · Milestone 17 · Increment 3 (M17.3 — Close-out)

> **SESSION_145 shipped THREE code
> increments** (M17.0 planning + M17.1 backend
> + M17.2 frontend) per user direction
> "continue" after each landed. Commits:
> `404605e` M17.0 planning + `f217e0d` M17.1
> backend + `bedc615` M17.1 docs + `4235137`
> M17.2 frontend. **M17.3 close-out remains
> for SESSION_146.**
>
> **Backend baseline: 4,363 pass**, 1
> skipped, 0 fail (+37 tests at M17.1).
> **Frontend Vitest baseline: 140 pass**
> (+18 tests at M17.2). Migrations
> `0043`–`0046` (+1 at M17.1). Tenancy
> carriers 47 → **49**. DRF admin surface
> 104 → **107**. Frontend operator routes
> 20 (unchanged — extended M14.2 page in
> place). Permission classes 7 (unchanged
> — **zero-drift streak nine consecutive
> milestones**: M10 + M11 + M12 + M13 +
> M14 + M15 + M16 + M17.1 + M17.2 no
> class change). Celery-beat task
> families 10 (unchanged — no beat entry
> per §5.c Option A).
>
> **SESSION_146 opens M17.3 — close-out
> docs.** Per `MILESTONE_17_PLANNING.md`
> §7 M17.3. Documentation-only per
> M10.8 / M11.7 / M12.8 / M13.4 / M14.5 /
> M15.2 / M16.2 precedent.

## First thing SESSION_146 must do

### 1. Verify starting state

- `git status` — clean (M17.2 commit
  `4235137` landed at SESSION_145 close).
- `git log --oneline -6` — top four
  should be `4235137` (M17.2 frontend),
  `bedc615` (M17.1 docs), `f217e0d`
  (M17.1 backend), `404605e` (M17.0
  planning).
- `python3 manage.py test dealer_ai`
  → **4,363 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` → **140
  pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_17_PLANNING.md`
  (frontmatter about to flip to
  shipped; §7 M17.3 scope).
- `docs/handoffs/SESSION_145_m17_inc0_planning.md`
- `docs/handoffs/SESSION_145_m17_inc1_backend.md`
- `docs/handoffs/SESSION_145_m17_inc2_frontend.md`
- `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
  (structure template for the M17
  retrospective).
- `docs/CAPABILITY_MATRIX.md` (add
  §7r for the M17 shipped surface).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  §Milestone 17 (add SHIPPED entry).

## What M17.3 delivers

Per `MILESTONE_17_PLANNING.md` §7
M17.3:

### Retrospective

Write
`docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
following the M16 retrospective
structure:

- §1 Planned scope (§5.a Option E + §5.b-
  §5.f + 4-increment sequencing).
- §2 What actually shipped (M17.0 +
  M17.1 + M17.2 + M17.3 with commit
  hashes).
- §3 Deferrals (12 M17-specific + 5
  universal = 17 per planning §3;
  verify each has a clear re-entry
  path).
- §4 Deviations (any?) — one to record:
  M14.2 empty-state copy tweak ("No
  postings yet" → "No postings through
  this date"). Also the permission-
  class miscount correction (7 actual,
  not 8) from M17.1 handoff.
- §5 Compatibility with existing
  surface (M1-M16 endpoints returning
  same shape; enumerate).
- §6 Lessons — expect ~6 per pattern:
  monthly-close v1 shape, bundled
  entity+picker, native date input over
  shadcn Calendar as a §0.a pattern,
  IntegrityError → DomainError re-raise
  pattern in freeze verb, per-account
  frozen row shape as immutable audit,
  in-place page extension avoiding
  route bloat.
- §7 Streak update — 70 planning-time
  as-recommended M5.1 → M17.0
  (unchanged; §5-decision streak). Four
  §0.a implementation-time micro-
  decisions across M17.1 + M17.2
  (dataclass rename, detail URL shape,
  picker default deferral, native date
  input) do NOT count against streak
  per M10 §9.
- §8 What M17 unblocks for M18+ —
  standing question about UI-polish
  milestone at M18 or M19 per M17
  planning §M16.2-close refinement.

### Capability matrix

Add `docs/CAPABILITY_MATRIX.md` §7r
describing the M17 trial-balance
materialization + `as_of` picker
surface. Follow §7q (M16) as template.

### Implementation roadmap

Add
`docs/roadmap/IMPLEMENTATION_ROADMAP.md`
§Milestone 17 SHIPPED entry. Bump the
sequence to end at Milestone 17.

### Planning doc flip

Frontmatter update on
`docs/roadmap/MILESTONE_17_PLANNING.md`:
`status: active` → `status: shipped`.

### M18 skeleton

Write
`docs/roadmap/MILESTONE_18_PLANNING.md`
skeleton from the M17 §8 unblocked-
work list per M10.8 / M11.7 / M12.8 /
M13.4 / M14.5 / M15.2 / M16.2
precedent. Include:

- §0 engineering practices to preserve.
- §1 candidate targets — include
  Options A / B / C / D / F / G / H /
  I / J from the M17 planning §1
  (still-valid unblocked work).
- **§1 Option G — M14 UX polish**
  becomes a stronger candidate at
  M18 per the M17-close standing
  question (M14 shape milestone to
  batch-consume UI polish +
  operator-evidence gaps from M15 +
  M16 + M17 surfaces).
- §5 skeleton with `[NEEDS-DECISION-
  BEFORE-M18.0]` §5.a target-selection
  placeholder.
- §7 4-increment sequencing template.

### Session start refresh

Overwrite `00-START-NEXT-SESSION.md`
with M18.0 priority.

### Coordinated commit

Land all M17.3 docs together in one
coordinated commit per M10.8 / M11.7
/ M12.8 / M13.4 / M14.5 / M15.2 /
M16.2 precedent.

## Explicit non-goals for SESSION_146

- ❌ Do NOT ship M18.0 planning
  expansion (skeleton only).
- ❌ Do NOT modify M17.1 backend or
  M17.2 frontend code.
- ❌ Do NOT force-push or amend any
  earlier commits.

## NEXT TASK

Start SESSION_146 with (a) starting-
state verification, (b) reading M17
planning + all three M17 handoffs +
M16 retrospective structure, (c)
writing the six close-out docs
(retrospective + capability matrix
§7r + roadmap flip + planning
frontmatter flip + M18 skeleton +
session-start refresh) + coordinated
commit landing all M17.3 docs.

Backend baseline at SESSION_146
close: **4,363 pass** (unchanged —
docs-only). Frontend Vitest: **140
pass** (unchanged).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_17_PLANNING.md`
   (active memo; about to flip
   shipped)
6. `docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`
   (structure template)
7. `docs/handoffs/SESSION_145_m17_inc0_planning.md`
8. `docs/handoffs/SESSION_145_m17_inc1_backend.md`
9. `docs/handoffs/SESSION_145_m17_inc2_frontend.md`
10. `docs/CAPABILITY_MATRIX.md` §7q
    (template for §7r addition)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_145 — M17.2 SHIPPED, M17.3 close next)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0046`. Test baseline:
  **4,363 pass**, 1 skipped, 0
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
  registered** (unchanged at
  M17). Next open slot for a
  future detector is 12:00.
- **Milestones shipped:** M1 →
  M16. M17 in progress: M17.0
  planning + M17.1 backend +
  M17.2 frontend shipped at
  SESSION_145. **M17.3 close-out
  remaining.**
- **DRF admin surface:** **107**
  endpoints (104 → 107 at M17.1:
  POST freeze + GET list + GET
  detail).
- **Frontend operator routes:**
  **20** (unchanged — M14.2 page
  extended in place at M17.2 per
  §4 test binding).
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven M12
  packages + `services/
  accounting/` (**seven modules
  now** including new
  `trial_balance_close.py`).
- **Frontend accounting
  surface:** `frontend/src/lib/
  accountingApi.ts` — **8
  fetchers + 2 mutators** (4 GET
  + 1 POST from M13/M14 plus 3
  new GET + 1 new POST at M17.2)
  + four page components
  (M14.2/3/4 + M17.2 extended
  trial-balance page) +
  `TrialBalanceDatePicker`
  component.
- **Tenancy carriers:** **49**
  (unchanged since M17.1).
- **Permission classes:** **7
  actual** — `IsAdvisorForSlug`,
  `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`,
  `IsDealerOwnerAtActiveDealership`,
  `IsFinanceManagerOrOwnerAtActiveDealership`,
  `ReadOnly`. **Zero-drift
  streak: nine consecutive
  milestones** (M10 → M17.2).
  Prior narrative doc "8" was a
  miscount — corrected at
  M17.1 handoff.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M17 has
  no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 17 status:**
  M17.0 planning + M17.1
  backend + M17.2 frontend
  SHIPPED at SESSION_145.
  **M17.3 close-out next**
  (SESSION_146).
