# Office / Accounting — the M16 detector timing story

**Archetype:** BHPH independent dealer
**Scenario slug:** `office_accounting_close`

## What happened before login

Your book has about thirty active BHPH notes. Payments trickle
in daily — some cash walked in yesterday, some ACH cleared this
morning, some check deposits from earlier this week already
posted.

**Here's the timing story you need to understand.** The M16
daily detector at 11:00 project-time posts newly-received BHPH
payments into the GL. Payments received before yesterday's
11:00 have already flowed through — you'll see them on the
current trial balance. Payments received between yesterday's
11:00 and today's 11:00 have `posted_at=NULL` and will land
after the next cycle.

This is the operational rhythm the M16 substrate exists to
support: payments queue up during the day; the detector posts
them overnight (well, at 11:00); the accounting surface tells
the correct story on any given morning.

## What you need to accomplish today

- **Pre-11:00 trial balance check.** Pull the current view.
  Note what BHPH Notes Receivable + BHPH Interest Income +
  Cash on Hand look like. There are roughly five recent
  payments that haven't posted yet, so those five aren't
  reflected here.
- **Post-11:00 check.** After the 11:00 detector cycle, pull
  again. The recent payments should now be reflected. The
  BHPH Notes Receivable balance should have decreased by the
  aggregate principal-applied. Interest Income should have
  increased.
- **Freeze a snapshot AFTER the detector runs.** If you freeze
  before 11:00, your snapshot will exclude the pending
  payments. This is intentional — different closes serve
  different purposes.

## What's intentionally incomplete

- Interest accrual for the 30-day past-due notes hasn't been
  posted (cash-basis, not accrual-basis).
- No aging bucket rollup in the accounting UI — you'll need
  to cross-reference the M12 portfolio surface for the aging
  breakdown.
- Late-fee charges aren't wired. `applied_to_fees` is always
  zero across every BhphPayment row.

## Which shipped capabilities should help

- **Trial balance (M14.2 / M17)** — as_of picker, freeze
  button, prior closes list. If prior closes exist, you can
  see the pre- vs post-detector comparison.
- **Journal entries browser (M14.3)** — each posted BHPH
  payment shows up as a distinct entry with "M12 BHPH payment
  intake" in the description.
- **BHPH portfolio (M12)** — active notes, per-note payment
  history including unposted rows.

## What successful completion looks like

You understand which payments have flowed to the GL and which
are waiting for the next detector cycle. You've either frozen
a snapshot or explicitly decided which side of the 11:00 line
you want to freeze from.

## Discoverable without a guided click path

- `/dealer-ai-accounting/trial-balance` — the main surface.
- Journal-entry list linked from trial balance.
- BHPH portfolio surfaces off the manager dashboard.
