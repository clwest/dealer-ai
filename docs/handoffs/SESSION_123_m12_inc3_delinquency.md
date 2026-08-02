---
title: "SESSION_123 handoff — Milestone 12 · Increment 3 (M12.3 — Delinquency detection + aging buckets)"
status: historical
type: handoff
date: 2026-08-02
session: 123
milestone: 12
milestone_status: in_progress
increment: 3
increment_status: shipped
commit: TBD
---

# SESSION_123 — Milestone 12 · Increment 3 (M12.3 — Delinquency detection + aging buckets)

## What shipped

Aging math + state-transitioning
Celery detector per
`MILESTONE_12_PLANNING.md` §1.3 +
§5.c Option A (7-value vocab locked
at SESSION_121 open).

Additive-column extension to
`BhphNote` (no new entity) +
`services/bhph_delinquency/`
package (pure compute + Celery
detector) + beat schedule at 08:00
project-time daily.

**Three §0.a M12.3 open decisions
recorded as-recommended:**

1. **Aging measurement source** —
   from the earliest unpaid
   scheduled due date (not from
   grace expiry). Matches BHPH
   portfolio reporting convention.
2. **New note column defaults** —
   `current_bucket = "current"`,
   `days_past_due = 0`. Detector
   recomputes.
3. **Detector idempotency scope**
   — match M11.5 pattern
   (idempotent within a run; only
   writes when derived value
   differs from stored).

Streak stands at **41 planning-time
as-recommended M5.1 → M12.1** (§0.a
implementation-time decisions don't
count against streak per M10 §9).

## By the numbers

- **Backend baseline: 4,024 pass, 1
  skipped, 0 fail** (was 3,986 at
  M12.2 close — **+38 tests, 0
  regressions**).
- **Frontend Vitest baseline: 67
  pass** (unchanged — no frontend
  at M12.3).
- **Migrations `0039`**
  (`0039_m123_bhph_note_aging_columns`
  — additive column-adds; no new
  entity).
- **Tenancy carriers: 41**
  (unchanged — additive columns
  on existing BhphNote).
- **DRF admin surface: 86**
  (unchanged — no new endpoints
  at M12.3; portfolio surfaces
  land at M12.7).
- **Frontend operator routes:** 15
  (unchanged).
- **Permission classes: 8**
  (unchanged).
- **`Vehicle.is_available`:**
  unchanged.
- **Celery-beat task families:
  6 → 7** (new M12.3 detector
  registered at 08:00 daily —
  next slot after M11.5 07:00).

## Files touched

### New
- `backend/dealer_ai/services/bhph_delinquency/__init__.py`
- `backend/dealer_ai/services/bhph_delinquency/compute.py`
  (three pure verbs)
- `backend/dealer_ai/services/bhph_delinquency/tasks.py`
  (per-tenant task + orchestrator)
- `backend/dealer_ai/migrations/0039_m123_bhph_note_aging_columns.py`
- `backend/dealer_ai/tests/test_m123_bhph_delinquency_compute.py`
  (25 tests)
- `backend/dealer_ai/tests/test_m123_bhph_delinquency_model.py`
  (2 tests)
- `backend/dealer_ai/tests/test_m123_bhph_delinquency_detector.py`
  (11 tests)
- `docs/handoffs/SESSION_123_m12_inc3_delinquency.md`
  (this file)

### Modified
- `backend/dealer_ai/models.py` — added
  `BhphNote.current_bucket` +
  `BhphNote.days_past_due` + 7-
  value aging vocab constants.
- `backend/dealer_kit/settings.py`
  — registered
  `bhph-delinquency-detector-daily-08-00`
  in `CELERY_BEAT_SCHEDULE`.
- `00-START-NEXT-SESSION.md` —
  flipped to SESSION_124 · M12.4
  priority.

## Aging vocab + boundaries

Fixed 7-value vocab per §5.c
Option A:

| Bucket                 | Days past due |
| ---------------------- | ------------- |
| `current`              | 0             |
| `1_15`                 | 1–15          |
| `16_30`                | 16–30         |
| `31_60`                | 31–60         |
| `61_90`                | 61–90         |
| `over_90`              | 91–119        |
| `charge_off_candidate` | 120+          |

Charge-off transition itself is
**M12.5+ operator scope** — this
bucket is a flag surfacing the
candidate, not an automatic state
change.

## Detector semantics

### Idempotent per run
Only writes when derived value
differs from stored. Runs on the
same day produce identical output.
Locked by
`test_detector_is_idempotent_within_run`.

### Cadence-aware next-due
projection
Uses M12.1
`_BHPH_NOTE_PERIOD_DAYS`
(weekly=7, biweekly=14,
semi_monthly=15). No schedule DB
read needed — the projection is
pure math from
`first_payment_due`,
`payment_frequency`,
`payments_made`.

### Grace respect
On-or-before
`next_expected + default_grace_days`
→ `days_past_due = 0`. Past that
→ aging clock starts from the
scheduled date (not from grace
expiry), matching BHPH portfolio
reporting norms.

### Fully-paid short-circuit
`outstanding_balance == 0` or
`payments_made >= term_periods`
→ `current`, 0. Paid-off notes
stay `current` regardless of
elapsed dates.

### Cross-tenant isolation
Per-tenant task queries
`BhphNote.objects.filter(dealership=…)`
and never touches sibling
dealerships. Locked by
`test_notes_isolated_across_dealerships`.

## Non-goals honored

- ❌ No PTP tracking (M12.4).
- ❌ No collections (M12.5).
- ❌ No repossession (M12.6).
- ❌ No portfolio analytics or UI
  (M12.7).
- ❌ No configurable bucket
  boundaries (§5.c constant).
- ❌ No auto-charge-off transitions
  — `charge_off_candidate` is a
  flag; state transition is
  M12.5+ operator scope.
- ❌ No collection contact log
  (M12.5).
- ❌ No portfolio bucket rollup
  surface — the histogram is
  logged from the task; endpoint
  surfaces land at M12.7.

## Design notes worth remembering

### Additive-column extension, not new entity
BhphNote's aging state (bucket +
days_past_due) is inherent to the
note itself, not a separate
lifecycle record. Denormalizing at
the row is faster for reads (no
join) and simpler for downstream
analytics. If a M12.7+ audit trail
of bucket transitions surfaces
operator need, a separate
`BhphAgingSnapshot` history entity
could layer on without breaking
this.

### Split pure verbs from Celery task
`bucket_for_days`,
`next_expected_due`,
`days_past_due_for` are pure —
tested with `SimpleTestCase`.
Detector task orchestrates DB
reads + writes but delegates all
math to the pure verbs. Same
posture as M12.2
`allocate_payment` vs
`record_payment`.

### 08:00 slot after M11.5 07:00
Non-overlapping-window pattern
preserved (M7.2 02:00, M7.3 03:00,
M7.4 04:00, M7.5 05:00, M11.4
06:00, M11.5 07:00, M12.3 08:00).

### Frozen-time test pattern
`_patch_today` returns a real
aware `datetime` (not a shim
object) because `patch` mutates
the shared `django.utils.timezone`
module — a shim leaks into
`auto_now` DateTimeField writes.
Locked as a working pattern for
future date-sensitive detector
tests.

## Anchors

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/MILESTONE_12_PLANNING.md`
   §1.3 + §5.c + §7 M12.3
4. `docs/handoffs/SESSION_122_m12_inc2_bhph_payment.md`
   (previous session)
5. `docs/handoffs/SESSION_121_m12_inc1_bhph_note.md`
6. `backend/dealer_ai/services/bhph_delinquency/compute.py`
7. `backend/dealer_ai/services/bhph_delinquency/tasks.py`
8. `backend/dealer_ai/models.py::BhphNote`
   (aging columns)
