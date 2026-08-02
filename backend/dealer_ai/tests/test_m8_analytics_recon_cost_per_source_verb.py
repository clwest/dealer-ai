"""Milestone 8 · Increment 1 (SESSION_094) — recon_cost_per_source tests.

Locks the behavior of
:func:`services.analytics.recon_cost_per_source` (Q1 aggregation).

Coverage:

- Empty tenant → empty list.
- Vehicles with no acquisition are skipped (source unknown).
- Costs outside ``RECON_CATEGORIES`` are excluded (flooring / admin
  / photography).
- Estimated costs (``is_estimate=True``) are excluded — realized
  spend only.
- Reversal rows (negative amounts) subtract from the running total.
- Multiple vehicles from one source aggregate correctly.
- Multiple sources produce one row per source; sorted by total desc.
- Cross-tenant isolation.
- Window filter (``window_start`` / ``window_end`` bounds).
- ``mean_recon_cost`` quantized to two decimal places.
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
    SOURCE_AUCTION,
    SOURCE_TRADE,
    SOURCE_WHOLESALE,
    Dealership,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from dealer_ai.services.analytics import recon_cost_per_source


def _make_vehicle(
    dealership: Dealership, stock: str, *, price: str = "22500.00"
) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal(price),
        dealership=dealership,
    )


def _make_acquisition(
    vehicle: Vehicle,
    dealership: Dealership,
    *,
    source: str,
    purchase_price: str = "18000.00",
    purchase_date: dt.date | None = None,
) -> VehicleAcquisition:
    return VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=source,
        purchase_price=Decimal(purchase_price),
        purchase_date=purchase_date or dt.date(2026, 6, 1),
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


class ReconCostPerSourceVerbTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="analytics-primary", name="Analytics Primary"
        )

    def test_empty_tenant_returns_empty_list(self) -> None:
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(rows, [])

    def test_vehicle_without_acquisition_is_skipped(self) -> None:
        # No VehicleAcquisition row — source is unknown, cost cannot be
        # attributed to a bucket.
        vehicle = _make_vehicle(self.dealership, "NOACQ")
        _post_cost(
            vehicle, self.dealership, category=CATEGORY_PARTS, amount="120.00"
        )
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(rows, [])

    def test_flooring_and_admin_costs_are_excluded(self) -> None:
        vehicle = _make_vehicle(self.dealership, "EX-1")
        _make_acquisition(
            vehicle, self.dealership, source=SOURCE_AUCTION
        )
        # Floor-plan interest — should NOT count.
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_FLOOR_PLAN_INTEREST,
            amount="47.00",
        )
        # Admin advertising — should NOT count.
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_ADVERTISING_ALLOCATION,
            amount="200.00",
        )
        # Photography — separate bucket, also excluded.
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PHOTOGRAPHY,
            amount="80.00",
        )
        rows = recon_cost_per_source(self.dealership)
        # No recon rows → no source appears.
        self.assertEqual(rows, [])

    def test_estimated_costs_are_excluded(self) -> None:
        vehicle = _make_vehicle(self.dealership, "EST-1")
        _make_acquisition(
            vehicle, self.dealership, source=SOURCE_AUCTION
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="500.00",
            is_estimate=True,
        )
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(rows, [])

    def test_reversal_rows_subtract_from_total(self) -> None:
        vehicle = _make_vehicle(self.dealership, "REV-1")
        _make_acquisition(
            vehicle, self.dealership, source=SOURCE_AUCTION
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="1000.00",
        )
        # Correction row — reverses part of the original charge.
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="-250.00",
        )
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].source, SOURCE_AUCTION)
        self.assertEqual(rows[0].total_recon_cost, Decimal("750.00"))
        self.assertEqual(rows[0].vehicle_count, 1)
        self.assertEqual(rows[0].mean_recon_cost, Decimal("750.00"))

    def test_multiple_vehicles_same_source_aggregate(self) -> None:
        for idx in range(3):
            vehicle = _make_vehicle(self.dealership, f"AGG-{idx}")
            _make_acquisition(
                vehicle, self.dealership, source=SOURCE_AUCTION
            )
            _post_cost(
                vehicle,
                self.dealership,
                category=CATEGORY_MECHANICAL_LABOR,
                amount="400.00",
            )
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.source, SOURCE_AUCTION)
        self.assertEqual(row.vehicle_count, 3)
        self.assertEqual(row.total_recon_cost, Decimal("1200.00"))
        self.assertEqual(row.mean_recon_cost, Decimal("400.00"))

    def test_multiple_sources_sorted_by_total_desc(self) -> None:
        # Wholesale: 1 vehicle, $500. Auction: 2 vehicles, $2400 total.
        # Trade: 1 vehicle, $900. Expected order: auction, trade,
        # wholesale (biggest cost centers first).
        wholesale_v = _make_vehicle(self.dealership, "WHO-1")
        _make_acquisition(
            wholesale_v, self.dealership, source=SOURCE_WHOLESALE
        )
        _post_cost(
            wholesale_v,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="500.00",
        )
        for idx, amount in enumerate(("1000.00", "1400.00")):
            v = _make_vehicle(self.dealership, f"AUC-{idx}")
            _make_acquisition(v, self.dealership, source=SOURCE_AUCTION)
            _post_cost(
                v,
                self.dealership,
                category=CATEGORY_MECHANICAL_LABOR,
                amount=amount,
            )
        trade_v = _make_vehicle(self.dealership, "TRD-1")
        _make_acquisition(trade_v, self.dealership, source=SOURCE_TRADE)
        _post_cost(
            trade_v,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="900.00",
        )

        rows = recon_cost_per_source(self.dealership)
        self.assertEqual([r.source for r in rows], [
            SOURCE_AUCTION,
            SOURCE_TRADE,
            SOURCE_WHOLESALE,
        ])
        self.assertEqual(rows[0].source_display, "Auction")
        self.assertEqual(rows[0].total_recon_cost, Decimal("2400.00"))
        self.assertEqual(rows[0].vehicle_count, 2)
        self.assertEqual(rows[0].mean_recon_cost, Decimal("1200.00"))

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="analytics-other", name="Analytics Other"
        )
        # Recon spend on the "other" tenant that MUST NOT bleed into
        # the primary tenant's aggregation.
        other_v = _make_vehicle(other, "OTHER-1")
        _make_acquisition(other_v, other, source=SOURCE_AUCTION)
        _post_cost(
            other_v, other, category=CATEGORY_PARTS, amount="9999.00"
        )
        # Primary tenant has one modest recon spend.
        mine_v = _make_vehicle(self.dealership, "MINE-1")
        _make_acquisition(mine_v, self.dealership, source=SOURCE_AUCTION)
        _post_cost(
            mine_v, self.dealership, category=CATEGORY_PARTS, amount="120.00"
        )

        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].total_recon_cost, Decimal("120.00"))

        # And symmetrically — the other tenant's aggregation still sees
        # its own spend.
        other_rows = recon_cost_per_source(other)
        self.assertEqual(other_rows[0].total_recon_cost, Decimal("9999.00"))

    def test_window_bounds_are_inclusive(self) -> None:
        vehicle = _make_vehicle(self.dealership, "WIN-1")
        _make_acquisition(vehicle, self.dealership, source=SOURCE_AUCTION)
        aware = timezone.make_aware
        # Three rows dated 2026-07-01, 2026-08-01, 2026-09-01.
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
            amount="200.00",
            incurred_at=aware(dt.datetime(2026, 8, 1, 12, 0)),
        )
        _post_cost(
            vehicle,
            self.dealership,
            category=CATEGORY_PARTS,
            amount="400.00",
            incurred_at=aware(dt.datetime(2026, 9, 1, 12, 0)),
        )

        # Full-history — all three sum.
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(rows[0].total_recon_cost, Decimal("700.00"))

        # Windowed to August only — 200.
        rows = recon_cost_per_source(
            self.dealership,
            window_start=dt.date(2026, 8, 1),
            window_end=dt.date(2026, 8, 31),
        )
        self.assertEqual(rows[0].total_recon_cost, Decimal("200.00"))

        # Windowed to August-onwards — 200 + 400 = 600.
        rows = recon_cost_per_source(
            self.dealership,
            window_start=dt.date(2026, 8, 1),
        )
        self.assertEqual(rows[0].total_recon_cost, Decimal("600.00"))

        # Windowed through July-end — 100 only.
        rows = recon_cost_per_source(
            self.dealership,
            window_end=dt.date(2026, 7, 31),
        )
        self.assertEqual(rows[0].total_recon_cost, Decimal("100.00"))

    def test_mean_recon_cost_is_quantized(self) -> None:
        # 3 vehicles, $1000 total → mean $333.33 (2dp) with the .01
        # rounding step exercised.
        for idx, amount in enumerate(("333.34", "333.33", "333.33")):
            v = _make_vehicle(self.dealership, f"QNT-{idx}")
            _make_acquisition(v, self.dealership, source=SOURCE_AUCTION)
            _post_cost(
                v,
                self.dealership,
                category=CATEGORY_PARTS,
                amount=amount,
            )
        rows = recon_cost_per_source(self.dealership)
        self.assertEqual(rows[0].vehicle_count, 3)
        self.assertEqual(rows[0].total_recon_cost, Decimal("1000.00"))
        self.assertEqual(rows[0].mean_recon_cost, Decimal("333.33"))
