"""Milestone 6 · Increment 1 (SESSION_082) — VehicleListing persistence tests.

Persistence-layer coverage only. Service-layer semantics (draft →
approved → published → unpublished transitions, LLM invocation, safety
scrub) land at M6.3 per ``MILESTONE_6_PLANNING.md`` §1.4 + §7 M6.3.

Locked invariants:

- Four canonical status choices per §5.a Option A (user-confirmed at
  SESSION_082): draft / approved / published / unpublished.
- OneToOne with Vehicle — a second listing on the same vehicle raises
  IntegrityError.
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean()`` guard walks ``vehicle.dealership``.
- All actor-provenance FKs nullable + SET_NULL (drafted_by,
  approved_by, published_by, unpublished_by).
- All timestamp fields nullable except created_at / updated_at
  (auto-managed).
- ``status`` defaults to ``draft``.
- Reverse accessor ``Vehicle.listing`` returns the OneToOne row.
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
    VEHICLE_LISTING_STATUS_APPROVED,
    VEHICLE_LISTING_STATUS_CHOICES,
    VEHICLE_LISTING_STATUS_DRAFT,
    VEHICLE_LISTING_STATUS_PUBLISHED,
    VEHICLE_LISTING_STATUS_UNPUBLISHED,
    Vehicle,
    VehicleListing,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


class VehicleListingStatusVocabulary(TestCase):
    """Four canonical statuses per §5.a Option A (user-confirmed at
    SESSION_082 open)."""

    def test_choices_contain_exactly_four_canonical_statuses(self):
        keys = {key for key, _ in VEHICLE_LISTING_STATUS_CHOICES}
        self.assertEqual(
            keys,
            {
                VEHICLE_LISTING_STATUS_DRAFT,
                VEHICLE_LISTING_STATUS_APPROVED,
                VEHICLE_LISTING_STATUS_PUBLISHED,
                VEHICLE_LISTING_STATUS_UNPUBLISHED,
            },
        )
        self.assertEqual(len(VEHICLE_LISTING_STATUS_CHOICES), 4)

    def test_archived_is_not_a_shipped_status_value(self):
        """§5.a Option A rejected the Option C 5-state vocabulary
        that would have added ``archived``. Shipping a state the
        M6.3 service always rejects would be dishonest."""
        keys = {key for key, _ in VEHICLE_LISTING_STATUS_CHOICES}
        self.assertNotIn("archived", keys)


class VehicleListingCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M61VL-CREATE", self.default)

    def test_round_trip_all_fields(self):
        User = get_user_model()
        drafter = User.objects.create_user(
            username="listing_drafter", password="pw12345678"
        )
        approver = User.objects.create_user(
            username="listing_approver", password="pw12345678"
        )
        publisher = User.objects.create_user(
            username="listing_publisher", password="pw12345678"
        )
        now = timezone.now()
        listing = VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_PUBLISHED,
            title="2024 Ford Escape SEL",
            body="Well-equipped 2024 Escape with low miles.",
            source_provenance={
                "sentence_0": "vehicle.year",
                "sentence_1": "vehicle.model",
            },
            drafted_by=drafter,
            drafted_at=now,
            approved_by=approver,
            approved_at=now,
            published_by=publisher,
            published_at=now,
        )
        fetched = VehicleListing.objects.get(pk=listing.pk)
        self.assertEqual(fetched.vehicle_id, self.vehicle.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.status, VEHICLE_LISTING_STATUS_PUBLISHED)
        self.assertEqual(fetched.title, "2024 Ford Escape SEL")
        self.assertIn("Well-equipped", fetched.body)
        self.assertEqual(
            fetched.source_provenance,
            {"sentence_0": "vehicle.year", "sentence_1": "vehicle.model"},
        )
        self.assertEqual(fetched.drafted_by_id, drafter.pk)
        self.assertEqual(fetched.approved_by_id, approver.pk)
        self.assertEqual(fetched.published_by_id, publisher.pk)
        self.assertEqual(fetched.drafted_at, now)
        self.assertEqual(fetched.approved_at, now)
        self.assertEqual(fetched.published_at, now)
        self.assertIsNone(fetched.unpublished_by_id)
        self.assertIsNone(fetched.unpublished_at)
        self.assertEqual(fetched.unpublished_reason, "")

    def test_status_defaults_to_draft(self):
        listing = VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
        )
        self.assertEqual(listing.status, VEHICLE_LISTING_STATUS_DRAFT)

    def test_defaults_produce_empty_shape(self):
        listing = VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
        )
        self.assertEqual(listing.title, "")
        self.assertEqual(listing.body, "")
        self.assertEqual(listing.source_provenance, {})
        self.assertIsNone(listing.drafted_by_id)
        self.assertIsNone(listing.drafted_at)
        self.assertIsNone(listing.approved_by_id)
        self.assertIsNone(listing.approved_at)
        self.assertIsNone(listing.published_by_id)
        self.assertIsNone(listing.published_at)
        self.assertIsNone(listing.unpublished_by_id)
        self.assertIsNone(listing.unpublished_at)
        self.assertEqual(listing.unpublished_reason, "")

    def test_invalid_status_rejected(self):
        listing = VehicleListing(
            vehicle=self.vehicle,
            dealership=self.default,
            status="archived",  # Option C rejected
        )
        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_actor_fks_nullable_and_set_null_on_user_delete(self):
        User = get_user_model()
        drafter = User.objects.create_user(
            username="listing_actor_delete", password="pw12345678"
        )
        listing = VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_DRAFT,
            drafted_by=drafter,
            drafted_at=timezone.now(),
        )
        drafter.delete()
        listing.refresh_from_db()
        self.assertIsNone(listing.drafted_by_id)


class VehicleListingOneToOneEnforcement(TestCase):
    """OneToOne means at most one listing per vehicle — the second write
    raises IntegrityError, not silently overwrites."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M61VL-1TO1", self.default)

    def test_second_listing_on_same_vehicle_raises(self):
        VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                VehicleListing.objects.create(
                    vehicle=self.vehicle,
                    dealership=self.default,
                )

    def test_reverse_accessor_returns_the_listing_row(self):
        listing = VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_APPROVED,
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.listing.pk, listing.pk)


class VehicleListingDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            VehicleListing._meta.get_field("dealership").null,
            "VehicleListing.dealership should be NOT NULL from day one",
        )


class VehicleListingCrossTenantClean(TestCase):
    """``dealership`` must match the vehicle's tenant. Same shape as
    ``VehicleStage.clean``."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-vl"
        )
        self.vehicle_at_a = _make_vehicle("M61VL-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        listing = VehicleListing(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
        )
        listing.full_clean()  # should not raise

    def test_mismatched_dealership_raises_validation_error(self):
        listing = VehicleListing(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,
        )
        with self.assertRaises(ValidationError) as ctx:
            listing.full_clean()
        self.assertIn("dealership", ctx.exception.error_dict)


class VehicleListingCascadeOnVehicleDelete(TestCase):
    def test_listing_removed_when_vehicle_deleted(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M61VL-CASCADE", default)
        listing = VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=default,
        )
        listing_pk = listing.pk
        vehicle.delete()
        self.assertFalse(VehicleListing.objects.filter(pk=listing_pk).exists())


class VehicleListingUnpublishedReasonOptional(TestCase):
    """``unpublished_reason`` is an operator note captured at unpublish
    time. Nullable-string semantics: default empty, non-blank when
    provided."""

    def test_unpublished_reason_captured_when_provided(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M61VL-UNPUB", default)
        listing = VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=default,
            status=VEHICLE_LISTING_STATUS_UNPUBLISHED,
            unpublished_at=timezone.now(),
            unpublished_reason="Vehicle sold pending paperwork.",
        )
        listing.refresh_from_db()
        self.assertEqual(
            listing.unpublished_reason,
            "Vehicle sold pending paperwork.",
        )


class VehicleListingOrderingAndStr(TestCase):
    """Deterministic ordering by ``-updated_at`` + human-readable str."""

    def test_ordering_is_updated_at_descending(self):
        self.assertEqual(VehicleListing._meta.ordering, ("-updated_at",))

    def test_str_contains_status_display_and_vehicle_id(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M61VL-STR", default)
        listing = VehicleListing.objects.create(
            vehicle=vehicle,
            dealership=default,
            status=VEHICLE_LISTING_STATUS_PUBLISHED,
        )
        s = str(listing)
        self.assertIn("Published", s)
        self.assertIn(f"#{vehicle.pk}", s)
