"""Milestone 5 · Increment 1 (SESSION_075) — bootstrap migration tests.

Tests for the ``0017_vehicle_lifecycle_persistence`` data-migration
step. Every existing Vehicle must land at ``frontline`` if
``is_available=True`` else ``off_market``; every Vehicle must have
exactly one bootstrap ``VehicleStageEvent`` mirroring the stage row.

The migration function is imported directly and invoked against the
live app registry so we can seed test Vehicles in setUp and then
re-run the bootstrap idempotently. This mirrors the pattern used
implicitly by M1's ``0009`` migration (whose default-Dealership
seeding is asserted indirectly across the suite via
``Dealership.objects.get(slug='default')``).

Locked invariants (per §5.c Option C, SESSION_075 refinement):

1. Every existing Vehicle gets one ``VehicleStage`` row.
2. Every existing Vehicle gets one bootstrap ``VehicleStageEvent``.
3. Event ``to_stage`` matches paired stage's ``current_stage``.
4. Event ``from_stage`` is NULL.
5. Event ``entered_at`` equals paired stage's ``entered_at``.
6. Event ``trigger='bootstrap'``.
7. Both rows' ``dealership`` matches vehicle's ``dealership``.
8. ``is_available=True`` → ``current_stage='frontline'``.
9. ``is_available=False`` → ``current_stage='off_market'``.
10. Empty DB is safe (no-op).
11. Idempotent — a re-run adds no duplicate rows.
12. ``Vehicle.is_available`` schema and values unchanged.
13. Reverse (unbootstrap) removes all bootstrap rows without
    touching ``Vehicle.is_available``.
"""

from __future__ import annotations

from decimal import Decimal

from django.apps import apps as django_apps
from django.test import TestCase

from dealer_ai.models import (
    Dealership,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
)

# Import the migration's RunPython callables directly. Django's migration
# framework runs these against a historical `apps` registry, but the
# functions themselves work against any registry with the required
# models, which lets us seed test fixtures and re-invoke bootstrap.
import importlib

_migration_module = importlib.import_module(
    "dealer_ai.migrations.0017_vehicle_lifecycle_persistence"
)
bootstrap_vehicle_stages = _migration_module.bootstrap_vehicle_stages
unbootstrap_vehicle_stages = _migration_module.unbootstrap_vehicle_stages


def _clear_all_bootstrap_rows() -> None:
    """Reset the ledger so a test can run bootstrap from a known state.

    The migration already ran during test-DB setup (against an empty
    Vehicle table, so it was a no-op). Test setUp creates Vehicles,
    then this helper wipes any stage/event rows a prior test may have
    inserted so the current test starts from a clean slate.
    """
    VehicleStageEvent.objects.all().delete()
    VehicleStage.objects.all().delete()


def _make_vehicle(
    stock: str, dealership: Dealership, *, is_available: bool = True
) -> Vehicle:
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        is_available=is_available,
        dealership=dealership,
    )
    # M5.5 test-only auto-bootstrap; wipe for M5.1 migration tests
    # that need to observe the migration bootstrap step directly.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


class BootstrapMigrationAvailableBecomesFrontline(TestCase):
    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "M51BOOT-AVAIL", self.default, is_available=True
        )

    def test_available_vehicle_receives_frontline_stage(self):
        bootstrap_vehicle_stages(django_apps, None)
        stage = VehicleStage.objects.get(vehicle=self.vehicle)
        self.assertEqual(stage.current_stage, VEHICLE_STAGE_FRONTLINE)
        self.assertEqual(stage.trigger, VEHICLE_STAGE_TRIGGER_BOOTSTRAP)
        self.assertIsNone(stage.entered_by_id)


class BootstrapMigrationUnavailableBecomesOffMarket(TestCase):
    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "M51BOOT-UNAVAIL", self.default, is_available=False
        )

    def test_unavailable_vehicle_receives_off_market_stage(self):
        bootstrap_vehicle_stages(django_apps, None)
        stage = VehicleStage.objects.get(vehicle=self.vehicle)
        self.assertEqual(stage.current_stage, VEHICLE_STAGE_OFF_MARKET)
        self.assertEqual(stage.trigger, VEHICLE_STAGE_TRIGGER_BOOTSTRAP)


class BootstrapMigrationOneStagePerVehicle(TestCase):
    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.available = _make_vehicle(
            "M51BOOT-1PER-A", self.default, is_available=True
        )
        self.unavailable = _make_vehicle(
            "M51BOOT-1PER-U", self.default, is_available=False
        )

    def test_exactly_one_stage_row_per_vehicle(self):
        bootstrap_vehicle_stages(django_apps, None)
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=self.available).count(), 1
        )
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=self.unavailable).count(), 1
        )


class BootstrapMigrationOneEventPerVehicle(TestCase):
    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "M51BOOT-1EVT", self.default, is_available=True
        )

    def test_exactly_one_bootstrap_event_per_vehicle(self):
        bootstrap_vehicle_stages(django_apps, None)
        events = VehicleStageEvent.objects.filter(
            vehicle=self.vehicle, trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP
        )
        self.assertEqual(events.count(), 1)


class BootstrapMigrationEventMatchesStage(TestCase):
    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.avail = _make_vehicle(
            "M51BOOT-MATCH-A", self.default, is_available=True
        )
        self.unavail = _make_vehicle(
            "M51BOOT-MATCH-U", self.default, is_available=False
        )

    def test_event_to_stage_matches_stage_current_stage(self):
        bootstrap_vehicle_stages(django_apps, None)
        for vehicle in (self.avail, self.unavail):
            stage = VehicleStage.objects.get(vehicle=vehicle)
            event = VehicleStageEvent.objects.get(
                vehicle=vehicle, trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP
            )
            self.assertEqual(event.to_stage, stage.current_stage)

    def test_event_from_stage_is_null(self):
        bootstrap_vehicle_stages(django_apps, None)
        for vehicle in (self.avail, self.unavail):
            event = VehicleStageEvent.objects.get(
                vehicle=vehicle, trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP
            )
            self.assertIsNone(event.from_stage)

    def test_event_entered_at_matches_stage_entered_at(self):
        """Migration MUST use one ``timezone.now()`` value per vehicle so
        the invariant is enforceable (a second .now() call would drift
        by microseconds)."""
        bootstrap_vehicle_stages(django_apps, None)
        for vehicle in (self.avail, self.unavail):
            stage = VehicleStage.objects.get(vehicle=vehicle)
            event = VehicleStageEvent.objects.get(
                vehicle=vehicle, trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP
            )
            self.assertEqual(event.entered_at, stage.entered_at)


class BootstrapMigrationDealershipCorrect(TestCase):
    """Bootstrap threads ``dealership`` explicitly from the parent
    Vehicle; it does NOT rely on the pre_save autofill safety net."""

    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-boot"
        )
        self.default_vehicle = _make_vehicle(
            "M51BOOT-D-DEFAULT", self.default, is_available=True
        )
        self.other_vehicle = _make_vehicle(
            "M51BOOT-D-OTHER", self.other, is_available=True
        )

    def test_stage_dealership_matches_vehicle_dealership(self):
        bootstrap_vehicle_stages(django_apps, None)
        default_stage = VehicleStage.objects.get(vehicle=self.default_vehicle)
        other_stage = VehicleStage.objects.get(vehicle=self.other_vehicle)
        self.assertEqual(default_stage.dealership_id, self.default.pk)
        self.assertEqual(other_stage.dealership_id, self.other.pk)

    def test_event_dealership_matches_vehicle_dealership(self):
        bootstrap_vehicle_stages(django_apps, None)
        default_event = VehicleStageEvent.objects.get(
            vehicle=self.default_vehicle,
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        other_event = VehicleStageEvent.objects.get(
            vehicle=self.other_vehicle,
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        self.assertEqual(default_event.dealership_id, self.default.pk)
        self.assertEqual(other_event.dealership_id, self.other.pk)


class BootstrapMigrationEmptyDatabase(TestCase):
    """No Vehicles → bootstrap is a no-op. Confirmed via the migration
    already having run during test-DB setup against an empty Vehicle
    table (that's the reason ``_clear_all_bootstrap_rows()`` is a
    prerequisite in the other test classes)."""

    def test_bootstrap_on_empty_database_is_safe(self):
        _clear_all_bootstrap_rows()
        # No Vehicles seeded. Calling bootstrap must not raise and must
        # produce zero stage/event rows.
        bootstrap_vehicle_stages(django_apps, None)
        self.assertEqual(VehicleStage.objects.count(), 0)
        self.assertEqual(
            VehicleStageEvent.objects.filter(
                trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP
            ).count(),
            0,
        )


class BootstrapMigrationIdempotent(TestCase):
    """Re-running bootstrap must skip vehicles that already have a
    stage row — a partial re-run must not duplicate."""

    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "M51BOOT-IDEMPOTENT", self.default, is_available=True
        )

    def test_second_run_creates_no_additional_rows(self):
        bootstrap_vehicle_stages(django_apps, None)
        bootstrap_vehicle_stages(django_apps, None)
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=self.vehicle).count(), 1
        )
        self.assertEqual(
            VehicleStageEvent.objects.filter(
                vehicle=self.vehicle,
                trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
            ).count(),
            1,
        )


class BootstrapMigrationDoesNotAlterVehicleIsAvailable(TestCase):
    """The migration MUST NOT touch ``Vehicle.is_available`` values."""

    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.avail = _make_vehicle(
            "M51BOOT-NOALT-A", self.default, is_available=True
        )
        self.unavail = _make_vehicle(
            "M51BOOT-NOALT-U", self.default, is_available=False
        )

    def test_is_available_values_unchanged_after_bootstrap(self):
        bootstrap_vehicle_stages(django_apps, None)
        self.avail.refresh_from_db()
        self.unavail.refresh_from_db()
        self.assertTrue(self.avail.is_available)
        self.assertFalse(self.unavail.is_available)

    def test_is_available_schema_unchanged(self):
        """``is_available`` remains a BooleanField (not migrated to a
        property or computed column). Per §5.e Option D."""
        field = Vehicle._meta.get_field("is_available")
        self.assertEqual(field.get_internal_type(), "BooleanField")


class BootstrapMigrationReverseRestoresBaseline(TestCase):
    """The reverse ``unbootstrap_vehicle_stages`` deletes every
    bootstrap row without touching ``Vehicle.is_available``."""

    def setUp(self):
        _clear_all_bootstrap_rows()
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "M51BOOT-REV", self.default, is_available=True
        )

    def test_reverse_removes_bootstrap_rows(self):
        bootstrap_vehicle_stages(django_apps, None)
        self.assertEqual(VehicleStage.objects.count(), 1)
        unbootstrap_vehicle_stages(django_apps, None)
        self.assertEqual(VehicleStage.objects.count(), 0)
        self.assertEqual(
            VehicleStageEvent.objects.filter(
                trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP
            ).count(),
            0,
        )

    def test_reverse_does_not_touch_vehicle_is_available(self):
        bootstrap_vehicle_stages(django_apps, None)
        unbootstrap_vehicle_stages(django_apps, None)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.is_available)

    def test_reverse_then_forward_is_stable(self):
        """A rollback + reapply cycle produces exactly the same shape
        (equivalent to a ``migration_check`` roundtrip)."""
        bootstrap_vehicle_stages(django_apps, None)
        unbootstrap_vehicle_stages(django_apps, None)
        bootstrap_vehicle_stages(django_apps, None)
        self.assertEqual(
            VehicleStage.objects.filter(vehicle=self.vehicle).count(), 1
        )
        self.assertEqual(
            VehicleStageEvent.objects.filter(
                vehicle=self.vehicle,
                trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
            ).count(),
            1,
        )


class TenancyCarriersExtended(TestCase):
    """``_TENANT_CARRIER_MODEL_NAMES`` extended from 15 → 17. Verified
    against the actual tuple in ``services.tenancy``."""

    def test_carrier_count_is_seventeen(self):
        from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES
        self.assertEqual(len(_TENANT_CARRIER_MODEL_NAMES), 17)

    def test_new_carriers_include_stage_and_event(self):
        from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES
        self.assertIn("VehicleStage", _TENANT_CARRIER_MODEL_NAMES)
        self.assertIn("VehicleStageEvent", _TENANT_CARRIER_MODEL_NAMES)

    def test_all_prior_m4_carriers_preserved(self):
        """M1/M2/M3/M4 carriers unchanged — additive only."""
        from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES
        expected_prior = {
            "Vehicle",
            "Salesperson",
            "ChatSession",
            "ChatMessage",
            "CustomerLead",
            "DealerOnboardingProfile",
            "ConditionReport",
            "ConditionFinding",
            "ConditionFindingPhoto",
            "Vendor",
            "ReconDecision",
            "WorkOrder",
            "WorkOrderFinding",
            "WorkOrderPart",
            "VendorCommunication",
        }
        self.assertTrue(expected_prior.issubset(set(_TENANT_CARRIER_MODEL_NAMES)))


class TenancyAutofillWiredForNewCarriers(TestCase):
    """The pre_save autofill safety net attaches the default dealership
    when neither is passed. This is a smoke test that the new carriers
    are wired into the same signal — the primary write path (M5.2
    service) will thread ``dealership=`` explicitly, but the safety
    net must catch a direct ORM misuse."""

    def test_stage_created_without_dealership_gets_default(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51BOOT-AUTOFILL", default)
        from django.utils import timezone as tz
        stage = VehicleStage.objects.create(
            vehicle=vehicle,
            # dealership omitted deliberately — the pre_save handler
            # should fill in the default.
            current_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=tz.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        stage.refresh_from_db()
        self.assertEqual(stage.dealership_id, default.pk)

    def test_event_created_without_dealership_gets_default(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M51BOOT-EAUTOFILL", default)
        from django.utils import timezone as tz
        event = VehicleStageEvent.objects.create(
            vehicle=vehicle,
            # dealership omitted deliberately.
            from_stage=None,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=tz.now(),
            trigger=VEHICLE_STAGE_TRIGGER_BOOTSTRAP,
        )
        event.refresh_from_db()
        self.assertEqual(event.dealership_id, default.pk)
