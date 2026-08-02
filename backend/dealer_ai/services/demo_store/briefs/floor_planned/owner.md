# Owner — capacity check

**Archetype:** Floor-planned / Recon-heavy independent dealer
**Scenario slug:** `owner_capacity_check`

## What happened before login

You run a mid-size independent Sun Belt used-car store. Forty
units on the lot right now, priced $12k–$35k, Ford / Chevy /
RAM / Toyota heavy. Auction floor-plan lender relationship. Six
staff: you, one sales manager, four advisors. Ten recent sales
closed in the last two-plus weeks — mostly retail finance, a
couple of cash.

Overnight the shop foreman texted you: one of the F-150s in
recon came in with a transmission problem worse than the
initial estimate. Vendor called for verbal approval on a
$1,425 rebuild; the WO was authorized at $600. You approved
verbally, the follow-up narrative is in the vendor comms log.
The rest of the recon queue is on track.

## What you need to accomplish today

- **Capacity check.** With 40 units and 10 recent sales, roughly
  how many days of inventory does that represent? What's your
  average days-on-lot trending toward?
- **Floor-plan exposure.** Every unit on the lot except the
  handful of trade-ins is auction-financed. What's the total
  floor-plan balance implied by the acquisition cost bases?
- **Sales-force capacity.** Your four advisors have 25 leads
  between them. Is that too much?
- **Recon overrun.** The F-150 overrun is $825 above authorized.
  The recon lead has it under control; is the ledger
  reflecting it?

## What's intentionally incomplete

- Floor-plan interest hasn't been accrued for the current
  period. That's a scheduled Celery job that will fire on
  its normal cadence.
- No CPO simulation on the newer inventory — mixed content on
  the lot; the shop treats them all as used.

## Which shipped capabilities should help

- **Manager dashboard** — sales this week, leads by advisor,
  chat sessions.
- **Vehicle investment ledger (M2)** — per-vehicle cost basis
  + projected gross. The F-150 with the overrun will show the
  higher total investment.
- **Recon queue** — the F-150 work order shows the
  authorized vs actual divergence.
- **Trial balance (M14.2 / M17)** — check cost-of-goods and
  receivables.
- **Vendor communications (M4.5)** — read the recon-overrun
  narrative log from Sunset Mechanical.

## What successful completion looks like

You have a defensible number for days-of-inventory, you've
verified the F-150 overrun is properly documented on both the
work order and the ledger, and you've decided whether to have
a conversation with the recon lead about approval thresholds.

## Discoverable without a guided click path

- `/dealer-ai-manager` for the sales side.
- `/dealer-ai-recon` for the queue + the F-150 detail.
- `/dealer-ai-accounting/trial-balance` for the ledger view.
