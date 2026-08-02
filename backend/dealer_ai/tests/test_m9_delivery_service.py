"""Milestone 9 · Increment 2 (SESSION_101) — Delivery service-verb tests.

Locks :func:`services.delivery.record_delivery`,
:func:`services.delivery.update_checklist_item`, and
:func:`services.delivery.verify_insurance` per
``MILESTONE_9_PLANNING.md`` §1.2.

Coverage:

- :func:`record_delivery` creates a Delivery for the Sale's Vehicle.
- :func:`record_delivery` refuses when Vehicle has no Sale.
- :func:`record_delivery` refuses duplicate Delivery on same Sale.
- :func:`record_delivery` refuses cross-tenant.
- :func:`update_checklist_item` toggles a valid key.
- :func:`update_checklist_item` refuses unknown key.
- :func:`update_checklist_item` refuses ``insurance_verified`` key
  (reserved to :func:`verify_insurance`).
- :func:`update_checklist_item` refuses cross-tenant.
- :func:`verify_insurance` writes both column + checklist key +
  timestamp atomically.
- :func:`verify_insurance` is idempotent (second call doesn't shift
  the timestamp).
- :func:`verify_insurance` refuses cross-tenant.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    DELIVERY_CHECKLIST_CUSTOMER_WALKTHROUGH,
    DELIVERY_CHECKLIST_FUELED,
    DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
    SALE_FINANCE_TYPE_CASH,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.delivery import (
    CrossTenantDeliveryError,
    DeliveryAlreadyExistsError,
    SaleNotFoundForDeliveryError,
    UnknownChecklistKeyError,
    record_delivery,
    update_checklist_item,
    verify_insurance,
)


def _make_vehicle_with_sale(
    dealership: Dealership, *, stock: str = "SVC-1"
) -> tuple[Vehicle, Sale]:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28000.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("32000.00"),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=Decimal("3500.00"),
    )
    return vehicle, sale


def _make_vehicle_only(dealership: Dealership, *, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("24000.00"),
        dealership=dealership,
    )


class RecordDeliveryVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m92-rec", name="M9.2 Record"
        )

    def test_creates_delivery(self) -> None:
        vehicle, sale = _make_vehicle_with_sale(self.dealership)
        delivery = record_delivery(
            vehicle,
            dealership=self.dealership,
            delivery_date=dt.date(2026, 8, 5),
            temp_tag_number="AZ-1234",
            notes="Pickup Saturday morning.",
        )
        delivery.refresh_from_db()
        self.assertEqual(delivery.sale_id, sale.pk)
        self.assertEqual(delivery.delivery_date, dt.date(2026, 8, 5))
        self.assertEqual(delivery.temp_tag_number, "AZ-1234")
        self.assertIn("Saturday", delivery.notes)

    def test_creates_delivery_without_optional_fields(self) -> None:
        vehicle, _sale = _make_vehicle_with_sale(
            self.dealership, stock="SVC-BARE"
        )
        delivery = record_delivery(vehicle, dealership=self.dealership)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.delivery_date)
        self.assertEqual(delivery.temp_tag_number, "")
        self.assertFalse(delivery.insurance_verified)

    def test_refuses_when_vehicle_has_no_sale(self) -> None:
        vehicle = _make_vehicle_only(self.dealership, stock="NO-SALE")
        with self.assertRaises(SaleNotFoundForDeliveryError):
            record_delivery(vehicle, dealership=self.dealership)

    def test_refuses_duplicate_delivery_same_sale(self) -> None:
        vehicle, _sale = _make_vehicle_with_sale(
            self.dealership, stock="SVC-DUP"
        )
        record_delivery(vehicle, dealership=self.dealership)
        with self.assertRaises(DeliveryAlreadyExistsError):
            record_delivery(vehicle, dealership=self.dealership)

    def test_refuses_cross_tenant(self) -> None:
        other = Dealership.objects.create(
            slug="m92-rec-other", name="Other Tenant"
        )
        vehicle, _sale = _make_vehicle_with_sale(
            self.dealership, stock="SVC-XT"
        )
        with self.assertRaises(CrossTenantDeliveryError):
            record_delivery(vehicle, dealership=other)


class UpdateChecklistItemVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m92-upd", name="M9.2 Update"
        )
        vehicle, sale = _make_vehicle_with_sale(self.dealership)
        self.delivery = record_delivery(vehicle, dealership=self.dealership)

    def test_toggles_valid_key(self) -> None:
        result = update_checklist_item(
            self.delivery,
            dealership=self.dealership,
            key=DELIVERY_CHECKLIST_FUELED,
            value=True,
        )
        self.assertTrue(result.checklist[DELIVERY_CHECKLIST_FUELED])
        # Other keys stay False.
        self.assertFalse(
            result.checklist[DELIVERY_CHECKLIST_CUSTOMER_WALKTHROUGH]
        )

    def test_toggle_back_to_false(self) -> None:
        update_checklist_item(
            self.delivery,
            dealership=self.dealership,
            key=DELIVERY_CHECKLIST_FUELED,
            value=True,
        )
        result = update_checklist_item(
            self.delivery,
            dealership=self.dealership,
            key=DELIVERY_CHECKLIST_FUELED,
            value=False,
        )
        self.assertFalse(result.checklist[DELIVERY_CHECKLIST_FUELED])

    def test_refuses_unknown_key(self) -> None:
        with self.assertRaises(UnknownChecklistKeyError):
            update_checklist_item(
                self.delivery,
                dealership=self.dealership,
                key="not_a_real_key",
                value=True,
            )

    def test_refuses_insurance_key_directly(self) -> None:
        with self.assertRaises(UnknownChecklistKeyError):
            update_checklist_item(
                self.delivery,
                dealership=self.dealership,
                key=DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
                value=True,
            )

    def test_refuses_cross_tenant(self) -> None:
        other = Dealership.objects.create(
            slug="m92-upd-other", name="Other Tenant"
        )
        with self.assertRaises(CrossTenantDeliveryError):
            update_checklist_item(
                self.delivery,
                dealership=other,
                key=DELIVERY_CHECKLIST_FUELED,
                value=True,
            )


class VerifyInsuranceVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m92-ins", name="M9.2 Insurance"
        )
        vehicle, sale = _make_vehicle_with_sale(self.dealership)
        self.delivery = record_delivery(vehicle, dealership=self.dealership)

    def test_writes_column_checklist_key_and_timestamp(self) -> None:
        result = verify_insurance(
            self.delivery, dealership=self.dealership
        )
        self.assertTrue(result.insurance_verified)
        self.assertIsNotNone(result.insurance_verified_at)
        self.assertTrue(
            result.checklist[DELIVERY_CHECKLIST_INSURANCE_VERIFIED]
        )

    def test_idempotent(self) -> None:
        first = verify_insurance(
            self.delivery, dealership=self.dealership
        )
        first_at = first.insurance_verified_at
        # Sleep-free idempotency check — a second call within
        # microseconds must not shift the timestamp.
        second = verify_insurance(first, dealership=self.dealership)
        self.assertEqual(second.insurance_verified_at, first_at)

    def test_respects_explicit_at_arg(self) -> None:
        explicit_at = dt.datetime(2026, 8, 4, 15, 0, tzinfo=dt.timezone.utc)
        result = verify_insurance(
            self.delivery,
            dealership=self.dealership,
            at=explicit_at,
        )
        self.assertEqual(result.insurance_verified_at, explicit_at)

    def test_refuses_cross_tenant(self) -> None:
        other = Dealership.objects.create(
            slug="m92-ins-other", name="Other Tenant"
        )
        with self.assertRaises(CrossTenantDeliveryError):
            verify_insurance(self.delivery, dealership=other)
