---
title: "SESSION_052 handoff — Milestone 2 · Increment 6 (ledger API + permission matrix)"
status: historical
type: handoff
date: 2026-07-31
session: 052
milestone: 2
milestone_status: in_progress
increment: 6
increment_status: shipped
commit: 9e5f6d7
---

# SESSION_052 — Milestone 2 · Increment 6 (M2.6 — ledger API + permission matrix)

## What shipped

Three tenant-safe admin endpoints exposing the M2.1–M2.5 ledger
surface. Reuses M1 · Increment 4D permission class unchanged. All
writes route through the ledger service (never bypass to
`objects.create`). No schema drift, no new migrations, no frontend
work.

## Endpoints shipped

| Method | URL | Purpose |
|--------|-----|---------|
| `GET`  | `/api/dealer-ai/admin/vehicles/<stock_number>/ledger/`      | Full ledger read — vehicle header + acquisition │ null + ordered costs + totals + `days_in_inventory` + `projected_gross` |
| `POST` | `/api/dealer-ai/admin/vehicles/<stock_number>/acquisition/` | Upsert acquisition — wraps `record_acquisition` |
| `POST` | `/api/dealer-ai/admin/vehicles/<stock_number>/costs/`       | Post one immutable cost row — wraps `add_cost` |

## Request and response contracts

**GET .../ledger/** — 200 response shape (all money fields
strings; consumer must not parse through JavaScript `Number`):

```json
{
  "vehicle": {
    "stock_number": "F25-014", "vin": "1FTER1EH...",
    "year": 2024, "make": "Ford", "model": "Ranger", "trim": "XLT",
    "price": "24900.00", "display_name": "2024 Ford Ranger XLT"
  },
  "acquisition": {          // or null
    "source": "auction", "source_display": "Auction",
    "source_detail": "Manheim Phoenix",
    "purchase_price": "18500.00", "purchase_date": "2026-05-01",
    "buyer_fees": "475.00", "arbitration_fees": "0.00",
    "transportation_cost": "850.00", "title_acquisition_cost": "125.00",
    "notes": "...", "created_at": "...", "updated_at": "..."
  },
  "costs": [                // chronological ASC by incurred_at, pk tie-break
    {
      "id": 42, "category": "parts", "category_display": "Parts",
      "category_group": "recon",
      "amount": "300.00", "incurred_at": "2026-05-15T12:00:00Z",
      "vendor": "...", "reference": "...", "notes": "...",
      "is_estimate": false, "created_by": "smoke_owner",
      "created_at": "..."
    }
  ],
  "totals": {
    "acquisition_total": "19950.00",
    "flooring_total": "0.00", "recon_total": "300.00",
    "administrative_total": "0.00", "photography_total": "0.00",
    "actual_cost_total": "300.00", "estimated_cost_total": "0.00",
    "total_investment": "20250.00",
    "projected_total_investment": "20250.00"
  },
  "days_in_inventory": 45,  // or null when no acquisition
  "projected_gross": "4650.00"
}
```

**POST .../acquisition/** — request body:

```json
{
  "source": "auction",       // required, one of ACQUISITION_SOURCE_CHOICES
  "source_detail": "",       // optional
  "purchase_price": "18500.00",   // required, Decimal, min_value=0
  "purchase_date": "2026-05-01",  // required, ISO date
  "buyer_fees": "475.00",         // optional, default 0
  "arbitration_fees": "0",        // optional, default 0
  "transportation_cost": "850.00",// optional, default 0
  "title_acquisition_cost": "125.00", // optional, default 0
  "notes": ""                     // optional
}
```

Response (201 create / 200 update):

```json
{"acquisition": {...projection...}, "created": true|false}
```

**POST .../costs/** — request body:

```json
{
  "category": "parts",        // required, one of VEHICLE_COST_CATEGORY_CHOICES
  "amount": "300.00",         // required, signed Decimal
  "incurred_at": "2026-05-15T12:00:00Z",  // required, ISO datetime
  "vendor": "",               // optional
  "reference": "",            // optional
  "notes": "",                // optional
  "is_estimate": false        // optional, default false
}
```

Response (201):

```json
{"cost": {...projection...}}
```

**`created_by` is NOT accepted in the request body** — the view
always attaches `request.user`. A client-supplied `created_by`
field is ignored (locked by
`CostCreatedByAttribution.test_client_supplied_created_by_is_ignored`).

## Validation approach

**DRF `Serializer` classes for input**, chosen over hand-rolled
`request.data.get(...)` for four reasons:

1. **Decimal safety.** DRF's `DecimalField(max_digits=..., decimal_places=...)` parses via `Decimal(str(value))` — never
   through binary float. Matches the M2.4a engine's coercion path.
2. **Choices enforcement from model constants.** `ChoiceField(
   choices=ACQUISITION_SOURCE_CHOICES)` and `choices=VEHICLE_COST_CATEGORY_CHOICES`
   — the serializer stays in lockstep with the canonical model
   enums. `test_source_choices_enum_covers_all_canonical_values`
   locks this.
3. **Field-level errors surface cleanly.** `is_valid(raise_exception=True)` →
   DRF returns 400 with `{"field_name": ["error message"]}` — no
   stack traces to the caller.
4. **Consistency with existing admin surface.** M1 · 4D uses the
   same `Serializer` + `is_valid(raise_exception=True)` pattern
   (see `AssignLeadSerializer` in `serializers.py`).

**Output projection = `ModelSerializer` + hand-quantized totals
dict.** The `ModelSerializer` handles Decimal → string conversion
natively. The totals block is built by hand (LedgerTotals is a
dataclass, not a Django model), so a small
`_money_str(value)` helper quantizes every money field to two
decimal places with `ROUND_HALF_UP` before `str()`. Otherwise ORM
`Sum` aggregation can strip trailing zeros
(`Decimal("300.00") + Decimal("300.00") → Decimal("300")` in some
backends), producing inconsistent `"300"` vs `"300.00"` on the
wire.

**Business validation stays in the service layer** —
`_scrub_acquisition_price` / `CrossTenantLedgerError` /
`full_clean()` invariants all still fire on the write path. The
serializer owns request-shape validation (types, choices,
presence); the service owns cross-tenant + business-rule
validation. Two layers of defense; no duplicated logic.

## Permission and tenant-scoping behavior

**Permission composition** on all three endpoints:
`[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]` —
reused byte-for-byte from Milestone 1 · Increment 4D. No new
permission class introduced.

**Tenant scoping pattern** — mirrors `admin_lead_assign`
(SESSION_042) exactly:

1. `dealership = get_current_dealership(request)` at the top of
   the view (once per request per `AUTHENTICATION_MODEL.md` §8b).
2. Vehicle lookup scoped:
   `Vehicle.objects.filter(dealership=dealership).get(
   stock_number=<url_kwarg>)`.
3. Both cross-tenant AND nonexistent `stock_number` raise
   `Vehicle.DoesNotExist` → caught → returned as 404 with a
   generic `{"detail": "Vehicle not found."}` body. Identical
   response for both cases → existence is not leaked via
   differential status codes.
4. Service functions receive `dealership=dealership` kwarg
   explicitly — no reliance on the `pre_save` autofill signal.

**Every endpoint's permission matrix is locked by tests** — six
cases per endpoint × three endpoints = 18 matrix tests:

| Case | Expected |
|------|----------|
| Anonymous | 401 or 403 (DRF's default for missing auth) |
| Advisor at same dealership | 403 |
| Advisor at wrong dealership | 403 |
| Sales manager at same dealership | 200 / 201 |
| Dealer owner at same dealership | 200 / 201 |
| Any authorized caller targeting cross-tenant stock_number | 404 |

## Query behavior

**Detail endpoint acceptable.** GET `.../ledger/` for a single
vehicle:

- 1 query for the Vehicle lookup (with `select_related("acquisition")`).
- 1 query for the vehicle's `dealership` (Django lazy-loads even
  through `select_related` on unrelated fields; not a concern for
  detail endpoints — see M2.3 handoff N+1 preview for the future
  bulk-list case).
- 6 queries from priming `vehicle.ledger_totals` (acquisition +
  4 category aggregates + 1 estimate aggregate — the M2.3 shape).
- 1 query for the ordered costs list.

Total: ~8-9 queries per detail response, all served from a
single vehicle. Well within the acceptable range for a single-
detail admin endpoint. The `vehicle.ledger_totals`
`@cached_property` primes ONCE — every totals field read below
returns from the cache, so the response assembly never
double-aggregates.

**Bulk-list optimization deferred** per M2.3 handoff — M2.6 is a
detail endpoint; the future inventory-list page (M2.7 or later)
should use a bulk aggregate query rather than looping N vehicles
× 9 queries.

## Tests added — 57 new, all passing

`test_admin_vehicle_ledger.py`, 15 classes:

| Category | Class | Tests |
|----------|-------|-------|
| Permission matrix | `PermissionMatrixLedgerRead` | 7 |
| | `PermissionMatrixAcquisitionUpsert` | 6 |
| | `PermissionMatrixCostCreate` | 6 |
| Read scenarios | `ReadLedgerEmptyState` | 1 |
| | `ReadLedgerAcquisitionOnly` | 2 |
| | `ReadLedgerMixedActualAndEstimate` | 3 |
| | `ReadLedgerReversingEntry` | 2 |
| | `ReadLedgerCostOrderingIsDeterministic` | 1 |
| | `ReadLedgerContractStability` | 4 |
| | `ReadLedgerCrossTenantIsolation` | 1 |
| Acquisition upsert | `AcquisitionCreate` | 1 |
| | `AcquisitionUpdate` | 1 |
| | `AcquisitionInvalidInput` | 5 |
| Cost create | `CostCreateValid` | 2 |
| | `CostCreateNegativeReversal` | 1 |
| | `CostCreateInvalidInput` | 4 |
| | `CostCreatedByAttribution` | 2 |
| | `CostImmutableRoutes` | 3 |
| Security verification | `PublicSurfacesNeverExposeLedgerData` | 5 |

**Security verification (5 tests):**

- `test_vehicle_detail_public_response_has_no_ledger_data` —
  15 ledger keywords are checked against
  `GET /api/dealer-ai/vehicles/<id>/`. None appear.
- `test_public_salespeople_response_has_no_ledger_data` — same
  check against `GET /api/dealer-ai/salespeople/`.
- `test_public_onboarding_get_has_no_ledger_data` — same check
  against `GET /api/dealer-ai/onboarding/profile/` (the public
  branding surface).
- `test_public_routes_remain_unauthenticated` — three sample
  public routes still respond 200 without auth. If a future
  change accidentally requires auth on one, this test breaks
  and forces the conversation.
- `test_default_permission_classes_remains_unset` — the M1 · 4B
  invariant that `settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]`
  stays absent, so a future endpoint that forgets to declare
  `permission_classes` doesn't silently gain a 401.

## Backend baseline

- **`python3 manage.py test dealer_ai` → 1,753 pass** (1,696
  baseline + 57 new M2.6 tests), 1 skipped, 0 fail. Zero
  regressions.
- **`makemigrations dealer_ai --check --dry-run` → "No changes
  detected".** Zero schema drift (M2.6 is pure Python + URL +
  view work).

## Compatibility result

Every existing invariant holds. Explicit rechecks:

- **M2.1–M2.5 contracts unchanged.** No file in
  `services/vehicle_ledger.py`, `services/payment_engine.py`,
  `services/dealer_config.py`, `services/llm_safety.py`,
  `services/tenancy.py`, `models.py`, `admin.py`,
  `permissions.py`, migrations, or `settings.py` touched.
- **M1 · 4D admin surface unchanged.** Permission class
  reused; no fork.
- **Ledger service is still the one write path.** Endpoints
  wrap `record_acquisition` / `add_cost`; direct
  `VehicleAcquisition.objects.create` / `VehicleCost.objects.create`
  is nowhere in the endpoint code.
- **Acquisition-price scrub still active + unchanged.** M2.5's
  71 tests all pass. The safety pipeline has NOT been touched
  by M2.6.
- **Public routes remain unauthenticated.** Verified explicitly
  by `PublicSurfacesNeverExposeLedgerData.test_public_routes_remain_unauthenticated`.
- **`DEFAULT_PERMISSION_CLASSES` remains unset.** Verified
  explicitly.
- **No new endpoint outside `/admin/`.** All three new routes
  are under the `admin/vehicles/<stock_number>/` prefix.
- **Frontend untouched.**

## Files touched this session

**Backend (3 files modified, 1 file new):**

- `backend/dealer_ai/serializers.py` — added imports for
  ledger constants + models + `category_group_of`; added six
  new serializer classes:
  `VehicleLedgerHeaderSerializer`,
  `VehicleAcquisitionOutputSerializer`,
  `VehicleCostOutputSerializer`,
  `AcquisitionUpsertRequestSerializer`,
  `CostCreateRequestSerializer`. No changes to existing
  serializers.
- `backend/dealer_ai/views.py` — added imports for the new
  serializers + models + `add_cost` / `record_acquisition` +
  a `_money_str` helper for quantized-to-cents JSON output.
  Added three view functions: `admin_vehicle_ledger`,
  `admin_vehicle_acquisition_upsert`,
  `admin_vehicle_cost_create`. No changes to existing views.
- `backend/dealer_ai/urls.py` — added three `path()` entries
  under the existing `/admin/` prefix.
- `backend/dealer_ai/tests/test_admin_vehicle_ledger.py` —
  **new file**, 57 tests across 15 classes.

**Docs (3 files):**

- `docs/roadmap/MILESTONE_2_PLANNING.md` §7.b · M2.6 row →
  SHIPPED with full summary of the API contract, permission
  composition, tenant scoping, cost ordering, `created_by`
  attribution, immutable-routes, and security-verification
  additions.
- `docs/handoffs/SESSION_052_milestone_2_ledger_api.md` —
  this file.
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_053 =
  M2.7.

**No changes to:** `services/vehicle_ledger.py`,
`services/payment_engine.py`, `services/dealer_config.py`,
`services/llm_safety.py`, `services/tenancy.py`,
`services/chat_engine.py`, `models.py`, `admin.py`, migrations,
`permissions.py`, `settings.py`, or any frontend file.

## Exact recommended scope for M2.7 (SESSION_053)

**M2.7 — Operator ledger UI.** Per `MILESTONE_2_PLANNING.md`
§1.6 + §7.b · M2.7. Frontend-only session; the backend contract
is locked at M2.6.

### In scope

1. **New route** `/dealer-ai-inventory/:stock/ledger` in
   `frontend/src/main.tsx`, wrapped in `<RequireAuth>`. Public
   / protected split from M1 · 4E preserved.

2. **New page component** `frontend/src/pages/VehicleLedgerPage.tsx`.
   Consumes the M2.6 JSON contract. Structure per planning §1.6:
   - Header: `{Year} {Make} {Model} #{stock_number}` +
     three-number bar (`total_investment` / `price` /
     `projected_gross`).
   - Days-in-inventory badge (color-coded per aging bucket:
     green 0–30, yellow 31–60, orange 61–90, red 91+; `null` →
     "record acquisition" pill).
   - Acquisition section — read-only display + edit-in-place
     inline form (POST to `.../acquisition/`).
   - Cost ledger table — chronological rows with columns
     (category / vendor / amount / incurred_at / notes /
     is_estimate flag / created_by).
   - "Add cost" inline form (POST to `.../costs/`).
   - Category totals block (four rows — flooring, recon,
     admin, photography — each with subtotal from the
     `totals` block).

3. **Three new `lib/api.ts` helpers**:
   - `fetchVehicleLedger(stock: string)`
   - `upsertVehicleAcquisition(stock: string, body: ...)`
   - `createVehicleCost(stock: string, body: ...)`
   All via `authFetch` (per M1 · 4E — operator surface uses
   session cookies, not localStorage tokens).

4. **Inventory list card gains a "Ledger" link** — one line
   per card that navigates to
   `/dealer-ai-inventory/:stock/ledger`.

5. **Role-based show/hide** on the write forms via `useAuth()`:
   `hasRole('sales_manager') || hasRole('dealer_owner')`
   controls whether the "Add cost" / "Edit acquisition" forms
   render. Belt-and-suspenders on top of the server-side 403 —
   matches the M1 · 4E pattern.

6. **Verification** at M2.7 close:
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.
   - Browser smoke: login as `smoke_owner` → navigate to
     `/dealer-ai-inventory/M2.1-DEMO/ledger` (seed a demo
     vehicle first if needed) → see the ledger → add a
     cost → see totals update.
   - Advisor role smoke: login as advisor → navigate to
     ledger URL directly → see 403 UI (not redirect).
   - Anonymous smoke: navigate to ledger URL → redirect to
     `/login?next=...`.

### Out of scope for M2.7

- Milestone 2 closeout retrospective (M2.8).
- Bulk inventory-list optimization (planning §5 deferral;
  detail-page-first suffices for M2).
- Update / delete cost operations (v1 uses reversing rows).
- New backend endpoints beyond M2.6's three.
- `floor_plan_apr` field in the Setup UI (deferred but
  M2.7-adjacent — SESSION_053 may fold it in if the ledger
  page needs to expose it, or defer to a Milestone 2.5-scoped
  onboarding-UI increment).
- Recon-manager role UI.
- Chart / visualization work (numbers only for v1).

### Verification steps at M2.7 close

- `npx tsc --noEmit` + `npx vite build` clean.
- Full backend suite unchanged (M2.7 is frontend-only).
- Manual browser smokes above.
- No touch to any backend file.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §2c (frontend auth
   primitives) — every M2.7 fetch goes through `authFetch`.
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 lesson 6
   (public/protected route split).
6. `docs/roadmap/MILESTONE_2_PLANNING.md` §1.6 + §7.b · M2.7.
7. `docs/handoffs/SESSION_052_milestone_2_ledger_api.md`
   (this file — the JSON contract M2.7 consumes).
8. `docs/handoffs/SESSION_051_milestone_2_acquisition_price_scrub.md`
9. `docs/handoffs/SESSION_050_milestone_2_accrual_command.md`
10. `docs/handoffs/SESSION_049_milestone_2_financial_math.md`
11. `docs/handoffs/SESSION_048_milestone_2_vehicle_read_model.md`
12. `docs/handoffs/SESSION_047_milestone_2_ledger_service.md`
13. `docs/handoffs/SESSION_046_milestone_2_schema.md`
14. `docs/handoffs/SESSION_045_milestone_2_planning.md`
15. Current source code — the M2.6 admin endpoints, their JSON
    shapes, and the six-case permission matrix.

Planning docs are claims. Rules + research + code are facts.
