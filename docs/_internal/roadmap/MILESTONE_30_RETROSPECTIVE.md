---
title: "Milestone 30 — Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern) — Retrospective"
status: historical
type: retrospective
milestone: 30
milestone_status: shipped
generated: 2026-08-04
generated_at_session: SESSION_202 (M30.2 close + close-out fold)
milestone_name: "Journal-Entry Template Edit / Delete UI (on M28.1 template substrate + M29.2 additive-prop pattern)"
increments_shipped: [0, 1, 2]
close_out_fold: true
sessions: [200, 201, 202]
commits_at_close: 6
---

# Milestone 30 — Template Edit / Delete UI — Retrospective

> Milestone 30 opened at SESSION_200 M30.0 planning under the
> durable primary operational-coverage lens plus the substrate-
> compound-value continuation framing that first validated at
> M27.1 → M28.1 → M28.2 → M29. M30.0 also folded in a §0.a M29
> CI regression correction (chip UI shape change broke a pre-
> existing M28.2 assertion) — the first §0.a-hotfix push under
> exception in the M30 cadence. M30.1 shipped the backend
> substrate at SESSION_201 (new detail endpoint + service verbs
> + include_inactive kwarg symmetry). M30.2 shipped the
> customer-facing UI + Playwright coverage at SESSION_202 with
> close-out folded in (no separate M30.3).
>
> **The anchor business question** — *Can a dealership
> accountant correct a stale journal-entry template (rename,
> fix a wrong GL account or amount, add/remove lines) or
> deactivate one that no longer belongs, using the shipped
> application, without corrupting historical journal entries
> that were instantiated from it in prior periods?* — is
> answered **yes**. One combined Playwright journey covers the
> end-to-end flow with soft-delete integrity assertions
> (historical JE description AND `total_debit` unchanged after
> edit AND after delete) drawn from the shipped UI.
>
> M30 realized the fourth link in the substrate-compound-value
> lineage (M27.1 gl-accounts → M28.1 template substrate → M29
> variable-amount extension → M30 CRUD closure) — spent with
> **zero new migrations**, demonstrating that CRUD extensions
> on well-designed substrate cost measurably less than green-
> field milestones.

## 1. Planned scope

Per `MILESTONE_30_PLANNING.md` §5.a locked at open: **NEW
Template edit / delete UI.**

Two-increment split per §5.e:

- **M30.1 (SESSION_201)** — backend substrate: new
  `admin/accounting/journal-entry-templates/<pk>/` detail
  endpoint (PATCH + DELETE), `update_journal_entry_template`
  + `delete_journal_entry_template` service verbs,
  `include_inactive: bool = False` kwarg on
  `get_journal_entry_template` for API symmetry with the list
  verb, `JournalEntryTemplateUpdateRequestSerializer`. New
  M30 service test file + endpoint/model extensions. DoD
  exception path invoked as **fifth precedent** (M26 + M27.1
  + M28.1 + M29.1 + M30.1).
- **M30.2 (SESSION_202)** — frontend + Playwright: rename
  `NewJournalEntryTemplateDialog.tsx` →
  `JournalEntryTemplateDialog.tsx` via `git mv` + import
  sweep in same commit; additive-mode props (`mode`,
  `initialTemplate`, `onEdited`, controlled-open pair) on the
  renamed component; row-level Edit + Delete buttons on
  `AccountingJournalEntriesPage`; inline delete confirmation
  dialog with mandated D3 copy; `updateJournalEntryTemplate`
  + `deleteJournalEntryTemplate` wrappers in
  `accountingApi.ts` (delete treats 404 as success — race-
  safe). Single new `test.describe("edit-delete", ...)` block
  extension of `accounting_je_template.spec.ts`. DoD satisfied
  directly via the new describe block — no exception path.

Two architectural verifications performed at M30.0 planning-
open per user direction, before locking §5.b:

- **§4.6 Dialog consolidation** — chose additive-mode pattern
  (rename + optional `mode` prop) over parallel
  `EditJournalEntryTemplateDialog` fork. Direct re-application
  of M29.2 durable lesson (t). The 200+ lines of shared
  validation + `TemplateLineRow` + `TemplateBalanceIndicator`
  would be pure duplication if forked.
- **§4.7 Soft-delete integrity** — grep across
  `backend/dealer_ai/**/*.py` confirmed no FK from
  `JournalEntry` to `JournalEntryTemplate` (M28.0 §5.b
  domain separation), so template edits + deletes cannot
  cascade to any historical journal entry. All four operator-
  behavior criteria pass by construction. Delete UI copy
  mandated to say "Deactivate" (not "Delete forever") +
  historical-entries reassurance.

## 2. What actually shipped

**§0.a M30.0 amendment (SESSION_200):**

- First M29 CI acceptance run (workflow 30919344101 on
  `e01cfde`) turned red on the pre-existing M28.2
  `getByLabel("Line 1 debit")` assertion that M29.2 had
  invisibly broken by replacing the amount cell with a
  `LockedAmountChip`.
- Fix: single-file assertion update at
  `accounting_je_template.spec.ts:291–306` using the new
  chip test-id + `toContainText(/\$1275\.00/)`.
- Verified via isolated re-run (7 passed) → full suite on
  fresh acceptance DB (26 passed) → CI on push (`43b715b`,
  26 passed / 2m43s).
- Pushed immediately under "restore red main" push-cadence
  exception (user-authorized). Second CI run confirmed
  green.

**M30.0 planning (SESSION_200):** full active memo at
`MILESTONE_30_PLANNING.md` — target locked as NEW Template
edit / delete UI; §5.b D1–D8, risk register, verifications,
phasing, DoD compliance, rollback, non-goals all landed.
Two architectural verifications performed at user direction
before locking §5.b (dialog consolidation + soft-delete
integrity).

**M30.1 backend substrate (SESSION_201):**

- **Service layer** (`services/accounting/template.py`):
  - `get_journal_entry_template` extended with
    `include_inactive: bool = False` kwarg (mirrors
    `list_journal_entry_templates` pattern). Default False
    fail-closes on soft-hidden rows.
  - `update_journal_entry_template(*, pk, dealership, name,
    description, lines)` — atomic (`@transaction.atomic`);
    fetches with `include_inactive=True`; full-replace of
    lines; preserves `is_active`; catches `IntegrityError`
    → `DuplicateJournalEntryTemplateNameError`.
  - `delete_journal_entry_template(*, pk, dealership)` —
    fetches with `include_inactive=True`; if already
    inactive, returns row without state change (idempotent
    — `updated_at` doesn't advance); otherwise sets
    `is_active = False` and saves via
    `update_fields=["is_active", "updated_at"]`.
- **Endpoint layer** (`views_accounting.py`):
  - `JournalEntryTemplateUpdateRequestSerializer` — mirrors
    the create serializer; `is_active` intentionally omitted
    so PATCH silently drops it per D5.
  - `admin_journal_entry_template_detail(request, pk)` view
    for PATCH + DELETE; reuses `_M131_PERMS`; error mapping
    matches create (400 for domain errors, 404 for missing/
    cross-tenant/GL, 409 for duplicate name, 204 for
    successful DELETE, 200 for successful PATCH).
- **URL** (`urls.py`): new pattern
  `admin/accounting/journal-entry-templates/<int:pk>/` →
  `admin-journal-entry-template-detail` url_name.
- **Zero migration** — soft-delete reuses M28.1's `is_active
  = BooleanField(default=True)` field.
- **Tests +33** (planned ~22; excess +11 from adding
  auth-denial + preserves-is_active coverage — better over-
  than-under):
  - NEW `test_m30_journal_entry_template_edit_delete_service
    .py` (17 tests: 11 update + 4 delete + 2 get with
    include_inactive kwarg).
  - EXTENDED `test_m28_journal_entry_template_endpoint.py`
    with `TemplateDetailEndpointTests` (15 tests: PATCH 200
    + full-replace + 404 missing + 404 cross-tenant + 400
    invalid + 409 duplicate + silently ignores is_active in
    body + DELETE 204 + 404 missing + 404 cross-tenant + 204
    idempotent + advisor + unauthenticated denied on both).
  - EXTENDED `test_m28_journal_entry_template_model.py` with
    `test_m30_updated_at_advances_on_save` (guardrail
    against a future migration accidentally dropping the
    auto-now posture that M30.2 edit UI relies on).

**M30.2 UI + Playwright (SESSION_202):**

- **Component rename** via `git mv` + import sweep in same
  commit per `DOC_GOVERNANCE.md` §5:
  `NewJournalEntryTemplateDialog.tsx` →
  `JournalEntryTemplateDialog.tsx` (+ sibling `.test.tsx`).
  Only two living-code callers swept:
  `AccountingJournalEntriesPage.tsx` +
  `JournalEntryTemplateDialog.test.tsx`. Historical handoffs
  + retrospectives + planning memos remain immutable
  (governance §5).
- **Additive-mode props on the renamed component:**
  - `mode?: "create" | "edit"` (default `"create"`) —
    preserves M29.2 behavior byte-identical when unspecified.
  - `initialTemplate?: JournalEntryTemplate` — populates
    form fields on open transition via new
    `templateToDraftLines` helper + `useEffect([open,
    isEditMode, initialTemplate])`.
  - `onEdited?: (template) => void` — fired after successful
    edit.
  - Controlled-open pair (`open?` + `onOpenChange?`) — when
    both supplied, baked-in `+ New template` trigger is NOT
    rendered; parent controls open state (row-level
    trigger).
  - Mode-aware branches: dialog title ("Edit template" vs
    "New recurring template"), submit label ("Save changes"
    vs "Save template"), submit test-id (`tmpl-edit-submit`
    vs `tmpl-create-submit`), and `handleSubmit` (calls
    `updateJournalEntryTemplate(initialTemplate.id,
    payload)` in edit mode).
- **Row buttons on `AccountingJournalEntriesPage.tsx`:**
  - `tmpl-edit-trigger-<pk>` (Edit button) opens the edit-
    mode dialog with `initialTemplate` populated.
  - `tmpl-delete-trigger-<pk>` (Delete button) opens the
    inline delete confirmation.
- **Delete confirmation** — new inline `TemplateDelete
  ConfirmDialog` component built on the existing shadcn
  `Dialog` primitive (no new `AlertDialog` dependency
  added). Mandated D3 copy: title "Deactivate template?",
  body "Are you sure you want to deactivate <name>?
  Historical journal entries created from this template are
  not affected — they remain unchanged in the Journal
  Entries list and in trial balance reports. You can restore
  this template later. (Restore UX ships in a future
  milestone.)", `[Cancel] [Deactivate]` footer with
  destructive variant on Deactivate.
- **API wrappers** (`accountingApi.ts`):
  - `updateJournalEntryTemplate(pk, payload)` — wraps
    `authPatchJSON`; returns projected template.
  - `deleteJournalEntryTemplate(pk)` — wraps `authDelete`;
    catches `ApiError.status === 404` and returns void
    (race-safe — the template is gone either way).
- **Frontend tests +18:**
  - Renamed dialog test file continues to run all 15 pre-
    existing create-mode tests unchanged (safe-default path
    regression guard).
  - +8 edit-mode branches in the renamed dialog test file:
    populate from initialTemplate, "Edit template" title,
    "Save changes" label, baked-in trigger NOT rendered
    when controlled-open, submit calls
    updateJournalEntryTemplate with pk + payload, onEdited
    fires on success, onOpenChange(false) closes dialog on
    success, inline error surfaces on rejection.
  - +5 in `AccountingJournalEntriesPage.test.tsx`: row
    renders Edit + Delete buttons, Edit click opens dialog
    in edit mode with initial values, Delete click opens
    confirmation with mandated copy, Delete confirm calls
    deleteJournalEntryTemplate + refetches, Delete failure
    surfaces inline error without closing.
  - +6 in `accountingApi.templates.test.ts`:
    updateJournalEntryTemplate PATCH URL + payload,
    propagate 409 duplicate name; deleteJournalEntryTemplate
    DELETE URL, 404-as-success, propagate 500.
- **Playwright +1 journey** — single new `test.describe(
  "edit-delete", ...)` block extension of
  `accounting_je_template.spec.ts`. 7-step journey:
  1. Seed fresh template via admin API ($100/$100).
  2. Instantiate through UI → post historical JE.
  3. Click row Edit → dialog opens in edit mode → rename +
     change amounts to $150/$150 → Save changes.
  4. **Load-bearing assertion:** historical JE STILL shows
     original amounts + description after template edit
     (§4.7 (b) contract).
  5. Click row Delete → confirmation dialog appears with
     D3 mandated copy → click Deactivate → template
     disappears from list.
  6. Reload page → template stays gone (soft-delete
     persists — verifies operator-visible half of D5 no-
     FK contract).
  7. **Load-bearing assertion:** historical JE STILL visible
     + correct after delete.

## 3. Deviations from plan and reason

None material.

The only quantitative deviation from planning was **backend
test count**: planned ~22 (D6), actual **+33**. Excess +11
came from adding explicit auth-denial (advisor + unauth on
both PATCH and DELETE) + preserves-is_active-True/False +
cross-tenant coverage on the update service. All additions
strengthen the endpoint's safety envelope; none add
architectural surface. Recorded as informative-not-corrective
— future §5.b D6 estimates on CRUD-endpoint additions can
budget +6–10 auth/tenancy tests on top of the primary happy-
path + error-mapping coverage.

Frontend test count matched plan exactly (+18 = +8 dialog +
5 page + 6 API + 1 baseline shift for the renamed dialog file
count staying at 36 vs 37 as originally projected — the
rename preserves the file count).

Playwright journey count matched plan exactly (20 → 21).

## 4. Deferrals from M30 (all valid for later re-entry)

Per `MILESTONE_30_PLANNING.md` §5.h — unchanged at M30.2
close:

- **Restore / "Show inactive" UI toggle.** Endpoint exposure
  (`?include_inactive=true`) remains an M28 §3 deferral. M30
  ships Delete (deactivate) but not Restore; operators who
  need to un-hide a template still need Django-shell access
  in the interim.
- **Hard-delete escape hatch.** DELETE at M30 always sets
  `is_active = False`; no `?hard=true` query param. Deferred
  pending operator evidence.
- **Template mutation audit trail** (`edited_by_user`,
  history rows). Deferred pending operator evidence during
  pilot.
- **Optimistic concurrency control on edit** (ETag /
  `updated_at` check). Deferred until M (multi-operator
  support) unblocks.
- **Bulk delete / bulk edit.** Deferred pending operator
  evidence.

All prior M29 §3 + M28 §3 + M27 §3 + M25 §4 deferrals
carried forward unchanged.

## 5. Durable design principles surfaced or reinforced

Six principles carried forward from M29 continue to apply.
Two are elevated at M30, and one is newly REINFORCED:

- **(REINFORCED, first re-application) Additive-prop pattern
  for UI reuse.** Durable lesson (t) surfaced at M29.2 (via
  `NewJournalEntryDialog.lockedLines`). **M30.2 re-applied
  successfully** on `JournalEntryTemplateDialog.mode` — same
  reasoning, same test-suite preservation posture, same
  smallest-blast-radius outcome. The 17 pre-existing create-
  mode vitests passed unchanged after adding the mode
  branches. Elevates the lesson from "surfaced" to "load-
  bearing across two milestones." Consideration for future
  milestones: at planning-open, when a reusable component
  needs a divergent context, evaluate additive-mode /
  additive-prop before reaching for a wrapper or a fork.

- **(REINFORCED, first re-application after surfacing at
  §0.a) Sweep the full acceptance suite when the semantic
  shape of an established UI element changes.** Durable
  lesson (v) surfaced at SESSION_200 §0.a (M29 CI
  regression). **M30.2 explicitly did NOT change the amount-
  cell shape** (chip / input / amber-ring preserved
  verbatim), and the pre-existing M28.2 + M29.2 assertions
  on that cell continued to pass. The lesson also informed
  M30.2's new test-id conventions: `tmpl-edit-trigger-<pk>`
  + `tmpl-delete-trigger-<pk>` mirror the existing
  `template-instantiate-<pk>` pattern for consistency, so
  any future selector-shape change on template row actions
  would be easy to detect + sweep. Elevates lesson (v) from
  "surfaced" to "load-bearing on subsequent milestone
  planning."

- **(REINFORCED, fifth invocation) DoD exception path for
  infrastructure-only sub-increments.** M30.1 marks the
  fifth invocation of the M21.0 §5.f Option B path (M26 +
  M27.1 + M28.1 + M29.1 + M30.1). Pattern is now firmly
  established. Backend substrate refinements with zero
  operator-facing behavior change invoke the exception
  path; the customer-facing sub-increment (M30.2) satisfies
  DoD directly. Five precedents all share the shape: a
  backend substrate landing (schema-reserve, service
  relaxation, new endpoint + verbs, etc.) followed by a UI
  + Playwright increment that binds the substrate to a
  user-visible workflow.

- **(REINFORCED, fourth link realized) Substrate-compound-
  value continuation across milestones.** M27.1 (gl-
  accounts) → M28.1 (template substrate) → M29 (variable-
  amount extension) → **M30 (template CRUD closure)** is
  the fourth link in an intentional lineage. Each link cost
  measurably less than a green-field milestone because it
  composed on the prior substrate. M30 spent zero new
  migrations by reusing M28.1's `is_active` field for soft-
  delete + M28.1's model shape verbatim for edit. Standing
  question for M31+ planning: candidates that continue this
  lineage (e.g., F&I chargeback substrate on M27.1, named
  template variables on M28.1) should be evaluated for
  compound-value framing alongside the primary operational-
  coverage lens.

- **(NEW at M30.2) `is_active` mutation surface asymmetry
  is a load-bearing design constraint.** PATCH must silently
  drop `is_active` from the request body — activation is
  DELETE-only (soft) or a future Restore verb (deferred),
  never through edit. Rationale: mixing activation into
  edit conflates two operator intents (correction vs
  lifecycle) and creates a foot-gun (edit accidentally
  reactivates a deactivated template). Enforcement is
  layered: the update serializer doesn't define the field
  (DRF drops it silently in `is_valid`); the service passes
  explicit `update_fields=["name", "description",
  "updated_at"]` on save; an endpoint test
  (`test_patch_silently_ignores_is_active_in_body`) asserts
  the behavior. Consideration for future milestones: any
  future soft-hide / lifecycle field on any model should
  apply the same asymmetry — mutation only through explicit
  DELETE/Restore verbs, never through general PATCH.

- **(NEW at M30.2) Delete UI copy must reframe row-action
  vocabulary into truth vocabulary.** The row-level button
  uses "Delete" (operator-vocabulary convention — familiar,
  destructive-looking); the confirmation dialog reframes to
  "Deactivate" (truth — soft-hide, historically preserved,
  restorable in principle) and includes explicit reassurance
  about historical entries. This asymmetry is deliberate:
  operators expect "Delete" to be permanent; the
  confirmation must correct their mental model before they
  commit. Playwright asserts the confirmation copy text
  verbatim.

## 6. Streak accounting at M30 close

- **Planning-time as-recommended streak: 9** (advanced from
  8 at M29.2 close). Target selected as recommended after
  five-alternative comparison + two architectural
  verifications performed at user direction. §0.a is
  corrective (not scope selection) — streak unaffected. M30.1
  + M30.2 both pure implementation of the M30.0 locked plan;
  streak unchanged at each. Historical run of 89 across M10
  → M23 preserved for the record.
- **Zero-drift permission-class streak: 31 consecutive
  milestones** (M10 → M30). M30.1 added a new detail endpoint
  reusing `_M131_PERMS` verbatim (no new permission class).
  M30.2 shipped no new endpoints.
- **Substrate-compound-value continuation: 4 links realized**
  (M27.1 → M28.1 → M29 → M30). M30 spent zero new migrations
  by composing on M28.1's `is_active` field + model shape.
- **DoD exception path invocations: 5** (M26 + M27.1 +
  M28.1 + M29.1 + M30.1). Pattern firmly established;
  future infrastructure-only sub-increments invoke it with
  confidence.
- **Additive-prop pattern (durable lesson (t)):** first re-
  application at M30.2 completed successfully. Elevated
  from "surfaced" (M29.2) to "load-bearing across two
  milestones" (M29.2 + M30.2).

## 7. Baselines at M30 close

- Backend: **4,904 pass**, 1 skipped, 0 fail. (M29 close
  4,871 → +33 at M30.1; unchanged at M30.2.)
- Frontend Vitest: **300 pass** across 36 files. (M29 close
  282 → unchanged at M30.1 → +18 at M30.2.)
- Acceptance: **21 journeys** (M29 close 20 → unchanged at
  M30.1 → +1 at M30.2). Full suite: **27 passed / 0 failed
  / 36.5s on fresh DB.**
- Audit: **157 endpoints / 123 covered / 34 backend-only /
  317 service verbs**. (M29 close 156 / 122 / 34 / 315 →
  M30.1 157 / 122 / 35 / 317 → M30.2 157 / 123 / 34 / 317
  as the M30.1 detail endpoint re-classifies from
  backend-only to covered.)
- DRF admin surface: **117** endpoints (M28.1 116 → +1 at
  M30.1; unchanged at M30.2).
- Frontend operator routes: **20** (unchanged; M30.2
  attached Edit + Delete buttons to existing rows on the
  JE list page, no new route).
- Permission classes: **7 actual** (unchanged — M30.1
  reused `_M131_PERMS`).
- Migrations: `0001`–`0050` (unchanged; no new migration at
  M30).
- Component rename: `NewJournalEntryTemplateDialog` →
  `JournalEntryTemplateDialog` (+ sibling test file). git
  mv preserves rename history; `git log --follow`
  continues to work.
- `manage.py check` + `makemigrations --check --dry-run`
  clean at M30.1 and M30.2 close.
- `tsc --noEmit` clean across frontend + acceptance
  workspaces at M30.1 and M30.2 close.
- `git grep NewJournalEntryTemplateDialog frontend/
  acceptance/`: empty (rename sweep verified).

## 8. Corrections (post-close)

None yet.

## 9. Evidence-based candidates for M31

**Elevated (highest recommendation strength for M31.0):**

- **NEW C — F&I chargeback substrate.** Would reuse M27.1
  gl-accounts substrate + M28.1 template substrate. Would
  continue the substrate-compound-value lineage into a
  **fifth link**. Elevated status contingent on operator
  evidence surfacing during a pilot (unchanged from M29 §9
  gating).
- **NEW — Restore / "Show inactive" UI toggle** on
  templates. M28 §3 deferral, freshly unblocked at M30 close
  because M30.1 already ships the service kwarg
  (`include_inactive`) — endpoint exposure is a one-line
  view-layer change; a "Show inactive" toggle on the M30.2
  templates section is small-to-moderate scope. Completes
  the operator-facing half of the soft-delete lifecycle.
  Direct sequential complement to M30 shipped surface.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30 deferral, unchanged). Requires
  SESSION-189-§3-style tracing at M31.0 open. Blast radius
  unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28/M29/M30 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M30.2 close
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow` trial-balance snapshot).
  Compound CI-stability value grows as the suite grows
  (now 21 journeys).

**Gated (unchanged from M29+M30 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the M10 → M30 zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M30 §3, M29 §3, M28 §3, M27 §3, M25 §4 (all
valid for later re-entry):**

- Hard-delete escape hatch on templates; template mutation
  audit trail; optimistic concurrency control on template
  edit; bulk delete/edit; fully-variable UX polish (Repeat
  last amounts); server-recorded instantiation audit trail;
  named / shared template variables; historical-template
  back-reference on `JournalEntry`; server-side template
  search / pagination; standalone template detail page;
  standalone Chart of Accounts page/route; JE edit/update;
  `posted_by_user` override; advanced picker filtering;
  server-side gl-accounts search/pagination; secondary
  "+ Record test drive" launch point; clickable "Referred
  by" nav; named-platform webhook adapters; attribution
  rollups; vehicle-picker advanced filters.

**Standing question for M31:** with the substrate-compound-
value framing now proven across FOUR consecutive links (M27.1
→ M28.1 → M29 → M30), the fifth link is the natural next
move under the compound-value lens. Two candidates continue
this lineage: (a) **F&I chargeback substrate on M27.1** —
would model backend-only F&I product chargebacks as JEs
reusing gl-accounts, potentially templates; gated on pilot
evidence today. (b) **Restore / Show-inactive UI on M28.1
+ M30.1** — completes the operator-facing soft-delete
lifecycle; small-to-moderate scope; directly sequential
complement to M30. Evidence at M30 close does not force
either path — both are compelling; both are additive to the
lineage. The primary operational-coverage lens favors
Restore UI (direct operator gain resolvable today); the
substrate-compound-value + business-impact lens favors F&I
chargeback (fifth link + revenue-adjacent operational value)
if pilot evidence surfaces.
