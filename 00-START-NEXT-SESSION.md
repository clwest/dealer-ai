---
state: active
date: 2026-08-02
last_session_shipped: SESSION_146
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
milestone_18_status: in-progress
next_session: SESSION_147
next_milestone: 18
next_milestone_name: "Demo Store Simulation + Pilot Validation Readiness"
next_increment: 1
next_increment_name: "M18.1 — Substrate: schema + service package + guards + TesterFeedback + send-boundary enumeration"
---

# Next session — SESSION_147 · Milestone 18 · Increment 1 (M18.1 — Substrate)

> **SESSION_146 shipped M18.0 —**
> planning refinement + all seven §5
> load-bearing decisions resolved at
> open. **§5.a Option O confirmed** —
> non-accounting target. Milestone
> name: **"Demo Store Simulation +
> Pilot Validation Readiness."** First
> non-accounting milestone since M12;
> validation infrastructure for
> founder-led pilot testing.
>
> **§5.b–§5.g all confirmed as-
> recommended.** Streak extends to
> **77 planning-time as-recommended
> M5.1 → M18.0** across **nine
> consecutive milestones now** (M10 +
> M11 + M12 + M13 + M14 + M15 + M16 +
> M17 + M18). Historical §5 counts
> have been 6; M18 at seven reflects
> the mixed architecture / ownership /
> representation / safety scope.
>
> **Backend baseline: 4,363 pass**, 1
> skipped, 0 fail (unchanged —
> planning-only). **Frontend Vitest
> baseline: 140 pass** (unchanged).
> Migrations `0043`–`0046`
> (unchanged). Tenancy carriers 49
> (unchanged — `TesterFeedback` lands
> at M18.1). DRF admin surface 107
> (unchanged — feedback POST endpoint
> lands at M18.5). Frontend operator
> routes 20 (unchanged — M18 adds
> **zero new operator routes** per
> §5.f + Q7). Permission classes 7
> (unchanged). Celery-beat task
> families 10 (unchanged).
>
> **SESSION_147 opens M18.1 —
> substrate.** Schema (two additive
> migrations) + service package
> (`services/demo_store/`) + belt-
> and-suspenders guards + `TesterFeedback`
> model + outbound-send-boundary
> enumeration + guards. Single
> backend increment. No frontend.

## First thing SESSION_147 must do

### 1. Enumerate the outbound-send-boundary verbs

Per `MILESTONE_18_PLANNING.md` §5.g
Option A + §7 M18.1, the first
substantive M18.1 task is producing
the **complete** list of existing
verbs that send outbound (email,
SMS, API call to lender / bureau /
integrator / accounting-provider).
Preliminary set from planning:

- **M11.4 follow-up cadence
  dispatch** (email + SMS).
- **M12.5 BHPH collection contact
  dispatch** (email + SMS).
- **M10 F&I lender-portal adapters**
  — credit-application dispatch.
- **M10 compliance / bureau pulls**
  — credit-bureau pull adapters.
- **M6 / M11 chat outbound routing**
  — assistant messages to email /
  SMS when operator inbox offline.
- **M9 test-drive delivery
  reminders**.

Verify the list is complete by
grepping for `send_mail`,
`send_sms`, `requests.post`,
`urllib.request` in
`services/` + `management/commands/`.
Add any additional verbs to the
guard set.

Each guard is an early check at the
top of the verb:

```python
if dealership.is_demo:
    logger.info(
        "demo-store outbound suppressed",
        extra={"verb": <name>,
               "dealership_slug": dealership.slug},
    )
    return  # or return a no-op sentinel matching the verb's contract
```

### 2. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top should
  be the M18.0 planning commit.
- `python3 manage.py test dealer_ai`
  → **4,363 pass, 1 skipped, 0 fail**.
- `cd frontend && npm test` → **140
  pass**.
- `python3 manage.py check` clean.
- `python3 manage.py makemigrations
  --check --dry-run` → "No changes
  detected."
- `cd frontend && npx tsc --noEmit`
  clean.
- `redis-cli ping` → `PONG`.

## What M18.1 delivers

Per `MILESTONE_18_PLANNING.md` §7
M18.1:

### Schema

- **Migration
  `0047_m181_dealership_demo_flags.py`**
  adding:
  - `Dealership.is_demo`
    `BooleanField(default=False)`.
  - `Dealership.demo_archetype`
    `CharField(choices=DEMO_ARCHETYPE_CHOICES,
    blank=True, max_length=32)`.
  - Per §5.b Option A. Additive-only,
    zero data migration.
- **Vocab constants in `models.py`**:
  `DEMO_ARCHETYPE_RETAIL_SUBPRIME` +
  `DEMO_ARCHETYPE_FLOOR_PLANNED` +
  `DEMO_ARCHETYPE_BHPH` +
  `DEMO_ARCHETYPE_CHOICES` tuple.
- **Migration
  `0048_m181_tester_feedback.py`**
  adding `TesterFeedback` model per
  §5.e Option A:
  - `dealership` FK CASCADE.
  - `tester_name` CharField(64).
  - `scenario_slug` CharField(64).
  - `category` CharField(32,
    choices=TESTER_FEEDBACK_CATEGORY_CHOICES).
  - `note` TextField.
  - `referenced_route`
    CharField(255, blank=True).
  - `created_at` auto_now_add.
- **`TESTER_FEEDBACK_CATEGORY_CHOICES`**
  vocab: `confusion` / `bug` /
  `feature_request` /
  `value_statement` /
  `willingness_to_pay`.
- **Register `TesterFeedback`** in
  `_TENANT_CARRIER_MODEL_NAMES` in
  `services/tenancy.py`. Count 49 →
  **50**.

### Service package

- **New `services/demo_store/`
  package** per §5.c Option A:
  - `__init__.py` with `__all__`
    exports.
  - `errors.py` —
    `NonDemoResetError(RuntimeError)`.
  - `synthetic_names.py` — fixed
    pseudonym roster (~40
    pseudonyms). Fixed vocab;
    exact-set assertion at test
    time.
  - `synthetic_data.py` — helpers:
    - `synthetic_vin(archetype:
      str, index: int) -> str` —
      17-char string prefixed
      `DEMO<archetype-code>` +
      11 hex chars.
    - `synthetic_phone(index: int)
      -> str` — `555-01xx` NANP.
    - `synthetic_email(name: str)
      -> str` —
      `<name>@demo.dealer-ai.example`.
  - `scenario_summary.py` —
    `ScenarioSummary` frozen
    dataclass (fields:
    `archetype`, `dealership_id`,
    `dealership_slug`,
    `seeded_stock_numbers`,
    `seeded_user_usernames`,
    `seeded_scenario_slugs`,
    `notes`).
  - `registry.py`:
    - `create_demo_store(*, slug,
      archetype, name=None,
      actor=None) -> Dealership`
      — atomic; delegates to
      archetype builder.
    - `reset_demo_store(*,
      dealership, actor=None) ->
      Dealership` — atomic;
      raises `NonDemoResetError`
      if `is_demo=False`;
      `assert dealership.is_demo`
      at write-path top.
    - `list_demo_stores() ->
      list[Dealership]` — returns
      only `is_demo=True` rows.
  - `archetypes/__init__.py`
    dispatcher mapping archetype
    string → builder module.
  - `archetypes/base.py`
    `ArchetypeBuilder` ABC with
    `build(dealership) ->
    ScenarioSummary` abstract
    method.
  - **Stubs only at M18.1**:
    `archetypes/retail_subprime.py`,
    `archetypes/floor_planned.py`,
    `archetypes/bhph.py`. Each
    raises `NotImplementedError`
    until M18.2-M18.4 fill them
    in.

### Management command

- **`dealer_ai/management/commands/demo_store.py`**
  with subcommands:
  - `demo_store create --slug
    <name> --archetype <name>
    [--display-name <name>]` —
    creates a fresh demo
    dealership + runs the
    archetype builder.
  - `demo_store reset --slug
    <name>` — resets to
    canonical starting state.
  - `demo_store list` — lists
    all demo dealerships.
  - `demo_store export_feedback
    --dealership <slug> [--since
    <date>] [--out <path>]` —
    CSV export.

### Outbound-send-boundary guards

- Enumerate at open (§1 above).
- Wrap each with early
  `if dealership.is_demo:
  log_and_noop()` check.
- New logger name:
  `dealer_ai.demo_store.outbound`
  for suppressed-outbound log
  lines.

### Test helper

- Extend `tests/_auth_helpers.py`
  with
  `make_demo_dealership(archetype:
  str, slug: str, name: str |
  None = None) -> Dealership` —
  wraps `make_dealership` + sets
  `is_demo=True` +
  `demo_archetype=<value>`.

### Tests

**~30-40 focused tests** in new
`tests/test_m181_demo_store_
substrate.py`:

- `Dealership.is_demo` +
  `demo_archetype` defaults on
  existing rows (both fields
  default per new migration).
- `DEMO_ARCHETYPE_CHOICES`
  exact-set equality (fixed-
  vocab lesson).
- `TESTER_FEEDBACK_CATEGORY_CHOICES`
  exact-set equality.
- `TesterFeedback` model
  contract + tenancy autofill.
- `create_demo_store` happy
  path.
- `create_demo_store` slug
  collision handling.
- `reset_demo_store` happy
  path (with a stub archetype
  builder or an inline one for
  test isolation).
- `reset_demo_store` raises
  `NonDemoResetError` when
  `Dealership.is_demo=False`.
- `assert dealership.is_demo`
  fires when write-path guard
  bypassed via mock
  (`RuntimeError` shape).
- `list_demo_stores` returns
  only `is_demo=True` rows.
- `synthetic_vin` produces
  17-char string prefixed
  `DEMO<archetype-code>`.
- `synthetic_vin` deterministic
  for (archetype, index) pair.
- `synthetic_phone` produces
  `555-01xx` NANP format.
- `synthetic_email` produces
  `@demo.dealer-ai.example`
  suffix.
- `synthetic_names` roster is
  fixed vocab (exact-set
  assertion).
- **Per-verb outbound-send-
  boundary guards** — one test
  per enumerated verb asserting
  demo dealerships suppress and
  non-demo dealerships proceed.
- Tenancy carrier count 49 →
  **50** (`>=` assertion per
  lesson).
- Permission-class set equality
  unchanged (zero-drift streak
  ten consecutive milestones).
- Endpoint count 107 (unchanged
  at M18.1 — the `TesterFeedback`
  POST endpoint lands at M18.5).

### Non-goals for M18.1

- ❌ No archetype scenario
  construction (M18.2-M18.4).
- ❌ No `TesterFeedback` POST
  endpoint (M18.5).
- ❌ No CSV export
  implementation body (M18.5).
- ❌ No frontend changes.
- ❌ No new Celery-beat
  entries.
- ❌ No new post-LLM scrub
  stages.

## Backend baseline target

**4,363 → ~4,393-4,403 pass**
(+30-40 tests, 0 regressions).
Frontend Vitest: 140 (unchanged
— M18.5 delta only if a feedback
capture form component lands per
§5.f evidence).

## Explicit non-goals for SESSION_147

- ❌ Do NOT ship M18.2 retail /
  subprime archetype pack.
- ❌ Do NOT modify M1-M17
  business logic.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_147 with (a)
enumerating the outbound-send-
boundary verbs (§1 above), (b)
starting-state verification, (c)
building schema + service package
+ guards + `TesterFeedback` +
outbound-send guards + tests per
§7 M18.1. Ship the M18.1 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_18_PLANNING.md`
   (active memo)
6. `docs/roadmap/MILESTONE_17_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_146_m18_inc0_planning.md`
   (this session's handoff)
8. `docs/CAPABILITY_MATRIX.md` §7r

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_146 — M18.0 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations `0001`–`0046`.
  Test baseline: **4,363 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on
  `:5173`. `tsc --noEmit` + `vite
  build` clean. **Vitest baseline:
  140 pass**.
- **Frontend (prod):** NONE.
- **Async runtime:** Celery 5.5.3 +
  Redis 6.4.0 + `django-celery-beat`
  2.8.1 DatabaseScheduler. **10
  scheduled task families
  registered**. Next open slot for
  a future detector is 12:00.
- **Milestones shipped:** M1 → M17.
  M18 in progress: M18.0 planning
  shipped at SESSION_146. M18.1
  substrate next (SESSION_147).
- **DRF admin surface:** **107**
  endpoints. Grows to 108 at M18.5
  (feedback POST).
- **Frontend operator routes:**
  **20** — remains unchanged
  through M18 per §5.f + Q7.
- **Public endpoints:** +1 M6.5
  showroom (unchanged).
- **Service surface:** complete
  `services/f_and_i/` (M10) + five
  M11 packages + seven M12
  packages + `services/accounting/`
  (seven modules). **New at
  M18.1**: `services/demo_store/`
  package.
- **Frontend accounting surface:**
  `frontend/src/lib/accountingApi.ts`
  with 8 fetchers + 2 mutators +
  four page components +
  `TrialBalanceDatePicker`
  component.
- **Tenancy carriers:** **49**.
  Grows to 50 at M18.1
  (`TesterFeedback`).
- **Permission classes:** **7
  actual** — zero-drift streak
  nine consecutive milestones
  (M10 → M17). Extends to ten
  after M18.1 as no new class
  ships.
- **`Vehicle.is_available`:**
  unchanged.
- **AI safety stack:** 17 scrub
  stages (unchanged — M18 has no
  LLM path).
- **Deterministic rules:**
  unchanged.
- **Milestone 18 status:** M18.0
  planning SHIPPED (SESSION_146).
  M18.1 substrate next
  (SESSION_147). M18.2-M18.4
  archetype packs
  (SESSION_148-150). M18.5 briefs
  + feedback endpoint
  (SESSION_151). M18.6 close-out
  (SESSION_152).
