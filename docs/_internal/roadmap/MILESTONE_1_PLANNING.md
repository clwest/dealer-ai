---
title: "Milestone 1 — Implementation-Planning Pass"
status: shipped
type: planning-artifact
generated: 2026-07-31
generated_at_session: SESSION_035 (pre-implementation)
updated: 2026-07-31
updated_at_session: SESSION_044 (Milestone 1 closeout — §3 annotated with shipped evidence, franchise env-override wired in settings.py)
milestone: 1
milestone_name: "Multi-tenant + role-based access foundation"
shipped_at_session: SESSION_044
shipped_over: SESSION_037, SESSION_038, SESSION_039, SESSION_040, SESSION_041, SESSION_042, SESSION_043, SESSION_044
retrospective: docs/roadmap/MILESTONE_1_RETROSPECTIVE.md
sources:
  - docs/PROJECT_RULES.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/BUSINESS_DOMAIN_MAP.md
  - docs/CAPABILITY_MATRIX.md
  - docs/research/VEHICLE_CENTRIC_PIVOT.md
  - docs/research/FINANCE_DEPARTMENT_MAPPING.md
  - docs/research/BHPH_OPERATIONS_MAPPING.md
supersedes: none
applies_to:
  - SESSION_035 Milestone 1 implementation session
  - Any subsequent session that resumes Milestone 1
---

> **Milestone 1 shipped at SESSION_044.** Original plan preserved
> below; §3 annotated in place with the shipped evidence, and
> §7 records the actual increment sequence with commit pointers.
> The retrospective at
> `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` captures deviations,
> lessons, and remaining deferred work. Do not rewrite the plan
> — annotate.

# Milestone 1 — Implementation-Planning Pass

> **What this is.** The planning artifact produced before Milestone 1
> implementation begins. Five sections: design memo, migration impact
> review, compatibility checklist, reusable-primitive review, scope
> discipline / deferrals.
>
> **Why this exists.** Milestone 1 introduces tenancy and authentication
> — the two changes with the broadest blast radius across the existing
> codebase (57 test files, 1,300 tests, every operator endpoint, every
> data-carrying model). Confirming the plan and the compatibility
> invariants before touching code is the difference between a clean
> milestone and a two-session recovery.
>
> **Precedence.** The six rules of `docs/PROJECT_RULES.md` override
> anything in this doc. The scope boundary of
> `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 overrides
> anything in this doc.
>
> **How to use it.** Read all five sections before writing code. Use the
> compatibility checklist (§3) as the acceptance test — Milestone 1 is
> not complete until every checklist item verifies true.

---

## 1. Design Memo

The memo is scoped to the four subsystems named in the roadmap plus a
fifth item — the singleton→per-tenant migration path — that the
roadmap implies but does not list separately. Each entry answers:
**why**, **research/roadmap citation**, **existing implementation to
extend**, **implementation to leave untouched**.

### 1.1 Tenancy — `Dealership` FK-carrier model

- **Why.** Every subsequent milestone stores data whose contamination
  between dealerships would be a compliance breach. Introducing the FK
  carrier now is cheap; retrofitting after Milestones 2, 10, 12 is
  brutal (VCP explicitly).
- **Citation.** `VEHICLE_CENTRIC_PIVOT.md:399-401` — *"Introduce
  `Dealership` FK-carrier model (even single-row). Every new model in
  Phases 1+ carries the FK. Retrofitting is brutal."* — item #1 of
  "Technical debt to pay down FIRST." Reinforced by roadmap §2.7,
  which lists this as `N` (not implemented) under cross-cutting
  foundations.
- **Extend.** `DealerOnboardingProfile` (models.py:205-312) — becomes
  per-`Dealership` (FK) instead of singleton. `services/dealer_config.py:127-275`
  resolver — becomes per-`Dealership`, still preserving env-override
  and default-fallback layers.
- **Leave untouched.** The 8 SESSION_032 indie shape-of-business
  fields (models.py:290-302). The `DealerProfile` dataclass shape in
  `services/dealer_config.py:62-83`. Field additions are out of scope;
  only the *carrier* changes.

### 1.2 Real authentication

- **Why.** Ledger data (Milestone 2), credit-app data (Milestone 10),
  and BHPH customer/payment data (Milestone 12) are all more sensitive
  than any string the scrub stack protects today. Auth is the
  compliance prerequisite for each.
- **Citation.** `FINANCE_DEPARTMENT_MAPPING.md:36` — F&I "the paper app
  that a walk-in customer fills out at the desk is *the most sensitive
  document in the building*." Reinforced by §6.4 (GLBA Safeguards
  Rule) and §6.9 (records retention 2–7yr).
  `BHPH_OPERATIONS_MAPPING.md:928-940` — FDCPA / TCPA / FCRA
  obligations on collection communications. `VEHICLE_CENTRIC_PIVOT.md:402-405`
  — item #2 of "Technical debt to pay down FIRST": *"Real auth +
  role-based permissions… Zero auth exists today."*
- **Extend.** Django's built-in `django.contrib.auth` (already in
  `INSTALLED_APPS`, already in `MIDDLEWARE` — currently inert). DRF's
  authentication/permission classes (currently absent from
  `REST_FRAMEWORK` in `settings.py:100-103`). Session or token auth —
  either is fine; the point is to *use* what's already installed
  rather than pull a new framework.
- **Leave untouched.** The `AllowAny` behavior of
  `/api/dealer-ai/chat/*` and `/api/dealer-ai/vehicles/<id>/ask/`.
  These are the customer-facing chat endpoints; the customer is not a
  user of the platform. The safety stack (§3.1) is unrelated to auth
  and must not be modified for it.

### 1.3 Role-based permissions

- **Why.** Roadmap explicitly names 7 roles: `dealer_owner`,
  `sales_manager`, `recon_manager`, `f_and_i_manager`, `collections`,
  `advisor`, `porter`. Each subsequent milestone will scope its own
  surfaces to these roles; Milestone 1 provides the vocabulary and
  the enforcement mechanism, not per-surface scoping.
- **Citation.** `IMPLEMENTATION_ROADMAP.md` §Milestone 1 Gap — the 7
  roles enumerated. `BUSINESS_DOMAIN_MAP.md:847-895` (§7
  Cross-department responsibility flow) — the business justification
  for role separation (Owner authorizes buys/repos/hardship; F&I owns
  compliance; Recon Manager owns front-line-ready; Accounting owns
  ledger truth; etc.).
- **Extend.** Django's `Group` / `Permission` system, or a lightweight
  `UserRole` mapping — either is fine. Roles attach to `User` scoped
  by `Dealership` (a user has role X *at* dealership Y).
- **Leave untouched.** Per-surface role gating on non-Milestone-1
  surfaces. Milestone 1 does NOT re-scope the trends dashboard, the
  ad-copy generator, or the leads pipeline UI to any role — those
  role scopings arrive with the milestone that owns the surface.
  Milestone 1 only enforces role checks where the *auth replacement*
  directly requires it (see 1.4).

### 1.4 Advisor-workspace slug-by-obscurity replacement

- **Why.** The only "access control" today on
  `/api/dealer-ai/advisor/<slug>/*` is `Salesperson.slug` being
  unguessable (views.py:462-463, 514-520). This is the specific auth
  debt Milestone 1 must resolve — it's the one endpoint that returns
  another user's lead data.
- **Citation.** `CAPABILITY_MATRIX.md:296` — *"Auth is by slug
  obscurity for the advisor workspace. Real auth was earmarked for a
  Phase 5 that hasn't happened."* Roadmap §Milestone 1 Gap: *"Advisor
  workspace slug-by-obscurity replaced by real auth."*
- **Extend.** The existing `advisor_workspace()` and
  `advisor_follow_up()` view functions (views.py:452-497, 500-564).
  Keep the URL shape (`/api/dealer-ai/advisor/<slug>/`) if possible —
  the frontend already routes to it — but require an authenticated
  `User` linked to `Salesperson` where `Salesperson.slug == slug` AND
  `Salesperson.dealership == request.user.dealership` AND
  `request.user.role in {advisor, dealer_owner}` (owner can view any
  advisor's queue).
- **Leave untouched.** The advisor's data shape (own leads only), the
  `invented_appointment` scrub in the follow-up draft path, the
  403-on-not-assigned lead check (views.py:529). The security
  *contract* is preserved; only the mechanism changes.

### 1.5 Migration path — singleton → per-tenant

- **Why.** The app runs today on a singleton `DealerOnboardingProfile`.
  Existing installs (including the dev database) must land in a valid
  multi-tenant state after Milestone 1 without operator intervention
  or data loss. This is the "every implementation decision must leave
  the application in a usable state" clause.
- **Citation.** `PROJECT_RULES.md` §Preserve Existing Code —
  reconciliation cadence starts with "What already exists?"
- **Extend.** Django migrations. Add a data migration in the same PR
  as the schema migration:
  1. Schema migration adds `Dealership` and nullable FKs on `Vehicle`,
     `Salesperson`, `ChatSession`, `ChatMessage`, `CustomerLead`,
     `DealerOnboardingProfile`.
  2. Data migration creates *one* `Dealership` row (name from
     `DealerOnboardingProfile.dealership_name` or env
     `DEALER_AI_DEALER_NAME` or `"Default Dealership"`), then
     backfills every existing row's FK to that Dealership.
  3. A follow-up migration flips the FKs to `NOT NULL` after backfill
     is verified.
- **Leave untouched.** The env-override path (`DEALER_AI_DEALER_NAME`,
  `DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`). In single-tenant
  local dev with no `Dealership` row explicitly configured, the
  resolver still returns the same result it does today. The Copper
  Canyon defaults still apply.

---

## 2. Migration Impact Review

Every existing system Milestone 1 touches, with the concrete work
required per system. Systems marked **NO IMPACT** are noted so nothing
goes unaccounted-for.

| # | System | Location | Impact | Work required |
|---|---|---|---|---|
| 1 | Dealer identity resolver | `services/dealer_config.py:127-275` | **Extended.** `get_dealer_name()`/`get_dealer_profile()` become per-`Dealership` lookups. Fall-back layers (env → default) preserved. | New signature accepts an optional `Dealership` (or reads from request context via `get_current_dealership()`). Existing callers pass in the current tenant, or use a `_default` helper for tenantless call sites (Django admin, management commands, tests). |
| 2 | Dealer onboarding profile | `models.py:205-312`, `views.py:876-967`, `serializers.py:390-434` | **Extended.** Loses singleton assumption. Gains `dealership` FK (unique). | Migration adds FK; data migration creates default `Dealership` + backfills. View changes `.objects.first()` → `.objects.get(dealership=request.user.dealership)`. Serializer unchanged (fields identical). |
| 3 | Advisor workspace | `views.py:452-564`, `urls.py:64-71` | **Replaced (auth mechanism).** URL shape preserved. Access moves from slug-obscurity to `IsAuthenticated + AdvisorForSlug + SameDealership`. | New DRF permission classes. `advisor_workspace()` and `advisor_follow_up()` add `authentication_classes`/`permission_classes`. Lead ownership check (views.py:529) preserved verbatim. |
| 4 | Customer chat + vehicle Q&A | `views.py` (chat/message, chat/start, vehicles/<id>/ask), `services/chat_engine.py`, `services/vehicle_assistant.py` | **Extended (tenant scoping only, no auth added).** The customer is not a platform user. Endpoints stay `AllowAny`. But `ChatSession`, `ChatMessage`, and matched-vehicle queries need `dealership` filtering. | Resolve `Dealership` from an incoming header (e.g. `X-Dealership-Slug`) or from the domain, or fall back to "the default dealership" for single-tenant. Scope querysets. **No behavior change** — same guards, same scrubs, same math. |
| 5 | Leads pipeline (admin) | `views.py` (admin/pipeline, admin/leads, admin/lead/<id>/*, admin/audit-events, admin/trends) | **Extended.** Admin endpoints move to `IsAuthenticated + IsSalesManagerOrOwner + SameDealership`. Querysets scoped by `dealership`. | Add auth to each admin endpoint. Scope every `Lead.objects.*`, `ChatSession.objects.*`, `Salesperson.objects.*` to the requesting user's dealership. No UI-visible behavior change for the operator when logged in. |
| 6 | Salesperson admin + team page | `views.py` (admin/salespeople, salespeople/, salespeople/<slug>/) | **Extended.** Admin listing gains auth. Public listing stays public but tenant-scoped. | Same pattern as #5. Public listing needs a way to resolve tenant (same mechanism as #4). |
| 7 | Vehicle model + inventory import | `services/inventory_import.py`, `models.py` Vehicle | **Extended.** `Vehicle` gains `dealership` FK. Unique constraint on `stock_number` becomes `(dealership, stock_number)`. Importer accepts a `dealership` argument. | Migration + backfill. Importer signature change + one call-site update per management command / API endpoint that invokes it. |
| 8 | Manager coaching chat | `POST /api/dealer-ai/manager-chat/` | **Extended.** Stateless endpoint gains auth (manager-only role). No state stored, so no tenant-scoping needed on data, only on the caller. | Auth + role check. Behavior contract (Shape A / Shape B enforcement) preserved. |
| 9 | Ad-copy generator | `POST /api/dealer-ai/admin/ad-copy/` | **Extended.** Admin endpoint gains auth. Because drafts are ephemeral, no per-tenant data migration needed. | Auth + role check. The `invented_promotion` scrub is unrelated to auth and stays put. |
| 10 | Onboarding UI endpoints | `GET/PUT /api/dealer-ai/onboarding/profile/`, `POST .../logo/` | **Extended.** Currently anyone can PUT — this is the biggest live security debt after advisor-slug obscurity. Move to `IsAuthenticated + IsDealerOwner + SameDealership`. | Auth + role check. Singleton `.first()` becomes per-tenant lookup. |
| 11 | Existing test baseline | `backend/dealer_ai/tests/` (57 files, 1,300 tests) | **At risk.** Many tests presumably call endpoints without auth. Any test that hits an endpoint now behind auth needs a fixture that supplies an authenticated request. Any test that instantiates a model that gained a required FK needs the FK. | Add a shared test fixture (e.g. `default_dealership()`, `authenticated_client(role=...)`). Sweep test files for direct model construction. Baseline 1,300 pass must be preserved; auth-related tests should *add* to the total. |
| 12 | Frontend fetch layer | `frontend/src/lib/*`, hooks like `useBrand()`/`useDealerProfile()`/`useOnboardingProfile()` | **Extended.** Public pages that currently hit `/api/dealer-ai/onboarding/profile/` unauthenticated will 401 after Milestone 1 if that endpoint gains auth. | The GET side of onboarding profile likely needs to stay `AllowAny` (branding is public — same reason CSS is public), or a lightweight public `GET /branding/` endpoint is carved out. Any operator page (leads, admin, coaching) needs a login page + `Authorization` header propagation. |
| 13 | Frontend brand tokens | `frontend/src/lib/brand.ts`, `tailwind.config.js`, `frontend/src/config/defaultDealer.ts` | **NO IMPACT.** Runtime brand tokens are consumed via `useBrand()`; as long as that hook can still resolve, styling is untouched. | None. |
| 14 | Chat safety stack | `services/llm_safety.py` and all scrub modules | **NO IMPACT.** Milestone 1 does not touch the 16-stage pipeline. | None. |
| 15 | Payment engine | `services/payment_engine.py` | **NO IMPACT.** Deterministic math is stateless. | None. |
| 16 | Franchise env-override config path | `DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<OEM>` | **Preserved.** Must continue to work for single-tenant local dev. | The resolver's env-override layer stays intact and takes precedence over the (new) per-tenant DB row when no explicit tenant context exists. |
| 17 | Dealer OS demo assets | `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`, `public/sams-freedom-ford-logo.jpg` | **NO IMPACT.** | None. |
| 18 | Django admin at `/admin/` | Uses `django.contrib.auth` today | **NO IMPACT.** Already authenticated. | None. |

---

## 3. Compatibility Checklist

**Milestone 1 shipped at SESSION_044. Every item verified true;
evidence recorded inline.** Original invariants preserved; each
row now cites the test class, code location, or runtime probe that
locks it. Where an item's outward behavior changed intentionally
(e.g. slug-obscurity 404 → real-auth 403), the annotation records
the new invariant + the reason.

### Existing onboarding flow
- [x] `GET /api/dealer-ai/onboarding/profile/` returns the same shape (35 fields including the 8 SESSION_032 indie fields).
  *Locked by `test_onboarding_profile.OnboardingDefaultsTests.test_get_returns_defaults_when_no_profile`. Endpoint at `views.py::onboarding_profile`; GET stays public via `[ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]`.*
- [x] `PUT /api/dealer-ai/onboarding/profile/` still upserts, now scoped to the authenticated user's dealership.
  *Locked by `test_onboarding_profile` + `test_admin_endpoints_auth.OnboardingProfileMutationAuth`. Requires `IsDealerOwnerAtActiveDealership`; `sales_manager` is 403.*
- [x] `POST /api/dealer-ai/onboarding/profile/logo/` still accepts multipart upload.
  *Locked by `test_onboarding_profile` + `test_admin_endpoints_auth.OnboardingLogoUploadRequiresDealerOwner`.*
- [x] `/dealer-ai-onboarding` UI (6 sections) still saves.
  *Frontend route wrapped in `<RequireAuth>` per `main.tsx`; `saveOnboardingProfile()` uses `authFetch` (`api.ts`). Verified via browser smoke at SESSION_043 (owner signed in → onboarding page → save).*

### Existing inventory import
- [x] `services/inventory_import.py` still upserts by `stock_number` per source, now scoped to a dealership.
  *`inventory_import.import_rows(..., dealership: Optional[Dealership] = None)` — line 288. When omitted, resolves to `get_default_dealership()`. Existing tests unchanged; SESSION_038 handoff §"Explicit dealership= sweeps".*
- [x] `Vehicle.last_seen_at` / `Vehicle.imported_at` semantics unchanged.
  *`test_inventory_import*` unchanged; the two fields are set only by the importer, whose behavior contract is preserved.*
- [x] The seed_phase3_demo (Copper Canyon 45-unit dataset) still loads cleanly against a default dealership.
  *Verified via SESSION_038 dev-DB reseed (135 vehicles post-seed per SESSION_038 handoff). Full baseline includes seed-consuming tests.*

### Existing vehicle behavior
- [x] `GET /api/dealer-ai/vehicles/<id>/` still returns payment analysis.
  *`views.py::vehicle_detail` unchanged (customer-facing, `AllowAny`). `test_vehicle_assistant` covers.*
- [x] `POST /api/dealer-ai/vehicles/<id>/ask/` still passes through the 16-stage safety stack unchanged.
  *`test_post_llm_safety` + `test_vehicle_assistant` — 90+ tests exercise the scrub stack; every one passes at the 1,466 baseline.*
- [x] `Vehicle.is_available` boolean semantics unchanged.
  *No `is_available` handling touched during Milestone 1. Computed-lifecycle refactor is deferred per §5 (Milestone 5 scope).*

### Existing advisor workflow (updated to record 4C invariants)
- [x] Advisor sees own leads only.
  *Unchanged. `views.py::advisor_workspace` still filters `CustomerLead.filter(assigned_to=sp)`.*
- [x] Follow-up drafts still pass through `invented_appointment` scrub.
  *`test_follow_up` exercises the scrub — no service-layer change.*
- [x] 403 still returned when a lead isn't assigned to this advisor.
  *Preserved verbatim (`views.py:597` — the `lead.assigned_to_id != sp.pk` check). Locked by `test_advisor_workspace_auth.AdvisorFollowUpAuthorization.test_lead_ownership_still_enforced_for_authorized_caller`.*
- [x] The URL `/dealer-ai-advisor/:slug` still resolves once logged in.
  *`main.tsx` route unchanged; wrapped in `<RequireAuth>`. Verified via SESSION_043 browser smoke steps 3, 4, 7.*
- [x] **New (4C):** unknown or deactivated advisor slugs return 403, not 404, to authenticated non-privileged callers. Reason: slug obscurity was the *thing being replaced* by real auth; returning 404 for missing slugs would re-leak existence via differential status codes. Locked by `AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs`.

### Existing chat behavior
- [x] All 8 pre-LLM guards fire in existing order.
- [x] All 8 post-LLM scrubs + fabricated-inventory + invented-promotion + invented-appointment + indie-prohibited-copy scrubs run.
- [x] Every dollar figure still comes from `payment_engine.py`.
- [x] Budget-fit classification (`fit / near_fit / over_budget`) unchanged.
- [x] The customer never encounters auth.
  *All five locked by the pre-existing scrub / payment-engine / budget-flow / demo-scenarios test suites (~700+ tests in the 1,466 baseline). Customer chat endpoints (`chat/start`, `chat/message`, `vehicles/<id>/ask`) remain `AllowAny` — verified by `views.py` review + `test_admin_endpoints_auth.PublicBrandingRemainsUnauthenticated`.*

### Existing dealer configuration resolution
- [x] Env-override still works: `DEALER_AI_DEALER_NAME=<name>` beats the DB row.
- [x] Franchise config path still works: `DEALER_AI_DEALER_TYPE=franchise` + `DEALER_AI_PRIMARY_MAKE=Ford` produces franchise-shaped `DealerProfile`.
- [x] Copper Canyon defaults still apply when neither env nor DB row is set.
- [x] `get_dealer_name()` and `get_dealer_profile()` still return the same shape.
  *All four verified at SESSION_044 close via a fresh-process smoke script (see retrospective §"Regressions avoided"). Note: SESSION_044 wired `DEALER_AI_DEALER_TYPE` and `DEALER_AI_PRIMARY_MAKE` into `settings.py` — the resolver reads them via `getattr(settings, ...)` and the settings entries were missing pre-4F, so the invariant was effectively broken. Two-line fix landed in the 4F commit.*

### Existing branding
- [x] `useBrand()` and `useDealerProfile()` still resolve without a logged-in user.
  *`brand.ts::useBrand` calls `fetchOnboardingProfile()` which uses plain `fetch` (not `authFetch`). GET `/onboarding/profile/` is public via `ReadOnly` composition. Locked by `test_auth_endpoints.PublicBrandingRemainsUnauthenticated`.*
- [x] `brand.*` Tailwind tokens unchanged.
  *`tailwind.config.js` untouched during Milestone 1.*
- [x] Public routes (`/`, `/assistant`, `/showroom`, `/embed/assistant`) still render unauthenticated.
  *`main.tsx` routes public routes OUTSIDE `<RequireAuth>`. Verified via SESSION_043 browser smoke step 8.*

### Existing AI behavior
- [x] Same LLM provider abstraction (OpenAI / Ollama) — no changes to `services/llm_client.py` or equivalent.
- [x] `INDIE_MODE_HINT` injection unchanged for indie configs.
- [x] `Ford-first` ranking generalized to `primary_make` unchanged.
- [x] Ad-copy generator still produces 2–3 variants, still passes through `invented_promotion` scrub.
- [x] Manager coaching chat still enforces Shape A / Shape B.
  *All five locked by `test_indie_mode_hint`, `test_ad_copy`, `test_manager_chat`, and the LLM factory tests — none of these files were touched by Milestone 1's service-layer `dealership=` threading (that argument was added; behavior for existing callers unchanged).*

### Existing test baseline
- [x] `python3 manage.py test dealer_ai` → **1,466 pass** (grew from 1,300 pre-Milestone-1 baseline via +166 new tenancy / auth / permission / scoping / auth-endpoint tests), 1 skipped.
- [x] No test suppressed with `@skip` to make the baseline pass.
  *Grep of `tests/` shows the single pre-existing `@skip` (unchanged from SESSION_037).*
- [x] Frontend `npx tsc --noEmit` still clean.
- [x] Frontend `npx vite build` still clean.
  *Both verified at SESSION_044 close; same pre-existing chunk-size warning as SESSION_042/043 (unrelated to auth work).*

### New (Milestone 1 introduced these invariants)
- [x] `DEFAULT_PERMISSION_CLASSES` remains **unset**. The DRF `AllowAny` default stands. Locked by `test_current_dealership.DrfAuthenticationDefaultsIntegration.test_default_permission_classes_remain_unset`.
- [x] Six tenant-carrying models (`Vehicle`, `Salesperson`, `ChatSession`, `ChatMessage`, `CustomerLead`, `DealerOnboardingProfile`) enforce `dealership` FK as **NOT NULL**. Locked by `test_dealership.WritePathFallback` + `test_fk_is_now_not_null`.
- [x] Every write path either passes `dealership=` explicitly OR is caught by the `pre_save` autofill signal that attaches the default. Locked by `test_dealership.WritePathFallback`. **The pre_save signal is a fallback safety net, not the preferred write mechanism** — production views pass `dealership=get_current_dealership(request)` explicitly. Recorded in `AUTHENTICATION_MODEL.md` §8b.
- [x] `get_current_dealership(request)` never returns `None` and never raises on unknown header slugs. Locked by `test_current_dealership.GetCurrentDealershipResolver`.
- [x] Cross-tenant pk lookups on admin endpoints fail closed (404), never 200 with cross-tenant data. Locked by `test_admin_endpoints_auth.AdminLeadDetailFailsClosedAcrossTenants`.
- [x] Cross-tenant salesperson body on `admin_lead_assign` returns 400. Locked by `test_admin_endpoints_auth.AdminLeadAssignRejectsCrossTenantSalesperson`.
- [x] Login endpoint returns identical 401 body for wrong password AND unknown user (no user enumeration). Locked by `test_auth_endpoints.AuthLoginEndpoint.test_unknown_user_returns_same_generic_401`.
- [x] Authenticated unsafe methods require `X-CSRFToken`. Locked by `test_auth_endpoints.CsrfEnforcedOnAuthenticatedMutations`.
- [x] `CSRF_TRUSTED_ORIGINS` includes the Vite dev origin (env-configurable). Confirmed by SESSION_043 browser smoke — pre-4E, every authenticated POST 403'd with "CSRF Failed: Origin checking failed".
- [x] Frontend distinguishes 401 (redirect to `/login`) from 403 ("Not authorized" surface, stays on page). Locked by `authFetch.ts` typed errors + `RequireAuth.tsx` behavior + SESSION_043 browser smoke step 4.

---

## 4. Reusable Primitives Review

Two roadmap primitives are cited by Milestone 1 (§3.9 dealer_config
resolver, §3.10 onboarding profile). Both **should be extended, not
paralleled**. A third — the safety stack — is untouched but
load-bearing on the compatibility checklist.

### §3.9 Dealer identity resolver — `services/dealer_config.py`

- **Current shape.** Frozen `DealerProfile` dataclass with 9 fields.
  Two resolution functions (`get_dealer_name`, `get_dealer_profile`)
  each with a documented fallback chain (DB → env → default).
- **Sufficient for Milestone 1?** *Yes, with extension.* The DB layer
  of the fallback chain becomes per-`Dealership` lookup instead of
  `.first()`. Env and default layers unchanged. Function signatures
  gain an optional `dealership` argument that, when omitted, resolves
  via a `get_current_dealership()` helper (request-context or
  single-tenant fallback).
- **Extension justification.** The resolver *is* the tenancy
  read-path. Building a second one would violate `PROJECT_RULES.md`
  §Preserve Existing Code and §Anti-patterns (*"Reimplementing dealer
  identity resolution outside of `services/dealer_config.py`"*).
- **Callers to sweep.** 10 files import it: chat_engine, ad_copy,
  inventory_search, llm_safety, lead_service, follow_up,
  handoff_service, vehicle_assistant, plus two test files. Each
  callsite either propagates the tenant (via request or explicit arg)
  or accepts the single-tenant fallback.

### §3.10 Onboarding profile — `DealerOnboardingProfile`

- **Current shape.** Singleton, 35 fields. Enforced-in-code, not
  schema (uses `.first()` + upsert).
- **Sufficient for Milestone 1?** *Yes, with extension.* Add
  `dealership = OneToOneField(Dealership)`. Enforce uniqueness in
  schema (a `Dealership` has exactly one `DealerOnboardingProfile`).
  The 8 SESSION_032 indie fields are preserved verbatim — Milestone 1
  adds no fields.
- **Extension justification.** Same as §3.9 — an alternate profile
  store would double the config surface and break every existing
  caller.
- **What Milestone 1 does NOT change.** The 35-field schema. The
  serializer. The onboarding form UI. The logo upload flow.

### §3.1 Safety stack — `services/llm_safety.py`

- **Load-bearing but untouched.** Every compatibility-checklist item
  under "existing chat/AI behavior" traces to this primitive.
  Milestone 1 does not modify it. Cited only so it's on the record as
  *why* the compatibility invariants hold.

### Genuinely greenfield in Milestone 1

- **`Dealership` model.** No existing primitive. Small — just an
  identity carrier (`name`, `slug`, timestamps).
- **`User` role attachment.** Django's `Group`/`Permission` model is
  present but unused. Extending it (vs. a custom `UserRole` table) is
  a judgment call to be made in the implementation session under
  Research Before Design — but *within* Django's built-ins either way.
  **No new auth framework.**
- **DRF authentication + permission classes.** The `REST_FRAMEWORK`
  config is currently minimal (no `DEFAULT_AUTHENTICATION_CLASSES`,
  no `DEFAULT_PERMISSION_CLASSES`). Milestone 1 adds them. This is
  greenfield config work, not a parallel implementation.
- **Frontend login page + auth header propagation.** Greenfield UI.
  Should live in `frontend/src/pages/Login.tsx` (or equivalent) and
  hook into the existing `fetch()` layer via a shared `authFetch()`
  helper.

**No parallel implementations proposed.** Every Milestone 1 change
either extends a §3 primitive or adds greenfield in a place that had
no primitive.

---

## 5. Scope Discipline + Deferrals

Ideas that surfaced during this pass that would expand scope beyond
Milestone 1. Per the Discovery Rule: **deferred, not discarded.**

| Idea | Why it's tempting | Discovery-Rule verdict | Deferred to |
|---|---|---|---|
| Multi-photo file storage (S3-compatible + CDN) | VCP `:406-407` names it as item #3 of "Technical debt to pay down FIRST" | Not required for Milestone 1. Milestone 3 introduces the first real multi-photo need; roadmap §6 notes this as a preserved tension for a pre-M3 decision. | Milestone 3 or a pre-M3 half-milestone |
| `Vehicle.is_available` → computed property | VCP `:408-410` names it as item #4 of "Technical debt to pay down FIRST" | Not required for Milestone 1 auth/tenancy. It's a Milestone 5 concern (lifecycle stages). | Milestone 5 |
| `Vehicle.make` default `"Ford"` rename | VCP `:411-414` names it as item #5. Harmless today. | Not required. | Milestone 2 or Milestone 5 opportunistically |
| SSO / MFA | Frequently expected in enterprise auth | Explicitly out-of-scope per roadmap §Milestone 1 scope boundary. Not currently research-motivated. | Not scheduled; needs research trigger |
| User-management UI beyond sign-in | Feels natural next to auth | Explicitly out-of-scope per roadmap §Milestone 1. | Later milestone if research surfaces need |
| Per-role UI polish (dashboards, sidebars) | Feels natural next to role model | Explicitly out-of-scope. Each subsequent milestone applies role scoping to its own surfaces. | Distributed across Milestones 2+ |
| `VehicleAcquisition` / `VehicleListing` / `VehicleStage` OneToOne factoring | VCP `:258-263` names it as a structural change | Belongs to Milestones 2, 5, 6. | Milestones 2 / 5 / 6 |
| `LeadVehicleInterest` through-model annotation | VCP `:265-268` names it | Belongs to Milestone 9. | Milestone 9 |
| Removing the singleton `.first()` upsert pattern generally | Feels like cleanup natural to touch | Only remove it *where* Milestone 1 requires it (onboarding profile). Anywhere else it exists, leave it. | Whichever future milestone touches that surface |
| Public-vs-authenticated split on `/api/dealer-ai/onboarding/profile/` GET | Branding is public; profile edits are not. Splitting the endpoint would be cleaner. | Justified within Milestone 1 IF the frontend requires it to keep the customer-facing chat page rendering. Otherwise defer to when a second tenant needs branding. Small enough to fold in if the compatibility checklist demands it. | Decide during implementation session; small enough to fold in |
| Prod deployment (Render Blueprint activation) | Roadmap §5 architectural notes call it out | Not a milestone in itself. Milestone 1 does not require prod. | Alongside the first milestone whose consumers are field-based (probably M2) |

**`docs/DEFERRED_IDEAS.md` should be created** the first time an idea
surfaces during Milestone 1 implementation that does not fit in a
milestone plan doc (per `PROJECT_RULES.md` §Discovery Rule and
`00-START-NEXT-SESSION.md`). The table above lives in this planning
pass and can be lifted into that file when it's created.

---

## 6. Anchors that win on conflict

If this planning doc disagrees with:

1. `docs/PROJECT_RULES.md` — the rules win.
2. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — the roadmap
   wins on scope questions.
3. `docs/research/*_MAPPING.md` and `*_PIVOT.md` — the research wins
   on business-truth questions.
4. `docs/CAPABILITY_MATRIX.md` — the matrix wins on "what does the
   software actually do today?" questions.
5. Current source code — the code wins on "what does the software
   actually do today?" questions.

Planning docs are claims. Rules + research + code are facts.

---

## 7. Increment sequencing (as-shipped)

The design memo (§1) describes *what* Milestone 1 delivers. This
section records *how* the work was sliced into per-session
increments so future readers understand the commit history and each
handoff's scope. Increments 1–3 shipped in SESSION_037–038;
Increments 4A–4F carry Milestone 1 to completion.

### Shipped

- **Increment 1 (SESSION_037, commit `36a4d74`)** — `Dealership`
  tenancy-root model in isolation. Schema migration `0007`. Model
  shape locked by 4 tests.
- **Increment 2 (SESSION_037, commit `0e7e710`)** — Nullable
  `dealership` FK on the six tenant carriers (`Vehicle`,
  `Salesperson`, `ChatSession`, `ChatMessage`, `CustomerLead`,
  `DealerOnboardingProfile`) via schema migration `0008`; data
  migration `0009` seeds the default `Dealership` row (slug=`default`)
  and backfills every existing row via a three-tier name-resolution
  ladder. Post-backfill count check inside a transaction, so a
  partial backfill can never commit. +9 tests.
- **Increment 3 (SESSION_038, commit `9ea7ff3`)** — Write-path
  plumbing. New `services/tenancy.py` primitive
  (`get_default_dealership` + `pre_save` autofill signal registered
  in `DealerAiConfig.ready`; signal also inherits from parent
  `ChatSession` for `ChatMessage` / `CustomerLead`). Extended
  `dealer_config.py` resolvers with optional `dealership=` argument.
  Explicit `dealership=` sweeps in `views.py`,
  `services/lead_service.py`, `services/inventory_import.py`.
  Migration `0010` flips all six FKs to `NOT NULL`. +9 tests
  (1,313 → 1,322).

### Remaining — Increment 4 sub-sequencing (A–F)

Each sub-increment is a single-session unit. Every one leaves the
application deployable and the test baseline healthy. The scope
boundary between sub-increments is a scope-discipline choice — a
single monolithic "auth increment" is high-blast-radius work with
poor rollback granularity, so the sequencing below trades one long
session for six smaller ones with independent verification points.

**4A — User↔Dealership membership + role foundation.**
Introduce the tenant-scoped role vocabulary from
`IMPLEMENTATION_ROADMAP.md` §Milestone 1 (`dealer_owner`,
`sales_manager`, `recon_manager`, `f_and_i_manager`, `collections`,
`advisor`, `porter`). Preferred shape: a small
`UserDealershipRole` through-model (User FK, Dealership FK, role
CharField with choices, timestamps) so a User can hold different
roles at different dealerships without collapsing the semantics
into Django `Group`. Extend `Salesperson` with an optional
`user = OneToOneField(User, null=True)` link so Increment 4C can
resolve advisor identity from the authenticated user. Django admin
registration for both. Zero endpoint auth changes. Migration +
model tests only.

*Design note (recorded post-implementation, SESSION_039).* The
shipped `UserDealershipRole.unique_together = (user, dealership,
role)` **permits multiple concurrent roles for a single user at a
single dealership** (e.g. an indie owner who also acts as sales
manager). This is an intentional architectural decision, not an
accident of the uniqueness constraint. Rationale:

1. **Business reality of small indie dealerships.** Copper Canyon
   Auto (the default persona) and the wider indie market routinely
   run with owner-operators wearing multiple hats. Collapsing
   `dealer_owner` + `sales_manager` into a single row would either
   force artificial choice or require a "primary role" concept
   that doesn't exist in the roadmap.
2. **Role composition, not role hierarchy.** The seven roles in
   §Milestone 1 name **responsibilities** (owns credit apps, owns
   recon queue, etc.), not seniority tiers. Multiple
   responsibilities per person is the natural business shape.
3. **Authorization is additive.** Increments 4C/4D check "does
   this user hold role X at this dealership?" — a set-membership
   query. Multi-role is expressible as `roles.filter(role__in=...)`
   without any active-role selection.
4. **Reversibility.** If a future increment needs "the single
   active role" (e.g. for a UI badge), it can layer that concept
   on top — either via role priority (`dealer_owner` wins), an
   explicit user preference persisted elsewhere, or a session-
   scoped active-role selection. None of those require altering
   4A's uniqueness constraint. The reverse — retrofitting
   multi-role onto a "one active role per dealership" schema —
   would break every historical row where the constraint was
   satisfied by dropping data.

**Trade-off accepted.** The resolver in 4B
(`get_active_membership`) must therefore choose deterministically
when a user holds multiple memberships at the same dealership.
Documented in 4B below as a distinct concern with its own
extension seam.

**4B — DRF authentication classes + request-context tenancy.**
Populate `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` with
`SessionAuthentication` (customer chat stays cookie-friendly for
the embed frame) plus `TokenAuthentication` for API clients. Add
`rest_framework.authtoken` to `INSTALLED_APPS` and run its
migration. **`DEFAULT_PERMISSION_CLASSES` is not set** — the
framework default (`AllowAny`) stands. Enforcement is 4C/4D; 4B
only establishes that requests *carry* identity when credentials
are present.

Extend `services/tenancy.py` with two helpers, split so that the
layers separate cleanly:

1. `get_active_membership(user)` — the **which of this user's
   memberships is active?** helper. Increment 4B ships the
   single-membership implementation (returns the sole
   `UserDealershipRole` when there is exactly one; deterministic
   `.first()` by ordering when there are several; `None` when
   there are none). This helper is the extension seam — future
   dealership-switching UI replaces its body with an explicit
   session-persisted selection, without altering
   `get_current_dealership`.
2. `get_current_dealership(request)` — the request-context
   resolver. Composes three orthogonal signals in priority order:
   authenticated identity (via `get_active_membership`), explicit
   request signal (`X-Dealership-Slug` header matched against a
   live `Dealership`), then `get_default_dealership()` as the
   terminal fallback. Never returns `None`.

Resolver tests only; no endpoint changes. The layering — Identity
(authentication result) → Authorization (which dealership is
this user acting within) → Business permissions (what may they
do) — is preserved as three separate concerns; 4B does not touch
Business permissions.

**4C — Advisor workspace slug-obscurity replacement.**
Replace the slug-only access check on
`/api/dealer-ai/advisor/<slug>/*` (views.py:452–564) with
`IsAuthenticated + AdvisorForSlug + SameDealership`. `AdvisorForSlug`
matches `request.user.salesperson.slug == slug`; `SameDealership`
matches the advisor's tenant against the requesting user's active
tenant. URL shape preserved. Lead-ownership check at views.py:529
preserved verbatim. Frontend still uses the slug URL — the login
UI lands in 4E, so this increment is verified via authenticated
DRF test-client calls. `dealer_owner` can view any advisor's queue
(per §1.4).

**4D — Admin endpoint gating + queryset scoping.**
Every `/api/dealer-ai/admin/*` endpoint moves to
`IsAuthenticated + IsSalesManagerOrOwner + SameDealership`. Every
`Lead.objects.*`, `ChatSession.objects.*`, `Salesperson.objects.*`
inside those endpoints gains a `.filter(dealership=...)` scoping
call. Includes: leads pipeline, admin leads list + detail,
salespeople admin, audit-events, trends, coaching (`manager_chat`),
ad-copy generator, onboarding profile (biggest live security debt
after advisor slug per §2 row 10 — moves to `IsDealerOwner`).
Customer-facing chat + vehicle Q&A stay `AllowAny` per §1.2 but
resolve tenancy from `get_current_dealership(request)` for queryset
scoping. Comprehensive test coverage: unauth → 401, wrong-role →
403, wrong-tenant → 403, correct → 200.

**4E — Frontend login + shared `authFetch()`.**
Greenfield `frontend/src/pages/Login.tsx` (or equivalent under the
existing routing structure). Shared `authFetch()` helper that
injects the `Authorization` / session cookie and handles 401 by
redirecting to `/login`. Every operator page (leads admin, coaching,
onboarding) uses `authFetch`; public pages (`/`, `/assistant`,
`/showroom`, `/embed/assistant`) do not. Persist auth state via a
lightweight context / hook, not a heavyweight state library.
Verified via `npx tsc --noEmit`, `npx vite build`, and manual
smoke of the login → leads-admin → logout flow in a browser.

**4F — Full compatibility sweep + hardening + Milestone 1 close.**
Walk every item in §3 of this doc and confirm it still holds.
Add integration tests spanning login → tenant scoping → advisor
workspace end-to-end. Verify the franchise env-override path
(`DEALER_AI_DEALER_TYPE=franchise`) still works under the new
resolver. Verify Copper Canyon defaults still ship for a
zero-config install. Verify the 16-stage scrub stack is byte-for-byte
untouched. Confirm no currently-public route regressed to 401
(branding, chat/*, vehicles/<id>/*, embed frame). Update
`docs/CAPABILITY_MATRIX.md` §7/§8 (auth model + roles now
implemented) and `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7
(Milestone 1 → complete). Handoff for closing out Milestone 1
and identifying Milestone 2 kickoff scope.

### Scope-discipline reminders that apply to every 4-series sub-increment

- ❌ No tenant-scoped uniqueness (`(dealership, stock_number)`,
  `(dealership, slug)`, `DealerOnboardingProfile` OneToOne) — those
  belong to the increment that first needs them.
- ❌ No multi-photo storage, no `Vehicle.is_available` → computed,
  no `Vehicle.make` default rename. All deferred per §5.
- ❌ No SSO / MFA. Explicitly out-of-scope per §5.
- ❌ No per-role UI polish beyond what auth strictly requires.
- ❌ No changes to the 16-stage scrub stack.
- ❌ No changes to `services/payment_engine.py`.
- ❌ No deletion of the franchise config path or Dealer OS demo
  assets.

---

## 8. Related documents

- `docs/PROJECT_RULES.md` — governance layer.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — the implementation
  contract this planning pass serves.
- `docs/roadmap/ASSISTANT_AGENT_CREATION_ROADMAP.md` — the sibling
  roadmap for AI-agent creation surfaces.
- `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference.
- `docs/CAPABILITY_MATRIX.md` — what the software does today.
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` — architectural pivot that
  names auth/tenancy as Phase 0 blockers.
- `docs/research/FINANCE_DEPARTMENT_MAPPING.md` — compliance framing
  for Milestone 1.
- `docs/research/BHPH_OPERATIONS_MAPPING.md` — compliance framing for
  Milestone 1.
- `00-START-NEXT-SESSION.md` — the session priority that motivates
  this planning pass.

---

*End of Milestone 1 planning pass.*
