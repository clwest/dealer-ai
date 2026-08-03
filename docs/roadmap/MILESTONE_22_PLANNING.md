---
title: "Milestone 22 — (target selection deferred to M22.0)"
status: draft
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_170 (skeleton + M21-close planning inputs)
milestone: 22
milestone_name: "(pending — locked at M22.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_21_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_21_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7v
---

# Milestone 22 — Planning skeleton (target TBD at M22.0)

Skeleton drafted at M21.5 close-out
(SESSION_170). This memo intentionally
does NOT lock a target; SESSION_171
(M22.0) presents the candidate list,
resolves §5.a with the user, and
expands the skeleton into a full active
planning memo per the M18 / M19 / M20 /
M21 precedent.

## Standing rule

Per the M18 / M19 / M20 / M21 planning
pattern: at M22.0 open the target
selection proceeds by presenting the
full candidate list, recommending one
option with rationale grounded in
operator pain resolved by that
candidate, and awaiting user
confirmation. Once selected, §5.b–§5.h
load-bearing planning decisions get
drafted with recommendations for
confirm-as-recommended at M22.0 open
(streak extension expected: 87 → 88
planning-time as-recommended M5.1 →
M22.0 across thirteen consecutive
milestones).

Per the M21.0 §5.f Option B DoD
amendment (now formalized in
IMPLEMENTATION_ROADMAP at M21.5): the
M22 planning memo must either name at
least one Playwright operational
journey addition or extension, OR
document in §3 why no journey change
is required. Infrastructure-only
milestones satisfy via the exception
path. This constraint applies to the
active memo, not this skeleton.

## Planning inputs from M21 close

The M21 Operational Surface Completion
milestone surfaced concrete inputs that
must inform M22 target selection + scope.
This section carries them forward as
first-class planning material.

### Input 1 — Audit-driven scope pool for future OSC-shape milestones

The regenerated M21.5 audit artifact
(`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`)
catalogs **47 backend-only endpoints**
distributed across:

- **`defer-candidate-O2` — 44
  endpoints** (future OSC-shape
  milestones): F&I write UI (16),
  walk-in / phone / referral / webhook
  lead creation (4), deal-writeup
  mutations (3), test-drive creation
  (2), BHPH note origination + payment
  intake (2), accounting journal
  create + list + trial balance
  dashboards (4), misc dashboards.
- **`defer-domain-milestone` — 3
  endpoints**: `journal-entry-reverse`,
  `trial-balance-snapshot-create`,
  `trial-balance-snapshot-list`,
  `trial-balance-snapshot-retrieve`
  (the fourth was already noted at
  M21.1; the audit surfaces the
  bounded accounting-UI scope).

Any M22 candidate that ships operator
UI should select from this pool.

### Input 2 — Elevated candidates at M22.0 open

Per the M21 retrospective §8 + §9:

**Elevated (recommendation strength
increased at M22 open):**

- **Candidate A — return to
  accounting stream.** Now four
  consecutive milestones diverging
  from the M18 §8 accounting
  designation (M18 → M21). The M21.1
  audit surfaced three accounting
  endpoints (`journal-entry-reverse`
  + `trial-balance-snapshot-create /
  list / retrieve`) with clean
  `defer-domain-milestone`
  disposition — a bounded scope
  target that maps to shipped
  backend + missing UI and can
  honor the M21 governing contract.
- **Candidate O2 — next OSC
  iteration.** Attractive if
  operational-surface velocity is
  higher than accounting-stream
  velocity at M22 open. Selects from
  the 44 `defer-candidate-O2`
  endpoints. Sub-candidates include:
  F&I write substrate (highest
  endpoint count), lead-source
  intake forms, BHPH note
  origination + payment intake,
  deal-writeup lifecycle. Scope
  selection at M22.0 grounded in
  operator-pain evidence.

**Gated (external signal
precondition still absent):**

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions between M21 close
  and M22.0 open. If sessions ran,
  T becomes actionable.
- **Candidate U** — hosted-demo
  substrate (public self-serve
  signup). Gated on willingness to
  hand demo stores to strangers.
- **Candidate L** — first-live-
  pilot staging dry-run. Gated on
  a real pilot dealer + a staging
  environment.
- **Candidate M** — multi-operator
  support (`IsPlatformOperator`
  permission class). Gated on a
  second operator being introduced.
  **Breaks the zero-drift
  permission-class streak with
  intent.**

**Deferred pending evidence
(unchanged posture from M20 / M21
close):**

- **Candidate D** — demo-aware
  LLM router / cost caps. Evidence
  trigger (observed token spend on
  demo tenants) not fired.
- **Candidate C** — F&I chargeback
  substrate. Operator demand not
  surfaced.

**Deferred but stable:**

- **Candidate P** — onboarding UX
  polish. Unblocked; may be subsumed
  by a future OSC iteration that
  bundles polish where it directly
  removes operational friction.
- **Candidate G** — dashboard
  testid hardening. Not urgent —
  M21 opportunistic testids
  landed without journey
  brittleness surfacing.

### Input 3 — DoD amendment now formalized

M21.0 §5.f Option B (adopt with
documented exception path) formalized
in `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
at M21.5. Every M22 customer-facing
milestone MUST add or update at least
one Playwright operational journey OR
explicitly document why not. Applies
to the M22.0 active memo (not this
skeleton).

### Input 4 — M21 governing-contract precedent

M21 shipped the Candidate O governing
contract (map to shipped backend +
close missing UI + journey extension +
not generic polish). Any OSC-shape M22
candidate inherits this contract by
default. Domain milestones (e.g.
Candidate A if scoped to a bounded
accounting substrate) can opt into
the same contract if the audit's
`defer-domain-milestone` rows are the
scope — the three accounting
endpoints fit the contract exactly.

### Input 5 — M21 velocity data

- M21.0 planning: 1 session.
- M21.1 audit: 1 session (~500-line
  script + populated artifact +
  scope-lock amendment).
- M21.2 BHPH: 1 session (7 wrappers
  + 7 components + 18 tests + seed
  extension + journey re-expansion).
- M21.3 Be-back + cadence: 1 session
  (2 components + 9 tests + seed
  extension + journey extension).
- M21.5 close-out: 1 session
  (retrospective + capability
  matrix + M22 skeleton + roadmap
  amendment + audit regen + push).

**Five sessions for one OSC-shape
milestone.** If M22 picks another
OSC iteration with similar scope
(2 anchor implementations + close-
out), expect similar velocity.
Candidate A (bounded accounting-UI
scope) fits the same shape and
could ship in similar time.

## Candidate list

Compiled from
`MILESTONE_21_RETROSPECTIVE.md` §8 +
§9 + carry-forwards from M19 / M20 /
M21 planning skeletons. **Priority
ranking happens at M22.0 with the
full brief in hand.**

### Elevated at M22.0

- **Candidate A — Return to
  accounting stream (bounded
  scope).** Per M21 retrospective
  §9. Ships operator UI for
  journal-entry reverse + trial-
  balance snapshot lifecycle
  (create + list + retrieve).
  Three endpoints match the M21
  governing contract; scope stays
  bounded. Recommendation
  strength: HIGH — four
  consecutive milestones
  diverging from the M18 §8
  designation and now a clean
  scope target exists.

- **Candidate O2 — Next
  Operational Surface Completion
  iteration.** Per M21 audit
  artifact + M21 retrospective §8.
  Selects from the 44
  `defer-candidate-O2` endpoints.
  Sub-scope options include: F&I
  write substrate (16 endpoints —
  broad scope; may need internal
  narrowing to two anchor
  workflows); lead-source-specific
  intake forms (walk-in / phone /
  referral / webhook — 4 endpoints;
  bounded and coherent); BHPH note
  origination + payment intake (2
  endpoints; small); deal-writeup
  lifecycle (3 endpoints;
  bounded). Recommendation
  strength: HIGH if M22 leans
  toward operational-surface
  velocity over domain-stream
  advancement.

### Gated candidates (from M19 / M20 / M21 §9)

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on tester
  sessions between M21 close and
  M22.0 open.
- **Candidate U** — hosted-demo
  substrate. Gated on demo-
  scaling willingness.
- **Candidate L** — first-live-
  pilot staging dry-run. Gated on
  real pilot + staging env.
- **Candidate M** — multi-operator
  support. Gated on second
  operator. **Breaks zero-drift
  streak with intent.**

### Deferred pending evidence

- **Candidate D** — demo-aware
  LLM router / cost caps.
- **Candidate C** — F&I chargeback
  substrate.

### Deferred but stable

- **Candidate P** — onboarding UX
  polish. May be subsumed by an
  OSC iteration.
- **Candidate G** — dashboard
  testid hardening.

## What M22.0 must do

At SESSION_171 (or whenever M22.0
opens):

1. **Verify CI status** on the M21
   push — confirm the coordinated
   push landed all five M21
   commits cleanly and CI ran on
   the extended journeys. Address
   any regression as §0.a M22.0
   amendments before opening §5.a.
2. **Regenerate the audit artifact**
   before candidate presentation.
   Any endpoint that shipped
   between M21.5 close and M22.0
   open will show up. Fresh
   evidence prevents proposing
   scope that's already partially
   covered.
3. **Present the candidate list**
   above with a recommendation +
   rationale per candidate.
   Explicit note: reference the
   M21 retrospective §9 elevation
   of Candidate A + the
   regenerated audit for Candidate
   O2 sub-scope selection.
4. **Recommend a target** for §5.a
   selection. Ground the
   recommendation in:
   - Operator pain resolved.
   - Dependencies on already-
     shipped substrate.
   - Deferred items with re-entry
     paths.
   - Whether the candidate blocks
     future milestones or is
     blocked by them.
   - Evidence from Inputs 1–5.
5. **Await user confirmation** or
   redirection to a different
   candidate.
6. **Once §5.a locks**, draft
   §5.b–§5.h load-bearing
   planning decisions with
   recommendations for confirm-
   as-recommended at M22.0 open.
   Streak 87 → 88 expected.
7. **DoD amendment compliance
   check.** The M22 active memo
   §3 must either name the
   Playwright journey addition
   / extension OR document why
   no journey change is required
   (infrastructure-only
   milestones only). Non-
   compliance is a planning-memo
   review finding.
8. **Expand this skeleton** into
   a full active planning memo
   analogous to
   `MILESTONE_18_PLANNING.md` /
   `MILESTONE_19_PLANNING.md` /
   `MILESTONE_20_PLANNING.md` /
   `MILESTONE_21_PLANNING.md`.
   Frontmatter `status: draft` →
   `status: active`;
   `milestone_name` populated
   from §5.a.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target at
  M21.5. Inputs 1–5 above inform
  the recommendation at M22.0
  open; they do not preempt it.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M21.5 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate at
  M21.5.
- ❌ Do NOT rewrite the candidate
  list order to imply priority
  — that's the M22.0 open
  exercise. The elevated /
  gated / deferred annotations
  are recommendation-strength
  signals, not a locked
  ranking.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
   §8 + §9 (M21 unblocks +
   standing M22 question)
6. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 governing contract that
   any OSC-shape M22 inherits)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit-driven scope pool for
   OSC candidates)
8. `docs/CAPABILITY_MATRIX.md`
   §7v (M21 shipped surface)
