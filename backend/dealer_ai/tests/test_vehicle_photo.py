"""Milestone 6 · Increment 1 (SESSION_082) — VehiclePhoto persistence tests.

Persistence-layer coverage only. Service-layer semantics (upload,
set-primary, reorder, mark-deleted, restore-deleted, listing-ready
count) land at M6.2 per ``MILESTONE_6_PLANNING.md`` §1.4 + §7 M6.2.

Locked invariants:

- Three canonical content-type choices per §1.1 (JPEG / PNG / WebP);
  HEIC deliberately not shipped (unlike M3.1 ``CONDITION_PHOTO_CONTENT_TYPE_CHOICES``).
- Many-per-Vehicle (ForeignKey, not OneToOne).
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean()`` guard walks ``vehicle.dealership``.
- ``storage_key`` unique at DB layer.
- ``uploaded_by`` + ``deleted_by`` provenance nullable + SET_NULL.
- Safer-direction deletion: ``marked_deleted_at`` + ``deleted_by``
  nullable by default; setting them does not remove the row.
- ``is_primary`` defaults to False (service-layer invariant, not DB).
- CASCADE on vehicle delete.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    VEHICLE_PHOTO_CONTENT_TYPE_CHOICES,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    VEHICLE_PHOTO_CONTENT_TYPE_PNG,
    VEHICLE_PHOTO_CONTENT_TYPE_WEBP,
    Vehicle,
    VehiclePhoto,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


class VehiclePhotoContentTypeVocabulary(TestCase):
    """Three canonical MIME values per §1.1 — narrower than M3.1's
    ``CONDITION_PHOTO_CONTENT_TYPE_CHOICES`` (which includes HEIC).
    Rationale: vehicle photos are customer-facing marketing content
    served through the M6.5 showroom endpoint; HEIC has poor
    cross-browser support."""

    def test_choices_contain_exactly_three_canonical_types(self):
        keys = {key for key, _ in VEHICLE_PHOTO_CONTENT_TYPE_CHOICES}
        self.assertEqual(
            keys,
            {
                VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                VEHICLE_PHOTO_CONTENT_TYPE_PNG,
                VEHICLE_PHOTO_CONTENT_TYPE_WEBP,
            },
        )
        self.assertEqual(len(VEHICLE_PHOTO_CONTENT_TYPE_CHOICES), 3)

    def test_heic_deliberately_not_shipped(self):
        """§1.1 excluded HEIC — customer-facing content served via
        M6.5 showroom, and HEIC lacks broad browser support."""
        keys = {key for key, _ in VEHICLE_PHOTO_CONTENT_TYPE_CHOICES}
        self.assertNotIn("image/heic", keys)


class VehiclePhotoCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M61VP-CREATE", self.default)

    def test_round_trip_all_fields(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="photo_actor", password="pw12345678"
        )
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/hero/original.jpg",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=1920,
            height_px=1080,
            sort_order=1,
            is_primary=True,
            caption="Front three-quarter",
            uploaded_by=actor,
        )
        fetched = VehiclePhoto.objects.get(pk=photo.pk)
        self.assertEqual(fetched.vehicle_id, self.vehicle.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(
            fetched.storage_key,
            "dealerships/default/vehicle-photos/hero/original.jpg",
        )
        self.assertEqual(fetched.content_type, VEHICLE_PHOTO_CONTENT_TYPE_JPEG)
        self.assertEqual(fetched.width_px, 1920)
        self.assertEqual(fetched.height_px, 1080)
        self.assertEqual(fetched.sort_order, 1)
        self.assertTrue(fetched.is_primary)
        self.assertEqual(fetched.caption, "Front three-quarter")
        self.assertEqual(fetched.uploaded_by_id, actor.pk)
        self.assertIsNone(fetched.marked_deleted_at)
        self.assertIsNone(fetched.deleted_by_id)

    def test_defaults_produce_sane_shape(self):
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/2/original.png",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_PNG,
            width_px=800,
            height_px=600,
        )
        self.assertEqual(photo.sort_order, 0)
        self.assertFalse(photo.is_primary)
        self.assertEqual(photo.caption, "")
        self.assertIsNone(photo.uploaded_by_id)
        self.assertIsNone(photo.marked_deleted_at)
        self.assertIsNone(photo.deleted_by_id)

    def test_invalid_content_type_rejected(self):
        photo = VehiclePhoto(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/bad/original",
            content_type="image/heic",  # excluded per §1.1
            width_px=100,
            height_px=100,
        )
        with self.assertRaises(ValidationError):
            photo.full_clean()

    def test_uploaded_by_nullable_and_set_null_on_user_delete(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="photo_uploader_delete", password="pw12345678"
        )
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/3/original.webp",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_WEBP,
            width_px=1200,
            height_px=900,
            uploaded_by=actor,
        )
        actor.delete()
        photo.refresh_from_db()
        self.assertIsNone(photo.uploaded_by_id)


class VehiclePhotoManyPerVehicle(TestCase):
    """Photos are ForeignKey (many-per-Vehicle), not OneToOne. Gallery
    behavior: multiple photos per vehicle allowed."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M61VP-MANY", self.default)

    def test_multiple_photos_per_vehicle_allowed(self):
        for i in range(3):
            VehiclePhoto.objects.create(
                vehicle=self.vehicle,
                dealership=self.default,
                storage_key=f"dealerships/default/vehicle-photos/many/{i}",
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
                width_px=1024,
                height_px=768,
                sort_order=i,
            )
        self.assertEqual(self.vehicle.photos.count(), 3)

    def test_cascade_on_vehicle_delete(self):
        VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/cascade/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        self.vehicle.delete()
        self.assertEqual(VehiclePhoto.objects.count(), 0)


class VehiclePhotoDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            VehiclePhoto._meta.get_field("dealership").null,
            "VehiclePhoto.dealership should be NOT NULL from day one",
        )


class VehiclePhotoCrossTenantClean(TestCase):
    """``dealership`` must match the vehicle's tenant. Same shape as
    ``VehicleStage.clean`` and ``ConditionFindingPhoto.clean``."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-vp"
        )
        self.vehicle_at_a = _make_vehicle("M61VP-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        photo = VehiclePhoto(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            storage_key="dealerships/default/vehicle-photos/xt-ok/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        photo.full_clean()  # should not raise

    def test_mismatched_dealership_raises_validation_error(self):
        photo = VehiclePhoto(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,
            storage_key="dealerships/rivertown/vehicle-photos/xt-bad/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        with self.assertRaises(ValidationError) as ctx:
            photo.full_clean()
        self.assertIn("dealership", ctx.exception.error_dict)


class VehiclePhotoStorageKeyUnique(TestCase):
    """``storage_key`` is unique at DB layer — every row corresponds to
    a distinct stored object."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M61VP-UNIQ", self.default)

    def test_duplicate_storage_key_raises_integrity_error(self):
        VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/dup/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VehiclePhoto.objects.create(
                    vehicle=self.vehicle,
                    dealership=self.default,
                    storage_key="dealerships/default/vehicle-photos/dup/original",
                    content_type=VEHICLE_PHOTO_CONTENT_TYPE_PNG,
                    width_px=100,
                    height_px=100,
                )


class VehiclePhotoSaferDirectionDeletion(TestCase):
    """The M6.2 delete gesture stamps ``marked_deleted_at`` + ``deleted_by``
    rather than removing the row. Persistence layer verifies the fields
    are nullable by default and record who initiated the delete."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M61VP-DELETION", self.default)

    def test_marking_deleted_does_not_remove_row(self):
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/deletion/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        User = get_user_model()
        actor = User.objects.create_user(
            username="photo_deleter", password="pw12345678"
        )
        photo.marked_deleted_at = timezone.now()
        photo.deleted_by = actor
        photo.save()
        # Row still exists in DB — safer-direction deletion.
        self.assertTrue(VehiclePhoto.objects.filter(pk=photo.pk).exists())
        fetched = VehiclePhoto.objects.get(pk=photo.pk)
        self.assertIsNotNone(fetched.marked_deleted_at)
        self.assertEqual(fetched.deleted_by_id, actor.pk)

    def test_deleted_by_set_null_on_user_delete(self):
        User = get_user_model()
        actor = User.objects.create_user(
            username="photo_deleter_delete", password="pw12345678"
        )
        photo = VehiclePhoto.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            storage_key="dealerships/default/vehicle-photos/setnull/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
            marked_deleted_at=timezone.now(),
            deleted_by=actor,
        )
        actor.delete()
        photo.refresh_from_db()
        # marked_deleted_at survives; deleted_by nulled per SET_NULL.
        self.assertIsNotNone(photo.marked_deleted_at)
        self.assertIsNone(photo.deleted_by_id)


class VehiclePhotoIsPrimaryDefault(TestCase):
    """``is_primary`` defaults False. The M6.2 service enforces the
    "at most one primary per vehicle" invariant; the persistence layer
    only enforces the default."""

    def test_is_primary_defaults_false(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M61VP-PRIMARY", default)
        photo = VehiclePhoto.objects.create(
            vehicle=vehicle,
            dealership=default,
            storage_key="dealerships/default/vehicle-photos/prim/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        self.assertFalse(photo.is_primary)


class VehiclePhotoOrderingAndStr(TestCase):
    """Deterministic ordering by (sort_order, uploaded_at) + human-
    readable str shape."""

    def test_ordering_is_sort_order_then_uploaded_at(self):
        self.assertEqual(
            VehiclePhoto._meta.ordering, ("sort_order", "uploaded_at")
        )

    def test_str_contains_pk_and_vehicle_id_and_primary_marker(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M61VP-STR", default)
        photo = VehiclePhoto.objects.create(
            vehicle=vehicle,
            dealership=default,
            storage_key="dealerships/default/vehicle-photos/str/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
            is_primary=True,
        )
        s = str(photo)
        self.assertIn(f"#{photo.pk}", s)
        self.assertIn(f"#{vehicle.pk}", s)
        self.assertIn("[primary]", s)

    def test_str_contains_deleted_marker_when_marked(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M61VP-STRDEL", default)
        photo = VehiclePhoto.objects.create(
            vehicle=vehicle,
            dealership=default,
            storage_key="dealerships/default/vehicle-photos/strdel/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
            marked_deleted_at=timezone.now(),
        )
        self.assertIn("[deleted]", str(photo))
