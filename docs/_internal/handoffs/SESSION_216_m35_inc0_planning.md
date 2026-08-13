---
title: "SESSION_216 handoff — Milestone 35 · Increment 0 (M35.0 — planning refinement + target selection)"
status: active
type: handoff
date: 2026-08-05
session: 216
milestone: 35
milestone_status: active
milestone_name: "Lender Submission Activation: record the latest structure's lender submission, capture the response on that same submission, and derive the current F&I state from verified FK events"
increment: 0
increment_status: shipped
commit: f17e1eb
commit_notes: "M35.0 planning session — local commit landed as f17e1eb per M28.0 / M29.0 / M30.0 / M31.0 / M32.0 / M33.0 / M34.0 planning-only cadence; hash backfilled via this subsequent commit; NOT pushed. Coordinated M35 close push deferred to explicit user confirmation after M35.2 close."
---

# SESSION_216 — Milestone 35 · Increment 0 (M35.0 — planning refinement + target selection)

## What shipped

SESSION_216 opened as a planning-only session per the M34.2
close-out priorities in `00-START-NEXT-SESSION.md`. One
deliverable landed:

1. **M35.0 planning memo** authored at
   `docs/roadmap/MILESTONE_35_PLANNING.md` — target locked as
   **Lender Submission Activation** (§5.a). Third link of the
   M32 → M33 F&I depth arc. User-confirmed after direct
   evaluation of three natural continuation modes per the M34 §9
   standing question: (a) continue F&I depth arc; (b) reset to
   breadth; (c) close another §3 deferral. All §5.b–§5.h
   decisions locked (D1–D11; risk register R1–R11; verifications
   §4.1–§4.8; two-increment phasing; DoD compliance; rollback;
   non-goals). **One blocking finding at §4.8 resolved
   architecturally via D4** (LenderProgram FK-discovery gap →
   new thin list endpoint at M35.1). **Two non-blocking scope
   corrections applied before §5.b lock** (getLenderSubmission
   wrapper removed; submitted_at field omitted). **Ten user-
   directed corrections total** applied at planning-open — z
   lesson on invocation 4 with substantial revision rounds
   strengthening the locked design.

No §0.a M35.0 amendments — the first M34 CI run on `c76e6db`
(M34.2 hash-backfill commit) is green (workflow `31015140258`,
success in 3m1s at 2026-08-05T14:25:46Z); no regression to
correct.

Full active memo authored at
`docs/roadmap/MILESTONE_35_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean;
  `HEAD == origin/main @ c76e6db` (0 commits ahead — M34 push
  confirmed pre-session as 6 commits on `main`); Redis PONG;
  Django `check` clean (4 benign DecimalField warnings —
  pre-existing, unchanged); `makemigrations --check` clean;
  frontend `tsc --noEmit` clean; acceptance `tsc --noEmit`
  clean; backend suite **5,021 pass, 1 skipped, 0 fail**
  (175.645s); frontend Vitest **402 pass** (45 files, 6.95s);
  acceptance DB proactively reset per SESSION_200 §0.a durable
  lesson (v). All matches M34.2 close baseline exactly.
- **First M34 CI run monitored (§2):** acceptance workflow on
  `c76e6db` (M34.2 hash-backfill commit, top of `main`)
  **completed success** in 3m1s at 2026-08-05T14:25:46Z. Prior
  runs on `main` all successful. Main is CI-verified shipped
  at the M34.2 baseline. No §0.a M35.0 amendment triggered.
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **162 total / 131 covered / 31 backend-only / 321
  service verbs**. Byte-identical to the committed M34.2
  artifact. Two-source agreement at M35.0 open.
- **Candidate list presented (§4)** across the M34 §9 tiers:
  - **Elevated (highest recommendation strength at M35.0):**
    NEW C — F&I chargeback substrate (still pilot-evidence
    gated); Lender Fit Recommendations (D10 elevation — 3 of
    4 blockers remain); NEW F&I workflow-state extensions
    beyond M33's two derived states; NEW F&I-scoped lead-
    context view (evidence-gated); NEW cross-lead sales-
    manager pending-approval queue page (evidence-gated);
    direct-create CA structuring branch (M33 §5.h explicit
    deferral); iteration UX (M33 D9 deferral); PATCH on
    DealStructure (activation-vocabulary-asymmetry
    preservation); NEW O2 (9-milestone deferral, unchanged);
    NEW O3 (9-milestone deferral, unchanged).
  - **Shipped since M33 §9:** H — Test-Hygiene Remediation
    (SHIPPED at M34).
  - **Fresh direct-operator gaps surveyed (breadth
    candidates):** vendor detail (#43 wrapper-only, small
    polish); photo reorder (#65 wrapper-only, small polish
    + D&D primitive selection); broader F&I subdomain
    (#89–101 excl. #101 chargeback — 11 uncovered post-M34,
    too large without direction).
  - **Gated:** T, U, L, M.
  - **Deferred pending evidence:** D.
  - **Deferred stable:** G.
  - **Deferred at M34 §3 / M33 §3 / M32 §3 / M31 §3 / M30
    §3 / M29 §3 / M28 §3 / M27 §3 / M25 §4:** all carried
    forward unchanged.
- **Recommendation (§5) and user confirmation:** F&I depth-arc
  continuation via NEW F&I workflow-state extensions, under
  the primary operational-coverage lens with F&I depth-arc
  framing per M34 §9 standing question. Rationale:
  1. M32 established the F&I intake receiver.
  2. M33 established the first F&I operator action (DealStructure
     creation).
  3. The next operational question — "Can the F&I manager
     accurately understand where every deal is in the F&I
     process?" — is directly answered by activating the send-
     and-response loop.
  4. Every other F&I candidate remains deferred by
     construction (NEW C still pilot-gated; Lender Fit still
     has three of four blockers; direct-create / iteration /
     PATCH all deferred; F&I-scoped lead-context view + cross-
     lead pending-approval queue still evidence-gated).
  5. Breadth pivot has no stronger evidence than the F&I arc
     (three named breadth gaps are wrapper-only polish or too-
     large-without-direction).
  6. Close-another-deferral per M34 precedent is available but
     not obviously higher-value than the arc continuation
     (F&I arc compound value is high — LenderSubmission
     activation unblocks the entire downstream chain
     Stipulation → Contract → BEPA → Funding → Chargeback →
     Compliance → Deal Jacket → Lender Fit).

  User locked "NEW F&I workflow-state extensions" for §5.a
  with the following scope-shaping constraints per user
  directive:

  1. Anchor question: **Can an F&I manager determine the true
     operational state of every active deal directly from
     Dealer OS, using workflow states derived from verified
     business events rather than manually inferred progress?**
     (subsequently refined at §4.8 correction — see below).
  2. Verification pass on the existing F&I domain to determine
     whether workflow states should remain derived from the FK
     graph or whether any state requires explicit persistence.
  3. Attempt to prove additional workflow states can continue
     the M33 philosophy of derivation. Only introduce stored
     workflow state if verification demonstrates that derivation
     becomes ambiguous or loses required business meaning.
  4. Scope discipline: deliver only the smallest workflow-state
     extension that answers the anchor question and unlocks the
     next operational loop.
  5. Do NOT expand into lender selection, automated
     recommendations, chargebacks, iteration UX, or PATCH
     semantics unless verification demonstrates they are an
     unavoidable prerequisite.

- **Verification pass at §4 (per user directive):** eight
  verifications performed. Findings:
  - §4.1 Status vocabulary + defaults: CLEAN. Four-value
    fixed set (`pending / approved / counter / declined`);
    default `pending`.
  - §4.2 Transition constraints: CLEAN. **Any-to-any
    transitions allowed** per M10.3 contract.
  - §4.3 Multiple submissions per DealStructure: CLEAN.
    **Explicitly supported** — but M35 UI does not surface
    second-submission creation (first-loop-only posture).
  - §4.4 Deterministic latest-submission ordering: CLEAN with
    refinement — add explicit `-pk` tiebreak beyond the model
    Meta ordering.
  - §4.5 `Counter` structured-terms: CLEAN — not required.
    M35 UI omits `counter_terms` capture and states so
    clearly.
  - §4.6 Projection sufficiency: CLEAN.
    `lender_program_name` denormalized in
    `_project_lender_submission`; complete for M35 needs.
  - §4.7 External transmission on create: CLEAN. `record_lender_submission`
    is a **pure DB insert**; no signals; no Celery tasks; no
    webhooks. UI language contract locked (D6 + D11 + R4):
    "Record" / "Submitted to" — never "Send" / "Transmit" /
    "Contact lender".
  - §4.8 Nested-annotation OuterRef compilation + discovered
    scope corrections. Live shell test executed against
    SQLite: **COMPILED_OK + EXECUTED_OK**. Postgres re-
    verification deferred to M35.1 §0.a checklist (R11
    mitigation). Three discovered scope corrections:
    (1) BLOCKING: NO list endpoint exists for LenderProgram;
        `list_active_lender_programs` service verb has no HTTP
        surface. Resolved via D4 (new thin list endpoint at
        M35.1).
    (2) NON-BLOCKING: `getLenderSubmission(id)` wrapper
        originally proposed in D5 points at a nonexistent
        endpoint (only POST + PATCH exist; no single-record
        GET). Wrapper removed; state reconciliation shifted to
        PATCH response body + CA list refetch.
    (3) NON-BLOCKING: `submitted_at` field originally proposed
        as operator-editable in D6 has no future-date validation
        (live-tested — accepted); no operational evidence
        supports back-entry. Field removed from D6; server
        records; UI displays returned value.

- **Ten user-directed corrections applied at planning-open
  (z lesson invocation 4):**
  1. Option 1 (narrowest — Submitted derived state only) →
     Option 2 (full send-and-response loop with Submitted /
     Approved / Counter-offer received / Declined derived
     states). Rationale: activating only submission creation
     would leave every submitted deal permanently
     indistinguishable inside Dealer OS once the lender
     responded, not fully satisfying the anchor question.
  2. Audit projection re-derivation from direct
     `M21_OPERATIONAL_SURFACE_AUDIT.md` artifact inspection
     (initial projection double-counted the two shipped
     LenderSubmission endpoints; corrected to M35.1 close =
     163/131/32/321 and M35.2 close = 163/134/29/321). Lesson
     (cc) fifth invocation.
  3. Removed `getLenderSubmission(id)` wrapper (no shipped
     endpoint).
  4. Rename post-response action: "Record lender response"
     (while pending) / "Update lender response" (after
     terminal) — never "Record another response".
  5. Explicit first-loop boundary: allowed = same-record
     status update on latest LenderSubmission; deferred = new
     submission / alternate lender / history / multi-
     submission management.
  6. Omit `submitted_at` field from D6 (server records;
     future-entry not supported by evidence).
  7. Narrow LenderProgram list projection to `{id, name}`
     (originally proposed 5 fields including contact / terms /
     is_active).
  8. Nested-annotation OuterRef treated as R11 technical risk
     (was previously "settled implementation detail") + 8-case
     regression test coverage matrix.
  9. Refine financial-language contract: chip may say
     "Approved" once verified `approved` status is recorded,
     but individual DealStructure values may NOT be labeled
     as "lender-approved terms" unless `approval_terms` data
     is captured and displayed.
  10. Strengthen Playwright journey around truthfulness:
      6 explicit truthfulness assertions + back-to-back
      double-run proof at M35.2 close (NOT `--repeat-each=2`).
      D11 refinement: locked verbatim per user directive.

  Milestone renamed per user directive from the initial "F&I
  workflow-state extensions" to **Lender Submission Activation:
  record the latest structure's lender submission, capture the
  response on that same submission, and derive the current F&I
  state from verified FK events.** Anchor question refined to:
  **Can an F&I manager record where a structured deal was
  submitted, capture the lender's response, and see the
  resulting operational state without leaving Dealer OS?**

- **§5.b–§5.h draft (per user directive):** eleven design
  decisions (D1–D11), eleven risks (R1–R11), eight
  verifications (§4.1–§4.8), two-increment phasing (M35.1
  backend + M35.2 frontend), DoD compliance check (invocation
  #12 of exception path — 12th customer-facing-milestone
  invocation), rollback plan (reverse ship order), non-goals
  (~20 explicit for M35 + all prior carried unchanged).

- **All §5 locks confirmed by user.**

## 1. Verification results at open

- **git status:** clean; `HEAD == origin/main @ c76e6db` (0
  commits ahead — M34 push confirmed pre-session).
- **git log --oneline -10:** shows the expected M34 commit
  sequence (M34.2 hash-backfill `c76e6db`; M34 close-out fold
  `fda9d56`; M34.1 hash-backfill `09d1299`; M34.1 backend
  `9abd0ad`; M34.0 hash-backfill `a03c5eb`; M34.0 planning
  `f163e93`; M33.2 hash-backfill `3a83584`; M33 close-out fold
  `622c51e`; M33.1 hash-backfill `1e0008f`; M33.1 backend
  `eb50f94`).
- **`python3 manage.py test dealer_ai`:** 5,021 pass, 1
  skipped, 0 fail (175.645s).
- **`cd frontend && npm test`:** 402 pass across 45 files
  (6.95s).
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

## 2. First M34 CI run

- **Workflow:** `acceptance` on `main`.
- **Latest run:** `31015140258` on `c76e6db` (M34.2 hash-
  backfill commit, top of `main`).
- **Result:** completed / success.
- **Duration:** 3m1s total.
- **Prior runs on `main`:** all successful.

**M34 is CI-verified shipped.** No §0.a M35.0 amendment
triggered.

## 3. Audit regeneration

- **Command:** `python3 -m
  dealer_ai.scripts.audit_operational_surface`.
- **Output:** 162 total / 131 covered / 31 backend-only / 321
  service verbs.
- **Artifact write:**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
- **Diff:** none. Byte-identical to M34.2 committed baseline.

**Two-source agreement** at M35.0 open: audit numbers match
the M34.2 handoff frontmatter and the M34 §7ι anchor (162 /
131 / 31 / 321).

## 4. Candidate list presented at open

Per M34 retrospective §9. Full list documented in
`docs/roadmap/MILESTONE_35_PLANNING.md` §5.a "Alternatives
considered explicitly."

## 5. Recommendation and user confirmation

**Primary recommendation:** F&I depth-arc continuation via
NEW F&I workflow-state extensions.

**Rationale under the primary operational-coverage lens with
F&I depth-arc framing per M34 §9 standing question:** see M35.0
planning memo §5.a for full rationale (six load-bearing
signals).

**User confirmation:** target locked with five scope-shaping
constraints; ten planning-time corrections applied before §5.b
lock; verification pass on the existing F&I domain performed
per user directive.

**Ten corrections applied before §5.b lock.** z lesson on
invocation 4 — first invocation with substantial revision
rounds (M32.0 was 4 corrections; M33.0 was 4 corrections;
M34.0 was 0 corrections; M35.0 is 10 corrections). Discipline
continues to demonstrate value at planning-open when tracing
surfaces gaps that would otherwise ship as bugs.

## 6. Verification pass (§4 of planning memo)

Eight verifications performed at open. **One blocking finding
resolved architecturally; two non-blocking scope corrections
applied.**

- **§4.1 Status vocabulary + defaults:** CLEAN. Four-value
  fixed set; default `pending`.
- **§4.2 Transition constraints:** CLEAN. Any-to-any
  transitions per M10.3 contract preserved verbatim.
- **§4.3 Multiple submissions per DealStructure:** CLEAN.
  Explicitly supported; M35 UI does not surface second-
  submission creation.
- **§4.4 Deterministic latest-submission ordering:** CLEAN
  with refinement — add explicit `-pk` tiebreak.
- **§4.5 `Counter` structured-terms:** CLEAN. Not required;
  M35 UI omits capture.
- **§4.6 Projection sufficiency:** CLEAN.
  `lender_program_name` denormalized; complete for M35 needs.
- **§4.7 External transmission on create:** CLEAN. Pure DB
  insert; UI language contract locked (D6 + D11 + R4).
- **§4.8 Nested-annotation OuterRef compilation + scope
  corrections:** verified working on SQLite; Postgres re-
  verify at M35.1 open per R11. One blocking finding resolved
  via D4 (FK discoverability); two non-blocking corrections
  applied (getLenderSubmission removed; submitted_at omitted).

**One blocking finding resolved architecturally.** Two non-
blocking scope corrections applied. Ten user-directed
corrections total before §5.b lock.

## 7. All §5 locks

Full detail in `docs/roadmap/MILESTONE_35_PLANNING.md`. Summary:

- **§5.a target:** Lender Submission Activation — record the
  latest structure's lender submission, capture the response
  on that same submission, and derive the current F&I state
  from verified FK events.
- **§5.b decisions:** D1 (M33.1 D1 annotation preserved);
  D2 (NEW latest_lender_submission_status annotation);
  D3 (projection extension); D4 (NEW LenderProgram list
  endpoint — narrow `{id, name}` projection);
  D5 (fAndIApi.ts — 3 wrappers, 4 types, no getter, no
  submitted_at, no status override); D6 (LenderSubmissionRecordForm
  — no submitted_at, prohibited-strings list); D7
  (LenderSubmissionResponseForm — three-value radio, mode-
  conditional headers); D8 (chip 2 → 6 states, state-
  conditional row actions, first-loop boundary explicit);
  D9 (NEW Playwright spec, `@rerun-hygiene` tag, back-to-
  back double-run proof); D10 (Submission Sasha seed with
  3 rerun invariants); D11 (financial-language contract
  refinement — 4-layer defense).
- **§5.c risks:** R1–R11 with mitigations. R11 is nested-
  annotation OuterRef Postgres compilation risk (SQLite
  verified live; Postgres re-verify at M35.1 §0.a; fallback
  documented).
- **§5.d verifications:** §4.1–§4.8 all resolved.
- **§5.e phasing:** M35.1 backend (SESSION_217) — FK-discovery
  endpoint + subquery annotations + projection extension +
  20 tests; M35.2 frontend + Playwright (SESSION_218) —
  API-client + 2 components + chip extension + spec + seed.
- **§5.f DoD:** exception path invocation #12 (M35.1); direct
  satisfaction (M35.2).
- **§5.g rollback:** reverse ship order (M35.2 → M35.1); both
  revertable independently (M35.2 depends on M35.1 for
  functionality, but M35.1 stays safe as additive substrate).
- **§5.h non-goals:** ~20 explicit for M35 + all prior carried
  unchanged.

## 8. Streaks at M35.0 close

- **Planning-time as-recommended streak:** 13 → **14**
  (projected at M35 close if no §0.a amendments). Target
  selected as recommended after ten-alternative comparison +
  eight-verification pass performed at user direction. **Ten
  correction rounds** applied — z lesson on invocation 4 with
  substantial revision rounds. Historical run of 89 across
  M10 → M23 preserved for the record.
- **Zero-drift permission-class streak:** unchanged at **38**
  (M10 → M34). M35.0 is planning-only; no code change.
  Projection at M35 close: **39 consecutive** (M35.1 adds one
  new endpoint reusing `_M101_PERMS`; M35.2 adds no new
  backend endpoints).
- **Substrate-compound-value continuation:** M32 sales-to-F&I
  bridge + M33 F&I first-loop activation reached 2 links; M34
  broke the arc intentionally (close-a-deferral); **M35
  restarts the arc at 3 links** (M32 + M33 + M35 F&I depth-arc
  continuation).
- **DoD exception path invocations:** 11. Projection at M35.1
  close: **12** (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1
  + M32.1 + M33.1 + M34.1 + M34.2 + M35.1). M35.2 satisfies
  DoD directly.
- **First activation of M10.3 substrate operationally** —
  108 sessions after M10.3 shipped at SESSION_108. Longest
  substrate-to-UI gap closed at M35 (surpassing M33's 19-
  session gap on M10.2 DealStructure).
- **Third link in the F&I depth arc** — M32 sales-to-F&I
  bridge + M33 F&I first-loop activation + M35 send-and-
  response loop. Arc compound value: activating
  LenderSubmission unblocks the entire downstream chain
  (Stipulation → Contract → BEPA → Funding → Chargeback →
  Compliance → Deal Jacket → Lender Fit).
- **Verification-driven revision cycles (M32-origin candidate
  lesson z; elevated to load-bearing-across-two-milestones at
  M33 close):** fourth invocation at M35.0 — ten user-directed
  corrections applied before §5.b lock. Discipline continues
  to demonstrate value at planning-open when tracing surfaces
  gaps.
- **First blocking-finding-resolved-architecturally at M35.0**
  — FK-discovery gap on LenderProgram → D4 new thin list
  endpoint. Preserves memory lesson
  `feedback_verify_fk_discoverability_before_lock.md` (M27.0
  origin).
- **Coverage-projection truthfulness (cc):** fifth invocation
  at M35.0. Initial projection double-counted the two shipped
  LenderSubmission endpoints; corrected via direct artifact
  inspection to M35.1 close = 163/131/32/321 and M35.2 close
  = 163/134/29/321. (cc) elevated to load-bearing-across-
  three-milestones at M34.2; M35.0 fifth invocation extends
  the discipline.
- **Candidate durable lesson (ff) awaits first re-application**
  — M34.0 D8 verbatim: *Acceptance journeys must be
  independently rerunnable against shared state; green-on-
  clean-DB alone is insufficient evidence of operational
  reliability.* M35.2 D9 + D10 will re-apply the contract
  (Submission Sasha seed idempotent from first shipping day;
  `@rerun-hygiene` tag + back-to-back double-run proof
  mechanism preserved verbatim). On first re-application (ff)
  elevates to load-bearing-across-two-milestones.

## 9. Push status

**No push at SESSION_216 close.** M35.0 is planning-only per
the standard M28.0 / M29.0 / M30.0 / M31.0 / M32.0 / M33.0 /
M34.0 cadence. Coordinated M35 close push deferred to explicit
user confirmation after M35.2 close.

Local commits at SESSION_216 close:

- SESSION_216 planning memo
  (`docs/roadmap/MILESTONE_35_PLANNING.md`) + this handoff +
  `00-START-NEXT-SESSION.md` flip land in a single local-only
  commit per planning-only session cadence; hash backfill via
  a subsequent commit.

Expected M35 commit count at coordinated push: **4–6**
(planning + M35.1 backend + M35.2 frontend + close-out fold,
plus hash-backfill follow-ups per convention).

## 10. Next session priorities

`00-START-NEXT-SESSION.md` overwritten for **SESSION_217 ·
Milestone 35 · Increment 1 (M35.1 — backend FK-discovery
endpoint + subquery annotations + projection extension +
Django regression tests)**. First-thing sequence per M28.1 /
M29.1 / M30.1 / M31.1 / M32.1 / M33.1 / M34.1 pattern:

1. **Verify starting state** (git status; backend tests 5,021
   pass; frontend Vitest 402 pass; checks; migrations; tsc;
   redis; `db.acceptance.sqlite3` proactive reset).
2. **§0.a FIRST ITEM at M35.1 open — Postgres OuterRef re-
   verification** per R11 mitigation. Run the M35.0 §4.8 live
   shell test against a Postgres-configured environment (spin
   up `POSTGRES_DB` env or use a temporary Postgres via
   `docker run --rm -p 5432:5432 -e POSTGRES_PASSWORD=... postgres:16`).
   If Postgres compilation OR execution fails, apply R11
   fallback (rewrite D2 without depending on D1 annotation —
   use `NOT EXISTS(newer DealStructure)` guard inside the
   LenderSubmission subquery filter) as §0.a M35.1 amendment
   before proceeding to D4.
3. **Confirm working from M35.0 planning memo** — read
   `docs/roadmap/MILESTONE_35_PLANNING.md` §5.b D1 + D2 + D3 +
   D4 + §5.e M35.1 before touching any file.
4. **Ship M35.1 backend substrate** per §5.e:
   - Extend `services/f_and_i/credit_application.py` with the
     D1 annotation preserved (already shipped at M33.1) + NEW
     D2 annotation correlating on `latest_deal_structure_id`
     with `("-submitted_at", "-created_at", "-pk")` ordering.
   - Extend `views_f_and_i.py` with D3 projection extension +
     NEW `admin_lender_program_list` view function reusing
     shipped `list_active_lender_programs` service verb.
     Narrow `{id, name}` projection per D4.
   - Extend `urls.py` with the new `admin/lender-programs/list/`
     route named `admin-lender-program-list`.
   - Create `backend/dealer_ai/tests/test_m351_lender_program_list.py`
     with endpoint permission matrix (5 negative + 2 positive
     per M33.1 pattern) + narrow projection shape + active-
     only filter + empty-tenant + N-programs cases.
   - Create `backend/dealer_ai/tests/test_m351_lender_submission_status_annotation.py`
     with 8-case regression matrix per R11.
   - Optionally extend `test_m331_deal_structure_read.py` OR
     add `test_m351_credit_application_projection.py` for
     projection extension coverage.
   - **Historical migrations NOT modified.**
   - **No new service verb.**
   - **No new permission class.**
   - **No migration; no schema change.**
5. **Verify M35.1 close baselines:** backend suite 5,021 →
   ~5,041 pass; `check` + `makemigrations --check` clean;
   audit artifact 163 / 131 / 32 / 321 (+1 endpoint total; +1
   backend-only; covered unchanged; service verbs unchanged).
6. **DoD exception path** — twelfth invocation. Document in
   §3 of M35.1 handoff (FK-discovery endpoint + queryset
   annotations + projection extension have zero operator-
   visible behavior; M35.2 satisfies DoD directly).
7. **Ship the M35.1 handoff at
   `docs/handoffs/SESSION_217_m35_inc1_backend.md`.** **Do NOT
   push** — coordinated push at M35 close.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_34_RETROSPECTIVE.md` §9 (M35
   candidate list + F&I depth-arc standing question)
6. **`docs/roadmap/MILESTONE_35_PLANNING.md`** (governing
   contract for M35)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` rows
   #93/#94/#95 (source of truth for §5.e audit projections)
8. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.3 (LenderProgram +
   LenderSubmission substrate contract)
9. `docs/roadmap/MILESTONE_33_PLANNING.md` §5.b D1 + D3 + D5
   (subquery-annotation pattern + financial-language contract
   preserved / extended at M35)
10. `docs/roadmap/MILESTONE_34_PLANNING.md` §5.b D7 + D10
    (rerun-hygiene contract preserved at M35 D9 + D10)
11. `docs/CAPABILITY_MATRIX.md` §7ι (M34 shipped surface);
    §7κ added at M35 close
12. `docs/handoffs/SESSION_215_m34_inc2_acceptance.md` (M34.2
    shipped + M34 close-out fold)
13. **This handoff** (`SESSION_216_m35_inc0_planning.md`)
14. Memory record
    `feedback_verify_fk_discoverability_before_lock.md` (M27.0
    origin — applied at §4.8 for LenderProgram FK discovery;
    resolved via D4)
15. Memory record
    `feedback_playwright_as_operational_contract.md` (M33 D8
    strengthening invocation; M34 preserves; M35 extends
    journey coverage to send-and-response loop)
16. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — no shared helper between M33 DealStructure
    forms and M35 LenderSubmission forms)
17. Memory record `feedback_terminal_output_discipline.md`
    (governs implementation-session output shape)
