"""Milestone 2 · Increment 1 — VehicleCost model tests.

Persistence-layer coverage only. Same M2.1 scope discipline as
``test_vehicle_acquisition.py`` — no business logic tested (no
`compute_totals`, no computed Vehicle properties, no accrual command,
no aggregation).

Locked invariants:

- Category vocabulary contains exactly 26 canonical categories.
- Category ``choices=`` validation rejects invalid strings.
- Dealership FK NOT NULL from day one.
- Cross-tenant contamination guard (``clean()`` raises when
  ``cost.dealership != vehicle.dealership``).
- Cascade on Vehicle delete.
- ``created_by`` SET_NULL when the authoring User is deleted —
  historical rows survive user account removal.
- Negative amounts are permitted (the correction / reversal pattern
  from planning §1.6 design note).
- ``is_estimate`` defaults to False.
- Ordering (most recently incurred first).
- ``__str__`` for admin readability.
- Reverse relation ``vehicle.costs`` works.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_ADVERTISING_ALLOCATION,
    CATEGORY_BANKING_FEES,
    CATEGORY_BATTERY,
    CATEGORY_BODY_WORK,
    CATEGORY_BRAKES,
    CATEGORY_CURTAILMENT,
    CATEGORY_DETAIL,
    CATEGORY_DIAGNOSTICS,
    CATEGORY_FLOOR_PLAN_FEES,
    CATEGORY_FLOOR_PLAN_INTEREST,
    CATEGORY_FUEL,
    CATEGORY_GLASS,
    CATEGORY_LISTING_FEES,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_MISC_DEALER_EXPENSES,
    CATEGORY_OIL_SERVICE,
    CATEGORY_PAINT,
    CATEGORY_PARTS,
    CATEGORY_PHOTOGRAPHY,
    CATEGORY_REGISTRATION,
    CATEGORY_SHIPPING,
    CATEGORY_TIRES,
    CATEGORY_TITLE_WORK,
    CATEGORY_UPHOLSTERY,
    CATEGORY_WHEEL_REPAIR,
    CATEGORY_WIRE_FEES,
    VEHICLE_COST_CATEGORY_CHOICES,
    Dealership,
    Vehicle,
    VehicleCost,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Ranger",
        price=Decimal("34000.00"),
        dealership=dealership,
    )


class CategoryVocabulary(TestCase):
    """The 26 canonical categories are enumerated in planning §1.2 and
    grouped as flooring (5) / recon (13) / admin (7) / photography (1).
    Any addition or rename requires a roadmap decision — this test
    forces that conversation."""

    def test_choices_contain_exactly_twenty_six_canonical_categories(self):
        keys = {key for key, _ in VEHICLE_COST_CATEGORY_CHOICES}
        expected = {
            # Flooring (5)
            CATEGORY_FLOOR_PLAN_INTEREST,
            CATEGORY_FLOOR_PLAN_FEES,
            CATEGORY_CURTAILMENT,
            CATEGORY_WIRE_FEES,
            CATEGORY_BANKING_FEES,
            # Reconditioning (13)
            CATEGORY_PARTS,
            CATEGORY_MECHANICAL_LABOR,
            CATEGORY_TIRES,
            CATEGORY_BRAKES,
            CATEGORY_BATTERY,
            CATEGORY_OIL_SERVICE,
            CATEGORY_DIAGNOSTICS,
            CATEGORY_GLASS,
            CATEGORY_BODY_WORK,
            CATEGORY_PAINT,
            CATEGORY_UPHOLSTERY,
            CATEGORY_WHEEL_REPAIR,
            CATEGORY_DETAIL,
            # Administrative (7)
            CATEGORY_FUEL,
            CATEGORY_LISTING_FEES,
            CATEGORY_ADVERTISING_ALLOCATION,
            CATEGORY_REGISTRATION,
            CATEGORY_TITLE_WORK,
            CATEGORY_SHIPPING,
            CATEGORY_MISC_DEALER_EXPENSES,
            # Photography (1)
            CATEGORY_PHOTOGRAPHY,
        }
        self.assertEqual(keys, expected)
        # Redundant belt-and-suspenders: 26 categories total.
        self.assertEqual(len(keys), 26)


class VehicleCostCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-COST-CREATE", self.default)

    def test_round_trip_all_fields(self):
        User = get_user_model()
        author = User.objects.create_user(
            username="poster", password="test-pass-abcd"
        )
        cost = VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_MECHANICAL_LABOR,
            amount=Decimal("485.75"),
            incurred_at=timezone.now(),
            vendor="Rick's Auto Repair",
            reference="INV-8842",
            notes="Front brake caliper replacement",
            is_estimate=False,
            created_by=author,
        )
        fetched = VehicleCost.objects.get(pk=cost.pk)
        self.assertEqual(fetched.category, CATEGORY_MECHANICAL_LABOR)
        self.assertEqual(fetched.amount, Decimal("485.75"))
        self.assertEqual(fetched.vendor, "Rick's Auto Repair")
        self.assertEqual(fetched.reference, "INV-8842")
        self.assertFalse(fetched.is_estimate)
        self.assertEqual(fetched.created_by_id, author.pk)

    def test_defaults_when_optional_fields_omitted(self):
        cost = VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
            amount=Decimal("3.42"),
            incurred_at=timezone.now(),
        )
        self.assertEqual(cost.vendor, "")
        self.assertEqual(cost.reference, "")
        self.assertEqual(cost.notes, "")
        self.assertFalse(cost.is_estimate)
        self.assertIsNone(cost.created_by_id)

    def test_category_full_clean_rejects_invalid_choice(self):
        cost = VehicleCost(
            vehicle=self.vehicle,
            dealership=self.default,
            category="miscellaneous",  # not a valid choice
            amount=Decimal("100"),
            incurred_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            cost.full_clean()

    def test_is_estimate_can_be_flipped_to_true(self):
        cost = VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_BODY_WORK,
            amount=Decimal("1200.00"),
            incurred_at=timezone.now(),
            is_estimate=True,
        )
        self.assertTrue(cost.is_estimate)

    def test_negative_amount_is_permitted(self):
        """Correction / reversal pattern per planning §1.6 design note.
        The ledger records corrections as a reversing row rather than
        editing the original — matches ACCOUNTING_DEPARTMENT_MAPPING
        §2.11 practice.
        """
        cost = VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("-150.00"),
            incurred_at=timezone.now(),
            reference="REVERSAL: original cost id=123",
        )
        self.assertEqual(cost.amount, Decimal("-150.00"))


class DealershipRequired(TestCase):
    """Same invariant as VehicleAcquisition — dealership FK NOT NULL
    from day one (greenfield table)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-COST-DEAL", self.default)

    def test_omitting_dealership_raises(self):
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                VehicleCost.objects.create(
                    vehicle=self.vehicle,
                    category=CATEGORY_PARTS,
                    amount=Decimal("50.00"),
                    incurred_at=timezone.now(),
                )

    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            VehicleCost._meta.get_field("dealership").null,
            "VehicleCost.dealership should be NOT NULL from day one",
        )


class CrossTenantClean(TestCase):
    """The denormalized ``dealership`` FK on VehicleCost must match the
    parent Vehicle's tenant. Same invariant as VehicleAcquisition."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-cost"
        )
        self.vehicle_at_a = _make_vehicle("M21-COST-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        cost = VehicleCost(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            category=CATEGORY_DETAIL,
            amount=Decimal("175.00"),
            incurred_at=timezone.now(),
        )
        cost.full_clean()  # should not raise

    def test_mismatched_dealership_raises_validation_error(self):
        cost = VehicleCost(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,  # wrong tenant
            category=CATEGORY_DETAIL,
            amount=Decimal("175.00"),
            incurred_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            cost.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class CascadeOnVehicleDelete(TestCase):
    """Deleting a Vehicle removes every VehicleCost row associated with
    it. Same identity-goes-away-costs-go-away rationale as
    VehicleAcquisition."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-COST-CASC", self.default)
        self.cost_pks = []
        for category, amount in [
            (CATEGORY_PARTS, Decimal("120.00")),
            (CATEGORY_MECHANICAL_LABOR, Decimal("340.00")),
            (CATEGORY_DETAIL, Decimal("85.00")),
        ]:
            cost = VehicleCost.objects.create(
                vehicle=self.vehicle,
                dealership=self.default,
                category=category,
                amount=amount,
                incurred_at=timezone.now(),
            )
            self.cost_pks.append(cost.pk)

    def test_delete_vehicle_removes_all_cost_rows(self):
        self.vehicle.delete()
        self.assertFalse(
            VehicleCost.objects.filter(pk__in=self.cost_pks).exists()
        )


class CreatedBySetNullOnUserDelete(TestCase):
    """When the authoring User is deleted, ``VehicleCost.created_by``
    becomes NULL — the cost row itself survives. Historical audit
    trail preserved (mirrors Salesperson.user SET_NULL rationale in
    Increment 4A)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-COST-USER", self.default)
        User = get_user_model()
        self.author = User.objects.create_user(
            username="soon-departing", password="test-pass-abcd"
        )
        self.cost = VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("640.00"),
            incurred_at=timezone.now(),
            created_by=self.author,
        )

    def test_user_delete_sets_created_by_null_leaves_cost_intact(self):
        cost_pk = self.cost.pk
        self.author.delete()
        surviving = VehicleCost.objects.get(pk=cost_pk)
        self.assertIsNone(surviving.created_by_id)
        # Amount + category still there — the row survived, only
        # provenance dropped.
        self.assertEqual(surviving.amount, Decimal("640.00"))
        self.assertEqual(surviving.category, CATEGORY_TIRES)


class ReverseRelation(TestCase):
    """The related_name is ``costs`` on Vehicle. Locks the accessor
    future ledger service will use (``vehicle.costs.all()``)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-COST-REV", self.default)
        self.pks = []
        for cat in (CATEGORY_PARTS, CATEGORY_DETAIL, CATEGORY_FUEL):
            c = VehicleCost.objects.create(
                vehicle=self.vehicle,
                dealership=self.default,
                category=cat,
                amount=Decimal("100"),
                incurred_at=timezone.now(),
            )
            self.pks.append(c.pk)

    def test_vehicle_dot_costs_returns_related_rows(self):
        vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        related_pks = set(vehicle.costs.values_list("pk", flat=True))
        self.assertEqual(related_pks, set(self.pks))

    def test_dealership_reverse_relation_works(self):
        # Custom related_name ``vehicle_costs`` on Dealership.
        related_pks = set(
            self.default.vehicle_costs.values_list("pk", flat=True)
        )
        self.assertTrue(set(self.pks).issubset(related_pks))


class OrderingContract(TestCase):
    """Newest cost surfaces first (``-incurred_at, -created_at``). The
    operator's default view is 'what was posted most recently?'."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M21-COST-ORD", self.default)
        now = timezone.now()
        # Insert out of chronological order to prove ORM ordering
        # takes precedence over insertion order.
        VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("100"),
            incurred_at=now - dt.timedelta(days=30),
        )
        VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_DETAIL,
            amount=Decimal("100"),
            incurred_at=now,
        )
        VehicleCost.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CATEGORY_FUEL,
            amount=Decimal("100"),
            incurred_at=now - dt.timedelta(days=10),
        )

    def test_default_ordering_surfaces_newest_first(self):
        categories = [c.category for c in VehicleCost.objects.all()]
        self.assertEqual(
            categories,
            [CATEGORY_DETAIL, CATEGORY_FUEL, CATEGORY_PARTS],
        )


class StringRepresentation(TestCase):
    """__str__ is what Django admin renders. Locks the shape."""

    def test_str_contains_category_amount_and_stock_number(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M21-COST-STR-STOCK", default)
        cost = VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=default,
            category=CATEGORY_PARTS,
            amount=Decimal("42.50"),
            incurred_at=timezone.now(),
        )
        as_string = str(cost)
        self.assertIn("Parts", as_string)
        self.assertIn("42.50", as_string)
        self.assertIn("M21-COST-STR-STOCK", as_string)
