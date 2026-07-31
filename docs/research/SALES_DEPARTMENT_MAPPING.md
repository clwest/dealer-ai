---
title: "Customer Acquisition & Sales Department — Operational Mapping"
status: reference
type: research
generated: 2026-07-31
scope: Independent used-car dealership customer acquisition, sales, CRM, and follow-up operations
voice: Experienced salesperson / sales manager / general manager / dealership owner
companion_docs:
  - "FINANCE_DEPARTMENT_MAPPING.md"
  - "ACCOUNTING_DEPARTMENT_MAPPING.md"
  - "VEHICLE_CENTRIC_PIVOT.md"
  - "INDEPENDENT_DEALER_PIVOT.md"
authoritative_for:
  - How indie used-car dealerships actually acquire customers, sell vehicles, and build long-term relationships
  - The operational reality of sales work at small-to-mid indie stores
not_authoritative_for:
  - Franchise BDC operations, OEM lead-management programs, or captive-return workflows (mentioned only for contrast)
  - CRM product features / vendor comparisons (this document is not a CRM feature review)
  - Advertising platform mechanics (rate cards, bid strategies)
  - Any implementation design
---

# Customer Acquisition & Sales Department — Operational Mapping

> **What this is.** A research artifact documenting how the sales
> organization of an independent used-car dealership actually
> acquires customers, sells vehicles, and builds repeat business.
> Written from the perspective of experienced salespeople, sales
> managers, general managers, and owner-operators who have
> personally sold cars — not from the perspective of software or
> consultants.
>
> **Who this is for.** Anyone (engineer, agent, product person)
> touching sales, CRM, lead-management, advertising, or customer
> relationship work in the Dealer AI Kit. Read this before
> opening a code editor or a wireframe tool.
>
> **What this is NOT.** Not a CRM feature review. Not an
> advertising platform comparison. Not a training manual for
> salespeople. Not an implementation plan. Not a critique of
> specific software.
>
> **Core philosophy.** Sales is not "closing deals." Sales is the
> operational bridge connecting nearly every department in the
> dealership. Sales touches inventory (what's available and what
> to promote), recon (what's ready vs. incoming), finance (what
> the customer can be structured into), accounting (deal booking,
> commissions, funding), marketing (which lead sources produced
> this customer), ownership (pricing, trade values, deal
> approvals), and — most importantly — customers themselves, whom
> the store depends on both for the current sale *and* for repeat
> and referral business years later. The purpose of sales is to
> help the right customer purchase the right vehicle in a way
> that produces a profitable transaction *and* a customer who
> will return, refer, and review favorably. A store that closes
> a lot of deals but produces no repeat customers is running an
> extraction business, not a dealership.

---

## Purpose & scope

The Dealer AI Kit's vehicle-centric pivot proposes making every
stock number a living operational record with lifecycle and
ledger (see `VEHICLE_CENTRIC_PIVOT.md`). Sales sits at the point
where that operational record meets a human being who might buy
it. Sales is also the department that generates the *demand*
side of the entire operation — no customer acquisition, no sales,
no reason to have inventory or F&I or accounting.

Before any sales-adjacent architecture is designed, this document
preserves the operational knowledge of how indie dealerships
consistently generate traffic, convert shoppers, and build the
kind of repeat business that keeps small operators alive year
over year.

**Scope boundary:** the *independent used-car dealer* scope
applies. That means:

- Small to mid-sized store (typically 2–8 salespeople, sometimes
  1 owner + 1 salesperson).
- Mixed-make used inventory.
- No OEM captive lease-return pipeline, no OEM CPO lead feed, no
  factory-managed CSI survey program.
- No dedicated BDC (Business Development Center) in most cases —
  owner or one salesperson handles internet leads part-time.
- Owner is often on the floor and personally involved in pricing,
  trade values, and TO ("turn-over") conversations.
- Community reputation is closer to survival than to marketing.
- 40–60% of business from repeat + referral in mature stores.
- Third-party listing sites (AutoTrader, Cars.com, CarGurus,
  Facebook Marketplace) are the largest single source of leads
  for most modern indies.

Where franchise practice differs materially, this document notes
the contrast briefly. It does not attempt to fully document
franchise BDC operations, OEM lead programs, or manufacturer
incentive-driven sales motions.

---

## Voice & caveats

The voice is that of a working salesperson or sales manager on
the floor. Terms are used as they're spoken ("TO the customer,"
"be-back," "close ratio," "work the phones," "walk the lot,"
"heat sheet," "hot leads," "cross-shopper"). Formal terms and
operator shorthand appear together where useful.

**Percentages, ranges, and costs.** Where specific figures
appear (closing ratios, ad-spend ranges, show rates), they are
illustrative of common experience across many indie stores.
Individual store performance varies enormously by market, price
point, staff quality, and inventory mix. Treat this document as
a description of the *shape* of sales work, not as a source of
truth for specific benchmarks — for those, use current NADA /
NIADA / NCM benchmarking data.

**Advertising platform caveats.** Platforms named in this
document (AutoTrader, Cars.com, CarGurus, Facebook Marketplace,
Craigslist, etc.) are used *as examples* of category leaders.
Their mechanics change, their pricing changes, their algorithm
behavior changes. This document describes their *role* in the
lead ecosystem, not their current product features.

**Compliance caveats.** Sales operates within compliance frames
(FTC Used Car Rule, state advertising laws, TCPA for
communications, fair-lending in product/pricing offerings). Some
compliance points are mentioned; a full compliance program is
covered under `FINANCE_DEPARTMENT_MAPPING.md` §6 and a future
`COMPLIANCE_DEPARTMENT_MAPPING.md`.

---

## 1. The indie sales landscape

Before documenting the workflow, some context on the environment
sales operates in at an indie store. This shapes everything that
follows.

### 1.1 The people

A typical indie sales team:

- **Owner-operator** — the person whose name is on the door.
  Often on the floor daily. Makes pricing decisions in real time.
  Signs every deal. Handles VIP customers personally. May also
  be the sales manager / F&I / dispatcher / everything.
- **Sales manager** — sometimes a distinct role, often the owner
  wearing that hat. Approves pricing, does turn-overs (TOs),
  monitors the deal desk.
- **Salespeople** — typically 2–8 in an indie store. Some are
  veterans (10+ years), some are green (first sales job). Some
  are family (owner's kids, spouse, cousins). Some are
  commission-only, some are salary-plus-commission, a few are
  salary-only.
- **Internet/BDC person** — many indies don't have one. When they
  do, this person answers internet leads, sets appointments,
  and hands off to a floor salesperson for the actual sale.
  Sometimes this is a part-time salesperson filling downtime.
- **Lot porter** — moves vehicles around, does light detail,
  fuels for delivery. Often the first person a walk-in interacts
  with.
- **Office manager** — see `ACCOUNTING_DEPARTMENT_MAPPING.md`.
  Not sales staff but critical to sales support.

Franchise contrast: franchise stores typically have 15–30
salespeople, a formal 3–5 person BDC, dedicated internet sales
managers, dedicated finance managers, a used-car manager separate
from a new-car manager, sometimes a dedicated fleet manager.
Indie compresses all those roles into a much smaller headcount.

### 1.2 The physical environment

- **The showroom / office** — where paperwork happens, where
  desks are, where customers sit to negotiate. Sometimes a
  literal converted trailer at very small operations.
- **The lot** — where the inventory sits. Often organized by
  body class (trucks on one row, SUVs on another) or by price
  point or by arrival date.
- **The service area** (if in-house) — where recon happens.
  Customers occasionally interact with it (waiting for delivery).
- **The phone** — a big deal. The main lot phone rings all day.
  Salespeople rotate answering.

### 1.3 The customer profile at indie used

Different from franchise:

- **Payment-focused** — most customers walk in with a payment in
  mind, not a price. "I can do $400 a month" is the opener.
- **Cash-and-carry** — a meaningful percentage of indie
  customers pay full cash, especially at lower price points
  ($5k-$12k range).
- **Credit-challenged** — indies serve a wider credit spectrum,
  including a lot of subprime and no-score customers who franchise
  stores often turn away or route to captive subprime only.
- **Trade-heavy** — most customers have a trade-in, often with
  negative equity.
- **Repeat/referral heavy** at mature stores — the store's own
  past customers keep coming back and sending their families.
- **Local** — customers typically come from within 30–50 miles
  of the store (except for very specialty inventory).
- **Time-sensitive** — customer often needs a car *now* because
  the current one broke down or is unreliable. Urgency is a real
  factor.

### 1.4 The economics of an indie sale

Rough per-unit gross profit landscape (illustrative, varies
enormously):

- **Front-end (vehicle) gross:** $1,000–$3,500 average, sometimes
  higher on specialty units, sometimes minimal or negative on
  aged inventory pushed to move.
- **F&I (back-end) gross:** $800–$2,000 average per copy (see
  `FINANCE_DEPARTMENT_MAPPING.md` §4).
- **Total gross per unit:** roughly $2,000–$5,000 target for
  most indies.

An indie doing 30 units/month at $3,500 average total gross
is producing $105,000/month total gross — from which everything
else (rent, salaries, floor plan interest, advertising, office
expenses, owner draw) must come. Every unit that walks off the
lot without a deal is real money the store doesn't have.

This economic reality shapes the urgency around every sales
motion. There is no OEM incentive money to fall back on.

### 1.5 The seasonal / calendar rhythm

Sales at indie is seasonal, with regional variation:

- **Tax refund season** (mid-Feb through April) — biggest sales
  season in most US markets. Customers have cash for down
  payments. Subprime volumes spike.
- **Spring** (May) — post-tax lull, sometimes strong.
- **Summer** (June-August) — steady, family car purchases (school
  starts).
- **Fall** (September-October) — slower; back-to-school spend
  competes.
- **Late fall / early winter** (November-December) — depends on
  market. Warmer regions still steady; snowbelt slows.
- **End-of-month** — every month, deals pile at month-end as
  salespeople push for their monthly quota / bonus.

Owners plan advertising, inventory, and staffing around these
patterns.

---

## 2. Customer Acquisition

Where customers come from. This is arguably the single most
important area of research because customer acquisition is where
the money starts (or doesn't).

### 2.1 The lead-source landscape at a glance

A typical modern indie's lead mix might look like:

| Source | Rough share of leads | Rough share of sales |
| --- | --- | --- |
| Third-party listing sites (AutoTrader, Cars.com, CarGurus) | 30–45% | 30–40% |
| Facebook Marketplace | 15–30% | 15–25% |
| Google Business Profile / organic search | 10–20% | 10–20% |
| Repeat and referral | 10–25% | 25–40% |
| Walk-in / drive-by | 5–15% | 10–20% |
| Craigslist (in markets where still relevant) | 2–10% | 2–8% |
| Traditional media (radio, newspaper, direct mail) | 0–10% | 0–10% |
| Owner-arranged (fleet, sponsorships, community) | 0–10% | 5–20% |

**Note:** "share of leads" and "share of sales" don't match
because different sources close at different rates. Repeat and
referral has a much higher close rate than a cold internet
lead. A store that does 20% of its leads from repeat/referral
might get 40% of its sales from that segment.

**Note also:** attribution is genuinely hard. Customers rarely
have a single "source." They see you on AutoTrader, check your
Google reviews, look at your Facebook page, then inquire via
Facebook Marketplace. Which source gets credit? The store's
CRM will attribute it to whichever channel the lead formally
entered on, but the real customer journey was multi-touch.

### 2.2 Digital sources — third-party listing sites

The most important paid category for modern indie sales.

**AutoTrader.com** — one of the two largest listing marketplaces.
Historic industry incumbent. Charges dealers a monthly
subscription plus per-vehicle listing costs. Package tiers vary;
smaller stores often pay $800–$2,000/month; larger stores much
more. Lead quality generally good; lead volume varies by market.

**Cars.com** — the other major incumbent. Comparable pricing
model to AutoTrader. Some markets favor one over the other. Most
stores subscribe to both.

**CarGurus** — newer entrant that grew fast on a value-transparency
positioning ("deal ratings" — Great Deal, Good Deal, Fair Deal,
based on their algorithm comparing your price to market). Free
tier for basic listing, paid tier for more visibility and
enhanced leads. Widely popular with price-sensitive shoppers.
Some dealers love it (drives cross-shopper leads); some hate
it (deal-rating pressures pricing).

**TrueCar** — pricing-transparency focused. Historically strong
with certain buyer segments. Less dominant now but still present.

**Carfax Listings** — Carfax offers vehicle listing as a sidecar
to its vehicle history report product. Rising in relevance.

**Craigslist** — free (in most markets) but requires manual
posting. Historic mainstay for indies; declining in relevance
in many markets due to Facebook Marketplace, but still meaningful
in certain regions and price points. Lead quality is highly
variable — a lot of low-intent inquiries and spam.

**Facebook Marketplace** — free (mostly), consumer-familiar,
massive audience. Has become the #1 or #2 source for many
modern indies. Requires manual posting per vehicle (or a
listing-integration service). Lead conversation happens in
Facebook Messenger rather than by phone/email — different
communication cadence. Consumer skew is younger, more mobile,
faster-response-expected.

**Regional / niche listing sites** — depending on market:
Kijiji (Canada), specific classified sites for certain vehicle
classes (trucks, exotics, RVs, motorcycles that dealers
occasionally handle).

**Cross-posting** — most dealers post the same inventory across
multiple sites. Some use listing-syndication services (part of
DMS or standalone) that push inventory to multiple platforms
from one entry. Manual cross-posting is a real time drain.

### 2.3 Digital sources — dealer website

The dealer's own website:

- **Inventory display** — customers browse the store's inventory
  with photos, prices, features.
- **Contact forms** — leads via web forms (email, sometimes with
  a callback request).
- **Live chat** — increasingly common; often outsourced to a
  chat service that answers 24/7 and forwards qualified leads
  to the dealer.
- **Text / SMS click-to-call from mobile pages.**
- **Trade-in valuation tools** — customer enters trade info,
  gets an estimate, becomes a lead.
- **Pre-approval / credit application forms.**

**Reality at indies:** many indie websites are template-based,
functional but not aggressively marketed. SEO is often
underinvested. Website leads are typically a smaller share of
total leads than third-party sites but tend to be higher-intent
(customer already knows the store).

### 2.4 Digital sources — Google Business Profile and organic search

**Google Business Profile** (formerly Google My Business) — free.
The dealer's listing in Google Maps and Google Search. Massive
visibility when well-maintained: photos, hours, phone, website,
reviews, posts.

Best practices (universally acknowledged but often missed at
indies):
- Complete profile with accurate hours, phone, address.
- Regular photo updates (lot, staff, recent arrivals).
- Prompt response to all reviews (positive and negative).
- Encourage every satisfied customer to leave a review.
- Use "Posts" for new arrivals or promotions.

Google reviews are load-bearing. Prospective customers filter by
star rating and read recent reviews before calling. A store at
3.2 stars with recent 1-star reviews for rude service will lose
leads before any conversation happens.

**Organic search / SEO** — the dealer's ranking in Google search
results for terms like "used cars [city]" or "used trucks near
me." Requires an SEO-optimized website, active blog / content,
local citations, and backlinks. Rarely a strength at indies
without dedicated marketing help.

### 2.5 Digital sources — paid search and social advertising

**Google Ads (search + display)** — paid placements in Google
search results and on the Google Display Network. Requires
budget and skill (or an agency). Common at franchise, less
common at indies, growing.

**Facebook / Instagram / Meta ads** — paid targeted ads on Meta
platforms. Powerful targeting (demographics, interests,
location, income proxy). Cheaper than Google search per click
but generally lower intent. Some indies use Meta ads well for
BHPH audiences; others waste money.

**YouTube ads** — pre-roll and in-stream ads on YouTube. Growing
category. Rare at indies; occasional experiments.

**Retargeting** — ads that follow a person who visited your
website. Available on Google Display, Meta, other platforms.
Effective when configured right.

**OTT (over-the-top TV) / connected TV** — ads on streaming
platforms (Hulu, Roku, Peacock ads). Growing category. Some
indies experiment; most don't.

### 2.6 Digital sources — email and text messaging

**Email marketing** — email campaigns to past customers, house
list, and lead databases. Works well for repeat/service
customers, less well for cold prospects. Deliverability is a
constant challenge.

**SMS marketing** — text campaigns to customers who have opted
in. Higher open rates than email but more compliance-sensitive
(TCPA — Telephone Consumer Protection Act — has real teeth).

### 2.7 Traditional sources

Still relevant, though generally shrinking as a share.

**Drive-by traffic and lot signage** — the location, the sign,
the lot's visibility from the road. Every dealer has an intuitive
sense of drive-by conversion (how many people who see the lot
actually stop). Corner locations do better; back-of-plaza
locations do worse.

**Lot merchandising** — window flyers ("SOLD," "Reduced,"
"Special Financing"), balloons, banners ("Grand Opening,"
"Tax Season Special"), pricing on windshields, staff outside
being visible.

**Newspaper advertising** — declining but not dead. Some
regional markets and demographics still respond. Weekend
inserts. Classified sections.

**Radio** — local AM/FM ads. Effective in some markets
(particularly for BHPH targeting where the customer profile
maps to certain formats: country, urban, sports, talk).
Owner-voiced radio spots are common at indies ("Hi, I'm
[owner's name] at [store name] — come see me for the best used
truck deal in [city]"). Radio is brand-building more than
direct-response.

**Direct mail** — printed postcards, flyers, "special offer"
mailers. Used for BHPH prospecting (targeting lower-income ZIP
codes with "$500 down!" mailers), lease-maturity mailings
(mostly franchise), and community events. Response rates
typically low (0.5–2%) but consistent.

**Community sponsorships** — Little League, church raffles, high
school sports teams, 5K runs. Long-tail brand building.
Owner-relationship-driven. Rarely produces measurable direct
leads but builds community presence over years.

**Local events and shows** — indie car shows, community festivals,
county fairs. Some dealers set up a small booth or park inventory
at events. Brand-visibility play.

### 2.8 Relationship sources — repeat and referral

For mature indie stores, this is the biggest and most
undermeasured category.

**Repeat customers** — past buyers who come back for their next
vehicle. Repeat purchase cycle is typically 3–5 years for
average buyers, 1–3 years for enthusiasts or fleet-adjacent
buyers, indefinite for buyers who keep vehicles until failure.

**Referral customers** — new customers who came in because a
past customer told them to. "My cousin bought a truck from you
last year and told me you'd take care of me" is one of the
most valuable openings a salesperson can hear.

**Friends and family** — one degree removed from referral. A
buyer's spouse, sibling, adult child, parent.

**Business relationships** — small business owner who buys a
work truck, and their business partners follow. Fleet accounts
(small local companies with 3–20 vehicles).

**Service customers** — for stores with in-house service, the
service bay is a lead generator. Customer comes in for repair
of their current vehicle, salesperson has a conversation about
upgrading. Powerful in the right setup.

**Previous buyers with new needs** — the family that bought a
Malibu three years ago is now expecting their second child and
needs a minivan. Salespeople who track their customers' life
events can preempt the shopping cycle.

**Referral programs** — some stores pay cash ($100–$500) or
give gift cards for every referral that becomes a sale.
Effective when the program is simple and prompt.

Owner-operator note: at mature indie stores, the owner
personally knows a substantial fraction of the community's
customers. A good owner remembers birthdays, family updates,
which kid is at which college, what the customer does for work.
That relationship is the reason those customers keep coming back
even when a bigger store advertises lower prices. **This is
extremely hard to systematize and impossible to fake.**

### 2.9 Inbound contact channels

How leads actually reach the store:

**Phone calls** — the classic. Lot phone rings, salesperson
answers. Customer typically asking about a specific vehicle
they saw online. Phone-up conversion (how many phone-up
inquiries become appointments) is a critical metric.

**Walk-ins** — customer physically arrives without prior contact.
Traditionally the largest single source; declining as customers
research online first.

**Internet leads** — form submissions from listing sites, own
website, or third-party lead aggregators. Delivered by email or
directly into the CRM. Response time is critical — leads not
responded to within an hour convert at a fraction of the rate
of leads responded to within 15 minutes.

**Text messages** — SMS inquiries from customers who saw a
listing. Growing rapidly; younger customers prefer text over
phone. Requires the store to have a dedicated business text
number (personal-cell texting is compliance-fragile).

**Facebook Messenger** — messages from Facebook Marketplace
listings or the Facebook business page. Cadence is different
from other channels — customers expect very fast responses on
Messenger.

**Live chat** — website chat inquiries. Often outsourced to a
chat service.

**Email inquiries** — customer directly emails the sales
address. Less common than form-generated leads.

**Trade requests** — customer submits a trade-in appraisal
request. Often an early-stage lead; the customer is comparing
trade values across dealers before shopping.

**Appointment requests** — customer explicitly asks to schedule
a time to visit. Higher intent than a generic inquiry.

**Social media inquiries** — DMs on Instagram, Facebook, or
occasionally Twitter/X or TikTok. Growing channel.

### 2.10 Lead source measurement — the attribution problem

Every store wants to know which lead sources produce which sales.
Reality:

- **Multi-touch customer journeys.** A customer sees you on
  AutoTrader (touch 1), Googles you and reads reviews (touch 2),
  visits your Facebook page (touch 3), inquires via Facebook
  Marketplace (touch 4). CRM captures touch 4 as "source." Ad
  budget analysis credits Facebook. Reality: all four touches
  mattered.
- **Self-reported sources.** Customers asked "how'd you find us?"
  often don't remember accurately.
- **Referral pipe.** Referrals are often mis-attributed to whatever
  channel the customer used to contact (they say "I heard about
  you" but the CRM logs "walk-in").
- **Repeat customers.** Someone who bought before may see an
  AutoTrader ad, but they're really a "repeat" customer — the
  ad didn't create the customer, it just reminded them.

**Attempted attribution methods:**

- **First-touch attribution** — credit the first channel where
  the customer engaged. Hard to measure because early touches
  are invisible.
- **Last-touch attribution** — credit the channel where the
  customer converted (form submitted, phone rang). Easy to
  measure, misleading because it ignores earlier influence.
- **Multi-touch attribution** — split credit across touches.
  More sophisticated; requires tracking infrastructure most
  indies don't have.
- **Self-report at delivery** — sales asks the customer at
  delivery "how did you originally find us?" Better than
  nothing; often inaccurate.
- **Dedicated tracking phone numbers** — each ad source uses a
  unique tracking phone number. Calls to that number get
  attributed. Requires phone-tracking service.
- **UTM tagging on web ads** — track which ad campaign brought
  the web visitor.

**Owner reality.** Most indie owners have a general sense
("AutoTrader produces a lot for us," "CarGurus is a waste,"
"Facebook Marketplace has been huge lately") based on
observation. Formal attribution is rarely done well. Advertising
budgets get allocated by feel and by year-over-year comparison
of aggregate results.

### 2.11 Advertising ROI in practice

The owner's core question: "Is this advertising working?"

Common frameworks:

- **Cost per lead (CPL)** — total spend on a source divided by
  leads produced. Useful for comparing sources; misleading if
  lead quality varies wildly.
- **Cost per sold unit** — total spend on a source divided by
  sold units attributed. Better than CPL; requires attribution.
- **Lifetime value (LTV) per source** — average revenue over
  years from customers acquired via a source. Requires long-term
  tracking; almost no indie does this well.
- **Payback period** — how many months of profit does it take
  to recoup the ad spend. Ties to CPL and close rate.
- **Aggregate month-over-month** — the crude but reliable
  metric. Store advertised $8k in June and did 35 units;
  advertised $10k in July and did 38 units; owner concludes
  the extra $2k was worth ~3 more units, or roughly $650/unit
  in incremental ad spend.

**Owner rules of thumb** vary by store but common ones:

- Ad spend should be roughly 5–15% of gross profit (industry
  average sometimes cited around 8–10%).
- Cost per sold unit target roughly $400–$800.
- Any source whose CPL/CPU is 2×+ the store average gets scrutiny.
- Any source whose lead volume drops month-over-month gets
  investigated.

**The "we can't measure it but we know it works" bucket.**
Community sponsorships, radio brand-building, repeat/referral —
these produce sales that can't be cleanly attributed but every
experienced owner knows they matter. Cutting these to "save
money" is a common mistake that erodes the store over years.

---

## 3. Sales Workflow — the road to sale

Every dealership has some version of "the road to sale." Formal
training programs teach 8, 10, or 12 steps. Real-world indie
practice is looser but recognizably similar. This section walks
the standard flow with indie-specific realities.

### 3.1 Greeting

The first 60 seconds of a customer's visit or call.

**Walk-in greeting** — customer enters the lot or showroom.
Ideally greeted within 30 seconds of arrival. Warm, unhurried,
open. Traditional openers ("Can I help you find something?") get
"I'm just looking" 80% of the time. Better openers focus on
comfort and rapport: "Welcome — first time here?" or
"Good morning, are you shopping for yourself or someone else?"

**Phone greeting** — every call answered within 3 rings, with
the store name and salesperson name. "Thanks for calling [Store
Name], this is [Name], how can I help you?" Callers who reach a
mumbled or delayed greeting hang up and try the next dealer.

**Internet lead first response** — response should go out within
15 minutes ideally, within an hour minimum. First response can
be text, email, or phone based on the lead type. Fast response
is one of the single biggest predictors of closing.

**Facebook Messenger response** — customer expects near-instant
reply. Response time expectations here are shorter than any
other channel.

### 3.2 Rapport and needs assessment (the interview)

The critical middle of the sales process. Also the part most
salespeople rush past.

Goal: understand who the customer is, what they're really
looking for, what their financial situation supports, and what
their timeline is.

**Rapport** — talk about non-vehicle topics first. Their day.
Their job. Their family. The weather. Where they live. Nothing
about cars. Two minutes of genuine human conversation dramatically
improves everything downstream.

**Needs assessment** — questions worth asking:

- What are you driving now? How's it working for you?
- What do you need this vehicle to do? (Commute, family, work,
  towing, off-road, mixed.)
- Passenger requirements? Cargo requirements?
- Fuel economy priorities?
- Any brands or models you're already considering?
- What features are non-negotiable? What would be nice-to-have?
- Are you buying for yourself, or for someone else (spouse,
  teen driver, aging parent)?
- Timeline — need one now, this week, this month, next few
  months?
- Have you shopped anywhere else? What did you see, what did you
  think?
- Cash purchase, financing, or open to both?
- Trade-in? Tell me about it.
- Ballpark budget — comfortable payment range, or comfortable
  total price range?
- Credit story — anything you want me to know upfront?

**Skilled salespeople ask, listen, and take notes.** Poor
salespeople launch into pitching a specific vehicle before
understanding what the customer needs.

**Owner reality:** the best salespeople treat this stage like a
consultation, not an interrogation. The customer walks away
feeling *understood*, not sold to.

### 3.3 Vehicle selection and inventory search

Based on the interview, the salesperson identifies 1–3 vehicles
worth showing.

**Approach patterns:**

- **Show three** — the classic. Present 3 vehicles across a
  range (mid-tier, upgraded, budget alternative). Customer picks
  or narrows.
- **Show the exact match** — if the interview surfaced a very
  specific need, show the one vehicle that fits and start with
  that.
- **Show the customer around the whole lot** — walk-the-lot
  approach. Customer sees the range, salesperson observes what
  the customer's eyes go to.

**Inventory search reality** at indies:

- Salesperson needs current inventory knowledge — what's on the
  lot, what's front-line ready, what's still in recon (with an
  ETA), what's arriving soon, what just sold.
- New arrivals every week. Recon status changes daily. Aged
  inventory gets repriced.
- Some stores publish a "heat sheet" daily — a printed or
  emailed summary of front-line ready inventory, priced,
  suggested first-choice for various customer profiles.
- Sales manager or owner often walks the lot with the sales team
  each morning to note new arrivals, recon completions, and
  priorities.

### 3.4 Walk-around

The salesperson walks the customer around the selected vehicle,
pointing out features, benefits, and story.

**Standard walk-around structure:**

- Start at the front (grille, headlights, hood).
- Drivers side (paint, wheels, side profile).
- Rear (trunk/cargo space, taillights, exhaust).
- Passenger side (finish walk).
- Under the hood if the customer cares (engine size, condition).
- Interior driver's seat (adjust for the customer, show controls).
- Interior features (infotainment, sound system, backup camera).
- Rear seats (space, folding, child seat if relevant).
- Cargo area / trunk.

**Feature-benefit selling** — connect features to the customer's
stated needs. Don't just say "backup camera." Say "for those
tight parking spots at the school pickup, the backup camera
makes it easier to see kids and other cars." Personalize.

**Story-selling** — vehicle history matters. "This one came
from a local family, one owner, garage-kept, all maintenance
records included." Or: "This is a trade from a customer who
bought a bigger truck for work — this one was too small for his
new job but perfect for a commuter."

### 3.5 Demonstration drive

Getting the customer behind the wheel. Critical step.

**Best practice at indies:**

- Salesperson drives the vehicle first (short loop) to a
  planned demo route.
- Customer takes the wheel at a safe location (parking lot).
- Planned route: mix of city, highway, and a curvy road to
  show handling.
- Salesperson in the passenger seat, not talking too much.
  Ask the occasional question: "How does the steering feel?"
- Let the customer *feel* the vehicle. Comfort, visibility,
  power, brakes, silence at highway speed.

**Some indies skip the demo drive** on lower-priced units to
save time. This is usually a mistake — customers who drive close
more than customers who don't.

**Insurance and paperwork** — some states require a temporary
insurance certificate or specific paperwork before the customer
drives. Compliance varies.

### 3.6 Trade evaluation

If the customer has a trade, this can happen before, during, or
after the demo drive. Common flow:

- Salesperson gets basic trade info during the interview (§3.2).
- Someone (used-car manager, buyer, sometimes an outside
  appraiser) walks the trade, notes condition, evaluates.
- Book-out on multiple sources (KBB, Manheim MMR, JD Power, plus
  reference to recent auction data).
- Wholesale value determined.
- Retail-equivalent (what the trade could be reconditioned and
  retailed for) considered.
- Trade allowance offered to customer — often slightly above
  wholesale, sometimes closer to retail (with corresponding
  reduction elsewhere in the deal).

**Trade appraisal politics:**

- Customer thinks trade is worth more than it is. Almost always.
- Salesperson delivers the number — the customer's face falls.
- Salesperson explains the wholesale market, reconditioning
  costs, "the number we can be in it for," etc.
- Sometimes the trade allowance is negotiable; sometimes it's
  firm.
- If negative equity exists, the conversation gets harder (see
  `FINANCE_DEPARTMENT_MAPPING.md` §3.8).

**Trade shopping** — some customers shop their trade at multiple
dealers before deciding where to buy. First trade appraisal
often sets an anchor.

### 3.7 Payment discussion and write-up

Now the deal math starts. Salesperson has to know or find out:

- Vehicle price (posted price is starting point; management may
  authorize discount).
- Trade allowance.
- Cash down (if any).
- Payment target the customer stated.
- Rough credit profile.
- Term preference (if any).

**Write-up format** varies:

- **Four-square** — classic layout with vehicle price, trade,
  down payment, and monthly payment in four quadrants. Customer
  and salesperson negotiate each quadrant.
- **Simplified quote sheet** — modern indie often uses a simple
  printout: vehicle price, tax, fees, monthly payment estimate.
- **Verbal negotiation** — smaller stores, especially with
  cash buyers, may negotiate verbally without a paper write-up.

**Payment-first vs price-first customers:**

- **Payment-first** customers want a monthly number. Salesperson
  works backward from payment to price (given credit tier and
  term).
- **Price-first** customers want the vehicle price. Salesperson
  quotes the price and lets F&I structure the payment.

Most indie customers are payment-first. Franchise buyers are
more mixed.

### 3.8 Manager involvement — the TO ("turn-over")

At some point in the negotiation, the salesperson may TO the
customer to the manager or owner. Reasons:

- Salesperson can't or won't authorize a needed discount.
- Customer is stuck at a price/payment the salesperson can't
  bridge.
- The manager wants to build rapport with the customer
  personally.
- The customer requested to "talk to the manager."
- The salesperson is losing the deal and needs help.

**A good TO** is warm and consultative, not confrontational.
The manager greets the customer, listens to the concern, and
offers a solution or explanation. Sometimes the manager can
approve a discount the salesperson can't. Sometimes the manager
just needs to reassure the customer.

**At owner-operated stores**, the owner often IS the TO. Every
deal that gets close goes through the owner.

### 3.9 Finance transition

Once the price/payment is agreed and the customer decides to
buy, sales hands off to F&I (see `FINANCE_DEPARTMENT_MAPPING.md`).

**A clean hand-off includes:**

- Customer profile (name, contact, credit story if known).
- Vehicle info (stock number, deal terms).
- Trade info (with payoff quote if available).
- Cash down amount.
- Payment target agreed.
- Any special promises made ("we'll throw in new floor mats,"
  "we'll deliver Saturday morning").
- Any red flags ("customer is very sensitive about their
  credit," "the wife hasn't decided yet — need to be careful").

**Sales stays involved** during F&I but usually steps back
during the actual product menu presentation. Sales sometimes
returns for the closing signature to congratulate the customer.

### 3.10 Vehicle delivery

The moment the customer takes possession. Often underweighted in
sales training but hugely important for CSI, referral generation,
and repeat business.

Typical delivery elements:

- Vehicle detailed (or at least freshly washed and vacuumed).
- Full tank of gas (customary at most indies).
- Fresh vehicle inspection.
- Owner's manual and second key.
- Customer walkthrough of vehicle features (5–20 minutes
  depending on complexity).
- Bluetooth pairing to the customer's phone.
- Explanation of any warranty coverage.
- Handoff of temp tag paperwork.
- Congratulations, photos (with customer permission — the sold
  customer with the car makes a great social media post).
- Introduction to service department (if in-house) for future
  needs.

**Delivery is where the "aftermath" starts.** A great delivery
makes the customer feel confident and taken-care-of, and
predisposes them to be a repeat / referral customer for years.

### 3.11 Customer education

Related to delivery but ongoing. Modern vehicles are complex —
customers often don't understand half the features. Salesperson
role includes:

- Walk through infotainment / touchscreen.
- Explain safety features (lane keep, adaptive cruise, collision
  warning).
- Bluetooth pairing.
- Voice command demo.
- Any tricky controls (headlight switches, wiper controls,
  parking brake).
- Maintenance basics (oil change intervals, fluid checks).
- What to do if the "check engine" light comes on.

Salespeople who invest in customer education have customers who
call them (rather than a random search) for follow-up questions
— which keeps the relationship active.

### 3.12 Follow-up and after-sale contact

The salesperson's job is not done at delivery. Follow-up
sequence typically:

- **24-48 hours post-delivery:** "How's the vehicle treating
  you? Any questions?"
- **1 week post-delivery:** "Everything still going well?"
- **30 days:** Check-in.
- **90 days:** Check-in.
- **6 months:** Check-in, birthday if known.
- **1 year:** Anniversary of purchase.
- **Ongoing:** Birthday, holidays, life events, service
  reminders, upgrade opportunities.

This is where CRM discipline matters. See §5.

### 3.13 Referral request

At the right moment (usually post-delivery, or during a
positive follow-up call), the salesperson asks:

"You've been great to work with — do you know anyone who might
be shopping for a vehicle? I'd love to take care of them the way
I took care of you."

Some stores have formal referral programs (cash, gift cards).
Some rely on informal ask.

**Timing matters.** Right after delivery is often too early
(customer hasn't had time to enjoy the car). 30-90 days post
delivery, when the customer is genuinely happy, is prime.

### 3.14 The "be-back" — customer returns to complete a sale

A "be-back" is a customer who visited or inquired, didn't buy,
and later returns. Some percentage of customers naturally
become be-backs — they need to sleep on it, discuss with a
spouse, sell their current car, wait for a paycheck.

**Statistics that most salespeople know:**

- Roughly 20% of unsold customers *will* buy a vehicle within a
  short window — the question is whether they buy from you or
  from a competitor.
- Follow-up is the single biggest determinant of be-back
  conversion.
- A customer contacted 3+ times after their visit is
  meaningfully more likely to return than a customer contacted
  once or not at all.

**Common salesperson mistake:** treating every un-sold customer
as a "lost" deal instead of a "future" deal. The follow-up
discipline for un-sold customers is where average salespeople
lose money and top salespeople make it.

---

## 4. CRM and Follow-up

CRM (Customer Relationship Management) at indie stores is a
mixed reality. Big-store franchise CRMs (VinSolutions, Elead,
DealerSocket) are overkill for many indies. Indies often use
lighter DMS-integrated CRMs, standalone lighter CRMs, or (at
smallest operations) spreadsheets and notebooks.

**The purpose of CRM is not the software.** The purpose is
maintaining a durable relationship with every customer and
prospect the store has ever touched, so that:

- Un-sold prospects come back later.
- Sold customers repeat 3-5 years later.
- Sold customers refer friends and family.
- Life-event opportunities are caught (family growing, kid
  turning 16, new job, retirement).

### 4.1 Lead / opportunity categories

CRM organizes contacts by stage:

- **Internet lead (new)** — just came in; not yet responded to
  or engaged.
- **Actively engaged (working)** — communicating, hasn't
  visited yet.
- **Appointment set** — coming in on a specific date/time.
- **Visited (un-sold)** — came in, didn't buy. Follow-up
  discipline critical.
- **Be-back** — returned after prior visit.
- **Sold customer (active)** — in delivery / recent post-delivery.
- **Sold customer (long-term)** — past customer in retention mode.
- **Service customer** — comes in for service on their vehicle,
  potential upgrade.
- **Do-not-contact** — opted out or asked not to be contacted.

### 4.2 Follow-up cadence — un-sold customers

Common cadences (top salespeople follow more disciplined
schedules):

- Day 0 (visit day): Same-day thank-you (call, text, or email).
- Day 1: Follow-up call to answer questions.
- Day 3: Check-in, offer additional inventory that fits their
  criteria.
- Day 7: Extended follow-up.
- Day 14: Special-offer check-in.
- Day 30: Long-form check-in.
- Day 60: If no response, one final long-form message.
- Day 90+: Move to long-term drip (monthly newsletter, new
  arrivals, seasonal specials).

**Reality:** most salespeople follow up 1–2 times and stop. The
disciplined 10-touch salespeople have 3–5× the be-back
conversion.

### 4.3 Follow-up cadence — sold customers

Common sequences:

- 24 hours post-delivery: "Everything great?"
- 1 week: Check-in, service intro if applicable.
- 30 days: Check-in.
- 90 days: Check-in.
- 6 months: Check-in, life-event ask ("anything new going on
  with the family?").
- 1 year: Anniversary of purchase.
- Ongoing: Birthdays, holidays, service reminders.

Some stores use email newsletters for the ongoing touch;
others use personal calls; the best use both, personalized.

### 4.4 Equity mining and upgrade opportunities

**Equity mining** — identifying past customers who have equity
in their current vehicle and could trade up.

Sources of equity:

- Vehicle appreciated (rare but happens; used SUV/truck market
  post-2020 saw appreciation).
- Loan paid down enough to exceed depreciation.
- Customer received a cash windfall (bonus, inheritance, tax
  refund).
- Customer's life circumstances changed (family growing,
  business succeeding, moving up).

Tools:
- Loan payoff estimates (based on original terms + time
  elapsed).
- Current vehicle value estimates.
- Difference = equity (or negative equity).
- Customers with meaningful equity get proactive outreach.

**Reality at indies:** rarely done systematically. When done,
big lift in repeat sales.

### 4.5 Repeat purchase cycles

Different customer types have different natural cycles:

- **Cash buyers of older vehicles:** 3–7 years, driven by
  vehicle failure/reliability.
- **Long-term financed buyers:** 4–6 years, near loan payoff.
- **Serial upgraders / enthusiasts:** 1–3 years.
- **Family expansion buyers:** driven by life events (kids,
  more kids, teen drivers, kids leaving home, retirement).
- **Business buyers:** driven by business growth, tax
  considerations, or vehicle failure.
- **Never-again buyers:** who had a bad experience. Won't be
  back. Might tell people.

The store's job in the middle years is to *stay top of mind*
so that when the natural cycle hits, they choose you.

### 4.6 Note discipline

The single most-cited CRM problem: notes.

- Salesperson has a great conversation with a customer.
- Learns the kids' names, spouse's job, that the customer is
  saving for their daughter's college.
- Doesn't write it down.
- Six months later, calls the customer, doesn't remember any
  of it, sounds like a stranger, customer disengages.

**Great notes include:**
- Family details (spouse name, kids' ages, pets).
- Job / employer.
- Vehicle preferences (make preference, feature must-haves).
- Trade info as it changes.
- Previous vehicles owned.
- Life events (upcoming vacation, house purchase, retirement).
- Concerns raised in prior visits.

**Great notes are the difference** between "another customer"
and "the family I know I can help."

### 4.7 Long-term relationship database

The most successful indie owners maintain a long-term customer
database — sometimes formal (CRM), sometimes informal
(handwritten notes, spreadsheets, personal memory). Customers
they sold to 10, 15, 20 years ago. Grandparents. Grandkids.

This is the community reputation asset. It's built one
customer at a time. It's the reason indie dealerships that
survive 20+ years survive.

---

## 5. Inventory Knowledge

Sales's relationship with Inventory is intimate. The salesperson
who doesn't know their inventory can't help their customers.

### 5.1 What "knowing the inventory" means

At minimum, current-day awareness of:

- **Front-line ready units** — vehicles ready for retail sale.
  Priced, photographed, listed.
- **In-recon units** — vehicles in reconditioning with rough ETA.
  These can sometimes be pre-sold or reserved.
- **Incoming** — vehicles just acquired (auction, trade, wholesale)
  not yet in recon.
- **Aged units** — vehicles over 60/90/120 days that need
  attention (reprice, feature, wholesale).
- **Just sold** — units that went off the lot recently.
- **Just reduced** — units whose prices moved down.

Top salespeople walk the lot every morning. They know each
vehicle's story: where it came from, what's been done to it,
what it's priced at, why the price is where it is.

### 5.2 Daily inventory rhythm

Common morning workflow:

- Sales manager or owner walks the lot with the sales team.
- New arrivals introduced ("this Camry came in yesterday, it's
  in recon for a week, retail target $12,900").
- Recon completions announced ("the Explorer is front-line ready
  today").
- Price changes announced.
- Aged units flagged for extra push.
- Special situations noted ("the F-150 with the sunroof is on
  hold for a be-back tomorrow").

Some stores publish a **daily heat sheet** — printed or emailed
summary of front-line inventory with prices, priorities, and
suggested customer matches.

### 5.3 Inventory as sales tool

Salesperson looking for a match for a specific customer:

- Search by body class, price range, features.
- Check recent additions.
- Check inventory in the "just reduced" bucket.
- Check similar vehicles (if the customer liked the Camry,
  what other mid-size sedans do we have?).
- Check alternative vehicles (if the Camry is out of budget,
  what's the next tier down?).
- Check incoming (if nothing fits today, what's arriving in
  the next 2 weeks?).

### 5.4 Pricing awareness

Salespeople should know:

- Every front-line unit's asking price.
- The pricing "story" — why is it priced there, is there room?
- Recent comparable sales at the store (to justify pricing to
  customers).
- Recent market comps (what similar units are priced at
  nearby dealers).
- Which units have room to negotiate, which are firm.

Pricing conversations with customers require this knowledge.

### 5.5 Vehicle history awareness

For each front-line unit:

- Prior use (personal, commercial, rental, lease return).
- Accident history from the vehicle history report (Carfax,
  AutoCheck).
- Number of owners.
- Service history (if available).
- Notable features (equipped options, rare trim, popular color).
- Any issues found during inspection and repaired.

Salespeople who can tell the vehicle's story sell more than
those who can only quote the specs.

### 5.6 Trade opportunities

Sales feeds trade opportunities back to inventory:

- Customer trade-in that fits store's preferred inventory mix
  (used-car manager wants more Toyotas, salesperson knows a
  customer with a Corolla trade coming).
- Customer trade-in that's a wholesale-out (won't retail well
  at this store).
- Customer trade that's too new / too rare / needs specialty
  outlet.

The trade-in decision affects inventory acquisition strategy
(see `INVENTORY_ACQUISITION_MAPPING.md`, future research).

### 5.7 Alternative inventory when the target isn't right

If the specific vehicle the customer came in for isn't the best
fit, the salesperson pivots. Requires knowing:

- What's a step up.
- What's a step down.
- What alternative body class might work.
- What incoming or recon-completing inventory to preview.

The customer who came in for a specific Camry might leave with
an Accord, a Sonata, or a slightly older Camry with lower
mileage. Or they might leave without buying because the
salesperson didn't know the lot well enough to pivot.

---

## 6. Customer Communication

Every channel used by indie sales, and what customers expect on
each.

### 6.1 Phone

Still the backbone. Customer expectations:

- Answer within 3 rings.
- Warm, professional greeting.
- Salesperson can look up the specific vehicle within 30
  seconds.
- Salesperson has current inventory knowledge (§5.1).
- Salesperson offers to set an appointment or send more info.

**Common phone frustrations for customers:**

- Long hold times.
- Transferred multiple times.
- "That vehicle is sold" (with no offer of alternatives).
- Salesperson who doesn't know the inventory.
- Aggressive pressure to come in immediately.

**Common phone frustrations for salespeople:**

- Price shoppers ("just tell me your bottom price").
- Location-checkers ("where are you located again?" — could
  have Googled).
- Callers who won't share their contact info.
- Callers who ask about vehicles that sold weeks ago.

### 6.2 Email

Slower cadence than other channels. Customer expectations:

- Response within a few hours for initial inquiry.
- Complete answer to specific questions (not just "call us").
- Professional writing.
- No aggressive drip campaigns that feel spammy.

### 6.3 SMS / text

Growing rapidly, especially with younger buyers. Customer
expectations:

- Response within minutes.
- Short, friendly, conversational tone.
- Ability to send photos and video.
- Follow-up via text without pushing to phone or in-person.

**Compliance:** TCPA (Telephone Consumer Protection Act)
requires prior express written consent for marketing texts.
Individual transactional messages (in reply to a customer's
inquiry) are more permissive. Store-initiated marketing text
campaigns require opt-in.

### 6.4 Website chat

Live chat on the website. Common patterns:

- **Real-person chat** — staff or outsourced service answers.
- **AI / chatbot chat** — automated responses, sometimes with
  handoff to a human.
- **Hybrid** — chatbot handles simple questions, escalates.

Customer expectations:

- Response within 30 seconds.
- Ability to answer specific vehicle questions.
- Handoff to a human when needed.
- Ability to schedule appointments.

### 6.5 Facebook Messenger

Critical for Facebook Marketplace leads. Customer expectations:

- Response within minutes.
- Conversational tone (not corporate).
- Ability to share photos, video, additional info.
- Willingness to negotiate via message before visit.

Facebook Messenger conversations feel more casual than
phone/email. Customers often expect same-day (or same-hour)
response.

### 6.6 Video messaging

Growing category. Salesperson records a walk-around video of the
vehicle the customer inquired about and sends it via text or
email.

Powerful because:
- Feels personal.
- Answers the "what does it really look like?" question.
- Salesperson's face and voice build trust before the visit.
- Differentiates from dealers who send stock photos and links.

### 6.7 Social media messaging (Instagram, other)

Growing but not yet dominant. Younger customers. Salesperson
needs a presence and awareness.

### 6.8 Appointment confirmations and reminders

- Customer sets appointment (phone, form, chat).
- Store sends confirmation same day (text or email).
- Store sends reminder day-before or morning-of.
- Store confirms customer is still coming with 2–4 hours notice.

Appointment show rates improve dramatically with reminders.
Without reminders, no-show rates on internet-lead appointments
can be 40–60%. With good reminder cadence, no-show rates drop
below 20%.

### 6.9 Follow-up reminders

Automated or manual reminders sent to customers about:

- Scheduled service.
- Warranty expiration.
- Loan anniversary.
- Birthday / holiday.
- "We haven't seen you in a while" reactivation.

Modern DMS/CRM systems support automated sends; smaller shops
do this manually or skip it.

### 6.10 Customer communication channel preferences

Different customers prefer different channels:

- **Older customers (60+):** prefer phone and email.
- **Middle age (35-60):** mix, with growing text preference.
- **Younger (under 35):** text and Messenger dominant.

Best practice: ask the customer their preference at first
contact and honor it.

---

## 7. Reputation and Referrals

The long game. For indie stores, reputation is the durable
asset that either builds year over year or erodes year over year.

### 7.1 Online reviews

Where customers check before contacting:

- **Google reviews** — highest visibility. Top of search
  results.
- **Facebook reviews / recommendations.**
- **DealerRater** — auto-industry-specific review site.
- **Cars.com dealer reviews.**
- **CarGurus dealer reviews.**
- **Yelp** — less impactful for auto but still visible.
- **Better Business Bureau** — some customers still check.

**Review mechanics:**

- 4.5+ stars with lots of recent reviews is competitive.
- 4.0-4.4 stars is acceptable but not aspirational.
- Below 4.0 stars loses leads before conversation.
- Recent negative reviews (last 30 days) hurt more than old
  ones.
- Owner responses to reviews (both positive and negative) show
  the store cares.

**Review generation strategies:**

- Ask every satisfied customer at delivery.
- Send a follow-up text/email 3-7 days post-sale with a review
  request link.
- Some CRMs automate this.
- Never buy reviews (violates every platform's terms and
  eventually gets caught).
- Never write fake reviews (same).

**Response to negative reviews:**

- Respond promptly (within 48 hours).
- Acknowledge the customer's experience.
- Offer to resolve offline.
- Never argue publicly.
- Never disclose customer details.

A well-handled negative review can be a positive signal to
future customers ("this store responds and cares").

### 7.2 Referral programs

Formal programs offering incentives for referrals:

- **Cash referral fee** — $100-$500 for every referral that
  becomes a sale.
- **Gift cards** — some stores prefer gift cards (easier
  bookkeeping).
- **Charitable donation** — donate to a charity in the
  referrer's name.
- **Reduced service pricing.**

**Referral fulfillment:**

- Track referrer at time of new customer visit.
- Confirm relationship with new customer.
- Pay promptly after sale (within 30 days ideal).
- Send thank-you note.

**Reality:** most indie referrals happen informally without a
formal program. The formal program adds structure but doesn't
create the underlying referral behavior — that comes from
customer satisfaction.

### 7.3 Customer satisfaction

Measurement:

- **Post-delivery CSI (customer satisfaction index) surveys** —
  franchise stores get these from OEMs; indies rarely do them
  formally.
- **Google review sentiment.**
- **Repeat purchase behavior** — best measure of satisfaction
  years later.
- **Complaints received.**
- **BBB / state consumer protection complaints.**

**Drivers of satisfaction** (from studies and operator
experience):

- Sales experience felt honest and unhurried.
- Vehicle turned out to be what was promised.
- No surprises at delivery (numbers matched what was quoted).
- F&I experience was straightforward.
- Follow-up after sale was genuine, not just sales-pushy.
- Any post-sale issues were resolved without hassle.

### 7.4 Community reputation

For an indie store in a specific geographic market, community
reputation compounds. Elements:

- Length of time in business (older = more trusted, usually).
- Location visibility (well-kept lot in a good location).
- Sponsorships (Little League, church, school).
- Owner visibility (owner known in community, active locally).
- Word-of-mouth (mechanic recommendations, insurance-agent
  recommendations).
- Public presence at local events.

Owner-operated stores at 20+ years typically have deep
community reputation that competitors can't quickly replicate.
This is a real barrier to entry for new competitors.

### 7.5 Social proof

Beyond formal reviews:

- **Facebook page** with photos of sold customers with their
  vehicles.
- **Instagram** with lot photos, new arrivals, sold-customer
  celebrations.
- **Website testimonials.**
- **Local media** — occasional feature stories in local
  newspapers or radio.

Sold-customer photos (with permission) posted to social media
serve multiple functions: celebrating the customer, showing
prospective customers real people buying real cars, generating
social engagement.

### 7.6 Repeat buyers as a strategy

Some stores explicitly target repeat buyers:

- Maintain long-term customer database.
- Segment by purchase date and vehicle age.
- Proactive outreach at 3-5 year mark ("your loan is almost
  paid off — want to trade up?").
- Special repeat-buyer offers.
- Anniversary-of-purchase touchpoints.

Repeat business is the highest-margin, lowest-CAC (customer
acquisition cost) business a store can do.

### 7.7 Service retention (where applicable)

For stores with in-house service, the service bay is a
customer-retention weapon:

- Customers who service with you stay connected.
- Service visits are natural upgrade conversations.
- Service quality signals overall store quality.
- Service problems (that get resolved well) build loyalty.

Indies without in-house service can partner with local shops or
recommend one — the customer still associates the eventual
service with the store that sold them the car.

---

## 8. Sales Metrics

The operational metrics dealerships actually watch, day-to-day
and month-to-month.

### 8.1 Volume metrics

- **Units sold** — the base count. Per day, per week, per
  month, per salesperson, per manager.
- **Retail units vs wholesale units** — retail is the
  profitable business; wholesale is inventory disposition.
- **Units delivered vs units contracted** — sometimes a deal is
  contracted but not yet delivered (waiting on funding, trade
  paperwork, etc.).
- **Repeat / referral share** of total units.

### 8.2 Gross metrics

- **Front-end (vehicle) gross** — sale price - vehicle cost.
- **Back-end (F&I) gross** — product + reserve income.
- **Total gross** — sum of front + back.
- **Average per-unit gross** (all three above, averaged).
- **Per-copy F&I gross (PVR)** — total F&I gross / units. Same
  metric from F&I doc §4.8.

### 8.3 Conversion metrics

- **Closing ratio (opportunities to deals)** — the fraction of
  qualified opportunities that become sales. Definitions vary;
  a common definition: any customer who progressed past the
  greeting into a real conversation counts as an opportunity.
  Typical range 15-25% at indie; top salespeople 30%+.
- **Appointment show rate** — appointments set / appointments
  that actually happened. Target above 70% for phone
  appointments, above 50% for internet-lead appointments (with
  good reminder cadence).
- **Appointment set rate** — leads that became appointments /
  total leads. Highly variable by source.
- **Internet lead conversion** — internet leads that became
  sales. Typical range 5-15%; excellent 20%+.
- **Phone conversion** — phone-ups that became appointments,
  and appointments that became sales.
- **Walk-in conversion** — walk-ins that became sales. Higher
  than internet lead conversion (walk-ins have higher intent).
  Typical 25-40%.
- **Trade-appraisal conversion** — customers who got a trade
  quote and later purchased. Signal of how well the store
  handles trade shopping.

### 8.4 Productivity metrics

- **Salesperson productivity** — units per salesperson per
  month. Typical range at indie 8-15 units/month; top
  performers 20+.
- **Salesperson gross production** — total gross per
  salesperson.
- **Per-salesperson lead handling** — leads assigned / leads
  responded to / leads that became appointments / sales.
- **Follow-up compliance** — how often the salesperson follows
  up with prior customers.

### 8.5 Cost metrics

- **Customer acquisition cost (CAC)** — total ad spend / units
  sold, or per-source calculations.
- **Advertising ROI** — gross generated per ad dollar spent.
- **Cost per lead (CPL)** — per source.
- **Cost per sold unit (CPU)** — per source.

### 8.6 Inventory-adjacent metrics

- **Inventory turn** — how many times per year the inventory
  turns over. Higher = faster-moving inventory = healthier
  business. Typical indie turn 8-12x per year.
- **Days to sale** — days from acquisition to sale. Aggregate
  average and per-unit.
- **Days-on-lot aging distribution** — how many units in each
  aging bucket (0-30, 31-60, 61-90, 91+).

### 8.7 Customer-relationship metrics

- **Repeat customer %** — sales to prior customers.
- **Referral customer %** — sales driven by referral.
- **Review count and rating** across platforms.
- **Follow-up cadence execution** — percentage of scheduled
  follow-ups actually completed.

### 8.8 How managers actually use metrics

- **Daily huddle:** yesterday's units, today's expected traffic,
  new inventory, aged inventory priorities.
- **Weekly review:** week-to-date units, gross, follow-up
  status, ad spend pacing.
- **Monthly close:** all the above rolled up. Bonuses, spiffs,
  and coaching decisions triggered.
- **Ad-hoc:** when something's off (units down, gross soft,
  specific salesperson struggling), the specific metric gets
  attention.

**The reality of metric use:** many indie owners run largely on
gut and daily observation. Formal metric reviews happen at
larger indies and disciplined smaller ones; many operate mostly
on intuition backed by monthly financials.

---

## 9. Pain Points

Repetitive friction sales staff experience daily. Documentation
only, no solutions proposed.

### 9.1 Following up with customers consistently

The single most-cited pain point. Salespeople know they should
follow up more; competing priorities pull them away; the
customers who didn't get followed up with don't buy.

### 9.2 Forgetting callbacks

The customer said "call me Thursday afternoon." Thursday comes,
salesperson forgets, customer buys elsewhere on Friday.

### 9.3 Poor CRM notes

The salesperson had a great conversation, didn't write it down.
The next follow-up feels like a cold call to the customer.

### 9.4 Waiting on recon

Customer wants a specific vehicle. It's in recon. ETA is
"maybe next week." Customer's timeline is now. Deal lost or
delayed. Salesperson can't control the recon schedule.

### 9.5 Waiting on finance

Customer is at the desk, deal is agreed, F&I is with another
customer. Wait time erodes the customer's excitement and
increases the chance of buyer's remorse.

### 9.6 Looking for inventory

Sales looking for a specific vehicle spec that's supposed to be
in stock. Not on the lot where expected. Search team, search
recon, search the alternate lot. Time wasted, customer waiting.

### 9.7 Scheduling appointments across channels

Customer texts asking for Saturday morning. Salesperson replies
from the phone. Salesperson also has appointments in CRM
calendar. Appointments in one channel don't show in the other.
Double-bookings, missed appointments.

### 9.8 Repeating customer information

Customer told the salesperson about the trade. Salesperson tells
the used-car manager. Manager doesn't note it. F&I asks the
customer again. Customer is annoyed by the repeated questions.

### 9.9 Trade appraisal delays

Customer wants a trade number. Used-car manager is with another
deal. Delay 30-60 minutes. Customer loses momentum.

### 9.10 Manual advertising updates

New vehicle acquired. Needs to be photographed, priced, and
listed on 4-6 platforms (website, AutoTrader, Cars.com, CarGurus,
Facebook Marketplace, possibly Craigslist). Manual entry on each
platform. Hours of work per new arrival.

### 9.11 Vehicle price changes across platforms

Owner reduces the price of a vehicle. That change has to
propagate to every listing platform. Manual updates. Some
platforms sync; some don't.

### 9.12 Listing photo management

Every listed vehicle needs 20-40 photos. Photos have to be
uploaded to each platform separately (unless syndicated). Photos
have to be reordered, tagged, sometimes edited. Time-consuming.

### 9.13 Managing multiple communication channels

Customer messages via Facebook Marketplace. Salesperson replies.
Same customer texts the store number. Different salesperson
replies. Then customer emails the store address. Third person
handles it. Nobody has the full conversation history.
Customer gets frustrated by inconsistent responses.

### 9.14 Cross-shopper questions

Customer says "the store down the street has one for $500 less."
Salesperson has to verify, respond to the price comparison,
explain differences (mileage, condition, warranty). This
conversation happens dozens of times a week.

### 9.15 Managing be-back promises

Salesperson tells customer "we'll hold this for you until
Thursday." Customer doesn't come. Vehicle should have been
available to other customers all week. Or: customer comes
Thursday, vehicle was sold to someone else Wednesday. Bad
outcome either way.

### 9.16 Working leads across shifts

Salesperson works today, has tomorrow off. Their leads have
follow-ups scheduled for tomorrow. Coverage plan for the day
off is inconsistent. Follow-ups fall through the cracks.

### 9.17 Explaining pricing to customers

The internet listing shows $17,500. The customer arrives, and
after adding tax, doc, and other fees, the out-the-door number
is $19,800. "But the website said $17,500!" A conversation the
salesperson has every single week.

### 9.18 Handling multiple customers simultaneously

Weekend afternoon, three customers on the lot, all wanting
attention. Salesperson triages. Someone gets ignored, feels
disrespected, leaves.

### 9.19 Owner interruptions

Owner walks up mid-negotiation with a "quick question" that
disrupts the customer conversation. Or owner needs the
salesperson to move a car. Or owner takes over a deal in ways
that confuse the customer.

### 9.20 Chargeback communications

Weeks after delivery, F&I / accounting informs sales that the
deal charged back (first payment default, product cancellation).
Salesperson's commission is reduced. Salesperson has no way to
have prevented or predicted this.

---

## 10. Operational Decisions

Decisions salespeople and sales managers make repeatedly. Each
is a candidate for future decision-support intelligence.

### 10.1 Which customer should be contacted first?

Every morning: 15 open leads, 8 be-backs to follow up, 3 sold
customers due for check-ins, 2 appointments today. What's the
priority order?

Factors: urgency (deal timing), engagement (recent activity),
predicted close probability, relationship value.

### 10.2 Which vehicle best fits this customer's needs?

Given what the customer told you about needs and budget, and
knowing your current inventory, which 1-3 vehicles to
present?

### 10.3 Should the manager become involved?

TO decision. Is this deal close enough that a manager's help
would close it? Or is the customer not ready and TO would feel
pushy?

### 10.4 Should this customer complete a credit application?

Time to move to F&I? Or still in the presentation stage?

### 10.5 Should this trade be appraised now?

Some trades are worth appraising before the customer commits;
some are better appraised after commitment. Judgment call.

### 10.6 Which inventory should be advertised today?

New arrivals prioritized. Aged inventory pushed with reduced
prices. Vehicles matching current lead demand featured.

### 10.7 Which lead source deserves additional advertising investment?

Aggregate performance patterns say: source X is producing
above-average CPL. Source Y is producing below-average CPL.
Reallocate?

### 10.8 Which customers are most likely to purchase?

Given engagement patterns, past visits, credit indicators, and
timing, which of my open opportunities is closest to a sale?

### 10.9 Is this customer's timeline real?

"I need to buy this week" — is that real urgency or negotiating
posture? Judgment affects how hard to push and how much
inventory to commit to their consideration.

### 10.10 Which price to quote?

Given the customer's credit tier, trade situation, and
willingness to close, what's the right first quote? Not the
posted price, not the walk-away price — somewhere in between.

### 10.11 Which follow-up channel to use?

Some customers prefer text; some prefer email; some prefer
phone. Getting the channel right increases response rate.

### 10.12 How aggressive to be with follow-up cadence?

Enough to stay top of mind; not so much that it feels like
harassment. Judgment call, varies by customer signals.

### 10.13 Do I chase this internet lead or triage it?

Every lead deserves a first response. Not every lead deserves
five follow-ups. Which are worth continued investment?

### 10.14 Should I request the referral now?

Timing on the ask. Too early (post-delivery day-of) feels
awkward. Too late (a year later) is too diffuse. Judgment
based on customer signals.

### 10.15 Should I promise something the store may not deliver?

Customer wants Saturday delivery. Detail team is booked. Do I
promise Saturday and hope it works? Do I promise Monday and
lose the deal to a store that will promise Saturday? Common
tension between closing pressure and delivery reality.

### 10.16 When to walk away from a deal

Sometimes the customer is impossible, or the deal math doesn't
work anywhere, or the customer's expectations aren't real. Time
to move on and let the next customer in.

---

## 11. Automation Opportunities

Where repetitive administrative work lives. Opportunity
identification, not solution design. Automation should support
salespeople; relationship-building and closing decisions stay
with humans.

### 11.1 Follow-up schedule organization

Every open lead + every recent visit + every sold customer
should have a next-touch date, a preferred channel, and a
suggested message frame. Reducing the "what do I do today"
mental scan.

### 11.2 Draft customer communications

Draft (never send) initial responses to internet leads, follow-up
messages, appointment confirmations, thank-you notes. Salesperson
reviews, personalizes, and sends. Reduces the blank-page
paralysis and speeds initial response.

### 11.3 Appointment reminder automation

Automated confirmation and reminder cadence for every set
appointment (day-before, morning-of). Reduces no-show rate.

### 11.4 Lead prioritization

Given all current open opportunities and their engagement
signals, produce a suggested priority order. Salesperson uses
as starting point.

### 11.5 Inventory recommendations for a specific customer

Given a customer profile (needs, budget, credit tier), suggest
1-3 in-stock vehicles that fit. Salesperson uses as starting
point.

### 11.6 CRM note completion suggestions

At end of customer conversation, prompt salesperson for key
notes to capture (family, job, vehicle preferences, life events).
Reduces the "forgot to note it" problem.

### 11.7 Marketing content draft (listing copy, ad copy)

For new arrivals, draft (never publish) listing copy that
highlights the vehicle's features against typical shopper
interests. Human reviews and posts. Reduces the copywriting
burden.

### 11.8 Listing synchronization across platforms

Push vehicle inventory (photos, description, price) from one
source to multiple listing platforms (AutoTrader, Cars.com,
CarGurus, Facebook Marketplace, dealer website). Reduces manual
duplication.

### 11.9 Price change propagation

Owner reduces the price of a vehicle. Change flows to every
listing platform automatically. Reduces manual updates.

### 11.10 Daily salesperson task plan

Each morning, produce a suggested day plan: which follow-ups
first, which appointments, which be-backs due, which sold-customer
check-ins. Salesperson reviews and adjusts.

### 11.11 Cross-channel conversation consolidation

All communications with a customer (phone, text, email,
Messenger) surfaced in a single view. Any team member picking
up the conversation has full history.

### 11.12 Missed-follow-up recovery

Follow-ups that were scheduled but not completed get surfaced
next day with a suggested catch-up message.

### 11.13 Be-back timeline management

Every customer who visited and left un-sold gets a be-back
prediction (based on stated timeline, engagement signals) and
follow-up cadence. Salesperson sees the "be-back watch list"
each morning.

### 11.14 Referral request timing

For sold customers, suggest the right timing to ask for a
referral (based on satisfaction signals, elapsed time).

### 11.15 Equity mining alerts

Past customers whose current loan payoff + vehicle depreciation
suggests they have equity get flagged for upgrade conversations.

### 11.16 Lead-source attribution assistance

Every new lead is tagged with source. Multi-touch history
attempted (if the customer's phone or email matches earlier
website visits, connect the dots).

### 11.17 Review generation prompts

Sold customers who haven't left a review get a suggested
follow-up 5-10 days post-sale.

### 11.18 Ad performance surface

Weekly or monthly view of per-source lead volume, conversion,
and cost. Owner uses to make ad allocation decisions.

Each is a candidate for its own future planning session; the
list identifies the highest-friction, highest-repetition items.

---

## 12. Cross-Department Dependencies

### 12.1 Vehicle Acquisition & Recon

**Sales depends on Acquisition & Recon for:**
- Steady flow of new arrivals matching customer demand.
- Accurate ETA on in-recon units so promises to customers can
  be reliable.
- Notification of recon completion so newly-frontline units can
  be pushed.
- Notification of adjustments (price changes on aged inventory,
  discovery of issues, etc.).
- Photos of new arrivals as soon as available.
- Vehicle history reports and known-issue disclosure.

**Acquisition & Recon depend on Sales for:**
- Feedback on customer demand patterns (which body classes,
  price points, features are asked for most).
- Trade opportunities identified during sales conversations
  ("customer coming in with a Corolla trade").
- Reality-check on pricing (units that get shopped and lost
  need pricing review).
- Signal on which units are getting no interest (may need
  reprice or wholesale disposition).

### 12.2 Finance / F&I

**Sales depends on F&I for:**
- Timely deal structuring after customer commits.
- Realistic payment quotes salesperson can use in negotiation.
- Coaching on which customers can be structured into which
  vehicles.
- Cover on payment-target promises salesperson made.
- Clean F&I handoff experience for the customer.
- Coaching on chargeback-risk deals before commitment.

**F&I depends on Sales for:**
- Accurate customer information at handoff.
- Realistic pricing that fits the deal math.
- Trade information brought forward.
- Coaching customer on documentation to bring.
- Not overpromising to customer on rates or terms.

### 12.3 Accounting

**Sales depends on Accounting for:**
- Confirmed booked-and-funded status for commission
  calculation.
- Timely payment of commissions.
- Chargeback communications (with enough detail to understand
  the reason).
- Petty cash / spiff payments when applicable.
- Deposit handling for cash down payments.

**Accounting depends on Sales for:**
- Complete deal information at handoff.
- Documentation from delivery (delivery checklist, signed
  documents, insurance verification).
- Notification of any unusual arrangements (deferred down,
  refund promises, delivery holds).

### 12.4 Customers

**Sales depends on Customers for:**
- Truthful information about needs, budget, trade, credit.
- Timely response to follow-up.
- Showing up for appointments.
- Reasonable expectations.
- Referring friends and family.
- Leaving reviews.

**Customers depend on Sales for:**
- Honest, unhurried consultation.
- Accurate vehicle information.
- Consistent pricing (no bait-and-switch).
- Reasonable follow-up cadence (not harassment).
- Post-sale support for questions.
- Honoring promises made.

### 12.5 Marketing / advertising platforms

**Sales depends on Marketing for:**
- Consistent lead flow.
- Accurate listings on platforms (matching current inventory
  and pricing).
- Reputation management (reviews, social presence).
- Coordination on promotions and specials.
- Response to platform performance changes.

**Marketing depends on Sales for:**
- Lead feedback (source, quality, close rate).
- Customer testimonial content.
- Delivery photos and sold-customer stories.
- Real-time inventory changes to propagate.
- Salesperson participation in content creation
  (walk-around videos, testimonials).

### 12.6 Vendors

Sales interacts with some vendors directly:

- **Third-party listing services** (AutoTrader, Cars.com,
  CarGurus, Facebook Marketplace) — salesperson may manage
  listings, respond to leads.
- **CRM vendors** — daily use, training issues, feature
  requests.
- **Chat services** (if outsourced) — quality of chat handoff.
- **Trade appraisal services** — third-party appraisal
  requests.
- **Insurance verifiers** — for delivery insurance verification
  workflows.

### 12.7 Ownership

**Sales depends on Ownership for:**
- Pricing authority (final decisions on discounts).
- Trade approval on unusual trades.
- Deal approval on unusual structures.
- Handling of escalated customer complaints.
- VIP / long-time customer relationships.
- Community relationship maintenance.
- Advertising budget decisions.
- Hiring, training, and team composition.

**Ownership depends on Sales for:**
- Consistent daily execution.
- Team productivity toward monthly / quarterly goals.
- Customer relationship quality (that reflects on the store's
  reputation).
- Feedback on inventory decisions (what's selling, what's not).
- Cash flow (funded deals per week).
- Escalation of issues before they become bigger problems.
- Community relationship maintenance at the customer level.

---

## 13. Deferred Ideas

Ideas that surfaced during Sales research but belong to other
departments' future research. Recorded briefly here; not
expanded.

**Vehicle Acquisition & Recon** — Demand-driven acquisition
buying signals from sales conversations; recon ETA accuracy
tracking; new-arrival announcement workflow to sales team.

**Finance / F&I** — Payment quote consistency between sales
floor and F&I office; sales-facing "will this deal work"
pre-qualification signals; chargeback root-cause feedback to
sales.

**Accounting** — Commission calculation with real-time gross
transparency; chargeback communication with sales; spiff /
bonus tracking.

**Titles / DMV Operations** — Delivery paperwork completeness
check; temp tag issuance workflow; customer registration
status reporting to sales.

**Compliance** — TCPA compliance for text campaigns;
fair-lending consistency in product/pricing offerings;
adverse-action notification flow from sales to F&I.

**Marketing** — Multi-platform listing management as its own
department capability; SEO / paid search / social ad
optimization; review generation and response management;
brand-consistency across channels; reputation management as a
formal discipline.

**Customer Data / CRM Architecture** — Customer identity across
visits, channels, and time; deduplication of prospect records;
household-level relationship tracking (families, co-buyers);
long-term customer database as a strategic asset.

**Service Department (if in-house)** — Sales-service handoff
for delivery; service reminder cadence; upgrade opportunity
identification from service visits.

**BHPH Operations (if applicable)** — BHPH-specific customer
acquisition (community outreach, direct mail, radio); payment
shopper conversation flow; deferred-down deal handling from
sales floor.

**Business Development Center (BDC)** — If the store scales
enough to add a BDC, workflow design for dedicated
lead-response team; hand-off from BDC to floor salesperson.

**Fleet / Commercial Sales** — Selling to small business
accounts, government/municipal accounts; multi-vehicle deals;
different sales cadence and pricing conventions.

**Wholesale Sales** — Dealer-to-dealer sales; auction-out
disposition; wholesale relationship management.

**Sales Training & Development** — Onboarding new
salespeople; ongoing product training; coaching cadence;
performance improvement plans for underperforming staff.

**Compensation & Incentive Structure** — Commission plans,
spiff programs, referral fees, bonuses. Ties to Accounting
and Payroll.

**Customer Communication Infrastructure** — Multi-channel
inbox architecture; consent management; opt-out compliance;
message-history unification.

Each of the above deserves its own research session before
implementation. This document catches them so they aren't
forgotten; future department-specific research will develop
them.

---

## How to use this document

**For engineers and product people** starting sales / CRM /
lead-management / advertising work: read sections 1–3 first (the
indie landscape, customer acquisition sources, and sales
workflow). Those sections carry the mental model everything else
builds on. Read section 12 (cross-department dependencies)
before designing anything that connects to other departments.
Section 11 (automation opportunities) is where product ideas
start — but each opportunity should be developed into its own
scoped plan before implementation.

**For AI agents** starting a Sales-related session: this
document is source-of-truth for how independent dealerships
sell cars. If anything you're asked to do contradicts what's
described here, push back. Particular anti-patterns to flag:
- Any suggestion that AI should communicate directly with
  customers without human review. All AI-drafted customer
  communications remain drafts pending salesperson approval.
- Any suggestion that lead prioritization or vehicle
  recommendation should be a hidden algorithm the salesperson
  can't inspect. Sales trust is built on humans making
  relationship decisions.
- Any suggestion that CRM notes should be auto-generated
  without the salesperson's input. Great notes are a human
  observation, not a transcription.
- Any suggestion that "automate follow-up" means sending
  autoresponders. Follow-up quality is exactly the thing that
  differentiates a store; automating it into spam destroys the
  differentiator.

**For domain experts** reading this document: this is a snapshot
of common indie practice. Every market and store has
idiosyncrasies. Corrections and additions are welcome and
expected as the platform evolves.

**Update discipline.** Update this document when:
- New lead-source categories emerge (as Facebook Marketplace did
  in the late 2010s).
- Regulatory changes materially alter communication practices
  (TCPA updates, state-specific advertising rules).
- Common customer expectations shift (response-time norms,
  channel preferences).
- Common industry-benchmark metrics shift meaningfully.

Do **not** update this document with:
- Specific software product feature reviews.
- Advertising platform bid strategies or algorithmic tactics.
- Personal opinions about specific vendors.
- Implementation designs.

---

## Glossary — sales terms used in this document

- **Appointment show rate** — Percentage of set appointments that
  the customer actually attends.
- **Be-back** — A customer who visited or inquired, didn't
  purchase, and later returns.
- **BDC** — Business Development Center. Team dedicated to
  responding to internet leads and setting appointments.
- **CAC** — Customer Acquisition Cost. Total spend to acquire a
  customer.
- **Closing ratio** — Fraction of qualified sales opportunities
  that become sales.
- **Cost per lead (CPL)** — Total spend on a source / leads
  produced by that source.
- **Cost per sold unit (CPU)** — Total spend on a source / sales
  attributed to that source.
- **CRM** — Customer Relationship Management. Software system
  for tracking customer interactions.
- **CSI** — Customer Satisfaction Index. Formal customer
  satisfaction measurement, common at franchise.
- **Cross-shopper** — Customer shopping the same or similar
  vehicles at multiple dealers.
- **Demo drive** — Vehicle demonstration drive (test drive).
- **Drive-by traffic** — Customers who saw the lot from the road
  and stopped in.
- **Equity mining** — Identifying past customers with vehicle
  equity for upgrade opportunities.
- **F&I** — Finance and Insurance. See
  `FINANCE_DEPARTMENT_MAPPING.md`.
- **First-touch attribution** — Crediting the first channel a
  customer engaged with.
- **Four-square** — Traditional deal-write-up format with four
  quadrants: price, trade, down payment, monthly payment.
- **Front-end gross** — Vehicle gross profit (sale price minus
  vehicle cost).
- **Heat sheet** — Daily printed / emailed summary of front-line
  inventory, prices, and priorities.
- **Internet lead** — Customer inquiry originating from an
  online source.
- **Last-touch attribution** — Crediting the channel where the
  customer converted (most common; can be misleading).
- **Lead** — A prospective customer contact.
- **Multi-touch attribution** — Splitting credit across all
  channels involved in a customer journey.
- **Opportunity** — A qualified prospective sale in progress.
- **Payment-first customer** — Customer focused on monthly
  payment rather than total price.
- **Phone-up** — Inbound phone inquiry about a specific vehicle
  or in general.
- **PVR / per-copy** — Per-Vehicle Retail. F&I gross per unit
  sold.
- **Referral customer** — New customer sent by a past customer.
- **Repeat customer** — Past buyer returning for another
  vehicle.
- **Road to sale** — The standardized customer journey through
  the sales process (greeting, interview, presentation, demo,
  trade, write-up, F&I, delivery, follow-up).
- **SEO** — Search Engine Optimization. Practices to improve
  organic search ranking.
- **Show rate** — See appointment show rate.
- **Sold customer** — A customer who purchased.
- **Spiff** — Special incentive or bonus paid on specific
  vehicles or deals.
- **TCPA** — Telephone Consumer Protection Act. Federal law
  regulating automated calls and texts.
- **TO** — Turn-Over. Introducing the customer to a manager or
  more senior salesperson mid-deal.
- **Trade appraisal** — Evaluation of a customer's trade-in
  vehicle to determine its value.
- **Un-sold customer** — A customer who visited or inquired but
  did not purchase (yet).
- **Walk-in** — A customer who arrived at the lot without prior
  contact.
- **Walk-the-lot** — Practice of physically walking the lot to
  observe inventory (either by salesperson or by owner with team).

---

## Related research

- `FINANCE_DEPARTMENT_MAPPING.md` — F&I department; downstream
  of Sales for every customer who buys.
- `ACCOUNTING_DEPARTMENT_MAPPING.md` — Accounting department;
  ultimately books every sale and pays every commission.
- `VEHICLE_CENTRIC_PIVOT.md` — Overall pivot plan. Sales
  research feeds Phase 4 (lifecycle stages — the frontline gate),
  Phase 5 (listing generation — where sales-and-marketing
  collaborates), Phase 7 (operational intelligence — sales
  metrics), and Phase 8 (Sale + Delivery models — the deal
  bookend to the vehicle record).
- `INDEPENDENT_DEALER_PIVOT.md` — Established the indie-first
  scope this document uses.
- `CAPABILITY_MATRIX.md` — Current shipped capabilities;
  significantly, the AI chat capability is currently sales-
  adjacent (customer-facing conversation) but the customer
  acquisition, CRM, follow-up, and long-term relationship
  management described in this document are almost entirely
  greenfield.

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

*End of Customer Acquisition & Sales Department mapping.*
