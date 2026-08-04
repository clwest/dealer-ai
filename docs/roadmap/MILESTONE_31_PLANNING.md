---
title: "Milestone 31 — Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
status: active
type: planning-memo
generated: 2026-08-04
generated_at_session: SESSION_203 (skeleton + expansion + all §5 locks)
milestone: 31
milestone_name: "Journal-Entry Template Restore / \"Show inactive\" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_28_PLANNING.md
  - docs/roadmap/MILESTONE_29_PLANNING.md
  - docs/roadmap/MILESTONE_30_PLANNING.md
  - docs/roadmap/MILESTONE_30_RETROSPECTIVE.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7ε
  - backend/dealer_ai/models.py (JournalEntryTemplate, JournalEntryTemplateLine — unchanged since M28.1)
  - backend/dealer_ai/services/accounting/template.py (M30.1 include_inactive kwarg on list + get)
  - backend/dealer_ai/views_accounting.py (M30.1 detail endpoint + list endpoint that does not yet expose include_inactive)
  - backend/dealer_ai/urls.py (M30.1 detail URL pattern — Restore adds one sibling)
  - frontend/src/components/accounting/JournalEntryTemplateDialog.tsx (M30.2 renamed dialog with additive mode props)
  - frontend/src/pages/AccountingJournalEntriesPage.tsx (M30.2 row-level Edit + Delete; shipped Restore-promise copy at lines 668-672)
  - frontend/src/lib/accountingApi.ts (M30.2 update/delete wrappers)
  - acceptance/journeys/office/accounting_je_template.spec.ts (M30.2 edit-delete describe block)
---

# Milestone 31 — Journal-Entry Template Restore / "Show inactive" UI (lifecycle-completion on M28.1 substrate + M30.1 include_inactive kwarg)

> **Active planning memo.** Drafted + expanded + all §5 locks at
> SESSION_203 M31.0 open.
>
> **§5.a locked at open** as **NEW Restore / "Show inactive"
> templates UI (lifecycle-completion)**, under the *primary
> operational-coverage lens* (durable since M22 close) evaluated
> as a lifecycle-completion workflow per explicit user direction —
> **not** as UI polish and **not** solely as a
> substrate-compound-value continuation. Restore was recommended
> and confirmed because it is the only candidate on the M31 board
> that closes a shipped-surface operator-safety promise
> (`AccountingJournalEntriesPage.tsx:670-672` shipped M30.2 copy
> reads verbatim: *"You can restore this template later. (Restore
> UX ships in a future milestone.)"*) AND removes a real
> "backend intervention required" operational blocker (today the
> only way to un-hide a soft-deleted template is Django shell).
>
> **The anchor business question** — *Can a dealership accountant
> safely view previously deactivated journal-entry templates,
> understand their status, and restore one to active use — without
> engineering intervention — while existing journal entries and
> reports remain completely unaffected?* — governs every M31 scope
> decision.
>
> **Lifecycle-integrity precheck performed at planning-open** (per
> user direction, before locking §5.b): current-state trace of the
> instantiate flow confirmed instantiation is purely client-side
> hydration (`AccountingJournalEntriesPage.tsx:271` `handleInstantiate`
> copies `template.description` + lines + lock config into React
> state; the JE that gets POSTed via `createJournalEntry` does not
> carry the template pk). There is no server "instantiate"
> endpoint that could check `template.is_active`. Consequences
> recorded as **L1 lifecycle-integrity guard** — the smallest
> fail-closed fix is a frontend button-disable on inactive rows;
> a server guard would have nothing to check because JE and
> JournalEntryTemplate are intentionally decoupled (M28.0 §5.b +
> M30.0 §4.7). See §4.1 and §5.b D7.
>
> **Substrate readiness verification.** Both `get_journal_entry_template`
> and `list_journal_entry_templates` already accept
> `include_inactive: bool = False` kwarg (M30.1 —
> `services/accounting/template.py:270-282` + `285-315`). Neither
> endpoint currently exposes the kwarg. Restore UI unblocks with
> one endpoint addition + one one-line view-layer extension +
> zero new migration.
>
> **Fifth link in the substrate-compound-value lineage** (M27.1
> gl-accounts → M28.1 template substrate → M29 variable-amount
> extension → M30 template CRUD closure → **M31 template
> lifecycle closure**). This framing is *supporting*, not
> *load-bearing*, on the §5.a selection per explicit user
> guidance — Restore stands under the primary operational-
> coverage lens alone.

## 0.a Change log (implementation-time amendments)

Per M5–M30 §9 mandates, load-bearing planning decisions may need
narrow amendment at implementation time as substrate reality
asserts itself. Every amendment records the session, option, and
the affected sections.

_None yet at M31.0._

## 1. Context

### 1.1 Why now

Two forces converge to make lifecycle-completion the highest-
value bounded M31 target:

1. **M30.2 shipped a copy promise that the shipped surface does
   not yet fulfill.** The delete confirmation dialog at
   `AccountingJournalEntriesPage.tsx:670-672` reads verbatim:
   *"You can restore this template later. (Restore UX ships in a
   future milestone.)"* Every operator who deactivates a
   template today reads this promise and — because M30 shipped
   no Restore surface — either discovers the gap themselves or
   escalates to engineering. This is an integrity gap on
   shipped customer-facing surface, not a missing polish.
2. **Backend intervention is currently the only path to
   restore a deactivated template.** The service layer verb
   `get_journal_entry_template` defaults `include_inactive=False`,
   so a soft-hidden row is invisible to every consumer that
   uses the default posture — including any hypothetical
   Restore UI that would need to discover the pk to un-hide.
   The M30.1 kwarg (`include_inactive: bool = False`) provides
   the substrate for discovery, but no endpoint currently
   surfaces it. Operators who need to un-hide a template today
   need Django-shell access. Colloquially: the M30 shipped
   surface can only walk one direction of a two-direction
   lifecycle.

### 1.2 What the operator gets

At M31 close:

- A **"Show inactive" toggle** in the templates section of the
  Journal Entries page. Default off (byte-identical to M30.2
  shipped surface). Explicit operator opt-in — never auto-
  enabled, never a silent mixed-status list.
- **Semantically-distinct inactive rows** when the toggle is on:
  visible "Inactive" badge + row `aria-label` announcing
  lifecycle status + muted visual state + dedicated
  `template-row-inactive-<pk>` testid. A11y-first — the badge
  and aria-label are the load-bearing signals; muted styling is
  reinforcement, not the primary signal.
- A **Restore row action** on inactive rows (replaces the
  Delete slot). Confirmation dialog reframes the row-button
  vocabulary ("Restore") into truth vocabulary ("Reactivate
  template?"), reassures that historical journal entries are
  not affected, and completes the reversible lifecycle with a
  single click.
- **Disabled Edit and Instantiate controls on inactive rows**
  with explanatory accessible labels — the row exists and is
  visible to the operator, but mutations and instantiation
  require restoration first. This is the fail-closed direct-UI-
  path guard (L1) that makes the newly-exposed inactive-state
  UI truthful.
- **A fulfilled copy promise.** The M30.2 Delete confirmation
  copy is updated in the same milestone to point operators at
  the new Show-inactive toggle: *"You can restore this
  template later — turn on **Show inactive** to find and
  reactivate it."* No shipped UI carries a stale "future
  milestone" reference after M31 close.

### 1.3 What the operator does not get at M31

Explicitly out of scope — carried as future re-entry candidates:

- **Hard delete** on templates. Deactivate + Restore fully
  cover the reversible lifecycle. Hard delete escape hatch
  remains M30 §3 deferral; gated on operator evidence.
- **Bulk actions** on the templates list (bulk deactivate,
  bulk restore, bulk edit). Remains M30 §3 deferral.
- **Template mutation audit trail** (`edited_by_user`,
  history rows, restore/deactivate log). Remains M30 §3
  deferral; consider under M (multi-operator) if evidence
  surfaces.
- **Optimistic concurrency control** (ETag / `updated_at`
  check) on Restore or Deactivate. Remains M30 §3 deferral;
  gated on M (multi-operator).
- **Template mutation history / diff viewer.** Future re-entry
  candidate.
- **Auto-refresh / websocket invalidation** of stale-tab
  template list. Accepted per R1; documented as intentional
  decoupling consequence.
- **Persistent Show-inactive toggle state** (URL param,
  localStorage). Deferred pending operator evidence.
- **Any modification to M1–M30 shipped surface** except the
  M30.2 Delete confirmation copy per D10 (which is the
  fulfillment side of a shipped promise, not a modification
  of behavior).
- **Any change to the JournalEntry → JournalEntryTemplate
  coupling.** The decoupling is load-bearing on
  Restore/Deactivate safety. Server-side coupling to prevent
  the R1 stale-tab race is explicitly rejected — the accepted
  race outcome (a JE created from previously-hydrated
  template values is a valid standalone posting) is
  intentional per M28.0 §5.b + M30.0 §4.7.

## 2. Increment structure

**Two increments, standard M28+M29+M30 shape.**

- **M31.1 (SESSION_204) — Backend substrate.** New Restore
  service verb + Restore POST endpoint + list-endpoint
  `?include_inactive=true` query-param exposure with fail-
  closed parsing. Zero migration. **DoD exception path
  invocation #6** (M26 + M27.1 + M28.1 + M29.1 + M30.1 +
  M31.1) — backend substrate with no operator-facing behavior
  change on its own; DoD is satisfied by the M31.2 customer-
  facing follow-up.
- **M31.2 (SESSION_205) — Frontend + Playwright.** Show-
  inactive toggle + inactive-row rendering (Inactive badge +
  row aria-label + testid + muted styling) + Restore row
  action + `TemplateRestoreConfirmDialog` + list wrapper
  `includeInactive` parameter + `restoreJournalEntryTemplate`
  wrapper + disabled Edit/Instantiate controls on inactive
  rows with explanatory aria-labels (L1 lifecycle-integrity
  guard) + D10 M30.2 Delete-confirmation copy fulfillment
  update + single new `test.describe("restore-inactive",
  ...)` block extending `accounting_je_template.spec.ts`.
  Journey count 21 → 22. DoD satisfied directly.

Both increments are independently revertable via `git revert`.
Zero-migration property makes rollback cheap on both sides.

## 3. Deferrals (all valid for later re-entry)

Recorded per M30 §3 pattern. All are explicit non-goals for
M31 (see §5.h) and carried forward as candidates for future
milestones when evidence surfaces:

- **Hard delete on templates.** M30 §3 deferral unchanged.
  Gated on operator evidence — no signal at M31.0 open.
- **Bulk delete / bulk restore / bulk edit** on templates.
  M30 §3 deferral unchanged. Gated on operator evidence.
- **Template mutation audit trail** (`edited_by_user`,
  history rows, restore/deactivate log). M30 §3 deferral
  unchanged. Consider under M (multi-operator) if evidence
  surfaces.
- **Optimistic concurrency control** on Restore / Deactivate.
  M30 §3 deferral unchanged. Gated on M (multi-operator).
- **Template mutation history / diff viewer.** New M31 §3
  deferral. Future re-entry candidate.
- **Server-side filtering / pagination on templates list.**
  M25 §4 deferral unchanged. Show-inactive is a client-side
  re-request against the full list, not a paginated cursor.
- **Auto-refresh / websocket invalidation of stale-tab
  template list.** New M31 §3 deferral. Accepted per R1;
  intentional decoupling consequence.
- **Persistent Show-inactive toggle state** (URL param,
  localStorage). New M31 §3 deferral. Toggle is component-
  local state — fresh page mount = default off.
- **Bulk lifecycle actions across templates list** (Restore
  all inactive / Deactivate all active). New M31 §3
  deferral. Gated on pilot evidence.

All prior M30 §3 + M29 §3 + M28 §3 + M27 §3 + M25 §4
deferrals carried forward unchanged.

## 4. Verifications performed at planning-open

Eight verifications performed at M31.0 open. All must resolve
CLEAN before §5.b locks.

### 4.1 Lifecycle-integrity precheck (L1 — user-directed)

**Directed by user at §5.a lock request:** verify whether
inactive templates can currently still be instantiated through
any stale client state or direct UI path. If so, include the
smallest fail-closed guard necessary in M31 and record it as
lifecycle integrity, not feature expansion.

**Result: partial exposure exists; smallest fix is frontend
button-disable.**

**Trace.** Current instantiate flow (M28.2 shipped surface,
unchanged through M30):

1. `AccountingJournalEntriesPage.tsx:271` `handleInstantiate`
   — purely client-side hydration. Copies
   `template.description` + `template.lines` + lock
   configuration into local React state, opens
   `NewJournalEntryDialog` prepopulated. No API call at this
   step.
2. Operator submits the JE dialog; frontend calls
   `createJournalEntry`. The POST body carries JE lines
   only — **template pk is never sent**.
3. Backend `admin_journal_entry_create` creates a standalone
   `JournalEntry` with those lines and no template back-
   reference (M28.0 §5.b domain separation, verified at
   M30.0 §4.7).

**Consequences.**

- **Stale-tab race** (row cached as active in one tab;
  deactivated in another): Instantiate button appears
  enabled; click succeeds; a valid, standalone JE is
  created. This is **not** a lifecycle-integrity violation
  — it is the intentional consequence of the decoupled
  contract. Adding a server-side guard would break domain
  separation. **Accepted per user direction; documented in
  §5.c R1 as intentional race outcome.**
- **Show-inactive toggle on + inactive row visible**
  (M31.2 new state): without a guard, an operator could
  click Instantiate on a row explicitly rendered with an
  Inactive badge and produce a JE. This *is* a lifecycle-
  integrity gap once M31 exposes inactive rows to the
  operator. **Include the smallest fail-closed guard — L1
  in §5.b D7 — as lifecycle integrity, not feature
  expansion.**

**L1 guard (frontend only, zero backend change).** On rows
where `template.is_active === false`, disable both the
`template-instantiate-<pk>` and `tmpl-edit-trigger-<pk>`
buttons with explanatory `aria-label`. The Delete slot on
inactive rows becomes Restore per §5.b D7 row-action
asymmetry. This is the smallest fail-closed fix because a
server-side check would have nothing to check — the JE
create endpoint does not receive the template pk.

### 4.2 Substrate readiness

Verified: `get_journal_entry_template` and
`list_journal_entry_templates` both accept
`include_inactive: bool = False` kwarg (M30.1 —
`services/accounting/template.py:270-282` + `285-315`).

Neither endpoint currently exposes the kwarg. The public
list endpoint (`admin/accounting/journal-entry-templates/`)
returns active-only unconditionally; the detail endpoint
(`admin/accounting/journal-entry-templates/<pk>/`) uses
`include_inactive=True` internally for edit / delete
callers per M30.1 design but is not read-exposed. **One
one-line view-layer addition is needed to expose the
list kwarg; zero addition is needed for the detail
endpoint (edit and delete already work on soft-hidden
rows via M30.1 substrate).**

### 4.3 No FK from JournalEntry to JournalEntryTemplate

Verified structurally at M30.0 §4.7 and unchanged.
Re-verified at M31.0 open: `grep -R "template" backend/dealer_ai/models.py`
shows only the `JournalEntryTemplate` and `TemplateLine`
classes; the `JournalEntry` model has no `template` FK, no
`template_id` column, no reverse relation. Restore +
Deactivate cannot cascade to any existing JE, snapshot,
trial-balance report, or JE list/detail surface.

### 4.4 Copy-promise audit on M30.2 shipped surface

Verified: `AccountingJournalEntriesPage.tsx:670-672`
shipped delete-confirmation copy contains verbatim
promise:

> *"You can restore this template later. (Restore UX
> ships in a future milestone.)"*

The parenthetical is a **shipped promise about M31
completion** that operators can read today. D10
fulfillment scope in §5.b requires updating this copy in
M31.2 to point at the new Show-inactive toggle so no
shipped surface carries a stale "future milestone"
reference after M31 close. Vitest assertion at
`AccountingJournalEntriesPage.test.tsx:592` +
Playwright assertion updated in the same increment.

### 4.5 Endpoint-shape precedent

Verified: `admin/vehicle-photos/<uuid:public_id>/restore/`
(M21 audit endpoint #68, currently covered) already
exists in the codebase as a dedicated-Restore-verb
pattern. M31 uses the same URL shape
(`admin/accounting/journal-entry-templates/<int:pk>/restore/`)
and the same HTTP verb (POST — idempotent + no request
body needed). This confirms the shape is idiomatic for
Dealer AI Kit, not novel.

### 4.6 Row-action FK discoverability (feedback memory rule)

Per the `feedback_verify_fk_discoverability_before_lock.md`
memory rule (M27.0 origin, verified through M30.0):
Restore is a **state-mutation surface**, not a create /
edit surface. It requires no new FK exposure. The pk
needed to Restore is present on every Show-inactive-view
row via `data-testid="template-row-inactive-<pk>"`. No
substrate work required for discoverability.

### 4.7 Downstream + intake symmetry check

Per the M24.1-open + M25.0 + M25.2-open + SESSION_189 §3 +
SESSION_190 §2 + M27.0 §7 + M28.0 §7 + M29.0 §7 + M30.0
§7 durable lesson: every planning-open surface
verification must cover both intake AND downstream paths.

- **Intake:** the Show-inactive toggle is the sole intake
  surface for lifecycle-state discovery. A Restore attempt
  via direct URL to `.../restore/` for an active row
  returns 200 (idempotent — R3 mitigation). No other
  intake path exists.
- **Downstream:** after Restore, the row re-enters the
  default active list AND becomes a valid instantiation
  target AND becomes editable. Both directions of the
  reversible lifecycle covered.
- **Substrate accuracy check:** the M21 audit artifact
  post-M31 will show 158 endpoints (157 → +1 for
  Restore), 124 covered (123 → +1), 34 backend-only
  (unchanged). Two-source agreement gate at M31.2 close.

### 4.8 DoD compliance check on §3 draft

Per M21.0 §5.f Option B (M26 lineage): every customer-
facing milestone must add or update at least one
Playwright operational journey OR explicitly document
why no journey change is required.

- **M31.1** invokes DoD exception path — backend
  substrate with no operator-facing behavior change on
  its own. **Sixth invocation** (M26 + M27.1 + M28.1 +
  M29.1 + M30.1 + M31.1). Pattern firmly established.
- **M31.2** satisfies DoD directly via the new
  `restore-inactive` describe block in
  `accounting_je_template.spec.ts`. Coverage 21 → 22
  journeys.

## 5. Load-bearing decisions (all locked at M31.0)

### 5.a Target selection (locked at open)

**NEW Restore / "Show inactive" templates UI (lifecycle-
completion).**

Selected under the **primary operational-coverage lens**
evaluated as a lifecycle-completion workflow per explicit
user direction (§4.1 lifecycle-integrity precheck was
directed at open before scope lock). The
substrate-compound-value continuation framing (M27.1 →
M28.1 → M29 → M30 → M31 = fifth link) is **supporting,
not load-bearing** on the selection — per user guidance,
Restore was to be favored only if evidence showed
completing the reversible template lifecycle is the
highest-value bounded operator workflow available.

**Evidence.** Four load-bearing signals:

1. **Shipped-surface operator-safety promise unfulfilled.**
   M30.2 Delete confirmation copy at
   `AccountingJournalEntriesPage.tsx:670-672` reads
   *"You can restore this template later. (Restore UX
   ships in a future milestone.)"* Operators reading and
   acting on this today discover an integrity gap. Every
   day this ships, the gap compounds.
2. **Backend intervention required today.** Django shell
   is the only way to un-hide a deactivated template. No
   other operator surface exists.
3. **Bounded scope.** One new endpoint + one new service
   verb + one one-line view-layer extension + toggle +
   row state + Restore button + confirmation + L1
   button-disable guard + single Playwright describe
   block. Fits a two-increment M31 comfortably.
4. **Substrate is at 60%+ readiness.** M30.1 `include_inactive`
   kwarg already exists on both list and get verbs;
   endpoint exposure is a one-line addition; M28.1
   `is_active` field already backs everything; zero new
   migration required. Substrate-compound-value framing
   supports the selection as a fifth link but does not
   force it.

**Alternatives considered (per M31.0 candidate list
presented at §4 of SESSION_203 handoff):**

- **NEW C — F&I chargeback substrate.** Fails the "bounded
  + evidenced" test. §9 gating (M30 retrospective)
  requires pilot evidence not yet surfaced. Chargeback
  endpoint (#101) exists but is one of 13 uncovered F&I
  endpoints (audit #89–101); meaningful chargeback UI
  needs contract + back-end-product context; single-
  endpoint UI would be incoherent. Correct to defer.
- **NEW O2 / NEW O3.** Audit-tooling accuracy work.
  Unchanged M26/M27/M28/M29/M30 deferrals. Require
  SESSION-189-§3-style tracing at open; blast radius
  unknown; no direct operator gain.
- **H — Test-hygiene remediation.** CI-stability infra;
  zero direct operator gain. Compound value grows with
  journey count but does not close a shipped-surface
  gap.
- **Deal writeups (audit #112–114)** and other fresh
  direct-operator gaps surveyed from the audit backend-
  only list. None have evidenced operator pain; none
  close a shipped-surface promise; opening new domain
  surface without operator direction risks the wrong
  shape.
- **Gated (T/U/L/M):** unchanged gating; no upgrade at
  M31.0. Deferred **D** and deferred-stable **G**
  unchanged.

Restore was the only candidate that closed a shipped-
surface operator-safety promise AND removed a real
"backend intervention required" blocker AND met the
bounded-scope test.

### 5.b Design decisions (D1–D10)

#### D1 — Restore is a dedicated verb, never a PATCH side-effect

Add a **new** `restore_journal_entry_template(*, pk,
dealership)` service verb + a **new** endpoint
`admin/accounting/journal-entry-templates/<int:pk>/restore/`
(POST). Do **not** allow the existing PATCH detail
endpoint to set `is_active=True`. The
`JournalEntryTemplateUpdateRequestSerializer` continues to
omit `is_active`; a new M31 endpoint test locks the
behavior (mirrors the M30.2
`test_patch_silently_ignores_is_active_in_body` shape).

**Rationale.** Durable lesson (w) — activation surface
asymmetry. Mixing lifecycle state into a general edit
conflates two operator intents and creates a foot-gun
(edit accidentally reactivates a deactivated template).
Enforcement stays layered: update serializer doesn't
define the field; service passes explicit
`update_fields=[…]` on save; endpoint tests assert the
behavior.

**Precedent for endpoint shape.**
`admin/vehicle-photos/<uuid:public_id>/restore/` (audit
#68, already covered) — same dedicated-Restore-verb
pattern.

#### D2 — Restore is idempotent, tenant-scoped, and preserves everything except the lifecycle timestamp

Service contract:

```python
def restore_journal_entry_template(
    *, pk: int, dealership: Dealership
) -> Optional[JournalEntryTemplate]:
    """Restore a soft-hidden JournalEntryTemplate by setting
    ``is_active = True``.

    Fetches with ``include_inactive=True`` so a repeat Restore
    on an already-active row returns the same row without
    state change (idempotent — ``updated_at`` doesn't
    advance). Returns ``None`` when the pk doesn't exist or
    belongs to another tenant (endpoint layer maps to 404);
    otherwise returns the (now-active) row (endpoint layer
    maps to 200).

    Preserves ``name``, ``description``, ``lines`` (all
    fields + amounts + ordering), and ``created_at``
    verbatim. Advances ``updated_at`` only on the
    state-change branch (Django auto-now behavior on
    ``update_fields=["is_active", "updated_at"]``).
    """
    template = get_journal_entry_template(
        pk=pk, dealership=dealership, include_inactive=True
    )
    if template is None:
        return None
    if template.is_active:
        return template  # idempotent — no state change
    template.is_active = True
    template.save(update_fields=["is_active", "updated_at"])
    return template
```

**Explicitly guaranteed by construction** (do NOT add a
migration or a field to enforce):

- `name`, `description`, `line_count`, all `TemplateLine`
  fields (account_id, side, amount, order) — untouched.
  Restore does not re-read or re-write lines. Endpoint
  test asserts `Template.objects.get(pk=…).name == "…"`
  etc. after Restore.
- `created_at` — untouched. Endpoint test asserts
  `created_at` unchanged before/after.
- `updated_at` — advances ONLY on the state-change
  branch. Endpoint test asserts unchanged on idempotent
  repeat-Restore.
- Historical `JournalEntry` rows — untouched (verified
  structurally by §4.3; carried into M31 via Playwright).

#### D3 — Endpoint list exposure of `?include_inactive=true` is a one-line change; default posture is fail-closed

Extend the existing list view to parse
`?include_inactive=true` from `request.GET`. Fail-closed
parsing per user confirmation: **only the literal string
`"true"`, case-insensitive** (`true`, `TRUE`, `True`),
enables inactive rows. Every other value — `1`, `yes`,
empty string, malformed, omitted — resolves to the
active-only default. Pass through to
`list_journal_entry_templates(include_inactive=…)`.

Default remains False — the plain endpoint continues to
return active-only. **Inactive templates never mix into
the default active list.**

Endpoint tests: default returns active-only;
`?include_inactive=true` returns both; `?include_inactive=TRUE`
returns both (case-insensitive); `?include_inactive=True`
returns both; `?include_inactive=1` returns active-only
(fail-closed); `?include_inactive=yes` returns active-
only; `?include_inactive=` (empty) returns active-only;
`?include_inactive=maybe` (malformed) returns active-
only; missing param returns active-only.

#### D4 — Frontend list wrapper accepts an explicit `includeInactive` parameter

Extend `listJournalEntryTemplates(dealershipId)` in
`accountingApi.ts` to accept an optional second
parameter `{ includeInactive?: boolean }` (default
false). When true, the request URL appends
`?include_inactive=true`. The page-level list query hook
reruns whenever the toggle state changes.

**Naming discipline.** The operator-facing toggle label
is **"Show inactive"** (not "Show all", not "Include
deleted"). The API parameter name in the wrapper is
`includeInactive` (camelCase); the URL parameter remains
`include_inactive` (snake_case, matching backend
convention).

#### D5 — Show-inactive is an explicit operator toggle; no silent mixed-status list

The toggle is a shadcn `Switch` (or `Checkbox`) with
label "Show inactive templates". Default state: **off**.
Location: templates section header of
`AccountingJournalEntriesPage.tsx`, adjacent to the
"+ New template" button.

When off (default): the list is active-only — byte-
identical to M30.2 shipped surface.

When on: the list contains active + inactive rows, with
inactive rows visually and semantically distinct per D6.

**No auto-toggle** — the toggle never flips automatically
(e.g., after a Deactivate). The operator asks to see
inactive; the system does not decide for them. This is
the truthfulness posture: mixed-status lists must be
explicitly opted into.

#### D6 — Inactive rows are visually AND semantically distinct (a11y-first, not muted-only)

Every inactive row carries **three independent signals**:

1. **Semantic status text.** A visible "Inactive" badge
   (shadcn `Badge`) rendered adjacent to the template
   name. Screen-reader text is the badge content; the
   badge is not `aria-hidden`.
2. **Row `aria-label`** on the `<tr>` — e.g.,
   `aria-label="Template <name>, inactive"` — so screen
   readers announce lifecycle state independent of
   visual styling.
3. **`data-testid` marker.** New
   `template-row-inactive-<pk>` on inactive rows
   (mirrors `template-row-<pk>` pattern) so Playwright +
   Vitest can assert on lifecycle status directly.

**Plus** muted visual state (reduced opacity, applied via
CSS class) — reinforcement of the semantic signals, not a
replacement for them. Do **not** rely on muted styling
alone. The badge + `aria-label` + testid are the load-
bearing signals; the visual muting survives color-
blindness modes and dark mode by virtue of not being the
primary channel.

#### D7 — Row-action asymmetry: Restore replaces Delete on inactive rows; Edit + Instantiate are visible-but-disabled (L1 lifecycle-integrity guard)

On an **inactive row**:

- **Delete slot → Restore button.** New
  `data-testid="tmpl-restore-trigger-<pk>"` (mirrors
  M30.2 `tmpl-delete-trigger-<pk>` pattern). Opens the
  Restore confirmation dialog per D8.
- **Edit button — visible-but-disabled** with
  `aria-label="Edit template — restore it first to
  enable"`. Reason: editing an inactive template would
  surface a mode-ambiguity that the (w) asymmetry rules
  out (activation is DELETE / Restore-only, never
  through PATCH).
- **Instantiate button — visible-but-disabled** with
  `aria-label="Instantiate template — template is
  inactive; restore it first to enable"`. This is the
  **L1 lifecycle-integrity guard** identified in §4.1 —
  the smallest fail-closed direct-UI-path fix against
  operator-visible instantiation of a badge-labeled
  Inactive row.

**Visible-but-disabled** chosen (per user confirmation
of §5.b review point 2) over "hide entirely". A visible-
but-disabled control is a **stronger a11y signal** than a
hidden one — it communicates that the actions exist AND
that restoration is the path to enable them. Hiding
would create an operator mental-model gap ("wait, why
can't I edit this?").

On an **active row** (default): no change from M30.2
shipped surface. Instantiate + Edit + Delete continue
unchanged.

#### D8 — Restore confirmation dialog reframes row-action vocabulary to truth vocabulary

Mandated copy — mirrors the M30.2 D3 asymmetry per
lesson (x):

- **Title:** "Reactivate template?" (truth vocabulary —
  soft-hide is being reversed to active state).
- **Body:** *"Are you sure you want to reactivate
  `<name>`? This template will reappear in the active
  templates list and can be used to create new journal
  entries again. Existing journal entries created from
  this template are not affected — they remain unchanged
  in the Journal Entries list and in trial balance
  reports."*
- **Footer:** `[Cancel] [Reactivate]` — Reactivate as
  primary (not destructive variant; this is an additive
  action).
- **Test-ids:** `tmpl-restore-confirm-body`,
  `tmpl-restore-cancel`, `tmpl-restore-submit`.

The row button says **"Restore"** (short, familiar
operator vocabulary). The confirmation reframes to
**"Reactivate"** (truth vocabulary — what actually
happens: `is_active` transitions False → True).
Playwright asserts the confirmation title + body copy
verbatim.

**Component.** New inline `TemplateRestoreConfirmDialog`
in `AccountingJournalEntriesPage.tsx` (co-located,
parallel to `TemplateDeleteConfirmDialog`). Do **not**
extract to a shared abstraction — the M28.0 lesson
(`feedback_duplicate_small_stable_logic.md`) applies:
duplicate small, stable, domain-local dialog logic in
favor of a shared helper.

#### D9 — Existing journal entries and reports are untouched by Restore or Deactivate

Structural guarantee (already true at M30.0 §4.7 —
carried into M31): no FK from `JournalEntry` to
`JournalEntryTemplate`. Restore + Deactivate mutate one
field on one row; nothing cascades.

**Playwright assertion carried through the Restore
lifecycle spec:** after the deactivate → restore round-
trip, historical JE description AND `total_debit` AND
trial-balance total are byte-identical to pre-cycle
values. This proves **both directions** of the
reversible-lifecycle contract.

#### D10 — Update the M30.2 Delete confirmation dialog copy to reflect Restore is now shipped

The M30.2 shipped copy at
`AccountingJournalEntriesPage.tsx:670-672` reads: *"You
can restore this template later. (Restore UX ships in a
future milestone.)"* — the parenthetical is a **shipped
promise about M31 completion**. Update to: *"You can
restore this template later — turn on **Show inactive**
to find and reactivate it."* Update the corresponding
Vitest assertion at
`AccountingJournalEntriesPage.test.tsx:592` +
Playwright assertion in the same increment.

**This is not a copy tweak; it is the fulfillment side
of the shipped M30.2 operator-safety promise.** Bundled
in M31.2 UI scope per user confirmation of §5.b review
point 4 — no shipped UI carries a stale "future
milestone" reference after M31 close.

### 5.c Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Stale-tab race allows JE creation from a template the user deactivated in another tab | Med | Low | **Accepted per user direction.** JE and JournalEntryTemplate are intentionally decoupled (M28.0 §5.b + M30.0 §4.7). Resulting JE is well-formed; no data corruption. Not fixable without breaking intentional decoupling. Documented in §4.1, not guarded. |
| R2 | Operator on Show-inactive view clicks Instantiate on an Inactive-badged row | Low (with D7) / Med (without) | Med | D7 disables Instantiate + Edit on inactive rows with explanatory aria-label. **L1 lifecycle-integrity guard** — makes the newly exposed inactive-state UI truthful and safe (per user confirmation of §5.b review point 6). |
| R3 | Restore endpoint racing with concurrent Deactivate → last-write-wins ambiguity | Low | Low | Both verbs are idempotent + narrow (`update_fields=["is_active", "updated_at"]`). Optimistic concurrency control on templates is explicitly deferred (M30 §3, unchanged). Documented as accepted race — matches BHPH / condition-finding precedent. |
| R4 | Cross-tenant Restore attempt returns wrong row's state | None (by construction) | Critical | `restore_journal_entry_template` fetches via `get_journal_entry_template` which filters by dealership. Endpoint test asserts cross-tenant returns 404. Reuses M30.1 pattern. |
| R5 | Malformed `?include_inactive` query values silently include inactive rows | Low | Med | D3 fail-closed parsing — only literal `"true"` (case-insensitive) opts in; everything else defaults to False. Endpoint tests cover `1`, `yes`, `TRUE`, `True`, empty, malformed, missing. |
| R6 | Copy asymmetry ("Restore" button → "Reactivate" confirmation) confuses operators | Low | Low | Precedent: M30.2 Delete → Deactivate asymmetry shipped without complaint. Playwright asserts confirmation copy verbatim. Established lesson (x) pattern. |
| R7 | Inactive-badge styling relies on color / opacity alone → a11y failure in high-contrast / color-blindness modes | Low (with D6) / Med (without) | Med | D6 mandates three independent signals: semantic Badge text + row `aria-label` + `data-testid`. None color-dependent. Muted styling is reinforcement only. |
| R8 | Show-inactive toggle state persists across page navigations, surprising operators returning to the page | Low | Low | Toggle is component-local state (not URL-serialized, not localStorage-persisted). Fresh page mount = default off. Consistent with M30.2 templates-section toggle behavior. |
| R9 | New endpoint pushes DRF admin surface count past cleanly-tracked baseline | None | Very Low | Expected DRF admin count post-M31: **118** (117 → +1 for Restore). Endpoint category tracker in retrospective §7 accounts for it. |
| R10 | Adding Restore inflates permission-class count (breaks 31-milestone zero-drift streak) | None (by construction) | Med (streak) | Restore endpoint reuses `_M131_PERMS` verbatim (same admin_or_advisor pattern as M30.1). Zero-drift streak advances 31 → **32**. Explicit precondition of D1. |

### 5.d Verifications completed at planning-open

Eight verifications (§4.1–§4.8 above) all resolved CLEAN:

- §4.1 Lifecycle-integrity precheck (L1 — user-directed):
  smallest fail-closed guard identified; server guard
  ruled out by decoupled contract.
- §4.2 Substrate readiness: M30.1 `include_inactive`
  kwarg present on both list and get; one-line view
  extension needed for list endpoint exposure.
- §4.3 No FK from `JournalEntry` to
  `JournalEntryTemplate`: verified structurally,
  unchanged from M30.0 §4.7.
- §4.4 Copy-promise audit: M30.2 delete-confirmation
  copy carries a shipped Restore promise that requires
  D10 fulfillment in M31.2.
- §4.5 Endpoint-shape precedent: audit endpoint #68
  `admin/vehicle-photos/<uuid>/restore/` confirms the
  idiomatic shape.
- §4.6 FK discoverability: not applicable — Restore is
  state-mutation, not create/edit. Pk discoverability
  via `template-row-inactive-<pk>` testid.
- §4.7 Downstream + intake symmetry: both directions
  covered — Show-inactive toggle intake; row re-enters
  active list + becomes editable + instantiable
  downstream after Restore.
- §4.8 DoD compliance: M31.1 exception path (#6);
  M31.2 direct satisfaction via new describe block.

### 5.e Phase / increment structure

Standard two-increment split. Both revertable
independently; zero-migration property makes rollback
cheap on both sides.

#### M31.1 (SESSION_204) — Backend substrate

**DoD exception path invocation #6.**

- **Service layer** (`services/accounting/template.py`):
  - New `restore_journal_entry_template(*, pk,
    dealership)` verb — atomic, idempotent,
    `update_fields=["is_active", "updated_at"]`. Module
    docstring updated to list the new verb alongside
    `update_` and `delete_`.
- **Endpoint layer** (`views_accounting.py`):
  - New `admin_journal_entry_template_restore(request,
    pk)` view (POST). Reuses `_M131_PERMS`. Error
    mapping: 404 missing/cross-tenant, 200 restored,
    200 idempotent already-active.
  - Extend `admin_journal_entry_template_list` to parse
    `?include_inactive=true` per D3 fail-closed
    parsing and pass through to service.
- **URL** (`urls.py`): new pattern
  `admin/accounting/journal-entry-templates/<int:pk>/restore/`
  → `admin-journal-entry-template-restore`.
- **Zero migration** — reuses `is_active` field
  verbatim.
- **Tests (planned ~24; may exceed budget +2–5 for
  auth/tenancy coverage per M30.1 lesson):**
  - NEW `test_m31_journal_entry_template_restore_service.py`
    (~12: happy path, idempotent repeat-Restore
    returns row without state change, returns None on
    missing pk, returns None on cross-tenant, preserves
    name, preserves description, preserves lines
    including amounts and ordering, preserves
    created_at, advances updated_at only on state-
    change branch, accepts already-active pk without
    error, returns the projected row shape).
  - EXTEND `test_m28_journal_entry_template_endpoint.py`
    with `TemplateRestoreEndpointTests` (~10: POST 200
    restore, POST 200 idempotent-already-active, POST
    404 missing, POST 404 cross-tenant, admin
    allowed, advisor allowed, unauth denied, PATCH
    cannot mutate is_active — regression re-assertion
    from M30.2, list default returns active-only, list
    with `?include_inactive=true` returns both).
  - EXTEND `test_m28_journal_entry_template_endpoint.py`
    list tests with `?include_inactive` fail-closed
    parsing (~4: `true` and `TRUE` and `True` enable;
    `1`, `yes`, empty, malformed, missing all resolve
    to active-only).
- **Expected count:** 4,904 → **~4,930** (+~26 tests).
- **`manage.py check` + `makemigrations --check
  --dry-run`:** clean.
- **Non-goals in M31.1:** no frontend changes; no
  Playwright; no UI copy fix; no DRF admin count re-
  baselining (rolls into M31 close-out per convention).

#### M31.2 (SESSION_205) — Frontend + Playwright

**DoD satisfied directly via new `restore-inactive`
describe block.**

- **Frontend list wrapper** (`accountingApi.ts`):
  - Extend `listJournalEntryTemplates` with optional
    `{ includeInactive?: boolean }`; append
    `?include_inactive=true` when true.
  - New `restoreJournalEntryTemplate(pk)` wrapper —
    wraps `authPostJSON` (POST empty body); returns
    projected template.
- **Page (`AccountingJournalEntriesPage.tsx`):**
  - Show-inactive `Switch` (or `Checkbox`) in
    templates section header — component-local state;
    triggers refetch with `includeInactive` when
    changed.
  - `TemplateRow` gains `is_active`-aware rendering:
    Inactive badge + row `aria-label` + testid
    `template-row-inactive-<pk>` + Restore button
    replacing Delete on inactive rows + disabled Edit
    + disabled Instantiate with explanatory aria-
    labels (L1 guard per D7).
  - New inline `TemplateRestoreConfirmDialog` co-
    located with `TemplateDeleteConfirmDialog`.
    Mandated copy per D8.
  - **Copy fix (D10):** M30.2 delete-confirmation body
    updated — new phrasing "turn on **Show inactive**
    to find and reactivate it". Vitest assertion at
    line 592 updated to match new text.
- **Frontend tests planned (~22):**
  - `AccountingJournalEntriesPage.test.tsx` (+~14):
    Show-inactive toggle renders + default off;
    toggle on triggers refetch with
    `includeInactive=true`; inactive-row Inactive
    badge visible; inactive-row aria-label present;
    inactive-row testid `template-row-inactive-<pk>`;
    inactive-row Restore button renders; inactive-row
    Edit button disabled + aria-label; inactive-row
    Instantiate button disabled + aria-label; Restore
    click opens confirmation with D8 copy; Restore
    confirm calls `restoreJournalEntryTemplate` +
    refetches; Restore failure surfaces inline error
    without closing; D10 updated Delete-confirm copy
    assertion.
  - `accountingApi.templates.test.ts` (+~6):
    `listJournalEntryTemplates` with
    `includeInactive=true` appends
    `?include_inactive=true`; false or omitted does
    not append; `restoreJournalEntryTemplate` POST
    URL; propagates 404; propagates 500; 200 returns
    projected template.
- **Playwright (+1 journey — extension of
  `accounting_je_template.spec.ts`):** new
  `test.describe("restore-inactive", ...)` block,
  single 7-step journey mapping 1:1 to user constraint:
  1. Seed an active template via admin API
     ($100/$100); confirm it appears in the default
     active list.
  2. Row Delete → confirm Deactivate → assert
     template disappears from the default list;
     reload → still gone.
  3. Toggle Show inactive ON.
  4. Assert template row reappears with
     `template-row-inactive-<pk>` testid AND Inactive
     badge visible AND row `aria-label` contains
     "inactive" AND Instantiate button is disabled
     (`toBeDisabled()`) AND Edit button is disabled.
  5. Click row Restore → confirmation appears with D8
     mandated copy ("Reactivate template?" +
     "will reappear in the active templates list" +
     "Existing journal entries created from this
     template are not affected") → click Reactivate.
  6. Toggle Show inactive OFF.
  7. Assert template reappears in the default active
     list AND Instantiate button is enabled AND
     clicking Instantiate opens the JE dialog
     prepopulated → post a fresh JE → assert JE
     appears in Journal Entries list. **Load-bearing
     lifecycle assertion:** historical JE from step 1
     (if any was created before the cycle) AND its
     `total_debit` AND trial-balance total are byte-
     identical before and after the full cycle.
- **Expected counts:** frontend 300 → **~322**;
  acceptance 21 → **22 journeys**.
- **D10 copy fix ships with M31.2** — no shipped
  surface carries a stale "future milestone" reference
  after M31 close.
- **`tsc --noEmit`:** clean across frontend +
  acceptance.
- **`git grep "Restore UX ships in a future
  milestone" frontend/ acceptance/`:** empty (D10
  verified).

### 5.f DoD compliance check

Per M21.0 §5.f Option B (M26 lineage): every customer-
facing milestone must add or update at least one
Playwright operational journey, OR explicitly document
why no journey change is required.

- **M31.1** invokes the DoD exception path — backend
  substrate with no operator-facing behavior change on
  its own. **Sixth invocation** (M26 + M27.1 + M28.1 +
  M29.1 + M30.1 + M31.1). Pattern firmly established.
  Exception rationale documented in §3 of the M31.1
  handoff.
- **M31.2** satisfies DoD directly via the new
  `restore-inactive` describe block in
  `accounting_je_template.spec.ts`. Coverage 21 → 22
  journeys. Covers the complete reversible lifecycle
  per user 7-step spec.

### 5.g Rollback plan

Both increments are independently revertable via `git
revert`. Zero-migration property makes rollback cheap
on both sides — no data migration to unwind.

- **M31.1 revert.** Removes the Restore endpoint +
  `?include_inactive` list-endpoint exposure + service
  verb. Data-safe: Restore does not migrate rows;
  deactivated rows keep `is_active=False` and remain
  accessible only via Django shell (returns to pre-M31
  state).
- **M31.2 revert.** Removes the Show-inactive toggle +
  Restore UI + inactive-row rendering + L1 disable
  guards. Operator falls back to Django-shell-only
  Restore. D10 copy update reverts back to the
  "Restore UX ships in a future milestone" text —
  factually incorrect by then but not operationally
  harmful.
- **Coordinated M31 close push** deferred to explicit
  user confirmation per M27 / M28 / M29 / M30
  coordinated-close cadence. Push cadence exception
  path preserved for any §0.a M31.0 amendment that
  might land (e.g., a red first-M30 CI run — not
  expected; last M30 CI run on `f658c06` is green).

### 5.h Non-goals for M31

Explicitly out of scope per user constraints (see §1.3
for operator-facing framing):

- ❌ **Hard delete** on templates (query param, alt
  endpoint, admin escape hatch) — remains M30 §3
  deferral.
- ❌ **Bulk delete / bulk restore / bulk edit** on
  templates — remains M30 §3 deferral.
- ❌ **Template mutation audit history**
  (`edited_by_user`, history rows, restore/deactivate
  log) — remains M30 §3 deferral.
- ❌ **Optimistic concurrency control** (ETag /
  `updated_at` check) on Restore or Deactivate —
  remains M30 §3 deferral.
- ❌ **Template mutation history / diff viewer** —
  new M31 §3 deferral.
- ❌ **Server-side filtering / pagination** on the
  templates list — remains M25 §4 deferral. The
  Show-inactive toggle is a client-side re-request,
  not a paginated cursor.
- ❌ **Auto-refresh / websocket invalidation** of
  stale-tab template list — accepted per R1; carried
  as intentional decoupling consequence.
- ❌ **Persistent Show-inactive toggle state** (URL
  param, localStorage) — new M31 §3 deferral.
- ❌ **Bulk lifecycle actions across the templates
  list** (Restore all / Deactivate all) — new M31 §3
  deferral.
- ❌ **Any modification to M1–M30 shipped surface**
  except the M30.2 Delete-confirmation copy per D10.
- ❌ **Any change to the JournalEntry →
  JournalEntryTemplate coupling** (no FK — the
  decoupling is load-bearing on Restore/Deactivate
  safety). Server-side coupling to prevent the R1
  stale-tab race is explicitly rejected — the
  accepted race outcome (JE created from previously-
  hydrated template values is a valid standalone
  posting) is intentional per M28.0 §5.b + M30.0
  §4.7.
- ❌ **New permission classes** — Restore endpoint
  reuses `_M131_PERMS`; zero-drift streak advances
  31 → 32.

## 6. Streak accounting projections (at M31.0)

- **Planning-time as-recommended streak: 9 → 10.**
  Target selected as recommended after five-alternative
  comparison + lifecycle-integrity precheck performed
  at user direction. §0.a M31.0 amendments (none as of
  M31.0 open) are corrective and do not affect the
  streak. Historical run of 89 across M10 → M23
  preserved for the record.
- **Zero-drift permission-class streak: 31 → 32
  (projected at M31 close).** M31.1 adds Restore
  endpoint reusing `_M131_PERMS` verbatim; M31.2
  ships no new endpoints. Zero-drift preserved.
- **Substrate-compound-value continuation: 4 → 5
  links (projected at M31 close).** M27.1 (gl-
  accounts) → M28.1 (template substrate) → M29
  (variable-amount) → M30 (template CRUD closure) →
  **M31 (template lifecycle closure)**. Zero new
  migration; reuses M28.1 `is_active` field + M30.1
  `include_inactive` kwarg.
- **DoD exception path invocations: 5 → 6.** M26 +
  M27.1 + M28.1 + M29.1 + M30.1 + **M31.1**. Pattern
  firmly established.
- **Additive-prop pattern (durable lesson (t)):**
  first re-application at M30.2 established the
  pattern as "load-bearing across two milestones."
  M31 does not add new mode branches to the renamed
  `JournalEntryTemplateDialog` component (Restore is
  a state-mutation, not a form). Additive-prop
  pattern is *available* if a future need surfaces;
  M31 uses a co-located inline dialog per the
  `feedback_duplicate_small_stable_logic.md` rule
  instead.
- **Copy-vocabulary asymmetry (durable lesson (x)):**
  first re-application at M31.2 confirmation dialog
  ("Restore" row button → "Reactivate" confirmation).
  Elevates from "surfaced" (M30.2) to "load-bearing
  across two milestones."
- **Audit coverage projected at M31 close:** 157 →
  158 endpoints; 123 → 124 covered; 34 backend-only
  unchanged; 317 → 318 service verbs (+1 for
  `restore_journal_entry_template`).

## 7. Anchors that win on conflict (for M31.1 / M31.2)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M1–M28 shipped in-tree; M29–M31 shipped surface
   in CAPABILITY_MATRIX §7δ + §7ε + §7ζ per
   convention adopted at M27+)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_30_RETROSPECTIVE.md` §9
   (M31 candidate list origin — Restore/Show-inactive
   elevated on the basis of §4.1 shipped-promise
   evidence + M30.1 substrate readiness)
6. **`docs/roadmap/MILESTONE_31_PLANNING.md`** (this
   document — M31 governing contract + §0.a + all §5
   locks + §4.1 lifecycle-integrity precheck)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (M30.2 baseline — 157 endpoints / 123 covered / 34
   backend-only / 317 service verbs; M31 projected
   delta +1 endpoint, +1 covered, +1 verb)
8. `docs/CAPABILITY_MATRIX.md` §7z (M25) + §7α
   (M26) + §7β (M27) + §7γ (M28) + §7δ (M29) + §7ε
   (M30 shipped surface); M31 §7ζ added at M31 close
9. `docs/handoffs/SESSION_202_m30_inc2_frontend.md`
   (M30.2 shipped + M30 close-out; source of shipped
   Restore-promise copy at §4.4)
10. Memory record `feedback_duplicate_small_stable_logic.md`
    (M28.0 origin — governs the D8 co-located inline-
    dialog choice; no shared abstraction)
11. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — verified through M31.0 §4.6)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.
