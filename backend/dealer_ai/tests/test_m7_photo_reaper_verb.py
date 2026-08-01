"""Milestone 7 · Increment 5 (SESSION_092) — photo tombstone reaper verb tests.

Locks the behavior of
:func:`services.photo_gallery.reaper.reap_tombstoned_photos`:

- Live rows (``marked_deleted_at=None``) are ignored.
- Tombstoned rows within the 30-day retention window are ignored.
- Rows past the retention window are physically deleted (both bytes
  AND row).
- Storage-first delete order — bytes gone before row gone.
- Storage failure leaves the row intact and increments the
  ``storage_failed`` counter.
- Cross-tenant isolation.
- Empty tenant returns an empty result.
- ``as_of`` defaults to ``timezone.now()``; explicit ``as_of``
  honored.
- Counters + PK lists match the deleted / failed sets.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    Dealership,
    Vehicle,
    VehiclePhoto,
)
from dealer_ai.services import photo_storage
from dealer_ai.services.photo_gallery import upload_photo
from dealer_ai.services.photo_gallery.reaper import (
    PHOTO_RETENTION_DAYS,
    ReaperResult,
    reap_tombstoned_photos,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SAMPLE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-body"


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _upload(vehicle: Vehicle, dealership: Dealership) -> VehiclePhoto:
    return upload_photo(
        vehicle,
        dealership=dealership,
        data=_SAMPLE_BYTES,
        content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
        width_px=1920,
        height_px=1080,
    )


def _tombstone_at(photo: VehiclePhoto, when: dt.datetime) -> VehiclePhoto:
    """Directly stamp ``marked_deleted_at`` — bypasses the M6.2
    :func:`mark_deleted` verb which uses ``timezone.now()`` internally
    and would ignore our test-controlled cutoff."""
    photo.marked_deleted_at = when
    photo.is_primary = False
    photo.save(
        update_fields=["marked_deleted_at", "is_primary", "updated_at"]
    )
    return photo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class RetentionConstantLocked(TestCase):
    """§5.d Option A — fixed 30-day retention."""

    def test_retention_days_is_thirty(self):
        self.assertEqual(PHOTO_RETENTION_DAYS, 30)


class LiveRowsIgnored(TestCase):
    """Rows with ``marked_deleted_at=None`` are not touched."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M75-LIVE", self.default)
        self.photo = _upload(self.vehicle, self.default)
        # Deliberately NOT tombstoned.

    def test_live_photo_not_touched(self):
        result = reap_tombstoned_photos(self.default)
        self.assertEqual(result.candidates, 0)
        self.assertEqual(result.deleted, 0)
        # Row still present.
        self.assertTrue(
            VehiclePhoto.objects.filter(pk=self.photo.pk).exists()
        )


class InRetentionWindowIgnored(TestCase):
    """Tombstoned but recent → within retention → not reaped."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M75-INRET", self.default)
        self.photo = _upload(self.vehicle, self.default)
        self.as_of = timezone.now()
        # Tombstoned 10 days ago — well within the 30-day window.
        _tombstone_at(
            self.photo, self.as_of - dt.timedelta(days=10)
        )

    def test_in_retention_not_reaped(self):
        result = reap_tombstoned_photos(self.default, as_of=self.as_of)
        self.assertEqual(result.candidates, 0)
        self.assertEqual(result.deleted, 0)
        self.assertTrue(
            VehiclePhoto.objects.filter(pk=self.photo.pk).exists()
        )

    def test_at_exact_cutoff_not_reaped(self):
        # Exactly PHOTO_RETENTION_DAYS ago → NOT past the cutoff (the
        # query uses ``__lt``, not ``__lte``).
        _tombstone_at(
            self.photo,
            self.as_of - dt.timedelta(days=PHOTO_RETENTION_DAYS),
        )
        result = reap_tombstoned_photos(self.default, as_of=self.as_of)
        self.assertEqual(result.candidates, 0)


class PastRetentionReaped(TestCase):
    """Tombstoned more than 30 days ago → physically deleted."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M75-REAP", self.default)
        self.photo = _upload(self.vehicle, self.default)
        self.as_of = timezone.now()
        _tombstone_at(
            self.photo,
            self.as_of - dt.timedelta(days=PHOTO_RETENTION_DAYS + 1),
        )
        self.photo_pk = self.photo.pk

    def test_row_deleted(self):
        result = reap_tombstoned_photos(self.default, as_of=self.as_of)
        self.assertEqual(result.candidates, 1)
        self.assertEqual(result.deleted, 1)
        self.assertEqual(result.storage_failed, 0)
        self.assertFalse(
            VehiclePhoto.objects.filter(pk=self.photo_pk).exists()
        )

    def test_deleted_photo_ids_populated(self):
        result = reap_tombstoned_photos(self.default, as_of=self.as_of)
        self.assertEqual(result.deleted_photo_ids, [self.photo_pk])
        self.assertEqual(result.storage_failed_photo_ids, [])


class StorageFirstDeleteOrder(TestCase):
    """Bytes are removed BEFORE the row (M3.5 pattern)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M75-ORDER", self.default)
        self.photo = _upload(self.vehicle, self.default)
        self.as_of = timezone.now()
        _tombstone_at(
            self.photo,
            self.as_of - dt.timedelta(days=PHOTO_RETENTION_DAYS + 1),
        )

    def test_storage_delete_called_before_row_delete(self):
        # Assert ordering by capturing state at delete_object call
        # time: the row must still exist when delete_object fires.
        photo_pk = self.photo.pk
        row_existed_when_storage_called = {"answer": False}

        original_delete_object = photo_storage.delete_vehicle_photo_object

        def _spy(storage_key):
            row_existed_when_storage_called["answer"] = (
                VehiclePhoto.objects.filter(pk=photo_pk).exists()
            )
            return original_delete_object(storage_key)

        with patch.object(photo_storage, "delete_vehicle_photo_object", side_effect=_spy):
            reap_tombstoned_photos(self.default, as_of=self.as_of)
        self.assertTrue(row_existed_when_storage_called["answer"])
        # And by end of run, the row is gone.
        self.assertFalse(
            VehiclePhoto.objects.filter(pk=photo_pk).exists()
        )


class StorageFailureLeavesRow(TestCase):
    """If storage delete raises ObjectStorageError, the row survives
    and the failure is counted."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M75-FAIL", self.default)
        self.photo = _upload(self.vehicle, self.default)
        self.as_of = timezone.now()
        _tombstone_at(
            self.photo,
            self.as_of - dt.timedelta(days=PHOTO_RETENTION_DAYS + 1),
        )

    def test_storage_error_leaves_row_and_increments_counter(self):
        with patch.object(
            photo_storage,
            "delete_vehicle_photo_object",
            side_effect=photo_storage.ObjectStorageError(
                "simulated backend failure"
            ),
        ):
            result = reap_tombstoned_photos(
                self.default, as_of=self.as_of
            )
        self.assertEqual(result.candidates, 1)
        self.assertEqual(result.deleted, 0)
        self.assertEqual(result.storage_failed, 1)
        self.assertEqual(
            result.storage_failed_photo_ids, [self.photo.pk]
        )
        # Row still exists — a subsequent run can retry.
        self.assertTrue(
            VehiclePhoto.objects.filter(pk=self.photo.pk).exists()
        )


class MidBatchStorageFailureIsolated(TestCase):
    """A storage failure on one candidate does NOT abort the batch;
    subsequent candidates still process."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.as_of = timezone.now()
        stamp = self.as_of - dt.timedelta(
            days=PHOTO_RETENTION_DAYS + 1
        )
        self.photos = []
        for stock in ("M75-BATCH-1", "M75-BATCH-2", "M75-BATCH-3"):
            v = _make_vehicle(stock, self.default)
            p = _upload(v, self.default)
            _tombstone_at(p, stamp)
            self.photos.append(p)

    def test_mid_batch_failure_processes_remaining(self):
        call_count = {"n": 0}

        original = photo_storage.delete_vehicle_photo_object

        def _fake(storage_key):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise photo_storage.ObjectStorageError(
                    "second-candidate simulated failure"
                )
            return original(storage_key)

        with patch.object(
            photo_storage, "delete_vehicle_photo_object", side_effect=_fake
        ):
            result = reap_tombstoned_photos(
                self.default, as_of=self.as_of
            )

        self.assertEqual(result.candidates, 3)
        self.assertEqual(result.deleted, 2)
        self.assertEqual(result.storage_failed, 1)
        # The second candidate's PK is in the failed list; the other
        # two are in the deleted list.
        self.assertEqual(len(result.deleted_photo_ids), 2)
        self.assertEqual(len(result.storage_failed_photo_ids), 1)


class CrossTenantIsolation(TestCase):
    """A reaper run for tenant A does not touch tenant B's photos."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other-r")

        as_of = timezone.now()
        stamp = as_of - dt.timedelta(days=PHOTO_RETENTION_DAYS + 1)

        v_def = _make_vehicle("M75-XT-DEF", self.default)
        p_def = _upload(v_def, self.default)
        _tombstone_at(p_def, stamp)
        self.def_photo_pk = p_def.pk

        v_oth = _make_vehicle("M75-XT-OTH", self.other)
        p_oth = _upload(v_oth, self.other)
        _tombstone_at(p_oth, stamp)
        self.oth_photo_pk = p_oth.pk

    def test_only_target_tenant_photos_reaped(self):
        reap_tombstoned_photos(self.default)
        # Default tenant's photo removed.
        self.assertFalse(
            VehiclePhoto.objects.filter(pk=self.def_photo_pk).exists()
        )
        # Other tenant's photo survives.
        self.assertTrue(
            VehiclePhoto.objects.filter(pk=self.oth_photo_pk).exists()
        )


class EmptyTenantReturnsEmptyResult(TestCase):
    """No tombstoned photos → zero candidates + zero deletions."""

    def test_empty_tenant(self):
        empty = Dealership.objects.create(name="Empty", slug="empty-r")
        result = reap_tombstoned_photos(empty)
        self.assertIsInstance(result, ReaperResult)
        self.assertEqual(result.candidates, 0)
        self.assertEqual(result.deleted, 0)
        self.assertEqual(result.storage_failed, 0)


class AsOfHandling(TestCase):
    """``as_of=None`` defaults to now; explicit ``as_of`` respected."""

    def test_defaults_to_now(self):
        empty = Dealership.objects.create(name="Empty", slug="empty-r2")
        before = timezone.now()
        result = reap_tombstoned_photos(empty)
        after = timezone.now()
        self.assertGreaterEqual(result.as_of, before)
        self.assertLessEqual(result.as_of, after)

    def test_explicit_as_of_stamped_on_result(self):
        empty = Dealership.objects.create(name="Empty", slug="empty-r3")
        explicit = timezone.now() - dt.timedelta(hours=1)
        result = reap_tombstoned_photos(empty, as_of=explicit)
        self.assertEqual(result.as_of, explicit)

    def test_explicit_as_of_used_for_cutoff_calculation(self):
        # A photo tombstoned 25 days before `explicit` should NOT be
        # reaped when explicit=now (25 < 30). Bumping explicit to
        # 10 days from now moves the cutoff so the same photo is
        # past retention.
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M75-ASOF", default)
        photo = _upload(vehicle, default)
        now = timezone.now()
        _tombstone_at(photo, now - dt.timedelta(days=25))

        # Under as_of=now, the photo is within retention.
        result_now = reap_tombstoned_photos(default, as_of=now)
        self.assertEqual(result_now.deleted, 0)

        # Under as_of=now+10d, the photo is 35 days past tombstone.
        future = now + dt.timedelta(days=10)
        result_future = reap_tombstoned_photos(default, as_of=future)
        self.assertEqual(result_future.deleted, 1)
