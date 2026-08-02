---
state: active
date: 2026-08-02
last_session_shipped: SESSION_153
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
next_session: SESSION_154
next_milestone: 19
next_milestone_name: "Founding Dealer Pilot Onboarding"
next_increment: 1
next_increment_name: "M19.1 — Backend substrate: schema + service package + guards"
---

# Next session — SESSION_154 · Milestone 19 · Increment 1 (M19.1 — Backend substrate)

> **SESSION_153 shipped M19.0 —**
> planning refinement + all eight §5
> load-bearing decisions resolved at
> open. **§5.a Option V confirmed** —
> pilot-customer onboarding. Milestone
> name: **"Founding Dealer Pilot
> Onboarding."** Tester sessions have
> not happened since M18 close so
> Option T stays deferred. Option V
> builds the controlled conversion
> path from demo → pilot so testers
> who commit have a place to land.
>
> **§5.b–§5.h all confirmed as-
> recommended.** Streak extends to
> **85 planning-time as-recommended
> M5.1 → M19.0** across **ten
> consecutive milestones now** (M10 +
> M11 + M12 + M13 + M14 + M15 + M16
> + M17 + M18 + M19). Historical §5
> counts have been 6-7 per milestone;
> M19 at eight reflects the pilot-
> onboarding scope's breadth
> (fourteen planning topics
> compressed into eight decisions).
>
> **Backend baseline: 4,538 pass**,
> 1 skipped, 0 fail (unchanged —
> planning-only). **Frontend Vitest
> baseline: 140 pass** (unchanged).
> Migrations `0043`–`0047`
> (unchanged). Tenancy carriers 50
> (unchanged — PilotOnboardingChecklist
> + PilotOnboardingStep land at M19.1).
> DRF admin surface 108 (unchanged
> — 4 new endpoints land at M19.3).
> Frontend operator routes 20
> (unchanged — M19.4 extends
> existing admin route in place).
> Permission classes 7 (unchanged
> — zero-drift streak holds at
> fourteen consecutive milestones;
> M19.3 endpoint additions reuse
> existing classes). Celery-beat
> task families 10 (unchanged — M19
> has no beat entry).
>
> **SESSION_154 opens M19.1 —
> backend substrate.** Migration
> `0048_m191_pilot_substrate.py`
> bundling three additive
> `Dealership` columns +
> `PilotProspect` +
> `PilotOnboardingChecklist` +
> `PilotOnboardingStep`. New
> `services/pilot_onboarding/`
> package. Extend M18.1 outbound
> guard. Single backend increment;
> ~40-50 focused tests.

## First thing SESSION_154 must do

### 1. Resolve §0.a M19.1 micro-decisions

Two micro-decisions surfaced in
the M19.0 planning memo that need
resolution at M19.1 open:

1. **`PilotProspect` tenancy
   posture.** The model has no
   `Dealership` FK by §5.b design
   (it's scoped to Chris's operator
   surface, not a specific
   dealership tenant). Should it
   be registered in
   `_TENANT_CARRIER_MODEL_NAMES`
   for the pre_save autofill
   safety net? **Recommendation:**
   yes, register it. The autofill
   attaches the default dealership
   defensively; the
   `list_prospects` verb filters
   by operator role, not by
   tenancy scope. Registering
   preserves the M18.1 pattern
   without special-casing. Tenancy
   carrier count 50 → **53** (+3
   for PilotProspect + Checklist
   + Step) instead of 50 → 52.
2. **`suppress_if_demo` rename.**
   The M18.1 helper is called
   `suppress_if_demo`; §5.g Option
   A introduces
   `is_synthetic_tenant()`.
   Should `suppress_if_demo` be
   renamed to
   `suppress_if_synthetic` +
   preserve the old name as a
   deprecated alias?
   **Recommendation:** yes,
   rename. All existing callers
   of `suppress_if_demo` update
   in the same commit; the alias
   stays as a shim until M20+
   confirms no external usage.

Present both to the user briefly
at open; expect confirm-as-
recommended per the M5.1 → M19.0
streak posture. Record as §0.a
M19.1 amendments.

### 2. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M19.0 planning
  commit.
- `python3 manage.py test dealer_ai`
  → **4,538 pass, 1 skipped, 0
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

## What M19.1 delivers

Per `MILESTONE_19_PLANNING.md` §7
M19.1:

### Schema

- **Migration
  `0048_m191_pilot_substrate.py`**
  bundling all M19 schema
  additions (per M13.1 / M18.1
  bundling precedent):
  - `AddField
    Dealership.is_pilot`
    BooleanField(default=False).
  - `AddField
    Dealership.terminated_at`
    DateTimeField(null=True,
    blank=True).
  - `AddField
    Dealership.termination_reason`
    TextField(blank=True,
    default="").
  - `CreateModel PilotProspect`
    per §5.b field set (no
    dealership FK).
  - `CreateModel
    PilotOnboardingChecklist`
    (dealership FK CASCADE,
    is_ready BooleanField,
    created_at, updated_at).
  - `CreateModel
    PilotOnboardingStep`
    (checklist FK CASCADE,
    dealership FK CASCADE,
    step_slug CharField
    choices, completed_at
    DateTimeField null, notes
    TextField blank,
    created_at).
    `Meta.unique_together =
    (('checklist',
    'step_slug'),)`.

### Vocab constants

In `models.py`:

- `PILOT_PROSPECT_STATE_*` +
  `PILOT_PROSPECT_STATE_CHOICES`
  (fixed vocab: prospect /
  qualified / converted /
  declined).
- `PILOT_ONBOARDING_STEP_*`
  slug constants +
  `PILOT_ONBOARDING_STEP_CHOICES`
  (fixed vocab: seven step
  slugs per §5.f).

Exact-set assertions at test
time.

### Tenancy registration

Register `PilotProspect` +
`PilotOnboardingChecklist` +
`PilotOnboardingStep` in
`_TENANT_CARRIER_MODEL_NAMES`
in `services/tenancy.py`.
Count 50 → **53** per §0.a
M19.1 decision 1 (see
"First thing" above).

### Service package

New `services/pilot_onboarding/`
package (per §5.d Option A):

- `__init__.py` with `__all__`
  exports.
- `errors.py`:
  - `PilotAlreadyExistsError`
    (409 mapping).
  - `NonPilotTerminationError`
    (500 broken-invariant guard).
  - `PilotReadinessNotConfirmedError`
    (409 mapping).
- `registry.py`:
  - `create_pilot_dealership(*,
    slug, name, owner_user,
    profile_kwargs) ->
    Dealership` — atomic. Catches
    `IntegrityError` on slug +
    re-raises as
    `PilotAlreadyExistsError`.
    Auto-fires
    `PilotOnboardingChecklist`.
  - `list_pilot_dealerships() ->
    list[Dealership]` — pure
    read (`is_pilot=True,
    terminated_at=NULL`).
  - `terminate_pilot(*,
    dealership, reason, actor,
    mode) -> Dealership` —
    atomic. Raises
    `NonPilotTerminationError`
    if `is_pilot=False`; belt-
    and-suspenders `assert
    dealership.is_pilot` at top.
- `prospects.py`:
  - `create_prospect(...)`.
  - `advance_prospect_state(*,
    prospect, new_state)`.
  - `list_prospects() ->
    list[PilotProspect]`.
- `checklist.py`:
  - `create_checklist(*,
    dealership) ->
    PilotOnboardingChecklist`
    (called by
    `create_pilot_dealership`).
  - `advance_step(*, checklist,
    step_slug, notes='') ->
    PilotOnboardingStep`
    (raises
    `PilotReadinessNotConfirmedError`
    if trying to advance
    `readiness_confirmed`
    before prior steps
    complete).
  - `is_pilot_ready(dealership)
    -> bool`.
- `inventory_import.py`:
  - `PilotInventoryImportResult`
    frozen dataclass.
  - `import_pilot_inventory`
    stub (raises
    `NotImplementedError`;
    ships fully at M19.2).

### Extend M18.1 outbound guard

Update
`services/demo_store/outbound_guard.py`
per §5.g Option A + §0.a
M19.1 decision 2:

- Add
  `is_pilot_dealership(dealership)
  -> bool`.
- Add
  `is_synthetic_tenant(dealership)
  -> bool` (`is_demo or
  is_pilot`).
- Rename `suppress_if_demo` →
  `suppress_if_synthetic`;
  preserve `suppress_if_demo`
  as deprecated alias
  (shim + logger.warning +
  DeprecationWarning).
- Preserve
  `is_demo_dealership()` as
  deprecated alias.
- **Extend the outbound-egress
  scanner test** to hold —
  it should still pass without
  modification since the
  extended helper is a drop-in
  replacement.

### Test helper

Extend `tests/_auth_helpers.py`
with:

- `make_pilot_dealership(*,
  slug, name, owner_user_kwargs,
  profile_kwargs) ->
  Dealership` companion to
  `make_dealership`.

### Tests

**~40-50 focused tests** in new
`tests/test_m191_pilot_substrate.py`:

- Model defaults + vocab
  exact-set equality.
- `PilotProspect` model +
  state machine transitions.
- Checklist model +
  unique_together per step.
- `create_pilot_dealership`
  happy path (atomic; all
  substrate commits together).
- Slug collision raises
  `PilotAlreadyExistsError`.
- `create_pilot_dealership`
  against existing demo slug
  raises.
- `list_pilot_dealerships`
  filters correctly.
- `terminate_pilot` both
  modes (`archive` + `cleanup`).
- `terminate_pilot` raises
  `NonPilotTerminationError`
  on non-pilot.
- Belt-and-suspenders `assert`
  fires on bypass mock.
- Checklist step advance
  happy path.
- Checklist advance blocked
  when `readiness_confirmed`
  precondition not met.
- `is_pilot_ready` returns
  True only when checklist
  complete.
- Outbound guard extension
  (is_synthetic_tenant for
  demo / pilot / both / live).
- Scanner test continues to
  hold.
- Tenancy carrier count 53
  (or 52 depending on §0.a
  decision 1) — `>=`
  assertion.
- Permission-class set
  equality unchanged (zero-
  drift streak fifteen
  consecutive milestones).
- Endpoint count 108
  (unchanged at M19.1).

### Non-goals for M19.1

- ❌ No DRF endpoints (M19.3).
- ❌ No frontend.
- ❌ No inventory import
  implementation body (M19.2).
- ❌ No playbook or template
  docs (M19.5).
- ❌ No new Celery-beat
  entries.
- ❌ No new permission classes.
- ❌ No new operator routes.

## Backend baseline target

**4,538 → ~4,578-4,588 pass**
(+40-50 tests, 0 regressions).
Frontend Vitest: 140 (unchanged
— M19.4 delta only).

## Explicit non-goals for SESSION_154

- ❌ Do NOT ship M19.2 inventory
  import implementation.
- ❌ Do NOT modify M1-M18
  business logic (except the
  deliberate M18.1 outbound
  guard extension).
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_154 with (a)
resolving the two §0.a M19.1
micro-decisions with the user
(PilotProspect tenancy
registration + `suppress_if_demo`
rename), (b) starting-state
verification, (c) building
schema + service package +
outbound guard extension + tests
per §7 M19.1. Ship the M19.1
handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_153_m19_inc0_planning.md`
   (this session's handoff)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
8. `docs/CAPABILITY_MATRIX.md` §7s

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_153 — M19.0 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0047`. Test baseline:
  **4,538 pass**, 1 skipped, 0
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
  planning shipped at
  SESSION_153. M19.1 substrate
  next (SESSION_154).
- **DRF admin surface:** **108**
  endpoints. Grows to 112 at
  M19.3 (+4 pilot endpoints).
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
  briefs package). **New at
  M19.1**:
  `services/pilot_onboarding/`
  package.
- **Frontend accounting
  surface:** unchanged from
  M17.
- **Tenancy carriers:**
  **50**. Grows to 53 at
  M19.1 (PilotProspect +
  PilotOnboardingChecklist +
  PilotOnboardingStep per
  §0.a M19.1 decision 1).
- **Permission classes:**
  **7 actual** — zero-drift
  streak fourteen consecutive
  milestones (M10 → M18.5).
  Extends to fifteen after
  M19.3 as no new class
  ships.
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
  substrate next
  (SESSION_154). M19.2
  inventory import, M19.3
  endpoints, M19.4 frontend,
  M19.5 playbook + dry-run,
  M19.6 close-out to follow.
