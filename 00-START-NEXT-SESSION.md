---
state: active
date: 2026-08-05
last_session_shipped: SESSION_215
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
next_session: SESSION_216
next_milestone: 35
next_milestone_name: "(target selection pending — locked at M35.0 open)"
next_increment: 0
next_increment_name: "M35.0 — Planning refinement + target selection"
---

# Next session — SESSION_216 · Milestone 35 · Increment 0 (M35.0 — planning refinement + target selection)

> **Milestone 34 — Test-Hygiene Remediation — SHIPPED at
> SESSION_215.** M34.0 planning + M34.1 backend seeds + tests
> + M34.2 acceptance helper defense + `@rerun-hygiene` tag +
> close-out fold all landed. Backend baseline 5,015 → 5,021
> (+6 M34.1). Frontend Vitest 402 unchanged. Acceptance 25
> spec files / 32 tests unchanged in count; repeated-run
> proof at M34.2 close 10 passed / 19.9s first + 10 passed
> / 15.9s second. Audit unchanged 162 / 131 / 31 / 321.
>
> **Zero-drift permission-class streak advanced 37 → 38
> consecutive milestones** (M10 → M34). Planning-time as-
> recommended streak reached **13** at M34.0 with **zero
> correction rounds** — first M34-series planning cycle
> requiring no revisions.
>
> **Six-milestone H deferral closed** — H persisted M27.2 →
> M33.2 as an unchanging deferral in every retrospective's
> §9. M34 closes it. First fully non-customer-facing
> milestone since M20 (13 consecutive customer-facing
> milestones M21 → M33 broken intentionally per M33 §9
> "close a deferral" resolution).
>
> **Two §0.a corrections within M34** (M34.1 test count
> overshoot 3 → 6; M34.2 D7 proof mechanism `--repeat-each`
> vs back-to-back). Both belong to the (cc) coverage-
> projection truthfulness class extended at M34.2 to also
> cover planning-time claims about testing/tooling behavior.
> **(cc) elevated to load-bearing-across-three-milestones**
> (M33.1 origin + M34.1 + M34.2 — first lesson to reach
> three-milestone load-bearing status).
>
> **New candidate durable lesson `(ff)` locked at M34.0 D8
> verbatim per user directive:** *Acceptance journeys must
> be independently rerunnable against shared state; green-
> on-clean-DB alone is insufficient evidence of operational
> reliability.* Awaits first re-application to elevate.
>
> **§9 evidence for M35** (per M34 retrospective §9):
> **unchanged from M33 §9 minus H (shipped)**. All F&I
> depth-arc candidates remain evidence-gated; NEW O2 + NEW
> O3 now 9-milestone deferrals; gated T/U/L/M unchanged;
> deferred D + stable G unchanged.
>
> **Standing question at M35.0** (per M34 §9): the F&I depth
> arc's 2-link run paused intentionally at M34 for the
> deferral-close. Three natural next moves: (a) **continue
> the F&I depth arc** via NEW C chargeback (third link if
> pilot evidence surfaces) OR NEW F&I workflow-state
> extensions OR Lender Fit Recommendations (if operator
> evidence surfaces on lender selection); (b) **reset to
> breadth** via a fresh direct-operator gap; (c) **close
> another §3 deferral** (M34 precedent: deferral-close
> milestones are a legitimate value-shipping mode when the
> deferral has compound value).
>
> **Meta-observation for M35 planning per M34 retrospective
> §9:** M34 demonstrated that "close a deferral" can be a
> highly productive milestone choice when the deferral has
> genuine compound value. If M35 opens with no fresh operator
> evidence for depth-arc continuation, closing another §3
> deferral is a valid target per M34 precedent — not a
> "fallback."
>
> **Coordinated M34 close push pending.** All M34 work is
> local-only; awaits explicit user confirmation. Expected
> M34 commits at push: **6** — M34.0 planning (`f163e93`);
> M34.0 hash-backfill (`a03c5eb`); M34.1 backend
> (`9abd0ad`); M34.1 hash-backfill (`09d1299`); M34.2 +
> close-out fold (this session); M34.2 hash-backfill
> (follow-up).
>
> **SESSION_216 opens M35.0 — planning refinement + target
> selection.** The assistant recommends one option with
> rationale grounded in the durable primary operational-
> coverage lens; the user confirms or redirects.
> Verification-driven revision cycles at planning-open
> discipline (z — now load-bearing across three milestones
> including M34.0 zero-revision invocation) anticipates
> user revision rounds strengthening the locked design if
> they surface (but does not require them if the tracing
> at open is thorough enough).

## First thing SESSION_216 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M34 push (if pushed) OR local `HEAD`
  ahead by 6 commits (SESSION_213–215 planning + impls +
  hash-backfills + close-out fold) if push not yet executed.
- `git log --oneline -10` — top should be the M34.2 hash-
  backfill commit; check for expected M34 commit sequence.
- `python3 manage.py test dealer_ai` → **5,021 pass, 1
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

### 2. If M34 pushed — monitor first M34 CI run

If M34 has been pushed, verify the CI acceptance workflow
status via:

```bash
gh run list --workflow=acceptance --branch=main --limit 5
gh run view <run-id> --log
```

**If red:** address as §0.a M35.0 amendments before opening
§5.a.

**If green:** M34 is CI-verified shipped; proceed to §3.

### 3. Regenerate the audit artifact

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Expected: **162 / 131 / 31 / 321** unchanged (M34 adds no
endpoints). If the artifact drifts, investigate before
scope-locking.

### 4. Present the M35 candidate list

Per the M34 retrospective §9 evidence:

**Elevated (highest recommendation strength at M35.0):**

- **NEW C — F&I chargeback substrate.** Third-link F&I depth-
  arc candidate. Still pilot-evidence gated. Post-M33
  operator context strongest yet.
- **Lender Fit Recommendations.** D10 elevation from M33; 3
  of 4 blockers remain.
- **NEW F&I workflow-state extensions beyond M33's two
  derived states.**
- **NEW F&I-scoped lead-context view** (unchanged M32/M33
  §3 deferral).
- **NEW cross-lead sales-manager pending-approval queue
  page** (unchanged M32/M33 §3 deferral).
- **Direct-create CA structuring branch** — M33 explicit
  deferral.
- **Iteration UX** — M33 D9 deferral.
- **PATCH on DealStructure** — activation-vocabulary-
  asymmetry preservation.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (9-milestone deferral).
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (9-milestone deferral).

**Shipped since M33 §9:**

- ~~**H — Test-hygiene remediation.**~~ SHIPPED at M34.

**Fresh direct-operator gaps to survey (breadth candidates):**
vendor detail (#43); photo reorder (#65); broader F&I
subdomain (#89–101 excluding chargeback = 11 uncovered
post-M34).

**Gated:** T, U, L, M.
**Deferred pending evidence:** D.
**Deferred but stable:** G.
**Deferred at M34 §3 / M33 §3 / M32 §3 / M31 §3 / M30 §3 /
M29 §3 / M28 §3 / M27 §3 / M25 §4:** all carried forward
unchanged.

Present each with two-sentence scope + operator pain
resolved + dependency notes, then present the recommendation.

### 5. Recommend a target for §5.a

Ground the recommendation in the **primary operational-
coverage lens** OR its reframes (F&I depth-arc continuation
per M32 + M33 precedent; "close a deferral" per M34
precedent) if evidence supports.

**Standing question from M34 retrospective §9:** three
natural next moves — (a) continue F&I depth arc via NEW C
chargeback OR NEW F&I workflow-state extensions OR Lender
Fit Recommendations (if evidence surfaces); (b) reset to
breadth via a fresh direct-operator gap; (c) close another
§3 deferral (per M34 precedent — deferral-close is a
legitimate value-shipping mode). Evaluate through the
primary operational-coverage lens first; secondary reframes
only if evidence surfaces.

**Alternatively:** if the M34 CI run surfaces regression
work at M35.0, address as §0.a amendments first.

### 6. Draft §5.b–§5.h load-bearing decisions

Once §5.a locks, draft the standard load-bearing decisions
per M28/M29/M30/M31/M32/M33/M34 shape.

### 7. Verify BOTH intake AND downstream UI surfaces + FK discoverability before locking §5.b + §5.d

**M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 + M29.0 §7 + M30.0 §7
+ M31.0 §7 + M32.0 §4 + M33.0 §4 + M34.0 §4 durable
lesson.** Every planning-open surface verification must
cover both intake AND downstream paths, including audit-
substrate accuracy checks + FK / identifier discoverability
for any create/edit workflow candidate + role-access
verification for any cross-role UI + field-level
prepopulation truthful-entry check for any form candidate.

**Verification-driven revision cycles discipline (z — now
load-bearing across three milestones)** — multiple user-
directed revision rounds at §5.b–§5.h before scope-lock are
acceptable and often strengthen the milestone; do not batch
objections into one revision round. M34.0 applied zero
rounds (thorough tracing at open resolved ambiguity inline);
this is a valid outcome of (z), not an abdication.

**Coverage-projection truthfulness (cc — load-bearing-
across-three-milestones after M34)** — at §5.e phase-
projection lock AND at §5.b tool-usage/proof-mechanism
claim locks, name the specific semantic being invoked and
validate the projection/claim against a concrete recent
precedent OR an empirical test before locking scope.

**(ff) rerun-safety-against-shared-state as operational-
reliability contract** — at planning-open verification for
any journey add or extension, name concrete invariants the
journey depends on and confirm the seed restores them
across mutations the journey applies.

### 8. DoD compliance check

Per the M21.0 §5.f amendment: the M35 active memo §3 must
either name a Playwright journey addition or extension OR
explicitly document why no journey change is required (M26
+ M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + M33.1 +
M34.1 + M34.2 precedents for the exception path — pattern
firmly established at ten invocations).

### 9. Expand M35 planning skeleton

Draft fresh per the standard active-memo shape (no existing
skeleton at close of M34).

### 10. Ship the M35.0 handoff

- `docs/handoffs/SESSION_216_m35_inc0_planning.md`.
- **Do NOT push** — M35.0 is planning only; coordinated push
  at M35 close.

## Non-goals for SESSION_216

- ❌ Do NOT ship any backend or frontend code — planning-only
  session.
- ❌ Do NOT open any M35 implementation increment.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M34 shipped surface.
- ❌ Do NOT modify the acceptance suite unless CI regression
  fixes land as §0.a M35.0 amendments.
- ❌ Do NOT skip the DoD compliance check.
- ❌ Do NOT skip the field-level truthful-entry check for any
  form candidate (per M33.0 §4.7 blocking-finding discipline).
- ❌ Do NOT re-litigate M34 seed idempotency contract or
  helper defense — locked at M34.0 and validated through
  M34.2 shipping.
- ❌ Do NOT re-open the D5 "preserve shape vs return `{snapshots, totalCount}`"
  design question — preserve-shape locked at M34.2.
- ❌ Do NOT modify the shipped M34 assertion helper contract
  (`expectSnapshotCountAtLeast` returns
  `TrialBalanceSnapshotSummary[]` while asserting against
  `totalCount` internally) — the contract is now project-
  wide, not just M34-scoped.
- ❌ Do NOT change the `@rerun-hygiene` tag string or the
  back-to-back invocation proof mechanism — both locked at
  M34.2 per D7 Option A + §0.a correction.

## Baseline expected at close

Backend + frontend + acceptance unchanged from M34.2 close.
Only planning docs change.

## NEXT TASK

Start SESSION_216 with (a) starting-state verification;
(b) if M34 pushed, monitor first M34 CI run + fix any
regressions as §0.a M35.0 amendments; (c) regenerate the
audit artifact and confirm 162/131/31/321 holds;
(d) present the candidate list with recommendation +
rationale under the primary operational-coverage lens
(with F&I depth-arc continuation vs breadth-reset vs close-
another-deferral framing per M34 §9 standing question);
(e) await user confirmation of §5.a; (f) draft §5.b–§5.h
with verification-driven revision cycles anticipated per
(z); (g) DoD compliance check on §3 draft; (h) expand the
M35 planning memo; (i) ship the M35.0 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_34_RETROSPECTIVE.md`** §5
   (three re-applied lessons including (cc) elevation to
   load-bearing-across-three-milestones) + §9 (M35
   candidate list origin + F&I depth-arc standing question
   preserved from M33)
6. `docs/roadmap/MILESTONE_34_PLANNING.md` (historical;
   governing contract for M34)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M34 baseline unchanged from M33 — **162 endpoints
   / 131 covered / 31 backend-only / 321 service verbs**)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α (M26) +
   §7β (M27) + §7γ (M28) + §7δ (M29) + §7ε (M30) +
   §7ζ (M31) + §7η (M32) + §7θ (M33) + **§7ι (M34 shipped
   surface)**
9. `docs/handoffs/SESSION_215_m34_inc2_acceptance.md` (M34.2
   shipped + M34 close-out fold)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — re-applied at M34.1 D1 for three-seed
    no-shared-helper discipline)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at M34.0 §4.5 for cascade
    behavior)
12. Memory record
    `feedback_playwright_as_operational_contract.md` (M34
    preserves the contract by making it rerun-safe;
    strengthening invocation)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_215 — Milestone 34 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0051` (unchanged since M32.1). Test baseline:
  **5,021 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 402 pass** across
  45 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS
  5.6 operational; **25 journeys** total (unchanged M34).
  Repeated-run proof at M34.2 close 10 passed / 19.9s + 10
  passed / 15.9s.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `3a83584` (M33.2 hash-backfill commit):
  **success in 3m8s** at 2026-08-05T04:20:13Z. First real
  M34 CI run pending on the M34 push.
- **Async runtime:** unchanged (Celery 5.5.3 + Redis 6.4.0
  + `django-celery-beat` 2.8.1 DatabaseScheduler).
- **Milestones shipped:** M1 → **M34**. M35 target
  selection pending (SESSION_216).
- **DRF admin surface:** **122** endpoints (unchanged at M34
  — M34 adds no endpoints).
- **Frontend operator routes:** **21** (unchanged at M34).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **321** verbs (unchanged at M34).
- **Frontend surfaces:** unchanged at M34 (M34 is infra-
  only).
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **thirty-eight consecutive milestones** (M10 → M34).
  M34 preserved the streak by construction (no new
  endpoints).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 34 status:** SHIPPED (SESSION_215 close-out
  landed all documentation + status flips + close-out
  session-local commit, awaits explicit user push
  confirmation for coordinated M34 push).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **131 / 162** (unchanged at M34 close — M34 adds no
  endpoints).
- **Playwright personas:** **6 actual** (unchanged M34).
- **Playwright fixtures:** unchanged M34 — Intake Iris
  (M32.3) + Structure Sam (M33.2) both still live and fully
  independent.
- **Seed rerun-safety (NEW at M34):** three
  `seed_journey_*` commands restore pre-flight invariants
  across mutate → re-seed cycles:
  `seed_journey_sales_manager_daily_startup` (4 invariants);
  `seed_journey_recon_workflow` (1 invariant);
  `seed_journey_office_accounting_workflow` (1 invariant
  under `M20_ACCEPTANCE_DB` env-guard).
- **Assertion helper defense (NEW at M34):**
  `expectSnapshotCountAtLeast` asserts against
  `total_count` internally; return type unchanged
  (preserve-shape) so M20.3 journey needs no consumer
  edits. Defense-in-depth against page-cap-vs-total_count
  drift.
- **Repeated-run proof mechanism (NEW at M34):** back-to-
  back `npx playwright test --grep "@rerun-hygiene"`
  invocations (setup runs each invocation; seeds fire;
  invariants restore). NOT `--repeat-each=2` (which
  doesn't re-invoke setup between repeats — M34.2 §0.a
  correction).
- **§9 evidence for M35:** unchanged from M33 §9 minus H
  (which shipped at M34). NEW C F&I chargeback substrate
  (pilot-evidence gated); Lender Fit Recommendations (3 of
  4 blockers remain); NEW F&I workflow-state extensions;
  NEW F&I-scoped lead-context view; NEW cross-lead pending-
  approval queue page; direct-create structuring branch;
  iteration UX; PATCH on DealStructure; NEW O2 + NEW O3
  (9-milestone deferral). Gated T/U/L/M. Deferred D.
  Deferred stable G. Plus M34 §3 + M33 §3 + M32 §3 + prior
  deferrals.
- **Planning-time streak: 13** (at M34.2 close; unchanged
  from M34.0 as-recommended; M34.1 + M34.2 both pure
  implementation with §0.a corrections that do not affect
  streak per convention; historical run of 89 across M10
  → M23 preserved).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least
  one Playwright operational journey, or explicitly
  document in §3 why no journey change is required. M26
  first invocation; M27.1 second; M28.1 third; M29.1
  fourth; M30.1 fifth; M31.1 sixth; M32.1 seventh; M33.1
  eighth; **M34.1 ninth; M34.2 tenth** (M34 as a whole is
  the first fully non-customer-facing milestone since M20).
- **M34 audit coverage at close:** 162 endpoints, **131
  covered / 31 backend-only** (unchanged throughout M34 —
  M34 adds no endpoints). Two-source agreement confirmed
  at both M34.1 and M34.2 close.
- **Durable lessons carried into M35+:** all (a)–(ee) plus
  M34-elevated (ff) *Acceptance journeys must be
  independently rerunnable against shared state; green-on-
  clean-DB alone is insufficient evidence of operational
  reliability.* (recorded verbatim per M34.0 §5.b D8;
  awaits first re-application to elevate). **(cc) elevated
  to load-bearing-across-three-milestones** at M34.2 (M33.1
  origin + M34.1 + M34.2 — first lesson to reach three-
  milestone load-bearing status). (z) verification-driven
  revision cycles at planning-open — third invocation at
  M34.0 with **zero revision rounds observed**, extending
  the discipline to include "the tracing at open should be
  thorough enough that revisions are minimized as an
  outcome, not required."
