---
title: "SESSION_214 handoff — Milestone 34 · Increment 1 (M34.1 — backend seed extensions + Django regression tests)"
status: active
type: handoff
date: 2026-08-05
session: 214
milestone: 34
milestone_status: active
milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys"
increment: 1
increment_status: shipped
commit: pending
commit_notes: "M34.1 backend seed extensions + Django regression tests — local commit landing at close per M28.1 / M29.1 / M30.1 / M31.1 / M32.1 / M33.1 planning-only cadence; hash backfilled via a subsequent commit; NOT pushed. Coordinated M34 close push deferred to explicit user confirmation after M34.2 close."
---

# SESSION_214 — Milestone 34 · Increment 1 (M34.1 — backend seed extensions + Django regression tests)

## What shipped

SESSION_214 opened per the M34.0 first-thing sequence in
`00-START-NEXT-SESSION.md`. One deliverable landed:

1. **M34.1 backend substrate** per M34.0 planning memo §5.b
   D1 + D2 + D3 + D4 + D6 + §5.e M34.1:
   - **Sales-manager seed extended** (D2 —
     `seed_journey_sales_manager_daily_startup.py`): added
     `BeBack` import; new `_restore_rerun_invariants(dealership)`
     method restoring four invariants (unassign seeded leads;
     delete BeBacks on seeded leads; delete non-24hr cadences
     on seeded leads; re-activate seed 24hr cadence); wired
     into `handle()` before `_provision_leads`;
     `## Rerun invariants` section added to module docstring.
   - **Recon seed extended** (D3 —
     `seed_journey_recon_workflow.py`): added `ReconDecision`
     import; new `_restore_rerun_invariants(dealership)` method
     deleting `ReconDecision` rows on the seeded finding via
     tag + dealership scope; wired into `handle()` before
     `_provision_report_and_finding`; `## Rerun invariants`
     section added to module docstring.
   - **Accounting seed extended** (D4 —
     `seed_journey_office_accounting_workflow.py`): added
     `TrialBalanceSnapshot` import; new
     `_restore_rerun_invariants(dealership)` method wiping
     TrialBalanceSnapshots on the fixture dealership; wired
     into `handle()` before `_provision_journal_entry`;
     `## Rerun invariants` section + explicit
     `M20_ACCEPTANCE_DB` invariant note added to module
     docstring.
   - **Regression tests created** (D6 —
     `backend/dealer_ai/tests/test_seed_journey_idempotency.py`,
     new file, 285 lines, **6 tests** — see §0.a below):
     `SalesManagerDailyStartupRerunInvariantTests` × 4
     methods (one per D2 invariant); `ReconWorkflowRerunInvariantTests`
     × 1; `OfficeAccountingWorkflowRerunInvariantTests` × 1.
     Each test uses `django.core.management.call_command()` +
     direct service verbs (`record_be_back`, `start_cadence`,
     `pause_cadence`, `record_decision`, `freeze_trial_balance`)
     + fixture selectors imported from the seed commands.

**No product-code changes** (no view, service, model,
permission, URL, migration edits). Consistent with M34.0 §5.h
non-goals discipline.

**Historical migration NOT modified.** Consistent with M34.0
§5.h + M33.1 + M32.1 + M31.1 + M30.1 + M29.1 + M28.1 + M27.1
+ M26 + M25 + M24.2 + M24.1 + M23.2 discipline.

**DoD exception path invocation #9** documented in §3 below.

## 0.a Deviations from M34.0 planning memo

**One deviation — test count overshoot (3 → 6):**

- **What deviated:** M34.0 §5.b D6 planned "three tests, one
  per seed"; M34.0 §5.e M34.1 projected backend baseline
  5,015 → **~5,018** pass (+3 new tests). Actual M34.1 close:
  5,015 → **~5,021** pass (+6 new tests).
- **Why:** D2 restores four distinct invariants
  (unassign; delete be-backs; delete non-24hr cadences;
  re-activate 24hr cadence). Consolidating all four into a
  single test method would (a) fail-fast on the first
  invariant that breaks, obscuring which of the four broke;
  (b) require awkward setup that mutates all four kinds of
  state before a single `_run_sm_seed()` and single fat
  assertion block. Splitting into four focused test methods
  is more debuggable and better documents the D2 invariant
  contract for future readers.
- **Impact:** minor baseline overshoot (+3 above projection).
  Audit unchanged (162 / 131 / 31 / 321). No behavior
  change. No customer-facing impact.
- **Durable lesson (cc — coverage-projection truthfulness,
  M33.1 origin, second re-application at M34.1):** at §5.e
  test-count projections in future planning memos, explicitly
  account for cases where a single seed's invariant contract
  decomposes into N distinct assertions that are more
  debuggable as N separate tests. Elevate (cc) to load-
  bearing-across-two-milestones per SESSION_212 §5 candidate-
  lesson-elevation convention. First re-application of (cc);
  M33.1 origin invocation was the M33.0 §5.e coverage-
  projection truthfulness correction.
- **Alternative considered:** consolidate to 3 tests (one per
  seed) with multiple assertions per test to match the memo
  verbatim. Rejected because focused tests are strictly more
  informative and the memo's "~3 tests" was a rough
  projection, not a load-bearing contract. The load-bearing
  contract is "one test file, one test per invariant
  restored"; that is satisfied.

**No other deviations.** All other §5.b + §5.e items landed
as specified.

## 1. Verification results at open

- **git status:** clean; `HEAD == a03c5eb` (2 commits ahead
  of `origin/main` post-M34.0 close: `f163e93` M34.0 planning
  + `a03c5eb` M34.0 hash-backfill).
- **git log --oneline -5:** shows the expected M34.0 → M33.2
  sequence (`a03c5eb` M34.0 hash-backfill; `f163e93` M34.0
  planning; `3a83584` M33.2 hash-backfill; `622c51e` M33
  close-out fold; `1e0008f` M33.1 hash-backfill).
- **`python3 manage.py test dealer_ai` (pre-M34.1):** 5,015
  pass, 1 skipped, 0 fail (170.958s at M33.2 close;
  unchanged at M34.0 open per SESSION_213 §1).
- **`cd frontend && npm test` (pre-M34.1):** 402 pass across
  45 files (unchanged at M34.0 open).
- **`python3 manage.py check`:** clean.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`redis-cli ping`:** PONG.

State matches M34.0 close exactly — no code touched between
M34.0 planning-close and M34.1 open (same conversation).

## 2. Implementation details

### 2.1 Sales-manager seed (D2) —
`seed_journey_sales_manager_daily_startup.py`

**Docstring:** added `## Rerun invariants (M34.1 · D2)`
section naming four restored invariants explicitly (per M34.0
D1 contract).

**Import:** extended `dealer_ai.models` import block to
include `BeBack`.

**Reset method:** new `_restore_rerun_invariants(dealership)`:

```python
seeded = _existing_leads(dealership)
seeded.update(assigned_to=None)
BeBack.objects.filter(lead__in=seeded).delete()
FollowUpCadence.objects.filter(
    lead__in=seeded
).exclude(template="24hr").delete()
FollowUpCadence.objects.filter(
    lead__in=seeded, template="24hr"
).update(is_active=True)
```

**Note:** `FollowUpCadence` has no `paused_at` column (pause
semantics per M11.4 model docstring are `is_active=False`
only). D2 restores active state via single `is_active=True`
update; docstring and M34.0 planning memo D2 corrected
inline before code landed (see also §0.a — Pyright surfaced
the field-does-not-exist error immediately on first test
run).

**Wire:** call added in `handle()` between `_provision_advisor`
and `_provision_leads`.

### 2.2 Recon seed (D3) — `seed_journey_recon_workflow.py`

**Docstring:** added `## Rerun invariants (M34.1 · D3)`
section per M34.0 D1 contract.

**Import:** extended `dealer_ai.models` import block to
include `ReconDecision`.

**Reset method:** new `_restore_rerun_invariants(dealership)`:

```python
ReconDecision.objects.filter(
    finding__description__startswith=FIXTURE_FINDING_TAG,
    dealership=dealership,
).delete()
```

Tag AND dealership scoped for defense-in-depth. OneToOne
cascade behavior verified at M34.0 §4.5 — direct child
`.delete()` does not affect parent.

**Wire:** call added in `handle()` between
`_provision_vehicle` and `_provision_report_and_finding`.

### 2.3 Accounting seed (D4) —
`seed_journey_office_accounting_workflow.py`

**Docstring:** added `## Rerun invariants (M34.1 · D4)` and
`## M20_ACCEPTANCE_DB invariant (M34.1 · D4)` sections per
M34.0 D1 + D4 contracts.

**Import:** extended `dealer_ai.models` import block to
include `TrialBalanceSnapshot`.

**Reset method:** new `_restore_rerun_invariants(dealership)`:

```python
TrialBalanceSnapshot.objects.filter(dealership=dealership).delete()
```

Dealership-scoped wipe. Safety enforced by the
`M20_ACCEPTANCE_DB=1` env-guard in `login.setup.ts`
(re-documented in the module docstring).

**Wire:** call added in `handle()` between the `--reset`
branch and `_provision_journal_entry`.

### 2.4 Regression tests (D6) —
`backend/dealer_ai/tests/test_seed_journey_idempotency.py`

New file, 285 lines, 6 tests across 3 test classes:

- `SalesManagerDailyStartupRerunInvariantTests`
  - `test_re_seed_unassigns_leads_after_journey_style_assignment`
  - `test_re_seed_deletes_journey_created_be_backs`
  - `test_re_seed_clears_non_24hr_cadences_but_preserves_seed_24hr`
  - `test_re_seed_restores_paused_seed_24hr_cadence_to_active`
- `ReconWorkflowRerunInvariantTests`
  - `test_re_seed_clears_recon_decision_after_journey_style_click`
- `OfficeAccountingWorkflowRerunInvariantTests`
  - `test_re_seed_deletes_snapshots_on_fixture_dealership`

Pattern per test: seed → mutate (via real service verb —
`record_be_back`, `start_cadence` + `pause_cadence`,
`record_decision`, `freeze_trial_balance`) → re-seed →
assert invariant restored. Tests run under Django's default
per-test transactional rollback so they don't affect the
acceptance DB.

Test class count deliberately mirrors the three seed
commands under test; test method count reflects the natural
invariant decomposition (see §0.a).

## 3. DoD exception path — invocation #9

M34.1 is backend-only (seed idempotency + Django regression
tests). Zero operator-visible behavior — no view, service,
model, permission, URL, migration, or shipped-behavior change.
M34.0 §5.f documents this as the ninth invocation of the
M21.0 §5.f Option B exception path (M26 + M27.1 + M28.1 +
M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1). M34.2
continues the exception path (no new customer-facing
journey; existing three journeys tagged for rerun-proof).

M34 as a whole is the first fully non-customer-facing
milestone since M20 — 13 consecutive customer-facing
milestones broken intentionally per M33 §9 "close a
deferral" resolution.

## 4. Baselines at M34.1 close

- **Backend suite:** 5,015 → **5,021** pass, 1 skipped, 0
  fail (+6 vs planned +3; see §0.a). Duration measured at
  close: see run log.
- **Frontend Vitest:** unchanged (402 pass; M34.1 does not
  touch the frontend).
- **Acceptance workspace:** unchanged (25 spec files / 32
  tests; M34.1 does not touch the acceptance workspace).
- **`python3 manage.py check`:** clean.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **Audit artifact:** unchanged (162 / 131 / 31 / 321 — M34.1
  adds no endpoints, no service verbs). Two-source agreement
  gate at M34.1 close.

## 5. Streaks at M34.1 close

- **Planning-time as-recommended streak:** unchanged at **12
  → 13** projected at M34.2 close. M34.1 is pure
  implementation; §0.a coverage-projection truthfulness
  correction (test count overshoot) does not affect streak
  per SESSION_212 M33.1 §0.a convention. Historical run of
  89 across M10 → M23 preserved.
- **Zero-drift permission-class streak:** unchanged at **37**
  (M10 → M33). Projection at M34 close: **38 consecutive**
  (M34.1 adds no endpoints; M34.2 adds no endpoints).
- **Substrate-compound-value continuation:** unchanged from
  M34.0 — intentional pause per M33 §9 "close a deferral"
  resolution. F&I depth arc remains primary M35 candidate.
- **DoD exception path invocations:** 8 → **9** at M34.1.
  M34.2 continues (invocation still #9 conceptually since
  M34.2 doesn't add a new customer-facing journey; but the
  invocation count is a per-increment tally, so M34.2 will
  be #10 by that counting rule).
- **First (cc) re-application:** M33.1 origin at coverage-
  projection truthfulness correction; **M34.1 §0.a second
  invocation** at test-count overshoot. Elevation to load-
  bearing-across-two-milestones triggered at M34.1 per
  SESSION_212 M33 §5 candidate-elevation convention.
- **Six-milestone H deferral half-closed** — the seed-side
  half of H ships at M34.1; the acceptance-workspace half
  (helper defense + `@rerun-hygiene` tag + repeated-run
  evidence) ships at M34.2.

## 6. Push status

**No push at SESSION_214 close.** M34.1 is intermediate per
the standard M28.1 / M29.1 / M30.1 / M31.1 / M32.1 / M33.1
cadence. Coordinated M34 close push deferred to explicit
user confirmation after M34.2 close.

Local commits at SESSION_214 close:

- SESSION_214 backend seed extensions + regression tests +
  this handoff land in a single local-only commit per
  standard increment-close cadence; hash backfill via a
  subsequent commit.

Expected M34 commit count at coordinated push: **4–6**
(M34.0 planning + M34.0 hash-backfill + M34.1 backend +
M34.1 hash-backfill + M34.2 acceptance + M34.2 hash-
backfill / close-out fold).

## 7. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_215 ·
Milestone 34 · Increment 2 (M34.2 — acceptance workspace:
helper defense + `@rerun-hygiene` tag + repeated-run
proof + M34 close-out fold)**. First-thing sequence per
M28.2 / M29.2 / M30.2 / M31.2 / M32.3 / M33.2 pattern:

1. **Verify starting state** (git status; backend suite
   **5,021 pass** matches M34.1 close; frontend Vitest 402
   pass; checks; migrations; tsc; redis;
   `db.acceptance.sqlite3` proactive reset).
2. **Confirm working from M34.0 planning memo** — read
   `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D5 + D7 + D8
   + §5.e M34.2 + §5.h before touching acceptance code.
3. **Ship M34.2 acceptance substrate** per §5.e:
   - Refactor `acceptance/support/assertions/accounting.ts`
     per D5 (`fetchSnapshotList` returns
     `{snapshots, totalCount}`; `expectSnapshotCountAtLeast`
     asserts against `totalCount`; `fetchAllJournalEntries`
     untouched — M22.2 JE-reversal journey unaffected).
   - Add `@rerun-hygiene` tag to the three
     `test.describe(...)` strings per D7.
   - Update `acceptance/README.md` with the developer-side
     repeated-run invocation per D7 Option A.
   - Run `npx playwright test --repeat-each=2 --grep "@rerun-hygiene"`
     locally and record pass output in the M34.2 handoff §7.
4. **Ship M34 close-out fold:**
   - New `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` with
     §1–§9 including candidate lesson (ff) per D8 verbatim.
   - `docs/CAPABILITY_MATRIX.md` new §7ι M34 shipped surface
     entry + (ff) candidate + (cc) elevation-to-load-bearing
     note.
   - `MILESTONE_34_PLANNING.md` frontmatter flip
     `active` → `historical`.
   - `00-START-NEXT-SESSION.md` flip to SESSION_216 M35.0
     planning.
5. **Verify M34.2 close baselines:** backend suite unchanged
   at 5,021 pass; audit unchanged at 162 / 131 / 31 / 321;
   acceptance suite unchanged in count (25 spec files / 32
   tests; timing budget +2s allowed for seed reset overhead).
6. **DoD exception path** — tenth invocation. Document in §3
   of M34.2 handoff (helper refactor + tag + README have
   zero operator-visible behavior; existing journeys
   preserve their operational contract).
7. **Ship the M34.2 handoff at
   `docs/handoffs/SESSION_215_m34_inc2_acceptance.md`.**
   **Coordinated M34 push at close** after explicit user
   confirmation.

## 8. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_34_PLANNING.md`** (governing
   contract for M34)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (unchanged
   at M34.1 close — 162 / 131 / 31 / 321)
8. `docs/CAPABILITY_MATRIX.md` §7θ (M33 shipped surface);
   §7ι added at M34 close
9. `docs/handoffs/SESSION_213_m34_inc0_planning.md` (M34.0
   planning close)
10. **This handoff** (`SESSION_214_m34_inc1_seeds.md`)
11. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs D1 no-shared-helper decision;
    honored at M34.1 with three domain-local
    `_restore_rerun_invariants` methods and no shared
    abstraction)
12. Memory record
    `feedback_playwright_as_operational_contract.md` (M33
    D8 strengthening invocation; M34.1 preserves the
    contract by making the seed side rerun-safe; M34.2 will
    add the acceptance-side proof)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at M34.0 §4.5 for cascade
    behavior on `ReconDecision.finding` OneToOne)
14. Memory record `feedback_terminal_output_discipline.md`
    (governs implementation-session output shape)
