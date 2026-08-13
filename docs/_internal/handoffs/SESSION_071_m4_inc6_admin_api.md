---
title: "SESSION_071 handoff — Milestone 4 · Increment 6 (admin API + permission matrix)"
status: historical
type: handoff
date: 2026-08-01
session: 071
milestone: 4
milestone_status: in-progress
increment: 6
increment_status: shipped
commit: b031f09
---

# SESSION_071 — Milestone 4 · Increment 6 (M4.6 — admin API + permission matrix)

## What shipped

New DRF admin API for the M4 recon subsystem. Eighteen
endpoints registered under `/api/dealer-ai/admin/`
(vendor CRUD, recon dashboard, recon decision, WorkOrder
lifecycle, WorkOrder findings attach/detach, WorkOrder
patch/revise-estimate, WorkOrderPart create/patch/delete,
VendorCommunication draft/approve/mark-sent/log). All
routes delegate entirely to `services/recon.py` +
`services/vendor_comm.py` — zero business logic in the
view layer.

New permission class
`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
in `dealer_ai/permissions.py` — composed from existing
`recon_manager` + `sales_manager` + `dealer_owner`
roles per planning §5.f. Every M4.6 endpoint uses this
class. Advisor / porter / f_and_i_manager / collections
all receive 403 (locked by the per-endpoint permission
matrix).

New view module `dealer_ai/views_recon.py` (~750 lines)
holding all M4.6 endpoints, request serializers, response
projections, cross-tenant lookup helpers, and the
domain-error → HTTP status translator. Keeps the primary
`views.py` from growing beyond ~2,400 lines.

89 focused endpoint tests in
`backend/dealer_ai/tests/test_admin_recon_endpoints.py`.
**Zero migrations. Zero frontend changes. Zero real LLM
API calls in tests** (MockLLMProvider throughout).

## Session preamble

No planning refinements needed. §5.f locked the permission
matrix; §7 M4.6 locked the endpoint list; the
SESSION_066–070 amendments to the planning artifact fully
anchored M4.6.

## Read-first pass performed

1. `docs/roadmap/MILESTONE_4_PLANNING.md` §5.f + §7 M4.6.
2. `docs/handoffs/SESSION_070_m4_inc5_vendor_comm.md`
   scope block.
3. `backend/dealer_ai/permissions.py` — the existing
   `IsSalesManagerOrOwnerAtActiveDealership` composition
   pattern.
4. `backend/dealer_ai/views.py` — M2.6 admin ledger
   endpoints + M3.6 condition-report endpoints
   (`admin_condition_report_create`, `_complete`,
   `_finding_create`). Note the tenant-scoping +
   cross-tenant-fail-closed pattern.
5. `backend/dealer_ai/urls.py` — route registration
   pattern.
6. `backend/dealer_ai/tests/test_admin_endpoints_auth.py`
   `AdminEndpointAuthMatrixBase` mixin — the shape M4.6
   mirrors (extended with `recon_manager` +
   `f_and_i_manager` + `collections` cases).

## Concrete deliverables

### Permission class

`IsReconManagerSalesManagerOrOwnerAtActiveDealership` in
`dealer_ai/permissions.py`. Composed via
`_user_holds_any_role_at(user, dealership, (RECON_MANAGER,
SALES_MANAGER, DEALER_OWNER))`. Mirrors the shape of
`IsSalesManagerOrOwnerAtActiveDealership`. `message`
string is operator-appropriate.

### New view module

`backend/dealer_ai/views_recon.py`. Eighteen `@api_view`
functions + request serializers + response projections +
lookup helpers + `_map_service_error` translator.

**Endpoints (per planning §7 M4.6):**

Vendor CRUD:
- `GET/POST admin/vendors/` — list + create.
- `GET/PATCH admin/vendors/<slug>/` — retrieve + patch. No
  DELETE (PROTECT contract from §5.b; deactivate via
  `is_active=False`).

Recon dashboard:
- `GET admin/vehicles/<stock>/recon/` — latest completed
  condition report + decisions + work orders + parts +
  communications.

Recon decision:
- `POST admin/vehicles/<stock>/findings/<id>/recon-decision/`
  — create/upsert per M4.2 reconsideration policy.

WorkOrder lifecycle:
- `POST admin/vehicles/<stock>/work-orders/` — create draft.
- `POST admin/work-orders/<id>/approve/` — draft → approved.
- `POST admin/work-orders/<id>/start/` — approved →
  in_progress.
- `POST admin/work-orders/<id>/complete/` — in_progress →
  completed. Requires `actual_cost`.
- `POST admin/work-orders/<id>/cancel/` — any nonterminal
  → cancelled.
- `PATCH admin/work-orders/<id>/` — revise-estimate via
  `new_estimated_cost` (M4.3 flow).
- `POST admin/work-orders/<id>/findings/` — attach.
- `DELETE admin/work-orders/<id>/findings/<fid>/` —
  detach.

Parts:
- `POST admin/work-orders/<id>/parts/` — add part.
- `PATCH admin/parts/<id>/` — update (whitelist) OR
  transition status (`new_status`). Mixing both in one
  request is refused with 400 to keep intent explicit.
- `DELETE admin/parts/<id>/` — draft-only.

Vendor communications:
- `POST admin/work-orders/<id>/comms/draft/` — AI-draft
  new outbound comm.
- `POST admin/comms/<id>/approve/` — draft → approved.
- `POST admin/comms/<id>/mark-sent/` — approved → sent.
- `POST admin/comms/log/` — operator-recorded off-system
  comm.

### Domain-error → HTTP status mapping

Locked at `_map_service_error`:

| Error class                              | HTTP status |
|------------------------------------------|-------------|
| `CrossTenantReconError`                  | 404         |
| `CrossTenantVendorCommError`             | 404         |
| `ReconImmutableError`                    | 409         |
| `VendorCommImmutableError`               | 409         |
| `InvalidReconTransitionError`            | 409         |
| `IncompleteConditionReportError`         | 409         |
| `ReconFactScrubDroppedError`             | 422         |
| `EmptyDraftError`                        | 502         |
| `ValueError`                             | 400         |

Cross-tenant maps to 404 (not 403) so we never leak
whether a resource exists in another dealership.

### Response projections

Five projection helpers (`_project_vendor`,
`_project_finding_link`, `_project_part`,
`_project_work_order`, `_project_comm`,
`_project_recon_decision`). Comm projection includes
`source_provenance` so the M4.7 UI can render the source
bundle + scrubs fired + LLM provider alongside the draft.

### Cross-tenant lookup helpers

Six `_lookup_*_or_404` functions. Each queries with an
explicit `dealership=<current>` filter. Cross-tenant
access returns `None` → 404 (same shape as M2.6 / M3.6).
`_lookup_user_at_dealership_or_none` prevents cross-tenant
assignee assignment (an operator at Dealership A cannot
assign a WO to a user at Dealership B).

### URL routes

18 new routes registered in `dealer_ai/urls.py`. Every
route has a `dealer_ai:*` reverse name locked by the
`M46RoutesRegistered` regression test.

### Tests (89 new in `test_admin_recon_endpoints.py`)

**Permission matrix (5 endpoints × 9 outcomes = 45
tests)** via `ReconAdminEndpointAuthMatrixBase` mixin
covering `admin-vendor-list` (GET + POST),
`admin-recon-dashboard`, `admin-work-order-create`,
`admin-comm-log`. Each outcome:

- unauth → 401/403
- no-role → 403
- advisor → 403
- porter → 403
- f_and_i_manager → 403
- collections → 403
- recon_manager → OK
- sales_manager → OK
- dealer_owner → OK

**Vendor CRUD (7 tests)** — create+list, detail, deactivate
patch, cross-tenant 404, list tenant scoping, no DELETE
surface (405), duplicate slug conflict.

**Recon dashboard (3 tests)** — empty, populated, cross-
tenant 404.

**WorkOrder lifecycle (13 tests)** — create in-house +
outsourced, outsourced-without-vendor 409,
unknown-vendor-slug 404, full lifecycle (create → attach
→ approve → start → complete), approve without findings
409, complete without actual_cost 400, double-start 409,
cancel-approved-requires-reason 400, cancel-draft-no-
reason OK, revise-estimate via PATCH, cross-tenant 404 on
approve, detach finding on draft.

**Parts (7 tests)** — add, update via PATCH, transition
via PATCH, mixed-update-and-status 400, delete draft OK,
delete approved 409, cross-tenant PATCH 404.

**Vendor comm (8 tests)** — approve endpoint, mark_sent
with edited content, mark_sent default uses draft_content,
mark_sent from draft 409, log with WO, log null WO, log
missing body 400, cross-tenant approve 404, provenance
visible in dashboard response.

**Recon decision (3 tests)** — create, draft-report 409,
cross-tenant 404.

**Regression (1 test)** — recon data does not leak on
public onboarding profile endpoint.

**Module (1 test)** — every M4.6 URL name resolves.

**Total new tests: 89.**

## Verification evidence

- `python3 manage.py test dealer_ai` → **2,518 pass, 1
  skipped, 0 fail** (up from 2,429; +89 M4.6 tests).
- `python3 manage.py check` → clean.
- `python3 manage.py makemigrations --check --dry-run` →
  "No changes detected."
- **No new migration files.** No frontend files changed.

## Compatibility

Preserved unchanged:

- **M1/M2/M3 substrate.** All APIs unchanged.
- **M4.1 – M4.5 substrate.** Every service function
  consumed unchanged. Delegate-only view layer means M4.6
  cannot silently drift service semantics.
- **Existing permission classes.** No changes; the new
  class is additive.
- **Existing endpoints.** All M1 – M3 endpoints
  unchanged (no route conflicts; all M4.6 routes are new
  paths).
- **Existing serializers.** No changes to
  `serializers.py`; M4.6 request serializers live
  co-located with the views in `views_recon.py`.
- **Frontend contracts.** No frontend files touched.

## Explicitly out of scope for M4.6

- ❌ Frontend — M4.7.
- ❌ Any new service module (M4.6 delegates entirely to
  M4.2 – M4.5 services).
- ❌ Modifying M4.1 – M4.5 substrate.
- ❌ Outbound SMTP / SMS send (planning §5.i deferred).
- ❌ New domain errors — use the ones the services expose.
- ❌ QC verification fields / endpoints (§1.0.QC-GAP
  annotation defers to a future increment).

## Files changed

- `backend/dealer_ai/permissions.py` — imports extended
  (`ROLE_RECON_MANAGER`); new
  `IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  class added before
  `IsDealerOwnerAtActiveDealership`.
- `backend/dealer_ai/views_recon.py` — new file, ~750
  lines.
- `backend/dealer_ai/urls.py` — imports extended
  (`views_recon`); 18 new `path()` entries registered
  after the M3.6 photo local-upload route.
- `backend/dealer_ai/tests/test_admin_recon_endpoints.py`
  — new file, ~1,100 lines (89 tests).
- `docs/handoffs/SESSION_071_m4_inc6_admin_api.md` —
  this handoff.
- `00-START-NEXT-SESSION.md` — overwritten with SESSION_072
  = M4.7 priority.

## Recommended exact scope for SESSION_072 (M4.7 — operator UI)

Per `MILESTONE_4_PLANNING.md` §7 M4.7:

**Scope.**

- New route `/dealer-ai-inventory/:stock/recon` inside
  `<RequireAuth>` in `frontend/src/main.tsx`.
- `frontend/src/pages/VehicleReconPage.tsx` (~500 lines
  target — extract components per M3.7 discipline).
- Small extracted components in
  `frontend/src/components/recon/`:
  - `ReconDashboard`
  - `DecisionRow`
  - `WorkOrderCard`
  - `WorkOrderStatusBadge`
  - `PartRow`
  - `VendorCommDraftPanel`
  - `VendorPickerModal`
- Typed API helpers in `frontend/src/lib/api.ts` for every
  M4.6 endpoint.
- "Recon" button on operator inventory card (beside M2.7
  "Ledger" + M3.7 "Condition Report").
- Role gating (recon_manager + sales_manager + dealer_owner
  see write affordances).
- Draft-vs-approved-vs-sent visual states.
- `source_provenance` rendered on vendor-comm drafts (AI
  prose sentences visually distinct).
- Distinct 401 / 403 / 404 / 409 / 422 / 502 UX.

**Verification.** `npx tsc --noEmit` clean; `npx vite
build` clean. Backend baseline unchanged. Manual browser
walkthrough deferred to operator first-live-use per M3.7
honesty precedent.

**Boundary.** Frontend files only. Backend baseline
**2,518 pass** unchanged.

**Explicit non-goals for M4.7:**

- ❌ Do NOT touch backend files.
- ❌ Do NOT add real SMTP/SMS send UI. Planning §5.i
  deferred.
- ❌ Do NOT surface QC verification UI (§1.0.QC-GAP
  annotation deferred).

## Anchors that win on conflict for SESSION_072

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 4
4. `docs/roadmap/MILESTONE_4_PLANNING.md` §7 M4.7
5. `docs/handoffs/SESSION_071_m4_inc6_admin_api.md` — this
   handoff.
6. Prior M4 handoffs (066–070).
7. `docs/handoffs/SESSION_063_m3_inc7_operator_ui.md` — the
   M3.7 shape M4.7 mirrors most closely.
8. `frontend/src/pages/VehicleConditionReportPage.tsx` — the
   M3.7 operator page pattern.
9. CLAUDE.md frontend stack notes (Tailwind v3 + shadcn on
   the radix-nova preset bridge).
