# Sales Manager — BHPH originations

**Archetype:** BHPH independent dealer
**Scenario slug:** `bhph_sales_manager_originations`

## What happened before login

Ten active leads across the two collectors (Drew and Emerson).
Five BHPH sales cleared in the last two weeks — mixed weekly +
biweekly payment frequencies, APRs 22.9% – 24.9%, term lengths
52 / 78 / 104 weeks depending on the deal.

Each sale spawned a BhphNote with the payment amount computed by
the M12 payment engine.

## What you need to accomplish today

- **Check the recent originations.** Confirm each sale's finance
  type is `bhph`, the note principal matches the sold price,
  and the first payment due date is one week after sale.
- **Route the ten active leads.** Some may want vehicles that
  are on the lot; others may be more research-oriented.
- **Follow-ups on the pipeline leads.** A couple have follow-up
  cadences running.

## What's intentionally incomplete

- Not every sale has an associated CreditApplication row —
  BHPH deals often don't go through a formal credit-app
  workflow.
- Follow-up cadences don't fire actual email / SMS. The M11.4
  substrate surfaces the tasks; delivery is deferred.

## Which shipped capabilities should help

- **Manager dashboard** — pipeline, filter by advisor.
- **Sales list** — filter by finance type = BHPH.
- **BHPH note detail** — payment amount, term, first payment
  due date.

## What successful completion looks like

Every recent BHPH sale has a matching note with correct terms.
Every active lead has an owner. Follow-up tasks are current.

## Discoverable without a guided click path

- `/dealer-ai-manager` for pipeline.
- Sales list linked from manager dashboard.
- BHPH note detail linked from the sale detail.
