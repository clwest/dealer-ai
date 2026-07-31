---
title: "Reconditioning Department — Operational Mapping"
status: reference
type: research
generated: 2026-07-31
scope: Independent used-car dealership reconditioning operations — inspection, work planning, vendor management, and front-line preparation
voice: Experienced recon manager / shop foreman / service manager / owner-mechanic
companion_docs:
  - "INVENTORY_ACQUISITION_MAPPING.md"
  - "FINANCE_DEPARTMENT_MAPPING.md"
  - "ACCOUNTING_DEPARTMENT_MAPPING.md"
  - "SALES_DEPARTMENT_MAPPING.md"
  - "VEHICLE_CENTRIC_PIVOT.md"
  - "INDEPENDENT_DEALER_PIVOT.md"
authoritative_for:
  - How indie used-car dealerships actually get vehicles from acquired-condition to front-line-ready
  - The condition-inspection discipline, work-planning judgment, and vendor management that determine recon cost and turn time
not_authoritative_for:
  - Franchise service department operations (in-house full service bays with OEM warranty work)
  - ASE technician certification or shop-management training
  - Specific vendor selection or vendor performance in any particular market
  - Any implementation design
---

# Reconditioning Department — Operational Mapping

> **What this is.** A research artifact documenting how the
> reconditioning ("recon") function of an independent used-car
> dealership actually operates. Written from the perspective of
> an experienced recon manager, shop foreman, service manager,
> or owner-mechanic — the person who decides what work gets done
> to which vehicle, by whom, at what cost, and when it's
> "front-line ready."
>
> **Who this is for.** Anyone (engineer, agent, product person)
> touching recon, condition-reporting, work-order, vendor-
> management, or front-line-readiness work in the Dealer AI Kit.
> Read this before opening a code editor or a wireframe tool.
>
> **What this is NOT.** Not a technician training manual. Not
> a shop-management operations manual. Not a comparison of
> specific service software. Not an implementation plan.
>
> **Core philosophy.** **"You can't sell what you don't have,
> and you can't have what isn't ready."** Every unit in recon
> is capital sitting idle. Every day in recon is a day of floor
> plan interest, depreciation, and lost retail opportunity.
> But: shipping a unit out of recon before it's actually ready
> is worse than any delay — you're guaranteeing a warranty
> claim, a chargeback risk, a customer complaint, and a hit to
> the store's reputation. The recon manager's job is to move
> vehicles through recon as quickly as possible **while still
> shipping vehicles that will not embarrass the store 30 days
> later.** That tension between speed and quality is the daily
> work. Additionally: **the condition report is where recon
> quality begins.** If the inspection missed a defect, recon
> can't plan for it. If the technician didn't write it down,
> the vendor didn't get told about it, and the customer will
> find it. Human-authored inspection discipline is
> non-negotiable.

---

## Purpose & scope

The Dealer AI Kit's vehicle-centric pivot (see
`VEHICLE_CENTRIC_PIVOT.md`) proposes making every stock number
a living operational record with lifecycle, ledger, and
condition report. This document is the operational-truth
companion to that pivot, covering the reconditioning side of
the vehicle's lifecycle — from post-acquisition inspection
through front-line-ready sign-off.

The acquisition side (buying decisions, pricing, aging,
disposition) is documented in
`INVENTORY_ACQUISITION_MAPPING.md`. Together the two documents
cover the full vehicle-side operation. A store's used-car
manager often runs both, but recon has enough distinct
operational discipline to warrant separate treatment.

**Scope boundary:** *independent used-car dealer* scope.

- Small to mid-sized store (25–150 vehicles in inventory).
- Recon operations range from **fully outsourced** (all work
  goes to outside vendors) to **partially in-house** (small
  shop for basics, outsourcing for specialty work) to
  **substantially in-house** (a service bay with technicians
  handling most work).
- Vehicles typically 3–15 model years old with corresponding
  recon needs.
- Recon budgets typically $500–$2,500 per unit average;
  wider ranges by tier.
- 1–5 people directly involved in recon decisions.
- BHPH-heavy stores skew older vehicles with tighter recon
  budgets aimed at "will this last the loan term?"

Where franchise service-department practice differs materially,
this document notes the contrast briefly. It does not attempt
to fully document franchise service operations (dispatch,
warranty administration, ASE-certified technician management,
factory training).

---

## Voice & caveats

The voice throughout is that of an experienced recon manager or
shop foreman — someone who has personally torn down engines,
priced parts, negotiated with vendors, and signed off on
front-line units. Terminology is used as it's spoken ("R.O."
for repair order, "book time," "flat rate," "at the body man,"
"pulled it off the front line," "safety fail," "book
time vs real time," "warranty came back").

**Numeric caveats.** Specific dollar figures, hour estimates,
and time windows are illustrative of common practice. Real
recon costs vary enormously by market (labor rates in the
Northeast are double those in some rural Southern markets),
vehicle class, condition tier, and vendor pricing. Treat this
document as a description of *what work exists and how
decisions get made*, not as a source of pricing truth.

**Compliance caveats.** Recon operations intersect compliance
(safety-recall handling, brake / tire / airbag safety, state
inspection requirements, emissions in emissions states,
disclosure of significant repairs to buyers). Some points are
noted; a full compliance program is separate.

---

## 1. The indie recon landscape

### 1.1 The three recon models

Indie stores fall along a spectrum:

**Model A — Fully outsourced.** No in-house shop. Every unit
goes to outside vendors for every step: mechanical, body,
glass, tires, alignment, detail, photography. The used-car
manager or owner coordinates the vendor sequence for each
unit.

- **Advantages:** low overhead, no shop rent / insurance /
  liability, flexible capacity (surge to more vendors when
  needed).
- **Disadvantages:** less control over timing, higher per-job
  cost, quality varies vendor to vendor, communication
  overhead.
- **Common at:** smaller indies (25 or fewer units in
  stock), stores in dense urban markets where good vendors
  are close, stores whose owner isn't from a mechanical
  background.

**Model B — Partial in-house (hybrid).** Small shop for basics
(oil, tires mounted, brakes, minor mechanical, detail),
outsourcing for specialty (body, paint, glass, upholstery,
larger mechanical). One or two techs on staff.

- **Advantages:** fast turn on routine work, cost control on
  basics, in-house eyes on inspection quality.
- **Disadvantages:** shop overhead (bay, tools, tech wages,
  insurance), still coordinating outside vendors for the hard
  stuff.
- **Common at:** mid-sized indies (40–100 units), stores where
  the owner has a mechanical background, stores in markets
  with good tech labor availability.

**Model C — Substantially in-house.** Full service bay,
multiple techs, capacity to do most mechanical / brake / tire
/ light body work. Only specialty (paint, glass, complex body,
alignment on some equipment) goes out.

- **Advantages:** maximum control over timing and quality,
  best cost control, opportunity to internally bill techs at
  a labor rate that adds to accounting profit.
- **Disadvantages:** significant overhead (multiple techs,
  large facility, equipment, insurance, workers' comp).
  Requires enough volume to keep techs busy.
- **Common at:** larger indies (100+ units), stores that also
  operate a public service department (mixing recon with paid
  customer service work), stores with a family / partnership
  where a family member is the head tech.

Franchise contrast: nearly all franchise stores have a full
service department because OEM warranty work requires it.
Franchise recon typically runs through the same service bays as
customer service work, on internal ROs.

### 1.2 The people

Depending on the model:

- **Recon manager / shop foreman** — dispatches work, sets
  priorities, coordinates with vendors, signs off on
  completed units. Often the used-car manager or owner
  wearing that hat at smaller stores.
- **Service writer** — writes up repair orders, communicates
  with technicians, tracks in-progress work. Rare at pure
  indie recon; common at hybrid or in-house shops.
- **Technicians** — mechanical work. Range from generalist
  ("A tech" — can do most mechanical work) to specialist
  ("brake tech," "trans specialist") to apprentice ("B tech,"
  "C tech" — routine work under supervision).
- **Detail crew** — interior and exterior detail. Often lower
  wage, sometimes contract labor.
- **Photographer** — often a detail crew member or a
  salesperson. Rarely a dedicated role at indies.
- **Vendor liaison** — whoever calls vendors, drops off /
  picks up vehicles, chases quotes, chases stips. Often
  informal; sometimes assigned to a specific person (owner's
  spouse, office manager, dedicated coordinator).

### 1.3 The physical environment

Depending on model:

- **Vendor-only stores** — just a "recon area" of the back
  lot where vehicles wait for vendor pickup or return.
- **Hybrid stores** — a small shop (1–3 bays) with basic
  equipment (lifts, tools, tire machine, brake lathe).
- **In-house stores** — full service bay area (3–8 bays),
  parts room, alignment machine (sometimes), paint booth
  (rarely), body work area.

**The recon lot** is where vehicles live between recon steps:
- Just acquired, awaiting inspection.
- Inspected, awaiting work approval.
- Waiting for parts.
- Between vendor visits (came back from mechanical, awaiting
  body man).
- Recon complete, awaiting detail.
- Detail complete, awaiting photos.
- Photos taken, awaiting listing.

An organized recon lot has clear "zones" so at a glance
someone can see what's in what state. A disorganized recon lot
loses vehicles ("wait, where's that Explorer?").

### 1.4 The seasonal / calendar rhythm of recon

Recon has its own rhythms:

- **Post-auction days** — Tuesday/Wednesday auction buys
  arrive Thursday/Friday. Recon capacity is maxed out
  Friday–following-Wednesday.
- **Tax season (Feb–April)** — inventory acquisition surges;
  recon backlog builds; sales pressure on recon to turn units
  fast.
- **Summer heat** — some recon work is harder (paint,
  interior detail, technician comfort in un-air-conditioned
  bays).
- **Winter** — cold-weather work (batteries, tires, snow tire
  installation), body work slows for outdoor operations.
- **End of month** — sales pressure translates to recon
  pressure: "we need three more units front-line by
  Saturday."

Skilled recon managers plan capacity around these rhythms.

### 1.5 The economics of recon

Recon is where a store's per-unit gross gets defended or lost.

Typical recon spend per unit:
- **Minimal recon** — clean trade-in that just needs detail
  and inspection: $150–$400.
- **Standard recon** — most auction buys: $600–$1,500.
- **Heavy recon** — tires, brakes, mechanical work, minor
  body: $1,500–$3,500.
- **Major recon** — significant mechanical, body work, paint:
  $3,500–$8,000+.
- **Beyond retail cost** — recon costs approach or exceed
  wholesale-value spread. Wholesale-out decision.

A store buying 30 units/month at average $1,200 recon is
spending $36,000/month on recon. That's a significant
operating expense — and every dollar under-estimated by the
buyer at acquisition compresses per-unit gross.

**Cost control matters daily.** A vendor who charged $600 for
what should have been a $400 job just took $200 out of that
unit's gross. Repeated across the year, that's real money.

---

## 2. Condition Assessment (Inspection)

The condition report is the foundational document of recon.
Everything else follows from what the inspection found.

### 2.1 The multi-point inspection

Every acquired vehicle should receive a documented inspection
before recon planning begins.

Standard inspection categories:

- **Mechanical** — engine performance, transmission function,
  fluid conditions, belts and hoses, exhaust, cooling system,
  charging system, starting system, drive-line.
- **Cosmetic / paint** — panels, paint condition, chips,
  scratches, faded clear coat, evidence of prior repaint.
- **Body / structural** — panel fit, evidence of prior
  collision (welds, seals, mismatched paint), frame
  integrity.
- **Glass** — windshield chips or cracks, side glass, rear
  glass, sunroof glass, mirrors.
- **Tires** — tread depth, sidewall condition, brand
  matching, age (DOT date codes), spare condition.
- **Interior** — upholstery condition, dashboard cracks,
  odors (smoke, pet, mildew), carpet condition, controls
  functionality, features working (radio, HVAC, power
  windows, seats).
- **Fluids** — oil condition, coolant color and level, brake
  fluid, power steering fluid, transmission fluid,
  differential (as applicable).
- **Electrical** — battery condition and CCA, alternator
  output, all lighting functional, warning lights, all
  accessories working (mirrors, seats, sunroof, keyless entry,
  navigation, backup camera).
- **Safety** — brakes (pad thickness, rotor condition), brake
  fluid, tires (as tire and safety overlap), airbag warning
  lights, seatbelts functional, headlight aim, wipers.
- **Accessories / features present** — floor mats, spare tire
  and tools, jack, wheel locks and key, spare key/fob, cargo
  cover, third-row headrests, owner's manual, service
  records if any.
- **Missing items** — anything expected that isn't there
  (missing second key, missing owner's manual, missing headrest,
  missing floor mats, missing radio anti-theft code).

Some stores add:
- **Emissions system** (in emissions-testing states) — check
  engine light history, evap system, catalytic converter
  presence.
- **Safety recalls** — check for open recalls using VIN
  (NHTSA lookup or manufacturer portal).
- **Vehicle history report review** — Carfax / AutoCheck
  cross-referenced to what was disclosed at auction.

### 2.2 Severity levels

Not every finding is equal. Common severity conventions:

- **Advisory** — noted, no action required. ("Slight wear on
  driver seat bolster, cosmetic only.")
- **Recommended** — should be addressed, not blocking front-line
  status. ("Front brakes at 40% — recommend replacement within
  next service.")
- **Required** — must be addressed before front-line.
  ("Rear brake pads worn to metal.")
- **Safety** — must be addressed before front-line, highest
  priority. ("Cracked windshield in driver line of sight.")

Different stores use different labels ("critical / high /
medium / low," "must / should / could," etc.) but the shape is
consistent. The categorization drives what recon actually gets
done.

### 2.3 Who does the inspection?

- **In-house tech** — at hybrid or in-house shops, a tech
  performs the inspection as first-touch when the vehicle
  arrives.
- **Outside vendor mechanical shop** — a mechanical vendor
  does an "inspection service" (typically $75–$200) that
  returns a written estimate on all findings.
- **State safety inspection station** — in states with
  mandatory safety inspection, this doubles as a partial
  recon inspection.
- **Used-car manager / owner personal inspection** — at
  smaller stores, the buyer inspects on arrival and dispatches
  work based on their assessment.
- **Combination** — arrival inspection by buyer (for obvious
  issues), then vendor inspection for detailed mechanical.

**Human-authored inspection discipline is non-negotiable.**
The AI or software may organize the findings, but a
qualified human must actually inspect the vehicle. Skipping
inspection or letting AI infer condition creates warranty
exposure downstream.

### 2.4 The condition report document

Whatever the process, the output is a document (paper, digital,
photos) that captures:

- Inspector name and date.
- Vehicle identification (stock number, VIN, mileage at
  inspection).
- Category-by-category findings.
- Severity of each finding.
- Cost estimate if known (some inspections include estimates,
  some just findings).
- Recommendations for work sequence.
- Photos of significant findings (paint issues, damage,
  odometer, VIN plate).

This report lives in the vehicle jacket. It's the source
document for every recon action taken.

### 2.5 Photos in condition reporting

Photos matter because:

- Document pre-existing damage (protection against later
  disputes about who caused what).
- Communicate to vendors (a photo of a specific scratch
  faster than describing it).
- Support insurance claims if applicable.
- Serve as before/after evidence of recon work.

Common photo practice at inspection:
- Overall exterior (4-6 shots covering all angles).
- Any damage close-ups.
- Odometer close-up.
- VIN plate close-up.
- Interior overview.
- Any interior damage close-ups.
- Under-hood overview.
- Tire tread close-ups (each tire) with brand and DOT visible.

### 2.6 What the AI is never allowed to do at inspection

- **Invent a finding.** Every finding on the condition report
  must trace back to a human observation. AI-generated
  "predicted" findings are not findings.
- **Change severity.** If the tech marked something recommended
  and AI thinks it should be safety-priority, AI can flag the
  disagreement for human review, not silently upgrade.
- **Modify the tech's description.** The tech's words stand.
  AI can suggest structured tagging (mechanical vs cosmetic
  vs safety) but doesn't rewrite descriptions.

### 2.7 What the AI IS allowed to do with condition data

- **Summarize** the findings into a proposed work plan.
- **Cross-reference** with historical costs (similar findings
  on prior vehicles typically cost X).
- **Suggest vendors** based on category and past performance.
- **Group similar findings** across the fleet ("3 units need
  tires this week; combined order for volume discount?").
- **Draft** (never send) vendor communications, parts orders,
  work-order narratives.

These distinctions matter because condition data is the
foundation of everything else. If it's polluted with
AI-invented content, every downstream decision is unreliable.

---

## 3. Recon Planning

Once the condition report exists, the recon manager decides
what work actually gets done. This is judgment work.

### 3.1 The three-tier decision framework

Every finding falls into one of three planning categories:

- **Must do** — safety and required items. Non-negotiable.
- **Should do** — recommended items that improve retail
  potential or reduce warranty risk.
- **Won't do** — advisory items the store won't invest in.

The "won't do" decisions are often the most consequential.
Skimping on a $200 belt that then fails at day 45 costs the
store the customer relationship and potentially the belt cost
plus a tow plus a rental plus goodwill repair.

### 3.2 The "walk-away" cost

Sometimes the total recon estimate exceeds what the deal can
support. Decision path:

- **Reduce scope** — do only the must-dos, skip everything
  else. May work; may create warranty exposure.
- **Wholesale-out** — the unit goes to a peer or auction
  rather than being reconditioned for retail. See
  `INVENTORY_ACQUISITION_MAPPING.md` §9.
- **Reprice at retail** — retail at a lower price that fits
  the recon math. May work if the reduced price still
  attracts buyers.
- **Salvage / parts vehicle** — for units where the recon
  cost approaches or exceeds retail value entirely. Rare but
  happens.

The walk-away decision is a joint call between the recon
manager and used-car manager (or owner). It's usually made
after the initial inspection reveals a bigger problem than
the buyer estimated at acquisition.

### 3.3 The recon estimate vs cap

Every unit implicitly has a recon budget cap based on:

- Acquisition cost + expected recon + expected floor plan
  interest = total investment.
- Target retail.
- Required gross.

The recon cap is what's left after the target gross. When
recon estimates approach or exceed the cap, the plan has to
change (reduce scope, wholesale, or accept lower gross).

**Cost creep is real.** A $1,200 recon estimate that turns
into $1,600 actual (through discovered work, parts variance,
vendor overrun) directly compresses gross. Discipline on
estimates matters.

### 3.4 Prioritization within the plan

Once must-do work is scoped, the sequence matters:

- **Mechanical first** — has to run and drive correctly
  before other work makes sense.
- **Body / paint second** — before detail (paint dust and
  fumes ruin fresh detail).
- **Glass any time** — often standalone vendor with own
  timing.
- **Alignment after body / suspension work** — reassemble
  first, align last.
- **Tires before alignment** — new tires may change alignment
  needs.
- **Detail second-to-last** — after all messy work is done.
- **Photography last** — after detail, with the vehicle at
  its best.
- **Listing after photography.**

Skilled recon managers sequence to minimize back-and-forth
between vendors and to avoid re-doing work (a fresh detail
after body work is wasted labor).

### 3.5 Parts pre-ordering

Some recon plans require ordering parts before scheduling
labor:

- OEM-only parts (specific to make/model, only from
  dealership parts counter).
- Back-order-prone items.
- Parts that need to be in-hand before a tech takes the
  vehicle apart.

Skilled recon managers pre-order parts when the plan is set,
so the tech isn't waiting on parts when scheduled work day
arrives.

### 3.6 Vendor selection per job

For each job in the plan, the recon manager selects a vendor:

- Historical performance (turn time, cost, quality).
- Current availability.
- Vendor's specialty match to the job.
- Vendor pricing for this category.
- Relationship considerations (vendor rep, ongoing account
  standing).

At smaller indies, vendor selection is often mental — "for
paint work, we use [Body Shop A]; for glass, we use [Glass
Vendor B]; for mechanical, we use [Independent Mechanic C]
first, [Mechanic D] if C is backed up."

### 3.7 Scheduling and capacity

Recon planning also considers timing:

- Vendor availability (some vendors are always backed up).
- Store's need (which units need to be front-line first).
- Combined work efficiency (drop three units at the body man
  at once to save trips).
- Weather considerations (paint doesn't dry well below 50°F).

The recon calendar is often kept in someone's head at smaller
stores; larger stores use a whiteboard or a shop management
system.

---

## 4. In-house Shop Operations

For stores with in-house recon (Models B and C from §1.1).
This section skips at fully outsourced stores.

### 4.1 Technician staffing

Common staffing patterns:

- **Solo tech** — one all-purpose technician handling
  everything the shop does. Common at smaller Model B stores.
- **Lead tech + apprentice** — experienced tech dispatches
  and does complex work; apprentice does routine work
  (oil, tires, brakes) under supervision.
- **Specialty staff** — larger in-house shops may have a
  brake specialist, a diagnostic specialist, an
  electrical specialist.

Technician skill matters enormously. A great tech spots
issues the inspection missed and fixes things right the first
time. A weak tech misses things, does incomplete work, and
creates warranty exposure.

### 4.2 Repair Order (R.O.) flow

The R.O. is the work order — the document that authorizes and
tracks a specific job on a specific vehicle.

Typical flow:
- Service writer (or recon manager) creates R.O. based on
  condition report + planned work.
- R.O. assigned to a tech.
- Tech completes work; notes hours actually spent, parts
  actually used, any additional findings.
- R.O. closed (with time and cost recorded).
- Recon manager reviews closed R.O., approves for the
  vehicle jacket.

Multiple R.O.s per vehicle over the recon cycle (inspection
R.O., mechanical R.O., brake R.O., separate R.O. per major
job).

### 4.3 Parts stocking

In-house shops typically stock:

- Common wear items (oil filters, air filters, wiper blades).
- Common brake pads for popular vehicles in the store's
  inventory profile.
- Batteries (common sizes).
- Miscellaneous (fluids, small hardware, shop supplies).

Parts inventory is separate from vehicle inventory. Parts
have their own accounting (parts inventory GL account, parts
usage expensed to vehicle when consumed).

### 4.4 Labor rate and time tracking

**Labor rate** — the dollar rate at which tech time is billed
against the vehicle. Common indie shop rates $60–$120/hour
for internal / recon work (vs $100–$200/hour for public
service work at franchise).

**Book time vs real time** — book time is the manufacturer's
or industry-standard estimate for a job. Real time is what
the tech actually spent. Efficient techs beat book time
regularly; slower techs run over book time.

**Time tracking:**
- Some shops bill tech hours to the vehicle at real time.
- Some bill at book time (tech efficiency wins go to shop
  profitability rather than the vehicle).
- Combinations exist.

### 4.5 In-house recon cost accounting

If the shop bills labor to the vehicle:
- Vehicle inventory account debited for labor.
- Service department credited (creates "internal revenue" for
  the service dept).
- Parts inventory debited (or expensed directly to vehicle).

If the shop expenses labor as store operating expense:
- Labor is a fixed cost, not per-unit.
- Vehicle inventory carries only parts + outside vendor
  costs.

The accounting choice matters for per-unit gross analysis and
service-department profitability reporting.

### 4.6 In-house vs outsourced cost comparison

For each work category, the recon manager mentally compares:

- What would in-house cost (labor + parts + overhead
  allocation)?
- What would outside vendor cost (invoiced amount)?

In-house is usually cheaper per job when the shop has
capacity. In-house is more expensive per job when the shop is
idle (fixed costs already sunk) — but sending work outside
just wastes the sunk capacity.

Some jobs are always outsourced regardless (paint, complex
body, specialty alignment, custom upholstery) because
in-house doesn't have the equipment or expertise.

---

## 5. Outsourced Vendor Management

For all stores (even in-house shops outsource specialty work).

### 5.1 Vendor categories

Common recon vendor categories:

- **General mechanical repair** — engine, transmission,
  cooling, electrical work beyond in-house capability.
- **Diagnostic** — specialty diagnostic shops for hard-to-find
  issues (electrical gremlins, intermittent problems).
- **Body work / collision repair** — panel replacement, dent
  repair, structural work.
- **Paint** — full or partial repaints, spot repair, color
  match.
- **Paintless dent repair (PDR)** — specialty vendor for dings
  without paint work.
- **Glass** — windshield, side glass, rear glass replacement.
- **Tire installation** — tire replacement, mounting, balance,
  disposal.
- **Alignment** — 4-wheel or 2-wheel alignment on a rack.
- **Interior repair / upholstery** — leather repair, cloth
  repair, headliner replacement.
- **Detail / recon detail** — full interior/exterior detail,
  paint correction, sometimes headlight restoration.
- **Odor removal** — ozone treatment for smoke or pet odors.
- **Reconditioning specialist** — some vendors do
  comprehensive recon (multiple job types) under one roof.
- **Photography** — professional photographer for listing
  photos.
- **Key programming** — dealer-only key/fob programming for
  vehicles that need it.
- **Transmission specialist** — for complex trans work
  in-house shops don't handle.

### 5.2 Vendor selection criteria

Factors weighed:

- **Historical turn time** — how many days from drop-off to
  completion?
- **Historical cost** — per job or per hour?
- **Quality** — how often does work come back for rework or
  fail warranty?
- **Communication** — does the vendor return calls,
  proactively update on issues, deliver honest estimates?
- **Location** — close vendors reduce drop-off/pickup labor.
- **Capacity** — is the vendor overloaded, or has bandwidth?
- **Specialty match** — does the vendor actually do what
  you're sending them?
- **Warranty on work** — vendor stands behind their work?
- **Payment terms** — net 30, net 15, immediate?
- **Relationship** — long-established, personal rapport with
  the vendor's owner or foreman?

### 5.3 Turn time reality

Vendor turn time is the single most common frustration:

- **Promised vs delivered** — vendors promise Tuesday, deliver
  Friday, ruin the store's sales pipeline.
- **Backlog exposure** — a great vendor whose backlog is 3+
  weeks can't help you meet weekend sales pressure.
- **Batch vs immediate** — some vendors batch work (do all
  Wednesday's cars together), which is efficient but
  inflexible.
- **Complications** — vendor finds additional issues that
  extend the job.

Managing vendor turn time is largely relationship management.
Vendors reciprocate loyalty. Vendors who know you're a
consistent, prompt-paying customer prioritize your work.

### 5.4 Cost variance — estimates vs actuals

When a vendor bills:

- The invoice may match the estimate (good).
- The invoice may exceed estimate due to "additional found
  issues" (justifiable if communicated in advance;
  frustrating if surprise).
- Rare: invoice below estimate (usually because the vendor
  overestimated to leave room; sometimes an honest reduction).

Recon manager tracks estimate-vs-actual per vendor over
time. Vendors whose invoices consistently exceed estimates
by 20%+ get scrutinized or replaced.

### 5.5 Warranty on vendor work

Vendors typically warranty their work — parts and labor for a
defined period (30 days, 90 days, 12 months / 12k miles).

Warranty comes back when:
- Repaired issue reoccurs (customer or store notices).
- New issue traceable to the repair (technique failure).
- Sold customer brings the car back for a warranty issue
  during the vendor's warranty period.

When warranty work is needed, the store contacts the vendor,
the vendor either takes the vehicle back for rework or
provides credit for another shop's work.

Vendors who deny warranty responsibly (blaming the customer,
blaming another shop, blaming "hidden damage") lose the
relationship.

### 5.6 Vendor relationship maintenance

- Prompt payment is table stakes.
- Consistent volume matters (a vendor sees you as a
  significant customer and reciprocates).
- Personal rapport (owner-to-owner or manager-to-manager
  relationships build over years).
- Fair communication (don't ask for "impossible" turn times
  routinely; don't dispute every invoice).
- Reciprocity (occasionally throw the vendor easy jobs, refer
  service customers to their public work, be a good customer).

Good vendors are competitive advantages. Losing a good
vendor to another dealer or a business closure is a real
operational hit.

### 5.7 Vendor performance metrics

Skilled recon managers track:

- **Average turn time** per vendor per category.
- **Average cost** per vendor per job type.
- **Variance to estimate** per vendor.
- **Warranty return rate** per vendor.
- **Quality complaints** — sales team feedback on vehicles
  reconditioned by specific vendors.

Not always formal metrics; often mental scorecards. Larger
stores formalize.

---

## 6. Parts Sourcing

Parts is the material component of recon.

### 6.1 OEM vs aftermarket

- **OEM parts** — original manufacturer parts (from a
  franchise dealer parts counter or online OEM parts
  vendor). More expensive; guaranteed fit; often
  higher-quality materials.
- **Aftermarket parts** — third-party parts (from aftermarket
  suppliers). Cheaper; fit and quality vary; some are
  as-good-as-OEM, some are noticeably inferior.
- **Salvage / used parts** — pulled from wrecked vehicles at
  salvage yards. Cheapest; quality varies; sometimes the
  only option for older or rare vehicles.

The choice depends on:
- Cost budget for the specific unit.
- Availability (OEM back-ordered? Aftermarket instantly
  available?).
- Application (safety-critical parts get OEM; less-critical
  parts can go aftermarket).
- Warranty considerations (some warranties only cover OEM
  parts).

### 6.2 Local vs online sourcing

- **Local parts stores** (NAPA, AutoZone, O'Reilly, Advance,
  local independents) — same-day availability for common
  parts, delivery service, established store accounts with
  discount pricing.
- **OEM dealer parts counter** — same-day for stocked parts,
  next-day for special-order.
- **Online parts vendors** (RockAuto, PartsGeek, various OEM
  online) — often cheaper for the same part; delivery time
  is the tradeoff (2–5 business days typical).
- **Salvage yards** — local yards for used parts; online
  salvage networks for hard-to-find parts.

### 6.3 Parts inventory in the shop

In-house shops typically stock:
- High-turn wear items.
- Common brake pads for popular vehicles.
- Common oil filter sizes.
- Common batteries.
- Miscellaneous hardware and shop supplies.

Non-stock parts get ordered per job. Delay is the cost.

### 6.4 Parts markup vs pass-through

Different stores handle parts markup differently:

- **Pass-through** — parts cost is expensed to the vehicle at
  invoice cost. No markup.
- **Markup** — parts are marked up (25%, 40%, sometimes
  higher) and the difference is service department revenue.

Markup is more common at franchise. Indie recon often
passes through parts at cost. The store's profit is on labor
efficiency, not parts markup.

### 6.5 Parts warranty

Parts carry manufacturer warranty (usually 12 months / 12k
miles for aftermarket, 24 months / 24k miles for OEM). If
a part fails within warranty, the store can claim warranty
replacement from the parts vendor (with proof of purchase
and original defective part in some cases).

Warranty claim workflow is administrative overhead that gets
managed by whoever tracks parts.

### 6.6 Special-order and back-order handling

Sometimes a part isn't available immediately:

- Special order — vendor doesn't stock, orders on request.
  Lead time typically 3–10 days.
- Back-order — part is temporarily unavailable from
  manufacturer. Lead time varies from days to months.
- No-longer-available — part is discontinued. May require
  used part sourcing or vehicle disposition decision.

Back-orders can strand vehicles in recon indefinitely. Recon
manager decides whether to wait, source elsewhere, or
skip/rescope.

---

## 7. Quality Control

Before a vehicle moves to front-line, someone verifies the
recon work was actually done and done right.

### 7.1 Post-recon inspection

A second inspection after work completion:

- Check that all planned work was actually performed.
- Verify no new issues introduced.
- Confirm fluids topped off, tools returned, all interior
  reassembled.
- Test drive to confirm mechanical work is right.
- Visual once-over on cosmetic work.

Often the recon manager or a designated senior tech performs
QC. At smaller shops, the owner may personally sign off on
every unit.

### 7.2 QC checklist

Common items checked:

- Fluids: engine oil, coolant, transmission, brake fluid,
  power steering, windshield washer.
- Filters: engine, cabin, air.
- Belts, hoses, connections tight.
- Wheels torqued, lug nuts tight.
- Tires inflated correctly.
- All warning lights off (no check-engine, no ABS, no airbag).
- All accessories functional (lights, mirrors, windows,
  seats, radio, HVAC, backup camera, keyless entry).
- Interior clean and reassembled.
- Exterior detailed.
- Photos taken.

### 7.3 Test drive

A meaningful test drive:

- Not just around the block — a mixed route (city, highway,
  varied speeds).
- Listen for any noises (bearings, exhaust, suspension).
- Test brakes at multiple speeds.
- Confirm shifting is right through the gear range.
- Check acceleration and any hesitation.
- Verify cruise control and other driver assist features.
- Return to lot; note any issues that need addressing before
  front-line.

### 7.4 Rework decisions

If QC finds issues:

- Minor issues (missing floor mat, dirty spot) — handled on
  the spot.
- Vendor rework — vehicle returned to vendor with a list of
  what needs redoing.
- New-issue discovery — condition changed since original
  inspection or vendor caused a new problem; separate work
  order.

Rework delays front-line-ready and adds cost. Frequent
rework from a specific vendor is a signal to change vendors.

### 7.5 Owner / manager walkthrough

Some stores require the owner or general manager to physically
inspect every unit before it goes front-line. Time-consuming
but a discipline that catches things.

Others delegate entirely to the recon manager. Trust and
volume drive this decision.

---

## 8. Detail

Detail is the last recon touch before photography. Often
overlooked; often the difference between a $16,500 sale and
a $17,500 sale on the same vehicle.

### 8.1 Exterior detail

- Wash (thorough, including door jambs and undercarriage on
  some).
- Clay bar treatment for stubborn contamination.
- Buff and polish for paint clarity.
- Wax or sealant for shine and protection.
- Wheel and tire cleaning.
- Tire dressing.
- Chrome polish (bumpers, trim).
- Headlight restoration (sanding and polishing for
  yellowed / clouded lenses).
- Windshield and window cleaning.
- Bug and tar removal if needed.

### 8.2 Interior detail

- Vacuum every surface (seats, carpet, headliner if fabric).
- Steam clean or extract cleanshampoo carpets and cloth seats
  for stains.
- Leather cleaning and conditioning.
- Dashboard and console cleaning.
- Vent cleaning.
- Door jamb cleaning.
- Odor treatment (ozone or specialized products for smoke,
  pet, mildew).
- Trunk / cargo area cleaning.
- Air freshener applied.
- Owner's manual and paperwork placed neatly.

### 8.3 Engine bay detail (optional)

Some stores clean engine bays; some don't. A clean engine bay
signals attention to detail; sloppy engine bays don't
necessarily hurt sale but don't help.

### 8.4 In-house vs outsourced detail

- **In-house detail team** — dedicated staff. Consistent
  quality, fast turn. Overhead: wages, space, supplies,
  equipment.
- **Outsourced detail** — vendor performs detail. Cost per
  unit, variable quality, timing depends on vendor
  availability.

Detail is often the most in-house-able recon function even at
otherwise outsourced stores (small space, low equipment cost,
labor is unskilled entry-level).

### 8.5 Detail cost

Typical detail cost per unit:
- Light detail (clean trade, minimal work): $75–$150.
- Standard detail: $150–$300.
- Heavy detail (paint correction, stubborn stains, odor
  treatment): $300–$600.
- Full recon detail (extensive paint correction, deep
  cleaning): $500–$1,000+.

---

## 9. Photography

Photos are how the vehicle is presented to online shoppers.
Often the single most-viewed asset for the vehicle.

### 9.1 Photo requirements

Different listing platforms have different requirements (see
`INVENTORY_ACQUISITION_MAPPING.md` §11.2). Common minimums:

- Exterior: 4 corners, straight-on views (front, back, both
  sides), 3/4 angles.
- Interior: driver's seat view, passenger seat view, back
  seat, cargo area, dashboard.
- Features: infotainment screen, gauges, key fob, sunroof if
  present.
- Engine bay.
- Odometer close-up.
- VIN plate close-up (some platforms).
- Wheels close-up (one photo).
- Any special features (tow package, roof rack, etc.).

Total photo count: 20–40 typical, sometimes more for
higher-priced vehicles.

### 9.2 Photo quality

- Good lighting (early morning or late afternoon; avoid
  midday harsh sunlight; avoid rain and overcast).
- Clean backgrounds (many stores build a "photo booth" area
  of the lot with a neutral background).
- Clean vehicle (photos are only as good as the detail).
- Sharp focus.
- Consistent angles across the store's inventory (uniformity
  in the listing catalog).
- No distractions (no salespeople in photos, no other
  vehicles in the frame if possible).

### 9.3 Photographer roles

- **Dedicated in-house photographer** — rare at indies;
  common at large stores.
- **Salesperson doubling as photographer** — very common;
  quality varies.
- **Detail crew member** — occasional; usually less
  aesthetically trained.
- **Outsourced photographer** — some stores use
  professional automotive photographers for consistent
  quality.

### 9.4 Photo editing

- Basic crop and straighten.
- Watermark (dealer logo, dealer info).
- Background removal (some services offer replaced neutral
  background for professional look).
- Color correction for consistency.

Modern software (Photoshop, Lightroom, specialty
dealer-photo services) handles this. Some stores skip
editing and use straight-from-camera images.

### 9.5 Cross-platform photo delivery

Once photos are ready, they need to go to every listing
platform (see `INVENTORY_ACQUISITION_MAPPING.md` §11.4).
Ordering matters — first photo is the hero image; some
platforms show only first 5–10 photos in preview.

### 9.6 Photo aging

Photos should be current. If a vehicle sat in recon for two
weeks with old photos on listings, that's misleading. Some
stores retake photos after significant time or after any
condition change (new tires, minor damage repair).

---

## 10. Listing Preparation Coordination

The handoff from recon to sales / marketing.

### 10.1 What "ready for listing" means

- Detail complete.
- Photos taken and available.
- Vehicle at final resting position on the retail lot.
- Description written (or generatable from vehicle data).
- Priced.
- Windshield sticker (or dealer sticker) applied.
- Ready for customers to see and inquire on.

### 10.2 Description coordination

Description writing is not strictly recon work but happens
at the same stage:

- Feature list (from window sticker, from vehicle data
  system, from tech observation).
- Condition notes (any recon highlights: "new tires," "new
  brakes," "detail complete").
- Vehicle history highlights (one owner, local trade, clean
  Carfax).
- Any dealer-specific language (warranty offer, financing
  offer).

At most indies, listing description is written by an
inventory manager, salesperson, or dedicated internet person
— not by recon directly. But recon input matters ("we
replaced the tires and did the brakes — mention that in
the listing").

### 10.3 Handoff signals

Recon signals to sales / inventory that a unit is ready:

- Update in the DMS status (e.g., "front-line ready" flag
  set).
- Physical move of the vehicle to the retail lot.
- Verbal / text / email notification.
- Morning huddle mention.

If the signal is missed, sales doesn't know the unit is
available, or lists it before it's ready. Communication
protocols matter.

### 10.4 Pre-sold coordination

Sometimes a unit is pre-sold during recon (a customer
committed to the vehicle before recon completed). Recon
manages this by:

- Prioritizing the pre-sold unit in the recon queue.
- Communicating realistic ETA to sales / customer.
- Alerting on any complications that would extend the ETA.

Pre-sold vehicles that miss promised delivery dates create
customer complaints.

---

## 11. Recon Aging

Days-in-recon is a real metric that skilled recon managers
watch.

### 11.1 The recon aging report

Every vehicle currently in recon, with:

- Stock number.
- Date arrived at recon.
- Days in recon.
- Current stage (awaiting inspection / awaiting work /
  in-progress / awaiting parts / at vendor / awaiting QC /
  awaiting detail / awaiting photos).
- Blocker (what's holding it up).
- Expected front-line date.

### 11.2 Recon aging thresholds

- **0–5 days:** normal. Inspection to work in progress.
- **6–15 days:** typical for standard recon.
- **16–30 days:** starting to age. Investigate.
- **31+ days:** stuck. Escalate.

Vehicles in recon 31+ days are often stuck on:
- Parts back-order.
- Body work waiting on paint booth.
- Discovered issue creating scope creep.
- Vendor delay.
- Vehicle jacket confusion (lost paperwork).

### 11.3 Bottleneck identification

Aggregated recon aging surfaces bottlenecks:

- **All vehicles waiting for the body man** — body vendor is
  overloaded; need alternate vendor.
- **Detail crew backup** — need to add capacity or overtime.
- **Photography backlog** — need to assign photo work.
- **Parts back-order across multiple units** — need to
  order proactively or find alternate sourcing.

Recon manager who watches aging patterns catches bottlenecks
before they become problems.

### 11.4 Vehicle-jacket confusion

Sometimes a vehicle sits without progress because paperwork
got lost — the work order, the parts on order, the tech's
notes. Physical vehicle jackets can get misfiled. Digital
jackets can get corrupted or the DMS confused.

Weekly "walk the recon lot" audits catch these.

### 11.5 Sales pressure feedback loop

When sales asks "when is that Explorer going to be ready,"
recon should have an answer. Delayed or vague answers cost
sales opportunities. Real ETAs (backed by knowledge of the
vendor timeline, parts availability, etc.) are load-bearing.

---

## 12. Front-Line Ready Decision

The formal moment when the vehicle moves from recon to
retail availability.

### 12.1 The checklist

Common front-line-ready criteria (varies by store):

- Condition report complete.
- All required and safety work completed.
- Recommended work completed (per store policy).
- QC inspection passed.
- Post-recon test drive completed.
- Fluids topped, tires inflated, all warning lights off.
- Detail complete.
- Photos taken.
- Description ready.
- Priced.
- Vehicle jacket documented (all invoices, all work orders).
- Physical move to retail lot.

### 12.2 Sign-off authority

Who signs off varies:

- **Recon manager** — most common.
- **Owner or GM** — at smaller stores or for higher-value
  units.
- **Senior tech** — for the mechanical assessment portion.
- **Detail lead** — for the cosmetic portion.

Formal sign-off (initial on a checklist, digital toggle in
DMS) creates accountability. Informal sign-off (verbal
"yeah, it's ready") creates confusion.

### 12.3 Front-line status change

Once signed off:

- Vehicle status changes in the DMS.
- Sales team notified (in the morning huddle, in a
  broadcast, in a shared board).
- Listing published on all platforms (or listing status
  changed from "coming soon" to "available").
- Vehicle physically staged on the retail lot.

### 12.4 The retail-eligibility gate

Only front-line-ready units should be sellable. The
vehicle-centric pivot proposes making `stage='frontline'`
the technical gate (see `VEHICLE_CENTRIC_PIVOT.md`
§Workflow). Today this discipline is enforced by convention
and DMS status — occasionally violated (a customer wants a
specific unit still in recon; sales pushes to sell before
front-line-ready; QC gets skipped; customer takes delivery
with issues).

### 12.5 Post-frontline discovery of missed work

Sometimes after front-line status, someone (salesperson,
customer, tech doing something else) discovers work that
should have been done but wasn't.

- Pull unit from front-line back to recon.
- Complete the missed work.
- Return to front-line.

Cost: retail day lost, credibility hit if a customer already
saw the unit. Prevention: better QC, better inspection.

---

## 13. Warranty and Post-Sale Recon

Recon issues don't always end at delivery.

### 13.1 The warranty exposure

Vehicles sold with skipped or incomplete recon can fail
post-sale. The store's exposure:

- **Store's own warranty offer** — some stores offer 30-day /
  1,000-mile warranty on used vehicles. Failures during that
  window are on the store.
- **Federal implied warranty** — most states require an
  implied warranty of merchantability, meaning the vehicle
  is fit for its ordinary purpose. Egregious defects create
  legal exposure.
- **Buyer's Guide "As Is" vs "Warranty"** — the FTC-required
  Buyer's Guide checkbox for "As Is - No Warranty" or a
  specific warranty offer. Language matters.
- **Vehicle Service Contract (VSC)** claims — if the
  customer bought a VSC, some post-sale failures are covered
  by the VSC provider, not the store. But the store's
  relationship with the customer is still at stake.
- **Chargeback risk** — lenders may chargeback dealer
  compensation on deals that default early due to vehicle
  problems.
- **Reputation exposure** — a bad-vehicle story on social
  media or online review can hurt future sales.

### 13.2 Customer post-sale complaints

Customer returns with an issue:

- Store investigates (tech looks at it).
- Decision: cover repair, cover partially, deny.
- If covered: rework at the store's cost.
- If denied: customer relationship potentially damaged;
  possible escalation to BBB, state consumer protection, or
  small claims court.

The judgment on "cover or deny" is judgment. Small issues
covered generously build reputation. Large issues denied
harshly damage reputation. Wise stores lean toward covering
when reasonable.

### 13.3 Post-sale service opportunities

For stores with in-house service:
- Post-sale customer becomes a service customer.
- First oil change often complimentary or discounted.
- Ongoing service relationship becomes a repeat-buy channel
  (see `SALES_DEPARTMENT_MAPPING.md` §7.7).

For outsourced-service stores:
- Recommendation to a partner shop.
- Loose relationship with post-sale customer.

### 13.4 Warranty labor tracking

If in-house service, warranty labor should be tracked
separately:

- Not billed to the vehicle (already sold).
- Not billed to a customer (covered by store warranty).
- Charged to a "warranty expense" account.

If outsourced, similar — vendor invoice for warranty work
goes to warranty expense, not to vehicle cost.

Warranty expense is a metric worth watching. Rising warranty
expense signals recon quality problems upstream.

---

## 14. Pain Points

Repetitive friction recon staff experience daily. Documentation
only; no solutions proposed.

### 14.1 Vendor turn-time unreliability

Vendor promised Tuesday. Vehicle sitting Wednesday, Thursday.
No call from vendor. Have to call to check status. Sales
pressure builds. Repeat every week.

### 14.2 Discovered work mid-recon

Job started as brake pads. Tech opens it up and finds seized
caliper. Scope expands. Cost expands. Timeline extends.
Recon manager has to re-approve and communicate change.

### 14.3 Parts availability surprises

Vehicle scheduled for work today. Tech starts, needs a part.
Local parts store doesn't have it. Special order 3 days.
Vehicle sits.

### 14.4 Inspection quality variance

Some inspections are thorough; some are cursory. When a
cursory inspection misses something that emerges during
recon, scope changes and timeline slips.

### 14.5 Vehicle-jacket confusion

Physical jacket lost or incomplete. Digital jacket unclear
which invoice matches which repair. Tech doesn't know what
was already done. Wasted labor investigating history.

### 14.6 Multiple techs on the same vehicle

Vehicle passed from tech A (mechanical) to tech B (brakes) to
tech C (detail). Miscommunications about what's done, what's
pending. Sometimes work gets duplicated; sometimes gets
skipped.

### 14.7 Chasing vendors for status

The store's coordinator spends significant time each day
calling vendors: "Is the Explorer ready?" "When can you take
the Camry?" "Did you get the parts I sent?" Time drain.

### 14.8 Chasing vendors for invoices

Vendor did the work weeks ago; invoice hasn't arrived.
Store's accounting can't close out the vehicle cost.
Recurring administrative friction.

### 14.9 Detail crew capacity

Weekend approaches with 8 units needing detail and 2
detailers. Overtime or slip the front-line date. Either way,
sales suffers.

### 14.10 Photography backlog

Vehicles ready for photos, no photographer available.
Vehicles sit an extra day (or three) without listing
readiness.

### 14.11 Communication gaps with sales

Sales asks recon manager for ETA on 5 vehicles. Recon
manager has to check DMS, check vendor status, check
tech calendar, remember what parts are on order.
Not a fast answer.

### 14.12 Rework friction with vendors

QC caught an issue after vendor completed work. Vendor
disputes ("customer must have caused it"). Time and energy
resolving the dispute; sometimes lose the labor cost.

### 14.13 Owner interruptions

Owner walks up: "put the Explorer aside, I need it fixed
today for a customer." Existing schedule blown up. Other
vehicles' timelines slip.

### 14.14 Post-sale warranty callback

Customer 20 days post-sale calls with an issue. Recon
manager has to remember the vehicle, pull the jacket, decide
on coverage, arrange the repair. Time drain that produces no
new revenue.

### 14.15 Vendor pricing drift

Vendor's prices creep up over time. Nobody negotiates
because "it's a good vendor." Recon costs quietly rise.

### 14.16 Weather delays

Rain / cold / heat delays paint, delays outdoor work, delays
transport. Nothing to do but wait.

### 14.17 Parts markup pass-through complaints

Store passes vendor parts markup through to vehicle cost.
Owner questions "why did that job cost $350 instead of $200?"
Recon manager explains parts pricing, feels defensive.

### 14.18 Recon estimate accuracy under time pressure

At auction, buyer estimated $800 recon. Actual recon $1,600.
The extra $800 came out of gross. Buyer's estimating is
under-scrutinized because he's rarely challenged, but the
gap has real impact.

### 14.19 New tech ramp-up

New tech hired. First few weeks: slower than experienced
tech, occasional errors. Existing team covers extra work.
Ramp-up cost paid by recon capacity, not measured
separately.

### 14.20 Losing a good vendor

Vendor closes shop, retires, or sells to someone less good.
Recon manager has to rebuild the vendor relationship, often
at higher cost or lower quality for months.

---

## 15. Operational Decisions

Decisions recon staff make repeatedly. Each is a candidate for
future decision-support intelligence.

### 15.1 Which finding to fix vs skip?

For each condition-report finding, must-do vs should-do vs
skip. Cost, warranty risk, retail impact all in play.

### 15.2 In-house or send out?

For a specific job, does in-house shop have capacity and
capability today? Or is this a vendor job? Cost, time, and
quality tradeoffs.

### 15.3 Which vendor for this job?

Multiple vendor options for the same job category. Which
vendor gets this one? Based on turn time need, cost, current
vendor backlog, quality confidence.

### 15.4 OEM or aftermarket for this part?

Safety-critical part or wear item? Cost pressure or quality
priority? Backorder concern? Aftermarket acceptable?

### 15.5 Which unit gets priority in the queue?

Pre-sold unit ahead of others. Aged inventory ahead of fresh.
Higher-gross opportunity ahead of lower. Recon manager makes
the call.

### 15.6 Escalate discovered issue to management?

Tech found something not in the original scope. Small enough
to handle within budget authority? Or needs manager approval
for expanded scope?

### 15.7 Approve or deny warranty work?

Customer returned with issue. Coverage judgment: full cover,
partial cover, deny.

### 15.8 Rework request to vendor: push or absorb?

QC found an issue with vendor's work. Push vendor to rework
(relationship friction, delay) or absorb the cost (financial
hit but no relationship damage)?

### 15.9 Front-line early or wait?

Unit is 95% ready. Sales wants it front-line today. Can it be
listed as "coming soon" or should we wait for full readiness?

### 15.10 Pull from front-line to fix?

Unit already front-line; salesperson noticed an issue.
Pull for repair (loses retail day) or address at sale time?

### 15.11 Buy new tools or continue outsourcing?

Recurring category of work sent to outside vendor. Cost
justifies buying the equipment and doing in-house?

### 15.12 Add capacity or extend timeline?

Recon backlog growing. Bring in overtime, add temp help,
send more to vendors, or accept longer front-line times?

### 15.13 Salvage-part or new-part for older vehicle?

Older vehicle needs a part. New part is expensive; salvage
part is cheap but variable quality. Vehicle's total value
matters.

### 15.14 Change vendors?

Current vendor has been sliding on quality or cost or
timeliness. Cost of switching (rebuilding relationship,
possible timeline hit) vs. cost of continuing?

### 15.15 Wholesale-out mid-recon?

Discovered issue makes recon economically questionable.
Complete the work anyway or stop and wholesale-out?

### 15.16 Photograph now or after listing polish?

Photos are the most-viewed asset. Rush to get listing up or
wait for optimal photography conditions?

---

## 16. Automation Opportunities

Where repetitive administrative work lives. Opportunity
identification only.

### 16.1 Condition-report structured entry

Instead of freeform text notes, structured entry per
category with severity tagging. Human-authored content;
structured storage. Enables all downstream analysis.

### 16.2 Recon plan generation from condition report

Given completed condition report, draft (never execute)
proposed work plan: which items to fix, in what sequence,
suggested vendor per item, estimated cost per item, total
estimated cost. Recon manager reviews and adjusts.

### 16.3 Vendor recommendation per job

Based on job category, current vendor performance data
(turn time, cost, quality), and current vendor availability,
suggest the best-fit vendor for a specific job. Recon
manager picks or overrides.

### 16.4 Parts pre-order workflow

Once work plan is approved, generate parts orders per job,
pre-populate with the specific parts needed, route to the
approver, submit to sourcing.

### 16.5 Vendor communication drafting

Draft vendor emails/texts for job assignment, status
follow-up, invoice questions. Human reviews and sends.

### 16.6 Recon aging dashboard

Real-time view of every vehicle in recon, current stage,
days in stage, blocker (if any), suggested next action.

### 16.7 Bottleneck alerts

Systemic bottleneck detection: "3 vehicles have been waiting
at Body Vendor A for over 10 days." Recon manager sees
patterns rather than individual delays.

### 16.8 Sales-team new-arrival broadcast

When a vehicle changes status to "front-line ready," sales
team gets automatic notification with photos, features, and
suggested-customer notes.

### 16.9 ETA update workflow

When a vendor updates a timeline (verbally or via message),
that update propagates to sales / DMS / customer-facing
listings. Reduces "why does the DMS still say Tuesday when
we all know it's Thursday" friction.

### 16.10 Cost-variance tracking

Actual cost per vendor per category vs estimates. Vendor
performance quantified over time. Estimate accuracy
quantified per buyer / recon manager.

### 16.11 Vendor warranty tracking

Which vendor performed which work on which unit? When
warranty comes back, automatically identify the responsible
vendor.

### 16.12 Photo-workflow status

Vehicle detailed but not yet photographed → surface to
photographer's queue. Photos taken → surface to listing
publish workflow. Reduce manual coordination.

### 16.13 Front-line-ready checklist enforcement

Prevent status change to front-line unless every checklist
item is completed. Enforced discipline (currently
convention-based).

### 16.14 Warranty exposure alerts

Deals sold with skipped-recommended items get tagged for
post-sale warranty monitoring. Return rates by skipped-item
category quantified.

### 16.15 Recon-cost prediction

Given VIN, condition report, and store's historical data,
predict likely total recon cost. Compared to buyer's
estimate. Variance signals estimating skill or scope
creep.

### 16.16 Vendor invoice automation

Vendor invoices received (digital or scanned) get parsed,
matched to work orders, routed to approval, entered into
accounting. Reduces paper handling.

### 16.17 Recall check automation

Every acquired vehicle automatically has VIN checked against
NHTSA recall database. Open recalls surfaced to recon
manager.

Each is a candidate for its own future planning session.

---

## 17. Cross-Department Dependencies

### 17.1 Inventory & Acquisition

**Recon depends on Inventory for:**
- Timely delivery of acquired vehicles to the recon area.
- Buyer's initial recon estimate (informs planning and
  budget).
- Vehicle jacket with acquisition documents, VIN, mileage,
  known issues from auction disclosure.
- Priority signals (which units are needed for sales sooner).
- Budget authorization for higher-cost items.
- Wholesale-out decision when recon exceeds economic sense.

**Inventory depends on Recon for:**
- Accurate condition report (informs pricing and retail
  potential).
- Realistic recon estimates (informs future buying
  discipline).
- Realistic ETAs on in-recon units.
- Front-line-ready signal (unit truly ready).
- Communication when scope changes or a bigger problem
  emerges.
- Quality workmanship (chargebacks and warranty come from
  poor recon).

### 17.2 Sales

**Recon depends on Sales for:**
- Priority signals (pre-sold units ahead of others).
- Realistic customer promises on delivery dates (don't
  promise Saturday when recon is Wednesday-ready-earliest).
- Post-sale feedback on issues customers reported.
- Feedback on vehicles the customer noticed
  quality-of-recon issues at inspection.

**Sales depends on Recon for:**
- Reliable ETAs on in-recon units.
- Steady flow of front-line-ready inventory.
- Communication of scope-change or delay proactively.
- Photos and description details of what was done to each
  vehicle (basis for selling story).
- Support on post-sale warranty issues.

### 17.3 F&I (Finance and Insurance)

**Recon depends on F&I for:**
- Feedback on VSC claim patterns (which vehicle categories,
  recon skips, or vendor issues predict VSC claims).
- Communication of chargeback trends that trace back to
  recon quality.

**F&I depends on Recon for:**
- Vehicle in the condition sold to the customer (customer
  post-sale surprises are worse than any product menu
  problem).
- Support on claims requiring recon documentation.

### 17.4 Accounting

**Recon depends on Accounting for:**
- Timely vendor invoice processing and payment.
- Cost accumulation per vehicle (running total).
- Parts inventory accounting.
- Warranty expense tracking separately.
- Reconciliation of vendor statements.
- Approval workflow for larger invoices.

**Accounting depends on Recon for:**
- Correct coding of invoices (which vehicle / which
  category).
- Timely approval of vendor invoices.
- Notification of any adjustments (rework credits, warranty
  claims, disputed invoices).
- Communication of unusual recon scope (major work needing
  special approval).
- Parts inventory usage information.

### 17.5 Vendors

**Recon depends on Vendors for:**
- Reliable turn time.
- Quality workmanship.
- Honest estimates.
- Fair pricing.
- Prompt communication on issues.
- Standing behind warranty.
- Capacity when needed.

**Vendors depend on Recon (dealer) for:**
- Prompt payment.
- Fair volume (not just calling when in a bind).
- Reasonable expectations (not asking for impossible turn
  times routinely).
- Cooperative dispute resolution.
- Honest work descriptions (not asking vendors to
  rush-work under false claims of urgency).

### 17.6 Ownership

**Recon depends on Ownership for:**
- Budget authorization on higher-cost work.
- Approval on wholesale-out decisions.
- Support on vendor relationship issues.
- Strategic guidance (which recon investments are worth it,
  which aren't).
- Backup on scope-expansion decisions.
- Warranty claim decisions on borderline cases.

**Ownership depends on Recon for:**
- Cost discipline (staying within recon budget expectations).
- Quality execution (units that don't come back with
  warranty issues).
- Turn-time discipline (units flow through in reasonable
  windows).
- Vendor management (relationships maintained, no crises).
- Warranty exposure minimization.
- Communication of issues before they become bigger
  problems.

---

## 18. Deferred Ideas

Ideas that surfaced during Recon research but belong to other
departments' future research.

**Inventory & Acquisition** — Buyer's recon-estimate accuracy
analytics; auction-source recon-cost patterns; wholesale-out
decision analytics; per-vehicle-category recon-cost
benchmarks.

**Sales** — Pre-sold vehicle delivery-date accuracy; sales
promise vs recon reality reconciliation; post-sale customer
complaint tracking with recon traceback.

**F&I** — VSC claim analytics by recon vendor / recon
category; chargeback traceback to recon quality;
warranty-eligible items that were skipped in recon.

**Accounting** — Vendor invoice automation; parts inventory
management; warranty expense tracking; in-house labor cost
allocation to vehicles.

**Titles / DMV** — Recall check integration (open recalls at
acquisition, required-before-sale in some states).

**Compliance** — Safety recall handling workflow; Buyer's
Guide warranty disclosure accuracy; state-specific inspection
requirements.

**Marketing** — Photography workflow beyond recon (marketing
uses of photos, brand-consistent photography); listing
description generation coordinated between recon (technical
detail) and marketing (buyer-facing language).

**Service Department** (for stores with public service in
addition to recon) — Service department capacity balancing
between paid customer work and recon; internal labor rate
optimization; public service as customer-retention channel.

**Vendor Management System** — Formalized vendor performance
tracking, vendor selection based on multiple criteria, vendor
relationship health monitoring, vendor payment workflow.

**Quality Assurance** — Formal QC checklist system; QC pass
rate tracking; rework rate by vendor; post-sale defect rate
by vendor / by recon type.

**BHPH-Specific Recon** — Longer-term reliability focus
(vehicle needs to last the BHPH loan term without becoming a
repo); different budget calculus (cheaper vehicles, tighter
recon budgets); different customer expectations.

**Portable Photo Studios / Photo Automation** — Booth
construction, photo composition automation, AI-assisted photo
editing.

**Warranty Program Design** — Store warranty terms, coverage
policies, cost accrual models, exclusions.

**Recall Management** — Systematic open-recall handling,
recall completion tracking, customer notification of
post-sale recalls.

Each of the above deserves its own research session before
implementation.

---

## How to use this document

**For engineers and product people** starting recon /
condition-report / work-order / vendor-management work: read
sections 1–3 first (the landscape, the inspection, and the
planning discipline). Those sections carry the mental model.
Read section 17 (dependencies) before designing anything that
connects to other departments. Section 16 (automation
opportunities) is where product ideas start — but each
opportunity should be developed into its own scoped plan
before implementation.

**For AI agents** starting a Recon-related session: this
document is source-of-truth for how independent dealerships
actually recondition vehicles. If anything you're asked to do
contradicts what's described here, push back. Particular
anti-patterns to flag:

- Any suggestion that AI should author condition-report
  findings. Findings must trace to human observation.
- Any suggestion that AI should approve work autonomously.
  Recon scope decisions have cost and warranty implications
  that belong to human judgment.
- Any suggestion that AI should dispatch to vendors or send
  emails without human review. All vendor communication
  remains drafts pending recon-manager approval.
- Any suggestion that "streamline" means skipping QC. QC is
  the discipline that prevents warranty claims. Automation
  supports QC, doesn't replace it.
- Any suggestion that the front-line-ready decision is
  algorithmic. Some units meet checklists but aren't
  actually ready; some units don't meet a checklist strictly
  but are ready. Human judgment matters.

**For domain experts** reading this document: this is a
snapshot of common indie practice. Every store has its own
recon philosophy (aggressive-turn vs. quality-first), its own
vendor stable, its own in-house/outsource balance.
Corrections and additions are welcome.

**Update discipline.** Update this document when:
- New recon-service categories emerge (electrification
  changes may bring new categories: battery service, EV
  charging system recon).
- Regulatory changes affect recon (new safety-recall
  requirements, new emissions-testing rules).
- Common industry-benchmark metrics shift meaningfully.

Do **not** update this document with:
- Specific software product feature reviews.
- Personal opinions about specific vendors or shops.
- Implementation designs.

---

## Glossary — recon terms used in this document

- **Bay** — a service work area in a shop; a shop's capacity
  is often measured in bays.
- **Book time** — manufacturer's or industry-standard
  estimated time to complete a specific job. Compared to
  real time actually spent.
- **CCA** — Cold Cranking Amps. Battery capacity metric.
- **Detail** — comprehensive cleaning of interior and
  exterior; the last recon step before photography.
- **Diagnostic** — investigation of a mechanical or
  electrical issue to identify root cause.
- **Discovered work** — issues found during scheduled work
  that weren't in the original scope.
- **Flat rate** — pay structure where technician is paid per
  job (at book time) regardless of actual time spent.
- **Front-line ready** — vehicle fully reconditioned,
  detailed, photographed, and available for retail sale.
- **NHTSA** — National Highway Traffic Safety Administration.
  Maintains recall database.
- **PDR** — Paintless Dent Repair. Specialty vendor for
  dings and dents without paint work.
- **PSI** — Post-Sale Inspection. Optional paid mechanical
  inspection at an auction after purchase.
- **QC** — Quality Control. Post-recon verification that
  work was done correctly.
- **Recall** — manufacturer-issued notice that a vehicle has
  a defect requiring remedy, typically at no cost to the
  owner.
- **R.O.** — Repair Order. Work order document authorizing
  and tracking a specific job.
- **Rework** — re-doing work that was completed but found to
  be incorrect or incomplete.
- **Salvage / used parts** — parts pulled from wrecked or
  disposed vehicles.
- **Scope creep** — expansion of a job's scope during
  execution.
- **Service writer** — person who creates R.O.s and
  interfaces between technicians and dispatch.
- **Turn time** — days from job start to job completion at a
  vendor or in a shop.
- **VSC** — Vehicle Service Contract. Aftermarket coverage
  for post-warranty mechanical issues. See
  `FINANCE_DEPARTMENT_MAPPING.md`.
- **Walk-away cost** — recon cost above which the vehicle
  should be wholesaled rather than reconditioned.
- **Warranty comeback** — customer returning after sale with
  an issue covered by store warranty or implied warranty.

---

## Related research

- `INVENTORY_ACQUISITION_MAPPING.md` — Inventory & Acquisition
  department; upstream of recon (acquisition initiates recon).
- `SALES_DEPARTMENT_MAPPING.md` — Sales department; consumes
  front-line-ready inventory and drives demand signals back.
- `FINANCE_DEPARTMENT_MAPPING.md` — F&I; product sales that
  can be triggered by recon-quality confidence
  (customer's willingness to buy a VSC influenced by
  perceived vehicle condition).
- `ACCOUNTING_DEPARTMENT_MAPPING.md` — Accounting; tracks
  every recon transaction, vendor payment, cost accumulation.
- `VEHICLE_CENTRIC_PIVOT.md` — Architectural plan for
  building software that supports the recon operations
  described in this document. Phase 2 (Condition report),
  Phase 3 (Recon automation), and Phase 5 (Photography +
  listing generation) all touch this domain directly.
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

*End of Reconditioning Department mapping.*
