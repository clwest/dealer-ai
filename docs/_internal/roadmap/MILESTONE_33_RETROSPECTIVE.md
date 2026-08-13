---
title: "Milestone 33 — F&I Intake Activation: Incoming Application to Active Deal Structure — Retrospective"
status: historical
type: retrospective
milestone: 33
milestone_status: shipped
generated: 2026-08-04
generated_at_session: SESSION_212 (M33.2 close + close-out fold)
milestone_name: "F&I Intake Activation: Incoming Application to Active Deal Structure (derived DealStructure status + DealStructure read endpoint + F&I structuring UI + Playwright loop)"
increments_shipped: [0, 1, 2]
close_out_fold: true
sessions: [210, 211, 212]
commits_at_close: 6
---

# Milestone 33 — F&I Intake Activation — Retrospective

> Milestone 33 opened at SESSION_210 M33.0 planning under the
> durable primary operational-coverage lens, evaluated against
> the M32 §9 standing question (F&I depth-arc continuation vs
> breadth reset vs M32 §3 deferral closure). Resolved in favor
> of F&I depth-arc continuation — the sales-to-F&I bridge M32
> opened (writeup → intake receiver) receives its first F&I-
> side operator action (DealStructure creation).
>
> M33.1 shipped the backend substrate at SESSION_211 (two
> tenant-scoped subquery annotations on the M32.1 CA list
> queryset — `has_deal_structure` via `Exists` + `latest_deal_structure_id`
> via deterministic `Subquery` with `("-created_at", "-pk")`
> ordering; one new read endpoint at the canonical path
> `GET /admin/deal-structures/<int:pk>/` — thin wrapper on the
> shipped M10.2 `get_deal_structure` service verb; 20 new
> tests). DoD exception path invocation #8.
>
> M33.2 shipped the frontend UI + Playwright loop + close-out
> fold at SESSION_212 (this session): API-client extensions;
> `DealStructureForm` component with the D5 truthful-entry
> contract (blank ≠ 0; explicit "No trade payoff" checkbox
> affordance; basic consistency-warning surface; financial-
> language contract enforced); `DealStructureReadView`
> component with NULL-safe ratio display; `DealerFandIIncoming`
> extension (derived-status chip + row actions per D9 first-
> loop-only); new Playwright spec covering the full first-loop
> end-to-end; new idempotent seed command provisioning the
> dedicated `Structure Sam` fixture; +25 Vitest tests; +1
> acceptance journey (passes in 513ms). DoD satisfied
> directly.
>
> **Activation of 19-session-old M10.2 substrate.** The M10.2
> DealStructure model + service + create endpoint shipped at
> SESSION_107 and waited 19 sessions for an operator receiver.
> M33.2 delivers the receiver. Longest substrate-to-UI gap
> closed in the project's history.
>
> **First planning-time financial-language contract locked.**
> Sales targets vs proposed structure values; never lender-
> approved / lender-committed / actual until a verified
> LenderSubmission or approval workflow exists. Three-layer
> defense (D5 spec + Vitest anti-drift assertion + Playwright
> regex assertion on both form and read view). Candidate
> durable lesson `(dd)` awaiting first re-application to
> elevate.
>
> **First future capability recorded with full design contract
> at planning time.** Lender Fit Recommendations recorded per
> operator directive at M33.0 with the full structured/auditable/
> human-controlled contract (hard eligibility + likely fit +
> missing information + operator explanation + preserved human
> decision authority). NOT implemented in M33; blocked on
> named prerequisites. Design discipline demonstration.
>
> **§0.a M33.1 truthfulness correction on coverage projection**
> — first coverage-projection correction in project history.
> M33.0 §5.e projected 129 → 130 covered / 32 → 31 backend-
> only / 321 → 322 service verbs; all three were overstated.
> Audit script classifies "covered" by frontend-consumer
> presence, not backend test presence. Actual M33.1 close:
> 162/129/33/321. Corrected M33.2 projection landed exactly at
> **162/131/31/321**. Candidate durable lesson `(cc)` awaiting
> first re-application to elevate.

## 1. Planned scope

Per `MILESTONE_33_PLANNING.md` §5.a locked at SESSION_210
M33.0 open under the primary operational-coverage lens with
F&I depth-arc continuation framing resolving the M32 §9
standing question:

**F&I Intake Activation — Incoming Application to Active Deal
Structure.**

Extend the M32.3 F&I intake page with derived DealStructure
status ("Incoming" / "In progress"), enable "Start
structuring" from Incoming rows to create the first
DealStructure via the shipped M10.2 `POST /admin/deal-structures/`
endpoint, and enable "Open structure" from In progress rows
to view the latest DealStructure. Prove the complete first-
loop through a new Playwright journey.

Two-increment split scope-driven per §5.a surface size:

- **M33.1** — backend queryset annotation (D1 + D3) + read
  endpoint (D2) + ~15 tests. DoD exception path invocation
  #8.
- **M33.2** — frontend components (D5 + D6) + status chip
  (D4) + row actions (D9) + Playwright journey (D8) + new
  seed command. DoD directly satisfied.

Four planning-time corrections applied at M33.0 before §5.b
lock (M32 candidate lesson z — verification-driven revision
cycles, re-applied at M33.0):

1. **Financial-language contract** — sales targets / proposed
   structure values; never lender-approved / lender-committed
   / actual.
2. **Deterministic latest-structure selection** —
   `order_by("-created_at", "-pk")` + explicit tenant-scope
   filter as belt over model `clean()` + service
   `CrossTenantDealStructureError` suspenders.
3. **Canonical endpoint path** —
   `GET /admin/deal-structures/<int:pk>/` enforced verbatim
   across memo, handoff, frontend wrapper, tests, and
   Playwright expectations.
4. **Strengthened truthful-entry validation** — 0 valid only
   as explicit operator entry; blank never converts silently
   to 0; `trade_payoff` requires explicit "No trade payoff"
   checkbox affordance (not placeholder copy alone); basic
   consistency-warning surface (not full desking math).

## 2. What actually shipped

### M33.0 planning (SESSION_210)

Full planning memo `MILESTONE_33_PLANNING.md` + handoff
`SESSION_210_m33_inc0_planning.md` + `00-START-NEXT-SESSION.md`
flip. Two local commits: `7b8f6b6` (planning) + `e03d31c`
(hash backfill).

- §5.a target locked as F&I Intake Activation.
- §5.b D1–D10 locked in one draft (no revision rounds after
  the four corrections above applied at open).
- §5.c 10-item risk register (R1–R10).
- §5.d nine verifications resolving 1 blocking finding (§4.7
  field-level prepopulation truthful-entry) architecturally
  via D5 form contract.
- §5.e two-increment split.
- §5.f DoD exception at M33.1 + direct satisfaction at M33.2.
- §5.g rollback in reverse ship order (M33.2 → M33.1); no
  migration; no schema change.
- §5.h non-goals lock the discovery-rule perimeter — no state
  machine invention; no LenderSubmission/Stipulation/
  Contract/Funding/Chargeback UI; no lender ranking; no
  Lender Fit Recommendations (recorded as future candidate
  per D10); no PATCH/DELETE; no multi-structure UX; no
  vehicle-picker; no client-side payment auto-derivation; no
  desking arithmetic; no historical-migration modification.

No §0.a M33.0 amendments (M32 CI was verified green at open;
no regression to correct).

### M33.1 backend substrate (SESSION_211)

Two local commits: `eb50f94` (backend + tests + audit
regeneration + SESSION_211 handoff + `00-START-NEXT-SESSION.md`
flip) + `1e0008f` (hash backfill).

**Backend delivered:**

- `services/f_and_i/credit_application.py` — extended
  `list_credit_applications(...)` queryset with two subquery
  annotations, both explicitly tenant-scoped in the filter
  base (belt over model `clean()` + service
  `CrossTenantDealStructureError` suspenders):
  - `has_deal_structure=Exists(tenant_deal_structures)` per
    D1.
  - `latest_deal_structure_id=Subquery(tenant_deal_structures.order_by("-created_at", "-pk").values("pk")[:1])`
    per D3.
- `views_f_and_i.py` — extended
  `_project_credit_application_with_writeup(app)` with both
  new fields; new view function
  `admin_deal_structure_read(request, pk)` — thin wrapper on
  shipped `get_deal_structure(pk, dealership=dealership)`
  service verb; reuses shipped `_project_deal_structure(deal)`
  projection verbatim; `_M101_PERMS`; 404 fail-closed on
  unknown or cross-tenant.
- `urls.py` — new path
  `admin/deal-structures/<int:pk>/` named
  `admin-deal-structure-read` (canonical path locked at D2).
- `models.py` — `DealStructure` docstring extended with M33.1
  read-surface paragraph.

**No migration. No schema change. No service verb signature
changes. Historical migration NOT modified.**

**Tests: +20 in new file `test_m331_deal_structure_read.py`**
across four test classes: annotation with 0/1/N=3 structures
+ deterministic tie-break under shared `created_at` +
tenant-scope belt via direct-ORM bypass + composition with
`intake` filter; CA list projection extension; read endpoint
permission matrix (5 negative + 2 positive); read endpoint
behavior + projection-shape parity + NULL-safe ratios.
Backend baseline **4,995 → 5,015**.

**§0.a M33.1 truthfulness correction on M33.0 §5.e coverage
projection** — first coverage-projection correction in
project history. M33.0 projected 161/129/32/321 →
162/130/31/322; actual **162/129/33/321** (+1 endpoint / +1
backend-only; covered unchanged; service verbs unchanged
because the new endpoint reuses the shipped
`get_deal_structure` service verb). Audit script classifies
"covered" by frontend-consumer presence, not backend test
presence. Correction documented in
`SESSION_211_m33_inc1_backend.md` §5. Candidate durable
lesson `(cc)`.

DoD exception path **invocation #8** (M26 + M27.1 + M28.1 +
M29.1 + M30.1 + M31.1 + M32.1 + **M33.1**).

Zero-drift permission-class streak **36 → 37** (new endpoint
reused `_M101_PERMS` unchanged).

### M33.2 frontend UI + Playwright loop (SESSION_212 — this session)

**Frontend delivered:**

- `fAndIApi.ts` — `CreditApplicationProjection` extended with
  `has_deal_structure: boolean` + `latest_deal_structure_id: number | null`;
  new `DealStructureProjection` + `CreateDealStructureRequest`
  types; two new typed wrappers (`createDealStructure` POSTs
  to shipped M10.2 endpoint; `getDealStructure(id)` GETs the
  canonical M33.1 read path).
- NEW co-located components in
  `frontend/src/components/f-and-i/` (new package):
  - **`DealStructureForm.tsx`** — three-section layout with
    the full D5 truthful-entry contract. Sales-side targets
    prepopulate from `writeup_context.terms` with a "Sales
    target" affordance badge that flips to "Proposed" once
    the operator revises the value. F&I proposed structure
    values (`amount_financed`, `taxes`, `fees`, `trade_payoff`)
    blank on load with "F&I entry required" affordance.
    Submit disabled until all three required F&I fields
    carry explicit values (blank ≠ 0) AND `trade_payoff` is
    explicitly confirmed either by numeric entry or by the
    dedicated "No trade payoff" checkbox (checkbox locks the
    input to 0 and signals explicit zero-intent). Basic
    non-blocking consistency-warning surface fires when
    `trade_payoff > 0 && trade_allowance == 0`. Financial-
    language contract enforced — no "lender-approved" /
    "lender-committed" / "actual" anywhere in labels /
    placeholders / tooltips / aria-labels. `back_end_products`
    omitted per §5.b D5.
  - **`DealStructureReadView.tsx`** — three-section read-only
    layout. Every value labeled as "proposed structure value"
    (never "sales target" at read time — all values are
    committed to the structure). NULL-safe ratio display
    ("Not computable — requires income" for NULL PTI/DTI on
    M10.1-era CAs without income captured). No edit / PATCH
    / delete controls in M33.
- `DealerFandIIncoming.tsx` extended per D4 + D5 + D6 + D9:
  - Derived-status chip (Incoming amber / In progress blue)
    with three-signal a11y (double-marker testid
    `incoming-row-status-<state>-<pk>` + `aria-label` +
    visible label).
  - "Start structuring" button on Incoming rows only, further
    gated on `writeup_context !== null` per R1 mitigation
    (direct-create CAs render a documented affordance
    instead of the action).
  - "Open structure" button on In progress rows only.
  - Inline panel state (form-vs-read); refetch after
    successful create.
  - First-loop-only posture per D9 (no iteration UX).

**Playwright delivered:**

- NEW spec
  `acceptance/journeys/f_and_i_manager/fandi_intake_activation.spec.ts`
  — 14-step journey covering the full first-loop end-to-end.
  Financial-language regex assertion on BOTH the form and
  the read view (D8 anti-drift enforcement). Runs against
  the dedicated Structure Sam fixture; passes in 513ms.
- NEW idempotent seed command
  `seed_journey_fandi_intake_activation.py` provisioning the
  Structure Sam lead + FANDI-STRUCT-1 vehicle + approved+
  handed-off writeup + paired CA (NO DealStructure — the
  journey creates it via the M33.2 UI). Distinct four-square
  terms from M32.3 Intake Iris fixture so accidental
  cross-fixture matches fail loudly. Fully independent per
  M33 §5.c R7 independence guarantee.
- `login.setup.ts` SEED_COMMANDS extended with the new seed.
- Reuses shipped M32.3 `f_and_i_manager` persona; no new
  persona work; zero-drift persona registry.

**Tests: +25 Vitest across 4 new files** (`fAndIApi.dealStructures.test.ts`
+4; `DealStructureReadView.test.tsx` +4; `DealStructureForm.test.tsx`
+12; extended `DealerFandIIncoming.test.tsx` +5). Vitest
baseline **377 → 402**. Acceptance **24 → 25 spec files /
31 → 32 tests / 34.7s fresh-DB run**. Backend baseline
unchanged at 5,015 (no backend code in M33.2).

**Audit at M33.2 close: 162 / 131 / 31 / 321** — both M10.2
create + M33.1 read moved from backend-only to covered when
the frontend wrappers + Playwright journey landed. Refined
M33.2 projection landed exactly.

DoD satisfied directly via the fandi-intake-activation
Playwright journey — no exception path invocation at M33.2.

### Close-out fold (this session)

- `docs/CAPABILITY_MATRIX.md` — new §7θ M33 shipped surface
  entry (per M32 §7η precedent).
- `docs/roadmap/MILESTONE_33_RETROSPECTIVE.md` — this
  document.
- `docs/roadmap/MILESTONE_33_PLANNING.md` — status flipped
  from `active` to `historical` in frontmatter.
- `00-START-NEXT-SESSION.md` — flipped to SESSION_213 M34.0
  planning.
- `docs/handoffs/SESSION_212_m33_inc2_frontend.md` — this
  session's handoff.

## 3. Deviations from plan and reason

Two deviations from the M33.0 planning memo landed at
implementation time; neither changed the target or scope.

**§0.a M33.1 truthfulness correction on coverage projection.**
M33.0 §5.e projected 161/129/32/321 → 162/130/31/322 at
M33.1 close on the assumption that "the new read endpoint
covered because tests cover it." All three delta numbers were
overstated. Actual M33.1 close: **162/129/33/321**. The audit
script classifies "covered" by frontend-consumer presence,
not by backend test presence. Correction documented in
`SESSION_211_m33_inc1_backend.md` §5 so future planning
sessions distinguish frontend-consumer coverage from backend-
test coverage explicitly. Candidate durable lesson `(cc)`
recorded in §5 below. Refined M33.2 projection (162/131/31/321)
landed exactly at M33.2 close.

**Form header copy revision to preserve financial-language
contract.** Initial `DealStructureForm.tsx` header included
the sentence "No values are lender-committed — a lender
submission has not yet been created" — an explanatory
statement of the contract but literally containing the
"lender-committed" phrase, which triggered the Vitest anti-
drift regex assertion. Reworded to "A lender submission has
not yet been created — every value on this form is a
proposal." Same operator communication; no false-positive
trigger. Discovered during Vitest run at M33.2 close;
resolved in the same session before commit. No planning
implication.

## 4. Deferrals from M33 (all valid for later re-entry)

Per `MILESTONE_33_PLANNING.md` §5.h and §3, unchanged at
close:

- Any new stored `status` / `workflow_state` column.
- Submitted / Approved / Contracted / Funded / Chargedback
  status derivation or UI.
- LenderSubmission / Stipulation / Contract / BEPA /
  Funding / Chargeback UI extensions.
- Lender Fit Recommendations — recorded per D10 with full
  design contract; NOT implemented in M33; blocked on
  DealStructure creation operationally complete (M33
  delivers this) + LenderProgram rule verification +
  attribute retrieval + real dealer evidence.
- PATCH or DELETE on DealStructure.
- Multi-structure UX (list-per-CA, activate, delete,
  iterate).
- Iteration flow (second DealStructure on already-In-progress
  CA).
- Vehicle-picker substrate for direct-create CAs (M10.1
  without hand-off upstream). M33 covers writeup-originated
  CAs only.
- F&I role extension to `admin_lead_detail`.
- Client-side monthly-payment auto-derivation via
  `services.payment_engine`.
- Full desking arithmetic
  (`amount_financed = sale_price + taxes + fees + trade_payoff
  - down_payment - trade_allowance`).
- Pagination on `admin/credit-applications/list/`.
- Cross-lead sales-manager pending-approval queue page
  (unchanged M32 §3 deferral).
- F&I-scoped lead-context view (unchanged M32 §3 deferral).
- Retroactive modification of historical migration 0026.
- All prior M32 §3 + M31 §3 + M30 §3 + M29 §3 + M28 §3 +
  M27 §3 + M25 §4 deferrals — unchanged.

## 5. Durable design principles surfaced or reinforced

### Reinforced / re-applied

**(z) verification-driven revision cycles at planning-open**
(M32.0 origin — first re-application). At M33.0, four
correction rounds applied at planning-open before §5.b lock
(financial-language contract; deterministic ordering +
tenant-scope filter; canonical endpoint path; strengthened
truthful-entry with explicit affordance + basic consistency
warning). None changed the target selection; all strengthened
the locked design. Elevated at M33 close to **"load-bearing
across two milestones"** (M32.0 + M33.0).

**(aa) historical-migration-immutability discipline** (M32.1
origin — first re-application). M33 §5.h explicitly forbids
retroactive modification of historical migration 0026;
architectural evolution recorded in current model + service
docstrings + planning memo + retrospective. Elevated at M33
close to **"load-bearing across two milestones"** (M32.1 +
M33 both invoke the discipline; M33 does so without shipping
a new migration).

**(u) audit correctness as supporting infrastructure**
(M12.0-era origin). M33.1 tenant-scope belt on the subquery
annotation is the third layer of defense over the model
`clean()` + service `CrossTenantDealStructureError`
suspenders — protects the derived-status projection from
hypothetical bug-created cross-tenant rows even though the
first two layers already prevent legitimate ones. Direct-ORM-
bypass test asserts the belt fires.

### Newly surfaced (candidates for M34+ elevation)

**(cc) coverage-projection truthfulness — distinguish
frontend-consumer coverage from backend-test coverage.**
M33.0 §5.e projected 129 → 130 covered / 32 → 31 backend-
only / 321 → 322 service verbs at M33.1 close on the false
assumption that "the new read endpoint is covered because
tests cover it." All three deltas were overstated. Audit
script classifies "covered" by frontend-consumer presence.
New endpoints correctly stay backend-only until UI lands
(matching M32.1 precedent verbatim). Service verbs unchanged
when a new view function reuses an existing service verb.
Candidate lesson: at every §5.e phase-projection lock, name
the specific coverage-classification semantic being invoked
and validate the projection against a similar recent
increment's actual result. Awaits first re-application at
M34+.

**(dd) planning-time financial-language contract with
three-layer defense.** M33.0 §5.b D5 locks financial-value
language semantics ("sales targets" vs "proposed structure
values"; never "lender-approved" / "lender-committed" /
"actual" until a verified LenderSubmission exists). D5 spec
+ Vitest anti-drift regex assertion + Playwright regex
assertion across form and read view = three-layer defense.
First planning-time contract in project history on financial
vocabulary semantics. Candidate lesson: when a UI describes
values that carry semantic weight tied to the state of a
downstream entity (lender submission, contract signature,
funding, etc.), lock the vocabulary at planning time with
enforcement in both static tests and operational Playwright
assertions. Awaits first re-application at M34+.

**(ee) future capability recording with full design
contract at planning time.** M33.0 §3 + §5.b D10 record
Lender Fit Recommendations with the full contract (hard
eligibility + likely fit + missing information + operator
explanation + preserved human decision authority) + named
prerequisites, without implementing any part of it. Per
operator directive. Design discipline demonstration —
captured, deferred, blocked on named prerequisites; not
implemented; discoverable by future planning sessions via
`MILESTONE_33_PLANNING.md` §3 + retrospective §9. Candidate
lesson: when scope naturally suggests an adjacent future
capability but operator evidence for it doesn't exist yet,
record the full contract at planning time so scope stays
disciplined and the future capability is not lost. Awaits
first re-application at M34+.

**(y) Playwright-independent-fixture pattern** (M32.3
origin) — re-applied at M33.2 with the dedicated
`Structure Sam` fixture (distinct from M32.3 `Intake Iris`
and M32.2 `Sales Sam`). Both journeys pass in the same run
without cross-contamination; test order irrelevant. Elevated
at M33 close to **"load-bearing across two milestones"**.

**(bb) non-navigational cross-role UI when role-gating
conflicts** (M32.3 origin). NOT re-applied at M33 — the
M33.2 UI extends the M32.3 non-navigational rows in place
(status chip + row actions) without introducing new cross-
role navigation. Discipline preserved but not tested at
M33; awaits a future milestone where role-gating conflict
recurs.

## 6. Streak accounting at M33 close

- **Planning-time as-recommended streak:** **11 → 12** at
  M33.0 close. Unchanged at M33.1 (§0.a truthfulness
  correction does not affect target-selection streak per
  convention). Unchanged at M33.2 (pure implementation).
  Historical run of 89 across M10 → M23 preserved.
- **Zero-drift permission-class streak:** **36 → 37**
  consecutive milestones (M10 → M33). M33.1's new endpoint
  reused `_M101_PERMS` unchanged; M33.2 shipped no new
  backend endpoints.
- **Substrate-compound-value continuation:** M32 broke the
  M27.1 → M31 five-link streak by choosing breadth. **M33
  restarts the arc at 2 links** (M32 sales-to-F&I bridge +
  M33 F&I first-loop activation).
- **DoD exception path invocations:** **7 → 8** (M26 +
  M27.1 + M28.1 + M29.1 + M30.1 + M31.1 + M32.1 + **M33.1**).
  M33.2 satisfies DoD directly. Eight-invocation pattern
  firmly established.
- **First milestone to activate M10.2 substrate
  operationally** — 19 sessions after M10.2 shipped at
  SESSION_107. Longest substrate-to-UI gap closed at M33.
- **Second consecutive customer-facing milestone in the F&I
  domain** (M32 shipped intake receiver; M33 ships first
  F&I action).
- **First planning-time financial-language contract locked.**
- **First future capability recorded with full design
  contract at planning time** (Lender Fit Recommendations).
- **First §0.a truthfulness correction on a coverage
  projection** (M33.1).
- **First Playwright fixture-independence re-application**
  (M33.2 Structure Sam distinct from M32.3 Intake Iris).

## 7. Baselines at M33 close

- Backend: **5,015 pass**, 1 skipped, 0 fail (177s).
- Frontend Vitest: **402 pass** across 45 files (~6.3s).
- Acceptance: **25 spec files / 32 tests / 0 failed /
  34.7s** on fresh DB run.
- Migrations: **0001–0051** (unchanged since M32.1; no new
  migration in M33).
- Audit: **162 / 131 / 31 / 321** at M33.2 close.
- DRF admin surface: **122** endpoints (M32.1 121 → +1 at
  M33.1).
- Frontend operator routes: **21** (unchanged; M33.2 extends
  `DealerFandIIncoming.tsx` in place).
- Frontend components: new `frontend/src/components/f-and-i/`
  package with `DealStructureForm.tsx` + `DealStructureForm.test.tsx`
  + `DealStructureReadView.tsx` + `DealStructureReadView.test.tsx`.
- Service verbs enumerated: **321** (unchanged; new read
  endpoint reuses shipped `get_deal_structure` verb).
- Permission classes: **7 actual**, zero-drift streak **37
  consecutive** milestones (M10 → M33).
- Playwright personas: **6 actual** (unchanged since M32.3;
  M33 reused `f_and_i_manager`).
- Playwright fixtures: **Intake Iris** (M32.3) + **Structure
  Sam** (M33.2) both live and fully independent.

## 8. Corrections (post-close)

*(None at close-out fold. Reserved for future factual
corrections per DOC_GOVERNANCE handoff-immutability
discipline.)*

## 9. Evidence-based candidates for M34

**Elevated (highest recommendation strength for M34.0):**

- **NEW C — F&I chargeback substrate.** Sixth-link
  substrate-compound-value candidate; still gated on pilot
  evidence today (unchanged from M30/M31/M32/M33 §9). Now
  with even stronger post-M33 context: F&I team can create
  DealStructures (M33.2 UI) — the natural next step in the
  F&I depth arc after post-funding chargeback exposure
  surfaces operator evidence. If pilot evidence surfaces at
  M34.0 open, this becomes the natural next depth-arc link
  and would restart the substrate-compound-value continuation
  toward 3 links (M32 + M33 + M34).
- **Lender Fit Recommendations (D10 future candidate
  elevation).** Recorded at M33.0 with full design contract.
  M33 delivered the first blocker (DealStructure creation
  operationally complete). Three blockers remain (LenderProgram
  rule verification; attribute retrieval; real dealer
  evidence on lender selection). Elevate to top of candidate
  list once operator evidence surfaces on lender selection
  criteria. Structured, auditable, human-controlled ranking
  — never opaque AI recommendation.
- **F&I workflow-state extensions beyond M33's two derived
  states** (Submitted / Approved / Contracted / Funded /
  Chargedback). Would extend the M33.2 In-progress state
  into a proper multi-state F&I workflow tracker. Requires
  operator evidence on state model — narrowed to M33's two
  derived states per operator directive at M33.0.
- **F&I-scoped lead-context view** (NEW at M32.3 §3; still
  evidence-gated at M33 close). M33.2 preserved M32.3
  non-navigational inline triage. If operator evidence
  surfaces need for richer context, elevate as either
  (a) new endpoint with narrowed projection or (b) selective
  role-gating expansion on `admin_lead_detail` with what-
  leaks review.
- **Cross-lead sales-manager pending-approval queue page**
  (NEW at M32.3 §3; still evidence-gated). Per-lead
  LeadDetailModal approval assumed sufficient through M33
  close.
- **Direct-create CA structuring branch** — M33 explicitly
  deferred (§5.h). Would require a vehicle-picker substrate.
  Elevate if operator evidence surfaces on direct-create CA
  volume.
- **Iteration UX** — creating a second DealStructure for a
  CA already In progress (subprime counter, revised terms
  after stip clears, etc.). M33 first-loop-only per D9.
  Elevate if operator evidence surfaces on iteration
  frequency.
- **PATCH on DealStructure** — activation-vocabulary-
  asymmetry preserved through M33 (create-and-read only).
  Elevate if operator evidence surfaces on edit-existing-
  structure need.
- **NEW O2 — Row 5 public-fetch-helper regex refinement**
  (M26/M27/M28/M29/M30/M31/M32/M33 deferral, unchanged).
  Requires SESSION-189-§3-style tracing at open.
- **NEW O3 — Rows 1–4 plain-string-literal investigation**
  (deferral count matches O2).
- **H — Test-hygiene remediation.** Three shared-DB non-
  idempotent journeys unchanged from M27.2 → M33.2 close.
  CI-stability compound value grows with journey count
  (now 25 spec files / 32 tests).

**Fresh direct-operator gaps surveyed (breadth candidates):**

- **Vendor detail (#43)** — wrapper-only; small polish.
- **Photo reorder (#65)** — wrapper-only; small polish
  + D&D primitive selection.
- **Broader F&I subdomain (#89–101 excl. chargeback which
  is NEW C)** — 11 uncovered endpoints post-M33 (down from
  12 pre-M33 as M33.1 read joined the covered side); still
  too large without operator direction.

**Gated (unchanged from M29+M30+M31+M32+M33 close):**

- T (real tester feedback); U (hosted-demo substrate); L
  (first-live-pilot staging); M (multi-operator support —
  breaks the M10 → M33 zero-drift streak with intent).

**Deferred pending evidence:**

- D (LLM router / cost caps).

**Deferred but stable:**

- G (dashboard testid hardening).

**Deferred at M33 §3 / M32 §3 / M31 §3 / M30 §3 / M29 §3 /
M28 §3 / M27 §3 / M25 §4:** all carried forward unchanged.

**Standing question for M34:** the F&I depth arc has 2 links
(M32 + M33). Three natural next moves: (a) **continue the
F&I depth arc** via NEW C chargeback substrate (third link —
sixth substrate-compound-value link overall — if pilot
evidence surfaces) OR NEW F&I workflow-state extensions
(broader state model beyond Incoming / In progress) OR
Lender Fit Recommendations (three blockers remain but M33
delivered the first); (b) **reset to breadth** via a fresh
direct-operator gap surveyed from the 31 backend-only audit
endpoints; (c) **close an M33 §3 deferral** like the direct-
create structuring branch or iteration UX. Evaluate through
the primary operational-coverage lens first; secondary
reframes only if evidence surfaces.
