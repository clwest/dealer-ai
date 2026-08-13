---
title: "Milestone 27 — Journal-Entry Creation UI (via shared GLAccount substrate)"
status: active
type: planning-memo
generated: 2026-08-03
generated_at_session: SESSION_191 (skeleton + expansion + all §5 locks)
milestone: 27
milestone_name: "Journal-Entry Creation UI (via shared GLAccount substrate)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_26_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_26_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7α
  - backend/dealer_ai/views_accounting.py
  - frontend/src/lib/accountingApi.ts
  - frontend/src/pages/AccountingJournalEntriesPage.tsx
  - frontend/src/pages/AccountingJournalEntryDetailPage.tsx
  - acceptance/journeys/office/accounting_je_reversal.spec.ts
---

# Milestone 27 — Journal-Entry Creation UI (via shared GLAccount substrate)

> **Active planning memo.** Drafted + expanded + all §5 locks
> at SESSION_191 M27.0 open.
>
> **§5.a locked at open** as **A2 — Journal-Entry creation UI**,
> under the *primary operational-coverage lens* that has governed
> §5.a selection since M22 close (durable). At M27.0 open,
> §7 intake+downstream verification revealed that the create
> endpoint (`admin/accounting/journal-entries/` — row 140,
> `defer-candidate-O2`) requires `lines: [{account_id, ...}]`
> — numeric GLAccount primary keys — while the frontend has
> **no GLAccount list endpoint, no `fetchGLAccounts` wrapper,
> and no chart-of-accounts picker anywhere**. The Trial Balance
> page (the closest existing surface) is activity-filtered and
> does not return `id`. A naive A2 scope would have shipped a
> form operators could not actually use — the exact intake gap
> §7 exists to catch (M24.1-open + M25.0 + SESSION_189 §3 +
> SESSION_190 §2 lineage).
>
> **The user's substrate-attachment rule (M27.0):** rather than
> ship a new standalone Chart of Accounts page as an M27.1
> operator surface, attach the picker to existing accounting
> navigation. Trial Balance stays unchanged. The GLAccount
> endpoint + wrapper are shipped as pure infrastructure at
> M27.1; operators encounter the CoA inside the M27.2 JE-create
> dialog picker (the natural point of need). This preserves
> the one-workflow-beats-two rule (M25.0 durable) and the
> preserve-existing-code rule (PROJECT_RULES §5).
>
> **M27 is deliberately scoped as two implementation
> increments + close-out.** M27.1 ships the tenant-scoped
> `GET admin/accounting/gl-accounts/` endpoint + `fetchGLAccounts`
> wrapper (no UI change; DoD exception path per M26 precedent).
> M27.2 ships the "+ New journal entry" dialog on the existing
> `AccountingJournalEntriesPage`, using the M27.1 substrate for
> the account picker, plus the Playwright journey extension
> covering both successful creation and cancellation-without-
> persistence.
>
> **`gl-accounts` is shared accounting infrastructure.** The
> endpoint + wrapper are deliberately generic (id + code + name
> + type; full CoA including zero-balance accounts). Every
> future accounting workflow that needs account selection
> (recurring journals, adjustments, budget uploads, statement
> reconciliation, F&I chargeback flows, period-open entries)
> reuses the same substrate. M27.1's operator gain is compound
> — it is not JE-only.
>
> **Coverage arithmetic at M27 close:** backend endpoints
> **154 → 155** (new gl-accounts). Row 140 flips
> `defer-candidate-O2 → covered` at M27.2. New gl-accounts
> row lands `covered` at M27.2 (M27.1 introduces the
> endpoint before the consumer exists; the row is expected
> `defer-candidate-O2` at M27.1 close and flips to `covered`
> at M27.2). Post-M27.2 target: **155 total / 121 covered /
> 34 backend-only** (119 → 121: +row 140 + gl-accounts).
>
> **Streak posture:** zero-drift permission-class streak
> preserved at **26 → 27** consecutive milestones (M10 → M27)
> — both new surfaces reuse `_M131_PERMS` per the accounting
> module's existing pattern; no permission classes evolve.
> Planning-time as-recommended streak enters M27 at **5** and
> is intended to reach **6** at M27.0 close.
>
> **The anchor business question** — *Can a dealership
> accountant originate a journal entry entirely through the
> shipped application?* — governs every M27 scope decision.
>
> Anchor cross-refs:
> - `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md` §9 — records
>   A2 elevated as the leading M27 §5.a candidate.
> - `docs/CAPABILITY_MATRIX.md` §7α — M26 audit-tooling
>   refinement; the corrected 119 / 154 baseline M27 opens on.
> - `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` row 140 —
>   the target row A2 flips.
> - Memory record
>   `feedback_verify_fk_discoverability_before_lock.md` —
>   the durable planning lesson surfaced at M27.0 §7
>   verification; governs future create/edit workflow scoping.
> - Memory record `feedback_one_workflow_over_two_overlapping.md`
>   — the durable rule that prevented a parallel Chart of
>   Accounts route at M27.1.
> - Memory record `feedback_preserve_existing_code.md` — the
>   rule that governed attaching the dialog to the existing
>   `AccountingJournalEntriesPage` rather than a new route.

## Guiding question (durable, per M22 close)

**Which candidate most increases operational coverage for a
dealership employee?**

**M27 answers directly under the primary lens.** A2 is
direct operator coverage: an accountant (or dealer_owner
persona wearing the accounting hat) can now originate a
journal entry through the shipped application instead of
asking backend or working through reversal-only edits.
Small user population × moderate frequency = real, bounded
operator gain — the exact shape the primary lens rewards.

## Preserve the M20–M26 operational contract (durable)

- **Zero-drift permission-class streak preserved.** M27
  reuses `_M131_PERMS` for both new surfaces (list + create
  are same tenant-admin trust boundary as retrieve / reverse
  / list). Intended posture at M27 close: **27 consecutive
  milestones (M10 → M27)**.
- **17-stage scrub stack unchanged.** M27 does not touch
  the LLM path.
- **Existing accounting response envelopes preserved.** The
  new endpoint follows the `cost_posting_failures` precedent
  (unpaginated collection wrapped as
  `{<resource>: {<items>: [...]}}`). No new envelope shape.
- **No new frontend operator routes.** JE origination attaches
  to the existing `/dealer-ai-accounting/journal-entries` route
  as a modal Dialog. Frontend operator routes stay at **20**.
- **Trial Balance unchanged.** No feature creep on a report page.
- **Append-only ledger discipline preserved.** M27 adds
  *create*, not *edit*. JE corrections continue to happen via
  the existing reverse-and-repost flow (M14.4).

## Guiding principle (substrate-attachment + shared accounting infrastructure)

Two rules govern M27's shape:

1. **Substrate-attachment (M27.0 §7 user direction).** Before
   creating a new accounting surface (page, route, navigation
   entry), verify that operators already navigate to the
   nearest equivalent. If so, attach the new workflow there
   rather than shipping a parallel route. §7 verification
   surfaced that the Trial Balance page is the operator's de
   facto CoA navigation, but its response shape (no `id`,
   activity-filtered) does not satisfy the JE-create picker's
   needs. Rather than modify Trial Balance (report semantics)
   or ship a parallel CoA page (competing entry point), M27.1
   ships a *silent* substrate endpoint and M27.2 attaches the
   dialog to the JE list page (the natural origination context
   for a JE).

2. **Shared accounting infrastructure (M27.0 user direction).**
   The `gl-accounts` endpoint is not JE-specific. It is
   deliberately generic — full CoA, id + code + name + type —
   so every future accounting workflow needing account
   selection reuses it. M27.1's operator gain compounds across
   the accounting roadmap.

## 0. Engineering practices to preserve from M2–M26

- **Tenant discipline.** New `admin/accounting/gl-accounts/`
  scopes strictly to `get_current_dealership(request)` (same
  pattern as `admin_journal_entry_list`). No cross-tenant
  reads possible; the endpoint returns only the current
  tenant's GLAccounts.
- **Money as Decimal-as-string on the wire.** Per M9.5 /
  M10.1 / M12 BHPH / M14 §5.c Option A. The gl-accounts
  endpoint does not return money (chart metadata only), but
  the create-JE payload passes `debit` / `credit` as strings
  per the existing `JournalEntryCreateRequestSerializer`
  contract.
- **DRF `@api_view` + `_M131_PERMS`.** New endpoint follows
  the accounting-module precedent verbatim.
- **Response envelope discipline.** `{<resource_plural>:
  {<items_key>: [...]}}` for unpaginated collections
  (matches `cost_posting_failures`). No flat-array
  responses; no new envelope shapes.
- **Regression-test coverage.** Every new endpoint ships
  with backend unit tests (positive + negative +
  cross-tenant + permission). Every new frontend wrapper
  ships with a component/hook vitest. Every new operator
  workflow ships with a Playwright journey per M21.0 §5.f
  DoD (§5.g details M27.1 exception path).
- **Repo baseline discipline.** Backend 4,805 → **≥4,805 +
  N** where N counts new tests (§5.c estimates N).
  Frontend Vitest 226 → **≥226 + N**. Acceptance 14 → 15
  or unchanged (depending on §5.d extend-vs-add decision).
- **Zero-drift permission classes.** No new permission
  class added; both new surfaces reuse `_M131_PERMS`.
- **No LLM-path change.** N/A.
- **Coordinated push at milestone close, not per
  increment.** Per M18 → M26 cadence.

## 1. Business questions this milestone answers

**Primary — governs §5.a.** *Can a dealership accountant
originate a journal entry entirely through the shipped
application?*

**Secondary questions M27 answers along the way:**

1. What is the operator's canonical origination context for
   a new JE? (Answered by §5.b: the existing
   `AccountingJournalEntriesPage` — the same page they use
   to browse posted JEs. One workflow, one entry point.)
2. What surface exposes the full chart of accounts for
   selection during origination? (Answered by §5.b M27.1:
   a new `GET admin/accounting/gl-accounts/` endpoint
   returning the full CoA including zero-balance accounts,
   consumed inside the M27.2 dialog picker.)
3. Does the picker require its own standalone browsing
   surface (route / page / navigation entry)? (Answered:
   **no.** The picker inside the create dialog IS the
   browsable CoA surface. Trial Balance remains the
   activity-oriented view. See §5.b out-of-scope.)
4. How does the create dialog surface validation
   feedback? (Answered by §5.c: inline dialog error banner
   for serializer 400s + 404s; client-side balanced-line
   check before submit; success indicator = list refetch +
   inline success badge on the list page per the M25.2
   durable "modal-attached + success badge > toast"
   pattern.)
5. How does the Playwright journey prove the workflow is
   operationally real? (Answered by §5.d: two test cases
   — successful create + cancel-without-persistence —
   both making business-outcome assertions via the admin
   API.)

## 2. What existing primitives extend

**Backend (extends `views_accounting.py`, `urls.py`, and
the accounting module's `services/accounting/`):**

- `views_accounting.py` — add `admin_gl_account_list` at
  M27.1. Same shape as `admin_journal_entry_list` (DRF
  `@api_view(["GET"])`, `permission_classes(_M131_PERMS)`,
  `get_current_dealership(request)` scoping). Returns a
  projection of every GLAccount for the current tenant.
- `services/accounting/` — add a small helper (probably
  `list_gl_accounts(dealership)`) or use ORM directly from
  the view. Consistent with the existing helper pattern in
  `journal.py`. Trade-off deferred to M27.1 open.
- `urls.py` — add one route:
  `path("admin/accounting/gl-accounts/",
  views_accounting.admin_gl_account_list,
  name="admin-gl-account-list")`.
- **Reuses without change** at M27.2: existing
  `admin_journal_entry_create` view (row 140 endpoint),
  its `JournalEntryCreateRequestSerializer`, and its
  `post_journal_entry` service. M27.2 adds no backend
  code; it wires the frontend to the pre-existing
  endpoint (which is exactly why row 140 flips → `covered`).

**Frontend (extends `accountingApi.ts` + existing
accounting pages):**

- `lib/accountingApi.ts` — add:
  - `GLAccount` type (id + code + name + type).
  - `fetchGLAccounts(): Promise<GLAccount[]>` wrapper.
  - `CreateJournalEntryPayload` type + `createJournalEntry`
    wrapper (at M27.2).
- `pages/AccountingJournalEntriesPage.tsx` — extend at M27.2
  with a "+ New journal entry" button in the page header
  (peer of the existing "Journal Entries" title). Button
  opens a modal `<Dialog>` (reuses the M14.4 pattern
  from `AccountingJournalEntryDetailPage.tsx`). No route
  change.
- **New component** at M27.2:
  `components/accounting/NewJournalEntryDialog.tsx` —
  the dialog contents (description field, posted_at field
  defaulting to today, lines table with dynamic add/remove
  rows, per-row `GLAccountPicker`, per-row debit/credit
  inputs, balance-check indicator, submit + cancel
  buttons).
- **New component** at M27.2:
  `components/accounting/GLAccountPicker.tsx` — a
  searchable single-select combobox (`shadcn/ui` `Command`
  or `Popover + Command`, following existing shadcn
  patterns in the codebase). Client-side filter matches
  against both `code` and `name`. Small enough to render
  the full CoA client-side (no server-side search
  endpoint needed).

**Tests (new dedicated files):**

- `backend/dealer_ai/tests/test_m27_gl_account_list.py` —
  M27.1 endpoint tests (positive: returns full tenant CoA
  sorted by code, includes zero-balance accounts; negative:
  cross-tenant isolation, permission enforcement,
  authentication required).
- `frontend/src/lib/accountingApi.gl_accounts.test.ts` —
  M27.1 wrapper vitest (response projection, error path).
- `frontend/src/components/accounting/GLAccountPicker.test.tsx`
  — M27.2 picker component test (search-by-code,
  search-by-name, selection, keyboard nav).
- `frontend/src/components/accounting/NewJournalEntryDialog.test.tsx`
  — M27.2 dialog test (open, fill, balance validation,
  submit → success, cancel → no side effects).
- `acceptance/journeys/office/accounting_je_create.spec.ts`
  OR extension of `accounting_workflow.spec.ts` — M27.2
  journey (two test cases per §5.d).
- **Existing** `test_m141_journal_entry_list_endpoint.py`,
  `test_m131_accounting_endpoint.py` — remain untouched.

**Artifact (regenerated, not hand-edited):**

- `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md` —
  regenerated at both M27.1 close and M27.2 close per
  §5.e discipline. Coverage arithmetic:
  - **M27.1 close:** 154 → 155 endpoints. New gl-accounts
    row disposition: `defer-candidate-O2` (endpoint exists,
    no consumer yet).
  - **M27.2 close:** row 140 → `covered` (JE-create dialog
    consumes the create endpoint). gl-accounts row →
    `covered` (JE-create dialog consumes `fetchGLAccounts`).
    Coverage 119 → 121 covered.

**Docs (update-in-place per DOC_GOVERNANCE):**

- `docs/CAPABILITY_MATRIX.md` §7 — add a §7β "M27 shipped
  surface" block noting the new gl-accounts endpoint +
  JE-create dialog + framing note about gl-accounts as
  shared accounting infrastructure.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — M27 entry in
  the shipped table.
- `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md` — NEW at
  M27 close per the standard retrospective shape.
- `00-START-NEXT-SESSION.md` — overwritten at M27 close
  with SESSION_194 priorities (M28 target selection).

## 3. What's NOT in this milestone (deferrals)

- **Standalone Chart of Accounts page / route / navigation
  entry.** Explicitly deferred per user direction at M27.0.
  The picker inside the M27.2 dialog IS the browsable CoA
  surface. Trial Balance remains the activity-oriented
  view. If operator evidence later demands a dedicated CoA
  browsing surface (e.g., accountants needing to review
  account definitions outside a JE workflow), it re-enters
  as a future candidate.
- **Trial Balance changes.** No modification to the TB
  page, its endpoint, or its response shape. Per the
  substrate-attachment rule, TB stays a report; JE
  origination attaches to the JE list page.
- **JE edit / update.** Journal entries remain an
  append-only ledger. Corrections continue to happen via
  the existing reverse-and-repost flow (M14.4). No `PATCH`
  or `PUT` on JEs.
- **JE templates / recurring journals.** Common in mature
  accounting products (template a recurring rent JE, post
  monthly). Real operator gain, but distinct workflow —
  re-enters as a separate M28+ candidate if evidence
  supports it.
- **`posted_by_user` override.** The create endpoint
  already sets `posted_by_user = request.user`. The
  dialog does not expose an override for the posting
  user — the authenticated operator IS the posting user.
- **Account-picker filtering beyond client-side text
  search.** No filter-by-type dropdown at M27.2 (all
  account types are selectable). If operator evidence
  surfaces friction (e.g., accountants routinely picking
  from only one or two types), a type filter re-enters
  as a small M28+ increment.
- **Server-side search on `gl-accounts`.** The full CoA is
  small (typically 20–100 accounts for an indie or
  small-franchise dealership) — client-side filter is
  sufficient. No `?search=` query param at M27.1.
- **Pagination on `gl-accounts`.** Full CoA is returned
  in a single response. If future dealerships have
  materially larger charts (>1000 accounts), pagination
  re-enters — but current data does not justify the
  substrate cost.
- **NEW row-5 public-fetch-helper regex refinement**
  (M26 deferral O2). Still deferred at M27 per user
  direction. Re-enters as an M28+ candidate.
- **NEW rows 1–4 plain-string-literal investigation**
  (M26 deferral O3). Still deferred at M27. Re-enters as
  an M28+ candidate.
- **Test-hygiene remediation (Candidate H).** Kept
  separate. M27 is customer-facing operator coverage;
  H is CI stability. Re-enters as an M28+ candidate.
- **All M25 §4 deferrals** — remain valid for later
  re-entry (secondary "+ Record test drive" launch point;
  clickable "Referred by" attribution navigation;
  named-platform webhook adapters; attribution rollups;
  vehicle-picker advanced filters).
- **Gated candidates T / U / L / M** — unchanged posture
  from M26 close.

**Playwright journey binding for DoD compliance (M27.1
exception path per M21.0 §5.f Option B):** M27.1 is a
pure backend + wrapper increment with no operator surface
change. Per the M26 precedent, infrastructure-only
increments may invoke the exception path — journey
coverage for the new endpoint lands at M27.2 via the
JE-create journey (which exercises the picker, which
exercises the wrapper, which exercises the endpoint).
§5.g documents this explicitly. **M27.2 is customer-
facing** and satisfies DoD directly via the journey
extension in §5.d.

## 4. What existing tests bind

- **Backend suite (4,805 pass, 1 skipped)** — M27 must
  hold this baseline. New tests added per §5.c:
  - M27.1: endpoint tests → **≥4,805 + ~5–7** at M27.1
    close.
  - M27.2: no new backend tests (M27.2 is frontend +
    Playwright).
- **Frontend Vitest (226 pass across 32 files)** —
  unchanged at M27.1. Extended at M27.2:
  - M27.1: wrapper vitest → **≥226 + ~2** at M27.1 close.
  - M27.2: picker + dialog vitests → **≥228 + ~10–15**
    at M27.2 close.
- **Acceptance (14 journeys, clean-DB dry-run ~30s)** —
  unchanged at M27.1. Extended at M27.2:
  - M27.2: one journey file with two test cases (success
    + cancel), extending the existing
    `accounting_workflow.spec.ts` OR added as peer
    `accounting_je_create.spec.ts`. Extend-vs-add
    decision deferred to M27.2 open. Preferred posture:
    **extend** to keep the office/accounting seed harness
    consolidated.
- **`test_m131_journal_entry_model.py`,
  `test_m141_journal_entry_list_endpoint.py`,
  `test_m141_journal_entry_list_service.py`,
  `test_m131_accounting_endpoint.py`,
  `test_m131_accounting_service.py`,
  `test_m151_sale_booking.py`,
  `test_m161_bhph_payment_gl.py`** — all remain untouched.
  M27 does not modify existing accounting behavior.
- **`AccountingJournalEntriesPage.test.tsx`,
  `AccountingJournalEntryDetailPage.test.tsx`,
  `AccountingTrialBalancePage.test.tsx`** — remain
  untouched at M27.1. Extended at M27.2 (`AccountingJournalEntriesPage.test.tsx`
  gains a "+ New journal entry" button assertion + a
  dialog-opens-on-click assertion).

## 5. Load-bearing decisions

### §5.a — Milestone target selection

**LOCKED at M27.0 open as A2 — Journal-Entry creation
UI**, under the primary operational-coverage lens.

**Independent recommendation rationale (SESSION_191 §4–§5):**
Under the durable operational-coverage guiding question,
four candidates were elevated at M27.0 open — A2 (JE
creation UI, direct operator gain), O2 (row-5 public-fetch-
helper regex refinement, substrate), O3 (rows-1–4
plain-string investigation, substrate), and H (test-
hygiene, CI stability). The AI's independent recommendation
was A2 under the primary lens, with three grounds: (a)
direct operator-facing coverage gain in a known scope,
(b) O2/O3 require SESSION-189-§3-style tracing before
they can be scope-locked (pushing real ship work into
planning ambiguity), and (c) M26 already spent a bounded
substrate-integrity milestone — back-to-back substrate
work without positive evidence of active mis-selection
risk consumes operator-facing momentum.

The user confirmed the recommendation.

**§7 verification then surfaced the GLAccount FK intake
gap** — the create endpoint takes numeric primary keys with
no discovery surface. The user directed the substrate-
attachment response: split M27 into two increments (M27.1
backend substrate + M27.2 create UI), attach the dialog to
the existing JE list page, do not ship a standalone CoA
page. The user also directed that gl-accounts be recorded
as shared accounting infrastructure for future workflows,
not JE-only.

**Streak accounting (see §8):** locked as recommended
after alternatives presented + §7 substrate-scope
adjustment applied without shifting the target →
planning-time as-recommended streak increments **5 → 6**
at M27.0 open.

### §5.b — Scope split (M27.1 substrate + M27.2 create UI)

**LOCKED as a two-increment split with the substrate
strictly M27.1 and the operator surface strictly M27.2.**

**M27.1 — Backend substrate + frontend wrapper.**

- **New backend endpoint:** `GET admin/accounting/gl-accounts/`
  - Tenant-scoped: `get_current_dealership(request)` per
    the accounting-module pattern.
  - Permission: `_M131_PERMS` (reused; zero-drift preserved).
  - Returns the **full chart of accounts** for the current
    tenant, **including zero-balance accounts** (unlike
    the Trial Balance, which activity-filters).
  - Fields per account: `id`, `code`, `name`, `type`
    (one of `asset` / `liability` / `equity` / `revenue`
    / `expense`).
  - Sort order: `code` ascending (matches accounting
    convention — chart of accounts is naturally
    code-sorted).
  - No pagination (see §3 for justification).
  - No server-side search (see §3 for justification).
- **New frontend wrapper:** `fetchGLAccounts` in
  `lib/accountingApi.ts`.
- **No UI change at M27.1.** No new component, no
  modification to any existing accounting page.
- **DoD exception path** invoked per §5.g.
- **`gl-accounts` framing (M27.0 user direction):** the
  endpoint + wrapper are **shared accounting
  infrastructure**, not JE-specific. Future accounting
  workflows needing account selection (recurring
  journals, adjustments, budget uploads, statement
  reconciliation, F&I chargeback flows, period-open
  entries) reuse the same substrate. Recorded in
  CAPABILITY_MATRIX §7β at M27 close.

**M27.2 — JE-create dialog on the existing JE list page.**

- **Entry point:** a "+ New journal entry" button in the
  header of `AccountingJournalEntriesPage`
  (`/dealer-ai-accounting/journal-entries`). Peer of the
  page title. **No new frontend route.**
- **Dialog:** modal `<Dialog>` (shadcn/ui) reusing the
  M14.4 reversal-dialog pattern from
  `AccountingJournalEntryDetailPage.tsx`. New component
  file: `components/accounting/NewJournalEntryDialog.tsx`.
- **Dialog fields:**
  - `description` — text input, required, non-empty.
  - `posted_at` — date input, **defaults to today's
    date** (client-side `new Date()`), operator can edit.
  - `lines[]` — dynamic table:
    - Two lines default (one debit-side placeholder, one
      credit-side placeholder), minimum enforced at 2.
    - Per-row: `account_id` (via `GLAccountPicker`),
      `debit` (numeric input), `credit` (numeric input),
      `memo` (text input, optional).
    - "+ Add line" button appends a new blank row.
    - "− Remove" button per row (disabled when only 2
      lines remain).
- **`GLAccountPicker` component:** new file
  `components/accounting/GLAccountPicker.tsx`. Searchable
  single-select combobox (shadcn `Command` /
  `Popover + Command` per existing shadcn patterns in
  the codebase). Client-side filter matches against both
  `code` (e.g., "1010") **and** `name` (e.g., "Cash").
  Selected value displayed as `"{code} — {name}"`.
- **Client-side balance indicator:** a live-computed
  `Σ debits === Σ credits` check displayed as a badge
  in the dialog footer (green "Balanced" / red
  "Unbalanced by $X.XX"). Submit button disabled unless
  balanced + description non-empty + all lines have
  a picked account + each line has non-zero on exactly
  one side.
- **Submit:** invokes new `createJournalEntry` wrapper →
  `POST admin/accounting/journal-entries/`. On 201,
  dialog closes, list refetches, inline success badge
  appears on the list page (M25.2 durable pattern:
  "modal-attached success badge > toast"). On 4xx,
  inline error banner inside the dialog with the
  serializer detail; dialog stays open for correction.
- **Cancel:** dialog closes without side effects. No
  confirmation prompt at M27.2 (dialog state is
  ephemeral; if operator loses work, they re-open and
  re-type).
- **Row 140 flips → `covered`** at M27.2 audit regen.
  gl-accounts row also flips → `covered` at M27.2 regen
  (the picker consumes `fetchGLAccounts`).

**Out of scope for §5.b (also enumerated in §3):**

- Standalone Chart of Accounts page / route / nav entry.
- Trial Balance changes.
- JE edit / update endpoints.
- JE templates / recurring journals.
- `posted_by_user` override in the dialog.
- Account-picker filtering beyond client-side text search.
- Server-side search or pagination on `gl-accounts`.
- Any change to existing accounting endpoints, serializers,
  services, or pages beyond the M27.2 button addition on
  `AccountingJournalEntriesPage`.

### §5.c — Interface + payload contract

**LOCKED to match the existing accounting API response
envelope convention (verified at M27.0 §5.c open).**

**M27.1 `GET admin/accounting/gl-accounts/` response
(follows `cost_posting_failures` precedent —
unpaginated-collection envelope):**

```json
{
  "gl_accounts": {
    "accounts": [
      {"id": 1, "code": "1010", "name": "Cash — Operating", "type": "asset"},
      {"id": 2, "code": "1020", "name": "Cash — Petty",     "type": "asset"},
      {"id": 3, "code": "4010", "name": "Vehicle Sales — Retail", "type": "revenue"},
      ...
    ]
  }
}
```

- HTTP 200 always for authenticated in-tenant requests
  (empty `accounts` array is possible but not expected
  for real dealerships).
- HTTP 401 / 403 per standard DRF permission handling.
- Sort: `code` ASC.

**M27.1 frontend wrapper:**

```ts
export type GLAccountType =
  | "asset" | "liability" | "equity" | "revenue" | "expense";

export interface GLAccount {
  id: number;
  code: string;
  name: string;
  type: GLAccountType;
}

interface GLAccountListResponse {
  gl_accounts: { accounts: GLAccount[] };
}

export function fetchGLAccounts(): Promise<GLAccount[]> {
  return authGetJSON<GLAccountListResponse>(
    "/admin/accounting/gl-accounts/",
  ).then((body) => body.gl_accounts.accounts);
}
```

Note the deliberate reuse of the existing `GLAccountType`
alias already exported by `accountingApi.ts` (from the
M14 trial-balance types) — no duplicate type declaration.

**M27.2 `createJournalEntry` payload** matches the
existing `JournalEntryCreateRequestSerializer` contract
(verified against `views_accounting.py` line 158–205):

```ts
export interface CreateJournalEntryLine {
  account_id: number;
  debit: string;   // Decimal-as-string per §5.c Option A
  credit: string;  // Decimal-as-string per §5.c Option A
  memo?: string;
}

export interface CreateJournalEntryPayload {
  description: string;
  posted_at?: string;  // ISO 8601; defaults server-side when omitted
  lines: CreateJournalEntryLine[];
}

export function createJournalEntry(
  payload: CreateJournalEntryPayload,
): Promise<JournalEntry> {
  return authPostJSON<JournalEntryDetailResponse>(
    "/admin/accounting/journal-entries/",
    payload,
  ).then((body) => body.journal_entry);
}
```

- HTTP 201 on success; response envelope
  `{"journal_entry": {...projection...}}` (existing
  server envelope; reused from `reverseJournalEntry`).
- HTTP 400 for `EmptyJournalEntryError`,
  `InvalidJournalLineError`,
  `UnbalancedJournalEntryError`, or invalid line
  payload — `{"detail": "..."}`.
- HTTP 404 for `CrossTenantGLAccountError` (picked an
  account the current tenant cannot see) —
  `{"detail": "GLAccount not found."}`.

**Client-side validation (in `NewJournalEntryDialog`):**

- `description` non-empty (trimmed).
- ≥2 lines (enforced by minimum-row constraint).
- Every line has a picked `account_id`.
- Every line has non-zero on **exactly one side** (i.e.
  `(debit > 0 AND credit == 0) OR (debit == 0 AND
  credit > 0)`).
- `Σ debits === Σ credits` (balanced).

Submit button disabled unless all five conditions hold.

**Error surfaces in the dialog:**

- Client validation failures: inline per-field or
  per-row error messages; balance indicator badge
  displays specific delta.
- Server 400: inline dialog error banner with the
  serializer `detail` string; dialog stays open.
- Server 404 (cross-tenant GLAccount): inline dialog
  error banner with a friendlier phrasing ("Account
  not available; refresh and try again."); dialog
  stays open.
- Network / other: generic inline error banner
  ("Failed to create journal entry. Try again.");
  dialog stays open.

**Success surface:**

- Dialog closes on 201.
- List refetches (`fetchJournalEntries` on the parent
  page).
- Inline success badge on the list page:
  `"Journal Entry #{id} posted"` with a subtle
  auto-dismiss after ~5s (matches the M25.2
  success-badge pattern; details TBD at M27.2 open).

### §5.d — Playwright verification protocol

**LOCKED as two test cases in a single spec (per user
direction at M27.0), covering both successful creation
AND cancellation-without-persistence.**

**Extend-vs-add decision:** deferred to M27.2 open.
Preferred posture is **extend** `accounting_workflow.spec.ts`
(the M20.3 + M22.2 substrate) to keep the office/accounting
seed harness consolidated. If the shape doesn't fit
cleanly, add peer `accounting_je_create.spec.ts` following
the M22.2 `accounting_je_reversal.spec.ts` pattern.

**Test case 1 — Successful create:**

1. Owner navigates to `/dealer-ai-accounting/journal-entries`.
2. Owner clicks "+ New journal entry" — dialog opens.
3. Owner types a description with the M27 fixture prefix
   (`[M27.2-office-je-create] ...`).
4. Owner confirms the `posted_at` field defaults to
   today's date (assertion: value ≈ today).
5. Owner clicks the first line's account picker, types
   part of an account **code** (e.g., "1010"), selects
   the resulting Cash account.
6. Owner clicks the second line's account picker, types
   part of an account **name** (e.g., "Sales"), selects
   the resulting Vehicle Sales — Retail account. **Both
   search modes exercised.**
7. Owner enters balanced amounts (debit $250 on line 1,
   credit $250 on line 2).
8. Owner asserts balance badge reads "Balanced".
9. Owner clicks "Create journal entry" — dialog closes.
10. List page shows the new entry as the top row; inline
    success badge visible for the newly-posted id.
11. Owner opens detail page — confirms description +
    lines + account codes render correctly.
12. **Business-outcome assertion via admin API:** entry
    exists with the expected description prefix,
    balanced (`is_balanced` true), correct `account_id`s
    and amounts on lines.

**Test case 2 — Cancel without persistence:**

1. Owner navigates to `/dealer-ai-accounting/journal-entries`.
2. Owner records the current `total_count` from the list
   header (baseline for the no-persistence assertion).
3. Owner clicks "+ New journal entry" — dialog opens.
4. Owner types a description with a distinct cancel-test
   fixture prefix (`[M27.2-cancel-test] ...`).
5. Owner picks one account + enters one amount (partial
   form; deliberately not enough to submit).
6. Owner clicks Cancel — dialog closes with no
   confirmation prompt.
7. List page `total_count` unchanged (assertion equals
   step-2 baseline; may need a brief `await` for React
   settle).
8. **Business-outcome assertion via admin API:** no
   entry with the cancel-test description prefix exists
   in the current tenant's JE list. Persistence never
   happened.

**Seed data:** extend
`seed_journey_office_accounting_workflow` (already
provisioned by M20.3 + M22.2) to guarantee ≥2 GLAccounts
of appropriate types (asset + revenue; the M13
accounting substrate seed likely already covers this).
Confirm at M27.2 open; augment the management command
only if the existing seed is insufficient.

**Cross-test isolation:** the two test cases use distinct
description prefixes; each asserts against its own
prefix. Both test cases can run in either order without
interference.

**Guiding principle (per M22.2 §5.f Option B):** the
journey is the operational contract. If the shipped
surface cannot complete either workflow, the test fails
loudly and §5.d gap-handling applies at close.

### §5.e — Coverage-baseline update discipline

**LOCKED as the two-source agreement discipline
inherited from M26 §5.e, applied at each M27 increment
close.**

**At M27.1 close, audit regeneration expected diff:**

- Backend endpoints: **154 → 155** (new gl-accounts row).
- New gl-accounts row disposition: **`defer-candidate-O2`**
  (endpoint exists; no consumer wrapper referenced from a
  non-test frontend file yet — the M27.1 wrapper exists
  but is not called anywhere until M27.2).
- Coverage summary: **119 / 155** covered (119 unchanged;
  denominator +1).
- Backend-only: 35 → 36.
- Service verbs: 312 → 312 + N (small).
- All other rows unchanged.

**At M27.2 close, audit regeneration expected diff:**

- Row 140 (`admin/accounting/journal-entries/` create):
  populated with `accountingApi.ts:XXX createJournalEntry`;
  disposition flips → **`covered`**.
- New gl-accounts row: populated with `accountingApi.ts:XXX
  fetchGLAccounts`; disposition flips → **`covered`**.
- Coverage summary: **119 → 121 covered / 155 total**.
- Backend-only: 36 → 34.
- All other rows unchanged.

**Two-source agreement (M26 §5.e discipline preserved):**

Before recording the corrected baseline at any M27
increment close, BOTH of the following must agree:

1. **Regenerated artifact.** Refreshed
   `M21_OPERATIONAL_SURFACE_AUDIT.md` reflects the
   expected numeric diffs above.
2. **Direct repository inspection.** The wrappers named
   in the diff exist at the reported `{filename}:{line}`,
   with correct HTTP helper, and are imported and called
   by at least one non-test `.tsx` or `.ts` component
   under `frontend/src/`.

If either source disagrees, the baseline is NOT
updated — halt the close-out, document the discrepancy,
treat as a §5.b implementation gap.

**Recording sites at M27 close (in order):**

- `docs/CAPABILITY_MATRIX.md` §7β block.
- `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md` §1 shipped
  scope summary + §2 quantitative surface deltas.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` M27 row.
- `docs/handoffs/SESSION_NNN_m27_close.md` frontmatter +
  baseline block.
- `00-START-NEXT-SESSION.md` operational-state block.

### §5.f — Increment shape

**LOCKED as 2 implementation increments + close-out,
with close-out folding into M27.2 per §5.h Option B
unless evidence forces a split.**

- **M27.0 — Planning refinement + target selection
  (this session, SESSION_191).** Locks all §5 decisions.
  Ships the M27 memo + the SESSION_191 handoff. **No
  code, no push.**
- **M27.1 — Backend substrate + frontend wrapper
  (SESSION_192).** Ships `GET admin/accounting/gl-accounts/`
  + `fetchGLAccounts`. Backend tests + wrapper vitest.
  Docs update: CAPABILITY_MATRIX §7β (M27.1 partial).
  **No UI, no journey.** DoD exception path per §5.g.
  **~1 session.**
- **M27.2 — JE-create dialog + Playwright journey
  (SESSION_193).** Ships "+ New journal entry" button +
  `NewJournalEntryDialog` + `GLAccountPicker` +
  `createJournalEntry` wrapper + component vitests +
  journey extension. Docs update: CAPABILITY_MATRIX §7β
  (M27.2 complete). **~1 session.**
- **M27.3 — Close-out** (retrospective + coordinated
  push). **Folds into M27.2 close per §5.h Option B
  unless verification surfaces §5.e discrepancies at
  either increment.**

**Total: 2–3 sessions.** M27 is intentionally larger
than M26 (which was audit-tooling-only) because M27
delivers a genuine operator-facing workflow. Still
well under the M18 → M25 velocity envelope.

### §5.g — DoD compliance (M21.0 §5.f exception path for M27.1 only)

**LOCKED with the exception path explicitly invoked for
M27.1 and satisfied directly at M27.2.**

Per the M21.0 §5.f Option B DoD amendment: every future
customer-facing milestone must add or update at least
one Playwright operational journey, OR explicitly
document in §3 why no journey change is required.

**M27.1 is an infrastructure-only increment.** No
operator surface changes. The new gl-accounts endpoint
has no consumer until M27.2 lands. Per the M26
precedent (audit-tooling refinement invoked the same
exception path), M27.1 documents the exception here in
§5.g and mirrors it in §3 (deferrals-for-this-increment)
and the M27.1 retrospective §journey-plan section. The
new endpoint's operational journey coverage arrives at
M27.2 via the JE-create journey.

**M27.2 is customer-facing** and satisfies DoD
directly. The Playwright journey per §5.d covers both
the successful-create and cancel-without-persistence
paths — exercising the button + dialog + picker +
`fetchGLAccounts` wrapper + `createJournalEntry`
wrapper + the create endpoint + the list refetch + the
detail page in a single end-to-end assertion.

### §5.h — Close-out posture

**LOCKED as evidence-sized Option B (per M18 → M26
precedent).**

If M27.2 ships cleanly — backend green, frontend green,
journey green, both increments' audit regenerations
produce exactly the expected coverage diffs per §5.e,
docs update-in-place with no anomalies — **fold the
close-out into the M27.2 session** (retrospective +
coordinated push in the same session). Otherwise
promote to a separate M27.3 close-out session.

Push executes **once**, at the end of the milestone,
per M18 → M26 cadence. No per-increment pushes.

**Expected commit count:**

- **6 folded:** M27.0 planning + M27.0 hash backfill +
  M27.1 implementation + M27.1 hash backfill + M27.2
  implementation & close + M27.2 hash backfill.
- **8 split:** add M27.3 close-out commit + hash
  backfill.

## 6. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_26_RETROSPECTIVE.md` §5 (durable
   lessons) + §9 (M27 evidence — A2 elevated)
6. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (current 119 / 154 baseline; source of truth pre-M27)
7. `docs/CAPABILITY_MATRIX.md` §7z (M25 shipped surface)
   + §7α (M26 audit refinement) + §7β (M27 shipped
   surface, added at close)
8. `backend/dealer_ai/views_accounting.py` (existing
   accounting-module patterns — permission classes,
   tenant scoping, response envelopes)
9. `frontend/src/lib/accountingApi.ts` (existing wrapper
   conventions — envelope projection, Decimal-as-string)
10. `frontend/src/pages/AccountingJournalEntryDetailPage.tsx`
    (M14.4 reversal-dialog pattern — the template for
    the M27.2 create dialog)
11. `acceptance/journeys/office/accounting_je_reversal.spec.ts`
    (M22.2 journey pattern — the template for the M27.2
    journey)
12. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (durable planning lesson surfaced at M27.0 §7 —
    governs future create/edit workflow scoping)
13. Memory record `feedback_one_workflow_over_two_overlapping.md`
    (durable rule preventing parallel CoA route at M27.1)
14. Memory record `feedback_preserve_existing_code.md`
    (durable rule attaching M27.2 dialog to existing
    JE list page rather than a new route)

## 7. Sequencing

**M27.0 (SESSION_191, this session)** — planning
refinement + target selection + all §5 locks. Ships
memo + handoff. No code, no push.

**M27.1 (SESSION_192)** — backend substrate + wrapper.
In order:

1. Verify M26 close baseline holds (backend 4,805 pass,
   frontend 226 pass, acceptance 14 journeys clean-DB,
   audit 119 / 154, HEAD at `a277ab8` or later, redis
   PONG).
2. Regenerate audit to confirm 119 / 154 still holds.
3. Draft the new endpoint's serializer (probably
   inline in `views_accounting.py` following the
   existing pattern; no separate `serializers.py` file
   change unless the accounting module already has one).
4. Implement `admin_gl_account_list` view (DRF
   `@api_view(["GET"])`, `_M131_PERMS`, tenant scoping,
   sorted-by-code projection).
5. Wire `urls.py` route.
6. Write `test_m27_gl_account_list.py` backend tests
   (positive: full CoA sorted; zero-balance included;
   negative: cross-tenant isolation; permission
   enforcement; unauthenticated 401/403).
7. Run `python3 manage.py test dealer_ai` — assert
   green (4,805 → ~4,810–4,812).
8. Add `fetchGLAccounts` + `GLAccount` type +
   `GLAccountListResponse` interface in `accountingApi.ts`.
9. Write `accountingApi.gl_accounts.test.ts` vitest.
10. Run `npm test` — assert green (226 → ~228).
11. Regenerate audit; assert exactly the expected diff
    per §5.e M27.1 (154 → 155; new row
    `defer-candidate-O2`).
12. §5.e Phase 2 per-row verification for the new row
    (endpoint file:line correct; view symbol matches;
    permissions match).
13. Update `docs/CAPABILITY_MATRIX.md` §7β with the
    M27.1 partial shipped surface.
14. Draft M27.1 handoff `docs/handoffs/SESSION_192_m27_inc1_
    substrate.md`.
15. Coordinated push (M27.1 commit + hash backfill).

**M27.2 (SESSION_193)** — JE-create dialog + Playwright.
In order:

1. Verify M27.1 close baseline holds (backend ~4,810
   pass, frontend ~228 pass, acceptance 14 journeys
   clean-DB, audit 119 / 155 with gl-accounts row at
   `defer-candidate-O2`, HEAD at M27.1 close commit).
2. Add "+ New journal entry" button to
   `AccountingJournalEntriesPage` header.
3. Implement `NewJournalEntryDialog` component
   (description + posted_at defaulting to today +
   dynamic lines table + balance indicator + submit/cancel).
4. Implement `GLAccountPicker` component (shadcn
   Command combobox; client-side filter by code AND
   name; displays `"{code} — {name}"`).
5. Add `createJournalEntry` wrapper + payload types in
   `accountingApi.ts`.
6. Write component vitests (`GLAccountPicker.test.tsx`,
   `NewJournalEntryDialog.test.tsx`; extend
   `AccountingJournalEntriesPage.test.tsx`).
7. Run `npm test` — assert green (~228 → ~240).
8. Confirm seed
   `seed_journey_office_accounting_workflow` provides
   ≥2 GLAccounts of appropriate types; augment if
   needed.
9. Extend `accounting_workflow.spec.ts` (preferred) or
   add peer `accounting_je_create.spec.ts` with two
   test cases per §5.d.
10. Run acceptance suite; assert both test cases green.
11. Run `python3 manage.py test dealer_ai` — assert
    baseline holds (no backend changes at M27.2).
12. Regenerate audit; assert exactly the expected diff
    per §5.e M27.2 (row 140 → `covered`; gl-accounts
    row → `covered`; coverage 119 → 121).
13. §5.e Phase 2 per-row verification for both flipped
    rows.
14. Update `docs/CAPABILITY_MATRIX.md` §7β (M27.2
    complete).
15. Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` M27
    entry.
16. Draft `docs/roadmap/MILESTONE_27_RETROSPECTIVE.md`.
17. Overwrite `00-START-NEXT-SESSION.md` with
    SESSION_194 priorities (M28 target selection).
18. Compose M27.2 handoff
    `docs/handoffs/SESSION_193_m27_close.md` (or split
    if §5.h evidence forces).
19. Coordinated push (all M27 commits + hash backfills).

**M27.3 (SESSION_194, only if split)** — close-out.
Retrospective + coordinated push of any deferred M27
work.

## 8. Streak accounting (M27)

- **Zero-drift permission-class streak** — enters M27 at
  **26 consecutive milestones (M10 → M26)**. M27 reuses
  `_M131_PERMS` for both new surfaces (list + create);
  no permission classes evolve. Intended posture at M27
  close: extend to **27 consecutive milestones (M10 →
  M27)**.
- **Planning-time as-recommended streak** — enters M27
  at **5** (M25.0 + M25.1 + M25.2 + M26.0 + M26.1 all
  locked as recommended, with M26.1 counted per the
  empirical-discovery-refinement precedent). Historical
  run of 89 across M10 → M23 preserved for the record.
  M27.0 opens with an AI recommendation of A2 under the
  primary operational-coverage lens; the user confirmed
  the recommendation, and the §7 substrate-attachment
  adjustment refined the scope shape (split into
  M27.1/M27.2, no standalone CoA page) without shifting
  the target. Per the empirical-discovery precedent
  (M25.0 + M25.2-open + M26.1-open + SESSION_189 §3),
  scope refinements that narrow evidence without
  changing the selected target still count as
  as-recommended. **M27.0 counts as as-recommended →
  streak increments 5 → 6.**

## 9. Non-goals for the remaining M27 increments

- ❌ Do NOT create a standalone Chart of Accounts page,
  route, or navigation entry. §5.b out-of-scope; §3
  deferrals; per user direction at M27.0.
- ❌ Do NOT modify the Trial Balance page, endpoint, or
  response shape. TB stays a report; JE origination
  attaches to the JE list page.
- ❌ Do NOT add JE edit / update endpoints. Corrections
  continue via reverse-and-repost (M14.4).
- ❌ Do NOT ship JE templates or recurring-journal
  workflows at M27. Real operator value, but distinct
  scope; separate M28+ candidate.
- ❌ Do NOT expose a `posted_by_user` override in the
  dialog. Authenticated operator IS the posting user.
- ❌ Do NOT add server-side search or pagination on
  `gl-accounts` at M27.1. Full CoA is small; client-side
  filter is sufficient.
- ❌ Do NOT add filter-by-type or other advanced picker
  controls at M27.2. Text search over code + name is
  sufficient; advanced controls re-enter on operator
  evidence.
- ❌ Do NOT investigate the M26-deferred row-5 public-
  fetch-helper regex defect (O2) or the rows-1–4
  plain-string-literal false positives (O3). Both remain
  M28+ candidates.
- ❌ Do NOT combine test-hygiene (Candidate H) into M27.
  Kept separate; M27 is customer-facing, H is CI stability.
- ❌ Do NOT hand-edit `M21_OPERATIONAL_SURFACE_AUDIT.md`.
  Regenerate only.
- ❌ Do NOT record the M27.1 or M27.2 coverage baselines
  without both §5.e sources agreeing.
- ❌ Do NOT push per-increment. Coordinated push at M27
  close per §5.h.
- ❌ Do NOT skip either Playwright test case at M27.2.
  Both successful-create AND cancel-without-persistence
  are required per §5.d.
- ❌ Do NOT skip the §5.e Phase 2 per-row manual
  verification at either M27.1 or M27.2 close. The M25.3
  → SESSION_189 §3 → SESSION_190 §2 lineage is the
  load-bearing evidence that regeneration alone is
  insufficient.
- ❌ Do NOT let M27 broaden into a general "accounting
  workflows" milestone. The JE-create workflow is
  precisely scoped; adjacent workflows (recurring
  journals, adjustments, budgets, statement recon, F&I
  chargebacks) are M28+ candidates with their own
  evidence requirements — even though they will reuse
  the M27.1 gl-accounts substrate.
