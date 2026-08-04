---
title: "Milestone 29 — Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
status: active
type: planning-memo
generated: 2026-08-04
generated_at_session: SESSION_197 (skeleton + expansion + all §5 locks)
milestone: 29
milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_28_PLANNING.md
  - docs/roadmap/MILESTONE_28_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7γ
  - backend/dealer_ai/models.py (JournalEntryTemplate, JournalEntryTemplateLine)
  - backend/dealer_ai/migrations/0050_m281_je_template.py
  - backend/dealer_ai/services/accounting/template.py
  - backend/dealer_ai/services/accounting/journal.py (post_journal_entry, M13.1)
  - backend/dealer_ai/views_accounting.py (M28.1 combined GET+POST endpoint)
  - frontend/src/components/accounting/NewJournalEntryTemplateDialog.tsx (M28.2)
  - frontend/src/components/accounting/NewJournalEntryDialog.tsx (M27.2 + M28.2 initialValues path)
  - frontend/src/pages/AccountingJournalEntriesPage.tsx (M28.2 templates section + Instantiate wiring)
  - frontend/src/lib/accountingApi.ts (M28.1 template wrappers)
  - acceptance/journeys/office/accounting_je_template.spec.ts (M28.2)
  - acceptance/journeys/office/accounting_je_create.spec.ts (M27.2 + M28.2 regression)
---

# Milestone 29 — Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)

> **Active planning memo.** Drafted + expanded + all §5 locks
> at SESSION_197 M29.0 open.
>
> **§5.a locked at open** as **NEW variable-amount templates**,
> under the *primary operational-coverage lens* that has
> governed §5.a selection since M22 close (durable), plus the
> *substrate-compound-value continuation* framing that first
> validated at M27.1 → M28.1 → M28.2. M29 is the second
> operator-facing consumer of the M28.1 template substrate on
> top of the M27.1 gl-accounts substrate — compound value on
> compound value, exactly as the M28.1 model docstring
> ("`amount IS NULL` posture is intentional forward-compat")
> predicted at reservation time.
>
> **The anchor business question** — *Can a dealership
> accountant persist a recurring journal-entry recipe once,
> instantiate it monthly with amounts that vary period-to-
> period (depreciation, utilities, payroll accruals), and
> post a balanced entry to the GL through the shipped
> application?* — governs every M29 scope decision.
>
> **One implementation-boundary verification performed at
> M29.0 open** (per user direction, before locking §5.b):
> The M27.2 `NewJournalEntryDialog` already supports
> `initialValues` cleanly via an open-transition `useEffect`
> (lines 178–191) and a `reset()` on close (line 235). Adding
> an *optional* per-line `lockedLines?: readonly boolean[]`
> prop is truly additive — when `lockedLines` is `undefined`
> (the blank-entry path used by the "+ New journal entry"
> trigger), the render path is byte-identical to the M27.2
> baseline and every existing `NewJournalEntryDialog.test.tsx`
> case passes unchanged. The thin-wrapper alternative
> (`InstantiateJournalEntryDialog`) was considered and
> rejected: the read-only-chip UI must appear inside the
> per-line amount cell, which cannot be composed cleanly from
> outside the base dialog without exposing a render slot —
> more surface change than the additive prop. See §5.b D3.

## 1. Context

### 1.1 Why now

M28.1 shipped a `JournalEntryTemplateLine.amount` DecimalField
with `null=True, blank=True` — deliberately reserved schema
space for variable-amount templates. The M28.0 architectural
verification named the three most common recurring-JE
patterns whose amounts vary period-to-period (**depreciation,
utilities, payroll accruals**) and recorded them in memory as
the intended payoff of the forward-compat design. At M28
close no operator surface exists for these — the M28.1 create
serializer requires `amount` non-null and the M28.2 UI has no
"Variable amount" affordance.

M29 spends the reserved schema. Zero DB migration; the model
column is already nullable.

### 1.2 What the operator gets

An accounting operator can:

1. **Create** a recurring journal-entry template with one or
   more lines marked as *variable amount* (side + GL account
   fixed at template-creation time; amount deferred to
   instantiation).
2. **Instantiate** the template — the New Journal Entry dialog
   opens with fixed lines displayed as read-only chips
   ("$1,250.00 (from template) [Override]") and variable
   lines highlighted with an amber ring and "Enter amount"
   placeholder.
3. **Override** any fixed amount via an inline pencil, without
   the operator having to leave the dialog or re-key the
   whole line.
4. **Post** a balanced entry to the GL through the same
   M13.1 posting path used by blank-entry creation — no
   template mutation, no new backend posting service.

### 1.3 What the operator does not get at M29

- Editing / deleting existing templates (deferred candidate,
  unchanged from M28 §3).
- Named / shared variables across multiple lines (M28 §3
  deferral). Two-line same-amount templates are supported at
  M29 by having the operator enter each amount independently
  — **no silent cross-line coupling**.
- Historical back-reference on `JournalEntry` (M28 §3
  deferral).
- Standalone template detail page (M28 §3 deferral).

## 2. Increment structure

Two-increment structure, following the M27 / M28 pattern:

- **M29.1 — Backend substrate** (SESSION_198): serializer
  `allow_null=True`, service null-branch logic, balance check
  ignores nulls at create-time, extended endpoint / service /
  model tests. Frontend + acceptance untouched. DoD exception
  path invoked as *fourth precedent* (M26 + M27.1 + M28.1 +
  M29.1).
- **M29.2 — Frontend + Playwright** (SESSION_199): variable-
  amount checkbox in `NewJournalEntryTemplateDialog`; the
  additive `lockedLines` prop on `NewJournalEntryDialog`; the
  Override toggle UI; extended vitests; new
  `test.describe("variable-amount", ...)` block in the
  existing `accounting_je_template.spec.ts` covering all six
  user-specified assertions from §5.b D8. **DoD satisfied
  directly**; no exception path.

Two-source agreement gate at each increment close (M26.1
durable lesson): audit artifact regeneration must reconcile
with the endpoint diff before the increment is declared
shipped.

## 3. Deferrals (all valid for later re-entry)

Carried forward from M28 §3, M27 §3, M25 §4 — unchanged.

New at M29:

- **Fully-variable UX polish.** If pilot evidence supports it,
  add a "Repeat last amounts" affordance to help operators
  recall the previous instantiation's values. Not shipped at
  M29 — the M27.2 balance indicator is a sufficient guard
  against fat-finger errors on first pass.
- **Server-recorded instantiation audit trail.** No
  `last_instantiated_at` or `instantiation_count` fields on
  `JournalEntryTemplate`. Preserves D5 template-immutability;
  can be added later without schema break if operator
  evidence demands it.
- **Named / shared template variables.** Explicitly reaffirmed
  as an M28 §3 deferral. §5.b D4 documents the design
  constraint that M29 must not falsely imply auto-linkage
  when a template happens to have a two-line same-amount
  shape.

## 4. Verifications performed at planning-open

Per the M24–M28 durable lessons carried into M29 (from the M28
retrospective §5 + `00-START-NEXT-SESSION.md` §7).

### 4.1 Substrate verification

- ✅ **Model schema:** `JournalEntryTemplateLine.amount =
  DecimalField(null=True, blank=True, ...)` confirmed in
  migration `0050_m281_je_template.py` line 66–74. Zero DB
  migration required for M29.
- ✅ **Model docstring** (`models.py:7568`): "**`amount IS NULL`
  posture is intentional forward-compat**, not accidental
  permissiveness." M29 spends what M28.1 reserved.
- ✅ **Frontend initial-value plumbing:**
  `AccountingJournalEntriesPage.templateToInitialValues`
  (line 80–89) already null-safe: `const amount = line.amount
  ?? "";` — a variable line arrives at the JE dialog as an
  empty string.
- ✅ **JE dialog balance indicator:** `NewJournalEntryDialog`
  computes live `isBalanced = balanceDelta === 0 && totalDebit
  > 0` at line 225 with the "+ Post" button gated on it. No
  new balance surface required.
- ✅ **M13.1 posting path:** unchanged — instantiation posts a
  `JournalEntry` via the same `post_journal_entry` service
  used by blank creation. No new backend posting surface.

### 4.2 FK / input discoverability (M27.0 durable lesson)

- ✅ **GL account picker at create-template + instantiate:**
  reused from M27.2. No new FKs introduced.
- ✅ **Variable-amount input discoverability at
  instantiate:** the D3 Option A visual-distinction design
  (read-only chip for fixed, amber ring + "Enter amount"
  placeholder for variable) satisfies the M27.0 lesson at
  the input-level — the operator cannot miss which fields
  require input.

### 4.3 Downstream UI verification (M24.1 + SESSION_189/190
     durable lesson)

- ✅ **JE list page:** `AccountingJournalEntriesPage`
  displays posted JEs including those from template
  instantiation. Confirmed at M28.2 via
  `accounting_je_template.spec.ts` journey.
- ✅ **JE detail page:** M27.2 detail rendering identical for
  hand-entered vs template-instantiated entries; no
  divergence at data model.

### 4.4 Audit-substrate verification (M26.1 durable lesson)

- ✅ **No new endpoint.** M29.1 relaxes the existing
  combined-verb `POST /admin/accounting/journal-entry-
  templates/` (row 150 in M21 audit). Coverage remains
  **122 / 156**.

### 4.5 Implementation-boundary verification

- ✅ **`NewJournalEntryDialog` reuse posture:** the base
  dialog already accepts `initialValues` via an open-
  transition `useEffect` (lines 178–191) with a `reset()` on
  close (line 235). Extension is additive — see §5.b D3.

## 5. Load-bearing decisions (all locked at M29.0)

### 5.a Target selection (locked at open)

**NEW variable-amount journal templates.** Recommendation
grounded in the primary operational-coverage lens
(depreciation / utilities / payroll accruals are the three
most common recurring accounting entries that vary period-to-
period; without variable-amount support M28.1's template
substrate only serves fixed-ratio entries) plus the
substrate-compound-value continuation framing (second
operator-facing consumer of the M28.1 substrate — compound
value on compound value, per M27.1 → M28.1 → M29 substrate
lineage). Alternatives (template edit/delete UI, O2/O3 audit
refinement, H test-hygiene) evaluated and passed.

Deferred candidates unchanged: template edit / delete UI
remains a strong candidate for a future milestone unless
narrow correction evidence surfaces during M29 impl.

### 5.b Design decisions (D1–D8)

#### D1 · Serializer + service relaxation posture

- **Model:** unchanged (already `null=True, blank=True` since
  migration `0050`).
- **`JournalEntryTemplateLineSerializer.amount`:** add
  `allow_null=True`. No other serializer changes.
- **`_validate_template_lines` in `services/accounting/
  template.py`:** replace the "amount required" branch
  (currently at lines 140–144) with three-state logic:
  1. `amount is None` → skip balance contribution; mark line
     as *variable*; do not raise.
  2. `amount is not None and amount > 0` → contribute to
     debit-side or credit-side sum per `side`.
  3. `amount is not None and amount <= 0` → raise
     `InvalidJournalEntryTemplateLineError` (existing
     behavior preserved for the zero / negative case).
- **Balance check at CREATE time:** run against populated
  (non-null) lines only. Three legitimate template shapes
  are all accepted:
  - **Fully fixed** (M28.1 behavior): every line has an
    amount; debit-side sum == credit-side sum.
  - **Fully variable:** every line has `amount: null`; no
    balance check at create-time (both sums are zero, which
    trivially equals).
  - **Mixed:** some lines have amounts, some are null; the
    non-null lines' debit-side sum must equal their credit-
    side sum. Rationale: forbidding mixed-with-imbalanced-
    populated-portion catches the "operator set one fixed
    amount without matching the other side" bug at create
    time rather than deferring it to instantiate.
- **Full balance re-checked at INSTANTIATE time** via the
  existing M13.1 `post_journal_entry` service — no new
  backend validation surface at instantiate time. The M27.2
  `NewJournalEntryDialog` submit path already routes through
  `postJournalEntry` → M13.1 service, which fails closed on
  imbalance.

**No new API flag.** The presence / absence of `amount` in
the POST body (`amount: null` ↔ variable line) is the
signal. Keeps the serializer change minimal and self-
documenting.

#### D2 · Fixed vs variable at create-time UI

- **`NewJournalEntryTemplateDialog`** gets a per-line
  "**Variable amount**" checkbox positioned next to the
  amount input. When checked: amount input disables +
  visually greys out; the submitted line has `amount: null`.
  When unchecked (default): amount input required non-null
  > 0 (M28.1 behavior preserved for fixed lines).
- **Client-side balance indicator at create-time:** if any
  line is variable, the balance indicator shows "Variable
  amounts — balance validated at instantiate time." (i.e.,
  suppresses the current red "Unbalanced by $X" message for
  the variable-inclusive case). If no line is variable, the
  M28.2 balance indicator behavior is preserved unchanged.

#### D3 · Instantiation UI — visual distinction (Option A, locked)

**Implementation boundary (locked at §5.b).**

Add ONE new optional prop to `NewJournalEntryDialog`:

```ts
interface NewJournalEntryDialogProps {
  // ... existing props unchanged ...
  initialValues?: NewJournalEntryInitialValues;
  /** M29 — per-line locking for template instantiation.
   *  Index-aligned with initialValues.lines. When
   *  lockedLines[i] === true, the amount cell for line i
   *  renders as a read-only chip ("$X (from template)")
   *  with an inline "Override" pencil that toggles line i
   *  to editable. When lockedLines is undefined (blank-
   *  entry path), all inputs are editable — behavioral
   *  no-op. */
  lockedLines?: readonly boolean[];
}
```

**Additive-prop pattern rationale.** The user directive was
to prefer keeping `NewJournalEntryDialog` reusable rather
than hardwiring template-specific behavior into its normal
blank-entry path, and to inspect the existing component
before choosing between the additive prop and the thin-
wrapper alternative. Inspection at §4.5 confirmed the base
dialog already has clean `initialValues` support via an
open-transition `useEffect` (lines 178–191) with a `reset()`
on close (line 235). The additive prop is the smallest clean
design:

- No branching outside the amount-input renderer.
- Safe default `undefined` → normal input → **blank-entry
  path byte-identical to M27.2 baseline**.
- Existing `NewJournalEntryDialog.test.tsx` regression
  suite passes unchanged (no test sets `lockedLines`).
- Thin-wrapper alternative rejected: the read-only-chip UI
  must appear inside the per-line amount cell, which cannot
  be composed from outside the base dialog without exposing
  a render slot — a larger API surface change than the
  single additive prop.

**Internal state.**

```ts
const [overridden, setOverridden] = useState<Set<number>>(
  () => new Set(),
);
```

**Reset guarantee (per user constraint — override state must
not leak between instantiations or between template ↔ blank-
entry sessions).** The `overridden` set is cleared in every
one of the four reset paths:

1. **Dialog open false → true transition:** extend the
   existing `useEffect` at lines 178–191 to clear
   `overridden` alongside `setDescription` / `setPostedAt`
   / `setLines`. Add `lockedLines` to the dependency array
   so a template swap without a close-reopen also clears.
2. **`initialValues` reference change:** already in the
   `useEffect` deps; extended to also reset `overridden`.
3. **`reset()` function** (line 235): clear `overridden`
   alongside description / postedAt / lines.
4. **Dialog close via `onOpenChange(false)`** (line 296–299):
   already invokes `reset()`; per (3) that now clears
   `overridden`.

**Line-row rendering (only the amount cell branches).**

For each line index `i`:

- If `lockedLines?.[i] === true && !overridden.has(i)`:
  render a **read-only chip** showing
  `"$X,XXX.XX (from template)"` in the amount cell, with a
  small inline pencil icon labeled "Override" that, on
  click, calls `setOverridden((s) => new Set([...s, i]))` —
  which flips the render branch to the normal editable
  input on the next render.
- Else: render the existing editable input **untouched**.

Variable lines (`lockedLines?.[i] === false`) render as
normal editable inputs with an amber outline + "Enter
amount" placeholder text — the amber ring is a small CSS
class conditionally applied when the line has an empty
amount and is a *variable* line (i.e., `lockedLines?.[i]
=== false`). No new state.

**Consumer wiring (`AccountingJournalEntriesPage`
`handleInstantiate`).**

```ts
const handleInstantiate = useCallback(
  (template: JournalEntryTemplate) => {
    setInstantiateInitial(templateToInitialValues(template));
    setInstantiateLocks(
      template.lines.map((line) => line.amount !== null),
    );
    setInstantiateOpen(true);
  },
  [],
);
```

Fixed line (`line.amount !== null`) → `lockedLines[i] =
true`. Variable line (`line.amount === null`) → `lockedLines[i]
= false`. Blank-entry path never sets `lockedLines` →
`undefined` → normal behavior.

**No changes to the base dialog beyond:** (a) the new
optional prop, (b) the new internal `overridden` state,
(c) extending the existing `useEffect` deps + reset paths,
(d) the amount-cell branch on `lockedLines?.[i] && !
overridden.has(i)`. Nothing else in the dialog is aware of
templates. **The M27.2 regression test file remains
unchanged and continues to cover the blank-entry
workflow.**

#### D4 · Two-line same-amount case — no silent mirroring

- **Zero coupling.** The operator sees two separate inputs
  when both lines are variable; must enter each value
  independently; the M27.2 balance indicator (line 224–225)
  turns green only when both sums equal. If they enter $500
  debit and $499 credit, the Post button stays disabled with
  "Unbalanced by $1.00" visible.
- **No auto-fill affordance.** No "apply to other lines"
  helper. No shared-variable placeholder text implying
  auto-link. Explicit design intent.
- **Named / shared variables** remain an M28 §3 deferral. If
  operator evidence during pilot supports them, promote as
  a separate milestone.

#### D5 · Template immutability

- **Zero writes to `JournalEntryTemplate` or
  `JournalEntryTemplateLine` during instantiate.** No
  server-side `last_instantiated_at` field. No client-side
  mutation of the template object (`templateToInitialValues`
  already produces a fresh plain object; the wrapper
  approach keeps this intact).
- **Acceptance journey** (see D8) asserts template row is
  byte-identical after instantiate: GET the template, POST
  the instantiate, GET the template again, deep-equal the
  two projections.
- **Historical back-reference on `JournalEntry`** (M28 §3
  deferral) remains out of scope.

#### D6 · Backend test surface additions

- **New file** `test_m29_variable_amount_template_service.py`
  (~15 tests):
  - `test_create_accepts_null_amount_on_all_lines`
  - `test_create_accepts_null_amount_on_some_lines`
  - `test_create_rejects_null_amount_with_negative_populated`
  - `test_create_rejects_null_amount_with_populated_imbalance`
  - `test_create_accepts_null_amount_with_populated_balance`
  - `test_null_amount_line_stores_none_not_zero`
  - `test_fully_variable_template_line_count`
  - ... (plus edge cases)
- **Extension** of
  `test_m28_journal_entry_template_endpoint.py` (~4 tests):
  - `test_post_variable_amount_returns_201`
  - `test_post_mixed_amount_returns_201`
  - `test_post_null_amount_with_negative_returns_400`
  - `test_get_projection_returns_null_amount_for_variable`
- **Extension** of `test_m28_journal_entry_template_model.py`
  (~2 tests): model-level null-amount coercion + clean().
- **Instantiate flow needs no new backend tests** — reuses
  M13.1 posting-service coverage.
- Expected backend baseline: 4,855 → ~4,876 (+~21).

#### D7 · Frontend test surface additions

- **`NewJournalEntryTemplateDialog.test.tsx`** extension
  (~4 tests): variable checkbox toggles disable/enable of
  amount input; submitting with variable line posts `amount:
  null`; balance indicator suppressed when any line is
  variable; mixed template validates fixed-portion balance.
- **`NewJournalEntryDialog.test.tsx`** extension (~3 tests):
  `lockedLines` undefined → blank-entry behavior unchanged
  (regression guard); `lockedLines[0] === true` → chip
  rendered; clicking Override toggles to editable input +
  clears on close.
- **`AccountingJournalEntriesPage.test.tsx`** extension
  (~2 tests): variable-line renders with amber ring;
  handleInstantiate passes correct `lockedLines` derived
  from template.
- **`accountingApi.templates.test.ts`** extension (~2 tests):
  create-template with null amount serializes as
  `amount: null` on the wire; projection preserves `null`
  through fetch.
- Expected frontend baseline: 270 → ~281 (+~11).

#### D8 · Playwright journey — single combined `test.describe` block (locked)

**Extend** `accounting_je_template.spec.ts` with **one new
`test.describe("variable-amount", ...)` block** containing a
single end-to-end journey that covers all six user-specified
assertions from constraint #7 in sequence:

1. **Create a variable-amount template.** Fill the create
   dialog, check "Variable amount" on at least one line
   (both lines in a two-line template), submit, assert
   201 + template appears in the list.
2. **Instantiate visibly requests the missing amounts.**
   Open the JE dialog via the template row's Instantiate
   button; assert variable lines render with amber ring +
   "Enter amount" placeholder; assert fixed lines (if any)
   render as read-only chips with an "Override" pencil.
3. **Unbalanced entry submission blocked.** Type a debit
   amount that does not match the credit side; assert the
   Post button stays disabled and the balance indicator
   reads "Unbalanced by $X.XX".
4. **Balanced entry posts successfully.** Correct the
   amounts to balance; click Post; assert the dialog
   closes and a success badge / list-refresh occurs.
5. **Saved template unchanged.** Re-fetch the template via
   `postWithCsrf` (M28.2 durable helper) or a direct
   `request.get(...)` against the M28.1 endpoint; deep-
   compare the projection to the pre-instantiate snapshot
   captured after step 1; assert byte-identical (no writes
   during instantiate).
6. **Resulting JE appears in list/detail.** Assert the new
   JE row appears in the JE list with the correct
   description + posted date; open the detail dialog and
   assert the entered amounts + account codes match what
   the operator submitted.

**Journey count:** 19 → 20.

**No blank-path regression at M29.** The M27.2 +
M28.2-extended `accounting_je_create.spec.ts` blank-entry
journey continues to cover the `lockedLines === undefined`
path directly — no additional regression spec required.

### 5.c Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Serializer `allow_null=True` weakens M28.1 validation for existing (non-variable) templates | Low | Low | Existing M28.1 tests already assert fully-populated templates succeed; regression suite unchanged. |
| Fully-variable template (all null lines) accepted at create-time but unusable in practice | Low | Low | Legitimate use case (ad-hoc monthly accrual). Instantiation enforces full balance. Acceptance covers. |
| Operator confusion — fixed vs variable indistinguishable at instantiate | Medium | High | D3 Option A (read-only chips + Override toggle) makes distinction unmistakable. Playwright asserts amber ring on variable lines + chip presentation on fixed. |
| Accidental template mutation via shared React state | Low | High | D5 assertion: template row byte-identical after instantiate (Playwright fetches template pre + post + deep-compares). |
| Two-line same-amount UX creates operator perception of auto-link | Medium | Medium | D4 explicit no-coupling; amber ring on each independent variable input; balance indicator forces manual reconciliation. Documented in retrospective §5. |
| Override state leaks across template instantiations | Low | High | D3 reset guarantee: `overridden` cleared on open transition, `initialValues` change, `lockedLines` change, `reset()` call, and `onOpenChange(false)`. Playwright asserts by instantiating template A, overriding a line, closing, then instantiating template B and asserting no override state. |
| Additive prop weakens `NewJournalEntryDialog` reusability | Low | Low | Safe default `undefined` → normal behavior. Regression test for blank-entry path added at D7 (guard). Documented in D3. |

### 5.d Verifications completed at planning-open

See §4. Summary:

- ✅ **Substrate verification** (§4.1): model schema, initial-
  value plumbing, balance indicator, M13.1 posting path.
- ✅ **FK / input discoverability** (§4.2): GL picker inherited;
  variable-amount input discoverability designed into D3.
- ✅ **Downstream UI verification** (§4.3): JE list + detail
  pages already display template-instantiated JEs correctly.
- ✅ **Audit-substrate verification** (§4.4): no new endpoint;
  M21 coverage unchanged at 122 / 156.
- ✅ **Implementation-boundary verification** (§4.5):
  `NewJournalEntryDialog` already reusable via `initialValues`;
  additive-prop pattern chosen at D3.

### 5.e Phase / increment structure

**Two increments (§2), with two-source agreement gates at
each close.**

- **M29.1 (SESSION_198):**
  - Phase 1: implement + unit-test the serializer + service
    relaxation (D1 + D6).
  - Phase 2: run backend suite (expected +~21 → ~4,876);
    verify existing M28.1 tests unchanged (regression
    guard); verify `manage.py check` + `makemigrations
    --check` clean (no migration expected).
  - DoD exception path (M21.0 §5.f Option B) invoked as
    fourth precedent (M26 + M27.1 + M28.1 + M29.1) —
    infrastructure-only sub-increment; §3 documents why
    no Playwright change is required at this sub-increment.

- **M29.2 (SESSION_199):**
  - Phase 1: implement + unit-test D2 (create-time variable
    checkbox), D3 (instantiate-time chip + Override toggle),
    D7 frontend tests.
  - Phase 2: extend `accounting_je_template.spec.ts` per D8;
    run full acceptance suite; audit artifact regeneration
    reconciles against no new endpoints (expected identity
    with 122 / 156).
  - DoD satisfied directly via D8 journey.

**Two-source agreement gate at each increment close.**

### 5.f DoD compliance check

- **M29.1** — DoD exception path invoked (fourth precedent).
  §3 will document: "M29.1 is a backend-only substrate
  relaxation with no operator-facing behavior change.
  Existing M13.1 posting path unchanged. Playwright coverage
  intact via existing `accounting_je_template.spec.ts` +
  `accounting_je_create.spec.ts` regression."
- **M29.2** — DoD satisfied directly. §3 will name the D8
  `test.describe("variable-amount", ...)` block extension
  in `accounting_je_template.spec.ts` (journey count 19 →
  20).

### 5.g Rollback plan

- **M29.1 rollback:**
  - Revert `JournalEntryTemplateLineSerializer.amount` back
    to non-null.
  - Revert `_validate_template_lines` three-state logic to
    the M28.1 "amount required" branch.
  - Delete `test_m29_variable_amount_template_service.py`;
    revert the endpoint + model test extensions.
  - Model migration `0050` untouched → no DB rollback.
  - Any variable-amount templates saved during M29.1 impl
    (before rollback) remain in the DB with `amount = NULL`
    lines — these render as `null` in projection but the
    M28.1 UI cannot instantiate them (M28.2 falls back to
    empty string; JE dialog treats as invalid at balance
    check). Safe.

- **M29.2 rollback:**
  - Revert `NewJournalEntryTemplateDialog` "Variable amount"
    checkbox.
  - Revert the `lockedLines` prop on `NewJournalEntryDialog`
    + internal `overridden` state + amount-cell branch.
  - Revert `AccountingJournalEntriesPage` `handleInstantiate`
    to the M28.2 shape (no locks passed).
  - Revert the D7 vitests + D8 acceptance extension.
  - No data loss — variable-amount templates in the DB
    continue to be readable via GET (return `amount: null`
    for variable lines); the M28.2 UI shows an empty string
    at instantiate but the operator cannot post an
    unbalanced entry via the M27.2 balance guard.

### 5.h Non-goals for M29

- ❌ Template edit / delete UI (deferred candidate; may re-
  enter as a future milestone unless narrow correction
  evidence surfaces during M29 impl).
- ❌ Named / shared template variables (M28 §3 deferral,
  reaffirmed).
- ❌ Historical-template back-reference on `JournalEntry`
  (M28 §3 deferral).
- ❌ Server-side template search / pagination (M28 §3
  deferral).
- ❌ `?include_inactive=true` endpoint exposure (M28 §3
  deferral).
- ❌ Standalone template detail page (M28 §3 deferral).
- ❌ O2 / O3 audit refinement (deferred unless fresh
  evidence).
- ❌ H test-hygiene remediation (deferred unless fresh
  evidence).
- ❌ Multi-operator support / permission-class evolution
  (would break the M10 → M28 zero-drift streak; no intent
  at M29).
- ❌ Server-side instantiation audit trail (new deferral at
  M29 §3 — no `last_instantiated_at` / `instantiation_count`
  fields).
- ❌ Cross-line variable coupling (`sharedAmount: "monthly
  rent"` semantic) — reaffirmed as an M28 §3 named-variables
  deferral. D4 documents the specific UX constraint that M29
  must not falsely imply auto-linkage.

## 6. Streak accounting projections (at M29.0)

- **Planning-time as-recommended streak:** 7 (unchanged from
  M28.2 close). If §5.a is confirmed at M29.0 as the memo
  recommends (which it was — user confirmed variable-amount
  templates at SESSION_197), the streak advances to **8** at
  M29.0 close.
- **Zero-drift permission-class streak:** 28 consecutive
  milestones (M10 → M28). M29 preserves the streak — no new
  endpoints, no permission-class changes. Projection at M29
  close: **29 consecutive**.
- **Substrate-compound-value continuation:** M27.1 gl-accounts
  substrate → M28.1 template substrate → M29 variable-amount
  extension. Third link in the compound-value lineage.

## 7. Anchors that win on conflict (for M29.1 / M29.2)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_29_PLANNING.md` (this document)
4. `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md` §5 (durable
   lessons) + §9 (M29 candidate lineage)
5. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (baseline 122 / 156 — expected identity at M29 close)
6. `docs/CAPABILITY_MATRIX.md` §7γ (M28 shipped surface)
7. Memory records:
   - `feedback_duplicate_small_stable_logic.md` (M28.0 origin)
   - `feedback_verify_fk_discoverability_before_lock.md`
     (M27.0 origin — verified at §4.2)
   - `feedback_prefer_updating_authoritative_docs.md`
   - `feedback_terminal_output_discipline.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
