---
state: active
date: 2026-08-04
last_session_shipped: SESSION_204
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
next_session: SESSION_205
next_milestone: 31
next_milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
next_increment: 2
next_increment_name: "M31.2 — Frontend + Playwright (Show-inactive toggle + inactive-row rendering + Restore UI + D10 copy fulfillment + reversible-lifecycle journey)"
---

# Next session — SESSION_205 · Milestone 31 · Increment 2 (M31.2 — frontend + Playwright + M31 close-out fold)

> **M31.1 backend substrate SHIPPED at SESSION_204.** New
> Restore verb + POST endpoint + list `?include_inactive=true`
> fail-closed parsing landed with zero migration. Backend
> baseline advanced **4,904 → 4,933** (+29 tests: 13 service +
> 7 restore endpoint + 9 include_inactive parsing). Audit
> transitional state **158 / 123 / 35 / 318** — M31.2 will
> re-cover the new Restore endpoint via the frontend wrapper
> and close at **158 / 124 / 34 / 318**.
>
> **Zero-drift permission-class streak advanced 31 → 32** at
> M31.1 (Restore endpoint reused `_M131_PERMS` verbatim).
> **DoD exception path #6 invoked** — pattern firmly
> established at six invocations (M26 + M27.1 + M28.1 + M29.1
> + M30.1 + M31.1).
>
> **Lesson (w) mutation-surface asymmetry elevated to
> "load-bearing across two milestones"** — M30.2 surfaced,
> M31.1 re-applied by adding Restore as second dedicated
> lifecycle verb + new regression test
> `test_patch_still_cannot_mutate_is_active_after_m31`.
>
> **SESSION_205 opens M31.2** — frontend + Playwright + M31
> close-out fold per M30.2 precedent. Show-inactive toggle,
> inactive-row rendering (Inactive badge + row aria-label +
> testid + muted styling), Restore button on inactive rows,
> disabled Edit/Instantiate on inactive rows (L1 lifecycle-
> integrity guard), inline `TemplateRestoreConfirmDialog`,
> `restoreJournalEntryTemplate` wrapper, list wrapper
> `includeInactive` param, D10 M30.2 delete-confirmation copy
> fulfillment, single new `test.describe("restore-inactive",
> ...)` block in `accounting_je_template.spec.ts` per §5.e
> M31.2 spec. Journey count 21 → 22. **DoD satisfied
> directly** at M31.2.
>
> **Coordinated M31 close push at M31.2 close** — awaits
> explicit user confirmation per M27/M28/M29/M30 cadence.

## First thing SESSION_205 must do

### 1. Verify starting state

- `git status` — clean; local `HEAD` ahead of `origin/main` by
  4 commits (SESSION_203 M31.0 planning + M31.0 hash-backfill
  + SESSION_204 M31.1 + M31.1 hash-backfill).
- `git log --oneline -10` — top should be the SESSION_204 M31.1
  hash-backfill commit.
- `python3 manage.py test dealer_ai` → **4,933 pass, 1
  skipped, 0 fail**.
- `cd frontend && npm test` → **300 pass** across 36 files.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc --noEmit` clean.
- `cd acceptance && npx tsc --noEmit` clean.
- `redis-cli ping` → `PONG`.
- `rm -f backend/db.acceptance.sqlite3` — proactive reset per
  SESSION_200 §0.a durable lesson (v).

### 2. Read the M31 governing contract before writing UI code

- `docs/roadmap/MILESTONE_31_PLANNING.md` §5.b D4 (frontend
  list wrapper `includeInactive` parameter), D5 (Show-inactive
  is explicit operator toggle), D6 (inactive rows visually AND
  semantically distinct — three independent signals: Badge +
  aria-label + testid), D7 (row-action asymmetry + L1
  visible-but-disabled guard with explanatory aria-label), D8
  (Restore confirmation dialog vocabulary asymmetry — mandated
  copy), D9 (historical JEs untouched — Playwright load-bearing
  assertion), D10 (M30.2 delete-confirmation copy fulfillment).
- `docs/roadmap/MILESTONE_31_PLANNING.md` §5.e M31.2 spec — wrapper,
  page changes, tests, Playwright 7-step journey.
- `docs/handoffs/SESSION_204_m31_inc1_backend.md` §10 (what
  SESSION_205 opens with) + §3 (D3 fail-closed parsing shape
  the wrapper must match).

Do **not** re-open scope. §5.a target and all §5.b decisions
are locked; any narrow amendment goes through the §0.a
change-log path in the planning memo.

### 3. Ship M31.2 frontend + Playwright

Per `MILESTONE_31_PLANNING.md` §5.e M31.2:

- **Frontend list wrapper** (`frontend/src/lib/accountingApi.ts`):
  - Extend `listJournalEntryTemplates(dealershipId)` with
    optional `{ includeInactive?: boolean }`; append
    `?include_inactive=true` when true.
  - New `restoreJournalEntryTemplate(pk)` — wraps
    `authPostJSON` (POST empty body); returns projected
    template.
- **Page (`frontend/src/pages/AccountingJournalEntriesPage.tsx`):**
  - Show-inactive `Switch` (or `Checkbox`) in templates
    section header — component-local state; triggers
    refetch when changed.
  - `TemplateRow` gains `is_active`-aware rendering:
    - Inactive badge (shadcn `Badge`) adjacent to template
      name.
    - Row `aria-label="Template <name>, inactive"`.
    - New testid `template-row-inactive-<pk>`.
    - Delete slot → Restore button
      (`data-testid="tmpl-restore-trigger-<pk>"`).
    - Edit button visible-but-disabled with
      `aria-label="Edit template — restore it first to
      enable"`.
    - Instantiate button visible-but-disabled with
      `aria-label="Instantiate template — template is
      inactive; restore it first to enable"`. **This is
      the L1 lifecycle-integrity guard.**
  - New inline `TemplateRestoreConfirmDialog` co-located
    with `TemplateDeleteConfirmDialog`. Mandated copy per
    D8: title "Reactivate template?"; body reassures
    historical JEs unaffected; footer `[Cancel]
    [Reactivate]`; test-ids `tmpl-restore-confirm-body`,
    `tmpl-restore-cancel`, `tmpl-restore-submit`.
  - **D10 copy fix:** update the M30.2 Delete confirmation
    body at `AccountingJournalEntriesPage.tsx:670-672` from
    *"You can restore this template later. (Restore UX
    ships in a future milestone.)"* to *"You can restore
    this template later — turn on **Show inactive** to find
    and reactivate it."*
- **Frontend tests planned (+~22):**
  - `AccountingJournalEntriesPage.test.tsx` (+~14): toggle
    renders + default off; toggle triggers refetch with
    `includeInactive=true`; Inactive badge; row aria-label;
    inactive testid; Restore button renders; Edit disabled
    + aria-label; Instantiate disabled + aria-label; Restore
    click opens confirmation; Restore confirm calls
    `restoreJournalEntryTemplate` + refetches; failure
    surfaces inline error without closing.
  - `accountingApi.templates.test.ts` (+~6):
    `listJournalEntryTemplates` with `includeInactive=true`
    appends `?include_inactive=true`; false or omitted does
    not append; `restoreJournalEntryTemplate` POST URL;
    propagates 404; propagates 500; 200 returns projected
    template.
  - +~2 regression assertions on D10 updated Delete-confirm
    copy.
- **Playwright (+1 journey):** new
  `test.describe("restore-inactive", ...)` block in
  `acceptance/journeys/office/accounting_je_template.spec.ts`.
  Full 7-step reversible lifecycle per §5.e:
  1. Seed an active template via admin API ($100/$100);
     confirm default active list.
  2. Row Delete → confirm Deactivate → template disappears
     from default list; reload → still gone.
  3. Toggle Show inactive ON.
  4. Assert `template-row-inactive-<pk>` testid + Inactive
     badge visible + row aria-label contains "inactive" +
     Instantiate button `toBeDisabled()` + Edit button
     `toBeDisabled()`.
  5. Click Restore → confirmation with D8 copy → click
     Reactivate.
  6. Toggle Show inactive OFF.
  7. Assert template reappears in default active list +
     Instantiate re-enabled + click Instantiate opens JE
     dialog prepopulated → post fresh JE → assert JE
     appears in Journal Entries list. **Load-bearing
     lifecycle assertion:** historical JE + total_debit +
     trial-balance total byte-identical before and after
     the full cycle.

### 4. Verify M31.2 close baselines

- Backend suite: unchanged (**4,933 pass**, 1 skipped, 0 fail).
- Frontend Vitest: **300 → ~322 pass** across 36 files.
- Acceptance: **21 → 22 journeys**. Full-suite fresh-DB run
  expected ~35-40s local.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` → "No
  changes detected."
- Frontend `tsc --noEmit` clean.
- Acceptance `tsc --noEmit` clean.
- Audit regen: **158 / 124 / 34 / 318** (+1 covered from M31.1
  transitional; -1 backend-only as the Restore endpoint re-
  classifies to covered via the M31.2 wrapper). Two-source
  agreement gate at M31.2 close per convention.
- `git grep "Restore UX ships in a future milestone" frontend/
  acceptance/`: empty (D10 fulfillment verified).

### 5. Fold M31 close-out into the SESSION_205 handoff

Per M30.2 close-out precedent — no separate M31.3 session.
Include in the SESSION_205 handoff:

- M31 retrospective (`docs/roadmap/MILESTONE_31_RETROSPECTIVE.md`).
- CAPABILITY_MATRIX.md §7ζ addition for M31 shipped surface.
- Milestone status flip in
  `docs/roadmap/MILESTONE_31_PLANNING.md` (status: active →
  shipped; shipped_at_session: SESSION_205).
- Streak accounting summary at M31 close.

### 6. Ship the SESSION_205 handoff

- `docs/handoffs/SESSION_205_m31_inc2_frontend.md`.
- **Coordinated M31 close push** — await explicit user
  confirmation before pushing. Expected M31 commit count at
  push: **4–6** (SESSION_203 planning + M31.0 hash-backfill +
  SESSION_204 M31.1 + M31.1 hash-backfill + this session's
  M31.2 + close-out commits + hash-backfill follow-up).

## Non-goals for SESSION_205

- ❌ Do NOT modify any M31.1 backend surface — Restore verb,
  endpoint, and `?include_inactive` parsing are locked.
- ❌ Do NOT add any new backend tests unless a regression
  surfaces (very unlikely — M31.1 exhaustively covers the
  substrate).
- ❌ Do NOT add a migration.
- ❌ Do NOT introduce any new permission class.
- ❌ Do NOT re-open §5.a or §5.b decisions.
- ❌ Do NOT re-litigate the L1 visible-but-disabled framing —
  locked per SESSION_203 user confirmation of §5.b review
  point 2.
- ❌ Do NOT deviate from D8 mandated copy without user
  confirmation.
- ❌ Do NOT hide inactive rows' Edit / Instantiate buttons
  (visible-but-disabled per D7 + L1).
- ❌ Do NOT rely on muted styling alone for inactive rows —
  three independent signals per D6 are load-bearing.
- ❌ Do NOT add server-side coupling between JournalEntry and
  JournalEntryTemplate. The stale-tab race outcome remains
  accepted per R1.
- ❌ Do NOT modify pre-M30 shipped surface. D10 fulfillment
  is the only shipped-copy modification permitted.
- ❌ Do NOT push without explicit user confirmation.

## Baseline expected at close

- Backend: unchanged (4,933 pass, 1 skipped, 0 fail).
- Frontend: 300 → ~322 pass across 36 files.
- Acceptance: 21 → 22 journeys.
- Migrations: 0001–0050 unchanged.
- DRF admin surface: 118 unchanged (no new endpoint at
  M31.2).
- Service verbs: 318 unchanged.
- Frontend operator routes: 20 unchanged (Show-inactive
  toggle + inactive-row rendering attach to the existing JE
  list page).
- Permission classes: 7 unchanged (zero-drift streak
  advances 32 → 33 at M31 close).
- Audit: 158 / 124 / 34 / 318 (from M31.1's transitional
  158/123/35/318).

## NEXT TASK

Start SESSION_205 with (a) starting-state verification;
(b) read M31 governing contract §5.b D4–D10 + §5.e M31.2;
(c) implement frontend wrapper + page changes per §5.e;
(d) ship ~22 frontend tests + 1 Playwright journey per §5.e;
(e) verify close baselines (frontend ~322 + acceptance 22 +
audit 158/124/34/318); (f) fold M31 close-out (retrospective +
CAPABILITY_MATRIX §7ζ + planning memo status flip);
(g) ship SESSION_205 handoff; (h) await explicit user
confirmation before coordinated M31 close push.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M30 shipped surface in
   CAPABILITY_MATRIX §7δ + §7ε per convention; §7ζ added
   at M31 close)
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
8. `docs/CAPABILITY_MATRIX.md` §7z–§7ε (M25 → M30 shipped
   surface); §7ζ added at M31 close
9. `docs/handoffs/SESSION_203_m31_inc0_planning.md` (M31.0
   planning shipped — §5 locks summary + L1 lifecycle-
   integrity precheck + confirmed §5.b review points)
10. **`docs/handoffs/SESSION_204_m31_inc1_backend.md`** (M31.1
    backend substrate shipped — service + endpoint + list
    parsing + tests; lesson (w) hardened)
11. `docs/handoffs/SESSION_202_m30_inc2_frontend.md` (M30.2
    shipped + M30 close-out; source of shipped Restore-
    promise copy that D10 fulfills)
12. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs D8 co-located inline dialog)
13. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0 §6.6)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

---

## Operational state (post-SESSION_204 — Milestone 31 ACTIVE at M31.1)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0050` (unchanged since M28.1). Test baseline:
  **4,933 pass**, 1 skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit` +
  `vite build` clean. Vitest baseline: **300 pass** across
  36 test files. **Projected at M31.2 close: ~322 pass.**
- **Frontend (prod):** NONE.
- **Acceptance workspace (local):** Playwright 1.49 + TS 5.6
  operational; **21 journeys** total. **Projected at M31.2
  close: 22 journeys.**
- **Acceptance (CI):** live on
  `.github/workflows/acceptance.yml`. Latest run on
  `origin/main` at `f658c06` (M30.2 hash-backfill commit):
  26 passed / 0 failed / 2m50s. First M31 CI run pending
  on the coordinated M31 close push.
- **Async runtime:** Celery 5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1 DatabaseScheduler. 10
  scheduled task families registered.
- **Milestones shipped:** M1 → **M30**. **M31 active at
  M31.1** (SESSION_204 backend substrate shipped);
  M31.2 target SESSION_205 with fold-in close-out.
- **DRF admin surface:** **118** endpoints (M28.1 116 → +1
  at M30.1 → +1 at M31.1). Unchanged at M31.2 (no new
  endpoint).
- **Frontend operator routes:** 20 (unchanged; M31.2 will
  attach Show-inactive toggle + row-state rendering to the
  existing JE list page).
- **Public endpoints:** +1 M6.5 showroom (unchanged).
- **Service surface:** **318** verbs (M30 close 317 → +1
  `restore_journal_entry_template` at M31.1).
- **Frontend surfaces:** unchanged at M31.1. M31.2 will
  add Show-inactive toggle, `TemplateRestoreConfirmDialog`,
  inactive-row rendering (Inactive badge + aria-label +
  testid + muted opacity), disabled Edit/Instantiate on
  inactive rows (L1 guard), D10 copy update on
  `TemplateDeleteConfirmDialog`.
- **Tenancy carriers:** 52 (unchanged).
- **Permission classes:** **7 actual** — zero-drift streak
  advanced **32 consecutive milestones** (M10 → M31 at
  M31.1; M31.2 adds no endpoints so streak advances to 33
  at M31 close).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages (unchanged).
- **Deterministic rules:** unchanged.
- **Milestone 31 status:** ACTIVE at M31.1. M31.0
  planning + M31.1 backend substrate landed. M31.2 UI +
  Playwright + close-out fold target SESSION_205.
- **Audit tooling status:** unchanged from M26.1.
  Coverage post-M31.1: **123 / 158** (transitional; +1
  endpoint, +1 backend-only). Projected at M31.2 close:
  **124 / 158** (+1 covered; -1 backend-only as Restore
  endpoint re-classifies to covered).
- **§9 evidence carried into M31.2:** NEW Restore /
  "Show inactive" UI toggle (selected as M31 target at
  M31.0; backend substrate shipped M31.1; UI + Playwright
  target M31.2); NEW C F&I chargeback substrate
  (unchanged — gated pending pilot evidence); NEW O2 +
  NEW O3 (unchanged); H test-hygiene (unchanged); gated
  T/U/L/M unchanged; deferred D + deferred-stable G
  unchanged; M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25 §4
  deferrals unchanged. New at M31 §3: template mutation
  history / diff viewer; auto-refresh of stale-tab
  template list (accepted per R1); persistent Show-inactive
  toggle state; bulk lifecycle actions.
- **Planning-time streak: 10** (at M31.0 close; unchanged
  at M31.1 — pure implementation; historical run of 89
  across M10 → M23 preserved).
- **DoD amendment (M21.0 §5.f Option B):** every future
  customer-facing milestone must add or update at least
  one Playwright operational journey, or explicitly
  document in §3 why no journey change is required.
  Precedents: M26 first, M27.1 second, M28.1 third,
  M29.1 fourth, M30.1 fifth, **M31.1 sixth**. M31.2 will
  satisfy DoD directly via new `restore-inactive`
  describe block.
- **Post-M31.1 audit coverage:** 158 endpoints, **123
  covered / 35 backend-only** (transitional — Restore
  endpoint at index 152 counted as backend-only until
  M31.2 frontend wrapper lands). M31.2 close will
  re-classify to **158 / 124 / 34**.
- **Durable lessons carried into M31.2:** all (a)–(x) from
  the M30 close-state list continue to apply. M31.1
  hardened lesson (w) — elevated from "newly surfaced at
  M30.2" to "load-bearing across two milestones" via
  Restore as second dedicated lifecycle verb + regression
  test `test_patch_still_cannot_mutate_is_active_after_m31`.
  M31.2 will re-apply lesson (x) — row "Restore" →
  confirmation "Reactivate template?" copy asymmetry —
  elevating (x) to "load-bearing across two milestones"
  as well.
