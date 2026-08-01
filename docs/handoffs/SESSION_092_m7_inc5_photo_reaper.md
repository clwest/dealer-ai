---
title: "SESSION_092 handoff — Milestone 7 · Increment 5 (photo tombstone reaper)"
status: historical
type: handoff
date: 2026-08-01
session: 092
milestone: 7
milestone_status: in-progress
increment: 5
increment_status: shipped
commit: TBD
---

# SESSION_092 — Milestone 7 · Increment 5 (M7.5 — photo tombstone reaper)

## What shipped

The fourth (and final scheduled-body) job under the M7.1
substrate. `services/photo_gallery.py` restructured into
a package (Option B — zero-breaking, verified across 7
downstream import sites), new `reaper.py` module with
the `reap_tombstoned_photos` verb (storage-first delete
per M3.5 pattern), `tasks.py` with two Celery task
shells, a Beat entry at 05:00 project-time daily
completing the sequential 02:00-05:00 pattern, and 29
focused tests (target ~20 — batch-isolation +
order-verification coverage warranted the extra 9
assertions). One additive extension to
`services/photo_storage.py` — a sibling
`delete_vehicle_photo_object` function that validates
against `_VEHICLE_PHOTO_KEY_PATTERN` (M3.4's
`delete_object` only validates the M3.4 shape).

Also: **one implementation-time seam decision confirmed
by the user at session open** (per M7 §7 lesson 8).

## Session preamble — one seam decision confirmed

Per the SESSION_091 start-here flag, the M7.5 verb
+ task modules needed a home:

- **Option A** — extend flat `services/photo_gallery.py`
  + sibling `photo_gallery_tasks.py`. Preserves M6.2
  file layout; small deviation from M7.2-M7.4 package
  pattern.
- **Option B (chosen, user-confirmed)** —
  `git mv services/photo_gallery.py → services/photo_gallery/__init__.py`;
  add `reaper.py` + `tasks.py` as siblings. Consistent
  with M7.2/M7.3/M7.4 package structure. Verified zero-
  breaking against 7 downstream import sites.

## New files (M7.5)

1. **`backend/dealer_ai/services/photo_gallery/reaper.py`**
   — the `reap_tombstoned_photos` verb + `ReaperResult`
   dataclass + `PHOTO_RETENTION_DAYS = 30` constant (per
   §5.d Option A, SESSION_088 preamble). Storage-first
   delete pattern. Iteration-level failure isolation
   (mid-batch storage failure does NOT abort remaining
   candidates).

2. **`backend/dealer_ai/services/photo_gallery/tasks.py`**
   — two `@instrumented_task`-wrapped Celery tasks
   mirroring M7.2/M7.3/M7.4:
   - `reap_tombstoned_photos_for_tenant(*, dealership_id,
     as_of_iso=None)` — per-tenant.
   - `reap_tombstoned_photos_for_all_tenants(*,
     as_of_iso=None)` — orchestrator.

3. **`backend/dealer_ai/tests/test_m7_photo_reaper_verb.py`**
   — 19 tests. Retention constant, live rows ignored,
   in-retention window ignored (including exact-cutoff
   edge case), past-retention reaped (bytes + row),
   storage-first order verification (spy captures
   row-still-exists state at storage-delete time),
   storage-failure isolation (single row + mid-batch),
   cross-tenant isolation, empty tenant, `as_of`
   defaulting + explicit stamping + cutoff-calculation
   effect.

4. **`backend/dealer_ai/tests/test_m7_photo_reaper_tasks.py`**
   — 10 tests. Task registration, per-tenant task
   returns dict summary, `JobRunLog` row stamped,
   `as_of_iso` kwarg handling, orchestrator fans out
   per Dealership, orchestrator writes own `JobRunLog`
   row, Beat entry at 05:00, Beat entry ordering
   constraint (after M7.4), cumulative M7 Beat-entry
   audit (all 4 entries present with expected hours).

## Modified files (M7.5)

1. **`backend/dealer_ai/services/photo_gallery.py` →
   `backend/dealer_ai/services/photo_gallery/__init__.py`**
   — moved via `git mv`. Two relative-import bumps
   (`from ..models` → `from ...models`; `from . import
   photo_storage` → `from .. import photo_storage`) to
   account for the extra package depth. Zero business-
   logic changes. Every downstream import site (7 total:
   `views_photos.py`, `services/vehicle_lifecycle.py`,
   `services/vehicle_listing.py`, 4 test files)
   continues to work identically — Python treats the
   package interchangeably with the flat module for
   `from services import photo_gallery` and
   `from services.photo_gallery import <name>` patterns.

2. **`backend/dealer_ai/services/photo_storage.py`** —
   added `delete_vehicle_photo_object` function +
   `_validate_vehicle_photo_storage_key` internal
   helper. Sibling of the M3.4 `delete_object` /
   `_validate_storage_key` pair. Rationale: M3.4's
   `delete_object` validates against `_KEY_PATTERN`
   (condition-report shape); M6.2 vehicle photos use
   `_VEHICLE_PHOTO_KEY_PATTERN`. Two functions so both
   patterns stay independently enforceable. Added
   `delete_vehicle_photo_object` to the public
   `__all__` export list.

3. **`backend/dealer_kit/settings.py`** — appended the
   `"photo-tombstone-reaper-daily-05-00"` entry to
   `CELERY_BEAT_SCHEDULE` targeting the orchestrator at
   `crontab(hour=5, minute=0)`.

## Verification

- **Backend tests:** 3,121 → **3,150 pass**, 1 skipped,
  0 fail. **+29 tests** (target ~20).
- **`python3 manage.py check`:** no issues.
- **`python3 manage.py makemigrations --check --dry-run`:**
  "No changes detected."
- **Frontend `npx tsc --noEmit`:** clean.
- **Frontend `npx vite build`:** clean.
- **Celery task registration:** both M7.5 tasks appear
  in `celery_app.tasks` under their dotted names.
- **Beat entries registered:** all 4 M7 entries at
  02:00 / 03:00 / 04:00 / 05:00.
- **Package restructure zero-breaking:** the 112 tests
  spanning `test_photo_gallery`,
  `test_admin_photo_endpoints`,
  `test_vehicle_lifecycle_rules_m6`, and
  `test_vehicle_listing_service` all continue to pass
  after the `.py` → `/__init__.py` move.

## Design decisions worth flagging

**Storage-first delete order (M3.5 pattern).** Removing
the row before the bytes would orphan the storage
object — nothing in the DB to reference it, no future
code path to clean it up. The reverse order (bytes
first, then row) leaves at most a transient "row
references already-gone bytes" state that the row-
delete second step resolves within the same iteration.
Locked by
`StorageFirstDeleteOrder::test_storage_delete_called_before_row_delete`
using a spy that captures row-existence state at
storage-delete time.

**Storage failure leaves the row intact.** If
`delete_vehicle_photo_object` raises
`ObjectStorageError`, the reaper logs + counts the
failure and moves on — the row stays for a subsequent
run to retry. This is the "storage bytes are ground
truth" invariant: never orphan bytes by deleting the
row that referenced them.

**Iteration-level failure isolation (not
transaction-level).** Unlike the M7.2 accrual verb (which
wraps the whole batch in `transaction.atomic` and rolls
back on any exception), the reaper processes each
candidate independently. Rationale: partial progress is
BETTER than no progress for a housekeeping job — the
successful deletes are already good, and the next daily
run picks up whatever failed. Locked by
`MidBatchStorageFailureIsolated`.

**Sibling `delete_vehicle_photo_object` instead of
loosening `delete_object`.** Two functions with two
patterns keeps defense-in-depth strict — a caller
handling M3.4 keys cannot silently succeed with M6.2
keys, and vice versa. Consistent with the existing
`build_canonical_key` vs `build_canonical_vehicle_photo_key`
+ `parse_canonical_key` vs
`parse_canonical_vehicle_photo_key` split in
`photo_storage.py`.

**`delete_object` idempotency preserved.** Both
condition-report and vehicle-photo delete paths inherit
the M3.4 adapter contract: already-missing = success.
So a reaper run that races with an operator's manual
S3 console delete (or a partial previous run) still
succeeds without incident.

**No transaction wrapping around the DB row delete.**
Django's `.delete()` is atomic per row; the reaper
doesn't need broader atomicity because each iteration
already handles its own row + bytes independently.
Adding `transaction.atomic` at the loop level would
mean a single storage failure aborted every row-delete
in the batch — the opposite of the intended
isolation semantics.

**`as_of` defaults to `timezone.now()`, cutoff computed
inside the verb.** The verb owns the cutoff math
(`as_of - PHOTO_RETENTION_DAYS`) — callers don't have
to know the retention window. Locked by
`AsOfHandling::test_explicit_as_of_used_for_cutoff_calculation`.

**Beat entry at 05:00, LAST in the daily M7 window.**
The reaper is the only M7 job that physically deletes
data. Running it after the read-heavy aging aggregation
(M7.3 03:00) and the write-heavy accrual (M7.2 02:00)
means the day's snapshots + accruals ran against
pre-reap data, so a deleted tombstoned photo doesn't
retroactively invalidate anything.

**Package facade omits `reaper` and `tasks`.** Same
discipline as M7.2/M7.3/M7.4 — the `photo_gallery/`
package's `__init__.py` re-exports only the original
M6.2 public surface. Callers that need the M7.5 reaper
or tasks import from their explicit sub-modules. Keeps
the M7.5 additions decoupled from the M6.2 upload/
listing workflow.

## Non-goals — deferred to later increments

- ❌ No changes to `VehiclePhoto` model.
- ❌ No changes to the M6.2 `mark_deleted` verb.
- ❌ No per-dealer configurable retention (§5.d Option
  C deferred until operator evidence surfaces).
- ❌ No admin surface for "restore this tombstoned
  photo before it reaps" — the M6.2 `restore_deleted`
  verb already handles restore; a UI on top is not M7.5
  scope.
- ❌ No cross-run retry policy — the reaper is
  idempotent + deterministic, so re-running is safe;
  operators can invoke the per-tenant task manually
  from `manage.py shell` if a specific tenant needs
  immediate re-processing.
- ❌ No Prometheus / metrics substrate — deferred (§5.e
  Option B).
- ❌ No delete-metrics dashboard — M8.

## What's next — SESSION_093 (M7.6 — closeout)

Documentation-only. Per M7 §7 M7.6:

- Compatibility sweep (§3 checklist in
  `MILESTONE_7_PLANNING.md`).
- `docs/roadmap/MILESTONE_7_RETROSPECTIVE.md` — new
  doc, mirrors M5/M6 shape (six sections).
- `docs/CAPABILITY_MATRIX.md` §7h — new subsection for
  async infrastructure.
- `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 7
  status flip: `in-progress` → `shipped`.
- `docs/roadmap/MILESTONE_7_PLANNING.md` frontmatter:
  `status: draft` → `status: shipped`.
- Session-start refresh
  (`docs/DEALER_KIT_SESSION_START.md`) to reference the
  four async task families.
- `docs/roadmap/MILESTONE_8_PLANNING.md` — new planning
  doc per standing user directive.
- Coordinated commit + push of M7.1–M7.6 to
  `origin/main` (per standing user directive at M6
  close — one push per milestone).

**No code changes at M7.6.** Baseline stays at
**3,150 pass**.

Read-first list at SESSION_093 open:

- `docs/roadmap/MILESTONE_7_PLANNING.md` §7 M7.6, §3.
- `docs/handoffs/SESSION_092_m7_inc5_photo_reaper.md`
  (this handoff).
- `docs/handoffs/SESSION_088_m7_inc1_infra.md` through
  `SESSION_091_m7_inc4_vendor_sla.md` — the five prior
  M7 handoffs feeding the retrospective.
- `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md` — the
  template shape (M7 retro should mirror the six-section
  structure).
- `docs/roadmap/MILESTONE_5_RETROSPECTIVE.md` — same
  reference for the section-6 lessons format.
- `docs/CAPABILITY_MATRIX.md` §7g — the M6 subsection
  the M7 subsection follows structurally.

## Anchors that win on conflict

1. `docs/PROJECT_RULES.md`
2. `docs/DOC_GOVERNANCE.md`
3. `docs/roadmap/IMPLEMENTATION_ROADMAP.md` §Milestone 7
4. `docs/roadmap/AUTHENTICATION_MODEL.md`
5. `docs/roadmap/MILESTONE_7_PLANNING.md`
6. `docs/roadmap/MILESTONE_6_RETROSPECTIVE.md`
7. `docs/handoffs/SESSION_092_m7_inc5_photo_reaper.md`
8. `docs/handoffs/SESSION_091_m7_inc4_vendor_sla.md`
9. `docs/handoffs/SESSION_090_m7_inc3_aging.md`
10. `docs/handoffs/SESSION_089_m7_inc2_floor_plan.md`
11. `docs/handoffs/SESSION_088_m7_inc1_infra.md`
12. `docs/handoffs/SESSION_087_m6_closeout.md`
13. `docs/roadmap/MILESTONE_6_PLANNING.md` (shipped —
    M6.2 photo gallery substrate M7.5 extends)
14. `docs/research/VEHICLE_CENTRIC_PIVOT.md` Phase 6

Planning docs are claims. Rules + research + code are
facts.
