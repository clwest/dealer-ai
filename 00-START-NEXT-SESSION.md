---
state: active
date: 2026-08-03
last_session_shipped: SESSION_179
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
milestone_23_status: shipped
next_session: SESSION_180
next_milestone: 24
next_milestone_name: "(target selection pending — locked at M24.0 open)"
next_increment: 0
next_increment_name: "M24.0 — Planning refinement + target selection"
---

# Next session — SESSION_180 · Milestone 24 · Increment 0 (M24.0 — planning refinement + target selection)

> **Milestone 23 — BHPH Origination
> + Payment Intake — SHIPPED at
> SESSION_179.** Five-increment
> milestone across SESSION_175 →
> SESSION_179. Milestone shape
> matched planned 5-increment
> target exactly (no shape
> shrinkage, unlike M21.4/M22.3).
> **Backend baseline 4,766 →
> 4,780** (+14). Frontend Vitest
> **180 → 193** (+13). Acceptance
> suite **7 → 9 journeys**. Full
> clean-DB dry-run: **15 passed
> (~20.5s)**.
>
> **BHPH lifecycle now
> operationally complete** —
> every M12 verb reachable
> through the product with
> Playwright acceptance
> coverage.
>
> **Zero-drift permission-class
> streak extends 22 → 23**
> consecutive milestones (M10
> → M23). **Planning-time as-
> recommended streak extends
> 88 → 89** across fourteen
> consecutive milestones.
>
> **First M23 push executed at
> M23.4** — all five M23
> commits surface to
> `origin/main` in one
> coordinated push per M18/M19/M20/M21/M22
> cadence. **First real M23 CI
> run fires on that push —
> verify status at M24.0 open.**
>
> **NEW audit-verified genuine
> gap surfaced at M23.1:** JE
> creation UI
> (`admin-journal-entry-create`)
> reclassified from covered
> (false-positive) to defer-
> candidate-O2. Highest per-
> item operational-coverage
> delta at smallest scope
> among M24 candidates.
>
> **SESSION_180 opens M24.0 —
> planning refinement + target
> selection.** No target
> locked yet — the candidate
> list surfaces at open
> (elevated: Candidate A2 JE
> creation UI [NEW at M23.1],
> Candidate H test-hygiene
> [expanded at M23.2],
> Candidate O2 next OSC
> iteration; gated: T/U/L/M;
> deferred pending evidence:
> D/C; deferred but stable:
> G). The assistant
> recommends one option with
> rationale grounded in the
> primary operational-
> coverage lens; the user
> confirms or redirects.
> Streak 89 → 90 expected on
> confirm-as-recommended.

## First thing SESSION_180 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M23.4 close-
  out commit; `origin/main`
  should now be at the same
  head (push already executed
  at M23.4).
- `python3 manage.py test dealer_ai`
  → **4,780 pass, 1 skipped,
  0 fail**.
- `cd frontend && npm test` →
  **193 pass**.
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

### 2. Monitor first M23 CI run

The M23.4 push at SESSION_179
was the first push of the M23
commits. The acceptance job
fires on that `main` push —
verify its status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a
M24.0 amendments before
opening §5.a.

**If green:** M23 is CI-
verified shipped; proceed
to §3.

### 3. Regenerate the audit artifact

Before candidate presentation,
rerun the audit tooling:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Post-M23.1 fix the audit is
trustworthy for BHPH +
accounting. Other domains may
still have latent false-
positive/negative classes.

### 4. Present the M24 candidate list

Per
`docs/roadmap/MILESTONE_24_PLANNING.md`
skeleton (§Candidate list):

**Elevated (highest
recommendation strength at
M24.0):**

- **Candidate A2 — JE creation
  UI (NEW at M23.1).** Ships
  new `createJournalEntry`
  wrapper + form + Playwright
  journey for
  `admin-journal-entry-create`
  (POST
  `/admin/accounting/journal-
  entries/`). Small bounded
  scope; matches M23.2/M23.3
  shipping shape. **Highest
  per-item operational-
  coverage delta at smallest
  scope** — leads the
  operational-coverage-lens
  ranking.
- **Candidate H — test-hygiene
  remediation (expanded at
  M23).** Extends three
  affected seeds (freeze
  snapshot, lead-assignment,
  recon-decision) with cleanup
  + sweeps session-
  invalidation `set_password`
  pattern across other seeds.
  Small scope, high engineering-
  velocity value.
- **Candidate O2 — next OSC
  iteration.** Selects from
  remaining ~40
  `defer-candidate-O2`
  endpoints. Sub-scope options
  unchanged from M22/M23:
  F&I substrate (large — 16
  endpoints — warrants
  dedicated F&I milestone),
  lead-source-specific intake
  forms (4), deal-writeup
  lifecycle (3), test-drive
  creation (2).

**Gated candidates:**

- **Candidate T** — process
  real tester feedback.
- **Candidate U** — hosted-
  demo substrate.
- **Candidate L** — first-
  live-pilot staging.
- **Candidate M** — multi-
  operator support. **Breaks
  zero-drift streak with
  intent.**

**Deferred pending
evidence:**

- **Candidate D** — LLM
  router / cost caps.
- **Candidate C** — F&I
  chargeback substrate.

**Deferred but stable:**

- **Candidate G** —
  dashboard testid hardening.

Present each with two-
sentence scope + operator
pain resolved + dependency
notes, then present the
recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in
the **primary operational-
coverage lens** ("which
candidate most increases
operational coverage for a
dealership employee?").
Additional considerations:

- Operator pain resolved.
- Dependencies on shipped
  substrate.
- Whether the candidate
  blocks future milestones
  or is blocked by them.
- Whether the M23 CI run
  surfaced any operational
  friction that reshuffles
  priority.
- Whether Candidate A2
  (JE creation UI, small
  scope, high per-item
  delta) is the natural
  extension of M22
  Accounting Operational
  Validation + M23 BHPH
  bookend-completion
  pattern.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the
standard six-to-eight
load-bearing decisions with
confirm-as-recommended
posture. Streak target: **89
→ 90** planning-time as-
recommended M5.1 → M24.0
across fifteen consecutive
milestones.

### 7. DoD compliance check

Per the M21.0 §5.f amendment:
the M24 active memo §3 must
either name a Playwright
journey addition or extension
OR explicitly document why
no journey change is required
(infrastructure-only
milestones only).

### 8. Expand M24 planning skeleton

`MILESTONE_24_PLANNING.md`
exists as a draft skeleton.
SESSION_180 expands to full
active memo per the standard
shape.

### 9. Ship the M24.0 handoff

- `docs/handoffs/SESSION_180_m24_inc0_planning.md`.
- **Do NOT push** — M24.0 is
  planning only; coordinated
  push at M24 close.

## Non-goals for SESSION_180

- ❌ Do NOT ship any backend
  or frontend code — planning-
  only session.
- ❌ Do NOT open any M24
  implementation increment.
- ❌ Do NOT force-push or
  amend earlier commits.
- ❌ Do NOT modify M1-M23
  shipped surface.
- ❌ Do NOT modify the
  acceptance suite unless CI
  regression fixes land as
  §0.a M24.0 amendments.
- ❌ Do NOT skip the DoD
  compliance check.

## Baseline expected at close

Backend + frontend unchanged
from M23 close. Acceptance
suite unchanged. Only
planning docs change.

## NEXT TASK

Start SESSION_180 with (a)
starting-state verification,
(b) monitor first real M23
acceptance CI run + fix any
regressions as §0.a M24.0
amendments, (c) regenerate
the audit artifact, (d)
present the candidate list
with recommendation +
rationale under primary
operational-coverage lens,
(e) await user confirmation
of §5.a, (f) draft §5.b–§5.h
with confirm-as-recommended
posture, (g) DoD compliance
check on §3 draft, (h)
expand the M24 planning
skeleton into a full active
memo, (i) ship the M24.0
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M23 shipped section landed
   at M23.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (skeleton — expanded at
   SESSION_180)
6. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
   §8 (M23 corrections) + §9
   (standing M24 question)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit-driven scope pool —
   authoritative for BHPH +
   accounting post-M23.1)
8. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing contract
   inherited by UI-creation-
   shape M24 candidates)
9. `docs/CAPABILITY_MATRIX.md`
   §7x (M23 shipped surface)
10. `docs/handoffs/SESSION_179_m23_inc4_close.md`
    (M23 shipped)

Narrative docs are claims.
Rules + research + code are
facts.

---

## Operational state (post-SESSION_179 — Milestone 23 SHIPPED)

- **Backend (local):** Django
  on `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,780 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT
  active.
- **Frontend (local):** Vite
  on `:5173`. `tsc --noEmit`
  + `vite build` clean.
  **Vitest baseline: 193
  pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49
  + TS 5.6 operational;
  **nine journeys** passing
  end-to-end on clean DB.
  Full dry-run baseline:
  **15 passed (~20.5s)** (6
  setup + 9 journeys).
- **Acceptance (CI):** live
  on
  `.github/workflows/acceptance.yml`.
  First real M23 CI run
  triggered by the M23.4
  push at SESSION_179 —
  status verified at
  SESSION_180 open.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1
  → **M23**. M24 target
  selection pending
  (SESSION_180).
- **DRF admin surface:**
  **113** endpoints.
- **Frontend operator
  routes:** **20**.
- **Public endpoints:** +1
  M6.5 showroom.
- **Service surface:** all
  M1–M23 packages unchanged.
  M23 added zero service
  verbs.
- **Frontend surfaces:** M23
  added two components
  (`RecordBhphNoteForm` on
  BHPH portfolio Notes card
  as CTA + Dialog;
  `RecordBhphPaymentForm`
  inline in note detail
  Payments card). No new
  routes.
- **Tenancy carriers:**
  **52**.
- **Permission classes:**
  **7 actual** — zero-drift
  streak **twenty-three
  consecutive milestones**
  (M10 → M23).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 23 status:**
  SHIPPED (SESSION_179 close-
  out landed all documentation
  + status flips + M24
  skeleton + coordinated
  close-out commit + first
  M23 push).
- **BHPH lifecycle
  operationally complete:**
  M12 backend + M12.7 read
  UI + M20.4 Playwright +
  M21.2 collections write-
  side + M23.2 origination
  + M23.3 payment intake.
- **Audit tooling:**
  authoritative for BHPH +
  accounting endpoints
  post-M23.1 fix. Rerun at
  M24.0 open to reflect any
  drift.
- **§9 evidence for M24:**
  Candidate A2 JE creation
  UI (NEW, highest per-item
  operational-coverage delta
  under primary lens),
  Candidate H test-hygiene
  (expanded with session-
  invalidation seed pattern
  sweep), Candidate O2 next
  OSC iteration (remaining
  sub-scopes: F&I 16, lead-
  source intake 4, deal-
  writeup 3, test-drive 2).
- **Planning-time streak:**
  **89 as-recommended M5.1
  → M23.0** across fourteen
  consecutive milestones.
  Target for M24.0: 89 →
  90 across fifteen.
- **DoD amendment (M21.0
  §5.f Option B):** every
  future customer-facing
  milestone must add or
  update at least one
  Playwright operational
  journey, or explicitly
  document in §3 why no
  journey change is
  required. Applies to
  M24 forward.
- **M23 audit coverage at
  close:** 108 / 153
  endpoints covered post-
  M23.1 fix; 45 backend-
  only remain for future
  OSC scope selection.
