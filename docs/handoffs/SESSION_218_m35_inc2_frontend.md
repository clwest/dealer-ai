---
title: "SESSION_218 handoff — Milestone 35 · Increment 2 (M35.2 — frontend API-client + LenderSubmission components + chip extension + Playwright journey + Submission Sasha seed)"
status: active
type: handoff
date: 2026-08-05
session: 218
milestone: 35
milestone_status: shipped
milestone_name: "Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
increment: 2
increment_status: shipped
commit: TBD
commit_notes: "M35.2 frontend + Playwright + seed session — local commit landed at close; hash backfilled via a subsequent commit; NOT pushed. Coordinated M35 close push awaits explicit user confirmation."
---

# SESSION_218 — Milestone 35 · Increment 2 (M35.2 — frontend API-client + LenderSubmission components + chip extension + Playwright journey + Submission Sasha seed)

## What shipped

SESSION_218 shipped the M35.2 frontend + Playwright substrate per
`docs/roadmap/MILESTONE_35_PLANNING.md` §5.b D5 + D6 + D7 + D8 +
D9 + D10 + D11 + §5.e M35.2. Six user-facing deliverables + one
§0.a scope amendment on M35.1 land in a single local commit:

1. **§0.a M35.2 scope amendment — `latest_lender_submission_id`
   annotation added to M35.1 backend.** Discovered during D8
   implementation: the response form needs a submission pk to
   PATCH, and the M35.1 D3 projection intentionally omitted the
   id field. Small backend amendment (one additional Subquery
   annotation + one projection field) preserves the M35.0 §5.h
   non-goal of NOT adding a GET single-record endpoint (the
   response form now PATCHes via the derived id from the CA
   projection, no GET needed). Backend tests extended to cover
   the new field (cases 1 + 3 + projection case now assert
   `latest_lender_submission_id`). Frontend
   `CreditApplicationProjection` type extended with the field.
   Documented as M35.2 §0.a scope amendment; the discipline
   preserved is: FK discoverability requirements can surface
   during implementation and require small backend amendments —
   these are legitimate §0.a corrections, not scope creep.
2. **D5 API-client extensions** in `frontend/src/lib/fAndIApi.ts`:
   `CreditApplicationProjection` extended with
   `latest_lender_submission_status` (M35.1 D3) +
   `latest_lender_submission_id` (M35.2 §0.a). Four new types
   (`LenderProgramSelectorProjection`, `LenderSubmissionProjection`,
   `RecordLenderSubmissionRequest`, `UpdateLenderSubmissionStatusRequest`).
   Three typed wrappers: `listLenderPrograms()`,
   `recordLenderSubmission(req)`,
   `updateLenderSubmissionStatus(id, req)`. NO `getLenderSubmission`
   (no shipped GET endpoint per M35.0 §4.8). Full docstring
   documents the record-vs-transmit UI language contract and the
   first-loop boundary.
3. **D6 NEW component**
   `frontend/src/components/f-and-i/LenderSubmissionRecordForm.tsx`
   + `.test.tsx` (7 tests). Two fields: LenderProgram select
   (populated on mount) + optional notes. Submit-disabled gate.
   NO `submitted_at` field. NO `status` override. NO
   `counter_terms`/`approval_terms` capture. Header "Record
   lender submission"; button "Record submission". R4 fourth
   defense layer test asserts prohibited-string absence in the
   component source (imported via Vite's `?raw` query — no
   `@types/node` dependency).
4. **D7 NEW component**
   `frontend/src/components/f-and-i/LenderSubmissionResponseForm.tsx`
   + `.test.tsx` (10 tests). Takes `LenderSubmissionResponseContext`
   = `{ id, status, initialNotes? }` (narrow context sourced from
   the CA-list row — not the full LenderSubmissionProjection).
   Three-value status radio (pending excluded); optional notes.
   Mode-conditional headers/buttons: pending → "Record lender
   response" / "Record response"; terminal → "Update lender
   response" / "Update response". Any-to-any correction per
   M10.3 contract. R4 fourth defense layer test.
5. **D8 chip + row-action extension** in
   `frontend/src/pages/DealerFandIIncoming.tsx` + `.test.tsx`
   extension (+12 tests). Chip 2 → 6 states with distinct labels
   + colors + testid suffix + aria-labels per D8 table. State-
   conditional row actions: "Start structuring" (Incoming);
   "Open structure" + "Record lender submission" (In progress);
   "Open structure" + "Record lender response" (Submitted);
   "Open structure" + "Update lender response" (terminal). First-
   loop boundary explicit in code comments. New `ActivePanel`
   kinds `record-submission` + `record-response`. New local
   `recentSubmissions` cache keyed by CA id so post-record the
   response form gets the freshly-returned projection (falls back
   to minimal context on page refresh via the M35.2 §0.a id
   annotation).
6. **D9 NEW Playwright spec**
   `acceptance/journeys/f_and_i_manager/fandi_submission_response_loop.spec.ts`
   tagged `@rerun-hygiene`. 18-step journey covering the full
   send-and-response loop end-to-end with 6 truthfulness
   assertions verbatim per D9 spec: (1) record-vs-transmit
   button text + prohibited-strings absence in form; (2) chip
   flips to "Submitted — awaiting response" with three-signal
   a11y; (3) response header differentiates record-mode vs
   update-mode; (4) chip flips to "Approved" after recording
   `approved`; (5) same-record any-to-any correction (approved →
   counter) flips chip to "Counter-offer received"; (6) full-
   page assertion that no text labels individual DealStructure
   values as "lender-approved terms" (M35 does not capture
   approval_terms).
7. **D10 NEW idempotent seed**
   `backend/dealer_ai/management/commands/seed_journey_fandi_submission_response.py`
   provisioning Submission Sasha fixture: distinct lead name +
   FANDI-SUB-1 vehicle stock + FIXTURE_TERMS + FIXTURE_DEAL_STRUCTURE
   distinct from Iris/Sam so cross-fixture matches fail loudly.
   Three rerun invariants restored across mutate → re-seed
   cycles per M34.0 (ff) contract: (1) DealStructure exists;
   (2) LenderProgram "Yuma Community Bank" active; (3) NO
   LenderSubmission on the DealStructure. Reset-invariant #3
   runs FIRST at seed re-entry so the deletion happens before
   any DealStructure lookup. Seed smoke-tested locally with a
   simulated mutation: created LenderSubmission (count=1), re-
   ran seed, count=0 (invariant restored). `login.setup.ts`
   SEED_COMMANDS extended with the new seed.
8. **D11 four-layer defense** on financial-language contract:
   (a) D5 spec locked verbatim per user directive #10; (b)
   Vitest anti-drift regex assertions in both new component
   tests; (c) Playwright regex assertion in the new spec on the
   full page body; (d) Vitest source-level string-absence tests
   on both component files (`?raw` imports, no `@types/node`).

**Frontend baseline: 402 → 431 pass, 47 files** (+29 tests,
+2 files, 6.35s). Zero regressions.

**Backend baseline: 5,045 pass** (unchanged — M35.2 backend
changes only touched the D2 subquery + D3 projection additive
extension; existing tests updated to assert the new field but
count unchanged; new seed is a management command, not a test).

**Acceptance: 25 → 26 spec files / 32 → 33 tests / 46.3s
fresh-DB run.** Full suite passes.

**Audit at M35.2 close: 163 / 134 / 29 / 321** — exact M35.0
§5.e M35.2 projection match. Three lender endpoints
(`admin/lender-programs/list/`, `admin/lender-submissions/`
POST, `admin/lender-submissions/<pk>/` PATCH) all moved
backend-only → covered by adding the frontend wrappers +
Playwright coverage. Service verbs unchanged (321). Backend-
only decreases 32 → 29.

**M35.2 back-to-back @rerun-hygiene proof** per D9 + M34.2
§0.a correction: two consecutive
`npx playwright test --grep "@rerun-hygiene"` invocations
against the same shared DB. **Both pass:** run 1 = 11 passed /
25.8s (fresh DB); run 2 = 11 passed / 19.5s (against mutated
DB from run 1). Second run is faster (warm cache) — consistent
with M34.2 pattern. **@rerun-hygiene tag count: 3 → 4** (M34's
3 preserved + M35's 1 added). **(ff) durable lesson first re-
application successful** — elevates to load-bearing-across-two-
milestones at M35.2 close.

**DoD satisfied directly** via
`fandi_submission_response_loop.spec.ts` — first M35 direct
DoD satisfaction after M35.1 exception path invocation #12.

## 1. Verification results at open

- **git status:** clean; `HEAD == origin/main + 4` (M35.0
  planning + hash-backfill + M35.1 backend + hash-backfill).
- **git log --oneline -5:** shows the expected M35.1
  sequence (M35.1 hash-backfill `22ae5c1`; M35.1 backend
  `17fa3b8`; M35.0 hash-backfill `50755f3`; M35.0 planning
  `f17e1eb`; M34.2 hash-backfill `c76e6db`).
- **`python3 manage.py test dealer_ai`:** 5,021 → **5,045** at
  M35.1 close (verified pre-session); unchanged during M35.2.
- **`cd frontend && npm test`:** 402 pass at open.
- **`python3 manage.py check`:** clean.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`cd frontend && npx tsc --noEmit`:** clean.
- **`cd acceptance && npx tsc --noEmit`:** clean.
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed.

## 2. §0.a M35.2 amendments applied

**Two §0.a M35.2 amendments applied:**

- **Amendment A — `latest_lender_submission_id` annotation
  gap on M35.1 D3.** Discovered during D8 implementation: the
  LenderSubmissionResponseForm needs a submission pk to PATCH,
  and page refresh erases any locally-cached
  `LenderSubmissionProjection`. M35.1 D3 intentionally omitted
  the id per the M35.0 planning memo, on the reasoning that
  "state reconciled via PATCH response body + list refetch" —
  but that only works within a single session, not across
  refreshes. Fix: add a second Subquery annotation
  (`latest_lender_submission_id`) using the same
  `tenant_latest_submissions` subquery with `.values("pk")[:1]`
  instead of `.values("status")[:1]`; extend the projection;
  extend the frontend type. Tests updated in-place (cases 1 +
  3 + projection case now assert both status AND id fields).
  Amendment preserves M35.0 §5.h non-goal of NOT adding a GET
  single-record endpoint. Documented in
  `credit_application.py` D2 docstring + `_project_credit_application_with_writeup`
  D3 docstring + fAndIApi.ts type comment.
- **Amendment B — test isolation bug in
  `DealerFandIIncoming.test.tsx`.** Discovered when the new
  M35.2 chip tests failed in batch but passed individually.
  Root cause: a pre-existing M33.2 test ("opens the structuring
  form panel...") queues two `mockResolvedValueOnce` responses
  (initial load + post-create refetch) but only consumes one
  (Cancel is clicked instead of Submit). `vi.clearAllMocks()`
  in `beforeEach` clears call records but NOT queued
  implementations, so the leftover queued response polluted
  the next test's fetch. Fix: change `beforeEach` to
  `vi.resetAllMocks()` which clears both. Comment added
  explaining the reason. This is a pre-existing bug that
  M35.2 surfaced — not introduced by M35.2.

Zero-drift permission class preserved by M35.1 (D4 endpoint
reuses `_M101_PERMS`); M35.2 adds no backend endpoints so
streak stays at 39. Postgres OuterRef verification passed at
M35.1 open per R11 (unchanged at M35.2 — the added
`latest_lender_submission_id` annotation uses the same
correlation pattern).

## 3. What shipped (details)

### 3.1 §0.a Amendment A — backend `latest_lender_submission_id` annotation

`services/f_and_i/credit_application.py`:

- Added `latest_lender_submission_id=Subquery(tenant_latest_submissions.values("pk")[:1])`
  to `.annotate(...)`.
- Extended docstring with a fifth bullet documenting the id
  field, its NULL conditions, and the M35.2 §0.a origin.

`views_f_and_i.py`:

- `_project_credit_application_with_writeup(app)` extended
  with `base["latest_lender_submission_id"] = app.latest_lender_submission_id`.
- Docstring updated to document the new field.

`tests/test_m351_lender_submission_status_annotation.py`:

- Cases 1 + 3 extended to assert the id annotation.
- Projection test extended to assert
  `row["latest_lender_submission_id"]` equals the created
  submission's pk.

### 3.2 D5 API-client extensions

`frontend/src/lib/fAndIApi.ts`:

- `CreditApplicationProjection` gains
  `latest_lender_submission_status` (M35.1) +
  `latest_lender_submission_id` (M35.2 §0.a).
- NEW `LenderSubmissionStatus` type alias.
- NEW `LenderProgramSelectorProjection` = `{id, name}`.
- NEW `LenderSubmissionProjection` (full — used for PATCH
  response body).
- NEW `RecordLenderSubmissionRequest` = `{deal_structure_id,
  lender_program_id, notes?}`.
- NEW `UpdateLenderSubmissionStatusRequest` = `{status:
  'approved' | 'counter' | 'declined', notes?}`.
- Three typed wrappers: `listLenderPrograms`,
  `recordLenderSubmission`, `updateLenderSubmissionStatus`.

### 3.3 D6 NEW `LenderSubmissionRecordForm.tsx`

7 tests: submit-disabled gate; POST payload shape (no
submitted_at / no status / no counter or approval terms);
notes only when non-empty; programs-empty message; programs
error handling; language contract (record-not-transmit);
submit error handling.

### 3.4 D7 NEW `LenderSubmissionResponseForm.tsx`

10 tests: record-mode language when pending; update-mode
language for approved/counter/declined; only three response
options (pending excluded); terminal-status pre-selection;
submit-disabled gate; minimal PATCH payload when notes
unchanged; notes included when edited; no counter_terms /
approval_terms fields; error handling; language contract.

Response form's `submission` prop takes
`LenderSubmissionResponseContext` = `{id, status,
initialNotes?}` (not full projection).

### 3.5 D8 `DealerFandIIncoming.tsx` chip + row-action extension

- 6 chip states with distinct labels + colors + testids +
  aria-labels per D8 table.
- `deriveChipState(ca)` helper: pure function of
  `has_deal_structure` + `latest_lender_submission_status`.
- Three lookup dicts: `CHIP_LABELS`, `CHIP_ARIA`,
  `CHIP_CLASSES`.
- `ActivePanel` extended with `record-submission` +
  `record-response` kinds.
- `openResponsePanel(caId, dealStructureId)` helper — reads
  `latest_lender_submission_id` + `latest_lender_submission_status`
  from the CA row; consults `recentSubmissions` cache for
  freshly-returned projections; falls back to minimal context
  on page refresh.
- Row-action rendering: state-conditional per D8 table
  (record-submission on In progress; record-response on
  Submitted; update-response on terminal).
- Panel rendering: 4 kinds (form, read, record-submission,
  record-response) each in a dedicated Card wrapper with a
  testid; refetch after mutation.

12 new test cases in `DealerFandIIncoming.test.tsx`: 4 chip-
state cases via `it.each`; 5 row-action tests including 3
terminal-status cases via `it.each`; 2 panel-open tests.
Existing 21 M32/M33 tests unchanged.

### 3.6 D9 NEW Playwright spec

`acceptance/journeys/f_and_i_manager/fandi_submission_response_loop.spec.ts`
tagged `@rerun-hygiene`. 18-step journey; 6 truthfulness
assertions verbatim per D9. Runtime ~750ms per invocation.

### 3.7 D10 NEW `seed_journey_fandi_submission_response.py`

- Submission Sasha fixture with all 3 rerun invariants.
- `_delete_prior_lender_submissions` method runs FIRST at seed
  entry — deletes any LenderSubmissions on the fixture
  DealStructure created by prior journey runs.
- `_provision_lender_program` restores `is_active=True` if a
  prior mutation deactivated the program.
- `_provision_deal_structure` reuses existing DS via `.first()`
  ordered by `("-created_at", "-pk")` OR creates a fresh one
  via `record_deal_structure` service verb.
- `--reset` flag deletes the fixture chain (lead, vehicle,
  program) for teardown; CA row survives via SET_NULL
  (retention-clock discipline per M10.1 §5.e).
- `login.setup.ts` SEED_COMMANDS extended.

Seed idempotency smoke-tested locally:
- Fresh run: provisioned all rows; count=0 LenderSubmissions.
- Second run: reused all rows; count=0 LenderSubmissions.
- Mutation simulated (created LenderSubmission via shell);
  seed re-run; invariant restored (count=0).

### 3.8 D11 four-layer defense

- (a) Spec locked verbatim per user directive #10 in M35.0.
- (b) Vitest regex assertions in
  `LenderSubmissionRecordForm.test.tsx` +
  `LenderSubmissionResponseForm.test.tsx`.
- (c) Playwright regex assertion in
  `fandi_submission_response_loop.spec.ts` on the full page
  body (`FORBIDDEN_LENDER_APPROVED_TERMS_LANGUAGE` +
  `FORBIDDEN_TRANSMIT_LANGUAGE`).
- (d) Vitest source-level `?raw`-import string-absence tests
  on both component files.

Prohibited strings enumerated only in test files (never in
component source) so component files cannot self-match. This
is a candidate durable lesson: **R4-class defense tests that
scan source must not enumerate the prohibited terms in the
scanned file** — enumerate in the scanner only.

## 4. Baselines at M35.2 close

- **Backend:** 5,045 pass, 1 skipped, 0 fail (174.844s).
- **Frontend Vitest:** 431 pass across 47 files (6.35s;
  +29 tests, +2 files from M35.1 close).
- **Acceptance:** 26 spec files / 33 tests / 0 failed / 46.3s
  fresh-DB run. @rerun-hygiene tag count 3 → **4**.
- **Migrations:** 0001–0051 (unchanged; no new migration).
- **Audit:** **163 / 134 / 29 / 321** — exact M35.0 projection
  match. +3 covered; -3 backend-only; total unchanged; service
  verbs unchanged.
- **DRF admin surface:** 123 (unchanged from M35.1).
- **Frontend operator routes:** 21 (unchanged; extended
  DealerFandIIncoming in place).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service verbs enumerated:** 321 (unchanged).
- **Permission classes:** 7 actual, zero-drift streak
  **39 consecutive** (M10 → M35 — preserved).
- **Playwright fixtures:** Intake Iris (M32.3) + Structure Sam
  (M33.2) + **Submission Sasha (M35.2 NEW)** — all three live
  and independent; three fixtures + three journeys.
- **`@rerun-hygiene` tagged specs:** 4 (M34's 3 sales_manager/
  daily_startup + recon/workflow + office/accounting_workflow
  + M35's 1 fandi_submission_response_loop).
- **Django check + makemigrations --check:** clean.

## 5. M35.2 back-to-back @rerun-hygiene proof

Per D9 + M34.2 §0.a correction: two consecutive
`npx playwright test --grep "@rerun-hygiene"` invocations
against the same shared DB. Fresh DB before first run;
second run consumes mutated state.

- **Run 1:** 11 passed / **25.8s** (fresh DB).
- **Run 2:** 11 passed / **19.5s** (against mutated DB from
  run 1).

Second run is 6.3s faster (warm cache; consistent with M34.2
pattern). Both runs demonstrate that all four `@rerun-hygiene`
journeys' seeds restore their invariants across mutations.

**Durable lesson (ff) first re-application successful.**
Elevates to **load-bearing-across-two-milestones** at M35.2
close (M34.0 origin + M35.2 re-application).

## 6. DoD compliance

**DoD satisfied directly** via
`fandi_submission_response_loop.spec.ts` — the new Playwright
journey covers the full operational send-and-response loop
end-to-end for the F&I manager persona. First M35 direct DoD
satisfaction; M35.1 was the exception path invocation #12.

Twelve total exception path invocations across customer-facing
milestones (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1 +
M32.1 + M33.1 + M34.1 + M34.2 + M35.1). Pattern preserved.

## 7. Streaks at M35.2 close

- **Planning-time as-recommended streak:** 13 → 14 at M35
  close (target selected as recommended at M35.0; ten user-
  directed corrections applied at planning-open but these
  strengthened the locked design). Historical run of 89 across
  M10 → M23 preserved.
- **Zero-drift permission-class streak:** **38 → 39**
  consecutive milestones (M10 → M35). M35.1 D4 endpoint reused
  `_M101_PERMS`; M35.2 adds no backend endpoints.
- **Substrate-compound-value continuation:** M32 + M33 + M35 =
  **3 links in the F&I depth arc**. Restart after M34's
  deferral-close intentional pause.
- **DoD exception path invocations:** 12 (unchanged at M35.2
  — direct satisfaction).
- **First activation of M10.3 substrate operationally
  complete** — the two shipped-but-dormant LenderSubmission
  endpoints (POST + PATCH; shipped SESSION_108) now have
  operator UI consumers. 110-session substrate-to-UI gap
  closed — new project record (surpasses M33's 19-session gap
  on M10.2 DealStructure).
- **F&I depth arc unlocks entire downstream chain.** With
  LenderSubmission operational, Stipulation / Contract / BEPA
  / Funding / Chargeback / Compliance / DealJacket / Lender
  Fit are all now technically activate-able (they remain
  deferred per §5.h until their own scope decisions).
- **Verification-driven revision cycles (z):** fourth
  invocation at M35.0 (10 corrections). Preserved discipline
  at M35.2 via §0.a Amendment A — implementation-time
  discovery of the id-annotation gap resolved via small in-
  session backend amendment rather than deferring the entire
  response form to a future milestone.
- **Coverage-projection truthfulness (cc):** **seventh
  invocation at M35.2 close** — audit projection
  163/134/29/321 locked from direct artifact inspection at
  M35.0 planning; observed at close matches verbatim. (cc)
  continues to hold as load-bearing-across-three-milestones.
- **(ff) — rerun-safety-against-shared-state:** **first re-
  application at M35.2** — Submission Sasha seed idempotent
  from first shipping day; @rerun-hygiene tag + back-to-back
  proof successful. Elevates to **load-bearing-across-two-
  milestones** (M34.0 origin + M35.2 re-application).
- **R4 fourth-defense-layer pattern proven:** source-level
  string-absence tests via Vite `?raw` imports work without
  `@types/node`. Prohibited terms enumerated only in test
  files. Candidate durable lesson: **R4-class scanner tests
  must not enumerate the prohibited strings inside the scanned
  file** — enumerate in the scanner only. First observation at
  M35.2; may elevate on re-observation.
- **§0.a implementation-time amendment discipline:** M35.2
  §0.a Amendment A (id-annotation gap) is a legitimate small
  backend scope amendment surfaced by frontend implementation.
  M35.1 also had a §0.a (comment-inside-path). Both fixed in-
  session without deferring scope. Convention preserves
  planning-time streak on target-selection basis.

## 8. Push status

**No push at SESSION_218 close.** M35.2 lands in a single
local-only commit per the standard M28.2 / M29.2 / M30.2 /
M31.2 / M32.3 / M33.2 / M34.2 cadence. Coordinated M35 close
push deferred to explicit user confirmation.

Local commits at SESSION_218 close:

- SESSION_218 §0.a amendment (backend annotation extension +
  test updates) + D5 API-client + D6 record form + test + D7
  response form + test + D8 chip extension + test extension +
  D9 Playwright spec + D10 seed + login.setup.ts extension +
  audit regeneration + this handoff + `00-START-NEXT-SESSION.md`
  flip land in a single local-only commit; hash backfill via
  a subsequent commit per convention.

Expected M35 commit count at coordinated push: **6**
(M35.0 planning `f17e1eb`; M35.0 hash-backfill `50755f3`;
M35.1 backend `17fa3b8`; M35.1 hash-backfill `22ae5c1`;
M35.2 frontend + Playwright (this session); M35.2 hash-
backfill (follow-up)) — plus optional close-out fold commit
if a M35 retrospective is written before push.

## 9. Next session priorities

**M35 SHIPPED at M35.2.** Anchor question answered: *Can an
F&I manager record where a structured deal was submitted,
capture the lender's response, and see the resulting
operational state without leaving Dealer OS?* — YES, via the
Playwright-verified send-and-response loop.

`00-START-NEXT-SESSION.md` overwritten for **SESSION_219 ·
Milestone 36 · Increment 0 (M36.0 — planning refinement +
target selection)** per M35 close.

Standing candidate list (unchanged from M35 close except
"Lender Submission Activation" SHIPPED):

- **NEW C — F&I chargeback substrate** (pilot-evidence gated;
  strongest post-M35 context — LenderSubmission unblocks the
  downstream chain including Chargeback).
- **Lender Fit Recommendations** (D10 elevation; three of
  four blockers remain — M35 did NOT deliver the fourth
  blocker intentionally; narrow LenderProgram list projection
  preserved).
- **NEW F&I workflow-state extensions beyond M35's four new
  derived states** (Contracted / Funded via M10.5 substrate
  activation, or richer state model).
- **Contract UI** (M10.5 substrate now unblockable per M35).
- **Funding UI** (M10.5 substrate now unblockable per M35).
- **Stipulation UI** (M10.4 substrate now unblockable per M35).
- **Chargeback UI** (M10.6 substrate now unblockable per M35;
  also = NEW C above).
- **Compliance UI** (M10.7 substrate now unblockable per M35).
- **DealJacket UI** (M10.7 substrate now unblockable per M35).
- **NEW F&I-scoped lead-context view** (unchanged M32 §3
  deferral).
- **Cross-lead sales-manager pending-approval queue** (unchanged
  M32 §3 deferral).
- **Direct-create CA structuring branch** (M33 §5.h explicit
  deferral).
- **Iteration UX** (M33 D9 deferral).
- **PATCH on DealStructure** (activation-vocabulary preservation).
- **Alternate-lender resubmission** (M35 §5.h deferral —
  requires iteration UX).
- **Submission history view** (M35 §5.h deferral).
- **Structured `counter_terms` / `approval_terms` capture**
  (M35 §5.h deferral).
- **LenderProgram create UI** (M35 §5.h deferral).
- **NEW O2 / NEW O3** (10-milestone deferral).
- **Gated:** T, U, L, M.
- **Deferred:** D, G.
- **Deferred at M35 §5.h + all prior deferrals** — carried
  forward unchanged.

**Standing question at M36.0** (three natural next moves):
(a) **continue F&I depth arc** at 4 links via NEW C chargeback
substrate (first M10.6 UI activation) OR NEW F&I workflow-
state extensions (Contract/Funding UI + derived state extension
to 8-state chip); (b) **reset to breadth** via a fresh direct-
operator gap; (c) **close another §3 deferral** per M34
precedent. F&I arc's compound value has grown significantly at
M35 — unblocking the M10.5–M10.7 substrate makes each F&I arc
continuation cheaper (no new substrate needed).

Per M34 §9 standing question preserved: evaluate through the
primary operational-coverage lens first; secondary reframes
only if evidence surfaces.

First-thing sequence for SESSION_219 per M28.0 / M29.0 /
M30.0 / M31.0 / M32.0 / M33.0 / M34.0 / M35.0 pattern:

1. **Verify starting state** (git; backend 5,045; frontend
   431; acceptance 26/33; audit 163/134/29/321).
2. **If M35 pushed — monitor first M35 CI run.**
3. **Regenerate the audit artifact.**
4. **Present the M36 candidate list.**
5. **Recommend a target for §5.a under the primary
   operational-coverage lens.**
6. **Draft §5.b–§5.h load-bearing decisions** once §5.a locks.
7. **Verify BOTH intake AND downstream UI surfaces + FK
   discoverability before locking §5.b + §5.d.**
8. **DoD compliance check.**
9. **Expand M36 planning skeleton.**
10. **Ship the M36.0 handoff** at
    `docs/handoffs/SESSION_219_m36_inc0_planning.md`.

## 10. Non-goals for SESSION_219

- ❌ Do NOT ship implementation code — M36.0 is planning only.
- ❌ Do NOT open any M36 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M35 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI regression
  fixes land as §0.a M36.0 amendments.
- ❌ Do NOT re-open the M35 first-loop boundary (same-record
  status update allowed; new-submission / alternate-lender /
  history / multi-submission mgmt deferred).
- ❌ Do NOT re-open the M35 §5.h deferrals without user
  direction (structured terms; LenderProgram create UI;
  submission history; iteration UX; alternate-lender flow).
- ❌ Do NOT re-open the (ff) `@rerun-hygiene` tag or back-to-
  back double-run proof mechanism — both locked and now load-
  bearing-across-two-milestones.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_35_PLANNING.md`** (governing
   contract for M35 — now historical at M35 close, but the
   §5.b + §5.h + R11 locks remain the source of truth for
   what M35 shipped)
6. `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §9 (F&I depth-
   arc standing question — preserved for M36)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (regenerated
   at M35.2 close: 163 / 134 / 29 / 321)
8. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.4 + §1.5 + §1.6
   + §1.7 (Stipulation / Contract / Funding / Chargeback /
   Compliance substrate contracts — now candidates for
   activation)
9. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D5 (financial-
   language contract; extended at M35 D11 four-layer defense)
10. `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D7 + D10
    ((ff) rerun-hygiene contract; first re-applied at M35.2)
11. `docs/CAPABILITY_MATRIX.md` §7ι (M34); §7κ added at M35
    close
12. `docs/handoffs/SESSION_217_m35_inc1_backend.md` (M35.1
    shipped)
13. **This handoff** (`SESSION_218_m35_inc2_frontend.md`)
14. Memory record
    `feedback_verify_fk_discoverability_before_lock.md` (M27.0
    origin — resolved via M35.1 D4; re-invoked at M35.2 §0.a
    Amendment A for `latest_lender_submission_id` gap)
15. Memory record
    `feedback_playwright_as_operational_contract.md` (M35.2
    re-applied at D9 + D10 + back-to-back proof)
16. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — no shared helper between M35 record and
    response forms)
17. Memory record `feedback_terminal_output_discipline.md`
