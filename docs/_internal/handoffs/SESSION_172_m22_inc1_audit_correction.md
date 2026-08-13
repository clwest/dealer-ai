---
title: "SESSION_172 handoff — Milestone 22 · Increment 1 (M22.1 — audit tooling correction + artifact refresh)"
status: historical
type: handoff
date: 2026-08-03
session: 172
milestone: 22
milestone_status: in-progress
milestone_name: "Accounting Operational Validation"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_172 — Milestone 22 · Increment 1 (M22.1 — audit tooling correction + artifact refresh)

## What shipped

Supporting-work increment per §5.e
Option B — targeted regex + parser
enhancements to
`backend/dealer_ai/scripts/audit_operational_surface.py`
that close the four accounting
false-negatives identified during
M22.0 empirical discovery. Not the
milestone centerpiece; the anchor
JE reversal journey lands at M22.2.

**Coverage delta.** Audit artifact
regenerated. Coverage **106 → 110
(+4)**. Backend-only **47 → 43 (-4)**.
All four accounting endpoints
identified at M22.0 open reclassify
from backend-only to `covered`:

- `admin-trial-balance` — was
  `defer-candidate-O2`, now
  `covered` (accountingApi.ts:65
  `fetchTrialBalance`).
- `admin-journal-entry-list` — was
  `defer-candidate-O2`, now
  `covered` (accountingApi.ts:201
  `fetchJournalEntries`).
- `admin-cost-posting-failures` —
  was `defer-candidate-O2`, now
  `covered` (accountingApi.ts:310
  `fetchCostPostingFailures`).
- `admin-trial-balance-snapshot-list`
  — was `defer-domain-milestone`,
  now `covered` (accountingApi.ts:142
  `listTrialBalanceSnapshots`).

**Budget guard status.** ~30-40
minutes of active work — well under
the ~2-hour §5.e guard. No deferral
to a future audit-tooling milestone
required.

**Backend baseline unchanged:** 4,761
pass, 1 skipped, 0 fail. Verified
post-fix with full
`python3 manage.py test dealer_ai`
— zero regressions. Frontend Vitest
unchanged: 180 pass. Acceptance
suite unchanged: 6 journeys.
Migrations, tenancy carriers,
permission classes, DRF endpoints,
frontend routes, celery-beat
families all unchanged.

## Root-cause reframe

The M21 retrospective §4 documented
the false-negative class as **"nested
TypeScript template literals confuse
the URL normalizer."** M22.1
investigation shows this framing was
partially incorrect. The actual
class is **variable-first URL
assembly** — wrappers that assign
their URL into a `const path`
variable and pass the identifier to
`authGetJSON(path)` rather than a
string literal. `_HELPER_CALL_RE`
only matched literal-arg helper
calls, so these wrappers were
completely invisible to the audit
regardless of their template
complexity.

Nested template literals are a
common co-occurring pattern (three
of the four affected wrappers use
`` const path = `/admin/.../${qs ? `?${qs}` : ""}` ``)
so both fixes were needed: the
identifier-arg regex to detect the
wrapper at all, plus balanced-brace
parsing to correctly collapse the
nested `${...}` at normalization
time.

Reframing this in the audit script
docstrings and in the M22 planning
memo §0.a M22.1 amendment helps
future audit maintainers understand
the actual failure mode when
similar patterns recur.

## Three targeted changes

1. **Extended `_HELPER_CALL_RE`** to
   match identifier arguments as a
   new alternative:
   ```
   \(\s*(`[^`]*(?:`|$)|"[^"]*"|'[^']*'|[a-zA-Z_][\w]*)
   ```
   The identifier alt fires when the
   URL is a variable rather than a
   literal. Also widened the
   template-literal alt to allow
   unterminated matches (`(?:`|$)`)
   as a safety net.
2. **New `_resolve_variable_url()` +
   `_extract_url_literals()`
   helpers.** When
   `_HELPER_CALL_RE` captures an
   identifier, `_resolve_variable_url`
   walks backward from the helper
   call to the enclosing wrapper's
   `export function` header, then
   uses a regex to find the last
   `const|let|var <name> = <expr>;`
   assignment. `_extract_url_literals`
   walks the assignment expression
   char-by-char (with backtick +
   `${}` depth tracking) to extract
   every string/template literal —
   handling both plain assignments
   and ternaries
   (`const path = cond ? "..." : "..."`)
   by emitting both branches as
   distinct consumers.
3. **Balanced-brace
   `_collapse_ts_templates()` +
   rewritten `_expand_helper_calls()`.**
   Both use a char-by-char parser
   that walks `${...}` substitutions
   with proper depth counting and
   backtick-nesting awareness. The
   previous `[^}]+` regex approach
   truncated at the first `}` and
   produced garbage output for
   nested cases like
   `` ${qs ? `?${qs}` : ""} ``.

## Verification

- Ran
  `python3 -m dealer_ai.scripts.audit_operational_surface`
  from `backend/`. Output:
  - Backend endpoints: 153 (unchanged)
  - Covered: 106 → **110 (+4)**
  - Backend-only: 47 → **43 (-4)**
  - Service verbs: 312 (unchanged)
- Diff of
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  isolated to:
  - Four accounting rows (142, 143,
    144, 146) reclassify to
    `covered`.
  - Two ancillary row-order
    shuffles (recon row 51,
    f_and_i row 101) where the
    same wrappers list in different
    order — same dispositions, no
    semantic change.
  - Summary counts updated
    accordingly.
  - No unexpected reclassifications
    elsewhere.
- Ran full backend test suite
  post-fix — **4,761 pass, 1
  skipped, 0 fail** — zero
  regressions.

## Deferrals surfaced during M22.1

- **Full AST-based audit rewrite.**
  Still explicit non-goal per §5.e
  Option B. The targeted regex +
  parser approach is sufficient
  for the current wrapper corpus.
  If future patterns break it
  (URLs assembled by string
  concatenation across multiple
  statements, computed URL values
  from Map/Record lookups, URLs
  built inside conditional
  branches spanning multiple
  statements), those become
  candidates for a dedicated
  audit-tooling milestone.
- **Audit-script correctness
  tests.** Discretionary per
  M22.0. Not added at M22.1 —
  the artifact regeneration is
  the functional verification.
  If the audit script becomes
  more complex or if regressions
  surface, adding pytest
  coverage of the URL-normalizer
  helpers is a reasonable future
  investment.
- **Documentation of the
  actual false-negative class
  in audit-script comments.**
  The script's docstring still
  refers to regex-based
  extraction being "sufficient"
  which is true but understates
  the variable-resolution
  complexity added at M22.1.
  Comment-level refactoring
  deferred to a future audit-
  tooling milestone.

## Streak

**Planning-time as-recommended:
still 88 across thirteen
consecutive milestones (M10 → M22).**
M22.1 is implementation work; no
new §5 decisions surfaced.

**Zero-drift permission-class:
still 21 consecutive milestones
(M10 → M21).** M22.1 introduces
zero permission-class changes.
Streak target at M22.4 close:
22.

## What's next: SESSION_173 M22.2 JE reversal journey + seed extension

Per `MILESTONE_22_PLANNING.md` §7
M22.2:

- **Extended seed** at
  `backend/dealer_ai/management/commands/seed_journey_office_accounting_workflow.py`
  with a reversible-JE fixture
  (stable description tag —
  `[M22.2-office-je-reversal]` or
  similar; idempotent reuse per
  the M20.3 pattern). Add backend
  test covering fixture
  idempotency + tenant scoping.
- **Extended assertion helper** at
  `acceptance/support/assertions/accounting.ts`
  with `expectJournalEntryReversed(request, originalId)`
  — asserts the reversal entry
  exists with swapped debit/credit
  lines and `reverses_id`
  pointing back to the original.
- **New journey** at
  `acceptance/journeys/office/accounting_je_reversal.spec.ts`
  walking: navigate to JE detail
  for the seeded reversible entry
  → open reversal dialog → fill
  reason ("M22 test reversal") →
  click confirm → verify status
  message → verify reversal
  linkage badge appears on page
  reload → business-outcome
  assertion via the new API
  helper.
- **Concurrent §5.b page/persona
  walk during authoring** — while
  authoring the journey, walk the
  three shipped accounting pages
  (`AccountingTrialBalancePage`,
  `AccountingJournalEntriesPage`,
  `AccountingJournalEntryDetailPage`)
  from the office-manager persona
  perspective. Document every
  distinct workflow surfaced.
  Findings feed the M22.3 scope
  decision (skip vs. author N
  additional journeys).
- **Small operator-surface gap
  fixes per §5.d** if any
  discovered — inline label typo,
  missing testid on a new insertion
  point, broken link, form
  validation bug. In-scope for one-
  file trivial changes; larger
  gaps get documented in
  retrospective §9 as next
  accounting candidate per §5.d
  Option B.
- **Session handoff** at
  `docs/handoffs/SESSION_173_m22_inc2_je_reversal.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M22.3 or M22.4
  depending on §5.b findings.

**Backend baseline target at M22.2
close:** 4,761 → **~4,763** (seed
fixture idempotency tests).
Frontend Vitest: 180 (unchanged
unless §5.d fixes add cases).
Acceptance suite: **6 → 7**.

## What lands at M22.3 (conditional, SESSION_174)

Only if the M22.2 §5.b page/persona
walk surfaces additional distinct
journey-worthy workflows. Skipped
entirely if the walk demonstrates
JE reversal was the only genuine
gap. See MILESTONE_22_PLANNING.md
§7 M22.3 for details.

## What lands at M22.4 (SESSION_174 or SESSION_175) — close-out

CI validation on all new / extended
journeys + capability matrix +
retrospective + M23 planning
skeleton + coordinated close-out
push per M18.6 / M19.6 / M20.5 /
M21.5 cadence. See
MILESTONE_22_PLANNING.md §7 M22.4
for details.

## Non-goals for the remaining M22 increments

Per MILESTONE_22_PLANNING.md §3:

- ❌ Do NOT ship new accounting UI
  (rebuilding what already ships
  from M14/M17).
- ❌ Do NOT add new backend service
  verbs, DRF endpoints, tenancy
  carriers, migrations, permission
  classes, or frontend routes.
- ❌ Do NOT rewrite the audit
  script as AST-based — targeted
  regex fix already landed at
  M22.1 per §5.e Option B.
- ❌ Do NOT manually verify
  workflows before authoring
  journeys — journey-as-verifier
  per §5.f Option B.
- ❌ Do NOT force-scope larger
  discovered accounting gaps into
  M22 — document as retrospective
  §9 evidence per §5.d Option B.
- ❌ Do NOT split the accounting
  seed into per-workflow seeds
  pre-emptively — extend
  additively per §5.g Option A.
- ❌ Do NOT push M22 commits
  individually — coordinated
  close-out push at M22.4 per
  M18.6 / M19.6 / M20.5 / M21.5
  cadence.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M21 shipped + DoD amendment
   landed at M21.5)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (active memo — §0.a M22.1
   amendment records the root-
   cause reframe and shipped
   fix)
6. `docs/handoffs/SESSION_171_m22_inc0_planning.md`
   (M22.0 close — empirical
   discovery record that drove
   M22.1)
7. `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
   §4 (original false-negative
   class documentation — M22.1
   updates the framing)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — now
   authoritative for accounting
   endpoints post-M22.1 fix)
9. `docs/CAPABILITY_MATRIX.md` §7v
   (M21 shipped surface)
