---
title: "SESSION_042 handoff — Milestone 1 Increment 4D (administrative authorization + first data scoping)"
status: historical
type: handoff
date: 2026-07-31
session: 042
commits:
  - 17333af  # Increment 4D — permissions + admin gating + service tenant threading + existing test updates + new focused auth/scoping tests + AUTHENTICATION_MODEL §7/§8b updates
  - 91b634c  # SESSION_042 handoff + SESSION_043 pointer
---

# SESSION_042 — Milestone 1 · Increment 4D

## What shipped

Every `/api/dealer-ai/admin/*` endpoint, `manager-chat`, onboarding
profile mutation, and logo upload now requires membership-based
authorization at the caller's active dealership. Every gated
queryset is explicitly tenant-scoped via
`.filter(dealership=get_current_dealership(request))`. Public
branding continues to render on unauthenticated pages
(GET `/onboarding/profile/`). Cross-tenant leakage is prevented at
three levels: the permission classes, the view-level tenant filter,
and the service layer's `dealership=` argument threaded through
every model query in `trends`, `pipeline`, `audit`, and `ad_copy`.

The four-layer separation from `AUTHENTICATION_MODEL.md` §1 held
throughout: Identity (DRF authentication classes, unchanged from
4B) → Authorization (the two new permission classes) → Business
permissions (out of scope for 4D) → Data scoping (explicit
`.filter(dealership=…)` at each view + `dealership=` kwarg on each
service function).

### 1. `dealer_ai/permissions.py` — extended

Two new permission classes plus a small method-based primitive:

- **`IsSalesManagerOrOwnerAtActiveDealership`** — passes when the
  authenticated user holds `sales_manager` OR `dealer_owner` at
  `get_current_dealership(request)`.
- **`IsDealerOwnerAtActiveDealership`** — passes when the
  authenticated user holds `dealer_owner` at
  `get_current_dealership(request)`.
- **`ReadOnly`** — passes any HTTP safe method (GET / HEAD /
  OPTIONS). Composable primitive for "public read, restricted
  write" gates. Composed on onboarding profile as
  `[ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]`
  so branding renders publicly while upserts require dealer_owner.

Private helper `_user_holds_any_role_at(user, dealership, roles)`
centralizes the role lookup so every permission query goes through
one code path. Both admin classes consult
`services.tenancy.get_current_dealership` — no duplicate tenancy
resolution inside permissions.

### 2. Views — 11 endpoints gated + tenant-scoped

Every gated view resolves tenant once at the top:
`dealership = get_current_dealership(request)`. Every subsequent
queryset filters against that value.

- `admin_lead_list` — `IsSalesManagerOrOwner` + `.filter(dealership=…)` on `CustomerLead`.
- `admin_chat_session_list` — same + `ChatSession.objects.filter(dealership=…)`.
- `admin_trends` — `trends_snapshot(dealership=…)`.
- `admin_pipeline` — `pipeline_snapshot(dealership=…)`.
- `admin_ad_copy` — `generate_ad_copy(..., dealership=…)`.
- `admin_salespeople` — `Salesperson.objects.filter(dealership=…)`.
- `admin_lead_detail` — 404 for cross-tenant pk.
- `admin_lead_handoff` — same.
- `admin_lead_assign` — 404 for cross-tenant lead pk **and** 400
  for cross-tenant salesperson body (two-level scoping).
- `admin_audit_events` — `audit_events_snapshot(..., dealership=…)`.
- `manager_chat` — `IsSalesManager…` + throwaway `ChatSession`
  attached to caller's dealership.
- `onboarding_profile` (PUT/PATCH) — `IsDealerOwnerAtActiveDealership`;
  GET stays public via the `ReadOnly` composition.
- `onboarding_logo_upload` — `IsDealerOwnerAtActiveDealership`.

Not touched (correctly): `chat/start`, `chat/message`,
`chat/session/<uuid>/`, `leads/`, `vehicles/<id>/`,
`vehicles/<id>/ask/`, `salespeople/`, `salespeople/<slug>/`, the
advisor endpoints (4C), and the two `demo/*` utilities.

### 3. Service-layer tenant threading

Every model query in the four admin-facing services now accepts an
explicit `dealership` argument. `dealership=None` at each public
entry resolves to `get_default_dealership()` — the fallback is
explicit inside the service, not implicit, so the pre-4D test suite
that omits the argument continues to work byte-for-byte.

- `services/trends.py` — 10 functions threaded (module docstring
  documents the pattern). Every helper now filters its queryset by
  the resolved dealership.
- `services/pipeline.py` — `_compute_stages`, `_compute_demand_vs_supply`,
  `_marketing_cards`, `_trends_for_recommendations`,
  `recommended_actions`, `pipeline_snapshot` all thread through.
- `services/audit.py` — `_preceding_user_message` and
  `audit_events_snapshot` thread through; the sibling lookup can
  never cross dealership boundaries.
- `services/ad_copy.py` — `_resolve_vehicles_for_recommendation`
  and `generate_ad_copy` thread through. An owner at Dealership A
  cannot resolve Dealership B's vehicles even by supplying an
  explicit `vehicle_id`.

### 4. Existing test updates (batched)

Every pre-4D admin test that hit a now-gated endpoint was updated
to authenticate via one of two new `_auth_helpers.py` fixtures:

- `sales_manager_client_at_default()` — `APIClient` authenticated
  as `sales_manager` at the seeded default Dealership. Used by
  admin endpoint tests, manager-chat tests, and ad-copy endpoint
  tests.
- `dealer_owner_client_at_default()` — same but with `dealer_owner`.
  Used by onboarding profile PUT/PATCH and logo upload tests.

Files updated: `test_admin_endpoints.py`,
`test_admin_lead_filters.py`, `test_onboarding_profile.py` (GET
tests untouched — public per §3), `test_manager_chat.py`,
`test_handoff_and_reset.py` (admin_lead_handoff only; demo_reset
untouched — see §7 non-goals), `test_salesperson_and_assignment.py`
(admin_salespeople + admin_lead_assign classes),
`test_ad_copy.py`, `test_pipeline_service.py` (also threaded
`dealership=get_default_dealership()` through direct calls to
`_compute_stages` / `_compute_demand_vs_supply` in the service
tests), `test_audit_service.py`. No assertion semantics were
changed; only the client used to make the request.

### 5. New focused authorization + scoping suite

New file `tests/test_admin_endpoints_auth.py`. 84 focused tests
across 11 admin endpoints plus the public-GET invariant, the
cross-tenant lookup lock, and the cross-tenant assignment
validation.

- **`AdminEndpointAuthMatrixBase`** — mixin exercising six
  authorization outcomes per endpoint (unauth, no-role,
  advisor-only, porter-only, sales_manager, dealer_owner).
  Instantiated by 10 subclasses, one per endpoint.
  `OnboardingProfileMutationAuth` overrides the sales_manager
  case to expect 403 — that endpoint requires dealer_owner
  explicitly.
- **`OnboardingProfileGetIsPublic`** — locks the §3 compatibility
  invariant that GET stays public.
- **`AdminListEndpointsAreTenantScoped`** — cross-tenant fixture
  proving `admin/leads`, `admin/chat-sessions`,
  `admin/salespeople`, `admin/trends`, and `admin/pipeline` each
  return only the active dealership's rows.
- **`AdminLeadDetailFailsClosedAcrossTenants`** — pk lookups for
  another dealership's lead return 404 (not 200, not 403), on
  detail / handoff / assign.
- **`AdminLeadAssignRejectsCrossTenantSalesperson`** — even with
  a same-tenant lead, a cross-tenant salesperson body returns
  400. Locks the two-level scoping on `admin_lead_assign`.
- **`OnboardingLogoUploadRequiresDealerOwner`** — sales_manager
  cannot upload (403); dealer_owner passes auth and hits
  validation (400 for empty body) — distinguishes "auth failed"
  from "auth passed, bad input".

### Test baseline

- **1,361 → 1,445 pass, 1 skipped, 0 fail** (+84 new focused
  tests; zero regressions; no test suppressed with `@skip`).

## Compatibility checklist verification (§3 of MILESTONE_1_PLANNING.md)

Every §3 item verified true after 4D. Key rechecks:

- ✅ **Customer-facing chat + vehicle Q&A stay `AllowAny`.**
  Not touched. The customer never encounters auth.
- ✅ **Public branding renders unauthenticated.**
  `OnboardingProfileGetIsPublic` locks this. `useBrand()` on
  public pages continues to resolve.
- ✅ **`DEFAULT_PERMISSION_CLASSES` still unset.** Locked by
  `test_default_permission_classes_remain_unset` (from 4B).
- ✅ **Chat safety stack untouched.** Baseline includes all
  scrub-stack tests; every one passes.
- ✅ **Payment engine untouched.**
- ✅ **Franchise env-override path unchanged.**
- ✅ **Copper Canyon defaults unchanged.**
- ✅ **Advisor endpoints (4C) unchanged.**
- ✅ **`get_current_dealership` unchanged.** No advisor-specific
  or admin-specific logic added to the tenancy service.
- ✅ **URL shape preserved.** Zero URL changes.
- ✅ **Payload shapes preserved.** Zero serializer changes.

## Files touched

Created:

- `backend/dealer_ai/tests/test_admin_endpoints_auth.py` (84 tests).
- `docs/handoffs/SESSION_042_milestone_1_admin_authorization_and_scoping.md`
  (this file).

Modified:

- `backend/dealer_ai/permissions.py` — added
  `IsSalesManagerOrOwnerAtActiveDealership`,
  `IsDealerOwnerAtActiveDealership`, `ReadOnly`, and the private
  `_user_holds_any_role_at` helper.
- `backend/dealer_ai/views.py` — gated 11 endpoints with
  `@permission_classes(...)`; added
  `dealership = get_current_dealership(request)` + `.filter(dealership=…)`
  or `dealership=` service kwargs everywhere.
- `backend/dealer_ai/services/trends.py` — 10 functions threaded
  with optional `dealership` kwarg.
- `backend/dealer_ai/services/pipeline.py` — 6 functions threaded.
- `backend/dealer_ai/services/audit.py` — 2 functions threaded.
- `backend/dealer_ai/services/ad_copy.py` — 2 functions threaded.
- `backend/dealer_ai/tests/_auth_helpers.py` — added
  `sales_manager_client_at_default` and
  `dealer_owner_client_at_default`.
- 9 test files updated to authenticate previously-anonymous admin
  calls (list in §4 above).
- `docs/roadmap/AUTHENTICATION_MODEL.md` — §7 concrete class names +
  new §8b (tenant-scoped query patterns).
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_043
  (Increment 4E).

Not touched (correctly):

- `settings.py` — DRF defaults unchanged since 4B.
- `services/tenancy.py` — no admin-specific logic added.
- 16-stage safety pipeline — untouched.
- Frontend — login UI is 4E.
- Customer-facing chat / vehicles / lead-creation endpoints.
- `demo/reset/` + `demo/scenarios/` (see Deferred below).
- `docs/CAPABILITY_MATRIX.md` — Milestone 1 close is 4F.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7 — flips at 4F.

## Deferred (noted, not shipped)

- **`demo/reset/` + `demo/scenarios/` remain ungated.** The scope
  brief was explicit: "Apply authorization only to dealership
  administration endpoints identified in the roadmap." Neither is
  listed in `MILESTONE_1_PLANNING.md` §7 · 4D. These endpoints
  wipe demo state across the entire database (not tenant-scoped
  by design) and would need a separate scope decision — either
  gate them under `dealer_owner` and keep the cross-tenant wipe
  semantics, or scope them per-tenant. Recorded here for the
  reader who will eventually pick this up; a candidate for a
  small post-Milestone-1 hardening pass.

## Deviation from plan — one intentional refactor recorded

The initial focused-test matrix included two "wrong tenant" cases
(`sales_manager_at_wrong_tenant` and `dealer_owner_at_wrong_tenant`).
Both failed with 200 status codes; investigation showed why: admin
endpoints derive their active dealership from the caller's
membership, so a "wrong tenant" scenario is not expressible for
this URL-shape family. The user IS acting as their own tenant. The
tests were removed from the shared matrix and replaced with
focused cross-tenant *data* scoping tests
(`AdminListEndpointsAreTenantScoped`,
`AdminLeadDetailFailsClosedAcrossTenants`,
`AdminLeadAssignRejectsCrossTenantSalesperson`), which correctly
express "an admin at Dealership B cannot read/mutate Dealership A
data" as a data-layer invariant rather than a permission-layer
invariant. The mixin's docstring records this distinction so
future admin surfaces reuse the correct pattern.

## Recommended scope for SESSION_043 — Increment 4E

**Goal:** frontend login UI + shared `authFetch()` helper so real
sessions can drive the operator pages that 4C/4D now gate.

**In scope** (per `MILESTONE_1_PLANNING.md` §7 · 4E):

1. Greenfield `frontend/src/pages/Login.tsx` (or equivalent under
   the existing routing structure). Simple username + password
   form posting to a DRF session-auth endpoint (add a small
   login/logout view pair in `dealer_ai/views.py` if one does not
   already exist — Django's admin login is not the customer-facing
   flow).
2. Shared `authFetch()` helper: injects the `Authorization` /
   session cookie header, handles 401 by redirecting to `/login`.
3. Every operator page (leads admin, coaching, onboarding, advisor
   workspace) uses `authFetch`. Public pages (`/`, `/assistant`,
   `/showroom`, `/embed/assistant`) do NOT.
4. Persist auth state via a lightweight React context / hook, not
   a heavyweight state library.
5. Verify via `npx tsc --noEmit`, `npx vite build`, and manual
   browser smoke: log in → hit leads admin → verify data → log
   out. Ideally exercise the composed 4C/4D flow end-to-end.

**Out of scope for 4E**:

- Compatibility sweep + Milestone 1 close (4F).
- Password-reset UI (deferred; not in roadmap).
- SSO / MFA (§5 deferred).
- Gating the `demo/*` endpoints (see Deferred above; separate
  scope decision).

## Anchors that win on conflict

Unchanged from SESSION_041 close:

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing)
5. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model)
6. `docs/BUSINESS_DOMAIN_MAP.md`
7. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs (this one + `SESSION_041_*.md`).
10. `git log --oneline -25`

## Operational state at session close

- **Backend (local):** Django on `:8001`. Migrations `0001`–`0011`
  applied; `authtoken` migrations applied. Default `Dealership`
  row exists (`slug='default'`).
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
- **Frontend (local):** Vite on `:5173`. Untouched this session.
- **Test baseline:** 1,445 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`;
  `DEFAULT_PERMISSION_CLASSES` still unset.
- **Endpoint-level permission classes shipped:** advisor workspace
  (4C) + advisor follow-up (4C) + 11 admin surfaces (4D).
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- `docs/roadmap/DEFERRED_IDEAS.md` — still does not exist. The
  ungated `demo/*` endpoints are recorded above and in the next-
  session pointer; no separate deferred-ideas doc needed yet.

*End of SESSION_042 handoff.*
