---
title: "Milestone 25 — (target selection deferred to M25.0)"
status: draft
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_184 (skeleton + M24-close planning inputs)
milestone: 25
milestone_name: "(pending — locked at M25.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_24_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_24_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7y
---

# Milestone 25 — Planning skeleton (target TBD at M25.0)

Skeleton drafted at M24.5 close
(SESSION_184). This memo intentionally
does NOT lock a target; SESSION_185
(M25.0) presents the candidate list,
resolves §5.a with the user, and
expands the skeleton into a full
active planning memo per the M18 /
M19 / M20 / M21 / M22 / M23 / M24
precedent.

## Standing rule

Per the M18 / M19 / M20 / M21 / M22 /
M23 / M24 planning pattern: at M25.0
open, target selection proceeds by
presenting the full candidate list,
recommending one option with
rationale grounded in the primary
operational-coverage lens ("which
candidate most increases operational
coverage for a dealership
employee?"), and awaiting user
confirmation. Once selected, §5.b–
§5.h load-bearing planning decisions
get drafted with recommendations for
confirm-as-recommended posture.
Streak counter starts fresh at M25.0
(reset to 0 at M24.0; stayed at 0
through M24.1-open correction).

Per the M21.0 §5.f Option B DoD
amendment (formalized in
`IMPLEMENTATION_ROADMAP.md` at M21.5,
applied by M22 + M23 + M24): the M25
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
selection at M25.0. Endpoint count,
implementation effort, roadmap
momentum, and continuity with prior
scope are secondary signals used to
break ties within candidates that
score comparably on operational
coverage.

## Preserve the M20–M24 operational contract (durable)

Compound guidance carried forward
through every M25 decision:

- Verify through the real
  application before locking scope
  — including BOTH intake AND
  downstream UI surfaces (M24.1-
  open durable lesson).
- Let evidence drive roadmap
  decisions.
- Keep milestones tightly
  bounded.
- Extend Playwright journeys
  whenever customer-facing
  operational behavior changes.
- Allow completed operational
  journeys to reveal the next
  highest-value work rather than
  planning from assumptions.
- Sibling-pattern discipline
  (M23 durable) — first-of-a-
  kind changes surface latent
  bugs; inherited patterns
  don't.
- Record planning corrections
  honestly (M24 durable) — streak
  integrity beats streak count.

## Planning inputs from M24 close

The M24 Sales Operational Entry
milestone surfaced concrete inputs
that must inform M25 target
selection + scope.

### Input 1 — Genuinely-missing UI surfaces documented at M24.1 open

Three §3 deferrals added at M24.1
open per the downstream-verb UI
substrate correction, with
explicit M25 re-entry paths:

- **§3 deferral 12** —
  `<RecordTestDriveForm>` component
  + attachment on
  `DealerAiSalesTestDrives`.
  Wrapper exists since M11.6 but
  no UI consumes it;
  `DealerAiSalesTestDrives.tsx` is
  read-only per M11.6 explicit
  deferral. **Candidate A4 at
  M25.**
- **§3 deferral 13** —
  `referrer_id` / "Referred by"
  display in `LeadDetailModal`.
  Backend contract preserved but
  operator can't see attribution
  in modal. Small UI extension
  (~20-line addition). **Candidate
  A3 (bundle) at M25.**
- **§3 deferral 14** — `platform`
  display in `LeadDetailModal` for
  webhook-origin leads. Operator
  sees `channel="listing_form"`
  but not the specific platform.
  Small UI extension (~10-line
  addition). **Bundle with §3
  deferral 13 as A3.**

### Input 2 — Elevated candidates at M25.0 open

Per the M24 retrospective §9:

**Elevated (recommendation strength
increased at M25 open):**

- **Candidate A3 — Lead source
  attribution display bundle
  (NEW at M24.1 open).** Bundle
  §3 deferrals 13 + 14. Small
  UI extensions to
  `LeadDetailModal` for
  `referrer` display + `platform`
  display. Would strengthen the
  M24.3 referral journey's
  downstream assertion from
  API-side to modal-side +
  give webhook journey a full
  platform-visible assertion.
  **Highest per-item operational-
  coverage delta at smallest
  scope** — leads the
  operational-coverage-lens
  ranking. Every
  referral/webhook lead the
  salesperson opens is a
  moment where this gap
  surfaces.
- **Candidate A4 — RecordTestDriveForm
  UI (NEW at M24.1 open).** §3
  deferral 12. Completes the
  M24.1 walk-in journey's
  original operational-entry
  story (create → assign →
  schedule test drive as
  intended before the M24.1
  substrate verification).
  Small scope, matches M24.1
  substrate pattern
  (LeadIntakeForm-style component
  + attachment + journey).
- **Candidate H — test-hygiene
  remediation (reinforced at
  M24.1 close).** Three shared-
  DB non-idempotent journeys
  (`sales_manager/daily_startup`,
  `recon/workflow`,
  `office/accounting_workflow`)
  break full-suite runs on
  state-dirty DB. Original M22
  §9 scope: extend three
  affected seeds with cleanup.
  Expanded at M23.2:
  session-invalidation seed
  pattern sweep. Reinforced at
  M24.1 close: the CI baseline
  fragility is now
  operationally important
  because M24 grew the suite
  to 13 journeys.
- **Candidate A2 — JE creation
  UI (unchanged since M23
  close).** Single new wrapper
  + form + journey for
  `admin-journal-entry-create`.
  Small scope; smallest per-
  item delta of the elevated
  candidates but still real
  gap.

**Gated (external signal
precondition still absent):**

- **Candidate T** — process
  real tester feedback (M18.5
  CSV export).
- **Candidate U** — hosted-
  demo substrate.
- **Candidate L** — first-
  live-pilot staging dry-
  run.
- **Candidate M** — multi-
  operator support. **Breaks
  zero-drift permission-class
  streak with intent.**

**Deferred pending evidence:**

- **Candidate D** — demo-
  aware LLM router / cost
  caps.
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
at M21.5. Every M25 customer-
facing milestone MUST add or
update at least one Playwright
operational journey OR
explicitly document why not.

### Input 4 — M24 governing-contract precedent

M24 inherited the M21 Candidate
O UI-creation contract cleanly.
Any M25 candidate that ships
new UI inherits the same
contract by default.
Validation-shape milestones
(like M22) use the M22
refinement. Integration-to-
operator variants (like M24
webhook) use the M24 revised
formulation.

### Input 5 — M24 velocity data

- M24.0 planning: 1 session
  (SESSION_180).
- M24.0 correction (SESSION_181
  open): pre-implementation
  planning revision + commit.
  Not a separate session.
- M24.1 walk-in: 1 session
  (SESSION_181).
- M24.2 phone: 1 session
  (SESSION_182).
- M24.3 referral: 1 session
  (SESSION_183).
- M24.4 folded with M24.5
  close-out: 1 session
  (SESSION_184).

**Five sessions for a four-
journey UI-creation milestone
with two mid-milestone
planning corrections.** M24.4
collapsed into M24.5 per
evidence-sized §5.h Option B
posture (webhook journey-only
work + no §5.d operator-
surface fixes).

If M25 picks A3 (Lead source
attribution display bundle),
expect **~3 sessions**
(planning + small UI
extensions + close-out — no
new form component, no new
seed, existing journey
extension). If M25 picks A4
(RecordTestDriveForm UI),
expect **~3-4 sessions**
(planning + form + journey +
close-out matching M23.2 shape).
If M25 picks Candidate H
alone, expect **~3 sessions**
(planning + seed sweeps +
close-out). If M25 picks a
larger O2 sub-scope, expect
5+ sessions per M24 pattern.

### Input 6 — M24 lessons applied

Sibling-pattern discipline
(M24.2 phone + M24.3 referral
both first-run passes) +
session-safe seed pattern
(M24.1) + journey-as-verifier
posture + record-planning-
redirects-honestly (M24)
inheritable to any M25
candidate.

**New durable lesson from
M24.1 open:** planning-open
verification must cover BOTH
intake AND downstream UI
surfaces before locking §5.b
+ §5.d for any UI-creation
milestone.

## Candidate list

Compiled from
`MILESTONE_24_RETROSPECTIVE.md`
§9. **Priority ranking
happens at M25.0 with the
full brief in hand.**

### Elevated at M25.0

- **Candidate A3 — Lead source
  attribution display bundle
  (NEW at M24.1 open).**
  Recommendation strength:
  HIGH under operational-
  coverage lens — smallest
  scope + highest per-item
  delta + closes two
  M24.1-open genuine gaps.
- **Candidate A4 —
  RecordTestDriveForm UI
  (NEW at M24.1 open).**
  Recommendation strength:
  HIGH — completes M24.1
  walk-in journey's original
  operational-entry story.
- **Candidate H — test-
  hygiene remediation
  (reinforced at M24.1
  close).** Recommendation
  strength: MEDIUM-HIGH —
  indirect operational-
  coverage delta but bounded
  and high-compound-value
  for CI baseline stability.
- **Candidate A2 — JE
  creation UI (unchanged).**
  Recommendation strength:
  MEDIUM — small scope +
  audit-verified genuine
  gap but lower per-user ×
  frequency delta than
  A3/A4.
- **Candidate O2 — next OSC
  iteration.** Sub-scope
  options unchanged.

### Gated candidates (from M19 / M20 / M21 / M22 / M23 / M24 §9)

- **Candidate T** — tester
  feedback.
- **Candidate U** — hosted-
  demo.
- **Candidate L** — first-
  live-pilot staging.
- **Candidate M** — multi-
  operator support.

### Deferred pending evidence

- **Candidate D** — LLM
  router / cost caps.
- **Candidate C** — F&I
  chargeback substrate.

### Deferred but stable

- **Candidate G** — dashboard
  testid hardening.

## What M25.0 must do

At SESSION_185 (or whenever
M25.0 opens):

1. **Verify CI status** on
   the M24 push. First real
   M24 CI run fires on the
   M24.5 push — verify
   status.
2. **Regenerate the audit
   artifact** before
   candidate presentation.
   Post-M23.1 fix the audit
   is trustworthy for BHPH +
   accounting + sales intake
   (post-M24).
3. **Present the candidate
   list** above with a
   recommendation per
   candidate.
4. **Recommend a target**
   for §5.a selection under
   the primary operational-
   coverage lens. Suggested
   ranking: A3 > A4 > H >
   A2, per the M24 §9
   retrospective analysis.
   Alternative: bundle A3 +
   A4 as a "sales UI
   completeness" milestone
   if scope fits.
5. **Await user confirmation**
   or redirection.
6. **Once §5.a locks**, draft
   §5.b–§5.h load-bearing
   planning decisions.
7. **DoD amendment compliance
   check** on §3 draft.
8. **Verify BOTH intake AND
   downstream UI surfaces**
   before locking §5.b + §5.d
   per M24.1-open durable
   lesson.
9. **Expand this skeleton**
   into a full active
   planning memo.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target
  at M24.5. Inputs 1–6 inform
  the recommendation at M25.0
  open; they do not preempt
  it.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M24.5 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate
  at M24.5.
- ❌ Do NOT rewrite the
  candidate list order to
  imply priority — that's
  the M25.0 open exercise.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`
   §8 + §9 (M24 corrections
   + standing M25 question)
6. `docs/roadmap/MILESTONE_24_PLANNING.md`
   (M24 governing contract
   inherited by M25 UI-
   creation candidates)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact —
   authoritative for BHPH +
   accounting post-M23.1;
   authoritative for sales
   intake at M24.0)
8. `docs/CAPABILITY_MATRIX.md`
   §7y (M24 shipped surface)
