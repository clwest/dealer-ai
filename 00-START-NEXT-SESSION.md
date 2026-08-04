---
state: active
date: 2026-08-04
last_session_shipped: SESSION_207
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
milestone_30_status: shipped
milestone_31_status: shipped
milestone_32_status: active
next_session: SESSION_208
next_milestone: 32
next_milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
next_increment: 2
next_increment_name: "M32.2 — Sales-manager UI + sales-side Playwright"
---

# Next session — SESSION_208 · Milestone 32 · Increment 2 (M32.2 — sales-manager UI + sales-side Playwright)

> **M32.1 backend substrate shipped at SESSION_207.** Migration
> 0051 (nullable OneToOneField); 3 new service verbs
> (`list_deal_writeups`, `get_deal_writeup`,
> `list_credit_applications`); 3 new endpoints (writeup list,
> writeup detail, CA list — all on distinct `/list/` sibling
> URLs to preserve M10.1 + M11.3 shipped URL config); 1 new
> error class (`DealWriteupAlreadyLinkedError`); 4 docstring
> updates on shipped M11.3/M10.1 files; +62 tests including
> mandatory `test_writeup_cannot_link_to_multiple_credit_applications`
> exercising all three defense layers of the D9-revised²
> provenance-FK guard. **Baselines at M32.1 close:** backend
> 4,995 pass (+62); frontend 319 (unchanged); acceptance 22
> (unchanged); audit **161 / 124 / 37 / 321**. DoD exception
> path invocation #7. Zero-drift permission-class streak 33
> → 34.
>
> **SESSION_208 opens M32.2 sales-manager UI.** Writeups tab
> on `LeadDetailModal` (manager-only by transitivity per
> D4-revised²); inline four-square form; inline Approve +
> Send-to-F&I buttons with two confirmation dialogs
> (D5-revised state-machine-truthful approve copy; D6
> irreversibility hand-off copy); state visual signals per
> D7 (Badge + row aria-label + testids). Removal of
> `salesApi.ts:10-25` "UI deferred" comments. **New Playwright
> describe block `sales-manager-writeup-handoff`** — sales-side
> only in M32.2, uses existing `sales_manager` persona (no new
> persona in M32.2 — that lands at M32.3 per D11). Six-step
> journey proves create → Pending → Approve → Approved →
> Send-to-F&I → Handed off through the real UI, with inline
> technical assertion that the CA was created.
>
> **DoD satisfied directly** — no exception on customer-facing.

## First thing SESSION_208 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main` by
  4 commits (SESSION_206 planning + hash-backfill; SESSION_207
  substrate + hash-backfill).
- `git log --oneline -6` — top should be SESSION_207 M32.1
  hash-backfill; check for expected M32 commit sequence.
- `python3 manage.py test dealer_ai` → **4,995 pass, 1 skipped,
  0 fail**.
- `cd frontend && npm test` → **319 pass** across 36 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. Confirm working from M32.0 planning memo

Read `docs/roadmap/MILESTONE_32_PLANNING.md` §5.b D4-revised²
+ D5 + D6 + D7 + §5.e M32.2 before touching frontend code.
Reference `docs/handoffs/SESSION_207_m32_inc1_backend.md` §9
for M32.2 first-thing sequence.

Key pre-reads:

- **D4-revised²** — no visible-but-disabled tab for advisor
  viewers. Advisors cannot open `LeadDetailModal` at all
  (backend 403 on lead detail fetch). No advisor Writeups-
  specific UI ships.
- **D5** — approve copy is state-machine-truthful (no false
  re-approval advertisement). Approved rows hide the Approve
  button.
- **D6** — irreversibility copy verbatim per M32.0 §5.b D6.
- **D7** — three-signal a11y (Badge + row aria-label +
  double-marker testids).
- **M28.0 `feedback_duplicate_small_stable_logic.md`** — all
  new inline dialog components co-located inside
  `LeadDetailModal`, not extracted to a shared abstraction.

### 3. Ship M32.2 sales-manager UI

Per §5.e M32.2:

- **Frontend wrappers** (`salesApi.ts`): 5 new —
  `listDealWriteups`, `getDealWriteup`, `createDealWriteup`,
  `approveDealWriteup`, `handOffDealWriteup`. **Remove**
  `salesApi.ts:10-25` "UI deferred" comments.
- **`LeadDetailModal`**: new "Writeups" tab (manager-only by
  transitivity per D4-revised²).
- **New inline components** (co-located):
  - `DealWriteupForm` — four-square form with vehicle picker
    (reuses `listAdminVehicles` from `RecordTestDriveForm`).
  - `WriteupApproveConfirmDialog` — D5-revised copy.
  - `WriteupHandoffConfirmDialog` — D6 irreversibility copy.
- **State visual signals** per D7.
- **~34 Vitest tests** covering form validation, POST paths,
  list rendering by state, approve happy path + copy verbatim,
  hand-off happy path + irreversibility copy verbatim, state
  badge + testid assertions, non-manager modal 403 error
  branch, comment removal verification.

### 4. Playwright — new sales-side describe block

Per §5.e M32.2:

- **New spec** `acceptance/journeys/sales_to_fandi_handoff.spec.ts`
  with `test.describe("sales-manager-writeup-handoff", …)`.
- Uses existing `sales_manager` persona (existing storageState;
  no new persona in M32.2).
- **Six-step journey** proving create → Pending → Approve →
  Approved → Send-to-F&I → Handed off through the real UI.
- **Inline technical assertion** via
  `page.request.get('/admin/credit-applications/list/?intake=true')`
  after hand-off to prove the CA was created on the backend
  side (F&I UI ships in M32.3).
- Extend `seed_journey_sales_operational_entry` if needed for
  isolation (add a fresh lead/vehicle) — idempotent per M20
  lesson.
- Journey count 22 → **23**.

### 5. Verify M32.2 close baselines

- Backend suite: **4,995 pass** (unchanged — no backend changes
  in M32.2).
- Frontend Vitest: **319 → ~353 pass** (+~34).
- Acceptance: **22 → 23 journeys**; full-suite run green
  (fresh-DB reset first).
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `git grep "UI deferred" frontend/` → empty (removal
  verified).
- Audit: **161 / 124 → ~126 / 37 → 35 backend-only** (three
  writeup endpoints re-cover as UI wires them up; CA list
  remains backend-only until M32.3 F&I UI).

### 6. DoD satisfied directly

No exception. Sales-manager UI ships operator surface; new
`sales-manager-writeup-handoff` describe block satisfies DoD
directly. Documented in §3 of the M32.2 handoff.

### 7. Ship the M32.2 handoff

- `docs/handoffs/SESSION_208_m32_inc2_sales_ui.md`.
- Follow M31.2 handoff shape.
- **Do NOT push** — coordinated push at M32 close.

## Non-goals for SESSION_208

- ❌ Do NOT ship any F&I UI or `f_and_i_manager` persona work
  — M32.3 scope.
- ❌ Do NOT modify any M32.1 backend code (except if a
  regression surfaces as §0.a M32.2 amendment).
- ❌ Do NOT modify M11.3 shipped endpoint functions or URLs.
- ❌ Do NOT modify historical migrations.
- ❌ Do NOT ship advisor-visible Writeups tab surface (per
  D4-revised² non-goal — advisors cannot open the modal).
- ❌ Do NOT advertise re-approval as an operator workflow (per
  D5-revised — hide Approve button on non-`pending` rows).
- ❌ Do NOT push.

## Baseline expected at close

- Backend: 4,995 pass (unchanged).
- Frontend: 319 → ~353 pass.
- Acceptance: 22 → 23 journeys.
- Audit: 161 endpoints / 124 → ~126 covered / 37 → 35 backend-
  only (writeup endpoints re-cover via UI; CA list stays
  backend-only until M32.3).

## NEXT TASK

Start SESSION_208 with (a) starting-state verification;
(b) confirm working from M32.0 planning memo (D4-revised² + D5
+ D6 + D7 + §5.e M32.2); (c) ship M32.2 sales-manager UI —
`salesApi.ts` wrappers + `LeadDetailModal` Writeups tab +
inline `DealWriteupForm` + inline confirmation dialogs +
state visual signals + ~34 Vitest tests; (d) ship new
Playwright describe block `sales-manager-writeup-handoff`
using existing `sales_manager` persona; (e) verify M32.2 close
baselines (frontend ~353 pass; acceptance 23 journeys; `git
grep "UI deferred"` empty); (f) DoD satisfied directly (no
exception); (g) ship the M32.2 handoff at
`docs/handoffs/SESSION_208_m32_inc2_sales_ui.md`; **do NOT
push** — coordinated push at M32 close.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_32_PLANNING.md`** §5.b D4-revised²
   + D5 + D6 + D7 + §5.e M32.2 (governing contract for M32.2)
6. `docs/handoffs/SESSION_206_m32_inc0_planning.md` (M32.0
   planning close-out)
7. `docs/handoffs/SESSION_207_m32_inc1_backend.md` (M32.1
   backend close-out)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-M32.1
   baseline — 161 / 124 / 37 / 321)
9. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3 (M11.3
   DealWriteup entity origin)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs M32.2 co-located inline-dialog
    choice)
11. Memory record
    `feedback_playwright_as_operational_contract.md` (M32.2
    Playwright is the operational contract for sales-manager
    handoff journey)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_207 — Milestone 32.1 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (M32.1 added `0051_m32_credit_application_deal_writeup_fk`).
  Test baseline: **4,995 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. **Vitest baseline: 319
  pass** across 36 test files. M32.2 will add ~34 tests →
  ~353.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS 5.6
  operational; **22 journeys** total. M32.2 will add +1 → 23.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `08fef5f` (M31.2 hash-backfill): 28 passed
  / 0 failed / 2m57s.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
- **Milestones shipped:** M1 → M31. **M32 in progress —
  M32.0 planning + M32.1 backend substrate shipped;** M32.2 +
  M32.3 next.
- **DRF admin surface:** 118 → **121** endpoints (+3 at M32.1:
  writeup list + writeup detail + CA list).
- **Frontend operator routes:** 20 (unchanged; M32.3 will add
  `/dealer-ai-f-and-i/incoming`).
- **Service surface:** 318 → **321** verbs (+3 at M32.1).
- **Frontend surfaces:** unchanged; M32.2 will add sales-
  manager Writeups tab on `LeadDetailModal`; M32.3 will add
  new `DealerFandIIncoming.tsx` page.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-four consecutive milestones** (M10 → M32.1).
  Projected 35 → 36 at M32.2 → M32.3 close.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Milestone 32 status:** ACTIVE (M32.0 + M32.1 shipped;
  M32.2 next).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **124 / 161** (M32.1 close; 3 new endpoints classified as
  backend-only transitionally, re-cover at M32.2 + M32.3).
- **§9 evidence for M33+:** unchanged from M32.0 — NEW C F&I
  chargeback substrate (still pilot-evidence-gated); NEW O2
  + NEW O3; H test-hygiene; gated T/U/L/M; deferred D;
  deferred stable G; new M32 §3 deferrals per M32.0 §5.h.
- **Planning-time streak: 11 (unchanged at M32.1 — pure
  implementation).**
- **DoD amendment (M21.0 §5.f Option B):** M32.1 = seventh
  invocation of exception path (M26 + M27.1 + M28.1 + M29.1 +
  M30.1 + M31.1 + M32.1). M32.2 + M32.3 satisfy DoD directly.
- **First schema-level pairing constraint at M32.1** — the
  nullable OneToOneField backpointer; three-layer defense
  documented + tested (mandatory
  `test_writeup_cannot_link_to_multiple_credit_applications`).
- **First F&I-role-gated list endpoint at M32.1** —
  `admin_credit_application_list`.
- **Historical-migration-immutability discipline preserved** —
  migration 0034 untouched; architectural evolution recorded
  in currently-mutable surfaces only.
- **Durable lessons carried into M32.2+:** all (a)–(x) from
  the SESSION_202 close-state list plus M31-elevated (w) +
  (x). M32 may elevate at retrospective:
  Playwright-independent-fixture (new at M32.3),
  verification-driven revision cycles (surfaced at M32.0).
