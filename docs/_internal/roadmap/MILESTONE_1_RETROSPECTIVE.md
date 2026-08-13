---
title: "Milestone 1 — Retrospective"
status: shipped
type: retrospective
date: 2026-07-31
sessions: SESSION_037 → SESSION_044
milestone: 1
milestone_name: "Multi-tenant + role-based access foundation"
related:
  - docs/roadmap/MILESTONE_1_PLANNING.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/CAPABILITY_MATRIX.md §7b
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §2.7
---

# Milestone 1 — Retrospective

Written at Milestone 1 close (SESSION_044). Records what was
planned, what shipped, what deviated and why, and the lessons that
should shape Milestone 2 and beyond. Not another handoff — the
handoffs already carry the per-session diffs.

## 1. What was planned

`MILESTONE_1_PLANNING.md` at SESSION_035 laid out five design memos
(§1 tenancy, real auth, roles, advisor-workspace slug replacement,
singleton→per-tenant migration path) plus a §3 compatibility
checklist that every existing invariant had to uphold. §5 identified
the deferrals (multi-photo storage, `Vehicle.is_available` compute,
tenant-scoped uniqueness, SSO/MFA, user-management UI, per-role UI
polish) and named the milestones they would land in.

Increment sequencing was added to §7 at SESSION_038 close: three
structural increments (Increments 1–3 — tenancy model, FK
carriers + backfill, write-path plumbing + NOT NULL) followed by
Increment 4 split across six sub-sessions (4A membership + role
vocabulary, 4B auth defaults + request-context resolver, 4C
advisor authorization, 4D admin authorization + data scoping, 4E
browser auth flow, 4F closeout).

## 2. What shipped

Every §3 compatibility item verified true; details in the annotated
checklist at `MILESTONE_1_PLANNING.md` §3. Summary of the shipped
substrate:

| Layer | Shipped surface | Session |
|---|---|---|
| Tenancy root | `models.Dealership` + migration `0007` | 037 (Inc. 1) |
| Nullable FKs on six carriers + verified backfill | migrations `0008` + `0009` | 037 (Inc. 2) |
| Write-path plumbing + `NOT NULL` | `services/tenancy.py` + migration `0010` + `pre_save` autofill | 038 (Inc. 3) |
| User↔Dealership membership + seven-role vocabulary | `UserDealershipRole`, `Salesperson.user` link, migration `0011` | 039 (Inc. 4A) |
| DRF auth defaults + request-context resolver | `SessionAuthentication` + `TokenAuthentication`, `get_current_dealership`, `get_active_membership` (extension seam) | 040 (Inc. 4B) |
| Advisor authorization | `IsAdvisorForSlug`, `IsDealerOwnerForAdvisorSlug` | 041 (Inc. 4C) |
| Admin authorization + first request-context data scoping | `IsSalesManagerOrOwnerAtActiveDealership`, `IsDealerOwnerAtActiveDealership`, `ReadOnly`; service-layer `dealership=` threading through `trends`, `pipeline`, `audit`, `ad_copy` | 042 (Inc. 4D) |
| Browser sign-in flow | `/auth/{login,logout,me}` + `CSRF_TRUSTED_ORIGINS` + `authFetch`/`AuthContext`/`RequireAuth`/`LoginPage` | 043 (Inc. 4E) |
| Milestone close: compat sweep + doc flips + retrospective | This session + franchise env-override wiring fix | 044 (Inc. 4F) |

**Test baseline:** 1,300 → 1,466 pass (+166), 1 skipped, 0 fail
across the milestone. Zero regressions. No test suppressed with
`@skip`. Frontend `npx tsc --noEmit` clean; `npx vite build`
clean.

## 3. Sequencing changes

The Increment 4 split into 4A–4F (added at SESSION_038 close, §7
of the planning doc) is the only material sequencing deviation
from the original SESSION_035 plan. The plan named "endpoint
authentication" as a single Increment 4; SESSION_038 recognized
that a monolithic auth increment would be high-blast-radius work
with poor rollback granularity, and traded one long session for
six smaller ones with independent verification points. The trade
paid off — every session ended with a healthy baseline and the
next reviewer could resume without a running-context tax.

## 4. Deviations and why

Four intentional deviations from the shipped-as-planned expectation,
each recorded in its session's handoff:

1. **Multi-role per dealership** (4A, SESSION_039). The planning
   memo did not specify whether a User could hold multiple concurrent
   roles at one dealership. The shipped
   `UserDealershipRole.unique_together = (user, dealership, role)`
   permits it — an intentional choice for indie shops where the
   owner routinely acts as sales manager. Documented in
   `MILESTONE_1_PLANNING.md` §7 · 4A design note.

2. **`get_active_membership` extension seam** (4B, SESSION_040). The
   original 4B contract described a single `get_current_dealership`
   function. Review guidance at SESSION_039 close identified that
   `user.memberships.first()` should not become the durable
   business rule for "which dealership is this user acting within".
   Refactored the contract (commit `dc24ab6`) into
   `get_active_membership(user)` (extension seam) +
   `get_current_dealership(request)` (composer). Future
   dealership-switching UI replaces the seam's body without
   touching the composer or any downstream caller.

3. **Slug-obscurity 404 → real-auth 403** (4C, SESSION_041). Under
   the pre-auth mechanism, an unknown advisor slug returned 404,
   which leaked slug existence via differential status codes. The
   shipped authorization returns 403 uniformly for unknown slugs +
   deactivated advisors + cross-tenant callers. This is a strict
   security improvement; two pre-4C tests that codified the old
   leaky behavior were retired and their coverage moved to
   `test_advisor_workspace_auth`.

4. **Admin "wrong tenant" tests removed from the shared matrix**
   (4D, SESSION_042). Initial focused-test matrix included
   `sales_manager_at_wrong_tenant` and
   `dealer_owner_at_wrong_tenant` cases; both failed with 200
   because admin endpoints derive their active dealership from the
   caller's membership — the "wrong tenant" concept is not
   expressible for this URL-shape family. Cross-tenant data
   protection is a data-layer invariant (locked by
   `AdminListEndpointsAreTenantScoped`,
   `AdminLeadDetailFailsClosedAcrossTenants`,
   `AdminLeadAssignRejectsCrossTenantSalesperson`), not a
   permission-layer invariant. The mixin's docstring records this
   distinction so future admin surfaces reuse the correct pattern.

Plus one **evidence-driven fix landed at 4F close**:
`DEALER_AI_DEALER_TYPE` and `DEALER_AI_PRIMARY_MAKE` env variables
were referenced by the resolver via `getattr(settings, ...)` but
were never wired in `settings.py`. The §3 checklist claimed the
franchise env-override "still works" — verification proved
otherwise. Two-line fix landed in `settings.py`; the invariant is
now truly upheld, verified via a fresh-process smoke.

## 5. Regressions avoided

The compatibility contract held in full. Explicit rechecks at
milestone close:

- **Public branding renders unauthenticated.** GET `/onboarding/profile/`,
  `/salespeople/`, `/`, `/assistant`, `/showroom`, `/embed/assistant`
  all resolve without a session. Locked by
  `test_auth_endpoints.PublicBrandingRemainsUnauthenticated` +
  browser smoke (SESSION_043 step 8).
- **Customer chat, vehicle Q&A, lead creation.** Unchanged. Every
  scrub-stack test in the 1,466 baseline passes.
- **Franchise env-override + Copper Canyon defaults.** Both
  verified at 4F close via a fresh-process smoke (see §"Deviations"
  item on `settings.py` fix).
- **Payment engine.** Untouched.
- **16-stage safety pipeline.** Untouched.
- **`DEFAULT_PERMISSION_CLASSES` unset.** Locked by
  `test_default_permission_classes_remain_unset` from 4B.
- **401 / 403 / 404 distinction.** Locked by
  `SessionAuthenticationDrivesProtectedEndpoints.test_wrong_role_gets_403_not_401`
  and by the browser smoke (advisor cross-slug shows 403 UI, not a
  /login redirect).
- **CSRF enforced on authenticated mutations.** Locked by
  `CsrfEnforcedOnAuthenticatedMutations`.
- **No user enumeration on login.** Locked by
  `AuthLoginEndpoint.test_unknown_user_returns_same_generic_401`.

## 6. Lessons learned

The lessons the next milestone should carry forward:

1. **Nullable FK → backfill → write-path plumbing → `NOT NULL` is
   the correct migration sequence.** Attempted the other order in
   thought early — landing NOT NULL first would have required an
   application-level lock (block writes) during the window between
   FK addition and backfill. The three-migration sequence
   (`0008` add nullable, `0009` backfill, `0010` flip to NOT NULL)
   let the migration run against a live dev DB with zero writer
   coordination and no observable outage.

2. **Destructive migration verification should use a dedicated
   database alias.** SESSION_038 verified `migrate dealer_ai zero`
   → `migrate` against the actual dev DB, wiping ~200 rows of
   demo data that had to be re-seeded via three seed commands
   (recorded in that handoff). The right pattern is
   `DATABASES["migration_check"]` — a dedicated alias that the
   migration-verification script points at, isolating destructive
   probes from developer state. Add for Milestone 2's ledger
   migrations.

3. **Pre-save tenancy autofill is a fallback, not the primary
   business path.** Documented explicitly in
   `AUTHENTICATION_MODEL.md` §8b at 4F close. Production views
   MUST pass `dealership=get_current_dealership(request)`
   explicitly. The signal exists to defeat "forgot to pass tenant"
   bugs from causing null-FK integrity errors — not to be the
   architecture. Relying on the fallback in production code is a
   bug: a request-scoped tenant would silently write against the
   default dealership instead of the caller's active one.

4. **Identity, authentication, authorization, business permissions,
   and data scoping are intentionally separated layers.** Each
   layer owns one question; a failure in one is not another
   layer's job to catch. Introduced formally in
   `AUTHENTICATION_MODEL.md` §1. Every 4C/4D endpoint respects the
   split. Preserving the split kept the permission classes small
   and reusable — `IsAdvisorForSlug` and
   `IsDealerOwnerAtActiveDealership` are both under 30 lines
   because tenant resolution + role check + view-level scoping are
   distinct concerns living in distinct places.

5. **Focused permission matrices provided strong confidence without
   requiring oversized integration tests.** Each endpoint family
   (advisor, admin, onboarding) shipped with a permission-matrix
   test class enumerating the six required outcomes. At 4F close,
   the focused suite already exercises every layer (identity via
   session cookie in
   `SessionAuthenticationDrivesProtectedEndpoints`; authorization
   via each matrix; data scoping via
   `AdminListEndpointsAreTenantScoped`,
   `AdminLeadDetailFailsClosedAcrossTenants`). A ceremonial
   end-to-end integration test that would duplicate this coverage
   was **not** added — 4F verified the seam is fully locked by the
   focused suite.

6. **Public and operator route boundaries must remain explicit.**
   The frontend split (`main.tsx` — public routes OUTSIDE
   `<RequireAuth>`, operator routes INSIDE) is the single place
   where the boundary lives. `lib/api.ts` mirrors it: public
   endpoints use plain `fetch`, operator endpoints use `authFetch`.
   A broken session on a customer-facing page cannot cause a
   `/login` redirect because the code path never reaches
   `authFetch`. Every future milestone that adds a public route
   must place it outside the gate; every future operator route
   must go inside.

7. **DRF `SessionAuthentication` needs `CSRF_TRUSTED_ORIGINS` in
   dev when the frontend and backend live on different ports.**
   Not documented anywhere in the DRF quickstart. Costs half a
   session's debugging when discovered late; costs zero when the
   setting is added alongside the auth endpoints. Env-configurable
   so prod (single-origin behind one domain) can override.

8. **Login CSRF via `@ensure_csrf_cookie` on the `/me/` boot call
   is the ergonomic pattern.** No separate `/csrf/` endpoint;
   the boot call the frontend has to make anyway doubles as the
   CSRF primer. Documented in `AUTHENTICATION_MODEL.md` §2b.

## 7. Remaining deferred work

Recorded here so nothing gets rediscovered from source.

**In scope for later milestones (per `MILESTONE_1_PLANNING.md` §5
+ the roadmap):**

- Tenant-scoped uniqueness on `Salesperson.slug`,
  `Vehicle.stock_number`, `DealerOnboardingProfile` — lands in the
  milestone that first needs a second live dealership. Deferred
  because premature schema tightening on globally-unique fields
  would require a data migration that has no live consumer today.
- `Vehicle.is_available` → computed lifecycle. Milestone 5 concern.
- Multi-photo file storage (S3-compatible + CDN). Milestone 3
  concern; may need a pre-M3 half-milestone per the VCP.
- `Vehicle.make` default `"Ford"` rename. Milestone 2 or Milestone
  5 opportunistically.
- Full CRM / F&I / BHPH / accounting departments (Milestones 2, 6,
  9–13).

**Explicitly out-of-scope for the auth model** (per
`AUTHENTICATION_MODEL.md` §9):

- SSO (SAML, OIDC beyond Django's built-ins). No research trigger.
- MFA. No research trigger.
- Row-level ACLs beyond dealership scope.
- Impersonation / act-as flows.
- API rate limiting per token.
- Structured audit log of authentication events for GLBA / FDCPA
  compliance. Milestone 10 / Milestone 12 concern.

**Post-Milestone-1 hardening candidates** (recorded now so the
first Milestone 2 session can decide whether to fold any of them
in):

- Gate `demo/reset/` + `demo/scenarios/` endpoints. Currently
  ungated because their design intent is "wipe all demo state,
  cross-tenant". Under a real multi-tenant deployment they need
  either `dealer_owner` gating with same cross-tenant semantics
  (undesirable) or per-tenant scoping (semantically different).
  Separate scope decision.
- User-management CLI (`manage.py create_dealer_owner <username>
  <dealership_slug>`). Right now provisioning the first
  `dealer_owner` requires either a manual `shell` seed script or
  the Django admin `UserDealershipRoleAdmin` surface. A CLI would
  shorten Milestone 2 onboarding for future dealers.
- Frontend bundle chunk-splitting. `dist/assets/index-*.js` is
  502 kB / 138 kB gz — one vite warning. Explicitly not a
  Milestone 1 concern; noted for whichever milestone owns the
  frontend perf pass.

## 8. Does the roadmap need adjustment?

**No structural changes.** The Milestone 1 → Milestone 13 sequence
in `IMPLEMENTATION_ROADMAP.md` §4 remains sound. Two small edits
already landed at 4F close:

- §2.7 rows for "Multi-tenancy" and "Real auth" flipped from N to F
  with concrete pointers.
- §Milestone 1 recommended-order paragraph updated to record the
  shipped date + retrospective link.

Milestone 2 (Vehicle investment ledger) is next. Its planning
artifact will land in SESSION_045 per the next-session pointer.
The retrospective's most relevant guidance for Milestone 2:

- **Migration sequence** — use the nullable → backfill → NOT NULL
  pattern for the ledger's stock-number FK if it needs backfill.
- **Dedicated migration-check DB alias** — set up before running
  any destructive migration verification.
- **Layer discipline** — the ledger's row-level permissions
  (does this user have write access to this cost entry?) belong
  in **Business permissions** (layer 3), not authorization. Every
  service function that queries the ledger should thread
  `dealership=` explicitly — no hidden filtering.
- **Focused test matrix over integration tests** — enumerate the
  six required outcomes per endpoint family.

---

*End of Milestone 1 retrospective.*
