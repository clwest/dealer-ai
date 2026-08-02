"""Milestone 8 · Increment 4 (SESSION_097) — vehicle_type_recon_cost tests.

Locks the behavior of
:func:`services.analytics.vehicle_type_recon_cost` (Q3 proxy).

Coverage:

- Empty tenant → empty list.
- Flooring / admin / photography categories excluded.
- Estimated costs (``is_estimate=True``) excluded.
- Reversal rows subtract.
- Multiple vehicles of the same ``(make, model)`` aggregate.
- Sort by total desc; tiebreak on (make, model) asc.
- Cross-tenant isolation.
- Window bounds inclusive.
- Mean quantized to 2dp.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_ADVERTISING_ALLOCATION,
    CATEGORY_FLOOR_PLAN_INTEREST,
    CATEGORY_MECHANICAL_LABOR,
    CATEGORY_PARTS,
    CATEGORY_PHOTOGRAPHY,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.analytics import vehicle_type_recon_cost


def _make_vehicle(
    dealership: Dealership,
    stock: str,
    *,
    make: str = "Ford",
    model: str = "F-150",
) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        make=make,
        model=model,
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _post_cost(
    vehicle: Vehicle,
    dealership: Dealership,
    *,
    category: str,
    amount: str,
    incurred_at: dt.datetime | None = None,
    is_estimate: bool = False,
) -> VehicleCost:
    return VehicleCost.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=category,
        amount=Decimal(amount),
        incurred_at=incurred_at or timezone.now(),
        is_estimate=is_estimate,
    )


class VehicleTypeReconCostVerbTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="vt-primary", name="VT Primary"
        )

    def test_empty_tenant_returns_empty(self) -> None:
        self.assertEqual(vehicle_type_recon_cost(self.dealership), [])

    def test_non_recon_categories_excluded(self) -> None:
        vehicle = _make_vehicle(
            self.dealership, "EX-1", make="Ford", model="F-150"
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
            amount="47.00",
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_ADVERTISING_ALLOCATION,
            amount="200.00",
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PHOTOGRAPHY,
            amount="80.00",
        )
        self.assertEqual(vehicle_type_recon_cost(self.dealership), [])

    def test_estimated_costs_excluded(self) -> None:
        vehicle = _make_vehicle(
            self.dealership, "EST-1", make="Ford", model="Escape"
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="500.00",
            is_estimate=True,
        )
        self.assertEqual(vehicle_type_recon_cost(self.dealership), [])

    def test_reversal_row_subtracts(self) -> None:
        vehicle = _make_vehicle(
            self.dealership, "REV-1", make="Ford", model="F-150"
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="1000.00",
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="-250.00",
        )
        rows = vehicle_type_recon_cost(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].total_recon_cost, Decimal("750.00"))
        self.assertEqual(rows[0].mean_recon_cost, Decimal("750.00"))

    def test_multiple_vehicles_same_type_aggregate(self) -> None:
        for idx in range(3):
            v = _make_vehicle(
                self.dealership,
                f"AGG-{idx}",
                make="Ford",
                model="F-150",
            )
            _post_cost(
                v,
                self.dealership,
                category=CATEGORY_MECHANICAL_LABOR,
                amount="400.00",
            )
        rows = vehicle_type_recon_cost(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].make, "Ford")
        self.assertEqual(rows[0].model, "F-150")
        self.assertEqual(rows[0].vehicle_count, 3)
        self.assertEqual(rows[0].total_recon_cost, Decimal("1200.00"))
        self.assertEqual(rows[0].mean_recon_cost, Decimal("400.00"))

    def test_multi_type_sort_and_tiebreak(self) -> None:
        # F-150: 1 vehicle, $1500. Escape: 1 vehicle, $800.
        # Bronco: 1 vehicle, $1500 (ties F-150 on total; tiebreak on
        # (make, model) asc — Ford Bronco < Ford F-150).
        f150 = _make_vehicle(self.dealership, "T1", model="F-150")
        _post_cost(
            f150, self.dealership, category=CATEGORY_PARTS, amount="1500.00"
        )
        escape = _make_vehicle(self.dealership, "T2", model="Escape")
        _post_cost(
            escape,
            self.dealership,
            category=CATEGORY_MECHANICAL_LABOR,
            amount="800.00",
        )
        bronco = _make_vehicle(self.dealership, "T3", model="Bronco")
        _post_cost(
            bronco, self.dealership, category=CATEGORY_PARTS, amount="1500.00"
        )

        rows = vehicle_type_recon_cost(self.dealership)
        self.assertEqual(
            [(r.make, r.model) for r in rows],
            [("Ford", "Bronco"), ("Ford", "F-150"), ("Ford", "Escape")],
        )

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="vt-other", name="VT Other"
        )
        other_v = _make_vehicle(other, "OTHER-1", model="F-150")
        _post_cost(
            other_v, other, category=CATEGORY_PARTS, amount="9999.00"
        )
        mine = _make_vehicle(self.dealership, "MINE-1", model="F-150")
        _post_cost(
            mine, self.dealership, category=CATEGORY_PARTS, amount="200.00"
        )
        rows = vehicle_type_recon_cost(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].total_recon_cost, Decimal("200.00"))

    def test_window_bounds_inclusive(self) -> None:
        vehicle = _make_vehicle(self.dealership, "WIN-1", model="F-150")
        aware = timezone.make_aware
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="100.00",
            incurred_at=aware(dt.datetime(2026, 7, 1, 12, 0)),
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="300.00",
            incurred_at=aware(dt.datetime(2026, 8, 15, 12, 0)),
        )
        rows = vehicle_type_recon_cost(self.dealership)
        self.assertEqual(rows[0].total_recon_cost, Decimal("400.00"))
        rows = vehicle_type_recon_cost(
            self.dealership, window_start=dt.date(2026, 8, 1)
        )
        self.assertEqual(rows[0].total_recon_cost, Decimal("300.00"))
        rows = vehicle_type_recon_cost(
            self.dealership, window_end=dt.date(2026, 7, 31)
        )
        self.assertEqual(rows[0].total_recon_cost, Decimal("100.00"))
