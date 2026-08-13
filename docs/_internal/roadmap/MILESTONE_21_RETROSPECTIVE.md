---
title: "Milestone 21 — Retrospective"
status: shipped
type: retrospective
date: 2026-08-03
sessions: SESSION_166 → SESSION_170
milestone: 21
milestone_name: "Operational Surface Completion"
related:
  - docs/roadmap/MILESTONE_21_PLANNING.md
  - docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md
  - docs/roadmap/MILESTONE_20_RETROSPECTIVE.md
  - docs/CAPABILITY_MATRIX.md §7v
  - docs/roadmap/IMPLEMENTATION_ROADMAP.md §Milestone 21
---

# Milestone 21 — Retrospective

Written at Milestone 21 close
(SESSION_170). Records what was planned,
what shipped, what deviated and why, and
lessons carried forward for Milestone 22
and beyond. Mirrors the
`MILESTONE_20_RETROSPECTIVE.md` structure
so milestone history remains directly
comparable.

## 1. Planned scope

`MILESTONE_21_PLANNING.md` at SESSION_165
close (skeleton) and SESSION_166 (full
active memo) defined the milestone as
**Operational Surface Completion** —
Candidate O per §5.a. Governing contract
(Candidate O): every M21 shipped surface
must (a) map to an already-shipped
backend capability, (b) close a missing
operator-facing UI, (c) add or extend a
Playwright operational journey, and (d)
not be generic UX polish. Two anchor
implementations pre-committed at
planning-time (BHPH write-side UI +
be-back write-side UI); one conditional
scope item (follow-up cadence queue UI);
a systematic audit as Increment 1 to
drive remaining scope by evidence.

Eight §5 load-bearing decisions all
resolved as-recommended at M21.0 open
(§5.a target = Candidate O; §5.b audit
methodology = combined service-verb +
DRF-endpoint enumeration; §5.c audit
artifact format = single markdown table;
§5.d scope-selection mechanism =
recommend + confirm-as-recommended;
§5.e journey-extension contract =
mixed extend/new by workflow shape;
§5.f DoD amendment adoption = adopt
with documented exception path; §5.g
testid hardening posture = opportunistic
only; §5.h increment sequencing =
evidence-sized four-to-six increments).

## 2. What actually shipped

**Five increments across five sessions**
(SESSION_166 → SESSION_170) — one
sequencing shift vs. the six-increment
planning-memo expectation: **M21.4
collapsed per the M21.1 audit's evidence
that no additional scope-worthy items
existed.** Milestone shape: M21.0
planning + M21.1 audit + M21.2 BHPH +
M21.3 be-back + cadence + M21.5
close-out. Down from six because M21.4
was gated on audit findings that never
materialized.

### M21.0 — Planning refinement + target selection (SESSION_166)

Full memo expansion + all eight §5
decisions resolved. Candidate O
confirmed at open; two anchor
implementations pre-committed. DoD
amendment formalized as §5.f Option B.
**Streak: 86 → 87 planning-time as-
recommended M5.1 → M21.0 across twelve
consecutive milestones (M10 → M21).**
Handoff at
`docs/handoffs/SESSION_166_m21_inc0_planning.md`.

### M21.1 — Systematic operational-surface audit + M21 scope lock (SESSION_167)

Audit tooling shipped at
`backend/dealer_ai/scripts/audit_operational_surface.py`
per §5.b Option C. Audit artifact
populated at
`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
per §5.c Option A schema. **153
endpoints enumerated at M21.1**:
96 covered / 57 backend-only. Three
reconciliations against M20 skeleton
Input 1: (a) be-back write path
narrower than assumed — only CREATE
missing at component level; mark-verbs
ship via `DealerAiSalesBeBacks.tsx`;
(b) follow-up cadence queue partly
UI-consumed — list / complete / skip
ship via `DealerAiSalesFollowUps.tsx`;
only CONFIG (create + pause) missing;
(c) BHPH write path confirmed at
exactly seven verbs. Scope locked per
§5.d Option B: M21.2 BHPH writes; M21.3
be-back CREATE + cadence CONFIG; M21.4
skipped; M21.5 close-out. Handoff at
`docs/handoffs/SESSION_167_m21_inc1_audit.md`.

### M21.2 — BHPH write-side UI + journey extension (SESSION_168)

Seven `bhphApi.ts` write wrappers +
seven React components (5 files) wired
into `DealerAiBhphNoteDetail.tsx`.
**18 new Vitest tests** (153 → 171
pass). Extended
`seed_journey_bhph_collections_workflow`
with three M21.2 fixtures (promised
promise + recovered repossession +
complete ConditionReport). Re-expanded
`bhph/collections_workflow.spec.ts`
from M20.4 read-only narrow to full
7-endpoint write coverage. **Verified
locally 7/7 pass (846ms).** Backend
baseline 4,755 → 4,758 (+3 seed
tests). Handoff at
`docs/handoffs/SESSION_168_m21_inc2_bhph_write.md`.

### M21.3 — Be-back CREATE + Follow-up cadence CONFIG + journey extension (SESSION_169)

`RecordBeBackForm` on
`DealerAiSalesBeBacks.tsx`;
`CadenceConfigPanel` (create +
pause-by-id + inline pause) on
`DealerAiSalesFollowUps.tsx`. **9 new
Vitest tests** (171 → 180 pass).
Extended
`seed_journey_sales_manager_daily_startup`
with a pre-existing 24hr
`FollowUpCadence`. Extended
`sales_manager/daily_startup.spec.ts`
per §5.e Option C with three new
sub-steps (record be-back + create
cadence + inline-pause). **Verified
locally 7/7 pass (1.1s).** Backend
baseline 4,758 → 4,761 (+3 seed
tests). Handoff at
`docs/handoffs/SESSION_169_m21_inc3_be_back_cadence.md`.

### M21.5 — Close-out (SESSION_170)

Regenerated M21.1 audit artifact —
coverage 96 → **106** endpoints;
backend-only 57 → **47**. M21-anchor
and M21-conditional buckets both empty,
confirming M21.2 + M21.3 closed the
exact gaps they were scoped to close.
Full acceptance suite verified locally:
**12 passed (~18s)** matching M20 close
shape. `docs/CAPABILITY_MATRIX.md` §7v
lands. This retrospective. M22 planning
skeleton. IMPLEMENTATION_ROADMAP
amendment with formalized DoD.
Coordinated close-out commit + **first
M21 push** — five commits (M21.0 +
M21.1 + M21.2 + M21.3 + M21.5) surface
to `origin/main` together per M18.6 /
M19.6 / M20.5 cadence. Handoff at
`docs/handoffs/SESSION_170_m21_inc5_close.md`.

## 3. Deviations vs. planning memo

- **M21.4 collapsed** — the M21
  planning memo (§0.a §5.h) explicitly
  provisioned M21.4 for
  audit-surfaced conditional scope. The
  M21.1 audit found no additional
  scope-worthy items beyond the two
  anchors + one conditional
  (follow-up cadence CONFIG) already
  named. Collapsing was the right
  call — bolting a `defer-candidate-O2`
  item onto M21 would have violated
  the governing contract. This is a
  feature of the evidence-sized §5.h
  Option B posture, not a deviation
  from it.
- **Be-back scope narrowed vs. M21
  skeleton Input 1** — the M21
  planning skeleton assumed all three
  be-back verbs (create + mark-returned
  + mark-no-show) needed UI. Audit
  showed mark-verbs already shipped;
  only CREATE was missing. Anchor 2
  narrowed from three verbs to one.
  Not a deviation from planning — a
  correction that the audit was
  designed to surface.
- **Backend baseline delta smaller
  than estimated** — planning memo
  §4 estimated 4,755 → ~4,770-4,790
  at M21 close. Actual: **4,755 →
  4,761** (+6). The estimate assumed
  new seed delta commands per
  increment; actual approach reused
  the existing M20 seed commands and
  layered M21 fixtures on top via
  extensions. Cleaner + more
  idempotent than net-new commands.
- **Frontend Vitest delta larger
  than estimated** — planning memo
  §4 estimated 153 → ~170-185.
  Actual: **153 → 180** (right at
  the upper end of the estimate).
  Extra tests came from covering
  confirm-modal + button-disabled +
  wrapper-only edge cases per the
  M21.1 audit's clearer picture of
  what to test.
- **Everything else landed as
  planned** — governing contract
  compliance, zero-drift streak
  extension (20 → 21), planning-time
  streak extension (86 → 87), five-
  increment shape, coordinated
  close-out push.

## 4. Deferrals reviewed

Every deferral from
`MILESTONE_21_PLANNING.md` §3 remains
valid. Explicit review:

- **Generic UX polish** — deferred
  per §3 (1). No exceptions taken.
- **New backend service verbs or
  endpoints** — deferred per §3 (2).
  No exceptions.
- **Component-level refactoring for
  its own sake** — deferred per §3
  (3). Attaching new forms did not
  refactor the existing panel
  structure.
- **Full dashboard testid coverage
  (Candidate G)** — deferred per §3
  (4). Only opportunistic testids
  landed per §5.g Option B.
- **Accounting stream advances
  (Candidate A)** — deferred per §3
  (5). Elevated to M22 standing
  question in §9 below.
- **Migration to `vite preview` in
  CI** — carries forward from M20.5
  per §3 (6).
- **Cross-browser CI matrix** —
  carries forward per §3 (7).
- **npm audit vulnerability
  remediation** — carries forward
  per §3 (8).
- **CI artifact upload verification
  via intentional failure** — NOT
  verified this milestone; carries
  forward per §3 (9). The M21 pushes
  will trigger CI runs; if any fail
  as a natural regression, we'll
  observe the artifact upload flow
  then.
- **Systematic audit refresh
  schedule** — carries forward per
  §3 (10). Regenerated at M21.5
  open; formal refresh cadence
  defers.

**New M21-specific deferrals surfaced
during implementation:**

- **44 `defer-candidate-O2`
  endpoints** carried forward for
  future OSC-shaped milestones.
- **3 `defer-domain-milestone`
  endpoints** (accounting reversal +
  trial-balance snapshots) — clean
  M22 Candidate A scope target.
- **Nested TypeScript template
  literal support** in the audit
  regex — ~3 false-positive
  backend-only findings documented
  in the artifact.
- **CI-based audit regeneration** —
  audit is currently operator-
  invoked. If the artifact drifts
  as the codebase evolves, consider
  a nightly CI job or a git hook
  for future OSC milestones.

## 5. Lessons learned

**Lesson 1: The audit is a
first-class planning input, not a
one-time exercise.** The M21.1 audit
tightened anchor 2 from three verbs
to one and confirmed anchor 1 exactly
right. Without the audit, M21.3 would
have shipped three components for
be-back writes; two would have been
redundant. Every future OSC-shape
milestone should regenerate the
audit before locking scope.

**Lesson 2: Wrapper-only tagging
matters.** The M21.1 audit's second-
pass component-consumption check
(walking every non-test `.tsx` for
imports of `*Api.ts` exports)
reclassified 6 endpoints from
apparent-coverage to wrapper-only.
Without that check, the audit would
have said "be-back CREATE is
covered" when in reality the wrapper
existed but no form consumed it.
The wrapper-only category is the
subtle-gap detector; keep it in
future audit iterations.

**Lesson 3: Evidence can shrink a
milestone.** M21.4 was provisioned;
M21.4 was skipped. The milestone
shape adjusted to the audit findings
rather than forcing scope to fit a
planned increment count. §5.h Option
B ("evidence-sized four-to-six
increments") is the right posture
for umbrella-shaped milestones —
overriding it with a fixed count
would have created either padding
work (bolting a defer-O2 item on)
or scope violations (relaxing the
governing contract).

**Lesson 4: Reference the existing
seed shape.** M21.2 extended the
existing `seed_journey_bhph_collections_workflow`
rather than creating a new seed
command. Same for M21.3 with
`seed_journey_sales_manager_daily_startup`.
Layering additive fixtures on
existing seeds preserves the
journey's setup context (one seed
run, one journey run) and avoids
seed-command sprawl. Every future
OSC-shape milestone should ask
"which existing seed can I extend?"
before proposing a new one.

**Lesson 5: `@testid`s land
opportunistically, not
prophylactically.** §5.g Option B
committed to adding `data-testid`
only where new / extended journeys
needed them. In practice, ~40 new
testids landed at natural
insertion points (form field
inputs, submit buttons, row-action
buttons, state badges). None
"just in case." Journey stability
did not suffer; the testids that
matter got added; Candidate G's
full-coverage pass remains a
distinct future milestone.

**Lesson 6: The recovered repossession
+ ConditionReport fixture pattern
matters for state-machine journeys.**
Journeys that walk state transitions
(recorded → broken; ordered →
recovered; recovered → re-intaked)
need target rows in the expected
starting state. M21.2's approach of
adding two pre-transitioned fixtures
(promised-state promise + recovered-
state repossession + complete
ConditionReport) let the journey
walk the full transition sequence
without fabricating state mid-
journey via API calls. Future
journeys with multi-step state
machines should follow the same
pattern.

**Lesson 7: Combined-methodology
audit is worth the extra parse pass.**
§5.b Option C (walk BOTH urls.py AND
`*Api.ts` modules) surfaced gaps
that either single-source walk would
have missed. The service-verb walk
caught endpoint-less capabilities;
the DRF walk caught wrapper-less
endpoints; the component-consumption
pass caught wrapper-only endpoints.
Belt-and-suspenders paid off.

## 6. Streak status

- **Zero-drift permission-class
  posture:** **twenty-one
  consecutive milestones** (M10 →
  M21). Extended from 20 at M21
  close. Every M21 UI attaches to
  an existing endpoint via an
  existing wrapper via an existing
  permission class.
- **Planning-time as-recommended:**
  **87 across twelve consecutive
  milestones** (M10 → M21). All
  eight §5 decisions at M21.0 open
  confirmed as-recommended. M21.1
  scope-lock (§5.d Option B
  recommendation) also confirmed
  as-recommended.
- **Backend test-count
  monotonicity:** preserved.
  4,755 → 4,761 (+6). Zero
  regressions across the milestone.

## 7. Governing-contract validation

Every shipped M21 surface (10
components + 7 wrappers + 2 seed
extensions + 2 journey extensions +
1 audit artifact) satisfies all four
Candidate O conditions:

- **Maps to shipped backend
  capability** — audit-traceable
  for every UI action.
- **Closes a missing operator-
  facing UI** — verified by pre-
  M21 wrapper-only tagging + audit
  findings.
- **Adds or extends a Playwright
  operational journey** — DoD
  amendment satisfied for M21.2 +
  M21.3 via the two extended
  journeys.
- **Not generic UX polish** — no
  scope item required a new
  service verb; every scope item
  ties 1:1 to a backend verb + a
  missing form / button / action.

Contract compliance is a first-
class M21 deliverable — the M21
retrospective + audit artifact +
capability matrix §7v jointly
provide the trail for future
review.

## 8. Unblocks / new candidates surfaced by M21 work

- **Candidate A elevated to M22
  focal recommendation.** Four
  consecutive milestones now have
  diverged from the M18 §8
  accounting designation (M18 →
  M21). The M21.1 audit surfaced
  three accounting endpoints with
  `defer-domain-milestone`
  disposition (`journal-entry-
  reverse`, `trial-balance-
  snapshot-create/list/retrieve`)
  — a clean scope target for M22
  even if broader accounting work
  is out of appetite.
- **Candidate O2 preserved for
  future OSC iterations.** 44
  endpoints in `defer-candidate-O2`.
  Each is a legitimate umbrella
  scope target (F&I writes,
  lead-source-specific intake
  forms, BHPH note origination,
  BHPH payment intake, deal-
  writeup lifecycle, test-drive
  creation). Future OSC-shape
  milestones select from the
  regenerated artifact.
- **Candidate G surfaced as
  future opportunity.** M21
  landed opportunistic testids
  only; full-coverage testid
  pass across the shipped
  dashboards remains an
  independent milestone scope.
  Not urgent unless testid-
  brittleness surfaces in a real
  regression.
- **Audit tooling reusable.** The
  `audit_operational_surface.py`
  script is domain-agnostic (walks
  urls.py + `*Api.ts` + components).
  Future OSC-shape milestones
  inherit it — no per-milestone
  audit-tool rewrite needed.

## 9. Standing M22 question

**Is M22 the return-to-accounting
milestone (Candidate A)?**

**Elevated recommendation strength
at M21 close:** Four consecutive
milestones have diverged from the
M18 §8 accounting designation (M18
scoping change → M19 pilot
onboarding → M20 acceptance
substrate → M21 operational surface
completion). The M21.1 audit's
`defer-domain-milestone` disposition
gives Candidate A a clean, bounded
scope target — three specific
accounting endpoints (journal-entry
reverse + trial-balance snapshot
create / list / retrieve) that map
to existing service verbs + missing
UI. That framing lets a Candidate A
milestone honor the M21 governing
contract (map to shipped backend +
missing UI + Playwright journey +
not generic polish) rather than
re-opening the broader accounting
substrate work.

Alternative candidates preserved:

- **Candidate O2** — next OSC
  iteration selecting from the
  regenerated audit artifact.
  Attractive if the operational-
  surface work has more velocity
  than the accounting stream at
  M22 open.
- **Candidate T / U / L / M** —
  signal-gated. If Chris runs
  tester sessions between M21
  close and M22.0 open, T
  becomes actionable. If a real
  pilot dealer stages up, L
  becomes actionable.
- **Candidate D / C** — evidence-
  deferred. Same posture as M20 /
  M21 close.

**Recommendation to raise at M22.0
open:** Candidate A (accounting
reversal + snapshot lifecycle UI)
as the leading option; note the
elevated urgency (four consecutive
milestones diverging) alongside
the substrate opportunity
(Candidate A now fits the M21
governing-contract shape thanks
to the audit's disposition
work).

M22.0 §5.a resolution belongs to
SESSION_171. This retrospective's
role is to surface the question,
not to pre-commit the answer.
