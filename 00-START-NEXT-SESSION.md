---
state: active
date: 2026-07-31
last_session_shipped: SESSION_038
next_session: SESSION_039
---

# Next session — SESSION_039 · Milestone 1 · Increment 4A (User↔Dealership membership + role foundation)

> **Milestone 1 is in progress.** SESSION_038 shipped Increment 3
> (write-path tenancy plumbing + `NOT NULL` on all six tenancy FKs).
> Handoff at
> `docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md`.
>
> **Increment 4 is split across six sessions (4A–4F).** The full
> per-sub-increment scope + rationale is recorded in
> `docs/roadmap/MILESTONE_1_PLANNING.md` §7. SESSION_039 opens
> Increment 4A.
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 —
>   scope boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §3 — acceptance
>   contract (must still verify true after 4A).
> - `docs/roadmap/MILESTONE_1_PLANNING.md` §7 — Increment 4
>   sub-sequencing (why the work is split A–F).

## What just shipped

- **SESSION_038** — Increment 3 (write-path tenancy plumbing +
  `NOT NULL` flip). Commits `9ea7ff3`, `bf4197f`, `8760292`. Test
  baseline 1,313 → 1,322. Handoff at
  `docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md`.
- **SESSION_037** — Increments 1 & 2 (`Dealership` model +
  nullable FKs + verified backfill).

## Increment 4 at a glance

Recorded in full at `docs/roadmap/MILESTONE_1_PLANNING.md` §7.
Each sub-increment is a single-session unit; each leaves the
application deployable and the test baseline healthy.

- **4A** (this session) — User↔Dealership membership + role
  foundation. Model + admin + tests. **Zero endpoint auth
  changes.**
- **4B** — DRF `DEFAULT_AUTHENTICATION_CLASSES` +
  `get_current_dealership(request)` resolver. Permission classes
  stay permissive; no endpoint tightens yet.
- **4C** — Advisor workspace: slug-obscurity → auth + tenant
  scope. URL shape preserved.
- **4D** — Admin endpoint gating + queryset scoping across every
  `/api/dealer-ai/admin/*` route + onboarding profile
  (`IsDealerOwner`).
- **4E** — Frontend login page + shared `authFetch()` helper.
- **4F** — Full compatibility sweep + hardening + Milestone 1
  close (update `CAPABILITY_MATRIX` §7/§8 + roadmap §2.7).

## What SESSION_039 should do — Increment 4A

**Goal:** land the User↔Dealership membership model + role
vocabulary so 4B–4D have something to check against. **No
endpoint auth changes this session.**

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_038_milestone_1_write_path_tenancy.md`
     — the tenancy primitive contract 4A extends.
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §1.3 (why 7 roles) +
     §1.4 (the specific advisor-user link 4C will need) +
     §7 (why 4A is scoped this way).
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — the
     canonical role list.
   - `backend/dealer_ai/models.py::Salesperson` — the existing
     shape 4A extends with an optional `user` link.

2. **Implement in this order** (each step verifiable
   independently):

   1. **Add `UserDealershipRole` model** in `backend/dealer_ai/models.py`.
      Shape:
      - `user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name="memberships")`
      - `dealership = ForeignKey(Dealership, on_delete=CASCADE, related_name="memberships")`
      - `role = CharField(max_length=32, choices=ROLE_CHOICES)`
      - `created_at`, `updated_at` timestamps
      - `Meta.unique_together = ("user", "dealership", "role")`
      - `Meta.ordering = ("user", "dealership", "role")`

      `ROLE_CHOICES` — the seven from `IMPLEMENTATION_ROADMAP.md`
      §Milestone 1: `dealer_owner`, `sales_manager`,
      `recon_manager`, `f_and_i_manager`, `collections`, `advisor`,
      `porter`. Keep the list in a module-level constant so
      subsequent increments import it without duplicating the
      string literals.

   2. **Extend `Salesperson`** with
      `user = OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL, related_name="salesperson")`.
      Nullable during backfill; 4C is the increment that requires
      the link to be present for authenticated advisor access.

   3. **Generate migration `0011_userdealershiprole_and_salesperson_user.py`**.
      Schema-only; no data migration in 4A (no existing users to
      backfill — Django `django.contrib.auth` is inert today per
      SESSION_037 handoff).

   4. **Register both in `backend/dealer_ai/admin.py`** so a superuser
      can create the first `dealer_owner` membership manually before
      4C ships (bootstrap path). Simple `ModelAdmin` — no custom
      forms.

   5. **Tests** in `backend/dealer_ai/tests/test_userdealershiprole.py`
      (new file). Cover:
      - Model round-trip (create → fetch by user + dealership).
      - `unique_together` enforcement.
      - `related_name="memberships"` reverse-accessor.
      - `Salesperson.user` link nullable + reverse-accessor
        `user.salesperson`.
      - Role choices contain exactly the seven canonical values.
      Test baseline: 1,322 → ≥ 1,327 (5+ new tests).

3. **Verify continuously.** After each of steps 1–5 run
   `python3 manage.py test dealer_ai` and confirm zero regressions.

4. **Verify the compatibility checklist** (§3 of the planning
   memo). Every pre-existing item must still verify true — 4A
   should be behavior-transparent to every existing surface.

5. **Preserve the franchise config path.** Env overrides
   (`DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
   `DEALER_AI_DEALER_NAME`) still work for single-tenant local dev.
   4A doesn't touch the resolver.

6. **Close the session** with:
   - Handoff at `docs/handoffs/SESSION_039_<slug>.md`.
   - `docs/CAPABILITY_MATRIX.md` update **not required** — the
     software's outward behavior is unchanged in 4A. Add a note
     under §7/§8 that the role vocabulary now exists in the
     schema only if useful for the next reader; otherwise skip.
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with the
     SESSION_040 = Increment 4B priority.

## Explicit non-goals for SESSION_039 (Increment 4A)

- ❌ Do NOT change `settings.py::REST_FRAMEWORK`. Auth defaults
  are 4B.
- ❌ Do NOT add `authentication_classes` or `permission_classes`
  to any view. Endpoint auth is 4C/4D.
- ❌ Do NOT create the `get_current_dealership(request)` resolver.
  That's 4B.
- ❌ Do NOT touch frontend code. Login UI is 4E.
- ❌ Do NOT backfill users / memberships automatically. There are
  no users to backfill; the first `dealer_owner` is created
  manually via Django admin before 4C ships.
- ❌ Do NOT introduce tenant-scoped uniqueness on `Salesperson.slug`,
  `Vehicle.stock_number`, or `DealerOnboardingProfile`. Those
  belong to the increment that first needs them (out of Milestone
  1 scope per §5).
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT create parallel docs. Update
  `MILESTONE_1_PLANNING.md` §7 only if implementation reveals a
  real deviation from the contract.

## NEXT TASK

Start SESSION_039 with the read-first list above, then implement
Increment 4A in the five-step sequence.

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
8. Most recent handoffs (`SESSION_038_*.md`, `SESSION_037_*.md`).
9. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_038)

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_ai/`. Migrations `0001`–`0010` applied. Default
  `Dealership` row exists (`slug='default'`,
  `name='Default Dealership'`). All six tenant FKs enforce NOT
  NULL. Write-path fallback via `pre_save` signal registered in
  `DealerAiConfig.ready`.
- **Backend (prod):** `vehicle-match-api.onrender.com` — NOT
  active. Milestone 1 does not require prod.
- **Frontend (local):** Vite on `:5173`. Unchanged since
  SESSION_038.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,322 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** — still does not exist.
- **Dev DB note (unchanged from SESSION_038 handoff):**
  `DealerOnboardingProfile` count = 0. Visit
  `/dealer-ai-onboarding` and save once to restore if the demo
  relies on a persisted profile.
