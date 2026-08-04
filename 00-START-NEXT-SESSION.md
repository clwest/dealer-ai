---
state: active
date: 2026-08-04
last_session_shipped: SESSION_206
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
next_session: SESSION_207
next_milestone: 32
next_milestone_name: "Deal Writeups: Sales-Manager-to-F&I Handoff (writeup CRUD substrate + sales-manager UI + F&I intake queue + provenance-FK migration)"
next_increment: 1
next_increment_name: "M32.1 — Backend substrate + provenance-FK migration"
---

# Next session — SESSION_207 · Milestone 32 · Increment 1 (M32.1 — backend substrate + provenance-FK migration)

> **Milestone 32 opened at SESSION_206 M32.0.** Target
> locked as **NEW Deal Writeups: Sales-Manager-to-F&I
> Handoff** — the largest un-gated direct operator-coverage
> gain of any M32 candidate, natural bridge domain between
> the sales domain (fully covered M11.1–M11.6) and the F&I
> domain (mostly uncovered #89–101), answering the M31 §9
> breadth-vs-depth standing question with breadth after
> five consecutive accounting/templates selections
> (M27.1 → M31).
>
> **The anchor business question** governing every M32
> scope decision: *Can a sales manager create a deal
> writeup, review and approve it, and hand it off to F&I
> such that the F&I team receives a complete, actionable
> incoming credit application with unambiguous provenance
> — all through Dealer OS?*
>
> **Three-increment scope-driven split** (first customer-
> facing milestone since M11 to ship across three
> increments):
>
> - **M32.1 (SESSION_207) — Backend substrate +
>   provenance-FK migration.** New writeup list + detail
>   endpoints (D1 + D2); new credit-application list
>   endpoint (D3); new `credit_application.deal_writeup`
>   nullable OneToOneField migration (D9-revised²); new
>   `DealWriteupAlreadyLinkedError` service-layer error
>   class; `hand_off_to_fandi` updated to set FK inside
>   its existing atomic block; `record_credit_application`
>   signature-additive `deal_writeup` kwarg + service-
>   layer guard; ~51 tests including mandatory pairing-
>   uniqueness test. **DoD exception path invocation #7.**
> - **M32.2 (SESSION_208) — Sales-manager UI + sales-side
>   Playwright.** Writeups tab on `LeadDetailModal`
>   (manager-only by transitivity); inline form, list,
>   Approve, Send-to-F&I buttons; two confirmation dialogs
>   with state-machine-truthful copy (no false re-approval
>   advertisement; irreversibility flagged). Removal of
>   `salesApi.ts:10-25` "UI deferred" comments. New
>   Playwright describe block satisfies DoD directly.
> - **M32.3 (SESSION_209) — F&I intake UI + F&I-side
>   Playwright extension + new persona.** New
>   `DealerFandIIncoming.tsx` page (non-navigational rows
>   — F&I role cannot access `admin_lead_detail`); new
>   F&I nav "Incoming" link; new `f_and_i_manager`
>   persona; new idempotent `seed_journey_fandi_intake_receipt`
>   seed command provisioning independent `Intake Iris`
>   fixture. New Playwright describe block satisfies DoD
>   directly.
>
> **Three blocking findings + two inaccessibility findings
> resolved architecturally at M32.0** before scope-lock:
> writeup pk discoverability (D1 + D2); downstream F&I UI
> receiver (D3 + D8); CA↔writeup pairing determinism
> (D9-revised² OneToOneField with three-layer defense);
> F&I role access to lead detail (D8-revised non-
> navigational rows); advisor viewer LeadDetailModal
> access (D4-revised² no-treatment posture).
>
> **Zero-drift permission-class streak preserved:** 33
> (M31) → **34 → 35 → 36** at M32 close (all reuse
> existing classes). **Substrate-compound-value depth arc:
> 5 links preserved** (no sixth link; NEW C F&I chargeback
> remains pilot-evidence-gated). **First break out of
> accounting/templates domain since M27** (six milestones
> ago).
>
> **Historical migration 0034 will NOT be modified** per
> project directive: architectural evolution recorded in
> current model/service docstrings + migration 0051
> docstring + M32 planning memo + retrospective +
> `docs/CAPABILITY_MATRIX.md` §7η, not by retroactively
> rewriting M11.3's historical migration.
>
> **SESSION_207 ships M32.1 backend substrate only.** No
> frontend changes; no Playwright; no DRF admin count
> re-baselining. DoD exception path invocation #7 —
> seventh consecutive substrate-first pattern (M26 +
> M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1).

## First thing SESSION_207 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of
  `origin/main` by 1 commit (SESSION_206 planning memo +
  handoff + START flip, plus follow-up hash backfill = 2
  commits total at M32.0 close). If push not yet
  executed for M32.0 planning, local ahead by 2.
- `git log --oneline -10` — top should be SESSION_206
  M32.0 hash-backfill commit; check for expected M32.0
  commit sequence + prior M31 commit sequence.
- `python3 manage.py test dealer_ai` → **4,933 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **319 pass** across 36
  files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive
  reset per SESSION_200 §0.a durable lesson (v).

### 2. Confirm working from M32.0 planning memo

Read `docs/roadmap/MILESTONE_32_PLANNING.md` §5.b D1 +
D2 + D3 + D9 + §5.e M32.1 before touching backend code.
Reference `docs/handoffs/SESSION_206_m32_inc0_planning.md`
§7 for locks summary and §10 for M32.1 first-thing
sequence.

Key architectural pre-reads:

- **D9-revised²** — nullable OneToOneField with three-
  layer defense. Three-layer defense is load-bearing;
  the mandatory
  `test_writeup_cannot_link_to_multiple_credit_applications`
  test asserts all three layers.
- **D1 + D3 fail-explicit filter validation** — invalid
  filter values return 400, not silent unfiltering.
  Explicit test matrix required for each filter parameter
  (state / lead_id / intake / since).
- **Historical migration 0034 NOT modified** — all
  architectural evolution goes into `models.py`
  docstrings + service docstrings + migration 0051.

### 3. Ship M32.1 backend substrate

Per §5.e M32.1:

- **Migration** `0051_m32_credit_application_deal_writeup_fk.py`
  — add `credit_application.deal_writeup` nullable
  `OneToOneField` (SET_NULL, `related_name="credit_application"`).
  Reversible column drop.
- **Service layer** (`services/deal_writeups/deal_writeup.py`
  + `services/f_and_i/credit_application.py`):
  - New `list_deal_writeups(*, dealership, state=None,
    lead=None)` verb.
  - New `get_deal_writeup(*, pk, dealership)` verb.
  - New `list_credit_applications(*, dealership,
    intake=False, lead=None, since=None)` verb —
    `intake=True` filters CAs without contract; projection
    includes writeup context via new FK.
  - Update `hand_off_to_fandi` to set
    `credit_app.deal_writeup=writeup` (2-line change
    inside existing `@transaction.atomic` block).
  - Update `record_credit_application` signature to
    accept optional `deal_writeup` kwarg (default None);
    add `DealWriteupAlreadyLinkedError` guard raised
    before DB write when writeup is already paired.
  - New error class `DealWriteupAlreadyLinkedError` in
    `services/f_and_i/credit_application.py`.
  - **Model docstring updates** on `CreditApplication`
    (`models.py:4454+` — amend "Attach shape" paragraph)
    and on `DealWriteup` (add reference to
    `credit_application` reverse relation).
  - **Service docstring updates** on `hand_off_to_fandi`
    and `record_credit_application`.
- **Endpoint layer** (`views_deal_writeups.py` +
  `views_f_and_i.py`):
  - `admin_deal_writeup_list(request)` (GET) — D1 fail-
    explicit query parsing.
  - `admin_deal_writeup_detail(request, pk)` (GET) — D2.
  - `admin_credit_application_list(request)` (GET) — D3
    fail-explicit query parsing.
- **URL** (`urls.py`): 3 new patterns.
- **DO NOT modify** `migrations/0034_m113_deal_writeup_entity.py`.
- **Tests planned (~51):**
  - ~14 for writeup list.
  - ~8 for writeup detail.
  - ~16 for CA list (including `intake=false → 400`).
  - ~7 for pairing FK behavior including mandatory
    `test_writeup_cannot_link_to_multiple_credit_applications`
    exercising all 3 defense layers (service
    `DealWriteupAlreadyLinkedError`; DB `IntegrityError`
    via bypass-service direct ORM; M11.3
    `WriteupAlreadyHandedOffError` via `hand_off_to_fandi`
    second-call path).
  - ~6 auth/tenancy coverage.

### 4. Verify M32.1 close baselines

- Backend suite: **4,933 → ~4,984 pass**, 1 skipped, 0
  fail.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run`
  → "No changes detected."
- `cd frontend && npx tsc --noEmit` clean (no frontend
  changes expected).
- `cd acceptance && npx tsc --noEmit` clean.
- Regenerate audit artifact:
  `python3 -m dealer_ai.scripts.audit_operational_surface`.
  Expected: 158 → **161** endpoints; 124 covered
  unchanged (three new endpoints backend-only at M32.1;
  re-cover at M32.2 + M32.3); 34 → 34 backend-only
  transitional (three backend-only #112–114 remain
  classified so at M32.1 close; new list + detail
  endpoints add to backend-only). Service verbs 318 →
  321 (+3 new verbs).

### 5. DoD exception path invocation #7

Document in §3 of M32.1 handoff:

- Backend substrate with no operator-facing behavior
  change on its own.
- Seventh consecutive substrate-first pattern (M26 +
  M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1).
- M32.2 + M32.3 satisfy DoD directly.

### 6. Ship the M32.1 handoff

- `docs/handoffs/SESSION_207_m32_inc1_backend.md`.
- Follow M31.1 handoff shape.
- **Do NOT push** — coordinated push at M32 close.

## Non-goals for SESSION_207

- ❌ Do NOT ship any frontend or Playwright code — M32.1
  is backend substrate only.
- ❌ Do NOT open any M32.2 or M32.3 UI work.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M31 shipped surface.
- ❌ **Do NOT modify historical migration
  `0034_m113_deal_writeup_entity.py`.** Architectural
  evolution goes into `models.py` + service docstrings +
  migration 0051.
- ❌ Do NOT modify the acceptance suite unless CI
  regression fixes land as §0.a M32.1 amendments.
- ❌ Do NOT skip the DoD exception rationale documentation
  in §3 of the M32.1 handoff.
- ❌ Do NOT skip the mandatory
  `test_writeup_cannot_link_to_multiple_credit_applications`
  test — it is the load-bearing assertion that the
  three-layer defense holds.
- ❌ Do NOT loosen D1 + D3 fail-explicit validation to
  silent unfiltering — 400 on invalid values is
  intentional.

## Baseline expected at close

- Backend: 4,933 → ~4,984 pass.
- Frontend: 319 pass (unchanged — no frontend work in
  M32.1).
- Acceptance: 22 journeys (unchanged — no Playwright in
  M32.1).
- Audit: 158 → 161 endpoints; 124 covered unchanged; 34
  → 34 backend-only (transitional); 318 → 321 service
  verbs.
- DRF admin surface: 118 → 121.

## NEXT TASK

Start SESSION_207 with (a) starting-state verification;
(b) confirm working from M32.0 planning memo (read D1 +
D2 + D3 + D9 + §5.e M32.1); (c) ship M32.1 backend
substrate — migration 0051 + 3 service verbs + 3
endpoints + `DealWriteupAlreadyLinkedError` class +
`hand_off_to_fandi` update + `record_credit_application`
signature-additive kwarg + docstring updates (NOT
historical migration 0034); (d) verify M32.1 close
baselines (backend ~4,984 pass; audit 161 endpoints /
124 covered / 34 backend-only transitional / 321 service
verbs); (e) DoD exception path #7 documented in §3 of
handoff; (f) ship the M32.1 handoff at
`docs/handoffs/SESSION_207_m32_inc1_backend.md`; **do NOT
push** — coordinated push at M32 close.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M31 shipped surface in
   CAPABILITY_MATRIX §7δ + §7ε + §7ζ per convention
   adopted at M27+; M32 shipped surface will be §7η per
   M31 precedent)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_32_PLANNING.md`** §5.b D1 +
   D2 + D3 + D9-revised² + §5.e M32.1 (governing contract
   for M32.1)
6. `docs/handoffs/SESSION_206_m32_inc0_planning.md`
   §7 + §10 (M32.0 close-out; first-thing sequence for
   M32.1)
7. `docs/roadmap/MILESTONE_31_RETROSPECTIVE.md` §5 +
   §9 (M32 candidate list origin; breadth-vs-depth
   standing question resolved with breadth answer)
8. `docs/roadmap/MILESTONE_11_PLANNING.md` §7 M11.3
   (M11.3 DealWriteup entity origin — governs the
   architectural preference that M32.1 D9-revised²
   evolves to peer-with-optional-backpointer)
9. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M31 baseline — 158 endpoints / 124 covered / 34
   backend-only / 318 service verbs; M32.1 projected
   delta +3 endpoints, 0 covered transitionally, +3
   verbs)
10. `docs/CAPABILITY_MATRIX.md` §7ζ (M31 shipped surface);
    §7η added at M32 close
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M32.0 §4.5 for
    APPROVE / HAND-OFF discoverability; M32.1 D1 + D2
    resolve)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs future M32.2 co-located
    inline-dialog choice; not relevant to M32.1 backend
    scope but load-bearing for M32.2 planning)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_206 — Milestone 32 OPEN)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,933 pass**, 1 skipped, 0 fail. M32.1 will add
  migration `0051`.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  + `vite build` clean. **Vitest baseline: 319 pass**
  across 36 test files. M32.1 does not change frontend.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **22 journeys** total. Latest full-
  suite run at M31.2 close: 28 passed / 0 failed / 32.6s.
  M32.1 does not change acceptance.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `08fef5f` (M31.2 hash-backfill
  commit): 28 passed / 0 failed / 2m57s.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → M31. **M32 opened at
  M32.0 (planning-only).**
- **DRF admin surface:** **118** endpoints (unchanged
  since M31.1; M32.1 will add +3 → 121).
- **Frontend operator routes:** 20 (unchanged; M32.3
  will add `/dealer-ai-f-and-i/incoming`).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **318** verbs (unchanged since
  M31.1; M32.1 will add +3 → 321).
- **Frontend surfaces:** M32 will add sales-manager
  Writeups tab on `LeadDetailModal` (M32.2) + new
  `DealerFandIIncoming.tsx` page (M32.3).
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift
  streak **thirty-three consecutive milestones** (M10
  → M31). Projected 34 → 35 → 36 at M32.1 → M32.2 →
  M32.3 close (all reuse existing classes).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 32 status:** ACTIVE (M32.0 planning
  shipped; M32.1 next).
- **Audit tooling status:** unchanged from M26.1.
  Coverage **124 / 158** (M31.2 baseline).
- **§9 evidence for M33+:** NEW C F&I chargeback
  substrate (unchanged — still gated pending pilot
  evidence); NEW O2 + NEW O3 (unchanged from
  M26+M27+M28+M29+M30+M31); H (test-hygiene — same 3
  failing journeys unchanged); plus gated T/U/L/M,
  deferred D, deferred stable G, plus M32 §3 + M31 §3
  + M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25 §4
  deferrals. **New M32 §3 deferrals:** salesperson-
  authored writeups; writeup edit (PATCH); cross-lead
  sales-manager pending-approval queue page; F&I-scoped
  lead-context view; per-CA detail page; separation-of-
  duties enforcement; pagination on 3 new list
  endpoints; websocket/auto-refresh; F&I state
  extensions on intake rows; `intake=false` filter;
  backfill of `credit_application.deal_writeup`; F&I-
  scoped post-intake acceptance journey.
- **Planning-time streak: 10 → 11 (projected at M32.0
  close, unchanged at M32.1/M32.2/M32.3 as pure
  implementation).** Historical run of 89 across M10 →
  M23 preserved.
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least
  one Playwright operational journey, or explicitly
  document in §3 why no journey change is required.
  Six invocations at M31 close (M26 + M27.1 + M28.1 +
  M29.1 + M30.1 + M31.1); **seventh at M32.1**.
  M32.2 + M32.3 satisfy DoD directly.
- **M32 audit coverage projected at close:** 161
  endpoints, **127 covered / 34 backend-only unchanged**
  (delta from M31.2: +3 endpoints, +3 covered by M32
  close, 0 backend-only net change — the three writeup
  #112–114 endpoints re-classify from backend-only to
  covered via M32.2 UI + the 3 new M32.1 list/detail
  endpoints add to backend-only transitionally at M32.1
  and re-classify to covered via M32.2/M32.3 UI).
  Two-source agreement gate at M32.3 close.
- **Durable lessons carried into M33+:** all (a)–(x)
  from the SESSION_202 close-state list plus M31-
  elevated (w) + (x) continue to apply. M32 may elevate
  the **Playwright-independent-fixture pattern** (new at
  M32.3) to durable lesson (y) at M32 retrospective §5
  if it re-applies at M33+. **One NEW principle
  candidate at M32.0** — verification-driven revision
  cycles as a planning-open discipline (three blocking
  findings + two inaccessibility findings resolved via
  two user-review revision rounds); awaits first re-
  application to elevate.
