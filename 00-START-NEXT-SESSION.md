---
state: active
date: 2026-08-02
last_session_shipped: SESSION_165
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
next_session: SESSION_166
next_milestone: 21
next_milestone_name: "(target selection pending — locked at M21.0 open)"
next_increment: 0
next_increment_name: "M21.0 — Planning refinement + target selection"
---

# Next session — SESSION_166 · Milestone 21 · Increment 0 (M21.0 — planning refinement + target selection)

> **Milestone 20 — Operational Journey
> Validation (Playwright acceptance
> testing) — SHIPPED at SESSION_165.**
> Six-increment milestone across
> SESSION_160 → SESSION_165. Framework
> substrate + support layer + six
> journey specs + six seed delta
> commands + GitHub Actions CI job +
> settings.py env branch. Zero new
> tenancy carriers, zero new endpoints,
> zero new migrations, zero new
> permission classes, zero new
> frontend routes. **Backend baseline
> 4,679 → 4,755 pass** (+76, zero
> regressions). Frontend Vitest **153
> pass** (unchanged — acceptance is a
> separate test surface). Full local
> acceptance dry-run: **12 passed
> (~18s)** — 6 setup + 6 journeys.
>
> **Zero-drift permission-class streak
> extended from nineteen → twenty
> consecutive milestones** (M10 → M20).
> **Planning-time as-recommended streak
> extends 85 → 86** across eleven
> consecutive milestones.
>
> **First push executed at M20.5**
> (SESSION_165) — all six M20 commits
> surfaced to `origin/main` in one
> coordinated push per M18/M19 cadence.
> **First real GitHub Actions
> acceptance CI run fires on that push
> — verify status at M21.0 open.**
>
> **SESSION_166 opens M21.0 —
> planning refinement + target
> selection.** No target locked yet
> — the ten-candidate list surfaces
> at open (8 carry-forwards from
> M19 §9 + 2 new from M20 §8), the
> assistant recommends one option
> with rationale, the user confirms
> or redirects. Once §5.a locks,
> §5.b–§5.h planning-time decisions
> get drafted with confirm-as-
> recommended posture expected
> (streak 86 → 87 across twelve
> consecutive milestones).

## First thing SESSION_166 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top should
  be the M20.5 close-out commit;
  `origin/main` should now be at the
  same head (push already executed
  at M20.5).
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

### 2. Monitor first CI run

The M20.5 push at SESSION_165 was the
first push of the M20 commits +
`.github/workflows/acceptance.yml`.
The acceptance job fires on that
`main` push — verify its status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M21.0
amendments before opening §5.a
target selection. The CI environment
may surface an issue that didn't
appear locally (Python/Node version
drift, Playwright browser install
differences, permissions, seed-
command ordering under a fresh CI
DB). Fix + push before proceeding.

**If green:** M20 is CI-verified
shipped; proceed to §3.

### 3. Present the M21 candidate list

Ten candidates surfaced from
`MILESTONE_21_PLANNING.md`. Present
each with two-sentence scope +
operator pain resolved + dependency
notes, then present the
recommendation.

**Carry-forward candidates (from
M19 §9):**

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions.
- **Candidate U** — hosted-demo
  substrate (public self-serve
  signup).
- **Candidate A** — return to
  accounting stream. **Elevated
  recommendation strength** at
  M21.0 because M18/M19/M20 all
  diverged from M18 §8's
  accounting designation; three
  consecutive milestones diverging
  risks ossifying the divergence.
- **Candidate D** — demo-aware
  LLM router / cost caps.
- **Candidate C** — F&I chargeback
  substrate.
- **Candidate P** — onboarding UX
  polish.
- **Candidate L** — first-live-
  pilot staging dry-run.
- **Candidate M** — multi-operator
  support. Breaks zero-drift
  streak with intent.

**New at M20 §8:**

- **Candidate B — M12.8 BHPH
  collections write-side UI.**
  Missing UI surfaced by M20.4
  scope narrowing.
- **Candidate G — dashboard testid
  hardening.** Technical debt
  against Playwright journey
  extensions.

### 4. Recommend a target for §5.a

Ground the recommendation in:
- Operator pain resolved.
- Dependencies on shipped
  substrate.
- Whether the candidate blocks
  future milestones or is blocked
  by them.
- Whether the M20 CI run
  surfaced any operational
  friction that reshuffles
  priority.

### 5. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard
six-to-eight load-bearing decisions
with confirm-as-recommended posture.
Streak target: **86 → 87** planning-
time as-recommended M5.1 → M21.0
across twelve consecutive
milestones.

### 6. Expand M21 planning skeleton

`MILESTONE_21_PLANNING.md` exists as
a draft skeleton. SESSION_166
expands to full active memo:
frontmatter `status: draft` →
`status: active`; `milestone_name`
populated from §5.a lock; §1
business context + §2 primitives to
extend + §3 deferrals + §5 load-
bearing decisions + §7 increment
sequencing.

### 7. Ship the M21.0 handoff

- `docs/handoffs/SESSION_166_m21_inc0_planning.md`.
- **Do NOT push** — M21.0 is
  planning only; the coordinated
  push happens at M21 close per
  M18/M19/M20 cadence.

## Non-goals for SESSION_166

- ❌ Do NOT ship any backend or
  frontend code — planning-only
  session.
- ❌ Do NOT open any implementation
  increment — M21.1 is a separate
  session.
- ❌ Do NOT force-push or amend
  earlier commits (M20 close is
  already on `origin/main`).
- ❌ Do NOT modify M1-M20 shipped
  surface.
- ❌ Do NOT modify the acceptance
  suite unless CI regression fixes
  land as §0.a M21.0 amendments.

## Baseline expected at close

Backend + frontend unchanged from
M20 close. Acceptance suite
unchanged. Only planning docs
change.

## NEXT TASK

Start SESSION_166 with (a) starting-
state verification, (b) monitor
first real acceptance CI run + fix
any regressions as §0.a M21.0
amendments, (c) present the ten-
candidate list with recommendation
+ rationale, (d) await user
confirmation of §5.a, (e) draft
§5.b–§5.h with confirm-as-
recommended posture, (f) expand
the M21 planning skeleton into a
full active memo, (g) ship the
M21.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (skeleton — expanded at
   SESSION_166)
6. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 (M20 unblocks) + §9 (standing
   question — is M21 the return-to-
   accounting milestone?)
7. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (carry-forward candidates)
8. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 + §9 (accounting slot
   designation preserved)
9. `docs/CAPABILITY_MATRIX.md` §7u
   (M20 shipped surface)
10. `docs/handoffs/SESSION_165_m20_inc5_close.md`
    (M20 shipped)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_165 — Milestone 20 SHIPPED)

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
  passing end-to-end. Full dry-run
  baseline: **12 passed in ~18s**
  (6 setup + 6 journeys).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  First real CI run triggered by
  the M20.5 push at SESSION_165 —
  status verified at SESSION_166
  open.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M20**. M21 target selection
  pending (SESSION_166).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all M1–M19
  packages unchanged. M20 added
  zero service verbs. **Six seed
  delta management commands** in
  `dealer_ai/management/commands/seed_journey_*.py`.
- **Frontend surfaces:** unchanged
  since M19.4.
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty consecutive
  milestones** (M10 → M20).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 20 status:**
  SHIPPED (SESSION_165 close-out
  landed all documentation +
  status flips + M21 skeleton +
  coordinated close-out commit +
  first push).
- **Planning-time streak:** **86
  as-recommended M5.1 → M20.0**
  across eleven consecutive
  milestones. Target for M21.0:
  86 → 87 across twelve.
- **Guiding principle for M20+
  operational validation:**
  business outcomes through real
  UI on deterministic seeded
  state; not UI automation.
