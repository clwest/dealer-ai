---
title: "SESSION_213 handoff — Milestone 34 · Increment 0 (M34.0 — planning refinement + target selection)"
status: active
type: handoff
date: 2026-08-05
session: 213
milestone: 34
milestone_status: active
milestone_name: "Test-Hygiene Remediation: Idempotent seeds + rerun-safe acceptance journeys (three shared-DB non-idempotent journeys: sales_manager/daily_startup + recon/workflow + office/accounting_workflow)"
increment: 0
increment_status: shipped
commit: pending
commit_notes: "M34.0 planning session — local commit landing at close per M28.0 / M29.0 / M30.0 / M31.0 / M32.0 / M33.0 planning-only cadence; hash backfilled via a subsequent commit; NOT pushed. Coordinated M34 close push deferred to explicit user confirmation after M34.2 close."
---

# SESSION_213 — Milestone 34 · Increment 0 (M34.0 — planning refinement + target selection)

## What shipped

SESSION_213 opened as a planning-only session per the M33.2
close-out priorities in `00-START-NEXT-SESSION.md`. One
deliverable landed:

1. **M34.0 planning memo** authored at
   `docs/roadmap/MILESTONE_34_PLANNING.md` — target locked as
   **Test-Hygiene Remediation — idempotent seeds + rerun-safe
   acceptance journeys** (§5.a). User-confirmed after direct
   evaluation against ten alternatives (NEW C F&I chargeback
   substrate — still pilot-evidence gated; Lender Fit
   Recommendations — three blockers remain; NEW F&I workflow-
   state extensions — evidence-gated; NEW F&I-scoped lead-
   context view — evidence-gated; NEW cross-lead sales-manager
   pending-approval queue — evidence-gated; direct-create CA
   structuring branch — M33 explicit deferral; iteration UX —
   M33 D9 deferral; PATCH on DealStructure — activation-
   vocabulary-asymmetry preservation; NEW O2 / NEW O3 — 8-
   milestone deferral) plus three fresh direct-operator gaps
   (vendor detail #43, photo reorder #65, broader F&I #89–101).
   All §5.b–§5.h decisions locked (D1–D8; risk register R1–R9;
   verifications §4.1–§4.6; two-increment phasing; DoD
   compliance; rollback; non-goals). **Zero blocking findings**
   at §4 verification. **Zero corrections** required before
   §5.b lock — first M34 planning-open cycle with zero
   revisions.

No §0.a M34.0 amendments — the first M33 CI run on `3a83584`
(M33.2 hash-backfill commit) is green (workflow `30974838541`,
success in 3m8s at 2026-08-05T04:20:13Z); no regression to
correct.

Full active memo authored at
`docs/roadmap/MILESTONE_34_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean;
  `HEAD == origin/main @ 3a83584` (0 commits ahead — M33 push
  confirmed pre-session as 6 commits on `main`); Redis PONG;
  Django `check` clean; `makemigrations --check` clean;
  frontend `tsc --noEmit` clean; acceptance `tsc --noEmit`
  clean; backend suite **5,015 pass, 1 skipped, 0 fail**
  (170.958s); frontend Vitest **402 pass** (45 files, 7.95s);
  acceptance DB proactively reset per SESSION_200 §0.a durable
  lesson (v). All matches M33.2 close baseline exactly.
- **First M33 CI run monitored (§2):** acceptance workflow on
  `3a83584` (M33.2 hash-backfill commit, top of `main`)
  **completed success** in 3m8s at 2026-08-05T04:20:13Z. Prior
  runs on `main` all successful. Main is CI-verified shipped
  at the M33.2 baseline. No §0.a M34.0 amendment triggered.
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **162 total / 131 covered / 31 backend-only / 321
  service verbs**. Byte-identical to the committed M33.2
  artifact. Two-source agreement at M34.0 open.
- **Candidate list presented (§4)** across the M33 §9 tiers:
  - **Elevated (highest recommendation strength at M34.0):**
    NEW C — F&I chargeback substrate (still pilot-evidence
    gated with strongest-yet post-M33 context); Lender Fit
    Recommendations (D10 elevation — 1 of 4 blockers
    delivered by M33; 3 remain); NEW F&I workflow-state
    extensions (evidence-gated on state model); NEW F&I-
    scoped lead-context view (evidence-gated); NEW cross-
    lead sales-manager pending-approval queue (evidence-
    gated); direct-create CA structuring branch (M33 §5.h
    explicit deferral); iteration UX (M33 D9 deferral);
    PATCH on DealStructure (activation-vocabulary-asymmetry
    preservation); NEW O2 (8-milestone deferral, unchanged);
    NEW O3 (8-milestone deferral, unchanged); H — test-
    hygiene remediation.
  - **Fresh direct-operator gaps surveyed (breadth
    candidates):** vendor detail (#43 wrapper-only, small
    polish); photo reorder (#65 wrapper-only, small polish
    + D&D primitive selection); broader F&I subdomain
    (#89–101 excl. #101 chargeback — 11 uncovered post-
    M33, too large without direction).
  - **Gated:** T, U, L, M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - **Deferred at M33 §3 / M32 §3 / M31 §3 / M30 §3 / M29
    §3 / M28 §3 / M27 §3 / M25 §4:** all carried forward
    unchanged.
- **Recommendation (§5) and user confirmation:** H — Test-
  Hygiene Remediation, under the primary operational-coverage
  lens with "close a deferral" framing per M33 §9 standing
  question (F&I depth arc → continue vs reset vs close-a-
  deferral). Rationale:
  1. No M34 candidate has fresh operator evidence — every
     F&I candidate is evidence-gated; choosing any without
     evidence violates the *Build Around Operational
     Problems* project rule.
  2. H is the one candidate where the operational-coverage
     lens argues *now*, not "if evidence surfaces later" —
     three shared-DB non-idempotent journeys have persisted
     unchanged M27.2 → M33.2 (six milestones).
  3. Breadth pivot has no strong evidence either — the 26
     defer-candidate-O2 endpoints include auth / chat /
     vehicle endpoints where "direct operator wrapper" isn't
     the shape; the three named breadth gaps are wrapper-
     only polish or too-large-without-direction.
  4. F&I depth arc preservation — M34 breaks the M32+M33 2-
     link arc intentionally per M33 §9 standing question
     resolution ("close a deferral"). Arc remains primary
     continuation candidate for M35.

  User locked H for §5.a with ten scope constraints:
  1. Scope strictly to the three named journeys.
  2. For each, identify exact leaked state + root cause +
     smallest durable cleanup.
  3. Prefer deterministic seed/reset behavior over test-order
     dependence, broad DB wipes, or per-test hacks.
  4. Preserve parallel + rerun safety (four invariants).
  5. Do NOT hide failures via assertion-weakening, sleeps,
     retries, or full-DB-reset-between-tests.
  6. Add focused regression coverage.
  7. Any new failure discovered during repeated-run testing
     is in scope only if same non-idempotency class;
     otherwise record and defer.
  8. Use customer-facing DoD exception path explicitly.
  9. Record durable lesson verbatim.
  10. Keep operator-facing M35 candidate list unchanged unless
      M34 evidence materially alters urgency.

  User also directed: **tracing pass on all three journeys
  before writing the memo; stop for review if any require
  broader product-code changes.**
- **Tracing pass (per user directive):** performed on all
  three journeys. Findings:
  - `sales_manager/daily_startup` — three leak sources
    (assigned_to; be-back rows; 1wk cadence). Seed-only fix.
  - `recon/workflow` — one leak source (ReconDecision on
    seeded finding). Seed-only fix.
  - `office/accounting_workflow` — one leak source
    (TrialBalanceSnapshot count vs helper page cap at 10).
    Seed + helper dual defense.

  **Conclusion:** no product-code changes required for any of
  the three journeys. All corrections live in the three seed
  commands + one Playwright assertion helper. User approved
  the scoping and directed §5.b–§5.h draft.
- **§5.b–§5.h draft (per user directive):** eight design
  decisions (D1–D8), nine risks (R1–R9), six verifications
  (§4.1–§4.6, all CLEAN), two-increment phasing (M34.1
  backend + M34.2 acceptance), DoD compliance check
  (invocation #9 of exception path — first fully non-
  customer-facing milestone since M20), rollback plan
  (reverse ship order), non-goals (12 explicit for M34 + all
  prior carried unchanged).
- **All §5 locks confirmed by user.**

## 1. Verification results at open

- **git status:** clean; `HEAD == origin/main @ 3a83584` (0
  commits ahead — M33 push complete).
- **git log --oneline -10:** shows the expected M33 commit
  sequence (M33.2 hash-backfill `3a83584`; M33 close-out fold
  `622c51e`; M33.1 hash-backfill `1e0008f`; M33.1 backend
  `eb50f94`; M33.0 hash-backfill `e03d31c`; M33.0 planning
  `7b8f6b6`; M32.3 hash-backfill `2a1e359`; M32 close-out
  fold `9906938`; M32.2 hash-backfill `2d9bb30`; M32.2 UI
  `2ef039d`).
- **`python3 manage.py test dealer_ai`:** 5,015 pass, 1
  skipped, 0 fail (170.958s).
- **`cd frontend && npm test`:** 402 pass across 45 files
  (7.95s).
- **`python3 manage.py check`:** clean (4 benign DecimalField
  warnings — pre-existing, unchanged).
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **`cd frontend && npx tsc --noEmit`:** clean (no output).
- **`cd acceptance && npx tsc --noEmit`:** clean (no output).
- **`redis-cli ping`:** PONG.
- **`rm -f backend/db.acceptance.sqlite3`:** completed (no-op
  if absent) per SESSION_200 §0.a durable lesson (v).

All matches M33.2 close baseline exactly.

## 2. First M33 CI run

- **Workflow:** `acceptance` on `main`.
- **Latest run:** `30974838541` on `3a83584` (M33.2 hash-
  backfill commit, top of `main`).
- **Result:** completed / success.
- **Duration:** 3m8s total.
- **Prior runs on `main`:** all successful.

**M33 is CI-verified shipped.** No §0.a M34.0 amendment
triggered.

## 3. Audit regeneration

- **Command:** `python3 -m
  dealer_ai.scripts.audit_operational_surface`.
- **Output:** 162 total / 131 covered / 31 backend-only / 321
  service verbs.
- **Artifact write:**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
- **Diff:** none. Byte-identical to M33.2 committed baseline.

**Two-source agreement** at M34.0 open: audit numbers match
the M33.2 handoff frontmatter and the M33 §7θ anchor (162 /
131 / 31 / 321).

## 4. Candidate list presented at open

Per M33 retrospective §9. Full list documented in
`docs/roadmap/MILESTONE_34_PLANNING.md` §5.a "Alternatives
considered explicitly."

## 5. Recommendation and user confirmation

**Primary recommendation:** H — Test-Hygiene Remediation.

**Rationale under the primary operational-coverage lens with
"close a deferral" framing per M33 §9 standing question:**
see M34.0 planning memo §5.a for full rationale (four load-
bearing signals).

**User confirmation:** target locked; ten scope constraints
locked into §5.b–§5.h (verbatim in memo §5.a); tracing pass
directed before memo write; §5.b–§5.h draft approved.

**Zero corrections applied before §5.b lock.** First M34
planning-open cycle with zero revisions.

## 6. Verification pass (§4 of planning memo)

Six verifications performed at open. **Zero blocking
findings.**

- **§4.1 Journey trace — sales_manager/daily_startup:**
  CLEAN. Three leak sources (A/B/C) identified; seed-only
  fix via D2.
- **§4.2 Journey trace — recon/workflow:** CLEAN. One leak
  source (D) identified; seed-only fix via D3.
- **§4.3 Journey trace — office/accounting_workflow:**
  CLEAN. One leak source (E) identified; dual defense via
  D4 seed wipe + D5 helper.
- **§4.4 D4 scoped-wipe safety verification:** CLEAN.
  `M20_ACCEPTANCE_DB=1` env guard enforced; no cross-
  referenced usage outside the acceptance workspace.
- **§4.5 Model relationship + cascade verification:** CLEAN.
  `ReconDecision.finding` OneToOne with CASCADE — direct
  decision deletion does not affect finding; safe.
- **§4.6 DoD compliance check on §5.e:** CLEAN. M34 is
  infra-only; exception path invocation #9.

**Zero blocking findings.** First M34 planning-open cycle
with zero revisions required.

## 7. All §5 locks

Full detail in `docs/roadmap/MILESTONE_34_PLANNING.md`. Summary:

- **§5.a target:** Test-Hygiene Remediation (H).
- **§5.b decisions:** D1 (seed idempotency contract);
  D2 (sales-manager 3-source reset); D3 (recon 1-line
  reset); D4 (accounting scoped wipe); D5 (helper
  `total_count` defense); D6 (Django regression tests);
  D7 (`@rerun-hygiene` Option A); D8 (durable lesson
  verbatim).
- **§5.c risks:** R1–R9 with mitigations.
- **§5.d verifications:** §4.1–§4.6 all CLEAN.
- **§5.e phasing:** M34.1 backend (SESSION_214) + M34.2
  acceptance (SESSION_215).
- **§5.f DoD:** exception path invocation #9 (M34.1);
  continuation (M34.2). First fully non-customer-facing
  milestone since M20.
- **§5.g rollback:** reverse ship order (M34.2 → M34.1);
  both revertable independently.
- **§5.h non-goals:** 12 explicit for M34 + all prior
  carried unchanged.

## 8. Streaks at M34.0 close

- **Planning-time as-recommended streak:** 12 → **13**
  (projected at M34 close if no §0.a amendments). Target
  selected as recommended after ten-alternative comparison +
  six-verification pass performed at user direction. **Zero
  correction rounds** — first M34 planning-open cycle with
  zero revisions. Historical run of 89 across M10 → M23
  preserved for the record.
- **Zero-drift permission-class streak:** unchanged at **37**
  (M10 → M33). M34.0 is planning-only; no code change.
  Projection at M34 close: **38 consecutive** (M34.1 adds no
  endpoints; M34.2 no endpoints).
- **Substrate-compound-value continuation:** M32 + M33 2-link
  arc breaks intentionally at M34 per M33 §9 standing
  question resolution ("close a deferral"). F&I depth arc
  remains primary continuation candidate for M35.
- **DoD exception path invocations:** 8. Projection at M34.1
  close: **9** (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1
  + M32.1 + M33.1 + M34.1). M34.2 continues exception path
  (no new customer-facing journey).
- **First fully non-customer-facing milestone since M20** —
  M21 → M33 all shipped operator-visible behavior or
  operator-facing infra. M34 is the first infra-only
  milestone in 13 consecutive customer-facing milestones.
- **First M34 planning-open cycle with zero revisions.**
  z lesson (verification-driven revision cycles at planning-
  open) on invocation 3 — anticipated revisions did not
  materialize because tracing pass at open was thorough
  enough to resolve ambiguity inline. Candidate durable
  observation: at "close a deferral" milestones with
  narrowly-scoped fixes, tracing-first at open eliminates
  need for revision rounds.
- **Verification-driven revision cycles (M32-origin candidate
  lesson z; elevated to load-bearing-across-two-milestones at
  M33 close):** third invocation at M34.0 — zero revisions
  needed. Elevation stands; the discipline continues to
  demonstrate value even when applied under different
  circumstances.
- **Six-milestone H deferral closed** — H persisted M27.2 →
  M33.2 as "three shared-DB non-idempotent journeys unchanged
  from M27.2 close" note in every retrospective. M34 closes
  the deferral.

## 9. Push status

**No push at SESSION_213 close.** M34.0 is planning-only per
the standard M28.0 / M29.0 / M30.0 / M31.0 / M32.0 / M33.0
cadence. Coordinated M34 close push deferred to explicit user
confirmation after M34.2 close.

Local commits at SESSION_213 close:

- SESSION_213 planning memo
  (`docs/roadmap/MILESTONE_34_PLANNING.md`) + this handoff +
  `00-START-NEXT-SESSION.md` flip land in a single local-only
  commit per planning-only session cadence; hash backfill via
  a subsequent commit.

Expected M34 commit count at coordinated push: **4–6**
(planning + M34.1 backend + M34.2 acceptance + close-out
fold, plus hash-backfill follow-ups per convention).

## 10. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_214 ·
Milestone 34 · Increment 1 (M34.1 — backend seed extensions +
Django regression tests)**. First-thing sequence per M28.1 /
M29.1 / M30.1 / M31.1 / M32.1 / M33.1 pattern:

1. **Verify starting state** (git status; backend tests 5,015
   pass; frontend Vitest 402 pass; checks; migrations; tsc;
   redis; `db.acceptance.sqlite3` proactive reset).
2. **Confirm working from M34.0 planning memo** — read
   `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D1 + D2 + D3
   + D4 + D6 + §5.e M34.1 before touching any seed file.
3. **Ship M34.1 backend substrate** per §5.e:
   - Extend `seed_journey_sales_manager_daily_startup.py`
     with D2 reset lines + `## Rerun invariants` docstring
     section + `BeBack` model import.
   - Extend `seed_journey_recon_workflow.py` with D3 reset
     line + `## Rerun invariants` docstring section.
   - Extend `seed_journey_office_accounting_workflow.py`
     with D4 wipe line + `## Rerun invariants` docstring
     section + explicit `M20_ACCEPTANCE_DB` invariant note
     + `TrialBalanceSnapshot` model import.
   - Create `backend/dealer_ai/tests/test_seed_journey_idempotency.py`
     with three regression tests per D6 (~120 lines).
   - **Historical migration NOT modified.**
   - **No product-code change.**
4. **Verify M34.1 close baselines:** backend suite 5,015 →
   ~5,018 pass; `check` + `makemigrations --check` clean;
   audit artifact 162 / 131 / 31 / 321 unchanged.
5. **DoD exception path** — ninth invocation. Document in §3
   of M34.1 handoff (seed idempotency + Django regression
   tests have zero operator-visible behavior; M34.2
   continues exception path).
6. **Ship the M34.1 handoff at
   `docs/handoffs/SESSION_214_m34_inc1_seeds.md`.** **Do NOT
   push** — coordinated push at M34 close.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` §9
6. **`docs/roadmap/MILESTONE_34_PLANNING.md`** (governing
   contract for M34)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7θ (M33 shipped surface);
   §7ι added at M34 close
9. `docs/handoffs/SESSION_212_m33_inc2_frontend.md`
10. `docs/roadmap/MILESTONE_20_PLANNING.md` §5.d (compose-
    service-verbs-not-ORM rule for seeds; superseded at M34
    for reset-scoped ORM queries per D2 + D3 + D4)
11. **This handoff** (`SESSION_213_m34_inc0_planning.md`)
12. Memory record
    `feedback_duplicate_small_stable_logic.md` (M28.0
    origin — governs D1 no-shared-helper decision)
13. Memory record
    `feedback_playwright_as_operational_contract.md` (M33
    D8 strengthening invocation; M34 preserves the contract
    by making it rerun-safe)
14. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at §4.5 for cascade behavior on
    `ReconDecision.finding` OneToOne)
15. Memory record
    `feedback_terminal_output_discipline.md` (governs
    implementation-session output shape)
