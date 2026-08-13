---
title: "SESSION_153 handoff — Milestone 19 · Increment 0 (M19.0 — planning refinement)"
status: historical
type: handoff
date: 2026-08-02
session: 153
milestone: 19
milestone_status: in-progress
milestone_name: "Founding Dealer Pilot Onboarding"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_153 — Milestone 19 · Increment 0 (M19.0 — planning refinement)

## What shipped

Planning-only session per the M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 / M15.0 /
M16.0 / M17.0 / M18.0 precedent. Full
memo expansion + all **eight** §5 load-
bearing decisions resolved at open.

**§5.a → Option V confirmed** — pilot-
customer onboarding. Milestone name:
**"Founding Dealer Pilot Onboarding."**
User named at SESSION_153 M19.0 open.
Tester sessions have not happened since
M18 close, so Option T (process tester
feedback) stays deferred for a future
milestone. Option V builds the controlled
conversion path from demo → pilot so
testers who commit have a place to land.

**§5.b–§5.h all confirmed as-recommended.**
Streak extends to **85 planning-time as-
recommended M5.1 → M19.0** across **ten
consecutive milestones now** (M10 + M11
+ M12 + M13 + M14 + M15 + M16 + M17 +
M18 + M19). Historical §5 counts have
been 6-7 per milestone; M19 at eight
reflects the pilot-onboarding scope's
breadth (fourteen planning topics
compressed into eight decisions).

**Backend baseline unchanged:** 4,538
pass, 1 skipped, 0 fail (verified at
session open). **Frontend Vitest
baseline unchanged:** 140 pass.
Migrations `0043`–`0047` (unchanged).
Tenancy carriers 50 (unchanged —
PilotProspect + PilotOnboardingChecklist
+ PilotOnboardingStep land at M19.1).
DRF admin surface 108 (unchanged — 4
new endpoints land at M19.3). Frontend
operator routes 20 (unchanged — M19.4
extends existing admin route in place).
Permission classes 7 (unchanged —
zero-drift streak holds at fourteen
consecutive milestones; M19.3 endpoint
additions reuse existing classes).
Celery-beat task families 10 (unchanged
— M19 has no beat entry).

## Load-bearing decisions confirmed at M19.0 open

Eight decisions per M10.0 / M11.0 / M12.0
/ M13.0 / M14.0 / M15.0 / M16.0 / M17.0 /
M18.0 precedent. All confirmed as-
recommended.

**§5.a — Milestone target selection.**
Option V — pilot-customer onboarding.
Milestone name: "Founding Dealer Pilot
Onboarding." M18 shipped validation
infrastructure; the natural follow-on is
the controlled conversion path so
committed testers can be onboarded
safely.

**§5.b — Pilot eligibility + conversion
criteria.** Option C — hybrid
`PilotProspect` entity with structured
note fields (`dealer_type`,
`bhph_enabled`, `estimated_inventory_size`,
`contact_source`, `chris_notes`) +
operator-owned `eligibility_state` state
machine (`prospect` → `qualified` →
`converted` OR → `declined`).

**§5.c — Tenancy type designation.**
Option A — add `Dealership.is_pilot
BooleanField(default=False)` mirroring
M18's `is_demo` shape. New
`is_synthetic_tenant(dealership) ->
bool` helper (`is_demo or is_pilot`)
extends the M18.1 outbound guard.

**§5.d — Pilot dealership creation
service.** Option A — new
`services/pilot_onboarding/` package
with `create_pilot_dealership(*, slug,
name, owner_user, profile_kwargs) ->
Dealership` atomic verb. Sibling to
`services/demo_store/registry`. Auto-
fires `PilotOnboardingChecklist` per
§5.f Option A.

**§5.e — Inventory import + dirty-data
handling.** Option A — extend M6.3
substrate with
`PilotInventoryImportResult` frozen
dataclass. Per-row accepted/rejected +
errors. **No silent defaulting** —
Chris hand-cleans rejected rows. New
`docs/PILOT_INVENTORY_TEMPLATE.md`
ships at M19.5.

**§5.f — Capability enablement +
onboarding checklist + readiness.**
Option A — capability gating reads
existing `DealerOnboardingProfile`
fields; new `PilotOnboardingChecklist`
+ `PilotOnboardingStep` with fixed-
vocab step slugs
(`dealership_created`,
`profile_configured`,
`owner_user_added`,
`staff_users_added`,
`inventory_imported`,
`capabilities_enabled`,
`readiness_confirmed`).
`is_ready=True` gates operator surface
access.

**§5.g — Outbound integration posture
during pilot.** Option A — extend the
M18.1 outbound guard to include
pilots. **All outbound suppressed by
default for pilots.** Per-verb opt-in
gated on future code review.
Documented in the M19.5 playbook.

**§5.h — Pilot termination + software-
vs-consulting boundary.** Option A —
`terminate_pilot(*, dealership,
reason, actor, mode)` atomic verb.
Two additive `Dealership` columns:
`terminated_at` +
`termination_reason`. `mode='archive'`
preserves child rows;
`mode='cleanup'` cascades reverse-
order per M18.2 pattern. Boundary
policy documented in
`docs/PILOT_ONBOARDING_PLAYBOOK.md`
at M19.5.

## Streak

**85 planning-time as-recommended
M5.1 → M19.0.** Ten consecutive
milestones now (M10 + M11 + M12 + M13
+ M14 + M15 + M16 + M17 + M18 + M19)
with every §5 decision confirmed as-
recommended at planning-time open.

Historical §5 counts:
- M10 through M17: 6 decisions each
  = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- Total: 48 + 7 + 8 = **63 §5
  decisions across ten milestones**.
- Wait — 85 is the running counter
  including everything from M5.1
  forward, not just M10-M19.

Correction: the streak count "85
planning-time as-recommended M5.1 →
M19.0" accumulates across the full
tracked history from M5.1. The ten
consecutive milestones (M10 → M19)
carries the "as-recommended per
milestone open" invariant without a
single deviation.

## What's next: SESSION_154 M19.1 backend substrate

Per `MILESTONE_19_PLANNING.md` §7
M19.1:

- Migration
  `0048_m191_pilot_substrate.py`
  bundling `is_pilot` + termination
  fields + PilotProspect +
  PilotOnboardingChecklist +
  PilotOnboardingStep.
- Vocab constants: prospect state
  choices + onboarding step slug
  choices.
- Register PilotOnboardingChecklist
  + PilotOnboardingStep in
  `_TENANT_CARRIER_MODEL_NAMES`
  (count 50 → 52; PilotProspect
  posture TBD as §0.a M19.1 micro-
  decision).
- New `services/pilot_onboarding/`
  package with errors + registry
  (create_pilot_dealership +
  list_pilot_dealerships +
  terminate_pilot) + prospects
  (create_prospect +
  advance_prospect_state +
  list_prospects) + checklist
  (create_checklist + advance_step
  + is_pilot_ready) + inventory_import
  stub.
- Extend M18.1
  `services/demo_store/outbound_guard.py`
  with `is_pilot_dealership()` +
  `is_synthetic_tenant()` helpers.
  Preserve `is_demo_dealership()`
  as deprecated alias.
- New `make_pilot_dealership(...)`
  test helper in
  `tests/_auth_helpers.py`.
- ~40-50 focused tests in
  `tests/test_m191_pilot_substrate.py`.
- Domain exceptions:
  `PilotAlreadyExistsError` (409),
  `NonPilotTerminationError` (500),
  `PilotReadinessNotConfirmedError`
  (409).

**Backend baseline target at M19.1
close:** 4,538 → ~4,578-4,588 pass.
Frontend Vitest: 140 (unchanged).

## What lands at M19.2 (SESSION_155)

- Fill in
  `services/pilot_onboarding/inventory_import.py::import_pilot_inventory`.
- Extend M6.3 substrate as needed.
- Validation contract per row
  (required cols + type + range
  checks).
- ~15-25 focused tests.

## What lands at M19.3 (SESSION_156)

- Four DRF endpoints in
  `views_pilot_onboarding.py`:
  create + list + checklist advance +
  terminate.
- DRF admin surface 108 → **112**
  (+4).
- Zero-drift permission-class streak
  extends to fifteen consecutive
  milestones.
- ~20-30 focused tests.

## What lands at M19.4 (SESSION_157)

- Frontend: pilot admin surface
  extending existing admin route in
  place. Frontend operator routes
  stay at 20.
- New `pilotOnboardingApi.ts`
  fetchers + mutators + types.
- Vitest coverage.

## What lands at M19.5 (SESSION_158)

- `docs/PILOT_ONBOARDING_PLAYBOOK.md`
  + `docs/PILOT_INVENTORY_TEMPLATE.md`.
- First end-to-end dry-run against a
  synthetic prospect.
- UI defect fixes only per §5.f
  evidence gate.

## What lands at M19.6 (SESSION_159)

- Close-out: retrospective +
  capability matrix §7t + roadmap
  flip + M20 skeleton + session-start
  refresh + coordinated commit.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (this session's expansion target)
6. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §6 + §8 + §9
7. `docs/CAPABILITY_MATRIX.md` §7s
8. `docs/research/INDEPENDENT_DEALER_PIVOT.md`
