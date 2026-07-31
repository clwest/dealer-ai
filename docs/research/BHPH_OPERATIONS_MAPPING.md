---
title: "Buy Here Pay Here (BHPH) Operations — Operational Mapping"
status: reference
type: research
generated: 2026-07-31
scope: Independent used-car dealership Buy Here Pay Here portfolio operations — from account setup through payoff, including collections, portfolio management, and vehicle recovery
voice: Experienced BHPH owner / collections manager / office manager / dealership operator
companion_docs:
  - "FINANCE_DEPARTMENT_MAPPING.md"
  - "ACCOUNTING_DEPARTMENT_MAPPING.md"
  - "SALES_DEPARTMENT_MAPPING.md"
  - "INVENTORY_ACQUISITION_MAPPING.md"
  - "RECON_MAPPING.md"
  - "VEHICLE_CENTRIC_PIVOT.md"
  - "INDEPENDENT_DEALER_PIVOT.md"
authoritative_for:
  - How an independent Buy Here Pay Here dealership actually operates after the sale
  - The customer lifecycle, payment operations, collections, and recovery discipline unique to BHPH
not_authoritative_for:
  - Indirect subprime finance operations (covered in `FINANCE_DEPARTMENT_MAPPING.md`)
  - Legal advice on collections, repossession, or consumer lending
  - Specific software product recommendations
  - Any implementation design
---

# Buy Here Pay Here (BHPH) Operations — Operational Mapping

> **What this is.** A research artifact documenting how a Buy
> Here Pay Here dealership actually operates after the customer
> takes delivery. Written from the perspective of an experienced
> BHPH owner or portfolio manager — the person who signs the
> repossession orders on Monday and hands over keys to the same
> customer's cousin on Thursday.
>
> **Who this is for.** Anyone (engineer, agent, product person)
> touching customer-account, payment-operations, collections,
> portfolio, or vehicle-recovery work in the Dealer AI Kit. Read
> this before opening a code editor or a wireframe tool.
>
> **What this is NOT.** Not a collections training program. Not
> legal advice on repossession law (which varies dramatically
> by state). Not a comparison of specific BHPH software. Not an
> implementation plan.
>
> **Why this document is different from the F&I mapping.** For
> indirect financing, the dealership hands the customer to a
> lender at delivery. The dealership's role ends at funding.
> **In BHPH, the dealership IS the lender.** The relationship
> continues for 2–4 years — through 100+ payments, through job
> changes, through vehicle problems, through life crises,
> through repeat purchases. This creates an entirely different
> operational model that overlaps with F&I only at the
> beginning.
>
> **Core philosophy.** **"You make your money over time, not at
> the sale."** BHPH profit shows up over 24–42 months of
> collected payments plus (if the customer succeeds) a repeat
> sale down the line. A BHPH deal booked today doesn't tell you
> if it made money — the customer has to actually pay for that
> answer to come back. This shifts every operational instinct.
> Sales at BHPH is really the *first month* of a long
> relationship, not the culmination of a shopping process. The
> office manager and collections team spend more customer-hours
> per deal than the salesperson did. **Success is measured by
> the customer graduating** — paying off, coming back, sending
> family. Failure is measured by the repo, the charge-off, and
> the reputation damage in the community. The best BHPH
> operators are half lender, half social worker, half community
> figure — helping customers succeed while running a business
> that has to stay solvent.

---

## Purpose & scope

For many independent dealerships, BHPH isn't a sideline — it's
the whole business. BHPH stores buy inventory differently
(§Inventory), price differently, sell differently (§Sales),
finance differently (§F&I overlaps briefly at deal writing),
account differently (§Accounting §3.16), and — the subject of
this document — operate the customer relationship for years
after delivery in a way no other retail channel does.

The Dealer AI Kit's vehicle-centric pivot (see
`VEHICLE_CENTRIC_PIVOT.md`) proposes making every stock number
a living operational record. In BHPH, that record continues
long after the sale — through payment history, delinquency,
modification, and (sometimes) repossession-and-back-into-inventory.
This document preserves the operational knowledge that must
inform any BHPH-touching implementation.

**Scope boundary:** *independent BHPH dealer* scope.

- Small to mid-sized BHPH portfolio (50–1,500 active accounts;
  larger operations exist and share most of these operational
  patterns).
- Deep subprime and no-score customers as the primary
  segment; occasional near-prime customers by choice.
- Vehicles typically $4,000–$18,000 sale price; sometimes
  higher for near-prime deals.
- Payment cadence typically weekly, biweekly, or
  semi-monthly (matched to customer paydays).
- Terms typically 24–42 months.
- Cash-heavy payment intake at office; debit card, ACH, and
  online growing.
- 1–5 people directly operating the portfolio (owner,
  office manager, collectors; larger portfolios add dedicated
  collections team).
- BHPH may coexist with indirect finance at the same store,
  or the store may be pure BHPH.

Where mixed-model stores differ from pure-BHPH operators,
this document notes the contrast. Where BHPH varies materially
by state (repo law, licensing, starter-interrupt rules),
state-specific footnotes are avoided in favor of the
underlying operational dynamic.

---

## Voice & caveats

The voice throughout is that of an experienced BHPH operator.
Terminology is used as it's spoken: "the paper," "the
portfolio," "the book," "static pool," "charge-off," "PTP"
(promise to pay), "roll it" (modify a delinquent account),
"skip" (customer who disappeared), "hit the account" (post a
payment), "run the deal" (start the customer relationship),
"cash out" (payoff), "come back around" (repeat buyer),
"deep sub" (deep subprime), "reho" (repo followed by
recondition-and-resale).

**Numeric caveats.** Any specific figures — interest rates,
delinquency thresholds, static pool losses, repo cost ranges
— are illustrative of common experience. Real numbers vary
enormously by market, state, customer selection discipline,
and vintage of loans. Treat this document as a description of
the *shape* of BHPH operations, not as a source of truth for
specific benchmarks. Serious BHPH benchmarks come from NIADA,
NABD (National Alliance of Buy Here Pay Here Dealers), and
Subprime Analytics.

**Legal / compliance caveats.** BHPH is regulated at multiple
layers (federal Truth in Lending, state consumer-lending
codes, state repo law, FCRA, GLBA, FDCPA in some contexts,
state licensing, state starter-interrupt-device rules).
Nothing in this document is legal advice. Every BHPH operator
must build their compliance program with an attorney or
industry-specialist compliance advisor.

**Customer-relationship caveats.** BHPH customers are often
in genuinely difficult financial circumstances. This document
describes operational reality including collection and repo
work, but the operational reality of the best BHPH operators
is that customers are treated with dignity throughout. The
"we help people who need help" ethic isn't marketing — it's
what distinguishes stores that survive multi-generationally
from stores that don't.

---

## 1. The BHPH Business Model

### 1.1 What BHPH actually is

**Buy Here Pay Here** means the dealership serves as both
seller and lender. The customer buys the vehicle from the
dealership and pays the dealership directly for the loan —
not a bank, not a captive finance company, not a
subprime aggregator.

Concrete implications:

- **The dealership is the lender of record** on the loan.
- **The dealership collects payments directly** — cash,
  check, debit card, ACH, or online.
- **The dealership holds the title as lienholder** until the
  loan is paid off.
- **The dealership carries the risk** — if the customer
  doesn't pay, the dealership loses (either recovers the
  vehicle at reduced value, or takes a total loss on the
  account).
- **The dealership earns interest income** over the life of
  the loan.
- **The dealership manages the entire customer relationship**
  for the term of the loan (typically 24–42 months).

### 1.2 How BHPH differs from indirect financing

At an indirect-financed sale:

- Store hands customer to lender at delivery.
- Store's role ends when funding is received (typically 24–72
  hours).
- Store's revenue is: retail markup + reserve + product
  commissions. Lump sum.
- Store's exposure is: chargeback risk for 90 days or so.
- After funding, the store never sees the customer again
  unless the customer chooses to shop there again years
  later.

At a BHPH sale:

- Store retains customer relationship for 24–42 months.
- Store's revenue is: retail markup + interest income over
  the loan life. Streamed.
- Store's exposure is: full principal risk if customer
  defaults, plus repossession costs, plus reputation risk.
- After delivery, the store sees the customer weekly,
  biweekly, or monthly for the life of the loan.

**The two models are not just different in terms — they're
different businesses layered over the same physical
dealership.** A store doing 50% indirect and 50% BHPH is
really operating two companies out of one building.

### 1.3 The profit sources

BHPH profit comes from three sources:

**1. Retail markup on the vehicle.** Just like any used-car
sale. Vehicle acquired for $5,000, reconditioned for $1,000
(total $6,000 invested), sold for $9,500 retail. Gross of
$3,500 at sale time — but that gross isn't fully recognized
under installment-sale accounting (see §Accounting §3.16). It
gets recognized as the customer pays.

**2. Interest income over the loan life.** State usury caps
typically 21%–29.99% APR for subprime auto. At 24% APR on a
$9,000 balance over 36 months, cumulative interest is
substantial — often $3,500+ per contract if paid to term.
Portfolio-wide interest income can be the largest single
revenue stream at a mature BHPH.

**3. Repeat purchase revenue.** BHPH customers who succeed
often come back. A customer who paid off in 30 months and has
established payment history is a warm prospect for the next
vehicle. Repeat buyers close faster, cost less to acquire,
and often trade up. In mature BHPH portfolios, 30%–50% of new
sales can be repeat customers.

### 1.4 The loss sources

Correspondingly, three loss patterns:

**1. Charge-offs on uncollectible accounts.** Customer stops
paying, vehicle can't be recovered or recovery yields
insufficient proceeds, account written off. Charge-off losses
typically run 15%–30% of a BHPH portfolio on a static-pool
basis — meaning of every $100 loaned out, $15–$30 is
eventually lost.

**2. Repossession costs.** Recovery agent fees ($350–$800
typical), transport, storage, cleanup, resale-preparation
recon. Each repo costs the store real cash before any
recovery happens.

**3. Reputation and legal exposure.** Aggressive collections
practices, wrongful repossessions, or compliance missteps can
trigger complaints, lawsuits, or state regulatory attention.
Legal costs and settlements are real risks in the BHPH
segment.

### 1.5 Capital requirements

BHPH is capital-intensive because the store finances every
sale. Consider:

- Store sells vehicle for $9,500. Customer puts $1,500 down.
  Store has just extended $8,000 in credit.
- Sold on 36-month payment plan at $110/week.
- First-month cash inflow: $440–$550 from the customer.
- Store paid $6,000 for the vehicle plus $1,000 recon.
- Store received $1,500 down + first-month payments.
- Net cash position: still $5,000+ underwater on this
  vehicle at month 1.

Multiply across dozens or hundreds of active accounts. The
store's cash is deployed in the portfolio. New sales require
new cash (or borrowing against the portfolio).

**Capital sources:**

- **Owner equity.** Small BHPH often starts with owner cash.
  Slow-grow model.
- **Line of credit** secured against portfolio. Some banks
  do BHPH-portfolio lending; specialty lenders exist
  (e.g., Nicholas Financial-style factoring, though
  regulations vary).
- **Portfolio sale.** Larger BHPH sometimes sells older /
  seasoned portfolios to specialty buyers, freeing capital
  for new sales.
- **Bulk factoring** or receivables lending against the
  portfolio.

Capital constraint is the single biggest limit on BHPH growth
for small operators. A store might be able to sell 15 units
a month based on demand but only 8 based on capital
availability.

### 1.6 Portfolio as a balance-sheet asset

The BHPH portfolio — sum of all outstanding contract
receivables — is a real asset on the store's balance sheet.
A store with 300 active accounts averaging $6,000 outstanding
has a $1.8M portfolio. That's real capital, and it's real
value.

**Portfolio value considerations:**

- Face value (sum of remaining principal balances).
- Discounted value (reflecting expected losses and time
  value).
- Cash flow generation (monthly interest + principal
  collections).
- Marketability (can it be sold, if needed).

Sophisticated BHPH operators think of the portfolio as
strategically important — not just "the money customers owe
us" but a productive asset generating cash and enabling
long-term customer relationships.

### 1.7 Why an owner chooses BHPH

Common reasons operators go into BHPH:

- **Customer segment underserved by traditional lenders.**
  Owners who see subprime customers walking away disappointed
  and think "I can help those people."
- **Higher gross per unit.** BHPH deals typically produce
  higher total gross (over the loan life) than indirect
  subprime deals. Interest income compounds.
- **Repeat business.** Loyalty is real in BHPH; a happy paid-
  off customer often refers extended family.
- **Community role.** BHPH operators become recognized
  community figures ("I got my first car from him twenty
  years ago").
- **Control.** No lender rules, no chargebacks from someone
  else's underwriting decisions. The dealer sets the
  terms.

Common reasons operators avoid or exit BHPH:

- **Capital requirements** — can't tie up cash for years.
- **Collections work** — running collections is emotionally
  and administratively demanding.
- **Charge-off exposure** — losses are the dealer's; can
  destabilize a small operation.
- **Compliance risk** — state and federal exposure grows
  every year.
- **Reputation friction** — repo is unpleasant work with
  community consequences.

Not every operator is suited for BHPH. The best BHPH
operators are patient with capital, disciplined with
collections, empathetic with customers, and rigorous with
compliance.

---

## 2. Customer Lifecycle

The BHPH customer relationship spans the entire loan term. This
section walks that lifecycle chronologically.

### 2.1 Account setup at delivery

At vehicle delivery (see `SALES_DEPARTMENT_MAPPING.md` §3.10),
the customer signs the retail installment contract and
transitions from prospect to account holder.

Account setup elements:

- **Signed contract** — RISC (Retail Installment Sale
  Contract) with all Truth in Lending disclosures.
- **Payment schedule** — first payment date, cadence
  (weekly, biweekly, semi-monthly, monthly), payment amount,
  final payment date.
- **Payment method preference** — cash at office, ACH from
  bank account, debit card, online portal.
- **Contact information** — verified addresses (home, work),
  phone numbers (mobile, home, work), email, emergency
  contacts, references.
- **Insurance information** — full-coverage policy with the
  dealership as lienholder, deductible, insurance company,
  policy number, agent.
- **GPS / starter interrupt device** — if installed,
  activated and disclosed per state law.
- **Payment book** — some stores provide a physical payment
  coupon book; some provide a printed schedule; some are
  fully digital.
- **Welcome packet** — often includes payment schedule,
  contact info, "what to do if you have a problem" guidance.

### 2.2 The first payment

The first payment is a big deal in BHPH. It signals whether
the customer will actually pay or not. First payment default
(FPD) is the single strongest early signal of trouble.

Typical timing:

- Down payment collected at delivery.
- First scheduled payment 7–14 days after delivery (some
  stores collect the first regular payment at delivery
  along with the down).
- Second payment on schedule.

If the first payment isn't made:

- Contact within 24-48 hours ("just checking in, everything
  okay?").
- Escalation cadence begins immediately (§Collections).
- Repossession consideration much earlier than for a
  seasoned account.

### 2.3 Payment routine — the ongoing rhythm

Once payment cadence is established, the customer relationship
becomes a rhythm:

- **Weekly customer:** pays every Friday, or every Monday,
  or their specific payday.
- **Biweekly customer:** pays every other Friday.
- **Semi-monthly customer:** pays on the 1st and 15th (or
  15th and 30th).
- **Monthly customer:** pays on a specific day of the month.

Cadence is often matched to the customer's paycheck timing.
A customer paid every other Friday finds it easier to pay
BHPH every other Friday than to make a monthly payment.

The office / collections team knows the rhythms of hundreds
of customers. "Sara comes in every other Thursday around 5pm
with her cash payment. Marcus does ACH auto-draft. The
Rodriguezes always pay in person on Saturdays."

### 2.4 Ongoing communication

Beyond payment collection, the store maintains ongoing
communication:

- **Payment reminders** ahead of due dates (text, email,
  call).
- **Payment confirmations** after posting.
- **Late notices** when payments are missed.
- **Insurance renewal reminders** (customer must maintain
  full coverage; lapse triggers CPI or repo consideration).
- **Vehicle service reminders** (some stores offer post-sale
  service or partner discounts).
- **Anniversary touches** ("thanks for being a customer for
  6 months").
- **Life event outreach** — good BHPH operators know
  customers' major life events.
- **Repeat-buyer outreach** as the loan approaches payoff.

Communication cadence balances staying-in-touch with not
being intrusive. Over-communication feels like harassment;
under-communication misses issues.

### 2.5 Account modifications during the loan

Life happens. Common modifications during the loan:

- **Payment date change** — customer's payday shifted; adjust
  payment schedule.
- **Payment amount reduction** — customer's income dropped;
  reduce payment (extends term).
- **Payment deferral** — one payment deferred to end of loan
  (customer had a specific short-term hardship).
- **Term extension** — extending loan by weeks/months to
  reduce payment.
- **Payoff acceleration** — customer wants to pay off early
  (bonus, tax refund, life change).
- **Late fee waiver** — one-time waiver for a customer with
  otherwise-good history.

Modifications are discretionary and require judgment. Some
stores modify liberally to keep customers current; some are
strict about original terms. The choice affects both
collections effectiveness and portfolio performance.

### 2.6 Customer support and vehicle issues

The car breaks down. The customer calls. Now what?

- **In-house service option.** Some BHPH stores have a
  service shop and offer discounted or complimentary
  service for BHPH customers. Reduces repossessions caused
  by mechanical failures.
- **Preferred vendor referral.** Store recommends an
  affordable local shop.
- **No support.** Customer is on their own for repairs.

The stores that handle vehicle problems well have lower
repos. A customer whose transmission fails and gets brushed
off often stops paying — the vehicle isn't drivable, so why
pay for it? Wise operators try to keep customers running.

### 2.7 Payoff

Successful payoff is a graduation:

- Customer makes final payment.
- Store issues satisfaction / payoff letter.
- Store releases lien on title (paper title returned to
  customer or ELT updated).
- Payment book / coupon book closed.
- Account marked paid off in the DMS.
- Customer notified of the payoff and thanked.

Payoff should be celebrated. A paid-off BHPH customer is a
walking testimonial and a highly likely repeat buyer.

### 2.8 Payoff — variations

- **On-time payoff** — customer completes the full term.
- **Early payoff** — customer pays off in full before term
  end. Store collects less interest than projected but frees
  capital.
- **Refinance payoff** — customer refinances with a bank or
  credit union (their credit improved), pays off BHPH loan.
- **Trade-in payoff** — customer trades vehicle at the same
  store for a new loan. Payoff comes from the new deal.
- **Sold customer payoff** — customer sells the vehicle
  privately; buyer's financing pays the BHPH lien.

Each payoff type has slightly different accounting handling
(see `ACCOUNTING_DEPARTMENT_MAPPING.md` §3.16 for BHPH
accounting).

### 2.9 The repeat buyer cycle

Successful payoff often leads to repeat purchase. The cycle:

- Customer approaches payoff (final 6-12 payments).
- Store initiates repeat conversation ("what's your next
  vehicle need?").
- Customer often ready for something newer / bigger /
  different.
- New sale structured. Sometimes new sale is indirect-financed
  (customer's credit improved enough to qualify with an
  outside lender); sometimes new sale is BHPH again with
  better terms (larger vehicle, longer term, lower APR because
  the customer's history is proven).

Repeat buyers are the highest-margin, lowest-CAC segment of
BHPH. Some mature BHPH stores derive 30%–50%+ of their sales
from repeat + referral.

### 2.10 The unsuccessful outcomes

Not every customer succeeds. Failure modes:

- **Repossession** — vehicle recovered, loan defaulted.
  Customer relationship typically ends.
- **Charge-off without repossession** — vehicle can't be
  recovered (customer disappeared, vehicle destroyed, unable
  to locate), account written off.
- **Bankruptcy filing** — customer files bankruptcy; the loan
  is handled through bankruptcy court.
- **Voluntary surrender** — customer brings the vehicle back
  voluntarily, unable to continue payments.
- **Insurance total loss** — vehicle wrecked and totaled; GAP
  or shortfall handling.

Each failure mode has its own operational workflow and its
own community-reputation implications. The store's reputation
depends partly on *how* it handles failures, not just how
often they happen.

---

## 3. Payment Operations

Daily payment work is the heartbeat of BHPH. The office is a
constant flow of payments, reminders, and follow-up.

### 3.1 Payment methods

Common payment methods at BHPH:

- **Cash at office** — customer walks in, hands cash to the
  office, receives a receipt. Traditional and still common
  in the deep-subprime segment (many BHPH customers are
  cash-only).
- **Cashier's check / money order** — customer brings a
  cashier's check or money order (sometimes required for
  larger payments or when trust is limited).
- **Debit card** — customer swipes debit card in-person or
  provides card info by phone or online. Fees apply (small
  fraction of transaction).
- **ACH auto-draft** — customer authorizes automatic bank
  draft on payment day. Reduces missed payments; simplifies
  office workflow.
- **ACH one-time** — customer initiates single ACH from bank
  account.
- **Online payment portal** — customer logs in to a portal
  and makes payments (debit or ACH).
- **Payment kiosk** — some stores have a lobby kiosk for
  self-service payment.
- **Text-to-pay** — newer feature; customer receives payment
  link via text, pays via link.
- **Third-party payment processors** — some BHPH stores use
  services like PayNearMe, Western Union, or MoneyGram to
  allow customers to pay at retail locations (grocery
  stores, check-cashing centers).

Modern BHPH tends to support 4-6 methods concurrently to
match customer preferences.

### 3.2 The cash payment workflow

Cash payment is common and requires disciplined handling:

- Customer arrives at office.
- Office identifies the customer (customer name and stock
  number typical).
- Payment amount collected.
- Receipt generated (paper or digital).
- Receipt handed to customer.
- Cash secured (locked drawer, safe, deposit prep).
- Payment posted to the customer's account in the DMS.
- Payment reflected in the customer's next payment due date
  and balance.

Cash requires careful accounting (see §Accounting §3.3 daily
cash reconciliation). Two-person handling reduces fraud risk.
Nightly deposit or bank-drop reduces on-premises cash.

### 3.3 The ACH workflow

ACH auto-drafts are the operator's dream — payment happens
automatically without labor:

- Customer authorizes ACH at contract signing (NACHA-compliant
  authorization).
- Payment cadence and account established.
- ACH batch runs on payment date (via processor).
- Successful ACH: payment applied automatically.
- Failed ACH: NSF notice received, customer contacted,
  payment rescheduled or alternate method arranged.

ACH failures happen — NSF (insufficient funds), closed
accounts, changed banking. Each failure creates a mini-workflow
(contact customer, arrange alternate, sometimes charge NSF
fee).

### 3.4 Debit card operations

Debit card payments:

- Customer provides card at office or online.
- Processor debits card in real time.
- Immediate confirmation.
- Payment posted to account.
- Processing fee incurred by dealer (typically 1.5%–3.5% of
  payment).

For weekly / biweekly cadence, some stores set up recurring
debit charges. Card expirations and declines require follow-up.

### 3.5 Payment posting

Regardless of method, every payment must be **posted** to the
customer's account:

- Payment amount recorded.
- Payment date recorded.
- Payment applied to: late fees (first), interest (second),
  principal (third) — this is standard installment-loan
  application order.
- New balance calculated.
- Next payment due date updated.
- Payment history log updated.

**Application discipline matters.** If payments post to wrong
accounts (customer with similar name), or partial payments
get applied incorrectly, or late fees aren't captured, the
account state diverges from reality.

### 3.6 Payment promises (PTP)

A **Promise to Pay** (PTP) is a customer commitment to make a
payment on a specific future date:

- Customer says "I'll pay Friday at 5pm."
- Office records the PTP with date, amount, method promised.
- Follow-up scheduled for the promised date.
- If PTP is kept: normal payment processing.
- If PTP is broken: escalation, new PTP request or
  disciplinary action.

PTPs are a core collections tool (§4). Well-managed PTPs
signal customer engagement; broken PTPs signal trouble.

### 3.7 Partial payments

Customer can't pay the full amount but can pay something.
Handling varies:

- **Accept partial** — apply to account, expect balance
  soon. Customer stays "current" for late fee purposes if
  policy permits.
- **Accept but count late** — payment applied but account
  remains flagged past due.
- **Reject** — some stores reject partials and require full
  payment. Rare and generally counterproductive (rejecting
  cash worsens outcomes).

Most BHPH stores accept partials with a defined policy
about when the balance must be brought current.

### 3.8 Late fees

Standard practice: after a grace period (3-7 days typical),
a late fee is assessed. Amount is usually a flat dollar
($15-$50) or percentage of payment. State usury laws cap
some of this.

Late fee policy considerations:

- Consistent application (fair-lending concern; every
  customer treated the same).
- Waiver policy (when do you waive? Once per year for
  otherwise-good customers?).
- Compounding rules (does a second late fee apply to the
  same missed payment?).
- Communication (customer notified of late fee at
  application).

### 3.9 Receipt generation

Every payment produces a receipt:

- **Physical receipt** for in-person cash payments (still
  standard).
- **Digital receipt** by text or email for card / ACH /
  online payments.
- **Coupon book stamp** for stores using paper payment books.

Receipts prove the payment was made. Customer disputes about
"I already paid that!" are resolved via receipt evidence.

### 3.10 Daily payment posting rhythm

The office's daily rhythm:

- Morning: check overnight ACH results, post successful
  drafts, flag failures.
- Morning: review yesterday's cash payments for posting
  confirmation.
- Throughout day: post in-person cash / card payments as
  they come in.
- Throughout day: reminders on today's due-date payments.
- End of day: cash count and deposit prep.
- End of day: report on today's payment activity, current
  delinquency, PTPs coming due tomorrow.

At a 200-account BHPH, this is a full-time job for one
person or half-time for two.

### 3.11 Payment history and account statement

At any moment, the office should be able to show a customer
their complete payment history:

- Every payment date, amount, method.
- Every late fee assessed.
- Every modification applied.
- Current principal balance.
- Interest accrued (typically shown on statement).
- Next payment due date and amount.
- Payoff amount as of today (principal + accrued interest +
  any fees).

Some stores mail monthly statements; some make statements
available on request; some post on customer portals.

### 3.12 The "book" — the customer's account record

Historically, each BHPH customer had a physical file / book
containing:

- The RISC (contract).
- Payment coupon book.
- Payment history log (handwritten or printed).
- All notes about the customer.
- Copies of any modifications.

Modern BHPH stores use digital account records in DMS or
dedicated BHPH software. Some still maintain physical files
for legal / historical purposes.

---

## 4. Collections

Collections is where BHPH lives or dies. Every operator has a
collections philosophy; the best operators are firm but
empathetic.

### 4.1 The delinquency spectrum

Standard delinquency categorization:

- **Current** — payment made on schedule (or within grace
  period).
- **1–10 days late** — first stage of delinquency. Reminder
  contact.
- **11–30 days late** — meaningful delinquency. Escalated
  contact. Payment arrangements discussed.
- **31–60 days late** — serious delinquency. Repossession
  consideration begins. Vehicle location confirmed.
- **61–90 days late** — repossession typically ordered
  (customer-dependent, state-law-dependent).
- **91+ days** — repossession completed or account in
  collections / charge-off consideration.

Different portfolios use slightly different thresholds. Deep
subprime portfolios often see faster escalation.

### 4.2 First-touch reminder

At the first sign of delinquency (day 1-3 past due), a soft
reminder:

- **Text message** — quickest, least invasive. "Hi Sara,
  just a friendly reminder your payment was due yesterday.
  Please call us if you need to arrange."
- **Phone call** — direct contact. Voice message or
  conversation.
- **Email** — for customers who prefer email.

Tone matters. First-touch reminders should be friendly and
non-accusatory. Many first-touch customers just forgot; they
pay within a day. Aggressive tone at first-touch damages
relationships with customers who would have paid anyway.

### 4.3 Escalation contact

Day 5-15 past due:

- Multiple contact attempts if no response.
- Increasingly direct language.
- Request for PTP if customer can't pay in full immediately.
- Note-taking on every contact attempt (voicemails left,
  no-answer, disconnected number).

Collections notes are legal documentation. Sloppy note-taking
creates disputes; disciplined notes support both collections
effectiveness and compliance defensibility.

### 4.4 Payment arrangement conversation

When the customer can't pay the full amount now:

- **Partial payment today, balance by X** — customer commits
  to a specific plan.
- **Full payment by later specific date** — PTP for a future
  date.
- **Modified payment schedule going forward** — larger
  restructuring.
- **Referral to hardship program** if the store has one.

Payment arrangements are documented. Customer commits verbally
or in writing (some stores get written confirmation via text
or portal).

### 4.5 Promise-to-pay tracking

Every PTP:

- Recorded with amount, date, method promised.
- Tracked for fulfillment.
- Follow-up scheduled for the promised date.
- Kept promises reduce delinquency counts.
- Broken promises escalate the customer to next tier.

Sophisticated BHPH tracks a **PTP kept rate** per customer
and portfolio-wide. Customers who consistently keep PTPs are
generally lower risk than customers who consistently break
them, even if the eventual payments come through.

### 4.6 Skip tracing

**Skip** — customer who has disappeared (unreachable at all
contact points).

Skip tracing techniques:

- Contact the emergency contacts / references from the
  original app.
- Contact previous employer.
- Check social media for location clues.
- Address / phone number searches via skip-tracing services
  (Accurint, TLO, LocatePlus — professional data services).
- Vehicle GPS if installed and active.
- Contact drive-past to previous addresses.

Skip tracing has compliance boundaries (FDCPA, state consumer
protection, privacy law). Discipline required.

### 4.7 Repossession decision

At some point, non-paying customers become repossession
candidates. The decision:

- **How long delinquent?** — most stores have a threshold
  (30 days typical, 60 days conservative).
- **Prior payment history?** — a customer with 20 months of
  good history gets more grace than a customer 4 months in.
- **Customer engagement?** — customer who calls in and
  explains, versus customer who dodges calls.
- **Vehicle situation?** — do we know where the vehicle
  is? Is it in drivable condition?
- **Recovery cost vs recovery value?** — is the vehicle
  worth enough to justify $500-$1000 repo costs?

Repossession is a judgment decision. Some stores repo
faster; some slower. Faster repo reduces portfolio losses
but produces more customer / community friction. Slower repo
preserves customer relationships but risks larger losses.

### 4.8 Communication ethics and legal boundaries

BHPH collections must comply with:

- **FDCPA** — technically applies to third-party collectors
  more than creditors, but many states extend to first-party
  creditors, and best practice follows FDCPA guidelines
  regardless.
- **State consumer collection laws** — vary widely; some
  states have very strict first-party collection rules.
- **TCPA** — restrictions on automated calls and texts.
- **Fair Debt Collection Practices** — no harassment, no
  false statements, no third-party disclosure of the debt.
- **Fair Credit Reporting Act** — if reporting to bureaus,
  reporting must be accurate.

Aggressive collections that stray outside compliance create
legal exposure. Every BHPH operator should have a written
collections policy and staff training.

### 4.9 Hardship situations

Real hardship (job loss, illness, family crisis, natural
disaster) requires judgment:

- **Deferral** — postpone this month's payment; add to end
  of loan.
- **Reduced payment temporary** — smaller payments for a
  defined period; then return to regular payments.
- **Modified schedule** — permanently smaller payments over
  extended term.
- **Voluntary surrender** — customer voluntarily returns
  vehicle; no repo cost, no forcible recovery.
- **Debt forgiveness** — rare; typically only for the most
  severe cases (customer's death, terminal illness).

Wise operators distinguish "won't pay" from "can't pay." The
first is a repossession candidate; the second is a
modification candidate. Getting this distinction wrong costs
either customer relationships or portfolio losses.

### 4.10 Hardening the account

Some customers repeatedly slip into delinquency but recover
each time. Options:

- **Payment plan adjustment** — change from monthly to
  weekly (matches cadence to paycheck).
- **Auto-draft requirement** — mandatory ACH going forward
  to remove customer discretion.
- **Additional collateral** — rare in BHPH but possible.
- **Referee / co-signer addition** — bringing in a family
  member as guarantor.

These hardenings are negotiated and documented.

---

## 5. Portfolio Management

The portfolio is the business asset. Managing it well is what
distinguishes surviving BHPH operators from failing ones.

### 5.1 Portfolio composition

At any moment, the portfolio consists of:

- **Active accounts** — customers paying on schedule.
- **Delinquent accounts** — customers past due.
- **Charged-off accounts** — accounts written off, still
  possibly collectible.
- **Bankruptcy accounts** — customers in bankruptcy
  proceedings.
- **Recently paid-off accounts** — customers who completed
  loans (repeat-buyer prospects).

Portfolio management is about understanding, monitoring, and
optimizing this composition.

### 5.2 Portfolio metrics

The metrics BHPH operators actually watch:

**Delinquency metrics:**

- **Current-to-30 delinquency %** — accounts 1-30 days past
  due as % of total accounts.
- **30-60 delinquency %** — deeper delinquency.
- **60+ delinquency %** — serious delinquency.
- **Rolling delinquency** — accounts that "roll" into worse
  buckets each month (getting worse).
- **Cure rate** — accounts that recover from delinquency to
  current.

**Portfolio loss metrics:**

- **Static pool loss %** — for a specific cohort of loans
  (loans booked in a specific month or quarter), cumulative
  losses over time. Best metric for measuring BHPH
  underwriting quality. Typical range 15%-30% cumulative
  losses on a static pool.
- **Charge-off rate** — accounts charged off in the period,
  as % of portfolio.
- **Recovery rate** — dollars recovered on charge-offs, as %
  of charge-off amount.
- **Net loss %** — charge-offs net of recoveries.

**Cash flow metrics:**

- **Portfolio yield** — annualized interest income / average
  portfolio balance.
- **Cash flow per account** — average monthly cash generation.
- **Portfolio principal collections** — actual principal
  paydowns per period.

**Growth / composition metrics:**

- **New account additions per month** — sales pace.
- **Payoffs per month** — customers completing loans.
- **Net portfolio growth** — additions minus payoffs and
  charge-offs.
- **Average account balance** — trending up or down.
- **Average term remaining** — portfolio "seasoning."

**Repeat-buyer metrics:**

- **Repeat buyer %** — new sales that are prior BHPH
  customers.
- **Loyalty lift** — repeat buyer close rate vs. new customer
  close rate.

### 5.3 Static pool analysis

The gold-standard BHPH performance metric. A **static pool**
is the set of all loans booked in a specific vintage (e.g.,
"all loans booked in Q1 2024"). Static pool analysis tracks
that pool's performance over time:

- Month 1: 100% of accounts current (or close to it).
- Month 6: X% current, Y% delinquent, Z% charged off.
- Month 12: pattern continues.
- Month 36: pool substantially resolved (paid off, charged
  off, or still paying).

Cumulative losses on a static pool tell the story of
underwriting quality. Pools with high early losses signal
underwriting problems (took bad customers, took bad vehicles,
priced too high).

Portfolio managers watch static pool performance by vintage
to spot underwriting drift.

### 5.4 Portfolio aging

The **portfolio aging report** shows accounts distributed by
delinquency bucket, at a point in time:

- Current: X% of accounts.
- 1-10 days: Y%.
- 11-30 days: Z%.
- 31-60 days: W%.
- 61-90 days: V%.
- 91+ days: U%.

Healthy portfolio: 75-85% current, minimal serious
delinquency.

Struggling portfolio: 50-60% current, meaningful concentration
in 30+ days.

Owner reviews aging at least weekly; some daily.

### 5.5 Risk indicators

Early warning signs on individual accounts:

- Payment date drift (customer starts paying later each
  month).
- Method changes (customer switched from ACH to cash,
  suggesting bank issues).
- Broken PTPs.
- Contact avoidance (customer not answering calls).
- Vehicle location changes (GPS shows unexpected patterns).
- Third-party contact (family member calls asking questions).
- Insurance lapse.

Portfolio-wide indicators:

- Rising delinquency %.
- Rising charge-off rate.
- Falling PTP kept rate.
- Falling cash flow per account.
- Rising portfolio aging days.

### 5.6 Cash flow forecasting

Portfolio produces predictable cash flow (mostly):

- Scheduled principal + interest per active account per
  period.
- Reduced for expected delinquency and charge-off.
- Adjusted for expected payoffs.
- Adjusted for seasonal patterns.

Cash flow forecasts inform:

- Buying capacity (can we buy more inventory this month?).
- Debt service (are we going to be able to make our
  payments?).
- Owner draws.
- Growth investments.

Sophisticated BHPH operators forecast cash flow 30-90 days
ahead.

### 5.7 Repeat customer identification

Customers approaching payoff are prime candidates for repeat
purchase. The portfolio management function identifies:

- Customers with 6 or fewer months remaining.
- Customers with good payment history (proven).
- Customers whose vehicles are aging.
- Customers who mentioned upcoming needs in conversations.

These customers get proactive outreach for repeat-purchase
conversations (see `SALES_DEPARTMENT_MAPPING.md` §4.4 equity
mining).

### 5.8 Portfolio segmentation

Sophisticated operators segment the portfolio for management:

- **By vintage** — when the loan was booked.
- **By payment method** — ACH vs cash vs debit.
- **By risk tier** — the credit / down / vehicle-based tier
  at origination.
- **By collector** — which collector handles which accounts.
- **By vehicle class** — trucks vs cars vs SUVs.
- **By dealership location** — for multi-location operators.

Segmentation surfaces where underwriting or collections is
working / not working.

---

## 6. Vehicle Recovery (Repossession)

Repossession is the enforcement mechanism of last resort. It's
unpleasant work with real operational and reputation
implications.

### 6.1 The repossession decision

Reiterating from §4.7:

- Length of delinquency (typically 30+ days).
- Payment history (long-term good customer vs. new problem).
- Customer engagement (talking to us vs. hiding).
- Vehicle situation (known location, drivable, recoverable).
- Cost-benefit (repo cost vs. recoverable value).

The owner or a designated authority (collections manager)
approves the repo. The order goes to a recovery agent.

### 6.2 Repossession agents

Two models:

- **Third-party recovery agent** — most common at small and
  mid-sized BHPH. Store has relationships with 1-3 local
  agents. Agent is licensed, insured, and specializes in
  vehicle recovery.
- **In-house recovery** — larger operations. Store maintains
  its own repo trucks and staff. More control, more cost.

Recovery agents charge fees:

- **Flat repo fee** — $350-$800 per successful recovery.
- **Storage fees** — per day the vehicle sits at agent's lot
  before store pickup.
- **Skip fees** — additional charges when the vehicle
  location must be investigated.
- **Voluntary surrender fees** — smaller fees when the
  customer surrenders voluntarily and the agent just picks
  up.

### 6.3 Skip tracing

When the vehicle location is unknown:

- Recovery agent uses skip tracing tools (§4.6).
- GPS on vehicle (if installed) helps immediately.
- Sometimes the customer is home; sometimes at work;
  sometimes hidden.
- Agents patiently monitor known locations, waiting for the
  vehicle.
- Some vehicles are never recovered ("skips"). Account
  charge-off follows.

### 6.4 GPS-assisted recovery

Many BHPH stores install GPS trackers on vehicles at sale.
Benefits:

- Locate vehicle for repossession (dramatically reduces skip
  rate).
- Recover in remote / unusual locations.
- Confirm vehicle is being used as customer represents
  (going to work vs. sitting).
- Some GPS systems also disable the vehicle (see §6.5).

Regulations vary. Some states require disclosure of GPS
tracking. Best practice: disclose at contract signing, note
in the contract, and update customer if devices are
activated.

### 6.5 Starter interrupt devices

Devices that prevent the vehicle from starting when payment
is missed:

- Installed at sale.
- Customer receives a payment code monthly that keeps the
  vehicle running.
- Missed payment → no new code → vehicle won't start.
- Grace-period warning tones typically precede shutdown.

Controversial. Regulated in several states (Nevada, Wisconsin,
others have specific rules or prohibitions). Consumer
advocates argue devices strand people in dangerous locations
or force payment under duress.

Operators who use starter interrupts must:

- Disclose clearly at sale.
- Follow all state rules on notice / warning tones /
  operational safety.
- Have policies for emergencies (medical, weather).
- Weigh the collections lift against reputation and legal
  exposure.

Many BHPH operators avoid starter interrupts entirely for
these reasons.

### 6.6 Post-repossession processing

Once vehicle is recovered:

- Transport from recovery agent lot to dealership (or agent
  delivers).
- Physical inspection at arrival:
  - Condition assessment (damage, wear, missing parts).
  - Inventory check (customer's personal items in the
    vehicle — must be returned to customer per most state
    laws).
  - Mileage recorded.
  - Photos taken.
- Personal items secured and inventoried; customer notified
  and given a window to retrieve.

### 6.7 State redemption rules

Most states give the customer a right to **redeem** the
vehicle after repossession — pay the delinquency (plus repo
costs and possibly full acceleration of the loan) to get the
vehicle back. Redemption windows are state-specific (10-30
days typical).

During redemption:

- Vehicle is held; not resold.
- Customer receives formal notice of repossession, right to
  redeem, and amount to redeem.
- If customer redeems, account continues; vehicle returned.
- If customer doesn't redeem, vehicle can be sold.

### 6.8 Deficiency / surplus handling

After the redemption window, if the customer didn't redeem,
the vehicle is sold (wholesale or retail after recon).

Accounting:

- Sale proceeds - unpaid balance - repo costs = deficiency
  or surplus.
- **Deficiency** (proceeds insufficient to cover loan +
  costs) — customer may owe the deficiency; some states
  require formal deficiency-judgment procedures.
- **Surplus** (proceeds exceed loan + costs) — customer is
  entitled to surplus per most state laws.

Deficiency collection is difficult in practice (customer who
couldn't pay the loan often can't pay the deficiency either).
Some stores pursue via collections agency; some write off
deficiencies as charge-off.

### 6.9 Reconditioning after repossession

Repossessed vehicles need recon before resale:

- Interior cleaning (often heavily needed — cars sat, got
  neglected).
- Mechanical assessment (customer may have deferred
  maintenance).
- Body condition (repo agents sometimes cause minor damage).
- Detail.

Repo units come back rougher than typical trades. Recon
costs on repos often exceed initial-acquisition recon costs
on the same unit years earlier. See `RECON_MAPPING.md`.

### 6.10 Resale — retail vs wholesale

Post-recon, the repossessed vehicle needs disposition:

- **Retail** — put back on the lot, sell to a new customer,
  potentially another BHPH deal. Highest proceeds; longest
  timeline; recon cost investment.
- **Wholesale to another dealer** — dispose quickly at
  wholesale price; recovery is less but faster.
- **Auction** — send back to auction; recovery varies.

Choice depends on: vehicle condition, current inventory
needs, market timing, cash flow priorities.

### 6.11 Customer relationship after repo

The customer relationship typically ends at repo. Occasionally:

- Customer comes back after financial recovery, asks for
  another chance. Some operators consider; some categorically
  refuse.
- Customer refers a family member. Awkward but happens.
- Customer files a complaint or lawsuit. Requires legal
  response.

The community sees repos. A store known for aggressive or
unfair repos loses future customers. A store known for fair
handling even in bad situations builds long-term reputation.

---

## 7. Compliance

BHPH compliance is a multi-layer stack. Awareness-level only in
this section; every BHPH operator must build a real program
with counsel.

### 7.1 Consumer lending — Truth in Lending Act (Reg Z)

Same as covered in `FINANCE_DEPARTMENT_MAPPING.md` §6.1 —
APR disclosure, finance charge, itemization, payment
schedule, security interest. Applies fully to BHPH.

### 7.2 State usury caps

Most states cap the maximum interest rate on consumer auto
loans. Common ranges: 21%-29.99% APR. Some states have no
cap or very high caps for auto loans specifically. Some have
sliding scales based on loan amount.

Operating above the cap creates significant legal exposure
(unenforceable loans, statutory damages, potential license
loss).

### 7.3 State BHPH licensing

Some states require specific BHPH dealer licenses in addition
to regular dealer licenses:

- **BHPH-specific license** — required for dealer-financed
  sales.
- **Sales finance license** — some states require a separate
  license for the finance operation.
- **Retail installment seller license** — some states.

Requirements vary from "check a box on your regular dealer
license application" to "detailed application with capital
requirements and annual reporting."

### 7.4 Repossession law

Every state has its own repossession law:

- **Notice requirements** — pre-repo notice? Post-repo
  notice? Content requirements?
- **Peaceful repossession** — how "peaceful" is defined
  varies; breach of peace during repo can invalidate the
  recovery.
- **Redemption rights** — window and terms.
- **Right to notice of sale** — customer notice before
  vehicle is sold.
- **Deficiency judgment** — process and requirements.
- **Personal property in vehicle** — return requirements and
  timelines.

Repossessions handled incorrectly under state law can
result in wrongful-repossession lawsuits with real damages.

### 7.5 Collection regulations

- **FDCPA** — federal law regulating debt collection. Most
  strictly applies to third-party collectors, but many
  states extend to first-party creditors, and best-practice
  follows FDCPA regardless.
- **TCPA** — federal law on automated calls and texts.
  Prior express consent required.
- **State-specific collection laws** — some states have very
  strict first-party collection rules (prohibited hours,
  disclosure requirements, harassment definitions).

### 7.6 Customer privacy — GLBA

Same as covered in `FINANCE_DEPARTMENT_MAPPING.md` §6.4:

- Privacy notice at start of customer relationship.
- Safeguards Rule requirements for information security.
- Non-public personal information protection.

BHPH portfolios contain years of customer financial
information — extensive NPI accumulates over time. Security
matters.

### 7.7 Fair credit reporting (FCRA)

If the store reports customer payment history to credit
bureaus (some BHPH does, some doesn't):

- Reporting must be accurate.
- Customer disputes must be investigated within timelines.
- Adverse-action notices required.
- Furnisher obligations continue as long as reporting
  continues.

Some BHPH stores don't report because reporting requires
ongoing compliance work. Non-reporting means customers'
positive BHPH payment history doesn't help their credit —
which some customers care about, some don't.

### 7.8 GPS / starter interrupt device disclosure

State rules vary:

- Nevada, Wisconsin, others: specific disclosure and
  operational rules.
- General: best practice is contractual disclosure at
  signing.
- Emergency access requirements (some states require
  emergency starts even after shutoff).

### 7.9 Records retention

- Contracts, payment history, collection notes: retained per
  state and federal rules (typically 5-7 years post-payoff
  or charge-off).
- Repo records: retained per state redemption / deficiency
  rules.
- Consumer complaint records: retained per state consumer
  protection rules.

Digital retention subject to Safeguards Rule (encrypted,
access-controlled). Paper retention subject to Disposal Rule.

### 7.10 State audit exposure

State regulators (attorney general, banking / consumer credit
division, DMV) audit BHPH operations:

- Rate compliance.
- Disclosure accuracy.
- Collection practices.
- Repo compliance.
- Licensing status.
- Consumer complaint history.

Audit prep means having records organized, policies
documented, staff trained. Ad hoc audits are more common in
states with active consumer protection agencies.

---

## 8. Pain Points

Repetitive friction BHPH staff experience daily. Documentation
only; no solutions proposed.

### 8.1 Daily payment posting volume

At a 200-account BHPH, daily payment posting is dozens of
transactions per day. Cash counting, receipt generation,
DMS posting, exception handling. Full-time work.

### 8.2 Reminder call fatigue

Making 30-50 reminder calls a day is exhausting. Many go to
voicemail. Every voicemail should be logged. Every reached
customer requires a real conversation.

### 8.3 Payment method chaos

Some customers pay ACH, some cash, some debit, some online,
some third-party. Different processors, different confirmation
patterns, different failure modes. Reconciliation across
methods is manual.

### 8.4 Promise-to-pay tracking

Every PTP taken becomes a follow-up task for the promised
date. At 20+ PTPs open at any moment, the tracking is
challenging in spreadsheets.

### 8.5 Missed follow-ups

The collector planned to call Sara today but got pulled into
a walk-in customer. Sara didn't get called. Small oversights
accumulate.

### 8.6 Skip investigations

Customer disappeared. Investigating takes hours — calling
references, driving by addresses, checking social media,
using skip-tracing services. Sometimes fruitless.

### 8.7 Repo coordination

Ordering a repo, tracking recovery agent progress, dealing
with agent delays, coordinating vehicle pickup, processing
personal property return — dozens of steps per repo.

### 8.8 Vehicle return processing

Recovered vehicle arrives. Inspection, inventory, photos,
personal property, mileage check, damage documentation.
Real time per vehicle.

### 8.9 Customer disputes about payments

"I paid on the 5th, not the 8th!" Requires pulling payment
history, receipt lookup, sometimes bank statement comparison.
Time-consuming.

### 8.10 Insurance lapse monitoring

Customer's insurance lapses. Store gets notice from insurer.
Now what? Contact customer, arrange replacement coverage, or
consider CPI (collateral protection insurance), or consider
repo. All manual chasing.

### 8.11 Portfolio reporting for owner

Owner wants: current delinquency, this week's collections,
top-risk accounts, cash flow projection, repo pipeline. Every
week. Building reports from DMS data takes hours.

### 8.12 Compliance documentation

Written policies, staff training records, compliance
attestations, state-specific filings. Ongoing paperwork.

### 8.13 Account reconciliation

Payments posted, late fees assessed, modifications applied,
interest accrued. Ensuring the customer's account balance
matches actual dollars owed. Discrepancies require investigation.

### 8.14 Multi-source communication tracking

Customer sent a text, called two days later, came in yesterday
in person, sent an email today. Piecing together the customer's
full communication history requires checking multiple systems.

### 8.15 Deferred / modified account edge cases

Every modification is a bespoke deal. Deferrals don't fit
standard payment schedules. Modified terms don't match the
original coupon book. Manual account setup.

### 8.16 Charge-off decisions

Which accounts to charge off this month? Every one gets
individual review. Judgment fatigue.

### 8.17 Deficiency collection

Post-repo, the customer owes a deficiency. Nine times out of
ten, uncollectible. Should we chase? Write off? Legal action?
Ambiguous decisions.

### 8.18 Repeat-buyer identification

Customers approaching payoff should get repeat-buyer outreach.
Identifying them manually requires reviewing the portfolio.

### 8.19 Hardship judgment fatigue

Real hardships vs. excuses. Every conversation requires
judgment. Wrong judgment either costs money (accepting excuses
as hardship) or destroys relationships (dismissing real
hardship).

### 8.20 Community / reputation friction

Repos in a small community are visible. Angry customers post
online reviews. Family members complain. Emotional labor for
staff.

---

## 9. Operational Decisions

Decisions BHPH staff make repeatedly. Each is a candidate for
future decision-support intelligence.

### 9.1 Which customers to contact today

Every morning: current delinquency list, PTPs due today,
follow-ups scheduled. Priority order?

### 9.2 Which accounts present elevated risk

Payment history patterns, communication engagement, vehicle
issues, life circumstances. Which accounts need proactive
outreach before they hit delinquency?

### 9.3 Should we offer a payment arrangement?

Customer asks for a modification. Judgment: legitimate need,
first-time ask, part of a pattern, high-value customer?

### 9.4 Has the PTP been kept?

For each open PTP, check payment activity. Kept promises
build trust; broken promises escalate.

### 9.5 Is repossession appropriate?

Customer 45 days past due. Repo now, or wait, or work with
the customer?

### 9.6 Repair or wholesale a returned vehicle?

Post-repo vehicle. Retail with recon, wholesale to a peer,
send to auction?

### 9.7 Which customers are likely repeat buyers?

Approaching payoff, good payment history, established
relationship. Which ones to prioritize for outreach?

### 9.8 How aggressive to be with collections cadence?

More contact reduces delinquency; more contact damages
relationships. Where's the balance?

### 9.9 Should we harden the account?

Repeatedly delinquent customer. Move to ACH-only, weekly
cadence, tighter oversight?

### 9.10 Is this a "won't pay" or "can't pay"?

Every serious delinquency requires this judgment. Wrong
answer either creates portfolio loss or destroys customer
relationships.

### 9.11 Should we waive this late fee?

First-time miss for a great customer, or first-time miss for
a problem customer, or repeat late fee same account?

### 9.12 Do we send this to charge-off this month?

Aged charge-off candidates. Continue chasing or write off?

### 9.13 Do we accept a partial payment now vs. requiring full?

Customer offers $300 vs. the $500 due. Accept and buy time,
or push for full amount?

### 9.14 Do we allow a payment modification without written
approval?

Verbal agreements are fast but risky. Written modifications
protect but take time.

### 9.15 Should we offer this customer another vehicle?

Repo'd customer wants to try again. Second chance policy?

### 9.16 Do we report this account to credit bureau?

Ongoing choice about whether to report positive / negative
payment history.

---

## 10. Automation Opportunities

Where repetitive administrative work lives. Opportunity
identification only.

### 10.1 Payment reminder cadence automation

Every customer's payment cadence generates reminder events
automatically (text / email / call queue). Reduces manual
scheduling.

### 10.2 Payment posting automation

Cash / debit / ACH payments post to the correct account with
correct application order (fees → interest → principal) with
minimal manual entry.

### 10.3 PTP tracking with follow-up scheduling

Every PTP creates a follow-up task on the promised date.
Kept promises auto-close. Broken promises escalate.

### 10.4 Delinquency queue with prioritization

Daily queue of customers to contact, prioritized by risk /
timing / assignment. Reduces "who to call first" cognitive
load.

### 10.5 Portfolio dashboard for owner

Real-time view: current delinquency, cash flow this week,
top-risk accounts, this month's charge-offs, repo pipeline,
month-over-month trends. Reduces manual report building.

### 10.6 Communication draft assistance

Reminder texts, PTP follow-ups, payment confirmations,
hardship acknowledgments — all draftable given the context.
Human reviews and personalizes.

### 10.7 Daily work queue

Each collector's daily list: contacts to make, PTPs due,
scheduled follow-ups, priority accounts. Personalized and
manageable.

### 10.8 Account-status monitoring

Real-time account status changes surface to relevant staff:
NSF returned, insurance lapsed, GPS anomaly, payment method
change.

### 10.9 Skip-tracing assistance

Automated aggregation of skip-tracing signals (last known
address, employer, references, social media presence) into a
consolidated view.

### 10.10 Repossession workflow tracking

Order created → agent assigned → status updates → recovery
confirmation → vehicle receipt → inspection → resale
disposition. Steps and dates tracked.

### 10.11 Static pool analysis

Loans booked in Q1 tracked over time as a cohort. Losses
accumulated. Comparison across vintages surfaces underwriting
drift.

### 10.12 Repeat-buyer identification

Customers within 6 months of payoff, with good payment
history, flagged for repeat-buyer outreach.

### 10.13 Deficiency collection tracking

Post-repo deficiencies tracked, aged, escalated per policy.

### 10.14 Compliance calendar

Annual license renewals, state reporting deadlines, staff
training refreshes, policy review cadence — all calendar
events.

### 10.15 Insurance lapse detection

Insurance status monitored (via daily or weekly checks with
insurers). Lapses surfaced immediately for follow-up.

### 10.16 Charge-off eligibility list

Accounts eligible for charge-off per store policy surfaced
for monthly review. Reduces manual portfolio review.

### 10.17 Contact history unification

All customer contacts (text, call, in-person, portal) in one
timeline. Any staff member picking up the customer sees full
history.

Each is a candidate for its own future planning session.

---

## 11. Cross-Department Dependencies

### 11.1 Inventory & Acquisition

**BHPH Operations depends on Inventory for:**
- Appropriate inventory selection for the BHPH customer
  profile (reliable used vehicles at the right price points).
- Fair acquisition cost basis (BHPH gross has to work over
  the loan life, not just at sale).
- Reasonable recon budget (over-reconditioning eats gross).
- Timely front-line-ready units.
- Willingness to take back repo vehicles into inventory.

**Inventory depends on BHPH Operations for:**
- Feedback on which vehicles perform well through BHPH
  contracts (last the loan term, few warranty claims, low
  repo rates).
- Feedback on repo-return condition patterns (which
  vehicles come back beaten up).
- Coordination on repo units (recon needs, disposition
  decisions).

### 11.2 Recon

**BHPH Operations depends on Recon for:**
- Quality reconditioning that produces vehicles that last
  the loan term.
- Post-repo reconditioning quality (returned vehicles need
  to be resellable).
- Vehicle-issue support for customer vehicles under BHPH
  contract (some stores offer in-house service to BHPH
  customers).

**Recon depends on BHPH Operations for:**
- Notification of repo returns (planned incoming work).
- Coordination on repo unit disposition (retail vs
  wholesale).
- Feedback on customer complaints traceable to recon
  quality.

### 11.3 Sales

**BHPH Operations depends on Sales for:**
- Appropriate customer selection (customers who can
  actually pay).
- Realistic customer expectations at sale (payment
  cadence, terms, consequences of default).
- Accurate customer information collection (contact info,
  references, employer, income).
- Positive customer handoff (customer feels good about the
  purchase and the store; more likely to succeed).
- Coordination on repeat-buyer opportunities.

**Sales depends on BHPH Operations for:**
- Portfolio-based repeat-buyer leads.
- Feedback on customer success / failure patterns.
- Guidance on inventory positioning (which vehicles work
  for the BHPH customer segment).

### 11.4 Finance / F&I

**BHPH Operations depends on F&I for:**
- Clean deal writing at sale (contract accuracy is
  foundational).
- Product structure (VSC, GAP on BHPH deals is often
  omitted — but sometimes offered).
- Compliance foundation (Reg Z, disclosures).

**F&I depends on BHPH Operations for:**
- Portfolio performance data (what deal structures
  perform).
- Customer success signals for pricing / product decisions
  at sale.

### 11.5 Accounting

**BHPH Operations depends on Accounting for:**
- Correct installment-sales accounting (deferred gross
  profit).
- Portfolio reporting (schedules, aging, cash flow).
- Charge-off accounting.
- Repo inventory accounting.
- Reserve for uncollectible accounts.
- Tax filings on BHPH-specific items.

**Accounting depends on BHPH Operations for:**
- Payment posting discipline.
- Charge-off recommendations with documentation.
- Repo cost tracking.
- Deficiency / surplus documentation.
- Portfolio-management data for reporting.

### 11.6 Customers

**BHPH Operations depends on Customers for:**
- Payments per contract terms.
- Honest communication about problems.
- Maintaining insurance.
- Notification of address / phone / employment changes.
- Cooperation during hardship discussions.
- Positive word-of-mouth in the community.

**Customers depend on BHPH Operations for:**
- Fair collections practices.
- Willingness to work with hardship.
- Accurate payment tracking.
- Prompt receipts.
- Reasonable communication cadence.
- Respect and dignity throughout the relationship.
- Support with vehicle problems where possible.

### 11.7 Vendors

**BHPH Operations depends on Vendors for:**
- Recovery agents (repossession services).
- GPS / starter interrupt device providers.
- Skip-tracing services.
- Payment processors (debit, ACH, portal).
- Third-party payment intake (PayNearMe, MoneyGram).
- Occasionally: portfolio finance / factoring lenders.
- Occasionally: collections agencies for charge-off
  recovery.

**Vendors depend on BHPH Operations for:**
- Prompt payment.
- Compliance with vendor requirements (agent licensing,
  processor rules, device installation standards).
- Fair volume / relationship.

### 11.8 Community / regulators

**BHPH Operations depends on the Community for:**
- Customer base (repeat + referral is the growth engine).
- Reputation as fair and helpful.
- Word-of-mouth referrals.
- Community goodwill.

**Community depends on BHPH Operations for:**
- Access to vehicles for customers other lenders won't
  serve.
- Fair dealings that don't cause community harm.
- Local employment.
- Support for community events / sponsorships.

State regulators expect: compliance, transparency, honest
dealing, willingness to cooperate with consumer protection
inquiries.

---

## 12. Deferred Ideas

Ideas that surfaced during BHPH research but belong to other
departments' future research. Recorded briefly; not expanded.

**Sales** — BHPH-specific customer acquisition (community
outreach, direct mail targeting, radio for BHPH audiences),
payment-shopper conversation flow, structured "second chance"
customer education, deferred-down handling from sales floor.

**F&I** — BHPH deal structuring (down / term / payment
optimization), payment cadence selection at sale, product
offering (VSC / GAP appropriateness on BHPH deals), TIL
disclosure discipline for BHPH.

**Inventory & Acquisition** — BHPH-specific vehicle selection
(older, cheaper, reliable), acquisition strategy for the
portfolio (units that will last 24-42 months), post-repo
disposition strategy.

**Recon** — Post-repo reconditioning workflow, vehicle
condition patterns from repo returns, in-house service for
BHPH customer vehicles.

**Accounting** — Detailed installment-sales accounting,
deferred gross profit management, reserve for uncollectible
accounts modeling, charge-off timing decisions, tax method
election implications.

**Compliance** — BHPH-specific compliance program design,
state-by-state BHPH license tracking, repo law playbook per
state, collection practice policy documentation, staff
training program.

**Customer / CRM** — Long-term customer relationship tracking
across the loan life, contact management, communication
preferences, life-event tracking, family / referral network
mapping.

**Portfolio Management Software** — Static pool analytics,
delinquency forecasting, cash flow modeling,
underwriting-drift detection, portfolio segmentation and
performance attribution.

**Payment Processing** — Multi-method payment intake, ACH
authorization management, debit card recurring, online
portal, kiosk, third-party (PayNearMe, MoneyGram) integration.

**Recovery Operations** — Recovery agent management, GPS
integration, starter-interrupt device management, skip-tracing
workflow, personal-property inventory workflow.

**Compliance Tooling** — TCPA-compliant communication (opt-in
management, consent tracking), FDCPA-aligned collection
scripts and cadence, state-specific compliance calendars.

**Bureau Reporting** — Metro 2 file generation, dispute
handling, furnisher obligations, monthly reporting cadence.

**Legal Workflow** — Bankruptcy notice handling, deficiency
lawsuit preparation, consumer complaint response,
regulator inquiry response.

**BHPH Customer Portal** — Customer self-service for payment,
account view, contact updates, PTP setup, hardship request
submission.

Each of the above deserves its own research session before
implementation.

---

## How to use this document

**For engineers and product people** starting BHPH-related
work: read sections 1–5 first (business model, customer
lifecycle, payment operations, collections, portfolio
management). Those sections carry the mental model. Read
section 11 (dependencies) before designing anything that
connects to other departments. Section 10 (automation
opportunities) is where product ideas start — but each
opportunity should be developed into its own scoped plan
before implementation.

**For AI agents** starting a BHPH-related session: this
document is source-of-truth for how independent BHPH
operations actually work. If anything you're asked to do
contradicts what's described here, push back. Particular
anti-patterns to flag:

- Any suggestion that AI should make repossession decisions.
  These are among the most consequential judgments in the
  business and belong to humans.
- Any suggestion that AI should judge "won't pay vs. can't
  pay" categorization. This requires human judgment about
  the customer's specific circumstances.
- Any suggestion that AI should determine hardship
  legitimacy. Hardship decisions are relationship decisions.
- Any suggestion that AI should communicate with customers
  in ways that violate FDCPA / TCPA / state collection law.
  All AI-drafted customer communications remain drafts
  pending human review.
- Any suggestion that "streamlined collections" means more
  aggressive collections. The best BHPH operators are firm
  but fair; automation should support that discipline, not
  overturn it.
- Any suggestion that starter-interrupt or GPS use should be
  default-on without explicit operator opt-in and
  jurisdiction-specific compliance review.
- Any suggestion that AI should charge off accounts
  autonomously. Charge-off is a business judgment with
  accounting, tax, and customer implications.

**For domain experts** reading this document: this is a
snapshot of common BHPH practice. Portfolio dynamics vary
enormously by market, customer selection, and operator
philosophy. Corrections and additions are welcome and
expected as the platform evolves.

**Update discipline.** Update this document when:
- Regulatory changes materially alter BHPH practice (new
  state rules, federal enforcement changes, TCPA updates,
  starter-interrupt legislation).
- Portfolio dynamics shift meaningfully in the industry.
- Common technology adoption changes (e.g., text-to-pay
  moving from novelty to standard).

Do **not** update this document with:
- Specific software product feature reviews.
- Personal opinions about specific recovery agents, GPS
  providers, or payment processors.
- Aggressive collection tactics or "hacks."
- Implementation designs.

---

## Glossary — BHPH terms used in this document

- **ACH** — Automated Clearing House. Electronic bank
  transfer.
- **BHPH** — Buy Here Pay Here. Dealer-financed vehicle
  sales.
- **Book** — Traditional term for the customer's account
  record; also "the book" for the whole portfolio ("the
  paper").
- **Cadence** — Payment schedule (weekly, biweekly,
  semi-monthly, monthly).
- **Charge-off** — Accounting recognition that an account
  is uncollectible; written off as expense.
- **Contract receivable** — The customer's outstanding
  principal balance; the portfolio asset on the balance
  sheet.
- **CPI** — Collateral Protection Insurance. Force-placed
  insurance when the customer's insurance lapses.
- **Cure rate** — Percentage of delinquent accounts that
  recover to current.
- **Deep sub / deep subprime** — Customers with severely
  impaired credit (FICO below 550 typical).
- **Deferred gross profit** — Under installment-sales
  accounting, gross profit not yet recognized because the
  cash hasn't been collected yet.
- **Deficiency** — Post-repo balance owed by the customer
  after vehicle sale proceeds are applied.
- **Delinquency** — Being past due on payments.
- **FDCPA** — Fair Debt Collection Practices Act.
- **FCRA** — Fair Credit Reporting Act.
- **FPD** — First Payment Default. Customer misses first
  payment. Strong early warning signal.
- **GLBA** — Gramm-Leach-Bliley Act. Financial privacy law.
- **Installment sale method** — Tax accounting method that
  defers gross profit recognition until payments are
  received.
- **NSF** — Non-Sufficient Funds. Bank returns an ACH or
  check for insufficient balance.
- **Paper** — Slang for the loan or the portfolio ("carry
  the paper").
- **Portfolio** — All open BHPH loan accounts collectively.
- **PTP** — Promise to Pay. Customer commitment to a
  specific future payment.
- **Redemption** — Customer's right to reclaim a
  repossessed vehicle by paying delinquent amounts (plus
  costs).
- **Repo / repossession** — Recovery of the vehicle from a
  defaulting customer.
- **Repo agent / recovery agent** — Third-party licensed
  agent who performs vehicle recovery.
- **Reserve for uncollectible accounts** — Accounting
  reserve for expected future portfolio losses.
- **RISC** — Retail Installment Sale Contract. The
  foundational loan document.
- **Roll / rolling delinquency** — When accounts get worse
  month-over-month, moving into deeper delinquency buckets.
- **Season / seasoning** — Age of the loan; seasoned
  accounts have proven payment history.
- **Skip** — Customer who has disappeared (no contact, no
  known location).
- **Skip tracing** — Investigation to locate a skip customer
  and/or vehicle.
- **Starter interrupt** — Device that prevents vehicle
  starting when payment is missed. Regulated.
- **Static pool** — Cohort of loans booked in a specific
  vintage; tracked for performance over time.
- **Surplus** — Post-repo excess when vehicle sale proceeds
  exceed the loan balance plus costs. Owed to the customer.
- **TCPA** — Telephone Consumer Protection Act. Regulates
  automated communications.
- **Term** — Length of the loan (typically 24-42 months for
  BHPH).
- **Truth in Lending Act (TILA / Reg Z)** — Federal
  disclosure law for consumer credit.
- **Voluntary surrender** — Customer voluntarily returns
  vehicle without forcible repossession.

---

## Related research

- `FINANCE_DEPARTMENT_MAPPING.md` — F&I; upstream of BHPH
  (deal writing) and adjacent to BHPH (both handle
  customer credit).
- `SALES_DEPARTMENT_MAPPING.md` — Sales; the front-end of
  every BHPH customer relationship.
- `INVENTORY_ACQUISITION_MAPPING.md` — Inventory; sources
  the vehicles BHPH sells.
- `RECON_MAPPING.md` — Recon; conditions the vehicles and
  handles post-repo reconditioning.
- `ACCOUNTING_DEPARTMENT_MAPPING.md` — Accounting; tracks
  portfolio, charge-offs, and BHPH-specific accounting;
  §3.16 covers BHPH accounting in detail.
- `VEHICLE_CENTRIC_PIVOT.md` — Architectural plan. BHPH
  operations touch multiple phases: the customer / CRM side
  extends the pivot's Phase 8 (Sale + Delivery); the
  portfolio management side is largely greenfield.
- `INDEPENDENT_DEALER_PIVOT.md` — Established the
  indie-first scope; BHPH is a subset of the indie space.

Deferred research topics — proposed during discovery but not
part of the initial corpus. May be revisited if implementation
surfaces a critical gap:
`TITLE_DEPARTMENT_MAPPING.md`,
`MARKETING_DEPARTMENT_MAPPING.md`,
`COMPLIANCE_DEPARTMENT_MAPPING.md`,
`SERVICE_DEPARTMENT_MAPPING.md` (for stores with in-house
service), `PAYROLL_DEPARTMENT_MAPPING.md`,
`CUSTOMER_CRM_MAPPING.md`,
`VENDOR_MANAGEMENT_MAPPING.md`.

---

*End of Buy Here Pay Here Operations mapping.*
