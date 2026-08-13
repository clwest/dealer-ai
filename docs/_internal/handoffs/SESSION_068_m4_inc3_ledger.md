---
title: "SESSION_068 handoff — Milestone 4 · Increment 3 (ledger integration)"
status: historical
type: handoff
date: 2026-08-01
session: 068
milestone: 4
milestone_status: in-progress
increment: 3
increment_status: shipped
commit: 568d81e
---

# SESSION_068 — Milestone 4 · Increment 3 (M4.3 — ledger integration + estimate retirement)

## What shipped

Ledger integration wired into the M4.2 recon service. Five
reference-key module constants, five private `_post_*`
helpers, one new public function (`revise_estimate`), and
refactors to `approve_work_order` / `complete_work_order` /
`cancel_work_order` to invoke the helpers at the right
transitions. Plus a **category-mapping table** documented in
planning §5.e (SESSION_068) and locked at runtime by the
service module's
`_WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY` dict.

33 focused ledger tests in the new
`test_recon_ledger.py`, plus updated regression coverage in
`test_recon_service.py` (the M4.2 zero-ledger class flipped
to a "no ledger side effects **without** estimated_cost"
class since M4.3 posts ledger rows whenever `estimated_cost`
is set OR `actual_cost` is supplied at completion).

**Zero migrations.** Zero API endpoints. Zero permission
classes. Zero frontend changes. Zero AI role.

## Session preamble

No planning refinements needed at session open — the
SESSION_066 planning refinement (§5.e reference-key
vocabulary + completion-time reversal) and the SESSION_067
annotations (§1.0.QC-GAP, §1.6.SHIPPED) fully anchored M4.3.
The only planning-doc addition is a new §5.e appendix
documenting the WorkOrder → VehicleCost category mapping
table adopted here.

## Read-first pass performed

Per the start-here doc's recommended sequence:

1. `docs/roadmap/MILESTONE_4_PLANNING.md` — §3 ledger
   invariants (refined SESSION_066), §5.b Vendor-snapshot
   invariant, §5.e (full estimate-retirement contract), §7
   M4.3 (helper signatures).
2. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
   — the "Recommended exact scope for SESSION_068" section.
3. `backend/dealer_ai/services/vehicle_ledger.py::add_cost`
   — the M2 API M4.3 wraps: signature, tenant guard,
   category validation, negative-amount permitted for
   reversals.
4. `backend/dealer_ai/services/vehicle_ledger.py::compute_totals`
   + `LedgerTotals` dataclass — the M2 read surface used to
   verify the anti-double-count invariant.
5. `backend/dealer_ai/services/recon.py` — the M4.2 service
   the refactor extends. Confirmed the transition functions
   already run inside `transaction.atomic()` blocks.
6. `backend/dealer_ai/models.py::VehicleCost` — the model
   receiving the auto-minted rows. Confirmed
   `is_estimate=True` for all estimate / reversal families
   and `is_estimate=False` only for actuals.

## Concrete deliverables

### Reference-key vocabulary (five module-level constants)

Added to `backend/dealer_ai/services/recon.py` at module
top:

```python
WORKORDER_LEDGER_REF_ESTIMATE = "WORKORDER:{wo_id}:estimate:{seq}"
WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:estimate_reversal:{seq}"
WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:completion_estimate_reversal"
WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL = "WORKORDER:{wo_id}:estimate_reversal:cancel"
WORKORDER_LEDGER_REF_ACTUAL = "WORKORDER:{wo_id}:actual"
```

Locked at test `ReferenceKeyFormatStrings` (five tests, one
per family) so a refactor cannot silently drift them.

### Category-mapping table

Added to `services/recon.py` as
`_WORK_ORDER_CATEGORY_TO_LEDGER_CATEGORY` (12 entries,
CONDITION_CATEGORY_* → VehicleCost CATEGORY_*). Rationale
inline. Documented in planning §5.e; regression coverage at
`CategoryMappingCompleteness`.

### Five private ledger-posting helpers

- `_post_estimate(work_order, *, seq, actor=None)` —
  initial or revised estimate. Returns `None` when
  `estimated_cost` is null (nothing to estimate) or when
  the reference key already exists (idempotent replay).
- `_post_estimate_reversal(work_order, *, outstanding_amount, seq, actor=None)`
  — mid-life reversal matched to a prior `estimate:<seq>`.
  Called from `revise_estimate`.
- `_post_completion_reversal(work_order, *, outstanding_amount, actor=None)`
  — one-shot completion-time reversal under
  `completion_estimate_reversal`. Called only from
  `complete_work_order`.
- `_post_cancel_reversal(work_order, *, outstanding_amount, actor=None)`
  — cancellation reversal under
  `estimate_reversal:cancel`. Called only from
  `cancel_work_order`.
- `_post_actual(work_order, *, actor=None)` — actual cost
  under `actual`. Uses `actual_completion_date` for
  `incurred_at`.

Every helper: (a) idempotency-checks via
`VehicleCost.objects.filter(reference=<key>).exists()`, (b)
returns `None` when there is nothing to post, (c) passes
`vendor=<snapshot>` via `_vendor_snapshot(work_order)` so
the M2 free-text captures the vendor name at posting time
(planning §5.b Option C invariant preserved), (d) passes
`category=_ledger_category_for(work_order)` via the mapping
table above.

### Three additional private helpers

- `_ledger_category_for(work_order)` — dict lookup.
- `_vendor_snapshot(work_order)` — one-line delegation.
- `_outstanding_estimate_amount(work_order) -> Decimal` —
  signed sum of every estimate + reversal row for the WO's
  reference-key family via `is_estimate=True` +
  `reference__startswith` filter. Returns `Decimal("0.00")`
  when no estimate rows exist.
- `_next_estimate_seq(work_order) -> int` — max seq + 1
  across the WO's `estimate:*` family. Starts at 1.

### New public function

- `revise_estimate(work_order, *, dealership,
  new_estimated_cost, revised_by=None) -> WorkOrder` —
  separate operator gesture from re-approval. Refuses from
  any status except `approved`. Nonnegative Decimal
  required. Same-value pass-through is a no-op. Posts
  reversal + new estimate atomically inside a
  `transaction.atomic()` block. Updates
  `work_order.estimated_cost` to the new value. Sequential
  revisions produce monotonic `estimate:1 → :2 → :3 → ...`
  plus matching `estimate_reversal:1 → :2 → ...`.

### Transition function refactors

- **`approve_work_order`** — draft→approved path calls
  `_post_estimate(seq=_next_estimate_seq(wo))` after saving.
  Idempotent approved→approved path unchanged (does NOT
  revise estimate; that's what `revise_estimate` is for).
- **`complete_work_order`** — after saving, calls
  `_post_completion_reversal(outstanding=_outstanding_estimate_amount(wo))`
  + `_post_actual` inside the same `transaction.atomic()`
  block. A mid-completion crash rolls back both the WO
  save and the ledger writes.
- **`cancel_work_order`** — after saving, calls
  `_post_cancel_reversal(outstanding=<current>)` inside
  the same transaction. Zero when nothing was estimated.

Public signatures unchanged. State-machine semantics
unchanged.

### Planning amendment

- `docs/roadmap/MILESTONE_4_PLANNING.md` §5.e — new
  "Category mapping" appendix documenting the 12-entry
  WorkOrder → VehicleCost category table with rationale.
  Unrelated sections untouched.

### Tests (33 new in `test_recon_ledger.py`)

- `ReferenceKeyFormatStrings` (5) — locks the five format
  strings exactly.
- `CategoryMappingCompleteness` (1) — locks all 12 entries.
- `ApproveWithEstimatePostsInitialEstimate` (4) — first
  approval posts, no-estimate case is a no-op, category
  mapping applied, idempotent re-approve does not
  duplicate.
- `VendorSnapshotOnLedgerRow` (4) — snapshot captured,
  rename does not rewrite history, inactive vendor still
  readable, in-house WO posts empty snapshot.
- `CompletionPostsReversalPlusActualAtomically` (5) —
  completion posts reversal + actual with correct signs,
  net estimate = Decimal("0.00") after completion,
  projected_total_investment no longer double-counts,
  completion with no prior estimate posts only actual,
  atomic-completion rollback on validation failure
  (patches `_post_actual` to raise mid-transaction).
- `ReviseEstimate` (8) — first revision, work-order field
  updated, same-value no-op, sequential revisions
  monotonic, negative rejected, from-draft rejected,
  from-completed rejected, revision-then-completion still
  nets zero.
- `CancelPostsEstimateReversal` (3) — cancel from approved
  reverses, cancel from draft posts nothing, cancel after
  revision reverses current outstanding.
- `IdempotencyOnReplay` (2) — direct helper replay does
  not duplicate estimate; direct helper replay does not
  duplicate actual.
- `ConditionFindingEstimatedCostStillDoesNotPost` (1) —
  M3.5 invariant preserved.

Plus `test_recon_service.py::NoLedgerSideEffectsWithoutEstimate`
(replaces the M4.2 `ZeroLedgerSideEffectsAcrossAllTransitions`
class; 2 tests): approve without estimated_cost posts no
row; cancel without outstanding estimate posts no row.
These preserve the invariant "M4.3 does not fabricate cost
rows when there was nothing to estimate."

**Total new tests: 33.**

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,318 pass, 1
  skipped, 0 fail** (up from 2,285; +33 M4.3 ledger tests).
- `python3 manage.py check` → clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- **No new migration files.** M4.3 is service-layer only.
- No frontend / permissions / URL / view files changed.

## Compatibility

Preserved unchanged:

- **M1 substrate.** Tenancy resolvers unchanged.
- **M2 ledger substrate.** `services/vehicle_ledger.py`
  API unchanged in signature. `add_cost` receives the new
  reference-key strings additively — the M4.3 rows appear
  in `compute_totals` aggregations without special-casing.
  `VehicleCost` immutability unchanged (M4.3 posts new
  rows; never edits or deletes).
- **M3 substrate.** `services/condition_report.py`
  unchanged. Completed reports still immutable.
  `ConditionFinding.estimated_cost` still never posts to
  `VehicleCost` (locked by
  `ConditionFindingEstimatedCostStillDoesNotPost`).
- **M4.1 substrate.** Model shapes untouched. Six admin
  registrations unchanged.
- **M4.2 substrate.** State machine semantics preserved;
  new ledger calls are additive at the end of the same
  `transaction.atomic()` blocks. The two `Vehicle`
  @property accessors unchanged. `_OPEN_STATUSES` and
  `_DECISION_LOCKING_WORK_ORDER_STATUSES` frozensets
  unchanged.
- **Frontend contracts.** No frontend files touched.

## Explicitly out of scope for M4.3

- ❌ Parts service (add / order / receive / install /
  return transitions) — M4.4.
- ❌ Vendor communication drafting + LLM path — M4.5.
- ❌ `_scrub_invented_recon_fact` — M4.5.
- ❌ Admin API endpoints — M4.6.
- ❌ New permission class — M4.6.
- ❌ Frontend — M4.7.
- ❌ AI role — nowhere.
- ❌ QC verification (per §1.0.QC-GAP annotation).
- ❌ Partial-completion posting on cancel-after-in-progress
  — M4.4 or later; planning §5.e documents the interaction
  but M4.3 does not implement the partial-actual write
  path.

## Files changed

- `backend/dealer_ai/services/recon.py` — extended with
  five reference-key constants + category mapping dict + 
  five `_post_*` helpers + three private helpers +
  `revise_estimate` public function. Approve / complete /
  cancel transition bodies extended with ledger calls
  inside their existing atomic blocks. Module docstring
  updated to reflect M4.3 landed.
- `backend/dealer_ai/tests/test_recon_ledger.py` — new file
  (~700 lines, 33 tests).
- `backend/dealer_ai/tests/test_recon_service.py` — M4.2
  `ZeroLedgerSideEffectsAcrossAllTransitions` class
  replaced with `NoLedgerSideEffectsWithoutEstimate` (2
  tests). Test count in this file unchanged at 66.
- `docs/roadmap/MILESTONE_4_PLANNING.md` — added §5.e
  category-mapping appendix.
- `docs/handoffs/SESSION_068_m4_inc3_ledger.md` — this
  handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_069
  = M4.4 priority.

## Recommended exact scope for SESSION_069 (M4.4 — parts service)

Per `MILESTONE_4_PLANNING.md` §7 M4.4:

**Scope.** Parts-tracking service functions in
`backend/dealer_ai/services/recon.py`:

- `add_part(work_order, *, dealership, name, quantity=1,
  part_number="", source_type="in_stock", source_name="",
  unit_cost=None, notes="") -> WorkOrderPart` — refuses
  when WO is not in a state that permits parts changes
  (`draft`, `approved`, `in_progress`).
- `update_part(part, *, dealership, **updates) -> WorkOrderPart`
  — whitelist: name, description, part_number, quantity,
  unit_cost, source_type, source_name, notes. Status
  transitions happen via dedicated function.
- `transition_part_status(part, *, dealership, new_status,
  actor)` — validates transition (`needed → ordered`,
  `ordered → received`, `received → installed`,
  `ordered → backordered`, `ordered → returned`,
  `received → returned`); sets appropriate timestamp field.
- `delete_part(part, *, dealership) -> None` — only when
  parent WO is `draft`.

**Boundary.** ~30 focused parts-service tests. Backend
baseline: 2,318 → ~2,348. No migrations. No ledger
integration (parts do not currently post to VehicleCost —
their cost lives on the WorkOrder's estimate/actual
aggregate). No frontend. No API.

**Explicit non-goals for M4.4:**

- ❌ Do NOT post parts cost to VehicleCost independently.
- ❌ Do NOT add live parts marketplace / auto-order
  integration (planning §5.h explicit out-of-scope).
- ❌ Do NOT touch M4.5+ scope.

## Anchors that win on conflict for SESSION_069

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` §5.h (parts
   scope), §7 M4.4 (parts service signatures).
6. `docs/handoffs/SESSION_068_m4_inc3_ledger.md` — this
   handoff.
7. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
8. `docs/handoffs/SESSION_066_m4_inc1_core_models.md`
9. `docs/handoffs/SESSION_065_m4_planning.md`
10. `docs/research/RECON_MAPPING.md` §6.1–§6.6 (parts
    sourcing).
