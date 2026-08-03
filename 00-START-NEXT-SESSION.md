---
state: active
date: 2026-08-02
last_session_shipped: SESSION_156
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: shipped
milestone_7_status: shipped
milestone_8_status: shipped
milestone_9_status: shipped
milestone_10_status: shipped
milestone_11_status: shipped
milestone_12_status: shipped
milestone_13_status: shipped
milestone_14_status: shipped
milestone_15_status: shipped
milestone_16_status: shipped
milestone_17_status: shipped
milestone_18_status: shipped
milestone_19_status: in-progress
next_session: SESSION_157
next_milestone: 19
next_milestone_name: "Founding Dealer Pilot Onboarding"
next_increment: 4
next_increment_name: "M19.4 — Frontend admin surface + inventory-import endpoint"
---

# Next session — SESSION_157 · Milestone 19 · Increment 4 (M19.4 — Frontend admin surface)

> **SESSION_156 shipped M19.3 —**
> four pilot admin endpoints
> (`POST /admin/pilots/create/`, `GET
> /admin/pilots/`, `POST
> /admin/pilots/<slug>/checklist/advance/`,
> `POST /admin/pilots/<slug>/terminate/`)
> + serializers + URL wiring + 31
> focused tests. Two §0.a M19.3
> implementation-time decisions
> recorded — inventory-import endpoint
> deferred to M19.4 alongside its
> frontend consumer + endpoints gated
> on `IsAuthenticated` alone (no new
> permission class).
>
> **Backend baseline: 4,628 → 4,659
> pass** (+31 tests, 0 regressions).
> **Frontend Vitest: 140 pass**
> (unchanged). Migrations `0043`–`0048`
> (unchanged). Tenancy carriers 52
> (unchanged). DRF admin surface **108
> → 112** (+4 pilot endpoints).
> Frontend operator routes 20
> (unchanged). Permission classes 7
> (unchanged — zero-drift streak now
> **seventeen consecutive milestones**
> M10 → M19.3). Celery-beat task
> families 10 (unchanged).
>
> **SESSION_157 opens M19.4 —
> frontend admin surface.** Extends
> the existing `/admin` route with a
> pilot-onboarding section (list,
> create, checklist stepper,
> terminate, CSV upload) + ships the
> deferred inventory-import endpoint
> alongside its consumer. Single
> mixed-stack increment;
> backend +8-12 tests,
> frontend +10-15 Vitest.

## First thing SESSION_157 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M19.3 endpoints
  commit.
- `python3 manage.py test dealer_ai`
  → **4,659 pass, 1 skipped, 0
  fail**.
- `cd frontend && npm test` →
  **140 pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No
  changes detected."
- `cd frontend && npx tsc
  --noEmit` clean.
- `redis-cli ping` → `PONG`.

### 2. Surface §0.a M19.4 micro-decisions

Two candidates likely surface at
M19.4 open:

1. **File-upload contract.** The
   inventory-import endpoint at
   M19.4 accepts a multipart
   file. Options:
   (a) DRF `FileField` on a
   serializer (canonical);
   (b) raw `request.FILES`
   inspection. **Recommendation:**
   `FileField`. Uniform with
   future upload endpoints;
   validated at the boundary;
   composable.
2. **Frontend route placement.**
   The pilot admin surface can
   (a) live at
   `/admin/pilots` as a
   sub-section of the existing
   `/admin` route, or (b) get
   its own top-level `/pilots`
   route. **Recommendation:**
   sub-section under `/admin`.
   Matches the intent that only
   Chris (the platform operator)
   sees this surface + keeps
   route count 20 unchanged.

Present both briefly at open;
expect confirm-as-recommended per
the 85-milestone streak posture.
Record as §0.a M19.4 amendments.

## What M19.4 delivers

Per `MILESTONE_19_PLANNING.md` §7
M19.4 + §0.a M19.3 decision 1
(deferred inventory-import
endpoint):

### Backend

**New endpoint**
`POST /admin/pilots/<slug>/inventory/import/`
in
`dealer_ai/views_pilot_onboarding.py`
wrapping `import_pilot_inventory`.

- Multipart file upload (DRF
  `FileField` per §0.a M19.4
  decision 1 recommendation).
- 200 with serialized
  `PilotInventoryImportResult`
  (dealership_id + accepted +
  rejected).
- 404 on nonexistent /
  non-pilot slug.
- 500 on `NonPilotImportError`
  (broken-invariant guard —
  shouldn't reach if the slug
  filter catches; belt-and-
  suspenders).
- 400 on missing file / bad
  content-type.

**URL wiring** adds a fifth
pilot admin path; admin surface
grows **112 → 113**.

### Frontend

**New sub-section** under the
existing `/admin` route:

- Pilot list panel — table view
  reading `GET /admin/pilots/`.
  Per-row: slug, name, ready
  badge, terminate button.
- Create form — modal (or
  inline) posting to
  `POST /admin/pilots/create/`.
- Checklist stepper —
  per-pilot detail view
  reading the checklist
  projection + POSTing to
  `checklist/advance/`.
- CSV upload panel — file
  input + submit posting
  multipart to
  `inventory/import/`.
  Rejected rows table.
- Terminate confirmation —
  modal with mode picker
  (archive / cleanup) +
  reason field.
- ~2-4 new components under
  `frontend/src/features/admin/pilots/`.
  Reuse shadcn primitives
  (Card, Table, Dialog, Form,
  Input, Button).

**No new frontend operator
routes.** Sub-section under
`/admin` per §0.a M19.4
decision 2 recommendation.

### Tests

**Backend ~8-12 tests** in new
`tests/test_m194_inventory_import_endpoint.py`:

- Multipart happy path — 200
  with dealership_id +
  accepted stock numbers +
  rejected rows in projection.
- Nonexistent slug → 404.
- Non-pilot slug → 404.
- Missing file → 400.
- Auth gating.
- Partial-success shape
  matches the M19.2 wrapper's
  return contract.
- Endpoint count `>=` 113
  growth-only assertion.
- Permission-class zero-drift
  streak now **eighteen
  consecutive milestones**.

**Frontend ~10-15 Vitest** in
new
`frontend/src/features/admin/pilots/__tests__/`:

- Pilot list renders slug +
  ready badge.
- Create form validation.
- Checklist stepper displays
  ordered steps + placeholder
  rows.
- CSV upload triggers POST
  with correct multipart
  body.
- Terminate modal fires
  correct mode.

### Non-goals for M19.4

- ❌ No new tenancy carriers.
- ❌ No changes to M19.1 /
  M19.2 / M19.3 backend
  contracts.
- ❌ No new operator routes.
- ❌ No M19.5 playbook doc.

## Baseline targets

- **Backend:** 4,659 → ~4,667-
  4,671 pass (+8-12 tests, 0
  regressions).
- **Frontend Vitest:** 140 →
  ~150-155 pass (+10-15
  tests).
- **Admin surface:** 112 →
  **113** (+1 inventory-import
  endpoint).
- **Frontend routes:** 20
  (unchanged).

## Explicit non-goals for SESSION_157

- ❌ Do NOT ship M19.5
  playbook or dry-run doc.
- ❌ Do NOT modify M1-M19.3
  business logic.
- ❌ Do NOT add new permission
  classes.
- ❌ Do NOT force-push or
  amend earlier commits.

## NEXT TASK

Start SESSION_157 with (a)
surfacing the two §0.a M19.4
micro-decisions (file-upload
contract + frontend route
placement) with the user,
(b) starting-state
verification, (c) implementing
the inventory-import endpoint
+ pilot admin sub-section +
tests per §7 M19.4. Ship the
M19.4 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_156_m19_inc3_endpoints.md`
   (this session's handoff)
7. `docs/handoffs/SESSION_155_m19_inc2_inventory_import.md`
8. `docs/PILOT_INVENTORY_TEMPLATE.md`
9. `docs/CAPABILITY_MATRIX.md` §7s
10. `backend/dealer_ai/views_pilot_onboarding.py`
    (endpoint pattern for the
    M19.4 import handler)
11. `backend/dealer_ai/services/pilot_onboarding/inventory_import.py`
    (wrapper the M19.4 endpoint
    invokes)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_156 — M19.3 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,659 pass**, 1 skipped, 0
  fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` +
  `vite build` clean. **Vitest
  baseline: 140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery
  5.5.3 + Redis 6.4.0 +
  `django-celery-beat` 2.8.1
  DatabaseScheduler. **10
  scheduled task families
  registered**.
- **Milestones shipped:** M1 →
  M18. M19 in progress: M19.0
  planning + M19.1 substrate +
  M19.2 inventory import +
  M19.3 endpoints shipped.
  M19.4 frontend + import
  endpoint next (SESSION_157).
- **DRF admin surface:** **112**
  endpoints (108 → 112 at
  M19.3; grows to 113 at
  M19.4).
- **Frontend operator routes:**
  **20** — unchanged through
  M19 (M19.4 extends existing
  admin route in place).
- **Public endpoints:** +1
  M6.5 showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) +
  five M11 packages + seven
  M12 packages + `services/
  accounting/` (seven modules)
  + `services/demo_store/`
  (ten modules including
  briefs package) +
  `services/pilot_onboarding/`
  (six modules). New at M19.3:
  `dealer_ai/views_pilot_onboarding.py`.
- **Frontend accounting
  surface:** unchanged from
  M17.
- **Tenancy carriers:**
  **52** (unchanged at M19.3
  — endpoints/views only).
- **Permission classes:**
  **7 actual** — zero-drift
  streak **seventeen
  consecutive milestones**
  (M10 → M19.3).
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17
  scrub stages (unchanged —
  M19 has no LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 19 status:**
  M19.0 planning SHIPPED
  (SESSION_153). M19.1
  substrate SHIPPED
  (SESSION_154). M19.2
  inventory import SHIPPED
  (SESSION_155). M19.3
  endpoints SHIPPED
  (SESSION_156). M19.4
  frontend + import endpoint
  next (SESSION_157).
  M19.5 playbook + dry-run,
  M19.6 close-out to follow.
