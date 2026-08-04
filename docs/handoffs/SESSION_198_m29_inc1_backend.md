---
title: "SESSION_198 handoff — Milestone 29 · Increment 1 (M29.1 — backend substrate relaxation)"
status: historical
type: handoff
date: 2026-08-04
session: 198
milestone: 29
milestone_status: active
milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_198 — Milestone 29 · Increment 1 (M29.1 — backend substrate relaxation)

## What shipped

M29.1 spent the M28.1 nullable-amount schema reservation
(migration 0050) — no new migration, only a serializer +
service relaxation that accepts `amount = null` as a
*variable* line and validates balance against the populated
portion only. Fully-variable and mixed templates now flow
through the create pipeline; fully-populated templates
retain M28.1 behavior byte-identical. Backend baseline
4,855 → 4,871 (+16 net); frontend + acceptance untouched;
DoD exception path invoked as fourth precedent (M26 + M27.1
+ M28.1 + M29.1).

Per MILESTONE_29_PLANNING.md §5.b D1 and §5.e M29.1.

### Backend service change

- **`backend/dealer_ai/services/accounting/template.py`
  `_validate_template_lines`** — replaced the "amount
  required" branch with three-state logic:
  1. `amount is None` → variable line; skip balance
     contribution (side + GL still validated).
  2. `amount > 0` → fixed line; contribute to
     `total_debit` / `total_credit` per `side`.
  3. `amount <= 0` → reject as
     `InvalidJournalEntryTemplateLineError` (behavior
     preserved from M28.1).
- **Balance check** runs against the populated portion
  only: `sum(populated debit) == sum(populated credit)`.
  Three legitimate template shapes accepted:
  - **Fully fixed** — M28.1 behavior preserved.
  - **Fully variable** — trivially balances (both sums
    zero).
  - **Mixed** — populated portion must self-balance, or
    reject as `UnbalancedJournalEntryTemplateError`.
- **Cross-tenant guard** moved earlier in the loop so it
  applies to variable lines as well as fixed. (Previously
  cross-tenant was checked after amount validation;
  reordering has no effect on the M28.1 test surface — all
  M28.1 tests continue to pass.)
- Module + error-class + `TemplateLineInput` docstrings
  updated to reflect the M29 posture ("M29 spent what M28.1
  reserved"). `create_journal_entry_template` docstring
  updated to name the three legitimate template shapes.

### Backend serializer change

- **`backend/dealer_ai/views_accounting.py`
  `JournalEntryTemplateLineSerializer.amount`** — added
  `allow_null=True`. Comment updated to name M29
  semantics.

### Backend model docstring update

- **`backend/dealer_ai/models.py:7568`** —
  `JournalEntryTemplateLine` docstring "`amount IS NULL`
  posture" paragraph refreshed from "future variable-amount
  milestone" to "M29.1 spent the reservation" + names
  M29.2 as the UI increment. No field changes; no
  migration.

### Backend test surface additions

**New file** `backend/dealer_ai/tests/
test_m29_variable_amount_template_service.py` (11 tests).
Class `VariableAmountTemplateCreateTests` covers:

- Fully-variable template accepted (both lines null).
- Null amount stored as `None`, not coerced to zero.
- Mixed template with balanced populated portion accepted.
- Mixed template with imbalanced populated rejected as
  `UnbalancedJournalEntryTemplateError`.
- Zero populated amount still rejected as
  `InvalidJournalEntryTemplateLineError`.
- Negative populated amount still rejected.
- Bad `side` still rejected on variable lines.
- Cross-tenant GL account still rejected on variable lines
  (`CrossTenantGLAccountError`).
- Side + ordering + memo preserved on variable lines.
- Populated balance enforced at $0.01 rounding-imbalance
  in a mixed 3-line template.
- Fully-populated regression guard (M28.1 happy path
  unchanged).

**Extension** of
`test_m28_journal_entry_template_endpoint.py` (+4 tests):

- `test_post_m29_fully_variable_returns_201` — POST with
  `amount: null` on all lines → 201.
- `test_post_m29_mixed_populated_and_variable_returns_201`
  — mixed 4-line utility template → 201.
- `test_post_m29_mixed_with_imbalanced_populated_returns_400`
  — one fixed debit + null credit → 400.
- `test_get_m29_projection_returns_null_amount_for_variable_lines`
  — GET returns `amount: null` for variable lines in
  projection.

**Extension** of `test_m28_journal_entry_template_model.py`
(+2 tests):

- `test_m29_mixed_variable_and_fixed_lines_roundtrip` —
  mixed template round-trips through ORM with `Decimal` +
  `None` preserved.
- `test_m29_fully_variable_template_two_lines_null_ok` —
  fully-variable template stores + queries via
  `amount__isnull`.

**Removed** from
`test_m28_journal_entry_template_service.py`:

- `test_refuses_null_amount_at_m28` — asserted the M28.1
  behavior that M29.1 intentionally lifted. Module
  docstring updated with an inline note pointing to the
  M29 file for null-amount coverage.

### Baselines at M29.1 close

| Metric | M28 close | M29.1 close | Delta |
|---|---|---|---|
| Backend tests | 4,855 | **4,871** | +16 |
| Skipped | 1 | 1 | 0 |
| Failed | 0 | 0 | 0 |
| Frontend Vitest | 270 | 270 | 0 (untouched) |
| Acceptance journeys | 19 | 19 | 0 (untouched) |
| Audit endpoints | 156 | 156 | 0 |
| Audit covered | 122 | 122 | 0 |
| Audit backend-only | 34 | 34 | 0 |
| Service verbs | 315 | 315 | 0 |
| Migrations | 0050 | 0050 | 0 (no new) |
| DRF admin surface | 116 | 116 | 0 (no new endpoint) |
| Permission classes | 7 | 7 | 0 (zero-drift streak preserved) |

## 1. Verification results at open

| Check | Expected | Actual |
|---|---|---|
| `git status` | clean; ahead 2 | ✅ clean; ahead 2 |
| `git log --oneline -3` top | M29.0 hash backfill (7ee1b65) | ✅ 7ee1b65 |
| Django `check` | clean | ✅ clean |
| `makemigrations --check` | No changes | ✅ No changes |
| `redis-cli ping` | PONG | ✅ PONG |

Backend / frontend / acceptance test suites re-verified
implicitly by baseline-preservation gates below (§4).

## 2. No CI run to monitor

M29.0 was not pushed (coordinated push at M29 close per
§5.e). Skipped per M29.0 handoff §2.

## 3. Audit artifact unchanged

Regenerated at M29.1 close (`python3 -m
dealer_ai.scripts.audit_operational_surface`): output
**156 / 122 / 34 / 315** byte-identical to the M28.2
committed artifact. No drift.

## 4. M28.1 regression guard intact

Explicit gate per §5.e Phase 2:

- All 15 surviving M28.1 service tests (was 16, minus the
  intentionally-removed null-rejection test) pass
  unchanged.
- All 16 M28.1 endpoint tests (before adding 4 M29
  extensions) pass unchanged.
- All 9 M28.1 model tests (before adding 2 M29
  extensions) pass unchanged.
- The `test_amount_null_posture_preserved` M28.1 model
  test (which round-trips a null through the ORM at the
  model layer without the service in play) continues to
  pass — the model column reservation is what M29.1
  spends, not what M29.1 changes.

## 5. Two-source agreement gate

Per M26.1 durable lesson:

- `git diff --stat backend/dealer_ai/urls.py` → empty
  (no URL change).
- `git diff` scan of `views_accounting.py` → only the
  `JournalEntryTemplateLineSerializer.amount` field gained
  `allow_null=True` and a comment refresh; **zero new
  endpoint definitions**.
- Audit artifact regeneration confirms `156 / 122 / 34 /
  315` identity.
- Endpoint count on M21 row 150 (combined `GET+POST
  admin/accounting/journal-entry-templates/`) unchanged
  in scope and coverage.

**No endpoint drift at M29.1.** Zero-drift permission-class
streak preserved at 28.

## 6. DoD exception path (fourth precedent)

Per MILESTONE_29_PLANNING.md §5.f + M21.0 §5.f Option B:

M29.1 is a backend-only substrate relaxation with **no
operator-facing behavior change**. No frontend touched, no
new API surface. Playwright coverage remains intact via
existing `accounting_je_template.spec.ts` +
`accounting_je_create.spec.ts` regression — both continue
to exercise the M27.2 posting path which M29.1 does not
touch (M13.1 `post_journal_entry` service unchanged).

Fourth invocation of the exception path (M26 audit-tooling
substrate + M27.1 gl-accounts substrate + M28.1 template
substrate + M29.1 variable-amount substrate). Pattern is
now well-established for backend-only substrate
increments.

Direct DoD satisfaction returns at M29.2 via the D8
`test.describe("variable-amount", ...)` block extension
(journey count 19 → 20).

## 7. Streaks at M29.1 close

- **Planning-time as-recommended streak:** 8 (unchanged;
  M29.1 is pure implementation of the M29.0 locked plan).
- **Zero-drift permission-class streak:** 28 (unchanged;
  no new endpoints).
- **Substrate-compound-value continuation:** M27.1 →
  M28.1 → M29.1 (third link now realized on backend,
  awaiting M29.2 UI to complete the operator loop).

## 8. Non-goals for SESSION_198 (all honored)

- ❌ Did not modify the `JournalEntryTemplate` /
  `JournalEntryTemplateLine` model schema.
- ❌ Did not create any new endpoints.
- ❌ Did not touch frontend or acceptance workspaces.
- ❌ Did not force-push or amend earlier commits.
- ❌ Did not modify the M13.1 posting path.
- ❌ Did not add historical back-reference / audit trail
  fields on `JournalEntry` (M28 §3 + M29 §3 deferral
  reaffirmed).
- ❌ Did not touch DoD compliance corners (exception path
  explicitly documented at §6).

## 9. What SESSION_199 (M29.2) opens

- Frontend + Playwright per §5.b D2 + D3 + D7 + D8.
- "Variable amount" checkbox on
  `NewJournalEntryTemplateDialog` (D2).
- Additive `lockedLines?: readonly boolean[]` prop on
  `NewJournalEntryDialog` + internal `overridden: Set<number>`
  state + Override toggle UI (D3 Option A). Reset paths
  guaranteed per D3 §5.b.
- `AccountingJournalEntriesPage.handleInstantiate` computes
  `lockedLines` from `template.lines[i].amount !== null`.
- Vitest extensions (~11) per D7.
- Single combined
  `test.describe("variable-amount", ...)` block extension
  in `accounting_je_template.spec.ts` per D8; journey
  count 19 → 20.
- DoD satisfied directly.
- Two-source agreement gate at close.
- Local commit only; coordinated push at M29 close.

See `00-START-NEXT-SESSION.md` for the SESSION_199 opening
brief.
