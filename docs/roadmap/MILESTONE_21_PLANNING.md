---
title: "Milestone 21 — Operational Surface Completion"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_165 (skeleton), SESSION_166 (expansion)
milestone: 21
milestone_name: "Operational Surface Completion"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_20_PLANNING.md
  - docs/roadmap/MILESTONE_20_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_19_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_18_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md
---

# Milestone 21 — Operational Surface Completion

> **Active planning memo.** Expanded at
> SESSION_166 M21.0 open from the
> skeleton drafted at M20.5 close.
> §5.a Candidate O confirmed at open —
> Operational Surface Completion, an
> evidence-driven umbrella milestone
> that closes the highest-value missing
> UI workflows found by the M20
> operational audit. Every scope item
> maps to an already-shipped backend
> capability that lacks an operator-
> facing UI; every operator surface
> shipped under M21 adds or extends a
> corresponding Playwright operational
> journey.
>
> **M21 is the first milestone to
> consume M20's substrate as its
> primary planning input.** The M20
> acceptance suite produced a concrete
> gap map (M21 planning skeleton
> Input 1 + Input 2) that this
> milestone converts into shipped
> operator surface. Two anchor
> implementations are carried in at
> planning-time: **BHPH write-side UI**
> (subsumes carry-forward Candidate B;
> unblocks re-expansion of the M20.4
> journey) and **be-back write-side
> UI** (surfaced during M20.2 sales-
> manager journey authoring). A third
> candidate — follow-up cadence queue
> UI — enters scope only if the
> systematic audit at M21.1 confirms
> it fits without violating milestone
> discipline.
>
> **M21 is a partially domain,
> partially tooling-axis milestone.**
> Domain-axis surface: new frontend
> forms + action buttons + queues
> against already-shipped M11.6, M12
> (and possibly other) backend
> endpoints. Tooling-axis surface: a
> new systematic operational-audit
> artifact + a formalized Definition
> of Done amendment that binds every
> future customer-facing milestone to
> journey-extension. M21 introduces
> zero new tenancy carriers, zero new
> migrations, zero new permission
> classes, zero new DRF endpoints (all
> targets are already shipped). The
> zero-drift permission-class streak
> extends **twenty → twenty-one**
> consecutive milestones.
>
> **Eight load-bearing decisions** —
> §5.a target + §5.b audit
> methodology + §5.c audit artifact
> format + §5.d scope selection
> mechanism + §5.e journey-extension
> contract + §5.f DoD amendment +
> §5.g testid hardening posture +
> §5.h increment sequencing +
> completion contract. **All eight
> confirmed as-recommended at
> SESSION_166 M21.0 open** — streak
> extends to **87 planning-time as-
> recommended M5.1 → M21.0** across
> **twelve consecutive milestones
> now** (M10 → M21).

## Guiding principle (Candidate O governing contract)

Every M21 shipped surface must
satisfy four conditions:

1. **Maps to an already-shipped
   backend capability** — service
   verb, DRF endpoint, or both.
   Confirmed by cross-reference
   during the M21.1 systematic
   audit.
2. **Closes a missing operator-
   facing UI** — the capability is
   reachable today only via curl /
   Postman / Django shell, or is
   unreachable entirely. Dealership
   staff cannot operate it through
   the product.
3. **Adds or extends a Playwright
   operational journey** — the
   coverage contract from M20
   extends by construction; no
   silent regression window opens.
4. **Is not generic UX polish** —
   scope items must map to a
   backend capability + a missing
   form/button/action/queue, not
   to "the current UI could look
   nicer." Cosmetic friction
   discovered mid-milestone feeds
   Candidate P (deferred), not
   this milestone.

This governing contract binds every
§5 decision, every increment scope
call, every audit finding review,
and every review of a proposed scope
addition. When these conditions
conflict with feasibility mid-
milestone, the resolution posture is
to defer the scope item to a future
milestone (Candidate O2 or another
umbrella) rather than relax any of
the four conditions.

## 0. Engineering practices to preserve from M2–M20

Same posture as M20.0 except where
noted. Non-negotiable:

- **Backend-first architecture.**
  M21 ships no new backend
  business logic. Every UI action
  goes through an existing service
  verb via an existing endpoint;
  the frontend is the only
  workspace whose surface expands.
  Backend delta commands (if any
  are needed for M21's journey
  extensions) live in
  `dealer_ai/management/commands/`
  and compose existing service
  verbs, per the M20 §5.d
  precedent.
- **Service ownership.** Every UI
  target must invoke an existing
  service verb — no parallel
  write paths. If a proposed
  scope item would require a new
  service verb to be shipped, it
  is out of scope for M21
  (candidate for a domain
  milestone).
- **Tenancy discipline.** Every
  new UI form scopes reads +
  writes through the existing
  tenant middleware. No M21 UI
  bypasses the tenancy carrier
  stack; every write asserts
  dealership context per the
  existing authenticated-cookie
  pattern.
- **Load-bearing decisions get
  user review BEFORE code.** All
  eight §5 decisions confirmed at
  SESSION_166 M21.0 open. Any
  implementation-time micro-
  decisions surface as §0.a
  amendments.
- **Additive extension over
  fork.** M21 does not modify
  existing endpoints, does not
  modify existing service verbs,
  does not modify existing pages
  in ways that break current
  operator use. New frontend
  surfaces attach to existing
  pages/panels (per the M17 §6
  lesson 6 + M19.4 in-place-page
  extension posture) or introduce
  new panels within existing
  routes; **M21 adds zero
  frontend routes**.
- **Zero-drift permission-class
  posture.** Every UI action uses
  the existing authenticated-
  cookie flow; every endpoint
  invocation stays within its
  shipped permission class. Streak
  extends **twenty → twenty-one**
  consecutive milestones (M10 →
  M21). If a scope item requires a
  new permission class, it is out
  of scope for M21.
- **Every M21 assertion of
  shipped-surface counts uses
  `>=`** per the M9–M20 growth-
  only-list lesson (M18.5
  retrospective §6 lesson 5).
  Journey counts stay exact-
  equality where the milestone
  shape locks a specific number
  (M21 targets six journeys at
  open — same shape as M20 close;
  journey count may grow to seven
  if a follow-up cadence journey
  is added under §5.h Increment 4
  scope selection).
- **In-place page extension over
  new route** per M17 §6 lesson 6
  + M19.4 posture. M21 target
  pages: `BhphCollectorDashboard`
  or equivalent for BHPH write
  surfaces; `SalesManagerDashboard`
  / lead-detail modal for be-back
  write surfaces; queue surface
  attaches to existing
  `SalesManagerDashboard` if
  follow-up cadence enters scope.
  No new top-level routes.
- **Naming discipline** per M17
  §6 lesson 3. Component names
  reflect operator vocabulary
  (`RecordPromiseToPayForm`,
  `RecordBeBackForm`,
  `MarkBrokenPromiseButton`),
  not developer vocabulary
  (`PtpModal`, `BbForm`).
- **Journey isolation, per-
  journey delta seeds, and
  business-outcome assertions**
  per M20 §5.d and §5.e. Every
  new journey (or every extension
  of an existing journey) carries
  a corresponding seed delta
  command that composes existing
  service verbs, and asserts
  business state (a promise is
  recorded, a be-back is logged,
  a repossession is initiated) —
  not DOM state.
- **Fail-loud contract** per M20
  §0. Journey test names identify
  the operational workflow.
  Failure messages target the
  business outcome that failed.
  Screenshots + traces attach on
  failure per the M20 CI job
  configuration.

### 0.a Change log — resolved decisions

**SESSION_166 M21.0 open (2026-08-03):**

- **§5.a → Candidate O confirmed
  at open.** User named at
  SESSION_166 open —
  **Operational Surface
  Completion**. Evidence-driven
  umbrella milestone with two
  anchor implementations (BHPH
  write-side UI + be-back write-
  side UI) and a systematic audit
  as Increment 1. Follow-up
  cadence queue UI is a
  conditional third anchor,
  entering scope only if the
  audit confirms fit.
  Candidate B (BHPH write-side
  UI) subsumed. Candidate A
  (accounting), Candidate P
  (onboarding UX polish),
  Candidate G (dashboard testid
  hardening), Candidates D, C
  (evidence-deferred), and
  Candidates T, U, L, M (signal-
  gated) all deferred with re-
  entry paths preserved per
  discovery rule.
- **§5.b → Option C confirmed as-
  recommended.** Combined
  service-verb + DRF-endpoint
  enumeration cross-referenced
  against frontend consumption.
  Belt-and-suspenders posture —
  service-verb walk catches
  capabilities that exist as
  verbs without endpoint
  exposure; DRF walk catches
  endpoints without frontend
  consumers. Audit is executed
  as programmatic scripts under
  `backend/dealer_ai/scripts/`
  (not runtime code); output
  feeds §5.c artifact.
- **§5.c → Option A confirmed as-
  recommended.** Single markdown
  audit artifact at
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Per-row schema: (a) backend
  capability, (b) missing
  operator surface, (c) affected
  operational journey, (d)
  recommended milestone
  disposition (`M21-anchor`,
  `M21-conditional`, `defer-
  candidate-O2`, `defer-domain-
  milestone`, `intentional-
  omission`). One canonical
  table + brief per-domain
  narrative sections; the
  artifact becomes the source of
  truth for M21 scope selection
  and for future OSC iterations.
- **§5.d → Option B confirmed as-
  recommended.** After the M21.1
  audit lands, the assistant
  drafts scope recommendations
  for M21.2 onward with rationale
  per candidate; user confirms or
  redirects. Two anchor
  implementations (BHPH + be-
  back) are pre-committed at
  §5.a; scope selection
  mechanism governs the
  conditional third anchor
  (follow-up cadence) and any
  audit-surfaced additions.
- **§5.e → Option C confirmed as-
  recommended.** Journey
  extension where the operator
  workflow shape naturally
  matches an existing journey
  (BHPH writes extend
  `bhph/collections_workflow.spec.ts`
  as originally planned pre-
  narrow at M20.4); new journey
  where the workflow shape is
  distinct from any existing
  journey (be-back writes may
  extend
  `sales_manager/daily_startup.spec.ts`
  or introduce a new sales-
  manager-adjacent journey based
  on M21.1 audit findings). Per-
  workflow decision made at each
  implementation increment's
  planning open.
- **§5.f → Option B confirmed as-
  recommended.** Definition of
  Done amendment adopted: **every
  future customer-facing
  milestone must either add or
  update at least one operational
  Playwright journey, or
  explicitly document in §3 of
  its planning memo why no
  journey change is required.**
  Preserves engineering
  discipline without creating
  bureaucracy for legitimate
  infrastructure-only milestones.
  Amendment applies from M21
  forward. M21 itself trivially
  satisfies via the §5.e journey-
  extension contract.
- **§5.g → Option B confirmed as-
  recommended.** Testid
  hardening (Candidate G)
  bundled opportunistically —
  add `data-testid` attributes
  only where new M21 journeys or
  extended M21 journeys need
  them for stable selectors.
  Full-coverage testid pass
  remains a Candidate G scope
  item for a future milestone;
  M21 does not obligate itself
  to coverage beyond its
  journeys' needs.
- **§5.h → Option B confirmed as-
  recommended.** Evidence-sized
  increment count. **M21.0
  planning** (this session) +
  **M21.1 systematic audit + M21
  scope lock** + **M21.2 BHPH
  write-side UI + journey
  extension** + **M21.3 be-back
  write-side UI + journey
  extension** + **M21.4
  conditional follow-up cadence
  UI + journey addition** (only
  if audit confirms fit; skipped
  otherwise) + **M21.5 close-
  out** (retrospective,
  capability matrix update, M22
  skeleton, coordinated close-
  out commit). Milestone
  completion contract: every
  in-scope UI ships with a
  passing operational journey
  extension or addition on
  `main` CI; audit artifact
  committed and current;
  retrospective §9 records
  standing question for M22.
- **Streak extends to 87
  planning-time as-recommended
  M5.1 → M21.0.** Twelve
  consecutive milestones now
  (M10 → M21).

## 1. Business questions this milestone answers

Five operator-workflow questions,
each tied to the governing contract.
Every question was answerable in
principle before M21 (backend
capability exists) but not in
practice (no UI path).

### Q1. Can a BHPH collector do their daily job through the product?

**Before M21:** Only partially. The
collector can review the portfolio
and drill into note detail (read
side). But recording a promise-to-
pay, marking a broken promise,
logging a collection contact, and
initiating repossession — the four
verbs that constitute the collector's
actual workday — are reachable only
via curl / Postman / Django shell.
The M12 backend has been shippable
by that measure since M12.7; the
M20.4 acceptance journey confirmed
the gap by having to narrow its
scope to the read side.

**After M21:** Yes. The M21.2 BHPH
write-side UI closes the four verbs.
The M20.4 journey re-expands to
cover the full workflow — record a
PtP, mark it broken next visit, log
the collection contact, initiate
repossession. Collector's daily
work is fully product-native.

### Q2. Can a sales manager triage the be-back queue and manage follow-up cadence through the product?

**Before M21:** Not for be-backs.
The M11.6 backend ships
`record_be_back`, `mark_returned`,
`mark_no_show` service verbs and
their DRF endpoints. No frontend
form exists for any of them; sales
managers cannot triage the be-back
queue through the UI. The M20.2
sales-manager daily-startup journey
narrowed to lead-assignment-only for
exactly this reason. Follow-up
cadence queue is a similar gap
identified in the M20.2 planning
notes — no dedicated frontend
surface.

**After M21:** Yes for be-backs
(anchor M21.3). Conditionally yes
for follow-up cadence — depends on
M21.1 audit confirming the cadence
UI fits M21 discipline. If cadence
lands in M21.4, the sales-manager
journey re-expands to cover be-
back triage + cadence review; if
not, cadence carries forward with a
documented re-entry path.

### Q3. What other backend-only capabilities exist that dealership staff cannot reach through the product?

**Before M21:** Unknown in
aggregate. Three are catalogued
(BHPH writes, be-back writes,
follow-up cadence). The M21
planning skeleton Input 1 explicitly
flagged additional suspects — recon
vendor comms, accounting reversal,
pilot outbound-enable — but no
systematic audit has been performed.
The scope of "backend-shipped-but-
UI-missing" is unmeasured.

**After M21:** Fully catalogued.
The M21.1 systematic audit walks
every shipped service verb and DRF
endpoint, cross-references against
frontend consumption, and produces
the M21 audit artifact with per-row
disposition (M21-anchor, M21-
conditional, defer-candidate-O2,
defer-domain-milestone, intentional-
omission). Future OSC-shaped
milestones select from this artifact
with evidence in hand.

### Q4. Is the M20 acceptance-testing substrate durable as milestones accumulate, or does it silently atrophy?

**Before M21:** Durability is
unspecified. The M20 substrate ships
six journeys but nothing binds
future milestones to extend them.
Two silent-regression paths exist:
(1) a new customer-facing surface
ships without a journey; regression
detection reverts to the pre-M20
model (human exploratory testing).
(2) an existing surface gets
extended, breaking assumptions in an
existing journey; the assertion
matches the wrong business outcome
without failing loudly.

**After M21:** The DoD amendment
(§5.f) formally binds every future
customer-facing milestone to
journey-addition or -update, or to
explicit documentation of why no
journey change is required. Path 1
is closed by construction. Path 2
remains a concern requiring
authoring discipline, but the M21
audit artifact provides the standing
review target — future OSC
iterations regenerate the artifact
and re-check disposition rows.

### Q5. Can M22+ target selection be evidence-driven for operator-surface work, not intuition-driven?

**Before M21:** No. Operator-surface
priorities depend on what Chris
observes during his daily use and
what surfaces during acceptance-
journey authoring. Both are real
signals; neither is systematic. The
Candidate O in the M21 skeleton was
proposed precisely because no
systematic view existed.

**After M21:** Yes. The M21 audit
artifact catalogues every backend-
shipped capability against its UI
status with a recommended
disposition. Future milestones
proposing an OSC-shape can select
from a live artifact rather than
proposing scope from scratch. The
artifact itself becomes standing
substrate — regenerated when M21
closes and again when future OSC
milestones open.

## 2. What existing primitives extend

M21 continues the "additive
extension over fork" pattern
(M11.1 / M12.3 / M13.2 / M14.1 /
M15.1 / M16.1 / M17.1 / M18.1 /
M19.1 / M20.1). No new backend
service verbs, no new DRF endpoints,
no new tenancy carriers, no new
migrations, no new frontend routes,
no new permission classes.

### Extended — frontend workspace

- **BHPH collector dashboard /
  panel surface.** The M12.7
  frontend surface for the read
  side (portfolio table + note
  detail with Promises card,
  Contacts card, Repossessions
  card) becomes the anchor for
  new write-side components:
  - `RecordPromiseToPayForm`
    (attached to Promises card
    action area).
  - `MarkBrokenPromiseButton` +
    `MarkKeptPromiseButton` (row-
    level actions on Promises
    card).
  - `LogCollectionContactForm`
    (attached to Contacts card
    action area).
  - `InitiateRepossessionForm`
    (attached to Repossessions
    card action area).
  - `MarkRecoveredButton` (row-
    level action on
    Repossessions card).
- **Sales manager dashboard / lead
  detail modal surface.** The
  M11 sales manager dashboard +
  M11 Phase 4 lead detail modal
  become the anchor for be-back
  write-side components:
  - `RecordBeBackForm` (surface
    attached to lead detail
    modal or dashboard, per
    M21.3 planning-time decision).
  - `MarkBeBackReturnedButton` +
    `MarkBeBackNoShowButton` (row-
    level actions on be-back
    queue view).
  - `BeBackQueueTable` if the
    sales manager dashboard
    lacks a dedicated queue
    surface today (M21.1 audit
    to confirm).
- **Follow-up cadence queue
  surface** (conditional, M21.4
  scope-selection-dependent).
  Attaches to sales manager
  dashboard as a queue table +
  action panel. Only lands if
  M21.1 audit confirms the
  cadence backend surface is
  ready and the queue fits M21
  scope discipline.
- **Additional surfaces from
  audit findings** (conditional,
  M21.4 scope-selection-
  dependent). Any surface
  identified by the M21.1 audit
  with a disposition of
  `M21-anchor` (elevated at
  scope-lock) or `M21-conditional`
  (fits within remaining M21
  capacity) may enter scope. Any
  surface not selected receives
  `defer-candidate-O2` or
  `defer-domain-milestone`
  disposition with explicit re-
  entry path.

### Extended — acceptance workspace

- **`acceptance/journeys/bhph/collections_workflow.spec.ts`**
  — re-expanded from the M20.4
  narrowed scope to cover the
  full four-verb write side:
  record PtP → mark broken →
  log contact → initiate
  repossession. Business-outcome
  assertions extend accordingly
  (promise recorded, promise
  state = broken, contact
  logged, repossession state =
  initiated).
- **`acceptance/journeys/sales_manager/daily_startup.spec.ts`**
  — extended to cover be-back
  triage (record a be-back →
  mark returned; separately mark
  no-show) alongside the existing
  lead-assignment coverage.
  Alternative: a new
  `sales_manager/be_back_triage.spec.ts`
  journey introduced at M21.3
  open if the workflow shape
  warrants distinct isolation.
- **New journey for follow-up
  cadence** (conditional, M21.4).
  If cadence UI lands, a new
  journey at
  `acceptance/journeys/sales_manager/follow_up_cadence.spec.ts`
  or extension of the daily-
  startup journey, per M21.4
  planning-time decision.
- **Seed delta commands** for the
  extended / new journeys, per
  the M20 §5.d precedent. Each
  compose existing service verbs
  and are idempotent + tenant-
  scoped. Commands live in
  `dealer_ai/management/commands/seed_journey_*.py`
  and receive `+= backend tests`
  covering idempotency + tenant
  scoping (per M20 backend test
  precedent).

### New surface — audit artifact

- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`**
  — the M21.1 systematic audit
  output. Per-row schema per
  §5.c: (a) backend capability
  (service verb path + DRF
  endpoint path when present),
  (b) missing operator surface
  (component path expected, or
  "unreachable"), (c) affected
  operational journey (existing
  or "new required"), (d)
  recommended milestone
  disposition. Followed by per-
  domain narrative sections
  summarizing patterns (e.g.
  "BHPH write path — 5 verbs, 0
  UI surfaces; recommended
  disposition: M21-anchor via
  §5.a scope").

### New surface — audit scripts

- **`backend/dealer_ai/scripts/audit_operational_surface.py`**
  (or split into two focused
  scripts per §5.b combined-
  methodology posture). Walks
  service-verb modules + DRF
  viewsets + URL configs; cross-
  references against frontend
  API-call surface
  (`frontend/src/**/*.{ts,tsx}`
  `useMutation` / `useQuery` /
  `axios.*` / `fetch` call
  sites). Emits input for the
  M21 audit artifact. Not
  runtime code — scripts are
  operator-invoked during the
  M21.1 increment.

### Consumed but not modified

- **All shipped M1–M20 service
  verbs and DRF endpoints.** M21
  UI attaches to them. No
  backend modifications.
- **All shipped frontend routes.**
  M21 adds no routes; every new
  UI attaches to an existing
  page (`BhphCollectorDashboard`,
  `SalesManagerDashboard`, lead
  detail modal). Frontend
  operator routes stay at **20**.
- **All shipped M1–M20 tenancy
  carriers, permission classes,
  and migrations.** No
  modifications. Zero-drift
  streak extends **twenty →
  twenty-one** consecutive
  milestones.
- **M20 acceptance framework +
  CI job.** M21 consumes the
  framework; no framework
  modifications. New per-journey
  seed delta commands follow the
  M20 §5.d convention; extended
  journeys keep their existing
  file paths (BHPH,
  sales_manager).

## 3. What's NOT in this milestone (deferrals)

Every deferral recorded with a
clear re-entry path. **Ten M21-
specific + eleven universal = 21
deferrals.**

**M21-specific deferrals:**

1. **Generic UX polish.** Explicit
   non-scope per Candidate O's
   governing contract. Every M21
   surface maps to a backend
   capability + a missing form /
   button / action; "the current
   UI could look nicer" work
   defers to Candidate P
   (onboarding UX polish) as a
   future milestone candidate.
2. **New backend service verbs
   or endpoints.** Explicit non-
   scope. If a proposed scope
   item requires a new verb or
   endpoint, it belongs in a
   domain milestone (accounting
   under Candidate A, F&I
   chargeback under Candidate C,
   etc.), not in M21.
3. **Component-level refactoring
   for its own sake.** Non-scope
   per Rule 4 (scope discipline).
   Refactoring incidental to
   attaching a new form to an
   existing panel is
   in-scope; refactoring the
   existing panel to be
   "cleaner" is not.
4. **Full dashboard testid
   coverage.** §5.g Option B —
   testid additions land only
   where M21's new / extended
   journeys need them.
   Comprehensive `data-testid`
   pass across all M11/M12/M17
   dashboard surfaces remains
   Candidate G's future
   milestone shape.
5. **Accounting stream advances.**
   Explicit deferral. Candidate
   A remains elevated for M22
   consideration per the M20
   retrospective §9 standing
   question. M21's audit will
   catalogue any accounting-
   surface UI gaps (e.g.
   snapshot reopen, JE reversal
   through UI) and disposition
   them explicitly; M21 does not
   ship those UIs.
6. **Migration to `vite preview`
   in CI.** Carries forward from
   M20.5 §0.a. CI stays on
   `vite dev`; re-entry gated on
   someone reproducing the auth-
   bootstrap timeout under
   preview mode with a fix at
   the preview-server level.
7. **Cross-browser CI matrix.**
   Carries forward from M20.
   Chromium-only in CI; Firefox
   + WebKit remain locally
   available via
   `--project=firefox` /
   `--project=webkit`. Re-entry
   gated on observed browser-
   specific regression evidence.
8. **npm audit vulnerability
   remediation.** Carries
   forward from M20.5 §0.a. The
   coverage-v8 downgrade
   introduced 4 vulns (3
   moderate, 1 high) not
   remediated at M20 close.
   Re-entry via a dedicated
   dependency-hygiene task or
   folded into a future vitest-
   upgrade milestone.
9. **CI artifact upload
   verification via intentional
   failure.** Carries forward
   from M20.5 §0.a. Locally
   verified at M20.5 open; not
   yet exercised in a real CI
   failure. Recommendation:
   opportunistically verify on
   the first real M21+ journey
   regression, or add a
   controlled intentional-
   failure step to a future
   increment.
10. **Systematic audit refresh
    schedule.** The M21.1 audit
    is a snapshot. As M22+
    milestones ship new backend
    surfaces, the audit will
    drift. Formal refresh cadence
    (e.g. every OSC milestone
    open, or every quarter)
    defers to a future milestone
    that adopts OSC as a
    repeating shape.

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

M21 introduces zero new backend
migrations, zero new tenancy
carriers, zero new permission
classes, zero new endpoints. The
existing `>=` counting tests all
stay satisfied.

- **Backend test baseline.** M21
  is expected to grow the backend
  baseline modestly through new
  seed delta command tests
  (idempotency + tenant scoping),
  matching the M20 pattern.
  Baseline **4,755** at M21.0
  open; target ~**4,770–4,790**
  at M21 close depending on the
  number of new / extended
  journeys and their delta
  commands.
- **Frontend Vitest baseline.**
  M21 will grow Vitest coverage
  as new components ship —
  primarily unit tests for the
  new forms (validation, submit
  handler, error path) and
  component tests for the new
  buttons + queue tables.
  Baseline **153** at M21.0
  open; target ~**165–180** at
  M21 close depending on final
  scope selection.
- **Acceptance suite.** M21
  extends existing journeys
  (BHPH, sales_manager) and
  conditionally adds one new
  journey (follow-up cadence).
  Journey count grows from
  **6 → 6 or 7** by M21 close
  depending on §5.h Increment 4
  outcome. Pilot-critical
  subset (2 journeys at M20
  close) may grow to 3 if the
  BHPH journey is elevated to
  pilot-critical after re-
  expansion; §5.h Increment 5
  planning-time decision.
- **Migrations.** Unchanged
  through M21 close at
  `0001`–`0048`.
- **Tenancy carriers.**
  Unchanged at **52**.
- **Permission classes.**
  Unchanged at **7 actual**.
  Zero-drift streak extends
  **twenty → twenty-one**
  consecutive milestones
  (M10 → M21).
- **DRF admin surface.**
  Unchanged at **113**. New M21
  UI attaches to existing
  endpoints; no endpoints
  added.
- **Frontend operator
  routes.** Unchanged at
  **20**. New M21 components
  attach to existing pages; no
  routes added.
- **Celery-beat task
  families.** Unchanged at
  **10**.

## 5. Load-bearing decisions

Eight decisions. **All eight
confirmed as-recommended at
SESSION_166 M21.0 open.** Streak
extends to **87 planning-time as-
recommended M5.1 → M21.0** (twelve
consecutive milestones now).

### 5.a `[RESOLVED at SESSION_166 open]` — Milestone target selection

**Question.** Which candidate from
the M20 skeleton (T, U, A, D, C,
P, L, M, B, G, O) defines M21
scope?

**Decision.** **Candidate O —
Operational Surface Completion.**
User named at SESSION_166 M21.0
open. Milestone name:
**"Operational Surface Completion."**
Two anchor implementations pre-
committed at planning-time: BHPH
write-side UI (subsumes Candidate
B) + be-back write-side UI.
Conditional third anchor: follow-
up cadence queue UI. Systematic
audit as Increment 1 drives
remaining scope selection.
Candidate A, P, G, D, C, T, U, L,
M all deferred with re-entry paths
preserved per discovery rule.

**Rationale.** (1) Evidence-driven,
not slot-driven — Candidate A's
elevation was procedural (three
milestones diverging from the M18
§8 designation); Candidate O's
elevation is substantive (M20 audit
produced a concrete gap map).
(2) Consumes M20 substrate directly
— M20's operational contract is only
load-bearing if it changes what
ships next; O uses M20's gap-map
output as scope input. (3) Unblocks
Candidate A for M22 with tighter
scope — M21's audit will surface
which accounting UI gaps are real
operational pain vs. nice-to-haves.
(4) Bounded by construction —
scope selects from a finite audited
pool with the "must map to shipped
backend + missing UI" filter
excluding P territory. (5) Streak-
neutral — zero new tenancy
carriers, zero new permission
classes; zero-drift streak extends
20 → 21. (6) Fully unblocked; no
external signal preconditions
required.

### 5.b `[RESOLVED at SESSION_166 open]` — Audit methodology

**Question.** How does the M21.1
systematic audit identify backend-
only capabilities?

- **Option A** — Service-verb
  enumeration only. Walk every
  service module, cross-reference
  to frontend `useMutation` /
  `axios.*` / `fetch` call sites.
- **Option B** — DRF endpoint
  enumeration only. Walk every
  viewset action + URL config,
  cross-reference to frontend
  API-call surface.
- **Option C** — Combined: both A
  and B, cross-referenced against
  frontend consumption.

**Decision. Option C — combined
methodology** confirmed as-
recommended.

**Rationale.** (1) Belt-and-
suspenders: service-verb walk
catches capabilities that exist
as verbs without endpoint exposure
(rare but real — some internal
verbs power multiple endpoints or
none); DRF walk catches endpoints
that exist but have no frontend
consumer (the M12 write endpoints
were exactly this shape). (2)
Cross-referenced against frontend
consumption prevents false
positives (an endpoint may be
consumed via a non-standard call
path). (3) Cost is low — the two
walks are programmatic scripts,
not manual review. (4) The audit
artifact schema tolerates both
input sources; per-row provenance
gets recorded as (service verb
path, endpoint path) so future
audits can regenerate consistently.
(5) Single-source methodology
(Options A or B alone) risks
missing the exact class of gap
M20's authoring surfaced.

### 5.c `[RESOLVED at SESSION_166 open]` — Audit artifact format

**Question.** How is the M21.1
audit output documented?

- **Option A** — Single markdown
  audit artifact at
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
  One canonical table + per-
  domain narrative sections.
- **Option B** — Structured
  YAML / JSON manifest committed
  to the repo. Machine-parseable;
  no narrative.
- **Option C** — Extension of
  `docs/CAPABILITY_MATRIX.md`
  with a "surfaceable via UI"
  column across every existing
  matrix row.

**Decision. Option A — single
markdown audit artifact**
confirmed as-recommended.

**Rationale.** (1) Matches the
governing-contract requirement:
per-row documentation of (backend
capability, missing operator
surface, affected operational
journey, recommended milestone
disposition). Markdown table
directly satisfies this schema.
(2) Human-readable + review-
friendly — audit artifacts get
reviewed by Chris and by any
future contributor scoping an
OSC-shaped milestone. Machine-
parseable YAML (Option B) is
harder to review and adds no
downstream consumer today. (3)
CAPABILITY_MATRIX extension
(Option C) mixes two concerns —
the matrix documents what
capabilities exist; the audit
documents whether they're
surfaced through UI. Different
lifecycles (matrix grows with
domain milestones; audit
regenerates with OSC milestones).
Per DOC_GOVERNANCE.md §2 (prefer
updating authoritative documents)
the audit is a distinct
authoritative document, not a
matrix column. (4) Location
`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
keeps it discoverable alongside
planning + retrospective docs.
(5) Per-domain narrative sections
capture patterns (e.g. "BHPH
write path — 5 verbs, 0 UI
surfaces") that pure tables lose.

### 5.d `[RESOLVED at SESSION_166 open]` — Scope selection mechanism (post-audit)

**Question.** How is the audit
converted to M21.2–M21.4
implementation scope?

- **Option A** — User picks
  directly from the audit
  artifact at M21.2 open. No
  intermediate recommendation.
- **Option B** — Recommendation +
  confirm-as-recommended posture.
  Assistant recommends scope
  after the M21.1 audit lands
  with rationale per candidate;
  user confirms or redirects.
- **Option C** — Framework-driven
  predefined criteria (must have
  operator pain evidence; must
  not exceed X story points;
  must not extend > 2 domains).
  Mechanical scope selection.

**Decision. Option B —
recommendation + confirm-as-
recommended** confirmed as-
recommended.

**Rationale.** (1) Matches the
established planning-time posture
that produced the M10–M20 streak
(86 as-recommended). Consistency
matters — abrupt shift to a
different mechanism at M21 risks
introducing scope-selection noise
just when the milestone shape is
new. (2) Two anchor
implementations (BHPH + be-back)
are pre-committed at §5.a; the
selection mechanism governs the
conditional third anchor (follow-
up cadence) and any audit-
surfaced additions. Bounded
decision surface. (3) Framework-
driven criteria (Option C) are
attractive but require judgment
about "operator pain evidence"
that isn't yet formalized;
premature to lock. (4)
Recommendation timing: assistant
proposes scope + rationale +
increment sequencing update
after M21.1 audit closes; user
confirms or redirects before
M21.2 opens. Same posture as
§5.b–§5.h at open.

### 5.e `[RESOLVED at SESSION_166 open]` — Journey-extension contract

**Question.** How does each M21
UI-shipping increment tie to a
Playwright journey?

- **Option A** — Extend existing
  journeys only. BHPH extends
  `bhph/collections_workflow.spec.ts`;
  be-back extends
  `sales_manager/daily_startup.spec.ts`.
  No new journey files.
- **Option B** — New journey per
  new operational workflow. BHPH
  writes get a new
  `bhph/collections_write.spec.ts`;
  be-back gets a new
  `sales_manager/be_back_triage.spec.ts`.
  Existing journeys stay narrowly
  read-side.
- **Option C** — Mixed: extend
  where workflow shape matches;
  new where distinct. Per-
  workflow decision at each
  implementation increment's
  open.

**Decision. Option C — mixed
extend / new by workflow shape**
confirmed as-recommended.

**Rationale.** (1) BHPH write
path naturally extends the
existing `collections_workflow`
journey — it was originally
scoped that way at M20.4 before
being narrowed. Re-expansion
keeps the operator-workflow
coherent (a single collector's
daily-book review flows read →
write in the same journey).
(2) Be-back triage may extend
the sales-manager daily-startup
journey (workflow context: same
persona, same time-of-day
posture) or may warrant a new
journey if the triage flow is
distinct enough that bundling
creates test-name confusion.
Decision surfaces at M21.3 open.
(3) Follow-up cadence, if it
lands at M21.4, similarly needs
a per-workflow decision — extend
the sales-manager journey (if
cadence review is part of daily
startup) or introduce a new
cadence-specific journey (if
cadence work happens at a
separate time-of-day). (4)
Extending existing journeys is
preferred where the workflow
shape matches because it
preserves the M20 principle of
"if this journey passes, the
employee can perform the
workflow." Splitting a single
operator workflow across two
journeys splits the assertion
context. (5) New journey where
the workflow shape is distinct
avoids monster journey files
that mix concerns.

### 5.f `[RESOLVED at SESSION_166 open]` — Definition of Done amendment adoption

**Question.** Adopt the M21
planning skeleton Input 4
proposal — bind every future
customer-facing milestone to
journey-addition or -update, or
explicit documentation of why no
journey change is required?

- **Option A** — Adopt without
  exception. Every M21+
  customer-facing increment
  must ship a journey addition
  or update.
- **Option B** — Adopt with
  documented exception path.
  Milestones that genuinely
  don't need a new journey
  record the reason in §3 of
  their planning memo. Preserves
  the norm without creating
  bureaucracy.
- **Option C** — Defer to M22 or
  later. Treat M21 as a proof-
  of-concept for the DoD
  extension; formal contract
  lands at M22.
- **Option D** — Reject. Keep
  journey addition / update as
  an implicit norm.

**Decision. Option B — adopt with
documented exception path**
confirmed as-recommended (per
explicit user instruction at
SESSION_166 M21.0 open).

**Rationale.** (1) Codifies the
norm that the M20 substrate
depends on. Without a binding
DoD contract, journeys silently
atrophy as new operator-facing
surfaces ship without acceptance
coverage — the exact failure
mode M20 was designed to
prevent. (2) The exception path
prevents bureaucracy for
legitimate infrastructure-only
milestones (e.g. a migration-
only milestone, a
dependency-hygiene milestone, a
build-tool upgrade). The
requirement to document the
exception in §3 preserves review
discipline — an exception with
no rationale surfaces as a gap
during planning-memo review.
(3) Rejects Option A because
some future milestones will
genuinely be non-customer-
facing; forcing a journey
addition would create
performative work. (4) Rejects
Option C because M20 already
proved the substrate; deferring
formalization to M22 leaves the
window open for one milestone
of implicit-norm compliance
that may or may not hold. (5)
Rejects Option D because
implicit norms decay under
pressure; explicit contracts
survive. (6) Amendment applies
from M21 forward. M21 itself
trivially satisfies via the
§5.e journey-extension
contract.

**Amendment text (for
IMPLEMENTATION_ROADMAP + future
planning memos):** *Every
customer-facing milestone must
either (a) add or update at
least one Playwright operational
journey covering the shipped
operator surface, or (b)
explicitly document in §3 of the
planning memo why no journey
change is required. Infrastructure-
only milestones with no
customer-facing surface changes
satisfy via (b). Non-adherence
is a planning-memo review
finding.*

### 5.g `[RESOLVED at SESSION_166 open]` — Testid hardening posture

**Question.** How does M21
relate to Candidate G (dashboard
testid hardening)?

- **Option A** — Formal bundle.
  Candidate G's full-coverage
  testid pass across DealerOverview,
  DealerAdmin's SalesPipeline +
  Recent Leads, LeadsPage, and
  the assignment / detail
  surfaces lands as M21 sub-
  scope.
- **Option B** — Opportunistic.
  Add `data-testid` attributes
  only where new / extended M21
  journeys need them for stable
  selectors. Full-coverage pass
  remains Candidate G territory
  for a future milestone.
- **Option C** — Defer entirely.
  M21 uses existing selectors +
  role-based lookups exclusively;
  Candidate G stays fully
  future.

**Decision. Option B —
opportunistic** confirmed as-
recommended.

**Rationale.** (1) Preserves
Rule 4 (scope discipline). Full-
coverage testid pass is a
comprehensive tooling task that
doesn't map to the governing
contract (no backend capability +
missing UI); belongs in
Candidate G's own milestone
shape, not bundled into an OSC
milestone. (2) Opportunistic
adds close the exact gaps M21's
journeys need without expanding
obligation. Where a new form
lands, a `data-testid` on the
submit button + on the form
container is trivial to author
inline. (3) Option A risks
scope creep — full-coverage
testids require walking every
component surface, which
duplicates the audit-shape
effort M21.1 does for backend
capabilities. Two audits in one
milestone violates scope
discipline. (4) Option C over-
corrects — role-based
selectors are viable for many
patterns but occasionally
brittle (multiple buttons with
similar labels, dynamic copy).
Opportunistic testids at the
new-form-attachment points
preserve journey stability
without ceremony.

### 5.h `[RESOLVED at SESSION_166 open]` — Increment sequencing + completion contract

**Question.** How are M21
increments sequenced, and what
does "M21 shipped" mean?

- **Option A** — Three increments:
  M21.1 audit + M21.2 all
  implementations combined +
  M21.3 close. Front-loaded.
- **Option B** — Evidence-sized
  four-to-six increments. M21.1
  audit → scope lock → M21.2
  BHPH → M21.3 be-back → M21.4
  conditional (cadence /
  audit-surfaced additions) →
  M21.5 close.
- **Option C** — Fixed six
  increments matching the M20
  shape regardless of audit
  findings.

**Decision. Option B — evidence-
sized four-to-six increments**
confirmed as-recommended.

**Rationale.** (1) Preserves
Rule 4 (small complete
increments) while respecting
the audit-driven nature of the
milestone. Option A risks a
monster M21.2 debug marathon
(three UIs shipped concurrently
across two workspaces). (2)
Preserves scope discipline —
M21.4 lands only if the audit
confirms fit; skipping M21.4 if
the audit surfaces no
additional scope is a
legitimate outcome. (3) Two
anchor increments (M21.2, M21.3)
are pre-committed at §5.a
because their scope is already
known from M20 evidence; no
audit finding will remove them.
(4) M21.5 close matches the
M20.5 pattern — CI hardening,
retrospective, capability matrix
update, M22 skeleton,
coordinated close-out commit.
(5) Increment sizing is bounded
by the two anchors + one
conditional + close; five is
the expected shape at M21.0
open; four (drop M21.4) if the
audit confirms no additional
scope; six (split BHPH or
be-back for size reasons) only
if the audit surfaces an
implementation reason.

**Milestone completion
contract:**
- **BHPH write-side UI ships**
  with the four verbs (record
  PtP, mark broken / kept, log
  contact, initiate repossession,
  mark recovered) attached to
  the M12.7 collector dashboard
  surface; `bhph/collections_workflow.spec.ts`
  extends to cover the write
  side end-to-end.
- **Be-back write-side UI
  ships** with the three verbs
  (record be-back, mark
  returned, mark no-show)
  attached to the M11 sales-
  manager dashboard or lead-
  detail modal;
  `sales_manager/daily_startup.spec.ts`
  extends (or a new be-back-
  triage journey is added) to
  cover the write side.
- **Follow-up cadence queue UI**
  either ships in M21.4 (if
  audit confirms fit) or is
  explicitly deferred to
  Candidate O2 in the M21.5
  retrospective §9.
- **M21 audit artifact
  committed** and current as of
  M21.5 close, with per-row
  disposition for every
  identified gap.
- **DoD amendment adopted** and
  referenced from
  `IMPLEMENTATION_ROADMAP.md`.
- **All M21 shipped journeys +
  extensions pass on `main`
  CI**; pilot-critical subset
  passes on PR.
- **Retrospective §9** records
  the standing question for M22
  target selection with
  Candidate A (accounting) still
  elevated and any newly-
  surfaced candidates from the
  M21 audit's `defer-domain-
  milestone` rows.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 + §9 (M20 unblocks +
   standing M21 question — this
   milestone's origin)
6. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (M20 substrate that M21
   consumes; framework + journey
   patterns M21 extends)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 (accounting slot
   designation — preserved as
   elevated M22 recommendation
   per §5.a rationale (3))
8. `docs/CAPABILITY_MATRIX.md`
   §7u (M20 shipped surface —
   the substrate M21's audit
   walks)

## 7. Sequencing

**Four to six increments,
evidence-sized.** Confirmed as-
recommended per §0.a §5.h.
Combine increments if
implementation evidence shows a
smaller complete shape; do not
split merely to match this
draft.

### Increment 0 (M21.0) — Planning refinement + target selection

**Scope.** SESSION_166 (this
session). §5.a Candidate O
confirmed at open; §5.b–§5.h
drafted with recommendations,
all eight confirmed as-
recommended. Full memo expansion
(this document). DoD amendment
formalized as §5.f.

**Deliverable.**
- This planning memo, expanded
  from the M20.5 skeleton.
- §0.a change log with all
  eight §5 decisions resolved.
- Session handoff at
  `docs/handoffs/SESSION_166_m21_inc0_planning.md`.
- `00-START-NEXT-SESSION.md`
  overwritten with M21.1
  priority.

**Backend baseline unchanged:**
4,755 pass, 1 skipped, 0 fail.
Frontend Vitest unchanged: 153
pass. Acceptance suite
unchanged: 6 journeys.

### Increment 1 (M21.1) — Systematic operational-surface audit + M21 scope lock

**Scope.** SESSION_167. Land
the audit tooling + the audit
artifact + user-confirmed scope
selection for M21.2 onward.

**Deliverable.**
- `backend/dealer_ai/scripts/audit_operational_surface.py`
  (or split into two focused
  scripts) implementing §5.b
  Option C combined
  methodology.
- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  populated with per-row
  dispositions per §5.c
  Option A schema.
- **Assistant recommendation +
  user confirmation** on scope
  for M21.2 onward per §5.d
  Option B. Recommendation
  includes: BHPH + be-back
  anchor confirmation, follow-
  up cadence disposition (fit
  or defer), any additional
  audit-surfaced items with
  `M21-anchor` or
  `M21-conditional`
  disposition.
- Scope lock recorded as §0.a
  M21.1 amendment in this
  planning memo (frontmatter
  `sources` may extend; §7
  increment shape may adjust).
- Session handoff at
  `docs/handoffs/SESSION_167_m21_inc1_audit.md`.

**Backend baseline target at
M21.1 close:** 4,755 (unchanged
— audit scripts are operator-
invoked, not tested; no seed
delta commands land in this
increment). Frontend Vitest:
153 (unchanged). Acceptance
suite: 6 journeys (unchanged).

### Increment 2 (M21.2) — BHPH write-side UI + journey extension

**Scope.** SESSION_168. First
anchor implementation.

**Deliverable.**
- Frontend components:
  - `RecordPromiseToPayForm`
    attached to Promises card.
  - `MarkBrokenPromiseButton` +
    `MarkKeptPromiseButton`
    row-level actions on
    Promises card.
  - `LogCollectionContactForm`
    attached to Contacts card.
  - `InitiateRepossessionForm`
    attached to Repossessions
    card.
  - `MarkRecoveredButton` row-
    level action on
    Repossessions card.
- Vitest coverage for the new
  forms (submit + validation +
  error paths) and buttons
  (click handler + confirm
  dialog if applicable).
- Extended
  `dealer_ai/management/commands/seed_journey_bhph_collections_workflow.py`
  covering the write-side setup
  (a fresh PtP-ready note in
  a state where the collector
  can immediately record) +
  backend tests (idempotency +
  tenant scoping).
- Extended
  `acceptance/journeys/bhph/collections_workflow.spec.ts`
  covering: record PtP → mark
  broken → log contact →
  initiate repossession, with
  business-outcome assertions
  at each step.
- Opportunistic testids per
  §5.g on the new form / button
  surfaces where needed.

**Backend baseline target at
M21.2 close:** ~4,760–4,770.
Frontend Vitest: ~163–170.
Acceptance suite: 6 journeys
(BHPH re-expanded, others
unchanged).

### Increment 3 (M21.3) — Be-back write-side UI + journey extension or addition

**Scope.** SESSION_169. Second
anchor implementation.

**Deliverable.**
- Frontend components:
  - `RecordBeBackForm` (attach
    location — dashboard vs.
    lead detail modal —
    finalized at M21.3 open
    based on M21.1 audit
    finding about where the
    workflow originates).
  - `MarkBeBackReturnedButton`
    + `MarkBeBackNoShowButton`
    row-level actions on the
    be-back queue view.
  - `BeBackQueueTable` if the
    sales manager dashboard
    lacks a dedicated queue
    surface (M21.1 audit to
    confirm).
- Vitest coverage for the new
  form + buttons + queue table.
- Extended
  `dealer_ai/management/commands/seed_journey_sales_manager_daily_startup.py`
  (or new
  `seed_journey_sales_manager_be_back_triage.py`)
  + backend tests.
- Extended
  `acceptance/journeys/sales_manager/daily_startup.spec.ts`
  or new
  `acceptance/journeys/sales_manager/be_back_triage.spec.ts`
  per §5.e Option C decision
  made at M21.3 open.
- Opportunistic testids per
  §5.g.

**Backend baseline target at
M21.3 close:** ~4,770–4,780.
Frontend Vitest: ~170–180.
Acceptance suite: 6 or 7
journeys.

### Increment 4 (M21.4) — Conditional follow-up cadence UI + audit-surfaced additions

**Scope.** SESSION_170.
**Conditional** — lands only
if the M21.1 audit's scope
selection at §5.d includes
cadence and / or additional
audit-surfaced items. If
scope-selection excludes M21.4
scope, this increment is
skipped and M21.5 becomes
SESSION_170.

**Deliverable (if applicable).**
- Frontend components for
  follow-up cadence queue +
  action surfaces per M21.1
  audit findings.
- Any additional audit-
  surfaced UI items marked
  `M21-anchor` or
  `M21-conditional` at scope
  lock.
- Corresponding Vitest
  coverage.
- Extended or new seed delta
  commands + backend tests.
- Extended or new Playwright
  journey per §5.e Option C.
- Opportunistic testids per
  §5.g.

**Backend baseline target at
M21.4 close (if applicable):**
~4,780–4,790. Frontend Vitest:
~180–195. Acceptance suite: 7
or 8 journeys depending on
scope + journey-shape
decision.

### Increment 5 (M21.5) — CI hardening + retrospective + close-out

**Scope.** SESSION_170 or
SESSION_171 depending on M21.4
outcome. Full-suite CI
validation + close-out
documentation + capability
matrix update + retrospective
+ M22 skeleton.

**Deliverable.**
- CI job validation on all
  extended / new journeys.
  Verify pilot-critical PR
  subset stays within ~90s
  target; full suite stays
  within ~5–8 min target.
- `docs/CAPABILITY_MATRIX.md`
  §7v — M21 shipped surface:
  new frontend components +
  new seed delta commands +
  extended journeys + audit
  artifact + DoD amendment.
- `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
  covering lessons learned,
  what shipped, deferrals
  reviewed, §9 standing
  question for M22 (is M22
  the return-to-accounting
  milestone? — Candidate A
  preserved as elevated re-
  entry per discovery rule;
  any new candidates surfaced
  from M21 audit dispositions
  documented).
- `docs/roadmap/MILESTONE_22_PLANNING.md`
  skeleton (status: draft)
  with candidate list refreshed
  from M21 retrospective §9 +
  remaining M20 / M19
  candidates.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M21 shipped
  status + DoD amendment
  formalized in the roadmap
  contract section.
- Session handoff at
  `docs/handoffs/SESSION_170_m21_inc5_close.md`
  or
  `SESSION_171_m21_inc5_close.md`
  depending on M21.4 outcome.
- `00-START-NEXT-SESSION.md`
  refreshed for M22.0.
- Coordinated close-out commit
  + push per M18.6 / M19.6 /
  M20.5 pattern.

**Backend baseline target at
M21.5 close:** ~4,770–4,790
depending on scope. Frontend
Vitest: ~170–195. Acceptance
suite: 6, 7, or 8 journeys.
Migrations unchanged
`0001`–`0048`. Tenancy carriers
unchanged at 52. Permission
classes unchanged at 7 (zero-
drift streak twenty →
**twenty-one** consecutive
milestones). Frontend operator
routes unchanged at 20.
