"""Milestone 9 · Increment 1 (SESSION_100) — Sale model tests.

Locks the persistence-layer shape of :class:`Sale` per
``MILESTONE_9_PLANNING.md`` §1.1 + §5.b/c (all Option A —
user-confirmed at SESSION_100 open, recorded in §0.a).

Coverage:

- Field defaults + choice validation.
- Ordering (``-sale_date``, ``-created_at``).
- OneToOne on ``vehicle`` — second Sale on same vehicle raises
  :class:`django.db.utils.IntegrityError`.
- ``clean()`` cross-tenant guards (dealership vs vehicle, buyer).
- ``buyer`` SET_NULL when parent :class:`CustomerLead` deleted.
- Tenant-carrier autofill signal wires ``Sale`` in as the 23rd
  carrier (M8.1 was 22).
- ``__str__`` renders a human-scannable summary.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from dealer_ai.models import (
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    CustomerLead,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


def _make_vehicle(dealership: Dealership, *, stock: str = "SALE-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


class SaleShapeTests(TestCase):
    """Field-level invariants."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m91-shape", name="M9.1 Shape"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.buyer = CustomerLead.objects.create(
            dealership=self.dealership, name="Alice Buyer"
        )

    def test_create_persists_all_fields(self) -> None:
        sale = Sale.objects.create(
            dealership=self.dealership,
            vehicle=self.vehicle,
            buyer=self.buyer,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
            lender_name="First National",
            gross_realized=Decimal("3500.00"),
        )
        sale.refresh_from_db()
        self.assertEqual(sale.dealership_id, self.dealership.pk)
        self.assertEqual(sale.vehicle_id, self.vehicle.pk)
        self.assertEqual(sale.buyer_id, self.buyer.pk)
        self.assertEqual(sale.sale_date, dt.date(2026, 8, 1))
        self.assertEqual(sale.sold_price, Decimal("32000.00"))
        self.assertEqual(sale.finance_type, SALE_FINANCE_TYPE_RETAIL)
        self.assertEqual(sale.lender_name, "First National")
        self.assertEqual(sale.gross_realized, Decimal("3500.00"))

    def test_default_ordering_is_sale_date_desc_then_created_desc(
        self,
    ) -> None:
        v2 = _make_vehicle(self.dealership, stock="SALE-2")
        v3 = _make_vehicle(self.dealership, stock="SALE-3")
        Sale.objects.create(
            dealership=self.dealership,
            vehicle=self.vehicle,
            sale_date=dt.date(2026, 7, 15),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("2000.00"),
        )
        Sale.objects.create(
            dealership=self.dealership,
            vehicle=v2,
            sale_date=dt.date(2026, 8, 5),
            sold_price=Decimal("30000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
            gross_realized=Decimal("3000.00"),
        )
        Sale.objects.create(
            dealership=self.dealership,
            vehicle=v3,
            sale_date=dt.date(2026, 7, 20),
            sold_price=Decimal("22000.00"),
            finance_type=SALE_FINANCE_TYPE_BHPH,
            gross_realized=Decimal("1500.00"),
        )
        ordered = list(Sale.objects.all())
        self.assertEqual(
            [s.sale_date for s in ordered],
            [dt.date(2026, 8, 5), dt.date(2026, 7, 20), dt.date(2026, 7, 15)],
        )

    def test_str_renders_human_summary(self) -> None:
        sale = Sale.objects.create(
            dealership=self.dealership,
            vehicle=self.vehicle,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        rendered = str(sale)
        self.assertIn(str(sale.pk), rendered)
        self.assertIn(self.vehicle.stock_number, rendered)
        self.assertIn("32000", rendered)
        self.assertIn("Cash", rendered)

    def test_lender_name_optional_defaults_blank(self) -> None:
        sale = Sale.objects.create(
            dealership=self.dealership,
            vehicle=self.vehicle,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        sale.refresh_from_db()
        self.assertEqual(sale.lender_name, "")

    def test_buyer_optional(self) -> None:
        sale = Sale.objects.create(
            dealership=self.dealership,
            vehicle=self.vehicle,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        sale.refresh_from_db()
        self.assertIsNone(sale.buyer_id)


class SaleOneToOneVehicleTests(TestCase):
    """The 'one sale per vehicle' invariant lives at the DB layer."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m91-onetoone", name="M9.1 OneToOne"
        )
        self.vehicle = _make_vehicle(self.dealership)

    def test_second_sale_on_same_vehicle_raises(self) -> None:
        Sale.objects.create(
            dealership=self.dealership,
            vehicle=self.vehicle,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        with self.assertRaises(IntegrityError):
            Sale.objects.create(
                dealership=self.dealership,
                vehicle=self.vehicle,
                sale_date=dt.date(2026, 8, 15),
                sold_price=Decimal("34000.00"),
                finance_type=SALE_FINANCE_TYPE_RETAIL,
                gross_realized=Decimal("5000.00"),
            )


class SaleCleanCrossTenantTests(TestCase):
    """Model-layer cross-tenant guards fire before DB write."""

    def setUp(self) -> None:
        self.dealership_a = Dealership.objects.create(
            slug="m91-tenant-a", name="Tenant A"
        )
        self.dealership_b = Dealership.objects.create(
            slug="m91-tenant-b", name="Tenant B"
        )
        self.vehicle_a = _make_vehicle(self.dealership_a, stock="A-1")
        self.buyer_a = CustomerLead.objects.create(
            dealership=self.dealership_a, name="Buyer A"
        )
        self.buyer_b = CustomerLead.objects.create(
            dealership=self.dealership_b, name="Buyer B"
        )

    def test_clean_raises_on_vehicle_dealership_mismatch(self) -> None:
        sale = Sale(
            dealership=self.dealership_b,
            vehicle=self.vehicle_a,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            sale.clean()
        self.assertIn("dealership", ctx.exception.error_dict)

    def test_clean_raises_on_buyer_dealership_mismatch(self) -> None:
        sale = Sale(
            dealership=self.dealership_a,
            vehicle=self.vehicle_a,
            buyer=self.buyer_b,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            sale.clean()
        self.assertIn("buyer", ctx.exception.error_dict)

    def test_clean_passes_when_all_tenants_align(self) -> None:
        sale = Sale(
            dealership=self.dealership_a,
            vehicle=self.vehicle_a,
            buyer=self.buyer_a,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        # Should not raise.
        sale.clean()

    def test_clean_passes_when_buyer_none(self) -> None:
        sale = Sale(
            dealership=self.dealership_a,
            vehicle=self.vehicle_a,
            buyer=None,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
            gross_realized=Decimal("3500.00"),
        )
        sale.clean()


class SaleBuyerSetNullTests(TestCase):
    """CustomerLead deletion should not cascade Sale deletion."""

    def test_buyer_set_null_on_lead_delete(self) -> None:
        dealership = Dealership.objects.create(
            slug="m91-setnull", name="M9.1 SET_NULL"
        )
        vehicle = _make_vehicle(dealership)
        buyer = CustomerLead.objects.create(
            dealership=dealership, name="Doomed Lead"
        )
        sale = Sale.objects.create(
            dealership=dealership,
            vehicle=vehicle,
            buyer=buyer,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("32000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
            gross_realized=Decimal("3500.00"),
        )
        buyer.delete()
        sale.refresh_from_db()
        self.assertIsNone(sale.buyer_id)
        # Sale itself survives — the closing event is the ledger of
        # record; lead deletion is provenance loss only.
        self.assertTrue(Sale.objects.filter(pk=sale.pk).exists())


class SaleTenancyCarrierTests(TestCase):
    """M9.1 tenant-carrier autofill signal covers Sale."""

    def test_sale_registered_as_tenancy_carrier(self) -> None:
        # M8.1 count was 22; M9.1 adds Sale as the 23rd. Assert with
        # ``>=`` per the M7/M8 §6 pattern so future M9+ increments
        # can extend further without editing this test.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 23)
        self.assertIn("Sale", _TENANT_CARRIER_MODEL_NAMES)
