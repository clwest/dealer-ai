---
date: 2026-07-31
title: SESSION_033 — discovery corpus + project rules + transition to implementation
type: discovery-completion + governance-adoption
test_baseline: 1300 pass, 1 skipped (unchanged — docs-only session)
persona: Copper Canyon Auto (Yuma, AZ)
picks_up_from: SESSION_032_indie_onboarding_migration.md
migration: none (docs-only)
research_commit: ff0e986
rules_commit: TBD  # this commit
---

# Session handoff — discovery corpus + project rules

SESSION_033 closed the discovery phase. The session started as a
vehicle-centric architecture research session and expanded into
a full multi-department operational research corpus, followed by
a formal governance adoption transitioning the project from
"understanding the business" to "building the software."

**Test baseline: 1300 pass, 1 skipped, 0 fails, zero regressions
(unchanged — docs-only session).**

## What shipped

### Research corpus (commit `ff0e986`)

Six operator-voice department mapping docs under `docs/research/`,
each structured identically: purpose / scope / voice / core
philosophy → operational sections → pain points → operational
decisions → automation opportunities → cross-department
dependencies → deferred ideas → how-to-use → glossary → related
research.

| Doc | Lines | Focus |
| --- | --- | --- |
| `FINANCE_DEPARTMENT_MAPPING.md` | 2,462 | F&I workflow, lender relationships, deal structuring, funding, compliance |
| `ACCOUNTING_DEPARTMENT_MAPPING.md` | 2,887 | COA spine, vehicle + deal accounting, A/P + A/R, titles, bank rec, month-end, compliance |
| `SALES_DEPARTMENT_MAPPING.md` | 2,411 | Indie sales landscape, customer acquisition sources, road to sale, CRM/follow-up, inventory knowledge, reputation |
| `INVENTORY_ACQUISITION_MAPPING.md` | 2,189 | Auctions, trades, wholesale, buying discipline, floor plan, pricing, aging, disposition |
| `RECON_MAPPING.md` | 2,081 | Three-model recon spectrum, condition assessment, work planning, vendor management, QC, front-line-ready |
| `BHPH_OPERATIONS_MAPPING.md` | 2,222 | Dealer-as-lender model, customer lifecycle, payments, collections, portfolio management, repossession |

**Total: 14,252 lines of new research** committed as a single
unit (`ff0e986`). All six docs identify the operational pain
points and recurring decisions that future automation must
address, while explicitly listing AI anti-patterns (never
invent condition-report findings, never make repo decisions,
never communicate with customers without human review, etc.).

Consistency pass applied before commit: renamed cross-references
(`INVENTORY_DEPARTMENT_MAPPING` → `INVENTORY_ACQUISITION_MAPPING`,
`RECON_DEPARTMENT_MAPPING` → `RECON_MAPPING`) and standardized
the "Deferred research topics" block across all six docs.

The two pivot docs (`VEHICLE_CENTRIC_PIVOT.md`,
`INDEPENDENT_DEALER_PIVOT.md`) were already committed in prior
sessions and were also relocated to `docs/research/` during
this session (in an earlier commit within this session,
`253665b`).

### Project rules (this commit)

- **`docs/PROJECT_RULES.md`** — authoritative governance doc
  containing all six rules with framing, exceptions, and
  anti-patterns.
- **`CLAUDE.md`** updated with a hand-written "Project rules
  (hand-written; load before implementation)" section
  summarizing the six rules and pointing at the full doc.
- **Auto-memory** populated at
  `~/.claude/projects/-Users-donkeyking-development-freedom-ford/memory/`
  with 7 feedback / project / reference entries and a
  `MEMORY.md` index so every future AI session picks up the
  rules automatically.

### Session-close artifacts (this commit)

- **This handoff** (`docs/handoffs/SESSION_033_discovery_corpus_and_project_rules.md`).
- **`00-START-NEXT-SESSION.md`** overwritten with SESSION_034
  priority (implementation transition prep).

## The six project rules — one-line summary

1. **Discovery Phase Complete** — no new capabilities without
   documented business problem in `docs/research/`.
2. **Discovery Rule** — new ideas must map to documented
   problem AND current milestone; else defer (never discard).
3. **Research Before Design** — chain: Business Reality →
   Research → Architecture → Implementation.
4. **Scope Discipline** — no feature creep, no "while we're
   here," ship small complete increments.
5. **Preserve Existing Code** — first question is always
   "what already exists?" — reference `docs/CAPABILITY_MATRIX.md`.
6. **Build Around Operational Problems** — implementation
   driven by pain points, not by technology interest.

Full rules in `docs/PROJECT_RULES.md`.

## Timeline of this session

Long session with multiple phases:

1. **Vehicle-centric architecture session** — produced initial
   `VEHICLE_CENTRIC_PIVOT.md` as a full architectural plan
   (models, phases, weeks).
2. **Docs relocation** — moved architectural docs to
   `docs/platform/` then to `docs/research/` (with
   `samsfreedomford/` audit deletion). Committed as
   `253665b`.
3. **F&I mapping** — established the department-mapping
   pattern.
4. **Accounting mapping** — extended the pattern to
   accounting operations.
5. **Sales mapping** — extended to customer acquisition +
   sales.
6. **Pivot doc reconsideration** — recognized that
   `VEHICLE_CENTRIC_PIVOT.md` mixed genres (business reframe
   + implementation plan); decided to write vehicle-side
   business mappings as companions rather than rewrite the
   pivot.
7. **Inventory & Acquisition mapping** — vehicle-side upstream.
8. **Recon mapping** — vehicle-side downstream.
9. **BHPH Operations mapping** — the after-the-sale business.
10. **Consistency pass, commit, push** — corpus committed as
    `ff0e986`.
11. **Governance adoption** — user directed discovery closed;
    project rules adopted; transition to implementation
    formalized.

## Design decisions locked

- **Research corpus is source of truth** for business
  behavior. Any implementation must trace to a research doc.
- **Two-genre distinction preserved:** *mapping* docs
  (business truth, operator voice) vs *pivot* docs
  (architectural plan). `VEHICLE_CENTRIC_PIVOT.md` retained
  as-is rather than rewritten in mapping form.
- **Uniform mapping structure** across all six department
  docs: purpose → operations → pain points → decisions →
  automation opportunities → cross-dept dependencies →
  deferred ideas → how-to-use → glossary → related. Future
  mapping additions should honor this shape.
- **AI anti-patterns explicit** in every mapping doc's
  "How to use" section. Anti-patterns cover: inventing
  findings, autonomous authorization decisions, unreviewed
  customer communication, bypassing scrubs.
- **Deferred research topics identified but not committed
  to.** Titles, Marketing, Compliance, Service, Payroll,
  Customer/CRM, Vendor Management — may be revisited if
  implementation surfaces a critical gap.

## What SESSION_034 should do (per user direction)

**Do NOT begin implementation.** Instead, prepare for
implementation by:

1. Reviewing the completed research corpus.
2. Producing a high-level **business domain map** connecting
   Inventory, Recon, Sales, Finance, and Accounting (i.e., a
   single diagram or structured doc showing how the
   departments' operational events connect end-to-end).
3. Comparing the business domain against the current Dealer
   AI Kit implementation (reference `docs/CAPABILITY_MATRIX.md`).
4. Producing an **implementation roadmap** that maps
   documented business requirements to existing code,
   identifies reusable components, identifies gaps, and
   prioritizes implementation work.

No additional discovery unless a critical gap surfaces
during this preparation.

**Suggested deliverable name:** `docs/IMPLEMENTATION_ROADMAP.md`
(new file) plus possibly `docs/BUSINESS_DOMAIN_MAP.md` (new
file) — TBD by SESSION_034.

## Guardrails carried forward (unchanged)

- ❌ Do NOT delete the franchise config path.
- ❌ Do NOT reintroduce hardcoded "Sam Wampler" / "Freedom
  Ford" / Ford-model strings in default paths.
- ❌ Do NOT change chat behavior contracts. 1300-test
  baseline must stay green.
- ❌ Do NOT delete `docs/demo/FREEDOM_FORD_DEMO_SCRIPT.md`
  or `public/sams-freedom-ford-logo.jpg`.
- ❌ Do NOT do dep-major upgrades concurrent with feature
  work.
- ❌ Do NOT commit any real `OPENAI_API_KEY`.

## New guardrails adopted this session

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
  approval when a critical implementation gap is
  identified.

## Anchors that win on conflict

If anything here disagrees with reality:

1. `docs/PROJECT_RULES.md` — the governance rules.
2. `docs/research/*_MAPPING.md` + `*_PIVOT.md` — the
   business-truth corpus.
3. `docs/CAPABILITY_MATRIX.md` — what actually ships.
4. `git log --oneline -25` (what actually shipped).
5. `git show HEAD:<path>` (current source).

Narrative docs are claims. Code and handoffs are facts.

---

*End of SESSION_033 handoff.*
