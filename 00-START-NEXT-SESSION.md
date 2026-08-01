---
state: active
date: 2026-08-01
last_session_shipped: SESSION_066
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: in-progress
next_session: SESSION_067
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 2
next_increment_name: "M4.2 — Recon service + WorkOrder state machine"
---

# Next session — SESSION_067 · Milestone 4 · Increment 2 (M4.2 — recon service + state machine)

> **Milestone 4 · Increment 1 shipped at SESSION_066.**
> Six recon models, migration `0016`, admin registrations,
> `_TENANT_CARRIER_MODEL_NAMES` 9 → 15, and 95 focused
> tests. Backend baseline **2,124 → 2,219 pass**, 1
> skipped, 0 fail. Frontend unchanged. Three planning
> refinements to `MILESTONE_4_PLANNING.md` landed at
> session open (vendor PROTECT contract, estimate
> retirement on completion, VendorCommunication `logged`
> semantics).
>
> **SESSION_067 opens M4.2 — the service layer.** New
> module `backend/dealer_ai/services/recon.py` with recon
> decision + WorkOrder state-machine functions +
> attach/detach findings + `Vehicle.open_work_orders` /
> `.has_recon_decisions` properties.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §8b — every
   service entry point threads `dealership=` explicitly.
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.1 (recon
   decision service semantics), §1.3 (WorkOrder state),
   §1.4 (attach/detach through table), §1.7 (Vehicle
   read-model extension), §5.c (state machine allowed
   transitions), §5.f (permission matrix — deferred to
   M4.6), §7 M4.2 entry.
6. `docs/handoffs/SESSION_066_m4_inc1_core_models.md` —
   the M4.1 closeout + "Recommended exact scope for
   SESSION_067" section.
7. `docs/handoffs/SESSION_065_m4_planning.md` — the
   ten-decision resolutions.
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 lessons.
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons.
10. `docs/research/RECON_MAPPING.md` — §3.1 (recon
    decision), §4.2 (R.O. as work order), §14
    (bottlenecks driving state).

## What M4.2 delivers

**Service layer only.** No migrations. No endpoints. No
frontend. No AI.

Per SESSION_066 handoff `Recommended exact scope for
SESSION_067` section: new `backend/dealer_ai/services/recon.py`
with eleven exports (`record_decision`, `create_work_order`,
`attach_findings`, `detach_finding`, `approve_work_order`,
`start_work_order`, `complete_work_order`,
`cancel_work_order`, two `Vehicle` `@property` accessors,
`CrossTenantReconError`, `ReconImmutableError`). Every
public function threads `dealership=` explicitly. State
transitions live in the service module; the M4.1 model
layer already refuses illegal shapes via `clean()`.

### Ledger integration is DEFERRED to M4.3

The `services/vehicle_ledger.py::add_cost` calls do NOT
land in M4.2. The M4.2 transition functions capture the
state changes; M4.3 will refactor them to add ledger
calls per the SESSION_066 §5.e refinement (five reference-
key families; completion posts reversal + actual
atomically). **Do not add ledger-hook stubs** — those
would let tests prove a false contract.

## What SESSION_067 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.1 – §1.7,
     §5.c, §5.e (SESSION_066 refinement), §7 M4.2.
   - `docs/handoffs/SESSION_066_m4_inc1_core_models.md` —
     the "Recommended exact scope for SESSION_067" section.
   - `backend/dealer_ai/services/condition_report.py` —
     M3.2 service module as the template.
   - `backend/dealer_ai/services/vehicle_ledger.py::add_cost`
     signature — read but do NOT call in M4.2.
   - `backend/dealer_ai/models.py` — the M4.1 models added
     at SESSION_066.
   - `backend/dealer_ai/tests/test_condition_report_service.py`
     — the test shape M4.2 mirrors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,219 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."

3. **Draft `services/recon.py`** with the exports above.

4. **Add `Vehicle.open_work_orders` +
   `Vehicle.has_recon_decisions` @property accessors** to
   `Vehicle` class (function-local imports per M3.3
   pattern).

5. **Write ~55 focused service tests** in
   `backend/dealer_ai/tests/test_recon_service.py`.

6. **Full-suite verification.** Target 2,219 → ~2,274
   pass. Zero regressions.

7. **Ship handoff at
   `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`**
   mirroring `SESSION_066_m4_inc1_core_models.md` shape.

8. **Overwrite `00-START-NEXT-SESSION.md`** with M4.3
   priority.

## Explicit non-goals for SESSION_067

- ❌ Do NOT implement any ledger integration or ledger
  hook stubs — those land in M4.3.
- ❌ Do NOT create any `VehicleCost` row from any M4.2
  service function.
- ❌ Do NOT write `services/vendor_comm.py` — that is M4.5.
- ❌ Do NOT add parts-service functions — M4.4.
- ❌ Do NOT add `_scrub_invented_recon_fact` — M4.5.
- ❌ Do NOT add any endpoint — M4.6.
- ❌ Do NOT add the new permission class — M4.6.
- ❌ Do NOT modify `services/vehicle_ledger.py`.
- ❌ Do NOT modify `services/condition_report.py`.
- ❌ Do NOT modify `services/llm_safety.py`.
- ❌ Do NOT modify `dealer_ai/permissions.py`.
- ❌ Do NOT modify any M4.1 model shape.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT touch frontend.

## NEXT TASK

Start SESSION_067 with the read-first list above. Draft
`services/recon.py`, add the two `@property` accessors on
`Vehicle`, and write focused service tests. Target
baseline 2,219 → ~2,274. Ship the M4.2 handoff.

Backend baseline at SESSION_067 close: **~2,274 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` (SESSION_066
   refinements landed at §1.2 + §1.3 + §1.6 + §3 + §5.b +
   §5.e + §7 M4.3)
6. `docs/handoffs/SESSION_066_m4_inc1_core_models.md`
7. `docs/handoffs/SESSION_065_m4_planning.md`
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 + §8
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6
10. `docs/research/RECON_MAPPING.md` §3.1 + §4.2 + §14
11. `docs/CAPABILITY_MATRIX.md` §7c + §7d
12. Most recent handoffs
    (`SESSION_066_m4_inc1_core_models.md`,
    `SESSION_065_m4_planning.md`,
    `SESSION_064_m3_inc8_closeout.md`,
    `SESSION_063_m3_inc7_operator_ui.md`,
    `SESSION_062_m3_inc6b_photo_api.md`,
    `SESSION_061_m3_inc6a_admin_api.md`,
    `SESSION_060_m3_inc5_upload_flow.md`,
    `SESSION_059_m3_inc4_storage.md`,
    `SESSION_058_m3_inc3_read_model.md`,
    `SESSION_057_m3_inc2_service_layer.md`,
    `SESSION_056_m3_inc1_core_models.md`).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_066 — M4.1 recon persistence shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016`. Test baseline: **2,219 pass**, 1 skipped,
  0 fail (up from 2,124; +95 M4.1 tests).
- **Backend (prod):** NOT active (per §5.j — deferred to
  pre-pilot pass).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged.
- **Env-override surface:** unchanged.
- **Milestone 4 status:** M4.1 shipped (core persistence);
  planning artifact `status: draft`.
  `MILESTONE_4_PLANNING.md` §1.2 + §1.3 + §1.6 + §3 +
  §5.b + §5.e + §7 M4.3 amended at SESSION_066.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
  Unchanged.
- **New model tables in dev DB:** `dealer_ai_vendor`,
  `dealer_ai_recondecision`, `dealer_ai_workorder`,
  `dealer_ai_workorderfinding`, `dealer_ai_workorderpart`,
  `dealer_ai_vendorcommunication` — all empty.
