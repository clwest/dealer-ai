---
title: "Milestone 1 — Implementation-Planning Pass"
status: planning
type: planning-artifact
generated: 2026-07-31
generated_at_session: SESSION_035 (pre-implementation)
milestone: 1
milestone_name: "Multi-tenant + role-based access foundation"
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
| 17 | Freedom Ford demo assets | `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`, `public/sams-freedom-ford-logo.jpg` | **NO IMPACT.** | None. |
| 18 | Django admin at `/admin/` | Uses `django.contrib.auth` today | **NO IMPACT.** Already authenticated. | None. |

---

## 3. Compatibility Checklist

**Milestone 1 is not complete until every item below is verified true.**
These are the invariants the existing platform must uphold *after*
Milestone 1 ships. Each item is testable.

### Existing onboarding flow
- [ ] `GET /api/dealer-ai/onboarding/profile/` returns the same shape (35 fields including the 8 SESSION_032 indie fields).
- [ ] `PUT /api/dealer-ai/onboarding/profile/` still upserts, now scoped to the authenticated user's dealership.
- [ ] `POST /api/dealer-ai/onboarding/profile/logo/` still accepts multipart upload.
- [ ] `/dealer-ai-onboarding` UI (6 sections) still saves.

### Existing inventory import
- [ ] `services/inventory_import.py` still upserts by `stock_number` per source, now scoped to a dealership.
- [ ] `Vehicle.last_seen_at` / `Vehicle.imported_at` semantics unchanged.
- [ ] The seed_phase3_demo (Copper Canyon 45-unit dataset) still loads cleanly against a default dealership.

### Existing vehicle behavior
- [ ] `GET /api/dealer-ai/vehicles/<id>/` still returns payment analysis.
- [ ] `POST /api/dealer-ai/vehicles/<id>/ask/` still passes through the 16-stage safety stack unchanged.
- [ ] `Vehicle.is_available` boolean semantics unchanged (`Vehicle.is_available` → computed lifecycle is a Milestone 5 concern, NOT Milestone 1).

### Existing advisor workflow
- [ ] Advisor sees own leads only (same behavior).
- [ ] Follow-up drafts still pass through `invented_appointment` scrub.
- [ ] 403 still returned when a lead isn't assigned to this advisor.
- [ ] The URL `/dealer-ai-advisor/:slug` still resolves once logged in (frontend routing unchanged).

### Existing chat behavior
- [ ] All 8 pre-LLM guards fire in existing order.
- [ ] All 8 post-LLM scrubs + fabricated-inventory + invented-promotion + invented-appointment + indie-prohibited-copy scrubs run.
- [ ] Every dollar figure still comes from `payment_engine.py`.
- [ ] Budget-fit classification (`fit / near_fit / over_budget`) unchanged.
- [ ] The customer never encounters auth.

### Existing dealer configuration resolution
- [ ] Env-override still works: `DEALER_AI_DEALER_NAME=<name>` beats the DB row.
- [ ] Franchise config path still works: `DEALER_AI_DEALER_TYPE=franchise` + `DEALER_AI_PRIMARY_MAKE=Ford` produces franchise-shaped `DealerProfile`.
- [ ] Copper Canyon defaults still apply when neither env nor DB row is set.
- [ ] `get_dealer_name()` and `get_dealer_profile()` still return the same shape.

### Existing branding
- [ ] `useBrand()` and `useDealerProfile()` still resolve without a logged-in user (public pages must render).
- [ ] `brand.*` Tailwind tokens unchanged (Copper Canyon palette still ships as default).
- [ ] Public routes (`/`, `/assistant`, `/showroom`, `/embed/assistant`) still render unauthenticated.

### Existing AI behavior
- [ ] Same LLM provider abstraction (OpenAI / Ollama) — no changes to `services/llm_client.py` or equivalent.
- [ ] `INDIE_MODE_HINT` injection unchanged for indie configs.
- [ ] `Ford-first` ranking generalized to `primary_make` unchanged.
- [ ] Ad-copy generator still produces 2–3 variants, still passes through `invented_promotion` scrub.
- [ ] Manager coaching chat still enforces Shape A / Shape B.

### Existing test baseline
- [ ] `python3 manage.py test dealer_ai` → **at least 1,300 pass**, 1 skipped. Milestone 1 is expected to *add* auth/tenancy/permission tests, not remove existing ones.
- [ ] No test suppressed with `@skip` to make the baseline pass.
- [ ] Frontend `npx tsc --noEmit` still clean.
- [ ] Frontend `npx vite build` still clean.

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

## 7. Related documents

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
