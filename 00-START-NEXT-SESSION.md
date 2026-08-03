---
state: active
date: 2026-08-02
last_session_shipped: SESSION_155
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
next_session: SESSION_156
next_milestone: 19
next_milestone_name: "Founding Dealer Pilot Onboarding"
next_increment: 3
next_increment_name: "M19.3 — DRF endpoints: pilot create/list/checklist/terminate (+optional import)"
---

# Next session — SESSION_156 · Milestone 19 · Increment 3 (M19.3 — DRF endpoints)

> **SESSION_155 shipped M19.2 —**
> pilot inventory import wrapper + CSV
> schema doc. `import_pilot_inventory`
> is a thin overlay on the shipped
> M6.3 `services/inventory_import.py`
> substrate — reuses the 21-column
> vocab verbatim (no fork) with three
> pilot-specific policy overrides
> (belt-and-suspenders `is_pilot`
> guard, `mark_missing_unavailable=False`,
> stable `source="pilot-inventory-import"`
> label). Partial-success + re-import-
> updates semantics inherited from
> M6.3. `docs/PILOT_INVENTORY_TEMPLATE.md`
> documents the shipping vocab as the
> authoritative pilot schema. Two §0.a
> M19.2 implementation-time decisions
> recorded — CSV vocab reuse + pilot
> policy overlay. Both grounded in the
> M6.3 substrate discovery at session
> open.
>
> **Backend baseline: 4,597 → 4,628
> pass** (+32 new − 1 retired
> stub = +31 net, 0 regressions).
> **Frontend Vitest: 140 pass**
> (unchanged). Migrations `0043`–`0048`
> (unchanged). Tenancy carriers 52
> (unchanged). DRF admin surface 108
> (unchanged — 4 endpoints land at
> M19.3). Frontend operator routes 20
> (unchanged). Permission classes 7
> (unchanged — zero-drift streak now
> **sixteen consecutive milestones**
> M10 → M19.2). Celery-beat task
> families 10 (unchanged).
>
> **SESSION_156 opens M19.3 —
> pilot admin endpoints.** Four
> handlers wrapping the M19.1 service
> verbs + potentially a fifth wrapping
> the M19.2 `import_pilot_inventory`.
> Single backend increment; ~25-35
> focused tests.

## First thing SESSION_156 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M19.2 commit.
- `python3 manage.py test dealer_ai`
  → **4,628 pass, 1 skipped, 0
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

### 2. Surface §0.a M19.3 micro-decisions

Two candidate micro-decisions
surface at M19.3 open:

1. **Include the inventory-import
   endpoint at M19.3.** The
   planning memo §7 M19.3 lists
   four handlers (create / list /
   checklist / terminate). The
   M19.2 `import_pilot_inventory`
   wrapper is done; wiring it as a
   5th endpoint keeps the admin
   surface self-contained before
   M19.4 frontend consumes.
   **Recommendation:** yes, ship at
   M19.3. Admin surface goes 108 →
   113 instead of 108 → 112. Small
   marginal cost + big cohesion
   win. If declined, the endpoint
   defers to M19.4 (frontend upload
   with no backend receiver — bad
   ergonomics) or M19.5 (playbook
   uses the Django management
   command instead — acceptable
   fallback).
2. **Permission-class posture.**
   Chris is the "operator of the
   platform," not a
   `IsDealerOwnerAtActiveDealership`
   at a pilot tenant (that role
   only exists after
   `create_pilot_dealership`
   attaches him). Options:
   (a) reuse
   `IsAuthenticated` for M19.3
   endpoints since only Chris has
   admin console access;
   (b) add a new
   `IsPlatformOperator` permission
   class scoped to a specific
   role.
   **Recommendation:**
   `IsAuthenticated` for M19.3.
   The M19.4 admin route already
   gates on
   `IsDealerOwnerAtActiveDealership`
   at the DealerKit control tenant.
   Adding a class here would
   break the zero-drift streak
   without operational benefit
   pre-multi-operator.

Present both briefly at open;
expect confirm-as-recommended per
the 85-milestone streak posture.
Record as §0.a M19.3 amendments.

## What M19.3 delivers

Per `MILESTONE_19_PLANNING.md` §7
M19.3 + §0.a M19.3 recommendations:

### New view module

**`dealer_ai/views_pilot_onboarding.py`**
with four (or five per §0.a
decision 1) handlers:

- `POST admin/pilots/create/` →
  `create_pilot_dealership` +
  201 with serialized
  `PilotOnboardingChecklist`.
  Domain-error mapping:
  `PilotAlreadyExistsError` →
  409.
- `GET admin/pilots/` →
  `list_pilot_dealerships` +
  200 with array of pilot
  summaries. Terminated pilots
  excluded per M19.1 posture.
- `POST admin/pilots/<slug>/checklist/advance/`
  → `advance_step` + 200 with
  updated checklist state.
  Domain-error mapping:
  `UnknownChecklistStepError` →
  400,
  `ChecklistStepAlreadyCompletedError`
  → 409,
  `PilotReadinessNotConfirmedError`
  → 409.
- `POST admin/pilots/<slug>/terminate/`
  → `terminate_pilot` + 200
  with terminated Dealership
  summary. Domain-error mapping:
  `NonPilotTerminationError` →
  500 (surfaces as internal
  server error; broken-invariant
  guard).
- **(optional 5th per §0.a M19.3
  decision 1)**
  `POST admin/pilots/<slug>/inventory/import/`
  → `import_pilot_inventory` +
  200 with serialized
  `PilotInventoryImportResult`.
  Accepts multipart file upload.
  Domain-error mapping:
  `NonPilotImportError` → 500,
  `FileNotFoundError` → 400.

### URL wiring

Register the four (or five)
handlers in
`dealer_ai/urls.py` under
`/admin/pilots/*`. Endpoint count
108 → **112** (or **113** with the
optional inventory-import
endpoint).

### Serializers

Thin DRF serializers projecting:

- `Dealership` → pilot summary
  (slug, name, is_pilot,
  outbound_enabled, created_at).
- `PilotOnboardingChecklist` +
  `PilotOnboardingStep` → nested
  checklist state (is_ready +
  ordered step list with
  completed_at / completed_by /
  notes).
- `PilotInventoryImportResult`
  → JSON dict with
  dealership_id + accepted +
  rejected arrays.

### Tests

**~25-35 focused tests** in new
`tests/test_m193_pilot_endpoints.py`:

- 200 happy path per endpoint.
- Auth gating (unauth → 401).
- Domain-error → HTTP status
  mapping (per error class).
- Serialization contract
  (nested checklist shape).
- Slug-in-URL validation
  (`<slug>` matches an existing
  pilot; 404 otherwise).
- Growth-only endpoint count
  assertion (108 → >=112 or
  113).
- Permission-class set
  equality (zero-drift streak
  seventeen consecutive
  milestones).

### Non-goals for M19.3

- ❌ No frontend (M19.4).
- ❌ No new tenant-scoped models.
- ❌ No new permission classes
  (per §0.a M19.3 decision 2
  recommendation).
- ❌ No modifications to M19.1
  service verbs.
- ❌ No changes to M6.3 or
  M19.2 inventory-import code.

## Backend baseline target

**4,628 → ~4,653-4,663 pass**
(+25-35 tests, 0 regressions).
Frontend Vitest: 140 (unchanged
— no frontend at M19.3).

## Explicit non-goals for SESSION_156

- ❌ Do NOT ship M19.4 frontend.
- ❌ Do NOT modify M1-M18 or
  M19.1-M19.2 business logic.
- ❌ Do NOT add new tenancy
  carriers.
- ❌ Do NOT force-push or amend
  earlier commits.

## NEXT TASK

Start SESSION_156 with (a)
surfacing the two §0.a M19.3
micro-decisions (inventory-
import endpoint inclusion +
permission-class posture) with
the user, (b) starting-state
verification, (c) building the
view module + URL wiring +
serializers + tests per §7 M19.3.
Ship the M19.3 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_155_m19_inc2_inventory_import.md`
   (this session's handoff)
7. `docs/handoffs/SESSION_154_m19_inc1_backend_substrate.md`
8. `docs/PILOT_INVENTORY_TEMPLATE.md`
9. `docs/CAPABILITY_MATRIX.md` §7s
10. `backend/dealer_ai/services/pilot_onboarding/`
    (verbs the endpoints will wrap)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_155 — M19.2 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,628 pass**, 1 skipped, 0
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
  M19.2 inventory import
  shipped. M19.3 endpoints next
  (SESSION_156).
- **DRF admin surface:** **108**
  endpoints. Grows to 112 (or
  113 with the optional
  inventory-import endpoint) at
  M19.3.
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
  (six modules — full
  `import_pilot_inventory`
  body shipped at M19.2).
- **Frontend accounting
  surface:** unchanged from
  M17.
- **Tenancy carriers:**
  **52** (unchanged at M19.2
  — M19.2 is service-only).
- **Permission classes:**
  **7 actual** — zero-drift
  streak **sixteen consecutive
  milestones** (M10 → M19.2).
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
  endpoints next (SESSION_156).
  M19.4 frontend, M19.5
  playbook + dry-run, M19.6
  close-out to follow.
