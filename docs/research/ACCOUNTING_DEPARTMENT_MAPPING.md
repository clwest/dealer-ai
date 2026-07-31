---
title: "Accounting Department — Operational Mapping"
status: reference
type: research
generated: 2026-07-31
scope: Independent used-car dealership accounting operations
voice: Experienced dealership controller / office manager / owner
companion_docs:
  - "FINANCE_DEPARTMENT_MAPPING.md"
  - "VEHICLE_CENTRIC_PIVOT.md"
  - "INDEPENDENT_DEALER_PIVOT.md"
authoritative_for:
  - How accounting actually operates day-to-day at an independent used-car dealership
  - The reconciliation / validation logic that binds every operational event
not_authoritative_for:
  - Franchise factory-financial reporting (mentioned only for contrast)
  - GAAP or IFRS accounting theory
  - Tax advice (compliance section is awareness only)
  - Specific DMS software features (mentioned by category, not endorsed)
  - Any implementation design
---

# Accounting Department — Operational Mapping

> **What this is.** A research artifact documenting how the
> Accounting department (often just called "the office") of an
> independent used-car dealership actually operates. Written from
> the perspective of an experienced dealership controller or
> office manager — the person who reconciles everything and
> keeps the owner from finding out about problems the hard way.
>
> **Who this is for.** Anyone (engineer, agent, product person)
> touching accounting-related work in the Dealer AI Kit. Read
> this before opening a code editor or designing a UI. The
> mental model in these pages is what your work has to serve.
>
> **What this is NOT.** Not a bookkeeping textbook. Not a
> chart-of-accounts standard. Not tax advice. Not an implementation
> plan. Not a catalog of DMS features.
>
> **Core philosophy.** Accounting is not "bookkeeping" and it is
> not "recording transactions." **Accounting is the
> reconciliation layer that validates every operational event
> occurring throughout the dealership actually happened
> correctly.** Every dollar spent. Every dollar received. Every
> document. Every title. Every payoff. Every funding. Every
> vendor payment. Every stock number. **Everything must
> reconcile.** If it doesn't reconcile, either accounting missed
> something, operations missed something, or something is wrong.
> Accounting's job is to find out which one.

---

## Purpose & scope

The Dealer AI Kit's vehicle-centric pivot proposes a live
per-vehicle investment ledger that answers "what do we have in
this?" and a lifecycle machine that answers "what still needs to
happen?" (see `VEHICLE_CENTRIC_PIVOT.md`). Both of those
questions are, in existing dealership practice, **accounting
questions first** — the controller has been answering them (with
paper, spreadsheets, and the DMS) since long before software was
proposed for them.

Before any Accounting-adjacent architecture is designed, this
document preserves the operational knowledge an experienced
controller carries in their head about how money, documents, and
accountability actually move through a dealership.

**Scope boundary:** the *independent used-car dealer* scope
applies. That means:

- Small to mid-sized store (one to three office / accounting
  staff — sometimes exactly one, sometimes owner + bookkeeper).
- Mixed-make used inventory acquired through auctions, trades,
  wholesale, and private-party purchase.
- No OEM factory-financial reporting requirement.
- BHPH (buy-here-pay-here) portfolio may or may not exist —
  covered as a distinct sub-topic where relevant.
- Deals financed by a mix of prime, near-prime, subprime, credit
  union, and in-house (BHPH) lenders.
- Common DMS choices: Frazer, DealerCenter, Auto/Mate,
  DealerSocket DMS, ProMax, ABCoA, custom / spreadsheet-driven
  in the smallest shops. (Franchise-scale DMS — Reynolds, CDK,
  Dealertrack — mostly overkill for the segment.)

Where franchise practice differs materially, this document notes
the contrast briefly. It does not attempt to fully document
franchise controller work; that would be a separate research
effort with a much larger footprint (factory reporting, OEM
incentive accounting, warranty submission, etc.).

---

## Voice & caveats

Voice throughout is the third-person operational controller — the
person whose desk you don't want to leave a stack of unsigned
invoices on. Terminology used is what's actually said in the
office ("wash out the account," "the schedule is off,"
"unapplied cash," "the recap doesn't tie"). Formal names are
given alongside operator shorthand where useful.

**Numeric caveats.** Where specific dollars appear as examples,
they are illustrative. Real chart-of-account structures, tax
rates, retention periods, and reconciliation cadences vary by
DMS, state, and dealer preference. Treat this document as a
description of the *shape* of accounting work, not a source of
truth for specific figures.

**Compliance caveats.** The compliance section is
awareness-level only. Sales tax, 1099, IRS Form 8300, state
dealer reporting, and audit response all require an actual CPA
or dealer-experienced compliance advisor. Nothing here is legal
or tax advice.

---

## 1. The accounting spine — chart of accounts, schedules, and DMS

You can't understand what the controller does without
understanding the structure they work inside. This section is
foundational to every other section in the document.

### 1.1 Chart of Accounts (COA)

Every general ledger is organized by a chart of accounts — a
numbered list of "buckets" that transactions post to. Assets,
liabilities, equity, revenue, and expenses each get a range of
account numbers.

Indie dealer chart of accounts typically follows one of a few
common templates:

- **NADA / dealer-standard chart** — many small dealers inherit
  a variant of the NADA dealer chart-of-accounts. Six-digit
  account numbers organized as: 1-series assets, 2-series
  liabilities, 3-series equity, 4-series sales revenue, 5-series
  cost of sales, 6-series variable expense, 7-series semi-fixed,
  8-series fixed expense, 9-series other income/expense.
- **NCM composite / benchmarking chart** — used by dealers who
  benchmark against peer groups (mostly franchise, but some
  indie groups use it).
- **Custom / DMS-default chart** — some DMS platforms (Frazer,
  DealerCenter) ship an out-of-box chart the dealer customizes
  minimally.
- **QuickBooks-based chart** — smallest indies sometimes run
  the accounting side out of QuickBooks with a dealer-adapted
  chart, using their DMS only for inventory / deal entry and
  exporting to QB for financials.

The chart is not just organizational — it drives every financial
report. Miscoding a transaction to the wrong account produces
wrong financial statements. Consistent, disciplined coding is
one of the office manager's core responsibilities.

### 1.2 Department codes / cost centers

Beyond the base account number, most dealer charts use a
department suffix (or a separate department field) to distinguish:

- **New vehicle department** (indies without new inventory don't
  use this).
- **Used vehicle retail department** — the biggest indie
  department.
- **Used vehicle wholesale department** — for dealer-to-dealer
  and auction-out sales.
- **Service department** — if the store has a service shop
  (many indies don't; some do reconditioning in-house).
- **Parts department** — separate if the store sells parts
  externally (rare in indie).
- **Body shop** — separate if in-house (rare in indie).
- **F&I department** — some charts track F&I as its own
  department for gross-profit isolation.
- **BHPH department** — if the portfolio exists, sometimes
  segregated for gross and reserve analysis.

Franchise stores typically have a full department structure with
5–10 departments; indie stores may collapse everything into
"used retail" and "used wholesale" with the F&I gross broken out
by account rather than by department.

### 1.3 The schedule concept — subsidiary ledgers

The most important accounting concept in a dealership: **every
control account on the balance sheet is tied to a subsidiary
schedule that details what makes it up.**

Common schedules:

- **Used vehicle inventory schedule** — every used unit currently
  in stock, its cost, date acquired, cumulative recon, floor
  plan status, aging days. The sum of the schedule equals the
  used-inventory GL account. If they don't match, the schedule
  is "off" and the controller stops other work until it
  reconciles.
- **New vehicle inventory schedule** — same for new units (N/A
  for pure indie used).
- **Accounts receivable schedule** — every open receivable by
  customer/lender/product-company. Sum = A/R GL.
- **Accounts payable schedule** — every unpaid vendor invoice.
  Sum = A/P GL.
- **Contracts-in-transit / due-from-lender schedule** — every
  funded-pending deal awaiting lender deposit. Sum = the
  in-transit GL account.
- **Reserve receivable schedule** — every deal with expected
  future reserve income from the lender.
- **Warranty / product receivable schedule** — every product
  sale with commission still expected from the provider.
- **Trade payoff schedule** — every trade with a payoff owed to
  the trade lender (until title is released).
- **Prepaid expenses schedule** — insurance, licenses, prepaid
  advertising.
- **BHPH portfolio schedule** — every open contract, principal
  balance, days delinquent, next payment date (if applicable).
- **Vehicle jacket / vehicle detail** — the per-unit history of
  every cost, note, and adjustment. Not a schedule in the
  formal sense but functions like one at the unit level.

"The schedule is off" is a controller's daily anxiety. Any
transaction that hits a control account without a corresponding
subsidiary entry creates a mismatch. Finding and fixing
mismatches is a substantial share of accounting work.

### 1.4 The DMS (Dealer Management System)

The DMS is the operational backbone. It combines:

- Vehicle inventory records.
- Deal entry and printing.
- Customer records.
- The general ledger and schedules.
- Bank rec.
- A/P and A/R.
- Reporting.
- Sometimes: CRM, marketing, service scheduling, parts.

Indie DMS options range from lightweight (Frazer, DealerCenter,
Auto/Mate) to mid-market (DealerSocket, ProMax) to enterprise
(Reynolds, CDK — rarely used at pure indie). Some very small
shops run without a DMS at all — QuickBooks + spreadsheets +
manual paperwork.

**DMS as source of truth.** Almost every accounting reconciliation
starts from a DMS report. When the DMS is right, accounting is
right. When the DMS is wrong (data entry error, mid-month
adjustment, deleted record), accounting is wrong until the DMS
is corrected.

**DMS bypass problem.** When staff work *around* the DMS —
entering an invoice directly in QuickBooks, taking a cash payment
without a receipt in the DMS, adjusting inventory outside the
system — the DMS goes out of sync with reality. Reconciliation
tracks down and reverses these bypasses.

### 1.5 Cash vs accrual accounting

Most dealerships operate on **accrual accounting** — revenue is
recognized when earned (vehicle sold, even before funding
arrives) and expenses are recognized when incurred (recon
invoice received, even before it's paid). Accrual gives a truer
picture of dealership performance because vehicle sales and
funding are separated in time.

Some very small BHPH-only shops use **cash accounting** — record
transactions when cash actually changes hands — because the
installment-sale nature of BHPH creates deferred-gross-profit
complications under accrual that a small operator may not want
to track precisely. Tax treatment is separate and may follow
different rules (see §9).

**Modified cash / hybrid** setups exist: accrual for most
things but cash for specific accounts (like sales tax collected
or subscription-based service contracts).

### 1.6 The month, the trial balance, and the close

Accounting time runs on a monthly cadence:

- Days 1–25: transactions post continuously.
- Days 25–end-of-month: preparation for close (accruals reviewed,
  schedules tied out, floor plan reconciled).
- End of month: **month-end close** (see §8). Books "closed"
  when trial balance is balanced, schedules tie, financial
  statements are produced, and the owner has signed off.
- Days 1–10 of next month: prior month's close work continues
  (accruals booked, cutoff adjustments, tax return preparation).

**The trial balance** is the sum of all accounts at a point in
time. Debits must equal credits — if they don't, something is
posted wrong and has to be found and fixed. Modern DMS
generally prevents unbalanced entries at entry time, but manual
adjusting entries at close can still produce imbalances.

---

## 2. Vehicle Accounting — from acquisition to sale

The used vehicle inventory schedule is the largest, most-touched
schedule at an indie dealer. This section documents every kind
of transaction that touches a vehicle from the moment the dealer
buys it until the moment it's booked as sold.

### 2.1 Stock number assignment — the identity that makes accounting possible

The **stock number** is the unique identifier that links every
transaction on a vehicle back to the vehicle. It is assigned at
acquisition, before anything else can happen accounting-wise.

Stock number conventions vary. Common patterns:

- **Year-based sequence:** F-25-001, F-25-002 (first digit
  identifies year of acquisition).
- **Body-code prefix:** T25-001 for trucks, S25-001 for SUVs.
- **Source-based:** A-1234 for auction buys, T-1234 for trades,
  W-1234 for wholesale.
- **Sequential across the DMS:** just 12345, 12346, 12347.

**Once assigned, the stock number never changes.** Every future
transaction on the vehicle — recon invoices, floor plan
advances, sales, funding — references the stock number. The
stock number is what makes the vehicle jacket (§2.13) possible.

**VIN is separate.** VIN is the manufacturer identifier; stock
number is the dealer identifier. Both stay with the vehicle;
both are used for different purposes.

### 2.2 Purchase accounting

When a vehicle is acquired, its cost enters inventory. The
journal entry at the highest level:

```
Debit:  Used Vehicle Inventory (asset)
Credit: Cash / Floor Plan / Accounts Payable (source of funds)
```

**What "cost" includes** varies by acquisition source and dealer
policy. Some dealers include only the invoice price in the
initial cost; others include auction fees, transport, and even
initial recon in the initial cost. There is no universally
correct answer — what matters is *consistent application* so
that comparisons across units are apples-to-apples.

Common practice:

- **Auction acquisitions:** invoice price + auction buyer fees +
  arbitration fees are typically capitalized to the vehicle.
  Transportation is capitalized. Post-sale detail or
  transportation fees are capitalized.
- **Trade acquisitions:** the acquisition value ("ACV" —
  actual cash value, set by the used car manager or appraiser)
  is capitalized. Nothing else typically at acquisition.
- **Wholesale purchase:** invoice price + transportation
  capitalized.
- **Private party:** purchase price + any transportation
  capitalized.

**The "cost" at acquisition is only the beginning.** Recon costs
add to it (§2.7). The number that matters at sale time is the
*total* invested in the unit, not the acquisition-only cost.

### 2.3 Auction settlements

Auction accounting is a distinct discipline. Dealers who buy at
auction receive a **settlement statement** for each purchase,
typically including:

- Vehicle purchase price (the winning bid).
- **Buyer fees** — auction house fee, typically a sliding scale
  based on vehicle price.
- **Titling / documentation fees** — auction house prepares
  title work.
- **Post-sale inspection fees** if requested.
- **Arbitration fees** if applicable (buyer disputed a
  representation issue).
- **Transportation** if arranged through the auction.
- **Frame check / paint check / other inspection add-ons.**
- **Payment method fees** if applicable.

The settlement is what the auction bills. Payment is typically
by **auction floor plan** (see §2.5) — the auction has a
relationship with a flooring lender that pays them directly, and
the dealer's floor plan account gets debited.

For dealers paying cash at auction, an ACH or wire is required
by a stated deadline (often 48 hours after purchase); missing
the deadline incurs late fees or lockout from future auctions.

**Auction reconciliation** is a real workflow. Every purchased
vehicle should match a settlement line. Vehicles that appear on
settlements but weren't yours (data errors, wrong dealer code)
have to be disputed. Fees on settlements that seem wrong
(charged twice, wrong category) have to be disputed.

### 2.4 Transportation expenses

Transportation from auction (or wholesale seller, or trade
pickup) to the dealer's lot is a per-vehicle expense that
attaches to the specific unit.

Sources:
- **Auction-arranged transport** — billed on the settlement.
- **Third-party carriers** — dealer arranges directly, receives
  a separate invoice.
- **Dealer employees** driving vehicles back — mileage /
  employee time; usually not directly capitalized to unit but
  allocated as fixed operating expense.
- **Owner or family driving vehicles back** — often unrecorded;
  a real "hidden cost" of the operation.

For each unit, the controller has to identify the transport cost
and post it to the vehicle's cost.

### 2.5 Floor plan advances

Floor plan is the operating lifeline of most inventory-holding
dealers. A **floor plan** is a revolving line of credit
collateralized by the inventory. The lender pays the acquisition
seller directly; the dealer owes the lender the advance amount
plus interest until the vehicle sells.

Floor plan lenders in indie: Nextgear (Manheim), AFC, Westlake
Flooring, Ally Floorplan, local banks with dealer programs, some
specialty flooring lenders.

**Mechanics:**

- **Advance rate:** what percentage of the vehicle's value the
  floor plan will advance. Typically 100% of purchase price up
  to a book-value cap (KBB / Manheim MMR / dealer-negotiated
  formula), with sublimits for auction fees.
- **Interest rate:** variable, tied to prime or SOFR + a spread.
  Charged daily on outstanding balance.
- **Curtailment schedule:** the lender requires principal
  paydowns at specific ages (typical 30/60/90/120 day
  milestones). A vehicle at 90 days might require a 10%
  curtailment payment on the outstanding advance.
- **Floor plan audit:** the lender periodically (monthly to
  quarterly) visits the lot and physically inventories the
  vehicles. Any missing (sold-and-not-paid-off, missing without
  explanation, transferred without notice) unit triggers an
  **out-of-trust** notice — extremely serious, can freeze the
  line.
- **Payoff at sale:** when the vehicle is sold, the floor plan
  payoff (principal + accrued interest + curtailment shortfall)
  is due within a short window (typically 3–7 days) after
  vehicle sale.

**Accounting treatment:**

```
Purchase (advance drawn):
  Debit:  Used Vehicle Inventory
  Credit: Floor Plan Payable (liability)

Interest accrual (daily / monthly):
  Debit:  Floor Plan Interest Expense
  Credit: Floor Plan Payable (or Accrued Interest)

Sale payoff:
  Debit:  Floor Plan Payable
  Credit: Cash
```

The floor plan balance is a control account. Every vehicle
currently in inventory that was floor-planned should show a
per-unit balance on the floor plan schedule. Sum = floor plan
GL balance.

**Interest is a real per-unit cost.** A vehicle that sits 120
days at 8% floor-plan rate on a $15,000 advance has cost the
dealer nearly $400 in interest. Many dealers do not allocate
this back to the vehicle jacket — they treat it as
above-the-line expense — but it is a real per-unit hit to gross
profit.

### 2.6 Vendor invoices

Every service or good the dealer buys for a specific vehicle
generates a vendor invoice. Categories:

- **Parts** (mechanical parts for recon, tires, batteries,
  accessories).
- **Mechanical labor** (outside shop repair work).
- **Body shop / paint / paintless dent repair.**
- **Glass** (windshield, side glass replacement).
- **Detail** (wash, clean, condition).
- **Photography** (professional photos of the vehicle for
  listing).
- **Tire and wheel** (tire installation, alignment).
- **Transportation** (already covered in §2.4).
- **Fuel** (for test drives and delivery).
- **Miscellaneous** (keys, floor mats, air fresheners, small
  accessories).

Each invoice must be:

1. **Received** — either paper or electronic.
2. **Coded** — assigned to the specific vehicle (stock number)
   and expense category.
3. **Approved** — by whoever has authority (owner, GM, used-car
   manager) to approve the spend.
4. **Entered** in the DMS / accounting system.
5. **Paid** — via check, ACH, or credit card (§4).
6. **Filed** — retained for records (typically 7 years).

**Vehicle vs floor expense.** Vendor invoices for a specific
vehicle capitalize to that vehicle's cost. Vendor invoices for
the store overall (utilities, office supplies, general
advertising) expense to operating expense accounts. Coding
mistakes here — expensing what should be capitalized, or
capitalizing what should be expensed — distort both individual
vehicle profitability *and* period profit.

### 2.7 Recon expenses — the big pool

Reconditioning ("recon") is everything done to a vehicle to
prepare it for retail sale. Recon cost is the second-largest
component of total vehicle cost after acquisition.

Categories that typically accumulate to recon:

- Diagnostic labor.
- Mechanical repair labor and parts.
- Tires, brakes, battery, oil, fluids.
- Body work and paint.
- Glass.
- Interior work (upholstery repair, interior detail).
- Wheel repair and alignment.
- Exterior detail and paint correction.
- Photography.
- Vehicle-specific accessories (floor mats, keys, key fobs,
  cargo covers if missing).

**Recon accounting approaches** vary:

- **Direct capitalization:** each recon invoice is coded
  directly to the vehicle's inventory account, growing its
  cost. Simple; requires disciplined coding.
- **Recon holding account:** recon invoices post to a recon
  holding / work-in-process account and are transferred to
  vehicle cost when work is complete or at sale time. Cleaner
  for stores with heavy in-house shop work.
- **Recon reserve / average:** some dealers apply an *average*
  recon amount to each vehicle at acquisition and then reconcile
  actual vs. reserve at period end. Franchise dealers do this
  more often than indies.

The controller has to know which approach the store uses and
apply it consistently. Mid-year changes in approach make
year-over-year comparisons meaningless.

**In-house recon labor.** If the dealer has a service shop that
does recon in-house, the labor cost (technician wages) is
sometimes internally billed to the vehicle at a labor rate. This
is called an **internal work order** or **internal RO** and
creates a debit to vehicle cost and a credit to the service
department for revenue-crediting purposes. Franchise stores do
this heavily; indie stores that outsource all recon skip it.

### 2.8 Parts invoices

Parts specifically deserve their own paragraph because they can
be:

- **Vehicle-specific parts** — a starter motor for a specific
  used unit. Capitalize to vehicle.
- **General parts inventory** — a stock of common wear items
  (oil filters, wiper blades, brake pads) held for future use.
  Capitalize to parts inventory (a separate account), expensed
  to vehicle as used.
- **Consumables** — shop supplies (rags, cleaner, tape) that
  are expensed to shop supplies, not to vehicles.

Parts vendors typically bill weekly or monthly on statements
(§4.6). Reconciling the statement to individually received parts
requires matching invoices to statement lines.

### 2.9 Fuel expense

Fuel is a small but persistent per-vehicle expense. Sources:

- Fuel added at acquisition (some auctions include a small
  amount; sometimes tanks are near-empty).
- Fuel for test drives.
- Fuel for delivery to the customer (some dealers fill up as a
  courtesy).
- Fuel for internal movement of vehicles.

Some dealers capitalize per-vehicle fuel; most expense it as a
general operating expense with no per-vehicle allocation.
Consistent policy either way.

### 2.10 Miscellaneous vehicle expenses

The catch-all category for things that don't fit cleanly:

- Emissions / smog test (state-required in some states).
- Safety inspection (state-required in some states).
- VIN etch, tag, plate frame, dealer sticker.
- Second key programming.
- Missing owner's manual replacement.
- Vehicle-specific advertising (magazine listing, boosted social
  media post promoting one unit).
- Trip permits or temporary tags for movement.

Every one gets coded to the vehicle or to a general expense per
dealer policy.

### 2.11 Inventory adjustments

Sometimes the vehicle's book value on the schedule needs
adjusting. Examples:

- **Age-based write-down:** a vehicle sitting on the lot 120+
  days may be marked down to a realistic wholesale value if the
  dealer decides to wholesale it. The difference between book
  cost and adjusted value is a write-down expense.
- **Damage during possession:** vehicle damaged on the lot
  (customer, staff, storm). Insurance claim + adjustment.
- **Discovered condition issue:** vehicle discovered to have a
  branded title after acquisition (undisclosed at auction) or
  major mechanical problem. Adjustment down or wholesale
  disposition.
- **Reclassification:** vehicle moves from retail-intent to
  wholesale-intent. May move between schedules.
- **Cost correction:** invoice was miscoded to a different
  vehicle originally; correction moves cost from one vehicle to
  another.

Every adjustment must be documented — journal entry with
explanation, approval, source documents. Adjustments without
documentation are audit findings waiting to happen.

### 2.12 Vehicle cost tracking — the running total

At any moment, for any vehicle in inventory, the controller
should be able to answer: **"what have we got in this piece?"**

The answer is the sum of:

- Acquisition cost.
- Transportation.
- Auction / broker fees capitalized.
- All recon expenses posted to this unit.
- Parts capitalized to this unit.
- Fuel and miscellaneous capitalized.
- (Optionally) floor plan interest allocated.
- (Optionally) internal work at internal labor rates.

Less any adjustments or write-downs applied.

**This is the "current investment" number** that drives pricing,
aging decisions, and gross-profit projection. It is also the
answer the vehicle-centric pivot is proposing to surface in
real-time on a per-unit basis (see `VEHICLE_CENTRIC_PIVOT.md`
§Investment Ledger scope).

The DMS should be able to produce this per-unit total on demand.
When it can't, the controller falls back to spreadsheets and
manual invoice matching.

### 2.13 Vehicle jacket

A vehicle jacket is the complete per-unit file — physical
folder or digital equivalent. Contains:

- Purchase documents (auction settlement, trade appraisal, title
  transfer).
- Title itself (or reference to where it's stored).
- All vendor invoices related to the vehicle.
- Recon work orders.
- Photos.
- Any communications about the vehicle.
- The deal jacket (once sold — see §3.15).
- Sale documents (contract, funding paperwork).

Jackets are indexed by stock number. They are the physical /
digital source of truth if the DMS is ever questioned. Missing
paperwork in the jacket becomes an audit finding.

Modern practice: many dealers keep digital jackets in a document
management system with paper only for originals that must be
retained physically (titles, notarized documents).

### 2.14 Vehicle profitability calculation

At sale, the vehicle's gross profit is calculated:

```
Vehicle Gross = Sale Price - Total Cost
```

Where **Total Cost** is the sum from §2.12.

Adjustments to gross profit:

- Doc fee revenue (separated).
- Sales tax collected (liability, not revenue).
- Trade-in impact (trade-in overallowance vs actual acquisition
  value is a gross adjustment).
- F&I gross (product sales, reserve) is *separate* from vehicle
  gross — it belongs to F&I gross, not to vehicle gross.

**Per-copy** (vehicle) and **per-front-end** (vehicle only) and
**per-total** (vehicle + F&I) gross are all common metrics
watched at close.

### 2.15 Vehicle aging

Aging is days from acquisition to sale (or, for vehicles still
in stock, days from acquisition to today). Reported per unit and
aggregated.

Aging matters because:

- Floor plan interest is a per-day cost.
- Curtailment obligations kick in at defined ages.
- Consumer perception — a vehicle listed 90+ days looks stale.
- Depreciation of the vehicle itself over time.
- Store capital tied up in an unsold unit.

Accounting produces an **aging report** — vehicles categorized
by 0–30 days, 31–60, 61–90, 91–120, 121+ days. Vehicles in the
older buckets get management attention: reprice, wholesale,
promote.

### 2.16 Vehicle disposition — retail sale vs wholesale sale

Two ways a vehicle exits inventory:

- **Retail sale** — sold to a consumer. Full deal accounting
  applies (§3).
- **Wholesale sale** — sold to another dealer, an auction, or a
  wholesaler. Less deal complexity but different revenue
  classification (wholesale sales revenue account, wholesale
  gross usually lower and sometimes negative).

Occasionally:
- **Company vehicle** — moved to owner or manager as a company
  car. Reclassified out of retail inventory.
- **Total loss / theft** — insurance claim; unit removed from
  inventory when settlement received.
- **Return to previous owner** — rare; rescinded acquisition.

Every exit path has its own accounting entries. The point is:
the vehicle must *leave* inventory in an accountable way. No
"just disappeared" units.

---

## 3. Deal Accounting — from sale to fully closed

The deal recap is the accounting mirror of the F&I contract.
Every dollar the F&I manager writes on the contract has a
corresponding entry (or set of entries) the controller has to
book and eventually reconcile.

### 3.1 The deal recap

The **deal recap** is a one-page summary of a deal's finances,
produced by F&I at contract signing and reviewed by accounting
at posting.

Typical recap fields:

- Deal number, deal date, stock number, VIN.
- Customer name, address.
- F&I manager, sales manager, salesperson.
- Vehicle sale price.
- Trade allowance and actual trade acquisition value (ACV).
- Trade payoff amount and payoff lender.
- Cash down.
- Deferred / split down (if any).
- Tax collected.
- Doc fee.
- Registration / title fees.
- Tire tax / battery fee / other state pass-through fees.
- Product sales itemized (VSC cost / retail / provider; GAP
  same; T&W same; etc.).
- Amount financed.
- Lender name.
- Rate, term, first payment date.
- Reserve amount (dealer income).
- Front-end gross (vehicle) computed.
- Back-end gross (F&I) computed.
- Total gross.

The recap is the source document for the deal's journal entries.
It must be reviewed for accuracy before posting. Any recap
inconsistency (numbers don't add up, wrong customer, wrong
vehicle) has to be fixed before the deal posts.

### 3.2 Down payments

Cash down received at time of sale has an immediate journal
entry:

```
Debit:  Cash / Deposit Clearing
Credit: Cash Down (deal-specific account or subledger)
```

For deals not yet funded, the down is held against the deal.
Once funded, it's applied. For deals that fall through, the
down is refunded (see unwind, F&I §5.8).

**Deferred down** creates a receivable from the customer:

```
Debit:  Customer Receivable (deferred down)
Credit: Deferred Down Income (deal-specific)
```

The receivable is aged and pursued if the customer doesn't pay
by the agreed date.

### 3.3 Cash receipts

All cash coming into the dealership is logged into the DMS's
cash receipt module. Categorized:

- Down payments (per deal).
- Payoffs on trade receivables.
- Customer payments (on prior deals, BHPH, deferred down).
- Refunds returned (rare).
- Vendor rebates or credits received in cash.
- Other miscellaneous income (owner deposits, misc sales).

At the end of each day, the cash drawer is counted, matched to
the DMS cash receipts total, and deposited (§7.1). Any variance
gets investigated.

### 3.4 Trade payoff verification

When a customer trades a vehicle with a lien, the dealer takes
ownership of the trade but assumes obligation for the trade
payoff. Between contract signing and payoff being sent to the
trade lender, the dealer has:

- **Trade acquired** — trade asset now belongs to the dealer.
- **Trade payoff owed** — liability to the trade lender.

Journal entries at contract:

```
Debit:  Used Vehicle Inventory (trade acquisition value)
Debit:  Trade Payoff Payable (payoff amount) [if payoff > ACV]
Credit: Trade Overallowance / Trade Contra (if applicable)

or

Debit:  Used Vehicle Inventory (trade acquisition value)
Credit: Trade Equity Applied to Sale (if payoff < ACV)
Credit: Trade Payoff Payable (payoff amount)
```

The payoff is sent to the trade lender within days (waiting on
funding sometimes; some dealers pay off from operating funds and
recover on funding). The trade lender releases the title. **The
title release is the accounting close on the trade.** Until the
title arrives, the trade payoff is an open receivable in the
form of a title-in-transit obligation.

**Payoff variance.** The 10-day payoff quoted at deal time is
sometimes different from the actual payoff sent. Interest accrues
day-by-day; extra days between quote and payoff mean more owed.
Variance is either:

- Absorbed by the dealer (small variances, "cost of doing
  business").
- Charged back to the customer (dealer collects a check for the
  difference).
- Disputed with the trade lender (if variance is unreasonable).

### 3.5 Lender funding

When the F&I manager submits a funded deal packet to the lender,
the store expects a deposit within 24-72 hours (electronic
lenders) or 5-10 business days (paper / slower lenders).

Accounting tracks the expectation via the **contracts-in-transit
(CIT) account** — sometimes called "due from lender," "funding
pending," or "deal in transit."

Journal entry at contract:

```
Debit:  Contracts in Transit (asset, subledger by deal)
Credit: Used Vehicle Sales Revenue
Credit: Sales Tax Payable
Credit: Doc Fee Revenue
Credit: Product Sales Revenue (VSC, GAP, T&W, etc.)
Credit: Reserve Receivable (dealer reserve income)
Credit: Trade Payoff Payable (if applicable)
```

(Simplified — real journal has 10-30 lines depending on deal
complexity.)

When funding arrives:

```
Debit:  Cash
Credit: Contracts in Transit
```

The CIT schedule ages every open funded-pending deal. Deals over
5-7 days without funding get controller attention. Deals over 15
days are red-alert — either the packet is incomplete or the
lender declined post-delivery.

### 3.6 Reserve receivables

Reserve income comes from the lender either upfront (with the
funding) or streamed over the life of the loan. Depends on the
lender program.

**Upfront reserve** — the funding deposit includes the reserve
amount. Reserve income is recognized on the deal at funding.

**Streamed reserve** — the lender pays a monthly reserve
statement covering multiple deals over multiple months. The store
maintains a **reserve receivable schedule** — every deal with
expected future reserve payments and the amount expected.

Reserve accrual issues:
- The full life-of-loan reserve is often booked as income at
  time of sale (accrual), but with an offsetting **chargeback
  reserve** that estimates future chargebacks (early payoffs,
  first-payment defaults). GAAP treatment varies; small dealers
  often skip the chargeback reserve and just book the actuals as
  they hit.
- Reserve statements from the lender have to be reconciled
  monthly against the reserve receivable schedule — payments
  received vs. expected.

### 3.7 Warranty / VSC receivables

When a customer buys a VSC (vehicle service contract), the
dealer:

- Collected the retail price from the customer (financed into
  the loan or paid in cash).
- Owes the VSC provider the wholesale cost.
- Keeps the difference (retail - cost) as commission income.

Payment to the provider happens either:

- **Deducted from funding** — the lender remits the VSC premium
  directly to the provider, sending the store net of premium.
  Most modern practice.
- **Store remits** — store receives full funding, then writes a
  check to the provider each month for the sum of that month's
  sold VSCs. Less common now.

Either way, the store's commission on the VSC is receivable from
the provider (or already retained, depending on flow). The
**warranty / product receivable schedule** tracks these.

Chargeback exposure exists here — customer cancels the VSC or
pays off the loan early, provider claws back the commission
pro-rata.

### 3.8 GAP receivables

Same pattern as VSC. GAP premium collected, wholesale owed to
provider, commission retained.

Chargeback exposure larger for GAP because early payoffs and
refis are frequent in the first year of subprime loans.

### 3.9 Product cancellations

When a customer cancels a product (VSC, GAP, T&W, maintenance)
mid-term:

- Provider refunds pro-rata to the lender (if financed) or the
  customer (if paid in cash).
- Store's commission is charged back pro-rata.

Accounting entry (product commission chargeback):

```
Debit:  Product Commission Chargeback Expense (or reversal of
        original commission)
Credit: Due to Provider / Accounts Payable
```

Cancellations trickle in constantly. Every cancellation reduces
prior period gross. Some dealers accrue a **cancellation
reserve** to smooth the impact.

### 3.10 Chargebacks

Chargebacks are lender-initiated reversals of reserve income when
a deal underperforms (first payment default, early payoff, deal
rescission).

Chargeback entry:

```
Debit:  Reserve Chargeback Expense
Credit: Cash / Due from Lender (if the lender deducts from a
        future funding)
```

Chargeback exposure per lender is tracked. Some dealers accrue a
**chargeback reserve** at time of sale to spread the impact.

### 3.11 Deal corrections

Errors happen. A wrong customer address is caught. A miscoded
product. A missing signature discovered late. Corrections are:

- **Contract addendum** — small clarification, both parties
  sign, addendum added to jacket. No accounting change usually.
- **Full re-contract** — new contract signed, old contract
  voided. Accounting reverses the original entries and re-posts
  the corrected entries. Sometimes requires the lender to
  re-approve.
- **Journal-entry-only correction** — accounting fixes a coding
  error without changing the customer-facing contract.

Each correction creates an audit trail: who caught it, when it
was corrected, what changed, who approved the change. Corrections
made silently without documentation are audit findings.

### 3.12 Funding reconciliation

The daily / weekly process of matching lender deposits to CIT
schedule entries. Every deposit should:

- Match a specific deal on the CIT schedule (or match multiple
  deals in a batch).
- Be for the expected amount (or explain the variance:
  discount, product premium, first-payment holdback, etc.).
- Zero out the CIT entry.

Common variance sources:
- **Discount fees** — the lender deducts a discount from the
  advertised advance (subprime lenders). Amount should match
  the recap.
- **Product premiums deducted** — lender remits directly to
  product provider.
- **First-payment holdback** — some subprime lenders hold back
  a portion of funding until the customer makes their first
  payment.
- **Auction / floor plan payoff** — some lenders wire the
  amount net of a floor-plan payoff (rare but happens).
- **Bank fee** — small variances due to wire fees or ACH
  processing fees.

Unreconciled variances get investigated within 24-48 hours.

### 3.13 Sales tax accounting

When the dealer collects sales tax on a vehicle, the tax is a
**liability** — money the dealer holds temporarily on behalf of
the state.

```
At sale:
  Debit:  Cash / Contracts in Transit (tax collected)
  Credit: Sales Tax Payable (liability)

At tax filing:
  Debit:  Sales Tax Payable
  Credit: Cash (remittance to state)
```

Sales tax is **never revenue.** Miscoding sales tax as revenue
inflates income and creates a tax reporting problem. The Sales
Tax Payable account must reconcile to what the state expects
each filing period.

State-specific complications:

- Some states charge sales tax on the sale price; some on
  price-less-trade.
- Some states have local (city, county) taxes that add on top.
- Some states have tire fees, battery fees, luxury fees — each
  its own account.
- Nexus rules for cross-border sales (customer from another
  state buying vehicle to register in another state).
- Some states allow the customer to pay sales tax directly to
  the DMV (dealer doesn't collect).

The state's monthly / quarterly sales tax return has to
reconcile to the Sales Tax Payable schedule.

### 3.14 Deal booked / deal closed

A deal moves through accounting states:

1. **Deal entered** — F&I entered it in the DMS after
   contract signing.
2. **Deal posted** — controller reviewed the recap, adjusted if
   needed, posted to the GL. Contract now in the CIT schedule.
3. **Deal funded** — lender deposit received and applied.
   Vehicle removed from inventory. F&I commission generated.
4. **Deal closed** — all product commissions received or
   accrued, all follow-up items handled, deal moved from active
   to archived.
5. **Deal in retention** — kept in retention per record-retention
   policy (typically 7 years).

Chargebacks and product cancellations reopen "closed" deals for
adjustments.

### 3.15 Deal jacket

Analogous to vehicle jacket but for the deal side. Contains:

- Signed retail installment contract.
- Signed credit application.
- Product forms (VSC, GAP, T&W agreements).
- Odometer disclosure.
- Buyer's Guide.
- Menu / product-offering documentation.
- Insurance verification.
- Copy of driver's license, other stips.
- Lender approval printout.
- Funding confirmation.
- Any communication about the deal.

Deal jackets get retained per record-retention policy (§9.5).
Missing documents in the deal jacket create funding delays
(§F&I) and audit exposure.

### 3.16 BHPH portfolio accounting (if applicable)

If the store carries in-house BHPH paper, this is a whole
sub-department of accounting.

**Installment sale method (for tax):** IRS allows dealers to
elect installment-sale treatment for BHPH portfolios, meaning
gross profit is recognized as cash is collected rather than at
sale. This defers taxable income but complicates
book-vs-tax reconciliation. Book (accrual) and tax (cash /
installment) methods diverge.

**Contract receivable schedule:** every open BHPH contract, its
current principal balance, next payment date, days delinquent,
last-payment date. This schedule *is* the BHPH portfolio.

**Interest income:** interest accrued on outstanding principal.
Recorded as income daily / monthly.

**Deferred gross profit** (if using installment method): the
unrecognized gross profit that accompanies the outstanding
principal balance.

**Reserve for uncollectible accounts:** estimated portfolio
losses; charged to expense periodically.

**Repo inventory:** vehicles repossessed and awaiting
disposition. Repo cost (repo agent fee, transport, cleanup)
capitalizes to the repo unit; unit is then either resold retail
(back to active inventory) or wholesaled (loss recognition).

**Charge-off:** when a customer's account is deemed
uncollectible, the receivable is charged off. The unit becomes
a total loss (unless repossessed).

**Portfolio value:** total outstanding principal is a real
balance-sheet asset. Some BHPH stores sell portfolios or use them
as collateral for their own borrowing.

BHPH accounting is complicated enough that some indie stores
outsource it to specialty BHPH accountants or use dedicated BHPH
software modules on top of the general DMS.

---

## 4. Accounts Payable

### 4.1 Vendor setup and validation

Every new vendor must be set up in the DMS / accounting system
with:

- Legal name and DBA (doing-business-as) name.
- Address (for check mailing / 1099).
- Federal tax ID (EIN or SSN) via W-9 form.
- Contact person, phone, email.
- Payment terms (net 30, net 15, 2/10 net 30, etc.).
- Preferred payment method (check, ACH, credit card).
- Default expense account or category.
- 1099 flag (yes/no; category if yes).

**W-9 collection** should happen before the first invoice is
paid. Many stores make the mistake of paying an invoice first
and chasing the W-9 later — vendors are cooperative before
payment, uncooperative after.

**Duplicate vendor risk.** The same vendor added twice (typo in
name, different DBA vs legal name) causes duplicated statements,
unreconciled totals, and 1099 confusion. Vendor cleanup is a
recurring task.

### 4.2 Invoice receipt

Vendor invoices arrive:

- **In the mail** — physical paper, still common.
- **Via email** — PDF attachments; some vendors email directly to
  an AP inbox.
- **Vendor portal** — vendor uploads to their own portal, dealer
  logs in to retrieve.
- **In person** — vendor drops off an invoice with the office.
- **Auto-attached to purchase** — some vendors (auction, floor
  plan) generate invoices as part of the acquisition/settlement
  workflow.

Invoices should be date-stamped upon receipt and logged in an
inbound-invoice queue.

### 4.3 Invoice coding and approval

Each invoice must be:

- **Coded** — assigned to the right GL account. If vehicle-specific,
  attached to the stock number. If general operating, assigned
  to the right operating expense account (utilities, office,
  advertising, etc.).
- **Approved** — the person with spending authority for that
  category signs off. Often the used-car manager approves recon
  invoices; the owner or GM approves everything else.

**Segregation of duties.** In a well-run store, the person who
approves an invoice is *not* the person who prepares the check
and *not* the person who signs the check. Fraud risk drops when
two or three people touch each payment.

**Approval memory.** Owners commonly approve invoices verbally
during the day and expect the office to know. Written approvals
(initial on invoice, signed approval form, digital approval
workflow) protect everyone.

### 4.4 Payment workflow

Payments run on a schedule. Common patterns:

- **Weekly check run** — most common. All approved invoices due
  or discountable this week get paid Thursday or Friday.
- **Biweekly** — smaller stores.
- **Immediate for critical items** — floor plan payoffs (§2.5),
  auction settlements (deadline-driven), utilities on threat of
  shutoff.
- **Monthly for statements** — parts vendors, some service
  vendors bill on monthly statements.

Payment methods:

- **Paper check** — traditional, still most common. Printed
  from DMS or manually written.
- **ACH** — electronic bank transfer. Faster; increasingly used
  for regular vendors.
- **Wire transfer** — for time-critical / large payments (floor
  plan payoffs, auction settlements). Bank fees apply.
- **Credit card / debit card** — small purchases, some vendors.
  Watch for card fees vs. discounts captured.
- **Petty cash** — small in-person cash payments. Petty cash is
  reconciled weekly.

### 4.5 Approval and signature authority

Check signers are usually the owner or a designated officer.
Larger dealers may have dual-signature requirements above a
threshold ($5,000, $10,000). Wire transfers typically require
owner authorization for each wire.

**Owner controls.** The owner of a small indie dealership often
personally signs every check. This is a fraud control (owner
sees every payment) and a cash flow control (owner sees every
outflow). It's also a bottleneck when the owner is unavailable.

### 4.6 Vendor statement reconciliation

Vendors bill either:

- **Per invoice** — every purchase becomes an invoice.
- **On monthly statement** — the vendor sends a monthly
  statement summarizing all invoices for the month.

For statement-based vendors, reconciliation compares:

- The vendor's statement.
- The dealer's record of invoices received and payments made.

Discrepancies (invoice on statement never received, invoice paid
but not credited on statement, credit memo missing) get raised
with the vendor. Long-standing discrepancies become bad debt or
lost credits.

### 4.7 Discount capture

Many vendors offer early-pay discounts: "2/10 net 30" means 2%
off if paid within 10 days, full amount due at 30. The office
must:

- Recognize the discount terms on the invoice.
- Pay within the discount window to capture the savings.
- Record the discount as **purchase discount income** (or
  reduce the expense).

Missed discounts are foregone cash. Stores with weekly check
runs typically capture discounts naturally; stores with
biweekly or monthly cadence miss them.

### 4.8 Prepaid expenses

Some expenses are paid in advance for future periods:

- **Insurance premiums** paid annually.
- **License and permit renewals** paid annually.
- **Prepaid advertising** for future publication.
- **Software subscriptions** paid quarterly or annually.
- **Prepaid maintenance contracts**.

Payment creates a prepaid asset which is then amortized to
expense over the period covered.

```
Payment:
  Debit:  Prepaid Insurance (asset)
  Credit: Cash

Monthly amortization:
  Debit:  Insurance Expense
  Credit: Prepaid Insurance
```

The prepaid schedule tracks each prepaid item and its
amortization.

### 4.9 1099 tracking

Federal law requires 1099-NEC or 1099-MISC forms be sent to
non-corporate vendors paid $600 or more in a calendar year for
services (not products).

The 1099 threshold check runs continuously. Vendors are
categorized:

- **1099 vendor** — non-corporate (individuals, LLCs taxed as
  partnerships / disregarded). W-9 shows applicable box checked.
- **Non-1099 vendor** — corporations (C-Corp, S-Corp), typically
  exempt from 1099 for most payment types.
- **Product vendor** — payments for products only, generally not
  reportable on 1099.

Annual January 1099 mailing / e-filing is a compliance
obligation. Missing 1099s can result in penalties per form. Wrong
1099s (wrong amount, wrong TIN) can result in penalties per
form.

### 4.10 Vendor disputes and credit memos

Sometimes a vendor bills wrong. Common:

- **Wrong quantity** — invoiced 20 tires, received 18.
- **Wrong price** — invoiced at $200/hr, quoted $175/hr.
- **Wrong vehicle** — invoice references stock number not
  actually worked on.
- **Duplicate invoice** — same work billed twice.
- **Product return** — parts returned but not credited.

Disputes get raised with the vendor. Credit memos, when
received, reduce the vendor payable. Unresolved disputes become
either bad debt written off or lingering AR/AP items.

---

## 5. Accounts Receivable

Money owed *to* the dealership. Multiple sources, multiple aging
concerns.

### 5.1 Categories of receivables

- **Contracts in transit** — funded-pending deals waiting for
  lender deposit. Largest and most-watched.
- **Reserve receivables** — future reserve payments from
  lenders.
- **Warranty / product receivables** — commissions expected
  from product providers.
- **Trade payoff titles in transit** — trade lender owes title
  after payoff sent.
- **Customer receivables** — deferred down payments, service
  charges, misc customer balances.
- **BHPH portfolio receivables** — the whole portfolio (§3.16).
- **Wholesale receivables** — money owed from wholesale
  customers (other dealers) for units sold to them.
- **Dealer trade receivables** — money owed from dealer-to-dealer
  trades.
- **Insurance receivables** — pending insurance settlements for
  vehicles damaged / stolen in possession.
- **Miscellaneous / other** — refunds, rebates, one-off items.

### 5.2 In-transit / pending accounts

**Contracts in transit (CIT)** is the biggest single receivable
in most indie stores. It represents funded-pending deals.
Discussed in §3.5.

CIT ages daily. Deals over 5-7 days without funding are yellow.
Over 15 days, red — the deal may have been declined post-delivery
and the store may face an unwind or spot-delivery reversal.

### 5.3 Aging monitoring

Every receivable has an age. Standard AR aging buckets:

- 0-30 days (current).
- 31-60 days (past due).
- 61-90 days (aging).
- 91-120 days (concerning).
- 121+ days (collection or write-off territory).

The aging report is a weekly (sometimes daily) accounting output.
Items in older buckets get management attention.

### 5.4 Follow-up processes

Each receivable category has its own follow-up:

- **CIT over 5 days** — accounting calls the lender's funding
  desk to check status. Stips outstanding? Packet issue?
  Declined post-delivery?
- **Reserve receivable per statement variance** — accounting
  contacts lender rep to reconcile.
- **Product receivable over 60 days** — accounting contacts
  provider.
- **Trade title over 30 days** — accounting contacts trade
  lender for title release status.
- **Customer receivable past due** — customer contact:
  reminder, then demand, then collection escalation.
- **BHPH delinquency** — collection department contacts customer;
  repo consideration at longer delinquency.
- **Wholesale receivable past due** — dealer or auction contact.

### 5.5 Bad debt recognition

When a receivable becomes uncollectible, it must be written off:

```
Debit:  Bad Debt Expense
Credit: Accounts Receivable (specific item)
```

For BHPH, this often means charging off a customer contract:

```
Debit:  Reserve for Uncollectible Accounts
Credit: Contracts Receivable (BHPH)
```

Bad debt policies vary. Some dealers write off after 180 days of
no contact; some hold longer; some use collection agencies to
attempt recovery before writing off.

### 5.6 Reserve receivables from lenders

As discussed in §3.6. The schedule tracks per-deal expected
reserve income and matches monthly statements to the schedule.
Variances get resolved with the lender rep.

### 5.7 Chargeback exposure tracking

Every open reserve or product receivable carries chargeback
exposure — the possibility that future defaults or cancellations
will reverse income already accrued.

Sophisticated accounting maintains a **chargeback reserve** — an
estimated liability based on historical chargeback rates. This
smooths income recognition.

Simpler accounting books chargebacks as they hit, accepting
lumpier income patterns.

---

## 6. Titles & Registration

Title work is one of the most operationally sensitive areas of
the office. Missing or delayed titles freeze sales, create funding
delays, and trigger customer complaints.

### 6.1 Title receipt at purchase

Every acquired vehicle must arrive with (or have arranged for)
its title. Sources:

- **Auction:** title mails from the auction 5-15 business days
  after purchase. Some auctions ELT-transfer to the dealer's
  electronic title account.
- **Trade:** trade title comes from the payoff lender after
  payoff is sent and processed. Timeline 5-15 business days
  after payoff.
- **Wholesale:** title accompanies the vehicle (or arrives soon
  after) from the seller.
- **Private party:** title signed over at purchase.

The receiving log tracks every acquired vehicle: title expected
by date X, title actually received on date Y.

### 6.2 Title storage

Physical titles are kept in a fireproof safe or locked cabinet in
the office. Access is restricted (owner + office manager +
titles clerk if separate role). Loss of a physical title requires
duplicate application (§6.11) — weeks of delay and possible
customer impact if the vehicle is already sold.

ELT-state titles (§6.7) are held electronically by the state.
The DMS or the dealer's ELT portal shows the electronic title
status.

### 6.3 Title verification (chain of title)

Before selling a vehicle, the title should be verified for:

- **Chain of title** — clear signature chain from previous owner
  to dealer.
- **Odometer disclosure** — federal odometer statement completed
  by prior owner.
- **Brands** — flags on the title indicating salvage, rebuilt,
  flood, lemon-law buyback, junk. Branded titles severely limit
  fundability and resale value.
- **Liens** — any active liens must be released before sale.

Undisclosed brands discovered after acquisition are a
disaster case: vehicle may be untitleable, unsellable, or
require aggressive wholesale disposition.

### 6.4 Lien payoff on trades

Trade vehicles typically have an existing lien. Payoff process:

1. Get **10-day payoff quote** from the trade lender at contract
   signing.
2. Send payoff to the trade lender (check, wire, or ACH). Timing
   varies — some dealers pay off from operating cash immediately
   at contract; others wait for funding on the new deal.
3. Trade lender processes payoff (1-5 days).
4. Trade lender releases title (paper: mails to dealer; ELT:
   updates electronic record).
5. Dealer receives title, verifies release, files in vehicle
   jacket / registers new ownership.

**Payoff variance** (§3.4) is a common friction point. Wire
timing, weekend delays, and lender processing all contribute to
variance.

### 6.5 Lien release from selling lender

When the dealer sells a financed vehicle, the *new* lender
becomes the lienholder on the new title. Title work must reflect
this:

- **Paper title** — dealer submits title work to state DMV; new
  title issued with new lender listed. Timeline 4-12 weeks
  depending on state.
- **ELT** — dealer transfers electronic title control to the
  new lender at time of sale (same day or next).

The new lender does not release the title (or ELT) until the
loan is paid off — years later.

### 6.6 Registration paperwork for the buyer

At sale, the dealer processes the buyer's registration:

- Application for title in buyer's name (with lender as
  lienholder if financed).
- Application for license plate / registration.
- Sales tax collection and payment to state.
- Temporary tag issuance (if the state allows).

The registration paperwork bundle varies by state. Some states
require the dealer to submit; some allow the buyer to submit;
some require joint submission.

### 6.7 ELT (Electronic Lien and Title)

Most states now use ELT for lienholder titling. Benefits:

- No physical title storage risk.
- Faster lien perfection (electronic vs. paper mail).
- Reduced fraud (no forged paper titles).
- Faster payoff and release.

Not all states are ELT; some are ELT-optional; some ELT-mandatory
for certain lenders. Multi-state operators must know their
states' rules.

### 6.8 Out-of-state titles

When a customer from another state buys a vehicle for
out-of-state registration, or when a dealer buys a vehicle from
an out-of-state source, additional complications:

- **Nexus** — sales tax rules for cross-border sales vary.
- **Title mailing time** — cross-state title mailing adds days.
- **State-specific title forms** — receiving state may require
  its own paperwork.
- **Reciprocity** — some states have reciprocal recognition of
  each other's titles; some don't.

Every state's DMV / SoS handles this differently. Multi-state
dealers develop expertise; occasional cross-border deals require
research each time.

### 6.9 Temporary tags

Most states allow a temporary tag ("temp tag," "paper plate")
for a defined period (30-90 days) between sale and permanent
registration. The dealer issues the temp tag.

Temp tag inventory has to be tracked:

- Sequential numbering, tied to sold vehicles.
- Expiration date (drives when permanent registration must be
  in place).
- State-specific format and issuance rules.
- Compliance reporting to state (some states require monthly
  temp-tag reports).

Expired temp tags on customer vehicles are the customer's
problem legally, but they're often the dealership's problem
politically ("my temp tag expired and I still don't have plates
from you!").

### 6.10 DMV interaction

Regular DMV contact:

- Weekly or biweekly title submission runs.
- Monthly dealer reports (some states).
- Annual dealer license renewal.
- Salesperson license maintenance (some states).
- Audit response.

DMV interaction is often slow. Getting a straight answer requires
knowing which clerk to ask. Multi-state dealers deal with
multiple DMVs simultaneously.

### 6.11 Missing titles / duplicate title applications

When a title is missing:

- **Never arrived from auction/trade** — chase the source.
  Timeline can stretch weeks.
- **Lost in dealer possession** — apply for duplicate. State
  timelines 2-8 weeks depending on state; some require notary,
  affidavit of loss, or additional documentation.
- **Wrong state title on newly-acquired vehicle** — coordinate
  transfer with source state and receiving state.

Vehicles with title problems get held out of retail sale. If
already sold, the customer's registration is delayed until title
work completes — leading to expired temp tags and customer
complaints.

### 6.12 State-specific requirements

Every state's title system is slightly different:

- ELT vs paper.
- Odometer disclosure format.
- Notary requirements.
- Salvage / rebuilt title procedures.
- Temp tag rules.
- Dealer license requirements.
- Salesperson license requirements.
- Reporting cadence.
- Fee schedules.
- Reciprocity agreements.

Multi-state operators build state-specific playbooks.
Single-state indies know their state cold but may not know
others' rules.

### 6.13 Title aging report

The critical accounting report for titles:

- **Titles expected but not received** — vehicles acquired
  without title yet in hand.
- **Titles in dealer possession but sale pending** — retail-ready
  titles waiting for a buyer.
- **Titles submitted to state for customer** — post-sale
  registration in process.
- **Titles overdue at state** — customer registration should be
  complete by now but isn't.

Aging drives escalation. Titles over 60 days without resolution
get owner attention.

### 6.14 Title chargeback exposure

Some lenders will chargeback dealer if title work is incomplete
after a defined window (60-90 days post-sale). Store loses
funding, has to unwind or re-fund the deal.

Multi-state / multi-lienholder / paper-title states have the
highest title chargeback exposure. ELT states have lower.

---

## 7. Bank Reconciliation

Bank reconciliation is where accounting proves the DMS matches
the real world.

### 7.1 Daily deposits

Cash and check receipts collected each day should be:

- Counted and reconciled against DMS cash receipts total.
- Prepared for deposit (deposit slip, calculator tape, receipt
  detail).
- Deposited at the bank (in-person, night drop, or via mobile
  deposit for checks).
- Deposit receipt kept with the daily cash record.

Variances between DMS receipts and actual cash counted are
investigated same-day if possible. Persistent variances trigger
process review — misidentified receipts, miscount, missing
receipt, or theft.

### 7.2 Cash reconciliation

The daily cash reconciliation:

```
Beginning cash + Cash receipts - Cash disbursements - Deposits
= Ending cash on hand
```

The physical count at end of day should match. Discrepancies
same-day investigation.

Petty cash is separately reconciled weekly.

### 7.3 Credit card reconciliation

Credit card deposits from the merchant processor:

- Typically batch daily.
- Deposit is *net of fees* (or gross with fees deducted
  separately).
- Deposit typically hits the bank 1-2 business days after the
  batch date.

Reconciling credit card activity involves matching:

- The processor's daily batch report to internal credit card
  receipts.
- The deposit to the batch (net of fees).
- The monthly processor statement to the cumulative daily
  activity.

Chargebacks and refunds hit the merchant account like any other
adjustment.

### 7.4 ACH transactions

ACH (Automated Clearing House) is used for:

- **Incoming:** lender funding, customer BHPH payments, product
  provider commissions.
- **Outgoing:** payroll, vendor payments, floor plan payoffs
  and interest, tax payments.

ACH batches multiple times daily. Timing and settlement (typically
1-2 business days) has to be understood so the accounting timing
matches bank posting.

### 7.5 Wire transfers

Wire transfers are used for time-critical / large payments:

- Floor plan payoffs on sold vehicles.
- Auction settlements.
- Large vendor payments.
- Loan payments.
- Owner distributions or capital movement.

Wires carry bank fees (typically $20-50 outgoing, less for
incoming). Wire logs and confirmations kept.

### 7.6 Floor plan reconciliation

Floor plan reconciliation is a distinct process because of the
schedule (§2.5) and the per-unit tie:

- Every vehicle currently floor-planned should appear on the
  floor plan schedule at its current balance.
- Every advance drawn should appear.
- Every payoff sent should appear.
- Interest accrued should tie to interest expense recorded.
- Total schedule = floor plan payable GL balance.

Floor plan lenders provide their own statements. Reconciliation:
dealer's floor plan schedule vs. lender's statement.

**Floor plan audit** (§2.5) is the lender's physical verification
of what's on the lot. Missed audit units (**out-of-trust**) are
serious — can freeze the floor plan line, damage the lender
relationship, and require immediate payoff of the missed unit.

### 7.7 Bank statement reconciliation

Monthly bank statement rec:

- Reconciled cash balance = statement balance + deposits in
  transit - outstanding checks +/- adjusting items.
- Every deposit on the statement should match a DMS deposit.
- Every check on the statement should match a DMS-recorded
  check.
- ACH activity on the statement should match ACH records.
- Interest earned added to income.
- Bank fees expensed.

Unreconciled items get investigated. Common issues: check
outstanding for months (payee never cashed), missing deposit
record (DMS entry missed), bank error (rare but happens),
duplicate posting.

### 7.8 Multi-account reconciliation

Most dealers have multiple bank accounts:

- **Operating account** — day-to-day cash.
- **Payroll account** — funded on payroll dates.
- **Sales tax account** — sometimes segregated (best practice
  in some states).
- **Trust / customer deposit account** — for held customer funds
  before deal funding.
- **BHPH collection account** — if applicable, segregated from
  operating.
- **Floor plan lender account** — some floor plan lenders
  require a dedicated account for their advances and payoffs.

Each account reconciled independently. Inter-account transfers
tracked and reconciled.

### 7.9 Fraud and error detection

Bank rec is the primary fraud detection tool. Watch for:

- Unauthorized checks (fabricated payees).
- Duplicate deposits (potential fraud or duplicate posting).
- ACH transactions the store didn't originate.
- Wire transfers to unknown destinations.
- Login activity on the online banking portal at unusual times.
- Missing deposits (theft in transit).

Monthly rec is table stakes; daily online banking review is
better; positive-pay services (bank verifies checks against
issued check list before honoring) is best.

---

## 8. Month-End Operations

Month-end close is the sacred deadline. Everything else stops.

### 8.1 The close calendar

Common close timeline (day = business day of the new month):

- **Day -3 to -1:** cutoff communications to departments —
  "get me your invoices and receipts by end of month."
- **Day 1:** initial trial balance run. Unposted transactions
  investigated.
- **Days 1-3:** invoices dated in the prior month but received
  in the new month posted with prior-month date. Accruals for
  expenses incurred but not yet invoiced.
- **Days 2-5:** schedules reconciled — inventory, floor plan,
  A/R, A/P, CIT, warranty receivables.
- **Days 3-7:** adjusting entries booked. Depreciation. Interest
  accrual. Deferred/prepaid amortization.
- **Days 5-10:** financial statements produced. Reviewed by owner.
- **Days 5-15:** sales tax return prepared and filed.
- **Days 10-15:** month "closed" in the DMS. New month
  transactions still post, but prior month locked.

Small-shop reality: one office person doing all of this
frequently means close runs longer.

### 8.2 Inventory reconciliation

**Physical inventory** — someone physically walks the lot,
counts vehicles, records VINs and stock numbers.

**Book inventory** — the DMS inventory schedule.

Match physical to book. Missing (vehicle should be there but
isn't) or found (vehicle on lot but not on schedule) items get
investigated. Common causes:

- Recent sale not yet posted.
- Recent acquisition not yet entered.
- Vehicle moved off-site (recon vendor, owner's home, another
  lot) without notification.
- Data entry error on original stock assignment.

Physical inventory is typically done monthly at close, sometimes
weekly, always at year-end for tax purposes.

### 8.3 Vehicle schedules

The used vehicle inventory schedule is reconciled:

- Total of schedule = used inventory GL account.
- Every unit on the schedule matches physical inventory (from
  §8.2).
- Every unit's cost matches DMS unit records.
- Recon-in-process (if using a holding account) reconciled to
  general ledger.

Off-schedule variances are the controller's headache. They
happen and they must be resolved before close.

### 8.4 Floor plan reconciliation

Reconcile per §7.6. Every floor-planned vehicle traced from
purchase to current balance to (if applicable) payoff or
curtailment. Interest expense for the month tied out.

### 8.5 Expense reconciliation

Every operating expense account reviewed for:

- **Completeness** — all invoices received and posted?
- **Coding accuracy** — anything posted to wrong account?
- **Trending** — is this month's expense in line with typical?
  Sudden jumps flagged.
- **Cutoff** — invoices for services performed this month but
  invoiced next month should be accrued.

### 8.6 Accruals

Common month-end accruals:

- **Utility bills** received after close but for prior-month
  service.
- **Payroll accrual** for hours worked in the prior month but
  paid in the current month.
- **Interest accrual** on floor plan (if not daily).
- **Vendor invoice accruals** for services performed but not
  yet billed.
- **Chargeback reserve** (if using) for future chargeback
  exposure.
- **Bad debt accrual** for AR write-downs.

Accruals reverse automatically in the following month (or are
reversed manually) when the actual invoice hits.

### 8.7 Deferrals

Common deferrals:

- **Prepaid insurance / advertising / subscriptions** —
  monthly amortization.
- **Deferred product revenue** — for products where the store
  hasn't fully earned the commission yet (some product
  arrangements).
- **Deferred gross profit** on BHPH portfolio (installment
  method).

### 8.8 Financial statements

At close, financial statements produced:

- **Income statement / profit & loss (P&L)** — revenue and
  expenses for the month and year-to-date.
- **Balance sheet** — assets, liabilities, and equity as of
  month-end.
- **Cash flow statement** — sources and uses of cash for the
  month.
- **Sales / gross summary** — units sold, gross per unit,
  front-end gross, F&I gross, total gross.
- **Aging reports** — inventory, A/R, A/P.
- **Departmental P&L** — per-department profitability if
  department-tracked.

Owner review. Comparison to budget, prior month, prior year.
Explanations for variances.

### 8.9 Tax reporting

Sales tax return (state and local) filed monthly or quarterly.
Reconciles to Sales Tax Payable schedule (§3.13).

Federal quarterly tax deposits (income tax, payroll tax).
Annual returns (federal income, state income, unemployment,
1099s).

### 8.10 Owner review and sign-off

The owner (or CFO / controller if separate) reviews the closed
financials, asks questions, requests corrections if any. Once
approved, the month is done from the owner's perspective and
strategic decisions (pricing, marketing, inventory buying) get
made based on the financials.

### 8.11 Year-end

Year-end close is like month-end but larger:

- Full physical inventory (required for tax purposes).
- All schedules reconciled meticulously.
- Depreciation of fixed assets calculated.
- Owner distributions calculated.
- Tax return preparation (typically with external CPA).
- W-2s and 1099s issued.
- Retirement plan contributions calculated.
- Prior-year audit preparation if applicable.

Year-end close can extend into the following month. Some dealers
formally close year-end in February or March.

---

## 9. Compliance (awareness, not legal advice)

Accounting-adjacent compliance obligations. This section flags
what exists; a real compliance program requires a CPA and, for
some items, a compliance attorney.

### 9.1 Sales tax

The largest compliance area for dealer accounting. Every dealer
collecting sales tax on vehicle sales must:

- Register with the state's tax authority.
- Collect tax at the point of sale per state rules.
- Hold collected tax in Sales Tax Payable.
- File a periodic (monthly or quarterly) sales tax return.
- Remit collected tax to the state.
- Handle exempt sales (dealer-to-dealer, out-of-state, etc.)
  per state rules.

State-specific complications abound:

- Tax base (sale price vs. price-less-trade).
- Local jurisdiction taxes.
- Reciprocity between states.
- Documentation for exempt sales.
- Filing frequency.
- Filing forms and format.
- E-file requirements.
- Sales tax on aftermarket products (VSC, GAP) — sometimes
  taxable, sometimes not.

Missed sales tax returns generate penalties, interest, and
eventually revocation of the dealer license.

### 9.2 Use tax

Purchases made by the dealer without paying sales tax (from
out-of-state vendors, or on wholesale exemption certificates)
may owe **use tax** to the dealer's home state. Use tax reporting
is often on the same return as sales tax.

### 9.3 State dealer reporting

Some states require monthly dealer reports beyond sales tax:

- **Vehicle sales reports** — every sold vehicle reported by
  VIN.
- **Temp tag reports** — every temp tag issued.
- **Dealer license status** — reporting on license conditions.
- **Consumer complaint reporting** — reporting on complaints
  received.

Cadence, format, and content vary widely by state.

### 9.4 Federal reporting

- **1099 forms** (§4.9) — annual January mailing.
- **W-2 forms** — annual January for employees.
- **Form 8300** — required for cash transactions over $10,000.
  Bank-secrecy law. Applies to any single or aggregated
  transaction. Filed within 15 days of transaction. Customer
  notified.
- **Quarterly federal tax deposits** — income tax withholding,
  Social Security, Medicare, FUTA.
- **Annual federal income tax return** — corporate, S-corp,
  LLC, or Schedule C depending on entity structure.
- **State income tax returns** — same or separate from federal.

### 9.5 Record retention

Federal and state rules require retention of dealer records for
periods typically 3-7 years, some indefinitely:

- **Deal jackets** — 5-7 years typical after deal close.
- **Vehicle jackets** — 5-7 years after vehicle sold.
- **Bank statements and reconciliations** — 7 years.
- **Sales tax records** — 7 years typical (state-specific).
- **Payroll records** — 7 years typical.
- **W-9 and 1099 records** — 4 years after tax filing.
- **Corporate records** (incorporation, minutes, resolutions)
  — indefinite.
- **Titles and title work** — indefinite for permanent records.

Digital retention subject to secure storage requirements
(privacy law, industry practice). Paper retention subject to
shredding on disposal (Disposal Rule under FACTA).

### 9.6 Financial controls

Controls that reduce fraud and error risk:

- **Segregation of duties** — different people approve,
  prepare, and sign checks.
- **Authorization limits** — spending above defined amounts
  requires additional approval.
- **Reconciliation discipline** — daily / monthly reconciliations
  performed by a person independent of the transaction
  originator.
- **Physical security** — locked cabinets for cash, checks,
  titles.
- **System security** — role-based DMS access, password
  discipline, MFA on financial systems.
- **Positive pay** for check accounts.
- **Wire transfer callback verification** — outgoing wires
  confirmed via a callback to a known contact.
- **Owner review of financials** — regular, not perfunctory.

Small stores struggle with segregation of duties because there
aren't enough people. Compensating controls (owner review,
external CPA review, occasional external audit) mitigate.

### 9.7 Audit preparation

Different types of audits:

- **External CPA audit or review** — annual, if required by
  bank covenants or owner preference. Reviewed financials
  vs. audited financials.
- **State DMV audit** — inspection of dealer license
  compliance, title records, temp tag reports.
- **State sales tax audit** — sales tax return accuracy over a
  period.
- **IRS audit** — federal tax return examination.
- **Floor plan audit** — physical vehicle inventory verification
  (§2.5).
- **Product provider audit** — VSC/GAP providers occasionally
  audit dealer records for chargeback justification.

Preparation for any audit means having records organized,
reconciliations documented, and answers ready. Chaotic records
extend audit duration, increase adjustments, and raise repeat-audit
probability.

### 9.8 BHPH-specific compliance

If the store has a BHPH portfolio:

- **Truth in Lending** on the retail installment contracts.
- **State usury caps** on rates.
- **Collection practices** governed by state and federal law
  (FDCPA if using outside collectors).
- **Repo law** compliance — notice requirements, redemption
  rights, sale procedures, surplus / deficiency handling.
- **Starter-interrupt device** regulations where applicable
  (some states restrict; some require notice).
- **GPS tracking** disclosure requirements.
- **Installment sale accounting method** (§3.16) for tax.

---

## 10. Pain Points

Repetitive friction accounting personnel experience daily. This
section documents; does not propose fixes.

### 10.1 Matching invoices to purchase orders / receiving

If the store uses purchase orders (many indies don't formally),
matching invoice to PO to received-goods is a three-way
reconciliation. Discrepancies (over-shipment, under-shipment,
substituted parts, price variances) get investigated.

For stores without formal POs, the office just receives invoices
and has to figure out what they're for by asking the manager who
ordered.

### 10.2 Tracking missing funding

Every day, checking the CIT schedule against bank deposits.
Missing funding after 5+ days becomes phone calls to the lender's
funding desk. Chasing stips. Following up on packet completeness.

### 10.3 Chasing titles

Every day, checking title receipts against expected titles.
Following up with auctions ("where's the title for the Explorer
I bought three weeks ago?"). Following up with trade lenders
("we sent payoff on the Malibu 12 days ago — where's the
title?"). Applying for duplicates when originals are lost.

### 10.4 Reconciling vendor payments

Vendor statements come monthly. Statement lists 40 invoices;
office paid 38 of them (2 disputed); statement's ending balance
doesn't match office's records because of a credit memo the
office logged but the vendor forgot to apply. Multiply by 30
vendors. Every month.

### 10.5 Following up on stale receivables

Aging report shows a $2,400 warranty commission unpaid for 90
days. Contact the provider. They say they never received the
paperwork. Office resends. Provider processes and pays. Sometimes.

Some stale receivables become bad debt. Every one has to be
worked before write-off.

### 10.6 Correcting deal jackets after posting

F&I posted a deal with a coding error. The deal has funded, but
now needs correction — wrong sales tax, wrong product code, wrong
lender. Correcting means reversing part of the entry and
re-posting. All while the original documents stay in the jacket
with a correcting addendum.

### 10.7 Duplicate data entry

The deal is entered in the DMS. Then the funding data is
manually entered into the bank rec. Then the reserve receivable
is manually added to the reserve schedule. Then the product
commission is manually added to the product receivable schedule.
Then the deal is manually added to the daily sales report.
Every entry is an opportunity for error.

### 10.8 Manual reporting

The DMS produces standard reports. The owner wants a
non-standard report — sales gross by salesperson by lender by
month. Office pulls the data, manipulates in Excel, formats,
sends. Every month.

### 10.9 Waiting on bank feeds

Online banking feed updates once or twice daily. Time-sensitive
reconciliations (has that wire hit yet?) require phone calls to
the bank when the feed is stale.

### 10.10 Unapplied cash

Money hit the bank but the office can't figure out what deal or
customer it applies to. Sits in a suspense account ("unapplied
cash") until identified. Meanwhile the corresponding open deal
looks unfunded, or the customer looks like they haven't paid.
Unapplied cash aging is a real problem.

### 10.11 Reconciling schedules to control accounts

Schedule total = GL control account balance is the constant
requirement. When they don't match, the controller stops
everything else to find the variance. It's always something
mundane — a missed journal entry, a duplicate posting, a coding
error — and it always takes 30-90 minutes to find.

### 10.12 Reserve receivable estimates vs actuals

Reserve accrued at time of sale is an estimate (based on the
lender's reserve program). Actual reserve received may differ.
Reconciling estimate to actual, month over month, per lender, is
tedious.

### 10.13 Chargeback true-ups

Every product cancellation, every early payoff, every FPD
generates a chargeback. Each has to be:

- Recognized (usually via lender statement or product provider
  notice).
- Reversed in the schedule.
- Charged to the appropriate F&I manager's chargeback account.
- Reflected in the manager's commission calculation.
- Communicated to the manager.

None of it is hard individually. All of it is tedious.

### 10.14 Cross-department information hunting

"Whose deal is this funding for?" "Which vehicle did this recon
invoice apply to?" "Did we ever pay this vendor?" "Is this
customer on a payment plan?" Accounting is the department
everyone else asks. Answers require lookup across DMS, files,
paper, memory.

### 10.15 Waiting on owner approvals

Owner needs to sign checks. Owner needs to approve an unusual
invoice. Owner needs to review a schedule variance. Owner is
selling a car and unreachable for two hours. Office work backs
up.

### 10.16 Compliance workload

Every close comes with sales tax return prep. Every year comes
with 1099s and W-2s. Every audit request pulls hours of
document assembly. Every state form update requires re-learning
what to file. The compliance work is non-negotiable and grows.

---

## 11. Operational Decisions

Decisions accounting personnel make many times per day.

### 11.1 Has this vehicle been fully costed?

Every recon invoice received: is this the last one, or is more
coming? Every vehicle in the pre-sale pipeline: is the cost
complete enough to price accurately?

### 11.2 Is this deal funded?

Check the bank feed, check the CIT schedule, look at the
funding-pending list, cross-reference lender portals. Answer
sales' or accounting-junior's "did it fund" question.

### 11.3 Has this vendor been paid?

Look at check register, look at ACH sent, look at vendor
statement, look at outstanding invoice queue.

### 11.4 Is this invoice accurate?

Compare invoice to service performed, quoted price, delivered
quantity. Cross-check with whoever ordered.

### 11.5 Has this title arrived?

Check the physical title cabinet, check ELT status, check the
title-in-transit log, call the trade lender or auction if
overdue.

### 11.6 Should this expense be capitalized or expensed?

Vehicle-specific parts / labor → capitalize. Store overhead →
expense. Judgment call for gray-area items.

### 11.7 Is this charge legitimate?

Unexpected credit card charge, unexplained ACH debit, unusual
vendor bill. Investigate before paying / disputing.

### 11.8 Which financial reports need attention right now?

Aging report red items. Bank rec variances. Schedule
mismatches. Sales tax return due. All competing for time.

### 11.9 Which schedules are out of balance?

Daily quick-check on the biggest schedules. Any mismatch drives
immediate investigation.

### 11.10 Do I have enough cash for this week's obligations?

Payroll due Friday, vendor check run Thursday, floor plan
interest hitting Monday. Compare against expected deposits
(fundings, customer payments). Escalate to owner if
insufficient.

### 11.11 Do I have enough floor plan headroom?

Every acquisition draws floor plan. Every sale pays it down.
Balance headroom against upcoming auction attendance.

### 11.12 Which vendor discounts should I capture?

Weekly review of open invoices with discount terms. Pay early
if cash flow permits; capture the savings.

### 11.13 Is this journal entry documented?

Any adjusting entry needs a source and an approver. Undocumented
entries are audit findings.

### 11.14 Should I close the month now or wait for one more day?

Cutoff decisions. If waiting a day picks up 3 expected invoices,
maybe worth it. If waiting delays the owner review, maybe not.

### 11.15 Is this receivable becoming bad debt?

Judgment call. Continue chasing or write off. Impact on gross,
impact on customer relationship, impact on reporting.

### 11.16 Which owner decisions need surfacing?

Cash flow tight this week. Vendor threatens shutoff. Insurance
premium spiked. Owner needs to know but shouldn't drown in
detail.

---

## 12. Automation Opportunities

Where repetitive administrative work lives. This is opportunity
identification, not solution design.

### 12.1 Three-way match on invoices

For invoiced purchases with a purchase order and receiving
record, automated three-way match saves manual comparison of PO
+ receiving + invoice.

### 12.2 Missing document tracking

Titles in transit, funding pending, stips outstanding — a
document-aging dashboard that surfaces overdue items reduces
manual daily checking.

### 12.3 Funding monitoring — automatic bank-feed match to CIT

Bank feed vs. expected fundings, auto-matched where amounts and
timing align, flagged where they don't. Reduces manual daily
reconciliation.

### 12.4 Vendor payment discount timing

Alerting when a discount window is closing on an approved invoice.
Small dollars per invoice; meaningful annualized.

### 12.5 Title status tracking

Every acquired vehicle title expected-arrival-date, actual
arrival tracked, escalation on overdue. Reduces manual daily
title chasing.

### 12.6 Daily reconciliation report

Aggregated snapshot: bank rec status, cash count vs. DMS, CIT
aging, A/R aging, A/P aging, schedule variances. Reduces the
"what needs my attention" mental scan.

### 12.7 Outstanding receivable aging with escalation

Rules-based aging escalation ("A/R over 60 days → email
reminder to customer; over 90 → escalate to manager"). Reduces
manual follow-up cadence maintenance.

### 12.8 Vehicle jacket costing completeness check

Given a vehicle at a stage (recon complete, or pending sale),
verify all expected costs are in — recon, transportation,
photography, etc. Flag units where cost may be incomplete.

### 12.9 Floor plan curtailment reminders

Every floor-planned vehicle's next curtailment date; alerts as
they approach. Reduces manual calendar tracking.

### 12.10 Sales tax accrual auto-calculation

Real-time running total of Sales Tax Payable, cross-referenced
to expected filing. Reduces month-end scramble.

### 12.11 1099 running totals

Per-vendor cumulative annual payment, flagged as approaching /
exceeding the $600 threshold. Reduces January 1099 preparation
frenzy.

### 12.12 Schedule-to-GL reconciliation auto-tie

For each control account, real-time comparison of subsidiary
schedule total to GL balance. Immediate variance detection.

### 12.13 Unapplied cash aging with escalation

Unidentified deposits older than X days get flagged for
investigation. Reduces silent accumulation.

### 12.14 Deal-recap completeness check

At post-time, verify recap has all required fields, all products
have provider codes, all totals cross-foot. Reduces post-posting
correction burden.

### 12.15 Bank reconciliation auto-match candidates

Bank statement lines auto-matched to DMS entries where amount +
date + counterparty align. Manual review only for unmatched
items.

### 12.16 Chargeback prediction

Deals with characteristics historically predictive of FPD or
early payoff surfaced to F&I and accounting for extra attention
before the chargeback hits.

### 12.17 Vendor statement auto-match

Vendor's monthly statement lines matched to office records;
variances surfaced.

Each is a candidate for future dedicated planning; the list
represents the highest-friction, highest-repetition items.

---

## 13. Cross-Department Dependencies

### 13.1 Vehicle Acquisition & Recon

**Accounting depends on Acquisition & Recon for:**
- Accurate stock number assignment at acquisition.
- Timely handoff of auction settlement / purchase document.
- Vehicle-specific expense identification (which recon invoice
  belongs to which stock).
- Notification of vehicle location changes (moved to body shop,
  moved off-lot).
- Notification of completed recon so vehicle is ready for retail.
- Notification of adjustments needed (damage, condition
  discovery).

**Acquisition & Recon depends on Accounting for:**
- Approved vendor list and payment terms.
- Confirmation that vendor is set up for payment.
- Timely payment to vendors (relationship maintenance).
- Per-unit cost visibility (are we upside-down on this piece?).
- Floor plan headroom (can we buy more this week?).
- Historical cost data (average recon by category).

### 13.2 Finance / F&I

**Accounting depends on F&I for:**
- Accurate deal recap for posting.
- Complete deal jacket for retention.
- Product provider codes and commission structure.
- Timely notification of contract corrections or re-writes.
- Chargeback advance notice when known.
- Communication about spot-delivery status (deals delivered
  before full funding).

**F&I depends on Accounting for:**
- Confirmed funding status (feeds F&I commission calculation).
- Reserve receivable tracking (F&I sees reserve as it comes
  in vs. estimated).
- Chargeback reversals reflected in commission true-ups.
- Product provider communication (missing commission chase).
- Bank rec confirmation of unusual deposits or variances.

### 13.3 Sales

**Accounting depends on Sales for:**
- Accurate customer information collected on the deal.
- Trade information (year/make/model/VIN/payoff/lender) at
  deal writeup.
- Documentation received at delivery (insurance, ID, POI/POR).
- Notification of any customer commitments (deferred down,
  refund promises, pickup arrangements).

**Sales depends on Accounting for:**
- Confirmed booked-and-funded status (drives commission).
- Confirmation that customer's registration is progressing
  (customer complaints route via Sales).
- Communication of any deal-jacket completeness issues to
  address.

### 13.4 Vendors

**Accounting depends on Vendors for:**
- Accurate, timely invoicing.
- Proper vendor setup (W-9 up front).
- Monthly statement matching to office records.
- Prompt credit memos on disputes.
- Reasonable payment terms.
- Compliance with 1099 reporting on their side.

**Vendors depend on Accounting for:**
- Timely payment per terms.
- Prompt communication on any disputes.
- Accurate 1099s issued (vendors need them for their own tax
  reporting).
- Reliable point of contact.

### 13.5 Lenders

**Accounting depends on Lenders for:**
- Prompt funding after packet completeness.
- Accurate reserve statements matching per-deal expectations.
- Prompt chargeback documentation with reason and amount.
- Clear program terms (advance rates, discount fees, reserve
  caps).
- Rep responsiveness on questions.

**Lenders depend on Accounting for:**
- Complete packets promptly.
- Accurate deal information.
- Compliance with lender-specific program rules.
- Portfolio quality (low FPD, low early payoff, low unwind).
- Reserve dispute discipline (only disputing when justified).

### 13.6 Customers

**Accounting depends on Customers for:**
- Down payments received per contract terms.
- Deferred down payments made on schedule.
- Insurance in place and communicated to accounting.
- Notification of address changes (for BHPH or ongoing
  relationships).
- Payments per contract (BHPH).

**Customers depend on Accounting for:**
- Accurate paperwork (deal jacket, contract, registration).
- Timely temp tag issuance and permanent tag processing.
- Correct sales tax collection and remittance.
- Refund of unearned product premiums on cancellation.
- Refund of down payment if deal is unwound.

### 13.7 Government agencies

**Accounting depends on Government for:**
- Clear state tax rules and forms.
- Timely DMV processing of title work.
- Timely responses to license and registration inquiries.
- Audit notice with reasonable time to prepare.

**Government depends on Accounting for:**
- Accurate sales tax collected and remitted.
- Timely returns filed.
- Cooperation with audits.
- Compliance with all reporting cadences.
- Payment of all obligations (income tax, payroll tax,
  unemployment).

### 13.8 Bank / floor plan lender

**Accounting depends on Bank/Floor for:**
- Prompt clearing of deposits.
- Accurate statement of activity.
- Reasonable holds on new deposits.
- Timely posting of ACH / wire activity.
- Rate-competitive terms on floor plan.
- Reasonable notice on program changes.

**Bank/Floor depends on Accounting for:**
- Accurate floor plan reporting.
- Prompt curtailments.
- Prompt payoffs on sold units.
- Compliance with covenants (financial ratios, reporting).
- Truthfulness during audits.

### 13.9 Payroll

**Accounting depends on Payroll for:**
- Accurate hours worked (for hourly staff).
- Accurate commission calculations (from F&I gross, sales
  gross).
- Timely delivery of paychecks or ACH files.
- Timely tax deposits.

**Payroll depends on Accounting for:**
- Confirmed deal-funded status (drives commission).
- Chargeback data (drives commission reversals).
- Approval of manual adjustments.
- Cash position for payroll funding.

---

## 14. Deferred Ideas

Ideas that surfaced during Accounting research but belong to
other departments' future research. Recorded briefly here; not
expanded.

**Vehicle Acquisition & Recon** — Vendor performance metrics
(turn time, cost variance), auction ROI by source, book-value
data-source integration, recon workflow state machine.

**Finance / F&I** — Chargeback prediction models, product
provider reconciliation dashboard, deal-recap validation at
signing time.

**Sales** — Salesperson gross calculation, commission plan
integration, per-salesperson-per-lender reporting, delivery
checklist workflow.

**Titles / DMV Operations** — Title workflow dashboard, ELT
integration, temp-tag lifecycle tracking, per-state playbook
system, duplicate-title application workflow.

**Compliance** — Written information security plan (WISP)
tooling, red-flags detection workflow, safeguards audit trail,
per-state reporting calendar, records-retention policy engine,
audit-preparation packet builder.

**Payroll / Commissions** — Commission calculation engine,
chargeback true-up automation, tip and manual adjustment
handling, integration with tax deposit and W-2/1099 workflows.

**HR / Benefits** — Employee onboarding, benefits enrollment,
paid-time-off tracking, workers' comp reporting.

**Fixed Asset Accounting** — Building, equipment, computers,
software licenses, capitalization thresholds, depreciation
schedules, disposal accounting.

**Owner Reporting / KPI Dashboards** — Executive-level metrics
(units sold, PVR, gross, net, cash position, floor plan
utilization). Belongs in the executive intelligence layer.

**Multi-Lot / Multi-Entity Consolidation** — If owner has more
than one store, consolidated reporting, inter-company
eliminations, allocated shared expenses.

**Bank Relationship Management** — Line of credit renewals,
floor plan renewals, banking-terms comparison shopping.

**Marketing / Co-op Accounting** — Mostly franchise-specific
(OEM co-op advertising reimbursement); some indie co-op
programs exist with product providers and warranty companies.

**BHPH Portfolio Operations** — Collections workflow,
delinquency management, repo workflow, GPS/starter-interrupt
device integration, portfolio-level analytics, side notes.

**Cash Flow Forecasting** — Beyond the daily "do I have cash for
tomorrow" question, structured 30/60/90-day cash forecasts based
on expected fundings, customer payments, and known obligations.

**Reporting / Intelligence** — Per-vendor cost trends,
per-lender funding-cycle-time patterns, per-department gross
trends, seasonal analysis, comparable-period analysis.

Each of the above deserves its own research session before
implementation. This document catches them so they aren't
forgotten; future department-specific research will develop
them.

---

## How to use this document

**For engineers and product people** starting Accounting-related
work: read sections 1–3 first (the accounting spine, vehicle
accounting, deal accounting). Those sections carry the mental
model everything else builds on. Read section 13 (dependencies)
before designing anything that connects to another department's
data. Section 12 (automation opportunities) is where product
ideas start — but each opportunity should be developed into its
own scoped plan before implementation.

**For AI agents** starting an Accounting-related session: this
document is source-of-truth for what accounting actually does. If
anything you're asked to do contradicts what's described here,
push back. If a proposed feature bypasses reconciliation
discipline (schedule tie-outs, month-end close cadence,
segregation of duties), flag it — that discipline is the whole
point of the department.

**For domain experts** reading this document: this is a snapshot
of common indie practice. State-specific and DMS-specific
variations exist that this document doesn't fully capture.
Corrections and additions are welcome and expected as the
platform evolves.

**Update discipline.** Update this document when:
- Regulatory changes materially alter compliance requirements
  (e.g., new sales tax rules, Form 8300 threshold changes).
- Common accounting practice shifts (e.g., adoption of new
  installment-sales tax rules for BHPH).
- Common DMS practice shifts.
- Corrections are identified during implementation work.

Do **not** update this document with:
- Software implementation designs (put those in dedicated plan
  docs).
- Legal or tax advice (compliance section stays awareness-level).
- Specific state or DMS-specific detail that varies too much
  to be authoritative in a general document.

---

## Glossary — accounting terms used in this document

- **A/P** — Accounts Payable. Money the dealer owes vendors.
- **A/R** — Accounts Receivable. Money owed to the dealer.
- **Accrual accounting** — Recognize revenue when earned, expenses
  when incurred, regardless of when cash changes hands.
- **ACH** — Automated Clearing House. Electronic bank transfer
  system for batched payments.
- **ACV** — Actual Cash Value. Trade acquisition value set by the
  used-car manager.
- **Aging** — Days a receivable, payable, or inventory unit has
  been open.
- **BHPH** — Buy Here Pay Here. In-house dealer financing.
- **Cash accounting** — Recognize revenue and expenses when cash
  changes hands.
- **CIT** — Contracts in Transit. Funded-pending deals awaiting
  lender deposit.
- **COA** — Chart of Accounts. The numbered list of GL accounts.
- **Curtailment** — Periodic principal paydown on a floor-plan
  loan.
- **Deal jacket** — Complete file of documents for one deal.
- **Deferred gross profit** — Gross profit not yet recognized;
  used in installment-sale accounting for BHPH.
- **DMS** — Dealer Management System. The operational software
  backbone.
- **ELT** — Electronic Lien and Title. State-level electronic
  title system.
- **F&I** — Finance and Insurance. See `FINANCE_DEPARTMENT_MAPPING.md`.
- **FPD** — First Payment Default. Customer misses first payment.
- **Floor plan** — Revolving line of credit collateralized by
  inventory.
- **Form 8300** — Federal report for cash transactions over
  $10,000.
- **GL** — General Ledger. The complete record of all financial
  transactions.
- **In transit / in schedule** — Amounts owed or expected but
  not yet received/paid.
- **Journal entry** — A recorded transaction with debits and
  credits.
- **Out of trust** — Floor-plan audit finding: a floor-planned
  vehicle is missing without payoff. Serious.
- **P&L** — Profit & Loss statement.
- **Physical inventory** — Actual count of vehicles vs. the book.
- **Post / posting** — Recording a transaction to the GL.
- **PVR** — Per-Vehicle Retail. Gross per unit sold.
- **Reserve receivable** — Future reserve income expected from
  a lender.
- **Reserve for uncollectible accounts** — Estimated future
  losses on receivables.
- **Schedule** — Subsidiary ledger detailing the composition of
  a control account.
- **Segregation of duties** — Financial control requiring
  different people to approve, prepare, and authorize
  transactions.
- **Suspense account** — Holding account for unmatched or
  unidentified transactions.
- **Trial balance** — Sum of all account balances at a point in
  time; debits must equal credits.
- **Unapplied cash** — Money received but not yet matched to an
  invoice or deal.
- **VSC** — Vehicle Service Contract. Aftermarket coverage. See
  `FINANCE_DEPARTMENT_MAPPING.md`.
- **W-9** — Vendor tax ID form collected before payment.
- **W-2** — Employee wage and tax reporting form.
- **Wash / wash out** — Reconciling a suspense/holding account
  to zero.

---

## Related research

- `FINANCE_DEPARTMENT_MAPPING.md` — F&I department; upstream of
  Accounting for every deal.
- `VEHICLE_CENTRIC_PIVOT.md` — Overall pivot plan. Accounting
  research feeds Phase 1 (investment ledger — the vehicle jacket
  and per-unit cost tracking), Phase 6 (async infrastructure —
  daily floor-plan interest accrual), Phase 7 (operational
  intelligence — auction ROI, aging analytics), and Phase 8
  (Sale + Delivery models tie to deal accounting).
- `INDEPENDENT_DEALER_PIVOT.md` — Established the indie-first
  scope this document uses.
- `CAPABILITY_MATRIX.md` — Current shipped capabilities; nothing
  in that matrix touches accounting operations. Everything in
  this document is greenfield relative to the current product.

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

*End of Accounting Department mapping.*
