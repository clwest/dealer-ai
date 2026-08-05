---
title: "Milestone 34 — Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys — Retrospective"
status: historical
type: retrospective
milestone: 34
milestone_status: shipped
generated: 2026-08-05
generated_at_session: SESSION_215 (M34.2 close + close-out fold)
milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys (three shared-DB non-idempotent journeys: sales_manager/daily_startup + recon/workflow + office/accounting_workflow)"
increments_shipped: [0, 1, 2]
close_out_fold: true
sessions: [213, 214, 215]
commits_at_close: 6
---

# Milestone 34 — Test-Hygiene Remediation — Retrospective

> Milestone 34 opened at SESSION_213 M34.0 planning under the
> durable primary operational-coverage lens, evaluated against
> the M33 §9 standing question (F&I depth-arc continuation vs
> breadth reset vs M33 §3 deferral closure). Resolved in favor
> of **"close a deferral"** — H (test-hygiene remediation) had
> waited six milestones (M27.2 → M33.2) as an unchanging
> deferral in every retrospective's §9. The primary operational-
> coverage lens argued *now, not "if evidence surfaces later"*:
> H protects the durability of the 131-endpoint coverage set
> that every future depth-arc addition builds on.
>
> M34.1 shipped the backend seed extensions + Django regression
> tests at SESSION_214: three `seed_journey_*` commands got
> `_restore_rerun_invariants(dealership)` methods restoring
> pre-flight invariants across mutate → re-seed cycles (D2 4
> invariants for sales-manager; D3 1 invariant for recon; D4
> 1 invariant for accounting under `M20_ACCEPTANCE_DB` env-
> guard); one new test file `test_seed_journey_idempotency.py`
> with 6 focused tests (D2 decomposed into 4 methods for
> debuggability — +3 vs planned +3 baseline). DoD exception
> path invocation #9.
>
> M34.2 shipped the acceptance-workspace defense + M34 close-
> out fold at SESSION_215 (this session): preserve-shape D5
> refactor of `expectSnapshotCountAtLeast` (internal assertion
> now targets envelope `total_count`; return type unchanged so
> M20.3 journey needs no consumer edits per §5.h); three specs
> tagged `@rerun-hygiene`; README extended with back-to-back
> invocation documentation; **§0.a correction** on D7 proof
> mechanism (`--repeat-each=2` doesn't re-invoke setup; back-
> to-back invocations do); local proof executed (10 passed /
> 19.9s first + 10 passed / 15.9s second). DoD exception path
> continuation, invocation #10.
>
> **First fully non-customer-facing milestone since M20.** 13
> consecutive customer-facing milestones (M21 → M33) broken
> intentionally.
>
> **Six-milestone H deferral closed.** H persisted M27.2 →
> M33.2 as an unchanging deferral entry in every retrospective's
> §9. M34 closes it.
>
> **First planning-time cycle with zero revisions** — M34.0
> §5.b lock required zero correction rounds. (z) verification-
> driven revision cycles at planning-open discipline on
> invocation 3; the discipline remains valuable even when
> tracing at open resolves ambiguity so thoroughly that no
> revisions materialize.
>
> **(cc) elevated to load-bearing-across-three-milestones**
> across M33.1 + M34.1 + M34.2 — three consecutive
> §0.a truthfulness corrections at implementation time
> revealed the same class of failure: planning-time claims
> about implementation behavior (coverage semantics; test
> count decomposition; proof-mechanism semantics) that need
> validation against actual runtime behavior, not against
> assumed tool semantics.
>
> **New candidate durable lesson `(ff)` locked at planning-
> open** per D8: *Acceptance journeys must be independently
> rerunnable against shared state; green-on-clean-DB alone is
> insufficient evidence of operational reliability.* Awaits
> first re-application to elevate.

## 1. Planned scope

Per `MILESTONE_34_PLANNING.md` §5.a locked at SESSION_213
M34.0 open under the primary operational-coverage lens with
"close a deferral" framing resolving the M33 §9 standing
question:

**Test-Hygiene Remediation — idempotent seeds + rerun-safe
acceptance journeys** for the three known shared-DB non-
idempotent journeys: `sales_manager/daily_startup`,
`recon/workflow`, `office/accounting_workflow`.

For each journey: identify exact leaked state + root cause +
smallest durable cleanup. Prefer deterministic seed/reset
over test-order dependence, broad DB wipes, or per-test
hacks. Preserve parallel + rerun safety.

Two-increment split scope-driven per §5.a surface size:

- **M34.1** — backend seed extensions (D1 contract + D2 sales-
  manager 4 invariants + D3 recon 1 invariant + D4 accounting
  scoped wipe + D6 3 Django regression tests). DoD exception
  path invocation #9.
- **M34.2** — acceptance workspace (D5 preserve-shape helper
  defense + D7 `@rerun-hygiene` tag + `acceptance/README.md`
  documentation + local repeated-run proof) + M34 close-out
  fold. DoD exception path continuation, invocation #10.

**Zero correction rounds** applied at M34.0 before §5.b lock
— first planning-open cycle with zero revisions in the M34
series. (z) verification-driven revision cycles at planning-
open invocation 3; anticipated revisions did not materialize
because the tracing pass at open was thorough enough to
resolve ambiguity inline.

## 2. What actually shipped

### M34.0 planning (SESSION_213)

Full active memo at `MILESTONE_34_PLANNING.md`. §5.a locked
as H after ten-alternative comparison + six-verification pass.
§5.b D1–D8 covering seed idempotency contract (D1), sales-
manager 4-invariant reset (D2), recon 1-line reset (D3),
accounting scoped wipe (D4), assertion helper preserve-shape
defense (D5), three Django regression tests (D6), `@rerun-
hygiene` tag Option A (D7), durable lesson (ff) verbatim
(D8). §5.c R1–R9 risks. §5.d §4.1–§4.6 verifications all
CLEAN — zero blocking findings. §5.e two-increment phasing.
§5.f DoD exception path rationale. §5.g rollback plan. §5.h
12-item explicit non-goals + all prior deferrals carried
unchanged.

Handoff at `docs/handoffs/SESSION_213_m34_inc0_planning.md`.

### M34.1 backend seed extensions + regression tests (SESSION_214)

Three seed commands under
`backend/dealer_ai/management/commands/` extended with
`_restore_rerun_invariants(dealership)` methods:

- `seed_journey_sales_manager_daily_startup.py` (D2) — added
  `BeBack` model import; new reset method with four
  invariants; wired into `handle()` before `_provision_leads`;
  `## Rerun invariants` docstring section added.
- `seed_journey_recon_workflow.py` (D3) — added
  `ReconDecision` model import; new reset method deleting
  ReconDecision on the seeded finding via tag + dealership
  scope; wired into `handle()` before
  `_provision_report_and_finding`; `## Rerun invariants`
  docstring section added.
- `seed_journey_office_accounting_workflow.py` (D4) — added
  `TrialBalanceSnapshot` model import; new reset method
  wiping TrialBalanceSnapshots on the fixture dealership;
  wired into `handle()` before `_provision_journal_entry`;
  `## Rerun invariants` + `## M20_ACCEPTANCE_DB invariant`
  docstring sections added.

**Note on `FollowUpCadence`:** D2's initial planned reset
included `paused_at=None`, but the model has no such column
— pause semantics per M11.4 are `is_active=False` only. D2
corrected inline before code landed (Pyright + Django surface
the field-does-not-exist error immediately). Documented in
SESSION_214 handoff §2.1.

NEW test file `test_seed_journey_idempotency.py` with **6
focused tests** across 3 classes (one class per seed; D2
decomposed into 4 test methods for debuggability). Each test
follows the seed → mutate (via real service verb —
`record_be_back`, `start_cadence` + `pause_cadence`,
`record_decision`, `freeze_trial_balance`) → re-seed →
assert-invariant-restored shape.

**Backend baseline: 5,015 → 5,021 pass** (+6 vs planned +3).
Audit unchanged 162 / 131 / 31 / 321. Migrations unchanged.
Permission classes unchanged.

**DoD exception path invocation #9** (M26 + M27.1 + M28.1 +
M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1) documented
in §3 of `SESSION_214_m34_inc1_seeds.md`.

**§0.a M34.1 truthfulness correction on M34.0 §5.e test
count projection** — planned 3 tests, actual 6 tests. Second
re-application of (cc); elevation to load-bearing-across-two-
milestones. Documented in SESSION_214 handoff §0.a.

### M34.2 acceptance workspace + M34 close-out fold (SESSION_215, this session)

Acceptance workspace:

- `support/assertions/accounting.ts` refactored per D5
  preserve-shape approach:
  - New sibling `fetchSnapshotEnvelope(request)` returning
    `{snapshots, totalCount}`.
  - `fetchSnapshotList(request)` reuses the envelope
    internally; return type unchanged (`TrialBalanceSnapshotSummary[]`).
  - `expectSnapshotCountAtLeast(request, minCount)` now
    asserts against `totalCount` (not `snapshots.length`);
    return type unchanged so M20.3 journey needs no consumer
    edits per §5.h.
  - `fetchAllJournalEntries` untouched (M22.2 JE-reversal
    journey unaffected).
- Three specs tagged `@rerun-hygiene` in `test.describe`
  string (the only allowed spec touch per §5.h).
- `acceptance/README.md` extended with `## Repeated-run
  hygiene proof (Milestone 34)` section documenting the
  correct back-to-back invocation mechanism + explicit note
  that `--repeat-each=2` is NOT the right mechanism.

**Repeated-run proof executed at M34.2 close:**

- First invocation:
  `cd acceptance && npx playwright test --grep "@rerun-hygiene"`
  → 10 passed in 19.9s (setup ran; seeds provisioned;
  journeys ran; DB now carries mutations).
- Second invocation: same command → 10 passed in 15.9s
  (setup ran again; seeds' `_restore_rerun_invariants`
  methods fired; invariants restored; journeys ran again
  against the freshly-restored state).

Both green — proof valid.

M34 close-out fold (this session):

- `docs/CAPABILITY_MATRIX.md` — new §7ι M34 shipped surface
  entry (per M33 §7θ precedent).
- `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` — this
  document.
- `docs/roadmap/MILESTONE_34_PLANNING.md` — status flipped
  from `active` to `historical` in frontmatter.
- `00-START-NEXT-SESSION.md` — flipped to SESSION_216 M35.0
  planning.
- `docs/handoffs/SESSION_215_m34_inc2_acceptance.md` — this
  session's handoff.

**DoD exception path invocation #10** (M34.2 acceptance-
workspace-only continuation) documented in §3 of
`SESSION_215_m34_inc2_acceptance.md`.

## 3. Deviations from plan and reason

Two §0.a corrections landed at implementation time; neither
changed the target or scope.

**§0.a M34.1 truthfulness correction on test count
projection.** M34.0 §5.e projected 5,015 → ~5,018 pass at
M34.1 close (+3 new tests). Actual: 5,015 → 5,021 pass (+6).
D2's four-invariant contract naturally decomposes into four
focused test methods for debuggability (one class-and-fail-
fast per invariant, vs one fat method that fails-fast on
first invariant). Consolidating to 3 tests would have been a
false-economy — the "one test per invariant restored"
contract is what the code needs; the "~3 tests" was a rough
projection. Second re-application of (cc) coverage-projection
truthfulness; elevation to load-bearing-across-two-milestones
per SESSION_212 M33 §5 candidate-elevation convention.
Documented in `SESSION_214_m34_inc1_seeds.md` §0.a.

**§0.a M34.2 correction on D7 proof mechanism.** M34.0 §5.b
D7 specified `npx playwright test --repeat-each=2 --grep
"@rerun-hygiene"` as the developer-side rerun-proof
invocation. Empirical verification at M34.2 open revealed
that `--repeat-each` does NOT re-invoke the setup project
between individual test repeats — it repeats the test body
only, so the seed's `_restore_rerun_invariants` methods
never fire between repetitions and the second repeat sees
mutated state and fails on pre-flight assertions. Corrected
mechanism: **back-to-back invocations** of the full grep
subset (setup runs each invocation; seeds fire; invariants
restored between runs). Documented in `acceptance/README.md`
with explicit note about the `--repeat-each` failure mode.

Third re-application of (cc) — the failure class now extends
beyond "coverage-projection truthfulness" to "planning-time
claims about testing/tooling behavior must be validated
against the actual tool, not against tool-semantics
assumptions." (cc) elevated to load-bearing-across-three-
milestones. Documented in `SESSION_215_m34_inc2_acceptance.md`
§0.a.

## 4. Deferrals from M34 (all valid for later re-entry)

Per `MILESTONE_34_PLANNING.md` §5.h and §3, unchanged at
close:

- Any product-code file change (views, services, models,
  permissions, URLs, migrations, schemas).
- Journey `.spec.ts` step-logic changes (spec files only
  received `@rerun-hygiene` tag additions to `test.describe`
  strings).
- Fixes for the other 22 acceptance journeys — scope
  strictly to the three known non-idempotent journeys.
- Shared reset helper across seed commands (per
  `feedback_duplicate_small_stable_logic.md`).
- CI DB persistence, parallelization, or repeated-run
  gating (D7 Option B upgrade path deferred to a future
  milestone if CI evolves).
- Modifications to the M32.3 Intake Iris or M33.2 Structure
  Sam fixtures (already independently rerunnable per M32
  D11 + M33 R7).
- `TrialBalanceSnapshot.fixture_tag` field (schema change
  out of scope).
- `--reset` flag semantic changes on the three seed commands
  (reset remains a manual escape hatch).
- M35 candidate list changes (operator-facing list from
  `MILESTONE_33_RETROSPECTIVE.md` §9 carried forward
  unchanged with H replaced by SHIPPED marker).
- All prior M33 §3 + M32 §3 + M31 §3 + M30 §3 + M29 §3 +
  M28 §3 + M27 §3 + M25 §4 deferrals — unchanged.

## 5. Durable design principles surfaced or reinforced

### Reinforced / re-applied

**(z) verification-driven revision cycles at planning-open**
(M32.0 origin — elevated to load-bearing-across-two-
milestones at M33 close). Third invocation at M34.0 with
**zero revision rounds observed**. The discipline is not
"revisions must happen" — it's "revisions can happen without
being treated as scope drift, and the tracing at open should
be thorough enough that the need for revisions is minimized."
M34.0 satisfied the second half of that principle
completely. (z) discipline continues to demonstrate value
even when applied under different circumstances (zero
revisions).

**(cc) coverage-projection truthfulness** (M33.1 origin —
elevated to load-bearing-across-two-milestones at M34.1
§0.a; **elevated to load-bearing-across-three-milestones at
M34.2 §0.a**). Third invocation at M34.2 extends the failure
class from "coverage-projection truthfulness" to "planning-
time claims about implementation/testing/tooling behavior
must be validated against the actual system, not against
assumed semantics." Three distinct manifestations:
- M33.1 origin: audit-coverage semantic assumption (test
  coverage vs frontend-consumer coverage).
- M34.1 second: test-count decomposition assumption (one
  test per invariant contract vs one test per seed).
- M34.2 third: proof-mechanism-tooling assumption
  (`--repeat-each` re-invokes setup vs doesn't).

Anti-pattern reminder: at every planning-open §5.e
projection AND §5.b tool-usage claim, name the specific
semantic being invoked and validate the projection/claim
against a concrete recent precedent OR an empirical test
before locking scope.

**(aa) historical-migration-immutability discipline**
(M32.1 origin; elevated to load-bearing-across-two-
milestones at M33 close). Preserved at M34 by construction
— M34 adds no migration and touches no historical migration.
Continues to be honored across the M32 → M34 lineage.

**(y) Playwright-independent-fixture pattern** (M32.3
origin; elevated to load-bearing-across-two-milestones at
M33 close). Preserved at M34 by construction — the three
M34-affected journeys' fixtures were already independent
from each other at M20 shipping; M34 makes their seeds
rerun-safe without changing the fixture-independence
posture.

**feedback_duplicate_small_stable_logic** (M28.0 origin).
Applied at M34.1 D1 discipline: three short domain-local
`_restore_rerun_invariants` methods, not one shared
abstraction. First direct re-application in a milestone
where the design temptation for premature abstraction was
obvious (three similar reset methods across three files).

### Newly surfaced (candidates for M35+ elevation)

**(ff) rerun-safety-against-shared-state as the operational-
reliability contract.** Locked verbatim at M34.0 §5.b D8 per
user directive:

> Acceptance journeys must be independently rerunnable
> against shared state; green-on-clean-DB alone is
> insufficient evidence of operational reliability.

Why: M34 exists because three journeys shipped M20.2 → M20.3
passed against fresh migrated DBs in CI but leaked state
that would trip a rerun. CI DB reset masked the class for
six milestones (M27.2 → M33.2). Durable lesson protects
future infra work from re-introducing the same class.

How to apply: at every planning-open verification (§4) for
any journey add or extension, name the concrete invariants
the journey depends on and confirm the seed restores them
across mutations the journey applies. Awaits first re-
application at M35+ to elevate.

**(gg) — candidate for consideration — planning-time
proof-mechanism validation.** Surfaced at M34.2 §0.a. The
M34.0 D7 spec named `--repeat-each=2` as the proof
mechanism without empirically verifying it does what was
assumed. Same failure class as (cc) in the abstract, but
specific to test-tooling behavior claims. Rather than
create (gg) as a separate lesson, M34.2 extends (cc) to
include this scope — see (cc) elevation note above.
Documented here for future planning-session discoverability
as an alternative if (cc) ever needs to be split.

**Non-application of (bb) non-navigational cross-role UI
when role-gating conflicts** (M32.3 origin) — not re-applied
at M34 because M34 doesn't touch UI. Awaits future
opportunity.

**Non-application of (dd) planning-time financial-language
contract with three-layer defense** (M33.0 origin) — not
re-applied at M34 because M34 doesn't touch financial-value
vocabulary. Awaits future opportunity.

**Non-application of (ee) future capability recording with
full design contract at planning time** (M33.0 origin) —
not re-applied at M34 because M34 introduces no new
adjacent-future capability. Awaits future opportunity.

## 6. Streak accounting at M34 close

- **Planning-time as-recommended streak:** **12 → 13** at
  M34.0 close. Unchanged at M34.1 + M34.2 (both pure
  implementation; §0.a corrections in both do not affect
  target-selection streak per convention). Historical run
  of 89 across M10 → M23 preserved.
- **Zero-drift permission-class streak:** **37 → 38**
  consecutive milestones (M10 → M34). M34.1 adds no
  endpoints; M34.2 adds no endpoints. Both increments
  preserve the streak by construction.
- **Substrate-compound-value continuation:** **intentionally
  paused at M34** per M33 §9 "close a deferral" resolution.
  The F&I depth arc (M32 sales-to-F&I bridge + M33 F&I
  first-loop activation) remains the primary M35
  continuation candidate if pilot evidence surfaces on NEW
  C chargeback, NEW F&I workflow-state extensions, or
  Lender Fit Recommendations.
- **DoD exception path invocations:** **8 → 9 → 10** (M26 +
  M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 +
  **M34.1 + M34.2**). Ten-invocation pattern.
- **First fully non-customer-facing milestone since M20** —
  13 consecutive customer-facing milestones (M21 → M33)
  broken intentionally at M34.
- **Six-milestone H deferral closed at M34.** H persisted
  M27.2 → M33.2 as an unchanging deferral entry in every
  retrospective's §9. Six-milestone deferral closure — one
  of the longest-running deferrals in the project (rivals
  M10.2 substrate's 19-session activation wait).
- **First M34 planning-open cycle with zero correction
  rounds.** (z) invocation 3 with zero revisions observed
  — thorough tracing at open resolved ambiguity inline.
- **(cc) elevated to load-bearing-across-three-milestones**
  across M33.1 (origin coverage-projection) + M34.1 (test
  count) + M34.2 (D7 mechanism). First lesson to reach
  three-milestone load-bearing status.
- **Two §0.a corrections within a single milestone (M34.1 +
  M34.2)** — new pattern. Both belong to the same class
  (cc); both were caught quickly and resolved inline
  without scope drift.

## 7. Baselines at M34 close

- Backend: **5,021 pass**, 1 skipped, 0 fail (174s).
- Frontend Vitest: **402 pass** across 45 files (~8s;
  unchanged from M33.2 close).
- Acceptance: **25 spec files / 32 tests / 15.9s–19.9s**
  on repeated-run proof runs.
- Migrations: **0001–0051** (unchanged since M32.1; no new
  migration in M34).
- Audit: **162 / 131 / 31 / 321** at M34.2 close (unchanged
  throughout M34).
- DRF admin surface: **122** endpoints (unchanged; M34 adds
  none).
- Frontend operator routes: **21** (unchanged).
- Service verbs enumerated: **321** (unchanged).
- Permission classes: **7 actual**, zero-drift streak **38
  consecutive** milestones (M10 → M34).
- Playwright personas: **6 actual** (unchanged).
- Playwright fixtures: **Intake Iris** (M32.3) + **Structure
  Sam** (M33.2) both still live and fully independent.
- `manage.py check` clean. `makemigrations --check` clean.
  Frontend `tsc --noEmit` clean. Acceptance `tsc --noEmit`
  clean.
- **Seed rerun-safety** (NEW at M34): three
  `seed_journey_*` commands restore pre-flight invariants
  across mutate → re-seed cycles.
- **Assertion helper defense** (NEW at M34):
  `expectSnapshotCountAtLeast` targets `total_count` (page-
  cap-safe).
- **Repeated-run proof** (NEW at M34):
  `npx playwright test --grep "@rerun-hygiene"` twice back-
  to-back — both green.

## 8. Corrections (post-close)

*(None at close-out fold. Reserved for future factual
corrections per DOC_GOVERNANCE handoff-immutability
discipline.)*

## 9. Evidence-based candidates for M35

**Elevated (highest recommendation strength for M35.0),
unchanged from M33 §9 minus H (which shipped at M34):**

- **NEW C — F&I chargeback substrate.** Third-link F&I
  depth-arc candidate; still gated on pilot evidence today
  (unchanged from M30 / M31 / M32 / M33 / M34 §9). Post-M33
  operator context is the strongest yet: F&I team can create
  DealStructures via M33.2 UI, so the natural next surface
  is post-funding chargeback exposure. If pilot evidence
  surfaces at M35.0 open, this becomes the natural next
  depth-arc link and would restart the substrate-compound-
  value continuation toward 3 links (M32 + M33 + M35 with
  M34 as the "close a deferral" intermission).
- **Lender Fit Recommendations (D10 future candidate
  elevation).** M33 delivered the first of four blockers
  (DealStructure creation operationally complete). Three
  blockers remain (LenderProgram rule verification;
  attribute retrieval; real dealer evidence on lender
  selection criteria). Elevate to top of candidate list
  once operator evidence surfaces on lender selection.
- **F&I workflow-state extensions beyond M33's two derived
  states.** Would extend the M33.2 In-progress state into
  Submitted / Approved / Contracted / Funded / Chargedback.
  Requires operator evidence on state model.
- **F&I-scoped lead-context view** (NEW at M32.3 §3;
  unchanged M33 §9 + M34 §9). Evidence-gated.
- **Cross-lead sales-manager pending-approval queue page**
  (NEW at M32.3 §3; unchanged M33 §9 + M34 §9). Evidence-
  gated.
- **Direct-create CA structuring branch** — M33 explicit
  deferral (§5.h). Requires vehicle-picker substrate.
- **Iteration UX** — creating a second DealStructure for a
  CA already In progress. M33 first-loop-only per D9.
- **PATCH on DealStructure** — activation-vocabulary-
  asymmetry preserved through M34 (create-and-read only).
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26 / M27 / M28 / M29 / M30 / M31 / M32 / M33 / M34
  deferral, unchanged — now 9-milestone deferral).
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (deferral count matches O2 — 9-milestone deferral).

**Fresh direct-operator gaps surveyed at M33 §9 and
unchanged at M34 close:**

- **Vendor detail (#43)** — wrapper-only; small polish.
- **Photo reorder (#65)** — wrapper-only; small polish +
  D&D primitive selection.
- **Broader F&I subdomain (#89–101 excl. chargeback which
  is NEW C)** — 11 uncovered endpoints post-M33 (unchanged
  at M34 close since M34 adds no endpoints); still too
  large without operator direction.

**Shipped at M34:**

- ~~**H — Test-hygiene remediation.**~~ **SHIPPED at M34.**
  Three shared-DB non-idempotent journeys now rerun-safe
  via seed idempotency contract.

**Gated (unchanged from M29 + M30 + M31 + M32 + M33 + M34
close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the M10 → M34 zero-drift streak with intent).

**Deferred pending evidence:**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M34 §3 / M33 §3 / M32 §3 / M31 §3 / M30 §3 /
M29 §3 / M28 §3 / M27 §3 / M25 §4:** all carried forward
unchanged.

**Standing question for M35:** the F&I depth arc's 2-link
run paused intentionally at M34 for the deferral-close. The
same three natural next moves apply: (a) **continue the F&I
depth arc** via NEW C chargeback substrate (third link if
pilot evidence surfaces) OR NEW F&I workflow-state
extensions (broader state model) OR Lender Fit
Recommendations (three blockers remain but M33 delivered
the first); (b) **reset to breadth** via a fresh direct-
operator gap surveyed from the 31 backend-only audit
endpoints; (c) **close another §3 deferral** — vendor detail
#43, photo reorder #65, direct-create CA structuring,
iteration UX, PATCH on DealStructure, or the 9-milestone
NEW O2 / O3 pair. Evaluate through the primary operational-
coverage lens first; secondary reframes only if evidence
surfaces.

**Meta-observation for M35 planning:** M34 demonstrated that
"close a deferral" can be a highly productive milestone
choice when the deferral has genuine compound value (H
protected the 131-endpoint coverage set's durability). If
M35 opens with no fresh operator evidence for depth-arc
continuation, closing another §3 deferral is a valid target
per the M34 precedent — not a "fallback." M34 shipped in
two increments with zero product-code changes, preserved
all streaks by construction, and elevated (cc) to load-
bearing-across-three-milestones. Deferral-close milestones
are a legitimate mode of value-shipping.
