---
title: "SESSION_069 handoff — Milestone 4 · Increment 4 (parts service)"
status: historical
type: handoff
date: 2026-08-01
session: 069
milestone: 4
milestone_status: in-progress
increment: 4
increment_status: shipped
commit: 33438ff
---

# SESSION_069 — Milestone 4 · Increment 4 (M4.4 — parts tracking service)

## What shipped

Parts-tracking service functions added to
`services/recon.py`. Four public functions
(`add_part`, `update_part`, `transition_part_status`,
`delete_part`) plus one private cross-tenant guard
(`_assert_part_tenant`) plus three module-level constants
(`_PART_MUTATION_ALLOWED_WORK_ORDER_STATUSES`,
`_UPDATE_PART_ALLOWED_FIELDS`, `_PART_ALLOWED_TRANSITIONS`).

49 focused tests in the new
`backend/dealer_ai/tests/test_recon_parts.py`.

**Zero migrations. Zero API endpoints. Zero permission
classes. Zero frontend changes. Zero AI role. Zero
`VehicleCost` writes from any parts operation** (planning
§5.h locks the boundary — part costs live on the parent
WorkOrder's estimate/actual aggregate, not on their own
ledger rows).

## Session preamble

No planning refinements needed at session open. The
SESSION_066/067/068 amendments and the M4.1 WorkOrderPart
model shape fully anchored M4.4.

## Read-first pass performed

1. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.5
   (WorkOrderPart field shape), §5.h (parts scope: no
   marketplace, no auto-order, no vendor payment), §7 M4.4.
2. `docs/handoffs/SESSION_068_m4_inc3_ledger.md` — the
   "Recommended exact scope for SESSION_069" section.
3. `backend/dealer_ai/models.py::WorkOrderPart` — 6-value
   status enum, 7-value source-type enum,
   `MinValueValidator(1)` on quantity, four nullable
   per-state date fields.
4. `backend/dealer_ai/services/recon.py` — reviewed M4.2
   `_load_for_transition` + M4.3 helpers as the pattern
   M4.4 mirrors.
5. `backend/dealer_ai/tests/test_work_order.py`
   `WorkOrderPart*` classes — persistence coverage already
   locked; M4.4 layers service semantics on top.

## Concrete deliverables

### Four public parts-service functions

Added to `services/recon.py` after the cancel transition,
before the Vehicle read helpers:

- **`add_part(work_order, *, dealership, name, quantity=1,
  part_number="", description="", source_type="in_stock",
  source_name="", unit_cost=None, notes="") -> WorkOrderPart`**
  — always creates in `status='needed'`. Refuses when
  parent WO status is not one of
  `_PART_MUTATION_ALLOWED_WORK_ORDER_STATUSES` (draft /
  approved / in_progress). Validates `source_type` against
  the 7-value canonical vocabulary. Structural M4.1 clean
  guards (`quantity >= 1`) surface via `full_clean()`.
- **`update_part(part, *, dealership, **updates) -> WorkOrderPart`**
  — whitelist enforcement: 8 fields (`name`, `description`,
  `part_number`, `quantity`, `unit_cost`, `source_type`,
  `source_name`, `notes`). Rejects unknown fields,
  `status`, timestamps, `work_order`, `dealership` via
  `ValueError`. Parent WO status gating same as `add_part`.
- **`transition_part_status(part, *, dealership,
  new_status, actor=None)`** — validates against the
  7-transition table (see below). Auto-populates the
  matching timestamp field. `actor` accepted for future
  audit-trail extension; not currently persisted per
  planning §1.5 (parent WO provenance covers "who ordered
  this recon"). Uses `select_for_update` +
  `refresh_from_db` per M4.2 concurrency pattern.
- **`delete_part(part, *, dealership) -> None`** — hard
  delete permitted only when parent WO is `draft`. Refuses
  on approved / in_progress / completed / cancelled with
  `InvalidReconTransitionError`.

### Transition table

Locked at `_PART_ALLOWED_TRANSITIONS`:

| from state    | to state        | timestamp set  |
|---------------|-----------------|----------------|
| needed        | ordered         | ordered_at     |
| ordered       | received        | received_at    |
| ordered       | backordered     | (none)         |
| ordered       | returned        | returned_at    |
| backordered   | ordered         | ordered_at     |
| received      | installed       | installed_at   |
| received      | returned        | returned_at    |
| installed     | (terminal)      | —              |
| returned      | (terminal)      | —              |

All other transitions raise
`InvalidReconTransitionError`. `installed` and `returned`
are terminal in M4.4 (matches planning §1.5 — a returned
or installed part is history; the operator does not
un-return or un-install).

### Cross-tenant guard

`_assert_part_tenant(part, dealership)` — verifies both
`part.dealership_id` and `part.work_order.dealership_id`.
Mirrors `_assert_work_order_tenant` shape. Every public
function runs this at entry; every public function also
locks the parent WO row via `_load_for_transition` inside
`transaction.atomic()`.

### Concurrency

Every write path:
- Wraps in `transaction.atomic()`.
- Locks the parent WO via `select_for_update` for
  status-gate + write ordering.
- On transition + update, additionally locks the part row
  via `select_for_update` + fresh `.get()` so stale
  in-memory state cannot bypass the gate.

### Tests (49 new in `test_recon_parts.py`)

- `AddPartHappyPath` (3) — creates in needed, default
  source_type is in_stock, customer_supplied permitted.
- `AddPartWorkOrderStatusGating` (5) — draft/approved/
  in_progress OK; completed/cancelled rejected.
- `AddPartValidation` (3) — invalid source_type,
  zero quantity, cross-tenant.
- `AddPartNoLedgerSideEffect` (1) — no VehicleCost row.
- `UpdatePartWhitelist` (7) — whitelisted fields update;
  status, timestamps, work_order, dealership, unknown
  field, invalid source_type all rejected.
- `UpdatePartWorkOrderStatusGating` (2) — in_progress OK;
  completed rejected.
- `UpdatePartCrossTenant` (1) — cross-tenant refused.
- `TransitionPartStatusAllowed` (7) — every allowed
  transition succeeds; each sets the correct timestamp;
  ordered→backordered preserves ordered_at.
- `TransitionPartStatusDisallowed` (6) — needed→received,
  needed→installed, ordered→installed, received→needed,
  installed-is-terminal (5 target-status refusals),
  returned-is-terminal (5 target-status refusals).
- `TransitionPartStatusGating` (3) — completed WO
  rejected; invalid new_status; cross-tenant.
- `TransitionPartStatusRefreshBeforeCheck` (1) — stale
  in-memory status does not bypass gate.
- `DeletePart` (5) — draft OK; approved rejected;
  in_progress rejected; completed rejected; cross-tenant.
- `PartsSurviveTerminalTransitions` (2) — parts survive
  cancellation and completion.
- `NoLedgerSideEffectsFromPartsOperations` (1) — full
  parts lifecycle (add + update + 3 transitions + delete)
  creates no VehicleCost row.
- `PartsModuleConstantsExported` (2) — mutation-allowed
  status set + update whitelist locked.

**Total new tests: 49.**

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,367 pass, 1
  skipped, 0 fail** (up from 2,318; +49 M4.4 parts tests).
- `python3 manage.py check` → clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- **No new migration files.** No API / permissions / URL /
  frontend files changed.

## Compatibility

Preserved unchanged:

- **M1/M2/M3 substrate.** Tenancy resolvers, ledger API,
  condition-report API all unchanged.
- **M4.1 substrate.** WorkOrderPart model shape untouched.
  The `MinValueValidator(1)` shipped in M4.1 remains the
  quantity constraint; M4.4 surfaces it via `full_clean`.
- **M4.2 substrate.** State-machine functions untouched.
  Recon decision / attach-detach / approve / start /
  complete / cancel signatures preserved. Vehicle
  @property accessors unchanged.
- **M4.3 substrate.** Ledger helpers untouched. Reference-
  key vocabulary preserved. Category mapping preserved.
  `revise_estimate` unchanged.
- **Frontend contracts.** No frontend files touched.

## Explicitly out of scope for M4.4

- ❌ Parts cost → VehicleCost independently. Planning §5.h
  locks the boundary: parts contribute to the WO estimate /
  actual aggregate, not to a separate ledger family.
- ❌ Live parts marketplace / auto-order / vendor payment
  integration. Planning §5.h explicit out-of-scope.
- ❌ Vendor communication drafting + LLM path — M4.5.
- ❌ `_scrub_invented_recon_fact` — M4.5.
- ❌ Admin API endpoints — M4.6.
- ❌ New permission class — M4.6.
- ❌ Frontend — M4.7.
- ❌ AI role — nowhere.

## Files changed

- `backend/dealer_ai/services/recon.py` — imports extended
  (WORK_ORDER_PART_STATUS_*, WORK_ORDER_PART_SOURCE_*,
  WorkOrderPart); module docstring updated to reflect M4.4
  landed; ~350 lines added between the cancel transition
  and the Vehicle read helpers (three module constants,
  one guard helper, four public functions).
- `backend/dealer_ai/tests/test_recon_parts.py` — new file
  (~950 lines, 49 tests).
- `docs/handoffs/SESSION_069_m4_inc4_parts.md` — this
  handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_070
  = M4.5 priority.

## Recommended exact scope for SESSION_070 (M4.5 — vendor comm drafting + scrub)

Per `MILESTONE_4_PLANNING.md` §7 M4.5 + §5.g (AI boundary
+ safety scrub):

**Scope.**

- New module `backend/dealer_ai/services/vendor_comm.py`:
  - `draft_communication(work_order, *, dealership,
    drafted_by, kind, channel, extra_notes="") -> VendorCommunication`
    — assembles source bundle from WO + linked findings +
    parts; calls LLM via existing provider factory; runs
    output through post-LLM scrubs including the new
    `invented_recon_fact`; persists row with
    `status="draft"`, `drafted_by`, `drafted_at`,
    `source_provenance`.
  - `approve_communication(comm, *, dealership,
    approved_by) -> VendorCommunication` — draft→approved.
  - `mark_sent(comm, *, dealership, sent_by,
    sent_content=None) -> VendorCommunication` —
    approved→sent; captures optional edited `sent_content`
    (falls back to `draft_content`).
  - `log_communication(work_order, *, dealership,
    logged_by, kind, channel, direction, body) ->
    VendorCommunication` — records an off-system comm
    (phone / in-person / inbound). Creates directly at
    `status='logged'`.
- `services/llm_safety.py` extended with
  `_scrub_invented_recon_fact` firing on
  `kind="vendor_comm"`. Regex families per §5.g:
  - Invented finding IDs.
  - Invented part numbers.
  - Invented dollar amounts.
  - Invented dates.
- Two new `kind` values recognized by
  `apply_post_llm_scrubs`: `"vendor_comm"` and
  `"parts_order"`.

**Tests target.** ~55 focused tests split across:
- `services/vendor_comm` — draft happy path;
  `source_provenance` recording; state transitions;
  human-approval-required-before-send invariant;
  operator-logged rows skip approval; AI-drafted rows
  cannot jump to logged (SESSION_066 refinement locked at
  service layer).
- `services/llm_safety._scrub_invented_recon_fact` —
  invented finding IDs stripped; invented part numbers
  stripped; invented $ amounts stripped; invented dates
  stripped; correctly-attributed content passes untouched.
- LLM path stubbed via mock provider — zero real API
  access.

**Boundary.** Backend baseline: 2,367 → ~2,422 pass. No
migrations. No frontend.

**Explicit non-goals for M4.5:**

- ❌ Do NOT wire outbound SMTP / SMS send — deferred per
  planning §5.i.
- ❌ Do NOT add M4.6+ scope.
- ❌ Do NOT modify M4.1/M4.2/M4.3/M4.4 substrate.

## Anchors that win on conflict for SESSION_070

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.6 +
   §1.6.SHIPPED (SESSION_067 enum reconciliation),
   §5.g (AI boundary + `_scrub_invented_recon_fact`
   regex families), §5.i (send deferred), §7 M4.5.
6. `docs/handoffs/SESSION_069_m4_inc4_parts.md` — this
   handoff.
7. `docs/handoffs/SESSION_068_m4_inc3_ledger.md`
8. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
9. `docs/handoffs/SESSION_066_m4_inc1_core_models.md`
10. `docs/handoffs/SESSION_065_m4_planning.md`
11. `backend/dealer_ai/services/llm_safety.py` — existing
    scrub stack; M4.5 extends additively per M2.5 pattern.
12. `docs/research/RECON_MAPPING.md` §5.6 + §14.7 + §14.8
    + §16.5 (vendor communication research).
