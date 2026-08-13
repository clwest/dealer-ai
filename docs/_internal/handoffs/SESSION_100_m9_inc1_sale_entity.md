---
title: "SESSION_100 handoff — Milestone 9 · Increment 1 (M9.1 — Sale entity + gross_realized)"
status: historical
type: handoff
date: 2026-08-02
session: 100
milestone: 9
milestone_status: in_progress
increment: 1
increment_status: shipped
commit: TBD
---

# SESSION_100 — Milestone 9 · Increment 1 (M9.1 — Sale entity + gross_realized)

## What shipped

`Sale` entity substrate + `services/sale/`
package (`gross_realized` verb +
`record_sale` write path) +
`VehicleAcquisition.buyer` FK (M2 additive
extension bundled per §5.a Option A) +
first M9 DRF endpoint
(`POST /admin/vehicles/<stock>/sale/`) +
tenancy carrier extension (22 → 23) + 46
focused tests. All three
`[NEEDS-DECISION-BEFORE-M9.N]` items from
`MILESTONE_9_PLANNING.md` §9 confirmed at
session open (all three as-recommended,
Option A).

**Load-bearing decisions confirmed at session
open (recorded in `MILESTONE_9_PLANNING.md`
§0.a):**

1. **§5.a — Acquisition-buyer provenance
   bundling:** Option A — bundle the M2
   `VehicleAcquisition.buyer` FK into M9.1
   so Q7 unlocks in the same milestone.
2. **§5.b — `Sale.buyer` representation:**
   Option A — FK to existing `CustomerLead`
   (M3-M5 CRM substrate reused).
3. **§5.c — Sale finance-type vocabulary:**
   Option A — three initial values (`cash`
   / `retail` / `bhph`).

**Sequencing decision (implementation-time):**
Django's `makemigrations` combined both
model changes into a single M9.1 migration
`0023_sale_entity_and_buyer_fk` — cleaner
than the two-migration path (`0023` +
`0024`) the plan had projected. One atomic
delivery, one reverse operation. §0.a
amended narrowly to record this.

**M9.1 deliverables (seven):**

1. **New `Sale` model + migration `0023`**
   (`0023_sale_entity_and_buyer_fk`).
   Fields per plan (`dealership` FK CASCADE,
   `vehicle` OneToOne CASCADE, `buyer` FK
   `CustomerLead` SET_NULL nullable,
   `sale_date`, `sold_price` Decimal(10,2),
   `finance_type` from
   `SALE_FINANCE_TYPE_CHOICES`,
   `lender_name` optional CharField,
   `gross_realized` Decimal(10,2)
   denormalized at write). Ordering
   (`-sale_date`, `-created_at`).
   Model-layer `clean()` cross-tenant
   guard covers both `dealership` vs
   `vehicle.dealership` and `dealership`
   vs `buyer.dealership`.
2. **`VehicleAcquisition.buyer` FK
   (M2 additive extension)** — nullable
   FK to `settings.AUTH_USER_MODEL` with
   `SET_NULL` on user delete, ships in
   the same migration `0023` per §5.a
   Option A. Historical acquisition rows
   populate NULL (M9.4's Q7
   `buyer_estimate_accuracy` verb excludes
   NULL rows from the aggregation rather
   than treating them as a single
   anonymous buyer bucket).
3. **Tenancy-carrier extension 22 → 23.**
   `_TENANT_CARRIER_MODEL_NAMES` extended
   with `"Sale"`. `Sale` has a parent
   tenant relation via `vehicle` OneToOne,
   but per M8.1 pattern the M9.1 service
   (`record_sale`) writes `dealership`
   explicitly on every row; the autofill
   signal is a safety net only for
   callers that bypass the service
   (Django admin form, ad-hoc management
   command).
4. **New `services/sale/` package** —
   `__init__.py` facade re-exporting the
   verbs +
   `computation.py::gross_realized(sale)
   -> Decimal` (pure read verb; refuses
   cross-tenant with
   `CrossTenantSaleError`) +
   `computation.py::record_sale(vehicle,
   *, dealership, sale_date, sold_price,
   finance_type, buyer=None,
   lender_name="") -> Sale` (write path;
   transactional; denormalizes
   `gross_realized` at insert time;
   refuses duplicate Sale with
   `SaleAlreadyExistsError` and unknown
   `finance_type` with `ValueError`).
5. **First DRF endpoint:**
   `POST /api/dealer-ai/admin/vehicles/<stock>/sale/`
   in new `views_sale.py`. Role-gated on
   `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
   per §1.6 (mirrors the M4-M8 pattern).
   Domain-error mapping:
   `CrossTenantSaleError` → 404;
   `SaleAlreadyExistsError` → 409;
   `ValueError` → 400. Response projection
   returns stringified Decimals per M2 /
   M4 / M8 convention.
6. **`urls.py` wiring** — `views_sale`
   registered; route added as the M9.1
   §1.6 first entry, name
   `dealer_ai:admin-sale-create`.
7. **46 focused tests across four files:**
   - `test_m9_sale_model.py` (12 tests) —
     shape, ordering, OneToOne
     invariant, `clean()` cross-tenant
     guards, `buyer` SET_NULL on
     CustomerLead delete, tenancy-carrier
     registration.
   - `test_m9_vehicle_acquisition_buyer_fk.py`
     (4 tests) — nullable default, persist
     round-trip, SET_NULL on user delete,
     reverse accessor
     `user.acquisitions_bought`.
   - `test_m9_sale_computation.py` (12
     tests) — `gross_realized` returns
     Decimal / positive / negative /
     estimates-excluded / cross-tenant
     refused; `record_sale` persists all
     fields / denormalizes gross / rejects
     duplicate / rejects cross-tenant
     vehicle+buyer / rejects unknown
     finance_type / accepts null buyer.
   - `test_m9_sale_endpoint.py` (18
     tests) — full auth matrix (9), success
     with + without buyer, 404 on unknown
     vehicle / buyer, 409 on duplicate, 400
     on invalid finance_type / missing
     field, cross-tenant vehicle → 404,
     cross-tenant buyer → 404.

## Test baseline

- **Backend:** 3,274 → **3,320 pass**, 1
  skipped, 0 fail (+46 M9.1 tests exactly).
- **Frontend Vitest:** unchanged at 19 pass
  (no frontend at M9.1 per plan
  non-goals).
- **`tsc --noEmit`:** clean.
- **`vite build`:** clean.
- **`manage.py check`:** clean.
- **`manage.py makemigrations --check
  --dry-run`:** "No changes detected."

## Migrations

`0001` – **`0023`** (one added at M9.1:
`0023_sale_entity_and_buyer_fk`).

## Files touched (M9.1 scope)

**Backend (added):**

- `backend/dealer_ai/migrations/0023_sale_entity_and_buyer_fk.py`
  (~55 lines + M9.1 module docstring).
- `backend/dealer_ai/services/sale/__init__.py`
  (~33 lines).
- `backend/dealer_ai/services/sale/computation.py`
  (~185 lines — module docstring +
  `CrossTenantSaleError` +
  `SaleAlreadyExistsError` +
  `gross_realized` +
  `record_sale`).
- `backend/dealer_ai/views_sale.py`
  (~155 lines — endpoint + serializer +
  projection).
- `backend/dealer_ai/tests/test_m9_sale_model.py`
  (~290 lines, 12 tests).
- `backend/dealer_ai/tests/test_m9_vehicle_acquisition_buyer_fk.py`
  (~120 lines, 4 tests).
- `backend/dealer_ai/tests/test_m9_sale_computation.py`
  (~320 lines, 12 tests).
- `backend/dealer_ai/tests/test_m9_sale_endpoint.py`
  (~320 lines, 18 tests).

**Backend (modified):**

- `backend/dealer_ai/models.py` —
  `SALE_FINANCE_TYPE_*` module-level
  constants + `SALE_FINANCE_TYPE_CHOICES` +
  `Sale` class (below `SlaBreachRecord`);
  `VehicleAcquisition.buyer` FK inserted
  between `title_acquisition_cost` and
  `notes`.
- `backend/dealer_ai/services/tenancy.py`
  — `_TENANT_CARRIER_MODEL_NAMES` extended
  with `"Sale"` (22 → 23) with M9.1
  provenance comment.
- `backend/dealer_ai/urls.py` — imports
  `views_sale`; registers
  `admin/vehicles/<str:stock_number>/sale/`
  route.

**Docs (modified):**

- `docs/roadmap/MILESTONE_9_PLANNING.md`
  §0.a — SESSION_100 amendment recording
  all three §5 decisions (Option A) + the
  single-migration sequencing decision.
- `00-START-NEXT-SESSION.md` — overwritten
  with M9.2 priority (see next-session
  section below).

## What SESSION_100 confirmed vs deferred

**Confirmed at session open (per user
"Agree with the recommended"):**

- §5.a Option A — buyer FK bundled.
- §5.b Option A — `CustomerLead` FK.
- §5.c Option A — three finance-type values.

**Deferred to M9.2+ per plan §7 non-goals:**

- `Delivery` model + checklist (M9.2).
- Q3 / Q6 / Q8 analytics extensions
  (M9.3).
- Q7 `buyer_estimate_accuracy` verb +
  endpoint (M9.4) — substrate now in
  place (`VehicleAcquisition.buyer` FK
  landed at M9.1) but the verb doesn't
  ship until M9.4.
- `LeadVehicleInterest.stage_at_interest`
  extension (M9.4).
- Frontend operator UI extension (M9.5)
  — no fifth analytics tab yet, no Sale
  list on Vehicle detail.
- F&I / stips / chargebacks (M10).

## Push authorization state

- Working tree clean at session close.
- All M9.1 changes staged in a single
  session on `main`.
- **`main` is currently up to date with
  `origin/main`** (verified at session
  open — commit `4923997` was already
  pushed by SESSION_099).
- **The M9.1 changes are UNCOMMITTED at
  handoff write time.** A coordinated
  commit ships at M9 close (per M8
  precedent — SESSION_099 landed one
  commit covering M8.1-M8.6). Intermediate
  commits per increment are the historical
  M1-M7 pattern; M8 moved to
  end-of-milestone bundling. SESSION_101
  M9.2 opens with these changes still
  uncommitted unless the user prefers
  per-increment commits.

## Fifteen M8 lessons — carry into M9

Per `MILESTONE_8_RETROSPECTIVE.md` §6, all
fifteen lessons carry forward. Two applied
directly at M9.1:

- **Lesson 11 — additive extension over
  rewrite.** The `VehicleAcquisition.buyer`
  FK is pure additive; no M2 code path
  changes; existing acquisition creation
  callers keep working with the FK
  defaulting to NULL.
- **Lesson 15 (new at M8) — verify handoff
  claims via direct inspection.** SESSION_100
  opened with a `git log
  origin/main..HEAD` check that surfaced
  the SESSION_099 handoff's "push
  deferred" claim was stale — commit had
  already been pushed. Recorded in this
  handoff's *Push authorization state*
  above; SESSION_099 handoff not
  rewritten (per DOC_GOVERNANCE.md
  principle 5 handoffs are immutable
  records).

## What SESSION_101 (M9.2) should do

Per `MILESTONE_9_PLANNING.md` §7 M9.2:

1. **Read first:**
   `MILESTONE_9_PLANNING.md` §1.2 +
   §5.d + §7 M9.2;
   `docs/handoffs/SESSION_100_m9_inc1_sale_entity.md`;
   `Sale` model (M9.1 parent);
   `Vehicle.is_available` (deferred M9.2
   question — should Sale writes flip
   this?).
2. **Verify starting state:** `git status`
   (M9.1 uncommitted unless user directs
   commit); `python3 manage.py test
   dealer_ai` → **3,320 pass**;
   `manage.py check` clean;
   `makemigrations --check --dry-run` →
   "No changes detected."
3. **Confirm one open question:** does
   `Delivery` OneToOne with `Sale`, or is
   Delivery a nullable OneToOne (temp-tag-
   only Delivery for cash-and-carry sales
   with no checklist)? Planning §1.2 has
   this as an "at the M9.n increment
   decide" note.
4. **Draft (in order):**
   - `Delivery` model + migration `0024`.
   - `services/delivery/` package +
     checklist verbs.
   - Tenancy carrier addition (23 → 24).
   - Endpoint:
     `POST /admin/vehicles/<stock>/delivery/`
     + probable
     `PATCH /admin/deliveries/<id>/`
     for checklist updates.
   - ~25 focused tests.
5. **Baseline projection:** 3,320 →
   **~3,345**.
6. **Ship handoff at
   `docs/handoffs/SESSION_101_m9_inc2_delivery.md`.**

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 9
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_9_PLANNING.md`
   (with §0.a SESSION_100 amendment)
6. `docs/roadmap/MILESTONE_8_RETROSPECTIVE.md`
   §6 (fifteen lessons carry into M9)
7. `docs/handoffs/SESSION_099_m8_closeout.md`
8. `docs/CAPABILITY_MATRIX.md` §7i (M8
   substrate M9 layers on top of)
9. `docs/research/VEHICLE_CENTRIC_PIVOT.md`
   §Phase 8
10. `docs/research/SALES_DEPARTMENT_MAPPING.md`
11. Current source code — authoritative.

Planning docs are claims. Rules + research
+ code are facts.
