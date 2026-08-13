---
title: "SESSION_174 handoff — Milestone 22 · Increment 4 (M22.4 — CI hardening + retrospective + close-out)"
status: historical
type: handoff
date: 2026-08-03
session: 174
milestone: 22
milestone_status: shipped
milestone_name: "Accounting Operational Validation"
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_174 — Milestone 22 · Increment 4 (M22.4 — CI hardening + retrospective + close-out)

## What shipped

Close-out increment per the M18.6 /
M19.6 / M20.5 / M21.5 cadence.
Clean-DB full-suite dry-run
verified; CAPABILITY_MATRIX §7w
added; retrospective + M23 planning
skeleton authored;
IMPLEMENTATION_ROADMAP updated with
M22 shipped status; coordinated
close-out commit + **first M22
push** landing all four M22
commits to `origin/main`.

**Milestone shape:** four
increments across four sessions
(SESSION_171 → SESSION_174) —
M22.0 planning + M22.1 audit
tooling correction + M22.2 JE
reversal journey + M22.4 close-
out. **M22.3 SKIPPED per §5.b
page/persona walk evidence**
(second consecutive milestone
where §5.h Option B evidence-
sized posture shrank the shape;
M21.4 skipped for the same
reason).

**Backend baseline delta across
M22:** 4,761 → 4,766 (+5 M22.2
seed idempotency tests). M22.1
added no tests per §0.a
discretionary call.

**Frontend Vitest unchanged
across M22:** 180 → 180. Zero
frontend components shipped per
§5.a refined framing.

**Acceptance suite: 6 → 7
journeys.** M22.2 added
`office/accounting_je_reversal.spec.ts`.
Clean-DB dry-run at M22.4
close: **13 passed @ 18.3s**
(matching M22.2 close baseline
exactly).

**Zero-drift permission-class
streak extends 21 → 22
consecutive milestones** (M10
→ M22). **Planning-time as-
recommended streak still 88
across thirteen consecutive
milestones** (M10 → M22).
Zero §0.a amendments
introducing new §5 decisions
throughout M22.

## Close-out artifacts landed

- **`docs/CAPABILITY_MATRIX.md`
  §7w** — M22 shipped surface
  documented with per-increment
  table + governing-contract
  refinement notes + deferrals
  list + operator-experience
  summary. Mirrors §7v format.
- **`docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`**
  — full retrospective with
  nine sections mirroring M21
  structure: §1 planned scope,
  §2 what shipped, §3 deviations
  (M22.3 collapse + §5.a reshape),
  §4 deferrals reviewed, §5
  eight lessons learned, §6
  streak status, §7 governing-
  contract validation, §8
  corrections landed, §9
  standing M23 question with
  three evidence-based candidates
  (H — test-hygiene; A2 — next
  accounting iteration; O2 —
  next OSC iteration).
- **`docs/roadmap/MILESTONE_23_PLANNING.md`**
  — skeleton (status: draft)
  with candidate list carrying
  Candidate H (NEW at M22
  close) elevated alongside
  A2 and O2; six planning
  inputs from M22 close; M23.0
  procedural checklist.
- **`docs/roadmap/IMPLEMENTATION_ROADMAP.md`**
  — M22 section added after
  M21 section covering business
  objective, empirical M22.0
  discovery, governing-contract
  refinement, operational pain
  resolved, existing reusable
  primitives, gap analysis,
  four shipped increments,
  deferrals list. Roadmap now
  reflects M22 SHIPPED status.
- **`docs/handoffs/SESSION_174_m22_inc4_close.md`**
  — this document.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M23.0 planning
  session.

## Verification

- **Starting state:** `git
  status` clean, top three
  commits M22.0/M22.1/M22.2,
  backend baseline **4,766
  pass**, frontend Vitest
  180 pass, tsc clean
  (frontend + acceptance),
  `manage.py check` +
  `makemigrations --check`
  clean, Redis PONG.
- **Clean-DB acceptance dry-
  run:** deleted
  `backend/db.acceptance.sqlite3`,
  ran `npx playwright test`
  → **13 passed @ 18.3s** (6
  setup + 7 journeys).
  Matches M22.2 close
  baseline exactly.
- **No CI regressions
  detected at close.** All 7
  journeys pass on clean-DB
  state; the pre-existing
  same-day multi-run
  hygiene issue (three
  journeys mutating state
  their seeds don't reset)
  documented in M22.2
  handoff and M22
  retrospective §9 as
  Candidate H (NEW).

## Streak status at M22.4 close

- **Zero-drift permission-
  class:** **twenty-two
  consecutive milestones**
  (M10 → M22). Extended from
  21. Every M22 endpoint
  invocation stays within
  existing permission classes
  (`IsSalesManagerOrOwnerAtActiveDealership`
  for all accounting
  workflows exercised by the
  M22.2 journey).
- **Planning-time as-
  recommended:** **88 across
  thirteen consecutive
  milestones** (M10 → M22).
  All seven §5 decisions at
  M22.0 open confirmed as-
  recommended. Zero §0.a
  amendments introducing new
  §5 decisions.
- **Evidence-sized shape
  shrink:** second consecutive
  milestone where §5.h
  Option B evidence-sized
  posture allowed the shape
  to shrink per evidence
  (M21.4 skipped; M22.3
  skipped). Reinforces the
  §5.h Option B posture as
  the correct default for
  audit / validation shapes.
- **Backend baseline
  monotonicity:** preserved.
  4,755 → 4,761 (+6 across
  M21) → 4,766 (+5 across
  M22). Zero regressions.

## What lands at M22.4 close-out push

Four commits surface to
`origin/main` together per
the M18.6 / M19.6 / M20.5 /
M21.5 cadence:

- `421a75c` — M22.0 planning
  refinement + target
  selection.
- `f95db70` — M22.1 audit
  tooling correction +
  artifact refresh.
- `6635a9d` — M22.2 JE
  reversal journey + seed
  extension.
- (M22.4 close-out commit,
  hash TBD after commit
  lands).

The M22.4 close-out push
triggers the **first real
M22 CI run**. Verified at
M23.0 open per the standing
CI-monitoring checklist.

## What's next: SESSION_175 M23.0 planning refinement + target selection

Per
`MILESTONE_23_PLANNING.md`
skeleton (§What M23.0 must
do):

1. Verify CI status on the
   M22 push (first M22 CI
   run).
2. Regenerate the audit
   artifact — accounting
   trustworthy post-M22.1
   fix; other domains may
   still have variable-first
   URL-assembly false
   negatives worth
   correcting.
3. Present the candidate
   list — H (test-hygiene,
   NEW), A2 (next accounting
   iteration), O2 (next OSC
   iteration) elevated;
   T/U/L/M gated; D/C
   evidence-deferred; P/G
   stable-deferred.
4. Recommend a §5.a target
   with rationale grounded
   in operator pain resolved,
   dependencies, scope
   discipline, and the M22
   §9 evidence.
5. Await user confirmation.
6. Once §5.a locks, draft
   §5.b–§5.h load-bearing
   decisions with confirm-
   as-recommended posture
   (streak target 88 → 89).
7. DoD amendment compliance
   check on §3 draft.
8. Expand skeleton to full
   active memo.
9. Ship
   `docs/handoffs/SESSION_175_m23_inc0_planning.md`.
10. Refresh
    `00-START-NEXT-SESSION.md`
    for M23.1.
11. Do NOT push — M23.0 is
    planning only; coordinated
    close-out push at M23
    close per M18/M19/M20/M21/M22
    cadence.

## Non-goals for SESSION_175

- ❌ Do NOT ship any backend or
  frontend code — planning-only
  session.
- ❌ Do NOT open any
  implementation increment —
  M23.1 is a separate session.
- ❌ Do NOT force-push or amend
  earlier commits (M22 close is
  on `origin/main` from this
  push).
- ❌ Do NOT modify M1-M22
  shipped surface.
- ❌ Do NOT modify the
  acceptance suite unless CI
  regression fixes land as
  §0.a M23.0 amendments.
- ❌ Do NOT skip the DoD
  compliance check — the M23
  active memo's §3 is required
  to address the amendment.

## Baseline expected at close

Backend + frontend unchanged
from M22.4 close. Backend
**4,766 pass**, frontend
Vitest **180 pass**,
acceptance suite **7
journeys / 13 passed on
clean DB (~18s)**.
Coordinated push landed all
4 M22 commits to
`origin/main`.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   (M22 shipped section
   landed at M22.4)
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_23_PLANNING.md`
   (skeleton — expanded at
   SESSION_175)
6. `docs/roadmap/MILESTONE_22_RETROSPECTIVE.md`
   §8 (M22 corrections) + §9
   (standing M23 question)
7. `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
   (audit artifact — now
   authoritative for accounting
   post-M22.1 fix)
8. `docs/roadmap/MILESTONE_22_PLANNING.md`
   (M22 refined governing
   contract that any
   validation-shape M23
   inherits)
9. `docs/CAPABILITY_MATRIX.md`
   §7w (M22 shipped surface)
10. `docs/handoffs/SESSION_173_m22_inc2_je_reversal.md`
    (M22.2 close — first
    anchor journey)
