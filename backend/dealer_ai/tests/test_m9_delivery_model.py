"""Milestone 9 · Increment 2 (SESSION_101) — Delivery model tests.

Locks the persistence-layer shape of :class:`Delivery` per
``MILESTONE_9_PLANNING.md`` §1.2 Option A (user-confirmed at
SESSION_101 open, recorded in §0.a).

Coverage:

- Field defaults + checklist populated from
  ``_default_delivery_checklist`` at insert.
- Ordering (``-created_at``).
- OneToOne on ``sale`` — second Delivery on same Sale raises
  :class:`django.db.utils.IntegrityError`.
- ``clean()`` cross-tenant guard (dealership vs sale.dealership).
- Tenant-carrier autofill signal wires ``Delivery`` in as the 24th
  carrier (M9.1 was 23).
- ``__str__`` renders a human-scannable summary.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from dealer_ai.models import (
    DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
    DELIVERY_CHECKLIST_KEYS,
    SALE_FINANCE_TYPE_CASH,
    Delivery,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


def _make_sale(
    dealership: Dealership, *, stock: str = "DEL-1"
) -> Sale:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28000.00"),
        dealership=dealership,
    )
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("32000.00"),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=Decimal("3500.00"),
    )


class DeliveryShapeTests(TestCase):
    """Field-level invariants."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m92-shape", name="M9.2 Shape"
        )
        self.sale = _make_sale(self.dealership)

    def test_create_populates_all_checklist_keys_false(self) -> None:
        delivery = Delivery.objects.create(
            dealership=self.dealership,
            sale=self.sale,
        )
        delivery.refresh_from_db()
        self.assertEqual(
            set(delivery.checklist.keys()), set(DELIVERY_CHECKLIST_KEYS)
        )
        self.assertTrue(
            all(v is False for v in delivery.checklist.values())
        )

    def test_defaults(self) -> None:
        delivery = Delivery.objects.create(
            dealership=self.dealership,
            sale=self.sale,
        )
        delivery.refresh_from_db()
        self.assertIsNone(delivery.delivery_date)
        self.assertEqual(delivery.temp_tag_number, "")
        self.assertFalse(delivery.insurance_verified)
        self.assertIsNone(delivery.insurance_verified_at)
        self.assertEqual(delivery.notes, "")

    def test_ordering_created_at_desc(self) -> None:
        d1 = Delivery.objects.create(
            dealership=self.dealership, sale=self.sale
        )
        s2 = _make_sale(self.dealership, stock="DEL-2")
        d2 = Delivery.objects.create(
            dealership=self.dealership, sale=s2
        )
        ordered = list(Delivery.objects.all())
        self.assertEqual([d.pk for d in ordered], [d2.pk, d1.pk])

    def test_str_renders_human_summary(self) -> None:
        delivery = Delivery.objects.create(
            dealership=self.dealership, sale=self.sale
        )
        rendered = str(delivery)
        self.assertIn(str(delivery.pk), rendered)
        self.assertIn(str(self.sale.pk), rendered)
        self.assertIn("insurance_verified=False", rendered)

    def test_persist_full_fields(self) -> None:
        checklist = {key: True for key in DELIVERY_CHECKLIST_KEYS}
        delivery = Delivery.objects.create(
            dealership=self.dealership,
            sale=self.sale,
            delivery_date=dt.date(2026, 8, 5),
            checklist=checklist,
            temp_tag_number="TX-99887",
            insurance_verified=True,
            insurance_verified_at=dt.datetime(2026, 8, 4, 15, 0, tzinfo=dt.timezone.utc),
            notes="Weekend delivery.",
        )
        delivery.refresh_from_db()
        self.assertEqual(delivery.delivery_date, dt.date(2026, 8, 5))
        self.assertEqual(delivery.temp_tag_number, "TX-99887")
        self.assertTrue(delivery.insurance_verified)
        self.assertEqual(delivery.checklist, checklist)
        self.assertIn("Weekend", delivery.notes)


class DeliveryOneToOneSaleTests(TestCase):
    """The 'one Delivery per Sale' invariant lives at the DB layer."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m92-onetoone", name="M9.2 OneToOne"
        )
        self.sale = _make_sale(self.dealership)

    def test_second_delivery_on_same_sale_raises(self) -> None:
        Delivery.objects.create(
            dealership=self.dealership, sale=self.sale
        )
        with self.assertRaises(IntegrityError):
            Delivery.objects.create(
                dealership=self.dealership, sale=self.sale
            )


class DeliveryCleanCrossTenantTests(TestCase):
    """Model-layer cross-tenant guard fires before DB write."""

    def setUp(self) -> None:
        self.dealership_a = Dealership.objects.create(
            slug="m92-tenant-a", name="Tenant A"
        )
        self.dealership_b = Dealership.objects.create(
            slug="m92-tenant-b", name="Tenant B"
        )
        self.sale_a = _make_sale(self.dealership_a, stock="A-1")

    def test_clean_raises_on_sale_dealership_mismatch(self) -> None:
        delivery = Delivery(
            dealership=self.dealership_b,  # mismatch
            sale=self.sale_a,
        )
        with self.assertRaises(ValidationError) as ctx:
            delivery.clean()
        self.assertIn("dealership", ctx.exception.error_dict)

    def test_clean_passes_when_tenants_align(self) -> None:
        delivery = Delivery(
            dealership=self.dealership_a,
            sale=self.sale_a,
        )
        delivery.clean()  # Should not raise.


class DeliveryTenancyCarrierTests(TestCase):
    """M9.2 tenant-carrier autofill signal covers Delivery."""

    def test_delivery_registered_as_tenancy_carrier(self) -> None:
        # M9.1 count was 23; M9.2 adds Delivery as the 24th.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 24)
        self.assertIn("Delivery", _TENANT_CARRIER_MODEL_NAMES)


class DeliveryChecklistVocabularyTests(TestCase):
    """Lock the M9.2 vocabulary shape."""

    def test_vocabulary_has_five_keys(self) -> None:
        self.assertEqual(len(DELIVERY_CHECKLIST_KEYS), 5)

    def test_insurance_verified_in_vocabulary(self) -> None:
        # The denormalized column mirrors this key.
        self.assertIn(
            DELIVERY_CHECKLIST_INSURANCE_VERIFIED,
            DELIVERY_CHECKLIST_KEYS,
        )
