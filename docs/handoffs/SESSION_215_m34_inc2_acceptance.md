---
title: "SESSION_215 handoff — Milestone 34 · Increment 2 (M34.2 — acceptance workspace: helper defense + @rerun-hygiene tag + repeated-run proof + M34 close-out fold)"
status: active
type: handoff
date: 2026-08-05
session: 215
milestone: 34
milestone_status: shipped
milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys"
increment: 2
increment_status: shipped
commit: pending
commit_notes: "M34.2 acceptance workspace + M34 close-out fold — local commit landing at close per M28.2 / M29.2 / M30.2 / M31.2 / M32.3 / M33.2 close-out cadence; hash backfilled via a subsequent commit; NOT pushed. Coordinated M34 push awaits explicit user confirmation."
---

# SESSION_215 — Milestone 34 · Increment 2 (M34.2 — acceptance workspace + M34 close-out fold)

## What shipped

SESSION_215 opened per the M34.1 first-thing sequence in
`00-START-NEXT-SESSION.md`. Three deliverables landed:

1. **Acceptance workspace helper defense + tag + README**
   per M34.0 §5.b D5 + D7 + §5.e M34.2:
   - **Preserve-shape D5 refactor**
     (`acceptance/support/assertions/accounting.ts`) — new
     sibling `fetchSnapshotEnvelope(request)` returning
     `{snapshots, totalCount}`; existing `fetchSnapshotList`
     unchanged in return type (reuses envelope internally);
     `expectSnapshotCountAtLeast(request, minCount)` now
     asserts against `totalCount` (not
     `snapshots.length`) — page-cap-safe. Return type of
     `expectSnapshotCountAtLeast` unchanged as
     `TrialBalanceSnapshotSummary[]` so M20.3 journey needs
     no consumer edits per §5.h. `fetchAllJournalEntries`
     untouched — M22.2 JE-reversal journey unaffected.
   - **`@rerun-hygiene` tag** added to `test.describe`
     string on the three specs
     (`sales_manager/daily_startup.spec.ts`,
     `recon/workflow.spec.ts`,
     `office/accounting_workflow.spec.ts`). Only allowed
     spec touch per §5.h.
   - **`acceptance/README.md`** extended with
     `## Repeated-run hygiene proof (Milestone 34)` section
     documenting the back-to-back invocation mechanism +
     explicit note about the `--repeat-each=2` failure
     mode (see §0.a below).
2. **M34 close-out fold** —
   `docs/CAPABILITY_MATRIX.md` new §7ι M34 shipped surface
   entry; `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` new
   document with §1–§9 sections including durable lesson
   (ff) verbatim + (cc) elevation-to-load-bearing-across-
   three-milestones + non-application notes for (bb)/(dd)/
   (ee); `MILESTONE_34_PLANNING.md` frontmatter flipped
   `active` → `historical`; SESSION_215 handoff (this
   file); `00-START-NEXT-SESSION.md` flipped to SESSION_216
   M35.0 planning.
3. **§0.a M34.2 correction on D7 proof mechanism** — the
   M34.0 planned `--repeat-each=2` doesn't re-invoke the
   setup project between repeats, so seeds' reset methods
   never fire between repetitions and the tagged journeys
   fail on pre-flight assertions in the second repeat. See
   §0.a below.

**Repeated-run proof executed at M34.2 close** (M34.0 §5.b
D7 evidence requirement):

- First invocation
  `cd acceptance && npx playwright test --grep "@rerun-hygiene"`
  → **10 passed in 19.9s** (setup ran; seeds provisioned;
  journeys ran; DB now carries mutations).
- Second invocation same command → **10 passed in 15.9s**
  (setup ran again; seeds'
  `_restore_rerun_invariants` methods fired; invariants
  restored; journeys ran again against the freshly-restored
  state).

Both green — proof valid.

**DoD exception path invocation #10** documented in §3
below (M34.2 acceptance-workspace-only continuation of the
M34.1 exception path). **M34 is the first fully non-
customer-facing milestone since M20** — 13 consecutive
customer-facing milestones (M21 → M33) broken intentionally.

**M34 SHIPPED at SESSION_215 close.** Coordinated M34 push
awaits explicit user confirmation.

## 0.a Deviation from M34.0 planning memo — D7 proof mechanism correction

**Third consecutive §0.a truthfulness correction in the M34
series** (following M34.1 §0.a test count overshoot).

- **What deviated:** M34.0 §5.b D7 specified
  `npx playwright test --repeat-each=2 --grep "@rerun-hygiene"`
  as the developer-side rerun-proof invocation. Empirical
  verification at M34.2 open produced 3 failed / 10 passed
  in a single invocation — the second repeat of each tagged
  journey failed on its pre-flight assertion (accounting:
  `expected at least 1 frozen trial-balance snapshot(s);
  got total_count=0` after a snapshot was frozen on the
  first repeat; similar failures on recon decision + sales-
  manager assignment).
- **Why:** `--repeat-each=N` repeats the test body N times
  within a single `npx playwright test` invocation, but does
  NOT re-invoke the setup project between repetitions.
  Playwright's setup project runs once per invocation as a
  dependency; individual test repetition doesn't re-fire
  dependencies. So the seeds' `_restore_rerun_invariants`
  methods (which live in the setup project via
  `login.setup.ts`) fire once at invocation start and never
  again. The second repeat sees mutated state and fails.
- **Corrected mechanism:** **Back-to-back invocations of
  the full grep subset** —
  `npx playwright test --grep "@rerun-hygiene"` twice.
  Setup runs on each invocation; seeds fire; invariants
  restore. Both invocations pass.
- **Verified empirically at M34.2 close:** first
  invocation 10 passed / 19.9s; second invocation 10 passed
  / 15.9s.
- **README updated** with explicit note about the
  `--repeat-each` failure mode so future developers don't
  hit the same trap.
- **Same class as M33.1 + M34.1 §0.a corrections** — (cc)
  coverage-projection truthfulness now extends beyond
  "coverage-projection truthfulness" to cover "planning-
  time claims about implementation/testing/tooling
  behavior must be validated against the actual system,
  not against assumed semantics." Three distinct
  manifestations:
  - M33.1 origin: audit-coverage semantic assumption (test
    coverage vs frontend-consumer coverage).
  - M34.1 second: test-count decomposition assumption (one
    test per invariant contract vs one test per seed).
  - M34.2 third: proof-mechanism-tooling assumption
    (`--repeat-each` re-invokes setup vs doesn't).
- **(cc) elevated to load-bearing-across-three-milestones**
  at M34.2 — first lesson to reach three-milestone load-
  bearing status. Elevation recorded in M34 retrospective
  §5 and CAPABILITY_MATRIX §7ι.
- **Alternative considered:** revert the M34.0 D7 spec to
  say "back-to-back invocations" retroactively. Rejected —
  the M34.0 planning memo is now historical (per DOC_
  GOVERNANCE handoff-immutability discipline for factual
  claims frozen at their commit); the correction lives in
  this §0.a and the retrospective §3 as the authoritative
  record. The planning memo's `--repeat-each` reference is
  a historical claim about what was locked at M34.0 open,
  not a live instruction.
- **Impact:** minor — no code was written to the wrong
  mechanism (the M34.2 helper refactor + tag work is
  correct regardless of proof-invocation shape). No
  behavior change. No customer-facing impact. Only
  affects developer documentation.

**Same-milestone dual §0.a pattern** (new): M34 has now
had two §0.a corrections (M34.1 test count; M34.2 proof
mechanism). Both belong to the (cc) class; both caught
quickly and resolved inline without scope drift. Suggests
"two §0.a corrections within a milestone" is a healthy
signal — the milestone's live planning memo is
sufficiently detailed that assumption-tests happen and
corrections land inline rather than accumulating as tech
debt.

## 1. Verification results at open

- **git status:** clean; `HEAD == 09d1299` (4 commits ahead
  of `origin/main` post-M34.1 close).
- **git log --oneline -5:** shows the expected M34.0 →
  M34.1 → M33.2 sequence (`09d1299` M34.1 hash-backfill;
  `9abd0ad` M34.1 backend; `a03c5eb` M34.0 hash-backfill;
  `f163e93` M34.0 planning; `3a83584` M33.2 hash-backfill).
- **`python3 manage.py test dealer_ai` (pre-M34.2):** 5,021
  pass, 1 skipped, 0 fail (174.197s at M34.1 close;
  unchanged at M34.2 open — no code touched between M34.1
  close and M34.2 open in the same conversation).
- **`cd frontend && npm test` (pre-M34.2):** 402 pass
  across 45 files (unchanged).
- **`python3 manage.py check`:** clean.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`cd acceptance && npx tsc --noEmit` (pre-M34.2 + post-
  M34.2 refactor):** clean both times.
- **`redis-cli ping`:** PONG.

State matches M34.1 close exactly.

## 2. Implementation details

### 2.1 Assertion helper preserve-shape refactor (D5) — `acceptance/support/assertions/accounting.ts`

**Design choice — preserve-shape over shape-change.** M34.0
D5 originally spec'd changing `fetchSnapshotList` return
shape to `{snapshots, totalCount}`, which would have
required updating the M20.3 journey's `snapshotsBefore` and
`snapshotsAfter` consumers. §5.h forbids modifying the
three journeys' step logic. Preserve-shape approach: keep
`fetchSnapshotList` return type as
`TrialBalanceSnapshotSummary[]`; introduce a NEW sibling
`fetchSnapshotEnvelope` that exposes `totalCount` for
`expectSnapshotCountAtLeast` to assert against internally.
Journey code unchanged.

**Files changed:**
- `acceptance/support/assertions/accounting.ts`:
  - Added `fetchSnapshotEnvelope(request)` — new async
    function returning `{snapshots: TrialBalanceSnapshotSummary[], totalCount: number}`.
  - Refactored `fetchSnapshotList(request)` — reuses
    envelope internally; return type unchanged.
  - Refactored `expectSnapshotCountAtLeast(request, minCount)` —
    asserts against `totalCount` instead of
    `snapshots.length`; return type unchanged.
  - Updated error message: `expected at least N frozen
    trial-balance snapshot(s); got total_count=X (page shows Y)`.
  - Added module comment referencing M34.0 §5.b D5 +
    preserve-shape rationale + §5.h non-goals discipline.
- `fetchAllJournalEntries` untouched — M22.2 JE-reversal
  journey continues to work verbatim.

**Tsc check:** clean.

### 2.2 `@rerun-hygiene` tag (D7)

**Files changed** — one-line edit each, appending
`@rerun-hygiene` to the `test.describe` string:

- `acceptance/journeys/sales_manager/daily_startup.spec.ts`:
  `"Sales manager daily startup — triage overnight leads +
  assign to advisor @rerun-hygiene"`.
- `acceptance/journeys/recon/workflow.spec.ts`:
  `"Recon workflow — recon manager records a decision on a
  condition finding @rerun-hygiene"`.
- `acceptance/journeys/office/accounting_workflow.spec.ts`:
  `"Office / accounting workflow — freeze a trial balance
  snapshot @rerun-hygiene"`.

Only allowed spec touch per §5.h.

### 2.3 `acceptance/README.md`

Added new section
`## Repeated-run hygiene proof (Milestone 34)` at the end
of the file (after `## Interpreting CI failures`). Contains:

- Rationale (three journeys mutate shared DB state; M34.1
  extended seeds to restore invariants).
- Correct invocation — back-to-back
  `npx playwright test --grep "@rerun-hygiene"`.
- Explicit note about the `--repeat-each=2` failure mode
  and the M34.2 §0.a correction that surfaced it.
- Reference to durable lesson (ff) in CAPABILITY_MATRIX.
- Guidance to fix the seed side, not the journey side, if
  the second run fails on a pre-flight assertion (per §5.h
  non-goals discipline).

### 2.4 Repeated-run proof execution (§7)

Executed at M34.2 close:

```
cd acceptance
npx playwright test --grep "@rerun-hygiene"
# → 10 passed in 19.9s (setup ran; seeds provisioned;
#   journeys ran; DB now carries mutations)

npx playwright test --grep "@rerun-hygiene"
# → 10 passed in 15.9s (setup ran again; seeds'
#   _restore_rerun_invariants fired; invariants restored;
#   journeys ran against the freshly-restored DB)
```

**Both invocations passed. Proof valid.**

Also verified at M34.2 open that `--repeat-each=2`
FAILS (as the M34.0 D7 spec would have used) — 10 passed +
3 failed in a single invocation on the second repeats.
This empirical failure is what triggered the §0.a
correction.

### 2.5 M34 close-out fold

- **`docs/CAPABILITY_MATRIX.md`** — new §7ι section
  inserted between §7θ (M33) and §8 (dealer branding).
  Follows the M33 §7θ template shape with: intro
  paragraph, anchor business question, four principle
  callouts (first fully non-customer-facing since M20;
  seed idempotency contract D1; preserve-shape helper
  defense D5; rerun-proof mechanism D7 + M34.2 §0.a
  correction), §0.a M34.2 correction category note,
  durable lesson (ff) mention, 4-row shipped-surface
  table (M34.0 planning; M34.1 backend; M34.2 acceptance
  + close-out; Test baseline aggregation), M34 status
  paragraph, "What is NOT shipped in M34" deferral list
  (10 items).
- **`docs/roadmap/MILESTONE_34_RETROSPECTIVE.md`** — new
  document (§1–§9). §5 records (z) invocation 3 with zero
  revisions; (cc) elevated to load-bearing-across-three-
  milestones; (aa) preserved by construction; (y)
  preserved by construction; `feedback_duplicate_small_stable_logic`
  applied at D1. Newly surfaced: (ff) rerun-safety-
  against-shared-state contract (candidate awaiting first
  re-application). Non-application notes for (bb) + (dd)
  + (ee) since M34 doesn't touch UI / financial-value
  vocabulary / adjacent-future capability.
- **`docs/roadmap/MILESTONE_34_PLANNING.md`** frontmatter
  flipped `status: active` → `status: historical`.
- **`00-START-NEXT-SESSION.md`** overwritten for
  SESSION_216 M35.0 planning per the standard cadence.
- **`docs/handoffs/SESSION_215_m34_inc2_acceptance.md`**
  — this document.

## 3. DoD exception path — invocation #10

M34.2 is acceptance-workspace-only (helper refactor + tag
+ README + close-out documentation). Zero operator-visible
behavior — no view, service, model, permission, URL,
migration, or shipped-behavior change. No new customer-
facing Playwright journey; the existing three journeys
were tagged in place for developer-side rerun-proof
invocation. **Tenth invocation of DoD exception path**
(M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 +
M33.1 + M34.1 + M34.2).

M34 as a whole is the first fully non-customer-facing
milestone since M20 — 13 consecutive customer-facing
milestones (M21 → M33) broken intentionally per M33 §9
"close a deferral" resolution.

## 4. Baselines at M34.2 close

- **Backend suite:** unchanged **5,021 pass**, 1 skipped,
  0 fail (M34.2 does not touch backend).
- **Frontend Vitest:** unchanged **402 pass** across 45
  files (M34.2 does not touch frontend).
- **Acceptance suite:** **25 spec files / 32 tests
  unchanged in count**; three specs now carry
  `@rerun-hygiene` tag; helper refactor is internal.
  Repeated-run proof timing: 19.9s + 15.9s (both under
  the 37s budget with M34.0 D7 +2s allowance).
- **`python3 manage.py check`:** clean.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`cd acceptance && npx tsc --noEmit`:** clean.
- **Audit artifact:** unchanged **162 / 131 / 31 / 321**
  (M34 adds no endpoints). Two-source agreement gate at
  M34.2 close.

## 5. Streaks at M34.2 close

- **Planning-time as-recommended streak:** **13**
  unchanged from M34.0 (§0.a M34.2 D7-mechanism
  correction does not affect target-selection streak per
  convention). Historical run of 89 across M10 → M23
  preserved.
- **Zero-drift permission-class streak:** **37 → 38**
  consecutive milestones (M10 → M34). M34 preserved the
  streak by construction (no new endpoints).
- **Substrate-compound-value continuation:**
  **intentionally paused at M34** per M33 §9 "close a
  deferral" resolution. F&I depth arc (M32 + M33 2-link)
  remains primary M35 continuation candidate.
- **DoD exception path invocations:** **9 → 10** at M34.2
  (M34.1 was #9). Ten-invocation pattern.
- **First fully non-customer-facing milestone since M20.**
  13 consecutive customer-facing milestones (M21 → M33)
  broken intentionally at M34.
- **Six-milestone H deferral CLOSED at M34.** H persisted
  M27.2 → M33.2 as an unchanging deferral entry in every
  retrospective's §9.
- **(cc) elevated to load-bearing-across-three-milestones**
  at M34.2 — first lesson to reach three-milestone load-
  bearing status. M33.1 origin + M34.1 test count + M34.2
  D7 mechanism.
- **Two §0.a corrections within M34** (M34.1 + M34.2) —
  new pattern. Both belong to (cc); both caught inline;
  both resolved without scope drift.
- **First M34-series planning cycle with zero revisions**
  at M34.0 open — (z) discipline on invocation 3 with
  zero revision rounds. Extends (z) to include "the
  tracing at open should be thorough enough that
  revisions are minimized as an outcome, not required."

## 6. Push status

**No push at SESSION_215 close.** Coordinated M34 push
awaits explicit user confirmation. All M34 work is local-
only.

Local commits at SESSION_215 close:

- SESSION_215 M34.2 acceptance refactor + tags + README
  + M34 close-out fold + this handoff land in a single
  local-only commit per standard close-out cadence; hash
  backfill via a subsequent commit.

**Expected M34 commit count at coordinated push: 6** —
`f163e93` M34.0 planning + `a03c5eb` M34.0 hash-backfill
+ `9abd0ad` M34.1 backend + `09d1299` M34.1 hash-backfill
+ this session's M34.2 + close-out fold commit + M34.2
hash-backfill follow-up.

## 7. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_216 ·
Milestone 35 · Increment 0 (M35.0 — planning refinement +
target selection)**. First-thing sequence per M28.0 /
M29.0 / M30.0 / M31.0 / M32.0 / M33.0 / M34.0 pattern:

1. **Verify starting state** (git status; backend suite
   5,021 pass; frontend Vitest 402 pass; checks;
   migrations; tsc; redis; `db.acceptance.sqlite3`
   proactive reset).
2. **If M34 pushed, monitor first M34 CI run.** If red,
   address as §0.a M35.0 amendments.
3. **Regenerate the audit artifact.** Expected 162 / 131
   / 31 / 321 unchanged.
4. **Present the M35 candidate list.** Per M34
   retrospective §9: unchanged from M33 §9 minus H (which
   shipped at M34). Standing question includes M34-
   introduced "close another §3 deferral" as a valid
   third path per M34 precedent.
5. **Recommend a target for §5.a.** Under the primary
   operational-coverage lens with F&I depth-arc-
   continuation-vs-breadth-reset-vs-close-another-
   deferral framing.
6. **Await user confirmation of §5.a.**
7. **Draft §5.b–§5.h** — anticipate revision rounds per
   (z) but do not require them (M34.0 zero-revision
   precedent).
8. **DoD compliance check on §3 draft** — customer-
   facing milestone requires Playwright journey; else
   exception path documentation (eleventh invocation if
   invoked).
9. **Expand the M35 planning memo.**
10. **Ship the M35.0 handoff** at
    `docs/handoffs/SESSION_216_m35_inc0_planning.md`. **Do
    NOT push** — M35.0 is planning only.

## 8. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_34_RETROSPECTIVE.md`** §5
   (three re-applied lessons including (cc) elevation to
   load-bearing-across-three-milestones) + §9 (M35
   candidate list origin)
6. `docs/roadmap/MILESTONE_34_PLANNING.md` (historical —
   governing contract for M34)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (unchanged at M34 — 162 / 131 / 31 / 321)
8. `docs/CAPABILITY_MATRIX.md` §7ι (M34 shipped surface)
9. `docs/handoffs/SESSION_213_m34_inc0_planning.md`
10. `docs/handoffs/SESSION_214_m34_inc1_seeds.md`
11. **This handoff**
    (`SESSION_215_m34_inc2_acceptance.md`)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — re-applied at M34.1 D1)
13. Memory record
    `feedback_playwright_as_operational_contract.md` (M34
    preserves operational contract via rerun-safety;
    strengthening invocation)
14. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at M34.0 §4.5 for cascade
    behavior)
15. Memory record `feedback_terminal_output_discipline.md`
    (governs implementation-session output shape)
