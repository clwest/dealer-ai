---
state: active
date: 2026-08-05
last_session_shipped: SESSION_214
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
next_session: SESSION_215
next_milestone: 34
next_milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys"
next_increment: 2
next_increment_name: "M34.2 — Acceptance workspace: helper defense + @rerun-hygiene tag + repeated-run proof + M34 close-out fold"
---

# Next session — SESSION_215 · Milestone 34 · Increment 2 (M34.2 — acceptance workspace + M34 close-out fold)

> **Milestone 34 · Increment 1 shipped at SESSION_214.** All
> three seed commands now restore the pre-flight invariants
> the M20.2 / M20.3 journeys depend on. Six focused regression
> tests prove the mutate → re-seed cycle restores state.
> Backend baseline advanced 5,015 → **5,021** pass (+6 vs
> planned +3 per M34.0 §5.e; §0.a coverage-projection
> truthfulness correction documented in SESSION_214 handoff
> §0.a; (cc) durable lesson elevated to load-bearing-across-
> two-milestones on second invocation).
>
> **No product-code changes** — seeds + tests only. Audit
> unchanged at 162 / 131 / 31 / 321. Migrations unchanged.
> Zero-drift permission-class streak unchanged at 37 (M10 →
> M33); M34 close projection: 38.
>
> **DoD exception path invocation #9 at M34.1.** M34.2
> continues the exception path — no new customer-facing
> journey; the existing three journeys are tagged for
> developer-side rerun-proof invocation per D7 Option A.
>
> **SESSION_215 ships M34.2** — the acceptance-workspace half
> of H (assertion helper defense + `@rerun-hygiene` tag +
> `acceptance/README.md` invocation documentation + local
> repeated-run evidence) AND the M34 close-out fold (M34
> retrospective document + CAPABILITY_MATRIX §7ι + planning-
> memo frontmatter flip to historical + SESSION_216 M35.0
> planning marker).
>
> **Substrate-compound-value continuation** remains
> intentionally paused per M33 §9 "close a deferral"
> resolution. F&I depth arc remains primary M35 candidate;
> M35.0 planning at SESSION_216 will re-evaluate against the
> M33 §9 elevated candidate list under the primary
> operational-coverage lens.
>
> **Coordinated M34 push pending user confirmation** at M34.2
> close. Expected M34 commits at push: **4–6** (M34.0
> planning `f163e93`; M34.0 hash-backfill `a03c5eb`; M34.1
> backend + tests; M34.1 hash-backfill; M34.2 acceptance +
> close-out fold; M34.2 hash-backfill).

## First thing SESSION_215 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main`
  by 4 commits (M34.0 planning + M34.0 hash-backfill +
  M34.1 backend + M34.1 hash-backfill).
- `git log --oneline -10` — top should be the M34.1 hash-
  backfill; expected sequence follows the standard M28+
  cadence.
- `python3 manage.py test dealer_ai` → **5,021 pass, 1
  skipped, 0 fail** (matches M34.1 close baseline).
- `cd frontend && npm test` → **402 pass** across 45 files
  (unchanged).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset
  per SESSION_200 §0.a durable lesson (v).

### 2. Read the M34.0 planning memo sections for M34.2

Read the following before touching acceptance code:

- **§5.b D5** — assertion helper defense: `total_count` over
  `.length`; scoped to `fetchSnapshotList` +
  `expectSnapshotCountAtLeast`; `fetchAllJournalEntries`
  untouched.
- **§5.b D7** — `@rerun-hygiene` tag on three
  `test.describe(...)` strings; `acceptance/README.md`
  invocation documentation for
  `npx playwright test --repeat-each=2 --grep "@rerun-hygiene"`;
  Option A locked at M34.0 open.
- **§5.b D8** — durable lesson (ff) verbatim text and
  placement (`docs/CAPABILITY_MATRIX.md` §7 durable-lessons
  + M34 retrospective §5).
- **§5.e M34.2** — file paths + acceptance suite target
  (25 spec files / 32 tests / ≤37s with +2s budget for seed
  reset overhead).
- **§5.f** — DoD exception path continuation rationale.
- **§5.h** — non-goals (no product-code; no spec step
  changes; no assertion weakening; no shared helper).

### 3. Ship M34.2 acceptance substrate

Per M34.0 §5.e M34.2:

- **Refactor
  `acceptance/support/assertions/accounting.ts` per D5:**
  - Change `fetchSnapshotList` return shape to
    `{ snapshots, totalCount }`.
  - `expectSnapshotCountAtLeast` asserts against
    `totalCount` (not `snapshots.length`).
  - Journey `accounting_workflow.spec.ts` needs a small
    update to consume the new return shape at the
    `snapshotsBefore` and `snapshotsAfter` sites (this is
    the ONLY allowed journey-code touch — see §5.h).
  - Actually per §5.h "Do NOT modify the three journey
    `.spec.ts` files' step logic, timeouts, waits, or
    assertions" — the shape update is a mechanical consumer
    change, not a step-logic change. Document explicitly in
    §2 of the M34.2 handoff which lines changed and why they
    are within-scope. Consider an alternative: preserve the
    old return shape as `snapshots: TrialBalanceSnapshotSummary[]`
    (a plain array) and add a separate
    `expectSnapshotTotalCountAtLeast` helper that fetches
    `total_count`. This preserves journey code verbatim.
    Evaluate at M34.2 open; recommend the preserve-shape
    approach to minimize scope.
  - `fetchAllJournalEntries` untouched (M22.2 JE-reversal
    journey unaffected).
- **Add `@rerun-hygiene` tag to three spec files per D7:**
  - `acceptance/journeys/sales_manager/daily_startup.spec.ts`
  - `acceptance/journeys/recon/workflow.spec.ts`
  - `acceptance/journeys/office/accounting_workflow.spec.ts`
- **Update `acceptance/README.md`:** add developer-side
  invocation per D7 Option A. If README doesn't exist,
  create it minimally (title + this invocation section).
- **Run repeated-run proof locally:**
  `cd acceptance && npx playwright test --repeat-each=2 --grep "@rerun-hygiene"`.
  Record pass output verbatim in the M34.2 handoff §7.

### 4. Ship M34 close-out fold

- **Create `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md`** with
  §1–§9 following the M33 retrospective shape. Key content:
  - §5 candidate durable lessons: (ff) verbatim per M34.0
    D8; (cc) elevation-to-load-bearing note.
  - §9 evidence-based candidates for M35 (same list as M34
    §9 minus H which now ships at M34).
- **Update `docs/CAPABILITY_MATRIX.md`:** add §7ι M34
  shipped surface entry; add (ff) to durable-lessons
  narrative; note (cc) elevation.
- **Flip `docs/roadmap/MILESTONE_34_PLANNING.md` frontmatter
  `status: active` → `status: historical`.**
- **Overwrite `00-START-NEXT-SESSION.md`** for SESSION_216
  M35.0 planning per the standard cadence.

### 5. Verify M34.2 close baselines

- `python3 manage.py test dealer_ai` → **5,021 pass** unchanged
  (M34.2 does not touch backend).
- Frontend Vitest: unchanged at 402 pass.
- Acceptance suite: 25 spec files / 32 tests / ≤37s
  (measure at close; note timing budget).
- Audit artifact: **162 / 131 / 31 / 321 unchanged**.

### 6. DoD exception path — tenth invocation

Document in §3 of M34.2 handoff:

> M34.2 is acceptance-workspace-only (helper refactor + tag
> + README + close-out documentation). Zero operator-visible
> behavior. Tenth invocation of DoD exception path (M26 +
> M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 +
> M34.1 + M34.2). Existing three journeys preserve their
> operational contract; M34.2 makes the contract rerun-safe
> without adding a new customer-facing journey.

### 7. Ship the M34.2 handoff + coordinate M34 push

- `docs/handoffs/SESSION_215_m34_inc2_acceptance.md`.
- **Coordinated M34 push at close** after explicit user
  confirmation. Expected commits at push: **4–6**.

## Non-goals for SESSION_215

- ❌ Do NOT modify any backend / product-code file (views,
  services, models, permissions, URLs, migrations,
  schemas). M34.2 is acceptance-workspace only.
- ❌ Do NOT modify the three journey `.spec.ts` files' step
  logic, timeouts, waits, or assertions. The only allowed
  touch is adding `@rerun-hygiene` to `test.describe(...)`;
  if the D5 helper refactor requires shape changes to
  journey call sites, prefer the preserve-shape alternative
  (see §3).
- ❌ Do NOT introduce a shared reset helper across seed
  commands (per M34.0 §5.b D1 no-abstraction discipline).
- ❌ Do NOT modify the shipped M32.3 Intake Iris or M33.2
  Structure Sam fixtures — already independently rerunnable
  per M32 D11 + M33 R7.
- ❌ Do NOT add sleeps, retries, or weaken assertions.
- ❌ Do NOT change the CI workflow to add DB persistence,
  parallelization, or repeated-run gating (Option B is
  deferred; Option A locked at M34.0).
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT skip the DoD exception path documentation in §3
  of the handoff.
- ❌ Do NOT skip the local `--repeat-each=2` proof — its
  output is the M34.2 handoff §7 evidence.
- ❌ Do NOT push without explicit user confirmation.
- ❌ Do NOT modify M35 candidate list unless M34 evidence
  materially alters urgency.

## Baseline expected at close

- Backend suite: 5,021 pass unchanged (M34.2 no backend
  touch).
- Frontend: Vitest 402 pass unchanged.
- Acceptance: 25 spec files / 32 tests unchanged in count;
  timing ≤37s with +2s seed-reset budget.
- Audit: **162 / 131 / 31 / 321 unchanged**.
- Permission classes: 7 (zero-drift streak advances 37 →
  **38** at M34 close).
- Migrations: unchanged (M34 adds none).
- **M34 shipped** at SESSION_215 close.

## NEXT TASK

Start SESSION_215 with (a) starting-state verification;
(b) read M34.0 planning memo §5.b D5 + D7 + D8 + §5.e M34.2
+ §5.f + §5.h; (c) refactor `accounting.ts` helper per D5
(evaluate preserve-shape alternative to minimize journey
touch); (d) add `@rerun-hygiene` tag to the three specs;
(e) update `acceptance/README.md` with developer invocation;
(f) run repeated-run proof locally and record output verbatim;
(g) ship M34 close-out fold (retrospective + CAPABILITY_MATRIX
§7ι + planning-memo flip + start-next flip); (h) verify
baselines; (i) DoD exception path documentation in §3;
(j) ship the M34.2 handoff at
`docs/handoffs/SESSION_215_m34_inc2_acceptance.md`;
(k) **coordinated M34 push at close after explicit user
confirmation**.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_34_PLANNING.md`** (governing
   contract for M34 — read §5.b D5 + D7 + D8 + §5.e M34.2 +
   §5.h before code)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (unchanged
   at M34.1 close — 162 / 131 / 31 / 321)
8. `docs/CAPABILITY_MATRIX.md` §7θ (M33 shipped surface);
   §7ι added at M34 close
9. `docs/handoffs/SESSION_213_m34_inc0_planning.md` (M34.0
   planning close)
10. `docs/handoffs/SESSION_214_m34_inc1_seeds.md` (M34.1
    backend close)
11. `docs/handoffs/SESSION_212_m33_inc2_frontend.md` (M33.2
    shipped + M33 close-out fold — pattern reference for
    M34 close-out fold shape)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs D1 no-shared-helper discipline;
    honored at M34.1 and continues at M34.2)
13. Memory record
    `feedback_playwright_as_operational_contract.md` (M34.2
    adds the acceptance-side rerun-safety proof to the
    operational contract)
14. Memory record `feedback_terminal_output_discipline.md`
    (governs implementation-session output shape)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_214 — Milestone 34 · Increment 1 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged since M32.1). Test baseline:
  **5,021 pass**, 1 skipped, 0 fail (+6 vs M33.2 close
  baseline of 5,015).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 402 pass** across
  45 test files (unchanged).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **25 journeys** total (unchanged M34.1).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `3a83584` (M33.2 hash-backfill):
  **success in 3m8s** at 2026-08-05T04:20:13Z.
- **Async runtime:** unchanged (Celery 5.5.3 + Redis 6.4.0
  + `django-celery-beat` 2.8.1 DatabaseScheduler).
- **Milestones shipped:** M1 → **M33**. M34.0 planning
  shipped at SESSION_213; M34.1 backend seeds + tests
  shipped at SESSION_214; M34.2 acceptance + close-out
  pending.
- **DRF admin surface:** **122** endpoints (unchanged M34.1).
- **Frontend operator routes:** **21** (unchanged M34.1).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged M34.1).
- **Frontend surfaces:** unchanged M34.1.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-seven consecutive milestones** (M10 → M33).
  M34 projected: 38 at close.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 34 status:** M34.0 SHIPPED (planning); M34.1
  SHIPPED (backend seeds + tests); M34.2 pending.
- **Audit tooling status:** unchanged from M26.1. Coverage
  **131 / 162** (unchanged at M34.1 close). M34 projection:
  unchanged (M34 adds no endpoints).
- **Playwright personas:** **6 actual** (unchanged M34.1).
- **Playwright fixtures:** unchanged M34.1 — Intake Iris
  (M32.3) + Structure Sam (M33.2) remain independently
  rerunnable per M32 D11 + M33 R7.
- **Seed rerun-safety** (M34.1): three
  `seed_journey_*` commands now restore pre-flight
  invariants across mutate → re-seed cycles:
  `seed_journey_sales_manager_daily_startup` (4 invariants
  — unassign + BeBack delete + non-24hr cadence delete +
  24hr cadence re-activate); `seed_journey_recon_workflow`
  (1 invariant — ReconDecision delete on seeded finding);
  `seed_journey_office_accounting_workflow` (1 invariant
  — TrialBalanceSnapshot wipe on fixture dealership under
  M20_ACCEPTANCE_DB env-guard).
- **§9 evidence for M35:** unchanged from M33 §9 minus H
  (F&I depth-arc candidates: NEW C chargeback substrate,
  Lender Fit Recommendations, NEW F&I workflow-state
  extensions, NEW F&I-scoped lead-context view, NEW
  cross-lead pending-approval queue; deferrals: direct-
  create structuring, iteration UX, PATCH on DealStructure;
  NEW O2 + NEW O3 unchanged; plus gated T/U/L/M, deferred
  D, deferred stable G, plus M33 §3 + M32 §3 + prior
  deferrals). H closes at M34.
- **Planning-time streak: 12 → 13** projected at M34.2 close
  (unchanged at M34.1; §0.a coverage-projection
  truthfulness correction is per-M34.1 §0.a convention not
  streak-affecting).
- **(cc) durable lesson elevated to load-bearing-across-
  two-milestones** at M34.1 on second re-application (M33.1
  origin: coverage-projection truthfulness on M33.0 §5.e
  projection; M34.1 second: test-count overshoot vs M34.0
  §5.e projection). Elevation triggered per SESSION_212
  M33 §5 candidate-elevation convention.
- **DoD amendment (M21.0 §5.f Option B):** ninth invocation
  of exception path at M34.1. M34.2 tenth invocation
  projected. First fully non-customer-facing milestone
  since M20.
- **M33 audit coverage at close:** 162 endpoints, **131
  covered / 31 backend-only** (unchanged at M34.1 close).
- **Durable lessons carried into M35+:** all (a)–(ee) plus
  M34.0-origin candidate (ff) *Acceptance journeys must be
  independently rerunnable against shared state; green-on-
  clean-DB alone is insufficient evidence of operational
  reliability.* (recorded verbatim per §5.b D8; awaits
  first re-application to elevate). (cc) elevated at M34.1
  to load-bearing-across-two-milestones.
