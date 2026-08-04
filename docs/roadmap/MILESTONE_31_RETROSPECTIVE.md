---
title: "Milestone 31 — Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 + M30.1 substrate) — Retrospective"
status: historical
type: retrospective
milestone: 31
milestone_status: shipped
generated: 2026-08-04
generated_at_session: SESSION_205 (M31.2 close + close-out fold)
milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 + M30.1 substrate)"
increments_shipped: [0, 1, 2]
close_out_fold: true
sessions: [203, 204, 205]
commits_at_close: 6
---

# Milestone 31 — Template Restore / "Show inactive" UI — Retrospective

> Milestone 31 opened at SESSION_203 M31.0 planning under the
> durable primary operational-coverage lens **evaluated as a
> lifecycle-completion workflow per explicit user direction** —
> not as UI polish and not solely as a substrate-compound-value
> continuation. M31.1 shipped the backend substrate at
> SESSION_204 (Restore verb + POST endpoint + list
> `?include_inactive=true` fail-closed parsing). M31.2 shipped
> the customer-facing UI + Playwright + M31 close-out at
> SESSION_205 (Show-inactive toggle, inactive-row rendering
> with three independent a11y signals, Restore row action +
> confirmation dialog, L1 lifecycle-integrity guard on
> Edit/Instantiate, D10 M30.2 copy fulfillment, 7-step
> reversible-lifecycle Playwright journey).
>
> **The anchor business question** — *Can a dealership
> accountant safely view previously deactivated journal-entry
> templates, understand their status, and restore one to active
> use — without engineering intervention — while existing
> journal entries and reports remain completely unaffected?* —
> is answered **yes**. A single Playwright journey covers the
> full reversible lifecycle (deactivate → toggle Show inactive
> → verify three D6 signals + L1 disabled Instantiate/Edit +
> Restore button → Reactivate → toggle off → template back in
> default list + Instantiate re-enabled + post fresh JE), with
> the D9 load-bearing assertion that historical JE description
> AND `total_debit` are byte-identical before and after the
> full round-trip.
>
> M31 realized the **fifth link** in the substrate-compound-
> value lineage (M27.1 gl-accounts → M28.1 template substrate →
> M29 variable-amount extension → M30 template CRUD closure →
> **M31 template lifecycle closure**) — spent with **zero new
> migrations**, demonstrating for the fifth consecutive
> milestone that lifecycle extensions on well-designed
> substrate cost measurably less than green-field milestones.

## 1. Planned scope

Per `MILESTONE_31_PLANNING.md` §5.a locked at open: **NEW
Restore / "Show inactive" templates UI (lifecycle-completion)**.

Two-increment split per §5.e:

- **M31.1 (SESSION_204)** — backend substrate: new
  `restore_journal_entry_template(*, pk, dealership)` service
  verb + new POST endpoint
  `admin/accounting/journal-entry-templates/<int:pk>/restore/`
  + list endpoint `?include_inactive=true` fail-closed
  parsing extension (per D3 — only literal `true` case-
  insensitive opts in). Zero migration. DoD exception path
  invoked as **sixth precedent** (M26 + M27.1 + M28.1 +
  M29.1 + M30.1 + M31.1).
- **M31.2 (SESSION_205)** — frontend + Playwright: extend
  `fetchJournalEntryTemplates` with `includeInactive`
  option; add `restoreJournalEntryTemplate` wrapper;
  Show-inactive toggle on the templates section header;
  is_active-aware `TemplateRow` rendering with three D6
  signals (Inactive badge + row aria-label + dedicated
  testid); L1 lifecycle-integrity guard on inactive rows
  (visible-but-disabled Edit + Instantiate with explanatory
  aria-labels); Delete-slot swaps to Restore button on
  inactive rows (D7 asymmetry); inline
  `TemplateRestoreConfirmDialog` with D8 mandated copy
  ("Reactivate template?" reframing per lesson (x)
  asymmetry); D10 M30.2 delete-confirmation copy
  fulfillment update; single new
  `test.describe("restore-inactive", ...)` block extending
  `accounting_je_template.spec.ts` with 7-step reversible-
  lifecycle journey. DoD satisfied directly.

Lifecycle-integrity precheck performed at M31.0 planning-open
per explicit user direction, before locking §5.b:

- **L1 stale-instantiation trace** — traced
  `handleInstantiate` at
  `AccountingJournalEntriesPage.tsx:271`. Confirmed
  instantiation is purely client-side hydration; the JE
  POSTed via `createJournalEntry` never carries the template
  pk. Consequences: (a) stale-tab race outcomes **accepted
  per user direction** — JournalEntry and JournalEntryTemplate
  are intentionally decoupled (M28.0 §5.b + M30.0 §4.7);
  server-side coupling explicitly rejected; (b) Show-inactive
  view requires the smallest fail-closed frontend guard —
  disable Edit + Instantiate on inactive rows with
  explanatory aria-label. Recorded as lifecycle integrity,
  not feature expansion.

## 2. What actually shipped

**M31.0 planning (SESSION_203):** full active memo at
`MILESTONE_31_PLANNING.md` — §5.a locked as NEW Restore /
"Show inactive" UI under the primary operational-coverage
lens (lifecycle-completion framing); §5.b D1–D10, 10-item
risk register (R1 accepted stale-tab race), 8 verifications
including L1 precheck, two-increment phasing, DoD compliance,
rollback plan, non-goals. Six user-confirmed §5.b review
points locked: D3 fail-closed parsing (only literal `true`
case-insensitive), D7 visible-but-disabled controls with
aria-labels (not silently hidden), D8 confirmation copy as
drafted, D10 M30.2 copy update bundled in M31.2, M31.1 test
budget ~24–26, L1 framing as lifecycle-integrity not feature
expansion. First M30 CI run verified green at open (workflow
`30930670900` on `f658c06`, 26 passed / 2m50s). No §0.a M31.0
amendments.

**M31.1 backend substrate (SESSION_204):**

- **Service layer** (`services/accounting/template.py`):
  - New `restore_journal_entry_template(*, pk, dealership)`
    verb — atomic reactivate; guard clause on
    `if not template.is_active` so already-active input
    returns row without a save; explicit
    `update_fields=["is_active", "updated_at"]` on the
    state-change branch (Django auto-now triggers only via
    `save()`); tenant-scoped via `get_journal_entry_template
    (include_inactive=True)`; returns
    `Optional[JournalEntryTemplate]` (None → 404 at
    endpoint layer).
  - Module docstring updated: five verbs → **six verbs**;
    documents lesson (w) mutation-surface asymmetry
    hardening (Restore is a dedicated verb, never a PATCH
    side-effect; activation now backed by two dedicated
    verbs — Delete/Deactivate + Restore/Reactivate).
  - `services/accounting/__init__.py`: exported
    `restore_journal_entry_template`; alphabetically
    inserted into `__all__`.
- **Endpoint layer** (`views_accounting.py`):
  - New `admin_journal_entry_template_restore(request, pk)`
    view (POST-only). Reuses `_M131_PERMS`. Error mapping:
    200 with projected row on success + idempotent
    already-active, 404 on missing/cross-tenant.
  - Extended `admin_journal_entry_template_list_or_create`
    GET branch with `include_inactive =
    request.GET.get("include_inactive", "").lower() ==
    "true"` per D3 fail-closed parsing.
- **URL** (`urls.py`): new pattern
  `admin/accounting/journal-entry-templates/<int:pk>/restore/`
  → `admin-journal-entry-template-restore`. Sibling of
  M30.1 detail endpoint; same shape as audit endpoint #68
  (`admin/vehicle-photos/<uuid:public_id>/restore/`).
- **Zero migration** — reuses M28.1 `is_active` field.
- **Tests +29** (planned ~24–26; excess +3–5 from adding
  auth-denial + preserves-is_active regression coverage per
  M30.1 lesson — better over-than-under):
  - NEW `test_m31_journal_entry_template_restore_service.py`
    (13 tests: happy path, idempotency incl. updated_at
    no-advance on no-save path, missing/cross-tenant None,
    preservation contract for name/description/lines byte-
    identical/created_at, updated_at state-change end-to-
    end, post-Restore visibility via default get).
  - EXTENDED `test_m28_journal_entry_template_endpoint.py`
    with `TemplateRestoreEndpointTests` (7 tests: POST 200
    with projected row + re-appears in default list,
    idempotent already-active 200 twice, missing pk 404,
    cross-tenant 404 + foreign row untouched, advisor
    denied 403, unauth 401/403, PATCH still cannot mutate
    is_active after M31.1 — regression re-assertion of the
    M30.2 durable lesson (w) enforcement).
  - EXTENDED `test_m28_journal_entry_template_endpoint.py`
    with `TemplateListIncludeInactiveEndpointTests` (9
    tests for D3 fail-closed parsing across `true`/`TRUE`/
    `True`/`false`/`1`/`yes`/empty/malformed/missing).

**M31.2 UI + Playwright + close-out fold (SESSION_205):**

- **Frontend wrapper** (`accountingApi.ts`):
  - `fetchJournalEntryTemplates` extended with optional
    `{ includeInactive?: boolean }`; appends
    `?include_inactive=true` when true.
  - New `restoreJournalEntryTemplate(pk)` wrapper — POST
    with empty body; returns projected template.
- **Page (`AccountingJournalEntriesPage.tsx`):**
  - Show-inactive `<input type="checkbox">` in the
    templates section header (aria-label "Show inactive
    templates" + testid `templates-show-inactive-toggle`);
    default off; component-local state; refetch fires
    whenever it flips. Consistent with existing plain-
    checkbox convention across the codebase (M28.2
    `NewJournalEntryDialog`, `DealerAiSalesFollowUps`,
    `VehicleReconPage`, etc.) — no new shadcn primitive
    added.
  - `TemplateRow` gains is_active-aware rendering with
    three independent D6 signals on inactive rows:
    - Visible `Badge` (shadcn) labeled "Inactive" with
      testid `template-inactive-badge-<pk>`.
    - Row `aria-label="Template <name>, inactive"`.
    - Dedicated testid `template-row-inactive-<pk>`
      distinct from the active-row `template-row-<pk>`
      pattern.
    - Plus muted opacity styling as reinforcement (not
      primary signal, per D6).
  - Row-action asymmetry per D7 + L1 guard on inactive
    rows: Instantiate + Edit remain visible but disabled
    (`disabled={disabled || isInactive}`) with explanatory
    aria-labels ("Instantiate template — template is
    inactive; restore it first to enable" and "Edit
    template — restore it first to enable"); Delete slot
    swaps to Restore button (`tmpl-restore-trigger-<pk>`).
  - Restore state + handlers (`restoringTemplate`,
    `restoreSubmitting`, `restoreError`,
    `lastRestoredTemplate`; `handleRestoreClick`,
    `handleRestoreCancel`, `handleRestoreConfirm`) mirror
    the M30.2 delete flow shape.
  - Restore success badge (`tmpl-restore-success-badge`)
    surfaces on successful Restore, cleared by
    Show-inactive toggle changes.
  - New inline `TemplateRestoreConfirmDialog` co-located
    with `TemplateDeleteConfirmDialog` per M28.0
    duplicate-small-stable-domain-logic rule — no shared
    abstraction. Mandated D8 copy: title "Reactivate
    template?" (truth vocabulary — is_active transitions
    False → True); body "Are you sure you want to
    reactivate <name>? This template will reappear in the
    active templates list and can be used to create new
    journal entries again. Existing journal entries created
    from this template are not affected — they remain
    unchanged in the Journal Entries list and in trial
    balance reports."; `[Cancel] [Reactivate]` footer with
    Reactivate as primary (not destructive).
  - **D10 fulfillment:** M30.2 delete-confirmation body
    updated from *"You can restore this template later.
    (Restore UX ships in a future milestone.)"* to *"You
    can restore this template later — turn on **Show
    inactive** to find and reactivate it."* `git grep
    "Restore UX ships in a future milestone" frontend/
    acceptance/` shows only the D10 guard test's assertion
    itself; shipped code has zero hits.
- **Frontend tests +19** (planned ~22; slight under-run
  because the D10 fulfillment update was accomplished by
  updating one existing assertion + adding one guard test
  rather than the ~2 originally budgeted):
  - `AccountingJournalEntriesPage.test.tsx` +12: Show-
    inactive toggle renders + default off; toggle flip
    triggers refetch with `includeInactive=true`; three
    inactive-row D6 signals (badge + aria-label + testid);
    L1 disabled Instantiate + Edit with explanatory
    aria-label; active-row unchanged after M31.2; Delete/
    Restore slot swap on is_active; Restore confirmation
    D8 mandated copy; Restore confirm + success badge;
    Restore failure inline error without closing; Restore
    cancel closes without wrapper call; D10 copy
    fulfillment (positive + negative "future milestone"
    guard).
  - `accountingApi.templates.test.ts` +7:
    fetchJournalEntryTemplates `?include_inactive=true`
    shape across omitted/false/true;
    restoreJournalEntryTemplate POST URL + envelope
    projection + 404 propagation + 500 propagation.
- **Playwright +1 journey** — single new `test.describe(
  "restore-inactive", ...)` block extending
  `accounting_je_template.spec.ts`. 7-step journey:
  1. Seed a fresh balanced template via admin API +
     instantiate through shipped UI + post one historical
     JE (D9 byte-identity baseline).
  2. Row Delete → confirm Deactivate (assert D10 copy
     "turn on Show inactive to find and reactivate it")
     → template disappears from default list; reload →
     still gone.
  3. Toggle Show inactive ON.
  4. Assert three D6 signals (aria-label + Inactive badge
     + inactive testid) + L1 guard (Instantiate
     `toBeDisabled()` with aria-label + Edit
     `toBeDisabled()`) + D7 asymmetry (Delete gone;
     Restore present).
  5. Click Restore → confirmation with D8 mandated copy
     ("Reactivate template?" + "will reappear in the
     active templates list" + "Existing journal entries
     created from this template are not affected") →
     click Reactivate.
  6. Toggle Show inactive OFF.
  7. Template back in default active list + Instantiate
     re-enabled + click Instantiate + post fresh JE.
     **Load-bearing D9 assertion:** historical JE from
     step 1 description AND `total_debit` byte-identical
     before and after the full deactivate → restore
     cycle; post-cycle JE also lands correctly with the
     expected description.
- **M31 close-out fold:** MILESTONE_31_RETROSPECTIVE.md
  authored (this document); CAPABILITY_MATRIX.md §7ζ
  added; MILESTONE_31_PLANNING.md status flipped from
  active to shipped.

## 3. Deviations from plan and reason

None material.

Two quantitative deviations from planning worth recording as
informative-not-corrective:

- **Backend test count:** planned ~24–26 (§5.e M31.1), actual
  **+29**. Excess +3–5 from adding explicit auth-denial
  (advisor + unauth on Restore endpoint) + preserves-
  is_active regression re-assertion
  (`test_patch_still_cannot_mutate_is_active_after_m31`)
  beyond the primary happy-path + error-mapping coverage.
  All additions strengthen the endpoint's safety envelope;
  none add architectural surface. Matches M30.1's pattern
  exactly (M30.1 planned +22, actual +33 for same reasons).
  **Future §5.b test-count estimates on CRUD-endpoint /
  lifecycle-verb additions can budget +5–10 auth/tenancy/
  regression tests on top of primary coverage.**
- **Frontend test count:** planned ~22, actual **+19**.
  Slight under-run because the D10 fulfillment was
  accomplished by updating one existing M30.2 delete-copy
  assertion + adding one guard test rather than the ~2
  separate regression tests originally budgeted.
  Insignificant deviation; matches spirit of the plan.

Playwright journey count matched plan exactly (21 → 22).

## 4. Deferrals from M31 (all valid for later re-entry)

Per `MILESTONE_31_PLANNING.md` §5.h — unchanged at M31.2 close:

- **Hard-delete escape hatch** on templates (query param,
  alt endpoint, admin escape hatch) — remains M30 §3
  deferral. Gated on operator evidence.
- **Bulk delete / bulk restore / bulk edit** on templates —
  remains M30 §3 deferral. Gated on operator evidence.
- **Template mutation audit history** (`edited_by_user`,
  history rows, restore/deactivate log) — remains M30 §3
  deferral; consider under M (multi-operator) if evidence
  surfaces.
- **Optimistic concurrency control** (ETag / `updated_at`
  check) on Restore or Deactivate — remains M30 §3 deferral;
  gated on M (multi-operator).
- **Template mutation history / diff viewer** — new M31 §3
  deferral. Future re-entry candidate.
- **Server-side filtering / pagination** on templates list —
  remains M25 §4 deferral. Show-inactive is a client-side
  re-request, not a paginated cursor.
- **Auto-refresh / websocket invalidation** of stale-tab
  template list — accepted per R1; new M31 §3 deferral as
  intentional decoupling consequence.
- **Persistent Show-inactive toggle state** (URL param,
  localStorage) — new M31 §3 deferral. Toggle is component-
  local state — fresh page mount = default off.
- **Bulk lifecycle actions** across the templates list
  (Restore all inactive / Deactivate all active) — new M31
  §3 deferral.
- **Server-side coupling between JournalEntry and
  JournalEntryTemplate** — **explicitly rejected**, not
  deferred. Per R1 accepted-race-outcome + M28.0 §5.b +
  M30.0 §4.7 + M31.0 §4.1: the JE ↔ JET decoupling is
  load-bearing on Restore/Deactivate safety; adding a
  coupling would break the intentional contract.

All prior M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25 §4
deferrals carried forward unchanged.

## 5. Durable design principles surfaced or reinforced

Eight principles carried forward from M30 continue to apply.
Two are elevated at M31, and one is newly SURFACED:

- **(ELEVATED, first re-application) `is_active` mutation
  surface asymmetry is a load-bearing design constraint.**
  Durable lesson (w) surfaced at M30.2 (Delete/Deactivate
  as the sole activation-lifecycle verb; PATCH silently
  drops `is_active`). **M31.1 re-applied successfully** by
  adding Restore as the second dedicated activation verb
  and re-asserting the PATCH-cannot-mutate constraint via
  `test_patch_still_cannot_mutate_is_active_after_m31`.
  Layered enforcement now covers three surfaces (serializer
  omission + service `update_fields` + endpoint regression
  tests from both M30.2 and M31.1 pathways). Elevates from
  "newly surfaced at M30.2" to "load-bearing across two
  milestones." **Consideration for future milestones:** any
  future soft-hide / lifecycle field on any model should
  apply the same asymmetry — mutation only through explicit
  Deactivate/Restore verbs, never through general PATCH;
  and if a Restore counterpart is added, re-assert the
  PATCH-cannot-mutate constraint in a new regression test
  that names the sibling verb (`test_patch_still_cannot_
  mutate_X_after_MYY`).

- **(ELEVATED, first re-application) Row-action vocabulary
  reframes to truth vocabulary in the confirmation.**
  Durable lesson (x) surfaced at M30.2 (row button "Delete"
  → confirmation "Deactivate template?" reframes to truth).
  **M31.2 re-applied successfully** — row button "Restore"
  (short, familiar operator vocabulary) → confirmation
  title "Reactivate template?" (truth — is_active
  transitions False → True). Confirmation body reassures
  historical JEs are unaffected, matching the M30.2
  reassurance pattern. Elevates from "newly surfaced at
  M30.2" to "load-bearing across two milestones."
  **Consideration for future milestones:** row-action
  buttons should optimize for operator vocabulary
  convention (short + familiar); the confirmation is where
  the reframing to truth vocabulary happens (with any
  necessary reassurance about downstream consequences).
  Applies to any additive OR destructive lifecycle action.

- **(REINFORCED, sixth invocation) DoD exception path for
  infrastructure-only sub-increments.** M31.1 marks the
  **sixth invocation** of the M21.0 §5.f Option B path
  (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1). Pattern
  is now firmly established across six milestones. All six
  share the shape: backend substrate landing (schema-
  reserve, service relaxation, new endpoint + verbs, etc.)
  followed by a UI + Playwright increment that binds the
  substrate to a user-visible workflow. **Consideration for
  future milestones:** the exception path is a normal
  shape, not an anomaly — no streak counter for exception
  uses; the shape is expected whenever a milestone splits
  into backend-substrate + UI increments.

- **(REINFORCED, fifth link realized) Substrate-compound-
  value continuation across milestones.** M27.1 (gl-
  accounts) → M28.1 (template substrate) → M29 (variable-
  amount extension) → M30 (template CRUD closure) → **M31
  (template lifecycle closure)** is the fifth link in an
  intentional lineage. Each link cost measurably less than
  a green-field milestone because it composed on the prior
  substrate. M31 spent **zero new migrations** by reusing
  M28.1's `is_active` field + M30.1's `include_inactive`
  kwarg. **Consideration for future milestones:** the
  substrate-compound-value framing is now proven across
  **five** consecutive links. F&I chargeback substrate
  remains the natural sixth-link candidate if pilot
  evidence surfaces (M30 §9 gating unchanged).

- **(REINFORCED, load-bearing across two milestones)
  Additive-prop pattern for UI reuse.** Durable lesson (t)
  first surfaced at M29.2 (`NewJournalEntryDialog.
  lockedLines`), re-applied at M30.2
  (`JournalEntryTemplateDialog.mode`). **M31.2 did NOT
  need it** — Restore is a state-mutation, not a form —
  and instead used a co-located inline
  `TemplateRestoreConfirmDialog` per the M28.0
  duplicate-small-stable-domain-logic rule. Lesson (t)
  posture unchanged: it stays "available if a future need
  surfaces"; M31.2's not-invoking-it is itself a signal
  that the M28.0 rule remains healthy as a first-order
  choice.

- **(REINFORCED, load-bearing on subsequent milestone
  planning) Sweep the full acceptance suite when a UI
  element's semantic shape changes.** Durable lesson (v)
  surfaced at SESSION_200 §0.a (M29 CI regression). M31.2
  **explicitly re-used the M30.2 test-id patterns**
  (`tmpl-restore-trigger-<pk>` mirrors `tmpl-delete-
  trigger-<pk>` mirrors `template-instantiate-<pk>`);
  `template-row-inactive-<pk>` mirrors `template-row-<pk>`.
  Pattern consistency means any future selector-shape
  change would be easy to detect + sweep. First M31 CI run
  will validate this at M31 push (pending explicit user
  confirmation).

- **(NEW at M31.0) Lifecycle-integrity precheck governs
  the shape of L1-class fail-closed guards.** When a
  planning-open surface verification uncovers a partial-
  exposure situation (existing feature works safely today
  but a new UI surface would expose a fail-closed gap),
  the smallest fix is identified at the natural
  enforcement layer — which is not always the layer the
  new surface touches. M31.0 §4.1 traced the instantiate
  flow and found it purely client-side hydration: adding
  a server guard would have nothing to check because JE
  create never receives the template pk. The smallest
  fail-closed fix was therefore frontend-only (button
  disable + explanatory aria-label). Recording this as a
  design principle so future L-class guards can be
  evaluated on the same "smallest fix at the natural
  enforcement layer" axis rather than defaulting to
  "server-side check because that's more correct."
  **Consideration for future milestones:** whenever a
  planning-open verification uncovers a partial-exposure
  gap, trace the current flow before locking the guard
  shape; the natural enforcement layer may differ from
  the layer the new surface introduces.

## 6. Streak accounting at M31 close

- **Planning-time as-recommended streak: 10** (advanced
  from 9 at M30.2 close). Target selected as recommended
  after five-alternative comparison + lifecycle-integrity
  precheck performed at user direction. §0.a M31.0
  amendments (none) do not affect the streak. M31.1 +
  M31.2 both pure implementation of the M31.0 locked
  plan; streak unchanged at each. Historical run of 89
  across M10 → M23 preserved for the record.
- **Zero-drift permission-class streak: 33 consecutive
  milestones** (M10 → M31). M31.1 added a new endpoint
  reusing `_M131_PERMS` verbatim (no new permission
  class); M31.2 shipped no new endpoints. Advanced
  31 → 32 at M31.1 → 33 at M31.2.
- **Substrate-compound-value continuation: 5 links
  realized** (M27.1 → M28.1 → M29 → M30 → **M31**). M31
  spent zero new migrations by composing on M28.1's
  `is_active` field + M30.1's `include_inactive` kwarg.
- **DoD exception path invocations: 6** (M26 + M27.1 +
  M28.1 + M29.1 + M30.1 + M31.1). Pattern firmly
  established at six invocations.
- **Additive-prop pattern (durable lesson (t)):**
  unchanged posture — M31.2 did not invoke; used co-
  located inline dialog per M28.0 rule instead. Elevation
  posture from M30.2 close ("load-bearing across two
  milestones") preserved.
- **Mutation-surface asymmetry (durable lesson (w)):**
  first re-application at M31.1 completed successfully.
  Elevated from "surfaced at M30.2" to **"load-bearing
  across two milestones"** (M30.2 Delete + M31.1
  Restore).
- **Row-action truth-vocabulary asymmetry (durable
  lesson (x)):** first re-application at M31.2 completed
  successfully. Elevated from "surfaced at M30.2" to
  **"load-bearing across two milestones"** (M30.2
  "Delete"/"Deactivate" + M31.2 "Restore"/"Reactivate").
- **NEW durable principle (lifecycle-integrity precheck
  governs L1-class guard shape):** surfaced at M31.0.
  Awaits first re-application to elevate.

## 7. Baselines at M31 close

- Backend: **4,933 pass**, 1 skipped, 0 fail. (M30 close
  4,904 → +29 at M31.1; unchanged at M31.2.)
- Frontend Vitest: **319 pass** across 36 files. (M30
  close 300 → unchanged at M31.1 → +19 at M31.2.)
- Acceptance: **22 journeys** (M30 close 21 → unchanged
  at M31.1 → +1 at M31.2). Full suite fresh-DB run at
  M31.2 close: **28 passed / 0 failed / 32.6s**.
- Audit: **158 endpoints / 124 covered / 34 backend-only
  / 318 service verbs**. (M30 close 157/123/34/317 →
  M31.1 158/123/35/318 transitional → M31.2
  158/124/34/318 as the M31.1 Restore endpoint re-
  classifies from backend-only to covered.)
- DRF admin surface: **118** endpoints (M30.1 117 → +1
  at M31.1; unchanged at M31.2).
- Frontend operator routes: **20** (unchanged; M31.2
  attached Show-inactive toggle + inactive-row
  rendering + Restore button + Restore dialog to the
  existing JE list page, no new route).
- Permission classes: **7 actual** (unchanged — M31.1
  reused `_M131_PERMS`).
- Migrations: `0001`–`0050` (unchanged; no new migration
  at M31).
- Component + dialog shape: `TemplateRow` gained is_active-
  aware conditional rendering + explanatory aria-labels;
  new inline `TemplateRestoreConfirmDialog` co-located
  with `TemplateDeleteConfirmDialog` (no shared
  abstraction per M28.0 rule). New API wrapper
  `restoreJournalEntryTemplate`; extended list wrapper
  option `{ includeInactive?: boolean }`.
- `manage.py check` + `makemigrations --check --dry-run`
  clean at M31.1 and M31.2 close.
- `tsc --noEmit` clean across frontend + acceptance
  workspaces at M31.1 and M31.2 close.
- `git grep "Restore UX ships in a future milestone"
  frontend/ acceptance/`: two hits — both in the D10
  guard test's `.not.toContain(...)` assertion + comment.
  Shipped code: zero hits (D10 fulfilled).

## 8. Corrections (post-close)

None yet.

## 9. Evidence-based candidates for M32

**Elevated (highest recommendation strength for M32.0):**

- **NEW C — F&I chargeback substrate.** Fifth-link
  candidate elevated at M30 §9 and M31 close; still gated
  on pilot evidence per §9. Would continue the
  substrate-compound-value lineage into a **sixth link**
  by reusing M27.1 gl-accounts substrate + M28.1 template
  substrate. **Standing question:** with the substrate-
  compound-value framing now proven across FIVE
  consecutive links (M27.1 → M28.1 → M29 → M30 → M31),
  the sixth link is the natural next move under the
  compound-value lens if pilot evidence surfaces.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30/M31 deferral, unchanged). Requires
  SESSION-189-§3-style tracing at M32.0 open. Blast
  radius unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28/M29/M30/M31 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M31.2 close
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow` trial-balance snapshot).
  Compound CI-stability value grows as the suite grows
  (now 22 journeys).

**Gated (unchanged from M29+M30+M31 close):**

- T (real tester feedback); U (hosted-demo substrate);
  L (first-live-pilot staging); M (multi-operator support
  — breaks the M10 → M31 zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M31 §3, M30 §3, M29 §3, M28 §3, M27 §3,
M25 §4 (all valid for later re-entry):**

- Hard-delete escape hatch on templates; bulk delete/
  restore/edit on templates; template mutation audit
  history; optimistic concurrency control on Restore/
  Deactivate; template mutation history / diff viewer;
  auto-refresh / websocket invalidation of stale-tab
  template list (R1 accepted decoupling consequence);
  persistent Show-inactive toggle state; bulk lifecycle
  actions across templates list; all prior M30 §3 +
  M29 §3 + M28 §3 + M27 §3 + M25 §4 deferrals.

**Standing question for M32:** the reversible template
lifecycle is now complete. Two natural next moves under
the primary operational-coverage lens: (a) **F&I
chargeback substrate** — sixth substrate-compound-value
link if pilot evidence surfaces; would extend the same
lineage-completion arc that M27.1 → M31 has proven; (b)
**a different domain surface** — the M27.1 → M31 arc has
absorbed five consecutive planning-time selections in the
accounting/templates domain, and the operator-coverage
lens may benefit from breadth after depth. Fresh direct-
operator gaps to survey at M32.0 open include the 34
backend-only audit endpoints (deal writeups #112–114,
vendor detail #43, photo reorder #65, F&I domain surface
#89–101 excluding chargeback which is already
elevated). Neither path is forced by evidence at M31
close.
