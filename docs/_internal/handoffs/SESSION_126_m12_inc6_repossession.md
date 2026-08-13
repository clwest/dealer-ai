---
title: "SESSION_126 handoff — Milestone 12 · Increment 6 (M12.6 — Repossession record + post-repo handoff)"
status: historical
type: handoff
date: 2026-08-02
session: 126
milestone: 12
milestone_status: in_progress
increment: 6
increment_status: shipped
commit: TBD
---

# SESSION_126 — Milestone 12 · Increment 6 (M12.6 — Repossession record + post-repo handoff)

## What shipped

Fifth BHPH-portfolio entity
(`Repossession`) — three-state
machine (ordered → recovered →
re_intaked) tying into M3
`ConditionReport` for the post-
repo handoff — plus three verbs
+ four DRF endpoints. Per
`MILESTONE_12_PLANNING.md` §1.6.

**Five §0.a M12.6 open decisions
recorded as-recommended:**

1. **State machine** — three-
   state (ordered / recovered /
   re_intaked).
2. **Verb shape** — three verbs
   mirroring M12.4 (record_
   repossession / mark_recovered
   / mark_re_intaked). Terminal
   `re_intaked` is final.
3. **`intake_condition_report`
   FK deletion** — SET_NULL
   (the repo row is historical
   evidence).
4. **`agent_name`** — free text
   at MVP. RepoAgent entity
   defers to M12+ if operator
   evidence surfaces.
5. **Post-repo lifecycle
   handoff** — writes a fresh
   ConditionReport via existing
   M3/M4/M5 substrate; no new
   lifecycle states introduced.

Streak stands at **41 planning-time
as-recommended M5.1 → M12.1** (§0.a
implementation-time decisions don't
count against streak per M10 §9).

## By the numbers

- **Backend baseline: 4,126 pass, 1
  skipped, 0 fail** (was 4,096 at
  M12.5 close — **+30 tests, 0
  regressions**).
- **Frontend Vitest baseline: 67
  pass** (unchanged — no frontend
  at M12.6).
- **Migrations `0042`**
  (`0042_m126_repossession`).
- **Tenancy carriers: 43 → 44**
  (`Repossession` registered).
- **DRF admin surface: 92 → 96**
  (four new endpoints — create /
  list / mark-recovered /
  mark-re-intaked).
- **Frontend operator routes:** 15
  (unchanged).
- **Permission classes: 8**
  (unchanged).
- **Celery-beat task families: 8**
  (unchanged — no new detector
  at M12.6).

## Files touched

### New
- `backend/dealer_ai/services/repossessions/__init__.py`
- `backend/dealer_ai/services/repossessions/repossession.py`
  (three verbs)
- `backend/dealer_ai/views_repossessions.py`
  (four endpoints)
- `backend/dealer_ai/migrations/0042_m126_repossession.py`
- `backend/dealer_ai/tests/test_m126_repossession_model.py`
  (7 tests)
- `backend/dealer_ai/tests/test_m126_repossession_service.py`
  (13 tests)
- `backend/dealer_ai/tests/test_m126_repossession_endpoint.py`
  (10 tests)
- `docs/handoffs/SESSION_126_m12_inc6_repossession.md`
  (this file)

### Modified
- `backend/dealer_ai/models.py` — added
  `Repossession` model + 3-state
  vocab at end.
- `backend/dealer_ai/services/tenancy.py`
  — extended
  `_TENANT_CARRIER_MODEL_NAMES` 43
  → 44.
- `backend/dealer_ai/urls.py` — four
  new admin paths.
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_127 · M12.7
  priority.

## State machine

```
ordered ──mark_recovered──▶ recovered
                              │
                              └─mark_re_intaked──▶ re_intaked (terminal)
                                       (+ ConditionReport)
```

**Skip transitions refused.** `ordered
→ re_intaked` raises
`InvalidStateTransitionError` → 409
— the vehicle must be recovered
first. The state machine is more
strict than M12.4 (which had two
independent paths from `promised`);
here the linear ordering reflects
the physical reality of the repo
workflow.

## Post-repo handoff to M3/M4/M5

The `mark_re_intaked` transition
requires a :class:`ConditionReport`
reference. The operator creates a
fresh inspection via the existing
M3 endpoints when the vehicle
returns; that ConditionReport pk
then flows into the mark-re-intaked
endpoint payload:

```
POST /admin/bhph-repossessions/<pk>/mark-re-intaked/
Body: {"condition_report_id": <M3 report pk>}
```

This preserves the M3/M4/M5
substrate byte-for-byte — no new
recon-lifecycle states introduced.
The re-intaked vehicle enters the
existing recon workflow as any
newly-inspected unit would.

## Non-goals honored

- ❌ No portfolio analytics or UI
  (M12.7).
- ❌ No `RepoAgent` first-class
  entity — free text at MVP.
- ❌ No M4 recon-lifecycle
  modifications.
- ❌ No auto-charge-off on
  repossession — `charge_off_
  candidate` bucket flag stays
  operator scope (M12+).
- ❌ No SMS / notification of
  the customer when a
  repossession is ordered
  (compliance-sensitive; defer).
- ❌ No auto-creation of the
  ConditionReport — operator
  triggers M3 inspection
  workflow explicitly.

## Design notes worth remembering

### Three-state linear machine
Distinct from M12.4's promised →
kept / broken branching. Repo has
a mandatory ordering (order →
recover → re-intake) matching
the physical workflow. The linear
constraint prevents operators
from marking a repo re_intaked
without a recovery event on
record.

### `mark_re_intaked` requires payment reference-equivalent
The `condition_report_id` payload
mirrors the M12.4 `bhph_payment_id`
pattern — a terminal transition
that carries a link to the
downstream artifact fulfilling
the transition. Preserves audit
clarity.

### SET_NULL on ConditionReport
FK deletion doesn't cascade into
the repo record. Historical
evidence must survive an
accidental report deletion.
The re_intaked state stays
recorded even if the FK is
subsequently null.

### `agent_name` free text
Deliberate MVP simplicity. Real
BHPH portfolios often work with a
small handful of recovery agents;
denormalizing the name into the
row now, then extracting a
`RepoAgent` entity later, is
cheaper than premature abstraction.
The M11-pattern of not
introducing entities without
documented business need.

### Vehicle FK path stays intact
Repossession.note.sale.vehicle
walks the chain; the re-intaked
ConditionReport.vehicle should
match. Not enforced at the model
layer — operator responsibility
to inspect the correct unit.
A future validation layer could
tighten this at M12+.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.6 + §7 M12.6
4. `docs/handoffs/SESSION_125_m12_inc5_collections.md`
   (previous session)
5. `backend/dealer_ai/services/repossessions/`
6. `backend/dealer_ai/models.py::Repossession`
7. `backend/dealer_ai/models.py::ConditionReport`
   (M3 attach target)
