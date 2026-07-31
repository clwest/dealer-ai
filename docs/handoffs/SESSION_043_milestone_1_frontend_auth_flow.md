---
title: "SESSION_043 handoff — Milestone 1 Increment 4E (frontend auth flow)"
status: historical
type: handoff
date: 2026-07-31
session: 043
commits:
  - 0935ed6  # Increment 4E — /auth/{login,logout,me} + CSRF trust origins + frontend authFetch/AuthContext/RequireAuth/LoginPage + api.ts operator split + AUTHENTICATION_MODEL §2/§2b/§2c updates
  - cffa37c  # SESSION_043 handoff + SESSION_044 pointer
---

# SESSION_043 — Milestone 1 · Increment 4E

## What shipped

The minimum complete browser sign-in flow. Operators can now log in
through the Django session backend, remain authenticated across
navigations and reloads, hit every 4C/4D-protected surface, and log
out — all without a single change to the public customer experience
(`/`, `/assistant`, `/showroom`, `/embed/assistant`, branding GET).

The four-layer separation from `AUTHENTICATION_MODEL.md` §1 was
preserved:

- **Identity** — three new DRF endpoints wrap Django's built-in
  `authenticate` / `login` / `logout` and expose the current
  session state.
- **Authorization** — unchanged; already answered by the 4B tenancy
  resolver + 4C/4D permission classes.
- **Business permissions** — unchanged; per-endpoint DRF permission
  classes from 4C/4D still gate the same operations.
- **Data scoping** — unchanged.

### 1. Backend — three new endpoints

`backend/dealer_ai/views.py` gained:

- **`POST /api/dealer-ai/auth/login/`** — `{username, password}`;
  200 with the same `me` payload on success, 401 with
  `{"detail": "Invalid credentials."}` for wrong password OR
  unknown user (identical body defeats user enumeration), 400 for
  a missing field.
- **`POST /api/dealer-ai/auth/logout/`** — clears the Django
  session. Idempotent — 200 whether or not a session existed. The
  frontend calls it on ambiguous state without pre-flighting.
- **`GET /api/dealer-ai/auth/me/`** — decorated with
  `@ensure_csrf_cookie` so the very first bootstrap primes the
  `csrftoken` cookie. Returns `{authenticated: false}` for
  anonymous callers and
  `{authenticated: true, user, dealership, roles}` for signed-in
  ones. The `dealership` + `roles` fields are resolved via
  `services.tenancy.get_current_dealership(request)` +
  `UserDealershipRole.objects.filter(user, dealership)` — no
  parallel identity resolver.

URL patterns added to `dealer_ai/urls.py`.

### 2. Backend — CSRF trust origins

Django's `CsrfViewMiddleware` (via DRF's
`SessionAuthentication.enforce_csrf`) validates the browser's
`Origin` header on every authenticated unsafe method. In dev the
browser talks to Vite on `:5173`; without an entry for that origin
in `CSRF_TRUSTED_ORIGINS`, every authenticated POST returns 403
with `"CSRF Failed: Origin checking failed"`. Added to
`backend/dealer_kit/settings.py`:

```python
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",") if o.strip()
]
```

Env-configurable so prod (single-origin behind one domain) can
override. Same shape as the existing `CORS_ALLOWED_ORIGINS` block.

**`DEFAULT_PERMISSION_CLASSES` remains unset** — the invariant
from 4B still holds (locked by
`test_default_permission_classes_remain_unset`).

### 3. Backend — focused auth tests

New file `tests/test_auth_endpoints.py` — 21 focused tests across
five classes:

- **`AuthMeEndpoint`** (5) — anonymous returns
  `{authenticated: false}`; `csrftoken` cookie is set on every
  call (bootstrap primer); authenticated returns full identity +
  active dealership + roles; multiple concurrent roles surface as
  a list (4A design note honored); linked `Salesperson.slug`
  exposed for advisor routing.
- **`AuthLoginEndpoint`** (6) — valid creds return the `me` shape;
  session cookie is established; wrong password + unknown user
  both return the same generic 401 body; missing username / missing
  password → 400.
- **`AuthLogoutEndpoint`** (3) — clears session; safe to call
  when anonymous; idempotent under repeated calls.
- **`SessionAuthenticationDrivesProtectedEndpoints`** (3) — full
  round-trip: log in → hit an admin endpoint via the same session
  cookie → success. Log out → same endpoint returns 401/403. An
  authenticated advisor role hitting an admin endpoint gets 403,
  not 401 — the distinct-status invariant the frontend routes on.
- **`CsrfEnforcedOnAuthenticatedMutations`** (2) — uses
  `django.test.Client(enforce_csrf_checks=True)` to match real
  browser semantics. Authenticated POST without `X-CSRFToken`
  → 403. Same POST with the header passes CSRF and reaches the
  view (404 for a non-existent lead pk = auth passed, CSRF
  passed, business logic ran).
- **`PublicBrandingRemainsUnauthenticated`** (2) — §3 compat lock:
  onboarding GET + public salespeople list remain 200 for
  anonymous callers.

### 4. Frontend — one shared fetch primitive + one context + one gate

Created:

- **`frontend/src/lib/authFetch.ts`** — the single operator-fetch
  primitive. `credentials: "same-origin"` + reads `csrftoken`
  cookie + attaches `X-CSRFToken` on unsafe methods. Throws
  `UnauthenticatedError` on 401, `ForbiddenError` on 403,
  `ApiError(status, body)` on other non-2xx. Wrappers exported:
  `authGetJSON`, `authPostJSON`, `authPutJSON`, `authPostForm`.
- **`frontend/src/lib/auth.ts`** — `fetchMe()`, `loginRequest()`,
  `logoutRequest()` + shared `AuthUser`, `AuthDealership`,
  `MeResponse` types + `InvalidCredentialsError`. `fetchMe` never
  throws — it returns `{authenticated: false}` on network failure
  so app bootstrap always terminates.
- **`frontend/src/lib/AuthContext.tsx`** — `<AuthProvider>` +
  `useAuth()`. Small context; no state library. Exposes `status`
  (`"loading" | "authenticated" | "anonymous"`), `user`,
  `dealership`, `roles`, `hasRole(...)`, `login`, `logout`,
  `refresh`. Bootstraps once on mount by calling `fetchMe()`.
- **`frontend/src/components/RequireAuth.tsx`** — route wrapper.
  `loading` → render nothing (no login-flash); `anonymous` →
  `<Navigate to="/login?next=..." replace />` preserving the
  intended path; `authenticated` → `<Outlet />`. Does **not**
  enforce role checks — those live server-side, propagate as
  `ForbiddenError`, and each page surfaces its own inline error.
- **`frontend/src/pages/LoginPage.tsx`** — username + password +
  submit + inline error. Reads `?next=` and validates it against
  the `SAFE_INTERNAL_PATH` regex — protocol-relative URLs
  (`//attacker.example.com`) are rejected to block open-redirect.
  Redirects to `/dealer-ai-overview` when `next` is missing or
  unsafe.

Modified:

- **`frontend/src/main.tsx`** — wraps the tree in `<AuthProvider>`;
  adds `/login`; wraps every operator route (under the `App`
  outlet) with `<RequireAuth>`. Public routes (`/`, `/assistant`,
  `/showroom`, `/embed/assistant`) stay outside the gate.
- **`frontend/src/App.tsx`** — added a small `SignedInBadge`
  component to the topbar (username + Sign out button). Reads
  `useAuth()`. Sign out fires `logout()`, RequireAuth then
  redirects to `/login`.
- **`frontend/src/lib/api.ts`** — every operator API function now
  goes through `authFetch` (admin list/detail/mutation, advisor
  workspace + follow-up, manager chat, ad copy, onboarding
  PUT/PATCH, logo upload). Public functions (customer chat,
  vehicles, public salespeople, lead creation POST, and the
  branding GET on onboarding) stay on plain `fetch`. Removed
  the now-unused `putJSON` and `postForm` helpers.

### 5. Documentation

Updated `docs/roadmap/AUTHENTICATION_MODEL.md` in place:

- §2 rewritten to describe the shipped browser session flow +
  endpoint list + no-DRF-token-in-localStorage constraint.
- New §2b — CSRF contract (bootstrap primer, `X-CSRFToken` on
  unsafe methods, `CSRF_TRUSTED_ORIGINS` requirement, no
  `DEFAULT_PERMISSION_CLASSES` weakening).
- New §2c — frontend primitives (`authFetch`, `AuthContext`,
  `RequireAuth`, `LoginPage`) and the public/protected route
  boundary.

No parallel docs created.

### 6. Browser smoke — all 8 required steps

Verified against `localhost:5173` (Vite dev) proxying to
`localhost:8001` (Django) with two dev-only seeded users
(`smoke_owner` = `dealer_owner`, `smoke_advisor` = `advisor` linked
to `Salesperson.slug=smoke-advisor-slug`):

1. ✅ Open `/dealer-ai-admin` while logged out → redirects to
   `/login?next=%2Fdealer-ai-admin`.
2. ✅ Sign in as advisor → lands on `/dealer-ai-overview` with the
   full sidebar + "smoke_advisor" chip in the topbar.
3. ✅ Advisor accesses `/dealer-ai-advisor/smoke-advisor-slug` and
   sees the own-leads workspace.
4. ✅ Advisor navigates to `/dealer-ai-advisor/some-other-slug` and
   sees "Not authorized." **without a redirect to /login** — the
   401 vs 403 distinction is preserved in the UI.
5. ✅ Sign out → `/login?next=...`, `document.cookie` no longer
   carries `sessionid`, `fetchMe()` returns
   `{authenticated: false}`.
6. ✅ Sign in as owner (`smoke_owner`).
7. ✅ Owner accesses `/dealer-ai-admin` and sees the real dashboard
   (23 chat sessions, 23 leads, $427 avg target payment); accesses
   `/dealer-ai-advisor/smoke-advisor-slug` per §1.4 (owner may view
   any advisor's queue at the same dealership).
8. ✅ Sign out; anonymous `/showroom` and `/` render fully — branding
   (Copper Canyon Auto, Yuma AZ, phone number, tagline) resolves via
   the public onboarding GET.

Test users provisioned via a one-shot `python3 manage.py shell`
seed script (recorded in this handoff, not committed to source).
No credentials hardcoded into production code.

### Test baseline

- **1,445 → 1,466 pass, 1 skipped, 0 fail** (+21 focused auth
  tests; zero regressions; no `@skip` suppression).

### Frontend verification

- `npx tsc --noEmit` → clean.
- `npx vite build` → clean (`dist/assets/index-*.js` 502 kB /
  138 kB gz; same pre-existing chunk-size warning as SESSION_042).
- Browser smoke → all 8 steps pass.

## Compatibility checklist verification (§3 of MILESTONE_1_PLANNING.md)

Every §3 item verified true after 4E:

- ✅ **Public branding renders unauthenticated.** Locked by
  `PublicBrandingRemainsUnauthenticated` + verified via browser
  smoke of `/` and `/showroom` while logged out.
- ✅ **Customer chat, vehicle Q&A, embed frame — all unchanged.**
  Public API functions in `api.ts` still use plain `fetch`.
- ✅ **`DEFAULT_PERMISSION_CLASSES` still unset.** Locked by
  `test_default_permission_classes_remain_unset` (from 4B).
- ✅ **All 4C/4D permission matrices still pass** — 1,466-test
  baseline includes every focused permission + scoping test.
- ✅ **Chat safety stack untouched.**
- ✅ **Payment engine untouched.**
- ✅ **Franchise env-override path unchanged.**
- ✅ **Copper Canyon defaults unchanged.**
- ✅ **URL shapes preserved** — no operator route URL changed;
  `/login` added as the sole new path.
- ✅ **Payload shapes preserved** on every pre-existing endpoint.
- ✅ **401 / 403 / 404 distinct** — locked by
  `SessionAuthenticationDrivesProtectedEndpoints.test_wrong_role_gets_403_not_401`
  and by the browser smoke (advisor cross-slug shows 403 UI, not
  a redirect).

## Files touched

Created:

- `backend/dealer_ai/tests/test_auth_endpoints.py` (21 tests).
- `frontend/src/lib/authFetch.ts`.
- `frontend/src/lib/auth.ts`.
- `frontend/src/lib/AuthContext.tsx`.
- `frontend/src/components/RequireAuth.tsx`.
- `frontend/src/pages/LoginPage.tsx`.
- `docs/handoffs/SESSION_043_milestone_1_frontend_auth_flow.md`
  (this file).

Modified:

- `backend/dealer_ai/views.py` — three new endpoints
  (`auth_login`, `auth_logout`, `auth_me`) + `_me_payload` helper.
- `backend/dealer_ai/urls.py` — three URL patterns.
- `backend/dealer_kit/settings.py` — `CSRF_TRUSTED_ORIGINS`.
- `frontend/src/main.tsx` — `<AuthProvider>`, `/login`,
  `<RequireAuth>` wrapper.
- `frontend/src/App.tsx` — `<SignedInBadge>` in the topbar.
- `frontend/src/lib/api.ts` — operator functions routed through
  `authFetch`; removed unused `putJSON` / `postForm`.
- `docs/roadmap/AUTHENTICATION_MODEL.md` — §2 rewritten; new
  §2b (CSRF contract); new §2c (frontend primitives).
- `00-START-NEXT-SESSION.md` — overwritten for SESSION_044 =
  Increment 4F.

Not touched (correctly):

- 4C / 4D permission classes.
- `services/tenancy.py`.
- 16-stage safety pipeline.
- Public branding GET, customer chat, embed frame, vehicle Q&A,
  public salespeople list.
- `demo/*` endpoints (deferred per SESSION_042 handoff).
- `docs/CAPABILITY_MATRIX.md` — updated at 4F.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7 — flips at 4F.

## Deviation from plan — one landed defense

The original 4E contract implied only the three auth endpoints +
frontend wiring. Implementation surfaced a real dev-environment
CSRF failure: Django's `Origin` check rejects `http://localhost:5173`
unless it appears in `CSRF_TRUSTED_ORIGINS`, and until this
increment nothing forced that configuration. Left unfixed, the
first authenticated mutation from the Vite dev server would 403
with a cryptic message. Landed the setting alongside the auth
endpoints so the dev experience matches the browser smoke script;
production still overrides via env.

Recorded here so the next reviewer knows why the setting appeared
in this session's diff.

## Recommended scope for SESSION_044 — Increment 4F (Milestone 1 close)

**Goal:** ship the compatibility sweep, hardening pass, and
documentation flips that formally close Milestone 1.

**In scope** (per `MILESTONE_1_PLANNING.md` §7 · 4F):

1. **Compatibility checklist walk-through** — every §3 item
   verified true one more time, in one place, in one commit.
2. **`docs/CAPABILITY_MATRIX.md` §7 / §8** — update the auth + role
   entries from "N (not implemented)" to "Y" with pointers to the
   shipped classes.
3. **`docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7** — flip
   Milestone 1 to complete.
4. **Consider one small integration test spanning login → tenant
   scoping → advisor workspace end-to-end** if the existing
   focused suite leaves an obvious gap.
5. **Handoff at `docs/handoffs/SESSION_044_<slug>.md`** identifying
   Milestone 2 kickoff scope (vehicle investment ledger — see
   `IMPLEMENTATION_ROADMAP.md` §Milestone 2).

**Out of scope for 4F**:

- New features on any surface.
- Tenant-scoped uniqueness.
- Frontend password reset / MFA / SSO.
- Gating `demo/*` endpoints — separate scope decision.
- The 4E chunk-size warning — not a Milestone 1 concern.

## Anchors that win on conflict

Unchanged from SESSION_042 close:

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing)
5. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model)
6. `docs/BUSINESS_DOMAIN_MAP.md`
7. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs (this one + `SESSION_042_*.md`).
10. `git log --oneline -25`

## Operational state at session close

- **Backend (local):** Django on `:8001`. Migrations `0001`–`0011`
  applied; `authtoken` migrations applied. Default `Dealership`
  row exists.
- **Dev DB seeded users** (from browser smoke, safe to keep):
  `smoke_owner` (`dealer_owner`) and `smoke_advisor` (`advisor`,
  linked to `Salesperson.slug=smoke-advisor-slug`). Password
  `smoke-pass-4e` for both.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
- **Frontend (local):** Vite on `:5173`. Auth flow wired.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,466 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`
  installed; `DEFAULT_PERMISSION_CLASSES` unset.
- **CSRF trust origins:** localhost:5173, 127.0.0.1:5173,
  localhost:3000, 127.0.0.1:3000 (env-configurable).
- **Endpoint-level permission classes shipped (unchanged from
  SESSION_042):** advisor (4C) + admin (4D) surfaces.
- **Auth endpoints (new this session):** `/auth/login/`,
  `/auth/logout/`, `/auth/me/`.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.

*End of SESSION_043 handoff.*
