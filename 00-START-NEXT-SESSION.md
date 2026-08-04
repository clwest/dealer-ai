---
state: active
date: 2026-08-04
last_session_shipped: SESSION_208
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
next_session: SESSION_209
next_milestone: 32
next_milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
next_increment: 3
next_increment_name: "M32.3 — F&I intake UI + F&I-side Playwright + new f_and_i_manager persona"
---

# Next session — SESSION_209 · Milestone 32 · Increment 3 (M32.3 — F&I intake UI + F&I-side Playwright + new f_and_i_manager persona)

> **M32.2 sales-manager UI shipped at SESSION_208.** Five new
> `salesApi.ts` wrappers (removes shipped-source "UI deferred"
> promise); three new co-located components
> (`DealWriteupForm`, `WriteupConfirmDialogs`,
> `LeadWriteupsPanel`); LeadDetailModal wiring; 35 new Vitest
> tests (+4 test files); new Playwright describe block
> `sales-manager-writeup-handoff` proving the full sales-side
> workflow through the real UI with D5-revised + D6
> irreversibility copy asserted verbatim. **DoD satisfied
> directly** — no exception. **Two §0.a M32.2 amendments** vs
> the M32.0 memo (see `docs/handoffs/SESSION_208_m32_inc2_sales_ui.md`
> §7): (1) technical assertion switched from F&I-gated CA list
> to sales-role-accessible writeup detail endpoint (F&I role
> not available in M32.2); (2) M32.3 spec will live at a
> distinct file under a new `f_and_i_manager` project entry in
> playwright.config.ts (file-per-persona strengthens the
> independence guarantee).
>
> **Baselines at M32.2 close:** backend **4,995 pass**
> (unchanged); frontend **319 → 354 pass** (+35 tests / +4
> files); acceptance **22 → 23 spec files / 29 tests / 30.5s**;
> audit **161 / 128 / 33 / 321** (+4 covered for writeup
> create/approve/hand-off/list; -4 backend-only). Zero-drift
> permission-class streak 34 → 35.
>
> **SESSION_209 opens M32.3 F&I intake UI + F&I-side Playwright
> + new f_and_i_manager persona.** New persona addition per D11
> (personas.ts + login.setup.ts + AUTH_STORAGE.fAndIManager +
> new project entry in playwright.config.ts + idempotent
> `seed_journey_fandi_intake_receipt` seed command provisioning
> both persona and independent `Intake Iris` fixture). New
> `fetchCreditApplications` wrapper in `fAndIApi.ts`. New
> `DealerFandIIncoming.tsx` page at `/dealer-ai-f-and-i/incoming`
> per D8-revised (non-navigational rows; all triage info
> rendered inline — F&I role cannot access `admin_lead_detail`).
> "Incoming" nav link in F&I side nav. ~20 Vitest tests. New
> Playwright describe block `fandi-intake-receipt` at
> `journeys/f_and_i_manager/fandi_intake_receipt.spec.ts` using
> new persona + pre-seeded independent fixture (deterministic
> under any test order or parallelism).
>
> **After M32.3 ships:** M32 close-out fold per M31 precedent
> — `CAPABILITY_MATRIX.md` §7η, audit re-baseline,
> `IMPLEMENTATION_ROADMAP.md` milestone_32_status flip,
> retrospective at `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md`.
>
> **DoD satisfied directly** — no exception.

## First thing SESSION_209 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main` by
  6 commits (SESSION_206 planning + hash-backfill;
  SESSION_207 substrate + hash-backfill; SESSION_208 UI +
  hash-backfill).
- `git log --oneline -8` — top should be SESSION_208 M32.2
  hash-backfill; check for expected M32 commit sequence.
- `python3 manage.py test dealer_ai` → **4,995 pass, 1 skipped,
  0 fail**.
- `cd frontend && npm test` → **354 pass** across 40 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. Confirm working from M32.0 planning memo + M32.2 amendments

Read `docs/roadmap/MILESTONE_32_PLANNING.md` §5.b D3 + D8-revised
+ D11 + §5.e M32.3 before touching code. **Consult the
SESSION_208 handoff §7 amendments** — Amendment 2 changes M32.3
to a separate spec file under a new `f_and_i_manager` project
entry in playwright.config.ts.

Key pre-reads:

- **D3** — CA list endpoint already shipped at M32.1 with fail-
  explicit validation (`intake=true` only accepted; `intake=false`
  → 400; projection includes writeup context via D9-revised²
  FK). M32.3 wires the wrapper + page.
- **D8-revised** — F&I intake rows are **non-navigational** —
  no lead-detail link (would 403 for F&I). All triage fields
  rendered inline: lead name/phone/email; vehicle
  stock/description; four-square terms; CA notes verbatim;
  written-up-by; approved-by; hand-off timestamp.
- **D11** — new `f_and_i_manager` persona requires four files
  updated: `personas.ts`, `login.setup.ts`, `playwright.config.ts`,
  and a new seed command registered in `SEED_COMMANDS`.
- **SESSION_208 handoff §7 Amendment 2** — spec lives at
  `journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`;
  needs new project entry with
  `testMatch: /journeys\/f_and_i_manager\/.*\.spec\.ts/` and
  `storageState: AUTH_STORAGE.fAndIManager`.

### 3. Ship the new f_and_i_manager persona

Per D11 + M32.2 §7 Amendment 2:

- **`acceptance/support/auth/personas.ts`** — add entry with
  `username: "acceptance-f-and-i-manager"`, `password`, and
  role hint.
- **`acceptance/playwright.config.ts`** —
  - Add `fAndIManager: path.join(HERE, ".auth/f_and_i_manager.json")`
    to `AUTH_STORAGE`.
  - Add new project entry with
    `testMatch: /journeys\/f_and_i_manager\/.*\.spec\.ts/` and
    `storageState: AUTH_STORAGE.fAndIManager`.
- **`acceptance/support/auth/login.setup.ts`** —
  - Add `setup("authenticate as f_and_i_manager", ...)` task.
  - Register new seed command in `SEED_COMMANDS`.
- **New management command
  `backend/dealer_ai/management/commands/seed_journey_fandi_intake_receipt.py`**
  — idempotent per M20 lesson; provisions:
  - `acceptance-f-and-i-manager` user with
    `f_and_i_manager` role at default dealership.
  - `Intake Iris` lead.
  - `FANDI-INTAKE-1` vehicle.
  - Approved deal writeup on that lead+vehicle with realistic
    four-square terms.
  - Handed-off CA via real `hand_off_to_fandi` code path (uses
    the M32.1 provenance FK).

### 4. Ship M32.3 F&I intake UI

Per §5.e M32.3:

- **Frontend wrapper `fetchCreditApplications`** in
  `fAndIApi.ts` — consumes GET
  `/admin/credit-applications/list/` with optional `intake`,
  `leadId`, `since` filters + typed projection matching the
  M32.1 D3 endpoint shape (including `writeup_context`).
- **New page `DealerFandIIncoming.tsx`** at
  `/dealer-ai-f-and-i/incoming`:
  - Backend-gated on
    `IsFinanceManagerOrOwnerAtActiveDealership` via the D3
    endpoint. UI shows access-denied branch on 403.
  - Non-navigational rows per D8-revised. Every triage field
    rendered inline (no `<a>` wrapping; no click handlers).
  - Filter controls (intake / lead search / since).
  - Empty state: *"No incoming applications. Credit
    applications from sales-manager hand-offs appear here."*
- **F&I nav "Incoming" link** — extend existing F&I nav
  component; adjacent to "Deals".
- **~20 Vitest tests** — page rendering, filter passthrough,
  empty state, inline field rendering (lead + vehicle + terms
  + notes + attribution + hand-off timestamp), non-
  navigational-row assertions (no `<a>` wrapping / no click
  handler / no cursor-pointer), advisor 403 branch, nav link
  visibility per role.

### 5. Playwright — new F&I-side describe block

Per §5.e M32.3 + M32.2 §7 Amendment 2:

- **New spec** at
  `acceptance/journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`
  with `test.describe("fandi-intake-receipt", …)`.
- Uses new `f_and_i_manager` persona (via project storageState).
- Reads pre-seeded `Intake Iris` fixture deterministically
  by lead name / writeup pk from seed output.
- **Fully independent of M32.2 fixture** — distinct rows; no
  shared state; test order irrelevant; parallelism-safe.
- Steps:
  1. Navigate to `/dealer-ai-f-and-i/incoming`.
  2. Assert row for `Intake Iris` fixture appears with full
     inline data: lead name/phone/email; vehicle stock; four-
     square terms verbatim; written-up-by; approved-by;
     hand-off timestamp.
  3. Assert row is non-navigational (no `<a>` wrapping / no
     click handler / no cursor-pointer).
  4. Assert notes carries the M11.3 `Deal write-up #<pk>
     handoff:` prefix + four-square summary.

### 6. Verify M32.3 close baselines

- Backend suite: **4,995 pass** (unchanged — no backend
  changes in M32.3 aside from seed command).
- Frontend Vitest: **354 → ~374 pass** (+~20 M32.3 tests).
- Acceptance journeys (spec files): 23 → **24**.
- Acceptance suite tests: 29 → **~31+ tests** (accounting for
  new persona setup + new journey).
- `tsc --noEmit` clean across frontend + acceptance.
- Audit: 161 endpoints; 128 → **129** covered (CA list #90
  becomes covered via `fetchCreditApplications` wrapper); 33
  → **32** backend-only.

### 7. DoD satisfied directly

No exception. F&I intake UI ships operator surface; new
`fandi-intake-receipt` describe block satisfies DoD directly.
Documented in §3 of the M32.3 handoff.

### 8. Ship the M32.3 handoff + M32 close-out fold

- `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md`.
- **M32 close-out fold per M31 precedent:**
  - `docs/CAPABILITY_MATRIX.md` §7η — add M32 shipped surface.
  - `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` — final
    baseline.
  - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` —
    milestone_32_status: shipped.
  - `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md` — new file;
    §5 durable-lesson candidates (Playwright-independent-
    fixture; verification-driven revision cycles; historical-
    migration-immutability); §9 M33+ candidates.
- **Coordinated push at M32 close** — after explicit user
  confirmation. Expected 6–8 commits per §9 of M32.2
  handoff.

## Non-goals for SESSION_209

- ❌ Do NOT modify M32.1 backend code or M32.2 frontend code
  (except if regressions surface as §0.a M32.3 amendments).
- ❌ Do NOT modify M11.3 shipped endpoint functions or URLs.
- ❌ Do NOT modify historical migrations.
- ❌ Do NOT modify `admin_lead_detail` role gating — F&I-scoped
  lead-context view is a M33+ evidence-gated deferral per
  §5.h.
- ❌ Do NOT add F&I-workflow state extensions to intake rows
  (In progress / Structuring / etc.) — M32 intake rows carry
  only "Incoming" state.
- ❌ Do NOT push until explicit user confirmation post-M32
  close-out fold.

## Baseline expected at close

- Backend: 4,995 pass (unchanged).
- Frontend: 354 → ~374 pass.
- Acceptance: 23 → 24 spec files / 29 → ~31 tests.
- Audit: 161 endpoints / 128 → 129 covered / 33 → 32 backend-
  only / 321 service verbs.

## NEXT TASK

Start SESSION_209 with (a) starting-state verification;
(b) confirm working from M32.0 planning memo + M32.2 handoff §7
amendments (D3 + D8-revised + D11 + §5.e M32.3 + Amendments 1+2);
(c) ship new `f_and_i_manager` persona (personas.ts +
login.setup.ts + playwright.config.ts + seed command
provisioning `Intake Iris` fixture); (d) ship M32.3 F&I intake
UI (`fetchCreditApplications` wrapper + `DealerFandIIncoming.tsx`
page + F&I nav link + ~20 Vitest tests); (e) new Playwright
spec `journeys/f_and_i_manager/fandi_intake_receipt.spec.ts`
using pre-seeded `Intake Iris` fixture; (f) verify M32.3 close
baselines (frontend ~374 pass; acceptance 24 journeys / ~31
tests; audit 128 → 129 covered); (g) DoD satisfied directly
(no exception); (h) ship the M32.3 handoff + M32 close-out
fold (CAPABILITY_MATRIX §7η, roadmap flip, retrospective);
(i) **coordinated M32 close push after explicit user
confirmation**.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_32_PLANNING.md`** §5.b D3 +
   D8-revised + D11 + §5.e M32.3 (governing contract for M32.3)
6. `docs/handoffs/SESSION_206_m32_inc0_planning.md` (M32.0)
7. `docs/handoffs/SESSION_207_m32_inc1_backend.md` (M32.1)
8. **`docs/handoffs/SESSION_208_m32_inc2_sales_ui.md`** §7
   Amendment 2 (spec file placement for M32.3)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-M32.2
   baseline — 161 / 128 / 33 / 321)
10. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3
11. Memory record `feedback_duplicate_small_stable_logic.md`
12. Memory record
    `feedback_playwright_as_operational_contract.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_208 — Milestone 32.2 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051`. Test baseline: **4,995 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. **Vitest baseline:
  354 pass** across 40 test files (was 319/36 at M32.1 close;
  +35 tests / +4 files at M32.2).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS 5.6
  operational; **23 journeys** total (was 22 at M32.1 close;
  +1 for M32.2 `sales_to_fandi_handoff.spec.ts`). Full-suite
  run: 29 passed / 30.5s.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `08fef5f` (M31.2 hash-backfill): 28 passed
  / 0 failed / 2m57s.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
- **Milestones shipped:** M1 → M31. **M32 in progress —
  M32.0 + M32.1 + M32.2 shipped;** M32.3 next.
- **DRF admin surface:** 121 endpoints (unchanged from M32.1;
  M32.3 ships no new backend endpoints).
- **Frontend operator routes:** 20 (unchanged; M32.3 will add
  `/dealer-ai-f-and-i/incoming`).
- **Service surface:** 321 verbs (unchanged).
- **Frontend surfaces:** M32.2 added sales-manager Writeups
  tab on `LeadDetailModal` via `LeadWriteupsPanel` +
  `DealWriteupForm` + `WriteupConfirmDialogs`; M32.3 will add
  new `DealerFandIIncoming.tsx` page.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-five consecutive milestones** (M10 → M32.2).
  Projected 36 at M32.3 close.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Milestone 32 status:** ACTIVE (M32.0 + M32.1 + M32.2
  shipped; M32.3 next).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **128 / 161** (M32.2 close; +4 vs M32.1 for writeup
  create/approve/hand-off/list; +1 more expected at M32.3 for
  CA list once F&I UI wrapper lands).
- **§9 evidence for M33+:** unchanged from M32.0 + M32.1.
- **Planning-time streak: 11** (unchanged; M32.2 is pure
  implementation per plan with one §0.a amendment on
  Playwright technical assertion).
- **DoD amendment (M21.0 §5.f Option B):** M32.1 = seventh
  invocation of exception path (M26 + M27.1 + M28.1 + M29.1 +
  M30.1 + M31.1 + M32.1); M32.2 satisfies directly; M32.3
  satisfies directly (pending).
- **Two §0.a M32.2 amendments** (SESSION_208 handoff §7):
  Amendment 1 — technical assertion switched to sales-role-
  accessible writeup detail endpoint; Amendment 2 — M32.3
  spec at a distinct file under new `f_and_i_manager`
  project (file-per-persona; strengthens R11 independence
  guarantee).
- **First operator UI to reach M11.3 DealWriteup surface** —
  9 sessions after M11.3 shipped; closes shipped-source
  deferral promise called out in M32.0 §5.a Evidence #1.
- **Durable lessons carried into M32.3+:** all (a)–(x) plus
  M31-elevated (w) + (x). Candidate lessons at M32
  retrospective: (y) Playwright-independent-fixture pattern
  (M32.3); (z) verification-driven revision cycles (M32.0);
  (aa) historical-migration-immutability discipline (M32.1).
