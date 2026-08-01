"""Milestone 7 · Increment 5 (SESSION_092) — tombstoned-photo reaper.

The tenant-scoped service verb that physically removes
:class:`VehiclePhoto` rows tombstoned by the M6.2 :func:`mark_deleted`
verb more than :data:`PHOTO_RETENTION_DAYS` ago. Bytes are removed
first (via :func:`services.photo_storage.delete_object`), then the row.
If storage removal fails, the row is left intact and the failure is
counted + logged — a follow-up run can retry.

**Chosen at §5.d Option A** (SESSION_088 preamble): fixed 30-day
retention window for v1. Per-dealer configurability (§5.d Option C) is
a deliberate M7.5 non-goal.

**Storage-first delete (M3.5 pattern).** Removing the row before the
bytes would orphan the storage object — nothing left in the DB
references it, so no future code path could clean it up. The reverse
order (bytes first, then row) leaves at most a "row references
already-gone bytes" transient state, which the row-delete second step
resolves within the same iteration. If the DB write fails after a
successful storage delete, the next reaper run will re-process the
row (bytes already gone → :func:`delete_object`'s idempotent
"already-missing = success" path holds).

**What this module does NOT own:**

- Celery task decoration + tenant fan-out — that lives in
  :mod:`.tasks`.
- Broker / Beat schedule wiring — ``dealer_kit/settings.py``.
- Deciding which photos to tombstone — that's the M6.2
  :func:`mark_deleted` verb. The reaper only processes rows the
  operator (or a future automation) has already tombstoned.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.5 +
§5.d (Option A) + §7 M7.5.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

from ...models import Dealership, VehiclePhoto
from .. import photo_storage


# ---------------------------------------------------------------------------
# Retention policy constant
# ---------------------------------------------------------------------------

# Fixed 30-day retention per §5.d Option A. Long enough for accidental-
# delete recovery via M6.2's :func:`restore_deleted`; short enough to
# keep storage costs bounded. Per-dealer configurability is a
# deliberate non-goal for v1 (§5.d Option C deferred). If operator
# evidence surfaces need, the extension shape is a
# ``DealerOnboardingProfile.photo_retention_days`` override resolved
# via ``services.dealer_config``.
PHOTO_RETENTION_DAYS = 30


_LOGGER = logging.getLogger("dealer_ai.photo_gallery.reaper")


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class ReaperResult:
    """Execution summary for one reaper run.

    - ``candidates`` — rows the query matched (tombstoned + past
      retention). Sum of ``deleted`` + ``storage_failed``.
    - ``deleted`` — rows where both bytes AND row were removed.
    - ``storage_failed`` — rows where the storage delete raised.
      The row stays; a subsequent run retries.
    - ``deleted_photo_ids`` — successfully-deleted PKs (useful for
      audit + tests).
    - ``storage_failed_photo_ids`` — PKs of rows the storage delete
      failed on. Correlate with structured log stream.
    """

    dealership_slug: str
    as_of: dt.datetime
    candidates: int = 0
    deleted: int = 0
    storage_failed: int = 0
    deleted_photo_ids: list[int] = field(default_factory=list)
    storage_failed_photo_ids: list[int] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public verb
# ---------------------------------------------------------------------------


def reap_tombstoned_photos(
    dealership: Dealership,
    *,
    as_of: Optional[dt.datetime] = None,
) -> ReaperResult:
    """Physically delete tombstoned photos past the retention window.

    Parameters
    ----------
    dealership : Dealership
        The tenant whose tombstoned photos are candidates. Required —
        the verb is single-tenant; the M7.5 orchestrator handles
        multi-tenant fan-out.
    as_of : datetime, optional
        Reference time for the retention cutoff. Defaults to
        ``timezone.now()``. Explicit values enable deterministic
        testing and backfill scenarios.

    Returns
    -------
    ReaperResult
        Contains the counters + PK lists documented on the dataclass.

    Notes
    -----
    Not atomic across the batch. Each candidate is processed
    independently: bytes-then-row within one iteration, but a failure
    on candidate #5 does NOT roll back candidates #1-#4. Rationale:
    partial progress is BETTER than no progress for a housekeeping
    job — the successful deletes are already good, and the next run
    will re-attempt the failed row.
    """
    if as_of is None:
        as_of = timezone.now()

    cutoff = as_of - dt.timedelta(days=PHOTO_RETENTION_DAYS)

    result = ReaperResult(
        dealership_slug=dealership.slug,
        as_of=as_of,
    )

    # Every VehiclePhoto tombstoned more than PHOTO_RETENTION_DAYS ago.
    # Ordered by pk for deterministic processing order (helps
    # test reasoning + operator log-inspection).
    candidates = list(
        VehiclePhoto.objects.filter(
            dealership=dealership,
            marked_deleted_at__isnull=False,
            marked_deleted_at__lt=cutoff,
        ).order_by("pk")
    )
    result.candidates = len(candidates)

    for photo in candidates:
        pk = photo.pk
        storage_key = photo.storage_key
        try:
            # Storage-first delete (M3.5 pattern). The M6.2 vehicle-
            # photo delete path is a sibling of the M3.4 condition-
            # photo :func:`photo_storage.delete_object` — both are
            # idempotent (already-missing = success), both raise
            # ObjectStorageError on real backend faults. Two functions
            # so the two key patterns stay independently validated.
            photo_storage.delete_vehicle_photo_object(storage_key)
        except photo_storage.ObjectStorageError as exc:
            _LOGGER.error(
                "photo_reaper.storage_failed dealership=%s photo_id=%d "
                "storage_key=%s error=%r",
                dealership.slug,
                pk,
                storage_key,
                exc,
            )
            result.storage_failed += 1
            result.storage_failed_photo_ids.append(pk)
            continue

        # Bytes gone (or already gone). Now remove the row.
        photo.delete()
        result.deleted += 1
        result.deleted_photo_ids.append(pk)
        _LOGGER.info(
            "photo_reaper.deleted dealership=%s photo_id=%d "
            "storage_key=%s",
            dealership.slug,
            pk,
            storage_key,
        )

    _LOGGER.info(
        "photo_reaper.completed dealership=%s candidates=%d deleted=%d "
        "storage_failed=%d",
        dealership.slug,
        result.candidates,
        result.deleted,
        result.storage_failed,
    )
    return result
