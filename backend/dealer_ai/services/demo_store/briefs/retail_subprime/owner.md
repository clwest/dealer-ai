# Owner — daily snapshot

**Archetype:** Retail / Subprime independent dealer
**Scenario slug:** `owner_daily_snapshot`

## What happened before login

You own a small used-car lot. Twenty units on the ground, mixed
makes, priced $8k–$18k, targeting cash buyers and sub-prime finance
customers. Four staff — you (playing the sales manager role) plus
three advisors. Weekly closing rhythm; monthly bank reconciliation.

Overnight, three things landed:

- Five recent sales in the last two weeks cleared through the
  ledger — a mix of cash and retail-finance, and one BHPH deal on
  a well-loved Fusion. Journal entries auto-posted via the M15
  sync-sibling path.
- Two sub-prime credit applications from the retail-finance side
  are in the intake queue.
- Three vehicles remain in recon on the back lot; the recon
  spend for each is documented in the vehicle-investment ledger.

## What you need to accomplish today

Get a read on where the store stands:

- **Sales this week.** What closed. Which advisor booked what.
  What margin held vs slipped.
- **Recon exposure.** Are the three in-recon vehicles trending
  toward completion, or are we bleeding into next week?
- **Trial balance.** Cash-on-hand, receivables, BHPH note
  balance. Is the ledger telling the story you expect?
- **Pipeline pressure.** Fifteen active leads, four assigned
  advisors — is anyone overloaded?

## What's intentionally incomplete

- Some leads sit unassigned. That's real: not every walk-in gets
  a name attached in the first ten minutes.
- Some recon work orders are still `in_progress` with no
  `completed_at`.
- The BHPH sale from the past two weeks has a fresh note but no
  payments yet — the first payment isn't due for another week.

## Which shipped capabilities should help

- **Sales pipeline** — filter by advisor, by week, by finance
  type.
- **Vehicle investment ledger (M2)** — total investment per
  vehicle, projected gross once sold.
- **Trial balance (M14.2 / M17)** — the current view + prior
  closes if any exist. As of today none have been frozen; you
  can freeze one right now if you want a durable close-of-week
  record.
- **Recon queue (M4)** — every vehicle with an open work order,
  their vendor + status + parts.
- **Manager dashboard** — leads, chat sessions, ad copy
  performance.

## What successful completion looks like

You have a defensible answer to "how did we do this week?" —
grounded in what the trial balance says, what the sales pipeline
shows, and what the recon queue is trending toward. You've either
frozen this week's trial balance snapshot for the record, or
you've decided you want to wait until Friday. You know which
advisor to lean on next week.

## Discoverable without a guided click path

The routes you'd use are the ones a real operator would use:

- `/dealer-ai-manager` for the sales pipeline surface.
- `/dealer-ai-accounting/trial-balance` for the ledger.
- `/dealer-ai-recon` or the recon detail routes for the queue.
- `/dealer-ai-manager/vehicles` for inventory-level ledger reads.

Nothing here requires a hand-crafted URL or a special view.
