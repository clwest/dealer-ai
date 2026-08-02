# Sales Manager — pipeline review

**Archetype:** Floor-planned / Recon-heavy independent dealer
**Scenario slug:** `sales_manager_pipeline_review`

## What happened before login

Twenty-five active leads split across four advisors — Blake,
Cameron, Drew, Emerson. Several unassigned. Ten sales cleared
in the last two-plus weeks; three CreditApplications are in the
intake queue with sub-prime and prime lender routing.

Three be-back rows are open: one test-drive promise expired
unmet last week (no-show), one bring-co-signer promise already
returned, one bring-trade-in promise pending.

Overnight, the follow-up scheduler surfaced three FollowUpTask
rows due this morning.

## What you need to accomplish today

- **Distribute the unassigned.** Look at each advisor's current
  load and route the unassigned leads accordingly.
- **Follow up on be-backs.** The no-show promise from last week
  needs a call or text. The bring-trade-in promise is due
  today.
- **Credit-app review.** Three CreditApps waiting. Verify
  applicant name + source format + sale attachment.
- **Sales rhythm.** Ten sales in two weeks — is that ahead of
  or behind the store's usual pace?

## What's intentionally incomplete

- Some FollowUpTask rows are pending without an assigned
  advisor.
- The BeBack that already returned hasn't been converted to a
  fresh CustomerLead yet — the return happened, but the
  follow-through logic isn't wired in.
- No LenderProgram catalog entries are populated for the
  sub-prime routing — the sub-prime lender name lives as
  free text on the Sale row.

## Which shipped capabilities should help

- **Manager dashboard** — pipeline, filter by advisor.
- **BeBack surface** — promised/returned/no-show rows for
  every advisor.
- **Credit application queue** — intake list with retention
  clock.
- **Follow-up substrate (M11.4)** — task list, cadence status.

## What successful completion looks like

Every lead has an owner. Every open be-back has a plan.
CreditApps are either progressed or explicitly deferred with
a note. The no-show has been reached out to, or you've
recorded that they went radio silent.

## Discoverable without a guided click path

- `/dealer-ai-manager` for pipeline + BeBack surfaces.
- Credit application queue lives under the F&I admin surface.
