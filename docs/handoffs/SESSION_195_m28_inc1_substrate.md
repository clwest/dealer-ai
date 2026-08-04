---
title: "SESSION_195 handoff — Milestone 28 · Increment 1 (M28.1 — backend substrate + wrappers)"
status: historical
type: handoff
date: 2026-08-03
session: 195
milestone: 28
milestone_status: active
milestone_name: "Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_195 — Milestone 28 · Increment 1 (M28.1 — backend substrate + frontend wrappers)

## What shipped

M28.1 delivers the backend substrate for recurring journal
templates plus the frontend wrappers that M28.2 will consume.
No operator surface yet (§5.g DoD exception path invoked — third
invocation after M26 audit-tooling + M27.1 gl-accounts). Full
active memo governs at `docs/roadmap/MILESTONE_28_PLANNING.md`.

### Backend models

- **`JournalEntryTemplate`** (models.py:7492+) — one row per
  named recipe.
  - FKs: `dealership` CASCADE, `related_name="journal_entry_templates"`.
  - Fields: `name` CharField(200), `description` CharField(500),
    `is_active` BooleanField(default=True) — soft-hide reservation
    per M13.1 GLAccount precedent (no operator UI at M28).
  - Unique constraint: `(dealership, name)` — enforced at DB layer.
  - `Meta.ordering = ["name"]`.

- **`JournalEntryTemplateLine`** (models.py:7554+) — recipe line
  with **intentional forward-compat schema divergence** from
  `JournalEntryLine`.
  - FKs: `template` CASCADE, `dealership` CASCADE, `account`
    PROTECT.
  - `side` CharField(max_length=6, choices=[("debit","debit"),
    ("credit","credit")]) — always required (the fixed-structure
    signal).
  - `amount` DecimalField(max_digits=14, decimal_places=2,
    **null=True**, blank=True, validators=[MinValueValidator(0)])
    — **NULL intentionally reserved for future variable-amount
    templates**; M28 serializer requires non-null; docstring
    documents the reservation.
  - `memo` CharField(255, blank), `ordering` PositiveIntegerField.
  - `Meta.ordering = ["ordering", "id"]`.
  - `clean()` implements cross-tenant guard inline (~10 lines) —
    **duplicated from `JournalEntryLine.clean`, deliberately**,
    per M28.0 §5.b evidence-first standard.

- **`JournalEntryLine` UNCHANGED.** The shipped M13.1 model is
  not touched at M28. Existing tests remain green without
  modification (verified: full M131 suite still passes as part
  of the 4,855-test run).

### Migration

- `dealer_ai/migrations/0050_m281_je_template.py` (renamed from
  auto-detected `0050_journalentrytemplate_journalentrytemplateline_and_more.py`
  to match memo convention). Two CreateModel operations + the
  unique constraint. `makemigrations --check --dry-run` clean
  post-rename.

### Service verbs

New module `services/accounting/template.py`:

- `create_journal_entry_template(dealership, name, description,
  lines: list[TemplateLineInput]) -> JournalEntryTemplate` —
  atomic create with balance + tenant + name-uniqueness
  validation. Wraps the `IntegrityError` from the DB unique
  constraint into `DuplicateJournalEntryTemplateNameError`.
- `list_journal_entry_templates(dealership, include_inactive=False)
  -> QuerySet[JournalEntryTemplate]` — active-only by default;
  the `include_inactive` opt-in is present for tests but not
  exposed via endpoint at M28 (§3 deferral).
- `get_journal_entry_template(pk, dealership) ->
  JournalEntryTemplate | None` — fail-closed cross-tenant read.
- `TemplateLineInput` dataclass (account + side + amount + memo
  + ordering).
- New domain errors: `EmptyJournalEntryTemplateError`,
  `InvalidJournalEntryTemplateLineError`,
  `UnbalancedJournalEntryTemplateError`,
  `DuplicateJournalEntryTemplateNameError`. Reuses existing
  `CrossTenantGLAccountError`.

Exports added to `services/accounting/__init__.py` __all__.

### Endpoint

- **`GET / POST admin/accounting/journal-entry-templates/`** via
  `admin_journal_entry_template_list_or_create` at
  `views_accounting.py:706+`.
  - `@api_view(["GET", "POST"])` + `permission_classes(_M131_PERMS)`.
  - GET returns unpaginated list envelope
    `{"journal_entry_templates": {"templates": [...]}}`;
    templates ordered by `name`; full line breakdown included so
    instantiation doesn't need a separate detail fetch.
  - POST creates atomically; envelope `{"journal_entry_template":
    {...projection...}}`; error mapping: 400 (empty / invalid /
    unbalanced / serializer error), 404 (cross-tenant GLAccount),
    409 (duplicate name).
  - Projection fields per template: `id`, `dealership_id`, `name`,
    `description`, `is_active`, `line_count`, `lines[]`,
    `created_at`, `updated_at`. Per-line: `id`, `account_id`,
    `account_code`, `side`, `amount` (nullable string), `memo`,
    `ordering`.
- New serializers: `JournalEntryTemplateLineSerializer`,
  `JournalEntryTemplateCreateRequestSerializer`.
- Route wired at `urls.py:1041` with name
  `admin-journal-entry-template-list-or-create`.

### Frontend wrappers

`frontend/src/lib/accountingApi.ts` (~85 new lines):

- Types: `JournalEntryTemplateLineSide`,
  `JournalEntryTemplateLine`, `JournalEntryTemplate`,
  `CreateJournalEntryTemplateLine`,
  `CreateJournalEntryTemplatePayload`.
- Wrappers: `fetchJournalEntryTemplates()`,
  `createJournalEntryTemplate(payload)`.
- Both reuse the existing `authGetJSON` / `authPostJSON` helpers;
  Decimal-as-string wire posture; nullable amount preserved
  through the projection (documented as forward-compat).

### Test coverage

- **Backend +42:**
  - `test_m28_journal_entry_template_model.py` (10 tests) —
    round-trip + amount NULL posture + name uniqueness per
    tenant + cross-tenant guards (account + template) + cascade
    delete + PROTECT on account with lines + Meta.ordering.
  - `test_m28_journal_entry_template_service.py` (17 tests) —
    happy path + refuses empty/single/null-amount/zero/negative/
    bad-side/cross-tenant/unbalanced/duplicate-name; list active-
    only + include_inactive opt-in + empty tenant + tenant
    scoping; get returns None for missing + cross-tenant.
  - `test_m28_journal_entry_template_endpoint.py` (15 tests) —
    POST 201 happy path + envelope projection + serializer
    error 400 + empty/single-line/unbalanced/bad-side 400 +
    missing/cross-tenant account 404 + duplicate name 409 +
    advisor 403 + unauthenticated 401/403; GET 200 active-only
    ordered-by-name + empty tenant 200 + tenant scoping +
    advisor 403 + unauthenticated 401/403.
- **Frontend +5:** `lib/accountingApi.templates.test.ts` —
  fetch calls correct URL + projects envelope; empty envelope
  returns []; nullable-amount preserved through projection;
  create posts to correct URL with payload + projects response;
  error propagation from `authPostJSON`.

### Baselines at M28.1 close

- **Backend: 4,813 → 4,855 pass, 1 skipped, 0 fail** (167.3s).
- **Frontend Vitest: 246 → 251 pass** across 34 → 35 files.
- **Acceptance: 16 journeys unchanged** (DoD exception path
  invoked per §5.g).
- **Audit: 155 → 156 endpoints / 121 covered / 34 → 35 backend-
  only / 312 → 315 service verbs.** New row 150
  `admin/accounting/journal-entry-templates/` disposition
  `defer-candidate-O2` (both wrappers detected as
  `⚠ wrapper-only` — expected M28.1 state, flips to `covered`
  at M28.2 when the templates section consumes them).
- `python3 manage.py check` clean; `makemigrations --check
  --dry-run` clean; `redis-cli ping` PONG; `frontend tsc
  --noEmit` clean.

### §5.e two-source agreement

Both sources agree at M28.1 close:

1. **Regenerated artifact.** New audit row 150 present with
   correct URL, view symbol, URL name, wrapper lines, and
   `defer-candidate-O2` disposition.
2. **Direct repo inspection.** Both wrappers exist at the
   reported lines (accountingApi.ts:446 / 452 — audit reports
   lines 447 / 455 following its first-body-statement
   convention, matches shipped precedent for `fetchGLAccounts`
   at line 342 / audit-reported 343).

### §5.e empirical-discovery refinement recorded

The M28 memo predicted the audit delta as **+2 rows** at M28.1
close (155 → 157) because I miscounted GET + POST on a single
URL as two audit entries. The audit tool treats a single URL
as one row regardless of `@api_view` verb dispatch. **Actual
delta: +1 row (155 → 156).** No scope shift — the endpoint
itself behaves exactly as scoped; the memo's numerical
prediction was empirically corrected at first regen. Recorded
in the CAPABILITY_MATRIX §7γ M28.1 row and in this handoff.
Future memo predictions for combined-verb endpoints will use
+1, not +2.

**Adjusted M28.2 close targets:**
- Coverage: **156 / 122** (not 157 / 123) — one row flips from
  `defer-candidate-O2` to `covered` when the templates section
  + template dialog consume both wrappers.
- Backend-only: 35 → 34.

## What was NOT touched this session

- **Shipped `JournalEntryLine` model** — untouched per §5.b
  evidence-first duplication decision.
- **No frontend UI.** No new component, no page extension, no
  route change. M28.2 scope.
- **No Playwright journey.** DoD exception path invoked at
  §5.g; journey coverage lands at M28.2.
- **No push.** Coordinated push at M28 close per §5.h.

## Files created / modified this session

- **CREATED:** `backend/dealer_ai/services/accounting/template.py`
  (new service module).
- **CREATED:** `backend/dealer_ai/migrations/0050_m281_je_template.py`
  (auto-generated, renamed to memo convention).
- **CREATED:** `backend/dealer_ai/tests/test_m28_journal_entry_template_model.py`.
- **CREATED:** `backend/dealer_ai/tests/test_m28_journal_entry_template_service.py`.
- **CREATED:** `backend/dealer_ai/tests/test_m28_journal_entry_template_endpoint.py`.
- **CREATED:** `frontend/src/lib/accountingApi.templates.test.ts`.
- **MODIFIED:** `backend/dealer_ai/models.py` — appended two new
  classes after `JournalEntryLine.clean()`; nothing else touched.
- **MODIFIED:** `backend/dealer_ai/services/accounting/__init__.py`
  — added template imports + `__all__` entries.
- **MODIFIED:** `backend/dealer_ai/views_accounting.py` — added
  template serializers + view + projection helpers + resolver;
  extended existing model + service imports.
- **MODIFIED:** `backend/dealer_ai/urls.py` — added template
  route.
- **MODIFIED:** `frontend/src/lib/accountingApi.ts` — appended
  template wrappers + types after the M27.2 `createJournalEntry`
  wrapper.
- **MODIFIED:** `docs/CAPABILITY_MATRIX.md` — new §7γ block.
- **MODIFIED:** `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  — regenerated with new row 150.
- **CREATED:** `docs/handoffs/SESSION_195_m28_inc1_substrate.md`
  — this handoff.

## Streak accounting (post-SESSION_195)

- **Zero-drift permission-class streak:** unchanged at **27**
  intended → **28** at M28 close. Both new endpoints (GET +
  POST via `@api_view(["GET","POST"])`) reuse `_M131_PERMS`;
  no permission classes evolve at M28.1.
- **Planning-time as-recommended streak:** unchanged at **7**
  (M28.1 is pure implementation of the M28.0 locked plan).

## Durable lessons carried forward from M28.1

- **REINFORCED at M28.1** — *Duplicate small stable domain
  logic; extract only on evidence.* The M28.1 implementation
  applied this rule verbatim: `JournalEntryTemplateLine.clean`
  duplicates the ~10-line cross-tenant guard from
  `JournalEntryLine.clean` instead of extracting a shared
  helper. Both `clean()` methods stay local to their owning
  models. This was the first M28+ increment to *apply* the
  new memory rule after M28.0 authored it — evidence that
  the rule is actionable.
- **REINFORCED at M28.1** — *Variable-amount forward-compat
  via `side` + nullable `amount` separation.* The shipped
  schema matches the M28.0 design exactly; the model's
  docstring records the intentional forward-compat posture
  for future contributors.
- **NEW at M28.1** — *Combined GET+POST endpoints count as ONE
  audit row, not two.* Refines the memo's numerical prediction
  (155 → 156, not 155 → 157). Empirical-discovery-refinement
  precedent per M25.0 + M25.2 + SESSION_189 §3 + M27.0. Future
  planning memos should use +1 for single-URL multi-verb
  endpoints.

## What SESSION_196 must do (M28.2)

Per `docs/roadmap/MILESTONE_28_PLANNING.md` §7 M28.2 sequencing:

1. Verify M28.1 close baseline holds (backend 4,855 pass,
   frontend 251 pass, acceptance 16 journeys, audit 121 / 156
   with row 150 at `defer-candidate-O2`, HEAD at M28.1 close
   local commit).
2. Extend `AccountingJournalEntriesPage.tsx` with templates
   fetch + "Recurring templates" collapsible section beneath
   the JE list card + "+ New template" button + Instantiate
   row action + state wiring.
3. Implement `components/accounting/NewJournalEntryTemplateDialog.tsx`
   (name + description + dynamic lines with `side` select +
   `amount` input + `GLAccountPicker` reuse + balance indicator +
   submit/cancel + M27.2 dialog viewport constraints).
4. Extend `NewJournalEntryDialog` with optional `initialValues`
   prop (additive; existing tests remain green).
5. Wire Instantiate handler to build `initialValues` from a
   template (mapping `side` + `amount` → `debit` / `credit` for
   the JE dialog shape) and open the pre-populated dialog.
6. Write component vitests:
   - `NewJournalEntryTemplateDialog.test.tsx` (~12–15 cases).
   - `AccountingJournalEntriesPage.test.tsx` extension (~4
     templates-section cases).
   - `NewJournalEntryDialog.test.tsx` extension (~3
     pre-populate cases).
7. Frontend suite → assert green (251 → ~266–269).
8. Confirm seed `seed_journey_office_accounting_workflow`
   provides sufficient GLAccounts for template fixtures.
9. Add `acceptance/journeys/office/accounting_je_template.spec.ts`
   with 2 test cases (create-template + instantiate-template)
   per §5.d.
10. Extend `accounting_je_create.spec.ts` with 1 test case
    (blank-path regression guard).
11. Acceptance suite → all three new cases green.
12. Backend suite → baseline holds (no M28.2 backend changes;
    4,855 pass expected).
13. Regenerate audit; assert **156 → 156** (no new endpoints)
    with row 150 flipping `defer-candidate-O2 → covered`.
    Coverage 121 → 122; backend-only 35 → 34.
14. §5.e Phase 2 per-row verification for the flipped row.
15. Update `docs/CAPABILITY_MATRIX.md` §7γ (M28.2 complete).
16. Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` M28 entry.
17. Draft `docs/roadmap/MILESTONE_28_RETROSPECTIVE.md`.
18. Overwrite `00-START-NEXT-SESSION.md` with SESSION_197
    priorities.
19. Compose M28.2 handoff `docs/handoffs/SESSION_196_m28_close.md`
    (or split if §5.h evidence forces).
20. Coordinated push (all M28 commits + hash backfills).

## Non-goals for SESSION_196

- ❌ Do NOT ship variable-amount serializer support.
- ❌ Do NOT ship template edit / delete UI.
- ❌ Do NOT expose `?include_inactive=true`.
- ❌ Do NOT add a `template_id` back-reference on JournalEntry.
- ❌ Do NOT modify M13.1 create endpoint or M27.1 gl-accounts
  endpoint.
- ❌ Do NOT skip the two-source agreement check at audit
  regeneration.
- ❌ Do NOT push per-increment. Coordinated push at M28 close
  only.

## Coordination

- **Push posture:** local-only through M28.1. Coordinated
  push at M28 close per §5.h Option B.
- **Expected M28 commits at close:** now **8 folded** (M28.0
  planning + hash backfill + M28.1 substrate + hash backfill +
  M28.2 close + hash backfill + optional §5.h split adds 2
  more). Two M28 commits already landed locally at M28.0.
