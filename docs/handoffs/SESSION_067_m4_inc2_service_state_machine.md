---
title: "SESSION_067 handoff — Milestone 4 · Increment 2 (recon service + state machine)"
status: historical
type: handoff
date: 2026-08-01
session: 067
milestone: 4
milestone_status: in-progress
increment: 2
increment_status: shipped
commit: TBD
---

# SESSION_067 — Milestone 4 · Increment 2 (M4.2 — recon service + state machine)

## What shipped

The business layer for recon decisions and work-order state
transitions. One new service module
(`backend/dealer_ai/services/recon.py`, ~800 lines), four
domain error classes, ten public service functions, and two
new `@property` accessors on `Vehicle`. Plus **66 focused
service tests** and **two narrow planning amendments** to
`MILESTONE_4_PLANNING.md` (enum reconciliation for the M4.1
shipped vocabularies, and a §1.0.QC-GAP annotation
renegotiating Q13 down from "verified" to "marked
complete").

**Zero ledger integration.** Per the SESSION_067 brief's
pushback on ledger-hook stubs, `services/recon.py` contains
no `add_cost` call, no hook seam, no no-op placeholder. The
M4.3 ledger implementation will extend the transition
functions with narrow internal helpers via a reviewed
refactor.

**Zero migrations.** Zero API endpoints. Zero permission
classes. Zero frontend changes. Zero AI role. Zero
`VehicleCost` rows created by any M4.2 code path (locked by
regression tests).

## Session preamble — two planning amendments before code

The user approved M4.1 with one prerequisite: reconcile
three enum divergences between the M4.1 shipped code and the
draft `MILESTONE_4_PLANNING.md` §1.6 field-shape list. That
reconciliation had to land as an annotation *before* M4.2
service code was written, because the M4.5 vendor-comm
service will consume the exact enum vocabulary and needs
canonical justification for the shipped shape. In the same
pass, I added a QC-GAP annotation flagging that
`WorkOrder.completed_at` does NOT answer Q13 ("was the work
verified?") — completion timestamps prove *when* work was
marked complete, not *whether* it was verified. The M4.2
service therefore does not accept a `qc_verified` parameter
and no QC field is set anywhere.

### The two planning amendments (docs-only)

1. **§1.6.SHIPPED — enum reconciliation.** New sub-section
   after §1.6, before §1.7. Justifies the three shipped
   vocabularies against the draft:
   - **Kind** shipped as `(vendor_comm, parts_order,
     narrative)` — smaller, durable classification of
     communication role rather than per-message intent
     taxonomy. Explains where the original `assignment /
     status_check / invoice_question / general_note` intents
     live in the shipped schema (in `draft_content` /
     `sent_content` prose; in `direction`; in `channel`).
   - **Channel** shipped adds `internal_note` (5 values
     instead of 4). Justifies internal_note as a channel
     because it applies to any of the three kinds — not
     just narrative — and the operator may record
     internal-only notes about a vendor_comm or parts_order
     that already went out via a different channel.
   - **Status** shipped without `failed` (4 values instead
     of 5). Justifies removal because M4 v1 has no live
     send path; a `failed` status without live sending is a
     false affordance. Documents Options A (add `failed`
     back when send is wired) and B (sibling
     `VendorCommunicationSendAttempt` model) for whoever
     picks up prod-send.
   - Confirms no research-cited operational question loses
     answerability under the shipped enums.

2. **§1.0.QC-GAP — Q13 renegotiated.** New sub-section
   after §1.0 questions table. Flags that
   `WorkOrder.completed_at` proves *when work was marked
   complete*, not *whether it was verified*. Documents
   Path A (recommended, deferred): future `QcVerification`
   model. Path B: `qc_verified_at` / `qc_verified_by` /
   `qc_notes` fields on WorkOrder directly. Both explicitly
   deferred outside M4.2 – M4.4. §1.3 WorkOrder header
   updated to remove Q13 from the "answered" list; §1.0
   footnote below the questions table updated to point at
   the QC-GAP annotation. M4.2 service explicitly does not
   accept `qc_verified` parameter (locked by test).

## Pushback on the "ledger hook stub" pattern

The M4.2 recommended-scope block I drafted in the M4.1
handoff proposed a stub-hook pattern
(`_post_estimate_hook`, `_post_actual_hook`, etc. as no-op
functions M4.3 would fill in). The SESSION_067 brief
pushed back on this pattern:

> Do not add a no-op function that looks like ledger
> integration occurred. M4.2 should contain no ledger call
> at all. M4.3 can extend the transition functions through
> a narrow internal helper or reviewed refactor. A silent
> stub risks tests proving a false contract.

I adopted the correction. `services/recon.py` contains
**zero** `_post_*` functions, **zero** ledger imports,
**zero** references to `add_cost` or `VehicleCost`. M4.3
will refactor the transition functions to add ledger calls
at that time. The compensating discipline is a regression
test (`ZeroLedgerSideEffectsAcrossAllTransitions`) that
walks the entire lifecycle and asserts
`VehicleCost.objects.count()` is unchanged.

## Read-first pass performed

Per the start-here doc's recommended sequence, read in
order:

1. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.1 (recon
   decision semantics), §1.3 (WorkOrder state), §1.4
   (attach/detach through table), §1.6 (before writing
   the §1.6.SHIPPED annotation), §1.7 (Vehicle read-model
   extension), §5.c (state machine allowed transitions),
   §5.e (SESSION_066 refinement — noted that M4.2 stubs
   deliberately absent per SESSION_067 pushback), §7 M4.2
   entry.
2. `docs/handoffs/SESSION_066_m4_inc1_core_models.md` —
   the "Recommended exact scope for SESSION_067" section.
3. `backend/dealer_ai/services/condition_report.py` — M3.2
   service module as the template (state machine +
   cross-tenant guard entry pattern; the
   `_refresh_and_assert_draft` shape).
4. `backend/dealer_ai/services/vehicle_ledger.py::add_cost`
   signature — read but explicitly NOT imported into
   `services/recon.py`.
5. `backend/dealer_ai/models.py` — reread the M4.1 models
   from SESSION_066 (Vendor, ReconDecision, WorkOrder,
   WorkOrderFinding, WorkOrderPart, VendorCommunication)
   + the two existing `Vehicle` @property accessors
   (`latest_condition_report`, `latest_completed_condition_report`)
   as the shape M4.2 mirrors.

## Concrete deliverables

### Service module (`backend/dealer_ai/services/recon.py`)

New file, ~800 lines. Ten public functions + four domain
errors + three cross-tenant guard helpers + one transition
locking helper.

**Public functions (ten):**

- `record_decision(finding, *, dealership, tier,
  decided_by=None, decided_at=None, notes="") -> ReconDecision`
  — upsert-while-not-yet-authorized; requires completed
  parent report; refuses tier not in
  `RECON_DECISION_TIER_CHOICES`; locks decision once any
  linked WorkOrder has left draft (raises
  `ReconImmutableError`).
- `create_work_order(vehicle, *, dealership, category, venue,
  vendor=None, assignee=None, estimated_cost=None,
  estimated_completion_date=None, notes="") -> WorkOrder` —
  always creates in `status='draft'`; refuses cross-tenant
  vehicle + vendor; refuses outsourced-without-vendor
  (re-raised as `InvalidReconTransitionError`).
- `attach_findings(work_order, *, dealership,
  finding_ids: Sequence[int]) -> list[WorkOrderFinding]`
  — batch-atomic; deduplicates input; skips existing links;
  refuses when: WO status != draft, finding cross-tenant,
  parent report != complete, finding.vehicle != WO.vehicle,
  ID does not exist. Returns deterministically ordered
  links by finding_id.
- `detach_finding(work_order, finding, *, dealership) -> None`
  — draft-only; raises when link does not exist.
- `approve_work_order(work_order, *, dealership,
  approved_by, authorized_cost=None) -> WorkOrder` —
  draft→approved or idempotent approved→approved (refreshes
  `approved_at`, preserves original `approved_by`, permits
  `authorized_cost` update); refuses when
  `finding_links.count() == 0`.
- `start_work_order(work_order, *, dealership, started_by)
  -> WorkOrder` — approved→in_progress one-way; refuses
  repeat starts.
- `complete_work_order(work_order, *, dealership,
  completed_by, actual_cost,
  actual_completion_date=None) -> WorkOrder` —
  in_progress→completed only (no direct approved→completed
  per planning §5.c); requires nonnegative Decimal
  `actual_cost`; sets `actual_completion_date` to today if
  omitted. **Does NOT accept `qc_verified` per the
  §1.0.QC-GAP annotation.**
- `cancel_work_order(work_order, *, dealership,
  cancelled_by, cancellation_reason="") -> WorkOrder` —
  any nonterminal source; reason required for
  approved/in_progress source (nonblank string check).
- `open_work_orders_for_vehicle(vehicle, *, dealership)`
  — read helper backing `Vehicle.open_work_orders`;
  ordered by `-created_at`; filters non-terminal.
- `has_recon_decisions_for_vehicle(vehicle, *, dealership)
  -> bool` — read helper backing `Vehicle.has_recon_decisions`;
  uses `.exists()` (no full load).

**Domain errors (four):**

- `CrossTenantReconError(ValueError)` — fail-closed guard
  at every service entry against Vehicle / Finding / WO /
  Vendor tenant mismatch.
- `ReconImmutableError(ValueError)` — reconsideration lock
  after a linked WO has left draft; distinct class so M4.6
  API can map to 409 with a different remediation message.
- `InvalidReconTransitionError(ValueError)` — illegal
  state transition (draft→completed, in_progress→approved,
  approve-without-findings, attach-on-non-draft, etc.).
- `IncompleteConditionReportError(ValueError)` — target
  finding belongs to a report whose status is not
  `complete`.

**Cross-tenant guard helpers (three, private):**

- `_assert_vehicle_tenant`, `_assert_finding_tenant`,
  `_assert_work_order_tenant` — mirror
  `services/condition_report.py::_assert_*_tenant` shape.

**Transition locking helper (one, private):**

- `_load_for_transition(work_order)` — SELECT ... FOR
  UPDATE the row inside the caller's transaction so the
  from-state check sees committed data and no concurrent
  transaction can flip the status underneath.

**Module-level constants (two frozensets, exposed for
tests):**

- `_OPEN_STATUSES = {draft, approved, in_progress}` —
  drives the open-work-orders filter and cancel-source
  check.
- `_DECISION_LOCKING_WORK_ORDER_STATUSES = {approved,
  in_progress, completed, cancelled}` — drives the
  reconsideration lock.

### Vehicle read-model extension (`backend/dealer_ai/models.py`)

Two new `@property` accessors on the `Vehicle` class,
appended after the M3.3 accessors:

- `Vehicle.open_work_orders` — one-line delegation to
  `open_work_orders_for_vehicle(self, dealership=self.dealership)`.
  Function-local import (avoids the same cycle the M3.3
  properties document).
- `Vehicle.has_recon_decisions` — one-line delegation to
  `has_recon_decisions_for_vehicle(...)`. Same pattern.

Both properties: no caching, no business logic on the
Vehicle side, tenant scoping resolved via
`self.dealership` per M3.3 precedent.

### Planning amendments (docs-only)

- `docs/roadmap/MILESTONE_4_PLANNING.md`:
  - `§1.0` questions table + trailing paragraph — Q13
    moved from "work-order state machine + QC lifecycle"
    grouping to a standalone §1.0.QC-GAP annotation.
  - **New §1.0.QC-GAP annotation** — full renegotiation
    of Q13; Path A + Path B documented; scope explicitly
    deferred.
  - `§1.3` WorkOrder header — Q13 removed from the
    answered list; sentence added explaining
    completion-timestamps-are-not-QC.
  - **New §1.6.SHIPPED annotation** — full three-enum
    reconciliation (kind / channel / status).
  - Unrelated sections untouched.

### Tests

One new file, `backend/dealer_ai/tests/test_recon_service.py`
(~1,300 lines), 66 focused tests across nine test classes:

- `RecordDecisionCreate` (2) — happy-path + default
  `decided_at`.
- `RecordDecisionRequiresCompletedReport` (1) — draft
  report rejected + no side-effect row.
- `RecordDecisionCrossTenantRejection` (1) — cross-tenant
  finding rejected.
- `RecordDecisionTierValidation` (1) — invalid tier raises.
- `RecordDecisionReconsideration` (3) — upsert before WO
  approval, upsert while WO still draft, lock once linked
  WO approved.
- `RecordDecisionNoSideEffects` (1) — zero WO / VehicleCost
  created.
- `CreateWorkOrderShape` (4) — draft-only birth,
  outsourced-without-vendor raises, in-house without
  vendor, outsourced with vendor succeeds.
- `CreateWorkOrderCrossTenant` (2) — vehicle + vendor.
- `CreateWorkOrderNoLedgerSideEffect` (1) — zero
  VehicleCost created.
- `AttachFindingsShape` (4) — ordered links, dedupe,
  skip-existing, empty input.
- `AttachFindingsGating` (5) — non-draft WO refused,
  missing ID batch-atomic refused, draft-report refused,
  cross-vehicle refused, cross-tenant caller refused.
- `AttachFindingsManyToMany` (1) — one finding across two
  WOs.
- `DetachFinding` (3) — draft removes, non-draft refused,
  nonexistent link refused.
- `ApproveWorkOrder` (5) — draft→approved, no-findings
  refused, idempotent re-approve preserves original
  approver + refreshes timestamp + updates authorized_cost,
  approve-from-in_progress refused, cross-tenant refused.
- `StartWorkOrder` (3) — approved→in_progress + sets
  provenance + preserves approval, repeat-start refused,
  start-from-draft refused.
- `CompleteWorkOrder` (4) — in_progress→completed happy
  path, missing actual_cost raises, negative actual_cost
  raises, direct approved→completed refused.
- **`CompletionDoesNotClaimQc` (2)** — schema check that
  no `qc_*` field exists on WorkOrder; signature check
  that `complete_work_order` does not accept
  `qc_verified` / `qc_verified_by` kwargs. **This is the
  QC-GAP lock — the load-bearing test from the
  SESSION_067 brief.**
- `CancelWorkOrder` (5) — draft-no-reason OK,
  approved-requires-nonblank-reason (empty + whitespace-
  only rejected + nonblank succeeds), in-progress
  preserves start provenance, completed rejected,
  cancelled-from-cancelled rejected.
- `ZeroLedgerSideEffectsAcrossAllTransitions` (2) — full
  lifecycle creates no VehicleCost; cancel-from-approved
  creates no VehicleCost. Regression boundary for the
  M4.3 refactor.
- `RefreshBeforeStateCheck` (1) — stale in-memory status
  does not bypass the select_for_update + refresh_from_db
  guard.
- `OpenWorkOrdersProperty` (5) — empty, includes
  draft+approved, excludes completed+cancelled,
  deterministic ordering, tenant isolation.
- `HasReconDecisionsProperty` (5) — false without report,
  false with draft report, false with completed report but
  no decisions, true with at least one decision, uses
  .exists() (large-N sanity).
- `M3ReportsAndFindingsUnchanged` (1) — full lifecycle
  leaves `report.updated_at` + `finding.updated_at`
  unchanged; report still complete; finding still exists.
- `ServiceHelperDirectInvocation` (2) — service function
  output == @property output.
- `ModuleConstantsExported` (2) — locks the
  `_OPEN_STATUSES` and
  `_DECISION_LOCKING_WORK_ORDER_STATUSES` frozenset
  vocabularies against silent drift.

**Total new tests: 66.**

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,285 pass, 1
  skipped, 0 fail** (up from 2,219; +66 new tests).
- `python3 manage.py check` → "System check identified no
  issues (0 silenced)."
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- **No new migration files.** M4.2 is service + property
  layer only.
- `git status --short frontend/ backend/dealer_ai/permissions.py
  backend/dealer_ai/views.py backend/dealer_ai/urls.py`
  → empty. No API / permissions / URL / frontend files
  changed.
- **Zero `VehicleCost` rows** created by any M4.2 code
  path (locked by
  `ZeroLedgerSideEffectsAcrossAllTransitions`).

## Compatibility (M1 + M2 + M3 + M4.1 substrate)

Preserved unchanged:

- **Tenancy substrate.** `get_default_dealership` /
  `get_current_dealership` / `get_active_membership`
  signatures unchanged. `_TENANT_CARRIER_MODEL_NAMES`
  unchanged (still 15 entries from SESSION_066).
- **Identity + authentication.** No permission changes.
- **M2 ledger substrate.** `services/vehicle_ledger.py`
  API unchanged. Zero calls into it from `services/recon.py`.
  `VehicleCost` immutability unchanged.
  `total_investment` semantic contract unchanged.
- **M3 substrate.** `services/condition_report.py` API
  unchanged (M4.2 imports one function —
  `latest_completed_condition_report` — for
  `has_recon_decisions_for_vehicle`; no side effects).
  Completed condition reports remain immutable.
  `ConditionFinding.estimated_cost` still documentation-
  only (M4.2 does not read it as input to any WorkOrder
  field).
- **M4.1 substrate.** Model shapes untouched. The two
  new `@property` accessors on `Vehicle` are additive —
  existing accessors and fields unchanged.
- **Frontend contracts.** No frontend files touched.
- **Safety stack.** No `services/llm_safety.py` change.
  No new scrub. M4.5 owns the recon scrub.

## Explicitly out of scope for M4.2 (deferred to specific
increments)

- ❌ Any `VehicleCost` row creation — M4.3 (ledger
  integration + estimate retirement per SESSION_066
  refinement).
- ❌ Any `add_cost` call — M4.3.
- ❌ Any ledger-hook stub or seam — deliberately absent
  per SESSION_067 brief pushback. M4.3 refactors the
  transition functions to add ledger calls.
- ❌ Parts service (add/order/receive/install/return
  transitions) — M4.4.
- ❌ Vendor communication drafting + LLM path — M4.5.
- ❌ `_scrub_invented_recon_fact` — M4.5.
- ❌ Admin API endpoints — M4.6.
- ❌ New permission class — M4.6.
- ❌ Frontend — M4.7.
- ❌ AI role — nowhere.
- ❌ QC verification (Q13 renegotiated to §1.0.QC-GAP
  annotation) — future increment (Path A recommended).

## Files changed

- `backend/dealer_ai/services/recon.py` — new file, ~800
  lines (10 public functions + 4 domain errors + 3
  guard helpers + 1 locking helper + 2 module constants).
- `backend/dealer_ai/models.py` — added two `@property`
  accessors on `Vehicle` (`open_work_orders`,
  `has_recon_decisions`) after the M3.3 accessors.
- `backend/dealer_ai/tests/test_recon_service.py` — new
  file, ~1,300 lines (66 tests across 20 test classes).
- `docs/roadmap/MILESTONE_4_PLANNING.md`:
  - §1.0 questions table trailing paragraph — Q13
    reference updated.
  - §1.0.QC-GAP — new annotation.
  - §1.3 WorkOrder header — Q13 removed from answered
    list.
  - §1.6.SHIPPED — new enum reconciliation annotation.
  - Unrelated sections untouched.
- `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
  — this handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_068
  = M4.3 priority.

## Recommended exact scope for SESSION_068 (M4.3 — ledger
integration + estimate retirement)

Per `MILESTONE_4_PLANNING.md` §7 M4.3 (locked at
SESSION_065; refined at SESSION_066):

**Scope.** Refactor the four transition functions
(`approve_work_order`, `complete_work_order`,
`cancel_work_order`, plus the estimate-revision path
that patches `estimated_cost` on an approved WO) to call
into `services/vehicle_ledger.add_cost` at the right
moments. Add five module-level constants for the
reference-key vocabulary. Zero-drift on the M4.2
state-machine semantics — M4.3 is purely additive
ledger integration.

**New module constants:**

- `WORKORDER_LEDGER_REF_ESTIMATE = "WORKORDER:{wo_id}:estimate:{seq}"`
- `WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:estimate_reversal:{seq}"`
- `WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:completion_estimate_reversal"`
- `WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL = "WORKORDER:{wo_id}:estimate_reversal:cancel"`
- `WORKORDER_LEDGER_REF_ACTUAL = "WORKORDER:{wo_id}:actual"`

**New private helpers:**

- `_post_estimate(work_order, *, seq)` — posts
  `add_cost(is_estimate=True, ...)` under the
  `estimate:<seq>` key; idempotent.
- `_post_estimate_reversal(work_order, *,
  outstanding_amount, seq)` — negative-amount reversing
  entry under `estimate_reversal:<seq>`.
- `_post_completion_reversal(work_order, *,
  outstanding_amount)` — negative-amount reversal under
  the one-shot `completion_estimate_reversal` key
  (SESSION_066 refinement).
- `_post_cancel_reversal(work_order, *,
  outstanding_amount)` — negative-amount reversal under
  `estimate_reversal:cancel`.
- `_post_actual(work_order)` — posts
  `add_cost(is_estimate=False, ...)` under `actual`;
  idempotent.

**Refactor points in existing transition functions:**

- `approve_work_order` (both draft→approved and idempotent
  approved→approved) calls `_post_estimate` when
  `estimated_cost` is non-null.
- Estimate revision path (a new function or a widened
  parameter on `approve_work_order` — decide at
  implementation time) posts
  `_post_estimate_reversal(outstanding=<old>, seq=old_seq)`
  + `_post_estimate(seq=old_seq + 1)`.
- `complete_work_order` calls
  `_post_completion_reversal(outstanding=<current>)` +
  `_post_actual` atomically inside the transaction.
- `cancel_work_order` calls
  `_post_cancel_reversal(outstanding=<current>)` when
  the WO had any outstanding estimate at cancel time.
  Preserves any partial actual posted before cancel
  (they represent work truly performed).

**Vendor snapshot.** Every `add_cost` call passes
`vendor=work_order.vendor.name if work_order.vendor else ""`
so `VehicleCost.vendor` free-text captures the snapshot
at posting time. Vendor rename does not rewrite history.

**Tests target.** ~35 focused tests: estimate posts on
approval; actual posts on completion; **completion-time
estimate reversal atomic with actual** (SESSION_066
refinement); **net estimate contribution = Decimal("0.00")
for terminal WO**; **projected_total_investment does not
double-count completed WOs**; cancellation reverses
outstanding estimate; double-approve idempotent;
double-complete raises; ConditionFinding.estimated_cost
never triggers a post (M3.5 invariant preserved);
VehicleCost.vendor free-text captures work_order.vendor.name;
inactive vendor still readable in historical rows; sequential
estimate updates produce correct reversing pattern;
mid-completion crash leaves ledger untouched (atomicity
test).

**Backend baseline.** 2,285 → ~2,320. **No migrations.**
No new files (extends `services/recon.py`; adds
`test_recon_ledger.py`).

**Explicit non-goals for M4.3.**

- ❌ Do NOT modify M4.1 model shapes.
- ❌ Do NOT modify M4.2 state-machine semantics — only
  add ledger calls at existing transitions.
- ❌ Do NOT modify `services/vehicle_ledger.py` — only
  call `add_cost`.
- ❌ Do NOT touch M4.4+ scope.
- ❌ Do NOT add QC fields (per §1.0.QC-GAP annotation;
  QC lands in a future increment via Path A / B).

## Anchors that win on conflict for SESSION_068

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every service
   entry point threads `dealership=` explicitly.
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §5.e
   (SESSION_066 refinement — reference-key vocabulary +
   completion-time estimate reversal invariant) is
   load-bearing for M4.3. §7 M4.3 locks the helper
   signatures.
6. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
   — this handoff (M4.2 state-machine + no-ledger
   contract).
7. `docs/handoffs/SESSION_066_m4_inc1_core_models.md` —
   the M4.1 model shapes M4.3 posts against.
8. `docs/handoffs/SESSION_065_m4_planning.md` — the
   ten-decision resolutions.
9. `docs/roadmap/MILESTONE_2_PLANNING.md` §2 — the
   `services/vehicle_ledger.add_cost` API contract M4.3
   consumes.
10. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
    (reversing-entry pattern from ACCOUNTING §2.11).
11. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6
    lessons.
12. `docs/research/RECON_MAPPING.md` §5.4 (authorized cost
    vs actual) + §14 (bottlenecks driving reversal cases).
