"""Milestone 14 · Increment 1 (SESSION_134) — cost-posting failures endpoint tests.

Covers ``GET admin/accounting/cost-posting-failures/`` per
MILESTONE_14_PLANNING.md §7 M14.1.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    CATEGORY_PARTS,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


FAILURES_URL = "dealer_ai:admin-cost-posting-failures"


def _sm_client(username: str = "m141fe-sm") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_SALES_MANAGER)
    return authenticated_client(user)


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Test",
        price=Decimal("10000.00"),
        dealership=dealership,
    )


def _make_old_cost(
    dealership: Dealership,
    vehicle: Vehicle,
    amount: Decimal,
    *,
    hours_ago: int = 48,
    is_estimate: bool = False,
) -> VehicleCost:
    cost = VehicleCost.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CATEGORY_PARTS,
        amount=amount,
        incurred_at=timezone.now(),
        is_estimate=is_estimate,
        reference="INV-M141FE",
        vendor="M141FE Vendor",
    )
    VehicleCost.objects.filter(pk=cost.pk).update(
        created_at=timezone.now() - dt.timedelta(hours=hours_ago)
    )
    cost.refresh_from_db()
    return cost


class CostPostingFailuresEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.vehicle = _make_vehicle(self.dealership, "M141FE-STOCK")
        self.client_ = _sm_client()

    def test_get_empty_returns_200_with_empty_failures(self) -> None:
        response = self.client_.get(reverse(FAILURES_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["cost_posting_failures"]
        self.assertEqual(body["failures"], [])
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["threshold_hours"], 24)
        self.assertIn("as_of", body)

    def test_get_with_failures_returns_projected_rows(self) -> None:
        cost = _make_old_cost(self.dealership, self.vehicle, Decimal("42.00"))
        response = self.client_.get(reverse(FAILURES_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["cost_posting_failures"]
        self.assertEqual(body["count"], 1)
        row = body["failures"][0]
        self.assertEqual(row["id"], cost.pk)
        self.assertEqual(row["vehicle_stock"], "M141FE-STOCK")
        self.assertEqual(row["amount"], "42.00")  # Decimal-as-string.
        self.assertEqual(row["category"], CATEGORY_PARTS)
        self.assertEqual(row["reference"], "INV-M141FE")
        self.assertEqual(row["vendor"], "M141FE Vendor")
        # 48 hours (created_at_override) → 48 age_in_hours.
        self.assertGreaterEqual(row["age_in_hours"], 47)
        self.assertLessEqual(row["age_in_hours"], 49)

    def test_custom_threshold_hours_via_query_param(self) -> None:
        _make_old_cost(
            self.dealership, self.vehicle, Decimal("10.00"), hours_ago=36
        )
        _make_old_cost(
            self.dealership, self.vehicle, Decimal("20.00"), hours_ago=72
        )
        # 48-hour threshold: only the 72-hour-old row qualifies.
        response = self.client_.get(
            reverse(FAILURES_URL), data={"threshold_hours": 48}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["cost_posting_failures"]
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["threshold_hours"], 48)

    def test_invalid_threshold_hours_returns_400(self) -> None:
        response = self.client_.get(
            reverse(FAILURES_URL), data={"threshold_hours": 0}
        )
        self.assertEqual(response.status_code, 400)

    def test_threshold_hours_over_max_returns_400(self) -> None:
        response = self.client_.get(
            reverse(FAILURES_URL), data={"threshold_hours": 999999}
        )
        self.assertEqual(response.status_code, 400)

    def test_excludes_estimates(self) -> None:
        _make_old_cost(
            self.dealership,
            self.vehicle,
            Decimal("100.00"),
            is_estimate=True,
        )
        response = self.client_.get(reverse(FAILURES_URL))
        body = response.json()["cost_posting_failures"]
        self.assertEqual(body["count"], 0)

    def test_requires_authentication(self) -> None:
        response = APIClient().get(reverse(FAILURES_URL))
        self.assertIn(response.status_code, {401, 403})

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="m141fe-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        advisor = authenticated_client(user)
        response = advisor.get(reverse(FAILURES_URL))
        self.assertEqual(response.status_code, 403)

    def test_scoped_to_calling_dealership(self) -> None:
        other = Dealership.objects.create(slug="m141fe-other", name="Other")
        seed_default_coa(other)
        other_vehicle = _make_vehicle(other, "OTHER-STOCK-FE")
        _make_old_cost(other, other_vehicle, Decimal("999.00"))
        response = self.client_.get(reverse(FAILURES_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["cost_posting_failures"]
        self.assertEqual(body["count"], 0)

    def test_failure_row_shape(self) -> None:
        _make_old_cost(self.dealership, self.vehicle, Decimal("1.00"))
        response = self.client_.get(reverse(FAILURES_URL))
        row = response.json()["cost_posting_failures"]["failures"][0]
        self.assertEqual(
            set(row.keys()),
            {
                "id",
                "vehicle_id",
                "vehicle_stock",
                "category",
                "category_display",
                "amount",
                "reference",
                "vendor",
                "incurred_at",
                "created_at",
                "age_in_hours",
            },
        )
