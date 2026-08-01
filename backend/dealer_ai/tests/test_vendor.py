"""Milestone 4 · Increment 1 — Vendor model tests.

Persistence-layer coverage only. No service-layer semantics (vendor
CRUD gating, activate/deactivate workflow) are tested here — those
land at M4.6. Same shape as M3.1's ``test_condition_report.py``.

Locked invariants:

- Dealership FK NOT NULL from day one.
- Slug unique-per-dealership (same slug allowed in different
  dealerships).
- Categories persist as a JSONField list.
- ``is_active`` defaults to True and toggles cleanly.
- PROTECT contract on ``WorkOrder.vendor`` and
  ``VendorCommunication.vendor`` — hard-deleting a referenced Vendor
  raises ``ProtectedError``.
- Ordering by name (alphabetical).
- ``__str__`` for Django admin display.
- Vendor deletion when unreferenced succeeds (no PROTECT bar).
"""

from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_MECHANICAL,
    Dealership,
    Vehicle,
    Vendor,
    VendorCommunication,
    VENDOR_COMMUNICATION_CHANNEL_EMAIL,
    VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
    VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
    VENDOR_COMMUNICATION_STATUS_DRAFT,
    WORK_ORDER_VENUE_OUTSOURCED,
    WorkOrder,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("42000.00"),
        dealership=dealership,
    )


class VendorCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_round_trip_all_fields(self):
        vendor = Vendor.objects.create(
            dealership=self.default,
            name="Yuma Body Works",
            slug="yuma-body-works",
            categories=[CONDITION_CATEGORY_BODY, "paint"],
            phone="928-555-0100",
            email="ops@yumabody.example",
            notes="Prefers text over email; net-15 invoicing.",
        )
        fetched = Vendor.objects.get(pk=vendor.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.name, "Yuma Body Works")
        self.assertEqual(fetched.slug, "yuma-body-works")
        self.assertEqual(fetched.categories, [CONDITION_CATEGORY_BODY, "paint"])
        self.assertEqual(fetched.phone, "928-555-0100")
        self.assertEqual(fetched.email, "ops@yumabody.example")
        self.assertIn("net-15", fetched.notes)
        self.assertTrue(fetched.is_active)

    def test_categories_default_empty_list(self):
        vendor = Vendor.objects.create(
            dealership=self.default,
            name="Mystery Vendor",
            slug="mystery",
        )
        self.assertEqual(vendor.categories, [])

    def test_is_active_defaults_true(self):
        vendor = Vendor.objects.create(
            dealership=self.default,
            name="Active",
            slug="active",
        )
        self.assertTrue(vendor.is_active)

    def test_inactive_flag_persists(self):
        vendor = Vendor.objects.create(
            dealership=self.default,
            name="Retired",
            slug="retired",
            is_active=False,
        )
        self.assertFalse(Vendor.objects.get(pk=vendor.pk).is_active)


class VendorSlugUniquenessPerDealership(TestCase):
    """The uniq_vendor_slug_per_dealership constraint enforces
    slug uniqueness scoped per-dealership — not globally. Two
    independent dealerships must be free to use overlapping vendor
    slugs (a generic ``bobs-body`` at both stores is expected)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-vendor"
        )

    def test_same_slug_different_dealership_allowed(self):
        Vendor.objects.create(
            dealership=self.default,
            name="Bob's Body",
            slug="bobs-body",
        )
        # Same slug at a different dealership must not conflict.
        Vendor.objects.create(
            dealership=self.other,
            name="Bob's Body",
            slug="bobs-body",
        )
        self.assertEqual(Vendor.objects.filter(slug="bobs-body").count(), 2)

    def test_duplicate_slug_same_dealership_rejected(self):
        Vendor.objects.create(
            dealership=self.default,
            name="Original",
            slug="dup-slug",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vendor.objects.create(
                    dealership=self.default,
                    name="Duplicate",
                    slug="dup-slug",
                )


class VendorDealershipRequired(TestCase):
    """Dealership FK is NOT NULL from day one."""

    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            Vendor._meta.get_field("dealership").null,
            "Vendor.dealership should be NOT NULL from day one",
        )


class VendorReferencedDeleteProtection(TestCase):
    """Vendor deletion contract (planning refinement SESSION_066).

    Normal removal path is ``is_active=False``. Hard-delete is
    prevented at the schema layer by ``on_delete=PROTECT`` on every
    FK pointing at Vendor. Historical rows keep the reference
    intact; a superuser who genuinely needs to purge an unreferenced
    vendor may do so (no bar when nothing references it)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41V-DEL", self.default)
        self.vendor = Vendor.objects.create(
            dealership=self.default,
            name="Protected Body Shop",
            slug="protected-body",
        )

    def test_unreferenced_vendor_delete_succeeds(self):
        # No WorkOrder / VendorCommunication points at this vendor.
        pk = self.vendor.pk
        self.vendor.delete()
        self.assertFalse(Vendor.objects.filter(pk=pk).exists())

    def test_workorder_referenced_vendor_delete_raises_protected(self):
        WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=self.vendor,
        )
        with self.assertRaises(ProtectedError):
            self.vendor.delete()
        # Vendor row and referencing WorkOrder still exist.
        self.assertTrue(Vendor.objects.filter(pk=self.vendor.pk).exists())

    def test_vendor_communication_referenced_vendor_delete_raises_protected(self):
        VendorCommunication.objects.create(
            dealership=self.default,
            vendor=self.vendor,
            kind=VENDOR_COMMUNICATION_KIND_VENDOR_COMM,
            channel=VENDOR_COMMUNICATION_CHANNEL_EMAIL,
            direction=VENDOR_COMMUNICATION_DIRECTION_OUTBOUND,
            status=VENDOR_COMMUNICATION_STATUS_DRAFT,
            draft_content="Placeholder body.",
        )
        with self.assertRaises(ProtectedError):
            self.vendor.delete()
        self.assertTrue(Vendor.objects.filter(pk=self.vendor.pk).exists())

    def test_deactivate_referenced_vendor_succeeds(self):
        # The normal removal path — always available regardless of
        # references.
        WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=self.vendor,
        )
        self.vendor.is_active = False
        self.vendor.save()
        fetched = Vendor.objects.get(pk=self.vendor.pk)
        self.assertFalse(fetched.is_active)


class VendorStrRepresentation(TestCase):
    def test_str_returns_name(self):
        vendor = Vendor.objects.create(
            dealership=Dealership.objects.get(slug="default"),
            name="Copper Canyon Detail",
            slug="copper-detail",
        )
        self.assertEqual(str(vendor), "Copper Canyon Detail")


class VendorOrdering(TestCase):
    """Meta.ordering by name (alphabetical) — the M4.6 vendor picker
    depends on this for a stable, predictable list."""

    def test_ordered_alphabetically_by_name(self):
        default = Dealership.objects.get(slug="default")
        Vendor.objects.create(dealership=default, name="Zeta Auto", slug="zeta")
        Vendor.objects.create(dealership=default, name="Alpha Auto", slug="alpha")
        Vendor.objects.create(dealership=default, name="Mesa Auto", slug="mesa")
        names = list(Vendor.objects.filter(dealership=default).values_list("name", flat=True))
        self.assertEqual(names, ["Alpha Auto", "Mesa Auto", "Zeta Auto"])
