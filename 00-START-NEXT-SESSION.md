---
state: active
date: 2026-07-31
last_session_shipped: SESSION_041
next_session: SESSION_042
---

# Next session — SESSION_042 · Milestone 1 · Increment 4D (admin endpoint gating + queryset scoping)

> **Milestone 1 is in progress.** SESSION_041 shipped Increment 4C
> (advisor workspace slug-obscurity → real membership-based
> authorization). Handoff at
> `docs/handoffs/SESSION_041_milestone_1_advisor_authorization.md`.
>
> Increment 4 remains split across six sub-sessions (4A–4F). The full
> contract lives in `docs/roadmap/MILESTONE_1_PLANNING.md` §7.
> SESSION_042 opens **Increment 4D**.
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/AUTHENTICATION_MODEL.md` — canonical layer
>   separation. **Read §7 before writing permission classes.** 4C
>   updated it with the concrete `IsAdvisorForSlug` +
>   `IsDealerOwnerForAdvisorSlug` shapes; 4D will add
>   `IsSalesManagerOrOwnerAtActiveDealership` +
>   `IsDealerOwnerAtActiveDealership`.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — scope
>   boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — acceptance contract
>   (must still verify true after 4D).
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 — Increment 4
>   sub-sequencing (why the work is split A–F).

## What just shipped

- **SESSION_041** — Increment 4C. Test baseline 1,349 → 1,361.
  Commits `76d625b` (feat), `<fill after docs>` (handoff +
  AUTHENTICATION_MODEL.md §7 update). Handoff at
  `docs/handoffs/SESSION_041_milestone_1_advisor_authorization.md`.
- **SESSION_040** — Increment 4B. Commits `dc24ab6`, `7fc415f`,
  `aa02bc6`, `02b0252`.
- **SESSION_039** — Increment 4A. Commit `92e3c48`.
- **SESSION_038** — Increment 3.
- **SESSION_037** — Increments 1 & 2.

## Increment 4 at a glance

Recorded in full at `docs/roadmap/MILESTONE_1_PLANNING.md` §7.

- **4A** ✅ (SESSION_039) — User↔Dealership membership + role foundation.
- **4B** ✅ (SESSION_040) — DRF auth defaults + `get_current_dealership`.
- **4C** ✅ (SESSION_041) — Advisor workspace: slug-obscurity → auth
  + tenant scope.
- **4D** (this session) — Admin endpoint gating + queryset scoping
  across every `/api/dealer-ai/admin/*` route + onboarding profile
  (`IsDealerOwner`).
- **4E** — Frontend login page + shared `authFetch()` helper.
- **4F** — Full compatibility sweep + hardening + Milestone 1 close
  (update `CAPABILITY_MATRIX` §7/§8 + roadmap §2.7).

## What SESSION_042 should do — Increment 4D

**Goal:** apply real authorization + tenant scoping to every admin
endpoint and to the onboarding profile mutation. Customer-facing
endpoints stay `AllowAny`. The GET side of onboarding profile stays
public because `useBrand()` renders on unauthenticated pages.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/roadmap/AUTHENTICATION_MODEL.md` — the layer separation
     4D must respect. §7 lists the shipped 4C classes; 4D extends
     with `IsSalesManagerOrOwnerAtActiveDealership` +
     `IsDealerOwnerAtActiveDealership`.
   - `docs/handoffs/SESSION_041_milestone_1_advisor_authorization.md`
     — the 4C pattern (permission composition at the view layer,
     shared `_auth_helpers`).
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 · 4D.
   - `backend/dealer_ai/permissions.py` — the module 4D extends.
   - `backend/dealer_ai/services/tenancy.py::get_current_dealership`
     — the resolver 4D's new classes consume.
   - Every admin view in `backend/dealer_ai/views.py` (search for
     `admin/` in `urls.py` to enumerate).

2. **Implement in this order:**

   1. **Extend `dealer_ai/permissions.py`** with:
      - `IsSalesManagerOrOwnerAtActiveDealership` — the caller
        holds `sales_manager` OR `dealer_owner` at
        `get_current_dealership(request)`.
      - `IsDealerOwnerAtActiveDealership` — the caller holds
        `dealer_owner` at `get_current_dealership(request)`.
      Both consult the resolver rather than a URL kwarg — this is
      a different URL-shape family from 4C. Keep the classes
      focused and reusable.
   2. **Gate every admin endpoint.** Apply `[IsAuthenticated &
      IsSalesManagerOrOwnerAtActiveDealership]` to:
      `admin/pipeline`, `admin/leads`, `admin/lead/<id>/*`,
      `admin/salespeople`, `admin/audit-events`, `admin/trends`,
      `admin/ad-copy`, `manager-chat`.
   3. **Gate onboarding profile mutation.** Apply
      `[IsAuthenticated & IsDealerOwnerAtActiveDealership]` to
      PUT/PATCH on `onboarding/profile/` and POST on
      `onboarding/profile/logo/`. Keep GET `AllowAny` — branding
      is public per §3.
   4. **Queryset scoping.** For each gated admin endpoint add
      `.filter(dealership=get_current_dealership(request))` to
      every `Lead.objects.*`, `ChatSession.objects.*`,
      `Salesperson.objects.*` query. This is the Data Scoping
      layer landing on the admin surface.
   5. **Existing test updates.** Any admin test that currently
      hits an endpoint anonymously must authenticate via the
      `_auth_helpers` fixtures. Prefer minimal edits — add
      authentication in `setUp`, adjust assertions only when the
      new authorization semantics require it.
   6. **New focused tests** in `tests/test_admin_endpoints_auth.py`.
      For each admin endpoint: unauth → 401/403; wrong-role
      (authenticated advisor) → 403; wrong-tenant (correct role at
      a different dealership) → 403; correct → 200. Plus a
      queryset-scoping test per endpoint: an admin at Dealership A
      only sees Dealership A's rows.

3. **Verify continuously.** After each step run
   `python3 manage.py test dealer_ai` and confirm zero regressions
   plus every §3 compatibility item.

4. **Verify layer discipline** against `AUTHENTICATION_MODEL.md`:
   - Identity — DRF auth classes (unchanged, inherited).
   - Authorization — the two new classes.
   - Business permissions — the role check inside those classes.
   - Data scoping — `.filter(dealership=...)` in every gated view.
   No layer collapsed into another.

5. **Close the session** with:
   - Handoff at `docs/handoffs/SESSION_042_<slug>.md`.
   - Overwrite this file with the SESSION_043 = Increment 4E
     priority.
   - Update `AUTHENTICATION_MODEL.md` §7 with the concrete new
     class names.
   - `docs/CAPABILITY_MATRIX.md` update **not required** —
     Milestone 1 close is 4F.

## Explicit non-goals for SESSION_042 (Increment 4D)

- ❌ Do NOT touch the advisor workspace or its permission classes.
  4C is done.
- ❌ Do NOT change `DEFAULT_PERMISSION_CLASSES` in settings.
  Enforcement is per-endpoint.
- ❌ Do NOT touch frontend code. Login UI is 4E.
- ❌ Do NOT introduce tenant-scoped uniqueness on any model
  (`Salesperson.slug`, `Vehicle.stock_number`,
  `DealerOnboardingProfile` OneToOne). Deferred.
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT re-scope customer-facing chat, embed frame, or vehicle
  Q&A — those stay `AllowAny` per §1.2.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT create parallel docs. Update `AUTHENTICATION_MODEL.md`
  §7 and `MILESTONE_1_PLANNING.md` §7 · 4D only if implementation
  reveals a real deviation from the contract.

## NEXT TASK

Start SESSION_042 with the read-first list above, then implement
Increment 4D in the six-step sequence.

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
9. Most recent handoffs (`SESSION_041_*.md`, `SESSION_040_*.md`).
10. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_041)

- **Backend (local):** Django on `:8001`. Package `backend/dealer_ai/`.
  Migrations `0001`–`0011` applied. `authtoken` migrations
  `0001`–`0004` applied. Default `Dealership` row exists
  (`slug='default'`). No `Token` / live `UserDealershipRole` rows in
  dev DB; the authorization surface is exercised entirely by
  focused tests.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
- **Frontend (local):** Vite on `:5173`. Unchanged since SESSION_038.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,361 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`
  installed at framework level; `DEFAULT_PERMISSION_CLASSES` unset.
- **Endpoint-level permission classes shipped:** advisor workspace
  + advisor follow-up only.
  `IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)`.
  Every other endpoint still uses the DRF default (`AllowAny`).
- **Request-context resolver:**
  `services.tenancy.get_current_dealership(request)` and
  `services.tenancy.get_active_membership(user)` available and
  consumed by `IsDealerOwnerForAdvisorSlug` indirectly (via role
  check). 4D's new classes will call `get_current_dealership`
  directly.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
- **Dev DB note (unchanged from SESSION_038 handoff):**
  `DealerOnboardingProfile` count = 0.
