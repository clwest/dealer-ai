# Owner — portfolio health

**Archetype:** BHPH independent dealer
**Scenario slug:** `owner_portfolio_health`

## What happened before login

You run a small BHPH shop. Twenty-five units of reliable-
transportation inventory on the lot, priced $4k–$12k. Four staff:
you, one sales manager, two collectors. Active portfolio of about
thirty BhphNotes across aging buckets — some current, some 30-day
past-due, some 60-day past-due. One vehicle recently repossessed
and recovered.

Overnight, five payments came in — some cash walked in yesterday,
some ACH cleared this morning. The M16 daily detector at 11:00
project-time will post those into the GL on its next run.

## What you need to accomplish today

- **Portfolio at a glance.** How many notes are current vs 30
  past-due vs 60 past-due? What's the total outstanding
  principal balance across the book?
- **Recent origination.** Five sales cleared in the last two
  weeks, all BHPH. Confirm each sale spawned exactly one
  BhphNote with correct principal + APR + term.
- **Repossession status.** One note was ordered for repo three
  weeks ago and recovered twelve days ago. What's the next
  step — re-intake for resale, or write-off?
- **Collections activity.** Both collectors have been running
  their book. How many contacts logged this week? Any
  promises kept? Any broken?

## What's intentionally incomplete

- No interest-accrual posting per note (accrual-basis GL is
  deferred; you're on cash-basis).
- No aging-bucket dashboard component — you'll need to compute
  the buckets from the M12 note surface manually.
- The repossessed vehicle hasn't been re-intaked yet. There's
  no `intake_condition_report` on the Repossession row.

## Which shipped capabilities should help

- **BHPH portfolio surface (M12)** — active notes, aging,
  payment schedule, outstanding balance per note.
- **Trial balance (M14.2 / M17)** — BHPH Notes Receivable +
  BHPH Interest Income + Cash on Hand should reflect the
  portfolio activity. Note: recent payments won't post to
  the GL until after 11:00 today.
- **Repossession detail (M12.6)** — state machine + agent name
  + recovery details.
- **Collection contacts (M12.5)** — audit log per note.

## What successful completion looks like

You have a defensible answer to "how healthy is the book right
now?" You know how many notes are past-due, how much cash came
in this week, and whether the recovered vehicle is on a path
back into inventory. You've decided whether to freeze a trial-
balance snapshot for the record.

## Discoverable without a guided click path

- `/dealer-ai-manager` for the sales-side surface (recent
  sales, active leads).
- `/dealer-ai-accounting/trial-balance` for the ledger.
- BHPH portfolio surfaces off the manager dashboard.
- Repossession detail is linked from the note detail.
