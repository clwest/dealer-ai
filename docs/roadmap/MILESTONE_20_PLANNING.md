---
title: "Milestone 20 — (target selection deferred to M20.0)"
status: draft
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_159 (skeleton)
milestone: 20
milestone_name: "(pending — locked at M20.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_18_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_19_RETROSPECTIVE.md
---

# Milestone 20 — Planning skeleton (target TBD at M20.0)

Skeleton drafted at M19.6 close-out
(SESSION_159) per §0.a M19.6 decision 2
(defer target selection to M20.0). This
memo intentionally does NOT lock a
target; SESSION_160 (M20.0) presents
the candidate list, resolves §5.a with
the user, and expands the skeleton into
a full active planning memo per the M18
+ M19 precedent.

## Standing rule

Per the M18 + M19 planning pattern: at
M20.0 open the target selection
proceeds by presenting the full
candidate list, recommending one option
with rationale grounded in operator
pain resolved by that candidate, and
awaiting user confirmation. Once
selected, §5.b–§5.h load-bearing
planning decisions get drafted with
recommendations for confirm-as-
recommended at M20.0 open (streak
extension expected: 85 → 86 planning-
time as-recommended M5.1 → M20.0
across eleven consecutive milestones).

## Candidate list

Compiled from `MILESTONE_18_RETROSPECTIVE.md`
§9 (three candidates surfaced at M18
close) + `MILESTONE_19_RETROSPECTIVE.md`
§9 (nine candidates including the M18
carry-forwards + six new options).

**Business-priority candidates.** In
no particular order — priority ranking
happens at M20.0 with the full brief:

### Candidate T — Process real tester feedback

**Carry-forward from M18 §9.** Gated on
whether Chris runs tester sessions
using the M18 substrate before M20.0
open. Scope depends on volume + quality
of feedback captured via the M18.5
POST endpoint. If no tester sessions
have happened by M20.0 open, this
candidate defers again.

### Candidate U — Hosted-demo substrate (public self-serve signup)

**Carry-forward from M18 §9.** Public
self-serve demo signup + tester-
tracking dashboard. Deferred at M18
per §3. Re-entry gated on Chris's
willingness to hand demo stores to
operators he doesn't already know.

### Candidate A — Return to accounting stream

**M18 retrospective's designated M20
slot per §8.** Multiple sub-candidates:
period-close comparison view / audit,
financial-reports substrate (P&L +
balance sheet), CSV / PDF export of
frozen snapshots, auto-freeze on
schedule, reopen / unfreeze workflow,
M10 chargeback GL reversal, NSF /
payment-reversal workflow, category-
group-aware GL mapping, deposit / bank
reconciliation, BhphFee entity + late-
fee GL posting, BHPH interest accrual
detector. A single M20 in accounting
would pick one and scope it as a
milestone.

### Candidate P — Onboarding UX polish

**New at M19 §9.** Prospect intake UI,
checklist progress bar, terminate-flow
refinements, pilot-list filtering /
search. Scope depends on M19 pilot
conversion friction observed in
practice. Intentionally distinct from
**Candidate J** — the objective here
is UX polish for Chris, not workflow
validation for operators.

### Candidate L — First-live-pilot staging dry-run

**New at M19 §9.** Codify the M19.5
dry-run against a real staging DB with
a real pilot dealer, not just SQLite
test fixtures. Could bundle with
**Candidate J** (Playwright acceptance
testing) since both target executable
operational validation.

### Candidate M — Multi-operator support

**New at M19 §9.** Add
`IsPlatformOperator` permission class
+ update the M19.3 endpoint gating +
extend `list_prospects` with operator
scope. **Breaks the zero-drift streak
with intent.** Re-entry gated on a
second platform operator actually
being introduced.

### Candidate D — Demo-aware LLM router / cost caps

**Carry-forward from M18.1 §0.a
decision 1.** Route LLM calls through
a demo-aware wrapper that either
short-circuits on demo tenants or
rate-limits token consumption. Re-
entry gated on tester usage burning
significant tokens against synthetic
inventory.

### Candidate C — F&I chargeback substrate

**Carry-forward from M18.2 §0.a
decision 1.** F&I scenario milestone
picks up where M10 left off. Re-entry
gated on operator evidence surfacing
demand.

### Candidate J — Operational Journey Validation (Playwright acceptance testing)

**New at M19.6 close-out per §0.a M19.6
decision 2 (expanded candidate list).**
Build durable Playwright acceptance
suites executing real dealership
workflows against the M18 demo stores
and M19 pilot-onboarding substrate.

**Business objective.** Establish
executable operational acceptance
tests as part of the milestone
completion contract — alongside unit
tests, integration tests, capability
matrix updates, and retrospectives.
These are business-workflow validation
scenarios, not generic UI regression
tests.

**Representative journeys.**

- **Owner morning review** — landing
  on the dashboard, scanning yesterday's
  pipeline + realized gross + upcoming
  showings, drilling into the top lead.
- **Sales manager daily startup** —
  reviewing overnight leads, assigning
  to advisors, checking the follow-up
  cadence queue, marking a be-back
  handled.
- **Recon workflow** — receiving a
  new acquisition, ordering the
  condition report, authoring the
  ReconDecision list, dispatching to
  a vendor, marking work complete.
- **Office / accounting workflow** —
  end-of-day trial balance review,
  as_of picker on the journal-entry
  page, drilling into a specific
  posting.
- **BHPH collections workflow** —
  daily book review, recording a
  promise-to-pay, capturing a
  collection contact, initiating
  repossession on a broken promise.
- **Pilot onboarding journey** —
  end-to-end walk of the M19.5
  playbook using the M19.4 admin
  surface: create a pilot, advance
  the checklist, upload inventory,
  confirm readiness.

Each journey executes end-to-end
through the shipped UI and validates
that a dealership can perform
realistic daily operations using
shipped capabilities.

**Intentionally distinct from
Candidate P.** The objective is
business-workflow validation, not
UX polish. Discovered UX friction
during Playwright authoring feeds
Candidate P; failing acceptance
tests feed regression fixes in the
existing capability surface.

**Distinct from Candidate L.**
Candidate L codifies the M19.5
dry-run against staging (backend
substrate contract). Candidate J
codifies operator-facing UI
journeys (frontend + backend
end-to-end contract). Could bundle
if scope allows.

## What M20.0 must do

At SESSION_160 open:

1. **Present the candidate list**
   above with a recommendation +
   rationale per candidate.
2. **Recommend a target** for §5.a
   selection. Ground the
   recommendation in:
   - Operator pain resolved.
   - Dependencies on already-shipped
     substrate.
   - Deferred items with re-entry
     paths.
3. **Await user confirmation** or
   redirection to a different
   candidate.
4. **Once §5.a locks**, draft §5.b–
   §5.h load-bearing planning
   decisions with recommendations
   for confirm-as-recommended at
   M20.0 open. Streak 85 → 86
   expected.
5. **Expand this skeleton** into a
   full active planning memo
   analogous to
   `MILESTONE_18_PLANNING.md` /
   `MILESTONE_19_PLANNING.md`.
   Frontmatter `status: draft` →
   `status: active`; `milestone_name`
   populated from §5.a.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target at
  M19.6.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M19.6 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate at
  M19.6.
- ❌ Do NOT rewrite the candidate
  list order to imply priority
  — that's the M20.0 open
  exercise.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (this candidate list's
   source of truth)
6. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 + §9 (carry-forward
   candidates)
7. `docs/CAPABILITY_MATRIX.md`
   (verified surface for scope
   grounding)
