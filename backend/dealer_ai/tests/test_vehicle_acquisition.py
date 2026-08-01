"""Milestone 2 · Increment 1 — VehicleAcquisition model tests.

Persistence-layer coverage only. No business logic tested — the M2.1
scope boundary defers service-layer semantics (`compute_totals`,
`record_acquisition`, computed properties on Vehicle) to Increment 2.

Locked invariants:

- Field shape (choices enforcement, decimal precision, date required).
- OneToOne uniqueness (a vehicle has at most one acquisition record).
- Dealership FK NOT NULL (schema-level, inherited from Increment 3
  pattern — every M2 model carries a dealership FK from day one).
- Cross-tenant contamination guard (`clean()` raises when
  `acquisition.dealership != vehicle.dealership`).
- Cascade on Vehicle delete (deleting a vehicle removes its
  acquisition record — cost history + operational trail should not
  survive the identity being removed).
- Ordering (recent acquisitions surface first).
- ``__str__`` for the Django admin display.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from dealer_ai.models import (
    ACQUISITION_SOURCE_CHOICES,
    SOURCE_AUCTION,
    SOURCE_FLEET,
    SOURCE_OFF_LEASE,
    SOURCE_PRIVATE,
    SOURCE_RENTAL,
    SOURCE_REPO,
    SOURCE_TRADE,
    SOURCE_WHOLESALE,
    Dealership,
    Vehicle,
    VehicleAcquisition,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    """Factory: minimal Vehicle for tests that only care about the FK.

    Kept private to this file — every M2 model test file will build
    its own minimal fixture. When a shared fixture surfaces
    (SESSION_047 M2.2 will build service-layer tests that need the
    same shape), lift into ``tests/_ledger_helpers.py``.
    """
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


class SourceChoicesVocabulary(TestCase):
    """The eight canonical acquisition sources are enumerated in the
    planning doc §1.1 and INVENTORY_ACQUISITION_MAPPING.md §2. Any
    addition or rename requires a roadmap decision — this test forces
    that conversation.
    """

    def test_choices_contain_exactly_eight_canonical_sources(self):
        keys = {key for key, _ in ACQUISITION_SOURCE_CHOICES}
        self.assertEqual(
            keys,
            {
                SOURCE_AUCTION,
                SOURCE_TRADE,
                SOURCE_WHOLESALE,
                SOURCE_PRIVATE,
                SOURCE_OFF_LEASE,
                SOURCE_RENTAL,
                SOURCE_REPO,
                SOURCE_FLEET,
            },
        )


class VehicleAcquisitionCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-CREATE", self.default)

    def test_round_trip_all_fields(self):
        acq = VehicleAcquisition.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            source_detail="Manheim Phoenix, lane 4, run #217",
            purchase_price=Decimal("18500.00"),
            purchase_date=dt.date(2026, 5, 12),
            buyer_fees=Decimal("475.00"),
            arbitration_fees=Decimal("0"),
            transportation_cost=Decimal("850.00"),
            title_acquisition_cost=Decimal("125.00"),
            notes="Frame check passed. Right rear tire near wear bar.",
        )
        fetched = VehicleAcquisition.objects.get(pk=acq.pk)
        self.assertEqual(fetched.vehicle_id, self.vehicle.pk)
        self.assertEqual(fetched.source, SOURCE_AUCTION)
        self.assertEqual(fetched.purchase_price, Decimal("18500.00"))
        self.assertEqual(fetched.purchase_date, dt.date(2026, 5, 12))
        self.assertEqual(fetched.buyer_fees, Decimal("475.00"))
        self.assertEqual(fetched.transportation_cost, Decimal("850.00"))

    def test_defaults_when_optional_fields_omitted(self):
        acq = VehicleAcquisition.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            source=SOURCE_TRADE,
            purchase_price=Decimal("9500.00"),
            purchase_date=dt.date(2026, 6, 1),
        )
        # Every fee field defaults to zero — trades typically have no
        # buyer / arbitration / transportation / title-acquisition
        # cost at the acquisition event itself.
        self.assertEqual(acq.buyer_fees, Decimal("0"))
        self.assertEqual(acq.arbitration_fees, Decimal("0"))
        self.assertEqual(acq.transportation_cost, Decimal("0"))
        self.assertEqual(acq.title_acquisition_cost, Decimal("0"))
        self.assertEqual(acq.source_detail, "")
        self.assertEqual(acq.notes, "")

    def test_source_full_clean_rejects_invalid_choice(self):
        acq = VehicleAcquisition(
            vehicle=self.vehicle,
            dealership=self.default,
            source="carfax",  # not a valid choice
            purchase_price=Decimal("15000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        with self.assertRaises(ValidationError):
            acq.full_clean()


class OneToOneUniqueness(TestCase):
    """A single vehicle has at most one acquisition record. Second insert
    against the same vehicle must fail at the DB layer — matches the
    planning §1.1 design note ("OneToOne is correct: the acquisition
    event is unique per unit")."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-1TO1", self.default)
        VehicleAcquisition.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            source=SOURCE_WHOLESALE,
            purchase_price=Decimal("12000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )

    def test_second_acquisition_for_same_vehicle_fails(self):
        with self.assertRaises(IntegrityError):
            VehicleAcquisition.objects.create(
                vehicle=self.vehicle,
                dealership=self.default,
                source=SOURCE_PRIVATE,
                purchase_price=Decimal("11500.00"),
                purchase_date=dt.date(2026, 6, 1),
            )


class DealershipRequired(TestCase):
    """Dealership FK is NOT NULL from day one (greenfield table, no
    backfill). Every M2 write must supply it explicitly (the pre_save
    autofill in `services/tenancy.py` covers only the six M1 carriers
    — M2 tables are NOT registered with that fallback per the M2
    planning §7 scope discipline)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-DEAL", self.default)

    def test_omitting_dealership_raises(self):
        # Django surfaces missing NOT NULL FKs as IntegrityError at
        # insert time (SQLite) or a validation-time RelatedObjectDoesNotExist,
        # depending on driver. Both are acceptable failure modes.
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                VehicleAcquisition.objects.create(
                    vehicle=self.vehicle,
                    source=SOURCE_AUCTION,
                    purchase_price=Decimal("15000.00"),
                    purchase_date=dt.date(2026, 5, 1),
                )

    def test_dealership_field_is_not_null_at_schema_level(self):
        # Locks the invariant that M2 tables carry a NOT NULL dealership
        # FK from day one — mirrors the M1 · Increment 3 test
        # ``test_fk_is_now_not_null`` for the six original carriers.
        self.assertFalse(
            VehicleAcquisition._meta.get_field("dealership").null,
            "VehicleAcquisition.dealership should be NOT NULL from day one",
        )


class CrossTenantClean(TestCase):
    """The denormalized ``dealership`` FK on VehicleAcquisition must
    match the parent Vehicle's tenant. ``clean()`` is the model-layer
    guard against a mis-scoped view writing an acquisition for the
    wrong tenant. See ``AUTHENTICATION_MODEL.md`` §1 layer 4."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown"
        )
        self.vehicle_at_a = _make_vehicle("M21-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        acq = VehicleAcquisition(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            source=SOURCE_OFF_LEASE,
            purchase_price=Decimal("22000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        # Should not raise — happy path.
        acq.full_clean()

    def test_mismatched_dealership_raises_validation_error(self):
        acq = VehicleAcquisition(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,  # wrong tenant
            source=SOURCE_OFF_LEASE,
            purchase_price=Decimal("22000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            acq.full_clean()
        # The error attaches to the 'dealership' field so admin /
        # future API surfaces render it inline.
        self.assertIn("dealership", ctx.exception.message_dict)


class CascadeOnVehicleDelete(TestCase):
    """Deleting a Vehicle removes its VehicleAcquisition. The stock
    number is the vehicle's identity; when the identity goes away the
    ledger records for that identity go with it (there is no
    'orphan acquisition' concept)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-CASC", self.default)
        self.acq = VehicleAcquisition.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            source=SOURCE_RENTAL,
            purchase_price=Decimal("13000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )

    def test_delete_vehicle_removes_acquisition(self):
        acq_pk = self.acq.pk
        self.vehicle.delete()
        self.assertFalse(
            VehicleAcquisition.objects.filter(pk=acq_pk).exists()
        )


class ReverseRelation(TestCase):
    """The OneToOne related_name is ``acquisition`` on Vehicle, per
    the planning §1.1. Locks the accessor future ledger UI + service
    layer will use (``vehicle.acquisition``)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-REV", self.default)
        self.acq = VehicleAcquisition.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            source=SOURCE_REPO,
            purchase_price=Decimal("8500.00"),
            purchase_date=dt.date(2026, 5, 1),
        )

    def test_vehicle_dot_acquisition_returns_the_record(self):
        # Refetch to bypass ORM cache — proves the reverse accessor
        # works through a fresh query.
        vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertEqual(vehicle.acquisition.pk, self.acq.pk)

    def test_dealership_reverse_relation_works(self):
        # Custom related_name ``vehicle_acquisitions`` on Dealership
        # (planning §1.1 shape). Locks the accessor.
        self.assertIn(
            self.acq, self.default.vehicle_acquisitions.all()
        )


class OrderingContract(TestCase):
    """Newer acquisitions surface first (``-purchase_date, -created_at``).
    The operator's default view is 'what came in most recently?'."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicles = [
            _make_vehicle(f"M21-ORD-{i}", self.default) for i in range(3)
        ]
        # Create in mixed date order to verify the ORM ordering (not
        # insertion order) surfaces the newest first.
        VehicleAcquisition.objects.create(
            vehicle=self.vehicles[0],
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("10000.00"),
            purchase_date=dt.date(2026, 3, 1),
        )
        VehicleAcquisition.objects.create(
            vehicle=self.vehicles[1],
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("10000.00"),
            purchase_date=dt.date(2026, 6, 15),
        )
        VehicleAcquisition.objects.create(
            vehicle=self.vehicles[2],
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("10000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )

    def test_default_ordering_surfaces_newest_first(self):
        dates = [a.purchase_date for a in VehicleAcquisition.objects.all()]
        self.assertEqual(
            dates,
            [
                dt.date(2026, 6, 15),
                dt.date(2026, 5, 1),
                dt.date(2026, 3, 1),
            ],
        )


class StringRepresentation(TestCase):
    """__str__ is what Django admin renders in list views. Locks the
    shape so admin surfaces stay readable across renames."""

    def test_str_contains_stock_number_and_source(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M21-STR-STOCK", default)
        acq = VehicleAcquisition.objects.create(
            vehicle=vehicle,
            dealership=default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        as_string = str(acq)
        self.assertIn("M21-STR-STOCK", as_string)
        # Source display label, not the raw string — get_source_display
        # returns "Auction" for SOURCE_AUCTION.
        self.assertIn("Auction", as_string)
