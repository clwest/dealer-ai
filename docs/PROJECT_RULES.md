---
title: "Dealer AI Kit — Project Rules"
status: authoritative
type: governance
generated: 2026-07-31
adopted_at_commit: ff0e986
supersedes: none
applies_to:
  - All future implementation sessions
  - All AI agent sessions (Claude Code, other agents)
  - All human contributors
---

# Dealer AI Kit — Project Rules

> **What this is.** Durable governance rules for the project.
> Adopted 2026-07-31 at the close of the discovery phase.
> Every implementation session — human or AI — must honor
> these rules. They are the operating constraints under which
> all future work happens.
>
> **Why this exists.** Discovery produced a research corpus
> under `docs/research/` that describes how an independent
> used-car dealership actually operates. Implementation must
> now be disciplined by that corpus, not by whatever seems
> interesting or technically appealing in the moment. These
> rules preserve that discipline.
>
> **Precedence.** These rules override individual session
> preferences, technical inclinations, and "while we're here"
> temptations. When these rules conflict with a proposed
> approach, the rules win — or the user must consciously
> approve an exception.

---

## Discovery Phase Complete

The discovery phase is complete.

From this point forward, no new product capabilities should
be introduced unless they solve a problem documented within
the research corpus.

Future implementation must be grounded in documented
operational reality.

**The research corpus is now considered the primary source of
business truth.**

The research corpus consists of:

- `docs/research/FINANCE_DEPARTMENT_MAPPING.md`
- `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
- `docs/research/SALES_DEPARTMENT_MAPPING.md`
- `docs/research/INVENTORY_ACQUISITION_MAPPING.md`
- `docs/research/RECON_MAPPING.md`
- `docs/research/BHPH_OPERATIONS_MAPPING.md`
- `docs/research/VEHICLE_CENTRIC_PIVOT.md` (architectural plan)
- `docs/research/INDEPENDENT_DEALER_PIVOT.md` (persona /
  scope plan)

Additional research documents may be added in the future if
implementation surfaces a critical gap that cannot be
resolved without deeper business-domain investigation. Such
additions require explicit user approval and should reference
the specific gap that motivates them.

---

## Discovery Rule

During implementation, new ideas are not implemented
immediately.

Every new idea must answer two questions:

1. **Which documented business problem does this solve?**
2. **Is solving that problem required to complete the
   current implementation milestone?**

If either answer is **No**, the idea is **recorded for future
consideration** and implementation continues without
interruption.

**Ideas are never discarded.** They are deferred until the
appropriate milestone.

### Where deferred ideas live

- **Session-scoped deferrals:** captured in the current
  session's handoff doc under a "Deferred to future
  milestones" section.
- **Longer-term deferrals:** added to the appropriate
  milestone plan doc or to a running `docs/DEFERRED_IDEAS.md`
  index (create when needed).
- **Cross-department ideas:** if the idea reveals a research
  gap, note it in the appropriate research doc's Deferred
  Ideas section and flag whether new research is warranted.

### The point of this rule

Deferral is not rejection. Deferral is discipline. A great
idea implemented at the wrong milestone breaks the milestone
and often the idea. A great idea deferred to its right
moment ships cleanly.

---

## Research Before Design

Future architecture decisions must reference one or more
research documents.

Future implementation decisions must reference one or more
architecture decisions.

**Maintain the chain:**

```
Business Reality
      ↓
Research (docs/research/*_MAPPING.md)
      ↓
Architecture (docs/research/*_PIVOT.md or similar)
      ↓
Implementation (code + tests + handoff)
```

**No implementation should bypass this chain.**

### What this means in practice

- Before writing a Django model, cite the research doc(s) it
  serves.
- Before designing an API endpoint, cite the architecture
  decision that motivates it, which in turn cites research.
- Before adding a UI surface, cite the operational pain point
  or decision it addresses.
- Before adding a new dependency, cite what the addition
  enables in the chain.

### What this doesn't mean

- Not every code change needs a formal reference chain. Bug
  fixes, refactors, and small quality improvements to
  existing capability follow standard engineering discipline.
- New *capabilities* must follow the chain. New *fixes* to
  existing capabilities do not.

---

## Scope Discipline

- **Avoid feature creep.**
- **Avoid "while we're here" development.**
- **Avoid expanding milestones because related work exists.**

Complete the current milestone before introducing additional
capabilities.

**Favor small, complete, working increments over large
partially-completed systems.**

### Practical guidance

- If a milestone is defined as "add capability X," complete
  X. Do not add Y and Z because they seem convenient.
- If you notice a related improvement opportunity during
  implementation, capture it as a deferred idea (per the
  Discovery Rule) and continue with X.
- If the current milestone reveals that X cannot be completed
  without also completing Y, stop and escalate — do not
  silently expand scope. The user decides whether the
  milestone changes or the plan does.
- A working increment that ships and is used beats a large
  architectural investment that doesn't ship.

---

## Preserve Existing Code

The Dealer AI Kit is not a greenfield project.

Existing capabilities should be reused whenever practical.

Future implementation should begin by reconciling the research
corpus against the existing codebase.

**The first question should always be: "What already exists
that satisfies this business requirement?"** — before creating
anything new.

### What already exists (as of session close 2026-07-31)

Documented in `docs/CAPABILITY_MATRIX.md`:

- 16-stage guard/scrub pipeline (pre-LLM + post-LLM), backed
  by 1,300 tests.
- Deterministic backend math (payment engine, budget
  classification).
- Full sales-pipeline surface (leads, assignments, advisor
  workspaces, coaching mode, handoff packets, follow-up
  drafts, ad-copy generation).
- Runtime dealer-identity templating and 8-field
  shape-of-business persistence.
- Multi-provider LLM abstraction (OpenAI, Ollama).
- CSV inventory import with per-source upsert discipline.
- Onboarding form + `useDealerProfile()` frontend hook.

### The reconciliation cadence

Before implementing anything from the research corpus,
reconcile against `docs/CAPABILITY_MATRIX.md`:

- Does this business requirement map to existing capability?
- If yes: extend or refine the existing capability. Do not
  build a parallel implementation.
- If partially: identify the gap; implement only the gap.
- If no: proceed with new implementation, but reference the
  research doc(s) that motivate it.

### Anti-patterns

- Rewriting scrubs, payment math, or the guard pipeline
  without a specific research-documented reason.
- Creating a second inventory import path when the CSV
  importer already handles upsert-by-stock-number.
- Reimplementing dealer identity resolution outside of
  `services/dealer_config.py`.
- Bypassing the LLM safety stack for new drafted artifacts.

---

## Build Around Operational Problems

**Implementation should never be driven by technology.**

**Implementation should always be driven by operational pain
points identified during research.**

Technology is a tool.

Operational improvement is the objective.

### What this means

- The question "should we adopt X framework / pattern / tool"
  is not the right first question.
- The right first question is: "Which operational pain point
  are we addressing, and what evidence do we have that this
  technology solves it?"
- Elegance, novelty, and technical interest are not
  justifications. Operational impact is.

### Signal it correctly

When proposing implementation work:

- **Good framing:** "F&I is spending 30 minutes per deal
  re-entering credit-app data into lender portals
  (documented in FINANCE §7.1). Building a shared
  customer-data submission workflow would eliminate that."
- **Bad framing:** "We should add a workflow orchestration
  library because it would give us clean job semantics."

If the framing sounds like the "bad framing," pause and
locate the operational pain point that would justify it. If
you can't find one, defer the work.

---

## How to use this document

**For AI agents starting a session:** read this document
during orientation, alongside `CLAUDE.md` and the
context-kit orient output. These rules constrain every
subsequent decision in the session. When asked to do
something that would violate a rule, push back and cite the
specific rule. When in doubt, ask the user for explicit
approval to proceed against a rule.

**For human contributors:** review this document before
starting implementation work. If a proposed change would
violate a rule, either revise the change or make the
exception explicit and documented.

**For code reviewers:** flag PRs that appear to bypass the
research → architecture → implementation chain, expand scope
beyond the stated milestone, or reintroduce
already-existing capabilities.

**Update discipline.** These rules can be updated when:
- Discovery is formally reopened for a specific reason.
- A rule proves counterproductive in practice (with specific
  evidence).
- New rules are added because the project's shape has
  changed.

Do **not** update these rules to accommodate a specific
in-progress session's convenience. If a rule is inconvenient
for a specific session, either the session's approach or
the rule is wrong — investigate which, don't paper over the
conflict.

---

## Rule provenance

These rules were adopted at the end of the discovery phase
(SESSION_033, commit `ff0e986`, date 2026-07-31) as the
formal transition from research to implementation. The
user's directive is captured in the SESSION_033 handoff
doc under `docs/handoffs/`.

The rules apply to all sessions from SESSION_034 forward
until formally amended.

---

## Related documents

- `CLAUDE.md` — session entry point for AI agents; references
  these rules.
- `docs/CAPABILITY_MATRIX.md` — inventory of what already
  exists in the codebase; primary reference for "what
  already exists that satisfies this business requirement?"
- `docs/research/` — the research corpus these rules
  reference as the primary source of business truth.
- `docs/handoffs/SESSION_033_*.md` — the session at which
  these rules were adopted.
- `00-START-NEXT-SESSION.md` — the next session's priority,
  which will operate under these rules.

---

*End of Project Rules.*
