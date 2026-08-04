---
title: "SESSION_193 handoff — Milestone 27 · Increment 2 (M27.2) + close-out fold"
status: historical
type: handoff
date: 2026-08-03
session: 193
milestone: 27
milestone_status: shipped
milestone_name: "Journal-Entry Creation UI (via shared GLAccount substrate)"
increment: 2
increment_status: shipped
commit: pending-post-push
---

# SESSION_193 — Milestone 27 · Increment 2 (M27.2 — JE-create dialog + Playwright) + close-out fold

## What shipped

M27.2 delivers all remaining operator-facing value for
Milestone 27: the "+ New journal entry" dialog attached to
the existing JE list page, the searchable GLAccount picker,
the `createJournalEntry` wrapper, twenty new component
vitests, and a Playwright peer spec with two test cases
covering both successful creation and cancel-without-
persistence. M27.3 close-out folds into M27.2 per §5.h
Option B — both increments' §5.e Phase 1 + Phase 2
verifications passed cleanly on the first regeneration.

### Frontend page extension

- **`frontend/src/pages/AccountingJournalEntriesPage.tsx`** —
  extended in place per M27.0 §5.b substrate-attachment
  rule (no new frontend route). Added:
  - Second `useEffect` to fetch the full CoA on mount via
    the M27.1 `fetchGLAccounts` wrapper.
  - "+ New journal entry" button in the page header (peer
    of the title), disabled when accounts.length < 2 or
    the CoA fetch failed.
  - Inline emerald success badge above the entries table
    on successful creation, dismissed on next mount.
  - `handleCreated` callback that jumps to page 1 if the
    operator was elsewhere in the pagination (recent-first
    ordering ensures the new entry surfaces where the
    badge sits) or refetches the current page.
  - CoA fetch-error inline message when
    `fetchGLAccounts` fails.

### Two new components

- **`components/accounting/GLAccountPicker.tsx`** — searchable
  single-select over the M27.1 CoA payload. Client-side
  filter matches BOTH `code` AND `name` case-insensitively
  per M27.0 §5.b user direction. Built on the shipped
  `Input` primitive rather than shadcn `Command` — the
  installed shadcn subset does not include `Command`/`Popover`,
  and CLAUDE.md frontend-stack notes forbid re-running
  `npx shadcn init` under the current v3+v4 bridge. Renders
  a search box + scrollable list when nothing is selected;
  swaps to a "code — name" pill + Change button when a
  value is set. Emits `onChange(id)` on click and
  `onChange(null)` on Change.
- **`components/accounting/NewJournalEntryDialog.tsx`** —
  modal dialog reusing the M14.4 reversal-dialog pattern
  from `AccountingJournalEntryDetailPage`. Fields:
  description (required textarea), `posted_at` (date input
  defaulting to today's local date via a helper that
  formats `YYYY-MM-DD`), and a dynamic lines table with
  minimum 2 lines enforced. Each line renders a
  `GLAccountPicker` + debit/credit number inputs + optional
  memo. `LineRow` internal component handles the per-row
  rendering. `BalanceIndicator` internal component shows
  live `Σ debits · Σ credits` with a green "Balanced" badge
  when equal + non-zero, or a red "Unbalanced by $X" /
  "Enter amounts" badge otherwise. Client-side validation
  blocks submit unless description non-empty + every line
  has picked account + every line non-zero on exactly one
  side + balanced.
- **UI regression discovered + fixed during Playwright run:**
  first journey run failed because the dialog was taller
  than Playwright's default 1280×720 viewport, pushing
  submit + cancel offscreen. Fix: `DialogContent` given
  `max-h-[90vh] flex-col` + inner body given
  `overflow-y-auto pr-1` so the footer stays fixed while
  the middle scrolls. Both journey test cases green after
  the fix. New durable design principle recorded to M27
  retrospective §5(e).

### New wrapper

- **`frontend/src/lib/accountingApi.ts`** — added
  `CreateJournalEntryLine`, `CreateJournalEntryPayload`
  types + `createJournalEntry` wrapper (~30 LOC with
  header comment). Envelope + Decimal-as-string
  conventions match the existing `reverseJournalEntry`
  wrapper verbatim.

### Component vitests (+20)

- **`components/accounting/GLAccountPicker.test.tsx`** — 8
  tests covering: renders all accounts when no query set;
  filters by account code; filters by account name;
  filters case-insensitively; empty-state message when no
  accounts match; fires onChange with picked id; shows
  selected pill when value set; clears via Change button.
- **`components/accounting/NewJournalEntryDialog.test.tsx`**
  — 9 tests covering: renders trigger button; disables
  trigger when <2 accounts; opens dialog on click;
  posted_at defaults to today; blocks submit until
  balanced with description; shows "Balanced" badge when
  debits = credits; posts payload + fires onCreated on
  success; inline server-error banner keeps dialog open;
  cancel closes without invoking API.
- **`pages/AccountingJournalEntriesPage.test.tsx`** —
  extended with a new `fetchGLAccounts` mock at
  `beforeEach` (existing 14 tests continue to pass) + 3
  new M27.2 tests: renders trigger button; disables trigger
  when CoA has <2 accounts; surfaces CoA fetch-error
  message.

### Playwright journey

- **`acceptance/journeys/office/accounting_je_create.spec.ts`**
  — peer of the M22.2 reversal spec (extend-vs-add decision
  landed at add-peer for consistency with the M22.2
  precedent shape). Two test cases per §5.d:
  1. **Successful create** — owner navigates to
     `/dealer-ai-accounting/journal-entries`, waits for
     the "+ New journal entry" trigger to enable (indirect
     signal that the M27.1 CoA fetch resolved), opens the
     dialog, fills a description with a unique per-run
     `Date.now()` token, confirms `posted_at` field value
     matches today's local date, picks line 1 via CODE
     search ("110" → 110000 Bank), enters $125.00 debit,
     picks line 2 via NAME search ("Sales" → 400000
     Vehicle Sales — Retail) (both picker search modes
     exercised per §5.d), enters $125.00 credit, confirms
     balance indicator flips to "Balanced" and submit
     enables, clicks Create, dialog closes, success badge
     visible, new entry surfaces in the list via
     run-token substring match. Business-outcome
     assertion via admin API: entry exists with correct
     description prefix, is not a reversal, total_debit =
     125.00, detail projection carries account_codes
     "110000" (debit line) + "400000" (credit line).
  2. **Cancel without persistence** — owner records
     baseline count of entries with the cancel-test
     prefix (guaranteed 0 by per-run token), navigates to
     the JE list, opens the dialog, fills partial form
     (description + one line only — deliberately
     insufficient to satisfy the balanced-two-line submit
     requirement), clicks Cancel, dialog closes with no
     confirmation prompt. Post-cancel assertions: no
     success badge visible; admin API count of entries
     with the cancel-test description = 0 (persistence
     never happened).
- Seed: `seed_journey_office_accounting_workflow`
  (existing since M20.3 + M22.2) already invokes
  `seed_default_coa` on every run, guaranteeing the
  tenant has ≥2 GLAccounts including `110000` Bank —
  Operating and `400000` Vehicle Sales — Retail. No
  seed extension needed.

### Documentation

- **`docs/CAPABILITY_MATRIX.md`** — §7β block updated:
  status flipped from "in progress" to "shipped", M27.2
  row backfilled with full shipped-surface detail
  (button + dialog + picker + wrapper + component
  vitests + Playwright spec + audit-flip evidence + UI
  viewport-fix note), test-baseline row updated to
  reflect the full 4,813 backend + 246 vitest + 16
  journey / 22 acceptance-run baseline at M27 close.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** — added
  new "Milestone 27 — Journal-Entry Creation UI (via
  shared GLAccount substrate) — SHIPPED at SESSION_193"
  block matching the M26 shape.
- **`docs/roadmap/MILESTONE_27_RETROSPECTIVE.md`** — NEW,
  mirroring the M26 retrospective shape: §1 planned
  scope, §2 what actually shipped (per-increment
  breakdown), §3 deviations (3 in-scope refinements —
  vitest convention deferral, picker-primitive choice,
  DialogContent viewport fix), §4 deferrals (all M27
  §3 items held), §5 five durable design principles (2
  NEW at M27 — FK-discoverability lesson + test-driven
  UI viewport constraint; plus reinforcements of
  substrate-attachment, shared-infrastructure framing,
  DoD exception path), §6 streak accounting (26 → 27
  permission-class; 5 → 6 planning-time), §7 baselines
  table, §8 corrections (none at close), §9 M28
  evidence-based candidates (NEW recurring journal
  templates elevated; O2 / O3 / H unchanged from M26).
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`** —
  regenerated per §5.e M27.2 protocol. Row 140
  (`admin/accounting/journal-entries/`) flipped
  `defer-candidate-O2` → `covered` with wrapper
  `accountingApi.ts:377 createJournalEntry`. Row 149
  (`admin/accounting/gl-accounts/`) flipped
  `defer-candidate-O2` (M27.1 state) → `covered` with
  wrapper `accountingApi.ts:343 fetchGLAccounts` (M27.2
  gains a non-test consumer via the dialog). Coverage
  summary 119 / 155 → **121 / 155**. Backend-only 36
  → 34.
- **`00-START-NEXT-SESSION.md`** — overwritten with
  SESSION_194 (M28.0 planning) priorities. Records M27
  shipped operational state, M28 candidate list
  (elevated: NEW recurring templates, O2, O3, H),
  updated streak counters (permission-class 27,
  planning-time 6), and the durable-lesson index
  including the M27 additions.

## §5.e verification — two-source agreement ✅ (both increments)

**M27.1 close** (SESSION_192 — recorded in that handoff,
re-verified this session at start):

- Phase 1 (artifact): 154 → 155 / 119 covered / 35 → 36
  backend-only. New row 149 disposition
  `defer-candidate-O2` with `⚠ wrapper-only` ✅
- Phase 2 (repo inspection): view symbol matches,
  `_M131_PERMS` applied, GET method matches, wrapper at
  correct file:line, wrapper NOT called by any non-test
  component (matches the "⚠ wrapper-only" audit
  disposition) ✅

**M27.2 close** (this session):

- Phase 1 (artifact): 155 unchanged / 119 → **121
  covered** / 36 → **34 backend-only** ✅
- Phase 2 (repo inspection):
  - Row 140: wrapper `createJournalEntry` exists at
    `accountingApi.ts:377`, uses `authPostJSON`, calls
    the correct path `/admin/accounting/journal-entries/`,
    imported by `components/accounting/NewJournalEntryDialog.tsx`
    (non-test) ✅
  - Row 149: wrapper `fetchGLAccounts` exists at
    `accountingApi.ts:343`, uses `authGetJSON`, calls the
    correct path `/admin/accounting/gl-accounts/`,
    imported by `pages/AccountingJournalEntriesPage.tsx`
    (non-test) ✅

Both sources agree at both increment closes. Baselines
recorded across CAPABILITY_MATRIX §7β, IMPLEMENTATION_ROADMAP
§Milestone 27, MILESTONE_27_RETROSPECTIVE §7, and this
handoff's baseline block. Close-out folded per §5.h Option B.

## Verification / baselines at close

- **Backend:** **4,813 pass, 1 skipped, 0 fail** (unchanged
  from M27.1 close — M27.2 adds no backend code; wires the
  pre-existing `admin_journal_entry_create` endpoint).
- **Frontend Vitest:** **226 → 246 pass across 32 → 34
  files** (+20 across GLAccountPicker.test.tsx (+8),
  NewJournalEntryDialog.test.tsx (+9),
  AccountingJournalEntriesPage.test.tsx (+3 M27.2
  assertions)).
- **Acceptance:** **14 → 16 journeys** (+2 test cases in
  the new `accounting_je_create.spec.ts` peer spec). Full
  clean-DB dry-run baseline: **22 passed (~30s)** (6
  setup + 16 journeys).
- **Django check:** clean.
- **Migrations:** no changes detected (no schema change
  at M27 — GLAccount already exists from M13.1).
- **Frontend + acceptance `tsc --noEmit`:** clean.
- **Redis:** PONG (verified at session start).
- **Audit artifact:** 155 total / **121 covered** / 34
  backend-only / 312 service verbs.

**Note on H test-hygiene:** the M27.2 full-suite run
initially showed 3 failures
(`sales_manager/daily_startup`, `recon/workflow`,
`office/accounting_workflow`). Root cause verified as the
pre-existing 3 shared-DB non-idempotent journeys tracked
as Candidate H since M25 — the polluted acceptance test DB
(`backend/db.acceptance.sqlite3`) causes deterministic
collision failures on re-run. After resetting the test DB
(`rm db.acceptance.sqlite3`), the full acceptance run
passes 22/22 as expected. **This is NOT a M27.2
regression** — my new spec is idempotent (uses per-run
`Date.now()` tokens in every description prefix). Recorded
in the M27 retrospective §4 (deferrals — H) and the M28
handoff §9 evidence (H elevated as an M28 candidate with
the 3 failing journeys now enumerated).

## What changed in the repo

- **Modified:** `frontend/src/lib/accountingApi.ts` (+~35
  LOC — createJournalEntry wrapper + types).
- **Modified:** `frontend/src/pages/AccountingJournalEntriesPage.tsx`
  (~+60 LOC — CoA fetch effect, header button, success
  badge, handleCreated callback, error surface, imports).
- **Modified:** `frontend/src/pages/AccountingJournalEntriesPage.test.tsx`
  (~+40 LOC — fetchGLAccounts mock in beforeEach, +3
  M27.2 test cases).
- **Created:** `frontend/src/components/accounting/GLAccountPicker.tsx`.
- **Created:** `frontend/src/components/accounting/GLAccountPicker.test.tsx`
  (8 test methods).
- **Created:** `frontend/src/components/accounting/NewJournalEntryDialog.tsx`.
- **Created:** `frontend/src/components/accounting/NewJournalEntryDialog.test.tsx`
  (9 test methods).
- **Created:** `acceptance/journeys/office/accounting_je_create.spec.ts`
  (2 test cases in one spec).
- **Modified:** `docs/CAPABILITY_MATRIX.md` (§7β status
  flip + M27.2 row backfill + test-baseline row update).
- **Modified:** `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  (new M27 shipped block).
- **Created:** `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md`.
- **Modified:** `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  (regenerated — coverage summary updates + rows 140 +
  149 flip to `covered`).
- **Modified:** `00-START-NEXT-SESSION.md` — overwritten
  with SESSION_194 (M28.0 planning) priorities.
- **Created:** `docs/handoffs/SESSION_193_m27_close.md` —
  this handoff.

## Deferrals / follow-on items

All deferrals recorded in
`MILESTONE_27_RETROSPECTIVE.md` §4 + §9. Summary:

- Standalone Chart of Accounts page/route/nav entry (per
  user substrate-attachment direction).
- Trial Balance changes.
- JE edit / update endpoints.
- JE templates / recurring journals — **NEW elevated M28
  candidate** (would demonstrate M27.1 substrate compound
  value).
- `posted_by_user` override in JE dialog.
- Advanced picker filtering / server-side gl-accounts
  search / pagination / `?include_inactive=true`.
- **O2** (row-5 public-fetch-helper regex) — remains M28+
  candidate (unchanged from M26).
- **O3** (rows-1–4 plain-string investigation) — remains
  M28+ candidate (unchanged from M26).
- **H** (test-hygiene) — remains M28+ candidate; 3
  failing journeys now enumerated
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow`).
- All M25 §4 deferrals — remain valid for later re-entry.
- Gated / deferred candidate pool unchanged.

## Non-goals achieved (SESSION_193)

- ❌ No standalone Chart of Accounts page, route, or nav
  entry created (per user direction at M27.0 §7).
- ❌ No Trial Balance modifications (report page
  untouched).
- ❌ No JE edit / update endpoints added.
- ❌ No JE templates / recurring-journal workflow shipped.
- ❌ No `posted_by_user` override in the dialog.
- ❌ No advanced filtering added to the account picker
  (text search over code + name only).
- ❌ No server-side search or pagination on `gl-accounts`.
- ❌ No M26-deferred O2 (row-5 public-fetch-helper) or O3
  (rows-1–4 plain-string) audit refinement.
- ❌ No test-hygiene remediation (H) — kept separate;
  M28+ candidate.
- ❌ No hand-edit of
  `M21_OPERATIONAL_SURFACE_AUDIT.md` (regenerated only).
- ❌ No M27 baseline recorded without both §5.e sources
  agreeing (they did at both increment closes).
- ❌ No push (per §5.h + explicit user reminder to hold
  push until after M27 completes — the coordinated push
  awaits user confirmation).

## Streak accounting at M27.2 close (milestone close)

- **Zero-drift permission-class streak:** enters M27 at
  26. M27 adds one new endpoint (M27.1
  `admin/accounting/gl-accounts/`) reusing `_M131_PERMS`;
  wires one existing endpoint (M27.2 create wiring).
  No permission classes evolve. **Extends to 27
  consecutive milestones (M10 → M27).**
- **Planning-time as-recommended streak:** 6 at M27.2
  close. M27.0 target A2 locked as recommended after
  four alternatives presented under two framings; §7
  substrate-attachment scope adjustment refined shape
  without shifting target (empirical-discovery-refinement
  precedent). M27.1 + M27.2 both pure implementation
  increments executing the M27.0 locked plan. Streak
  unchanged through both implementation increments.
  Historical run of 89 across M10 → M23 preserved for
  the record.

## Next session (SESSION_194 — M28.0 planning)

Per the overwritten `00-START-NEXT-SESSION.md`:

1. Verify M27 close baseline holds (backend 4,813,
   frontend 246, acceptance 16 journeys clean-DB,
   audit 155 / 121 / 34, HEAD at M27.2 hash backfill
   or later).
2. If M27 pushed by then: monitor first M27 CI run;
   address any regressions as §0.a M28.0 amendments.
3. Regenerate audit to confirm 155 / 121 holds.
4. Present the M28 candidate list per M27 retrospective §9
   (elevated: NEW recurring journal templates, O2, O3, H;
   gated: T / U / L / M; deferred: D / C / G).
5. Recommend a target under the primary operational-
   coverage lens (recurring templates would demonstrate
   M27.1 substrate compound value) or a reframe if
   evidence supports it.
6. Await user confirmation of §5.a.
7. Draft §5.b–§5.h.
8. §7 verification — **including FK / identifier
   discoverability check per the M27.0 durable lesson**.
9. DoD compliance check on §3 draft.
10. Expand M28 planning memo.
11. Ship the M28.0 handoff.

## Anchors that win on conflict (M27.2 close)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_27_PLANNING.md` §5 (all
   locks)
4. `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md` §3
   (deviations) + §5 (durable lessons) + §9 (M28
   candidates)
5. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (current 121 / 155 baseline; source of truth
   post-M27)
6. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 27
   (shipped block)
7. `docs/CAPABILITY_MATRIX.md` §7β (M27 shipped
   surface)
8. `backend/dealer_ai/views_accounting.py`
   (`admin_gl_account_list` at M27.1 +
   `admin_journal_entry_create` at M13.1 — wired at
   M27.2)
9. `frontend/src/pages/AccountingJournalEntriesPage.tsx`
   (M27.2 header button + success badge + CoA fetch)
10. `frontend/src/components/accounting/NewJournalEntryDialog.tsx`
    (M27.2 dialog contract)
11. `frontend/src/components/accounting/GLAccountPicker.tsx`
    (M27.2 picker contract)
12. `acceptance/journeys/office/accounting_je_create.spec.ts`
    (M27.2 journey contract — both test cases)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
14. `docs/handoffs/SESSION_191_m27_inc0_planning.md`
    (M27.0 close — §5 locks + §7 discovery)
15. `docs/handoffs/SESSION_192_m27_inc1_substrate.md`
    (M27.1 close — substrate + wrapper)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
