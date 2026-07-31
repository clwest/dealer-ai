---
state: active
date: 2026-07-31
last_session_shipped: SESSION_040
next_session: SESSION_041
---

# Next session — SESSION_041 · Milestone 1 · Increment 4C (Advisor workspace: slug-obscurity → real auth + tenant scope)

> **Milestone 1 is in progress.** SESSION_040 shipped Increment 4B
> (DRF authentication defaults + `get_current_dealership` request-
> context resolver + `AUTHENTICATION_MODEL.md` reference). Handoff at
> `docs/handoffs/SESSION_040_milestone_1_auth_defaults_and_request_context.md`.
>
> Increment 4 remains split across six sub-sessions (4A–4F). The full
> contract lives in `docs/roadmap/MILESTONE_1_PLANNING.md` §7.
> SESSION_041 opens **Increment 4C**.
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/AUTHENTICATION_MODEL.md` — canonical layer
>   separation. **Read this before writing permission classes.**
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — scope
>   boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — acceptance contract
>   (must still verify true after 4C).
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 — Increment 4
>   sub-sequencing (why the work is split A–F).

## What just shipped

- **SESSION_040** — Increment 4B. Test baseline 1,333 → 1,349.
  Commits `dc24ab6` (docs refinement), `7fc415f` (feat),
  `aa02bc6` (handoff + AUTHENTICATION_MODEL.md).
  Handoff at
  `docs/handoffs/SESSION_040_milestone_1_auth_defaults_and_request_context.md`.
- **SESSION_039** — Increment 4A. Commit `92e3c48`.
- **SESSION_038** — Increment 3.
- **SESSION_037** — Increments 1 & 2.

## Increment 4 at a glance

Recorded in full at `docs/roadmap/MILESTONE_1_PLANNING.md` §7. Each
sub-increment is a single-session unit; each leaves the application
deployable and the test baseline healthy.

- **4A** ✅ (SESSION_039) — User↔Dealership membership + role foundation.
- **4B** ✅ (SESSION_040) — DRF auth defaults + `get_current_dealership`.
- **4C** (this session) — Advisor workspace: slug-obscurity → auth +
  tenant scope. URL shape preserved.
- **4D** — Admin endpoint gating + queryset scoping across every
  `/api/dealer-ai/admin/*` route + onboarding profile
  (`IsDealerOwner`).
- **4E** — Frontend login page + shared `authFetch()` helper.
- **4F** — Full compatibility sweep + hardening + Milestone 1 close
  (update `CAPABILITY_MATRIX` §7/§8 + roadmap §2.7).

## What SESSION_041 should do — Increment 4C

**Goal:** replace the advisor-workspace slug-obscurity check with
real authentication + role + tenant enforcement. URL shape preserved
(the frontend still routes to `/dealer-ai-advisor/:slug`).

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/roadmap/AUTHENTICATION_MODEL.md` — the layer separation
     4C must respect. This is the canonical reference; do not
     collapse Identity / Authorization / Business permissions.
   - `docs/handoffs/SESSION_040_milestone_1_auth_defaults_and_request_context.md`
     — the resolver and auth defaults 4C consumes.
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §1.4 + §7 · 4C.
   - `backend/dealer_ai/views.py::advisor_workspace` and
     `::advisor_follow_up` (currently ~lines 452–564; verify against
     the file — line numbers may drift).
   - The 403 lead-ownership check inside `advisor_follow_up`
     (currently ~views.py:529). Preserve verbatim.

2. **Implement in this order:**

   1. **DRF permission classes** in a new file
      `backend/dealer_ai/permissions.py`:
      - `AdvisorForSlug` — passes when
        `request.user.is_authenticated` AND
        `getattr(request.user, "salesperson", None)` exists AND
        `request.user.salesperson.slug == view.kwargs["slug"]`.
      - `SameDealership` — passes when the requesting user's active
        dealership (via `get_current_dealership(request)`) matches
        the target Salesperson's dealership.
      - `IsDealerOwnerOrAdvisorForSlug` — union: an authenticated
        dealer_owner at the same dealership may view any advisor's
        queue (per `MILESTONE_1_PLANNING.md` §1.4).
   2. **Apply to `advisor_workspace()` and `advisor_follow_up()`.**
      Add `@permission_classes([...])` (or class-based equivalent).
      Keep `authentication_classes` at DRF default (Session + Token
      inherit from settings). Do not touch other views.
   3. **Preserve the lead-ownership 403** at views.py:529 verbatim.
      That check is orthogonal to auth — it enforces "own leads
      only" once the auth check has passed.
   4. **Test-client fixture** in a new
      `backend/dealer_ai/tests/_auth_helpers.py`. Helpers:
      - `make_advisor_user(slug, dealership)` — creates User +
        Salesperson (with slug + dealership) + `Salesperson.user`
        link.
      - `make_membership(user, dealership, role)` — creates
        `UserDealershipRole`.
      - `authenticated_client(user)` — returns a DRF `APIClient`
        with `force_authenticate(user=user)`.
   5. **Update existing advisor tests** (search for
      `/api/dealer-ai/advisor/`) so they authenticate. The test
      count should *increase* — the pre-4C tests exercised
      anonymous slug-only access; 4C replaces that with
      authenticated access and adds negative-path coverage.
   6. **New negative-path tests** in
      `tests/test_advisor_workspace_auth.py`:
      - Unauthenticated → 401.
      - Authenticated user, no linked Salesperson → 403.
      - Authenticated user, linked to a different Salesperson slug
        → 403.
      - Authenticated advisor, correct slug, correct dealership →
        200.
      - Authenticated dealer_owner at same dealership, any slug →
        200 (per §1.4).
      - Authenticated dealer_owner at *different* dealership → 403.

3. **Verify continuously.** After each step run
   `python3 manage.py test dealer_ai` and confirm the pre-existing
   advisor tests still pass (after being updated to authenticate)
   and every §3 compatibility item still holds.

4. **Verify layer discipline.** Cross-check against
   `AUTHENTICATION_MODEL.md`:
   - Identity — DRF auth classes (unchanged, inherited from
     settings).
   - Authorization — `get_current_dealership(request)` (called by
     `SameDealership`).
   - Business permissions — the three classes above.
   - Data scoping — the existing lead-ownership queryset filter
     inside `advisor_follow_up` (preserved).
   No layer is collapsed into another.

5. **Close the session** with:
   - Handoff at `docs/handoffs/SESSION_041_<slug>.md`.
   - Overwrite this file with the SESSION_042 = Increment 4D priority.
   - Update `AUTHENTICATION_MODEL.md` §7 with the concrete
     `AdvisorForSlug + SameDealership` permission-class names now
     that they exist in code.
   - `docs/CAPABILITY_MATRIX.md` update **not required** — Milestone
     1 auth surface is not complete until 4F.

## Explicit non-goals for SESSION_041 (Increment 4C)

- ❌ Do NOT touch admin endpoints. That's 4D.
- ❌ Do NOT change `DEFAULT_PERMISSION_CLASSES` in settings.
  Enforcement is per-endpoint.
- ❌ Do NOT touch frontend code. Login UI is 4E.
- ❌ Do NOT introduce tenant-scoped uniqueness on `Salesperson.slug`.
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT auto-create `Salesperson.user` links. The bootstrap
  path (superuser wires the link via Django admin) is still the
  only mechanism.
- ❌ Do NOT change the URL shape. Frontend routing must continue to
  resolve `/dealer-ai-advisor/:slug` unchanged.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT create parallel docs. Update `AUTHENTICATION_MODEL.md`
  and `MILESTONE_1_PLANNING.md` only if implementation reveals a
  real deviation from the contract.

## NEXT TASK

Start SESSION_041 with the read-first list above, then implement
Increment 4C in the six-step sequence.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing)
5. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model)
6. `docs/BUSINESS_DOMAIN_MAP.md`
7. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs (`SESSION_040_*.md`, `SESSION_039_*.md`).
10. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_040)

- **Backend (local):** Django on `:8001`. Package `backend/dealer_ai/`.
  Migrations `0001`–`0011` applied. `authtoken` migrations
  `0001`–`0004` applied. Default `Dealership` row exists
  (`slug='default'`). No `Token` / `UserDealershipRole` rows exist;
  `Salesperson.user` is NULL on every existing row.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
- **Frontend (local):** Vite on `:5173`. Unchanged since SESSION_038.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,349 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`
  installed at framework level; `DEFAULT_PERMISSION_CLASSES` is
  unset (DRF `AllowAny` default stands).
- **Request-context resolver:**
  `services.tenancy.get_current_dealership(request)` and
  `services.tenancy.get_active_membership(user)` available. No
  view calls them yet — 4C is the first consumer.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
- **Dev DB note (unchanged from SESSION_038 handoff):**
  `DealerOnboardingProfile` count = 0. Visit `/dealer-ai-onboarding`
  and save once to restore if the demo relies on a persisted profile.
