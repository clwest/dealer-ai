---
title: "Milestone 21 — (target selection deferred to M21.0)"
status: draft
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_165 (skeleton + M20-close planning inputs)
milestone: 21
milestone_name: "(pending — locked at M21.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_19_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_20_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md §7u
---

# Milestone 21 — Planning skeleton (target TBD at M21.0)

Skeleton drafted at M20.5 close-out
(SESSION_165). This memo intentionally
does NOT lock a target; SESSION_166
(M21.0) presents the candidate list,
resolves §5.a with the user, and expands
the skeleton into a full active planning
memo per the M18 / M19 / M20 precedent.

## Standing rule

Per the M18 / M19 / M20 planning pattern:
at M21.0 open the target selection
proceeds by presenting the full candidate
list, recommending one option with
rationale grounded in operator pain
resolved by that candidate, and awaiting
user confirmation. Once selected,
§5.b–§5.h load-bearing planning decisions
get drafted with recommendations for
confirm-as-recommended at M21.0 open
(streak extension expected: 86 → 87
planning-time as-recommended M5.1 → M21.0
across twelve consecutive milestones).

## Planning inputs from M20 close

The M20 acceptance-testing milestone
surfaced concrete inputs that must
inform M21 target selection + scope.
This section carries them forward as
first-class planning material. Nothing
here locks §5.a — but every
recommendation at M21.0 open must be
weighed against these inputs.

### Input 1 — Journey coverage map

The six M20 acceptance journeys have
different depths of operational
coverage. Categorized:

**Fully green — writes exercised
through the shipped UI:**

- `pilot/onboarding.spec.ts` — end-to-
  end conversion (create pilot →
  advance all seven checklist steps →
  `is_ready=true`). The M19 pilot
  admin surface is the reference
  standard for shipped write UI.
- `sales_manager/daily_startup.spec.ts`
  — lead assignment via the
  LeadDetailModal + AssignmentDropdown
  (M11 Phase 4 write path).
- `recon/workflow.spec.ts` — recon
  decision recording (`must_do` tier
  click; M4.7 write path).
- `office/accounting_workflow.spec.ts`
  — trial-balance snapshot freeze +
  drill-in (M17.1 write path).

**Intentionally read-only — journey by
design does not exercise a mutation:**

- `owner/morning_review.spec.ts` —
  dashboard scan + drill into pipeline
  detail. Read-only by owner
  workflow-shape (a morning review is
  observation, not action).

**Stopped because operator UI is
missing — journey scope narrowed at
authoring time:**

- `bhph/collections_workflow.spec.ts`
  — narrowed to portfolio + note-
  detail READ side at M20.4 §0.a
  decision 1. The four planned write
  operations (record PtP, mark
  broken, log contact, initiate
  repossession) have no shipped
  frontend UI as of M12.7. Backend
  endpoints exist; collectors can't
  reach them through the product.

**Backend capabilities unreachable
through normal UI — identified so
far, likely non-exhaustive:**

- **BHPH write path** — `record_promise`,
  `mark_kept`, `mark_broken`,
  `record_contact`, `record_repossession`,
  `mark_recovered`. All exist as M12
  service verbs + DRF endpoints; none
  is wired to a UI form.
- **Be-back write path** — flagged
  during M20.2 sales manager journey
  authoring (M20.2 handoff notes the
  BHPH-adjacent gap). `record_be_back`,
  `mark_returned`, `mark_no_show`
  exist as M11.6 service verbs; no
  frontend surface. Sales-manager
  journey scope was narrowed to
  lead-assignment-only as a result.
- **Follow-up cadence queue** — the
  M20.2 planning called for "check
  the follow-up cadence queue" in
  the sales manager journey; no
  dedicated frontend queue surface
  shipped. Assignment was covered
  instead.
- **Full write-side audit for other
  surfaces (recon vendor comms,
  accounting reversal, pilot
  outbound-enable, etc.) has NOT
  been performed.** M21.0 should
  consider commissioning a
  systematic audit as part of the
  Operational Surface Completion
  candidate below.

### Input 2 — Known acceptance gaps

Journeys where Playwright validated
only part of the intended operational
story:

- **BHPH collections journey** —
  covers the read side of the daily
  book review only. Missing:
  recording a promise-to-pay, marking
  a broken promise, logging a
  collection contact, initiating
  repossession. Journey re-expands
  to full write coverage the moment
  M12.8 BHPH write-side UI ships.
- **Sales manager daily startup
  journey** — covers lead assignment
  only. Missing: be-back-due-today
  queue review, marking a be-back
  handled, follow-up cadence queue
  triage. Journey re-expands the
  moment the be-back + cadence UI
  ships.
- **Owner morning review journey**
  — intentionally read-only by
  workflow shape (not a gap per se,
  but worth naming so the coverage
  contract is honest).
- **Recon workflow journey** —
  covers first-tier decision
  recording only. Full M4.7 recon
  lifecycle (work order creation,
  vendor communication, parts
  approval, work-order completion +
  cost reconciliation) is not
  exercised. UI exists per M4.7
  ship; journey scope kept narrow.
  Re-entry path: extend
  `recon/workflow.spec.ts` in a
  future increment.
- **Office/accounting workflow
  journey** — freezes one snapshot.
  Does not exercise journal-entry
  reversal, prior-close comparison,
  or the M17.1 snapshot reopen
  flow. UI shipped for JE list +
  detail; journey scope kept
  narrow. Same re-entry path as
  recon.

### Input 3 — Framework debt surfaced by CI

The first five CI attempts on the M20
push surfaced four §0.a M20.5 CI-
cleanup amendments. Each is a real
piece of debt worth carrying forward:

- **vite preview mode deferred**
  (M20.5 CI-cleanup 3). CI currently
  uses `vite dev` in both local and
  CI per §0.a M20.5. Original M20 §5.f
  Option A design was `vite preview` in
  CI ("catches build-only regressions").
  Adding `preview.proxy` to
  `frontend/vite.config.ts` did not fix
  the auth-bootstrap timeout under
  preview. When someone reintroduces
  `vite preview` in CI, they'll need
  to reproduce the /api/* proxy issue
  (curl-test `vite preview` manually
  hitting the backend) and fix at the
  preview-server level.
- **Dependency pins changed for CI
  stability:**
  - `backend/requirements.txt`:
    `celery[redis]==5.5.3` →
    `celery==5.5.3` (M20.5 CI-cleanup
    1). Kombu's `[redis]` extra pins
    `redis<=5.2.1`, conflicting with
    the explicit `redis==6.4.0` pin.
    Runtime works — the extra is
    redundant.
  - `frontend/package.json`:
    `@vitest/coverage-v8: ^4.1.10`
    → `^3.2.7` (M20.5 CI-cleanup 2).
    coverage-v8 v4.x requires
    vitest v4.x as peer; vitest is
    pinned at v3.2.7. `npm ci` fails
    under strict peer resolution.
    Coverage tooling stays on v3
    until vitest is upgraded.
  - `npm audit` reports 4 vulns
    (3 moderate, 1 high) after the
    coverage-v8 downgrade — not
    remediated at M20.5, deferred as
    a separate concern (audit
    remediation is not a CI-unblock
    scope).
- **Browser matrix — Chromium-only
  in CI.** Firefox and WebKit are
  available locally via
  `--project=firefox` /
  `--project=webkit` (Playwright
  supports the config out of the
  box) but not wired into the
  `.github/workflows/acceptance.yml`
  matrix. Re-entry gated on
  observed browser-specific
  regression evidence.
- **Artifact upload — verified
  locally, not yet verified in CI.**
  The M20.5 intentional-failure
  test at session open confirmed
  the artifact flow end-to-end
  LOCALLY (HTML report + screenshot
  + video + error-context all land
  in expected paths on failure).
  The CI upload step
  (`actions/upload-artifact@v4`
  with `if: failure() || cancelled()`)
  has NOT been exercised in a real
  CI failure — the five failed CI
  attempts all failed pre-suite
  (dep resolution, then login
  setup timeout without downstream
  test artifacts). Recommendation:
  add a controlled intentional-
  failure verification to a future
  M21+ increment, OR simply wait
  for the first real journey
  regression to prove the CI
  upload flow end-to-end.

### Input 4 — Definition-of-done amendment (M21.0 consideration)

**Proposal.** Adopt a new milestone-
completion contract addition: every
future customer-facing milestone MUST
add or update at least one Playwright
acceptance journey before close-out.
Alongside unit tests, integration
tests, capability matrix updates, and
retrospectives — journeys become the
fifth pillar of milestone completion.

**Rationale.** The M20 substrate is
only valuable if every subsequent
milestone extends it. Left as an
implicit norm, journeys will atrophy
— silent regressions creep in as new
operator-facing surfaces ship without
acceptance coverage. The M20.4 BHPH
scope-narrow was the first concrete
proof: a shipped backend capability
(M12 write endpoints) has no
acceptance coverage because there's
no journey to add coverage to.

**Load-bearing decision surface for
M21.0.** Should the M21 planning
memo (whatever §5.a resolves to)
adopt this DoD amendment as a §5.x
decision? Options:

- **Option A** — adopt without
  exception; every customer-facing
  M21+ increment must ship a
  journey addition/update. Backend-
  only milestones (e.g. accounting
  substrate work that only surfaces
  through existing UI) trivially
  satisfy this by extending an
  existing journey.
- **Option B** — adopt with a
  documented "explicit exception"
  path: milestones that genuinely
  don't need a new journey record
  the reason in §3 of their
  planning memo. Guards against
  bureaucracy while preserving the
  norm.
- **Option C** — defer adoption
  until M22 or later; treat M21
  as a proof-of-concept for the
  DoD extension (M21 itself adds
  or updates journeys; formal DoD
  contract lands at M22).
- **Option D** — reject; keep
  journey addition/update as an
  implicit norm.

**Recommendation to raise at M21.0
open:** Option B is the balanced
choice — codifies the norm without
creating friction for legitimate
exceptions. But this is a §5.x
question, not a §5.a question;
M21.0 should surface it once §5.a
is locked.

### Input 5 — Likely M21 target

**User's leading candidate at M20.5
close: an evidence-driven Operational
Surface Completion milestone.** Not
generic UX polish. Close the highest-
value missing UI workflows found by
the M20 audit — the ones where
backend capability already exists but
dealership staff cannot operate it
through the product.

Added below as Candidate O
("Operational Surface Completion").
Explicitly umbrella-shaped: subsumes
Candidate B (M12.8 BHPH write-side
UI) and may subsume parts of
Candidate P (onboarding UX polish)
depending on scope selection at
M21.0 open.

Recommendation strength notes at
M21.0 open:

- **Elevated:** Candidate O
  (Operational Surface Completion)
  — directly addresses evidence
  from M20 audit; user-identified
  as leading candidate.
- **Elevated:** Candidate A (return
  to accounting stream) — three
  consecutive milestones diverging
  risks ossifying the divergence.
- **Gated:** Candidates T, U, L, M
  — external signal preconditions
  (tester sessions, hosted-demo
  willingness, first live pilot,
  second operator).
- **Deferred pending evidence:**
  Candidates D (LLM router), C
  (F&I chargeback) — same signals
  that led to prior deferrals
  still absent.

## Candidate list

Compiled from `MILESTONE_20_RETROSPECTIVE.md`
§8 unblocks + §9 candidate list +
carry-forwards from M19 §9. **Priority
ranking happens at M21.0 with the full
brief in hand.**

### Carry-forward candidates (from M19 §9)

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions between M20
  close and M21.0 open.
- **Candidate U** — hosted-demo
  substrate (public self-serve
  signup). Gated on willingness to
  hand demo stores to operators
  Chris doesn't already know.
- **Candidate A** — return to
  accounting stream (M18
  retrospective §8's designated
  M20 slot; M20 diverged to
  Candidate J). **Recommendation
  strength elevated at M21.0**
  because three consecutive
  milestones (M18, M19, M20)
  diverging from the accounting
  designation risks ossifying the
  divergence. Multiple accounting
  sub-candidates listed in
  `MILESTONE_18_RETROSPECTIVE.md`
  §8 (period-close comparison
  view / audit, financial-reports
  substrate (P&L + balance sheet),
  CSV/PDF export of frozen
  snapshots, auto-freeze on
  schedule, reopen/unfreeze
  workflow, M10 chargeback GL
  reversal, NSF workflow,
  category-group-aware GL
  mapping, deposit/bank
  reconciliation, BhphFee entity,
  interest-accrual detector).
- **Candidate D** — demo-aware
  LLM router / cost caps (M18.1
  §0.a decision 1 deferral).
- **Candidate C** — F&I chargeback
  substrate (M18.2 §0.a decision
  1 deferral).
- **Candidate P** — onboarding UX
  polish (prospect intake UI,
  checklist progress bar,
  terminate-flow refinements,
  pilot-list filtering/search).
- **Candidate L** — first-live-
  pilot staging dry-run (codify
  the M19.5 dry-run against a
  real staging DB with a real
  pilot dealer).
- **Candidate M** — multi-
  operator support
  (`IsPlatformOperator`
  permission class). **Breaks the
  zero-drift streak with intent.**
  Gated on a second operator
  actually being introduced.

### New at M20 close (from M20 §8 + §9 + M21 planning inputs)

- **Candidate O — Operational Surface
  Completion.** *User's leading
  candidate at M20.5 close.*
  Evidence-driven umbrella milestone
  closing the highest-value missing
  UI workflows found by the M20
  operational audit — the ones where
  backend capability already exists
  but dealership staff cannot
  operate it through the product.
  **Scope selection happens at
  M21.0 open** grounded in the
  Input 1 + Input 2 gap map:
  - **In-scope candidates** (M20-
    identified gaps with shipped
    backend + missing UI):
    - **BHPH write-side UI** (record
      PtP, mark broken / mark kept,
      log collection contact,
      initiate repossession, mark
      recovered) — subsumes
      Candidate B.
    - **Be-back write-side UI**
      (record be-back, mark
      returned, mark no-show) —
      surfaced during M20.2 sales
      manager journey authoring.
    - **Follow-up cadence queue
      UI** — surfaced during M20.2
      planning; no dedicated
      frontend queue shipped.
    - **Systematic audit of other
      backend-only capabilities**
      not yet catalogued (recon
      vendor comms, accounting
      reversal, pilot outbound-
      enable, etc.).
  - **Explicit non-scope:** generic
    UX polish or component-level
    refactoring (that's Candidate P
    territory). Every OSC scope
    item must map to a shipped
    backend capability + a missing
    UI form/button/action, not to
    "the current UI could look
    nicer".
  - **Journey-extension contract:**
    every UI shipped under OSC ships
    with a corresponding Playwright
    journey addition or extension.
    This is the concrete pilot for
    the Input 4 DoD amendment
    proposal.
- **Candidate B — M12.8 BHPH
  collections write-side UI.**
  Surfaced by M20.4 §0.a decision
  1 (BHPH scope narrowing). Would
  ship: record PtP form, mark-
  broken / mark-kept action
  buttons on Promises card, log-
  contact form on Contacts card,
  initiate-repossession form on
  Repossessions card. Once
  shipped, M20.4 journey scope
  expands to cover the write side.
  Operator pain: today the M12
  write endpoints are only usable
  via curl / Postman / Django
  shell — collectors can't do
  their work through the UI.
  **Subsumed by Candidate O if
  OSC is selected at §5.a.**
- **Candidate G — dashboard
  testid hardening.** *Renamed
  from the M20 §8 "Candidate D"
  entry per the letter-reuse
  disambiguation below.* Add
  `data-testid` patterns across
  DealerOverview, DealerAdmin's
  SalesPipeline + Recent Leads
  table, LeadsPage's lead queue
  + LeadDetailPanel,
  LeadDetailModal, and the
  AssignmentDropdown. Enables
  future Playwright journey
  extensions to write clean
  assertions instead of leaning
  on brittle text/role selectors
  + class-signature modal scoping.
  Not urgent (M20.2/M20.3
  journeys work today); becomes
  urgent as component copy
  evolves. Could bundle with
  Candidate O as supporting
  scope.

**Candidate-letter disambiguation
resolved.** Candidate D remains
"demo-aware LLM router / cost caps"
per M19 §9. The M20 §8 "dashboard
testid hardening" candidate is
renamed to Candidate G per this
skeleton. Future candidate letters
should be assigned when the
candidate is first surfaced; the
memo tracks assignments so history
stays legible.

## What M21.0 must do

At SESSION_166 (or whenever M21.0
opens):

1. **Verify CI status** on the most
   recent `main` push — confirm the
   M20 full acceptance suite still
   passes end-to-end. Address any
   regression as §0.a M21.0
   amendments before opening §5.a.
2. **Present the candidate list**
   above with a recommendation +
   rationale per candidate.
   Explicit note: reference Input 1
   + Input 2 (journey coverage +
   acceptance gaps) when scoring
   Candidate O.
3. **Recommend a target** for §5.a
   selection. Ground the
   recommendation in:
   - Operator pain resolved.
   - Dependencies on already-shipped
     substrate.
   - Deferred items with re-entry
     paths.
   - Whether the candidate blocks
     future milestones or is
     blocked by them.
   - Evidence from Inputs 1–3
     (coverage map, gaps, CI-debt).
4. **Await user confirmation** or
   redirection to a different
   candidate.
5. **Once §5.a locks**, draft §5.b–
   §5.h load-bearing planning
   decisions with recommendations
   for confirm-as-recommended at
   M21.0 open. Streak 86 → 87
   expected.
6. **Surface the Input 4 DoD
   amendment** as an explicit §5.x
   decision. Recommend Option B
   (adopt with documented exception
   path); await user confirmation.
   Whether adopted, modified,
   deferred, or rejected — the
   answer becomes part of the M21
   milestone-completion contract.
7. **Cross-reference Input 3
   framework debt** in §3
   (deferrals) of the expanded
   memo. At minimum: vite preview
   mode remains deferred; browser
   matrix remains Chromium-only in
   CI; the dependency-pin drift
   (celery, coverage-v8) is
   permanent (not a temporary
   workaround). npm audit vulns
   defer to a separate concern.
8. **Expand this skeleton** into a
   full active planning memo
   analogous to
   `MILESTONE_18_PLANNING.md` /
   `MILESTONE_19_PLANNING.md` /
   `MILESTONE_20_PLANNING.md`.
   Frontmatter `status: draft` →
   `status: active`; `milestone_name`
   populated from §5.a.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target at
  M20.5. Inputs 1–5 above inform
  the recommendation at M21.0
  open; they do not preempt it.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M20.5 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate at
  M20.5. Candidate O's specific
  in-scope items get selected at
  M21.0 with the operator-pain
  weights in hand.
- ❌ Do NOT rewrite the candidate
  list order to imply priority
  — that's the M21.0 open
  exercise. The Input 5
  "elevated / gated / deferred"
  annotations are recommendation-
  strength signals, not a locked
  ranking.
- ❌ Do NOT lock the Input 4 DoD
  amendment at M20.5 — surface
  at M21.0 §5.x with user
  confirmation.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 (M20 unblocks) + §9 (standing
   question)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (M19 candidate list — still
   valid for the seven candidates
   M20 didn't pick)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 (accounting-slot designation
   preserved as elevated M21
   recommendation)
8. `docs/CAPABILITY_MATRIX.md`
   §7u (M20 shipped surface)
