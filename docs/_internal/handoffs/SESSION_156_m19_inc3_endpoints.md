---
title: "SESSION_156 handoff — Milestone 19 · Increment 3 (M19.3 — Pilot admin endpoints)"
status: historical
type: handoff
date: 2026-08-02
session: 156
milestone: 19
milestone_status: in-progress
milestone_name: "Founding Dealer Pilot Onboarding"
increment: 3
increment_status: shipped
---

# SESSION_156 — Milestone 19 · Increment 3 (M19.3 — Pilot admin endpoints)

## What shipped

Single backend increment per
`MILESTONE_19_PLANNING.md` §7 M19.3.
Four lifecycle admin endpoints wrapping
the M19.1 pilot service verbs +
serializers + URL wiring + 31 focused
tests.

**Two §0.a M19.3 implementation-time
decisions recorded** (do not count
against planning-time streak per M10
§9). Both surfaced at open with a
defense from the assistant that the
user confirmed.

### §0.a M19.3 decision 1 — inventory-import endpoint deferred to M19.4

**Decision.** M19.3 ships four lifecycle
endpoints only (create / list /
checklist advance / terminate). The
`POST /admin/pilots/<slug>/inventory/import/`
endpoint ships with its M19.4 frontend
consumer.

**Why the session-start opener's
recommendation was reversed.** The
session-start opener leaned "yes, ship
at M19.3" arguing cohesion. Reexamined
at M19.3 open: the "frontend upload
with no backend receiver" concern
dissolves because M19.4 ships as one
unit (frontend + any backend it needs),
so bundling the endpoint into M19.4
alongside its consumer is architecturally
cleaner. Advantages:

- M19.3 stays lifecycle-focused — one
  theme per increment.
- M19.4 owns its full stack — file-
  upload UI + multipart backend
  receiver ship together, reviewed
  together.
- Cleaner endpoint deltas: **108 →
  112 at M19.3** (four lifecycle);
  **112 → 113 at M19.4** (import).

### §0.a M19.3 decision 2 — `IsAuthenticated` alone

**Decision.** All four pilot admin
endpoints gate on `IsAuthenticated`
only. No new permission class ships at
M19.3.

**Why the two existing role-gated
classes did not fit.** Both
`IsDealerOwnerAtActiveDealership` and
`IsSalesManagerOrOwnerAtActiveDealership`
require the caller to hold a role at
`get_current_dealership(request)` —
their *active* tenant. That doesn't
work for the pilot admin surface:

- `POST /admin/pilots/create/` — no
  target pilot exists yet; Chris (the
  platform operator) has no active-
  pilot-tenant to hold a role in.
- Later verbs would work after
  `create_pilot_dealership` attaches
  Chris as `dealer_owner`, but routing
  through the active-tenant middleware
  requires a hop to switch active
  tenant to the target slug. Extra
  complexity for one operator.

Adding a new `IsPlatformOperator` class
would break the zero-drift streak
without operational benefit — Chris is
the only platform operator today.
`IsAuthenticated` is the honest,
minimal contract: "these are platform-
owner endpoints; authenticated Chris
is trusted." M20+ can revisit if a
second platform operator is introduced.

**Consequence.** Zero-drift permission-
class streak extends to **seventeen
consecutive milestones** (M10 →
M19.3).

## Delivered

**New view module**
`dealer_ai/views_pilot_onboarding.py`
(343 lines) with four handlers +
three request-body serializers + three
projection helpers:

- Request serializers:
  `PilotCreateRequestSerializer`,
  `ChecklistAdvanceRequestSerializer`,
  `TerminateRequestSerializer` — each
  validates its inbound vocab against
  the fixed-vocab constants from
  `models.py`.
- Projections:
  `_project_dealership`,
  `_project_step`,
  `_project_checklist` (surfaces steps
  in `PILOT_ONBOARDING_STEP_ORDER`
  order with placeholder rows for
  uncompleted steps so the UI renders
  a stable checklist),
  `_project_pilot_with_checklist`.
- Handlers:
  - `admin_pilot_create` — 201 on
    success with combined pilot +
    checklist; 400 on validation /
    unknown owner_username; 409 on
    `PilotAlreadyExistsError`.
  - `admin_pilot_list` — 200 with
    active pilots + nested
    checklists. Terminated pilots
    excluded per M19.1 posture.
  - `admin_pilot_checklist_advance` —
    200 with updated pilot; 400 on
    `UnknownChecklistStepError`; 404
    on nonexistent slug / non-pilot
    slug; 409 on
    `ChecklistStepAlreadyCompletedError`
    /
    `PilotReadinessNotConfirmedError`.
  - `admin_pilot_terminate` — 200
    with terminated dealership
    projection; 400 on unknown mode;
    404 on nonexistent slug; 500 on
    `NonPilotTerminationError`
    (broken-invariant guard).

**URL wiring** in
`dealer_ai/urls.py` — four new
paths:

- `admin/pilots/create/`
- `admin/pilots/`
- `admin/pilots/<slug:slug>/checklist/advance/`
- `admin/pilots/<slug:slug>/terminate/`

**31 focused tests** in new
`tests/test_m193_pilot_endpoints.py`:

- Auth gating (4): unauth → 401 (or
  403) per endpoint.
- `POST /admin/pilots/create/` (6):
  happy path 201 with full projection;
  slug collision vs existing pilot →
  409; slug collision vs existing demo
  → 409; unknown owner_username →
  400; missing required field → 400;
  profile_kwargs optional.
- `GET /admin/pilots/` (3):
  active-only filter (excludes
  terminated + non-pilot); each entry
  includes checklist; empty list when
  no pilots.
- `POST /admin/pilots/<slug>/checklist/advance/`
  (7): happy path advances step +
  projection reflects; unknown
  step_slug → 400; re-advance same
  step → 409; readiness precondition
  refused → 409; readiness after
  prior steps flips `is_ready=True`;
  nonexistent slug → 404; demo slug
  (non-pilot) → 404.
- `POST /admin/pilots/<slug>/terminate/`
  (5): archive mode flips is_pilot;
  cleanup mode cascades child
  Vehicles; unknown mode → 400;
  nonexistent slug → 404; blank
  reason ok.
- Checklist projection contract (2):
  steps ordered by
  `PILOT_ONBOARDING_STEP_ORDER`;
  placeholder rows have null
  completed_at.
- Zero-drift assertions (4):
  endpoint count `>=` 112 (108 →
  112); permission-class exact-set
  equality (streak of seventeen
  consecutive milestones); vocab
  constant sanity (7 steps in
  order); termination-mode constants
  stable.

## Baseline delta

- **Backend:** 4,628 → **4,659 pass**,
  1 skipped, 0 fail. **+31 tests, 0
  regressions.** In-range with the
  25-35 planning target.
- Migrations `0043-0048` (unchanged
  — M19.3 is view-only).
- Tenancy carriers **52** (unchanged
  — M19.3 adds no tenant-scoped
  models).
- DRF admin surface **108 → 112**
  (+4 pilot endpoints).
- Frontend operator routes **20**
  (unchanged — M19.4 extends
  existing admin route in place).
- Permission classes **7 actual** —
  **zero-drift streak now seventeen
  consecutive milestones** (M10 →
  M19.3).
- Celery-beat task families **10**
  (unchanged).
- Frontend Vitest **140**
  (unchanged — no frontend at
  M19.3).

## Streak update

**85 planning-time as-recommended
M5.1 → M19.0** (unchanged — M19.3 is
implementation-time work per M10 §9).
**Two §0.a M19.3 implementation-time
decisions recorded** (inventory-
import deferred to M19.4; endpoints
gated on `IsAuthenticated` alone).
Both defended in this handoff and
grounded in the pre-existing shipping
patterns (M18.5 admin endpoint style
+ M19.1 service-verb contract).

## What's next: SESSION_157 M19.4 frontend admin surface

Per `MILESTONE_19_PLANNING.md` §7
M19.4:

- Extend the existing DealerKit
  admin route in place (`/admin`)
  with a pilot-onboarding section
  — pilot list, create form,
  checklist stepper, terminate
  confirmation, and (per §0.a M19.3
  decision 1) a CSV upload panel
  wired to the new M19.4 inventory-
  import endpoint.
- New endpoint at M19.4:
  `POST /admin/pilots/<slug>/inventory/import/`
  wrapping `import_pilot_inventory`.
  Admin surface grows **112 → 113**.
- Frontend delta: ~2-4 new
  components under
  `frontend/src/features/admin/pilots/`
  reusing shadcn primitives; ~10-15
  Vitest additions.
- Focused frontend tests target:
  ~10-15 new Vitest cases in
  `frontend/src/features/admin/pilots/__tests__/`.
- Backend focused tests target:
  ~8-12 for the new inventory-
  import endpoint (both happy
  path + `NonPilotImportError` →
  500 + partial-success projection
  + file-upload edge cases).

**Baseline targets at M19.4 close:**
- Backend 4,659 → ~4,667-4,671 pass
  (+8-12 tests).
- Frontend Vitest 140 → ~150-155
  pass (+10-15 tests).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_155_m19_inc2_inventory_import.md`
7. `docs/handoffs/SESSION_154_m19_inc1_backend_substrate.md`
8. `docs/PILOT_INVENTORY_TEMPLATE.md`
9. `docs/CAPABILITY_MATRIX.md` §7s
10. `backend/dealer_ai/views_pilot_onboarding.py`
    (M19.3 handlers — reference
    shape for the M19.4 import
    handler)
11. `backend/dealer_ai/tests/test_m193_pilot_endpoints.py`
    (behavior contract)
