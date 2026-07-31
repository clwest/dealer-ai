---
title: "Dealer AI Kit — Implementation Roadmap"
status: authoritative
type: implementation-contract
generated: 2026-07-31
generated_at_session: SESSION_034
sources:
  - docs/PROJECT_RULES.md
  - docs/BUSINESS_DOMAIN_MAP.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/INDEPENDENT_DEALER_PIVOT.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/RECON_MAPPING.md
  - docs/research/SALES_DEPARTMENT_MAPPING.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
supersedes: none
applies_to:
  - All future implementation sessions
  - All AI agent sessions
---

# Dealer AI Kit — Implementation Roadmap

> **What this is.** The implementation contract for the project.
> Every milestone traces to one or more documented operational
> pain points in the research corpus. Every milestone identifies
> reusable existing code and states its scope boundary.
>
> **What this is not.** A design document. There are no model
> names, endpoint paths, UI layouts, or code structures in the
> milestones — those are decided *within* each milestone at
> implementation time under the Research Before Design chain.
>
> **How to use it.** When a session begins, read the highest
> unshipped milestone and pick a scope that is small and
> complete inside that milestone. Do not silently expand a
> milestone. Do not silently jump ahead. When a new idea
> surfaces, apply the Discovery Rule: if it doesn't map to a
> documented business problem for the current milestone, defer
> it — never discard it.
>
> **Precedence.** The six rules in `docs/PROJECT_RULES.md`
> override every milestone in this document. If a milestone
> contradicts a rule, the rule wins and the milestone is wrong.

---

## 1. How to read this document

The doc has three main parts:

- **Section 2 — Reconciliation summary.** For each major
  business capability named in the domain map, its status
  against the current codebase (Fully / Partially / Not
  Implemented) and the reusable primitives that would extend
  the existing implementation.
- **Section 3 — Existing reusable primitives.** A catalog of
  the eight primary shipped capabilities that will be extended
  (not rebuilt) by future milestones. Each milestone cites from
  this catalog by number.
- **Section 4 — Milestone sequence.** The ordered list of
  milestones. Every milestone has: business objective, related
  research, operational pain points, existing reusable
  implementation, gap, scope boundary, recommended-order
  justification.

Section 5 captures explicit non-goals and deferrals. Section 6
records the scope-discipline verification for the roadmap as a
whole.

---

## 2. Reconciliation summary — business capability vs. shipped code

The domain map (`docs/BUSINESS_DOMAIN_MAP.md`) names the
canonical business capabilities across six departments. The
capability matrix (`docs/CAPABILITY_MATRIX.md`) enumerates
what the platform actually ships today. This section
reconciles the two.

**Legend:**
- **F** = Fully implemented (business need is met today)
- **P** = Partially implemented (some capability exists; a
  documented business need remains unmet)
- **N** = Not implemented (no capability exists that serves
  this business need)

### 2.1 Inventory & Acquisition

| Business capability | Status | Reusable primitives (see §3) | Notes |
|---------------------|--------|------------------------------|-------|
| Vehicle identity record (stock number, VIN, description) | F | §3.5 Vehicle model | Vehicle model with `stock_number` unique, VIN, YMM, features |
| Multi-source inventory import (upsert, per-source) | F | §3.6 inventory_import | CSV importer with per-source upsert-by-stock discipline |
| Acquisition record (source, purchase price, fees, purchase date) | N | §3.5 Vehicle model (target) | No VehicleAcquisition or equivalent |
| Per-vehicle cost basis + running investment total | N | §3.5 Vehicle model (target) | No VehicleCost ledger |
| Floor plan advance / interest / curtailment tracking | N | §3.2 payment math (interest math reusable) | No floor plan schedule; no daily accrual |
| Aging report + reprice cadence (Day 15/30/45/60/90/120) | N | §3.7 recommended-actions pattern (extends cleanly) | No aging bucket logic; no reprice suggestion generator |
| Trade appraisal record (customer trade → wholesale value + allowance) | N | §3.2 payment math (some reuse) | No trade appraisal entity |
| Wholesale disposition path | N | — | Not present |
| Company-use / owner-use reclassification | N | — | Not present |

### 2.2 Recon

| Business capability | Status | Reusable primitives | Notes |
|---------------------|--------|---------------------|-------|
| Structured condition report (category + severity + photos) | N | §3.5 Vehicle model (target) | No ConditionReport / ConditionFinding |
| Recon work plan (must / should / won't do sequencing) | N | §3.7 recommended-actions pattern | Cleanly generalizable |
| Vendor entity + per-vendor turn/cost history | N | — | Not present |
| Work order (in-house or vendor) with status + cost | N | §3.4 handoff-packet pattern (assembly) | Not present |
| Parts order tracking | N | — | Not present |
| QC checklist + rework routing | N | — | Not present |
| Multi-photo upload / gallery per vehicle | N | §3.5 file storage (currently one-logo-deep) | File storage needs extension |
| Recon aging + bottleneck reporting | N | §3.7 recommended-actions pattern | Extends |
| AI-drafted vendor emails / POs / work orders (human-approved) | N | §3.3 ad_copy / follow_up drafting; §3.1 llm_safety | Direct pattern reuse |
| Warranty callback (post-sale repair) tracking | N | — | Not present |

### 2.3 Customer Acquisition & Sales

| Business capability | Status | Reusable primitives | Notes |
|---------------------|--------|---------------------|-------|
| Lead capture from chat channel | F | §3.8 leads + salesperson system | Chat sessions → leads pipeline |
| Lead capture from other channels (walk-in, phone, listing forms) | N | §3.8 leads pipeline (target) | Only chat-originated leads today |
| Customer profile with rich notes (family, job, preferences, concerns) | P | §3.8 lead detail + session profile | Chat session profile exists; not the full CRM record described in research |
| Vehicle matching to customer needs | F | §3.2 payment math + budget classifier + retrieval | Chat engine matches vehicles by keyword + budget |
| Walk-around / test-drive / demonstration tracking | N | — | Not present |
| Deal write-up (four-square, sales worksheet) | N | — | Not present |
| Trade appraisal (see Inventory 2.1) | N | — | Not present |
| Sales-to-F&I handoff packet | P | §3.4 handoff-packet builder | Handoff packets exist for lead → salesperson; F&I handoff packet does not |
| Delivery checklist (vehicle prep, customer education, temp-tag, insurance) | N | — | Not present |
| Follow-up cadence orchestration (24hr / 1wk / 30day / 90day / 6mo / 1yr) | P | §3.3 follow-up drafts (with invented_appointment scrub) | Individual drafts exist; scheduled cadence orchestration does not |
| Be-back tracking (unsold customer scheduled re-contact) | N | §3.8 leads pipeline (target) | Not present |
| Referral capture + attribution | N | — | Not present |
| Ad-copy generation (trending-signal driven) | F | §3.3 ad_copy | Ephemeral drafts only — no persistence |
| Manager coaching chat | F | (self-contained) | Stateless coaching chat with structural enforcement |

### 2.4 Finance (F&I)

| Business capability | Status | Reusable primitives | Notes |
|---------------------|--------|---------------------|-------|
| Credit application intake (signed, retained) | N | — | Not present; heavy compliance |
| Bureau pull integration | N | — | Not present |
| Tier assessment (FICO band → lender panel) | N | — | Not present |
| Deal structure (LTV / PTI / DTI / term / rate / down) | P | §3.2 payment math + budget classifier | The math exists; the structuring surface does not |
| Lender submission tracking (per-deal, per-lender, waterfall) | N | — | Not present |
| Approval / counter / decline response tracking | N | — | Not present |
| Stipulation package tracking (stips required → gathered → verified) | N | §3.4 handoff-packet pattern | Not present |
| RISC + product agreements (VSC / GAP / T&W) | N | — | Not present |
| Funding packet assembly + funding record | N | §3.4 handoff-packet pattern | Not present |
| Chargeback recording + commission reversal | N | — | Not present |
| Per-deal compliance record (retention 2–7 yr) | N | — | Not present |

### 2.5 Accounting

| Business capability | Status | Reusable primitives | Notes |
|---------------------|--------|---------------------|-------|
| Deal booking (post to GL) | N | — | Not present |
| Vendor invoice processing (approve → check / ACH → post) | N | — | Not present |
| Bank reconciliation (statement to GL) | N | — | Not present |
| Contracts-in-transit (CIT) schedule + funding tracking | N | — | Not present |
| Floor plan reconciliation (schedule to lender statement) | N | — | Depends on floor plan entity (see 2.1) |
| Per-vehicle cost accumulation | N | §3.5 Vehicle model (target) | Depends on cost entity (see 2.1) |
| Title arrival + aging + storage tracking | N | — | Not present |
| Reserve receivable + product commission receivable schedules | N | — | Depends on F&I entities (see 2.4) |
| Monthly close + trial balance + adjusting entries | N | — | Not present |
| Financial statement production (P&L, balance sheet, cash flow) | N | — | Not present |
| Sales tax filing | N | — | Not present |
| Payroll + payroll tax deposits | N | — | Not present (typically external service) |
| 1099 / W-2 issuance | N | — | Not present (typically external service) |

### 2.6 BHPH Operations

| Business capability | Status | Reusable primitives | Notes |
|---------------------|--------|---------------------|-------|
| BHPH note origination (structural) | P | §3.2 payment math BHPH variant | Weekly/biweekly math exists; note record does not |
| Payment schedule per contract | N | §3.2 payment math (schedule generator reuses) | Not present |
| Payment intake + posting (cash / debit / ACH / online / third-party) | N | — | Not present |
| Payment ledger per account (application: fees → interest → principal) | N | — | Not present |
| Delinquency detection + escalation buckets (1-10 / 11-30 / 31-60 / 61-90 / 91+) | N | §3.7 recommended-actions pattern (extends) | Not present |
| Reminder / collection contact log | N | §3.3 follow-up drafts pattern (reusable) | Not present |
| Promise-to-pay tracking | N | — | Not present |
| Skip-tracing record | N | — | Not present |
| Repossession record (order → agent → recovery → inventory) | N | §3.4 handoff-packet pattern (repo packet) | Not present |
| Redemption window + notice tracking | N | — | State-law-driven |
| Post-repo disposition (retail vs. wholesale) | N | (uses Inventory paths) | Depends on Inventory disposition |
| Deficiency / surplus calculation + collection | N | §3.2 payment math (partial) | Not present |
| Portfolio aging report | N | §3.7 recommended-actions pattern | Not present |
| Static-pool loss analysis | N | — | Not present |
| GPS / starter-interrupt device integration | N | — | Not present; vendor-integration |
| Repeat-buyer outreach (approaching payoff → sales handoff) | N | §3.3 follow-up drafts pattern | Not present |
| Indie-prohibited-copy scrub (protects BHPH customer comms from OEM-captive language) | F | §3.1 llm_safety | Shipped SESSION_030 Phase 1 |

### 2.7 Cross-cutting foundations

| Business capability | Status | Reusable primitives | Notes |
|---------------------|--------|---------------------|-------|
| 16-stage LLM safety stack (pre-LLM guards + post-LLM scrubs) | F | §3.1 llm_safety | The moat; Day-1 dependency for every drafted artifact |
| Deterministic payment math (APR + BHPH weekly/biweekly + affordable_max_price) | F | §3.2 payment math | LLM never invents money math |
| Runtime dealer identity resolver (env → profile → default) | F | §3.9 dealer_config | Also right shape for per-vehicle overrides |
| Dealer onboarding profile (35 fields, indie shape-of-business) | F | §3.10 onboarding profile | Complete for the fields captured |
| Runtime brand tokens (frontend `brand.*`; useBrand + useDealerProfile) | F | (self-contained) | Multi-tenant capable at the presentation layer |
| Chat-engine safety pipeline (chat/message + vehicles/<id>/ask) | F | §3.1 + §3.2 | 8-stage pre-LLM chain + 8-stage post-LLM scrubs; 1300 tests |
| Multi-tenancy (Dealership FK-carrier model) | N | — | Singleton onboarding profile today |
| Real authentication + role-based permissions | N | — | Slug-by-obscurity for advisor workspace; no other auth |
| Multi-photo file storage (S3-compatible + CDN) | N | (logo upload uses default_storage) | One-logo-deep today |
| Async job orchestration (Celery / Redis) | N | — | Not present; deferred per VCP |
| Prod deployment | N | — | Render Blueprint staged, not active |

### 2.8 What this reconciliation says at a glance

- **The chat / lead / advisor / ad-copy / coaching surfaces are
  substantially built.** The retail-facing side of the sales
  motion is the mature part of the codebase.
- **The vehicle-operational side (acquisition, recon, lifecycle,
  photography, listing) is barely started.** Vehicle exists as
  a card; there is no ledger, no condition report, no vendor,
  no work order, no lifecycle stage.
- **F&I as a full department is not built.** Deal math exists;
  deal desk does not.
- **BHPH as a full department is not built.** Deal-writeup
  math exists; portfolio operations do not.
- **Accounting as a full department is not built.** The
  reconciliation layer is greenfield.
- **Two foundations must land before sensitive-data surfaces:**
  multi-tenancy and real auth.

---

## 3. Existing reusable primitives (extend, do not duplicate)

Numbered so milestones can cite specifically.

### §3.1 LLM safety stack (`services/llm_safety.py` + tests)
16 stages (8-stage pre-LLM guard chain + 8-stage post-LLM
scrub stack) plus fabricated-inventory, invented-promotion,
invented-appointment, indie-prohibited-copy scrubs. Backed by
the majority of the 1300-test baseline. **Non-negotiable Day-1
dependency for every AI-drafted artifact** — recon vendor
emails, POs, work-order narratives, listing copy, F&I customer
messaging, BHPH customer messaging.

### §3.2 Payment engine (`services/payment_engine.py`)
Deterministic APR math + BHPH weekly/biweekly variant +
`affordable_max_price` reverse-solve. Same math computes daily
floor-plan interest accrual. LLM never touches money math.

### §3.3 LLM drafting patterns (`services/ad_copy.py`,
`services/follow_up.py`)
The archetypal "LLM drafts → post-LLM scrub → return to
operator for approval" pattern. Direct pattern reuse for:
listing copy, vendor emails, PO drafts, work-order narratives,
BHPH reminder-language templates, F&I customer explanations.

### §3.4 Handoff-packet builder (leads admin handoff endpoint)
Assembles a structured packet from disparate source data.
Pattern generalizes to: recon-work-order-to-vendor packet, F&I
funding packet, BHPH repo packet, delivery packet.

### §3.5 Vehicle model + inventory identity
`Vehicle.stock_number` (unique per dealer), VIN, YMM, features,
`imported_at`, `last_seen_at`, `source`. The correct primary
identity to hang lifecycle, cost, condition, photos, and
listing off. Note: `Vehicle.is_available` is currently one
boolean covering all pre-frontline states — needs replacement
with computed lifecycle stage.

### §3.6 Inventory import (`services/inventory_import.py`)
CSV upsert-by-stock-number with per-source scoping and
soft-unavailable discipline. Exactly the shape auction-feed
adapters (Manheim / ADESA / ACV), trade-in feeds, wholesale-buy
feeds, and DMS write-backs will need. **Extend the source
adapters; keep the upsert core.**

### §3.7 Recommended-actions engine (`services/pipeline.py`
`trends_snapshot` + `recommended_actions`)
Aggregates operational signals, produces prioritized suggestions.
Directly generalizes to: recon-recommended-actions (units
stalled in a stage), aging-recommended-actions (units crossing
threshold buckets), portfolio-recommended-actions (top-risk
accounts, PTP overdue, aging buckets).

### §3.8 Leads pipeline + salesperson / advisor system
5-stage lead pipeline, lead queue with urgency filters, lead
detail with transcript, lead assignment, advisor workspace,
follow-up drafts (with invented_appointment scrub). This is
the natural bridge point for the customer journey; new
non-chat lead sources plug into the same pipeline.

### §3.9 Dealer identity resolver (`services/dealer_config.py`)
DB (`DealerOnboardingProfile`) → env (`DEALER_AI_*`) → sensible
default. The right shape for per-vehicle overrides later
(e.g., "vendor for glass in Yuma"). Also the resolution
pattern that enables franchise-config to coexist with the
Copper Canyon indie default.

### §3.10 Dealer onboarding profile
Singleton `DealerOnboardingProfile` with 35 fields including the
SESSION_032 indie shape-of-business fields (`dealer_type`,
`bhph_enabled`, `subprime_lenders`, `floor_plan_lender`,
`warranty_offering`, `credit_range_served`, `makes_carried`).
The natural default source for ledger vendor selection, F&I
lender panel, BHPH policy toggles.

---

## 4. Milestone sequence

The order below is derived from three constraints:

- **Foundation-first.** Tenancy and auth land before any
  milestone that handles sensitive data (Investment ledger,
  F&I credit apps, BHPH customer data). The Vehicle-Centric
  Pivot names this as a Phase-0 blocker; SESSION_033's F&I
  and BHPH research reinforces it.
- **Standalone value.** The Investment Ledger is the smallest
  complete increment that produces standalone operator value
  (per VCP §"Sequenced to prove ROI on Phase 1 alone"). It
  ships early to prove the pattern.
- **Data-dependency order.** Recon Automation depends on
  Condition Reports; Photography / Listing depends on
  Lifecycle Stages; Operational Intelligence depends on real
  ledger + work-order data; Sale + Delivery depends on
  Lifecycle Stages.

The user's Scope Discipline rule sits on top of the whole
sequence: **complete the current milestone before opening the
next**.

Each milestone below identifies the fields the user's SESSION_034
brief requires — business objective, related research, existing
reusable, gap, recommended-order justification — plus a scope
boundary and the operational pain points the research names.

---

### Milestone 1 — Multi-tenant + role-based access foundation

**Business objective.** Enable multiple dealerships to use the
platform without data crossover. Enable role-based visibility
(owner sees investment ledger; porter does not; customer
never). Preserve every existing behavior contract while adding
the foundation for every sensitive-data milestone that follows.

**Related research.**
- `VEHICLE_CENTRIC_PIVOT.md` §"Technical debt to pay down
  FIRST" items 1 and 2; §"Structural changes required" items
  4 and 7.
- `FINANCE_DEPARTMENT_MAPPING.md` §"the paper app that a
  walk-in customer fills out at the desk is *the most
  sensitive document in the building*."
- `BHPH_OPERATIONS_MAPPING.md` §compliance — FDCPA / TCPA /
  GLBA / FCRA / state-specific collection laws.

**Operational pain resolved.** Not a direct pain-point
reducer; a compliance and safety foundation. Without it, every
subsequent milestone that stores credit data, ledger data, or
payment data ships a compliance and security debt the store
would rightly refuse.

**Existing reusable primitives.**
- §3.9 `dealer_config.py` resolver — will be the
  read-through mechanism for per-tenant configuration.
- §3.10 onboarding profile — becomes per-tenant instead of
  singleton.

**Gap.**
- Dealership entity (single row today, multi-row-ready
  tomorrow) — every operational entity added by later
  milestones carries a Dealership reference.
- Real authentication (framework's built-in is fine).
- Role-based permissions with at minimum these role classes
  named in research: `dealer_owner`, `sales_manager`,
  `recon_manager`, `f_and_i_manager`, `collections`,
  `advisor`, `porter`.
- Advisor workspace slug-by-obscurity replaced by real auth.

**Scope boundary.**
- In: tenancy model, real auth, role permissions, replacement
  of advisor-workspace slug obscurity.
- Out: user-facing settings / admin UI beyond the minimum
  needed to sign in; per-role UI polish (each subsequent
  milestone applies role scoping to its own surfaces); SSO;
  MFA (add later if research surfaces the need).

**Recommended order — first.** Blocks Milestones 2, 6, 10, 12,
and 13. The Vehicle-Centric Pivot names auth as
"[moved from] a 'Phase 5 debt' to a **Phase 0 blocker**"
because ledger data is more sensitive than any string the
existing scrub stack protects.

---

### Milestone 2 — Vehicle investment ledger

**Business objective.** For any stock number, answer two
questions: *"What do we have invested in this vehicle right
now?"* and *"What is the projected gross if we sell at the
current price?"* This is the single feature that is worth
selling standalone to another dealer tomorrow.

**Related research.**
- `INVENTORY_ACQUISITION_MAPPING.md` §"You make your money
  when you buy, not when you sell" (core philosophy).
- `INVENTORY_ACQUISITION_MAPPING.md` pain #4 (aged unit
  decision paralysis), #10 (floor plan monitoring), #17
  (over-/underbought scenarios and gross-visibility).
- `INVENTORY_ACQUISITION_MAPPING.md` §"Retail-to-Wholesale
  Spread = Recon + Gross + Overhead."
- `VEHICLE_CENTRIC_PIVOT.md` Phase 1.

**Operational pain resolved.**
- Buyers cannot easily answer "what have we spent on this
  piece" without pulling multiple invoices.
- Aged-unit decisions get deferred because gross-vs-carrying-
  cost math is hidden.
- Floor plan interest accrual is manual (or unknown) at
  many stores.
- Buyer estimate accuracy has no data trail (was my $800
  recon estimate on this unit a real $800?).

**Existing reusable primitives.**
- §3.5 Vehicle model — the identity primitive the ledger
  hangs off.
- §3.2 payment math — the same APR math computes daily
  floor-plan interest.
- §3.6 inventory import — the upsert / soft-unavailable
  pattern the auction-adapter refactor will preserve.
- §3.9 dealer_config resolver — extends to per-vehicle
  vendor / lender / rate overrides.
- §3.10 onboarding profile — `floor_plan_lender`,
  `warranty_offering`, etc. are the default sources for
  ledger entries.

**Gap.**
- Acquisition record (source classification: auction /
  trade / wholesale / private / off-lease / rental /
  repo / fleet; purchase price; fees; date).
- Per-vehicle cost ledger with ~25 line-item categories
  spanning acquisition / flooring / recon / admin (per VCP
  §"Investment ledger scope").
- Computed properties: total_investment, expected_gross,
  projected_gross, net profitability.
- Daily floor-plan interest accrual mechanism (manual
  re-run acceptable at first — async infra doesn't ship
  until Milestone 7).
- New post-LLM scrub: **acquisition-price scrub** — belt-
  and-suspenders against any ledger figure leaking to
  customer chat.

**Scope boundary.**
- In: cost basis capture, per-vehicle cost accumulation,
  computed gross properties, one operator UI surface to
  inspect a vehicle's ledger, acquisition-price scrub.
- Out: floor-plan-lender integration (manual entry ok for
  v1); auction-feed adapters (deferred; VCP §Phase 1 does
  not scope them); vendor negotiation workflows; trade
  appraisal workflow (belongs to Milestone 11 sales-side).

**Recommended order — second.** VCP names this as "the first
day the product is worth selling standalone to another
dealer." It also generates the data Milestone 4 (recon
automation), Milestone 8 (operational intelligence), and
Milestone 9 (sale + delivery gross reconciliation) need.

---

### Milestone 3 — Structured condition report

**Business objective.** Capture, in structured human-authored
form, what needs to happen before a vehicle is front-line
ready. Foundation for every downstream recon activity.

**Related research.**
- `RECON_MAPPING.md` §"the condition report is where recon
  quality begins. If the inspection missed a defect, recon
  can't plan for it."
- `RECON_MAPPING.md` §"Human-authored inspection discipline
  is non-negotiable."
- `RECON_MAPPING.md` pains #4 (inspection quality variance),
  #5 (jacket confusion), #6 (multiple techs on same vehicle).
- `VEHICLE_CENTRIC_PIVOT.md` Phase 2.

**Operational pain resolved.**
- Inspections vary in thoroughness; missed items become
  discovered work mid-recon (scope + timeline pain).
- Missing / unclear jackets waste labor as techs re-investigate.
- Multiple techs on the same vehicle duplicate or skip work.
- No structured record for warranty defense.

**Existing reusable primitives.**
- §3.5 Vehicle model — target of the report.

**Gap.**
- ConditionReport record (per-vehicle, timestamped, authored
  by a named human).
- ConditionFinding record (category from the VCP §"Categories
  the schema must support" list; severity from
  advisory / recommended / required / safety; description;
  optional cost estimate; optional photos).
- Multi-photo attachment per finding (introduces first real
  file-storage need beyond the single logo; addressed by
  Milestone 3's own scope OR deferred to a pre-Phase-2
  storage-story milestone at the user's option).
- Deliberate absence of AI: this milestone ships with **no
  LLM role at all** so the data shape gets proven before
  automation lands on top (per VCP: "AI role: NONE yet.
  Deliberately un-automated so the data shape gets proven
  before automation lands on top").

**Scope boundary.**
- In: report + finding entities, multi-photo upload,
  operator UI to author + view a condition report, file
  storage story sufficient for report photos.
- Out: AI-drafted recon plans (Milestone 4); vendor
  recommendations (Milestone 4); auto-mint of stage
  transitions from condition report (Milestone 5);
  historical-cost-informed cost estimates (Milestone 8).

**Recommended order — third.** No AI-drafted recon plan can
exist until this structured data shape does. VCP is explicit
that the AI role is zero in this phase.

---

### Milestone 4 — Recon automation (drafted, not authorized)

**Business objective.** Reduce the "chase vendor for status,
chase vendor for invoice, chase parts store for order" pain by
having the AI draft the artifacts that today require manual
composition — work orders, vendor emails, purchase orders,
work-order narratives — while humans retain approval and
sending authority.

**Related research.**
- `RECON_MAPPING.md` pains #1 (vendor turn-time unreliability),
  #7 (chasing vendors for status), #8 (chasing vendors for
  invoices), #11 (communication gaps with sales), #13 (vendor
  quality inconsistency).
- `RECON_MAPPING.md` §"What the AI IS allowed to do with
  condition data" (summarize, suggest vendors, draft parts
  orders / POs / vendor emails / vendor SMS, group findings,
  estimate cost).
- `RECON_MAPPING.md` §"What the AI is NEVER allowed to do"
  (invent findings, change severity, modify tech description,
  send anything without approval).
- `VEHICLE_CENTRIC_PIVOT.md` Phase 3.

**Operational pain resolved.**
- Recon coordinator's day spent calling vendors for status.
- Time from finding → PO → vendor dispatch is manual per
  step.
- Estimate → actual variance has no historical training
  data (Milestone 8 will close this loop; Milestone 4
  generates the data).

**Existing reusable primitives.**
- §3.3 ad_copy / follow_up drafting patterns — direct pattern
  reuse.
- §3.1 llm_safety — Day-1 dependency; the new artifacts pass
  through the same shared safety stack + a new
  **invented-recon-fact scrub** (per VCP: mirrors
  `invented_promotion`).
- §3.4 handoff-packet builder — the shape of an
  outbound-to-vendor work packet.
- §3.9 dealer_config resolver — per-dealer default vendor
  preferences.

**Gap.**
- Vendor record (name, categories, contact, active,
  avg_turn_days).
- WorkOrder record (vehicle FK, finding FK optional,
  category, vendor FK optional, status enum, estimated_cost,
  actual_cost, estimated_completion, actual_completion,
  notes). On `status=complete`, auto-mint a Milestone-2
  VehicleCost entry.
- AI drafting for work-order narratives, vendor emails,
  vendor SMS, purchase orders. All pass through the LLM
  safety stack and the new invented-recon-fact scrub.
- **Humans send everything.** AI drafts only.

**Scope boundary.**
- In: vendor entity, work-order entity, AI drafting for
  outbound artifacts with human approval gate, auto-mint
  on complete.
- Out: automated vendor SLA warnings (Milestone 7, needs
  async infra); historical vendor performance analytics
  (Milestone 8); vendor-portal integrations; vendor payment
  automation (belongs to accounting Track).

**Recommended order — fourth.** Depends on Milestone 3
(structured findings to draft against) and Milestone 2
(cost ledger to auto-mint into). VCP: "This is where the
pivot's promise — 'AI reduces repetitive work' — becomes
visible."

---

### Milestone 5 — Vehicle lifecycle stages + retail gating

**Business objective.** Distinguish "in inventory" from
"actually retail-eligible" at the data layer, so the retail
chat only surfaces vehicles that are truly front-line ready
and so aging can be tracked per stage.

**Related research.**
- `RECON_MAPPING.md` pain #12 (recon ETAs that don't match
  reality); Sales pain #4 (waiting on recon).
- `INVENTORY_ACQUISITION_MAPPING.md` §"Inventory
  categorization" (front-line ready, in recon, incoming,
  wholesale-out, company use, hold/reserved, off-market).
- `VEHICLE_CENTRIC_PIVOT.md` Phase 4 + §"Retail eligibility
  rule."

**Operational pain resolved.**
- Salespeople sometimes commit customers to vehicles that
  aren't actually retail-ready.
- Recon aging can't be measured per stage without stages.
- Sales team surprised by scope-change delays because there
  is no shared truth about the stage.

**Existing reusable primitives.**
- §3.5 Vehicle model — `is_available` boolean is the
  current (too-coarse) proxy; becomes a computed property
  returning `stage == 'frontline'`.
- Chat engine retrieval paths — the change to require
  `stage='frontline'` is one line with a test-suite ripple.

**Gap.**
- VehicleStage entity (1:1 with Vehicle, current stage,
  entered_at).
- VehicleStageEvent entity (audit trail with from_stage,
  to_stage, actor, trigger, notes).
- Deterministic stage-transition rules the VCP names
  (inspection → recon when a completed condition report has
  ≥1 recommended-or-higher finding; recon → qc when all
  required/safety work orders complete; photography → listing
  at photo threshold; listing → frontline when published +
  price > 0).
- Manual stage transitions with actor logging.
- Retail-eligibility change in the chat retrieval path.

**Scope boundary.**
- In: stage entity + event log + rule-driven suggestions
  with manual approval + retail-gating change.
- Out: aging-per-stage analytics (Milestone 8); async
  bottleneck warnings (Milestone 7); stage-specific
  role-scoped UIs (deferred; each subsequent milestone can
  add its own role-scoped view).

**Recommended order — fifth.** Depends on Milestones 2, 3, 4
to generate real lifecycle events. Order also matches VCP
Phase 4.

---

### Milestone 6 — Photography + listing generation

**Business objective.** Address the "photo management +
cross-platform listing maintenance" pain by giving vehicles a
structured photo gallery, generating listing copy with the
same drafting-with-scrub pattern already shipped, and
auto-advancing lifecycle stage on publish.

**Related research.**
- `INVENTORY_ACQUISITION_MAPPING.md` pains #8 (cross-platform
  listing maintenance) and #9 (photo management).
- `RECON_MAPPING.md` §photography and §listing prep.
- `VEHICLE_CENTRIC_PIVOT.md` Phase 5.

**Operational pain resolved.**
- 20–40 photos per vehicle, uploaded and reordered per
  platform, is hours of work per unit today.
- New unit listings and price changes are manually
  propagated across 4–6 platforms.
- Listing copy writing is another manual step per unit.

**Existing reusable primitives.**
- §3.3 ad_copy — the LLM drafting pattern for listings is
  the closest match to the ad-copy generator already
  shipped; direct reuse.
- §3.1 llm_safety — required for the listing-copy path.
- §3.5 Vehicle model — target for the photos and listing.

**Gap.**
- VehiclePhoto entity (order, alt_text, category, uploader,
  timestamp).
- Bulk photo upload / reorder UI.
- VehicleListing entity (headline, body, published,
  published_at, generated_by).
- AI listing-copy drafting pass-through.
- Listing-publish → auto-advance stage to 'listing'
  (Milestone 5 dependency).

**Scope boundary.**
- In: photo gallery + listing entity + AI copy drafting +
  stage auto-advance.
- Out: cross-platform syndication to AutoTrader / Cars.com
  / CarGurus / Facebook (deferred — vendor integration and
  contract each; the corpus names this pain but the pivot
  does not scope solving it in Phase 5).
- Out: listing analytics per platform (Milestone 8).

**Recommended order — sixth.** Depends on Milestone 5 for
the stage-advance semantics. Also unlocks a natural end-to-end
demo (acquisition → recon → photograph → list → front-line
→ chat matches it).

---

### Milestone 7 — Async infrastructure

**Business objective.** Support recurring background work
generated by earlier milestones — daily floor-plan interest
accrual, aging reports, vendor SLA warnings, photo processing,
BHPH payment reminder cadence, F&I stip aging alerts.

**Related research.**
- `VEHICLE_CENTRIC_PIVOT.md` Phase 6 explicitly and
  deliberately: *"Do not adopt Celery earlier. Nothing to
  run yet."*
- `INVENTORY_ACQUISITION_MAPPING.md` pain #10 (floor plan
  monitoring, manual).
- `RECON_MAPPING.md` pains #7 and #12 (status-chasing).
- `BHPH_OPERATIONS_MAPPING.md` pain #2 (reminder call
  fatigue).

**Operational pain resolved.**
- Interest accruals, aging warnings, SLA breaches are
  manually re-run today.
- Reminder cadences for BHPH and F&I are today either
  manual or non-existent.

**Existing reusable primitives.**
- None; greenfield infra.

**Gap.**
- Task queue + scheduler (framework-agnostic, but Django
  ecosystem defaults are Celery + Redis; VCP names both).
- Initial scheduled jobs: floor-plan-interest-accrual,
  aging-report-refresh, vendor-SLA-warning, photo-derived-
  work.
- Job observability (retries, failure alerts).

**Scope boundary.**
- In: task queue + scheduler + first four scheduled jobs
  named above + observability.
- Out: multi-worker autoscaling; complex workflow DAGs; UI
  for job status (log inspection acceptable for v1).

**Recommended order — seventh.** VCP is explicit that this
should not ship earlier — premature async infra is a
maintenance tax with nothing to run.

---

### Milestone 8 — Operational intelligence

**Business objective.** Answer the questions the corpus
explicitly names: which auctions produce the highest recon
costs, which vendors finish fastest, which vehicle types
produce the highest profit, which repairs are consistently
underestimated, aging trends per stage, gross-profit trends,
buyer estimate accuracy over time.

**Related research.**
- `VEHICLE_CENTRIC_PIVOT.md` §"Operational intelligence
  (long-term)" — the full list of questions the platform
  should answer post-Phases-1-7. "No ML required. These are
  SQL aggregations."
- `INVENTORY_ACQUISITION_MAPPING.md` §"To Ownership /
  Owner" outputs (gross performance per source, recon cost
  variance analytics, inventory turn, days-to-sale).
- `RECON_MAPPING.md` §"To Ownership" outputs (cost
  discipline, quality execution, turn-time discipline,
  warranty exposure alerts).
- `BHPH_OPERATIONS_MAPPING.md` §portfolio-level activities
  (delinquency %, rolling delinquency, cure rate, static-
  pool loss %, charge-off rate, recovery rate, portfolio
  yield, cash flow per account).

**Operational pain resolved.**
- Owners today assemble portfolio / inventory / recon /
  vendor / auction / gross reports manually from DMS
  extracts, or don't produce them at all.
- Estimate-vs-actual variance is invisible without
  aggregation, so buyer discipline is under-scrutinized.

**Existing reusable primitives.**
- §3.7 recommended-actions + trends_snapshot — the exact
  pattern for turning aggregations into prioritized
  operator suggestions.
- §3.1 llm_safety — any drafted summarization passes
  through.

**Gap.**
- Aggregation queries over the ledger (§Milestone 2),
  condition reports (§Milestone 3), work orders / vendor
  history (§Milestone 4), stage events (§Milestone 5),
  sales (§Milestone 9), portfolio activity (§Milestone 12).
- Operator dashboards per role (owner sees everything;
  role-scoped views for managers).
- Optional: LLM-drafted "read the dashboard for me"
  summaries, passed through the safety stack.

**Scope boundary.**
- In: SQL aggregations, operator dashboards, LLM
  summarizations passed through safety stack.
- Out: predictive ML (VCP explicitly rules this out for
  this milestone); external BI-tool exports.

**Recommended order — eighth.** Depends on Milestones 2-5 for
source data; Milestone 7 for scheduled refresh.

---

### Milestone 9 — Sale + delivery closure

**Business objective.** Close the loop between the vehicle
side and the customer side. When a Vehicle transitions to
sold, the CRM side of the record activates. Realized gross is
tied back to projected gross so the merchandising cycle can be
measured end-to-end.

**Related research.**
- `SALES_DEPARTMENT_MAPPING.md` §customer journey (deal →
  delivery → follow-up).
- `SALES_DEPARTMENT_MAPPING.md` §delivery workflow
  (checklist, temp tag, customer education, service intro).
- `VEHICLE_CENTRIC_PIVOT.md` Phase 8.

**Operational pain resolved.**
- Today the platform's Vehicle record does not know it has
  been sold. No projected-vs-realized-gross measurement is
  possible.
- Delivery preparation is uncoordinated (detail booked?
  fueled? temp tag? insurance? customer walkthrough?).
- LeadVehicleInterest has no annotation — no record of
  which lifecycle stage the vehicle was at when the customer
  became interested.

**Existing reusable primitives.**
- §3.8 leads pipeline + salesperson system — the customer
  journey is already partly built through the leads pipeline.
- §3.4 handoff-packet builder — pattern for delivery packet.
- §3.5 Vehicle model — target of the sold transition.

**Gap.**
- Sale record (buyer / vehicle / sale_date / sold_price /
  finance_type: cash / retail / BHPH / lender / gross_realized).
- Delivery record (sale FK / delivery_date / checklist JSON
  / temp_tag_number / insurance verification).
- LeadVehicleInterest through-model annotation (which stage
  when interest expressed).
- gross_realized computed against Milestone 2's total
  investment.

**Scope boundary.**
- In: sale + delivery entities, checklist tracking,
  realized-gross computation.
- Out: DMS write-back integrations; state e-filing
  integrations; sales-tax computation surface (belongs to
  Accounting track).

**Recommended order — ninth.** Depends on Milestone 2 for
gross-realized math and Milestone 5 for stage semantics. Also
closes the vehicle-operational side of the roadmap and creates
the natural bridge into Milestones 10 and 12.

---

### Milestone 10 — Finance (F&I) deal desk

**Business objective.** Support F&I workflow from customer
commit through funding. Reduce stip-chase pain, chargeback
reconciliation lag, and per-deal jacket incompleteness.

**Related research.**
- `FINANCE_DEPARTMENT_MAPPING.md` §workflow (credit-app
  intake → deal structure → lender submission → approval /
  counter → stips → contract → funding → post-funding
  chargebacks).
- `FINANCE_DEPARTMENT_MAPPING.md` §"Every step in the
  process serves one of those two questions: Will a lender
  approve this customer on this vehicle at terms that work?
  Can the deal be delivered clean?"
- `FINANCE_DEPARTMENT_MAPPING.md` pains #1 (duplicate data
  entry across DMS + Route One + lender portals + title +
  insurance + deal jacket + commission), #4 (stip creep),
  #6 (holding multiple lender programs in memory), #7
  (tracking 15–40 open deals with various stip states),
  #9 (chargeback exposure lag).
- `FINANCE_DEPARTMENT_MAPPING.md` §compliance (retention 2–7
  years; adverse-action; privacy; safeguards; red flags).

**Operational pain resolved.**
- Customer credit data re-entered across ≥7 systems today.
- Stips tracked in F&I manager's head across dozens of open
  deals.
- Chargebacks flow back weeks after delivery with no
  systematic reconciliation surface.

**Existing reusable primitives.**
- §3.2 payment math — deal structure math (LTV, PTI, DTI,
  affordable_max_price already exists).
- §3.1 llm_safety — required for any customer-facing
  drafted output.
- §3.4 handoff-packet builder — pattern for funding packet.
- §3.10 onboarding profile — `subprime_lenders` /
  `credit_range_served` shape the lender panel.
- Milestone 1 auth — required (customer credit data is the
  most sensitive doc in the building).

**Gap.**
- Credit application entity with legal retention discipline.
- Deal structure entity (LTV, PTI, DTI computation).
- Lender submission tracking (per-lender-per-deal state).
- Stipulation package tracking.
- RISC + product-agreement records.
- Funding packet assembly + funding-status monitoring.
- Chargeback record and downstream reversal to commission.
- Per-deal compliance record and retention clock.

**Scope boundary.**
- In: entities + workflow states + drafting for customer
  explanations + funding-status surface + chargeback
  reconciliation.
- Out: direct lender-portal integrations (belongs to a
  future vendor-integration milestone); e-contracting
  provider integration; automated bureau pull integration
  (belongs to a future compliance-heavy milestone).

**Recommended order — tenth.** Depends on Milestone 1 (auth)
before any credit-app data can be stored. Depends on
Milestone 9 (sale record) for chargeback → commission-reversal
plumbing.

---

### Milestone 11 — Sales-side non-chat channels + customer-journey completeness

**Business objective.** Extend the leads pipeline beyond
chat-originated leads to cover the walk-in, phone, listing-
platform-form, and referral channels the sales research names.
Add the customer-journey artifacts the chat channel does not
produce today (test-drive record, deal write-up, follow-up
cadence orchestration, referral capture, be-back scheduling).

**Related research.**
- `SALES_DEPARTMENT_MAPPING.md` §lead acquisition (channel
  mix percentages).
- `SALES_DEPARTMENT_MAPPING.md` §workflow (all 16 steps
  from lead acquisition through be-back management).
- `SALES_DEPARTMENT_MAPPING.md` pains #1 (following up
  consistently), #2 (forgetting callbacks), #3 (poor CRM
  notes), #13 (managing multiple communication channels),
  #15 (be-back promises), #16 (working leads across
  shifts).

**Operational pain resolved.**
- Today's lead system only captures chat-originated leads.
  Walk-ins, phone calls, listing-platform inquiries, and
  referrals sit outside the platform.
- Follow-up drafts exist but no cadence orchestration
  scheduling.
- Be-back tracking absent.

**Existing reusable primitives.**
- §3.8 leads pipeline + salesperson system — the target
  extension surface.
- §3.3 follow_up — the drafting pattern; scheduling is the
  new part.
- §3.4 handoff-packet builder — pattern for sales → F&I
  handoff memo (see Milestone 10).
- Milestone 7 async infra — required for scheduled cadence.

**Gap.**
- Multi-channel lead intake (form endpoints for walk-in
  capture, phone log, listing-platform webhooks, referral
  registration).
- Test-drive / demonstration record.
- Deal write-up entity (four-square-style summary tied to
  the F&I handoff memo).
- Follow-up cadence orchestration (24hr / 1wk / 30day /
  90day / 6mo / 1yr) with role-scoped assignment.
- Be-back tracking + scheduled re-contact.
- Referral capture + attribution.

**Scope boundary.**
- In: multi-channel intake + test-drive record + deal
  write-up + cadence orchestration + be-back + referral.
- Out: listing-platform outbound syndication (belongs to
  Milestone 6 or a dedicated integrations milestone);
  advertising-spend analytics; CSI survey integration.

**Recommended order — eleventh.** Depends on Milestone 7
(async) for cadence orchestration. Sequenced after the
vehicle-operational track so the operator has real
front-line inventory to attach the leads to.

---

### Milestone 12 — BHPH portfolio operations (v1)

**Business objective.** For dealers with `bhph_enabled=True`,
manage the in-house lending business after the deal funds —
payment intake, delinquency detection, collection contact
logging, promise-to-pay tracking, repossession coordination,
portfolio-level owner reporting.

**Related research.**
- `BHPH_OPERATIONS_MAPPING.md` §workflow (origination →
  payment cadence → delinquency → collections → default →
  repo → post-repo disposition).
- `BHPH_OPERATIONS_MAPPING.md` §"You make your money over
  time, not at the sale."
- `BHPH_OPERATIONS_MAPPING.md` pains #1 (daily payment
  posting volume), #2 (reminder call fatigue), #3 (payment
  method chaos), #4 (PTP tracking), #7 (repo coordination),
  #10 (portfolio reporting for owner).
- `BHPH_OPERATIONS_MAPPING.md` §portfolio-level activities
  (delinquency buckets, cure rate, static-pool loss,
  charge-off, portfolio yield).

**Operational pain resolved.**
- Daily payment posting takes hours across mixed methods.
- Reminder-call cadence is manual + fatiguing.
- PTP tracking is spreadsheet-native and error-prone.
- Owner portfolio reporting is manually assembled weekly
  (some daily).

**Existing reusable primitives.**
- §3.2 payment math BHPH variant — the weekly / biweekly
  math is already shipped for deal writeup; extends to
  payment-schedule generation and payoff computation.
- §3.10 onboarding profile — `bhph_enabled`,
  `subprime_lenders` shape the surface's activation.
- §3.7 recommended-actions — the pattern for
  top-risk-accounts + PTP-overdue + aging-bucket summaries.
- §3.3 follow_up — drafting pattern for reminder / late /
  hardship messages, passed through indie-prohibited-copy
  scrub.
- §3.1 llm_safety — indie-prohibited-copy scrub is already
  shipped; extends naturally to BHPH-specific prohibited
  language (deficiency threats, harassment-adjacent phrasing).
- Milestone 1 auth — required (customer PII + payment data).

**Gap.**
- BHPH note entity + payment schedule.
- Payment record + application logic (fees → interest →
  principal).
- Delinquency detection + escalation-bucket tagging.
- Promise-to-pay record + follow-up scheduling.
- Collection contact log with FDCPA-compliant
  documentation.
- Repossession record (order → agent → recovery →
  inventory intake).
- Portfolio aging + static-pool reporting.
- New post-LLM scrub: **collection-language scrub**
  (belt-and-suspenders against FDCPA-adjacent drafted
  messaging).

**Scope boundary.**
- In: v1 — payment intake, payment ledger, delinquency
  buckets, PTP tracking, collection contact log,
  repossession record entry, portfolio aging + owner
  dashboard.
- Out (deferred to a v2 BHPH milestone): GPS / starter-
  interrupt device integration, skip-tracing service
  integration, credit-bureau reporting, static-pool
  cohort analysis, repo agent dispatch integration,
  automated deficiency judgment paperwork. These are
  each named in research and worth building but exceed
  a "small complete increment."

**Recommended order — twelfth.** Depends on Milestone 1
(auth), Milestone 7 (async for cadence + aging refresh),
Milestone 9 (Sale record to attach the note to), and
Milestone 10 (F&I → BHPH handoff at contract signing when
the dealer is the lender).

---

### Milestone 13 — Accounting reconciliation core

**Business objective.** Establish the ledger truth layer.
Every operational event on the platform → matching accounting
entry. Reduce DMS-bypass pain, control-account mismatch, and
unapplied-cash friction the corpus names.

**Related research.**
- `ACCOUNTING_DEPARTMENT_MAPPING.md` §"Accounting is the
  reconciliation layer that validates every operational
  event."
- `ACCOUNTING_DEPARTMENT_MAPPING.md` §"When the DMS is
  right, accounting is right."
- `ACCOUNTING_DEPARTMENT_MAPPING.md` pains #1 (three-way
  reconciliation without POs), #2 (chasing funding), #3
  (chasing titles), #4 (reconciling vendor payments), #7
  (duplicate data entry across ≥7 systems), #8 (unapplied
  cash), #9 (schedule to control-account reconciliation),
  #10 ("the schedule is off").

**Operational pain resolved.**
- Vendor invoices approved outside the platform bypass the
  DMS → control-account drift.
- Cash receipts posted in one system, tied to deals in
  another → unapplied cash accumulates.
- Titles arrive without automatic linkage to inventory.
- Floor plan schedule reconciliation is spreadsheet-heavy.

**Existing reusable primitives.**
- §3.5 Vehicle model — target for per-vehicle cost
  accumulation (already leveraged by Milestone 2).
- Milestones 2 (ledger), 4 (work orders), 9 (sale), 10
  (F&I), 12 (BHPH) — each already produces the operational
  records this milestone reconciles.
- §3.1 llm_safety — required if any customer-facing or
  vendor-facing accounting output is LLM-drafted.

**Gap.**
- Deal booking record (F&I deal → GL posting).
- Vendor invoice → approval → check / ACH → GL journal chain.
- Bank reconciliation (statement + feed → GL).
- Contracts-in-transit schedule (funding-pending deals).
- Floor plan reconciliation (schedule vs. lender statement).
- Title arrival + aging + storage tracking.
- Reserve receivable + product commission receivable
  schedules.
- Monthly close + trial balance + adjusting entries
  workflow.
- Financial statement generation (P&L, balance sheet, cash
  flow).
- Sales tax filing surface.

**Scope boundary.**
- **This milestone is deliberately structured to be
  incremental** — a single monolithic "accounting"
  milestone would violate Scope Discipline. In practice
  this milestone is a *series of smaller milestones layered
  onto Milestones 2, 4, 9, 10, 12* as those surfaces ship.
  Each accounting slice adds the reconciliation layer for
  the operational surface it accompanies.
- In (as prerequisite for other milestones): per-vehicle
  cost accumulation (Milestone 2 already delivers this);
  simple bank-reconciliation entry for funding deposits
  (Milestone 10 adjacency); deal-booking flow (Milestone 10
  adjacency).
- Out: payroll (external service handles); W-2 / 1099
  generation (external service); year-end tax return
  preparation (external CPA); GAAP-compliant audited
  financial reporting (out of scope for platform v1).

**Recommended order — thirteenth as a coherent whole; but
should be layered onto earlier milestones incrementally.**
Wait to build the full close-and-financial-statement surface
until the operational milestones have generated enough activity
for a monthly close to be meaningful. When in doubt during any
earlier milestone, ask: does this operational event produce a
financial journal entry someone needs to see at month-end? If
yes, that accounting slice belongs to *that* milestone.

---

## 5. Explicit non-goals and deferrals

The following are documented in research but explicitly out of
scope for the current roadmap. Each is deferred (per the
Discovery Rule — deferred, never discarded).

**Deferred from earlier pivots (still valid):**
- Real inventory-feed integrations (auction API adapters:
  Manheim / ADESA / ACV / etc.). Scoped in
  `INVENTORY_ACQUISITION_MAPPING.md` §vendor interactions;
  deferred by VCP §"Non-goals."
- Bilingual UI. Deferred by `INDEPENDENT_DEALER_PIVOT.md`
  §"Non-goals."
- Payment processing / e-sign / DMS write-back. Deferred by
  `INDEPENDENT_DEALER_PIVOT.md` §"Non-goals."
- Multi-tenant SaaS shell (billing / org). The Milestone 1
  tenancy model is FK-carrier tenancy, not full SaaS.
- Franchise-specific default paths. Franchise remains a
  supported configuration; only default path stays indie
  (per SESSION_030+031).

**Deferred from SESSION_033 research (add to future
milestones as evidence surfaces):**
- Cross-platform listing syndication (AutoTrader / Cars.com /
  CarGurus / Facebook / Craigslist). Milestone 6 covers
  listing generation but not outbound syndication.
- Direct lender-portal integrations (Route One / Dealertrack /
  per-lender portals). Milestone 10 assumes manual portal
  operation.
- GPS / starter-interrupt device integration. Milestone 12
  v1 excludes.
- Skip-tracing service integration (Accurint / TLO /
  LocatePlus). Milestone 12 v1 excludes.
- Credit-bureau reporting (Metro 2 furnisher). Milestone 12
  v1 excludes.
- Static-pool cohort analysis. Milestone 12 v1 excludes.
- Automated deficiency judgment paperwork. Milestone 12 v1
  excludes.
- E-contracting provider integration. Milestone 10 excludes.
- Automated bureau pull integration. Milestone 10 excludes.
- Payroll + 1099 / W-2 generation. Milestone 13 excludes
  (external service).
- GAAP-audited financial reporting. Milestone 13 excludes.
- Predictive ML on operational data. Milestone 8 explicitly
  rules out ("no ML required; SQL aggregations").
- Multi-worker autoscaling / complex workflow DAGs.
  Milestone 7 excludes.
- SSO / MFA on top of Milestone 1 auth. Not currently
  research-motivated.

**Not deferrals but architectural notes:**
- Prod deployment (`CAPABILITY_MATRIX.md` §honest gaps: Render
  Blueprint staged but not activated). Recon/ledger is
  worthless if the operator can't reach it from the lot on
  a phone. This is not a milestone in itself; it is a
  prerequisite that must be scheduled alongside any
  milestone whose consumers are field-based.
- `docs/DEFERRED_IDEAS.md` should be created the first time
  a session generates a deferred idea that does not fit
  neatly into any milestone plan doc. Per
  `docs/PROJECT_RULES.md` §Discovery Rule.

---

## 6. Scope-discipline verification (self-check)

Per SESSION_034 brief Step 5, every milestone was checked
against two questions:

1. **Which documented business problem does this solve?**
2. **Is solving this required to complete the current
   implementation milestone?**

Verification per milestone:

| Milestone | Q1 answer (research citation) | Q2 answer |
|-----------|------------------------------|-----------|
| 1 Auth foundation | Compliance requirement for every subsequent milestone that stores credit / ledger / payment data (Finance §compliance, BHPH §compliance) | Yes — foundation for M2, M6, M10, M12, M13 |
| 2 Investment ledger | Inventory §"You make your money when you buy"; pains #4 #10 #17 | Yes — first standalone-valuable milestone per VCP |
| 3 Condition report | Recon §"foundation of everything downstream"; pain #4 | Yes — prerequisite for M4 |
| 4 Recon automation | Recon pains #1 #7 #8 #11 #13 | Yes — depends on M3 |
| 5 Lifecycle + retail gating | Recon pain #12; Sales pain #4; Inventory §categorization | Yes — depends on M2/M3/M4 lifecycle events existing |
| 6 Photography + listing | Inventory pains #8 #9; Recon §listing prep | Yes — depends on M5 for stage-auto-advance |
| 7 Async infra | Deferred per VCP until real work to schedule exists (M1-M6 generate real work) | Yes — enables M8, M11, M12 |
| 8 Operational intelligence | VCP §operational intelligence; Inventory §"To Ownership"; Recon §"To Ownership"; BHPH §portfolio-level | Yes — depends on M2-M5 source data |
| 9 Sale + delivery | Sales §delivery workflow; VCP Phase 8 | Yes — closes vehicle-operational side |
| 10 F&I deal desk | Finance §workflow; pains #1 #4 #6 #7 #9; compliance | Yes — depends on M1 auth |
| 11 Sales non-chat channels | Sales §lead acquisition (5 channels); pains #1 #2 #3 #13 #15 #16 | Yes — depends on M7 async |
| 12 BHPH portfolio v1 | BHPH §workflow; pains #1 #2 #3 #4 #7 #10 | Yes — depends on M1/M7/M9/M10 |
| 13 Accounting reconciliation | Accounting §workflow; pains #1 #2 #3 #4 #7 #8 #9 #10 | Yes — layered onto M2/M4/M9/M10/M12 |

**No milestone traces to technology interest.** Every milestone
traces to at least one named operational pain or documented
business need.

**No milestone silently expands scope.** Where scope
temptations exist (e.g. Milestone 6 auto-syndication;
Milestone 10 e-contracting; Milestone 12 GPS integration),
those are explicitly deferred in Section 5.

**No milestone rebuilds existing capability.** Each cites at
least one of the eight primitives in Section 3, or documents
why the surface is genuinely greenfield (Milestones 1, 3, 7,
13 have honest greenfield notes).

**Two roadmap-level tensions were noted and preserved for a
future session's decision:**
- Milestone 3 introduces the first real multi-photo storage
  need. The user may choose to address storage as a
  half-milestone before Milestone 3 or absorb it into M3's
  scope.
- Milestone 13 is deliberately structured as an incremental
  overlay rather than a monolithic milestone. If a future
  session decides accounting is easier to reason about as a
  discrete phase, that structural decision can be revisited.

---

## 7. Anchors that win on conflict

If this roadmap disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win. This roadmap is
   the implementation contract; the rules are the
   governance layer above it.
2. `docs/research/*_MAPPING.md` — the research wins. This
   roadmap synthesizes research into milestones; the
   research is the primary source of business truth.
3. `docs/BUSINESS_DOMAIN_MAP.md` — the domain map wins on
   business-shape questions.
4. `docs/CAPABILITY_MATRIX.md` — the capability matrix wins
   on "what does the software actually do today?" questions.
5. Any future handoff that adjusts a milestone's scope with
   explicit user approval — the handoff wins for that
   milestone.

Roadmaps are claims. Research + code + rules are facts.

---

## 8. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference
  (produced same session).
- `docs/CAPABILITY_MATRIX.md` — what the software does today.
- `docs/PROJECT_PIPELINE.md` — runtime flow map of the
  existing chat + safety pipeline.
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` — architectural
  plan on which Milestones 1-9 are built.
- `docs/research/INDEPENDENT_DEALER_PIVOT.md` — persona /
  scope pivot on which the whole platform sits.
- `docs/research/*_MAPPING.md` — the six primary research
  docs.
- `docs/handoffs/SESSION_034_*.md` — the handoff that
  captures this roadmap's shipping.

---

*End of Implementation Roadmap.*
