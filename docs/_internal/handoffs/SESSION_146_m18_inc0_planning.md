---
title: "SESSION_146 handoff — Milestone 18 · Increment 0 (M18.0 — planning refinement)"
status: historical
type: handoff
date: 2026-08-02
session: 146
milestone: 18
milestone_status: in-progress
milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_146 — Milestone 18 · Increment 0 (M18.0 — planning refinement)

## What shipped

Planning-only session per the M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 / M15.0
/ M16.0 / M17.0 precedent. Full memo
expansion + all **seven** §5 load-
bearing decisions resolved at open.

**§5.a → Option O confirmed** —
non-accounting target. Milestone
name: **"Demo Store Simulation +
Pilot Validation Readiness."** First
non-accounting milestone since M12;
validation infrastructure for
founder-led pilot testing with
experienced independent-dealer
operators.

**§5.b–§5.g all confirmed as-
recommended.** Streak extends to
**77 planning-time as-recommended
M5.1 → M18.0** across **nine
consecutive milestones now** (M10 +
M11 + M12 + M13 + M14 + M15 + M16 +
M17 + M18). Historical §5 counts
have been 6 per milestone; M18 at
seven reflects the mixed
architecture / ownership /
representation / safety scope.

**Backend baseline unchanged:**
4,363 pass, 1 skipped, 0 fail
(verified at session open).
**Frontend Vitest baseline
unchanged:** 140 pass. Migrations
`0043`–`0046` (unchanged).
Tenancy carriers 49 (unchanged
— TesterFeedback lands at M18.1).
DRF admin surface 107 (unchanged
— feedback POST endpoint lands
at M18.5). Frontend operator
routes 20 (unchanged — M18
introduces zero new operator
routes per §5.f + Q7). Permission
classes 7 (unchanged). Celery-
beat task families 10 (unchanged
— M18 has no beat entry).

## Load-bearing decisions confirmed at M18.0 open

Seven decisions per M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 /
M15.0 / M16.0 / M17.0 precedent.
All confirmed as-recommended.

**§5.a — Milestone target
selection.** Option O — non-
accounting target. Milestone
name: "Demo Store Simulation +
Pilot Validation Readiness."
The platform now has broad
verified capability surface
through M17; another isolated
accounting extension has
diminishing marginal value
without validation that the
existing capability surface
actually resonates with real
independent-dealer operators.
Testers Chris already knows in
the car business may become the
first pilot customers.

**§5.b — Demo architecture.**
Option A —
`Dealership.is_demo
BooleanField(default=False)` +
`Dealership.demo_archetype
CharField(choices=DEMO_ARCHETYPE_CHOICES,
blank=True)` with fixed vocab
(`retail_subprime`,
`floor_planned`, `bhph`, blank).
Preserves the "one authoritative
tenancy model" invariant. One
additive migration (`0047`).

**§5.c — Seed/reset ownership.**
Option A — new
`services/demo_store/` package
+ one management command
`python manage.py demo_store
{create|reset|list|export_feedback}
--archetype <name> --slug
<name>`. Belt-and-suspenders
guard:
`NonDemoResetError(RuntimeError)`
+ `assert dealership.is_demo`
at top of every write verb.

**§5.d — Scenario representation.**
Option A — Python builder
classes in
`services/demo_store/archetypes/{retail_subprime,floor_planned,bhph}.py`.
Each archetype exposes a
`build(dealership) ->
ScenarioSummary` atomic verb.
Scenarios are code, versioned
like code.

**§5.e — Tester feedback capture.**
Option A — new `TesterFeedback`
model + one POST endpoint +
management-command exporter.
Tenancy carrier 49 → **50**.
Endpoint count 107 → **108** at
M18.5.

**§5.f — UI correction boundary.**
Option A — explicit criteria:
only workflow-blocking or
materially misleading defects
belong in M18; everything else
recorded via §5.e for a later
UX-polish milestone. Every M18.x
UI correction records the
specific blocking scenario in
its commit message + M18
retrospective §4 deviations.

**§5.g — Data realism and
safety.** Option A —
unmistakably synthetic:
`DEMO`-prefixed VINs; fixed
pseudonym roster; `555-01xx`
NANP fiction phones;
`@demo.dealer-ai.example`
emails (IANA-reserved TLD);
SSN / payment credentials never
populated. **Outbound-send
guard**: enumerate existing
send-boundary verbs at M18.1
planning + wrap each with
early `if dealership.is_demo:
log_and_noop()`.

## Streak

**77 planning-time as-recommended
M5.1 → M18.0.** Nine consecutive
milestones now (M10 + M11 + M12
+ M13 + M14 + M15 + M16 + M17 +
M18) with every §5 decision
confirmed as-recommended at
planning-time open.

## What's next: SESSION_147 M18.1 backend substrate

Per `MILESTONE_18_PLANNING.md`
§7 M18.1:

### Schema

- Migration `0047_m181_dealership_demo_flags.py`
  adding `Dealership.is_demo`
  BooleanField(default=False) +
  `Dealership.demo_archetype`
  CharField(choices=CHOICES,
  blank=True, max_length=32) per
  §5.b Option A. Additive-only.
- New model constants +
  `DEMO_ARCHETYPE_CHOICES` in
  `models.py`.
- Migration `0048_m181_tester_
  feedback.py` adding
  `TesterFeedback` model per §5.e
  Option A.
- Register `TesterFeedback` in
  `_TENANT_CARRIER_MODEL_NAMES`.
  Count 49 → 50.

### Service package

- New `services/demo_store/`
  package:
  - `errors.py` —
    `NonDemoResetError(RuntimeError)`.
  - `synthetic_names.py` — fixed
    pseudonym roster.
  - `synthetic_data.py` — VIN /
    phone / email helpers.
  - `scenario_summary.py` —
    `ScenarioSummary` frozen
    dataclass.
  - `registry.py` —
    `create_demo_store`,
    `reset_demo_store`,
    `list_demo_stores`. All
    atomic. Belt-and-suspenders
    guard on reset.
  - `archetypes/__init__.py`
    dispatcher.
  - `archetypes/base.py` ABC.
  - Archetype-module STUBS only
    at M18.1 (raise
    `NotImplementedError` until
    M18.2-M18.4).

### Management command

- `dealer_ai/management/commands/demo_store.py`
  with subcommands `create` /
  `reset` / `list` /
  `export_feedback`.

### Outbound-send-boundary guards

- **First task at M18.1 open:**
  enumerate every existing verb
  that sends outbound (email,
  SMS, API call to lender /
  bureau / integrator /
  accounting-provider). Wrap
  each with early
  `if dealership.is_demo:
  log_and_noop()`.
- Preliminary list (verify at
  M18.1 open): M11.4 follow-up
  cadence dispatch; M12.5 BHPH
  collection dispatch; M10 F&I
  lender-portal adapters; M10
  compliance / bureau pulls;
  M6/M11 chat outbound routing;
  M9 test-drive delivery
  reminders.

### Test helper

- `_auth_helpers.make_demo_dealership(archetype,
  slug)` companion to
  `make_dealership`.

### Tests

**~30-40 focused tests** in new
`tests/test_m181_demo_store_
substrate.py` per §7 M18.1
including tenancy carrier count
49 → **50** (`>=`) + permission-
class set equality (zero-drift
streak extends to ten
consecutive milestones) +
endpoint count 107 (unchanged
at M18.1 — feedback POST lands
at M18.5).

### Non-goals for M18.1

- ❌ No archetype scenario
  construction (M18.2-M18.4).
- ❌ No feedback POST endpoint
  (M18.5).
- ❌ No frontend changes.
- ❌ No new Celery-beat
  entries.
- ❌ No new post-LLM scrub
  stages.

### Backend baseline target

**4,363 → ~4,393-4,403 pass**
(+30-40 tests, 0 regressions).
Frontend Vitest: 140 (unchanged).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
   (this session's expansion
   target)
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
   §6 + §8 + §9 (standing
   question resolved at M18.0)
7. `docs/CAPABILITY_MATRIX.md` §7r
8. `docs/research/INDEPENDENT_DEALER_PIVOT.md`
   (archetype persona shape)
9. `docs/research/SALES_DEPARTMENT_MAPPING.md`
   +
   `docs/research/BHPH_OPERATIONS_MAPPING.md`
   +
   `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
   +
   `docs/research/RECON_MAPPING.md`
   (per-archetype operational
   patterns)
