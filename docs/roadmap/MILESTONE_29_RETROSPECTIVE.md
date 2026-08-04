---
title: "Milestone 29 — Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate) — Retrospective"
status: historical
type: retrospective
milestone: 29
milestone_status: shipped
generated: 2026-08-04
generated_at_session: SESSION_199 (M29.2 close + close-out fold)
milestone_name: "Variable-Amount Journal Templates (on M28.1 template substrate + M27.1 gl-accounts substrate)"
increments_shipped: [0, 1, 2]
close_out_fold: true
sessions: [197, 198, 199]
commits_at_close: 6
---

# Milestone 29 — Variable-Amount Journal Templates — Retrospective

> Milestone 29 opened at SESSION_197 M29.0 planning under the
> durable primary operational-coverage lens plus the substrate-
> compound-value continuation framing that first validated at
> M27.1 → M28.1 → M28.2. M29.1 shipped the backend serializer +
> service relaxation at SESSION_198; M29.2 shipped the customer-
> facing UI + Playwright coverage at SESSION_199 with close-out
> folded in (no separate M29.3).
>
> **The anchor business question** — *Can a dealership accountant
> persist a recurring journal-entry recipe once, instantiate it
> monthly with amounts that vary period-to-period (depreciation,
> utilities, payroll accruals), and post a balanced entry through
> the shipped application?* — is answered **yes**. One combined
> Playwright journey covers the end-to-end flow with all six
> user-specified assertions in sequence.
>
> M29 realized the intended payoff of the M28.1 forward-compat
> schema reservation (nullable `amount` on `JournalEntryTemplateLine`
> via migration `0050`) — spent with zero new migrations,
> demonstrating the substrate-compound-value framing on the
> immediately-following milestone.

## 1. Planned scope

Per `MILESTONE_29_PLANNING.md` §5.a locked at open: **NEW
variable-amount journal templates.**

Two-increment split per §5.e:

- **M29.1 (SESSION_198)** — backend substrate relaxation:
  serializer `allow_null=True`; service three-state balance
  logic (null → variable line skip; positive → contribute;
  zero/negative → reject); balance check on populated portion
  only. New M29 service test file + endpoint/model extensions.
  DoD exception path invoked as fourth precedent (M26 + M27.1
  + M28.1 + M29.1).
- **M29.2 (SESSION_199)** — frontend + Playwright: per-line
  "Variable amount" checkbox on `NewJournalEntryTemplateDialog`;
  additive `lockedLines` prop + `overridden` state + Override
  toggle on `NewJournalEntryDialog`; `variableSide` extension
  on `NewJournalEntryInitialValues`; `AccountingJournalEntriesPage`
  consumer wiring. Single combined `test.describe("variable-
  amount", ...)` block extension of `accounting_je_template.spec.ts`
  covering all six user-specified assertions. DoD satisfied
  directly.

Anchor: **Can accounting staff instantiate a variable-amount
template (depreciation / utilities / payroll accruals) into a
balanced JE without leaking amounts into the saved template?**

## 2. What actually shipped

Delivered end-to-end per §1 with two clean substrate refinements
that surfaced during implementation:

- **Cross-tenant guard reordering (M29.1).** In
  `_validate_template_lines`, the cross-tenant account check was
  moved earlier in the line loop so it applies to variable lines
  (which skip the amount branch) as well as fixed lines. The
  M28.1 test surface continues to pass unchanged — no functional
  regression, just cleaner ordering.
- **`NewJournalEntryInitialValues.lines[i].variableSide`
  extension (M29.2).** During D3 implementation, it became clear
  that a variable-amount line needs to signal WHICH side the
  operator should enter into (the template stores `side` as
  `debit` or `credit`; the JE dialog has separate `debit` and
  `credit` cells). Rather than shoehorn a fifth signal through
  the `lockedLines` prop, the initial-value shape was extended
  with an optional `variableSide` field. Same additive-safe
  posture as `lockedLines`; the blank-entry path never sets it.

Backend baseline: **4,855 → 4,871** (+16 net at M29.1).
Frontend Vitest: **270 → 282** (+12 at M29.2). Acceptance:
**19 → 20 journeys** (+1 combined variable-amount describe
block). Audit: **156 / 122 / 34 / 315** identity across the
milestone (no endpoint drift). Zero-drift permission-class
streak: 28 → 29 (unchanged M10–M29 permission classes).

## 3. Deviations from plan and reason

Two minor scope refinements from the M29.0 memo, both surfaced
mid-implementation:

- **Existing M28.2 Instantiate test updated at M29.2.** The
  `AccountingJournalEntriesPage.test.tsx::opens the JE dialog
  pre-populated when Instantiate is clicked` case asserted
  `getByLabelText("Line 1 debit")` on an editable input — that
  input no longer exists at M29.2 for a fixed template line
  (chip renders instead). Test updated to assert the chip
  + Override presence. Analogous to the M29.1 removal of
  `test_refuses_null_amount_at_m28` — behavior intentionally
  changed at M29 (D3 Option A locked at M29.0), test refreshed
  in-place to reflect the new UX. No scope shift; the test
  continues to guard the Instantiate flow's operator-facing
  contract.
- **`variableSide` shape extension not called out at M29.0.**
  The M29.0 memo D3 spec named `lockedLines` as the sole prop
  addition. During M29.2 implementation, `NewJournalEntryInitialValues.lines[i]`
  was also extended with an optional `variableSide` field to
  signal which side an amber ring should apply to. This is
  additive-safe (same posture as `lockedLines`, no impact on
  blank-entry path) and does not violate the D3 implementation-
  boundary constraint (still no template-specific branching
  outside the amount-cell renderer). Recorded here so a future
  reader knows the M29.0 memo D3 spec was slightly under-scoped
  on the initialValues shape.

**No exception-path DoD justifications required at M29.2** —
the D8 combined variable-amount describe block satisfies DoD
directly (journey 19 → 20).

## 4. Deferrals from M29 (all valid for later re-entry)

Carried forward from M28 §3, M27 §3, M25 §4 — unchanged. Plus
new M29 §3 deferrals:

- **Fully-variable UX polish** — "Repeat last amounts" affordance
  at instantiate. Not shipped; the M27.2 balance indicator is a
  sufficient guard against fat-finger errors on first pass.
- **Server-recorded instantiation audit trail** — no
  `last_instantiated_at` / `instantiation_count` fields on
  `JournalEntryTemplate`. Preserves D5 template-immutability
  posture; additive if operator evidence supports it later.
- **Named / shared template variables** — one operator input
  drives multiple line amounts. Reaffirmed as an M28 §3 deferral.
- **Template edit / delete UI** — remains a strong candidate for
  a future milestone; not scoped into M29 unless narrow
  correction evidence surfaced (it did not).

## 5. Durable design principles surfaced or reinforced

Five principles carried forward from M28 continue to apply. Two
principles are NEW at M29 or reinforced enough to record:

- **(NEW at M29.2) Additive-prop pattern for UI reuse.** When a
  reusable component (`NewJournalEntryDialog`) needs to serve a
  new context (template Instantiate) with divergent per-line
  rendering, an *additive optional prop* with a safe default
  (`lockedLines?: readonly boolean[]` → `undefined` = blank-
  entry byte-identical) is preferred over a thin wrapper
  component when the divergent UI must render inside an
  existing cell (the amount cell). The wrapper alternative
  requires exposing a render slot — larger API surface change
  than one optional prop with default-safe semantics. Recorded
  in the M29.0 memo §5.b D3 implementation-boundary decision
  and reinforced by the M29.2 blank-entry regression guard test
  passing without modification. Consideration for future
  milestones: when adding UI variants to shipped reusable
  components, evaluate the additive-prop pattern before
  reaching for a wrapper.

- **(NEW at M29.2) Reset every override / annotation state in
  every reset path.** The `overridden: Set<number>` state on
  `NewJournalEntryDialog` must clear in five paths (open
  transition, `initialValues` change, `lockedLines` change,
  `reset()` call, `onOpenChange(false)`) to prevent leaking
  between instantiations. Failure mode: an override from
  template A leaks into template B, letting the operator post
  a JE that treats a fixed line as editable when it should be
  locked. The five-way reset is explicit and covered by the
  M29.2 Playwright + vitest coverage. Similar patterns will
  apply to any future UI state that annotates a subset of a
  reusable component's line list.

- **(REINFORCED, fourth invocation) DoD exception path for
  infrastructure-only sub-increments.** M29.1 marks the fourth
  invocation of the M21.0 §5.f Option B path (M26 + M27.1 +
  M28.1 + M29.1). Pattern is now well-established: backend
  substrate refinements that do not change operator-facing
  behavior can invoke the exception path, provided the
  customer-facing increment (M29.2) satisfies DoD directly.
  The four precedents share the shape: a schema-reserved or
  service-relaxation change with no new operator affordance,
  followed by a UI + Playwright increment that binds the
  substrate to a user-visible workflow.

- **(REINFORCED) Substrate-compound-value continuation across
  milestones.** M27.1 (gl-accounts) → M28.1 (template substrate)
  → M29 (variable-amount extension) is the third link in an
  intentional lineage. Each link cost measurably less than a
  green-field milestone because it composed on the prior
  substrate. Consideration for future milestones: candidates
  that continue this lineage (e.g., F&I chargeback substrate
  on M27.1) should be evaluated for compound-value framing
  alongside the primary operational-coverage lens.

- **(REINFORCED) Update behavioral assertions in-place when a
  spec change lifts them.** M29.1 removed `test_refuses_null_amount_at_m28`
  and M29.2 updated `AccountingJournalEntriesPage.test.tsx::opens
  the JE dialog pre-populated` — both because the earlier
  behavioral contract was intentionally lifted, and asserting
  the old behavior would be a stale-contract lock rather than a
  useful regression guard. Distinct from the M29.2 blank-entry
  regression guard test on `NewJournalEntryDialog`, which
  explicitly locks the M27.2 blank-entry contract that remains
  in force.

## 6. Streak accounting at M29 close

- **Planning-time as-recommended streak:** **8** (unchanged
  from M29.0 close). M29.1 + M29.2 both pure implementation of
  the M29.0 locked plan; no re-litigation required. Historical
  run of 89 across M10 → M23 preserved for the record.
- **Zero-drift permission-class streak:** **29 consecutive
  milestones** (M10 → M29). M29 shipped no new endpoints and no
  new permission classes; the M28.1 combined-verb
  `admin/accounting/journal-entry-templates/` endpoint continued
  reusing `_M131_PERMS` at M29.
- **Substrate-compound-value continuation:** **3 links realized**
  (M27.1 → M28.1 → M29). M29 completes the payoff of the M28.1
  forward-compat schema reservation.
- **DoD exception path invocations:** **4** (M26 + M27.1 +
  M28.1 + M29.1). Pattern now well-established; future
  infrastructure-only sub-increments can invoke it with
  confidence.

## 7. Baselines at M29 close

- Backend: **4,871 pass**, 1 skipped, 0 fail. (M28 close 4,855
  → +16 at M29.1.)
- Frontend Vitest: **282 pass** across 36 files. (M28 close 270
  → +12 at M29.2.)
- Acceptance: **20 journeys** (M28 close 19 → +1 at M29.2).
- Audit: **156 / 122 covered / 34 backend-only / 315 service
  verbs** (byte-identical baseline to M28.2 close).
- DRF admin surface: **116** endpoints (unchanged).
- Frontend operator routes: **20** (unchanged).
- Permission classes: **7 actual** (unchanged).
- Migrations: `0001`–`0050` (unchanged; no new migration at M29).
- `manage.py check` + `makemigrations --check --dry-run` clean.
- `tsc --noEmit` clean across frontend + acceptance workspaces.

## 8. Corrections (post-close)

None yet.

## 9. Evidence-based candidates for M30

**Elevated (strong recommendation strength for M30.0):**

- **NEW — Template edit / delete UI.** M28 §3 deferral held
  through M29; `is_active` still lives only at the DB layer with
  no operator surface. Substrate to build on: M28.2 templates
  section + M29.2 chip/Override infrastructure. Small-to-
  moderate scope; direct operator-facing value (mid-year chart-
  of-accounts correction; deactivate stale templates without DB
  access). Would extend the M28/M29 template surface into a
  third increment on the same lineage.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29 deferral, unchanged). Requires SESSION-189-
  §3-style tracing at M30.0 open. Blast radius unknown.
- **NEW O3 — Rows-1–4 plain-string-literal investigation**
  (M26/M27/M28/M29 deferral). Requires tracing.
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M28.2 → M29.2 close
  (`sales_manager/daily_startup`, `recon/workflow`,
  `office/accounting_workflow` trial-balance snapshot). Compound
  CI-stability value grows as the suite grows (now 20 journeys).
- **NEW C — F&I chargeback substrate.** Would reuse M27.1
  gl-accounts substrate + M28.1 template substrate. Continues
  the substrate-compound-value lineage into a fourth link if
  operator evidence surfaces during a pilot.

**Gated (unchanged from M28+M29 close):**

- T (real tester feedback); U (hosted-demo substrate); L (first-
  live-pilot staging); M (multi-operator support — breaks the
  zero-drift streak with intent).

**Deferred pending evidence (unchanged):**

- D (LLM router / cost caps); C (F&I chargeback — moved to
  elevated with substrate framing above).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M29 §3, M28 §3, M27 §3, M25 §4 (all valid for
later re-entry):**

- Fully-variable UX polish (Repeat last amounts); server-
  recorded instantiation audit trail; named / shared template
  variables; historical-template back-reference on
  `JournalEntry`; server-side template search / pagination;
  `?include_inactive=true` endpoint exposure; standalone
  template detail page; standalone Chart of Accounts page/route;
  JE edit/update; `posted_by_user` override; advanced picker
  filtering; server-side gl-accounts search/pagination;
  `?include_inactive=true` on gl-accounts; secondary
  "+ Record test drive" launch point; clickable "Referred by"
  nav; named-platform webhook adapters; attribution rollups;
  vehicle-picker advanced filters.

**Standing question for M30:** should the substrate-compound-
value framing continue for a fourth link (template edit/delete
UI on the M28+M29 base, OR F&I chargeback substrate on the
M27.1 base), or should M30 spend the substrate-integrity audit-
refinement path (O2 + O3 as a combined M26-analogous milestone)?
Evidence at M29 close does not force either path. The primary
operational-coverage lens would favor template edit/delete UI
(direct operator gain); the substrate-integrity framing would
favor O2+O3 (compound-infrastructure gain).
