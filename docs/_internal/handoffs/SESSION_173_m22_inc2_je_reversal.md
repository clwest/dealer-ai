---
title: "SESSION_173 handoff — Milestone 22 · Increment 2 (M22.2 — JE reversal journey + seed extension)"
status: historical
type: handoff
date: 2026-08-03
session: 173
milestone: 22
milestone_status: in-progress
milestone_name: "Accounting Operational Validation"
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_173 — Milestone 22 · Increment 2 (M22.2 — JE reversal journey + seed extension)

## What shipped

First anchor journey — validates
the JE reversal workflow end-to-
end via Playwright per the M22
governing contract. Journey passes
locally on both isolated
(`office_accounting` project, 7
passed @ 450ms) and full-suite
(clean-DB dry-run, 13 passed @
18.2s) invocations.

**Backend baseline delta: 4,761 →
4,766 (+5)** — five new M22.2
test cases in the seed test
module covering the reversible-
JE fixture, its idempotency, the
seed-side reversal cleanup, and
reset behavior. Zero test
regressions.

**Frontend Vitest unchanged at
180** — M22.2 introduces zero
frontend components per §5.a
refined framing. The M14.3/M14.4
detail page + reversal dialog
ship operationally complete; no
UI changes needed.

**Acceptance suite: 6 → 7
journeys.** New file
`acceptance/journeys/office/accounting_je_reversal.spec.ts`
joins the existing six baseline
journeys.

**M22.3 SKIPPED** per §5.h Option
B evidence-sized posture. §5.b
page/persona walk during
authoring surfaced no additional
distinct-workflow gaps warranting
dedicated Playwright coverage.
Slot returned to milestone;
M22.4 close-out becomes
SESSION_174.

## Journey walked

`acceptance/journeys/office/accounting_je_reversal.spec.ts`
authenticated as the
`acceptance-owner` persona
(dealer_owner role, valid for
the M13/M14/M17 accounting
endpoint permission gate
`IsSalesManagerOrOwnerAtActiveDealership`):

1. Look up the M22.2 reversible
   fixture via the M14.1 admin
   list endpoint using the
   description-prefix helper
   `findJournalEntryByDescriptionPrefix`.
   The seed guarantees exactly
   one entry with the
   `[M22.2-office-je-reversal]`
   tag; helper fails loudly if
   zero or multiple match.
2. Navigate to
   `/dealer-ai-accounting/journal-entries/<pk>`.
   Detail heading verified to
   contain the JE id.
3. Click "Reverse this entry"
   button — reversal dialog
   opens with the JE id in its
   heading.
4. Fill reason textarea with
   a stable test string ("M22
   acceptance journey —
   verifying the reversal
   workflow is operational").
5. Click "Confirm reversal" —
   dialog closes after the
   POST resolves.
6. Business-outcome assertion
   via `expectJournalEntryReversed(request, fixture.id)`:
   - Reversal entry exists with
     `reverses_id === fixture.id`.
   - Reversal reason is non-
     empty and contains the
     submitted string.
   - Sign-flip invariant holds
     — reversal total debits
     equals original total
     credits, and vice versa
     (M13.1 immutability +
     line-swap contract).

## Seed extension

`backend/dealer_ai/management/commands/seed_journey_office_accounting_workflow.py`
extended additively per §5.g
Option A:

- New constants
  `M22_REVERSIBLE_FIXTURE_DESCRIPTION`
  and `M22_REVERSIBLE_FIXTURE_AMOUNT`
  ($250 — distinct from M20.3
  fixture $100 so debug traces
  name them unambiguously).
- `handle()` now provisions
  both fixtures via a
  refactored
  `_provision_journal_entry(description, amount, memo_tag)`
  helper that accepts arbitrary
  description + amount +
  memo_tag rather than hard-
  coding the M20.3 values.
- New `_drop_reversals_targeting(target)`
  helper deletes any reversal
  entries carrying
  `reverses_id = target.pk`.
  Called on the M22.2 fixture
  after provisioning so the
  fixture stays reversible
  across suite re-runs.
- `_reset()` now sweeps both
  fixture descriptions.

**Idempotency preserved.**
Re-invocation with the same
suite state produces identical
row shape (M20.3 fixture reused
+ M22.2 fixture reused + any
reversals from prior journey
runs cleared).

## Assertion helper extension

`acceptance/support/assertions/accounting.ts`
extended with:

- `JournalEntryListRow` +
  `JournalEntryDetail` types
  matching the M14.1 list +
  M13.1 detail projections.
- `findJournalEntryByDescriptionPrefix(request, prefix)`
  — fetches the full JE list
  (page_size=100; the M22.2
  fixture set stays well under
  one page) and returns the
  single row matching the
  prefix. Fails loudly if zero
  or multiple match.
- `expectJournalEntryReversed(request, originalId)`
  — fetches the JE list to
  find reversals targeting the
  original, fetches the newest
  reversal's detail, asserts
  linkage + non-empty reason +
  sign-flipped line totals.

## Seed test extension

`backend/dealer_ai/tests/test_m203_seed_journey_office_accounting_workflow.py`
extended with a new test class
`SeedOfficeAccountingWorkflowM22ReversibleFixtureTests`
containing 5 test cases:

1. `test_m22_fixture_provisioned_alongside_m20_fixture`
   — both fixtures exist on
   the default dealership after
   seed.
2. `test_m22_fixture_has_expected_amount_and_shape`
   — line count, debit/credit
   accounts, amounts distinct
   from M20.3.
3. `test_second_invocation_does_not_duplicate_m22_fixture`
   — idempotency.
4. `test_seed_clears_reversal_targeting_m22_fixture`
   — posts a reversal via the
   `reverse_journal_entry`
   service verb, re-runs seed,
   asserts the reversal is
   deleted while the fixture
   itself survives.
5. `test_reset_deletes_m22_fixture`
   — `--reset` removes both
   fixtures and re-provisions
   them fresh.

All 12 tests in the module pass
(7 original + 5 new).

## §5.b page/persona walk outcome (drives M22.3 SKIP decision)

Walked the three shipped
accounting pages from the
office-manager persona
perspective during M22.2
authoring:

| Page | Workflow | Coverage | M22.3 decision |
|---|---|---|---|
| `AccountingTrialBalancePage` | Trial-balance freeze + prior-closes drill-down | **Covered** (M20.3 journey) | N/A |
| `AccountingTrialBalancePage` | As-of picker interaction for historical trial balance | Uncovered; low-frequency analytical work, not workflow-critical for daily operations | Defer as future evidence |
| `AccountingTrialBalancePage` | Cost-posting failures rendering path | Conditional (only fires when failures exist); requires additional seed scaffolding | Defer as future evidence |
| `AccountingJournalEntriesPage` | List navigation + drill-in | Endpoint reclassified `covered` at M22.1 (wrapper consumed); shipped Vitest coverage validates rendering | Defer as future evidence — small marginal value; operators arrive at detail through multiple paths (list, deep-links, notification actions) |
| `AccountingJournalEntryDetailPage` | JE reversal workflow | **Covered** (M22.2 journey) | N/A |
| `AccountingJournalEntryDetailPage` | Back-to-list link | Implicit navigation covered by shipped React Router | N/A |

**Decision: M22.3 SKIPPED.** No
additional distinct-workflow
gaps warrant dedicated journey
files per §5.h Option B
evidence-sized posture.
Remaining uncovered workflows
are either (a) covered by non-
Playwright means (Vitest +
audit reclassification), (b)
low-frequency analytical, or
(c) conditional edge cases
requiring dedicated seed
scaffolding. All three feed
retrospective §9 as future
evidence rather than force-
scope into M22.

## §5.d gap fixes

**None required.** Journey
authoring proceeded cleanly
against the shipped M14.3/M14.4
markup. `getByRole` +
`getByText` selectors matched
against existing accessible-
name attributes on the
"Reverse this entry" button,
the dialog heading, the Reason
textarea, and the "Confirm
reversal" button. No testid
additions or copy fixes needed
per §5.d Option B threshold.

**Corollary:** the shipped
reversal UI's accessibility
posture is journey-friendly by
default. Future accounting
journey authoring can rely on
the same role-based selector
approach without pre-instrumentation.

## Verification

- **Isolated run:** `npx
  playwright test office/accounting_je_reversal.spec.ts
  --project=office_accounting`
  → 7 passed (6 setup + 1
  journey) in 10.5s.
- **Full suite (clean DB):**
  Deleted
  `backend/db.acceptance.sqlite3`,
  reran `npx playwright test`
  → 13 passed (6 setup + 7
  journeys) in 18.2s.
- **Backend full suite:**
  `python3 manage.py test
  dealer_ai` → 4,766 pass, 1
  skipped, 0 fail. Zero
  regressions from the seed
  changes.
- **Acceptance tsc:** `cd
  acceptance && npx tsc
  --noEmit` clean.

## Pre-existing test-hygiene issue noted (NOT M22.2 regression)

The first full-suite run
before deleting the acceptance
DB surfaced 3 pre-existing
failures caused by same-day
multi-run state pollution:

1. `office/accounting_workflow`
   — 409 on freeze (snapshot
   already exists for today).
2. `sales_manager/daily_startup`
   — advisor assignment
   assertion (`expected null;
   got existing assignment`).
3. `recon/workflow` — decision
   assertion (`expected null;
   got existing decision`).

**Not caused by M22.2 changes.**
After deleting
`backend/db.acceptance.sqlite3`
and re-running, all 13 tests
pass cleanly. The three
journeys mutate DB state that
their seeds don't reset;
running the suite twice on the
same day without a DB reset
surfaces the issue.

**Future work candidate (not
M22 scope):** Extend the three
affected seeds to sweep the
mutated state they don't
currently clean up
(analogous to how M22.2's seed
now sweeps reversals). Feeds
retrospective §9 as an
operational-hygiene
observation rather than an
M22 in-scope fix.

## Streak

**Planning-time as-recommended:
still 88 across thirteen
consecutive milestones (M10 →
M22).** M22.2 is implementation
work; no new §5 decisions
surfaced.

**Zero-drift permission-class:
still 21 consecutive milestones
(M10 → M21).** M22.2 introduces
zero permission-class changes.
Streak target at M22.4 close:
22.

## What's next: SESSION_174 M22.4 close-out

M22.3 SKIPPED per §5.b findings
— M22.4 close-out advances
directly to SESSION_174.

Per `MILESTONE_22_PLANNING.md`
§7 M22.4:

- **CI validation** on all
  extended / new journeys.
  Full-suite dry-run on clean
  DB before coordinated push.
- **`docs/CAPABILITY_MATRIX.md`
  §7w** — M22 shipped surface:
  audit tooling correction +
  seed fixture extension + new
  assertion helpers + new JE
  reversal journey.
- **`docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`**
  covering: what shipped, §5.a
  refinement empirical
  discovery, §5.b page/persona
  walk findings, M22.3 skip
  rationale, §5.d no-gap-
  fixes outcome, §8
  corrections landed (audit
  reclassifications), §9 next-
  accounting-candidate
  identified with evidence
  (including the pre-existing
  test-hygiene issue as a
  potential future scope
  target).
- **`docs/roadmap/MILESTONE_23_PLANNING.md`**
  skeleton (status: draft)
  with candidate list refreshed
  from M22 retrospective §9
  findings + remaining M21 /
  M20 / M19 candidates.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`**
  updated with M22 shipped
  status.
- **Session handoff** at
  `docs/handoffs/SESSION_174_m22_inc4_close.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M23.0.
- **Coordinated close-out
  commit + push per M18.6 /
  M19.6 / M20.5 / M21.5
  cadence.**

## Non-goals for SESSION_174

Per MILESTONE_22_PLANNING.md §3:

- ❌ Do NOT ship new accounting
  UI or wrappers.
- ❌ Do NOT add new backend
  service verbs, DRF endpoints,
  tenancy carriers, migrations,
  permission classes, or
  frontend routes.
- ❌ Do NOT extend M22 scope
  by pulling in future-work
  candidates surfaced during
  M22.2 (test-hygiene fix,
  navigation-audit journey,
  as-of picker journey,
  cost-posting-failures
  journey) — all recorded in
  retrospective §9 as
  evidence-based candidates
  for M23+ consideration.
- ❌ Do NOT push M22 commits
  individually — coordinated
  push at M22.4 close-out.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD amendment
   landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (active memo — §0.a M22.2
   amendment records shipped
   journey + skip decision)
6. `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`
   (M22.1 close — audit fix
   context)
7. `docs/handoffs/SESSION_171_m22_inc0_planning.md`
   (M22.0 close — empirical
   discovery + governing
   contract)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — authoritative
   for accounting post-M22.1
   fix)
9. `acceptance/journeys/office/accounting_workflow.spec.ts`
   (existing M20.3 trial-balance
   freeze journey — pattern
   reference for M22.2
   authoring)
10. `docs/CAPABILITY_MATRIX.md` §7v
    (M21 shipped surface)
