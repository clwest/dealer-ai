---
title: "Milestone 28 — Recurring Journal Templates (on M27.1 shared GLAccount substrate) — Retrospective"
status: historical
type: retrospective
milestone: 28
milestone_status: shipped
generated: 2026-08-03
generated_at_session: SESSION_196 (M28.2 close + M28.3 close-out fold)
milestone_name: "Recurring Journal Templates (on M27.1 shared GLAccount substrate)"
increments_shipped: [0, 1, 2]
close_out_fold: true
sessions: [194, 195, 196]
commits_at_close: 6
---

# Milestone 28 — Recurring Journal Templates (on M27.1 shared GLAccount substrate) — Retrospective

> Milestone 28 opened at SESSION_194 M28.0 planning under the
> durable primary operational-coverage lens. M28.1 shipped the
> backend substrate + frontend wrappers at SESSION_195. M28.2
> shipped the customer-facing UI + Playwright coverage at
> SESSION_196 with M28.3 close-out folded in per §5.h evidence-
> sized Option B (both increments' §5.e Phase 1 + Phase 2
> checks passed cleanly on the first regeneration).
>
> **The anchor business question** — *Can a dealership accountant
> persist a recurring journal-entry recipe once and instantiate
> it monthly through the shipped application?* — is answered
> **yes**. Two Playwright cases confirm the end-to-end flow via
> business-outcome assertions against the admin API.
>
> M28 also validated the M27.1 "shared accounting infrastructure"
> framing empirically: the M27.1 gl-accounts substrate now has
> two operator-facing consumers (M27.2 JE-create dialog + M28.2
> template dialog), demonstrating compound value on the first
> follow-on milestone rather than letting the substrate sit
> unproven.

## 1. Planned scope

Per `MILESTONE_28_PLANNING.md` §5.b:

**M28.1 — Backend substrate.** Two new models
(`JournalEntryTemplate` + `JournalEntryTemplateLine` with
intentional forward-compat `side` + nullable `amount`), three
service verbs (`create_journal_entry_template`,
`list_journal_entry_templates`, `get_journal_entry_template`),
four new domain errors, one new endpoint
(`GET+POST admin/accounting/journal-entry-templates/`) reusing
`_M131_PERMS`, two frontend wrappers
(`fetchJournalEntryTemplates`, `createJournalEntryTemplate`).
No UI change; DoD exception path invoked per §5.g (third
invocation after M26 + M27.1).

**M28.2 — UI + Playwright + close-out fold.** New
"Recurring templates" collapsible section on the existing
`AccountingJournalEntriesPage` (substrate-attachment per M27.0
rule), new `NewJournalEntryTemplateDialog` component,
extension of `NewJournalEntryDialog` with additive
`initialValues` + controlled-open props for the Instantiate
flow, row-level Instantiate action that opens a second,
controlled mount of the JE dialog pre-populated from the
template. Playwright coverage: new
`accounting_je_template.spec.ts` with two test cases +
one-case extension to `accounting_je_create.spec.ts`
(blank-path regression guard).

## 2. What actually shipped

Exact match to plan. All §5.b decisions held; all §5.c payload
contracts held; all §5.d Playwright test cases green; §5.e
two-source agreement confirmed at both increments' close; §5.f
increment shape held (2 implementation + close-out fold); §5.g
DoD exception path invoked at M28.1 + satisfied directly at
M28.2; §5.h close-out fold invoked (M28.3 folded).

**Quantitative surface deltas:**

- **Backend endpoints:** 155 → 156 (+1). Single audit row for
  the combined GET+POST URL — memo predicted +2 but the audit
  tool counts one URL as one row regardless of HTTP verb
  dispatch (empirical-discovery refinement recorded at M28.1).
- **DRF admin surface:** 115 → 116 endpoints.
- **Service verbs:** 312 → 315 (+3 template verbs).
- **Backend tests:** 4,813 → 4,855 pass (+42) at M28.1;
  unchanged at M28.2.
- **Frontend Vitest:** 246 → 270 pass (+24) across 34 → 36
  files (+5 wrapper at M28.1 + 19 UI at M28.2).
- **Acceptance journeys:** 16 → 19 (+3 M28.2 cases in 2
  files). Full acceptance run: 22 passed / 3 pre-existing
  shared-DB failures unchanged from M27.2 close (Candidate H).
- **Audit coverage:** 121 / 155 → **122 / 156**. Row 150
  shipped `defer-candidate-O2` at M28.1 and flipped `covered`
  at M28.2.
- **Migrations:** 0049 → 0050 (`0050_m281_je_template.py`).
- **Frontend operator routes:** 20 unchanged (substrate-
  attachment).
- **Permission classes:** 7 unchanged.

**M28 shipped surface** documented in
`docs/CAPABILITY_MATRIX.md` §7γ (three rows: M28.0 planning,
M28.1 substrate, M28.2 UI+journeys+close).

**Shipped `JournalEntryLine` UNCHANGED.** Per the M28.0 §5.b
architectural verifications: no fusion, no inheritance, no
helper extraction. The two `clean()` methods across
`JournalEntryLine` and `JournalEntryTemplateLine` remain
independently owned per the evidence-first duplication
standard.

## 3. Deviations from plan and reason

**Numerical prediction refinement (M28.1 close):** memo
predicted audit delta +2 rows (155 → 157) for the GET+POST
endpoint but the tool counts one URL as one row. Actual delta
+1. No scope shift; endpoint behaves exactly as scoped.
Recorded in the M28.1 handoff and CAPABILITY_MATRIX §7γ.
Adjusted M28.2 close target to 156/122/34 (not 157/123/34).

**Playwright CSRF handling (M28.2 close):** the instantiate
spec's seed step (POST via `request` fixture) initially
returned 403 Forbidden. Root cause: DRF SessionAuthentication
requires `X-CSRFToken` header on mutating requests; browser
fetch/XHR wiring auto-populates this from the csrftoken
cookie but Playwright's APIRequestContext does not. Added a
`postWithCsrf` helper that extracts the csrftoken from
`request.storageState()` and includes it as an `X-CSRFToken`
header. This is a durable pattern for any future spec that
does mutating admin-API calls from the `request` fixture.

**Playwright numeric-input assertion refinement (M28.2 close):**
`toHaveValue("1275")` failed on `<input type="number">` when
the pre-populated value was `"1275.00"` (browser may normalize
trailing zeros or preserve them). Fixed by using a regex
`/^1275(\.00)?$/`. Durable pattern for any spec asserting
pre-formatted numeric inputs.

**No other deviations.** All eight §5 locks held from M28.0
open through M28.2 close.

## 4. Deferrals from M28 (all valid for later re-entry)

- **Variable-amount templates** (depreciation, utilities,
  payroll accruals). Schema-reserved via nullable `amount`;
  serializer + UI relaxations only — no DB migration required.
- **Named template variables** (one operator input drives
  multiple line amounts). Not schema-reserved. Future
  additive `TemplateVariable` migration.
- **Template edit / update / delete UI.** `is_active` exists
  at DB layer for future soft-hide surfacing.
- **Historical-template back-reference** on `JournalEntry`.
- **Server-side template search / pagination.**
- **`?include_inactive=true`** endpoint exposure (service verb
  supports it; endpoint hardcodes False).
- **Save-as-template checkbox** on the JE dialog — rejected
  at M28.0 in favor of dedicated template dialog.
- **Standalone template detail page.**
- All prior M27 §3 + M25 §4 deferrals — unchanged posture.

## 5. Durable design principles surfaced or reinforced

**NEW at M28.0** — *Duplicate small stable domain logic;
extract only on evidence.* Surfaced from user pushback on
initial helper-extraction proposal in §5.b. Short (~5-line),
stable, domain-local logic (e.g., a `clean()` method) stays
local to its owning model until divergence or measurable
maintenance burden supports extraction. DRY-for-its-own-sake
is not evidence. Saved to memory as
`feedback_duplicate_small_stable_logic.md`. Applies broadly
across future refactor scoping.

**REINFORCED at M28.0** — *Variable-amount forward-compat via
schema separation of `side` + nullable `amount`* (new
architectural pattern). Dual-column encoding
(`debit`/`credit`) cannot express "side known, amount deferred
to instantiation" without an added side column — so adding
`side` now, once, at template creation time, avoids a later
migration + backfill. Documented in the model docstring for
future contributors.

**REINFORCED at M28.0** — *Recipes vs postings are different
domain concepts.* Fusing them via inheritance, mixin, or
`is_template` flag destroys separation of concerns and forces
`WHERE is_template = FALSE` filters on every posting-query
consumer. Normalization is correct; sharing would be premature
coupling.

**REINFORCED at M28.0** — *Verify FK / identifier
discoverability at planning-open* (M27.0 origin). All M28 FKs
verified against existing discovery surfaces before §5.b lock:
Template IDs surface via the templates section on
`AccountingJournalEntriesPage`; GLAccount IDs reuse the M27.2
`GLAccountPicker` (which consumes the M27.1 `fetchGLAccounts`
wrapper).

**REINFORCED at M28.1** — *DoD exception path for
infrastructure-only sub-increments*. Third invocation (M26
audit-tooling + M27.1 gl-accounts + M28.1 template substrate).
The pattern is now well-established.

**NEW at M28.1** — *Combined GET+POST endpoints count as one
audit row, not two.* Refines memo prediction pattern for
`@api_view(["GET","POST"])` endpoints. Empirical-discovery
refinement precedent per M25.0 + M25.2 + SESSION_189 + M27.0.

**NEW at M28.2** — *Playwright APIRequestContext does NOT
auto-populate `X-CSRFToken` from the storage-state csrftoken
cookie.* Browser fetch/XHR wiring does this automatically;
Playwright does not. Mutating requests from the `request`
fixture need an explicit CSRF header extracted from
`request.storageState()`. Helper pattern available at
`accounting_je_template.spec.ts:postWithCsrf` for future
specs.

**NEW at M28.2** — *Numeric input value pre-population may
normalize trailing zeros* (`3500.00` → `3500` or preserved
depending on browser). Playwright assertions on `<input
type="number">` values should use regex when comparing to a
pre-formatted numeric string.

## 6. Streak accounting at M28 close

- **Zero-drift permission-class streak:** 27 → **28**
  consecutive milestones (M10 → M28). The M28.1 template
  endpoint reuses `_M131_PERMS` verbatim (POST + GET on the
  same URL via `@api_view(["GET","POST"])`); zero new
  permission classes.
- **Planning-time as-recommended streak:** 6 → **7** at
  M28.0 close (A locked as recommended after four
  alternatives presented + two architectural verifications
  + one durable refinement adopted from user pushback);
  unchanged through M28.1 + M28.2 (both pure implementation
  increments executing the M28.0 locked plan). Historical
  run of 89 across M10 → M23 preserved for the record.

## 7. Baselines at M28 close

- **Backend:** 4,855 pass, 1 skipped, 0 fail (164.1s).
- **Frontend Vitest:** 270 pass across 36 files.
- **Acceptance:** 19 journeys total; 22 tests passed / 3
  pre-existing shared-DB failures unchanged from M27.2
  close (Candidate H remediation, not M28 scope).
- **Audit:** 156 endpoints / 122 covered / 34 backend-only
  / 315 service verbs.
- **Migrations:** 0001–0050.
- **DRF admin surface:** 116 endpoints (+1 vs M27 close).
- **Frontend operator routes:** 20 unchanged.
- **Public endpoints:** +1 M6.5 showroom unchanged.
- **Permission classes:** 7 actual — zero-drift streak
  28 consecutive milestones (M10 → M28).
- **`Vehicle.is_available`:** unchanged.
- **AI safety stack:** 17 scrub stages unchanged.
- **Deterministic rules:** unchanged.
- `manage.py check` clean; `makemigrations --check
  --dry-run` clean; `redis-cli ping` PONG; `frontend tsc
  --noEmit` clean; `acceptance tsc --noEmit` clean.

## 8. Corrections (post-close)

None.

## 9. Evidence-based candidates for M29

**Elevated (strong recommendation strength for M29.0):**

- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28 deferral, unchanged). Requires SESSION-189-§3-
  style tracing at M29.0 open. Blast radius unknown.
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (M26/M27/M28 deferral). Likely `component_consumed`
  word-boundary defect. Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB
  non-idempotent journeys confirmed at M28.2 full-suite run
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow` trial-balance snapshot).
  Compound CI-stability value grows as suite grows.
- **NEW — Variable-amount templates.** Would relax the M28.1
  serializer's non-null `amount` constraint + add
  instantiation-prompt UI. **Zero DB migration** (schema
  reserved at M28.1). Direct operator gain for accounting
  staff posting depreciation, utilities, payroll accruals.
  Recorded in memory as the intended payoff of the M28 §5.b
  forward-compat design.
- **NEW — Template edit / delete UI.** Currently `is_active`
  exists at DB layer with no operator surface. If operator
  evidence supports mid-year chart-of-accounts edits or
  template deactivation, promote.

**Gated (unchanged from M28 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps); C (F&I chargeback substrate
  — would reuse M27.1 gl-accounts substrate).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M28 §3 (all valid for later re-entry):**

Named template variables (multi-line shared input);
historical-template back-reference on JournalEntry;
server-side template search / pagination;
`?include_inactive=true` endpoint exposure; save-as-template
checkbox on JE dialog (rejected in favor of dedicated
dialog); standalone template detail page.

**Deferred at M27 §3 + M25 §4 (all valid for later
re-entry):** carried forward unchanged.

**Standing question for M29:** should the substrate-integrity
audit-refinement candidates (O2 + O3) be spent together as a
single M29 milestone (M26-analogous), or should the
substrate-compound-value framing continue (variable-amount
templates would be the next operator-facing consumer of the
M28.1 substrate)? Evidence at M28 close does not force either
path — both are viable. The primary operational-coverage lens
would favor variable-amount templates (direct operator gain);
the substrate-integrity framing would favor O2+O3
(compound-infrastructure gain).
