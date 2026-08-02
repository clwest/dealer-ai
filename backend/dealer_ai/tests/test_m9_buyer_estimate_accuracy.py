"""Milestone 9 · Increment 4 (SESSION_103) — Q7 buyer_estimate_accuracy tests.

Covers the verb + DRF endpoint. Q7 was deferred at M8.2
(SESSION_095) because the substrate (:attr:`VehicleAcquisition.buyer`
FK) did not exist; M9.1 shipped the FK; M9.4 ships the verb + endpoint.

`LeadVehicleInterest.stage_at_interest` (also planned for M9.4) is
deferred separately per SESSION_103 §0.a — the through-model does
not exist and creating it is scope creep. Covered by a future
increment.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    SOURCE_AUCTION,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_VENUE_IN_HOUSE,
    Dealership,
    Vehicle,
    VehicleAcquisition,
    WorkOrder,
)
from dealer_ai.services.analytics import buyer_estimate_accuracy
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


User = get_user_model()

URL_NAME = "dealer_ai:admin-analytics-buyer-estimate-accuracy"


def _make_vehicle(
    dealership: Dealership,
    *,
    stock: str,
    buyer: User | None = None,
    purchase_days_ago: int = 5,
) -> Vehicle:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("30000.00"),
        dealership=dealership,
    )
    VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal("22000.00"),
        purchase_date=(
            timezone.now().date() - dt.timedelta(days=purchase_days_ago)
        ),
        buyer=buyer,
    )
    return vehicle


def _make_completed_wo(
    dealership: Dealership,
    vehicle: Vehicle,
    *,
    estimated: str,
    actual: str,
) -> WorkOrder:
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_IN_HOUSE,
        status=WORK_ORDER_STATUS_COMPLETED,
        estimated_cost=Decimal(estimated),
        actual_cost=Decimal(actual),
    )


# ---------------------------------------------------------------------------
# Verb tests
# ---------------------------------------------------------------------------


class BuyerEstimateAccuracyVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m94-bea", name="M9.4 BEA"
        )
        self.alice = User.objects.create_user(
            username="alice-bidder",
            email="alice@example.com",
            password="x",
            first_name="Alice",
            last_name="Bidder",
        )
        self.bob = User.objects.create_user(
            username="bob-bidder",
            email="bob@example.com",
            password="x",
        )

    def test_empty_returns_empty_list(self) -> None:
        self.assertEqual(buyer_estimate_accuracy(self.dealership), [])

    def test_computes_variance_and_bias(self) -> None:
        # Alice acquired 1 vehicle; 2 WOs:
        # WO#1: est 1000, actual 1200 → signed +20%, abs 20%
        # WO#2: est 500,  actual 400  → signed -20%, abs 20%
        # Mean absolute = 20%; bias = 0%.
        v = _make_vehicle(self.dealership, stock="A-1", buyer=self.alice)
        _make_completed_wo(self.dealership, v, estimated="1000", actual="1200")
        _make_completed_wo(self.dealership, v, estimated="500", actual="400")

        rows = buyer_estimate_accuracy(self.dealership)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.buyer_user_id, self.alice.pk)
        self.assertEqual(row.buyer_display, "Alice Bidder")
        self.assertEqual(row.vehicle_count, 1)
        self.assertEqual(row.work_order_count, 2)
        self.assertEqual(row.mean_absolute_variance_pct, Decimal("20.00"))
        self.assertEqual(row.bias_pct, Decimal("0.00"))

    def test_falls_back_to_username_when_no_full_name(self) -> None:
        v = _make_vehicle(self.dealership, stock="B-1", buyer=self.bob)
        _make_completed_wo(self.dealership, v, estimated="100", actual="110")
        rows = buyer_estimate_accuracy(self.dealership)
        self.assertEqual(rows[0].buyer_display, "bob-bidder")

    def test_positive_bias_flags_underestimator(self) -> None:
        # Two WOs both over-run — bias positive.
        v = _make_vehicle(self.dealership, stock="UND-1", buyer=self.alice)
        _make_completed_wo(self.dealership, v, estimated="100", actual="150")
        _make_completed_wo(self.dealership, v, estimated="200", actual="240")
        rows = buyer_estimate_accuracy(self.dealership)
        self.assertGreater(rows[0].bias_pct, Decimal("0.00"))

    def test_negative_bias_flags_overestimator(self) -> None:
        v = _make_vehicle(self.dealership, stock="OVR-1", buyer=self.alice)
        _make_completed_wo(self.dealership, v, estimated="100", actual="80")
        rows = buyer_estimate_accuracy(self.dealership)
        self.assertLess(rows[0].bias_pct, Decimal("0.00"))

    def test_excludes_null_buyer_acquisitions(self) -> None:
        # Vehicle with no buyer — must be excluded from the aggregation
        # per docstring rule (historical rows have no provenance).
        v = _make_vehicle(self.dealership, stock="NULL-1", buyer=None)
        _make_completed_wo(self.dealership, v, estimated="100", actual="150")
        self.assertEqual(buyer_estimate_accuracy(self.dealership), [])

    def test_excludes_non_completed_wos(self) -> None:
        v = _make_vehicle(self.dealership, stock="INF-1", buyer=self.alice)
        WorkOrder.objects.create(
            vehicle=v, dealership=self.dealership,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            status=WORK_ORDER_STATUS_APPROVED,  # in-flight
            estimated_cost=Decimal("100"),
            actual_cost=None,
        )
        self.assertEqual(buyer_estimate_accuracy(self.dealership), [])

    def test_excludes_zero_or_null_estimate(self) -> None:
        v = _make_vehicle(self.dealership, stock="ZE-1", buyer=self.alice)
        # Zero estimate — excluded (division-by-zero guard).
        _make_completed_wo(self.dealership, v, estimated="0", actual="100")
        self.assertEqual(buyer_estimate_accuracy(self.dealership), [])

    def test_multiple_buyers_ranked_by_accuracy(self) -> None:
        # Alice: exact estimate (0% variance).
        v_a = _make_vehicle(self.dealership, stock="RANK-A", buyer=self.alice)
        _make_completed_wo(self.dealership, v_a, estimated="1000", actual="1000")
        # Bob: 50% overrun.
        v_b = _make_vehicle(self.dealership, stock="RANK-B", buyer=self.bob)
        _make_completed_wo(self.dealership, v_b, estimated="1000", actual="1500")

        rows = buyer_estimate_accuracy(self.dealership)
        # Alice's 0% variance ranks first (most accurate).
        self.assertEqual(rows[0].buyer_user_id, self.alice.pk)
        self.assertEqual(rows[1].buyer_user_id, self.bob.pk)

    def test_filter_by_buyer_user_id(self) -> None:
        v_a = _make_vehicle(self.dealership, stock="F-A", buyer=self.alice)
        _make_completed_wo(self.dealership, v_a, estimated="100", actual="110")
        v_b = _make_vehicle(self.dealership, stock="F-B", buyer=self.bob)
        _make_completed_wo(self.dealership, v_b, estimated="100", actual="90")

        alice_only = buyer_estimate_accuracy(
            self.dealership, buyer_user_id=self.alice.pk
        )
        self.assertEqual(len(alice_only), 1)
        self.assertEqual(alice_only[0].buyer_user_id, self.alice.pk)

    def test_window_days_filters_out_older_acquisitions(self) -> None:
        v = _make_vehicle(
            self.dealership, stock="OLD-1",
            buyer=self.alice, purchase_days_ago=200,
        )
        _make_completed_wo(self.dealership, v, estimated="100", actual="110")
        self.assertEqual(
            buyer_estimate_accuracy(self.dealership, window_days=90), []
        )

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(slug="m94-bea-other", name="Other")
        v = _make_vehicle(other, stock="OTH-1", buyer=self.alice)
        _make_completed_wo(other, v, estimated="100", actual="110")
        self.assertEqual(buyer_estimate_accuracy(self.dealership), [])


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


class BuyerEstimateAccuracyEndpointTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m94-bea-ep")
        self.user = make_user(username="m94-bea-ep-user")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

        self.alice = User.objects.create_user(
            username="alice-ep", email="alice-ep@example.com", password="x",
            first_name="Alice", last_name="Endpoint",
        )
        v = _make_vehicle(self.dealership, stock="EP-1", buyer=self.alice)
        _make_completed_wo(self.dealership, v, estimated="1000", actual="1200")

    def test_response_shape(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["window_days"], 90)
        self.assertIsNone(body["buyer_user_id"])
        rows = body["rows"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["buyer_user_id"], self.alice.pk)
        self.assertEqual(row["buyer_display"], "Alice Endpoint")
        self.assertEqual(row["vehicle_count"], 1)
        self.assertEqual(row["work_order_count"], 1)
        self.assertEqual(row["mean_absolute_variance_pct"], "20.00")
        self.assertEqual(row["bias_pct"], "20.00")

    def test_buyer_user_id_query_arg_filter(self) -> None:
        response = self.client.get(
            reverse(URL_NAME) + f"?buyer_user_id={self.alice.pk}"
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["buyer_user_id"], self.alice.pk)
        self.assertEqual(len(body["rows"]), 1)

    def test_400_on_malformed_buyer_user_id(self) -> None:
        response = self.client.get(
            reverse(URL_NAME) + "?buyer_user_id=notanumber"
        )
        self.assertEqual(response.status_code, 400)

    def test_400_on_malformed_window_days(self) -> None:
        response = self.client.get(
            reverse(URL_NAME) + "?window_days=nope"
        )
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_forbidden(self) -> None:
        response = APIClient().get(reverse(URL_NAME))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        advisor = make_user(username="m94-bea-advisor")
        make_membership(advisor, self.dealership, ROLE_ADVISOR)
        response = authenticated_client(advisor).get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_dealer_owner_ok(self) -> None:
        owner = make_user(username="m94-bea-owner")
        make_membership(owner, self.dealership, ROLE_DEALER_OWNER)
        response = authenticated_client(owner).get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)

    def test_cross_tenant_no_leak(self) -> None:
        tenant_b = make_dealership(slug="m94-bea-ep-b")
        v = _make_vehicle(tenant_b, stock="XT-B-1", buyer=self.alice)
        _make_completed_wo(tenant_b, v, estimated="100", actual="200")
        response = self.client.get(reverse(URL_NAME))
        # Tenant B's data must not appear — tenant A only sees the
        # single Alice row from its own dealership.
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 1)
        # And the totals show only the tenant-A WO, not the B one.
        self.assertEqual(rows[0]["work_order_count"], 1)
