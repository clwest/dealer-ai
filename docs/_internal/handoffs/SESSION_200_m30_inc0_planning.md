---
title: "SESSION_200 handoff — Milestone 30 · Increment 0 (M30.0 — planning refinement + target selection) + §0.a M29 CI regression correction"
status: historical
type: handoff
date: 2026-08-04
session: 200
milestone: 30
milestone_status: active
milestone_name: "Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern)"
increment: 0
increment_status: shipped
commit: 43b715b
commit_notes: "43b715b is the §0.a amendment + M30 planning memo commit (pushed to restore red main). The SESSION_200 handoff + 00-START-NEXT-SESSION.md flip land in a follow-up local-only commit per planning-only session cadence; hash backfill via a subsequent commit."
---

# SESSION_200 — Milestone 30 · Increment 0 (M30.0 — planning refinement + target selection) + §0.a M29 CI regression correction

## What shipped

SESSION_200 opened as a planning-only session per the
M29.2 close-out priorities in `00-START-NEXT-SESSION.md`.
Three deliverables landed:

1. **M30.0 planning memo** authored at
   `docs/roadmap/MILESTONE_30_PLANNING.md` — target locked
   as **Template edit / delete UI** (§5.a, user-confirmed
   with two additional architectural verifications directed
   at open). All §5.b–§5.h decisions locked (D1–D8, risk
   register, verifications, phasing, DoD compliance,
   rollback, non-goals). Substrate-compound-value continuation
   framing carries into the fourth link on the M28+M29
   template surface.
2. **§0.a M30.0 amendment** — the first M29 CI acceptance
   run turned red at
   `journeys/office/accounting_je_template.spec.ts:213`
   because a pre-existing M28.2 fixed-line assertion still
   referenced the old `getByLabel("Line 1 debit")` input
   shape after M29.2 replaced it with a `LockedAmountChip`.
   Fix committed + pushed as `43b715b` under the "restore
   red main" push-cadence exception. Second CI run post-
   correction: **26 passed / 0 failed / 2m43s** — main
   restored to shipped-baseline green.
3. **M29 retrospective update** — new durable lesson
   recorded in §5 ("When changing the semantic shape of an
   established UI element, sweep the full acceptance suite
   for stale selectors + assertions on that element");
   correction record added to §8 with cross-reference to
   the §0.a amendment.

Full active memo authored at
`docs/roadmap/MILESTONE_30_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean, `HEAD ==
  origin/main @ e01cfde` (M29 push confirmed pre-session),
  Redis PONG, Django `check` clean, `makemigrations --check`
  clean, frontend `tsc --noEmit` clean, acceptance
  `tsc --noEmit` clean. Backend suite **4,871 pass, 1
  skipped, 0 fail** (172.9s). Frontend Vitest **282 pass**
  (36 files). All matches M29.2 close baseline exactly.
- **First M29 CI run monitored (§2):** acceptance workflow
  on `e01cfde` (M29.2 hash-backfill commit) **completed
  failure** in 2m44s. One failed / 25 passed:
  `accounting_je_template.spec.ts:213` "owner can
  instantiate a template into a balanced posting via the
  pre-populated JE dialog" — the pre-existing M28.2 journey
  broke on M29.2's chip UI change. Immediately triaged as a
  §0.a M30.0 amendment per the start-here §2 rule
  ("If red: address as §0.a M30.0 amendments before opening
  §5.a").
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **156 total / 122 covered / 34 backend-only / 315
  service verbs**. Byte-identical to the committed M29.2
  artifact — no drift.
- **Candidate list presented (§4)** across the M29 §9 tiers:
  - **Elevated (highest recommendation strength):** NEW
    template edit / delete UI; NEW C — F&I chargeback
    substrate; NEW O2; NEW O3; H test-hygiene remediation.
  - **Gated:** T, U, L, M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - **Deferred at M29 §3 / M28 §3 / M27 §3 / M25 §4:** all
    carried forward unchanged.
- **Recommendation (§5):** NEW template edit / delete UI,
  under the primary operational-coverage lens (mid-year
  chart-of-accounts corrections and stale-template cleanup
  currently force Django-shell access) plus the substrate-
  compound-value continuation framing (fourth link on the
  M28+M29 template lineage).
- **User confirmation:** §5.a locked as **NEW Template
  edit / delete UI** with two additional architectural
  verifications required before locking §5.b (dialog
  consolidation + soft-delete integrity). Both verifications
  performed at planning-open (see §6 below).
- **Both verifications resolved CLEAN.** Additive-mode
  pattern chosen for the dialog (direct application of
  M29.2 durable lesson (t)). Soft-delete integrity confirmed
  by construction (no FK from `JournalEntry` to
  `JournalEntryTemplate` per M28.0 §5.b rejection; grep
  sweep of `backend/dealer_ai/**/*.py` confirms).
- **§5 locks (all):** target (§5.a), eight load-bearing
  design decisions D1–D8 (§5.b), risk register (§5.c),
  verifications (§5.d), two-increment phasing (§5.e), DoD
  compliance (§5.f — exception path at M30.1 as fifth
  precedent, direct satisfaction at M30.2), rollback plan
  (§5.g), non-goals (§5.h).
- **§0.a M30.0 amendment shipped:** test-assertion update
  to `accounting_je_template.spec.ts` lines 291–306 (chip
  test-id + `toContainText` instead of input `toHaveValue`).
  Verified via isolated re-run (7 passed) → full suite on
  fresh DB (26 passed / 0 failed / 31.5s local) → CI run on
  push (**26 passed / 0 failed / 2m43s**).
- **Push cadence exception invoked:** correction pushed
  immediately as `43b715b` (not deferred to M30 close) to
  restore red `main` to green. Subsequent M30 planning
  artifacts (this handoff + `00-START-NEXT-SESSION.md`
  flip) land in a follow-up local-only commit resuming the
  normal planning-only cadence.

## 1. Verification results at open

| Check | Expected | Actual |
|---|---|---|
| `git status` | clean | ✅ clean |
| `HEAD == origin/main` | true | ✅ true (e01cfde) |
| `git log --oneline -10` top | M29.2 hash backfill | ✅ e01cfde |
| Backend suite | 4,871 pass, 1 skip | ✅ 4,871 pass, 1 skip (172.9s) |
| Frontend Vitest | 282 pass, 36 files | ✅ 282 pass, 36 files (6.4s) |
| Django `check` | clean | ✅ clean |
| `makemigrations --check` | No changes | ✅ No changes |
| Frontend `tsc --noEmit` | clean | ✅ clean |
| Acceptance `tsc --noEmit` | clean | ✅ clean |
| `redis-cli ping` | PONG | ✅ PONG |
| Audit artifact | 156 / 122 / 34 / 315 | ✅ 156 / 122 / 34 / 315 (byte-identical) |
| First M29 CI run | green (expected) | ❌ **RED** (1 failed / 25 passed) — triggered §0.a |

## 2. First M29 CI run

Run ID: `30919344101`. Status: **failure**. Duration: 2m44s
on `main` at commit `e01cfde` (M29.2 hash-backfill commit).

Failure: `accounting_je_template.spec.ts:213` "owner can
instantiate a template into a balanced posting via the pre-
populated JE dialog" — the pre-existing M28.2 assertion at
lines 295–300 called `dialog.getByLabel("Line 1 debit")
.toHaveValue(/^1275(\.00)?$/)`, but M29.2 changed the
amount cell for fixed template lines from `<Input aria-label
="Line 1 debit">` to `LockedAmountChip aria-label="Line 1
debit amount (from template)" data-testid="je-line-0-debit-
chip"`. Aria-label no longer resolves; timeout 5000ms.

Confirmed as an intentional-UI-shape regression on a stale-
selector M28.2 test (not a bug in M29.2 shipped behavior).
Local vitest + tsc + frontend build cannot catch stale
Playwright selectors; only the acceptance suite catches
them.

## 3. §0.a M30.0 amendment — the fix

**Trigger + root cause + verification** — see
`docs/roadmap/MILESTONE_30_PLANNING.md` §0.a.1 for the
full record.

**Fix scope** — one file, one journey:
`acceptance/journeys/office/accounting_je_template.spec.ts`
lines 291–306: replace `dialog.getByLabel("Line 1 debit")
.toHaveValue(...)` with `dialog.getByTestId("je-line-0-
debit-chip").toContainText(/\$1275\.00/)` (and companion
for Line 2 credit). Six-line comment documents the M29.2
shape change + reference to §0.a.

**Verification sequence:**

1. Reproduce failing spec locally — same error trace as CI
   (aria-label resolves to zero elements after M29.2).
2. Apply fix; re-run same spec — 7 passed / 0 failed.
3. Full acceptance suite (pre-existing DB) — 24 passed /
   2 failed, both failures in known H (test-hygiene)
   shared-DB-state journeys unrelated to template/JE UI.
4. `rm backend/db.acceptance.sqlite3` → Playwright's
   `webServer` migrate step recreates fresh DB → re-run
   full suite — **26 passed / 0 failed / 31.5s**.
5. Grep sweep across `acceptance/journeys/**/*.spec.ts`
   for `getByLabel\("Line \d+ (debit|credit)"\)` — all
   remaining call sites correct-by-context (variable-line
   inputs, blank-entry journeys).

**Commit + push:** `43b715b`, pushed to `origin/main` under
push-cadence exception ("restore red main trumps normal
coordinated-push cadence" — user-authorized).

## 4. Second M29 CI run (post-§0.a)

Run ID: `30926157616`. Status: **success**. Duration:
2m43s on `main` at commit `43b715b` (§0.a amendment).
**26 passed / 0 failed.** Main restored to shipped-baseline
green.

## 5. Audit regeneration

`python3 -m dealer_ai.scripts.audit_operational_surface`
produced **156 total / 122 covered / 34 backend-only / 315
service verbs**. Byte-identical to the committed M29.2
artifact. No drift.

## 6. Two architectural verifications performed at planning-open

Both directed by user at §5.b lock request. Full records
in `docs/roadmap/MILESTONE_30_PLANNING.md` §4.6 and §4.7.

### 6.1 Dialog consolidation — CLEAN, additive-mode chosen

Inspection of `NewJournalEntryTemplateDialog.tsx` (513
lines) confirmed a self-contained component with baked-in
`+ New template` trigger, internal state, and ~200 lines of
`TemplateLineRow` + validation + `TemplateBalanceIndicator`
that would be pure duplication if forked into an edit
dialog. Three patterns evaluated:

- **Pattern A (chosen):** additive-mode props on the
  existing component. `mode?: "create" | "edit"` (default
  create), `initialTemplate?`, `onEdited?`, controlled-
  open `open` + `onOpenChange` pair. Rename
  `NewJournalEntryTemplateDialog.tsx` →
  `JournalEntryTemplateDialog.tsx` via `git mv` + import
  sweep in same commit per `DOC_GOVERNANCE.md` §5.
  Direct application of M29.2 durable lesson (t) — the
  additive-prop pattern for UI reuse.
- **Pattern B rejected:** extract shared subcomponents +
  two dialog wrappers. Two wrappers still diverge on
  trigger, submit, reset, success flow — larger PR surface
  than Pattern A.
- **Pattern C rejected:** fork with duplication. Maximum
  divergence risk — the failure mode M29.2 lesson (t)
  exists to prevent.

**Instantiate stays separate** — explicit design decision.
The M29.2 pattern (`templateToInitialValues` +
`templateToLockedLines` + `NewJournalEntryDialog(lockedLines
=…)`) already correctly models template → JE conversion,
which is not a template mutation. Folding instantiate into
the template dialog would violate M28.0 §5.b domain
separation and the M13.1 single-posting-path contract.

### 6.2 Soft-delete integrity — CLEAN by construction

Grep sweep across `backend/dealer_ai/**/*.py` for
`template_id`, `journal_entry_template`, `from_template`,
`instantiate_from_template`, and any FK from
`JournalEntry` to `JournalEntryTemplate` — none exists
outside the template model file itself. M28.0 §5.b rejected
fusing template + posting domains via an `is_template`
flag; instantiation copies template values into a fresh
`JournalEntry` and records no back-reference.

All four operator-behavior criteria pass by construction:

- **(a) Inactive templates disappear from lists.**
  `list_journal_entry_templates` filters `is_active=True`
  by default (`services/accounting/template.py:263`); view
  calls without `include_inactive` kwarg
  (`views_accounting.py:832`). Zero-effort.
- **(b) Existing JEs unchanged.** No FK → soft-delete
  (or hard-delete) has zero effect on any historical JE.
- **(c) Historical reporting intact.** Trial balance,
  snapshots, JE list, JE detail all read from
  `JournalEntry` + `JournalEntryLine` + `GLAccount` — no
  template dependency.
- **(d) `include_inactive` stays additive.** Service
  kwarg already exists; future `?include_inactive=true`
  endpoint exposure is one-line view-layer passthrough.
  `get_journal_entry_template` gets the symmetric kwarg
  at M30.1 for API consistency.

**Locked design constraint surfaced from the verification:**
delete UI copy must say "Deactivate" (not "Delete forever")
and reassure "Historical journal entries created from this
template are not affected." Locked at §5.b D3.

## 7. §5 locks summary

All eight §5.b design decisions D1–D8 locked in the memo.
The most detailed decisions are:

- **D1 — Backend endpoints.** One new URL:
  `admin/accounting/journal-entry-templates/<int:pk>/`
  supporting PATCH (full-replace) + DELETE (soft — sets
  `is_active = False`). PATCH silently ignores `is_active`
  in body (activation is DELETE-only, not editable). DELETE
  is idempotent (already-inactive → 204).
- **D2 — Dialog consolidation** (additive-mode pattern per
  §6.1 above).
- **D3 — Delete UI** (row-level Delete button + AlertDialog
  confirmation with mandated "Deactivate" copy + historical-
  entries reassurance).
- **D4 — Edit UI** (row-level Edit button + controlled-open
  pattern; `handleEditClick` + `handleEdited` +
  `editingTemplate` state on `AccountingJournalEntriesPage`).
- **D5 — Soft-delete integrity** (documented in full at
  §4.7 / §6.2 above).
- **D6 — Backend test surface** (~22 new tests: 14 service +
  7 endpoint + 1 model).
- **D7 — Frontend test surface** (~18 new: rename existing
  test file + 8 dialog extensions + 5 page extensions + 4 API
  extensions).
- **D8 — Playwright journey** (single new
  `test.describe("edit-delete", ...)` block in
  `accounting_je_template.spec.ts`; journey count 20 → 21).

**Coverage delta at M30 close (projected):** 156 → 157
endpoints (+1); 122 → 123 covered (+1); 34 backend-only
unchanged. Two-source agreement gate at M30.2 close.

## 8. Streaks at M30.0 close

- **Planning-time as-recommended streak:** 8 → **9**. Target
  selected as recommended after five-alternative comparison
  + two architectural verifications performed at user
  direction. §0.a amendment does not affect the streak
  (corrective, not scope selection). Historical run of 89
  across M10 → M23 preserved for the record.
- **Zero-drift permission-class streak:** unchanged at 29
  (M10 → M29). M30.0 is planning-only; no code change.
  §0.a fix touches only a test file, not a permission
  class. Projection at M30 close: **31 consecutive** (M30.1
  adds new detail endpoint reusing existing permission
  class; M30.2 no permission change).
- **Substrate-compound-value continuation:** 3 links
  realized (M27.1 → M28.1 → M29). Projected 4 at M30 close.
- **DoD exception path invocations:** 4 (M26 + M27.1 +
  M28.1 + M29.1). Projected 5 at M30.1 close.
- **Additive-prop pattern re-application:** first re-
  application at M30.2 (D2 dialog consolidation) — would
  elevate lesson (t) from "surfaced" to "load-bearing
  across two milestones."

## 9. Baselines expected at close

Session-local (post-§0.a) values:

- Backend: 4,871 pass, 1 skip, 0 fail — unchanged.
- Frontend Vitest: 282 pass across 36 files — unchanged.
- Acceptance: 20 journeys (unchanged in count; one
  assertion updated to match the M29.2 chip UI).
- Audit coverage: 122 / 156 — unchanged.
- DRF admin surface: 116 endpoints — unchanged.
- Frontend operator routes: 20 — unchanged.
- Permission classes: 7 actual — unchanged.
- Migrations: `0001`–`0050` — unchanged.

Files changed:

- `acceptance/journeys/office/accounting_je_template.spec.ts`
  (§0.a fix — 22 lines changed).
- `docs/roadmap/MILESTONE_29_RETROSPECTIVE.md` (new durable
  lesson in §5 + correction record in §8 — 51 lines added).
- `docs/roadmap/MILESTONE_30_PLANNING.md` (new file —
  ~1000 lines including §0.a subsection).
- This handoff (new file).
- `00-START-NEXT-SESSION.md` (overwritten for SESSION_201
  M30.1).

## 10. Non-goals for SESSION_200 (all honored)

- ❌ Did not ship any M30 backend or frontend implementation
  code.
- ❌ Did not open any M30 implementation increment.
- ❌ Did not force-push or amend earlier commits (§0.a fix
  is a normal forward commit).
- ❌ Did not modify M1–M29 shipped surface (§0.a touches
  only a test assertion, not shipped operator behavior).
- ❌ Did not skip the DoD compliance check (§5.f — exception
  path at M30.1 as fifth precedent, direct satisfaction at
  M30.2).
- ❌ Did not skip the downstream / substrate / FK-
  discoverability verification (all six §4 subsections
  performed).
- ❌ Did not re-litigate the M29.0 D3 implementation-
  boundary verification (the additive-prop pattern was
  locked and proven correct at M29.2; M30.2 re-applies it).
- ❌ Did not resume M30 planning momentum before CI green
  post-§0.a (per user direction — CI monitored to green
  before writing this handoff).

## 11. What SESSION_201 (M30.1) opens

- Backend substrate per D1 + D6.
- New detail endpoint
  `admin/accounting/journal-entry-templates/<int:pk>/`
  supporting PATCH + DELETE.
- New service verbs `update_journal_entry_template` +
  `delete_journal_entry_template` + symmetric
  `include_inactive` kwarg on `get_journal_entry_template`.
- ~22 new backend tests (D6).
- No frontend, no acceptance change.
- DoD exception path (fifth precedent — pattern well-
  established).
- Two-source agreement gate at close.
- **Local commits only; coordinated push at M30 close.**
  (Distinct from the §0.a push exception in this session —
  that was a corrective hotfix; M30.1 resumes the normal
  planning + implementation-increment cadence.)

See `00-START-NEXT-SESSION.md` for the SESSION_201 opening
brief.

---

**Retrospective handoff note.** SESSION_200 was intended as
a pure planning session and shipped one planning memo as
expected. The §0.a M29 CI regression correction was an
unplanned corrective sub-task that surfaced during §1
starting-state verification (specifically §2 CI monitoring)
and executed cleanly per user direction: reproduce → fix →
verify isolated → verify full suite on fresh DB → record
as §0.a amendment → commit + push under exception → monitor
CI to green → resume planning finalization. Total elapsed
correction time: ~40 minutes end-to-end. Zero scope change
to M30 target or §5 locks.
