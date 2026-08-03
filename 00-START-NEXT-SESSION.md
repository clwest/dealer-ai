---
state: active
date: 2026-08-03
last_session_shipped: SESSION_190
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
next_session: SESSION_191
next_milestone: 27
next_milestone_name: "(target selection pending — locked at M27.0 open)"
next_increment: 0
next_increment_name: "M27.0 — Planning refinement + target selection"
---

# Next session — SESSION_191 · Milestone 27 · Increment 0 (M27.0 — planning refinement + target selection)

> **Milestone 26 — Audit-Script Parser Refinement
> (Planning-Substrate Integrity) — SHIPPED at SESSION_190.**
> Two-session milestone (SESSION_189 → SESSION_190). M26.2
> close-out folded into M26.1 per §5.h Option B — no code
> discrepancies at any §5.d checkpoint. **Backend baseline
> 4,793 → 4,805 (+12 regression tests). Audit coverage
> 114 / 154 → 119 / 154** (five nested-template-literal false
> positives correctly recognized post-fix; row 5 remains
> `defer-candidate-O2` per M26.1-open empirical refinement —
> separate `getJSON` public-helper defect deferred to M27+).
>
> **§5.d two-source agreement confirmed** at 119 / 154 across
> all four recording sites: `CAPABILITY_MATRIX.md` §7α,
> `IMPLEMENTATION_ROADMAP.md` §Milestone 26,
> `MILESTONE_26_RETROSPECTIVE.md` §2 + §7, this doc's
> operational-state block.
>
> **Zero-drift permission-class streak extends 25 → 26**
> consecutive milestones (M10 → M26). Zero endpoints added.
>
> **Planning-time as-recommended streak reached 5** (was 3 at
> M25 close; +1 at M26.0 with target locked as recommended
> after 3-tier framing + 5 scope-discipline constraints; +1
> at M26.1 with M26.1-open row-5 empirical refinement counted
> as as-recommended because it narrowed evidence without
> shifting target). Historical run of 89 across M10 → M23
> preserved for the record.
>
> **Coordinated push at M26 close pending.** M26.1 shipped
> the parser fix, regression suite, audit regeneration, all
> §5.e doc updates, retrospective, this start-here overwrite,
> and the M26.1-close handoff. Awaits explicit user
> confirmation before push. Expected M26 commits at push:
> 4 (M26.0 planning + hash backfill + M26.1 close + hash
> backfill).
>
> **Three durable design principles surfaced or reinforced
> at M26** (see `MILESTONE_26_RETROSPECTIVE.md` §5):
> (a) *empirical-discovery refinements preserve streak
> integrity when the target does not shift* — reinforced
> for the fourth time in the M24–M26 arc;
> (b) *two-source agreement (§5.d Phase 1 diff + Phase 2
> per-row verification) is the mechanical guard against
> baseline drift* — reinforced by catching the row-5
> misclassification before it hit the record;
> (c) *DoD exception path (M21.0 §5.f Option B) applies
> cleanly to infrastructure-focused milestones* — new at
> M26; audit-tooling / test-hygiene / CI-infrastructure
> milestones can cite this precedent.
>
> **Three NEW M27+ candidates surfaced during M26** (all
> deferred per user constraints or empirical discovery):
> (a) **Row 5 public-fetch-helper regex refinement** —
> extend `_HELPER_CALL_RE` to include public helpers
> (`getJSON` / `postJSON` / etc.), OR broaden
> `_PUBLIC_FETCH_RE` filters; blast radius unknown
> pre-tracing;
> (b) **Plain-string-literal false-positive investigation
> (rows 1–4)** — surfaced at SESSION_189 §3, likely
> `component_consumed` word-boundary check;
> (c) **A2 (JE creation UI)** — kept elevated per user
> constraint as leading M27 §5.a direct operator-coverage
> candidate. Row 140 `admin/accounting/journal-entries/`
> create endpoint remains genuinely uncovered post-M26.
>
> **SESSION_191 opens M27.0 — planning refinement + target
> selection.** No target locked yet — the candidate list
> surfaces at open (elevated: A2, NEW row-5 public-helper
> refinement, NEW rows-1–4 plain-string investigation, H
> test-hygiene; gated: T / U / L / M; deferred pending
> evidence: D / C; deferred stable: G; plus all M25 §4
> deferrals still valid). The assistant recommends one
> option with rationale grounded in the durable primary
> operational-coverage lens (or a reframe if evidence
> supports it); the user confirms or redirects.

## First thing SESSION_191 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches `origin/main`
  post-M26 push (if pushed) OR local `HEAD` ahead by 4
  commits (M26.0 planning + hash backfill + M26.1 close +
  hash backfill) if push not yet executed.
- `git log --oneline -10` — top should be the M26.1
  hash-backfill commit; four M26 commits total.
- `python3 manage.py test dealer_ai` → **4,805 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **226 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. If M26 pushed — monitor first M26 CI run

If M26 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M27.0 amendments before opening
§5.a.

**If green:** M26 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

Before candidate presentation, rerun the audit tooling to
confirm the M26.1 baseline holds:

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **154 total / 119 covered / 35 backend-only /
312 service verbs**. If the artifact drifts from this,
investigate before scope-locking.

### 4. Present the M27 candidate list

Per the M26 retrospective §9 evidence:

**Elevated (highest recommendation strength at M27.0):**

- **A2 — Journal-Entry creation UI.** Direct operator-
  coverage gain. Row 140 `admin/accounting/journal-entries/`
  create endpoint uncovered; reverse / retrieve / list
  wrappers all ship. Small population × moderate frequency;
  small scope; single-increment-shaped.
- **NEW Row 5 public-fetch-helper regex refinement.** Extend
  `_HELPER_CALL_RE` to include public helpers, OR broaden
  `_PUBLIC_FETCH_RE` filters. Blast radius unknown; requires
  SESSION-189-§3-style tracing at M27.0 open.
- **NEW Rows 1–4 plain-string-literal investigation.**
  Requires tracing at M27.0 open to determine root cause
  (likely `component_consumed` word-boundary check).
- **H — test-hygiene remediation.** 3 shared-DB
  non-idempotent journeys. High compound value as suite
  grows. Not operator-facing directly.

**Gated (unchanged from M25 close):**

- **T** — process real tester feedback.
- **U** — hosted-demo substrate.
- **L** — first-live-pilot staging.
- **M** — multi-operator support (breaks zero-drift
  streak with intent).

**Deferred pending evidence (unchanged):**

- **D** — LLM router / cost caps.
- **C** — F&I chargeback substrate.

**Deferred but stable:**

- **G** — dashboard testid hardening.

**Deferred at M25 §4 (all valid for later re-entry):**

Secondary "+ Record test drive" launch point on
`DealerAiSalesTestDrives`; clickable "Referred by"
attribution navigation; named-platform webhook adapters
(Autotrader / Cars.com / etc.) — JSONField substrate
ready; attribution analytics / rollups; vehicle picker
advanced filters.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the
recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** ("which candidate most increases
operational coverage for a dealership employee?") OR its
reframe (planning-substrate integrity, per M26 precedent)
if evidence supports it.

Elevated candidates evaluated under the primary lens:

- **A2 (JE creation UI)** — direct operator-facing; small
  population × moderate frequency; small scope. Wins on
  strict operator-coverage grounds.
- **NEW row-5 audit refinement** — indirect (accuracy of
  roadmap-planning substrate). Very small scope. Wins on
  compound-infrastructure grounds ONLY if M26 didn't
  fully correct the audit drift.
- **NEW rows-1–4 investigation** — indirect; scope
  unknown pre-tracing.
- **H (test-hygiene)** — indirect (CI stability); high
  compound value as suite grows.

**Judgment call for M27:** M26 already spent a bounded
audit-tooling milestone; whether M27 should spend another
depends on whether the row-5 or rows-1–4 defects would
compound before A2's operator gain lands. Present both
framings and let the user pick.

**Alternatively:** if the M26 CI run surfaces regression
work at M27.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard six-to-eight
load-bearing decisions.

### 7. Verify BOTH intake AND downstream UI surfaces before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 durable lesson reinforced across M24
through M26.** Every planning-open surface verification
must cover both intake AND downstream paths, including
audit-substrate accuracy checks when audit is
load-bearing on the selection.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M27 active memo §3
must either name a Playwright journey addition or
extension OR explicitly document why no journey change
is required (M26 precedent for the exception path).

### 9. Expand M27 planning skeleton

Draft fresh per the standard active-memo shape (no
existing skeleton at close of M26).

### 10. Ship the M27.0 handoff

- `docs/handoffs/SESSION_191_m27_inc0_planning.md`.
- **Do NOT push** — M27.0 is planning only; coordinated
  push at M27 close.

## Non-goals for SESSION_191

- ❌ Do NOT ship any backend or frontend code — planning-
  only session.
- ❌ Do NOT open any M27 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M26 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI
  regression fixes land as §0.a M27.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the downstream / substrate verification
  (M24–M26 durable lesson).

## Baseline expected at close

Backend + frontend unchanged from M26 close. Acceptance
suite unchanged. Only planning docs change.

## NEXT TASK

Start SESSION_191 with (a) starting-state verification,
(b) if M26 pushed, monitor first M26 CI run + fix any
regressions as §0.a M27.0 amendments, (c) regenerate the
audit artifact and confirm 119/154 holds, (d) present
the candidate list with recommendation + rationale
under the primary operational-coverage lens (or
substrate-integrity reframe if evidence supports it),
(e) await user confirmation of §5.a, (f) draft
§5.b–§5.h, (g) DoD compliance check on §3 draft,
(h) expand the M27 planning memo, (i) ship the M27.0
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M26 shipped section landed at M26.1)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md`
   §3 (deviations) + §5 (durable lessons) + §9
   (standing M27 question)
6. `docs/roadmap/MILESTONE_26_PLANNING.md`
   (M26 governing contract + all §5 locks +
   SESSION_189 §3 + SESSION_190 §2 empirical
   discovery record)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M26 baseline — 154 endpoints /
   **119 covered** / 35 backend-only)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped
   surface) + §7α (M26 audit-tooling refinement)
9. `docs/handoffs/SESSION_190_m26_close.md`
   (M26.1 shipped + M26.2 close-out fold)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_190 — Milestone 26 SHIPPED)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0049`. Test baseline: **4,805
  pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 226 pass** across 32 test
  files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **14 journeys** passing
  end-to-end on clean DB. Full dry-run baseline:
  **20 passed (~30s)** (6 setup + 14 journeys).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First real
  M26 CI run pending on the M26 push (executes at
  M26 close after explicit user confirmation).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M26**. M27
  target selection pending (SESSION_191).
- **DRF admin surface:** **114** endpoints
  (unchanged — M26 added zero endpoints).
- **Frontend operator routes:** 20 (unchanged).
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** all M1–M26 packages
  unchanged. Zero M26 service verbs (M26 is
  audit-script-only).
- **Frontend surfaces:** unchanged (M26 does not
  touch `frontend/src/`).
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** —
  zero-drift streak **twenty-six consecutive
  milestones** (M10 → M26).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages
  (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 26 status:** SHIPPED (SESSION_190
  close-out landed all documentation + status
  flips + M27 handoff + coordinated close-out
  session-local commits, awaits explicit user
  push confirmation).
- **Audit tooling status:** M26.1 corrected the
  nested-template-literal defect via post-match
  refinement of `extract_frontend_consumers` +
  extracted shared substrate
  `_extract_balanced_template_literal`. Coverage
  114 / 154 → **119 / 154** (real). 12 regression
  tests in `test_audit_operational_surface.py`
  guard the fix. §5.d Phase 2 per-row manual
  verification passed for all 5 flipped rows
  (7, 16, 29, 111, 121). Row 5 remains
  `defer-candidate-O2` per M26.1-open empirical
  refinement (separate `getJSON` public-helper
  defect deferred to M27+). Row 42
  `admin/vendors/` cosmetic wrapper-reorder in
  M26.1 audit regen (deterministic script
  output).
- **§9 evidence for M27:** A2 elevated (leading
  direct operator-coverage candidate); NEW row-5
  public-fetch-helper regex refinement (surfaced
  M26.1 open); NEW rows-1–4 plain-string
  investigation (surfaced SESSION_189 §3); H
  test-hygiene (unchanged from M25); plus gated
  T/U/L/M, deferred pending evidence D/C,
  deferred stable G, plus all M25 §4 deferrals.
- **Planning-time streak: 5** (at M26.1 close;
  extends M25 close of 3 through M26.0 + M26.1
  as-recommended increments; historical run of
  89 across M10 → M23 preserved for the record).
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or
  update at least one Playwright operational
  journey, or explicitly document in §3 why no
  journey change is required. M26 invoked the
  exception path (audit-tooling / infrastructure
  focus); future infrastructure milestones can
  cite the M26 precedent.
- **M26 audit coverage at close:** 154 endpoints,
  **119 covered / 35 backend-only** (was 114 / 40
  pre-fix; §5.e two-source agreement confirms
  these are the true coverage numbers).
- **Durable lessons carried into M27:** (a) one
  operational workflow beats two overlapping
  (M25.0 §5.d origin); (b) planning-open
  verification must cover persistence path (M25.0
  §5.b + M25.2 §5.e origin); (c) additive-forever
  JSONField beats CharField (M25.0 §5.b origin);
  (d) record empirical-discovery refinements
  honestly (M25.0 + M25.2 + SESSION_189 §3 +
  SESSION_190 §2 origin; four reinforcements
  across M24–M26); (e) modal-attached collapsible
  + success badge > toast (M25.2 origin); (f)
  dependency-injectable helpers over network
  mocks in unit tests (M25.2 origin); (g) audit
  correctness is supporting infrastructure — every
  accuracy gain compounds (M25.3 → M26 origin);
  (h) two-source agreement (§5.d Phase 1 diff +
  §5.d Phase 2 per-row verification) is the
  mechanical guard against baseline drift (M26.1
  origin); (i) DoD exception path applies cleanly
  to infrastructure-focused milestones (M26
  origin — first post-M21.0 exception invocation).
