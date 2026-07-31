---
title: "Dealer AI Kit — Authentication Model"
status: active
type: reference
generated: 2026-07-31
generated_at_session: SESSION_040 (Milestone 1 · Increment 4B)
supersedes: none
applies_to:
  - Every subsequent milestone that touches authentication,
    authorization, or tenant scoping.
---

# Dealer AI Kit — Authentication Model

> **What this is.** The single reference for every authentication and
> authorization decision in the kit. Introduced at SESSION_040 close
> so future milestones do not rediscover these concepts from source.
>
> **What this is not.** A change log, a session narrative, or a spec
> for a specific increment. It records the *durable* model. When a
> milestone extends the model (SSO, MFA, per-role UI polish, active-
> role switching), edit this file — do not create a parallel doc.
>
> **Precedence.** When this doc disagrees with `PROJECT_RULES.md` or
> `IMPLEMENTATION_ROADMAP.md`, those win. When it disagrees with
> current source code, the code wins. Rules + code are facts; this
> doc is a claim.

---

## 1. Four layers, always separated

Do not collapse these layers. Every future authentication decision
belongs to exactly one of them.

| # | Layer | Question it answers | Owned by |
|---|---|---|---|
| 1 | **Identity** | *Who is making this request?* | DRF authentication classes (`SessionAuthentication`, `TokenAuthentication`). Result: `request.user` (real user or `AnonymousUser`). |
| 2 | **Authorization** (tenant scope) | *Which dealership is this user acting within?* | `services.tenancy.get_current_dealership(request)`. Never returns `None`. |
| 3 | **Business permissions** | *Is this user allowed to do this action?* | DRF permission classes per endpoint (introduced per-endpoint by 4C, 4D, and every subsequent milestone that adds a sensitive surface). |
| 4 | **Data scoping** | *Which rows may this user see?* | Explicit `.filter(dealership=...)` on every queryset in a scoped view. Not automatic — no ORM manager magic. Adding rows to the tenant carriers is covered by the write-path `pre_save` autofill (Increment 3). |

**The layers are ordered.** A request cannot skip a layer. Identity
runs first; Authorization runs before any Business permission check;
Business permissions run before any Data scoping decision that would
leak rows.

**A layer's failure is not another layer's job to catch.** If a view
forgets to add `.filter(dealership=...)` (layer 4), that is a data
leak — no permission class (layer 3) will paper it over. If a
permission class forgets to check role (layer 3), no queryset filter
will substitute for it.

---

## 2. Identity

- **Authentication classes** (`settings.REST_FRAMEWORK`):
  `SessionAuthentication` first, then `TokenAuthentication`.
  Both installed at framework level; individual views inherit both
  unless they override `authentication_classes`.
  - `SessionAuthentication` drives the browser flow. Cookie-backed
    Django sessions; CSRF enforcement (see §2b below).
  - `TokenAuthentication` is reserved for scripted / API-client /
    integration access. Tokens are managed by
    `django.contrib.authtoken` and provisioned via
    `python3 manage.py drf_create_token <username>` or
    `Token.objects.create(user=…)`. **The browser never stores a
    DRF token in localStorage** — session cookies are the browser
    contract. This is an intentional constraint on the frontend.
- **`request.user`** is populated after authentication succeeds.
  Anonymous requests carry `AnonymousUser` — always truthy for
  `is_authenticated == False`.
- **Browser auth endpoints** (Increment 4E):
  - `POST /api/dealer-ai/auth/login/` — `{username, password}`;
    200 with `me` payload on success, 401 with `{"detail": "Invalid
    credentials."}` on bad credentials (identical body for unknown
    user vs. wrong password — no user enumeration), 400 for missing
    fields.
  - `POST /api/dealer-ai/auth/logout/` — clears the session.
    Idempotent — 200 whether or not one existed. Frontend calls it
    on ambiguous state without pre-flighting.
  - `GET /api/dealer-ai/auth/me/` — decorated with
    `@ensure_csrf_cookie`. Returns
    `{authenticated: false}` for anonymous callers and
    `{authenticated: true, user, dealership, roles}` for signed-in
    ones. Dealership + roles are resolved via
    `services.tenancy.get_current_dealership(request)` +
    `UserDealershipRole.objects.filter(user, dealership)` — never
    parallel identity resolvers.
- **What Identity does not decide.** Identity does not decide which
  dealership the user is acting within, and it does not decide what
  the user is permitted to do. Both are separate layers.

## 2b. CSRF contract

Session cookies without CSRF protection are a live XSRF footgun.
The kit's contract:

- Every unsafe method (`POST`, `PUT`, `PATCH`, `DELETE`) issued by
  an authenticated caller against a `SessionAuthentication`-backed
  endpoint MUST include a valid `X-CSRFToken` header matching the
  `csrftoken` cookie. DRF's `SessionAuthentication.enforce_csrf`
  applies Django's CSRF check on every authenticated request.
- The browser bootstraps its `csrftoken` cookie by calling
  `/auth/me/` on mount — the endpoint is decorated with
  `@ensure_csrf_cookie` for exactly this purpose. Django rotates
  the token on `login()` per its default; the frontend re-reads the
  cookie for every unsafe request via `authFetch` so the current
  value is always used.
- `settings.CSRF_TRUSTED_ORIGINS` must include the browser's
  observed `Origin` — for dev that is `http://localhost:5173` (Vite
  dev server proxying to Django on `:8001`). Configurable via env
  (`CSRF_TRUSTED_ORIGINS=...`) for prod.
- **`DEFAULT_PERMISSION_CLASSES` remains unset.** Do not weaken
  `SessionAuthentication` to simplify frontend work — enforce
  every operator mutation via `X-CSRFToken`.

Focused tests (`tests/test_auth_endpoints.py::CsrfEnforcedOnAuthenticatedMutations`)
lock: authenticated POST without `X-CSRFToken` → 403; same request
with the header → passes CSRF and reaches the view.

## 2c. Frontend auth primitives (Increment 4E)

- **`lib/authFetch.ts`** — the one operator-fetch primitive.
  Includes `credentials: "same-origin"` (session cookie), reads
  `csrftoken` from `document.cookie` and attaches `X-CSRFToken` on
  unsafe methods, and throws typed errors so callers preserve the
  401 vs 403 vs 4xx distinction:
  - `UnauthenticatedError` → the request layer's boundary for "must
    sign in".
  - `ForbiddenError` → "signed in but not authorized". Never
    redirects to `/login`.
  - `ApiError(status, body)` → everything else.
- **`lib/auth.ts`** — thin wrapper around the three endpoints
  (`fetchMe`, `loginRequest`, `logoutRequest`) plus
  `InvalidCredentialsError`. `fetchMe` never throws on
  `Unauthenticated` — it returns `{authenticated: false}` so
  bootstrap always terminates.
- **`lib/AuthContext.tsx`** — small `<AuthProvider>` +
  `useAuth()`. Fields: `status ("loading" | "authenticated" |
  "anonymous")`, `user`, `dealership`, `roles`, `hasRole(...)`,
  `login`, `logout`, `refresh`. Bootstraps once on mount via
  `fetchMe()`. No heavyweight state library.
- **`components/RequireAuth.tsx`** — route wrapper. `loading` →
  render nothing (avoid login-flash); `anonymous` → `<Navigate to="/login?next=..." replace />`;
  `authenticated` → `<Outlet />`. **Does not** enforce role checks
  — those live server-side, propagate as `ForbiddenError`, and each
  page surfaces the message in its own error state.
- **`pages/LoginPage.tsx`** — username + password + submit. Reads
  `?next=` and validates it (must start with `/[^/]` — rejects
  protocol-relative URLs like `//attacker.example.com` to block
  open redirects). Redirects to `/dealer-ai-overview` when `next` is
  absent or unsafe.
- **Public / protected route split** (see `src/main.tsx`):
  - **Public** (outside `RequireAuth`): `/`, `/assistant`,
    `/showroom`, `/embed/assistant`, `/login`.
  - **Protected** (inside `RequireAuth`): every operator surface
    under the App shell (overview, live assistant, inventory,
    leads, coaching, admin, team, setup, advisor workspace).
- **`lib/api.ts` boundary** — every operator API function goes
  through `authFetch`; public endpoints (customer chat,
  `/vehicles/*`, `/salespeople/*`, `/leads/` POST, and the
  branding GET on `/onboarding/profile/`) stay on plain `fetch`.
  A broken session on a customer-facing page can never cause a
  redirect to `/login`.

---

## 3. Membership

- **Model.** `dealer_ai.models.UserDealershipRole`. Fields: `user`
  (FK to `AUTH_USER_MODEL`), `dealership` (FK to `Dealership`),
  `role` (CharField over the seven canonical values), timestamps.
- **Uniqueness.** `unique_together = (user, dealership, role)`.
  A single user may hold **multiple concurrent roles at a single
  dealership** (e.g. an indie owner who also acts as sales manager)
  and may **belong to multiple dealerships** with different roles.
  Rationale documented in `MILESTONE_1_PLANNING.md` §7 · 4A design
  note.
- **Bootstrap.** Before Increment 4E ships the login flow, the first
  `dealer_owner` membership is created manually by a superuser via
  Django admin. There is no auto-create-on-first-login.
- **Salesperson link.** `Salesperson.user = OneToOneField(User,
  null=True, SET_NULL)`. Optional today; required for authenticated
  advisor workspace access from Increment 4C onwards. `SET_NULL`
  preserves historical lead attribution when a user account is
  removed.

---

## 4. Active dealership resolution

- **Entry point.** `services.tenancy.get_current_dealership(request)`.
- **Priority order** (never returns `None`, never raises on unknown
  header slugs):
  1. **Authenticated identity.** Via
     `services.tenancy.get_active_membership(user)`. If a live
     membership exists, its dealership wins — this is the strongest
     signal because the user chose to log in as themselves and their
     memberships are explicit business data.
  2. **Explicit request signal.** The `X-Dealership-Slug` header,
     matched against a live `Dealership.slug`. Silent fall-through
     when missing or unresolved. Enables public / embed /
     cross-domain callers that cannot authenticate.
  3. **Default fallback.** `get_default_dealership()` — the seeded
     `slug="default"` row from migration 0009.
- **Extension seam.** `get_active_membership(user)` is the seam
  where future dealership-switching lands. Increment 4B ships a
  deterministic single-membership implementation. Future work
  (session-scoped active-role selection, explicit picker UI,
  role-priority tie-breakers) replaces *this helper's body* without
  altering `get_current_dealership` or any downstream caller.

---

## 5. Roles

The seven canonical roles are defined in `dealer_ai.models` as
module-level constants:

- `ROLE_DEALER_OWNER` — authorizes buys, repos, hardship exceptions,
  compliance escalations.
- `ROLE_SALES_MANAGER` — owns the sales pipeline, approves
  assignments, sees leads across advisors.
- `ROLE_RECON_MANAGER` — owns the recon queue and front-line-ready
  status.
- `ROLE_F_AND_I_MANAGER` — owns finance + insurance compliance;
  credit apps live in this role's queue.
- `ROLE_COLLECTIONS` — BHPH collections floor; scoped to
  overdue accounts.
- `ROLE_ADVISOR` — floor advisor; sees own leads only.
- `ROLE_PORTER` — vehicle movement + reception; minimal permissions.

Adding an eighth role requires a roadmap change first —
`test_role_choices_contain_exactly_seven_canonical_values` in
`test_userdealershiprole.py` forces that conversation.

**Roles name responsibilities, not seniority.** Multi-role per
person is the natural business shape for indie shops (see
`MILESTONE_1_PLANNING.md` §7 · 4A design note).

---

## 6. Authorization (which dealership)

- Answered by `get_current_dealership(request)`.
- Every scoped view calls it exactly once and passes the returned
  `Dealership` to every `.filter(dealership=…)` in that view.
- Views that are intentionally cross-tenant (there are none in
  Milestone 1; a future superadmin surface might qualify) must
  bypass the resolver *explicitly* — never by accident.

---

## 7. Business permissions

- Enforced by DRF permission classes per endpoint. Classes live in
  `dealer_ai/permissions.py`. Compose them at the view layer via
  DRF's `&` and `|` operators — prefer composition over adding
  logic to a single class.
- **Shipped classes (Increment 4C — advisor workspace):**
  - `IsAdvisorForSlug` — the authenticated user *is* the
    Salesperson identified by the URL kwarg `slug` (via the
    `Salesperson.user` OneToOne link from 4A).
  - `IsDealerOwnerForAdvisorSlug` — the authenticated user holds
    `dealer_owner` at the dealership that owns the Salesperson
    identified by the URL kwarg `slug`. Cross-dealership
    ownership does not grant access.
  - Applied composition (both advisor views):
    `[IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]`.
- **Shipped classes (Increment 4D — admin gating):**
  - `IsSalesManagerOrOwnerAtActiveDealership` — the caller holds
    `sales_manager` OR `dealer_owner` at
    `get_current_dealership(request)`. Applied to every
    `/api/dealer-ai/admin/*` endpoint plus `manager-chat`.
  - `IsDealerOwnerAtActiveDealership` — the caller holds
    `dealer_owner` at `get_current_dealership(request)`. Applied
    to `onboarding/profile/` PUT/PATCH and
    `onboarding/profile/logo/`.
  - `ReadOnly` — small method-based primitive. Passes any HTTP
    safe method. Composed with `IsDealerOwnerAtActiveDealership`
    on `onboarding/profile/` so branding GETs stay public while
    upserts require dealer_owner:
    `[ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]`.
  - All three consult `get_current_dealership(request)` for tenant
    scope rather than a URL kwarg — a different URL-shape family
    from the 4C advisor classes.
- **Layer separation on the advisor endpoint.** The 403 lead-
  ownership check inside `advisor_follow_up`
  (`lead.assigned_to_id != sp.pk`) is preserved verbatim in 4C. It
  is the data-scoping layer's manifestation — orthogonal to the
  authorization layer. A dealer_owner authorized to access an
  advisor's URL still cannot draft on leads assigned to a
  different advisor.
- Customer-facing chat + vehicle Q&A remain `AllowAny` at the
  permission layer per `MILESTONE_1_PLANNING.md` §1.2. Tenant
  scoping still applies via `get_current_dealership` (layer 2 does
  not require Identity to have succeeded).
- **`REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is intentionally
  unset.** The DRF default (`AllowAny`) stands. Tightening the
  global default without per-endpoint whitelisting would silently
  break every currently-public endpoint. Each endpoint declares its
  own permission classes.
- **No information leakage via differential status codes.** Unknown
  slugs return 403 to authenticated non-privileged callers — the
  same status a known slug returns to an unauthorized caller. This
  invariant is locked by
  `AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs` and
  extends to deactivated Salesperson rows (an authorized owner
  cannot distinguish "deactivated advisor slug" from "unknown
  slug"; both are 403).

---

## 8. Future dealership switching

Not required by Milestone 1. When a real multi-dealership user
appears, extend the model as follows — no schema migration is
expected:

1. Add a `set_active_membership(request, membership)` helper that
   validates the membership belongs to `request.user` and writes
   `request.session["active_membership_id"] = membership.pk`.
2. Extend `get_active_membership(user, session=None)` to read
   the session key first, validate it, and fall through to the
   deterministic-first branch if unset or stale.
3. Add a dealership-picker UI + POST endpoint that calls
   `set_active_membership`.

The extension lands **inside** `get_active_membership`. Every
downstream caller (`get_current_dealership`, every permission
class that consults role at the active dealership, every view that
scopes querysets) continues to work unmodified. This is why the
seam is scoped to the smallest possible helper.

---

## 8b. Tenant-scoped query patterns (Increment 4D)

Data scoping is the fourth layer (§1 row 4) — separate from
authorization, separate from tenancy resolution. The rules:

- **Every gated admin queryset carries an explicit
  `.filter(dealership=…)` at the view layer.** No hidden filtering
  via custom managers; the filter is right where the reader can see
  it.
- **Views resolve tenant once, at the top of the handler.**
  `dealership = get_current_dealership(request)` produces the
  `Dealership` instance every subsequent queryset filters against.
  Never call the resolver twice inside one view — it makes the
  data flow harder to audit.
- **Service functions that query models accept
  `dealership` as a keyword argument.** No service reaches into
  request state directly. Tenant context is passed from the view.
  Backwards compatibility for the pre-4D tests is provided via
  `dealership=None` defaulting to the seeded default via
  `get_default_dealership()` — the fallback is explicit inside
  the service, not implicit.
- **Object-lookup views fail closed on cross-tenant pk.** A pk
  belonging to another dealership resolves to `.DoesNotExist` and
  returns 404 — never 200 with cross-tenant data, never 403
  (which would leak existence).
- **Mutation views validate any FK in the body against the same
  tenant.** `admin/lead/<id>/assign/` checks both that the lead
  belongs to the caller's dealership (404) and that the target
  salesperson belongs to the caller's dealership (400). One
  scoping check per FK, one per level of the request graph.

The `manager_chat` endpoint is a special case: it creates a
throwaway `ChatSession` per request, so tenant scoping there means
attaching the caller's active dealership to the row it creates
(not filtering an existing queryset).

## 9. What this model does NOT cover

Out of scope for the kit's authentication model as of Milestone 1.
Any of these becomes in-scope only via a roadmap update:

- **SSO** (SAML, OIDC beyond Django's built-ins). Deferred; no
  research trigger yet.
- **MFA**. Deferred; no research trigger yet.
- **Row-level ACLs beyond dealership scope.** Every scoped model
  belongs to exactly one dealership; there is no "shared with"
  concept and no plan for one.
- **Impersonation / act-as** flows. Deferred until a support
  operator role is defined.
- **API rate limiting per token.** DRF throttling exists but is
  not configured; add if abuse surfaces.
- **Audit log of authentication events.** Django logs standard
  auth events; a structured audit trail for compliance (GLBA,
  FDCPA) is a Milestone 10 / Milestone 12 concern.

---

## 10. Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md`
5. Current source code (`backend/dealer_ai/models.py`,
   `backend/dealer_ai/services/tenancy.py`,
   `backend/dealer_kit/settings.py`).
6. This document.

Planning docs are claims. Rules + code are facts.
