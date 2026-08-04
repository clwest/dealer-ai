---
title: "SESSION_204 handoff — Milestone 31 · Increment 1 (M31.1 — backend substrate: Restore verb + POST endpoint + list ?include_inactive fail-closed parsing + tests)"
status: historical
type: handoff
date: 2026-08-04
session: 204
milestone: 31
milestone_status: active
milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
increment: 1
increment_status: shipped
commit: pending
commit_notes: "M31.1 commits stay local per M31 coordinated-push cadence; hash backfill via a follow-up commit. NOT pushed. Coordinated push at M31 close after explicit user confirmation."
---

# SESSION_204 — Milestone 31 · Increment 1 (M31.1 — backend substrate)

## What shipped

M31.1 delivers the load-bearing backend substrate that the M31.2
operator surface will attach to. A new endpoint
`admin/accounting/journal-entry-templates/<int:pk>/restore/`
supports POST (reactivate a soft-hidden template by setting
`is_active = True`; idempotent — repeat POST on an already-active
row returns 200 without state change and without advancing
`updated_at`). One new service verb
(`restore_journal_entry_template`) plus a one-line extension of
the existing list endpoint that parses `?include_inactive=true`
with fail-closed semantics (only the literal string `true`,
case-insensitive, opts in; every other value resolves to active-
only default so inactive templates never mix into the default
active list). Zero schema migration (Restore reuses the M28.1
`is_active` field verbatim; endpoint reuses the M30.1
`include_inactive` kwarg on `get_journal_entry_template`). Zero
operator-facing behavior change — the M28.2 templates section,
M29.2 Instantiate flow, and M30.2 Edit / Delete flow continue to
work unchanged.

**Session artifacts:**

- **Starting-state verification (§1):** git clean; local `HEAD ==
  5d12184` (SESSION_203 M31.0 handoff hash-backfill commit, 2
  commits ahead of `origin/main` per planning-only cadence).
  Backend suite **4,904 pass / 1 skip / 0 fail** (168.9s) —
  matches M30.2 close baseline. Frontend Vitest **300 pass / 36
  files** unchanged. Django `check` + `makemigrations --check`
  clean. Frontend + acceptance `tsc --noEmit` clean. Redis PONG.
  Acceptance DB reset proactively per SESSION_200 §0.a durable
  lesson (v).
- **Audit-artifact baseline hold at open (§2):** unchanged from
  M30.2 close at 157 / 123 / 34 / 317 before implementation.
  After implementation: **158 / 123 / 35 / 318** (delta matches
  M31.0 §5.e M31.1 projected transitional state exactly — new
  endpoint row at audit index 152, disposition
  `defer-candidate-O2` transitional; M31.2 flips it to `covered`
  when frontend wrappers land).
- **Implementation per §5.b D1–D3 + §5.e M31.1 spec (§3):**
  - `backend/dealer_ai/services/accounting/template.py`:
    - Added `restore_journal_entry_template` verb — atomic
      reactivate; idempotent (already-active input returns row
      without a save so `updated_at` doesn't advance on the no-op
      path); tenant-scoped via `get_journal_entry_template
      (include_inactive=True)`; explicit
      `update_fields=["is_active", "updated_at"]` on the state-
      change branch per D2 preservation contract; returns
      `Optional[JournalEntryTemplate]` (None → 404 at endpoint
      layer).
    - Updated module docstring: five verbs → **six verbs**;
      M31.1 posture note documents the lesson (w) mutation-
      surface asymmetry hardening (now backed by two dedicated
      verbs — Delete/Deactivate + Restore/Reactivate — plus the
      PATCH-cannot-mutate-is_active enforcement).
  - `backend/dealer_ai/services/accounting/__init__.py`:
    exported `restore_journal_entry_template`; alphabetically
    inserted into `__all__`.
  - `backend/dealer_ai/views_accounting.py`:
    - Added `admin_journal_entry_template_restore(request, pk)`
      view — POST-only; reuses `_M131_PERMS`; error mapping
      returns 200 with projected row on success + idempotent
      already-active, 404 on missing / cross-tenant.
    - Extended `admin_journal_entry_template_list_or_create` GET
      branch with `include_inactive = request.GET.get(
      "include_inactive", "").lower() == "true"` and passes
      through to the service. Fail-closed by construction — the
      `.lower() == "true"` chain accepts only `true`, `TRUE`,
      `True`, and treats every other value including missing,
      empty, `1`, `yes`, and malformed as False.
    - Imported `restore_journal_entry_template` alphabetically.
  - `backend/dealer_ai/urls.py`:
    - Registered new pattern
      `admin/accounting/journal-entry-templates/<int:pk>/restore/`
      → `admin-journal-entry-template-restore` url_name.
      Sibling of the M30.1 detail endpoint. Comment cross-
      references M31 planning §5.b D1–D2 and the audit endpoint
      #68 shape precedent (`admin/vehicle-photos/<uuid>/restore/`).
  - **Zero schema migration** — Restore reuses M28.1 `is_active`
    field; no new fields, indexes, or constraints added.
- **Test surface added per §5.e M31.1 (§4):**
  - NEW `test_m31_journal_entry_template_restore_service.py` —
    **13 tests** covering happy path (flip is_active + projected
    row), idempotency (repeat on active + updated_at unchanged +
    never-deactivated row), missing / cross-tenant (returns
    None), preservation contract (name, description, lines byte-
    identical, created_at), updated_at advances-only-on-state-
    change end-to-end, and post-Restore visibility via default
    `get_journal_entry_template`.
  - EXTENDED `test_m28_journal_entry_template_endpoint.py`:
    - NEW `TemplateRestoreEndpointTests` class (**7 tests**):
      POST 200 with projected row + re-appears in default list;
      idempotent already-active POST 200 twice; missing pk 404;
      cross-tenant 404 + foreign row untouched; advisor denied
      403 + underlying row untouched; unauthenticated 401/403;
      **PATCH still cannot mutate is_active after M31.1** —
      regression re-assertion of the M30.2 durable lesson (w)
      layered enforcement so a future change can't re-add
      `is_active` to the update serializer as a shortcut.
    - NEW `TemplateListIncludeInactiveEndpointTests` class
      (**9 tests**) for D3 fail-closed parsing: `true`,
      `TRUE`, and `True` all enable inactive rows; `false`,
      `1`, `yes`, empty string, malformed value, and missing
      param all resolve to active-only default.
  - **Total M31.1 test delta: +29** (13 service + 16 endpoint /
    parsing). Actual **4,904 → 4,933** matches the M31.0 §5.e
    projected ~4,930 within the M30.1-lesson tolerance for
    auth/tenancy/regression coverage.
- **Focused test run (§5) before full-suite:** 97 tests across
  the four template test files (M28 service + M28 endpoint +
  M30 edit/delete + M31 restore) all pass in 4.2s isolated —
  fast-catch of regression before committing the full 165s
  suite run.
- **Post-implementation close baselines (§6):**
  - Backend suite: **4,933 pass / 1 skip / 0 fail** (165.0s).
  - Django `check`: system check identified no issues (0
    silenced).
  - `makemigrations --check --dry-run`: No changes detected.
  - Frontend Vitest: unchanged (300 pass / 36 files) — M31.1
    made zero frontend changes.
  - Frontend `tsc --noEmit`: clean.
  - Acceptance `tsc --noEmit`: clean.
  - Redis: PONG.
  - Audit artifact: 158 / 123 / 35 / 318 (post-implementation
    regen; +1 endpoint / +1 backend-only transitional / +1
    service verb; covered unchanged during M31.1 transitional
    state — M31.2 wraps to 158 / 124 / 34).
- **DoD exception path — sixth invocation (§7):** M31.1 is
  backend substrate with no operator-facing behavior change on
  its own; DoD satisfied by the M31.2 UI + Playwright follow-up.
  Pattern firmly established at six invocations (M26 + M27.1 +
  M28.1 + M29.1 + M30.1 + M31.1).

## 1. Verification results at open

| Check | Expected | Actual |
|---|---|---|
| `git status` | clean | ✅ clean |
| `HEAD` | 5d12184 (SESSION_203 hash-backfill) | ✅ 5d12184 (2 commits ahead of origin/main) |
| Backend suite | 4,904 pass, 1 skip | ✅ 4,904 pass, 1 skip (168.9s) |
| Frontend Vitest | 300 pass, 36 files | ✅ 300 pass, 36 files (5.7s) |
| Django `check` | clean | ✅ clean |
| `makemigrations --check` | No changes | ✅ No changes |
| Frontend `tsc --noEmit` | clean | ✅ clean |
| Acceptance `tsc --noEmit` | clean | ✅ clean |
| `redis-cli ping` | PONG | ✅ PONG |
| Acceptance DB reset | done | ✅ removed proactively |

## 2. Audit-artifact regeneration (post-implementation)

Ran `python3 -m dealer_ai.scripts.audit_operational_surface`
post-implementation.

| Metric | Pre-M31.1 (M30.2 close) | Post-M31.1 | Delta | Match §5.e projection? |
|---|---|---|---|---|
| Backend endpoints | 157 | 158 | +1 | ✅ |
| Covered | 123 | 123 | unchanged | ✅ (M31.2 ticks to 124) |
| Backend-only | 34 | 35 | +1 | ✅ (M31.2 shifts back to 34) |
| Service verbs | 317 | 318 | +1 | ✅ |

New endpoint at audit index 152: `admin/accounting/journal-
entry-templates/<int:pk>/restore/` — currently `defer-
candidate-O2` transitional disposition (backend-only). Will re-
classify to `covered` at M31.2 when the frontend wrapper +
UI land.

## 3. §5.b D1–D3 implementation summary

### D1 — Restore is a dedicated verb, never a PATCH side-effect

New URL pattern `admin/accounting/journal-entry-templates/
<int:pk>/restore/` → `admin_journal_entry_template_restore`
view. POST-only; no request body needed. Reuses `_M131_PERMS`.

The PATCH detail endpoint (M30.1) continues to omit `is_active`
from its serializer — the `JournalEntryTemplateUpdateRequest
Serializer` field set is unchanged at M31.1. Layered enforcement
of the (w) asymmetry is now:

1. **Serializer layer:** update serializer doesn't define
   `is_active`; DRF silently drops it in `is_valid`.
2. **Service layer:** update service passes explicit
   `update_fields=["name", "description", "updated_at"]` on
   save.
3. **Endpoint tests:** two regression assertions —
   `test_patch_silently_ignores_is_active_in_body` (M30.2
   original) + `test_patch_still_cannot_mutate_is_active_after_
   m31` (M31.1 addition), both asserting the same behavior
   from different scaffolding paths so a future change to
   either layer would be caught.

### D2 — Idempotent, tenant-scoped, preservation contract

Service verb `restore_journal_entry_template(*, pk,
dealership)` mirrors `delete_journal_entry_template` structure
exactly:

- Fetches via `get_journal_entry_template(include_inactive=
  True)` so soft-hidden rows are reachable.
- Returns `None` for missing pk or cross-tenant (endpoint layer
  maps to 404).
- Guard clause on `if not template.is_active` — only saves when
  actually transitioning False → True. Already-active input
  returns row without side effects.
- `update_fields=["is_active", "updated_at"]` on the state-
  change branch — Django auto-now on `updated_at` triggers
  only via `save()`.

Preservation contract asserted by the following M31.1 service
tests:

- `test_restore_preserves_name` — name byte-identical after
  Restore.
- `test_restore_preserves_description` — description byte-
  identical.
- `test_restore_preserves_lines_byte_identical` — all line
  fields (account_id, side, amount, memo, ordering) byte-
  identical using a sorted-by-ordering snapshot comparison.
- `test_restore_preserves_created_at` — created_at unchanged.
- `test_restore_advances_updated_at_only_on_state_change` —
  end-to-end assertion that state-change branch DOES advance
  `updated_at` and idempotent branch does NOT.
- `test_repeat_restore_does_not_advance_updated_at` — narrow
  regression test on the no-save path.
- `test_restore_on_never_deactivated_row_is_idempotent` — a
  pk that has always been active doesn't trigger a save
  (verified via `updated_at` unchanged after Restore).

### D3 — Fail-closed `?include_inactive=true` parsing

One-line addition to the list endpoint GET branch:

```python
include_inactive = (
    request.GET.get("include_inactive", "").lower() == "true"
)
```

By construction, only the literal string `"true"` (case-
insensitive) resolves to True; every other value — including
missing, empty, `1`, `yes`, `false`, `TRUE!`, `maybe` —
resolves to False. Nine `TemplateListIncludeInactiveEndpoint
Tests` methods cover the accepted spellings (`true`, `TRUE`,
`True`) + the rejected spellings (`false`, `1`, `yes`, empty,
malformed, missing).

The default posture remains active-only — byte-identical to the
M30.2 shipped list-endpoint behavior. Inactive templates
**never** mix into the default active list.

## 4. Lesson (w) mutation-surface asymmetry — hardening

M30.2 durable lesson (w) established that `is_active` mutation
must stay behind dedicated verbs — never through general PATCH.
M31.1 hardens this by:

1. Adding a second dedicated activation verb (Restore) alongside
   the existing Deactivate (Delete), so the lifecycle is now
   fully behind explicit verbs from both directions.
2. Re-asserting the PATCH-cannot-mutate constraint via
   `test_patch_still_cannot_mutate_is_active_after_m31` — a new
   regression test that pre-emptively guards against any future
   refactor that would add `is_active` to the update serializer
   as a shortcut for Restore.
3. Documenting the layered enforcement in the module docstring
   (three enforcement layers: serializer + service `update_
   fields` + endpoint tests).

The lesson (w) posture is now **load-bearing across two
milestones** (M30.2 surfaced + M31.1 re-applied) — elevates from
"newly surfaced at M30.2" to "load-bearing across two
milestones," matching the lesson (t) elevation pattern from
M30.2.

## 5. DoD exception path — sixth precedent

Per M21.0 §5.f Option B (M26 lineage): every customer-facing
milestone must add or update at least one Playwright operational
journey, OR explicitly document why no journey change is
required.

**M31.1 invokes the exception path** — backend substrate with
no operator-facing behavior change on its own. The
`?include_inactive=true` list-endpoint capability + the Restore
POST endpoint are both invisible to operators until M31.2 binds
them to UI. Any Playwright journey assertion at M31.1 would
require inventing a synthetic backend-only scenario that
doesn't represent operator behavior.

**Sixth invocation** (M26 + M27.1 + M28.1 + M29.1 + M30.1 +
M31.1). Pattern firmly established:

- All six invocations share the shape: a backend substrate
  landing (schema-reserve, service relaxation, new endpoint +
  verbs, etc.) followed by a UI + Playwright increment (M26 has
  no UI-follow-up; the audit tooling itself is the deliverable).
- The customer-facing follow-up increment satisfies DoD
  directly.
- No streak counter for "exception uses" — the pattern is a
  normal shape, not an anomaly.

M31.2 will satisfy DoD directly via the new
`test.describe("restore-inactive", ...)` block in
`accounting_je_template.spec.ts` — journey count 21 → 22.

## 6. Streaks at M31.1 close

- **Planning-time as-recommended streak:** unchanged at **10**
  (M31.0 close). M31.1 is pure implementation of the M31.0-
  locked plan; no re-litigation of §5.a or §5.b.
- **Zero-drift permission-class streak:** advanced **31 → 32
  consecutive milestones** (M10 → M31). Restore endpoint reuses
  `_M131_PERMS` verbatim — no new permission class added.
- **Substrate-compound-value continuation:** M31 achieves the
  fifth link (M27.1 gl-accounts → M28.1 template substrate →
  M29 variable-amount → M30 template CRUD closure → **M31
  template lifecycle closure**). Zero new migration; reuses
  M28.1 `is_active` field + M30.1 `include_inactive` kwarg.
- **DoD exception path invocations:** advanced **5 → 6** at
  M31.1 (M26 + M27.1 + M28.1 + M29.1 + M30.1 + **M31.1**).
- **Lesson (w) mutation-surface asymmetry:** elevated from
  "newly surfaced at M30.2" to "**load-bearing across two
  milestones**" (M30.2 + M31.1).
- **DRF admin surface:** 117 → **118** (+1 for Restore
  endpoint).
- **Service surface:** 317 → **318** verbs (+1 for
  `restore_journal_entry_template`).

## 7. Baselines at M31.1 close

| Metric | M30.2 close | M31.1 close | Delta |
|---|---|---|---|
| Backend suite | 4,904 pass, 1 skip | **4,933 pass, 1 skip** | +29 |
| Frontend Vitest | 300 pass, 36 files | 300 pass, 36 files | unchanged |
| Acceptance | 21 journeys | 21 journeys | unchanged |
| Migrations | 0001–0050 | 0001–0050 | unchanged |
| DRF admin | 117 | 118 | +1 |
| Frontend routes | 20 | 20 | unchanged |
| Permission classes | 7 | 7 | unchanged (streak 31 → 32) |
| Service verbs | 317 | 318 | +1 |
| Audit endpoints | 157 | 158 | +1 |
| Audit covered | 123 | 123 | unchanged (M31.2 → 124) |
| Audit backend-only | 34 | 35 | +1 transitional (M31.2 → 34) |

## 8. Files changed

- `backend/dealer_ai/services/accounting/template.py` —
  module docstring update + new
  `restore_journal_entry_template` verb appended.
- `backend/dealer_ai/services/accounting/__init__.py` —
  `restore_journal_entry_template` added to imports + `__all__`.
- `backend/dealer_ai/views_accounting.py` —
  list-endpoint GET branch extended with fail-closed
  `?include_inactive=true` parsing; new
  `admin_journal_entry_template_restore` view + section-
  header comment; import extended.
- `backend/dealer_ai/urls.py` — new pattern for the Restore
  endpoint sibling to the M30.1 detail endpoint.
- `backend/dealer_ai/tests/test_m31_journal_entry_template_
  restore_service.py` — NEW file, 13 tests.
- `backend/dealer_ai/tests/test_m28_journal_entry_template_
  endpoint.py` — two new test classes appended
  (`TemplateRestoreEndpointTests` — 7 tests;
  `TemplateListIncludeInactiveEndpointTests` — 9 tests).
- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` —
  regenerated post-implementation.

Frontend files: **none touched** — M31.1 is pure backend
substrate.

## 9. Non-goals for SESSION_204 (all honored)

- ✅ Did NOT ship any frontend or Playwright code.
- ✅ Did NOT touch `AccountingJournalEntriesPage.tsx`,
  `JournalEntryTemplateDialog.tsx`, or `accountingApi.ts`.
- ✅ Did NOT ship the D10 M30.2 copy update — bundled with
  M31.2 UI increment.
- ✅ Did NOT re-open §5.a or §5.b decisions.
- ✅ Did NOT push. Coordinated push at M31 close after
  explicit user confirmation.
- ✅ Did NOT force-push or amend earlier commits.
- ✅ Did NOT modify M1–M30 shipped surface (M30.2 delete-
  confirmation copy carrying the "Restore UX ships in a
  future milestone" text is unchanged at M31.1; D10 fulfills
  it at M31.2).
- ✅ Did NOT introduce any new permission class — Restore
  reuses `_M131_PERMS` verbatim.
- ✅ Did NOT add server-side coupling between JournalEntry
  and JournalEntryTemplate — the M28.0 §5.b + M30.0 §4.7 +
  M31.0 §4.1 decoupling stays intact.
- ✅ Did NOT add a migration. Zero-migration property
  preserved for rollback cheapness per §5.g.
- ✅ Did NOT allow PATCH to mutate `is_active` — hardened
  via new regression test.

## 10. What SESSION_205 (M31.2) opens

Per M31.0 §5.e M31.2 spec — frontend + Playwright:

- **Frontend list wrapper** (`accountingApi.ts`):
  - Extend `listJournalEntryTemplates` with optional
    `{ includeInactive?: boolean }` param; append
    `?include_inactive=true` when true.
  - New `restoreJournalEntryTemplate(pk)` wrapper.
- **Page (`AccountingJournalEntriesPage.tsx`):**
  - Show-inactive `Switch` in templates section header —
    component-local state; triggers refetch.
  - `TemplateRow` gains `is_active`-aware rendering:
    Inactive badge + row `aria-label` + testid
    `template-row-inactive-<pk>` + Restore button replacing
    Delete on inactive rows + disabled Edit + disabled
    Instantiate with explanatory aria-labels (L1 guard).
  - New inline `TemplateRestoreConfirmDialog` per D8.
  - D10 M30.2 delete-confirmation copy update.
- **Frontend tests planned (+~22):** ~14 page tests + ~6 API
  wrapper tests + ~2 delete-copy regression.
- **Playwright (+1 journey):** `test.describe("restore-inactive",
  ...)` block per M31.0 §5.e user 7-step spec — full
  reversible lifecycle including post-cycle historical-JE
  byte-identity assertion.
- **Expected counts:** frontend 300 → **~322**; acceptance
  21 → **22 journeys**; DRF admin unchanged at 118 (no new
  endpoint at M31.2); audit 158 / 124 / 34 / 318 (Restore
  endpoint re-classifies to covered).

### First thing SESSION_205 must do

1. Verify starting state (backend **4,933 pass**, frontend
   Vitest 300 pass, acceptance 21, tsc + check + makemigrations
   clean, redis PONG, acceptance DB reset).
2. Read `docs/roadmap/MILESTONE_31_PLANNING.md` §5.b D4–D10
   + §5.e M31.2 spec before writing UI code.
3. Ship M31.2 frontend + Playwright per §5.e.
4. Verify M31.2 close baselines (backend unchanged at 4,933;
   frontend ~322 pass; acceptance 22 journeys; audit
   158/124/34/318).
5. Fold M31 close-out into the same SESSION_205 handoff
   (per M30.2 close-out fold precedent — no separate M31.3).
6. Ship the M31.2 handoff at
   `docs/handoffs/SESSION_205_m31_inc2_frontend.md`.
7. **Coordinated M31 close push** — await explicit user
   confirmation before pushing.

## 11. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. **`docs/roadmap/MILESTONE_31_PLANNING.md`** — M31
   governing contract; §5.b D4–D10 + §5.e M31.2 spec govern
   SESSION_205 implementation
6. `docs/roadmap/MILESTONE_30_RETROSPECTIVE.md` §9 (M31
   candidate list origin)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` (post-
   M31.1 baseline — 158 endpoints / 123 covered / 35
   backend-only transitional / 318 service verbs; M31.2
   projected delta 0 endpoint / +1 covered / -1 backend-only
   / 0 verb)
8. `docs/CAPABILITY_MATRIX.md` §7ζ added at M31 close
9. `docs/handoffs/SESSION_203_m31_inc0_planning.md` (M31.0
   planning shipped)
10. **This handoff** (`SESSION_204_m31_inc1_backend.md`)
11. `docs/handoffs/SESSION_202_m30_inc2_frontend.md` (M30.2
   shipped + M30 close-out; source of shipped Restore-
   promise copy that D10 fulfills at M31.2)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs D8 co-located inline dialog at
    M31.2)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0 §6.6)
