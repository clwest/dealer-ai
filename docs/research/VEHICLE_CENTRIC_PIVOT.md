---
title: "Vehicle-Centric Operating System — Scoping & Execution Plan"
status: proposed
last_updated: 2026-07-31
baseline_commit: 51db6a4
phase_0_completed_commit: TBD  # Tenancy + auth foundation
phase_1_completed_commit: TBD  # Investment ledger
phase_2_completed_commit: TBD  # Condition report
phase_3_completed_commit: TBD  # Recon automation
phase_4_completed_commit: TBD  # Lifecycle stages + retail gating
phase_5_completed_commit: TBD  # Photography + listing generation
phase_6_completed_commit: TBD  # Async infrastructure (Celery)
phase_7_completed_commit: TBD  # Operational intelligence
phase_8_completed_commit: TBD  # Sale + delivery + post-sale
target_persona: Copper Canyon Auto (Yuma, AZ) — inherits from INDEPENDENT_DEALER_PIVOT
---

# Vehicle-Centric Operating System — Scoping & Execution Plan

> **Reframe (2026-07-31).** The Dealer AI Kit is no longer primarily
> an AI sales assistant. It becomes a **dealership operating system**
> in which every stock number is a living operational record from
> acquisition through sale, and the AI is one capability among many
> — the glue that reduces repetitive work while humans retain
> authority over business decisions.
>
> This doc is the **living plan** for that pivot. It is sibling to
> `INDEPENDENT_DEALER_PIVOT.md` (which established the Copper Canyon
> indie persona) and inherits its guardrails. Update the `status:`
> field and the `phase_N_completed_commit:` fields as phases ship.

---

## The core reframe (operator's view)

Today the platform's center of gravity is the **conversation**. A
chat comes in, we match it to inventory, we route it to a lead. The
`Vehicle` model is a card the chat holds up.

The pivot makes the vehicle the center of gravity. Every stock
number becomes a living operational record with a **lifecycle**
(where it is right now), a **ledger** (what we've put into it), and
a **condition report** (what still has to happen). The chat, the
leads, the ad copy — all of that becomes **downstream** of the
vehicle record.

- When a stock number reaches `stage=frontline`, it becomes eligible
  for chat matching.
- When it hits `stage=sold`, the CRM side of the record activates.

The AI's job also shifts: from **primary product** to **operational
glue**. It drafts vendor emails, drafts purchase orders, drafts
listing copy, summarizes condition reports into work plans, detects
aging anomalies. It never authorizes. The human still runs the
store.

**The moat doesn't change.** The 16-stage guard/scrub stack
(dealer-cost, invented-inventory, invented-promotion,
fake-negotiation, etc.) remains the crown jewel — and every new
AI-drafted artifact (vendor email, PO, listing) MUST pass through
it. Day 1 discipline, not a Phase 7 concern.

---

## Core principle — the two questions

Every feature in this plan should make the software better at
answering these two questions for any stock number:

1. **What do we have invested in this vehicle right now?**
2. **What still needs to happen before this vehicle is front-line ready?**

If a proposed feature does not sharpen the answer to one of those,
it does not belong in this pivot.

---

## Vehicle lifecycle (canonical stages)

The unified workflow spans the vehicle's entire life on the lot.
Not every stage is enforced as a state-machine transition — some
are advisory — but every stage is representable in the data model.

| # | Stage | Enters when | Exits when |
|---|-------|-------------|------------|
| 1 | `acquisition` | Purchase recorded | Transport dispatched |
| 2 | `transport` | Transport dispatched | Arrival confirmed |
| 3 | `inspection` | Arrival confirmed | ConditionReport marked complete |
| 4 | `recon` | ConditionReport has ≥1 finding at severity `recommended` or higher | All `required`/`safety` WorkOrders complete |
| 5 | `qc` | Recon complete | QC checklist passed (manual flip) |
| 6 | `detail` | QC passed | Detail complete (manual flip) |
| 7 | `photography` | Detail complete | ≥ N photos uploaded (configurable per dealer) |
| 8 | `listing` | Photo threshold met | Listing published + price > 0 |
| 9 | `frontline` | Listing published + price > 0 | Sale record created |
| 10 | `sold` | Sale record created | Delivery record created |
| 11 | `delivered` | Delivery record created | (terminal) |
| 12 | `archived` | Sale reversed / vehicle written off | (terminal) |

**Retail eligibility rule:** `search_vehicles()` filters on
`stage='frontline'`. Today it filters on `is_available=True`. That
one-line change — reframing `is_available` as a computed property
that returns `stage == 'frontline'` — is the single most important
integration point between the operational side and the retail chat.

---

## Condition report contract

The condition report is **human-authored**. The AI never invents
inspection results. It only reacts to structured human input.

### Categories the schema must support

Mechanical repairs · cosmetic repairs · body work · glass · tires ·
interior · fluids · electrical · safety concerns · accessories ·
missing items · dealer-defined categories.

### Severity levels

- `advisory` — noted, no action required.
- `recommended` — should be addressed, not blocking sale.
- `required` — must be addressed before frontline.
- `safety` — must be addressed before frontline, higher priority.

### What the AI IS allowed to do with condition data

- Summarize findings into a proposed recon work plan.
- Suggest vendors for a category based on ledger history.
- Draft parts orders, purchase orders, vendor emails, vendor SMS.
- Group similar findings across the fleet ("3 units need tires this week").
- Estimate cost based on historical averages from the ledger.

### What the AI is NEVER allowed to do

- Invent a finding.
- Change a severity.
- Modify a technician's description.
- Send anything (emails, SMS, POs) without human approval.

---

## Investment ledger scope

Every stock number maintains a continuously-updated ledger. The
ledger must always answer:

- Total investment
- Recon investment
- Estimated remaining investment
- Expected gross
- Projected gross
- Net profitability

### Line-item categories the schema must support

**Acquisition**
- Purchase price · auction fees · transportation · broker fees ·
  arbitration fees · title acquisition.

**Banking / flooring**
- Floor plan fees · interest · wire fees · banking fees ·
  merchant fees · curtailments.

**Reconditioning**
- Parts · mechanical labor · tires · brakes · battery · oil
  service · diagnostics · glass · body work · paint · upholstery
  · wheel repair · detail · photography.

**Administrative**
- Fuel · listing fees · advertising allocation · registration ·
  title work · shipping · miscellaneous dealer expenses.

### Ledger safety discipline

Ledger data is **more sensitive than dealer-cost strings the chat
already scrubs**. A new post-LLM scrub — the **"acquisition-price
scrub"** — is added as belt-and-suspenders in Phase 1 to catch any
accidental leakage of ledger figures into customer-facing chat.

---

## Recon automation contract

Once a condition report is complete, the system automatically
proposes a work plan. Every action below is **drafted** by the AI
and **approved** by a human before it takes effect.

- Identify required replacement parts.
- Search suppliers, compare pricing, compare availability.
- Recommend vendors (ranked by historical turn time + cost from the
  ledger).
- Prepare purchase orders.
- Schedule outside vendors.
- Draft emails and text messages.
- Notify internal departments.
- Estimate completion dates.
- Track outstanding work.

**On WorkOrder.status → complete + actual_cost recorded:** the
system auto-mints a `VehicleCost` ledger entry. This is how the
recon side and the ledger side stay in sync without double entry.

---

## Operational intelligence (long-term)

The long-term opportunity is not more AI chat. It is dealership
intelligence emerging from operational data no competitor has.

Questions the platform should answer once Phases 1–7 have shipped:

- Which auctions consistently produce the highest recon costs?
- Which vendors finish fastest? Which are most cost-effective?
- Which vehicle types produce the highest profit?
- Which repairs are consistently underestimated?
- Average recon days by vehicle category.
- Recon bottlenecks (p50 / p95 days per stage).
- Average cost per repair type.
- Time from acquisition to frontline.
- Inventory aging trends.
- Gross profit trends.

**No ML required.** These are SQL aggregations over the ledger,
work orders, stage events, and sales.

---

## Alignment with the current architecture

The current Dealer AI Kit already contains meaningful foundations
for this pivot. In priority order:

| Existing asset | Fit |
|---|---|
| `Vehicle.stock_number` (unique, at `backend/dealer_ai/models.py`) | Correct primary identity. Ready to hang lifecycle + ledger off. |
| `Vehicle.vin`, `imported_at`, `last_seen_at`, `source` | Basic provenance already there. `source` becomes the auction/wholesale/trade-in classifier. |
| `services/inventory_import.py` (upsert-by-stock, per-source scoping) | Exactly the shape auction-feed adapters (Manheim, ADESA, ACV) will need. Refactor CSV parser into a `Source` adapter; keep the upsert core. |
| `DealerOnboardingProfile` shape-of-business (SESSION_032) | `floor_plan_lender`, `warranty_offering`, `credit_range_served`, `subprime_lenders`, `makes_carried`, `bhph_enabled` — **default sources for ledger entries and vendor defaults**. `floor_plan_lender` → who your daily interest accrues to. |
| `services/payment_engine.py` (BHPH weekly/biweekly + APR math) | Same math computes daily floor-plan interest accrual. Zero new math needed. |
| `services/dealer_config.py` resolver (DB → env → default) | Right shape for per-vehicle overrides later (e.g. "vendor for glass in Yuma"). |
| `services/pipeline.py` recommended-actions generator | Generalizes cleanly to "recommended recon actions" — units aging in a stage, work orders past estimate, condition reports overdue. |
| `services/ad_copy.py`, `services/follow_up.py` (LLM + scrub for drafts) | Direct reuse for **listing copy**, **vendor emails**, **PO drafts**, **work-order narratives**. Same scrub stack, new prompt scaffolding. |
| `services/llm_safety.py` scrub stack | Non-negotiable Day 1 dependency for every new AI-drafted artifact. |
| `services/audit.py` | Extend to log every recon decision, every vendor selection, every stage transition. Operator legal defensibility. |

---

## Structural changes required

Honest — bounded but not free.

1. **`Vehicle.is_available: Boolean` is too coarse.** Chat matches
   on `is_available=True`. Recommended: keep `is_available` as a
   computed property returning `stage == 'frontline'`. One-line
   ripple through `inventory_search.py`, `chat_engine.py`,
   `vehicle_assistant.py`.

2. **`Vehicle` model will bloat.** 15 fields today, 30+ if we jam
   lifecycle + acquisition + listing on. Recommended: keep
   `Vehicle` as identity + descriptive facts (VIN, YMM, features).
   Factor out `VehicleAcquisition` (OneToOne), `VehicleListing`
   (OneToOne), `VehicleStage` (OneToOne with audit trail via
   `VehicleStageEvent`).

3. **`CustomerLead.interested_vehicles` M2M has no annotation.**
   Once vehicles have stages, we need "when did they become
   interested" and "what stage was the vehicle at that moment."
   Requires a `LeadVehicleInterest` through-model.

4. **No permission system.** Recon staff should see the ledger;
   the porter shouldn't; the customer never can. Role-based
   access is required **before** ledger data goes live.

5. **`DealerOnboardingProfile` is a singleton row.** Every new
   operational model needs a `dealership` FK or a schema-per-tenant
   story. **Introduce a `Dealership` model in Phase 0**, even
   with one row, and add FKs to everything as you go. Retrofitting
   tenancy later is 10× the work.

6. **File storage is one-logo-deep.** `default_storage` works for
   a single logo. Multi-photo inspection galleries + vehicle
   listings need S3-compatible + CDN, configured via env.

7. **No API auth.** Every endpoint is public. Advisor workspace
   is slug-by-obscurity (flagged in `CAPABILITY_MATRIX.md`). The
   pivot moves auth from a "Phase 5 debt" to a **Phase 0 blocker**.

---

## New domain models (recommended)

Every new model carries a `dealership` FK once the Phase 0 tenancy
model lands.

**Identity & tenancy**
- `Dealership` — single-row today, multi-row-ready.

**Acquisition**
- `VehicleAcquisition` (1:1 Vehicle) — source (auction/trade/
  wholesale/private), source_detail (which auction, run/lane),
  purchase_price, purchase_date, buyer_fees, arbitration_fees.

**Investment ledger**
- `VehicleCost` — vehicle FK, category (~25 enum values across
  acquisition/flooring/recon/admin), amount, incurred_at, vendor
  FK (nullable), reference (invoice/PO #), notes, is_estimate.

**Condition & recon**
- `ConditionReport` — vehicle FK, inspected_by, inspected_at,
  status (draft/complete), notes. Human-authored, always.
- `ConditionFinding` — report FK, category (mechanical/cosmetic/
  body/glass/tires/interior/fluids/electrical/safety/accessories/
  missing/other), severity (advisory/recommended/required/safety),
  description, estimated_cost, photos.
- `Vendor` — name, categories (M2M or JSON), contact, address,
  active, avg_turn_days (computed).
- `WorkOrder` — vehicle FK, condition_finding FK (nullable),
  category, vendor FK (nullable), status (draft/approved/sent/
  in_progress/complete/canceled), estimated_cost, actual_cost,
  estimated_completion, actual_completion, notes. On
  `status=complete`, auto-mint a `VehicleCost` entry.

**Photography & listing**
- `VehiclePhoto` — vehicle FK, image (FileField), order,
  alt_text, category (exterior/interior/mechanical/damage/
  feature/VIN/odometer), uploaded_at, uploaded_by.
- `VehicleListing` (1:1 Vehicle) — headline, body, published,
  published_at, generated_by (human / AI-drafted-human-approved).

**Lifecycle**
- `VehicleStage` (1:1 Vehicle) — current stage (enum from the
  lifecycle table above), entered_at.
- `VehicleStageEvent` — vehicle FK, from_stage, to_stage,
  entered_at, by (user), trigger (manual/deterministic-rule),
  notes.

**Sale & delivery** (closes the loop back to CRM)
- `Sale` — buyer (CustomerLead FK), vehicle FK, sale_date,
  sold_price, finance_type (cash/retail/BHPH), lender,
  gross_realized (computed: sold_price - VehicleCost.total).
- `Delivery` — sale FK, delivery_date, checklist (JSON),
  temp_tag_number.

---

## Workflow / state-machine changes

**Recommendation:** don't adopt a heavyweight framework
(django-fsm, transitions). Use a **thin service module** —
`services/vehicle_lifecycle.py` — with pure functions like
`advance_stage(vehicle, to_stage, actor, reason)`. Same pattern
as `services/dealer_config.py`. The test suite is the contract,
not a state framework. Proven testable pattern already established.

**Deterministic transitions (system-suggested, human-approved):**
- `inspection → recon` when a `ConditionReport.status=complete`
  has ≥1 finding at severity `recommended` or higher.
- `recon → qc` when all WorkOrder at severity `required`/`safety`
  are `status=complete`.
- `photography → listing` when `VehiclePhoto.count ≥ N`
  (configurable per dealer).
- `listing → frontline` when `VehicleListing.published=True` AND
  `Vehicle.price > 0`.
- `frontline → sold` when a `Sale` record is created.

**Manual transitions:** `qc → detail`, `detail → photography`,
and any override. All logged to `VehicleStageEvent`.

---

## Reusable code (do not rebuild)

- `services/llm_safety.py` — every drafted artifact runs through
  it. Non-negotiable.
- `services/inventory_import.py` — upsert / soft-unavailable
  logic → auction adapter foundation.
- `services/payment_engine.py` — reuse APR math for floor-plan
  interest accrual.
- `services/dealer_config.py` resolver — reuse for per-vehicle
  overrides.
- `services/pipeline.py` — recommended-actions generator
  generalizes to recon.
- `services/ad_copy.py`, `services/follow_up.py` — drafting
  patterns for listing / vendor email / PO / work order.
- `services/audit.py` — extend to operational decision log.
- `services/handoff_service.py` — pattern reusable for
  recon-handoff packets (assign work order to vendor with all
  context).
- Post-LLM scrub tests (`tests/test_post_llm_safety.py`) — the
  model for how recon-side drafting gets tested.

---

## Technical debt to pay down FIRST

Do these in order. Skipping any of them will hurt within one
release.

1. **Introduce `Dealership` FK-carrier model** (even single-row).
   Every new model in Phases 1+ carries the FK. Retrofitting is
   brutal.
2. **Real auth + role-based permissions.** At minimum:
   `dealer_owner`, `sales_manager`, `recon_manager`, `advisor`,
   `porter`. Ledger + costs scoped to owner / managers. Zero auth
   exists today.
3. **File storage story.** S3-compatible + CDN. Configured via
   env. Before `VehiclePhoto` ships.
4. **`Vehicle.is_available` → computed property.** One-line
   change with test-suite ripple. Do it before adding stages so
   the pattern is proven.
5. **Rename `Vehicle.make` default.** `default="Ford"` at
   `models.py:11` is a franchise leftover from before the
   SESSION_030 pivot; harmless today but confusing in a schema
   built around stock items.
6. **Deploy the backend.** Currently local-only per
   `CAPABILITY_MATRIX.md:302`. Recon/ledger is worthless if the
   operator can't reach it from the lot on a phone.

---

## Phased implementation roadmap

Sequenced to prove ROI on **Phase 1 alone** — the investment
ledger is the single feature an operator would pay for tomorrow,
standalone.

### Phase 0 — Tenancy + auth (foundation, no user-visible feature)

Weeks 1–2. `Dealership` model + FK migrations, real auth
(Django's built-in + DRF tokens), role-based permissions. Nothing
to demo except "the ledger endpoint refuses unauthenticated
requests." Required before Phase 1.

### Phase 1 — Investment ledger (highest-ROI standalone feature)

Weeks 3–5. `VehicleAcquisition`, `VehicleCost`, computed
properties on Vehicle (`total_investment`, `expected_gross`,
`projected_gross`). New API: `GET/POST /vehicles/<id>/costs/`,
`GET /vehicles/<id>/ledger/`. New UI page:
`/dealer-ai-inventory/<stock>/ledger`. Add the new post-LLM
**"acquisition-price scrub"**. Ship a floor-plan-interest daily
accrual (manual re-run for now — no Celery yet).

**Demo test:** an operator can enter a $18,500 auction buy, $850
transport, $200 broker fee, and see *"$19,550 in it; asking
$24,900; projected gross $5,350."* That's the first day the
product is worth selling standalone to another dealer.

### Phase 2 — Condition report (structured operational data)

Weeks 6–8. `ConditionReport` + `ConditionFinding`.
Human-authored inspection form. Multi-photo upload per finding
(requires file storage from Phase 0). AI role: NONE yet.
Deliberately un-automated so the data shape gets proven before
automation lands on top.

### Phase 3 — Recon automation (first AI role in the OS)

Weeks 9–12. `Vendor`, `WorkOrder`. AI **drafts** work orders
from findings, **suggests** vendors (ranked by historical turn
time + cost from the ledger), **drafts** emails/SMS to vendors.
Human approves everything. On WorkOrder complete → auto-mint
VehicleCost. This is where the pivot's promise — "AI reduces
repetitive work" — becomes visible. New scrub added:
**"invented-recon-fact scrub"** (mirrors `invented_promotion`
from `ad_copy.py`).

### Phase 4 — Lifecycle stages + retail gating

Weeks 13–14. `VehicleStage`, `VehicleStageEvent`, deterministic
transitions, manual overrides. **Flip `search_vehicles` to
require `stage='frontline'`.** This is where the retail chat
becomes a natural downstream consumer of the operational data.

### Phase 5 — Photography + listing generation

Weeks 15–17. `VehiclePhoto` gallery, bulk upload, reorder.
`VehicleListing` model. AI drafts listing copy (reusing
`services/ad_copy.py` scrub stack), operator approves. On
listing publish → stage auto-advances to `listing`.

### Phase 6 — Async infrastructure (Celery, finally justified)

Weeks 18–19. Celery + Redis. Jobs: daily floor-plan interest
accrual, aging reports, vendor SLA warnings, photo processing.
Do not adopt Celery earlier. Nothing to run yet.

### Phase 7 — Operational intelligence

Weeks 20–24. SQL aggregations over ledger, work orders, stage
events, sales. Auction ROI, vendor performance, stage
bottlenecks, repair unit economics, aging trends. New endpoints
under `/admin/intelligence/*`. No ML. This is where "dealership
intelligence" becomes real and defensible — proprietary
operational data no competitor has.

### Phase 8 — Sale + delivery + post-sale (closes the loop)

Weeks 25–27. `Sale`, `Delivery`. Ties `CustomerLead` → vehicle
counterparty. `gross_realized` becomes the truth ledger against
`projected_gross`. Post-sale document attachment.

---

## Guardrails (do NOT lists)

**Inherited from `INDEPENDENT_DEALER_PIVOT.md`:**

- ❌ Do NOT delete the franchise config path.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Dealer OS"
  / Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts. 1300-test baseline
  must stay green.
- ❌ Do NOT delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` or
  `public/sams-freedom-ford-logo.jpg`.
- ❌ Do NOT do dep-major upgrades concurrent with feature work.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

**Added by this pivot:**

- ❌ Do NOT ship any ledger endpoint before Phase 0 auth lands.
  Ledger data is more sensitive than any string the existing
  scrub stack protects.
- ❌ Do NOT let the AI author condition findings. Humans
  author; AI reacts.
- ❌ Do NOT let the AI send anything (emails, SMS, POs) without
  human approval. Draft-only.
- ❌ Do NOT add new AI-drafted artifacts (vendor email, PO,
  listing) without wiring them through `services/llm_safety.py`.
- ❌ Do NOT adopt Celery before Phase 6. Premature async
  infrastructure is a maintenance tax with nothing to run.
- ❌ Do NOT build a monolithic single-role UI. Role-scope every
  view (recon manager, sales manager, owner, advisor, porter).

---

## Two pushbacks worth remembering

Recorded here for future sessions that might drift.

**1. "Every stage should be part of a unified workflow rather
than disconnected modules"** — agreed on data model, but resist
a single monolithic UI. Recon staff, sales staff, and the owner
want radically different views of the same vehicle. Build one
canonical **Vehicle Detail Operator View** (all lifecycle +
ledger + condition + work orders + photos + listing + chat
history), but let each role see a role-scoped subset. Otherwise
the recon manager drowns in chat transcripts and the salesperson
drowns in vendor emails.

**2. "The AI should never invent inspection results"** — 100%
agreed, and extend the rule: the AI should never invent
**vendors, prices, availability, ETAs, or vehicle-history facts
either.** Every AI-drafted artifact must trace every claim back
to a ledger entry, condition finding, vendor record, or
supplier API response.

---

## Related docs

- `docs/research/INDEPENDENT_DEALER_PIVOT.md` — the SESSION_030+
  indie-persona pivot that this plan sits on top of.
- `docs/CAPABILITY_MATRIX.md` — verified capability matrix (what
  the platform actually does today).
- `docs/PROJECT_PIPELINE.md` — current request-flow map (entry
  points, guards, scrubs, state surfaces).
- `docs/DEALER_KIT_BEHAVIOR_LAYER.md` — voice / tone / constraint
  contract that all AI output must honor.
- `docs/DEALER_KIT_TRANSLATION_LAYER.md` — per-audience
  translation contract.

## Anchors that win on conflict

If anything in this plan disagrees with reality:

1. The 1300-test backend baseline is the behavior contract.
2. `docs/CAPABILITY_MATRIX.md` is the verified-capability
   snapshot.
3. `git log --oneline -25` (what actually shipped).
4. `git show HEAD:<path>` (current source).

Narrative plans are claims. Code and handoffs are facts.
