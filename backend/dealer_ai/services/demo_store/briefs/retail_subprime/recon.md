# Recon Lead — vehicle-by-vehicle status

**Archetype:** Retail / Subprime independent dealer
**Scenario slug:** `advisor_walk_in_workup` (yes, recon-role on
the retail archetype often overlaps with the advisor role at a
small shop — you're doing both.)

## What happened before login

Three vehicles are in recon. Each has:

- An acquisition record with the auction / trade / private-party
  source and cost basis.
- A completed condition report with two findings (brakes + tires,
  typically).
- Must-do decisions on each finding.
- A single outsourced work order to your mechanical vendor
  ("Desert Auto Repair").
- Parts installed, labor and tires posted as VehicleCost rows,
  detail bay finish scheduled.

## What you need to accomplish today

- **Trigger the frontline flip.** For any vehicle whose work is
  done, transition it from `recon` → `frontline` so the sales
  side can list it.
- **Verify recon spend is captured.** The M2 investment ledger
  should show the parts + labor + tires + detail totals against
  each vehicle's cost basis. Cross-check against the vendor
  invoice references on the VehicleCost rows.
- **Confirm no work order stays stale.** All three WOs should
  either be complete or have an active-day-count trending
  reasonably.

## What's intentionally incomplete

- No `actual_cost` populated on the work orders — you'll fill
  those in as vendor invoices land.
- No photos taken yet. Photo capture per M6 is not part of the
  today's scenario.
- Vendor communications live in the M4.5 substrate but there
  aren't any drafted for these three vehicles — they went
  straight to the shop without a comms log.

## Which shipped capabilities should help

- **Recon queue** — every open work order, vendor, category.
- **Vehicle detail — investment ledger tab** — total
  investment, cost breakdown, projected gross.
- **Condition report + findings surface** — see what the
  inspector flagged.
- **Lifecycle stages (M5)** — the frontline flip transition.

## What successful completion looks like

Each recon vehicle either progressed toward frontline or has a
clear reason it hasn't. The investment ledger tells the same
story as the physical shop status.

## Discoverable without a guided click path

- `/dealer-ai-recon` for the queue.
- Vehicle detail routes off the recon list.
- Investment ledger tab is a section on the vehicle detail
  page.
