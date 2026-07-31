---
title: "Dealer AI Kit — Business Domain Map"
status: authoritative
type: business-reference
generated: 2026-07-31
generated_at_session: SESSION_034
sources:
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/RECON_MAPPING.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
  - docs/research/INDEPENDENT_DEALER_PIVOT.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
supersedes: none
applies_to: All future implementation sessions
---

# Dealer AI Kit — Business Domain Map

> **What this is.** The single highest-level business reference
> for the project. It answers one question:
> **How does an independent used-car dealership actually operate
> from beginning to end?**
>
> **What this is not.** A software design. A data schema. A
> feature list. There are zero endpoints, zero model names, zero
> UI descriptions in this document. It is a description of the
> business the software serves.
>
> **Who this is for.** A new engineer (or new AI session) who
> must understand the dealership before touching the code. Read
> this first, then `docs/CAPABILITY_MATRIX.md` to see what the
> software does today, then the research corpus for depth.
>
> **How this was built.** Synthesized in SESSION_034 from the six
> department mapping docs and the two pivot docs in
> `docs/research/` (research corpus commit `ff0e986`). Every
> claim in this doc traces back to those sources. Nothing new was
> introduced — this is a re-projection of research into a
> cross-department operational view.
>
> **Precedence.** If this doc disagrees with the source mapping
> docs, the mapping docs win — they are the primary research.
> This doc is a synthesis and can drift; the mappings are ground
> truth.

---

## 1. The core reframe — what an indie dealership actually is

An independent used-car dealership is **two interlocking
businesses that share a physical store**:

- **A merchandising business** that acquires vehicles, adds
  value through reconditioning, and sells them to retail
  customers. Its unit of work is the **stock number**. Its
  economics are turn-driven: a vehicle that sits is a vehicle
  losing money.

- **A lending business** — either indirect (F&I arranges
  third-party financing on the customer's behalf) or direct
  (BHPH: the dealer *is* the lender). Its unit of work is the
  **funded deal**. Its economics are risk-adjusted-yield
  driven: every deal booked is exposure that will pay or default
  over the loan's life.

The six departments this doc maps are the operational functions
that keep those two businesses in sync:

- **Inventory & Acquisition** and **Recon** run the
  merchandising side (from acquisition to front-line ready).
- **Sales** is the bridge — it consumes ready inventory,
  qualifies customers, and hands off funded deals.
- **Finance (F&I)** structures the deal, submits to lenders,
  and funds it.
- **BHPH Operations** owns the in-house lending business after
  the deal signs (only present at BHPH-enabled stores).
- **Accounting** is the reconciliation layer — every dollar,
  every title, every payoff, every funding must tie back to a
  documented operational event.

**Ownership**, at indie stores, is not a seventh department —
it is a person who typically owns, buys, appraises, prices,
signs, and closes personally. The owner is present in nearly
every operational flow. This concentration of authority is a
defining feature of the segment.

---

## 2. The vehicle journey (end-to-end)

The vehicle is the primary unit of work on the merchandising
side. Its journey has eleven canonical stages. Not every stage
is a discrete event — some are advisory, some overlap — but every
stage is a real point in operational reality.

| # | Stage | What happens | Primary owner |
|---|-------|---------------|--------------|
| 1 | **Acquisition** | Purchase decision made and executed (auction, trade, wholesale, private party, off-lease/rental, repo, fleet). Cost basis initialized (purchase price + auction fees + transport). Stock number assigned. Floor plan advance drawn (if not cash-bought). Title in transit. | Owner / used-car manager / buyer |
| 2 | **Transport** | Vehicle moved from source (auction lane, remote seller) to dealer lot. Third-party carrier common. | Buyer / logistics |
| 3 | **Intake** | Physical arrival. VIN verified, odometer recorded, condition photographed, damage documented, keys/paperwork accounted for, stock number physically applied, vehicle staged. | Lot manager / porter |
| 4 | **Condition Report** | Systematic inspection across mechanical, cosmetic, body, glass, tires, interior, fluids, electrical, safety, accessories. Findings recorded with severity (advisory / recommended / required / safety). **Human-authored, always.** | Recon manager / tech / inspector |
| 5 | **Recon Planning** | Findings converted to a work plan (must-do / should-do / won't-do). Sequencing planned (mechanical → body → paint → glass → alignment → tires → detail → photography → listing). Vendor selection, cost estimates, parts pre-ordering. | Recon manager |
| 6 | **Recon Execution** | Work dispatched to in-house shop and/or outside vendors. Each job produces a repair order (R.O.) or vendor work order. Discovered work (scope expansion) escalated for re-approval. On completion, actual cost recorded against the vehicle. | Recon manager + techs / vendors |
| 7 | **QC** | Post-recon inspection verifies planned work complete, no new issues, fluids topped, test drive performed. Rework returned to vendor or handled on-the-spot. | Recon manager / senior tech |
| 8 | **Detail** | Interior and exterior detail; interior odor treatment; headlight restoration; wheel/tire cleaning. | Detail crew (in-house or outsourced) |
| 9 | **Photography** | 20–40 photos across exterior, interior, features, engine bay, odometer, VIN, wheels. Edited (crop, straighten, watermark, color). | Photographer (often detail-crew or salesperson) |
| 10 | **Listing** | Description written, price set, listing published across platforms (AutoTrader, Cars.com, CarGurus, Facebook Marketplace, store website, Craigslist). Windshield sticker applied. Vehicle physically moved to retail lot. | Salesperson / office manager / owner |
| 11 | **Front-Line** | Vehicle is retail-available. Every salesperson can show it, every listing platform has it, chat / phone / walk-in inquiries can be matched to it. Ongoing: aging monitoring, competitive scanning, reprice cadence (Day 15 → 30 → 45 → 60 → 90 → 120), potential wholesale-out decision if it doesn't retail. | Sales / used-car manager |

**After front-line, one of two paths:**

- **Retail Sale** (see the customer journey below) — vehicle exits the merchandising cycle at delivery; the customer journey continues.
- **Wholesale Disposition** — aged unit sold dealer-to-dealer, back to auction, or on an online wholesale platform. Recovery-focused, not gross-focused. Frees floor plan capacity; usually near or below cost basis; loss booked to inventory gross.

**Two off-path outcomes** the doc names explicitly:

- **Insurance total loss** if the vehicle is damaged beyond
  economic repair while in dealer possession — cash inflow from
  insurer, title transferred out.
- **Company / owner use** — vehicle reclassified out of retail
  inventory for personal or store use. Removes an
  income-producing unit; carries tax implications.

**Retail eligibility** is a single business rule: a vehicle is
retail-eligible only when it has cleared QC, detail,
photography, and listing — the *frontline* state. Everything
before that is inventory investment being built; everything
after that is inventory the sales team can honestly show.

---

## 3. The customer journey (end-to-end)

The customer is the primary unit of work on the sales and
finance side. The doc names five discrete lifecycle segments,
plus a distinct sixth segment for BHPH customers who continue
as portfolio accounts after the sale.

### 3.1 Prospect

Customer inquiry originates via third-party listing sites
(AutoTrader / Cars.com / CarGurus — 30–45%), Facebook
Marketplace (15–30%), Google Business Profile / organic (10–20%),
repeat / referral (10–25%), walk-in (5–15%), traditional media
(0–10%). A **lead record** is created — source, contact,
inquiry vehicle, timestamp. Response SLA: internet lead within
15 min ideal, 1 hr min; walk-in within 30 seconds; phone
within 3 rings.

### 3.2 Engagement / Qualification

Salesperson builds rapport (non-vehicle conversation first),
then interviews for needs, current vehicle, budget, timeline,
credit story, trade-in. A **customer profile** grows: family
details, job, preferences, concerns, budget, timeline. Deep
notes here become the difference between a repeat relationship
and a one-time transaction.

### 3.3 Presentation / Test Drive

Salesperson selects 1–3 vehicles fitting stated needs from
current front-line inventory (feeding demand signals back to
inventory). Walk-around, story-selling, demonstration drive.
If a trade is present, the used-car manager appraises it
(wholesale value from KBB / MMR / JD Power / auction comps,
minus a recon estimate → allowance offered to customer).

### 3.4 Deal Structuring

Salesperson writes up a **deal** — vehicle price, trade
allowance, cash down, payment target, term preference. At
indies, most customers are payment-first (they work backward
from a monthly payment to a price). The sales manager or owner
may TO ("turn over") on stuck deals. When the customer commits
in principle, sales hands off to F&I with a **handoff memo** —
customer profile, vehicle, trade info + payoff, cash down,
payment target, special promises, red flags.

### 3.5 Finance

F&I owns the deal from handoff to funding.

- **Credit application** captured and signed. Hard bureau pull
  (Equifax / Experian / TransUnion) authorized. FICO band
  assigned (super-prime / prime / near-prime / non-prime /
  subprime / deep-subprime / no-score / BHPH-only).
- **Deal structure** built — LTV, PTI (payment-to-income), DTI
  (debt-to-income), term (24–96 mo), buy rate, sell rate.
- **Lender submission** to one or more of a lender panel
  (targeted vs. waterfall). At an indie serving credit-inclusive
  customers, the panel is prime + near-prime + subprime, and
  many customers land in the bottom half.
- **Approval / counter / decline** received. Stips (income /
  residence / identity / vehicle / trade) chased.
- **Products** presented via menu (VSC, GAP, T&W, maintenance,
  appearance, key, credit insurance). Product acceptance drives
  most of per-deal back-end gross.
- **Contract** signed (RISC + credit app + privacy notice +
  odometer disclosure + Buyer's Guide + product agreements +
  adverse-action notice if declined).
- **Funding packet** assembled and submitted; **funding**
  received (ACH / wire / check).

If the deal is **BHPH** (in-house financed rather than
third-party), the same contract mechanics happen but the
dealership itself is the lender. The customer relationship then
transitions to Section 3.7.

### 3.6 Delivery

Vehicle detailed, fueled, inspected. Owner's manual + second
key handed over. Customer walkthrough of features (Bluetooth
pairing, safety features, infotainment). Warranty explained.
Temp tag issued. Insurance verified. Photo taken (with
permission) for social. Introduction to service department (if
in-house). Deal is now delivered.

### 3.7 Post-Sale

**All customers:**

- **Follow-up cadence** — 24–48 hr check-in, 1 week, 30 days,
  90 days, 6 months, 1 year. Referral request at the right
  moment (usually 30–90 days).
- **Service opportunity** — first oil change often
  complimentary; establishes an ongoing service relationship
  which is itself a repeat-buy channel.
- **Repeat / referral** — repeat customers are the
  highest-margin, lowest-CAC segment. Owner-operated stores at
  20+ years typically have community reputation competitors
  can't quickly replicate.

**BHPH customers (portfolio track — the store is the lender):**

- **Payment cadence** — weekly / biweekly / semi-monthly /
  monthly, matched to customer payday. Payment methods vary
  (cash at office, debit, ACH auto-draft, online, third-party
  intake like PayNearMe / MoneyGram / Western Union).
- **Delinquency management** — a distinct workflow. Day 1–10:
  soft reminder. Day 11–30: escalated contact, PTPs. Day 31–60:
  serious delinquency, repossession consideration. Day 61–90:
  repossession usually ordered. Day 91+: charge-off
  consideration or repo already completed.
- **Skip tracing** if the customer disappears. **GPS device**
  and **starter-interrupt device** (state-permitting) manage
  collateral risk.
- **Repossession → redemption window (10–30 days state-dependent)
  → resale → deficiency / surplus calculation.** Deficiency
  collection is difficult in practice.
- **Repeat-buyer approach** at 6 months from payoff — the doc
  names 30–50% of sales at mature BHPH stores as repeat /
  referral.

### 3.8 Be-Back Management (for un-sold customers)

Customer visited but did not purchase. Scheduled follow-up:
Day 0 (same-day thank-you), Day 1, Day 3 (new inventory), Day 7,
Day 14, Day 30, Day 60, Day 90+. **~20% of unsold customers buy
within a short window**; whether they buy here or elsewhere is
follow-up-determined.

---

## 4. The six departments — identity, rhythm, boundary

### 4.1 Inventory & Acquisition

**Function.** Source, price, hold, and dispose of the store's
inventory. Manage floor plan capacity. Determine what to buy,
at what price, how long to hold, when to reprice, when to
wholesale.

**Core belief the corpus asserts.** *"You make your money when
you buy, not when you sell."*

**Rhythm.** Weekly buying cadence (auctions), continuous
in-lot monitoring, weekly aging review, seasonal buying cycles
(tax-refund season Jan–Feb, softer summer, back-to-school /
winter Sept–Oct).

**Ownership pattern.** At indie stores, the owner is often the
primary buyer. Distinct "buyer" role only at larger stores.

**Boundary.** Owns the vehicle from the moment of acquisition
until sale or wholesale disposition. Owns floor plan lender
relationship. Owns wholesale peer-dealer network.

### 4.2 Recon

**Function.** Transform acquired vehicles from post-acquisition
condition to front-line-ready retail condition. Inspect, plan,
dispatch, coordinate, QC, detail, photograph, sign off.

**Core tension.** *"You can't sell what you don't have, and you
can't have what isn't ready."* Speed vs. quality is the daily
tradeoff — shipping a vehicle unready is worse than any delay
(warranty claim, chargeback, reputation).

**Rhythm.** Per-vehicle project cadence (minimal recon 1–3
days, standard 3–7 days, heavy 7–14 days, major 14+ days).
Continuous vendor status-chasing.

**Ownership pattern.** Recon manager (often the used-car
manager or owner at smaller stores). In-house shop + outside
vendor mix varies by store.

**Boundary.** Owns the vehicle from intake through front-line
sign-off. Owns vendor relationships for mechanical, body,
paint, glass, tires, alignment, upholstery, detail, key
programming. Owns post-sale warranty callback repairs.

### 4.3 Customer Acquisition & Sales

**Function.** The operational bridge. Acquire leads, qualify
customers, present vehicles, negotiate deals, hand off to F&I,
support delivery, drive post-sale relationship.

**Core belief.** Sales exists to help the right customer
purchase the right vehicle in a way that produces both a
profitable transaction and a customer who will return, refer,
and review favorably. A store that closes deals but produces no
repeat customers is running an extraction business, not a
dealership.

**Rhythm.** Same-day response for internet leads; ongoing
follow-up cadence for engaged prospects (10-touch discipline
correlates with 3–5× be-back conversion); weekend traffic
peaks.

**Ownership pattern.** 2–8 salespeople typical. Owner often on
the floor. Sales manager sometimes distinct role. Internet /
BDC role rare at smaller indies. Delivery coordinator sometimes
separate.

**Boundary.** Owns the customer relationship from lead
generation through delivery and post-sale follow-up. Does not
own the deal structure (F&I) or the vehicle condition (recon).

### 4.4 Finance (F&I)

**Function.** Arrange third-party or in-house financing for
retail deals. Sell aftermarket products (VSC, GAP, T&W,
maintenance, appearance, key, credit insurance). Ensure legal
compliance on credit, disclosure, privacy.

**Core belief.** Two questions define the desk: *"Will a lender
approve this customer on this vehicle at terms that work?"* and
*"Can the deal be delivered clean — fundable without callbacks
and without eating a chargeback thirty days later?"*

**Rhythm.** Per-deal project cadence (typically hours to days
from handoff to funded; longer for subprime with stip creep).
Continuous stip-chase management (15–40 open deals in various
stip states at any moment). Monthly reserve reconciliation.

**Ownership pattern.** 1–3 F&I managers per indie store. Owner
often functions as F&I at smallest stores. Sole owner of
customer credit data.

**Boundary.** Owns the deal from sales handoff through funding
completion. Owns lender relationships. Owns product provider
relationships. Owns per-deal compliance record.

**Distinction from BHPH:** F&I structures and funds the deal;
BHPH Operations continues the customer relationship if the
funding lender is the dealership itself. Same signed RISC, but
different downstream owner.

### 4.5 Accounting

**Function.** Reconciliation layer. Every dollar, every title,
every payoff, every funding must tie back to a documented
operational event. Cash management, floor plan reconciliation,
vendor A/P, bank rec, payroll, sales tax filings, monthly
close, financial statement production, year-end tax with
external CPA.

**Core belief.** *"The schedule is off"* is a controller's
daily anxiety. Every subsidiary ledger (inventory, floor plan,
A/R, A/P, contracts-in-transit, warranty receivable, reserve
receivable) must equal its control account. Every mismatch
stops other work until found.

**Rhythm.** Daily (cash receipts, bank feeds, CIT aging, title
arrivals). Weekly (check run — typically Thursday / Friday —
vendor invoice processing, statement reconciliation). Monthly
(close, financial statements, sales tax). Annual (physical
inventory, W-2 / 1099, tax return).

**Ownership pattern.** 1–3 office / accounting staff. Small
stores often one office manager doing everything. Larger stores
have office manager + controller + bookkeeper split. Owner
approves and signs.

**Boundary.** Owns nothing operationally — reconciles
everything. Every other department's activity produces the
records accounting must tie out.

### 4.6 BHPH Operations

**Function.** Manage the in-house lending business after the
BHPH deal signs. Payment intake, reconciliation, delinquency
management, collections, repossession, post-repo disposition,
portfolio monitoring, deficiency / charge-off handling,
repeat-buyer outreach.

**Core belief.** *"You make your money over time, not at the
sale."* A BHPH deal booked today doesn't tell you if it made
money — the customer has to actually pay for that answer to
come back. Success is customer graduation (payoff + repeat +
referral); failure is repo, charge-off, and community reputation
damage.

**Rhythm.** Daily (payment intake, reminder calls, PTP
follow-up, delinquency escalation). Weekly (portfolio review
with owner). Monthly (static-pool analysis, charge-off review,
deferred-gross-profit recognition). Per-loan (24–42 month
lifecycle).

**Ownership pattern.** Office manager / collections manager /
portfolio manager roles. Owner reviews portfolio at least
weekly, often daily. Distinct from F&I; may share staff at
small stores. Third-party repo agents on retainer.

**Boundary.** Owns the customer from BHPH deal funding through
payoff or charge-off. Owns collections practice (FDCPA / TCPA
compliance). Owns GPS / starter-interrupt device management.
Owns repo coordination. Owns portfolio-level reporting to
owner.

**When absent.** At non-BHPH stores this department does not
exist. Presence is a store-shape flag, not a phase.

---

## 5. Shared business entities

Nine business entities connect the six departments. Every
entity is created, consumed, or reconciled by more than one
department. Understanding what each entity *is* — as a business
object, not a database row — is the shortest path to
understanding how the dealership operates.

### 5.1 Vehicle

The unit of merchandising work. Identified by a **stock
number** (assigned at acquisition; unique to the dealer) and a
**VIN** (universal). Everything the store does about that
vehicle — cost basis, condition, work performed, photographs,
listings, sales history, insurance — accumulates against those
two identifiers.

- **Created by:** Inventory & Acquisition (at purchase).
- **Reshaped by:** Recon (condition + work + cost accretion),
  Sales (listing + price changes + hold requests), Accounting
  (cost accumulation, floor plan status), Finance (title +
  lien records at sale).
- **Terminal states:** Sold + delivered → retail exit; wholesaled
  → merchandising exit; total-lossed → insurance exit;
  reclassified to company use → operational exit.
- **Why it matters cross-department:** Every question of "what
  do we have in this piece?" and "what still has to happen
  before it's front-line ready?" is a question about the same
  Vehicle entity, asked from different departmental
  perspectives.

### 5.2 Customer

The unit of relationship work. Identified by contact info
(name + phone + email) and, at credit-app time, by SSN + DOB.

- **Prospect** state: lead capture, needs assessment, appointment,
  test drive. Salesperson-owned.
- **Buyer** state: deal write-up, credit app, contract. F&I and
  sales joint.
- **Delivered** state: has taken possession; follow-up cadence
  begins. Sales-owned.
- **Portfolio account** state (BHPH only): the customer is now
  a debtor. Payment schedule, delinquency status, collection
  contacts, potentially a repo target. BHPH Operations-owned.
- **Repeat / referral source** state: post-payoff or post-warranty
  window; sales-owned again.
- **Why it matters cross-department:** The same person appears
  in Sales' lead system, F&I's credit file, Accounting's cash
  receipts, and BHPH's aging report — as different projections
  of one relationship. Duplicate data entry across those views
  is a documented pain point.

### 5.3 Deal

The commercial event that binds a Customer to a Vehicle in
exchange for money. Identified by stock number + customer +
sale date.

**Deal has phases**, each with its own operational reality:

- **Worked** (sales floor, price / trade / payment being agreed).
- **Committed** (customer says yes in principle, handoff to F&I).
- **Structured** (F&I has built a deal that fits a lender's
  buy-box and a customer's payment tolerance).
- **Approved** (lender has said yes, possibly conditional).
- **Contracted** (RISC signed by customer).
- **Funded** (lender money has hit the dealer's bank).
- **Delivered** (vehicle transferred to customer).
- **Booked** (accounting has posted the deal to the GL).
- **Chargedback** (post-funding reversal: FPD, early payoff,
  product cancellation, repo within window).

A deal can also **unwind** (customer or lender backs out
pre-funding) or **fall through** (approved but never signed) —
vehicle returns to available inventory.

**BHPH deals** have the same phases through Delivered, then
enter the portfolio-account lifecycle in Section 3.7.

**Why it matters cross-department:** Sales, F&I, Accounting,
and (for BHPH deals) BHPH Operations each see the deal at a
different phase and need to agree on its current state.
Chargebacks flowing back through weeks after delivery are the
most-mentioned interdepartmental friction.

### 5.4 Vendor

Any external party the store buys goods or services from
(recon side) or that supports operations (technology, insurance,
professional services). Not the same as a Lender.

Vendor types the corpus names:

- **Recon vendors** — mechanical, body / paint, glass, tires,
  alignment, upholstery, PDR, odor removal, detail, key
  programming, transmission specialists.
- **Parts vendors** — OEM parts counters, aftermarket parts
  stores (NAPA, AutoZone, O'Reilly, Advance), online (RockAuto,
  PartsGeek), salvage yards.
- **Auction vendors** — Manheim, ADESA, regional / specialty
  auctions.
- **Transportation vendors** — carriers moving vehicles from
  auctions or remote sellers to the lot.
- **Payment intake vendors** — debit / ACH processors, online
  portal, PayNearMe / MoneyGram / Western Union.
- **Skip-tracing vendors** — Accurint, TLO, LocatePlus.
- **Repo agents / recovery vendors** — licensed, per-repo fee.
- **GPS / starter-interrupt vendors** — PassTime, Spireon.
- **Photography vendors** — rare at indies (usually in-house).
- **Advertising / listing platforms** — AutoTrader, Cars.com,
  CarGurus, Facebook Marketplace, Craigslist, store website.
- **Professional service vendors** — CPA, payroll processor,
  attorney, IT / DMS provider, insurance broker.

**Cross-department view:** Inventory picks the auction and
carrier. Recon picks the mechanical / body / paint vendor for a
given job. Accounting sets up the vendor master record, matches
the invoice, cuts the check. BHPH engages the payment
processor, skip-tracer, repo agent. Sales engages the listing
platform. The vendor master record and payment terms are
accounting-owned; the operational vendor relationship is
department-owned.

### 5.5 Lender

Any external party that extends credit against a vehicle or a
customer. Distinct from Vendor.

- **Floor plan lender** — advances against inventory (NextGear,
  AFC, Westlake Flooring, Ally, local bank programs). One
  relationship, per-vehicle draws and payoffs. Owner-negotiated.
- **Retail deal lenders** — the deal panel (banks, credit
  unions, prime / near-prime / subprime finance companies —
  Ally, Capital One, Chase Auto, US Bank, Regional / national
  banks; near-prime: GLS, Westlake, Santander, Exeter; subprime:
  Credit Acceptance, ACA, CPS, Prestige, Regional Acceptance,
  United Auto Credit, Skopos, Flagship). F&I-owned relationships
  and program grids.
- **Trade lenders** — whichever bank holds a lien on the
  customer's trade-in. F&I obtains 10-day payoff, Accounting
  sends payoff, waits for title release.
- **The dealership itself as lender (BHPH)** — legally a lender
  when it originates in-house paper. Governed by state usury
  law, TILA / Reg Z, state repo law, GLBA privacy.

**Cross-department view:** Inventory & Acquisition depends on
the floor plan lender for buying capacity. F&I depends on
retail deal lenders to fund deals. Accounting reconciles all
lender activity (advances, curtailments, funding deposits,
payoff variances, reserve statements). BHPH becomes the lender
role internally.

### 5.6 Employee

Every role the corpus names is either a salaried or hourly
staff member, a commissioned salesperson, a family member of
the owner, or the owner. The corpus is explicit that role
concentration at indies is common (owner is buyer + sales
manager + F&I + collections at the smallest stores).

Roles named across the six mappings:

- **Owner / dealer principal** — sets pricing philosophy, approves
  aged-unit calls, signs floor plan agreement, approves
  spot-delivery risk, approves BHPH repossession orders,
  reviews portfolio, handles VIP customers personally.
- **Used-car manager / buyer** — often owner-worn hat; appraises
  trades, prices inventory, approves reprices, coordinates
  recon, makes wholesale-out calls.
- **Recon manager / shop foreman** — dispatches work, coordinates
  vendors, signs off on front-line-ready. Often also used-car
  manager or owner.
- **Service writer** — writes R.O.s; rare at indies without
  in-house shop.
- **Technicians** — mechanical work; ranges from generalist to
  specialist to apprentice.
- **Detail crew** — interior / exterior detail; often lower-wage
  or contract labor.
- **Photographer** — takes listing photos; usually detail-crew
  member or salesperson.
- **Vendor liaison** — informal role; often owner's spouse or
  office manager; chases vendors for status and invoices.
- **Lot manager / porter** — moves vehicles, stages inventory,
  supports the physical lot.
- **Salesperson** — 2–8 typical; commission-heavy comp.
- **Sales manager** — often owner-worn hat; approves pricing,
  does TOs.
- **Internet / BDC** — rare at smaller indies.
- **Delivery coordinator** — preps and explains vehicle at
  delivery; sometimes a distinct role.
- **F&I manager / business manager** — owns credit and deal
  structure work; sometimes also owner-worn.
- **Office manager / controller / bookkeeper** — reconciliation,
  vendor A/P, payroll, close.
- **Collections manager / collector** — BHPH-side collector
  activity.
- **External CPA** — year-end tax + audit + compliance guidance.
- **External payroll processor** — often outsourced.
- **Recovery / repo agent** — third-party licensed vehicle
  recovery, per-repo fee.
- **Attorney** — rarely staffed internally; consulted on repo
  practice, wrongful-repo defense, bankruptcy notices.

**Why it matters cross-department:** Role concentration means a
single employee often participates in three or four
departmental workflows simultaneously. Any system serving this
segment must accept that the same person is the buyer, the
appraiser, the recon dispatcher, and the F&I closer.

### 5.7 Documents

Documents are the durable evidence of every operational event.
The corpus names dozens of document types, grouped by
originating department. The most cross-department documents:

- **Vehicle jacket** — per-stock-number file. Acquisition docs
  (auction settlement, trade appraisal, wholesale invoice,
  bill of sale), title (or title reference), condition report
  at acquisition, all recon invoices and R.O.s, vehicle
  history (Carfax / AutoCheck), photos through the lifecycle,
  known-issue notes, customer communications (holds /
  reservations). Retention 5–7 years post-sale.
- **Deal jacket** — per-deal file. Credit application, bureau
  report, ID, income / residence docs, all stips gathered,
  signed RISC, all amendments / addenda, trade payoff, title
  work, insurance, product agreements, Buyer's Guide, privacy
  notice, adverse-action notice, commission record, chargeback
  record. Retention 2–7 years (federal / state driven).
- **Title** — legal ownership document. Physical paper or
  electronic (ELT). Must be present or clearly-in-transit for a
  vehicle to be legally sold. Chain of title verified on every
  vehicle (signature chain, odometer, brands, liens).
- **Retail Installment Sale Contract (RISC)** — the loan
  document. Signed by customer + co-buyer if any. Federally
  required disclosures (Reg Z / TILA).
- **Condition report** — human-authored inspection artifact.
  Categories, severities, cost estimates, photos of significant
  findings. Foundation of everything downstream in recon.
- **R.O. / work order / vendor invoice** — every recon dollar
  is traced through this chain. Cost accumulates on the
  Vehicle.
- **Payment ledger / payment record / promise-to-pay** —
  BHPH-specific; every customer payment and every promise
  documented.
- **Floor plan schedule + lender statement** — accounting's
  daily reconciliation surface. Per-vehicle balances must sum
  to the lender's outstanding balance.
- **Trial balance + subsidiary ledger + schedule tie-out** —
  accounting's monthly close artifacts.
- **Sales tax return, W-2, 1099-NEC, Form 8300, federal /
  state income tax return** — accounting's compliance filings.

**Why it matters cross-department:** Most documented pain
points cluster at document handoffs (missing titles, mislaid
condition reports, incomplete deal jackets, unmatched vendor
invoices, unapplied cash, stip creep). Documents are the joints
of the operation.

### 5.8 Financial Transactions

Every operational event has a financial dimension. Grouped by
direction:

**Cash inflows:**

- Customer down payments (Sales / F&I → Accounting).
- Lender funding (F&I → Accounting via bank feed).
- Reserve income (F&I → Accounting monthly).
- Product commission income (F&I → Accounting monthly).
- BHPH principal + interest collections (BHPH → Accounting daily).
- Warranty / product provider commission payments (F&I product
  side → Accounting monthly).
- Wholesale disposition proceeds (Inventory → Accounting).
- Insurance total-loss settlements (Inventory → Accounting).
- Trade equity applied (F&I → Accounting).
- Vendor rebates / credits (Accounting).

**Cash outflows:**

- Vehicle acquisition (Inventory → Accounting → seller /
  auction / trade lender).
- Auction fees + transportation (Inventory → Accounting).
- Recon expenses (Recon → Accounting → vendors).
- Vendor payments — weekly check run (Accounting).
- Floor plan payoffs on sold units — 3–7 days post-sale
  (Accounting → floor plan lender).
- Floor plan interest — daily accrual (Accounting).
- Curtailments — at 30 / 60 / 90 / 120 day marks (Accounting
  → floor plan lender).
- Trade payoffs — post-deal signing (Accounting → trade
  lender).
- Sales tax remittance — monthly or quarterly (Accounting →
  state).
- Payroll — weekly or biweekly (Accounting).
- Payroll tax deposits — quarterly federal, monthly state
  (Accounting).
- Repossession costs (BHPH → Accounting → repo agent).
- Owner distributions (Accounting).

**Non-cash accounting entries the corpus names explicitly:**

- Daily floor plan interest accrual.
- Monthly recon-in-process reconciliation.
- Deferred gross profit recognition (BHPH installment-sales
  accounting).
- Chargeback reversals (F&I income reversed).
- Reserve for uncollectible accounts (BHPH portfolio).
- Vehicle cost accumulation per stock number.
- Wholesale-loss journal entry when disposition < cost basis.
- Depreciation on fixed assets (year-end).

**Why it matters cross-department:** The Financial Transactions
entity is the reconciliation lens through which Accounting
sees every other department's work. Any operational event that
does not produce a matching financial transaction is a hole in
the ledger.

### 5.9 Time (implicit ninth entity)

The corpus does not name "Time" as a separate entity, but
every department's decision framework depends on it:

- **Inventory:** days in stock (aging bucket 0-30 / 31-60 /
  61-90 / 91-120 / 121+), reprice cadence tied to age.
- **Recon:** days in recon (aging by stage), vendor turn time,
  ETA promises to sales.
- **Sales:** response SLA on internet leads, follow-up cadence
  (24-hr / 1-wk / 30-day / 90-day / 6-mo / 1-yr), 10-touch
  discipline.
- **Finance:** stip clock (before funding), chargeback windows
  (90-day FPD, 3–5-year pro-rated product refund).
- **Accounting:** monthly close deadline, weekly check run,
  daily bank rec, quarterly tax deposits, annual returns.
- **BHPH:** payment cadence (weekly / biweekly / monthly),
  delinquency bucket (1-10 / 11-30 / 31-60 / 61-90 / 91+),
  redemption window (state 10–30 days), static-pool cohort
  aging.

Every dashboard, alert, and escalation the corpus describes is
some function of time-since-event.

---

## 6. Cross-department information flow

The following table captures the primary flows the mapping docs
name. **From** produces the artifact; **To** consumes it; the
**Trigger** is what makes the handoff happen. This table is not
exhaustive — the six mapping docs together enumerate hundreds
of small flows — but it captures the load-bearing ones.

| From | To | Artifact / decision | Trigger |
|------|----|--------------------|--------|
| Inventory | Recon | Vehicle + acquisition condition report + budget authorization + priority signal | Every acquisition |
| Inventory | Sales | New-arrival heat sheet (photos, features, target retail, "who this fits") | New unit becomes front-line-ready |
| Inventory | Sales | Trade appraisal (ACV, allowance, retail-vs-wholesale recommendation) | Sales desk request at deal write-up |
| Inventory | Finance | Book-out data (KBB / MMR / retail) at deal time | F&I preparing lender submission |
| Inventory | Finance | Vehicle features / trim / mileage / recall status / photos | Deal being structured |
| Inventory | Accounting | Stock number assignment + initial cost recording | Every acquisition |
| Inventory | Accounting | Unit-status change (moved to wholesale, reclassified, etc.) | Any status transition |
| Recon | Inventory | Realistic recon estimate + condition report + ETA + front-line-ready signal | Inspection complete, ongoing status |
| Recon | Sales | Reliable ETA on in-recon units + scope-change communication | Recon plan set; scope changes discovered |
| Recon | Sales | Front-line notification with photos + recon highlights | QC sign-off complete |
| Recon | Accounting | Correctly-coded vendor invoices for approval | Vendor invoice arrival |
| Recon | Finance | Documentation supporting VSC claim defense | VSC claim raised post-sale |
| Sales | Inventory | Customer demand feedback (body class, price point, features asked for) | Aggregate of sales conversations |
| Sales | Inventory | Pricing feedback (units shopped-and-lost, no-interest units, hold requests) | Ongoing customer feedback |
| Sales | Finance | Customer handoff memo (profile, vehicle, trade + payoff, cash down, payment target, promises, red flags) | Customer commits to purchase |
| Sales | Accounting | Delivery checklist + insurance verification + documented commitments | Delivery complete |
| Finance | Sales | Payment quote + approval status + funding status | Deal being structured; status updates |
| Finance | Inventory | Financeability feedback ("this unit doesn't book at subprime") + funded-deal disposition | Ongoing / at funding |
| Finance | Accounting | Deal recap + gross breakdown (VSC / GAP / T&W / reserve / discount / doc fee) + commission inputs + chargeback estimate | Deal signed; ongoing |
| Finance | BHPH Ops | Signed RISC + payment schedule + customer contact info + insurance record + GPS/starter-interrupt disclosure | BHPH deal funds |
| Finance | Customer | Payment quote + product menu + contract + adverse-action notice + privacy notice | Deal process |
| Accounting | Finance | Confirmed funding status + reserve-receivable status + chargeback reversals | Ongoing |
| Accounting | Inventory | Floor plan headroom + per-unit cost accumulation + curtailment obligations | Ongoing; at curtailment dates |
| Accounting | Sales | Commission payment confirmations + chargeback details | Payroll cycle; chargeback events |
| Accounting | Owner | Financial statements + cash flow + aging reports + variance | Monthly close |
| Accounting | BHPH Ops | Portfolio reporting + static-pool analysis + charge-off accounting + deferred-gross recognition | Monthly close |
| BHPH Ops | Accounting | Daily payment posting + charge-off recommendations + repo cost documentation + deficiency / surplus documentation | Daily / per-repo |
| BHPH Ops | Sales | Repeat-buyer leads (customers approaching payoff) | 6 months from payoff |
| BHPH Ops | Inventory | Repo-vehicle return + condition patterns + disposition decision (retail vs wholesale) | Post-repo |
| BHPH Ops | Recon | Notification of repo return + reconditioning requirement | Post-repo inspection |
| BHPH Ops | Owner | Portfolio metrics (delinquency %, static-pool losses, cash flow forecast, top-risk accounts) | Weekly (some daily) |
| Owner | All depts | Buying budget, pricing philosophy, repo policy, hardship judgment on escalated cases, capital allocation | Continuous |

**Two properties this flow map reveals:**

1. **Accounting sits downstream of every other department.**
   Every operational event produces a document Accounting must
   book. When any department bypasses that discipline (a cash
   payment not receipted, an invoice paid directly in
   QuickBooks, an inventory adjustment made outside the DMS),
   the ledger drifts from reality until reconciliation catches
   it.

2. **Sales sits at the funnel of nearly every other
   department.** Inventory produces the vehicles Sales
   promotes. Recon produces the ETA Sales promises. F&I
   produces the deal structure Sales presents. Accounting
   confirms the funding on which Sales commissions depend.
   BHPH produces the repeat-buyer leads Sales reworks. When
   any upstream handoff breaks, Sales is where the customer
   feels it.

---

## 7. Cross-department responsibility flow

Information flowing is different from responsibility flowing.
The corpus makes some responsibility rules explicit:

- **Owner authorizes** major buying decisions, wholesale-out
  calls on aged inventory, spot-delivery risk, BHPH
  repossession orders, borderline warranty coverage, capital
  spending, and any hardship modification above a defined
  threshold. Owner is the escalation target for every "should
  we?" question the doc describes.

- **F&I owns compliance responsibility** for the deal jacket —
  every disclosure filed, every signature captured, every
  retention clock started. Deal-jacket incompleteness is an
  F&I failure even when the missing document is a vendor's or
  a customer's.

- **Recon manager owns the front-line-ready declaration** —
  when the vehicle is signed off, the store is publicly
  committing to its condition. Any post-sale warranty issue
  traceable to skipped-recommended work is a recon
  responsibility.

- **Accounting owns the ledger's truth** — any control-account
  mismatch is Accounting's problem to find, even when the
  source of the mismatch was another department's data-entry
  error.

- **Inventory & Acquisition owns the buy** — cost basis
  discipline, floor plan health, and the aging portfolio are
  inventory's responsibility even when the buyer is the
  owner personally.

- **Sales owns the customer relationship through delivery** —
  every promise made in the sales conversation ("we'll hold
  it till Thursday", "Saturday delivery", "floor mats
  included") is Sales' responsibility to keep, even when
  fulfillment depends on Recon, Detail, or F&I.

- **BHPH Operations owns the portfolio customer post-funding** —
  every collection contact, every hardship judgment, every repo
  decision, every state-law-compliance choice is BHPH's.

Responsibility handoffs are **fewer and later** than information
handoffs. Information flows constantly; responsibility flows at
distinct events (acquisition → recon; recon → sales; sales →
F&I; F&I → BHPH or F&I → delivered).

---

## 8. Critical operational touchpoints (where the seams strain)

The mapping docs, taken together, cluster documented pain
around a small number of specific interdepartmental handoffs.
These are the operational joints that most often crack:

1. **Acquisition → Recon: cost estimate accuracy.** Buyer's
   pre-purchase recon estimate versus actual recon spend.
   Under-estimates compress gross; over-estimates cause
   walkaways from good buys. Named in Inventory and Recon docs.

2. **Recon → Sales: ETA reliability.** "Ready Friday" often
   becomes "ready next Wednesday." Sales promised Saturday
   delivery on the assumption. Chain of broken promises.
   Named in all three of Recon, Sales, and Inventory docs.

3. **Sales → F&I: handoff completeness.** Customer profile,
   payment target, trade info, red flags. Skipped fields
   become stipulations become funding delays. Named in Sales
   and Finance docs.

4. **F&I → Lender → F&I: stip creep.** Approval with stip list
   A → stips gathered → resubmission → lender now wants stip
   list B. Legitimate sometimes, aggravating always. Named in
   Finance and Accounting docs.

5. **F&I → Accounting: chargeback reconciliation.** Deal
   funded three weeks ago; first payment defaulted; commission
   must be reversed; Sales notified; F&I posts adjustment.
   Multi-week friction cycle.

6. **All depts → Accounting: DMS bypass.** Any transaction
   entered outside the DMS (cash payment without a DMS
   receipt, invoice posted directly in QuickBooks, inventory
   adjusted outside the system) creates a control-account
   mismatch that Accounting must find and reverse.

7. **BHPH → Recon: repo return processing.** Vehicle returns
   in worse condition than typical trade-in. Recon costs
   often higher than initial-acquisition recon. Disposition
   decision (retail with recon vs. wholesale) has cash-flow
   and portfolio-loss implications.

8. **Inventory → Accounting: title arrival.** Vehicle bought
   three weeks ago, title hasn't arrived. Unit unsellable.
   $15,000 of dead capital. Chase auction repeatedly.

9. **Sales → Sales: cross-shift lead coverage.** Salesperson
   works today, off tomorrow; their leads' follow-ups fall
   through the cracks in the coverage plan.

10. **BHPH → Customer: hardship judgment.** Real hardship
    vs. excuse. Wrong answer costs either portfolio losses
    (accepting excuses) or customer relationships (dismissing
    real hardship). Named as the single most fatiguing
    judgment in BHPH ops.

These are the places the software either helps most or breaks
most, depending on how it's built. Any implementation work
should be evaluated against how much it strengthens or ignores
these joints.

---

## 9. Financial flow overview

Money moves through the operation in three intertwined
lifecycles:

### 9.1 The inventory dollar cycle

```
Acquisition (cash out) → Floor plan advance (offsetting inflow)
  → Recon spend (cash out per vendor invoice)
  → Daily floor plan interest (small, continuous cash out)
  → Curtailments at 60/90/120 days (cash out to lender)
  → Sale (customer down + lender funding = large inflow)
  → Floor plan payoff (cash out within 3–7 days)
  → Net = gross recovered − aging cost
```

Skilled operators optimize this cycle by turning inventory
quickly (8×/yr baseline, 12×/yr elite) because every extra
day is floor plan interest + depreciation + occupied capital.

### 9.2 The deal-per-copy cycle (F&I)

```
Deal signed → funding packet assembled → lender funds
  → Products commissioned (VSC/GAP/T&W/etc.)
  → Reserve booked (prime: dealer earns; subprime: dealer discounts)
  → Chargeback window opens (90-day FPD; 3–5-year pro-rated products)
  → Any chargeback = commission clawback + gross reversal
```

Target per-copy gross at indie: **~$1,200** (VSC ~$400, GAP
~$250, T&W ~$150, net reserve ~$200, doc fee ~$200).

### 9.3 The portfolio cycle (BHPH only)

```
Deal signed → down payment collected → dealer extends ~$8,000 in credit
  → First weekly/biweekly/monthly payment cycle begins
  → Ongoing: principal + interest inflow, offset by delinquency and charge-off
  → Static-pool losses typically 15–30% over portfolio life
  → Portfolio yield realized over 24–42 months
  → Repeat-buyer conversion at payoff (30–50% at mature stores)
```

BHPH's cash-position math is defining: at deal signing the
store is *underwater* on that unit (paid $6k vehicle + $1k
recon, received $1.5k down + $450 first month = $5k+ negative
in Month 1) and only breaks even months later. Capital
requirements are the primary constraint on BHPH growth.

**Accounting's job** is to keep all three cycles reconciled to
the general ledger and to produce the aging + cash-flow reports
that let the owner see where each cycle is trending.

---

## 10. Where documented pain concentrates

Reading the six mapping docs together, the corpus's pain is not
evenly distributed. It concentrates in these categories:

- **Manual data re-entry** across departments (customer info,
  vehicle info, deal info, cost info) is the single most-cited
  pain — appears in all six mappings.
- **Cross-platform maintenance** for listings (4–6 platforms,
  each with different rules and sync gaps) is named in
  Inventory and Sales.
- **Status-chasing** (chasing vendors for ETAs, chasing lenders
  for funding, chasing customers for stips or payments) is
  named in Recon, Finance, Accounting, and BHPH.
- **Reconciliation friction** (schedule mismatches, vendor
  statement differences, unapplied cash, unmatched titles) is
  the dominant Accounting pain.
- **Judgment under time pressure** (bid or walk, accept the
  trade or not, spot-deliver or not, repo now or later,
  hardship-real or excuse) is named across Inventory,
  Finance, and BHPH.
- **Communication gaps** (new-arrival not announced to sales,
  scope-change not surfaced, chargeback not routed back) is
  named in every mapping.
- **Compliance drag** (federal disclosures, state repo law,
  privacy, retention, tax reporting) is heaviest in Finance,
  Accounting, and BHPH.

Any implementation priority should trace back to at least one
of these documented pain categories. If a proposed piece of
work does not, it is not being driven by operational reality
(see project rule: *Build Around Operational Problems*).

---

## 11. Anchors that win on conflict

If this doc disagrees with any of the underlying sources:

1. `docs/research/*_MAPPING.md` — the six primary research
   docs. Ground truth.
2. `docs/research/*_PIVOT.md` — architectural / scoping plans
   built on top of the research.
3. `docs/PROJECT_RULES.md` — the governance layer telling any
   subsequent session how to use this doc.
4. `docs/CAPABILITY_MATRIX.md` — the verified snapshot of what
   the software actually does today. This doc describes the
   *business*; the capability matrix describes the
   *software*.

Narrative synthesis (this doc) is a claim. Research docs and
runtime code are facts.

---

## 12. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/CAPABILITY_MATRIX.md` — verified capability snapshot.
- `docs/IMPLEMENTATION_ROADMAP.md` — prioritized milestones
  built on this domain map (produced same session).
- `docs/PROJECT_PIPELINE.md` — request-flow map of what the
  software does today.
- `docs/DEALER_KIT_BEHAVIOR_LAYER.md` — voice / tone / constraint
  contract for AI output.
- `docs/DEALER_KIT_TRANSLATION_LAYER.md` — per-audience
  translation contract.
- `docs/research/` — the six mapping docs + two pivots that
  are the primary source of business truth.
- `docs/handoffs/SESSION_034_*.md` — this session's handoff.

---

*End of Business Domain Map.*
