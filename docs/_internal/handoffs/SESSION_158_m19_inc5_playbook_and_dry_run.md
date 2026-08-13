---
title: "SESSION_158 handoff — Milestone 19 · Increment 5 (M19.5 — Playbook + end-to-end dry-run)"
status: historical
type: handoff
date: 2026-08-02
session: 158
milestone: 19
milestone_status: in-progress
milestone_name: "Founding Dealer Pilot Onboarding"
increment: 5
increment_status: shipped
---

# SESSION_158 — Milestone 19 · Increment 5 (M19.5 — Playbook + first end-to-end dry-run)

## What shipped

Single-purpose increment per
`MILESTONE_19_PLANNING.md` §7 M19.5.
Ships the operator playbook doc +
an authoritative end-to-end dry-run
test walking the full M19.1-M19.4
substrate in one coherent journey.

**Two §0.a M19.5 implementation-time
decisions recorded** (do not count
against planning-time streak per M10
§9). Both surfaced at open with
grounding in the M19 posture and
doc-governance rules.

### §0.a M19.5 decision 1 — dry-run as Django TestCase

**Decision.** The end-to-end dry-run
ships as a Django `TestCase` in
`tests/test_m195_pilot_dry_run.py` —
part of the normal
`manage.py test dealer_ai` suite.

**Why the management-command
alternative was ruled out for M19.5.**
The dry-run's primary value is
codified contract verification across
M19.1-M19.4 — every push proves the
pilot substrate holds end-to-end. A
management-command diagnostic only
catches drift when Chris (or CI)
explicitly invokes it, giving up the
per-push CI signal.

A management-command layer may ship
at M19.6 or M20 if Chris wants an
operator smoke button against
staging/prod. Not blocked by this
decision.

### §0.a M19.5 decision 2 — text + `data-testid` selectors (no screenshots)

**Decision.** The playbook narrates
each step by intent + role +
frontend selector, never by
screenshot.

**Why.** Screenshots go stale
immediately as UI iterates; text +
`data-testid` selectors stay in sync
with the code because the M19.4
component test asserts on those
selectors. Any rename fires CI
failure, keeping the playbook honest.
Aligns with `DOC_GOVERNANCE.md`
Principle 2 (prefer updating
authoritative docs over parallel
artifacts) and Principle 3 (avoid
duplicate documentation).

Screenshots would belong in a
future customer-facing marketing
artifact, not the internal
operational source of truth.

## Delivered

**New end-to-end test suite**
`backend/dealer_ai/tests/test_m195_pilot_dry_run.py`
(571 lines) with **10 focused tests**:

- :class:`FullPilotJourneyDryRun` (1
  test — `test_full_journey`) — one
  coherent narrative test method
  walking thirteen phases:
  1. Record a prospect referencing
     the source demo dealership.
  2. Qualify the prospect
     (`prospect → qualified`).
  3. Create the pilot dealership
     (verify `is_pilot=True`,
     `outbound_enabled=False`,
     `is_demo=False`, auto-fired
     checklist + `dealership_created`
     step, owner dealer_owner
     membership).
  4. Convert the prospect pinning
     the `converted_dealership` FK.
  5. Advance `profile_configured`.
  6. Import inventory via
     `import_pilot_inventory`
     (2 accepted + 1 rejected —
     partial-success semantics).
  7. Advance `inventory_imported`.
  8. Attach staff advisor
     (Salesperson + advisor role).
  9. Advance `owner_user_added`,
     `staff_users_added`,
     `capabilities_enabled`.
  10. Assert `is_pilot_ready==False`,
      advance `readiness_confirmed`,
      assert `checklist.is_ready==True`
      + `is_pilot_ready==True`.
  11. Verify outbound guard suppresses
      (`is_outbound_enabled==False`;
      `suppress_if_outbound_disabled`
      returns `SuppressedOutbound`
      marker) for both pilot AND the
      original source demo (M19.1
      refactor: policy field, not
      tenant type).
  12. Cross-tenant isolation:
      a second dealership's Vehicles
      + memberships do not leak into
      the pilot's queries.
  13. Belt-and-suspenders guards
      refuse import + terminate
      against a non-pilot dealership
      (`NonPilotImportError`,
      `NonPilotTerminationError`).
  14. Terminate in archive mode;
      verify pilot leaves
      `list_pilot_dealerships`,
      children survive,
      `converted_dealership` FK
      still resolves, prospect
      remains in `list_prospects`.
- :class:`EndpointE2EDryRunTests` (1
  test) — drives all five M19.3+M19.4
  admin endpoints in the operator
  sequence through a single
  authenticated `APIClient`:
  `POST create` → `GET list` →
  `POST checklist advance` →
  `POST inventory import` (multipart)
  → `POST terminate` → verify pilot
  removed from re-fetched list.
- :class:`SafetyGuardDryRunTests` (5
  tests) — import against live
  dealership raises
  `NonPilotImportError`; terminate
  against live raises
  `NonPilotTerminationError`;
  terminate against demo raises
  `NonPilotTerminationError`;
  deprecated `suppress_if_demo` alias
  still routes through policy-field
  predicate; prospect
  `converted_dealership` FK survives
  archive termination.
- :class:`M195ZeroDriftTests` (3
  tests) — tenancy carriers `>=` 52,
  admin endpoints `>=` 113,
  permission-class exact-set equality
  (streak now **nineteen consecutive
  milestones** M10 → M19.5).

**New operator playbook**
`docs/PILOT_ONBOARDING_PLAYBOOK.md`
— narrative operator reference
covering all thirteen phases. Names
the backend verb / endpoint at each
step + the frontend `data-testid`
selector where the operator acts.
Includes a rollback / recovery
section for common failure modes
(bad slug, wrong owner, bad
inventory, readiness precondition,
wrong-pilot terminate) and links
to the authoritative dry-run test
as the source-of-truth contract.

**One implementation-time
correction:** the initial dry-run
passed `dealer_business_name` to
`profile_kwargs` but
`DealerOnboardingProfile` has field
`dealership_name`. Fixed by
correcting the kwarg name — the
test caught its own guessing before
the full-suite run.

## Baseline delta

- **Backend:** 4,669 → **4,679 pass**,
  1 skipped, 0 fail. **+10 tests, 0
  regressions.** In-range with the
  5-10 planning target.
- Migrations `0043-0048` (unchanged
  — M19.5 is test + doc only).
- Tenancy carriers **52** (unchanged
  — no new tenant-scoped models).
- DRF admin surface **113**
  (unchanged — M19.5 adds no
  endpoints).
- Frontend operator routes **20**
  (unchanged).
- Permission classes **7 actual** —
  **zero-drift streak now nineteen
  consecutive milestones** (M10 →
  M19.5).
- Celery-beat task families **10**
  (unchanged).
- Frontend Vitest **153**
  (unchanged — no frontend at
  M19.5).

## Streak update

**85 planning-time as-recommended
M5.1 → M19.0** (unchanged — M19.5 is
implementation-time work per M10
§9). **Two §0.a M19.5 implementation-
time decisions recorded** (dry-run
as TestCase + text-first playbook
posture). Both grounded in the
M19 posture and doc-governance
rules.

## What's next: SESSION_159 M19.6 close-out

Per `MILESTONE_19_PLANNING.md` §7
M19.6:

- Milestone retrospective doc
  `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
  — captures shipped scope,
  deferrals, lessons, and
  numeric baseline delta across
  M19.0 → M19.5. Follows the
  M18 retrospective template.
- Update `docs/CAPABILITY_MATRIX.md`
  §7t (or next-index) with the
  M19 additions:
  `services/pilot_onboarding/`,
  `views_pilot_onboarding.py`,
  `<PilotOnboardingSection>`,
  `PILOT_INVENTORY_TEMPLATE.md`,
  `PILOT_ONBOARDING_PLAYBOOK.md`.
- Refresh `00-START-NEXT-SESSION.md`
  for **Milestone 20 planning**
  (SESSION_160 opens M20.0).
- Coordinated close-out commit
  ("Milestone 19 shipped").
- Potential Milestone 20 candidates
  to surface at close-out:
  - Onboarding UX polish
    (progress bar, tester intake
    UI for the deferred prospect
    surface).
  - First live pilot conversion
    dry-run against staging (not
    just codified tests).
  - Multi-operator support
    (adds `IsPlatformOperator`
    permission class — breaks
    the zero-drift streak with
    intent).
  - Return to accounting stream
    (M20 candidate list from
    M18 retrospective).

**Backend baseline target at M19.6
close:** 4,679 → ~4,679-4,682 pass
(close-out increments typically add
0-3 tests). Frontend Vitest: 153
(unchanged).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_157_m19_inc4_frontend_and_import_endpoint.md`
7. `docs/PILOT_ONBOARDING_PLAYBOOK.md`
   (freshly shipped)
8. `docs/PILOT_INVENTORY_TEMPLATE.md`
9. `docs/CAPABILITY_MATRIX.md` §7s
10. `backend/dealer_ai/tests/test_m195_pilot_dry_run.py::FullPilotJourneyDryRun::test_full_journey`
    (authoritative end-to-end
    contract — playbook and code
    disagree, this test wins)
