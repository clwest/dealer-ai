---
state: active
date: 2026-07-31
last_session_shipped: SESSION_042
next_session: SESSION_043
---

# Next session — SESSION_043 · Milestone 1 · Increment 4E (frontend login + shared authFetch)

> **Milestone 1 is in progress.** SESSION_042 shipped Increment 4D
> (admin endpoint gating + first request-context data scoping + 84
> focused authorization/scoping tests). Handoff at
> `docs/handoffs/SESSION_042_milestone_1_admin_authorization_and_scoping.md`.
>
> Increment 4 is split across six sub-sessions (4A–4F). SESSION_043
> opens **Increment 4E** — the frontend counterpart to the backend
> auth surface 4B–4D shipped.
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/AUTHENTICATION_MODEL.md` — canonical layer
>   separation. §7 lists the shipped 4C+4D permission classes; §8b
>   documents the tenant-scoped query patterns.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — scope
>   boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — acceptance contract.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 · 4E — this session's
>   contract.

## What just shipped

- **SESSION_042** — Increment 4D. Test baseline 1,361 → 1,445.
  Commits `17333af` (feat), `<fill after docs>` (handoff). Handoff at
  `docs/handoffs/SESSION_042_milestone_1_admin_authorization_and_scoping.md`.
- **SESSION_041** — Increment 4C. Commits `76d625b`, `b1816a9`,
  `6c7cc49`.
- **SESSION_040** — Increment 4B. Commits `dc24ab6`, `7fc415f`,
  `aa02bc6`, `02b0252`.
- **SESSION_039** — Increment 4A. Commit `92e3c48`.
- **SESSION_038** — Increment 3.
- **SESSION_037** — Increments 1 & 2.

## Increment 4 at a glance

- **4A** ✅ (SESSION_039) — User↔Dealership membership + role foundation.
- **4B** ✅ (SESSION_040) — DRF auth defaults + `get_current_dealership`.
- **4C** ✅ (SESSION_041) — Advisor workspace: slug-obscurity → auth.
- **4D** ✅ (SESSION_042) — Admin endpoint gating + queryset scoping.
- **4E** (this session) — Frontend login page + shared `authFetch()`
  helper.
- **4F** — Full compatibility sweep + hardening + Milestone 1 close
  (update `CAPABILITY_MATRIX` §7/§8 + roadmap §2.7).

## What SESSION_043 should do — Increment 4E

**Goal:** ship the frontend so real users can drive the authenticated
operator surfaces 4C/4D now gate. Public pages must continue to
render unauthenticated — no regression on `useBrand()`, embed frame,
customer chat, showroom.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/roadmap/AUTHENTICATION_MODEL.md` — the canonical model
     4E must serve without altering.
   - `docs/handoffs/SESSION_042_milestone_1_admin_authorization_and_scoping.md`
     — the backend gate 4E logs users into.
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 · 4E — the contract.
   - `frontend/src/App.tsx` (or the equivalent router entry point)
     — the routing surface 4E extends.
   - `frontend/src/lib/*` — existing fetch helpers; extend the
     existing surface, do not parallel it.

2. **Implement in this order:**

   1. **Backend login/logout view pair** in `backend/dealer_ai/views.py`
      + URL patterns. Simple `POST /api/dealer-ai/auth/login/`
      accepting `{"username", "password"}`, returning 200 with
      user + memberships payload on success and 401 on failure;
      `POST /api/dealer-ai/auth/logout/` accepting session cookie
      and clearing it. Use Django's `authenticate` + `login`
      / `logout` — do not roll a custom auth backend. Add
      permission-class `AllowAny` explicitly on the login endpoint;
      logout requires `IsAuthenticated`.
   2. **Focused tests** for the two auth endpoints — happy path,
      bad credentials 401, logout clears session. Reuse
      `_auth_helpers.py`.
   3. **Frontend `Login.tsx` page** (or the equivalent named path
      under `frontend/src/pages/`). Simple form: username +
      password + submit. On success, redirect to `/dealer-ai-admin/`
      (or wherever the operator lands post-login). On 401 render
      an inline error.
   4. **Shared `authFetch()` helper** in `frontend/src/lib/`.
      Wraps `fetch()`; includes `credentials: "include"` for
      cookie propagation; handles 401 by redirecting to `/login`.
      Every operator page (leads admin, coaching, onboarding,
      advisor workspace) uses `authFetch`.
   5. **React auth context / hook** — lightweight (`useAuth()`
      returning `{user, memberships, login, logout}`). Do NOT
      add a heavyweight state library.
   6. **Wire existing operator pages to `authFetch`.** Public
      pages (`/`, `/assistant`, `/showroom`, `/embed/assistant`)
      keep using plain `fetch` for their public endpoints. The
      onboarding profile GET stays public; only its PUT/PATCH
      needs auth.

3. **Verify continuously:**
   - `python3 manage.py test dealer_ai` after each backend step.
   - `npx tsc --noEmit` and `npx vite build` in `frontend/` after
     each frontend step.
   - **Browser smoke** at session close: log in → open leads
     admin → verify data renders → open advisor workspace →
     verify → log out → verify a 401 redirect to `/login`.

4. **Update `AUTHENTICATION_MODEL.md` §2** to record the login/
   logout endpoint paths and the fact that the frontend uses
   session cookies. Do NOT create parallel docs.

5. **Close the session** with:
   - Handoff at `docs/handoffs/SESSION_043_<slug>.md`.
   - Overwrite this file with the SESSION_044 = Increment 4F
     priority.
   - `docs/CAPABILITY_MATRIX.md` update **not required** —
     Milestone 1 close is 4F.

## Explicit non-goals for SESSION_043 (Increment 4E)

- ❌ Do NOT ship password-reset / password-change flows. Add if
  research surfaces the need; not in the roadmap today.
- ❌ Do NOT ship SSO or MFA (§5 deferred).
- ❌ Do NOT introduce a heavyweight state library (Redux, Zustand,
  Jotai, etc.). React context + `useState` is sufficient for auth
  state today.
- ❌ Do NOT touch backend permission classes or admin views. 4C/4D
  are done.
- ❌ Do NOT gate the `demo/*` endpoints — that decision belongs to
  a separate scope pass (see SESSION_042 handoff §Deferred).
- ❌ Do NOT introduce tenant-scoped uniqueness on any model.
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT commit any real `OPENAI_API_KEY` or user credentials.
- ❌ Do NOT create parallel docs. Update `AUTHENTICATION_MODEL.md`
  only if implementation meaningfully refines the model.

## NEXT TASK

Start SESSION_043 with the read-first list above, then implement
Increment 4E in the six-step sequence.

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
9. Most recent handoffs (`SESSION_042_*.md`, `SESSION_041_*.md`).
10. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_042)

- **Backend (local):** Django on `:8001`. Migrations `0001`–`0011`
  applied; `authtoken` migrations applied. Default `Dealership`
  row exists (`slug='default'`). No `Token` rows in dev DB; no
  live `UserDealershipRole` rows (authorization surface is
  exercised entirely by focused tests).
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
- **Frontend (local):** Vite on `:5173`. Unchanged since SESSION_038.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,445 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`
  installed at framework level; `DEFAULT_PERMISSION_CLASSES` is
  unset.
- **Endpoint-level permission classes shipped:**
  - Advisor workspace + follow-up (4C):
    `[IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)]`.
  - Admin endpoints + manager-chat (4D):
    `[IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]`.
  - Onboarding profile PUT/PATCH + logo upload (4D):
    `[IsAuthenticated & IsDealerOwnerAtActiveDealership]`.
  - Onboarding profile GET (4D): public via
    `[ReadOnly | (IsAuthenticated & IsDealerOwnerAtActiveDealership)]`.
  Every other endpoint still uses the DRF default (`AllowAny`).
- **Service-layer tenant threading:** `trends`, `pipeline`,
  `audit`, `ad_copy` all accept `dealership=` at each entry
  point; `None` resolves to the seeded default for backwards
  compat with pre-4D tests.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
  Ungated `demo/*` endpoints recorded in SESSION_042 handoff.
- **Dev DB note (unchanged from SESSION_038 handoff):**
  `DealerOnboardingProfile` count = 0.
