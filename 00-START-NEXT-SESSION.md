---
state: active
date: 2026-07-31
last_session_shipped: SESSION_038
next_session: SESSION_039
---

# Next session — SESSION_039 · Milestone 1 · Increment 4 (endpoint authentication + request-context tenancy)

> **Milestone 1 is in progress.** SESSION_038 completed the tenancy
> *foundation*: the ``Dealership`` model (037), nullable FKs +
> verified backfill (037), and now (038) write-path plumbing +
> ``NOT NULL`` on all six tenant carriers. Handoff at
> ``docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md``.
>
> **SESSION_039 opens the authentication half of Milestone 1.**
>
> **All governance layers apply:**
>
> - ``docs/PROJECT_RULES.md`` — six project-work rules.
> - ``docs/DOC_GOVERNANCE.md`` — documentation rules.
> - ``docs/roadmap/IMPLEMENTATION_ROADMAP.md`` §Milestone 1 —
>   scope boundary.
> - ``docs/roadmap/MILESTONE_1_PLANNING.md`` — acceptance
>   contract (§3 compatibility checklist must still verify
>   true after Increment 4).

## What just shipped

- **SESSION_038 (this session)** — Milestone 1 Increment 3.
  New ``services/tenancy.py`` primitive (``get_default_dealership``
  + ``pre_save`` autofill signal wired via ``DealerAiConfig.ready``),
  ``dealer_config.py`` resolvers extended with optional ``dealership=``
  arg, explicit write-path sweeps in ``views.py`` /
  ``services/lead_service.py`` / ``services/inventory_import.py``,
  migration ``0010_dealership_fks_not_null.py`` flipping all six FKs
  to NOT NULL. Test baseline moved 1,313 → 1,322 (+9). See handoff
  ``docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md`` for
  the full contract-verification narrative + the note about the dev
  DB re-seed that happened during migration verification.
- **SESSION_037** — Increments 1 & 2 (``Dealership`` model + nullable
  FKs + verified backfill).

## What SESSION_039 should do — Increment 4

**Goal:** propagate authenticated request context through the API so
tenancy is derived from the authenticated user (or a public header
where operator auth doesn't apply) instead of always defaulting to
the ``slug="default"`` row.

### Recommended step sequence

1. **Read first (in this order):**
   - ``docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md``
     — the tenancy primitive contract that Increment 4 extends,
     including the "parent-session inheritance" nuance in the
     ``pre_save`` handler.
   - ``docs/roadmap/MILESTONE_1_PLANNING.md`` §1.2, §1.3, §1.4, §2
     rows 3, 5, 6, 8, 9, 10, 11, 12 — the per-system impact table
     for endpoint auth work.
   - ``backend/dealer_ai/services/tenancy.py`` — the primitive to
     extend, **not parallel**.
   - ``backend/dealer_kit/settings.py`` — inspect the (currently
     empty) ``REST_FRAMEWORK`` ``DEFAULT_AUTHENTICATION_CLASSES`` /
     ``DEFAULT_PERMISSION_CLASSES`` config.

2. **Implement in this order** (each step verifiable independently):

   1. **DRF auth config** in ``settings.py``. Pick session-or-token
      per the planning memo — either is fine, the point is to use
      Django's built-ins.
   2. **User → dealership + role mapping.** Django ``Group`` /
      ``Permission`` is preferred if the mapping is clean; a small
      ``UserRole`` (or ``UserDealershipRole``) table is fine when it
      isn't. Roles per ``IMPLEMENTATION_ROADMAP.md`` §Milestone 1:
      ``dealer_owner``, ``sales_manager``, ``recon_manager``,
      ``f_and_i_manager``, ``collections``, ``advisor``, ``porter``.
   3. **Extend the tenancy primitive.** Add a
      ``get_current_dealership(request)`` (or equivalent) that
      resolves from ``request.user.dealership`` when authenticated,
      or a public header (``X-Dealership-Slug``) for customer-facing
      endpoints. Falls back to ``get_default_dealership()`` for
      single-tenant local dev.
   4. **Advisor workspace auth.** Replace the slug-obscurity check
      in ``views.py::advisor_workspace`` / ``advisor_follow_up``
      with ``IsAuthenticated + AdvisorForSlug + SameDealership``.
      Keep the URL shape.
   5. **Admin endpoint auth.** Every ``/api/dealer-ai/admin/*``
      endpoint gains ``IsAuthenticated + IsSalesManagerOrOwner +
      SameDealership`` plus queryset scoping by ``request.user.dealership``.
   6. **Customer-facing scoping.** Chat / vehicle Q&A endpoints stay
      ``AllowAny`` (customer is not a platform user). But
      ``ChatSession`` / ``ChatMessage`` / matched-vehicle queries
      resolve tenancy from the incoming header or default. Chat/vehicle
      scrub stack **untouched**.
   7. **Frontend login page + auth header propagation.** Greenfield
      ``frontend/src/pages/Login.tsx`` (or equivalent). Shared
      ``authFetch()`` helper. Every operator page (leads, admin,
      coaching) uses it; public pages (``/``, ``/assistant``,
      ``/showroom``, ``/embed/assistant``) do not.

3. **Verify continuously.** After each step run the backend suite
   (``python3 manage.py test dealer_ai``) plus the frontend
   type-check and build. The 1,322-pass baseline must be preserved
   — Increment 4 is expected to *add* auth/permission tests, not
   remove existing ones.

4. **Verify the compatibility checklist** (§3 of the planning memo)
   after each step. Every pre-existing item must still verify true.
   The frontend-side items in particular ("public routes render
   unauthenticated") are the ones most likely to regress if auth
   propagates too aggressively.

5. **Preserve the franchise config path.** Env overrides
   (``DEALER_AI_DEALER_TYPE``, ``DEALER_AI_PRIMARY_MAKE``,
   ``DEALER_AI_DEALER_NAME``) must continue to work for single-tenant
   local dev.

6. **Close the session** with:
   - Handoff at ``docs/handoffs/SESSION_039_<slug>.md``.
   - Update ``docs/CAPABILITY_MATRIX.md`` §7/§8 (auth model, roles)
     — this is the increment that visibly changes what the software
     does. Update ``IMPLEMENTATION_ROADMAP.md`` §2.7 if Milestone 1
     is complete at session close.
   - Overwrite this file (``00-START-NEXT-SESSION.md``) with the
     SESSION_040 priority (either Milestone 1 wrap-up if Increment 4
     spans multiple sessions, or Milestone 2 kickoff).

## Explicit non-goals for SESSION_039

- ❌ Do NOT introduce tenant-scoped unique constraints
  (``(dealership, stock_number)``, ``(dealership, slug)``,
  ``DealerOnboardingProfile`` OneToOne). Those come with the
  increment that needs them.
- ❌ Do NOT introduce SSO / MFA. Explicitly out-of-scope per the
  planning memo §5.
- ❌ Do NOT build a user-management UI beyond sign-in. Out-of-scope.
- ❌ Do NOT add per-role UI polish (dashboards, sidebars) beyond
  what auth strictly requires. Each future milestone applies role
  scoping to its own surfaces.
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT delete the franchise config path or Freedom Ford demo
  assets.
- ❌ Do NOT commit any real ``OPENAI_API_KEY``.
- ❌ Do NOT create parallel docs (per ``DOC_GOVERNANCE.md`` §7.2).
  Update the existing planning memo only if implementation reveals
  a real deviation from the contract.

## NEXT TASK

Start SESSION_039 with the read-first list above, then implement
Increment 4 in the seven-step sequence.

---

## Anchors that win on conflict

1. ``docs/PROJECT_RULES.md``
2. ``docs/DOC_GOVERNANCE.md``
3. ``docs/roadmap/IMPLEMENTATION_ROADMAP.md``
4. ``docs/roadmap/MILESTONE_1_PLANNING.md``
5. ``docs/BUSINESS_DOMAIN_MAP.md``
6. ``docs/research/*_MAPPING.md`` + ``*_PIVOT.md``
7. ``docs/CAPABILITY_MATRIX.md``
8. Most recent handoffs (``SESSION_038_*.md``,
   ``SESSION_037_*.md``).
9. ``git log --oneline -25``; ``git show HEAD:<path>``.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_038)

- **Backend (local):** Django on ``:8001``. Package
  ``backend/dealer_ai/``. Migrations ``0001``–``0010`` applied.
  Default ``Dealership`` row exists (``slug='default'``,
  ``name='Default Dealership'``). All six tenant FKs enforce NOT
  NULL at the schema layer. Write-path fallback via ``pre_save``
  signal registered in ``DealerAiConfig.ready``.
- **Backend (prod):** ``vehicle-match-api.onrender.com`` — NOT
  active. Milestone 1 does not require prod.
- **Frontend (local):** Vite on ``:5173``. Unchanged this session;
  ``/dealer-ai-onboarding`` still has 6 sections.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,322 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  ``DEALER_AI_DEALER_TYPE=franchise``,
  ``DEALER_AI_PRIMARY_MAKE=<OEM>``,
  ``DEALER_AI_DEALER_NAME=<name>``.
- **``docs/roadmap/DEFERRED_IDEAS.md``** — still does not exist.
  Create it the first time an idea surfaces during Milestone 1
  that doesn't fit inside an existing milestone plan doc.
- **Dev DB note:** the SESSION_037 ``DealerOnboardingProfile``
  singleton was wiped during SESSION_038's migration-cycle
  verification and not regenerated. Visit
  ``/dealer-ai-onboarding`` once and save to restore if the
  demo relies on a persisted profile.
