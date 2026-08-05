---
title: "SESSION_217 handoff — Milestone 35 · Increment 1 (M35.1 — backend FK-discovery endpoint + subquery annotations + projection extension + Django regression tests)"
status: active
type: handoff
date: 2026-08-05
session: 217
milestone: 35
milestone_status: active
milestone_name: "Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
increment: 1
increment_status: shipped
commit: TBD
commit_notes: "M35.1 backend session — local commit landed at close; hash backfilled via a subsequent commit; NOT pushed. Coordinated M35 close push deferred to explicit user confirmation after M35.2 close."
---

# SESSION_217 — Milestone 35 · Increment 1 (M35.1 — backend FK-discovery endpoint + subquery annotations + projection extension + Django regression tests)

## What shipped

SESSION_217 shipped the M35.1 backend substrate per
`docs/roadmap/MILESTONE_35_PLANNING.md` §5.b D1 + D2 + D3 + D4
+ §5.e M35.1. Four deliverables landed in a single local commit:

1. **§0.a first item — Postgres OuterRef re-verification (R11
   mitigation) PASSED.** Before any implementation, spun up a
   fresh Postgres 15.13 database (`dealer_ai_m35_verify` on
   localhost:5432 via the existing Homebrew Postgres install),
   ran `manage.py migrate --run-syncdb` to load the full schema,
   then executed the M35.0 §4.8 live shell test verbatim against
   Postgres. Result: **POSTGRES_COMPILED_OK + POSTGRES_EXECUTED_OK**
   (SQL length 1620 chars — identical to SQLite). The nested-
   annotation OuterRef pattern (correlating on `OuterRef("latest_deal_structure_id")`
   where `latest_deal_structure_id` is itself a Subquery
   annotation from M33.1 D1) works on both database backends.
   R11 fallback (rewrite D2 without depending on D1 annotation)
   NOT needed. Temp DB dropped at close.
2. **D1 preserved + D2 NEW annotation** in
   `backend/dealer_ai/services/f_and_i/credit_application.py`.
   The M33.1 D1 `has_deal_structure` + `latest_deal_structure_id`
   annotations preserved verbatim. NEW D2
   `latest_lender_submission_status = Subquery(LenderSubmission.objects.filter(dealership=dealership, deal_structure_id=OuterRef("latest_deal_structure_id")).order_by("-submitted_at", "-created_at", "-pk").values("status")[:1])`.
   Docstring extended with M35.1 annotation contract paragraph
   documenting the six derived states, the correlation-on-
   annotation pattern, the deterministic ordering rationale, and
   the tenant-scope belt.
3. **D3 projection extension** in
   `backend/dealer_ai/views_f_and_i.py` — extended
   `_project_credit_application_with_writeup(app)` with
   `latest_lender_submission_status` field. Docstring extended
   to document all three M32.1 + M33.1 + M35.1 projection fields.
4. **D4 NEW endpoint** — `GET /admin/lender-programs/list/` in
   `views_f_and_i.py` + URL route in `urls.py` named
   `admin-lender-program-list`. Narrow `{id, name}` projection
   via new `_project_lender_program_selector` helper (docstring
   documents why contact / terms_summary / is_active are
   intentionally NOT exposed — audit-trail data not needed for
   FK discovery; extra exposure would falsely broaden the Lender
   Fit Recommendations blocker scope). Reuses shipped
   `list_active_lender_programs` service verb; `_M101_PERMS`;
   zero-drift streak preserved (38 → 39 at M35.1 close).
5. **Regression tests** across two new files:
   - `test_m351_lender_program_list.py` (12 tests) — permission
     matrix (7 tests: unauthenticated + no membership + advisor +
     sales_manager + porter + f_and_i_manager + dealer_owner) +
     behavior (5 tests: empty tenant, N-programs name-ordering,
     inactive-excluded, narrow projection shape, cross-tenant
     exclusion).
   - `test_m351_lender_submission_status_annotation.py` (12
     tests) — 8-case R11 annotation matrix + 4-case projection
     extension coverage (incoming null, in-progress null,
     submitted pending, approved).

**Backend baseline: 5,021 → 5,045 pass, 1 skipped, 0 fail
(180.679s).** +24 tests. Zero regressions.

**Audit at M35.1 close: 163 / 131 / 32 / 321** — exact match to
M35.1 §5.e projection. +1 endpoint (`admin/lender-programs/list/`
at row #94); +1 backend-only (from 31 → 32); covered unchanged
(131); service verbs unchanged (321 — new endpoint reuses
shipped `list_active_lender_programs` verb). (cc) discipline re-
applied: projection locked from direct artifact inspection at
M35.0 planning; observed at M35.1 close matches verbatim.

**One §0.a M35.1 amendment applied** — the initial `urls.py`
route placement embedded the M35.1 D4 comment INSIDE the
`path(...)` call, which caused the audit script's `_PATH_CALL_RE`
regex to skip the endpoint. Discovered when the first audit
regeneration returned 162/131/31/321 (unchanged from M34.2 close)
instead of the expected 163/131/32/321. Corrected in the same
session by moving the comment above the `path(...)` line;
audit re-run returned the expected values. Recorded as (cc)
sixth invocation and additionally as a candidate durable lesson:
**per-endpoint comments must sit above `path(...)`, not inside
its argument list**, to preserve audit-artifact accuracy per (u)
audit-correctness-as-supporting-infrastructure.

**DoD exception path invocation #12** — M35.1 is backend-only
per §5.e; the new list endpoint + queryset annotations +
projection extension have zero operator-visible behavior. M35.2
will satisfy DoD directly via the new
`fandi_submission_response_loop.spec.ts` Playwright journey.
Pattern established at eleven prior invocations (M26 + M27.1 +
M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1 + M34.2 +
M35.1).

## 1. Verification results at open

- **git status:** clean; `HEAD == origin/main + 2` (M35.0
  planning commit + hash-backfill).
- **git log --oneline -5:** shows the expected M35.0 commit
  sequence (M35.0 hash-backfill `50755f3`; M35.0 planning
  `f17e1eb`; M34.2 hash-backfill `c76e6db`; M34 close-out
  `fda9d56`; M34.1 hash-backfill `09d1299`).
- **`python3 manage.py test dealer_ai`:** 5,021 pass, 1
  skipped, 0 fail (180.706s at open).
- **`cd frontend && npm test`:** 402 pass across 45 files
  (7.04s).
- **`python3 manage.py check`:** clean (4 benign DecimalField
  warnings — pre-existing, unchanged).
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`cd frontend && npx tsc --noEmit`:** clean (no output).
- **`cd acceptance && npx tsc --noEmit`:** clean (no output).
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed per
  SESSION_200 §0.a durable lesson (v).

All matches M34.2 close baseline exactly.

## 2. §0.a first item — Postgres OuterRef re-verification (R11)

**Result: PASSED. R11 fallback NOT needed.**

Environment setup:

- Existing Homebrew Postgres 15.13 already running on
  localhost:5432 (owner: `donkeyking`, trust auth for local
  connections). Verified via `lsof -i :5432` + `psql -c "SELECT
  version();"`.
- Created ephemeral DB `dealer_ai_m35_verify` via
  `CREATE DATABASE`; migrated with
  `POSTGRES_DB=dealer_ai_m35_verify POSTGRES_USER=donkeyking
  POSTGRES_PASSWORD= POSTGRES_HOST=localhost POSTGRES_PORT=5432
  python3 manage.py migrate --run-syncdb`; migrations completed
  through the M32.1 CA-writeup FK migration + all Celery Beat
  tables.

Verification query (verbatim from M35.0 §4.8 SQLite live-test):

```python
from django.db.models import Exists, OuterRef, Subquery
from dealer_ai.models import CreditApplication, DealStructure, LenderSubmission, Dealership

d, _ = Dealership.objects.get_or_create(name='M35 Verify')

tenant_structures = DealStructure.objects.filter(
    credit_application_id=OuterRef('pk'),
    dealership=d,
).order_by('-created_at', '-pk')

qs = CreditApplication.objects.filter(dealership=d).annotate(
    latest_deal_structure_id=Subquery(tenant_structures.values('pk')[:1]),
)

tenant_subs = LenderSubmission.objects.filter(
    deal_structure_id=OuterRef('latest_deal_structure_id'),
    dealership=d,
).order_by('-submitted_at', '-created_at', '-pk')

qs = qs.annotate(
    latest_lender_submission_status=Subquery(tenant_subs.values('status')[:1]),
)

sql, params = qs.query.sql_with_params()  # POSTGRES_COMPILED_OK
rows = list(qs.values('pk', 'latest_deal_structure_id', 'latest_lender_submission_status'))  # POSTGRES_EXECUTED_OK; ROWS=0
```

**Results:**

- `POSTGRES_COMPILED_OK`
- `SQL_LENGTH: 1620` — byte-identical to SQLite compilation
  length; Django generates the same ANSI-standard correlated
  subquery for both backends.
- `POSTGRES_EXECUTED_OK; ROWS=0` — empty result set as expected
  (no fixture data beyond the seed Dealership).

Cleanup: `DROP DATABASE dealer_ai_m35_verify;` + removed
`/tmp/pg-m35-verify.log`.

**R11 conclusion:** the nested-annotation OuterRef pattern works
on both SQLite and Postgres. Fallback (rewrite D2 without
depending on D1 annotation via `NOT EXISTS(newer DealStructure)`
guard) is preserved in the M35.0 planning memo §5.c R11 as
documentation but NOT needed for M35.1 shipping.

## 3. What shipped (details)

### 3.1 D1 preserved + D2 NEW annotation

`services/f_and_i/credit_application.py`:

- Added `LenderSubmission` to the `from ...models import (...)`
  block.
- Added a `tenant_latest_submissions` querying block just above
  the existing `tenant_deal_structures` querying block in
  `list_credit_applications`.
- Added `latest_lender_submission_status=Subquery(tenant_latest_submissions.values("status")[:1])`
  to the `.annotate(...)` chain.
- Extended the docstring with a full "M35.1 extension" paragraph
  documenting the D2 annotation semantics, correlation pattern,
  deterministic ordering, and tenant-scope belt.

### 3.2 D3 projection extension

`views_f_and_i.py`:

- Extended `_project_credit_application_with_writeup(app)` to
  set `base["latest_lender_submission_status"] = app.latest_lender_submission_status`.
- Extended the docstring with the M35.1 field documentation
  (nullable string; one of pending/approved/counter/declined;
  null when latest DS has no submissions OR CA has no DS).

### 3.3 D4 NEW endpoint

`views_f_and_i.py`:

- Added `_project_lender_program_selector(program)` narrow
  projection helper.
- Added `admin_lender_program_list(request)` view function
  wrapping `f_and_i_service.list_active_lender_programs(dealership=dealership)`.

`urls.py`:

- Added `path("admin/lender-programs/list/", views_f_and_i.admin_lender_program_list, name="admin-lender-program-list")`.
- Comment placement corrected during §0.a amendment (comment
  moved above `path(...)` line to preserve audit-script
  `_PATH_CALL_RE` regex compatibility).

### 3.4 Regression tests

**`test_m351_lender_program_list.py`** (12 tests):

- `LenderProgramListEndpointAuthTests`: unauthenticated /
  no-membership / advisor / sales_manager / porter →
  401-or-403; f_and_i_manager / dealer_owner → 200.
- `LenderProgramListEndpointBehaviorTests`: empty tenant
  returns `{"lender_programs": []}` (200, not 404); N-programs
  returned in name-ascending order (matches Meta.ordering);
  inactive programs excluded; narrow projection shape asserts
  `set(row.keys()) == {"id", "name"}` verbatim; cross-tenant
  programs excluded.

**`test_m351_lender_submission_status_annotation.py`** (12 tests):

- `LenderSubmissionStatusAnnotationTests` (8 cases per R11):
  1. No DealStructure → None
  2. DealStructure + no submissions → None
  3. One pending submission → "pending"
  4. Multiple submissions latest wins (approved)
  5. Shared submitted_at tie-breaks on created_at DESC
  6. Shared submitted_at + created_at tie-breaks on pk DESC
  7. Older DS approved but latest DS unsubmitted → None
     (CRITICAL current-iteration semantic proof)
  8. Cross-tenant submission via direct ORM bypass → None
- `CreditApplicationListProjectionM35Tests` (4 cases): projection
  carries the new field null for incoming/in-progress; pending
  for submitted; approved for approved.

## 4. Baselines at M35.1 close

- **Backend:** 5,021 → **5,045 pass**, 1 skipped, 0 fail
  (180.679s). +24 tests. Zero regressions.
- **Frontend Vitest:** 402 pass across 45 files (unchanged —
  M35.1 is backend-only).
- **Acceptance:** 25 spec files / 32 tests (unchanged — M35.1
  is backend-only).
- **Migrations:** 0001–0051 (unchanged; no new migration).
- **Audit:** **163 / 131 / 32 / 321** — exact M35.1 projection
  match.
- **DRF admin surface:** 122 → **123** endpoints.
- **Frontend operator routes:** 21 (unchanged).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** 321 verbs (unchanged — new list endpoint
  reuses shipped `list_active_lender_programs`).
- **Permission classes:** 7 actual, zero-drift streak
  **38 → 39 consecutive** (M10 → M35.1; new endpoint reuses
  `_M101_PERMS`).
- **Django check + makemigrations --check:** clean.

## 5. §0.a M35.1 amendments applied

**One §0.a amendment applied at M35.1:**

- **Comment-inside-path() audit-regex incompatibility.** The
  initial `urls.py` route placement embedded the M35.1 D4
  comment INSIDE the `path(...)` argument list. The audit
  script's `_PATH_CALL_RE` regex (backend/dealer_ai/scripts/audit_operational_surface.py:236)
  uses `\s*` between `path(` and the string arg — this matches
  whitespace including newlines but NOT `#` comment content.
  The endpoint was NOT extracted by the audit script; first
  audit regeneration returned 162/131/31/321 (unchanged from
  M34.2) instead of expected 163/131/32/321.
- **Fix:** moved the D4 comment above the `path(...)` line;
  re-ran audit; returned expected 163/131/32/321.
- **Lesson recorded:** per-endpoint comments must sit above
  `path(...)`, not inside its argument list. Reinforces (u)
  audit-correctness-as-supporting-infrastructure (M12.0-era
  origin). Convention preserves streak on target-selection
  basis per M33.1 precedent.

No other §0.a amendments. Zero-drift permission class preserved
by reusing `_M101_PERMS`. Postgres OuterRef verification passed
(no R11 fallback needed).

## 6. DoD compliance

**Exception path invocation #12** (M26 + M27.1 + M28.1 + M29.1
+ M30.1 + M31.1 + M32.1 + M33.1 + M34.1 + M34.2 + **M35.1**).

§3 documents rationale: M35.1 shipped a new list endpoint +
queryset annotations + projection extension. None of these
change operator-visible behavior — the endpoint is FK-discovery
substrate with no frontend consumer yet; the annotations power
a projection field with no frontend consumer yet. M35.2 will
satisfy DoD directly via
`fandi_submission_response_loop.spec.ts`.

Pattern firmly established at twelve invocations. Convention
preserves the exception path's legitimacy for backend-substrate
increments that unlock customer-facing UI in the immediately
following increment.

## 7. Streaks at M35.1 close

- **Planning-time as-recommended streak:** 13 → **14**
  (M35.0 target selected as recommended; ten user-directed
  corrections applied at planning-open but these strengthened
  the locked design rather than changing target selection —
  convention preserves streak on target-selection basis).
  Historical run of 89 across M10 → M23 preserved.
- **Zero-drift permission-class streak:** **38 → 39**
  consecutive milestones (M10 → M35.1). New list endpoint
  reused `_M101_PERMS` unchanged.
- **Substrate-compound-value continuation:** M32 + M33 = 2
  links; M34 = deferral-close (intentional pause); **M35.1 =
  restart at 3 links** (M32 + M33 + M35 F&I depth-arc
  continuation).
- **DoD exception path invocations:** 11 → **12** (M35.1).
  M35.2 satisfies DoD directly.
- **First activation of M10.3 substrate operationally begun** —
  109 sessions after M10.3 shipped at SESSION_108 (surpassing
  M33's 19-session gap on M10.2 DealStructure — new longest-
  substrate-to-UI-gap record; the D4 discovery endpoint is the
  first M10.3 surface with a consumer path; M35.2 completes the
  activation).
- **Verification-driven revision cycles (z — load-bearing-
  across-two-milestones at M33 close; extended at M34.0 to
  include "the tracing at open should be thorough enough that
  revisions are minimized as an outcome"):** fourth invocation
  at M35.0 with 10 corrections — first invocation with
  substantial revision rounds. Continues to demonstrate value.
- **Coverage-projection truthfulness (cc — load-bearing-across-
  three-milestones after M34.2):** **sixth invocation at M35.1**
  (M33.1 origin + M34.1 + M34.2 + M35.0 planning + M35.1 §0.a
  urls.py comment-placement amendment). (cc) now covers three
  distinct sub-classes: (a) test-based vs frontend-consumer
  coverage classification (M33.1); (b) tool/proof-mechanism
  claims about testing behavior (M34.1/M34.2); (c) direct-
  artifact-inspection precedence over inference at planning
  (M35.0); (d) syntactic constraints on audit-script parsing
  (M35.1 new sub-class).
- **Candidate durable lesson (ff) — Playwright rerun-hygiene
  contract:** awaits M35.2 first re-application (Submission
  Sasha seed idempotent from first shipping day +
  `@rerun-hygiene` tag + back-to-back double-run proof
  mechanism). On re-application (ff) elevates to load-bearing-
  across-two-milestones.
- **Audit-comment-placement discipline (candidate lesson):**
  per-endpoint comments must sit above `path(...)`, not inside
  its argument list. Preserves audit-artifact accuracy per (u).
  First observation at M35.1 §0.a amendment. May elevate on
  re-observation.

## 8. Push status

**No push at SESSION_217 close.** M35.1 lands in a single local-
only commit per the standard M28.1 / M29.1 / M30.1 / M31.1 /
M32.1 / M33.1 / M34.1 cadence. Coordinated M35 close push
deferred to explicit user confirmation after M35.2 close.

Local commits at SESSION_217 close:

- SESSION_217 backend substrate + regression tests + audit
  artifact regeneration + this handoff + `00-START-NEXT-SESSION.md`
  flip land in a single local-only commit; hash backfill via a
  subsequent commit per convention.

Expected M35 commit count at coordinated push: **6** (M35.0
planning `f17e1eb`; M35.0 hash-backfill `50755f3`; M35.1
backend + tests + audit (this session); M35.1 hash-backfill
(follow-up); M35.2 frontend + Playwright (SESSION_218); M35.2
hash-backfill (SESSION_218 follow-up)) — plus optional close-
out fold commit at M35 shipped close.

## 9. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_218 ·
Milestone 35 · Increment 2 (M35.2 — frontend API-client +
components + chip extension + Playwright journey + Submission
Sasha seed)**. First-thing sequence per M28.2 / M29.2 / M30.2 /
M31.2 / M32.3 / M33.2 pattern:

1. **Verify starting state** (git status; backend tests 5,045
   pass; frontend Vitest 402 pass; checks; migrations; tsc;
   redis; `db.acceptance.sqlite3` proactive reset).
2. **Confirm working from M35.0 planning memo** — read
   `docs/roadmap/MILESTONE_35_PLANNING.md` §5.b D5 + D6 + D7 +
   D8 + D9 + D10 + D11 + §5.e M35.2 before touching any file.
3. **Ship M35.2 frontend + Playwright** per §5.e:
   - **D5 API-client extensions** in `frontend/src/lib/fAndIApi.ts`:
     types (5 new: `CreditApplicationProjection` extension +
     `LenderProgramSelectorProjection` + `LenderSubmissionProjection`
     + `RecordLenderSubmissionRequest` + `UpdateLenderSubmissionStatusRequest`);
     three typed wrappers (`listLenderPrograms`,
     `recordLenderSubmission`, `updateLenderSubmissionStatus`).
     NO `getLenderSubmission` (no shipped GET endpoint per
     M35.0 §4.8). NO `submitted_at` on RecordLenderSubmissionRequest
     (server records per D6). NO `status` override on create.
   - **D6 NEW component** `frontend/src/components/f-and-i/LenderSubmissionRecordForm.tsx`:
     LenderProgram select (populated from listLenderPrograms
     on mount) + optional notes textarea. Submit disabled until
     LenderProgram selected. Header "Record lender submission";
     button "Record submission". PROHIBITED strings
     ("Send to lender", "Send", "Submit to lender", "Transmit",
     "Contact lender", "Submitting…") MUST NOT appear anywhere.
   - **D7 NEW component** `LenderSubmissionResponseForm.tsx`:
     status radio (approved/counter/declined — pending excluded);
     optional notes. Header/button language mode-conditional:
     pending → "Record lender response" / "Record response";
     terminal → "Update lender response" / "Update response".
     NO counter_terms/approval_terms fields.
   - **D8 chip + row-action extension** in `DealerFandIIncoming.tsx`:
     6 chip states (Incoming/In progress preserved from M33;
     Submitted/Approved/Counter/Declined NEW) with three-signal
     a11y (testid + aria-label + visible label); state-
     conditional row actions per D8 table; first-loop boundary
     comments in code.
   - **D9 NEW Playwright spec** at
     `acceptance/journeys/f_and_i_manager/fandi_submission_response_loop.spec.ts`
     tagged `@rerun-hygiene` with 6 truthfulness assertions
     per D9 spec.
   - **D10 NEW idempotent seed** at
     `backend/dealer_ai/management/commands/seed_journey_fandi_submission_response.py`
     provisioning Submission Sasha fixture with 3 rerun
     invariants. Extend `login.setup.ts` SEED_COMMANDS list.
   - **D11 four-layer defense** on financial-language contract:
     spec + Vitest anti-drift regex + Playwright regex +
     Vitest string-absence test on both component files.
4. **Verify M35.2 close baselines:** backend suite 5,045 pass
   (unchanged — M35.2 adds no backend code); frontend Vitest
   402 → ~430 pass; acceptance 25 → 26 spec files / 32 → 33
   tests; audit artifact **163 / 134 / 29 / 321** (three
   lender endpoints move backend-only → covered).
5. **M35.2 proof mechanism at close** per D9 + M34.2 §0.a
   correction: back-to-back `npx playwright test --grep
   "@rerun-hygiene"` executions (4 tags total after M35.2:
   M34's 3 + M35's 1). BOTH runs must pass. Record timings in
   M35.2 handoff §7. **NOT `--repeat-each=2`.**
6. **DoD satisfied directly** via
   `fandi_submission_response_loop.spec.ts`. Document in §3 of
   M35.2 handoff.
7. **Ship the M35.2 handoff at
   `docs/handoffs/SESSION_218_m35_inc2_frontend.md`.** **Do NOT
   push** — coordinated push at M35 close.

## 10. Non-goals for SESSION_218

- ❌ Do NOT ship backend code — M35.1 is complete; M35.2 is
  frontend + Playwright + seed only.
- ❌ Do NOT add a GET single-record LenderSubmission endpoint —
  §5.h explicit deferral (PATCH response body suffices).
- ❌ Do NOT add `contact` / `terms_summary` / `is_active` to
  the D4 projection (narrow `{id, name}` locked at M35.1).
- ❌ Do NOT ship LenderProgram create UI.
- ❌ Do NOT ship structured `counter_terms` / `approval_terms`
  capture (free-form JSONField stays server-side only).
- ❌ Do NOT add `submitted_at` operator-editable field to D6.
- ❌ Do NOT surface second-submission-on-same-DS UX (first-loop-
  only preserved).
- ❌ Do NOT expand into alternate-lender / submission-history /
  multi-submission management (all §5.h deferred).
- ❌ Do NOT use `--repeat-each=2` as the rerun-hygiene proof
  mechanism (M34.2 §0.a correction; back-to-back `--grep`
  invocations only).
- ❌ Do NOT modify M32.3 Intake Iris or M33.2 Structure Sam
  fixtures (Submission Sasha is fully additive).
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M35.1 shipped surface.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_35_PLANNING.md`** (governing
   contract for M35)
6. `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §9 (M35
   candidate list + F&I depth-arc standing question)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (regenerated
   at M35.1 close: 163 / 131 / 32 / 321)
8. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D1 + D3
   (preserved at M35.1 D1)
9. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.3 (M10.3
   LenderProgram + LenderSubmission substrate contract)
10. `docs/CAPABILITY_MATRIX.md` §7ι (M34 shipped surface);
    §7κ added at M35 close
11. `docs/handoffs/SESSION_216_m35_inc0_planning.md` (M35.0
    shipped)
12. **This handoff** (`SESSION_217_m35_inc1_backend.md`)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md` (M27.0
    origin — resolved via M35.1 D4)
14. Memory record
    `feedback_playwright_as_operational_contract.md` (M35.2
    will re-apply the rerun-hygiene contract from M34.2)
