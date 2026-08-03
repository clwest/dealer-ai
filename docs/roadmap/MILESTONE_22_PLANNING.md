---
title: "Milestone 22 — Accounting Operational Validation"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_170 (skeleton), SESSION_171 (expansion)
milestone: 22
milestone_name: "Accounting Operational Validation"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_21_PLANNING.md
  - docs/roadmap/MILESTONE_21_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7v
---

# Milestone 22 — Accounting Operational Validation

> **Active planning memo.** Expanded at
> SESSION_171 M22.0 open from the
> skeleton drafted at M21.5 close.
> §5.a Candidate A confirmed at open
> — the return-to-accounting milestone
> long designated by M18 §8 finally
> lands, reshaped by empirical M22.0
> discovery from "ship missing UI"
> into **Accounting Operational
> Validation**. The three shipped
> accounting operator pages already
> exist (`AccountingTrialBalancePage`,
> `AccountingJournalEntriesPage`,
> `AccountingJournalEntryDetailPage`);
> the M21.5 audit misclassified four
> of their endpoints as backend-only
> due to the nested-template-literal
> regex limitation documented at
> M21.1 close. M22's job is not to
> rebuild what already ships; M22's
> job is to prove the shipped
> workflows are operationally
> complete via Playwright end-to-end
> validation and to correct the audit
> tooling so its output becomes
> trustworthy source material for
> future accounting candidates.
>
> **M22 is the first validation-shape
> milestone.** M20 introduced the
> operational acceptance substrate;
> M21 introduced the OSC pattern of
> shipping missing UI + journey
> coverage together. M22 introduces
> the pattern of taking a domain
> whose UI already ships and
> establishing operational-completion
> confidence through end-to-end
> validation, correcting supporting
> tooling as necessary, and using the
> journey-authoring process itself as
> the next-candidate-selection
> mechanism. This shape is directly
> reusable for other domains
> (F&I / recon / pilot onboarding /
> BHPH beyond M21) where the UI is
> shipped but operational-completion
> evidence is thin.
>
> **M22 introduces zero new backend
> service verbs, zero new DRF
> endpoints, zero new frontend
> routes, zero new tenancy carriers,
> zero new migrations, zero new
> permission classes.** The zero-drift
> permission-class streak extends
> **twenty-one → twenty-two**
> consecutive milestones (M10 → M22).
> Backend baseline growth expected
> only from new seed-fixture tests +
> possibly audit-script correctness
> tests.
>
> **Seven load-bearing decisions** —
> §5.a target selection + §5.b
> workflow enumeration source + §5.c
> journey folder + shape + §5.d
> discovered-gap handling posture +
> §5.e audit tooling correction
> posture + §5.f baseline verification
> approach + §5.g seed command
> pattern + §5.h increment sequencing
> and completion contract. **All
> confirmed as-recommended at
> SESSION_171 M22.0 open** — streak
> extends to **88 planning-time
> as-recommended M5.1 → M22.0**
> across **thirteen consecutive
> milestones now** (M10 → M22).

## Guiding principle (Candidate A refined governing contract)

M22 inherits the M21 Candidate O
governing contract (map to shipped
backend + close missing UI + add or
extend Playwright journey + not
generic polish) and refines it for
validation-shape milestones. Every
M22 shipped surface must satisfy
four conditions:

1. **Maps to already-shipped
   frontend surface plus already-
   shipped backend capability** —
   the M22 refinement of M21's
   condition (1). The validation
   contract additionally requires
   that a shipped operator page
   exists; if a workflow ships as
   an endpoint without any UI,
   that's OSC territory (Candidate
   O2), not validation territory.
2. **Establishes operational-
   completion evidence through
   Playwright** — end-to-end
   journey demonstrating the
   workflow can be performed by
   the intended persona (office
   manager). Vitest coverage does
   not satisfy this condition —
   Vitest mocks the API layer;
   only Playwright exercises the
   full stack.
3. **Uses journey-as-verifier** —
   failure to complete the
   workflow through the UI
   surfaces as a Playwright
   failure with a specific
   business-outcome assertion,
   not as a manual bug report.
4. **Discovered gaps split by
   size** — a small operator-
   surface gap discovered during
   authoring (missing testid,
   broken link, label typo,
   form validation bug — a one-
   file trivial change) is fixed
   in-scope. A large gap
   (missing form, missing wrapper,
   missing service verb, new UI
   structure) is documented in
   retrospective §9 as the next
   accounting candidate with
   reproducible evidence, not
   bolted onto M22.

The governing contract binds every
§5 decision, every journey
authoring choice, every gap-review
decision. When these conditions
conflict with feasibility mid-
milestone, the resolution posture
is to catalog the finding as
evidence for a future milestone
rather than relax any condition.

## 0. Engineering practices to preserve from M2–M21

Same posture as M21.0 except where
noted. Non-negotiable:

- **Backend-first architecture.**
  M22 ships zero new backend
  business logic. Every journey
  exercises existing service verbs
  through existing endpoints
  behind existing permission
  classes. Backend baseline
  growth expected only from new
  seed-fixture tests + possible
  audit-script correctness tests.
- **Service ownership.** Every UI
  step in every journey invokes
  an existing service verb through
  an existing wrapper. No new
  service verbs; no parallel
  write paths. If journey
  authoring reveals a workflow
  needs a new service verb to
  complete, that is evidence for a
  future accounting candidate, not
  in-scope for M22.
- **Tenancy discipline.** Every
  journey seeds under the existing
  tenant middleware + acceptance-
  owner persona provisioned by
  `seed_journey_owner_morning_review`.
  No M22 journey bypasses the
  tenancy carrier stack.
- **Load-bearing decisions get
  user review BEFORE code.** All
  seven §5 decisions confirmed at
  SESSION_171 M22.0 open. Any
  implementation-time micro-
  decisions surface as §0.a
  amendments.
- **Additive extension over
  fork.** M22 does not modify
  existing accounting pages,
  service verbs, or endpoints in
  ways that break current use.
  New journeys attach to existing
  routes; new fixtures extend
  the existing accounting seed
  additively (per M21 §Lesson 4).
- **Zero-drift permission-class
  posture.** Every journey step
  authenticates through the
  existing acceptance-owner
  session; every endpoint stays
  within its shipped permission
  class
  (`IsSalesManagerOrOwnerAtActiveDealership`
  for M13/M14/M17 accounting).
  Streak extends **twenty-one →
  twenty-two** consecutive
  milestones (M10 → M22).
- **Every M22 assertion of
  shipped-surface counts uses
  `>=`** per the M9–M21 growth-
  only-list lesson. Journey
  counts stay exact-equality
  where the milestone shape
  locks a specific number (M22
  targets six-plus journeys at
  open — six existing + at
  minimum one new JE reversal
  journey; may grow to eight or
  nine if the §5.b page/persona
  walk surfaces additional
  workflows warranting distinct
  journeys).
- **Journey isolation, per-
  journey seed fixtures, and
  business-outcome assertions**
  per M20 §5.d and §5.e. Every
  new journey extends
  `seed_journey_office_accounting_workflow`
  additively (per §5.g) and
  asserts business state
  (a reversal is posted with
  swapped debits/credits; a
  journal-entry list contains
  expected rows) — not DOM
  state.
- **Fail-loud contract** per M20
  §0. Journey test names identify
  the operational workflow.
  Failure messages target the
  business outcome that failed.
  Screenshots + traces attach on
  failure per the M20 CI job
  configuration.
- **Journey-as-verifier over
  manual verification.** Per §5.f
  Option B — no manual developer
  pass-through of workflows before
  authoring. The journey itself
  is the verification. If the
  shipped UI cannot complete the
  workflow, the journey fails
  loudly, that failure IS the
  evidence, and the gap-handling
  posture (§5.d) governs response.

### 0.a Change log — resolved decisions

**SESSION_171 M22.0 open (2026-08-03):**

- **§5.a → Candidate A confirmed at
  open.** User named at SESSION_171
  M22.0 open with refined framing:
  the M18 §8 accounting designation
  finally lands, but the milestone
  is reshaped from "ship missing UI"
  into **Accounting Operational
  Validation**. Discovery during
  M22.0 open surfaced that both
  anchor UIs originally named (JE
  reversal + trial-balance snapshot
  create/list/detail) already ship
  as fully-wired operator pages
  from M14.2–M14.4 and M17.2, and
  that the M21.5 audit
  misclassified four accounting
  endpoints as backend-only due to
  the nested-template-literal
  regex limitation documented at
  M21.1 close. User redirected M22
  from UI creation to workflow
  validation + supporting audit
  correction. Milestone name:
  **"Accounting Operational
  Validation."** Candidate O2
  preserved for M23+ with the
  evidence surfaced during M22
  journey authoring as scope
  input.
- **§5.b → Option D confirmed as-
  recommended.** Workflow
  enumeration walks both the
  shipped accounting pages
  (`AccountingTrialBalancePage`,
  `AccountingJournalEntriesPage`,
  `AccountingJournalEntryDetailPage`)
  and the office-manager persona
  workflow. Pages define what's
  shippable; persona defines
  authoring priority order. The
  M21 audit is explicitly NOT the
  source — accounting endpoint
  dispositions are known
  unreliable pending §5.e
  correction.
- **§5.c → Option B confirmed as-
  recommended.** Per-workflow spec
  files under `acceptance/journeys/office/`,
  siblings to the existing
  `accounting_workflow.spec.ts`
  (trial-balance freeze coverage,
  M20.3). Distinct workflows
  (JE reversal, JE list navigation)
  get distinct spec files matching
  the M21 §5.e Option C precedent
  of "new journey where workflow
  shape is distinct." No new
  folder; office persona already
  owns the container.
- **§5.d → Option B confirmed as-
  recommended.** Discovered-gap
  handling posture: fix small
  operator-surface gaps in-scope
  (missing testid, broken link,
  label typo, form validation
  bug — one-file trivial change);
  document larger workflow gaps
  (missing form, missing wrapper,
  missing service verb, new UI
  structure) in retrospective §9
  as the next accounting candidate
  with reproducible evidence.
  Preserves Rule 4 (scope
  discipline) while allowing
  friction removal that would
  otherwise block a shipped
  workflow from being validatable.
- **§5.e → Option B confirmed as-
  recommended.** Audit-tooling
  correction is targeted — fix
  the documented nested-template-
  literal false-negative class
  plus the four known accounting
  misclassifications
  (`admin-trial-balance`,
  `admin-journal-entry-list`,
  `admin-cost-posting-failures`,
  `admin-trial-balance-snapshot-list`).
  Explicit non-goal: full AST-
  based audit rewrite using
  TypeScript compiler API. If
  targeted regex fix exceeds ~2
  hours at M22.1 open, defer the
  deeper refactor to a future
  audit-tooling milestone.
  Supporting work; not the
  milestone centerpiece.
- **§5.f → Option B confirmed as-
  recommended.** Baseline
  verification approach: journey-
  as-verifier. No manual
  developer pass-through before
  authoring. Playwright IS the
  verification; if the shipped
  page cannot complete a
  workflow, the journey fails
  loudly and the §5.d posture
  governs response. Vitest
  coverage explicitly does not
  substitute (mocks the API
  layer; validates component
  behavior, not full-stack
  completability).
- **§5.g → Option A confirmed as-
  recommended.** Seed pattern
  extends the existing
  `seed_journey_office_accounting_workflow`
  additively with per-journey
  fixtures (JE reversal needs a
  specific reversible JE; JE
  list needs multiple JEs
  spanning multiple dates for
  pagination validation). Matches
  M21 §Lesson 4 (reference
  existing seed shape). Per-
  fixture idempotency via stable
  description tags per the
  existing seed pattern. If seed
  size becomes an issue mid-
  milestone, split then; do not
  pre-split.
- **§5.h → Option B confirmed as-
  recommended.** Evidence-sized
  four-to-five increments. **M22.0
  planning** (this session) +
  **M22.1 audit-tooling
  correction + artifact refresh**
  + **M22.2 JE reversal journey**
  + **M22.3 additional journeys
  from §5.b page/persona walk
  (conditional — collapses if
  the walk surfaces only JE
  reversal as genuine gap)** +
  **M22.4 close-out**
  (retrospective, capability
  matrix update, M23 skeleton,
  coordinated close-out commit).
  M22.3 skips if evidence shows
  no additional journey-worthy
  workflows uncovered; expands
  to 4-5 increments if page
  walk + persona walk surface
  multiple distinct new
  journeys.
- **Streak extends to 88
  planning-time as-recommended
  M5.1 → M22.0.** Thirteen
  consecutive milestones now
  (M10 → M22).

## 1. Business questions this milestone answers

Five operator-workflow questions,
each grounded in the office-manager
persona and the shipped accounting
surface.

### Q1. Can an office manager freeze a trial-balance snapshot end-to-end through the product?

**Before M22:** Yes, and validated
by `office/accounting_workflow.spec.ts`
(M20.3). The trial-balance freeze
workflow ships operationally
complete and has Playwright coverage
for the primary path (land → freeze
→ prior-closes drill-down →
business-outcome assertion via
API).

**After M22:** Still yes, with the
existing journey preserved and
potentially extended per §5.b
enumeration to also cover the
cost-posting failures rendering
path (currently untested by the
Playwright layer) and the as-of
date picker interaction (currently
untested end-to-end). If §5.b
enumeration surfaces these as
distinct gaps, they either extend
the existing journey or become new
sibling journeys per §5.c.

### Q2. Can an office manager reverse a posted journal entry end-to-end through the product?

**Before M22:** Unvalidated. The
`ReverseEntryDialog` in
`AccountingJournalEntryDetailPage.tsx`
ships (M14.3/M14.4) with reason
textarea + posted_at input +
confirm button + error handling.
Vitest coverage exists. No
Playwright journey walks the full
workflow (navigate to JE → open
reversal dialog → fill reason →
confirm → verify reversal posted
with swapped debits/credits +
linkage back to original). Whether
an office manager can actually
perform this workflow through the
real UI is an untested claim.

**After M22:** Yes and validated.
The M22.2 JE reversal journey
walks the workflow end-to-end
against seeded fixtures (per §5.g)
and asserts the business outcome
via API (reversal entry exists,
lines are swapped, reverses_id
points back to original). If the
shipped UI cannot complete this
workflow, the journey fails
loudly per §5.f Option B and
§5.d handling posture governs the
response.

### Q3. Can an office manager navigate the journal-entry history and drill into detail end-to-end?

**Before M22:** Unvalidated. The
`AccountingJournalEntriesPage`
ships (M14.3) with paginated list
+ "View" links to detail. Vitest
coverage exists. No Playwright
journey walks the navigation
workflow. Whether the pagination,
row-click, and detail-page
handoff actually work as an
operator would experience them
is an untested claim.

**After M22:** Answer determined
by §5.b page/persona walk. If the
walk surfaces this as a distinct
workflow warranting a dedicated
journey, M22.3 authors
`office/accounting_je_list_navigation.spec.ts`.
If the walk shows it's covered by
the JE reversal journey's implicit
navigation steps, no new dedicated
journey ships. Either way the
outcome is recorded in the
retrospective as evidence.

### Q4. Is the M21 audit artifact trustworthy as scope source for future accounting-related milestones?

**Before M22:** No, as demonstrated
during M22.0 open. Four accounting
endpoints
(`admin-trial-balance`,
`admin-journal-entry-list`,
`admin-cost-posting-failures`,
`admin-trial-balance-snapshot-list`)
are misclassified as backend-only
in the regenerated M21.5 artifact
despite being wired through
consumed wrappers in the shipped
pages. The known limitation class
(nested TypeScript template
literals) is documented at M21.5
close but not fixed. Anyone
scoping a future accounting-
related milestone from the audit
in its current state would build
on incorrect premises — exactly
what M22.0 open surfaced.

**After M22:** Yes, for accounting
endpoints and for the documented
false-negative class. The M22.1
targeted regex fix closes the
nested-template-literal class; the
regenerated M22.1 artifact
reflects accurate accounting
coverage. The audit remains
imperfect for other classes not
yet catalogued (per §3 deferral)
but becomes trustworthy source
material for the next accounting
candidate. Retrospective §8
records the specific
misclassifications corrected and
any additional false-negative
patterns discovered during the
correction pass.

### Q5. What is the next accounting-related work worth doing, based on evidence rather than speculation?

**Before M22:** Speculative. The
M21 retrospective §9 named "JE
reversal + trial-balance snapshot
lifecycle UI" as the next
accounting candidate based on the
M21.1 audit dispositions. M22.0
discovery proved that scope was
already shipped — the candidate
was born of audit noise, not
operational evidence. Any similar
speculation about F&I / recon /
BHPH / pilot-onboarding gaps
carries the same risk.

**After M22:** Evidence-based.
M22.2 + potential M22.3 journey
authoring surfaces any workflow
that cannot complete through the
UI as a small in-scope fix (per
§5.d) or as a documented next
candidate (per §5.d). The M22.4
retrospective §9 records the
identified next accounting
candidate — if any — with
reproducible steps to demonstrate
the gap. Future OSC-shape
milestones proposing accounting
scope draw from that evidence, not
from audit disposition alone.

## 2. What existing primitives extend

M22 continues the "additive
extension over fork" pattern
(M11.1 / M12.3 / M13.2 / M14.1 /
M15.1 / M16.1 / M17.1 / M18.1 /
M19.1 / M20.1 / M21.2). Zero new
backend service verbs, zero new
DRF endpoints, zero new tenancy
carriers, zero new migrations,
zero new frontend routes, zero
new permission classes.

### Extended — acceptance workspace

- **`acceptance/journeys/office/accounting_workflow.spec.ts`**
  — existing (M20.3) trial-
  balance freeze journey.
  Preserved intact; potentially
  extended if §5.b enumeration
  surfaces cost-posting failures
  rendering path or as-of
  picker interaction as distinct
  gaps within the same workflow.
- **`acceptance/journeys/office/accounting_je_reversal.spec.ts`**
  (new). M22.2 anchor. Walks:
  land on JE detail page for a
  seeded reversible entry →
  open reversal dialog → fill
  reason ("M22 test reversal")
  → click confirm → verify
  status message → verify page
  reload shows reversal linkage.
  Business-outcome assertion via
  API: the reversal entry
  exists, has swapped debits/
  credits, and its `reverses_id`
  matches the original entry's
  id.
- **`acceptance/journeys/office/accounting_je_list_navigation.spec.ts`**
  (conditional, M22.3). Ships
  only if §5.b page/persona
  walk demonstrates this is a
  distinct workflow warranting
  dedicated coverage (rather
  than being implicitly covered
  by the reversal journey's
  navigation steps).
- **Additional workflow-specific
  journeys** — conditional per
  §5.b enumeration findings.
  Any surfaced during the
  M22.2/M22.3 authoring passes
  ships if the workflow warrants
  its own journey; is deferred
  per §5.d if the workflow is
  covered by an existing
  journey's implicit steps.

### Extended — backend workspace

- **`backend/dealer_ai/management/commands/seed_journey_office_accounting_workflow.py`**
  — existing (M20.3) accounting
  seed. Extended additively per
  §5.g Option A with new fixture
  entries: (a) reversible JE
  fixture for the reversal
  journey (stable description
  tag; idempotent reuse); (b)
  multi-JE fixture spanning
  multiple dates for the
  conditional JE list
  navigation journey (if it
  ships). Backend tests
  covering fixture idempotency
  + tenant scoping per the
  M20 backend test precedent.
- **`backend/dealer_ai/scripts/audit_operational_surface.py`**
  — existing (M21.1) audit
  script. Corrected per §5.e
  Option B to handle nested
  template literals in URL
  construction paths. Explicit
  scope: fix the four known
  accounting misclassifications
  plus any additional false-
  negative patterns of the
  same class. Explicit non-
  scope: AST rewrite.
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`**
  — existing (M21.1/M21.5)
  audit artifact. Regenerated
  at M22.1 close with
  corrected accounting
  dispositions. Coverage
  count expected to increase
  by at least four
  (accounting misclassifications
  corrected) and potentially
  more (any other false-
  negative patterns discovered).

### Extended — support helpers

- **`acceptance/support/assertions/accounting.ts`**
  — existing (M20.3) accounting
  business-outcome assertion
  helpers (`expectSnapshotBalanced`,
  `expectSnapshotCountAtLeast`).
  Extended with new helpers
  for the reversal journey:
  `expectJournalEntryReversed(request, originalId)`
  asserts a reversal exists
  with swapped lines and
  correct linkage. Additional
  helpers per M22.3 workflow
  requirements.

### Consumed but not modified

- **All shipped M1–M21 service
  verbs and DRF endpoints.** M22
  journeys exercise them; no
  backend modifications.
- **All shipped frontend routes
  and pages.** M22 authors
  journeys against them; no
  page modifications beyond
  §5.d small operator-surface
  gap fixes if any are
  surfaced.
- **All shipped M1–M21 tenancy
  carriers, permission classes,
  and migrations.** No
  modifications. Zero-drift
  streak extends **twenty-one
  → twenty-two** consecutive
  milestones.
- **M20 acceptance framework +
  M20/M21 CI job.** M22
  consumes the framework and
  extends journey count; no
  framework modifications. New
  journey files follow the
  M20/M21 spec-file convention.

## 3. What's NOT in this milestone (deferrals)

Every deferral recorded with a
clear re-entry path. **Twelve M22-
specific + eleven universal = 23
deferrals.**

**DoD compliance (per M21.0 §5.f
Option B amendment formalized in
IMPLEMENTATION_ROADMAP at M21.5):**
M22 satisfies the customer-facing
milestone journey-addition
requirement **by construction**.
Every implementation increment
(M22.2 anchor JE reversal journey;
conditional M22.3 additional
journeys per §5.b) adds a
Playwright operational journey.
The audit-tooling correction
increment (M22.1) is supporting
work and does not itself require
a journey change. The close-out
increment (M22.4) references the
journeys shipped during M22.2 +
M22.3 as the DoD-satisfying
output.

**M22-specific deferrals:**

1. **Building new accounting UI.**
   Explicit non-scope per §5.a
   refined framing. M22 does not
   ship new components, new
   wrappers, new pages, or new
   routes. If §5.d classifies a
   discovered gap as "large,"
   the gap is documented in
   retrospective §9 as a future
   accounting candidate, not
   built in-scope.
2. **New backend service verbs
   or endpoints.** Explicit non-
   scope. If journey authoring
   surfaces a workflow requiring
   a new verb, it becomes future
   evidence for a domain-shaped
   milestone.
3. **Component-level refactoring
   for its own sake.** Non-scope
   per Rule 4. Small operator-
   surface fixes to unblock
   validation (per §5.d) are
   in-scope; broader refactoring
   is not.
4. **Full AST-based audit
   rewrite.** Explicit non-scope
   per §5.e Option B. Targeted
   regex fix only. Deeper
   refactor deferred to a future
   audit-tooling milestone.
5. **Non-accounting audit
   corrections.** M22 fixes only
   the accounting false-
   negatives + the underlying
   template-literal class. Other
   audit correctness issues
   (if any) are catalogued for
   future audit-tooling work.
6. **Broader accounting workflows
   without shipped UI.** JE
   creation UI (`accountingApi.ts`
   exposes no `createJournalEntry`
   wrapper based on shipped
   surface; the create endpoint
   ships but has no operator
   form); cost-posting failures
   remediation actions (currently
   read-only rendering only);
   month-end close workflow
   (may not exist as a coherent
   operator surface); accounting-
   focused operator navigation
   surface (may or may not be
   discoverable). All deferred
   pending §5.b evidence during
   M22.2+ journey authoring.
7. **Migration to `vite preview`
   in CI.** Carries forward from
   M20.5 §0.a → M21 §3(6). CI
   stays on `vite dev`.
8. **Cross-browser CI matrix.**
   Carries forward from M20 → M21
   §3(7). Chromium-only in CI.
9. **npm audit vulnerability
   remediation.** Carries forward
   from M20.5 §0.a → M21 §3(8).
10. **CI artifact upload
    verification via intentional
    failure.** Carries forward
    from M20.5 §0.a → M21 §3(9).
    M22 acceptance runs may or
    may not naturally regress;
    if any journey fails during
    the M22 push cycle we
    observe the artifact flow
    then.
11. **Systematic audit refresh
    schedule.** Carries forward
    from M21 §3(10). M22
    regenerates once at M22.1
    close; formal cadence
    remains future.
12. **Retrospective §9 next-
    candidate lock.** M22
    retrospective §9 documents
    evidence surfaced during
    journey authoring but does
    not pre-lock M23 target.
    M23.0 open follows the same
    recommend-and-confirm
    posture used at M22.0.

**Universal deferrals (any
platform milestone):**

- Payroll (external service).
- W-2 / 1099 generation
  (external service).
- Year-end tax return
  preparation (external CPA).
- GAAP-compliant audited
  financial reporting.
- Direct DMS integration
  (future vendor-integration
  milestone).
- Real inventory-feed
  integrations
  (Manheim / ADESA / ACV).
- Bilingual UI.
- Payment processing / e-sign
  / DMS write-back.
- Multi-tenant SaaS shell
  (billing / org).
- Predictive ML on
  operational data.
- SSO / MFA on top of M1 auth.

## 4. What existing tests bind

M22 introduces zero new backend
migrations, zero new tenancy
carriers, zero new permission
classes, zero new endpoints, zero
new frontend routes. All existing
`>=` counting tests stay
satisfied.

- **Backend test baseline.** M22
  is expected to grow the backend
  baseline modestly through new
  seed fixture tests
  (idempotency + tenant scoping
  for the reversible JE fixture
  and any multi-JE fixture per
  M21 pattern) plus possible
  audit-script correctness
  tests. Baseline **4,761** at
  M22.0 open; target
  **~4,765–4,775** at M22 close
  depending on final scope
  selection.
- **Frontend Vitest baseline.**
  M22 introduces no new
  components (per §5.a refined
  framing). Vitest coverage
  stays at **180** at M22 close
  unless §5.d small operator-
  surface fixes add test cases
  incidentally. If Vitest count
  grows, growth stays modest
  (a handful of new cases at
  most).
- **Acceptance suite.** Journey
  count grows from **6 → 7 or
  more** by M22 close depending
  on §5.b enumeration
  outcomes. Minimum shape: 6
  existing + 1 M22.2 JE
  reversal journey = **7**.
  Conditional shape: 6 + 1 +
  N M22.3 journeys where N
  depends on §5.b findings.
  Pilot-critical subset stays
  as-is; new journeys default
  to full-suite unless
  operational criticality
  argues otherwise (evaluated
  at each authoring
  increment's open).
- **Migrations.** Unchanged
  through M22 close at
  `0001`–`0048`.
- **Tenancy carriers.**
  Unchanged at **52**.
- **Permission classes.**
  Unchanged at **7 actual**.
  Zero-drift streak extends
  **twenty-one → twenty-two**
  consecutive milestones
  (M10 → M22).
- **DRF admin surface.**
  Unchanged at **113**. M22
  journeys exercise existing
  endpoints; no endpoints
  added.
- **Frontend operator routes.**
  Unchanged at **20**. M22
  journeys navigate to
  existing routes; no routes
  added.
- **Celery-beat task
  families.** Unchanged at
  **10**.

## 5. Load-bearing decisions

Seven decisions. **All confirmed
as-recommended at SESSION_171
M22.0 open.** Streak extends to
**88 planning-time as-recommended
M5.1 → M22.0** (thirteen
consecutive milestones now).

### 5.a `[RESOLVED at SESSION_171 open]` — Milestone target selection

**Question.** Which candidate
from the M22 skeleton (A, O2, T,
U, L, M, D, C, P, G) defines M22
scope?

**Decision.** **Candidate A —
Return to accounting stream**,
reshaped by M22.0 empirical
discovery from "ship missing UI"
into **Accounting Operational
Validation**. User named at
SESSION_171 M22.0 open. Milestone
name: **"Accounting Operational
Validation."** Discovery surfaced
that both anchor UIs originally
named (JE reversal + trial-balance
snapshot create/list/detail)
already ship as fully-wired
operator pages from M14.2–M14.4
and M17.2; the M21.5 audit
misclassified four accounting
endpoints as backend-only. User
redirected M22 from UI creation
to workflow validation +
supporting audit correction.
Candidate O2 preserved for M23+
with M22 journey-authoring
evidence as scope input.
Candidates T / U / L / M / D / C
/ P / G all deferred with re-
entry paths preserved per
discovery rule.

**Rationale.** (1) Four
consecutive milestones now have
diverged from the M18 §8
accounting designation. Deferring
a fifth compounds the divergence.
(2) The refined framing preserves
Rule 5 (preserve existing code)
— M22 does not rebuild what
already ships. (3) The refined
framing preserves Rule 6 (build
around operational problems) —
"can an office manager actually
perform the shipped accounting
workflow" is a real operational
question the codebase cannot
currently answer. (4) The M22
completion state produces
evidence for M23+ candidate
selection (per §5.a rationale for
M21 → M22 transition). (5)
Streak-neutral: zero new tenancy
carriers, zero new permission
classes; zero-drift streak
extends 21 → 22.

### 5.b `[RESOLVED at SESSION_171 open]` — Workflow enumeration source

**Question.** What defines the
"shipped accounting workflow"
surface M22 validates?

- **Option A** — Walk shipped
  accounting pages and enumerate
  user-facing affordances.
- **Option B** — Walk the audit's
  accounting endpoint rows and
  verify each has a UI path.
- **Option C** — Walk the office-
  manager persona's expected
  accounting workflow.
- **Option D** — Options A + C
  combined (page-surface
  authoritative; persona
  ordering).

**Decision. Option D — pages +
persona combined** confirmed
as-recommended.

**Rationale.** (1) Pages define
what's shippable; walking them
enumerates every user-facing
affordance regardless of audit
disposition. (2) Persona
provides authoring order —
freeze-a-period (existing) is
more workflow-critical than
JE-list-navigation is more
workflow-critical than JE-
reversal-once-per-quarter, but
the reversal journey is the
one with the highest untested
business risk. (3) Explicitly
rejects Option B — the audit
is precisely the source we've
proven unreliable for
accounting; using it as
enumeration source would
propagate the noise. (4)
Rejects Option A alone
because pages might have
affordances that aren't
persona-critical (e.g. a
button covered by an
existing journey's implicit
navigation). Persona ordering
prevents authoring redundant
journeys. (5) Rejects Option
C alone because persona
walking without page grounding
risks omitting affordances
the persona doesn't know
about but that ship in the
UI.

### 5.c `[RESOLVED at SESSION_171 open]` — Journey folder + shape

**Question.** Where do new
accounting journeys live?

- **Option A** — Extend the
  single `office/accounting_workflow.spec.ts`
  to cover everything.
- **Option B** — Per-workflow
  spec files under `office/`
  (siblings to the existing
  spec).
- **Option C** — New
  `acceptance/journeys/accounting/`
  folder distinct from `office/`.

**Decision. Option B — per-
workflow spec files under
office/** confirmed as-
recommended.

**Rationale.** (1) The office-
manager persona already owns the
container; introducing a
separate `accounting/` folder
splits the same persona's
journeys across two locations
without semantic justification.
(2) Distinct workflows (freeze
period, reverse JE, browse JE
history) warrant distinct spec
files matching the M21 §5.e
Option C precedent — "new
journey where workflow shape is
distinct." (3) Option A creates
a monster spec file that mixes
concerns and makes selective
test running harder (a JE
reversal debug shouldn't require
running the freeze journey).
(4) Preserves existing
`accounting_workflow.spec.ts`
intact — the existing journey
is trusted output; adding
siblings is additive.

### 5.d `[RESOLVED at SESSION_171 open]` — Discovered-gap handling posture

**Question.** When journey
authoring reveals a workflow
that cannot complete through the
UI, what happens?

- **Option A** — Fix everything
  discovered in-scope.
- **Option B** — Fix small
  operator-surface gaps
  in-scope; larger workflows
  become future evidence.
- **Option C** — Catalog
  everything; fix nothing
  in-scope.

**Decision. Option B — split
by size** confirmed as-
recommended.

**Rationale.** (1) Matches user
explicit instruction at M22.0
redirect. (2) Preserves Rule 4
(scope discipline) — a small
label typo or missing testid
discovered during authoring
shouldn't force a whole
milestone rewrite; blocking
validation of a shipped
workflow on a one-line fix
violates the governing
contract's outcome
(operational-completion
confidence). (3) Preserves
Rule 5 (preserve existing
code) at the scope level — a
missing form or missing
service verb is genuinely new
work, not a "small polish"
call. (4) Definition of
"small": one-file trivial
change — missing testid,
broken link, label typo, form
validation bug, missing button
label, missing error handling
copy. Definition of "large":
missing form, missing wrapper,
missing service verb, new UI
structure, new page. (5)
Discovered gaps get recorded
in §0.a M22.N amendments
either way — small ones with
"fixed in-scope" notation;
large ones with "documented as
next candidate" notation.

### 5.e `[RESOLVED at SESSION_171 open]` — Audit tooling correction posture

**Question.** How deep does the
audit-tooling correction go?

- **Option A** — Full AST-based
  rewrite using TypeScript
  compiler API.
- **Option B** — Targeted regex
  fix for the documented false-
  negative class + known
  accounting misclassifications.
- **Option C** — Defer audit
  fix; document journey
  findings as authoritative
  operational truth.

**Decision. Option B — targeted
regex fix** confirmed as-
recommended.

**Rationale.** (1) Matches
user's explicit "supporting work
rather than centerpiece"
framing. (2) The known false-
negative class is narrow — the
M21 retrospective §4 documented
it as "nested TypeScript
template literals (`${qs ? \`?${qs}\`
: ""}`) confuse the URL
normalizer." A targeted regex
enhancement addresses that
class directly; if additional
false-negative patterns surface
during correction, extend the
targeted fix rather than
switching to AST. (3) Option A
risks scope creep — a full AST
rewrite could easily consume
the whole milestone, defeating
the "validation is the
centerpiece" framing. (4)
Option C leaves M23+ candidate
selection dependent on
journey-authoring evidence
alone; the audit remains
partially untrustworthy for
future OSC-shaped milestones.
Fixing what we can now
compounds trust as future
milestones consume the
artifact. (5) Explicit budget
constraint: if the targeted
fix exceeds ~2 hours at M22.1
open, defer the deeper
refactor to a future audit-
tooling milestone — do not
let audit correction bleed
into anchor scope.

### 5.f `[RESOLVED at SESSION_171 open]` — Baseline verification approach

**Question.** How do we
establish what actually works
today before authoring the
validation?

- **Option A** — Manual
  developer pass-through of
  each shipped workflow before
  authoring the journey.
- **Option B** — Author
  journey directly; failures
  reveal reality (journey-as-
  verifier).
- **Option C** — Trust
  existing Vitest coverage as
  baseline.

**Decision. Option B —
journey-as-verifier** confirmed
as-recommended.

**Rationale.** (1) Playwright
IS the verification. If the
shipped page cannot complete
the workflow, the journey
fails with a specific business-
outcome assertion — that
failure is the evidence, no
manual step needed. (2)
Preserves the M20 fail-loud
contract — journey failures
target the business outcome
that failed. (3) Option A
introduces a manual step
without adding evidence
Playwright wouldn't already
surface — every discovery a
manual pass-through would
produce also surfaces as a
journey failure. Manual
verification is redundant
work. (4) Option C is
insufficient — Vitest mocks
the API layer; passing
Vitest coverage means the
component renders correctly
against mocked responses, not
that the full stack completes
the workflow. Only Playwright
exercises the auth + tenant
middleware + service verb +
DB round-trip. (5) The §5.d
handling posture governs the
response to any journey
failure — small in-scope fix
or documented next candidate.

### 5.g `[RESOLVED at SESSION_171 open]` — Seed command pattern

**Question.** New per-journey
seed commands or extend the
existing accounting seed?

- **Option A** — Extend
  `seed_journey_office_accounting_workflow`
  additively with per-journey
  fixtures.
- **Option B** — New per-
  workflow seed commands
  (`seed_journey_office_je_reversal`,
  `seed_journey_office_je_list`, ...).

**Decision. Option A — extend
existing seed additively**
confirmed as-recommended.

**Rationale.** (1) Matches M21
Lesson 4 ("reference existing
seed shape") — the seed
already serves the office/
accounting persona and posts
balanced JEs. Adding a
reversible-JE fixture is
additive; adding a multi-JE
fixture for pagination is
additive. (2) Preserves
tenant context — one seed
run continues to establish
the full accounting-workflow
setup, regardless of which
journey runs against it. (3)
Preserves idempotency via
stable description tags per
the existing seed pattern
(each fixture has a
distinguishable
`[M22.N-...]` prefix so
re-invocation detects +
reuses existing rows). (4)
Option B creates seed sprawl
— five per-workflow seeds
where one extended seed
suffices. (5) Splitting is
reversible; if the extended
seed becomes hard to reason
about mid-milestone, split
then. Do not pre-split.

### 5.h `[RESOLVED at SESSION_171 open]` — Increment sequencing + completion contract

**Question.** How are M22
increments sequenced, and what
does "M22 shipped" mean?

- **Option A** — 3 fixed
  increments (M22.0 + M22.1 all
  validation + M22.2 close-out).
- **Option B** — Evidence-
  sized four-to-five increments.
  M22.0 planning + M22.1 audit
  correction + refresh + M22.2
  JE reversal journey + M22.3
  additional journeys per §5.b
  (conditional) + M22.4 close-
  out.
- **Option C** — Fixed 5-
  increment shape matching M21.

**Decision. Option B —
evidence-sized four-to-five
increments** confirmed as-
recommended.

**Rationale.** (1) Matches M21
§5.h Option B posture. Fixed
increment counts distort scope
either upward (padding) or
downward (compression). (2)
Preserves Rule 4 — small
complete increments — while
respecting the evidence-driven
nature of §5.b enumeration.
(3) Two increments are pre-
committed at open (M22.1
audit correction + M22.2 JE
reversal) because their scope
is known from M22.0
discovery. M22.3 collapses if
the M22.2 authoring +
concurrent §5.b page/persona
walk surface only the JE
reversal gap; expands to 1-N
sub-increments if additional
distinct workflows warrant
distinct journeys. (4) M22.4
close matches the M20.5 /
M21.5 pattern — CI hardening,
retrospective, capability
matrix update, M23 skeleton,
coordinated close-out commit.
(5) Increment sizing is
bounded by one supporting-
work increment + one to N
anchor increments + close;
four is the expected minimum
at M22.0 open; five if §5.b
enumeration surfaces one
additional journey worth
authoring separately.

**Milestone completion
contract:**

- **JE reversal journey ships**
  at `acceptance/journeys/office/accounting_je_reversal.spec.ts`
  with reversible-JE seed
  fixture + business-outcome
  assertion helper. Journey
  passes locally + on `main`
  CI.
- **Any additional M22.3
  journeys ship** with
  fixtures + assertions per
  §5.g and §5.b enumeration
  findings, or M22.3 is
  explicitly skipped in
  §0.a with rationale.
- **Audit tooling corrected**
  — nested-template-literal
  false-negative class closed;
  the four known accounting
  misclassifications
  (`admin-trial-balance`,
  `admin-journal-entry-list`,
  `admin-cost-posting-failures`,
  `admin-trial-balance-snapshot-list`)
  reclassify to `covered` in
  the regenerated M22.1
  artifact. Additional false-
  negative patterns surfaced
  during the correction pass
  either get fixed or get
  documented in §0.a M22.1
  amendments.
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  regenerated** with accurate
  accounting coverage at M22.1
  close.
- **All M22 shipped journeys +
  extensions pass on `main`
  CI** in the coordinated push
  at M22.4.
- **Retrospective §8** records
  the accounting workflows
  now operationally complete
  by evidence, the audit
  corrections landed, and the
  M22-specific deferrals
  reviewed.
- **Retrospective §9** records
  the next-accounting-
  candidate identified by
  journey-authoring evidence
  (if any). Format: "workflow
  X cannot complete through
  the UI because Y;
  reproducible steps in the
  M22.N handoff; recommended
  M23 elevation with bounded
  scope Z" — evidence-
  grounded, not speculation.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD
   amendment landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
   §8 (M21 unblocks) + §9
   (standing M22 question,
   answered by M22.0 discovery)
6. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 governing contract that
   M22 refines for validation-
   shape milestones)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — known
   unreliable for accounting
   until M22.1 correction lands;
   authoritative for other
   domains post-M22.1 regen)
8. `docs/CAPABILITY_MATRIX.md`
   §7v (M21 shipped surface)

## 7. Sequencing

**Four-to-five increments total**
— locked at SESSION_171 M22.0
close per §5.h Option B. Expected
minimum shape is four (M22.0 +
M22.1 + M22.2 + M22.4) with
M22.3 conditional on §5.b
enumeration findings during the
M22.2 authoring pass. Combine
increments if implementation
evidence shows a smaller complete
shape; do not split merely to
match this draft.

### Increment 0 (M22.0) — Planning refinement + target selection

**Scope.** SESSION_171 (this
session). §5.a Candidate A
confirmed at open, reshaped from
"ship missing UI" to
**Accounting Operational
Validation** per M22.0
discovery. §5.b–§5.h drafted
with recommendations; all seven
confirmed as-recommended. Full
memo expansion (this document).
DoD compliance verified via §3
by-construction path.

**Deliverable.**
- This planning memo, expanded
  from the M21.5 skeleton.
- §0.a change log with all
  seven §5 decisions resolved.
- Session handoff at
  `docs/handoffs/SESSION_171_m22_inc0_planning.md`.
- `00-START-NEXT-SESSION.md`
  overwritten with M22.1
  priority.

**Backend baseline unchanged:**
4,761 pass, 1 skipped, 0 fail.
Frontend Vitest unchanged: 180
pass. Acceptance suite
unchanged: 6 journeys.

### Increment 1 (M22.1) — Audit tooling correction + artifact refresh

**Scope.** SESSION_172. Supporting
work per §5.e Option B.

**Deliverable.**
- Targeted regex fix in
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  handling nested TypeScript
  template literals in URL
  construction paths.
- Optional (as-needed): a
  small backend test verifying
  the fix against the known
  false-negative patterns.
- Regenerated
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  with corrected accounting
  dispositions. Coverage
  count expected to increase
  by at least four
  (accounting
  misclassifications
  corrected); if additional
  false-negatives surface,
  cataloged and either fixed
  or deferred per §0.a M22.1
  amendment.
- Session handoff at
  `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M22.2.

**Backend baseline target at
M22.1 close:** 4,761 → **~4,762–
4,763** (audit-script tests if
any). Frontend Vitest:
unchanged. Acceptance suite:
unchanged.

**Budget guard.** If audit
correction exceeds ~2 hours,
stop, document the remaining
false-negative patterns as a
future audit-tooling milestone,
and proceed to M22.2 with a
partial fix per §5.e Option B.

### Increment 2 (M22.2) — JE reversal journey + seed extension

**Scope.** SESSION_173. First
anchor journey.

**Deliverable.**
- Extended
  `seed_journey_office_accounting_workflow`
  with a reversible-JE fixture
  (stable description tag;
  idempotent) + backend tests
  covering idempotency +
  tenant scoping.
- Extended
  `acceptance/support/assertions/accounting.ts`
  with `expectJournalEntryReversed(request, originalId)`
  helper.
- New
  `acceptance/journeys/office/accounting_je_reversal.spec.ts`
  walking: navigate to JE
  detail for seeded reversible
  entry → open reversal
  dialog → fill reason → click
  confirm → verify status
  message → verify page reload
  shows reversal linkage.
  Business-outcome assertion:
  reversal entry exists with
  swapped lines and correct
  `reverses_id` linkage.
- Concurrent §5.b page/persona
  walk during authoring —
  document any additional
  accounting workflows
  surfaced that warrant
  distinct M22.3 journeys.
- Small operator-surface gap
  fixes per §5.d if any
  discovered (in-scope) with
  §0.a M22.2 amendments.
- Session handoff at
  `docs/handoffs/SESSION_173_m22_inc2_je_reversal.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M22.3 or
  M22.4 depending on §5.b
  findings.

**Backend baseline target at
M22.2 close:** ~4,763 → **~4,765**
(seed fixture idempotency
tests). Frontend Vitest:
unchanged unless §5.d small
fixes add test cases. Acceptance
suite: **6 → 7**.

### Increment 3 (M22.3) — Additional journeys per §5.b enumeration (conditional)

**Scope.** SESSION_174.
Conditional per M22.2 §5.b
findings. Ships zero or more
additional per-workflow
journeys (JE list navigation,
cost-posting failures rendering
extension, as-of picker
interaction, other §5.b-
surfaced workflows). Skipped
entirely if the M22.2 walk
demonstrates JE reversal is
the only journey-worthy gap.

**Deliverable.**
- For each additional journey:
  seed fixture extension +
  business-outcome assertion
  helper extension + spec
  file per §5.c Option B.
- Small operator-surface gap
  fixes per §5.d.
- Session handoff at
  `docs/handoffs/SESSION_174_m22_inc3_additional_journeys.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M22.4.

**Backend baseline target at
M22.3 close:** depends on
scope. Frontend Vitest:
depends on §5.d fixes.
Acceptance suite: **7 → 7+N**
where N is the count of
distinct additional journeys
authored.

**Skip criterion.** If the
M22.2 page/persona walk
surfaces no additional
distinct journey-worthy
workflows (all workflow steps
covered by the JE reversal or
existing freeze journey's
implicit navigation), M22.3
is explicitly SKIPPED with
§0.a amendment recording the
enumeration outcome. M22.4
close-out becomes the next
session in that case.

### Increment 4 (M22.4) — CI hardening + retrospective + close-out

**Scope.** SESSION_174 (if
M22.3 skipped) or SESSION_175
(if M22.3 shipped). Full-suite
CI validation + close-out
documentation + capability
matrix update + retrospective
+ M23 skeleton.

**Deliverable.**
- CI job validation on all
  new / extended journeys.
- `docs/CAPABILITY_MATRIX.md`
  §7w — M22 shipped surface:
  new / extended journeys +
  audit tooling correction +
  seed fixture extensions.
- `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
  covering lessons learned,
  what shipped, deferrals
  reviewed, §8 corrections
  landed, §9 next-accounting-
  candidate identified with
  evidence.
- `docs/roadmap/MILESTONE_23_PLANNING.md`
  skeleton (status: draft)
  with candidate list
  refreshed from M22
  retrospective §9 findings +
  remaining M21 / M20 / M19
  candidates.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M22 shipped
  status.
- Session handoff at
  `docs/handoffs/SESSION_17{4|5}_m22_inc4_close.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M23.0.
- Coordinated close-out commit
  + push per M18.6 / M19.6 /
  M20.5 / M21.5 pattern.

**Backend baseline target at
M22.4 close:** **~4,765–
4,775** depending on scope.
Frontend Vitest: **180**
unless §5.d fixes added
cases. Acceptance suite: **7
or 7+N** journeys. Migrations
unchanged `0001`–`0048`.
Tenancy carriers unchanged at
52. Permission classes
unchanged at 7 (zero-drift
streak twenty-one → **twenty-
two** consecutive milestones).
Frontend operator routes
unchanged at 20.
