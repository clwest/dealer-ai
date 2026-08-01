---
state: active
date: 2026-08-01
last_session_shipped: SESSION_071
milestone_1_status: shipped
milestone_2_status: shipped
milestone_3_status: shipped
milestone_4_status: in-progress
next_session: SESSION_072
next_milestone: 4
next_milestone_name: "Recon automation"
next_increment: 7
next_increment_name: "M4.7 — Operator UI (VehicleReconPage + components)"
---

# Next session — SESSION_072 · Milestone 4 · Increment 7 (M4.7 — operator UI)

> **Milestone 4 · Increment 6 shipped at SESSION_071.**
> Eighteen admin API endpoints under
> `/api/dealer-ai/admin/`, new permission class
> `IsReconManagerSalesManagerOrOwnerAtActiveDealership`,
> new view module `views_recon.py` (~750 lines), 89
> focused endpoint tests. Backend baseline **2,429 →
> 2,518 pass**, 1 skipped, 0 fail. Zero frontend changes.
> Zero migrations. Endpoints delegate entirely to
> `services/recon.py` + `services/vendor_comm.py`.
>
> **SESSION_072 opens M4.7 — the frontend operator UI.**
> New route `/dealer-ai-inventory/:stock/recon` +
> `VehicleReconPage.tsx` + 7 extracted components +
> typed API helpers for every M4.6 endpoint. Backend
> stays frozen — this session is frontend-only.

## Governance layers (all apply, in this order on conflict)

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md`:
   - §1.7 (Vehicle read-model extension —
     `open_work_orders` + `has_recon_decisions`).
   - §5.g provenance rendering + human-approval visual
     distinction.
   - §7 M4.7 (frontend deliverable list + shape).
6. `docs/handoffs/SESSION_071_m4_inc6_admin_api.md` — this
   session's authoritative closeout + "Recommended exact
   scope for SESSION_072".
7. Prior M4 handoffs (066–070).
8. `docs/handoffs/SESSION_063_m3_inc7_operator_ui.md` —
   M3.7 operator UI, the closest analog M4.7 mirrors.
9. `frontend/src/pages/VehicleConditionReportPage.tsx` —
   M3.7's operator page + component extraction pattern.
10. `CLAUDE.md` frontend stack notes — Tailwind v3 +
    shadcn on the radix-nova bridged preset.

## What M4.7 delivers

**Frontend only.** No backend changes. No migrations. No
new endpoints. No AI. No SMTP/SMS. Every screen surface
consumes M4.6 admin API via `authFetch` per
AUTHENTICATION_MODEL.md.

### New route

`/dealer-ai-inventory/:stock/recon` — inside `<RequireAuth>`
in `frontend/src/main.tsx`. Sits alongside M2.7 ledger +
M3.7 condition-report routes.

### Page + extracted components

- `frontend/src/pages/VehicleReconPage.tsx` (~500 line
  target — extract per M3.7 discipline).
- Extracted components in `frontend/src/components/recon/`:
  - `ReconDashboard` — the top-of-page recon summary
    (report + decisions + WO list).
  - `DecisionRow` — one recon decision line with
    must/should/won't visual affordances.
  - `WorkOrderCard` — one WorkOrder tile with all
    metadata + action buttons per current status.
  - `WorkOrderStatusBadge` — reusable status pill
    (draft / approved / in_progress / completed /
    cancelled).
  - `PartRow` — one WorkOrderPart line with
    transition-status dropdown.
  - `VendorCommDraftPanel` — vendor comm draft display +
    approve/edit/mark-sent affordances; renders
    `source_provenance` alongside the draft body so
    operators can see the AI-vs-human boundary.
  - `VendorPickerModal` — modal for selecting a vendor
    when creating an outsourced WO.

### Typed API helpers

Extend `frontend/src/lib/api.ts` with typed helpers for
every M4.6 endpoint. Each helper uses `authFetch` and
maps the domain-error → HTTP status codes M4.6 documented
(404 / 409 / 422 / 502 / 400) into distinct UI states.

### Role gating

Show write affordances only for `recon_manager` /
`sales_manager` / `dealer_owner` (mirrors the M4.6 permission
class). Read-only for other roles that somehow land on the
page. Uses `useAuth()` to gate.

### Provenance rendering

`source_provenance` on vendor comm rows contains
`source_bundle` (the human-authored facts the AI drew
from), `scrubs_fired` (which safety scrubs modified the
output), and `llm_provider`. The UI renders the source
bundle in a collapsible side panel so the operator can
compare the AI draft against the ground truth.

### Distinct HTTP-status UX

- 401 → redirect to `/login?next=<current>`.
- 403 → "You don't have permission to modify this."
- 404 → "Resource not found." (never leak cross-tenant
  existence).
- 409 → "This action conflicts with the current state.
  Refresh and try again." (per-transition text may
  provide more context.)
- 422 → "The AI draft was rejected by the safety scrub.
  Please review your inputs and retry." (specific to
  vendor comm draft.)
- 502 → "The AI service returned no draft. Please retry
  in a moment."

### Draft-vs-approved-vs-sent visual states

Vendor comm rows visually distinct across all four states
(draft, approved, sent, logged). Not merely disabled
buttons — per planning §3 checklist for M4 frontend:
"Draft-vs-approved-vs-sent UI states are visually
distinct (not merely disabled) — same discipline as
M3.7's CompletionBanner."

## What SESSION_072 should do

### Recommended step sequence

1. **Read first (in order):**
   - `docs/roadmap/MILESTONE_4_PLANNING.md` §1.7 +
     §5.g + §7 M4.7.
   - `docs/handoffs/SESSION_071_m4_inc6_admin_api.md` —
     scope block above.
   - `docs/handoffs/SESSION_063_m3_inc7_operator_ui.md` —
     M3.7 operator UI closest analog.
   - `frontend/src/pages/VehicleConditionReportPage.tsx` —
     the M3.7 page pattern.
   - `frontend/src/components/condition-report/` — extracted
     components pattern.
   - `frontend/src/lib/api.ts` — existing helper shape.
   - `frontend/src/main.tsx` — where to register the new
     route.
   - `CLAUDE.md` frontend stack notes — Tailwind v3 +
     shadcn bridge details.

2. **Verify starting state.**
   - `git status` clean (or only pre-existing untracked).
   - `python3 manage.py test dealer_ai` → **2,518 pass, 1
     skipped, 0 fail** (backend frozen for this session).
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.

3. **Add typed API helpers** for every M4.6 endpoint to
   `lib/api.ts`.

4. **Create component files** in
   `frontend/src/components/recon/`. Start with
   `WorkOrderStatusBadge` (simplest; reusable across
   other components). Then `DecisionRow`, `PartRow`,
   `WorkOrderCard`, `VendorCommDraftPanel`,
   `VendorPickerModal`, `ReconDashboard`.

5. **Create `VehicleReconPage.tsx`** that composes the
   components and wires them to the API helpers via
   `useQuery` / `useMutation` (or the existing fetch
   pattern in this codebase — check `VehicleConditionReportPage`
   for the choice).

6. **Register the route** in `main.tsx` inside
   `<RequireAuth>`.

7. **Add the "Recon" button** to the operator inventory
   card wherever the M2.7 "Ledger" + M3.7 "Condition
   Report" buttons live. Match style.

8. **Verify frontend build.**
   - `npx tsc --noEmit` clean.
   - `npx vite build` clean.
   - Manual browser walkthrough NOT required for M4.7 —
     per M3.7 honesty precedent, deferred to operator
     first-live-use.

9. **Ship handoff at
   `docs/handoffs/SESSION_072_m4_inc7_operator_ui.md`**
   mirroring the previous shape.

10. **Overwrite `00-START-NEXT-SESSION.md`** with M4.8
    priority (deferred send subset, or M4.9 closeout if
    M4.8 is not landing per §5.i).

## Explicit non-goals for SESSION_072

- ❌ Do NOT touch backend files.
- ❌ Do NOT add real SMTP/SMS send UI. Planning §5.i
  defers.
- ❌ Do NOT surface QC verification UI — §1.0.QC-GAP
  annotation deferred to future increment.
- ❌ Do NOT add any new endpoint — M4.6 is closed.
- ❌ Do NOT modify any service module.
- ❌ Do NOT introduce any migration.
- ❌ Do NOT add real LLM API calls anywhere.

## NEXT TASK

Start SESSION_072 with the read-first list above. Extend
`lib/api.ts` with typed helpers for all 18 M4.6
endpoints. Build the seven recon components + one
`VehicleReconPage.tsx`. Register the route + add the
inventory-card button. Verify `tsc --noEmit` + `vite
build` clean. Ship the M4.7 handoff.

Backend baseline at SESSION_072 close: **2,518 pass** (unchanged
— frontend-only session).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_4_PLANNING.md` (SESSION_066 +
   SESSION_067 + SESSION_068 amendments; §7 M4.7 anchors)
6. `docs/handoffs/SESSION_071_m4_inc6_admin_api.md`
7. Prior M4 handoffs (066, 067, 068, 069, 070)
8. `docs/handoffs/SESSION_063_m3_inc7_operator_ui.md`
9. `docs/handoffs/SESSION_065_m4_planning.md`
10. `frontend/src/pages/VehicleConditionReportPage.tsx`
11. `CLAUDE.md` frontend stack notes
12. `docs/CAPABILITY_MATRIX.md` §7c + §7d
13. Most recent handoffs
    (`SESSION_071_m4_inc6_admin_api.md`,
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

## Operational state (post-SESSION_071 — M4.6 admin API shipped)

- **Backend (local):** Django on `:8001`. Migrations
  `0001`–`0016` (unchanged since SESSION_066). Test
  baseline: **2,518 pass**, 1 skipped, 0 fail (up from
  2,429; +89 M4.6 endpoint tests).
- **Backend (prod):** NOT active.
- **Frontend (local):** Vite on `:5173`. `tsc --noEmit`
  clean. `vite build` clean. Unchanged.
- **Frontend (prod):** NONE.
- **DRF admin surface:** 18 new M4.6 endpoints under
  `/api/dealer-ai/admin/` for vendors, recon dashboard,
  work orders, parts, and vendor comms. All gated by
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`.
- **Milestone 4 status:** M4.1 + M4.2 + M4.3 + M4.4 +
  M4.5 + M4.6 shipped; frontend operator UI (M4.7) is
  the next in-scope increment.
- **Dev DB seeded users:** `smoke_owner` +
  `smoke_advisor`. Neither has `recon_manager` role yet;
  M4.7 verification should create a `smoke_recon` user
  with `recon_manager` role for smoke testing (or
  extend `smoke_owner` with an additional membership).
- **Service surface:**
  - `services/recon.py`: 11 recon + 1 revise_estimate + 4
    parts + 2 Vehicle read helpers + 4 domain errors + 5
    ledger helpers.
  - `services/vendor_comm.py`: 4 functions + 4 domain
    errors.
- **View surface:** `views.py` (M1 – M3 endpoints, ~2,400
  lines) + `views_recon.py` (M4.6 endpoints, ~750 lines).
- **Permission classes:**
  `IsAdvisorForSlug`, `IsDealerOwnerForAdvisorSlug`,
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6), `IsDealerOwnerAtActiveDealership`, `ReadOnly`.
