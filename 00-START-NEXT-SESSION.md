---
state: active
date: 2026-08-02
last_session_shipped: SESSION_164
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
milestone_19_status: shipped
milestone_20_status: in-progress
next_session: SESSION_165
next_milestone: 20
next_milestone_name: "Operational Journey Validation (Playwright acceptance testing)"
next_increment: 5
next_increment_name: "M20.5 — Close-out (CI validation + retrospective + M21 skeleton + first push)"
---

# Next session — SESSION_165 · Milestone 20 · Increment 5 (M20.5 — close-out + first push)

> **M20.4 shipped at SESSION_164.** Sixth
> and final journey layered: **BHPH
> collections read-side workflow**.
> **Scope narrowed from the M20 plan** —
> the write-side operations (record
> PtP, mark broken, log contact,
> initiate repossession) have no shipped
> frontend UI, so the journey exercises
> the read side of the daily book
> review workflow. Missing write-side
> UI captured as an M21+ candidate
> ("M12.8 BHPH collections write-side
> UI") in the M20.4 handoff.
>
> **Local acceptance dry-run: 12 passed
> (19.1s)** — 6 setup steps + 6
> journeys.
>
> **Backend baseline:** 4,741 → **4,755
> pass** (+14). Frontend Vitest: **153
> pass** (unchanged). Zero drift.
>
> **SESSION_165 opens M20.5 close-out** —
> retrospective + capability matrix +
> M21 skeleton + IMPLEMENTATION_ROADMAP
> flip + first push (surfaces all five
> M20 commits to GitHub Actions and
> triggers the first real acceptance
> CI run).

## First thing SESSION_165 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top should
  be the M20.4 shipped commit.
- `python3 manage.py test dealer_ai`
  → **4,755 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Full-suite CI validation via local dry-run

Before committing M20.5 close-out
docs, verify the local acceptance
suite is green end-to-end:

```bash
cd acceptance
rm -f ../backend/db.acceptance.sqlite3
rm -rf .auth playwright-report test-results
mkdir -p .auth
npm test
```

Expect **12 passed** (6 setup + 6
journeys). Measure the duration —
that's the local proxy for the CI
`main` push duration.

### 3. Intentional-failure verification of artifact upload

Temporarily break ONE journey (e.g.
change a text selector), run
`npm test`, verify the failure
produces:
- HTML report at
  `playwright-report/`.
- Trace file at
  `test-results/`.
- Video at
  `test-results/`.

Revert the intentional break. This
validates that when CI fails, the
artifacts will land in the GitHub
Actions run per §5.g Option A.

### 4. Ship M20 retrospective

`docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`:
- §1 What shipped (all six
  increments summarized).
- §2 What each increment surfaced
  about the operational-acceptance
  contract.
- §3 Lessons learned (framework
  substrate defects surfaced by
  first dry-run; scope narrowing
  when shipped UI is missing;
  envelope-wrapped API responses;
  selector strategy without
  data-testids).
- §4 Deferrals reviewed.
- §5 Metrics: journey count (6),
  seed command count (6), backend
  test additions (~76), streak
  extensions.
- §8 Unblocks: M12.8 BHPH write-
  side UI, dashboard testid hardening.
- §9 Standing question: is M21 the
  return-to-accounting milestone?

### 5. Update capability matrix

`docs/CAPABILITY_MATRIX.md` §7u
capturing the M20 shipped surface:
- New top-level `acceptance/`
  workspace.
- Six journey specs.
- Six seed delta management
  commands.
- New `.github/workflows/acceptance.yml`
  CI job.
- Settings.py `M20_ACCEPTANCE_DB`
  extension.
- Zero new tenancy carriers, zero
  new endpoints, zero new
  migrations, zero new permission
  classes (streak extends
  nineteen → **twenty**).

### 6. Ship M21 planning skeleton

`docs/roadmap/MILESTONE_21_PLANNING.md`
as `status: draft`. Candidate list
combining:
- Carry-forward candidates from
  M19 §9 (T, U, A, P, L, M, D, C).
- New from M20 retrospective §9
  (M12.8 BHPH write-side UI,
  dashboard testid hardening,
  possibly others).

### 7. Flip roadmap

`docs/roadmap/IMPLEMENTATION_ROADMAP.md`:
- M20 status → shipped.
- Update the current-milestone
  pointer.

### 8. Ship the M20.5 close-out handoff

- `docs/handoffs/SESSION_165_m20_inc5_close.md`.
- Coordinated close-out commit
  containing: retrospective +
  capability matrix update +
  M21 skeleton + roadmap flip +
  handoff + `00-START-NEXT-SESSION`
  refresh.

### 9. FIRST PUSH

**`git push origin main`** —
surfaces all five M20 commits
(M20.0 + M20.1 + M20.2 + M20.3 +
M20.4 + M20.5) to GitHub Actions
in one coordinated push per the
M18/M19 cadence.

This triggers the first real
acceptance CI run. If CI fails,
address as §0.a M20.5 amendments
before declaring M20 shipped.

## Non-goals for SESSION_165

- ❌ Do NOT modify any existing
  backend service verb, endpoint,
  migration, or frontend route
  (except selector-stability
  fixes surfaced by CI, recorded
  as §0.a).
- ❌ Do NOT ship new journeys —
  M20.5 is close-out only.
- ❌ Do NOT force-push, amend, or
  push before the coordinated
  M20.5 commit is in.
- ❌ Do NOT ship the M21 planning
  memo as `status: active` —
  skeleton only, activation
  happens at M21.0 open per the
  M19.6 → M20.0 precedent.

## Baseline expected at close

- **Backend:** unchanged at 4,755
  pass (M20.5 is docs-only).
- **Frontend Vitest:** 153
  (unchanged).
- **Migrations:** unchanged
  `0001`–`0048`.
- **Tenancy carriers:** unchanged
  at 52.
- **Permission classes:** unchanged
  at 7 — **zero-drift streak
  extends nineteen → twenty
  consecutive milestones (M10 →
  M20)**.
- **DRF admin surface:** unchanged
  at 113.
- **Frontend operator routes:**
  unchanged at 20.
- **Acceptance suite:** **6
  journeys** passing locally +
  (target) 6 journeys passing on
  first `main` CI run after push.
- **Pilot-critical subset:** 2
  passing on PR after next PR.
- **Milestone 20:** SHIPPED.

## NEXT TASK

Start SESSION_165 with (a) starting-
state verification, (b) full local
acceptance dry-run, (c) intentional-
failure verification of artifact
upload, (d) ship M20 retrospective,
(e) update capability matrix §7u,
(f) ship M21 planning skeleton,
(g) flip IMPLEMENTATION_ROADMAP,
(h) ship the M20.5 close-out
handoff + coordinated commit,
(i) `git push origin main` and
monitor the first real acceptance
CI run.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (this milestone's active memo)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (Candidate J origin)
7. `docs/CAPABILITY_MATRIX.md` §7t
   (M19 shipped surface)
8. `docs/handoffs/SESSION_164_m20_inc4_bhph_journey.md`
   (M20.4 shipped)
9. `docs/handoffs/SESSION_163_m20_inc3_backoffice_journeys.md`
   (M20.3)
10. `docs/handoffs/SESSION_162_m20_inc2_dashboard_journeys.md`
    (M20.2)
11. `docs/handoffs/SESSION_161_m20_inc1_framework.md`
    (M20.1 framework substrate)
12. `docs/handoffs/SESSION_160_m20_inc0_planning.md`
    (M20.0 planning close)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_164 — M20.4 shipped)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0048`.
  Test baseline: **4,755 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):**
  Playwright 1.49 + TS 5.6
  operational; **all six planned
  journeys** green end-to-end.
  Full dry-run: **12 passed in
  19.1s**.
- **Acceptance (CI):** wired via
  `.github/workflows/acceptance.yml`.
  First actual CI run pending the
  M20.5 push (SESSION_165).
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10 scheduled
  task families registered**.
- **Milestones shipped:** M1 →
  **M19**. M20 in-progress (M20.0
  + M20.1 + M20.2 + M20.3 + M20.4
  shipped; M20.5 close-out
  pending).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all M1–M19
  packages unchanged. M20 adds no
  service verbs. **Six management
  commands**
  (`seed_journey_pilot_onboarding`
  + `seed_journey_owner_morning_review`
  + `seed_journey_sales_manager_daily_startup`
  + `seed_journey_recon_workflow`
  + `seed_journey_office_accounting_workflow`
  + `seed_journey_bhph_collections_workflow`).
- **Frontend surfaces:** unchanged
  since M19.4.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **nineteen consecutive
  milestones** (M10 → M19.5).
  Extends to **twenty** at M20.5
  close.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 20 status:** IN
  PROGRESS. M20.0 planning +
  M20.1 framework + M20.2
  dashboard journeys + M20.3
  back-office journeys + M20.4
  BHPH read-side journey shipped.
  **One increment remaining
  (M20.5 close-out)** per §7
  sequencing.
- **Planning-time streak:** **86
  as-recommended M5.1 → M20.0**
  across eleven consecutive
  milestones.
- **Acceptance-suite journeys:**
  **6** authored (pilot onboarding
  [`@pilot-critical`] + owner
  morning review [`@pilot-critical`]
  + sales manager daily startup +
  recon workflow + office/
  accounting workflow + BHPH
  collections read-side).
- **M20 commits held on `main`
  (unpushed):** M20.0 (69b8214) +
  M20.1 (66ee652) + M20.2
  (e634c34) + M20.3 (59dc43d) +
  M20.4 (this session's commit).
  First push happens at M20.5
  close per M18/M19 cadence.
- **Guiding principle for M20
  implementation:** business
  outcomes through real UI on
  deterministic seeded state; not
  UI automation.
