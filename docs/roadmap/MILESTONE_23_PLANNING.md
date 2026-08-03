---
title: "Milestone 23 — BHPH Origination + Payment Intake"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_174 (skeleton), SESSION_175 (expansion)
milestone: 23
milestone_name: "BHPH Origination + Payment Intake"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_22_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_22_PLANNING.md
  - docs/roadmap/MILESTONE_21_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7w
---

# Milestone 23 — BHPH Origination + Payment Intake

> **Active planning memo.** Expanded at
> SESSION_175 M23.0 open from the
> skeleton drafted at M22.4 close.
> §5.a Candidate O2 (BHPH note
> origination + payment intake sub-
> scope) confirmed at open per the
> primary operational-coverage lens
> — closes the BHPH lifecycle bookends
> that M12 (backend), M12.7 (read UI),
> M20.4 (Playwright coverage of
> collections), and M21.2 (write-side
> UI for collections) established.
> Before M23, dealership BHPH
> workflows are shippable for the
> collector persona but broken for
> the originating persona — a
> dealership cannot CREATE a BHPH
> note through the product, and a
> collector cannot record a cash
> payment against an existing note.
> Both gaps require curl or Django
> shell today.
>
> **M23 returns to the M21 Candidate
> O UI-creation shape** after M22's
> validation-shape milestone. The
> refined governing contract for
> UI-creation milestones applies:
> every M23 surface (a) maps to
> shipped backend + missing frontend,
> (b) closes a missing operator-
> facing UI, (c) adds or extends a
> Playwright operational journey,
> (d) is not generic UX polish.
>
> **M23 also carries M22's audit-
> correctness-as-supporting-
> infrastructure posture** — the
> M23.0 empirical verification
> surfaced a NEW audit false-
> positive class distinct from
> M22.1's variable-first URL
> assembly: **HTTP-verb-agnostic
> URL-prefix matching**. Row 123 of
> the audit misclassifies
> `admin-bhph-note-create` as
> `covered` via `getBhphNote` (a
> GET wrapper on the pk-suffixed
> URL that shares the same path
> prefix as the POST create
> endpoint but hits a different
> verb + path shape). M23.1 ships
> the targeted fix per §5.d under
> a ~2-hour budget guard, matching
> M22.1's precedent.
>
> **M23 introduces zero new backend
> service verbs, zero new DRF
> endpoints, zero new frontend
> routes, zero new tenancy
> carriers, zero new migrations,
> zero new permission classes.** The
> zero-drift permission-class
> streak extends **twenty-two →
> twenty-three** consecutive
> milestones (M10 → M23). Backend
> baseline growth expected only
> from new seed-fixture tests +
> possibly audit-script correctness
> tests + component Vitest tests.
>
> **Eight load-bearing decisions** —
> §5.a target selection + §5.b
> component attachment plan + §5.c
> journey folder + shape + §5.d
> audit-tool false-positive side-
> fix posture + §5.e seed command
> pattern + §5.f baseline
> verification approach + §5.g
> testid hardening posture + §5.h
> increment sequencing and
> completion contract. **All eight
> confirmed as-recommended at
> SESSION_175 M23.0 open** — streak
> extends to **89 planning-time as-
> recommended M5.1 → M23.0** across
> **fourteen consecutive milestones
> now** (M10 → M23).

## Guiding question (durable, per M22 close)

**Which candidate most increases
operational coverage for a
dealership employee?**

This lens governed §5.a target
selection at M23.0. It also
governs any mid-milestone scope
addition or subtraction. Endpoint
count, implementation effort,
roadmap momentum, and continuity
with prior scope are secondary
signals used to break ties within
candidates that score comparably
on operational coverage. Applies
to every future milestone open.

## Preserve the M20–M22 operational contract (durable)

Compound guidance carried forward
through every M23 decision and
increment:

- Verify through the real
  application before locking
  scope (M22 lesson;
  operationalized as the M23.0
  empirical verification of the
  two BHPH endpoints that
  surfaced the audit false-
  positive class).
- Let evidence drive roadmap
  decisions — retrospective §9
  recommendations decay when the
  codebase changes.
- Keep milestones tightly
  bounded — evidence-sized §5.h
  Option B posture allows shape
  to shrink as well as grow.
- Extend Playwright journeys
  whenever customer-facing
  operational behavior changes
  (M21.0 §5.f DoD amendment).
- Allow completed operational
  journeys to reveal the next
  highest-value work rather than
  planning from assumptions.

## Guiding principle (Candidate O UI-creation contract, M21 shape)

M23 inherits the M21 Candidate O
governing contract (M22 refined
it for validation-shape
milestones; M23 returns to the
UI-creation shape). Every M23
shipped surface must satisfy
four conditions:

1. **Maps to an already-shipped
   backend capability** — the
   two anchor endpoints
   (`admin-bhph-note-create` +
   `admin-bhph-payment-create`)
   ship since M12; the M23
   scope closes their operator-
   facing UI gap.
2. **Closes a missing operator-
   facing UI** — verified
   empirically at M23.0 open.
   Neither endpoint has a
   consumer wrapper in
   `bhphApi.ts` today; both are
   reachable only via curl /
   Django shell.
3. **Adds or extends a
   Playwright operational
   journey** — two new sibling
   spec files under
   `acceptance/journeys/bhph/`
   per §5.c Option B.
4. **Is not generic UX polish**
   — scope items map 1:1 to a
   backend verb + a missing
   form; cosmetic friction
   discovered mid-milestone
   feeds Candidate P (deferred),
   not this milestone.

This governing contract binds
every §5 decision, every
increment scope call, every gap-
review decision. When these
conditions conflict with
feasibility mid-milestone, the
resolution posture is to defer
the scope item to a future
milestone rather than relax any
of the four conditions.

## 0. Engineering practices to preserve from M2–M22

Same posture as M22.0 except
where noted. Non-negotiable:

- **Backend-first architecture.**
  M23 ships zero new backend
  business logic. Every UI
  action goes through an
  existing service verb via an
  existing endpoint; the
  frontend + acceptance
  workspaces are the only
  workspaces whose surface
  expands (plus M23.1's
  audit-script fix).
- **Service ownership.** Every
  UI target invokes an existing
  service verb — no parallel
  write paths. If a proposed
  scope item would require a
  new service verb, it is out
  of scope for M23.
- **Tenancy discipline.** Every
  new UI form scopes writes
  through the existing tenant
  middleware. No M23 UI
  bypasses the tenancy carrier
  stack; every write asserts
  dealership context per the
  existing authenticated-cookie
  pattern.
- **Load-bearing decisions get
  user review BEFORE code.** All
  eight §5 decisions confirmed
  at SESSION_175 M23.0 open.
  Any implementation-time
  micro-decisions surface as
  §0.a amendments.
- **Additive extension over
  fork.** M23 does not modify
  existing endpoints, service
  verbs, or components in ways
  that break current operator
  use. New forms attach to
  existing pages (per M17 §6
  lesson 6 + M21.2 precedent).
  M23 adds zero frontend
  routes.
- **Zero-drift permission-class
  posture.** Every UI action
  uses the existing
  authenticated-cookie flow;
  both anchor endpoints stay
  within their shipped
  permission class
  (`IsSalesManagerOrOwnerAtActiveDealership`).
  Streak extends **twenty-two →
  twenty-three** consecutive
  milestones (M10 → M23).
- **Every M23 assertion of
  shipped-surface counts uses
  `>=`** per the M9–M22
  growth-only-list lesson.
  Journey counts stay exact-
  equality where the milestone
  shape locks a specific
  number (M23 targets 9
  journeys at close — 7
  existing + 2 new per §5.c
  Option B).
- **In-place page extension
  over new route** per M17 §6
  lesson 6 + M21.2 posture.
  M23 target pages:
  `DealerAiBhphPortfolio.tsx`
  (note origination form
  attaches to Notes card
  header, replacing the empty-
  state CTA);
  `DealerAiBhphNoteDetail.tsx`
  (payment intake form
  attaches as a new Payments
  card matching the
  Promises/Contacts/Repossessions
  pattern). No new top-level
  routes.
- **Naming discipline** per
  M17 §6 lesson 3. Component
  names reflect operator
  vocabulary
  (`RecordBhphNoteForm`,
  `RecordBhphPaymentForm`),
  not developer vocabulary
  (`CreateNoteModal`,
  `PmtForm`).
- **Journey isolation, per-
  workflow spec files, and
  business-outcome assertions**
  per M20 §5.d + §5.e and M22
  §5.c precedent. Each new
  journey extends the existing
  BHPH seed additively (per
  §5.e Option A) and asserts
  business state (a BHPH note
  is originated with expected
  principal / APR; a payment
  is recorded reducing the
  outstanding balance) — not
  DOM state.
- **Fail-loud contract** per
  M20 §0. Journey test names
  identify the operational
  workflow. Failure messages
  target the business outcome
  that failed. Screenshots +
  traces attach on failure per
  the M20 CI job configuration.
- **Journey-as-verifier per
  §5.f Option B** carries
  forward from M22.2 — no
  manual pre-verification of
  workflows before authoring
  journeys.
- **Opportunistic testids per
  §5.g Option B** carries
  forward — add `data-testid`
  only where new journeys need
  stable selectors.

### 0.a Change log — resolved decisions

**SESSION_175 M23.0 open (2026-08-03):**

- **§5.a → O2 (BHPH note
  origination + payment intake
  sub-scope) confirmed at
  open** per the operational-
  coverage primary lens. User
  named at SESSION_175 M23.0
  open. Milestone name: **"BHPH
  Origination + Payment
  Intake."** Completes the
  BHPH lifecycle bookends from
  M12 (backend), M12.7 (read
  UI), M20.4 (Playwright
  coverage), and M21.2 (write-
  side UI for collections).
  Candidates H (test-hygiene),
  A2 (next accounting
  iteration), other O2 sub-
  scopes (F&I, lead-source
  intake, deal-writeup, test-
  drive), and T/U/L/M/D/C/P/G
  all deferred with re-entry
  paths preserved per
  discovery rule.
- **Empirical verification at
  M23.0 open surfaced NEW
  audit false-positive class**
  distinct from M22.1's
  variable-first URL
  assembly: **HTTP-verb-
  agnostic URL-prefix
  matching**. Audit row 123
  (`admin-bhph-note-create`)
  claims coverage via
  `getBhphNote` — but that's
  the GET wrapper for
  `admin/bhph-notes/<pk>/`,
  not the POST create
  wrapper. Empirical verify:
  no `createBhphNote` in
  `bhphApi.ts`. Both anchor
  endpoints are genuinely
  backend-only. The false-
  positive class becomes
  M23.1 supporting-work
  scope per §5.d Option A.
- **§5.b → Option A confirmed
  as-recommended.** Note
  origination attaches to
  `DealerAiBhphPortfolio.tsx`
  (Notes card header,
  replacing the current empty-
  state message with a
  persistent CTA); payment
  intake attaches to
  `DealerAiBhphNoteDetail.tsx`
  as a new Payments card
  matching the existing
  Promises/Contacts/Repossessions
  pattern. Matches M17 §6
  lesson 6 + M21.2 in-place-
  page-extension posture. No
  new routes.
- **§5.c → Option B confirmed
  as-recommended.** New
  sibling spec files:
  `acceptance/journeys/bhph/note_origination.spec.ts`
  +
  `acceptance/journeys/bhph/payment_intake.spec.ts`.
  Origination and payment
  intake are distinct
  workflows from collections
  (different persona intent);
  matches M22.2 §5.c Option B
  precedent for distinct-
  workflow-shape journeys.
  Existing
  `bhph/collections_workflow.spec.ts`
  stays untouched.
- **§5.d → Option A confirmed
  as-recommended.** Bounded
  targeted fix in-scope per
  M22.1 §5.e precedent
  (matching HTTP verb between
  wrapper and endpoint). Ships
  as M23.1 supporting-work
  increment. ~2-hour budget
  guard. Explicit non-goal:
  AST-based audit rewrite.
  If targeted fix exceeds
  guard, ship partial + defer
  residual to a future audit-
  tooling milestone.
- **§5.e → Option A confirmed
  as-recommended.** Extend
  `seed_journey_bhph_collections_workflow`
  additively with a vehicle
  fixture (origination target
  — an available inventory
  vehicle for the operator to
  attach a BHPH note to) +
  fresh-note fixture (payment
  intake target — a note with
  non-zero balance for the
  operator to record a payment
  against). Idempotent via
  stable description /
  reference tags per M20.3 /
  M22.2 precedent. If seed
  size becomes unwieldy, split
  later.
- **§5.f → Option B confirmed
  as-recommended.** Journey-as-
  verifier carries forward
  from M22.2 §5.f Option B.
  Playwright IS the
  verification; if the shipped
  workflow doesn't complete,
  the journey fails loudly.
  Vitest doesn't substitute
  (mocks API layer).
- **§5.g → Option B confirmed
  as-recommended.** Opportunistic
  testids only per M21 §5.g +
  M22 practice. Add
  `data-testid` only where new
  M23 journeys need stable
  selectors.
- **§5.h → Option B confirmed
  as-recommended.** Evidence-
  sized four-to-five
  increments. **M23.0 planning**
  (this session) + **M23.1
  audit-tool false-positive
  fix** (supporting work) +
  **M23.2 note origination UI
  + journey** + **M23.3
  payment intake UI +
  journey** + **M23.4 close-
  out** (retrospective,
  capability matrix update,
  M24 skeleton, coordinated
  close-out commit).
  Milestone completion
  contract: every in-scope UI
  ships with a passing
  operational journey; audit
  correction closes the HTTP-
  verb-agnostic false-
  positive class; retrospective
  §9 records the BHPH
  lifecycle now operationally
  complete + M24 candidate
  evidence.
- **Streak extends to 89
  planning-time as-recommended
  M5.1 → M23.0.** Fourteen
  consecutive milestones now
  (M10 → M23).

**SESSION_176 M23.1 close (2026-08-03):**

- **Audit tooling fix shipped**
  per §5.d Option A. Three
  targeted additions to
  `backend/dealer_ai/scripts/audit_operational_surface.py`:
  (1) new `methods: frozenset[str]`
  field on `BackendEndpoint`
  dataclass with default empty
  frozenset; (2) new
  `extract_view_methods()`
  helper walks every
  `views*.py` under
  `dealer_ai/` and extracts
  `{view_function_name: frozenset(methods)}`
  from `@api_view([...])`
  decorator + `def` header
  pairs via regex; (3) new
  `_HELPER_TO_VERB` module-
  level dict mapping
  `authGetJSON` → GET,
  `authPostJSON` /
  `authPostForm` → POST,
  `authPatchJSON` → PATCH,
  `authPutJSON` → PUT,
  `authDelete` → DELETE,
  `fetch` → GET. `extract_backend_endpoints`
  extended with optional
  `view_methods` param; when
  provided, each endpoint
  carries its declared
  methods. `cross_reference`
  filters candidate consumers
  by `_HELPER_TO_VERB[c.helper]
  ∈ ep.methods` before de-
  duplication. Skips the
  verb filter when the
  endpoint's methods are
  empty (view has no
  `@api_view` decorator) —
  backwards-compat preserved
  for future / non-DRF
  patterns.
- **Artifact regenerated.**
  Coverage **110 → 108 (-2)**;
  backend-only **43 → 45
  (+2)**.
- **Two rows fully reclassified
  `covered` → `defer-candidate-
  O2`** (genuine backend-only
  revealed):
  - **Row 123
    `admin-bhph-note-create`
    (POST `admin/bhph-notes/`)**
    — was falsely claimed as
    consumed by `getBhphNote`
    (a GET wrapper for the
    pk-suffixed path). Now
    correctly `defer-candidate-
    O2`. Confirms the M23.2
    target scope.
  - **Row 139
    `admin-journal-entry-create`
    (POST `admin/accounting/journal-entries/`)**
    — was falsely claimed as
    consumed by
    `fetchJournalEntry` (a
    GET wrapper for the pk-
    suffixed path). **NEW
    genuine gap surfaced by
    audit correction** — JE
    creation UI is genuinely
    missing from the frontend.
    This is exactly the type
    of finding the M22
    retrospective §9 A2
    candidate speculated about
    but couldn't confirm.
    Recorded here as evidence
    for the M23.4
    retrospective §9 M24
    candidate discussion.
- **Five rows with wrapper-
  list pruned but staying
  `covered`** (different-verb
  wrappers dropped;
  correct-verb wrapper
  remains):
  - Row 41 `admin-vendor-
    list` (GET) — pruned
    `updateVendor` (PUT); kept
    `fetchVendors` + others.
  - Row 51 `admin-work-order-
    attach-findings` (POST) —
    pruned `detachFinding`
    (DELETE); kept
    `attachFindings`.
  - Row 62 `admin-photo-list`
    (GET) — pruned
    `deletePhoto` (DELETE);
    kept `fetchVehiclePhotos`.
  - Row 101 `admin-compliance-
    create` (POST) — pruned
    `updateCompliance`
    (PUT/PATCH); kept
    `createCompliance`.
  - Row 145 `admin-trial-
    balance-snapshot-create`
    (POST) — pruned
    `fetchTrialBalanceSnapshot`
    (GET); kept
    `freezeTrialBalance`.
- **Backend baseline unchanged
  at 4,766** — the audit
  script has no tests
  (regeneration IS the
  functional test per M22.1
  precedent). Full backend
  suite re-verified post-
  fix: zero regressions.
- **Budget guard status.**
  Fix completed in ~30-40
  minutes of active work —
  well under the ~2-hour §5.d
  guard. Same envelope as
  M22.1. No deferral to a
  future audit-tooling
  milestone required.
- **Cross-M22 pattern
  confirmation.** M22.1's
  fix targeted the variable-
  first URL assembly false-
  negative class; M23.1's fix
  targeted the HTTP-verb-
  agnostic URL-prefix
  matching false-positive
  class. Two distinct audit
  regex/parser limitation
  classes, both fixable with
  bounded targeted work
  under a ~2-hour budget
  guard. Suggests the audit
  script's regex-based
  approach has 2-3 more such
  latent limitation classes;
  each is separately
  correctable when
  operational evidence
  surfaces them. Reinforces
  the "audit correctness as
  supporting infrastructure"
  posture — compound
  improvements land at low
  per-milestone cost.

## 1. Business questions this milestone answers

Five operator-workflow questions,
each tied to the governing
contract. Every question is
answerable in principle before
M23 (backend capability exists)
but not in practice (no UI
path).

### Q1. Can a dealership originate a BHPH note on a vehicle sale through the product?

**Before M23:** No. The M12
backend ships
`admin-bhph-note-create` (POST
`admin/bhph-notes/`) since
SESSION_128 (M12). No wrapper
in `bhphApi.ts`; no component
consumes it. Origination
requires curl / Django shell.
The `DealerAiBhphPortfolio.tsx`
empty-state message literally
documents this gap by
instructing operators to `POST
/admin/bhph-notes/` on a BHPH
sale.

**After M23:** Yes. The M23.2
note origination UI closes the
gap. `RecordBhphNoteForm`
attaches to the Notes card
header in
`DealerAiBhphPortfolio.tsx`;
operators pick an available
inventory vehicle + fill note
terms (principal, APR, cadence,
first payment date) + submit.
The M23.2 Playwright journey
walks the workflow end-to-end
and asserts the resulting note
persists with the expected
shape.

### Q2. Can a BHPH collector record a cash payment against an existing note through the product?

**Before M23:** No. The M12/M16
backend ships
`admin-bhph-payment-create`
(POST `admin/bhph-notes/<pk>/payments/`)
since SESSION_128/M12 with M16
integration. No wrapper in
`bhphApi.ts`; no component
consumes it. Cash payment
recording requires curl /
Django shell. The
`DealerAiBhphNoteDetail.tsx`
Promises / Contacts /
Repossessions cards are shipped
but the natural counterpart —
Payments — is absent.

**After M23:** Yes. The M23.3
payment intake UI closes the
gap. `RecordBhphPaymentForm`
attaches as a new Payments
card matching the existing
sibling-card pattern; operators
fill amount + method + date +
memo + submit. The M23.3
Playwright journey walks the
workflow end-to-end and
asserts the resulting payment
persists with the expected
shape + reduces the
outstanding balance
appropriately.

### Q3. Is the M21 audit artifact trustworthy across ALL domains, or only for accounting (post-M22.1)?

**Before M23:** Only for
accounting endpoints. M22.1
fixed the variable-first URL
assembly false-negative class
for accounting; other domains
may still have similar
misclassifications. Additionally,
the M23.0 empirical verification
surfaced a NEW false-positive
class — HTTP-verb-agnostic
URL-prefix matching — that
affects at least one BHPH
endpoint (row 123). Anyone
scoping a future OSC-shape
milestone from the audit's
BHPH-adjacent rows would build
on partially-incorrect premises.

**After M23:** Trustworthy for
the HTTP-verb-agnostic false-
positive class post-M23.1
targeted fix (per §5.d Option
A). Row 123 reclassifies from
`covered` to `wrapper-only`
before M23.2 lands (revealing
the genuine gap); back to
`covered` after M23.2 ships the
`createBhphNote` wrapper +
component consumer. Other
false-positive/negative
patterns not yet surfaced
remain candidates for future
M22.1-shape targeted fixes.

### Q4. Is the BHPH lifecycle now operationally complete through the product?

**Before M23:** Partially.
Complete for the collector
persona (M12.7 read UI + M20.4
Playwright coverage + M21.2
write-side UI for collections
workflow). Broken for the
originating persona — a
dealership cannot CREATE a
BHPH note without curl. Also
broken for cash payment
recording — the collector
cannot record incoming cash
without curl.

**After M23:** Yes. All BHPH
lifecycle verbs — origination,
promise-to-pay recording,
promise-kept / promise-broken
transitions, collection contact
logging, cash payment
recording, repossession
initiation, repossession
mark-recovered / mark-re-
intaked — reachable through
the product with Playwright
journey coverage. Anchors the
BHPH persona (originating
finance manager +
collector) whose Playwright
coverage now spans origination
→ collection → repossession
end-to-end.

### Q5. What is the next M24 candidate, based on evidence rather than speculation?

**Before M23:** Speculative.
The M22 retrospective §9
elevated H (test-hygiene), A2
(accounting iteration), and O2
(next OSC iteration). Without
M23's journey-authoring
evidence, M24 candidate
selection would rely on
retrospective assumptions
similar to how the M21 §9
recommendation was falsified
at M22.0.

**After M23:** Evidence-based.
M23.2 + M23.3 journey
authoring surfaces any
workflow that cannot complete
through the UI as a small
in-scope fix (per §5.d
inherited posture) or as a
documented next candidate.
The M23.4 retrospective §9
records the identified next
candidate — H (test-hygiene
still elevated), A2
(accounting iteration if any
dedicated sub-audit surfaces
genuinely-missing accounting
workflows), remaining O2 sub-
scopes (F&I write substrate,
lead-source intake, deal-
writeup lifecycle, test-drive
creation), or a new candidate
surfaced during M23 authoring.

## 2. What existing primitives extend

M23 continues the "additive
extension over fork" pattern
(M11.1 / M12.3 / M13.2 / M14.1 /
M15.1 / M16.1 / M17.1 / M18.1 /
M19.1 / M20.1 / M21.2 / M22.2).
Zero new backend service verbs,
zero new DRF endpoints, zero
new tenancy carriers, zero new
migrations, zero new frontend
routes, zero new permission
classes.

### Extended — frontend workspace

- **`frontend/src/lib/bhphApi.ts`**
  — extended with two new
  typed write wrappers:
  `createBhphNote(payload)`
  hitting POST
  `admin/bhph-notes/` and
  `createBhphPayment(notePk, payload)`
  hitting POST
  `admin/bhph-notes/<pk>/payments/`.
  Payload types match the
  backend serializers verbatim.
  These wrappers close the
  M23.0 empirical-verification
  gaps.
- **`frontend/src/components/bhph/`**
  extended with two new
  components:
  - `RecordBhphNoteForm.tsx`
    — origination form with
    vehicle picker, principal
    input, APR input, cadence
    picker, first-payment-date
    picker, submit + error
    handling.
  - `RecordBhphPaymentForm.tsx`
    — payment intake form with
    amount input, method
    picker (cash / check /
    money order / etc), date
    picker, memo textarea,
    submit + error handling.
    Attached inside a new
    Payments card matching the
    existing Promises /
    Contacts / Repossessions
    sibling pattern.
- **`frontend/src/pages/DealerAiBhphPortfolio.tsx`**
  — Notes card extended with
  a persistent "Add note" CTA
  in the header (replacing the
  current documentation-of-
  gap empty-state text).
  Opens a modal containing
  `RecordBhphNoteForm`.
  Optimistic list refresh on
  submit success.
- **`frontend/src/pages/DealerAiBhphNoteDetail.tsx`**
  — new Payments card added
  as a sibling to
  Promises/Contacts/Repossessions,
  containing the existing
  payment list (already
  consumed via
  `listBhphPayments`) + the
  new `RecordBhphPaymentForm`.
  Optimistic list refresh on
  submit success.

### Extended — acceptance workspace

- **`acceptance/journeys/bhph/note_origination.spec.ts`**
  (new). M23.2 anchor. Walks:
  land on
  `/dealer-ai-bhph-portfolio`
  → click "Add note" → fill
  origination form → submit →
  verify status message →
  verify new note appears in
  Notes card. Business-outcome
  assertion via API — a BHPH
  note exists with the
  expected shape (correct
  vehicle FK, principal, APR,
  cadence).
- **`acceptance/journeys/bhph/payment_intake.spec.ts`**
  (new). M23.3 anchor. Walks:
  land on note detail page
  for seeded note-with-balance
  fixture → click "Record
  payment" → fill amount +
  method + date → submit →
  verify status message →
  verify new payment appears
  in Payments card. Business-
  outcome assertion via API —
  the payment persists with
  the expected shape, and the
  note's outstanding balance
  decreases by the payment
  amount.
- **Extended assertion
  helpers** at
  `acceptance/support/assertions/bhph.ts`
  with two new helpers:
  `expectBhphNoteOriginated(request, vehicleId)`
  and
  `expectBhphPaymentRecorded(request, noteId, amount)`.

### Extended — backend workspace

- **`backend/dealer_ai/management/commands/seed_journey_bhph_collections_workflow.py`**
  — existing BHPH seed
  extended additively per §5.e
  Option A with:
  - **Vehicle fixture** — an
    available inventory
    vehicle (stable stock
    number tag; idempotent)
    that the M23.2 origination
    journey targets. Different
    vehicle from the note-
    detail fixture so
    origination has a fresh
    target on each run.
  - **Fresh-note-with-balance
    fixture** — a distinct
    BHPH note with non-zero
    outstanding balance (no
    payments yet) that the
    M23.3 payment-intake
    journey targets. Distinct
    from the existing
    collections-workflow note.
  - **Payment cleanup on
    re-invocation** — analogous
    to M22.2's reversal-
    cleanup: any payment
    recorded against the
    M23.3 fixture in a
    previous journey run
    gets deleted so the
    fixture stays reversible.
- **`backend/dealer_ai/tests/test_m204_seed_journey_bhph_collections_workflow.py`**
  (or the equivalent existing
  seed test module) extended
  with test cases covering
  the new fixtures'
  idempotency + tenant
  scoping + payment cleanup
  behavior.
- **`backend/dealer_ai/scripts/audit_operational_surface.py`**
  — existing (M21.1)
  audit script. Corrected per
  §5.d Option A to discriminate
  HTTP verb between wrapper
  calls and endpoint patterns
  before claiming coverage.
  Explicit scope: fix the
  HTTP-verb-agnostic URL-
  prefix matching false-
  positive class. Explicit
  non-scope: AST rewrite.
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`**
  — regenerated at M23.1
  close (both endpoints
  reclassify to
  `wrapper-only` / stay
  backend-only until the
  M23.2/M23.3 wrappers ship);
  regenerated again at M23.4
  close (both reclassify to
  `covered`).

### Consumed but not modified

- **All shipped M1–M22
  service verbs and DRF
  endpoints.** M23 UI attaches
  to them. No backend
  modifications.
- **All shipped frontend
  routes.** M23 adds no
  routes; every new UI
  attaches to an existing
  page. Frontend operator
  routes stay at **20**.
- **All shipped M1–M22
  tenancy carriers,
  permission classes, and
  migrations.** No
  modifications. Zero-drift
  streak extends **twenty-two
  → twenty-three** consecutive
  milestones.
- **M20 acceptance framework
  + M22 CI job.** M23
  consumes the framework;
  no framework modifications.
  New journey files follow
  the M20/M21/M22 spec-file
  convention.

## 3. What's NOT in this milestone (deferrals)

Every deferral recorded with
a clear re-entry path.
**Twelve M23-specific +
eleven universal = 23
deferrals.**

**DoD compliance (per M21.0
§5.f Option B amendment
formalized in
IMPLEMENTATION_ROADMAP at
M21.5):** M23 satisfies the
customer-facing milestone
journey-addition requirement
**by construction**. M23.2
ships
`bhph/note_origination.spec.ts`
and M23.3 ships
`bhph/payment_intake.spec.ts`
— both new Playwright
operational journeys directly
addressing shipped operator
surface. The audit-tooling
correction increment (M23.1)
is supporting work and does
not itself require a journey
change. The close-out
increment (M23.4) references
the two new journeys as the
DoD-satisfying output.

**M23-specific deferrals:**

1. **Sale-time origination
   trigger** — attaching
   `RecordBhphNoteForm` to
   `VehicleSalePage.tsx`
   (§5.b Option B) so the
   note is originated at the
   moment a sale is marked
   BHPH. Deferred to operator-
   use evidence — the M23.2
   portfolio-based CTA
   attachment ships first;
   sale-time trigger revisited
   when operator usage
   demonstrates the sale-time
   flow is more natural.
2. **F&I write substrate**
   (16 endpoints) — largest
   remaining OSC scope.
   Warrants dedicated F&I
   milestone shape rather
   than OSC bite. Deferred
   to M24 or later
   consideration.
3. **Lead-source-specific
   intake forms** (walk-in /
   phone / referral / webhook
   — 4 endpoints). Deferred
   to future OSC iteration.
4. **Deal-writeup lifecycle**
   (3 endpoints). Deferred
   to future OSC iteration.
5. **Test-drive creation**
   (2 endpoints). Deferred
   to future OSC iteration.
6. **Additional accounting
   workflows** — as-of picker
   interaction journey, cost-
   posting failures rendering
   journey, JE list navigation
   journey (Candidate A2 from
   M22 §9). Deferred to
   dedicated accounting-
   completeness milestone.
7. **Test-hygiene remediation**
   (Candidate H from M22
   §9) — extend three
   affected seeds (freeze
   snapshot, lead assignment,
   recon decision) with
   cleanup analogous to
   M22.2's reversal-cleanup.
   Deferred as future work;
   would improve suite re-
   runnability but doesn't
   add employee workflow
   coverage.
8. **Full AST-based audit
   rewrite** — explicit non-
   scope per §5.d Option A.
   Targeted regex fix only.
9. **Non-BHPH audit false-
   positive/negative sweep**
   — the M23.1 fix
   generalizes to other
   domains with HTTP-verb-
   agnostic URL-prefix
   matching. Deferred to
   future audit-tooling
   milestone.
10. **Payment method
    validation richness** —
    the M12/M16 backend
    accepts a discrete list
    of payment methods
    (cash / check / money
    order / ACH / card).
    M23.3 UI uses the
    shipped enum unchanged;
    validation beyond the
    backend's existing
    enforcement is not
    in-scope.
11. **BHPH note contract
    PDF generation** — real-
    world BHPH origination
    typically produces a
    printable contract for
    signature. Explicit non-
    scope for M23; contract-
    generation is a separate
    domain warranting its
    own milestone shape if
    prioritized.
12. **Migration to `vite
    preview` in CI,
    cross-browser CI matrix,
    npm audit remediation,
    CI artifact upload
    verification, systematic
    audit refresh schedule**
    — all carry forward per
    M21 §3(6)–(10) and M22
    §3(7)–(11).

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

M23 introduces zero new backend
migrations, zero new tenancy
carriers, zero new permission
classes, zero new endpoints,
zero new frontend routes. All
existing `>=` counting tests
stay satisfied.

- **Backend test baseline.**
  M23 is expected to grow the
  backend baseline modestly
  through new seed fixture
  tests (idempotency + tenant
  scoping + payment cleanup)
  plus possibly one audit-
  script correctness test.
  Baseline **4,766** at M23.0
  open; target **~4,772–
  4,780** at M23 close
  depending on final scope
  selection.
- **Frontend Vitest baseline.**
  M23 will grow Vitest
  coverage as two new
  components ship (form
  validation, submit handler,
  error paths, vehicle picker
  interaction for origination,
  method picker interaction
  for payment intake).
  Baseline **180** at M23.0
  open; target **~195–210**
  at M23 close.
- **Acceptance suite.** M23
  adds two new sibling
  journeys per §5.c Option B.
  Journey count grows from
  **7 → 9** by M23 close.
  Pilot-critical subset stays
  as-is unless BHPH
  origination or payment
  intake is judged pilot-
  critical at each authoring
  increment's open.
- **Migrations.** Unchanged
  through M23 close at
  `0001`–`0048`.
- **Tenancy carriers.**
  Unchanged at **52**.
- **Permission classes.**
  Unchanged at **7 actual**.
  Zero-drift streak extends
  **twenty-two → twenty-
  three** consecutive
  milestones (M10 → M23).
- **DRF admin surface.**
  Unchanged at **113**.
- **Frontend operator
  routes.** Unchanged at
  **20**.
- **Celery-beat task
  families.** Unchanged at
  **10**.

## 5. Load-bearing decisions

Eight decisions. **All eight
confirmed as-recommended at
SESSION_175 M23.0 open.**
Streak extends to **89
planning-time as-recommended
M5.1 → M23.0** (fourteen
consecutive milestones now).

### 5.a `[RESOLVED at SESSION_175 open]` — Milestone target selection

**Question.** Which candidate
from the M23 skeleton
(H / A2 / O2 subtypes /
T / U / L / M / D / C / P / G)
defines M23 scope?

**Decision.** **O2 — BHPH note
origination + payment intake
sub-scope.** User named at
SESSION_175 M23.0 open per the
primary operational-coverage
lens. Milestone name: **"BHPH
Origination + Payment
Intake."** Completes the BHPH
lifecycle bookends from M12
backend + M12.7 read UI +
M20.4 Playwright + M21.2 write-
side UI for collections.
Candidates H, A2, other O2 sub-
scopes, and T/U/L/M/D/C/P/G
all deferred with re-entry
paths preserved per discovery
rule.

**Rationale.** (1) Highest
per-item operational-coverage
delta at smallest scope — two
endpoints; each resolves a
real employee workflow that
currently requires curl.
(2) Completes the BHPH
lifecycle story — M12 backend
+ M12.7 read + M20.4 journey
+ M21.2 write-side existed;
origination + payment intake
are the missing bookends.
(3) Compounds forward — once
BHPH is end-to-end operational,
future BHPH work becomes
validation/extension rather
than gap-filling. (4) Governing
contract fit is clean (M21
Candidate O UI-creation
contract). (5) Streak-neutral
— zero new permission classes;
zero-drift streak extends 22
→ 23. (6) Empirical
verification at M23.0 open
surfaced NEW audit false-
positive class (HTTP-verb-
agnostic URL-prefix matching)
that becomes bounded M23.1
supporting-work scope per
§5.d.

### 5.b `[RESOLVED at SESSION_175 open]` — Component attachment plan

**Question.** Where do the two
new forms attach?

- **Option A** — Note
  origination attaches to
  `DealerAiBhphPortfolio.tsx`
  (Notes card header CTA);
  payment intake attaches to
  `DealerAiBhphNoteDetail.tsx`
  (new Payments card
  matching sibling pattern).
- **Option B** — Note
  origination attaches to
  `VehicleSalePage.tsx`
  (sale-time trigger); payment
  intake same as A.
- **Option C** — Dedicated
  routes for both.

**Decision. Option A —
portfolio CTA + note-detail
Payments card** confirmed
as-recommended.

**Rationale.** (1) Matches
M17 §6 lesson 6 + M21.2 in-
place-page-extension posture
— no new routes. (2) The
portfolio page already
communicates the origination
gap in its empty state
(`DealerAiBhphPortfolio.tsx:193`
literally documents the
required curl); converting
that documentation-of-gap
into an actionable CTA is a
natural fit and provides
immediate operator value.
(3) The payment intake
attachment (note detail page
with new Payments card
matching Promises/Contacts/
Repossessions sibling
pattern) matches operator
mental model — the payment
card lives next to the other
per-note action cards.
(4) Sale-time origination
trigger (Option B) is a
follow-up worth revisiting
after operator use — too
speculative at M23.0 without
evidence. Recorded as §3
deferral 1. (5) Dedicated
routes (Option C) add
navigation cost without
justification when in-place
extension works.

### 5.c `[RESOLVED at SESSION_175 open]` — Journey folder + shape

**Question.** Extend existing
`bhph/collections_workflow.spec.ts`
or add new sibling spec files?

- **Option A** — Extend the
  existing spec file with
  origination + payment steps.
- **Option B** — New sibling
  spec files:
  `bhph/note_origination.spec.ts`
  +
  `bhph/payment_intake.spec.ts`.
- **Option C** — One new
  consolidated spec:
  `bhph/origination_and_payment.spec.ts`.

**Decision. Option B — two
new sibling spec files**
confirmed as-recommended.

**Rationale.** (1) Origination
is a distinct workflow from
collections (different
persona intent: finance
manager originating vs.
collector working the
portfolio). (2) Payment
intake is a distinct workflow
from origination (different
persona intent: collector
recording cash vs. finance
manager originating).
(3) Matches M22.2 §5.c Option
B precedent for distinct-
workflow-shape journeys.
(4) Two separate specs keeps
failure attribution clean —
a payment-intake regression
doesn't fail the origination
journey. (5) `collections_workflow.spec.ts`
stays untouched — trusted
output from M20.4 / M21.2.
(6) Consolidated single spec
(Option C) mixes concerns and
makes selective test running
harder.

### 5.d `[RESOLVED at SESSION_175 open]` — Audit-tool false-positive side-fix posture

**Question.** M23.0 empirical
verification surfaced NEW
audit false-positive class —
HTTP-verb-agnostic URL-prefix
matching claims coverage that
doesn't exist. Fix in-scope
or defer?

- **Option A** — Bounded
  targeted fix in-scope per
  M22.1 §5.e precedent
  (matching HTTP verb between
  wrapper and endpoint). ~2-
  hour budget guard.
- **Option B** — Defer to
  future audit-tooling
  milestone.
- **Option C** — Fix as part
  of M23.2 note-origination
  increment (fold in).

**Decision. Option A —
bounded targeted fix as M23.1
supporting-work increment**
confirmed as-recommended.

**Rationale.** (1) Matches
the durable-guidance memory
established at M22 close
("audit correctness as
supporting infrastructure —
welcome bounded audit-
correction sub-scope"). Every
accuracy gain compounds
across future scope decisions.
(2) Matches M22.1 shape —
supporting work first, anchor
work second. Discipline the
audit correction with a
budget guard so it can't
consume anchor scope.
(3) Explicit non-goal: AST-
based audit rewrite. Full
refactor belongs in a
dedicated audit-tooling
milestone.
(4) If the targeted fix
exceeds ~2 hours at M23.1
open, ship partial fix,
document residual patterns
for future audit-tooling
milestone, and proceed to
M23.2.
(5) Option B leaves M24+
candidate selection dependent
on partially-untrustworthy
audit rows for BHPH.
(6) Option C folds concerns
— the audit fix and the
anchor UI shouldn't ship in
the same commit for clean
attribution.

### 5.e `[RESOLVED at SESSION_175 open]` — Seed command pattern

**Question.** New per-journey
seed commands or extend the
existing BHPH seed?

- **Option A** — Extend
  `seed_journey_bhph_collections_workflow`
  additively with vehicle
  fixture (origination
  target) + fresh-note
  fixture (payment intake
  target) + payment cleanup.
- **Option B** — New per-
  workflow seed commands
  (`seed_journey_bhph_note_origination`
  +
  `seed_journey_bhph_payment_intake`).

**Decision. Option A —
extend existing seed
additively** confirmed as-
recommended.

**Rationale.** (1) Matches
M21 Lesson 4 ("reference
existing seed shape") +
M22.2 §5.g Option A
("additive fixtures preserve
tenant context"). (2) The
existing seed already
provisions BHPH state on the
default dealership; adding
vehicle + fresh-note
fixtures is additive without
disrupting the collections
workflow the existing
journey depends on.
(3) Payment cleanup on
re-invocation mirrors
M22.2's reversal-cleanup
pattern — proven reliable
for suite re-runnability
without `--reset`.
(4) Idempotency preserved
via stable fixture tags per
existing seed pattern.
(5) Option B creates seed
sprawl — three seeds where
one suffices. (6) Splitting
reversible — if the
extended seed becomes hard
to reason about mid-
milestone, split then; do
not pre-split.

### 5.f `[RESOLVED at SESSION_175 open]` — Baseline verification approach

**Question.** Manual pre-
verification of workflows
before authoring journeys,
or journey-as-verifier?

- **Option A** — Manual
  developer pass-through of
  each shipped workflow
  before authoring journey.
- **Option B** — Journey-as-
  verifier (author the
  journey; let it be the
  verification).

**Decision. Option B —
journey-as-verifier** carries
forward from M22.2 §5.f
Option B confirmed as-
recommended.

**Rationale.** (1) M22.2
proved fast and reliable —
JE reversal journey passed
on first run without manual
pre-verification. (2) The
M23 shipping surface is
NEW UI (M22 was already-
shipped UI); expect the
journey-as-verifier posture
to surface small operator-
surface gaps via §5.d
inherited posture (small
in-scope fix vs. large
deferred as next candidate
evidence) — same policy as
M22.2 but with higher
likelihood of small fixes
since the UI is fresh.
(3) Playwright's fail-loud
contract catches any
incompleteness in the
shipped workflow as a
specific business-outcome
assertion failure — cheaper
than manual verification
and produces test artifacts
for regression detection.
(4) Vitest coverage
(component-level) does not
substitute — mocks the API
layer; only Playwright
exercises the full stack.

### 5.g `[RESOLVED at SESSION_175 open]` — Testid hardening posture

**Question.** Opportunistic
testids or full-coverage
pass?

- **Option A** — Full-
  coverage testid pass
  across the shipped BHPH
  surfaces.
- **Option B** —
  Opportunistic — add
  `data-testid` only where
  new M23 journeys need
  stable selectors.

**Decision. Option B —
opportunistic** carries
forward from M21 §5.g + M22
practice confirmed as-
recommended.

**Rationale.** (1) M22.2
shipped zero testid
additions since role-based
selectors matched shipped
markup cleanly. Expect
similar for M23 given the
new components will use
the same shadcn/Radix
primitives. (2) Full-
coverage testid pass
remains Candidate G's
future milestone shape.
(3) Opportunistic-only
preserves Rule 4 (scope
discipline). (4) Testids
land at natural insertion
points during journey
authoring — form field
inputs, submit buttons,
newly-inserted list rows.

### 5.h `[RESOLVED at SESSION_175 open]` — Increment sequencing + completion contract

**Question.** How are M23
increments sequenced, and
what does "M23 shipped"
mean?

- **Option A** — 3 fixed
  increments (M23.0 + M23.1
  both anchors + M23.2
  close).
- **Option B** — Evidence-
  sized 4-to-5 increments.
  M23.0 planning + M23.1
  audit fix (supporting) +
  M23.2 note origination
  UI + M23.3 payment intake
  UI + M23.4 close-out.
- **Option C** — 5 fixed
  increments matching M22
  shape.

**Decision. Option B —
evidence-sized four-to-
five increments** confirmed
as-recommended.

**Rationale.** (1) Matches
M21.h + M22.h Option B
posture. Fixed increment
counts distort scope
either upward (padding) or
downward (compression).
(2) Preserves Rule 4
(small complete
increments). (3) Two
anchor UIs are pre-
committed at §5.a because
their scope is known; the
audit fix is bounded per
§5.d. (4) M23.4 close
matches the M20.5 / M21.5
/ M22.4 pattern. (5)
Expected shape is 5
increments. Collapse to 4
if M23.2 + M23.3 fold
together (unlikely — each
has its own journey +
assertion helper + form
component). Skip M23.1 if
the audit fix exceeds the
~2-hour §5.d budget guard.

**Milestone completion
contract:**

- **`createBhphNote` +
  `createBhphPayment`
  wrappers ship** in
  `bhphApi.ts` with types
  matching backend
  serializers verbatim.
- **`RecordBhphNoteForm`
  attaches to
  `DealerAiBhphPortfolio.tsx`**
  as a Notes card header
  CTA + modal.
- **`RecordBhphPaymentForm`
  attaches to
  `DealerAiBhphNoteDetail.tsx`**
  as a new Payments card
  matching sibling pattern.
- **Two new Playwright
  journeys ship**:
  `bhph/note_origination.spec.ts`
  +
  `bhph/payment_intake.spec.ts`,
  both passing on `main`
  CI.
- **Seed extended** with
  vehicle fixture +
  fresh-note fixture +
  payment cleanup on
  re-invocation.
- **Audit tooling
  correction closes** the
  HTTP-verb-agnostic URL-
  prefix-matching false-
  positive class;
  regenerated artifact
  correctly reflects
  `admin-bhph-note-create`
  as `wrapper-only` before
  M23.2 (revealing the
  gap) and `covered` after.
- **Vitest coverage
  grows** for the two new
  components (~10-15
  tests).
- **All M23 shipped
  journeys pass on `main`
  CI** in the coordinated
  push at M23.4.
- **Retrospective §9**
  records the BHPH
  lifecycle now
  operationally complete +
  M24 next-candidate
  identified by journey-
  authoring evidence.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section
   landed at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
   §8 + §9 (M22 corrections
   + standing M23 question)
6. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (M22 refined governing
   contract for validation-
   shape milestones — M23
   inherits the M21 shape
   as it returns to UI-
   creation)
7. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (M21 Candidate O
   governing contract that
   M23 inherits directly)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact —
   authoritative for
   accounting post-M22.1;
   authoritative for BHPH
   post-M23.1 targeted fix)
9. `docs/CAPABILITY_MATRIX.md`
   §7w (M22 shipped
   surface)

## 7. Sequencing

**Four-to-five increments
total** — locked at
SESSION_175 M23.0 close per
§5.h Option B. Expected
minimum shape is five
(M23.0 + M23.1 + M23.2 +
M23.3 + M23.4) with M23.1
optional-skip if the audit
fix exceeds the ~2-hour
§5.d budget guard.
Combine increments if
implementation evidence
shows a smaller complete
shape; do not split merely
to match this draft.

### Increment 0 (M23.0) — Planning refinement + target selection

**Scope.** SESSION_175 (this
session). §5.a O2 (BHPH
note origination + payment
intake sub-scope) confirmed
at open per operational-
coverage lens. §5.b–§5.h
drafted with recommendations;
all seven confirmed as-
recommended. Empirical
verification of the two
target endpoints surfaced
NEW audit false-positive
class (HTTP-verb-agnostic
URL-prefix matching). Full
memo expansion (this
document). DoD compliance
verified via §3 by-
construction path.

**Deliverable.**
- This planning memo,
  expanded from the M22.4
  skeleton.
- §0.a change log with all
  eight §5 decisions
  resolved.
- Session handoff at
  `docs/handoffs/SESSION_175_m23_inc0_planning.md`.
- `00-START-NEXT-SESSION.md`
  overwritten with M23.1
  priority.

**Backend baseline
unchanged:** 4,766 pass, 1
skipped, 0 fail. Frontend
Vitest unchanged: 180 pass.
Acceptance suite
unchanged: 7 journeys.

### Increment 1 (M23.1) — Audit-tool false-positive fix + artifact refresh ✅ SHIPPED

**Scope.** SESSION_176.
Supporting work per §5.d
Option A. See §0.a M23.1
close entry for shipped
outcome + evidence-based
findings surfaced.

**Deliverable.**
- Targeted fix in
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  to discriminate HTTP verb
  between wrapper calls and
  endpoint patterns before
  claiming coverage.
- Optional backend test for
  the fix.
- Regenerated
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Row 123
  (`admin-bhph-note-create`)
  should reclassify from
  `covered` to `wrapper-only`
  or backend-only (depending
  on whether any wrapper
  hits the exact POST verb
  — expected: no such wrapper
  exists, so classification
  becomes `defer-candidate-
  O2` matching the audit's
  current handling of row
  126 `admin-bhph-payment-
  create`). Coverage count
  expected to change by a
  small delta (potentially
  -1 or so as false-
  positives get corrected).
- Session handoff at
  `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M23.2.

**Backend baseline target
at M23.1 close:** 4,766 →
**~4,767** (possible audit-
script correctness test).
Frontend Vitest: 180
(unchanged). Acceptance
suite: 7 (unchanged).

**Budget guard.** If audit
correction exceeds ~2
hours, stop, document the
remaining false-positive
patterns as a future
audit-tooling milestone,
and proceed to M23.2 with
a partial fix per §5.d
Option A.

### Increment 2 (M23.2) — Note origination UI + journey

**Scope.** SESSION_177.
First anchor UI.

**Deliverable.**
- `createBhphNote` wrapper
  in
  `frontend/src/lib/bhphApi.ts`
  hitting POST
  `admin/bhph-notes/`.
- `RecordBhphNoteForm`
  component in
  `frontend/src/components/bhph/`
  with vehicle picker,
  principal, APR, cadence,
  first-payment-date,
  submit + error handling.
- Attached to
  `DealerAiBhphPortfolio.tsx`
  Notes card as a
  persistent "Add note"
  CTA + modal.
- Vitest coverage for the
  new component (submit +
  validation + error paths
  + vehicle picker
  interaction).
- Extended
  `seed_journey_bhph_collections_workflow`
  with vehicle fixture
  (origination target) +
  backend tests
  (idempotency + tenant
  scoping).
- Extended
  `acceptance/support/assertions/bhph.ts`
  with
  `expectBhphNoteOriginated(request, vehicleId)`
  helper.
- New
  `acceptance/journeys/bhph/note_origination.spec.ts`
  walking: land on
  `/dealer-ai-bhph-portfolio`
  → click "Add note" →
  fill form → submit →
  verify status → verify
  new note appears in
  Notes card → business-
  outcome assertion via
  API.
- Concurrent §5.d small
  operator-surface gap
  fixes per M22.2
  precedent if any
  discovered (in-scope)
  with §0.a M23.2
  amendments.
- Session handoff at
  `docs/handoffs/SESSION_177_m23_inc2_note_origination.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M23.3.

**Backend baseline target
at M23.2 close:** ~4,767 →
**~4,770** (seed fixture
idempotency tests).
Frontend Vitest: 180 →
**~187-192** (new
component tests).
Acceptance suite: **7 →
8**.

### Increment 3 (M23.3) — Payment intake UI + journey

**Scope.** SESSION_178.
Second anchor UI.

**Deliverable.**
- `createBhphPayment`
  wrapper in
  `frontend/src/lib/bhphApi.ts`
  hitting POST
  `admin/bhph-notes/<pk>/payments/`.
- `RecordBhphPaymentForm`
  component in
  `frontend/src/components/bhph/`
  with amount, method
  picker, date, memo,
  submit + error handling.
- Attached to
  `DealerAiBhphNoteDetail.tsx`
  as a new Payments card
  matching Promises/Contacts/
  Repossessions sibling
  pattern.
- Vitest coverage for the
  new component.
- Extended
  `seed_journey_bhph_collections_workflow`
  with fresh-note-with-
  balance fixture +
  payment cleanup on
  re-invocation + backend
  tests.
- Extended
  `acceptance/support/assertions/bhph.ts`
  with
  `expectBhphPaymentRecorded(request, noteId, amount)`
  helper.
- New
  `acceptance/journeys/bhph/payment_intake.spec.ts`
  walking: land on note
  detail for seeded
  fresh-note fixture →
  click "Record payment"
  → fill form → submit →
  verify status → verify
  new payment appears in
  Payments card →
  business-outcome
  assertion via API
  (payment persists,
  balance decreases).
- Concurrent §5.d small
  operator-surface gap
  fixes if any surfaced.
- Session handoff at
  `docs/handoffs/SESSION_178_m23_inc3_payment_intake.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M23.4.

**Backend baseline target
at M23.3 close:** ~4,770 →
**~4,774** (seed fixture
idempotency + payment
cleanup tests). Frontend
Vitest: ~192 → **~200-205**.
Acceptance suite: **8 →
9**.

### Increment 4 (M23.4) — CI hardening + retrospective + close-out

**Scope.** SESSION_179.
Close-out.

**Deliverable.**
- CI job validation on all
  new / extended journeys.
- `docs/CAPABILITY_MATRIX.md`
  §7x — M23 shipped
  surface: audit tooling
  correction + 2 new
  wrappers + 2 new
  components + seed
  fixture extensions + 2
  new journeys + 2 new
  assertion helpers.
- `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`
  covering lessons
  learned, what shipped,
  deferrals reviewed, §8
  corrections landed, §9
  next-candidate
  identified with
  evidence.
- `docs/roadmap/MILESTONE_24_PLANNING.md`
  skeleton (status:
  draft).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M23
  shipped status.
- Session handoff at
  `docs/handoffs/SESSION_179_m23_inc4_close.md`.
- `00-START-NEXT-SESSION.md`
  refreshed for M24.0.
- Coordinated close-out
  commit + push per M18.6
  / M19.6 / M20.5 / M21.5
  / M22.4 pattern.

**Backend baseline target
at M23.4 close:** **~4,774
pass**, 1 skipped, 0 fail.
Frontend Vitest: **~200-
205 pass**. Acceptance
suite: **9 journeys / 15
passed on clean DB
(~20s)**. Migrations
unchanged `0001`–`0048`.
Tenancy carriers
unchanged at 52.
Permission classes
unchanged at 7 — zero-
drift streak twenty-two
→ **twenty-three**
consecutive milestones.
Frontend operator routes
unchanged at 20.
