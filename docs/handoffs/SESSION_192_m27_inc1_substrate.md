---
title: "SESSION_192 handoff — Milestone 27 · Increment 1 (M27.1 — backend substrate + frontend wrapper)"
status: historical
type: handoff
date: 2026-08-03
session: 192
milestone: 27
milestone_status: active
milestone_name: "Journal-Entry Creation UI (via shared GLAccount substrate)"
increment: 1
increment_status: shipped
commit: f9256c2
---

# SESSION_192 — Milestone 27 · Increment 1 (M27.1 — backend substrate + frontend wrapper)

## What shipped

M27.1 ships the **shared GLAccount list substrate** — a
tenant-scoped `GET admin/accounting/gl-accounts/` endpoint +
`fetchGLAccounts` frontend wrapper. Zero UI change. Zero
consumer wiring. DoD exception path per M21.0 §5.f Option B
invoked (infrastructure-only increment; new endpoint's
operational journey coverage arrives at M27.2 via the JE-create
Playwright journey extension).

**gl-accounts is deliberately shared accounting infrastructure**
— not JE-specific. Immediate consumer is the M27.2 JE-create
dialog picker; future consumers include recurring journals,
adjustments, budget uploads, statement reconciliation, F&I
chargeback flows, and period-open workflows.

### Backend changes

- **`backend/dealer_ai/views_accounting.py`** — new
  `admin_gl_account_list` view (~48 LOC including docstring).
  DRF `@api_view(["GET"])`, `permission_classes(_M131_PERMS)`,
  tenant-scoped via `get_current_dealership(request)`. Returns
  the active CoA (`is_active=True`) sorted by `code` ASC.
  Response envelope follows the `cost_posting_failures`
  precedent verbatim:
  ```json
  {"gl_accounts": {"accounts": [{"id":..., "code":..., "name":..., "type":...}, ...]}}
  ```
- **`backend/dealer_ai/urls.py`** — one new route:
  ```python
  path("admin/accounting/gl-accounts/",
       views_accounting.admin_gl_account_list,
       name="admin-gl-account-list"),
  ```
- **`backend/dealer_ai/tests/test_m27_gl_account_list.py`** —
  NEW file, 8 test methods across 1 class
  (`GLAccountListEndpointTests`):
  1. Envelope shape (`{"gl_accounts": {"accounts": [...]}}`).
  2. Active CoA returned sorted by code ASC.
  3. Row projection carries exactly `{id, code, name, type}`.
  4. Zero-balance accounts included (contrast with TB).
  5. Soft-hidden (`is_active=False`) accounts excluded.
  6. Cross-tenant isolation (other dealership's accounts do
     not leak).
  7. Advisor role denied (403 — permission enforcement).
  8. Unauthenticated request rejected (401 or 403).

### Frontend changes

- **`frontend/src/lib/accountingApi.ts`** — added `GLAccount`
  interface, `GLAccountListResponse` internal interface, and
  `fetchGLAccounts(): Promise<GLAccount[]>` wrapper (~33 LOC
  with header comment). Reuses the existing `GLAccountType`
  alias (already exported from the M14 trial-balance types) —
  no duplicate declaration.
- **No frontend UI change at M27.1** per §5.b. No new
  components. No new pages. No new routes. No JSX modified.
- **No standalone vitest for the wrapper.** Follows the
  established `analyticsApi.test.ts` convention documented at
  the top of that file: "The API-client fetch wrappers are
  exercised end-to-end via the tab tests, not stub-tested
  here." The `fetchGLAccounts` wrapper is exercised at M27.2
  via the `GLAccountPicker` and `NewJournalEntryDialog`
  component tests.

### Documentation changes

- **`docs/CAPABILITY_MATRIX.md`** — added §7β "Journal-Entry
  Creation UI — via shared GLAccount substrate (Milestone 27,
  in progress)" block noting M27.0 planning shipped, M27.1
  substrate shipped, and M27.2 dialog pending. Records
  gl-accounts framing as shared accounting infrastructure,
  DoD exception path invocation for M27.1, and the durable
  planning lesson from M27.0 §7.
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`** —
  regenerated per §5.d. New row 149
  `admin/accounting/gl-accounts/` with view symbol
  `views_accounting.admin_gl_account_list`, URL name
  `admin-gl-account-list`, wrapper detected as
  `accountingApi.ts:343 fetchGLAccounts ⚠ wrapper-only`,
  disposition `defer-candidate-O2` (M27.1 predicted state —
  wrapper exists, no consumer component yet).

## §5.e verification — two-source agreement ✅

**Phase 1 (regenerated artifact):**

- Backend endpoints: **154 → 155** ✅
- Covered: **119 unchanged** ✅
- Backend-only: **35 → 36** ✅
- Service verbs: **312 unchanged** ✅
- New row 149 disposition: **`defer-candidate-O2`** ✅

**Phase 2 (direct repository inspection):**

- Endpoint file:line matches view symbol — `admin_gl_account_list`
  present in `views_accounting.py`, decorated correctly ✅
- Permissions match `_M131_PERMS` — decorator applied ✅
- HTTP method matches GET — `@api_view(["GET"])` ✅
- Wrapper `fetchGLAccounts` exists at `accountingApi.ts:343`
  with correct helper (`authGetJSON`) and correct path
  (`/admin/accounting/gl-accounts/`) ✅

Both sources agree. Baseline recorded in CAPABILITY_MATRIX §7β.

## Verification / baselines at close

- **Backend:** **4,805 → 4,813 pass, 1 skipped, 0 fail** (+8
  across `test_m27_gl_account_list.py`).
- **Frontend Vitest:** 226 pass across 32 files (unchanged
  — wrapper tested via M27.2 consumer per the
  `analyticsApi.test.ts` convention).
- **Acceptance:** 14 journeys unchanged. §5.g exception path
  invoked at M27.1 per M21.0 §5.f Option B (infrastructure-
  only increment).
- **Django check:** clean.
- **Migrations:** no changes detected (no model or migration
  changes at M27.1 — GLAccount already exists from M13.1).
- **Frontend `tsc --noEmit`:** clean.
- **Acceptance `tsc --noEmit`:** clean (not run in this
  session — untouched).
- **Redis:** PONG (verified at session start).
- **Audit artifact:** **155 total / 119 covered / 36
  backend-only / 312 service verbs**. New row 149
  `admin/accounting/gl-accounts/` disposition
  `defer-candidate-O2` with wrapper detected as
  `⚠ wrapper-only` — flips to `covered` at M27.2 when the
  dialog consumes the wrapper.

## What changed in the repo

- **Modified:** `backend/dealer_ai/views_accounting.py`
  (+57 LOC — new view + section comment).
- **Modified:** `backend/dealer_ai/urls.py` (+13 LOC — new
  route + section comment).
- **Modified:** `frontend/src/lib/accountingApi.ts` (+33 LOC
  — GLAccount type + wrapper + section comment).
- **Modified:** `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  (regenerated — new row 149 + coverage summary updates + a
  small counter shift; deterministic script output).
- **Modified:** `docs/CAPABILITY_MATRIX.md` (+~55 LOC — new
  §7β block).
- **Created:**
  `backend/dealer_ai/tests/test_m27_gl_account_list.py`
  (8 test methods).
- **Created:**
  `docs/handoffs/SESSION_192_m27_inc1_substrate.md` — this
  handoff.

## Deferrals / follow-on items

M27.2 (SESSION_193) delivers everything user-facing:

- "+ New journal entry" button on
  `AccountingJournalEntriesPage`.
- `NewJournalEntryDialog` modal component (description +
  `posted_at` defaulting to today + dynamic lines table +
  balance indicator + submit/cancel).
- `GLAccountPicker` component (searchable by both `code` AND
  `name`; client-side filter over the M27.1 CoA payload).
- `createJournalEntry` wrapper in `accountingApi.ts`.
- Component vitests for `GLAccountPicker`,
  `NewJournalEntryDialog`, extended
  `AccountingJournalEntriesPage.test.tsx`.
- Playwright journey extension (prefer extending
  `accounting_workflow.spec.ts`; add peer
  `accounting_je_create.spec.ts` only if the shape doesn't
  fit) with two test cases per §5.d — successful create AND
  cancel-without-persistence.
- CAPABILITY_MATRIX §7β update (M27.2 complete row).
- Retrospective + start-here overwrite + coordinated push at
  M27 close.

Deferred from M27 entirely (still valid for later re-entry):

- Standalone Chart of Accounts page / route / nav entry (per
  user substrate-attachment rule at M27.0).
- Trial Balance changes.
- JE edit / update endpoints.
- JE templates / recurring journals.
- `posted_by_user` override in the dialog.
- Advanced account-picker filtering.
- Server-side search / pagination on `gl-accounts`.
- `?include_inactive=true` query param on `gl-accounts`
  (add when a consumer needs inactive accounts).
- **O2 + O3 + H** (M26 deferrals) — remain M28+ candidates.
- All M25 §4 deferrals — remain valid for later re-entry.

## Non-goals achieved (SESSION_192)

- ❌ No frontend UI change (M27.1 is backend + wrapper only).
- ❌ No "+ New journal entry" button (M27.2).
- ❌ No `NewJournalEntryDialog` or `GLAccountPicker`
  component created (M27.2).
- ❌ No `createJournalEntry` wrapper added (M27.2).
- ❌ No Playwright journey added or extended (§5.g
  exception path invoked).
- ❌ No standalone Chart of Accounts page, route, or nav
  entry created (per user direction at M27.0 §7).
- ❌ No Trial Balance modifications (report page untouched).
- ❌ No modification to any existing accounting endpoint,
  serializer, service, page, or component beyond the M27.1
  additions.
- ❌ No hand-edit of `M21_OPERATIONAL_SURFACE_AUDIT.md`
  (regenerated only).
- ❌ No M27.1 baseline recorded without both §5.e sources
  agreeing (they did).
- ❌ No M26-deferred O2 / O3 / H investigation.
- ❌ No push (per §5.h — coordinated push at M27 close).

## Streak accounting at M27.1 close

- **Zero-drift permission-class streak:** 26 consecutive
  milestones entering M27. M27.1 reuses `_M131_PERMS`; zero
  new permission classes. Intended posture at M27 close
  (i.e., after M27.2 which will consume the create endpoint
  via the dialog): extend to **27 consecutive milestones
  (M10 → M27)**.
- **Planning-time as-recommended streak:** 6 at M27.0 close.
  M27.1 is a pure implementation increment executing the
  M27.0 locked plan exactly — no planning decisions made or
  refined in this session. Streak unchanged (6).

## Next session (SESSION_193 — M27.2 create dialog + Playwright)

Per `MILESTONE_27_PLANNING.md` §7 and the (to-be-overwritten
at M27.2 close) `00-START-NEXT-SESSION.md`:

1. Verify M27.1 close baseline holds (backend 4,813 pass,
   frontend 226 pass, acceptance 14 journeys clean-DB,
   audit 155 / 119 / 36 with row 149 `defer-candidate-O2`).
2. Add "+ New journal entry" button to
   `AccountingJournalEntriesPage` header.
3. Implement `NewJournalEntryDialog` component (description
   + `posted_at` defaulting to today + dynamic lines table +
   balance indicator + submit/cancel).
4. Implement `GLAccountPicker` component (shadcn `Command`
   combobox; client-side filter by code AND name; displays
   `"{code} — {name}"`).
5. Add `createJournalEntry` wrapper + payload types to
   `accountingApi.ts`.
6. Write component vitests
   (`GLAccountPicker.test.tsx`,
   `NewJournalEntryDialog.test.tsx`; extend
   `AccountingJournalEntriesPage.test.tsx`).
7. Run `npm test` — assert green (~226 → ~240).
8. Confirm seed
   `seed_journey_office_accounting_workflow` provides ≥2
   GLAccounts of appropriate types; augment if needed.
9. Extend `accounting_workflow.spec.ts` (preferred) or add
   peer `accounting_je_create.spec.ts` with two test cases
   per §5.d (successful create + cancel-without-persistence).
10. Run acceptance suite; assert both test cases green.
11. Run `python3 manage.py test dealer_ai` — assert baseline
    holds.
12. Regenerate audit; assert diff per §5.e M27.2 (row 140
    → `covered`; row 149 → `covered`; coverage 119 → 121 /
    155 total / 34 backend-only).
13. §5.e Phase 2 per-row verification for both flipped rows.
14. Update `docs/CAPABILITY_MATRIX.md` §7β (M27.2 complete
    row).
15. Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` M27
    entry.
16. Draft `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md`.
17. Overwrite `00-START-NEXT-SESSION.md` with SESSION_194
    priorities (M28 target selection).
18. Compose M27.2 handoff `docs/handoffs/SESSION_193_m27_
    close.md` (or split into M27.2 + M27.3 if §5.h
    evidence forces).
19. Coordinated push (all M27 commits + hash backfills) —
    per §5.h Option B evidence-sized fold.

## Anchors that win on conflict (M27.1 close)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_27_PLANNING.md` §5 (all locks)
4. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (current
   155 / 119 baseline; source of truth post-M27.1)
5. `backend/dealer_ai/views_accounting.py`
   (`admin_gl_account_list` view — the M27.1 shipped
   endpoint)
6. `frontend/src/lib/accountingApi.ts` (`fetchGLAccounts` +
   `GLAccount` type — the M27.1 shipped wrapper)
7. `backend/dealer_ai/tests/test_m27_gl_account_list.py`
   (M27.1 test contract)
8. `docs/CAPABILITY_MATRIX.md` §7β (M27 in-progress
   shipped surface)
9. Memory record
   `feedback_verify_fk_discoverability_before_lock.md`
10. `docs/handoffs/SESSION_191_m27_inc0_planning.md`
    (M27.0 close; records all §5 locks)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
