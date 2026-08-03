---
title: "Milestone 24 — (target selection deferred to M24.0)"
status: draft
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_179 (skeleton + M23-close planning inputs)
milestone: 24
milestone_name: "(pending — locked at M24.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_23_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_23_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7x
---

# Milestone 24 — Planning skeleton (target TBD at M24.0)

Skeleton drafted at M23.4 close-out
(SESSION_179). This memo intentionally
does NOT lock a target; SESSION_180
(M24.0) presents the candidate list,
resolves §5.a with the user, and
expands the skeleton into a full
active planning memo per the M18 /
M19 / M20 / M21 / M22 / M23
precedent.

## Standing rule

Per the M18 / M19 / M20 / M21 / M22 /
M23 planning pattern: at M24.0 open,
target selection proceeds by
presenting the full candidate list,
recommending one option with
rationale grounded in the primary
operational-coverage lens
("which candidate most increases
operational coverage for a
dealership employee?"), and awaiting
user confirmation. Once selected,
§5.b–§5.h load-bearing planning
decisions get drafted with
recommendations for confirm-as-
recommended at M24.0 open (streak
extension expected: 89 → 90
planning-time as-recommended M5.1 →
M24.0 across fifteen consecutive
milestones).

Per the M21.0 §5.f Option B DoD
amendment (formalized in
IMPLEMENTATION_ROADMAP at M21.5,
applied by M22 + M23): the M24
planning memo must either name at
least one Playwright operational
journey addition or extension, OR
document in §3 why no journey change
is required. Infrastructure-only
milestones satisfy via the exception
path.

## Guiding question (durable, per M22 close)

**Which candidate most increases
operational coverage for a
dealership employee?**

This lens governs §5.a target
selection at M24.0. Endpoint count,
implementation effort, roadmap
momentum, and continuity with prior
scope are secondary signals used to
break ties within candidates that
score comparably on operational
coverage.

## Preserve the M20–M23 operational contract (durable)

Compound guidance carried forward
through every M24 decision:

- Verify through the real
  application before locking scope.
- Let evidence drive roadmap
  decisions.
- Keep milestones tightly bounded.
- Extend Playwright journeys
  whenever customer-facing
  operational behavior changes.
- Allow completed operational
  journeys to reveal the next
  highest-value work rather than
  planning from assumptions.
- **NEW at M23 close:** apply
  sibling-pattern discipline —
  first-of-a-kind changes surface
  latent bugs; inherited patterns
  don't. When implementing, look
  for the closest existing pattern
  and follow it exactly;
  deviations require conscious
  justification.

## Planning inputs from M23 close

The M23 BHPH Origination + Payment
Intake milestone surfaced concrete
inputs that must inform M24 target
selection + scope.

### Input 1 — Audit-driven scope pool (post-M23.1 fix)

The M23.1-corrected audit artifact
catalogs **45 backend-only
endpoints** (up from 43 pre-M23.1 as
false-positives got corrected). The
M23.1 fix reclassified two endpoints
that had been falsely covered:

- **`admin-bhph-note-create`** —
  closed by M23.2 origination UI
  (row now `covered` again by
  legitimate wrapper).
- **`admin-journal-entry-create`**
  — **NEW genuine gap**. JE
  creation UI is missing from the
  frontend. `admin/accounting/journal-entries/`
  POST endpoint ships since M13.1
  but has no consumer wrapper in
  `accountingApi.ts`. **Highest-
  priority M24 evidence-based
  candidate.**

Remaining `defer-candidate-O2`
endpoint pool (~40) unchanged in
composition from M22 close (F&I
substrate 16, lead-source intake 4,
deal-writeup 3, BHPH note
origination + payment ✓ shipped
M23, test-drive creation 2,
remaining accounting writes + misc
dashboards).

### Input 2 — Elevated candidates at M24.0 open

Per the M23 retrospective §8 + §9:

**Elevated (recommendation strength
increased at M24 open):**

- **Candidate A2 — JE creation UI
  (NEW at M23.1).** Row 139 audit-
  verified genuine gap. Single new
  wrapper + form + journey
  attached to existing
  `AccountingJournalEntriesPage`
  or `AccountingJournalEntryDetailPage`.
  Small bounded scope; fits M21
  Candidate O UI-creation
  contract; matches M23.2/M23.3
  shipping-shape. **Highest per-
  item operational-coverage delta
  at smallest scope** — leads the
  operational-coverage-lens
  ranking.

- **Candidate H — test-hygiene
  remediation (expanded at M23).**
  Original scope from M22 §9:
  extend three affected seeds
  (freeze snapshot cleanup, lead-
  assignment reset, recon-
  decision reset) with cleanup
  analogous to M22.2's reversal-
  cleanup. **Expanded at M23.2:**
  session-invalidation seed
  pattern sweep — other
  seed_journey_* commands may
  have unconditional
  `set_password` calls that break
  when future journeys re-invoke
  seeds mid-suite. Small scope,
  high engineering-velocity
  value.

- **Candidate O2 — next OSC
  iteration.** Selects from ~40
  remaining `defer-candidate-O2`
  endpoints. Sub-scope options
  unchanged from M22/M23:
  F&I substrate (large — 16
  endpoints — warrants dedicated
  milestone), lead-source-
  specific intake forms (4),
  deal-writeup lifecycle (3),
  test-drive creation (2),
  additional accounting writes
  bundled with A2.

**Gated (external signal
precondition still absent):**

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions between M23
  close and M24.0 open.
- **Candidate U** — hosted-demo
  substrate.
- **Candidate L** — first-live-
  pilot staging dry-run.
- **Candidate M** — multi-
  operator support. **Breaks
  zero-drift permission-class
  streak with intent.**

**Deferred pending evidence:**

- **Candidate D** — demo-aware
  LLM router / cost caps.
- **Candidate C** — F&I
  chargeback substrate.

**Deferred but stable:**

- **Candidate G** — dashboard
  testid hardening.

### Input 3 — DoD amendment binding

M21.0 §5.f Option B (adopt with
documented exception path)
formalized in
`docs/roadmap/IMPLEMENTATION_ROADMAP.md`
at M21.5. Every M24 customer-facing
milestone MUST add or update at
least one Playwright operational
journey OR explicitly document why
not.

### Input 4 — M23 governing-contract precedent

M23 inherited the M21 Candidate O
UI-creation contract successfully.
Any M24 candidate that ships new
UI inherits the same contract by
default. Validation-shape
milestones (like M22) use the M22
refinement.

### Input 5 — M23 velocity data

- M23.0 planning: 1 session.
- M23.1 audit tooling fix: 1
  session (~30-40 min active work
  under ~2-hour budget guard).
- M23.2 note origination: 1
  session (wrapper + form + Vitest
  + seed extension + assertion
  helper + journey + 1 §5.d fix).
- M23.3 payment intake: 1 session
  (same shape as M23.2, first-run
  pass with 0 §5.d fixes).
- M23.4 close-out: 1 session
  (retrospective + capability
  matrix + M24 skeleton + roadmap
  amendment + push).

**Five sessions for one two-anchor
UI-creation milestone.** If M24
picks Candidate A2 (single anchor
UI), expect **~3-4 sessions**
matching M22's four-increment shape
(planning + audit-related supporting
work + anchor UI + close-out). If
M24 picks H (test-hygiene), expect
**~3 sessions** (planning + seed
sweeps + close-out). If M24 picks
O2 with a larger sub-scope, expect
5+ sessions per M23 pattern.

### Input 6 — M23 lessons applied

Sibling-pattern discipline (M23.3
first-run pass) + `invokeSeed()` +
stdout parsing (M23.2 + M23.3) +
"verify at planning open"
discipline (M23.0 → M23.1 →
M23.2 chain) are inheritable to
any M24 candidate. Session-
invalidation seed fix (M23.2 §5.d)
generalizes.

## Candidate list

Compiled from
`MILESTONE_23_RETROSPECTIVE.md` §8 +
§9 + carry-forwards from M19 / M20 /
M21 / M22 / M23 planning skeletons.
**Priority ranking happens at M24.0
with the full brief in hand.**

### Elevated at M24.0

- **Candidate A2 — JE creation UI
  (NEW at M23.1 audit fix).** Per
  M23 retrospective §9. Ships new
  wrapper + form + journey for
  `admin-journal-entry-create`.
  Small bounded scope; matches
  M23.2/M23.3 shipping shape.
  Recommendation strength: HIGH
  under operational-coverage lens
  — smallest scope + highest per-
  item delta + closes an audit-
  verified genuine gap.

- **Candidate H — test-hygiene
  remediation (expanded at M23).**
  Extends three affected seeds
  (freeze snapshot, lead-
  assignment, recon-decision)
  with cleanup + sweeps session-
  invalidation `set_password`
  pattern across other seeds.
  Small scope, high engineering-
  velocity value.
  Recommendation strength:
  MEDIUM-HIGH — indirect
  operational-coverage delta
  (reliability of existing
  coverage) but bounded and high-
  compound-value.

- **Candidate O2 — next OSC
  iteration.** Selects from
  remaining ~40 `defer-candidate-O2`
  endpoints. Sub-scope options
  unchanged from M22/M23.
  Recommendation strength:
  MEDIUM — highest scope; risk of
  scope creep if F&I substrate
  chosen (16 endpoints).

### Gated candidates (from M19 / M20 / M21 / M22 / M23 §9)

- **Candidate T** — tester
  feedback. Gated on tester
  sessions.
- **Candidate U** — hosted-demo.
  Gated on demo-scaling
  willingness.
- **Candidate L** — first-live-
  pilot staging. Gated on real
  pilot + staging env.
- **Candidate M** — multi-
  operator support. Breaks
  zero-drift streak with intent.

### Deferred pending evidence

- **Candidate D** — LLM router /
  cost caps.
- **Candidate C** — F&I
  chargeback substrate.

### Deferred but stable

- **Candidate G** — dashboard
  testid hardening.

### Deferred with re-entry path (M23-specific)

- **Sale-picker UI / deep-link
  for BHPH origination** (M23.2
  §3 deferral 1). Small polish
  scope. Could bundle with a
  future BHPH-adjacent
  enhancement milestone or ship
  standalone.
- **Route URL discovery friction
  → generated planning artifact
  experiment** (M23.2 finding
  linked to M22 durable-lesson
  memory). Small experimental
  scope; potentially catalyzes
  broader planning-artifact
  automation work. Not urgent.
- **Full AST-based audit rewrite**
  (M21.4 / M22.1 / M23.1 non-
  goal). Only warranted if
  patterns arise that break the
  regex + parser approach
  entirely.

## What M24.0 must do

At SESSION_180 (or whenever M24.0
opens):

1. **Verify CI status** on the M23
   push. First real M23 CI run
   fires on the M23.4 push —
   verify status.
2. **Regenerate the audit artifact**
   before candidate presentation.
   Any endpoint that shipped
   between M23.4 close and M24.0
   open will show up. Post-M23.1
   fix the audit is trustworthy
   for BHPH + accounting; other
   domains may still have latent
   false-positive/negative
   classes.
3. **Present the candidate list**
   above with a recommendation +
   rationale per candidate.
   Explicitly note the two-way
   tie between Candidate A2
   (highest per-item operational-
   coverage delta at smallest
   scope) and Candidate H
   (bounded infrastructure with
   high engineering-velocity
   value).
4. **Recommend a target** for
   §5.a selection under the
   primary operational-coverage
   lens.
5. **Await user confirmation** or
   redirection.
6. **Once §5.a locks**, draft
   §5.b–§5.h load-bearing
   planning decisions with
   recommendations for confirm-
   as-recommended posture.
   Streak target: 89 → 90
   across fifteen consecutive
   milestones.
7. **DoD amendment compliance
   check** on §3 draft.
8. **Expand this skeleton** into
   a full active planning memo.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target at
  M23.4. Inputs 1–6 inform the
  recommendation at M24.0 open;
  they do not preempt it.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M23.4 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate at
  M23.4.
- ❌ Do NOT rewrite the candidate
  list order to imply priority
  — that's the M24.0 open
  exercise.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
   §8 + §9 (M23 corrections +
   standing M24 question)
6. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (M23 governing contract
   inherited by UI-creation-
   shape M24 candidates)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — authoritative
   for BHPH + accounting post-
   M23.1)
8. `docs/CAPABILITY_MATRIX.md`
   §7x (M23 shipped surface)
