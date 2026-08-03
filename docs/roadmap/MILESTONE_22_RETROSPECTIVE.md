---
title: "Milestone 22 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-03
sessions: SESSION_171 → SESSION_174
milestone: 22
milestone_name: "Accounting Operational Validation"
related:
  - docs/roadmap/MILESTONE_22_PLANNING.md
  - docs/roadmap/MILESTONE_21_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7w
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 22
---

# Milestone 22 — Retrospective

Written at Milestone 22 close
(SESSION_174). Records what was
planned, what shipped, what
deviated and why, and lessons
carried forward for Milestone 23
and beyond. Mirrors the
`MILESTONE_21_RETROSPECTIVE.md`
structure so milestone history
remains directly comparable.

## 1. Planned scope

`MILESTONE_22_PLANNING.md` at
SESSION_170 close (skeleton) and
SESSION_171 (full active memo)
defined the milestone as
**Accounting Operational
Validation** — Candidate A per
§5.a, reshaped from the M21
retrospective §9's "ship missing
UI" recommendation by empirical
discovery during M22.0 open.
Governing contract refined for
validation-shape milestones:
every M22 shipped surface must
(a) map to shipped frontend
surface PLUS shipped backend
capability; (b) establish
operational-completion evidence
through Playwright end-to-end
journey; (c) use journey-as-
verifier rather than manual
verification; (d) split
discovered gaps by size — small
in-scope fix vs. large deferred
as future evidence.

One anchor implementation pre-
committed at planning-time (JE
reversal Playwright journey +
seed extension + assertion
helpers), one supporting-work
increment pre-committed (audit
tooling correction), one
conditional increment gated on
§5.b page/persona walk findings
during authoring.

Seven §5 load-bearing decisions
all resolved as-recommended at
M22.0 open (§5.a target =
Candidate A refined; §5.b
workflow enumeration = pages +
persona combined; §5.c journey
folder + shape = per-workflow
spec files under `office/`;
§5.d discovered-gap handling =
split by size; §5.e audit-
tooling correction = targeted
regex fix; §5.f baseline
verification = journey-as-
verifier; §5.g seed pattern =
extend existing seed
additively; §5.h increment
sequencing = evidence-sized
four-to-five increments).

## 2. What actually shipped

**Four increments across four
sessions** (SESSION_171 →
SESSION_174) — one sequencing
shift vs. the four-to-five
range at §5.h Option B:
**M22.3 collapsed per the
M22.2 §5.b page/persona walk
evidence that no additional
scope-worthy items existed**
(second consecutive milestone
where evidence-sized shape
shrank; M21.4 collapsed for
the same reason). Milestone
shape: M22.0 planning + M22.1
audit tooling correction +
M22.2 JE reversal journey +
M22.4 close-out.

### M22.0 — Planning refinement + target selection (SESSION_171)

Full memo expansion + all seven
§5 decisions resolved.
Candidate A confirmed at open
with refined framing.
**Empirical M22.0 discovery
falsified the M21 retrospective
§9 assumptions within one
session** — both anchor UIs
originally named (JE reversal
+ trial-balance snapshot
lifecycle) already ship as
fully-wired operator pages
from M14.2–M14.4 and M17.2;
the M21.5 audit misclassified
four accounting endpoints as
backend-only. User redirected
M22 from UI creation to
workflow validation +
supporting audit correction.
Milestone name: **"Accounting
Operational Validation."**
**Streak: 87 → 88 planning-time
as-recommended M5.1 → M22.0
across thirteen consecutive
milestones (M10 → M22).**
Handoff at
`docs/handoffs/SESSION_171_m22_inc0_planning.md`.

### M22.1 — Audit tooling correction + artifact refresh (SESSION_172)

Three targeted changes to
`backend/dealer_ai/scripts/audit_operational_surface.py`
per §5.e Option B:
(1) `_HELPER_CALL_RE` extended
with identifier-argument
alternative; (2) new
`_resolve_variable_url()` +
`_extract_url_literals()`
helpers walk backward from
helper calls to find `const
path = <expr>;` assignments;
(3) balanced-brace
`_collapse_ts_templates()` +
rewritten `_expand_helper_calls()`
handle nested `${...}`
substitutions. Root-cause
reframe: the M21 retrospective
§4 called this the "nested TS
template literal class." M22.1
investigation showed the actual
class is **variable-first URL
assembly** — wrappers passing
identifiers to helper calls
rather than literals; nested
templates are a common co-
occurring pattern. Coverage
**106 → 110 (+4)**; backend-
only **47 → 43 (-4)**. All four
accounting misclassifications
reclassify to `covered`.
Budget guard held (~30-40 min
vs. ~2-hour §5.e guard). No
audit-script correctness test
added — regeneration is the
functional verification.
Backend baseline unchanged
(4,761); zero regressions.
Handoff at
`docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`.

### M22.2 — JE reversal journey + seed extension (SESSION_173)

First anchor journey. Walks
navigate → dialog → reason →
confirm → business-outcome
assertion via API. Extended
`seed_journey_office_accounting_workflow.py`
additively with reversible-JE
fixture (`[M22.2-office-je-
reversal]` tag; $250 amount)
+ reversal-cleanup on re-
invocation. Extended
`test_m203_seed_journey_office_accounting_workflow.py`
with 5 new test cases. Extended
`acceptance/support/assertions/accounting.ts`
with
`findJournalEntryByDescriptionPrefix`
+
`expectJournalEntryReversed`.
**Journey passed on first run**
(office_accounting project: 7
passed @ 450ms; full clean-DB
suite: 13 passed @ 18.2s) —
journey-as-verifier per §5.f
Option B validated. **No small
operator-surface gap fixes
required per §5.d** — journey
authoring proceeded cleanly
against shipped M14.3/M14.4
markup using role-based
selectors. Backend baseline
**4,761 → 4,766 (+5)**.
§5.b page/persona walk
outcome: M22.3 SKIPPED (no
additional workflow-worthy
gaps). Handoff at
`docs/handoffs/SESSION_173_m22_inc2_je_reversal.md`.

### M22.4 — CI hardening + retrospective + close-out (SESSION_174)

Clean-DB full-suite dry-run:
**13 passed @ 18.3s**
(matching M22.2 close
baseline exactly).
`docs/CAPABILITY_MATRIX.md`
§7w lands. This retrospective.
M23 planning skeleton.
IMPLEMENTATION_ROADMAP.md
updated with M22 shipped
status. Coordinated close-out
commit + **first M22 push** —
all four commits (M22.0 +
M22.1 + M22.2 + M22.4)
surface to `origin/main`
together per M18.6 / M19.6 /
M20.5 / M21.5 cadence.
Handoff at
`docs/handoffs/SESSION_174_m22_inc4_close.md`.

## 3. Deviations vs. planning memo

- **M22.3 collapsed** — the M22
  planning memo (§0.a §5.h)
  provisioned M22.3 for
  additional journeys surfaced
  by the §5.b page/persona
  walk. The walk during M22.2
  authoring surfaced no
  additional distinct-workflow
  gaps warranting dedicated
  journey files. Findings
  (as-of picker interaction,
  cost-posting failures
  rendering, JE list
  navigation) were either
  covered by non-Playwright
  means or represented low-
  frequency edge cases not
  workflow-critical for daily
  operations. Deferred to
  future-evidence retrospective
  §9 rather than force-scope
  into M22. This is a feature
  of the evidence-sized §5.h
  Option B posture, not a
  deviation from it —
  identical shape shrink to
  M21.4's collapse.
- **§5.a scope reshape from
  "ship missing UI" to
  "validate shipped UI"** —
  the M21 retrospective §9's
  specific scope recommendation
  ("ship JE reversal UI +
  trial-balance snapshot
  lifecycle UI") was falsified
  during M22.0 open by
  empirical inspection of the
  frontend. Both were already
  shipped. The reshape
  preserved Rule 5 (preserve
  existing code) and Rule 6
  (build around operational
  problems) while still
  honoring the M18 §8
  accounting slot designation
  — accounting operational
  completeness is a real
  operational problem even
  though "the UI doesn't
  exist" was not the actual
  gap. **Not a deviation from
  planning; a correction that
  the M22.0 open discipline
  was designed to enable.**
- **Backend baseline delta
  smaller than earlier
  estimate** — planning memo
  §4 estimated 4,761 →
  ~4,765–4,775 at M22 close.
  Actual: **4,761 → 4,766**
  (+5). All growth came from
  the M22.2 seed idempotency
  tests. The M22.1 audit fix
  intentionally added no
  tests per §0.a discretionary
  call.
- **Frontend Vitest unchanged**
  as estimated (180 → 180).
  Zero frontend components
  shipped per §5.a refined
  framing.
- **Acceptance suite grew
  6 → 7** as estimated at
  minimum shape. Would have
  grown to 7+N if M22.3
  shipped; N=0.
- **Everything else landed as
  planned** — governing
  contract compliance, zero-
  drift streak extension
  (21 → 22), planning-time
  streak extension (87 → 88),
  four-increment shape (down
  from four-to-five range),
  coordinated close-out push,
  DoD amendment satisfied by
  construction.

## 4. Deferrals reviewed

Every deferral from
`MILESTONE_22_PLANNING.md` §3
remains valid. Explicit review:

- **Building new accounting
  UI** — deferred per §3 (1).
  No exceptions taken.
- **New backend service verbs
  or endpoints** — deferred
  per §3 (2). No exceptions.
- **Component-level
  refactoring for its own
  sake** — deferred per §3
  (3). No refactoring
  occurred; journey authoring
  worked against shipped
  markup unchanged.
- **Full AST-based audit
  rewrite** — deferred per §3
  (4). Targeted regex fix
  sufficed at M22.1.
- **Non-accounting audit
  corrections** — deferred
  per §3 (5). Two ancillary
  row-order shuffles observed
  (recon row 51, f_and_i row
  101) — same dispositions,
  no semantic change; not
  further investigated.
- **Broader accounting
  workflows without shipped
  UI** — deferred per §3 (6).
  §5.b page/persona walk
  surfaced no evidence of
  missing UI beyond what the
  M22 governing contract's
  Rule 5 (preserve existing
  code) posture explicitly
  excluded. Future accounting
  sub-audit would be the
  path to enumerating any
  such gaps.
- **Migration to `vite
  preview` in CI** — carries
  forward from M20.5 →
  M21 §3(7) → M22 §3(7).
- **Cross-browser CI matrix**
  — carries forward per §3(8).
- **npm audit vulnerability
  remediation** — carries
  forward per §3(9).
- **CI artifact upload
  verification via intentional
  failure** — NOT verified
  this milestone; carries
  forward per §3(10). The
  M22 push at close-out
  triggers the first M22 CI
  run.
- **Systematic audit refresh
  schedule** — carries
  forward per §3(11). M22.1
  regenerated once; formal
  cadence remains future.
- **Retrospective §9 next-
  candidate lock** — deferred
  per §3(12). §9 below
  records evidence-based
  candidates for M23+ without
  pre-committing.

**New M22-specific deferrals
surfaced during implementation:**

- **As-of picker interaction
  journey** — trial-balance
  page's date picker supports
  historical trial balance
  views but has no Playwright
  end-to-end coverage. Low-
  frequency analytical
  workflow; deferred as future
  evidence for M23+
  consideration.
- **Cost-posting failures
  rendering journey** — the
  trial-balance page renders
  a failures card when
  `fetchCostPostingFailures`
  returns non-zero rows.
  Conditional (only fires
  when failures exist);
  requires additional seed
  scaffolding to reproduce
  deterministically. Deferred
  as future evidence.
- **JE list navigation
  journey** — endpoint
  reclassified `covered` at
  M22.1 (wrapper consumed by
  `AccountingJournalEntriesPage`);
  shipped Vitest coverage
  validates rendering. Small
  marginal value in a dedicated
  browser-navigation journey.
  Deferred as future evidence.
- **Pre-existing test-hygiene
  issue** — three journeys
  (office/accounting_workflow
  freeze, sales_manager/
  daily_startup lead-
  assignment, recon/workflow
  decision) mutate DB state
  their seeds don't reset,
  surfacing as same-day
  multi-run failures. Not
  caused by M22 changes;
  surfaces cleanly on clean-
  DB runs. Recorded as M23+
  candidate for test-hygiene
  remediation increment.
- **Non-accounting audit
  false-negative sweep** —
  the M22.1 regex+parser fix
  generalizes to any wrapper
  using variable-first URL
  assembly. Ancillary row-
  ordering shuffles observed
  in recon + f_and_i rows
  suggest other domains may
  also benefit from a fresh
  audit pass. Deferred as
  future audit-tooling work.

## 5. Lessons learned

**Lesson 1: Empirical M22.0
discovery saved M22 from
rebuilding shipped UI.** The
M21 retrospective §9's
specific scope recommendation
was falsified within one
session by inspecting the
frontend surface. Every future
retrospective §9 candidate
recommendation should be
reverified at the following
milestone's open — retrospective
recommendations decay when the
codebase state changes between
close and re-entry. The M22
governing-contract refinement
(condition 1: shipped
frontend surface AND shipped
backend capability) codifies
this discipline for validation-
shape milestones.

**Lesson 2: Journey-as-verifier
per §5.f Option B is fast and
reliable.** The M22.2 JE
reversal journey passed on
first run without manual pre-
verification. Playwright's
role-based selectors matched
against the shipped
M14.3/M14.4 markup cleanly.
The fail-loud contract meant
that any incompleteness in
the shipped workflow would
have surfaced as a specific
business-outcome assertion
failure — but none surfaced,
confirming the workflow is
operationally complete. This
posture generalizes to any
future validation-shape
milestone: skip the manual
pass-through; author the
journey; let it be the
verification.

**Lesson 3: Variable-first URL
assembly is a distinct audit
false-negative class.** The
M21 retrospective §4 framed
the class as "nested TS
template literals." M22.1
investigation revealed the
actual class is wrappers
using `const path = ...;
authGetJSON(path)` rather
than passing literals to the
helper call. Nested templates
are a common co-occurring
pattern but not the root
cause. Reframing in the
audit-script docstring +
capability matrix §7w helps
future audit maintainers
understand the actual failure
mode when similar patterns
recur.

**Lesson 4: Evidence can
shrink a validation-shape
milestone.** M22.3 was
provisioned; M22.3 was
skipped. Second consecutive
milestone where the §5.h
Option B evidence-sized
posture allowed the shape to
adjust to reality (M21.4
skipped per audit finding;
M22.3 skipped per §5.b walk
finding). Fixed increment
counts distort scope either
upward (padding — bolting a
low-value journey on) or
downward (compression —
skipping validation of a
worthwhile workflow). §5.h
Option B is the correct
posture for evidence-driven
milestones.

**Lesson 5: The M22 governing
contract's "shipped frontend"
condition is load-bearing.**
Without it, M22 would have
been Candidate O2 (build the
missing UI) rather than
Candidate A refined (validate
what ships). The condition
prevents scope drift when
audit false-negatives suggest
UI is missing that actually
exists. Future validation-
shape milestone proposals
should carry this condition
explicitly.

**Lesson 6: Role-based
selectors work on well-
structured shadcn/Radix
markup without pre-
instrumentation.** The M22.2
journey uses
`getByRole("button", { name:
/^Reverse this entry$/ })`
and
`getByRole("dialog", { name:
/Reverse journal entry/ })`
against the shipped
`AccountingJournalEntryDetailPage`
markup and matches cleanly.
No testid additions needed
per §5.d Option B "small
operator-surface fix"
threshold. Future accounting
journey authoring can rely
on the same role-based
selector approach, confirming
the M21 §5.g Option B
opportunistic-testids
posture is correct — proactive
testid coverage isn't
justified until brittleness
surfaces.

**Lesson 7: Additive seed
extension per §5.g Option A
preserves suite hygiene.**
Extending
`seed_journey_office_accounting_workflow`
with the M22.2 reversible-JE
fixture — and adding a
reversal-cleanup step — kept
the seed idempotent across
re-runs. The alternative
(per-workflow seed commands)
would have created seed
sprawl without benefit.
Matches M21 Lesson 4
("reference existing seed
shape").

**Lesson 8: Suite hygiene
isn't automatic — journeys
need seeds that reset their
own mutations.** The three
pre-existing failures on
same-day multi-run scenarios
(freeze snapshot, lead
assignment, recon decision)
surfaced during M22.2
development. Not M22.2-
caused, but not M22.2-fixed
either — recorded as
future evidence. The M22.2
seed's reversal-cleanup is
a proactive example of the
pattern that could remediate
those failures.

## 6. Streak status

- **Zero-drift permission-class
  posture:** **twenty-two
  consecutive milestones**
  (M10 → M22). Extended from
  21 at M22 close. Every M22
  surface stays within
  existing permission classes
  — `IsSalesManagerOrOwnerAtActiveDealership`
  for all accounting
  endpoints exercised by the
  M22.2 journey.
- **Planning-time as-
  recommended:** **88 across
  thirteen consecutive
  milestones** (M10 → M22).
  All seven §5 decisions at
  M22.0 open confirmed as-
  recommended. Zero §0.a
  amendments introducing new
  §5 decisions — the
  M22.1 + M22.2 §0.a entries
  record shipped outcomes,
  not new decisions.
- **Backend test-count
  monotonicity:** preserved.
  4,761 → 4,766 (+5). Zero
  regressions across the
  milestone.
- **Evidence-sized shape
  shrink:** **second
  consecutive milestone**
  where §5.h Option B allowed
  the shape to shrink per
  evidence (M21.4 skipped;
  M22.3 skipped). Reinforces
  the §5.h Option B posture
  as the correct default for
  audit / validation shapes.

## 7. Governing-contract validation

Every shipped M22 surface (M22.1
audit fix + M22.2 journey +
seed extension + assertion
helpers) satisfies all four
refined validation-shape
conditions:

- **Maps to shipped frontend
  surface + shipped backend
  capability** —
  `AccountingJournalEntryDetailPage`
  (shipped M14.3) +
  `reverse_journal_entry`
  service verb (shipped
  M13.1) + reversal endpoint
  (shipped M13.1). Zero
  changes to any of the
  three.
- **Establishes operational-
  completion evidence through
  Playwright** — the M22.2
  journey walks the reversal
  workflow end-to-end and
  asserts the business
  outcome (reversal exists,
  linkage correct, reason
  non-empty, lines sign-
  flipped per M13.1
  invariant).
- **Uses journey-as-verifier**
  — no manual pre-verification
  happened before authoring;
  the first passing run IS
  the evidence.
- **Splits discovered gaps by
  size** — §5.b walk surfaced
  three future-evidence
  candidates (as-of picker,
  cost-posting failures, JE
  list navigation) all
  deferred per §5.d Option B
  large-gap posture. Zero
  small-gap fixes in-scope
  because none surfaced —
  journey authoring proceeded
  cleanly against shipped
  markup.

Contract compliance is a first-
class M22 deliverable — this
retrospective + audit artifact
regen + capability matrix §7w
jointly provide the trail for
future review.

## 8. Corrections landed by M22 work

- **Four accounting endpoints
  now trustworthy in audit
  artifact** post-M22.1 fix:
  `admin-trial-balance`,
  `admin-journal-entry-list`,
  `admin-cost-posting-failures`,
  `admin-trial-balance-snapshot-list`
  all reclassify from
  backend-only to `covered`.
  Coverage 106 → 110.
- **Audit tooling reusable
  for future variable-first
  URL-assembly wrappers.**
  The regex + parser
  enhancements handle:
  identifier arguments to
  helper calls, backward
  lookup for `const path =
  <expr>;` assignments,
  ternary assignments
  (returns both branches as
  distinct consumers),
  balanced-brace collapse of
  nested `${...}`
  substitutions. Any future
  wrapper using the same
  idioms is detected
  automatically.
- **Root-cause reframe of the
  M21 retrospective §4
  false-negative class** —
  from "nested template
  literals" to "variable-
  first URL assembly with
  nested templates as a
  common co-occurring
  pattern." Documented in
  audit script commit
  message + memo §0.a M22.1
  amendment + capability
  matrix §7w + this
  retrospective §5 Lesson 3.
- **JE reversal workflow now
  operationally validated
  end-to-end.** Regressions
  to the shipped reversal
  workflow surface as loud
  journey failures rather
  than silent operational
  breakage. Part of the M20
  operational acceptance
  contract from M22.4 close.

## 9. Standing M23 question

**What is M23?** M22 shipped
Accounting Operational
Validation successfully. The
M18 §8 accounting slot
designation is honored (though
in refined form). The natural
M23 question is: continue
accounting substrate work, or
return to OSC-shape work, or
address the pre-existing
test-hygiene issue, or
respond to signal-gated
candidates if any external
signal fired?

**Evidence-based candidates
surfaced during M22:**

- **Additional accounting
  workflows (Candidate A2 —
  next accounting iteration).**
  §5.b walk cataloged three
  future-evidence candidates:
  as-of picker interaction
  journey, cost-posting
  failures rendering
  journey, JE list
  navigation journey. All
  small-scope; could be
  bundled into a single
  accounting-adjacent
  milestone or subsumed by a
  future OSC iteration.
  Additional candidates for
  investigation: JE creation
  UI (may or may not exist —
  no shipped wrapper detected
  during §5.b walk), cost-
  posting failures
  remediation actions
  (currently read-only
  rendering), month-end
  close workflow (may or may
  not exist as a coherent
  operator surface),
  accounting operator
  navigation surface (may or
  may not be discoverable
  from the dashboard). A
  dedicated accounting sub-
  audit at M23.0 open could
  enumerate remaining
  accounting gaps
  systematically.

- **Test-hygiene remediation
  (Candidate H — new).**
  Three journeys
  (office/accounting_workflow,
  sales_manager/daily_startup,
  recon/workflow) mutate DB
  state their seeds don't
  reset. Same-day multi-runs
  fail; clean-DB runs pass.
  Small-scope tooling
  improvement — extend each
  seed with cleanup
  analogous to M22.2's
  reversal-cleanup. Would
  make the acceptance suite
  reliably re-runnable
  across sessions without
  DB reset. Not urgent
  (M22.4 verified clean-DB
  runs work) but low
  effort.

- **Candidate O2 (next OSC
  iteration).** Selects from
  the regenerated audit
  artifact (43 backend-only
  endpoints post-M22.1 fix,
  down from 47). Sub-scope
  options unchanged from
  M22.0: F&I write substrate
  (16 endpoints), lead-
  source-specific intake
  forms (4), BHPH note
  origination + payment
  intake (2), deal-writeup
  lifecycle (3), test-drive
  creation (2).

**Signal-gated candidates
preserved** (unchanged
posture from M22.0):

- **Candidate T** — process
  real tester feedback.
  Gated on Chris running
  tester sessions between
  M22 close and M23.0 open.
- **Candidate U** — hosted-
  demo substrate. Gated on
  demo-scaling willingness.
- **Candidate L** — first-
  live-pilot staging dry-
  run. Gated on real pilot
  dealer + staging env.
- **Candidate M** — multi-
  operator support. Gated on
  second operator; would
  break the zero-drift
  permission-class streak.

**Evidence-deferred
candidates** (unchanged):

- **Candidate D** — demo-
  aware LLM router / cost
  caps.
- **Candidate C** — F&I
  chargeback substrate.

**Deferred but stable:**

- **Candidate P** —
  onboarding UX polish.
- **Candidate G** —
  dashboard testid hardening.

**Recommendation to raise
at M23.0 open:** if no
external signal fired, the
choice is between (a)
Candidate A2 (small
accounting completeness
work + audit-driven sub-
audit), (b) Candidate H
(test-hygiene remediation
— smallest scope + high
operational value), or (c)
Candidate O2 (next OSC
iteration from the audit-
driven scope pool). All
three fit the M22 refined
governing contract shape.
M23.0 §5.a resolution
belongs to SESSION_175.
This retrospective's role
is to surface the
question, not to pre-
commit the answer.
