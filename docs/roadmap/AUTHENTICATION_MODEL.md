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
  - `SessionAuthentication` — the customer-facing chat + embed frame
    are cookie-friendly. Also the mechanism the frontend uses
    (Increment 4E lands the login form).
  - `TokenAuthentication` — for scripted / API-client / integration
    access. Tokens are managed by `django.contrib.authtoken` (the
    `authtoken` app) and provisioned per-user via
    `python3 manage.py drf_create_token <username>` or the standard
    `Token.objects.create(user=…)`.
- **`request.user`** is populated after authentication succeeds.
  Anonymous requests carry `AnonymousUser` — always truthy for
  `is_authenticated == False`.
- **What Identity does not decide.** Identity does not decide which
  dealership the user is acting within, and it does not decide what
  the user is permitted to do. Both are separate layers.

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

- Enforced by DRF permission classes per endpoint. Milestone 1
  introduces two families:
  - `AdvisorForSlug + SameDealership` (Increment 4C) — advisor
    workspace.
  - `IsSalesManagerOrOwner + SameDealership` (Increment 4D) —
    admin endpoints.
  - `IsDealerOwner + SameDealership` (Increment 4D) — onboarding
    profile mutation.
- Customer-facing chat + vehicle Q&A remain `AllowAny` at the
  permission layer per `MILESTONE_1_PLANNING.md` §1.2. Tenant
  scoping still applies via `get_current_dealership` (layer 2 does
  not require Identity to have succeeded).
- **`REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` is intentionally
  unset.** The DRF default (`AllowAny`) stands. Tightening the
  global default without per-endpoint whitelisting would silently
  break every currently-public endpoint. Each endpoint declares its
  own permission classes.

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
