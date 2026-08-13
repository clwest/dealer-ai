---
title: "SESSION_041 handoff — Milestone 1 Increment 4C (advisor workspace authorization)"
status: historical
type: handoff
date: 2026-07-31
session: 041
commits:
  - 76d625b  # Increment 4C — permissions.py + advisor view gating + tests + AUTHENTICATION_MODEL §7 update
  - b1816a9  # SESSION_041 handoff + SESSION_042 pointer
---

# SESSION_041 — Milestone 1 · Increment 4C

## What shipped

Advisor slug-obscurity fully replaced by explicit, membership-based
authorization. The advisor workspace and follow-up endpoints now
require an authenticated caller who either **is** the advisor
identified by the URL slug (via the `Salesperson.user` link from
4A) or is a **`dealer_owner` at the same dealership**. Cross-
dealership access is prevented — an owner of Dealership A cannot
reach Dealership B's advisors under any composition.

The layer separation held: Identity (DRF auth) → Authorization
(permission classes) → Business permissions (out of scope for 4C) →
Data scoping (the pre-existing lead-ownership 403 preserved
verbatim).

### 1. `dealer_ai/permissions.py` — new module

Two focused, reusable permission classes plus a module-level
docstring naming the layer separation:

- **`IsAdvisorForSlug`** — the authenticated user's linked
  `Salesperson.slug` matches the URL kwarg `slug`. Silent `False`
  on anonymous / missing link / mismatch / missing kwarg.
- **`IsDealerOwnerForAdvisorSlug`** — the authenticated user holds
  `dealer_owner` role at the dealership that owns the Salesperson
  identified by the URL slug. Silent `False` on unknown slug (no
  information leakage via differential exceptions).

Both classes are `BasePermission` subclasses composable via DRF's
`&` and `|` operators. No `SameDealership` mixin — the target-
tenant discovery (Salesperson slug → dealership) is inherent to
each class, keeping the composition at the view layer trivial.

### 2. Views gated

`backend/dealer_ai/views.py`:

- `advisor_workspace(request, slug)` — added `@permission_classes(
  [IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)])`.
- `advisor_follow_up(request, slug, lead_id)` — same composition.
- Docstrings updated to describe the new authorization layer and
  the preserved data-scoping 403 on lead ownership.

URL shape, request body, and response body are byte-for-byte
unchanged. Frontend routing continues to resolve
`/dealer-ai-advisor/:slug` without modification.

### 3. `tests/_auth_helpers.py` — shared fixtures

New module. Small helpers so every authorization test expresses
"who is calling" in one line:

- `make_dealership(slug, name=None)` — a second dealership for
  cross-tenant coverage.
- `make_user(username, password)` — plain auth user.
- `make_advisor_user(slug, dealership, ...)` — User + linked
  Salesperson with the `user` OneToOne set. Returns
  `(user, salesperson)`.
- `make_membership(user, dealership, role)` — a
  `UserDealershipRole` row.
- `authenticated_client(user)` — DRF `APIClient` pre-authenticated
  via `force_authenticate` (bypasses the login endpoint — that's
  Increment 4E).

### 4. Test suite

Test baseline: **1,349 → 1,361** pass (+12 net), 1 skipped, 0 fail.

- **New:** `test_advisor_workspace_auth.py` — 14 focused permission
  tests:
  - `AdvisorWorkspaceAuthorization` (7) — the six required
    outcomes (unauth, correct advisor, cross-dealership advisor,
    same-dealership dealer_owner, cross-dealership dealer_owner,
    authenticated user with no relationship) plus a lock that
    "role=advisor membership alone is not sufficient" (must have
    the Salesperson.user link matching the slug).
  - `AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs` (1) —
    locks the "no information leakage via differential status
    codes" invariant. Unknown slug returns 403, not 404.
  - `AdvisorFollowUpAuthorization` (6) — the same authorization
    matrix on the follow-up endpoint, plus explicit coverage that
    the lead-ownership 403 is still enforced for authorized
    dealer_owners (layer separation lock).
- **Updated:** `test_salesperson_and_assignment.py::AdvisorWorkspaceEndpointTests` — happy path now authenticates
  via `authenticated_client(maria_user)`. The pre-4C
  `test_workspace_404_for_unknown_slug` was retired (its
  invariant — slug obscurity as access control — is the exact
  thing 4C removes; the new focused suite covers unknown-slug
  behavior under real auth). The `test_workspace_404_for_inactive_advisor`
  was reframed as
  `test_workspace_deactivated_advisor_is_not_leaked_to_owners` —
  the new invariant is 403 (no leakage), not 404 (which came
  from slug obscurity).
- **Updated:** `test_follow_up.py::FollowUpEndpointTests` — happy
  paths authenticate; `test_403_when_lead_belongs_to_other_advisor`
  reframed under real auth (`other` authenticates as themselves,
  hits their own slug, ownership check fires). Pre-4C
  `test_404_for_unknown_advisor` retired for the same reason
  above.

### 5. Docs

- **Updated:** `docs/roadmap/AUTHENTICATION_MODEL.md` §7 replaced
  the placeholder class names with the shipped `IsAdvisorForSlug`
  and `IsDealerOwnerForAdvisorSlug`. Added the composition applied
  at the view layer and the "no information leakage via
  differential status codes" invariant.
- **No new docs.** Update-in-place per DOC_GOVERNANCE.md.

## Compatibility checklist verification (§3 of MILESTONE_1_PLANNING.md)

Every §3 item verified true after 4C:

- ✅ **Existing advisor workflow.** Correct advisor (authenticated,
  linked to their Salesperson row) still sees own leads only.
  Follow-up drafts still pass through `invented_appointment`
  scrub — the follow-up service is untouched.
- ✅ **403 lead-ownership check preserved.** `lead.assigned_to_id
  != sp.pk` at views.py:529 is byte-for-byte unchanged and
  exercised by two tests (one existing, one new).
- ✅ **URL shape preserved.** `/api/dealer-ai/advisor/<slug>/*`
  and `dealer_ai:advisor-workspace` / `dealer_ai:advisor-follow-up`
  reverse names unchanged.
- ✅ **No other endpoint touched.** Customer chat, embed frame,
  vehicle Q&A, onboarding profile, admin endpoints — all
  behavior-identical to SESSION_040 close.
- ✅ **Chat safety stack untouched** — full baseline passes.
- ✅ **Payment engine untouched.**
- ✅ **Franchise env-override path unchanged.**
- ✅ **Copper Canyon defaults unchanged.**
- ✅ **`DEFAULT_PERMISSION_CLASSES` still unset** — locked by
  `test_default_permission_classes_remain_unset` from SESSION_040.
- ✅ **Tenancy service unchanged.** `get_current_dealership` and
  `get_active_membership` remain generic — no advisor-specific
  logic leaked into the tenancy layer per the review guidance.

## Files touched

Created:

- `backend/dealer_ai/permissions.py` (67 lines, 2 classes).
- `backend/dealer_ai/tests/_auth_helpers.py` (5 helpers).
- `backend/dealer_ai/tests/test_advisor_workspace_auth.py`
  (14 tests, 3 classes).
- `docs/handoffs/SESSION_041_milestone_1_advisor_authorization.md`
  (this file).

Modified:

- `backend/dealer_ai/views.py` — added imports for
  `permission_classes`, `IsAuthenticated`,
  `IsAdvisorForSlug`, `IsDealerOwnerForAdvisorSlug`; added
  `@permission_classes(...)` decorators to `advisor_workspace`
  and `advisor_follow_up`; refreshed both docstrings.
- `backend/dealer_ai/tests/test_salesperson_and_assignment.py` —
  authenticated happy-path advisor tests; reframed the
  deactivated-advisor test; removed the retired
  unknown-slug-404 test.
- `backend/dealer_ai/tests/test_follow_up.py` — authenticated
  happy-path follow-up tests; reframed the cross-advisor 403 test;
  removed the retired unknown-advisor-404 test.
- `docs/roadmap/AUTHENTICATION_MODEL.md` §7 — concrete class names
  + composition + information-leakage invariant.
- `00-START-NEXT-SESSION.md` — overwritten to point at SESSION_042
  (Increment 4D).

Not touched (correctly):

- `settings.py` — DRF defaults unchanged since SESSION_040.
- `services/tenancy.py` — no advisor-specific logic added per the
  review guidance.
- Any other view — endpoint gating for admin is 4D.
- Frontend — login UI is 4E.
- 16-stage safety pipeline — untouched.
- `docs/CAPABILITY_MATRIX.md` — Milestone 1 close is 4F.

## Deviation from plan — one intentional invariant change

The pre-4C behavior returned **404** for unknown advisor slugs and
for deactivated advisor slugs. Under real authorization the
resolver returns **403** to authenticated callers instead —
information leakage via differential status codes is a
weaker-than-necessary posture and the "no leakage" invariant is
now locked by `AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs`
and the reframed
`test_workspace_deactivated_advisor_is_not_leaked_to_owners`.

The affected historical tests measured slug-obscurity behavior
that 4C explicitly replaces (per §Milestone 1 Gap in the roadmap:
*"Advisor workspace slug-by-obscurity replaced by real auth."*).
Retiring them was not a coverage regression — the equivalent
outcomes are covered by the new focused suite under the new
authorization semantics.

## Recommended scope for SESSION_042 — Increment 4D

**Goal:** admin endpoint gating + queryset scoping across every
`/api/dealer-ai/admin/*` route + onboarding profile mutation
(`IsDealerOwner`). Customer-facing endpoints stay `AllowAny`.

**In scope** (per `MILESTONE_1_PLANNING.md` §7 · 4D):

1. New permission classes in `dealer_ai/permissions.py`:
   - `IsSalesManagerOrOwnerAtActiveDealership` — passes when the
     authenticated user holds `sales_manager` OR `dealer_owner`
     role at `get_current_dealership(request)`.
   - `IsDealerOwnerAtActiveDealership` — passes when the
     authenticated user holds `dealer_owner` role at
     `get_current_dealership(request)`.
2. Apply `IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership`
   to every admin endpoint: `admin/pipeline`, `admin/leads`,
   `admin/lead/<id>/*`, `admin/salespeople`, `admin/audit-events`,
   `admin/trends`, `admin/ad-copy`, `manager-chat`.
3. Apply `IsAuthenticated & IsDealerOwnerAtActiveDealership` to
   `onboarding/profile` (PUT/PATCH) and `onboarding/profile/logo/`.
   Keep the GET permissive so branding (`useBrand()`) still
   resolves without a logged-in user (per §3 checklist).
4. **Queryset scoping.** Every `Lead.objects.*`,
   `ChatSession.objects.*`, `Salesperson.objects.*` inside those
   endpoints gains `.filter(dealership=get_current_dealership(request))`.
   This is the Data Scoping layer landing on the admin surface.
5. **Test coverage.** For each admin endpoint: unauth → 401/403,
   wrong-role (e.g. authenticated advisor) → 403, wrong-tenant
   (correct role at a *different* dealership) → 403, correct → 200.
   Plus queryset scoping tests: an admin at Dealership A sees only
   Dealership A's rows.
6. Reuse `tests/_auth_helpers.py` — extend if needed, do not
   duplicate.

**Out of scope for 4D**:

- Frontend login (4E).
- Compatibility sweep + Milestone 1 close (4F).
- Tenant-scoped uniqueness on any model.

## Anchors that win on conflict

Unchanged from SESSION_040 close:

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing)
5. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model)
6. `docs/BUSINESS_DOMAIN_MAP.md`
7. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs (this one + `SESSION_040_*.md`).
10. `git log --oneline -25`

## Operational state at session close

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_ai/`. Migrations `0001`–`0011` applied. Default
  `Dealership` row present (`slug='default'`). No `Token` or live
  `UserDealershipRole` rows in dev DB; the dev DB was not
  provisioned with a real dealer_owner user this session because
  the authorization surface is exercised entirely by focused tests.
- **Backend (prod):** `vehicle-match-api.onrender.com` — not active.
- **Frontend (local):** Vite on `:5173`. Untouched this session.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,361 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`
  (unchanged since 4B); `DEFAULT_PERMISSION_CLASSES` unset.
- **Endpoint-level permission classes shipped:** advisor workspace
  + advisor follow-up only. Every other endpoint still uses the
  DRF default (`AllowAny`).
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- `docs/roadmap/DEFERRED_IDEAS.md` — still does not exist. Nothing
  out-of-milestone surfaced during 4C.

*End of SESSION_041 handoff.*
