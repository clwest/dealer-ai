---
state: active
date: 2026-08-04
last_session_shipped: SESSION_203
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
milestone_31_status: active
next_session: SESSION_204
next_milestone: 31
next_milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
next_increment: 1
next_increment_name: "M31.1 — Backend substrate (Restore verb + endpoint + list ?include_inactive exposure)"
---

# Next session — SESSION_204 · Milestone 31 · Increment 1 (M31.1 — backend substrate)

> **Milestone 31 opened at SESSION_203 M31.0 planning.**
> Target locked as **NEW Restore / "Show inactive"
> templates UI (lifecycle-completion)** under the primary
> operational-coverage lens, evaluated as lifecycle-
> completion per explicit user direction. All §5.b–§5.h
> locks landed (D1–D10, 10-item risk register, 8
> verifications including L1 lifecycle-integrity
> precheck, two-increment split, DoD compliance,
> rollback, non-goals).
>
> **Planning-time as-recommended streak advanced 9 →
> 10** at M31.0 close (target selected as recommended
> after five-alternative comparison + user-directed
> lifecycle-integrity precheck; historical run of 89
> across M10 → M23 preserved).
>
> **Substrate-compound-value continuation to fifth link
> projected at M31 close** (M27.1 → M28.1 → M29 → M30 →
> **M31 template lifecycle closure**). M31 will spend
> zero new migrations by composing on M28.1's `is_active`
> field + M30.1's `include_inactive` service kwarg.
>
> **First M30 CI run verified green** at SESSION_203
> open (workflow `30930670900` on `f658c06` — 26 passed /
> 0 failed / 2m50s). No §0.a M31.0 amendments landed.
>
> **SESSION_204 opens M31.1 — backend substrate
> implementation** per `MILESTONE_31_PLANNING.md` §5.b
> D1–D3 + §5.e M31.1 spec. Pure backend increment; no
> frontend changes. DoD exception path invocation #6
> (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1).
> Coordinated M31 close push deferred to explicit user
> confirmation after M31.2 close.

## First thing SESSION_204 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` matches
  `origin/main` post-M30 push (`f658c06`); planning-only
  M31.0 commit from SESSION_203 present locally, unpushed.
- `git log --oneline -10` — top should be the SESSION_203
  M31.0 planning commit (+ optional hash-backfill
  follow-up).
- `python3 manage.py test dealer_ai` → **4,904 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **300 pass** across 36
  files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive
  reset per SESSION_200 §0.a durable lesson (v).

### 2. Read the M31 governing contract before writing code

Load-bearing docs to read before M31.1 implementation:

- `docs/roadmap/MILESTONE_31_PLANNING.md` §5.b D1
  (Restore is a dedicated verb, not a PATCH side-
  effect), D2 (idempotent, tenant-scoped, preservation
  contract), D3 (fail-closed `?include_inactive`
  parsing).
- `docs/roadmap/MILESTONE_31_PLANNING.md` §5.e M31.1
  spec (service verb, endpoint, URL, tests).
- `docs/handoffs/SESSION_203_m31_inc0_planning.md` §5
  + §7 for the confirmed §5.b review points.

Do **not** re-open scope. §5.a target and all §5.b
decisions are locked; any narrow amendment goes through
the §0.a change-log path in the planning memo.

### 3. Ship M31.1 backend substrate

Per `MILESTONE_31_PLANNING.md` §5.e M31.1:

- **Service layer** (`services/accounting/template.py`):
  - New `restore_journal_entry_template(*, pk,
    dealership) -> Optional[JournalEntryTemplate]` verb
    per D2 contract. Atomic; idempotent on already-
    active input; `update_fields=["is_active",
    "updated_at"]` on state-change branch.
  - Module docstring updated to list the new verb
    alongside `update_` and `delete_`.
- **Endpoint layer** (`views_accounting.py`):
  - New `admin_journal_entry_template_restore(request,
    pk)` view (POST). Reuses `_M131_PERMS`. Error
    mapping: 404 missing/cross-tenant, 200 restored,
    200 idempotent already-active.
  - Extend `admin_journal_entry_template_list` to
    parse `?include_inactive=true` per D3 fail-closed
    parsing. Only literal `"true"` (case-insensitive)
    enables inactive rows; every other value resolves
    to active-only default.
- **URL** (`urls.py`): new pattern
  `admin/accounting/journal-entry-templates/<int:pk>/restore/`
  → `admin-journal-entry-template-restore`.
- **Zero migration.** Reuses `is_active` field.

### 4. Ship tests per D2 + D3 coverage

Planned ~24–26 tests:

- **NEW `test_m31_journal_entry_template_restore_service.py`** (~12):
  happy-path Restore; idempotent repeat-Restore returns
  row without state change AND `updated_at` unchanged;
  returns None on missing pk; returns None on cross-
  tenant; preserves `name`; preserves `description`;
  preserves lines including amounts and ordering;
  preserves `created_at`; advances `updated_at` only on
  state-change branch; accepts already-active pk
  without error; returns projected row shape.
- **EXTEND `test_m28_journal_entry_template_endpoint.py`**
  with `TemplateRestoreEndpointTests` (~10): POST 200
  restore; POST 200 idempotent already-active; POST 404
  missing; POST 404 cross-tenant; admin allowed;
  advisor allowed; unauth denied; **PATCH cannot
  mutate `is_active`** — regression re-assertion from
  M30.2; list default returns active-only; list with
  `?include_inactive=true` returns both.
- **EXTEND `test_m28_journal_entry_template_endpoint.py`**
  list tests with `?include_inactive` fail-closed
  parsing (~4): `true`, `TRUE`, `True` all enable
  inactive rows; `1`, `yes`, empty string, malformed
  value, missing param all resolve to active-only.

### 5. Verify M31.1 close baselines

- Backend suite: **4,904 → ~4,930 pass**, 1 skipped, 0
  fail.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- Frontend Vitest unchanged (300 pass) — M31.1 makes
  no frontend changes.
- `cd frontend && npx tsc --noEmit` unchanged (clean).
- `cd acceptance && npx tsc --noEmit` unchanged (clean).

Optional at close: regenerate audit artifact and
confirm expected transitional state (157 → 158
endpoints; 122 covered / 35 backend-only during M31.1
transitional state before M31.2 re-covers the new
endpoint). Two-source agreement gate at M31.2 close per
convention.

### 6. Document DoD exception path invocation #6

M31.1 invokes the DoD exception path per M21.0 §5.f
Option B (M26 lineage) — backend substrate with no
operator-facing behavior change on its own. Document
in §3 of the M31.1 handoff:

- M31.1 is infrastructure-only; M31.2 satisfies DoD
  directly via new `restore-inactive` describe block.
- Sixth invocation of the exception path (M26 + M27.1
  + M28.1 + M29.1 + M30.1 + M31.1). Pattern firmly
  established.

### 7. Ship the M31.1 handoff

- `docs/handoffs/SESSION_204_m31_inc1_backend.md`.
- **Do NOT push** — coordinated push at M31 close.

## Non-goals for SESSION_204

- ❌ Do NOT ship any frontend or Playwright code — pure
  backend substrate increment.
- ❌ Do NOT touch `AccountingJournalEntriesPage.tsx`,
  `JournalEntryTemplateDialog.tsx`, or
  `accountingApi.ts`.
- ❌ Do NOT ship the D10 M30.2 copy update — bundled
  with M31.2 UI increment.
- ❌ Do NOT re-open §5.a or §5.b decisions; narrow
  amendments go through §0.a change-log path.
- ❌ Do NOT push. Coordinated push at M31 close after
  explicit user confirmation.
- ❌ Do NOT force-push or amend earlier commits.
- ❌ Do NOT modify M1–M30 shipped surface.
- ❌ Do NOT introduce any new permission class —
  Restore endpoint reuses `_M131_PERMS` verbatim.
- ❌ Do NOT add server-side coupling between
  JournalEntry and JournalEntryTemplate — the
  decoupling is load-bearing on Restore/Deactivate
  safety per M28.0 §5.b + M30.0 §4.7 + M31.0 §4.1
  L1 finding. Stale-tab JE creation from previously-
  hydrated template values is an accepted race
  outcome per user direction.
- ❌ Do NOT add a migration. Zero-migration property
  is load-bearing on rollback cheapness per §5.g.
- ❌ Do NOT allow PATCH to mutate `is_active`.
  Activation stays behind dedicated Deactivate /
  Restore verbs per M30.2 lesson (w).

## Baseline expected at close

- Backend: 4,904 → ~4,930 pass, 1 skipped, 0 fail.
- Frontend: unchanged (300 pass across 36 files).
- Acceptance: unchanged (21 journeys).
- Migrations: `0001`–`0050` unchanged (zero migration).
- DRF admin surface: 117 → 118 (+1 for Restore).
- Service verbs: 317 → 318 (+1 for
  `restore_journal_entry_template`).
- Permission classes: 7 unchanged (Restore reuses
  `_M131_PERMS`; zero-drift streak advances 31 → 32).

## NEXT TASK

Start SESSION_204 with (a) starting-state verification;
(b) read the M31 governing contract; (c) implement
Restore service verb + endpoint + list
`?include_inactive` exposure per §5.b D1–D3 and §5.e
M31.1 spec; (d) ship ~24–26 tests per D2 + D3
coverage; (e) verify close baselines (backend ~4,930
pass; check + makemigrations clean; frontend/acceptance
unchanged); (f) document DoD exception path invocation
#6 in the M31.1 handoff §3; (g) ship the M31.1 handoff
at `docs/handoffs/SESSION_204_m31_inc1_backend.md`; (h)
DO NOT push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M30 shipped surface
   in CAPABILITY_MATRIX §7δ + §7ε per convention
   adopted at M27+; M31 §7ζ added at M31 close)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_31_PLANNING.md`** —
   M31 governing contract; §5.b D1–D3 + §5.e M31.1
   spec govern SESSION_204 implementation
6. `docs/roadmap/MILESTONE_30_RETROSPECTIVE.md` §9
   (M31 candidate list origin; standing question
   on substrate-compound-value fifth link resolved
   in favor of Restore under primary operational-
   coverage lens)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (post-M30 baseline — 157 endpoints / **123
   covered** / 34 backend-only / 317 service verbs;
   M31 projected delta +1 endpoint / +1 covered /
   +1 verb at M31.2 close)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α
   (M26) + §7β (M27) + §7γ (M28) + §7δ (M29) +
   §7ε (M30 shipped surface); §7ζ added at M31
   close
9. **`docs/handoffs/SESSION_203_m31_inc0_planning.md`**
   (M31.0 planning shipped — §5 locks summary + L1
   lifecycle-integrity precheck + confirmed §5.b
   review points)
10. `docs/handoffs/SESSION_202_m30_inc2_frontend.md`
    (M30.2 shipped + M30 close-out; source of
    shipped Restore-promise copy that D10 fulfills)
11. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs D8 co-located inline-
    dialog choice at M31.2)
12. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0 §6.6)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_203 — Milestone 31 ACTIVE at M31.0)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,904 pass**, 1 skipped, 0 fail. **Projected at
  M31.1 close: ~4,930 pass.**
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  + `vite build` clean. Vitest baseline: **300 pass**
  across 36 test files. **Unchanged at M31.1 close;
  projected ~322 at M31.2 close.**
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 +
  TS 5.6 operational; **21 journeys** total.
  **Unchanged at M31.1 close; projected 22 at M31.2
  close.**
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `f658c06` (M30.2 hash-backfill
  commit): **26 passed / 0 failed / 2m50s** (workflow
  `30930670900`, verified green at SESSION_203 open).
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → **M30**. **M31 active
  at M31.0 planning** (SESSION_203); M31.1 target
  SESSION_204; M31.2 target SESSION_205.
- **DRF admin surface:** **117** endpoints (M28.1 116
  → +1 at M30.1). Projected at M31.1 close: **118**
  (+1 for Restore endpoint).
- **Frontend operator routes:** 20 (unchanged;
  Show-inactive toggle + row-state rendering attach
  to the existing JE list page).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** 317 verbs at M30 close. Projected
  at M31.1 close: **318** (+1 for
  `restore_journal_entry_template`).
- **Frontend surfaces:** unchanged at M31.1;
  M31.2 will add Show-inactive toggle,
  `TemplateRestoreConfirmDialog`, inactive-row
  rendering, disabled Edit/Instantiate guards, D10
  copy update on `TemplateDeleteConfirmDialog`.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift
  streak **thirty-one consecutive milestones** (M10 →
  M30). **Projected 32 at M31 close** (M31.1 Restore
  endpoint reuses `_M131_PERMS`).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 31 status:** ACTIVE at M31.0 (planning
  landed; two implementation increments pending —
  M31.1 backend + M31.2 frontend + Playwright).
- **Audit tooling status:** unchanged from M26.1.
  Coverage **123 / 157** at M30 close. Projected at
  M31.2 close: **124 / 158** (+1 endpoint, +1
  covered; backend-only unchanged after M31.2
  re-covers the M31.1 endpoint via the frontend
  wrapper).
- **§9 evidence carried into M31:** NEW Restore /
  "Show inactive" UI toggle **selected as M31 target
  under primary operational-coverage lens** (M28 §3
  deferral resolved at M31); NEW C F&I chargeback
  substrate (unchanged — gated pending pilot
  evidence); NEW O2 + NEW O3 (unchanged); H test-
  hygiene (unchanged); gated T/U/L/M unchanged;
  deferred D + deferred-stable G unchanged; M30 §3 +
  M29 §3 + M28 §3 + M27 §3 + M25 §4 deferrals
  unchanged. New at M31 §3 (see planning memo):
  template mutation history / diff viewer; auto-
  refresh of stale-tab template list (accepted per
  R1); persistent Show-inactive toggle state; bulk
  lifecycle actions.
- **Planning-time streak: 10** (at M31.0 close;
  advanced from 9 at M30.2 close per §5.a
  as-recommended lock; historical run of 89 across
  M10 → M23 preserved).
- **DoD amendment (M21.0 §5.f Option B):** every
  future customer-facing milestone must add or update
  at least one Playwright operational journey, or
  explicitly document in §3 why no journey change is
  required. M26 was first invocation; M27.1 second;
  M28.1 third; M29.1 fourth; M30.1 fifth. **M31.1
  will be sixth** (backend substrate). M31.2 will
  satisfy DoD directly via new `restore-inactive`
  describe block.
- **M30 audit coverage at close:** 157 endpoints,
  **123 covered / 34 backend-only** (baseline
  unchanged at SESSION_203; carries forward to
  SESSION_204). Two-source agreement confirmed at
  M30 close.
- **Durable lessons carried into M31+:** all (a)–(x)
  from the M30 close-state list continue to apply.
  M31 exercises (t) additive-prop pattern in a
  reinforcement posture (no new mode branches on the
  renamed dialog; co-located inline dialog for
  Restore confirmation per (M28.0)
  `feedback_duplicate_small_stable_logic.md`); (v)
  acceptance-selector-sweep (row testid mirrors the
  M30.2 `tmpl-*-trigger-<pk>` pattern for
  consistency); (w) `is_active` mutation surface
  asymmetry is **hardened** at M31 (adds Restore as
  the second dedicated verb alongside Delete/
  Deactivate; PATCH cannot mutate is_active — locked
  again at endpoint test layer); (x) delete-UI copy
  vocabulary asymmetry **re-applied** at M31.2
  (row "Restore" → confirmation "Reactivate template?").
