---
title: "Milestone 26 — Audit-Script Parser Refinement (Planning-Substrate Integrity)"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_189 (skeleton + expansion + all §5 locks)
milestone: 26
milestone_name: "Audit-Script Parser Refinement (Planning-Substrate Integrity)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_25_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_25_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7z
  - backend/dealer_ai/scripts/audit_operational_surface.py
---

# Milestone 26 — Audit-Script Parser Refinement (Planning-Substrate Integrity)

> **Active planning memo.** Drafted + expanded + all §5 locks
> at SESSION_189 M26.0 open.
>
> **Session-numbering note:** the start-here doc that opened
> this session named it "SESSION_188," but the M25.3
> folded-close-out handoff (`SESSION_188_m25_inc3_close.md`)
> already occupies the 188 slot per the DOC_GOVERNANCE
> incrementing convention. This session is **SESSION_189**;
> corrected at M26.0 open and reflected in all §5, §7, §8
> references + the SESSION_189 handoff + the
> `00-START-NEXT-SESSION.md` overwrite.
>
> **§5.a locked at open** per an *independent recommendation
> under the planning-substrate integrity lens* (see §5.a). The
> primary operational-coverage guiding question (per M22 close
> durable) remains — but M26 answers a **prerequisite** to that
> question: *is the coverage evidence we use to answer it
> actually trustworthy?* The M25.3 close-out handoff scoped a
> 2-endpoint false-positive gap; SESSION_189 §3 audit
> regeneration + direct extractor tracing revealed the true
> nested-template-literal blast radius is **5 endpoints**
> (2.5× understatement). Every M27+ §5.a selection made from
> the current audit inherits that drift.
>
> **M26.1-open empirical refinement (SESSION_190 §2):** pre-
> implementation verification of the six SESSION_189-listed
> false positives revealed that row 5
> (`vehicles/<int:vehicle_id>/`, wrapper `fetchVehicleDetail`
> at api.ts:611) is NOT a nested-template-literal defect —
> it uses the public `getJSON` helper, which is entirely
> outside `_HELPER_CALL_RE`'s auth-helper regex (line 390).
> Its coverage gap is a separate defect (public-fetch-helper
> regex omission) that M26 does NOT address per the user
> scope constraint. Corrected M26.1 blast radius: **5
> endpoints** (rows 7, 16, 29, 111, 121). Corrected post-fix
> coverage baseline: **119 / 154** (not 120 / 154 as
> originally locked at M26.0 open). Row 5 is added to §3
> deferrals as a NEW M27+ candidate: **public-fetch-helper
> audit-tooling refinement**. §5.c regression test #6
> (the `getVehicleDetail` two-interpolation case)
> repurposed from a positive regression case to a negative
> documentation case per §5.c refinement. Streak counted
> as as-recommended: the refinement is an empirical-
> discovery correction of the underlying evidence, not a
> departure from the recommendation itself; §5.a target
> selection unchanged.
>
> **M26 is deliberately small.** One implementation increment
> plus close-out. The parser fix, targeted regression suite,
> audit regeneration, doc updates, and coordinated push are
> expected to fit inside a single session. Close-out folds per
> the M18 → M25 evidence-sized §5.h Option B posture unless
> evidence forces a split.
>
> **The anchor business question** — *Can future milestone
> selection rely on the operational-surface audit as
> trustworthy coverage evidence?* — governs every M26 scope
> decision. M26 does NOT ship a new operator surface. M26 does
> NOT change endpoint dispositions. M26 does ONE thing:
> corrects the frontend-consumer tokenizer so that six shipped
> wrappers using nested template literals + optional query
> strings are correctly recognized as covering their endpoints.
>
> Anchor cross-refs:
> - M25.3 handoff `SESSION_188_m25_inc3_close.md` — records
>   the 2-endpoint estimate that SESSION_189 §3 corrected to 6.
> - `docs/CAPABILITY_MATRIX.md` §7z — M25 shipped surface;
>   M26 does not touch operator-facing capability.
> - Memory record `feedback_audit_correctness_as_supporting_infra.md`
>   — durable principle: audit correctness is welcome
>   supporting infrastructure inside larger milestones or as a
>   bounded standalone milestone; every accuracy gain compounds
>   across future scope decisions.
> - M23.1 §5.d fix precedent — small bounded parser fix inside
>   the same audit script (`@api_view` verb-filter). M26 is
>   shaped identically.

## Guiding question (durable, per M22 close)

**Which candidate most increases operational coverage for a
dealership employee?**

**M26 answers the prerequisite question:** does the audit
substrate we use to answer that question tell us the truth?
When the substrate under-reports coverage by 3×, every future
target selection made under the lens is compromised. M26
restores substrate integrity so the M27+ candidate ranking
inherits accurate evidence.

## Preserve the M20–M25 operational contract (durable)

- **No operator-facing surface change.** M26 modifies the
  `audit_operational_surface.py` script only. Zero backend
  endpoints, zero frontend components, zero acceptance
  journeys added or removed.
- **No endpoint disposition changes without separate
  evidence.** M26 may not upgrade or downgrade any row from
  its current disposition category *except* for the six
  false positives whose upgrade is entirely mechanical
  (parser correctly identifies the pre-existing wrapper).
- **Zero-drift permission-class streak preserved at 25.**
  M26 adds zero endpoints; no permission classes evolve.
  Streak intended posture at M26 close: **26 consecutive
  milestones (M10 → M26).**
- **17-stage scrub stack unchanged.** M26 does not touch
  the LLM path.
- **Additive-only script change.** The `extract_frontend_
  consumers` regex + companion tokenizer are refined in a
  way that recognizes strictly *more* wrapper URL shapes;
  the fix must not shrink recognition on any shape the
  current parser already handles.

## Guiding principle (audit correctness as supporting infrastructure)

Per the durable memory record: audit-correctness work is
welcome as bounded scope whenever the audit is a
load-bearing input to a decision cycle. M26 elevates it to
a standalone milestone because (a) the M25.3 discovery
revealed the blast radius exceeds the "sub-scope" size, (b)
the fix is naturally self-contained, and (c) fixing it
before opening M27's §5.a selection maximizes compound
value.

**Analogous precedent:** M23.1 §5.d — the `@api_view`
verb-filter fix inside the same audit script. That fix
turned "false-positive coverage on GET wrappers prefix-
matching POST endpoints" into a clean audit. M26 turns
"false-negative coverage on nested-template-literal
wrappers" into a clean audit. Same shape, opposite
direction, same script.

## 0. Engineering practices to preserve from M2–M25

- **Tenant discipline.** N/A — no runtime code paths
  touched.
- **Deterministic script output.** The audit script writes
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  deterministically from the current repo state. M26
  preserves that determinism — the same repo state must
  produce the same audit artifact byte-for-byte.
- **Regression-test coverage.** Every parser branch that
  changes ships with a dedicated Python unit test
  asserting both the *tokenized URL expression* and the
  *normalized pattern* under `dealer_ai/tests/`.
- **Repo baseline discipline.** Backend 4,793 → **≥4,793 +
  N** where N counts the new parser regression tests.
  Frontend Vitest **226 unchanged**. Acceptance **14
  journeys unchanged** (no new journey per §5.g).
- **Zero-drift permission classes.** No endpoints added.
- **No LLM-path change.** N/A.
- **Coordinated push at milestone close, not per
  increment.** M26.1 (single implementation increment) +
  close-out fold per §5.h.

## 1. Business questions this milestone answers

**Primary — governs §5.a.** *Can future milestone
selection rely on the operational-surface audit as
trustworthy coverage evidence?*

**Secondary questions M26 answers along the way:**

1. Which frontend wrapper URL-expression shapes does the
   `extract_frontend_consumers` regex currently
   mis-tokenize? (Answered at SESSION_189 §3: nested
   template literals inside `${...}` interpolation with
   optional-querystring ternaries.)
2. What is the true M25-close-shipped coverage baseline
   after the parser fix? (Expected: **119 / 154**
   post-M26.1-open refinement, confirmed only after the
   regenerated artifact and direct repository inspection
   agree per §5.d. Was 120 / 154 at M26.0 open; corrected
   at M26.1 open when row 5 was reclassified as a
   separate defect.)
3. Does the parser fix over-classify any unconsumed
   endpoint as covered? (Answered by §5.c negative-case
   regression suite.)
4. Are there additional false-negative shapes beyond
   the trailing-optional-querystring pattern that
   SESSION_189 §3 tracing surfaced? (Two suspected:
   plain-string-literal wrappers on `chat/start/`,
   `chat/message/`, `chat/session/`, `leads/` where the
   component-import check may be masking legitimate
   coverage. **Explicitly deferred from M26 scope —
   see §3.** Requires separate evidence before scope.)

## 2. What existing primitives extend

**Script (one file, one change surface):**

- `backend/dealer_ai/scripts/audit_operational_surface.py`
  — refine `_HELPER_CALL_RE` (line 390) and/or the
  `extract_frontend_consumers` tokenizer (line 607) so the
  template-literal branch recognizes nested `${...}`
  expressions and does not terminate the outer template
  string at an inner backtick.
- `normalize_frontend()` (line 207) — unchanged. Already
  correctly collapses `${...}` to `{PARAM}` and strips
  query strings. The bug is upstream in raw expression
  capture.

**Tests (new dedicated file):**

- `backend/dealer_ai/tests/test_audit_operational_surface.py`
  — NEW. Six positive regression tests (one per confirmed
  false positive) + representative negative cases (see
  §5.c). Runs under existing `python3 manage.py test
  dealer_ai` invocation. No Django test-DB usage — pure
  Python unit tests over the script's public functions
  (`extract_frontend_consumers`, `normalize_frontend`,
  `cross_reference`).

**Artifact (regenerated, not hand-edited):**

- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` —
  regenerated by the fixed script. **Five** rows flip
  from `defer-candidate-O2` → `covered` (refined at
  SESSION_190 §2 from six). Coverage summary updates
  from **114 / 154 → 119 / 154**. Row wrapper-ordering
  diffs (like the SESSION_189 §3 regen's
  `admin/vendors/` re-order) are absorbed as normal
  script output.

**Docs (update-in-place per DOC_GOVERNANCE):**

- `docs/CAPABILITY_MATRIX.md` §7 — add a §7α "M26 shipped
  surface" block noting the audit-tooling refinement,
  the 6-endpoint reclassification, and the corrected
  coverage baseline. No capability rows are added or
  changed.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — M26 entry
  in the shipped table (name, ship session, incremental
  scope: audit-tooling correctness, no operator-facing
  change).
- `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md` — NEW at
  M26 close per the standard retrospective shape.
- `00-START-NEXT-SESSION.md` — overwritten at M26 close
  with SESSION_189 priorities (A2 elevated as leading
  §5.a candidate per user constraint).

## 3. What's NOT in this milestone (deferrals)

- **Plain-string-literal false-positive investigation
  (rows 1–4 `chat/start/`, `chat/message/`,
  `chat/session/<uuid:session_id>/`, `leads/`).** These
  four rows show `defer-candidate-O2` in the current
  audit despite wrappers existing as plain string
  literals in `api.ts` (lines 138, 142, 149, 584). Root
  cause is *not* the nested-template-literal defect —
  likely the `component_consumed` word-boundary check
  at `audit_operational_surface.py:1096` failing to
  detect the wrapper's callers, or a different
  tokenizer branch. **Explicitly deferred from M26.**
  Requires separate SESSION_189 §3-style tracing before
  scope commit. Re-entry candidate for M27+ once
  evidence surfaces.
- **Row 5 `vehicles/<int:vehicle_id>/` public-fetch-
  helper regex refinement (NEW at SESSION_190 §2).**
  The wrapper `fetchVehicleDetail` at api.ts:611 uses
  the public `getJSON` helper, which is not enumerated
  in `_HELPER_CALL_RE` (audit script line 390 —
  matches only `authGetJSON/authPostJSON/authPatchJSON/
  authPutJSON/authDelete/authPostForm`). The
  `_PUBLIC_FETCH_RE` alternate path (line 508) matches
  only literal `fetch(...)` calls, and further requires
  `/api/dealer-ai/` or `${API_BASE}` in the URL.
  `fetchVehicleDetail` matches neither path — its
  coverage gap is a separate defect from the nested-
  template-literal one M26 addresses. **Explicitly
  deferred from M26** per the user scope constraint
  ("scope strictly to the nested-template-literal and
  optional-query-string parsing defect"). §5.c
  regression case #7 documents this gap explicitly
  (asserts `fetchVehicleDetail` remains invisible
  post-M26-fix). M27+ candidate: extend
  `_HELPER_CALL_RE` to include `getJSON/postJSON/
  patchJSON/putJSON/deleteJSON` public helpers, OR
  broaden `_PUBLIC_FETCH_RE` filters. Blast radius
  of that fix is unknown pre-tracing; standard SESSION_
  189-§3-style verification required before scope
  commit.
- **Test-hygiene remediation (Candidate H).** Kept
  separate per user constraint. Both M26 and H are
  infrastructure-shaped, but combining them broadens
  scope past the "keep M26 intentionally small"
  constraint and mixes two distinct decision axes
  (planning-substrate integrity vs CI stability under
  suite growth). H remains a live M27+ candidate.
- **A2 (JE creation UI).** Kept as the leading direct
  operator-coverage candidate for M27 per user
  constraint. If the corrected audit reveals a
  stronger genuine gap at M27.0 open (i.e. an
  operator-facing endpoint reclassified to
  `defer-candidate-O2` legitimately, or a previously-
  masked gap surfaces), the M27.0 recommendation may
  re-rank. Default posture at M26 close: A2 elevated.
- **Endpoint disposition changes unrelated to the six
  known false positives.** M26 must not upgrade or
  downgrade dispositions on rows the parser fix does
  not directly reclassify. The `recommend_disposition()`
  heuristic (script line 782) is out of scope.
- **Audit script rewrite / restructure.** M26 fixes the
  narrow parser defect. Any broader refactor
  (dedicated tokenizer class, TS AST parser
  integration, etc.) is deferred pending evidence
  that additional defects justify it.
- **Audit output format changes.** Markdown row shape,
  disposition legend, coverage summary format — all
  unchanged. Diff at M26.1 close is expected to be
  strictly: (a) **5** rows flip `defer-candidate-O2` →
  `covered` with wrapper columns populated (refined at
  SESSION_190 §2 from 6), (b) coverage summary
  numerator updates **114 → 119**.
- **CAPABILITY_MATRIX §7 through §7z rewrite.** M26
  adds a §7α block; no historical §7 rows are
  rewritten or removed per DOC_GOVERNANCE.

**Playwright journey binding for DoD compliance (M21.0
§5.f Option B exception path):** M26 modifies planning
infrastructure rather than customer-facing operational
behavior. §5.g documents the exception path explicitly.
No Playwright journey change is required. Acceptance
baseline remains **14 journeys unchanged**.

## 4. What existing tests bind

- **Backend suite (4,793 pass, 1 skipped)** — M26 must
  hold this baseline. Regression tests added under §5.c
  increment it to **≥4,793 + N**; the exact N depends
  on how granularly the negative-case suite splits (see
  §5.c). No existing test is expected to break — the
  parser change is additive-forever (recognizes
  strictly more wrapper shapes).
- **Frontend Vitest (226 pass)** — unchanged. M26 does
  not touch `frontend/src/`.
- **Acceptance (14 journeys, clean-DB dry-run ~30s)** —
  unchanged. M26 does not add or extend any journey.
  The 3 shared-DB non-idempotent journeys (H candidate)
  remain outstanding, on their own re-entry path.
- **`test_audit_service.py`** (existing) — the pre-M26
  audit-related test file. Unrelated to the parser
  defect (it exercises different audit-adjacent
  logic). M26 leaves it untouched.

## 5. Load-bearing decisions

### §5.a — Milestone target selection

**LOCKED at M26.0 open as the audit-script parser
refinement**, framed as **planning-substrate integrity**
rather than operational coverage.

**Independent recommendation rationale (SESSION_189
§4):** Under the durable operational-coverage guiding
question, three candidates were elevated at M26.0 open —
A2 (JE creation UI, direct operator gain), the NEW
audit-script refinement (indirect, planning-substrate),
and H (test-hygiene, CI stability). The AI's independent
recommendation was the audit-script refinement,
primarily because the SESSION_189 §3 audit regeneration
revealed the M25.3 handoff's 2-endpoint estimate
understated the true blast radius by 3× (6 confirmed
false positives). Every M27+ target selection made
under the operational-coverage lens depends on the
audit being accurate — fixing the audit *before* the
next major candidate ranking maximizes compound value.

The user confirmed the recommendation and added five
scope-discipline constraints (see §5.b–§5.e). The user
also constrained A2 to remain elevated as the leading
M27 §5.a candidate and H to remain separate — both
constraints preserved in §3 deferrals.

**Streak accounting (see §8):** locked as recommended
after alternatives presented → planning-time
as-recommended streak increments **3 → 4** at M26.0
open.

### §5.b — Parser-fix scope (nested-template-literal + optional-querystring only)

**LOCKED as narrow parser fix inside
`extract_frontend_consumers` (audit script line 607),
strictly bounded to the two coupled defects**:

1. **Nested-template-literal tokenization.** The current
   `_HELPER_CALL_RE` at line 390–403 uses `` `[^`]*(?:`|$) ``
   for the template-literal branch. This regex terminates
   the outer template string at the first inner backtick,
   which is wrong when the outer template contains a
   `${...}` interpolation whose body is itself a template
   literal (the SESSION_189 §3 pattern:
   `` `/admin/vehicles/${qs ? `?${qs}` : ""}` ``). Fix:
   replace the regex template-literal branch with a
   balanced-brace-aware tokenizer that tracks `${...}`
   nesting depth and skips inner backticks that appear
   inside an active interpolation.
2. **Optional-querystring pattern normalization.** The
   `normalize_frontend()` function (line 207) already
   handles the collapsed `${...}` → `{PARAM}` translation
   correctly (verified at SESSION_189 §3 via direct
   invocation). The bug is upstream — once the
   tokenizer captures the full expression, normalization
   produces the correct `/path/{PARAM}/` shape, and
   `cross_reference()`'s candidate-pattern set
   (`endpoint + "{PARAM}/"` at line 712) matches. No
   change to `normalize_frontend` is expected.

**Implementation shape (recommended, subject to fine-tuning at M26.1 open):**

- Replace the template-literal branch of `_HELPER_CALL_RE`
  with a bounded regex that captures only the *start*
  of the template literal, then use a companion function
  (`_extract_balanced_template_literal(source, start_pos)
  -> tuple[str, int]`) to walk the source character-by-
  character, tracking `${` depth, and returning the
  full expression + end position.
- OR keep the regex as-is for non-template-literal
  branches and add a post-match refinement step: if the
  captured template contains an unterminated `${` (i.e.
  the balanced-brace parser detects the tokenizer stopped
  too early), re-tokenize from `m.start()` with the
  companion function.

**Preferred approach:** the second option (post-match
refinement). Lower blast radius, preserves the fast-path
regex for the majority of wrappers, isolates the fix.

**Out of scope for §5.b:**

- Any change to `normalize_frontend()`.
- Any change to `cross_reference()` candidate-pattern
  generation.
- Any change to `_HELPER_TO_VERB` (M23.1 §5.d fix
  substrate — untouched).
- Any change to disposition heuristics.
- Any change to markdown emission.
- Any change to backend endpoint extraction.
- Any change to service-verb enumeration.

### §5.c — Regression-test surface

**LOCKED as dedicated test file
`backend/dealer_ai/tests/test_audit_operational_surface.py`
covering six positive cases + representative negative
cases.**

**Positive regression cases (one per confirmed
nested-template-literal false positive from SESSION_189
§3 tracing, refined at SESSION_190 §2):**

1. `` `/admin/vehicles/${qs ? `?${qs}` : ""}` `` → tokenizer
   captures full expression; `normalize_frontend` returns
   `/admin/vehicles/{PARAM}/`; the cross-reference against
   backend endpoint `admin/vehicles/` yields a `covered`
   match with wrapper `listAdminVehicles`.
2. `` `/admin/test-drives/list/${qs ? `?${qs}` : ""}` ``
   → analogous, wrapper `listTestDrives`.
3. `` `/admin/leads/${qs ? `?${qs}` : ""}` `` →
   analogous, wrapper `fetchAdminLeads`.
4. `` `/admin/audit-events/${qs ? `?${qs}` : ""}` `` →
   analogous, wrapper `fetchAuditEvents`.
5. `` `/admin/be-backs/list/${qs ? `?${qs}` : ""}` `` →
   analogous, wrapper `listBeBacks`.

**(Original positive case #6 —
`` `/vehicles/${vehicleId}/${qs ? `?${qs}` : ""}` `` /
`fetchVehicleDetail` — moved to negative case #7 per
SESSION_190 §2 refinement. Root cause is separate
public-`getJSON`-helper regex gap, not nested-template-
literal tokenization; the parser fix will not reclassify
it.)**

**Negative regression cases (representative — do not
over-classify):**

1. A wrapper URL expression with a legitimate `?` in a
   query-string position but no template nesting (e.g.
   `` `/some/path/?fixed=1` ``) — tokenizer must not
   accidentally include the query string in the
   normalized pattern.
2. A wrapper URL expression that references an endpoint
   which genuinely does not exist in `urls.py` — the
   fixed parser must not manufacture a match. Assert
   that the fabricated wrapper is captured as a consumer
   with a normalized pattern that finds no endpoint.
3. A wrapper URL expression using the fast-path
   (plain single-`${...}`, no nested template)
   — assert the post-match refinement does NOT fire
   for these, i.e. the fast-path regex output stands
   unchanged. Guards against a refinement pass that
   silently rewrites already-correct output.
4. An identifier-passed URL (e.g. the M22.1 §5.e
   `_resolve_variable_url` case: `authGetJSON(path)`
   where `path` is defined earlier via `const path =
   ...`) — assert the identifier-resolution path
   still works. Guards against the parser fix
   incidentally breaking the M22.1 lookback.
5. An empty template literal (`` `` ``) or a template
   with only interpolation (`` `${x}` ``) — assert
   the tokenizer terminates cleanly and produces a
   reasonable (possibly empty) normalized pattern
   without raising.
6. A malformed / unterminated template literal (backtick
   opens but never closes before EOF) — assert the
   tokenizer terminates without hang, returning the
   partial capture and a sentinel end-position matching
   the current behavior for malformed input.
7. **NEW at SESSION_190 §2** —
   `fetchVehicleDetail`'s `getJSON` call at api.ts:626
   pattern
   (`` `/vehicles/${vehicleId}/${qs ? `?${qs}` : ""}` ``).
   Documents that even after the nested-template-literal
   fix, this call remains **invisible** to the audit
   script because `getJSON` is not enumerated in
   `_HELPER_CALL_RE`. Assertion: no consumer with wrapper
   `fetchVehicleDetail` appears in `extract_frontend_
   consumers(api_source)` output. The test's docstring
   references this refinement and the M27+ public-fetch-
   helper deferral in §3.

**Verb-filter co-verification (M23.1 §5.d substrate
preserved):** at least one positive case (recommended:
case 1 `admin/vehicles/`, since `listAdminVehicles` is
a GET wrapper against a genuinely-GET endpoint) must
assert that the resolved GET-wrapper is *not*
incorrectly claimed against an unrelated POST endpoint
at the same URL prefix. Guards against silent regression
of the M23.1 verb filter.

**Test count target: 12 positive + negative test
methods** (5 positive + 7 negative, refined at
SESSION_190 §2 from 6 + 6). Backend baseline expected
to move **4,793 → 4,805** at M26.1 close (±1–2
depending on test grouping).

### §5.d — Audit regeneration + manual verification protocol

**LOCKED as a two-phase protocol at M26.1 close.**

**Phase 1 — Regenerate:** After the §5.b fix + §5.c
tests land green, invoke `python3 -m
dealer_ai.scripts.audit_operational_surface` once. The
artifact `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
is expected to change in exactly the following ways
(refined at SESSION_190 §2 — row 5 removed):

- Coverage summary numerator: **114 → 119**.
- Row 7 (`admin/leads/`) — populated with `api.ts:284
  fetchAdminLeads`; disposition flips → `covered`.
- Row 16 (`admin/audit-events/`) — populated with
  `api.ts:341 fetchAuditEvents`; disposition flips
  → `covered`.
- Row 29 (`admin/vehicles/`) — populated with
  `salesApi.ts:257 listAdminVehicles`; disposition
  flips → `covered`.
- Row 111 (`admin/test-drives/list/`) — populated with
  `salesApi.ts:204 listTestDrives`; disposition flips
  → `covered`.
- Row 121 (`admin/be-backs/list/`) — populated with
  `salesApi.ts:425 listBeBacks`; disposition flips
  → `covered`.
- **Row 5 (`vehicles/<int:vehicle_id>/`) remains
  `defer-candidate-O2` post-fix** — its wrapper
  `fetchVehicleDetail` uses public `getJSON`, invisible
  to `_HELPER_CALL_RE`. Documented as new §3 deferral;
  M27+ candidate.
- No other row semantically changes. Cosmetic
  wrapper-ordering shifts (like the SESSION_189 §3
  regen's `admin/vendors/` row 42 re-order) are
  acceptable script-deterministic output and do not
  constitute scope creep.

**Phase 2 — Manual verification (one row at a time,
all five):** For each of the five reclassified rows
(rows 7, 16, 29, 111, 121 per SESSION_190 §2
refinement), open the wrapper's source file at the
reported `{filename}:{line}` and confirm:

1. The wrapper exists at the reported line.
2. The wrapper's HTTP helper (`authGetJSON` /
   `authPostJSON` / etc.) matches the endpoint's
   declared methods per `extract_view_methods()`.
3. The wrapper is imported and called by at least one
   non-test `.tsx` or `.ts` component under
   `frontend/src/` (grep for the wrapper name with a
   word boundary).

If any row fails any of the three checks, the
reclassification is not real and the parser fix has a
subtler defect than §5.b captured — halt M26.1 close-
out, document the discrepancy, treat as a §5.b
implementation gap rather than a §5.d verification
failure. Do NOT patch around it by hand-editing the
audit artifact.

### §5.e — Coverage-baseline update discipline

**LOCKED as a two-source agreement requirement.**

The corrected coverage baseline of **119 / 154**
(refined at SESSION_190 §2 from 120 / 154 after row 5
reclassified as separate defect) is recorded in
`docs/CAPABILITY_MATRIX.md` §7α and elsewhere ONLY
after both of the following agree:

1. **Regenerated artifact.** The refreshed
   `M21_OPERATIONAL_SURFACE_AUDIT.md` coverage summary
   reads `114 → 119`.
2. **Direct repository inspection.** All **five** §5.d
   Phase 2 manual verifications pass (refined at
   SESSION_190 §2).

If either source disagrees, the baseline is NOT
updated. The M25.3 handoff's 2-endpoint understatement
(corrected to 6 at SESSION_189 §3, then to 5 at
SESSION_190 §2 pre-implementation refinement) is
precisely the failure mode this discipline prevents
— rely on one source without cross-checking the other
and the number that lands in the milestone record is
wrong. This discipline is written into §5.d Phase 2
mechanically (fail-halt on any mismatch) but also
recorded here as the *reason* the mechanical check
exists.

**Recording sites for the corrected baseline (in order,
at M26 close):**

- `docs/CAPABILITY_MATRIX.md` §7α block.
- `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md` §1 shipped
  scope summary.
- `docs/handoffs/SESSION_NNN_m26_inc1_parser_fix.md`
  (or `SESSION_NNN_m26_close.md` if folded) baseline
  block.
- `00-START-NEXT-SESSION.md` operational-state block.

### §5.f — Increment shape

**LOCKED as 1 implementation increment + close-out,
with close-out folding per §5.h Option B unless
evidence forces a split.**

- **M26.0 — Planning refinement + target selection
  (this session, SESSION_189).** Locks all §5
  decisions. Ships the M26 memo + the SESSION_189
  handoff. **No code, no push.**
- **M26.1 — Parser fix + regression tests + audit
  regeneration + doc updates.** Backend: parser
  refinement per §5.b + regression suite per §5.c.
  Artifact: regenerated audit per §5.d. Docs:
  §5.e updates. **~1 session (SESSION_190).**
- **M26.2 — Close-out** (retrospective + coordinated
  push). **Folds into M26.1 close per §5.h Option B
  unless verification surfaces §5.d discrepancies.**

**Total: 1–2 sessions.** Half the M25 velocity envelope
by design — M26 is intentionally the smallest full
milestone since M12.

### §5.g — DoD compliance (M21.0 §5.f exception path)

**LOCKED with the exception path explicitly invoked.**

Per the M21.0 §5.f Option B DoD amendment: every
future customer-facing milestone must add or update at
least one Playwright operational journey, OR
explicitly document in §3 why no journey change is
required.

**M26 is not a customer-facing milestone.** M26
modifies planning infrastructure (the audit script)
rather than operator or customer behavior. No new
operator surface ships. No existing operator surface
changes shape or contract. The acceptance suite's 14
journeys remain unchanged — they already exercise
the shipped operator surfaces the audit describes;
those journeys are unaffected by the audit script's
tokenizer.

The exception path is documented here (§5.g) and
mirrored in §3 (deferrals section). At M26 close the
retrospective §journey-plan section explicitly notes
"no journey change; audit-tooling refinement; §5.g
exception path invoked per M21.0 §5.f."

### §5.h — Close-out posture

**LOCKED as evidence-sized Option B (per M18 → M25
precedent).**

If M26.1 ships cleanly — parser fix green, regression
suite green, audit regeneration produces exactly the
six expected reclassifications per §5.d Phase 1, all
six manual verifications per §5.d Phase 2 pass,
docs update-in-place with no anomalies — **fold the
close-out into the M26.1 session** (retrospective +
coordinated push in the same session). Otherwise
promote to a separate M26.2 close-out session.

Push executes **once**, at the end of the milestone,
per M18 → M25 cadence. No per-increment pushes.
Expected commit count: **2** (M26.1 implementation +
hash backfill) if folded, **3–4** if split.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_RETROSPECTIVE.md` §8 + §9
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (current 114 / 154 baseline; source of truth pre-fix)
7. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped surface)
   + §7α (M26 audit-tooling refinement, added at close)
8. `backend/dealer_ai/scripts/audit_operational_surface.py`
   (implementation source of truth; the artifact is a
   deterministic output of this file + repo state)
9. `docs/handoffs/SESSION_188_m25_inc3_close.md`
   (M25.3 close-out; records the 2-endpoint estimate
   SESSION_189 §3 corrected to 6)
10. Memory record
    `feedback_audit_correctness_as_supporting_infra.md`
    (durable principle governing M26 framing)

## 7. Sequencing

**M26.0 (SESSION_189, this session)** — planning
refinement + target selection + all §5 locks. Ships
memo + handoff. No code, no push.

**M26.1 (SESSION_190)** — parser fix + tests + audit
regen + docs. In order:

1. Verify M25 close baseline holds (backend 4,793 pass,
   frontend 226 pass, acceptance 14 journeys clean-DB,
   HEAD at `6a3efbb`).
2. Refine `_HELPER_CALL_RE` template-literal branch OR
   add post-match refinement per §5.b preferred
   approach.
3. Add `backend/dealer_ai/tests/test_audit_operational_
   surface.py` with **5 positive + 7 negative**
   regression tests per §5.c (refined SESSION_190 §2).
4. Run `python3 manage.py test dealer_ai` — assert
   green (4,793 → ~4,805).
5. Invoke `python3 -m dealer_ai.scripts.audit_operational
   _surface` — regenerate the artifact.
6. Diff the regenerated artifact against the pre-fix
   version. Assert exactly the **five** §5.d Phase 1
   expected reclassifications appear (rows 7, 16, 29,
   111, 121), no more, no fewer.
7. Perform §5.d Phase 2 manual verification on each of
   the **five** rows. If any fails: halt, document,
   treat as §5.b implementation gap.
8. Update `docs/CAPABILITY_MATRIX.md` with §7α block.
9. Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` M26
   entry.
10. Draft `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md`.
11. Overwrite `00-START-NEXT-SESSION.md` with SESSION_191
    priorities (A2 elevated as leading §5.a candidate;
    H remains separate; row 5 public-fetch-helper
    refinement as NEW M27+ candidate; corrected
    119 / 154 baseline).
12. Compose M26.1 handoff.
13. Coordinated push (M26.1 commit + hash backfill).
14. If any step 6–7 discrepancy: promote close-out to
    M26.2 in a new session.

**M26.2 (SESSION_191, only if split)** — close-out.
Retrospective + coordinated push of any deferred M26
work.

## 8. Streak accounting (M26)

- **Zero-drift permission-class streak** — enters M26
  at **25 consecutive milestones (M10 → M25)**. M26
  adds zero endpoints. Intended posture at M26 close:
  extend to **26 consecutive milestones (M10 → M26)**.
- **Planning-time as-recommended streak** — enters
  M26 at **3** (M25.0 + M25.1 + M25.2 all locked as
  recommended after mid-planning refinements).
  Historical run of 89 across M10 → M23 preserved
  for the record. M26.0 opens with an AI recommendation
  presented under the planning-substrate integrity
  lens (a *reframe* of the durable operational-coverage
  guiding question, not a departure from it); the
  user confirmed the recommendation and added five
  scope-discipline constraints (§5.b–§5.e narrowing,
  A2 posture, H separation). All five constraints
  were incorporated additively into the corresponding
  §5 sections; the target itself did not shift. **M26.0
  counts as as-recommended → streak increments 3 → 4.**

## 9. Non-goals for the remaining M26 increments

- ❌ Do NOT touch any `frontend/src/` file. M26 is
  audit-script-only.
- ❌ Do NOT touch any backend view, model, migration,
  serializer, permission class, or `urls.py`. M26 is
  audit-script-only.
- ❌ Do NOT add, remove, or extend any Playwright
  journey. §5.g exception path invoked; acceptance
  baseline unchanged.
- ❌ Do NOT change any endpoint disposition beyond the
  **five** mechanical reclassifications the parser fix
  produces (rows 7, 16, 29, 111, 121; refined at
  SESSION_190 §2 from six). `recommend_disposition()`
  heuristic is out of scope per §3.
- ❌ Do NOT investigate the plain-string-literal
  false-positive suspicion on rows 1–4 (`chat/start/`
  etc.) within M26. Deferred to M27+ per §3.
- ❌ Do NOT combine test-hygiene (Candidate H) into
  M26. Kept separate per user constraint / §3.
- ❌ Do NOT hand-edit `M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Regenerate only. If the regenerated artifact
  disagrees with expectation, fix the script — never
  the artifact.
- ❌ Do NOT record the corrected 119 / 154 baseline
  without both §5.e sources agreeing.
- ❌ Do NOT push per-increment. Coordinated push at
  M26 close per §5.h.
- ❌ Do NOT let M26 broaden into a general "audit
  quality" milestone. The parser defect is precisely
  scoped; any adjacent tooling refinements are M27+
  candidates with their own evidence requirements.
- ❌ Do NOT skip the §5.d Phase 2 per-row manual
  verification. The M25.3 → SESSION_189 §3
  understatement is the load-bearing evidence that
  regeneration alone is insufficient.
