---
state: active
date: 2026-08-04
last_session_shipped: SESSION_197
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
milestone_29_status: active
next_session: SESSION_198
next_milestone: 29
next_milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
next_increment: 1
next_increment_name: "M29.1 — Backend substrate relaxation (serializer allow_null + service three-state balance logic)"
---

# Next session — SESSION_198 · Milestone 29 · Increment 1 (M29.1 — backend substrate relaxation)

> **Milestone 29 — Variable-Amount Journal Templates — OPEN
> (planning-only at M29.0, shipped at SESSION_197).**
> Two-increment structure locked at M29.0 per §5.e of
> `docs/roadmap/MILESTONE_29_PLANNING.md`. M29.1 is backend-
> only; M29.2 is the operator-facing frontend + acceptance
> journey.
>
> **M29.0 shipped:** planning memo authored at
> `docs/roadmap/MILESTONE_29_PLANNING.md` with all §5 locks;
> handoff at `docs/handoffs/SESSION_197_m29_inc0_planning.md`.
> M29.0 is **local-only** at open of SESSION_198 (coordinated
> push at M29 close per M28 precedent).
>
> **Planning-time as-recommended streak reached 8** (was 7 at
> M28.2 close; +1 at M29.0 with target locked as recommended
> after five-alternative comparison + one implementation-
> boundary verification). Historical run of 89 across M10 →
> M23 preserved for the record.
>
> **Zero-drift permission-class streak preserved at 28**
> (M10 → M28); M29.0 planning-only. M29.1 backend-only + no
> new endpoints — streak projected to advance to 29 at M29
> close.

## First thing SESSION_198 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main`
  by **2 commits** (M29.0 planning memo + handoff hash
  backfill will follow this session's ship + local commit,
  bringing it to 4 by SESSION_198 open). Expect local HEAD
  at `60af5cf` + 2 (if M29.0 hash-backfill commit not yet
  made) or + 3 (if it was).
- `git log --oneline -10` — top should be the M29.0 hash-
  backfill commit (or the M29.0 memo + handoff commit if
  not yet backfilled).
- `python3 manage.py test dealer_ai` → **4,855 pass, 1
  skipped, 0 fail** (unchanged from M28.2 close — M29.0
  is planning only).
- `cd frontend && npm test` → **270 pass** (unchanged).
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. No CI to monitor

M29.0 was not pushed; coordinated push at M29 close. Skip
the CI verification step.

### 3. Audit artifact unchanged

Optional at M29.1 open (endpoint surface unchanged from
M28.2 close). If regenerated, expected identity:
**156 total / 122 covered / 34 backend-only / 315 service
verbs**.

### 4. Implement §5.b D1 — serializer + service relaxation

Per `docs/roadmap/MILESTONE_29_PLANNING.md` §5.b D1:

- **`backend/dealer_ai/views_accounting.py`
  `JournalEntryTemplateLineSerializer.amount`:** add
  `allow_null=True`. No other serializer changes.
- **`backend/dealer_ai/services/accounting/template.py`
  `_validate_template_lines`:** replace the "amount required"
  branch (currently lines 140–144) with three-state logic:
  1. `amount is None` → skip balance contribution; do not
     raise.
  2. `amount is not None and amount > 0` → contribute to
     debit-side or credit-side sum per `side`.
  3. `amount is not None and amount <= 0` → raise
     `InvalidJournalEntryTemplateLineError` (existing
     behavior preserved).
- **Balance check:** run against populated (non-null) lines
  only. Accept three legitimate template shapes: fully
  fixed (M28.1 behavior preserved); fully variable (both
  sums zero, trivially equal); mixed (populated portion
  must balance).
- **Update the model docstring at `models.py:7568`** if
  wording needs refinement post-M29.1 (optional; the
  existing docstring already predicts this milestone).

### 5. Implement §5.b D6 — backend test surface additions

Per `docs/roadmap/MILESTONE_29_PLANNING.md` §5.b D6:

- **New file** `backend/dealer_ai/tests/
  test_m29_variable_amount_template_service.py` (~15 tests).
  Cover the eight named cases in the memo plus edge cases
  (max lines, mixed with cross-tenant reject, tenant-scoped
  read).
- **Extension** of
  `backend/dealer_ai/tests/test_m28_journal_entry_template_endpoint.py`
  (~4 tests). Cover the four named cases in the memo.
- **Extension** of
  `backend/dealer_ai/tests/test_m28_journal_entry_template_model.py`
  (~2 tests). Cover model-level null-amount coercion +
  clean().
- **No instantiate-flow backend tests** — reuses M13.1
  posting-service coverage.
- Expected backend baseline: **4,855 → ~4,876 (+~21)**.

### 6. Verify M28.1 regression at close

- Run backend suite. Verify existing M28.1 test files pass
  unchanged (regression guard on `_validate_template_lines`
  relaxation): every fully-populated-lines template in the
  M28.1 endpoint tests continues to succeed.
- Run `manage.py check` + `makemigrations --check --dry-run`
  clean — no migration expected (model schema unchanged
  from `0050`).

### 7. DoD exception path (fourth precedent)

Per `docs/roadmap/MILESTONE_29_PLANNING.md` §5.f:

- M29.1 is a **backend-only substrate relaxation with no
  operator-facing behavior change**. Playwright coverage
  remains intact via existing
  `accounting_je_template.spec.ts` + `accounting_je_create.spec.ts`
  regression.
- Fourth precedent (M26 + M27.1 + M28.1 + M29.1).
- SESSION_198 handoff §3 must explicitly document why no
  journey change is required at this sub-increment.

### 8. Two-source agreement gate

Per M26.1 durable lesson: at increment close, verify no
endpoint drift by comparing the M21 audit artifact against
the git diff. Expected: **zero endpoint diff** at M29.1
(no new views, no permission classes evolved).

### 9. Ship the M29.1 handoff

- `docs/handoffs/SESSION_198_m29_inc1_backend.md`.
- **Do NOT push** — M29.1 is a mid-milestone increment;
  coordinated push at M29 close per M28 precedent.
- Commit locally with a message like: `"Milestone 29 ·
  Increment 1 — Variable-amount template substrate
  relaxation (SESSION_198)"`.

## Non-goals for SESSION_198

- ❌ Do NOT ship any frontend code — M29.2 territory.
- ❌ Do NOT extend or create any Playwright journeys — M29.2
  territory.
- ❌ Do NOT modify the `JournalEntryTemplate` /
  `JournalEntryTemplateLine` model schema — the M28.1
  reserved-nullable-amount column is the entire schema
  substrate for M29.
- ❌ Do NOT create any new endpoints — M29 preserves the
  zero-drift permission-class streak.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M28 shipped surface (other than the
  narrow `_validate_template_lines` branch relaxation
  covered by D1).
- ❌ Do NOT skip the DoD exception-path documentation.
- ❌ Do NOT skip the two-source agreement gate.
- ❌ Do NOT skip the M28.1 regression guard.
- ❌ Do NOT push M29.0 or M29.1 — coordinated push at M29
  close.

## Baseline expected at close (M29.1)

- Backend suite: **4,855 → ~4,876 (+~21)** — new
  `test_m29_variable_amount_template_service.py` (~15)
  + extension of `test_m28_journal_entry_template_endpoint.py`
  (~4) + extension of `test_m28_journal_entry_template_model.py`
  (~2).
- Frontend Vitest: **270 pass** (unchanged — M29.2
  territory).
- Acceptance: **19 journeys** (unchanged — M29.2 territory).
- Audit coverage: **122 / 156** (unchanged — no new
  endpoints).
- DRF admin surface: **116 endpoints** (unchanged).
- Permission classes: **7 actual** (unchanged — zero-drift
  streak preserved).
- Migration count: **0050** (unchanged — no new migration).

## NEXT TASK

Start SESSION_198 with (a) starting-state verification;
(b) implement §5.b D1 (serializer allow_null + service
three-state relaxation); (c) implement §5.b D6 (new test
file + two extensions); (d) run backend suite and verify
+~21 tests with M28.1 regression guard intact;
(e) two-source agreement gate; (f) DoD exception path
documentation in §3 of the handoff; (g) ship
`docs/handoffs/SESSION_198_m29_inc1_backend.md`;
(h) local commit only, no push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_29_PLANNING.md`
   (M29.0 active memo — all §5 locks)
6. `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md` §5
   (durable lessons) + §9 (M29 candidate lineage)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (baseline **122 / 156** — expected identity at M29.1
   close)
8. `docs/CAPABILITY_MATRIX.md` §7γ (M28 shipped surface)
9. `docs/handoffs/SESSION_197_m29_inc0_planning.md`
   (M29.0 shipped)
10. Memory records:
    - `feedback_duplicate_small_stable_logic.md` (M28.0
      origin — governs the substrate-relaxation refactor
      scoping at M29.1)
    - `feedback_verify_fk_discoverability_before_lock.md`
      (M27.0 origin — verified at M29.0 §4.2)
    - `feedback_prefer_updating_authoritative_docs.md`
    - `feedback_terminal_output_discipline.md`

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_197 — Milestone 29 OPEN, M29.0 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,855 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest baseline: 270 pass** across
  36 test files.
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 +
  TS 5.6 operational; **19 journeys** total.
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Last verified green
  on the M28.2 hash-backfill push (2m36s at SESSION_197
  open).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → **M28**. M29 open (M29.0
  shipped; M29.1 + M29.2 pending).
- **DRF admin surface:** **116** endpoints (unchanged
  since M28.1).
- **Frontend operator routes:** 20 (unchanged).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** all M1–M28 packages unchanged.
  M29.1 will narrowly relax `_validate_template_lines` in
  `services/accounting/template.py` per §5.b D1.
- **Frontend surfaces:** unchanged at M29.0. M29.2 will
  add the "Variable amount" checkbox to
  `NewJournalEntryTemplateDialog`, the additive
  `lockedLines` prop + `overridden` internal state on
  `NewJournalEntryDialog`, and the Override toggle UI.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  **28 consecutive milestones** (M10 → M28). Projected to
  advance to 29 at M29 close.
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 29 status:** OPEN. M29.0 shipped
  (SESSION_197 planning memo + handoff); M29.1 pending
  (SESSION_198 backend substrate); M29.2 pending
  (SESSION_199 frontend + Playwright).
- **Audit tooling status:** unchanged from M26.1. Coverage
  **122 / 156** (matches M28.2 close exactly).
- **§9 evidence carried into M29.1:** all seven binding
  constraints from the SESSION_197 confirmation message
  recorded in `SESSION_197_m29_inc0_planning.md` §6 and
  memo §5.b D1–D8.
- **Planning-time streak: 8** (at M29.0 close; historical
  run of 89 across M10 → M23 preserved).
- **DoD amendment (M21.0 §5.f Option B):** M29.1 will
  invoke the exception path as fourth precedent (M26 +
  M27.1 + M28.1 + M29.1) — infrastructure-only sub-
  increment; §3 of the handoff must document why no
  journey change is required. M29.2 satisfies DoD
  directly.
- **M29.0 audit coverage:** **156 endpoints, 122 covered /
  34 backend-only** (unchanged from M28.2 close). No new
  endpoint at M29 (see §5.b D1).
- **Durable lessons carried into M29:** all (a)–(s) from
  the M28 close-state list continue to apply. M29.0 adds
  no new durable lessons at this planning increment;
  M29.1 + M29.2 may surface new ones at close.
