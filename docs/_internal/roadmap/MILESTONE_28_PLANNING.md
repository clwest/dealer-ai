---
title: "Milestone 28 — Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_194 (skeleton + expansion + all §5 locks)
milestone: 28
milestone_name: "Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_27_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_27_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7β
  - backend/dealer_ai/models.py (JournalEntry, JournalEntryLine, GLAccount)
  - backend/dealer_ai/views_accounting.py (M13.1 create + M27.1 gl-accounts)
  - backend/dealer_ai/services/accounting.py (post_journal_entry, JournalLineInput)
  - frontend/src/components/accounting/GLAccountPicker.tsx (M27.2)
  - frontend/src/components/accounting/NewJournalEntryDialog.tsx (M27.2)
  - frontend/src/lib/accountingApi.ts (M27.1 + M27.2 wrappers)
  - frontend/src/pages/AccountingJournalEntriesPage.tsx (M27.2 host page)
  - acceptance/journeys/office/accounting_je_create.spec.ts (M27.2 journey)
---

# Milestone 28 — Recurring Journal Templates (on M27.1 shared GLAccount substrate)

> **Active planning memo.** Drafted + expanded + all §5 locks
> at SESSION_194 M28.0 open.
>
> **§5.a locked at open** as **A — Recurring journal
> templates**, under the *primary operational-coverage lens*
> that has governed §5.a selection since M22 close (durable).
> Candidate A is the first M28-eligible option that is
> directly operator-facing among the elevated set (A / O2 /
> O3 / H); it also demonstrates M27.1's "shared accounting
> infrastructure" compound-value framing on real operator
> workflow — the M27.1 gl-accounts substrate exists but has
> one consumer (the M27.2 dialog); templates make it two,
> validating the substrate framing early rather than letting
> it sit unproven.
>
> **The anchor business question** — *Can a dealership
> accountant persist a recurring journal-entry recipe once
> and instantiate it monthly through the shipped application?*
> — governs every M28 scope decision.
>
> **Two architectural verifications performed at M28.0 open**
> (per user direction, before locking any §5 decisions):
>
> 1. **Model duplication check.** `JournalEntryTemplateLine`
>    was compared field-by-field against the shipped
>    `JournalEntryLine`. Four sharing options were
>    considered — abstract base class (retrofit inheritance
>    on shipped M13.1 model), fuse into `JournalEntry` with
>    `is_template` flag, dual-column amount mirroring, and
>    a small cross-tenant guard helper. Only the last is
>    adopted. Rejection rationale in §5.b commentary block:
>    templates are *recipes* (editable, amount optionally
>    deferred, no `posted_at`, no reversal semantics); JEs
>    are *postings* (immutable per M13.1, `posted_at`
>    required, reversal-chain via `reverses` FK). Fusing
>    destroys separation of concerns and forces
>    `WHERE is_template = FALSE` filters on every
>    trial-balance / JE-list / audit query. Abstract base
>    class shares only three fields for negative ROI (4,813
>    tests at risk for cosmetic dedup). The cross-tenant
>    guard was evaluated for extraction as a shared helper
>    and **deliberately kept duplicated** at M28: the two
>    `clean()` methods are ~5 lines each, are unlikely to
>    diverge (they enforce the same invariant against
>    different parents), and letting each model own its own
>    invariant preserves local clarity. Extraction is
>    reserved for the point where evidence of divergence or
>    a genuine maintenance burden appears — DRY for its own
>    sake is not that evidence.
>
> 2. **Variable-amount forward-compat check.** The proposed
>    `side` + nullable `amount` design was tested against
>    four future workflows (monthly rent, depreciation,
>    utilities, payroll accruals). All four instantiate
>    correctly without a schema migration — M28's serializer
>    requires non-null `amount`, and a future variable-amount
>    milestone need only relax that constraint and add an
>    instantiation-prompt UI. Dual-column `debit`/`credit`
>    encoding cannot express "side known, amount deferred"
>    without adding a side column, so adding `side` now
>    avoids a future migration + backfill. Named-variable
>    shared-across-lines feature is out of scope AND
>    intentionally not schema-reserved (its future migration
>    is a pure additive `TemplateVariable` table — cheap).
>
> **M28 is deliberately scoped as two implementation
> increments + close-out fold** (mirrors M27.1 / M27.2
> cadence). M28.1 ships the backend substrate: new
> `JournalEntryTemplate` + `JournalEntryTemplateLine`
> models, new `create_journal_entry_template` +
> `list_journal_entry_templates` service verbs, two new
> endpoints (`POST` + `GET
> admin/accounting/journal-entry-templates/`), and the
> `fetchJournalEntryTemplates` + `createJournalEntryTemplate`
> frontend wrappers. DoD exception path invoked per
> §5.g (no operator surface at M28.1). M28.2 ships the
> "Recurring templates" collapsible section on the existing
> `AccountingJournalEntriesPage`, the
> `NewJournalEntryTemplateDialog` component, the
> pre-populate wiring on the existing
> `NewJournalEntryDialog`, and the new
> `accounting_je_template.spec.ts` Playwright peer spec
> with two test cases (create-template + instantiate-
> template) plus a small extension to the existing
> `accounting_je_create.spec.ts` (blank-path regression
> guard).
>
> **Coverage arithmetic at M28 close:** backend endpoints
> **155 → 157** (two new template endpoints). Both new
> rows land `defer-candidate-O2` at M28.1 close (endpoints
> exist; wrappers exist but not yet consumed by non-test
> frontend). Both flip → `covered` at M28.2 close. Post-
> M28.2 target: **157 total / 123 covered / 34 backend-
> only** (121 → 123).
>
> **Streak posture:** zero-drift permission-class streak
> preserved at **27 → 28** consecutive milestones (M10 →
> M28) — both new surfaces reuse `_M131_PERMS` per the
> accounting module's existing pattern; no permission
> classes evolve. Planning-time as-recommended streak
> enters M28 at **6** and is intended to reach **7** at
> M28.0 close (assuming the user confirms the recommended
> target).
>
> Anchor cross-refs:
> - `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md` §9 —
>   records recurring journal templates elevated as the
>   leading M28 §5.a candidate.
> - `docs/CAPABILITY_MATRIX.md` §7β — M27 shipped surface
>   (JE creation UI + gl-accounts substrate); the 121 / 155
>   baseline M28 opens on.
> - `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` — the
>   audit rows that flip at M28 close (two new rows in the
>   `admin/accounting/journal-entry-templates/` group).
> - Memory record
>   `feedback_verify_fk_discoverability_before_lock.md` —
>   verified at M28.0 §7 (all M28 FKs land inside existing
>   discovery surfaces).
> - Memory record `feedback_one_workflow_over_two_overlapping.md`
>   — the rule that shaped the "+ New journal entry"
>   vs "Instantiate" branch distinction (not overlapping —
>   distinct problems, row-level vs header-level actions).
> - Memory record `feedback_preserve_existing_code.md` —
>   the rule that governed attaching the templates section
>   to the existing `AccountingJournalEntriesPage` rather
>   than a new route AND rejecting fusion of template-line
>   into shipped `JournalEntryLine`.
> - Memory record `feedback_audit_correctness_as_supporting_infra.md`
>   — durable rule permitting audit-correctness gains as
>   bounded sub-scope; noted but not invoked at M28 (M28
>   is direct operator-facing, no audit-tooling sub-scope).

## Guiding question (durable, per M22 close)

**Which candidate most increases operational coverage for
a dealership employee?**

**M28 answers directly under the primary lens.**
Recurring templates deliver bounded operator gain to
accounting staff: after a template is persisted once, the
repeated monthly / weekly posting workflow collapses from
"open dialog → pick account → enter amount → pick account
→ enter amount → …" to "open templates section → click
Instantiate → confirm → submit". Small user population ×
high frequency = real bounded gain — the exact shape the
primary lens rewards. Additionally, M28 demonstrates the
M27.1 substrate compound-value framing (two operator
consumers of the shared gl-accounts endpoint instead of
one).

## Preserve the M20–M27 operational contract (durable)

- **Zero-drift permission-class streak preserved.** M28
  reuses `_M131_PERMS` for both new endpoints (template
  create + list are same tenant-admin trust boundary as
  the M13.1 JE create / M27.1 gl-accounts). Intended
  posture at M28 close: **28 consecutive milestones
  (M10 → M28)**.
- **17-stage scrub stack unchanged.** M28 does not touch
  the LLM path.
- **Existing accounting response envelopes preserved.**
  Both new endpoints follow the `cost_posting_failures` /
  `gl_accounts` precedent (unpaginated collection wrapped
  as `{<resource_plural>: {<items_key>: [...]}}`; retrieval
  wrapped as `{<resource_singular>: {...}}`). No new
  envelope shapes.
- **No new frontend operator routes.** Templates attach
  to the existing `/dealer-ai-accounting/journal-entries`
  route as a collapsible section beneath the JE list card.
  Frontend operator routes stay at **20**.
- **Trial Balance unchanged.** No modification.
- **Append-only ledger discipline preserved.** M28 adds
  a *recipe* concept (mutable, editable in principle);
  JEs themselves remain immutable-once-posted. Templates
  are separate models — they never touch the ledger's
  immutability contract.
- **Shipped `JournalEntryLine` model unchanged.** Per
  M28.0 §5.b architectural verification, template-line
  data lives in a *new* model (`JournalEntryTemplateLine`)
  rather than being fused via inheritance or a shared
  flag. The M13.1 posting model is stable, tested, and
  protected by the preserve-existing-code rule.

## Guiding principle (substrate-compound-value + normalization-over-coupling)

Two rules govern M28's shape:

1. **Substrate compound value (M27.1 continuation).**
   M27.1 shipped `admin/accounting/gl-accounts/` as
   *shared accounting infrastructure* with an explicit
   promise of compound value for future workflows.
   M28.2's `NewJournalEntryTemplateDialog` reuses the
   M27.2 `GLAccountPicker` component (which in turn
   consumes the M27.1 `fetchGLAccounts` wrapper) — the
   first substrate consumer beyond the M27.2 dialog. The
   validation of that framing was the immediate M28
   scope decision: recurring templates was selected
   partly because it exercises this exact reuse path.

2. **Normalization over coupling (M28.0 architectural
   verification).** Template lines and posting lines are
   *shaped* the same (account FK + tenancy + memo) but
   *are* different domain concepts. Recipes are
   editable and can defer amount specification; postings
   are immutable and require amounts. M28 keeps them in
   separate tables. The cross-tenant guard was evaluated
   for extraction as a shared helper and **deliberately
   kept duplicated** — the two `clean()` methods stay
   local to their owning models, each ~5 lines,
   unlikely to diverge. Small, stable, domain-local
   invariants are more readable when each model owns
   them explicitly than when they hide behind a shared
   helper. Fusion (via inheritance, mixin, or
   `is_template` flag) is rejected because it destroys
   separation of concerns and forces defensive filters
   on every posting-query consumer. Extraction (of the
   cross-tenant guard) is deferred until evidence of
   divergence or maintenance burden supports it.

## 0. Engineering practices to preserve from M2–M27

- **Tenant discipline.** New endpoints scope strictly to
  `get_current_dealership(request)` (same pattern as
  `admin_journal_entry_list`, `admin_gl_account_list`).
  No cross-tenant reads possible.
- **Money as Decimal-as-string on the wire.** Template
  line `amount` transmitted as string per M9.5 / M10.1 /
  M12 BHPH / M14 §5.c Option A / M27.2 continuity.
- **DRF `@api_view` + `_M131_PERMS`.** New endpoints
  follow the accounting-module precedent verbatim.
- **Response envelope discipline.**
  `{<resource_plural>: {<items_key>: [...]}}` for
  unpaginated collections;
  `{<resource_singular>: {...}}` for retrievals /
  creations. Matches `gl_accounts` / `journal_entry`.
- **Regression-test coverage.** Every new endpoint ships
  with backend unit tests (positive + negative + cross-
  tenant + permission + duplicate-name). Every new
  frontend wrapper ships with a wrapper vitest. Every
  new component ships with a component vitest. Every
  new operator workflow ships with a Playwright journey
  per M21.0 §5.f DoD (§5.g details M28.1 exception
  path).
- **Repo baseline discipline.** Backend 4,813 → **≥4,813
  + N** where N counts new tests. Frontend Vitest 246 →
  **≥246 + N**. Acceptance 16 → **19** (2 new template
  cases + 1 blank-path regression extension).
- **Zero-drift permission classes.** No new permission
  class added; both new endpoints reuse `_M131_PERMS`.
- **No LLM-path change.** N/A.
- **Coordinated push at milestone close, not per
  increment.** Per M18 → M27 cadence.
- **Duplicate small stable domain logic; extract only on
  evidence.** Per M28.0 §5.b architectural decision, the
  cross-tenant guard on `JournalEntryLine.clean` is
  **not** extracted at M28. The two `clean()` methods
  (existing on `JournalEntryLine`, new on
  `JournalEntryTemplateLine`) are ~5 lines each, enforce
  the same invariant against different parents, and are
  unlikely to diverge. Keeping them duplicated preserves
  local clarity — each model owns its own invariant
  explicitly rather than hiding it behind a shared
  helper. Extraction is reserved for the point where
  divergence or genuine maintenance burden appears; DRY
  for its own sake is not sufficient justification. This
  standard applies broadly: prefer duplication of small,
  stable, domain-local logic; extract only when evidence
  supports it.

## 1. Business questions this milestone answers

**Primary — governs §5.a.** *Can a dealership accountant
persist a recurring journal-entry recipe once and
instantiate it monthly through the shipped application?*

**Secondary questions M28 answers along the way:**

1. Where does template management live? (Answered by
   §5.b: as a collapsible "Recurring templates" section
   attached to `AccountingJournalEntriesPage` beneath
   the existing JE list card. No new route.)
2. How does an operator create a template? (Answered
   by §5.b: "+ New template" button in the templates
   section opens a new
   `NewJournalEntryTemplateDialog` — parallel to the
   M27.2 JE dialog, minus `posted_at`, with `name` +
   `description` + lines using `side` + `amount`.)
3. How does an operator instantiate a template? (Answered
   by §5.b: row-level "Instantiate" button on each
   template row opens the existing `NewJournalEntryDialog`
   pre-populated with the template's description +
   lines. Operator can edit any field before submit.
   Submit uses the existing M13.1 create endpoint — no
   new posting endpoint.)
4. How does the template line schema accommodate future
   variable-amount templates? (Answered by §5.b + §5.c:
   `side` (CharField choices) + nullable `amount`. M28
   serializer requires non-null; future variable-amount
   work relaxes serializer + adds instantiation prompt
   UI — zero schema migration.)
5. Should `JournalEntryTemplateLine` fuse with or
   inherit from `JournalEntryLine`? (Answered by §5.b
   architectural verification: **no.** Separate models;
   only the cross-tenant guard extracts to a shared
   helper. Rationale documented in §5.b commentary.)
6. How does the Playwright journey prove the workflow
   is operationally real? (Answered by §5.d: new
   `accounting_je_template.spec.ts` with create-template
   + instantiate-template cases, business-outcome
   assertions via admin API; plus 1-case extension to
   `accounting_je_create.spec.ts` for blank-path
   regression.)

## 2. What existing primitives extend

**Backend (extends `models.py`, `services/accounting.py`,
`views_accounting.py`, `urls.py`):**

- `models.py` — add two new model classes
  (`JournalEntryTemplate`, `JournalEntryTemplateLine`)
  near the existing `JournalEntry` / `JournalEntryLine`
  section (~lines 7300–7480). **`JournalEntryLine` is
  not modified.** The new `JournalEntryTemplateLine.clean`
  implements its own cross-tenant guard inline, mirroring
  (but not sharing) the pattern from
  `JournalEntryLine.clean`. See §0 and §5.b commentary
  for the rationale (small, stable, domain-local
  invariants stay duplicated until evidence supports
  extraction).
- `services/accounting.py` — add three new service
  verbs following the existing pattern:
  - `create_journal_entry_template(dealership, name,
    description, lines: list[TemplateLineInput]) ->
    JournalEntryTemplate` — atomic template + lines
    creation. Validates name uniqueness per tenant, ≥2
    lines, each line's account belongs to tenant,
    template-time balance (Σ debit-side = Σ credit-side
    using non-null amounts only).
  - `list_journal_entry_templates(dealership,
    include_inactive=False) -> QuerySet[JournalEntryTemplate]`
    — active templates ordered by name; the
    `include_inactive` param is present but only False
    is exercised at M28 (True defers to a future
    milestone).
  - `get_journal_entry_template(pk, dealership) ->
    JournalEntryTemplate | None` — fail-closed cross-
    tenant retrieval.
  - New `TemplateLineInput` dataclass mirroring the
    existing `JournalLineInput` shape (account + side +
    amount + memo).
  - New domain errors: `EmptyJournalEntryTemplateError`,
    `UnbalancedJournalEntryTemplateError`,
    `DuplicateJournalEntryTemplateNameError`,
    `InvalidJournalEntryTemplateLineError`. Reuses
    existing `CrossTenantGLAccountError`.
- `views_accounting.py` — add two new views:
  - `admin_journal_entry_template_create` (POST) with
    error mapping per §5.c.
  - `admin_journal_entry_template_list` (GET).
  - New request serializers
    (`JournalEntryTemplateCreateRequestSerializer`,
    `JournalEntryTemplateLineSerializer`).
  - New projection helpers (`_project_template`,
    `_project_template_line`).
- `urls.py` — add two routes under an accounting-
  specific section following the M27.1 pattern:
  - `path("admin/accounting/journal-entry-templates/",
    views_accounting.admin_journal_entry_template_create,
    name="admin-journal-entry-template-create")` for POST.
  - Same URL routed to `admin_journal_entry_template_list`
    for GET (Django-style method dispatch via a wrapper
    view, OR two @api_view methods on the same path).
    Decision: use DRF's `@api_view(["GET", "POST"])`
    approach with in-view method dispatch — matches the
    codebase's existing pattern where verb methods live
    in the same function.
- `services/accounting.py` **reuses without change** at
  M28.2 instantiation: the existing `post_journal_entry`
  service handles the actual posting when an operator
  instantiates a template. M28 adds no new posting
  path — templates are recipes, not postings.

**Frontend (extends `accountingApi.ts` + existing
accounting pages):**

- `lib/accountingApi.ts` — add:
  - `JournalEntryTemplateLineSide` type ("debit" |
    "credit").
  - `JournalEntryTemplateLine` + `JournalEntryTemplate`
    types.
  - `CreateJournalEntryTemplateLine` +
    `CreateJournalEntryTemplatePayload` types.
  - `fetchJournalEntryTemplates()` wrapper.
  - `createJournalEntryTemplate(payload)` wrapper.
- `pages/AccountingJournalEntriesPage.tsx` — extend
  in place with:
  - Second `useEffect` (or unified fetch) to load
    templates on mount via `fetchJournalEntryTemplates`.
  - New "Recurring templates" collapsible section
    beneath the existing JE list card. Section header
    contains title + count badge + "+ New template"
    button.
  - Row-level "Instantiate" action per template row.
  - State + handler wiring to open
    `NewJournalEntryDialog` pre-populated when
    Instantiate is clicked, and to open
    `NewJournalEntryTemplateDialog` when "+ New
    template" is clicked.
  - On template-created success: refetch templates
    list; inline success badge on the templates
    section (parallel to the existing JE success
    badge).
- **New component** at M28.2:
  `components/accounting/NewJournalEntryTemplateDialog.tsx`
  — peer to `NewJournalEntryDialog`. Fields: `name`
  (required, non-empty, trimmed, ≤200 chars),
  `description` (required, non-empty, trimmed, ≤500
  chars), dynamic `lines[]` table (min 2). Per-row:
  `GLAccountPicker` + `side` select (debit / credit)
  + `amount` number input + optional `memo`. Live
  balance indicator (Σ debit-side amounts vs Σ
  credit-side amounts). Submit + Cancel buttons. On
  submit → `createJournalEntryTemplate`. On 201 →
  close dialog + refetch list + inline success badge.
  Reuses the M27.2 dialog viewport-constraint pattern
  (`max-h-[90vh] flex-col` + scrollable inner body).
- **Existing component reused** at M28.2:
  `NewJournalEntryDialog` gains a new optional
  `initialValues` prop. When present, it pre-populates
  description + lines from a supplied template shape.
  All other behavior unchanged. `posted_at` still
  defaults to today's date at instantiation (templates
  don't specify posting timestamps).
- **Existing component reused** at M28.2:
  `GLAccountPicker` used verbatim inside the new
  template dialog. Zero changes to the picker.

**Tests (new dedicated files):**

- `backend/dealer_ai/tests/test_m28_journal_entry_template_model.py`
  — new template model tests (positive validation,
  cross-tenant guard on the new model,
  cascade-on-parent-delete, ordering + name uniqueness).
- `backend/dealer_ai/tests/test_m28_journal_entry_template_service.py`
  — service verb tests (create-atomic, list-active-
  ordered-by-name, get-fail-closed-cross-tenant,
  empty-lines-error, unbalanced-lines-error,
  duplicate-name-error).
- `backend/dealer_ai/tests/test_m28_journal_entry_template_endpoint.py`
  — endpoint tests (POST 201 success, POST 400
  serializer errors, POST 400 unbalanced, POST 409
  duplicate name, POST 404 cross-tenant account, GET
  200 list, GET 200 empty list, permission +
  authentication).
- `frontend/src/lib/accountingApi.templates.test.ts` —
  wrapper vitest (fetch + create; envelope projection;
  error path).
- `frontend/src/components/accounting/NewJournalEntryTemplateDialog.test.tsx`
  — dialog component tests (~12–15 cases mirroring
  `NewJournalEntryDialog.test.tsx`).
- `frontend/src/pages/AccountingJournalEntriesPage.test.tsx`
  — extend with ~4 cases for the templates section
  (renders section, empty state, "+ New template"
  opens template dialog, "Instantiate" opens JE
  dialog pre-populated).
- `frontend/src/components/accounting/NewJournalEntryDialog.test.tsx`
  — extend with ~3 cases for the pre-populate path
  (fields render pre-filled from `initialValues` prop;
  operator edits do not mutate the source template
  shape; submit posts the edited values).
- `acceptance/journeys/office/accounting_je_template.spec.ts`
  — NEW spec, two test cases per §5.d.
- `acceptance/journeys/office/accounting_je_create.spec.ts`
  — extend with one case (blank-path regression
  guard).

**Artifact (regenerated, not hand-edited):**

- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` —
  regenerated at both M28.1 close and M28.2 close per
  §5.e discipline. Coverage arithmetic:
  - **M28.1 close:** 155 → 157 endpoints. Two new
    template rows: `defer-candidate-O2` (endpoints
    exist, wrappers exist but not yet consumed by
    non-test frontend).
  - **M28.2 close:** both new rows flip → `covered`.
    Coverage 121 → 123.

**Docs (update-in-place per DOC_GOVERNANCE):**

- `docs/CAPABILITY_MATRIX.md` §7 — add a §7γ "M28
  shipped surface" block noting the new template
  endpoints + templates section + template dialog +
  pre-populate wiring on JE dialog.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — M28 entry
  in the shipped table.
- `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md` — NEW
  at M28 close per the standard retrospective shape.
- `00-START-NEXT-SESSION.md` — overwritten at M28
  close with SESSION_197 priorities (M29 target
  selection).

## 3. What's NOT in this milestone (deferrals)

- **Variable-amount templates.** Schema-reserved via
  the nullable `amount` column, but no M28 UI or
  serializer support. When operator evidence supports
  variable-amount templates (depreciation, utilities,
  payroll accruals), it re-enters as a future
  candidate. **Zero DB migration** — serializer relax
  + instantiation prompt UI only.
- **Named template variables** (one operator input
  drives multiple line amounts). Not schema-reserved
  at M28 to avoid YAGNI over-engineering. Future
  additive migration only (new `TemplateVariable`
  table + nullable FK on line).
- **Template edit / update endpoint.** No PATCH / PUT
  on `JournalEntryTemplate` at M28. If operator
  evidence demands template edit (e.g., mid-year
  chart-of-accounts changes require repointing a
  template line's account), it re-enters as a future
  milestone. Workaround at M28: create a new template
  and soft-hide the old one (via `is_active=False` at
  the DB layer — no UI yet).
- **Template delete / soft-hide UI.** No delete button
  or "Deactivate" affordance at M28. The `is_active`
  field exists on the model for future use; operator
  workaround is out-of-band (backend or SQL). Defers
  to a future milestone.
- **Historical-template back-reference.** No column on
  `JournalEntry` recording which template (if any)
  instantiated it. If operator evidence supports "show
  me every JE posted from template X", it re-enters
  as a future additive-migration candidate.
- **Server-side template search / pagination.** Full
  template list returned in a single response. Templates
  are expected to be small (typically ≤50 per tenant);
  if a future dealership has materially larger sets,
  pagination re-enters — but current data does not
  justify the substrate cost.
- **`?include_inactive=true` query parameter.** The
  service verb accepts the parameter but the endpoint
  hardcodes `False` at M28. Endpoint-level exposure
  defers to a future milestone.
- **Save-as-template checkbox on `NewJournalEntryDialog`.**
  Considered as an alternative UI shape (piggyback
  template creation on JE creation). Rejected at M28.0
  §5.b in favor of a dedicated dialog — clearer
  separation of concerns (template = recipe, JE =
  posting), first-class discoverability, better
  foundation for future variable-amount templates.
- **Template detail page.** Templates render inline in
  the templates section on the JE list page; no
  standalone detail route. Follows the M27.0
  substrate-attachment rule.
- **Any change to the M13.1 JE-create endpoint** or
  the M27.1 gl-accounts endpoint. Both are consumed
  as-is.
- **All prior M27 §3 deferrals** — remain valid for
  later re-entry (standalone CoA page/route; JE
  edit/update; `posted_by_user` override; advanced
  picker filtering; server-side gl-accounts pagination;
  `?include_inactive=true` on gl-accounts).
- **All prior M25 §4 deferrals** — remain valid for
  later re-entry.
- **NEW O2** (row-5 public-fetch-helper regex
  refinement). Still deferred at M28 per §5.a lens
  (operator-facing candidate selected over indirect
  substrate work). Re-enters as an M29+ candidate.
- **NEW O3** (rows-1–4 plain-string investigation).
  Still deferred at M28. Re-enters as an M29+
  candidate.
- **Test-hygiene remediation (Candidate H).** Kept
  separate at M28. Re-enters as an M29+ candidate;
  three-journey population confirmed at M27.2 full-
  suite run.
- **Gated candidates T / U / L / M** — unchanged
  posture from M27 close.

**Playwright journey binding for DoD compliance (M28.1
exception path per M21.0 §5.f Option B):** M28.1 is a
pure backend + wrapper increment with no operator
surface change. Per the M26 + M27.1 precedent
(second and third invocations of the exception path,
respectively), infrastructure-only increments may
invoke this exception — journey coverage for the new
endpoints lands at M28.2 via the new template journey
(which exercises both endpoints end-to-end). §5.g
documents this explicitly. **M28.2 is customer-facing**
and satisfies DoD directly.

## 4. What existing tests bind

- **Backend suite (4,813 pass, 1 skipped)** — M28 must
  hold this baseline. The shipped `JournalEntryLine.clean`
  is untouched at M28 (per §5.b evidence-first
  duplication decision); existing M13.1 model tests
  remain green without modification. New tests added
  per §5.c:
  - M28.1: model + service + endpoint tests → **≥4,813
    + ~20–25** at M28.1 close.
  - M28.2: no new backend tests (M28.2 is frontend +
    Playwright).
- **Frontend Vitest (246 pass across 34 files)** —
  unchanged at M28.1. Extended at M28.2:
  - M28.1: wrapper vitest → **≥246 + ~3** at M28.1
    close (wrapper file only; ~248–249 pass).
  - M28.2: template dialog + pre-populate + templates-
    section extensions → **≥249 + ~15–18** at M28.2
    close (~264–267 pass).
- **Acceptance (16 journeys, clean-DB dry-run ~30s)** —
  unchanged at M28.1. Extended at M28.2:
  - M28.2: new spec `accounting_je_template.spec.ts`
    with 2 test cases + 1-case extension to
    `accounting_je_create.spec.ts` → **19 journeys**
    at M28.2 close.
- **`test_m131_journal_entry_model.py`,
  `test_m131_accounting_endpoint.py`,
  `test_m131_accounting_service.py`,
  `test_m151_sale_booking.py`,
  `test_m161_bhph_payment_gl.py`,
  `test_m27_gl_account_list.py`,
  all M13–M27 accounting tests** — remain untouched.
  Shipped `JournalEntryLine` is not modified at M28;
  no test modifications required.
- **`AccountingJournalEntriesPage.test.tsx`,
  `AccountingJournalEntryDetailPage.test.tsx`,
  `AccountingTrialBalancePage.test.tsx`,
  `NewJournalEntryDialog.test.tsx`,
  `GLAccountPicker.test.tsx`** — extended at M28.2 as
  noted in §2. All extensions are additive (existing
  cases remain green).

## 5. Load-bearing decisions

### §5.a — Milestone target selection

**LOCKED at M28.0 open as A — Recurring journal
templates**, under the primary operational-coverage
lens.

**Independent recommendation rationale (SESSION_194
§5.a):** Four candidates elevated at M28.0 open under
the durable operational-coverage guiding question — A
(recurring templates, direct operator gain,
demonstrates M27.1 substrate compound value), O2
(row-5 public-fetch-helper regex refinement,
substrate), O3 (rows-1–4 plain-string investigation,
substrate), H (test-hygiene, CI stability). The AI's
independent recommendation was A under the primary
lens, with four grounds:

1. Only A is directly operator-facing among the
   elevated set. B / C / D are all indirect (audit
   accuracy or CI stability).
2. A is the first candidate that would *demonstrate*
   M27.1's "shared accounting infrastructure"
   compound-value framing on a real operator workflow.
3. Scope is bounded and small-to-moderate; comparable
   to M27's size. Fits an intentionally short M28 arc.
4. Satisfies DoD directly via new + extended Playwright
   journeys (no exception path needed at the
   customer-facing increment).

**Alternative framings considered:**
- **Combined O2 + O3 (M26-analogous)** — viable per
  the M27 §9 standing question, but neither is
  operator-facing; picking two indirect wins in a row
  after M26 (also audit-tooling) would drift from the
  operational-coverage lens without evidence of active
  mis-selection defects.
- **H — test-hygiene** — legitimate compound value but
  neither operator-facing nor tied to recent evidence
  urgency. Better as bounded sub-scope inside a future
  operator milestone (audit-correctness-as-supporting-
  infra pattern per memory
  `feedback_audit_correctness_as_supporting_infra.md`).

**Deferral promotion note:** JE templates / recurring
appears in M27 §3 as a deferral. M28 promotes it from
deferral to §5.a target because M27.1 + M27.2 shipped
the substrate that makes the operator-facing UI cheap
(the `GLAccountPicker` and `NewJournalEntryDialog`
components + the `fetchGLAccounts` wrapper are all
directly reusable).

**User confirmation:** the user confirmed the
recommendation at M28.0 §5.a. Then, before locking
§5.b, the user requested two architectural
verifications (variable-amount forward-compat and
model duplication analysis) — both were completed and
recorded in this memo's opening block + in §5.b's
commentary. Both verifications confirmed the current
design; the user then approved proceeding to §5.b–§5.h
draft, and confirmed the drafted decisions.

**Streak accounting (see §8):** locked as recommended
with two architectural verifications performed at open
+ documented refinements applied (cross-tenant helper
extraction; forward-compat rationale recorded) →
planning-time as-recommended streak increments **6 →
7** at M28.0 close.

### §5.b — Scope split (M28.1 backend substrate + M28.2 UI)

**LOCKED as a two-increment split with the substrate
strictly M28.1 and the operator surface strictly M28.2.**

**M28.1 — Backend substrate + frontend wrappers.**

*New models (in `dealer_ai/models.py`, added near the
existing `JournalEntry` / `JournalEntryLine` section):*

- **`JournalEntryTemplate`** — one row per named recipe.
  - `dealership` FK (CASCADE, `related_name="journal_entry_templates"`).
  - `name` CharField(max_length=200).
  - `description` CharField(max_length=500).
  - `is_active` BooleanField(default=True) — soft-hide
    reservation per M13.1 GLAccount precedent; no UI
    exposure at M28.
  - `created_at` / `updated_at`.
  - `Meta.constraints`: `UniqueConstraint(fields=
    ["dealership", "name"], name=
    "uniq_je_template_name_per_dealership")`.
  - `Meta.ordering = ["name"]`.

- **`JournalEntryTemplateLine`** — recipe line.
  - `template` FK (CASCADE, `related_name="lines"`).
  - `dealership` FK (CASCADE, cross-tenant guard mirror
    of `JournalEntryLine`).
  - `account` FK to `GLAccount` (PROTECT — same posture
    as `JournalEntryLine`).
  - `side` CharField(max_length=6,
    choices=[("debit","debit"), ("credit","credit")]) —
    always required (the fixed-structure signal).
  - `amount` DecimalField(max_digits=14, decimal_places=2,
    null=True, blank=True, validators=[MinValueValidator
    (Decimal("0.00"))]) — **NULL intentionally reserved
    for future variable-amount templates**; M28
    serializer requires non-null; docstring documents
    the reservation.
  - `memo` CharField(max_length=255, blank=True,
    default="").
  - `ordering` PositiveIntegerField(default=0).
  - `Meta.ordering = ["ordering", "id"]`.
  - `clean()` implements its own cross-tenant guard
    inline (~5 lines) — mirrors, but does not share,
    the pattern from `JournalEntryLine.clean`. See §5.b
    commentary and §0 engineering-practices for the
    evidence-first duplication rationale.

*Shipped `JournalEntryLine` model unchanged.* The
cross-tenant guard on the existing model is left as-is.
No refactor. Per §5.b architectural decision
(evidence-first duplication over DRY-for-its-own-sake):
the two `clean()` methods are ~5 lines each, enforce
the same invariant against different parents, and are
unlikely to diverge. Extraction is deferred until
evidence of divergence or maintenance burden appears.

*New service verbs (in
`dealer_ai/services/accounting.py`):*

- `create_journal_entry_template(dealership, name,
  description, lines: list[TemplateLineInput]) ->
  JournalEntryTemplate` — atomic template + lines
  creation.
- `list_journal_entry_templates(dealership,
  include_inactive=False) -> QuerySet[JournalEntryTemplate]`.
- `get_journal_entry_template(pk, dealership) ->
  JournalEntryTemplate | None`.
- New `TemplateLineInput` dataclass (account + side +
  amount + memo).
- New domain errors:
  `EmptyJournalEntryTemplateError`,
  `UnbalancedJournalEntryTemplateError`,
  `DuplicateJournalEntryTemplateNameError`,
  `InvalidJournalEntryTemplateLineError`.

*New endpoints (in `dealer_ai/views_accounting.py`,
same permission class `_M131_PERMS`):*

- **`POST admin/accounting/journal-entry-templates/`**
  → `admin_journal_entry_template_create`.
- **`GET admin/accounting/journal-entry-templates/`**
  → `admin_journal_entry_template_list`.
- Both routed at the same URL via
  `@api_view(["GET", "POST"])`; view branches on
  method.

*New migration:*
`dealer_ai/migrations/0050_m281_je_template.py`
(auto-detected via `makemigrations`; verify at open).

*New frontend wrappers (in `lib/accountingApi.ts`)
— no UI at M28.1:*

- `fetchJournalEntryTemplates(): Promise<JournalEntryTemplate[]>`.
- `createJournalEntryTemplate(payload):
  Promise<JournalEntryTemplate>`.

**M28.1 DoD exception path invoked** per §5.g (mirrors
M26 + M27.1).

---

**M28.2 — Frontend UI + Playwright + close-out fold.**

*Entry-point structure on `AccountingJournalEntriesPage`
(substrate-attachment per M27.0 §7 rule — no new
frontend route):*

- New "Recurring templates" collapsible section
  rendered beneath the existing JE list card (peer of
  the JE list on the same page).
- Section header: "Recurring templates" + count badge
  + "+ New template" button.
- Collapsed by default until operator expands
  (progressive disclosure — the primary flow is still
  JE creation; templates are a secondary affordance).
- Each row shows: name, description (truncated), line
  count, "Instantiate" button.
- Empty state: "No templates yet. Save your first
  template using the '+ New template' button."

*New component: `components/accounting/NewJournalEntryTemplateDialog.tsx`*

- Peer to `NewJournalEntryDialog`; reuses the M27.2
  dialog pattern including `GLAccountPicker` and the
  viewport-constraint fix
  (`max-h-[90vh] flex-col` + scrollable inner body).
- Fields: `name` (required, non-empty, trimmed, unique
  server-side per tenant), `description` (required,
  non-empty, trimmed), `lines[]` (min 2, per-row:
  `account_id` via picker + `side` select (debit /
  credit) + `amount` numeric input + optional `memo`).
- Balance indicator: `Σ debit-side amounts === Σ
  credit-side amounts` badge — same UX as JE dialog.
- **No `posted_at`** (templates aren't postings; the
  field appears at instantiation).
- Submit → `createJournalEntryTemplate` → on 201:
  closes dialog + refetches templates + inline success
  badge above the templates section (parallel to the
  M25.2 durable success-badge pattern).
- Cancel → dialog closes with no side effects.

*Existing component extended:
`components/accounting/NewJournalEntryDialog.tsx`*

- New optional `initialValues` prop accepting a
  `{description, lines}` shape.
- When present, dialog pre-populates the description
  input and the lines table from `initialValues`.
- `posted_at` still defaults to today's date at
  instantiation (templates don't specify posting
  timestamps).
- All other behavior unchanged. Existing dialog tests
  remain green (additive prop with a defaulting
  behavior).

*Existing component reused verbatim: `GLAccountPicker`.*
Zero changes.

*Instantiate flow (glue in `AccountingJournalEntriesPage`):*

- Clicking "Instantiate" on a template row builds an
  `initialValues` object from the template's
  `description` + `lines` (mapping `side` + `amount`
  → `debit` / `credit` for the JE dialog's shape) and
  opens the existing `NewJournalEntryDialog` with the
  built object. Operator can edit any field before
  submit. Submit posts a real JE via the existing
  `createJournalEntry` wrapper — no new posting
  endpoint.

*One-workflow-over-two check:* the two dialog-open
paths ("+ New journal entry" blank vs "Instantiate"
pre-populated) are **not overlapping** per memory
`feedback_one_workflow_over_two_overlapping.md`. They
solve distinct operational problems (originate a
fresh entry vs replay a recurring recipe) and Instantiate
is a per-template row action rather than a peer header
button. Legitimate branch, not overlap.

**Out of scope for §5.b (also enumerated in §3):**

- Variable-amount templates (schema-reserved, no UI
  or serializer support).
- Named template variables shared across lines.
- Template edit / update endpoints or UI.
- Template delete / soft-hide UI.
- Historical-template back-reference on `JournalEntry`.
- Server-side template search / pagination.
- `?include_inactive=true` on the endpoint.
- Save-as-template checkbox on `NewJournalEntryDialog`
  (considered and rejected in favor of dedicated
  template dialog).
- Standalone template detail page.
- Any change to M13.1 JE-create endpoint or M27.1
  gl-accounts endpoint.

**Commentary — on duplication vs sharing** (M28.0
architectural decision):

`JournalEntryTemplateLine` and `JournalEntryLine`
share three fields (`dealership`, `account`, `memo`)
and one logic pattern (cross-tenant guard on
`clean()`). Fusing the two models — either as an
abstract base class or by adding an `is_template`
flag on `JournalEntry` — was considered and rejected.
The former requires retrofitting inheritance on the
shipped, tested M13.1 model for negative ROI (three-
field dedup vs 4,813-test blast radius). The latter
destroys the M13.1 immutability + `posted_at` +
reversal invariants and forces
`WHERE is_template = FALSE` filters on every trial-
balance / JE-list / audit query — a maintenance
liability far larger than the duplication it removes.
The two models are line-shaped but represent different
domain concepts: recipes are editable and can defer
amount specification; postings are immutable and must
specify amounts. Normalization is correct here;
sharing would be premature coupling.
<br><br>
**On extracting the cross-tenant guard as a shared
helper** — considered and **rejected at M28** on the
same evidence-first standard applied across recent
milestones. The two `clean()` methods are ~5 lines
each; they enforce the same invariant against
different parents; they are unlikely to diverge.
Duplication of small, stable, domain-local logic
preserves *local clarity* — each model owns its own
invariant explicitly rather than hiding it behind a
module-level helper whose callers must be traced.
Extraction would satisfy DRY-for-its-own-sake without
solving an observed problem. The correct standard:
**duplicate small stable domain logic when it improves
local clarity; extract only when future divergence or
maintenance burden is supported by evidence.** If
either model's `clean()` grows non-trivially in a
future milestone, or if a third similarly-shaped model
lands, extraction re-enters as an evidence-backed
refactor. Not before.

**Commentary — on amount storage divergence** (M28.0
architectural decision):

`JournalEntryLine` uses dual `debit` / `credit`
columns (each non-negative, default 0).
`JournalEntryTemplateLine` uses `side` (CharField
choices) + nullable `amount`. This divergence is
intentional and forward-compatible with variable-
amount templates (depreciation, utilities, payroll
accruals). Dual-column encoding cannot express "side
known, amount deferred to instantiation" without an
added `side` column, so adding `side` now — once, at
template creation time — avoids a future migration +
backfill. At M28, the serializer requires non-null
`amount`; a future variable-amount milestone need
only relax that constraint and add an instantiation-
prompt UI. No M28 UI or serializer support for NULL
amounts; schema-only reservation, documented in the
model docstring so future contributors know the NULL
posture is intentional forward-compatibility, not a
bug.

### §5.c — Interface + payload contract

**LOCKED to match the existing accounting API response
envelope convention (verified at M28.0 §5.c open
against `gl_accounts` + `journal_entry` precedents).**

**M28.1 `POST admin/accounting/journal-entry-templates/`
request:**

```json
{
  "name": "Monthly rent",
  "description": "Rent expense — monthly",
  "lines": [
    {"account_id": 42, "side": "debit",  "amount": "3500.00", "memo": ""},
    {"account_id": 17, "side": "credit", "amount": "3500.00", "memo": ""}
  ]
}
```

Response `201`: `{"journal_entry_template": {...projection...}}`.

Projection includes: `id`, `dealership_id`, `name`,
`description`, `is_active`, `created_at`, `updated_at`,
`line_count`, `lines` (each with `id`, `account_id`,
`account_code`, `side`, `amount` (nullable string),
`memo`, `ordering`).

Error mapping:

- `400` — `EmptyJournalEntryTemplateError` /
  `InvalidJournalEntryTemplateLineError` /
  `UnbalancedJournalEntryTemplateError` / serializer
  error.
- `409` — `DuplicateJournalEntryTemplateNameError`
  (name collides with an existing template in the
  tenant).
- `404` — `CrossTenantGLAccountError` (fail-closed) —
  `{"detail": "GLAccount not found."}`.

**M28.1 `GET admin/accounting/journal-entry-templates/`
response** (unpaginated-collection envelope, mirrors
`gl_accounts`):

```json
{
  "journal_entry_templates": {
    "templates": [
      {
        "id": 1,
        "name": "Monthly rent",
        "description": "Rent expense — monthly",
        "is_active": true,
        "line_count": 2,
        "lines": [
          {"id": 1, "account_id": 42, "account_code": "615000",
           "side": "debit",  "amount": "3500.00", "memo": "", "ordering": 0},
          {"id": 2, "account_id": 17, "account_code": "110000",
           "side": "credit", "amount": "3500.00", "memo": "", "ordering": 1}
        ]
      }
    ]
  }
}
```

- HTTP 200 always for authenticated in-tenant
  requests (empty `templates` array is possible and
  expected for new dealerships).
- HTTP 401 / 403 per standard DRF permission handling.
- Sort: `name` ASC.
- List projection includes full line breakdown so the
  instantiate flow doesn't need a separate detail
  fetch (small payloads at M28; server-side detail
  endpoint deferred).

**M28.1 frontend wrapper types:**

```ts
export type JournalEntryTemplateLineSide = "debit" | "credit";

export interface JournalEntryTemplateLine {
  id: number;
  account_id: number;
  account_code: string;
  side: JournalEntryTemplateLineSide;
  amount: string | null;   // null reserved for future variable-amount
  memo: string;
  ordering: number;
}

export interface JournalEntryTemplate {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  line_count: number;
  lines: JournalEntryTemplateLine[];
}

export interface CreateJournalEntryTemplateLine {
  account_id: number;
  side: JournalEntryTemplateLineSide;
  amount: string;   // M28 serializer requires non-null
  memo?: string;
}

export interface CreateJournalEntryTemplatePayload {
  name: string;
  description: string;
  lines: CreateJournalEntryTemplateLine[];
}

export function fetchJournalEntryTemplates(): Promise<JournalEntryTemplate[]> {
  return authGetJSON<JournalEntryTemplateListResponse>(
    "/admin/accounting/journal-entry-templates/",
  ).then((body) => body.journal_entry_templates.templates);
}

export function createJournalEntryTemplate(
  payload: CreateJournalEntryTemplatePayload,
): Promise<JournalEntryTemplate> {
  return authPostJSON<JournalEntryTemplateResponse>(
    "/admin/accounting/journal-entry-templates/",
    payload,
  ).then((body) => body.journal_entry_template);
}
```

**Client-side validation (in
`NewJournalEntryTemplateDialog`):**

- `name` non-empty (trimmed), ≤200 chars.
- `description` non-empty (trimmed), ≤500 chars.
- ≥2 lines (enforced by minimum-row constraint).
- Every line has picked `account_id`.
- Every line has chosen `side`.
- Every line has positive `amount` > 0.
- Σ debit-side amounts equals Σ credit-side amounts
  (balance indicator badge).

Submit button disabled unless all seven conditions
hold.

**Error surfaces in the dialog:**

- Client validation failures: inline per-field or
  per-row error messages; balance indicator badge
  displays specific delta.
- Server 400: inline dialog error banner with the
  serializer `detail` string; dialog stays open.
- Server 409 (duplicate name): inline dialog error
  banner with the friendly phrasing "A template with
  that name already exists in this dealership."; dialog
  stays open.
- Server 404 (cross-tenant GLAccount): inline dialog
  error banner with "Account not available; refresh
  and try again."; dialog stays open.
- Network / other: generic inline error banner ("Failed
  to save template. Try again."); dialog stays open.

**Success surface:**

- Dialog closes on 201.
- Templates list refetches
  (`fetchJournalEntryTemplates` on the parent page).
- Inline success badge above the templates section:
  `"Template '{name}' saved"` with a subtle
  auto-dismiss after ~5s.

**Instantiate flow payload:**

- No new backend endpoint. `AccountingJournalEntriesPage`
  builds an `initialValues` object from the clicked
  template and passes it to the existing
  `NewJournalEntryDialog`. When the operator submits,
  the existing `createJournalEntry` wrapper posts a
  regular JE. The template is *not* referenced by the
  posted JE at the DB layer (no back-reference at
  M28; deferred).

### §5.d — Playwright verification protocol

**LOCKED as one new spec with two test cases + a
one-case extension to the existing
`accounting_je_create.spec.ts`.**

**New spec: `acceptance/journeys/office/accounting_je_template.spec.ts`.**

**Test case 1 — Successful create + instantiate.**

1. Owner navigates to
   `/dealer-ai-accounting/journal-entries`.
2. Owner expands the "Recurring templates" section
   (assert section renders empty state on first run).
3. Owner clicks "+ New template" — template dialog opens.
4. Owner types a name with the M28 fixture prefix
   (`[M28.2-tmpl-create] Monthly rent {runToken}`).
5. Owner types a description (`Rent expense —
   monthly`).
6. Owner picks line 1's account via CODE search
   (e.g., "615" for a rent-expense account); selects
   the `debit` side; enters `3500.00`.
7. Owner picks line 2's account via NAME search
   (e.g., "Bank" for the M13 default
   `110000 Bank — Operating`); selects the `credit`
   side; enters `3500.00`. **Both search modes
   exercised.**
8. Owner asserts balance badge reads "Balanced".
9. Owner clicks "Save template" — dialog closes.
10. Templates section refreshes; new row visible; inline
    success badge visible for the newly-saved template.
11. **Business-outcome assertion via admin API:**
    template exists with the expected name + line
    account_ids + amounts; balanced.

**Test case 2 — Instantiate template.**

1. Owner navigates to
   `/dealer-ai-accounting/journal-entries`.
2. Owner expands "Recurring templates" section.
3. Owner clicks "Instantiate" on the template seeded
   in test case 1 (or a fresh one if test case 2 runs
   independently — the spec's `beforeAll` may seed one
   via the admin API to keep the cases independent).
4. `NewJournalEntryDialog` opens with description +
   lines pre-populated. Assert description matches
   template. Assert account_ids match template.
   Assert debit/credit amounts match template's
   `amount` for the correct side.
5. Owner asserts `posted_at` defaults to today's date.
6. Owner asserts balance badge reads "Balanced".
7. Owner clicks "Create journal entry" — dialog closes.
8. JE list refreshes; new entry visible as top row;
   JE success badge visible for the newly-posted id.
9. **Business-outcome assertion via admin API:** JE
   exists with the template's description + account_ids
   + amounts on lines; `reverses_id` null; balanced.

**Extension to `accounting_je_create.spec.ts`
— one new test case:**

**Test case 3 (extension) — Blank-path regression guard.**

1. Owner navigates to
   `/dealer-ai-accounting/journal-entries`.
2. Owner clicks "+ New journal entry" (blank path,
   NOT via Instantiate).
3. Dialog opens with EMPTY description + EMPTY lines
   (minimum 2 blank rows). Assert dialog fields render
   empty (regression guard against Instantiate wiring
   accidentally pre-populating the blank path).
4. Owner fills description + 2 balanced lines +
   submits. Assert 201 + JE appears.

**Seed data:** verify
`seed_journey_office_accounting_workflow` provides
sufficient GLAccounts of appropriate types (rent-
expense + AP account for the monthly-rent fixture).
If the M13 default CoA lacks the rent-expense account,
augment the seed at M28.2 open.

**Cross-test isolation:** all three test cases use
distinct fixture prefixes (`[M28.2-tmpl-create]`,
`[M28.2-tmpl-instantiate]`, `[M28.2-blank-regression]`)
with per-run tokens; each asserts against its own
prefix; can run in any order without interference.

**Guiding principle (per M22.2 §5.f Option B):** the
journey is the operational contract. If the shipped
surface cannot complete any of the three workflows,
the test fails loudly and §5.d gap-handling applies
at close.

### §5.e — Coverage-baseline update discipline

**LOCKED as the two-source agreement discipline
inherited from M26.1 / M27, applied at each M28
increment close.**

**At M28.1 close, audit regeneration expected diff:**

- Backend endpoints: **155 → 157** (two new template
  endpoints; POST + GET on the same URL count as two
  audit rows).
- Both new rows disposition: **`defer-candidate-O2`**
  (endpoints exist; wrappers exist but not called by
  any non-test frontend file until M28.2).
- Coverage summary: **121 / 157** covered (121
  unchanged; denominator +2).
- Backend-only: 34 → 36.
- Service verbs: 312 → 312 + N (small).
- All other rows unchanged.

**At M28.2 close, audit regeneration expected diff:**

- Both new template rows populated with
  `accountingApi.ts:XXX fetchJournalEntryTemplates`
  and `accountingApi.ts:XXX createJournalEntryTemplate`;
  both dispositions flip → **`covered`**.
- Coverage summary: **121 → 123 covered / 157 total**.
- Backend-only: 36 → 34.
- All other rows unchanged.

**Two-source agreement (M26 §5.e discipline
preserved):**

Before recording the corrected baseline at any M28
increment close, BOTH of the following must agree:

1. **Regenerated artifact.** Refreshed
   `M21_OPERATIONAL_SURFACE_AUDIT.md` reflects the
   expected numeric diffs above.
2. **Direct repository inspection.** The wrappers
   named in the diff exist at the reported
   `{filename}:{line}`, with correct HTTP helper, and
   are imported and called by at least one non-test
   `.tsx` or `.ts` component under `frontend/src/`.

If either source disagrees, the baseline is NOT
updated — halt the close-out, document the
discrepancy, treat as a §5.b implementation gap.

**Recording sites at M28 close (in order):**

- `docs/CAPABILITY_MATRIX.md` §7γ block (new for M28).
- `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md` §1
  shipped scope summary + §2 quantitative surface
  deltas.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` M28 row.
- `docs/handoffs/SESSION_NNN_m28_close.md` frontmatter
  + baseline block.
- `00-START-NEXT-SESSION.md` operational-state block.

### §5.f — Increment shape

**LOCKED as 2 implementation increments + close-out,
with close-out folding into M28.2 per §5.h Option B
unless evidence forces a split.**

- **M28.0** — Planning refinement + target selection
  **(this session, SESSION_194)**. Locks all §5
  decisions. Ships the M28 memo + the SESSION_194
  handoff. **No code, no push.**
- **M28.1** — Backend substrate + frontend wrappers
  **(SESSION_195)**. Ships two new models + shared
  cross-tenant helper + three service verbs + two
  endpoints + two wrappers + backend tests + wrapper
  vitest. Docs update: `CAPABILITY_MATRIX.md` §7γ
  (M28.1 partial). DoD exception path per §5.g.
  **~1 session.**
- **M28.2** — Frontend UI + Playwright + close-out
  fold **(SESSION_196)**. Ships templates section +
  template dialog + Instantiate wiring +
  pre-populate extension on JE dialog + component
  vitests + new Playwright spec + one-case extension
  to existing spec. Docs update: `CAPABILITY_MATRIX.md`
  §7γ (M28.2 complete) + `IMPLEMENTATION_ROADMAP.md` +
  retrospective + `00-START-NEXT-SESSION.md`.
  **~1 session.**
- **M28.3** — Close-out (retrospective + coordinated
  push). **Folds into M28.2 close per §5.h Option B**
  unless verification surfaces §5.e discrepancies at
  either increment.

**Total: 2–3 sessions.** M28 is comparable to M27 in
size (M27 was two-increment substrate+UI split; M28
is same shape with a slightly larger backend surface
— new models vs new endpoint on existing models — and
a slightly larger frontend surface — new section +
new dialog + pre-populate extension).

### §5.g — DoD compliance (M21.0 §5.f exception path for M28.1 only)

**LOCKED with the exception path explicitly invoked
for M28.1 and satisfied directly at M28.2.**

Per the M21.0 §5.f Option B DoD amendment: every
future customer-facing milestone must add or update
at least one Playwright operational journey, OR
explicitly document in §3 why no journey change is
required.

**M28.1 is an infrastructure-only increment.** No
operator surface changes. The new template endpoints
have no consumer until M28.2 lands. Per the M26
precedent (audit-tooling refinement) and M27.1
precedent (gl-accounts substrate), M28.1 documents
the exception here in §5.g and mirrors it in §3
(deferrals-for-this-increment) and the M28.1
retrospective §journey-plan section. The new
endpoints' operational journey coverage arrives at
M28.2 via the template journey. **Third invocation
of the exception path** — the pattern is now
established for infrastructure-only sub-increments
inside operator-facing milestones.

**M28.2 is customer-facing** and satisfies DoD
directly. The Playwright coverage per §5.d covers:

- Template create workflow (dialog open + fill +
  submit + success badge + business-outcome API
  assertion).
- Template instantiate workflow (row Instantiate +
  pre-populated JE dialog + submit + JE post +
  business-outcome API assertion).
- Blank-path regression guard (existing JE dialog
  path remains empty when not opened via Instantiate).

All three exercise both new template endpoints, the
existing M13.1 create endpoint, the M27.1 gl-accounts
endpoint (via the picker), and the full frontend
dialog stack. A single end-to-end operational contract
covering the M28 shipped surface.

### §5.h — Close-out posture

**LOCKED as evidence-sized Option B (per M18 → M27
precedent).**

If M28.2 ships cleanly — backend green, frontend
green, all three Playwright cases green, both
increments' audit regenerations produce exactly the
expected coverage diffs per §5.e, docs update-in-
place with no anomalies — **fold the close-out into
the M28.2 session** (retrospective + coordinated
push in the same session). Otherwise promote to a
separate M28.3 close-out session.

Push executes **once**, at the end of the milestone,
per M18 → M27 cadence. No per-increment pushes.

**Expected commit count:**

- **6 folded:** M28.0 planning + M28.0 hash backfill +
  M28.1 implementation + M28.1 hash backfill + M28.2
  implementation & close + M28.2 hash backfill.
- **8 split:** add M28.3 close-out commit + hash
  backfill.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md` §5
   (durable lessons) + §9 (M28 evidence — A elevated)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (current 121 / 155 baseline; source of truth
   pre-M28)
7. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped
   surface) + §7α (M26 audit refinement) + §7β (M27
   shipped surface) + §7γ (M28 shipped surface, added
   at close)
8. `backend/dealer_ai/models.py` (existing
   `JournalEntry` / `JournalEntryLine` / `GLAccount`
   patterns — cross-tenant guard, PROTECT-vs-CASCADE
   FK posture, `Meta.constraints` conventions)
9. `backend/dealer_ai/views_accounting.py` (existing
   accounting-module patterns — permission classes,
   tenant scoping, response envelopes)
10. `backend/dealer_ai/services/accounting.py`
    (existing service-verb pattern —
    `create_*` / `list_*` / `get_*`, `*Input`
    dataclasses, domain error hierarchy)
11. `frontend/src/lib/accountingApi.ts` (existing
    wrapper conventions — envelope projection,
    Decimal-as-string)
12. `frontend/src/components/accounting/NewJournalEntryDialog.tsx`
    (M27.2 dialog pattern — the template for the M28.2
    template dialog; also the target of the
    pre-populate extension)
13. `frontend/src/components/accounting/GLAccountPicker.tsx`
    (M27.2 picker — reused verbatim inside the M28.2
    template dialog)
14. `frontend/src/pages/AccountingJournalEntriesPage.tsx`
    (M27.2 host page — the target of the templates
    section extension)
15. `acceptance/journeys/office/accounting_je_create.spec.ts`
    (M27.2 journey pattern — the template for the M28.2
    template journey; also the target of the blank-path
    regression extension)
16. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (durable planning lesson from M27.0 §7 —
    verified at M28.0 §7)
17. Memory record `feedback_one_workflow_over_two_overlapping.md`
    (durable rule; M28 verified the "+ New JE" vs
    "Instantiate" branch is not overlapping)
18. Memory record `feedback_preserve_existing_code.md`
    (durable rule; drove M28.0 rejection of both
    inheritance fusion and `is_template` flag fusion
    for the template models)

## 7. Sequencing

**M28.0 (SESSION_194, this session)** — planning
refinement + target selection + all §5 locks + two
architectural verifications. Ships memo + handoff.
No code, no push.

**M28.1 (SESSION_195)** — backend substrate + wrappers.
In order:

1. Verify M27 close baseline holds (backend 4,813
   pass, frontend 246 pass, acceptance 16 journeys
   clean-DB, audit 121 / 155, HEAD at `172de87` or
   later, redis PONG).
2. Regenerate audit to confirm 121 / 155 still holds.
3. Add `JournalEntryTemplate` + `JournalEntryTemplateLine`
   models in `models.py` near the existing `JournalEntry`
   / `JournalEntryLine` section. `JournalEntryTemplateLine.clean`
   implements its own cross-tenant guard inline (~5
   lines). **Do not modify** `JournalEntryLine` — no
   refactor at M28 (per §5.b evidence-first duplication
   decision).
4. Run `python3 manage.py makemigrations` — verify the
   auto-detected migration matches expectation
   (`0050_m281_je_template.py` with two `CreateModel`
   operations + the unique constraint).
5. Add service verbs (`create_journal_entry_template`,
   `list_journal_entry_templates`,
   `get_journal_entry_template`) + `TemplateLineInput`
   dataclass + new domain errors in
   `services/accounting.py`.
6. Add serializers + view function + URL route in
   `views_accounting.py` + `urls.py`.
7. Write `test_m28_journal_entry_template_model.py`,
   `test_m28_journal_entry_template_service.py`,
   `test_m28_journal_entry_template_endpoint.py`
   (positive + negative + cross-tenant + duplicate-
   name + permission + authentication cases per §5.c).
8. Run `python3 manage.py test dealer_ai` — assert
   green (4,813 → ≥4,830). Existing M13.1 model tests
   remain untouched and remain green (no modification
   to shipped model).
9. Add `fetchJournalEntryTemplates` +
   `createJournalEntryTemplate` wrappers + types in
   `accountingApi.ts`.
10. Write `accountingApi.templates.test.ts` vitest.
11. Run `npm test` — assert green (246 → ~249).
12. Regenerate audit; assert exactly the expected
    diff per §5.e M28.1 (155 → 157; two new rows at
    `defer-candidate-O2`).
13. §5.e Phase 2 per-row verification for the new
    rows (endpoint file:line correct; view symbol
    matches; permissions match).
14. Update `docs/CAPABILITY_MATRIX.md` §7γ with the
    M28.1 partial shipped surface.
15. Draft M28.1 handoff
    `docs/handoffs/SESSION_195_m28_inc1_substrate.md`.
16. **No push at M28.1 close.** Coordinated push at
    M28 close per §5.h.

**M28.2 (SESSION_196)** — frontend UI + Playwright +
close-out fold. In order:

1. Verify M28.1 close baseline holds (backend ~4,835
   pass, frontend ~249 pass, acceptance 16 journeys
   clean-DB, audit 121 / 157 with two new rows at
   `defer-candidate-O2`, HEAD at M28.1 close local
   commit).
2. Extend `AccountingJournalEntriesPage.tsx` with
   templates fetch + "Recurring templates"
   collapsible section + "+ New template" +
   Instantiate row action + state wiring.
3. Implement `NewJournalEntryTemplateDialog` component
   (name + description + dynamic lines with `side`
   select + `amount` input + balance indicator +
   submit/cancel).
4. Extend `NewJournalEntryDialog` with optional
   `initialValues` prop (additive; existing tests
   remain green).
5. Wire Instantiate handler in
   `AccountingJournalEntriesPage.tsx` to build
   `initialValues` from a template and open the JE
   dialog pre-populated.
6. Write component vitests
   (`NewJournalEntryTemplateDialog.test.tsx`; extend
   `AccountingJournalEntriesPage.test.tsx` for
   templates section; extend
   `NewJournalEntryDialog.test.tsx` for pre-populate
   path).
7. Run `npm test` — assert green (~249 → ~264–267).
8. Confirm seed
   `seed_journey_office_accounting_workflow`
   provides sufficient GLAccounts for template
   fixtures; augment if needed.
9. Add `accounting_je_template.spec.ts` with two test
   cases (create-template + instantiate-template) per
   §5.d.
10. Extend `accounting_je_create.spec.ts` with one
    test case (blank-path regression guard).
11. Run acceptance suite; assert all three new cases
    green.
12. Run `python3 manage.py test dealer_ai` — assert
    baseline holds (no backend changes at M28.2).
13. Regenerate audit; assert exactly the expected
    diff per §5.e M28.2 (both new rows flip → `covered`;
    coverage 121 → 123).
14. §5.e Phase 2 per-row verification for both flipped
    rows.
15. Update `docs/CAPABILITY_MATRIX.md` §7γ (M28.2
    complete).
16. Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
    M28 entry.
17. Draft `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md`.
18. Overwrite `00-START-NEXT-SESSION.md` with
    SESSION_197 priorities (M29 target selection).
19. Compose M28.2 handoff
    `docs/handoffs/SESSION_196_m28_close.md` (or
    split if §5.h evidence forces).
20. Coordinated push (all M28 commits + hash
    backfills).

**M28.3 (SESSION_197, only if split)** — close-out.
Retrospective + coordinated push of any deferred M28
work.

## 8. Streak accounting (M28)

- **Zero-drift permission-class streak** — enters M28
  at **27 consecutive milestones (M10 → M27)**. M28
  reuses `_M131_PERMS` for both new endpoints; no
  permission classes evolve. Intended posture at M28
  close: extend to **28 consecutive milestones (M10 →
  M28)**.
- **Planning-time as-recommended streak** — enters
  M28 at **6** (M25.0 + M25.1 + M25.2 + M26.0 + M26.1
  + M27.0 all locked as recommended). M28.0 opens with
  an AI recommendation of A under the primary
  operational-coverage lens; the user confirmed the
  recommendation, then requested two architectural
  verifications (variable-amount forward-compat and
  model duplication analysis) before locking §5.b.
  Both verifications confirmed the current design.
  The initial draft of §5.b proposed extracting the
  cross-tenant guard as a shared helper; the user
  applied the evidence-first standard and directed
  that small stable domain logic be duplicated until
  divergence or maintenance burden warrants
  extraction. The memo was updated to reflect this
  standard as a durable engineering-practices rule
  and to remove the helper-extraction step from M28.1
  sequencing. Per the empirical-discovery precedent
  (M25.0 + M25.2-open + M26.1-open + SESSION_189 §3 +
  M27.0 §7), design refinements that narrow evidence
  or add forward-compat rationale without changing
  the selected target still count as as-recommended.
  **M28.0 counts as as-recommended → streak
  increments 6 → 7.**

## 9. Non-goals for the remaining M28 increments

- ❌ Do NOT create a standalone template detail
  page, route, or navigation entry. §5.b out-of-scope;
  §3 deferrals; per M27.0 substrate-attachment rule
  continuity.
- ❌ Do NOT modify the shipped M13.1 `JournalEntry`
  or `JournalEntryLine` models. No refactor at M28,
  including no extraction of the cross-tenant guard.
  §5.b architectural verification rejected fusion;
  §5.b evidence-first duplication decision rejected
  helper extraction. Both stand.
- ❌ Do NOT ship variable-amount templates. Schema
  reserves the path; no UI or serializer support at
  M28.
- ❌ Do NOT ship named template variables. Not
  schema-reserved at M28 (future additive migration).
- ❌ Do NOT ship template edit / delete UI. `is_active`
  exists at the DB layer but has no operator surface.
- ❌ Do NOT add a `template_id` back-reference on
  `JournalEntry` at M28. Deferred.
- ❌ Do NOT add server-side template search /
  pagination.
- ❌ Do NOT expose `?include_inactive=true` on the
  endpoint.
- ❌ Do NOT modify the M13.1 JE-create endpoint or
  the M27.1 gl-accounts endpoint.
- ❌ Do NOT push at M28.1 close. Single coordinated
  push at M28.2 close per §5.h.
- ❌ Do NOT skip the two-source agreement check at
  either increment's audit regeneration.
- ❌ Do NOT skip the §7 FK-discoverability check at
  M28.1 open. All FKs must have discovery surfaces
  before M28.1 code ships (verified at M28.0; carry
  forward at M28.1 open to catch drift).
