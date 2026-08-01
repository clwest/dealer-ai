---
title: "Milestone 2 — Implementation-Planning Pass"
status: planning
type: planning-artifact
generated: 2026-07-31
generated_at_session: SESSION_045 (pre-implementation)
milestone: 2
milestone_name: "Vehicle investment ledger"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_1_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_1_PLANNING.md
  - docs/BUSINESS_DOMAIN_MAP.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/INVENTORY_ACQUISITION_MAPPING.md
  - docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
supersedes: none
applies_to:
  - SESSION_046+ Milestone 2 implementation sessions
  - Any subsequent session that resumes Milestone 2
---

# Milestone 2 — Implementation-Planning Pass

> **What this is.** The planning artifact produced before Milestone 2
> implementation begins. Mirrors the shape that
> `MILESTONE_1_PLANNING.md` proved out: engineering practices to
> preserve (§0), design memo (§1), migration impact review (§2),
> compatibility checklist (§3), reusable-primitive review (§4),
> scope discipline + deferrals (§5), anchors (§6), increment
> sequencing (§7).
>
> **Why this exists.** Milestone 2 introduces the first sensitive
> operational data the platform has ever held — the per-vehicle
> investment ledger. Every dollar figure captured here is more
> sensitive than any string the 16-stage scrub stack currently
> protects. The blast radius is smaller than Milestone 1
> (greenfield tables, not retrofit FKs across every carrier), but
> the *sensitivity* of what's held is higher. Confirming the plan
> and the compatibility invariants before touching code is the
> difference between a clean milestone and a leak incident.
>
> **Precedence.** The six rules of `docs/PROJECT_RULES.md` override
> anything in this doc. The scope boundary of
> `IMPLEMENTATION_ROADMAP.md` §Milestone 2 overrides anything in
> this doc. The layer discipline in `AUTHENTICATION_MODEL.md` §1
> overrides anything in this doc.
>
> **How to use it.** Read all sections before writing code. Use the
> compatibility checklist (§3) as the acceptance test — Milestone 2
> is not complete until every checklist item verifies true, with
> evidence recorded inline the way Milestone 1's §3 was annotated
> at close.

---

## 0. Engineering practices to preserve from Milestone 1

Not philosophy — the engineering process Milestone 2 inherits from
the Milestone 1 retrospective (`MILESTONE_1_RETROSPECTIVE.md` §6).
Every increment session should be able to point at these and say
"we did this."

1. **Small implementation increments with independent verification
   points.** M1 split Increment 4 into 4A–4F precisely because a
   monolithic auth increment would have been high-blast-radius work
   with poor rollback granularity. M2 plans 3 increments (§7); each
   ends with the app deployable and the test baseline healthy.
2. **Compatibility-first thinking.** Every M1 session verified the
   §3 checklist before landing new code. M2's §3 enumerates every
   M1 invariant (tenancy, auth, scrub stack, payment engine,
   franchise env-override) that M2 must uphold. Verified inline at
   milestone close, never by inference.
3. **Migration-before-constraint sequencing.** M1 lesson 1:
   nullable FK → backfill → write-path plumbing → `NOT NULL`.
   M2's greenfield tables don't need the four-step dance (no
   existing rows to backfill), but the *principle* — never land
   a NOT NULL constraint that a live writer could violate — carries
   forward for every additive field the ledger surfaces.
4. **Dedicated migration-check DB alias.** M1 lesson 2: SESSION_038
   wiped ~200 rows of demo data when it verified
   `migrate dealer_ai zero` → `migrate` against the actual dev DB.
   M2 introduces two new tables plus a management command that
   writes to them; set up `DATABASES["migration_check"]` **before**
   the first destructive verification run.
5. **Extend existing primitives over parallel implementation.**
   M1 lesson 4 formalized the four-layer separation (identity /
   tenancy / permissions / data scoping). M2 extends the Vehicle
   model (new related tables), the payment engine (daily accrual
   math), the scrub stack (new `SafetyKind`), the dealer_config
   resolver (new fields), the permissions module (new composed
   classes). Zero parallel implementations.
6. **Clear layer separation.** M1 lesson 4: identity, tenant scope,
   business permissions, and data scoping are separate concerns
   living in separate files. Every ledger write path threads
   `dealership=get_current_dealership(request)` explicitly at the
   view layer. `.filter(dealership=...)` stays visible in views —
   no hidden ORM manager magic. The `pre_save` autofill signal
   remains a fallback, never a primary write path (this is called
   out in `AUTHENTICATION_MODEL.md` §8b and reinforced in the M1
   retrospective §6 lesson 3).
7. **Focused permission matrices over oversized integration
   tests.** M1 lesson 5: each endpoint family shipped with a
   permission-matrix test class enumerating six required outcomes
   (unauth, wrong-role, wrong-tenant, correct owner, correct
   sales_manager, and — where applicable — correct advisor). M2
   applies the same shape to every new endpoint.
8. **Documentation discipline.** Handoffs are immutable. Session
   ends produce `docs/handoffs/SESSION_NNN_<slug>.md`.
   `00-START-NEXT-SESSION.md` is overwritten, not appended-to.
   `MILESTONE_2_PLANNING.md` (this file) gets annotated in-place
   at milestone close with the shipped evidence — mirroring the
   pattern `MILESTONE_1_PLANNING.md` §3 established.

Rule of thumb for every M2 session: if an increment can't be
described in one sentence that names the shipped surface and the
locked invariant, it is too large.

---

## 1. Design Memo

Every entry answers **the same three questions** in this order:
what business question does this subsystem answer? which existing
primitive does it extend? what does it leave untouched?

**Start with the questions, not the models.** The ledger exists
because the buyer standing at auction next Tuesday needs to answer
"what have we already got tied up on stock #F25-014?" before
deciding whether to bid $18k or walk away. The data model exists
to support that answer. If a proposed field or endpoint does not
sharpen one of the questions below, it does not belong in
Milestone 2.

### 1.0 The operational questions Milestone 2 must answer

Six questions, each traced to the research corpus. These are the
acceptance test for whether the milestone shipped the right thing.

| # | Question | Research citation |
|---|----------|-------------------|
| 1 | **How much money do we have invested in this stock number right now?** | `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.12 ("what have we got in this piece?"); `VEHICLE_CENTRIC_PIVOT.md` §Investment ledger scope. |
| 2 | **What is today's true cost basis by category (acquisition / flooring / recon / admin)?** | `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.2, §2.7, §2.12; `INVENTORY_ACQUISITION_MAPPING.md` §4.2. |
| 3 | **What is the projected front-end gross if we sell at the current asking price?** | `INVENTORY_ACQUISITION_MAPPING.md` §3.6 (gross projection); `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.14 (`Vehicle Gross = Sale Price − Total Cost`); VCP Phase 1 demo test (*"$19,550 in it; asking $24,900; projected gross $5,350"*). |
| 4 | **How many days has this vehicle been sitting, and how much floor-plan interest has accrued against it?** | `INVENTORY_ACQUISITION_MAPPING.md` §5, §5.5 (curtailment planning); `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.5 ("Interest is a real per-unit cost"), §2.15 (aging report). |
| 5 | **Should this vehicle continue through recon, be retailed at current price, or be wholesaled?** | `INVENTORY_ACQUISITION_MAPPING.md` §14.5 (aged-unit paralysis), §15.5 (wholesale-out or continue retailing?), §15.10 (move from retail to wholesale-out?). M2 does not *answer* this decision — it makes the underlying gross-vs-carrying-cost math visible so the human can. |
| 6 | **Why has this vehicle stopped progressing?** | `INVENTORY_ACQUISITION_MAPPING.md` §14.12 (recon ETAs that don't match reality); `RECON_MAPPING.md` (referenced by Milestone 3). M2 provides the cost trail; recon-side reasons come with Milestone 3 (ConditionReport) and Milestone 5 (lifecycle stages). |

Questions 1–4 are fully answerable within M2. Question 5 becomes
answerable *because* the ledger exists; the actual disposition
workflow is Milestone 11 sales-side / a future disposition
milestone. Question 6 is partly answerable (cost trail shows where
money stopped flowing) but requires M3/M5 for the full picture.

### 1.1 Acquisition record — `VehicleAcquisition` (1:1 Vehicle)

- **Business question answered.** Q1 + Q2 partial. Every ledger
  computation starts from "what did we pay for this and what came
  with the buy?" Without this record, `total_investment` has no
  floor.
- **Citation.** `INVENTORY_ACQUISITION_MAPPING.md` §2 (Sources of
  Acquisition), §4.2 (What enters cost basis at acquisition);
  `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.2 (Purchase accounting),
  §2.3 (Auction settlements); `VEHICLE_CENTRIC_PIVOT.md`
  §"Acquisition" and §Phase 1.
- **Fields (planning shape — final field list decided in M2.1).**
  - `vehicle` (OneToOneField, required, on_delete=CASCADE).
  - `dealership` (FK, NOT NULL from day one — greenfield table).
  - `source` (CharField with choices: `auction`, `trade`,
    `wholesale`, `private`, `off_lease`, `rental`, `repo`,
    `fleet`). Enumerated straight from `INVENTORY_ACQUISITION_MAPPING.md` §2.
  - `source_detail` (CharField, blank) — free text for "Manheim
    Phoenix, lane 4, run #217" or "trade from CustomerLead #482".
    The narrative research calls this out explicitly (§2.1).
  - `purchase_price` (Decimal).
  - `purchase_date` (Date).
  - `buyer_fees` (Decimal, default 0) — auction house fee.
  - `arbitration_fees` (Decimal, default 0).
  - `transportation_cost` (Decimal, default 0) — capitalized to
    the unit per §2.4.
  - `title_acquisition_cost` (Decimal, default 0) — separate line
    because §2.3 breaks it out.
  - `notes` (TextField, blank).
  - Timestamps.
- **Extend.** §3.5 Vehicle model (OneToOne target). No changes to
  Vehicle's own fields.
- **Leave untouched.** `Vehicle.source` (import-provenance
  CharField, already exists). The acquisition record is *distinct*
  from the import provenance — one is "who fed this row into our
  DB (CSV, feed, seed script)", the other is "how did the physical
  car arrive in inventory". They may agree in practice but the
  research treats them as separate concerns and the model shouldn't
  collapse them.

**Design note — one acquisition per vehicle.** OneToOne is
correct: the acquisition event is unique per unit. If a unit is
returned to the previous owner and reacquired (rare — §2.16 names
it), that's a new stock number, not a second acquisition record on
the same vehicle.

### 1.2 Cost ledger — `VehicleCost` (many-per-Vehicle)

- **Business question answered.** Q1 + Q2 (running total by
  category) + Q4 (floor plan interest is stored as `VehicleCost`
  rows, one per accrual run).
- **Citation.** `VEHICLE_CENTRIC_PIVOT.md` §Investment ledger
  scope (line-item categories); `ACCOUNTING_DEPARTMENT_MAPPING.md`
  §2.6 (Vendor invoices), §2.7 (Recon expenses), §2.8 (Parts),
  §2.9 (Fuel), §2.10 (Misc), §2.12 (Vehicle cost tracking — the
  running total).
- **Fields.**
  - `vehicle` (FK, required, on_delete=CASCADE).
  - `dealership` (FK, NOT NULL from day one).
  - `category` (CharField with choices — enumerated below).
  - `amount` (Decimal).
  - `incurred_at` (DateTime — when the expense happened, not when
    it was posted).
  - `vendor` (CharField, blank) — no `Vendor` model in M2 (deferred
    to M4 per VCP Phase 3); free text captures the invoice's
    counterparty until then.
  - `reference` (CharField, blank) — invoice #, PO #, or the
    accrual-run stamp for floor-plan-interest rows.
  - `notes` (TextField, blank).
  - `is_estimate` (BooleanField, default False) — separates
    committed spend from projected. Named in VCP as a required
    distinction.
  - `created_by` (FK to User, nullable, SET_NULL) — provenance
    for who posted the cost. Nullable so seed/management-command
    writes don't require a synthetic user.
  - Timestamps.
- **Category enum (planning shape — the final enum lives in the
  models file; add/rename as evidence warrants during M2.2).**
  - **Flooring (5):** `floor_plan_interest`, `floor_plan_fees`,
    `curtailment`, `wire_fees`, `banking_fees`.
  - **Reconditioning (13):** `parts`, `mechanical_labor`, `tires`,
    `brakes`, `battery`, `oil_service`, `diagnostics`, `glass`,
    `body_work`, `paint`, `upholstery`, `wheel_repair`,
    `detail`.
  - **Administrative (7):** `fuel`, `listing_fees`,
    `advertising_allocation`, `registration`, `title_work`,
    `shipping`, `misc_dealer_expenses`.
  - **Photography (1):** `photography` — separate because VCP
    calls it out separately (recon vs. listing prep), and M6
    photography milestone will want to distinguish "shot for
    listing" from "shot for damage documentation".

  ~26 categories. Acquisition-day costs (purchase price, auction
  fees, arbitration, transportation, title acquisition) live on
  `VehicleAcquisition` (§1.1), not `VehicleCost`. This split keeps
  the acquisition record small (one row per vehicle, all its
  buying-day totals) and the cost ledger uniform (each row is one
  post-acquisition expense).

- **Extend.** §3.5 Vehicle model (FK relationship target).
- **Leave untouched.** No changes to any existing model. No
  addition to `Vehicle.price` — asking price stays on Vehicle;
  cost basis lives on the related rows.

**Design note — why not category constants on the model?** The
enum lives in a module-level constants block (mirroring
`ROLE_CHOICES` in `models.py`) so tests and the accrual command
can import the canonical names without re-declaring string
literals. The M1 pattern already established this (see
`models.py::ROLE_DEALER_OWNER` etc.).

**Design note — no cost hierarchy in M2.** Some accounting
systems model recon as a two-level tree (recon → parts → filter).
The research does not require it (§2.7 lists categories flat).
Every additional structural concept slows migration and delays
value. Keep flat; revisit if operator feedback surfaces a real
need.

### 1.3 Computed gross properties on `Vehicle`

> **Read/write layer note (annotated at SESSION_048, M2.3
> shipped).** The `Vehicle` model is the **read model** for the
> ledger — thin `@property` accessors that expose already-computed
> ledger information without duplicating math. All aggregation,
> category grouping, upsert semantics, and cross-tenant guards
> live in `services/vehicle_ledger.py` (the **business layer +
> write model**). One `@cached_property ledger_totals` runs the
> lookup once per Vehicle instance; every per-total property
> delegates to that cached `LedgerTotals`. Consequences:
>
> - Callers can read `vehicle.total_investment` naturally without
>   knowing the service exists.
> - Adding a new total requires *only* extending `LedgerTotals` +
>   `compute_totals` — the Vehicle side becomes one delegator
>   `@property`.
> - Callers who need fresh totals after a write on the same
>   instance must refetch (`Vehicle.objects.get(pk=...)`) or
>   `del vehicle.ledger_totals`. In the request/response cycle
>   this is not a concern — each request builds a fresh instance.

- **Business question answered.** Q1 (total investment), Q2
  (breakdown by category), Q3 (projected gross), Q4 (aging days).
- **Citation.** `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.14 (Vehicle
  profitability calculation); VCP §Investment ledger scope
  ("Total investment, Recon investment, Estimated remaining
  investment, Expected gross, Projected gross, Net profitability").
- **Shape.** Read-only Python properties on `Vehicle` that call
  service functions in `services/vehicle_ledger.py`. No stored
  fields — computed from `VehicleAcquisition` + related
  `VehicleCost` rows every time. Staleness is impossible.

  - `total_acquisition_cost` → sum from `VehicleAcquisition`.
  - `total_flooring_cost` → sum of `VehicleCost` with category in
    the flooring set.
  - `total_recon_cost` → sum of the recon set.
  - `total_admin_cost` → sum of the admin set (+ photography).
  - `total_investment` → sum of the four above. This is the
    number the operator wants first.
  - `projected_gross` → `Vehicle.price - total_investment`.
    Matches the VCP Phase 1 demo test verbatim.
  - `days_in_inventory` → `today - VehicleAcquisition.purchase_date`
    (or the earlier of `Vehicle.imported_at` and the acquisition
    date, when both exist).

- **`expected_gross` — deferred to M3.** VCP names both
  "expected" and "projected" gross. In dealer parlance the
  difference is `expected_gross = price - total_investment -
  estimated_remaining_investment`. `estimated_remaining_investment`
  requires a ConditionReport with cost estimates on unfinished
  findings — which is Milestone 3's scope. Shipping
  `expected_gross` in M2 with `estimated_remaining_investment = 0`
  would make the property numerically identical to
  `projected_gross` and semantically dishonest. Defer per
  Discovery Rule (§5).
- **Extend.** §3.5 Vehicle model — new `@property` accessors.
- **Leave untouched.** `Vehicle.price` stays as-is (the asking
  price is an authoring surface, not a computed value).
  `Vehicle.is_available` stays as-is (M5 concern).

### 1.4 Floor-plan-interest accrual mechanism

- **Business question answered.** Q4 in full. Also feeds Q1 (the
  running total must include flooring interest).
- **Citation.** `ACCOUNTING_DEPARTMENT_MAPPING.md` §2.5 ("Interest
  accrual (daily/monthly)... Interest is a real per-unit cost");
  `INVENTORY_ACQUISITION_MAPPING.md` §5.1 (Floor plan health as a
  store health signal); VCP Phase 1 ("Ship a floor-plan-interest
  daily accrual (manual re-run for now — no Celery yet)").
- **Shape.** A management command:
  `python3 manage.py accrue_floor_plan_interest [--dealership=slug] [--as-of=YYYY-MM-DD] [--dry-run]`.
  - Reads floor-plan APR from a new resolver in
    `services/dealer_config.py`
    (`get_floor_plan_apr(dealership) -> Decimal`), which itself
    layers: `DealerOnboardingProfile.floor_plan_apr` (new nullable
    field, see §2 row 10) → env `DEALER_AI_FLOOR_PLAN_APR` → a
    Copper Canyon default (~8.5%).
  - For each vehicle in the tenant that has a
    `VehicleAcquisition` and no matching disposition record:
    1. Find the latest `VehicleCost` row with
       `category='floor_plan_interest'` and `reference` starting
       with `"ACCRUAL:"` — take its `incurred_at` as the last
       accrual date. If none, use
       `VehicleAcquisition.purchase_date`.
    2. Compute `days_elapsed = as_of - last_accrual_date`. If
       zero, skip (idempotency).
    3. Compute `interest = principal * daily_rate * days_elapsed`
       where `principal = VehicleAcquisition.purchase_price -
       sum(curtailment amounts to date)` and
       `daily_rate = apr / 365`. (Curtailments in v1: manual
       entries via cost ledger; if none, principal = purchase
       price. Automated curtailment scheduling is deferred — see
       §5.)
    4. Create one `VehicleCost` row with the accrual amount,
       category `floor_plan_interest`, `reference="ACCRUAL:<as_of>"`,
       `is_estimate=False`, `notes` describing the calculation.
  - **Idempotency.** Re-running with the same `--as-of` finds the
    prior day's row and skips (Step 2 zero-day case). Re-running
    with a later date accrues only the delta. This is the same
    idempotency shape `services/inventory_import.py` uses for CSV
    re-imports (§3.6 in the roadmap).
  - **Tenant scope.** Command must be scoped to a dealership. No
    "accrue everything" command — the research (`§8b` in
    `AUTHENTICATION_MODEL.md`) warns explicitly that management
    commands are the one place `pre_save` autofill is acceptable,
    but this command should still name the dealership explicitly
    so the operator (or ops-run cron) knows what they're doing.
- **Extend.** §3.2 payment engine — new helper
  `daily_floor_plan_interest(principal: Decimal, apr: Decimal, days_elapsed: int) -> Decimal`.
  The math is one line; the reason it belongs in
  `payment_engine.py` is layer discipline (payment_engine owns
  every money-math function; adding this elsewhere would fragment
  the "LLM never invents numbers" boundary).
- **Leave untouched.** Curtailment automation — deferred (§5).
  Floor-plan lender integration (Nextgear / AFC / Westlake APIs)
  — deferred per roadmap §Milestone 2 out-of-scope. Async
  scheduling — Milestone 7 (Celery).

**Design note — why a management command, not a request-time
signal?** The daily accrual could be triggered on-demand from a
view or via post_save signal on `VehicleAcquisition`, but:

1. Accrual should run once per day per vehicle, not per read.
   Signal / view-time triggers create N accruals per day per read
   or per write — the exact drift the "is_estimate" flag doesn't
   catch.
2. A management command is trivially runnable manually today,
   trivially wrappable in a cron tomorrow, and trivially
   Celery-taskable in Milestone 7. Zero rework.
3. The operator can `--dry-run` before committing — a signal has
   no dry-run.

### 1.5 Acquisition-price scrub (17th safety pipeline stage)

- **Business question answered.** *Prevents* the ledger from
  answering customer-facing questions it must never answer
  ("what did you pay for this?"). Belt-and-suspenders against
  ledger figures leaking into customer chat.
- **Citation.** VCP §Ledger safety discipline ("A new post-LLM
  scrub — the 'acquisition-price scrub' — is added as
  belt-and-suspenders in Phase 1"); the M1 retrospective §6
  lesson 3 (layer discipline — every layer has one job, and
  "don't leak internal cost" is the scrub layer's job even when
  M2 promises never to feed ledger figures to the LLM).
- **Shape.** New `_scrub_acquisition_price(text) -> Tuple[str, bool]`
  in `services/llm_safety.py`, mirroring the existing
  `_scrub_indie_prohibited` / `_scrub_invented_promotion` /
  `_scrub_invented_appointment` shape:
  - A `_ACQUISITION_PRICE_PATTERNS` regex list catching phrases
    like *"we paid $X"*, *"our cost was $X"*, *"total investment
    $X"*, *"in it for $X"*, *"we've got $X in"*, *"purchase price
    $X"*, *"acquired for $X"*, *"floor plan interest of $X"*,
    *"recon spent $X on"*, *"our investment on this piece"*.
    Each pattern replaces with a safe substitute
    (*"a great value"*, deletion, or *"our current pricing"*)
    and the caller's `dropped_reason` is set when the pattern is
    a wholesale-rewrite class.
  - Gated on `apply_post_llm_scrubs(text, kind=...)` for every
    kind. The scrub fires on `chat`, `vehicle_ask`, `ad`, and
    `follow_up` because ledger leakage is equally wrong
    everywhere.
  - Runs *after* the existing dealer-cost-safety detector
    (`detect_unsafe_response`) so the pre-existing wholesale
    rewrite still takes precedence when its pattern fires.
- **Extend.** §3.1 llm_safety stack — one additional stage. The
  16-stage count becomes 17. `apply_post_llm_scrubs` signature
  unchanged. No existing scrub is modified.
- **Leave untouched.** Every existing scrub (pre-LLM guards,
  post-LLM partial scrubs, wholesale rewrites, invented_promotion,
  invented_appointment, indie_prohibited). The 1,466 test baseline
  must stay green.

**Design note — the scrub does not depend on the ledger.** The
patterns are text-only. The scrub can be shipped, tested, and
verified against synthetic strings *before* the ledger models
exist. This means the scrub can land in Increment M2.2 (or even
M2.1) independently of the ledger endpoints — the
belt-and-suspenders is in place *before* the first ledger figure
exists.

**Design note — no ledger data flows into the LLM in M2.** The
ledger UI is server-rendered JSON, not LLM-touched. The scrub is
defense in depth for future milestones (M4 recon automation may
want the LLM to summarize vendor cost data; M8 operational
intelligence will absolutely feed aggregate cost data to
narrative generation). Shipping the scrub in M2 pays down the
future debt before it accumulates.

### 1.6 Operator ledger UI surface

- **Business question answered.** Q1–Q4 in a form a human can
  actually look at. All the rest of Milestone 2 is worthless if
  the operator has to shell into Django admin to see the numbers.
- **Citation.** VCP §Phase 1 ("New UI page:
  `/dealer-ai-inventory/<stock>/ledger`"); user brief step 7
  ("It should become the implementation contract for Milestone 2
  exactly as MILESTONE_1_PLANNING.md did for Milestone 1" —
  implying user-facing operator surface, not just APIs).
- **Shape.**
  - **Backend API (three endpoints, all under `/admin/`).**
    - `GET /api/dealer-ai/admin/vehicles/<stock_number>/ledger/`
      — returns the full ledger view: acquisition record, all
      cost rows, computed totals, days-in-inventory. One request
      populates the whole page.
    - `POST /api/dealer-ai/admin/vehicles/<stock_number>/acquisition/`
      — creates or updates the `VehicleAcquisition` row. PUT
      semantics on OneToOne.
    - `POST /api/dealer-ai/admin/vehicles/<stock_number>/costs/`
      — creates a new `VehicleCost` row. No update / delete in
      v1 — see design note below.
  - **Permission composition.** All three:
    `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
    Rationale: the M1 retrospective §6 lesson 4 says role-level
    permissions are additive; owner + sales_manager already have
    every admin surface today, and the ledger is the same kind
    of "operator can look at and manage inventory numbers"
    concern. `recon_manager` access is deferred to M4 when the
    recon side ships (it will need read on cost + write on
    recon-category costs). `advisor` never has ledger access —
    the customer-facing risk is too high.
  - **Frontend route.** New page component at
    `/dealer-ai-inventory/:stock/ledger` (parameterized route,
    off-nav — reached from `/dealer-ai-inventory` list by
    clicking a "Ledger" button on the inventory card). Under
    `<RequireAuth>` per the M1 public/protected split.
  - **UI shape (planning — final in M2.3).**
    - Header: `{Year} {Make} {Model} #{stock_number}` and the
      three-number bar: **In it for $X · Asking $Y · Projected
      gross $Z**.
    - Days in inventory badge next to the header (colored by
      aging bucket per §2.15 accounting: green 0–30, yellow
      31–60, orange 61–90, red 91+).
    - Section: acquisition record (edit-in-place inline form).
    - Section: cost ledger table (paginated, sortable by
      incurred_at / category / amount).
    - Section: "Add cost" inline form (category dropdown, amount,
      date, vendor, reference, notes, is_estimate checkbox).
    - Section: category totals (four rows — acquisition,
      flooring, recon, admin — each with subtotal).
  - **Uses existing frontend primitives.**
    - `lib/authFetch.ts` for all three endpoint calls
      (operator-side; not public).
    - `lib/AuthContext.tsx`'s `useAuth()` for role checking
      (`hasRole('sales_manager') || hasRole('dealer_owner')`
      guards the write forms; anonymous / non-privileged users
      never see the page thanks to the server-side 403 +
      `<RequireAuth>` wrapper).
    - Existing `shadcn/ui` primitives on Tailwind v3 (per
      CLAUDE.md Frontend Stack Notes) — Table, Card, Dialog,
      Input, Select. Tokens: `brand.*` for headers/totals,
      shadcn tokens for chrome.
- **Extend.** §3.8 leads pipeline admin URL family — the ledger
  endpoints follow the same `/api/dealer-ai/admin/*` shape and
  reuse the same permission-composition idiom. Nothing about the
  leads pipeline is *touched*, but the pattern is inherited.
- **Leave untouched.** The `/dealer-ai-inventory` list page (it
  stays as-is; the ledger button is one additional link on each
  card). The customer-facing inventory browser (public
  `/showroom` and `/assistant`) — they never see ledger data.

**Design note — no delete/update on `VehicleCost` in v1.** The
ledger is an operational record; corrections happen by posting a
reversing row (`amount = -original_amount`, `reference` referring
to the original row's ID). This mirrors accounting practice
(`ACCOUNTING_DEPARTMENT_MAPPING.md` §2.11 Inventory adjustments —
"Every adjustment must be documented — journal entry with
explanation, approval, source documents"). It also removes an
entire class of "wait, when did that number change?" bugs. If
operator feedback demands editability, add later — not in v1.

**Design note — sensitive-cost visibility to session sniffers.**
The ledger endpoints return ledger figures in JSON. Anyone with a
browser dev-tools tab in the operator session can read them. That
is the correct behavior: an authenticated sales_manager or
dealer_owner *should* be able to see them. The risk to
mitigate is (a) an anonymous or wrong-role caller seeing them
(covered by the permission classes) and (b) the LLM ever quoting
them at a customer (covered by the acquisition-price scrub).
`authFetch` already refuses to store the DRF token in
localStorage (per `AUTHENTICATION_MODEL.md` §2c), which reduces
the token-exfiltration surface. No separate ledger-figure
obfuscation is required.

### 1.7 What Milestone 2 enables for future milestones

Per user brief step 5 — the ledger is the source of truth that
Operational Intelligence (Milestone 8) later consumes. Recording
which future questions become possible *because* accurate ledger
data exists disciplines against feature creep in M2 (if it's not
required to answer Q1–Q6 in §1.0, defer). Also disciplines against
M8 accidentally re-planning M2 scope.

Questions the ledger unlocks for future milestones (not
implemented here):

- **Milestone 4 (Recon automation):** "Which vendors' actual
  costs deviate most from estimates?" (requires vendor tracking
  in M4 + cost history from M2). "Which recon categories
  consistently exceed budget?"
- **Milestone 5 (Lifecycle stages):** "Average days from
  acquisition to frontline, per stage." (requires stage events
  from M5 + acquisition_date from M2).
- **Milestone 8 (Operational intelligence):** "Which auctions
  produce vehicles with the highest per-unit gross?" (requires
  many acquisitions with source_detail + cost totals — pure SQL
  over M2 tables). "Vehicle types with highest turn * gross."
  "Recon spend p50/p95 by body_style." All of these are SQL
  aggregations over the ledger — no ML.
- **Milestone 9 (Sale + delivery):** "Realized gross vs.
  projected gross at close." Requires a Sale record; the
  comparison is trivially `sold_price -
  vehicle.total_investment_at_close`.
- **Milestone 11 (Sales non-chat channels):** "Which trade-in
  sources produce the best gross?" Requires `VehicleAcquisition.source='trade'`
  linked to the originating CustomerLead (via `source_detail`).
- **Milestone 13 (Accounting reconciliation):** "Does the sum of
  cost ledger entries equal the DMS's inventory GL control
  account?" Requires the ledger to exist. That reconciliation is
  the entire premise of Milestone 13 §accounting layered onto
  M2's ledger.

**None of these are implemented in M2.** They are recorded so the
milestone stays disciplined about *what the ledger is for* and
future sessions can find the pointer without re-deriving it.

---

## 2. Migration Impact Review

Every existing system Milestone 2 touches, with the concrete work
required per system. Systems marked **NO IMPACT** are noted so
nothing goes unaccounted-for. Compared to Milestone 1, the M2
blast radius is smaller — most of the work is greenfield tables
plus one extension per existing primitive.

| # | System | Location | Impact | Work required |
|---|---|---|---|---|
| 1 | `Vehicle` model | `models.py:58-124` | **Extended (properties only).** Gains `total_acquisition_cost`, `total_flooring_cost`, `total_recon_cost`, `total_admin_cost`, `total_investment`, `projected_gross`, `days_in_inventory` — all `@property` methods delegating to `services/vehicle_ledger.py`. No new fields on `Vehicle` itself. | Add property methods; service module implements the underlying aggregation queries with tenant scoping. |
| 2 | `VehicleAcquisition` model (new) | `models.py` (new class) | **NEW.** OneToOne with `Vehicle`, greenfield table. | Migration `0012_vehicleacquisition`. Admin registration. Model-level tests. |
| 3 | `VehicleCost` model (new) | `models.py` (new class) | **NEW.** FK to `Vehicle`, greenfield table. Category enum lives as module-level constants. | Migration `0013_vehiclecost`. Admin registration. Model-level tests. |
| 4 | `services/vehicle_ledger.py` (new) | New module | **NEW.** Business layer: `record_acquisition(vehicle, ..., *, dealership)`, `add_cost(vehicle, category, amount, ..., *, dealership)`, `compute_totals(vehicle, *, dealership) -> LedgerTotals` (dataclass with the six computed numbers). | Module + tests. Every function threads `dealership=` explicitly per M1 §8b. |
| 5 | `services/payment_engine.py` | `services/payment_engine.py` | **Extended.** Add `daily_floor_plan_interest(principal, apr, days_elapsed) -> Decimal`. Pure function, no I/O. | One helper + tests. Preserves the boundary that all money math lives here. |
| 6 | `services/llm_safety.py` | `services/llm_safety.py:336-404` (`apply_post_llm_scrubs`) | **Extended.** New `_scrub_acquisition_price` + `_ACQUISITION_PRICE_PATTERNS` block. New branch inside `apply_post_llm_scrubs` that fires on every `kind`. Signature unchanged. | Regex block + tests. 1,466 baseline must remain green. |
| 7 | `services/dealer_config.py` | `services/dealer_config.py:127-275` | **Extended.** New resolver `get_floor_plan_apr(dealership: Optional[Dealership] = None) -> Decimal` layering DB → env → default. | One resolver + tests, mirroring existing `get_dealer_name` / `get_dealer_profile` shape. |
| 8 | `services/tenancy.py` | `services/tenancy.py` | **NO IMPACT.** M2 consumes `get_current_dealership` and `get_default_dealership` unchanged. | None. |
| 9 | `dealer_ai/permissions.py` | `dealer_ai/permissions.py:146-166` | **NO IMPACT (reuse).** M2 composes the existing `IsSalesManagerOrOwnerAtActiveDealership` at every ledger endpoint. No new class needed until M4 introduces `recon_manager` write access. | None. |
| 10 | `DealerOnboardingProfile` | `models.py:317-436` | **Extended (one nullable field).** Add `floor_plan_apr = DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)`. Nullable so existing rows migrate without a data migration. Onboarding UI adds the field to the "Business shape" section. | Migration `0014_onboardingprofile_floor_plan_apr`. Serializer field. Frontend input. Additive migration only — no NOT NULL flip in M2. |
| 11 | Views (`views.py`) | `views.py` | **Extended.** Three new view functions: `admin_vehicle_ledger`, `admin_vehicle_acquisition_upsert`, `admin_vehicle_cost_create`. Each: composes `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`, resolves `dealership = get_current_dealership(request)` once at top, threads through service calls, filters querysets by dealership. | ~150 LOC. Follows the exact shape of the existing `admin_lead_list` / `admin_lead_detail` / `admin_lead_assign` triad from M1 · Increment 4D. |
| 12 | URLs (`urls.py`) | `urls.py:5-99` | **Extended.** Three new paths under `admin/vehicles/<stock_number>/…`. | Three `path()` entries. |
| 13 | Management commands | `dealer_ai/management/commands/` | **NEW.** `accrue_floor_plan_interest.py`. Args: `--dealership=<slug>`, `--as-of=YYYY-MM-DD`, `--dry-run`. | Command + tests. |
| 14 | Django admin | `dealer_ai/admin.py` (or where existing `Salesperson` / `Dealership` admins live) | **Extended.** Register `VehicleAcquisition` + `VehicleCost` for internal debugging. Read-mostly; write via UI is the operator surface, admin is the fallback. | Two `ModelAdmin` classes. |
| 15 | Frontend: `lib/api.ts` | `frontend/src/lib/api.ts` | **Extended.** Three new operator API functions (`fetchVehicleLedger`, `upsertVehicleAcquisition`, `createVehicleCost`), all through `authFetch`. Every function includes CSRF handling automatically via `authFetch`. | ~40 LOC. Mirrors existing `fetchAdminLeads` etc. |
| 16 | Frontend: new page + route | `frontend/src/pages/` (new file), `frontend/src/main.tsx` | **NEW.** `VehicleLedgerPage.tsx`. Route `/dealer-ai-inventory/:stock/ledger` inside `<RequireAuth>`. | ~250 LOC (page + inline forms + table). |
| 17 | Frontend: inventory list | `frontend/src/pages/InventoryPage.tsx` (or equivalent) | **Extended (one link per card).** Add "Ledger" link on each inventory card that navigates to the new route. | Two lines per card. Non-breaking. |
| 18 | Chat safety stack | `services/chat_engine.py`, `services/vehicle_assistant.py` | **NO IMPACT.** The new scrub attaches to `apply_post_llm_scrubs` which chat already calls. No changes to chat_engine or vehicle_assistant themselves. | None. |
| 19 | Payment engine callers | `services/chat_engine.py`, `services/vehicle_assistant.py`, tests | **NO IMPACT.** The new `daily_floor_plan_interest` helper is additive; existing callers unchanged. | None. |
| 20 | Existing test baseline | `backend/dealer_ai/tests/` (57 files, 1,466 tests) | **At risk (mitigable).** New scrub could accidentally rewrite existing chat replies that happen to look like ledger references. New model migrations could break test fixtures that instantiate `Vehicle` outside a `dealership`-scoped factory. | Pattern the scrub regexes conservatively (only price-adjacent phrasing, not any `$X` mention). Add fixture helpers `default_acquisition_for(vehicle)` and `add_cost_to(vehicle, category, amount)` so ledger-related tests don't repeat setup boilerplate. Baseline 1,466 must be preserved; ledger tests should *add* to the total. |
| 21 | Frontend: `useBrand()` / branding hooks | `frontend/src/lib/brand.ts` | **NO IMPACT.** M2 does not touch branding tokens. | None. |
| 22 | Frontend: shadcn/ui bridge | `frontend/src/index.css`, `frontend/tailwind.config.js`, `frontend/components.json` | **NO IMPACT.** M2 uses existing shadcn primitives (Table, Card, Dialog, Input, Select). Does not touch the v3→v4 bridge or the shipped `brand.*` tokens. | None. |
| 23 | Franchise env-override | `settings.py` (fixed at SESSION_044 · 4F) | **NO IMPACT.** `DEALER_AI_DEALER_TYPE` + `DEALER_AI_PRIMARY_MAKE` continue to flow through. `DEALER_AI_FLOOR_PLAN_APR` is *new* env var; wire it alongside the existing two. | Two new lines in `settings.py`, matching the M1 · 4F fix pattern. |
| 24 | `demo/reset` + `demo/scenarios` | `views.py` | **NO IMPACT (deferred).** The M1 retrospective §7 flags gating these endpoints as a separate scope decision. M2 does not fold it in. | None. If demo-reset creates vehicles, seed a matching acquisition + trivial cost history so the demo ledger has content. |
| 25 | Prod deployment | Render Blueprint | **NO IMPACT.** M2 does not require prod. The retrospective flags prod as a milestone-alongside-M2/M3 decision, but the planning artifact doesn't schedule it here — a separate deployment session lands when the first field-based operator (real buyer at auction) exists. | None. |

---

## 3. Compatibility Checklist

Milestone 2 must uphold every invariant Milestone 1 shipped, plus
the new invariants Milestone 2 introduces. This is the acceptance
contract. Every item verified inline at Milestone 2 close, with
the test class / code location / runtime probe recorded — mirroring
the shape `MILESTONE_1_PLANNING.md` §3 established.

### Milestone 1 invariants Milestone 2 must not regress

Tenancy substrate:
- [ ] `Dealership` model + migration `0007` unchanged.
- [ ] Every existing tenant-carrying model (`Vehicle`,
  `Salesperson`, `ChatSession`, `ChatMessage`, `CustomerLead`,
  `DealerOnboardingProfile`) still has `dealership` FK NOT NULL.
- [ ] `services/tenancy.py::get_default_dealership` / `pre_save`
  autofill / `get_current_dealership` unchanged in signature and
  contract.
- [ ] Any new tenant-carrying model M2 introduces
  (`VehicleAcquisition`, `VehicleCost`) has `dealership` FK NOT
  NULL **from day one** (greenfield) and, if it acquires a
  `pre_save` autofill, registered via
  `services/tenancy.register_default_dealership_autofill()` in
  the same style.

Identity + authentication:
- [ ] `DEFAULT_PERMISSION_CLASSES` remains **unset**. Locked by
  `test_current_dealership.DrfAuthenticationDefaultsIntegration.test_default_permission_classes_remain_unset`.
- [ ] `SessionAuthentication` + `TokenAuthentication` still installed.
- [ ] `/auth/{login,logout,me}` endpoints unchanged.
- [ ] Login endpoint still returns identical 401 for wrong password
  vs unknown user (no user enumeration). Locked by
  `AuthLoginEndpoint.test_unknown_user_returns_same_generic_401`.
- [ ] CSRF still enforced on authenticated mutations. Locked by
  `CsrfEnforcedOnAuthenticatedMutations`.
- [ ] `CSRF_TRUSTED_ORIGINS` still includes dev + prod origins.

Existing endpoint-level permissions:
- [ ] Advisor workspace still authorized by
  `[IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]`.
  Cross-dealership access still rejected; unknown slug still 403.
- [ ] Admin endpoints still authorized by
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
- [ ] Onboarding profile PUT/PATCH still requires
  `IsDealerOwnerAtActiveDealership`. GET still public via
  `[ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]`.
- [ ] Cross-tenant pk lookups on admin endpoints still fail
  closed (404). Locked by
  `AdminLeadDetailFailsClosedAcrossTenants`.

Customer-facing surfaces:
- [ ] Public branding renders unauthenticated. Locked by
  `PublicBrandingRemainsUnauthenticated`.
- [ ] Customer chat (`chat/start`, `chat/message`) unchanged.
- [ ] Per-vehicle Q&A (`vehicles/<id>/ask/`) unchanged.
- [ ] `/`, `/assistant`, `/showroom`, `/embed/assistant`, `/login`
  routes still resolve without a session.

Safety stack (the moat):
- [ ] All 8 pre-LLM guards fire in existing order.
- [ ] All 8 post-LLM scrubs + fabricated-inventory +
  `invented_promotion` + `invented_appointment` +
  `indie_prohibited_copy` scrubs run.
- [ ] Every dollar figure in customer chat still comes from
  `services/payment_engine.py`.
- [ ] Budget-fit classification (`fit / near_fit / over_budget`)
  unchanged.
- [ ] Manager coaching chat still enforces Shape A / Shape B.
- [ ] Ad-copy generator still produces 2–3 variants, still passes
  through `invented_promotion` scrub.
- [ ] Advisor follow-up drafts still pass through
  `invented_appointment` scrub.

Dealer identity resolution:
- [ ] `get_dealer_name()` + `get_dealer_profile()` still resolve
  DB → env → default in the documented order.
- [ ] Franchise env-override still works
  (`DEALER_AI_DEALER_TYPE=franchise` +
  `DEALER_AI_PRIMARY_MAKE=Ford` → franchise-shaped `DealerProfile`).
  Locked by fresh-process smoke — Milestone 1 · 4F caught this
  invariant broken pre-verification; M2 must not silently re-break
  it. Verify with an explicit smoke script in the M2 closeout
  handoff.
- [ ] Copper Canyon defaults still apply when neither env nor DB
  is set.

Frontend contracts:
- [ ] `useBrand()` + `useDealerProfile()` still resolve
  unauthenticated.
- [ ] `brand.*` Tailwind tokens unchanged.
- [ ] `authFetch` / `AuthContext` / `RequireAuth` / `LoginPage`
  unchanged in contract.
- [ ] Public / protected route split in `main.tsx` unchanged (M2
  adds routes *inside* `<RequireAuth>`; nothing moves from
  protected to public).
- [ ] `npx tsc --noEmit` clean.
- [ ] `npx vite build` clean (pre-existing chunk-size warning
  acceptable — same as SESSION_042/043/044).

Test baseline:
- [ ] `python3 manage.py test dealer_ai` → **≥ 1,466 pass** (M2
  ships additively; grew from 1,466 pre-M2 via + new ledger /
  scrub / accrual / permission / API tests), 1 skipped, 0 fail.
- [ ] No test suppressed with `@skip` to make the baseline pass.

### New invariants Milestone 2 introduces

Model-layer:
- [ ] Every `VehicleAcquisition` row has `dealership` FK NOT NULL
  matching its parent `Vehicle.dealership`. Enforced by explicit
  argument at write-path; verified by a targeted test.
- [ ] Every `VehicleCost` row has `dealership` FK NOT NULL
  matching its parent `Vehicle.dealership`.
- [ ] `VehicleAcquisition` is OneToOne with `Vehicle` at the
  schema level (a `unique` constraint on the FK column).
- [ ] `VehicleCost.category` is validated at the model layer via
  `choices=` (invalid category raises `ValidationError`).

Business-layer:
- [ ] `record_acquisition` refuses to create a second
  `VehicleAcquisition` for the same `Vehicle` (returns the
  existing row for update instead — OneToOne upsert semantics).
- [ ] `add_cost` refuses to write a row whose `dealership`
  differs from the parent `Vehicle.dealership` — a defense
  against cross-tenant contamination via a mis-scoped view.
- [ ] `compute_totals(vehicle, *, dealership)` verifies
  `vehicle.dealership_id == dealership.id` before executing any
  aggregation — same fail-closed shape as `AdminLeadDetailFailsClosedAcrossTenants`.
- [ ] `daily_floor_plan_interest(principal, apr, days_elapsed)`
  is pure (no I/O). Handles `apr == 0` (returns 0), negative
  `days_elapsed` (returns 0), and float / Decimal inputs
  consistently.

Endpoint-layer:
- [ ] Every new endpoint composes
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
- [ ] Every new endpoint calls
  `dealership = get_current_dealership(request)` exactly once at
  the top of the handler (per `AUTHENTICATION_MODEL.md` §8b).
- [ ] Every new endpoint's queryset carries an explicit
  `.filter(dealership=dealership)` (or is scoped inside a service
  function that requires `dealership=`).
- [ ] Cross-tenant `stock_number` lookups on the three new
  endpoints fail closed (404) — mirrors
  `AdminLeadDetailFailsClosedAcrossTenants`.
- [ ] The full permission matrix for each new endpoint is locked
  by a focused test class (unauth → 401, wrong-role → 403,
  wrong-tenant → 404, correct sales_manager → 200, correct
  dealer_owner → 200, advisor → 403).

Safety-layer:
- [ ] `_scrub_acquisition_price` fires on `kind ∈ {"chat",
  "vehicle_ask", "ad", "follow_up"}` — every current kind.
- [ ] No existing chat / vehicle_ask / ad / follow_up test
  regresses because of the new scrub (verified by baseline).
- [ ] New scrub is exercised by focused positive AND negative
  tests: positive = the scrub fires on synthetic ledger-leakage
  strings; negative = the scrub does NOT fire on a comprehensive
  set of legitimate strings (existing chat replies, safe
  descriptions like "priced under $20,000", etc.).

Management-command layer:
- [ ] `accrue_floor_plan_interest` refuses to run without
  `--dealership` (no accidental all-tenant runs).
- [ ] Second run against the same `--as-of` is a no-op (skip
  count reported; no duplicate rows created).
- [ ] `--dry-run` never writes.

Frontend:
- [ ] Ledger page is inside `<RequireAuth>` (verified by
  route-file inspection).
- [ ] Ledger page's fetch calls use `authFetch` (verified by
  page-file inspection).
- [ ] Anonymous navigation to the ledger URL redirects to
  `/login?next=…` (integration smoke).
- [ ] Advisor-role user navigating to the ledger URL sees the
  403 UI (integration smoke), not the ledger.
- [ ] No ledger figure appears in any customer-facing surface
  (`/`, `/assistant`, `/showroom`, `/embed/assistant`) —
  server-side query returns nothing for these routes; the scrub
  is defense in depth.

---

## 4. Reusable Primitives Review

Six primitives from `IMPLEMENTATION_ROADMAP.md` §3 are cited by
Milestone 2. All should be **extended**, not paralleled. Two
Milestone-1 primitives (`services/tenancy.py`,
`dealer_ai/permissions.py`) are cited for **direct reuse** — no
extension needed.

### §3.1 LLM safety stack — `services/llm_safety.py`

- **Current shape.** `apply_post_llm_scrubs(text, *, kind) ->
  (cleaned_text, scrubs_fired, dropped_reason)`. Delegates to the
  chat_engine wholesale-rewrite detectors + partial scrubs, plus
  three optional scrub sets gated on `kind`.
- **Sufficient for Milestone 2?** *Yes, with one extension.* Add
  `_scrub_acquisition_price` as a new stage that fires on every
  `kind`. No existing scrub is touched; no test file for the
  existing scrubs regresses.
- **Extension justification.** Building a second scrub pipeline
  would violate `PROJECT_RULES.md` §Preserve Existing Code and
  §Anti-patterns (*"Rewriting scrubs, payment math, or the guard
  pipeline without a specific research-documented reason"*).
- **Callsites unchanged.** `chat_engine`, `vehicle_assistant`,
  `ad_copy`, `follow_up` — all four continue to call
  `apply_post_llm_scrubs(text, kind=...)` unchanged.

### §3.2 Payment engine — `services/payment_engine.py`

- **Current shape.** `estimate_payment`, `estimate_bhph_payment`,
  `affordable_max_price`, `bhph_min_down_payment`. Deterministic
  APR math + BHPH weekly/biweekly variant.
- **Sufficient for Milestone 2?** *Yes, with one extension.* Add
  `daily_floor_plan_interest(principal: Decimal, apr: Decimal,
  days_elapsed: int) -> Decimal`. One-line formula
  (`principal * (apr / Decimal(365)) * days_elapsed`).
- **Extension justification.** The payment engine is the boundary
  where every money-math function lives. Placing daily accrual math
  elsewhere would fragment the "LLM never invents numbers" boundary
  that the M1 retrospective §6 lesson 4 formalized.

### §3.5 Vehicle model + inventory identity

- **Current shape.** `stock_number` (globally unique — tenant-scoped
  uniqueness is deferred per M1 §5), VIN, YMM, features, `source`,
  `imported_at`, `last_seen_at`, `dealership` FK NOT NULL,
  `is_available` (boolean — computed-lifecycle refactor is M5).
- **Sufficient for Milestone 2?** *Yes, with:*
  - New OneToOne related model `VehicleAcquisition`.
  - New FK related model `VehicleCost`.
  - Additive `@property` methods (`total_investment`, etc.) that
    delegate to `services/vehicle_ledger.py`.
- **Extension justification.** `Vehicle` is the identity primitive
  the ledger hangs off. VCP §"Structural changes required" #2
  explicitly says *"keep Vehicle as identity + descriptive facts…
  factor out VehicleAcquisition (OneToOne)"*.
- **What Milestone 2 does NOT change.** No changes to any
  existing Vehicle field. No stock_number uniqueness change
  (deferred to the milestone that first needs two live dealerships
  competing for a shared stock namespace). No `make="Ford"`
  default rename (opportunistic per M1 §5; M2 does not fold it in
  because it has no research trigger this milestone).

### §3.6 Inventory import — `services/inventory_import.py`

- **Current shape.** Upsert-by-stock-number with per-source
  scoping, tenant-scoped via optional `dealership=` argument
  (added in M1 · Increment 3).
- **Sufficient for Milestone 2?** *Not consulted.* M2 does not
  import ledger data from CSV or any external feed — every ledger
  row is authored by the operator through the UI (or the accrual
  command for floor-plan interest). Cited here only to record
  that M2 explicitly does not touch this primitive.
- **What Milestone 2 does NOT change.** Nothing.

### §3.7 Recommended-actions engine — `services/pipeline.py`

- **Current shape.** `trends_snapshot` + `recommended_actions`
  aggregates chat/lead signals into prioritized suggestions.
- **Sufficient for Milestone 2?** *Not consulted.* M2 does not
  emit recommended actions from the ledger (that is Milestone 8
  operational intelligence). Cited here because a future session
  might tempt scope-creeping "aging-alert recommended actions"
  into M2 — that would violate the Discovery Rule (§5).
- **What Milestone 2 does NOT change.** Nothing.

### §3.9 Dealer identity resolver — `services/dealer_config.py`

- **Current shape.** `get_dealer_name(dealership=None)`,
  `get_dealer_profile(dealership=None)` — each layering DB → env
  → default.
- **Sufficient for Milestone 2?** *Yes, with one extension.* Add
  `get_floor_plan_apr(dealership: Optional[Dealership] = None)
  -> Decimal` in the same layered shape. Consumed by the accrual
  command.
- **Extension justification.** Adding a parallel resolver would
  violate the anti-pattern *"Reimplementing dealer identity
  resolution outside of `services/dealer_config.py`"*.

### §3.10 Dealer onboarding profile

- **Current shape.** Singleton in-code, 35 fields, one row per
  dealership (per-tenant conversion at M1 · Increment 4A —
  onboarding profile still uses `.first()`-per-tenant, OneToOne
  conversion deferred per M1 §5).
- **Sufficient for Milestone 2?** *Yes, with one nullable field.*
  `floor_plan_apr = DecimalField(max_digits=5, decimal_places=2,
  null=True, blank=True)`. Nullable so existing rows migrate with
  no data migration. UI adds it to the "Business shape" section.
- **Extension justification.** Same as §3.9 — one config store,
  not two.

### Directly reused (no extension) — `services/tenancy.py`

- Consumed by every new view (`get_current_dealership(request)`)
  and every new service function (`dealership=` kwarg per M1 §8b).
- The `pre_save` autofill remains a fallback safety net for
  tenantless call sites (management commands, seeders); every
  request-scoped write in M2 threads tenancy explicitly.

### Directly reused (no extension) — `dealer_ai/permissions.py`

- `IsSalesManagerOrOwnerAtActiveDealership` composes onto every
  new ledger endpoint. Covers the "operator can look at + manage
  vehicle numbers" concern.
- **No new permission class in M2.** `recon_manager` write access
  lands in M4 (when recon cost entries would come from
  recon-manager workflows, not sales_manager posting invoices).
  Locking that decision here prevents "well, maybe recon should
  see this too" scope creep in M2.

### Genuinely greenfield in Milestone 2

- `VehicleAcquisition` model.
- `VehicleCost` model.
- `services/vehicle_ledger.py` service module.
- `accrue_floor_plan_interest` management command.
- Frontend `VehicleLedgerPage.tsx`.

Everything above is either a new file or a small addition to an
existing primitive. **No parallel implementations proposed.**

---

## 5. Scope Discipline + Deferrals

Ideas that surfaced during this pass that would expand scope
beyond Milestone 2. Per the Discovery Rule: **deferred, not
discarded.**

| Idea | Why it's tempting | Discovery-Rule verdict | Deferred to |
|---|---|---|---|
| `expected_gross` computed property (as distinct from `projected_gross`) | Named in VCP §Investment ledger scope alongside `projected_gross`. | `expected_gross = price - total_investment - estimated_remaining_investment`. `estimated_remaining_investment` requires a ConditionReport with per-finding cost estimates, which is Milestone 3. Shipping in M2 with `estimated_remaining=0` would make the value numerically identical to `projected_gross` — semantically dishonest and a debt future-us will resent. | Milestone 3 (Condition Report) |
| `Vendor` model | VCP §"Recon" names it as part of the recon-side entity list. Every `VehicleCost` row has a `vendor` field that would benefit from FK integrity. | Deferred by VCP §Phase 3. M2 uses a `vendor: CharField(blank=True)` — free text — until Milestone 4 introduces the vendor entity and can data-migrate the free-text values. | Milestone 4 (Recon automation) |
| Automated curtailment scheduling | `INVENTORY_ACQUISITION_MAPPING.md` §5.5 names it as a recurring operational concern; skilled operators forecast 30 days ahead. | M2 v1 accepts curtailments as manually-posted `VehicleCost` rows (category `curtailment`). Automated schedule generation depends on floor-plan-lender integration (deferred by roadmap §Milestone 2 out-of-scope) and async infra (Milestone 7). | Milestone 7+ (needs lender integration OR async) |
| Recon-manager read/write access on the ledger | VCP §"Do NOT build a monolithic single-role UI. Role-scope every view (recon manager, sales manager, owner, advisor, porter)." | Deferred to M4 (Recon automation), where recon-manager workflows create cost entries directly. M2's ledger surface is authored by sales_manager / dealer_owner posting invoices; recon-manager access lands when there's a recon-flow reason for it. | Milestone 4 (Recon automation) |
| Aging-alert recommended actions | `INVENTORY_ACQUISITION_MAPPING.md` §14.5 (aged-unit paralysis); ledger makes the math visible; §3.7 recommended-actions engine cleanly generalizes. | Deferred per the roadmap — this is Milestone 8 (Operational intelligence) scope. M2 makes the underlying data visible in the UI; the aging-alert generator is a separate consumer. Adding it in M2 would fold M8 scope into M2. | Milestone 8 (Operational intelligence) |
| Tenant-scoped uniqueness on `Vehicle.stock_number` | The ledger amplifies the pain of a global-namespace collision (two dealerships with same stock number would produce cross-tenant ledger contamination if a query ever missed its filter). | Deferred from M1 §5. M2 scopes every query explicitly by `dealership` — no query can succeed cross-tenant even under a stock-number collision. Adding the uniqueness change now costs a schema migration + backfill dry-run against a system that has no cross-tenant users. Land it when the *second* live dealership appears. | Milestone that first onboards a second live dealership |
| `Vehicle.is_available` → computed lifecycle | Adding a "stage=frontline" concept would let the ledger show "should this be listed?" natively. | Deferred to Milestone 5 (Lifecycle stages + retail gating). M2's ledger works fine with the boolean. Adding computed lifecycle in M2 folds M5 scope. | Milestone 5 (Lifecycle stages) |
| `Vehicle.make="Ford"` default rename | Franchise leftover; the ledger doesn't actually care about `make`. | Deferred per M1 §5 as opportunistic — M2 does not fold it in because it has no research-driven reason this milestone. Doing it in M2 would be feature creep. | Milestone that opportunistically touches Vehicle schema (M5 is likely) |
| Multi-photo storage (S3-compatible + CDN) | Ledger UI is text-only; but photo-uploads-per-VehicleCost (invoice scans, damage documentation) would be a natural extension. | Deferred to Milestone 3 (Condition Report) or a pre-M3 half-milestone per VCP §"Structural changes required" #6. M2 ledger is text-only. | Milestone 3 or pre-M3 storage-story |
| Async / Celery for the accrual command | The command will grow to run for every tenant nightly; cron is fine to start but a queue is cleaner. | Deferred to Milestone 7 (Async infrastructure) explicitly by VCP §Phase 6 ("Do not adopt Celery earlier. Nothing to run yet."). M2's manual re-run + system cron is exactly right for v1. | Milestone 7 (Async infrastructure) |
| Cost update / delete on `VehicleCost` | Operators will want to correct typos. | Rejected for v1 in favor of reversing rows (per accounting practice — see §1.6 design note). Revisit only if operator feedback surfaces friction that reversing doesn't solve. | Data-first — revisit with operator evidence |
| Full DMS-style deal recap | `ACCOUNTING_DEPARTMENT_MAPPING.md` §3.1 describes the deal recap as a rich cross-department artifact. | M2 is inventory-side only. Deal recap is Milestone 9 (Sale + delivery) + Milestone 13 (Accounting reconciliation). Absolutely out of scope here. | Milestones 9 + 13 |
| Prod deployment as part of M2 | The retrospective §7 flags prod as needing to land alongside the first field-based milestone. | Not a milestone in itself; a prerequisite that should be scheduled explicitly. M2 does not require prod (operator can inspect ledger from dev laptop). Land prod alongside the first milestone whose consumer stands on a lot with a phone (M3 or M4 more likely). | Alongside M3 or M4 |
| Gating `demo/reset` + `demo/scenarios` | The M1 retrospective §7 flags this as a separate scope decision. | Not folded into M2. If the demo reset ever spins up ledger data across tenants, it becomes cross-tenant data-corruption territory — but M2's demo does not do that today. Revisit if evidence surfaces. | Separate decision — not blocking M2 |

Ideas explicitly *not* deferred here (they belong to earlier
sessions' deferral lists and remain deferred by inheritance):

- SSO / MFA. Deferred per M1 §5.
- User-management UI. Deferred per M1 §5.
- Dealership-switcher UI. Extension seam left inside
  `get_active_membership` per M1 §8.
- Cross-platform listing syndication, direct lender-portal
  integrations, GPS/starter-interrupt, skip-tracing, credit
  bureau reporting, e-contracting, GAAP financial reporting,
  predictive ML. Deferred per roadmap §5.

**`docs/DEFERRED_IDEAS.md` should be created** the first time an
M2 session surfaces a deferred idea that does not fit in a
milestone plan doc (per `PROJECT_RULES.md` §Discovery Rule and
`00-START-NEXT-SESSION.md`). The table above stays in this
planning pass and can be lifted into that file when it's created.

---

## 6. Anchors that win on conflict

If this planning doc disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win.
2. `docs/DOC_GOVERNANCE.md` — the doc governance wins.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — the
   roadmap wins on scope questions.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth model wins
   on identity / tenancy / permission questions.
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons — the
   lessons win on engineering-process questions.
6. `docs/research/*_MAPPING.md` + `VEHICLE_CENTRIC_PIVOT.md` —
   the research wins on business-truth questions.
7. `docs/CAPABILITY_MATRIX.md` — the matrix wins on "what does
   the software actually do today?" questions.
8. Current source code — the code wins on "what does the
   software actually do today?" questions.

Planning docs are claims. Rules + research + code are facts.

---

## 7. Increment sequencing

The design memo (§1) describes *what* Milestone 2 delivers. This
section records *how* the work is sliced into per-session
increments so each session ends with the app deployable and the
test baseline healthy.

> **§7 was refined at SESSION_047 during Milestone 2 implementation.**
> The original three-increment plan (M2.1 / M2.2 / M2.3) is
> preserved verbatim below under §7.a as the historical planning
> record. The as-shipped sequence (M2.1 through M2.8) lives under
> §7.b. Do not treat §7.a as the current contract — read §7.b
> for the increment boundaries every subsequent SESSION_04x
> session is bound by.
>
> **Why the refinement.** SESSION_047's brief recognized that the
> proposed M2.2 (twelve deliverables spanning ledger business
> logic, Vehicle computed properties, API surfaces, permissions,
> tenant scoping, acquisition-price safety, floor-plan math,
> floor-plan configuration, and accrual command behavior) combined
> too many independent concerns into a single session. That would
> undo the increment discipline that made Milestone 1 successful.
> Deferred work should be redistributed into small increments, not
> accumulated into one large session. §7.b is the redistribution.

### §7.a Original three-increment plan (preserved for history)

Three increments per the VCP Weeks 3–5 allocation, as scoped at
SESSION_045.

### Increment 1 (M2.1) — schema + model layer

**Deliverable.** `VehicleAcquisition` model + `VehicleCost`
model + migrations `0012` (VehicleAcquisition) and `0013`
(VehicleCost) + admin registration + model-level tests. No API,
no views, no scrub yet.

**Scope boundary.**
- ✅ Two new models with `dealership` FK NOT NULL from day one.
- ✅ Module-level constants for category enum.
- ✅ Django admin registration (read-mostly, for internal
  debugging).
- ✅ Model-level tests: field validation, choices enforcement,
  OneToOne uniqueness, `dealership` FK required, cascade behavior
  on Vehicle delete.
- ✅ `services/vehicle_ledger.py` skeleton with `LedgerTotals`
  dataclass + `compute_totals(vehicle, *, dealership) ->
  LedgerTotals` implemented. Cost breakdown + total_investment.
- ✅ Computed properties on `Vehicle` (`total_investment`,
  `projected_gross`, `days_in_inventory`, category subtotals) —
  delegating to the service.
- ❌ No API endpoints.
- ❌ No frontend.
- ❌ No scrub.
- ❌ No accrual command.
- ❌ No `expected_gross` (deferred).

**Verification at close.**
- Migrations apply cleanly against dev DB.
- Migrations apply cleanly against a fresh DB
  (`migrate dealer_ai zero` → `migrate`) via the dedicated
  `DATABASES["migration_check"]` alias — M1 lesson 2 in action.
- Test baseline grows to ≥ 1,466 + new model tests. Zero
  regressions.
- Admin surface reachable at `/admin/dealer_ai/vehicleacquisition/`
  + `/admin/dealer_ai/vehiclecost/`.

### Increment 2 (M2.2) — API + service layer + safety + accrual

**Deliverable.** Everything backend that turns the M2.1 models
into a usable operator ledger.

**Scope boundary.**
- ✅ `services/vehicle_ledger.py` completed: `record_acquisition`,
  `add_cost`, `compute_totals` (already sketched in M2.1). Every
  function threads `dealership=` explicitly.
- ✅ Three new endpoints:
  `GET /api/dealer-ai/admin/vehicles/<stock_number>/ledger/`,
  `POST /api/dealer-ai/admin/vehicles/<stock_number>/acquisition/`,
  `POST /api/dealer-ai/admin/vehicles/<stock_number>/costs/`.
- ✅ Permission composition on all three:
  `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
- ✅ Focused permission matrix per endpoint (six-case matrix).
- ✅ `services/dealer_config.py::get_floor_plan_apr` resolver.
- ✅ `DealerOnboardingProfile.floor_plan_apr` field + migration
  `0014` (nullable, additive).
- ✅ `settings.py` wires `DEALER_AI_FLOOR_PLAN_APR` env var
  (mirroring the 4F pattern that fixed `DEALER_AI_DEALER_TYPE`).
- ✅ `services/payment_engine.py::daily_floor_plan_interest`
  helper + tests.
- ✅ `services/llm_safety.py::_scrub_acquisition_price` +
  patterns + branch in `apply_post_llm_scrubs`. Comprehensive
  positive AND negative test coverage.
- ✅ `manage.py accrue_floor_plan_interest --dealership=<slug>
  [--as-of=YYYY-MM-DD] [--dry-run]` command + tests
  (idempotency, dry-run purity, tenant-required guard).
- ❌ No frontend.
- ❌ No `Vendor` model.
- ❌ No `expected_gross` computed property.

**Verification at close.**
- Test baseline grows again; zero regressions in the pre-M2
  1,466.
- Manual `curl` smoke of the three endpoints against a
  dev-DB dealership + authenticated `smoke_owner` session.
- Manual smoke of the accrual command: `--dry-run` shows
  expected counts; live run posts rows; re-run same-day is a
  no-op.
- Fresh-process smoke of `DEALER_AI_FLOOR_PLAN_APR` env-override
  (mirrors the M1 · 4F pattern).

### Increment 3 (M2.3) — operator UI surface + closeout

**Deliverable.** The `/dealer-ai-inventory/:stock/ledger` page +
full §3 compatibility sweep + retrospective.

**Scope boundary.**
- ✅ `frontend/src/pages/VehicleLedgerPage.tsx` per §1.6 shape.
- ✅ Three new `lib/api.ts` helper functions (all via `authFetch`).
- ✅ Route registered inside `<RequireAuth>` in `main.tsx`.
- ✅ "Ledger" link added to each inventory card in the existing
  inventory list page.
- ✅ `useAuth()` role-based show/hide on the "Add cost" /
  "Edit acquisition" forms (belt-and-suspenders on top of the
  server-side 403 — matches the M1 · 4E pattern).
- ✅ Full §3 compatibility sweep — walk every item, record
  evidence inline, mirror the SESSION_044 pattern.
- ✅ `docs/CAPABILITY_MATRIX.md` update: new §7c "Vehicle
  investment ledger" enumerating shipped surface.
- ✅ `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.1 row
  "Acquisition record", "Per-vehicle cost basis + running
  investment total" flipped from `N` to `F` (or `P` if
  `expected_gross` deferral kept them partial); §Milestone 2
  recommended-order paragraph updated with shipped date +
  retrospective link.
- ✅ `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` written (mirror
  `MILESTONE_1_RETROSPECTIVE.md` structure).
- ✅ `00-START-NEXT-SESSION.md` overwritten with the SESSION_M+1
  priority (Milestone 3 planning pass, no code).

**Verification at close.**
- `npx tsc --noEmit` clean.
- `npx vite build` clean.
- Browser smoke: login as `smoke_owner` → inventory → click
  Ledger on a card → see acquisition + costs → add a cost →
  see totals update.
- Advisor-role smoke: login as an advisor → navigate to a
  ledger URL directly → see the 403 UI (not redirect).
- Anonymous smoke: navigate to a ledger URL → redirect to
  `/login?next=…`.
- Full test baseline pass — zero regressions across all 1,466 +
  M2's additions.

### Scope-discipline reminders that apply to every M2 sub-increment

- ❌ No tenant-scoped uniqueness on `Vehicle.stock_number` — still
  deferred.
- ❌ No `Vendor` model — Milestone 4.
- ❌ No `expected_gross` — Milestone 3.
- ❌ No condition report or work order — Milestones 3 / 4.
- ❌ No lifecycle stage — Milestone 5.
- ❌ No sale / delivery record — Milestone 9.
- ❌ No changes to the 16-stage safety pipeline (M2 *adds* stage
  17; does not modify the existing 16).
- ❌ No changes to `services/payment_engine.py` existing helpers
  (M2 adds one new helper; existing math untouched).
- ❌ No changes to any Milestone 1 permission class.
- ❌ No async / Celery.
- ❌ No `demo/*` gating decision (separate scope per M1 §7).
- ❌ No commit of any real `OPENAI_API_KEY`.
- ❌ No deletion of the franchise config path or Freedom Ford
  demo assets.

### §7.b Refined as-shipped increment sequence (SESSION_047+)

Eight increments. Each one small enough that a single session ships
it end-to-end with focused tests and full-suite verification. The
scope-discipline reminders above still apply to every increment.

- **M2.1 — Core ledger models (SHIPPED at SESSION_046,
  commits `795fee4` + `882b8e5`).**
  `VehicleAcquisition` + `VehicleCost` models, migrations `0012`
  + `0013`, admin registrations, `SOURCE_*` × 8 and `CATEGORY_*`
  × 26 module-level constants, `DATABASES["migration_check"]`
  alias (per M1 lesson 2), 30 focused model tests. Test baseline:
  1,466 → 1,496 pass. **Deviation from the original §7.a M2.1
  scope:** the persistence layer shipped without the service
  module or `Vehicle` `@property` methods (SESSION_046 brief
  narrowed to persistence-only). Those absorbed into the M2.2 /
  M2.3 boundary below.

- **M2.2 — Ledger business service (SHIPPED at SESSION_047).**
  `services/vehicle_ledger.py` with `LedgerTotals` dataclass +
  `record_acquisition` upsert (returning `(instance, created)`) +
  `add_cost` immutable-post-only + `compute_totals` deterministic
  rollup + `category_group_of` classifier + `CrossTenantLedgerError`
  fail-closed guard on every function. Category groupings
  (`FLOORING_CATEGORIES`, `RECON_CATEGORIES`,
  `ADMIN_CATEGORIES`, `PHOTOGRAPHY_CATEGORIES`) added to
  `models.py`. 44 focused deterministic financial tests
  (hand-verified dollar values). No migrations. No API. No
  frontend. No `Vehicle` `@property` methods (that is M2.3).
  **Load-bearing semantic decision recorded:** `total_investment`
  equals acquisition_total + actual_cost_total *excluding* rows
  where `is_estimate=True`. Estimated spend lives in
  `estimated_cost_total`. `projected_total_investment` is the
  sum of both. Rationale: labeling estimated spending as invested
  money would mislead operators making disposition decisions —
  the `is_estimate` field exists precisely because the
  distinction matters at decision time.

- **M2.3 — Vehicle computed properties (SHIPPED at SESSION_048).**
  `@cached_property ledger_totals` on `Vehicle` (delegates to
  `services/vehicle_ledger.compute_totals`) + nine `@property`
  accessors reading fields off the cached `LedgerTotals` +
  `days_in_inventory` (temporal metric; returns `None` when no
  acquisition record exists — misleading fallbacks like
  `imported_at` are deliberately rejected). 29 focused tests
  including `assertNumQueries` verification that all nine
  per-total properties after cache priming cost zero additional
  queries. Cross-tenant read isolation verified. Zero writes
  during property access. Vehicle became the read model; the
  service stayed the write/business model. See §1.3 above for
  the layer contract annotation.

- **M2.4a — Financial mathematics foundation (SHIPPED at
  SESSION_049).**
  `services/payment_engine.py::daily_floor_plan_interest(
  principal, apr, days_elapsed) -> Decimal` — pure engine, no
  DB, no dealership knowledge, no Vehicle knowledge, no ledger
  writes. Reusable for future payoff / curtailment / lender-
  balance calculations. Load-bearing financial rules locked
  by tests: APR/principal/days-zero → `Decimal("0.00")`;
  negative days → `Decimal("0.00")` (idempotency escape hatch);
  negative principal / negative APR → `ValueError`
  (data-corruption signal, not benign edge case); 365-day
  year (documented); ROUND_HALF_UP (documented divergence from
  banker's rounding). `DealerOnboardingProfile.floor_plan_apr`
  nullable field + additive migration `0014`.
  `services/dealer_config.py::get_floor_plan_apr` — layered
  resolver DB → env → `Decimal("8.5")` default; silent
  fall-through on unparseable env values.
  `settings.py::DEALER_AI_FLOOR_PLAN_APR` env override
  (M1 · 4F pattern). 37 focused tests including hand-verified
  1-day / 30-day / 90-day / 365-day accruals + all edge cases.
  **Split from original M2.4 scope** because the original
  bundled ledger posting + management-command idempotency +
  batch processing with the pure math + config layers; keeping
  the engine pure before wiring the workflow around it is
  cheaper to test and cleaner to reuse.

- **M2.4b — Floor-plan accrual command (NEXT — SESSION_050).**
  `manage.py accrue_floor_plan_interest --dealership=<slug>
  [--as-of=DATE] [--dry-run]` command — consumes the M2.4a
  math + config to post `VehicleCost` rows via
  `services.vehicle_ledger.add_cost` (never
  `VehicleCost.objects.create` directly). Idempotency
  (re-running same-day is a no-op), dry-run purity,
  tenant-required guard.

- **M2.5 — Acquisition-price safety scrub (safety pipeline
  stage 17).** `services/llm_safety.py::_scrub_acquisition_price`
  + `_ACQUISITION_PRICE_PATTERNS` block + branch in
  `apply_post_llm_scrubs` firing on every `kind`. Positive AND
  negative tests. Existing 16 scrub stages untouched.

- **M2.6 — Ledger API + permission matrix.** Three endpoints
  under `/api/dealer-ai/admin/vehicles/<stock_number>/…`:
  `GET .../ledger/`, `POST .../acquisition/`, `POST .../costs/`.
  Permission composition: `[IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership]` on all three.
  Focused six-case permission matrix per endpoint (unauth,
  wrong-role, wrong-tenant, correct sales_manager, correct
  dealer_owner, advisor → 403). URL registrations. Cross-tenant
  `stock_number` lookups fail closed (404) — same shape as
  `AdminLeadDetailFailsClosedAcrossTenants`.

- **M2.7 — Operator ledger UI.** Frontend
  `VehicleLedgerPage.tsx` at `/dealer-ai-inventory/:stock/ledger`,
  inside `<RequireAuth>`. Three `lib/api.ts` helpers via
  `authFetch`. "Ledger" link on each inventory-list card.
  `useAuth()` role-gated show/hide on write forms
  (belt-and-suspenders on top of server-side 403).
  `npx tsc --noEmit` + `npx vite build` clean.

- **M2.8 — Milestone verification + closeout.** Full §3
  compatibility sweep with evidence recorded inline (mirror the
  SESSION_044 pattern). `docs/CAPABILITY_MATRIX.md` §7c
  "Vehicle investment ledger" enumerating shipped surface.
  `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.1 rows for
  acquisition + cost basis flipped `N` → `F`.
  `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` written.
  `00-START-NEXT-SESSION.md` overwritten with Milestone 3
  planning-pass priority.

**Increment discipline for §7.b.** Every session lands one
increment. No session ever bundles two increments to "save time";
the increment discipline that made Milestone 1 successful (each
of 4A–4F ended with the app deployable and the baseline healthy)
is preserved verbatim here.

---

## 8. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/DOC_GOVERNANCE.md` — documentation rules.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2 — scope
  contract.
- `docs/roadmap/AUTHENTICATION_MODEL.md` — the auth substrate
  every ledger endpoint inherits.
- `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` — the lessons M2
  inherits (§6 in particular).
- `docs/roadmap/MILESTONE_1_PLANNING.md` — the planning-artifact
  template this doc mirrors.
- `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference,
  especially §4.1 Inventory & Acquisition, §4.5 Accounting,
  §5.1 Vehicle, §5.8 Financial Transactions, §9.1 The inventory
  dollar cycle.
- `docs/CAPABILITY_MATRIX.md` — what the software does today
  (baseline against which M2's compatibility invariants hold).
- `docs/research/INVENTORY_ACQUISITION_MAPPING.md` — the primary
  business-truth source for M2 (§4 cost basis, §5 floor plan,
  §14 pain points, §15 operational decisions).
- `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md` — the
  accounting side of the same reality (§2 Vehicle accounting,
  §2.12 running total, §2.14 profitability calculation, §2.15
  aging).
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` — architectural plan
  for the whole vehicle-centric pivot (Phase 1 is M2).
- `00-START-NEXT-SESSION.md` — the session priority that
  motivates this planning pass.

---

*End of Milestone 2 planning pass.*
