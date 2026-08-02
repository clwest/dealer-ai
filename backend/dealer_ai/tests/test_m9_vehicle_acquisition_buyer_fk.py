"""Milestone 9 · Increment 1 (SESSION_100) — VehicleAcquisition.buyer FK tests.

Locks the M2 additive extension shipped in migration
``0023_sale_entity_and_buyer_fk`` per
``MILESTONE_9_PLANNING.md`` §5.a Option A (user-confirmed at
SESSION_100 open, recorded in §0.a).

Coverage:

- ``buyer`` is nullable — pre-M9 acquisition rows survive.
- ``buyer`` SET_NULL when the User is deleted.
- Reverse accessor ``user.acquisitions_bought`` works.
- Setting a buyer round-trips through the DB.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dealer_ai.models import (
    SOURCE_AUCTION,
    Dealership,
    Vehicle,
    VehicleAcquisition,
)


User = get_user_model()


def _make_acquisition_setup(dealership: Dealership, *, stock: str = "ACQ-1"):
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("42000.00"),
        dealership=dealership,
    )
    return vehicle


class VehicleAcquisitionBuyerFkTests(TestCase):
    """M9.1 additive extension — buyer FK behavior."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m91-buyer-fk", name="M9.1 Buyer FK"
        )
        self.buyer_user = User.objects.create_user(
            username="acq-buyer", email="buyer@example.com", password="x"
        )

    def test_buyer_defaults_to_null(self) -> None:
        """Pre-M9 acquisition rows survive — buyer FK is optional."""
        vehicle = _make_acquisition_setup(self.dealership, stock="NULL-1")
        acq = VehicleAcquisition.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("38000.00"),
            purchase_date=dt.date(2026, 6, 1),
        )
        acq.refresh_from_db()
        self.assertIsNone(acq.buyer_id)

    def test_buyer_persisted_when_set(self) -> None:
        vehicle = _make_acquisition_setup(self.dealership, stock="SET-1")
        acq = VehicleAcquisition.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("38000.00"),
            purchase_date=dt.date(2026, 6, 1),
            buyer=self.buyer_user,
        )
        acq.refresh_from_db()
        self.assertEqual(acq.buyer_id, self.buyer_user.pk)

    def test_buyer_set_null_on_user_delete(self) -> None:
        vehicle = _make_acquisition_setup(self.dealership, stock="DEL-1")
        acq = VehicleAcquisition.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("38000.00"),
            purchase_date=dt.date(2026, 6, 1),
            buyer=self.buyer_user,
        )
        self.buyer_user.delete()
        acq.refresh_from_db()
        # Acquisition survives (the ledger of record) but buyer
        # provenance is gone.
        self.assertIsNone(acq.buyer_id)
        self.assertTrue(
            VehicleAcquisition.objects.filter(pk=acq.pk).exists()
        )

    def test_reverse_accessor_returns_bought_acquisitions(self) -> None:
        v1 = _make_acquisition_setup(self.dealership, stock="REV-1")
        v2 = _make_acquisition_setup(self.dealership, stock="REV-2")
        VehicleAcquisition.objects.create(
            vehicle=v1,
            dealership=self.dealership,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("38000.00"),
            purchase_date=dt.date(2026, 6, 1),
            buyer=self.buyer_user,
        )
        VehicleAcquisition.objects.create(
            vehicle=v2,
            dealership=self.dealership,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("40000.00"),
            purchase_date=dt.date(2026, 6, 2),
            buyer=self.buyer_user,
        )
        bought = self.buyer_user.acquisitions_bought.all()
        self.assertEqual(bought.count(), 2)
        self.assertEqual(
            {a.vehicle_id for a in bought}, {v1.pk, v2.pk}
        )
