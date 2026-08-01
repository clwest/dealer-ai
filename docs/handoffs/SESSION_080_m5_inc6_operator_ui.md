---
title: "SESSION_080 handoff — Milestone 5 · Increment 6 (operator UI)"
status: historical
type: handoff
date: 2026-08-01
session: 080
milestone: 5
milestone_status: in-progress
increment: 6
increment_status: shipped
commit: TBD
---

# SESSION_080 — Milestone 5 · Increment 6 (M5.6 — operator UI)

## What shipped

The frontend operator surface for vehicle lifecycle. One
new route + one new page + 4 extracted components + 1
shared client-side lifecycle module + 3 typed API
helpers. **Zero backend changes, zero migrations.**

Backend baseline **unchanged: 2,754 pass**, 1 skipped, 0
fail. `npx tsc --noEmit` clean. `npx vite build` clean.

## Route

`/dealer-ai-inventory/:stock/lifecycle` inside
`<RequireAuth>` — registered in `main.tsx` alongside the
M2.7 ledger + M3.7 condition-report + M4.7 recon routes.

## Page

`frontend/src/pages/VehicleLifecyclePage.tsx` (~280 lines
— under the 400-line target because the components carry
most of the visual weight).

State-owning container. Fetches
`/api/dealer-ai/admin/vehicles/:stock/lifecycle/` (M5.4
dashboard endpoint) via `fetchLifecycleDashboard`.

Renders:
- Back link → inventory.
- Current stage card (stage badge + entered_at + entered_by +
  trigger + last_transition_note + hold_reserved return hint
  when applicable).
- Suggested transitions card (SuggestedTransitionsPanel).
- Manual transition card (ManualTransitionForm) — only
  shown when `canWrite` is true.
- Recent events card (StageTimeline).
- Refresh button.

Distinct 400/401/403/404/409 UX via `_humanizeLoadError` +
`_humanizeTransitionError` helpers.

## Extracted components (four)

`frontend/src/components/lifecycle/`:

1. **`StageBadge.tsx`** — reusable stage pill mirroring
   the M4.7 `WorkOrderStatusBadge` shape. 12 stages, each
   with distinct icon + color per `STAGE_META` +
   `STAGE_ICONS`. `null` renders as neutral "No stage" pill.

2. **`StageTimeline.tsx`** — vertical timeline of every
   `VehicleStageEvent` returned by the dashboard.
   Reverse chronological (most-recent first). Each row:
   from → to badges, trigger label, actor username
   ("system" for null actor), entered_at (locale
   string), notes if present, rule_name for `trigger='rule'`.

3. **`SuggestedTransitionsPanel.tsx`** — renders
   `suggested_transitions[]`. Each suggestion is a card
   with the target stage badge + evidence text. Suggestions
   with `unmet_prerequisites.length > 0` render a yellow
   "Waiting on:" hint block instead of the accept button
   — the `photography_to_listing` case (§5.h SESSION_075
   refined). Enabled suggestions render an "Accept
   suggestion" button. Hidden entirely when `canWrite` is
   false.

4. **`ManualTransitionForm.tsx`** — dropdown of allowed
   target stages computed client-side via
   `allowedTargetsForRole(currentStage, activeRole)` +
   reason textarea + submit. Empty state ("No manual
   transitions available from this stage for your role")
   when the role/stage combination has no legal targets.

## Shared client-side lifecycle module

`frontend/src/lib/lifecycle.ts` (~230 lines) — mirrors the
backend's `services/vehicle_lifecycle.py`
`_ALLOWED_TRANSITIONS` + `_STAGE_ROLE_AUTHORITY`:

- `ALLOWED_TRANSITIONS: Record<VehicleStageKey, VehicleStageKey[]>`
  — full transition table per §5.b SESSION_075 refined.
- `STAGE_ROLE_AUTHORITY: Record<VehicleStageKey, RoleKey[]>`
  — role gating per §5.f SESSION_075 refined.
- `canRoleAdvanceTo(role, toStage)` boolean helper.
- `allowedTargetsForRole(currentStage, role) → VehicleStageKey[]`
  — powers the ManualTransitionForm dropdown.
- `STAGE_META` + `getStageMeta(stage)` — labels + Tailwind
  class strings for the StageBadge.

**Backend is authoritative.** A stale client submitting a
disallowed target still receives 403 (role) or 409
(structural) from the M5.2 service. The client-side table
is a UX affordance; the truth is server-side.

## API helpers

`frontend/src/lib/api.ts` gains three helpers + shared
types + a value-vocabulary export:

- `VehicleStageKey` type union (12 stages).
- `VehicleStageTriggerKey` type union (4 triggers).
- `VEHICLE_STAGE_CHOICES` array (mirrors backend value+label pairs).
- `LifecycleActor` / `LifecycleStage` / `LifecycleEvent` /
  `LifecycleSuggestedTransition` / `LifecycleDashboardResponse`
  / `LifecycleTransitionResponse` interfaces.
- `LifecycleManualTransitionPayload` / `LifecycleRuleTransitionPayload`
  request-body types.
- `fetchLifecycleDashboard(stock)` → GET dashboard.
- `postLifecycleManualTransition(stock, {to_stage, notes})`
  → POST manual transition.
- `postLifecycleRuleTransition(stock, {rule_name})` →
  POST rule accept.

All via `authGetJSON` / `authPostJSON` — session cookies +
CSRF handled uniformly per the existing pattern.

## Role gating (§5.f SESSION_075 refined)

- Read-only for viewers who don't hold
  `recon_manager` / `sales_manager` / `dealer_owner`.
- Manual transition affordances gated to
  `WRITE_ROLES = [recon_manager, sales_manager, dealer_owner]`.
- Commercial/disposition targets (`hold_reserved`,
  `wholesale_out`, `company_use`, `off_market`)
  additionally gated to `dealer_owner` +
  `sales_manager` only via the client-side
  `allowedTargetsForRole` filter (which reads
  `STAGE_ROLE_AUTHORITY`).
- Even if a stale UI submits a disallowed target, the
  M5.2 service rejects with
  `UnauthorizedStageTransitionError` → HTTP 403. The
  UI's error-humanizer renders "You don't have permission
  to move this vehicle to that stage" — distinct from
  404 "Vehicle not found".

## Not touched

- **`InventoryPreviewPage.tsx`** stage-badge + "Lifecycle"
  button integration — DEFERRED. The dedicated
  `/lifecycle` route works standalone; adding the badge +
  button to each inventory card requires touching
  `InventoryPreviewPage` which is out of scope for this
  session's clean-shipping boundary. Scoped into M5.7
  or a follow-up.
- Backend service changes.
- Migrations.

## Backend baseline

- **Pre-session:** 2,754 pass, 1 skipped, 0 fail.
- **Post-session:** 2,754 pass, 1 skipped, 0 fail. **No
  change** — M5.6 is frontend-only.

## Frontend verification

- `npx tsc --noEmit` → clean (0 errors, 0 warnings).
- `npx vite build` → clean (605 kB gzip 162 kB — same
  order-of-magnitude bundle size as prior sessions).
- Manual browser walkthrough deferred to operator
  first-live-use per M3.7 / M4.7 honesty precedent.

## Commit hashes

- Session commit: **TBD** (deferred per user directive —
  commit + push after M5.7 closes AND
  `MILESTONE_6_PLANNING.md` is created).

## Exact recommended scope for M5.7

**M5.7 — Verification + closeout.** Documentation-only
session mirroring M3.8 / M4.9.

### Deliverables

1. **§3 compatibility sweep** with evidence citations —
   every invariant from `MILESTONE_5_PLANNING.md` §3
   verified either by a test file citation or a runtime
   probe.

2. **`docs/roadmap/MILESTONE_5_RETROSPECTIVE.md`**
   mirroring M4 retrospective shape:
   - What worked (§0.a amendment discipline; single
     choke-point flip; test-only auto-bootstrap signal;
     distinct domain errors per §0.a item 5).
   - What surfaced during implementation (annotation
     name collision with @property; `_RETAIL_PREPARATION_STAGES`
     including frontline; §5.i customer-language
     deferral; InventoryPreviewPage integration
     deferral).
   - Lessons for M6.
   - Deferrals cataloged.

3. **`docs/CAPABILITY_MATRIX.md` §7f** — "Vehicle
   lifecycle stages (Milestone 5, shipped)". Lists every
   shipped surface: 2 models + 4 domain errors + 5
   service functions + 3 rule evaluators + 3 endpoints
   + 4 UI components + 1 page + 12-stage vocabulary + 4
   triggers.

4. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** — M5
   marked SHIPPED; M6 promoted to "next in sequence."

5. **Planning-doc frontmatter flip** —
   `MILESTONE_5_PLANNING.md` `status: draft` → `shipped`.

6. **`docs/DEALER_KIT_SESSION_START.md`** — refresh the
   "current capabilities" section to mention lifecycle.

7. **Followups list** — capture the deferred items in a
   discoverable place:
   - §5.i customer-language refactor
     (`vehicle_detail`/`vehicle_ask` truthful phrasing).
   - `InventoryPreviewPage` stage-badge + Lifecycle
     button integration.
   - `ad_copy.py` / `pipeline.py` `is_available`
     consumer audit (per §5.e Option D — non-retail
     consumers migrate on their own schedule).
   - `is_available` field removal audit (post-M9 per
     §5.e).

### Boundary

No code changes. Backend baseline: **2,754** unchanged.
Frontend baseline: unchanged.

### Then, per the standing user directive

After M5.7 ships, **create `MILESTONE_6_PLANNING.md`**
in the same shape as M4 / M5 planning docs. M6 is
"Photography + listing generation" per
`IMPLEMENTATION_ROADMAP.md`. When both M5.7 closeout
AND `MILESTONE_6_PLANNING.md` are done, commit + push
per the user's session-open directive.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 5
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_5_PLANNING.md` — as amended
   SESSION_075
6. `docs/handoffs/SESSION_080_m5_inc6_operator_ui.md`
   (this doc)
7. `docs/handoffs/SESSION_079_m5_inc5_retail_gating.md`
8. `docs/handoffs/SESSION_078_m5_inc4_admin_api.md`
9. `docs/handoffs/SESSION_077_m5_inc3_deterministic_rules.md`
10. `docs/handoffs/SESSION_076_m5_inc2_service_state_machine.md`
11. `docs/handoffs/SESSION_075_m5_inc1_core_models.md`

Narrative docs are claims. Rules + research + code are facts.
