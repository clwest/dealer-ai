# Collector — daily book

**Archetype:** BHPH independent dealer
**Scenario slug:** `bhph_collector_daily_book`

## What happened before login

You're one of two collectors on the book. Between you and the
other collector, you own about thirty active notes across aging
buckets. Weekly and biweekly payment frequencies. Some notes
are current; others are 30 or 60 days past-due.

Overnight three things landed:

- A payment came in from a customer on your book — cash,
  logged yesterday afternoon. Not yet posted to the GL (the
  M16 detector runs at 11:00).
- One of your promise-to-pay records is due today. The
  customer promised $150 via paycheck; the promise is still
  in `promised` state.
- Another PTP from last week already turned into a real
  payment — a $200 tax-refund promise came through on time;
  the record is now in `kept` state, linked to the payment.
- And one PTP from three weeks ago was never fulfilled — the
  customer's $120 family-help promise broke.

Five collection contacts have been logged over the last two
weeks — a mix of phone calls (contact_made, left_message),
one SMS with no_answer, and a letter.

## What you need to accomplish today

- **Work the promised-today PTP.** Call, text, or otherwise
  reach the customer to confirm the promise or acknowledge
  the miss.
- **Log every contact.** Whatever channel you use, capture
  the outcome as a CollectionContact row.
- **Convert kept promises.** The already-kept promise is
  done; no action needed but confirm the linkage.
- **Follow up on broken promises.** The broken PTP from
  three weeks ago is escalating — decide whether to file a
  new PTP, escalate to letter, or move toward repossession
  order.

## What's intentionally incomplete

- The M12.5 CollectionContact log is the audit surface;
  there's no dialer, no auto-SMS. Every contact is manually
  logged.
- No FDCPA compliance guardrails beyond what the model
  enforces — you're expected to know the collection
  regulations for your state.
- Follow-up cadences (M11.4) are for sales-side leads, not
  active BHPH customers. Collection contacts stand alone.

## Which shipped capabilities should help

- **BHPH portfolio (M12)** — every note, filter by aging
  bucket, click into note detail.
- **Note detail** — payment history, PTP history, contact
  log.
- **Promise-to-pay surface (M12.4)** — every open PTP, state
  filter.
- **Collection contacts (M12.5)** — record a new contact
  attempt.
- **Repossession order (M12.6)** — if the broken PTP
  escalates.

## What successful completion looks like

Every open PTP is either worked or explicitly deferred. Every
contact attempt is logged. The broken PTP from three weeks ago
has a next step (fresh PTP, letter, repo order, or write-off
recommendation).

## Discoverable without a guided click path

- BHPH portfolio surfaces off the manager dashboard.
- Note detail links to PTP + contact log.
- Repossession order is a button on the note detail if the
  situation escalates.
