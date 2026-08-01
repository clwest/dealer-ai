---
state: active
date: 2026-08-01
last_session_shipped: SESSION_073
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: shipped
next_session: SESSION_074
next_milestone: 5
next_milestone_name: "Vehicle lifecycle stages + retail gating"
next_increment: 0
next_increment_name: "M5.0 — Planning pass (docs-only)"
---

# Next session — SESSION_074 · Milestone 5 · Increment 0 (M5.0 — planning pass)

> **Milestone 4 closed at SESSION_073.**
> Nine increments (M4.0 → M4.9) minus M4.8 (deferred per
> §5.i / §5.j). Backend baseline **2,124 → 2,518 pass**
> across M4.1 – M4.6; M4.7 was frontend-only; M4.9 was
> docs-only. Full delivery record at
> `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md`; shipped
> surface enumerated at `docs/CAPABILITY_MATRIX.md` §7e;
> planning artifact `status: shipped`.
>
> **SESSION_074 opens M5.0 — the Milestone 5 planning
> pass.** Documentation-only session mirroring
> SESSION_055 (M3.0) + SESSION_065 (M4.0) invocations.
> Deliverable: `docs/roadmap/MILESTONE_5_PLANNING.md`
> anchoring subsequent increments M5.1 – M5.N.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md` — six project-work rules.
2. `docs/DOC_GOVERNANCE.md` — documentation rules
   (planning artifact goes in `docs/roadmap/`).
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5 —
   business objective + related research + operational
   pain + reusable primitives + gap + scope boundary +
   recommended order.
4. `docs/roadmap/AUTHENTICATION_MODEL.md` — every M5
   service entry inherits the tenancy substrate; new
   permission classes compose from existing role
   constants where possible.
5. `docs/handoffs/SESSION_073_m4_closeout.md` — this
   session's authoritative closeout + "Recommended exact
   scope for SESSION_074".
6. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` — §8 M5
   bootstrap notes: read-model prerequisites shipped
   (`Vehicle.open_work_orders`, `Vehicle.has_recon_decisions`,
   `services/recon.py::open_work_orders_for_vehicle`,
   `has_recon_decisions_for_vehicle`). §6 lessons M5
   inherits.
7. `docs/roadmap/MILESTONE_4_PLANNING.md` — the 8-section
   shape M5.0 mirrors most closely.
8. `docs/roadmap/MILESTONE_3_PLANNING.md` — same shape
   reference (M3.0 was the first planning-pass example).
9. `docs/research/RECON_MAPPING.md` §"pains" (recon ETA
   mismatch drives the stage-truth need — Sales pain #4
   "waiting on recon"; recon pain #12 "ETAs that don't
   match reality").
10. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
    §"Inventory categorization" — the seven-value stage
    vocabulary M5 will formalize (front-line ready, in
    recon, incoming, wholesale-out, company use,
    hold/reserved, off-market).
11. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4 +
    §"Retail eligibility rule" — the VCP semantic
    contract M5 implements.
12. `docs/CAPABILITY_MATRIX.md` §7e — M4 shipped surfaces
    M5 reads.

## What M5.0 delivers

**Documentation only.** No code changes. No migrations.
No frontend. Backend baseline **2,518 pass** unchanged.

The single deliverable is
`docs/roadmap/MILESTONE_5_PLANNING.md`, structured to
mirror `MILESTONE_4_PLANNING.md` (which mirrored
`MILESTONE_3_PLANNING.md`, which mirrored
`MILESTONE_2_PLANNING.md`). 8 sections:

**§0 Engineering practices to preserve from M2 + M3 + M4.**
Synthesize the ten lessons from `MILESTONE_4_RETROSPECTIVE.md`
§6 as the carry-forward set for M5.

**§1 Design memo — start with operational questions.**
Frame the four operational questions M5 must answer
(candidates):
- Q1: "Is this vehicle front-line ready?" (VCP retail-
  eligibility rule).
- Q2: "What stage is this vehicle in?" (INVENTORY §
  categorization enum).
- Q3: "When and by whom did each stage transition happen?"
  (audit trail).
- Q4: "Which recon-completion events triggered which
  stage transitions?" (M4 → M5 causal chain).

Then §1.1 – §1.N one entry per subsystem:
- §1.1 `VehicleStage` entity (1:1 with Vehicle, current
  stage, entered_at). Or refactor `Vehicle.is_available`
  into a computed property backed by the stage enum.
- §1.2 `VehicleStageEvent` entity (audit trail:
  from_stage, to_stage, actor, trigger, notes).
- §1.3 Retail-gating service (public chat retrieval path
  filters on `stage='frontline'` — one-line change with
  test-suite ripple).
- §1.4 Deterministic stage-transition rules per VCP:
  inspection → recon when a completed condition report
  has ≥1 recommended-or-higher finding; recon → qc when
  all `must_do` / `safety` WorkOrders are complete;
  photography → listing at photo threshold; listing →
  frontline when published + price > 0.
- §1.5 Manual stage transitions with actor logging.
- §1.6 Vehicle read-model extension (new @property
  accessors as needed).
- §1.7 What M5 enables for downstream milestones (M6
  photography stage; M7 async aging warnings; M8
  aging-per-stage analytics; M11+ sale-eligibility gate).

**§2 Migration impact review.** Every existing surface M5
touches with the concrete work required. M4 substrate is
read-only from M5's perspective — no changes needed to
`services/recon.py` or `services/vendor_comm.py`.

**§3 Compatibility checklist.** M1 + M2 + M3 + M4
invariants M5 must not regress.

**§4 Reusable primitives review.** Every primitive M5
should extend or directly reuse.

**§5 Load-bearing decisions + deferrals.** Candidates for
M5.0:
- §5.a State-machine granularity (7 states from
  INVENTORY §, or a smaller v1 subset?).
- §5.b Auto-transitions from M4 recon completion vs
  manual transitions (hybrid?).
- §5.c Retail gating: hard-block (chat cannot surface
  non-frontline units at all) vs advisory (chat can
  mention with a warning)?
- §5.d Aging-per-stage: measured in M5 or deferred to
  M8?
- §5.e Existing `Vehicle.is_available` — deprecate,
  refactor to computed, or leave as an override switch?
- §5.f Role permission matrix (new class needed?).
- Additional decisions surfaced during the memo pass.

**§6 Anchors that win on conflict.**

**§7 Increment sequencing.** Target: 5–7 sub-increments,
one per session, ending at M5.N closeout mirroring M3.8 /
M4.9.

**§8 Related documents.**

## What SESSION_074 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone
     5 — the business framing.
   - `docs/handoffs/SESSION_073_m4_closeout.md` — the
     scope block above.
   - `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md` §8 —
     the M4 → M5 bootstrap surface.
   - `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4 +
     §"Retail eligibility rule".
   - `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
     §"Inventory categorization".
   - `docs/research/RECON_MAPPING.md` pains #12 (recon
     ETA mismatch) + Sales pain #4 (waiting on recon).
   - `docs/roadmap/MILESTONE_4_PLANNING.md` — the 8-
     section shape M5.0 mirrors.
   - `docs/roadmap/MILESTONE_3_PLANNING.md` — same shape
     reference.
   - `backend/dealer_ai/services/recon.py` — the M4
     surface M5 reads.
   - `backend/dealer_ai/models.py::Vehicle` — the
     current `is_available` field + M3/M4 @property
     accessors.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,518 pass,
     1 skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Draft `docs/roadmap/MILESTONE_5_PLANNING.md`** —
   8 sections per the shape above. Cite research
   corpus + VCP + INVENTORY mapping wherever an
   assertion is made. Aim for ~1,500 – 2,000 lines
   (M3.0 was 1,342 lines; M4.0 was 1,712 → 2,061 after
   amendments; M5.0 should land in the same ballpark).

4. **Resolve every load-bearing decision** at §5. If a
   decision needs user input, mark it as
   `[NEEDS-DECISION-BEFORE-M5.1]` in the draft. Do not
   silently pick an option for a decision the user should
   see.

5. **Sequence increments at §7.** Target 5–7 sub-
   increments. Each ends with a healthy test baseline +
   a shipped surface + a handoff.

6. **Ship handoff at
   `docs/handoffs/SESSION_074_m5_planning.md`** mirroring
   `SESSION_055_milestone_3_planning.md` and
   `SESSION_065_m4_planning.md` shape.

7. **Overwrite `00-START-NEXT-SESSION.md`** with M5.1
   priority (first M5 implementation increment).

## Explicit non-goals for SESSION_074

- ❌ Any code change (M5.0 is docs-only per SESSION_055
  + SESSION_065 precedent).
- ❌ Any migration.
- ❌ Any endpoint / permission / frontend change.
- ❌ Silently picking a load-bearing decision option
  without user review. Mark it
  `[NEEDS-DECISION-BEFORE-M5.1]` in the draft instead.
- ❌ Committing to M5.8 or later before M5.1 has landed.
  Plan the next 5–7 sub-increments; leave later scope
  for later planning refinement.

## NEXT TASK

Start SESSION_074 with the read-first list above. Draft
`docs/roadmap/MILESTONE_5_PLANNING.md` (8 sections;
~1,500 – 2,000 lines target; every load-bearing decision
resolved or marked for user review). Ship the M5.0
handoff. Overwrite start-here for M5.1.

Backend baseline at SESSION_074 close: **2,518 pass**
unchanged (M5.0 is docs-only).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/handoffs/SESSION_073_m4_closeout.md`
6. `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md`
7. `docs/roadmap/MILESTONE_4_PLANNING.md`
8. `docs/roadmap/MILESTONE_3_PLANNING.md`
9. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md`
10. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 4
11. `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
12. `docs/research/RECON_MAPPING.md`
13. `docs/CAPABILITY_MATRIX.md` §7e
14. Most recent handoffs
    (`SESSION_073_m4_closeout.md`,
    `SESSION_072_m4_inc7_operator_ui.md`,
    `SESSION_071_m4_inc6_admin_api.md`,
    `SESSION_070_m4_inc5_vendor_comm.md`,
    `SESSION_069_m4_inc4_parts.md`,
    `SESSION_068_m4_inc3_ledger.md`,
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

## Operational state (post-SESSION_073 — Milestone 4 shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged since SESSION_066). Test
  baseline: **2,518 pass**, 1 skipped, 0 fail (unchanged
  since SESSION_071; M4.7 was frontend-only; M4.9 was
  docs-only).
- **Backend (prod):** NOT active (per M4 planning §5.j
  deferred to pre-pilot pass).
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. M4.7 recon UI + inventory-
  card button shipped.
- **Frontend (prod):** NONE.
- **DRF admin surface:** 18 M4.6 recon endpoints under
  `/api/dealer-ai/admin/` (unchanged since SESSION_071).
- **Milestone 4 status:** **SHIPPED**. Planning artifact
  `status: shipped`. Retrospective at
  `docs/roadmap/MILESTONE_4_RETROSPECTIVE.md`. Capability
  matrix §7e enumerates every surface. M4.8 (outbound
  send) deferred per §5.i / §5.j.
- **Milestone 5 status:** **NEXT** — planning pass at
  SESSION_074.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not
  exist. Every deferred item has a home in an existing
  planning / retrospective / handoff doc.
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
  Neither has `recon_manager` role. For M4 verification
  smoke testing, either extend `smoke_owner` with an
  additional `recon_manager` membership or create a
  `smoke_recon` user.
- **Service surface:**
  - `services/recon.py`: 15 public functions + 4 domain
    errors + ledger integration constants + parts
    functions + Vehicle read helpers.
  - `services/vendor_comm.py`: 4 public functions + 4
    domain errors.
- **View surface:** `views.py` (M1 – M3, ~2,400 lines) +
  `views_recon.py` (M4.6, ~750 lines).
- **Permission classes:**
  `IsAdvisorForSlug`, `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6), `IsDealerOwnerAtActiveDealership`, `ReadOnly`.
- **Frontend surface:** M4.7 recon page + 6 components +
  18 typed API helpers + "Recon" button on operator
  inventory card.
