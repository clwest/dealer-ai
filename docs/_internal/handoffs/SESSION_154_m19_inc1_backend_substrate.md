---
title: "SESSION_154 handoff — Milestone 19 · Increment 1 (M19.1 — Backend substrate)"
status: historical
type: handoff
date: 2026-08-02
session: 154
milestone: 19
milestone_status: in-progress
milestone_name: "Founding Dealer Pilot Onboarding"
increment: 1
increment_status: shipped
---

# SESSION_154 — Milestone 19 · Increment 1 (M19.1 — Backend substrate)

## What shipped

Single backend increment per
`MILESTONE_19_PLANNING.md` §7 M19.1. All
M19 substrate — schema + service package
+ guards + outbound-guard refactor + test
helper.

**Two §0.a M19.1 implementation-time
decisions recorded** (do not count against
planning-time streak per M10 §9). Both
surfaced in the M19.0 planning memo and
resolved at M19.1 open with a defense +
counter-recommendation from the assistant
that the user confirmed:

### §0.a M19.1 decision 1 — `PilotProspect` tenancy posture

**Decision.** `PilotProspect` remains a
**pre-tenant operator record** and is NOT
registered in `_TENANT_CARRIER_MODEL_NAMES`.
Instead, two optional `SET_NULL` FKs
(`source_demo_dealership`,
`converted_dealership`) preserve the
conversion audit trail without forcing
tenant scope.

**Why the M19.0 planning recommendation
was reversed.** The tenancy autofill
pre_save signal calls
`instance.dealership = get_default_dealership()`.
That fails hard if the model has no
`dealership` FK — which `PilotProspect` by
design does not have. Registering a model
without the FK would break the autofill
contract on every insert. Correct
architecture: keep `PilotProspect`
pre-tenant, add two nullable audit-trail
FKs. `PilotOnboardingChecklist` and
`PilotOnboardingStep` do carry
`dealership` FKs so they register as
tenancy carriers.

**Tenancy carrier count 50 → 52** (added
`PilotOnboardingChecklist` +
`PilotOnboardingStep`; NOT `PilotProspect`).

### §0.a M19.1 decision 2 — outbound-guard policy field

**Decision.** Add
`Dealership.outbound_enabled =
BooleanField(default=False)`. Refactor the
outbound guard from
`suppress_if_demo(is_demo)` to
`suppress_if_outbound_disabled(outbound_enabled)`.
Keep `suppress_if_demo` as a deprecated
alias that delegates to
`suppress_if_outbound_disabled` and emits
`DeprecationWarning`. Preserve
`is_demo_dealership()` as a diagnostic
helper. Add `is_pilot_dealership()` +
`is_outbound_enabled()` as companion
diagnostics.

**Why the M19.0 planning recommendation
was upgraded from a rename.** The naive
rename to `suppress_if_synthetic` was
correct for the M19 scope but wouldn't
scale: any future live production
dealership needs its own suppression
switch until the operator confirms
outbound is safe. A policy field on the
Dealership row provides the durable
contract:

- **Orthogonality.** Tenant-type flags
  (`is_demo`, `is_pilot`) describe **what
  the record is**. The policy field
  (`outbound_enabled`) describes **what
  the platform is allowed to do on the
  tenant's behalf**. Conflating them
  couples policy to identity.
- **Auditability.** `outbound_enabled` at
  any point-in-time answers "was outbound
  enabled when X happened?" — a question
  the identity-based predicate couldn't
  answer cleanly.
- **Per-tenant control.** A pilot that
  needs controlled outbound enablement
  (e.g. per-verb code review before flip)
  is a single-column update. No tenant-
  type reclassification required.
- **Live-dealer default.** New live
  Dealership rows default
  `outbound_enabled=False` too. Operator
  explicitly flips to `True` at go-live.
  Fail-safe by construction.

**Backward compatibility.** Existing
callers of `suppress_if_demo` continue to
work via the deprecation shim. The
canonical guard for adapters at M19.1+ is
`suppress_if_outbound_disabled`.

## Delivered

**Migration `0048_m191_pilot_substrate.py`**
(auto-generated + applied cleanly; bundled
per M13.1 / M18.1 precedent):

- `AddField Dealership.is_pilot`
  BooleanField(default=False).
- `AddField Dealership.outbound_enabled`
  BooleanField(default=False).
- `AddField Dealership.terminated_at`
  DateTimeField(null=True, blank=True).
- `AddField Dealership.termination_reason`
  TextField(blank=True, default="").
- `CreateModel PilotProspect` per §5.b
  field set + two optional
  `source_demo_dealership` /
  `converted_dealership` FKs
  (SET_NULL).
- `CreateModel PilotOnboardingChecklist`
  (OneToOneField Dealership CASCADE,
  is_ready BooleanField).
- `CreateModel PilotOnboardingStep`
  (dealership FK CASCADE, checklist FK
  CASCADE, step_slug CharField choices,
  completed_at DateTimeField null,
  completed_by FK User SET_NULL, notes
  TextField blank).
  `Meta.constraints` adds a unique
  constraint on `(checklist,
  step_slug)`.

**Vocab constants in `models.py`:**

- `PILOT_PROSPECT_STATE_PROSPECT` /
  `_QUALIFIED` / `_CONVERTED` /
  `_DECLINED` +
  `PILOT_PROSPECT_STATE_CHOICES`.
- `PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED`
  / `_PROFILE_CONFIGURED` /
  `_OWNER_USER_ADDED` /
  `_STAFF_USERS_ADDED` /
  `_INVENTORY_IMPORTED` /
  `_CAPABILITIES_ENABLED` /
  `_READINESS_CONFIRMED` +
  `PILOT_ONBOARDING_STEP_CHOICES` +
  `PILOT_ONBOARDING_STEP_ORDER` tuple.
- `PILOT_TERMINATION_MODE_ARCHIVE` /
  `_CLEANUP` +
  `PILOT_TERMINATION_MODE_CHOICES`.

**New service package
`services/pilot_onboarding/`** (six
modules, ~835 lines):

- `errors.py` —
  `PilotAlreadyExistsError(ValueError)`
  (409), `NonPilotTerminationError(RuntimeError)`
  (500), `PilotReadinessNotConfirmedError(ValueError)`
  (409).
- `registry.py` — `create_pilot_dealership`
  atomic (creates Dealership +
  `outbound_enabled=False` + seeds COA +
  attaches owner UserDealershipRole +
  populates DealerOnboardingProfile +
  fires PilotOnboardingChecklist with
  `dealership_created` step complete).
  `list_pilot_dealerships` pure read
  (`is_pilot=True,
  terminated_at__isnull=True`).
  `terminate_pilot` belt-and-suspenders
  guarded — raises
  `NonPilotTerminationError` +
  `assert dealership.is_pilot`.
  `mode='archive'` preserves child rows;
  `mode='cleanup'` cascades reverse-order
  per M18.2 pattern + deletes pilot-owned
  Users.
- `prospects.py` — `create_prospect`,
  `advance_prospect_state` state machine
  (prospect → {qualified, declined};
  qualified → {converted, declined};
  terminal converted / declined),
  `list_prospects` recent-first.
  `InvalidProspectTransitionError` +
  `ConvertedRequiresDealershipError`
  (both 409).
- `checklist.py` — `advance_step` atomic
  with `UnknownChecklistStepError` (400)
  + `ChecklistStepAlreadyCompletedError`
  (409) + readiness precondition guard
  (`readiness_confirmed` refuses if any
  prior step incomplete). Flips
  `is_ready=True` when
  `readiness_confirmed` completes.
  `is_pilot_ready(dealership)` pure
  predicate.
- `inventory_import.py` —
  `PilotInventoryImportResult` frozen
  dataclass return contract +
  `import_pilot_inventory` stub raising
  `NotImplementedError` (ships fully at
  M19.2).
- `__init__.py` — public API `__all__`
  with 18 exported symbols.

**Register `PilotOnboardingChecklist` +
`PilotOnboardingStep`** in
`_TENANT_CARRIER_MODEL_NAMES` in
`services/tenancy.py`. Count 50 → **52**.
(`PilotProspect` NOT registered per §0.a
decision 1.)

**Outbound guard refactor**
(`services/demo_store/outbound_guard.py`):

- New primary guard
  `suppress_if_outbound_disabled(dealership,
  *, verb_name, **log_extra) ->
  Optional[SuppressedOutbound]`. Returns
  a marker if
  `dealership.outbound_enabled=False`
  OR `dealership is None`.
- New diagnostics
  `is_outbound_enabled(dealership)` +
  `is_pilot_dealership(dealership)`.
- Preserved `is_demo_dealership()`
  diagnostic (still returns True iff
  `is_demo=True`).
- Deprecated alias `suppress_if_demo`
  delegates to
  `suppress_if_outbound_disabled` +
  emits `DeprecationWarning`.
- M18.1 outbound-egress scanner
  contract unchanged — still enforces
  guard adoption on every future
  `services/` egress verb, with the
  same LLM allowlist.

**Test helper**
`tests/_auth_helpers.py::make_pilot_dealership(slug,
name=None, outbound_enabled=False)`
companion to `make_demo_dealership`.

**58 focused tests** in new
`tests/test_m191_pilot_substrate.py`:

- Vocab exact-set equality (5):
  `PilotProspectStateVocabTests` (2),
  `PilotOnboardingStepVocabTests` (3 —
  including step_order matches choices),
  `PilotTerminationModeVocabTests`
  implicit.
- Dealership pilot fields (3):
  `DealershipPilotFieldsTests` — new
  Dealership defaults; existing rows
  unchanged; migration-seeded default.
- Tenancy carrier registration (3):
  `M191TenancyCarrierTests` — checklist
  + step registered; `PilotProspect`
  NOT registered; count `>=` 52.
- `PilotProspect` model (4): defaults,
  `clean()` invariants, SET_NULL FKs.
- Checklist + Step models (3): OneToOne
  enforcement via IntegrityError,
  unique constraint on
  `(checklist, step_slug)`, cross-tenant
  `clean()` guard.
- `create_pilot_dealership` (4):
  happy path validates all substrate;
  slug collision guards vs existing
  pilot AND existing demo.
- `list_pilot_dealerships` (2):
  filters `is_pilot=True`; excludes
  terminated.
- `terminate_pilot` (5):
  `NonPilotTerminationError` on real +
  demo; archive preserves; cleanup
  cascades child rows; unknown mode
  raises `ValueError`.
- Checklist `advance_step` (6): happy
  path; unknown step raises; re-advance
  immutability; readiness precondition
  refuses out-of-order; readiness after
  prior steps.
- `is_pilot_ready` (3): False for
  non-pilot; False before advance;
  True after full sequence.
- Prospect verbs (7): defaults; all
  legal transitions; direct
  prospect→converted refused;
  qualified→converted with/without
  dealership FK; terminal states have
  no outgoing transitions; list
  recent-first.
- `PilotInventoryImportResult` stub
  (2): raises NotImplementedError;
  dataclass defaults empty tuples.
- Outbound guard (5):
  `IsOutboundEnabledTests` (3),
  `IsPilotDealershipTests` (2 —
  diagnostic).
- `suppress_if_outbound_disabled` (3):
  None marker; disabled marker;
  enabled None; demo suppressed by
  default.
- `suppress_if_demo` deprecation (2):
  delegates + emits DeprecationWarning.
- Permission-class zero-drift set
  equality (1):
  `M191PermissionClassZeroDriftTests`
  — streak of fifteen consecutive
  milestones (M10 → M19.1).
- Endpoint count unchanged (1):
  `M191EndpointCountTests` — `>=` 108.

**M18.1 test file updated** —
`SuppressIfDemoTests` in
`tests/test_m181_demo_store_substrate.py`
rewritten to reflect the M19.1 semantic
shift: `suppress_if_demo` now delegates
to `suppress_if_outbound_disabled`, so a
None dealership or `outbound_enabled=False`
suppresses by design (fail-safe). Two
prior test bodies encoding the old
identity-based semantics were replaced
with three tests covering the new policy-
field semantics.

## Baseline delta

- **Backend:** 4,538 → **4,597 pass**,
  1 skipped, 0 fail. **+59 tests, 0
  regressions.** Exceeded 40-50 planning
  target by 9 due to the deprecation-
  warning coverage + tenant-type
  diagnostic split + M18.1
  `SuppressIfDemoTests` gaining one net
  test case in the policy-field rewrite.
- Migrations 0043-0047 → **0043-0048**
  (+1 at M19.1).
- Tenancy carriers 50 → **52** (added
  `PilotOnboardingChecklist` +
  `PilotOnboardingStep`; NOT
  `PilotProspect` per §0.a decision 1).
- DRF admin surface **108** (unchanged
  — 4 new endpoints land at M19.3).
- Frontend operator routes **20**
  (unchanged — M19 introduces zero new
  routes; M19.4 extends existing in
  place).
- Permission classes **7 actual** —
  **zero-drift streak now fifteen
  consecutive milestones** (M10 →
  M19.1).
- Celery-beat task families **10**
  (unchanged — M19 has no beat
  entry).
- Frontend Vitest **140** (unchanged
  — no frontend at M19.1).

## Streak update

**85 planning-time as-recommended M5.1
→ M19.0** (unchanged — M19.1 is
implementation-time work per M10 §9).
**Two §0.a M19.1 implementation-time
decisions recorded** (PilotProspect
tenancy posture + outbound-guard policy
field). Both defended in this handoff.

## What's next: SESSION_155 M19.2 inventory import

Per `MILESTONE_19_PLANNING.md` §7 M19.2:

- `services/pilot_onboarding/inventory_import.py`
  — replace the stub with the full
  atomic `import_pilot_inventory`
  implementation.
- CSV parse + row validation +
  `Vehicle.objects.bulk_create()` +
  rejected-row surfacing on
  `PilotInventoryImportResult`.
- Enforce M13/M14 unit-price
  invariants + M18.1 outbound guard
  where applicable.
- Field mapping doc
  `docs/PILOT_INVENTORY_TEMPLATE.md`
  covering the CSV schema, required
  columns, and archetype-neutral
  intake for an indie/franchise
  starter fleet.
- Focused tests (~20-25 target) in
  `tests/test_m192_pilot_inventory_import.py`.

**Backend baseline target at M19.2
close:** ~4,596 → ~4,616-4,621 pass
(+20-25 tests).

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_153_m19_inc0_planning.md`
7. `docs/CAPABILITY_MATRIX.md` §7s
8. `docs/research/INDEPENDENT_DEALER_PIVOT.md`
9. `backend/dealer_ai/services/pilot_onboarding/`
   (substrate freshly shipped)
10. `backend/dealer_ai/services/demo_store/outbound_guard.py`
    (M19.1 policy-field refactor)
11. `backend/dealer_ai/tests/test_m191_pilot_substrate.py`
    (test coverage document)
