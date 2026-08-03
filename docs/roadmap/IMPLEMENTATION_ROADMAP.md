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
| Acquisition record (source, purchase price, fees, purchase date) | F | §3.5 Vehicle model + `services/vehicle_ledger.py` | Milestone 2 (SESSION_046+). `VehicleAcquisition` OneToOne with Vehicle; 8-value source enum; `record_acquisition` upsert. See `CAPABILITY_MATRIX.md` §7c. |
| Per-vehicle cost basis + running investment total | F | §3.5 Vehicle model + `services/vehicle_ledger.py` | Milestone 2 (SESSION_046+). `VehicleCost` immutable rows across 26 categories (flooring/recon/admin/photography); `compute_totals` deterministic. Actual vs. estimated semantic contract locked. See `CAPABILITY_MATRIX.md` §7c. |
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
| Per-vehicle cost accumulation | F | §3.5 Vehicle model + `services/vehicle_ledger.py` | Milestone 2 (SESSION_046+). `VehicleCost` + `LedgerTotals` computed. Vendor entity remains N (deferred to Milestone 4). See `CAPABILITY_MATRIX.md` §7c. |
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
| Chat-engine safety pipeline (chat/message + vehicles/<id>/ask) | F | §3.1 + §3.2 | 8-stage pre-LLM chain + 8-stage post-LLM scrubs; 1466 tests |
| Multi-tenancy (Dealership FK-carrier model) | F | §3.9 dealer_config resolver (extended) | Milestone 1 (SESSION_037–044). `Dealership` model + `dealership` FK on all six tenant carriers + `NOT NULL` at the DB layer + `pre_save` autofill safety net + request-context resolver. See `CAPABILITY_MATRIX.md` §7b. |
| Real authentication + role-based permissions | F | §3.9 dealer_config + `services/tenancy.py` + `dealer_ai/permissions.py` | Milestone 1 (SESSION_037–044). DRF `SessionAuthentication` + `TokenAuthentication`; seven-role vocabulary via `UserDealershipRole`; per-endpoint permission classes for advisor + admin surfaces; browser session flow. See `CAPABILITY_MATRIX.md` §7b and `docs/roadmap/AUTHENTICATION_MODEL.md`. |
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
- **Multi-tenancy + real auth shipped (Milestone 1, SESSION_044).**
  Every subsequent milestone that stores sensitive data (ledger,
  credit apps, BHPH payments) now inherits the substrate — no more
  "foundations must land first" caveat.

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

**Recommended order — first. Shipped SESSION_037 → SESSION_044.**
Six sub-increments (4A–4F within the tenancy + auth + admin +
frontend split). Full planning artifact at
`docs/roadmap/MILESTONE_1_PLANNING.md`; retrospective at
`docs/roadmap/MILESTONE_1_RETROSPECTIVE.md`.

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

**Recommended order — second. Shipped SESSION_046 → SESSION_054.**
Eight sub-increments (M2.1 models · M2.2 service · M2.3 read
model · M2.4a financial engine + APR config · M2.4b accrual
command · M2.5 acquisition-price scrub · M2.6 admin API · M2.7
operator UI · M2.8 verification + closeout). Full planning
artifact at `docs/roadmap/MILESTONE_2_PLANNING.md`;
retrospective at `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md`.
Test baseline: 1,466 → 1,753 pass (+287); 1 skipped, 0 fail;
zero regressions. VCP's "first day the product is worth selling
standalone to another dealer" now delivers: an operator can
enter an $18,500 auction buy + $475 buyer fees + $850 transport
+ $125 title and see *"$19,475 in it; asking $24,900; projected
gross $5,425"* on the operator ledger page.

---

### Milestone 3 — Structured condition report — SHIPPED at SESSION_064

*Full delivery record: `docs/roadmap/MILESTONE_3_PLANNING.md` §7
(annotated SHIPPED per increment) and
`docs/roadmap/MILESTONE_3_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7d. Test baseline
delta: 1,753 → 2,124 (+371, zero regressions). Sessions
055 → 064. Frontend `tsc --noEmit` + `vite build` clean.*

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

### Milestone 4 — Recon automation — SHIPPED at SESSION_073

*Full delivery record: `docs/roadmap/MILESTONE_4_PLANNING.md`
§7 (annotated SHIPPED per increment) and
`docs/roadmap/MILESTONE_4_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7e. Test baseline
delta: 2,124 → 2,518 (+394, zero regressions). Sessions
065 → 073. M4.8 (outbound SMTP / SMS send) deferred per
planning §5.i / §5.j pending real pilot-store engagement.
Frontend `tsc --noEmit` + `vite build` clean.*

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

### Milestone 5 — Vehicle lifecycle stages + retail gating — SHIPPED at SESSION_081

*Full delivery record: `docs/roadmap/MILESTONE_5_PLANNING.md`
§7 (annotated SHIPPED per increment; §0.a change-log
lists the 10 refinements landed inside increments) and
`docs/roadmap/MILESTONE_5_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7f.
Test baseline delta: 2,518 → 2,754 (+236 tests, zero
regressions). Sessions 074 → 081. Frontend `tsc
--noEmit` + `vite build` clean. `sold` stage deferred
entirely to M9 (no enum constant, no stub).*

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

### Milestone 6 — Photography + listing generation — SHIPPED at SESSION_087

*Full delivery record: `docs/roadmap/MILESTONE_6_PLANNING.md`
§7 (annotated SHIPPED per increment; zero §0.a change-log
amendments required) and
`docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7g.
Test baseline delta: 2,754 → 2,948 (+194 tests, zero
regressions). Sessions 082 → 087. Frontend `tsc
--noEmit` + `vite build` clean. Cross-platform
syndication (Facebook / AutoTrader / Cars.com /
CarGurus) explicitly out-of-scope per §5.e — publish =
local `/showroom/vehicles/<stock_number>/` only.
Milestone 11+ owns vendor integrations.*

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

### Milestone 7 — Async infrastructure — SHIPPED at SESSION_093

*Full delivery record: `docs/roadmap/MILESTONE_7_PLANNING.md`
§7 (annotated SHIPPED per increment; zero §0.a change-log
amendments required) and
`docs/roadmap/MILESTONE_7_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7h.
Test baseline delta: 2,948 → 3,150 (+202 tests, zero
regressions). Sessions 088 → 093. Frontend `tsc
--noEmit` + `vite build` clean (unchanged — M7 shipped
no frontend). Four scheduled job families at hourly
cadence 02:00 – 05:00 project-time (floor-plan accrual /
aging snapshot / vendor SLA warnings / photo tombstone
reaper). BHPH reminder cadence deferred to Milestone
12; multi-worker autoscaling + complex workflow DAGs +
notification channels + job-history UI explicitly out-
of-scope per M7 planning §1.*

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

### Milestone 8 — Operational intelligence — SHIPPED at SESSION_099

*Full delivery record: `docs/roadmap/MILESTONE_8_PLANNING.md`
§7 (annotated SHIPPED per increment; two §0.a change-log
amendments required — Q7 deferral at M8.2 open and Q1
reallocation + Q3 proxy at M8.4 open, both substrate-gap
discoveries surfaced at session open) and
`docs/roadmap/MILESTONE_8_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7i.
Backend test baseline delta: 3,150 → 3,274 (+124 tests,
zero regressions). Frontend Vitest baseline established
from scratch at M8.5: 19 pass (new — project had zero
frontend tests before M8.5). Sessions 094 → 099. Six
operational-intelligence aggregations shipped (Q1 + Q2 +
Q4 + Q5 + Q9 + Q10) plus two proxies (Q3 for vehicle-
type recon cost + Q8 for days-at-frontline) pending M9
Sale substrate. One materialized model (`SlaBreachRecord`)
+ M7.4 verb-extension. Six DRF endpoints under
`/api/dealer-ai/admin/analytics/`. One operator UI at
`/dealer-ai-analytics/` with four tabs + recharts +
first frontend test infra in the project's history
(Vitest + @testing-library/react + jsdom). Q6 (gross-
profit trend) + Q7 (buyer estimate accuracy) deferred to
Milestone 9 pending Sale + acquisition-buyer-provenance
substrate. `AnalyticsCache` materialization deferred per
§5.a Option C hybrid pending operator latency evidence.
No predictive ML per VCP; no external BI exports per
planning §1.0.*

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

### Milestone 9 — Sale + delivery closure — SHIPPED at SESSION_105

*Full delivery record: `docs/roadmap/MILESTONE_9_PLANNING.md`
§7 (annotated SHIPPED per increment; five §0.a
change-log amendments recorded — one for the M9.1
combined-migration sequencing decision, one for the
M9.2 Delivery-OneToOne interpretation clarification,
one for the M9.3 implementation notes, one for the
M9.4 `LeadVehicleInterest` annotation deferral
substrate-gap, one for the M9.5 UI decisions + GET
dispatch substrate-gap) and
`docs/roadmap/MILESTONE_9_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md`
§7j. Backend test baseline delta: 3,274 → 3,426
(+152 tests, zero regressions). Frontend Vitest
baseline: 19 → 34 (+15). Sessions 100 → 105. Two
new entities (Sale + Delivery) with mandatory
OneToOne (Delivery.sale). Two new services packages
(`services/sale/` + `services/delivery/`). Four
"true" analytics verbs closing M8 deferrals — Q3
(`vehicle_type_profitability`), Q6
(`gross_profit_trend`), Q7 (`buyer_estimate_accuracy`),
Q8 (`inventory_turn`). Seven new DRF endpoints (one
M9.1 Sale + two M9.2 Delivery + three M9.3 + one
M9.4). Fifth analytics tab **Realized Gross** + new
per-vehicle `dealer-ai-inventory/:stock/sale/` page.
GET dispatch added additively to M9.1 + M9.2 write
URLs via `@api_view(["GET", "POST"])` method-multiplex
(URL names preserved). Migrations `0023` +
`0024`. Tenancy carriers 22 → 24 (+`Sale`,
+`Delivery`). `VehicleAcquisition.buyer` FK
(nullable) shipped alongside M9.1 as the M2
substrate Q7 reads. `LeadVehicleInterest.stage_at_interest`
annotation deferred per §0.a SESSION_103
substrate-gap (through-model doesn't exist).
Sale/Delivery cross-vehicle list views + dense
gross-profit series + `AnalyticsCache`
materialization all deferred pending operator
evidence. No DMS / e-filing / sales-tax /
BHPH / F&I work per planning §scope-boundary
non-goals.*

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

### Milestone 10 — Finance (F&I) deal desk — SHIPPED at SESSION_113

*Full delivery record: `docs/roadmap/MILESTONE_10_PLANNING.md`
§7 (annotated SHIPPED per increment; seven §0.a change-log
amendments recorded — one per implementation session
SESSION_106 → SESSION_112, each capturing the decisions
resolved at that session's open) and
`docs/roadmap/MILESTONE_10_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7k. Backend test
baseline delta: 3,426 → 3,730 (+304 tests, zero regressions).
Frontend Vitest baseline: 34 → 51 (+17). Sessions 106 → 113.
Ten new entities (CreditApplication, DealStructure,
LenderProgram, LenderSubmission, Stipulation, Contract,
BackEndProductAgreement, Funding, Chargeback, ComplianceRecord)
plus three additive extensions (CA gross_monthly_income +
existing_monthly_debt at M10.2; BEPA cancelled_at +
cancellation_amount at M10.6; Stipulation evidence_url + BEPA
product_agreement_url at M10.7). One complete new services
package (`services/f_and_i/` with seven submodules —
credit_application, deal_structure, lender, stipulation,
contract, funding, chargeback, compliance). One new
permission class
(`IsFinanceManagerOrOwnerAtActiveDealership` at M10.1 —
reused unchanged M10.2-M10.7; zero permission-class drift
across the F&I surface). Seventeen new DRF admin endpoints
(one M10.1, one M10.2, three M10.3, two M10.4, five M10.5,
one M10.6, four M10.7). Migrations `0025`–`0031`. Tenancy
carriers 24 → 34 (+10). First F&I frontend surface at M10.7
— `/dealer-ai-f-and-i/` two-tab MVP per §1.8.d Option A
(deals-in-progress list + per-deal compliance-audit view).
Twenty-nine load-bearing decisions resolved across seven
implementation sessions, **all confirmed as-recommended by
the user** (streak-pattern signal per retrospective §6
lesson 16). Photo/document upload plumbing deferred through
M10.4/M10.5/M10.7 as a discrete post-M10 initiative if
operator evidence demands. Full 7-step F&I operator UI +
server-side pagination on deals list + `resync_retention`
verb + bureau-response integration all deferred pending
operator evidence. No DMS / lender-portal / BHPH / accounting
work per planning §scope-boundary non-goals.*

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

### Milestone 11 — Sales-side non-chat channels + customer-journey completeness — SHIPPED at SESSION_120

*Full delivery record: `docs/roadmap/MILESTONE_11_PLANNING.md`
§7 (annotated SHIPPED per increment; five §0.a change-log
amendments recorded — M11.1 open plus per-session amendments at
M11.3 / M11.4 / M11.5 / M11.6 open) and
`docs/roadmap/MILESTONE_11_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7l. Backend test
baseline delta: 3,730 → 3,895 (+165 tests, zero regressions).
Frontend Vitest baseline: 51 → 67 (+16). Sessions 114 → 120.
Five new entities (TestDrive, DealWriteup, FollowUpCadence,
FollowUpTask, BeBack) plus one additive extension (CustomerLead
gains `channel` CharField with 5+1 vocab + backfill + `referrer`
self-FK at M11.1 via migration `0032`). Five new services
packages (`services/leads/` M11.1 — with adapter-registry sub-
package; `services/test_drives/` M11.2; `services/deal_writeups/`
M11.3; `services/follow_ups/` M11.4 — with Celery-beat surfacer;
`services/be_backs/` M11.5 — with Celery-beat detector).
**Zero new permission classes** — every M11 endpoint reused
`IsSalesManagerOrOwnerAtActiveDealership` (M4). Sixteen new DRF
admin endpoints (M11.1 +4 lead intake; M11.2 +1 test-drive create;
M11.3 +3 deal writeup; M11.4 +5 cadence / task; M11.5 +3 be-back;
M11.6 +2 list endpoints for the operator UI). One new frontend
route family (`/dealer-ai-sales/*`) with four MVP pages at M11.6
per §5.f Option C (extended UI at follow-on; DealWriteup UI
deferred to M12+). Migrations `0032`–`0036`. Tenancy carriers
34 → 39. Celery-beat task families 4 → 6 (M11.4 06:00 surfacer +
M11.5 07:00 detector). **Six planning-time §5 decisions
confirmed as-recommended at M11.1 open** (streak stands at 35
planning-time as-recommended M5.1 → M11.1). **Twelve
implementation-time micro-decisions** recorded in §0.a across
M11.3-M11.6 opens per M11.3 / M11.4 / M11.5 / M11.6 amendments
(not counted against the streak per M10 §9). DealWriteup + F&I
handoff UI + delivery adapters (SMS/email) + operator-configurable
cadence templates + auto-skip on stale tasks + auto-cadence-on-
BeBack integration + `reopen_task` verb + named-platform webhook
adapters all deferred pending operator evidence. No modification
of M1-M10 business logic; M1 chat funnel + M10.1 CreditApplication
retention lock both preserved byte-for-byte.*

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

### Milestone 12 — BHPH portfolio operations (v1) — SHIPPED at SESSION_128

*Full delivery record: `docs/roadmap/MILESTONE_12_PLANNING.md`
§7 (annotated SHIPPED per increment; five §0.a change-log
amendments recorded — M12.1 open plus per-session amendments at
M12.3 / M12.4 / M12.5 / M12.6 / M12.7 open) and
`docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7m. Backend test
baseline delta: 3,895 → 4,150 (+255 tests, zero regressions).
Frontend Vitest baseline: 67 → 78 (+11). Sessions 121 → 128.
Five new entities (BhphNote, BhphPayment, BhphPromiseToPay,
CollectionContact, Repossession) plus one additive extension
(BhphNote gains `current_bucket` + `days_past_due` at M12.3 via
migration `0039`). Seven new services packages (`bhph_notes` /
`bhph_payments` / `bhph_delinquency` / `bhph_promises` /
`collection_contacts` / `repossessions` / `bhph_analytics`).
Two new Celery-beat task families (M12.3 aging detector at 08:00
+ M12.4 broken-PTP detector at 09:00). One new post-LLM scrub
stage (`collection_language` under `kind="collection_contact"`).
One new `/dealer-ai-bhph/` frontend route family with two MVP
pages (portfolio dashboard + per-note detail); collection-contact
create UI + repo-order create UI deferred per §5.f Option C.
Migrations `0037`–`0042`. Tenancy carrier 39 → 44 (+5). DRF
admin surface 82 → 98 (+16 endpoints). Frontend operator routes
15 → 17. Permission classes unchanged at 8 across seven M12
implementation increments. **Six §5 decisions confirmed as-
recommended at M12.1 open** — streak stands at 41 planning-time
as-recommended M5.1 → M12.1 across three consecutive milestones.*

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

### Milestone 13 — Accounting reconciliation core (v1) — SHIPPED at SESSION_132

*Full delivery record: `docs/roadmap/MILESTONE_13_PLANNING.md`
§7 (annotated SHIPPED per increment; two §0.a change-log
amendments recorded — M13.0 open plus per-session amendments at
M13.2 / M13.3 open) and
`docs/roadmap/MILESTONE_13_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7n. Backend test
baseline delta: 4,150 → 4,240 (+90 tests, zero regressions).
Frontend Vitest baseline: 78 (unchanged — no frontend at M13
per §5.f Option C). Sessions 129 → 132. Three new entities
(GLAccount, JournalEntry, JournalEntryLine) plus one additive
extension (VehicleCost gains `posted_at` at M13.2 via migration
`0044`). One new services package (`accounting`) with four
modules (`default_coa` + `journal` + `vehicle_cost` +
`snapshot`). One new Celery-beat task family (M13.2 vehicle-
cost posting at 10:00). Zero new post-LLM scrub stages (M13
substrate is entirely deterministic double-entry math; no LLM
path introduced). Zero new frontend routes (backend-only per
§5.f Option C). Migrations `0043`–`0044`. Tenancy carrier 44 →
47 (+3). DRF admin surface 98 → 102 (+4 endpoints: three
journal-entry + one trial-balance). Frontend operator routes
17 (unchanged). Permission classes unchanged at 8 across three
M13 implementation increments — extends zero-drift posture to
five consecutive milestones (M10 + M11 + M12 + M13).
**Milestone deliberately incremental** per this section's
scope-boundary note: M13 ships substrate + Q1 (M2 cost
reconciliation) + trial-balance aggregator; remaining eight
business questions (M9 sale-booking GL post, M10 F&I
chargeback GL reversal, M12 BHPH payment GL post, M4 vendor
invoice → A/P reconciliation, title-arrival tracking, floor-
plan reconciliation, contracts-in-transit, monthly close +
adjusting entries) layer onto M14+ or into ongoing
operational milestones as those surfaces ship. **Six §5
decisions confirmed as-recommended at M13.0 open** — streak
extends to 47 planning-time as-recommended M5.1 → M13.0 across
four consecutive milestones (M10 + M11 + M12 + M13).*

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

### Milestone 14 — Operator UI for accounting substrate — SHIPPED at SESSION_138

*Full delivery record: `docs/roadmap/MILESTONE_14_PLANNING.md`
§7 (annotated SHIPPED per increment; four §0.a change-log
amendments recorded across M14.1 + M14.2 + M14.3 + M14.4
implementation sessions) and
`docs/roadmap/MILESTONE_14_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7o. Backend test
baseline delta: 4,240 → 4,277 (+37 tests, zero regressions).
Frontend Vitest baseline delta: 78 → 122 (+44 tests, zero
regressions). Sessions 133 → 138. Zero new backend entities.
Two additive sibling verbs in `services/accounting/` (M14.1
`list_journal_entries` in `journal.py` +
`detect_cost_posting_failures` in `vehicle_cost.py`) — both
consumed by the M14.2–M14.4 UI. One new frontend API client
module (`accountingApi.ts`) with four fetchers + one mutator.
Three new frontend pages (`AccountingTrialBalancePage` +
`AccountingJournalEntriesPage` +
`AccountingJournalEntryDetailPage`). Three new operator routes
under a new `dealer-ai-accounting/*` group. One shadcn
`<Dialog>` wired for reversal (modal, not a route). Zero
migrations. Zero permission-class drift — extends zero-drift
posture to six consecutive milestones (M10 + M11 + M12 + M13 +
M14). Zero new Celery-beat task families (M14 is entirely
read-only + one operator-intent write path that reuses M13.1
substrate). Zero new post-LLM scrub stages (M14 has no LLM
path). DRF admin surface 102 → 104 (+2 endpoints: journal-
entry list + cost-posting failures). Frontend operator routes
17 → 20 (+3). Tenancy carrier 47 (unchanged — no new models).
**Six §5 decisions confirmed as-recommended at M14.0 open** —
streak extends to 53 planning-time as-recommended M5.1 → M14.0
across five consecutive milestones (M10 + M11 + M12 + M13 +
M14). Thirty-one §0.a implementation-time micro-decisions
across M14.1 (7) + M14.2 (7) + M14.3 (8) + M14.4 (9) — do not
count against the streak per M10 §9.*

**Business objective.** Make the M13 accounting reconciliation
core operator-usable. Trial-balance render + journal-entry
browser + reversal-with-reason dialog + cost-posting failure
surfacing — all four UI surfaces named in the M13 retrospective
§3 item 4 shipped as a single milestone.

**Related research.**
- `ACCOUNTING_DEPARTMENT_MAPPING.md` §"Accounting is the
  reconciliation layer that validates every operational
  event" — the operator side of that reconciliation is
  what M14 surfaces.
- `MILESTONE_13_RETROSPECTIVE.md` §3 item 4 (operator UI
  deferred per §5.f Option C) + §8 (M13 unblocked-work
  list) — M14 is the "Option D" pick from that list.

**Operational pain resolved.**
- The M13 substrate is unreachable without `manage.py shell`
  or raw curl — accounting operators can't visually confirm
  trial-balance state or audit-trail journal-entry postings.
- Cost-posting failures from the M13.2 detector are logged
  but not surfaced — operators discover them only by seeing
  M2 costs stay unposted for days, then hunting through logs.
- Mis-posted journal entries require a `manage.py shell`
  call to `reverse_journal_entry` — inaccessible to non-
  engineers.

**Existing reusable primitives.**
- All four M13 admin endpoints (three M13.1 journal-entry +
  one M13.3 trial-balance) — the frontend consumes them
  unchanged.
- M13.1 `reverse_journal_entry` service verb + endpoint —
  the M14.4 reversal dialog routes through this without
  modification.
- M12 BHPH portfolio page pattern (`useEffect` +
  cancellation flag + shadcn `<Card>` + `<Table>` +
  `<Badge>`) — the M14 pages mirror this posture.
- `authGetJSON` / `authPostJSON` from
  `frontend/src/lib/authFetch.ts` — the M14 API client
  module funnels through the shared operator fetch
  primitive.
- `RequireAuth` route wrapper — every M14 route inherits
  the M1 authentication gate.

**Gap.**
- Frontend accounting surface (M14 fills this).
- Journal-entry list endpoint (M14.1 fills this).
- Cost-posting failure surfacer endpoint (M14.1 fills this).

**Scope (six increments).**
- **M14.0** — planning refinement + target selection.
- **M14.1** — backend list + failure endpoints (2 pure
  query verbs + 2 admin endpoints).
- **M14.2** — frontend trial-balance render page + new
  `accountingApi.ts` module.
- **M14.3** — frontend journal-entry browser + detail page.
- **M14.4** — frontend reversal dialog + cost-posting
  failure card.
- **M14.5** — close-out docs.

**Out of scope for M14** (deferrals cataloged in
`MILESTONE_14_RETROSPECTIVE.md` §3):
- Journal-entry list filters; `as_of` picker on trial-
  balance; manual create UI; sidebar nav entry; date-picker
  widget on reversal `posted_at`; category-group-aware GL
  mapping.
- M9 sale-booking GL post; M10 F&I chargeback GL reversal;
  M12 BHPH payment GL post (substrate-consuming write-path
  milestones; the M14 UI will surface any resulting
  journal entries automatically once these ship).
- `TrialBalanceSnapshot` materialization + monthly close
  workflow; period-comparison verbs; CSV export.
- Per-dealer COA overrides UI; `post_save` COA seeder wiring.

### Milestone 15 — M9 sale-booking GL post — SHIPPED at SESSION_141

*Full delivery record: `docs/roadmap/MILESTONE_15_PLANNING.md`
§7 (annotated SHIPPED per increment; one §0.a change-log
amendment recorded across M15.1 implementation session) and
`docs/roadmap/MILESTONE_15_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7p. Backend test
baseline delta: 4,277 → 4,296 (+19 tests, zero regressions).
Frontend Vitest baseline: 122 (unchanged — no frontend at M15
per §5.f Option A). Sessions 139 → 141. Zero new backend
entities. One new module in `services/accounting/`
(`sale_booking.py`) with one atomic sibling-service verb
(`post_sale_booking_journal`) + `_lookup_required_account` +
`_resolve_receivable_account` helpers + `UnmappedFinanceTypeError`
+ six account-code constants + finance-type → receivable
mapping table. Extended `services/sale/computation.record_sale`
with `posted_by_user` kwarg + per-vehicle un-posted-cost flush
loop + sibling call to `post_sale_booking_journal`. Extended
`views_sale.admin_sale_create` for `request.user` propagation.
Extended `tests/_auth_helpers.make_dealership` to seed default
COA on creation. Zero migrations. Zero new endpoints — sale-
booking is a side effect of M9's existing create endpoint.
Zero permission-class drift — extends zero-drift posture to
seven consecutive milestones (M10 + M11 + M12 + M13 + M14 +
M15). Zero new Celery-beat task families (sale booking is
operator intent per M13 §5.d Option C hybrid — not detector-
shaped). Zero new post-LLM scrub stages (M15 has no LLM
path). DRF admin surface 104 (unchanged). Frontend operator
routes 20 (unchanged — no frontend touched). Tenancy carrier
47 (unchanged — no new models). **Six §5 decisions confirmed
as-recommended at M15.0 open** — streak extends to 58 planning-
time as-recommended M5.1 → M15.0 across six consecutive
milestones (M10 + M11 + M12 + M13 + M14 + M15). Nine §0.a
implementation-time micro-decisions across M15.1 — do not
count against the streak per M10 §9.*

**Business objective.** Wire the M9 sale write path to the
M13 accounting substrate. Every sold vehicle produces a
matching balanced JournalEntry automatically. Real accounting
workflows now reflect the full retail operation, not just M2
cost accrual + reversal.

**Related research.**
- `ACCOUNTING_DEPARTMENT_MAPPING.md` §3.5 (Contracts in
  Transit + funding workflow) — M15 posts the sale-side
  half (DR CIT at booking); the funding-side half (DR Cash
  / CR CIT at funding) defers to a payments-inbound
  milestone.
- `MILESTONE_13_PLANNING.md` §5.d Option C hybrid
  (sync sibling for M9 sale-booking, detector for M2 cost
  accrual + M12 BHPH payment posting) — M15 exercises the
  sync half.
- `MILESTONE_13_RETROSPECTIVE.md` §8 + `MILESTONE_14_RETROSPECTIVE.md`
  §8 — both flagged M9 sale-booking GL post as the M14
  substrate-consuming target. M15 picks it up.

**Operational pain resolved.**
- Before M15, trial balance reflected only M2 cost accrual
  activity (Recon WIP + A/P Trade). Revenue + COGS accounts
  showed zero regardless of sales volume.
- Before M15, the M14.3 journal-entry browser showed only
  M13.2 cost-accrual entries — invisible to operators
  looking for sale audit trails.
- Before M15, Recon WIP grew unboundedly — every M13.2
  posting added; nothing cleared. Balance was meaningless
  after 30 days.
- Before M15, receivables (Cash / CIT / BHPH Notes) were
  never posted from the sale side — the accounting
  department had no ledger record of what the sales team
  had actually closed.

**Existing reusable primitives.**
- M13.1 `services/accounting/post_journal_entry` — the
  atomic sibling target for M15's sale-booking verb.
  Consumed unchanged.
- M13.2 `services/accounting/post_vehicle_cost_journal` —
  invoked per un-posted VehicleCost row for the sold
  vehicle at sale time per §5.d Option A. Consumed
  unchanged.
- M13.2 `_lookup_required_account` — mirrored verbatim in
  the sale-booking module for account resolution (not
  promoted to shared helper — evidence gate for refactor
  not tripped).
- Default COA seeded per Dealership by M13.1 migration
  `0043` — all six accounts M15 uses (100000 / 120000 /
  122000 / 123000 / 400000 / 500000) exist for every
  tenant.
- M9 `services/sale/record_sale` — the write path extended
  with `posted_by_user` kwarg + cost-flush loop + sibling
  call. Already `@transaction.atomic`; the sibling calls
  inherit that transaction.
- M14.3 journal-entry browser + M14.2 trial-balance page —
  the UI surface that surfaces M15's new entries
  automatically. Zero frontend changes needed.
- `IsSalesManagerOrOwnerAtActiveDealership` (via composed
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`) —
  the permission class on M9's existing create endpoint.
  Reused — zero-drift streak extends to seven consecutive
  milestones.

**Gap.**
- Wire `record_sale` to `post_journal_entry` (M15.1 fills
  this).
- Finance-type → receivable account mapping (M15.1 fills
  this — §5.b Option A three-way branch).
- Per-vehicle un-posted-cost flush at sale time (M15.1
  fills this — §5.d Option A keeps trial balance always
  internally consistent).

**Scope (three increments).**
- **M15.0** — planning refinement + target selection.
- **M15.1** — backend sale-booking GL post (new sibling
  module + `record_sale` extension + view `posted_by_user`
  propagation).
- **M15.2** — close-out docs.

**Out of scope for M15** (deferrals cataloged in
`MILESTONE_15_RETROSPECTIVE.md` §3):
- Sales-tax posting; trade-in accounting; F&I product
  revenue at sale; doc-fee revenue; reserve receivable at
  sale; BHPH interest income accrual; wholesale sale
  variant; sale-reversal workflow; JournalEntry ⇄ Sale FK
  linkage; Contracts-in-Transit funding workflow; cost-of-
  sale variance handling; GL-derived reporting analytics.
- M10 F&I chargeback GL reversal + M12 BHPH payment GL
  post — substrate ready per M13 §5.d Option C hybrid;
  M15 demonstrated the sync-sibling pattern that M10
  chargeback would follow; the M14 UI will surface any
  resulting journal entries automatically once these ship.
- Payroll / W-2 / 1099 (external services). GAAP-audited
  financial reporting (out of scope for platform v1).
  Direct DMS integration (belongs to a future vendor-
  integration milestone).

---

### Milestone 16 — M12 BHPH payment GL post — SHIPPED at SESSION_144

*Full delivery record: `docs/roadmap/MILESTONE_16_PLANNING.md`
§7 (annotated SHIPPED per increment; one §0.a change-log
amendment recorded across M16.1 implementation session) and
`docs/roadmap/MILESTONE_16_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7q. Backend test
baseline delta: 4,296 → 4,326 (+30 tests, zero regressions —
top of the 25-30 planning target). Frontend Vitest baseline:
122 (unchanged — no frontend at M16 per §5.f Option A).
Sessions 142 → 144. Zero new backend entities. One additive
migration (`0045` — `BhphPayment.posted_at` denormalization
column for detector idempotency). One new module in
`services/accounting/` (`bhph_payment.py` — sixth module
alongside `default_coa.py`, `journal.py`, `snapshot.py`,
`vehicle_cost.py`, `sale_booking.py`) with three verbs
(`detect_unposted_bhph_payments` pure query +
`post_bhph_payment_journal` atomic sibling +
`post_all_unposted_bhph_payments_for_dealership`
orchestrator) + `UnexpectedBhphPaymentFeesError` broken-
invariant guard + three account-code constants + local
`_lookup_required_account` helper (duplicated from M13.2 per
M15.1 §0.a decision 3 posture). Extended
`services/accounting/tasks.py` with two `@instrumented_task`
functions (`post_bhph_payment_journals_for_dealership` per-
tenant + `post_bhph_payment_journals_for_all_tenants`
orchestrator) + two task-name constants. New
`accounting-bhph-payment-post-daily-11-00` beat entry in
`dealer_kit/settings.py::CELERY_BEAT_SCHEDULE` at
`crontab(hour=11, minute=0)` — tenth beat family, next open
non-overlapping slot after M13.2's 10:00. Extended
`services/accounting/__init__.py` `__all__` for the new
verbs + constant + error class. Zero new endpoints —
detector is Celery-scheduled, not operator-visible. Zero
permission-class drift — extends zero-drift posture to eight
consecutive milestones (M10 + M11 + M12 + M13 + M14 + M15 +
M16). Celery-beat task families 9 → 10 (one added at
M16.1). Zero new post-LLM scrub stages (M16 has no LLM
path). DRF admin surface 104 (unchanged). Frontend operator
routes 20 (unchanged — no frontend touched). Tenancy carrier
47 (unchanged — BhphPayment gained a column, not a new
model). **Six §5 decisions confirmed as-recommended at
M16.0 open** — streak extends to 64 planning-time as-
recommended M5.1 → M16.0 across seven consecutive milestones
(M10 + M11 + M12 + M13 + M14 + M15 + M16). Five §0.a
implementation-time micro-decisions across M16.1 — do not
count against the streak per M10 §9.*

**Business objective.** Wire the M12 BhphPayment write path
to the M13 accounting substrate via a detector-shaped
Celery-beat job. Every unposted BhphPayment produces a
matching balanced JournalEntry automatically. The BHPH loan
portfolio now amortizes visibly at the GL level (Notes
Receivable decreases as principal is collected); interest
income accrues cash-basis; aggregate cash-collected reaches
the GL.

**Related research.**
- `BHPH_OPERATIONS_MAPPING.md` §3 (payment operations),
  §3.10 (daily payment posting rhythm), §11.5 (BHPH ↔
  accounting dependencies) — the operational rhythm
  motivates the daily detector cadence.
- `ACCOUNTING_DEPARTMENT_MAPPING.md` §1.1 (chart of
  accounts — 100000 / 123000 / 430000) — the three
  accounts M16 posts against were already defined in the
  M13.1 default COA fixture.
- `MILESTONE_13_PLANNING.md` §5.d Option C hybrid
  (sync sibling for M9 sale-booking, detector for M2 cost
  accrual + M12 BHPH payment posting) — M16 exercises the
  detector half of the hybrid (M15 exercised the sync
  half).
- `MILESTONE_15_RETROSPECTIVE.md` §8 — flagged M12 BHPH
  payment GL post as the M16 target. M16 picks it up.

**Operational pain resolved.**
- Before M16, trial balance reflected M13.2 cost accrual +
  M15 sale-booking activity, but zero BHPH payment
  amortization. 123000 BHPH Notes Receivable grew
  monotonically with each BHPH sale and never decreased,
  regardless of how many payments the operator collected.
- Before M16, the M14.3 journal-entry browser showed no
  BHPH-payment entries — invisible to operators looking for
  payment-side audit trails.
- Before M16, 430000 BHPH Interest Income showed zero
  balance regardless of collection activity. The single
  most operationally important BHPH revenue metric was
  absent from the ledger.
- Before M16, aggregate cash-collected from BHPH payments
  had no GL representation. Operator ran the BHPH ops UI
  in one window and the accounting UI in another; the two
  never reconciled at the ledger level.

**Existing reusable primitives.**
- M13.1 `services/accounting/post_journal_entry` — the
  atomic sibling target for M16's payment-posting verb.
  Consumed unchanged.
- M13.2 `services/accounting/vehicle_cost.py` — the
  template for M16.1's module shape (`detect_unposted_*` +
  `post_*_journal` + `post_all_unposted_*_for_dealership`).
  Mirrored near-verbatim.
- M13.2 `services/accounting/tasks.py` — the template for
  M16.1's Celery task pair. Extended with two new
  `@instrumented_task` functions.
- M13.2 `CELERY_BEAT_SCHEDULE` pattern (02:00–10:00 non-
  overlapping window) — M16.1 extends by one hour with an
  11:00 entry.
- M13.2 `_lookup_required_account` — mirrored verbatim in
  the BHPH-payment module for account resolution per
  M15.1 §0.a decision 3 (evidence gate for refactor not
  tripped).
- M15.1 account-code declaration pattern — local constants
  per module, `__init__.py` re-exports from canonical
  origin. `bhph_payment.py` re-declares
  `CASH_ACCOUNT_CODE` + `BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE`
  locally (duplicates `sale_booking.py`); declares new
  `BHPH_INTEREST_INCOME_ACCOUNT_CODE`.
- Default COA seeded per Dealership by M13.1 migration
  `0043` — all three accounts M16 uses (100000 / 123000 /
  430000) exist for every tenant.
- M12.2 `services/bhph_payments/record_payment` — the
  write path that produces the rows M16.1 posts.
  Consumed unchanged (BhphPayment gained a nullable
  `posted_at` column; existing callers unaffected).
- M14.3 journal-entry browser + M14.2 trial-balance page
  — the UI surface that surfaces M16's new entries
  automatically. Zero frontend changes needed.
- `_auth_helpers.make_dealership` — already seeds default
  COA per M15.1 §0.a decision 8. Every M16.1 test uses
  the helper for tenant setup.

**Gap.**
- Wire `BhphPayment` rows to `post_journal_entry` via a
  daily detector (M16.1 fills this).
- Cash-side account mapping (M16.1 fills this — §5.c
  Option A uniform DR 100000).
- Line composition for zero-amount split columns (M16.1
  fills this — §5.e Option A skip-zero pattern produces
  2- or 3-line entries).
- Detector idempotency signal (M16.1 fills this — §5.d
  Option A `BhphPayment.posted_at` column mirroring
  M13.2's `VehicleCost.posted_at` verbatim).

**Scope (three increments).**
- **M16.0** — planning refinement + target selection.
- **M16.1** — backend BHPH payment GL detector (new
  sibling module + migration + Celery tasks + beat
  entry).
- **M16.2** — close-out docs.

**Out of scope for M16** (deferrals cataloged in
`MILESTONE_16_RETROSPECTIVE.md` §3):
- Method-aware fund-flow routing; late fee GL posting;
  NSF / payment-reversal handling; GL-derived BHPH
  analytics; BHPH interest accrual detector (accrual-
  basis); deposit / bank reconciliation workflow;
  JournalEntry ⇄ BhphPayment FK linkage; charge-off GL
  wiring; payment modification / deferral GL; cross-run
  detector concurrency guard beyond Celery-beat single-
  dispatcher assumption; repossession-inventory transfer
  GL.
- M10 F&I chargeback GL reversal + trial-balance
  materialization / monthly close workflow + category-
  group-aware GL mapping for M13.2 detector + M14 UX
  polish + cost-of-sale variance handling + sale-
  reversal workflow — all remain unblocked as M17+
  candidates; substrate ready for each.
- Payroll / W-2 / 1099 (external services). GAAP-audited
  financial reporting (out of scope for platform v1).
  Direct DMS integration (belongs to a future vendor-
  integration milestone).

---

### Milestone 17 — Trial-balance materialization + as_of picker (monthly-close v1) — SHIPPED at SESSION_145

*Full delivery record: `docs/roadmap/MILESTONE_17_PLANNING.md`
§7 (annotated SHIPPED per increment; four §0.a change-log
amendments recorded across M17.1 + M17.2 implementation
sessions) and
`docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`. Shipped surface
enumerated in `docs/CAPABILITY_MATRIX.md` §7r. Backend test
baseline delta: 4,326 → 4,363 (+37 tests, zero regressions —
in the 30-40 planning target range). Frontend Vitest baseline
delta: 122 → 140 (+18 tests, exceeded 8-16 target by 2 due to
the picker-helpers test file). Sessions: 145 (all four
increments collapsed to one calendar session per user
direction "continue" after each landed; commits `404605e`
M17.0 + `f217e0d` M17.1 backend + `bedc615` M17.1 docs +
`4235137` M17.2 frontend + `dc064cf` M17.2 docs + this
close-out commit). Two new backend entities
(`TrialBalanceSnapshot` header + `TrialBalanceSnapshotRow`
child; tenancy carriers 47 → 49). One additive migration
(`0046` — two `CreateModel` + two `AddConstraint`; zero data
migration). One new module in `services/accounting/`
(`trial_balance_close.py` — seventh module alongside
`default_coa.py`, `journal.py`, `snapshot.py`,
`vehicle_cost.py`, `sale_booking.py`, `bhph_payment.py`) with
three verbs (`freeze_trial_balance` atomic sync-sibling +
`list_trial_balance_snapshots` paginated per M14.1 pattern +
`get_trial_balance_snapshot` tenant-scoped retrieve) + new
`DuplicateTrialBalanceSnapshotError` domain exception (409
mapping) + `TrialBalanceSnapshotListPage` frozen dataclass.
Internal rename `TrialBalanceSnapshot` → `TrialBalanceComputation`
+ `TrialBalanceRow` → `TrialBalanceComputationRow` in
`snapshot.py` frees the "snapshot" name for the durable
Django model (§0.a M17.1 decision 1). Three new endpoints in
`views_accounting.py` (POST freeze + GET list at
`/snapshots/list/` + GET detail at `/snapshots/<int:pk>/`) —
DRF admin surface 104 → 107. All three reuse
`IsSalesManagerOrOwnerAtActiveDealership` — zero-drift streak
extends to nine consecutive milestones (M10 + M11 + M12 +
M13 + M14 + M15 + M16 + M17.1 + M17.2). Frontend: `frontend/
src/lib/accountingApi.ts` extended with `fetchTrialBalance(asOf?)`
+ three new fetchers/mutators + four TypeScript types.
`frontend/src/components/accounting/TrialBalanceDatePicker.tsx`
— new component wrapping `<input type="date">` in the shadcn
`Input` primitive (§0.a M17.2 micro-decision: native browser
primitive over shadcn `Calendar` install). `frontend/src/
pages/AccountingTrialBalancePage.tsx` extended in place with
Query controls card (picker + Freeze button + inline banners)
+ Prior closes card (paginated snapshot list) + inline
`FrozenSnapshotDetailCard` on row click. Frontend operator
routes 20 (unchanged — page extends in place per §4 test
binding). Celery-beat task families 10 (unchanged — no beat
entry at M17 per §5.c Option A sync-sibling shape). Zero new
post-LLM scrub stages (M17 has no LLM path). AI safety stack
17 scrub stages (unchanged). **Six §5 decisions confirmed
as-recommended at M17.0 open** — streak extends to 70
planning-time as-recommended M5.1 → M17.0 across eight
consecutive milestones (M10 + M11 + M12 + M13 + M14 + M15 +
M16 + M17). Four §0.a implementation-time micro-decisions
across M17.1 + M17.2 — do not count against the streak per
M10 §9.*

**Business objective.** Wire a durable materialization layer
on top of the M13.3 live trial-balance aggregator + give
operators the UI to query historical dates and freeze
period-close snapshots. **The smallest complete operator-
usable slice of monthly-close workflow** per §5.a Option E
bundling: without the picker, the materialization has no
operator consumer; without the materialization, the picker
has nothing durable to record. Together they answer "what
did the trial balance look like on May 31, and can I ensure
that answer stays stable even if backdated corrections land
later?"

**Related research.**
- `ACCOUNTING_DEPARTMENT_MAPPING.md` §1.1 (chart of accounts
  — no additions at M17; all M17 activity is over the
  M13.1-seeded default COA), §2.4 (period-close operational
  rhythm) — motivates the "close of business" end-of-day
  semantics for the picker per §5.e Option B.
- `MILESTONE_13_PLANNING.md` §5 M13.3 — the pure recompute
  aggregator that M17 preserves + materialization layer bolts
  on top of.
- `MILESTONE_14_PLANNING.md` §3 deferral 2 (M14.2 `as_of`
  picker deferred to a monthly-close slice) — that slice is
  M17.
- `MILESTONE_15_RETROSPECTIVE.md` §6 (M15.1 sync-sibling
  template) + §8 — M17.1's freeze verb mirrors the sync-
  sibling posture verbatim.
- `MILESTONE_16_RETROSPECTIVE.md` §6 (six lessons carry into
  M17) + §8 — flagged trial-balance materialization as an
  unblocked M17 candidate. M17 picks it up.

**Operational pain resolved.**
- Before M17, `compute_trial_balance(as_of=X)` recomputed
  every call. A backdated JournalEntry with `posted_at <= X`
  silently changed the historical trial balance. The
  reported May close on June 1 was not the same as the
  reported May close on June 15 if any backdated entry
  landed in between.
- Before M17, the frontend `fetchTrialBalance()` sent no
  `as_of` param — the M13.3 endpoint's `?as_of=` query
  parameter was on the wire but had no operator UI. Operators
  could only query "now."
- Before M17, no entity recorded prior period closes; no
  endpoint listed them. Operators wanting to compare "May
  close" against "June close" had no durable record of
  either.

**Existing reusable primitives.**
- M13.3 `services/accounting/compute_trial_balance` — pure
  recompute aggregator, unchanged. The new freeze verb
  calls it internally.
- M13.3 GET `/admin/accounting/trial-balance/[?as_of=]`
  endpoint — the query parameter was on the wire since M13.3
  §0.a decision 4; M17.2 starts sending it from the picker.
- M15.1 `services/accounting/sale_booking` — pattern
  template for the M17.1 sync-sibling freeze verb (atomic
  posture, module shape, verb signature).
- M14.1 `list_journal_entries` paginated verb — pattern
  template for M17.1 `list_trial_balance_snapshots`
  (frozen dataclass return shape, pagination bounds, tenancy
  isolation).
- M13.1 `IsSalesManagerOrOwnerAtActiveDealership` — reused
  for all three M17.1 endpoints (zero-drift streak nine
  consecutive milestones).
- M14.2 `AccountingTrialBalancePage.tsx` — extended in place
  at M17.2 with new picker + freeze button + Prior closes
  card + inline detail.
- shadcn `Input` primitive — wrapped as the picker's
  underlying `<input type="date">` per §0.a M17.2 (native
  browser primitive over shadcn `Calendar`).
- `_auth_helpers.make_dealership` already seeds default COA
  per M15.1 §0.a decision 8 — all M17.1 tests using the
  helper have the required substrate.

**Gap.**
- Durable persistence layer for period-close snapshots
  (M17.1 fills this — `TrialBalanceSnapshot` header +
  `TrialBalanceSnapshotRow` child).
- Operator UI to pick historical `as_of` moments + freeze
  snapshots + browse prior closes (M17.2 fills this — date
  picker + Freeze button + Prior closes card + inline
  detail).
- Uniqueness guard against double-freeze (M17.1 fills this
  — `unique_together=(dealership, as_of)` + `IntegrityError`
  → `DuplicateTrialBalanceSnapshotError` → 409).
- Immutability of frozen rows against backdated JournalEntry
  changes (M17.1 fills this — per-account rows materialized
  via `bulk_create` at freeze time; live aggregator + frozen
  rows are independent per §5.f Option A).

**Scope (four increments — first mixed backend+frontend
milestone since M14; all four collapsed to SESSION_145 per
user direction).**
- **M17.0** — planning refinement + target selection.
- **M17.1** — backend TrialBalanceSnapshot entity + freeze
  verb + three endpoints.
- **M17.2** — frontend as_of picker + Freeze button + Prior
  closes list + inline detail.
- **M17.3** — close-out docs.

**Out of scope for M17** (deferrals cataloged in
`MILESTONE_17_RETROSPECTIVE.md` §3):
- Backdated-entry discrepancy surface; auto-freeze on
  schedule; reopen / unfreeze workflow; period comparison
  view; CSV / PDF export; time-of-day picker; tenant timezone
  configuration; future-date freezing guard; snapshot-source
  FK on downstream audit entities; DB-level immutability
  enforcement; materialized aggregate reports (P&L, balance
  sheet); snapshot detail versioning through COA renames.
- M10 F&I chargeback GL reversal + category-group-aware GL
  mapping for M13.2 detector + M14 UX polish (JE filters +
  sidebar nav; `as_of` picker portion now shipped at M17.2)
  + cost-of-sale variance handling + sale-reversal workflow
  + NSF / payment-reversal workflow + BhphFee entity +
  BHPH interest accrual detector + deposit / bank
  reconciliation workflow + method-aware fund-flow routing
  — all remain unblocked as M18+ candidates; substrate ready
  for each.
- Payroll / W-2 / 1099 (external services). GAAP-audited
  financial reporting (out of scope for platform v1).
  Direct DMS integration (belongs to a future vendor-
  integration milestone).

---

### Milestone 18 — Demo Store Simulation + Pilot Validation Readiness — SHIPPED at SESSION_152

*Full delivery record:
`docs/roadmap/MILESTONE_18_PLANNING.md` §7 (annotated
SHIPPED per increment; five §0.a change-log amendments
recorded across M18.1 + M18.2 implementation sessions) and
`docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7s.
Backend test baseline delta: 4,363 → 4,538 (+175 tests
across all M18 increments, zero regressions). Frontend
Vitest baseline: 140 (unchanged — feedback capture form
deferred per §5.f evidence gate). Sessions: 146 → 152
(seven increments including planning + close-out; commits
`469bc9e` M18.0 planning + `fe9a19a` M18.1 substrate +
`4c82f71` M18.1 docs + `a7eb65e` M18.2 retail_subprime +
`ee64e25` M18.2 docs + `aa6343f` M18.3 floor_planned +
`2dec5d6` M18.3 docs + `42c604d` M18.4 bhph + `e18e84a`
M18.4 docs + `957a7ba` M18.5 briefs + endpoint + `6b6c3a5`
M18.5 docs + this close-out commit). One new backend
entity (`TesterFeedback`; tenancy carriers 49 → 50). Two
additive `Dealership` columns (`is_demo` +
`demo_archetype`). One additive migration (`0047` — two
`AddField` + one `CreateModel`; zero data migration). One
new endpoint (POST `/admin/demo-store/feedback/`; DRF
admin surface 107 → 108). One new service package
(`services/demo_store/` with ten modules including nine
core + `briefs/` sub-package containing 13 markdown daily
brief files + brief loader). One new views module
(`views_demo_store.py`). One new management command
(`demo_store` with four subcommands). Three archetype
builders (`retail_subprime.py` + `floor_planned.py` +
`bhph.py`) each constructing coherent operational stories
across every shipped M1-M17 capability that applies to
the archetype. **All three archetype builders + all 13
briefs + POST endpoint + CSV export** verified end-to-end
via 175 focused tests. Frontend Vitest 140 (unchanged —
zero frontend at M18). Frontend operator routes 20
(unchanged — testers use existing M1-M17 routes). Zero-
drift permission-class posture — extends to fourteen
consecutive milestones (M10 → M18.5). Celery-beat task
families 10 (unchanged — no beat entry at M18). Zero new
post-LLM scrub stages (M18 has no LLM path). **Seven §5
decisions confirmed as-recommended at M18.0 open** —
streak extends to 77 planning-time as-recommended M5.1 →
M18.0 across nine consecutive milestones (M10 + M11 +
M12 + M13 + M14 + M15 + M16 + M17 + M18). Five §0.a
implementation-time micro-decisions across M18.1 + M18.2
— do not count against the streak per M10 §9.*

**Business objective.** The platform now has a broad
verified capability surface through M17. The highest-
value next step is not another isolated accounting
extension — it is **proving that experienced independent-
dealer operators can enter a believable store, recognize
their normal operating world, work through a realistic
day using shipped capabilities, and provide actionable
product + commercial feedback**. Testers Chris already
knows in the car business may become the first pilot
customers.

**Related research.**
- `INDEPENDENT_DEALER_PIVOT.md` — the persona shape the
  three archetypes reflect (retail/subprime,
  floor-planned/recon-heavy, BHPH).
- `SALES_DEPARTMENT_MAPPING.md` §retail + subprime motion.
- `BHPH_OPERATIONS_MAPPING.md` §portfolio operations +
  payment rhythm.
- `INVENTORY_ACQUISITION_MAPPING.md` §floor-planned
  patterns.
- `RECON_MAPPING.md` §outside-recon workflows.

**Operational pain resolved.**
- Before M18, Chris could show prospective testers **one**
  demo persona (Copper Canyon Auto — the migration-seeded
  default). The tester saw *a* store, not *their* store.
  No coherent story linked across shipped capabilities to
  demonstrate the platform's cross-domain integrity.
- Before M18, tester feedback was captured on paper or in
  ad-hoc spreadsheets. No structured category vocabulary.
  No willingness-to-pay signal that could be aggregated.
  No CSV export.
- Before M18, hand-provisioning a demo store required
  manually seeding vehicles + salespeople + leads +
  sales + notes + payments across ~15 shipped models.
  Tester sessions would have been prohibitively expensive
  to run repeatably.
- Before M18, no guard-by-construction posture protected
  demo stores from accidental real-world side effects
  (real email, real SMS, real bureau pulls, real payment
  processing). The scanner test enforces the contract
  going forward.

**Existing reusable primitives.**
- **`Dealership` model** — gained two additive columns
  without breaking any existing tenancy path.
- **`_TENANT_CARRIER_MODEL_NAMES`** — extended by one for
  `TesterFeedback` following the M13.1 + M17.1 pattern.
- **`_auth_helpers.make_dealership`** — companion
  `make_demo_dealership(archetype, slug)` helper wraps it.
- **M13.1 `seed_default_coa`** — called by the demo-store
  registry on create + reset so archetype-authored M15
  sale-bookings have the required accounts.
- **M15 `record_sale` + M12 `record_bhph_note` + M12
  `record_payment` + M12 `record_promise` + M12
  `mark_kept` + M12 `record_contact` + M12
  `record_repossession` + M12 `mark_recovered` + M10
  `record_credit_application` + M11 `start_cadence`** —
  every archetype builder consumes these shipped service
  verbs; zero modifications.
- **M2 investment ledger + M4 recon work order + M5
  lifecycle stage + M6 photography + M13.3 trial
  balance + M14.3 journal-entry browser + M16 detector
  + M17 as_of picker** — all consumed by the archetype
  builders via the same routes real operators would use.

**Gap.**
- Demo dealership designation (`is_demo` flag) so guards
  can distinguish live from demo tenants (M18.1 fills).
- Archetype vocab + builders for the three canonical
  independent-dealer shapes (M18.2 + M18.3 + M18.4 fill).
- Deterministic seed/reset substrate with belt-and-
  suspenders guards (M18.1 fills).
- Outbound-send-boundary guard toolkit + scanner (M18.1
  fills).
- Tester feedback capture (M18.1 model, M18.5 endpoint +
  exporter).
- Daily briefs walking role-scoped scenarios (M18.5
  fills).

**Scope (seven increments — first non-accounting
milestone since M12; all shipped SESSION_146 → 152).**
- **M18.0** — planning refinement + target selection.
- **M18.1** — backend substrate (schema + service
  package + guards + management command + scanner).
- **M18.2** — retail/subprime archetype pack.
- **M18.3** — floor-planned archetype pack (with $825
  recon overrun anchor).
- **M18.4** — BHPH archetype pack (with M16 detector
  timing anchor).
- **M18.5** — 13 daily briefs + POST feedback endpoint +
  CSV exporter completion.
- **M18.6** — close-out docs.

**Out of scope for M18** (deferrals cataloged in
`MILESTONE_18_RETROSPECTIVE.md` §3):
- Public self-serve demo signup; production deployment
  solely for this milestone; full customer onboarding
  automation; product tours / walkthrough overlays;
  broad clickstream analytics; session recording; generic
  whole-platform UI polish; fake stubs for unfinished
  capabilities; outbound email / SMS to real
  destinations; DMS / lender / bank / auction / bureau /
  payment / accounting-provider integrations; pricing
  logic / billing / subscriptions / contracts;
  conversion of testers into real-data pilot stores.
- **Chargeback substrate** per §0.a M18.2 decision 1.
  Re-entry: F&I scenario milestone if operator evidence
  surfaces demand.
- **Demo-store-aware LLM cost caps** per §0.a M18.1
  decision 1.
- **Feedback capture UI form** — deferred per §5.f
  evidence gate.
- Payroll / W-2 / 1099 (external services). GAAP-audited
  financial reporting (out of scope for platform v1).
  Direct DMS integration (belongs to a future vendor-
  integration milestone).
- All still-valid unblocked-work items from earlier
  milestones per M17 §8 (period-close comparison view;
  financial-reports substrate; CSV / PDF export of
  frozen snapshots; auto-freeze on schedule; reopen /
  unfreeze; M10 chargeback GL reversal; NSF / payment-
  reversal; category-group-aware GL mapping; M14 UX
  polish; sale-reversal; VehicleCost variance;
  deposit / bank reconciliation; method-aware fund-flow;
  BhphFee entity; BHPH interest accrual detector).

### Milestone 19 — Founding Dealer Pilot Onboarding — SHIPPED at SESSION_159

*Full delivery record:
`docs/roadmap/MILESTONE_19_PLANNING.md` §7 (annotated
SHIPPED per increment; eleven §0.a change-log
amendments recorded across M19.1 → M19.5
implementation sessions) and
`docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7t.
Backend test baseline delta: 4,538 → 4,679 (+141 tests
across all M19 increments, zero regressions). Frontend
Vitest baseline: 140 → 153 (+13 tests at M19.4 for the
new `PilotOnboardingSection` component). Sessions: 153
→ 159 (seven increments including planning + close-out;
commits `8892447` M19.0 planning + `4ffb514` M19.1
substrate + `23e92da` M19.2 inventory import + `c3b58ba`
M19.3 endpoints + `ad9bf21` M19.4 frontend + import
endpoint + `89a58c8` M19.5 playbook + dry-run + this
close-out commit). Three new backend entities
(`PilotProspect` pre-tenant record + `PilotOnboardingChecklist`
+ `PilotOnboardingStep`; tenancy carriers 50 → 52 —
`PilotProspect` intentionally NOT registered per §0.a
M19.1 decision 1). Four additive `Dealership` columns
(`is_pilot` + `outbound_enabled` + `terminated_at` +
`termination_reason`). One additive migration (`0048` —
four `AddField` + three `CreateModel` + one unique
constraint; zero data migration). Five new endpoints
(`POST /admin/pilots/create/`, `GET /admin/pilots/`,
`POST /admin/pilots/<slug>/checklist/advance/`, `POST
/admin/pilots/<slug>/inventory/import/`, `POST
/admin/pilots/<slug>/terminate/`; DRF admin surface
108 → 113). One new service package
(`services/pilot_onboarding/` with six modules). One
new views module (`views_pilot_onboarding.py`). One new
frontend component (`frontend/src/components/pilots/PilotOnboardingSection.tsx`
~530 lines with four sub-panels) embedded in existing
`/dealer-ai-admin` route per §0.a M19.4 decision 2 —
**zero new operator routes**. Two new operator reference
docs (`docs/PILOT_INVENTORY_TEMPLATE.md` +
`docs/PILOT_ONBOARDING_PLAYBOOK.md`). Refactored M18.1
outbound guard from identity-based (`is_demo`) to
policy-field (`outbound_enabled`) predicate per §0.a
M19.1 decision 2; deprecated `suppress_if_demo` alias
preserved. Frontend Vitest 140 → 153 (+13 at M19.4).
Frontend operator routes 20 (unchanged). Zero-drift
permission-class posture — extends to nineteen
consecutive milestones (M10 → M19.5). Celery-beat task
families 10 (unchanged — no beat entry at M19). Zero
new post-LLM scrub stages (M19 has no LLM path).
**Eight §5 decisions confirmed as-recommended at M19.0
open** — streak extends to 85 planning-time as-
recommended M5.1 → M19.0 across ten consecutive
milestones (M10 + M11 + M12 + M13 + M14 + M15 + M16 +
M17 + M18 + M19). Eleven §0.a implementation-time
micro-decisions across M19.1 → M19.5 — do not count
against the streak per M10 §9.*

**Business objective.** M18 gave Chris the demo stores +
daily briefs to run tester sessions; the natural M19
follow-through is **the controlled path from a demo
tester who says "I want to try this with my store" to
a safe, usable real-store pilot without ad hoc database
work or code edits**. Testers Chris already knows in
the car business now have a place to land as pilot
customers.

**Related research.**
- `INDEPENDENT_DEALER_PIVOT.md` — the persona shape the
  pilot substrate accommodates.
- `INVENTORY_ACQUISITION_MAPPING.md` — pilot dealer
  inventory intake patterns.
- Every M18 archetype builder — reference for
  cross-domain integrity expectations.

**Operational pain resolved.**
- Before M19, converting a demo tester into a live
  pilot dealer required ad hoc database work: create
  Dealership row, seed COA, attach owner user, populate
  onboarding profile, import inventory manually.
  Multi-step + error-prone + risky.
- Before M19, no fail-safe posture for outbound
  behavior on a fresh dealership. Any adapter that
  egressed would fire against real destinations from a
  first-day pilot.
- Before M19, no seven-step operator checklist codified
  the onboarding path. The pilot readiness bar was
  Chris's memory.
- Before M19, no rejected-row surfacing for pilot
  inventory CSVs. A dealer's Excel export with one bad
  row would fail-hard or silently drop rows.
- Before M19, no codified end-to-end test proving the
  pilot substrate held. Substrate regressions could
  ship without CI signal.

**Existing reusable primitives.**
- **`Dealership` model** — gained four additive columns
  without breaking any existing tenancy path.
- **`_TENANT_CARRIER_MODEL_NAMES`** — extended by two
  (checklist + step). `PilotProspect` intentionally
  NOT registered per §0.a M19.1 decision 1.
- **`_auth_helpers.make_dealership`** — companion
  `make_pilot_dealership(slug, outbound_enabled)`
  helper wraps it.
- **M13.1 `seed_default_coa`** — called by the pilot
  registry so future GL posts have accounts.
- **M6.3 `services/inventory_import.py`** — reused
  verbatim per §0.a M19.2 decision 1. The pilot
  wrapper is a thin overlay.
- **M18.1 outbound guard toolkit** — refactored to
  policy-field predicate; deprecated alias preserves
  every M18-era caller.
- **M18.1 outbound-egress scanner** — contract
  unchanged; enforces guard adoption on every future
  `services/` egress verb.
- **DRF `IsAuthenticated`** — reused per §0.a M19.3
  decision 2 (no new permission class).
- **Django `UploadedFile` + `MultiPartParser`** —
  standard multipart contract per §0.a M19.4 decision
  1.

**Gap.**
- Pilot tenant-type flag (`is_pilot`) so verbs can
  distinguish pilot from demo / live tenants (M19.1
  fills).
- Send policy field (`outbound_enabled`) orthogonal to
  tenant-type (M19.1 fills).
- Pre-tenant operator record (`PilotProspect`) with
  state machine for demo → qualified → converted
  audit trail (M19.1 fills).
- Seven-step onboarding checklist model + service
  verbs (M19.1 fills).
- Pilot-specific CSV wrapper preserving M6.3 semantics
  (M19.2 fills).
- DRF admin surface for the five pilot lifecycle verbs
  (M19.3 + M19.4 fill).
- Frontend admin sub-section embedded in `/dealer-ai-admin`
  (M19.4 fills).
- Codified end-to-end contract test (M19.5 fills).
- Operator reference docs (M19.2 template + M19.5
  playbook fill).

**Scope (seven increments — first fully mixed
substrate + backend + frontend + doc + validation-
contract milestone since M10):**
- M19.0 (SESSION_153): planning refinement + target
  selection. Eight §5 decisions locked.
- M19.1 (SESSION_154): backend substrate. Migration
  0048 + three models + vocab constants + service
  package + outbound-guard refactor. +59 tests.
- M19.2 (SESSION_155): inventory import wrapper + CSV
  schema doc. Thin overlay on M6.3. +31 net.
- M19.3 (SESSION_156): four lifecycle admin endpoints
  + serializers + URL wiring. Admin surface 108 →
  112. +31 tests.
- M19.4 (SESSION_157): inventory-import endpoint +
  frontend admin sub-section embedded in DealerAdmin.
  Admin surface 112 → 113. +10 backend + +13
  frontend Vitest.
- M19.5 (SESSION_158): playbook doc + end-to-end
  dry-run TestCase covering the full M19.1-M19.4
  substrate in one coherent journey. +10 tests.
- M19.6 (SESSION_159): close-out (this retrospective
  + capability matrix update + implementation
  roadmap entry + planning doc frontmatter flip +
  M20 planning skeleton + session-start refresh).

**Non-goals (this milestone; documented for
transparency).**
- Prospect intake UI, first live-pilot dry-run
  against staging, management-command dry-run
  diagnostic, public / self-serve pilot signup,
  non-CSV inventory ingest, cross-operator
  `PilotProspect` scoping, multi-operator permission
  class, demo-aware LLM router / cost caps (M18.1
  §0.a decision 1 carry-forward), F&I chargeback
  substrate (M18.2 §0.a decision 1 carry-forward),
  all M18 §3 carry-forward deferrals.

### Milestone 20 — Operational Journey Validation (Playwright acceptance testing) — SHIPPED at SESSION_165

*Full delivery record:
`docs/roadmap/MILESTONE_20_PLANNING.md` §7 (annotated
SHIPPED per increment; twelve §0.a change-log
amendments recorded across M20.1 → M20.5
implementation sessions) and
`docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7u.
Backend test baseline delta: 4,679 → 4,755 (+76 tests
across the six seed delta commands, zero regressions).
Frontend Vitest baseline unchanged at 153 (M20 does
not extend Vitest — acceptance is a separate test
surface). Sessions: 160 → 165 (six increments including
planning + close-out; commits `69b8214` M20.0 planning
+ `66ee652` M20.1 framework + canonical pilot journey
+ `e634c34` M20.2 dashboard journeys + `59dc43d` M20.3
back-office journeys + `d7e92c2` M20.4 BHPH read-side
journey + this close-out commit). **Zero new backend
entities, zero new endpoints, zero new migrations, zero
new tenancy carriers, zero new permission classes,
zero new frontend routes.** The change surface is a new
top-level `acceptance/` workspace (Playwright 1.49 +
TypeScript 5.6) with six journey specs + five persona
storage-state files + five business-outcome assertion
helper modules; six new backend management commands
in `dealer_ai/management/commands/seed_journey_*.py`
(each idempotent + `--reset`-capable); a settings.py
`M20_ACCEPTANCE_DB=1` env branch pointing the default
DB at `backend/db.acceptance.sqlite3` (gitignored;
matches M2.1 `migration_check` pattern); and a new
`.github/workflows/acceptance.yml` CI job with tiered
execution (`@pilot-critical` subset on PR ~90s; full
suite on `main` ~5–8 min) + artifact upload on failure
(HTML report + trace + video + screenshot; 14-day
retention). Zero-drift permission-class posture —
extends to **twenty consecutive milestones** (M10 →
M20). Celery-beat task families 10 (unchanged — no
beat entry at M20). Zero new post-LLM scrub stages
(M20 has no LLM path). **Eight §5 decisions confirmed
as-recommended at M20.0 open** — streak extends to
86 planning-time as-recommended M5.1 → M20.0 across
**eleven consecutive milestones** (M10 → M20). Twelve
§0.a implementation-time micro-decisions across
M20.1 → M20.5 — do not count against the streak per
M10 §9.*

**Business objective.** M18 established realistic
demo dealerships; M19 shipped repeatable pilot
onboarding. **The natural M20 follow-through is to
establish the executable operational contract every
future milestone extends** — durable Playwright
acceptance suites walking real dealership workflows
through the shipped UI against deterministic seeded
state. Prevent workflow regressions from shipping to
operators by catching them at PR review time.

**Guiding principle.** The Playwright suite is an
operational acceptance contract, not a UI automation
project. Every journey validates business outcomes
through the real application using deterministic
seeded state. If a journey passes, the conclusion is
that a dealership employee can successfully perform
that operational workflow — not merely that buttons
were clicked successfully. Assertions target business
state (a lead is assigned, a pilot advances to
`readiness_confirmed`, a trial-balance snapshot is
balanced), not DOM state.

**Related research.** M20 references M18/M19 research
+ implementation as its substrate. No new research
corpus additions — Playwright acceptance testing is
a tooling-choice with an established literature.

**Operational pain resolved.**
- Before M20, every operator-facing workflow was
  regression-checkable only via manual exploratory
  testing between milestones. Silent regressions
  could ship to Chris without CI signal and only
  surface when an operator hit them in the shipped
  UI.
- Before M20, contributors reading the code could
  not tell "what does the platform actually do?" for
  operational workflows — the unit + integration
  suites prove verbs behave, but the connective
  tissue ("here's how an owner uses this in a normal
  day") lived only in Chris's head + the M18 demo
  briefs.
- Before M20, the M19.5 pilot onboarding playbook
  was a doc that could drift silently from the
  M19.4 admin UI. Only Chris's next dry-run would
  surface a mismatch.
- Before M20, the missing write-side BHPH
  collections UI (M12.7) was unnamed — a gap that
  would have been discovered during a live pilot's
  first collection cycle, not before.

**Existing reusable primitives.**
- **`_TENANT_CARRIER_MODEL_NAMES`** — unchanged.
  M20 adds zero tenancy carriers.
- **`_auth_helpers.make_dealership` +
  `make_pilot_dealership`** — used indirectly by
  the seed delta commands to plant fixture
  Dealership rows.
- **M13.1 `seed_default_coa`** — invoked by the
  M20.3 accounting seed command.
- **M18/M19 seed patterns** — the M20 seed delta
  commands compose existing M1–M19 service verbs
  (`record_phone_lead`, `create_prospect` +
  `advance_prospect_state`, `post_journal_entry`,
  `record_payment`, `record_promise` + `mark_broken`,
  `record_contact`, `record_repossession`). No
  parallel write paths.
- **M17.1 trial-balance snapshot service verbs** —
  exercised by the M20.3 accounting journey.
- **M12 BHPH read/write endpoints** — read side
  exercised by M20.4 BHPH journey.
- **M19.3 pilot admin endpoints** — exercised by
  the M20.1 canonical pilot onboarding journey.
- **M11 Phase 4 lead assignment endpoint** —
  exercised by the M20.2 sales manager daily
  startup journey.
- **M4.7 recon endpoints** — exercised by the
  M20.3 recon workflow journey.
- **shadcn/ui `<CardTitle>` component** — used as
  the anchor for text-based selectors where the
  dashboard components don't carry `data-testid`
  patterns (per §0.a M20.2 decision 5).
- **`div.fixed.inset-0.z-50` class signature** —
  used to scope selectors to the `LeadDetailModal`
  since it isn't a Radix Dialog (per §0.a M20.2
  decision 4).

**Gap.**
- Executable operational contract for every
  operator-facing workflow (M20.1–M20.4 fill for
  six representative journeys — pilot onboarding
  + owner morning review + sales manager daily
  startup + recon workflow + office/accounting
  workflow + BHPH collections read-side).
- Framework substrate (Playwright workspace +
  webServer + persona storage-state + seed delta
  commands + assertion helpers) — M20.1 fills.
- CI wiring so acceptance journeys fire on every
  PR + `main` push — M20.1 fills; first real CI
  run happens on the M20.5 coordinated push.
- Named write-side BHPH collections UI gap —
  M20.4 identifies as an M21+ candidate.
- Dashboard `data-testid` hardening across the
  DealerOverview + DealerAdmin + LeadsPage +
  LeadDetailModal + AssignmentDropdown surfaces
  — M20 identifies as an M21+ candidate.

**Scope (six increments — first tooling-axis
milestone with zero domain surface changes since
the framework was established):**
- M20.0 (SESSION_160): planning refinement +
  target selection. Eight §5 decisions locked.
  Candidate W folded into Candidate J per
  DOC_GOVERNANCE.md §2. Zero code changes.
- M20.1 (SESSION_161): framework substrate +
  canonical pilot onboarding journey.
  `acceptance/` workspace scaffolded; five-persona
  storage-state pattern; five assertion helper
  modules; six seed delta management commands
  (with one initially — pilot onboarding — the
  other five ship in M20.2–M20.4); GitHub Actions
  workflow; settings.py env branch. +15 backend
  tests.
- M20.2 (SESSION_162): owner morning review
  (`@pilot-critical`) + sales manager daily
  startup journeys. Two new personas; two new
  seed delta commands; three §0.a
  implementation-time decisions surfaced by
  first dry-run + resolved. +27 backend tests
  (12 owner + 15 sales_manager).
- M20.3 (SESSION_163): recon workflow +
  office/accounting workflow journeys. One new
  persona (recon_manager); office journey
  reuses owner persona. Two new seed delta
  commands. Four §0.a decisions (envelope-aware
  helpers, direct ORM creation matching demo
  archetype). +20 backend tests (13 recon + 7
  accounting).
- M20.4 (SESSION_164): BHPH collections read-
  side workflow journey (scope narrowed from
  the planning-time write+read scope per §0.a
  M20.4 decision 1 — write-side UI not shipped).
  One new persona (bhph_collector). One new
  seed delta command + assertion helper. Four
  §0.a decisions. +14 backend tests.
- M20.5 (SESSION_165): close-out (this
  retrospective + capability matrix §7u update +
  implementation roadmap entry + M20 planning
  memo frontmatter unchanged + M21 planning
  skeleton + session-start refresh + coordinated
  close-out commit + first push). Intentional-
  failure verification of CI artifact flow.
  Zero new tests.

**Non-goals (this milestone; documented for
transparency).**
- Write-side BHPH collections UI (record PtP,
  mark broken, log contact, initiate
  repossession) — endpoints exist, frontend UI
  never shipped; recorded as M21+ candidate
  "M12.8 BHPH collections write-side UI".
- Dashboard `data-testid` hardening — recorded
  as M21+ candidate.
- Full cross-browser CI matrix (Chromium-only
  in CI; Firefox + WebKit local).
- Mobile / responsive viewport journeys.
- Performance / load testing via Playwright.
- Third-party integration stubs / mocks (not
  needed — M18.1 outbound guard suppresses).
- Nightly-cron acceptance runs (`main` push
  trigger sufficient).
- Automatic journey generation from user
  telemetry (explicit non-goal).
- Additional pilot-critical journeys beyond the
  two currently tagged.
- All M19 §3 carry-forward deferrals; all M18
  §3 carry-forward deferrals still valid.

### Milestone 21 — Operational Surface Completion — SHIPPED at SESSION_170

*Full delivery record:
`docs/roadmap/MILESTONE_21_PLANNING.md` §7 (annotated
SHIPPED per increment; §0.a M21.1 scope-lock amendment
recorded) and
`docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`. Shipped
surface enumerated in `docs/CAPABILITY_MATRIX.md` §7v.
Backend test baseline delta: 4,755 → 4,761 (+6 seed
coverage tests across M21.2 BHPH + M21.3 sales-manager
extensions; zero regressions). Frontend Vitest baseline
delta: 153 → 180 (+27 new component tests across seven
test files). Acceptance suite: 6 journeys (2 extended
+ 4 unchanged); full local dry-run 12 passed (~18s).
Sessions: 166 → 170 (five increments — one shift vs.
the six-increment planning shape; M21.4 collapsed per
audit evidence). Commits `7ed5e1a` M21.0 planning +
`96a6f4d` M21.1 audit + scope lock + `9a77b84` M21.2
BHPH write-side UI + `0e14c2a` M21.3 be-back CREATE +
cadence CONFIG + this close-out commit. **Zero new
backend entities, zero new endpoints, zero new
migrations, zero new tenancy carriers, zero new
permission classes, zero new frontend routes.** Every
M21 UI attaches in-place to an already-shipped page.
The change surface is one operator-invoked audit
script + one audit artifact + 10 new components across
two domains (7 BHPH + 3 sales) + 7 new bhphApi.ts
write wrappers + 2 seed extensions + 2 journey
extensions. Zero-drift permission-class posture —
extends to **twenty-one consecutive milestones** (M10
→ M21). Celery-beat task families 10 (unchanged — no
beat entry at M21). Zero new post-LLM scrub stages.
**Eight §5 decisions confirmed as-recommended at M21.0
open** — streak extends to 87 planning-time as-
recommended M5.1 → M21.0 across **twelve consecutive
milestones** (M10 → M21). One §0.a implementation-
time amendment across M21.1 → M21.5 (§0.a M21.1
scope-lock recording the audit findings) — does not
count against the streak per M10 §9.*

**Business objective.** M20 established the
executable operational contract every future milestone
extends via Playwright acceptance journeys. **The
natural M21 follow-through is to consume that
substrate by closing the highest-value missing UI
workflows found by the M20 audit** — endpoints where
the backend capability exists but dealership staff
cannot operate it through the product. Every scope
item drives from audit evidence, not intuition.

**Guiding principle** (Candidate O governing
contract): every M21 shipped surface must (a) map to
an already-shipped backend capability, (b) close a
missing operator-facing UI, (c) add or extend a
Playwright operational journey, and (d) not be
generic UX polish. Cosmetic friction feeds Candidate
P (deferred); scope items that require a new backend
verb are out-of-scope (domain-milestone territory).

**Operational pain resolved.**
- Before M21, BHPH collectors could only review the
  portfolio through the product. Recording a
  promise-to-pay, marking it broken, logging a
  contact, initiating a repossession, and
  transitioning it through recovered → re-intaked
  all required curl / Postman / Django shell.
- Before M21, sales managers could not record a
  new be-back through the product — the
  `createBeBack` wrapper existed in salesApi.ts as
  of M11.6 but no component consumed it. Same for
  follow-up cadence config (`createCadence` +
  `pauseCadence` — both wrapper-only per the M21.1
  audit).
- Before M21, there was no systematic view of
  "backend-shipped-but-UI-missing" capabilities.
  Operational-surface priorities depended on what
  Chris observed during his daily use — real
  signal, but not systematic.

**Existing reusable primitives.**
- **M12 BHPH service verbs + endpoints** —
  `record_promise` / `mark_kept` / `mark_broken` /
  `record_contact` / `record_repossession` /
  `mark_recovered` / `mark_re_intaked`. Consumed
  by M21.2 UI unchanged.
- **M11.5 BeBack service verb + endpoint** —
  `record_be_back`. Consumed by M21.3 UI
  unchanged.
- **M11.4 FollowUpCadence service verbs +
  endpoints** — `start_cadence` +
  `pause_cadence`. Consumed by M21.3 UI
  unchanged.
- **M20 acceptance framework** —
  `acceptance/support/assertions/bhph.ts` +
  `dashboard.ts` extended (not modified). Journey
  extensions land in existing spec files per §5.e
  Option C.
- **M20 seed delta commands** —
  `seed_journey_bhph_collections_workflow` +
  `seed_journey_sales_manager_daily_startup`
  extended with M21-specific fixtures. No new
  seed commands.
- **shadcn/ui `<Dialog>` component** — used for
  confirm modals (mark-broken, mark-recovered,
  mark-re-intaked, pause-cadence-by-id).
- **`bhphApi.ts` read wrappers (M12.7)** — pattern
  matched for the seven new M21.2 write wrappers.
- **`salesApi.ts` write wrappers (M11.4 / M11.6)**
  — already existed as wrapper-only; M21.3 adds
  the component consumers.

**Gap.**
- The M20 operational contract is durable only if
  future milestones extend it. Without a binding
  DoD amendment, journeys silently atrophy as new
  operator-facing surfaces ship without acceptance
  coverage. The M21.0 §5.f Option B DoD amendment
  closes this gap — formalized in §5 below.

**Definition of Done amendment (M21.0 §5.f Option
B — now binding).** Every future customer-facing
milestone MUST either:

- **(a) add or update at least one Playwright
  operational journey covering the shipped
  operator surface**, OR
- **(b) explicitly document in §3 of the planning
  memo why no journey change is required.**

Infrastructure-only milestones with no customer-
facing surface changes satisfy via (b).
Non-adherence is a planning-memo review finding.
Amendment applies from M21 forward. M21.2 + M21.3
both satisfied via journey extensions (BHPH re-
expansion + sales-manager extension). This
amendment sits alongside the standing scope-
discipline rules per PROJECT_RULES.md.

**M21 shipped increments:**
- M21.0 (SESSION_166) — planning refinement +
  target selection. All 8 §5 decisions confirmed
  as-recommended.
- M21.1 (SESSION_167) — systematic operational-
  surface audit + M21 scope lock. Audit tooling
  at `backend/dealer_ai/scripts/audit_operational_surface.py`
  + audit artifact at
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  (153 endpoints enumerated).
- M21.2 (SESSION_168) — BHPH write-side UI (7
  endpoints). 7 wrappers + 7 components + 18
  Vitest tests + seed extension + journey re-
  expansion.
- M21.3 (SESSION_169) — Be-back CREATE +
  Follow-up cadence CONFIG (3 endpoints). 2
  panels + 9 Vitest tests + seed extension +
  journey extension.
- M21.4 — SKIPPED per §0.a M21.1 audit evidence.
- M21.5 (SESSION_170) — audit regen (coverage
  96 → 106) + capability matrix §7v +
  retrospective + M22 skeleton + IMPLEMENTATION_ROADMAP
  amendment (DoD formalization) + coordinated
  push per M18.6 / M19.6 / M20.5 cadence.

**Non-goals deferred from M21 (see
`MILESTONE_21_RETROSPECTIVE.md` §3 + §4):**
- 44 `defer-candidate-O2` endpoints for future
  OSC iterations (F&I writes, lead-source-
  specific intake, BHPH note origination + payment
  intake, deal-writeup lifecycle, test-drive
  creation, misc dashboards).
- 3 `defer-domain-milestone` endpoints for the
  accounting stream (journal-entry reverse +
  trial-balance snapshot lifecycle) — elevated as
  M22 Candidate A scope target.
- Nested TypeScript template literal support in
  the audit tooling (~3 false-positive backend-
  only findings; TS-aware parsing deferred).
- Full dashboard testid coverage (Candidate G) —
  M21 landed opportunistic testids only.
- All M20 §3 carry-forward deferrals still valid.

### Milestone 22 — Accounting Operational Validation — SHIPPED at SESSION_174

*Full delivery record:
`docs/roadmap/MILESTONE_22_PLANNING.md` §7
(annotated SHIPPED per increment; §0.a M22.0
+ M22.1 + M22.2 amendments recorded) and
`docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`.
Shipped surface enumerated in
`docs/CAPABILITY_MATRIX.md` §7w. Backend test
baseline delta: 4,761 → 4,766 (+5 M22.2 seed
idempotency tests; M22.1 audit fix added no
tests per §0.a discretionary call). Frontend
Vitest baseline unchanged at 180 — M22
introduced zero frontend components per §5.a
refined framing. Acceptance suite: 6 → 7
journeys; full clean-DB dry-run 13 passed
(~18s). Sessions: 171 → 174 (four increments
— M22.3 SKIPPED per §5.b page/persona walk
evidence; second consecutive milestone where
the evidence-sized §5.h Option B posture
shrank the shape). Commits `421a75c` M22.0
planning + `f95db70` M22.1 audit correction
+ `6635a9d` M22.2 JE reversal journey + this
close-out commit. **Zero new backend entities,
zero new endpoints, zero new migrations, zero
new tenancy carriers, zero new permission
classes, zero new frontend routes, zero new
frontend components.** The M14 + M17.2
accounting UI ships unchanged; M22 validated
it end-to-end without rebuilding what already
exists. Zero-drift permission-class posture —
extends to **twenty-two consecutive
milestones** (M10 → M22). Celery-beat task
families 10 (unchanged). Zero new post-LLM
scrub stages. **Seven §5 decisions confirmed
as-recommended at M22.0 open** — streak
extends to **88 planning-time as-recommended
M5.1 → M22.0** across **thirteen consecutive
milestones** (M10 → M22). Zero §0.a
amendments introducing new §5 decisions — all
M22.N §0.a entries record shipped outcomes.*

**Business objective.** M18 §8 designated
accounting as the next available domain-
milestone slot. Four subsequent milestones
diverged from that designation (M18 → M21).
The M21 retrospective §9 recommended Candidate
A as the M22 target based on M21.1 audit
dispositions claiming three accounting
endpoints (`journal-entry-reverse`, `trial-
balance-snapshot-list`, plus other snapshot
verbs) were backend-only.

**M22.0 empirical discovery falsified that
premise.** The three shipped accounting
operator pages
(`AccountingTrialBalancePage`,
`AccountingJournalEntriesPage`,
`AccountingJournalEntryDetailPage`) already
existed from M14/M17. Both anchor UIs
originally named (JE reversal + trial-balance
snapshot lifecycle) already shipped as fully-
wired operator surfaces. The M21.5 audit's
"backend-only" claims for four accounting
endpoints were false negatives from a regex
limitation the M21.1 close documented but
never fixed.

User redirected M22 from "ship missing UI"
to **Accounting Operational Validation** —
prove the shipped accounting workflows are
operationally complete via Playwright end-to-
end validation; correct the audit tooling so
its output becomes trustworthy source material
for future accounting candidates; identify any
genuinely missing workflows through journey
authoring evidence rather than speculation.

**Guiding principle** (Candidate A refined for
validation-shape milestones): every M22
shipped surface must (a) map to shipped
frontend surface AND shipped backend capability
— the validation-shape refinement of M21's
condition (1), preventing scope drift into
"build the missing UI" when the audit misled
us; (b) establish operational-completion
evidence through Playwright end-to-end journey
(Vitest doesn't count because it mocks the
API layer); (c) use journey-as-verifier rather
than manual pre-verification; (d) split
discovered gaps by size — small in-scope fix
(missing testid, broken link, label typo,
form validation bug) vs. large deferred as
next candidate evidence (missing form,
missing wrapper, missing service verb, new
UI structure).

**Operational pain resolved.**
- Before M22, the JE reversal workflow (JE
  detail → open dialog → fill reason → confirm
  → verify reversal) shipped from M14.3/M14.4
  but had no Playwright end-to-end validation.
  Vitest coverage existed but only proved
  component rendering against mocked
  responses, not full-stack completability.
- Before M22, the audit artifact was
  untrustworthy for accounting endpoints —
  four wrappers using variable-first URL
  assembly (`const path = ...; return
  authGetJSON(path);`) were invisible to
  `_HELPER_CALL_RE`, so their endpoints
  appeared backend-only. Any M23+ scope
  proposal grounded in the audit would build
  on false premises.
- Before M22, the M21 retrospective §9
  specific scope recommendation for M22
  Candidate A was speculative — grounded in
  M21.1 audit numbers that didn't reflect the
  actual shipped UI surface. Left unchecked,
  M22 would have shipped ~10 new components
  duplicating already-shipped operator
  workflows.

**Existing reusable primitives.**
- **M14.2/M14.3/M14.4 accounting frontend
  surface** — `AccountingTrialBalancePage`,
  `AccountingJournalEntriesPage`,
  `AccountingJournalEntryDetailPage`
  (including `ReverseEntryDialog`) all consumed
  by M22 journey unchanged. Zero component
  changes.
- **M17.2 trial-balance snapshot lifecycle
  UI** — freeze button + prior-closes card +
  inline snapshot detail. Already Playwright-
  validated by the M20.3
  `office/accounting_workflow.spec.ts`
  journey; M22 confirmed via clean-DB dry-run
  the journey still passes.
- **M13.1 `reverse_journal_entry` service
  verb + endpoint** — consumed by M22.2 UI
  unchanged.
- **M14.1 `admin_journal_entry_list` endpoint**
  — consumed by M22.2 assertion helper for the
  JE lookup by description prefix.
- **M20 acceptance framework** —
  `acceptance/support/assertions/accounting.ts`
  extended (not modified) with `findJournalEntryByDescriptionPrefix`
  + `expectJournalEntryReversed` helpers.
  Journey extension lands as a sibling spec
  file per §5.c Option B (existing office
  persona folder).
- **M20 seed delta commands** —
  `seed_journey_office_accounting_workflow`
  extended additively with the M22.2
  reversible-JE fixture. No new seed
  commands.
- **M21.1 audit tooling** — corrected per
  §5.e Option B targeted regex fix rather
  than rewritten. Regex + parser enhancements
  handle variable-first URL assembly + nested
  template literals correctly.
- **Owner persona storage state** — reused
  unchanged. Dealer_owner role is sufficient
  for the M13/M14/M17 accounting endpoint
  permission gate
  `IsSalesManagerOrOwnerAtActiveDealership`
  per M20 §5.e Option B posture.

**Gap.**
- The M20 acceptance contract binds
  customer-facing milestones to add or extend
  Playwright journeys. But it doesn't cover
  the case of an ALREADY-SHIPPED customer-
  facing surface that never received journey
  coverage in the first place. The M22 shape
  addresses this gap by treating validation-
  of-shipped-surface as a first-class
  milestone shape — same governing-contract
  discipline, different intent than
  UI-creation milestones.

**M22 shipped increments:**
- M22.0 (SESSION_171) — planning refinement +
  target selection. Candidate A confirmed at
  open, reshaped by empirical discovery. All
  7 §5 decisions confirmed as-recommended.
- M22.1 (SESSION_172) — audit tooling
  correction. Three targeted changes to
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  reclassified all four accounting
  misclassifications (`admin-trial-balance`,
  `admin-journal-entry-list`,
  `admin-cost-posting-failures`,
  `admin-trial-balance-snapshot-list`) from
  backend-only to `covered`. Coverage 106
  → 110 (+4). Budget guard held (~30-40 min
  vs. ~2-hour §5.e guard).
- M22.2 (SESSION_173) — JE reversal
  Playwright journey + seed extension +
  assertion helpers. New
  `acceptance/journeys/office/accounting_je_reversal.spec.ts`
  walks the M14.3/M14.4 reversal workflow
  end-to-end. Extended
  `seed_journey_office_accounting_workflow.py`
  additively with reversible-JE fixture +
  reversal-cleanup on re-invocation. Extended
  seed test module with 5 new test cases.
  Extended assertion helper with
  `findJournalEntryByDescriptionPrefix` +
  `expectJournalEntryReversed`. Journey passed
  on first run — journey-as-verifier per §5.f
  Option B validated.
- M22.3 — SKIPPED per §5.b page/persona walk
  evidence. No additional distinct-workflow
  gaps warrant dedicated journey files.
- M22.4 (SESSION_174) — CI hardening + audit
  artifact regen verification + capability
  matrix §7w + retrospective + M23 skeleton +
  IMPLEMENTATION_ROADMAP update + coordinated
  push per M18.6 / M19.6 / M20.5 / M21.5
  cadence.

**Non-goals deferred from M22 (see
`MILESTONE_22_RETROSPECTIVE.md` §3 + §4):**
- Building new accounting UI — explicit non-
  scope per §5.a refined framing. Large-gap
  findings become future evidence per §5.d
  Option B.
- Full AST-based audit tooling rewrite —
  explicit non-goal per §5.e Option B.
- Additional accounting Playwright journeys
  (as-of picker interaction, cost-posting
  failures rendering path, JE list
  navigation) — deferred per §5.b page/persona
  walk finding + §5.h Option B evidence-sized
  shape.
- Genuinely missing accounting workflows
  (JE creation UI, cost-posting failures
  remediation actions, accounting operator
  navigation surface, month-end close
  checklist) — none surfaced during M22.2
  authoring; possibility preserved for M23+
  scope proposal via a dedicated accounting
  sub-audit.
- Pre-existing test-hygiene issue (three
  journeys mutate DB state their seeds
  don't reset) — recorded as M23+ candidate.
- All M21 §3 carry-forward deferrals still
  valid.

### Milestone 23 — BHPH Origination + Payment Intake — SHIPPED at SESSION_179

*Full delivery record:
`docs/roadmap/MILESTONE_23_PLANNING.md` §7
(annotated SHIPPED per increment; §0.a M23.0
+ M23.1 + M23.2 + M23.3 amendments recorded)
and `docs/roadmap/MILESTONE_23_RETROSPECTIVE.md`.
Shipped surface enumerated in
`docs/CAPABILITY_MATRIX.md` §7x. Backend test
baseline delta: 4,766 → 4,780 (+14 across
M23.2 + M23.3 seed idempotency + cleanup
tests; M23.1 audit fix added no tests per
§0.a discretionary call). Frontend Vitest
baseline delta: 180 → 193 (+13 across two
new component test files: RecordBhphNoteForm
7 + RecordBhphPaymentForm 6). Acceptance
suite: 7 → 9 journeys; full clean-DB dry-
run 15 passed (~20.5s). Sessions: 175 →
179 (five increments — milestone shape
matched planned 5-increment target exactly,
unlike M21.4 skip / M22.3 skip). Commits
`6e2324c` M23.0 planning + `3f3b805` M23.1
audit fix + `7deeda1` M23.2 note origination
+ `a354d98` M23.3 payment intake + this
close-out commit. **Zero new backend
entities, zero new endpoints, zero new
migrations, zero new tenancy carriers, zero
new permission classes, zero new frontend
routes.** M23 UI attaches in-place to
existing pages (`DealerAiBhphPortfolio`
Notes card for origination;
`DealerAiBhphNoteDetail` Payments card for
payment intake). Zero-drift permission-class
posture — extends to **twenty-three
consecutive milestones** (M10 → M23).
Celery-beat task families 10 (unchanged).
Zero new post-LLM scrub stages. **Eight §5
decisions confirmed as-recommended at M23.0
open** — streak extends to **89 planning-
time as-recommended M5.1 → M23.0** across
**fourteen consecutive milestones** (M10 →
M23). Zero §0.a amendments introducing new
§5 decisions.*

**Business objective.** M12 backend shipped
the full BHPH lifecycle (note origination,
payment intake, promises, contacts,
repossessions). M12.7 shipped the read UI.
M20.4 shipped Playwright coverage of the
read-side portfolio review. M21.2 shipped
write-side UI for collections (promises,
contacts, repossessions). But two BHPH
bookends — origination and cash payment
intake — were still curl-only. Dealership
staff could COLLECT on notes but not
ORIGINATE them; collectors could work the
portfolio but not RECORD incoming cash
payments through the product. M23 closes
both gaps and validates each via Playwright
end-to-end. **The BHPH lifecycle is now
operationally complete** — every M12 verb
is reachable through the product with
regression-detecting acceptance coverage.

**Guiding principle** (inherited from M21
Candidate O UI-creation contract): every
M23 surface (a) maps to shipped backend
+ missing frontend, (b) closes a missing
operator-facing UI, (c) adds or extends
a Playwright operational journey, (d) not
generic UX polish.

**M23.0 empirical verification pattern
continued.** M23.0 open verified the two
target endpoints (row 123 + row 126)
against current code state before locking
scope. Surfaced NEW audit false-positive
class: HTTP-verb-agnostic URL-prefix
matching (row 123 falsely claimed
`getBhphNote` GET wrapper as consuming
POST endpoint). M23.1 bounded targeted
fix closed the class + revealed row 139
(`admin-journal-entry-create`) as
previously-hidden genuine gap (JE
creation UI is missing). Verification-
at-planning-open discipline continues to
generate compound planning value.

**Operational pain resolved.**
- Before M23, `admin-bhph-note-create`
  (POST `/admin/bhph-notes/`) had no
  wrapper in `bhphApi.ts` and no
  component consumer. Note origination
  required curl / Django shell.
  `DealerAiBhphPortfolio.tsx:193-194`
  literally documented the gap in its
  empty-state message.
- Before M23, `admin-bhph-payment-create`
  (POST `/admin/bhph-notes/<pk>/payments/`)
  had the same shape — wrapper-less,
  UI-less, curl-only. Existing Payments
  card on note detail was read-only.
- Before M23, the M22 retrospective §9
  A2 candidate (accounting completeness)
  couldn't be scoped precisely because
  the audit's HTTP-verb-agnostic false-
  positive class hid `admin-journal-
  entry-create` under a spurious
  "covered" label. M23.1 correction
  surfaces the gap; M24 can now scope it
  with evidence.

**Existing reusable primitives.**
- **M12 backend service verbs +
  endpoints** — `record_bhph_note` +
  `record_payment`. Consumed by M23 UI
  unchanged.
- **M12.7 frontend surfaces** —
  `DealerAiBhphPortfolio.tsx` (Notes
  card) + `DealerAiBhphNoteDetail.tsx`
  (Payments card). Extended in-place
  per M17 §6 lesson 6 + M21.2 precedent.
- **M20/M21 seed pattern** —
  `seed_journey_bhph_collections_workflow.py`
  extended additively with M23.2 +
  M23.3 fixtures + cleanup on re-
  invocation (matches M22.2 reversal-
  cleanup pattern).
- **M21.2 sibling-pattern discipline**
  — `RecordPromiseToPayForm` inline in
  Promises card became the template for
  `RecordBhphPaymentForm` inline in
  Payments card (M23.3 first-run pass).
- **M22.1 audit-tooling correction
  precedent** — bounded targeted fix
  under ~2-hour budget guard. M23.1
  applied the same shape.
- **`bhph_collector` persona** — reused
  unchanged. Storage state provisioned
  at setup; M23.2 fix to
  `_provision_collector` preserves
  session hashes across seed re-
  invocations.

**Gap.**
- The M22 refined validation-shape
  governing contract (require shipped
  frontend surface) is orthogonal to
  the M21 Candidate O UI-creation
  contract (build missing frontend
  against shipped backend). M23 used
  the M21 shape. M24+ candidates that
  are UI-creation shape inherit M21
  contract; validation-shape inherit
  M22 contract. Both contracts share
  three of four conditions.

**M23 shipped increments:**
- M23.0 (SESSION_175) — planning
  refinement + target selection. 8
  §5 decisions confirmed as-
  recommended. Empirical verification
  surfaced NEW audit false-positive
  class.
- M23.1 (SESSION_176) — audit-tooling
  correction. HTTP-verb-agnostic URL-
  prefix matching false-positive class
  closed. Coverage 110 → 108;
  backend-only 43 → 45. Row 139
  (`admin-journal-entry-create`)
  surfaced as NEW genuine gap for M24.
- M23.2 (SESSION_177) — note
  origination UI + journey. §5.d
  in-scope fix: session-invalidation
  seed bug.
- M23.3 (SESSION_178) — payment
  intake UI + journey. First-run
  pass — no §5.d fixes required.
- M23.4 (SESSION_179) — CI hardening
  + audit artifact regen verification
  + capability matrix §7x +
  retrospective + M24 skeleton +
  IMPLEMENTATION_ROADMAP amendment
  (this section) + coordinated push
  per M18.6 / M19.6 / M20.5 / M21.5 /
  M22.4 cadence.

**Non-goals deferred from M23 (see
`MILESTONE_23_RETROSPECTIVE.md` §3 + §4):**
- Sale-picker UI / deep-link for
  `RecordBhphNoteForm` (§3 deferral 1).
- Additional accounting workflows
  beyond JE creation UI (which is now
  audit-verified genuine gap, recorded
  as M24 candidate).
- Full AST-based audit rewrite (§3
  deferral 8; explicit non-scope).
- Non-BHPH audit false-positive/
  negative sweep (§3 deferral 9).
- Test-hygiene remediation across
  other seeds (Candidate H — expanded
  at M23.2 to include session-
  invalidation sweep).
- All M22 §3 carry-forward deferrals
  still valid.

### Milestone 24 — Sales Operational Entry — SHIPPED at SESSION_184

*Full delivery record:
`docs/roadmap/MILESTONE_24_PLANNING.md` §7
(annotated SHIPPED per increment; M24.1-open
correction preamble records the mid-milestone
planning revision to §5.b + §5.d + §5.h) and
`docs/roadmap/MILESTONE_24_RETROSPECTIVE.md`.
Shipped surface enumerated in
`docs/CAPABILITY_MATRIX.md` §7y. Backend test
baseline delta: 4,780 → 4,780 (unchanged — M24
added zero backend logic). Frontend Vitest
baseline delta: 193 → 209 (+16 across two new
component test files: LeadIntakeForm 8 +
ReferralLeadFormExtras 8). Acceptance suite:
9 → 13 journeys; full clean-DB dry-run 19
passed (~26.8s). Sessions: 180 → 184 (five
increments — M24.4 folded into M24.5 close-
out per §5.h Option B evidence-sized posture,
so five sessions spanned five logical
increments with the final session covering
M24.4 + M24.5 together). Commits `a52a56e`
M24.0 planning + `75752f1` M24.0 planning
correction + `89eb9ed` M24.1 walk-in +
`0e83342` M24.2 phone + `24ddad5` M24.3
referral + this close-out commit. **Zero
new backend entities, zero new endpoints,
zero new migrations, zero new tenancy
carriers, zero new permission classes, zero
new frontend routes.** M24 UI attaches in-
place to `DealerAiSalesLeads.tsx` (three
Dialog CTAs + `LeadDetailModal` +
`AssignmentDropdown` wire-in) — no new
routes. Zero-drift permission-class
posture — extends to **twenty-four
consecutive milestones** (M10 → M24) — all
four intake endpoints reuse
`IsSalesManagerOrOwnerAtActiveDealership`
(existing M4 class). Celery-beat task
families 10 (unchanged). Zero new post-LLM
scrub stages. **Planning-time as-recommended
streak RESET TO 0** at M24.0 open on the
webhook operator-UI posture redirect; second
planning revision at M24.1 open (downstream-
verb UI substrate gap) kept the streak at
0 — both corrections recorded honestly rather
than reclassified to preserve the counter.
Historical run of 89 across fourteen
consecutive milestones (M10 → M23) preserved
for the record.*

**Business objective.** M6 shipped the public
chat funnel that turns customer conversations
into `CustomerLead` rows. M11.1 shipped the
four non-chat lead intake endpoints (walk-in,
phone, referral, listing-platform webhook)
with typed wrappers in `salesApi.ts` since
M11.6. M11.6 shipped the sales-side leads
list at `/dealer-ai-sales/leads`. But none
of the four non-chat intake endpoints had
UI consumers today — every non-chat lead
intake required curl or Django shell. M24
closes this gap for the three operator-
created channels (walk-in, phone, referral)
via UI-native intake and validates the
integration-to-operator flow for the fourth
(webhook / listing platform) via a
Playwright journey that exercises the real
webhook endpoint. **The sales front-of-
funnel is now operationally complete at the
assign level** — every intake source
reaches the salesperson, opens the lead
detail modal, and enables an assignment.
Phone additionally reaches the follow-ups
page + 24hr cadence creation.

**Framing refined at M24.0 open** per user
direction, from "Sales Intake Bundle" (four
forms) to **"Sales Operational Entry"**
(one operational workflow with four channel-
specific entry points). Framing refinement
strengthened the workflow lens without
changing scope boundaries: four endpoints
→ three operator-created + one integration-
to-operator path (webhook is a system-to-
system integration, not a salesperson-
created lead source; §5.b + §5.d webhook
operator-UI posture redirected before
M24.0 lock).

**Framing corrected again at M24.1 open**
per user direction, before any implementation
code was authored. Empirical UI substrate
verification surfaced two evidence-based
mismatches: (a) route path `/dealer-ai/sales/leads/<id>`
does not exist (real route is
`/dealer-ai-sales/leads` with no `:id` sub-
route); (b) downstream verb UI substrate
assumed by M24.0 §5.d does not fully ship
today (test-drive creation UI absent per
M11.6 deferral; referrer_id display absent
in `LeadDetailModal`; platform display
absent). Revised decisions locked at M24.1
open: post-create opens `LeadDetailModal`
on same page (no redirect; `LeadDetailModal`
+ `AssignmentDropdown` wired into
`DealerAiSalesLeads` as small in-scope
extension); per-channel downstream verbs
scoped to the deepest shipped-and-reachable
operator action; genuinely-missing UI
surfaces (test-drive UI, referrer display,
platform display) deferred to M25 with
explicit re-entry paths.

**Guiding principle** (inherited from M21
Candidate O UI-creation contract): every
M24 surface (a) maps to shipped backend
+ missing frontend, (b) closes a missing
operator-facing UI OR validates a missing
integration-to-operator flow, (c) adds a
Playwright operational journey, (d) not
generic UX polish.

**Operational pain resolved.**
- Before M24, `admin-lead-walk-in-create`,
  `admin-lead-phone-create`, and `admin-
  lead-referral-create` (POST endpoints
  shipped since M11.1) had typed wrappers
  in `salesApi.ts` (since M11.6) but no
  component consumers. Every non-chat lead
  intake required curl / Django shell.
- Before M24, `LeadDetailModal` shipped
  since M4/M11 but was only wired into the
  older `/dealer-ai-leads` admin surface,
  not into `/dealer-ai-sales/leads`. The
  sales-side leads page was read-only —
  the salesperson could see leads but
  could not open detail or assign
  directly from there.
- Before M24, the webhook endpoint at
  `/admin/leads/webhook/` had no
  operational contract — nothing in the
  acceptance suite validated that a
  listing platform's ingested lead
  actually surfaces to the salesperson +
  is assignable via the shipped UI.

**Existing reusable primitives.**
- **M11.1 backend service verbs +
  endpoints** — `record_walk_in_lead`,
  `record_phone_lead`,
  `record_referral_lead`,
  `record_webhook_lead`. Consumed by M24
  unchanged.
- **M11.6 frontend wrappers** —
  `createWalkInLead`, `createPhoneLead`,
  `createReferralLead`,
  `createWebhookLead`. Three consumed by
  M24 UI unchanged; `createWebhookLead`
  remains wrapper-only (no operator UI
  per M24 §5.b redirect).
- **M11.1 `webhook_adapters/generic`
  adapter** — shipped adapter registry
  (`_ADAPTERS = {"generic": generic}`)
  + documented dealer-owned envelope
  (`full_name`, `phone`, `email`,
  `message`, budget hints). M24.4
  journey exercises this exact contract.
- **Frontend `LeadDetailModal` +
  `AssignmentDropdown`** — shipped since
  M4/M11; wired into
  `DealerAiSalesLeads` at M24.1 as a
  small in-scope extension (~30-line
  addition).
- **M21.3 `CadenceConfigPanel`** —
  shipped follow-up cadence creation UI
  on `/dealer-ai-sales/follow-ups`.
  M24.2 phone journey exercises this
  page's `CreateCadenceForm` to spawn
  a 24hr cadence for the new phone
  lead.
- **M20/M23 seed pattern** — new
  `seed_journey_sales_operational_entry`
  followed the M23.2 durable session-
  safe `set_password` guard from the
  start.

**Gap.**
- Referrer_id display in
  `LeadDetailModal` remains deferred to
  M25 per §3 deferral 13 — backend
  contract IS preserved (referrer FK
  set correctly), but the operator
  cannot see the attribution in the
  detail modal today. Recorded as small
  M25 UI extension candidate.
- Platform display in `LeadDetailModal`
  for webhook-origin leads remains
  deferred to M25 per §3 deferral 14 —
  operator sees `channel="listing_form"`
  in the list column but does not see
  the specific `platform` value.
  Recorded as small M25 UI extension
  candidate (bundle with #13 as a single
  "Lead source attribution display" M25
  candidate).
- Test-drive creation UI remains
  deferred to M25 per §3 deferral 12 —
  `createTestDrive` wrapper exists since
  M11.6 but no UI consumes it;
  `DealerAiSalesTestDrives.tsx` is read-
  only per M11.6 explicit deferral.
  Recorded as M25 Candidate O2 sub-
  scope.

**M24 shipped increments:**
- M24.0 (SESSION_180) — planning
  refinement + target selection. 8 §5
  decisions resolved at open. §5.b +
  §5.d redirected before lock on the
  webhook operator-UI posture.
- M24.0 correction (SESSION_181 open)
  — §5.b + §5.d + §5.h revised for the
  downstream-verb UI substrate gap.
  Route path corrected. Three §3
  deferrals added.
- M24.1 (SESSION_181) — shared
  `<LeadIntakeForm>` substrate + walk-in
  Dialog CTA + `LeadDetailModal` +
  `AssignmentDropdown` wire-in +
  walk-in journey + new seed.
- M24.2 (SESSION_182) — phone Dialog
  CTA reusing `<LeadIntakeForm>` +
  phone journey (adds cadence
  downstream step).
- M24.3 (SESSION_183) —
  `<ReferralLeadFormExtras>` referring-
  customer picker + referral Dialog
  CTA + referral journey with API-side
  referrer FK attribution assertion.
- M24.4 (SESSION_184) — webhook
  integration-to-operator journey.
  Journey-only work; folded into
  M24.5 close-out per §5.h Option B
  evidence-sized collapse posture.
- M24.5 (SESSION_184, folded) — CI
  validation + capability matrix §7y
  + retrospective + M25 skeleton +
  IMPLEMENTATION_ROADMAP amendment
  (this section) + coordinated push
  per M18.6 / M19.6 / M20.5 / M21.5 /
  M22.4 / M23.4 cadence.

**Non-goals deferred from M24 (see
`MILESTONE_24_RETROSPECTIVE.md` §3 + §4):**
- `<RecordTestDriveForm>` component +
  attachment on `DealerAiSalesTestDrives`
  (§3 deferral 12). Recorded as M25
  Candidate O2 sub-scope.
- `referrer_id` / "Referred by" display
  in `LeadDetailModal` (§3 deferral 13).
  Recorded as M25 small UI extension
  candidate.
- `platform` display in `LeadDetailModal`
  for webhook-origin leads (§3 deferral
  14). Bundle with #13.
- Manual webhook payload entry UI —
  deferred without scheduled re-entry
  per §3 deferral 1 (webhook is system-
  to-system integration boundary; no
  repository/research-corpus evidence
  supports operator payload entry).
- Named-platform webhook adapters
  (Autotrader, Cars.com, CarGurus,
  Facebook Marketplace) — deferred per
  §3 deferral 3.
- Test-hygiene remediation across pre-
  existing shared-DB non-idempotent
  journeys (Candidate H reinforcement
  from M24.1 close) — elevated as M25
  candidate.
- All M23 §3 carry-forward deferrals
  still valid.

### Milestone 25 — Lead-to-Test-Drive Operational Completion — SHIPPED at SESSION_187

**Sessions:** SESSION_185 → SESSION_187 (M25.3 close-out folded
into M25.2 per §5.h evidence-sized Option B).
**Anchor business question:** *Can a salesperson receive a lead,
understand exactly where it came from, assign it, and schedule
the customer's test drive entirely through the normal product
workflow?*

**Increments:**

- **M25.0 (SESSION_185)** — planning refinement + all eight §5
  locks. Full active memo at `MILESTONE_25_PLANNING.md`.
  Commit `4e0a958`.
- **M25.1 (SESSION_186)** — attribution display + JSONField
  backend addition. `CustomerLead.source_metadata` +
  `get_source_platform()` accessor + migration 0049.
  `CustomerLeadSerializer` additive extension (channel /
  referrer / referrer_name / source_metadata).
  `record_webhook_lead` writes source_metadata at intake.
  `LeadDetailModal` Source section. Extended M24.3 + M24.4
  Playwright journeys. Closes M24.1-open §3 deferrals 13 +
  14. Commit `368fe37`.
- **M25.2 (SESSION_187)** — test-drive UI + admin vehicle list
  endpoint. New `GET /admin/vehicles/` endpoint (M11.6
  precedent). `<RecordTestDriveForm>` component modal-only
  per §5.d. New Playwright journey `lead_to_test_drive.
  spec.ts`. Closes M24.1-open §3 deferral 12. Commit
  `27cbe87`.
- **M25.3 close-out folded** into M25.2 session
  (retrospective + audit rerun + roadmap update + M26
  handoff + coordinated push).

**Ships:**

- One additive backend migration (`0049_customerlead_
  source_metadata`).
- One new backend endpoint (`admin/vehicles/`).
- One new backend serializer method
  (`get_referrer_name`) + four additive serializer fields.
- One additive service-verb kwarg (`record_webhook_lead`
  writes `source_metadata`).
- One new frontend component
  (`frontend/src/components/sales/RecordTestDriveForm.tsx`).
- One new frontend API wrapper (`listAdminVehicles`).
- Two additive frontend type surfaces (`AdminVehicleRow`
  interfaces + `LeadDetailResponse.lead` attribution
  fields).
- One new deterministic acceptance seed fixture
  (`M25-TEST-DRIVE-01` Vehicle).
- One new Playwright journey +
  two extended journey assertions.

**Baselines at close:**

- Backend: **4,793 pass** (+13 across M25).
- Frontend: **226 pass** (+17 across M25).
- Acceptance: **14 journeys** (13 → 14); full clean-DB run
  20 passed (~30s).
- Migrations: **0049**.
- Zero-drift permission-class streak: **25** (M10 → M25).
- Planning-time as-recommended streak: **3** at M25.2 close
  (fresh counter from M24.0).
- Audit artifact: 154 endpoints, 114 covered / 40
  backend-only (reality is 116 / 154 — see M25
  retrospective §4 for the pre-existing audit-script
  trailing-optional-querystring template gap surfaced
  during M25.3).

**Non-goals for M25 (all held):**

- Secondary "+ Record test drive" launch on
  `DealerAiSalesTestDrives` — deferred per §5.d
  "one operational workflow beats two overlapping ones"
  durable principle.
- Clickable/navigable "Referred by" attribution link —
  deferred per §5.c display-only lock.
- Test-drive edit/delete UI — deferred per M11.2
  subsidiary-log design.
- Named-platform adapters (Autotrader/Cars.com/etc.) —
  JSONField substrate ready when needed.
- Analytics/rollup surfaces on attribution — JSONField
  query support enables later.
- Vehicle picker advanced filters (year/make/model
  dropdowns) — search substring suffices in M25.2.
- Structured objection vocabulary lookup — free-text list
  per M11.2.
- Test-drive scheduling in advance vs post-drive
  recording — M11.2 driven_at defaults to timezone.now();
  form override supported.
- All M24 §3 carry-forward deferrals still valid except
  12 + 13 + 14 (closed by M25).

---

### Milestone 26 — Audit-Script Parser Refinement (Planning-Substrate Integrity) — SHIPPED at SESSION_190

**Sessions:** SESSION_189 → SESSION_190 (M26.2 close-out folded
into M26.1 per §5.h evidence-sized Option B — no code
discrepancies at any §5.d checkpoint).
**Anchor business question:** *Can future milestone selection
rely on the operational-surface audit as trustworthy coverage
evidence?* (A prerequisite to the durable operational-coverage
guiding question, not a departure from it.)

**Increments:**

- **M26.0 (SESSION_189)** — planning refinement + target
  selection + all eight §5 locks under the planning-substrate
  integrity re-framing. Full active memo at
  `MILESTONE_26_PLANNING.md`. Commit `8bb588f`.
- **M26.1 (SESSION_190)** — parser fix + regression suite +
  audit regeneration + doc updates + M26.2 close-out fold.
  `_extract_balanced_template_literal` extracted as shared
  substrate; `extract_frontend_consumers` post-match
  refinement added for nested-template-literal tokenization.
  12 regression tests (5 positive + 7 negative) in new
  `test_audit_operational_surface.py`. Audit regenerated:
  114 / 154 → 119 / 154 covered. §5.d Phase 2 per-row
  verification pass. §5.e two-source agreement confirmed.
  M26.1-open empirical refinement: row 5
  `vehicles/<int:vehicle_id>/` reclassified as separate
  `getJSON` public-helper defect and deferred to M27+.

**Ships:**

- One narrow audit-script parser fix
  (`backend/dealer_ai/scripts/audit_operational_surface.py`):
  new `_extract_balanced_template_literal` companion; existing
  `_extract_url_literals` refactored to delegate to it;
  `extract_frontend_consumers` post-match refinement branch.
- One new regression test file
  (`backend/dealer_ai/tests/test_audit_operational_surface.py`)
  with 5 positive + 7 negative test methods.
- One regenerated audit artifact
  (`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`): 5 rows
  flip `defer-candidate-O2` → `covered` (rows 7, 16, 29, 111,
  121); coverage summary 114 → 119; per-module backend-only
  counts update; row 42 cosmetic wrapper-order.
- Zero backend views / models / migrations / serializers /
  permission classes / urls.py touched.
- Zero frontend components / API wrappers / types touched.
- Zero acceptance journeys added or extended (§5.g exception
  path invoked: audit-tooling is not operator-facing).

**Baselines at close:**

- Backend: **4,805 pass** (+12 across M26.1 regression suite).
- Frontend: **226 pass** unchanged.
- Acceptance: **14 journeys** unchanged.
- Migrations: **0049** (unchanged).
- Zero-drift permission-class streak: **26** (M10 → M26).
- Planning-time as-recommended streak: **5** at M26.1 close
  (extends M25 close streak of 3 through M26.0 + M26.1;
  historical run of 89 across M10 → M23 preserved).
- Audit artifact: **154 endpoints, 119 covered / 35
  backend-only** (was 114 / 40 pre-fix; the 5-endpoint
  reclassification is the mechanical result of the parser
  fix; §5.d two-source agreement confirms these are the true
  coverage numbers, not audit-tooling artifacts).

**Non-goals for M26 (all held):**

- Row 5 `vehicles/<int:vehicle_id>/` public-fetch-helper
  regex refinement — separate defect (public `getJSON` not
  enumerated in `_HELPER_CALL_RE`); NEW M27+ candidate.
- Plain-string-literal false-positive investigation on
  rows 1–4 (`chat/start/`, `chat/message/`,
  `chat/session/<uuid:session_id>/`, `leads/`) — surfaced
  at SESSION_189 §3 but out of M26 scope per user
  constraint; M27+ candidate.
- Test-hygiene remediation (Candidate H) — kept separate
  from M26 per user constraint; live M27+ candidate.
- A2 (JE creation UI) — kept elevated as leading M27
  §5.a direct operator-coverage candidate per user
  constraint at M26.0 open.
- Endpoint disposition changes unrelated to the five
  mechanical reclassifications — `recommend_disposition()`
  heuristic out of scope per §3.
- Audit script rewrite / restructure — narrow parser fix
  only; broader refactor deferred pending evidence.
- Audit output format changes — row shape, disposition
  legend, coverage summary format all unchanged.
- No operator-facing surface change — M26 is
  audit-script-only per the planning-substrate integrity
  framing.

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
