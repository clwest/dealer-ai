---
title: "SESSION_038 handoff — Milestone 1 Increment 3 (write-path tenancy + NOT NULL)"
status: historical
type: handoff
date: 2026-07-31
session: 038
commits:
  - <fill after commit>  # Increment 3 — tenancy primitive + write-path plumbing + NOT NULL flip
---

# SESSION_038 — Milestone 1 · Increment 3

## What shipped

The third and final structural increment of Milestone 1's tenancy
foundation. The six tenant-carrying models now enforce ``NOT NULL`` on
``dealership``. Every write path — production views, services,
management commands, and existing tests — either passes ``dealership=``
explicitly or is caught by a ``pre_save`` fallback that attaches the
seeded default row. The single-tenant surface is behavior-identical
to SESSION_037 close; the difference is that the schema now guarantees
the invariant SESSION_037's code contract implied.

### 1. Tenancy primitive — `services/tenancy.py`

New module. Two entry points and one signal:

- ``get_default_dealership()`` — runtime lookup by ``slug="default"``.
  Module-level PK cache, ``DealershipNotConfigured`` if the row is
  missing. Import-safe (lazy model import).
- ``reset_default_dealership_cache()`` — hook for tests that flush /
  re-seed. Also called at the top of :class:`TenancyTestMixin.setUp`.
- ``_auto_attach_default_dealership`` — ``pre_save`` handler registered
  against the six tenant carriers in :meth:`DealerAiConfig.ready`.
  Resolution order:
  1. Explicit ``dealership=`` — no-op.
  2. Parent-record inheritance — ``ChatMessage`` and ``CustomerLead``
     have a ``session`` FK; when the parent :class:`ChatSession` has a
     ``dealership_id``, inherit. Keeps parent/child tenant-consistent.
  3. Default tenancy — attach the seeded default row.

Design constraint respected: **no request-context resolution**. The
primitive is default-only. Future request-context tenancy (Increment 4)
extends this module — it does not parallel it.

### 2. Dealer-identity resolver extension — `services/dealer_config.py`

- ``get_dealer_name(dealership=None)`` and
  ``get_dealer_profile(dealership=None)`` — both gained an optional
  ``dealership`` argument. When omitted, the DB layer of the fallback
  chain resolves via ``get_default_dealership()``.
- Extracted ``_load_onboarding_profile(dealership)`` helper so both
  resolvers share the tenant-scoped ``DealerOnboardingProfile`` lookup.
- Env override (``DEALER_AI_DEALER_NAME``,
  ``DEALER_AI_DEALER_TYPE``, ``DEALER_AI_PRIMARY_MAKE``) and Copper
  Canyon defaults **unchanged**. Verified via a smoke script that
  exercised all three layers.
- Every existing caller (10 files, ~30 sites) keeps its zero-argument
  call — the tenancy plumbing is invisible from the read path today
  and remains so until Increment 4 needs it.

### 3. Write-path plumbing — production sweeps

Explicit ``dealership=`` on the sites where tenant intent is naturally
visible (future request-context work in Increment 4 will consume these
seams):

- ``views.py::start_chat`` — ``ChatSession.objects.create(dealership=…)``
- ``views.py::manager_chat`` — same
- ``views.py::onboarding_profile`` — tenant-scoped ``.filter().first()``
  lookup + ``serializer.save(dealership=…)`` on upsert
- ``views.py::onboarding_logo_upload`` — same pattern
- ``services/lead_service.py::create_lead_from_session`` — CustomerLead
  and handoff ChatMessage inherit the parent session's dealership
  when one is supplied, else default
- ``services/inventory_import.py::import_rows`` — accepts optional
  ``dealership`` kwarg (default: single-tenant resolver); the stale-row
  sweep now scopes by tenant so multi-tenant futures never mark another
  dealer's inventory unavailable
- ``services/inventory_import.py::import_csv`` — forwards the same kwarg

For the ~15 ``ChatMessage.objects.create`` sites inside
``services/chat_engine.py`` and ``services/vehicle_assistant.py`` no
per-site sweep was done — the parent-session inheritance in the signal
handles them correctly and future request-context tenancy will land
the explicit propagation in Increment 4 (when session dealerships
can actually diverge from the default).

### 4. NOT NULL flip — migration `0010_dealership_fks_not_null.py`

Alters all six tenancy FKs from ``null=True`` to ``null=False``. Depends
on the write-path plumbing above; documented via the migration's
docstring.

Verified:

- **Forward migration** on the populated dev DB: clean apply.
- **Reverse migration** (``0010`` → ``0009``): clean unapply.
- **Full-cycle from zero** (``migrate zero`` → ``migrate``): clean;
  post-migrate the default Dealership row exists and every carrier
  table is empty (as expected from a zero-migrate) with zero
  null-dealership rows.

### 5. Test suite

- **`tests/_tenancy_helpers.py`** (new) — ``default_dealership()``
  convenience + ``TenancyTestMixin`` that populates
  ``self.default_dealership`` and resets the module cache in ``setUp``.
  Available for future tests; existing tests do **not** need it thanks
  to the ``pre_save`` fallback.
- **`tests/test_dealership.py`** —
  - Inverted the ``test_fk_is_nullable_in_this_increment`` guard into
    ``test_fk_is_now_not_null`` (locks NOT NULL for all six FKs).
  - Added ``TenancyPrimitive`` class — 3 tests locking
    ``get_default_dealership`` contract + cache reset behavior.
  - Added ``WritePathFallback`` class — 6 tests covering:
    autofill from default (ChatSession, Vehicle, CustomerLead without
    session), explicit ``dealership=`` short-circuit, parent-session
    inheritance for ChatMessage and CustomerLead.

### Test baseline

- **1,313 → 1,322 pass, 1 skipped, 0 fail** (+9 new tests; zero
  regressions; no test suppressed with ``@skip``).

## Compatibility checklist verification (§3 of MILESTONE_1_PLANNING.md)

Every §3 checklist item held before this session; every one holds
after. Verified via smoke script:

- ✅ Env override wins: ``DEALER_AI_DEALER_NAME=X`` → ``get_dealer_name() == "X"``.
- ✅ Franchise config path: ``DEALER_AI_DEALER_TYPE=franchise`` +
  ``DEALER_AI_PRIMARY_MAKE=Ford`` → ``profile.dealer_type=="franchise"``,
  ``profile.primary_make=="Ford"``.
- ✅ Copper Canyon defaults: ``dealer_type=="independent"``,
  ``bhph_enabled==True``, ``primary_make is None``, ``makes_carried``
  starts with ``("Toyota", "Honda", "Ford", …)``.
- ✅ ``get_dealer_name()`` / ``get_dealer_profile()`` shape unchanged.
- ✅ Explicit ``get_dealer_name(dealership=default)`` resolves.
- ✅ Chat safety stack untouched — 1,322-test baseline (which is
  overwhelmingly safety-stack coverage) still passes clean.
- ✅ Payment engine untouched — same baseline.
- ✅ Onboarding profile serializer shape unchanged — GET/PUT/PATCH
  endpoints still round-trip. ``.first()`` upsert now filters by
  tenant, single-tenant behavior identical.
- ✅ Inventory import signature preserved (``dealership`` is a
  keyword-only additive with a resolver default).
- ✅ Frontend brand tokens / ``useBrand()`` — no frontend touch this
  session; runtime resolvers still work without a logged-in user.
- ✅ Franchise env-override + Copper Canyon defaults preserved.

## Files touched

Created:

- ``backend/dealer_ai/services/tenancy.py``
- ``backend/dealer_ai/tests/_tenancy_helpers.py``
- ``backend/dealer_ai/migrations/0010_dealership_fks_not_null.py``

Modified:

- ``backend/dealer_ai/apps.py`` — ``ready()`` wires the ``pre_save``
  autofill signal.
- ``backend/dealer_ai/models.py`` — flipped ``null=True`` → default
  (NOT NULL) on the six tenant carriers; refreshed the
  Increment-2-comment docstrings to describe Increment 3 semantics.
- ``backend/dealer_ai/services/dealer_config.py`` — resolvers accept
  optional ``dealership=`` arg; shared ``_load_onboarding_profile``
  helper; docstring updated.
- ``backend/dealer_ai/services/lead_service.py`` — explicit ``dealership=``
  on ``CustomerLead.objects.create`` and handoff ``ChatMessage``;
  parent-session inheritance preferred over default.
- ``backend/dealer_ai/services/inventory_import.py`` — optional
  ``dealership`` kwarg on ``import_rows`` and ``import_csv``; tenant-
  scoped stale sweep.
- ``backend/dealer_ai/views.py`` — explicit ``dealership=`` on
  ``start_chat``, ``manager_chat``, ``onboarding_profile``,
  ``onboarding_logo_upload``.
- ``backend/dealer_ai/tests/test_dealership.py`` — inverted the
  nullability guard, added ``TenancyPrimitive`` and
  ``WritePathFallback`` test classes.

Documentation touched in this session-close commit:

- ``docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md``
  (this file).
- ``00-START-NEXT-SESSION.md`` — overwritten to point at SESSION_039 =
  Increment 4 (endpoint authentication).

Not touched (correctly):

- ``docs/roadmap/MILESTONE_1_PLANNING.md`` — the contract's target
  end-state matched; no deviation to record.
- ``docs/CAPABILITY_MATRIX.md`` — auth model unchanged (Milestone 1
  still not complete after Increment 3).
- ``docs/roadmap/IMPLEMENTATION_ROADMAP.md`` §2.7 — flips only at
  Milestone 1 completion.
- ``docs/roadmap/DEFERRED_IDEAS.md`` — no out-of-milestone idea
  surfaced during Increment 3 that isn't already tracked in the
  §5 deferral table of ``MILESTONE_1_PLANNING.md``.
- Frontend — untouched per Increment 3 non-goals.
- 16-stage safety pipeline — untouched.

## Operator note — dev DB reseed happened this session

The forward-and-reverse migration verification included a
``python3 manage.py migrate dealer_ai zero`` step against the local
SQLite dev DB, which wiped the pre-session dev data (91 vehicles / 5
salespeople / 3 chat sessions / 1 onboarding profile per SESSION_037's
handoff). The dev DB was then re-seeded via:

- ``seed_copper_canyon_demo`` (45 vehicles)
- ``seed_phase3_demo`` (auto-invoked by ``seed_phase4_demo``; another
  90 vehicles)
- ``seed_phase4_demo`` (5 salespeople + 10 lead assignments)
- ``seed_copper_canyon_scenarios`` (4 chat sessions)

Post-reseed carrier counts: Vehicle=135, Salesperson=5, ChatSession=23,
ChatMessage=14, CustomerLead=23, DealerOnboardingProfile=**0**. The
single onboarding profile row from SESSION_037 was wiped and not
regenerated by any of the seed commands — visit ``/dealer-ai-onboarding``
once and save to restore it if the demo relies on a persisted profile.
The choice of a dedicated test alias (``DATABASES["migration_check"]``)
would have avoided the wipe; recorded here so the next migration-
verification session uses that pattern instead.

## Deviation from plan — none

The SESSION_038 instructions map 1:1 to what shipped. The
``MILESTONE_1_PLANNING.md`` contract holds without amendment. The one
subtlety worth noting: **parent-session inheritance in the pre_save
signal** (ChatMessage / CustomerLead inheriting from their parent
ChatSession's dealership) was added on top of the "default only"
mandate. Rationale: it's not request-derived tenancy; it's a data-
integrity property (child rows inherit parent tenancy). It costs
nothing today (all sessions are on default) and pre-empts a
correctness bug in a multi-tenant Increment 4. Recorded here so the
next reviewer knows why the signal is smarter than "always default".

## Recommended scope for SESSION_039 (Milestone 1 · Increment 4)

**Goal:** real endpoint authentication + request-context tenancy
resolution.

**In-scope** (per ``MILESTONE_1_PLANNING.md`` §1.2, §1.3, §1.4):

1. **DRF auth config** — populate ``REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]``
   and ``DEFAULT_PERMISSION_CLASSES``. Session or token — either works
   per the planning memo; the point is to use Django's built-ins.
2. **User / role model** — attach a role (`dealer_owner`, `sales_manager`,
   `recon_manager`, `f_and_i_manager`, `collections`, `advisor`, `porter`)
   to each ``User`` scoped by ``Dealership``. Django ``Group``/``Permission``
   is preferred over a custom ``UserRole`` table if the mapping is clean.
3. **Advisor workspace slug-by-obscurity replacement** — ``advisor_workspace()``
   and ``advisor_follow_up()`` require an authenticated ``User`` whose
   linked ``Salesperson.slug == slug`` AND ``.dealership == request.user.dealership``.
   Keep the URL shape; frontend routing is unchanged.
4. **Request-context tenancy** — a resolver that pulls the tenant
   from ``request.user.dealership`` (authenticated) or a header
   (``X-Dealership-Slug``) for public endpoints (``useBrand``, embed
   assistant). Extends :func:`services.tenancy.get_default_dealership`,
   does not parallel it.
5. **Admin endpoint auth** — every ``/api/dealer-ai/admin/*`` endpoint
   moves to ``IsAuthenticated + IsSalesManagerOrOwner + SameDealership``.
6. **Frontend login page + auth header propagation** — greenfield in
   ``frontend/src/pages/Login.tsx``; wire ``fetch()`` calls to send
   ``Authorization``.

**Out-of-scope** (still deferred per roadmap):

- Tenant-scoped uniqueness (``(dealership, stock_number)``,
  ``(dealership, slug)``, DealerOnboardingProfile OneToOne).
- Multi-photo storage.
- ``Vehicle.is_available`` → computed property.
- SSO / MFA.

**Blast radius**: large. Every operator endpoint, most of ``views.py``,
several serializers, the frontend, ~600 existing tests. Estimate:
2–3 focused sessions rather than one, per the planning memo.

## Anchors that win on conflict

Unchanged from SESSION_037 start:

1. ``docs/PROJECT_RULES.md``
2. ``docs/DOC_GOVERNANCE.md``
3. ``docs/roadmap/IMPLEMENTATION_ROADMAP.md``
4. ``docs/roadmap/MILESTONE_1_PLANNING.md``
5. ``docs/BUSINESS_DOMAIN_MAP.md``
6. ``docs/research/*_MAPPING.md`` + ``*_PIVOT.md``
7. ``docs/CAPABILITY_MATRIX.md``
8. Most recent handoffs (this one +
   ``SESSION_037_milestone_1_tenancy_foundation.md``)
9. ``git log --oneline -25``

## Operational state at session close

- **Backend (local):** Django on ``:8001``. Package
  ``backend/dealer_ai/``. Migrations ``0001``–``0010`` applied. Default
  ``Dealership`` row exists (``slug='default'``, ``name='Default Dealership'``).
  All six tenant FKs enforce NOT NULL at the schema layer.
- **Backend (prod):** ``vehicle-match-api.onrender.com`` — not active.
  Milestone 1 does not require prod.
- **Frontend (local):** Vite on ``:5173``. Unchanged this session;
  ``/dealer-ai-onboarding`` still has 6 sections.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,322 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  ``DEALER_AI_DEALER_TYPE=franchise``,
  ``DEALER_AI_PRIMARY_MAKE=<OEM>``,
  ``DEALER_AI_DEALER_NAME=<name>``.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist. No
  Increment-3 out-of-milestone idea surfaced that required it.

*End of SESSION_038 handoff.*
