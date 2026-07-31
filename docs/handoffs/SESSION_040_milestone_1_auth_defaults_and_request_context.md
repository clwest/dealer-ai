---
title: "SESSION_040 handoff — Milestone 1 Increment 4B (DRF auth defaults + request-context tenancy)"
status: historical
type: handoff
date: 2026-07-31
session: 040
commits:
  - dc24ab6  # docs — record multi-role design rationale + refine 4B contract
  - 7fc415f  # Increment 4B — DRF auth defaults + get_current_dealership + tests
  - <fill after docs commit>  # AUTHENTICATION_MODEL.md + SESSION_040 handoff + SESSION_041 pointer
---

# SESSION_040 — Milestone 1 · Increment 4B

## What shipped

The authentication + authorization scaffolding for Milestone 1.
Requests now *carry* identity when credentials are present; a
distinct request-context resolver answers *which dealership is this
user acting within*. **No endpoint tightens** — the DRF permission
default remains `AllowAny` per Increment 4B contract. Enforcement is
4C (advisor) + 4D (admin).

The three-layer separation is preserved (see the new
`docs/roadmap/AUTHENTICATION_MODEL.md` for the canonical description):

- **Identity** — DRF authentication classes (this session).
- **Authorization / tenant scope** —
  `services.tenancy.get_current_dealership` (this session).
- **Business permissions** — DRF permission classes per endpoint
  (4C/4D).

### 1. DRF authentication defaults — `backend/dealer_kit/settings.py`

- `rest_framework.authtoken` added to `INSTALLED_APPS`. Provides the
  `Token` model consumed by `TokenAuthentication`.
- `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
  "SessionAuthentication", "TokenAuthentication"]`.
  `SessionAuthentication` first — the customer chat + embed frame
  stay cookie-friendly and this is the mechanism 4E's login form will
  use. `TokenAuthentication` second — enables scripted / API-client
  access via `manage.py drf_create_token`.
- **`DEFAULT_PERMISSION_CLASSES` is intentionally NOT set.** The DRF
  default (`AllowAny`) stands so no currently-public endpoint
  silently gains a 401. Locked by
  `test_default_permission_classes_remain_unset`.

### 2. `services.tenancy` extension — two helpers, layered

Extended `backend/dealer_ai/services/tenancy.py` with:

- **`get_active_membership(user)`** — the **extension seam** for
  dealership switching. Increment 4B ships the deterministic
  single-membership implementation; future dealership-picker UI
  replaces the body of *this helper* without touching the composer
  or any downstream caller. Returns `None` for anonymous /
  `None` / no-memberships. Returns the sole membership when there
  is exactly one; returns deterministic `.first()` by ordering
  when there are several.
- **`get_current_dealership(request)`** — the composer. Priority
  order: authenticated identity → `X-Dealership-Slug` header →
  `get_default_dealership()`. Never returns `None`; never raises on
  unknown header slugs (the header is a hint, not a contract).
- Module docstring rewritten to describe the four-layer separation
  (Identity / Authorization / Business permissions / Data scoping).

### 3. `AUTHENTICATION_MODEL.md` — canonical reference doc

New file `docs/roadmap/AUTHENTICATION_MODEL.md`. Ten sections:
four-layer overview, Identity, Membership, Active dealership
resolution, Roles, Authorization, Business permissions, Future
dealership switching, Out-of-scope, Anchors. Written to be the
single reference every future authentication decision consults so
the model does not get rediscovered milestone-by-milestone.

### 4. Test suite

New file `backend/dealer_ai/tests/test_current_dealership.py`. Three
classes, 16 tests:

- `ActiveMembershipHelper` (5 tests) — the extension seam contract:
  `None` user, anonymous user, no memberships, single membership,
  multiple memberships.
- `GetCurrentDealershipResolver` (8 tests) — the composer:
  anonymous returns default, no `request.user` attribute returns
  default, header resolves, unknown header falls through, empty
  header falls through, authed user with no membership falls
  through, authed user with membership wins, membership beats
  header when both present.
- `DrfAuthenticationDefaultsIntegration` (3 tests) — auth classes
  configured, permission classes remain unset, `authtoken` app
  installed.

### Test baseline

- **1,333 → 1,349 pass, 1 skipped, 0 fail** (+16 new tests; zero
  regressions; no test suppressed with `@skip`).

## Compatibility checklist verification (§3 of MILESTONE_1_PLANNING.md)

Every §3 checklist item holds after 4B. Because
`DEFAULT_PERMISSION_CLASSES` is left unset, no currently-public
endpoint changes behavior. The full 1,333-test pre-existing
baseline exercises every §3 invariant directly; every test passes.

Explicit checks worth noting:

- ✅ `test_default_permission_classes_remain_unset` — locks the
  invariant that this session did not silently tighten enforcement.
- ✅ Every existing advisor-workspace / admin / chat / onboarding
  test continues to pass without any auth fixture (they hit
  endpoints anonymously and still succeed, because no endpoint
  gained a permission class).
- ✅ Chat safety stack untouched — 1,349-test baseline passes clean.
- ✅ Payment engine untouched.
- ✅ Franchise env-override path unchanged.
- ✅ Copper Canyon defaults unchanged.
- ✅ Write-path `pre_save` autofill from Increment 3 still fires —
  the `get_current_dealership` read-side resolver is orthogonal.

## Files touched

Created:

- `backend/dealer_ai/tests/test_current_dealership.py` (16 tests).
- `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical reference).
- `docs/handoffs/SESSION_040_milestone_1_auth_defaults_and_request_context.md` (this file).

Modified:

- `backend/dealer_kit/settings.py` — added `rest_framework.authtoken`
  to `INSTALLED_APPS`; populated
  `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`.
- `backend/dealer_ai/services/tenancy.py` — extended module docstring
  with the four-layer separation; added `get_active_membership`,
  `get_current_dealership`, `_read_dealership_header`,
  `_DEALERSHIP_HEADER` module constant.
- `docs/roadmap/MILESTONE_1_PLANNING.md` (in commit `dc24ab6`, prior
  to this session's feat commit) — added the multi-role-per-
  dealership design note to §7 · 4A, refined §7 · 4B to describe the
  helper split.
- `00-START-NEXT-SESSION.md` — overwritten to point at SESSION_041
  (Increment 4C).

Not touched (correctly):

- Any view — endpoint auth is 4C/4D.
- Any URL pattern.
- `docs/CAPABILITY_MATRIX.md` — outward behavior unchanged; matrix
  update lands at 4F when Milestone 1 closes.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7 — flips to
  `Y (Milestone 1 complete)` only at 4F.
- Frontend — login UI is 4E.
- 16-stage safety pipeline — untouched.
- `services/dealer_config.py` — no resolver changes needed; the
  Increment 3 optional `dealership=` argument already accepts the
  return of `get_current_dealership` when 4C/4D wire it up.

## Deviation from plan — one refinement recorded pre-implementation

The original `MILESTONE_1_PLANNING.md` §7 · 4B contract described a
single `get_current_dealership` function. During review of SESSION_039
close the user identified that `user.memberships.first()` should not
become the durable business rule for "which dealership is this user
acting within". Committed refinement (`dc24ab6`) recorded the split
into `get_active_membership` (extension seam) + `get_current_dealership`
(composer) *before* implementation began. This session implements the
refined contract. No deviation from the refined plan.

## Recommended scope for SESSION_041 — Increment 4C

**Goal:** replace the advisor-workspace slug-obscurity check with
real authentication + role + tenant enforcement.

**In scope** (per `MILESTONE_1_PLANNING.md` §7 · 4C):

1. Add DRF permission classes `AdvisorForSlug` +
   `SameDealership` to `advisor_workspace()` and
   `advisor_follow_up()` (`views.py:452–564`). URL shape preserved
   (`/api/dealer-ai/advisor/<slug>/*`).
2. `AdvisorForSlug` matches
   `request.user.salesperson.slug == slug`; `SameDealership`
   matches `request.user`'s active dealership (via
   `get_current_dealership`) against the target Salesperson's
   dealership.
3. `dealer_owner` at the same dealership can view any advisor's
   queue (per `MILESTONE_1_PLANNING.md` §1.4).
4. Lead-ownership check at `views.py:529` preserved verbatim.
5. Existing tests that hit the advisor workspace must gain an
   authenticated DRF test-client fixture; a shared helper
   (`authenticated_advisor_client(slug=...)`) in
   `tests/_auth_helpers.py` is the recommended shape.
6. New negative-path tests: unauthenticated → 401; authenticated
   wrong-advisor → 403; authenticated correct advisor →
   200; authenticated dealer_owner-at-same-dealership → 200;
   authenticated dealer_owner-at-different-dealership → 403.

**Out of scope for 4C**:

- Admin endpoint gating (4D).
- Frontend login UI (4E).
- Any global permission-class change (would break other endpoints).
- Tenant-scoped uniqueness on `Salesperson.slug`. Deferred per §5.

## Anchors that win on conflict

Unchanged from SESSION_039 close, plus the new reference doc:

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing)
5. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model reference)
6. `docs/BUSINESS_DOMAIN_MAP.md`
7. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs (this one + `SESSION_039_*.md`).
10. `git log --oneline -25`

## Operational state at session close

- **Backend (local):** Django on `:8001`. Package `backend/dealer_ai/`.
  Migrations `0001`–`0011` applied. `authtoken` migrations
  `0001`–`0004` applied. Default `Dealership` row present
  (`slug='default'`). No `Token` rows exist; no
  `UserDealershipRole` rows exist; `Salesperson.user` is NULL on
  all rows (unchanged from SESSION_039).
- **Backend (prod):** `vehicle-match-api.onrender.com` — not active.
- **Frontend (local):** Vite on `:5173`. Untouched this session.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,349 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- `docs/roadmap/DEFERRED_IDEAS.md` — still does not exist. Nothing
  out-of-milestone surfaced during 4B.

*End of SESSION_040 handoff.*
