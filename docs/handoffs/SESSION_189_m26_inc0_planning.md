---
title: "SESSION_189 handoff — Milestone 26 · Increment 0 (M26.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 189
milestone: 26
milestone_status: active
milestone_name: "Audit-Script Parser Refinement (Planning-Substrate Integrity)"
increment: 0
increment_status: shipped
commit: 8bb588f
---

# SESSION_189 — Milestone 26 · Increment 0 (M26.0 — planning refinement + target selection)

> **Note on session numbering:** the start-here doc that
> opened this session named it "SESSION_188" (following its
> `next_session: SESSION_188` frontmatter). However, the
> M25.3 folded-close-out handoff at
> `docs/handoffs/SESSION_188_m25_inc3_close.md` already
> occupies the 188 slot per the DOC_GOVERNANCE.md
> incrementing convention ("one handoff per session number,
> incrementing"). The start-here doc's session number was
> written at M25.3 close without accounting for the fold
> consuming that slot. **Corrected at M26.0 open — this
> session is SESSION_189.** The M26 planning memo, this
> handoff, and the overwritten `00-START-NEXT-SESSION.md`
> all use SESSION_189 → SESSION_190 → SESSION_191 numbering.

## What shipped

M26.0 opened Milestone 26 as a **planning-substrate
integrity** milestone — a reframe of the durable
operational-coverage guiding question rather than a
departure from it. All §5 decisions locked in this
session; no code changes; no push. Full active memo
authored at `docs/roadmap/MILESTONE_26_PLANNING.md`.

**Session artifacts:**

- **Starting-state verification (§1):** git clean, `HEAD
  == origin/main @ 6a3efbb`, Redis PONG, Django check
  clean, `makemigrations --check` clean, frontend `tsc
  --noEmit` clean, acceptance `tsc --noEmit` clean.
  Backend suite **4,793 pass, 1 skipped, 0 fail** (164s).
  Frontend Vitest **226 pass** (32 files). All matches
  M25-close baseline.
- **First M25 CI run verified (§2):** acceptance
  workflow on the M25.3 push completed **green in
  2m21s**. M25 is CI-verified shipped. Five most recent
  acceptance runs on `main` all green (M22 → M25).
- **Audit regeneration (§3):** `python3 -m
  dealer_ai.scripts.audit_operational_surface` invoked.
  Output: **154 total / 114 covered / 40 backend-only /
  312 service verbs**. Only diff on regen was a
  cosmetic wrapper-ordering shift on row 42
  (`admin/vendors/`); no semantic change.
- **§3 empirical discovery — M25.3 blast radius
  under-scoped by 3×.** M25.3 close-out handoff scoped
  the trailing-optional-querystring parser gap at 2
  false-positive endpoints (M11.6 `admin/test-drives/
  list/` + M25.2 `admin/vehicles/`). Direct invocation
  of `extract_frontend_consumers()` against `api.ts` +
  `salesApi.ts` at SESSION_189 revealed the true blast
  radius is **6 endpoints**. The root cause is a
  regex-tokenizer gap at
  `audit_operational_surface.py:390` (`_HELPER_CALL_RE`
  template-literal branch `` `[^`]*(?:`|$) ``) which
  terminates the outer template string at the first
  inner backtick — mis-tokenizing every wrapper that
  uses a nested template literal inside a `${...}`
  interpolation.
- **Confirmed false positives (all shipped wrappers, all
  consumed by shipped UI, all currently `defer-candidate-
  O2` in the audit):**

  | # | Endpoint | Wrapper | Ships since |
  |---|---|---|---|
  | 5 | `vehicles/<int:vehicle_id>/` | `getVehicleDetail` (api.ts:626) | pre-M11 |
  | 7 | `admin/leads/` | `fetchAdminLeads` (api.ts:284) | M11 |
  | 16 | `admin/audit-events/` | `fetchAuditEvents` (api.ts:341) | M11-era |
  | 29 | `admin/vehicles/` | `listAdminVehicles` (salesApi.ts:257) | M25.2 |
  | 111 | `admin/test-drives/list/` | `listTestDrives` (salesApi.ts:204) | M11.6 |
  | 121 | `admin/be-backs/list/` | `listBeBacks` (salesApi.ts:425) | M11 |

- **True coverage baseline (post-fix expected):** 120 /
  154, not 116 / 154 as M25.3 estimated.

**§4 candidate list presented with three-tier framing:**

- **Direct operator-coverage gains:** A2 (JE creation
  UI — row 140 genuinely uncovered).
- **Test-hygiene / audit-tooling improvements:** NEW
  audit-script parser refinement (M25.3 discovery,
  blast radius revised to 6); H (test-hygiene
  remediation — 3 shared-DB non-idempotent journeys).
- **Gated (lacks external trigger):** T (real tester
  feedback); U (hosted-demo substrate); L (first-live-
  pilot staging); M (multi-operator support — breaks
  zero-drift streak).
- **Deferred (no current evidence):** D (LLM router /
  cost caps); C (F&I chargeback substrate).
- **Deferred but stable:** G (dashboard testid
  hardening).
- **Deferred at M25 §4 (valid for later re-entry):**
  secondary "+ Record test drive" launch point;
  clickable "Referred by" nav; named-platform adapters;
  attribution analytics; vehicle picker advanced
  filters.

**Independent AI recommendation:** audit-script parser
refinement, framed as planning-substrate integrity —
primarily because the SESSION_189 §3 discovery revealed
the M25.3 estimate under-scoped the blast radius by 3×,
and every M27+ target selection depends on the audit
being accurate.

**User confirmation:** locked audit-script parser
refinement as M26 §5.a with the following five scope-
discipline constraints (all incorporated additively
into the §5 sections):

1. Scope strictly to the nested-template-literal +
   optional-querystring parsing defect (§5.b).
2. Regression tests for all six confirmed false
   positives plus representative negative cases so the
   fix does not over-classify unconsumed endpoints
   (§5.c).
3. Regenerate the full audit after implementation +
   manually verify each reclassified row against
   wrapper + actual UI consumer (§5.d).
4. No disposition changes unrelated to the parser
   defect without separate evidence (§3 deferrals).
5. Record 120/154 as corrected baseline only after
   regenerated artifact and repository inspection
   agree (§5.e).

Additional user-locked constraints:

- Use M21.0 §5.f exception path explicitly — no
  Playwright journey required (§5.g).
- A2 (JE creation UI) elevated as leading direct
  operator-coverage candidate for M27 unless corrected
  audit reveals a stronger genuine gap (§3 + start-
  here overwrite).
- H (test-hygiene) kept separate from M26 (§3).

**§5 locks (all captured in
`MILESTONE_26_PLANNING.md`):**

- **§5.a** — LOCKED as audit-script parser refinement,
  planning-substrate integrity framing.
- **§5.b** — LOCKED as narrow parser fix inside
  `extract_frontend_consumers` (audit script line
  607), bounded to nested-template-literal
  tokenization + optional-querystring normalization.
  Preferred approach: keep fast-path regex, add
  post-match refinement via balanced-brace-aware
  companion function
  (`_extract_balanced_template_literal`).
  `normalize_frontend()` untouched; `_HELPER_TO_VERB`
  untouched; `recommend_disposition()` untouched.
- **§5.c** — LOCKED as dedicated
  `backend/dealer_ai/tests/test_audit_operational_
  surface.py` with 6 positive + 6 negative test
  methods. Positive cases mirror the six confirmed
  false positives. Negative cases include:
  legitimate query-string wrapper without template
  nesting; wrapper against non-existent endpoint;
  fast-path wrapper with single `${...}` (post-match
  refinement must not fire); identifier-passed URL
  (M22.1 §5.e lookback preservation); empty template;
  malformed / unterminated template. Verb-filter
  co-verification per M23.1 §5.d substrate
  preservation. Backend baseline projected 4,793 →
  ~4,805.
- **§5.d** — LOCKED as two-phase protocol (regenerate
  + per-row manual verification of wrapper existence,
  verb match, and component-import). Any mismatch
  halts close-out and is treated as a §5.b
  implementation gap, not a §5.d verification
  failure.
- **§5.e** — LOCKED as two-source agreement
  requirement. Corrected 120/154 baseline recorded
  only after regenerated artifact and direct
  repository inspection agree. Recording sites at
  close: `CAPABILITY_MATRIX.md` §7α, retrospective
  §1, handoff baseline block, start-here operational
  state.
- **§5.f** — LOCKED as 1 implementation increment
  (M26.1) + close-out fold per §5.h. Half the M25
  velocity envelope by design.
- **§5.g** — LOCKED with M21.0 §5.f exception path
  explicitly invoked. Acceptance 14 journeys
  unchanged.
- **§5.h** — LOCKED as evidence-sized Option B fold
  (M18 → M25 precedent). Expected commit count 2 if
  folded, 3–4 if split.

**§3 deferrals recorded (all valid for later
re-entry with evidence):**

- Plain-string-literal false-positive investigation
  on rows 1–4 (`chat/start/`, `chat/message/`,
  `chat/session/<uuid:session_id>/`, `leads/`) —
  root cause is not the M26 defect; requires
  separate SESSION_189 §3-style tracing.
- Test-hygiene remediation (Candidate H) — kept
  separate per user constraint.
- A2 (JE creation UI) — elevated as leading M27
  §5.a candidate.
- Endpoint disposition changes unrelated to the
  six known false positives.
- Audit-script rewrite / restructure beyond the
  narrow parser fix.
- Audit output format changes.
- CAPABILITY_MATRIX historical §7 rewrites.

## What changed in the repo

- **Created:** `docs/roadmap/MILESTONE_26_PLANNING.md`
  — full active planning memo (all §5 locks).
- **Created:** `docs/handoffs/SESSION_189_m26_inc0_
  planning.md` — this handoff.
- **Modified:** `00-START-NEXT-SESSION.md` — overwritten
  with SESSION_190 (M26.1 implementation) priorities.
- **Modified (transient, planning-audit only):**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` — the
  §3 regen produced a cosmetic wrapper-ordering shift
  on row 42 (`admin/vendors/`). This is deterministic
  script output; the working-tree change may be
  reverted before M26.0 push OR left in and absorbed
  into the M26.1 audit-regen diff (recommended: revert
  before push, since M26.0 is planning-only and the
  reordering will re-appear at M26.1 close alongside
  the six coverage flips).

## Verification / baselines at close

- **Backend:** 4,793 pass, 1 skipped, 0 fail (unchanged
  from M25 close).
- **Frontend Vitest:** 226 pass across 32 files
  (unchanged).
- **Acceptance:** 14 journeys unchanged. Full clean-DB
  dry-run baseline (~30s) unchanged.
- **Django check:** clean.
- **Migrations:** no changes detected.
- **Frontend + acceptance `tsc --noEmit`:** clean.
- **Redis:** PONG.
- **CI:** M25.3 push run green (2m21s); five most
  recent `main` acceptance runs all green.

## Deferrals / follow-on items

All deferrals recorded in
`MILESTONE_26_PLANNING.md` §3. Summary:

- **Rows 1–4 plain-string-literal audit-parser
  investigation** — evidence surfaced at SESSION_189
  §3 but explicitly out of M26 scope per user
  constraint; separate M27+ candidate.
- **A2** — elevated as leading M27 §5.a candidate.
- **H** — kept separate; M27+ candidate.
- **T / U / L / M / D / C / G** — unchanged from
  M25 candidate pool.
- **All M25 §4 deferrals** — valid for later
  re-entry with operator evidence per the durable
  principles.

## Non-goals achieved (SESSION_189)

- ❌ No code shipped (planning-only session).
- ❌ No push (M26.0 is planning; coordinated push at
  M26 close).
- ❌ No implementation increment opened.
- ❌ No M1–M25 shipped surface modified.
- ❌ No acceptance journey added / extended.
- ❌ No endpoint disposition changes.
- ❌ No plain-string-literal investigation
  (deferred per §3).

## Streak accounting at M26.0 close

- **Zero-drift permission-class streak:** 25
  consecutive milestones (M10 → M25). M26 adds
  zero endpoints; intended posture at M26 close
  extends to 26.
- **Planning-time as-recommended streak:** 3 → **4**.
  M26.0 target locked as recommended after
  alternatives (A2, NEW audit-script refinement, H)
  presented with explicit three-tier framing (direct
  operator-coverage / test-hygiene + audit-tooling /
  gated / deferred). The user confirmed the AI's
  recommendation and added five scope-discipline
  constraints — all incorporated additively into the
  §5 sections; the target itself did not shift.
  Counts as as-recommended.

## Next session (SESSION_190 — M26.1 implementation)

Per `MILESTONE_26_PLANNING.md` §7 and the overwritten
`00-START-NEXT-SESSION.md`:

1. Verify M25 close baseline holds.
2. Implement §5.b parser fix (preferred: post-match
   refinement with balanced-brace-aware companion).
3. Add §5.c 12-test regression suite.
4. Regenerate audit.
5. Verify §5.d Phase 1 diff matches expectation
   exactly (six flips, coverage 114 → 120, no other
   semantic changes).
6. Perform §5.d Phase 2 per-row manual verification.
7. Update `CAPABILITY_MATRIX.md` §7α, roadmap M26
   entry, retrospective, start-here.
8. Compose M26.1 handoff, coordinated push if fold
   posture holds.

## Anchors that win on conflict (M26.0 close)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_26_PLANNING.md` §5 (all
   locks)
4. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (pre-fix 114 / 154 baseline)
5. `backend/dealer_ai/scripts/audit_operational_
   surface.py` (source of truth for the parser
   defect)
6. Memory record
   `feedback_audit_correctness_as_supporting_
   infra.md`
7. `docs/handoffs/SESSION_188_m25_inc3_close.md`
   (M25.3 close; records the under-scoped estimate
   this session corrected)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
