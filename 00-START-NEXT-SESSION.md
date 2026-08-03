---
state: active
date: 2026-08-03
last_session_shipped: SESSION_167
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
milestone_20_status: shipped
milestone_21_status: in-progress
next_session: SESSION_168
next_milestone: 21
next_milestone_name: "Operational Surface Completion"
next_increment: 2
next_increment_name: "M21.2 — BHPH write-side UI + journey extension"
---

# Next session — SESSION_168 · Milestone 21 · Increment 2 (M21.2 — BHPH write-side UI + journey extension)

> **Milestone 21.1 shipped at
> SESSION_167** — systematic
> operational-surface audit
> tooling +
> `M21_OPERATIONAL_SURFACE_AUDIT.md`
> artifact + user-confirmed
> scope lock for M21.2+.
>
> **Audit findings.** 153
> endpoints enumerated; 96
> covered; 57 backend-only.
> Dispositions: 8 M21-anchor,
> 2 M21-conditional, 3 defer-
> domain-milestone, 44 defer-
> candidate-O2, 5 intentional-
> omission.
>
> **Three reconciliations
> against M20 skeleton Input
> 1** — be-back write path
> narrower than assumed (only
> CREATE missing; mark-verbs
> ship); follow-up cadence
> queue partly UI-consumed
> (only CONFIG missing); BHPH
> write confirmed at exactly
> seven verbs.
>
> **Milestone shape revised
> to five increments** — M21.0
> planning + M21.1 audit +
> M21.2 BHPH + M21.3 be-back-
> create + cadence-config +
> M21.5 close-out. M21.4
> collapsed per audit
> evidence.
>
> **SESSION_168 opens M21.2
> — the first anchor
> implementation.** Ship
> seven `bhphApi.ts` write
> wrappers + seven frontend
> components attached to the
> M12.7 collector dashboard
> surface + extended
> `seed_journey_bhph_collections_workflow`
> + backend tests + full re-
> expansion of
> `bhph/collections_workflow.spec.ts`
> to end-to-end write coverage.

## First thing SESSION_168 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M21.1 commit
  (audit tooling + artifact +
  scope-lock amendment +
  handoff).
- `python3 manage.py test
  dealer_ai` → **4,755 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` →
  **153 pass**.
- `python3 manage.py check`
  clean.
- `python3 manage.py
  makemigrations --check
  --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `cd acceptance && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Verify acceptance CI still green

- `gh run list
  --workflow=acceptance
  --branch=main --limit 5` —
  top runs should still be
  green (M21.0 and M21.1 are
  local commits ahead of
  `origin/main`; the CI
  workflow runs on push to
  main, so the latest green
  run is still the pre-M21
  M20-close state).

### 3. Ship the seven `bhphApi.ts` write wrappers

`frontend/src/lib/bhphApi.ts`
currently exports only read
helpers. Add seven new exported
async functions:

- `recordPromiseToPay(noteId,
  payload)` → `POST
  /admin/bhph-notes/${noteId}/promises/`
- `markPromiseKept(promiseId,
  payload)` → `POST
  /admin/bhph-promises/${promiseId}/mark-kept/`
  (payload includes payment
  reference per M12.4 §5.d
  Option A operator-triggered
  reconciliation).
- `markPromiseBroken(promiseId,
  payload)` → `POST
  /admin/bhph-promises/${promiseId}/mark-broken/`
- `logCollectionContact(noteId,
  payload)` → `POST
  /admin/bhph-notes/${noteId}/contacts/`
- `initiateRepossession(noteId,
  payload)` → `POST
  /admin/bhph-notes/${noteId}/repossessions/`
- `markRepossessionRecovered(reposId,
  payload)` → `POST
  /admin/bhph-repossessions/${reposId}/mark-recovered/`
- `markRepossessionReIntaked(reposId,
  payload)` → `POST
  /admin/bhph-repossessions/${reposId}/mark-re-intaked/`
  (payload includes
  ConditionReport reference
  per M12.6 lifecycle).

Follow existing bhphApi.ts
type-export conventions. Add
TypeScript response types
based on the backend
serializers.

### 4. Ship the seven frontend components

Attach to the M12.7 collector
dashboard surface
(`DealerAiBhphNoteDetail.tsx`
Promises card, Contacts card,
Repossessions card):

- **Promises card:**
  - `RecordPromiseToPayForm`
    (attach to card action
    area — fields: promised
    amount, promised date,
    channel, notes).
  - `MarkKeptPromiseButton`
    row action (opens a
    lightweight payment-
    reference picker before
    posting).
  - `MarkBrokenPromiseButton`
    row action (opens a
    reason-code + notes
    dialog).
- **Contacts card:**
  - `LogCollectionContactForm`
    (attach to card action
    area — fields: channel,
    outcome, notes; FDCPA
    scrub applies via
    backend).
- **Repossessions card:**
  - `InitiateRepossessionForm`
    (attach to card action
    area — fields: reason,
    initiated-at, notes).
  - `MarkRecoveredButton`
    row action (recovered-at
    + location dialog).
  - `MarkReIntakedButton`
    row action (opens a
    ConditionReport picker
    scoped to the recovered
    vehicle).

Prefer operator vocabulary in
component names per M17 §6
lesson 3. All components
attach in-place per M17 §6
lesson 6 + M19.4 posture; no
new routes.

### 5. Ship Vitest coverage

For each new form:
- Submit path (happy path
  posts correct payload
  shape).
- Validation path (required
  fields, min/max, format).
- Error path (backend 400 /
  409 / 404 renders correctly).

For each new button:
- Click handler dispatches
  the wrapper with correct
  args.
- Confirm dialog (if
  applicable) appears + can
  be dismissed / confirmed.

Target Vitest baseline
movement: 153 → ~163-170.

### 6. Extend `seed_journey_bhph_collections_workflow`

Currently seeds a state where
the M20.4 read-side journey
can review the portfolio.
Extend to seed:
- A note with a PtP-ready
  balance (for `record_promise`).
- An existing active promise
  (for `mark_broken` /
  `mark_kept`).
- Existing contact history
  visible (so `log_contact`
  demonstrably grows the
  list).
- A note in a state where
  `initiate_repossession` is
  valid (broken PtP + past-
  due balance).
- A repossession record in
  `initiated` state (for
  `mark_recovered`).
- A recovered repossession
  (for `mark_re_intaked` +
  ConditionReport
  attachment).

Backend tests: idempotency
(rerun leaves same state) +
tenant scoping (writes are
scoped to demo tenant only).
Target backend baseline
movement: 4,755 → ~4,760-4,770.

### 7. Re-expand `acceptance/journeys/bhph/collections_workflow.spec.ts`

M20.4 narrowed to the read
side; M21.2 re-expands to the
full workflow:

- Operator navigates to BHPH
  portfolio → drills into a
  note.
- Records a promise-to-pay
  (asserts new row appears
  in Promises card).
- On a separate note, marks
  an existing promise as
  broken (asserts state
  transition, badge update).
- Logs a collection contact
  (asserts row appears in
  Contacts card).
- Initiates a repossession
  (asserts state transition
  + row in Repossessions
  card).
- Marks a recovered
  repossession as re-intaked
  with ConditionReport
  (asserts final state).

Business-outcome assertions at
each step. If any step
requires a testid that
doesn't exist on the target
component, add it opportunistically
per §5.g Option B.

### 8. Ship the M21.2 handoff + refresh entry point

- `docs/handoffs/SESSION_168_m21_inc2_bhph_write.md`.
- Refresh
  `00-START-NEXT-SESSION.md`
  for SESSION_169 / M21.3.
- **Do NOT push** — M21
  coordinated push happens
  at M21 close per M18.6 /
  M19.6 / M20.5 cadence.

## Non-goals for SESSION_168

- ❌ Do NOT modify any
  backend service verb —
  every M21.2 UI action
  invokes an existing verb
  through an existing
  endpoint.
- ❌ Do NOT add or modify
  any DRF endpoint — the
  seven target endpoints
  all ship as of M12.
- ❌ Do NOT add new
  frontend routes — attach
  to
  `DealerAiBhphNoteDetail.tsx`
  in place.
- ❌ Do NOT touch the be-
  back or cadence surfaces —
  those land in M21.3.
- ❌ Do NOT modify existing
  BHPH read-side components
  or the portfolio dashboard
  unless a specific bug
  surfaces during journey
  extension (in which case
  surface as an §0.a M21.2
  amendment).
- ❌ Do NOT force-push or
  amend earlier commits.
- ❌ Do NOT modify M1–M20
  shipped surface.
- ❌ Do NOT bundle Candidate
  G full-coverage testids —
  §5.g Option B binds M21
  to opportunistic testids
  only.
- ❌ Do NOT ship any
  additional endpoints from
  the audit's `defer-
  candidate-O2` list — those
  are Candidate O2 for M22+
  per §0.a M21.1 lock.

## Baseline expected at close

- **Backend:** ~4,760-4,770
  pass (up from 4,755 via
  delta command tests).
- **Frontend Vitest:** ~163-
  170 pass (up from 153 via
  new component tests).
- **Acceptance suite:** 6
  journeys (BHPH re-expanded
  end-to-end).
- **Migrations:** `0001`–`0048`
  (unchanged).
- **Tenancy carriers:** 52
  (unchanged).
- **Permission classes:** 7
  (unchanged — zero-drift
  streak targets extension
  to twenty-one at M21
  close).
- **Frontend operator
  routes:** 20 (unchanged).
- **DRF admin surface:** 113
  (unchanged — M21.2 adds
  zero endpoints).

## NEXT TASK

Start SESSION_168 with (a)
starting-state verification,
(b) acceptance CI green
re-confirmation, (c) ship
seven `bhphApi.ts` write
wrappers with typed responses,
(d) ship seven frontend
components on the M12.7
collector dashboard surface,
(e) Vitest coverage for
forms + buttons, (f) extend
`seed_journey_bhph_collections_workflow`
+ backend tests, (g) re-
expand
`bhph/collections_workflow.spec.ts`
to full write coverage with
business-outcome assertions,
(h) ship the M21.2 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (active — §0.a M21.1
   scope lock recorded)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (M21.1 audit artifact —
   traces M21.2+ scope
   decisions)
7. `docs/handoffs/SESSION_167_m21_inc1_audit.md`
   (M21.1 shipped)
8. `docs/handoffs/SESSION_166_m21_inc0_planning.md`
   (M21.0 shipped —
   governing contract +
   eight §5 decisions)
9. `docs/CAPABILITY_MATRIX.md`
   §7u (M20 shipped surface)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_167 — Milestone 21 · Increment 1 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,755 pass**, 1 skipped, 0
  fail (unchanged; audit
  scripts are operator-
  invoked, not tested).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **six
  journeys** passing end-to-
  end (unchanged).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`
  — green across the last
  three pushes (M20.5 CI-
  cleanups + M21 skeleton).
  M21.0 and M21.1 commits are
  local-ahead of
  `origin/main`; coordinated
  push at M21 close per
  M18.6 / M19.6 / M20.5.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M20**. **M21 in progress
  (M21.0 planning + M21.1
  audit shipped locally).**
- **DRF admin surface:** 113
  endpoints.
- **Frontend operator routes:**
  20.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M20 packages unchanged.
  M21 adds zero service
  verbs.
- **Frontend surfaces:**
  unchanged since M19.4;
  M21.2 will extend
  `DealerAiBhphNoteDetail.tsx`
  in place (no new routes).
- **Tenancy carriers:** 52.
- **Permission classes:** 7
  actual — zero-drift streak
  twenty consecutive
  milestones (M10 → M20).
  M21 targets extension to
  twenty-one at close.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 21 status:** IN
  PROGRESS. M21.0 (planning
  refinement + target
  selection) + M21.1
  (systematic operational-
  surface audit + M21 scope
  lock) shipped locally.
  Scope locked at M21.1
  close: M21.2 BHPH write-
  side UI (7 endpoints);
  M21.3 be-back CREATE +
  cadence CONFIG (3
  endpoints); M21.4 skipped;
  M21.5 close-out.
- **Audit tooling:**
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  operator-invoked from the
  `backend/` directory
  (`python3 -m dealer_ai.scripts.audit_operational_surface`).
  Rerun after new endpoints
  or component consumers
  ship to refresh
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
- **Planning-time streak:**
  **87 as-recommended M5.1
  → M21.0** across twelve
  consecutive milestones
  (M10 → M21). No new §5
  decisions land in M21.1
  or M21.2 (both are
  execution sessions);
  streak preserved.
- **DoD amendment
  (formalized at M21.0
  §5.f Option B):** every
  future customer-facing
  milestone must add or
  update at least one
  Playwright operational
  journey, or explicitly
  document in §3 why no
  journey change is
  required. Applies from
  M21 forward.
- **Governing contract
  (Candidate O):** every
  M21 shipped surface maps
  to an already-shipped
  backend capability,
  closes a missing
  operator-facing UI, adds
  or extends a Playwright
  operational journey, and
  is not generic UX polish.
