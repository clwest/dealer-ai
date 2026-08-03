---
state: active
date: 2026-08-03
last_session_shipped: SESSION_170
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
milestone_21_status: shipped
next_session: SESSION_171
next_milestone: 22
next_milestone_name: "(target selection pending — locked at M22.0 open)"
next_increment: 0
next_increment_name: "M22.0 — Planning refinement + target selection"
---

# Next session — SESSION_171 · Milestone 22 · Increment 0 (M22.0 — planning refinement + target selection)

> **Milestone 21 — Operational Surface
> Completion — SHIPPED at SESSION_170.**
> Five-increment milestone across
> SESSION_166 → SESSION_170 (M21.4
> collapsed per audit evidence). Audit
> tooling + artifact + 10 new
> components + 7 new bhphApi.ts write
> wrappers + 2 seed extensions + 2
> journey extensions. **Backend
> baseline 4,755 → 4,761 pass** (+6,
> zero regressions). Frontend Vitest
> **153 → 180 pass** (+27). Full local
> acceptance dry-run: **12 passed
> (~18s)** — 6 setup + 6 journeys.
>
> **Zero-drift permission-class streak
> extended from twenty → twenty-one
> consecutive milestones** (M10 →
> M21). **Planning-time as-recommended
> streak extends 86 → 87** across
> twelve consecutive milestones.
>
> **First M21 push executed at M21.5**
> (SESSION_170) — all five M21 commits
> surface to `origin/main` in one
> coordinated push per M18/M19/M20
> cadence. **First real M21 CI run
> fires on that push — verify status
> at M22.0 open.**
>
> **DoD amendment formalized in
> `docs/roadmap/IMPLEMENTATION_ROADMAP.md`**
> — every future customer-facing
> milestone MUST add or update at
> least one Playwright operational
> journey, or explicitly document in
> §3 why no journey change is
> required. Applies from M22 forward.
>
> **SESSION_171 opens M22.0 —
> planning refinement + target
> selection.** No target locked yet
> — the candidate list surfaces at
> open (elevated: Candidate A +
> Candidate O2; gated: T / U / L /
> M; deferred pending evidence: D /
> C; deferred but stable: P / G).
> The assistant recommends one
> option with rationale; the user
> confirms or redirects. Once §5.a
> locks, §5.b–§5.h planning-time
> decisions get drafted with
> confirm-as-recommended posture
> expected (streak 87 → 88 across
> thirteen consecutive milestones).

## First thing SESSION_171 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M21.5 close-out
  commit; `origin/main` should now
  be at the same head (push
  already executed at M21.5).
- `python3 manage.py test dealer_ai`
  → **4,761 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **180 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Monitor first M21 CI run

The M21.5 push at SESSION_170 was
the first push of the M21 commits.
The acceptance job fires on that
`main` push — verify its status
via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M22.0
amendments before opening §5.a
target selection. The CI
environment may surface an issue
that didn't appear locally (e.g.
Playwright browser cache, seed
timing, env-var drift). Fix +
push before proceeding.

**If green:** M21 is CI-verified
shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation,
rerun the audit tooling:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Any endpoint that shipped between
M21.5 close and M22.0 open will
show up. Fresh evidence prevents
proposing scope that's already
partially covered.

### 4. Present the M22 candidate list

Per
`docs/roadmap/MILESTONE_22_PLANNING.md`
skeleton (§Candidate list):

**Elevated (highest
recommendation strength at
M22.0):**

- **Candidate A — Return to
  accounting stream (bounded
  scope).** Four consecutive
  milestones diverging from the
  M18 §8 accounting designation.
  The M21.1 audit surfaced three
  accounting endpoints
  (`journal-entry-reverse` +
  `trial-balance-snapshot-create
  / list / retrieve`) with
  `defer-domain-milestone`
  disposition — a bounded scope
  target that maps to shipped
  backend + missing UI and can
  honor the M21 governing
  contract.
- **Candidate O2 — Next OSC
  iteration.** Selects from the
  44 `defer-candidate-O2`
  endpoints. Sub-scope options:
  F&I write substrate (16
  endpoints — needs internal
  narrowing to two anchor
  workflows); lead-source-
  specific intake forms (4);
  BHPH note origination +
  payment intake (2); deal-
  writeup lifecycle (3).

**Gated candidates:**

- **Candidate T** — process
  real tester feedback
  (M18.5). Gated on Chris
  running tester sessions
  between M21 close and
  M22.0 open.
- **Candidate U** — hosted-
  demo substrate. Gated on
  demo-scaling willingness.
- **Candidate L** — first-
  live-pilot staging dry-run.
  Gated on real pilot dealer
  + staging environment.
- **Candidate M** — multi-
  operator support. Gated on
  second operator.

**Deferred pending
evidence:**

- **Candidate D** — LLM
  router / cost caps.
- **Candidate C** — F&I
  chargeback substrate.

**Deferred but stable:**

- **Candidate P** —
  onboarding UX polish.
- **Candidate G** —
  dashboard testid hardening.

Present each with two-
sentence scope + operator
pain resolved + dependency
notes, then present the
recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in:

- Operator pain resolved.
- Dependencies on shipped
  substrate.
- Whether the candidate blocks
  future milestones or is
  blocked by them.
- Whether the M21 CI run
  surfaced any operational
  friction that reshuffles
  priority.
- Whether accounting-stream
  divergence (now four
  consecutive milestones)
  needs correction.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the
standard six-to-eight load-
bearing decisions with
confirm-as-recommended posture.
Streak target: **87 → 88**
planning-time as-recommended
M5.1 → M22.0 across thirteen
consecutive milestones.

### 7. DoD compliance check

Per the M21.0 §5.f amendment
now formalized in
IMPLEMENTATION_ROADMAP: the
M22 active memo §3 must either
name a Playwright journey
addition or extension OR
explicitly document why no
journey change is required
(infrastructure-only
milestones only). Non-
adherence is a planning-memo
review finding.

### 8. Expand M22 planning skeleton

`MILESTONE_22_PLANNING.md`
exists as a draft skeleton.
SESSION_171 expands to full
active memo: frontmatter
`status: draft` → `status:
active`; `milestone_name`
populated from §5.a lock; §1
business context + §2
primitives to extend + §3
deferrals + §5 load-bearing
decisions + §7 increment
sequencing.

### 9. Ship the M22.0 handoff

- `docs/handoffs/SESSION_171_m22_inc0_planning.md`.
- **Do NOT push** — M22.0 is
  planning only; the
  coordinated push happens at
  M22 close per M18/M19/M20/M21
  cadence.

## Non-goals for SESSION_171

- ❌ Do NOT ship any backend or
  frontend code — planning-only
  session.
- ❌ Do NOT open any
  implementation increment —
  M22.1 is a separate session.
- ❌ Do NOT force-push or amend
  earlier commits (M21 close is
  already on `origin/main`).
- ❌ Do NOT modify M1-M21
  shipped surface.
- ❌ Do NOT modify the
  acceptance suite unless CI
  regression fixes land as
  §0.a M22.0 amendments.
- ❌ Do NOT skip the DoD
  compliance check — the M22
  active memo's §3 is now
  required to address the
  amendment.

## Baseline expected at close

Backend + frontend unchanged
from M21 close. Acceptance
suite unchanged. Only planning
docs change.

## NEXT TASK

Start SESSION_171 with (a)
starting-state verification,
(b) monitor first real M21
acceptance CI run + fix any
regressions as §0.a M22.0
amendments, (c) regenerate the
audit artifact, (d) present the
candidate list with
recommendation + rationale,
(e) await user confirmation of
§5.a, (f) draft §5.b–§5.h with
confirm-as-recommended posture,
(g) DoD compliance check on §3
draft, (h) expand the M22
planning skeleton into a full
active memo, (i) ship the
M22.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD amendment
   landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (skeleton — expanded at
   SESSION_171)
6. `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
   §8 (M21 unblocks) + §9
   (standing M22 question — is
   M22 the return-to-accounting
   milestone?)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit-driven scope pool
   for OSC candidates)
8. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (governing contract that
   OSC-shape M22 inherits)
9. `docs/CAPABILITY_MATRIX.md`
   §7v (M21 shipped surface)
10. `docs/handoffs/SESSION_170_m21_inc5_close.md`
    (M21 shipped)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_170 — Milestone 21 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,761 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **six
  journeys** passing end-to-end.
  Full dry-run baseline: **12
  passed (~18s)** (6 setup + 6
  journeys). BHPH re-expanded
  from M20.4 read-only to full
  write coverage at M21.2;
  sales_manager extended at
  M21.3.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  First real M21 CI run
  triggered by the M21.5 push
  at SESSION_170 — status
  verified at SESSION_171
  open.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M21**. M22 target selection
  pending (SESSION_171).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M20 packages unchanged.
  M21 added zero service verbs.
- **Frontend surfaces:** M12.7
  BHPH collector dashboard +
  M11.5/M11.6 sales pages
  extended with 10 M21 write
  components across two
  domains (7 BHPH + 3 sales).
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty-one consecutive
  milestones** (M10 → M21).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 21 status:**
  SHIPPED (SESSION_170 close-
  out landed all documentation
  + status flips + M22 skeleton
  + DoD amendment formalization
  + coordinated close-out
  commit + first M21 push).
- **Audit tooling:** operator-
  invoked from `backend/`
  (`python3 -m dealer_ai.scripts.audit_operational_surface`).
  Rerun at M22.0 open to
  reflect any drift since
  M21.5 regen.
- **Planning-time streak:**
  **87 as-recommended M5.1 →
  M21.0** across twelve
  consecutive milestones.
  Target for M22.0: 87 → 88
  across thirteen.
- **DoD amendment (M21.0
  §5.f Option B, formalized
  in IMPLEMENTATION_ROADMAP
  at M21.5):** every future
  customer-facing milestone
  must add or update at least
  one Playwright operational
  journey, or explicitly
  document in §3 why no
  journey change is required.
  Applies from M22 forward.
- **M21 audit coverage at
  close:** 106 / 153 endpoints
  covered; 47 backend-only
  findings distributed across
  `defer-candidate-O2` (~41),
  `defer-domain-milestone` (3),
  `intentional-omission` (7).
  Elevated M22 candidates
  drawn from these buckets.
