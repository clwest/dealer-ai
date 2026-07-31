---
title: "Finance Department (F&I) — Operational Mapping"
status: reference
type: research
generated: 2026-07-31
scope: Independent used-car dealership Finance & Insurance operations
voice: Experienced F&I manager / dealership owner
companion_docs:
  - "VEHICLE_CENTRIC_PIVOT.md"
  - "INDEPENDENT_DEALER_PIVOT.md"
authoritative_for:
  - How F&I actually operates on the floor of an independent used-car dealership today
not_authoritative_for:
  - Franchise / OEM captive finance program specifics (mentioned only for contrast)
  - Legal advice
  - Specific lender program grids (those change; use current lender reps as source of truth)
  - Any implementation design
---

# Finance Department (F&I) — Operational Mapping

> **What this is.** A research artifact documenting how the Finance
> & Insurance (F&I) department of an independent used-car dealership
> actually operates today. Written from the perspective of an
> experienced F&I manager who has run desk at both franchise and
> independent stores.
>
> **Who this is for.** Anyone (engineer, agent, product person)
> touching Finance-related work in the Dealer AI Kit. This document
> is meant to be read *before* any Finance-related implementation
> begins, so that decisions are grounded in how the department
> actually works rather than in how software people imagine it
> works.
>
> **What this is NOT.** Not a training manual (won't make you an F&I
> manager). Not legal advice (compliance section is awareness only).
> Not an implementation plan (see the pivot docs for that). Not a
> catalog of specific lender programs (those change monthly; ask a
> lender rep for current grids).
>
> **Reading order.** Sections 1–8 describe the business. Section 9
> (Automation Opportunities) is where technology enters the
> conversation, and only in the form of "where the repetitive work
> lives." Section 10 documents dependencies on other departments
> (which will get their own research docs). Section 11 catches
> ideas that belong in other departments' future research.

---

## Purpose & scope

The Dealer AI Kit's vehicle-centric pivot (`VEHICLE_CENTRIC_PIVOT.md`)
proposes treating every stock number as a living operational record.
Finance is one of the departments that touches that record most
heavily — from the moment a customer sits at the desk to the moment
the deal funds and the vehicle is delivered.

Before any Finance-related architecture is designed, we need to
preserve the operational knowledge of what F&I actually does day to
day. This document is that preservation.

**Scope boundary:** this document describes the *independent
used-car dealer* F&I motion. That means:

- Mixed-make used inventory, no OEM captive relationship.
- Credit spectrum ranging from prime walk-ins to subprime and
  in-house (BHPH) buyers.
- Small to mid-sized store operation — one to three F&I managers,
  not a 20-person department.
- Deal sizes typically $4,000 to $30,000, occasionally higher.
- No OEM lease residual programs, no OEM incentive stacking.

Where franchise practice differs meaningfully, this document notes
the contrast briefly. It does not attempt to fully document
franchise F&I; that would be a separate research effort.

---

## Voice & caveats

The voice throughout is that of an experienced operator, not a
consultant. Terms are used the way they are actually spoken on the
sales floor. Where a formal term exists, both the formal name and
the operator shorthand are given.

**Numeric caveats.** Any specific numbers in this document — FICO
ranges, LTV caps, PTI ceilings, term limits, product cost ranges —
are *illustrative of typical practice*. Real lender programs vary
by lender, tier, market, vehicle class, and month. Any
implementation must source current numbers from lender reps,
program grids, or (better) machine-readable lender feeds. Treat
this document as a map of *what variables matter and how they
interact*, not as a rate sheet.

**Compliance caveats.** The compliance section is awareness-level
only. A dealer's compliance program must be built with an actual
compliance professional, not with this document. Nothing here is
legal advice.

---

## 1. The Customer Credit Process

The credit process is the first thing that happens after a customer
decides they want a specific vehicle (or, occasionally, before —
some customers get pre-qualified before they shop). The goal of the
process is to answer two questions:

1. **Will a lender approve this customer on this vehicle at terms
   that work for the customer and the store?**
2. **Can the deal be delivered clean — meaning fundable without
   the customer needing to come back for stipulations, and without
   the store eating a chargeback thirty days later?**

Every step in the process serves one of those two questions.

### 1.1 The credit application

The credit application ("credit app," "app") is a written or
electronic form on which the customer authorizes the dealer to
pull their credit and submit their information to lenders. It
captures:

- Personal identity (full legal name, SSN, DOB, driver's license
  number and state).
- Residence (current address, time at address, housing type — rent
  or own, monthly housing payment).
- Prior address if under two years at current.
- Employment (current employer, position, time on job, gross
  monthly income, employer phone).
- Prior employment if under two years at current.
- References (personal references — typically five or six, name
  address phone relationship — required by most subprime lenders,
  optional for prime).
- Trade information if applicable (year/make/model/mileage, VIN,
  payoff amount and lender).
- Signature and authorization language (usually acknowledging the
  credit pull, the sharing of information with lenders, and
  privacy policy).

**Formats.** Three common formats:

- **Paper app on a clipboard** — still used, especially with older
  customers, walk-ins, and stores that haven't gone digital.
- **In-store tablet or terminal** — customer types the app on a
  dealer-owned device.
- **Online pre-qualification form** — customer fills it out on
  their phone before or during the visit (many indie sites have
  this, tied to a DR/lead system).

Regardless of format, the application data ends up captured into
whatever software the store uses to actually submit deals (Route
One, Dealertrack, a CRM/DMS module, or in some smaller stores a
plain spreadsheet + manual portal entry).

**Joint vs single applications.** If there's a co-buyer, both
applicants sign, both SSNs are captured, both credit files get
pulled. A joint app is different from two single apps — a joint
app declares intent to be jointly liable and permits combining
incomes for ratio calculations.

**Operator note.** Getting the app filled out completely and
accurately on the first pass saves hours downstream. Every field
skipped ("I'll fill that in later") is a field that becomes a
stipulation, a phone call, or a delivery delay.

### 1.2 Identity verification

The store must verify that the person signing the app is who they
claim to be. This is both a compliance requirement (Red Flags Rule,
OFAC) and a fraud-prevention practice.

Standard steps:

- **Photocopy or scan of a government-issued photo ID** —
  typically driver's license, occasionally state ID or passport.
  Physical inspection to compare the photo to the customer and to
  spot obvious tampering.
- **SSN validation** — the credit bureau's response will flag
  obvious inconsistencies (SSN issued to someone deceased, SSN in
  a range that hadn't been issued at the customer's claimed DOB,
  SSN associated with a different name).
- **Address consistency** — the address on the app should match
  what the bureau shows. Discrepancies get investigated. New
  addresses (customer just moved) are common and legitimate but
  need proof of residence (see §1.4).
- **OFAC screening** — the customer's name is checked against the
  Office of Foreign Assets Control's Specially Designated
  Nationals (SDN) list. Most credit bureau responses include this
  check automatically. It rarely hits, but when it does it stops
  the deal cold.
- **Red Flags** — the store's identity theft prevention program
  (required by the FCRA) defines what "red flags" (indicators of
  possible ID theft) look like and how the store responds. Common
  red flags: SSN doesn't match name, address on ID doesn't match
  app, customer can't explain a name change, customer reluctant
  to show ID.

### 1.3 Employment verification

Lenders need to know the customer has income they can rely on to
make the monthly payment. Employment verification confirms:

- **Employer exists** and is currently operating.
- **Customer works there** in the role claimed.
- **Income is what the customer stated** (or close to it).
- **Time on job** meets the lender's minimum (often 30-90 days
  for prime, 6-12 months for subprime).

Common verification methods:

- **Recent paystubs** — usually two most recent, or 30 days
  worth, showing YTD gross. The gold standard.
- **VOE call (Verification of Employment)** — the store or lender
  calls the employer's HR line to confirm employment and income.
  Some employers use third-party services (The Work Number is the
  most common) that lenders can query electronically.
- **W-2 or tax return** — used when the customer is between jobs
  or when paystubs aren't available. Also used for
  self-employed customers.
- **Bank statements** — sometimes accepted as secondary income
  proof (regular deposits from employer matching stated pay).

**Self-employment.** A perennial complication. Self-employed
customers rarely have paystubs. They provide 1–2 years of tax
returns (Schedule C or K-1 for LLCs), 3–6 months of business bank
statements, or a CPA letter. Subprime lenders often cap or
discount self-employment income because it's harder to verify and
more volatile.

**1099 contractors** land in the same bucket as self-employed for
most lenders' purposes.

**Fixed-income customers** (retirees, disability, SSA, VA benefits,
pension). Award letters and bank statements substitute for
paystubs. Most lenders accept these but may have different DTI
treatment.

**Operator note.** Stated income above what a paystub confirms is
a common friction point. If the customer says they make $5,000 a
month but the paystub shows $3,200, the deal has to be resubmitted
at $3,200 or the customer has to bring documentation for the
missing $1,800 (tips, side job, spousal income if joint app).

### 1.4 Residence verification

Confirming where the customer actually lives, both for
identity/fraud purposes and because lenders want to know they can
find the customer if payments stop.

Common methods:

- **Utility bill** in the customer's name at the current address,
  dated within 60 days. Gas, electric, water, cable — not cell
  phone (cell bills can go anywhere).
- **Recent lease agreement** if renting.
- **Mortgage statement** if owning.
- **Driver's license address** if it matches.
- **Bank statement or credit card statement** to the address.

**Time at address** matters as much as verification. Two years or
more at current address is preferred. Less than that, the
customer is asked for prior address, and sometimes prior utility
bills or lease.

**Housing payment** is captured to feed DTI calculations (see
§3.6). Renters pay rent; homeowners have mortgage + taxes +
insurance ("PITI"); "lives with parents / relatives" is a common
subprime category with typically zero declared housing payment.

### 1.5 Income verification

Income verification overlaps with employment verification (§1.3)
but focuses on the *number* rather than the *employer*. All
income the customer claims — whether from a job, self-employment,
benefits, alimony, or child support received — has to be
documented if the lender is going to use it in ratio math.

Formal categories most lenders recognize:

- **Wage income** — paystubs, W-2, VOE.
- **Self-employment income** — 1040 with Schedules C/SE, business
  bank statements.
- **Retirement income** — SSA award letter, pension statement,
  1099-R.
- **Disability income** — SSA disability award letter, VA
  disability letter, private LTD policy.
- **Rental income** — Schedule E from tax return, lease
  agreements. Often haircut by 25% for vacancy allowance.
- **Alimony / child support received** — court order + evidence
  of receipt (bank deposits, ledger from state disbursement
  agency). Federal ECOA rules mean the customer *doesn't have to*
  disclose it, but if they do, the lender must consider it.
- **Investment / dividend income** — 1099-DIV, brokerage
  statements.

Any of these can be a customer's *primary* income depending on the
customer. An F&I manager sees the full spectrum in a typical week.

**Verification vs stated income.** For prime deals, "stated income"
(income declared without documentation) is sometimes accepted at
certain FICO thresholds. Deep subprime almost always requires
verified income — the lender has too much loss exposure to trust
customer statements.

### 1.6 Trade information

If the customer is trading in a vehicle, the trade becomes part of
the deal math and part of the deal jacket.

Captured on the credit app or a separate trade appraisal form:

- Year, make, model, trim, mileage.
- VIN (drives book-out; see §3.2).
- Condition (running, drivable, damage disclosure).
- **Payoff information** — the amount currently owed and to whom
  (lender name, account number, payoff phone number).
- Second lien if any (rare but happens with cash-out refis).
- Title status — customer has title in hand, or lender holds it,
  or it's a lost-title situation.

**Payoff quote.** The store calls the payoff lender (or requests
via an electronic payoff system) to get a **10-day payoff quote**
— the exact dollar amount required to pay off the loan on a
specific date. Payoffs decrease slightly each day (as interest
accrues on the remaining principal but pay-down happens too).
Getting the quote in writing is critical because that's what the
new lender is going to fund, and if the actual payoff differs
from the quote by even $50 the store may have to eat the
difference or chase the customer.

**Trade equity vs negative equity.**
- **Equity:** trade appraisal value > payoff. The excess counts as
  a down payment.
- **Negative equity ("upside down"):** payoff > trade value. The
  gap has to go somewhere — usually rolled into the new loan
  (which pushes the new loan LTV up and can make it unfundable),
  paid by the customer in cash at signing, or absorbed by the
  store as a discount on the new vehicle.

**Trade appraisal.** The store determines what to actually offer
for the trade. This is normally done by a used-car manager or
buyer, not F&I. F&I inherits whatever the appraisal is. See §10.1
on inventory dependencies.

### 1.7 Down payment

Down payment is any money the customer contributes toward the
vehicle at or before delivery that reduces the amount financed.

Sources:

- **Cash** — the customer's own money. Most common.
- **Trade equity** — see §1.6.
- **Deferred down ("split down")** — customer pays part now, part
  in 15–30 days after delivery. Lender acceptance varies; some
  won't allow it, some will up to a limit, some require the
  deferred portion to be a post-dated check or ACH. Deferred down
  is a chargeback risk (see §5.7).
- **Rebates and incentives** — much less relevant on used
  independent deals than on new franchise deals. Occasionally an
  aftermarket product rebate applies.
- **Refund promises** ("I'll pay you when my tax return comes in")
  — the store may or may not accept these. Some do informally and
  eat the risk; formal deferred down requires paperwork.

**Down payment percentage.** Different tiers require different
minimums. Prime deals often go with zero down. Deep subprime
lenders may require 10%–20% of the sale price, or a fixed dollar
minimum ($500, $1,000, $2,000), or 20% cash down PLUS trade
equity. BHPH portfolios typically demand 20% cash down as a
minimum with no waiver.

**Operator note.** More down = better deal for everyone. Lower
LTV = higher approval odds, lower rate, more room in the deal for
products, and lower chargeback risk. When the desk is fighting to
get a deal bought, the first lever is usually more down.

### 1.8 Co-buyers

A co-buyer (co-applicant) is a second person who signs the
contract and is jointly liable for the debt. A co-buyer's income
and credit combine with the primary applicant's for ratio and
approval decisions.

**When to add a co-buyer:**
- Primary applicant's income doesn't hit PTI/DTI ceilings but the
  household income does.
- Primary applicant's credit is thin or damaged; co-buyer has a
  stronger file.
- Primary applicant is a young buyer with no credit; parent or
  older relative cosigns.

**When NOT to add a co-buyer:**
- If the co-buyer's credit is *worse* than the primary's, adding
  them can hurt the deal (lenders often price to the lowest
  score, not the highest).
- If the relationship is unclear or the co-buyer is reluctant.
  Reluctant co-buyers become disputed accounts later.
- If it triggers additional stipulations that make the deal
  harder to close.

**Cosigner vs co-buyer.** Some lenders distinguish between them
(cosigner is liable but not on title; co-buyer is on title). Others
treat them identically. Practice varies.

**Common relationships:** spouse, parent, adult child, sibling.
Occasional non-relative (partner, friend) — most lenders permit
but a few require a family relationship.

### 1.9 Stipulations

A "stip" is anything the lender requires *in addition to* the
signed contract before they will fund the deal. Stips are the
number-one cause of funding delays and F&I frustration.

Common stip categories:

- **Proof of income** — additional paystubs, VOE, tax return.
- **Proof of residence** — utility bill matching current address.
- **References** — the lender may want to call references before
  funding.
- **Insurance** — proof of full-coverage insurance with the
  lender listed as loss payee (see §5.4).
- **Photo of vehicle** — some subprime and BHPH lenders require
  a photo of the actual vehicle, sometimes with the odometer
  visible.
- **Odometer statement** — separate federal disclosure required
  on any transfer, has its own form.
- **Buyer's Guide (FTC "Used Car Rule")** — must be posted on the
  vehicle window at time of sale and provided to buyer.
- **Copy of driver's license** — front and back, sometimes with
  address updated.
- **Trade payoff verification** — the 10-day quote plus title work.
- **Deal recap / re-signed docs** — if any contract terms changed
  during structuring, the lender may want the re-signed contract
  before funding.
- **CPI (Collateral Protection Insurance) disclosure** —
  applicable on some subprime lenders where the lender may
  force-place insurance if the customer lets theirs lapse.

Stipulations are lender-specific. What one lender requires
another may skip. Managing stips means knowing which stips each
lender attaches to which tiers and which vehicle classes.

**Stip creep** is a common frustration: the lender approves the
deal with stip list A, the store gathers everything on list A,
resubmits the funding packet, and the lender now wants stip list
B (something new they didn't ask for the first time). Legitimate
sometimes, aggravating always.

### 1.10 Bureau pulls

A bureau pull is a request for the customer's credit report from
one or more of the three major credit reporting agencies (Equifax,
Experian, TransUnion). Each pull comes with a "score" (typically
FICO Auto Score 8 or 9, or occasionally VantageScore) and a full
tradeline history.

**Permissible purpose** (FCRA). The dealer may only pull a bureau
when there is a permissible purpose. In auto sales, the two most
common permissible purposes are:

- **Written authorization** — the customer signed the credit app
  authorizing the pull.
- **Legitimate business need in connection with a credit
  transaction** — the customer is actively negotiating a deal.

Pulling without permissible purpose is a serious violation.
Bureaus audit dealer pull patterns. A dealer pulling everyone who
walks on the lot gets flagged.

**Hard vs soft pulls.**
- **Hard pull** — visible on the customer's credit report, may
  slightly reduce their score, counted by other lenders as an
  inquiry.
- **Soft pull** — invisible to other lenders, does not affect
  score. Used for pre-qualification.

Most in-store deal submissions are hard pulls. Pre-qualification
tools are soft pulls (the customer sees "no impact on your
credit"). The transition from soft-pull pre-qual to hard-pull
submission is a well-established practice.

**Single-bureau vs multi-bureau pulls.** Some lenders want a
single bureau (their preferred one). Others want all three (a
"tri-merge"). Some pull their own; others require the dealer to
submit a report already pulled. Cost varies from a few dollars per
pull (dealer-negotiated bureau contract) to substantial monthly
minimums.

**Inquiry timing.** Multiple auto-loan inquiries within a 14-day
(or sometimes 45-day, depending on the scoring model) window are
usually treated as a single inquiry for FICO scoring purposes.
This is the "rate shopping window" designed to let consumers
shop lenders without penalty. It is *not* an unlimited window —
sending the same deal to fifteen lenders across two weeks still
looks shopped and hurts approval odds, even if the FICO score
doesn't drop.

### 1.11 Privacy requirements

Federal law (Gramm-Leach-Bliley Act, or GLBA) treats dealer credit
information as regulated financial data. Key requirements at the
credit-app stage:

- **Privacy notice** — customer must receive a privacy notice
  describing what non-public personal information the dealer
  collects, how it's used, with whom it's shared, and how the
  customer can opt out of certain sharing. Usually a one-page
  form signed with the credit app.
- **Safeguards** — the customer's SSN, DOB, income, and other
  sensitive fields must be protected from unauthorized access
  (see §6.4 for the full Safeguards Rule).
- **Disposal** — when the paper app is no longer needed, it must
  be shredded (Disposal Rule under FACTA).

Any digital handling of credit-app data is subject to the
Safeguards Rule (updated 2021, took effect 2023): the dealer must
have a written information security program, designated qualified
individual, encrypted storage of sensitive data, multi-factor
auth for systems accessing it, and incident response procedures.

**Operator note.** The paper app that a walk-in customer fills out
at the desk is *the most sensitive document in the building*. SSN,
DOB, address, employer, income — everything an identity thief
needs. Every store should have a locking cabinet for filled apps
awaiting entry, a shredder for disposal, and a written policy
about who sees what.

### 1.12 A representative flow

Putting §1.1 through §1.11 together, a typical deal flow through
the credit process looks like this:

1. Customer picks a vehicle. Sales manager brings the customer to
   the F&I desk (or the F&I manager goes to sales).
2. F&I hands the customer the credit app (paper, tablet, or
   pre-filled from the online form).
3. Customer completes the app with F&I's help. Photo ID copied.
4. F&I inputs the app into whatever deal submission system the
   store uses.
5. F&I runs the customer's credit (one pull, feeding tri-merge, or
   whichever bureau the primary lender wants). Score, tradelines,
   and bureau flags come back within seconds.
6. F&I reviews the credit report and immediately forms a mental
   tier assessment (see §2.1 tiering).
7. F&I selects the first lender to submit to based on tier,
   vehicle, LTV, and store policy.
8. F&I structures the deal (see §3) — vehicle price, cash down,
   trade, term, rate goal — and submits.
9. Lender responds within minutes (electronic) or up to an hour
   (manual review). Response is approval, conditional approval,
   counter-offer, or decline.
10. F&I reviews the response with the desk / sales manager, works
    the deal (may resubmit with more down, different term, or
    different lender), presents to the customer with product menu,
    signs contracts, gathers stips.
11. Deal moves to funding (see §5).

Elapsed time from step 1 to signed contract: 30 minutes on a
clean prime deal, 3+ hours on a challenging subprime deal, sometimes
several days if the customer has to return with docs.

---

## 2. Lender Relationships

### 2.1 The lender tiering landscape

Lenders are not interchangeable. They compete for different slices
of the customer credit spectrum, and knowing which lender wants
which kind of deal is a huge part of F&I skill.

The credit spectrum is commonly divided into tiers:

| Tier | FICO Auto Score range (typical) | Character of customer |
| --- | --- | --- |
| **Super prime** | 780+ | Long clean history, low utilization, homeowner, high income. |
| **Prime** | 700–779 | Solid history, minor blemishes at worst. |
| **Near-prime** | 660–699 | Some recent late payments, high utilization, or thin file. |
| **Non-prime** | 620–659 | Bankruptcy 4+ years back, some charge-offs, higher utilization. |
| **Subprime** | 550–619 | Multiple derogatory accounts, recent bankruptcy, thin employment. |
| **Deep subprime** | Below 550 | Recent bankruptcy, active collections, judgments, first-time borrower with no cushion. |
| **No-score** | N/A | Insufficient credit history for a score to be calculated. |
| **BHPH bucket** | Wherever nobody else buys | The customer nobody outside financed. |

These ranges are illustrative. Every lender defines tiers
differently and moves the cutoffs based on their portfolio
performance.

Independent used-car dealers see the *entire* spectrum, weighted
toward the bottom half. A typical indie store might do 5% super
prime, 20% prime, 25% near-prime, 30% non-prime + subprime, 15%
deep subprime, 5% BHPH. A pure-BHPH lot is 100% BHPH.

### 2.2 Prime lenders

Prime lenders want the best customers on the best vehicles at the
lowest rates. They compete on rate, term flexibility, and speed of
approval. Examples of common prime auto lenders (illustrative, not
endorsement): Ally, Capital One, Chase Auto, US Bank, PNC, Wells
Fargo (via dealer network), regional banks, national credit unions
(PenFed, Navy Federal for indirect programs), local credit unions.

Characteristics:

- **Rates:** lowest available. Typical range depends on Fed rate
  environment and market, but prime rates are generally the
  floor for a given vehicle age.
- **Terms:** flexible, often out to 84 months on new-ish used.
- **Advance:** high LTV, often 130%–140% of book on strong
  customers (allowing product loading).
- **Stips:** minimal for clean prime deals. Sometimes stated
  income up to certain thresholds.
- **Vehicle restrictions:** age and mileage caps (often 10 years
  / 100k miles for used, less generous for higher tiers).
- **Speed:** electronic approvals in seconds via Route One /
  Dealertrack.

**Indie access to prime.** Not every prime lender works with
every indie store. Prime lenders often prefer larger volume
dealers and franchise stores. Some prime lenders only take
indirect deals through certain aggregators. Smaller indies may
have to route prime customers through a credit union or a
regional bank with which they have a relationship.

### 2.3 Near-prime lenders

Near-prime lenders occupy the space between prime and true
subprime. They price for slightly elevated risk and are often the
"first stop" for indie stores because most indie customers land
somewhere here.

Examples (illustrative): Ally near-prime programs, Global Lending
Services (GLS), Westlake Financial's tier programs, Santander,
Exeter Finance's higher tiers, some captive-adjacent programs.

Characteristics:

- **Rates:** meaningfully higher than prime.
- **Terms:** typically capped shorter than prime (often 60–72 months).
- **Advance:** more conservative LTV, often book +10% to +25% for
  a decent tier customer.
- **Stips:** paystub or VOE typically required, POR sometimes,
  references sometimes.
- **Vehicle restrictions:** age and mileage caps (often 8–10 years
  / 100k–125k miles).

Near-prime lenders are competitive with each other. F&I managers
often keep two or three in the near-prime bucket and pick based on
vehicle fit, current program pricing, and rep relationship.

### 2.4 Subprime lenders

Subprime lenders serve customers whose credit is materially
impaired. They accept higher default risk in exchange for higher
rates and stricter deal structures.

Examples (illustrative): Credit Acceptance, American Credit
Acceptance (ACA), Consumer Portfolio Services (CPS), Prestige
Financial, Regional Acceptance, Sheffield (for RV/marine, not
autos generally), United Auto Credit, Skopos, Flagship Credit
Acceptance.

Characteristics:

- **Rates:** high — often at or near state usury caps (24%–29%
  APR in many states, higher where legal). Rates are typically
  a function of tier + LTV + vehicle age.
- **Terms:** capped shorter (48–72 months typical).
- **Advance:** conservative to strict. Often book value
  ("clean trade" or "average trade") + limited product allowance.
- **Stips:** extensive. Paystubs, POR, references, insurance,
  phone verification, sometimes photos of vehicle.
- **Vehicle restrictions:** older vehicles allowed but with
  reduced advance. Higher mileage vehicles limited or excluded.
  Salvage / branded titles usually excluded.
- **Discount fees ("points" or "acquisition fees"):** the lender
  buys the paper from the dealer at a discount, meaning the
  dealer receives less than the amount financed. Discount ranges
  from 3% to 15% of amount financed depending on tier and lender.
  This is the subprime version of what prime lenders call
  "reserve" (see §4.2), except it works in the opposite direction
  — the dealer *pays* the lender rather than the lender paying
  the dealer.
- **Portfolio-quality pressure:** subprime lenders monitor dealer
  performance closely. Dealers whose customers default early lose
  program access.

**The subprime "waterfall."** Because approvals are hard to get,
F&I often submits to multiple subprime lenders in a specific
order (the "waterfall"), starting with the lender most likely to
buy the deal at the best terms and moving down. Aggressive
waterfalls can burn the deal (many hard pulls, adverse selection
flag). Skilled F&I is targeted, not shotgun.

### 2.5 Buy Here Pay Here (in-house)

BHPH is when the dealer is the lender. Customer buys the car and
pays the *dealer* weekly or biweekly, not a third-party bank. The
dealer holds the note, collects the payments, and takes the loss
on default.

BHPH is common at deep-subprime and no-score customers who cannot
get financing anywhere else. It is a completely different business
model layered onto the sales operation:

- **The dealer becomes a lender** with all the operational overhead
  that implies: payment processing, collections, delinquency
  management, repo, resale of repossessed units.
- **Vehicles are typically cheaper and older** — a BHPH lot
  usually has $5,000–$15,000 units, not $30,000 units.
- **Down payments are relatively high** — typically 20% cash,
  sometimes more, plus trade equity if any.
- **Terms are short** — 24–42 months typical, matched to the
  vehicle's expected reliable life.
- **Rates are at state maximums** in most jurisdictions.
- **Payment frequency is weekly or biweekly** — matches how the
  customer gets paid.
- **In-house payment devices** — some BHPH stores install a
  starter-interrupt device that disables the vehicle if payment is
  missed. Regulated in some states; controversial everywhere.

BHPH portfolios are a real business asset. A dealer with a
performing $2M portfolio earns interest income month over month
that dwarfs individual deal gross. Selling the portfolio (or
factoring receivables against it) is a significant liquidity
event.

**BHPH accounting is different from third-party financed sales.**
Revenue recognition, tax treatment (dealer as lender for
installment sales), and cash-flow patterns all differ. This is
one of the reasons a BHPH-optional store often has separate
software or a separate module for the BHPH portfolio.

### 2.6 Credit unions

Credit unions are member-owned lenders. In auto finance they play
in two lanes:

- **Direct** — the customer walks into their credit union, gets
  pre-approved for a loan amount, then shops for a vehicle and
  brings the pre-approval to the dealer. The dealer collects a
  smaller doc fee and passes the paper through. Dealer reserve is
  minimal to zero.
- **Indirect** — the credit union participates in an aggregator
  (Route One, Dealertrack, CUDL) and the dealer submits deals to
  the credit union like any other bank. Rates are typically
  competitive with prime banks, sometimes better.

Local credit unions often have deep community relationships and
service some deals other lenders won't (long-time members with
thin bureau files but demonstrated deposit/checking history).

For an indie store, having relationships with 2–3 local credit
unions is common and useful. National CUs (PenFed, Navy Fed) are
usually accessed via indirect aggregators.

### 2.7 Captive lenders (for contrast)

Captive lenders are the finance arms of the vehicle manufacturers:
Ford Credit, GM Financial, Toyota Financial Services, Honda
Financial, etc. They exist to help the OEM sell vehicles — subsidized
rates ("0.9% APR!"), lease residual programs, loyalty offers.

Captives are **not typically relevant to indie used-car F&I** for
two reasons:

1. Indie stores don't have OEM contracts.
2. Captives focus on new-vehicle deals; used deals at captives
   are typically CPO (Certified Pre-Owned) programs run through
   franchise dealers.

**Where captives do intersect indie F&I:** occasionally an indie
sells a certified pre-owned or newer-model used vehicle where the
customer's existing captive relationship (they have a Ford Credit
loan on their trade) is the payoff lender. That's the trade
payoff conversation, not a new-loan relationship.

Franchise dealers routinely default to captive first (best rate,
best terms, easy submission, strong OEM incentives). Indie F&I
doesn't have that option.

### 2.8 Buy boxes

A "buy box" is the shorthand phrase for a lender's stated
willingness to buy a specific class of deal. Every lender program
has one; skilled F&I knows the boxes cold.

A buy box combines many variables:

- **Customer tier** — FICO range, bankruptcy age, tradeline count.
- **Vehicle** — age (max model years back), mileage (max), body
  class (some lenders exclude salvage titles, exotics, work
  trucks, or high-mileage diesels), book value (some lenders won't
  finance sub-$5,000 vehicles at all).
- **LTV** — max loan-to-value percentage of book (see §3.2).
- **PTI / DTI** — max ratios (see §3.6).
- **Term** — max term for the tier and vehicle.
- **Down payment** — minimum required.
- **Time on job / time at residence** — minimum months.
- **Prior repossessions** — max count allowed and how recent.
- **Prior bankruptcy** — chapter 7 vs 13, discharged vs open,
  months since discharge.
- **State restrictions** — some lenders don't lend in certain
  states.

An experienced F&I manager can look at a customer's credit
snapshot and the vehicle and immediately mentally match to 2–3
best-fit lenders. That skill is what makes desk-time efficient.

**Buy boxes change.** Lenders adjust programs monthly, sometimes
weekly. A tier that was buyable last month may not be this month.
Program changes come via lender reps (email, portal, phone), rate
sheets, or (in modern systems) API updates to the submission
platform.

### 2.9 The submission decision — waterfall vs targeted

"Where do I send this deal first?" is a decision F&I makes on
every non-cash deal. Two schools of thought:

**Waterfall submission** — submit to a fixed sequence of lenders
in tier order, hoping one approves. Advantages: simple, doesn't
require deep program knowledge. Disadvantages: many hard pulls
(hurts customer's credit and looks shopped to lenders), lenders
see the customer was already shopped by others, slower response
(each lender waits its turn).

**Targeted submission** — submit only to the 1–2 lenders whose
buy box best matches the deal. Advantages: fewer hard pulls,
faster approvals, better rates because the deal isn't "shopped,"
better lender relationships (reps like clean submissions).
Disadvantages: requires the F&I manager to know current program
grids well, small margin for error.

Modern practice at experienced stores is targeted first, waterfall
as fallback. New F&I managers tend to over-submit; veterans
under-submit.

### 2.10 Program mechanics — flats, reserve, discount

How the dealer gets paid on the finance transaction depends on the
lender:

- **Flat fee** — the lender pays the dealer a fixed dollar amount
  (e.g. $150) per funded deal regardless of rate. Common at
  credit unions and some prime programs.
- **Reserve** — the dealer sets a "sell rate" above the lender's
  "buy rate" and earns the difference over the life of the loan.
  Regulatory pressure (CFPB) has capped reserve at 200bp or 300bp
  on many programs. Cash reserve (upfront) vs streamed reserve
  (over loan life) varies by lender.
- **Discount fees ("points")** — the lender buys the paper from
  the dealer at a discount. Dealer receives less than the amount
  financed. Common in subprime.
- **Product allowance** — the lender permits certain amount of
  aftermarket products (GAP, VSC) to be added to the amount
  financed without additional advance-limit calculation. The
  dealer's product profit is separate from finance income.

**Reserve caps** are typically expressed as a max markup in basis
points above buy rate. If the buy rate is 8.99% and cap is 200
bps, the dealer can contract up to 10.99% and earn the spread.

**Split funding** — some lenders send reserve at time of funding;
some pay it monthly as customer payments come in. This affects
cash flow and chargeback exposure.

### 2.11 Common funding rules

Not exhaustive; things every F&I manager knows:

- **Insurance verification is required before funding** — the
  lender needs to see proof of full-coverage insurance with
  themselves listed as loss payee. Deductibles capped (often
  $1,000 max).
- **Title must be in the dealer's name (or immediately assignable)
  at time of sale** to be funded. Missing title = spot delivery
  risk. See §5.9.
- **Recall check** — some lenders (especially subprime) require
  proof that any open recalls have been addressed before funding.
- **Odometer must be verified and disclosed** on the federal
  odometer statement.
- **Vehicle-value cap** — the lender will not fund above their
  stated book value + advance + product allowance. If the deal is
  written above cap, it must be restructured or the store eats
  the difference.
- **Contract date and delivery date must match** the sale reality.
  Backdating contracts is fraud. Post-dating creates funding
  problems.
- **Signatures must match** the customer's ID. Mismatch = funding
  hold.
- **Buyer's Guide (FTC used-car rule)** must be present in the
  deal jacket if the vehicle was sold to a consumer.

---

## 3. Deal Structuring

Deal structuring is what happens between "the customer picked a
vehicle" and "the contract is signed." F&I's job at this stage is
to build a deal that:

- The customer will sign (fits their monthly-payment target,
  respects their comfort with down payment and term).
- A lender will fund (meets the lender's buy box).
- The store makes money on (has room for front-end and back-end
  gross).
- Will not chargeback (fundable clean, not likely to first-payment
  default).

All four of those constraints have to be satisfied simultaneously.
The variables that go into satisfying them are enumerated below.

### 3.1 The variables in play

The classic "deal jacket" of variables F&I balances:

- Vehicle sale price
- Vehicle book value (multiple books; see §3.2)
- Loan-to-value ratio (LTV)
- Cash down payment
- Trade equity (positive or negative)
- Deferred down (if applicable)
- Term (loan length in months)
- Interest rate (buy vs sell)
- Advance limits (lender's max amount financed)
- PTI (payment-to-income ratio)
- DTI (debt-to-income ratio)
- Customer FICO / credit tier
- Vehicle age (model years back)
- Vehicle mileage
- Doc fee (state-regulated max)
- Sales tax (state / county / municipal)
- Title / registration fees (state schedule)
- Aftermarket products (VSC, GAP, T&W, maintenance, etc.)

Changing any one of these ripples through the others.

### 3.2 Book value and LTV

**Book value** is what a third-party pricing source says the
vehicle is worth in a given condition at a given mileage in a
given market. Common sources:

- **Kelley Blue Book (KBB)** — consumer-facing, but dealers use
  dealer-facing KBB numbers.
- **NADA Guides (now JD Power)** — traditional dealer book.
- **Black Book** — dealer-facing wholesale pricing.
- **Manheim MMR (Manheim Market Report)** — actual wholesale
  auction pricing.
- **vAuto / MPI / other appraisal tools** — proprietary book-outs
  fed by aggregated market data.

Each source produces different numbers. Every lender specifies
which book they use and which valuation column (rough, average,
clean, retail).

**LTV (Loan-to-Value)** is the loan amount as a percentage of book
value:

```
LTV = Amount Financed / Book Value
```

Lenders cap LTV. A prime customer might get 140% LTV allowed
(meaning the lender finances 140% of book — the extra 40% allows
for tax, doc, warranty, GAP, and reserve). A deep subprime customer
might be capped at 105% LTV (barely book plus a little).

**How LTV drives structuring.** If a vehicle books at $15,000 and
LTV cap is 130%, max amount financed is $19,500. Sale price plus
tax, title, doc, and any products must fit in that $19,500. If the
customer needs a $22,000 amount financed to make the deal work,
either the customer brings the $2,500 difference in cash, the store
discounts the vehicle by $2,500, or a different lender with higher
LTV is used.

### 3.3 Payment targets vs deal math

Most customers shop by monthly payment, not by price. "I want to
be under $400 a month" is a common opening. Sales team should be
capturing this early; F&I inherits it.

The math:

```
Monthly Payment = f(Amount Financed, APR, Term)
```

Reverse-solving: given a target payment, an APR (from lender
approval), and a max term (from lender buy box), F&I solves for
Amount Financed. That backs into a maximum vehicle price
(minus down, plus tax/doc/products).

**Levers to hit a payment target** when the deal doesn't naturally
work:

- Longer term (lowers payment; increases interest cost + negative
  equity risk).
- More down (lowers amount financed; needs customer to bring
  more cash).
- Lower vehicle price (reduces store gross).
- Drop or downgrade backend products (reduces store gross).
- Rate reduction (only possible if reserve room exists;
  regulatory caps).
- Different lender with better program.

The classic F&I dance: customer says "$400 or I walk"; the deal
naturally comes to $475; F&I finds the combination of levers that
brings it to $399 without losing all the store's gross or
distorting the deal beyond lender tolerance.

### 3.4 Term selection

Loan term is one of the most-manipulated variables because it has
the biggest impact on monthly payment. Longer term = lower
payment. But every additional month:

- **Increases total interest** paid over the life of the loan.
- **Increases the period of negative equity** — the vehicle
  depreciates faster than the loan pays down.
- **Increases default risk in the lender's model** — longer terms
  price higher.

Typical term availability:

- **24 / 36 months** — rare on used, seen on high-value clean
  deals.
- **48 months** — common on shorter-term used deals or
  subprime-capped deals.
- **60 months** — the "standard" for used-car financing in many
  tiers.
- **72 months** — very common; borderline default for
  mid-tier used.
- **75 / 78 months** — some lenders offer, others don't.
- **84 months** — available on newer used, prime tier only for
  most lenders.
- **96+ months** — rare in used; more common in RV/marine or new
  vehicle luxury.

The used-car indie sweet spot is typically 60–72 months.

### 3.5 Rate mechanics — buy vs sell, reserve

Every lender approval comes back with a "buy rate" — the lowest
rate the lender is willing to fund that specific deal at. The
dealer may contract the customer at the buy rate (rate-buy-down,
no reserve) or at a higher rate up to the lender's markup cap
(with reserve going to the dealer).

Example: buy rate 8.99%, cap +200 bps. Dealer can sell rate at
anywhere from 8.99% to 10.99%. If dealer contracts at 10.99%, the
dealer earns reserve income based on the spread over the loan life
(paid upfront or streamed, per lender).

**Rate disclosure.** Truth in Lending Act (Reg Z) requires the
dealer to disclose the APR to the customer clearly. The customer
sees the contract rate, not the buy rate. The dealer's reserve is
not itemized to the customer as a separate charge — it's baked
into the APR.

**Reserve caps.** Historically dealers had significant discretion.
CFPB enforcement actions in the 2010s pressured lenders to cap
dealer markup (typically 200 bps for 60-mo+ or 250 bps for
shorter), driven by concerns about disparate impact on protected
classes.

**Rate-shopping and reserve compression.** Sophisticated customers
shop rates. When a customer walks in with a pre-approval from
their credit union at 6.99% and the store's dealer floor at their
best lender is 8.99%, there's no reserve room and the store
either matches (giving up reserve) or loses the finance
transaction (customer uses their credit union — store gets doc fee
and product sales only).

### 3.6 Ratios — PTI and DTI

Two ratios drive lender fundability decisions:

**PTI (Payment-to-Income)** — the proposed monthly car payment as
a percentage of the customer's gross monthly income.

```
PTI = Monthly Payment / Gross Monthly Income
```

Typical caps:
- Prime: 15%–20%
- Near-prime: 15%–18%
- Subprime: 12%–15% (yes, tighter — subprime lenders are
  paranoid about default)

A customer earning $4,000/month and looking at a $600/month
payment is at 15% PTI. That's marginal for prime, tight for
subprime.

**DTI (Debt-to-Income)** — all monthly debt payments (car, housing,
credit cards, other loans, court-ordered child support) as a
percentage of gross monthly income.

```
DTI = Sum of All Monthly Debt Payments / Gross Monthly Income
```

Typical caps:
- Prime: 40%–50%
- Near-prime: 40%–45%
- Subprime: 40%–50% (varies widely by program)

A customer with a $1,200 rent payment, $200 credit card minimums,
$150 in student loans, and now a $600 proposed car payment on
$4,000 income is at 53.75% DTI. Most lenders will decline that.

**Solving ratio problems.** If PTI or DTI is over cap, options
include: more down (lowers payment), longer term (lowers
payment), lower vehicle price (lowers payment), co-buyer (adds
income), or restructure with a lender that has more forgiving
ratios.

### 3.7 Down payment sources

Rehashed from §1.7 with a structuring lens:

- **Cash** contributes 100% to lower LTV and lower payment.
- **Trade equity** does the same, but is only as good as the
  appraisal (see §1.6).
- **Deferred down / split down** — the lender may not count it
  toward down payment for LTV purposes. Some lenders exclude it
  entirely; some count 50%; some allow full weight but require
  post-dated check.
- **Manufacturer/aftermarket rebates** — mostly N/A for indie
  used.
- **Tax refund promises** — informal, high risk.

**Money down decisions are constant.** "Bring me $500 more and I
can move to a better lender / lower rate / longer term / include
that warranty you wanted" is a phrase F&I says every day.

### 3.8 Negative equity

When a customer owes more on their trade than it's worth. The
difference has to be absorbed:

- **Rolled into the new loan** — increases amount financed,
  raises LTV, may bust lender cap.
- **Paid in cash by customer** — clean solution, but the
  customer usually can't or won't.
- **Discounted from the new vehicle price** — comes out of store
  gross.
- **Combination** — some cash, some rolled, some discount.

**Compounding effect.** Rolling negative equity into a new loan
often creates a new deal that is *itself* upside-down from day
one. Two years later the customer trades again with more negative
equity. This cycle is a real driver of subprime distress.

Lenders track cumulative negative equity risk and often cap the
amount they'll allow rolled from a trade — typically 100%–125% of
the trade's book value.

### 3.9 The balancing act — a worked example

To make the interactions concrete, one example:

> Customer: FICO 620, income $3,800/month, lives with parents (no
> housing payment), 8 months on current job.
>
> Vehicle: 2020 Nissan Altima, 62,000 miles, priced at $17,500.
> Books at $15,800 clean retail (via JD Power).
>
> Trade: 2015 Chevy Malibu, 110,000 miles. Books at $6,500.
> Payoff quoted at $8,200. Negative equity: $1,700.
>
> Customer wants: $350/month, no cash down.
>
> Sales, tax, doc, title: $18,900 total on the new vehicle before
> negative equity roll.
>
> Deal option A: roll the $1,700 negative equity, no cash down,
> amount financed = $20,600. LTV = $20,600 / $15,800 = 130%.
> Subprime cap on this tier vehicle typically 120%. Deal is over
> cap.
>
> Deal option B: request $1,000 cash down. Amount financed =
> $19,600. LTV = 124%. Still over.
>
> Deal option C: request $2,500 cash down + $500 doc fee waiver
> from the store. Amount financed = $17,600. LTV = 111%.
> Fundable. Payment at 22% APR / 72 months ≈ $423/month.
> Above customer's target.
>
> Deal option D: same as C plus extend to 84 months (if lender
> allows). Payment ≈ $388/month. Still above target.
>
> Deal option E: option D + drop VSC and GAP from the deal.
> Amount financed drops to $15,900. LTV = 100%. Payment ≈
> $353/month. Meets target. Store loses backend product gross.
>
> Deal option F: option E but retain GAP (customer will thank
> you if the car is totaled at month 6). Amount financed +$800 =
> $16,700. LTV = 106%. Payment ≈ $371/month. Slightly above
> customer target.
>
> F&I presents F to customer with a payment-cushion story
> ("$21 more per month covers you if the car is totaled"). Deal
> closes.

Every real deal is a variant of this. F&I skill is doing the
math fluidly enough to see the levers in real time while sitting
across from the customer.

---

## 4. Profitability

### 4.1 Where indie F&I money actually comes from

Independent used-car F&I gross comes from several distinct
sources. Roughly in order of typical contribution:

1. **Aftermarket product sales** (VSC, GAP, T&W, maintenance
   plans, etc.) — usually the largest single line.
2. **Reserve** (finance income from lender markup) — meaningful
   but not dominant, capped by regulation.
3. **Doc fee** — small but consistent; state-regulated.
4. **BHPH interest income** — only if the store has an in-house
   portfolio.
5. **Subprime "discount give-back"** — really a *cost*, not
   income, but structured deals sometimes net out favorably.

The metric F&I is measured against is **per-copy** or
**per-vehicle retail (PVR)** — total F&I gross divided by units
sold. Common indie F&I PVR ranges from $800 to $2,000+ depending
on store mix, tier weighting, product menu discipline, and
customer profile.

### 4.2 Reserve — finance income

Covered in §3.5. In indie used it's smaller as a share of
per-copy gross than in franchise new because:

- Subprime deals often pay *discount* rather than reserve
  (dealer loses money on rate spread).
- Reserve caps limit upside.
- Prime deals often come with rate-shopping customers who
  compress the reserve.
- Credit union deals typically pay flats, not reserve.

A store doing 100 units a month might see $10,000–$25,000 in
reserve income depending on tier mix.

### 4.3 Vehicle service contracts (VSC)

VSCs (informally "extended warranties," though they're not legally
warranties) cover repair costs after the manufacturer's warranty
expires — or, for older used vehicles, from day one.

**Coverage tiers:**
- **Powertrain** — engine, transmission, drive axle. Cheapest.
- **Wrap** or "gold" — powertrain plus most other mechanical
  systems.
- **Exclusionary** or "platinum" — covers everything except a
  short exclusion list. Most expensive. Most similar to the
  manufacturer's warranty.

**Term / mileage:** VSCs are sold with a term (months) and a
mileage limit (odometer at expiration). Typical: 24/24k, 36/36k,
48/48k, 60/60k, 72/72k, 84/100k. Longer/more coverage costs more.

**Deductibles:** $0, $50, $100, $200 typical. Higher deductible
= lower premium.

**How they're priced.** F&I acquires the VSC from a provider
(third-party administrator) at a "cost" (also called "invoice" or
"floor"). The store marks it up to a retail price, disclosed to
the customer. The markup is often 100%+ of cost. Cancellation
refunds are pro-rated to the *customer*, not the store (unless
the customer cancels within a rescission window, which some
providers allow).

**Regulation.** VSC pricing is unregulated in most states
(consumer protection is the disclosure of the price and terms,
not the price itself). A few states cap dealer markup on VSCs.
Complete cancellation rights and refund calculations are the most
regulated aspects.

**Chargeback exposure.** If the customer cancels the VSC or pays
off the loan early, the store's commission is charged back
pro-rata. Big chargeback exposure item — see §5.7.

### 4.4 GAP — Guaranteed Asset Protection

GAP covers the difference between what a customer's primary auto
insurance pays if the vehicle is totaled and what the customer
still owes on the loan.

Example: customer owes $19,000, vehicle is totaled and insurance
pays out $14,500 (actual cash value). Without GAP, customer owes
$4,500 out of pocket. With GAP, GAP pays the $4,500 (or the
covered portion — max caps and exclusions apply).

**Who needs it:**
- Customers who are upside-down on the loan (i.e. most subprime,
  most long-term financed).
- Customers with high-mileage driving profiles (accident risk).
- Customers with limited savings.

**Who doesn't need it:**
- Customers who put substantial cash down.
- Customers with strong emergency funds.
- Customers on short terms with low LTV.

**Pricing.** GAP is typically a flat dollar cost ($400–$900
depending on state, term, and provider), marked up to a retail
price ($700–$1,200 typical). State-regulated maximums exist in
some jurisdictions.

**Cancellation.** GAP is fully cancellable pro-rata. Big
chargeback item. First-year cancellations are common (customer
pays off early, refinances, or trades).

### 4.5 Tire & Wheel, maintenance plans, other backend products

**Tire & Wheel (T&W)** — covers damage from road hazards
(potholes, debris) to tires and wheels. $200–$500 cost, $400–$900
retail typical.

**Prepaid maintenance** — bundle of oil changes and scheduled
services. $200–$500 cost, $400–$900 retail typical.

**Appearance / paintless dent repair** — covers minor dents,
scratches, interior stains for a defined period. $200–$400 cost,
$500–$900 retail typical.

**Key replacement** — covers lost / stolen keys and fobs.
$100–$200 cost, $200–$400 retail typical.

**Windshield replacement** — some markets bundle this separately
from T&W.

**Theft deterrent / etch / VIN etch** — historically a "pack"
item; less common now, subject to consumer scrutiny.

**Credit insurance (credit life, credit disability)** — pays the
loan if the customer dies or becomes disabled. Historically a
significant product; declined in popularity due to consumer
advocacy pressure and loss ratios. Still offered by some stores.

**Product menu discipline.** Modern F&I best practice is to
*present every product to every customer* using a standard menu
form. This is a legal-defense practice (fair-lending / product
steering complaints) and a compliance practice. The menu
documents that the customer was given the same offering
regardless of demographics.

### 4.6 Doc fee

The "documentation fee" or "doc fee" or "processing fee" is a fee
the dealer charges to prepare the deal paperwork. Every state
regulates the maximum. Ranges from $75 (some Northeastern states)
to $999 (Florida) to unlimited (a few states). Averages $300–$700
in many markets.

Doc fee is fully disclosed on the contract. It's a small but
consistent contribution to per-copy gross.

### 4.7 BHPH interest income (if applicable)

For stores with an in-house BHPH portfolio, interest income on the
portfolio is a substantial part of the business. See §2.5.

Portfolio management (collections, delinquency, repo) is a
non-trivial operational load and is really a separate business
from the sales operation, even when they share a physical roof.

### 4.8 Per-copy gross composition

A common indie F&I per-copy target of $1,200 might break down as:

| Source | Contribution |
| --- | --- |
| VSC | $400 |
| GAP | $250 |
| T&W / other minor products | $150 |
| Reserve (net of discount) | $200 |
| Doc fee | $200 |
| **Total** | **$1,200** |

Different stores have very different mixes. A subprime-heavy store
might see negative reserve (discount cost) but strong VSC + GAP.
A prime-heavy store might see strong reserve but lower product
attach because prime customers decline more products.

---

## 5. Funding

Funding is the process of the lender actually depositing the money
into the dealer's account for the sold deal. Between contract
signing and funding is a window of hours to days (occasionally
weeks) during which the store has:

- Delivered the vehicle to the customer.
- Not yet been paid.
- Exposure to any delay or reversal.

"Funded" means the deal is closed from the store's perspective.
Everything before funding is at-risk revenue.

### 5.1 The funding packet

A funding packet is the complete set of documents the lender
requires to process funding. It varies by lender but typically
includes:

- Signed retail installment contract (RISC) or lease agreement.
- Credit application (signed).
- Copy of driver's license (front and back sometimes).
- Proof of income (paystub, VOE, etc.).
- Proof of residence.
- Proof of insurance (full-coverage with lender as loss payee).
- Odometer disclosure statement (federal form).
- Title work (title in dealer's name, MSO for new).
- Trade payoff (if applicable).
- Any product forms (VSC, GAP, T&W agreements).
- Buyer's Guide (FTC used-car rule).
- Menu / product-offering documentation.
- Adverse-action notice (if applicable to lender counter-offer).
- Bank / lender-specific forms.

Some lenders take an electronic packet uploaded through their
portal; others require paper mailed or overnighted; some are
hybrid.

### 5.2 Common stipulation categories

Rehashed from §1.9 with a funding lens. Stips fall into categories
by what they verify:

- **Identity stips** — ID copy, SSN card, birth certificate for
  young buyers.
- **Income stips** — paystubs (usually 2), W-2, tax return, VOE
  form, benefit letters.
- **Residence stips** — utility bill, lease, mortgage statement.
- **Vehicle stips** — insurance card, photos of vehicle, mileage
  verification, VIN etch verification.
- **Contract stips** — corrected/re-signed contracts, disclosure
  addenda.
- **Portfolio stips** — trade payoff verification, trade title work,
  odometer statement.

### 5.3 Missing stips and delays

The biggest cause of funding delays. Store submits the packet,
lender reviews, lender responds with "we need X." Store hunts down
X, resubmits. Rinse and repeat.

Causes:
- Customer left without providing all stips at delivery
  (spot-delivered).
- Sales / F&I didn't verify stips before letting the customer
  leave.
- Lender's stip requirements changed after approval.
- Documentation was insufficient (unclear photo, out-of-date paystub).
- Post-delivery paperwork mistakes (missing signature, wrong date).

**How long delays run.** Simple missing paystub — 24 hours. Trade
payoff verification with a slow trade lender — 3–5 business days.
Missing title — indefinite. Insurance company slow to send binder
— several days.

### 5.4 Title requirements

The title is the legal document establishing ownership of the
vehicle. Every state has slightly different title rules, but the
common denominators:

- **Title must be in the dealer's name** (or immediately assignable
  by dealer) at time of sale to the customer.
- **Lienholder must be recorded** on the new title — the new lender
  becomes the lienholder, replacing the trade lender if any.
- **ELT (Electronic Lien & Title)** — many states use electronic
  title systems where the paper title is held by the state and
  lienholder status is tracked electronically. Faster and safer
  than paper titles.
- **Out-of-state titles** — mailing time to and from other states
  can add weeks.
- **Duplicate title** — if the title was lost, the dealer must
  apply for a duplicate before selling. Delay: 2–8 weeks depending
  on state.
- **Salvage / branded titles** — flag the vehicle history and often
  make it unfundable at most lenders.

**Trade title handoff.** If the customer's trade has a lien, the
dealer must pay off the trade lender to get the title released.
Timeline: 5–10 business days from payoff receipt to title arrival
at the dealer (paper) or ELT update.

### 5.5 Bank communication

Bank communication in F&I is:
- **The portal / DMS integration** — deal submission,
  approval/decline responses, stip lists, funding status.
- **Email with the lender rep** — for program questions,
  exceptions, escalations, chargeback disputes.
- **Phone calls to the funding department** — for urgent stip
  clarifications, delayed funding investigation, missing packet
  troubleshooting.
- **Occasional in-person visits from lender reps** — for program
  updates, relationship maintenance, trouble-deal reviews.

Each lender has a preferred communication channel for each type
of conversation. Modern F&I keeps notes per lender.

### 5.6 Funding confirmation

Funding confirmation comes in different forms:

- **ACH deposit** — the funds hit the dealer's account.
  Confirmation via bank statement or DMS bank feed.
- **Wire** — same-day funds, usually for larger deals.
- **Check** — mailed, usually for smaller lenders or specific
  programs.

The store's accounting or F&I office watches for the deposit and
matches it against the expected funding amount. Any variance
(fees deducted, discount taken, insurance escrow, first-payment
holdback) is investigated.

**Deal marked "funded"** in the deal management system when the
deposit is confirmed and the packet is complete on the lender's
side. This is the trigger for:

- F&I commission calculation and payout.
- Sales commission calculation and payout.
- Deal closure on the books.
- Vehicle inventory disposition finalization.
- Chargeback exposure clock start (see §5.7).

### 5.7 Chargebacks

A chargeback is when the lender reverses part or all of the
dealer's compensation on a funded deal because something
subsequently went wrong.

**Common chargeback triggers:**

- **First payment default (FPD)** — customer doesn't make the
  first monthly payment. Signals bad underwriting. Lender
  chargebacks reserve, sometimes acquisition fee, sometimes
  product commissions.
- **Early payoff** — customer refinances or pays off within
  90–180 days. Reserve was calculated over life-of-loan; lender
  reclaims unearned portion.
- **Voluntary cancellation of product** — customer cancels VSC,
  GAP, T&W within some period; store's commission is chargedback
  pro-rata.
- **Repossession within a chargeback window** — some lenders
  chargeback certain fees if the loan defaults quickly.
- **Deal rescission / unwind** — customer bails on the deal
  before it's fully funded, or contract is voided due to error.

**Chargeback windows vary** by lender and product. Common windows:
90 days for first payment / early payoff, 3-5 years pro-rated for
VSC/GAP.

**F&I compensation impact.** Most F&I managers are paid on
funded gross, but with a chargeback clawback: if the deal
chargebacks, the F&I manager's commission gets reduced or reversed
in the following pay period. F&I is directly incentivized to
avoid FPD-prone deals.

### 5.8 Deal unwinds

An "unwind" is when a deal that was signed and delivered gets
undone before it fully funds. Causes:

- **Lender bounce** — the deal was submitted, approved
  conditionally, delivered on the strength of the conditional
  approval, and then the lender declined after receiving the full
  packet. Common in spot-delivery situations.
- **Customer bail** — customer changes their mind and returns the
  vehicle before funding. Legally messy; depends on state and
  contract terms.
- **Contract errors** — signatures missing, wrong figures, wrong
  vehicle info. Requires re-contracting and sometimes re-delivery.
- **Vehicle problems** — customer discovers a mechanical problem
  during the first days, dealer chooses to unwind rather than
  fight.
- **Deceptive customer information** — customer misrepresented
  income or employment; lender declines when the truth comes out
  during funding stip review.

Unwinds are financially bad. The store loses the deal, has to
undo the sale in inventory, refund any customer money, and
sometimes eat depreciation on the returned vehicle.

**Spot-delivery unwinds** are the most common unwind category
and the reason F&I discipline around approval-before-delivery
matters (see §5.9).

### 5.9 Spot delivery — the recurring risk

"Spot delivery" is when the store lets the customer take the
vehicle home *before* full lender approval is in hand. Reasons:

- Customer pressure (they want the car today).
- Deal came in late Friday and no lender is answering till Monday.
- Manager wants to book the unit this month.
- Approval was conditional and the store bet on the stip being
  cleanable.

If the deal doesn't fund, the store has to get the vehicle back.
State laws vary widely on the mechanics of undoing a spot
delivery. Some states protect consumers strongly; some are
neutral; some favor dealers.

The industry standard mitigation is a **"conditional delivery"
agreement** signed by the customer, acknowledging that the sale is
contingent on lender funding and that the customer must return
the vehicle if funding fails. Enforceability varies.

**Spot delivery in indie subprime** is more common than in
franchise prime because subprime approvals are harder and slower
and customers often insist. Every subprime-heavy indie store
carries some spot-delivery risk continuously.

---

## 6. Compliance (awareness, not legal advice)

The compliance regulations in this section apply to any dealer
engaging in credit transactions. **Nothing here is legal advice.**
Every dealer's compliance program should be built with a qualified
compliance professional. The purpose of this section is to
identify *where* compliance touches the F&I workflow so that any
software the platform builds understands the constraints.

### 6.1 Truth in Lending Act (Reg Z)

Federal law requiring clear disclosure of credit terms to
consumers. Key F&I touch points:

- **APR must be prominently disclosed** on the contract and
  itemized separately from other fees.
- **Finance charge** (total dollar cost of credit over the loan)
  must be disclosed.
- **Amount financed** must be itemized (what the money is being
  spent on: vehicle price, tax, doc, GAP, VSC, etc.).
- **Payment schedule** must be disclosed (number of payments,
  amount, timing).
- **Total of payments** must be disclosed.
- **Prepayment terms** must be stated.
- **Security interest** must be identified (the vehicle serves as
  collateral).

Non-compliance can result in the customer having a right to
rescind the transaction, plus statutory damages. Reg Z errors are
the #1 source of consumer lawsuits against dealers.

### 6.2 OFAC screening

The Office of Foreign Assets Control maintains the SDN list of
sanctioned individuals and entities. Dealers must screen customers
against the list before extending credit. Rarely produces a hit
but the compliance obligation is absolute.

Most credit bureau services include an OFAC check as part of the
bureau pull. Documented "hit" or "no hit" for each transaction.

### 6.3 Red Flags Rule

Under the Fair Credit Reporting Act (FCRA), dealers must have a
written **identity theft prevention program (ITPP)**. Key elements:

- Identify **red flags** (patterns / activities / practices that
  indicate possible ID theft).
- Detect red flags in real time during transactions.
- Respond appropriately when red flags are detected.
- Update the program periodically.

Common red flag categories: SSN discrepancies, address
discrepancies, ID document alteration, customer behavior
suggesting impersonation.

The rule requires an actual written program, not just verbal
practice. Periodic training required for all staff who touch
customer credit data.

### 6.4 Privacy — GLBA and the Safeguards Rule

The Gramm-Leach-Bliley Act treats non-public personal information
(NPI) collected in a financial transaction as regulated data.
Two sub-rules dominate for dealers:

**Privacy Rule** — dealers must:
- Provide customers with an **initial privacy notice** at the
  start of a customer relationship.
- Provide **annual privacy notices** to ongoing customers.
- Give customers the right to **opt out** of certain kinds of
  information sharing.

**Safeguards Rule** — dealers must implement a **Written
Information Security Program (WISP)** that:
- Designates a **Qualified Individual** responsible for the WISP.
- Conducts a **risk assessment** of NPI storage and handling.
- Implements safeguards (physical, technical, administrative)
  proportionate to risk.
- Requires **encryption of NPI in transit and at rest**.
- Requires **multi-factor authentication** for systems accessing
  NPI.
- Provides **regular security training** for staff.
- Maintains an **incident response plan**.
- Requires oversight of **service providers** who handle NPI on
  the dealer's behalf.

The Safeguards Rule was significantly strengthened in 2021 with
requirements taking effect in stages through 2023. Any software
platform handling F&I data (customer credit apps, credit reports,
deal jackets, funding packets) becomes a service provider under
this rule, and the dealer bears responsibility for the platform's
security posture.

### 6.5 Adverse action

If a dealer takes an **adverse action** on a credit application
— denying credit, offering credit on materially less favorable
terms, requiring a co-signer, etc. — the customer is entitled to
an **adverse action notice** under FCRA and Reg B (ECOA).

The notice must:
- State the reasons for the action (or offer them on request).
- Identify the credit bureau used.
- Notify the customer of their right to a free copy of the report.
- Include ECOA anti-discrimination language.

**Timing:** within 30 days of the decision, in most cases.

**Who is the "creditor" that owes the notice?** Complicated. If
the *dealer* declined the deal, the dealer sends the notice. If a
*lender* declined and the dealer is arranging credit, the lender
sends the notice (but the dealer must sometimes also send one).
Multiple lenders declining the same submission may generate
multiple notices.

Missing adverse action notices are another common lawsuit source.

### 6.6 Fair lending — ECOA and Reg B

The Equal Credit Opportunity Act prohibits discrimination in
credit transactions based on race, color, religion, national
origin, sex, marital status, age (if of legal age to contract),
receipt of public assistance, or the exercise of consumer
protection rights.

For dealers this means:
- **Consistent pricing.** Reserve markup / rate discretion must
  be applied consistently across protected classes. Historical
  pattern of higher markup on minority customers has been the
  subject of significant enforcement actions.
- **Consistent product offering.** Every customer should be
  presented the same product menu at the same prices.
- **No steering.** F&I cannot steer customers to worse products
  based on protected characteristics.
- **Documentation.** Menu forms, rate quotes, and pricing
  decisions should be documented to establish consistency.

### 6.7 FTC Safeguards Rule (2023 updates)

Layered on top of the GLBA Safeguards Rule above. Key 2023
requirements:

- Written **information security program** in place.
- Named **Qualified Individual** with responsibility.
- **Annual risk assessment.**
- **Monitoring and testing** of safeguards.
- **Encryption** of NPI in transit and at rest.
- **Multi-factor authentication** for all NPI access.
- **Vendor oversight.**
- **Incident response plan** documented.
- **Training program** for staff.
- Written annual **status report** to the dealer's Board or
  equivalent management.

Enforcement began 2023; FTC has authority to fine
non-complying dealers and to publish enforcement actions.

### 6.8 State-specific

Every state has additional regulations layered on federal
requirements. Common categories:

- **Doc fee caps.**
- **Rate caps** (state usury limits — subprime deals often bump
  against these).
- **Cooling-off periods** — despite common consumer belief, most
  states do NOT have a cooling-off period on auto sales. A few
  do; F&I must know their state's rule.
- **Spot delivery / conditional delivery rules.**
- **Odometer disclosure specifics.**
- **Buyer's Guide language / format.**
- **Advertising rules** — restrictions on payment ads, rate
  disclosures, "as low as" language.
- **BHPH-specific rules** — starter-interrupt devices, GPS
  tracking, collection practices, refund on repo.
- **License plate / temporary tag rules.**
- **Documentation retention periods.**

### 6.9 Records retention

Federal and state rules require deal records be retained for
periods ranging from 2 years (some paper documents) to 5–7 years
(most transaction records) to indefinite (some title work). The
deal jacket is the operational record of retention.

Digital retention subject to the Safeguards Rule (encrypted,
access-controlled). Paper retention subject to the Disposal Rule
(shredded on disposal).

---

## 7. Pain Points

Repetitive operational friction F&I managers experience every day.
This section documents pain; it does not propose fixes.

### 7.1 Data re-entry

The customer fills out the credit app once, but that same data
gets entered into:
- The store's DMS.
- Route One or Dealertrack for lender submission.
- Each lender portal for direct submission (some lenders don't
  accept aggregator submissions).
- The state's title/registration system.
- The insurance verification system.
- The internal deal-jacket / paperwork prep system.
- The commission tracking system.

Any inconsistency between these entries becomes a downstream
funding stip or a rejected packet.

### 7.2 Lender program comparison

At desk time, F&I is mentally comparing multiple lenders' current
programs against the deal in front of them. Program rate sheets
sit in binders, in email inboxes, in portal messages, in the F&I
manager's head. Programs change monthly (sometimes weekly). The
"best lender for this deal" answer requires holding a lot of
current information.

### 7.3 Stipulation tracking

For every deal in the funding pipeline, F&I is tracking:
- Which lender is on the deal.
- What stips that lender listed at approval.
- What stips have been collected so far.
- What's still missing.
- Who's responsible for chasing what.

At any moment there might be 15–40 open deals with various stip
states. The tracking tool ranges from a spreadsheet to a
whiteboard to a DMS module.

### 7.4 Paperwork chase

Physical paper still dominates parts of F&I. Signed contracts,
paper trade titles, physical odometer statements, notarized
documents. Every piece of missing paper becomes a phone call, an
in-person follow-up, or a delay.

### 7.5 Funding follow-up

Deals sit in "funded pending" for hours to days. F&I calls the
funding department, chases stips, monitors the bank feed for
deposits, updates internal status, answers "did that deal fund
yet" questions from sales and accounting.

### 7.6 Deal jacket completion

At the end of every deal, someone (F&I or a dedicated deal
processor) has to assemble the complete deal jacket for
retention. Cross-reference every required document against a
checklist. Chase down anything missing. File.

### 7.7 Answering "did we fund yet?"

Sales wants to know for commission. Accounting wants to know for
booking. The customer sometimes wants to know for their own
peace of mind. F&I is the only source of truth for funding
status, and the question comes constantly.

### 7.8 Rewriting after program or stip changes

A lender changed a program mid-deal. A stip came back that
requires the contract to be re-signed. The customer's insurance
lapsed between contract and delivery. Every rewrite is a
re-collection of signatures, sometimes at the customer's home or
workplace.

### 7.9 Managing dead deals

Deals that fell through (customer went elsewhere, financing fell
through, customer bailed) still need to be closed out in the
system, adverse-action notices sent, credit bureau logs updated,
inventory reset to available. Dead deals get less attention than
live ones and accumulate incomplete records.

### 7.10 Explaining decisions to customers

Customer wants to know why they didn't get the rate they saw
advertised. Why the payment is $50 more than what sales quoted.
Why the deal needs $500 more down. Why they need a co-buyer. Why
the trade is worth what the appraisal says.

Every explanation takes time and requires balancing
transparency with not disclosing lender-specific pricing details
that are trade secrets or dealer-confidential.

### 7.11 Chargeback exposure

Every funded deal carries ongoing exposure to chargebacks for
months. First-payment defaults, early payoffs, product
cancellations — any of them can reverse F&I compensation weeks or
months after the deal was booked.

### 7.12 Compliance overhead

Every deal must generate the right disclosures, the right notices,
the right retention records. The compliance workload is
non-negotiable and grows with regulatory changes (like the 2023
Safeguards Rule update).

---

## 8. Operational Decisions

These are decisions F&I makes many times per day. Each one is a
candidate for future decision-support intelligence — but the
decisions themselves belong to humans.

### 8.1 Which lender should receive this deal first?

Inputs: customer tier, vehicle, LTV, PTI/DTI, current program
grids, rep relationships, recent portfolio performance with the
lender, deal-specific quirks. Output: one primary submission and
a mental backup list.

### 8.2 Should additional cash down be requested?

Inputs: current LTV, lender cap, payment target vs. current
projection, customer's tolerance for out-of-pocket. Output:
yes/no + specific dollar ask.

### 8.3 Should another lender be attempted?

After a decline or unacceptable counter, F&I decides whether to
restructure and resubmit to the same lender, submit to a different
lender, or work the deal a different way (different vehicle,
different structure).

### 8.4 Is this deal fundable clean?

Independent of lender approval, is the deal likely to fund
without stip creep or contract corrections? Predicts customer
follow-through, insurance timing, trade title readiness, etc.

### 8.5 Is this deal profitable enough to work hard on?

Some deals aren't worth the effort. A subprime deal with a
skinny reserve, no product attach, and stip issues might be
better killed than pushed. The judgment involves weighing store
volume goals against F&I efficiency.

### 8.6 What products fit this customer's needs and payment room?

Menu presentation is standardized (compliance), but the *ordering*
and *emphasis* is judgment. A customer with $50/month payment
cushion can absorb GAP + a light VSC. A customer with $10/month
cushion probably only gets GAP.

### 8.7 Which term unlocks the approval?

If the deal is over PTI at 60 months, does moving to 72 solve it
without violating LTV or DTI or lender term caps? F&I ratchets
term until the ratios work.

### 8.8 Do I re-contract or work around?

Small deal-jacket errors sometimes can be corrected with an
addendum; others require a full re-contract. Judgment call
weighing customer availability, lender tolerance, and time cost.

### 8.9 Do I accept the counter-offer or push back?

Lender counter-offers ("we'll approve at 22% instead of 20%," or
"we need $500 more down") can be accepted or negotiated. Rep
relationships and portfolio history matter here.

### 8.10 Should I spot-deliver this deal?

Every conditional approval that a customer wants to leave with is
a spot-delivery decision. The store's exposure vs the customer's
urgency vs the risk of unwind. Judgment based on customer profile,
deal cleanliness, and lender predictability.

### 8.11 Do I decline this deal?

Some deals shouldn't be pursued at all — customer red flags, deal
math that won't work anywhere, portfolio-damage risk to lender
relationships. F&I can decline a deal internally; sales manager
may push back.

### 8.12 What's the right customer explanation?

For every rate, product, or structure decision, F&I chooses how
to explain it to the customer. The framing affects customer
satisfaction, CSI scores, and long-term loyalty.

---

## 9. Automation Opportunities

This section identifies *where* repetitive operational work lives.
It does **not** design solutions. Design happens later, in
dedicated implementation planning.

Each item below is an area where humans currently spend meaningful
time on work that could plausibly be accelerated by software while
keeping the decision authority with the human.

### 9.1 Cross-application data flow

Customer information entered once in the credit app currently
gets re-entered into 4–8 downstream systems. Whenever the same
data is entered more than once, it's an automation candidate.

### 9.2 Lender program comparison at desk time

The mental model of "which lender for this deal" is doable by
software given current program data + deal facts + historical
performance. Not a decision-maker — a decision *support* tool.

### 9.3 Stipulation checklist auto-generation

Given lender + tier + deal type + collateral, the required stip
list is deterministic per lender program. Auto-generating that
checklist saves the manual lookup and reduces missed stips.

### 9.4 Funding packet completeness pre-check

Before a packet is submitted, a checklist can verify all required
documents are present, signatures are complete, and dates match.
Reduces the packet-round-trip rate.

### 9.5 Funding status tracking dashboard

Every open deal, current status (submitted / approved / signed /
funding pending / funded / declined), pending stips, days aging.
Answers "did we fund yet" without a manual query.

### 9.6 Chargeback risk indicators

Deal characteristics that predict elevated chargeback risk (very
short time on job + high LTV + minimum down + long term) can be
surfaced at time of structuring so F&I can address them.

### 9.7 Deal-jacket audit

Automated check of every deal jacket for completeness against a
per-deal-type checklist. Reduces post-funding jacket-scramble
work.

### 9.8 Rate-sheet drift detection

Lender program updates are hard to keep current. Software can
compare current rate sheets to prior versions and surface changes,
so F&I sees what changed this week.

### 9.9 Book-out variance flagging

The vehicle's book-out (from JD Power / KBB / MMR) should agree
across whichever sources the deal uses. Variance beyond a
threshold suggests a book-out error or a vehicle condition issue
worth flagging.

### 9.10 Compliance calendar

Annual WISP review, adverse-action mailings, safeguards audit,
state-specific renewals — a calendar-driven reminder system that
tracks compliance obligations by date.

### 9.11 Adverse-action letter generation

When a deal is declined, the adverse-action notice can be
auto-drafted using the credit bureau data already on file, ready
for review and send.

### 9.12 Trade payoff quote workflow

Trade payoff lender contact, quote request, quote receipt,
comparison to app-stated payoff — a structured workflow reduces
manual phone-and-fax overhead.

### 9.13 Insurance verification workflow

Customer's insurance company contact, verification request,
binder receipt, expiration monitoring for lapse — currently a
lot of manual chasing.

### 9.14 First-payment default early warning

Watching for FPD signals (customer contact goes silent, address
changes right after funding, insurance lapses in month one) can
surface chargeback risk before the FPD hits.

### 9.15 Menu presentation consistency check

Compliance (fair lending) requires consistent product menu
presentation. A verification step confirming every customer saw
the same menu supports compliance defensibility.

Each of these is a candidate for its own future research or
implementation planning session. The list is not exhaustive; it
represents the highest-friction, highest-repetition candidates
observed in the Pain Points section.

---

## 10. Cross-Department Dependencies

F&I does not operate alone. Every deal touches multiple other
departments. This section documents *what F&I needs from* and
*what F&I gives to* each. It does not propose changes to those
departments.

### 10.1 Inventory

**F&I depends on Inventory for:**
- Accurate book-out (correct year, make, model, trim, options,
  mileage). Book errors invalidate LTV math.
- Title status (title in hand, floor-planned, branded).
- Vehicle history report (Carfax / AutoCheck) — some lenders
  require it in the packet.
- Photos (some lender portals require).
- VIN verification and odometer statement source.
- Recall status.
- Actual current mileage at delivery (may differ from lot photo).

**Inventory depends on F&I for:**
- Timely disposition when a deal funds (unit removed from
  available inventory).
- Timely reset when a deal falls through (unit returned to
  available).
- Feedback on which units are "buyable" by which lenders (some
  units are unfundable at some tiers).

### 10.2 Sales

**F&I depends on Sales for:**
- Accurate customer profile (target payment, term preference,
  cash down capacity, trade information).
- Realistic vehicle pricing (Sales sometimes commits to prices
  F&I can't structure into a fundable deal).
- Timely handoff with all customer info collected.
- Coaching the customer to bring documentation (paystubs, ID,
  insurance card) to speed the process.
- Trade information brought forward (year/make/model, payoff
  quote requested if possible).

**Sales depends on F&I for:**
- Deal approval before over-committing to the customer.
- Payment quotes the customer can actually get.
- Coaching on which vehicles fit which customers' likely
  approvals.
- Timely close so the customer can leave with the vehicle.
- Fair split of blame when a deal falls apart.

### 10.3 Accounting

**F&I depends on Accounting for:**
- Bank feed / deposit reconciliation to confirm funding.
- Commission calculation and payout.
- Chargeback accounting when reversals hit.
- P&L visibility (F&I gross by manager, by lender, by product).
- Reserve accrual tracking (if lender pays reserve over time).
- Cash-flow reporting on BHPH portfolio (if applicable).

**Accounting depends on F&I for:**
- Deal-status truth (funded vs. pending vs. dead) for booking.
- Product-sale detail for revenue categorization.
- Reserve/discount detail for gross reconciliation.
- Chargeback prediction / accrual estimates.
- BHPH aging and delinquency data (if applicable).

### 10.4 Title / DMV work

**F&I depends on Title for:**
- Title in hand at time of sale.
- Trade title receipt after payoff.
- Timely lien perfection with the new lender.
- Out-of-state title handling.
- Temporary tag issuance and expiration tracking.
- Duplicate title applications when needed.

**Title depends on F&I for:**
- Timely notification of funded deals so titling work starts.
- Accurate customer information for state filings.
- Timely payoff on trades so lien releases can happen.

### 10.5 Compliance

**F&I depends on Compliance for:**
- Current program (WISP, ITPP) documentation and updates.
- Annual training completion.
- Adverse-action process oversight.
- Response guidance on customer complaints.
- Regulatory-change monitoring (state and federal).
- Vendor oversight (of software providers, credit bureau
  contracts, product providers).

**Compliance depends on F&I for:**
- Consistent execution of privacy, adverse-action, and menu
  procedures.
- Prompt reporting of red flags and incidents.
- Retention discipline (deal jackets, digital records).
- Cooperation with audits.

### 10.6 Customers

**F&I depends on Customers for:**
- Complete and truthful credit-app information.
- Timely production of stipulations.
- Insurance in place at delivery.
- Signed contracts and documents.
- Payments starting on time (avoiding FPD).

**Customers depend on F&I for:**
- Clear explanation of rates, fees, and products.
- Honest presentation of what they qualify for.
- Reasonable options across price / payment / down.
- Compliance with privacy expectations.
- Prompt communication of funding status and next steps.

### 10.7 Lenders

**F&I depends on Lenders for:**
- Current program grids and buy boxes.
- Prompt approval / decline responses.
- Clear stipulation lists at approval time.
- Consistent funding once packets are complete.
- Fair chargeback processes.
- Rep responsiveness on questions and exceptions.

**Lenders depend on F&I (dealer) for:**
- Clean deal submissions (not shopped, complete apps, accurate
  book-outs).
- Complete funding packets.
- Honest disclosure of customer circumstances.
- Portfolio quality (avoiding first-payment defaults, early
  payoffs, unwinds).
- Compliance with lender-specific program rules.
- Rep relationship maintenance.

---

## 11. Deferred Ideas

Ideas that surfaced during Finance research but belong to other
departments' future research. Recorded briefly here; not
expanded.

**Inventory** — Book-value source-of-truth strategy (JD Power vs
KBB vs MMR vs NADA integration). Recall status live-check. Photo
management for lender packet inclusion. Recon-cost impact on
per-unit pricing sensitivity.

**Sales** — Desking system (payment-first vs price-first
workflow), commissionable-gross calculation with F&I feed,
customer-profile collection standard for handoff quality.

**Accounting** — Reserve accrual model integration, BHPH portfolio
sub-ledger, chargeback provisioning against F&I gross,
per-lender profitability roll-up.

**Title** — ELT integration workflow, temp-tag lifecycle
tracking, trade-title receipt monitoring dashboard.

**Compliance** — Written Information Security Plan (WISP) tool,
Red Flags Rule detection workflow, Safeguards Rule audit trail,
per-state regulation registry, annual training tracking.

**Marketing** — Credit-tier-specific advertising and lead
routing, "as low as" payment ad compliance verification, buy-box
change alerts to marketing so campaigns can react to lender
program shifts.

**Customer / CRM** — Cross-visit customer identity (avoiding
duplicate app entries when the customer returns), delivery
walkthrough checklist, first-payment reminder outreach,
post-funding relationship maintenance (birthday, service intro,
referral requests).

**BHPH Operations** — In-house payment processing, delinquency
management, collections workflow, repossession workflow,
starter-interrupt device integration (where legally used),
portfolio aging analytics, side-note handling.

**Reporting / Intelligence** — Per-lender approval and funding
rates, per-vehicle-class approval patterns, F&I manager
performance metrics, per-customer-tier product attach rates,
chargeback trend analysis.

Each of the above deserves its own research session before
implementation. This document catches them so they aren't
forgotten; future department-specific research will develop them
properly.

---

## How to use this document

**For engineers and product people** starting Finance-related
work: read sections 1–8 (business) before opening any code editor
or design tool. The business language and the mental model in
those sections is what your work has to serve. Read section 10
(dependencies) to understand what your work will touch elsewhere.
Section 9 (automation opportunities) is where product ideas start
— but each opportunity should be developed into its own scoped
plan before implementation.

**For AI agents** starting a Finance-related session: this
document is source-of-truth for what F&I actually does. If
anything you're asked to do contradicts what's described here,
push back. If something you're asked to design isn't grounded in
one of the operational realities described here, ask why.

**For domain experts** reading this document: this is a snapshot
of common practice. Local variations, program-specific quirks,
and dealer-specific practices exist that this document doesn't
capture. Corrections and additions are welcome and expected as
the platform evolves.

**Update discipline.** This document is a living reference.
Update it when:
- Regulatory changes materially alter compliance requirements.
- Common lender program mechanics change (rare but does happen —
  the CFPB reserve caps, the Safeguards Rule updates).
- New F&I product categories become standard practice.
- Corrections are identified during implementation work.

Do **not** update this document with:
- Specific lender program numbers that will date (use ranges).
- Implementation designs (put those in dedicated plan docs).
- Legal advice (compliance section stays awareness-level).
- Specific software recommendations (put those in the
  implementation research for the relevant capability).

---

## Glossary — F&I terms used in this document

- **Advance / advance limit** — Maximum amount a lender will
  finance on a specific deal, usually expressed as a percentage
  of book value plus allowances for tax, doc, and products.
- **APR** — Annual Percentage Rate. The disclosed rate on the
  contract, inclusive of finance charges.
- **BHPH** — Buy Here Pay Here. In-house dealer financing.
- **Buy box** — A lender's stated willingness to buy a specific
  class of deal, expressed as a combination of tier, vehicle,
  LTV, PTI/DTI, term, and other variables.
- **Buy rate** — The lowest rate a lender will fund a deal at,
  before dealer markup.
- **Chargeback** — Lender-initiated reversal of dealer
  compensation on a funded deal that later underperforms.
- **Deal jacket** — The complete file of paperwork for a single
  deal, retained per compliance and audit requirements.
- **DTI** — Debt-to-income ratio. Sum of monthly debt obligations
  divided by gross monthly income.
- **ECOA / Reg B** — Equal Credit Opportunity Act and its
  implementing regulation. Federal fair-lending law.
- **ELT** — Electronic Lien and Title. State-level electronic
  title system.
- **F&I** — Finance and Insurance. The department that arranges
  financing and sells backend products.
- **FCRA / FACTA** — Fair Credit Reporting Act and Fair and
  Accurate Credit Transactions Act. Federal credit reporting law.
- **FICO** — Fair Isaac Corporation credit score. Multiple
  versions exist; FICO Auto Score 8 or 9 is common in auto finance.
- **First payment default (FPD)** — Customer misses their first
  monthly payment. Signals underwriting problem; triggers
  chargebacks.
- **Flat / flat fee** — Fixed dollar compensation to dealer per
  funded deal, independent of rate. Common at credit unions.
- **GAP** — Guaranteed Asset Protection. Product covering the
  gap between insurance payout and loan balance when a vehicle
  is totaled.
- **GLBA** — Gramm-Leach-Bliley Act. Federal financial privacy law.
- **ITPP** — Identity Theft Prevention Program. Required by Red
  Flags Rule.
- **LTV** — Loan-to-value. Amount financed divided by vehicle
  book value.
- **MMR** — Manheim Market Report. Wholesale auction pricing data.
- **NPI** — Non-public personal information. Regulated customer
  data under GLBA.
- **OFAC** — Office of Foreign Assets Control. Sanctions list
  screening.
- **Per-copy / PVR** — Per-vehicle retail. F&I gross per unit
  sold.
- **PTI** — Payment-to-income ratio. Monthly car payment divided
  by gross monthly income.
- **Reg Z** — Truth in Lending Act implementing regulation.
- **Reserve** — Dealer income from selling a loan at a rate
  higher than the lender's buy rate.
- **RISC** — Retail Installment Sale Contract. The core auto-loan
  document.
- **Safeguards Rule** — GLBA sub-rule requiring information
  security programs.
- **Sell rate** — Rate at which the dealer contracts the customer,
  potentially above the lender's buy rate.
- **Spot delivery** — Delivering a vehicle to the customer before
  full lender funding is secured.
- **Stipulation ("stip")** — Additional documentation or condition
  a lender requires before funding.
- **VSC** — Vehicle Service Contract. Aftermarket coverage for
  post-warranty mechanical repairs.
- **VOE** — Verification of Employment. Direct contact with the
  employer to confirm employment and income.
- **Waterfall** — Sequential lender submission strategy, from
  best-fit to fallback.
- **WISP** — Written Information Security Program. Required by
  Safeguards Rule.

---

## Related research

- `VEHICLE_CENTRIC_PIVOT.md` — Overall pivot plan; Finance
  research feeds Phase 0 (tenancy + auth) role definitions,
  Phase 7 (operational intelligence) F&I metrics, and eventual
  Sale/Delivery models (Phase 8).
- `INDEPENDENT_DEALER_PIVOT.md` — Established the indie-first
  scope this document uses.
- `CAPABILITY_MATRIX.md` — Current shipped capabilities;
  nothing in that matrix touches F&I operations yet. Everything
  in this document is greenfield relative to the current
  shipping product.

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

*End of Finance Department mapping.*
