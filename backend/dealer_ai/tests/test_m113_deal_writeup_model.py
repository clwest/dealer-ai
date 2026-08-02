"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup model tests.

Locks the schema surface of :class:`dealer_ai.models.DealWriteup` per
``MILESTONE_11_PLANNING.md`` §1.3 + §5.e Option A.

Coverage:

- Meta ordering (``-write_up_at``).
- Default values for approval / handoff / notes.
- ``clean()`` cross-tenant guard for both `lead` and `vehicle`.
- CASCADE on lead + vehicle delete.
- SET_NULL on written_up_by_user + sales_manager_approved_by_user
  delete.
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
    DealWriteup,
    Vehicle,
)


User = get_user_model()


def _make_vehicle(dealership: Dealership, stock: str = "DW-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Explorer",
        price=Decimal("42000.00"),
        dealership=dealership,
    )


class DealWriteupDefaultsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dw-defaults", name="DW Defaults"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Debbie"
        )
        self.vehicle = _make_vehicle(self.dealership)

    def test_defaults(self) -> None:
        writeup = DealWriteup.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            write_up_at=timezone.now(),
        )
        self.assertIsNone(writeup.sales_manager_approved_at)
        self.assertIsNone(writeup.sales_manager_approved_by_user)
        self.assertIsNone(writeup.handed_off_to_fandi_at)
        self.assertEqual(writeup.notes, "")
        self.assertIsNone(writeup.vehicle_price)

    def test_ordering_is_reverse_write_up_at(self) -> None:
        earlier = DealWriteup.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            write_up_at=timezone.now() - dt.timedelta(hours=2),
        )
        later = DealWriteup.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            write_up_at=timezone.now(),
        )
        self.assertEqual(list(DealWriteup.objects.all()), [later, earlier])


class DealWriteupCrossTenantCleanTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dw-clean-a", name="DW A"
        )
        self.other = Dealership.objects.create(
            slug="dw-clean-b", name="DW B"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.vehicle = _make_vehicle(self.dealership, "DW-A-1")
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.cross_vehicle = _make_vehicle(self.other, "DW-B-1")

    def test_clean_rejects_cross_tenant_lead(self) -> None:
        writeup = DealWriteup(
            dealership=self.dealership,
            lead=self.cross_lead,
            vehicle=self.vehicle,
            write_up_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            writeup.clean()
        self.assertIn("lead", ctx.exception.message_dict)

    def test_clean_rejects_cross_tenant_vehicle(self) -> None:
        writeup = DealWriteup(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.cross_vehicle,
            write_up_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            writeup.clean()
        self.assertIn("vehicle", ctx.exception.message_dict)


class DealWriteupCascadeAndSetNullTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dw-casc", name="DW Cascade"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Cassidy"
        )
        self.vehicle = _make_vehicle(self.dealership, "DW-C-1")
        self.writer = User.objects.create_user(username="dw-writer", password="x")
        self.approver = User.objects.create_user(
            username="dw-approver", password="x"
        )
        self.writeup = DealWriteup.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            write_up_at=timezone.now(),
            written_up_by_user=self.writer,
            sales_manager_approved_at=timezone.now(),
            sales_manager_approved_by_user=self.approver,
        )

    def test_lead_delete_cascades_writeup(self) -> None:
        self.lead.delete()
        self.assertFalse(DealWriteup.objects.filter(pk=self.writeup.pk).exists())

    def test_vehicle_delete_cascades_writeup(self) -> None:
        self.vehicle.delete()
        self.assertFalse(DealWriteup.objects.filter(pk=self.writeup.pk).exists())

    def test_writer_delete_sets_null(self) -> None:
        self.writer.delete()
        self.writeup.refresh_from_db()
        self.assertIsNone(self.writeup.written_up_by_user)

    def test_approver_delete_sets_null(self) -> None:
        self.approver.delete()
        self.writeup.refresh_from_db()
        self.assertIsNone(self.writeup.sales_manager_approved_by_user)
