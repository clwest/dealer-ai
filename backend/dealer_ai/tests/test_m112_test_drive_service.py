"""Milestone 11 · Increment 2 (SESSION_115) — TestDrive service tests.

Locks :func:`services.test_drives.record_test_drive` per
``MILESTONE_11_PLANNING.md`` §1.2 + §5.c Option A.

Coverage:

- Happy path sets every field.
- Minimal call uses defaults + default ``driven_at`` ≈ ``now()``.
- Cross-tenant lead / vehicle raises
  :class:`CrossTenantTestDriveError`.
- ``objections_captured`` JSON list persists round-trip.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CustomerLead,
    Dealership,
    TestDrive,
    Vehicle,
)
from dealer_ai.services.test_drives import (
    CrossTenantTestDriveError,
    record_test_drive,
)


User = get_user_model()


def _make_vehicle(dealership: Dealership, stock: str = "SVC-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("36000.00"),
        dealership=dealership,
    )


class RecordTestDriveHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="td-svc", name="TD Svc"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Sarah Salesee"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.driver = User.objects.create_user(
            username="td-svc-driver", password="x"
        )

    def test_full_field_write(self) -> None:
        when = timezone.now() - dt.timedelta(hours=1)
        drive = record_test_drive(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_by_user=self.driver,
            driven_at=when,
            duration_minutes=45,
            route_notes="Highway loop via I-8",
            customer_reaction="Loved the visibility",
            objections_captured=["Price too high", "Wants leather"],
            next_action="Follow up with pricing sheet by EOD",
        )
        self.assertEqual(drive.dealership_id, self.dealership.id)
        self.assertEqual(drive.lead_id, self.lead.id)
        self.assertEqual(drive.vehicle_id, self.vehicle.id)
        self.assertEqual(drive.driven_by_user_id, self.driver.id)
        self.assertEqual(drive.driven_at, when)
        self.assertEqual(drive.duration_minutes, 45)
        self.assertEqual(drive.route_notes, "Highway loop via I-8")
        self.assertEqual(drive.customer_reaction, "Loved the visibility")
        self.assertEqual(
            drive.objections_captured,
            ["Price too high", "Wants leather"],
        )
        self.assertEqual(drive.next_action, "Follow up with pricing sheet by EOD")

    def test_minimal_write_defaults_driven_at_to_now(self) -> None:
        before = timezone.now()
        drive = record_test_drive(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
        )
        after = timezone.now()
        self.assertGreaterEqual(drive.driven_at, before)
        self.assertLessEqual(drive.driven_at, after)
        self.assertEqual(drive.objections_captured, [])
        self.assertEqual(drive.route_notes, "")

    def test_objections_persist_roundtrip(self) -> None:
        drive = record_test_drive(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            objections_captured=["a", "b", "c"],
        )
        drive.refresh_from_db()
        self.assertEqual(drive.objections_captured, ["a", "b", "c"])


class RecordTestDriveCrossTenantTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="td-svc-a", name="TD Svc A"
        )
        self.other = Dealership.objects.create(
            slug="td-svc-b", name="TD Svc B"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.vehicle = _make_vehicle(self.dealership, "SVC-A-1")
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="CrossLead"
        )
        self.cross_vehicle = _make_vehicle(self.other, "SVC-B-1")

    def test_cross_tenant_lead_raises(self) -> None:
        with self.assertRaises(CrossTenantTestDriveError):
            record_test_drive(
                dealership=self.dealership,
                lead=self.cross_lead,
                vehicle=self.vehicle,
            )
        self.assertEqual(
            TestDrive.objects.filter(dealership=self.dealership).count(), 0
        )

    def test_cross_tenant_vehicle_raises(self) -> None:
        with self.assertRaises(CrossTenantTestDriveError):
            record_test_drive(
                dealership=self.dealership,
                lead=self.lead,
                vehicle=self.cross_vehicle,
            )
        self.assertEqual(
            TestDrive.objects.filter(dealership=self.dealership).count(), 0
        )
