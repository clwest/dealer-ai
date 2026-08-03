---
state: active
date: 2026-08-03
last_session_shipped: SESSION_175
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
milestone_23_status: in-progress
next_session: SESSION_176
next_milestone: 23
next_milestone_name: "BHPH Origination + Payment Intake"
next_increment: 1
next_increment_name: "M23.1 — Audit-tool false-positive fix + artifact refresh"
---

# Next session — SESSION_176 · Milestone 23 · Increment 1 (M23.1 — audit-tool false-positive fix + artifact refresh)

> **Milestone 23 · Increment 0 —
> BHPH Origination + Payment Intake
> planning refinement — SHIPPED at
> SESSION_175.** Full memo expansion
> from M22.4 skeleton + eight §5
> load-bearing decisions resolved
> as-recommended at open per the
> operational-coverage primary lens.
> §5.a chose O2 (BHPH note
> origination + payment intake sub-
> scope) — highest per-item
> operational coverage delta at
> smallest scope; completes the
> BHPH lifecycle bookends from
> M12 backend + M12.7 read UI +
> M20.4 Playwright + M21.2 write-
> side UI for collections.
>
> **Empirical M23.0 verification
> surfaced NEW audit false-positive
> class** distinct from M22.1's
> variable-first URL assembly:
> **HTTP-verb-agnostic URL-prefix
> matching**. Audit row 123
> (`admin-bhph-note-create`) claims
> coverage via a GET wrapper on a
> different-verb + different-path
> URL that shares only the prefix.
> Ships M23.1 targeted fix under
> ~2-hour budget guard.
>
> **Planning-time as-recommended
> streak extends 88 → 89 across
> fourteen consecutive milestones**
> (M10 → M23). **Zero-drift
> permission-class streak target
> at M23.4 close: 22 → 23**.
>
> **SESSION_176 opens M23.1 —
> audit-tool false-positive fix.**
> Supporting work per §5.d Option
> A (targeted regex + parser
> enhancement to discriminate HTTP
> verb). Not the milestone
> centerpiece; the two anchor UIs
> ship at M23.2 (note origination)
> and M23.3 (payment intake).
> Budget guard: if fix exceeds ~2
> hours, ship partial + defer
> residual to a future audit-
> tooling milestone.
>
> **DoD compliance satisfied by
> construction** for M23 — every
> anchor implementation increment
> (M23.2 + M23.3) adds a Playwright
> operational journey.

## First thing SESSION_176 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -6` — top
  should be the M23.0 close
  commit; `origin/main` still at
  the M22 durable-lessons head
  (M23 has not pushed).
- `python3 manage.py test dealer_ai`
  → **4,766 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **180 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `cd acceptance && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

### 2. Inspect the audit script's HTTP-verb matching

Open
`backend/dealer_ai/scripts/audit_operational_surface.py`
and locate `cross_reference()` +
`_HELPER_CALL_RE`. Identify where
wrapper URLs get matched against
endpoint URLs. The current code
matches by URL pattern alone — no
HTTP verb comparison.

Cross-check against the known
misclassification: row 123 in the
audit shows `admin-bhph-note-create`
(POST) as `covered` via
`bhphApi.ts:109 getBhphNote` (GET
wrapper for `admin/bhph-notes/<pk>/`).
These are different verbs + different
URL shapes (prefix match only).

### 3. Ship the targeted regex + parser fix

Per §5.d Option A — narrow scope.
Extract HTTP verb from wrapper's
helper-call name:
- `authGetJSON` → GET
- `authPostJSON` → POST
- `authPatchJSON` → PATCH
- `authPutJSON` → PUT
- `authDelete` → DELETE
- `authPostForm` → POST

Extract the endpoint's declared
HTTP verb from the view callable
(via `@api_view([...])` decorator
inspection or view function shape).
Store both verbs on the respective
data model
(`FrontendConsumer.helper_verb` +
`BackendEndpoint.methods`); modify
`cross_reference()` to only claim
coverage when the wrapper's verb
matches the endpoint's declared
verbs.

Do NOT attempt a full AST rewrite.
Do NOT expand scope to handle
other classes of false-positive
unless they surface as side-
effects of the same fix.

**Budget guard.** If the targeted
fix exceeds ~2 hours (from opening
the script to green-passing test),
stop. Document the remaining
false-positive patterns as future
audit-tooling milestone scope in
§0.a M23.1 amendment, land a
partial fix (or no fix), and
proceed to M23.2 with the audit
still partially unreliable.
Preserves scope discipline over
completionism.

### 4. Optional: add audit-script correctness test

If the audit script has an existing
test module, extend it with a
regression test for the HTTP-verb-
match case. If not, adding a new
test is discretionary — the
regenerated artifact itself is the
functional test in the sense that
row 123 either reclassifies or it
doesn't.

### 5. Regenerate the audit artifact

```bash
cd backend
python3 -m dealer_ai.scripts.audit_operational_surface
```

Verify the M21 audit artifact
updates with:
- `admin-bhph-note-create` →
  `defer-candidate-O2` (was
  `covered` — reclassifies because
  `getBhphNote` is a GET wrapper,
  not POST). Same disposition as
  row 126 (`admin-bhph-payment-
  create`).
- Coverage count: 110 → likely
  **~105-109** (small drop as
  false-positives get corrected;
  other domains may have similar
  patterns).
- Backend-only count: 43 →
  likely **~44-48**.

If `admin-bhph-note-create` does
NOT reclassify, the fix is
incomplete — either extend the
regex or document the residual
limitation in §0.a M23.1
amendment.

If additional endpoints reclassify
(from any domain), catalog them
in §0.a with brief context. These
are audit-noise reductions that
don't change M23 scope but
strengthen future OSC candidates.

### 6. Update M23 planning memo §0.a with M23.1 outcome

Add an `**SESSION_176 M23.1 close
(YYYY-MM-DD):**` entry to the §0.a
change log capturing: audit fix
shipped (yes/partial/skipped),
misclassifications corrected, any
additional false-positives
surfaced, budget-guard triggered
(yes/no), notes on the fix
approach.

### 7. Ship the M23.1 handoff

- `docs/handoffs/SESSION_176_m23_inc1_audit_fix.md`.
- Overwrite `00-START-NEXT-SESSION.md`
  with M23.2 priority (first
  anchor UI — note origination).
- **Do NOT push** — M23 uses
  coordinated close-out push per
  M18.6 / M19.6 / M20.5 / M21.5
  / M22.4 cadence at M23.4.

## Non-goals for SESSION_176

- ❌ Do NOT ship the note
  origination or payment intake
  UI (that's M23.2 + M23.3
  scope).
- ❌ Do NOT attempt a full AST-
  based audit rewrite (explicit
  non-goal per §5.d Option A).
- ❌ Do NOT modify shipped
  accounting UI or BHPH UI
  (M23 shipping surface is
  audit script + M23.2/M23.3
  anchors only).
- ❌ Do NOT let audit correction
  bleed past the ~2-hour budget
  guard.
- ❌ Do NOT expand fix scope to
  audit patterns unrelated to
  the HTTP-verb-agnostic class
  unless they surface as side-
  effects of the same fix.
- ❌ Do NOT push M23.1 commits
  individually.

## Baseline expected at close

- Backend baseline: 4,766 →
  **~4,767** (possible audit-
  script correctness test).
- Frontend Vitest: 180 (unchanged
  — no frontend changes).
- Acceptance suite: 7 journeys
  (unchanged — M23.2 introduces
  the first new M23 journey).
- Migrations `0001`–`0048`
  unchanged.
- Tenancy carriers 52 unchanged.
- Permission classes 7 unchanged
  (zero-drift streak intact).
- Audit artifact updated with
  ≥1 reclassification (row 123);
  possibly more if other domains
  share the pattern.

## NEXT TASK

Start SESSION_176 with (a)
starting-state verification, (b)
inspect the audit script's
`cross_reference()` +
`_HELPER_CALL_RE` for HTTP-verb
matching, (c) ship the targeted
regex + parser fix under the
~2-hour budget guard, (d)
optional audit-script correctness
test, (e) regenerate the audit
artifact and verify at least row
123 reclassifies, (f) update M23
planning memo §0.a with M23.1
outcome, (g) ship the M23.1
handoff and refresh
`00-START-NEXT-SESSION.md` for
M23.2. Do NOT push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section landed
   at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (active memo — governing
   contract for M23.1 audit
   correction posture)
6. `docs/handoffs/SESSION_175_m23_inc0_planning.md`
   (M23.0 close — empirical
   discovery record + §5
   decisions)
7. `docs/handoffs/SESSION_172_m22_inc1_audit_correction.md`
   (M22.1 close — audit
   correction precedent for
   M23.1 shape)
8. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact being
   regenerated — known
   unreliable for BHPH row 123
   until M23.1 fix lands)
9. `docs/CAPABILITY_MATRIX.md` §7w
   (M22 shipped surface)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_175 — Milestone 23.0 planning shipped)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,766 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 180 pass**.
- **Frontend (prod):** NONE.
- **Acceptance workspace
  (local):** Playwright 1.49 +
  TS 5.6 operational; **seven
  journeys** passing end-to-end
  on clean DB. Full dry-run
  baseline: **13 passed
  (~18s)**. No M23 journeys
  ship until M23.2 open.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`.
  First real M22 CI runs
  verified green: `30830291129`
  (M22 shipped push, 2m8s) +
  `30831196864` (M22 durable-
  lessons carry-forward push,
  2m3s). M23 has not pushed
  yet.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  **M22**. M23 in-progress
  (M23.0 planning shipped;
  M23.1 next at SESSION_176).
- **DRF admin surface:** **113**
  endpoints.
- **Frontend operator routes:**
  **20**.
- **Public endpoints:** +1 M6.5
  showroom.
- **Service surface:** all
  M1–M22 packages unchanged.
  M23 adds zero service verbs.
- **Frontend surfaces:** all
  M1–M22 components unchanged.
  M23 will add
  `RecordBhphNoteForm` +
  `RecordBhphPaymentForm`
  (M23.2 + M23.3).
- **Tenancy carriers:** **52**.
- **Permission classes:** **7
  actual** — zero-drift streak
  **twenty-two consecutive
  milestones** (M10 → M22).
  Target at M23.4 close: 23.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged).
- **Deterministic rules:**
  unchanged.
- **Milestone 23 status:** IN-
  PROGRESS. M23.0 planning
  shipped at SESSION_175 with
  eight §5 load-bearing
  decisions resolved as-
  recommended at open. Full
  active memo landed at
  `docs/roadmap/MILESTONE_23_PLANNING.md`.
- **Audit tooling:** operator-
  invoked from `backend/`
  (`python3 -m
  dealer_ai.scripts.audit_operational_surface`).
  Authoritative for accounting
  post-M22.1 fix. Known
  false-positive for BHPH row
  123 (HTTP-verb-agnostic URL-
  prefix matching) — M23.1
  targeted fix lands at
  SESSION_176.
- **Planning-time streak:** **89
  as-recommended M5.1 → M23.0**
  across fourteen consecutive
  milestones (M10 → M23).
- **DoD amendment (M21.0 §5.f
  Option B):** M23 satisfies
  by construction — M23.2 +
  M23.3 each add a Playwright
  operational journey.
- **M23 governing contract
  (inherited from M21
  Candidate O UI-creation
  shape):** (1) maps to
  shipped backend + missing
  frontend; (2) closes a
  missing operator-facing UI;
  (3) adds or extends a
  Playwright operational
  journey; (4) not generic UX
  polish.
- **M23 anchor implementations:**
  M23.1 audit tool fix
  (supporting), M23.2 note
  origination UI + journey
  (first anchor), M23.3
  payment intake UI + journey
  (second anchor), M23.4
  close-out.
- **M23 audit fix scope
  (M23.1):** targeted regex +
  parser enhancement to
  discriminate HTTP verb
  between wrapper calls and
  endpoint patterns.
  Reclassifies at minimum row
  123 (`admin-bhph-note-
  create`) from `covered` to
  `defer-candidate-O2`. Budget
  guard: ~2 hours.
