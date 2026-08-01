---
state: active
date: 2026-08-01
last_session_shipped: SESSION_067
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: in-progress
next_session: SESSION_068
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 3
next_increment_name: "M4.3 — Ledger integration + estimate retirement"
---

# Next session — SESSION_068 · Milestone 4 · Increment 3 (M4.3 — ledger integration)

> **Milestone 4 · Increment 2 shipped at SESSION_067.**
> `services/recon.py` (ten public functions, four domain
> errors), two `Vehicle` @property accessors
> (`open_work_orders`, `has_recon_decisions`), and 66
> focused service tests. Backend baseline **2,219 → 2,285
> pass**, 1 skipped, 0 fail. Frontend unchanged. Two
> planning amendments landed at session open (§1.6.SHIPPED
> enum reconciliation, §1.0.QC-GAP Q13 renegotiation).
> **Zero ledger calls in M4.2** — per SESSION_067 brief
> pushback on stub hooks, ledger integration is deferred
> entirely to M4.3.
>
> **SESSION_068 opens M4.3 — the ledger seam.** Refactor
> `services/recon.py` transition functions to call
> `services/vehicle_ledger.add_cost` at approve /
> revise-estimate / complete / cancel moments. Reference-key
> vocabulary per SESSION_066 refinement. **Completion posts
> reversal + actual atomically** so
> `projected_total_investment` never double-counts
> completed WOs.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` §8b — every
   service entry threads `dealership=` explicitly.
5. `docs/roadmap/MILESTONE_4_PLANNING.md` — §3
   ledger-integration invariants list, §5.b (Vendor
   snapshot on VehicleCost.vendor free-text unchanged),
   §5.e (SESSION_066 refinement — five reference-key
   families, net-estimate-on-terminal = 0 invariant,
   projected-not-double-count invariant), §7 M4.3
   (SESSION_066 refinement — five hook functions +
   transaction-atomic completion).
6. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
   — this session's authoritative closeout.
7. `docs/handoffs/SESSION_066_m4_inc1_core_models.md` —
   M4.1 shapes.
8. `docs/handoffs/SESSION_065_m4_planning.md` — the
   ten-decision resolutions.
9. `docs/roadmap/MILESTONE_2_PLANNING.md` §2 —
   `services/vehicle_ledger.add_cost` API contract.
10. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
    (reversing-entry pattern from ACCOUNTING §2.11).
11. `docs/research/RECON_MAPPING.md` §5.4 (authorized vs
    actual) + §14 (bottlenecks driving reversal cases).

## What M4.3 delivers

**Ledger integration only.** No new models. No migrations.
No new endpoints. No frontend. No AI. No new domain errors
unless the ledger integration surfaces a genuinely new
failure mode that operational code needs to distinguish.

### Reference-key vocabulary (per §5.e SESSION_066 refinement)

Five module-level constants added to
`backend/dealer_ai/services/recon.py`:

```python
WORKORDER_LEDGER_REF_ESTIMATE = "WORKORDER:{wo_id}:estimate:{seq}"
WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:estimate_reversal:{seq}"
WORKORDER_LEDGER_REF_COMPLETION_ESTIMATE_REVERSAL = "WORKORDER:{wo_id}:completion_estimate_reversal"
WORKORDER_LEDGER_REF_ESTIMATE_REVERSAL_CANCEL = "WORKORDER:{wo_id}:estimate_reversal:cancel"
WORKORDER_LEDGER_REF_ACTUAL = "WORKORDER:{wo_id}:actual"
```

### Five private ledger-posting helpers

Added to `services/recon.py`:

- `_post_estimate(work_order, *, seq) -> Optional[VehicleCost]`
  — posts `add_cost(is_estimate=True, ...)` under
  `estimate:<seq>`. Idempotent (skip if the reference key
  already exists).
- `_post_estimate_reversal(work_order, *, outstanding_amount,
  seq) -> VehicleCost` — negative-amount reversing entry
  under `estimate_reversal:<seq>`.
- `_post_completion_reversal(work_order, *,
  outstanding_amount) -> VehicleCost` — negative-amount
  reversing entry under the one-shot
  `completion_estimate_reversal` reference. Called only
  from the completion flow (SESSION_066 refinement).
- `_post_cancel_reversal(work_order, *,
  outstanding_amount) -> VehicleCost` — negative-amount
  reversing entry under `estimate_reversal:cancel`.
  Called only from the cancellation flow.
- `_post_actual(work_order) -> VehicleCost` — posts
  `add_cost(is_estimate=False, ...)` under `actual`.
  Idempotent.

Every helper passes
`vendor=work_order.vendor.name if work_order.vendor else ""`
as the `add_cost(vendor=...)` snapshot so
`VehicleCost.vendor` free-text captures the vendor name at
posting time. Vendor rename does not rewrite history
(planning §5.b Option C invariant).

### Refactor points in existing transition functions

- **`approve_work_order`** (both draft→approved AND
  idempotent approved→approved): calls `_post_estimate`
  when `estimated_cost` is non-null. Idempotent — a re-run
  under the same seq skips.
- **Estimate revision path** (either widen
  `approve_work_order` to detect a changed
  `estimated_cost` on the idempotent path, OR introduce
  a small dedicated helper — decide at implementation
  time): posts `_post_estimate_reversal(outstanding=<old>,
  seq=<old_seq>)` + `_post_estimate(seq=<old_seq> + 1)`.
- **`complete_work_order`**: calls
  `_post_completion_reversal(outstanding=<current>)` +
  `_post_actual` atomically inside the existing
  `transaction.atomic()` block. Reads current outstanding
  by summing the WO's estimate + estimate_reversal rows to
  date (Decimal arithmetic).
- **`cancel_work_order`**: calls
  `_post_cancel_reversal(outstanding=<current>)` when the
  WO had any outstanding estimate at cancel time.
  Preserves any partial actual posted before cancel (they
  represent work truly performed).

### Load-bearing invariants to test

Per planning §3 ledger-integration list (refined SESSION_066):

- Reference tag on every auto-minted VehicleCost row matches
  one of the five families.
- Idempotency: repeated call to the same reference key
  does not create a duplicate row.
- **Completion posts actual + estimate reversal atomically**
  (transaction rollback test).
- **Net estimate contribution for a terminal WO equals
  `Decimal("0.00")`** — sum of all estimate + reversal
  rows against the WO's reference-key family is zero.
- **`projected_total_investment` does not double-count
  completed WOs** — compute before + after completion;
  delta equals `actual − last_outstanding_estimate`.
- `ConditionFinding.estimated_cost` still never posts to
  VehicleCost (M3.5 invariant preserved — three existing
  tests continue to pass unchanged).
- `total_investment` still excludes estimates.

## What SESSION_068 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` — §3 ledger
     invariants (refined SESSION_066), §5.e (the full
     estimate-retirement contract), §7 M4.3.
   - `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
     — the "Recommended exact scope for SESSION_068"
     section.
   - `backend/dealer_ai/services/vehicle_ledger.py::add_cost`
     signature — this is the M2 API M4.3 wraps.
   - `backend/dealer_ai/services/recon.py` — the M4.2
     shipped service the M4.3 refactor extends.
   - `backend/dealer_ai/models.py::VehicleCost` — the
     model receiving the auto-minted rows.
   - `backend/dealer_ai/tests/test_vehicle_ledger.py` —
     the M2 test shape M4.3 mirrors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,285 pass,
     1 skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."

3. **Add the five reference-key constants** at module top
   of `services/recon.py`.

4. **Add the five private `_post_*` helpers.** Each
   passes `vendor=<snapshot>` to `add_cost`. Each
   idempotency-checks via
   `VehicleCost.objects.filter(reference=<key>).exists()`.

5. **Wire the helpers into the existing transition
   functions.** No new function signatures on the public
   API. `complete_work_order` wraps
   `_post_completion_reversal` + `_post_actual` inside
   the existing `transaction.atomic()` block so a mid-
   completion crash leaves the ledger untouched.

6. **Write ~35 focused ledger-integration tests** in
   `backend/dealer_ai/tests/test_recon_ledger.py`
   covering the invariants above. Update the M4.2
   `ZeroLedgerSideEffectsAcrossAllTransitions` test to
   the M4.3 reality — it should now assert *the right
   number of* VehicleCost rows are created (estimate +
   reversal + actual per approve → complete cycle), not
   zero.

7. **Full-suite verification.** Target 2,285 → ~2,320
   pass. Zero regressions on the 2,285 M1-M4.2 tests.

8. **Ship handoff at
   `docs/handoffs/SESSION_068_m4_inc3_ledger.md`**
   mirroring `SESSION_067_m4_inc2_service_state_machine.md`
   shape.

9. **Overwrite `00-START-NEXT-SESSION.md`** with M4.4
   priority (parts service).

## Explicit non-goals for SESSION_068

- ❌ Do NOT modify M4.1 model shapes.
- ❌ Do NOT modify M4.2 state-machine semantics — only
  add ledger calls at existing transitions.
- ❌ Do NOT modify `services/vehicle_ledger.py::add_cost`
  signature.
- ❌ Do NOT modify `services/condition_report.py`.
- ❌ Do NOT touch `services/llm_safety.py`.
- ❌ Do NOT add QC fields (per §1.0.QC-GAP annotation).
- ❌ Do NOT write `services/vendor_comm.py` — M4.5.
- ❌ Do NOT add parts-service functions — M4.4.
- ❌ Do NOT add any endpoint — M4.6.
- ❌ Do NOT add the new permission class — M4.6.
- ❌ Do NOT introduce any AI role.
- ❌ Do NOT touch frontend.
- ❌ Do NOT introduce any new migration.

## NEXT TASK

Start SESSION_068 with the read-first list above. Add the
five reference-key constants + five `_post_*` helpers to
`services/recon.py`; wire them into the existing
approve/complete/cancel/estimate-revision paths. Update
the M4.2 "zero ledger" regression test to the M4.3
reality. Write ~35 focused ledger-integration tests
locking the net-estimate-on-terminal = 0 invariant.
Target baseline 2,285 → ~2,320. Ship the M4.3 handoff.

Backend baseline at SESSION_068 close: **~2,320 pass**.
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
   §1.6.SHIPPED)
6. `docs/handoffs/SESSION_067_m4_inc2_service_state_machine.md`
7. `docs/handoffs/SESSION_066_m4_inc1_core_models.md`
8. `docs/handoffs/SESSION_065_m4_planning.md`
9. `docs/roadmap/MILESTONE_2_PLANNING.md` (add_cost API)
10. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` §6 lessons
11. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` §6 + §8
12. `docs/research/RECON_MAPPING.md` §5.4 + §14
13. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md` §2.11
    (reversing-entry pattern)
14. `docs/CAPABILITY_MATRIX.md` §7c + §7d
15. Most recent handoffs
    (`SESSION_067_m4_inc2_service_state_machine.md`,
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

## Operational state (post-SESSION_067 — M4.2 service + state machine shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged from SESSION_066; M4.2 added
  no migrations). Test baseline: **2,285 pass**, 1
  skipped, 0 fail (up from 2,219; +66 M4.2 service tests).
- **Backend (prod):** NOT active (per §5.j — deferred to
  pre-pilot pass).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF defaults + CSRF + permissions:** unchanged. No
  new permission class yet (M4.6).
- **Env-override surface:** unchanged.
- **Milestone 4 status:** M4.1 + M4.2 shipped; ledger
  integration (M4.3) is the next in-scope increment.
  Planning artifact `status: draft` (flips to `shipped`
  at M4.9). `MILESTONE_4_PLANNING.md` amendments landed
  through SESSION_067: §1.0.QC-GAP, §1.6.SHIPPED (both
  SESSION_067); §1.2 + §1.3 + §1.6 + §3 + §5.b + §5.e +
  §7 M4.3 (SESSION_066).
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. QC verification is a deferral captured in
  §1.0.QC-GAP.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
  Unchanged.
- **New M4 tables:** `dealer_ai_vendor`,
  `dealer_ai_recondecision`, `dealer_ai_workorder`,
  `dealer_ai_workorderfinding`, `dealer_ai_workorderpart`,
  `dealer_ai_vendorcommunication`. Empty; M4.6/M4.7 will
  populate.
- **New service:** `services/recon.py`. Ten public
  functions, four domain errors. Zero ledger calls yet.
- **New `Vehicle` @property accessors:**
  `open_work_orders`, `has_recon_decisions` (delegating
  to `services/recon.py`).
