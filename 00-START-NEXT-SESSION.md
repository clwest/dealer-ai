---
state: active
date: 2026-07-31
last_session_shipped: SESSION_037
next_session: SESSION_038
---

# Next session — SESSION_038 · Milestone 1 · Increment 3 (write-path tenancy + NOT NULL)

> **Milestone 1 is in progress.** SESSION_037 shipped Increments
> 1 and 2 (the `Dealership` model + nullable FKs on six
> tenant-carrying models + verified backfill of the default
> Dealership row). Handoff at
> `docs/handoffs/SESSION_037_milestone_1_tenancy_foundation.md`.
>
> **SESSION_038 continues Milestone 1 with Increment 3.**
>
> **All governance layers apply:**
>
> - `docs/PROJECT_RULES.md` — six project-work rules.
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 —
>   scope boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` — acceptance
>   contract (§3 compatibility checklist must still verify
>   true after Increment 3).

## What just shipped

- **SESSION_037 (this session)** — Milestone 1 Increments 1 & 2.
  Two commits (`36a4d74`, `0e7e710`). Test baseline moved from
  1,300 → 1,313. NOT NULL flip on the six new FKs was
  deferred from Increment 2 to Increment 3 (see the handoff's
  "Deviation from plan" section for rationale).
- **SESSION_036** — Documentation governance
  (`docs/DOC_GOVERNANCE.md`), CLAUDE.md governance section,
  auto-memory feedback entries. Handoff at
  `docs/handoffs/SESSION_036_doc_governance_and_repo_org.md`.

## What SESSION_038 should do — Increment 3

**Goal:** propagate tenancy through the write path so every
code path that creates a `Vehicle` / `Salesperson` /
`ChatSession` / `ChatMessage` / `CustomerLead` /
`DealerOnboardingProfile` sets `dealership=`, then flip all
six FKs to `NOT NULL`.

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/handoffs/SESSION_037_milestone_1_tenancy_foundation.md`
     — full context on what shipped and why NOT NULL was
     deferred.
   - `docs/roadmap/MILESTONE_1_PLANNING.md` §3.9 (resolver
     extension pattern) and §2 rows 1, 4, 5, 6, 7, 10 (the
     per-system impact table for the write-path callers).
   - `backend/dealer_ai/tests/test_dealership.py::
     TenancyFkAttachment.test_fk_is_nullable_in_this_increment`
     — this guard must be inverted (or removed) as part of
     the NOT NULL flip.

2. **Implement in this order** (each step verifiable
   independently):

   1. Introduce `backend/dealer_ai/services/tenancy.py::
      get_default_dealership()` — runtime lookup,
      cache-once, raises if missing. Import-safe (no
      top-level DB access).
   2. Extend `services/dealer_config.py`:
      `get_dealer_name()` and `get_dealer_profile()` gain an
      optional `dealership` argument; when omitted, resolve
      via `get_default_dealership()`. Env-override layer
      and Copper Canyon defaults preserved.
   3. Sweep write-path callers to pass `dealership=` on
      model creation (defaults-only — no request-context
      tenant resolution yet):
      - `services/inventory_import.py`
      - `services/chat_engine.py`
      - `services/lead_service.py`
      - `services/follow_up.py`
      - `services/handoff_service.py`
      - `views.py` (DealerOnboardingProfile upsert;
        Salesperson admin create if any)
   4. Add a shared test helper — a base `TestCase` mixin
      or `setUpTestData` pattern — that surfaces
      `self.default_dealership` and passes it into every
      model constructor. Sweep existing tests that construct
      the six tenant carriers.
   5. Generate migration `0010_dealership_fks_not_null.py`
      (Django will prompt about non-nullable; answer 2 =
      "handled manually" since the backfill in 0009 covered
      it).
   6. Invert the `test_fk_is_nullable_in_this_increment`
      guard into a `test_fk_is_now_not_null` assertion.

3. **Verify continuously.** After each of steps 1–6, run
   `python3 manage.py test dealer_ai` and confirm zero
   regressions. The final baseline should be ≥ 1,313 pass
   (Increment 3 is expected to *add* tests, not remove any).

4. **Verify the compatibility checklist** (§3 of the
   planning memo) after Increment 3 is complete. Every
   pre-existing item must still verify true.

5. **Preserve the franchise config path.** Env overrides
   (`DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
   `DEALER_AI_DEALER_NAME`) must continue to work for
   single-tenant local dev.

6. **Close the session** with:
   - Handoff at `docs/handoffs/SESSION_038_<slug>.md`.
   - Update `docs/CAPABILITY_MATRIX.md` only if
     Increment 3 shifts what the software *actually does*
     visibly (probably not — this is plumbing).
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     the SESSION_039 priority (Increment 4 — probably real
     authentication, per planning memo §1.2).

## Explicit non-goals for SESSION_038

- ❌ Do NOT introduce request-context tenant resolution
  (header / domain / authenticated-user). That's Increment 4+.
- ❌ Do NOT add endpoint auth / DRF authentication classes /
  permission classes. That's Increment 4.
- ❌ Do NOT introduce tenant-scoped unique constraints
  (`(dealership, stock_number)`, `(dealership, slug)`,
  `DealerOnboardingProfile` OneToOne). Those come with the
  increment that needs them.
- ❌ Do NOT touch the frontend.
- ❌ Do NOT touch the 16-stage safety pipeline.
- ❌ Do NOT delete the franchise config path or Freedom
  Ford demo assets.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT create parallel docs (per `DOC_GOVERNANCE.md`
  §7.2). Update `MILESTONE_1_PLANNING.md` only if
  implementation reveals a real deviation from the contract.

## NEXT TASK

Start SESSION_038 with the read-first list above, then
implement Increment 3 in the six-step sequence.

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/MILESTONE_1_PLANNING.md`
5. `docs/BUSINESS_DOMAIN_MAP.md`
6. `docs/research/*_MAPPING.md` + `*_PIVOT.md`
7. `docs/CAPABILITY_MATRIX.md`
8. Most recent handoffs (`SESSION_037_*.md`,
   `SESSION_036_*.md`).
9. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state (post-SESSION_037)

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_ai/`. Migrations `0001`–`0009` applied.
  Default `Dealership` row exists (`slug='default'`,
  `name='Default Dealership'`).
- **Backend (prod):** `vehicle-match-api.onrender.com` —
  NOT active. Milestone 1 does not require prod.
- **Frontend (local):** Vite on `:5173`. Unchanged this
  session; `/dealer-ai-onboarding` still has 6 sections.
- **Frontend (prod):** NONE.
- **Test baseline:** 1,313 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/roadmap/DEFERRED_IDEAS.md`** does not yet exist.
  Create it the first time an idea surfaces during
  Milestone 1 that doesn't fit inside an existing
  milestone plan doc.
