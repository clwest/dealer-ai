"""Milestone 5 · Increment 5 (SESSION_079) — retail-gating refactor tests.

Locks the new behavior introduced by M5.5:

- ``customer_visible_vehicles()`` now filters on
  ``VehicleStage.current_stage='frontline'`` (via the
  ``_lifecycle_retail_eligible`` annotation), NOT on
  ``Vehicle.is_available``.
- ``stage=frontline`` + ``is_available=False`` → still
  retail-eligible (stage is authoritative per §5.e Option D).
- ``stage=recon`` + ``is_available=True`` → NOT retail-eligible
  (M1 flag doesn't override).
- ``annotate_retail_eligible(qs)`` populates the
  ``_lifecycle_retail_eligible`` boolean without colliding with
  the ``Vehicle.is_retail_eligible`` @property.
- ``inventory_import`` Vehicle creation path explicitly seeds a
  ``frontline`` stage with ``trigger='import'`` (write-path
  integration per §0.a item 6 — no signals in production).
- Vehicles without any ``VehicleStage`` row → ``is_retail_eligible
  == False`` via the @property.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    Dealership,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_RECON,
    VEHICLE_STAGE_TRIGGER_IMPORT,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
)
from dealer_ai.services.chat_engine import customer_visible_vehicles
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.services.vehicle_lifecycle import (
    annotate_retail_eligible,
    ensure_current_stage,
)
from dealer_ai.tests._tenancy_helpers import wipe_lifecycle_state


def _make_vehicle(stock: str, dealership: Dealership, *,
                  is_available: bool = True) -> Vehicle:
    """Local factory that wipes the M5.5 test-only auto-bootstrap so
    each test can seed the stage state it wants to observe."""
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        is_available=is_available,
        dealership=dealership,
    )
    return wipe_lifecycle_state(v)


class CustomerVisibleFiltersOnFrontlineStage(TestCase):
    """The choke-point queryset filters on stage=frontline, NOT
    is_available=True."""

    def setUp(self):
        self.default = get_default_dealership()

    def test_vehicle_without_stage_row_not_visible(self):
        v = _make_vehicle("M55-NOSTAGE", self.default)
        stocks = {row.stock_number for row in customer_visible_vehicles()}
        self.assertNotIn("M55-NOSTAGE", stocks)

    def test_vehicle_at_frontline_is_visible(self):
        v = _make_vehicle("M55-FRONT", self.default)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        stocks = {row.stock_number for row in customer_visible_vehicles()}
        self.assertIn("M55-FRONT", stocks)

    def test_vehicle_at_recon_not_visible_despite_is_available(self):
        """§5.e — is_available MUST NOT override lifecycle-driven
        retail gating. A vehicle stuck in recon with is_available=True
        (M1 legacy state) is NOT retail-eligible under M5."""
        v = _make_vehicle("M55-RECON", self.default, is_available=True)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_RECON,
        )
        stocks = {row.stock_number for row in customer_visible_vehicles()}
        self.assertNotIn("M55-RECON", stocks)

    def test_vehicle_at_frontline_visible_even_when_is_available_false(self):
        """§5.e — stage is authoritative. A vehicle at frontline with
        is_available=False (M1 legacy flag) IS retail-eligible under M5."""
        v = _make_vehicle("M55-FRONT-UNAV", self.default, is_available=False)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        stocks = {row.stock_number for row in customer_visible_vehicles()}
        self.assertIn("M55-FRONT-UNAV", stocks)

    def test_vehicle_at_off_market_not_visible(self):
        v = _make_vehicle("M55-OFF", self.default)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_OFF_MARKET,
        )
        stocks = {row.stock_number for row in customer_visible_vehicles()}
        self.assertNotIn("M55-OFF", stocks)


class AnnotateRetailEligibleQuerysetHelper(TestCase):
    """The annotation uses a distinct name from the @property to
    avoid the setter conflict Pyright/Django would otherwise raise."""

    def setUp(self):
        self.default = get_default_dealership()

    def test_annotation_name_is_lifecycle_prefixed(self):
        """Locks the naming choice — see helper docstring for why."""
        v = _make_vehicle("M55-ANNO-NAME", self.default)
        qs = annotate_retail_eligible(Vehicle.objects.filter(pk=v.pk))
        row = qs.first()
        # Attribute exists (annotation populated).
        self.assertTrue(hasattr(row, "_lifecycle_retail_eligible"))

    def test_annotation_false_when_no_stage(self):
        v = _make_vehicle("M55-ANNO-NOSTAGE", self.default)
        qs = annotate_retail_eligible(Vehicle.objects.filter(pk=v.pk))
        self.assertFalse(qs.first()._lifecycle_retail_eligible)

    def test_annotation_true_at_frontline(self):
        v = _make_vehicle("M55-ANNO-FRONT", self.default)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        qs = annotate_retail_eligible(Vehicle.objects.filter(pk=v.pk))
        self.assertTrue(qs.first()._lifecycle_retail_eligible)

    def test_annotation_false_at_non_frontline(self):
        v = _make_vehicle("M55-ANNO-RECON", self.default)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_RECON,
        )
        qs = annotate_retail_eligible(Vehicle.objects.filter(pk=v.pk))
        self.assertFalse(qs.first()._lifecycle_retail_eligible)


class VehicleWritePathIntegration(TestCase):
    """Inventory import writes explicit lifecycle state (§0.a item 6
    — no signals in production)."""

    def test_inventory_import_seeds_frontline_with_import_trigger(self):
        """Simulate what inventory_import.py does at :326: create a
        Vehicle + call ensure_current_stage(initial_stage=frontline,
        trigger=import). Locked by direct invocation because a full
        CSV import is a heavier integration."""
        default = get_default_dealership()
        v = _make_vehicle("M55-IMPORT", default)
        # No stage yet (wipe just fired).
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=v).count(), 0
        )
        # Simulate the inventory_import call.
        ensure_current_stage(
            v,
            dealership=default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
            trigger=VEHICLE_STAGE_TRIGGER_IMPORT,
        )
        stage = VehicleStage.objects.get(vehicle=v)
        self.assertEqual(stage.current_stage, VEHICLE_STAGE_FRONTLINE)
        self.assertEqual(stage.trigger, VEHICLE_STAGE_TRIGGER_IMPORT)
        # Bootstrap event mirrors.
        event = VehicleStageEvent.objects.get(vehicle=v)
        self.assertEqual(event.trigger, VEHICLE_STAGE_TRIGGER_IMPORT)
        self.assertIsNone(event.from_stage)


class VehiclePropertyReadThroughRefactor(TestCase):
    """The M5.2 ``Vehicle.is_retail_eligible`` @property remains
    a pure read (no side effects), coexisting with the M5.5
    ``annotate_retail_eligible`` queryset annotation."""

    def setUp(self):
        self.default = get_default_dealership()

    def test_property_returns_false_without_stage(self):
        v = _make_vehicle("M55-PROP-NOSTAGE", self.default)
        self.assertFalse(v.is_retail_eligible)

    def test_property_returns_true_at_frontline(self):
        v = _make_vehicle("M55-PROP-FRONT", self.default)
        ensure_current_stage(
            v, dealership=self.default,
            initial_stage=VEHICLE_STAGE_FRONTLINE,
        )
        self.assertTrue(v.is_retail_eligible)
