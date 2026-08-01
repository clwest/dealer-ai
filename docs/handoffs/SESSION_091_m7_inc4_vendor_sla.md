---
title: "SESSION_091 handoff — Milestone 7 · Increment 4 (vendor SLA warning job)"
status: historical
type: handoff
date: 2026-08-01
session: 091
milestone: 7
milestone_status: in-progress
increment: 4
increment_status: shipped
commit: TBD
---

# SESSION_091 — Milestone 7 · Increment 4 (M7.4 — vendor SLA warnings)

## What shipped

The third scheduled job body under the M7.1 substrate.
A new `services/vendor_sla/` package containing the
detection verb (SLA policy encoded as three constants +
per-status rule dispatch), two Celery task shells
mirroring the M7.2/M7.3 pattern, a Beat schedule entry
at 04:00 project-time daily (continuing the
non-overlapping window pattern), and 34 focused tests
(target ~20 — rule coverage warranted the extra 14
assertions). **No new models. No new migrations.**

Also: **three implementation-time decisions confirmed
by the user at session open** (per M7 §7 lesson 8)
before code was written. §1.4 in
`MILESTONE_7_PLANNING.md` had no `[NEEDS-DECISION-BEFORE-M7.4]`
items but did leave three knobs open; surfacing them
early followed the SESSION_075 / SESSION_082 preamble
precedent.

## Session preamble — three decisions locked

Per §1.4 (planning leaves these to implementation):

1. **Approved-stale threshold: 7 days.**
   `APPROVED_STALE_THRESHOLD_DAYS = 7` in
   `services/vendor_sla/detection.py`. Confirmed as
   typical vendor-turnaround expectation; conservative
   enough to avoid first-day alert fatigue, aggressive
   enough to catch true stalls within a week.

2. **In-progress ETA grace: 0 days.**
   `IN_PROGRESS_ETA_GRACE_DAYS = 0`. The warning fires
   on the first day past ETA. No grace period —
   `estimated_completion_date < today` is the
   operator's promise to the operator, and missing it
   is the signal.

3. **Scope: `venue='outsourced'` only.** In-house WOs
   are excluded. Rationale: "vendor SLA" implies
   applying vendor pressure; in-house delays are a
   different operational problem (dispatch / capacity)
   and mixing them into one warning stream dilutes
   signal. In-house tech-delay detection can land
   later as its own job.

No planning amendments were required — the three
decisions were implementation-time choices, not
`[NEEDS-DECISION-BEFORE-M7.4]` items. Documented here
so future readers understand why the M7.4 constants
have the values they do.

## New files (M7.4)

1. **`backend/dealer_ai/services/vendor_sla/__init__.py`**
   — package facade. Re-exports `detect_sla_breaches`,
   `SlaBreach`, `SlaBreachReport`,
   `APPROVED_STALE_THRESHOLD_DAYS`, and
   `IN_PROGRESS_ETA_GRACE_DAYS`. Tasks kept out of the
   facade for the same import-cycle discipline as
   M7.2/M7.3.

2. **`backend/dealer_ai/services/vendor_sla/detection.py`**
   — the detection verb + three constants + breach-kind
   string constants + `SlaBreach` frozen dataclass +
   `SlaBreachReport` dataclass. Two rule branches
   (`_classify_in_progress`, `_classify_approved`) with
   documented rule-precedence semantics (only one status
   can be active at a time, so precedence is exercised
   only in the "hypothetical dual match" test).

3. **`backend/dealer_ai/services/vendor_sla/tasks.py`**
   — two `@instrumented_task`-wrapped Celery tasks
   mirroring M7.2/M7.3:
   - `detect_sla_breaches_for_tenant(*, dealership_id,
     as_of_iso=None)` — per-tenant. One `JobRunLog`
     row per invocation stamped with `dealership_id`.
     Returns JSON-safe dict summary.
   - `detect_sla_breaches_for_all_tenants(*,
     as_of_iso=None)` — orchestrator. Fans out via
     `.delay()`.

4. **`backend/dealer_ai/tests/test_m7_vendor_sla_verb.py`**
   — 24 tests. Policy constants locked, empty tenant,
   in-progress past ETA (with day-of / day-before / day-
   after / no-ETA cases), approved-stale (past / at-
   threshold / no-approved-at cases), terminal +
   cancelled + draft statuses excluded, in-house venue
   excluded, rule precedence, cross-tenant isolation,
   WARNING log emission with structured message, `as_of`
   defaulting + explicit stamping, dataclass re-exports.

5. **`backend/dealer_ai/tests/test_m7_vendor_sla_tasks.py`**
   — 10 tests. Task registration by dotted name, per-
   tenant task returns dict summary, `JobRunLog` row
   stamped, `as_of_iso` kwarg handling, orchestrator
   fans out per Dealership, orchestrator writes own
   `JobRunLog` row, Beat entry registered at 04:00,
   Beat entry ordering constraint (after M7.3).

## Modified files (M7.4)

1. **`backend/dealer_kit/settings.py`** — appended the
   `"vendor-sla-scan-daily-04-00"` entry to
   `CELERY_BEAT_SCHEDULE` targeting the orchestrator at
   `crontab(hour=4, minute=0)`.

## Verification

- **Backend tests:** 3,087 → **3,121 pass**, 1 skipped,
  0 fail. **+34 tests** (target ~20).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **Frontend `npx tsc --noEmit`:** clean.
- **Frontend `npx vite build`:** clean.
- **Celery task registration:** both M7.4 tasks appear
  in `celery_app.tasks` under their dotted names.
- **Beat entries registered:** M7.2 (02:00) + M7.3
  (03:00) + M7.4 (04:00).

## Design decisions worth flagging

**Read-only verb.** The detection verb writes NOTHING to
the DB. Every breach turns into a `logging.WARNING`
record; the audit trail lives in the log stream + the
`JobRunLog` row for the invocation itself. Rationale
per §1.4: "Emits log records at WARNING level; Milestone
8 dashboards will consume the log aggregation. **No
email / SMS / phone-call notification in M7 v1** —
those channels are Milestone 11+ vendor-integration
territory." A future notification-channel substrate
would layer on top of the log stream without touching
the verb.

**Rule precedence is defensive, not exercised.** The
`_classify` dispatcher picks rule 1 first (`in_progress`)
then rule 2 (`approved`). Because a single WO can only
have one `status` at a time, real WOs never satisfy
both rules simultaneously. The rule-precedence test
(`RulePrecedence::test_in_progress_wins_over_approved_stale`)
constructs a WO with `status='in_progress'` AND a
stale `approved_at` to prove the dispatcher does not
misclassify it — but the "both rules match" scenario
is hypothetical. Kept as a locked contract so future
extensions (e.g. re-approval workflows that keep an
`approved_at` while flipping status back) surface here.

**Missing `estimated_completion_date` is not a breach.**
An `in_progress` WO without an ETA is a data-quality
issue (the M4.2 service should have prompted the
operator for an ETA at approval time). Making it an
SLA breach would flag every WO an operator forgot to
date — bad signal. Locked at
`InProgressPastEtaFlagged::test_missing_eta_not_flagged`.

**Missing `approved_at` on `status='approved'` is not
a breach.** Similarly a data-integrity issue that the
M4.2 service should have prevented (approving a WO
without stamping the timestamp is a bug). Making it
an SLA breach would double-report the underlying bug.
Locked at
`ApprovedStaleFlagged::test_missing_approved_at_not_flagged`.

**`breach_days` semantics.**
- For `in_progress_past_eta`: `(as_of - eta).days`. A
  WO past ETA by 1 day reports `breach_days=1`.
- For `approved_stale`: `(as_of - approved_at.date()).days`.
  A WO approved 8 days ago reports `breach_days=8`.
Both variants are signed the same way (positive = worse)
so downstream dashboards can sort them together.

**`SlaBreach` carries `work_order` reference.** Frozen
dataclass with `compare=False, repr=False` on the FK
so equality + repr stay clean, but callers get direct
access to the WO for follow-up queries without another
DB round-trip. Consistent with the M7.3 `SnapshotResult`
shape.

**Query is `select_related("vehicle", "vendor")`.**
Every breach record needs `vehicle.stock_number` +
`vendor.name` for the log message. Without the
`select_related` each breach would trigger two extra
queries — for a scan that turns up dozens of breaches
on a busy dealer, the difference is 40+ queries per
run vs 1 per run.

**`venue='outsourced'` filtering happens in the query.**
The `WorkOrder.objects.filter(venue=..., status__in=(...))`
constraint keeps the in-house rows out of the Python
loop entirely — cheaper than filtering after fetch.

**Non-terminal status filter.** The query constrains
`status__in=(approved, in_progress)` — completed +
cancelled + draft are excluded at the SQL level. A
terminal WO with a past ETA is not a breach (the work
is done); a draft WO's clock hasn't started (no
approval provenance yet).

**Package facade omits `tasks`.** Consistent with
M7.2/M7.3 discipline — the package's `__init__.py`
re-exports the verb + dataclasses + constants but not
the Celery tasks. Callers that need the tasks import
from `services.vendor_sla.tasks` directly.

## Non-goals — deferred to later increments

- ❌ No email / SMS / phone-call notification channels
  — Milestone 11+.
- ❌ No SLA policy configuration UI — hard-coded
  constants for v1 per SESSION_091 preamble.
- ❌ No per-dealer configurability — deferred until
  operator evidence surfaces need. Extension shape
  documented in `detection.py`.
- ❌ No in-house tech-delay detection — scope confirmed
  outsourced-only at SESSION_091 open.
- ❌ No `SlaBreach`-model persistence — breaches live
  in the log stream; the log aggregation is the M8
  dashboard's input.
- ❌ No photo tombstone reaper (M7.5).
- ❌ No changes to `WorkOrder` model — read-only.

## What's next — SESSION_092 (M7.5)

Photo tombstone reaper — the M7.2 pattern applied to
the M6.2 photo-gallery substrate. New
`services/photo_gallery.py::reap_tombstoned_photos`
verb (per §1.5 — extends the existing M6.2 service).
Celery task shells + Beat schedule entry at 05:00
daily. Storage-first delete pattern (M3.5). ~20 tests.
Baseline 3,121 → ~3,141.

Read-first list at SESSION_092 open:

- `docs/roadmap/MILESTONE_7_PLANNING.md` §1.5, §7 M7.5.
- `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
  (this handoff).
- `backend/dealer_ai/services/photo_gallery.py` — the
  M6.2 service the M7.5 reaper extends.
- `backend/dealer_ai/services/photo_storage.py` —
  M3.4/M6.2 storage primitive (`delete_object`).
- `backend/dealer_ai/models.py::VehiclePhoto` — the
  M6.2 model with `marked_deleted_at` tombstone
  timestamp.
- `backend/dealer_ai/services/vendor_sla/` — the M7.4
  package as the layout template.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 7
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_7_PLANNING.md`
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
8. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
9. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
10. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
11. `docs/handoffs/SESSION_087_m6_closeout.md`
12. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 6
13. `docs/research/RECON_MAPPING.md` §pain #12
    (the operational pain M7.4 solves — recon ETAs
    don't match reality)

Planning docs are claims. Rules + research + code are
facts.
