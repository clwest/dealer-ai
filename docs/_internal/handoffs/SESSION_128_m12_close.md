---
title: "SESSION_128 handoff — Milestone 12 · Increment 8 (M12.8 — closeout)"
status: historical
type: handoff
date: 2026-08-02
session: 128
milestone: 12
milestone_status: shipped
increment: 8
increment_status: shipped
commit: TBD
---

# SESSION_128 — Milestone 12 · Increment 8 (M12.8 — closeout)

## What shipped

Documentation-only closeout per the
M10.8 / M11.7 precedent. Six close-
out docs + one coordinated commit.
**Milestone 12 — BHPH portfolio
operations (v1) — SHIPPED.**

**M12 close totals:** five new
entities across seven
implementation sessions (BhphNote +
BhphPayment + BhphPromiseToPay +
CollectionContact + Repossession) +
one additive `BhphNote` extension
(`current_bucket` + `days_past_due`
aging columns at M12.3) + seven new
`services/` packages (`bhph_notes` /
`bhph_payments` /
`bhph_delinquency` /
`bhph_promises` /
`collection_contacts` /
`repossessions` /
`bhph_analytics`) + one new
frontend route family (with two
MVP pages: portfolio dashboard +
per-note detail) + two new Celery-
beat task families (M12.3 aging
detector at 08:00 + M12.4 broken-
PTP detector at 09:00) + one new
post-LLM scrub stage
(`collection_language` under
`kind="collection_contact"`).
**Six planning-time §5 decisions
confirmed as-recommended at M12.1
open** — streak stands at **41
planning-time as-recommended
M5.1 → M12.1** across three
consecutive milestones now (M10 +
M11 + M12).

**Backend baseline: 4,150 pass, 1
skipped, 0 fail** (was 3,895 at
M11 close — **+255 tests, zero
regressions**). **Frontend Vitest
baseline: 78 pass** (was 67 at M11
close — **+11 tests, zero
regressions**). Migrations `0037`
–`0042`. Tenancy carriers 44. DRF
admin surface 98. Frontend
operator routes 17. Celery-beat
task families 8. Post-LLM scrub
layers 17. Permission classes 8
(unchanged — every M12 endpoint
reused
`IsSalesManagerOrOwnerAtActiveDealership`;
zero drift across seven M12
implementation increments).

**Push authorization:** eight
local commits (M12.1 through
M12.8) queued for user
authorization at SESSION_128
close.

## Files touched

### New
- `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
- `docs/roadmap/MILESTONE_13_PLANNING.md`
  (planning skeleton per standing
  user directive)
- `docs/handoffs/SESSION_128_m12_close.md`
  (this file)

### Modified
- `docs/CAPABILITY_MATRIX.md` —
  added new §7m subsection for
  M12 BHPH portfolio
  capabilities.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
  — flipped M12 heading to
  "SHIPPED at SESSION_128" +
  added full delivery-record
  summary block at the top of
  the M12 section.
- `docs/roadmap/MILESTONE_12_PLANNING.md`
  — frontmatter status flipped
  `draft` → `shipped`; added
  `shipped_at_session` +
  `retrospective` keys.
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_129 · M13.0
  (planning-refinement session).

## By the numbers

- **Backend baseline: 4,150 pass**
  (unchanged — docs-only).
- **Frontend Vitest baseline: 78
  pass** (unchanged).
- **Migrations `0042`** (unchanged
  — no new migrations at M12.8).
- **Tenancy carriers: 44**
  (unchanged).
- **DRF admin surface: 98**
  (unchanged).
- **Frontend operator routes: 17**
  (unchanged).
- **Celery-beat task families: 8**
  (unchanged).
- **Post-LLM scrub layers: 17**
  (unchanged).
- **Permission classes: 8**
  (unchanged).

## What SESSION_129 opens

**SESSION_129 opens M13.0 —
planning refinement + first-
decision review.** Per
`MILESTONE_13_PLANNING.md`
(drafted at M12.8 close per
standing user directive):

- Six §5 decisions to confirm at
  session open — all follow M12
  pattern (recommendations
  drafted per §4 of the M13
  planning skeleton).
- **§5.a is the load-bearing
  decision** — which of nine
  business questions define
  M13 scope. Recommendation:
  Option A (substrate + Q1 M2
  cost reconciliation as first
  slice).
- **Note the incremental
  structure** per
  IMPLEMENTATION_ROADMAP
  §Milestone 13: a single
  monolithic accounting
  milestone violates Project
  Rule 4 (Scope Discipline).
  Multiple slices layer onto
  M14+ or into ongoing
  operational milestones.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md`
   §Milestone 12 + §Milestone 13
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_12_RETROSPECTIVE.md`
   (this session's authored doc)
6. `docs/roadmap/MILESTONE_13_PLANNING.md`
   (this session's authored doc)
7. `docs/CAPABILITY_MATRIX.md` §7m
8. `docs/handoffs/SESSION_127_m12_inc7_analytics_ui.md`
   (previous session)
9. `docs/handoffs/SESSION_121_m12_inc1_bhph_note.md`
   through
   `docs/handoffs/SESSION_127_m12_inc7_analytics_ui.md`
   (seven M12 implementation
   handoffs)
10. `docs/research/BHPH_OPERATIONS_MAPPING.md`
11. `docs/research/ACCOUNTING_DEPARTMENT_MAPPING.md`
    (M13 substrate)
