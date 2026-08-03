---
state: active
date: 2026-08-02
last_session_shipped: SESSION_154
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
next_session: SESSION_155
next_milestone: 19
next_milestone_name: "Founding Dealer Pilot Onboarding"
next_increment: 2
next_increment_name: "M19.2 — Inventory import implementation + CSV schema doc"
---

# Next session — SESSION_155 · Milestone 19 · Increment 2 (M19.2 — Inventory import)

> **SESSION_154 shipped M19.1 —**
> backend substrate. Migration
> `0048_m191_pilot_substrate.py`
> applied cleanly. New
> `services/pilot_onboarding/`
> package (six modules, ~835
> lines) delivered. Outbound guard
> refactored from identity-based
> (`is_demo`) to policy-field
> (`outbound_enabled`); backward
> compatibility preserved via
> deprecated `suppress_if_demo`
> alias. Two §0.a M19.1
> implementation-time decisions
> recorded — `PilotProspect` stays
> pre-tenant (not a tenancy
> carrier) + `Dealership.outbound_enabled`
> policy field added.
>
> **Backend baseline: 4,538 → 4,597
> pass** (+59 tests, 0
> regressions). **Frontend Vitest:
> 140 pass** (unchanged).
> Migrations `0043`–`0048`.
> Tenancy carriers 50 → **52**
> (added `PilotOnboardingChecklist`
> + `PilotOnboardingStep`; NOT
> `PilotProspect`). DRF admin
> surface 108 (unchanged — 4
> endpoints land at M19.3).
> Frontend operator routes 20
> (unchanged — M19.4 extends
> existing admin route). Permission
> classes 7 (unchanged — zero-drift
> streak now **fifteen consecutive
> milestones** M10 → M19.1).
> Celery-beat task families 10
> (unchanged).
>
> **SESSION_155 opens M19.2 —
> pilot inventory import.** Full
> body for `import_pilot_inventory`
> replacing the M19.1 stub. CSV
> parse + row validation +
> `bulk_create` + rejected-row
> surfacing. New doc
> `docs/PILOT_INVENTORY_TEMPLATE.md`
> covering the CSV schema. Single
> backend increment; ~20-25
> focused tests.

## First thing SESSION_155 must do

### 1. Verify starting state

- `git status` — clean.
- `git log --oneline -5` — top
  should be the M19.1 substrate
  commit.
- `python3 manage.py test dealer_ai`
  → **4,597 pass, 1 skipped, 0
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

### 2. Surface any §0.a M19.2 micro-decisions

Expected candidates:

1. **CSV column set at v1.** The
   `PILOT_INVENTORY_TEMPLATE.md`
   authoritative schema needs a
   fixed column list. Options:
   (a) mirror the M18.2
   retail-subprime archetype
   builder fields (~15 columns),
   (b) narrower "starter fleet"
   set (10 columns: stock number,
   VIN, year, make, model, trim,
   miles, price, condition,
   floor-plan status),
   (c) archetype-parameterized
   (M18 archetype → column set).
   Recommendation lands at M19.2
   open based on Chris's actual
   pilot-conversion friction
   points from the demo runs.
2. **Rejected-row policy.**
   Whether `import_pilot_inventory`
   returns partial success
   (accepted rows commit; rejected
   surfaced) or all-or-nothing
   (any rejection rolls back the
   whole import). Recommendation:
   partial success is
   operationally correct for an
   onboarding-friction reduction
   surface — Chris resolves
   rejected rows separately.

Present both briefly at open;
expect confirm-as-recommended per
the 85-milestone streak posture.
Record as §0.a M19.2 amendments.

## What M19.2 delivers

Per `MILESTONE_19_PLANNING.md` §7
M19.2:

### Service body

- Replace the M19.1 `NotImplementedError`
  stub in
  `services/pilot_onboarding/inventory_import.py`
  with the full atomic
  `import_pilot_inventory` verb.
- Signature stays as declared at
  M19.1:
  `import_pilot_inventory(*,
  dealership: Dealership,
  csv_source: str | Path | IO)
  -> PilotInventoryImportResult`.
- CSV parse with `csv.DictReader`
  (default; no pandas dep).
- Row-by-row validation with
  domain-friendly error messages.
- `Vehicle.objects.bulk_create()`
  for accepted rows.
- Populated `accepted_row_stock_numbers`
  + `rejected_rows` (tuple of
  `(row_dict, error_message)` per
  §0.a M19.2 decision 2).
- Belt-and-suspenders `assert
  dealership.is_pilot` at top of
  write path.
- Enforce M13/M14 unit-price
  invariants where the imported
  VIN/stock number carries pricing.
- M18.1 outbound guard applies
  where inventory import triggers
  any adapter (e.g. VIN decoder
  call if one is used).

### Doc

- **New:** `docs/PILOT_INVENTORY_TEMPLATE.md`
  — authoritative CSV schema doc.
  Column list per §0.a M19.2
  decision 1. Fixed column names
  + types + required/optional
  markers + one-line-per-column
  domain notes.

### Tests

**~20-25 focused tests** in new
`tests/test_m192_pilot_inventory_import.py`:

- Happy path: N rows in → N
  Vehicles created + summary
  fields populated.
- Rejected rows: per-column
  validation errors surface with
  matching row_dict in
  `rejected_rows`.
- Partial-success posture per
  §0.a M19.2 decision 2.
- Belt-and-suspenders `assert`
  fires on demo/live dealership
  bypass.
- Unit-price invariant enforced
  where applicable.
- CSV parse edge cases: BOM,
  trailing whitespace, missing
  optional columns, extra columns
  ignored.
- Idempotency on re-import
  (stock number collision → row
  rejected, not silently updated).
- Empty CSV → empty result +
  no rows.

### Non-goals for M19.2

- ❌ No DRF endpoints (M19.3).
- ❌ No frontend surface.
- ❌ No management-command
  wrapper unless test-only.
- ❌ No new permission classes.
- ❌ No new tenancy carriers.
- ❌ No changes to
  `Vehicle` model schema.

## Backend baseline target

**4,597 → ~4,617-4,622 pass**
(+20-25 tests, 0 regressions).
Frontend Vitest: 140 (unchanged
— no frontend at M19.2).

## Explicit non-goals for SESSION_155

- ❌ Do NOT ship M19.3 endpoints.
- ❌ Do NOT modify M1-M18
  business logic.
- ❌ Do NOT introduce
  pandas / openpyxl / xlrd
  dependencies.
- ❌ Do NOT force-push or amend
  any earlier commits.

## NEXT TASK

Start SESSION_155 with (a) surfacing
the two §0.a M19.2 micro-decisions
(CSV column set + rejected-row
policy) with the user, (b)
starting-state verification, (c)
implementing the full
`import_pilot_inventory` body +
authoring `PILOT_INVENTORY_TEMPLATE.md`
+ tests per §7 M19.2. Ship the
M19.2 handoff.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_19_PLANNING.md`
   (active memo)
6. `docs/handoffs/SESSION_154_m19_inc1_backend_substrate.md`
   (this session's handoff)
7. `docs/handoffs/SESSION_153_m19_inc0_planning.md`
8. `docs/CAPABILITY_MATRIX.md` §7s
9. `backend/dealer_ai/services/pilot_onboarding/inventory_import.py`
   (stub about to be filled)
10. `backend/dealer_ai/services/demo_store/archetypes/retail_subprime.py`
    (M18.2 archetype builder — inventory
    field-set reference)

Narrative docs are claims. Rules +
research + code are facts.

---

## Operational state (post-SESSION_154 — M19.1 SHIPPED)

- **Backend (local):** Django on
  `:8001`. Migrations
  `0001`–`0048`. Test baseline:
  **4,597 pass**, 1 skipped, 0
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
  planning + M19.1 substrate
  shipped. M19.2 inventory
  import next (SESSION_155).
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
  package (six modules).
  Extended at M19.1:
  `services/demo_store/outbound_guard.py`
  refactored to policy-field
  predicate.
- **Frontend accounting
  surface:** unchanged from
  M17.
- **Tenancy carriers:**
  **52**. Grows further only
  if future milestones add
  tenant-scoped models (M19
  itself has no more
  additions).
- **Permission classes:**
  **7 actual** — zero-drift
  streak **fifteen consecutive
  milestones** (M10 → M19.1).
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
  inventory import next
  (SESSION_155). M19.3
  endpoints, M19.4 frontend,
  M19.5 playbook + dry-run,
  M19.6 close-out to follow.
