"""Milestone 6 · Increment 1 (SESSION_082) — tenancy-carrier extension tests.

Verifies that ``services/tenancy.py::_TENANT_CARRIER_MODEL_NAMES`` was
extended from 17 → 19 entries and that the ``pre_save`` autofill signal
wires cleanly for both new carriers (``VehiclePhoto``,
``VehicleListing``).

Mirrors the M5.1 shape in
``test_vehicle_lifecycle_bootstrap.py::TenancyCarriersExtended`` +
``TenancyAutofillWiredForNewCarriers``.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    Dealership,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    Vehicle,
    VehicleListing,
    VehiclePhoto,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


class TenancyCarriersExtended(TestCase):
    """The M6.1 extension adds ``VehiclePhoto`` + ``VehicleListing`` to
    the 17-entry M5.1 tuple, yielding 19."""

    def test_carrier_count_is_nineteen(self):
        self.assertEqual(
            len(_TENANT_CARRIER_MODEL_NAMES),
            19,
            "Milestone 6 · Increment 1 extended the tenancy-carrier "
            "tuple from 17 → 19 (added VehiclePhoto + VehicleListing).",
        )

    def test_new_carriers_present(self):
        self.assertIn("VehiclePhoto", _TENANT_CARRIER_MODEL_NAMES)
        self.assertIn("VehicleListing", _TENANT_CARRIER_MODEL_NAMES)

    def test_prior_carriers_preserved(self):
        """Every M1–M5 carrier must remain — additive extension only."""
        expected_prior = {
            # M1
            "Vehicle",
            "Salesperson",
            "ChatSession",
            "ChatMessage",
            "CustomerLead",
            "DealerOnboardingProfile",
            # M3
            "ConditionReport",
            "ConditionFinding",
            "ConditionFindingPhoto",
            # M4
            "Vendor",
            "ReconDecision",
            "WorkOrder",
            "WorkOrderFinding",
            "WorkOrderPart",
            "VendorCommunication",
            # M5
            "VehicleStage",
            "VehicleStageEvent",
        }
        actual = set(_TENANT_CARRIER_MODEL_NAMES)
        missing = expected_prior - actual
        self.assertEqual(
            missing,
            set(),
            f"M1–M5 tenancy carriers must be preserved; missing: {missing}",
        )


class TenancyAutofillWiredForVehiclePhoto(TestCase):
    """The ``pre_save`` autofill signal registered by
    :func:`register_default_dealership_autofill` covers the new M6.1
    carriers. Smoke test: a photo saved without ``dealership=`` gets
    the default attached automatically."""

    def test_photo_pre_save_autofills_default_dealership(self):
        default = Dealership.objects.get(slug="default")
        vehicle = Vehicle.objects.create(
            stock_number="M61TENANT-VP",
            year=2024,
            model="Escape",
            price=Decimal("22500.00"),
            dealership=default,
        )
        # Deliberately omit dealership= — the autofill safety net should
        # attach the default before save() persists the row.
        photo = VehiclePhoto(
            vehicle=vehicle,
            storage_key="dealerships/default/vehicle-photos/tenant/original",
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            width_px=800,
            height_px=600,
        )
        photo.save()
        photo.refresh_from_db()
        self.assertEqual(photo.dealership_id, default.pk)


class TenancyAutofillWiredForVehicleListing(TestCase):
    """Same smoke test for :class:`VehicleListing`."""

    def test_listing_pre_save_autofills_default_dealership(self):
        default = Dealership.objects.get(slug="default")
        vehicle = Vehicle.objects.create(
            stock_number="M61TENANT-VL",
            year=2024,
            model="Escape",
            price=Decimal("22500.00"),
            dealership=default,
        )
        listing = VehicleListing(vehicle=vehicle)
        listing.save()
        listing.refresh_from_db()
        self.assertEqual(listing.dealership_id, default.pk)
