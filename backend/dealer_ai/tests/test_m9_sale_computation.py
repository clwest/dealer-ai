"""Milestone 9 · Increment 1 (SESSION_100) — Sale service-verb tests.

Locks :func:`services.sale.gross_realized` and
:func:`services.sale.record_sale` per ``MILESTONE_9_PLANNING.md``
§1.4.

Coverage:

- :func:`gross_realized` returns Decimal.
- :func:`gross_realized` computes ``sold_price - total_investment``
  using sunk cost only (estimates excluded — matches M2 ledger
  contract).
- :func:`gross_realized` returns negative when sold below cost.
- :func:`gross_realized` refuses cross-tenant reads
  (:class:`CrossTenantSaleError`).
- :func:`record_sale` persists all fields.
- :func:`record_sale` denormalizes ``gross_realized`` at write.
- :func:`record_sale` refuses duplicate Sale on same Vehicle
  (:class:`SaleAlreadyExistsError`).
- :func:`record_sale` refuses cross-tenant vehicle
  (:class:`CrossTenantSaleError`).
- :func:`record_sale` refuses cross-tenant buyer
  (:class:`CrossTenantSaleError`).
- :func:`record_sale` refuses unknown ``finance_type``
  (:class:`ValueError`).
- :func:`record_sale` accepts NULL buyer.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_PARTS,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    SALE_FINANCE_TYPE_RETAIL,
    SOURCE_AUCTION,
    CustomerLead,
    Dealership,
    Sale,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.sale import (
    CrossTenantSaleError,
    SaleAlreadyExistsError,
    gross_realized,
    record_sale,
)


def _seed_vehicle_with_ledger(
    dealership: Dealership,
    *,
    stock: str = "GR-1",
    purchase_price: str = "20000.00",
    actual_costs: list[str] | None = None,
    estimated_costs: list[str] | None = None,
) -> Vehicle:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("28000.00"),
        dealership=dealership,
    )
    VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal(purchase_price),
        purchase_date=dt.date(2026, 6, 1),
    )
    for amt in actual_costs or []:
        VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_PARTS,
            amount=Decimal(amt),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
    for amt in estimated_costs or []:
        VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            category=CATEGORY_MECHANICAL_LABOR,
            amount=Decimal(amt),
            incurred_at=timezone.now(),
            is_estimate=True,
        )
    return vehicle


class GrossRealizedVerbTests(TestCase):
    """Pure read verb — never mutates."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m91-gr", name="M9.1 Gross Realized"
        )
        seed_default_coa(self.dealership)

    def test_returns_decimal(self) -> None:
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, purchase_price="20000.00"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        result = gross_realized(sale)
        self.assertIsInstance(result, Decimal)

    def test_computes_positive_realized_gross(self) -> None:
        # purchase 20,000 + actual 500 = 20,500 investment.
        # sold 25,000 → realized 4,500.
        vehicle = _seed_vehicle_with_ledger(
            self.dealership,
            stock="GR-POS",
            purchase_price="20000.00",
            actual_costs=["500.00"],
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
        )
        self.assertEqual(gross_realized(sale), Decimal("4500.00"))

    def test_computes_negative_when_sold_below_cost(self) -> None:
        # purchase 30,000 + actual 1,000 = 31,000 investment.
        # sold 28,000 → realized -3,000.
        vehicle = _seed_vehicle_with_ledger(
            self.dealership,
            stock="GR-NEG",
            purchase_price="30000.00",
            actual_costs=["1000.00"],
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("28000.00"),
            finance_type=SALE_FINANCE_TYPE_BHPH,
        )
        self.assertEqual(gross_realized(sale), Decimal("-3000.00"))

    def test_excludes_estimated_costs(self) -> None:
        # purchase 20,000 + actual 500 + estimated 2,000. Only sunk
        # cost (20,500) reduces gross_realized. Sold 25,000 → 4,500.
        vehicle = _seed_vehicle_with_ledger(
            self.dealership,
            stock="GR-EST",
            purchase_price="20000.00",
            actual_costs=["500.00"],
            estimated_costs=["2000.00"],
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        # If estimates were included: 25,000 - 22,500 = 2,500 (WRONG).
        # Correct sunk-cost basis: 25,000 - 20,500 = 4,500.
        self.assertEqual(gross_realized(sale), Decimal("4500.00"))

    def test_refuses_cross_tenant_read(self) -> None:
        other = Dealership.objects.create(
            slug="m91-gr-other", name="Other Tenant"
        )
        seed_default_coa(other)
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="GR-XTENANT"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        # Mutate in memory to simulate a mis-scoped caller.
        sale.dealership = other
        with self.assertRaises(CrossTenantSaleError):
            gross_realized(sale)


class RecordSaleVerbTests(TestCase):
    """Write path — persists Sale + denormalizes gross_realized."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m91-rec", name="M9.1 Record"
        )
        seed_default_coa(self.dealership)

    def test_persists_all_fields(self) -> None:
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-1", purchase_price="20000.00"
        )
        buyer = CustomerLead.objects.create(
            dealership=self.dealership, name="Test Buyer"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_RETAIL,
            buyer=buyer,
            lender_name="First National",
        )
        sale.refresh_from_db()
        self.assertEqual(sale.vehicle_id, vehicle.pk)
        self.assertEqual(sale.buyer_id, buyer.pk)
        self.assertEqual(sale.sale_date, dt.date(2026, 8, 1))
        self.assertEqual(sale.sold_price, Decimal("25000.00"))
        self.assertEqual(sale.finance_type, SALE_FINANCE_TYPE_RETAIL)
        self.assertEqual(sale.lender_name, "First National")

    def test_denormalizes_gross_realized_at_write(self) -> None:
        # purchase 20,000 → total_investment 20,000; sold 25,000 →
        # gross_realized 5,000 stored on the row.
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-DENORM"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        sale.refresh_from_db()
        self.assertEqual(sale.gross_realized, Decimal("5000.00"))

    def test_refuses_duplicate_sale_same_vehicle(self) -> None:
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-DUP"
        )
        record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        with self.assertRaises(SaleAlreadyExistsError):
            record_sale(
                vehicle,
                dealership=self.dealership,
                sale_date=dt.date(2026, 8, 15),
                sold_price=Decimal("27000.00"),
                finance_type=SALE_FINANCE_TYPE_RETAIL,
            )

    def test_refuses_cross_tenant_vehicle(self) -> None:
        other = Dealership.objects.create(
            slug="m91-rec-other", name="Other Tenant"
        )
        seed_default_coa(other)
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-XTENANT"
        )
        with self.assertRaises(CrossTenantSaleError):
            record_sale(
                vehicle,
                dealership=other,
                sale_date=dt.date(2026, 8, 1),
                sold_price=Decimal("25000.00"),
                finance_type=SALE_FINANCE_TYPE_CASH,
            )

    def test_refuses_cross_tenant_buyer(self) -> None:
        other = Dealership.objects.create(
            slug="m91-rec-buyer-other", name="Other Buyer Tenant"
        )
        seed_default_coa(other)
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-XBUYER"
        )
        other_buyer = CustomerLead.objects.create(
            dealership=other, name="Other Tenant Buyer"
        )
        with self.assertRaises(CrossTenantSaleError):
            record_sale(
                vehicle,
                dealership=self.dealership,
                sale_date=dt.date(2026, 8, 1),
                sold_price=Decimal("25000.00"),
                finance_type=SALE_FINANCE_TYPE_CASH,
                buyer=other_buyer,
            )

    def test_refuses_unknown_finance_type(self) -> None:
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-BADTYPE"
        )
        with self.assertRaises(ValueError):
            record_sale(
                vehicle,
                dealership=self.dealership,
                sale_date=dt.date(2026, 8, 1),
                sold_price=Decimal("25000.00"),
                finance_type="lease",  # Not in Option A vocabulary.
            )

    def test_accepts_null_buyer(self) -> None:
        vehicle = _seed_vehicle_with_ledger(
            self.dealership, stock="REC-NOBUYER"
        )
        sale = record_sale(
            vehicle,
            dealership=self.dealership,
            sale_date=dt.date(2026, 8, 1),
            sold_price=Decimal("25000.00"),
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        sale.refresh_from_db()
        self.assertIsNone(sale.buyer_id)
        self.assertEqual(Sale.objects.count(), 1)
