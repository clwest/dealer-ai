"""Milestone 14 · Increment 1 (SESSION_134) — cost-posting failures service tests.

Covers :func:`services.accounting.detect_cost_posting_failures` per
MILESTONE_14_PLANNING.md §7 M14.1.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_PARTS,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.accounting import (
    detect_cost_posting_failures,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Test",
        price=Decimal("10000.00"),
        dealership=dealership,
    )


def _make_cost(
    dealership: Dealership,
    vehicle: Vehicle,
    amount: Decimal,
    *,
    is_estimate: bool = False,
    created_at_override=None,
) -> VehicleCost:
    cost = VehicleCost.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CATEGORY_PARTS,
        amount=amount,
        incurred_at=timezone.now(),
        is_estimate=is_estimate,
    )
    if created_at_override is not None:
        # auto_now_add prevents constructor override — patch via update().
        VehicleCost.objects.filter(pk=cost.pk).update(
            created_at=created_at_override
        )
        cost.refresh_from_db()
    return cost


class DetectCostPostingFailuresTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.vehicle = _make_vehicle(self.dealership, "M141F-STOCK")
        self.now = timezone.now()

    def test_empty_returns_empty_queryset(self) -> None:
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now
        )
        self.assertEqual(list(failures), [])

    def test_includes_old_unposted_non_estimate(self) -> None:
        old = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("50.00"),
            created_at_override=self.now - dt.timedelta(hours=48),
        )
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now
        )
        self.assertEqual(list(failures.values_list("pk", flat=True)), [old.pk])

    def test_excludes_recent_unposted(self) -> None:
        # Created inside the 24h threshold — the detector may not have run yet.
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("25.00"),
            created_at_override=self.now - dt.timedelta(hours=6),
        )
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now
        )
        self.assertEqual(failures.count(), 0)

    def test_excludes_estimates_even_when_old(self) -> None:
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("100.00"),
            is_estimate=True,
            created_at_override=self.now - dt.timedelta(hours=72),
        )
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now
        )
        self.assertEqual(failures.count(), 0)

    def test_excludes_already_posted(self) -> None:
        posted = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("30.00"),
            created_at_override=self.now - dt.timedelta(hours=48),
        )
        posted.posted_at = self.now
        posted.save(update_fields=["posted_at"])
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now
        )
        self.assertEqual(failures.count(), 0)

    def test_custom_threshold_hours_narrows_result(self) -> None:
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("10.00"),
            created_at_override=self.now - dt.timedelta(hours=36),
        )
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("20.00"),
            created_at_override=self.now - dt.timedelta(hours=72),
        )
        # 48-hour threshold: only the 72-hour-old row qualifies.
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now, threshold_hours=48
        )
        self.assertEqual(failures.count(), 1)
        self.assertEqual(failures.first().amount, Decimal("20.00"))

    def test_ordering_oldest_first(self) -> None:
        newer = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("1.00"),
            created_at_override=self.now - dt.timedelta(hours=30),
        )
        older = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("2.00"),
            created_at_override=self.now - dt.timedelta(hours=60),
        )
        failures = list(
            detect_cost_posting_failures(
                dealership=self.dealership, now=self.now
            )
        )
        self.assertEqual([f.pk for f in failures], [older.pk, newer.pk])

    def test_tenancy_scoping_excludes_other_dealerships(self) -> None:
        other = Dealership.objects.create(slug="m141f-other", name="Other")
        seed_default_coa(other)
        other_vehicle = _make_vehicle(other, "OTHER-STOCK")
        _make_cost(
            other,
            other_vehicle,
            Decimal("999.00"),
            created_at_override=self.now - dt.timedelta(hours=72),
        )
        # Post one in the default tenant.
        mine = _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("5.00"),
            created_at_override=self.now - dt.timedelta(hours=48),
        )
        failures = detect_cost_posting_failures(
            dealership=self.dealership, now=self.now
        )
        self.assertEqual(
            list(failures.values_list("pk", flat=True)), [mine.pk]
        )

    def test_default_now_uses_timezone_now(self) -> None:
        _make_cost(
            self.dealership,
            self.vehicle,
            Decimal("7.00"),
            created_at_override=timezone.now() - dt.timedelta(hours=48),
        )
        # No `now=` passed → default resolves.
        failures = detect_cost_posting_failures(dealership=self.dealership)
        self.assertEqual(failures.count(), 1)
