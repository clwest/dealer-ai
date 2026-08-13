---
title: "SESSION_199 handoff — Milestone 29 · Increment 2 (M29.2) + close-out fold"
status: historical
type: handoff
date: 2026-08-04
session: 199
milestone: 29
milestone_status: shipped
milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
increment: 2
increment_status: shipped
commit: c79ff85
---

# SESSION_199 — Milestone 29 · Increment 2 (M29.2 — frontend + Playwright) + close-out fold

## What shipped

M29.2 delivers the remaining operator-facing value for
Milestone 29: the "Variable amount" per-line checkbox on
`NewJournalEntryTemplateDialog`, the additive `lockedLines`
prop on `NewJournalEntryDialog` with Override toggle chip,
the amber-ring variable input, the `AccountingJournalEntriesPage`
consumer wiring, twelve new component vitests, and a single
combined `test.describe("variable-amount", ...)` block
extension in `accounting_je_template.spec.ts` covering all
six user-specified assertions in one end-to-end journey.
M29 close-out is folded into M29.2 per §5.h Option B — both
increments' §5.e Phase 1 + Phase 2 verifications passed
cleanly on the first regeneration.

Per MILESTONE_29_PLANNING.md §5.b D2 + D3 + D7 + D8.

### Frontend surface additions

- **`frontend/src/components/accounting/NewJournalEntryTemplateDialog.tsx`**
  (D2):
  - New per-line "Variable amount" checkbox
    (`tmpl-line-{i}-variable`) that disables the amount
    input and marks the line for `amount: null` on the wire.
  - Amount input shows `placeholder="Set at instantiate"`
    when variable.
  - Balance indicator branches: any variable line → amber
    "Balance validated at instantiate" badge
    (`tmpl-create-variable-balance-note`) + validates the
    populated portion only; no variable lines → M28.2 balance
    behavior preserved.

- **`frontend/src/components/accounting/NewJournalEntryDialog.tsx`**
  (D3 Option A, additive-prop pattern):
  - New optional prop `lockedLines?: readonly boolean[]`.
    Safe default `undefined` → blank-entry path byte-
    identical to M27.2 baseline.
  - New internal state `overridden: Set<number>` cleared in
    five reset paths (open transition, `initialValues`
    reference change, `lockedLines` reference change,
    `reset()` invocation, `onOpenChange(false)`).
  - `NewJournalEntryInitialValues.lines[i]` gains optional
    `variableSide?: "debit" | "credit"` field for amber-ring
    routing (see §3 below for the deviation from the M29.0
    memo D3 spec).
  - `LineRow` amount-cell rendering branches: (a)
    `lockedLines?.[i] === true && !overridden.has(i)` →
    `LockedAmountChip` (`je-line-{i}-{side}-chip`) with
    inline Override pencil (`je-line-{i}-{side}-override`);
    (b) `lockedLines?.[i] === false` → amber-ring input
    (`ring-2 ring-amber-500`) + "Enter amount" placeholder
    on `line.variableSide`; opposite side disabled empty;
    (c) `lockedLines` undefined → existing editable input
    untouched.
  - New `LockedAmountChip` sub-component displays
    "$X.XX (from template)" + inline Override button.

- **`frontend/src/pages/AccountingJournalEntriesPage.tsx`**
  (consumer wiring):
  - `templateToInitialValues` populates `variableSide` when
    `line.amount === null`.
  - New `templateToLockedLines` helper maps `template.lines[i].amount
    !== null` per index.
  - `handleInstantiate` stashes `lockedLines` into new
    `instantiateLocks` state; the second dialog mount
    receives `lockedLines={instantiateLocks}`.
  - Blank-entry path (the "+ New journal entry" trigger on
    line 271) never sets `lockedLines` → undefined → M27.2
    behavior preserved.

- **`frontend/src/lib/accountingApi.ts`**:
  - `CreateJournalEntryTemplateLine.amount` type changed from
    `string` to `string | null` to match the M29.1 wire
    contract.
  - Module + type comments refreshed from "future variable-
    amount" to "M29.1 realized".

### Test surface additions

- **`NewJournalEntryTemplateDialog.test.tsx`** (+4 M29 tests):
  - Variable checkbox toggles amount input disable/enable.
  - Balance indicator suppresses fixed-only wording when any
    line is variable.
  - Fully-variable template posts `amount: null` on both lines.
  - Mixed template validates fixed-portion balance
    (populated $500 debit + null credit rejected as
    unbalanced).

- **`NewJournalEntryDialog.test.tsx`** (+4 M29 tests):
  - **M29 REGRESSION GUARD** — blank-entry path unchanged
    when `lockedLines` undefined (no chips, no Overrides, no
    amber ring; editable inputs on both sides of every line).
  - `lockedLines[i] === true` renders the populated side as
    a chip with an Override pencil; unpopulated side is
    disabled empty.
  - Clicking Override transitions a locked line to editable
    input; other locked lines unaffected.
  - Variable line renders with amber ring on the correct
    side + placeholder; opposite side disabled.

- **`AccountingJournalEntriesPage.test.tsx`** (+2 M29 tests, +1
  M28.2 test updated):
  - Fully-variable template instantiate renders both lines
    with amber ring on the correct side + no chips.
  - Mixed template instantiate renders one chip (fixed
    debit) + one amber-ring input (variable credit).
  - **Updated:** existing "opens the JE dialog pre-populated
    when Instantiate is clicked" test asserts the chip +
    Override presence (behavior intentionally changed per D3
    Option A locked at M29.0; explicit shift from M28.2 UX).

- **`accountingApi.templates.test.ts`** (+2 M29 tests):
  - Create posts `amount: null` on the wire unchanged (no
    coercion).
  - Mixed populated + null amounts round-trip through fetch
    without cross-contamination.

Frontend Vitest baseline: **270 → 282** (+12 M29.2 tests; one
existing M28.2 test updated in-place).

### Playwright extension

- **`acceptance/journeys/office/accounting_je_template.spec.ts`**
  (D8 — single combined `test.describe("variable-amount", ...)`
  block, journey count 19 → 20):
  - **§5.b D8.1 (create):** Owner fills the template create
    dialog, checks Variable amount on both lines, submits;
    asserts `tmpl-create-variable-balance-note` visibility
    + no "Unbalanced" wording + successful 201 + template
    row appears.
  - **§5.b D8.5 pre-snapshot:** Deep-copy the template
    projection via admin API for post-instantiate deep-compare.
  - **§5.b D8.2 (instantiate visibly requests amounts):**
    Instantiate; asserts JE dialog opens with description
    pre-filled; both variable lines have amber-ring inputs
    with "Enter amount" placeholders; opposite sides
    disabled; no chips on either line.
  - **§5.b D8.3 (unbalanced blocked):** Types $450 debit +
    $451 credit; asserts "Unbalanced by $1.00" + Post button
    disabled.
  - **§5.b D8.4 (balanced posts):** Corrects to $450 credit;
    asserts Balanced badge + Post enabled + click Post +
    dialog closes + success badge visible.
  - **§5.b D8.5 (template unchanged):** Re-fetches templates
    via admin API; `.toEqual(snapshot)` deep-compare —
    byte-identical, no mutation on instantiate.
  - **§5.b D8.6 (JE in list/detail):** Asserts posted JE
    surfaces in list with correct total_debit; opens detail
    endpoint; asserts description matches template,
    account codes match template stored side, amounts
    reflect what the operator entered.

### Baselines at M29.2 close

| Metric | M28 close | M29.1 close | M29.2 close | Delta |
|---|---|---|---|---|
| Backend tests | 4,855 | 4,871 | **4,871** | +16 |
| Skipped | 1 | 1 | 1 | 0 |
| Failed | 0 | 0 | 0 | 0 |
| Frontend Vitest | 270 | 270 | **282** | +12 |
| Acceptance journeys | 19 | 19 | **20** | +1 |
| Audit endpoints | 156 | 156 | 156 | 0 |
| Audit covered | 122 | 122 | 122 | 0 |
| Audit backend-only | 34 | 34 | 34 | 0 |
| Service verbs | 315 | 315 | 315 | 0 |
| Migrations | 0050 | 0050 | 0050 | 0 |
| DRF admin surface | 116 | 116 | 116 | 0 |
| Permission classes | 7 | 7 | 7 | 0 |

## 1. Verification results at open

All fast-path checks green at SESSION_199 open (see M29.1
close baselines). No CI to monitor per M29 coordinated-push
posture.

## 2. Two deviations from the M29.0 memo (recorded here)

- **Existing M28.2 Instantiate test updated in-place.** The
  `AccountingJournalEntriesPage.test.tsx::opens the JE dialog
  pre-populated when Instantiate is clicked` case asserted
  `getByLabelText("Line 1 debit")` on an editable input — no
  longer present at M29.2 (chip renders instead). Updated to
  assert chip + Override presence. Analogous in spirit to
  the M29.1 removal of `test_refuses_null_amount_at_m28`.

- **`NewJournalEntryInitialValues.lines[i].variableSide`
  extension.** The M29.0 memo D3 spec named `lockedLines` as
  the sole prop addition on `NewJournalEntryDialog`. During
  M29.2 implementation, the initial-value shape was also
  extended with an optional `variableSide?: "debit" |
  "credit"` field to signal which input to amber-ring for a
  variable line. Additive-safe (safe default undefined,
  blank-entry path untouched); does not violate D3
  implementation-boundary constraint (no template-specific
  branching outside the amount-cell renderer). Recorded so a
  future reader knows the M29.0 memo D3 spec was slightly
  under-scoped on the initialValues shape.

Both are documented in `MILESTONE_29_RETROSPECTIVE.md` §3.

## 3. Two-source agreement gate

- No new `urls.py` changes.
- No new endpoint definitions.
- No new permission classes.
- Zero-drift permission-class streak: **28 → 29** consecutive
  milestones (M10 → M29).
- Audit **156 / 122 / 34 / 315** identity at close (line
  reference on row 150 refreshed from `accountingApi.ts:447`
  to `:448` — legitimate refresh reflecting the type-comment
  update on `accountingApi.ts`; no coverage change).

## 4. DoD compliance

Per MILESTONE_29_PLANNING.md §5.f: M29.2 satisfies DoD
directly via the D8 combined variable-amount describe block
(journey count 19 → 20). No exception path invoked at the
customer-facing increment.

## 5. Streaks at M29.2 close

- **Planning-time as-recommended streak:** **8** (unchanged
  since M29.0 close). M29.1 + M29.2 both pure implementation.
- **Zero-drift permission-class streak:** **29 consecutive**
  milestones (M10 → M29).
- **Substrate-compound-value continuation:** **3 links realized**
  (M27.1 → M28.1 → M29). Payoff of the M28.1 forward-compat
  schema reservation delivered end-to-end.
- **DoD exception path invocations:** **4** (M26 + M27.1 +
  M28.1 + M29.1).

## 6. Non-goals for SESSION_199 (all honored)

- ❌ Did not touch backend service or serializer code (M29.1
  territory).
- ❌ Did not introduce `InstantiateJournalEntryDialog`
  wrapper — additive-prop pattern on `NewJournalEntryDialog`
  locked at M29.0 D3.
- ❌ Did not modify the base `NewJournalEntryDialog` beyond:
  (a) new `lockedLines` optional prop, (b) internal
  `overridden` state, (c) extending the `useEffect` deps +
  reset paths, (d) amount-cell branch. Nothing else in the
  dialog is template-aware.
- ❌ Did not create new endpoints — zero-drift streak
  advanced to 29 as intended.
- ❌ Did not add historical back-reference / instantiation
  audit trail on `JournalEntry` (M28 §3 + M29 §3 deferral
  reaffirmed).
- ❌ Did not add template edit / delete UI (M28 §3 deferred
  candidate).
- ❌ Did not push M29 — coordinated push at M29 close after
  explicit user confirmation.

## 7. M29 close-out

Milestone 29 SHIPPED at SESSION_199. Close-out folded into
M29.2 per §5.h Option B — both increments' §5.e Phase 1 +
Phase 2 verifications passed cleanly on the first
regeneration. No separate M29.3 required.

Close-out artifacts landed this session:

- `docs/CAPABILITY_MATRIX.md` §7δ (M29 shipped surface).
- `docs/roadmap/MILESTONE_29_RETROSPECTIVE.md`.
- This handoff.
- `00-START-NEXT-SESSION.md` overwritten with SESSION_200
  M30.0 opening brief.

Coordinated M29 push (M29.0 planning + backfill + M29.1
substrate + backfill + M29.2 close + backfill = 6 commits)
awaits explicit user confirmation per CLAUDE.md safety
protocol.

## 8. What SESSION_200 (M30.0) opens

- Starting-state verification at the M29.2 close baseline.
- **If M29 pushed:** monitor first M29 CI run; address any
  regression as §0.a M30.0 amendments.
- Regenerate audit artifact; confirm 122/156 identity.
- Present M30 candidate list per M29 retrospective §9:
  - **Elevated:** NEW template edit / delete UI; NEW O2 +
    O3 audit refinement; H test-hygiene; NEW C F&I chargeback
    substrate.
  - **Gated:** T / U / L / M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - Plus M29 §3 + M28 §3 + M27 §3 + M25 §4 deferrals.
- Recommend M30 target under the primary operational-
  coverage lens (or substrate-compound-value continuation
  reframe if evidence supports it).
- Await user confirmation; draft §5.b–§5.h.
- Verify FK / input discoverability + downstream UI +
  audit substrate before locking §5.b.
- DoD compliance check on §3 draft.
- Ship `docs/handoffs/SESSION_200_m30_inc0_planning.md`;
  local commit only, no push.

See `00-START-NEXT-SESSION.md` for the SESSION_200 opening
brief.
