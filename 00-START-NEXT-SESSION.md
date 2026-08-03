---
state: active
date: 2026-08-03
last_session_shipped: SESSION_189
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
milestone_26_status: active
next_session: SESSION_190
next_milestone: 26
next_milestone_name: "Audit-Script Parser Refinement (Planning-Substrate Integrity)"
next_increment: 1
next_increment_name: "M26.1 — Parser fix + regression suite + audit regeneration + doc updates"
---

# Next session — SESSION_190 · Milestone 26 · Increment 1 (M26.1 — parser fix + regression suite + audit regeneration + doc updates)

> **Milestone 26 opened at SESSION_189 (M26.0) as a
> planning-substrate integrity milestone** — a reframe of the
> durable operational-coverage guiding question rather than a
> departure from it. All §5 locks captured in
> `docs/roadmap/MILESTONE_26_PLANNING.md`.
>
> **§3 empirical discovery at SESSION_189 §3:** the M25.3
> close-out handoff scoped the trailing-optional-querystring
> parser gap at 2 false-positive endpoints. Direct extractor
> tracing revealed the true blast radius is **6 endpoints** —
> a 3× understatement. Every M27+ target selection made from
> the current audit inherits that drift; M26 corrects it
> before the next major candidate ranking.
>
> **The six confirmed false positives (all shipped
> wrappers, all consumed by shipped UI, all currently
> `defer-candidate-O2` in the audit):**
>
> - Row 5 `vehicles/<int:vehicle_id>/` — `getVehicleDetail`
>   (api.ts:626).
> - Row 7 `admin/leads/` — `fetchAdminLeads` (api.ts:284).
> - Row 16 `admin/audit-events/` — `fetchAuditEvents`
>   (api.ts:341).
> - Row 29 `admin/vehicles/` — `listAdminVehicles`
>   (salesApi.ts:257).
> - Row 111 `admin/test-drives/list/` — `listTestDrives`
>   (salesApi.ts:204).
> - Row 121 `admin/be-backs/list/` — `listBeBacks`
>   (salesApi.ts:425).
>
> **True post-fix coverage baseline:** 120 / 154. Recorded
> only after §5.e two-source agreement (regenerated artifact
> + direct repository inspection).
>
> **Root cause identified at SESSION_189 §3:** the regex
> tokenizer at `audit_operational_surface.py:390`
> (`_HELPER_CALL_RE` template-literal branch
> `` `[^`]*(?:`|$) ``) terminates the outer template string
> at the first inner backtick — mis-tokenizing every wrapper
> that uses a nested template literal inside a `${...}`
> interpolation.
>
> **Session numbering fix:** the previous start-here doc
> named "SESSION_188" as this current session, but the M25.3
> folded-close-out handoff already occupies the 188 slot per
> DOC_GOVERNANCE.md incrementing convention. Corrected at
> M26.0 open — the SESSION_189 handoff shipped at
> `docs/handoffs/SESSION_189_m26_inc0_planning.md`. This
> doc's `next_session: SESSION_190` reflects the corrected
> numbering.
>
> **Zero-drift permission-class streak** stands at 25 (M10 →
> M25). M26 adds zero endpoints; intended posture at M26
> close extends to 26.
>
> **Planning-time as-recommended streak** stands at 4 after
> M26.0 (was 3 at M25 close; increments to 4 at M26.0 with
> AI recommendation confirmed after alternatives presented
> and five scope-discipline constraints added additively to
> §5 sections without shifting the target).
>
> **M26 is deliberately small.** 1 implementation increment
> (this session) + close-out fold per §5.h Option B unless
> §5.d verification surfaces discrepancies. Expected commit
> count: **2** if folded, 3–4 if split. Half the M25
> velocity envelope by design.
>
> **A2 (JE creation UI)** remains elevated as the leading
> direct operator-coverage candidate for M27 §5.a per user
> constraint. **H (test-hygiene remediation)** kept
> separate. **Rows 1–4 plain-string-literal audit
> investigation** (surfaced at SESSION_189 §3 but out of
> M26 scope) available as a separate M27+ candidate.

## First thing SESSION_190 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-SESSION_189 push (planning-only
  session; if not pushed, `HEAD` remains at `6a3efbb`).
- `git log --oneline -10` — top should be the M25.3
  close-out hash-backfill commit at `6a3efbb`.
- `python3 manage.py test dealer_ai` → **4,793 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **226 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

If the M21 audit artifact shows a working-tree
modification (SESSION_189 §3 regen cosmetic
wrapper-ordering diff on row 42 `admin/vendors/`),
either revert before opening M26.1 OR leave it and
absorb into the M26.1 regen diff — the recommended
posture is revert-before, since M26.1 will produce the
same cosmetic diff alongside the six coverage flips.

### 2. Re-verify the six false positives before implementing

Before touching the parser, re-run the SESSION_189 §3
verification to confirm the six false positives are
still present in the audit and still have shipped
wrappers. This guards against a scenario where an
intervening change (unlikely but possible) shifted the
audit output.

```bash
cd backend
python3 -c "
import sys
sys.path.insert(0, '.')
from dealer_ai.scripts.audit_operational_surface import extract_frontend_consumers
for f in ['api.ts', 'salesApi.ts']:
    source = open(f'../frontend/src/lib/{f}').read()
    for c in extract_frontend_consumers(source):
        if 'qs ?' in c.url_expr:
            print(f'{f}:{c.source_line} helper={c.helper} url={c.url_expr!r} normalized={c.normalized_pattern!r}')
"
```

Expected: five entries showing bogus `normalized_pattern`
values like `/admin/vehicles/${qs /` — confirming the
tokenizer defect. (The sixth false positive, row 5
`vehicles/<int:vehicle_id>/`, uses a slightly different
pattern and may not appear in this quick check — verify
separately.)

### 3. Implement §5.b parser fix

Per `MILESTONE_26_PLANNING.md` §5.b:

- **Preferred approach:** keep the fast-path
  `_HELPER_CALL_RE` regex, add a post-match refinement
  via a balanced-brace-aware companion function
  `_extract_balanced_template_literal(source, start_pos)
  -> tuple[str, int]`. When the fast-path regex captures
  a template-literal expression that contains an
  unterminated `${` (detected by the companion function),
  re-tokenize from `m.start()` and replace the captured
  expression.
- **Do NOT** change `normalize_frontend()` (already
  correct once tokenizer captures full expression).
- **Do NOT** change `_HELPER_TO_VERB` (M23.1 §5.d
  substrate).
- **Do NOT** change `recommend_disposition()` heuristic
  (out of scope per §3).
- **Do NOT** change `cross_reference()` candidate-
  pattern generation.

### 4. Add §5.c 12-test regression suite

Create `backend/dealer_ai/tests/test_audit_operational_
surface.py` with **6 positive** + **6 negative** test
methods per §5.c. Positive cases mirror the six
confirmed false positives; negative cases guard against
over-classification and preserve M22.1 §5.e + M23.1 §5.d
substrate. Expected new tests: 12; backend baseline
target 4,793 → ~4,805.

### 5. Regenerate the audit + §5.d Phase 1 verification

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Diff the regenerated artifact against pre-fix. Assert
exactly the following changes appear:

- Coverage summary numerator: **114 → 120**.
- Six rows flip `defer-candidate-O2` → `covered` with
  wrapper columns populated (rows 5, 7, 16, 29, 111,
  121 per SESSION_189 §3 evidence table).
- Cosmetic wrapper-ordering shifts (like the
  SESSION_189 §3 regen's row 42 re-order) are
  acceptable script-deterministic output.
- **No other row semantically changes.**

If any expectation fails, halt — treat as a §5.b
implementation gap, not a §5.d verification failure.

### 6. §5.d Phase 2 per-row manual verification

For each of the six reclassified rows, open the wrapper
source file at the reported `{filename}:{line}` and
verify:

1. Wrapper exists at the reported line.
2. Wrapper's HTTP helper matches the endpoint's
   declared methods per `extract_view_methods()`.
3. Wrapper is imported and called by at least one
   non-test `.tsx` or `.ts` component under
   `frontend/src/`.

If any row fails any check: halt, document, treat as
§5.b implementation gap.

### 7. Update docs (§5.e — corrected baseline recording)

Record 120 / 154 baseline **only after both** §5.d
Phase 1 and Phase 2 pass. Recording sites in order:

- `docs/CAPABILITY_MATRIX.md` — add §7α block.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — M26 entry.
- `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md` — NEW at
  M26 close (draft during this session per fold
  posture).
- `docs/handoffs/SESSION_190_m26_inc1_parser_fix.md` (or
  `SESSION_190_m26_close.md` if folded).
- `00-START-NEXT-SESSION.md` — overwrite with
  SESSION_191 priorities (A2 elevated as leading M27
  §5.a candidate; H remains separate; corrected 120 /
  154 baseline reflected in operational-state block).

### 8. DoD compliance check (§5.g exception path)

Per the M21.0 §5.f Option B DoD amendment: M26.1 does
not add or extend any Playwright journey. The
retrospective §journey-plan section must explicitly
document the exception path: "no journey change;
audit-tooling refinement; §5.g exception path invoked
per M21.0 §5.f." Acceptance baseline **14 journeys
unchanged**.

### 9. Close-out posture (§5.h Option B fold)

If steps 3–7 all pass cleanly, fold M26.2 close-out
into this session — retrospective drafted + all docs
updated + coordinated push in one session.

If steps 5 (Phase 1) or 6 (Phase 2) surface any
mismatch, promote close-out to a separate M26.2
session (SESSION_191).

### 10. Ship the M26.1 handoff + coordinated push

- Handoff: `docs/handoffs/SESSION_190_m26_inc1_parser_
  fix.md` (or `_m26_close.md` if folded).
- Coordinated push (M26.1 commit + hash backfill).
  Expected commit count 2 if folded, 3–4 if split.
- Push per M18 → M25 cadence — one coordinated push
  per milestone close.

## Non-goals for SESSION_190

- ❌ Do NOT touch any `frontend/src/` file. M26 is
  audit-script-only.
- ❌ Do NOT touch any backend view, model, migration,
  serializer, permission class, or `urls.py`. M26 is
  audit-script-only.
- ❌ Do NOT add, remove, or extend any Playwright
  journey (§5.g exception path).
- ❌ Do NOT change any endpoint disposition beyond the
  six mechanical reclassifications the parser fix
  produces.
- ❌ Do NOT investigate the plain-string-literal
  false-positive suspicion on rows 1–4 within M26.
- ❌ Do NOT combine test-hygiene (Candidate H) into
  M26.
- ❌ Do NOT hand-edit `M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Regenerate only.
- ❌ Do NOT record the corrected 120 / 154 baseline
  without both §5.e sources agreeing.
- ❌ Do NOT push per-increment. Coordinated push at
  M26 close per §5.h.
- ❌ Do NOT let M26 broaden into a general "audit
  quality" milestone.
- ❌ Do NOT skip §5.d Phase 2 per-row manual
  verification.

## Baseline expected at close

- Backend: **≥4,805 pass** (4,793 + ~12 new parser
  regression tests), 1 skipped, 0 fail.
- Frontend Vitest: **226 pass** unchanged.
- Acceptance: **14 journeys** unchanged.
- Audit: **120 / 154 covered** (was 114 / 154).
- `manage.py check` clean.
- Migrations: no changes detected.
- `tsc --noEmit` clean (frontend + acceptance).

## NEXT TASK

Start SESSION_190 with (a) starting-state verification,
(b) re-verify the six false positives are still
present pre-fix, (c) implement §5.b parser fix
(post-match refinement approach), (d) add §5.c 12-test
regression suite, (e) regenerate audit + §5.d Phase 1
diff verification, (f) §5.d Phase 2 per-row manual
verification, (g) update docs per §5.e (only after
two-source agreement), (h) DoD §5.g exception-path
documentation, (i) fold close-out per §5.h if all
steps clean, (j) M26.1 handoff + coordinated push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M26 entry added at close)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_25_RETROSPECTIVE.md`
   §8 + §9
6. `docs/roadmap/MILESTONE_26_PLANNING.md`
   (M26 governing contract + all §5 locks +
   SESSION_189 §3 empirical discovery record)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (pre-fix 114 / 154 baseline; source of truth
   until M26.1 regenerates it)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped
   surface) + §7α (M26 audit-tooling refinement,
   added at close)
9. `backend/dealer_ai/scripts/audit_operational_
   surface.py` (implementation source of truth
   for the parser defect)
10. `docs/handoffs/SESSION_189_m26_inc0_planning.md`
    (M26.0 planning + §5 locks + SESSION_189 §3
    empirical discovery)
11. `docs/handoffs/SESSION_188_m25_inc3_close.md`
    (M25.3 close; records the under-scoped
    2-endpoint estimate SESSION_189 §3 corrected
    to 6)
12. Memory record
    `feedback_audit_correctness_as_supporting_
    infra.md` (durable principle governing M26
    framing)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_189 — Milestone 26 · Increment 0 shipped)

- **Backend (local):** Django on `:8001`.
  Migrations `0001`–`0049`. Test baseline: **4,793
  pass**, 1 skipped, 0 fail (unchanged from M25
  close).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`.
  `tsc --noEmit` + `vite build` clean.
  **Vitest baseline: 226 pass** across 32 test
  files (unchanged).
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49
  + TS 5.6 operational; **14 journeys** passing
  end-to-end on clean DB. Full dry-run baseline:
  **20 passed (~30s)** (6 setup + 14 journeys)
  (unchanged).
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. First real
  M25 CI run green (2m21s, verified at SESSION_189
  §2). Five most recent `main` runs all green.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler.
  10 scheduled task families registered.
- **Milestones shipped:** M1 → **M25**. M26 opened
  (M26.0 planning shipped SESSION_189).
- **DRF admin surface:** **114** endpoints
  (unchanged post-M25.2 `admin/vehicles/`).
- **Frontend operator routes:** 20 (unchanged).
- **Public endpoints:** +1 M6.5 showroom
  (unchanged).
- **Service surface:** all M1–M25 packages
  unchanged. Zero M26 service verbs.
- **Frontend surfaces:** unchanged. M26 does not
  touch `frontend/src/`.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift
  streak **twenty-five consecutive milestones**
  (M10 → M25). M26 posture at close extends to 26.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 26 status:** ACTIVE. M26.0 shipped
  (planning only, no code). M26.1 opens
  SESSION_190.
- **Audit tooling status:** current 114 / 154
  baseline under-reports true coverage by 6
  endpoints (SESSION_189 §3 empirical discovery).
  Corrected 120 / 154 baseline recorded at M26.1
  close only after §5.e two-source agreement.
- **§9 evidence for M27:** A2 elevated (leading
  candidate per user constraint at M26.0);
  H (test-hygiene, unchanged from M25);
  plain-string-literal audit investigation (NEW
  candidate surfaced at SESSION_189 §3, deferred
  from M26 scope); plus gated T/U/L/M, deferred
  pending evidence D/C, deferred stable G.
- **Planning-time streak:** **4** (at M26.0
  open; increments only if M26.1 lock matches
  M26.0 recommendation).
- **DoD amendment (M21.0 §5.f Option B):** M26.1
  invokes exception path — planning infrastructure,
  not customer-facing behavior. Acceptance 14
  journeys unchanged.
- **M25 audit coverage at close:** 114 / 154
  endpoints covered per script (**120 / 154 in
  reality** per SESSION_189 §3 empirical
  discovery; corrected artifact ships at M26.1
  close).
- **Durable lessons carried into M26:** (a) one
  operational workflow beats two partially
  overlapping ones (M25.0 §5.d origin); (b)
  planning-open verification must cover the
  persistence path, not just the UI path (M25.0
  §5.b + M25.2 §5.e origin); (c) additive-forever
  JSONField beats CharField (M25.0 §5.b origin);
  (d) record empirical-discovery refinements
  honestly (M25.0 + M25.2 origin); (e) modal-
  attached collapsible + success badge > toast
  (M25.2 origin); (f) dependency-injectable
  helpers over network mocks in unit tests (M25.2
  origin); (g) audit correctness is supporting
  infrastructure — every accuracy gain compounds
  across future scope decisions (M25.3 →
  SESSION_189 §3 origin; primary M26 framing).
