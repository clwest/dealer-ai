---
title: "SESSION_045 handoff — Milestone 2 planning pass (Vehicle investment ledger)"
status: historical
type: handoff
date: 2026-07-31
session: 045
milestone: 2
milestone_status: planning
commit: (pending)
---

# SESSION_045 — Milestone 2 · Increment 0 (planning pass)

## What shipped

One thing: a full implementation-planning pass for Milestone 2 —
persisted as `docs/roadmap/MILESTONE_2_PLANNING.md`. No code. No
migrations. No models. No services. No frontend. This session's
mandate was planning-only and the mandate was honored.

The planning artifact mirrors the shape `MILESTONE_1_PLANNING.md`
proved out at SESSION_035, plus one additional preamble section
(§0) that names the engineering practices from Milestone 1 that
Milestone 2 will inherit.

### `docs/roadmap/MILESTONE_2_PLANNING.md` — sections

- **§0 Engineering practices to preserve.** Eight practices lifted
  from `MILESTONE_1_RETROSPECTIVE.md` §6 that M2 will practice
  explicitly: small increments, compatibility-first, migration-
  before-constraint, dedicated migration-check DB alias, extend-
  over-parallel, clear layer separation, focused permission
  matrices, documentation discipline.
- **§1 Design memo.** Begins with §1.0 — six operational questions
  the ledger must answer, each traced to research (INVENTORY_ACQUISITION
  §4/§5/§14/§15, ACCOUNTING §2.12/§2.14/§2.15, VCP Phase 1). Then
  seven subsystem entries: acquisition record, cost ledger,
  computed gross properties, floor-plan-interest accrual mechanism,
  acquisition-price scrub (safety pipeline stage 17), operator
  ledger UI surface, and — new to this planning shape — §1.7
  "What Milestone 2 enables for future milestones" per user brief
  step 5.
- **§2 Migration impact review.** 25 systems inventoried with
  impact classification (Extended / NEW / NO IMPACT / Reused) and
  the concrete work required per system.
- **§3 Compatibility checklist.** Every Milestone-1 invariant M2
  must uphold (tenancy substrate, identity + auth, endpoint-level
  permissions, customer-facing surfaces, safety stack, dealer
  identity resolution, frontend contracts, test baseline) plus
  every new invariant M2 introduces (model-layer, business-layer,
  endpoint-layer, safety-layer, management-command layer,
  frontend). Every item will be annotated inline at Milestone 2
  close with the test class / code location / runtime probe that
  locks it — the SESSION_044 evidence-inline pattern.
- **§4 Reusable primitives review.** Six primitives from the
  roadmap §3 cited: §3.1 llm_safety (extended), §3.2 payment_engine
  (extended), §3.5 Vehicle model (extended), §3.6 inventory_import
  (not consulted — documented anyway), §3.7 recommended-actions
  (not consulted — documented so scope creep is preempted), §3.9
  dealer_config (extended), §3.10 onboarding profile (one nullable
  field). Two Milestone-1 primitives cited for direct reuse
  (`services/tenancy.py`, `dealer_ai/permissions.py`).
- **§5 Scope discipline + deferrals.** 13 ideas that surfaced
  during planning that would expand scope beyond Milestone 2,
  each deferred (per Discovery Rule) to a named future milestone.
- **§6 Anchors that win on conflict.** Eight-level precedence
  stack (rules → doc governance → roadmap → auth model → M1
  retrospective lessons → research → capability matrix → source
  code).
- **§7 Increment sequencing (planned).** Three increments:
  **M2.1** (schema + models + admin, no API), **M2.2** (API +
  service layer + safety + accrual — the biggest increment),
  **M2.3** (operator UI surface + full §3 compatibility sweep +
  retrospective + Milestone 2 close). Every increment ends with
  the app deployable and the test baseline healthy — the M1 · 4A–4F
  pattern.
- **§8 Related documents.** Cross-references to every source
  cited.

## What this session did NOT do

Explicit non-goals per the SESSION_045 brief, all honored:

- ❌ No Milestone 2 code (no models, no migrations, no services,
  no views, no tests).
- ❌ No changes to the 16-stage safety pipeline. Stage 17
  (acquisition-price scrub) is *planned* here; it lands with
  Increment M2.2, not this session.
- ❌ No re-derivation of Milestone 1 decisions. Every ledger row
  will inherit `dealership` FK NOT NULL from day one; every admin
  endpoint will compose `IsSalesManagerOrOwnerAtActiveDealership`;
  every service function will thread `dealership=` explicitly per
  `AUTHENTICATION_MODEL.md` §8b.
- ❌ No floor-plan-lender integration, auction-feed adapters,
  vendor negotiation, or trade appraisal in scope. All are named
  out-of-scope in the roadmap §Milestone 2.
- ❌ No tenant-scoped uniqueness on `Vehicle.stock_number`
  (still deferred from Milestone 1 §5).
- ❌ No `demo/*` gating decision (separate scope per Milestone 1
  §7 retrospective).

## Substrate confirmed — no surprises

Confirmed during the read-first pass that the substrate M2 will
build on has not drifted since Milestone 1 close (SESSION_044):

- `Vehicle.dealership` FK NOT NULL — verified in
  `backend/dealer_ai/models.py:79-83`.
- `services/tenancy.py::get_current_dealership(request)` +
  `get_active_membership(user)` extension seam + `pre_save`
  autofill — all stable and unchanged.
- `services/llm_safety.py::apply_post_llm_scrubs(text, *, kind)`
  has the obvious extension seam: adding an `_scrub_acquisition_price`
  function + gating it inside `apply_post_llm_scrubs` mirrors the
  existing `_scrub_indie_prohibited` / `_scrub_invented_promotion`
  / `_scrub_invented_appointment` pattern.
- `services/payment_engine.py` — the standard-APR + BHPH math is
  the correct primitive to extend with `daily_floor_plan_interest`.
- `dealer_ai/permissions.py::IsSalesManagerOrOwnerAtActiveDealership`
  is exactly the composed class M2's ledger endpoints will use.
- `DealerOnboardingProfile.floor_plan_lender` (SESSION_032 field,
  `models.py:424`) is already persisted — M2 adds *one* nullable
  field alongside it (`floor_plan_apr`) via additive migration
  `0014`.

## Deferrals surfaced in this planning session

Per the Discovery Rule, ideas that surfaced during this pass but
would expand M2 scope have been deferred (recorded in
`MILESTONE_2_PLANNING.md` §5):

- **`expected_gross` computed property** → Milestone 3. Would
  require `estimated_remaining_investment` which needs
  ConditionReport findings (M3).
- **`Vendor` FK model on `VehicleCost`** → Milestone 4. M2 uses
  free-text `vendor: CharField`.
- **Automated curtailment scheduling** → Milestone 7+ (needs
  lender integration or async).
- **`recon_manager` read/write access on the ledger** →
  Milestone 4 (Recon automation).
- **Aging-alert recommended actions** → Milestone 8
  (Operational intelligence).
- **Tenant-scoped uniqueness on `Vehicle.stock_number`** →
  milestone that first onboards a second live dealership.
- **`Vehicle.is_available` → computed lifecycle** → Milestone 5.
- **`Vehicle.make="Ford"` default rename** → opportunistic (M5
  is likely).
- **Multi-photo storage (S3 + CDN)** → Milestone 3 or pre-M3
  half-milestone.
- **Async / Celery for the accrual command** → Milestone 7.
- **Cost update / delete on `VehicleCost`** → data-first; add
  only if operator feedback warrants (reversing rows is the v1
  correction pattern).
- **Full DMS-style deal recap** → Milestones 9 + 13.
- **Prod deployment as part of M2** → alongside M3 or M4.

## Files touched this session

- **New:** `docs/roadmap/MILESTONE_2_PLANNING.md` (1,201 lines).
- **New:** `docs/handoffs/SESSION_045_milestone_2_planning.md`
  (this file).
- **Overwritten:** `00-START-NEXT-SESSION.md` — pointer updated
  from SESSION_045 = M2 Increment 0 (planning) to SESSION_046 =
  M2 Increment 1 (schema + model layer).

No source code, migrations, tests, or existing documentation
files touched. Zero test baseline delta (1,466 pass, 1 skipped,
0 fail — unchanged from SESSION_044).

## What the next session should do

**SESSION_046 = Milestone 2 · Increment 1 (M2.1 — schema + model
layer).**

Per the planning artifact's §7 · M2.1 boundary:

1. Read the planning artifact end-to-end (`docs/roadmap/MILESTONE_2_PLANNING.md`).
2. Land migrations `0012_vehicleacquisition` and `0013_vehiclecost`
   with the models + admin registration described in §1.1 and §1.2.
3. Implement `services/vehicle_ledger.py` with the `LedgerTotals`
   dataclass + `compute_totals(vehicle, *, dealership) ->
   LedgerTotals`. Every service function threads `dealership=`
   explicitly per `AUTHENTICATION_MODEL.md` §8b.
4. Add computed `@property` methods on `Vehicle`:
   `total_acquisition_cost`, `total_flooring_cost`,
   `total_recon_cost`, `total_admin_cost`, `total_investment`,
   `projected_gross`, `days_in_inventory`.
5. Model-level tests only. No API, no views, no scrub, no
   accrual command, no frontend.
6. Set up `DATABASES["migration_check"]` alias before verifying
   `migrate dealer_ai zero` → `migrate` (M1 lesson 2).
7. Close with a SESSION_046 handoff + overwrite
   `00-START-NEXT-SESSION.md` with the SESSION_047 = M2.2
   priority.

## Anchors that win on conflict (for the next session)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 2
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` §6 (lessons)
6. `docs/roadmap/MILESTONE_2_PLANNING.md` (this session's output —
   the acceptance contract for M2)
7. `docs/BUSINESS_DOMAIN_MAP.md`
8. `docs/research/*_MAPPING.md` + `VEHICLE_CENTRIC_PIVOT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. Current source code (`backend/dealer_ai/models.py`,
    `services/tenancy.py`, `services/llm_safety.py`,
    `services/payment_engine.py`, `permissions.py`)

Planning docs are claims. Rules + research + code are facts.
