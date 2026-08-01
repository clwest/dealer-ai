---
title: "SESSION_079 handoff — Milestone 5 · Increment 5 (retail-gating refactor)"
status: historical
type: handoff
date: 2026-08-01
session: 079
milestone: 5
milestone_status: in-progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_079 — Milestone 5 · Increment 5 (M5.5 — retail-gating refactor)

## What shipped

The retail-gating refactor. `customer_visible_vehicles()`
(the single choke point every customer-facing surface goes
through) now filters on `VehicleStage.current_stage='frontline'`
via a new queryset annotation, NOT on `Vehicle.is_available`.
`vehicle_assistant._similar_vehicles` routed through the
choke point. Vehicle write-path integration for the sole
production creation site (`inventory_import.py`) seeds a
`frontline` stage with `trigger='import'` explicitly. 12
net-new tests locking the new behavior + 1 test-only
`post_save` signal that auto-bootstraps `frontline` for all
existing test fixtures (documented separately below).

Baseline: 2,742 → **2,754 pass**, 1 skipped, 0 fail. +12
tests, 0 regressions. Frontend unchanged.

## Choke-point refactor: `customer_visible_vehicles()`

`services/chat_engine.py::customer_visible_vehicles` was the
single funnel every customer-facing consumer went through
(chat matched-vehicles, inventory search, per-vehicle
similar-vehicles). The M1 implementation filtered on
`is_available=True`. The M5.5 implementation composes:

```python
from .vehicle_lifecycle import annotate_retail_eligible

return (
    annotate_retail_eligible(Vehicle.objects.all())
    .filter(_lifecycle_retail_eligible=True)
    .exclude(stock_number__iregex=_CUSTOMER_VISIBLE_DEBUG_PATTERN)
)
```

One choke point flipped → every downstream consumer inherits
the new semantics automatically:
- `chat_engine` matched-vehicles.
- `inventory_search.search_vehicles` (which uses
  `customer_visible_vehicles()` internally).
- `vehicle_assistant._similar_vehicles` (this session
  refactored to route through the choke point too).

## New helpers

### `services/vehicle_lifecycle.py::annotate_retail_eligible(qs)`

Annotates a `Vehicle` queryset with a
`_lifecycle_retail_eligible` boolean via
`Exists(VehicleStage.filter(vehicle=OuterRef, current_stage=frontline))`.
The annotation name is deliberately underscore-prefixed to
avoid a collision with the `Vehicle.is_retail_eligible`
`@property` (Django populates annotations via `setattr` and
properties have no setter — first draft caught this via test
failure `AttributeError: property has no setter`).

### `tests/_tenancy_helpers.py::bootstrap_frontline(vehicle)`

Ergonomic wrapper around `ensure_current_stage(...,
initial_stage='frontline')` for tests that need a
retail-eligible vehicle. Idempotent.

### `tests/_tenancy_helpers.py::wipe_lifecycle_state(vehicle)`

Deletes any `VehicleStage` + `VehicleStageEvent` rows for
a vehicle. Used by M5.1–M5.4 test files to strip the
test-only auto-bootstrap when a test explicitly tests
pre-seed behavior.

## Vehicle write-path integration

Sole production Vehicle creation site: **one file** —
`services/inventory_import.py:326`. Refactored:

```python
vehicle = Vehicle(**cleaned)
vehicle.dealership = tenant
vehicle.source = source
vehicle.last_seen_at = started_at
vehicle.imported_at = started_at
vehicle.is_available = True
vehicle.save()

# M5.5 write-path integration — explicit, no signals.
from ..models import (
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_TRIGGER_IMPORT,
)
from .vehicle_lifecycle import ensure_current_stage

ensure_current_stage(
    vehicle,
    dealership=tenant,
    initial_stage=VEHICLE_STAGE_FRONTLINE,
    trigger=VEHICLE_STAGE_TRIGGER_IMPORT,
)
```

Imported vehicles seed at `frontline` (matching the M1
`is_available=True` retail-ready semantics for imports)
with `trigger='import'` so the audit trail records
provenance. **No `pre_save` signal. No property-read side
effect.** Per §0.a item 6.

## Test-only auto-bootstrap signal

**Design decision:** rather than update ~150 pre-existing
test fixtures individually (mechanical sweep with no design
value), a test-only `post_save` signal on `Vehicle`
auto-seeds `frontline` for every newly saved Vehicle.
Registered in `apps.py::ready()` gated on
`_is_running_tests()` (checks `sys.argv` for `test`).

**Rationale (documented in `tests/__init__.py` docstring):**

- Production write paths must remain explicit (§0.a item 6
  — the sole prod site was updated directly).
- Test fixtures that create vehicles expect them to appear
  in customer-facing surfaces because the tests exercise
  downstream behavior (chat, search, scrubs) that
  presupposes retail-visible vehicles.
- Making that setup implicit in tests is ergonomic; making
  it explicit in production is the correctness contract.

**Tests that explicitly test lifecycle behavior** (M5.1–M5.4
suites — 66 tests) opt out by calling `wipe_lifecycle_state`
in their local `_make_vehicle` helpers immediately after
creation. Each M5 test file was updated with a one-line
addition:

```python
def _make_vehicle(...):
    v = Vehicle.objects.create(...)
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)
```

## Customer-language refactor — DEFERRED

§5.i ("That vehicle is not currently available for retail.")
was deferred out of M5.5. Locating the exact stock-specific
lookup path inside `chat_engine.py` (4,000+ lines) that
maps a customer prompt like *"do you have #F150-42?"* to a
response requires deeper investigation than fits this
session. The `customer_visible_vehicles()` flip already
removes non-frontline units from `matched_vehicles`, so
the LLM has no basis to fabricate details about them —
the M4.5 `_scrub_invented_recon_fact` scrub also
independently prevents recon-detail leaks. **Truthful
phrasing for stock-specific direct lookups
(`vehicle_detail` / `vehicle_ask` endpoints) is scoped
into M5.6 or a follow-up increment.**

## Not touched (deliberate)

- `services/ad_copy.py` and `services/pipeline.py` still
  filter on `is_available=True`. These are operational
  dashboards / marketing analytics, not customer-facing
  retail surfaces. Per §5.e Option D, non-retail consumers
  migrate on their own schedule. Left for a future audit.
- `Vehicle.is_available` schema unchanged. §5.e Option D —
  retained as backwards-compat field.
- No migrations added.

## Backend baseline

- **Pre-session:** 2,742 pass, 1 skipped, 0 fail.
- **Post-session:** 2,754 pass, 1 skipped, 0 fail.
- Delta: +12 tests, 0 regressions.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."

## Commit hashes

- Session commit: **TBD** (deferred per user directive —
  commit + push after M5.7 closes AND
  `MILESTONE_6_PLANNING.md` is created).

## Exact recommended scope for M5.6

**M5.6 — Operator lifecycle UI.** Frontend surface only.

Route `/dealer-ai-inventory/:stock/lifecycle` inside
`<RequireAuth>` in `main.tsx`. New page +
small extracted components:

- `frontend/src/pages/VehicleLifecyclePage.tsx` (~400
  lines target).
- `frontend/src/components/lifecycle/StageBadge.tsx` —
  reusable stage pill (mirrors `WorkOrderStatusBadge`).
- `frontend/src/components/lifecycle/StageTimeline.tsx` —
  vertical timeline of every `VehicleStageEvent`.
- `frontend/src/components/lifecycle/SuggestedTransitionsPanel.tsx`
  — renders `suggest_transitions()` output as one-click
  "advance to X" buttons; disables + hints for suggestions
  with `unmet_prerequisites`.
- `frontend/src/components/lifecycle/ManualTransitionForm.tsx`
  — dropdown to any allowed target + reason textarea.

Typed API helpers in `frontend/src/lib/api.ts` for the M5.4
endpoints:
- `getLifecycleDashboard(stock_number)`.
- `postManualTransition(stock_number, { to_stage, notes })`.
- `postRuleTransition(stock_number, { rule_name })`.

Role gating (per §5.f):
- Read-only for viewers who don't have manager role.
- Manual transition affordances gated to
  `recon_manager` / `sales_manager` / `dealer_owner`.
- Commercial/disposition transition targets
  (`hold_reserved` / `wholesale_out` / `company_use` /
  `off_market`) further gated to `sales_manager` /
  `dealer_owner` only (recon_manager UI hides those
  buttons; even if a stale UI submits, the M5.2 service
  rejects with 403).

Distinct 400/401/403/404/409 UX: each domain-error → HTTP
code renders a distinct message so the operator understands
what to try next.

**Verification.** `npx tsc --noEmit` clean.
`npx vite build` clean. Backend baseline unchanged.
Manual browser walkthrough deferred to operator first-live
per M3.7 / M4.7 honesty precedent.

**Boundary.** Frontend files only. Backend baseline 2,754
unchanged.

**Out of M5.6:**
- ❌ Backend service changes.
- ❌ Migrations.
- ❌ Any AI role.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — as amended
   SESSION_075
6. `docs/handoffs/SESSION_079_m5_inc5_retail_gating.md`
   (this doc)
7. `docs/handoffs/SESSION_078_m5_inc4_admin_api.md`
8. `docs/handoffs/SESSION_077_m5_inc3_deterministic_rules.md`
9. `docs/handoffs/SESSION_076_m5_inc2_service_state_machine.md`
10. `docs/handoffs/SESSION_075_m5_inc1_core_models.md`
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md`

Narrative docs are claims. Rules + research + code are facts.
