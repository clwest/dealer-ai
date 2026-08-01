---
state: active
date: 2026-08-01
last_session_shipped: SESSION_065
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: planning
next_session: SESSION_066
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 1
next_increment_name: "M4.1 — Core persistence (Vendor + recon models)"
---

# Next session — SESSION_066 · Milestone 4 · Increment 1 (M4.1 — core persistence)

> **Milestone 4 planning pass shipped at SESSION_065.**
> `docs/roadmap/MILESTONE_4_PLANNING.md` (1,712 lines)
> resolves all ten load-bearing pre-implementation decisions
> and sequences nine increments. Backend baseline **2,124
> pass** unchanged. Frontend unchanged.
>
> **SESSION_066 opens M4.1 — the persistence layer.** Six
> models (`Vendor`, `ReconDecision`, `WorkOrder`,
> `WorkOrderFinding`, `WorkOrderPart`,
> `VendorCommunication`) + migration `0016` + admin +
> cross-tenant `clean()` guards + enum constants +
> `_TENANT_CARRIER_MODEL_NAMES` extension. **Zero services,
> zero endpoints, zero frontend, zero AI.**

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4 —
   business objective + scope boundary.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M4 model
   inherits the four-layer separation. Cross-tenant guards
   at model layer are load-bearing (belt-and-suspenders
   with the M4.6 service + endpoint layers).
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.1 through
   §1.7 (all seven subsystem shapes), §2 migration impact,
   §3 M4 invariants M4.1 must satisfy, §5.b + §5.c + §5.d
   + §5.f + §5.h (load-bearing decisions M4.1 honors at
   model layer), §7 M4.1 detail.
6. `docs/handoffs/SESSION_065_m4_planning.md` — the
   ten-decision resolutions + M4.1 scope authoritative for
   this session.
7. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 lessons
   (ten inherit unchanged) + §8 M4 bootstrap.
8. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
9. `docs/research/RECON_MAPPING.md` — full document;
   §§3–7 + §11 + §13.1 + §14 + §16 all cited by the
   planning artifact.

## What M4.1 delivers

**Persistence layer only.** Six new Django models +
migration `0016` + admin + module-level enum constants +
cross-tenant `clean()` guards + tenancy resolver
extension. No service module. No endpoints. No frontend.
No AI role.

### The six models (per `MILESTONE_4_PLANNING.md` §1)

1. **`Vendor`** (§1.2) — many-per-Dealership. Fields:
   `dealership` FK NOT NULL, `name`, `slug` (unique-per-
   dealership), `categories` JSONField (list of category
   slugs), `phone`, `email`, `notes`, `is_active` default
   True, timestamps. Soft-delete only (never hard-delete
   a vendor referenced by historical rows).

2. **`ReconDecision`** (§1.1) — one-per-ConditionFinding.
   Fields: `finding` OneToOne CASCADE, `dealership` FK
   NOT NULL, `tier` choices (`must_do`, `should_do`,
   `wont_do`), `decided_by` FK SET_NULL nullable,
   `decided_at`, `notes` TextField blank, timestamps.

3. **`WorkOrder`** (§1.3) — many-per-Vehicle. Fields:
   `vehicle` FK CASCADE, `dealership` FK NOT NULL,
   `category` choices (12 categories matching
   `ConditionFinding.category`), `venue` choices
   (`in_house`, `outsourced`), `vendor` FK SET_NULL
   nullable, `assignee` FK SET_NULL nullable, `status`
   choices (`draft`, `approved`, `in_progress`,
   `completed`, `cancelled`), `estimated_cost`,
   `authorized_cost`, `actual_cost` Decimals,
   `estimated_completion_date`,
   `actual_completion_date`, `notes`, plus provenance:
   `approved_at`, `approved_by`, `started_at`,
   `started_by`, `completed_at`, `completed_by`,
   `cancelled_at`, `cancelled_by`, `cancellation_reason`,
   timestamps.

4. **`WorkOrderFinding`** (§1.4) — through model.
   Fields: `work_order` FK CASCADE, `finding` FK
   CASCADE, `dealership` FK NOT NULL, `created_at`,
   `Meta.unique_together = ("work_order", "finding")`.

5. **`WorkOrderPart`** (§1.5) — many-per-WorkOrder.
   Fields per planning §1.5: `work_order` FK CASCADE,
   `dealership` FK NOT NULL, `name`, `description`,
   `part_number`, `quantity`, `unit_cost` Decimal
   nullable, `status` choices (six values: `needed`,
   `ordered`, `backordered`, `received`, `installed`,
   `returned`), `source_type` choices, `source_name`,
   per-state timestamps (`ordered_at`, `received_at`,
   `installed_at`, `returned_at`), `notes`, timestamps.

6. **`VendorCommunication`** (§1.6) — many-per-WorkOrder,
   many-per-Vendor. Fields: `work_order` FK CASCADE,
   `vendor` FK SET_NULL nullable, `dealership` FK NOT
   NULL, `kind` choices (`vendor_comm`, `parts_order`,
   `narrative`, etc.), `channel` choices (`email`,
   `sms`, `phone`, `in_person`, `internal_note`),
   `direction` choices (`outbound`, `inbound`),
   `status` choices (`draft`, `approved`, `sent`,
   `logged`), `draft_content` TextField,
   `sent_content` TextField blank, `source_provenance`
   JSONField, `drafted_by`, `drafted_at`,
   `approved_by`, `approved_at`, `sent_by`, `sent_at`,
   timestamps.

### Migration + tenancy + admin

- **Migration `0016`** — verify sequential via
  `python3 manage.py showmigrations dealer_ai`.
  `makemigrations --check --dry-run` must report "No
  changes detected." after generation.
- **`services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`**
  extended from 9 → 15 entries (six new carriers).
  Verify `register_default_dealership_autofill` still
  wires cleanly on app-ready.
- **Admin registrations** for all six models following
  the M2/M3 admin pattern
  (`VehicleAcquisitionAdmin`, `VehicleCostAdmin`,
  `ConditionReportAdmin`, `ConditionFindingAdmin`,
  `ConditionFindingPhotoAdmin`).

### Enum constants (module-level in `models.py`)

- `WORK_ORDER_STATUS_CHOICES` — 5 values.
- `WORK_ORDER_VENUE_CHOICES` — 2 values.
- `RECON_DECISION_TIER_CHOICES` — 3 values.
- `WORK_ORDER_PART_STATUS_CHOICES` — 6 values.
- `WORK_ORDER_PART_SOURCE_TYPE_CHOICES` — finalize
  count in M4.1 per RECON §6.1–§6.4.
- `VENDOR_COMMUNICATION_KIND_CHOICES` — includes
  `vendor_comm`, `parts_order`, `narrative`.
- `VENDOR_COMMUNICATION_CHANNEL_CHOICES` — includes
  `email`, `sms`, `phone`, `in_person`, `internal_note`.
- `VENDOR_COMMUNICATION_DIRECTION_CHOICES` —
  `outbound`, `inbound`.
- `VENDOR_COMMUNICATION_STATUS_CHOICES` — includes
  `draft`, `approved`, `sent`, `logged`.

### Cross-tenant `clean()` guards

Mirror `VehicleAcquisition.clean` +
`ConditionReport.clean` patterns. On each of the six
new models, `clean()` raises `ValidationError` when the
model's `dealership` FK does not match its parent's
(e.g. `WorkOrder.dealership` must equal
`WorkOrder.vehicle.dealership`; `ReconDecision.dealership`
must equal `ReconDecision.finding.dealership`;
`WorkOrderFinding.dealership` must equal both parent's).
This is the belt half of belt-and-suspenders;
service-layer guards land in M4.2.

## What SESSION_066 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` — §0, §1.1
     through §1.7, §2, §3, §5.b + §5.c + §5.d + §5.h,
     §7 M4.1 entry.
   - `docs/handoffs/SESSION_065_m4_planning.md` — the
     Exact M4.1 scope section.
   - `backend/dealer_ai/models.py` — reread
     `VehicleAcquisition`, `VehicleCost`,
     `ConditionReport`, `ConditionFinding`,
     `ConditionFindingPhoto` (persistence-layer
     template).
   - `backend/dealer_ai/services/tenancy.py` — the
     `_TENANT_CARRIER_MODEL_NAMES` tuple + the
     `register_default_dealership_autofill` function.
   - `backend/dealer_ai/tests/test_condition_report.py`
     + `test_condition_finding.py` — test shape M4.1
     mirrors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing
     untracked).
   - `python3 manage.py test dealer_ai` → **2,124
     pass, 1 skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check
     --dry-run` → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Draft models + enum constants + admin** in
   `backend/dealer_ai/models.py` +
   `backend/dealer_ai/admin.py`. Follow M2/M3 shape:
   choices as `[("value", "Label"), ...]` tuples;
   Decimals with `max_digits=10, decimal_places=2`;
   FK `related_name` explicit and readable;
   `Meta.ordering` set explicitly per model.

4. **Extend tenancy resolver.** Append six entries to
   `_TENANT_CARRIER_MODEL_NAMES`.

5. **Generate + apply migration `0016`.** Verify with
   `sqlmigrate` before applying. Confirm
   `makemigrations --check --dry-run` clean after.

6. **Write ~65 focused tests** across six new test
   files (`test_vendor.py`, `test_recon_decision.py`,
   `test_work_order.py`, `test_work_order_finding.py`,
   `test_work_order_part.py`,
   `test_vendor_communication.py`) — schema,
   choices, cascade, cross-tenant clean, unique
   constraints, tenancy-carrier registration.

7. **Full-suite verification.** Target 2,124 → ~2,189
   pass. Zero regressions.

8. **Ship handoff at
   `docs/handoffs/SESSION_066_m4_inc1_core_models.md`**
   mirroring `SESSION_056_m3_inc1_core_models.md` shape.

9. **Overwrite `00-START-NEXT-SESSION.md`** with M4.2
   priority (services layer + state machine).

## Explicit non-goals for SESSION_066

- ❌ Do NOT write `services/recon.py` — that is M4.2.
- ❌ Do NOT write `services/vendor_comm.py` — that is
  M4.5.
- ❌ Do NOT add any `@property` on `Vehicle` — M4.2.
- ❌ Do NOT add estimate-to-ledger integration — M4.3.
- ❌ Do NOT add parts-status transition service logic —
  M4.4.
- ❌ Do NOT add `_scrub_invented_recon_fact` — M4.5.
- ❌ Do NOT add any endpoint — M4.6.
- ❌ Do NOT add the new permission class — M4.6.
- ❌ Do NOT modify `services/vehicle_ledger.py`.
- ❌ Do NOT modify `services/condition_report.py`.
- ❌ Do NOT modify `services/tenancy.py` resolver
  signatures (only extend `_TENANT_CARRIER_MODEL_NAMES`).
- ❌ Do NOT modify `services/llm_safety.py`.
- ❌ Do NOT modify `dealer_ai/permissions.py`.
- ❌ Do NOT modify `VehicleCost.vendor` (per
  `MILESTONE_4_PLANNING.md` §5.b).
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT touch frontend.

## NEXT TASK

Start SESSION_066 with the read-first list above. Draft
the six models + migration `0016` + admin + enum
constants + cross-tenant `clean()` guards + tenancy
carrier extension. ~65 focused tests. Target baseline
2,124 → ~2,189. Ship the M4.1 handoff.

Backend baseline at SESSION_066 close: **~2,189 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md`
6. `docs/handoffs/SESSION_065_m4_planning.md`
7. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 + §8
8. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6
9. `docs/research/RECON_MAPPING.md` §§3–7 + §11 + §13.1
   + §14 + §16
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 3
11. `docs/CAPABILITY_MATRIX.md` §7c + §7d
12. Most recent handoffs
    (`SESSION_065_m4_planning.md`,
    `SESSION_064_m3_inc8_closeout.md`,
    `SESSION_063_m3_inc7_operator_ui.md`,
    `SESSION_062_m3_inc6b_photo_api.md`,
    `SESSION_061_m3_inc6a_admin_api.md`,
    `SESSION_060_m3_inc5_upload_flow.md`,
    `SESSION_059_m3_inc4_storage.md`,
    `SESSION_058_m3_inc3_read_model.md`,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`,
    `SESSION_055_milestone_3_planning.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_065 — Milestone 4 planning-pass shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0015`. Test baseline: **2,124 pass**, 1
  skipped, 0 fail (unchanged from SESSION_064).
- **Backend (prod):** NOT active (per §5.j — deferred
  to pre-pilot pass).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Env-override surface:** unchanged.
- **Milestone 4 status:** planning-pass shipped;
  ready for M4.1 core-persistence drafting.
  `MILESTONE_4_PLANNING.md` frontmatter
  `status: draft` (flips to `shipped` at M4.9).
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does
  not exist. Every deferral has a home in an existing
  planning / retrospective / handoff doc.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Unchanged.
