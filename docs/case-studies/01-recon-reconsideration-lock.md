# Recon Reconsideration Lock

Dealership managers change their minds about what needs fixing.
Until work is authorized, those decisions stay fluid. Once a work
order leaves draft, the specification is locked — changing it after
labor authorization creates audit-trail damage.

## Context

Every used vehicle that comes onto the lot generates condition
findings (inspection observations tied to the vehicle). A recon
manager records a **decision** on each finding — must_do,
should_do, or won't_do. That decision drives quoting: vendors bid
against the finding tier. The tier is not a permanent verdict;
managers legitimately reconsider the must_do / should_do line as
vendor estimates come back or budget tightens.

But once a work order (WO) has been approved, started, or completed
— meaning labor has been authorized and possibly begun — the
underlying decision must freeze. If you can retroactively change
"must_do" to "won't_do" after a mechanic has already begun the
repair, the audit trail becomes unreliable and the compliance story
falls apart. The operational rule, learned from actual recon
meetings, is: **you can change your mind about what to fix until
you send the quote; after that, the record is frozen.**

## Diagnosis

The rule was codified in SESSION_067 as part of the recon service
layer. It is enforced at the service call site, not by a database
constraint, so it can be reasoned about and tested cleanly in one
place: `backend/dealer_ai/services/recon.py`.

The set of "locking" WO statuses is a module-level constant:

```python
_DECISION_LOCKING_WORK_ORDER_STATUSES = {
    "approved", "in_progress", "completed", "cancelled",
}
```

When `record_decision(finding, ...)` is called, it looks for any
work order linked to that finding that has left the `draft` state.
If one exists, the call raises `ReconImmutableError` before touching
the decision.

## Correction

The reconsideration path is deliberately generous while quoting is
open. The service function upserts the decision (`update_or_create`)
so a manager can flip the tier as many times as they need before
authorizing labor. Once the WO is approved, the check flips: any
subsequent `record_decision` call for that finding is refused.

State transitions on the WO itself use `select_for_update()` on the
row so concurrent approvals cannot slip past the lock:

```python
def approve_work_order(work_order, *, dealership, approved_by, ...):
    work_order = _load_for_transition(work_order)   # SELECT ... FOR UPDATE
    if work_order.status not in ("draft", "approved"):
        raise InvalidReconTransitionError(...)
    work_order.status = "approved"
    work_order.approved_at = now()
    work_order.approved_by = approved_by
    work_order.save()
    return work_order
```

The transaction guarantees the "was the WO locked when we checked?"
question and the "the decision is now updated" write cannot be
interleaved by another caller.

## Verification

Three regression tests pin the invariant in
`backend/dealer_ai/tests/test_recon_service.py`:

- **Reconsideration allowed pre-approval** — flip must_do →
  should_do while WO is draft; no error.
- **Reconsideration still allowed on the same finding** — repeated
  mutation, still draft; still no error.
- **Lock engages after approval** — approve the WO, attempt to
  change the decision, expect `ReconImmutableError`.

A full-lifecycle test verifies that the lock does not interfere
with subsequent ledger posting (M4.3 → M13.2 integration).

## Lasting Effect

The pattern generalized. Any subsequent recon feature (vendor
communication, parts ordering, QC verification) can rely on the
invariant: once a WO leaves draft, its parent decision is readable
but not writable. Vendor-facing artifacts (RFQs, POs) reference the
locked decision text and never need to defensively re-check.

The lock is a case study in service-layer policy enforcement: the
rule is business logic, not a schema constraint. It lives where it
can be tested and audited, and its exception name
(`ReconImmutableError`) tells any caller *why* the write was
refused — which matters when a manager legitimately does not
understand why the tier button is greyed out.
