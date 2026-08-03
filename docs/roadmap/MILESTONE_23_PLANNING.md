---
title: "Milestone 23 — (target selection deferred to M23.0)"
status: draft
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_174 (skeleton + M22-close planning inputs)
milestone: 23
milestone_name: "(pending — locked at M23.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_22_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_22_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7w
---

# Milestone 23 — Planning skeleton (target TBD at M23.0)

Skeleton drafted at M22.5 close-out
(SESSION_174). This memo intentionally
does NOT lock a target; SESSION_175
(M23.0) presents the candidate list,
resolves §5.a with the user, and
expands the skeleton into a full active
planning memo per the M18 / M19 / M20 /
M21 / M22 precedent.

## Standing rule

Per the M18 / M19 / M20 / M21 / M22
planning pattern: at M23.0 open the
target selection proceeds by presenting
the full candidate list, recommending
one option with rationale grounded in
operator pain resolved by that
candidate, and awaiting user
confirmation. Once selected, §5.b–§5.h
load-bearing planning decisions get
drafted with recommendations for
confirm-as-recommended at M23.0 open
(streak extension expected: 88 → 89
planning-time as-recommended M5.1 →
M23.0 across fourteen consecutive
milestones).

Per the M21.0 §5.f Option B DoD
amendment (formalized in
IMPLEMENTATION_ROADMAP at M21.5, applied
by M22): the M23 planning memo must
either name at least one Playwright
operational journey addition or
extension, OR document in §3 why no
journey change is required.
Infrastructure-only milestones satisfy
via the exception path. This constraint
applies to the active memo, not this
skeleton.

## Planning inputs from M22 close

The M22 Accounting Operational
Validation milestone surfaced concrete
inputs that must inform M23 target
selection + scope. This section carries
them forward as first-class planning
material.

### Input 1 — Audit-driven scope pool (post-M22.1 fix)

The M22.1-corrected audit artifact
catalogs **43 backend-only endpoints**
(down from 47 pre-M22.1). The M22.1
fix reclassified four accounting
endpoints from backend-only to
`covered`; the remaining backend-only
count carries forward as scope pool
for future OSC-shape milestones:

- **`defer-candidate-O2` — 40+
  endpoints** (future OSC-shape
  milestones): F&I write UI (16),
  walk-in / phone / referral /
  webhook lead creation (4), deal-
  writeup mutations (3), test-drive
  creation (2), BHPH note origination
  + payment intake (2), remaining
  accounting write endpoints (JE
  create, possibly others), misc
  dashboards.
- **`defer-domain-milestone` —
  reduced from 3 to 0** for
  accounting (all reclassified at
  M22.1). If any remain in the
  regenerated artifact for other
  domains, they're candidates for
  their own domain milestones.
- **`intentional-omission`** —
  unchanged (auth flows, health
  checks, demo utilities).

Any M23 candidate that ships operator
UI should select from this pool. Any
M23 candidate that validates
already-shipped UI (validation-shape)
should draw evidence from the pre-
M22.1 misclassification patterns —
other domains may have similar
variable-first URL-assembly wrappers
still misclassified.

### Input 2 — Elevated candidates at M23.0 open

Per the M22 retrospective §8 + §9:

**Elevated (recommendation strength
increased at M23 open):**

- **Candidate A2 — next accounting
  iteration (bounded scope).** Per
  M22 retrospective §9. §5.b page/
  persona walk during M22.2
  surfaced three deferred future-
  evidence candidates (as-of picker
  interaction journey, cost-posting
  failures rendering journey, JE
  list navigation journey). Could
  be bundled into a single
  accounting-adjacent milestone.
  Additional candidates for
  investigation via dedicated
  accounting sub-audit at M23.0
  open: JE creation UI (may or may
  not exist — no shipped wrapper
  detected during §5.b walk), cost-
  posting failures remediation
  actions, month-end close workflow,
  accounting operator navigation.
  Small-to-medium scope; matches
  M22 refined governing contract
  shape.

- **Candidate H — test-hygiene
  remediation (NEW).** Three
  journeys (office/accounting_workflow
  freeze, sales_manager/daily_startup
  lead-assignment, recon/workflow
  decision) mutate DB state their
  seeds don't reset — same-day
  multi-runs fail; clean-DB runs
  pass. Small-scope tooling
  improvement — extend each seed
  with cleanup analogous to
  M22.2's reversal-cleanup. Would
  make the acceptance suite
  reliably re-runnable across
  sessions without DB reset.
  **Highest immediate operational
  value at lowest scope cost.**

- **Candidate O2 — next OSC
  iteration.** Selects from the
  40+ `defer-candidate-O2`
  endpoints. Sub-candidates
  unchanged from M22.0: F&I write
  substrate (16 endpoints — needs
  internal narrowing to 2 anchor
  workflows); lead-source-specific
  intake forms (4); BHPH note
  origination + payment intake
  (2); deal-writeup lifecycle (3);
  test-drive creation (2). Scope
  selection at M23.0 grounded in
  operator-pain evidence.

**Gated (external signal
precondition still absent):**

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions between M22
  close and M23.0 open. If
  sessions ran, T becomes
  actionable.
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
(unchanged posture from
M20 / M21 / M22 close):**

- **Candidate D** — demo-aware
  LLM router / cost caps.
- **Candidate C** — F&I chargeback
  substrate.

**Deferred but stable:**

- **Candidate P** — onboarding UX
  polish.
- **Candidate G** — dashboard
  testid hardening. Not urgent —
  M22.2 opportunistic testids
  landed with zero required per
  §5.d Option B; journey
  brittleness not surfacing.

### Input 3 — DoD amendment binding

M21.0 §5.f Option B (adopt with
documented exception path)
formalized in
`docs/roadmap/IMPLEMENTATION_ROADMAP.md`
at M21.5. Every M23 customer-facing
milestone MUST add or update at
least one Playwright operational
journey OR explicitly document why
not. Applies to the M23.0 active
memo (not this skeleton).

### Input 4 — M22 governing-contract precedent

M22 shipped the refined governing
contract for validation-shape
milestones (map to shipped
frontend + backend + Playwright
evidence + journey-as-verifier +
gap-split-by-size). Any M23
candidate that validates already-
shipped UI inherits this contract
by default. Domain milestones or
UI-creation milestones use the
M21 Candidate O contract shape.
Both contracts share three
conditions (map to shipped
backend, add/extend Playwright
journey, not generic polish);
they differ on whether shipped
frontend is required (validation)
or missing frontend is the scope
target (UI-creation).

### Input 5 — M22 velocity data

- M22.0 planning: 1 session.
- M22.1 audit tooling correction:
  1 session (3 targeted changes,
  ~30-40 min active work under a
  ~2-hour §5.e budget guard).
- M22.2 JE reversal journey: 1
  session (5 seed tests + 1
  journey + 2 assertion helpers,
  first-run pass).
- M22.3: SKIPPED.
- M22.4 close-out: 1 session
  (retrospective + capability
  matrix + M23 skeleton + roadmap
  amendment + audit artifact
  verified + push).

**Four sessions for one
validation-shape milestone.**
Down from M21's five-session
shape by one (M22.3 skipped).
If M23 picks another validation-
shape (e.g. Candidate H test-
hygiene, or Candidate A2
accounting-adjacent validation),
expect similar 3-4 session
velocity. If M23 picks a UI-
creation shape (O2), expect
the M21 five-session pattern
(one anchor increment per
sub-scope).

### Input 6 — M22 audit false-negative reframe

The M22.1 root-cause reframe
(from "nested TS template
literals" to "variable-first URL
assembly with nested templates
as co-occurring pattern") is
authoritative for M23+ audit
maintenance. Any future
milestone touching the audit
script should preserve this
framing. Also implies that
other domains (recon, F&I,
BHPH beyond M21) may have
similar variable-first URL-
assembly wrappers still
misclassified — a fresh
accounting-style sub-audit for
each domain could reduce audit
noise further.

## Candidate list

Compiled from
`MILESTONE_22_RETROSPECTIVE.md` §8 +
§9 + carry-forwards from M19 / M20 /
M21 / M22 planning skeletons.
**Priority ranking happens at M23.0
with the full brief in hand.**

### Elevated at M23.0

- **Candidate H — Test-hygiene
  remediation (NEW at M22 close).**
  Extend the three affected seeds
  (freeze snapshot cleanup, lead
  assignment reset, recon
  decision reset) with cleanup
  analogous to M22.2's reversal-
  cleanup. Small scope, high
  operational value (acceptance
  suite reliably re-runnable
  across sessions without DB
  reset). Recommendation
  strength: HIGH — bounded shape,
  matches M22 refined governing
  contract (shipped test surface
  + missing test hygiene + no
  journey change required if
  seeds fix the same journeys).

- **Candidate A2 — Next accounting
  iteration (bounded scope).**
  Per M22 retrospective §9. Ships
  operator UI or Playwright
  journeys for accounting gaps
  identified during M22.2 §5.b
  walk (as-of picker journey,
  cost-posting failures journey,
  JE list navigation journey) plus
  any additional gaps surfaced by
  a dedicated accounting sub-audit
  at M23.0 open (JE creation UI,
  cost-posting failures actions,
  month-end close, accounting
  operator navigation).
  Recommendation strength: MEDIUM
  — smaller than M21 shape;
  requires sub-audit to confirm
  scope boundary.

- **Candidate O2 — Next
  Operational Surface Completion
  iteration.** Per M22.1-corrected
  audit artifact. Selects from
  40+ `defer-candidate-O2`
  endpoints. Sub-scope options
  unchanged from M22.0.
  Recommendation strength: MEDIUM
  — highest scope; delivers most
  operator-visible surface; also
  the highest risk of scope creep
  if any of the sub-scopes turn
  out larger than they appear.

### Gated candidates (from M19 / M20 / M21 / M22 §9)

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on tester
  sessions between M22 close and
  M23.0 open.
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
  testid hardening. Not urgent.

## What M23.0 must do

At SESSION_175 (or whenever M23.0
opens):

1. **Verify CI status** on the M22
   push — confirm the coordinated
   push landed all four M22
   commits cleanly and CI ran on
   the extended journeys. Address
   any regression as §0.a M23.0
   amendments before opening §5.a.
2. **Regenerate the audit artifact**
   before candidate presentation.
   Any endpoint that shipped
   between M22.4 close and M23.0
   open will show up. Fresh
   evidence prevents proposing
   scope that's already partially
   covered. Post-M22.1 fix the
   audit is trustworthy for
   accounting; other domains may
   still have variable-first
   URL-assembly false negatives.
3. **Present the candidate list**
   above with a recommendation +
   rationale per candidate. Note
   the two-way tie between
   Candidate H (test-hygiene —
   small scope, high operational
   value) and Candidate A2 or O2
   (larger scope, more visible
   operator impact). Discuss
   trade-offs.
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
   - Evidence from Inputs 1–6.
5. **Await user confirmation** or
   redirection to a different
   candidate.
6. **Once §5.a locks**, draft
   §5.b–§5.h load-bearing
   planning decisions with
   recommendations for confirm-
   as-recommended at M23.0 open.
   Streak 88 → 89 expected.
7. **DoD amendment compliance
   check.** The M23 active memo
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
   `MILESTONE_21_PLANNING.md` /
   `MILESTONE_22_PLANNING.md`.
   Frontmatter `status: draft` →
   `status: active`;
   `milestone_name` populated
   from §5.a.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target at
  M22.4. Inputs 1–6 above inform
  the recommendation at M23.0
  open; they do not preempt it.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M22.4 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate at
  M22.4.
- ❌ Do NOT rewrite the candidate
  list order to imply priority
  — that's the M23.0 open
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
5. `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
   §8 + §9 (M22 corrections
   landed + standing M23
   question)
6. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (M22 refined governing
   contract that any validation-
   shape M23 inherits)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — authoritative
   for accounting post-M22.1
   fix; other domains may still
   need M22.1-shape corrections)
8. `docs/CAPABILITY_MATRIX.md`
   §7w (M22 shipped surface)
