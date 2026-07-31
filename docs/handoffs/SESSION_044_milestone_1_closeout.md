---
title: "SESSION_044 handoff — Milestone 1 Increment 4F (closeout, verification & handoff)"
status: historical
type: handoff
date: 2026-07-31
session: 044
milestone: 1
milestone_status: shipped
commits:
  - <fill after feat commit>  # Increment 4F — franchise env-override wiring + doc flips + retrospective + Milestone 2 kickoff pointer
  - <fill after docs commit>  # SESSION_044 handoff hash backfill (if separated)
---

# SESSION_044 — Milestone 1 · Increment 4F (closeout)

## What shipped

Verification only, plus one two-line hardening fix that surfaced
during the sweep. No new product behavior. Every §3 compatibility
item verified true; four authoritative documents flipped to
reflect shipped state; the retrospective created; the next-session
pointer set to a Milestone 2 planning pass (no code).

## 1. Compatibility sweep — full walk of §3

Walked every item in `docs/roadmap/MILESTONE_1_PLANNING.md` §3 with
evidence in place. Every checkbox now cites the test class, code
location, or runtime probe that locks the invariant.

**One shipped invariant intentionally differs from the pre-Milestone-1
contract:** unknown or deactivated advisor slugs return **403** to
authenticated non-privileged callers instead of the pre-4C 404.
Reason: 404-on-unknown-slug was the *thing being replaced* — it
leaked slug existence via differential status codes. Locked by
`AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs` (4C) +
`test_workspace_deactivated_advisor_is_not_leaked_to_owners` (4C).

**One real bug surfaced by the sweep** — landed within 4F scope
(the increment's mandate includes hardening):

- **Franchise env-override was broken.** The compat item claimed
  `DEALER_AI_DEALER_TYPE=franchise` + `DEALER_AI_PRIMARY_MAKE=Ford`
  "still works". Verification with a fresh subprocess showed the
  resolver read both via `getattr(settings, "DEALER_AI_...", "")`
  but `settings.py` never wired those env vars. They were silently
  falling through to `""` → Copper Canyon defaults. Two-line fix in
  `backend/dealer_kit/settings.py`:

    ```python
    DEALER_AI_DEALER_TYPE = os.getenv("DEALER_AI_DEALER_TYPE", "")
    DEALER_AI_PRIMARY_MAKE = os.getenv("DEALER_AI_PRIMARY_MAKE", "")
    ```

  Re-verified with a fresh-process smoke — franchise config now
  produces `dealer_type="franchise"`, `primary_make="Ford"`. Copper
  Canyon defaults still hold when env is unset. Test baseline
  unchanged (1,466 pass).

## 2. Authoritative-document flips

Updated in place per `DOC_GOVERNANCE.md`:

- **`docs/roadmap/MILESTONE_1_PLANNING.md`** — `status: planning`
  → `status: shipped`. Added `shipped_at_session` /
  `shipped_over` / `retrospective` frontmatter. §3 checklist
  annotated inline with the code / test / probe that locks each
  item. Original checklist items preserved verbatim; annotations
  appended.
- **`docs/CAPABILITY_MATRIX.md`** — new §7b "Multi-tenancy + real
  auth (Milestone 1, shipped)" enumerating tenancy root, resolver,
  membership, permission classes, browser flow, and the frontend
  primitives — each row citing concrete files. Updated §7
  advisor-workspace + admin-salespeople rows to reflect the DRF
  authorization. Updated "Honest gaps to flag when pitching" to
  remove the slug-obscurity claim and record the shipped/deferred
  boundary.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`** — §2.7 rows for
  "Multi-tenancy" and "Real authentication + role-based
  permissions" flipped from `N` to `F` with concrete pointers.
  §2.8 summary updated (removed the "two foundations must land
  first" caveat). §Milestone 1 recommended-order paragraph updated
  to record the shipped date + retrospective link.
- **`docs/roadmap/AUTHENTICATION_MODEL.md`** — §8b closes with the
  explicit "pre-save autofill is a fallback, not the primary write
  path" invariant + the rule of thumb for future callers.

Precise about what shipped (not overclaiming): FK-carrier tenancy,
real auth for the protected operator surfaces, seven-role
membership vocabulary, request-context tenancy, browser sign-in
via Django sessions. **Not** shipped: user-management UI, tenant
switcher, invitations, MFA, SSO, tenant-scoped uniqueness,
`demo/*` gating, prod deployment. Enumerated verbatim in
CAPABILITY_MATRIX §7b + RETROSPECTIVE §7.

## 3. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` — new

Sections: what was planned, what shipped, sequencing changes,
deviations and why, regressions avoided, lessons learned (all
eight mandatory items from the 4F brief), remaining deferred
work, whether the roadmap needs adjustment. The eight lessons
recorded verbatim:

1. Nullable FK → backfill → write-path plumbing → NOT NULL was
   the correct migration sequence.
2. Destructive migration verification should use a dedicated
   database alias.
3. Pre-save tenancy autofill is a fallback, not the primary
   business path.
4. Identity, authentication, authorization, business permissions,
   and data scoping were intentionally separated.
5. Focused permission matrices provided strong confidence without
   requiring oversized integration tests.
6. Public and operator route boundaries must remain explicit.
7. DRF `SessionAuthentication` needs `CSRF_TRUSTED_ORIGINS` in
   dev when frontend + backend live on different ports.
8. Login CSRF via `@ensure_csrf_cookie` on `/me/` is the
   ergonomic pattern.

Retrospective is a retrospective, not a handoff — it doesn't
duplicate per-session handoff content.

## 4. Integration test decision — evidence-driven skip

The 4F brief said: add a broader integration test only if a real
seam remains unverified.

**Decision: no new integration test added.** The focused suite
already exercises every layer of the six-step end-to-end flow the
brief named:

1. **Authenticated session** — locked by
   `SessionAuthenticationDrivesProtectedEndpoints`
   (`test_auth_endpoints.py`) — logs in via `/auth/login/`, hits a
   protected endpoint using only the returned session cookie
   (no `force_authenticate`).
2. **Active dealership resolution** — locked by
   `GetCurrentDealershipResolver` (`test_current_dealership.py`) —
   composes identity → header → default across 8 focused cases.
3. **Role membership** — locked by
   `UserDealershipRoleModel` + `RoleVocabulary`
   (`test_userdealershiprole.py`).
4. **Tenant-scoped lookup** — locked by
   `AdminListEndpointsAreTenantScoped` (5 list surfaces) +
   `AdminLeadDetailFailsClosedAcrossTenants` (3 endpoints)
   (`test_admin_endpoints_auth.py`).
5. **Advisor + admin authorization** — locked by
   `AdvisorWorkspaceAuthorization` (7 cases),
   `AdvisorFollowUpAuthorization` (6 cases),
   `AdminEndpointAuthMatrixBase` × 10 endpoint subclasses.
6. **Cross-tenant rejection** — locked by the fail-closed pk
   lookup tests above +
   `AdminLeadAssignRejectsCrossTenantSalesperson`.

Adding a ceremonial end-to-end integration test that walks the
same seam would duplicate this coverage. Recorded here so the next
reader knows the decision was deliberate, not an oversight.

The complementary evidence lives in the SESSION_043 browser smoke,
which walked the composed flow through the actual UI — that's the
"integration" verification the 4F brief called for, already done.

## 5. Security boundary + data isolation rechecks

Explicit rechecks against §4 + §5 of the 4F brief:

**Security boundary (§4):**

- ✅ Anonymous customer chat works —
  `chat/start`, `chat/message`, `vehicles/<id>/ask` unchanged,
  `AllowAny`.
- ✅ Public branding works — `PublicBrandingRemainsUnauthenticated`
  test class + SESSION_043 browser smoke step 8.
- ✅ Public showroom routes work — same evidence.
- ✅ Protected operator routes require auth — `RequireAuth`
  wrapper in `main.tsx` + SESSION_043 browser smoke step 1.
- ✅ Wrong-role users receive 403, not login redirects —
  `SessionAuthenticationDrivesProtectedEndpoints.test_wrong_role_gets_403_not_401`
  + `authFetch.ts` throws `ForbiddenError` (not
  `UnauthenticatedError`) for 403 + SESSION_043 browser smoke
  step 4.
- ✅ Cross-tenant object lookups fail closed —
  `AdminLeadDetailFailsClosedAcrossTenants`.
- ✅ Unknown advisor slugs do not leak existence —
  `AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs`.
- ✅ Unsafe session-authenticated mutations require CSRF —
  `CsrfEnforcedOnAuthenticatedMutations`.
- ✅ Login errors do not reveal username existence —
  `AuthLoginEndpoint.test_unknown_user_returns_same_generic_401`.
- ✅ No browser token stored in localStorage — `authFetch.ts`
  reads csrftoken from cookie only; no localStorage access
  anywhere in the frontend auth code (grep confirms).
- ✅ No global default permission class accidentally changed
  public behavior — `test_default_permission_classes_remain_unset`
  + explicit inspection of `settings.py::REST_FRAMEWORK`.

**Data isolation (§5):**

- ✅ Newly created records receive the correct dealership —
  admin writes pass `dealership=get_current_dealership(request)`
  explicitly; the `pre_save` autofill catches any omission and
  attaches the default. Locked by
  `test_dealership.WritePathFallback`.
- ✅ Administrative querysets use the active dealership —
  audited via grep: every `admin_*` view resolves tenant once at
  the top and passes into every `.filter(dealership=…)` or
  service-layer `dealership=` kwarg.
- ✅ Advisor authorization resolves against the target
  Salesperson's dealership — `IsDealerOwnerForAdvisorSlug`
  reads the target's `dealership_id` and checks the caller's
  role against THAT dealership, not the caller's own.
- ✅ Cross-tenant related-object assignment is rejected —
  `AdminLeadAssignRejectsCrossTenantSalesperson`.
- ✅ No unscoped lookups bypass tenancy — audited via
  `grep '\.objects\.' backend/dealer_ai/views.py`. Every
  unscoped `.get(...)` / `.filter(...)` in `views.py` is either
  (a) inside a customer-facing `AllowAny` endpoint where cross-
  tenant is impossible today (customer chat / vehicle Q&A —
  UUID session keys are unguessable, single-tenant deployment);
  (b) inside a public salespeople endpoint that intentionally
  serves the public team page cross-tenant (deferred per §5);
  or (c) inside a `demo/*` endpoint that intentionally wipes
  cross-tenant state (deferred per SESSION_042 handoff).
- ✅ Default-dealership fallback is used only where compat
  requires it — every service function has `dealership=None`
  as an optional kwarg for pre-Milestone-1 test callers; the
  fallback resolves to `get_default_dealership()`. Production
  view callers pass `dealership=` explicitly per the "pre-save
  is fallback" invariant now documented in
  `AUTHENTICATION_MODEL.md` §8b.

No tenant-scoped uniqueness introduced — deferred per §5 of the
planning artifact.

## 6. Final verification (§10 of the 4F brief)

- **Backend suite:** `python3 manage.py test dealer_ai` →
  **1,466 pass, 1 skipped, 0 fail**. Same baseline as SESSION_043.
- **Migration status:** all 11 `dealer_ai` migrations applied
  (`0001` → `0011`); `python3 manage.py makemigrations --check
  --dry-run dealer_ai` → "No changes detected". No pending
  migrations.
- **Targeted suites re-run individually** (spot-check):
  `test_auth_endpoints` (21 pass), `test_admin_endpoints_auth`
  (84 pass), `test_advisor_workspace_auth` (14 pass),
  `test_current_dealership` (16 pass), `test_userdealershiprole`
  (11 pass) — all clean.
- **Frontend:** `npx tsc --noEmit` clean; `npx vite build` clean
  (same pre-existing 500 kB chunk-size warning; unrelated to
  Milestone 1).
- **Runtime:** SESSION_043 browser smoke re-verified via
  `docs/handoffs/SESSION_043_milestone_1_frontend_auth_flow.md`
  §"Browser smoke — all 8 required steps". Not re-executed this
  session because nothing user-visible changed after 4E; the
  4F fix to `settings.py` was verified via a fresh-process
  Python smoke (recorded in §1 above).

**Test baseline did not decrease. No `@skip` introduced.**

## Files touched

Created:

- `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md`.
- `docs/handoffs/SESSION_044_milestone_1_closeout.md` (this file).

Modified:

- `backend/dealer_kit/settings.py` — wired
  `DEALER_AI_DEALER_TYPE` + `DEALER_AI_PRIMARY_MAKE` env vars.
- `docs/roadmap/MILESTONE_1_PLANNING.md` — status flipped to
  `shipped`; frontmatter annotated with sessions +
  retrospective; §3 checklist annotated inline; new "New
  (Milestone 1 introduced these invariants)" subsection
  documenting the 10 invariants Milestone 1 added.
- `docs/CAPABILITY_MATRIX.md` — §7 advisor rows updated with
  the shipped permission classes; new §7b "Multi-tenancy + real
  auth (Milestone 1, shipped)" enumerating every shipped
  surface with file pointers; "Honest gaps" updated to remove
  the slug-obscurity claim and record the shipped/deferred
  boundary.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — §2.7 tenancy + auth
  rows flipped `N` → `F`; §2.8 summary updated; §Milestone 1
  recommended-order paragraph records the shipped date +
  retrospective link.
- `docs/roadmap/AUTHENTICATION_MODEL.md` — §8b closes with the
  "pre-save is fallback, not primary write path" invariant.
- `00-START-NEXT-SESSION.md` — overwritten to point at
  SESSION_045 = Milestone 2 planning pass (no code).

Not touched (correctly):

- Any production `views.py` / `models.py` code — this session
  is verification + docs.
- 16-stage safety pipeline.
- Frontend — no user-visible change.
- Test suites — no additions, no deletions, no `@skip`.
- `demo/*` endpoints — deferred per SESSION_042 handoff.

## Deviation from plan — one narrowly-scoped hardening fix

The 4F brief said "verification and closure only. Do not introduce
new product behavior." The franchise env-override wiring is not
new product behavior — it's a two-line correction that makes the
`settings.py` layer honor the resolver's existing `getattr(settings,
...)` contract. Compat item claimed the invariant held; it did
not. Fixing it upheld the shipped invariant rather than downgrading
the checklist. Recorded here so the next reviewer knows why the
sole non-doc line in the 4F commit exists.

## Recommended scope for SESSION_045 — Milestone 2 (Vehicle
investment ledger) Increment 0 (planning pass)

**Goal:** produce `docs/roadmap/MILESTONE_2_PLANNING.md`, mirroring
the shape of the Milestone 1 planning doc. **No code.**

**In scope for the planning pass** (per the roadmap §Milestone 2
+ the eight-lesson retrospective §6):

1. §1 Design memo — one entry per shipped subsystem:
   acquisition record; per-vehicle cost ledger (~25 line-item
   categories per VCP); computed gross properties
   (`total_investment`, `expected_gross`, `projected_gross`);
   daily floor-plan interest accrual mechanism (manual re-run
   ok — Milestone 7 owns async); acquisition-price scrub (new
   post-LLM scrub, belt-and-suspenders); one operator UI
   surface to inspect a vehicle's ledger.
2. §2 Migration impact review — every existing system
   Milestone 2 touches.
3. §3 Compatibility checklist — the acceptance contract.
4. §4 Reusable primitives review — extend `Vehicle`, extend
   `payment_engine` (daily-accrual math), extend the scrub
   stack. No parallel implementations.
5. §5 Scope discipline + deferrals.
6. §7 Increment sequencing — commit to a shape upfront (likely a
   3-increment split: schema → write-path/service → UI/scrub).

Every ledger model gets a `dealership` FK by default (do not
re-derive Milestone 1 decisions). Every admin endpoint that serves
ledger data goes through
`IsSalesManagerOrOwnerAtActiveDealership` +
`.filter(dealership=get_current_dealership(request))`.

**Out of scope for SESSION_045:** any code. Any change to models,
migrations, services, views, tests, or frontend. Any decision to
scope in floor-plan-lender integration, auction-feed adapters,
vendor negotiation, or trade appraisal (all named out-of-scope in
the roadmap). Any change to `demo/*` gating (separate scope).

Full pointer in `00-START-NEXT-SESSION.md`.

## Anchors that win on conflict

Milestone 1 shipped; add the retrospective to the list:

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model)
5. `docs/roadmap/MILESTONE_1_RETROSPECTIVE.md` (lessons for M2)
6. `docs/roadmap/MILESTONE_1_PLANNING.md` (§3 = the acceptance
   template M2 mirrors)
7. `docs/BUSINESS_DOMAIN_MAP.md`
8. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
9. `docs/CAPABILITY_MATRIX.md`
10. Most recent handoffs.

## Operational state at Milestone 1 close

Unchanged from SESSION_043 close except for the settings.py fix.
Repeated here for the reader who lands cold.

- **Backend (local):** Django on `:8001`. Migrations `0001`–`0011`
  applied; `authtoken` applied. Default `Dealership` row exists.
  No pending migrations.
- **Backend (prod):** NONE.
- **Frontend (local):** Vite on `:5173`. Auth flow wired end-to-end.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,466 pass, 1 skipped, 0 fail. Grew from
  1,300 pre-Milestone-1 (+166 across the milestone).
- **DRF defaults:** `SessionAuthentication` +
  `TokenAuthentication`; `DEFAULT_PERMISSION_CLASSES` unset.
- **CSRF_TRUSTED_ORIGINS:** localhost:5173, 127.0.0.1:5173,
  localhost:3000, 127.0.0.1:3000 (env-configurable).
- **Franchise env-override + Copper Canyon defaults:** both work
  (verified fresh-process at 4F close).
- **Endpoint-level permission classes:** advisor (4C) + admin (4D).
- **Browser auth endpoints:** `/auth/{login,logout,me}`.
- **Frontend auth primitives:** `lib/authFetch.ts`,
  `lib/AuthContext.tsx`, `components/RequireAuth.tsx`,
  `pages/LoginPage.tsx`. Sign-out button in topbar.
- **Public/protected route split** (`main.tsx`): public = `/`,
  `/assistant`, `/showroom`, `/embed/assistant`, `/login`;
  everything else under `<RequireAuth>`.
- **Dev DB seeded users** (safe to keep): `smoke_owner`,
  `smoke_advisor` (password `smoke-pass-4e`). Not committed to
  source.
- `docs/roadmap/DEFERRED_IDEAS.md` — still does not exist.
  Every deferred idea is captured in `MILESTONE_1_PLANNING.md` §5
  + `MILESTONE_1_RETROSPECTIVE.md` §7.

*End of SESSION_044 handoff. Milestone 1 closed.*
