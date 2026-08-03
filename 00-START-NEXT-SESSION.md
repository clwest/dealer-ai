---
state: active
date: 2026-08-03
last_session_shipped: SESSION_166
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
next_session: SESSION_167
next_milestone: 21
next_milestone_name: "Operational Surface Completion"
next_increment: 1
next_increment_name: "M21.1 — Systematic operational-surface audit + M21 scope lock"
---

# Next session — SESSION_167 · Milestone 21 · Increment 1 (M21.1 — systematic operational-surface audit + M21 scope lock)

> **Milestone 21 opened at
> SESSION_166** with §5.a Candidate O
> confirmed — **Operational Surface
> Completion**, an evidence-driven
> umbrella milestone that closes the
> highest-value missing UI workflows
> found by the M20 operational
> audit. Two anchor implementations
> pre-committed at planning-time
> (BHPH write-side UI + be-back
> write-side UI); conditional third
> anchor (follow-up cadence queue
> UI) entering scope only if the
> M21.1 systematic audit confirms
> fit.
>
> **All eight §5 decisions confirmed
> as-recommended at M21.0 open.**
> Streak extends to **87 planning-
> time as-recommended M5.1 → M21.0
> across twelve consecutive
> milestones** (M10 → M21).
>
> **Governing contract established
> (Candidate O).** Every M21 shipped
> surface must satisfy four
> conditions: (1) maps to an
> already-shipped backend capability;
> (2) closes a missing operator-
> facing UI; (3) adds or extends a
> Playwright operational journey;
> (4) is not generic UX polish.
>
> **Definition of Done amendment
> formalized (§5.f Option B).**
> Every future customer-facing
> milestone must either add or
> update at least one Playwright
> operational journey, or explicitly
> document in §3 of the planning
> memo why no journey change is
> required. Amendment applies from
> M21 forward.
>
> **SESSION_167 opens M21.1 — the
> systematic operational-surface
> audit + M21 scope lock.** Lands
> the audit tooling
> (`backend/dealer_ai/scripts/audit_operational_surface.py`
> per §5.b Option C combined
> methodology) + the audit artifact
> (`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
> per §5.c Option A schema) + user-
> confirmed scope selection for
> M21.2 onward per §5.d Option B.

## First thing SESSION_167 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M21.0 planning
  commit (this session).
- `python3 manage.py test dealer_ai`
  → **4,755 pass, 1 skipped, 0
  fail** (baseline unchanged
  from M20 close).
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

### 2. Verify M20 acceptance CI still green

- `gh run list --workflow=acceptance
  --branch=main --limit 5` — top
  runs should all be green
  (M21.0 planning-only push adds
  no code that could break CI,
  but confirm as a matter of
  posture).

### 3. Author the audit tooling

Per §5.b Option C combined
methodology:

- **Service-verb enumeration.** Walk
  `backend/dealer_ai/services/**/*.py`;
  extract every publicly-exported
  callable. Cross-reference to
  frontend consumption via
  `axios.*` / `fetch` / `useMutation`
  / `useQuery` call sites in
  `frontend/src/**/*.{ts,tsx}` (by
  URL pattern match — service verbs
  power endpoints; endpoint URLs
  are the join key).
- **DRF endpoint enumeration.**
  Walk
  `backend/dealer_ai/**/urls.py`
  + viewset definitions; extract
  every action + method
  combination. Cross-reference to
  the same frontend call-site
  surface.
- **Emit a merged manifest** as
  input to the audit artifact.

Location:
`backend/dealer_ai/scripts/audit_operational_surface.py`
(single script preferred; may
split into
`enumerate_service_verbs.py` +
`enumerate_drf_endpoints.py` +
`join_and_report.py` if
implementation complexity
warrants).

**Not runtime code** — scripts are
operator-invoked during M21.1; no
Django app registration, no
management-command surface, no
tests required in this increment.

### 4. Populate the audit artifact

Per §5.c Option A schema. Create
`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.

**Per-row schema:**

| Backend capability | Missing operator surface | Affected operational journey | Recommended disposition |
| --- | --- | --- | --- |
| service verb path + DRF endpoint | expected component path or "unreachable" | existing journey path or "new required" | `M21-anchor` / `M21-conditional` / `defer-candidate-O2` / `defer-domain-milestone` / `intentional-omission` |

**Per-domain narrative sections**
after the table summarizing
patterns (e.g. "BHPH write path —
5 verbs, 0 UI surfaces;
recommended disposition:
M21-anchor via §5.a scope";
"Accounting reversal — 3 verbs, 0
UI surfaces; recommended
disposition: defer-domain-
milestone under Candidate A for
M22 consideration").

**Disposition definitions
(reference):**

- **`M21-anchor`** — pre-committed
  M21 scope (BHPH writes, be-back
  writes); confirmed by audit.
- **`M21-conditional`** — audit-
  surfaced item recommended for
  M21.4 conditional scope.
- **`defer-candidate-O2`** —
  future OSC-shaped milestone
  (M22+); explicit re-entry path.
- **`defer-domain-milestone`** —
  belongs in a distinct domain
  milestone (e.g. accounting
  reversal → Candidate A for
  M22); explicit re-entry path.
- **`intentional-omission`** —
  capability is internal / not
  meant to be user-facing;
  document why.

### 5. Draft M21.2+ scope recommendation

Per §5.d Option B. After the
audit artifact lands, draft a
scope recommendation for M21.2
onward:

- **Re-validate the two anchors**
  (BHPH write-side UI + be-back
  write-side UI) against the
  audit findings. Confirm the
  expected component surface
  matches the observed backend
  capability; flag any surprises
  as §0.a M21.1 amendments.
- **Disposition follow-up cadence
  queue UI.** Recommend M21-
  conditional (into M21.4) or
  defer-candidate-O2 based on
  audit evidence (does the
  cadence backend surface exist
  and is it complete? does the
  queue fit remaining M21
  capacity?).
- **Disposition any additional
  audit-surfaced items** with
  `M21-anchor` or `M21-
  conditional` recommendations.
  Ground each in operator pain
  + dependency notes.
- **Present the recommendation +
  await user confirmation.**

### 6. Lock M21.2+ scope

Once user confirms scope:

- Update
  `MILESTONE_21_PLANNING.md`
  §0.a with an M21.1 amendment
  recording the scope lock.
  Frontmatter `sources` may
  extend to reference the audit
  artifact.
- Adjust §7 sequencing if M21.4
  is skipped (M21.5 becomes the
  next increment) or if the
  audit surfaces implementation-
  splitting evidence.

### 7. Ship the M21.1 handoff

- `docs/handoffs/SESSION_167_m21_inc1_audit.md`
  matching M20.1 handoff shape.
- Refresh
  `00-START-NEXT-SESSION.md`
  for M21.2.
- **Do NOT push** — M21.1
  coordinated push happens at
  M21 close per M18/M19/M20
  cadence.

## Non-goals for SESSION_167

- ❌ Do NOT ship any frontend UI
  components in this increment
  — M21.1 is audit + scope-lock
  only.
- ❌ Do NOT ship any backend
  service verbs or endpoints —
  M21 has zero new backend
  surface per §0 preservation
  posture.
- ❌ Do NOT modify existing
  frontend routes — M21 adds
  zero routes.
- ❌ Do NOT modify shipped
  service verbs, endpoints,
  tenancy carriers, permission
  classes, or migrations —
  M21's zero-drift streak
  extension (twenty → twenty-
  one) depends on this.
- ❌ Do NOT extend or modify the
  M20 acceptance suite in this
  increment — journey
  extensions land in M21.2
  onward alongside their
  corresponding UI shipping.
- ❌ Do NOT force-push or amend
  earlier commits (M20 close is
  already on `origin/main`).
- ❌ Do NOT modify M1–M20
  shipped surface.
- ❌ Do NOT bundle Candidate G's
  full-coverage testid pass —
  §5.g Option B binds M21 to
  opportunistic testids only
  (in M21.2+ implementation
  increments).

## Baseline expected at close

Backend baseline: 4,755
(unchanged — audit scripts are
operator-invoked, not tested).
Frontend Vitest: 153
(unchanged). Acceptance suite: 6
journeys (unchanged). Migrations
`0001`–`0048` (unchanged).
Tenancy carriers 52 (unchanged).
Permission classes 7
(unchanged). Frontend operator
routes 20 (unchanged). DRF admin
surface 113 (unchanged).

**New surface at M21.1 close:**
`backend/dealer_ai/scripts/audit_operational_surface.py`
(or split scripts) +
`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
+ §0.a M21.1 scope-lock
amendment in
`MILESTONE_21_PLANNING.md`.

## NEXT TASK

Start SESSION_167 with (a)
starting-state verification, (b)
M20 CI-green re-confirmation, (c)
author the audit tooling per §5.b
Option C, (d) populate the audit
artifact per §5.c Option A, (e)
draft M21.2+ scope recommendation
per §5.d Option B, (f) await user
confirmation, (g) record scope
lock as §0.a M21.1 amendment, (h)
ship the M21.1 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (active — expanded at
   SESSION_166)
6. `docs/handoffs/SESSION_166_m21_inc0_planning.md`
   (M21.0 shipped)
7. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 + §9 (M20 unblocks +
   standing M21 question that
   became Candidate O)
8. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (framework + journey patterns
   M21 extends)
9. `docs/CAPABILITY_MATRIX.md`
   §7u (M20 shipped surface —
   the substrate M21's audit
   walks)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_166 — Milestone 21 · Increment 0 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,755 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 153 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):**
  Playwright 1.49 + TS 5.6
  operational; **six journeys**
  passing end-to-end.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`
  — green across the last three
  pushes (M20.5 CI-cleanups +
  M21 skeleton).
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M20**. **M21 in progress**
  (M21.0 planning shipped at
  SESSION_166; M21.1 audit + M21
  scope lock next at
  SESSION_167).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all M1–M20
  packages unchanged. M21 adds
  zero service verbs.
- **Frontend surfaces:** unchanged
  since M19.4.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty consecutive
  milestones** (M10 → M20).
  M21 targets extension to
  twenty-one at close.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 21 status:**
  IN PROGRESS. M21.0 (planning
  refinement + target selection)
  shipped at SESSION_166 with
  all eight §5 decisions
  confirmed as-recommended.
  Candidate O — Operational
  Surface Completion — locked
  as §5.a target. Two anchor
  implementations pre-committed
  (BHPH + be-back); conditional
  third (follow-up cadence)
  pending M21.1 audit.
- **Planning-time streak:** **87
  as-recommended M5.1 → M21.0**
  across twelve consecutive
  milestones (M10 + M11 + M12 +
  M13 + M14 + M15 + M16 + M17 +
  M18 + M19 + M20 + M21). Target
  for M21.1: audit-execution
  session — no §5 decisions
  land here; scope-lock recorded
  as §0.a amendment.
- **DoD amendment:** formalized
  at M21.0 §5.f Option B —
  every future customer-facing
  milestone must add or update
  at least one Playwright
  operational journey, or
  explicitly document in §3 why
  no journey change is required.
  Applies from M21 forward.
- **Guiding principle for M21+
  Operational Surface
  Completion:** every M21
  shipped surface maps to an
  already-shipped backend
  capability, closes a missing
  operator-facing UI, adds or
  extends a Playwright
  operational journey, and is
  not generic UX polish.
