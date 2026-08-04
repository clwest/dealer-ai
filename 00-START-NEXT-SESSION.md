---
state: active
date: 2026-08-04
last_session_shipped: SESSION_210
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
milestone_33_status: active
next_session: SESSION_211
next_milestone: 33
next_milestone_name: "F&I Intake Activation: Incoming Application to Active Deal Structure"
next_increment: 1
next_increment_name: "M33.1 — Backend annotation + read endpoint + tests"
---

# Next session — SESSION_211 · Milestone 33 · Increment 1 (M33.1 — backend annotation + read endpoint + tests)

> **Milestone 33.0 — Planning shipped at SESSION_210.** §5.a
> locked as **F&I Intake Activation — Incoming Application
> to Active Deal Structure**, resolving M32 §9 standing
> question with **F&I depth-arc continuation** over breadth
> reset. Substrate-compound-value continuation restarts at
> 2 links (M32 + M33) after the M32 breadth pivot.
>
> **Anchor business question:** *Can an F&I manager take
> an incoming credit application from the M32 queue, begin
> working it through the real product, and create the first
> durable deal-structure record without leaving Dealer OS?*
>
> **All §5.b–§5.h locks shipped at M33.0.** D1–D10; risk
> register R1–R10; nine-verification pass §4.1–§4.9; two-
> increment phasing; DoD exception path invocation #8 at
> M33.1; rollback in reverse ship order; non-goals lock
> the discovery-rule perimeter.
>
> **Four planning-time corrections applied at M33.0 before
> §5.b lock** (per M32 candidate lesson z — verification-
> driven revision cycles):
> 1. **Financial-language contract** — sales targets /
>    proposed structure values only; never lender-approved
>    / lender-committed / actual. D5 + D6 + D7 + D8 + R10
>    lock this; D8 Playwright regex asserts absence.
> 2. **Deterministic latest-structure selection** —
>    `order_by("-created_at", "-pk")` on subquery + explicit
>    `dealership=dealership` filter as belt over model
>    `clean()` + service `CrossTenantDealStructureError`
>    suspenders. Locked in D3.
> 3. **Canonical endpoint path** —
>    `GET /admin/deal-structures/<int:pk>/` enforced
>    verbatim across memo, handoff, frontend wrapper,
>    tests, and Playwright expectations. Locked in D2.
> 4. **Strengthened truthful-entry validation** — 0 valid
>    only as explicit operator entry; blank never converts
>    silently to 0; explicit values required for
>    `amount_financed` / `taxes` / `fees`; `trade_payoff`
>    requires "No trade payoff" checkbox affordance; basic
>    consistency-warning surface (not full desking math)
>    flags obviously contradictory entries. Locked in D5
>    with R2 three-layer defense.
>
> **M33.1 (this session) — backend-only substrate.** DoD
> exception path invocation #8 (M32.1 was #7). Adds two
> subquery annotations (`has_deal_structure` + `latest_deal_structure_id`)
> to the M32.1 `list_credit_applications` queryset + the
> `_project_credit_application_with_writeup` projection, one
> new read endpoint (`GET /admin/deal-structures/<int:pk>/`)
> with permission gate + tests, and ~15 new tests. **No
> migration; no schema change; no service verb signature
> changes.** Backend baseline 4,995 → ~5,010. Audit
> 161/129/32/321 → 162/130/31/322.
>
> **M33.2 (next session, SESSION_212) — frontend UI + Playwright.**
> Satisfies DoD directly. Derived-status chip; "Start
> structuring" action with truthful-entry form; "Open
> structure" read view; new `f_and_i_manager` Playwright
> journey covering the full first-loop; new
> `seed_journey_fandi_intake_activation` idempotent seed
> command provisioning dedicated `Structure Sam` fixture
> (per M32 D11 precedent). Vitest 377 → ~392; acceptance
> 24/31 → 25/32.
>
> **Zero-drift permission-class streak preserved** — all
> M33 endpoints reuse `_M101_PERMS` unchanged. 36 → 37
> projected at M33.1 close; 37 at M33.2 close (no new
> endpoints).
>
> **Future capability recorded at planning time** — Lender
> Fit Recommendations (structured, auditable eligibility +
> ranked compatibility + missing-information analysis;
> operator explanation always visible; preserved human
> decision authority). NOT implemented in M33. Blocked on
> DealStructure creation operationally complete +
> LenderProgram rule verification + attribute retrieval +
> real dealer evidence.
>
> **SESSION_211 opens M33.1 backend implementation.** All
> planning locks in
> `docs/roadmap/MILESTONE_33_PLANNING.md`; SESSION_210
> handoff at `docs/handoffs/SESSION_210_m33_inc0_planning.md`.

## First thing SESSION_211 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main @ 2a1e359` post-M32 push (M32 already
  CI-verified green at M33.0 open — run `30956621258`,
  success 3m10s at 2026-08-04T22:30:04Z) OR local `HEAD`
  ahead by 1 commit (SESSION_210 planning-only local
  commit awaiting hash-backfill follow-up per convention).
- `git log --oneline -10` — top should be either the
  SESSION_210 planning commit (with hash-backfill pending)
  or the hash-backfill commit + SESSION_210 planning
  commit. Verify M32 commit sequence intact.
- `python3 manage.py test dealer_ai` → **4,995 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **377 pass** across 42
  files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset
  per SESSION_200 §0.a durable lesson (v).

### 2. Confirm working from M33.0 planning memo

Before touching any backend code, read (in order):

- `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D1 + D2 +
  D3 — the three backend decisions M33.1 implements.
- `docs/roadmap/MILESTONE_33_PLANNING.md` §5.e M33.1 —
  the phase contract.
- `docs/roadmap/MILESTONE_33_PLANNING.md` §5.h — non-
  goals (esp. "no PATCH", "no migration", "no schema
  change", "historical migration NOT modified").

### 3. Ship M33.1 backend substrate per §5.e

**A. Queryset annotation extension**
(`backend/dealer_ai/services/f_and_i/credit_application.py`):

Extend `list_credit_applications(...)` with two subquery
annotations. Both explicitly tenant-scoped:

```python
from django.db.models import Exists, OuterRef, Subquery

qs = qs.annotate(
    has_deal_structure=Exists(
        DealStructure.objects.filter(
            dealership=dealership,
            credit_application=OuterRef("pk"),
        )
    ),
    latest_deal_structure_id=Subquery(
        DealStructure.objects
            .filter(
                dealership=dealership,
                credit_application=OuterRef("pk"),
            )
            .order_by("-created_at", "-pk")
            .values("pk")[:1]
    ),
)
```

No new service verb; no signature change; existing filter
composability (`intake` / `lead` / `since`) preserved.

**B. Projection extension** (`backend/dealer_ai/views_f_and_i.py`):

Extend `_project_credit_application_with_writeup(app)` to
include:

```python
"has_deal_structure": app.has_deal_structure,
"latest_deal_structure_id": app.latest_deal_structure_id,
```

**C. New view function** (`backend/dealer_ai/views_f_and_i.py`):

```python
@api_view(["GET"])
@permission_classes(_M101_PERMS)
def admin_deal_structure_read(request, pk):
    """GET: single DealStructure (M33.1 read).

    Tenant-scoped via shipped `get_deal_structure(pk,
    dealership=dealership)` service verb. Reuses shipped
    `_project_deal_structure(deal)` projection. Returns 404
    on unknown or cross-tenant (fail-closed, matches
    M9.1 / M10.1 / M10.2 shape).

    Read-only. No PATCH, no DELETE — activation-vocabulary-
    asymmetry per M31 lesson w.
    """
    dealership = get_current_dealership(request)
    deal = f_and_i_service.get_deal_structure(
        pk, dealership=dealership
    )
    if deal is None:
        return Response(
            {"detail": "Deal structure not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"deal_structure": _project_deal_structure(deal)},
        status=status.HTTP_200_OK,
    )
```

**D. URL pattern** (`backend/dealer_ai/urls.py`) — canonical
path verbatim:

```python
path(
    "admin/deal-structures/<int:pk>/",
    views_f_and_i.admin_deal_structure_read,
    name="admin-deal-structure-read",
),
```

Location: adjacent to the existing
`admin-deal-structure-create` entry
(`urls.py:547`).

**E. Model docstring update** on `DealStructure`
(`backend/dealer_ai/models.py:4742+`) — reference the new
read endpoint. No signature change on `get_deal_structure`
verb.

**F. Tests (target ~15 new):**

- Annotation with 0 structures → `has_deal_structure=False`
  + `latest_deal_structure_id=None`.
- Annotation with 1 structure → both populated.
- Annotation with N=3 structures → `latest_deal_structure_id`
  matches most-recent.
- Deterministic tie-break: create two DealStructures with
  identical `created_at` at microsecond granularity;
  assert subquery selects the higher-`pk` row.
- Annotation tenant-scoped: seed cross-tenant DealStructure
  targeting an own-tenant CA; assert subquery filter
  refuses to project it (`has_deal_structure=False`).
- Projection includes both new fields (Incoming + In
  progress cases).
- Read endpoint 200 for own-tenant existing DealStructure.
- Read endpoint 404 for unknown pk.
- Read endpoint 404 for cross-tenant pk (never leaks
  existence).
- Read endpoint 403 for non-F&I roles (sales_manager,
  recon_manager, advisor, porter, collections).
- Read endpoint projection matches shipped
  `_project_deal_structure` shape verbatim.

**G. Non-goals for M33.1 (per §5.h):**

- ❌ Do NOT introduce migrations.
- ❌ Do NOT modify historical `0026_deal_structure_entity.py`.
- ❌ Do NOT add PATCH or DELETE endpoints.
- ❌ Do NOT add a new service verb (annotations replace
  the need).
- ❌ Do NOT modify `POST /admin/deal-structures/` (M10.2
  shipped surface unchanged).
- ❌ Do NOT extend `_M101_PERMS` or add a new permission
  class.

### 4. Verify M33.1 close baselines

- Backend suite: 4,995 → **≈5,010 pass**, 1 skipped, 0
  fail.
- `python3 manage.py check` clean (7 benign DecimalField
  warnings unchanged).
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean (no frontend
  change).
- `cd acceptance && npx tsc --noEmit` clean (no
  acceptance change).
- Regenerate audit:
  ```bash
  python3 -m dealer_ai.scripts.audit_operational_surface
  ```
  Expected delta: **161 → 162** total; **129 → 130**
  covered; **32 → 31** backend-only; **321 → 322** service
  verbs. Two-source agreement gate.

### 5. DoD compliance check

Per M21.0 §5.f Option B: M33.1 backend-only invokes
exception path #8 (M26 + M27.1 + M28.1 + M29.1 + M30.1 +
M31.1 + M32.1 → M33.1). Document in §3 of M33.1 handoff:
queryset annotation + read endpoint has zero operator-
facing behavior change on its own; M33.2 satisfies DoD
directly via new Playwright journey (D8).

### 6. Ship the M33.1 handoff

`docs/handoffs/SESSION_211_m33_inc1_backend.md`.

**Do NOT push** — coordinated M33 close push deferred to
explicit user confirmation after M33.2 close, following
the M27 → M32 coordinated-close cadence.

## Non-goals for SESSION_211

- ❌ Do NOT ship any frontend code — M33.2 owns the F&I
  UI and Playwright journey.
- ❌ Do NOT open M33.2 in this session.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M32 shipped surface.
- ❌ Do NOT modify the acceptance suite (M33.2 owns the
  Playwright extension).
- ❌ Do NOT skip the DoD compliance check documentation.
- ❌ Do NOT skip the two-source audit agreement gate.
- ❌ Do NOT re-litigate M33.0 architectural verifications
  (M-to-1 iteration preserved; latest-only posture;
  deterministic tie-break; explicit tenant-scope on
  subquery; canonical endpoint path; financial-language
  contract; truthful-entry form contract — all locked at
  M33.0).
- ❌ Do NOT default `taxes` / `fees` / `trade_payoff` /
  `amount_financed` to 0 anywhere in code — the form
  contract lives in M33.2 but the backend serializer
  defaults are shipped M10.2 surface and stay untouched.
- ❌ Do NOT introduce Submitted / Approved / Contracted /
  Funded / Chargedback state derivation — those require
  underlying workflow verification per §3 of the planning
  memo.
- ❌ Do NOT touch LenderSubmission / Stipulation /
  Contract / Funding / Chargeback surfaces.
- ❌ Do NOT implement Lender Fit Recommendations. Recorded
  as future capability per §5.b D10 with named blockers.

## Baseline expected at close

- Backend: **≈5,010 pass**, 1 skipped, 0 fail.
- Frontend Vitest: **377 pass** (unchanged from M32.3).
- Acceptance: **24 spec files / 31 tests** (unchanged from
  M32.3).
- Audit: **162 / 130 / 31 / 322** (delta from M32.3: +1
  endpoint, +1 covered, −1 backend-only, +1 service verb).
- Migrations: **0001–0051** (unchanged since M32.1).
- Permission classes: **7 actual**, zero-drift streak
  **37 consecutive** (M10 → M33.1).

## NEXT TASK

Start SESSION_211 with (a) starting-state verification;
(b) read M33.0 planning memo §5.b D1 + D2 + D3 + §5.e
M33.1 + §5.h; (c) ship the annotation extension +
projection extension + read view + URL entry + docstring
update + ~15 tests per §5.e; (d) verify baselines including
two-source audit agreement gate (162/130/31/322);
(e) document DoD exception path invocation #8;
(f) ship the M33.1 handoff at
`docs/handoffs/SESSION_211_m33_inc1_backend.md`; **do NOT
push**.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_33_PLANNING.md`** (governing
   contract for M33)
6. `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md` §9 (M33
   candidate list origin + F&I depth-arc standing
   question resolution)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M32 baseline: **161/129/32/321**; post-M33.1
   projection: 162/130/31/322)
8. `docs/CAPABILITY_MATRIX.md` §7η (M32 shipped surface);
   §7θ added at M33 close.
9. `docs/handoffs/SESSION_210_m33_inc0_planning.md` (this
   session's handoff)
10. `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md` (M32
    close-out fold + F&I intake page shipped surface —
    the M33 receiver)
11. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.2 (M10.2
    DealStructure origin — governs the M-to-1 iteration
    semantic that M33 D9 preserves)
12. `docs/research/FINANCE_DEPARTMENT_MAPPING.md` §2 +
    §3.6 (F&I first-action + LTV / PTI / DTI semantics)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at M33.0 §4.6 for
    `vehicle_stock` discovery on writeup-originated vs
    direct-create CAs)
14. Memory record
    `feedback_playwright_as_operational_contract.md`
    (M33 D8 journey extends operational contract to F&I
    first-loop; financial-language regex assertion
    strengthens it)
15. Memory record
    `feedback_terminal_output_discipline.md` (governs
    M33.1 implementation-session output shape)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_210 — Milestone 33.0 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged since M32.1). Test baseline:
  **4,995 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 377 pass** across
  42 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **24 journeys** total. Full-suite
  fresh-DB run at M32.3 close: **31 passed / 0 failed /
  32.5s**.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `2a1e359` (M32.3 hash-backfill commit):
  **success in 3m10s** at 2026-08-04T22:30:04Z. M32 is
  CI-verified shipped.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → **M32**. M33 active (M33.0
  shipped at SESSION_210; M33.1 opens at SESSION_211).
- **DRF admin surface:** **121** endpoints (M32.1 count;
  M33.1 projection: 122).
- **Frontend operator routes:** **21** (unchanged since
  M32.3).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (M32.1 count; M33.1
  projection: 322).
- **Frontend surfaces:** M32.2 sales-manager Writeups tab
  on `LeadDetailModal`; M32.3 `DealerFandIIncoming.tsx`
  page + F&I "Incoming" nav entry. M33.2 will add
  status chip + row actions + `DealStructureForm` +
  `DealStructureReadView`.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **36 consecutive milestones** (M10 → M32). Projection at
  M33.1: 37; at M33.2: 37 (no new endpoints in M33.2).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 33 status:** ACTIVE. M33.0 SHIPPED at
  SESSION_210. M33.1 opens at SESSION_211.
- **Audit tooling status:** unchanged from M26.1. Coverage
  **129 / 161** (M32.3 close); projection at M33.1 close:
  130 / 162.
- **Playwright personas:** **6 actual** — platform_operator,
  owner, sales_manager, recon_manager, bhph_collector,
  f_and_i_manager (M32.3 addition). No new persona in M33.
- **§9 evidence for M34:** Lender Fit Recommendations
  elevated to future candidate list per operator directive
  at M33.0; NEW C F&I chargeback substrate (still pilot-
  evidence gated); NEW F&I workflow state extensions
  (beyond M33's two derived states — awaits operator
  evidence on richer state model); NEW F&I-scoped lead-
  context view; NEW cross-lead pending-approval queue;
  NEW O2 + NEW O3 (unchanged); H (test-hygiene); plus
  gated T/U/L/M, deferred D, deferred stable G, plus M32
  §3 + M31 §3 + M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25
  §4 deferrals.
- **Planning-time as-recommended streak: 11** (at M32.3
  close). M33.0 planning-only — projection to **12** at
  M33 close if no §0.a amendments (four verification-
  driven correction rounds shaped the design but did not
  change the target; per M21.0 lesson recorded at
  MILESTONE_21_RETROSPECTIVE, verification-driven revision
  does not break the as-recommended streak).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least
  one Playwright operational journey, or explicitly
  document why no journey change is required. M26 first
  invocation; M27.1 second; M28.1 third; M29.1 fourth;
  M30.1 fifth; M31.1 sixth; M32.1 seventh; **M33.1 eighth**
  (backend-only annotation + read endpoint with no
  operator-facing behavior change). M33.2 will satisfy
  DoD directly via D8.
- **Financial-language contract (NEW at M33.0):** sales
  targets / proposed structure values only; never lender-
  approved / lender-committed / actual. Locked at D5 + D6
  + D7 + D8 + R10. First planning-time contract on
  financial-value language semantics; candidate durable
  lesson if survives M33.2 Playwright verification.
- **Future capability recorded (NEW at M33.0):** Lender
  Fit Recommendations — structured, auditable,
  human-controlled. Full design contract at planning
  time. NOT implemented in M33. Blocked on named
  prerequisites.
- **Durable lessons carried into M34+:** all (a)–(x) plus
  M31-elevated (w) + (x). M32 candidate lessons (y) / (z)
  / (aa) / (bb) awaiting first re-application. M33.0
  re-applied (z) — verification-driven revision cycles
  applied four times at M33.0 planning-open before §5.b
  lock. Eligible for elevation at M33 retrospective §5 to
  "load-bearing across two milestones."
