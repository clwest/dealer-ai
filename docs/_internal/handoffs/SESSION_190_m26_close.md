---
title: "SESSION_190 handoff — Milestone 26 · Increment 1 + close-out (M26.1 shipped; M26.2 folded per §5.h Option B)"
status: historical
type: handoff
date: 2026-08-03
session: 190
milestone: 26
milestone_status: shipped
milestone_name: "Audit-Script Parser Refinement (Planning-Substrate Integrity)"
increment: 1
increment_status: shipped
commit: 228ec1d
folded_close_out: true
---

# SESSION_190 — Milestone 26 · Increment 1 + close-out (M26.1 shipped; M26.2 folded per §5.h Option B)

> **Close-out fold:** all §5.d checkpoints passed cleanly at
> M26.1; M26.2 folded into this session per §5.h Option B
> (M18 → M25 precedent). Retrospective + all §5.e doc updates
> + start-here overwrite + this handoff all land at
> SESSION_190 end. Expected M26 commit count at coordinated
> push: 4 (M26.0 planning + hash backfill from SESSION_189;
> M26.1 close + hash backfill from SESSION_190).

## What shipped

M26.1 delivered the narrow parser fix + regression suite +
audit regeneration + all §5.e doc updates that constitute the
full M26 implementation. Zero operator-facing surface change;
zero endpoint additions; zero backend runtime behavior
touched.

### M26.1-open §2 empirical refinement (blast radius 6 → 5)

Pre-implementation verification of the six SESSION_189-listed
false positives revealed row 5 `vehicles/<int:vehicle_id>/`
uses public `getJSON` (not `authGetJSON`) at api.ts:611. Its
coverage gap is a separate `_HELPER_CALL_RE` regex-omission
defect (public helpers are not enumerated); the M26 parser
fix would NOT reclassify it regardless of implementation
quality. Corrected M26.1 blast radius: **5 endpoints**
(rows 7, 16, 29, 111, 121). Corrected post-fix coverage
baseline: **119 / 154** (was projected as 120 / 154 at M26.0
open). Row 5 added to M26 planning memo §3 as NEW M27+
candidate. §5.c regression case #6 (`fetchVehicleDetail`
two-interpolation) repurposed to negative case #7 documenting
the M27+ deferral. Planning memo + start-here doc refined
additively without shifting §5.a target — counted as
as-recommended per the durable "record empirical-discovery
refinements honestly" principle. Streak → +1.

### Parser fix (§5.b)

**File:** `backend/dealer_ai/scripts/audit_operational_
surface.py`.

- **New helper `_extract_balanced_template_literal(source,
  start_pos) -> tuple[str, int]`** (~24 lines).
  Extracted the existing balanced-brace walking logic from
  `_extract_url_literals` (lines 462-484). Walks from an
  opening backtick, tracks `${...}` interpolation depth,
  handles inner backticks correctly, and returns the full
  literal + end position. Terminates cleanly on malformed
  input (returns partial + `len(source)`).
- **`_extract_url_literals` refactored** to delegate to the
  shared substrate. Behavioral shape preserved.
- **`extract_frontend_consumers` post-match refinement.**
  After the fast-path `_HELPER_CALL_RE` produces a match on
  a template-literal-branch capture, count `${` opens vs `}`
  closes in the raw URL expression. If opens > closes, the
  tokenizer stopped at an inner backtick — re-tokenize from
  `m.start(2)` (the opening-backtick position) with the
  balanced parser. Preserves the fast-path regex for the
  majority of wrappers.
- **Untouched per §5.b out-of-scope discipline:**
  `normalize_frontend`, `_HELPER_TO_VERB`,
  `cross_reference`, `recommend_disposition`, all
  markdown-emission logic.

### Regression suite (§5.c)

**File:** `backend/dealer_ai/tests/test_audit_operational_
surface.py` (new).

- **12 test methods across 2 classes** (5 positive + 7
  negative, refined from 6 + 6 at M26.1 open per §2).
- **Positive cases** — one per confirmed nested-template-
  literal false positive:
  - `test_row_7_admin_leads` — `fetchAdminLeads`
    (api.ts:283).
  - `test_row_16_admin_audit_events` — `fetchAuditEvents`
    (api.ts:340).
  - `test_row_29_admin_vehicles` — `listAdminVehicles`
    (salesApi.ts:256; shipped since M25.2).
  - `test_row_111_admin_test_drives_list` — `listTestDrives`
    (salesApi.ts:203; shipped since M11.6).
  - `test_row_121_admin_be_backs_list` — `listBeBacks`
    (salesApi.ts:424).
- **Negative cases** —
  - `test_negative_1_fixed_query_string` — legitimate `?`
    in URL without template nesting; `normalize_frontend`
    strips the query string.
  - `test_negative_2_nonexistent_endpoint` — wrapper against
    a fake path; parser captures the wrapper but does not
    manufacture coverage downstream.
  - `test_negative_3_fast_path_unchanged` — plain single
    `${var}` interpolation; post-match refinement does NOT
    fire (guards against silent rewrite).
  - `test_negative_4_identifier_lookback_preserved` — M22.1
    §5.e substrate; identifier-passed URL via
    `_resolve_variable_url` still resolves.
  - `test_negative_5_verb_filter_substrate_preserved` —
    M23.1 §5.d substrate; `_HELPER_TO_VERB` map unchanged
    (all 6 entries verified).
  - `test_negative_6_malformed_template_no_hang` —
    unterminated template returns partial + `len(source)`,
    no hang.
  - `test_negative_7_public_get_json_still_invisible` —
    M26.1 §5.b + §3 scope boundary; documents that public
    `getJSON` wrappers remain invisible until M27+ fix.
- **All 12 pass first run.** Pure `SimpleTestCase` — no
  Django test-DB usage; fast (~0.001s).

### Audit regeneration + §5.d two-source agreement

**Phase 1 — Regenerate.**
`python3 -m dealer_ai.scripts.audit_operational_surface`
produces exactly the expected diff:

| Change | Pre-fix | Post-fix |
|---|---|---|
| Coverage summary numerator | 114 | **119** |
| Backend-only | 40 | **35** |
| `defer-candidate-O2` group | 35 | **30** |
| Row 7 `admin/leads/` | `defer-candidate-O2` (—) | `covered` (`api.ts:283 fetchAdminLeads`) |
| Row 16 `admin/audit-events/` | `defer-candidate-O2` (—) | `covered` (`api.ts:340 fetchAuditEvents`) |
| Row 29 `admin/vehicles/` | `defer-candidate-O2` (—) | `covered` (`salesApi.ts:256 listAdminVehicles`) |
| Row 111 `admin/test-drives/list/` | `defer-candidate-O2` (—) | `covered` (`salesApi.ts:203 listTestDrives`) |
| Row 121 `admin/be-backs/list/` | `defer-candidate-O2` (—) | `covered` (`salesApi.ts:424 listBeBacks`) |
| Row 42 `admin/vendors/` | wrapper order A | wrapper order B (cosmetic; script-deterministic) |
| Row 5 `vehicles/<int:vehicle_id>/` | `defer-candidate-O2` (—) | `defer-candidate-O2` (—) UNCHANGED per §3 |
| Per-module backend-only counts | ... | -5 across affected modules |

No other row semantically changes.

**Phase 2 — Per-row manual verification.** For each of the
5 reclassified rows:

- Wrapper exists at reported `filename:line` ✓.
- Helper is `authGetJSON` → verb GET → endpoint methods per
  `extract_view_methods` are `['GET']` on all 5 views
  (`admin_lead_list`, `admin_audit_events`,
  `admin_vehicle_list`, `admin_test_drive_list`,
  `admin_be_back_list`) ✓.
- Wrapper imported by ≥1 non-test `.tsx` / `.ts` component
  (68 total imports across 17 files) ✓.

**Two-source agreement confirmed.** Corrected 119/154
baseline recorded across all §5.e sites (see below).

### Doc updates (§5.e)

- **`docs/CAPABILITY_MATRIX.md`** — new §7α block "M26
  audit-tooling refinement (planning-substrate integrity)."
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** — new
  Milestone 26 shipped-status section (after §Milestone 25).
- **`docs/roadmap/MILESTONE_26_RETROSPECTIVE.md`** — new
  retrospective with all 9 standard sections + M27
  candidate-list §9.
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`** —
  regenerated by the fixed script; represents the true
  post-M26 baseline.
- **`docs/roadmap/MILESTONE_26_PLANNING.md`** — refined
  additively at M26.1 open to reflect row-5 reclassification
  (5-endpoint blast radius, 119/154 corrected baseline,
  row-5 deferral to §3, §5.c case reshuffle).
- **`00-START-NEXT-SESSION.md`** — overwritten with
  SESSION_191 (M27.0 planning) priorities.
- **This handoff** at `docs/handoffs/SESSION_190_m26_close.md`.

## What changed in the repo (M26.1)

**Created:**

- `docs/handoffs/SESSION_190_m26_close.md` (this handoff).
- `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md`.
- `backend/dealer_ai/tests/test_audit_operational_surface.py`.

**Modified:**

- `00-START-NEXT-SESSION.md` (overwritten for SESSION_191).
- `docs/CAPABILITY_MATRIX.md` (new §7α block).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` (new §Milestone 26).
- `docs/roadmap/MILESTONE_26_PLANNING.md` (M26.1-open
  refinement notes — additive only per DOC_GOVERNANCE
  active-planning-memo posture).
- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  (regenerated; 5 coverage flips + numerator + cosmetic
  row-42 reorder).
- `backend/dealer_ai/scripts/audit_operational_surface.py`
  (new `_extract_balanced_template_literal` helper;
  refactored `_extract_url_literals`; post-match refinement
  branch in `extract_frontend_consumers`).

## Verification / baselines at close

- **Backend:** 4,805 pass, 1 skipped, 0 fail (was 4,793;
  +12 new tests all passing first run; ~160s wall-clock).
- **Frontend Vitest:** 226 pass across 32 files (unchanged;
  M26 does not touch `frontend/src/`).
- **Acceptance:** 14 journeys unchanged; §5.g exception
  path invoked (audit-tooling is not operator-facing).
- **`manage.py check`:** clean (pre-existing DecimalField
  deprecation warnings unchanged).
- **`makemigrations --check --dry-run`:** No changes
  detected.
- **`tsc --noEmit`** (frontend + acceptance): clean.
- **Redis:** PONG.
- **Audit artifact:** 154 total / 119 covered / 35
  backend-only / 312 service verbs. §5.d two-source
  agreement confirmed.

## Deferrals from M26 (all valid for later re-entry)

Full deferral list in
`MILESTONE_26_RETROSPECTIVE.md` §4. Summary:

- **Row 5 `vehicles/<int:vehicle_id>/` public-fetch-helper
  refinement** — NEW M27+ candidate surfaced at M26.1
  open. Extend `_HELPER_CALL_RE` to include public helpers
  (`getJSON` / `postJSON` / etc.), OR broaden
  `_PUBLIC_FETCH_RE` filters. Blast radius unknown
  pre-tracing.
- **Plain-string-literal false-positive investigation
  (rows 1–4).** Surfaced at SESSION_189 §3. M27+
  candidate.
- **A2 (JE creation UI).** Kept elevated as leading M27
  §5.a direct operator-coverage candidate per user
  constraint.
- **Test-hygiene remediation (Candidate H).** Kept
  separate from M26 per user constraint. M27+ candidate.
- **`recommend_disposition()` heuristic** — out of scope
  per §3.
- **Audit script rewrite / restructure** — M26 fixed the
  narrow defect; broader refactor deferred pending
  evidence.
- **Audit output format changes** — row shape, legend,
  summary format all unchanged.
- **All M25 §4 deferrals** — remain valid re-entry
  candidates.

## Non-goals achieved (SESSION_190 M26.1 close)

- ❌ No `frontend/src/` touched.
- ❌ No backend view / model / migration / serializer /
  permission class / urls.py touched.
- ❌ No acceptance journey added or extended (§5.g
  exception path).
- ❌ No endpoint disposition change beyond the 5
  mechanical reclassifications.
- ❌ No `recommend_disposition()` heuristic change.
- ❌ No plain-string-literal investigation (rows 1–4
  deferred per §3).
- ❌ No test-hygiene (H) combined into M26.
- ❌ No hand-edit of the audit artifact — regenerated
  only.
- ❌ Corrected 119/154 baseline recorded ONLY after
  §5.e two-source agreement.

## Streak accounting at M26 close

- **Zero-drift permission-class streak:** 26 consecutive
  milestones (M10 → M26). M26 added zero endpoints.
- **Planning-time as-recommended streak:** 5. M26.0 → 4
  (target locked as recommended after 3-tier framing +
  5 scope-discipline constraints added additively to
  §5); M26.1 → 5 (M26.1-open row-5 empirical
  refinement counted as as-recommended because it
  narrowed evidence without shifting §5.a target).
  Historical run of 89 across M10 → M23 preserved for
  the record.
- **DoD-exception-path invocations:** 1 (M26 is the
  first post-M21.0 §5.f Option B exception invocation).
  Future audit-tooling / test-hygiene / CI-
  infrastructure milestones can cite the precedent.

## Next session (SESSION_191 — M27.0 planning)

Per the overwritten `00-START-NEXT-SESSION.md`:

1. Verify M26 close baseline holds.
2. If M26 pushed, monitor first M26 CI run.
3. Regenerate audit; confirm 119/154 baseline holds.
4. Present M27 candidate list with recommendation +
   rationale.
5. Await user §5.a confirmation.
6. Draft §5.b–§5.h.
7. DoD compliance check on §3.
8. Expand M27 planning memo.
9. Ship M27.0 handoff.

## Anchors that win on conflict (M26 close)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 26
   (shipped section)
4. `docs/roadmap/MILESTONE_26_PLANNING.md` §5 (all locks
   + M26.1-open refinement notes)
5. `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md` §3
   (deviations) + §5 (durable lessons) + §9 (M27
   evidence)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M26 baseline 154 endpoints /
   **119 covered** / 35 backend-only)
7. `docs/CAPABILITY_MATRIX.md` §7α (M26 audit-tooling
   refinement)
8. `backend/dealer_ai/scripts/audit_operational_surface.py`
   (implementation source of truth; contains the
   `_extract_balanced_template_literal` shared substrate
   + post-match refinement branch)
9. `docs/handoffs/SESSION_189_m26_inc0_planning.md`
   (M26.0 planning + §5 locks + SESSION_189 §3
   empirical discovery)
10. Memory record
    `feedback_audit_correctness_as_supporting_infra.md`
    (durable principle governing M26 framing)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
