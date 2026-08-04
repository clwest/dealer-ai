---
title: "SESSION_205 handoff — Milestone 31 · Increment 2 (M31.2 — frontend + Playwright: Show-inactive toggle + inactive-row rendering + Restore UI + D10 copy fulfillment + reversible-lifecycle journey) + M31 close-out fold"
status: historical
type: handoff
date: 2026-08-04
session: 205
milestone: 31
milestone_status: shipped
milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
increment: 2
increment_status: shipped
close_out_fold: true
commit: 4b5f5b9
commit_notes: "M31.2 + M31 close-out fold commit landed as 4b5f5b9; hash backfilled via a follow-up commit. NOT pushed. Coordinated M31 close push awaits explicit user confirmation."
---

# SESSION_205 — Milestone 31 · Increment 2 (M31.2 — frontend + Playwright) + M31 close-out fold

## What shipped

M31.2 delivers the customer-facing surface that binds the
M31.1 backend substrate to the operator UI + closes the M31
milestone. The `AccountingJournalEntriesPage` templates
section gains a Show-inactive toggle (plain checkbox with
aria-label; component-local state; default off — matches the
existing project convention), is_active-aware `TemplateRow`
rendering with **three independent D6 signals** on inactive
rows (visible Inactive badge + row aria-label + dedicated
`template-row-inactive-<pk>` testid + muted opacity as
reinforcement), the **L1 lifecycle-integrity guard**
(visible-but-disabled Edit + Instantiate on inactive rows
with explanatory aria-labels), row-action asymmetry per D7
(Delete slot swaps to Restore on inactive rows), and a new
inline `TemplateRestoreConfirmDialog` (co-located per the
M28.0 duplicate-small-stable-domain-logic rule) with the
mandated D8 copy that reframes the row-button "Restore"
vocabulary to the confirmation-title "Reactivate template?"
truth vocabulary per durable lesson (x). `accountingApi.ts`
gains a `restoreJournalEntryTemplate(pk)` wrapper and an
`includeInactive` option on `fetchJournalEntryTemplates`. The
M30.2 delete-confirmation copy is updated per **D10
fulfillment** — the shipped promise "You can restore this
template later — turn on **Show inactive** to find and
reactivate it" replaces the M30.2 "Restore UX ships in a
future milestone" text. A single new
`test.describe("restore-inactive", ...)` block extends
`accounting_je_template.spec.ts` with the 7-step reversible-
lifecycle journey per user §5.e spec, including the D9
load-bearing byte-identity assertion on historical JE +
`total_debit` before and after the full round-trip.

The M31 close-out fold folded into the same SESSION_205 per
M30.2 precedent — no separate M31.3:
`MILESTONE_31_RETROSPECTIVE.md` authored;
`CAPABILITY_MATRIX.md` §7ζ added with the full M31 shipped-
surface record; `MILESTONE_31_PLANNING.md` status flipped
from active to shipped with `shipped_at_session:
SESSION_205` frontmatter.

**Session artifacts:**

- **Starting-state verification (§1):** git clean; local
  `HEAD == 7c1cced` (SESSION_204 M31.1 hash-backfill commit,
  4 commits ahead of `origin/main` per M31 coordinated-push
  cadence). Backend suite **4,933 pass / 1 skip / 0 fail**
  (169.6s) — matches M31.1 close baseline. Frontend Vitest
  **300 pass / 36 files** unchanged. Django `check` +
  `makemigrations --check` clean. Frontend + acceptance
  `tsc --noEmit` clean. Redis PONG. Acceptance DB reset
  proactively per SESSION_200 §0.a durable lesson (v).
- **Implementation per §5.b D4–D10 + §5.e M31.2 spec (§2):**
  - `frontend/src/lib/accountingApi.ts`:
    - `fetchJournalEntryTemplates` extended with optional
      `{ includeInactive?: boolean }` parameter (default
      false); appends `?include_inactive=true` when true.
      Backend fail-closed parser (M31.1 D3) only enables
      inactive on the literal `true` case-insensitive, so
      the wrapper's exact string emission is contract-safe.
    - New `restoreJournalEntryTemplate(pk)` — wraps
      `authPostJSON` with empty body; returns projected
      template. Unlike the M30.2 delete wrapper's race-safe
      404-swallow, restore propagates 404 to the caller
      (row genuinely doesn't exist for this tenant; operator
      should be told).
  - `frontend/src/pages/AccountingJournalEntriesPage.tsx`:
    - Added `ChangeEvent` import (type-only) for the
      toggle handler.
    - Added `restoreJournalEntryTemplate` import from the
      accounting API.
    - New component-local state: `showInactive` (default
      false), `restoringTemplate`, `restoreSubmitting`,
      `restoreError`, `lastRestoredTemplate`.
    - Templates fetch effect extended to pass
      `includeInactive: showInactive` + include
      `showInactive` in the dependency array so the fetch
      refires when the toggle flips.
    - New handlers `handleRestoreClick`,
      `handleRestoreCancel`, `handleRestoreConfirm`,
      `handleShowInactiveChange` — mirror the M30.2 delete
      flow shape.
    - Show-inactive toggle (`<input type="checkbox">` with
      aria-label + testid `templates-show-inactive-toggle`)
      added to the templates section header.
    - Restore success badge (`tmpl-restore-success-badge`)
      added alongside the M30.2 delete + edit success
      badges; cleared by toggle flips.
    - `TemplateRow` refactored for is_active-aware
      rendering per D6 + D7 + L1:
      - Inactive rows use `template-row-inactive-<pk>`
        testid + `aria-label="Template <name>, inactive"`
        + inline `Badge` with testid
        `template-inactive-badge-<pk>` labeled "Inactive"
        + muted opacity (`opacity-60`) — three
        independent semantic signals + one reinforcement.
      - Active rows retain the M30.2 `template-row-<pk>`
        testid + no badge + full opacity.
      - Instantiate button `disabled={disabled ||
        isInactive}` with explanatory `aria-label` when
        inactive ("Instantiate template — template is
        inactive; restore it first to enable"). L1 guard.
      - Edit button `disabled={disabled || isInactive}`
        with explanatory `aria-label` when inactive
        ("Edit template — restore it first to enable").
        L1 guard.
      - Delete slot conditionally swaps to Restore button
        (`tmpl-restore-trigger-<pk>`) on inactive rows;
        M30.2 `tmpl-delete-trigger-<pk>` shape preserved
        on active rows.
    - Mounted `<TemplateRestoreConfirmDialog>` beneath the
      existing `<TemplateDeleteConfirmDialog>` mount,
      gated on `restoringTemplate !== null`.
    - New inline `TemplateRestoreConfirmDialog` function
      component co-located with `TemplateDeleteConfirmDialog`
      (M28.0 duplicate-small-stable-domain-logic rule).
      Mandated D8 copy: title "Reactivate template?"; body
      "Are you sure you want to reactivate <name>? This
      template will reappear in the active templates list
      and can be used to create new journal entries again.
      Existing journal entries created from this template
      are not affected — they remain unchanged in the
      Journal Entries list and in trial balance reports.";
      `[Cancel] [Reactivate]` footer (Reactivate as primary
      variant, not destructive — this is an additive
      action). Test-ids: `tmpl-restore-confirm-dialog`,
      `tmpl-restore-confirm-title`, `tmpl-restore-confirm-body`,
      `tmpl-restore-cancel`, `tmpl-restore-submit`,
      `tmpl-restore-error`.
    - **D10 fulfillment:** M30.2 delete-confirmation body
      updated from *"You can restore this template later.
      (Restore UX ships in a future milestone.)"* to *"You
      can restore this template later — turn on **Show
      inactive** to find and reactivate it."* Bolded
      "Show inactive" via `<strong>` for emphasis.
      Comment block updated to cite M31 planning §5.b D10.
- **Frontend tests +19 (§3):**
  - `accountingApi.templates.test.ts` +7: three
    `fetchJournalEntryTemplates` includeInactive shape
    tests (omitted, false, true); four
    `restoreJournalEntryTemplate` wrapper tests (POST URL
    + empty body, envelope projection, 404 propagation,
    500 propagation).
  - `AccountingJournalEntriesPage.test.tsx` +12: toggle
    renders + default off; toggle flip triggers refetch
    with `includeInactive=true`; three inactive-row D6
    signals (badge + aria-label + testid); L1 disabled
    Instantiate with aria-label; L1 disabled Edit with
    aria-label; Delete/Restore slot swap on inactive vs
    active; active-row unchanged after M31.2 (regression
    guard); Restore click opens confirmation with D8
    copy; Restore confirm calls wrapper + refetches +
    surfaces success badge; Restore failure inline error
    without closing; Restore cancel closes without
    calling wrapper; D10 copy fulfillment (both the
    positive new-copy assertion and the negative "future
    milestone" guard that ensures the M30.2 promise text
    is gone from shipped code).
  - Also updated one existing M30.2 assertion (`M30.2 —
    Delete click opens confirmation dialog with mandated
    copy`) — the `/You can restore this template later/`
    regex tightened to `/You can restore this template
    later — turn on Show inactive to find and reactivate
    it/` to lock the D10 copy explicitly on the shared
    assertion path.
- **Playwright +1 journey (§4):** single new
  `test.describe("restore-inactive", ...)` block in
  `acceptance/journeys/office/accounting_je_template.spec.ts`.
  7-step reversible lifecycle mapping 1:1 to user §5.e
  spec:
  1. Seed a fresh balanced template via admin API +
     instantiate through shipped UI + post one historical
     JE (D9 byte-identity baseline).
  2. Row Delete → confirm Deactivate (assert D10 copy
     "turn on Show inactive to find and reactivate it")
     → template disappears from default list; reload →
     still gone.
  3. Toggle Show inactive ON.
  4. Assert three D6 signals (aria-label + Inactive
     badge visible + inactive testid) + L1 guard
     (Instantiate `toBeDisabled()` with aria-label; Edit
     `toBeDisabled()`) + D7 asymmetry (Delete gone via
     `toHaveCount(0)`; Restore present).
  5. Click Restore → confirmation with D8 mandated copy
     ("Reactivate template?" title + "will reappear in
     the active templates list" body + "Existing
     journal entries created from this template are not
     affected" reassurance) → click Reactivate → success
     badge appears.
  6. Toggle Show inactive OFF.
  7. Template back in default active list + Inactive
     badge NOT present (`toHaveCount(0)` guard) +
     Instantiate re-enabled + click Instantiate → post
     another JE from the restored template. **Load-
     bearing D9 assertion:** historical JE from step 1
     description AND `total_debit` byte-identical before
     and after the full deactivate → restore cycle; post-
     cycle JE also lands correctly with the expected
     description.
- **Focused vitest run before full-suite (§5):** 59 tests
  across the two touched files (19 wrapper + 40 page) all
  pass in 1.66s isolated — fast-catch of regression
  before the full 6s run.
- **Focused Playwright run before full-suite (§5):**
  isolated M31.2 restore journey passes in 953ms; full
  spec file (`accounting_je_template.spec.ts` — 11 tests
  including 6 auth setup + 4 pre-existing accounting
  journeys + this new one) 16.0s.
- **Post-implementation close baselines (§6):**
  - Backend suite: **4,933 pass / 1 skip / 0 fail**
    (unchanged from M31.1 close — M31.2 made zero
    backend changes).
  - Frontend Vitest: **300 → 319 pass** across 36 files
    (+19 M31.2 tests).
  - Acceptance: **21 → 22 journeys** (+1 M31.2 restore-
    inactive describe block). Full-suite fresh-DB run:
    **28 passed / 0 failed / 32.6s** (6 auth setup +
    22 business journeys).
  - Django `check`: system check identified no issues (0
    silenced).
  - `makemigrations --check --dry-run`: No changes
    detected.
  - Frontend `tsc --noEmit`: clean.
  - Acceptance `tsc --noEmit`: clean.
  - Redis: PONG.
  - Audit regen: **158 / 124 / 34 / 318** — matches M31
    close projection exactly. Restore endpoint (audit
    index 152) re-classified from `defer-candidate-O2`
    transitional (M31.1 backend-only 35) back to
    `covered` (M31.2 close: covered 124, backend-only
    34).
  - `git grep "Restore UX ships in a future milestone"
    frontend/ acceptance/`: two hits — both in the D10
    guard test's `.not.toContain(...)` assertion +
    comment. **Shipped code has zero hits.** D10 fully
    fulfilled.
- **M31 close-out fold (§7):**
  - `docs/roadmap/MILESTONE_31_RETROSPECTIVE.md` authored
    — full M31 record (planned scope, what shipped,
    deviations, deferrals, durable design principles
    including two elevations of (w) + (x) to
    "load-bearing across two milestones" and one NEW
    principle "lifecycle-integrity precheck governs
    L1-class guard shape", streak accounting, baselines,
    M32 candidate list with standing question about
    depth-vs-breadth for M32.0 selection).
  - `docs/CAPABILITY_MATRIX.md` §7ζ added: full M31
    shipped-surface record with per-increment table
    (M31.0 planning, M31.1 backend, M31.2 UI + close-out
    fold) + explicit non-goals + status footer.
  - `docs/roadmap/MILESTONE_31_PLANNING.md` frontmatter
    `status: active` → `status: shipped`;
    `shipped_at_session: SESSION_205` added.

## 1. Verification results at open

| Check | Expected | Actual |
|---|---|---|
| `git status` | clean | ✅ clean |
| `HEAD` | 7c1cced (SESSION_204 M31.1 hash-backfill) | ✅ 7c1cced (4 commits ahead of origin/main) |
| Backend suite | 4,933 pass, 1 skip | ✅ 4,933 pass, 1 skip (169.6s) |
| Frontend Vitest | 300 pass, 36 files | ✅ 300 pass, 36 files (5.7s) |
| Django `check` | clean | ✅ clean |
| `makemigrations --check` | No changes | ✅ No changes |
| Frontend `tsc --noEmit` | clean | ✅ clean |
| Acceptance `tsc --noEmit` | clean | ✅ clean |
| `redis-cli ping` | PONG | ✅ PONG |
| Acceptance DB reset | done | ✅ removed proactively |

## 2. §5.b D4–D10 implementation summary

### D4 — Frontend list wrapper `includeInactive` parameter

`fetchJournalEntryTemplates({ includeInactive?: boolean })` —
defaults to false; when true, appends the exact
`?include_inactive=true` query string that M31.1's fail-closed
parser accepts. Naming discipline preserved: operator-facing
label "Show inactive"; wrapper parameter `includeInactive`
(camelCase); URL parameter `include_inactive` (snake_case).

### D5 — Show-inactive is an explicit operator toggle

`<input type="checkbox">` with aria-label "Show inactive
templates" + testid `templates-show-inactive-toggle`. Default
off. Component-local state (`useState(false)`). Never auto-
toggles. When off, list is active-only (byte-identical to
M30.2 shipped surface); when on, list includes inactive rows
with D6 signals + D7 asymmetry. No silent mixed-status lists —
operator must explicitly opt in.

### D6 — Inactive rows visually AND semantically distinct

Three independent signals on inactive rows (a11y-first, not
muted-only):

1. **Semantic status text:** visible `Badge` with `variant=
   "outline"` labeled "Inactive"; screen-reader text is the
   badge content (not `aria-hidden`).
2. **Row `aria-label`:** `"Template <name>, inactive"` on
   the `<tr>` element so assistive tech announces
   lifecycle state independent of visual styling.
3. **Dedicated testid:** `template-row-inactive-<pk>`
   distinct from the active-row `template-row-<pk>`
   pattern for both Playwright + Vitest assertions.

Plus muted opacity (`opacity-60`) as **reinforcement, not
primary signal** — survives color-blindness modes and dark
mode by virtue of not being the primary channel.

### D7 — Row-action asymmetry + L1 lifecycle-integrity guard

On inactive rows:

- **Delete slot → Restore button.** New testid
  `tmpl-restore-trigger-<pk>` mirrors the M30.2
  `tmpl-delete-trigger-<pk>` pattern.
- **Edit button visible-but-disabled** with
  `aria-label="Edit template — restore it first to enable"`
  (per user confirmation of §5.b review point 2 — visible
  disabled is a stronger a11y signal than hidden).
- **Instantiate button visible-but-disabled** with
  `aria-label="Instantiate template — template is inactive;
  restore it first to enable"`. This is the **L1
  lifecycle-integrity guard** — the smallest fail-closed
  fix identified in M31.0 §4.1 for the direct-UI-path
  operator-visible-inactive-row instantiation gap. Recorded
  as lifecycle integrity, not feature expansion, per user
  confirmation of §5.b review point 6.

On active rows: no change from M30.2 shipped surface —
Instantiate + Edit + Delete continue unchanged.

### D8 — Restore confirmation dialog reframes vocabulary

Row button says **"Restore"** (short, familiar operator
vocabulary). Confirmation title reframes to **"Reactivate
template?"** (truth — is_active transitions False → True).
Confirmation body reassures historical JEs are unaffected
per D9. `[Cancel] [Reactivate]` footer (Reactivate as
primary, not destructive — this is an additive action).

New inline `TemplateRestoreConfirmDialog` co-located with
`TemplateDeleteConfirmDialog`. **Not extracted to a shared
abstraction** — per the M28.0 `feedback_duplicate_small_
stable_logic.md` rule. First re-application of durable
lesson (x) — elevates from "surfaced at M30.2" to
"load-bearing across two milestones."

### D9 — Historical JEs untouched by Restore

Structural guarantee unchanged from M30.0 §4.7 (no FK from
`JournalEntry` to `JournalEntryTemplate`). Playwright
load-bearing assertion carried through the M31.2 restore-
inactive journey: historical JE from step 1 description AND
`total_debit` byte-identical before and after the full
deactivate → restore round-trip. Post-cycle JE also lands
correctly with the expected description (proves the round-
trip re-enabled the instantiation capability end-to-end).

### D10 — M30.2 delete-confirmation copy fulfillment

M30.2 shipped copy at `AccountingJournalEntriesPage.tsx:670-
672` read: *"You can restore this template later. (Restore UX
ships in a future milestone.)"* The parenthetical was a
shipped promise about M31 completion.

Updated to: *"You can restore this template later — turn on
**Show inactive** to find and reactivate it."*

Verified via:

- Vitest assertion in `AccountingJournalEntriesPage.test.tsx`
  updated from `/You can restore this template later/` to
  `/You can restore this template later — turn on Show
  inactive to find and reactivate it/`.
- New guard test `M31.2 — D10 delete-confirm copy points at
  the new Show inactive toggle (fulfillment)` — positive
  assertion + negative `.not.toContain("Restore UX ships in
  a future milestone")` regression guard.
- Playwright assertion in the new restore-inactive journey:
  `page.getByTestId("tmpl-delete-confirm-body").toContainText
  (/turn on Show inactive to find and reactivate it/)`.
- `git grep "Restore UX ships in a future milestone"
  frontend/ acceptance/` shows only the D10 guard test's
  assertion + comment; shipped code has zero hits.

## 3. Two durable-lesson elevations

- **Lesson (w) mutation-surface asymmetry** elevated from
  "surfaced at M30.2" to **"load-bearing across two
  milestones"** via M31.1 Restore as second dedicated
  activation verb + regression test
  `test_patch_still_cannot_mutate_is_active_after_m31`.
  Layered enforcement now covers three surfaces (serializer
  omission + service `update_fields` + endpoint regression
  tests from both M30.2 and M31.1 pathways).
- **Lesson (x) row-action truth-vocabulary asymmetry**
  elevated from "surfaced at M30.2" to **"load-bearing
  across two milestones"** via M31.2 row button "Restore"
  → confirmation title "Reactivate template?" pairing.
  Matches the M30.2 "Delete"/"Deactivate" asymmetry
  pattern.

Full retrospective at
`docs/roadmap/MILESTONE_31_RETROSPECTIVE.md` §5.

## 4. NEW durable design principle

**Lifecycle-integrity precheck governs the shape of L1-class
fail-closed guards.** When a planning-open surface
verification uncovers a partial-exposure situation (existing
feature works safely today but a new UI surface would expose
a fail-closed gap), the smallest fix is identified at the
natural enforcement layer — which is not always the layer
the new surface touches. M31.0 §4.1 traced the instantiate
flow and found it purely client-side hydration: adding a
server guard would have nothing to check because JE create
never receives the template pk. The smallest fail-closed fix
was therefore frontend-only (button disable + explanatory
aria-label). Newly surfaced at M31.0; awaits first re-
application to elevate. Full text in retrospective §5.

## 5. Baselines at M31 close

| Metric | M31.1 close | M31.2 close | Delta |
|---|---|---|---|
| Backend suite | 4,933 pass, 1 skip | 4,933 pass, 1 skip | unchanged |
| Frontend Vitest | 300 pass, 36 files | **319 pass, 36 files** | +19 |
| Acceptance journeys | 21 | **22** | +1 |
| Acceptance total tests | 27 | **28** | +1 |
| Acceptance full-suite runtime | ~35s | 32.6s | comparable |
| Migrations | 0001–0050 | 0001–0050 | unchanged |
| DRF admin surface | 118 | 118 | unchanged |
| Frontend routes | 20 | 20 | unchanged |
| Permission classes | 7 | 7 | unchanged (streak 32 → **33**) |
| Service verbs | 318 | 318 | unchanged |
| Audit endpoints | 158 | 158 | unchanged |
| Audit covered | 123 | **124** | +1 |
| Audit backend-only | 35 (transitional) | **34** | −1 |

## 6. Files changed

- `frontend/src/lib/accountingApi.ts` —
  `fetchJournalEntryTemplates` accepts
  `{ includeInactive?: boolean }`; new
  `restoreJournalEntryTemplate(pk)` wrapper.
- `frontend/src/lib/accountingApi.templates.test.ts` —
  +7 tests (3 fetchJournalEntryTemplates includeInactive +
  4 restoreJournalEntryTemplate).
- `frontend/src/pages/AccountingJournalEntriesPage.tsx` —
  `ChangeEvent` import + `restoreJournalEntryTemplate`
  import; 5 new state variables + 4 new handlers; Show-
  inactive toggle in section header; Restore success
  badge; `TemplateRow` refactored for is_active-aware
  rendering + L1 guard; `TemplateRestoreConfirmDialog`
  co-located inline; D10 delete-confirmation copy update.
- `frontend/src/pages/AccountingJournalEntriesPage.test.tsx`
  — +12 tests + 1 updated existing assertion +
  `restoreJournalEntryTemplate` mock.
- `acceptance/journeys/office/accounting_je_template.spec.ts`
  — +1 `test.describe("restore-inactive", ...)` block
  with 7-step reversible-lifecycle journey.
- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` —
  regenerated post-M31.2 (158 / 124 / 34 / 318).
- `docs/roadmap/MILESTONE_31_PLANNING.md` — frontmatter
  status flipped active → shipped;
  `shipped_at_session: SESSION_205` added.
- `docs/CAPABILITY_MATRIX.md` — §7ζ Milestone 31 section
  added between existing §7ε (M30) and §8 (Dealer
  branding).
- `docs/roadmap/MILESTONE_31_RETROSPECTIVE.md` — NEW file.

Backend files: **none touched** — M31.2 is pure frontend +
Playwright + docs.

## 7. Non-goals for SESSION_205 (all honored)

- ✅ Did NOT modify any M31.1 backend surface (Restore
  verb, endpoint, list parsing all locked).
- ✅ Did NOT add any new backend tests (M31.1 exhaustively
  covers the substrate).
- ✅ Did NOT add a migration.
- ✅ Did NOT introduce any new permission class.
- ✅ Did NOT re-open §5.a or §5.b decisions.
- ✅ Did NOT re-litigate the L1 visible-but-disabled
  framing.
- ✅ Did NOT deviate from D8 mandated copy without user
  confirmation.
- ✅ Did NOT hide inactive rows' Edit / Instantiate
  buttons (visible-but-disabled per D7 + L1).
- ✅ Did NOT rely on muted styling alone (three
  independent D6 signals shipped).
- ✅ Did NOT add server-side coupling between JournalEntry
  and JournalEntryTemplate. R1 stale-tab race remains
  accepted.
- ✅ Did NOT modify pre-M30 shipped surface (D10 is the
  only shipped-copy modification permitted at M31.2).
- ✅ Did NOT push. Coordinated M31 close push awaits
  explicit user confirmation.

## 8. What SESSION_206 (M32.0) opens

Per M31 retrospective §9 candidate list — planning-only
session:

- **Elevated for M32.0 (highest recommendation strength):**
  - NEW C — F&I chargeback substrate (sixth-link
    candidate; still gated on pilot evidence per §9;
    would continue substrate-compound-value lineage into
    a sixth link).
  - NEW O2 — Row 5 public-fetch-helper regex refinement
    (audit-tooling accuracy work; requires SESSION-189-
    §3-style tracing at open; blast radius unknown).
  - NEW O3 — Rows-1–4 plain-string-literal investigation
    (audit-tooling accuracy work; requires tracing).
  - H — Test-hygiene remediation (three shared-DB non-
    idempotent journeys unchanged since M27.2; compound
    CI-stability value grows with journey count now 22).
- **Standing question at M32.0 open:** the reversible
  template lifecycle is now complete after five
  consecutive planning-time selections in the accounting/
  templates domain (M27.1 → M28.1 → M29 → M30 → M31).
  Depth vs breadth for M32.0: F&I chargeback continues
  the depth arc if pilot evidence surfaces; a different
  domain surface (deal writeups #112–114, vendor detail
  #43, photo reorder #65, or elsewhere in the 34
  backend-only audit endpoints) provides breadth. Neither
  path is forced by evidence at M31 close.
- **Gated (unchanged):** T (real tester feedback), U
  (hosted-demo substrate), L (first-live-pilot staging),
  M (multi-operator support).
- **Deferred pending evidence:** D (LLM router / cost
  caps). **Deferred stable:** G (dashboard testid
  hardening).

### First thing SESSION_206 must do

1. Verify starting state (backend 4,933 pass, frontend
   Vitest 319 pass, acceptance 22 journeys, tsc + check +
   makemigrations clean, redis PONG, acceptance DB reset).
2. **If M31 pushed** — monitor first M31 CI run via
   `gh run list --workflow=acceptance --branch=main
   --limit 5`. If red, address as §0.a M32.0 amendments
   before opening §5.a. If green, M31 is CI-verified
   shipped; proceed to §3.
3. Regenerate audit artifact — expect **158 / 124 / 34 /
   318** to hold.
4. Present M32 candidate list per M31 retrospective §9.
5. Recommend a target under the primary operational-
   coverage lens (or its reframes if evidence supports).
   Answer the standing question (depth vs breadth) with
   evidence.
6. Await user confirmation of §5.a → draft §5.b–§5.h →
   DoD compliance check → expand M32 planning memo →
   ship the M32.0 handoff at
   `docs/handoffs/SESSION_206_m32_inc0_planning.md`.
7. **Do NOT push.** M32.0 is planning only; coordinated
   push at M32 close per M27/M28/M29/M30/M31 cadence.

## 9. Push status

**No push at SESSION_205 close.** M31 coordinated close
push awaits explicit user confirmation per M27/M28/M29/M30
close-out cadence.

Local commits at SESSION_205 close (projected):

- SESSION_205 M31.2 implementation + M31 close-out fold
  (`MILESTONE_31_RETROSPECTIVE.md`, `CAPABILITY_MATRIX.md`
  §7ζ, `MILESTONE_31_PLANNING.md` status flip, this
  handoff, `00-START-NEXT-SESSION.md` flip for SESSION_206
  M32.0) — one commit.
- Hash-backfill on this handoff frontmatter — a follow-up
  commit.

Total M31 commits at coordinated push (projected): **6**:

1. `f45a630` — SESSION_203 M31.0 planning.
2. `5d12184` — SESSION_203 M31.0 hash-backfill.
3. `b0e21a8` — SESSION_204 M31.1 backend substrate.
4. `7c1cced` — SESSION_204 M31.1 hash-backfill.
5. (this session) — SESSION_205 M31.2 UI + Playwright +
   close-out fold.
6. (this session) — SESSION_205 hash-backfill.

## 10. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M31 shipped surface in
   CAPABILITY_MATRIX §7δ + §7ε + §7ζ per convention
   adopted at M27+)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_31_RETROSPECTIVE.md`** —
   authored this session; full M31 record + M32
   candidate list + standing depth-vs-breadth question
6. `docs/roadmap/MILESTONE_31_PLANNING.md` (governing
   contract; status flipped to shipped at SESSION_205)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-
   M31.2 baseline — 158 endpoints / **124 covered** / 34
   backend-only / 318 service verbs)
8. **`docs/CAPABILITY_MATRIX.md` §7ζ** (M31 shipped
   surface record — added this session)
9. `docs/handoffs/SESSION_204_m31_inc1_backend.md` (M31.1
   backend substrate shipped)
10. `docs/handoffs/SESSION_203_m31_inc0_planning.md`
    (M31.0 planning shipped)
11. **This handoff**
    (`SESSION_205_m31_inc2_frontend.md`)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governed the D8 co-located inline-
    dialog choice at M31.2)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0 §6.6)
