---
state: active
date: 2026-08-01
last_session_shipped: SESSION_068
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: in-progress
next_session: SESSION_069
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 4
next_increment_name: "M4.4 — Parts tracking service"
---

# Next session — SESSION_069 · Milestone 4 · Increment 4 (M4.4 — parts service)

> **Milestone 4 · Increment 3 shipped at SESSION_068.**
> Ledger integration wired into the M4.2 recon service.
> Five reference-key constants, five `_post_*` helpers,
> `revise_estimate` public function, category mapping
> table, transition-function refactors (approve /
> complete / cancel + estimate revision). Backend baseline
> **2,285 → 2,318 pass**, 1 skipped, 0 fail. Frontend
> unchanged. Planning §5.e appendix added for the category
> mapping.
>
> **SESSION_069 opens M4.4 — the parts service.** Four new
> service functions (`add_part`, `update_part`,
> `transition_part_status`, `delete_part`) in
> `services/recon.py`. Whitelisted-field updates, six-value
> status transition table, per-state timestamp population.
> **No ledger integration** — parts cost lives on the
> WorkOrder's estimate / actual aggregate; parts rows
> themselves do not post to VehicleCost independently.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §8b — every
   service entry threads `dealership=` explicitly.
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.5
   (WorkOrderPart shape), §5.h (parts procurement scope),
   §7 M4.4 (service signatures).
6. `docs/handoffs/SESSION_068_m4_inc3_ledger.md` — this
   session's authoritative closeout.
7. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
   — the M4.2 state machine + tenancy guard pattern M4.4
   mirrors.
8. `docs/handoffs/SESSION_066_m4_inc1_core_models.md` —
   the M4.1 WorkOrderPart model shape.
9. `docs/research/RECON_MAPPING.md` §6.1–§6.6 (parts
   sourcing operational context).

## What M4.4 delivers

**Parts service only.** No migrations. No new endpoints. No
frontend. No AI. **No ledger integration** — parts do not
independently post to VehicleCost; their cost lives on the
WorkOrder's estimate/actual aggregate. Planning §5.h locks
the "operational tracking data only" scope; live
marketplace / auto-order / vendor payment are all deferred.

### The four parts-service functions (per §7 M4.4)

Added to `backend/dealer_ai/services/recon.py`:

1. **`add_part(work_order, *, dealership, name,
   quantity=1, part_number="", source_type="in_stock",
   source_name="", unit_cost=None, notes="") -> WorkOrderPart`**
   — refuses when WO status is not one of `draft`,
   `approved`, `in_progress` (a completed / cancelled WO
   doesn't get new parts). Validates `source_type` against
   `WORK_ORDER_PART_SOURCE_TYPE_CHOICES`.
   `MinValueValidator(1)` on quantity surfaces via
   `full_clean()`.

2. **`update_part(part, *, dealership, **updates) -> WorkOrderPart`**
   — whitelist enforced: `name`, `description`,
   `part_number`, `quantity`, `unit_cost`, `source_type`,
   `source_name`, `notes`. Rejects any other kwarg
   (including `status` — that's what
   `transition_part_status` is for). Refuses when parent
   WO is not in a state that permits parts changes.

3. **`transition_part_status(part, *, dealership,
   new_status, actor)`** — validates transition against
   the allowed table:
   - `needed → ordered` (sets `ordered_at`)
   - `ordered → received` (sets `received_at`)
   - `received → installed` (sets `installed_at`)
   - `ordered → backordered` (no timestamp — waiting)
   - `backordered → ordered` (allowed re-order)
   - `ordered → returned` (sets `returned_at`)
   - `received → returned` (sets `returned_at`)
   
   All other transitions raise
   `InvalidReconTransitionError`. Uses
   `select_for_update` + `refresh_from_db` per M4.2
   concurrency pattern.

4. **`delete_part(part, *, dealership) -> None`** — only
   when parent WO is `draft`. Deleted rows are gone from
   the DB (no soft-delete); parts on approved / in-progress
   WOs stay as historical documentation.

### Test coverage target

~30 focused parts-service tests covering:

- `add_part` gating on WO status (draft/approved/in_progress
  allowed; completed/cancelled refused).
- `add_part` cross-tenant refusal.
- `add_part` invalid source_type refused.
- `update_part` whitelist enforcement.
- `update_part` gating on WO status.
- Every allowed part-status transition succeeds and sets
  the expected timestamp.
- Every disallowed part-status transition raises
  `InvalidReconTransitionError`.
- `delete_part` refuses on non-draft WOs.
- Parts survive WO cancellation (documentation).
- `full_clean` runs before every save (regression coverage
  from M4.2 pattern).

## What SESSION_069 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` — §1.5
     (WorkOrderPart field shape), §5.h (parts scope), §7
     M4.4 (service signatures).
   - `docs/handoffs/SESSION_068_m4_inc3_ledger.md` — the
     "Recommended exact scope for SESSION_069" section.
   - `backend/dealer_ai/services/recon.py` — the M4.2 +
     M4.3 shipped module. New functions land alongside the
     WorkOrder state machine + ledger helpers.
   - `backend/dealer_ai/models.py::WorkOrderPart` — the
     M4.1 model shape including the 6-value status enum
     and 7-value source-type enum.
   - `backend/dealer_ai/tests/test_work_order.py`
     `WorkOrderPart*` classes — persistence-layer coverage
     already locked; M4.4 layers service semantics on top.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,318 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."

3. **Add the four service functions** to
   `services/recon.py` in a new section after the ledger
   helpers. Each starts with a cross-tenant guard against
   the parent WO's tenant; each write path calls
   `full_clean()` before save.

4. **Write ~30 focused parts-service tests** in
   `backend/dealer_ai/tests/test_recon_parts.py`.

5. **Full-suite verification.** Target 2,318 → ~2,348
   pass. Zero regressions.

6. **Ship handoff at
   `docs/handoffs/SESSION_069_m4_inc4_parts.md`**
   mirroring `SESSION_068_m4_inc3_ledger.md` shape.

7. **Overwrite `00-START-NEXT-SESSION.md`** with M4.5
   priority (vendor comm drafting +
   `_scrub_invented_recon_fact`).

## Explicit non-goals for SESSION_069

- ❌ Do NOT post any WorkOrderPart cost to VehicleCost
  independently. Parts cost lives on the WorkOrder's
  estimate/actual aggregate (planning §5.h).
- ❌ Do NOT add live parts marketplace / auto-order
  integration (planning §5.h explicit out-of-scope).
- ❌ Do NOT modify M4.1 model shapes.
- ❌ Do NOT modify M4.2 state-machine semantics.
- ❌ Do NOT modify M4.3 ledger helpers.
- ❌ Do NOT touch M4.5+ scope.
- ❌ Do NOT add any endpoint — M4.6.
- ❌ Do NOT add new permission class — M4.6.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT touch frontend.

## NEXT TASK

Start SESSION_069 with the read-first list above. Add the
four parts-service functions to `services/recon.py`. Write
~30 focused parts-service tests. Target baseline 2,318 →
~2,348. Ship the M4.4 handoff.

Backend baseline at SESSION_069 close: **~2,348 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` (SESSION_066
   refinements at §1.2 + §1.3 + §1.6 + §3 + §5.b + §5.e +
   §7 M4.3; SESSION_067 amendments at §1.0.QC-GAP +
   §1.6.SHIPPED; SESSION_068 category-mapping table at §5.e)
6. `docs/handoffs/SESSION_068_m4_inc3_ledger.md`
7. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
8. `docs/handoffs/SESSION_066_m4_inc1_core_models.md`
9. `docs/handoffs/SESSION_065_m4_planning.md`
10. `docs/roadmap/MILESTONE_2_PLANNING.md` (add_cost API)
11. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
12. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 + §8
13. `docs/research/RECON_MAPPING.md` §6.1–§6.6 (parts)
14. `docs/CAPABILITY_MATRIX.md` §7c + §7d
15. Most recent handoffs
    (`SESSION_068_m4_inc3_ledger.md`,
    `SESSION_067_m4_inc2_service_state_machine.md`,
    `SESSION_066_m4_inc1_core_models.md`,
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

## Operational state (post-SESSION_068 — M4.3 ledger integration shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged from SESSION_066). Test
  baseline: **2,318 pass**, 1 skipped, 0 fail (up from
  2,285; +33 M4.3 ledger tests).
- **Backend (prod):** NOT active (per §5.j — deferred to
  pre-pilot pass).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged. No new
  permission class yet (M4.6).
- **Milestone 4 status:** M4.1 + M4.2 + M4.3 shipped;
  parts service (M4.4) is the next in-scope increment.
  Planning artifact `status: draft` (flips at M4.9).
  Amendments landed through SESSION_068: §1.0.QC-GAP,
  §1.6.SHIPPED (SESSION_067); §1.2 + §1.3 + §1.6 + §3 +
  §5.b + §5.e (including new category-mapping table at
  SESSION_068) + §7 M4.3 (SESSION_066).
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
- **New M4 tables:** unchanged from SESSION_066 (still
  empty at dev-DB level; test-DB populated during test
  runs).
- **Service surface:** `services/recon.py` now exposes
  eleven public functions (ten from M4.2 + `revise_estimate`
  from M4.3), four domain errors, five reference-key
  constants, and the WO→VehicleCost category mapping table.
- **Ledger behavior:** every M4.3 auto-minted VehicleCost
  row carries a `WORKORDER:<id>:*` reference matching one
  of five families. Net estimate contribution on any
  terminal WO is `Decimal("0.00")` by design (verified by
  test).
