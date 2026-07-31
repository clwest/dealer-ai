---
title: "Inventory & Acquisition Department — Operational Mapping"
status: reference
type: research
generated: 2026-07-31
scope: Independent used-car dealership inventory acquisition, pricing, aging, and disposition operations
voice: Experienced used-car manager / buyer / owner-buyer
companion_docs:
  - "FINANCE_DEPARTMENT_MAPPING.md"
  - "ACCOUNTING_DEPARTMENT_MAPPING.md"
  - "SALES_DEPARTMENT_MAPPING.md"
  - "VEHICLE_CENTRIC_PIVOT.md"
  - "INDEPENDENT_DEALER_PIVOT.md"
authoritative_for:
  - How indie used-car dealerships actually source, price, hold, and dispose of inventory
  - The buying decisions and pricing dynamics that determine store profitability
not_authoritative_for:
  - Franchise CPO programs or OEM inventory allocations (mentioned only for contrast)
  - Recon workflow and vendor management (see companion `RECON_MAPPING.md`)
  - Specific auction platform features or pricing subscriptions
  - Any implementation design
---

# Inventory & Acquisition Department — Operational Mapping

> **What this is.** A research artifact documenting how the
> inventory / acquisition function of an independent used-car
> dealership actually operates. Written from the perspective of
> an experienced used-car manager, buyer, or owner-buyer — the
> person who walks the auction lanes and decides which vehicles
> the store will invest in.
>
> **Who this is for.** Anyone (engineer, agent, product person)
> touching inventory, acquisition, pricing, aging, or disposition
> work in the Dealer AI Kit. Read this before opening a code
> editor or a wireframe tool.
>
> **What this is NOT.** Not an auction training manual. Not a
> book-value guide. Not a market-analysis tool review. Not an
> implementation plan. Not a critique of specific software or
> pricing platforms.
>
> **Core philosophy.** **"You make your money when you buy, not
> when you sell."** Every experienced used-car buyer has said or
> heard some version of this. The vehicle's profit margin is
> largely determined at acquisition — by what you pay, by what
> the reconditioning will cost, by whether the market will
> support the retail number you need. Skilled buying compounds
> into a healthy store; poor buying eats the store from the
> inside no matter how good sales or F&I is. Inventory is not
> just "the cars sitting on the lot" — it is the store's largest
> capital deployment and its biggest ongoing risk. Every vehicle
> is an investment, and every day that vehicle sits unsold is a
> day it is depreciating, accruing floor plan interest, and
> occupying space that could hold a better piece.

---

## Purpose & scope

The Dealer AI Kit's vehicle-centric pivot (see
`VEHICLE_CENTRIC_PIVOT.md`) proposes making every stock number a
living operational record with lifecycle and ledger. This
document is the *operational-truth* companion to that pivot,
covering the acquisition and inventory-management side of the
vehicle's life — from the buying decision through pricing,
aging, and eventual disposition.

The recon side (condition inspection, work planning, vendor
management, front-line preparation) is documented separately in
`RECON_MAPPING.md`. Together the two documents cover the full
vehicle-side operation. A store's used-car manager typically
runs both, but the operations are distinct enough to warrant
separate treatment.

**Scope boundary:** *independent used-car dealer* scope.

- Small to mid-sized store (25–150 units in inventory at any
  moment; sometimes larger for BHPH-heavy operators).
- Mixed-make used inventory: cars, SUVs, trucks, occasional
  vans, occasional specialty (motorcycle, RV, small commercial
  — most indies avoid these unless niched in).
- No OEM captive supply channel — no factory-issued new
  vehicles, no OEM-directed CPO program, no fleet-return
  allocations from the manufacturer.
- Deal sizes typically $4,000–$30,000 retail; wholesale
  purchases $2,000–$25,000 typical.
- Multiple sourcing channels: auctions (dominant), trade-ins,
  wholesale, private party, occasional specialty channels.
- 1–3 people directly involved in inventory decisions
  (owner + buyer + used-car manager, sometimes all one person).
- BHPH-optional — BHPH stores buy differently (cheaper, older,
  higher-margin), covered as a distinct pattern where relevant.

Where franchise practice differs materially, this document notes
the contrast briefly. It does not attempt to fully document
franchise CPO, OEM allocation, or manufacturer-incentivized
buying.

---

## Voice & caveats

The voice throughout is that of an experienced buyer — someone
who has walked auction lanes for years, can spot a repaint from
twenty feet, and has developed strong opinions about which
trades are gold and which will eat the store alive. Terminology
is used as it's spoken ("clean piece," "run through," "book
value," "over-allowance," "wholesale gross," "the pack," "MMR,"
"a piece we can be proud of").

**Numeric caveats.** Any specific figures in this document —
book-value ranges, floor plan interest rates, aging bucket
thresholds, turn rate targets, per-unit recon estimates — are
illustrative of common practice. Real numbers vary enormously
by market, price point, vehicle class, seasonality, and store
philosophy. Treat this document as a map of *what variables
matter and how they interact*, not as a source of truth for
specific figures.

**Market-condition caveats.** The used-car market went through
extreme dislocations 2020–2023 (COVID supply shortage,
2020–2022 appreciation, 2023 correction, ongoing rate-driven
demand softness). Some of the operational realities described
here are stable; others were reshaped during that period.
Where possible this document describes the underlying dynamics
rather than a specific market moment.

**Compliance caveats.** Inventory acquisition operates within
compliance frames (odometer disclosure, title-brand disclosure,
FTC Used Car Rule, state-specific dealer buying restrictions).
Some points are mentioned; a full compliance program is covered
in `FINANCE_DEPARTMENT_MAPPING.md` §6 and a future
`COMPLIANCE_DEPARTMENT_MAPPING.md`.

---

## 1. The indie inventory landscape

### 1.1 The players

A typical indie inventory function:

- **Owner-buyer** — the person whose name is on the door. Often
  the primary buyer at smaller stores. Walks auction lanes
  personally. Makes final calls on trades. Sets pricing
  philosophy. Signs the floor plan agreement.
- **Used-car manager** — sometimes a distinct role, often the
  owner wearing that hat. Prices inventory, decides on
  reprices, approves trade values, coordinates with recon,
  makes wholesale disposition calls.
- **Buyer** — at larger indies, sometimes a dedicated person
  (owner's business partner, family member, trusted longtime
  employee) who attends auctions and sources trades. Rarely
  a distinct role at smaller stores.
- **Lot manager / porter** — moves vehicles, stages inventory,
  supports the physical lot. Not a decision-maker but reports
  on lot condition, missing units, damage.
- **Detail crew** — in-house or outsourced. Prep vehicles for
  listing. Not decision-makers on inventory but critical to
  the front-line-ready timeline.

Franchise contrast: franchise stores typically have a dedicated
used-car manager separate from the new-car manager, a used-car
buyer who does nothing but source vehicles, and inventory
analysts who track pricing and aging with sophisticated
software. Indie compresses all those roles.

### 1.2 The physical environment

- **The retail lot** — where front-line-ready vehicles sit for
  customer viewing.
- **The back lot / recon area** — where vehicles wait for
  recon, get recon work done, or wait for photography and
  listing.
- **The wholesale row** — a designated area for vehicles the
  store plans to wholesale out rather than retail. Sometimes
  behind a fence or separated.
- **Off-site storage** — some indies use offsite space for
  overflow, aged inventory, or seasonal units (convertibles in
  winter, snow-capable units in summer).

Lot layout matters. A well-organized lot is a merchandising
tool. Vehicles at the front / roadside get attention. Vehicles
buried in the back get overlooked. Aged inventory rotated to the
front for visibility is a common merchandising move.

### 1.3 The inventory portfolio decision

At any moment, the store has a portfolio of vehicles at
different stages, ages, price points, and body classes. The
portfolio composition matters:

- **Body class mix** — trucks, SUVs, cars, vans. Should match
  local demand. In the Southwest, trucks dominate. In the
  Northeast, AWD SUVs and sedans balance. Urban markets skew
  toward smaller cars.
- **Price point distribution** — a spread from entry-level (say
  $6k) to mid-tier ($15k) to upper-tier ($22k+) depending on
  the store's positioning.
- **Age of inventory (model years)** — franchise stores tend
  toward 1–5 model years; indie ranges wider (3–15 years typical).
  BHPH tilts even older.
- **Condition tier** — clean units at retail prices, "as-is"
  units at lower prices, wholesale-out units awaiting
  disposition.
- **Financing appeal** — some units are prime-financeable, some
  are subprime-only, some are cash-only. Portfolio must match
  the customer credit spectrum the store serves.

A poorly-composed portfolio (too many of the same body class,
too many aged units, too much money tied up in high-priced
inventory that doesn't move) will underperform even with great
sales execution.

### 1.4 The economics of holding inventory

Every day a vehicle sits on the lot, the store incurs:

- **Floor plan interest** — daily accrual on the advance
  balance (see `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.5). At
  typical 8% APR on a $15,000 advance, that's about $3.30/day,
  or ~$100/month per unit. Multiply by 60 units = $6,000/month
  just in floor plan interest.
- **Depreciation** — vehicles lose value over time. A vehicle
  worth $15,000 today may be worth $14,700 in 60 days due to
  simple market movement, regardless of condition.
- **Physical exposure** — sun fade, hail risk, vandalism, theft.
- **Space cost** — every parking spot has an implicit cost
  (rent, insurance, taxes).
- **Attention cost** — every aged unit takes up mental space
  that could be used on newer, more promotable inventory.

**Turn is the enemy of aging.** A store that turns inventory
8× per year has an average vehicle in stock 45 days. A store
turning 12× has average stock at 30 days. That 15-day
difference translates to real money: less floor plan interest,
less depreciation exposure, faster capital recycling.

### 1.5 The seasonal rhythm of buying

Acquisition follows sales patterns with a lead time:

- **Late January – early February:** buying ramps for tax
  refund season (Feb–Apr). Auction attendance intensifies.
  Prices rise as demand climbs.
- **March – April:** peak inventory pressure. Selling fast,
  need to replace fast, competing with every other dealer at
  auction.
- **May – June:** softening. Buyers pull back. Auction prices
  ease.
- **July – August:** family / back-to-school buying starts. Buy
  side ramps modestly.
- **September – October:** slowing. Trade-ins pick up as
  customers upgrade for winter (in cold regions).
- **November – December:** holiday-adjacent. Some buyers pull
  back before year-end tax planning; others buy hard to move
  aged inventory before year-end.

Skilled buyers plan acquisition weeks ahead of anticipated
sales demand.

---

## 2. Sources of Acquisition

Where inventory actually comes from. Each source has different
mechanics, costs, risks, and typical vehicle profiles.

### 2.1 Auctions — the largest source for most indies

For most indie used-car dealers, physical or online auctions
are the single largest source of inventory. The two dominant
auction companies in North America are **Manheim** (Cox
Automotive) and **ADESA** (OpenLane / Carvana), plus regional
auction houses (America's Auto Auction, XLerate, various local
independents).

**Physical auction (in-lane):**
- Dealer travels to the auction physically.
- Vehicles run through auction lanes on a rolling schedule
  (specific sale days, e.g. Wednesday for a given auction).
- Dealer inspects vehicles on the lot before the sale
  (walk-around, engine start, sometimes short drive).
- Vehicles are announced with condition disclosures
  ("clean title," "structural damage," "salvage title,"
  "engine issue," "mileage exempt").
- Bidding happens in the lane, live auctioneer.
- Winning bidder pays for the vehicle (typically 48 hours
  after purchase) and takes possession.

**Online auction (simulcast or exclusively-online):**
- Dealer participates from a computer or phone.
- **Simulcast** — physical auction with online bidding
  overlay. Same vehicles, wider audience.
- **Online-only** — vehicles never see a physical lane;
  dealers bid based on condition reports and photos.
- Vehicle inspection typically limited to photos and a written
  condition report. Some platforms offer optional
  post-sale-arbitration windows.

**Auction house dynamics:**

- Manheim / ADESA reach every US market via their auction
  network. Prices are set by supply and demand in the specific
  lane on the specific day.
- **Regional auctions** — smaller, more local dealer base,
  sometimes better prices on specific vehicle classes, less
  competition but also fewer vehicles.
- **Specialty auctions** — luxury, salvage, commercial, RV.
  Indies occasionally participate in one specialty auction.
- **Dealer-only auctions** — restricted to licensed dealers.
  Most auto auctions are dealer-only (though some fleet
  auctions allow limited public participation).

**Auction house policies that matter to the buyer:**

- **Announcement conventions** — what the auctioneer
  discloses matters legally. A vehicle announced "structural"
  cannot be later disputed as having structural damage.
- **Arbitration policies** — window during which a dealer can
  dispute a purchase for undisclosed issues (typically 24-72
  hours). Arbitration fees apply if the buyer files and loses.
- **Post-sale inspection (PSI)** — some auctions offer paid
  post-sale mechanical inspection that gives the buyer a
  short window to reject the vehicle.
- **Frame damage / paint check** — some auctions include a
  visual paint / frame check on request.
- **Buyer fees** — sliding scale based on winning bid, often
  $150–$500+ per vehicle. Non-negotiable, disclosed on
  settlement.
- **Payment terms** — typically wire, ACH, or auction-floor
  plan within 24-48 hours. Late payment = fees + potential
  lockout.

**Auction risk categories:**

- **Undisclosed damage** — accident history not shown on the
  Carfax that emerges after purchase. Common frustration.
- **Mechanical issues** — engine, transmission, or other
  system fails within a short window post-purchase.
- **Cosmetic surprises** — paint issues, interior wear worse
  than photos suggested.
- **Title problems** — title arrives with a brand not
  disclosed, wrong VIN, or missing entirely.
- **Overpaying** — bidding got competitive; the winning bid
  is above what the vehicle will retail for.

Skilled buyers develop a mental model of "which lanes at which
auction on which day" produce the best inventory for their
store's needs.

### 2.2 Trade-ins from the sales floor

Trades are a significant source of inventory for most indies,
often 20–40% of total acquisitions.

**Mechanics:**

- Customer arrives with a trade during the sales process (see
  `SALES_DEPARTMENT_MAPPING.md` §3.6).
- Used-car manager or buyer appraises the trade.
- ACV (actual cash value) is determined — typically wholesale
  value minus expected recon.
- **Trade allowance** offered to customer — sometimes above
  ACV as a negotiation tool (with corresponding reduction
  elsewhere in the deal).
- Vehicle enters the store's inventory.

**Trade appraisal factors:**

- **Book value** — KBB, JD Power, Black Book. Range of numbers,
  usually pick the "rough trade" or "average trade" column
  depending on condition.
- **Manheim MMR** — actual auction data on the specific
  YMM/trim/mileage. The most objective single number for
  wholesale.
- **Local market comps** — what similar vehicles are sold at
  wholesale locally.
- **Condition assessment** — physical walk-around, engine
  check, test drive. Adjustments for damage, wear, tire
  condition, mechanical issues.
- **Reconditioning estimate** — what would it cost to
  front-line this trade? Deducted from wholesale value to
  arrive at ACV.
- **Retail potential** — could this vehicle retail well at
  this store, or is it better wholesaled out?

**Trade characteristics that make a trade valuable:**

- Popular body class at the store's price point.
- Local-market vehicle (avoiding regional preferences like a
  4WD in Miami).
- Recent history (low mileage, one owner, clean Carfax).
- Trims / options that command retail premium (SR5, Sport,
  Limited, etc.).
- Colors that sell (silver, white, black, gray — over red,
  green, yellow).

**Trade characteristics that make a trade a wholesale-out:**

- Vehicle outside the store's typical price/class range.
- High mileage or older model year than store typically stocks.
- Rare / niche vehicle that would take months to retail
  (specialty truck, high-mileage diesel, exotic).
- Extensive recon needed relative to retail potential.
- Branded title (salvage, rebuilt, flood, lemon) — most
  indies refuse to retail these.
- Model / trim that has poor local demand.

### 2.3 Wholesale (dealer-to-dealer) purchase

Dealer buying inventory directly from another dealer.

**When wholesale-in makes sense:**

- Trade another store has (their disposition) that fits your
  inventory profile.
- Aged inventory another dealer is trying to move quickly.
- Specific vehicle a customer requested that you can source
  from a peer.
- Post-auction cleanup where another dealer overbought.

**Mechanics:**

- Direct dealer-to-dealer relationships (built over years).
- Price is typically negotiated at wholesale + a small
  courtesy margin.
- Payment via check, wire, or ACH.
- Title transfers dealer-to-dealer (no consumer sale).
- Some dealer trades are handled via wholesale platforms
  (dealer-only online marketplaces) but most are still
  handshake / phone-based.

**Dealer-to-dealer trust matters.** If a dealer sells you a
vehicle with undisclosed issues, the relationship ends and
word gets around. Peer accountability is high.

### 2.4 Private party (retail-source purchase)

Buying vehicles from consumers who list on Craigslist, Facebook
Marketplace, or contact the dealer directly.

**Mechanics:**

- Consumer contacts dealer or dealer proactively responds to
  private-party listings.
- Dealer inspects the vehicle (at the seller's home,
  workplace, or at the dealership).
- Price negotiated with the seller.
- Payment via check, cashier's check, or ACH.
- Title transferred consumer-to-dealer (standard sale
  paperwork).

**Attractive because:**

- Prices are often below wholesale (consumers don't know true
  wholesale value).
- Vehicles often better-maintained than auction stock (owner
  care).
- No auction fees, no buyer premiums.
- Ability to interview the previous owner about history.

**Challenging because:**

- Time investment per vehicle is high (drive to see, inspect,
  negotiate).
- Sellers may back out or shop the offer.
- Title / lien complications more common (private seller
  may not know how to pay off their lien).
- Volume is limited (can't scale to 20 vehicles/month via
  private party for most indies).

### 2.5 Off-lease and rental returns

**Off-lease vehicles** — vehicles returning from a lease term.
Historically dominated by captive OEM lenders and franchise
CPO programs, but off-lease vehicles also enter the auction
stream after the captive completes disposition.

**Rental company returns** — Hertz, Enterprise, Avis, National
sell used rental fleet at auction, direct dealer channels, or
their own retail outlets (Hertz Car Sales, Enterprise Car
Sales). Rental vehicles tend to be recent model year with
higher mileage than lease returns.

Indies get exposure to both categories primarily through the
auction channel.

### 2.6 Repossession auctions

Vehicles repossessed by lenders (banks, credit unions, BHPH
operators) are auctioned to recover the loan balance.
Sometimes at dedicated repo auctions, more often mixed into
regular auction inventory.

Characteristics:
- Condition varies wildly (some well-maintained, some
  neglected).
- Titles are clean (repo is not a title brand).
- Some vehicles have been sitting for weeks pre-repo.
- Interior often needs deep cleaning.
- Occasionally starter-interrupt devices installed by the repo
  lender (need removal).

### 2.7 Fleet disposal

Fleet companies (rental, corporate, government, utility)
dispose of vehicles as they age out of their fleet. Sometimes
through specialty fleet auctions, sometimes through direct
dealer relationships.

Characteristics:
- Similar YMM units in bulk (fleet buys in blocks).
- Higher mileage typical.
- Well-maintained service history (usually).
- Sometimes fleet-only options (no keyless entry, work-truck
  configuration, no rear seat).

### 2.8 Consumer-direct programs (rare for indie)

Programs like Carvana, CarMax, Vroom, and dealer-branded
"we'll buy your car" programs are consumer-facing acquisition
channels. Mostly used by the large national players.

Some indies experiment with similar programs (in-store "we'll
buy your car" appraisal, website trade-in valuation tool).
Volume varies.

---

## 3. The buying decision

The moment of decision at auction (or on any acquisition) is
where the store's future gross gets locked in. This section
documents how experienced buyers actually decide.

### 3.1 Book-out — the foundational reference

Before considering any specific vehicle, the buyer needs to
know what the market says the vehicle is worth. The **book-out**
is the process of looking up the vehicle's value in one or
more pricing guides.

Common sources:

- **Kelley Blue Book (KBB)** — consumer-facing but has
  dealer-facing versions. Multiple value columns:
  fair-market-range, private-party, trade-in, dealer-retail.
- **JD Power (formerly NADA Guides)** — traditional dealer
  reference. Rough trade, average trade, clean trade,
  clean retail, and adjustments for options and mileage.
- **Black Book** — dealer-focused wholesale pricing.
  Rough / average / extra clean columns.
- **Manheim Market Report (MMR)** — the most respected single
  number for wholesale. Aggregated actual auction transaction
  data on the specific YMM/trim/mileage. Updated frequently.
- **vAuto / MPI / other proprietary tools** — some indies
  subscribe to these; more common at larger stores.

**Reading a book-out:**

- **Wholesale** or **trade** value — what the vehicle should
  bring at auction or as a wholesale trade.
- **Retail** value — what the vehicle should retail for, in
  clean condition, on a dealer lot.
- **Spread** — retail minus wholesale. This is the range
  within which the store's gross has to fit after recon.

### 3.2 Retail-to-wholesale spread

The critical number the buyer needs to know:

```
Retail Price - Wholesale Cost = Available for Recon + Gross + Overhead
```

Example:
- Clean-retail book: $18,500
- Realistic asking price: $17,900 (below book, priced to
  market)
- Wholesale cost at auction: $13,500
- Buyer fees + transport: $600
- Total cost basis: $14,100
- Estimated recon: $1,500
- Total invested: $15,600
- Projected gross: $17,900 − $15,600 = $2,300

If the retail-to-wholesale spread doesn't leave room for
recon + gross + typical below-book selling pressure, the buy
doesn't make sense.

### 3.3 Recon estimate

Every acquisition carries an implicit recon estimate. Skilled
buyers walk the vehicle at auction (or read the condition
report carefully) and mentally price:

- Tires — how much tread? Full set replacement is $400–$1,200.
- Brakes — pads, rotors. $200–$800 depending.
- Windshield — chip or crack. $250–$600 to replace.
- Body dings and dents — small paintless repair ($100–$300
  each), larger body work ($500–$2,000+).
- Interior — stains, tears, cigarette smoke odor. $100–$500
  for detail; more for reupholstery.
- Mechanical — any check engine, transmission issue, oil leak.
  Highly variable; $200 diagnostic minimum.
- Diagnostics — every buy gets at minimum a fluid check, brake
  check, tire check on arrival.
- Detail — every unit gets full detail before front-line.
  $150–$400 typical.

Recon estimates vary widely by store philosophy — some buyers
plan generously ("assume $1,500 recon on every purchase"),
some plan tightly ("only what I saw"). Underestimating recon
compresses gross; overestimating limits acquisition volume.

### 3.4 Days-to-sale projection

**"How long will this take to sell?"** The buyer forms a
mental projection:

- Popular local vehicle in the store's sweet spot — 30–45
  days.
- Niche or off-brand — 60–90 days.
- Expensive relative to store norm — 90–120+ days.
- Wrong color, wrong trim, wrong story — potential aged
  unit.

Days-to-sale drives floor plan interest cost. A 60-day sale
at $15,000 advance costs ~$200 in interest. A 120-day sale
costs ~$400. That $200 difference comes out of gross.

### 3.5 Floor plan impact

Every acquisition draws on the floor plan (see
`ACCOUNTING_DEPARTMENT_MAPPING.md` §2.5). The buyer thinks
about:

- **Current floor plan utilization** — how much of the line is
  drawn? A store at 90% utilization is one bad auction week
  from a cash crunch.
- **Advance amount** — the vehicle will draw its cost plus
  fees plus (possibly) transportation on the line.
- **Curtailment schedule** — the vehicle will incur curtailment
  obligations at 60, 90, 120 days if it doesn't sell.
- **Portfolio floor plan health** — an aged inventory
  portfolio means the floor plan is heavy with slow-moving
  units, requiring more curtailment payments and eating cash.

Owners who ignore floor plan health at buy time end up in
cash-flow trouble later.

### 3.6 Gross projection

The buyer's final mental math on any potential acquisition:

- Target retail (market-realistic).
- Total cost basis (purchase + fees + transport + recon).
- Days-to-sale × floor plan interest.
- Any known risk factors (uncertain title, mechanical
  question, cosmetic issue).
- Expected front-end gross.

If expected gross is less than a threshold ($1,500 typical
minimum, $2,500 comfortable, $3,500+ great), the buy is a
hard "no" for many buyers.

### 3.7 "Would I be proud to sell this?" — the curation call

Beyond math, experienced buyers apply a curation filter:

- Is this a vehicle I'd sell to my mother?
- Does it have a story I can tell honestly to a customer?
- Am I going to have this thing sitting on the lot for 90
  days making me question my judgment every morning?
- Is this consistent with the store's brand and community
  reputation?

Stores known for "we don't sell junk" have buyers who exercise
this curation aggressively. Stores that will retail anything
have looser filters — and typically higher aged inventory
percentages and lower customer retention.

### 3.8 Bidding discipline at auction

At the auction lane, the buyer sets a **walk-away number** —
the price above which the deal doesn't make sense. Bidding
discipline is:

- Set the number before the vehicle runs.
- Stick to it when adrenaline picks up in the lane.
- Walk away when someone else is willing to pay more than
  the deal supports.

Buyers who overbid in the moment produce aged inventory
downstream. Buyers who under-bid consistently miss the
inventory they need. Discipline is a learned skill.

### 3.9 Buying with a specific customer in mind

Sometimes a buyer sources a specific vehicle for a specific
customer. Sales tells the buyer "I have a customer looking for
a 2018 F-150 XLT crew cab, under $30k, under 60k miles."
Buyer keeps eyes open, and when a candidate runs through
auction, buyer knows the retail is de-risked (sold before
purchased).

This is opportunistic and works well when sales-buyer
communication is tight.

### 3.10 Buying with market data at hand

Modern buyers often carry tablets or phones with real-time
book-out access. Bid on a vehicle without knowing MMR and
retail is guessing. Skilled buyers pre-scan the sale list
before attending, mark the vehicles they want to bid on, and
have book-outs ready.

---

## 4. Cost basis and initial recording

Once a vehicle is acquired, its cost enters the accounting
system (see `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.2). The
inventory / acquisition side is concerned with:

### 4.1 Stock number assignment

Every acquisition gets a stock number. Assignment is typically
sequential or systematized by year/body/source (see accounting
doc §2.1 for conventions). This is the identity that connects
every future transaction on the vehicle back to the specific
unit.

### 4.2 What enters cost basis at acquisition

- Purchase price (winning bid or negotiated price).
- Buyer fees (auction fee, arbitration if applicable).
- Transportation from source to lot.
- Any acquisition-day expenses (fuel, quick lot detail for
  photos).
- Sometimes: initial recon estimate as a reserve (varies by
  store philosophy).

### 4.3 What does NOT enter cost basis at acquisition

- Ongoing floor plan interest (accrued daily, expensed
  separately).
- Recon costs (added as they're incurred, not estimated
  upfront in most stores).
- Overhead allocations (general store expenses aren't
  vehicle-specific).

### 4.4 Physical intake

When the vehicle arrives:

- Verify VIN matches paperwork.
- Odometer reading recorded.
- Physical condition photographed (before any recon).
- Any damage present at acquisition documented (protects
  against later "was that there when we bought it?" questions).
- Keys and paperwork accounted for.
- Stock number physically applied (window sticker or number
  in the windshield).
- Vehicle staged (back lot for recon queue, front lot if
  minimal recon needed).

---

## 5. Floor plan management

Floor plan is the operator's daily concern beyond just the
accounting side. See `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.5
for the accounting mechanics; this section adds the
operational perspective.

### 5.1 Floor plan health as a store health signal

An owner-buyer checks floor plan status weekly, sometimes
daily:

- **Total advance outstanding** vs. line limit — utilization
  percentage.
- **Number of units currently floored** — matches physical
  count?
- **Aged units on the line** — 60/90/120+ day units driving
  curtailment obligations.
- **Interest accrual for the month** — trending vs. plan.
- **Recent curtailments paid** — cash outflow to floor plan
  lender.

High utilization + heavy aged inventory + rising curtailments
= cash crunch coming. Skilled owners see this weeks ahead and
adjust (aggressive pricing, wholesale-out, less buying).

### 5.2 Floor plan lender relationship

Common indie floor plan lenders: NextGear (Manheim), AFC,
Westlake Flooring, Ally, local banks with dealer programs.

Relationship maintenance:
- On-time curtailment payments.
- Pay off sold units promptly (usually within 3–5 business
  days of sale).
- Respond promptly to lender questions or audits.
- Communicate proactively about upcoming issues (surge in
  aging, cash flow tightness).

Losing a floor plan line is close to a store-ending event for
most operators. Alternate lines can be found but the
transition is painful and typically at less favorable terms.

### 5.3 Floor plan audit — the physical inspection

The floor plan lender physically inspects the lot at intervals
(monthly to quarterly typical). Every floor-planned vehicle
must be present or accounted for (sold-and-paid-off,
wholesaled with payoff sent, transferred to owner's
personal account with permission).

**Out-of-trust** — a floor-planned vehicle that's missing
without payoff is an out-of-trust finding. Serious. Can
trigger:

- Immediate freeze on the line.
- Payoff demand on the specific vehicle.
- Increased audit frequency.
- Program termination in severe cases.

Preparing for audits means knowing where every unit is at all
times. Vehicles at recon vendors, being test-driven by
salespeople, or moved for photos should all be trackable.

### 5.4 Advance rate management

Floor plan lenders set advance rates — the percentage of book
value they'll advance on any given unit. Advance rates depend
on:

- Vehicle age (newer = higher advance).
- Vehicle mileage (lower = higher).
- Book value (higher = often higher advance percentage).
- Type of vehicle (some lenders limit exotics, salvage,
  commercial).
- Dealer history with the lender.

Buying units the floor plan won't advance well means cash out
of pocket at acquisition. Some dealers keep this in mind at
auction — a vehicle the floor plan will only advance 80% on
means 20% cash from the store to close the buy.

### 5.5 Curtailment planning

Curtailments hit at defined ages (typical 60/90/120 days). A
store with 15 units aging past those thresholds owes real
cash — often $200–$800 per curtailment depending on advance
size. Ten units at 90-day curtailment could be $5,000+ of
cash out one week.

Skilled owners forecast curtailment obligations 30 days
ahead and either move the aged units (reprice, wholesale) or
prepare the cash.

---

## 6. Inventory categorization

Vehicles in stock exist in different operational categories.
The controller / inventory manager needs to know which
category each vehicle is in.

### 6.1 Front-line ready

Vehicles fully reconditioned, priced, photographed, listed,
and available for customer viewing. This is the sales team's
active inventory.

Criteria (varies by store):

- Recon complete (see `RECON_MAPPING.md`).
- Detail complete.
- Photos taken and uploaded.
- Priced.
- Listed on the store's platforms (website, third-party
  listing sites).
- Physically on the retail lot.

### 6.2 In recon

Vehicles in the reconditioning pipeline — mechanical, body,
paint, interior, glass, detail. Not yet available for sale.

Sub-states:

- Awaiting inspection.
- Inspection complete, awaiting work approval.
- Work in progress (in-house shop or at outside vendor).
- Work complete, awaiting QC.
- QC complete, awaiting detail.
- Detail in progress.
- Awaiting photos / listing.

Some vehicles in recon are pre-sold (a customer committed
before recon completed and is waiting for delivery).

### 6.3 Incoming

Vehicles acquired but not yet at the store. Common examples:

- Purchased at auction, awaiting transport.
- Arriving via trade-in (customer will drop off after new
  vehicle delivery).
- Wholesale purchase in transit.

Incoming inventory is sometimes available for customer
preview (paperwork sale) before physical arrival.

### 6.4 Wholesale-out (disposition)

Vehicles the store has decided to wholesale rather than
retail. Reasons:

- Aged unit not moving.
- Wrong vehicle for the store's profile.
- Recon estimate exceeds retail potential.
- Discovered issue that changes the calculus.

Wholesale-out units sit in a separate area of the lot (or
sometimes off-lot) awaiting a dealer buyer, an auction date,
or an online wholesale platform posting.

### 6.5 Company / owner use

Some inventory is designated as company or owner-personal use.
Reasons:

- Owner's personal vehicle drawn from inventory.
- Employee vehicle assigned (sales manager, salesperson
  perk).
- Loaner or courtesy vehicle.
- Owner's family use.

These vehicles are usually removed from active inventory but
tracked separately. Tax and insurance implications matter.

### 6.6 Hold / reserved

Vehicles temporarily removed from active availability:

- Pending sale (customer committed, deal in progress).
- Reserved for a specific customer (be-back scheduled).
- Being test-driven or evaluated.
- Awaiting a specific event (photo shoot, ad copy, feature
  refresh).

### 6.7 Off-market / issue

Vehicles with a problem that prevents sale:

- Title problem (missing, branded, ownership dispute).
- Recall open, awaiting service.
- Mechanical issue discovered.
- Damage in possession (hail, vandalism, sales staff mishap).

Off-market inventory should be a small percentage of the total.
Large off-market counts signal operational problems.

---

## 7. Pricing dynamics

Pricing is the single most-adjustable variable an inventory
manager controls. Pricing philosophy varies enormously by
store.

### 7.1 Initial pricing

When a vehicle is ready for front-line, the initial price is
set. Common approaches:

- **Book-based** — start at clean-retail book, adjust down
  for known negatives.
- **Market-comp-based** — check similar vehicles on
  AutoTrader / Cars.com / CarGurus in the local market;
  price to be competitive.
- **Percentage-margin-based** — start at cost + target margin
  (e.g., cost + $3,000).
- **Ceiling-price-based** — highest price the market will
  accept, willing to negotiate down.

Most modern indies use a hybrid: check market comps, check
book, price to be within 5–10% of competitive vehicles
locally.

### 7.2 Competitive intelligence

Skilled inventory managers know what similar vehicles are
priced at nearby dealers:

- Weekly (or daily) scan of major listing platforms.
- Note pricing on comparable YMM/trim/mileage vehicles at
  competing dealers.
- Track pricing over time (which competitors move prices
  quickly, which sit).
- Understand pricing rank on major platforms (CarGurus
  "deal rating," similar features on Cars.com).

Software tools exist to automate this (vAuto, MPI's Market
Guide, others). Manual competitive scanning is still common
at smaller indies.

### 7.3 Pricing on listing platforms

Different platforms use different pricing psychology:

- **CarGurus** — algorithm explicitly compares your price to
  market. "Great Deal" units get badge and better visibility.
  Pricing pressure to fit the algorithm.
- **AutoTrader / Cars.com** — no explicit deal rating but
  price is a filter. Under-priced vehicles get more views.
- **Facebook Marketplace** — consumer-facing; visible pricing
  drives inquiry volume.

Some dealers price 5–10% under market on their most-visible
platforms to drive lead volume; others price at market and
compete on service.

### 7.4 The reprice cadence

Vehicles that haven't sold get repriced on a schedule:

- **Day 15–20 review** — first quick look for adjustment.
- **Day 30 reprice** — first formal reprice ($200–$500 typical).
- **Day 45 reprice** — second reprice.
- **Day 60 aggressive** — larger price cut ($500–$1,500).
- **Day 90 decision** — retail with an aggressive price, or
  wholesale-out?
- **Day 120+ escalation** — active disposition to wholesale.

Reprice cadence varies by store. Some do weekly reviews with
smaller adjustments; some go long stretches then large cuts.
Discipline on cadence matters more than the specific numbers.

### 7.5 The "priced to move" decision

Sometimes a vehicle is priced aggressively from day 1:

- Cost basis is unusually good (great auction find, easy
  trade).
- Owner wants faster inventory turn.
- Vehicle is a specific model the store wants to move quickly.
- Cash flow needs the sale.

"Priced to move" gives up some gross for turn. On balance,
faster turn typically outperforms slower higher-margin
holdings because floor plan interest and market movement work
against holding.

### 7.6 Below-cost pricing decisions

Sometimes a vehicle is priced below the store's cost basis:

- Aged unit past reasonable retail window.
- Discovered issue that reduces retail value.
- Market moved down while the store held the vehicle.
- Cash flow requires disposition regardless of loss.

Below-cost sales generate wholesale-loss journal entries and
impact overall gross performance. Skilled owners understand
the specific-unit loss is often better than continuing to hold
the aged unit and paying floor plan interest indefinitely.

### 7.7 Book value vs asking price

An asking price above book (dealer retail) is asking a premium
— hard to justify unless the vehicle has something special
(rare color, low mileage, one-owner, recent service records).

An asking price below wholesale book — the store is losing on
paper. Wholesale-out is usually the right call rather than
retail-at-a-loss.

### 7.8 The pricing "story" for salespeople

When a customer asks "why is this priced at $16,500?" the
salesperson needs an answer. Skilled inventory managers give
their salespeople a story:

- "This one has a clean two-owner Carfax and low mileage for
  the year — that's why we're at market rather than below."
- "This is the aged unit we've reduced twice — we're priced
  aggressively to move it, and there's not much room."
- "This came from a trade at a fair number, so we're able to
  price it a little under market."

The story anchors negotiation. Without a story, every price
feels arbitrary and customers press harder.

---

## 8. Aging management

Aging is the operational hangover of prior buying and pricing
decisions. Managing aging is a daily-to-weekly activity for
inventory managers.

### 8.1 The aging report

Every store produces (or should produce) an aging report:

- Every unit in current inventory.
- Days since acquisition.
- Current price.
- Cost basis (including recon).
- Cumulative floor plan interest to date.
- Projected total investment if held X more days.

Aging report is typically reviewed weekly (sometimes daily) by
the used-car manager or owner.

### 8.2 Aging buckets

Standard bucket structure:

- **0–30 days** — fresh inventory. High attention, promoted.
- **31–60 days** — normal aging. Monitored.
- **61–90 days** — starting to age. Repricing considered.
- **91–120 days** — aged. Aggressive action needed
  (reprice, wholesale).
- **121+ days** — problem inventory. Wholesale-out likely.

### 8.3 Bucket targets

Healthy inventory has bucket distribution roughly:

- 30–40% in 0–30 days.
- 25–35% in 31–60 days.
- 15–25% in 61–90 days.
- 10–15% in 91–120 days.
- <5% in 121+ days.

Sick inventory shows heavy concentration in 90+ day buckets.
That means the store bought too much of something it can't
sell.

### 8.4 The "10-day story"

For every unit in the 60+ day buckets, some stores demand a
"10-day story":

- What is the plan for this unit in the next 10 days?
- Reprice? Feature in marketing? Wholesale-out? Photo
  refresh?
- Who owns the plan?
- What would signal that the plan isn't working?

This forces discipline on aged inventory rather than allowing
it to age indefinitely.

### 8.5 Owner escalation

Very aged inventory (120+ days) typically triggers owner
attention. Decisions:

- Continue holding with reprice.
- Wholesale-out to another dealer.
- Send back to auction.
- Reclassify (personal use, employee use, parts vehicle).

Every path has cost implications. Owners weigh continuing
carrying cost vs. immediate realized loss.

### 8.6 Aging-driven merchandising

Aged units sometimes get moved to more visible lot positions.
Photos refreshed. New descriptions written. Sometimes a
"reduced" sticker or "special" callout. Sometimes
lot-signage promotion.

Marketing effort focused on aged inventory is a real (if
subtle) discipline.

---

## 9. Disposition paths

Every vehicle eventually leaves inventory. The path affects
economics.

### 9.1 Retail sale (the normal exit)

Full retail to a consumer. Covered in
`SALES_DEPARTMENT_MAPPING.md` (sales side) and
`FINANCE_DEPARTMENT_MAPPING.md` (F&I side) and
`ACCOUNTING_DEPARTMENT_MAPPING.md` §3 (accounting side).

From inventory's perspective:
- Unit removed from active inventory when contract signed.
- Floor plan payoff sent within 3–5 business days.
- Vehicle jacket closed on the inventory side; deal jacket
  opened on the sales / F&I side.

### 9.2 Wholesale to another dealer

The store sells to a peer dealer at wholesale price.

Reasons:
- Aged unit the peer will take.
- Vehicle outside the store's profile.
- Peer requesting a specific unit (courtesy trade).

Mechanics:
- Price negotiated (often at MMR or wholesale book).
- Payment by check, wire, or ACH.
- Title transferred dealer-to-dealer.
- Vehicle picked up by the buying dealer.
- Wholesale-loss or wholesale-gain journal entry booked.

Typical wholesale is at or near cost — front-end gross
minimal or negative. The purpose is disposition, not profit.

### 9.3 Auction-out (sell back to auction)

The store sends the vehicle back through the auction as a
seller.

Reasons:
- No local wholesale buyer.
- Wide potential buyer pool for the specific vehicle.
- Volume disposition of aged inventory.

Mechanics:
- Vehicle transported to auction.
- Seller pays auction fees (typically less than buyer fees,
  but still real).
- Vehicle runs through auction lane.
- Winning bidder buys it; store receives payout net of fees.
- Sometimes vehicles don't sell (no bidders willing to meet
  the store's floor); returned unsold with fee.

Auction-out proceeds are often below the store's book value.
The store realizes a loss on paper but frees up the floor
plan capacity.

### 9.4 Wholesale via online platforms

Various online wholesale marketplaces exist (Manheim's ADESA
online, various private dealer-only platforms) for
dealer-to-dealer sales without physical auction attendance.

Mechanics:
- Post listing with photos, condition report, price.
- Interested peer dealer buys, arranges transport.
- Payment and title transfer via platform or direct.

### 9.5 Company / personal vehicle transfer

Sometimes the store moves a unit from inventory to owner
personal use, employee use, or company use (dealership
courtesy vehicle).

Mechanics:
- Vehicle removed from retail inventory.
- Reclassified in accounting to appropriate category (owner
  draw, employee benefit, company asset).
- Tax and insurance implications addressed.
- Title may transfer to individual (owner, employee) or
  remain in company name.

### 9.6 Insurance total loss

Vehicle damaged (weather, accident, theft) beyond
economically-repairable point. Insurance claim filed. Settled
value received.

Mechanics:
- Insurance appraisal / total-loss determination.
- Settlement amount agreed.
- Title transferred to insurance carrier (or salvage).
- Cash proceeds recognized.
- Loss/gain vs cost basis booked.

### 9.7 Destruction / salvage

Rare. Vehicle destroyed beyond insurance recovery, or
salvaged for parts, or discovered to have a title-branding
issue that makes retail impossible.

---

## 10. Turn rate and cash flow

The relationship between inventory decisions and cash flow.

### 10.1 Turn rate

**Inventory turn** = units sold per year / average units in
inventory. Higher = faster-moving inventory = healthier
business.

Typical indie turn 8–12× per year. Elite performers 15×+.
Struggling operations 6× or lower.

Turn is a compound signal:
- Good buying (units the market wants).
- Good pricing (fits the market).
- Good sales execution (converts opportunities).
- Good recon flow (units get to front-line quickly).

Poor turn means one or more of the above is broken.

### 10.2 Days to sale

Related metric: days from acquisition to sale. Aggregate
average and per-unit.

Target ranges:
- Fast turn stores: 30–45 day average.
- Typical stores: 45–60 day average.
- Aged inventory issue: 60+ day average.

### 10.3 Cash flow cycle

A simplified model:
- Vehicle acquired: cash out (or floor plan draw).
- Vehicle reconditioned: cash out for vendor payments.
- Vehicle sold: contract signed, deal in transit.
- Deal funds: cash in (net of floor plan payoff).

Cycle time from acquisition to funded ≈ recon time + days on
lot + funding time. Typical 45–75 days from acquisition to
cash recovery.

Stores with tight cash flow watch this cycle closely. Slower
cycles = more capital tied up = more borrowing required.

### 10.4 The relationship between aging and cash flow

Every day of aging is a day of no cash recovery on that unit
and continued floor plan interest accrual. Compounding.

An operator whose inventory ages badly has a cash-flow
problem waiting to happen. Aggressive management of aged
inventory (reprice, wholesale-out) is a cash-flow move as much
as a gross-profit move.

---

## 11. Listing management

Listing is where inventory meets the customer-acquisition
machine. Covered from a sales perspective in
`SALES_DEPARTMENT_MAPPING.md` §5, this section covers the
inventory-management side.

### 11.1 Getting a unit listed

Once a unit is front-line ready:

- Photos taken (see `RECON_MAPPING.md` §9).
- Vehicle description written (features, condition,
  Carfax notes).
- Priced.
- Entered into the DMS with front-line status.
- Pushed to listing platforms.

### 11.2 Photo requirements

Different platforms have different photo requirements:

- **AutoTrader / Cars.com** — typically 20–40 photos, mix of
  exteriors, interiors, engine, VIN.
- **CarGurus** — similar.
- **Facebook Marketplace** — usually first photo is main
  hero; 10–20 photos work well.
- **Store's own website** — dealer control, typically
  20–40+.

Reality: many stores use the same photo set across platforms.
Some use listing-syndication services that push photos
automatically.

### 11.3 Description standards

Description conventions:
- Body starts with vehicle summary (year, make, model, trim,
  mileage).
- Key features called out (specific options: navigation,
  leather, sunroof, tow package, etc.).
- Condition notes ("clean Carfax," "one owner," "local
  trade").
- Purchase invitation or CTA.
- Store contact info.

Some stores use templates and fill in vehicle-specific
details; some hand-write each description; some outsource
listing copy to specialty services.

### 11.4 Cross-platform listing

Most indies list on multiple platforms:
- Store's own website (must-have).
- AutoTrader.
- Cars.com.
- CarGurus.
- Facebook Marketplace.
- Craigslist (in relevant markets).
- Sometimes specialty platforms (Carfax Listings, TrueCar,
  regional sites).

Manual cross-posting takes hours per unit. Syndication
services (part of DMS or standalone) reduce this but often
lag in coverage.

### 11.5 Price change propagation

When a unit is repriced, the change needs to reach every
platform. Well-integrated stores update once and syndicate;
loosely-integrated stores update each platform manually.
Price drift across platforms confuses customers and creates
credibility issues ("your website says $17,500, AutoTrader
says $18,000 — which is it?").

### 11.6 Sold-unit removal

When a unit sells, it needs to be removed from all listing
platforms. Failure to remove creates leads for sold units —
disappointing customers and generating "sorry, that just
sold" conversations.

### 11.7 Listing performance monitoring

Skilled inventory managers monitor per-listing performance:

- Views per platform per unit.
- Leads per platform per unit.
- Time-to-first-lead.
- Deal-rating status (CarGurus).
- Aging on platform (some platforms rank by freshness).

Underperforming listings get investigation: bad photos,
wrong price, weak description, wrong platform for the
vehicle type.

---

## 12. Vehicle jacket

The per-unit file that documents the vehicle's history at
the store. Related to but distinct from the deal jacket
(which documents the specific sale transaction).

### 12.1 Contents of the vehicle jacket

- Purchase documents (auction settlement, trade appraisal,
  wholesale purchase invoice, private-party bill of sale).
- Title (or reference to title storage).
- Vehicle condition report at acquisition (photos, notes).
- All recon-related invoices and work orders (see
  `RECON_MAPPING.md`).
- Photos (acquisition, mid-recon, listing-ready).
- Vehicle history report (Carfax, AutoCheck).
- Any known-issue notes.
- Any customer communications about the vehicle (be-back
  reservations, hold requests).
- Sale documents when applicable (or reference to the deal
  jacket).

### 12.2 Physical vs digital

Some stores keep physical jackets in file cabinets, indexed
by stock number. Some maintain digital jackets in DMS or
document-management systems. Modern practice trends digital;
some paper still exists for originals that must be retained
physically.

### 12.3 Jacket completeness

Well-run stores audit vehicle jackets for completeness at
various points (mid-recon, pre-front-line, post-sale). Missing
documents get chased and added.

Sloppy jackets create audit exposure and make it impossible
to answer questions like "what did we actually pay for this
piece?" or "did we replace the tires when we brought it in?"

### 12.4 Retention

Per record-retention policy (typically 5–7 years post-sale
per `ACCOUNTING_DEPARTMENT_MAPPING.md` §9.5). Sold-vehicle
jackets go to retention; sold vehicles occasionally return as
warranty-claim or customer-complaint matters years later.

---

## 13. Cross-shopper intelligence

Skilled inventory managers know what competing lots have.

### 13.1 Why it matters

Customers cross-shop. When a customer says "I saw one at
[other dealer] for $500 less," the store's inventory manager
should already know that vehicle exists and its actual
condition/pricing.

### 13.2 Sources of competitive intelligence

- Regular scans of major listing platforms filtered to
  competing dealers.
- Personal visits to competitor lots (drive by, spot-check).
- Salesperson feedback from customer conversations.
- Auction results (which competitors are buying what).
- Word-of-mouth in the local dealer community.

### 13.3 How it shapes decisions

- **Pricing** — knowing competing prices informs your own.
- **Acquisition** — knowing what competitors are buying (or
  not) informs what you buy.
- **Marketing** — knowing where you're most/least competitive
  informs which units to promote.
- **Wholesale disposition** — knowing which competitors need
  specific units helps place wholesale sales.

---

## 14. Pain Points

Repetitive friction inventory / acquisition staff experience.
Documentation only; no solutions proposed.

### 14.1 Auction attendance vs desk work

Attending auctions physically means someone else at the store
covers all the other daily work. Owner-buyers face this
constantly.

### 14.2 Book-out during live bidding

The vehicle is running through the lane in 60 seconds. Buyer
needs current MMR, KBB, and market comp. Tablet has to load
fast; data must be current. Missed data means missed bid or
wrong bid.

### 14.3 Post-purchase transportation coordination

Vehicle bought at auction 100 miles away needs to get to the
lot. Coordinate carrier, verify pickup, track arrival. Time
spent on logistics per vehicle.

### 14.4 Trade appraisal delays

Customer at the desk expects trade number quickly. Used-car
manager is with another customer, at auction, or unreachable.
Delay compounds through the sales process.

### 14.5 Aged unit decision paralysis

That 100-day unit sits on the lot. Reprice or wholesale?
Neither feels right. Decision keeps getting deferred, unit
keeps aging.

### 14.6 Book value disagreement across sources

KBB says $16,000. JD Power says $15,200. MMR says $14,800.
CarGurus market average $15,600. Which one is right?
Judgment call every time.

### 14.7 Manual competitive scanning

Every week, someone should be checking competitor pricing
on your inventory categories. Rarely happens systematically;
happens erratically.

### 14.8 Cross-platform listing maintenance

New unit needs to be listed on 5–6 platforms. Reprice needs
to propagate to 5–6 platforms. Sold unit needs to be removed
from 5–6 platforms. All manual (or partially manual, with
sync gaps).

### 14.9 Photo management

Photos have to be taken, edited (crop, sometimes background
removal), uploaded to each platform, ordered correctly on
each. Hours of work per unit.

### 14.10 Floor plan monitoring

Floor plan portal has to be checked regularly. Curtailment
schedule tracked. Interest accrual monitored. Utilization
watched. All manual for many stores.

### 14.11 Sales team not updated on new arrivals

Vehicle arrived Tuesday. Wednesday morning nobody in sales
knows about it. Customer inquires about a similar unit;
salesperson misses the opportunity to pivot to the new
arrival.

### 14.12 Recon ETAs that don't match reality

Vehicle promised to be front-line by Friday; actual ready
date is next Wednesday. Sales team promised customer
Saturday delivery. Chain of broken promises.

### 14.13 Vendor recon quality inconsistency

Same vendor produced great work last time; this time the
work has issues. Consistency across recon vendors is real
challenge; requires QC and vendor management.

### 14.14 Wholesale disposition timing

Aged unit ready to wholesale. But when? Next auction is a
week away. Local peer buyer said "maybe" three weeks ago.
Online wholesale platform posts sitting without offers.
Disposition timing is often opportunistic rather than
planned.

### 14.15 Missing / delayed titles at acquisition

Vehicle bought at auction three weeks ago; title hasn't
arrived. Unit can't be sold without title. Store's
inventory has $15,000 of dead capital until title arrives.
Chase the auction repeatedly.

### 14.16 Overbought scenarios

Buyer had a strong auction; store now has 15 units to
recon at once. Recon capacity (in-house or vendor) is
overwhelmed. Units age in recon before even reaching the
retail lot.

### 14.17 Underbought scenarios

Slow auction weeks; inventory shrinks; salespeople have
nothing to show new customers. Marketing budget spent on ads
but no fresh inventory to promote.

---

## 15. Operational Decisions

Decisions inventory managers make repeatedly.

### 15.1 Bid or walk at auction?

The lane vehicle is running. Bid to the walk-away number?
Push above? Walk away? Decision made in seconds under
adrenaline.

### 15.2 What to take as a trade?

Customer's trade evaluated. Take it into inventory or
wholesale-out? At what allowance?

### 15.3 Initial price on a new unit?

Just came off recon. Price at book? Above? Below? Match
market comps?

### 15.4 Reprice or hold?

45-day unit. Reprice now or wait another two weeks? By how
much?

### 15.5 Wholesale-out or continue retailing?

90-day unit. Cut the loss and wholesale? Or one more reprice
cycle?

### 15.6 Which units to feature this week?

Marketing budget or featured spots on listing platforms.
Which units get the treatment?

### 15.7 Which auction to attend this week?

Multiple auctions competing for buyer's time. Which one has
inventory that fits the store best?

### 15.8 How many units to acquire this week?

Given current inventory levels, sales pace, floor plan
capacity, and expected demand, how much to buy?

### 15.9 Which vendor to use for a specific recon job?

Multiple options (in-house, vendor A, vendor B). Trade off
cost, turn time, quality.

### 15.10 Move a vehicle from retail to wholesale-out?

The judgment moment when inventory categorization changes.
Committing to disposition rather than retail.

### 15.11 Accept an incoming trade the buyer thinks is questionable?

Buyer doesn't love the trade. Sales manager needs it to
close the deal. Owner mediates.

### 15.12 Take a chance on a vehicle with unclear title?

Auction announcement says "no title present." Buy anyway
and hope for the best? Wait? Skip?

### 15.13 Advance rate negotiation with floor plan lender?

Vehicle would be a great buy but floor plan will advance only
70% of cost. Take it and pay 30% cash? Skip?

### 15.14 Owner personal vehicle from inventory?

Owner wants a vehicle from the lot for personal use. Which
unit? At what internal transfer price?

---

## 16. Automation Opportunities

Where repetitive administrative work lives. Opportunity
identification only.

### 16.1 Real-time book-out lookup at auction

Buyer scans VIN or types YMM at the lane, receives
consolidated book-out (KBB, JD Power, MMR, market comps)
instantly. Reduces mental math and slow-loading tools during
live bidding.

### 16.2 Auction watchlist and sale-list pre-scan

Upload the day's auction sale list. Automatic pre-scan of
each vehicle against store buying criteria (body class, price
range, book value delta, recent MMR trend). Buyer arrives at
the auction with a prioritized watchlist.

### 16.3 Trade appraisal decision support

Given customer's trade YMM/mileage/condition-notes, produce
suggested wholesale value, retail potential, recon estimate,
and go/no-go recommendation. Used-car manager uses as
starting point.

### 16.4 Days-to-sale prediction

Given a candidate acquisition or an in-inventory unit,
predict days-to-sale based on historical data (similar
units, current market, store's historical turn on the
category). Informs pricing and reprice decisions.

### 16.5 Aging report with escalation

Every unit's aging surfaced daily; units crossing thresholds
(30, 60, 90 days) get flagged with suggested actions
(reprice, feature, wholesale).

### 16.6 Competitive pricing scan

Automated scan of major listing platforms for units matching
your inventory (YMM, trim, mileage range). Delta reported.
Reprice recommendations generated.

### 16.7 Listing cross-platform push

Once a unit is entered in the source of truth (DMS), photos
and descriptions push to all listing platforms. Price
changes propagate automatically. Sold-unit removal
propagates.

### 16.8 Photo-to-listing workflow

Photos taken at the lot get automatically organized, ordered,
edited (background, watermark), and staged for listing
publication.

### 16.9 Floor plan health dashboard

Real-time view of utilization, per-unit balances, aging on
the floor plan, upcoming curtailment obligations, cash
outflow forecast.

### 16.10 Wholesale disposition workflow

Aged units get posted to online wholesale platforms
automatically. Peer dealer buyers identified from past
transactions. Offers received and organized.

### 16.11 Buyer performance analytics

Buyer's historical performance by source, category, and
seasonality. Which sources produce your best gross? Your
worst? Where should acquisition budget shift?

### 16.12 Post-recon cost variance

For each acquired unit, actual recon cost vs. the buyer's
initial estimate at acquisition. Trending: is the buyer's
estimating getting better or drifting?

### 16.13 New arrival announcement to sales team

New units automatically communicated to sales team with
photos, key features, target retail, and "who this fits"
notes. Reduces the "nobody told me" problem.

### 16.14 Sales-buyer demand feedback loop

Sales conversations that ended without a fit (customer
wanted a body class or price point you didn't have) captured
and surfaced to the buyer as demand signal.

### 16.15 Vehicle history report auto-attachment

Every new acquisition automatically gets Carfax / AutoCheck
report pulled and attached to the vehicle jacket. Reduces
manual step; ensures every unit has a report.

### 16.16 Title receipt tracking

Every acquired unit's expected title date tracked.
Overdue titles flagged for follow-up. Chargeback risk on
sold-but-title-pending units surfaced.

Each is a candidate for its own future planning session.

---

## 17. Cross-Department Dependencies

### 17.1 Sales

**Inventory depends on Sales for:**
- Demand signal (what customers are asking for that isn't
  in stock).
- Trade information from the desk (year/make/model, payoff,
  condition).
- Timely feedback on aged units that keep coming up in
  customer conversations without closing.
- Feedback on units that get shopped and lost (pricing
  concern signal).
- Communication of holds / reservations to protect specific
  units.

**Sales depends on Inventory for:**
- Steady flow of fresh, salable inventory.
- Accurate current-day view of what's front-line, in recon,
  incoming.
- Accurate pricing.
- Reliable ETA on in-recon units.
- Vehicle history reports and known-issue disclosure.
- Photos of new arrivals.
- Trade appraisal turn-time that doesn't stall deals.

### 17.2 Recon

**Inventory depends on Recon for:**
- Realistic ETAs on in-recon units.
- Accurate cost estimates before work begins.
- Quality workmanship (chargebacks and warranty issues come
  from poor recon).
- Front-line-ready sign-off (unit truly ready).
- Communication when recon reveals a bigger problem than
  estimated.

**Recon depends on Inventory for:**
- Correct condition report at acquisition (what needs to be
  done).
- Priority signal (which units are needed sooner for sales
  demand).
- Budget authorization (approval for higher-cost items).
- Vehicle jacket accessibility (history, prior work).
- Timely delivery of vehicles to the recon area
  post-acquisition.

### 17.3 F&I (Finance and Insurance)

**Inventory depends on F&I for:**
- Feedback on financeability of specific units (some units
  don't book well at subprime tiers).
- Chargeback data from deals that funded on aged inventory
  (were they FPD-prone?).
- Coordination on units held for be-back customers vs
  available.

**F&I depends on Inventory for:**
- Accurate book-out data available at deal time.
- Vehicle features / trim / mileage accuracy (drives lender
  advance calculation).
- Photos required by some lender portals.
- Recall status on units being sold.
- Timely notification when an ordered unit is available for
  delivery.

### 17.4 Accounting

**Inventory depends on Accounting for:**
- Floor plan reconciliation and health reporting.
- Vendor payment on recon invoices (timely payment maintains
  vendor relationships).
- Cost accumulation on the vehicle jacket (running total per
  unit).
- Financial statements showing inventory value at close.
- Bank rec confirmation of deposits from auction settlements
  or wholesale sales.

**Accounting depends on Inventory for:**
- Timely stock number assignment and initial cost recording.
- Accurate categorization of expenses (which are
  capitalizable to the unit, which are operating).
- Physical inventory count for schedule reconciliation.
- Notification of any unit-status changes (moved to
  wholesale, off-market, company vehicle).
- Approval on recon vendor invoices.

### 17.5 Auction relationships

**Inventory depends on Auctions for:**
- Consistent inventory supply.
- Accurate condition disclosures.
- Reasonable arbitration process.
- Timely title delivery post-purchase.
- Rep responsiveness on disputes.
- Access to buyer support (post-sale inspection, etc.).

**Auctions depend on Inventory (dealer) for:**
- Prompt payment.
- Fair arbitration disputes (only when justified).
- Continued attendance and bidding.
- Buyer program participation (floor plan through auction's
  preferred lender, insurance, transport).

### 17.6 Wholesale dealer network

**Inventory depends on Wholesale peers for:**
- Buyers for the store's disposition inventory.
- Sellers for specific units the store needs.
- Honest dealings (accurate condition disclosure).
- Reasonable pricing that reflects wholesale market.

**Wholesale peers depend on Inventory (this dealer) for:**
- Honest dealings back.
- Reciprocal buyer-seller relationships.
- Prompt payment on wholesale-in purchases.
- Reliable pickup / drop-off logistics.

### 17.7 Floor plan lender

**Inventory depends on Floor Plan for:**
- Available credit for acquisitions.
- Competitive advance rates.
- Reasonable curtailment schedule.
- Timely audit process.
- Rep responsiveness on questions.

**Floor Plan depends on Inventory for:**
- Physical presence of all floor-planned units.
- Prompt payoff on sold units.
- Prompt curtailment payments.
- Compliance with lender policies.
- Accurate reporting.

### 17.8 Ownership

**Inventory depends on Ownership for:**
- Buying budget authorization.
- Cash for cash-required acquisitions.
- Trade approval on unusual trades.
- Wholesale-out approvals on aged inventory.
- Strategic direction (inventory portfolio composition, price
  points, body-class mix).
- Deal approval on unusual acquisitions.

**Ownership depends on Inventory for:**
- Consistent inventory turn (cash flow).
- Right composition (matching customer demand).
- Realistic pricing (matching market).
- Aging discipline (avoiding capital lock-up).
- Buyer discipline (avoiding overbid situations).
- Communication of issues before they become bigger problems.

---

## 18. Deferred Ideas

Ideas that surfaced during Inventory/Acquisition research but
belong to other departments' future research. Recorded briefly;
not expanded.

**Recon** — the entire recon workflow (see companion
`RECON_MAPPING.md`).

**Sales** — cross-shopper conversation handling, competitive
pricing customer-facing narrative, trade appraisal customer
transparency, sales-manager desk workflow.

**F&I** — book-value data source integration for lender-facing
book-outs, subprime-tier vehicle-eligibility flagging,
chargeback prediction on new acquisitions.

**Accounting** — real-time per-unit cost accumulation (the
ledger sub-topic in `VEHICLE_CENTRIC_PIVOT.md`), floor plan
interest allocation to per-unit gross calculation, wholesale
disposition accounting workflow.

**Titles** — auction title tracking dashboard, out-of-state
title handling, title chargeback risk monitoring, duplicate
title workflow for lost titles.

**Marketing** — demand-signal-driven acquisition, seasonal
marketing calendar tied to buying, market intelligence
integration (auction data → pricing → advertising).

**Auction Intelligence** — historical auction performance,
buyer-specific auction attendance ROI, per-source acquisition
quality analytics, buyer-decision-support platform.

**Wholesale Network Management** — dealer-to-dealer wholesale
relationships tracking, disposition-buyer identification,
online wholesale platform integration, wholesale pricing
benchmarking.

**Photo & Listing Production** — photo capture workflow,
photo editing pipeline, listing description generation,
cross-platform syndication, listing performance analytics.

**Cross-Shopper Intelligence** — competitive lot inventory
tracking, competitor pricing scans, per-market competitive
position, pricing-strategy recommendations.

**Fleet & Commercial Acquisition** — fleet disposal channel
management, commercial account acquisition (multi-unit
selling to fleet buyers), specialty inventory (RVs,
motorcycles, work trucks) if the store carries them.

**BHPH-Specific Buying** — deep-subprime-appropriate vehicle
selection (older, cheaper, reliable), BHPH portfolio
appropriateness (units that will hold up for the loan term),
BHPH acquisition targeting (buying units that BHPH customers
finance well).

Each of the above deserves its own research session before
implementation.

---

## How to use this document

**For engineers and product people** starting inventory /
acquisition / pricing / disposition work: read sections 1–3
first (the landscape, the sources, the buying decision).
Those sections carry the mental model everything else builds
on. Read section 17 (dependencies) before designing anything
that connects to other departments. Section 16 (automation
opportunities) is where product ideas start — but each
opportunity should be developed into its own scoped plan
before implementation.

**For AI agents** starting an Inventory-related session: this
document is source-of-truth for how independent dealerships
actually source and manage inventory. If anything you're
asked to do contradicts what's described here, push back.
Particular anti-patterns to flag:
- Any suggestion that AI should make final buying decisions
  autonomously. Buying decisions carry portfolio impact and
  belong to human judgment.
- Any suggestion that pricing should be fully algorithmic
  without human review. Market conditions and store-specific
  factors always modify algorithm output.
- Any suggestion that aged inventory decisions should be
  fully automated. Wholesale-out decisions have relationship
  and cash-flow implications the algorithm won't see.
- Any suggestion that acquisition targeting should be based
  solely on prior sales data. Fresh market signals, current
  auction dynamics, and competitive positioning all matter.

**For domain experts** reading this document: this is a
snapshot of common indie practice. Every market has quirks
(regional vehicle preferences, local wholesale networks,
state-specific title complications). Corrections and
additions are welcome and expected as the platform evolves.

**Update discipline.** Update this document when:
- Auction platform market share shifts materially.
- New pricing / book-out sources gain traction.
- Regulatory changes affect acquisition (title branding,
  disclosure rules, dealer buying restrictions).
- Common industry-benchmark metrics shift meaningfully.

Do **not** update this document with:
- Specific software product feature reviews.
- Auction platform bid strategies or algorithmic tactics.
- Personal opinions about specific vendors or auctions.
- Implementation designs.

---

## Glossary — inventory / acquisition terms used in this
document

- **ACV** — Actual Cash Value. Trade acquisition value set by
  the used-car manager.
- **Advance rate** — Percentage of book value a floor plan
  lender will advance on a specific vehicle.
- **Aged inventory** — Vehicles in stock beyond typical retail
  windows (60+ days, worse at 90+, problem at 120+).
- **Aging bucket** — Category grouping (0-30, 31-60, 61-90,
  91-120, 121+).
- **Arbitration** — Formal dispute process at an auction over
  undisclosed condition issues on a purchased vehicle.
- **Auction fees** — Buyer or seller fees charged by the
  auction house per transaction.
- **Book-out** — The process of looking up a vehicle's value
  in one or more pricing guides.
- **Book value** — Value reported by a pricing guide (KBB, JD
  Power, Black Book, MMR).
- **Buy box** — Not the same as F&I lender buy box. In
  acquisition context, informal store criteria for what to
  buy (body class, price point, mileage range, etc.).
- **CPO** — Certified Pre-Owned. OEM-affiliated used-car
  program; not typical at indie.
- **Curtailment** — Principal paydown on a floor plan loan
  required at defined intervals.
- **DMS** — Dealer Management System.
- **ELT** — Electronic Lien and Title.
- **Floor plan** — Revolving line of credit collateralized by
  inventory.
- **Front-line ready** — Vehicle completely prepared and
  available for retail sale.
- **KBB** — Kelley Blue Book.
- **LTV** — In inventory context, floor plan advance as
  percentage of vehicle value.
- **Manheim** — Major North American auction company (owned
  by Cox Automotive).
- **MMR** — Manheim Market Report. Wholesale auction pricing
  data.
- **NADA / JD Power** — Traditional dealer vehicle pricing
  guide, now branded JD Power.
- **Out of trust** — Floor plan audit finding: a
  floor-planned vehicle missing without payoff. Serious.
- **PSI** — Post-Sale Inspection. Optional paid mechanical
  inspection at an auction after purchase.
- **Reprice** — Adjusting a vehicle's retail price after
  aging or market change.
- **Simulcast** — Auction where in-lane and online bidders
  compete simultaneously.
- **Stock number** — Unique dealer identifier for a specific
  vehicle unit.
- **Turn / turn rate** — Inventory turnover (units sold per
  year / average units in inventory).
- **Walk-away number** — Maximum price a buyer will pay for a
  specific vehicle at auction.
- **Wholesale** — Sale of a vehicle to another dealer or back
  to auction, typically at wholesale (not retail) price.
- **Wholesale-out** — Disposition of a vehicle through
  wholesale rather than retail.

---

## Related research

- `RECON_MAPPING.md` — Recon department; downstream from
  acquisition, upstream of front-line-ready.
- `FINANCE_DEPARTMENT_MAPPING.md` — F&I; consumes inventory
  for retail sales.
- `SALES_DEPARTMENT_MAPPING.md` — Sales; consumes inventory
  and drives demand signal back to acquisition.
- `ACCOUNTING_DEPARTMENT_MAPPING.md` — Accounting; tracks
  every inventory transaction, floor plan mechanics, per-unit
  cost accumulation.
- `VEHICLE_CENTRIC_PIVOT.md` — Architectural plan for building
  software that supports the vehicle-side operations described
  in this document (and in `RECON_MAPPING.md`).
- `INDEPENDENT_DEALER_PIVOT.md` — Established the indie-first
  scope this document uses.

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

*End of Inventory & Acquisition Department mapping.*
