---
title: "SESSION_039 handoff — Milestone 1 Increment 4A (User↔Dealership membership + role foundation)"
status: historical
type: handoff
date: 2026-07-31
session: 039
commits:
  - 92e3c48  # Increment 4A — UserDealershipRole model + Salesperson.user link + admin + tests
---

# SESSION_039 — Milestone 1 · Increment 4A

## What shipped

The identity substrate for Milestone 1's authentication phase. A new
``UserDealershipRole`` through-model expresses membership (a User is
attached to a Dealership in a specific role), and ``Salesperson``
gained an optional ``user`` OneToOne link. **Zero endpoint behavior
changed** — this increment is schema-only. Increments 4B / 4C / 4D
consume these primitives to enforce authentication, tenancy
resolution, and per-endpoint authorization.

### 1. Role vocabulary — module-level constants

``backend/dealer_ai/models.py`` — the seven canonical roles from
``docs/roadmap/IMPLEMENTATION_ROADMAP.md`` §Milestone 1 are declared
as module-level constants (``ROLE_DEALER_OWNER``,
``ROLE_SALES_MANAGER``, ``ROLE_RECON_MANAGER``,
``ROLE_F_AND_I_MANAGER``, ``ROLE_COLLECTIONS``, ``ROLE_ADVISOR``,
``ROLE_PORTER``) plus a ``ROLE_CHOICES`` tuple. Kept at module scope
so 4B/4C/4D import the canonical list without re-declaring string
literals. A locking test (``RoleVocabulary``) forces the roadmap
conversation before an eighth role could be added.

### 2. `UserDealershipRole` model

- ``user = FK(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="memberships")``
- ``dealership = FK(Dealership, on_delete=CASCADE, related_name="memberships")``
- ``role = CharField(max_length=32, choices=ROLE_CHOICES)``
- ``created_at``, ``updated_at`` timestamps
- ``Meta.unique_together = (("user", "dealership", "role"),)``
- ``Meta.ordering = ("user", "dealership", "role")``

Uniqueness allows a User to hold **multiple roles at the same
dealership** (owner + sales_manager is realistic in an indie shop)
and to **belong to multiple dealerships** with different roles. The
constraint only forbids the exact duplicate row.

### 3. `Salesperson.user` OneToOne link

- ``user = OneToOneField(settings.AUTH_USER_MODEL, on_delete=SET_NULL, null=True, blank=True, related_name="salesperson")``

Nullable during the backfill window; Increment 4C is the first
increment that requires the link to be present for authenticated
advisor workspace access. ``SET_NULL`` on user delete preserves
historical lead attribution (same rationale as ``is_active=False``
retention on Salesperson).

### 4. Admin registration

- ``UserDealershipRoleAdmin`` — bootstrap surface. A superuser creates
  the initial ``dealer_owner`` membership here before 4C ships. No
  custom forms; the default ``ModelAdmin`` is sufficient for the
  bootstrap window.
- ``DealershipAdmin`` — added so ``autocomplete_fields`` in
  ``UserDealershipRoleAdmin`` and ``SalespersonAdmin`` can target it.
  Read-mostly (the seeded ``slug=default`` row is created by migration
  0009).
- ``SalespersonAdmin`` — gained ``autocomplete_fields = ("user",)`` so
  the manager can link an existing auth user to an existing
  Salesperson row through the standard admin UI.

### 5. Migration `0011_userdealershiprole_and_salesperson_user.py`

Schema-only. Two operations:

1. ``AddField`` — ``Salesperson.user`` (nullable OneToOne).
2. ``CreateModel`` — ``UserDealershipRole``.

No data migration in 4A: ``django.contrib.auth`` is inert today per
SESSION_037 handoff, so there are no existing users to backfill. The
first ``dealer_owner`` membership is created manually via Django admin
before 4C ships.

### 6. Test suite

New file ``backend/dealer_ai/tests/test_userdealershiprole.py``. Three
test classes, 11 tests:

- ``RoleVocabulary`` (1 test) — locks the seven canonical roles.
- ``UserDealershipRoleModel`` (6 tests) — round-trip, unique_together
  enforcement, multiple roles at one dealership, membership at multiple
  dealerships, both reverse accessors (``user.memberships`` and
  ``dealership.memberships``).
- ``SalespersonUserLink`` (4 tests) — nullable during backfill,
  reverse accessor (``user.salesperson``), OneToOne uniqueness
  enforcement, ``SET_NULL`` preserves Salesperson row on user delete.

### Test baseline

- **1,322 → 1,333 pass, 1 skipped, 0 fail** (+11 new tests; zero
  regressions; no test suppressed with ``@skip``).

## Compatibility checklist verification (§3 of MILESTONE_1_PLANNING.md)

Every §3 item verified true after Increment 4A. Because 4A is
additive-only (one nullable FK on ``Salesperson`` + one brand-new
``UserDealershipRole`` table) the compatibility surface is preserved
without any explicit branching. The 1,322 pre-existing tests exercise
the §3 invariants directly; every one passes.

Spot-checked via smoke script:

- ✅ Copper Canyon defaults intact — ``dealer_type='independent'``,
  ``bhph_enabled=True``, ``makes_carried`` starts with
  ``('Toyota', 'Honda', 'Ford')``.
- ✅ ``get_dealer_name()`` / ``get_dealer_profile()`` shapes unchanged.
- ✅ Franchise env-override path unchanged (no resolver touched).
- ✅ All seven canonical roles resolve from ``ROLE_CHOICES`` via public
  import from ``dealer_ai.models``.
- ✅ Chat safety stack untouched — 1,333-test baseline (which is
  overwhelmingly safety-stack coverage) passes clean.
- ✅ Payment engine untouched.
- ✅ Onboarding profile serializer / view / URL shape unchanged.
- ✅ Inventory import signature unchanged.
- ✅ Frontend brand tokens / ``useBrand()`` — no frontend touched.

## Files touched

Created:

- ``backend/dealer_ai/migrations/0011_userdealershiprole_and_salesperson_user.py``
- ``backend/dealer_ai/tests/test_userdealershiprole.py``
- ``docs/handoffs/SESSION_039_milestone_1_membership_and_roles.md`` (this file).

Modified:

- ``backend/dealer_ai/models.py`` — role constants + ``ROLE_CHOICES`` +
  ``Salesperson.user`` OneToOne + ``UserDealershipRole`` model.
- ``backend/dealer_ai/admin.py`` — registered ``Dealership`` and
  ``UserDealershipRole``; added ``autocomplete_fields = ("user",)`` to
  ``SalespersonAdmin``.
- ``00-START-NEXT-SESSION.md`` — overwritten to point at SESSION_040
  (Increment 4B).

Not touched (correctly):

- ``settings.py::REST_FRAMEWORK`` — auth defaults are 4B.
- Any view — endpoint auth is 4C/4D.
- ``services/tenancy.py`` — ``get_current_dealership(request)`` is 4B.
- ``services/dealer_config.py`` — no resolver changes needed.
- Frontend — login UI is 4E.
- ``docs/CAPABILITY_MATRIX.md`` — outward behavior unchanged; matrix
  update lands in 4F when Milestone 1 closes.
- ``docs/roadmap/IMPLEMENTATION_ROADMAP.md`` §2.7 — flips to
  ``Y (Milestone 1 complete)`` only at 4F.
- ``docs/roadmap/MILESTONE_1_PLANNING.md`` — the §7 A–F contract
  matched what shipped; no deviation to record.
- 16-stage safety pipeline — untouched.

## Deviation from plan — none

The SESSION_039 recommended step sequence maps 1:1 to what shipped.
One additive detail worth flagging for the next reviewer: the
compatibility of the ``UserDealershipRole.unique_together`` contract
with the "one user, one active role per dealership" phrasing in the
session brief. The shipped model **permits multiple concurrent roles
per (user, dealership)** because the roadmap's role list explicitly
distinguishes ``dealer_owner`` from ``sales_manager`` (and both are
plausibly held by one indie owner simultaneously). The uniqueness
constraint only forbids the *exact* duplicate row. Increments 4B/4C
that need "the active role" can resolve it via role priority
(``dealer_owner`` wins), a preference stored elsewhere, or a
future ``is_active_role`` flag — that decision belongs to the
increment that first needs it, not to 4A.

## Recommended scope for SESSION_040 — Increment 4B

**Goal:** DRF ``DEFAULT_AUTHENTICATION_CLASSES`` +
``get_current_dealership(request)`` resolver. Permission classes stay
permissive at the framework level so no currently-public endpoint
silently gains a 401. Endpoint-level tightening is 4C/4D.

**In scope** (per ``MILESTONE_1_PLANNING.md`` §7 · 4B):

1. Populate ``REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`` with
   ``SessionAuthentication`` (customer chat stays cookie-friendly for
   the embed frame) plus ``TokenAuthentication`` for API clients.
   ``DEFAULT_PERMISSION_CLASSES`` stays permissive.
2. Extend ``services/tenancy.py`` with ``get_current_dealership(request)``
   that resolves in this order:
   a. ``request.user.memberships.first().dealership`` when authenticated
      and a membership row exists.
   b. Header ``X-Dealership-Slug`` matched against a live ``Dealership``.
   c. ``get_default_dealership()`` — the existing single-tenant fallback.
3. Resolver tests only. No endpoint changes.

**Out of scope for 4B** (still deferred): every ❌ item on the
SESSION_039 non-goals list except (1) DRF auth defaults and (2) the
resolver itself.

## Anchors that win on conflict

Unchanged from SESSION_038 close:

1. ``docs/PROJECT_RULES.md``
2. ``docs/DOC_GOVERNANCE.md``
3. ``docs/roadmap/IMPLEMENTATION_ROADMAP.md``
4. ``docs/roadmap/MILESTONE_1_PLANNING.md`` (§7 = increment
   sub-sequencing)
5. ``docs/BUSINESS_DOMAIN_MAP.md``
6. ``docs/research/*_MAPPING.md`` + ``*_PIVOT.md``
7. ``docs/CAPABILITY_MATRIX.md``
8. Most recent handoffs (this one + ``SESSION_038_*.md``).
9. ``git log --oneline -25``

## Operational state at session close

- **Backend (local):** Django on ``:8001``. Package
  ``backend/dealer_ai/``. Migrations ``0001``–``0011`` applied. Default
  ``Dealership`` row still present (``slug='default'``).
  ``UserDealershipRole`` table exists, empty. ``Salesperson.user`` FK
  exists, all existing rows have ``user=NULL``.
- **Backend (prod):** ``vehicle-match-api.onrender.com`` — not active.
- **Frontend (local):** Vite on ``:5173``. Untouched this session.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,333 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  ``DEALER_AI_DEALER_TYPE=franchise``, ``DEALER_AI_PRIMARY_MAKE=<OEM>``,
  ``DEALER_AI_DEALER_NAME=<name>``.
- ``docs/roadmap/DEFERRED_IDEAS.md`` — still does not exist. Nothing
  out-of-milestone surfaced during 4A.

*End of SESSION_039 handoff.*
