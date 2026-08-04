---
state: active
date: 2026-08-04
last_session_shipped: SESSION_201
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
milestone_29_status: shipped
milestone_30_status: active
milestone_30_increment_0_status: shipped
milestone_30_increment_1_status: shipped
milestone_30_increment_2_status: pending
next_session: SESSION_202
next_milestone: 30
next_milestone_name: "Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern)"
next_increment: 2
next_increment_name: "M30.2 — Frontend + Playwright (dialog consolidation, row Edit + Delete buttons, delete confirmation, D8 acceptance block)"
---

# Next session — SESSION_202 · Milestone 30 · Increment 2 (M30.2 — frontend + Playwright)

> **M30.1 shipped at SESSION_201.** Backend substrate landed:
> new `admin/accounting/journal-entry-templates/<int:pk>/`
> detail endpoint (PATCH + DELETE), `update_journal_entry
> _template` + `delete_journal_entry_template` service verbs,
> `include_inactive: bool = False` kwarg on
> `get_journal_entry_template` for API symmetry. Backend
> baseline **4,871 → 4,904** (+33 M30.1 tests). Audit **156 →
> 157 endpoints, 122 covered (unchanged), 34 → 35 backend-
> only, 315 → 317 service verbs**. Zero migration (soft-delete
> reuses M28.1 `is_active`). DoD exception path invoked as
> **fifth precedent** (M26 + M27.1 + M28.1 + M29.1 + M30.1).
>
> **Zero-drift permission-class streak advanced 29 → 30** (new
> endpoint reuses `_M131_PERMS` verbatim; no new class).
> Planning-time as-recommended streak unchanged at 9.
> Substrate-compound-value continuation projected 3 → 4 at
> M30.2 close (template CRUD closure).
>
> **SESSION_202 opens M30.2 — frontend + Playwright.**
> Component rename via `git mv` + import sweep (same commit):
> `NewJournalEntryTemplateDialog.tsx` →
> `JournalEntryTemplateDialog.tsx`. Additive optional props
> (`mode` / `initialTemplate` / `onEdited` / controlled-open
> `open` + `onOpenChange`) applied to the renamed component.
> Row-level Edit + Delete buttons attached to the templates
> section of `AccountingJournalEntriesPage`. Inline delete
> confirmation with mandated "Deactivate" copy. API wrappers
> `updateJournalEntryTemplate` +
> `deleteJournalEntryTemplate`. ~18 vitests. **One new
> Playwright `test.describe("edit-delete", ...)` block**
> extending `accounting_je_template.spec.ts` — journey count
> **20 → 21**. **DoD satisfied directly** via D8 block. Two-
> source agreement gate at close.
>
> **Coordinated push at M30 close.** M30.0 + M30.1 + M30.2
> commits (plus hash-backfill follow-ups per convention) all
> push together at M30.2 close, awaiting explicit user
> confirmation.

## First thing SESSION_202 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main`
  by 2 commits (SESSION_200 handoff commit `1956ed7` +
  SESSION_201 M30.1 commit). `origin/main` at `43b715b`
  (SESSION_200 §0.a push).
- `git log --oneline -10` — top three should be
  (a) SESSION_201 M30.1 commit, (b) `1956ed7` SESSION_200
  handoff, (c) `43b715b` §0.a amendment.
- `python3 manage.py test dealer_ai` → **4,904 pass, 1
  skipped, 0 fail** (M30.1 baseline).
- `cd frontend && npm test` → **282 pass** across 36 files
  (unchanged from M29.2 — no frontend changes at M30.1).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected" (M30.2 is frontend + Playwright
  only — zero backend changes expected).
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactively reset
  acceptance DB per SESSION_200 §0.a durable lesson (v) —
  local Playwright re-runs corrupt shared-DB state across
  sessions; fresh state is cheaper than diagnosing flakes.
- Audit artifact should read **157 / 122 / 35 / 317**
  (M30.1 baseline).

### 2. Implement per §5.b D2 + D4 + D7 (frontend)

Follow the load-bearing decisions in
`docs/roadmap/MILESTONE_30_PLANNING.md` §5.b.

**D2 — Dialog consolidation** (additive-mode pattern per
M29.2 durable lesson (t)):

- **Rename in the same commit as import sweep** (per
  `DOC_GOVERNANCE.md` §5):
  ```
  git mv \
    frontend/src/components/accounting/NewJournalEntryTemplateDialog.tsx \
    frontend/src/components/accounting/JournalEntryTemplateDialog.tsx
  git mv \
    frontend/src/components/accounting/NewJournalEntryTemplateDialog.test.tsx \
    frontend/src/components/accounting/JournalEntryTemplateDialog.test.tsx
  ```
- Update the component name inside the file:
  `NewJournalEntryTemplateDialog` → `JournalEntryTemplateDialog`
  (both the exported component and the `Props` interface).
- **Sweep every import** — before commit, run
  `git grep NewJournalEntryTemplateDialog frontend/ acceptance/`
  and ensure the result is empty. Current known callers:
  - `frontend/src/pages/AccountingJournalEntriesPage.tsx`
    (imports the component + renders it in the templates
    section header).
  - `frontend/src/components/accounting/
    NewJournalEntryTemplateDialog.test.tsx` (self-import,
    handled by the file rename).
- **Add additive props** with safe defaults:
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
    /** Controlled-open pair. When both supplied, baked-in
     *  trigger is NOT rendered — parent controls open. When
     *  absent (M29.2 default), baked-in "+ New template"
     *  button renders. */
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
  }
  ```
- **Edit-mode population** — `useEffect([open,
  initialTemplate, mode])`: when `mode === "edit"` and
  `open` transitions true (or `initialTemplate` changes),
  populate `name` / `description` / `lines` from
  `initialTemplate` via a helper `templateToDraftLines
  (initialTemplate)`. Reuses the existing reset() function
  on close (M29.2 durable lesson (u) — reset every
  state).
- **Edit-mode submit** — `handleSubmit` branches on `mode`:
  `create` → `createJournalEntryTemplate(payload)` +
  `onCreated`; `edit` → `updateJournalEntryTemplate(pk,
  payload)` + `onEdited`.
- **Dialog title** — "New recurring template" (create) vs
  "Edit template" (edit). Submit-button label — "Save
  template" (create) vs "Save changes" (edit).
- **Test-ids** — `tmpl-create-trigger` + `tmpl-create-
  submit` preserved (unchanged); add `tmpl-edit-trigger-
  <pk>` + `tmpl-edit-submit` for edit mode; add
  `tmpl-dialog-title` on the DialogTitle element (used by
  vitests to assert mode).
- **Regression guard** — the 17 existing create-mode
  vitests in the renamed test file must continue to pass
  unchanged (safe-default path).

**D3 — Delete confirmation UI** (see §5.b D3 in planning
memo):

- Add row-level `Delete` button (variant outline, TrashIcon)
  with `data-testid="tmpl-delete-trigger-<pk>"`.
- Add row-level `Edit` button (variant outline, PencilIcon)
  with `data-testid="tmpl-edit-trigger-<pk>"` alongside the
  existing Instantiate button.
- Add inline delete confirmation — shadcn `AlertDialog` (or
  `Dialog` + overlay if AlertDialog is not yet imported).
  Mandated copy (D3 explicit design constraint):
  - Title: `Deactivate template?`
  - Body: `Are you sure you want to deactivate "<name>"?
    Historical journal entries created from this template
    are not affected — they remain unchanged in the Journal
    Entries list and in trial balance reports. You can
    restore this template later. (Restore UX ships in a
    future milestone.)`
  - Footer: `[Cancel] [Deactivate]` (destructive variant
    on Deactivate).
- On confirm: call
  `deleteJournalEntryTemplate(pk)`; bump
  `templatesReloadTick` on success; treat 404 as success
  (race-safe); optionally show a success badge for ~3s.

**D4 — Edit UI wiring** on
`AccountingJournalEntriesPage.tsx`:

```ts
const [editingTemplate, setEditingTemplate] =
  useState<JournalEntryTemplate | null>(null);
const editDialogOpen = editingTemplate !== null;

function handleEditClick(template) { setEditingTemplate(template); }
function handleEditDialogOpenChange(open) {
  if (!open) setEditingTemplate(null);
}
function handleEdited(template) {
  setLastEditedTemplate(template);
  setEditingTemplate(null);
  setTemplatesReloadTick((tick) => tick + 1);
}

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

The standalone create-mode `<JournalEntryTemplateDialog />`
at the templates section header continues to render as
today (baked-in trigger).

**API wrappers** in
`frontend/src/lib/accountingApi.ts`:

- `updateJournalEntryTemplate(pk, payload)` — PATCH the
  detail endpoint; return the projected updated template
  or throw on error. Payload shape identical to
  `CreateJournalEntryTemplatePayload`.
- `deleteJournalEntryTemplate(pk)` — DELETE the detail
  endpoint; return `void` on 204; return `void` on 404
  (race-safe — the template is gone either way).

**D7 — Frontend test surface additions** (~18 vitests):

- **Renamed file** — 17 existing create-mode tests pass
  unchanged.
- **Extensions in the renamed file** (~8 tests): edit-mode
  populates from initialTemplate; edit-mode submit calls
  updateJournalEntryTemplate; edit-mode success fires
  onEdited; edit-mode dialog title reads "Edit template";
  edit-mode submit label reads "Save changes"; controlled-
  open state respected; reset on close; inline error
  surfaces on edit failure.
- **`AccountingJournalEntriesPage.test.tsx`** extension
  (~5 tests): template row renders Edit + Delete buttons;
  Edit click opens dialog in edit mode with initial values;
  Delete click opens confirmation dialog with mandated
  copy; Delete confirm calls deleteJournalEntryTemplate +
  refetches; Delete 404 treated as success.
- **`accountingApi.templates.test.ts`** extension (~4 tests):
  updateJournalEntryTemplate wraps PATCH correctly;
  updateJournalEntryTemplate returns projection;
  deleteJournalEntryTemplate wraps DELETE correctly;
  deleteJournalEntryTemplate treats 404 as success.

### 3. Implement per §5.b D8 (Playwright)

**Extend** `acceptance/journeys/office/accounting_je
_template.spec.ts` with **one new `test.describe("edit-
delete", ...)` block** containing a single end-to-end
journey:

1. **Create a fresh template** ("M30 edit fixture", 2 lines,
   fixed $100/$100). Assert 201 + template appears in list.
2. **Instantiate the template into a JournalEntry** and post
   it — establishes a historical JE. Assert JE appears in
   list.
3. **Edit the template** — click row's Edit button; assert
   `tmpl-dialog-title` reads "Edit template" and form pre-
   populated; change name to "M30 edit fixture (renamed)";
   change amounts to $150/$150; click Save changes; assert
   dialog closes + list refreshes + new name visible.
4. **Verify historical JE unchanged** — assert JE from step
   2 still shows $100/$100 with original description.
   **Load-bearing assertion** for §4.7 criterion (b) —
   historical JEs are immune to template mutations.
5. **Delete the template** — click row's Delete button;
   assert confirmation dialog opens with "Deactivate
   template?" title + "historical entries not affected"
   body; click Deactivate; assert confirmation closes +
   template disappears from list.
6. **Verify template gone from operator list** — refresh
   page; assert template does not re-appear.
7. **Verify historical JE still visible after delete** —
   assert JE from step 2 still renders correctly.

**Journey count:** 20 → 21.

### 4. Two-source agreement gate at close

- `python3 manage.py test dealer_ai` → **4,904 pass, 1
  skip** (unchanged — no backend changes at M30.2).
- `cd frontend && npm test` → **282 → ~300 pass** (+~18
  M30.2 vitests). All 36 → 37 test files (renamed dialog
  test file + 3 extended files).
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `python3 -m dealer_ai.scripts.audit_operational_surface`
  — expected re-classification of the M30.1 detail endpoint
  row at index 151 from `defer-candidate-O2` to `covered`
  when the frontend wrappers are detected. Coverage summary
  should read **157 / 123 covered / 34 backend-only / 317
  service verbs**.
- Playwright acceptance suite locally on fresh DB — expect
  **all journeys green** (26 → 27 tests with the new D8
  block, or however Playwright counts the new describe
  block as tests).
- Frontend routes: 20 (unchanged — no new route added).
- Grep sweep: `git grep NewJournalEntryTemplateDialog
  frontend/ acceptance/` should return empty (rename +
  import sweep complete). Also grep
  `getByLabel\("Line \d+ (debit|credit)"\)` — should still
  return the pre-existing correct-by-context sites only.
  M30.2 does not change the amount-cell shape.

### 5. DoD compliance check

M30.2 §3 in the handoff must name the D8 acceptance journey
extension: single new `test.describe("edit-delete", ...)`
block in `accounting_je_template.spec.ts`, journey count
20 → 21. **DoD satisfied directly** — no exception path at
M30.2.

### 6. Ship the M30.2 handoff + coordinated M30 close push

- `docs/handoffs/SESSION_202_m30_inc2_frontend.md`.
- Flip milestone_30_status: shipped, milestone_30_increment
  _2_status: shipped in `00-START-NEXT-SESSION.md`
  frontmatter.
- Overwrite `00-START-NEXT-SESSION.md` for SESSION_203
  M31.0 planning.
- Update `MILESTONE_30_PLANNING.md` status: shipped.
- Author `docs/roadmap/MILESTONE_30_RETROSPECTIVE.md` with
  §1–§9 following the M29 retrospective shape (planned
  scope, what actually shipped, deviations, deferrals,
  durable lessons — especially whether additive-prop lesson
  (t) survives the M30.2 re-application, streak accounting,
  baselines, corrections, evidence-based candidates for
  M31).
- Update `docs/CAPABILITY_MATRIX.md` §7ε with M30 shipped
  surface.
- Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — mark
  M30 shipped.
- **Coordinated M30 close push** — await explicit user
  confirmation. Expected M30 commits at push: **7** — one
  for §0.a amendment (already pushed as `43b715b` at
  SESSION_200), SESSION_200 handoff (`1956ed7` local),
  SESSION_201 M30.1 commit + hash backfill, SESSION_202
  M30.2 commit + hash backfill, plus the M30 close-out
  documentation commit. Actual count may vary by 1–2
  depending on how the rename commit + implementation
  commits get grouped.

## Non-goals for SESSION_202

- ❌ Do NOT ship any backend code — M30.1 shipped the
  backend substrate; M30.2 is frontend + Playwright only.
- ❌ Do NOT modify backend endpoints, service verbs,
  serializers, or models — the M30.1 surface is locked at
  the M30.2 close of the milestone.
- ❌ Do NOT skip the rename import sweep — `git grep
  NewJournalEntryTemplateDialog` must be empty before
  commit; TypeScript will catch missed imports at
  `tsc --noEmit` regardless, but the grep guards against
  string-based references in comments / test-ids that
  drift.
- ❌ Do NOT expose Restore UI at M30.2 (deferred; requires
  `?include_inactive=true` endpoint exposure which is M28
  §3 deferral).
- ❌ Do NOT expose hard-delete UI (M30 §3 deferral).
- ❌ Do NOT add optimistic-concurrency ETags on edit (M30
  §3 deferral — single-operator MVP).
- ❌ Do NOT push under exception — M30 coordinated-push
  cadence applies. Push at M30.2 close awaits explicit user
  confirmation.
- ❌ Do NOT change the amount-cell UI shape on
  `NewJournalEntryDialog` — SESSION_200 §0.a durable
  lesson (v) applies: any semantic-shape change on an
  established UI element requires a full acceptance-suite
  selector sweep. M30.2 preserves M29.2's chip/input
  behavior verbatim.

## Baseline expected at close

- Backend: **4,904 pass** (unchanged from M30.1).
- Frontend Vitest: **282 → ~300 pass** (+~18 M30.2 vitests);
  36 → 37 test files (renamed dialog test file counts as
  the same file post-rename; extensions add tests to
  existing files).
- Acceptance: **20 → 21 journeys** (+1 D8 edit-delete
  block).
- Audit coverage: **122 → 123 covered** (+1 — M30.1 detail
  endpoint re-classified from backend-only to covered);
  backend-only 35 → 34 (-1).
- DRF admin surface: 117 (unchanged).
- Frontend operator routes: 20 (unchanged — no new route).
- Permission classes: 7 actual (unchanged).
- Migrations: `0001`–`0050` (unchanged).
- Component rename applied: `NewJournalEntryTemplateDialog`
  → `JournalEntryTemplateDialog` (+ sibling test file).
- New frontend files: none (rename preserves file count).
- New backend files: none (M30.1 shipped the backend).

## NEXT TASK

Start SESSION_202 with (a) starting-state verification
(including acceptance DB reset); (b) component rename via
`git mv` + import sweep + component-name update in the
same commit; (c) additive props on the renamed component
per D2/D4; (d) row-level Edit + Delete buttons on
`AccountingJournalEntriesPage` per D3; (e) inline delete
confirmation with mandated copy per D3; (f) API wrappers
per D7; (g) vitests per D7 (~18 tests); (h) new D8
Playwright `test.describe("edit-delete", ...)` block; (i)
two-source agreement gate at close (audit re-classifies
M30.1 endpoint to `covered`); (j) DoD satisfied directly
via D8 (no exception path); (k) ship M30.2 handoff +
retrospective + capability matrix update + roadmap flip;
(l) **coordinated M30 close push awaiting explicit user
confirmation**.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M30.0 + M30.1 shipped; M30.2 pending at SESSION_202
   open; M30 shipped after M30.2 close)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_30_PLANNING.md`
   (M30 governing contract + §0.a M29 CI regression
   correction record + all §5 locks + two architectural
   verifications at §4.6 and §4.7)
6. `docs/roadmap/MILESTONE_29_RETROSPECTIVE.md`
   §5 (durable lessons — (t) additive-prop pattern that
   M30.2 re-applies; (u) reset every override / annotation
   state; (v) sweep the full acceptance suite on UI shape
   change — all three actively load-bearing on M30.2) +
   §8 (corrections)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (M30.1 baseline — 157 endpoints / **122 covered** / 35
   backend-only / 317 service verbs; M30.2 projected 157
   / 123 covered / 34 backend-only / 317 service verbs)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α (M26) +
   §7β (M27) + §7γ (M28) + §7δ (M29 shipped surface) —
   M30 shipped surface lands at §7ε after M30.2 close
9. `docs/handoffs/SESSION_201_m30_inc1_backend.md`
   (M30.1 shipped — backend substrate)
10. `docs/handoffs/SESSION_200_m30_inc0_planning.md`
    (M30.0 shipped + §0.a M29 CI regression correction)
11. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — informs the M30.2 D2 additive-mode
    choice by capping duplication at short, stable,
    domain-local logic; the 200+ lines of shared dialog
    machinery in the template dialog exceed that threshold)
12. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified at M30.0 §4.2)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_201 — M30 · Increment 1 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,904 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 282 pass** across
  36 test files (unchanged — no frontend changes at M30.1).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **20 journeys** total.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run
  (30926157616 on `43b715b`) **26 passed / 0 failed /
  2m43s** (M29 CI green post-§0.a).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → M29, plus **M30.0 + M30.1
  shipped** at SESSION_200 + SESSION_201. M30.2 pending
  SESSION_202; M30 close awaits M30.2.
- **DRF admin surface:** **117** endpoints (M28.1 116 → +1
  at M30.1). M30.2 does not add endpoints.
- **Frontend operator routes:** 20 (unchanged; M30.2
  attaches Edit + Delete buttons to existing rows on the JE
  list page, no new route).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** M30.1 added `update_journal_entry
  _template` + `delete_journal_entry_template` verbs +
  `include_inactive` kwarg on `get_journal_entry_template`.
  M30.2 adds no service verbs.
- **Frontend surfaces:** M30.2 will rename
  `NewJournalEntryTemplateDialog.tsx` →
  `JournalEntryTemplateDialog.tsx`; add additive `mode` /
  `initialTemplate` / `onEdited` / `open` / `onOpenChange`
  props; attach Edit + Delete row buttons to the templates
  section; add inline delete confirmation dialog.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty consecutive milestones** (M10 → M30.1). M30.1
  reused `_M131_PERMS` on the new detail endpoint verbatim.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 30 · Increment 1 status:** SHIPPED
  (SESSION_201 close-out landed the backend substrate:
  detail endpoint + two service verbs + `include_inactive`
  kwarg + ~33 backend tests; audit artifact regenerated
  to 157 / 122 / 35 / 317).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **122 / 157** (M29.2 122 / 156 → M30.1 122 / 157 with
  new endpoint auto-classified backend-only until M30.2
  attaches wrappers).
- **§0.a M30.0 amendment status:** SHIPPED at `43b715b`
  (pushed to origin/main SESSION_200 under push-cadence
  exception). Second CI run confirmed green.
- **Planning-time streak: 9** (at M30.0 close; M30.1 pure
  implementation; unchanged at M30.1 close).
- **DoD amendment (M21.0 §5.f Option B):** M26 first
  invocation; M27.1 second; M28.1 third; M29.1 fourth;
  **M30.1 fifth invocation** (backend-only PATCH + DELETE
  substrate with no operator-facing behavior change).
  Pattern well-established.
- **M30.1 audit coverage at close:** 157 endpoints, **122
  covered / 35 backend-only** (delta +1 endpoint, +1
  backend-only from M29.2 close; +2 service verbs).
- **Durable lessons carried into M30+:** all (a)–(v) from
  the SESSION_200 close-state list continue to apply.
  M30.1 did not surface any new durable lesson (pure
  implementation of an M30.0-locked plan). M30.2's D2
  rename + additive-mode work will be the first re-
  application of lesson (t) — success there elevates the
  lesson from "surfaced" to "load-bearing across two
  milestones."
