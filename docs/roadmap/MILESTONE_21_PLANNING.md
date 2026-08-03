---
title: "Milestone 21 — (target selection deferred to M21.0)"
status: draft
type: planning-memo
generated: 2026-08-02
generated_at_session: SESSION_165 (skeleton)
milestone: 21
milestone_name: "(pending — locked at M21.0 open)"
sources:
  - docs/PROJECT_RULES.md
  - docs/DOC_GOVERNANCE.md
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md
  - docs/roadmap/AUTHENTICATION_MODEL.md
  - docs/roadmap/MILESTONE_19_RETROSPECTIVE.md
  - docs/roadmap/MILESTONE_20_RETROSPECTIVE.md
---

# Milestone 21 — Planning skeleton (target TBD at M21.0)

Skeleton drafted at M20.5 close-out
(SESSION_165). This memo intentionally
does NOT lock a target; SESSION_166
(M21.0) presents the candidate list,
resolves §5.a with the user, and expands
the skeleton into a full active planning
memo per the M18 / M19 / M20 precedent.

## Standing rule

Per the M18 / M19 / M20 planning pattern:
at M21.0 open the target selection
proceeds by presenting the full candidate
list, recommending one option with
rationale grounded in operator pain
resolved by that candidate, and awaiting
user confirmation. Once selected,
§5.b–§5.h load-bearing planning decisions
get drafted with recommendations for
confirm-as-recommended at M21.0 open
(streak extension expected: 86 → 87
planning-time as-recommended M5.1 → M21.0
across twelve consecutive milestones).

## Candidate list

Compiled from `MILESTONE_20_RETROSPECTIVE.md`
§8 unblocks + §9 candidate list +
carry-forwards from M19 §9. **Priority
ranking happens at M21.0 with the full
brief in hand.**

### Carry-forward candidates (from M19 §9)

- **Candidate T** — process real
  tester feedback (M18.5 CSV
  export). Gated on Chris running
  tester sessions between M20
  close and M21.0 open.
- **Candidate U** — hosted-demo
  substrate (public self-serve
  signup). Gated on willingness to
  hand demo stores to operators
  Chris doesn't already know.
- **Candidate A** — return to
  accounting stream (M18
  retrospective §8's designated
  M20 slot; M20 diverged to
  Candidate J). **Recommendation
  strength elevated at M21.0**
  because three consecutive
  milestones (M18, M19, M20)
  diverging from the accounting
  designation risks ossifying the
  divergence. Multiple accounting
  sub-candidates listed in
  `MILESTONE_18_RETROSPECTIVE.md`
  §8 (period-close comparison
  view / audit, financial-reports
  substrate (P&L + balance sheet),
  CSV/PDF export of frozen
  snapshots, auto-freeze on
  schedule, reopen/unfreeze
  workflow, M10 chargeback GL
  reversal, NSF workflow,
  category-group-aware GL
  mapping, deposit/bank
  reconciliation, BhphFee entity,
  interest-accrual detector).
- **Candidate D** — demo-aware
  LLM router / cost caps (M18.1
  §0.a decision 1 deferral).
- **Candidate C** — F&I chargeback
  substrate (M18.2 §0.a decision
  1 deferral).
- **Candidate P** — onboarding UX
  polish (prospect intake UI,
  checklist progress bar,
  terminate-flow refinements,
  pilot-list filtering/search).
- **Candidate L** — first-live-
  pilot staging dry-run (codify
  the M19.5 dry-run against a
  real staging DB with a real
  pilot dealer).
- **Candidate M** — multi-
  operator support
  (`IsPlatformOperator`
  permission class). **Breaks the
  zero-drift streak with intent.**
  Gated on a second operator
  actually being introduced.

### New at M20 close (from M20 §8 + §9)

- **Candidate B — M12.8 BHPH
  collections write-side UI.**
  Surfaced by M20.4 §0.a decision
  1 (BHPH scope narrowing). Would
  ship: record PtP form, mark-
  broken / mark-kept action
  buttons on Promises card, log-
  contact form on Contacts card,
  initiate-repossession form on
  Repossessions card. Once
  shipped, M20.4 journey scope
  expands to cover the write side.
  Operator pain: today the M12
  write endpoints are only usable
  via curl / Postman / Django
  shell — collectors can't do
  their work through the UI.
- **Candidate D — dashboard
  testid hardening.** Add
  `data-testid` patterns across
  DealerOverview, DealerAdmin's
  SalesPipeline + Recent Leads
  table, LeadsPage's lead queue
  + LeadDetailPanel,
  LeadDetailModal, and the
  AssignmentDropdown. Enables
  future Playwright journey
  extensions to write clean
  assertions instead of leaning
  on brittle text/role selectors
  + class-signature modal scoping.
  Not urgent (M20.2/M20.3
  journeys work today); becomes
  urgent as component copy
  evolves.

**Note on candidate letter reuse.**
"Candidate D" is used above for both
demo-aware LLM router (from M19 §9)
AND dashboard testid hardening (from
M20 §8). The M21.0 memo expansion
will disambiguate — likely by
renaming the new one (proposal:
"Candidate G — dashboard testid
hardening") or by using descriptive
short names throughout M21+ per the
DOC_GOVERNANCE.md preference for
authoritative names over letters.

## What M21.0 must do

At SESSION_166 (or whenever M21.0
opens):

1. **Present the candidate list**
   above with a recommendation +
   rationale per candidate.
2. **Recommend a target** for §5.a
   selection. Ground the
   recommendation in:
   - Operator pain resolved.
   - Dependencies on already-shipped
     substrate.
   - Deferred items with re-entry
     paths.
   - Whether the candidate blocks
     future milestones or is
     blocked by them.
3. **Await user confirmation** or
   redirection to a different
   candidate.
4. **Once §5.a locks**, draft §5.b–
   §5.h load-bearing planning
   decisions with recommendations
   for confirm-as-recommended at
   M21.0 open. Streak 86 → 87
   expected.
5. **Expand this skeleton** into a
   full active planning memo
   analogous to
   `MILESTONE_18_PLANNING.md` /
   `MILESTONE_19_PLANNING.md` /
   `MILESTONE_20_PLANNING.md`.
   Frontmatter `status: draft` →
   `status: active`; `milestone_name`
   populated from §5.a.

## Non-goals for this skeleton

- ❌ Do NOT lock §5.a target at
  M20.5.
- ❌ Do NOT draft §5.b–§5.h
  recommendations at M20.5 —
  those live inside the full
  planning memo after §5.a
  locks.
- ❌ Do NOT commit to any
  candidate's scope estimate at
  M20.5.
- ❌ Do NOT rewrite the candidate
  list order to imply priority
  — that's the M21.0 open
  exercise.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 (M20 unblocks) + §9 (standing
   question)
6. `docs/roadmap/MILESTONE_19_RETROSPECTIVE.md`
   §9 (M19 candidate list — still
   valid for the seven candidates
   M20 didn't pick)
7. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 (accounting-slot designation
   preserved as elevated M21
   recommendation)
8. `docs/CAPABILITY_MATRIX.md`
   §7u (M20 shipped surface)
