---
state: active
date: 2026-08-03
last_session_shipped: SESSION_174
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
milestone_22_status: shipped
next_session: SESSION_175
next_milestone: 23
next_milestone_name: "(target selection pending — locked at M23.0 open)"
next_increment: 0
next_increment_name: "M23.0 — Planning refinement + target selection"
---

# Next session — SESSION_175 · Milestone 23 · Increment 0 (M23.0 — planning refinement + target selection)

> **Milestone 22 — Accounting
> Operational Validation — SHIPPED
> at SESSION_174.** Four-increment
> milestone across SESSION_171 →
> SESSION_174 (M22.3 collapsed per
> §5.b evidence — second
> consecutive milestone where
> §5.h Option B evidence-sized
> posture shrank the shape after
> M21.4's collapse). Audit tooling
> correction + JE reversal
> Playwright journey + reversible-
> JE seed fixture + 2 new
> assertion helpers. **Backend
> baseline 4,761 → 4,766** (+5,
> zero regressions). Frontend
> Vitest unchanged at 180 — zero
> frontend components per §5.a
> refined framing. Full clean-DB
> acceptance suite: **13 passed
> (~18s)** — 6 setup + 7
> journeys.
>
> **Zero-drift permission-class
> streak extends 21 → 22
> consecutive milestones** (M10
> → M22). **Planning-time as-
> recommended streak extends
> 87 → 88** across thirteen
> consecutive milestones.
>
> **First M22 push executed at
> M22.4** (SESSION_174) — all
> four M22 commits surface to
> `origin/main` in one
> coordinated push per M18/M19/M20/M21
> cadence. **First real M22 CI
> run fires on that push —
> verify status at M23.0
> open.**
>
> **Governing-contract
> refinement introduced at
> M22.0** — validation-shape
> milestones require shipped
> frontend surface AND shipped
> backend capability, use
> journey-as-verifier, and
> split discovered gaps by
> size. Formalized in
> CAPABILITY_MATRIX §7w and
> MILESTONE_22_RETROSPECTIVE.md §7.
>
> **SESSION_175 opens M23.0 —
> planning refinement + target
> selection.** No target locked
> yet — the candidate list
> surfaces at open (elevated:
> Candidate H — NEW
> test-hygiene remediation; A2
> — next accounting iteration;
> O2 — next OSC iteration;
> gated: T / U / L / M;
> deferred pending evidence:
> D / C; deferred but stable:
> P / G). The assistant
> recommends one option with
> rationale; the user confirms
> or redirects. Once §5.a
> locks, §5.b–§5.h planning-
> time decisions get drafted
> with confirm-as-recommended
> posture expected (streak 88
> → 89 across fourteen
> consecutive milestones).

## First thing SESSION_175 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M22.4 close-
  out commit; `origin/main`
  should now be at the same
  head (push already executed
  at M22.4).
- `python3 manage.py test
  dealer_ai` → **4,766 pass,
  1 skipped, 0 fail**.
- `cd frontend && npm test` →
  **180 pass**.
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

### 2. Monitor first M22 CI run

The M22.4 push at SESSION_174
was the first push of the M22
commits. The acceptance job
fires on that `main` push —
verify its status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a
M23.0 amendments before opening
§5.a target selection.

**If green:** M22 is CI-verified
shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation,
rerun the audit tooling:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Post-M22.1 fix the audit is
trustworthy for accounting.
Other domains may still have
variable-first URL-assembly
false negatives worth
correcting — any endpoint that
was `defer-candidate-O2` on the
regen but is actually consumed
by a wrapper with a
`const path = ...` pattern is
a candidate for another
M22.1-shape targeted fix.

### 4. Present the M23 candidate list

Per
`docs/roadmap/MILESTONE_23_PLANNING.md`
skeleton (§Candidate list):

**Elevated (highest
recommendation strength at
M23.0):**

- **Candidate H — Test-
  hygiene remediation (NEW).**
  Extend three affected seeds
  (freeze snapshot cleanup,
  lead-assignment reset,
  recon-decision reset) with
  cleanup analogous to
  M22.2's reversal-cleanup.
  Small scope, high operational
  value.

- **Candidate A2 — Next
  accounting iteration
  (bounded scope).** Ship
  operator UI or Playwright
  journeys for accounting gaps
  identified during M22.2
  §5.b walk (as-of picker,
  cost-posting failures
  rendering, JE list
  navigation) plus any gaps
  surfaced by a dedicated
  accounting sub-audit at
  M23.0 open.

- **Candidate O2 — Next OSC
  iteration.** Selects from
  the 40+ `defer-candidate-O2`
  endpoints. Sub-scope options:
  F&I write substrate (16
  endpoints); lead-source
  intake forms (4); BHPH note
  origination + payment
  intake (2); deal-writeup
  lifecycle (3).

**Gated candidates:**

- **Candidate T** — process
  real tester feedback
  (M18.5). Gated on Chris
  running tester sessions.
- **Candidate U** — hosted-
  demo substrate. Gated on
  demo-scaling willingness.
- **Candidate L** — first-
  live-pilot staging dry-run.
  Gated on real pilot +
  staging env.
- **Candidate M** — multi-
  operator support. Gated on
  second operator.

**Deferred pending evidence:**

- **Candidate D** — LLM
  router / cost caps.
- **Candidate C** — F&I
  chargeback substrate.

**Deferred but stable:**

- **Candidate P** —
  onboarding UX polish.
- **Candidate G** —
  dashboard testid
  hardening.

Present each with two-
sentence scope + operator
pain resolved + dependency
notes, then present the
recommendation.

### 5. Recommend a target for §5.a

**Primary evaluation lens** (durable
guidance carried forward from M22
close):

> **Which candidate most increases
> operational coverage for a
> dealership employee?**

Evaluate every candidate through
this lens first. Endpoint count,
implementation effort, and roadmap
momentum are secondary signals for
tie-breaking within candidates that
score comparably on operational
coverage. Bounded infrastructure-
adjacent candidates (Candidate H is
the current example) can win via
"increases coverage RELIABILITY
across all existing journeys"
framing — reliability is a form of
coverage.

Then ground the recommendation in:

- **PRIMARY:** operational coverage
  delta for a dealership employee.
  Which employee-persona workflow
  does this candidate enable, make
  more reliable, or bring under
  Playwright end-to-end validation?
- Operator pain resolved.
- Dependencies on shipped substrate.
- Whether the candidate blocks
  future milestones or is blocked
  by them.
- Whether the M22 CI run surfaced
  any operational friction that
  reshuffles priority.
- Whether the M22 §9 evidence
  points more strongly at one
  candidate than others.
- Whether Candidate H's small
  scope + high operational
  value argues for a "quick
  win" milestone before
  returning to larger scope
  work.

Explicitly note candidates with
LOW operational-coverage delta —
they need a strong case on other
dimensions to win.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the
standard six-to-eight load-
bearing decisions with
confirm-as-recommended posture.
Streak target: **88 → 89**
planning-time as-recommended
M5.1 → M23.0 across fourteen
consecutive milestones.

### 7. DoD compliance check

Per the M21.0 §5.f amendment:
the M23 active memo §3 must
either name a Playwright
journey addition or extension
OR explicitly document why no
journey change is required
(infrastructure-only
milestones only). Non-
adherence is a planning-memo
review finding.

**Also verify §3 addresses the
compound operational contract**
carried forward from M20-M22:
(a) verify through the real
application before locking
scope; (b) let evidence drive
roadmap decisions; (c) keep
milestones tightly bounded;
(d) extend Playwright journeys
whenever customer-facing
operational behavior changes;
(e) allow completed operational
journeys to reveal the next
highest-value work rather than
planning from assumptions. Any
§5 decision that violates one
of these should be flagged
before locking.

### 7a. Planning artifact generation discussion (standing topic)

Not necessarily M23 scope, but
include as a standing
discussion topic at planning
time. Which planning artifacts
are mature enough for
generation from the codebase?
Current examples of the
maturity threshold catalogued in
`MILESTONE_23_PLANNING.md`
§"Planning artifact generation
discussion" — flag candidates
in retrospective §9 or elevate
to scope when hand-maintenance
cost exceeds generation tooling
cost.

### 8. Expand M23 planning skeleton

`MILESTONE_23_PLANNING.md`
exists as a draft skeleton.
SESSION_175 expands to full
active memo: frontmatter
`status: draft` → `status:
active`; `milestone_name`
populated from §5.a lock; §1
business context + §2
primitives to extend + §3
deferrals + §5 load-bearing
decisions + §7 increment
sequencing.

### 9. Ship the M23.0 handoff

- `docs/handoffs/SESSION_175_m23_inc0_planning.md`.
- **Do NOT push** — M23.0 is
  planning only; the
  coordinated push happens at
  M23 close per M18/M19/M20/M21/M22
  cadence.

## Non-goals for SESSION_175

- ❌ Do NOT ship any backend or
  frontend code — planning-only
  session.
- ❌ Do NOT open any
  implementation increment —
  M23.1 is a separate session.
- ❌ Do NOT force-push or amend
  earlier commits (M22 close is
  already on `origin/main`).
- ❌ Do NOT modify M1-M22
  shipped surface.
- ❌ Do NOT modify the
  acceptance suite unless CI
  regression fixes land as
  §0.a M23.0 amendments.
- ❌ Do NOT skip the DoD
  compliance check — the M23
  active memo's §3 is now
  required to address the
  amendment.

## Baseline expected at close

Backend + frontend unchanged
from M22 close. Acceptance
suite unchanged. Only planning
docs change.

## NEXT TASK

Start SESSION_175 with (a)
starting-state verification,
(b) monitor first real M22
acceptance CI run + fix any
regressions as §0.a M23.0
amendments, (c) regenerate the
audit artifact, (d) present the
candidate list with
recommendation + rationale,
(e) await user confirmation of
§5.a, (f) draft §5.b–§5.h with
confirm-as-recommended posture,
(g) DoD compliance check on §3
draft, (h) expand the M23
planning skeleton into a full
active memo, (i) ship the
M23.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section landed
   at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (skeleton — expanded at
   SESSION_175)
6. `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
   §8 (M22 corrections) + §9
   (standing M23 question)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit-driven scope pool
   for OSC candidates —
   authoritative for accounting
   post-M22.1 fix)
8. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (M22 refined governing
   contract that any
   validation-shape M23
   inherits)
9. `docs/CAPABILITY_MATRIX.md`
   §7w (M22 shipped surface)
10. `docs/handoffs/SESSION_174_m22_inc4_close.md`
    (M22 shipped)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_174 — Milestone 22 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,766 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **seven
  journeys** passing end-to-end
  on clean DB. Full dry-run
  baseline: **13 passed
  (~18s)** (6 setup + 7
  journeys). M22.2 added
  `office/accounting_je_reversal.spec.ts`.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  First real M22 CI run
  triggered by the M22.4 push
  at SESSION_174 — status
  verified at SESSION_175
  open.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M22**. M23 target selection
  pending (SESSION_175).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M22 packages unchanged.
  M22 added zero service verbs.
- **Frontend surfaces:** all
  M1–M22 pages unchanged. M22
  added zero components (per
  §5.a refined framing —
  validation, not creation).
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty-two consecutive
  milestones** (M10 → M22).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 22 status:**
  SHIPPED (SESSION_174 close-
  out landed all documentation
  + status flips + M23 skeleton
  + coordinated close-out
  commit + first M22 push).
- **Audit tooling:** operator-
  invoked from `backend/`
  (`python3 -m dealer_ai.scripts.audit_operational_surface`).
  **Now authoritative for
  accounting endpoints** post-
  M22.1 fix. Other domains
  may still have variable-
  first URL-assembly false
  negatives worth correcting.
  Rerun at M23.0 open to
  reflect any drift.
- **Planning-time streak:**
  **88 as-recommended M5.1 →
  M22.0** across thirteen
  consecutive milestones.
  Target for M23.0: 88 → 89
  across fourteen.
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
  Applies to M23 forward. M22
  satisfied by construction
  via the M22.2 JE reversal
  journey addition.
- **M22 refined governing
  contract for validation-
  shape milestones** —
  formalized at M22.0 §5.a
  refinement. Any M23
  candidate that validates
  already-shipped UI
  inherits this contract by
  default; UI-creation
  milestones use the M21
  Candidate O contract shape.
- **M22 audit coverage at
  close:** 110 / 153
  endpoints covered
  (post-M22.1 fix); 43
  backend-only remain for
  future OSC scope
  selection. Down from
  106 / 47 at M22.1 open
  thanks to the four
  accounting reclassifications.
- **M22 §9 evidence-based
  M23 candidates:** Candidate
  H (test-hygiene, NEW) +
  Candidate A2 (next
  accounting iteration) +
  Candidate O2 (next OSC
  iteration). All three fit
  the M22 refined governing
  contract shape.
