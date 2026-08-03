---
title: "Milestone 26 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-03
sessions: SESSION_189 → SESSION_190
milestone: 26
milestone_name: "Audit-Script Parser Refinement (Planning-Substrate Integrity)"
related:
  - docs/roadmap/MILESTONE_26_PLANNING.md
  - docs/roadmap/MILESTONE_25_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7α
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 26
---

# Milestone 26 — Retrospective

Written at Milestone 26 close (SESSION_190, close-out folded into
M26.1 per §5.h evidence-sized Option B — no code discrepancies at
any §5.d checkpoint). Records what was planned, what shipped,
what deviated and why, and lessons carried forward for
Milestone 27. Mirrors `MILESTONE_25_RETROSPECTIVE.md` shape.

## 1. Planned scope

`MILESTONE_26_PLANNING.md` at SESSION_189 (M26.0 open) defined
the milestone as **Audit-Script Parser Refinement** — a
planning-substrate integrity milestone under an AI independent
recommendation confirmed after three alternatives (A2 JE
creation UI, NEW audit-script refinement, H test-hygiene) were
presented under the three-tier operator-coverage /
test-hygiene-and-audit-tooling / gated / deferred framing.
Framing is a reframe of the durable operational-coverage
guiding question ("which candidate most increases operational
coverage for a dealership employee?"), not a departure —
the audit script is the substrate that answers coverage under
the lens, and the M25.3 close-out handoff's 2-endpoint
false-positive estimate compounded into planning drift.

**Anchor business question:** *Can future milestone selection
rely on the operational-surface audit as trustworthy coverage
evidence?* — a prerequisite to the durable operational-
coverage guiding question.

**Post-fix coverage baseline projected at M26.0 open:** 120 /
154 (later refined at M26.1 open to **119 / 154** — see §3).

**Two increments planned + close-out fold** (§5.f
evidence-sized shape):

- **M26.0** — planning refinement + all §5 locks (SESSION_189).
- **M26.1** — parser fix + regression suite + audit
  regeneration + doc updates (SESSION_190).
- **M26.2 close-out** folds into M26.1 per §5.h Option B
  unless verification surfaces §5.d discrepancies.

**All eight §5 locks** established at M26.0 open:

- §5.a — Audit-script parser refinement, planning-substrate
  integrity framing.
- §5.b — Narrow parser fix inside `extract_frontend_consumers`
  (script line 607); preferred approach: keep fast-path regex,
  add post-match refinement via balanced-brace-aware companion.
  `normalize_frontend`, `_HELPER_TO_VERB`, `cross_reference`,
  `recommend_disposition` all untouched.
- §5.c — Dedicated `test_audit_operational_surface.py` with
  regression tests (originally 6 positive + 6 negative;
  refined at M26.1 open to 5 + 7).
- §5.d — Two-phase protocol: regenerate + per-row manual
  verification of wrapper existence, verb match, component
  import.
- §5.e — Corrected baseline recorded only after regenerated
  artifact and direct repository inspection agree.
- §5.f — 1 implementation increment + close-out fold. Half the
  M25 velocity envelope by design.
- §5.g — M21.0 §5.f exception path explicitly invoked; no
  Playwright journey required (audit-tooling is not
  operator-facing).
- §5.h — Evidence-sized Option B fold (M18 → M25 precedent).

**User-locked scope-discipline constraints at M26.0 open:**

1. Scope strictly to the nested-template-literal + optional-
   query-string parsing defect (§5.b).
2. Regression tests for all confirmed false positives plus
   representative negatives (§5.c).
3. Regenerate + per-row manual verification (§5.d).
4. No disposition changes unrelated to the parser defect
   without separate evidence (§3).
5. Record corrected baseline only after two-source agreement
   (§5.e).

Plus: A2 elevated as leading M27 §5.a candidate. H kept
separate from M26. Exception path used explicitly for §5.g.

## 2. What actually shipped

**Ships matched the planned scope exactly minus one endpoint
whose reclassification was empirically discovered at M26.1
open to have a different root cause than the M26 defect
(row 5; see §3).**

### M26.0 — planning refinement (SESSION_189)

- Full active memo expansion at `MILESTONE_26_PLANNING.md`
  with all eight §5 locks.
- SESSION_189 §3 audit regeneration + direct extractor
  tracing revealed the M25.3 handoff's 2-endpoint estimate
  understated the true blast radius by 3× (6 confirmed false
  positives).
- Session-numbering correction: M25.3 folded-close-out
  handoff at `SESSION_188_m25_inc3_close.md` occupies the
  188 slot per DOC_GOVERNANCE incrementing convention. This
  session is SESSION_189 (not SESSION_188 as the prior
  start-here doc named it). Corrected across the planning
  memo + handoff + start-here doc.
- Handoff at `docs/handoffs/SESSION_189_m26_inc0_planning.md`.
- Commit `8bb588f` + hash-backfill `ee63777`.
- Planning-time as-recommended streak → 4.

### M26.1 — parser fix + regression + audit regen + close-out (SESSION_190)

- **M26.1-open §2 empirical refinement:** pre-implementation
  verification of the six SESSION_189-listed false positives
  revealed row 5 `vehicles/<int:vehicle_id>/`
  (wrapper `fetchVehicleDetail` at api.ts:611) uses the
  public `getJSON` helper, which is **not** enumerated in
  `_HELPER_CALL_RE` (matches only `authGetJSON` /
  `authPostJSON` etc.). `_PUBLIC_FETCH_RE` matches only
  literal `fetch(...)` calls with `/api/dealer-ai/` or
  `${API_BASE}` in the URL. Row 5's coverage gap is a
  separate defect from the nested-template-literal one M26
  addresses — a public-fetch-helper regex omission.
  Corrected M26.1 blast radius: **5 endpoints** (rows 7, 16,
  29, 111, 121). Corrected post-fix coverage baseline:
  **119 / 154**. Row 5 added to §3 as NEW M27+ candidate.
  §5.c positive case #6 (`fetchVehicleDetail`
  two-interpolation) repurposed to negative case #7
  documenting the M27+ deferral. Planning memo + start-here
  doc refined additively.

- **§5.b parser fix.** Extracted the existing balanced-brace
  walking logic from `_extract_url_literals` (lines 462-484)
  into a shared substrate
  `_extract_balanced_template_literal(source, start_pos) ->
  tuple[str, int]`. Added post-match refinement to
  `extract_frontend_consumers`: when the fast-path
  `_HELPER_CALL_RE` template branch captures a template
  literal with mismatched `${` vs `}` count (indicating
  truncation at an inner backtick), re-tokenize from
  `m.start(2)` using the balanced parser. `_extract_url_
  literals` refactored to delegate to the shared substrate.
  `normalize_frontend`, `_HELPER_TO_VERB`, `cross_reference`,
  `recommend_disposition` all untouched per §5.b out-of-scope
  discipline.

- **§5.c regression suite.** New
  `backend/dealer_ai/tests/test_audit_operational_surface.py`
  with 2 test classes / 12 methods:
  - **5 positive cases** — one per confirmed nested-
    template-literal false positive (rows 7, 16, 29, 111,
    121). Each asserts full-backtick capture, correct
    normalized pattern, `authGetJSON` verb, and wrapper
    name.
  - **7 negative cases** — (1) legitimate query-string
    wrapper without template nesting, (2) wrapper against
    nonexistent endpoint (does not manufacture coverage),
    (3) fast-path unchanged (post-match refinement does not
    fire when `${` count = `}` count), (4) M22.1 §5.e
    identifier-lookback preserved, (5) M23.1 §5.d
    `_HELPER_TO_VERB` map preserved, (6) malformed
    template terminates cleanly (no hang), (7) M26.1 §5.b
    scope boundary — public `getJSON` remains invisible
    post-fix (documents M27+ deferral).
  - All 12 tests pass first run.

- **§5.d Phase 1 audit regeneration.** `python3 -m
  dealer_ai.scripts.audit_operational_surface` produces
  exactly the expected diff:
  - Coverage summary: 114 → **119**.
  - Backend-only: 40 → **35**.
  - Row 7 → `covered` with `api.ts:283 fetchAdminLeads`.
  - Row 16 → `covered` with `api.ts:340 fetchAuditEvents`.
  - Row 29 → `covered` with `salesApi.ts:256
    listAdminVehicles`.
  - Row 111 → `covered` with `salesApi.ts:203
    listTestDrives`.
  - Row 121 → `covered` with `salesApi.ts:424 listBeBacks`.
  - Row 42 `admin/vendors/` cosmetic wrapper-reorder
    (deterministic script output; acceptable per §3).
  - `defer-candidate-O2` group size: 35 → 30.
  - Per-module backend-only counts update accordingly.
  - Row 5 correctly remains `defer-candidate-O2`.
  - No other row semantically changes.

- **§5.d Phase 2 per-row manual verification.** For each of
  the 5 reclassified rows:
  - Wrapper exists at reported `filename:line` ✓.
  - Helper is `authGetJSON` → verb GET → endpoint
    `admin_lead_list` / `admin_audit_events` /
    `admin_vehicle_list` / `admin_test_drive_list` /
    `admin_be_back_list` all `['GET']` per
    `extract_view_methods` ✓.
  - Wrapper imported by ≥1 non-test `.tsx` or `.ts`
    component (68 total imports across 17 files) — full
    coverage across the operator dashboard, lead-detail
    modal, sales pages, referral form, audit panel,
    handoff queue ✓.

- **§5.e corrected baseline recording.** Two-source
  agreement confirmed at 119 / 154. Baseline recorded in:
  - `docs/CAPABILITY_MATRIX.md` §7α (new block).
  - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 26.
  - This retrospective §2 + §7.
  - `docs/handoffs/SESSION_190_m26_close.md` baseline block.
  - `00-START-NEXT-SESSION.md` operational-state block
    (overwritten with SESSION_191 priorities).

- **§5.h close-out fold.** All §5.d checkpoints passed
  cleanly; M26.2 folded into M26.1 session per Option B.
  Retrospective + all docs updated + coordinated push in one
  session.

- **Baseline deltas at M26.1 close:**
  - Backend: **4,793 → 4,805 pass** (+12 across regression
    suite).
  - Frontend Vitest: **226 pass** unchanged.
  - Acceptance: **14 journeys** unchanged.
  - Audit: **114 / 154 → 119 / 154 covered** (+5 real
    coverage gain from the fix).
  - `manage.py check` + `makemigrations --check` clean.
  - Zero-drift permission-class streak → 26.
  - Planning-time as-recommended streak → 5.

- Handoff at `docs/handoffs/SESSION_190_m26_close.md`.

## 3. Deviations from plan and reason

**One deviation, recorded honestly per the durable "record
empirical-discovery refinements honestly" principle:**

**M26.1-open blast-radius correction (5 endpoints, not 6).**
The M26.0 planning memo locked the expected reclassifications
at 6 rows / 120 covered. Pre-implementation verification at
M26.1 open (SESSION_190 §2) revealed row 5
`vehicles/<int:vehicle_id>/` is not a nested-template-literal
defect at all — its wrapper `fetchVehicleDetail` uses the
public `getJSON` helper, which is entirely outside the
audit's `_HELPER_CALL_RE` scope. The M26 parser fix would
NOT reclassify it regardless of implementation quality; row
5's coverage gap awaits a separate M27+ public-fetch-helper
refinement.

**Handled per the planning-time as-recommended framework:**
this is an empirical-discovery refinement of the underlying
evidence (which endpoints qualify as nested-template-literal
false positives), not a departure from the §5.a target
(audit-script parser refinement remained locked). §5.b scope
unchanged; §5.c regression case count preserved (12 total —
5 positive + 7 negative instead of 6 + 6, with case #7 now
documenting the row-5 gap); §5.d Phase 1 expected diff
narrowed to 5 flips; §5.e baseline narrowed from 120 → 119;
§3 gains one new deferral (row 5). Streak count increments as
as-recommended.

This is the third refinement in the M25.3 → M26 chain:
- M25.3 close-out estimated 2 false positives.
- SESSION_189 §3 tracing corrected to 6.
- SESSION_190 §2 pre-implementation refinement corrected to
  5 (nested-template-literal-attributable subset).

**Substrate lesson:** the §5.e two-source agreement
discipline (§5.d Phase 1 diff + Phase 2 per-row verification)
is the mechanical guard against this exact class of drift.
If M26 had recorded 120 / 154 directly from the M26.0
planning memo without §5.d Phase 1 diff verification, the
baseline in `CAPABILITY_MATRIX.md` would have been wrong by
one endpoint and every M27+ audit read would inherit the
error. The discipline caught it because Phase 1 asserts
"exactly the following changes appear, no more, no fewer" —
row 5's absence from the diff was the first observable signal
that its inclusion in the M26.0 estimate was mistaken.

## 4. Deferrals from M26 (all valid for later re-entry)

- **Row 5 `vehicles/<int:vehicle_id>/` public-fetch-helper
  regex refinement.** Deferred per M26.1-open §2 empirical
  discovery + user scope constraint. NEW M27+ candidate:
  extend `_HELPER_CALL_RE` to include public helpers
  (`getJSON` / `postJSON` / `patchJSON` / `putJSON` /
  `deleteJSON`), OR broaden `_PUBLIC_FETCH_RE` filters.
  Blast radius unknown pre-tracing; standard SESSION-189-§3-
  style verification required before scope commit.
- **Plain-string-literal false-positive investigation
  (rows 1–4 `chat/start/`, `chat/message/`,
  `chat/session/<uuid:session_id>/`, `leads/`).** Surfaced
  at SESSION_189 §3 but out of M26 scope per user
  constraint. Root cause is likely the
  `component_consumed` word-boundary check at
  `audit_operational_surface.py:1096` — the chat wrappers
  are `startChat` / `sendChatMessage` / `getChatSession` /
  `createLead` and are only called from `ChatWidget.tsx`
  and adjacent chat surfaces; the word-boundary regex may
  be mis-matching them. M27+ candidate.
- **Test-hygiene remediation (Candidate H).** 3 shared-DB
  non-idempotent journeys (`sales_manager/daily_startup`,
  `recon/workflow`, `office/accounting_workflow`) break
  full-suite runs on state-dirty DB. Kept separate from
  M26 per user constraint. Live M27+ candidate.
- **A2 (JE creation UI).** Direct operator-coverage
  candidate; kept elevated as leading M27 §5.a per user
  constraint at M26.0 open. Row 140
  `admin/accounting/journal-entries/` create endpoint
  remains genuinely uncovered post-M26 (reverse / retrieve
  / list wrappers all ship in `accountingApi.ts`; only the
  create wrapper is missing).
- **`recommend_disposition()` heuristic changes.** No
  endpoint disposition changed outside the 5 mechanical
  reclassifications. Any broader heuristic refinement is
  deferred pending evidence.
- **Audit script rewrite / restructure.** M26 fixed the
  narrow parser defect via minimal-blast-radius
  post-match refinement + shared-substrate extraction.
  Broader refactor (dedicated tokenizer class,
  TypeScript-AST-parser integration) deferred pending
  evidence that additional defects justify it.
- **Audit output format changes.** Markdown row shape,
  disposition legend, coverage summary format all
  unchanged. Any format refinement deferred.
- **All M25 §4 deferrals** — secondary "+ Record test
  drive" launch, clickable "Referred by" nav, named-
  platform adapters, attribution analytics, vehicle
  picker advanced filters, structured objection
  vocabulary, test-drive scheduling in advance,
  salesperson advisor gate. All remain valid M27+
  candidates with operator-evidence gates.
- **All pre-M25 durable deferrals** — Candidates T
  (real tester feedback), U (hosted-demo substrate), L
  (first-live-pilot staging), M (multi-operator support
  — breaks zero-drift streak with intent), D (LLM
  router / cost caps), C (F&I chargeback substrate), G
  (dashboard testid hardening). Gate conditions
  unchanged.

## 5. Durable design principles surfaced or reinforced

**Reinforced:**

- **Record empirical-discovery refinements honestly.**
  The M26.1-open row-5 reclassification is the fourth
  instance in the M24-M26 arc (M25.0 §5.b `platform`-
  not-persisted; M25.2-open §5.e admin/vehicles/-not-
  shipped; SESSION_189 §3 6-endpoint discovery;
  SESSION_190 §2 5-endpoint refinement). Every time,
  the refinement was presented with options +
  recommendation + user confirmation, counted as
  as-recommended, and preserved streak integrity. The
  pattern works because the target itself does not
  shift — only the underlying evidence is corrected.
- **Two-source agreement is the mechanical guard
  against baseline drift.** §5.e discipline caught the
  row-5 misclassification at Phase 1 diff verification
  (row 5 absent from expected reclassifications) —
  before the corrected number was recorded anywhere.
  Regeneration alone would have shipped a wrong
  number; per-row verification alone might have missed
  the diff shape; both together caught it.
- **Small bounded parser fixes inside the audit
  script are welcome standalone milestones when the
  blast radius exceeds sub-scope size.** M26 parallels
  M23.1 §5.d (verb-filter false-positive removal) in
  shape — same script, same file region, same
  regression-suite discipline, opposite orientation
  (M23.1 removed false positives; M26 removed false
  negatives). The parallel confirms audit-correctness
  work as a repeatable milestone shape.

**Surfaced (new at M26):**

- **Planning-substrate integrity is a valid reframe
  of the durable operational-coverage guiding
  question, not a departure from it.** The audit is
  the substrate that answers coverage; when the
  substrate under-reports by 3× (M25.3 estimate) or
  by 4% (real M26.1 delta), every future selection
  under the lens compounds the drift. Fixing the
  substrate *before* the next major planning cycle
  maximizes compound value. Captured in the M26
  planning memo framing block; carried forward as a
  candidate re-entry pattern for future audit- or
  measurement-tooling milestones.
- **DoD exception path (§5.g M21.0 Option B) applies
  cleanly to infrastructure-focused milestones.** M26
  invoked the exception path explicitly — planning
  infrastructure, not customer-facing behavior. No
  Playwright journey added or extended. Acceptance
  baseline held at 14 journeys. The exception path
  worked as intended; future audit-tooling /
  test-hygiene / CI-infrastructure milestones can
  follow the same pattern without stretching the DoD.

## 6. Streak accounting at M26 close

- **Zero-drift permission-class streak: 26 consecutive
  milestones (M10 → M26).** M26 added zero endpoints;
  no permission classes evolved. Extends the M25
  streak of 25 → 26.
- **Planning-time as-recommended streak: 5.** Enters
  M26 at 3 (M25.0 + M25.1 + M25.2 all locked as
  recommended after mid-planning refinements). M26.0
  locks as recommended after alternatives (A2, NEW
  audit-script refinement, H) presented under
  three-tier framing; user confirmed with five
  scope-discipline constraints added additively to §5
  (target unchanged). M26.1 locks as recommended
  after M26.1-open row-5 empirical refinement
  narrowed evidence without shifting target. **3 → 4
  → 5.** Historical run of 89 across M10 → M23
  preserved for the record.
- **DoD-exception-path invocation count:** first
  post-M21.0 exception invocation. Documented in this
  retrospective §2 + planning memo §5.g + start-here
  doc. Future audit-tooling / test-hygiene / CI-
  infrastructure milestones can cite this precedent.

## 7. Baselines at M26 close

- **Backend tests:** 4,805 pass, 1 skipped, 0 fail
  (was 4,793 at M25 close; +12 across new
  `test_audit_operational_surface.py` regression
  suite).
- **Frontend Vitest:** 226 pass across 32 files
  (unchanged — M26 does not touch `frontend/src/`).
- **Acceptance suite:** 14 journeys passing on clean
  DB (unchanged — §5.g exception path).
- **Migrations:** 0049 (unchanged — no model changes).
- **Zero-drift permission-class streak:** 26
  consecutive milestones (M10 → M26).
- **Planning-time as-recommended streak:** 5.
- **Audit artifact:** 154 endpoints, **119 covered /
  35 backend-only** (was 114 / 40 pre-fix; the 5-row
  reclassification is the mechanical result of the
  parser fix; §5.e two-source agreement confirms
  these are the true coverage numbers, not audit-
  tooling artifacts).
- **Audit `defer-candidate-O2` group:** 30 rows
  (was 35 pre-fix; -5 from the reclassifications).

## 8. Corrections (post-close)

None as of retrospective drafting. If any surface post-
close, append under this section with date + session +
correction summary + factual delta.

## 9. Evidence-based candidates for M27

**Elevated (highest recommendation strength at M27.0):**

- **A2 — Journal-Entry creation UI.** Kept elevated per
  user constraint at M26.0 open. Row 140
  `admin/accounting/journal-entries/` create endpoint
  remains genuinely uncovered post-M26 (reverse / retrieve
  / list wrappers all ship in `accountingApi.ts`; only the
  create wrapper is missing). Direct operator-coverage
  gain; small population (1-2 accounting users weekly)
  × moderate frequency; small scope; single-increment-
  shaped milestone.

**NEW audit-tooling candidates (surfaced during M26):**

- **Row 5 public-fetch-helper regex refinement.** Extend
  `_HELPER_CALL_RE` to include public helpers
  (`getJSON` / `postJSON` / etc.), OR broaden
  `_PUBLIC_FETCH_RE` filters. Blast radius unknown
  pre-tracing.
- **Plain-string-literal false-positive investigation
  (rows 1–4).** Requires SESSION-189-§3-style tracing to
  determine root cause (likely `component_consumed`
  word-boundary check).

**Elevated (unchanged from M25 close):**

- **H — test-hygiene remediation.** 3 shared-DB
  non-idempotent journeys. Kept separate from M26 per
  user constraint. High compound value as suite grows
  past 14 journeys.

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

**Standing question for M27.0 open:** which lens
governs § 5.a selection?

- Direct operator-coverage lens → A2 wins.
- Compound infrastructure integrity lens → row-5
  audit-parser refinement OR rows 1–4 investigation
  win, since they compound across every future
  candidate ranking.
- CI-stability lens → H wins as the suite grows.

M26 chose the compound-infrastructure framing because
the M25.3 → SESSION_189 → SESSION_190 chain of
estimate corrections proved the substrate was
load-bearing and drifting. M27 will need to decide
whether the drift is fully corrected or whether
another substrate refinement (rows 1–4 or row 5)
outweighs A2 on operator-coverage grounds. Present
alternatives at M27.0 open under the same three-tier
framing.

---

**Milestone 26 shipped in 2 sessions (SESSION_189 →
SESSION_190) — half the M25 velocity envelope by
design. All §5 locks held. Zero operator-facing
regressions. Corrected coverage baseline 119 / 154
recorded across all four §5.e sites after two-source
agreement.**
