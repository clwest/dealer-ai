---
state: active
date: 2026-08-01
last_session_shipped: SESSION_081
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
milestone_5_status: shipped
milestone_6_status: planning
next_session: SESSION_082
next_milestone: 6
next_milestone_name: "Photography + listing generation"
next_increment: 1
next_increment_name: "M6.1 — Core persistence (VehiclePhoto + VehicleListing)"
---

# Next session — SESSION_082 · Milestone 6 · Increment 1 (M6.1 — core persistence)

> **SESSION_081 shipped Milestone 5 closeout +
> `MILESTONE_6_PLANNING.md`.** M5 retrospective +
> capability matrix §7f + roadmap flip + planning
> frontmatter shipped. M6 planning drafted in the same
> shape as M4/M5 (9 sections, 3 `[NEEDS-DECISION-BEFORE-M6.1]`
> items requiring user review). All M5 code +
> M5 docs + M6 planning committed and pushed to
> origin/main in one coordinated push per user
> directive.
>
> **Backend baseline: 2,754 pass, 1 skipped, 0 fail.**
> Frontend `tsc --noEmit` + `vite build` clean.
>
> **SESSION_082 opens M6.1 — core persistence for the
> photo gallery + listing model.** Two new models
> (`VehiclePhoto` + `VehicleListing`) + migration
> `0018` + admin registrations + module-level enum
> constants + cross-tenant `clean()` guards +
> `_TENANT_CARRIER_MODEL_NAMES` extended 17 → 19.
> **NO service module, NO endpoints, NO rules, NO
> frontend, NO AI role.** Persistence layer only.

## First thing SESSION_082 must do — CONFIRM THE THREE DECISIONS

Before any code lands, the user needs to confirm (or
override) three load-bearing decisions from
`MILESTONE_6_PLANNING.md` §9:

1. **§5.a — `VehicleListing` status vocabulary.**
   Recommendation: **Option A** (4 states —
   `draft` / `approved` / `published` / `unpublished`).
   Mirrors M4.5 vendor-comm shape; keeps the approve
   gesture explicit (matches "AI drafts, human
   approves, human publishes" contract).

2. **§5.b — Listing-ready photo count threshold.**
   Recommendation: **Option C** (fixed at 8 for v1;
   per-dealer configurable via
   `DealerOnboardingProfile.listing_ready_photo_count`
   in a future increment). Ship v1 with a sensible
   default; add configurability when operator evidence
   surfaces need.

3. **§5.c — Photo storage layer reuse.**
   Recommendation: **Option A** (extend M3.4's
   `services/photo_storage.py` with a new
   `store_vehicle_photo(...)` verb). Reuse over fork —
   M3.4 primitive is proven; adding a vehicle-photo
   verb is additive without disturbing condition-
   report photos.

**Do not write M6.1 code until these are confirmed or
overridden.** If the user overrides any decision,
amend `MILESTONE_6_PLANNING.md` narrowly at session
top (per SESSION_075 precedent — §0.a change-log
entry) before implementation.

## What M6.1 delivers

**Persistence layer only.** Two new Django models +
migration `0018` + admin + module-level enum constants +
cross-tenant `clean()` guards + tenancy resolver
extension. No service module. No endpoints. No
frontend. No AI role.

### The two models (per `MILESTONE_6_PLANNING.md` §1)

1. **`VehiclePhoto`** (§1.1) — many-per-Vehicle.
   Fields per planning + user's confirmed decisions.
   Cross-tenant `clean()`. Uploaded/deleted actor
   provenance. Safer-direction `marked_deleted_at` +
   `deleted_by` per §7 lesson 7.

2. **`VehicleListing`** (§1.2) — OneToOne with
   Vehicle. Status vocabulary per §5.a (Option A
   pending confirmation). Draft/approve/publish/
   unpublish actor + timestamp pairs. AI-drafted
   `body` + `source_provenance` JSONField mirroring
   M4.5 shape.

### Migration + tenancy + admin

- **Migration `0018`** — creates both models. No data-
  migration needed (unlike M5.1's `0017` — M6 has no
  existing rows to bootstrap).
- **`services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`**
  extended 17 → 19.
- **Admin registrations** for both models following
  the M5.1 diagnostic-only pattern.

### Enum constants (module-level)

- `VEHICLE_LISTING_STATUS_*` constants per §5.a
  decision.
- `VEHICLE_LISTING_STATUS_CHOICES` tuple.

## What SESSION_082 should do

### Recommended step sequence

0. **Confirm the three §9 decisions with the user.**
   Do NOT write code until every
   `[NEEDS-DECISION-BEFORE-M6.1]` item is resolved.
   Amend planning narrowly at session top if any
   decision is overridden.

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_6_PLANNING.md` — §1.1,
     §1.2, §2, §3, §5 (once confirmed), §7 M6.1.
   - `docs/handoffs/SESSION_081_m5_closeout.md` — the
     just-shipped M5 closeout.
   - `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` §6
     lessons.
   - `backend/dealer_ai/models.py` — reread
     `VehicleStage` + `VehicleStageEvent` (M5.1
     shape M6.1 mirrors).
   - `backend/dealer_ai/models.py` — reread
     `ConditionFindingPhoto` (M3.1 photo model shape
     M6.1 partially mirrors).
   - `backend/dealer_ai/services/photo_storage.py`
     (M3.4 photo storage primitive M6.2 will extend).
   - `backend/dealer_ai/models.py` — reread
     `VendorCommunication` (M4.1 draft/approve/sent
     shape M6's `VehicleListing` mirrors).
   - `backend/dealer_ai/services/tenancy.py` — the
     `_TENANT_CARRIER_MODEL_NAMES` tuple.

2. **Verify starting state.**
   - `git status` clean.
   - `python3 manage.py test dealer_ai` → **2,754
     pass, 1 skipped, 0 fail.**
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check
     --dry-run` → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Draft models + enum constants + admin.** Follow
   M5.1 shape.

4. **Extend tenancy resolver.** Add two entries to
   `_TENANT_CARRIER_MODEL_NAMES` (17 → 19).

5. **Generate + apply migration `0018`.** Verify with
   `sqlmigrate` before applying. Confirm
   `makemigrations --check --dry-run` clean after.

6. **Write ~35 focused persistence tests.**

7. **Full-suite verification.** Target 2,754 → ~2,789
   pass. Zero regressions.

8. **Ship handoff at
   `docs/handoffs/SESSION_082_m6_inc1_core_models.md`**
   mirroring `SESSION_075_m5_inc1_core_models.md`
   shape.

9. **Overwrite `00-START-NEXT-SESSION.md`** with M6.2
   priority (photo storage integration).

## Explicit non-goals for SESSION_082

- ❌ Do NOT create service modules — M6.2 (photo
  gallery) + M6.3 (listing).
- ❌ Do NOT integrate the LLM — M6.3.
- ❌ Do NOT add endpoints — M6.5.
- ❌ Do NOT touch frontend — M6.5.
- ❌ Do NOT fill in the M5.3 rule stubs — M6.4.
- ❌ Do NOT refactor the customer-chat truthful
  language — M6.5.
- ❌ Do NOT modify any M1–M5 substrate.
- ❌ Do NOT introduce any AI role.

## NEXT TASK

Start SESSION_082 with (a) confirming the three §9
decisions with the user, (b) the read-first list, then
(c) drafting the two models + migration `0018` +
admin + enum constants + cross-tenant `clean()`
guards + tenancy carrier extension. ~35 focused tests.
Target baseline 2,754 → ~2,789. Ship the M6.1 handoff.

Backend baseline at SESSION_082 close: **~2,789 pass**.
Frontend baseline: unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 6
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_6_PLANNING.md`
6. `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` (M5
   lessons carry into M6)
7. `docs/handoffs/SESSION_081_m5_closeout.md`
8. `docs/roadmap/MILESTONE_5_PLANNING.md` (§5.h
   rule stubs M6.4 fills)
9. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §6
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 5
11. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    pains #8 + #9
12. `docs/CAPABILITY_MATRIX.md` §7d M3 photo storage +
    §7e M4 vendor-comm drafting (M6 reuses both).

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_081 — Milestone 5 SHIPPED)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0017`. Test baseline: **2,754 pass**, 1
  skipped, 0 fail.
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  + `vite build` clean.
- **Frontend (prod):** NONE.
- **Milestones shipped:** M1 → M5. Milestone 6
  planning drafted.
- **DRF admin surface:** 21 endpoints.
- **Frontend operator routes:** 5 (dealer overview,
  ledger, condition report, recon, lifecycle).
- **Service surface:** `recon.py`, `vendor_comm.py`,
  `vehicle_lifecycle.py`, plus M2 ledger + M3
  condition report substrates.
- **Vehicle read-model:** 4 `@property` accessors
  (M4.7: `open_work_orders`, `has_recon_decisions`;
  M5.2: `current_stage`, `is_retail_eligible`).
- **Tenancy carriers:** 17.
- **`Vehicle.is_available`:** unchanged per §5.e
  Option D. Non-retail consumers still filter on it
  (deliberate per §5.e — they migrate on their own
  schedule).
- **Customer-facing filtering:** funnels through
  `customer_visible_vehicles()` which filters on
  `stage=frontline`.
- **Milestone 6 next:** photo gallery + listing
  generation. Fills the M5.3 rule stubs. Truthful
  customer-language refactor lands in M6.5.
