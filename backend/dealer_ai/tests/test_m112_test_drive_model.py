"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive model tests.

Locks the schema surface of :class:`dealer_ai.models.TestDrive` per
``MILESTONE_11_PLANNING.md`` §1.2 + §5.c Option A.

Coverage:

- Meta ordering (``-driven_at``).
- Default column values (``objections_captured``, ``route_notes``,
  ``customer_reaction``, ``next_action``).
- ``clean()`` cross-tenant guard for both ``lead`` and ``vehicle``
  FKs.
- CASCADE cleanup on ``lead`` / ``vehicle`` delete.
- SET_NULL preservation on ``driven_by_user`` delete.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CustomerLead,
    Dealership,
    TestDrive,
    Vehicle,
)


User = get_user_model()


def _make_vehicle(dealership: Dealership, stock: str = "TD-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("38500.00"),
        dealership=dealership,
    )


class TestDriveDefaultsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="td-defaults", name="TD Defaults"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Wanda"
        )
        self.vehicle = _make_vehicle(self.dealership)

    def test_defaults_are_empty_or_null(self) -> None:
        drive = TestDrive.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_at=timezone.now(),
        )
        self.assertEqual(drive.objections_captured, [])
        self.assertEqual(drive.route_notes, "")
        self.assertEqual(drive.customer_reaction, "")
        self.assertEqual(drive.next_action, "")
        self.assertIsNone(drive.duration_minutes)
        self.assertIsNone(drive.driven_by_user)

    def test_ordering_is_reverse_driven_at(self) -> None:
        earlier = TestDrive.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_at=timezone.now() - dt.timedelta(hours=2),
        )
        later = TestDrive.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_at=timezone.now(),
        )
        ordered = list(TestDrive.objects.all())
        self.assertEqual(ordered, [later, earlier])


class TestDriveCrossTenantCleanTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="td-clean-a", name="TD Clean A"
        )
        self.other = Dealership.objects.create(
            slug="td-clean-b", name="TD Clean B"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local Lisa"
        )
        self.vehicle = _make_vehicle(self.dealership, "TD-A-1")
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross Cara"
        )
        self.cross_vehicle = _make_vehicle(self.other, "TD-B-1")

    def test_clean_rejects_cross_tenant_lead(self) -> None:
        drive = TestDrive(
            dealership=self.dealership,
            lead=self.cross_lead,
            vehicle=self.vehicle,
            driven_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            drive.clean()
        self.assertIn("lead", ctx.exception.message_dict)

    def test_clean_rejects_cross_tenant_vehicle(self) -> None:
        drive = TestDrive(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.cross_vehicle,
            driven_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            drive.clean()
        self.assertIn("vehicle", ctx.exception.message_dict)


class TestDriveCascadeAndSetNullTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="td-cascade", name="TD Cascade"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Cascadia"
        )
        self.vehicle = _make_vehicle(self.dealership, "TD-C-1")
        self.user = User.objects.create_user(
            username="td-driver", password="x"
        )
        self.drive = TestDrive.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_by_user=self.user,
            driven_at=timezone.now(),
        )

    def test_lead_delete_cascades_drive(self) -> None:
        self.lead.delete()
        self.assertFalse(TestDrive.objects.filter(pk=self.drive.pk).exists())

    def test_vehicle_delete_cascades_drive(self) -> None:
        self.vehicle.delete()
        self.assertFalse(TestDrive.objects.filter(pk=self.drive.pk).exists())

    def test_user_delete_sets_driven_by_null(self) -> None:
        self.user.delete()
        self.drive.refresh_from_db()
        self.assertIsNone(self.drive.driven_by_user)
