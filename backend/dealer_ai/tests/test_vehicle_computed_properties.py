"""Milestone 2 · Increment 3 — Vehicle-as-read-model tests.

Locks the read-model contract:

- Every ledger property on ``Vehicle`` delegates to
  ``services/vehicle_ledger.compute_totals`` — no duplicated math.
- ``@cached_property ledger_totals`` runs the six-query lookup
  exactly once per instance; nine subsequent property reads
  produce zero additional queries.
- ``days_in_inventory`` is temporal-not-financial (does not route
  through ``ledger_totals``); returns ``None`` when no acquisition
  record exists (documented invariant); safely handles a
  purchase_date in the future by returning 0 rather than a
  negative day count.
- Tenant borrowing: the read-model resolves ``dealership`` from
  ``self.dealership``; cross-tenant leakage is impossible from
  the property surface.

Scope guard — this file tests the *read-model plumbing*. All
financial arithmetic is already proven in ``test_vehicle_ledger.py``
(44 tests). These tests intentionally do NOT re-verify money math;
they verify the delegation contract holds and the caching does
what it claims to do.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_BODY_WORK,
    CATEGORY_PARTS,
    CATEGORY_PHOTOGRAPHY,
    CATEGORY_TIRES,
    SOURCE_AUCTION,
    Dealership,
    Vehicle,
)
from dealer_ai.services.vehicle_ledger import (
    ZERO,
    CrossTenantLedgerError,
    LedgerTotals,
    add_cost,
    compute_totals,
    record_acquisition,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Ranger",
        price=Decimal("34000.00"),
        dealership=dealership,
    )


# ---- Delegation contract --------------------------------------------------


class PropertyDelegatesToLedgerService(TestCase):
    """Each of the nine per-total properties reads the correspondingly-
    named field off the cached ``ledger_totals``. No parallel math."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M23-DELEGATE", self.default)
        record_acquisition(
            self.vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("18000.00"),
            purchase_date=dt.date(2026, 5, 1),
            buyer_fees=Decimal("500.00"),
            transportation_cost=Decimal("850.00"),
            title_acquisition_cost=Decimal("125.00"),
        )
        # Actual costs: $250 recon (parts) + $500 body work + $150 photo.
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("250.00"),
            incurred_at=timezone.now(),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_BODY_WORK,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PHOTOGRAPHY,
            amount=Decimal("150.00"),
            incurred_at=timezone.now(),
        )
        # Open estimate: $400 tires.
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("400.00"),
            incurred_at=timezone.now(),
            is_estimate=True,
        )
        # Refetch so any cached_property from the setUp writes doesn't
        # bleed into the property tests below.
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.expected = compute_totals(
            self.vehicle, dealership=self.default
        )
        # Re-refetch because the compute_totals() call above populated
        # the cached_property on this instance. Give the test a fresh
        # Vehicle for property-under-test reads.
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)

    def test_ledger_totals_returns_a_ledger_totals_instance(self):
        self.assertIsInstance(self.vehicle.ledger_totals, LedgerTotals)

    def test_total_investment_property_matches_service(self):
        self.assertEqual(
            self.vehicle.total_investment, self.expected.total_investment
        )

    def test_projected_total_investment_property_matches_service(self):
        self.assertEqual(
            self.vehicle.projected_total_investment,
            self.expected.projected_total_investment,
        )

    def test_acquisition_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.acquisition_total, self.expected.acquisition_total
        )

    def test_actual_cost_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.actual_cost_total, self.expected.actual_cost_total
        )

    def test_estimated_cost_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.estimated_cost_total,
            self.expected.estimated_cost_total,
        )

    def test_flooring_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.flooring_total, self.expected.flooring_total
        )

    def test_recon_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.recon_total, self.expected.recon_total
        )

    def test_administrative_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.administrative_total,
            self.expected.administrative_total,
        )

    def test_photography_total_property_matches_service(self):
        self.assertEqual(
            self.vehicle.photography_total, self.expected.photography_total
        )


# ---- Caching contract -----------------------------------------------------


class CachedPropertyRunsOnce(TestCase):
    """``ledger_totals`` runs exactly once per Vehicle instance;
    every subsequent property read produces zero additional queries.

    This is the "one cached ledger lookup, many property reads"
    invariant from the SESSION_048 brief."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M23-CACHE", self.default)
        record_acquisition(
            self.vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("300.00"),
            incurred_at=timezone.now(),
        )

    def _fresh_vehicle(self) -> Vehicle:
        # Force a re-read so cached_property is clean at test start.
        return Vehicle.objects.get(pk=self.vehicle.pk)

    def test_first_ledger_totals_read_triggers_queries(self):
        # ``ledger_totals`` on a fresh instance triggers seven queries:
        # 1 lazy Dealership load (``vehicle.dealership`` — Django only
        #   loads the FK id at Vehicle fetch time, not the related row)
        #   + 6 from ``compute_totals`` (1 acquisition + 4 category
        #   aggregates + 1 estimate aggregate).
        # If a future optimization drops the Dealership lazy-load
        # (e.g. by accepting ``dealership_id`` in the service), this
        # expected count should drop to 6 accordingly.
        vehicle = self._fresh_vehicle()
        with self.assertNumQueries(7):
            _ = vehicle.ledger_totals

    def test_second_ledger_totals_read_uses_cache_zero_queries(self):
        vehicle = self._fresh_vehicle()
        # Prime the cache.
        _ = vehicle.ledger_totals
        # Second access must be zero queries.
        with self.assertNumQueries(0):
            _ = vehicle.ledger_totals

    def test_nine_property_reads_after_priming_are_zero_queries(self):
        """After the first ``ledger_totals`` read primes the cache,
        reading all nine per-total properties triggers zero queries.
        The 'one cached lookup, many property reads' invariant.
        """
        vehicle = self._fresh_vehicle()
        # Prime the cache.
        _ = vehicle.ledger_totals
        with self.assertNumQueries(0):
            _ = vehicle.total_investment
            _ = vehicle.projected_total_investment
            _ = vehicle.acquisition_total
            _ = vehicle.actual_cost_total
            _ = vehicle.estimated_cost_total
            _ = vehicle.flooring_total
            _ = vehicle.recon_total
            _ = vehicle.administrative_total
            _ = vehicle.photography_total

    def test_first_property_access_primes_cache_for_the_others(self):
        """A caller who reads a single per-total property (rather
        than ``ledger_totals`` directly) still benefits from the
        cache — subsequent per-total reads are zero queries."""
        vehicle = self._fresh_vehicle()
        # Reading `total_investment` triggers `ledger_totals` which
        # runs seven queries (see
        # ``test_first_ledger_totals_read_triggers_queries`` for the
        # breakdown).
        with self.assertNumQueries(7):
            _ = vehicle.total_investment
        # Every subsequent per-total read is free.
        with self.assertNumQueries(0):
            _ = vehicle.projected_total_investment
            _ = vehicle.recon_total
            _ = vehicle.photography_total

    def test_cache_is_per_instance_not_per_class(self):
        """Two distinct Vehicle instances (even for the same DB row)
        each get their own cached_property store — the cache does
        not leak across instances."""
        v1 = self._fresh_vehicle()
        v2 = self._fresh_vehicle()
        _ = v1.ledger_totals
        # v2 has not been primed, so its first read still queries
        # (same seven queries — see
        # ``test_first_ledger_totals_read_triggers_queries``).
        with self.assertNumQueries(7):
            _ = v2.ledger_totals


# ---- Empty / populated states ---------------------------------------------


class ReadModelHandlesEmptyStates(TestCase):
    """Vehicles with no ledger data return ``ZERO`` on every
    financial property (never ``None``) — same contract as the
    underlying ``compute_totals``."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_bare_vehicle_returns_zero_on_every_total(self):
        vehicle = _make_vehicle("M23-EMPTY", self.default)
        for field in (
            "total_investment",
            "projected_total_investment",
            "acquisition_total",
            "actual_cost_total",
            "estimated_cost_total",
            "flooring_total",
            "recon_total",
            "administrative_total",
            "photography_total",
        ):
            self.assertEqual(
                getattr(vehicle, field),
                ZERO,
                f"Vehicle.{field} on bare vehicle should equal ZERO",
            )
            self.assertIsInstance(
                getattr(vehicle, field),
                Decimal,
                f"Vehicle.{field} must be a Decimal, not None",
            )


class ReadModelReflectsMixedLedger(TestCase):
    """End-to-end smoke: a populated ledger routes cleanly through
    the read model. Financial specifics already proven in
    ``test_vehicle_ledger.py``; this is a delegation smoke, not a
    re-verification of math."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M23-MIXED", self.default)
        record_acquisition(
            self.vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("300.00"),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_BODY_WORK,
            amount=Decimal("400.00"),
            incurred_at=timezone.now(),
            is_estimate=True,
        )
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)

    def test_read_model_preserves_actual_vs_estimated_semantic(self):
        # Actual = $15,000 + $300 = $15,300.
        # Estimated = $400.
        # Projected = $15,700.
        self.assertEqual(self.vehicle.total_investment, Decimal("15300.00"))
        self.assertEqual(self.vehicle.estimated_cost_total, Decimal("400.00"))
        self.assertEqual(
            self.vehicle.projected_total_investment, Decimal("15700.00")
        )


class ReadModelHandlesReversingEntry(TestCase):
    """Negative reversing rows collapse the net through the read
    model without special handling."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M23-REVERSAL", self.default)
        record_acquisition(
            self.vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("10000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("-500.00"),
            incurred_at=timezone.now(),
            reference="reversal",
        )
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)

    def test_net_recon_total_is_zero_after_reversal(self):
        self.assertEqual(self.vehicle.recon_total, ZERO)

    def test_total_investment_reflects_the_net(self):
        # $10,000 acquisition + net actual $0 = $10,000.
        self.assertEqual(self.vehicle.total_investment, Decimal("10000.00"))


# ---- days_in_inventory ----------------------------------------------------


class DaysInInventoryTemporalMetric(TestCase):
    """``days_in_inventory`` uses acquisition.purchase_date when
    present, returns ``None`` when no acquisition exists, and
    clamps a future purchase_date to 0 rather than emitting a
    negative day count."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_no_acquisition_returns_none(self):
        vehicle = _make_vehicle("M23-DAYS-NO-ACQ", self.default)
        self.assertIsNone(vehicle.days_in_inventory)

    def test_recent_acquisition_returns_positive_days(self):
        vehicle = _make_vehicle("M23-DAYS-RECENT", self.default)
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        record_acquisition(
            vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=thirty_days_ago,
        )
        vehicle = Vehicle.objects.get(pk=vehicle.pk)
        # Exact days_in_inventory depends on when the test runs
        # relative to midnight, so lock a small window.
        days = vehicle.days_in_inventory
        self.assertIsNotNone(days)
        self.assertIn(days, (29, 30, 31))

    def test_today_acquisition_returns_zero(self):
        vehicle = _make_vehicle("M23-DAYS-TODAY", self.default)
        record_acquisition(
            vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=timezone.now().date(),
        )
        vehicle = Vehicle.objects.get(pk=vehicle.pk)
        self.assertEqual(vehicle.days_in_inventory, 0)

    def test_future_purchase_date_clamps_to_zero(self):
        # Data-entry error: a purchase_date in the future should
        # surface as "0 days" (i.e. "today") rather than as a
        # negative day count that would break aging math.
        vehicle = _make_vehicle("M23-DAYS-FUTURE", self.default)
        tomorrow = timezone.now().date() + dt.timedelta(days=1)
        record_acquisition(
            vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=tomorrow,
        )
        vehicle = Vehicle.objects.get(pk=vehicle.pk)
        self.assertEqual(vehicle.days_in_inventory, 0)


class DaysInInventoryUsesOneToOneCache(TestCase):
    """``days_in_inventory`` and ``ledger_totals`` both access
    ``vehicle.acquisition``. Django caches the OneToOne reverse
    accessor on the Vehicle instance, so calling both together
    does not double-query the acquisition row."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M23-DAYS-CACHE", self.default)
        record_acquisition(
            self.vehicle,
            dealership=self.default,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=timezone.now().date() - dt.timedelta(days=10),
        )

    def test_reading_days_after_totals_does_not_query_acquisition_again(self):
        vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        # Prime `ledger_totals` (which internally accesses
        # `vehicle.acquisition`).
        _ = vehicle.ledger_totals
        # Now `days_in_inventory` needs `vehicle.acquisition.purchase_date`.
        # Django's OneToOne reverse cache means this is a zero-query
        # access.
        with self.assertNumQueries(0):
            _ = vehicle.days_in_inventory


# ---- Tenant isolation -----------------------------------------------------


class VehicleReadModelTenantIsolation(TestCase):
    """The read model resolves ``dealership`` from
    ``self.dealership``. Cross-tenant data leakage through the
    property surface is impossible because a Vehicle's own
    dealership and the resolver's dealership are the same
    reference by construction.

    Two-tenant data isolation is the practical invariant: costs
    added to Vehicle A never appear in Vehicle B's totals, even
    though both vehicles are queried through the same
    ``ledger_totals`` property surface.
    """

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-readmodel"
        )
        self.vehicle_at_a = _make_vehicle("M23-TENANT-A", self.dealership_a)
        self.vehicle_at_b = _make_vehicle("M23-TENANT-B", self.dealership_b)
        record_acquisition(
            self.vehicle_at_a,
            dealership=self.dealership_a,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("15000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        record_acquisition(
            self.vehicle_at_b,
            dealership=self.dealership_b,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("22000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        add_cost(
            self.vehicle_at_a,
            dealership=self.dealership_a,
            category=CATEGORY_PARTS,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
        )

    def test_normal_access_returns_correct_totals(self):
        vehicle = Vehicle.objects.get(pk=self.vehicle_at_a.pk)
        self.assertEqual(vehicle.total_investment, Decimal("15500.00"))

    def test_vehicle_a_totals_do_not_include_vehicle_b_data(self):
        """The read model reads only the target vehicle's costs +
        acquisition — Vehicle A's totals must not include anything
        from Vehicle B (in either tenant)."""
        vehicle_a = Vehicle.objects.get(pk=self.vehicle_at_a.pk)
        vehicle_b = Vehicle.objects.get(pk=self.vehicle_at_b.pk)
        # A has $15,000 acquisition + $500 parts = $15,500.
        self.assertEqual(vehicle_a.total_investment, Decimal("15500.00"))
        # B has $22,000 acquisition + no costs = $22,000. If the
        # read model leaked across tenants, B would show A's
        # $500 parts too — the assertion would catch it.
        self.assertEqual(vehicle_b.total_investment, Decimal("22000.00"))
        self.assertEqual(vehicle_b.recon_total, ZERO)

    def test_read_model_uses_vehicles_own_dealership_not_ambient_state(self):
        """No hidden request-context lookup — the property resolves
        ``dealership`` from ``self.dealership`` exclusively. A
        vehicle read from any code path (management command, admin
        shell, request handler) produces the same totals."""
        vehicle_a_1 = Vehicle.objects.get(pk=self.vehicle_at_a.pk)
        vehicle_a_2 = Vehicle.objects.filter(
            pk=self.vehicle_at_a.pk
        ).first()
        self.assertEqual(
            vehicle_a_1.total_investment, vehicle_a_2.total_investment
        )

    def test_cross_tenant_error_still_raises_when_service_is_called_directly(self):
        """Defense-in-depth check: the service-layer guard fires
        when someone bypasses the read model and calls
        ``compute_totals`` with a mismatched dealership. This is
        the M2.2 contract, re-verified here to confirm the read
        model does not accidentally weaken it."""
        vehicle = Vehicle.objects.get(pk=self.vehicle_at_a.pk)
        with self.assertRaises(CrossTenantLedgerError):
            compute_totals(vehicle, dealership=self.dealership_b)


# ---- Public-API discipline: no writes, no side effects --------------------


class PropertiesAreSideEffectFree(TestCase):
    """Reading any Vehicle property must not create rows, must not
    mutate the DB, must not lazily upsert an acquisition."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_reading_properties_on_bare_vehicle_creates_no_rows(self):
        from dealer_ai.models import VehicleAcquisition, VehicleCost

        vehicle = _make_vehicle("M23-SIDEEFFECT", self.default)
        # Sanity — no ledger rows exist yet for this vehicle.
        self.assertFalse(
            VehicleAcquisition.objects.filter(vehicle=vehicle).exists()
        )
        self.assertFalse(
            VehicleCost.objects.filter(vehicle=vehicle).exists()
        )
        # Read every property that could plausibly be a foot-gun
        # for lazy creation.
        _ = vehicle.days_in_inventory
        _ = vehicle.total_investment
        _ = vehicle.projected_total_investment
        _ = vehicle.acquisition_total
        # Confirm no rows were lazily created by the reads.
        self.assertFalse(
            VehicleAcquisition.objects.filter(vehicle=vehicle).exists()
        )
        self.assertFalse(
            VehicleCost.objects.filter(vehicle=vehicle).exists()
        )
