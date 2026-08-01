---
title: "SESSION_051 handoff — Milestone 2 · Increment 5 (acquisition-price safety scrub)"
status: historical
type: handoff
date: 2026-07-31
session: 051
milestone: 2
milestone_status: in_progress
increment: 5
increment_status: shipped
commit: ea0ee04
---

# SESSION_051 — Milestone 2 · Increment 5 (M2.5 — acquisition-price safety scrub)

## What shipped

One thing: a narrow defense-in-depth scrub that catches internal
cost / investment leakage in LLM output. Joins the always-runs
section of `apply_post_llm_scrubs`. Text-only. Zero DB access.
Deterministic. Additive only — no existing scrub was modified,
no signature changed, no schema drift, no frontend touched.

## Scrub behavior shipped

**Function:** `services/llm_safety.py::_scrub_acquisition_price(text) -> Tuple[str, bool]`.

Mirrors the existing `_scrub_indie_prohibited` /
`_scrub_invented_promotion` / `_scrub_invented_appointment`
shape:
- Iterates a `_ACQUISITION_PRICE_PATTERNS` list of
  `(compiled_regex, replacement_str)` tuples.
- Case-insensitive matching.
- Substitution + whitespace-and-punctuation cleanup identical
  to the sibling scrubs.
- Returns `(cleaned_text, changed_bool)`.

**Pipeline placement:** `apply_post_llm_scrubs` gained a new
branch labelled `# 2b. Acquisition-price scrub` immediately after
the core partial scrubs and before the kind-specific scrubs. The
scrub fires on EVERY `kind` (`chat`, `vehicle_ask`, `ad`,
`follow_up`). No dealer-type gating (ledger data is sensitive
regardless of indie/franchise). Recorded in `scrubs_fired` as
`"acquisition_price"`.

**Precedence preserved:** the scrub runs AFTER
`detect_unsafe_response` (dealer-cost wholesale rewrite) and
AFTER `scrub_post_llm_override` (negotiation / handoff wholesale
rewrites). Where a pre-existing wholesale rewrite fires,
`apply_post_llm_scrubs` short-circuits with `dropped_reason` set
and never reaches the acquisition-price partial scrub — that's
exactly right (a wholesale rewrite is a stronger safety response
than a partial scrub).

**NOT called "stage 17" in code** per the SESSION_051 brief.
The numbered-stage count in `CAPABILITY_MATRIX.md` remains a
documentation concept, not a code contract. The scrub name
`"acquisition_price"` recorded in `scrubs_fired` is the durable
identifier; ordering dependencies would be brittle against
future scrub additions.

## Pattern families covered

Twelve regex patterns, each anchored on a verbal cost-ownership
signal (never a generic dollar detector — favor false negatives
over broad false positives, per SESSION_051 brief):

| Family | Example match | Replacement |
|--------|---------------|-------------|
| "we paid $X for this/at auction" (redundant with existing dealer-cost detector; defensive) | *"We paid $18,500 for this truck at auction."* | *"we picked this one up carefully"* |
| "our cost was $X" (redundant with existing detector; defensive) | *"Our cost on this SUV was $22,000."* | *"our current pricing reflects the market"* |
| **"we're / we are in it for $X"** | *"We're in it for $19,550 total."* | *"we've set a competitive price"* |
| **"we've got / we have $X in this/the &lt;word&gt;"** | *"We've got $20,300 in this vehicle."* | *"we've set a competitive price"* |
| **"our purchase price"** | *"Our purchase price is $17,500 on this piece."* | *"our current pricing"* |
| **"purchase price was/of $X"** (not "is" — customer-facing sticker phrasing) | *"The purchase price was $18,000 at the auction."* | *"our current pricing is what matters"* |
| **"acquired [words] for/at $X"** | *"Acquired the vehicle for $14,800 in a wholesale deal."* | *"brought this into inventory carefully"* |
| **"[our] total investment [is/of/was] $X"** | *"Total investment $21,030 on this Ranger."* | *"a strong value"* |
| **"our investment in this/the &lt;word&gt;"** (no $ required) | *"Our investment in this vehicle drives our pricing."* | *"our commitment to a fair price"* |
| **"floor plan interest"** / **"floor-plan interest"** (always internal) | *"Floor-plan interest of $387.74 lands next week."* | *""* (deletion) |
| **"[we] spent $X on recon/reconditioning/repair"** | *"Spent $1,240 on reconditioning."* | *"invested time in preparing the vehicle"* |
| **"recon costs were/of $X"** | *"Recon costs were $920 on this SUV."* | *"the vehicle was carefully prepared"* |

**Bold** entries are the incremental coverage the M2.5 scrub
adds. Non-bold entries ("we paid" / "our cost") are already
caught by the pre-existing `_RESPONSE_FORBIDDEN_PATTERNS`
(wholesale-rewrite class) — the M2.5 patterns for those phrases
are DEFENSIVE redundancy that will never fire under current
conditions but provide defense-in-depth if a future session
loosens the pre-existing detector.

## Replacement strategy

Every substitution is a **neutral phrase**, never a fabricated
customer-facing number:

- *"we picked this one up carefully"*
- *"our current pricing (reflects the market)"*
- *"we've set a competitive price"*
- *"our commitment to a fair price"*
- *"a strong value"*
- *"brought this into inventory carefully"*
- *"the vehicle was carefully prepared"*
- *""* (deletion — for floor-plan interest, which has no
  customer-facing counterpart)

The `_scrub_acquisition_price` function also runs the same
`\s{2,}` → single-space and `\s+([.,;:!?])` → punctuation cleanup
that the sibling scrubs use, so the remaining response reads
coherently. Locked by
`PositiveCoherentRemainder.test_replacement_leaves_no_double_space`
+ `.test_replacement_leaves_no_orphan_space_before_period`.

## Negative corpus summary

The load-bearing part of the increment per the SESSION_051 brief.
Every case verifies the scrub does NOT fire, across every current
`kind`. Categories covered:

| Category | Example |
|----------|---------|
| Asking price | *"This truck is asking $18,500 today."* |
| Priced at | *"Priced at $24,900 out the door."* |
| Sale price | *"The sale price is $22,750 including all fees."* |
| Monthly payment | *"Your monthly payment is around $450."* |
| Down payment | *"A $2,000 down payment brings the monthly payment down."* |
| Zero down | *"$0 down today."* |
| Save amount | *"Save $1,000 on your next purchase."* |
| Trade value | *"Your estimated trade value is around $8,500."* |
| Budget | *"Your budget is around $20,000."* |
| Discount | *"There's a $500 discount available on select models."* |
| APR / taxes / fees | *"Figure in about $2,500 in fees and taxes."* |
| Warranty price | *"The extended warranty costs $1,200."* |
| Product pricing | *"The GAP product is $795 and the T&W package is $499."* |
| Affordability | *"This F-150 fits well within your $22,000 budget."* |
| "What's the asking price…" (customer-side query) | *"What's the asking price on the blue F-150?"* |
| Customer-bring-this-amount | *"Bring $2,500 to cover the down payment."* |
| Registration fee paid on behalf | *"We paid $500 to the DMV on your behalf for your registration."* (Note: this DOES trigger the pre-existing `dealer_cost_safety` wholesale rewrite; M2.5 scope only asserts acquisition_price doesn't fire.) |
| "Our current pricing" survives | *"Our current pricing on this F-150 reflects the market."* |
| Warranty **costs** (verb, not "our cost") | *"The bumper-to-bumper warranty costs $1,200."* |
| Customer-side **your** investment | *"Your investment in reliability starts with a good used vehicle."* |
| **Purchase price IS $X** (customer-facing boundary) | *"The purchase price is $18,500 for the 2024 F-150."* |

The `test_purchase_price_is_customer_facing` case is particularly
important — it locks the deliberate `was`-and-`of`-only boundary
in the "purchase price" pattern. A future session tempted to add
`is` would break this test and be forced to reconsider.

## Tests added — 71 new, all passing

`test_acquisition_price_scrub.py`, 8 classes:

| Class | Tests | Locks |
|-------|-------|-------|
| `PositivePhraseFamilies` | 25 | Each incremental-coverage phrase family fires the scrub; scrubs_fired includes "acquisition_price"; sensitive figures are gone from cleaned text |
| `PositiveVariants` | 8 | Case-insensitivity + comma / decimal / no-thousands / bare-number / extra-whitespace tolerance |
| `PositiveMultipleLeakagesInOneResponse` | 1 | Multiple leakage phrases in one response all strip together; legitimate customer-facing figure survives |
| `PositiveFiresForEveryKind` | 4 | Fires on chat / vehicle_ask / ad / follow_up |
| `PositiveCoherentRemainder` | 2 | No double spaces or orphan punctuation after substitution |
| `PrecedencePreservedForExistingWholesaleRewrites` | 5 | "we paid" and "our cost" trigger `dealer_cost_safety` wholesale rewrite (existing behavior); negotiation wholesale rewrite still wins; `rate_language` partial fires alongside acquisition_price when both patterns present |
| `NegativeCorpusLegitimateCustomerLanguage` | 21 | Broad negative corpus above — none fire acquisition_price; customer-facing dollar amounts survive |
| `PublicSignatureUnchanged` | 3 | Three-tuple return shape; all four kinds still accepted; empty input still short-circuits |
| `DeterministicAndSideEffectFree` | 2 | Same input → same output; `_scrub_acquisition_price` runs with zero DB queries |

Total: 71 tests, 9 classes.

## Backend baseline

- **`python3 manage.py test dealer_ai` → 1,696 pass** (1,625
  baseline + 71 new M2.5 tests), 1 skipped, 0 fail. **Zero
  regressions in any existing chat / vehicle_ask / ad /
  follow_up test.** This was the load-bearing safety check for
  M2.5 and it passed cleanly.
- **`makemigrations dealer_ai --check --dry-run` → "No changes
  detected".** Zero schema drift.

## Compatibility result

Every existing invariant holds. Explicit rechecks:

- **All 16 pre-existing scrub stages unchanged.** No file in
  `services/chat_engine.py` touched. `_RESPONSE_FORBIDDEN_PATTERNS`
  unchanged. `_POST_LLM_OVERRIDE_PATTERNS` unchanged.
  `_RATE_SCRUB_PATTERNS` unchanged.
  `_scrub_indie_prohibited` / `_scrub_invented_promotion` /
  `_scrub_invented_appointment` all byte-for-byte identical.
- **`apply_post_llm_scrubs` signature and return shape
  unchanged.** Three-tuple `(cleaned_text, scrubs_fired,
  dropped_reason)`. Same four `kind` values accepted.
- **Precedence order preserved:** wholesale-rewrite branches
  (dealer-cost, negotiation) still short-circuit before any
  partial scrub runs. Rate-language / directive /
  default-assumption partial scrubs still run in their existing
  order. Indie-prohibited scrub still dealer-type gated and
  still runs last. Acquisition-price scrub joins the always-runs
  section as `# 2b`, between the core partial scrubs and the
  kind-specific scrubs.
- **M2.1 through M2.4b unchanged.** No file in
  `services/vehicle_ledger.py`, `services/payment_engine.py`,
  `services/dealer_config.py`, `models.py`, `admin.py`,
  `permissions.py`, `tenancy.py`, `settings.py`, `urls.py`,
  or `views.py` touched. All 44 M2.2 tests + 29 M2.3 tests +
  37 M2.4a tests + 19 M2.4b tests pass unchanged.
- **Public routes / auth substrate / frontend** all untouched.

## Files touched this session

**Backend (1 file modified, 1 file new):**

- `backend/dealer_ai/services/llm_safety.py` — added
  `_ACQUISITION_PRICE_PATTERNS` (12 patterns) + module-level
  design-principle comments + `_scrub_acquisition_price` function
  + branch `# 2b` inside `apply_post_llm_scrubs`. No other
  changes.
- `backend/dealer_ai/tests/test_acquisition_price_scrub.py` —
  **new file**, 71 tests across 9 classes.

**Docs (3 files):**

- `docs/roadmap/MILESTONE_2_PLANNING.md` §1.5 heading renamed
  from "17th safety pipeline stage" to "defense-in-depth"; §1.5
  body updated to remove the "16-stage count becomes 17" claim
  per the SESSION_051 brief's guidance on not baking numbered-
  stage into code or docs; §7.b M2.5 row marked SHIPPED with
  full summary.
- `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
  — this file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_052 =
  M2.6.

**No changes to:** `services/vehicle_ledger.py`,
`services/payment_engine.py`, `services/dealer_config.py`,
`services/chat_engine.py`, `services/tenancy.py`, `models.py`,
`admin.py`, migrations, `urls.py`, `views.py`, `permissions.py`,
`settings.py`, or any frontend file.

## Exact recommended scope for M2.6 (SESSION_052)

**M2.6 — Ledger API + permission matrix.** Per
`MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.6.

### In scope

1. **Three admin endpoints under
   `/api/dealer-ai/admin/vehicles/<stock_number>/`:**
   - `GET .../ledger/` — returns
     `{acquisition: {...} | null, costs: [...], totals: {...},
     days_in_inventory: int|null}`.
   - `POST .../acquisition/` — creates or updates the OneToOne
     via `services.vehicle_ledger.record_acquisition(...)`.
     Returns `{acquisition: {...}, created: bool}`.
   - `POST .../costs/` — creates one immutable cost row via
     `services.vehicle_ledger.add_cost(...)`. Returns
     `{cost: {...}}`.

2. **Permission composition** on all three:
   `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
   Reuses the Milestone 1 · Increment 4D permission class
   unchanged. Recon-manager access is deferred to Milestone 4
   per M2 §5 (planning artifact).

3. **Tenant scoping** at every endpoint:
   - `dealership = get_current_dealership(request)` at the top
     of the view.
   - `Vehicle.objects.filter(dealership=dealership)
     .get(stock_number=<url_kwarg>)` — cross-tenant `stock_number`
     lookups return 404 (fail closed).
   - Service functions receive `dealership=dealership` explicitly.

4. **URL registrations** in `dealer_ai/urls.py` — three `path()`
   entries under the existing `/admin/` prefix.

5. **Focused six-case permission matrix** per endpoint:
   - Unauthenticated → 401.
   - Authenticated advisor at same dealership → 403.
   - Authenticated advisor at wrong dealership → 403.
   - Authenticated sales_manager at same dealership → 200.
   - Authenticated dealer_owner at same dealership → 200.
   - Authenticated sales_manager targeting cross-tenant
     stock_number → 404 (fail closed).

6. **Serializer layer** — new
   `dealer_ai/serializers.py::VehicleAcquisitionSerializer` +
   `VehicleCostSerializer` + `LedgerTotalsSerializer` (or DRF
   Serializer classes / simple dict projections; SESSION_052
   picks the shape). Read-only for the GET endpoint;
   POST endpoints validate inputs and forward to the ledger
   service.

7. **Focused tests** — mirror the M1 · 4D `admin_lead_*` test
   shape.

### Out of scope for M2.6

- Frontend (M2.7).
- Milestone-2 closeout retrospective (M2.8).
- Any modification to the M2.1 models, M2.2 service, M2.3 read
  model, M2.4a engine, M2.4b command, or M2.5 scrub.
- Any modification to Milestone 1 permissions / tenancy /
  authentication.
- Async / Celery.
- Curtailment or vendor FK.
- `expected_gross` (M3).
- New migrations (M2.6 should be pure Python + URL + view work).

### Verification steps at M2.6 close

- Focused permission-matrix tests pass for all three endpoints.
- Full backend suite passes (target: 1,696 + M2.6 additions).
- `makemigrations --check --dry-run` reports no changes.
- Manual `curl` smoke against dev DB with `smoke_owner` session:
  - `GET .../ledger/` returns expected JSON shape.
  - `POST .../acquisition/` upserts.
  - `POST .../costs/` posts.
- No touch to any file outside `views.py`, `urls.py`,
  `serializers.py` (new or existing), and the new test file.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md` (M2.6 endpoints
   inherit the four-layer separation + §7 composition patterns)
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lessons
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.6
7. `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
   (this file — M2.6 authoritative scope)
8. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
9. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
10. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
11. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
12. `docs/handoffs/SESSION_046_milestone_2_schema.md`
13. `docs/handoffs/SESSION_045_milestone_2_planning.md`
14. Current source code — new imports available:
    - `dealer_ai.services.llm_safety::_scrub_acquisition_price`
      (private; wired through `apply_post_llm_scrubs`).
    - All prior M2.1–M2.4b + M1 imports unchanged.

Planning docs are claims. Rules + research + code are facts.
