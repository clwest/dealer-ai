---
state: active
date: 2026-08-04
last_session_shipped: SESSION_198
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: shipped
milestone_20_status: shipped
milestone_21_status: shipped
milestone_22_status: shipped
milestone_23_status: shipped
milestone_24_status: shipped
milestone_25_status: shipped
milestone_26_status: shipped
milestone_27_status: shipped
milestone_28_status: shipped
milestone_29_status: active
next_session: SESSION_199
next_milestone: 29
next_milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
next_increment: 2
next_increment_name: "M29.2 — Frontend + Playwright (Variable-amount checkbox at create; Override-toggle chip at instantiate; combined variable-amount describe block)"
---

# Next session — SESSION_199 · Milestone 29 · Increment 2 (M29.2 — frontend + Playwright)

> **Milestone 29 — Variable-Amount Journal Templates —
> M29.1 SHIPPED at SESSION_198.** Backend substrate
> relaxation landed. `JournalEntryTemplateLineSerializer.
> amount` accepts null; `_validate_template_lines` runs
> three-state logic (null → variable line; positive → fixed
> contributes to balance; zero-or-negative → reject). Full
> balance check runs against the populated portion only.
> Fully-variable + mixed + fully-fixed templates all accepted
> at create; imbalanced-populated portion rejected. Backend
> baseline **4,855 → 4,871 (+16 net)**. Frontend + acceptance
> untouched. DoD exception path invoked as fourth precedent
> (M26 + M27.1 + M28.1 + M29.1).
>
> **M29.2 is the operator-facing UI increment** —
> "Variable amount" checkbox on
> `NewJournalEntryTemplateDialog`, additive `lockedLines`
> prop on `NewJournalEntryDialog` + Override toggle,
> Playwright journey extension per §5.b D8. DoD satisfied
> directly.
>
> **Zero-drift permission-class streak preserved at 28**
> (M10 → M28); M29.1 was backend-only, no new endpoints.
> M29.2 is UI-only, no endpoint or permission-class
> changes. Projected to advance to 29 at M29 close.
>
> **Planning-time as-recommended streak: 8** (unchanged;
> M29.1 was pure implementation).

## First thing SESSION_199 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main`
  by **4 commits** (M29.0 planning + hash backfill +
  M29.1 substrate + hash backfill).
- `git log --oneline -5` — top should be the M29.1
  hash-backfill commit (or the M29.1 substrate commit if
  not yet backfilled).
- `python3 manage.py test dealer_ai` → **4,871 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **270 pass** (unchanged
  from M28.2 close).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. No CI to monitor

M29.0 + M29.1 not pushed; coordinated push at M29 close.
Skip the CI verification step.

### 3. Audit artifact unchanged

Optional at M29.2 open (endpoint surface unchanged from
M28.2 close). If regenerated, expected identity:
**156 total / 122 covered / 34 backend-only / 315 service
verbs**.

### 4. Implement §5.b D2 — "Variable amount" checkbox at create

Per `docs/roadmap/MILESTONE_29_PLANNING.md` §5.b D2:

- **`frontend/src/components/accounting/
  NewJournalEntryTemplateDialog.tsx`** — add a per-line
  "**Variable amount**" checkbox next to the amount input.
- When checked:
  - Amount input disables + visually greys out.
  - Submitted line body has `amount: null`.
- When unchecked (default):
  - Amount input required non-null > 0.
  - M28.1/M28.2 create-time behavior preserved.
- **Client-side balance indicator at create-time:** if
  any line is variable, the balance indicator shows
  "Variable amounts — balance validated at instantiate
  time." Otherwise, M28.2 behavior preserved unchanged.

### 5. Implement §5.b D3 — Instantiation UI visual distinction

Per `docs/roadmap/MILESTONE_29_PLANNING.md` §5.b D3
(Option A locked at M29.0).

**Additive prop pattern on `NewJournalEntryDialog`:**

- **`frontend/src/components/accounting/
  NewJournalEntryDialog.tsx`** — add one new optional prop:

  ```ts
  /** M29 — per-line locking for template instantiation.
   *  Index-aligned with initialValues.lines. When
   *  lockedLines[i] === true, the amount cell renders as
   *  a read-only chip with an inline "Override" pencil.
   *  When lockedLines is undefined (blank-entry path),
   *  all inputs are editable — behavioral no-op. */
  lockedLines?: readonly boolean[];
  ```
- **Internal state** `overridden: Set<number>` initialized
  `() => new Set()`. Cleared in five reset paths:
  1. Open false → true transition (extend `useEffect` at
     lines 178–191).
  2. `initialValues` reference change (already in deps).
  3. `lockedLines` reference change (add to deps).
  4. `reset()` invocation (line 235).
  5. Dialog close via `onOpenChange(false)` (already
     invokes `reset()`).
- **Line-row amount cell rendering** — branch:
  - `lockedLines?.[i] === true && !overridden.has(i)` →
    read-only chip `"$X,XXX.XX (from template)"` + inline
    Override pencil.
  - Else → existing editable input untouched.
- **Variable line highlighting** — when
  `lockedLines?.[i] === false`, add an amber ring CSS
  class + "Enter amount" placeholder to the (existing)
  input. No new state.

**Consumer wiring in
`frontend/src/pages/AccountingJournalEntriesPage.tsx`:**

- **`handleInstantiate`** computes `lockedLines` from the
  template:
  ```ts
  setInstantiateLocks(
    template.lines.map((line) => line.amount !== null),
  );
  ```
- Fixed line (`amount !== null`) → locked = true.
- Variable line (`amount === null`) → locked = false.
- Blank-entry path never sets `lockedLines` — undefined →
  behavior byte-identical.

### 6. Implement §5.b D7 — Frontend test surface additions

- **`NewJournalEntryTemplateDialog.test.tsx`** extension
  (~4 tests): variable checkbox toggles amount input
  disable/enable; posts `amount: null`; balance indicator
  suppressed when variable; mixed template validates
  fixed-portion balance.
- **`NewJournalEntryDialog.test.tsx`** extension (~3 tests):
  `lockedLines` undefined → blank-entry behavior unchanged
  (**explicit M27.2 regression guard**); `lockedLines[0]
  === true` → chip rendered; clicking Override toggles to
  editable input + clears on close.
- **`AccountingJournalEntriesPage.test.tsx`** extension
  (~2 tests): variable-line renders with amber ring;
  `handleInstantiate` passes correct `lockedLines`.
- **`accountingApi.templates.test.ts`** extension (~2
  tests): create-template with null amount serializes as
  `amount: null` on the wire; projection preserves `null`
  through fetch.
- Expected frontend baseline: **270 → ~281 (+~11)**.

### 7. Implement §5.b D8 — Playwright journey extension

Per `docs/roadmap/MILESTONE_29_PLANNING.md` §5.b D8:

**Extend** `acceptance/journeys/office/accounting_je_template.spec.ts`
with a **single new `test.describe("variable-amount",
...)` block** containing an end-to-end journey that covers
all six user-specified assertions from constraint #7:

1. Create a variable-amount template (fill create dialog,
   check "Variable amount" on at least one line, submit,
   assert 201 + list appearance).
2. Instantiate visibly requests missing amounts (open JE
   dialog via row's Instantiate; assert variable lines
   have amber ring + "Enter amount" placeholder; assert
   fixed lines render as read-only chips with Override
   pencil).
3. Unbalanced entry submission blocked (type mismatched
   amounts; Post button stays disabled; balance indicator
   reads "Unbalanced by $X.XX").
4. Balanced entry posts successfully (correct amounts,
   click Post, assert dialog closes + success badge or
   list refresh).
5. Saved template unchanged (re-fetch via `postWithCsrf`
   or direct `request.get`, deep-compare projection to
   pre-instantiate snapshot; assert byte-identical).
6. Resulting JE appears in list/detail (assert row in JE
   list + open detail dialog, assert entered amounts +
   account codes match).

Journey count: **19 → 20**.

**No blank-path regression at M29.** The existing M27.2 +
M28.2-extended `accounting_je_create.spec.ts` blank-entry
journey continues to cover the `lockedLines === undefined`
path directly — no additional regression spec required.

### 8. DoD satisfied directly

Per MILESTONE_29_PLANNING.md §5.f: M29.2 DoD satisfied
directly via the D8 journey extension. No exception path
required (unlike M29.1).

### 9. Two-source agreement gate

Per M26.1 durable lesson: at increment close, verify no
endpoint drift by comparing the M21 audit artifact against
the git diff. Expected: **zero endpoint diff** at M29.2
(no new views, no permission classes evolved). Zero-drift
streak advances to **29 consecutive milestones**.

### 10. Ship the M29.2 handoff

- `docs/handoffs/SESSION_199_m29_inc2_frontend.md`.
- **Do NOT push** — M29.2 is the milestone close increment;
  ship the M29 retrospective + capability matrix update +
  audit artifact refresh (if any) at close; coordinated
  push follows explicit user confirmation.
- Commit locally with a message like: `"Milestone 29 ·
  Increment 2 — Variable-amount UI + Playwright
  (SESSION_199)"`.

### 11. Milestone 29 close-out (fold or separate SESSION_200?)

Per M28.3 precedent, the M28 planning §5.h Option B fold
was invoked when both increments' §5.e Phase 1 + Phase 2
verifications passed cleanly. M29.2 SHOULD be the close-out
increment (M29 has only two increments); no separate M29.3
close-out is needed. At M29.2 close:

- Refresh `docs/CAPABILITY_MATRIX.md` §7δ with M29 shipped
  surface.
- Author `docs/roadmap/MILESTONE_29_RETROSPECTIVE.md`.
- Regenerate the audit artifact if row 150 needs any
  refresh (expected: unchanged).
- Overwrite this file with the SESSION_200 M30.0 opening
  brief (target selection pending, planning-only).

## Non-goals for SESSION_199

- ❌ Do NOT touch backend service or serializer code —
  M29.1 already shipped the substrate; M29.2 is UI-only.
- ❌ Do NOT introduce a new `InstantiateJournalEntryDialog`
  wrapper — per M29.0 D3 lock, additive-prop pattern on
  `NewJournalEntryDialog` is the chosen implementation.
- ❌ Do NOT modify the base `NewJournalEntryDialog` beyond:
  (a) the new `lockedLines` optional prop, (b) the
  internal `overridden` state, (c) extending the existing
  `useEffect` deps + reset paths, (d) the amount-cell
  branch. Nothing else in the dialog should become
  template-aware.
- ❌ Do NOT change the M27.2 blank-entry test file
  expectations — the additive prop with safe default
  guarantees byte-identical behavior. Any diff there is a
  bug.
- ❌ Do NOT create new endpoints — zero-drift streak must
  advance to 29 at M29 close.
- ❌ Do NOT introduce named / shared template variables
  (M28 §3 deferral reaffirmed).
- ❌ Do NOT add historical back-reference on
  `JournalEntry` (M28 §3 deferral reaffirmed).
- ❌ Do NOT add a template edit / delete UI at M29 (M28
  §3 deferred candidate — separate future milestone).
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT skip the DoD direct-satisfaction step.
- ❌ Do NOT skip the two-source agreement gate.
- ❌ Do NOT push M29 — coordinated push at M29 close after
  explicit user confirmation.

## Baseline expected at close (M29.2)

- Backend suite: **4,871 pass** (unchanged from M29.1
  close; M29.2 is frontend + acceptance only).
- Frontend Vitest: **270 → ~281 (+~11)** across new + 
  extended files.
- Acceptance: **19 → 20 journeys** (D8 combined
  variable-amount describe block).
- Audit coverage: **122 / 156** (unchanged).
- DRF admin surface: **116 endpoints** (unchanged).
- Permission classes: **7 actual** (unchanged; zero-drift
  streak advances to 29).
- Migration count: **0050** (unchanged).

## NEXT TASK

Start SESSION_199 with (a) starting-state verification;
(b) implement §5.b D2 (Variable-amount checkbox); (c)
implement §5.b D3 (additive lockedLines prop + Override
toggle); (d) implement §5.b D7 (frontend tests); (e)
implement §5.b D8 (combined Playwright describe block);
(f) run full frontend + acceptance suite with M27.2
regression guard intact; (g) two-source agreement gate;
(h) M29 close-out (CAPABILITY_MATRIX §7δ + retrospective +
audit refresh); (i) ship
`docs/handoffs/SESSION_199_m29_inc2_frontend.md`; (j) local
commit only, no push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_29_PLANNING.md`
   (M29.0 active memo — all §5 locks; M29.1 shipped;
   M29.2 pending)
6. `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md` §5
   (durable lessons)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (baseline **122 / 156** — expected identity at M29.2
   close)
8. `docs/CAPABILITY_MATRIX.md` §7γ (M28 shipped surface;
   §7δ pending at M29.2 close)
9. `docs/handoffs/SESSION_197_m29_inc0_planning.md`
   (M29.0 shipped)
10. `docs/handoffs/SESSION_198_m29_inc1_backend.md`
    (M29.1 shipped)
11. Memory records:
    - `feedback_duplicate_small_stable_logic.md`
    - `feedback_verify_fk_discoverability_before_lock.md`
    - `feedback_prefer_updating_authoritative_docs.md`
    - `feedback_terminal_output_discipline.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_198 — Milestone 29 M29.1 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,871 pass**, 1 skipped, 0 fail (was 4,855 at M28
  close; +16 at M29.1: +11 M29 service + 4 M29 endpoint +
  2 M29 model − 1 M28.1 obsolete null-rejection).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 270 pass**
  across 36 test files (unchanged from M28 close).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 +
  TS 5.6 operational; **19 journeys** total.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Last verified
  green on the M28.2 hash-backfill push (2m36s).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
- **Milestones shipped:** M1 → **M28**. M29 open (M29.0
  + M29.1 shipped; M29.2 pending).
- **DRF admin surface:** **116** endpoints (unchanged
  since M28.1).
- **Frontend operator routes:** 20 (unchanged).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** all M1–M28 packages unchanged.
  M29.1 relaxed `_validate_template_lines` in
  `services/accounting/template.py` (three-state logic).
- **Frontend surfaces:** unchanged at M29.1. M29.2 will
  add the "Variable amount" checkbox to
  `NewJournalEntryTemplateDialog`, the additive
  `lockedLines` prop + `overridden` internal state on
  `NewJournalEntryDialog`, and the Override toggle UI.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **28 consecutive milestones** (M10 → M28). Projected
  to advance to 29 at M29 close.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 29 status:** OPEN. M29.0 shipped (planning
  memo + handoff); M29.1 shipped (backend substrate
  relaxation); M29.2 pending (frontend + Playwright).
- **Audit tooling status:** unchanged from M26.1.
  Coverage **122 / 156** (matches M28.2 close exactly).
- **§9 evidence:** M29.1 delivered on the M28.1 forward-
  compat schema reservation. Backend accepts variable-
  amount templates; UI awaits M29.2.
- **Planning-time streak: 8** (unchanged from M29.0
  close). M29.1 was pure implementation.
- **DoD amendment (M21.0 §5.f Option B):** M29.1 invoked
  the exception path as fourth precedent (M26 + M27.1
  + M28.1 + M29.1). M29.2 satisfies DoD directly.
- **M29.1 audit coverage:** **156 endpoints, 122 covered /
  34 backend-only** (unchanged; no new endpoints). Two-
  source agreement gate passed.
- **Durable lessons carried into M29.2:** all M28-close
  lessons continue to apply. M29.1 reinforces (i) *DoD
  exception path applies cleanly to infrastructure-only
  sub-increments* (fourth invocation). No new durable
  lessons surfaced at M29.1; may surface at M29.2 close.
