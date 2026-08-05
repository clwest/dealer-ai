---
state: active
date: 2026-08-05
last_session_shipped: SESSION_213
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
milestone_34_status: active
next_session: SESSION_214
next_milestone: 34
next_milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys"
next_increment: 1
next_increment_name: "M34.1 — Backend: seed extensions + Django regression tests"
---

# Next session — SESSION_214 · Milestone 34 · Increment 1 (M34.1 — backend seed extensions + Django regression tests)

> **Milestone 34 planning complete at SESSION_213.** M34.0
> locked all §5 decisions (D1–D8; risks R1–R9; verifications
> §4.1–§4.6 all CLEAN; two-increment phasing; DoD compliance;
> rollback; non-goals). Governing contract:
> `docs/roadmap/MILESTONE_34_PLANNING.md`.
>
> **M34 target:** Test-Hygiene Remediation. Idempotent seeds
> + rerun-safe acceptance journeys for the three shared-DB
> non-idempotent journeys: `sales_manager/daily_startup`,
> `recon/workflow`, `office/accounting_workflow`. Six-
> milestone deferral (M27.2 → M33.2) closed.
>
> **Zero blocking findings at §4 verification. Zero
> corrections required before §5.b lock** — first M34
> planning-open cycle with zero revisions. Planning-time
> as-recommended streak at 13 (projected close if no §0.a
> amendments).
>
> **Fully non-customer-facing milestone** — first since M20.
> DoD exception path invocation #9 (M34.1) + continuation
> (M34.2). Justification per §5.f: H protects the durability
> of the 131-endpoint coverage set that every future depth-
> arc addition builds on.
>
> **Two-increment phasing:**
> - **M34.1** (this session): backend seed extensions (three
>   files) + Django regression tests (~3 tests).
> - **M34.2** (SESSION_215): acceptance-workspace helper
>   defense + `@rerun-hygiene` tag + repeated-run proof
>   evidence in handoff.
>
> **Substrate-compound-value continuation breaks intentionally
> at M34** — M32 + M33 2-link F&I depth arc pauses per M33 §9
> "close a deferral" resolution. Arc remains primary
> continuation candidate for M35 if pilot evidence surfaces
> on NEW C chargeback, NEW F&I workflow-state extensions, or
> Lender Fit Recommendations.
>
> **Zero-drift permission-class streak advances 37 → 38
> consecutive milestones** projected at M34 close (M34 adds
> no permission classes, no endpoints).
>
> **Durable lesson locked at M34.0 (D8):** *Acceptance
> journeys must be independently rerunnable against shared
> state; green-on-clean-DB alone is insufficient evidence of
> operational reliability.* Recorded as candidate (ff) at
> M34 retrospective §5; awaits first re-application to
> elevate.
>
> **SESSION_214 opens M34.1 — backend seed extensions +
> Django regression tests.** Read the M34.0 planning memo
> §5.b D1 + D2 + D3 + D4 + D6 + §5.e M34.1 before touching
> any seed file. No product-code changes anywhere.

## First thing SESSION_214 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M33 push OR ahead by 3 commits
  (SESSION_213 planning memo + handoff + start-next flip +
  hash-backfill follow-up) if M34.0 planning commit not yet
  pushed. **No coordinated push at M34.0 close** per §9 of
  SESSION_213 handoff.
- `git log --oneline -10` — top should be the M34.0 hash-
  backfill commit; check for expected M34.0 commit followed
  by the M33 commit sequence (`3a83584` M33.2 hash-backfill,
  `622c51e` M33 close-out fold, `1e0008f` M33.1 hash-
  backfill, `eb50f94` M33.1 backend, `e03d31c` M33.0 hash-
  backfill, `7b8f6b6` M33.0 planning).
- `python3 manage.py test dealer_ai` → **5,015 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **402 pass** across 45 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset
  per SESSION_200 §0.a durable lesson (v).

### 2. Read the M34.0 planning memo before touching code

Read the following sections of
`docs/roadmap/MILESTONE_34_PLANNING.md` before opening any
seed file:

- **§5.b D1** — seed-idempotency contract (project-wide
  statement + docstring `## Rerun invariants` section
  requirement).
- **§5.b D2** — sales-manager 3-source reset (exact code
  block; placement; tag-scoped queryset invariant).
- **§5.b D3** — recon 1-line reset (tag + dealership
  scoping; placement).
- **§5.b D4** — accounting scoped wipe (dealership-scoped;
  M20_ACCEPTANCE_DB invariant re-documented in module
  docstring).
- **§5.b D6** — Django regression tests (three tests;
  mutate → re-seed → invariant-check shape).
- **§5.e M34.1** — file paths + backend baseline projection
  (~5,018 pass) + audit-unchanged expectation.
- **§5.f** — DoD exception path invocation #9 rationale.
- **§5.h** — non-goals (12 explicit + no product-code
  changes; no assertion weakening; no shared helper; etc.).

### 3. Ship M34.1 backend substrate

Per M34.0 §5.e M34.1:

- **Extend `seed_journey_sales_manager_daily_startup.py`:**
  - Add `from dealer_ai.models import BeBack` (or extend
    existing import block).
  - Add D2 reset code block **before** the `_provision_leads`
    call in `handle()`. Exact order per §5.b D2:
    1. `_existing_leads(dealership).update(assigned_to=None)`
    2. `BeBack.objects.filter(lead__in=seeded).delete()`
    3. `FollowUpCadence.objects.filter(lead__in=seeded).exclude(template="24hr").delete()`
    4. `FollowUpCadence.objects.filter(lead__in=seeded, template="24hr").update(is_active=True, paused_at=None)`
  - Add `## Rerun invariants` section to module docstring
    naming each restored invariant explicitly.
  - `--reset` flag semantics preserved unchanged.
- **Extend `seed_journey_recon_workflow.py`:**
  - Add D3 reset line **before** `_provision_report_and_finding`:
    `ReconDecision.objects.filter(finding__description__startswith=FIXTURE_FINDING_TAG, dealership=dealership).delete()`.
  - Add `## Rerun invariants` docstring section.
- **Extend `seed_journey_office_accounting_workflow.py`:**
  - Add `from dealer_ai.models import TrialBalanceSnapshot`.
  - Add D4 wipe line **before** `_provision_journal_entry`:
    `TrialBalanceSnapshot.objects.filter(dealership=dealership).delete()`.
  - Add `## Rerun invariants` docstring section + explicit
    `M20_ACCEPTANCE_DB` invariant note per §5.b D4.
- **Create
  `backend/dealer_ai/tests/test_seed_journey_idempotency.py`
  (~120 lines):**
  - Three tests per D6:
    - `test_sales_manager_daily_startup_idempotent`
    - `test_recon_workflow_idempotent`
    - `test_office_accounting_workflow_idempotent`
  - Each uses `django.core.management.call_command()` +
    direct model queries + fixture selectors matching the
    seed's tag / stock / description constants.
  - Wrap in Django's default per-test transaction rollback.
- **Historical migration NOT modified.**
- **No product-code change** (no view, service, model,
  permission, URL, migration edits).

### 4. Verify M34.1 close baselines

- `python3 manage.py test dealer_ai` → **~5,018 pass, 1
  skipped, 0 fail** (target: 5,015 + 3 new regression tests).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `python3 -m dealer_ai.scripts.audit_operational_surface`
  → **162 / 131 / 31 / 321 unchanged** (M34.1 adds no
  endpoints).

### 5. DoD exception path — invocation #9

Document in §3 of M34.1 handoff:

> M34.1 is backend-only (seed idempotency + Django
> regression tests). Zero operator-visible behavior. Ninth
> invocation of DoD exception path (M26 + M27.1 + M28.1 +
> M29.1 + M30.1 + M31.1 + M32.1 + M33.1 + M34.1). M34.2
> continues exception path (no new customer-facing journey;
> existing three journeys tagged for rerun-proof).

### 6. Ship the M34.1 handoff

- `docs/handoffs/SESSION_214_m34_inc1_seeds.md`.
- **Do NOT push** — coordinated push at M34 close per §9
  of SESSION_213 handoff.

## Non-goals for SESSION_214

- ❌ Do NOT modify any product-code file (views, services,
  models, permissions, URLs, migrations, schemas). Seed +
  test files only.
- ❌ Do NOT modify the three journey `.spec.ts` files or
  the assertion helper — those land at M34.2.
- ❌ Do NOT introduce a shared reset helper across seed
  commands (per §5.b D1 no-abstraction discipline).
- ❌ Do NOT modify `--reset` flag semantics on the three
  seed commands — reset remains a manual escape hatch.
- ❌ Do NOT touch the M32.3 Intake Iris or M33.2 Structure
  Sam fixtures — already independently rerunnable per M32
  D11 + M33 R7.
- ❌ Do NOT add sleeps, retries, or weaken assertions
  anywhere.
- ❌ Do NOT expand scope to any other seed commands.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT skip the DoD exception path documentation in §3
  of the handoff.
- ❌ Do NOT push at M34.1 close — coordinated push at M34
  close.

## Baseline expected at close

- Backend suite: 5,015 → **~5,018** pass (3 new regression
  tests).
- Frontend: unchanged (Vitest 402 pass; no frontend code
  changes at M34.1).
- Acceptance: unchanged (M34.1 does not touch the acceptance
  workspace).
- Audit: **162 / 131 / 31 / 321 unchanged**.
- Permission classes: 7 (zero-drift streak advances 37 →
  **38** at M34 close).
- Migrations: unchanged (M34.1 adds none).

## NEXT TASK

Start SESSION_214 with (a) starting-state verification;
(b) read M34.0 planning memo §5.b D1 + D2 + D3 + D4 + D6 +
§5.e M34.1 + §5.f + §5.h before touching code; (c) ship the
three seed extensions per D2 + D3 + D4 including
`## Rerun invariants` docstring sections; (d) create
`test_seed_journey_idempotency.py` with the three regression
tests per D6; (e) verify baselines (5,018 pass; audit
unchanged; migrations unchanged); (f) DoD exception path
documentation in §3 of the handoff (invocation #9);
(g) ship the M34.1 handoff at
`docs/handoffs/SESSION_214_m34_inc1_seeds.md`. **Do NOT
push.**

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` §9 (M34
   candidate list origin + F&I depth-arc standing question)
6. **`docs/roadmap/MILESTONE_34_PLANNING.md`** (governing
   contract for M34 — read §5.b + §5.e + §5.h before code)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-M33
   baseline — 162 / 131 / 31 / 321)
8. `docs/CAPABILITY_MATRIX.md` §7θ (M33 shipped surface);
   §7ι added at M34 close
9. `docs/handoffs/SESSION_213_m34_inc0_planning.md` (M34.0
   planning close)
10. `docs/handoffs/SESSION_212_m33_inc2_frontend.md` (M33.2
    shipped + M33 close-out fold)
11. `docs/roadmap/MILESTONE_20_PLANNING.md` §5.d (M20 compose-
    service-verbs rule for seeds; superseded at M34 for
    reset-scoped ORM queries per D2 + D3 + D4)
12. Memory record
    `feedback_duplicate_small_stable_logic.md` (governs D1
    no-shared-helper decision at M34)
13. Memory record
    `feedback_playwright_as_operational_contract.md` (M34
    preserves operational contract via rerun-safety, not
    via new journey coverage)
14. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at §4.5 for cascade behavior)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_213 — Milestone 34 PLANNING SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged since M32.1). Test baseline:
  **5,015 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 402 pass** across
  45 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **25 journeys** total (unchanged M34.0).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `3a83584` (M33.2 hash-backfill commit):
  **success in 3m8s** at 2026-08-05T04:20:13Z.
- **Async runtime:** unchanged (Celery 5.5.3 + Redis 6.4.0
  + `django-celery-beat` 2.8.1 DatabaseScheduler).
- **Milestones shipped:** M1 → **M33**. M34.0 planning
  shipped at SESSION_213. M34.1 backend + M34.2 acceptance
  pending.
- **DRF admin surface:** **122** endpoints (unchanged M34.0).
- **Frontend operator routes:** **21** (unchanged M34.0).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged M34.0).
- **Frontend surfaces:** unchanged M34.0.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-seven consecutive milestones** (M10 → M33).
  M34 projected: 38 at close (no new classes anywhere in
  M34).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 34 status:** M34.0 SHIPPED (planning-only).
  M34.1 (backend seed extensions + regression tests) is
  the next increment.
- **Audit tooling status:** unchanged from M26.1. Coverage
  **131 / 162** (M33.2 close; unchanged at M34.0). M34
  projection: unchanged (M34 adds no endpoints).
- **Playwright personas:** **6 actual** (unchanged M34.0).
- **Playwright fixtures:** unchanged M34.0 — Intake Iris
  (M32.3) + Structure Sam (M33.2) remain independently
  rerunnable per M32 D11 + M33 R7.
- **§9 evidence for M35:** unchanged from M33 §9 (F&I
  depth-arc candidates: NEW C chargeback substrate, Lender
  Fit Recommendations, NEW F&I workflow-state extensions,
  NEW F&I-scoped lead-context view, NEW cross-lead pending-
  approval queue; deferrals: direct-create structuring,
  iteration UX, PATCH on DealStructure; NEW O2 + NEW O3
  unchanged; H closes at M34; plus gated T/U/L/M, deferred
  D, deferred stable G, plus M33 §3 + M32 §3 + prior
  deferrals).
- **Planning-time streak: 12 → 13** projected at M34 close
  (at M34.0 with zero corrections; historical run of 89
  across M10 → M23 preserved).
- **DoD amendment (M21.0 §5.f Option B):** ninth invocation
  of exception path at M34.1 (backend-only). M34.2
  continues exception path (no new customer-facing journey).
  First fully non-customer-facing milestone since M20.
- **M33 audit coverage at close:** 162 endpoints, **131
  covered / 31 backend-only** (unchanged at M34.0 open).
- **Durable lessons carried into M35+:** all (a)–(ee) plus
  M34-origin candidate lesson (ff): *Acceptance journeys
  must be independently rerunnable against shared state;
  green-on-clean-DB alone is insufficient evidence of
  operational reliability.* Recorded verbatim per §5.b D8;
  awaits first re-application to elevate to load-bearing-
  across-two-milestones. M33-origin candidates (cc)/(dd)/
  (ee) unchanged at M34.0 — no re-application opportunity
  (M34 is not a coverage-projection / financial-language /
  future-capability-recording milestone).
