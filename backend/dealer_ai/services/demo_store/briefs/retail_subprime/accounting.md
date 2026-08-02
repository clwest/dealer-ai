# Office / Accounting — week close

**Archetype:** Retail / Subprime independent dealer
**Scenario slug:** `office_accounting_close`

## What happened before login

Five sales cleared in the last two weeks:

- Two cash sales (M15 sync-sibling GL post fired immediately —
  DR 100000 Cash / CR 400000 Vehicle Sales — Retail, and
  matching COGS / Recon WIP clear pair).
- Two retail-finance sales (DR 120000 Contracts in Transit
  instead of Cash — otherwise identical shape).
- One BHPH sale (DR 123000 BHPH Notes Receivable — the note is
  fresh; first payment isn't due for another week).

For each sale, the auction cost basis was posted as a VehicleCost
row before the sale-booking journal, so Recon WIP clears cleanly
to zero for each vehicle sold. The trial balance should reflect
all five sales, cost bases, and the resulting receivables.

Three vehicles remain in recon with in-progress work orders and
VehicleCost rows already posted (parts + labor + tires + detail).

## What you need to accomplish today

- **Trial balance check.** Pull the current view and confirm the
  BHPH Notes Receivable line reflects exactly one active note
  balance ($8,495). Confirm Contracts in Transit reflects the
  two retail-finance receivables. Confirm no phantom Recon WIP
  is stuck on a sold vehicle.
- **Journal-entry audit.** Scroll M14.3 and confirm each sale
  produced a matching M15 "M9 sale booking" entry with the
  expected description format (stock number + finance type).
- **Consider freezing a snapshot.** If you're comfortable that
  the week reconciled, use the M17 freeze-trial-balance verb to
  create a durable close-of-week snapshot. The prior-closes
  list will start populating the moment you do.

## What's intentionally incomplete

- No cost-of-sale variance adjustments have been posted — if a
  sold vehicle's actual sale price diverged from projected
  gross, that variance sits in the ledger as-is.
- No bank reconciliation. The 100000 Cash on Hand balance is
  aggregate cash + undeposited funds. The deposit-workflow
  milestone is deferred.

## Which shipped capabilities should help

- **Trial balance (M14.2 / M17)** — live view + as_of picker +
  freeze button + prior closes list.
- **Journal entries browser (M14.3)** — every entry, filter
  by nothing (M14 shipped filterless) but reverse chronological
  order.
- **Vehicle investment ledger (M2)** — per-vehicle projected
  vs actual gross.
- **BHPH portfolio (M12)** — active notes, upcoming payment
  schedule.

## What successful completion looks like

The trial balance ties out. Either a new snapshot is frozen, or
you have a clear reason why not. Any surprises get captured
via the M18.5 feedback form so Chris knows what to prioritize
next.

## Discoverable without a guided click path

- `/dealer-ai-accounting/trial-balance` — the trial balance
  surface with picker + freeze + prior closes.
- Journal-entry list is linked from the trial-balance page.
- BHPH portfolio surfaces off the manager dashboard.
