---
state: active
date: 2026-07-31
last_session_shipped: SESSION_039
next_session: SESSION_040
---

# Next session — SESSION_040 · Milestone 1 · Increment 4B (DRF auth defaults + request-context tenancy resolver)

> **Milestone 1 is in progress.** SESSION_039 shipped Increment 4A
> (`UserDealershipRole` membership model + `Salesperson.user` link +
> admin registration + 11 tests). Handoff at
> `docs/handoffs/SESSION_039_milestone_1_membership_and_roles.md`.
>
> Increment 4 remains split across six sub-sessions (4A–4F). The
> full contract lives in `docs/roadmap/MILESTONE_1_PLANNING.md` §7.
> SESSION_040 opens **Increment 4B**.
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 —
>   scope boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — acceptance
>   contract (must still verify true after 4B).
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 — Increment 4
>   sub-sequencing (why the work is split A–F).

## What just shipped

- **SESSION_039** — Increment 4A. Test baseline 1,322 → 1,333. Commit
  `<fill after commit>`. Handoff at
  `docs/handoffs/SESSION_039_milestone_1_membership_and_roles.md`.
- **SESSION_038** — Increment 3 (write-path tenancy plumbing +
  `NOT NULL` flip).
- **SESSION_037** — Increments 1 & 2 (`Dealership` model + nullable
  FKs + verified backfill).

## Increment 4 at a glance

Recorded in full at `docs/roadmap/MILESTONE_1_PLANNING.md` §7. Each
sub-increment is a single-session unit; each leaves the application
deployable and the test baseline healthy.

- **4A** ✅ (SESSION_039) — User↔Dealership membership + role foundation.
- **4B** (this session) — DRF `DEFAULT_AUTHENTICATION_CLASSES` +
  `get_current_dealership(request)` resolver. Permission classes
  stay permissive; no endpoint tightens yet.
- **4C** — Advisor workspace: slug-obscurity → auth + tenant scope.
  URL shape preserved.
- **4D** — Admin endpoint gating + queryset scoping across every
  `/api/dealer-ai/admin/*` route + onboarding profile
  (`IsDealerOwner`).
- **4E** — Frontend login page + shared `authFetch()` helper.
- **4F** — Full compatibility sweep + hardening + Milestone 1 close
  (update `CAPABILITY_MATRIX` §7/§8 + roadmap §2.7).

## What SESSION_040 should do — Increment 4B

**Goal:** wire DRF authentication defaults + introduce the
request-context tenancy resolver. **No endpoint-level permission
tightening this session** — that's 4C/4D.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_039_milestone_1_membership_and_roles.md`
     — the membership contract 4B consumes.
   - `docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md`
     — the `services/tenancy.py` primitive 4B extends.
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §1.2 + §7 · 4B.
   - `backend/dealer_ai/services/tenancy.py` — the module 4B extends.
   - `backend/dealer_kit/settings.py::REST_FRAMEWORK` — the current
     config being extended.

2. **Implement in this order:**

   1. **DRF auth defaults.** Populate
      `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]` with
      `rest_framework.authentication.SessionAuthentication` and
      `rest_framework.authentication.TokenAuthentication`. Add
      `rest_framework.authtoken` to `INSTALLED_APPS` and run
      migrations for it. Leave
      `DEFAULT_PERMISSION_CLASSES` **at `AllowAny`** (or omit — same
      effect). The point of 4B is to make requests carry identity when
      credentials are present, not to reject anonymous requests.

   2. **`get_current_dealership(request)` resolver** in
      `backend/dealer_ai/services/tenancy.py`. Resolution order:
      a. `request.user.memberships.first().dealership` when
         `request.user.is_authenticated` and a membership row exists.
      b. `X-Dealership-Slug` header matched against a live
         `Dealership` (falls through silently if the header is missing
         or the slug doesn't resolve — no error).
      c. `get_default_dealership()` — the existing single-tenant
         fallback.
      Signature returns `Dealership`, never `None` (the default is
      the terminal fallback). Extend the module — do not parallel it.

   3. **Resolver tests** in a new
      `backend/dealer_ai/tests/test_current_dealership.py`. Cover:
      - Anonymous request → default.
      - Header-only match → header dealership.
      - Header points at unknown slug → default fallback (no exception).
      - Authenticated user with no membership → default.
      - Authenticated user with one membership → that dealership.
      - Authenticated user with multiple memberships → first (ordered)
        dealership; document the ordering behavior in the docstring so
        4C/4D reviewers know why "first" is safe.
      - Authenticated user's membership wins over any `X-Dealership-Slug`
        header (auth is the stronger signal).
      Test baseline target: 1,333 → ≥ 1,340 (7+ new tests).

3. **Verify continuously.** After each step run
   `python3 manage.py test dealer_ai` and confirm zero regressions.

4. **Verify the §3 compatibility checklist.** Every item must still
   hold — 4B is behavior-transparent to every existing endpoint
   because no permission class tightens.

5. **Close the session** with:
   - Handoff at `docs/handoffs/SESSION_040_<slug>.md`.
   - `docs/CAPABILITY_MATRIX.md` update **not required** — auth model
     doesn't ship until 4F closes Milestone 1.
   - Overwrite this file with the SESSION_041 = Increment 4C priority.

## Explicit non-goals for SESSION_040 (Increment 4B)

- ❌ Do NOT change `DEFAULT_PERMISSION_CLASSES` away from `AllowAny`.
  Endpoint tightening is 4C (advisor) + 4D (admin).
- ❌ Do NOT add `authentication_classes` / `permission_classes` to
  any specific view. The framework-level default is the only auth
  wiring 4B ships.
- ❌ Do NOT touch the advisor workspace or admin endpoints. Those
  are 4C/4D.
- ❌ Do NOT touch frontend code. Login UI is 4E.
- ❌ Do NOT introduce tenant-scoped uniqueness on `Salesperson.slug`,
  `Vehicle.stock_number`, or `DealerOnboardingProfile`.
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT create parallel docs. Update
  `MILESTONE_1_PLANNING.md` §7 only if implementation reveals a
  real deviation from the contract.

## NEXT TASK

Start SESSION_040 with the read-first list above, then implement
Increment 4B in the two-step sequence.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing)
5. `docs/BUSINESS_DOMAIN_MAP.md`
6. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
7. `docs/CAPABILITY_MATRIX.md`
8. Most recent handoffs (`SESSION_039_*.md`, `SESSION_038_*.md`).
9. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_039)

- **Backend (local):** Django on `:8001`. Package `backend/dealer_ai/`.
  Migrations `0001`–`0011` applied. Default `Dealership` row exists
  (`slug='default'`). `UserDealershipRole` table exists (empty).
  `Salesperson.user` FK exists, all existing rows have `user=NULL`.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
  Milestone 1 does not require prod.
- **Frontend (local):** Vite on `:5173`. Unchanged since SESSION_038.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,333 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
- **Dev DB note (unchanged from SESSION_038 handoff):**
  `DealerOnboardingProfile` count = 0. Visit `/dealer-ai-onboarding`
  and save once to restore if the demo relies on a persisted profile.
