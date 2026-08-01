---
state: active
date: 2026-08-01
last_session_shipped: SESSION_074
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: planning
next_session: SESSION_075
next_milestone: 5
next_milestone_name: "Vehicle lifecycle stages + retail gating"
next_increment: 1
next_increment_name: "M5.1 — Core persistence (VehicleStage + VehicleStageEvent)"
---

# Next session — SESSION_075 · Milestone 5 · Increment 1 (M5.1 — core persistence)

> **Milestone 5 planning pass shipped at SESSION_074.**
> `docs/roadmap/MILESTONE_5_PLANNING.md` (1,472 lines)
> resolves seven load-bearing decisions and leaves four
> for user confirmation at SESSION_075 top per the
> SESSION_073 mandate ("Do not silently pick a load-
> bearing decision option without user review"). Backend
> baseline **2,518 pass** unchanged. Frontend unchanged.
>
> **SESSION_075 opens M5.1 — the persistence layer, but
> only after the user confirms the four §9 decisions.**
> Two models (`VehicleStage`, `VehicleStageEvent`) +
> migration `0017` (with bootstrap data migration) +
> admin + module-level enum constants + cross-tenant
> `clean()` guards + `_TENANT_CARRIER_MODEL_NAMES`
> tuple 15 → 17. **Zero services, zero endpoints, zero
> frontend, zero retail-gating refactor.**

## First thing SESSION_075 must do — CONFIRM THE FOUR DECISIONS

Before any code lands, the user needs to confirm (or
override) four load-bearing decisions from
`MILESTONE_5_PLANNING.md` §9:

1. **§5.a Stage enum vocabulary** — recommendation:
   Option C hybrid (12 stages: `incoming → inspection
   → recon → qc → detail → photography → listing →
   frontline → sold`, plus `wholesale_out`,
   `hold_reserved`, `off_market`; `sold` stubbed until
   M9; `detail` kept distinct in v1).

2. **§5.b Allowed transition table** — recommendation:
   the table drafted at §5.b (14 permitted transitions;
   `frontline → sold` deferred to M9).

3. **§5.e `Vehicle.is_available` disposition** —
   recommendation: Option D (keep intact for backwards
   compat; add `is_retail_eligible` as new authoritative;
   docstring deprecation flag with scheduled removal in
   M9 or later).

4. **§5.f Role permission matrix** — recommendation:
   reuse M4.6 + M2.6 permission classes; no new class;
   fine-grained per-transition gating at service layer.
   Especially: is `recon_manager` authorized to mark
   `hold_reserved`? Recommendation: yes.

**Do not write M5.1 code until these are confirmed or
overridden.** If the user overrides any decision, amend
`MILESTONE_5_PLANNING.md` narrowly at session top (per
SESSION_066 refinement precedent) before implementation.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
   — business objective + scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M5
   model inherits the four-layer separation. Cross-
   tenant guards at model layer are load-bearing (belt-
   and-suspenders with the M5.2 service + M5.4 endpoint
   layers).
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — §1.1
   `VehicleStage`, §1.2 `VehicleStageEvent`, §2
   migration impact, §3 M5 invariants M5.1 must
   satisfy, §5.a stage enum decision (once confirmed),
   §5.b transition table (informs
   `Meta.constraints`), §5.c bootstrap decision
   (informs data migration), §7 M5.1 detail.
6. `docs/handoffs/SESSION_074_m5_planning.md` — the
   4-decision resolutions authoritative for this
   session.
7. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6
   lessons (ten inherit unchanged) + §8 M5 bootstrap.
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6
   lessons.
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6
   lessons.
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` §"Data-
    model changes".
11. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §6 seven-category taxonomy (informs Option C stage
    enum).

## What M5.1 delivers

**Persistence layer only.** Two new Django models +
migration `0017` (with bootstrap data migration) + admin
+ module-level enum constants + cross-tenant `clean()`
guards + tenancy resolver extension. No service module.
No endpoints. No frontend. No retail-gating refactor.
No AI role.

### The two models (per `MILESTONE_5_PLANNING.md` §1)

1. **`VehicleStage`** (§1.1) — OneToOne with Vehicle.
   Fields: `vehicle` OneToOne CASCADE, `dealership` FK
   NOT NULL, `current_stage` choices (12 values per
   §5.a Option C — once confirmed), `entered_at`
   DateTimeField, `entered_by` FK SET_NULL nullable,
   `trigger` choices (4 values per §5.b —
   `manual/rule/import/bootstrap`), `last_transition_note`
   TextField blank, timestamps.

2. **`VehicleStageEvent`** (§1.2) — many-per-Vehicle.
   Fields: `vehicle` FK CASCADE, `dealership` FK NOT
   NULL, `from_stage` choices nullable (only for the
   bootstrap event), `to_stage` choices NOT NULL,
   `entered_at` DateTimeField, `by` FK SET_NULL
   nullable, `trigger` choices matching `VehicleStage`,
   `rule_name` CharField blank, `notes` TextField
   blank, `created_at`.

### Migration + tenancy + admin

- **Migration `0017`** — creates both models. **Data-
  migration step per §5.c Option C**: inserts a
  `VehicleStage` row for every existing `Vehicle` where
  `current_stage='frontline'` when `is_available=True`
  else `current_stage='off_market'`;
  `trigger='bootstrap'`; `entered_at=now()`.
- **`services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`**
  extended from 15 → 17 entries (two new carriers).
  Verify `register_default_dealership_autofill` still
  wires cleanly on app-ready.
- **Admin registrations** for both models following the
  M4.1 admin pattern (`VendorAdmin`,
  `ReconDecisionAdmin`, etc.).

### Enum constants (module-level in `models.py`)

- `VEHICLE_STAGE_INCOMING` = `"incoming"` (and so on
  for every value in the enum decided at §5.a).
- `VEHICLE_STAGE_CHOICES` — tuple of (value, label)
  pairs.
- `VEHICLE_STAGE_TRIGGER_MANUAL` = `"manual"` (and
  same for `rule`, `import`, `bootstrap`).
- `VEHICLE_STAGE_TRIGGER_CHOICES` — tuple of (value,
  label) pairs.

Follow the M4.1 enum-constant house pattern (module-
level constants for every individual value + choice
tuples).

### Cross-tenant `clean()` guards

Mirror `VehicleAcquisition.clean` +
`ConditionReport.clean` +
`WorkOrder.clean` patterns. On both models, `clean()`
raises `ValidationError` when the model's `dealership`
FK does not match the parent Vehicle's tenant.

## What SESSION_075 should do

### Recommended step sequence

0. **Confirm the four §9 decisions with the user.** Do
   NOT write code until every `[NEEDS-DECISION-BEFORE-M5.1]`
   item is resolved. If the user overrides any
   recommendation, amend `MILESTONE_5_PLANNING.md`
   narrowly at session top before implementation.

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_5_PLANNING.md` — §1.1,
     §1.2, §2, §3, §5.a (once confirmed), §5.b, §5.c,
     §7 M5.1.
   - `docs/handoffs/SESSION_074_m5_planning.md` — the
     four-decision resolutions.
   - `backend/dealer_ai/models.py` — reread
     `VehicleAcquisition`, `VehicleCost`,
     `ConditionReport`, `ConditionFinding`,
     `WorkOrder`, `VendorCommunication` (persistence-
     layer template).
   - `backend/dealer_ai/services/tenancy.py` — the
     `_TENANT_CARRIER_MODEL_NAMES` tuple + the
     `register_default_dealership_autofill` function.
   - `backend/dealer_ai/tests/test_condition_report.py`
     + `test_vendor.py` (M4.1) — test shape M5.1
     mirrors.
   - `backend/dealer_ai/migrations/0009_backfill_dealership_fks.py`
     — data-migration pattern M5.1's `0017` bootstrap
     migration mirrors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing
     untracked).
   - `python3 manage.py test dealer_ai` → **2,518
     pass, 1 skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check
     --dry-run` → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Draft models + enum constants + admin** in
   `backend/dealer_ai/models.py` +
   `backend/dealer_ai/admin.py`. Follow M4.1 shape:
   choices as `[("value", "Label"), ...]` tuples; FK
   `related_name` explicit and readable; `Meta.ordering`
   set explicitly per model.

4. **Extend tenancy resolver.** Append two entries to
   `_TENANT_CARRIER_MODEL_NAMES` (15 → 17).

5. **Generate + apply migration `0017`.** Verify with
   `sqlmigrate` before applying. Confirm
   `makemigrations --check --dry-run` clean after.
   **Include the data-migration step** for bootstrap
   `VehicleStage` rows.

6. **Write ~40 focused tests** — schema, choices,
   cascade, cross-tenant clean, tenancy-carrier
   registration, bootstrap data migration verifies
   against a seeded fixture.

7. **Full-suite verification.** Target 2,518 → ~2,558
   pass. Zero regressions.

8. **Ship handoff at
   `docs/handoffs/SESSION_075_m5_inc1_core_models.md`**
   mirroring `SESSION_066_m4_inc1_core_models.md`
   shape.

9. **Overwrite `00-START-NEXT-SESSION.md`** with M5.2
   priority (lifecycle service + state machine).

## Explicit non-goals for SESSION_075

- ❌ Do NOT write `services/vehicle_lifecycle.py` — M5.2.
- ❌ Do NOT modify `services/chat_engine.py` or
  `services/inventory_search.py` — M5.5.
- ❌ Do NOT add `Vehicle.current_stage` or
  `Vehicle.is_retail_eligible` `@property` accessors
  — those belong to M5.2 alongside the service.
- ❌ Do NOT add any endpoint — M5.4.
- ❌ Do NOT touch frontend — M5.6.
- ❌ Do NOT modify `Vehicle.is_available` field per
  §5.e Option D (assuming user confirms).
- ❌ Do NOT modify any M2/M3/M4 substrate.
- ❌ Do NOT introduce any new domain error class —
  M5.2 introduces `CrossTenantLifecycleError` /
  `InvalidStageTransitionError` /
  `StageAlreadyCurrentError`.
- ❌ Do NOT introduce any AI role.

## NEXT TASK

Start SESSION_075 with (a) confirming the four §9
decisions with the user, (b) the read-first list, then
(c) draft the two models + migration `0017` (with
bootstrap data migration) + admin + enum constants +
cross-tenant `clean()` guards + tenancy carrier
extension. ~40 focused tests. Target baseline 2,518 →
~2,558. Ship the M5.1 handoff.

Backend baseline at SESSION_075 close: **~2,558 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone
   5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md`
6. `docs/handoffs/SESSION_074_m5_planning.md`
7. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6 + §8
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4 +
    §"Data-model changes"
11. `docs/research/INVENTORY_ACQUISITION_MAPPING.md` §6
12. `docs/CAPABILITY_MATRIX.md` §7e (M4 substrate M5
    reads)
13. Most recent handoffs
    (`SESSION_074_m5_planning.md`,
    `SESSION_073_m4_closeout.md`,
    `SESSION_072_m4_inc7_operator_ui.md`,
    `SESSION_071_m4_inc6_admin_api.md`,
    `SESSION_070_m4_inc5_vendor_comm.md`,
    `SESSION_069_m4_inc4_parts.md`,
    `SESSION_068_m4_inc3_ledger.md`,
    `SESSION_067_m4_inc2_service_state_machine.md`,
    `SESSION_066_m4_inc1_core_models.md`,
    `SESSION_065_m4_planning.md`,
    `SESSION_064_m3_inc8_closeout.md`,
    `SESSION_063_m3_inc7_operator_ui.md`).

Narrative docs are claims. Rules + research + code are
facts.

---

## Operational state (post-SESSION_074 — Milestone 5 planning-pass shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016`. Test baseline: **2,518 pass**, 1
  skipped, 0 fail (unchanged since SESSION_071; M4.7
  was frontend-only; M4.9 + M5.0 were docs-only).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean.
- **Frontend (prod):** NONE.
- **DRF admin surface:** 18 M4.6 recon endpoints
  (unchanged); M5.4 lifecycle endpoints land at
  SESSION_078.
- **Milestone 4 status:** **SHIPPED** at SESSION_073.
- **Milestone 5 status:** planning-pass shipped;
  ready for M5.1 core-persistence drafting once user
  confirms the four §9 decisions.
  `MILESTONE_5_PLANNING.md` frontmatter
  `status: draft` (flips to `shipped` at M5.7).
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Neither has `recon_manager` role.
- **Service surface:**
  - `services/recon.py` — 15 public functions + 4 domain
    errors (M4).
  - `services/vendor_comm.py` — 4 public functions + 4
    domain errors (M4).
  - `services/vehicle_lifecycle.py` — **not yet
    created**; lands at SESSION_076 (M5.2).
- **View surface:** `views.py` (M1 – M3) +
  `views_recon.py` (M4.6). M5.4 view module lands at
  SESSION_078.
- **Permission classes:**
  `IsAdvisorForSlug`, `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6), `IsDealerOwnerAtActiveDealership`,
  `ReadOnly`. M5 reuses M2.6 + M4.6 classes per §5.f
  recommendation.
- **Load-bearing decisions requiring user review:**
  four items at `MILESTONE_5_PLANNING.md` §9 — must be
  confirmed at SESSION_075 top before M5.1 code lands.
