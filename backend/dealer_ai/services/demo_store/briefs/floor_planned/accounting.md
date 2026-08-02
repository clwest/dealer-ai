# Office / Accounting — floor plan curtailment review

**Archetype:** Floor-planned / Recon-heavy independent dealer
**Scenario slug:** `floor_plan_curtailment_review`

## What happened before login

Ten sales cleared in the last two-plus weeks — mostly retail-
finance with a couple of cash deals. Every retail-finance
receivable sits in 120000 Contracts in Transit; cash proceeds
sit in 100000 Cash on Hand. Cost bases posted before each
sale; the M15 sync-sibling GL post fired for each.

Recon activity: five in-progress vehicles, four already-posted
VehicleCost row sets, one (the F-150 overrun) posted at
$1,425 across parts + labor + body work.

## What you need to accomplish today

- **Trial balance check.** Total debits and credits should tie
  out. Contracts in Transit should reflect roughly eight
  retail-finance receivables ($150k range depending on the
  mix). Cash on Hand should reflect the two cash sales plus
  any operator-recorded cash payments.
- **F-150 overrun visibility.** The 122000 Recon Work in
  Process account should show the F-150's $1,425 spend until
  the vehicle sells and the sale-booking journal clears it.
  Confirm the overrun is on the ledger, not just on the WO
  detail page.
- **COGS check.** Every sold vehicle's cost basis flowed into
  500000 Cost of Vehicle Sales. Sum the debits by hand
  against the ten sales' cost_basis values.

## What's intentionally incomplete

- Floor-plan interest for the current period hasn't been
  accrued yet. The M7 async job runs on its own schedule.
- No period-over-period comparison view. The M17 freeze verb
  captures snapshots but the comparison surface itself is a
  deferred milestone.
- The BackEndProductAgreement + Chargeback substrate isn't
  seeded — the F&I audit scenario belongs to a later brief.

## Which shipped capabilities should help

- **Trial balance (M14.2 / M17)** — live view + as_of picker +
  freeze button.
- **Journal entries browser (M14.3)** — one M15 "M9 sale
  booking" entry per sale.
- **Vehicle investment ledger (M2)** — F-150 total investment
  tells the same overrun story from the vehicle side.

## What successful completion looks like

The trial balance ties out. The F-150 overrun is visible on
both the ledger AND the work-order detail. You've either
frozen a snapshot or decided to wait.

## Discoverable without a guided click path

- `/dealer-ai-accounting/trial-balance`.
- Journal-entry list linked from trial balance.
- Vehicle detail (with investment ledger) linked from the
  vehicle list.
