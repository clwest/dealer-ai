---
state: active
date: 2026-07-31
last_session_shipped: SESSION_043
next_session: SESSION_044
---

# Next session — SESSION_044 · Milestone 1 · Increment 4F (Milestone 1 close)

> **Milestone 1 is nearly complete.** SESSION_043 shipped Increment
> 4E (browser auth flow — three new endpoints, `authFetch`,
> `AuthContext`, `RequireAuth`, `LoginPage`, `CSRF_TRUSTED_ORIGINS`,
> operator/public route split, browser smoke of all 8 required
> steps). Handoff at
> `docs/handoffs/SESSION_043_milestone_1_frontend_auth_flow.md`.
>
> Increment 4 is split across six sub-sessions (4A–4F). SESSION_044
> opens **Increment 4F** — the compatibility sweep, documentation
> flips, and Milestone 1 close.
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/AUTHENTICATION_MODEL.md` — canonical model
>   (§1–§9). Should require no updates in 4F unless the compat
>   sweep uncovers a real refinement.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — scope
>   boundary; §2.7 flips to "Y" at 4F close.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — the acceptance
>   contract 4F verifies end-to-end.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 · 4F — this session's
>   contract.

## What just shipped

- **SESSION_043** — Increment 4E. Test baseline 1,445 → 1,466 +
  clean frontend typecheck + clean vite build + browser smoke
  through all 8 required steps. Commits `0935ed6` (feat),
  `cffa37c` (handoff). Handoff at
  `docs/handoffs/SESSION_043_milestone_1_frontend_auth_flow.md`.
- **SESSION_042** — Increment 4D. Commits `17333af`, `91b634c`,
  `7ab2571`.
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
- **4E** ✅ (SESSION_043) — Frontend login + shared `authFetch()`.
- **4F** (this session) — Full compatibility sweep + hardening +
  Milestone 1 close.

## What SESSION_044 should do — Increment 4F

**Goal:** ship the compatibility sweep, doc flips, and Milestone 1
close in one focused session. No new features. Verify every §3 item
in one place; move `CAPABILITY_MATRIX.md` §7/§8 + roadmap §2.7
from "N" to "Y"; identify Milestone 2 kickoff scope in the handoff.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — the acceptance
     contract.
   - `docs/roadmap/AUTHENTICATION_MODEL.md` — verify the shipped
     model still matches the doc claim.
   - `docs/handoffs/SESSION_043_milestone_1_frontend_auth_flow.md`
     — the last-session state.
   - `docs/CAPABILITY_MATRIX.md` §7 (auth) + §8 (roles) — the
     entries that flip in 4F.
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7 — the
     cross-cutting foundations table.

2. **Do the sweep:**

   1. **Walk §3 of `MILESTONE_1_PLANNING.md` end-to-end.** Every
      item verified true, checked off in the handoff. If an item
      requires a test that does not yet exist and represents an
      obvious gap, add the focused test in this session (do not
      broaden to full integration coverage — 4F is close, not
      expansion).
   2. **Consider one integration test** spanning login → tenant
      scoping → advisor workspace end-to-end IF the focused
      per-layer suite leaves a gap. If the focused suite already
      exercises every layer, do not add integration coverage —
      the risk is duplicating what is already covered.
   3. **Update `docs/CAPABILITY_MATRIX.md` §7 (auth) + §8 (roles):**
      change "N (not implemented)" → "Y (Milestone 1)" with
      pointers to `dealer_ai/permissions.py`,
      `dealer_ai/models.py::UserDealershipRole`,
      `services/tenancy.py::get_current_dealership`, and the
      three `/auth/*` endpoints.
   4. **Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7** —
      Milestone 1 row: flip to "Y" with a short note pointing at
      the Milestone 1 planning artifact + the shipped increments.
   5. **Full backend test suite + frontend typecheck + vite build
      + browser smoke of the 8 steps in the 4E handoff.** Baseline
      must not decrease.

3. **Close the milestone** with:
   - Handoff at `docs/handoffs/SESSION_044_<slug>.md` recording:
     - Every §3 item verified.
     - Every doc flipped.
     - Milestone 1 total test-baseline delta (1,300 → 1,466 across
       SESSION_037–043, with 4F possibly nudging further).
     - Milestone 2 kickoff scope (see below).
   - Overwrite this file with the SESSION_045 = Milestone 2
     Increment 1 priority.

### Milestone 2 kickoff scope (for the handoff to identify)

Per `IMPLEMENTATION_ROADMAP.md` §Milestone 2 — **Vehicle investment
ledger.** Business objective: for any stock number, answer two
questions — "what did we pay to get this vehicle to a saleable
state?" and "what is the true net cost basis?" — with every ledger
row tenant-scoped and every mutation auditable.

Requires Milestone 1 (this session closes it). Recommended
Increment 1: introduce the `VehicleInvestmentEntry` model + the
first two entry kinds (`acquisition_cost`, `reconditioning_cost`).
The 4F handoff should identify this precisely so SESSION_045 opens
with a clear read-first list.

## Explicit non-goals for SESSION_044 (Increment 4F)

- ❌ Do NOT add new features on any surface.
- ❌ Do NOT introduce tenant-scoped uniqueness. Deferred.
- ❌ Do NOT gate `demo/*` endpoints — separate scope decision
  (recorded in SESSION_042 handoff).
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT ship SSO / MFA / password reset.
- ❌ Do NOT split the frontend bundle (chunk-size warning is not a
  Milestone 1 concern).
- ❌ Do NOT commit any real `OPENAI_API_KEY` or user credentials.
- ❌ Do NOT create parallel docs. Update `CAPABILITY_MATRIX.md`
  and `IMPLEMENTATION_ROADMAP.md` in place.

## NEXT TASK

Start SESSION_044 with the read-first list above, then walk the
sweep in three steps.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md` (§7 = increment
   sub-sequencing; §3 = the acceptance contract 4F verifies)
5. `docs/roadmap/AUTHENTICATION_MODEL.md` (canonical model)
6. `docs/BUSINESS_DOMAIN_MAP.md`
7. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
8. `docs/CAPABILITY_MATRIX.md`
9. Most recent handoffs (`SESSION_043_*.md`, `SESSION_042_*.md`).
10. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_043)

- **Backend (local):** Django on `:8001`. Migrations `0001`–`0011`
  applied; `authtoken` migrations applied. Default `Dealership`
  row exists.
- **Dev DB seeded users** (from SESSION_043 browser smoke; safe to
  keep for 4F re-verification): `smoke_owner` (`dealer_owner`) +
  `smoke_advisor` (`advisor`, linked to
  `Salesperson.slug=smoke-advisor-slug`). Password `smoke-pass-4e`
  for both. Not committed to source.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT active.
- **Frontend (local):** Vite on `:5173`. Auth flow wired end-to-end.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,466 pass, 1 skipped, 0 fail.
- **DRF defaults:** `SessionAuthentication` + `TokenAuthentication`
  installed; `DEFAULT_PERMISSION_CLASSES` unset (locked by
  `test_default_permission_classes_remain_unset`).
- **CSRF trust origins:** localhost:5173, 127.0.0.1:5173,
  localhost:3000, 127.0.0.1:3000 (env-configurable via
  `CSRF_TRUSTED_ORIGINS`).
- **Endpoint-level permission classes shipped:** advisor (4C) +
  admin (4D) surfaces.
- **Auth endpoints:** `/auth/login/`, `/auth/logout/`, `/auth/me/`.
- **Frontend auth primitives:** `lib/authFetch.ts`, `lib/auth.ts`,
  `lib/AuthContext.tsx`, `components/RequireAuth.tsx`,
  `pages/LoginPage.tsx`. Sign-out button in the topbar.
- **Public / protected route split** in `src/main.tsx`:
  public = `/`, `/assistant`, `/showroom`, `/embed/assistant`,
  `/login`. Everything else is under `RequireAuth`.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`, `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
