---
state: active
date: 2026-07-31
last_session_shipped: SESSION_036
next_session: SESSION_037
---

# Next session — SESSION_037 · Milestone 1 implementation (auth + tenancy)

> **Implementation begins here.** SESSION_035 shipped the
> Milestone 1 planning pass (`docs/roadmap/MILESTONE_1_PLANNING.md`)
> and reorganized the roadmap docs under `docs/roadmap/`.
> SESSION_036 shipped documentation governance
> (`docs/DOC_GOVERNANCE.md`) and updated CLAUDE.md + auto-memory
> so future sessions follow the rules without re-prompting.
>
> **SESSION_037 begins Milestone 1 code.**
>
> **All governance layers apply:**
> - `docs/PROJECT_RULES.md` — project-work rules (6 rules).
> - `docs/DOC_GOVERNANCE.md` — documentation rules.
> - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 — scope
>   boundary.
> - `docs/roadmap/MILESTONE_1_PLANNING.md` — acceptance contract
>   (the §3 compatibility checklist must verify true).

## What just shipped

- **SESSION_035** — Milestone 1 planning pass and roadmap reorg.
  Handoff at `docs/handoffs/SESSION_035_milestone_1_planning_and_roadmap_reorg.md`.
- **SESSION_036** — Documentation governance
  (`docs/DOC_GOVERNANCE.md`), CLAUDE.md governance section,
  auto-memory feedback entries. Handoff at
  `docs/handoffs/SESSION_036_doc_governance_and_repo_org.md`.

## What SESSION_037 should do

**Implement Milestone 1 as scoped in `docs/roadmap/MILESTONE_1_PLANNING.md`
and `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1.**

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/PROJECT_RULES.md`
   - `docs/DOC_GOVERNANCE.md`
   - `docs/roadmap/MILESTONE_1_PLANNING.md` (the acceptance
     contract — all five sections)
   - `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 1 +
     §Section 3

2. **Implement in the subsystem order in the planning memo (§1):**
   1. `Dealership` FK-carrier model + data migration (backfills
      existing rows to a default Dealership from
      `DEALER_AI_DEALER_NAME` / onboarding profile /
      `"Default Dealership"`).
   2. Real authentication using `django.contrib.auth` +
      DRF authentication/permission classes.
   3. Role-based permissions for the 7 roles named in the
      roadmap.
   4. Advisor-workspace slug-obscurity replaced by real auth.
   5. Frontend login page + `Authorization` header propagation.

3. **Verify against the compatibility checklist** (§3 of the
   planning memo) after each subsystem. Every item must remain
   true.

4. **Preserve the test baseline.** 1,300 pass, 1 skipped. Milestone
   1 should *add* tests, not remove any.

5. **Preserve the franchise config path.** Env overrides
   (`DEALER_AI_DEALER_TYPE`, `DEALER_AI_PRIMARY_MAKE`,
   `DEALER_AI_DEALER_NAME`) must continue to work for
   single-tenant local dev.

6. **Close the session** with:
   - A handoff at
     `docs/handoffs/SESSION_037_milestone_1_auth_and_tenancy.md`.
   - Update `CAPABILITY_MATRIX.md` §7 (advisor auth) and §8
     (branding/onboarding) to reflect the new auth model.
   - Update `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §2.7 to
     flip "Multi-tenancy" and "Real authentication" from `N` to
     `F`.
   - Flip `docs/roadmap/MILESTONE_1_PLANNING.md` frontmatter
     `status: planning` → `status: shipped` (per
     `DOC_GOVERNANCE.md` §7.3).
   - Overwrite this file (`00-START-NEXT-SESSION.md`) with
     SESSION_038 priority (should be Milestone 2 — investment
     ledger — assuming Milestone 1 completes cleanly).

## NEXT TASK

Start SESSION_037 with **Step 1** — the read-first list above.
Then implement Milestone 1 in the subsystem order.

**Explicit non-goals** (from `docs/roadmap/MILESTONE_1_PLANNING.md`
§5):

- ❌ Do NOT scope-creep into Milestone 2 (investment ledger).
- ❌ Do NOT introduce SSO / MFA / user-management UI beyond
  sign-in.
- ❌ Do NOT refactor shipped surfaces except where role scoping
  is directly required by Milestone 1.
- ❌ Do NOT bypass the 1,300-test baseline.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT delete the franchise config path or Freedom Ford
  demo assets.
- ❌ Do NOT do dep-major upgrades concurrent with feature work.
- ❌ Do NOT create parallel docs (per `DOC_GOVERNANCE.md` §7.2)
  — update authoritative docs instead.
- ❌ Do NOT rewrite historical handoffs (per `DOC_GOVERNANCE.md`
  §6).

---

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md` — project-work governance.
2. `docs/DOC_GOVERNANCE.md` — documentation governance.
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` — implementation
   contract.
4. `docs/roadmap/MILESTONE_1_PLANNING.md` — Milestone 1
   acceptance contract.
5. `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference.
6. `docs/research/*_MAPPING.md` + `*_PIVOT.md` — business-truth
   corpus.
7. `docs/CAPABILITY_MATRIX.md` — what actually ships.
8. Most recent handoffs (`docs/handoffs/SESSION_035_*.md`,
   `SESSION_036_*.md`).
9. `git log --oneline -25`; `git show HEAD:<path>`.

Narrative docs are claims. Rules + research + code are facts.

---

## Operational state

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_kit/`. Migration `0006` applied.
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**. Milestone 1 does not require prod.
- **Frontend (local):** Vite on `:5173`.
  `/dealer-ai-onboarding` has 6 sections.
- **Frontend (prod):** **NONE**.
- **Test baseline:** 1,300 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/DEFERRED_IDEAS.md`** does not yet exist. Create it the
  first time an idea surfaces during Milestone 1 that doesn't
  fit in a milestone plan doc, per `PROJECT_RULES.md` §Discovery
  Rule.
