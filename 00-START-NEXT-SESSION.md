---
state: active
date: 2026-07-31
last_session_shipped: SESSION_034
next_session: SESSION_035
---

# Next session — SESSION_035 · Milestone 1 kick-off (auth + tenancy)

> **Implementation begins here.** SESSION_034 closed the
> implementation-transition-prep session by shipping the
> business domain map and the implementation roadmap.
> SESSION_035 begins Milestone 1 of that roadmap —
> **Multi-tenant + role-based access foundation** — the
> compliance and safety blocker for every subsequent
> data-sensitive milestone.
>
> **All six project rules apply.** Read
> `docs/PROJECT_RULES.md` first, then the roadmap's
> Milestone 1 section, then this doc's task list.

## What just shipped (SESSION_034)

- **`docs/BUSINESS_DOMAIN_MAP.md`** — 12-section highest-
  level business reference. Answers "how does an indie
  dealership actually operate end to end?" Zero software
  content; entirely business flow. Every claim traces to
  the SESSION_033 research corpus.
- **`docs/IMPLEMENTATION_ROADMAP.md`** — the implementation
  contract. Reconciliation summary (F/P/N status for every
  major capability), catalog of 10 numbered reusable
  primitives, 13 ordered milestones each with business
  objective + research citation + reusable primitives +
  gap + scope boundary, explicit deferrals, scope-
  discipline self-check.
- **`docs/handoffs/SESSION_034_business_domain_map_and_roadmap.md`**
  — full handoff with method, verifications, and preserved
  tensions.

## The six project rules — still authoritative

1. **Discovery Phase Complete** — no new capabilities
   without documented business problem in `docs/research/`.
2. **Discovery Rule** — new ideas map to documented problem
   AND current milestone; else defer (never discard).
3. **Research Before Design** — chain Business Reality →
   Research → Architecture → Implementation. No
   implementation bypasses the chain.
4. **Scope Discipline** — no feature creep, no "while we're
   here," ship small complete increments. Complete Milestone
   1 before touching Milestone 2 material.
5. **Preserve Existing Code** — first question is always
   "what already exists?" — reference `docs/CAPABILITY_MATRIX.md`
   and the roadmap's §3 primitives catalog.
6. **Build Around Operational Problems** — implementation
   driven by pain points, not by technology interest.

Full text in `docs/PROJECT_RULES.md`.

---

## What SESSION_035 should do

**Complete Milestone 1 as scoped in
`docs/IMPLEMENTATION_ROADMAP.md` §Milestone 1.** Do not add
scope from Milestones 2+ silently. The Milestone-1 scope
boundary is explicit:

- **In:** tenancy model (`Dealership` as FK-carrier — single
  row today, multi-row-ready tomorrow); real authentication
  (framework built-in is fine); role-based permissions with
  at minimum the roles named in research (`dealer_owner`,
  `sales_manager`, `recon_manager`, `f_and_i_manager`,
  `collections`, `advisor`, `porter`); replacement of the
  advisor-workspace slug-by-obscurity access with real auth.
- **Out:** user-facing settings / admin UI beyond the
  minimum needed to sign in; per-role UI polish (each
  subsequent milestone applies role scoping to its own
  surfaces); SSO; MFA (add later if research surfaces the
  need).

### Recommended step sequence

1. **Read first (in this order):**
   - `docs/PROJECT_RULES.md`
   - `docs/IMPLEMENTATION_ROADMAP.md` §Milestone 1 + §Section 3
     (reusable primitives — Milestone 1 will extend §3.9
     dealer_config and §3.10 onboarding profile)
   - `docs/BUSINESS_DOMAIN_MAP.md` §7 (responsibility flow —
     the compliance context for Milestone 1)
   - `docs/CAPABILITY_MATRIX.md` §7 (advisor slug-obscurity —
     the specific auth debt Milestone 1 resolves)
   - `docs/research/FINANCE_DEPARTMENT_MAPPING.md` §compliance
     (the "most sensitive document in the building" framing)
   - `docs/research/BHPH_OPERATIONS_MAPPING.md` §compliance
     (FDCPA / TCPA / GLBA / FCRA / state repo law surface)
   - `docs/research/VEHICLE_CENTRIC_PIVOT.md` §"Technical
     debt to pay down FIRST" items 1 and 2

2. **Design under Research Before Design.** Before writing
   any model or endpoint, cite the specific research doc(s)
   that motivate each decision. Small design memo at the
   top of the session is fine; a comprehensive architectural
   doc is out of scope.

3. **Implement Milestone 1 as small commits.** Discrete
   commit per subsystem (tenancy → auth → permissions →
   advisor-workspace slug replacement). Bisectable if a
   test breaks.

4. **Preserve the test baseline.** 1300 pass, 1 skipped.
   Every commit must keep it green. Milestone 1 is expected
   to *add* tests (auth, permission, tenancy) without
   removing any.

5. **Preserve the franchise config path.** Multi-tenancy
   must not break the singleton-onboarding-profile fallback
   for single-tenant local dev with `DEALER_AI_*` env
   overrides.

6. **Close the session** with a handoff at
   `docs/handoffs/SESSION_035_milestone_1_auth_and_tenancy.md`
   and overwrite this file with SESSION_036 priority (which
   should be Milestone 2 — investment ledger — assuming
   Milestone 1 completes cleanly).

## NEXT TASK

Start SESSION_035 with **Step 1** — the read-first list
above. Then produce a small design memo tying each Milestone-1
subsystem decision to a specific research citation. Then begin
implementation in small commits.

**Explicit non-goals:**

- ❌ Do NOT scope-creep into Milestone 2 (investment ledger)
  because "we might as well add the model now."
- ❌ Do NOT introduce SSO / MFA / user-management UI beyond
  the minimum required to sign in.
- ❌ Do NOT refactor existing shipped surfaces
  (leads pipeline, chat safety stack, ad-copy generator)
  except where role scoping is directly required.
- ❌ Do NOT bypass the 1300-test baseline. Any failing test
  is a blocker.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.
- ❌ Do NOT delete the franchise config path or the Freedom
  Ford demo assets.
- ❌ Do NOT commit changes concurrent with a dep-major
  upgrade.

---

## Guardrails carried forward

**From SESSION_030+031 (pivot):**

- ❌ Do NOT delete the franchise config path.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Freedom
  Ford" / Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts.
- ❌ Do NOT delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`
  or `public/sams-freedom-ford-logo.jpg`.
- ❌ Do NOT do dep-major upgrades concurrent with feature
  work.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

**From SESSION_033 (project rules):**

- ❌ Do NOT introduce new product capabilities that don't
  trace to `docs/research/`.
- ❌ Do NOT bypass the Business Reality → Research →
  Architecture → Implementation chain.
- ❌ Do NOT expand milestone scope silently — capture as
  deferred and continue with the stated milestone.
- ❌ Do NOT build parallel implementations of existing
  capability without cited justification.
- ❌ Do NOT drive implementation from technology interest —
  drive it from documented operational pain points.
- ❌ Do NOT reopen discovery except with explicit user
  approval when a critical implementation gap is identified.

**Added by SESSION_034 (roadmap adoption):**

- ❌ Do NOT jump ahead in the milestone sequence. Milestone
  N+1 does not start until Milestone N is complete.
- ❌ Do NOT rebuild any capability catalogued in
  `docs/IMPLEMENTATION_ROADMAP.md` §3 primitives without
  cited justification for why the existing primitive does
  not serve the business need.
- ❌ Do NOT reshape the reconciliation summary
  (`IMPLEMENTATION_ROADMAP.md` §2) without regenerating
  from the current codebase — it is a point-in-time
  snapshot.

---

## Agent launch prompt for SESSION_035

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_035 on the Dealer AI Kit.

SESSION_034 shipped the business domain map
(docs/BUSINESS_DOMAIN_MAP.md) and the implementation roadmap
(docs/IMPLEMENTATION_ROADMAP.md). This session begins the first
milestone: Multi-tenant + role-based access foundation.

Read first, in this order:
- context-kit orient
- docs/PROJECT_RULES.md (all six rules)
- 00-START-NEXT-SESSION.md (this file)
- docs/IMPLEMENTATION_ROADMAP.md §Milestone 1 and §Section 3
- docs/BUSINESS_DOMAIN_MAP.md §7 (responsibility flow)
- docs/CAPABILITY_MATRIX.md §7 (advisor slug-obscurity note)
- docs/research/FINANCE_DEPARTMENT_MAPPING.md §compliance
- docs/research/BHPH_OPERATIONS_MAPPING.md §compliance
- docs/research/VEHICLE_CENTRIC_PIVOT.md §"Technical debt to
  pay down FIRST" items 1-2

Deliverables for this session (in order):
1. A small design memo tying each Milestone-1 subsystem
   decision (tenancy → auth → roles → advisor-slug replacement)
   to a specific research citation (Research Before Design chain).
2. Milestone 1 implementation in discrete commits per subsystem.
3. Test additions covering the new auth + permission + tenancy
   surface; test baseline 1300 pass must remain green.
4. Session handoff at
   docs/handoffs/SESSION_035_milestone_1_auth_and_tenancy.md
   and overwrite 00-START-NEXT-SESSION.md for SESSION_036.

Milestone 1 scope boundary (from IMPLEMENTATION_ROADMAP.md):
- IN: Dealership FK-carrier tenancy model; real auth
  (framework built-in fine); role-based permissions for at
  minimum: dealer_owner, sales_manager, recon_manager,
  f_and_i_manager, collections, advisor, porter; advisor
  workspace slug-by-obscurity replaced by real auth.
- OUT: user-facing admin UI beyond sign-in minimum;
  per-role UI polish; SSO; MFA.

Local dev (unchanged):
- LLM = OpenAI gpt-5-mini (API key in repo-root .env).
- Django on :8001, Vite on :5173.
- Backend baseline: python3 manage.py test dealer_ai → 1300
  pass, 1 skipped.

Do NOT:
- Scope-creep into Milestone 2 (investment ledger).
- Introduce SSO, MFA, or user-management UI beyond
  sign-in.
- Refactor shipped surfaces (leads pipeline, chat safety
  stack, ad-copy) except where role scoping is directly
  required by Milestone 1.
- Bypass the 1300-test baseline.
- Delete the franchise config path.
- Bypass any of the six project rules in docs/PROJECT_RULES.md.
```

---

## Operational state carried from SESSION_034

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_kit/`. Migration `0006` applied.
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**. Milestone 1 does not require prod deployment;
  Milestone 2+ arguably do (per capability matrix §honest
  gaps).
- **Frontend (local):** Vite on `:5173`.
  `/dealer-ai-onboarding` has 6 sections.
- **Frontend (prod):** **NONE**.
- **Test baseline:** 1300 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.
- **`docs/DEFERRED_IDEAS.md`** does not yet exist. Create
  it the first time an idea surfaces that doesn't fit in a
  milestone plan doc, per `docs/PROJECT_RULES.md` §Discovery
  Rule.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md` — governance rules.
2. `docs/IMPLEMENTATION_ROADMAP.md` — implementation
   contract.
3. `docs/BUSINESS_DOMAIN_MAP.md` — business-shape reference.
4. `docs/research/*_MAPPING.md` + `*_PIVOT.md` — business-
   truth corpus.
5. `docs/CAPABILITY_MATRIX.md` — what actually ships.
6. `docs/handoffs/SESSION_034_*.md` — most recent handoff.
7. `git log --oneline -25` (what actually shipped).
8. `git show HEAD:<path>` (current source).

Narrative docs are claims. Research + code + rules are facts.
