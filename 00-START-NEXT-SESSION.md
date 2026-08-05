---
state: active
date: 2026-08-05
last_session_shipped: SESSION_216
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
next_session: SESSION_217
next_milestone: 35
next_milestone_name: "Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
next_increment: 1
next_increment_name: "M35.1 — Backend FK-discovery endpoint + subquery annotations + projection extension + Django regression tests"
---

# Next session — SESSION_217 · Milestone 35 · Increment 1 (M35.1 — backend FK-discovery endpoint + subquery annotations + projection extension + Django regression tests)

> **Milestone 35 — Lender Submission Activation — OPENED at
> SESSION_216 M35.0.** Third link of the M32 → M33 F&I depth arc.
> Anchor question: **Can an F&I manager record where a structured
> deal was submitted, capture the lender's response, and see the
> resulting operational state without leaving Dealer OS?**
>
> **§5.a target locked at open** as **Lender Submission
> Activation** after evaluating three natural continuation modes
> per the M34 §9 standing question (continue F&I depth arc / reset
> to breadth / close another §3 deferral). F&I depth-arc continuation
> selected. All §5.b–§5.h decisions locked (D1–D11; risk register
> R1–R11; verifications §4.1–§4.8; two-increment phasing; DoD
> compliance; rollback; ~20 explicit non-goals plus all prior
> deferrals unchanged).
>
> **One blocking finding resolved architecturally at §4.8** — NO
> list endpoint exists for LenderProgram (`list_active_lender_programs`
> service verb shipped since M10.3 but has no HTTP surface).
> Resolved via D4 (new thin `GET /admin/lender-programs/list/`
> endpoint at M35.1). **Two non-blocking scope corrections
> applied** — `getLenderSubmission(id)` wrapper removed (no shipped
> GET endpoint; use PATCH response body + list refetch); `submitted_at`
> operator-editable field omitted (server records; no operational
> back-entry evidence).
>
> **Ten planning-open corrections applied before §5.b lock** —
> z lesson (verification-driven revision cycles at planning-open)
> on invocation 4 with substantial revision rounds. Discipline
> continues to demonstrate value at planning-open when tracing
> surfaces gaps that would otherwise ship as bugs. Historical run
> of 89 across M10 → M23 preserved.
>
> **Nested-annotation OuterRef pattern verified working on SQLite
> live** at §4.8 (COMPILED_OK + EXECUTED_OK). Postgres re-
> verification is the first §0.a checklist item at M35.1 open per
> R11 mitigation. Fallback documented (rewrite D2 without
> depending on D1 annotation) if Postgres compilation fails.
>
> **Financial-language contract refined per user directive #10.**
> Locked verbatim at D11: *"Before a verified LenderSubmission
> response exists, UI language may describe only operator-recorded
> submission activity and proposed structure values. After
> `status="approved"` is recorded, Dealer OS may describe the
> submission or deal workflow state as approved, but may not
> describe individual structure values as lender-approved terms
> unless verified approval-term data is captured and displayed."*
> Four-layer defense (spec + Vitest anti-drift regex + Playwright
> regex + Vitest string-absence test on both component files).
>
> **Two-increment shape** — backend / frontend boundary matching
> M33 shape. M35.1 ships FK-discovery endpoint + two subquery
> annotations + projection extension + Django regression tests
> (+20 tests). M35.2 ships API-client + two new components +
> chip extension + Playwright journey (`@rerun-hygiene` tag +
> back-to-back double-run proof) + Submission Sasha seed. Rollback
> fully independent in reverse ship order.
>
> **SESSION_217 opens M35.1 — backend FK-discovery endpoint +
> subquery annotations + projection extension.** DoD exception path
> invocation #12. The FIRST item after starting-state verification
> is **Postgres OuterRef re-verification** per R11 mitigation —
> before ANY implementation work, prove the D2 nested-annotation
> pattern compiles + executes on Postgres. If it fails, apply the
> documented R11 fallback as §0.a M35.1 amendment before proceeding.

## First thing SESSION_217 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  post-M34 push OR local `HEAD` ahead by 2 commits (SESSION_216
  planning + hash-backfill) if M35.0 planning commit has landed
  and CI hasn't picked it up yet.
- `git log --oneline -10` — top should be the M35.0 hash-
  backfill commit if applied, else the M35.0 planning commit,
  else the M34.2 hash-backfill; verify expected sequence.
- `python3 manage.py test dealer_ai` → **5,021 pass, 1 skipped,
  0 fail** (unchanged from M34.2 close).
- `cd frontend && npm test` → **402 pass** across 45 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. §0.a FIRST ITEM — Postgres OuterRef re-verification (R11 mitigation)

**Before ANY implementation work at M35.1, verify the D2 nested-
annotation OuterRef pattern compiles + executes on Postgres.**

Spin up a Postgres-configured environment (either set `POSTGRES_DB`
env from an existing local Postgres OR spin up ephemeral via
`docker run --rm -d --name m35-pg-verify -p 5432:5432 -e POSTGRES_PASSWORD=verify -e POSTGRES_DB=dealer_ai_verify -e POSTGRES_USER=verify postgres:16`).

Run the M35.0 §4.8 live shell test verbatim against Postgres:

```python
from django.db.models import Exists, OuterRef, Subquery
from dealer_ai.models import CreditApplication, DealStructure, LenderSubmission, Dealership

d = Dealership.objects.first()
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

sql, params = qs.query.sql_with_params()  # expect COMPILED_OK
rows = list(qs.values('pk', 'latest_deal_structure_id', 'latest_lender_submission_status'))  # expect EXECUTED_OK
```

**If Postgres compilation OR execution fails**, apply the R11
fallback (rewrite D2 without depending on D1 annotation — use
`NOT EXISTS(newer DealStructure)` guard inside the LenderSubmission
subquery filter) as §0.a M35.1 amendment before proceeding to D4.

**If green:** log the result in the M35.1 handoff §2 as evidence
and proceed to §3.

### 3. Confirm working from M35.0 planning memo

Read `docs/roadmap/MILESTONE_35_PLANNING.md` §5.b D1 + D2 + D3 +
D4 + §5.e M35.1 + §5.c R11 before touching any file. Verify no
scope drift from what was locked at M35.0.

### 4. Ship M35.1 backend substrate

Per §5.e M35.1:

- Extend `services/f_and_i/credit_application.py`:
  - D1 annotation preserved verbatim (already shipped at M33.1).
  - NEW D2 annotation:
    `latest_lender_submission_status = Subquery(LenderSubmission.objects.filter(deal_structure_id=OuterRef("latest_deal_structure_id"), dealership=dealership).order_by("-submitted_at", "-created_at", "-pk").values("status")[:1])`.
  - Docstring extended with M35.1 annotation contract.
- Extend `views_f_and_i.py`:
  - D3: extend `_project_credit_application_with_writeup(app)`
    with `latest_lender_submission_status` field.
  - NEW view function `admin_lender_program_list(request)` —
    thin wrapper on shipped `list_active_lender_programs`
    service verb; narrow `{id, name}` projection; `_M101_PERMS`.
- Extend `urls.py`:
  - NEW path `admin/lender-programs/list/` named
    `admin-lender-program-list`.
- Create `backend/dealer_ai/tests/test_m351_lender_program_list.py`:
  - Endpoint permission matrix (5 negative + 2 positive per
    M33.1 pattern).
  - Narrow projection shape (`{id, name}` only; no
    contact/terms/is_active fields).
  - Active-only filter (inactive programs excluded).
  - Empty-tenant + N-programs cases.
- Create `backend/dealer_ai/tests/test_m351_lender_submission_status_annotation.py`:
  - 8-case regression matrix per R11:
    1. No DealStructure → status = null
    2. DealStructure with no submissions → status = null
    3. One submission (pending) → status = "pending"
    4. Multiple submissions (latest = approved) → status = "approved"
    5. Shared `submitted_at` across submissions → tie-break on
       `created_at` DESC
    6. Shared `submitted_at` + `created_at` → tie-break on `pk` DESC
    7. Multiple DealStructures where older has approved
       submission but latest has none → status = null (proves
       current-iteration semantic)
    8. Cross-tenant rows via direct ORM bypass → excluded
       (belt-and-suspenders)
- Optionally extend `test_m331_deal_structure_read.py` OR add
  `test_m351_credit_application_projection.py` for CA list
  projection extension coverage.
- **Historical migrations NOT modified.**
- **No new service verb.**
- **No new permission class.**
- **No migration; no schema change.**

### 5. Verify M35.1 close baselines

- Backend suite: 5,021 → ~5,041 pass (projected +20 tests;
  refine at close).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- Frontend `tsc --noEmit` + Vitest unchanged (M35.1 is backend-
  only).
- Acceptance `tsc --noEmit` unchanged.
- Regenerate audit artifact:
  ```bash
  cd backend
  python3 -m dealer_ai.scripts.audit_operational_surface
  ```
  Expected: **163 / 131 / 32 / 321** (+1 endpoint total; +1
  backend-only; covered unchanged; service verbs unchanged).
  If drift, investigate before shipping.

### 6. DoD exception path invocation #12

Document in §3 of M35.1 handoff (FK-discovery endpoint + queryset
annotations + projection extension have zero operator-visible
behavior; M35.2 satisfies DoD directly via the new
`fandi_submission_response_loop` Playwright journey). Pattern
established at eleven prior invocations (M26 + M27.1 + M28.1 +
M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1 + M34.2 + M35.1).

### 7. Ship the M35.1 handoff

- `docs/handoffs/SESSION_217_m35_inc1_backend.md`.
- **Do NOT push** — M35.1 is planning-only in shipping sense;
  coordinated push at M35 close.

## Non-goals for SESSION_217

- ❌ Do NOT ship any frontend code — M35.1 is backend-only per
  §5.e.
- ❌ Do NOT ship any Playwright journey — M35.2 delivers it.
- ❌ Do NOT ship the Submission Sasha seed — M35.2 delivers it.
- ❌ Do NOT ship any component — M35.2 delivers `LenderSubmissionRecordForm`
  + `LenderSubmissionResponseForm` + `DealerFandIIncoming`
  extension.
- ❌ Do NOT add a GET single-record LenderSubmission endpoint —
  §5.h explicit deferral.
- ❌ Do NOT expose `contact` / `terms_summary` / `is_active`
  via the D4 list endpoint — narrow `{id, name}` locked.
- ❌ Do NOT ship LenderProgram create UI — §5.h explicit deferral.
- ❌ Do NOT introduce a stored `workflow_state` column, migration,
  or state machine.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M34 shipped surface.
- ❌ Do NOT skip the Postgres OuterRef re-verification at §0.a
  first item — R11 mitigation is a hard gate.
- ❌ Do NOT modify the M33.1 D1 annotation (preserved verbatim
  at M35.1 D1).
- ❌ Do NOT modify historical migrations (aa preservation).
- ❌ Do NOT modify M32.3 / M33.2 / M34 fixtures or seed contracts.

## Baseline expected at close

- Backend: 5,021 → ~5,041 pass, 1 skipped, 0 fail.
- Frontend: 402 pass (unchanged).
- Acceptance: 25 spec files / 32 tests (unchanged).
- Migrations: 0001–0051 (unchanged).
- Audit: **163 / 131 / 32 / 321**.
- DRF admin surface: **123** endpoints (122 → +1 at M35.1).
- Frontend operator routes: **21** (unchanged).
- Frontend components: unchanged at M35.1 (M35.2 adds two new
  in `frontend/src/components/f-and-i/`).
- Service verbs enumerated: **321** (unchanged — new list
  endpoint reuses shipped `list_active_lender_programs` verb).
- Permission classes: **7 actual**, zero-drift streak **38 → 39
  consecutive** (M10 → M35.1; new endpoint reused `_M101_PERMS`).

## NEXT TASK

Start SESSION_217 with (a) starting-state verification; (b)
§0.a first item — Postgres OuterRef re-verification per R11;
(c) confirm working from M35.0 planning memo; (d) ship M35.1
backend substrate per §5.e (D1 preserved + D2 NEW + D3
projection extension + D4 NEW list endpoint + 20 regression
tests); (e) verify baselines (5,041 backend pass; audit
163/131/32/321); (f) document DoD exception path invocation
#12; (g) ship the M35.1 handoff.

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
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` rows
   #93/#94/#95 (source of truth for §5.e audit projections)
8. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.3 (LenderProgram +
   LenderSubmission substrate contract)
9. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D1 + D3 + D5
   (patterns preserved / extended at M35)
10. `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D7 + D10
    (rerun-hygiene contract preserved at M35 D9 + D10)
11. `docs/CAPABILITY_MATRIX.md` §7ι (M34 shipped surface)
12. `docs/handoffs/SESSION_216_m35_inc0_planning.md` (M35.0
    shipped)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md` (M27.0
    origin — applied at §4.8 for LenderProgram FK discovery;
    resolved via D4)
14. Memory record
    `feedback_playwright_as_operational_contract.md` (M34
    preserves the contract; M35 extends coverage)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_216 — Milestone 35 OPENED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged). Test baseline: **5,021 pass**, 1
  skipped, 0 fail (unchanged from M34.2 close).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 402 pass** across 45
  test files (unchanged).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS 5.6
  operational; **25 journeys** total (unchanged M35.0).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `c76e6db` (M34.2 hash-backfill commit):
  **success in 3m1s** at 2026-08-05T14:25:46Z. M34 CI-verified
  shipped.
- **Async runtime:** unchanged.
- **Milestones shipped:** M1 → M34. **M35 OPENED (M35.0
  planning).** Target selection locked; M35.1 backend substrate
  is next.
- **DRF admin surface:** **122** endpoints (unchanged at M35.0;
  +1 projected at M35.1 close).
- **Frontend operator routes:** **21** (unchanged; +0 projected
  at M35 — extends existing F&I intake page in place).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged; M35 adds no
  new service verbs — D4 reuses `list_active_lender_programs`).
- **Frontend surfaces:** unchanged at M35.0; +2 new components
  projected at M35.2 (`LenderSubmissionRecordForm`,
  `LenderSubmissionResponseForm`).
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-eight consecutive milestones** (M10 → M34). M35
  projected to preserve at 39 consecutive.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 35 status:** OPEN — M35.0 planning shipped;
  M35.1 backend substrate is next; M35.2 frontend +
  Playwright follows.
- **Audit tooling status:** unchanged from M26.1. Coverage
  **131 / 162** (unchanged at M35.0 — planning only). M35.1
  projected close: **131 / 163**; M35.2 projected close: **134
  / 163**.
- **Playwright personas:** **6 actual** (unchanged; M35.2
  reuses `f_and_i_manager`).
- **Playwright fixtures:** unchanged at M35.0 — Intake Iris
  (M32.3) + Structure Sam (M33.2) both live and independent;
  **Submission Sasha** to be added at M35.2 per D10.
- **§9 evidence for M35 (locked at M35.0):** the M35 candidate
  is **Lender Submission Activation**. All other §9 items
  from M34 §9 preserved unchanged as M36+ candidates:
  NEW C (still pilot-gated), Lender Fit (three of four
  blockers remain — M35 delivers NONE of the fourth blocker
  intentionally), NEW F&I workflow-state extensions beyond
  M35's four new derived states, NEW F&I-scoped lead-context
  view, cross-lead pending-approval queue, direct-create CA
  structuring branch, iteration UX, PATCH on DealStructure,
  NEW O2, NEW O3, gated T/U/L/M, deferred D, deferred stable G.
- **Planning-time streak: 13** (at M34.2 close; projected 14
  at M35 close assuming no §0.a amendments; M35.0 applied 10
  user-directed corrections but these strengthened the locked
  design rather than changing the target selection —
  convention preserves streak on target-selection basis).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least one
  Playwright operational journey, or explicitly document in §3
  why no journey change is required. Projected M35.1
  invocation #12 (backend-only per M27.1 / M28.1 / etc.
  pattern); M35.2 satisfies DoD directly via
  `fandi_submission_response_loop.spec.ts` new journey.
- **M35 audit coverage projections at close:** M35.1 =
  163/131/32/321; M35.2 = 163/134/29/321. Both locked from
  direct artifact inspection per (cc) discipline.
- **Durable lessons carried into M35+:** all (a)–(ff) preserved
  from M34.2 close. (cc) load-bearing-across-three-milestones
  (extended to five invocations at M35.0). (ff) awaits first
  re-application at M35.2 D9 + D10; on re-application elevates
  to load-bearing-across-two-milestones. (z) verification-
  driven revision cycles fourth invocation at M35.0 — first
  invocation with substantial revision rounds (10 user-directed
  corrections). Discipline continues to demonstrate value.
