"""Milestone 6 · Increment 2 (SESSION_083) — photo gallery service tests.

Covers the six public verbs in :mod:`services.photo_gallery`:

- :func:`upload_photo` — bytes → storage backend → VehiclePhoto row.
- :func:`set_primary` — atomic swap of the vehicle's primary hero.
- :func:`reorder` — bulk sort_order update.
- :func:`mark_deleted` — safer-direction deletion.
- :func:`restore_deleted` — reverse of mark_deleted.
- :func:`listing_ready_count` — M6.4 predicate feeder.

Plus the four distinct domain-error classes (CrossTenantPhotoError,
PhotoValidationError, PhotoAlreadyDeletedError, PhotoNotDeletedError).

Uses the local FileSystemStorage backend (dev/test default) via
:mod:`services.photo_storage`. No S3, no boto3 mocking — the M6.2
storage extension has its own test file.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dealer_ai.models import (
    Dealership,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    Vehicle,
    VehiclePhoto,
)
from dealer_ai.services.photo_gallery import (
    CrossTenantPhotoError,
    LISTING_READY_MIN_HEIGHT_PX,
    LISTING_READY_MIN_WIDTH_PX,
    LISTING_READY_PHOTO_COUNT,
    PhotoAlreadyDeletedError,
    PhotoNotDeletedError,
    PhotoValidationError,
    listing_ready_count,
    mark_deleted,
    reorder,
    restore_deleted,
    set_primary,
    upload_photo,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


_SAMPLE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-body"


class ModuleConstants(TestCase):
    """The dimension threshold + count threshold are load-bearing
    per SESSION_083 §3 Option A + §5.b Option C. Locked here."""

    def test_dimension_threshold_1024_x_768(self):
        self.assertEqual(LISTING_READY_MIN_WIDTH_PX, 1024)
        self.assertEqual(LISTING_READY_MIN_HEIGHT_PX, 768)

    def test_photo_count_threshold_eight(self):
        self.assertEqual(LISTING_READY_PHOTO_COUNT, 8)


class UploadPhoto(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62UP-A", self.default)

    def test_creates_photo_row_and_persists_bytes(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="uploader", password="pw12345678"
        )
        photo = upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1920,
            height_px=1080,
            actor=actor,
            sort_order=0,
            caption="Front three-quarter",
        )
        self.assertIsNotNone(photo.pk)
        self.assertEqual(photo.vehicle_id, self.vehicle.pk)
        self.assertEqual(photo.dealership_id, self.default.pk)
        self.assertEqual(photo.width_px, 1920)
        self.assertEqual(photo.height_px, 1080)
        self.assertEqual(photo.caption, "Front three-quarter")
        self.assertEqual(photo.uploaded_by_id, actor.pk)
        self.assertFalse(photo.is_primary)  # NOT set here per contract
        self.assertRegex(
            photo.storage_key,
            r"^dealerships/default/vehicles/M62UP-A/photos/"
            r"[0-9a-f-]+/original$",
        )
        # public_id embedded in the storage_key must match the row's public_id.
        self.assertIn(str(photo.public_id), photo.storage_key)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-up")
        with self.assertRaises(CrossTenantPhotoError):
            upload_photo(
                self.vehicle,
                dealership=other,
                data=_SAMPLE_BYTES,
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                width_px=800,
                height_px=600,
            )

    def test_non_positive_dimensions_refused(self):
        with self.assertRaises(PhotoValidationError):
            upload_photo(
                self.vehicle,
                dealership=self.default,
                data=_SAMPLE_BYTES,
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                width_px=0,
                height_px=600,
            )
        with self.assertRaises(PhotoValidationError):
            upload_photo(
                self.vehicle,
                dealership=self.default,
                data=_SAMPLE_BYTES,
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                width_px=800,
                height_px=-1,
            )


class SetPrimary(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62SP-A", self.default)
        self.photo_a = upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1920,
            height_px=1080,
        )
        self.photo_b = upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1920,
            height_px=1080,
        )

    def test_first_set_primary_flips_flag(self):
        set_primary(self.photo_a, dealership=self.default)
        self.photo_a.refresh_from_db()
        self.assertTrue(self.photo_a.is_primary)

    def test_second_set_primary_swaps_atomically(self):
        set_primary(self.photo_a, dealership=self.default)
        set_primary(self.photo_b, dealership=self.default)
        self.photo_a.refresh_from_db()
        self.photo_b.refresh_from_db()
        self.assertFalse(self.photo_a.is_primary)
        self.assertTrue(self.photo_b.is_primary)
        # At most one primary invariant.
        primaries = VehiclePhoto.objects.filter(
            vehicle=self.vehicle, is_primary=True
        )
        self.assertEqual(primaries.count(), 1)

    def test_set_primary_on_deleted_photo_refused(self):
        mark_deleted(self.photo_a, dealership=self.default)
        with self.assertRaises(PhotoValidationError):
            set_primary(self.photo_a, dealership=self.default)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-sp")
        with self.assertRaises(CrossTenantPhotoError):
            set_primary(self.photo_a, dealership=other)


class Reorder(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62RE-A", self.default)
        self.photos = [
            upload_photo(
                self.vehicle,
                dealership=self.default,
                data=_SAMPLE_BYTES,
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                width_px=1024,
                height_px=768,
                sort_order=index,
            )
            for index in range(3)
        ]

    def test_reorder_updates_sort_order_per_list(self):
        # Reverse the ordering: [p2, p1, p0]
        reversed_pks = [p.pk for p in reversed(self.photos)]
        result = reorder(
            self.vehicle,
            dealership=self.default,
            ordered_photo_pks=reversed_pks,
        )
        self.assertEqual([r.pk for r in result], reversed_pks)
        for expected_sort_order, pk in enumerate(reversed_pks):
            photo = VehiclePhoto.objects.get(pk=pk)
            self.assertEqual(photo.sort_order, expected_sort_order)

    def test_reorder_rejects_duplicate_pks(self):
        with self.assertRaises(PhotoValidationError):
            reorder(
                self.vehicle,
                dealership=self.default,
                ordered_photo_pks=[
                    self.photos[0].pk,
                    self.photos[0].pk,
                ],
            )

    def test_reorder_rejects_pk_not_on_this_vehicle(self):
        other_vehicle = _make_vehicle("M62RE-OTHER", self.default)
        other_photo = upload_photo(
            other_vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        with self.assertRaises(PhotoValidationError):
            reorder(
                self.vehicle,
                dealership=self.default,
                ordered_photo_pks=[self.photos[0].pk, other_photo.pk],
            )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-re")
        with self.assertRaises(CrossTenantPhotoError):
            reorder(
                self.vehicle,
                dealership=other,
                ordered_photo_pks=[self.photos[0].pk],
            )


class MarkDeleted(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62MD-A", self.default)
        self.photo = upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1024,
            height_px=768,
        )

    def test_stamps_marked_deleted_at_and_actor(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="deleter", password="pw12345678"
        )
        result = mark_deleted(
            self.photo, dealership=self.default, actor=actor
        )
        self.assertIsNotNone(result.marked_deleted_at)
        self.assertEqual(result.deleted_by_id, actor.pk)
        # Row still exists — safer-direction deletion.
        self.assertTrue(VehiclePhoto.objects.filter(pk=self.photo.pk).exists())

    def test_clears_primary_flag(self):
        set_primary(self.photo, dealership=self.default)
        self.photo.refresh_from_db()
        self.assertTrue(self.photo.is_primary)
        mark_deleted(self.photo, dealership=self.default)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.is_primary)

    def test_second_mark_delete_refused(self):
        mark_deleted(self.photo, dealership=self.default)
        with self.assertRaises(PhotoAlreadyDeletedError):
            mark_deleted(self.photo, dealership=self.default)

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-md")
        with self.assertRaises(CrossTenantPhotoError):
            mark_deleted(self.photo, dealership=other)


class RestoreDeleted(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62RD-A", self.default)
        self.photo = upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1024,
            height_px=768,
        )
        mark_deleted(self.photo, dealership=self.default)

    def test_clears_marked_deleted_at_and_deleted_by(self):
        result = restore_deleted(self.photo, dealership=self.default)
        self.assertIsNone(result.marked_deleted_at)
        self.assertIsNone(result.deleted_by_id)

    def test_does_not_restore_primary_flag(self):
        """Contract: restore is a delete-reversal, not an auto-elect.
        Operator must explicitly re-elect via set_primary."""
        restore_deleted(self.photo, dealership=self.default)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.is_primary)

    def test_restore_of_non_deleted_photo_refused(self):
        restore_deleted(self.photo, dealership=self.default)
        with self.assertRaises(PhotoNotDeletedError):
            restore_deleted(self.photo, dealership=self.default)


class ListingReadyCount(TestCase):
    """M6.4 predicate feeder — counts photos meeting the dimension
    threshold, excluding marked-deleted rows."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62LR-A", self.default)

    def _upload(self, width, height):
        return upload_photo(
            self.vehicle,
            dealership=self.default,
            data=_SAMPLE_BYTES,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=width,
            height_px=height,
        )

    def test_zero_when_no_photos(self):
        self.assertEqual(
            listing_ready_count(self.vehicle, dealership=self.default), 0
        )

    def test_counts_photos_at_or_above_threshold(self):
        self._upload(1024, 768)  # exactly threshold — counts
        self._upload(1920, 1080)  # above — counts
        self.assertEqual(
            listing_ready_count(self.vehicle, dealership=self.default), 2
        )

    def test_excludes_photos_below_threshold(self):
        self._upload(1023, 768)  # width one below — excluded
        self._upload(1024, 767)  # height one below — excluded
        self._upload(1024, 768)  # exactly threshold — counts
        self.assertEqual(
            listing_ready_count(self.vehicle, dealership=self.default), 1
        )

    def test_excludes_marked_deleted_photos(self):
        self._upload(1920, 1080)
        p2 = self._upload(1920, 1080)
        mark_deleted(p2, dealership=self.default)
        self.assertEqual(
            listing_ready_count(self.vehicle, dealership=self.default), 1
        )

    def test_cross_tenant_refused(self):
        other = Dealership.objects.create(name="Other", slug="other-lr")
        with self.assertRaises(CrossTenantPhotoError):
            listing_ready_count(self.vehicle, dealership=other)
