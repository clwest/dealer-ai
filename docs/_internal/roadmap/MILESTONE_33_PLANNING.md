---
title: "Milestone 33 — F&I Intake Activation: Incoming Application to Active Deal Structure (derived DealStructure status + DealStructure read endpoint + F&I structuring UI + Playwright loop)"
status: historical
type: planning-memo
generated: 2026-08-04
generated_at_session: SESSION_210 (skeleton + expansion + all §5 locks)
milestone: 33
milestone_name: "F&I Intake Activation: Incoming Application to Active Deal Structure (derived DealStructure status + DealStructure read endpoint + F&I structuring UI + Playwright loop)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_10_PLANNING.md (M10.2 DealStructure entity + service verbs + M10.2 endpoint)
  - docs/roadmap/MILESTONE_32_PLANNING.md (M32.1 CA list projection + writeup_context; M32.3 F&I intake page + f_and_i_manager persona)
  - docs/roadmap/MILESTONE_32_RETROSPECTIVE.md §9 (M33 candidate list + F&I depth-arc standing question)
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/CAPABILITY_MATRIX.md §7η (M32 shipped surface)
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md §3.6 (LTV / PTI / DTI definitions)
  - backend/dealer_ai/models.py (DealStructure M10.2 entity; CreditApplication M10.1 record-of-record; DealWriteup M11.3 entity)
  - backend/dealer_ai/services/f_and_i/deal_structure.py (record_deal_structure, get_deal_structure, recompute_ratios verbs)
  - backend/dealer_ai/services/f_and_i/credit_application.py (M32.1 list_credit_applications verb)
  - backend/dealer_ai/views_f_and_i.py (M10.2 admin_deal_structure_create; M32.1 admin_credit_application_list + _project_credit_application_with_writeup)
  - backend/dealer_ai/permissions.py (IsFinanceManagerOrOwnerAtActiveDealership — reused unchanged)
  - backend/dealer_ai/urls.py (M10.2 URL pattern; M32.1 CA list URL)
  - frontend/src/lib/fAndIApi.ts (M32.3 credit-applications list wrapper)
  - frontend/src/pages/DealerFandIIncoming.tsx (M32.3 F&I intake page — receiver of derived-status chip + row actions)
  - acceptance/support/auth/personas.ts (f_and_i_manager persona shipped M32.3)
  - acceptance/support/auth/login.setup.ts (idempotent seed + login pattern per M20)
---

# Milestone 33 — F&I Intake Activation: Incoming Application to Active Deal Structure

> **Active planning memo.** Drafted + expanded + all §5 locks at
> SESSION_210 M33.0 open.
>
> **§5.a locked at open** as **F&I Intake Activation — Incoming
> Application to Active Deal Structure**, under the *primary
> operational-coverage lens* (durable since M22 close) with the
> M32 §9 standing question resolved in favor of **F&I depth-arc
> continuation** over breadth reset. Selected against six
> alternatives (NEW C F&I chargeback substrate — still pilot-
> evidence gated; NEW F&I-scoped lead-context view — evidence-
> gated; NEW cross-lead sales-manager pending-approval queue —
> evidence-gated; NEW O2 / NEW O3 audit refinements — tracing-
> first; H test-hygiene — evidence-independent but zero direct-
> operator-coverage gain) plus three fresh direct-operator gaps
> (vendor detail #43, photo reorder #65, broader F&I subdomain
> #89–101). Verification pass at planning-open surfaced one
> blocking finding on field-level prepopulation truthful-entry
> discipline; resolved architecturally before §5.b lock via D5
> form contract.
>
> **The anchor business question** — *Can an F&I manager take
> an incoming credit application from the M32 queue, begin
> working it through the real product, and create the first
> durable deal-structure record without leaving Dealer OS?* —
> governs every M33 scope decision.
>
> **One blocking finding surfaced at §4 verification and
> resolved architecturally before §5.b lock.**
>
> 1. **Field-level prepopulation gap** — the M32.1
>    `writeup_context.terms` projection carries six of the
>    thirteen DealStructure inputs (`vehicle_price`,
>    `trade_allowance`, `down_payment`, `monthly_payment_target`,
>    `term_months_target`, `apr_target`); it does **not** carry
>    `taxes`, `fees`, `trade_payoff`, or `amount_financed`. The
>    M10.2 serializer defaults `taxes` / `fees` / `trade_payoff`
>    to `0.00` — accepting the shipped serializer defaults from
>    the M33 form would silently invent false financial values.
>    Resolved by **D5 form contract**: no silent defaults on
>    financial fields; blank ≠ 0; submission requires explicit
>    values for `amount_financed`, `taxes`, `fees`; `trade_payoff`
>    remains optional only when the operator explicitly confirms
>    "No trade payoff" via a dedicated affordance.
>
> **Substrate-compound-value continuation restarts at 2 links
> (M32 + M33).** M32 chose breadth over depth (F&I chargeback
> gated at M32.0); M33 opens the F&I depth arc M32 opened by
> activating M10.2 backend-only substrate that has waited for
> an operator receiver since SESSION_107. Restart framing per
> M32 §9 standing question resolution.
>
> **Financial-language contract for M33 (locked at §5.b D5).**
> At the DealStructure stage no lender submission or approval
> exists yet. The M33 UI language therefore uses only two
> categories: **sales targets** (values that originate on the
> M11.3 sales-manager writeup and prepopulate into the F&I
> form) and **proposed structure values** (values the F&I
> manager confirms or revises). No M33 surface — form label,
> read view, confirmation copy, Playwright assertion, or
> memo prose — describes a value as *lender-approved*,
> *lender-committed*, or *actual*. Those categories become
> valid only once a verified LenderSubmission or approval
> workflow exists (deferred; see §3 and §5.h).
>
> **Latest-only read posture (locked at §5.b D9).** Status is
> derived from `deal_structures.count() >= 1`; the domain
> model's M-to-1 cardinality (multiple DealStructures per
> CreditApplication — iteration semantic per M10.2 planning) is
> preserved unchanged. "Start structuring" hidden on
> `In progress` rows in M33 (first-loop only). "Open structure"
> shows only the latest DealStructure by deterministic ordering
> `("-created_at", "-pk")` (§5.b D3). Iteration UX explicitly
> deferred per §5.h.
>
> **Deterministic tie-break required (locked at §5.b D3).** If
> two DealStructure rows share `created_at` at microsecond
> granularity (unlikely but possible under seed / migration /
> bulk-import scenarios), `-pk` secondary sort disambiguates.
> Subquery is explicitly tenant-scoped by including
> `dealership=dealership` in the filter — belt over the model
> `clean()` + service `CrossTenantDealStructureError`
> suspenders that already prevent legitimate cross-tenant rows.
>
> **Zero-drift permission-class streak preserved (M10 → M32:
> 36 consecutive; projected at M33 close: 37 → 38 → 39).** All
> M33 endpoints reuse `_M101_PERMS` (`IsFinanceManagerOrOwnerAtActiveDealership`)
> unchanged. The `f_and_i_manager` Playwright persona shipped at
> M32.3 already carries this permission — no persona work needed.
>
> **DoD amendment (M21.0 §5.f Option B) compliance.** M33.1
> backend-only → **DoD exception path invocation #8** (M32.1
> was #7). M33.2 satisfies DoD directly via new Playwright
> journey (D8). No customer-facing increment ships without
> operational-journey coverage.
>
> **Two-increment shape** — matches surface size (roughly half
> of M32's three-increment scope). M33.1 backend substrate
> (queryset annotation + read endpoint + tests); M33.2 frontend
> UI + Playwright journey. Rollback fully independent in
> reverse ship order.
>
> **Future candidate recorded (§3 and §5.b D10).** *Lender Fit
> Recommendations* — structured, auditable eligibility + ranked
> compatibility + missing-information analysis, always with
> operator explanation and preserved human decision authority.
> **NOT implemented in M33.** Blocked on (a) DealStructure
> creation operationally complete; (b) LenderProgram records +
> rule fields empirically verified; (c) system can retrieve
> app/vehicle/deal attributes for matching; (d) real dealer
> evidence clarifies how lenders are selected today. Recorded
> here per operator directive so scope stays disciplined and
> the future capability is discoverable by future planning
> sessions.

## 1. Anchor question

**Can an F&I manager take an incoming credit application from
the M32 queue, begin working it through the real product, and
create the first durable deal-structure record without leaving
Dealer OS?**

M33 answers *yes* by connecting the M32.3 F&I intake page
(customer-facing, first-loop only) to the M10.2 backend
substrate (`POST /admin/deal-structures/` + service verbs +
model — shipped SESSION_107, unwired from any operator UI for
19 sessions) plus one new read endpoint (`GET
/admin/deal-structures/<int:pk>/`) and one queryset annotation
(`has_deal_structure` + `latest_deal_structure_id`) that
enables derived-status rendering on the intake rows.

The narrow first-loop scope is scope-driven: the M10.2
substrate is intentionally minimal (DealStructure has no
`status` column; state is meant to be derived from downstream
FKs). Extending status to Submitted / Approved / Contracted /
Funded / Chargedback would require evidence-driven state-
machine design that has not yet surfaced. M33 delivers the
smallest complete operator loop that unlocks the F&I depth
arc, and defers richer state extensions to future milestones
gated on operator evidence.

## 2. Business problem this milestone solves

Per `docs/research/FINANCE_DEPARTMENT_MAPPING.md` §2 and §3.6,
the F&I manager's first responsibility on a new incoming
credit application is to structure the deal — assemble the
sale price, trade math, taxes, fees, amount financed, APR,
term, and monthly payment, then evaluate lender fit against
that structure. Today Dealer OS ships the substrate for this
work (M10.2 shipped SESSION_107) but no operator surface
exercises it: the M32.3 intake page renders CAs as terminal
"Incoming" rows with inline triage; no action lets the F&I
manager move a CA out of that state.

The operational consequence is that the M32 hand-off is a
half-loop — sales manager sends → F&I receives → F&I cannot
act. M33 closes the loop by making the first F&I action
(deal structuring) native to Dealer OS.

## 3. Non-goals for this milestone (deferred + future candidates)

**Explicitly deferred out of M33 scope:**

- Any new stored `status` / `workflow_state` column on
  `CreditApplication` or `DealStructure`. Status is derived
  from FK-graph presence.
- Submitted / Approved / Contracted / Funded / Chargedback
  status derivation or UI. Their underlying workflows are
  not yet verified; designing them from endpoint names alone
  would be speculation.
- LenderSubmission / Stipulation / Contract / BackEndProductAgreement
  / Funding / Chargeback UI. Their model + service + endpoint
  substrate ships as backend-only today; extensions await
  operator evidence per milestone.
- PATCH on DealStructure (edit existing structure). M33 is
  creation-and-read only.
- Iteration flow — creating a second DealStructure for a CA
  already in `In progress`. M33 handles first-loop only per
  §5.b D9. Multi-structure UX (list-per-CA, activate-structure,
  delete-structure) explicitly deferred.
- Vehicle-picker substrate for direct-create CAs (M10.1 without
  writeup upstream). M33 handles writeup-originated CAs
  only; direct-create branch out of scope.
- Pagination on `admin/credit-applications/list/` (unchanged
  from M10/M11/M32 precedent — deferred pending operator
  evidence of row-count pain).
- Cross-lead sales-manager pending-approval queue page
  (unchanged M32 §3 deferral).
- F&I-scoped lead-context view (unchanged M32 §3 deferral).
- Client-side monthly-payment auto-derivation via
  `services.payment_engine`. F&I types the proposed monthly
  payment explicitly; no calculator UX in M33 (cadence
  variability — standard APR vs BHPH weekly/biweekly —
  requires design work out of M33 scope).

**Future candidate recorded — Lender Fit Recommendations
(structured, auditable, human-controlled).**

Once a DealStructure exists, Dealer OS should eventually
evaluate the customer, vehicle, and proposed structure values
against available lender programs and present a ranked
shortlist explaining which lenders fit the deal best. The
desired operator outcome: instead of blindly submitting the
application to every lender, the F&I manager sees a ranked
shortlist explaining fit, program constraints, and missing
information.

Design contract (per operator directive, recorded here for
future planning):

1. **Hard eligibility** — lender/program requirements the
   deal clearly passes or fails. Deterministic; no AI.
2. **Likely fit** — ranked compatibility based on deal
   attributes and known lender preferences. Structured
   ranking with visible criteria.
3. **Missing information** — facts or documents required
   before a reliable recommendation can be made.
4. **Operator explanation** — every ranking carries visible
   reasons. Never merely "AI recommends this lender."
5. **Human decision authority** — Dealer OS recommends; the
   F&I manager chooses which lender submissions to create.

Likely inputs — customer credit tier + credit attributes;
verified income + payment-to-income ratio; debt-to-income
ratio; vehicle age / mileage / type / book value + loan-to-
value; amount financed + down payment + term + APR + payment
target; lender program rules + dealership-specific
eligibility; required stipulations; historical approval /
funding / chargeback outcomes when enough real dealer data
exists.

**NOT implemented in M33.** Blocked on:

- DealStructure creation operationally complete (M33 delivers
  this).
- LenderProgram records + their rule fields empirically
  verified.
- The system can retrieve the application, vehicle, and deal
  attributes required for matching.
- Real dealer evidence clarifies how lenders are selected
  today.

Also **do not implement in M33**: lender ranking, lender-
program ingestion, automated submissions, credit scoring, or
historical learning. All belong to the future Lender Fit
Recommendations candidate above.

## 4. Verifications performed at planning-open (SESSION_210)

Nine verifications performed. One blocking finding on field-
level prepopulation truthful-entry discipline; resolved
architecturally before §5.b lock via D5 form contract.

### 4.1 DealStructure model + FK graph inspection — CLEAN

`DealStructure` (`models.py:4742`) declares three CASCADE
foreign keys (`dealership`, `credit_application`, `vehicle`),
five required scalars (`sale_price`, `amount_financed`, `apr`,
`term_months`, `monthly_payment`), five defaulted-to-zero
scalars (`down_payment`, `trade_allowance`, `trade_payoff`,
`taxes`, `fees`), one free-form JSON list (`back_end_products`
defaults to `[]`), and three nullable denormalized ratio
outputs (`ltv_pct`, `pti_pct`, `dti_pct`). Cross-tenant
invariants in `clean()` enforce that `dealership` matches
both `credit_application.dealership` and `vehicle.dealership`.

**Cardinality is M-to-1 by design.** Model docstring
explicitly names iteration as the reason: *"F&I iterates:
primary lender approval, subprime counter-offer, revised
terms after a stip clears, etc. — standard M-to-1, no unique
constraint at M10.2."* M33 preserves this domain contract
unchanged.

### 4.2 Service verb inventory — CLEAN

`services/f_and_i/deal_structure.py` exports six verbs:
three pure ratio computations (`loan_to_value`,
`payment_to_income`, `debt_to_income`); one transactional
write path (`record_deal_structure` — populates ratios pre-
save, raises `CrossTenantDealStructureError` on cross-tenant
FKs, raises `ValueError` on non-positive `sale_price` /
`term_months`); one tenant-scoped single-row read
(`get_deal_structure`); one recomputation helper
(`recompute_ratios`).

**No list-by-CA verb exists.** M33 does not add one — the
`Exists(...)` + `Subquery(...)` annotations on the M32.1
`list_credit_applications` queryset (D1 + D3) replace the
need for a dedicated verb.

### 4.3 Endpoint contract inspection — CLEAN (create-only today)

The only shipped DealStructure endpoint is
`POST /admin/deal-structures/` (`views_f_and_i.py:507`,
`urls.py:547`). No GET, no LIST, no PATCH, no DELETE.
Request-shape (`DealStructureCreateRequestSerializer`):
`credit_application_id` (int), `vehicle_stock` (string, max
64 chars), five required Decimals + int, five optional
Decimals with `"0.00"` defaults, one optional list defaulting
to `[]`. Response shape (`_project_deal_structure`) includes
all 13 stored fields + three ratios + timestamps.

Error mapping: `CrossTenantDealStructureError` → 404
(fail-closed, matches M2.6 / M3.6 / M4.6 / M9.1 / M10.1);
`ValueError` → 400.

M33 adds one endpoint — `GET /admin/deal-structures/<int:pk>/`
— per §5.b D2. No PATCH (activation-vocabulary-asymmetry per
M31 lesson w).

### 4.4 Permission-class access — CLEAN (zero drift)

All M10 F&I endpoints gate on `_M101_PERMS`
(`IsFinanceManagerOrOwnerAtActiveDealership`,
`permissions.py:229`). Grants `f_and_i_manager` OR
`dealer_owner`; denies `sales_manager`, `recon_manager`,
`advisor`, `porter`, `collections`.

The `f_and_i_manager` Playwright persona shipped at M32.3
already carries this permission. **Zero new permission-class
work required.** The zero-drift streak (36 consecutive
milestones M10 → M32) is preserved. Projected at M33 close:
37 → 38 → 39 (M33.1 adds 1 new endpoint reusing existing
class; M33.2 no new endpoints).

### 4.5 FK-graph sequence: DealStructure is genuinely first — CLEAN

Post-intake F&I FK graph (`models.py` 4742–5900):

```
CreditApplication
  └── DealStructure ──┬─→ LenderSubmission ─→ Stipulation
                      └─→ Contract ──┬─→ BackEndProductAgreement
                                     ├─→ Funding (OneToOne)
                                     └─→ Chargeback
```

Key findings:

- **DealStructure is the sole gateway** from CA to every
  downstream F&I entity. LenderSubmission (via
  `deal_structure` FK) and Contract (via `deal_structure` FK)
  are both children of DealStructure.
- **LenderSubmission and Contract are independent siblings.**
  Neither is required to precede the other. Cash deals +
  house-paper BHPH can create a Contract without any
  LenderSubmission. This matches operator reality per
  `FINANCE_DEPARTMENT_MAPPING.md` §2.
- **Stipulation attaches to LenderSubmission**, not to
  DealStructure. Stipulations are lender-driven, not
  structure-driven.
- **Funding is OneToOne with Contract.**
- **Chargeback is many-to-one with Contract.**

**DealStructure is genuinely the first operator action after
intake.** No F&I workflow branches earlier than structuring.
This is exactly the invariant §5.a locks against.

### 4.6 FK discoverability for CREATE — CLEAN for writeup-originated CAs; direct-create OUT of scope

Per memory `feedback_verify_fk_discoverability_before_lock`
(M27.0 durable lesson): every required FK on a create surface
must have a truthful discovery surface before §5.b locks.

Required FKs on `POST /admin/deal-structures/`:

- **`credit_application_id`** — discoverable from the M32.3
  intake row (row is a CA). Unambiguous.
- **`vehicle_stock`** — discoverable from
  `writeup_context.vehicle.stock_number` when the CA has an
  M11.3 hand-off origin (M32.1 projection carries it). **For
  direct-create CAs (`writeup_context = null`), vehicle
  discovery is not available today** — M33 explicitly excludes
  direct-create CAs from the operator flow per §5.h. This is
  scope-truthful: the M32.3 intake page shows both writeup-
  originated and direct-create rows, but M33 offers "Start
  structuring" only where discovery is complete.

Deal-desk math values (`sale_price`, `amount_financed`, `apr`,
`term_months`, `monthly_payment`, `taxes`, `fees`,
`trade_payoff`, etc.) are operator-typed, not FK-discovered
— see §4.7.

### 4.7 Field-level prepopulation truthful-entry check — BLOCKING

Every required and defaulted DealStructure input maps to one
of three categories:

| Field | Category | Prepop source | M33 form disposition |
|---|---|---|---|
| `credit_application_id` | required FK | intake row PK | unambiguous |
| `vehicle_stock` | required FK | `writeup_context.vehicle.stock_number` | unambiguous (writeup-originated only) |
| `sale_price` | required Decimal | `writeup_context.terms.vehicle_price` | prepop as **sales target**; editable |
| `apr` | required Decimal | `writeup_context.terms.apr_target` | prepop as **sales target**; F&I confirms or revises as proposed structure value |
| `term_months` | required int | `writeup_context.terms.term_months_target` | prepop as **sales target**; F&I confirms or revises |
| `monthly_payment` | required Decimal | `writeup_context.terms.monthly_payment_target` | prepop as **sales target**; F&I types proposed structure value (no client-side auto-derivation) |
| `amount_financed` | required Decimal | ❌ no writeup source | **F&I truthful entry required** — blank on load; blank ≠ 0; submission blocked until explicit value |
| `down_payment` | opt (default 0) | `writeup_context.terms.down_payment` | prepop when writeup nonnull; blank when null; no silent 0 |
| `trade_allowance` | opt (default 0) | `writeup_context.terms.trade_allowance` | prepop when writeup nonnull; blank when null; no silent 0 |
| `trade_payoff` | opt (default 0) | ❌ no writeup source | **F&I explicit entry required** — blank on load; operator submits either an explicit numeric value or explicitly confirms "No trade payoff" via a checkbox affordance; untouched blank never converts to 0 |
| `taxes` | opt (default 0) | ❌ no writeup source | **F&I truthful entry required** — blank on load; blank ≠ 0; submission blocked until explicit value |
| `fees` | opt (default 0) | ❌ no writeup source | **F&I truthful entry required** — blank on load; blank ≠ 0; submission blocked until explicit value |
| `back_end_products` | opt (default `[]`) | ❌ n/a | default `[]` is truthful ("no BEPAs at structuring time") |
| `ltv_pct` / `pti_pct` / `dti_pct` | server-derived | n/a | never in form; server computes at write |

**Blocking:** the M10.2 backend serializer accepts
`taxes` / `fees` / `trade_payoff` defaults of `0.00`.
Applying those defaults from the M33 form would silently
invent false financial values on real credit deals.

**Resolved by D5** — form-level contract that (a) uses no
silent defaults on financial fields; (b) distinguishes blank
("not yet confirmed") from explicit 0 ("operator confirms
zero"); (c) blocks submission until `amount_financed`,
`taxes`, and `fees` carry explicit values; (d) requires
explicit "No trade payoff" affordance for `trade_payoff`
rather than accepting untouched blank; (e) surfaces a basic
consistency warning (not full desking math) for obviously
contradictory entries such as `trade_payoff > 0` with
`trade_allowance == 0`.

Backend serializer contract preserved unchanged — discipline
lives in the frontend form.

### 4.8 Derivable-status sufficiency — CLEAN

Derived status vocabulary for M33 (two states only):

- **Incoming** — `credit_application.deal_structures.count() == 0`.
- **In progress** — `credit_application.deal_structures.count() >= 1`.

Sufficient to express the M33 workflow ("does F&I have a
structure yet?"). No new schema column required. Downstream
states (Submitted / Approved / Contracted / Funded /
Chargedback) are deliberately not derived in M33 — they
require underlying workflow verification per §3.

The current M32.1 `intake=true` filter (`no downstream
Contract exists`) is a superset spanning both derived states.
M33 does not change the filter semantic — status is derived
per-row from the new `has_deal_structure` annotation, not
from the filter.

### 4.9 DoD compliance check on §5.e — CLEAN

Per M21.0 §5.f Option B: every customer-facing milestone
must add or update at least one Playwright operational
journey, or explicitly document why no journey change is
required. M33 phase split:

- **M33.1 backend-only** → invocation #8 of exception path
  (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 → M33.1).
  §3 explicitly documents: queryset annotation + read
  endpoint has zero operator-visible behavior until M33.2
  lands.
- **M33.2 customer-facing** → satisfies DoD directly via new
  Playwright journey (D8). Journey asserts the complete
  first-loop operator contract from Incoming → structuring
  form → In progress → read view.

Eight-invocation exception-path pattern is firmly established.

## 5. Load-bearing decisions (all locked at M33.0)

### 5.a Target selection (locked at open)

**Milestone 33 — F&I Intake Activation: Incoming Application
to Active Deal Structure.**

Extend the M32.3 F&I intake page with derived DealStructure
status ("Incoming" / "In progress"), enable "Start
structuring" from Incoming rows to create the first
DealStructure via the shipped M10.2 `POST /admin/deal-structures/`
endpoint, and enable "Open structure" from In progress rows
to view the latest DealStructure. Prove the complete first-
loop through a new Playwright journey (`f_and_i_manager`
persona already shipped M32.3).

**Rationale under the primary operational-coverage lens (with
depth-vs-breadth framing per M32 §9 standing question):**

- **Activates 19 sessions of dormant M10.2 substrate** —
  `POST /admin/deal-structures/` shipped SESSION_107 but has
  had zero operator receiver. M33.2 is the first surface to
  exercise it operationally.
- **Answers M32 §9 standing question with F&I depth-arc
  continuation** — M32 opened the sales-to-F&I bridge (writeup
  → intake receiver); M33 continues the arc with the first
  F&I-side operator action. Substrate-compound-value
  continuation restarts at 2 links (M32 + M33) after the
  M32 breadth pivot.
- **Direct-operator coverage delta** — moves the M10.2 create
  endpoint from backend-only to covered (161/129/32/321 →
  161/130/31/322 projected M33 close, plus one new
  `admin_deal_structure_read` endpoint 161/130 → 162/131/31/322).
- **Zero-drift preservation** — no new permission classes;
  `f_and_i_manager` persona already shipped.
- **Narrow scope respects the discovery rule** — M33 does not
  invent state machines, does not extend chargeback / lender
  / stipulation / contract / funding surfaces, does not touch
  historical migrations. Everything defers to evidence per
  §3 and §5.h.

**Alternatives considered explicitly:**

- NEW C — F&I chargeback substrate: still pilot-evidence
  gated (unchanged M30 / M31 / M32 §9). Recommended only
  if pilot evidence surfaces. Not selected.
- NEW F&I workflow state extensions on intake rows (broader
  than M33): would invent state model without operator
  evidence. Narrowed to M33's two derived states only per
  operator directive at planning open.
- NEW F&I-scoped lead-context view: evidence-gated on
  whether M32.3 D8 inline triage suffices. Deferred.
- NEW cross-lead sales-manager pending-approval queue page:
  evidence-gated on whether per-lead LeadDetailModal
  triage suffices. Deferred.
- NEW O2 + NEW O3: tracing-first, blast-radius unknown.
  Deferred.
- H — test-hygiene remediation: evidence-independent, zero
  direct operator-coverage gain. Would break customer-
  facing streak. Deferred.
- Fresh direct-operator gaps (vendor detail #43, photo
  reorder #65, broader F&I subdomain #89–101): all small
  polish or too large without direction. Not selected.

**User confirmation at open:** target locked; four
corrections applied before §5.b lock — (1) financial-language
contract distinguishing sales targets / proposed structure
values from lender-approved/committed/actual; (2)
deterministic ordering `("-created_at", "-pk")` on latest-
structure subquery + explicit tenant-scope filter; (3)
canonical endpoint path `GET /admin/deal-structures/<int:pk>/`
enforced everywhere; (4) truthful-entry discipline
strengthened with explicit "No trade payoff" affordance and
basic consistency-warning surface (not full desking math).

### 5.b Design decisions (D1–D10)

#### D1 — Backend: `has_deal_structure` annotation on M32.1 CA list projection

Extend `services/f_and_i/credit_application.list_credit_applications(...)`
queryset with:

```python
.annotate(
    has_deal_structure=Exists(
        DealStructure.objects.filter(
            dealership=dealership,
            credit_application=OuterRef("pk"),
        )
    )
)
```

Extend `_project_credit_application_with_writeup(app)` in
`views_f_and_i.py` to include:

```python
"has_deal_structure": app.has_deal_structure,
```

**No schema change.** Queryset-only. The subquery filter
explicitly includes `dealership=dealership` — belt over the
model `clean()` and service `CrossTenantDealStructureError`
suspenders that already prevent legitimate cross-tenant rows.

Frontend derives derived-status entirely from this boolean
(§5.b D4).

#### D2 — Backend: `GET /admin/deal-structures/<int:pk>/` read endpoint

New view function `admin_deal_structure_read` in
`views_f_and_i.py`. Thin wrapper on shipped
`get_deal_structure(pk, dealership=dealership)` service verb
(`services/f_and_i/deal_structure.py:168`). Reuses shipped
`_project_deal_structure(deal)` projection.

**Canonical URL path (locked verbatim):**

```
GET /admin/deal-structures/<int:pk>/
```

Full URL after prefix: `/api/dealer-ai/admin/deal-structures/<int:pk>/`.

`urls.py` addition:

```python
path(
    "admin/deal-structures/<int:pk>/",
    views_f_and_i.admin_deal_structure_read,
    name="admin-deal-structure-read",
),
```

Gates on `_M101_PERMS` — same permission composition as the
shipped M10.2 create endpoint. Returns 404 on unknown or
cross-tenant (fail-closed, matches M9.1 / M10.1 / M10.2).

**Read-only — no PATCH, no DELETE.** Activation-vocabulary-
asymmetry per M31 lesson w.

Backend URL name `admin-deal-structure-read` — matches the
existing `admin-deal-structure-create` naming pattern from
M10.2 (`urls.py:550`).

#### D3 — Backend: `latest_deal_structure_id` deterministic subquery on CA list projection

Extend `list_credit_applications` queryset annotation:

```python
.annotate(
    latest_deal_structure_id=Subquery(
        DealStructure.objects
            .filter(
                dealership=dealership,
                credit_application=OuterRef("pk"),
            )
            .order_by("-created_at", "-pk")
            .values("pk")[:1]
    )
)
```

**Deterministic ordering `("-created_at", "-pk")` locked.**
`-created_at` is the primary sort (matches
`DealStructure.Meta.ordering = ("-created_at",)`); `-pk` is
the tie-break for the rare case where two rows share
`created_at` at microsecond granularity (seed / migration /
bulk-import scenarios). Without the tie-break the subquery
result would be database-order-dependent and non-
deterministic under some Postgres query plans.

**Explicit tenant-scope in the filter.** Belt over the model
`clean()` and service `CrossTenantDealStructureError`
suspenders. If a bug elsewhere ever surfaces a cross-tenant
row, the subquery filter refuses to project it.

Extend `_project_credit_application_with_writeup(app)`:

```python
"latest_deal_structure_id": app.latest_deal_structure_id,  # None for Incoming rows
```

Frontend fetches full DealStructure via D2 when the operator
opens the row.

**Rejects a dedicated list-by-CA endpoint.** Single-latest-ID
is sufficient for the M33 loop; multi-structure UX is out of
scope per §5.h.

#### D4 — Frontend: derived-status chip on intake rows

Each row on `DealerFandIIncoming.tsx` renders exactly one of
two chips:

- **Incoming** — grey chip; `has_deal_structure === false`.
- **In progress** — blue chip; `has_deal_structure === true`.

**No other derived states in M33.** No Submitted / Approved /
Contracted / Funded / Chargedback chips; those are future
milestone territory per §3.

Chip accessibility: three-signal a11y per M31 D6 —
visible label + row `aria-label` extension (e.g.
`"Incoming credit application"` / `"In progress credit
application"`) + testid double marker
(`incoming-row-status-<state>-<pk>`).

#### D5 — Frontend: "Start structuring" action + DealStructure form (Incoming rows only) — truthful-entry contract

**Row visibility.** "Start structuring" button appears only
on rows with `has_deal_structure === false` (Incoming).
Hidden on In progress rows. This is the first-loop-only
posture per D9.

**Form shape.** Inline panel or modal (implementation choice
at M33.2 open — either satisfies the contract). Fields
grouped into three visual sections:

1. **Vehicle** — read-only display of
   `writeup_context.vehicle.stock_number`, year, make, model.
   Value derived from the intake row; not editable in the
   form (rebinding vehicle at structuring time would be a
   scope expansion).
2. **Sales-side targets (prepopulated from writeup;
   editable).** Each field displays with an explicit
   "sales target" affordance (label prefix or badge).
   Editing revises the value into a **proposed structure
   value**. Fields: `sale_price`, `down_payment`,
   `trade_allowance`, `apr`, `term_months`, `monthly_payment`.
3. **F&I proposed structure values (blank on load; explicit
   entry required).** `amount_financed`, `taxes`, `fees`,
   `trade_payoff`. Each field carries a "F&I entry required"
   affordance and validates non-blank before submit
   (except `trade_payoff` — see below).

**Truthful-entry contract (locked):**

- **Blank ≠ 0.** No frontend default on any financial field.
  Applying the M10.2 backend serializer defaults from the
  M33 form is explicitly forbidden.
- **0 is a valid explicit value** — but only when the
  operator intentionally types it or explicitly confirms
  it via the affordance below. Untouched blank never
  submits as 0.
- **Submit blocked until explicit values present for:**
  `amount_financed`, `taxes`, `fees`. Submit button
  disabled with visible reason ("Enter amount financed,
  taxes, and fees before submitting").
- **`trade_payoff` optional-with-explicit-confirmation.** The
  operator either (a) enters an explicit numeric value or
  (b) checks a dedicated **"No trade payoff"** checkbox
  that clears the input and signals explicit zero-intent.
  Leaving the field untouched with the checkbox unchecked
  disables submit with the reason "Confirm trade payoff
  (enter amount or check 'No trade payoff')".
- **Prepopulated fields are editable but preserve
  provenance.** When the operator revises a prepopulated
  value, the visual affordance transitions from "sales
  target" to "proposed structure value" so both operator
  and downstream reviewer can see whether F&I confirmed
  or revised the sales-side proposal.
- **Basic consistency warning surface (not full desking
  math).** One inline warning renders when
  `trade_payoff > 0` and `trade_allowance == 0` (obviously
  contradictory — a trade being paid off should carry an
  allowance). Warning is non-blocking (operator may
  override with an explicit acknowledgment gesture); does
  not invent or enforce desking arithmetic. M33 explicitly
  does not compute or validate
  `amount_financed = sale_price + taxes + fees +
  trade_payoff - down_payment - trade_allowance` or any
  variation — cross-state tax treatment variability puts
  that math out of scope.
- **Client-side monthly-payment auto-derivation is out of
  scope.** F&I types `monthly_payment` explicitly. See D7.
- **`back_end_products` omitted from M33 form.** Defaults to
  `[]` per the M10.2 backend serializer contract (truthful
  — "no BEPAs at structuring time"). Future milestone
  adds BEPA UI when Contract-side flow lands.

**Financial-language discipline.** All form labels, tooltips,
placeholders, aria-labels, and confirmation copy use only
two categories: **sales target** (prepopulated from writeup)
and **proposed structure value** (F&I-entered or F&I-revised).
No M33 surface describes any value as *lender-approved*,
*lender-committed*, or *actual*. Those categories become
valid only once a verified LenderSubmission or approval
workflow exists.

**Submit path.** On valid submit: `POST /admin/deal-structures/`
with all 13 body fields (5 required + 5 optional; `back_end_products`
omitted defaults to `[]` server-side). On 201: close form,
refetch intake list (M32.1 `admin_credit_application_list`),
row transitions from `Incoming` → `In progress`. On 400 /
409 / 404: surface backend error inline; do not close form.

**Testid discipline.** All new testids prefixed
`deal-structure-form-*` and `deal-structure-form-field-<field-name>`.
No collisions with existing `writeup-*`, `lead-*`,
`test-drive-*` families.

#### D6 — Frontend: "Open structure" action + read view (In progress rows only)

**Row visibility.** "Open structure" button appears only on
rows with `has_deal_structure === true` (In progress). Hidden
on Incoming rows.

**Click behavior.** Fetches `GET /admin/deal-structures/<int:pk>/`
using `latest_deal_structure_id` from the intake row
projection (D3). Displays a **read-only** panel with all 13
projected fields organized in the same three visual sections
as D5:

1. **Vehicle** — stock number, year, make, model.
2. **Proposed structure values** — `sale_price`,
   `down_payment`, `trade_allowance`, `trade_payoff`,
   `taxes`, `fees`, `amount_financed`, `apr`, `term_months`,
   `monthly_payment`. Every value labeled as "proposed
   structure value" (not "sales target" — at read time all
   values are committed to the structure).
3. **Derived ratios** — `ltv_pct`, `pti_pct`, `dti_pct`
   with clear labels and NULL-safe display ("Not
   computable — requires income" for NULL PTI/DTI on
   M10.1-era CAs without captured income).

**No edit control in M33.** No PATCH endpoint; no "Edit
structure" button; no "Create another structure" button.
Iteration UX deferred per §5.h.

Testid discipline: `deal-structure-read-*` prefix. No
collisions.

#### D7 — Frontend: no client-side monthly-payment auto-derivation

`services.payment_engine` exists (per M10.2 docstring
reference `payment_engine.DEFAULT_APR = 7.49`) and could
compute `PMT(amount_financed, apr, term_months)`. M33
explicitly does NOT wire it into the form.

**Rationale.** The payment engine supports standard-APR + BHPH
weekly/biweekly cadence. Committing to a specific cadence in
the M33 form either (a) forces standard-APR cadence and
misfits BHPH deals, or (b) requires a cadence selector UX
that expands M33 scope. `monthly_payment` at the DealStructure
stage is a **proposed structure value** (F&I's proposal for
what the customer will pay under this structure); it becomes
a lender-committed number only once a LenderSubmission is
approved or a Contract is signed. F&I types the proposed
monthly payment explicitly per the payment cadence they
intend.

Defer client-side recompute to a later milestone once
operator evidence surfaces cadence discipline.

#### D8 — Playwright: extend `f_and_i_manager` journey with M33 first-loop coverage

New Playwright spec file `f_and_i_intake_activation.spec.ts`
(or equivalent extension of M32.3 spec — implementation choice
at M33.2 open; either satisfies the operational contract).

**Journey shape:**

1. Sign in as `f_and_i_manager` (persona shipped M32.3;
   `AUTH_STORAGE.fAndIManager` storage-state file already
   exists).
2. Navigate to `/dealer-ai-f-and-i/incoming`.
3. Locate the M33 seed fixture row (see fixture
   independence guarantee below).
4. Assert chip = `Incoming`; assert row `aria-label` =
   "Incoming credit application"; assert testid
   `incoming-row-status-incoming-<pk>` present.
5. Click "Start structuring".
6. Assert form opens with:
   - Vehicle section read-only and populated from writeup.
   - Sales-target fields prepopulated (values match seed
     writeup terms); each field carries "sales target"
     affordance.
   - `amount_financed`, `taxes`, `fees` blank with "F&I
     entry required" affordance.
   - `trade_payoff` blank with "No trade payoff" checkbox
     unchecked.
   - Submit button disabled.
7. Fill required F&I proposed structure values.
8. Check "No trade payoff" (or enter explicit 0 — either
   satisfies the contract; journey uses checkbox path for
   coverage).
9. Assert submit button enabled.
10. Submit.
11. Assert form closes; intake list refetches.
12. Locate the same fixture row; assert chip transitioned to
    `In progress`; assert row `aria-label` = "In progress
    credit application"; assert testid
    `incoming-row-status-in-progress-<pk>` present.
13. Click "Open structure".
14. Assert read view opens with all values matching what was
    submitted; assert all values carry "proposed structure
    value" labeling (no "lender-approved" / "lender-committed"
    / "actual" language anywhere).
15. Assert derived ratios (LTV / PTI / DTI) render with
    plausible values or NULL-safe display.

**Fixture independence guarantee (per M32 D11 precedent).**
New idempotent seed command `seed_journey_fandi_intake_activation`
provisions a dedicated fixture — call it `Structure Sam`
(distinct from M32.2 `Sales Sam` and M32.3 `Intake Iris`).
Distinct lead + vehicle + writeup + CA row; no shared state
with any M32 fixture; journey looks up the fixture by known
name / pk from seed output. Distinct rows; parallelism-safe;
test order irrelevant.

**Consistency-warning coverage (secondary journey or extension
in the primary journey — implementation choice at M33.2
open).** Assert that entering `trade_payoff = 500` with
`trade_allowance = 0` renders the consistency warning; assert
that clearing either field or explicitly acknowledging
dismisses the warning; assert that the warning does not block
submit.

**Financial-language assertion.** At least one assertion
verifies that no M33 form or read view text matches
`/lender[- ]approved|lender[- ]committed|actual (rate|payment|apr|term|amount)/i`
across the operator flow — prevents accidental language drift
in future refactors.

#### D9 — Latest-only posture (locked)

Status derivation:

- **Incoming** — `deal_structures.count() == 0`.
- **In progress** — `deal_structures.count() >= 1`.

Row actions:

- **"Start structuring"** — visible only on Incoming rows.
- **"Open structure"** — visible only on In progress rows;
  displays latest DealStructure by `("-created_at", "-pk")`.

Domain model preserved unchanged:

- Multiple DealStructures per CreditApplication remain
  allowed (M10.2 M-to-1 iteration semantic).
- No `unique_together` constraint added.
- No "one active structure" business-rule guard added.
- No multi-structure list / activate / delete UI added.

Rationale: M33 delivers the first-loop only. Iteration UX
(subprime counter, revised terms after stip clears, etc.) is
future milestone territory once operator evidence surfaces
the shape.

#### D10 — Future candidate recording — Lender Fit Recommendations

Recorded verbatim per §3 (contract, likely inputs, blockers).
Documented in M33.0 planning memo §3 AND M33 retrospective §9
at M33 close (candidate elevated to M34+ candidate list).

**NOT implemented in M33.** No lender ranking, no lender-
program ingestion, no automated submissions, no credit
scoring, no historical learning. Substrate work (LenderProgram
records + rule fields empirical verification) is a prerequisite
that itself awaits operator direction.

### 5.c Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | F&I opens Structure form for a CA with `writeup_context = null` (direct-create via M10.1) → no prepopulation source; no vehicle | Low (M33 seed fixture is writeup-originated) | High if hit | §5.h explicitly excludes direct-create branch; D5 "Start structuring" button rendered only when `writeup_context !== null` (extension of D5 form contract); direct-create rows show only inline triage per M32.3, no structuring action |
| R2 | Silent tax / fee / trade_payoff default of 0 on submit invents false financials | None (by D5 construction) | Critical | D5 form contract: blank ≠ 0; submit disabled until explicit values; `trade_payoff` requires either explicit value or "No trade payoff" checkbox; three-layer defense (form validation + submit disable + D8 Playwright assertion of blank-form-blocks-submit) |
| R3 | F&I creates a second DealStructure while a first exists (iteration semantic per M10.2 planning) | Med (M10 domain allows it) | Med (would need multi-structure UX to resolve cleanly) | D9 first-loop-only posture: "Start structuring" hidden on In progress rows in M33; iteration UX explicitly deferred per §5.h; no domain-model change |
| R4 | `monthly_payment` inconsistent with `sale_price` / `amount_financed` / `apr` / `term_months` (operator entry error) | Low | Low (F&I responsibility at proposed-structure stage) | D7 explicitly names client-supplied payment; backend accepts what F&I types; no runtime derivation guard; documented as F&I entry discipline; D5 consistency-warning surface is deliberately not extended to payment-arithmetic checks (would require desking-math engine out of scope) |
| R5 | Cross-tenant DealStructure creation (CA / vehicle from another dealership) | None (by construction) | Critical | Belt (M10.2 `clean()`) + suspenders (`CrossTenantDealStructureError` in service verb) — both shipped; 404 shape unchanged; D3 subquery explicitly tenant-scopes via `dealership=dealership` filter (third layer of defense against cross-tenant leakage into latest-structure-ID projection) |
| R6 | `latest_deal_structure_id` subquery breaks intake list performance at high row count | Low (M33 fixture is small; M10/M11 no-pagination precedent has held through 32 milestones without operator complaint) | Med at scale | Subquery uses CA FK (indexed); acceptable for M33; pagination on the intake list deferred per M10/M11/M32 precedent |
| R7 | Playwright M33 fixture leaks with M32.3 `Intake Iris` or M32.2 `Sales Sam` fixture → cross-test contamination | None (by construction) | High | D8 fixture independence per M32 D11 precedent: dedicated `Structure Sam` seed via `seed_journey_fandi_intake_activation` idempotent command; distinct lead + vehicle + writeup + CA; distinct testid values; journey looks up by known name / pk from seed output |
| R8 | F&I role misses read endpoint (D2) because `_M101_PERMS` not wired to new view | None (by convention) | Med | D2 explicitly reuses `_M101_PERMS` per M10.2 pattern; endpoint test asserts 403 for non-F&I roles; three-layer coverage (view decorator + endpoint test + Playwright persona journey) |
| R9 | Two DealStructures share `created_at` at microsecond granularity → latest-selection non-deterministic | Very low (production writes are single-user-typed and spaced; only risk is seed / migration / bulk-import scenarios) | Med (would surface as "wrong structure opens" in In progress read view) | D3 subquery adds `-pk` secondary sort; deterministic under all scenarios; test asserts deterministic selection when two structures share `created_at` |
| R10 | M33 UI language drifts toward "lender-approved" / "lender-committed" / "actual" phrasing during implementation or later refactor | Low (D5 + D6 + D8 explicit) | High (violates financial-language contract; misrepresents state of the deal to F&I operator) | D8 Playwright assertion regex-checks form + read view for forbidden phrases; D5 + D6 spec locks language explicitly; retrospective §9 records language contract as a future-milestone reminder |

### 5.d Verifications completed at planning-open

Nine verifications (§4.1–§4.9 above) all resolved:

- §4.1 DealStructure model + FK graph: CLEAN (M-to-1
  cardinality preserved).
- §4.2 Service verb inventory: CLEAN
  (`record_deal_structure` + `get_deal_structure` +
  `recompute_ratios` all shipped; no new service verb
  needed).
- §4.3 Endpoint contract: CLEAN (POST-only today; D2 adds
  GET).
- §4.4 Permission-class access: CLEAN (`_M101_PERMS`
  unchanged; zero-drift streak preserved).
- §4.5 FK-graph sequence: CLEAN (DealStructure is genuinely
  first F&I entity; downstream siblings independent).
- §4.6 FK discoverability for CREATE: CLEAN for writeup-
  originated CAs; direct-create explicitly deferred to
  future milestone.
- §4.7 Field-level prepopulation truthful-entry: BLOCKING
  → resolved by D5 form contract.
- §4.8 Derivable-status sufficiency: CLEAN
  (`Exists(...)` annotation is sufficient).
- §4.9 DoD compliance check on §5.e: CLEAN (M33.1 exception
  path invocation #8; M33.2 satisfies directly).

**One blocking finding (§4.7) resolved architecturally
before scope-lock via D5 form contract.** Verification rigor
at planning-open shaped D5 from initial draft to final locked
shape.

### 5.e Phase / increment structure

**Two-increment split** — scope-driven per §5.a surface size
(roughly half of M32's three-increment scope). All revertable
independently; no migrations; no schema changes.

#### M33.1 (SESSION_211) — Backend: annotation + read endpoint + tests

**DoD exception path invocation #8.**

- **Queryset annotation extension**
  (`services/f_and_i/credit_application.py`):
  - Extend `list_credit_applications(...)` with two
    subquery annotations:
    - `has_deal_structure=Exists(DealStructure.objects.filter(dealership=dealership, credit_application=OuterRef("pk")))`.
    - `latest_deal_structure_id=Subquery(DealStructure.objects.filter(dealership=dealership, credit_application=OuterRef("pk")).order_by("-created_at", "-pk").values("pk")[:1])`.
  - No new service verb; no signature change; existing
    filter composability preserved (`intake` / `lead` /
    `since` all still work).
- **Projection extension** (`views_f_and_i.py`):
  - Extend `_project_credit_application_with_writeup(app)`
    to include `"has_deal_structure": app.has_deal_structure`
    and `"latest_deal_structure_id": app.latest_deal_structure_id`.
- **New view function** (`views_f_and_i.py`):
  - `admin_deal_structure_read(request, pk)` — thin
    wrapper on shipped `get_deal_structure(pk, dealership=dealership)`
    service verb; reuses shipped `_project_deal_structure(deal)`
    projection; returns 404 on unknown or cross-tenant;
    gates on `_M101_PERMS`.
- **URL pattern** (`urls.py`):
  - `path("admin/deal-structures/<int:pk>/", views_f_and_i.admin_deal_structure_read, name="admin-deal-structure-read")`.
- **Model + service docstring updates** — small: reference
  the new read endpoint in `DealStructure` model docstring
  (`models.py:4742+`); no signature change on
  `get_deal_structure` verb.
- **Tests** (target ~15 new):
  - Annotation with 0 / 1 / N DealStructures (N=3
    including tie-break scenario at shared `created_at`).
  - `latest_deal_structure_id` deterministic under shared
    `created_at` (asserts `-pk` tie-break).
  - Annotation tenant-scoped (subquery filters by
    `dealership`; cross-tenant DealStructures do not leak
    into projection).
  - Projection includes both new fields; both `null` for
    Incoming rows.
  - Read endpoint 200 for own-tenant existing DealStructure;
    404 for unknown; 404 for cross-tenant; 403 for
    non-F&I roles (sales_manager, recon_manager, advisor,
    porter, collections).
  - Read endpoint projection matches shipped
    `_project_deal_structure` shape verbatim.
- **Backend baseline projection:** 4,995 → **≈5,010** pass
  at M33.1 close.
- **Audit projection:** 161 → 162 endpoints; 129 → 130
  covered (new read endpoint covered because tests cover
  it; not because a Playwright journey exists yet — that's
  M33.2); 32 backend-only → 31; 321 → 322 service verbs.
- **Two-source agreement gate** at M33.1 close: run
  `python3 -m dealer_ai.scripts.audit_operational_surface`
  and confirm delta matches projection.

#### M33.2 (SESSION_212) — Frontend UI + Playwright loop

**Satisfies DoD directly.**

- **API client extensions** (`frontend/src/lib/fAndIApi.ts`):
  - `createDealStructure(payload)` — wraps
    `POST /admin/deal-structures/`.
  - `getDealStructure(id)` — wraps
    `GET /admin/deal-structures/<int:pk>/` (canonical path).
  - Extend `CreditApplicationProjection` type with
    `has_deal_structure: boolean` and
    `latest_deal_structure_id: number | null`.
- **DealStructureForm component** (new file under
  `frontend/src/components/f-and-i/` or equivalent):
  - Three-section layout per D5.
  - Sales-target prepopulation from
    `writeup_context.terms`.
  - Blank-required behavior for `amount_financed`,
    `taxes`, `fees`.
  - "No trade payoff" checkbox affordance for
    `trade_payoff`.
  - Consistency-warning surface for
    `trade_payoff > 0 && trade_allowance == 0`
    (non-blocking).
  - Financial-language discipline: only "sales target"
    and "proposed structure value" labels; no
    "lender-approved" / "lender-committed" / "actual".
  - Submit path: POST → close form → refetch intake list
    → row transitions Incoming → In progress.
- **DealStructureReadView component** (new file):
  - Three-section read-only layout per D6.
  - "Proposed structure value" labeling throughout.
  - NULL-safe display for ratios ("Not computable —
    requires income").
- **DealerFandIIncoming.tsx changes:**
  - Derived-status chip (Incoming / In progress) with
    three-signal a11y per D4.
  - "Start structuring" button on Incoming rows;
    "Open structure" button on In progress rows.
  - Both actions open the respective component
    (implementation choice: modal or inline panel).
  - Refetch intake list after successful create.
- **Vitest (target ~15 new):**
  - Form prepopulation from writeup context.
  - Form blank-required validation for `amount_financed`,
    `taxes`, `fees`.
  - Form "No trade payoff" checkbox behavior.
  - Form consistency-warning surface.
  - Form submit path (mocked POST → refetch).
  - Read view rendering of all fields.
  - Read view NULL-safe ratio display.
  - Status chip rendering for each derived state.
  - Row-action visibility (Start on Incoming, Open on In
    progress).
- **Playwright (new; per D8):**
  - `f_and_i_intake_activation.spec.ts` (or extension of
    existing M32.3 spec — implementation choice).
  - New idempotent seed command
    `seed_journey_fandi_intake_activation` provisioning
    `Structure Sam` fixture.
  - Financial-language regex assertion per D8.
  - Consistency-warning coverage per D8.
- **Frontend baseline projection:** Vitest 377 → **≈392**
  pass; acceptance 24 spec files → **25**; 31 tests → **32**;
  suite time still under 40s.
- **Audit projection:** 162 endpoints / 130 covered / 31
  backend-only / 322 service verbs unchanged at M33.2 close
  (Playwright coverage does not affect the audit total; it
  strengthens operational-contract coverage which is
  tracked separately in retrospective §5).
- **Two-source agreement gate** at M33.2 close: run audit;
  confirm baseline holds.

Rollback order at M33 close (reverse ship order):

- M33.2 revert first (frontend + Playwright commit).
  Removes UI + form + journey; backend surface stays
  valid (D2 read endpoint remains callable but unused).
- M33.1 revert second (backend commit). Queryset
  annotation + view removal; no migration; no schema
  change; trivial.

M33.1 cannot be reverted while M33.2 is shipped without
breaking the F&I intake page (frontend depends on M33.1
projection). Reverse-order discipline enforced.

### 5.f DoD compliance check (M21.0 §5.f Option B)

- **M33.1 backend-only** — invocation #8 of exception path
  (M26 + M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 →
  M33.1). §3 documents: queryset annotation + read
  endpoint has zero operator-visible behavior until M33.2
  lands. Exception path pattern firmly established at
  eight invocations.
- **M33.2** — satisfies DoD directly via D8 Playwright
  journey. New spec asserts the complete first-loop
  operator contract from Incoming → structuring → In
  progress → read view, plus financial-language regex
  assertion, plus consistency-warning coverage.

No customer-facing increment ships without operational
journey coverage.

### 5.g Rollback plan

- **M33.1 rollback:** revert the single commit. Queryset-
  only + view-only + URL entry. No migration; no schema
  change. Safe standalone if M33.2 has not shipped.
  Backend baseline returns to 4,995 pass; audit returns
  to 161/129/32/321.
- **M33.2 rollback:** revert the single commit. Removes
  frontend components + API-client extensions + Playwright
  spec + seed command. Backend surface stays valid (D2
  read endpoint remains callable but unused). Frontend
  baseline returns to Vitest 377 pass; acceptance 24 spec
  files / 31 tests.
- **Reverse-order rollback discipline** (M33.2 → M33.1)
  matches M32.2/M32.3/M32.1 shape. M33.1 cannot revert
  while M33.2 is shipped without breaking the F&I intake
  page.

Fixture rollback: the M33.2 `seed_journey_fandi_intake_activation`
command is idempotent; running it on a fresh DB re-provisions
`Structure Sam` from scratch. Removing the command on rollback
does not corrupt existing dev / acceptance DB state.

### 5.h Non-goals for M33

- ❌ Do NOT introduce a new stored `status` /
  `workflow_state` column on `CreditApplication` or
  `DealStructure`. Status is derived from FK-graph presence.
- ❌ Do NOT design or implement Submitted / Approved /
  Contracted / Funded / Chargedback status extensions.
  Their underlying workflows are not yet verified.
- ❌ Do NOT extend LenderSubmission, Stipulation, Contract,
  BackEndProductAgreement, Funding, or Chargeback UI in M33.
  Their backend substrate stays as-shipped.
- ❌ Do NOT implement lender ranking, lender-program
  ingestion, automated submissions, credit scoring, or
  historical learning. Recorded as future Lender Fit
  Recommendations candidate (D10) per operator directive.
- ❌ Do NOT enforce a "one deal structure per CA" domain
  constraint. Preserve M10.2 M-to-1 iteration semantic.
- ❌ Do NOT build multi-structure management UI (list-per-CA,
  delete-structure, activate-structure, iterate-structure,
  etc.). First-loop only per D9.
- ❌ Do NOT enable PATCH or DELETE on DealStructure. Create-
  and-read only.
- ❌ Do NOT extend F&I role access to `admin_lead_detail`.
  M32.3 non-navigational inline triage stands.
- ❌ Do NOT silently default `taxes` / `fees` / `trade_payoff`
  / `amount_financed` to 0 on the form. Blank ≠ 0. Explicit
  entry required (or explicit "No trade payoff" affordance
  for `trade_payoff`).
- ❌ Do NOT auto-derive `monthly_payment` client-side via
  `services.payment_engine` in M33. F&I types the proposed
  structure value explicitly.
- ❌ Do NOT enforce or compute full desking arithmetic
  (`amount_financed = sale_price + taxes + fees + trade_payoff
  - down_payment - trade_allowance`). Cross-state tax
  treatment variability puts that math out of scope. The
  D5 consistency-warning surface flags obviously
  contradictory entries (e.g. `trade_payoff > 0` with
  `trade_allowance == 0`) without inventing arithmetic.
- ❌ Do NOT add a vehicle-picker substrate for direct-create
  CAs (`writeup_context = null`). M33 covers writeup-
  originated CAs only. Direct-create branch (M10.1 without
  hand-off upstream) rendered without "Start structuring"
  action per D5 extension.
- ❌ Do NOT add pagination on
  `admin/credit-applications/list/`. Unchanged from
  M10/M11/M32 precedent.
- ❌ Do NOT ship a cross-lead sales-manager pending-approval
  queue page (unchanged M32 §3 deferral).
- ❌ Do NOT ship an F&I-scoped lead-context view (unchanged
  M32 §3 deferral).
- ❌ Do NOT modify the historical `0026_deal_structure_entity.py`
  migration retroactively. Any evolution recorded in current
  `models.py` docstrings + planning memo + retrospective per
  M32 (aa) historical-migration-immutability discipline.
- ❌ Do NOT describe any M33 UI value as *lender-approved*,
  *lender-committed*, or *actual*. Financial-language
  contract locked per D5. Playwright regex asserts absence
  per D8.
- ❌ Do NOT modify M1–M32 shipped surface.

## 6. Downstream planning artifacts

At M33 close:

- **`docs/roadmap/MILESTONE_33_RETROSPECTIVE.md`** (new) —
  records final baselines, load-bearing lesson candidates
  (four candidates carried from M32 `y` / `z` / `aa` / `bb`
  eligible for elevation on M33 re-application; any new
  candidates surfaced during M33.1 / M33.2 implementation),
  §9 M34 candidate list (Lender Fit Recommendations
  elevated; NEW C chargeback substrate; NEW workflow-state
  extensions; NEW F&I-scoped lead-context view; NEW cross-
  lead pending-approval queue; NEW O2 / NEW O3; H).
- **`docs/CAPABILITY_MATRIX.md`** — new §7θ section documenting
  M33 shipped surface (M32 was §7η).
- **`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`** —
  regenerated at M33.1 close (161 → 162 endpoints; 129 →
  130 covered; 32 → 31 backend-only; 321 → 322 service
  verbs) and again at M33.2 close (Playwright coverage
  strengthens operational contract; audit totals unchanged
  from M33.1).

## 7. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_32_RETROSPECTIVE.md` §9 (M33
   candidate list origin + F&I depth-arc standing question
   resolution)
6. **This memo** (`docs/roadmap/MILESTONE_33_PLANNING.md`)
   — governing contract for M33.
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
8. `docs/CAPABILITY_MATRIX.md` §7η (M32 shipped surface);
   §7θ added at M33 close.
9. `docs/handoffs/SESSION_209_m32_inc3_fandi_ui.md` (M32
   close-out fold + F&I intake page shipped surface)
10. `docs/roadmap/MILESTONE_10_PLANNING.md` §1.2 (M10.2
    DealStructure origin — governs the M-to-1 iteration
    semantic that D9 preserves)
11. `docs/research/FINANCE_DEPARTMENT_MAPPING.md` §2 +
    §3.6 (F&I first-action + LTV / PTI / DTI semantics)
12. Memory record
    `feedback_verify_fk_discoverability_before_lock.md`
    (M27.0 origin — applied at §4.6 for `vehicle_stock`
    discovery on writeup-originated vs direct-create CAs)
13. Memory record
    `feedback_duplicate_small_stable_logic.md` (M28.0
    origin — applicable at M33.2 for form validation
    helpers)
14. Memory record
    `feedback_playwright_as_operational_contract.md` (D8
    journey extends the operational contract to F&I
    first-loop)
15. Memory record `feedback_terminal_output_discipline.md`
    (governs implementation-session output shape)

Narrative docs are claims. Rules + research + code +
regenerated artifact are facts.

## 8. Streaks projected at M33 close

- **Planning-time as-recommended streak:** 11 → **12**
  (target selected as recommended after seven-alternative
  comparison + nine-verification pass performed at user
  direction; four verification-driven corrections applied
  before §5.b lock — financial-language contract;
  deterministic ordering + tenant-scope; canonical
  endpoint path; strengthened truthful-entry with explicit
  affordance + basic consistency warning). Historical run
  of 89 across M10 → M23 preserved.
- **Zero-drift permission-class streak:** 36 → **37**
  (M33.1) → 37 (M33.2 no new endpoints) → **37 at M33
  close**. All M33 endpoints reuse `_M101_PERMS`
  unchanged.
- **Substrate-compound-value continuation:** M32 broke the
  M27.1 → M31 five-link streak by choosing breadth.
  M33 restarts the arc with M32 as link 1 (sales-to-F&I
  bridge) and M33 as link 2 (F&I first-loop activation).
  Framing per M32 §9 standing question resolution.
- **DoD exception path invocations:** 7 → **8** (M33.1).
  M33.2 satisfies DoD directly.
- **First milestone to activate M10.2 substrate
  operationally** — 19 sessions after M10.2 shipped at
  SESSION_107.
- **Second consecutive customer-facing milestone in the
  F&I domain** (M32 shipped intake receiver; M33 ships
  first F&I action). Signals healthy F&I depth-arc
  continuation.
- **First milestone to lock a financial-language contract**
  at planning time (sales targets vs proposed structure
  values, with explicit rejection of lender-approved /
  lender-committed / actual). Candidate durable lesson at
  M33 retrospective §5 if the contract survives M33.2
  Playwright verification without drift.
- **First milestone to record a future capability
  (Lender Fit Recommendations) with full design contract
  at planning time**, per operator directive. Design
  discipline demonstration — captured, deferred, blocked
  on named prerequisites; not implemented.
