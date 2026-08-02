# Recon — BHPH inventory turnover

**Archetype:** BHPH independent dealer
**Scenario slug:** `bhph_recon_turnover`

## What happened before login

BHPH recon looks different from a retail store: the goal is fast
turnaround on inexpensive inventory. No vehicles are currently
in recon in this seeded scenario — the inventory is either
already frontline-ready or was quick-turn processed at
acquisition without a formal work-order chain.

There is, however, a repossession that came back in twelve days
ago (60+ day past-due note, ordered three weeks back, recovered
by the agency).

## What you need to accomplish today

- **Post-repo intake.** The recovered vehicle needs an intake
  condition report so the shop knows what it's dealing with.
- **Decide the disposition.** Re-intake for resale, wholesale
  it, or send it to auction? Whichever the choice, log it.

## What's intentionally incomplete

- The repossession's `intake_condition_report` FK is null —
  that's the workflow gap the M12.6 → M3 handoff is meant to
  cross, and it hasn't been crossed for this vehicle yet.
- No photos of the recovered condition. Photo capture is not
  part of this brief.

## Which shipped capabilities should help

- **Repossession detail (M12.6)** — the recovery date, agent
  name, recovery location.
- **Condition report create surface (M3)** — the intake CR
  would attach here.
- **Vehicle lifecycle stages (M5)** — the post-repo vehicle
  would flip from wherever it was to `incoming` or `recon`.

## What successful completion looks like

The recovered vehicle either has an intake CR written or has a
recorded reason it hasn't been assessed yet.

## Discoverable without a guided click path

- Repossession detail is linked from the associated BhphNote.
- Condition report create is on the vehicle detail page.
