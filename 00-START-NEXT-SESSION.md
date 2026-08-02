---
state: active
date: 2026-08-02
last_session_shipped: SESSION_150
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
milestone_18_status: in-progress
next_session: SESSION_151
next_milestone: 18
next_milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
next_increment: 5
next_increment_name: "M18.5 — Role-based daily briefs + feedback endpoint + CSV exporter"
---

# Next session — SESSION_151 · Milestone 18 · Increment 5 (M18.5 — Briefs + feedback endpoint + CSV exporter)

> **SESSION_150 shipped M18.4 —** the
> BHPH archetype pack. All three
> archetypes now shipped
> (retail_subprime + floor_planned +
> bhph). The demo-store package is
> code-complete for archetype
> construction. The BHPH archetype
> ships **~5 payments with
> posted_at=NULL** so the M16.1
> detector at 11:00 posts them into
> the GL on next cycle — the trial-
> balance surface changes after
> 11:00 for the tester walking the
> accounting-role daily brief.
>
> **Backend baseline: 4,483 → 4,514
> pass** (+31 tests, 0 regressions).
> Frontend Vitest 140 (unchanged).
> Migrations 0043-0047 (unchanged).
> Tenancy carriers 50 (unchanged).
> DRF admin surface 107 (unchanged).
> Frontend operator routes 20
> (unchanged). Permission classes 7
> — **zero-drift streak thirteen
> consecutive milestones** (M10 →
> M18.4). Celery-beat task families
> 10 (unchanged).
>
> **§0.a M18.2 decision 1 continues
> to apply.** Chargeback still
> deferred; will surface in an M18.5
> F&I scenario brief or be recorded
> as a permanent M18-scope
> deferral for a later milestone.
>
> **SESSION_151 opens M18.5 —**
> per-archetype daily briefs +
> TesterFeedback POST endpoint + CSV
> exporter body + optional UI
> capture form.

## First thing SESSION_151 must do

### 1. Verify starting state

- `git status` — clean (M18.4 commit
  `42c604d` landed at SESSION_150
  close).
- `git log --oneline -3` — top
  should be `42c604d` (M18.4 BHPH).
- `python3 manage.py test dealer_ai`
  → **4,514 pass, 1 skipped, 0
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

### 2. Read first (in order)

- `docs/roadmap/MILESTONE_18_PLANNING.md`
  §7 M18.5.
- `docs/handoffs/SESSION_150_m18_inc4_bhph_archetype.md`
  (M16 detector timing anchor).
- `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`
  (recon overrun anchor).
- `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
  (retail/subprime baseline).
- `backend/dealer_ai/services/demo_store/archetypes/*.py`
  (the seeded state the briefs
  will describe).

## What M18.5 delivers

Per `MILESTONE_18_PLANNING.md` §7
M18.5:

### Per-archetype daily briefs

Add `services/demo_store/briefs/`
package with per-archetype
markdown brief files. Each brief
follows the standard structure per
the milestone brief:

- What happened before login.
- What the operator needs to
  accomplish today.
- What information is
  intentionally incomplete /
  problematic.
- Which shipped capabilities
  should help.
- What successful completion
  looks like.
- What must remain discoverable
  without a guided click path.

**Brief inventory (per §5 M18.5):**

- **`retail_subprime/`**: owner,
  sales_manager, recon,
  accounting. (No collector — the
  archetype has no active BHPH
  book.)
- **`floor_planned/`**: owner,
  sales_manager,
  **recon (overrun
  intervention centerpiece)**,
  accounting. (No collector.)
- **`bhph/`**: owner, sales_manager,
  recon, accounting **(M16
  detector timing scenario)**,
  **collector (daily book,
  promise follow-up, repo
  handoff)**.

### TesterFeedback POST endpoint

Ship the endpoint the M18.1
substrate anticipated:

- Path: `POST
  /admin/demo-store/feedback/`
- Reuses
  `IsSalesManagerOrOwnerAtActiveDealership`
  (zero-drift streak extends to
  fourteen consecutive milestones).
- Body: `{ "tester_name",
  "scenario_slug", "category",
  "note", "referenced_route" }`.
- Returns 201 with the persisted
  TesterFeedback projection.
- Refuses non-demo dealerships
  via the M18.1
  `NonDemoResetError`-shaped guard
  (or a new
  `NonDemoFeedbackError` if
  needed).
- Endpoint count 107 → **108**.

### CSV exporter body

The M18.1 substrate shipped the
`export_feedback` subcommand
scaffold with header + basic
rows. If any fields are missing
or need polishing based on real
usage, complete them at M18.5.

### Optional UI capture form

Per §5.f — a small feedback
capture form component wired into
the M14 admin surface is a
plausible in-place extension. Only
ship if a scenario brief blocks
without it (test-drive per M18.5
walkthrough).

### Focused tests (~15-20 target)

`tests/test_m185_briefs_and_feedback.py`:

- Brief files load for each
  archetype role (matrix test).
- POST endpoint: 201 happy path;
  400 invalid category; 403 non-
  permitted role; 500 (RuntimeError
  or 403) when dealership is not a
  demo store.
- Export CSV shape (already
  covered at M18.1 — add end-to-
  end scenario).
- Feedback list scoped to tenant.
- If a UI component ships: Vitest
  cases mirroring the M17.2
  pattern.

### Non-goals for M18.5

- ❌ No M18.6 close-out docs.
- ❌ No new operator routes (feedback
  capture goes on an existing admin
  page).
- ❌ No new Celery-beat entries.
- ❌ No Chargeback substrate (§0.a
  M18.2 decision 1 still applies —
  may be re-evaluated at M18.6).
- ❌ Do NOT ship broad UX polish;
  §5.f discipline holds.

### Backend baseline target

**4,514 → ~4,529-4,549 pass**
(+15-20 tests, 0 regressions).
Frontend Vitest: 140 → ~140-155
if a feedback capture component
lands.

## Explicit non-goals for SESSION_151

- ❌ Do NOT ship M18.6 close-out
  docs in the same session.
- ❌ Do NOT modify M1-M17 business
  logic (except UI-correction
  discipline per §5.f).
- ❌ Do NOT force-push or amend any
  earlier commits.

## NEXT TASK

Start SESSION_151 with (a)
starting-state verification, (b)
reading the three archetype
handoffs to understand what
scenario state the briefs must
describe, (c) writing the
per-archetype brief markdown +
POST endpoint + CSV exporter
completion + tests. Ship the
M18.5 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
6. `docs/handoffs/SESSION_150_m18_inc4_bhph_archetype.md`
7. `docs/handoffs/SESSION_149_m18_inc3_floor_planned_archetype.md`
8. `docs/handoffs/SESSION_148_m18_inc2_retail_subprime_archetype.md`
9. `docs/handoffs/SESSION_147_m18_inc1_backend_substrate.md`
10. `docs/CAPABILITY_MATRIX.md` §7r
11. `backend/dealer_ai/services/demo_store/` — the shipped
    archetype surface the briefs
    reference

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_150 — M18.4 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0047`.
  Test baseline: **4,514 pass**,
  1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` + `vite
  build` clean. **Vitest baseline:
  140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 + `django-celery-beat`
  2.8.1 DatabaseScheduler. **10
  scheduled task families**.
- **Milestones shipped:** M1 → M17.
  M18 in progress: M18.0 + M18.1 +
  M18.2 + M18.3 + M18.4 shipped.
  **M18.5 briefs + feedback endpoint
  + exporter next** (SESSION_151).
- **DRF admin surface:** **107**.
  Grows to 108 at M18.5 (feedback
  POST).
- **Frontend operator routes:**
  **20** — unchanged through M18.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** complete
  `services/f_and_i/` (M10) + five
  M11 + seven M12 +
  `services/accounting/` (seven) +
  `services/demo_store/` (nine
  modules) **with all three
  archetypes fully implemented**.
- **Tenancy carriers:** **50**.
- **Permission classes:** **7
  actual** — **zero-drift streak
  thirteen consecutive milestones**
  (M10 → M18.4).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M18 has no
  LLM path).
- **Deterministic rules:** unchanged.
- **Milestone 18 status:** M18.0
  planning + M18.1 substrate +
  M18.2 retail/subprime + M18.3
  floor-planned + M18.4 BHPH
  SHIPPED. **M18.5 briefs +
  feedback + exporter next**
  (SESSION_151). M18.6 close-out to
  follow.
