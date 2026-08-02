# Sales Manager — morning pipeline

**Archetype:** Retail / Subprime independent dealer
**Scenario slug:** `sales_manager_morning_pipeline`

## What happened before login

You run the sales floor. Fifteen active leads across urgency
buckets, four of them unassigned. Your three advisors — Avery,
Jamie, Morgan — each have a mix of walk-ins and chat leads
assigned. Five sales cleared in the last two weeks; two of those
went to sub-prime lenders and need credit-application follow-up.

Overnight, a couple of chat leads came in with pricing questions
on the truck inventory.

## What you need to accomplish today

Get the floor moving:

- **Assign the unassigned.** Four leads have `assigned_to=None`.
  Route them to whoever has capacity.
- **Follow-up cadence check.** One lead has a 1-week cadence
  running with three tasks due at 1/3/7 day offsets. Are any of
  those due today?
- **Walk-throughs.** The immediate-urgency leads want to see a
  truck this morning. Which ones matched to your F-150 / Tacoma
  / Silverado inventory?
- **Sub-prime credit apps.** Two apps are in the intake queue.
  Confirm the applicant info is complete and the retention
  clock hasn't started drifting.

## What's intentionally incomplete

- Some leads have `urgency='researching'` — legitimate but not
  today's problem.
- One lead is on a follow-up cadence with a task overdue by a
  couple of days. That's part of the scenario — how do you
  triage?
- The chat leads coming in overnight are structured but the
  advisor hasn't been picked yet. Choose or leave — either
  answer is defensible.

## Which shipped capabilities should help

- **Manager dashboard** — lead list, filter by advisor, filter
  by urgency, filter by channel.
- **Lead detail** — extracted profile, chat history if the lead
  came in via chat.
- **Follow-up surface (M11.4)** — cadence status, task list,
  overdue tasks.
- **Credit application queue (M10)** — intake list, missing
  fields, retention expiration.

## What successful completion looks like

By end of morning: every lead has an owner. The overdue follow-up
task is either completed, skipped, or explicitly acknowledged.
The two credit apps have been reviewed and any missing fields
recorded (via feedback if the workflow doesn't support in-line
edits).

## Discoverable without a guided click path

- `/dealer-ai-manager` opens the pipeline surface.
- Lead detail routes off of each lead card.
- Credit application queue is admin-level under the F&I surface.
- Follow-up cadences don't have their own operator-facing route
  yet (M11.4 shipped substrate only); the manager dashboard
  surfaces the count.
