---
title: "SESSION_196 handoff — Milestone 28 · Increment 2 (M28.2) + close-out fold"
status: historical
type: handoff
date: 2026-08-03
session: 196
milestone: 28
milestone_status: shipped
milestone_name: "Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
increment: 2
increment_status: shipped
commit: 5a7f978
---

# SESSION_196 — Milestone 28 · Increment 2 (M28.2 — UI + Playwright) + close-out fold

## What shipped

M28.2 delivers all remaining operator-facing value for
Milestone 28: the "Recurring templates" collapsible section
on the existing JE list page, the `NewJournalEntryTemplateDialog`
component, the additive `initialValues` + controlled-open
props on the M27.2 `NewJournalEntryDialog`, the row-level
Instantiate wiring, nineteen new component vitests, and a
Playwright peer spec with two test cases (create-template +
instantiate-template) plus a one-case extension to the
existing `accounting_je_create.spec.ts` (blank-path regression
guard). M28.3 close-out folds into M28.2 per §5.h Option B —
both increments' §5.e Phase 1 + Phase 2 verifications passed
cleanly on the first regeneration.

### Frontend page extension

- **`frontend/src/pages/AccountingJournalEntriesPage.tsx`** —
  extended in place per M27.0 §5.b substrate-attachment rule
  (no new frontend route). Added:
  - Third `useEffect` to fetch active templates on mount via
    the M28.1 `fetchJournalEntryTemplates` wrapper + on a
    `templatesReloadTick` bump.
  - New "Recurring templates" collapsible section beneath the
    existing JE list card (peer of the JE list). Header
    contains title + count badge + "+ New template" trigger
    + Collapse/Expand toggle. Collapsed by default per
    progressive disclosure.
  - Row-level Instantiate action per template row that builds
    an `initialValues` object from the template (mapping
    `side`+`amount` → `debit`/`credit` for the JE dialog
    shape) and opens a second, controlled mount of
    `NewJournalEntryDialog` (with `hideTrigger`).
  - Second controlled `NewJournalEntryDialog` mount kept
    adjacent to the primary uncontrolled dialog so both share
    the same `accounts` prop and success callback.
  - `handleTemplateCreated` refetches the templates list on
    success + shows inline emerald success badge.
  - Templates fetch-error inline message when
    `fetchJournalEntryTemplates` fails.
  - `templateToInitialValues` helper maps template shape →
    JE-dialog `initialValues` shape (side derivation + memo
    passthrough + posted_at intentionally omitted so the JE
    dialog defaults to today).

### New component

- **`components/accounting/NewJournalEntryTemplateDialog.tsx`**
  — peer of the M27.2 `NewJournalEntryDialog` with the same
  viewport-constraint pattern (`max-h-[90vh] flex-col` +
  scrollable inner body + fixed footer). Fields: `name`
  (required trimmed ≤200 chars), `description` (required
  trimmed ≤500 chars), dynamic `lines[]` (min 2 enforced),
  per-row `GLAccountPicker` reuse + `side` select
  (debit/credit) + `amount` numeric input + optional `memo`.
  Live balance indicator (Σ debit-side vs Σ credit-side).
  Submit → `createJournalEntryTemplate` → on 201 closes
  dialog + refetches templates + inline success badge.
  Cancel closes with no side effects. Server errors render
  inline (409 duplicate name friendlier phrasing possible
  in a future refinement).

### Extended component

- **`components/accounting/NewJournalEntryDialog.tsx`** —
  additive refactor for the template Instantiate flow. New
  optional props: `open` + `onOpenChange` (controlled-open
  mode when both supplied; otherwise uncontrolled with
  built-in trigger — fully backward-compatible),
  `initialValues` (pre-populate description + lines on each
  open transition; falls back to blank),
  `hideTrigger` (suppress the "+ New journal entry" button
  for external-open contexts). Refactor is behavior-
  preserving; all 9 existing dialog tests remained green
  without modification. State reset now uses
  `initialValues`-aware defaults so re-opening the dialog
  in either uncontrolled (blank) or controlled+pre-populated
  contexts works identically.

### Component vitests (+19)

- **`NewJournalEntryTemplateDialog.test.tsx`** — 11 tests
  covering: renders trigger; disabled trigger with fewer
  than 2 accounts; opens dialog on trigger click; no
  `posted_at` field (templates are recipes); blocks submit
  when name blank; blocks submit when unbalanced; shows
  Balanced badge when debit-side sum equals credit-side
  sum; posts payload + fires `onCreated` on success;
  surfaces server errors inline without closing dialog;
  cancel closes with no side effects; add + remove lines
  beyond min-2 enforcement.
- **`NewJournalEntryDialog.test.tsx`** M28.2 extension —
  3 tests covering: `hideTrigger` suppresses the trigger
  button; `initialValues` pre-populates description + lines
  on open (verified via balance indicator + submit enabled
  without further typing); submit of a pre-populated dialog
  posts the visible payload and calls `onOpenChange(false)`
  on success.
- **`AccountingJournalEntriesPage.test.tsx`** M28.2 extension
  — 5 tests covering: templates section renders with count
  badge; empty-state message when expanded; template rows +
  Instantiate buttons when expanded; Instantiate opens the
  JE dialog pre-populated with description + line amounts
  + balance indicator Balanced immediately; templates fetch
  error surfaces inline.

### Playwright coverage

- **NEW spec `acceptance/journeys/office/accounting_je_template.spec.ts`**
  with two test cases per §5.d:
  - **Case 1 — Create template.** Owner navigates to the JE
    list page, expands the "Recurring templates" section,
    clicks "+ New template", fills name + description + two
    balanced lines using both code-search ("800" → 800000
    Rent Expense) and name-search ("Bank" → 110000 Bank —
    Operating) picker modes, flips line 2 side to credit,
    enters amounts, asserts Balanced indicator, submits.
    Success badge visible; template row appears in list.
    Business-outcome assertion via admin API: template
    exists with expected name + description + 2 lines +
    account codes + amounts.
  - **Case 2 — Instantiate template.** Owner opens JE list,
    expands templates section, clicks Instantiate on a
    template seeded via the admin API (using new
    `postWithCsrf` helper — DRF SessionAuthentication
    requires `X-CSRFToken` header on mutating requests,
    which Playwright's APIRequestContext does not auto-
    populate from the storage-state csrftoken cookie).
    JE dialog opens pre-populated with description +
    posted_at defaulting to today + line amounts on correct
    sides + balance indicator immediately Balanced + submit
    enabled without further typing. Operator clicks submit;
    dialog closes; success badge visible for the newly-
    posted JE. Business-outcome assertion via admin API: JE
    exists with template's description + account codes +
    amounts on lines; balanced.

- **Extension to `accounting_je_create.spec.ts`** — one new
  test case asserting the "+ New journal entry" blank path
  continues to open a blank dialog (regression guard against
  M28.2 pre-populate wiring accidentally polluting the
  blank flow).

### Playwright discoveries (recorded as durable lessons)

- **CSRF header not auto-populated.** DRF SessionAuthentication
  requires `X-CSRFToken` on mutating requests. Browser
  fetch/XHR wiring copies this from the csrftoken cookie
  automatically; Playwright's APIRequestContext does not.
  Added `postWithCsrf` helper that extracts csrftoken from
  `request.storageState()` and includes it as an
  `X-CSRFToken` header. Available for future specs.
- **Numeric input value normalization.** `<input type="number">`
  may render `3500.00` as `3500` or preserve the trailing
  zeros depending on browser. Playwright `toHaveValue`
  assertions on pre-formatted numeric strings should use
  regex to accept either format.

## Baselines at M28 close

- **Backend: 4,855 pass**, 1 skipped, 0 fail (164.1s) —
  unchanged from M28.1 close (no backend code at M28.2).
- **Frontend Vitest: 251 → 270 pass** across 35 → 36 files
  (+19 UI-facing tests at M28.2).
- **Acceptance: 16 → 19 journeys**. Full run: **22 passed / 3
  pre-existing shared-DB failures** unchanged from M27.2
  close (`sales_manager/daily_startup`,
  `recon/workflow`, `office/accounting_workflow` — Candidate
  H remediation, not M28 scope).
- **Audit: 155 → 156 endpoints / 121 → 122 covered / 34
  backend-only / 312 → 315 service verbs.** Row 150
  `admin/accounting/journal-entry-templates/` disposition
  flipped `defer-candidate-O2 → covered` at M28.2 (both
  wrappers now detected as consumed).
- `python3 manage.py check` clean; `makemigrations --check
  --dry-run` clean; `redis-cli ping` PONG; `frontend tsc
  --noEmit` clean; `acceptance tsc --noEmit` clean.

## §5.e two-source agreement (M28.2 close)

Both sources agree:

1. **Regenerated artifact.** Row 150 shows both wrappers
   consumed (no `⚠ wrapper-only` flag); disposition flipped
   to `covered`.
2. **Direct repo inspection.** Both wrappers imported and
   called by non-test frontend:
   - `fetchJournalEntryTemplates` — imported by
     `AccountingJournalEntriesPage.tsx` (templates section
     `useEffect`).
   - `createJournalEntryTemplate` — imported by
     `NewJournalEntryTemplateDialog.tsx` (submit handler).

## What was NOT touched this session

- **Backend code.** Zero M28.2 backend changes; baseline
  holds.
- **M13.1 shipped surface** (`JournalEntry`, `JournalEntryLine`,
  `admin_journal_entry_create` endpoint) — unchanged.
- **M27.1 shipped surface** (`gl-accounts` endpoint,
  `fetchGLAccounts` wrapper, `GLAccountPicker` component) —
  consumed as-is; not modified.
- **M28.1 shipped surface** (template models, service verbs,
  endpoint, wrappers) — consumed as-is; not modified.
- **Test-hygiene Candidate H** — 3 shared-DB non-idempotent
  journeys still fail on full-suite polluted-DB runs (same
  pre-existing failures documented at M27.2 close). Not M28
  scope; remains a live M29+ candidate.

## Files created / modified this session

- **CREATED:** `frontend/src/components/accounting/NewJournalEntryTemplateDialog.tsx`.
- **CREATED:** `frontend/src/components/accounting/NewJournalEntryTemplateDialog.test.tsx`
  (11 tests).
- **CREATED:** `acceptance/journeys/office/accounting_je_template.spec.ts`
  (2 test cases + `postWithCsrf` helper).
- **CREATED:** `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md`.
- **CREATED:** `docs/handoffs/SESSION_196_m28_close.md` —
  this handoff.
- **MODIFIED:** `frontend/src/components/accounting/NewJournalEntryDialog.tsx`
  — additive `open`/`onOpenChange`/`initialValues`/`hideTrigger`
  props + open-transition re-seed effect + `initialValues`-
  aware reset. Backward-compatible.
- **MODIFIED:** `frontend/src/components/accounting/NewJournalEntryDialog.test.tsx`
  — +3 M28.2 pre-populate/controlled-open tests.
- **MODIFIED:** `frontend/src/pages/AccountingJournalEntriesPage.tsx`
  — templates fetch + collapsible section + Instantiate
  wiring + `templateToInitialValues` helper + second
  controlled JE dialog mount.
- **MODIFIED:** `frontend/src/pages/AccountingJournalEntriesPage.test.tsx`
  — added `fetchJournalEntryTemplates` mock + `makeTemplate`
  fixture + 5 templates-section test cases.
- **MODIFIED:** `acceptance/journeys/office/accounting_je_create.spec.ts`
  — +1 blank-path regression test case.
- **MODIFIED:** `docs/CAPABILITY_MATRIX.md` — §7γ block
  updated with M28.2 row + M28 §3 deferrals; status flipped
  from "in progress" to "shipped".
- **MODIFIED:** `docs/roadmap/IMPLEMENTATION_ROADMAP.md` —
  new M28 section between M27 and §5 (Explicit non-goals).
- **MODIFIED:** `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  — regenerated with row 150 flipped `covered`.

## Streak accounting (post-SESSION_196)

- **Zero-drift permission-class streak: 27 → 28**
  consecutive milestones (M10 → M28). Both M28.1 endpoints
  (GET + POST via `@api_view(["GET","POST"])`) reuse
  `_M131_PERMS`; zero new permission classes evolved at
  M28.
- **Planning-time as-recommended streak: 7** unchanged
  through M28.2 (implementation-only, executing the M28.0
  locked plan). Historical run of 89 across M10 → M23
  preserved for the record.

## Durable lessons carried forward from M28.2

Consolidated in the M28 retrospective §5. New M28.2
additions:

- **NEW at M28.2** — *Playwright APIRequestContext does NOT
  auto-populate `X-CSRFToken` from the storage-state
  csrftoken cookie.* `postWithCsrf` helper pattern
  available at
  `acceptance/journeys/office/accounting_je_template.spec.ts`
  for future specs.
- **NEW at M28.2** — *Numeric input value pre-population may
  normalize trailing zeros* (`3500.00` → `3500` or preserved
  depending on browser). Playwright assertions on `<input
  type="number">` values should use regex when comparing to
  pre-formatted numeric strings.

## What SESSION_197 must do

Open M29 planning per the standard M-N.0 shape. Candidate
list surfaces at open per M28 retrospective §9:

**Elevated:**
- NEW O2 (row-5 public-fetch-helper regex refinement,
  M26/M27/M28 deferral).
- NEW O3 (rows-1–4 plain-string investigation).
- H (test-hygiene remediation — 3 shared-DB non-idempotent
  journeys, unchanged from M27.2 + M28.2).
- **NEW — Variable-amount templates** (would relax M28.1
  serializer's non-null `amount` constraint + add
  instantiation-prompt UI; zero DB migration; direct
  operator gain; recorded as intended payoff of M28 §5.b
  forward-compat design).
- NEW — Template edit / delete UI (mid-year edits or
  deactivate — currently `is_active` at DB layer only).

Gated / deferred / M28 §3 / M27 §3 / M25 §4 candidates all
carried forward as documented in the retrospective.

**Standing question for M29:** substrate-integrity path
(O2 + O3 M26-analogous) vs substrate-compound-value
continuation (variable-amount templates would be the next
operator-facing consumer of the M28.1 substrate).

## Non-goals for SESSION_197

- ❌ Do NOT ship any M28.2 refinements — M28 shipped as
  scoped.
- ❌ Do NOT modify M1–M28 shipped surface.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT open any M29 implementation increment (planning
  only).
- ❌ Do NOT skip the two architectural verifications
  performed at M28.0 open (variable-amount forward-compat +
  duplication analysis) — they were both correct; don't
  re-litigate.

## Coordination

- **Push posture:** M28 commits pushed at M28.2 close per
  §5.h coordinated-push rule (6 total: M28.0 planning +
  hash backfill + M28.1 substrate + hash backfill + M28.2
  close + hash backfill).
- **Awaits explicit user push confirmation** at M28.2 close
  per CLAUDE.md safety rules.
