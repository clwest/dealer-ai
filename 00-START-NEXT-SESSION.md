---
state: active
date: 2026-08-05
last_session_shipped: SESSION_217
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
milestone_32_status: shipped
milestone_33_status: shipped
milestone_34_status: shipped
milestone_35_status: active
next_session: SESSION_218
next_milestone: 35
next_milestone_name: "Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
next_increment: 2
next_increment_name: "M35.2 — Frontend API-client + LenderSubmissionRecordForm + LenderSubmissionResponseForm + DealerFandIIncoming chip extension + Playwright journey + Submission Sasha seed"
---

# Next session — SESSION_218 · Milestone 35 · Increment 2 (M35.2 — frontend API-client + components + chip extension + Playwright journey + Submission Sasha seed)

> **M35.1 SHIPPED at SESSION_217.** Backend FK-discovery endpoint
> + subquery annotations + projection extension + 24 regression
> tests. Backend baseline 5,021 → 5,045; audit 163/131/32/321
> (+1 total endpoint, +1 backend-only; covered unchanged; service
> verbs unchanged). Postgres OuterRef R11 verification PASSED
> (SQL length 1620 chars byte-identical to SQLite). Zero
> regressions. DoD exception path invocation #12. One §0.a
> amendment applied (comment-inside-path() audit-regex
> incompatibility — fixed by moving comment above path() line;
> (cc) sixth invocation).
>
> **SESSION_218 opens M35.2** — the customer-facing half of
> M35. Frontend API-client (3 wrappers, 4 types), two new
> components (`LenderSubmissionRecordForm` +
> `LenderSubmissionResponseForm`), chip extension in
> `DealerFandIIncoming` (2 → 6 states), new Playwright journey
> (`fandi_submission_response_loop.spec.ts` tagged
> `@rerun-hygiene`), Submission Sasha idempotent seed. **DoD
> satisfied directly** — first M35 direct DoD satisfaction.
>
> **First re-application of durable lesson (ff) at M35.2**
> (M34.0 D8 origin: *Acceptance journeys must be independently
> rerunnable against shared state; green-on-clean-DB alone is
> insufficient evidence of operational reliability.*). Submission
> Sasha seed idempotent from first shipping day per D10; new
> Playwright spec tagged `@rerun-hygiene` per D9; back-to-back
> double-run proof at close per D9 (NOT `--repeat-each=2` per
> M34.2 §0.a correction). On re-application (ff) elevates to
> load-bearing-across-two-milestones.
>
> **Four-layer financial-language contract** per D11: spec +
> Vitest anti-drift regex + Playwright regex + Vitest string-
> absence test on both new component files. UI language contract
> (per M35.0 §4.7 verification #7): record-not-transmit
> ("Record lender submission" / "Submitted to"; NEVER "Send" /
> "Transmit" / "Submit to lender" / "Contact lender" /
> "Submitting…").

## First thing SESSION_218 must do

### 1. Verify starting state

- `git status` — clean; local HEAD ahead of `origin/main`
  by 4 commits (M35.0 planning + M35.0 hash-backfill + M35.1
  backend + M35.1 hash-backfill) if not yet pushed.
- `git log --oneline -6` — verify expected sequence.
- `python3 manage.py test dealer_ai` → **5,045 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **402 pass** across 45 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. Confirm working from M35.0 planning memo

Read `docs/roadmap/MILESTONE_35_PLANNING.md` §5.b D5 + D6 + D7
+ D8 + D9 + D10 + D11 + §5.e M35.2 + §5.c R4 + R7 + R8 + R10
before touching any file. Verify no scope drift from what was
locked at M35.0.

### 3. Ship M35.2 frontend + Playwright substrate

Per §5.e M35.2:

- **D5 API-client** (`frontend/src/lib/fAndIApi.ts`):
  - Type: `CreditApplicationProjection` gets
    `latest_lender_submission_status: 'pending' | 'approved' |
    'counter' | 'declined' | null`.
  - NEW types: `LenderProgramSelectorProjection = {id: number;
    name: string}`; `LenderSubmissionProjection` (full);
    `RecordLenderSubmissionRequest = {deal_structure_id: number;
    lender_program_id: number; notes?: string}` (NO
    `submitted_at`; NO `status` override);
    `UpdateLenderSubmissionStatusRequest = {status:
    'approved' | 'counter' | 'declined'; notes?: string}`
    (pending excluded).
  - Three typed wrappers: `listLenderPrograms()`,
    `recordLenderSubmission(req)`,
    `updateLenderSubmissionStatus(id, req)`.
  - NO `getLenderSubmission` (no shipped GET endpoint).
- **D6 NEW** `frontend/src/components/f-and-i/LenderSubmissionRecordForm.tsx`:
  LenderProgram select (populated from `listLenderPrograms()`
  on mount); optional notes; submit disabled until program
  selected; header "Record lender submission"; button "Record
  submission"; PROHIBITED strings must not appear.
- **D7 NEW** `LenderSubmissionResponseForm.tsx`: status radio
  (approved/counter/declined; pending excluded); optional
  notes; header/button mode-conditional (pending → "Record
  lender response" / "Record response"; terminal → "Update
  lender response" / "Update response").
- **D8** `DealerFandIIncoming.tsx` chip 2 → 6 states + state-
  conditional row actions per D8 table. First-loop boundary
  comments in code.
- **D9 NEW** `acceptance/journeys/f_and_i_manager/fandi_submission_response_loop.spec.ts`
  tagged `@rerun-hygiene` with 6 truthfulness assertions.
- **D10 NEW** `backend/dealer_ai/management/commands/seed_journey_fandi_submission_response.py`
  Submission Sasha fixture with 3 rerun invariants.
- Extend `acceptance/support/auth/login.setup.ts`
  SEED_COMMANDS list with the new seed.
- **D11** four-layer defense on financial-language contract.
- Add Vitest test files:
  - `LenderSubmissionRecordForm.test.tsx` — submit-disabled
    gate; POST shape; success handling; language regex;
    prohibited-strings absence.
  - `LenderSubmissionResponseForm.test.tsx` — three-value
    radio; header language differentiation; PATCH shape;
    language regex; counter_terms/approval_terms field
    absence.
  - Extend `DealerFandIIncoming.test.tsx` — 6 chip states;
    state-conditional row actions; refetch after mutation.

### 4. Verify M35.2 close baselines

- Backend suite: 5,045 pass (unchanged — M35.2 adds no
  backend code).
- Frontend Vitest: 402 → ~430 pass (projected +28 tests
  across 4 new/extended files; refine at close).
- Acceptance: 25 → 26 spec files / 32 → 33 tests; runtime
  ≤37s (budget +2s for new spec).
- Regenerate audit artifact:
  ```bash
  cd backend
  python3 -m dealer_ai.scripts.audit_operational_surface
  ```
  Expected: **163 / 134 / 29 / 321** (three lender endpoints
  move backend-only → covered when their wrappers + journey
  land).

### 5. M35.2 proof mechanism at close (D9 + M34.2 §0.a correction)

Back-to-back invocations against the same shared DB:

```bash
cd acceptance
npx playwright test --grep "@rerun-hygiene"
# First run — expect 4 tests passing (M34's 3 + M35's 1)
npx playwright test --grep "@rerun-hygiene"
# Second run — MUST pass with same shared DB state
```

**NOT `--repeat-each=2`.** Record both run timings in the
M35.2 handoff §7 as evidence.

### 6. DoD compliance

**DoD satisfied directly** — first M35 direct satisfaction
after M35.1 exception path invocation #12. Document in §3 of
M35.2 handoff: the `fandi_submission_response_loop.spec.ts`
new journey covers the full send-and-response operational
loop end-to-end.

### 7. Ship the M35.2 handoff

- `docs/handoffs/SESSION_218_m35_inc2_frontend.md`.
- **Do NOT push** — coordinated M35 push at close.

## Non-goals for SESSION_218

- ❌ Do NOT ship backend code — M35.1 is complete.
- ❌ Do NOT add a GET single-record LenderSubmission endpoint
  (§5.h explicit deferral; PATCH response body suffices).
- ❌ Do NOT expose `contact` / `terms_summary` / `is_active`
  via the D4 projection (narrow `{id, name}` locked at M35.1).
- ❌ Do NOT ship LenderProgram create UI.
- ❌ Do NOT ship structured `counter_terms` / `approval_terms`
  capture.
- ❌ Do NOT add `submitted_at` operator-editable field.
- ❌ Do NOT surface second-submission-on-same-DS UX.
- ❌ Do NOT expand into alternate-lender / submission-history /
  multi-submission management.
- ❌ Do NOT use `--repeat-each=2`.
- ❌ Do NOT modify M32.3 / M33.2 / M34 fixtures.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M35.1 shipped surface.

## Baseline expected at close

- Backend: 5,045 pass, 1 skipped, 0 fail (unchanged).
- Frontend: 402 → ~430 pass.
- Acceptance: 25 → 26 spec files; 32 → 33 tests.
- Migrations: 0001–0051 (unchanged).
- Audit: **163 / 134 / 29 / 321**.
- DRF admin surface: 123 (unchanged).
- Frontend operator routes: 21 (unchanged — extends existing
  F&I intake page in place).
- Frontend components: +2 new in `frontend/src/components/f-and-i/`.
- Service verbs enumerated: 321 (unchanged).
- Permission classes: 7 actual, zero-drift streak
  **39 consecutive** (M10 → M35).
- Playwright fixtures: +1 new (Submission Sasha).
- Playwright specs: 25 → 26.
- @rerun-hygiene tags: 3 → 4.

## NEXT TASK

Start SESSION_218 with (a) starting-state verification;
(b) confirm working from M35.0 planning memo; (c) ship M35.2
frontend + Playwright + seed per §5.e (D5 API-client + D6/D7
components + D8 chip extension + D9 Playwright journey + D10
seed + D11 four-layer defense); (d) verify baselines (backend
unchanged; frontend ~430; acceptance 26/33; audit
163/134/29/321); (e) back-to-back `@rerun-hygiene` proof
mechanism (both runs must pass); (f) document DoD direct
satisfaction; (g) ship the M35.2 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_35_PLANNING.md`** (governing
   contract for M35)
6. `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §9 (M35
   candidate list + F&I depth-arc standing question)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (regenerated at M35.1 close: 163 / 131 / 32 / 321)
8. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D5 (financial-
   language contract — extended at M35 D11 + R4)
9. `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D7 + D10
   (rerun-hygiene contract preserved at M35 D9 + D10)
10. `docs/CAPABILITY_MATRIX.md` §7ι (M34 shipped surface);
    §7κ added at M35 close
11. `docs/handoffs/SESSION_217_m35_inc1_backend.md` (M35.1
    shipped)
12. `docs/handoffs/SESSION_216_m35_inc0_planning.md` (M35.0
    shipped)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — resolved via M35.1 D4)
14. Memory record
    `feedback_playwright_as_operational_contract.md` (M34
    preserves the contract; M35.2 re-applies it)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_217 — Milestone 35 · Increment 1 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged). Test baseline: **5,045 pass**, 1
  skipped, 0 fail (+24 M35.1 regression tests).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 402 pass** (unchanged
  M35.1).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS 5.6
  operational; **25 journeys** total (unchanged M35.1).
- **Acceptance (CI):** live; latest run on `origin/main`
  `c76e6db` (M34.2) — success in 3m1s. First M35 CI run pending
  on M35 push.
- **Async runtime:** unchanged.
- **Milestones shipped:** M1 → **M34**. **M35.1 shipped**;
  M35.2 pending.
- **DRF admin surface:** 122 → **123** endpoints (M35.1 +1
  `admin/lender-programs/list/`).
- **Frontend operator routes:** **21** (unchanged; +0
  projected at M35.2).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged — M35.1 reused
  shipped `list_active_lender_programs`).
- **Frontend surfaces:** unchanged at M35.1; +2 new components
  projected at M35.2.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **39 consecutive milestones** (M10 → M35.1). M35.2 projected
  to preserve.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 35 status:** ACTIVE — M35.0 planning + M35.1
  backend shipped; M35.2 frontend + Playwright + seed is next.
- **Audit tooling status:** unchanged from M26.1. Coverage
  **131 / 163** at M35.1 close. M35.2 projected close: **134
  / 163** (three lender endpoints move backend-only → covered).
- **Playwright personas:** **6 actual** (unchanged; M35.2
  reuses `f_and_i_manager`).
- **Playwright fixtures:** Intake Iris (M32.3) + Structure Sam
  (M33.2) both live and independent. **Submission Sasha to be
  added at M35.2** per D10.
- **M35 shipped surface at M35.1 close:** one new endpoint
  (`admin/lender-programs/list/`, `_M101_PERMS`, narrow `{id,
  name}` projection); two new queryset annotations
  (`latest_deal_structure_id` preserved from M33.1;
  `latest_lender_submission_status` NEW); one projection field
  (`latest_lender_submission_status` on CA list).
- **§0.a M35.1 amendments applied:** one — comment-inside-
  path() audit-regex incompatibility (fixed by moving comment
  above path() line). Recorded as (cc) sixth invocation and
  candidate audit-comment-placement discipline lesson.
- **Postgres OuterRef R11 verification:** PASSED at M35.1
  §0.a first item. Nested-annotation OuterRef pattern works
  on both SQLite (M35.0 §4.8) and Postgres (M35.1). R11
  fallback preserved as documentation only; not needed.
- **DoD amendment (M21.0 §5.f Option B):** exception path
  invocation #12 at M35.1 (M26 + M27.1 + M28.1 + M29.1 +
  M30.1 + M31.1 + M32.1 + M33.1 + M34.1 + M34.2 + M35.1).
  M35.2 satisfies DoD directly.
- **Durable lessons carried into M35.2+:** all (a)–(ff)
  preserved from M35.1 close. (cc) load-bearing-across-three-
  milestones with sixth invocation at M35.1 (added new sub-
  class: audit-script syntactic parsing constraints). (ff)
  awaits first re-application at M35.2. (z) verification-
  driven revision cycles fourth invocation at M35.0 (10 user-
  directed corrections). (u) audit-correctness-as-supporting-
  infrastructure re-invoked at M35.1 §0.a.
