---
title: "SESSION_208 handoff — Milestone 32 · Increment 2 (M32.2 — sales-manager UI + sales-side Playwright)"
status: active
type: handoff
date: 2026-08-04
session: 208
milestone: 32
milestone_status: active
milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
increment: 2
increment_status: shipped
commit: null
commit_notes: "M32.2 sales-manager UI + sales-side Playwright — local commit expected at close per M28.2 / M29.2 / M30.2 / M31.2 cadence; hash backfill via a subsequent commit; NOT pushed. Coordinated push at M32 close after explicit user confirmation."
---

# SESSION_208 — Milestone 32 · Increment 2 (M32.2 — sales-manager UI + sales-side Playwright)

## What shipped

SESSION_208 opened per the M32.1 close-out priorities in
`00-START-NEXT-SESSION.md`. Six deliverables landed:

1. **`salesApi.ts` extended** with 5 new wrappers for the M11.3 +
   M32.1 backend verbs: `listDealWriteups`, `getDealWriteup`,
   `createDealWriteup`, `approveDealWriteup`, `handOffDealWriteup`
   + typed projection interfaces + `derivedWriteupState` helper.
   Module docstring updated; **all "UI deferred" language
   removed** per §5.h non-goal.
2. **`main.tsx` comment updated** — the M11.6 route header
   comment now references the M32.2 shipping of the DealWriteup
   UI instead of the outdated "deferred" wording.
3. **Three new co-located components** in
   `frontend/src/components/sales/`:
   - `DealWriteupForm.tsx` — four-square form with vehicle
     picker (reuses `listAdminVehicles` per D4-revised²).
   - `WriteupConfirmDialogs.tsx` — `WriteupApproveConfirmDialog`
     (D5-revised copy) + `WriteupHandoffConfirmDialog` (D6
     irreversibility copy). Kept together per M28.0
     duplicate-small-stable-logic lesson (shared shell, distinct
     copy + action semantics).
   - `LeadWriteupsPanel.tsx` — per-lead writeup list with
     three-signal state a11y (Badge + row aria-label + double-
     marker testids per D7); inline Approve on Pending, inline
     Send-to-F&I on Approved; Handed-off rows are read-only
     history; "+ New writeup" CTA opens the inline form.
4. **`LeadDetailModal.tsx` wired** to render the new
   `<LeadWriteupsPanel>` in the left column, between the
   Schedule test drive collapsible and the AI conversation
   summary section. Manager-only by transitivity of the modal
   itself per D4-revised².
5. **35 new Vitest tests** across 4 files
   (`salesApi.dealWriteups.test.ts` — 12; `DealWriteupForm.test.tsx`
   — 6; `WriteupConfirmDialogs.test.tsx` — 6;
   `LeadWriteupsPanel.test.tsx` — 11) covering API wrapper URL
   shapes, envelope unwrapping, filter param serialization,
   form validation/submit paths, error surfaces, confirmation
   copy verbatim (D5 no false re-approval; D6 irreversibility),
   three-signal state a11y, row-action visibility per state,
   and inline form show/hide.
6. **New Playwright describe block
   `sales-manager-writeup-handoff`** at
   `acceptance/journeys/sales_manager/sales_to_fandi_handoff.spec.ts`
   proving the full sales-side workflow end-to-end: walk-in
   intake → Writeups panel open → four-square form → Pending
   badge → Approve confirmation with D5 copy verbatim → Approved
   badge → Send-to-F&I confirmation with D6 irreversibility
   copy verbatim → Handed off badge → technical business-outcome
   assertion via `/admin/deal-writeups/<pk>/` confirming all
   three state timestamps populated (**§0.a M32.2 amendment**
   from the M32.0 memo's F&I-gated CA list assertion — that
   endpoint 403s for sales_manager; the writeup-detail
   assertion transitively proves the M11.3 hand-off atomic block
   ran to completion including CA creation per M32.1 pairing
   tests).

**DoD satisfied directly** — no exception path. Sales-manager UI
ships operator surface; new Playwright describe block asserts the
full sales-side workflow.

**Session artifacts:**

- **Starting-state verification (§1):** git clean; `HEAD` ahead of
  `origin/main` by 4 (SESSION_206 planning + hash-backfill;
  SESSION_207 substrate + hash-backfill); Django `check` clean;
  `makemigrations --check` clean; frontend + acceptance
  `tsc --noEmit` clean; backend suite **4,995 pass, 1 skipped,
  0 fail** (173.8s); frontend Vitest **319 pass** (36 files,
  6.30s); redis PONG; acceptance DB proactively reset per
  SESSION_200 §0.a durable lesson (v).
- **Confirmed working from M32.0 planning memo (§2):** read §5.b
  D4-revised² + D5 + D6 + D7 + §5.e M32.2 before touching frontend
  code. One §0.a amendment surfaced at implementation time (see §7).
- **M32.2 sales-manager UI shipped (§3):** 3 co-located components
  + LeadDetailModal wiring + 5 salesApi wrappers + docstring
  update + main.tsx comment fix.
- **35 new Vitest tests added and green.**
- **New Playwright spec added and green** — sales-side journey
  covers create → Pending → Approve → Approved → Send-to-F&I →
  Handed off with D5 + D6 copy verbatim assertions; technical
  assertion via writeup detail endpoint (sales-role-accessible).
- **Full acceptance suite green** — 29 tests passed / 30.5s (was
  28 at M31.2 close; +1 for M32.2 new spec).
- **Regression check:** full backend suite still 4,995 pass; full
  frontend Vitest 319 → 354 pass (+35 M32.2 tests across 4 new
  test files); acceptance 22 → 23 journeys (spec files).
- **Close baselines (§4) all match projections:** frontend 353
  projected → **354 actual** (+1 for the extra §5.h "UI deferred"
  removal-verification test); acceptance 23 journeys; `git grep
  "UI deferred" frontend/` returns only the test file itself
  (asserting the removal — not a false positive); audit
  regenerated as **161 / 128 / 33 / 321** (matches M32.0 §5.e
  M32.2 projection: 124 → 128 covered = +4 for writeup create +
  approve + hand-off + list; 37 → 33 backend-only = -4).
- **§5.h non-goals respected:** no F&I UI or persona work; no
  M32.1 backend code touched; no M11.3 shipped endpoint
  functions or URLs modified; no historical migrations touched;
  no advisor-visible Writeups tab surface (transitively manager-
  only per D4-revised²); re-approval not advertised as an
  operator workflow.

## 1. Verification results at open

- **git status:** clean; `HEAD` ahead of `origin/main` by 4
  commits.
- **git log --oneline -6:** M32.1 hash-backfill `6f2b64d`; M32.1
  substrate `16c54e9`; M32.0 hash-backfill `4e2afc9`; M32.0
  planning `c3d46fd`; M31.2 hash-backfill `08fef5f`; M31 shipped
  `4b5f5b9`.
- **Backend suite:** 4,995 pass, 1 skipped, 0 fail (173.8s).
- **Frontend Vitest:** 319 pass across 36 files (6.30s).
- **Django `check`:** clean.
- **`makemigrations --check --dry-run`:** "No changes detected."
- **Frontend + acceptance `tsc --noEmit`:** clean.
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed.

## 2. §5.h non-goals respected

- ❌ **No F&I UI or `f_and_i_manager` persona work** — M32.3
  scope.
- ❌ **No M32.1 backend code modified.**
- ❌ **No M11.3 shipped endpoint functions or URLs modified.**
- ❌ **No historical migrations touched.**
- ❌ **No advisor Writeups tab UI shipped** — the modal is
  sales-role-gated at the backend (`admin_lead_detail`), so
  advisors receive 403 and cannot open the modal at all. No
  separate visible-but-disabled treatment is possible or
  required per D4-revised².
- ❌ **Re-approval not advertised** — Approved rows hide the
  Approve button per state-machine display. Re-approval remains
  a backend M11.3 contract but is not exposed in the M32 UI per
  D5-revised.

## 3. DoD satisfied directly

Per M21.0 §5.f Option B (M26 lineage): every customer-facing
milestone must add or update at least one Playwright operational
journey, or explicitly document why no journey change is
required.

**M32.2 satisfies DoD directly** via the new
`sales-manager-writeup-handoff` describe block at
`acceptance/journeys/sales_manager/sales_to_fandi_handoff.spec.ts`.

The journey proves the full sales-side workflow through the real
UI: walk-in intake → Writeups panel → four-square form → Pending
badge → Approve (D5 copy verbatim) → Approved badge → Send-to-F&I
(D6 irreversibility copy verbatim) → Handed off badge, with a
technical business-outcome assertion via the sales-role-accessible
`/admin/deal-writeups/<pk>/` endpoint confirming all three state
timestamps populated.

No exception path invoked. Full acceptance suite green: 29 tests
passed / 30.5s (M31.2 close was 28; +1 for M32.2 sales journey).

## 4. Baselines at close

- Backend suite: **4,995 pass** (unchanged — no backend changes
  in M32.2).
- Frontend Vitest: **319 → 354 pass** (+35 M32.2 tests across 4
  new test files: `salesApi.dealWriteups.test.ts` 12;
  `DealWriteupForm.test.tsx` 6; `WriteupConfirmDialogs.test.tsx`
  6; `LeadWriteupsPanel.test.tsx` 11).
- Frontend test files: 36 → 40 (+4).
- Acceptance journeys (spec files): 22 → **23** (+1
  `sales_to_fandi_handoff.spec.ts`).
- Acceptance suite runs: 28 → **29 tests passed** / 30.5s.
- Django `check`: clean.
- `makemigrations --check --dry-run`: "No changes detected."
- Frontend `tsc --noEmit`: clean.
- Acceptance `tsc --noEmit`: clean.
- `git grep "UI deferred" frontend/`: returns only
  `src/lib/salesApi.dealWriteups.test.ts` (the removal-verification
  test asserting the string does NOT appear in source — not a
  false positive).
- Audit artifact regenerated: **161 endpoints / 128 covered / 33
  backend-only / 321 service verbs**.
  - Endpoints unchanged from M32.1 (161).
  - Covered 124 → 128 (+4): audit #113–116 transition from
    backend-only to covered as the salesApi wrappers land
    (`createDealWriteup`, `approveDealWriteup`,
    `handOffDealWriteup`, `listDealWriteups`).
  - Backend-only 37 → 33 (-4): same four endpoints.
  - Detail endpoint #117 remains defer-candidate-O2
    (`getDealWriteup` is wrapper-only — not consumed by a UI
    component in M32.2; the Playwright journey uses it via
    `request.get` for the technical assertion but the audit
    only tracks in-component consumers).
  - Credit-app list #90 remains backend-only — M32.3 will add
    the `fetchCreditApplications` wrapper via the F&I intake
    page.
  - Service verbs unchanged from M32.1 (321).

## 5. Streaks at M32.2 close

- **Planning-time as-recommended streak:** unchanged at **11**
  (from M32.0 close). M32.2 is pure implementation per plan
  (with one §0.a amendment; see §7).
- **Zero-drift permission-class streak:** 34 → **35**
  consecutive (M10 → M32.2). M32.2 shipped no new backend
  endpoints; permission classes unchanged.
- **DoD exception path invocations:** 7 (unchanged from M32.1).
  M32.2 satisfies DoD directly.
- **Substrate-compound-value continuation:** 5 links unchanged.
- **First operator UI to reach the M11.3 DealWriteup surface**
  — 9 sessions after M11.3 shipped (SESSION_116). Closes the
  shipped-source deferral promise called out in M32.0 §5.a
  Evidence #1.
- **First customer-facing milestone since M11 to satisfy DoD
  directly at both increments of a three-increment shape** —
  M32.1 (backend substrate; DoD exception #7) → M32.2 (sales-
  manager UI; DoD satisfied directly) → M32.3 (F&I UI; DoD
  satisfied directly, pending).

## 6. What did NOT change

- ❌ **No F&I UI or `f_and_i_manager` persona work.**
- ❌ **No M32.1 backend code modified.**
- ❌ **No M11.3 shipped endpoint functions or URLs modified.**
  M32.2 consumes them via new frontend wrappers only.
- ❌ **No historical migrations touched.**
- ❌ **No new permission classes.**
- ❌ **No advisor Writeups tab UI.**
- ❌ **No re-approval operator surface.**

## 7. §0.a M32.2 amendment (implementation-time)

**Amendment 1 (SESSION_208, §5.e M32.2 Playwright plan):**
the M32.0 memo called for a technical business-outcome assertion
via `page.request.get('/admin/credit-applications/list/?intake=true')`
after hand-off. This endpoint is F&I-role-gated (D3 + D10);
the `sales_manager` persona used by the M32.2 journey receives
403. **Amendment:** use the sales-role-accessible
`/admin/deal-writeups/<pk>/` detail endpoint (added at M32.1
per D2) as the technical assertion. The detail endpoint reveals
all three state timestamps
(`sales_manager_approved_at`, `sales_manager_approved_by_user_id`,
`handed_off_to_fandi_at`); a populated `handed_off_to_fandi_at`
transitively proves the M11.3 `hand_off_to_fandi`
`@transaction.atomic` block ran to completion, which per M11.3
shipped contract + M32.1 D9-revised² FK-pairing tests guarantees
the paired CA exists with the deterministic backpointer.

F&I-side CA-list verification stays as M32.3 scope via the
`f_and_i_manager` persona spec (per D11).

**Amendment 2 (SESSION_208, §5.e M32.3 file structure implication):**
the M32.0 memo said the M32.3 fandi-intake-receipt journey
would "extend the existing spec". Playwright's project routing
in `playwright.config.ts` scopes each project by `testMatch`
regex against journey path, so a single spec file cannot span
two personas without introducing a new project entry.
**Amendment:** M32.3 will ship a separate spec at
`acceptance/journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`
under a new project entry that references the new
`AUTH_STORAGE.fAndIManager` storage state per D11. File-per-
persona strengthens the independence guarantee (per §5.c R11)
by construction — no shared state possible.

## 8. §7 shipped surface details

### Frontend (`frontend/src/lib/salesApi.ts`)

- Module docstring updated — M32.2 heading; removed "UI deferred"
  language per §5.h.
- New M11.3 + M32.1 wrappers with typed projections:
  - `DealWriteupState`, `DealWriteupProjection`,
    `CreateDealWriteupRequest`, `DealWriteupListFilters` types.
  - `derivedWriteupState(writeup)` — timestamp-derived state
    helper (mirrors backend `list_deal_writeups` derivation).
  - `listDealWriteups({leadId?, state?})` — GET
    `/admin/deal-writeups/list/`.
  - `getDealWriteup(pk)` — GET `/admin/deal-writeups/<pk>/`.
  - `createDealWriteup(payload)` — POST `/admin/deal-writeups/`.
  - `approveDealWriteup(pk)` — POST
    `/admin/deal-writeups/<pk>/approve/`.
  - `handOffDealWriteup(pk)` — POST
    `/admin/deal-writeups/<pk>/hand-off/`.

### Frontend (`frontend/src/main.tsx`)

- M11.6 route header comment updated to reference M32.2 UI ship
  instead of outdated "deferred" wording.

### Frontend components (`frontend/src/components/sales/`)

- **`DealWriteupForm.tsx`** — four-square form; vehicle picker
  with search + suggested + all-inventory zones (reuses
  `listAdminVehicles` per D4-revised²); decimal + integer
  coercion helpers; disabled submit without vehicle selected;
  error surfaces for 400 / 404 / 403 / generic; testids
  `deal-writeup-*` for Playwright.
- **`WriteupConfirmDialogs.tsx`** — two co-located dialogs:
  - `WriteupApproveConfirmDialog` — D5-revised copy verbatim
    (no false re-approval advertisement).
  - `WriteupHandoffConfirmDialog` — D6 irreversibility copy
    verbatim ("This cannot be undone" + duplicate-CA rationale).
  - Kept together per M28.0 duplicate-small-stable-logic lesson.
- **`LeadWriteupsPanel.tsx`** — per-lead collapsible with:
  - Three-signal state a11y per D7: `[Pending]` / `[Approved]`
    / `[Handed off]` Badge + row `aria-label` +
    `writeup-row-state-<state>-<pk>` double-marker testid.
  - Row-action visibility per state: Approve on Pending only;
    Send-to-F&I on Approved only; Handed-off rows are read-only
    history with attribution.
  - Inline "+ New writeup" CTA opens the `DealWriteupForm`
    inline within the panel.
  - Confirmation dialogs mount conditionally when triggered.

### Frontend wiring (`frontend/src/components/LeadDetailModal.tsx`)

- New import for `LeadWriteupsPanel`.
- `<LeadWriteupsPanel>` rendered in the left column between
  "Schedule test drive" collapsible and "AI conversation
  summary" section. Passes lead id + name + interested vehicles
  (mapped to picker's suggested zone).

### Vitest tests (4 new files, 35 tests)

- `frontend/src/lib/salesApi.dealWriteups.test.ts` (12 tests):
  wrapper URL shape + payload + envelope unwrapping + filter
  serialization + `derivedWriteupState` matrix (3 states) +
  §5.h "UI deferred" removal-verification test.
- `frontend/src/components/sales/DealWriteupForm.test.tsx`
  (6 tests): picker load + suggested zone; submit disabled
  without vehicle; POST payload with numeric coercion; 400 +
  404 error surfaces.
- `frontend/src/components/sales/WriteupConfirmDialogs.test.tsx`
  (6 tests): D5-revised approve copy verbatim (asserts
  removed re-approval language is absent); D5 submit path +
  cancel; D6 irreversibility copy verbatim; D6 submit path +
  cancel.
- `frontend/src/components/sales/LeadWriteupsPanel.test.tsx`
  (11 tests): collapsible lazy-load; empty/error states;
  three-signal a11y for pending/approved/handed_off; row-
  action visibility per state (Approve on pending only;
  Send-to-F&I on approved only; handed_off read-only); inline
  form show/hide.

### Playwright (`acceptance/journeys/sales_manager/sales_to_fandi_handoff.spec.ts`)

- New spec (1 test) under the existing `sales_manager` project.
- Uses existing `sales_manager` storageState (no new persona;
  M32.3 adds `f_and_i_manager`).
- Uses existing seeded fixture vehicle `#M25-TEST-DRIVE-01`.
- 8-step journey: walk-in intake → Writeups panel → four-
  square form + picker → Pending badge → Approve confirmation
  (D5 copy verbatim) → Approved badge → Send-to-F&I
  confirmation (D6 copy verbatim + customer name in body) →
  Handed off badge → technical assertion via
  `/admin/deal-writeups/<pk>/` (sales-role-accessible; per §7
  Amendment 1).

## 9. Push status

**No push at SESSION_208 close.** M32.2 is pure implementation
per the standard M28.2 / M29.2 / M30.2 / M31.2 cadence.
Coordinated M32 close push deferred to explicit user
confirmation after M32.3 close.

Local commits at SESSION_208 close:

- SESSION_208 M32.2 sales-manager UI + this handoff +
  `00-START-NEXT-SESSION.md` flip land in a single local-only
  commit per implementation-session cadence; hash backfill via
  a subsequent commit.

Expected M32 commit count at coordinated push: **6–8** (M32.0
planning + M32.0 hash-backfill + M32.1 backend + M32.1 hash-
backfill + M32.2 UI + M32.2 hash-backfill + M32.3 F&I UI +
close-out fold).

## 10. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_209 ·
Milestone 32 · Increment 3 (M32.3 — F&I intake UI + F&I-side
Playwright + new f_and_i_manager persona)**. First-thing
sequence per M28.2 / M29.2 / M30.2 / M31.2 pattern applied to a
three-increment milestone:

1. **Verify starting state** (git; backend 4,995 pass; frontend
   354 pass; acceptance 23 journeys / 29 tests; checks;
   migrations; tsc; redis; `db.acceptance.sqlite3` proactive
   reset).
2. **Confirm working from M32.0 planning memo** — read
   `docs/roadmap/MILESTONE_32_PLANNING.md` §5.b D3 + D8-revised
   + D11 + §5.e M32.3 before touching frontend code. **Consult
   §7 M32.2 amendments** in this handoff — Amendment 2 changes
   M32.3 to a separate spec file under a new
   `f_and_i_manager` project.
3. **Ship the new `f_and_i_manager` Playwright persona** per
   D11:
   - Add entry to `acceptance/support/auth/personas.ts`.
   - Add `AUTH_STORAGE.fAndIManager` +
     `authenticate as f_and_i_manager` setup task in
     `login.setup.ts`.
   - Add new project entry in `playwright.config.ts` matching
     `journeys/f_and_i_manager/.*\.spec\.ts`.
   - Add new idempotent seed command
     `seed_journey_fandi_intake_receipt` provisioning both the
     persona + the `Intake Iris` fixture (lead + vehicle +
     approved+handed-off writeup + paired CA via real
     `hand_off_to_fandi` code path).
   - Register the seed command in `SEED_COMMANDS`.
4. **Ship M32.3 F&I intake UI** per §5.e:
   - Frontend wrapper `fetchCreditApplications` in
     `fAndIApi.ts`.
   - New page `DealerFandIIncoming.tsx` at
     `/dealer-ai-f-and-i/incoming` per D8-revised (non-
     navigational rows; all triage info rendered inline).
   - Navigation link "Incoming" in F&I side nav.
   - ~20 Vitest tests.
5. **Playwright:** new spec
   `acceptance/journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`
   with `test.describe("fandi-intake-receipt", …)`. Uses new
   `f_and_i_manager` persona. Reads pre-seeded `Intake Iris`
   fixture deterministically by lead name / writeup pk. Fully
   independent of M32.2 fixture (distinct rows; no shared
   state; test order irrelevant).
6. **Verify M32.3 close baselines:** frontend 354 → ~374;
   acceptance 23 → 24 spec files / 29 → 30+ tests (also
   depends on persona setup addition to setup project);
   `tsc --noEmit` clean; audit 161 endpoints / 128 → ~129
   covered (CA list #90 becomes covered via M32.3 UI wrapper);
   33 → 32 backend-only.
7. **DoD satisfied directly** — no exception.
8. **Ship the M32.3 handoff at
   `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md`** + M32
   close-out fold per M31 precedent (`CAPABILITY_MATRIX.md`
   §7η; audit re-baseline; `IMPLEMENTATION_ROADMAP.md`
   milestone_32_status: shipped; retrospective at
   `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md`).
9. **Coordinated push after user confirmation** — expected 6–8
   commits per §9.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_32_PLANNING.md`** §5.b D3 +
   D8-revised + D11 + §5.e M32.3 (governing contract for
   M32.3)
6. `docs/handoffs/SESSION_206_m32_inc0_planning.md` (M32.0
   planning close-out)
7. `docs/handoffs/SESSION_207_m32_inc1_backend.md` (M32.1
   backend close-out)
8. **This handoff** (`SESSION_208_m32_inc2_sales_ui.md`) — §7
   amendments to M32.0 memo (file-per-persona; sales-role-
   accessible technical assertion)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-M32.2
   baseline — 161 / 128 / 33 / 321)
10. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3
11. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — exercised at M32.2 for
    `WriteupConfirmDialogs.tsx` co-location)
12. Memory record
    `feedback_playwright_as_operational_contract.md` (M32.2
    Playwright is the sales-side operational contract; M32.3
    ships F&I-side operational contract)

Narrative docs are claims. Rules + research + code + regenerated
artifact are facts.
