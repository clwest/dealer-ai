---
state: active
date: 2026-08-01
last_session_shipped: SESSION_072
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: closeout-pending
next_session: SESSION_073
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 9
next_increment_name: "M4.9 — Verification + closeout (docs-only)"
---

# Next session — SESSION_073 · Milestone 4 · Increment 9 (M4.9 — closeout)

> **Milestone 4 · Increment 7 shipped at SESSION_072.**
> Frontend recon operator UI: new route
> `/dealer-ai-inventory/:stock/recon` + `VehicleReconPage.tsx`
> + 6 extracted components in `components/recon/` + typed
> API helpers for all 18 M4.6 endpoints appended to
> `lib/api.ts` + "Recon" button on the operator inventory
> card. Backend frozen at **2,518 pass**; `tsc --noEmit`
> clean; `vite build` clean.
>
> **M4.8 (deferred send) is NOT landing** — planning §5.i
> + §5.j lock the "no live send in M4 v1" posture; without
> a real pilot-store engagement, M4.8 stays deferred. M4
> closes at M4.9.
>
> **SESSION_073 opens M4.9 — the closeout.** Documentation-
> only session mirroring M2.8 / M3.8 shape: §3 compatibility
> sweep, `MILESTONE_4_RETROSPECTIVE.md`, capability matrix
> §7e, roadmap flip, planning-doc frontmatter flip to
> `shipped`, start-here overwrite for M5.0 planning.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/MILESTONE_4_PLANNING.md`:
   - §3 compatibility checklist (every row gets an evidence
     citation at M4.9).
   - §5.i (send deferred) + §5.j (prod deployment
     deferred) locking M4.8 as NOT landing in this
     milestone.
   - §7 M4.9 (docs-only deliverable list).
5. `docs/handoffs/SESSION_072_m4_inc7_operator_ui.md` — this
   session's authoritative closeout + "Recommended exact
   scope for SESSION_073".
6. Prior M4 handoffs (066, 067, 068, 069, 070, 071).
7. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — the
   retrospective shape M4.9 mirrors.
8. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md` — same
   template.
9. `docs/CAPABILITY_MATRIX.md` §7c + §7d — the M2 / M3
   surface-entry shape M4.9 mirrors for §7e.

## What M4.9 delivers

**Documentation only.** No code changes. No migrations.
No frontend changes. Backend baseline **2,518 pass**
unchanged.

### Concrete deliverables

1. **§3 compatibility sweep in `MILESTONE_4_PLANNING.md`.**
   Every row in the M1 + M2 + M3 invariants list and the
   new M4 invariants list gets a bulleted evidence
   citation (test class, code location, or runtime probe
   that locks it). Mirrors M2.8 / M3.8 discipline.

2. **`docs/roadmap/MILESTONE_4_RETROSPECTIVE.md`** — new
   document mirroring `MILESTONE_3_RETROSPECTIVE.md`
   shape:

   - Shipped increments (M4.1 – M4.7 with commit hashes +
     one-line summaries + baseline deltas).
   - Load-bearing decisions in review (§5.a through
     §5.j — did each play out as expected? Any
     revisions warranted?).
   - Deferred:
     - M4.8 send (planning §5.i + §5.j — deferred to
       post-M4 prod-readiness pass).
     - QcVerification (§1.0.QC-GAP — Path A vs Path B
       decision deferred).
     - Vendor CRUD admin page in the UI (M4.7
       explicit non-goal).
     - Per-sentence source_provenance UI attribution.
   - Lessons learned (with cross-refs to M2 §6 + M3 §6
     lessons carried forward).
   - M5 bootstrap notes — what M5 needs to know about the
     M4 substrate (open_work_orders + has_recon_decisions
     Vehicle properties; ledger family in the M2
     substrate; the recon-fact scrub kind values).

3. **`docs/CAPABILITY_MATRIX.md` §7e** — new section
   "Recon automation (Milestone 4, shipped)". Every M4.1
   – M4.7 surface gets an entry mirroring §7c / §7d shape.

4. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md` §M4 marked
   SHIPPED; §M5 promoted** to the next in-scope
   milestone.

5. **`MILESTONE_4_PLANNING.md` frontmatter flip** to
   `status: shipped`.

6. **Overwrite `00-START-NEXT-SESSION.md`** with M5.0
   priority (M5 planning pass, mirroring the SESSION_055
   → M3 or SESSION_065 → M4 planning-pass shape).

## What SESSION_073 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` §3 checklist +
     §5.i + §5.j + §7 M4.9.
   - `docs/handoffs/SESSION_072_m4_inc7_operator_ui.md` —
     scope block.
   - All prior M4 handoffs (066–072) to gather commit
     hashes + baseline deltas for the retrospective.
   - `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` — the
     shape M4.9 mirrors.
   - `docs/CAPABILITY_MATRIX.md` §7c + §7d — the
     surface-entry shape §7e mirrors.
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §M4 + §M5.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,518 pass, 1
     skipped, 0 fail**.
   - `python3 manage.py check` clean.
   - `python3 manage.py makemigrations --check --dry-run`
     → "No changes detected."
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Do the §3 sweep** by walking every checklist row in
   `MILESTONE_4_PLANNING.md` §3 and adding an evidence
   citation. This is a hand-crafted pass — a mechanical
   grep is not sufficient because some invariants live
   across multiple test files.

4. **Draft `MILESTONE_4_RETROSPECTIVE.md`** with the six
   sections above.

5. **Add `CAPABILITY_MATRIX.md` §7e** with entries for
   every M4 surface.

6. **Flip `IMPLEMENTATION_ROADMAP.md`** — §M4 → SHIPPED,
   §M5 → next.

7. **Flip `MILESTONE_4_PLANNING.md` frontmatter** to
   `status: shipped`.

8. **Ship handoff at
   `docs/handoffs/SESSION_073_m4_closeout.md`** mirroring
   the M3.8 closeout handoff shape.

9. **Overwrite `00-START-NEXT-SESSION.md`** with the M5.0
   planning-pass priority (mirroring SESSION_055 → M3 or
   SESSION_065 → M4 planning-pass invocations).

## Explicit non-goals for SESSION_073

- ❌ Any code change (M4.9 is docs-only per §7 M4.9).
- ❌ Marking M4.8 shipped (it is deferred, not shipped).
- ❌ Any migration.
- ❌ Any frontend change.
- ❌ Adding `docs/roadmap/DEFERRED_IDEAS.md` — the
  deferred items already have homes in the planning /
  retrospective / handoff docs; a separate file is only
  worth adding when the volume genuinely exceeds what
  those homes can hold.

## NEXT TASK

Start SESSION_073 with the read-first list above. Do the
§3 evidence sweep, draft
`MILESTONE_4_RETROSPECTIVE.md`, add
`CAPABILITY_MATRIX.md` §7e, flip the roadmap +
planning-doc frontmatter, ship the M4 closeout handoff,
overwrite start-here for M5.0 planning. Backend baseline
unchanged. Frontend baseline unchanged.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/MILESTONE_4_PLANNING.md` (SESSION_066 +
   SESSION_067 + SESSION_068 amendments)
5. `docs/handoffs/SESSION_072_m4_inc7_operator_ui.md`
6. Prior M4 handoffs (066, 067, 068, 069, 070, 071)
7. `docs/handoffs/SESSION_065_m4_planning.md`
8. `docs/roadmap/MILESTONE_3_RETROSPECTIVE.md` (shape M4.9
   mirrors)
9. `docs/roadmap/MILESTONE_2_RETROSPECTIVE.md`
10. `docs/CAPABILITY_MATRIX.md` §7c + §7d
11. Most recent handoffs
    (`SESSION_072_m4_inc7_operator_ui.md`,
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

## Operational state (post-SESSION_072 — M4.7 operator UI shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged since SESSION_066). Test
  baseline: **2,518 pass**, 1 skipped, 0 fail (unchanged
  since SESSION_071).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. New route + page + 6
  components landed.
- **Frontend (prod):** NONE.
- **DRF admin surface:** 18 M4.6 recon endpoints under
  `/api/dealer-ai/admin/` (unchanged since SESSION_071).
- **Frontend surface:**
  - Route `/dealer-ai-inventory/:stock/recon` inside
    `<RequireAuth>`.
  - `VehicleReconPage.tsx` (~640 lines).
  - `components/recon/` — 6 extracted components:
    WorkOrderStatusBadge, DecisionRow, PartRow,
    VendorPickerModal, VendorCommDraftPanel,
    WorkOrderCard.
  - 18 typed API helpers in `lib/api.ts` covering every
    M4.6 endpoint + full type surface (response +
    request payload types + enum vocabularies).
  - "Recon" button on operator inventory card
    (`InventoryPreviewPage.tsx`).
- **Milestone 4 status:** M4.1 – M4.7 shipped; M4.8
  deferred per §5.i / §5.j; **M4.9 closeout is the next
  in-scope work**. Planning artifact `status: draft`
  (flips at M4.9).
- **Dev DB seeded users:** `smoke_owner` + `smoke_advisor`.
  Neither has `recon_manager` role yet — M4 verification
  should extend `smoke_owner` with an additional
  `recon_manager` membership (or create a `smoke_recon`
  user) for smoke testing.
- **Service surface:**
  - `services/recon.py`: 11 recon + revise_estimate + 4
    parts + 2 Vehicle read helpers + 4 domain errors + 5
    ledger helpers.
  - `services/vendor_comm.py`: 4 functions + 4 domain
    errors.
- **View surface:** `views.py` (M1 – M3, ~2,400 lines) +
  `views_recon.py` (M4.6, ~750 lines).
- **Permission classes:**
  `IsAdvisorForSlug`, `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`,
  `IsDealerOwnerAtActiveDealership`, `ReadOnly`.
