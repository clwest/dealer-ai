---
title: "SESSION_078 handoff — Milestone 5 · Increment 4 (admin API + permission matrix)"
status: historical
type: handoff
date: 2026-08-01
session: 078
milestone: 5
milestone_status: in-progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_078 — Milestone 5 · Increment 4 (M5.4 — admin API)

## What shipped

The DRF admin API surface for vehicle lifecycle. One new
view module (`views_lifecycle.py`, ~330 lines) with three
endpoints + three URL registrations. 48 focused endpoint
tests. **Zero migrations, zero service changes, zero
retail-gating refactor, zero frontend.**

Baseline: 2,694 → **2,742 pass**, 1 skipped, 0 fail. +48
tests, 0 regressions.

## Endpoints (three)

Under `/api/dealer-ai/admin/vehicles/<stock_number>/lifecycle/`:

1. **`GET .../lifecycle/`** — dashboard. Returns:
   - `stock_number` (echoed).
   - `has_stage` (bool).
   - `current_stage` (projected `VehicleStage` row or `null`).
   - `recent_events` (last 25 `VehicleStageEvent` rows).
   - `suggested_transitions` (M5.3 composition output).
   - `hold_reserved_return_target` (via
     `resolve_hold_reserved_return_target`).

2. **`POST .../lifecycle/transition/`** — apply manual
   transition. Body: `{"to_stage": "...", "notes": "..."}`.
   Calls `advance_stage(..., trigger='manual',
   actor=request.user)`.

3. **`POST .../lifecycle/transition/rule/`** — accept a
   rule-suggested transition. Body: `{"rule_name": "..."}`.
   Re-evaluates `suggest_transitions(...)` at apply time;
   refuses 409 if the specific rule no longer fires OR if
   the matched suggestion carries `unmet_prerequisites`
   (e.g. `photography_to_listing` pending M6 photo
   predicate). Calls `advance_stage(..., trigger='rule',
   rule_name=<matched>, actor=request.user)`.

All three URL patterns registered in `dealer_ai/urls.py`
alongside the M4.6 recon admin URLs.

## Permission layering

All three endpoints share the DRF permission class
`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
(M4.6). Nine-row permission matrix (per M4.6 pattern):

| Role                   | GET dashboard | POST manual | POST rule |
|------------------------|---------------|-------------|-----------|
| unauthenticated        | 401/403       | 401/403     | 401/403   |
| no role                | 403           | 403         | 403       |
| advisor                | 403           | 403         | 403       |
| porter                 | 403           | 403         | 403       |
| f_and_i_manager        | 403           | 403         | 403       |
| collections            | 403           | 403         | 403       |
| recon_manager          | 200           | 200*        | 200*      |
| sales_manager          | 200           | 200         | 200       |
| dealer_owner           | 200           | 200         | 200       |

*Recon manager's endpoint admission still hits
`UnauthorizedStageTransitionError` (→ 403) when the target
is `hold_reserved` / `wholesale_out` / `company_use` /
`off_market` — locked by the M4.2 service-layer per-target
role check. This is the layered enforcement §5.f
SESSION_075 refined: DRF admits the endpoint; the service
refuses the finer-grained per-transition target.

Locked by three `LifecycleEndpointAuthMatrixBase`
subclasses (one per endpoint), each producing nine tests =
27 permission-matrix tests.

## Domain-error → HTTP mapping

Per SESSION_075 §0.a item 5 — distinct classes, distinct
status codes; do not overload:

| Domain error                          | HTTP |
|---------------------------------------|------|
| `CrossTenantLifecycleError`           | 404 (fail-closed) |
| `UnauthorizedStageTransitionError`    | 403 |
| `InvalidStageTransitionError`         | 409 |
| `StageAlreadyCurrentError`            | 409 |
| `ValueError` (unknown stage/trigger)  | 400 |

Implemented via `_map_service_error(exc)` — one helper,
all three endpoints route through it. `raise exc` for
unknown types (surface as 500 rather than swallow).

## Tests

One new file, **48 tests**:

`test_admin_lifecycle_endpoints.py`:

- Three `LifecycleEndpointAuthMatrixBase` subclasses (27
  permission-matrix tests):
  - `LifecycleDashboardAuth` (9).
  - `LifecycleManualTransitionAuth` (9).
  - `LifecycleRuleTransitionAuth` (9).
- `LifecycleDashboardShape` (7) — has_stage=false for
  unseeded vehicle; current_stage + events for seeded;
  suggested_transitions at inspection with actionable
  findings; photography_to_listing prerequisite;
  hold_reserved return target populated; cross-tenant 404;
  missing stock 404.
- `LifecycleManualTransitionFlow` (8) — happy-path
  transition; structural refusal → 409; no-op → 409; role
  refusal → 403 (recon_manager on commercial target);
  unknown to_stage → 400 (`"sold"`); cross-tenant → 404;
  missing stock → 404; recon_manager CAN do retail-prep
  transition.
- `LifecycleRuleTransitionFlow` (5) — rule accept success;
  409 when rule doesn't fire (no completed report); 409
  for unknown rule_name; 409 for `photography_to_listing`
  prerequisite refusal; cross-tenant 404.
- `LifecycleEndpointsWriteNoM4Data` (1) — regression
  boundary: manual transition writes zero `WorkOrder` /
  `VehicleCost` rows.

## Backend baseline

- **Pre-session:** 2,694 pass, 1 skipped, 0 fail.
- **Post-session:** 2,742 pass, 1 skipped, 0 fail.
- Delta: +48 tests, 0 regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."

## Compatibility result

- **Frontend:** untouched.
- **Migrations:** none added.
- **`Vehicle.is_available`:** unchanged.
- **M1–M4 endpoints:** unchanged.
- **`services/vehicle_lifecycle.py`:** unchanged this
  session (M5.2 + M5.3 shape preserved).

## Commit hashes

- Session commit: **TBD** (deferred per user directive —
  commit + push after M5.7 closes AND
  `MILESTONE_6_PLANNING.md` is created).

## Exact recommended scope for M5.5

**M5.5 — Retail-gating refactor + fixture updates + Vehicle
write-path integration.** Per planning §5.e Option D + §5.i
+ §0.a item 6.

### Retail-gating refactor (coordinated)

Swap the retail-side consumers from `is_available=True`
filters to `is_retail_eligible=True` (via a queryset
annotation joining `VehicleStage.current_stage='frontline'`):

1. `services/chat_engine.py::_available_vehicles_queryset`.
2. `services/chat_engine.py::_vehicle_ask_target` (if it
   independently filters).
3. `services/inventory_search.py::search_vehicles`.
4. Public `/showroom` endpoint (`views.py`).

### Fixture updates

Existing tests that create a Vehicle and expect it to
appear in customer chat / search / showroom must seed a
`VehicleStage` row at `frontline`. New helper in
`_tenancy_helpers.py`:

```python
def bootstrap_frontline(vehicle, dealership):
    from ..services.vehicle_lifecycle import ensure_current_stage
    from ..models import VEHICLE_STAGE_FRONTLINE
    ensure_current_stage(
        vehicle, dealership=dealership,
        initial_stage=VEHICLE_STAGE_FRONTLINE,
    )
```

Fixture-update count locked at increment (~30 test files
per the M5.5 planning estimate; the exact number is a
consequence of the refactor).

### Vehicle write-path integration

Per SESSION_075 §0.a item 6 (no hidden writes from Vehicle
properties): every code path that creates a new `Vehicle`
must call `ensure_current_stage(vehicle,
dealership=dealership, initial_stage='incoming')`
explicitly. **Do NOT** rely on a pre-save signal or a
property-read side effect. Audit the current codebase for
`Vehicle.objects.create(...)` and `Vehicle(...)` +
`.save()` call sites; instrument each with the explicit
seeding call.

### Customer-language refactor (§5.i truthful phrasing)

When customer chat's stock-specific lookup finds a
non-frontline unit, surface: *"That vehicle is not
currently available for retail."* Do NOT expose internal
stage, recon details, completion estimate, vendor status,
or expected-ready date.

Wire the fallback copy in `services/chat_engine.py` where
the current `is_available=False` "we don't have that
vehicle" response lives.

### Customer chat anti-pattern lockout

Per §5.e SESSION_075 refined: `is_available` MUST NOT
remain a manual override for retail gating. If any
customer-facing surface still reads `is_available` after
this session, add a regression test that locks the
`is_retail_eligible`-driven behavior.

### Tests

~30 focused tests + fixture updates. Coverage:
- Non-frontline vehicles never appear in customer chat /
  search / showroom.
- A vehicle at `stage=frontline` with `is_available=False`
  IS still retail-eligible (a deliberate divergence — the
  M5.5 refactor's proof that stage is authoritative).
- A vehicle at `stage=in_recon` with `is_available=True`
  is NOT retail-eligible (the M1 flag doesn't override).
- Customer chat stock-specific lookup returns truthful
  "not currently available for retail" phrasing.
- Vehicle creation seeds `incoming` explicitly via
  `ensure_current_stage`.
- Public showroom rendered for anonymous users still
  works (no auth regression).

### Boundary

Test baseline: 2,742 → ~2,772 pass (+30 tests + fixture
updates net-zero). Zero regressions. Zero migrations.

### Out of M5.5

- ❌ Frontend — M5.6.
- ❌ Any AI role.
- ❌ Modifying `Vehicle.is_available` schema.
- ❌ Removing `is_available` from admin surfaces.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — as amended
   SESSION_075
6. `docs/handoffs/SESSION_078_m5_inc4_admin_api.md`
   (this doc)
7. `docs/handoffs/SESSION_077_m5_inc3_deterministic_rules.md`
8. `docs/handoffs/SESSION_076_m5_inc2_service_state_machine.md`
9. `docs/handoffs/SESSION_075_m5_inc1_core_models.md`
10. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 + §8
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md`

Narrative docs are claims. Rules + research + code are facts.
