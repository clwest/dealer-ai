---
title: "SESSION_166 handoff — Milestone 21 · Increment 0 (M21.0 — planning refinement + target selection)"
status: historical
type: handoff
date: 2026-08-03
session: 166
milestone: 21
milestone_status: in-progress
milestone_name: "Operational Surface Completion"
increment: 0
increment_status: shipped
commit: TBD
---

# SESSION_166 — Milestone 21 · Increment 0 (M21.0 — planning refinement + target selection)

## What shipped

Planning-only session per the M10.0 /
M11.0 / M12.0 / M13.0 / M14.0 / M15.0 /
M16.0 / M17.0 / M18.0 / M19.0 / M20.0
precedent. Full memo expansion from the
M20.5 skeleton + all **eight** §5 load-
bearing decisions resolved at open.

**§5.a → Candidate O confirmed** —
Operational Surface Completion, an
evidence-driven umbrella milestone that
closes the highest-value missing UI
workflows found by the M20 operational
audit. Milestone name: **"Operational
Surface Completion."** User named at
SESSION_166 M21.0 open. Two anchor
implementations pre-committed at
planning-time: BHPH write-side UI
(subsumes Candidate B) + be-back write-
side UI. Conditional third anchor:
follow-up cadence queue UI, entering
scope only if the M21.1 systematic
audit confirms fit. Candidate A
(accounting), Candidate P (onboarding
UX polish), Candidate G (dashboard
testid hardening — bundled
opportunistically per §5.g),
Candidates D, C (evidence-deferred),
and Candidates T, U, L, M (signal-
gated) all deferred with re-entry
paths preserved per discovery rule.

**§5.b–§5.h all confirmed as-recommended.**
Streak extends to **87 planning-time as-
recommended M5.1 → M21.0** across **twelve
consecutive milestones now** (M10 + M11 +
M12 + M13 + M14 + M15 + M16 + M17 + M18 +
M19 + M20 + M21).

**Governing contract established
(Candidate O).** Every M21 shipped
surface must satisfy four conditions:
(1) maps to an already-shipped backend
capability (service verb, DRF endpoint,
or both); (2) closes a missing operator-
facing UI (capability reachable today
only via curl / Postman / Django shell,
or unreachable entirely); (3) adds or
extends a Playwright operational
journey; (4) is not generic UX polish.
Governs every §5 decision, every
increment scope call, every audit
finding review, and every review of a
proposed scope addition.

**Definition of Done amendment
formalized (§5.f Option B).** Every
future customer-facing milestone must
either (a) add or update at least one
Playwright operational journey covering
the shipped operator surface, or (b)
explicitly document in §3 of the
planning memo why no journey change is
required. Infrastructure-only milestones
with no customer-facing surface changes
satisfy via (b). Non-adherence is a
planning-memo review finding. Amendment
applies from M21 forward; M21 itself
trivially satisfies via §5.e.

**Backend baseline unchanged:** 4,755
pass, 1 skipped, 0 fail (verified via
CI-green on the M20.5 + M21 skeleton
pushes; local re-verification trusted
to CI per user's SESSION_166 open
posture). **Frontend Vitest baseline
unchanged:** 153 pass. Migrations
`0001`–`0048` (unchanged). Tenancy
carriers 52 (unchanged — M21 adds no
tenancy carriers). DRF admin surface
113 (unchanged — M21 adds no
endpoints). Frontend operator routes
20 (unchanged — M21 adds no routes).
Permission classes 7 (unchanged —
zero-drift streak intact at twenty
consecutive milestones; M21 extends
to twenty-one at close). Celery-beat
task families 10 (unchanged — M21
has no beat entry). Acceptance suite
6 journeys (unchanged — M21 extends
existing journeys, conditionally
adds one, does not modify shipped
suite at M21.0).

## Load-bearing decisions confirmed at M21.0 open

Eight decisions per M20.0 precedent.
All confirmed as-recommended.

**§5.a — Milestone target selection.**
Candidate O — Operational Surface
Completion. Evidence-driven umbrella
consuming M20's operational audit as
scope input. Two anchor implementations
pre-committed (BHPH + be-back);
conditional third anchor (follow-up
cadence). Candidate A preserved as
standing M22 question per discovery
rule.

**§5.b — Audit methodology.** Option C —
combined service-verb + DRF-endpoint
enumeration cross-referenced against
frontend consumption. Belt-and-
suspenders posture — service-verb walk
catches capabilities that exist as
verbs without endpoint exposure; DRF
walk catches endpoints without frontend
consumers. Audit executed as
programmatic scripts under
`backend/dealer_ai/scripts/` (not
runtime code); output feeds §5.c
artifact.

**§5.c — Audit artifact format.** Option
A — single markdown audit artifact at
`docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`.
Per-row schema: (a) backend capability,
(b) missing operator surface, (c)
affected operational journey, (d)
recommended milestone disposition
(`M21-anchor`, `M21-conditional`,
`defer-candidate-O2`, `defer-domain-
milestone`, `intentional-omission`).
One canonical table + brief per-domain
narrative sections. Distinct
authoritative document (not a
CAPABILITY_MATRIX column) per
DOC_GOVERNANCE.md §2 separate-lifecycle
posture.

**§5.d — Scope selection mechanism
(post-audit).** Option B — assistant
recommends scope after M21.1 audit
lands with rationale per candidate;
user confirms or redirects.
Recommendation timing: after M21.1
audit closes, before M21.2 opens. Two
anchor implementations pre-committed
at §5.a; selection mechanism governs
the conditional third anchor + any
audit-surfaced additions.

**§5.e — Journey-extension contract.**
Option C — mixed extend / new by
workflow shape. BHPH write path
extends `bhph/collections_workflow.spec.ts`
(re-expansion of M20.4 narrowed
scope). Be-back triage extends the
sales-manager daily-startup journey
or introduces a new journey per M21.3
open decision. Follow-up cadence (if
scope) extends or new per M21.4 open
decision.

**§5.f — Definition of Done amendment
adoption.** Option B — adopt with
documented exception path. Every
customer-facing milestone must add
or update at least one Playwright
operational journey, or explicitly
document in §3 why no journey change
is required. Amendment applies from
M21 forward. M21 satisfies via §5.e.

**§5.g — Testid hardening posture.**
Option B — opportunistic. Add
`data-testid` attributes only where
new / extended M21 journeys need
them. Full-coverage testid pass
remains Candidate G territory for a
future milestone shape.

**§5.h — Increment sequencing +
completion contract.** Option B —
evidence-sized four-to-six
increments. **M21.0 planning** (this
session) + **M21.1 systematic audit
+ M21 scope lock** + **M21.2 BHPH
write-side UI + journey extension**
+ **M21.3 be-back write-side UI +
journey extension or addition** +
**M21.4 conditional follow-up
cadence UI + audit-surfaced
additions** (only if audit confirms
fit) + **M21.5 close-out**. Milestone
completion contract: all in-scope UIs
ship with passing journey extensions
/ additions on `main` CI; audit
artifact committed and current; DoD
amendment adopted and referenced from
IMPLEMENTATION_ROADMAP; retrospective
§9 records standing M22 question.

## Streak

**87 planning-time as-recommended
M5.1 → M21.0.** Twelve consecutive
milestones now (M10 + M11 + M12 + M13
+ M14 + M15 + M16 + M17 + M18 + M19 +
M20 + M21) with every §5 decision
confirmed as-recommended at planning-
time open.

Historical §5 counts:
- M10 through M17: 6 decisions each
  = 48.
- M18: 7 decisions.
- M19: 8 decisions.
- M20: 8 decisions.
- M21: 8 decisions.
- Total across eleven milestones
  (M10–M21): 48 + 7 + 8 + 8 + 8 =
  **79 §5 decisions**.

The "87 planning-time as-recommended
M5.1 → M21.0" counter accumulates
per the tracking convention
established at earlier milestones.
The twelve consecutive milestones
(M10 → M21) carries the "as-
recommended per milestone open"
invariant without a single
deviation.

## What's next: SESSION_167 M21.1 systematic operational-surface audit + M21 scope lock

Per `MILESTONE_21_PLANNING.md` §7
M21.1:

- **Audit scripts.**
  `backend/dealer_ai/scripts/audit_operational_surface.py`
  (or split into two focused
  scripts) implementing §5.b Option
  C combined methodology. Walks
  service-verb modules + DRF
  viewsets + URL configs; cross-
  references against frontend API-
  call surface (`frontend/src/**/*.{ts,tsx}`
  `useMutation` / `useQuery` /
  `axios.*` / `fetch` call sites).
  Emits input for the M21 audit
  artifact. Not runtime code —
  scripts are operator-invoked
  during the M21.1 increment.
- **Audit artifact.**
  `docs/roadmap/M21_OPERATIONAL_SURFACE_AUDIT.md`
  populated with per-row
  dispositions per §5.c Option A
  schema. Per-row: (a) backend
  capability (service verb path +
  DRF endpoint path when present),
  (b) missing operator surface
  (component path expected, or
  "unreachable"), (c) affected
  operational journey (existing or
  "new required"), (d) recommended
  milestone disposition
  (`M21-anchor`, `M21-conditional`,
  `defer-candidate-O2`, `defer-
  domain-milestone`, `intentional-
  omission`). One canonical table
  + per-domain narrative sections.
- **Scope recommendation +
  confirmation** per §5.d Option B.
  Assistant proposes scope for
  M21.2 onward with rationale per
  candidate. Recommendation
  includes: BHPH + be-back anchor
  confirmation (pre-committed at
  §5.a but re-validated against
  audit findings), follow-up
  cadence disposition (fit or
  defer), any additional audit-
  surfaced items with `M21-anchor`
  or `M21-conditional`
  disposition. User confirms or
  redirects.
- **Scope lock recorded** as §0.a
  M21.1 amendment in
  MILESTONE_21_PLANNING.md.
  Frontmatter `sources` may
  extend; §7 increment shape may
  adjust (M21.4 skipped if scope
  excludes conditional items;
  additional increments if audit
  surfaces implementation-splitting
  evidence).
- **Session handoff** at
  `docs/handoffs/SESSION_167_m21_inc1_audit.md`.
- **`00-START-NEXT-SESSION.md`**
  refreshed for M21.2.

**Backend baseline target at M21.1
close:** 4,755 (unchanged — audit
scripts are operator-invoked, not
tested; no seed delta commands land
in this increment). Frontend Vitest:
153 (unchanged). Acceptance suite: 6
journeys (unchanged).

## What lands at M21.2 (SESSION_168) — first anchor

BHPH write-side UI:

- Frontend components:
  - `RecordPromiseToPayForm`
    attached to Promises card.
  - `MarkBrokenPromiseButton` +
    `MarkKeptPromiseButton` row-
    level actions on Promises card.
  - `LogCollectionContactForm`
    attached to Contacts card.
  - `InitiateRepossessionForm`
    attached to Repossessions card.
  - `MarkRecoveredButton` row-
    level action on Repossessions
    card.
- Vitest coverage for the new forms
  + buttons.
- Extended
  `dealer_ai/management/commands/seed_journey_bhph_collections_workflow.py`
  covering the write-side setup +
  backend tests.
- Extended
  `acceptance/journeys/bhph/collections_workflow.spec.ts`
  covering: record PtP → mark
  broken → log contact → initiate
  repossession with business-
  outcome assertions.
- Opportunistic testids per §5.g.

Backend baseline target: ~4,760–
4,770. Frontend Vitest: ~163–170.
Acceptance suite: 6 journeys (BHPH
re-expanded).

## What lands at M21.3 (SESSION_169) — second anchor

Be-back write-side UI:

- Frontend components:
  - `RecordBeBackForm` (attach
    location finalized at M21.3
    open based on M21.1 audit
    finding).
  - `MarkBeBackReturnedButton` +
    `MarkBeBackNoShowButton` row-
    level actions on be-back queue
    view.
  - `BeBackQueueTable` if the
    sales manager dashboard lacks
    a dedicated queue surface
    (M21.1 audit to confirm).
- Vitest coverage.
- Extended
  `dealer_ai/management/commands/seed_journey_sales_manager_daily_startup.py`
  (or new
  `seed_journey_sales_manager_be_back_triage.py`)
  + backend tests.
- Extended
  `acceptance/journeys/sales_manager/daily_startup.spec.ts`
  or new
  `acceptance/journeys/sales_manager/be_back_triage.spec.ts`
  per §5.e Option C decision made
  at M21.3 open.
- Opportunistic testids per §5.g.

Backend baseline target: ~4,770–
4,780. Frontend Vitest: ~170–180.
Acceptance suite: 6 or 7 journeys.

## What lands at M21.4 (SESSION_170) — conditional

**Only if the M21.1 audit's scope
selection includes cadence and / or
additional audit-surfaced items.**

Follow-up cadence queue UI + any
additional audit-surfaced items
marked `M21-anchor` or
`M21-conditional`. Corresponding
Vitest coverage + seed delta
commands + journey extensions or
additions per §5.e Option C +
opportunistic testids per §5.g.

If scope-selection excludes M21.4,
this increment is skipped and M21.5
becomes SESSION_170.

Backend baseline target (if
applicable): ~4,780–4,790. Frontend
Vitest: ~180–195. Acceptance suite:
7 or 8 journeys.

## What lands at M21.5 (SESSION_170 or SESSION_171) — close-out

- CI job validation on all extended
  / new journeys.
- `docs/CAPABILITY_MATRIX.md` §7v
  (M21 shipped surface).
- `docs/roadmap/MILESTONE_21_RETROSPECTIVE.md`
  with §9 standing M22 question.
- `docs/roadmap/MILESTONE_22_PLANNING.md`
  skeleton (status: draft).
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  updated with M21 shipped status
  + DoD amendment formalized in the
  roadmap contract section.
- `00-START-NEXT-SESSION.md`
  refreshed for M22.0.
- Coordinated close-out commit + push
  per M18.6 / M19.6 / M20.5 pattern.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_21_PLANNING.md`
   (this session's expansion target)
6. `docs/roadmap/MILESTONE_20_RETROSPECTIVE.md`
   §8 + §9 (M20 unblocks + standing
   M21 question — M21's origin)
7. `docs/roadmap/MILESTONE_20_PLANNING.md`
   (M20 substrate M21 consumes;
   framework + journey patterns M21
   extends)
8. `docs/roadmap/MILESTONE_18_RETROSPECTIVE.md`
   §8 (accounting slot designation
   preserved as elevated M22
   recommendation per M21 §5.a
   rationale (3))
9. `docs/CAPABILITY_MATRIX.md` §7u
   (M20 shipped surface — the
   substrate M21's audit walks)
