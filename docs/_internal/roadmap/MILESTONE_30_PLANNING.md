---
title: "Milestone 30 — Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern)"
status: shipped
type: planning-memo
generated: 2026-08-04
generated_at_session: SESSION_200 (skeleton + expansion + all §5 locks)
shipped_at_session: SESSION_202 (M30.2 frontend + Playwright + close-out)
milestone: 30
milestone_name: "Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_28_PLANNING.md
  - docs/roadmap/MILESTONE_29_PLANNING.md
  - docs/roadmap/MILESTONE_29_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7δ
  - backend/dealer_ai/models.py (JournalEntryTemplate, JournalEntryTemplateLine)
  - backend/dealer_ai/services/accounting/template.py (list/get/create verbs)
  - backend/dealer_ai/services/accounting/journal.py (M13.1 posting service — unchanged)
  - backend/dealer_ai/views_accounting.py (M28.1 combined GET+POST endpoint)
  - backend/dealer_ai/urls.py (existing template URL — one row at #150 in M21 audit)
  - frontend/src/components/accounting/NewJournalEntryTemplateDialog.tsx (M28.2 + M29.2)
  - frontend/src/components/accounting/NewJournalEntryDialog.tsx (M27.2 + M28.2 + M29.2 additive lockedLines)
  - frontend/src/pages/AccountingJournalEntriesPage.tsx (M28.2 templates section + M29.2 handleInstantiate wiring)
  - frontend/src/lib/accountingApi.ts (M28.1 template wrappers)
  - acceptance/journeys/office/accounting_je_template.spec.ts (M28.2 + M29.2 variable-amount block)
---

# Milestone 30 — Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern)

> **Active planning memo.** Drafted + expanded + all §5 locks at
> SESSION_200 M30.0 open.
>
> **§5.a locked at open** as **NEW Template edit / delete UI**,
> under the *primary operational-coverage lens* that has governed
> §5.a selection since M22 close (durable), plus the *substrate-
> compound-value continuation* framing that first validated at
> M27.1 → M28.1 → M28.2 → M29 (now a fourth link on the M28+M29
> template surface). M30 completes the CRUD surface on the
> JournalEntryTemplate resource — the M28+M29 lineage shipped
> Create + Instantiate (fixed and variable); M30 ships Edit +
> Deactivate. The direct operator pain resolved: mid-year chart-
> of-accounts corrections currently require Django-shell access;
> stale templates accumulate silently with no operator surface
> for cleanup.
>
> **The anchor business question** — *Can a dealership accountant
> correct a stale journal-entry template (rename it, fix a wrong
> GL account or amount, add or remove a line) or deactivate one
> that no longer belongs, using the shipped application, without
> corrupting historical journal entries that were instantiated
> from it in prior periods?* — governs every M30 scope decision.
>
> **Two architectural verifications performed at M30.0 open** (per
> user direction, before locking §5.b):
>
> **(1) Dialog consolidation — CLEAN, additive-mode pattern
> chosen.** Inspection of `NewJournalEntryTemplateDialog.tsx`
> (500 lines) confirmed that the create dialog is a self-contained
> component with a baked-in `+ New template` trigger, internal
> state for name/description/lines, direct call to
> `createJournalEntryTemplate`, and ~200 lines of `TemplateLineRow`
> + validation + `TemplateBalanceIndicator` — logic that is 100%
> shared between create and edit. Spawning a parallel
> `EditJournalEntryTemplateDialog` would immediately create
> divergence risk on validation + balance math + variable-amount
> rendering (the durable lesson (t) that surfaced at M29.2 exists
> precisely to prevent this class of parallel-dialog drift). The
> shared-subcomponent alternative (extract `TemplateLineRow` +
> `TemplateBalanceIndicator` + validation hook + two thin dialog
> wrappers) was considered and rejected: two wrappers still
> diverge on trigger, submit endpoint, reset semantics, and
> success flow — larger surface change than a single additive
> `mode` prop. **Chosen:** in-place evolution of the existing
> dialog with additive optional props (`mode`, `initialTemplate`,
> `onEdited`, `renderTrigger`) — safe default `mode = "create"`
> + baked-in trigger preserves the M29.2 shape byte-identical.
> Rename `NewJournalEntryTemplateDialog.tsx` →
> `JournalEntryTemplateDialog.tsx` via `git mv` + import sweep in
> the same commit (per `DOC_GOVERNANCE.md` §5). Instantiate stays
> separate — the M29.2 pattern
> (`templateToInitialValues` + `templateToLockedLines` +
> `NewJournalEntryDialog(lockedLines=…)`) is a template →
> JournalEntry conversion, not a template mutation, and remains
> outside the dialog. See §5.b D2.
>
> **(2) Soft-delete integrity — CLEAN, all four operator-behavior
> criteria pass by construction.** Grepped across all
> `backend/dealer_ai/**/*.py` for `template_id`,
> `journal_entry_template`, `from_template`,
> `instantiate_from_template`, and any FK from
> `JournalEntry` → `JournalEntryTemplate`: **none exists**
> outside the template model file itself. M28.0 §5.b explicitly
> rejected fusing template and posting domains via an
> `is_template` flag; instantiation copies template values into a
> fresh `JournalEntry` and records no back-reference. Therefore
> setting `is_active = False` (or even hard-`DELETE`) on a
> template has **zero effect** on any existing journal entry,
> trial balance, snapshot, or JE list/detail — those surfaces
> read from `JournalEntry` + `JournalEntryLine` + `GLAccount` and
> touch no template row. `list_journal_entry_templates` already
> filters `is_active=True` by default
> (`services/accounting/template.py:263`) with a symmetric
> `include_inactive: bool = False` kwarg reserved for the
> future endpoint exposure that stays purely additive. See §5.b
> D5.

## 0.a Change log (implementation-time amendments)

Per M5–M28 §9 mandates, load-bearing planning decisions may
need narrow amendment at implementation time as substrate
reality asserts itself. Every amendment records the session,
option, and the affected sections.

### 0.a.1 · 2026-08-04 (SESSION_200) — M29 CI regression correction

**Trigger.** First M29 CI acceptance run (workflow ID
30919344101, commit `e01cfde` — "Record M29.2 commit hash in
SESSION_199 handoff frontmatter") turned red at
`journeys/office/accounting_je_template.spec.ts:213` — the
pre-existing M28.2 "owner can instantiate a template into a
balanced posting via the pre-populated JE dialog" journey.
Failure at line 295: `dialog.getByLabel("Line 1 debit")
.toHaveValue(/^1275(\.00)?$/)` — the aria-label resolved
to zero elements after M29.2's UI shape change on fixed
template lines.

**Root cause.** M29.2 replaced the amount cell for a fixed
(non-variable) template line at instantiate time from a
labeled `<Input aria-label="Line N debit">` to a read-only
`<LockedAmountChip>` (test-id `je-line-<i>-<side>-chip`,
aria-label `Line <i> <side> amount (from template)`). The
D8 M29.2 Playwright work added a fresh
`test.describe("variable-amount", ...)` block asserting on
the new chip shape but **did not sweep the pre-existing
M28.2 fixed-template assertion** (lines 295–300 of the same
spec file), which still called the old `getByLabel("Line 1
debit")` locator. Vitest + `tsc --noEmit` + frontend build
are structurally incapable of catching stale Playwright
locators (TypeScript sees `dialog.getByLabel("...")` as a
valid function call regardless of runtime DOM shape), so
the regression only surfaced on the M29 CI run.

**Fix scope.** Single-file test-assertion update in
`acceptance/journeys/office/accounting_je_template.spec.ts`
lines 291–306:

- Old (broken): `dialog.getByLabel("Line 1 debit")
  .toHaveValue(/^1275(\.00)?$/)` and companion for Line 2
  credit.
- New: `dialog.getByTestId("je-line-0-debit-chip")
  .toContainText(/\$1275\.00/)` and companion for Line 2.
- Added six-line comment documenting the M29.2 shape change
  + reference to this §0.a record.

**Verification performed at fix.**

1. **Reproduced the failure locally** with the fixed-set
   grep (`accounting_je_template.spec.ts --grep "pre-
   populated JE dialog"`) — confirmed the same error trace
   as CI (aria-label resolves to zero elements after M29.2).
2. **Verified the fix on the same isolated spec** — 7
   passed / 0 failed (Playwright's setup + persona-login
   projects auto-run alongside the target).
3. **Ran the full acceptance suite** on the pre-existing
   acceptance DB — 24 passed / 2 failed, with both failures
   in the known H (test-hygiene) shared-DB-state journeys
   (`sales_manager/daily_startup:76` "seededLead.assigned_to
   should be null" and `recon/workflow:59` "finding.decision
   should start with no decision"). Neither failure touches
   template/JE UI; both were caused by state left over from
   an earlier local test run (recon finding `decided_at:
   2026-08-04T03:17:30Z` pre-dated this session start).
4. **Reset the acceptance DB** (`rm backend/db.acceptance
   .sqlite3` — recreated by Playwright's `webServer` migrate
   step on next boot) and re-ran the full acceptance suite
   — **26 passed / 0 failed / 31.5s** confirming the fix is
   clean AND no other stale acceptance selectors depend on
   the M29.2 chip shape.
5. **Full-file grep across the acceptance suite** for
   `getByLabel\("Line \d+ (debit|credit)"\)` — only three
   remaining call sites, all correct-by-context:
   - `accounting_je_template.spec.ts:503–512` — inside the
     M29.2 variable-amount describe block, where the
     variable-side amount cell IS a normal `<Input>` (amber
     ring, not chip). Correct.
   - `accounting_je_create.spec.ts:147, 161, 264–267, 324`
     — M27.2 blank-entry journey, where no `lockedLines` is
     ever set and every amount cell is a normal `<Input>`.
     Correct.
   - Comment line at `accounting_je_template.spec.ts:298`
     — inside the new documentation comment added at the
     fix site. Reference only, not a live locator.

**M30 planning impact.**

- **Zero scope change.** The M30.0 target (Template edit /
  delete UI) and all §5 locks remain valid. This amendment
  is a scope-adjacent correction, not a re-litigation.
- **New anchor:** §7 (anchors that win on conflict) now
  cites the M29 retrospective §8 correction record for full
  traceability.
- **Streak effects at M30.0 close:**
  - Planning-time as-recommended streak: unchanged at 8 →
    projected **9** at M30.0 close (§0.a is a corrective
    amendment, not a scope selection).
  - Zero-drift permission-class streak: unchanged at 29
    (no code change to Django).
- **Durable lesson recorded** in M29 retrospective §5 as
  new principle: *"When changing the semantic shape of an
  established UI element, sweep the full acceptance suite
  for stale selectors + assertions on that element."*
  Mitigation for future milestones: any §5.b sub-decision
  that alters the DOM shape (chip ↔ input, badge ↔ button,
  hidden ↔ visible) of an element previously touched by
  Playwright must mandate a `grep` sweep across
  `acceptance/journeys/**/*.spec.ts` for stale locators on
  that element AND either update assertions in the same
  increment OR run the full acceptance suite locally
  before push.

**Deployment.** Per §0.a governance: local commits only,
coordinated push at M30 close — **overridden by user for
this amendment.** Rationale: `main` is red; restoring the
shipped-baseline green trumps the normal push cadence.
Amendment committed + pushed as a standalone correction;
subsequent M30 planning commits resume the coordinated-
push cadence.

**Sections affected.**

- New: this §0.a.1 subsection in `MILESTONE_30_PLANNING.md`.
- `MILESTONE_29_RETROSPECTIVE.md` §5 — new durable lesson
  entry.
- `MILESTONE_29_RETROSPECTIVE.md` §8 — new corrections
  entry cross-referencing this record.
- `acceptance/journeys/office/accounting_je_template.spec
  .ts` lines 291–306 — the actual fix.

## 1. Context

### 1.1 Why now

M28.1 shipped a `JournalEntryTemplate.is_active` boolean and the
model docstring explicitly reserved the flag for a future
operator-facing deactivate UI ("**Soft-hide reservation.**
`is_active` exists at the DB layer for future use — M28+
operator-facing deactivate UI is a §3 deferral" —
`models.py:7519`). M28.2 shipped Create + list; M29.2 shipped
variable-amount Instantiate. At M29 close no operator surface
exists for Edit or Deactivate — the only remedy for a stale
template is Django-shell access.

The M29 retrospective §9 elevated Template edit / delete UI as
the highest recommendation strength for M30, evaluated against
the primary operational-coverage lens (direct operator-facing
value: chart-of-accounts corrections are a recurring accounting-
operations pain point that currently forces DBA involvement).
The substrate-compound-value continuation lens *also* applies —
M30 becomes the fourth link on the M28+M29 template surface
(third increment on the same domain lineage).

Zero DB migration required: `is_active` column already exists.

### 1.2 What the operator gets

An accounting operator can:

1. **Edit** an existing template — click a row-level "Edit" link
   on the templates list; the dialog reopens in edit mode with
   name, description, and all lines pre-populated; correct any
   field; submit; the template row updates in place with a
   success indicator.
2. **Deactivate** a stale template — click a row-level "Delete"
   button; a confirmation dialog asks
   "Deactivate 'Monthly rent'? Historical journal entries
   created from this template are not affected. You can restore
   this template later." On confirm, the template disappears
   from the (active-only) list.
3. **Preserve history** — any journal entry previously
   instantiated from the deactivated template continues to
   render unchanged in the JE list, JE detail, trial balance,
   and snapshot surfaces. By construction (no FK), soft-delete
   cannot cascade.

### 1.3 What the operator does not get at M30

- **Restore / "Show inactive" toggle in the UI.** The
  `include_inactive=True` endpoint exposure remains an M28 §3
  deferral. M30 delivers Delete (deactivate) but not Restore —
  operators who need to un-hide a deactivated template still
  need Django-shell access in the interim. Rationale: shipping
  the correction path first is the primary operator value; the
  restore-inactive UX is a follow-up when operator evidence
  demands it.
- **Hard delete.** DELETE endpoint sets `is_active = False`
  (soft-delete). Hard-delete would risk `PROTECT` cascade on
  `JournalEntryTemplateLine.account` and complicates future
  restore. No operator evidence supports hard-delete.
- **Bulk delete or bulk edit.** No operator evidence supports.
- **Audit trail on template mutations** (who edited what,
  when). No `edited_by_user` field, no history rows. The M28
  `updated_at` auto-now field already exists; deferred as an
  M30 §3 item pending operator evidence.
- **Standalone template detail page** (M28 §3 deferral,
  unchanged).
- **Server-side template search / pagination** (M28 §3
  deferral, unchanged).

## 2. Increment structure

Two-increment structure, following the M27 / M28 / M29 pattern:

- **M30.1 — Backend substrate** (SESSION_201): add
  `admin/accounting/journal-entry-templates/<int:pk>/` detail
  endpoint supporting PATCH (full-replace of name/description/
  lines) + DELETE (soft — sets `is_active = False`). Add
  `update_journal_entry_template` + `delete_journal_entry_template`
  service verbs. Add `include_inactive: bool = False` kwarg to
  `get_journal_entry_template` mirroring the list function's
  signature. Extended endpoint / service / model tests. Frontend
  + acceptance untouched. **DoD exception path invoked as fifth
  precedent** (M26 + M27.1 + M28.1 + M29.1 + M30.1) — pattern
  well-established.
- **M30.2 — Frontend + Playwright** (SESSION_202): rename
  `NewJournalEntryTemplateDialog.tsx` →
  `JournalEntryTemplateDialog.tsx` via `git mv` + import sweep
  in the same commit; add additive `mode` / `initialTemplate` /
  `onEdited` / `renderTrigger` props; row-level Edit + Delete
  buttons on the templates section; delete confirmation dialog
  with the mandated operator-reassurance copy; wire the
  `AccountingJournalEntriesPage` consumer; extend vitests + one
  new `test.describe("edit-delete", ...)` block in the existing
  `accounting_je_template.spec.ts`. **DoD satisfied directly**;
  no exception path.

Two-source agreement gate at each increment close (M26.1 durable
lesson): audit artifact regeneration must reconcile with the
endpoint diff before the increment is declared shipped.

## 3. Deferrals (all valid for later re-entry)

Carried forward from M29 §3, M28 §3, M27 §3, M25 §4 — unchanged.

New at M30:

- **Restore / "Show inactive" UI toggle.** Endpoint exposure
  (`?include_inactive=true`) remains an M28 §3 deferral. M30
  ships the deactivate path but not the un-hide path; when
  operator evidence supports the restore UX, add a "Show
  inactive" toggle to the templates section and pass through
  the query param.
- **Hard-delete escape hatch.** No operator surface for hard
  DELETE at M30. If a pilot surfaces the need (e.g., accidentally
  created template that must be truly purged, not soft-hidden),
  add a separate `?hard=true` query param and a distinct
  "Delete permanently" confirmation with strong wording. Not
  in M30 scope.
- **Template mutation audit trail.** `edited_by_user` field on
  `JournalEntryTemplate` + a history model (or use the existing
  audit-events surface). Deferred pending operator evidence
  during pilot.
- **Optimistic concurrency control on edit** (e.g., ETag /
  `updated_at` check). Deferred — single-operator MVP means
  concurrent edits are architecturally impossible at M30.
  Revisit when M (multi-operator support) unblocks.
- **Bulk delete / bulk edit.** Deferred pending operator
  evidence.

## 4. Verifications performed at planning-open

Per the M24–M29 durable lessons carried into M30 (from the M29
retrospective §5 + `00-START-NEXT-SESSION.md` §7 + the two
architectural verifications the user directed at M30.0 open).

### 4.1 Substrate verification

- ✅ **Model schema:** `JournalEntryTemplate.is_active =
  BooleanField(default=True)` confirmed at `models.py:7532`.
  Zero DB migration required for M30.
- ✅ **Model docstring** (`models.py:7519`): "**Soft-hide
  reservation.** `is_active` exists at the DB layer for future
  use (M28+ operator-facing deactivate UI is a §3 deferral).
  At M28 the `list_journal_entry_templates` service filters
  `is_active=True` by default." M30 spends what M28.1 reserved.
- ✅ **Service list filter** (`services/accounting/template.py:
  263`): `list_journal_entry_templates` already applies
  `is_active=True` by default with a symmetric
  `include_inactive: bool = False` kwarg. Endpoint calls
  without the kwarg (`views_accounting.py:832`). Frontend hits
  this endpoint. Zero refactor to the read path.
- ✅ **Service get** (`services/accounting/template.py:267`):
  `get_journal_entry_template(*, pk, dealership)` currently
  does NOT filter on `is_active`. Add `include_inactive: bool
  = False` kwarg at M30.1 for symmetry; default False means
  the future edit-mode fetch path (if one is ever added) will
  fail-closed on inactive templates unless the view opts in.
  Additive change; zero effect on existing callers.
- ✅ **M13.1 posting path unchanged.** Edit and Delete do NOT
  touch `JournalEntry` — templates are recipes, postings are
  postings, no back-reference exists.

### 4.2 FK / input discoverability (M27.0 durable lesson)

- ✅ **No new FKs introduced.** Edit + Delete operate on the
  existing `JournalEntryTemplate` row.
- ✅ **Edit dialog inputs discoverable via list row.** The
  templates section (M28.2) already renders one row per
  template. M30.2 attaches Edit + Delete buttons to each row;
  discoverability is unambiguous.
- ✅ **Delete confirmation copy mandated by D3** (see §5.b).
  Operators cannot accidentally soft-delete a template
  without seeing the "historical entries not affected" +
  "can be restored later" reassurance.

### 4.3 Downstream UI verification (M24.1 + SESSION_189/190 durable lesson)

- ✅ **JE list page:** `AccountingJournalEntriesPage`
  displays posted JEs regardless of template `is_active`
  state — by construction (no FK from JE to template). Grep
  confirmed no template reference in
  `services/accounting/journal.py` or the JE view/serializer.
- ✅ **JE detail page:** identical for JEs whose source
  template is active vs deactivated vs deleted vs never
  existed — no divergence at data model.
- ✅ **Trial balance / snapshot:** read from
  `JournalEntryLine` + `GLAccount`; template deactivation
  invisible.
- ✅ **Templates section on `AccountingJournalEntriesPage`:**
  the M28.2 rendering already respects the active-only
  filter (fetches via `fetchJournalEntryTemplates` →
  `list_journal_entry_templates(is_active=True)`). Deactivated
  templates disappear from the list automatically — no
  frontend filter code needed.

### 4.4 Audit-substrate verification (M26.1 durable lesson)

- **One new endpoint at M30.1:**
  `admin/accounting/journal-entry-templates/<int:pk>/`
  supporting `PATCH` + `DELETE`. M21 audit counts one row per
  URL pattern (not per verb), so this is +1 endpoint.
- **Coverage delta at M30.2 close:**
  - Backend endpoints: **156 → 157** (+1).
  - Covered: **122 → 123** (+1 — the new detail endpoint gets
    two frontend wrappers, `updateJournalEntryTemplate` and
    `deleteJournalEntryTemplate`, but the endpoint counts as
    one covered row).
  - Backend-only: **34** (unchanged).
- Two-source agreement gate at M30.2 close: regenerate audit
  artifact + reconcile with the endpoint diff + confirm
  frontend wrapper listing catches both PATCH and DELETE
  callsites.

### 4.5 Implementation-boundary verification

- ✅ **Existing dialog reuse posture** (see §4.6 for the
  detailed architectural verification the user directed at
  open): `NewJournalEntryTemplateDialog` inspected line by
  line; state, trigger, and validation logic are amenable to
  additive-mode evolution without a rewrite.

### 4.6 Dialog consolidation architectural verification (user-directed at M30.0 open)

**Question posed by user at SESSION_200 §5.b lock request:**
Should `NewJournalEntryTemplateDialog` evolve into a shared
`JournalEntryTemplateDialog` operating in create/edit modes,
with instantiation as a separate consumer that converts a
template into `NewJournalEntryDialog` initial values? Goal:
avoid parallel dialog implementations that slowly diverge
over M30+.

**Inspection performed** (`git ls-files | grep Template`):

- `NewJournalEntryTemplateDialog.tsx` — 513 lines. Contains:
  - **Baked-in trigger button** at lines 224–232
    (`+ New template` button with `data-testid="tmpl-create-
    trigger"` — create-specific but generalizable via a
    `renderTrigger` slot).
  - **Internal state** for name / description / lines (lines
    98–106). Fully local; no external state control.
  - **Validation surface** (lines 108–158 — nameInvalid,
    descriptionInvalid, hasInvalidNumber, missingAccount,
    missingAmount, hasVariableLine, balanceDelta, isBalanced,
    canSubmit). ~50 lines. **Would be pure duplication if
    forked into an edit dialog.**
  - **`TemplateLineRow`** subcomponent (lines 344–460, ~117
    lines). Renders the GL account picker, side, amount, and
    variable checkbox for one line. **Would be pure
    duplication if forked.**
  - **`TemplateBalanceIndicator`** (lines 463–512, ~50 lines).
    **Would be pure duplication if forked.**
  - **`handleSubmit`** (lines 191–214) — calls
    `createJournalEntryTemplate` directly. This is the ONE
    branch that must differ per mode (create → POST,
    edit → PATCH).

**Three patterns considered:**

**Pattern A — Additive-mode props on the existing component
(in-place evolution).** Add `mode?: "create" | "edit"`
(default `"create"`), `initialTemplate?: JournalEntryTemplate`
(edit only), `onEdited?: (template) => void` (edit only),
`renderTrigger?: (open) => ReactNode` (optional; edit passes
custom row-menu trigger). Blank baseline (create + baked-in
trigger + no initialTemplate) is byte-identical to M29.2. The
`handleSubmit` branches by mode: create → `create…`, edit →
`update…`. Validation, balance math, `TemplateLineRow`,
`TemplateBalanceIndicator` are all shared verbatim.

**Pattern B — Extract shared subcomponents, keep two dialog
wrappers.** Move `TemplateLineRow`, `TemplateBalanceIndicator`,
and a `useTemplateFormState` hook into a shared module; write
`NewJournalEntryTemplateDialog.tsx` (create only) and
`EditJournalEntryTemplateDialog.tsx` (edit only) as thin
wrappers. Larger PR surface. Two dialog shells still diverge
on trigger, submit, reset, and success flow.

**Pattern C — Fork into `EditJournalEntryTemplateDialog.tsx`
with full duplication of the 200+ shared lines.** Maximum
divergence risk. Explicitly the failure mode that M29.2
durable lesson (t) — the *additive-prop pattern for UI reuse*
— exists to prevent.

**Chosen: Pattern A.** Rationale:

1. **Direct application of M29.2 durable lesson (t).** The
   lesson (t) — *"prefer additive optional prop with safe
   default over thin wrapper when divergent UI must render
   inside an existing cell"* — surfaced at M29.2 for
   `NewJournalEntryDialog.lockedLines`. M30 applies the same
   lesson to `JournalEntryTemplateDialog.mode` — the same
   reasoning, the same milestone lineage, the same test-suite
   preservation.
2. **Smallest blast radius.** One file renamed + one commit
   for the rename + import sweep + a modest set of additive
   prop definitions + a mode branch inside `handleSubmit`.
   Under 50 lines of diff outside the file.
3. **Preserves existing test suite.** The current
   `NewJournalEntryTemplateDialog.test.tsx` (17 tests) is
   renamed alongside the component and all cases continue to
   pass unchanged — they test create-mode with no
   initialTemplate, which is exactly the safe-default path.
4. **Extensible for future modes.** If a future milestone
   wants to add "Duplicate template" (copy of an existing
   template as a starting point for a new one), a
   `mode: "duplicate"` addition is a small extension of the
   same pattern.

**Rename mechanics** (per `DOC_GOVERNANCE.md` §5):
`git mv frontend/src/components/accounting/NewJournalEntryTemplateDialog.tsx
frontend/src/components/accounting/JournalEntryTemplateDialog.tsx`
+ rename the sibling `.test.tsx` + sweep every import via
`grep -rn "NewJournalEntryTemplateDialog" frontend/ acceptance/`
in the **same commit** as the rename. No test-id or class-name
churn — the `data-testid="tmpl-create-trigger"` becomes
`data-testid="tmpl-create-trigger"` still (create-mode default)
with a parallel `data-testid="tmpl-edit-trigger-<pk>"` from
each list row's edit button.

**Instantiate stays separate — explicit design decision.**
Instantiation is a template → `JournalEntry` conversion, not
a mutation of the template. The M29.2 pattern
(`templateToInitialValues` + `templateToLockedLines` +
`NewJournalEntryDialog` with `lockedLines`) already correctly
models this: `AccountingJournalEntriesPage` is a *consumer*
of the template. Folding instantiate into the template dialog
would either (a) confuse two domains (recipe vs posting) that
M28.0 §5.b explicitly kept separate, or (b) require the
template dialog to know how to post journal entries, violating
the M13.1 single-posting-path contract. Instantiate stays
where it is: `handleInstantiate` on
`AccountingJournalEntriesPage`, wiring to
`NewJournalEntryDialog`.

### 4.7 Soft-delete integrity architectural verification (user-directed at M30.0 open)

**Question posed by user at SESSION_200 §5.b lock request:**
Does `is_active = false` produce the correct operator behavior
everywhere? Specifically:

- inactive templates disappear from normal lists
- existing journal entries instantiated from them remain unchanged
- historical reporting remains intact
- future `include_inactive` support remains additive rather than
  requiring refactoring

**Grep sweep performed** to establish the FK topology between
`JournalEntry` and `JournalEntryTemplate`:

```bash
grep -rn 'template_id\|journal_entry_template\|from_template\|instantiate_from_template' \
     backend/dealer_ai/**/*.py
```

Result: no back-reference from any `JournalEntry`-adjacent code
to `JournalEntryTemplate` outside the template model file and
its test files. Instantiation is a client-side value copy — the
frontend's `templateToInitialValues` copies template fields into
the JE dialog's initial state, and the resulting JE row has no
`source_template_id`, no `template` FK, no back-reference at all.
This was M28.0 §5.b's explicit choice (documented in
`models.py:7504`): "Recipes and postings are different domain
concepts. Fusing this into `JournalEntry` via an `is_template`
flag was rejected."

**Four criteria evaluated:**

**(a) Inactive templates disappear from normal lists.** ✅

- `list_journal_entry_templates(*, dealership, include_inactive
  = False)` at `services/accounting/template.py:252` filters
  `is_active=True` when `include_inactive` is False.
- `admin_journal_entry_template_list_or_create` at
  `views_accounting.py:832` calls the service without the
  `include_inactive` kwarg — so the default False applies.
- Frontend `fetchJournalEntryTemplates` hits this endpoint.
- **Consequence:** the moment a template's `is_active` flips to
  False, it disappears from the operator list on the next
  refetch. Zero-effort by construction.

**(b) Existing JEs instantiated from them remain unchanged.**
✅

- **No FK exists** from `JournalEntry` to
  `JournalEntryTemplate`. Grep confirmed. M28.0 §5.b rejected
  fusion. Instantiation copies field values into a fresh
  `JournalEntry` row via the frontend `templateToInitialValues`
  helper + the M13.1 posting service.
- **Consequence:** setting `template.is_active = False` (or
  hard-deleting the template via a future `?hard=true` escape
  hatch) cannot cascade to any `JournalEntry` row. Historical
  entries continue to render with their original description,
  posted_at, lines, and amounts.

**(c) Historical reporting remains intact.** ✅

- Trial balance (`services/accounting/…compute_trial_balance`)
  reads from `JournalEntryLine` + `GLAccount`. No template
  dependency.
- Trial balance snapshots (M17.1 `TrialBalanceSnapshot` +
  `TrialBalanceSnapshotRow`) are materialized from the same
  join. No template dependency.
- JE list (`fetch_journal_entries`) reads from `JournalEntry`
  + `JournalEntryLine` + `GLAccount`. No template dependency.
- JE detail (M14.4 detail view) reads from the same tables.
  No template dependency.
- Reversal chain (M14.3) tracks `reverses_entry_id` on
  `JournalEntry` — internal to the JE domain, unrelated to
  templates.
- **Consequence:** historical reporting is completely immune
  to template lifecycle changes.

**(d) Future `include_inactive` support remains additive.** ✅

- `list_journal_entry_templates` already accepts
  `include_inactive: bool = False`. Future
  `?include_inactive=true` query-param endpoint exposure is a
  one-line view-layer passthrough:
  `include_inactive = request.query_params.get("include_inactive",
  "false").lower() == "true"` → pass to service. Zero refactor.
- `_project_template` already projects the `is_active` field
  (`views_accounting.py:780`). The client can filter or badge
  inactive rows visually without needing another endpoint.
- **M30.1 adds symmetric kwarg on `get_journal_entry_template`**
  for API consistency: `def get_journal_entry_template(*, pk,
  dealership, include_inactive: bool = False)`. Additive change
  — existing callers get the same semantics; a future
  edit-mode-fetch view would opt-in.

**One subtle recommendation surfaced from the verification:**
delete UI copy must be explicit about the soft-delete
semantics. Operators must not think they are permanently
destroying a template + all its history. Locked at §5.b D3:
"Deactivate 'Monthly rent'? Historical journal entries created
from this template are not affected. You can restore this
template later." The word "Delete" (which implies permanence)
is intentionally NOT used in the confirmation copy; the row-
level button uses "Delete" for concision + operator vocabulary
convention, but the confirmation dialog uses "Deactivate" for
truth.

## 5. Load-bearing decisions (all locked at M30.0)

### 5.a Target selection (locked at open)

**NEW Template edit / delete UI.** Recommendation grounded in
the primary operational-coverage lens (mid-year chart-of-
accounts corrections and stale-template cleanup are recurring
accounting-operations pain points that currently force
Django-shell access — the operator-visible failure mode is
"I need IT to fix my template") plus the substrate-compound-
value continuation framing (fourth link on the M28+M29
template lineage — Create + Instantiate shipped, Edit +
Deactivate complete the CRUD surface). Alternatives (NEW C
F&I chargeback substrate, NEW O2 / O3 audit refinement,
H test-hygiene remediation) evaluated and passed at §5.a
selection.

Deferred candidates unchanged:

- **NEW C — F&I chargeback substrate:** attractive as a
  fourth substrate-compound-value link, but the M29
  retrospective §9 gates it on "operator evidence surfaces
  during a pilot" — no pilot is in flight, evidence bar not
  met. Re-evaluate when T or L unblocks.
- **NEW O2 + O3 combined:** would be the M26-analogous
  substrate-integrity milestone. Compelling infrastructure
  gain but zero operator-facing surface and blast radius
  unknown at open. Better deferred until an operator-facing
  candidate isn't obviously ripe.
- **H — test-hygiene remediation:** compounds well but doesn't
  ship operator value. Fold into a larger milestone as in-
  flight tax when opportunity arises.

### 5.b Design decisions (D1–D8)

#### D1 · Backend endpoints — one new detail URL supporting PATCH + DELETE

- **New URL pattern:**
  `admin/accounting/journal-entry-templates/<int:pk>/` →
  `views_accounting.admin_journal_entry_template_detail`,
  `url_name = "admin-journal-entry-template-detail"`.
- **Supported verbs:** `PATCH` (full edit — name, description,
  lines) + `DELETE` (soft — sets `is_active = False`). No
  `GET` at M30 — the edit-mode dialog populates from the
  template row already loaded via `fetchJournalEntryTemplates`
  in the list response (`_project_template` already includes
  all fields including lines).
- **PATCH request body:** identical shape to the M28.1 create
  request payload (`JournalEntryTemplateCreateRequestSerializer`
  — reuse it as `…UpdateRequestSerializer` or reuse the same
  serializer verbatim, since the field validation is
  identical). Lines are **full-replace, not partial patch** —
  the operator resubmits the entire lines array. Rationale:
  template lines are a small ordered set (typically 2–5); a
  partial line patch adds serializer surface without operator
  value and risks silent line-ID reuse bugs.
- **DELETE request body:** empty. Response 204 with empty
  body. **Idempotent:** DELETE of an already-inactive template
  returns 204 (no error). Rationale: operators may double-
  click; the second click should not error.
- **Response projections** (PATCH and DELETE):
  - PATCH: full `_project_template(template)` projection
    (name, description, lines[], is_active, created_at,
    updated_at). `updated_at` will have advanced (auto-now
    field).
  - DELETE: 204 no body.
- **Cross-tenant guard:** both PATCH and DELETE fetch the
  template via `get_journal_entry_template(pk=pk,
  dealership=dealership, include_inactive=True)` — pass
  `include_inactive=True` so the deactivate → reactivate
  future path can find the row. Cross-tenant fetch returns
  `None` → 404. Same tenant + inactive template on DELETE
  → 204 idempotent (no state change).
- **Error mapping:**
  - Template not found or cross-tenant → 404.
  - PATCH with invalid payload (missing account, unbalanced
    populated portion, etc.) → 400 with the same error
    classes as M28.1 create (`EmptyJournalEntryTemplateError`,
    `InvalidJournalEntryTemplateLineError`,
    `UnbalancedJournalEntryTemplateError`).
  - PATCH with name collision inside the same tenant →
    409 (`DuplicateJournalEntryTemplateNameError`, reused
    from M28.1 create).

#### D2 · Frontend dialog consolidation — additive-mode pattern (locked)

**Implementation boundary (locked at §5.b, verified in §4.6).**

Rename `NewJournalEntryTemplateDialog.tsx` →
`JournalEntryTemplateDialog.tsx` via `git mv` + import sweep
in the same commit. Add the following additive optional props
with safe defaults:

```ts
export interface JournalEntryTemplateDialogProps {
  accounts: GLAccount[];
  disabled?: boolean;
  /** Default "create" — preserves M29.2 behavior byte-identical.
   *  Set to "edit" from row-level Edit trigger. */
  mode?: "create" | "edit";
  /** Required when mode === "edit". Populates the form fields
   *  on open. Ignored (undefined) when mode === "create". */
  initialTemplate?: JournalEntryTemplate;
  /** Called after successful create. Existing prop. */
  onCreated?: (template: JournalEntryTemplate) => void;
  /** Called after successful edit. Required when mode === "edit". */
  onEdited?: (template: JournalEntryTemplate) => void;
  /** Optional custom trigger renderer. When undefined, the
   *  baked-in "+ New template" button is used (create-mode
   *  default). Edit-mode passes a row-scoped pencil-icon
   *  button. Signature: (open) => ReactNode where the caller
   *  calls open() to open the dialog. */
  renderTrigger?: (open: () => void) => ReactNode;
}
```

**Behavior branches:**

- **`mode === "create"` (default):** all state initialized
  empty (existing behavior). `handleSubmit` calls
  `createJournalEntryTemplate`. Baked-in trigger renders
  unless `renderTrigger` is passed. `onCreated` fires on
  success.
- **`mode === "edit"`:** on open transition, populate
  `name` / `description` / `lines` from `initialTemplate` via
  a helper `templateToDraftLines(initialTemplate)`.
  `handleSubmit` calls `updateJournalEntryTemplate(pk, payload)`.
  `renderTrigger` is required (passed from the row).
  `onEdited` fires on success. Dialog title changes to
  "Edit template" and submit-button label to "Save changes".

**Reset guarantee** (per M29.2 durable lesson (u) — reset every
override / annotation state in every reset path):

The existing `reset()` function (lines 160–169) clears name /
description / lines / error / submitting. Extend to also
reset any edit-mode-specific state (there is none beyond the
form fields — good). Additional reset triggers:

1. **Dialog open false → true transition** (existing
   `onOpenChange` in `Dialog`): the `useEffect` (to be added)
   watches `[open, initialTemplate, mode]` and re-runs
   population when open flips true or `initialTemplate` /
   `mode` change.
2. **`initialTemplate` reference change while open:** covered
   by the same dep array.
3. **`mode` change while open** (theoretical — should not
   happen in practice, but the dep array protects against it).
4. **`onOpenChange(false)`** (existing behavior at lines
   219–222): calls `reset()`.

**Test-id conventions:**

- `data-testid="tmpl-create-trigger"` — create-mode baked-in
  trigger (unchanged from M29.2).
- `data-testid="tmpl-edit-trigger-<pk>"` — edit-mode row
  trigger (new).
- `data-testid="tmpl-create-submit"` — create-mode submit
  (unchanged).
- `data-testid="tmpl-edit-submit"` — edit-mode submit (new).
- `data-testid="tmpl-dialog-title"` — dialog title, values
  "New recurring template" vs "Edit template" (used by
  vitests to assert mode).

**Regression guard:** the renamed
`JournalEntryTemplateDialog.test.tsx` (was
`NewJournalEntryTemplateDialog.test.tsx`) continues to run all
17 existing create-mode tests unchanged. Any test that
constructs the dialog without `mode` or `initialTemplate`
exercises the safe-default create path — byte-identical to
M29.2.

#### D3 · Delete UI — row-level button + confirmation dialog (locked)

**Row-level Delete button on each template row.** Placement:
alongside the existing Instantiate button; label "Delete"
(operator vocabulary — familiar); `data-testid="tmpl-delete-
trigger-<pk>"`; variant `outline`; icon `TrashIcon` (from
lucide-react, already used elsewhere in the frontend).

**Confirmation dialog** — a shadcn `AlertDialog` (or Dialog +
overlay if AlertDialog is not yet imported). Copy:

```
Title:  Deactivate template?
Body:   Are you sure you want to deactivate "Monthly rent"?

        Historical journal entries created from this template
        are not affected — they remain unchanged in the
        Journal Entries list and in trial balance reports.

        You can restore this template later. (Restore UX
        ships in a future milestone.)
Footer: [ Cancel ]   [ Deactivate ] (destructive variant)
```

**Explicit design constraint** (locked at §5.b D3, surfaced
during the §4.7 verification): the confirmation title and
button use "Deactivate" (truth) even though the row button
uses "Delete" (vocabulary). This asymmetry is deliberate —
"Delete" is a familiar row-action label; the confirmation
must correct the operator's mental model before they commit.

**On confirm:** call `deleteJournalEntryTemplate(pk)` →
`DELETE /admin/accounting/journal-entry-templates/<pk>/`;
bump `templatesReloadTick` on success (template disappears
from the active-only list); optionally show a small success
badge "Template deactivated" in the templates section header
for ~3 seconds (reuse the M25.2 success-badge pattern already
used for `lastCreatedTemplate`).

**Error handling:** if DELETE returns 404 (template already
gone, race condition), treat as success — the template is
gone from the operator's perspective. If DELETE returns 5xx,
surface as inline error banner in the confirmation dialog
with retry button.

**Idempotent semantics documented in operator-facing copy:**
none — operators don't need to know about idempotency at the
UI level. The backend simply doesn't error on
already-inactive DELETE.

#### D4 · Edit UI — row-level Edit button + dialog in edit mode (locked)

**Row-level Edit button on each template row.** Placement:
alongside Instantiate and Delete; label "Edit";
`data-testid="tmpl-edit-trigger-<pk>"`; variant `outline`;
icon `PencilIcon`.

**On click:** open `JournalEntryTemplateDialog` with
`mode="edit"`, `initialTemplate={template}`,
`onEdited={handleEdited}`, `renderTrigger={(open) => null}`
(the row button *is* the trigger — pass a no-op renderer so
the dialog doesn't render its own baked-in trigger; the row
click programmatically opens the dialog via a controlled
`open` state, mirroring the M29.2 instantiate wiring).

Actually — cleaner pattern: instead of passing
`renderTrigger`, use a *controlled-open* prop. Let me refine:

**Refinement — controlled-open pattern** (aligns with the
M28.2 `NewJournalEntryDialog` controlled-open pattern):

Add an optional `open?: boolean` + `onOpenChange?: (open:
boolean) => void` prop pair. When both supplied, the dialog
is fully controlled (no baked-in trigger renders). When
absent, the baked-in `+ New template` button renders and
controls open state internally (M29.2 behavior).

This drops the `renderTrigger` prop and matches the
`NewJournalEntryDialog(open, onOpenChange)` shape shipped
at M28.2. Simpler, one existing pattern reused.

**Updated prop signature (superseding D2):**

```ts
export interface JournalEntryTemplateDialogProps {
  accounts: GLAccount[];
  disabled?: boolean;

  /** Default "create" — preserves M29.2 behavior byte-identical. */
  mode?: "create" | "edit";
  /** Required when mode === "edit". */
  initialTemplate?: JournalEntryTemplate;

  onCreated?: (template: JournalEntryTemplate) => void;
  onEdited?: (template: JournalEntryTemplate) => void;

  /** Controlled-open: when both open + onOpenChange are supplied,
   *  the baked-in trigger button is NOT rendered and the parent
   *  controls open state. When absent (M29.2 default), the
   *  baked-in "+ New template" button renders. */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}
```

**Edit-mode wiring in `AccountingJournalEntriesPage`:**

```ts
const [editingTemplate, setEditingTemplate] =
  useState<JournalEntryTemplate | null>(null);
const editDialogOpen = editingTemplate !== null;

function handleEditClick(template: JournalEntryTemplate) {
  setEditingTemplate(template);
}
function handleEditDialogOpenChange(open: boolean) {
  if (!open) setEditingTemplate(null);
}
function handleEdited(template: JournalEntryTemplate) {
  setLastEditedTemplate(template);
  setEditingTemplate(null);
  setTemplatesReloadTick((tick) => tick + 1);
}

// Render:
{editingTemplate && (
  <JournalEntryTemplateDialog
    accounts={accounts}
    mode="edit"
    initialTemplate={editingTemplate}
    onEdited={handleEdited}
    open={editDialogOpen}
    onOpenChange={handleEditDialogOpenChange}
  />
)}
```

The create-mode `<JournalEntryTemplateDialog />` continues to
render standalone (with its baked-in trigger) at the section
header. The edit-mode instance mounts conditionally, keyed by
the template being edited (so opening a different template
after closing the first remounts cleanly).

#### D5 · Soft-delete integrity — no FK, no cascade (locked)

Documented in full in §4.7. Summary:

- **No FK from `JournalEntry` to `JournalEntryTemplate`** —
  verified by grep across `backend/dealer_ai/**/*.py`.
- **Historical JEs are immune** by construction to template
  lifecycle changes (deactivate, hard-delete, edit-that-
  changes-line-accounts) — the JE row is a snapshot copy,
  not a reference.
- **`list_journal_entry_templates` filters `is_active=True`
  by default** — inactive templates disappear from the
  operator list on next refetch.
- **`include_inactive` future exposure stays additive** —
  one-line view-layer passthrough; service kwarg already
  exists; `get_journal_entry_template` gets the symmetric
  kwarg at M30.1.
- **DELETE semantics soft** — sets `is_active = False`,
  preserves the row + all lines + all cross-tenant guards.
  A future hard-delete escape hatch (`?hard=true` query
  param) is deferred (M30 §3).

**One trap to avoid at M30.1:** the PATCH endpoint must NOT
accept `is_active` in the request body. Editing does not
change activation — deactivate is a separate DELETE verb.
Reactivate is intentionally not exposed at M30 (deferred
Restore UX). Serializer validation must reject `is_active`
in PATCH payloads (or silently drop it — decision below).

**Decision:** silently ignore `is_active` in PATCH payloads
(field is not defined on `JournalEntryTemplateUpdateRequestSerializer`).
Rejecting with 400 would surface a poor error to a future
developer who forgets — silent ignore is defensive without
being punitive. Backend service always preserves the current
`is_active` value on PATCH.

#### D6 · Backend test surface additions

- **New file** `test_m30_journal_entry_template_edit_delete_service.py`
  (~14 tests):
  - `test_update_journal_entry_template_happy_path`
  - `test_update_replaces_lines_fully`
  - `test_update_preserves_is_active_true`
  - `test_update_preserves_is_active_false`
  - `test_update_preserves_created_at`
  - `test_update_advances_updated_at`
  - `test_update_cross_tenant_returns_none`
  - `test_update_rejects_negative_amount_line`
  - `test_update_rejects_populated_imbalance`
  - `test_update_accepts_variable_lines` (M29 regression)
  - `test_delete_soft_flips_is_active_false`
  - `test_delete_already_inactive_idempotent`
  - `test_delete_cross_tenant_returns_none`
  - `test_get_journal_entry_template_include_inactive_kwarg`
- **Extension** of `test_m28_journal_entry_template_endpoint.py`
  (~7 tests):
  - `test_patch_returns_200_with_updated_projection`
  - `test_patch_full_replace_lines`
  - `test_patch_cross_tenant_returns_404`
  - `test_patch_invalid_payload_returns_400`
  - `test_patch_duplicate_name_returns_409`
  - `test_delete_returns_204`
  - `test_delete_cross_tenant_returns_404`
  - `test_delete_already_inactive_returns_204_idempotent`
  - `test_patch_silently_ignores_is_active_in_body`
- **Extension** of `test_m28_journal_entry_template_model.py`
  (~1 test): assert `updated_at` is auto-now on save (already
  covered indirectly — a defensive assertion).
- **Instantiate flow needs no new backend tests** — reuses
  M13.1 posting-service coverage. Edit does not touch
  posting.
- **Expected backend baseline:** 4,871 → ~4,893 (+~22).

#### D7 · Frontend test surface additions

- **Rename** `NewJournalEntryTemplateDialog.test.tsx` →
  `JournalEntryTemplateDialog.test.tsx` in the same commit as
  the component rename. All 17 existing create-mode tests
  continue to pass unchanged (regression guard for the safe-
  default create path).
- **Extension** (~8 tests):
  - `test_edit_mode_populates_from_initialTemplate`
  - `test_edit_mode_submit_calls_updateJournalEntryTemplate`
  - `test_edit_mode_submit_success_fires_onEdited`
  - `test_edit_mode_dialog_title_reads_Edit_template`
  - `test_edit_mode_submit_button_reads_Save_changes`
  - `test_edit_mode_controlled_open_state`
  - `test_edit_mode_reset_on_close`
  - `test_edit_mode_error_surfaces_inline`
- **`AccountingJournalEntriesPage.test.tsx`** extension
  (~5 tests):
  - `test_template_row_renders_edit_button`
  - `test_template_row_renders_delete_button`
  - `test_edit_button_click_opens_dialog_in_edit_mode`
  - `test_delete_button_click_opens_confirmation_dialog`
  - `test_delete_confirm_calls_deleteJournalEntryTemplate_and_refetches`
- **`accountingApi.templates.test.ts`** extension (~4 tests):
  - `test_updateJournalEntryTemplate_serializes_payload_correctly`
  - `test_updateJournalEntryTemplate_returns_projection`
  - `test_deleteJournalEntryTemplate_hits_correct_url`
  - `test_deleteJournalEntryTemplate_treats_404_as_success`
- **Delete confirmation dialog** — new small component
  `TemplateDeleteConfirmDialog` OR inline in
  `AccountingJournalEntriesPage`. Decision: inline (small,
  page-scoped state). ~1 additional test on the page.
- **Expected frontend baseline:** 282 → ~300 (+~18).

#### D8 · Playwright journey — single combined `test.describe` block (locked)

**Extend** `accounting_je_template.spec.ts` with **one new
`test.describe("edit-delete", ...)` block** containing a
single end-to-end journey covering both Edit and Delete in
sequence:

1. **Create a fresh template** as a fixture (name = "M30 edit
   fixture", 2 lines, both fixed, balanced $100 debit / $100
   credit). Assert 201 + template appears in the list.
2. **Instantiate the template into a JournalEntry** and post
   it — this establishes a historical JE that must remain
   unaffected by later edits/deletes. Assert JE appears in
   list.
3. **Edit the template** — click the row's Edit button; assert
   dialog opens with `data-testid="tmpl-dialog-title"` reading
   "Edit template" and form fields pre-populated; change the
   name to "M30 edit fixture (renamed)"; change the debit
   amount to $150 and the credit amount to $150; click Save
   changes; assert dialog closes + list refreshes + new name
   visible.
4. **Verify historical JE unchanged** — navigate to the JE
   list; assert the JE created in step 2 still shows the
   original amounts ($100 / $100) with the original description
   from the template's pre-edit state. This is the load-bearing
   assertion for §4.7 criterion (b) — historical JEs are immune
   to template mutations by construction.
5. **Delete the template** — click the row's Delete button;
   assert the confirmation dialog opens with the mandated copy
   ("Deactivate template?" title, "historical journal entries
   ... are not affected" body); click Deactivate; assert the
   confirmation closes + the template disappears from the
   list.
6. **Verify template is truly gone from the operator list**
   — refresh the page (or navigate away and back); assert the
   template does not re-appear (i.e., soft-delete persists,
   not just a local state clear).
7. **Verify historical JE still visible after delete** —
   navigate to the JE list; assert the JE from step 2 still
   renders correctly with all original amounts and description.
   This is the load-bearing assertion for the "soft-delete
   preserves history" contract.

**Journey count:** 20 → 21.

**No blank-path regression at M30.** The M27.2 + M28.2 +
M29.2 blank-entry / template-create / instantiate journeys
continue to cover the safe-default paths directly — no
additional regression spec required. The renamed vitests
file continues to run the 17 existing create-mode cases.

### 5.c Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Dialog rename import sweep incomplete → build breaks | Low | Medium | Same-commit sweep: `git grep NewJournalEntryTemplateDialog frontend/ acceptance/` before commit; `npx tsc --noEmit` in frontend + acceptance as CI gate. |
| PATCH accidentally exposes `is_active` mutation | Low | Medium | D5 decision: silently drop `is_active` from PATCH payload (not defined on update serializer). Test `test_patch_silently_ignores_is_active_in_body` asserts. |
| Line replace semantics confuses future developers ("partial patch expected") | Low | Low | D1 documents full-replace explicitly + inline comment in the update service. |
| Operator hard-deletes template thinking it's permanent | Medium | High | D3 confirmation copy mandates "Deactivate" title + "historical entries not affected" + "can be restored later" body. Playwright asserts copy text. |
| DELETE 404 on race condition surfaces as error to operator | Low | Low | D3 error handling treats DELETE 404 as success. Tested at `test_deleteJournalEntryTemplate_treats_404_as_success`. |
| Additive-mode props weaken `JournalEntryTemplateDialog` reusability | Low | Low | Safe defaults `mode = "create"`, `open` / `onOpenChange` optional. Regression guard: renamed test file's 17 existing create-mode tests pass unchanged. |
| `updated_at` drift confuses "did the edit save?" — no operator-visible timestamp | Low | Low | Success flow: dialog closes + list refresh shows updated fields + success badge for 3s. Sufficient at MVP; formal update audit trail deferred (§3). |
| Rename disrupts historical git blame on the component file | Low | Low | `git mv` preserves rename history; `git log --follow` continues to work. Documented in the M30.2 handoff. |
| Concurrent edit conflicts (two operators editing same template) | Very Low | Medium | Single-operator MVP posture — concurrent edits architecturally impossible at M30. Deferred (§3) until M (multi-operator) unblocks. |
| Delete of template currently being instantiated (dialog open in another tab) | Very Low | Low | Instantiate is client-side value copy; even if the template row disappears mid-instantiate, the JE dialog holds its own copy of the initial values and posting continues normally. No fix needed. |

### 5.d Verifications completed at planning-open

See §4. Summary:

- ✅ **Substrate verification** (§4.1): `is_active` field
  reserved at M28.1; list service filters by default with
  symmetric `include_inactive` kwarg; get service ready for
  symmetric kwarg at M30.1.
- ✅ **FK / input discoverability** (§4.2): no new FKs; Edit +
  Delete buttons attach to existing rows; delete confirmation
  copy makes soft-delete semantics unmistakable.
- ✅ **Downstream UI verification** (§4.3): JE list / detail /
  trial balance / snapshots all read from `JournalEntry` +
  `JournalEntryLine` + `GLAccount` — no template dependency,
  soft-delete invisible to them by construction.
- ✅ **Audit-substrate verification** (§4.4): one new endpoint
  (+1 covered), 156 → 157 total, 122 → 123 covered. Two-source
  agreement gate at M30.2 close.
- ✅ **Implementation-boundary verification** (§4.5): existing
  dialog inspected line by line; additive-mode pattern viable
  without rewrite (see §4.6).
- ✅ **Dialog consolidation verification** (§4.6 — user-
  directed): Pattern A (additive-mode in-place evolution)
  chosen over Pattern B (extract subcomponents + two wrappers)
  and Pattern C (fork with duplication). Rename via `git mv`
  + import sweep in same commit per DOC_GOVERNANCE §5.
  Instantiate stays as a separate consumer.
- ✅ **Soft-delete integrity verification** (§4.7 — user-
  directed): all four criteria pass by construction. No FK
  from `JournalEntry` → `JournalEntryTemplate` (M28.0 §5.b
  rejection). `list_journal_entry_templates` filters by
  default. `include_inactive` future exposure additive.
  Delete UI copy mandated to prevent operator misunderstanding
  of soft-delete semantics.

### 5.e Phase / increment structure

**Two increments (§2), with two-source agreement gates at each
close.**

- **M30.1 (SESSION_201) — Backend substrate:**
  - Phase 1: add `admin_journal_entry_template_detail` view
    (PATCH + DELETE); add `update_journal_entry_template` +
    `delete_journal_entry_template` service verbs; add
    `include_inactive` kwarg to `get_journal_entry_template`;
    add URL pattern; add error class mappings; unit-test
    everything (D6).
  - Phase 2: run backend suite (expected 4,871 → ~4,893);
    verify existing M28.1 + M29.1 tests unchanged
    (regression guard); verify `manage.py check` +
    `makemigrations --check` clean (no migration expected);
    regenerate audit artifact and reconcile with expected
    156 → 157 / 122 → 123 delta (two-source agreement gate).
  - DoD exception path (M21.0 §5.f Option B) invoked as
    **fifth precedent** (M26 + M27.1 + M28.1 + M29.1 + M30.1)
    — infrastructure-only sub-increment; §3 of the M30.1
    handoff documents why no Playwright change is required
    at this sub-increment.

- **M30.2 (SESSION_202) — Frontend + Playwright:**
  - Phase 1: rename component + test file via `git mv` +
    import sweep (same commit); add additive props per D2/D4;
    add `updateJournalEntryTemplate` + `deleteJournalEntryTemplate`
    wrappers in `accountingApi.ts`; wire edit + delete row
    buttons on `AccountingJournalEntriesPage`; add inline
    delete confirmation dialog with mandated D3 copy; write
    D7 vitests.
  - Phase 2: extend `accounting_je_template.spec.ts` per D8;
    run full acceptance suite; audit artifact regeneration
    reconciles with new endpoint (two-source agreement gate).
  - DoD satisfied directly via D8 journey.

**Two-source agreement gate at each increment close.**

### 5.f DoD compliance check

- **M30.1** — DoD exception path invoked (**fifth precedent** —
  M26 + M27.1 + M28.1 + M29.1 + M30.1; pattern well-
  established, no further justification needed beyond
  reference). §3 of the M30.1 handoff will document:
  "M30.1 is a backend-only substrate that adds PATCH + DELETE
  verbs on a new detail endpoint with zero operator-facing
  behavior change. The M28.2 templates section and M29.2
  Instantiate flow continue to work unchanged. Playwright
  coverage intact via existing `accounting_je_template.spec.ts`
  + `accounting_je_create.spec.ts` regression. Operator-
  facing surface lands at M30.2."
- **M30.2** — DoD satisfied directly. §3 of the M30.2 handoff
  will name the D8 `test.describe("edit-delete", ...)` block
  extension in `accounting_je_template.spec.ts` (journey
  count 20 → 21).

### 5.g Rollback plan

- **M30.1 rollback:**
  - Revert `admin_journal_entry_template_detail` view
    (delete function).
  - Revert URL pattern addition in `urls.py`.
  - Revert `update_journal_entry_template` +
    `delete_journal_entry_template` service verbs.
  - Revert `include_inactive` kwarg on
    `get_journal_entry_template` (kwarg is additive; leaving
    it in would be harmless, but rollback is cleaner if the
    increment is fully unwound).
  - Delete `test_m30_journal_entry_template_edit_delete_service.py`;
    revert the endpoint + model test extensions.
  - No DB migration to roll back (none added).
  - No data loss — no data was written by the reverted
    endpoints; existing template rows untouched.

- **M30.2 rollback:**
  - Revert dialog rename via `git mv` back to
    `NewJournalEntryTemplateDialog.tsx` + revert import sweep
    (mirror of the M30.2 commit — `git log --follow` still
    resolves history).
  - Revert additive props on the component; revert
    `handleSubmit` mode branch.
  - Revert `AccountingJournalEntriesPage` row Edit + Delete
    buttons; revert edit dialog wiring; revert delete
    confirmation dialog.
  - Revert `updateJournalEntryTemplate` +
    `deleteJournalEntryTemplate` wrappers in
    `accountingApi.ts`.
  - Revert D7 vitests + D8 acceptance extension.
  - No data loss — no template rows mutated by frontend-only
    rollback (backend endpoints remain; they simply have no
    consumer).

### 5.h Non-goals for M30

- ❌ **Restore / "Show inactive" UI toggle** (M28 §3 deferral —
  ships in a future milestone when operator evidence surfaces).
- ❌ **Hard-delete escape hatch** (M30 §3 deferral — pending
  operator evidence).
- ❌ **Template mutation audit trail** (edited_by_user,
  history rows — M30 §3 deferral).
- ❌ **Optimistic concurrency control** on edit (deferred until
  M multi-operator unblocks).
- ❌ **Bulk delete / bulk edit** (M30 §3 deferral).
- ❌ **Standalone template detail page** (M28 §3 deferral,
  reaffirmed).
- ❌ **Server-side template search / pagination** (M28 §3
  deferral, reaffirmed).
- ❌ **F&I chargeback substrate** (deferred candidate — no
  pilot evidence at M30 open).
- ❌ **O2 / O3 audit refinement** (deferred candidate — no
  fresh evidence).
- ❌ **H test-hygiene remediation** (deferred candidate — no
  fresh evidence).
- ❌ **Multi-operator support / permission-class evolution**
  (would break the M10 → M29 zero-drift streak; no intent at
  M30 — streak advances to 30 → 31 across M30.1 + M30.2).
- ❌ **Instantiate consolidation into the template dialog**
  (§4.6 explicit rejection — instantiate is a template → JE
  conversion, not a template mutation; folding would violate
  the M28.0 §5.b domain separation and the M13.1 single-
  posting-path contract).

## 6. Streak accounting projections (at M30.0)

- **Planning-time as-recommended streak:** 8 (unchanged from
  M29.2 close). If §5.a is confirmed at M30.0 as the memo
  recommends (which it was — user confirmed Template edit /
  delete UI at SESSION_200 with additional architectural
  verifications), the streak advances to **9** at M30.0 close.
- **Zero-drift permission-class streak:** 29 consecutive
  milestones (M10 → M29). M30 preserves the streak — the new
  detail endpoint uses the same permission class as the M28.1
  list-or-create endpoint (`IsDealerOSAdminOrManagerReadOnly`
  or whichever class is already in use — verify at M30.1
  open, cf. `views_accounting.py:820`). Projection at M30
  close: **30 consecutive** (M30.1) → **31 consecutive**
  (M30.2 close).
- **Substrate-compound-value continuation:** M27.1 gl-accounts
  substrate → M28.1 template substrate → M28.2 create UI +
  M29.2 instantiate UI (variable) → **M30 edit + delete UI**.
  **Fourth link** on the M27.1 substrate lineage; **third
  increment** on the M28+M29 template surface.
- **Additive-prop pattern (durable lesson (t) from M29.2):**
  M30 is the first re-application of the pattern at a fresh
  component. Successful re-application would elevate the
  lesson from "surfaced" to "load-bearing across two
  milestones."

## 7. Anchors that win on conflict (for M30.1 / M30.2)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_30_PLANNING.md` (this document)
4. `docs/roadmap/MILESTONE_29_RETROSPECTIVE.md` §5 (durable
   lessons, especially (t) and (u)) + §9 (M30 candidate
   lineage)
5. `docs/roadmap/MILESTONE_29_PLANNING.md` (M29 governing
   contract, especially §4.5 + §5.b D3 which established the
   additive-prop pattern this milestone reuses)
6. `docs/roadmap/MILESTONE_28_PLANNING.md` §5.b M28.1 (model
   contract, especially the `is_active` soft-hide reservation
   at `models.py:7519` and the no-FK domain separation at
   `models.py:7504`)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (baseline 122 / 156 at M30 open; expected 123 / 157 at
   M30 close)
8. `docs/CAPABILITY_MATRIX.md` §7δ (M29 shipped surface,
   which §7ε M30 shipped surface will extend)
9. Memory records:
   - `feedback_prefer_updating_authoritative_docs.md`
   - `feedback_terminal_output_discipline.md`
   - `feedback_verify_fk_discoverability_before_lock.md`
     (M27.0 origin — verified at §4.2)
   - `feedback_duplicate_small_stable_logic.md` (M28.0 origin
     — informs the D2 dialog-consolidation decision by
     limiting duplication only to short, stable, domain-local
     logic; the 200+ lines of shared dialog machinery exceed
     that threshold, hence additive-mode is chosen)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
