# Recon Lead — the overrun intervention

**Archetype:** Floor-planned / Recon-heavy independent dealer
**Scenario slug:** `recon_lead_overrun_intervention`

## What happened before login

Five vehicles in recon. Four are progressing normally with
mechanical + tire work through Sunset Mechanical. **One — the
2020 Ford F-150 XLT SuperCrew, stock FP-01 — is a problem.**

Here's the timeline:

- Two weeks ago: inspection flagged transmission slippage under
  load. Estimated fix: $450 (torque converter suspect).
- Also two weeks ago: cosmetic finding on the rear bumper +
  driver door. Estimate: $175.
- Work order authorized at $600.
- Yesterday: vendor called with revised estimate. Teardown
  found torque converter internals damaged, wanted to do a
  full rebuild + cooler upgrade. Revised: $1,425.
- Verbal approval given on the phone. Written follow-up
  narrative logged in the vendor communications history.

**The $825 overrun is real** — it's on the WorkOrder as
`actual_cost=$1,425` vs `authorized_cost=$600`, and it's on
the vehicle's investment ledger as three VehicleCost rows
summing to $1,425 (parts + labor + body work). The M2
investment ledger reads correctly against the M4 work-order
detail.

## What you need to accomplish today

- **Decide whether to re-authorize in writing.** The verbal
  approval kept the work moving; the written record should
  reconcile.
- **Reconcile the ledger.** The VehicleCost total against the
  F-150 should equal the WorkOrder actual_cost. If they
  don't, something's wrong.
- **Talk to the owner.** The overrun exceeds your standing
  approval threshold. Make sure the owner has the vendor
  communications history on record.
- **Get the F-150 through recon.** Is the work actually done
  or is there more coming?

## What's intentionally incomplete

- No `completed_at` on the work order yet — the work is
  in-progress; the vendor promised finish this afternoon.
- No photos of the completed cosmetic work. Photo capture
  isn't part of this brief.
- The other four recon vehicles have `actual_cost=NULL` —
  they're mid-work and haven't been invoiced yet.

## Which shipped capabilities should help

- **Recon queue** — every open work order.
- **Work order detail** — authorized_cost vs actual_cost, the
  parts list, the vendor.
- **Vendor communications (M4.5)** — read the outbound email
  ($600 approval) + the inbound narrative log ($1,425
  revision).
- **Vehicle investment ledger (M2)** — F-150 total spend
  against the acquisition cost basis.
- **Trial balance (M14.2 / M17)** — Recon WIP balance
  reflects the overrun.

## What successful completion looks like

You can articulate the overrun in one sentence, with the ledger
+ work-order + vendor comms all pointing at the same $1,425
number. The other four recon vehicles are on track. The owner
has been briefed.

## Discoverable without a guided click path

- `/dealer-ai-recon` opens the queue.
- Click FP-01 to see the work-order + parts + vendor comms.
- The vehicle detail page has the investment ledger tab.
- Vendor communications live on the work-order detail page.
