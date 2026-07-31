---
state: active
date: 2026-07-31
last_session_shipped: SESSION_033
next_session: SESSION_034
---

# Next session — SESSION_034 · implementation transition prep

> **Discovery phase is complete.** SESSION_033 closed discovery
> with a six-department research corpus (~14.2k lines) and
> formal governance rules. SESSION_034 does NOT begin
> implementation — it prepares for implementation by
> reconciling the research corpus against the existing
> codebase and producing a prioritized roadmap.
>
> **Project rules apply from this session forward.** Read
> `docs/PROJECT_RULES.md` before doing anything else.

## What just shipped (SESSION_033)

- **6 research mapping docs** committed at `ff0e986` covering
  F&I, Accounting, Sales, Inventory/Acquisition, Recon, BHPH
  Operations (~14,252 lines total).
- **`docs/PROJECT_RULES.md`** — authoritative governance doc
  with 6 rules: Discovery Phase Complete, Discovery Rule,
  Research Before Design, Scope Discipline, Preserve Existing
  Code, Build Around Operational Problems.
- **`CLAUDE.md`** updated with a hand-written "Project rules"
  section summarizing the rules and pointing at the full doc.
- **Auto-memory** populated with the six rules as feedback /
  project / reference memories, so every future AI session
  picks them up automatically.
- **`docs/handoffs/SESSION_033_discovery_corpus_and_project_rules.md`**
  — full handoff with timeline and locked design decisions.

## The six project rules — memorize before working

1. **Discovery Phase Complete** — no new capabilities without
   documented business problem in `docs/research/`.
2. **Discovery Rule** — new ideas must map to documented
   problem AND current milestone; else defer (never discard).
3. **Research Before Design** — chain: Business Reality →
   Research → Architecture → Implementation. No implementation
   should bypass this chain.
4. **Scope Discipline** — no feature creep, no "while we're
   here," ship small complete increments.
5. **Preserve Existing Code** — first question is always
   "what already exists?" — reference `docs/CAPABILITY_MATRIX.md`.
6. **Build Around Operational Problems** — implementation
   driven by pain points, not by technology interest.

Full text and examples in `docs/PROJECT_RULES.md`.

## What SESSION_034 should do

**Not implementation. Preparation for implementation.**

### Step 1 — Review the completed research corpus

Read (or at least skim) the six mapping docs + two pivot docs
in `docs/research/`. Understand the business reality end to
end. Note the "Pain Points" and "Operational Decisions"
sections — these are the drivers of implementation priorities.

### Step 2 — Produce a business domain map

Deliverable: a structured doc (proposed name
`docs/BUSINESS_DOMAIN_MAP.md`) showing how the departments
connect operationally. At minimum:

- The vehicle's journey end-to-end: acquisition → recon →
  front-line → sold → funded → (BHPH: portfolio →
  payoff-or-repo).
- The customer's journey: prospect → visit → deal → funded →
  post-sale → repeat.
- Cross-department data flows (which department's outputs
  feed which department's inputs).
- Where automation opportunities from the mappings cluster.

Format: primarily text-based, structured; diagrams optional
(if diagrams are added, note the source and update discipline).

### Step 3 — Compare business domain against existing code

Deliverable: an honest reconciliation of the domain map
against `docs/CAPABILITY_MATRIX.md`. For each meaningful
capability in the domain map, note:

- **Fully implemented** — capability exists in the code today.
- **Partially implemented** — capability exists but doesn't
  fully satisfy the documented business need.
- **Not implemented** — capability doesn't exist and would
  need to be built.
- **Reusable primitives** — existing code that could be
  extended rather than duplicated.

### Step 4 — Produce implementation roadmap

Deliverable: `docs/IMPLEMENTATION_ROADMAP.md` (new file). At
minimum:

- Prioritized list of implementation milestones.
- Each milestone traced to the research doc(s) that motivate
  it (Research Before Design chain).
- Each milestone's scope explicitly bounded (Scope Discipline
  rule).
- Each milestone identifies existing code to reuse (Preserve
  Existing Code rule).
- Each milestone identifies the operational pain point it
  resolves (Build Around Operational Problems rule).
- Suggested ordering with justification.

**No implementation code changes in SESSION_034.** Any code
change discovered as necessary during roadmap production
should be captured as a milestone entry, not written.

## NEXT TASK

Start SESSION_034 with **Step 1** — review the research
corpus. Do not skip. The subsequent steps depend on the
mental model formed in Step 1.

**Explicit non-goals:**

- ❌ Do NOT begin implementation.
- ❌ Do NOT introduce new research topics (discovery is
  closed).
- ❌ Do NOT design specific Django models, API endpoints, or
  UI layouts as part of the roadmap. The roadmap identifies
  *what* and *why*; specific designs come during the actual
  implementation of each milestone.
- ❌ Do NOT expand the roadmap into a comprehensive
  architectural document. Milestones should be scoped to
  small complete increments per the Scope Discipline rule.

**Discovery is complete. The project now transitions from
understanding the business to building the software.**

---

## Guardrails carried forward

**From prior sessions:**

- ❌ Do NOT delete the franchise config path.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Freedom
  Ford" / Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts. 1300-test baseline
  must stay green.
- ❌ Do NOT delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md` or
  `public/sams-freedom-ford-logo.jpg`.
- ❌ Do NOT do dep-major upgrades concurrent with feature
  work.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

**Adopted SESSION_033 (project rules):**

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

---

## Agent launch prompt for SESSION_034

Paste into Claude Code / Cursor / any AI coding agent as the
session opener.

```text
You are picking up SESSION_034 on the Dealer AI Kit.

Discovery phase completed in SESSION_033 (commit ff0e986). A
six-department research corpus now lives in docs/research/,
along with two pivot docs. Formal project rules were adopted
in docs/PROJECT_RULES.md; CLAUDE.md summarizes them.

SESSION_034 does NOT begin implementation. Instead, prepare
for implementation.

Read first:
- context-kit orient
- docs/PROJECT_RULES.md (all six rules)
- 00-START-NEXT-SESSION.md
- docs/handoffs/SESSION_033_discovery_corpus_and_project_rules.md
- docs/research/ (six mapping docs + two pivot docs)
- docs/CAPABILITY_MATRIX.md

Deliverables for this session:
1. Business domain map (proposed
   docs/BUSINESS_DOMAIN_MAP.md) — how the departments connect
   end-to-end.
2. Domain-to-code reconciliation against
   docs/CAPABILITY_MATRIX.md — what's fully / partially / not
   implemented, and what existing primitives are reusable.
3. Implementation roadmap (docs/IMPLEMENTATION_ROADMAP.md) —
   prioritized milestones, each traced to research + scope-
   bounded + reusable-code-identified + pain-point-linked.

Local dev (unchanged):
- LLM = OpenAI gpt-5-mini (API key in repo-root .env).
- Django on :8001, Vite on :5173.
- Backend baseline: python3 manage.py test dealer_ai → 1300
  pass, 1 skipped.

Do NOT:
- Begin implementation code changes.
- Introduce new research topics (discovery closed).
- Design specific models / APIs / UI as part of the roadmap
  (roadmap identifies what+why; specific designs come later).
- Expand the roadmap into a comprehensive architectural
  document.
- Bypass any of the six project rules in docs/PROJECT_RULES.md.
```

---

## Operational state carried from SESSION_033

- **Backend (local):** Django on `:8001`. Package
  `backend/dealer_kit/`. Migration `0006` applied. LLM =
  OpenAI `gpt-5-mini` (repo-root `.env`).
- **Backend (prod):** `vehicle-match-api.onrender.com` — **NOT
  active**.
- **Frontend (local):** Vite on `:5173`.
  `/dealer-ai-onboarding` has 6 sections.
- **Frontend (prod):** **NONE**.
- **Test baseline:** 1300 pass, 1 skipped, 0 fail.
- **Env overrides for franchise config still work:**
  `DEALER_AI_DEALER_TYPE=franchise`,
  `DEALER_AI_PRIMARY_MAKE=<OEM>`,
  `DEALER_AI_DEALER_NAME=<name>`.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md` — governance rules.
2. `docs/research/*_MAPPING.md` + `*_PIVOT.md` — business-truth
   corpus.
3. `docs/CAPABILITY_MATRIX.md` — what actually ships.
4. `docs/handoffs/SESSION_033_*.md` — most recent handoff.
5. `git log --oneline -25` (what actually shipped).
6. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.
