# Accounting Immutability + Reversal

Journal entries are never mutated. Corrections happen through
reversal entries. There is no "who edited what" history because
nothing gets edited.

## Context

A dealership's general ledger has to be trustworthy. Trial balance
snapshots reference journal-entry lines; regulators, tax
preparers, and auditors read entries months or years after posting.
An accounting system that lets any manager edit any past entry is
a system nobody can trust.

Dealer AI implements a double-entry substrate — chart of accounts,
journal entries with debit/credit lines, trial balance snapshots
— and had to make one durable decision early: are entries
mutable, or immutable?

## Correction

Journal entries are immutable once posted. The write path in
`backend/dealer_ai/services/accounting/journal.py` never updates a
posted entry. Corrections are made by creating a **reversal
entry** — a new journal entry whose lines are the sign-flipped
debits and credits of the original. The original entry and the
reversal both survive; the net effect on the trial balance is
zero.

Idempotency is enforced by immutability plus sentinels:
`VehicleCost.posted_at` and `BhphPayment.posted_at` mark the
moment a source event was posted to the ledger. The scheduled
posting tasks
(`services/accounting/tasks.post_vehicle_cost_journals_for_all_tenants`,
`services/accounting/tasks.post_bhph_payment_journals_for_all_tenants`)
skip any source event whose `posted_at` is set. Rerunning a
posting task cannot duplicate entries.

The concrete substrate:

- `GLAccount` — chart of accounts; code (e.g. `100000`, `122000`,
  `200000`), name, account type. Seeded via
  `seed_default_coa`. Immutable-by-convention.
- `JournalEntry` — a posted entry; dealership, date, description.
  No update path in the service layer.
- `JournalEntryLine` — debit/credit pairs against GL accounts,
  amounts. Written together with the parent entry in one
  transaction; not updated afterwards.
- `TrialBalanceSnapshot` + `TrialBalanceSnapshotRow` — frozen
  balance state as of a snapshot date. Rebuildable from the
  entry history because entries are immutable.

## Verification

The GL substrate is pinned by
`backend/dealer_ai/tests/test_admin_vehicle_ledger.py` — a
1,224-line ledger state matrix covering:

- Vehicle lifecycle state transitions (acquisition → active →
  sold).
- Cost posting + reversal journal entries.
- Ledger balance reconciliation with trial balance snapshots.
- Multi-stage cost accumulation (recon costs, floor-plan interest
  accrual).

Additional pindowns:

- `test_m131_accounting_substrate.py` — journal entry + trial
  balance model invariants.
- `test_m171_trial_balance_materialization.py` — 699 lines of GL
  view tests.
- `test_m132_vehicle_cost_posting.py` — idempotency:
  double-invocation of the posting task produces exactly one entry.
- `test_m161_bhph_payment_posted_at.py` — same idempotency
  pattern for BHPH payment posting.

The Playwright accounting journeys
(`acceptance/journeys/office/accounting_je_reversal.spec.ts` and
`accounting_workflow.spec.ts`) exercise the reversal UI end-to-end
through the real browser against the seeded DB.

## Lasting Effect

Trust in the GL substrate is a precondition for the rest of the
dealership's finance operation. The immutability rule means:

- **Rebuilding a trial balance from the entry history is safe**
  at any point in time, because entries never move.
- **The reversal is itself an event.** A future auditor sees
  both the original and the correction, with timestamps and
  actor attribution. There is no "silent" fix.
- **Concurrent posting jobs cannot double-post.** The
  `posted_at` sentinel is the coordinator, not any lock or queue
  discipline.

This is one of several places in the codebase where the pattern is
"idempotency by immutability" rather than "idempotency by lock" —
the simpler and more auditable of the two. It is a small
codebase's version of the same discipline that underlies
production-scale ledger systems.
