"""Milestone 8 · Increment 3 (SESSION_096) — sla-breach-patterns endpoint tests.

Shape-level auth check + response shape + window arg. Full auth
matrix locked by M8.1 endpoint tests.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    ROLE_ADVISOR,
    ROLE_RECON_MANAGER,
    SLA_BREACH_KIND_APPROVED_STALE,
    SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
    SlaBreachRecord,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_VENUE_OUTSOURCED,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


URL_NAME = "dealer_ai:admin-analytics-sla-breach-patterns"


_STOCK_COUNTER = {"n": 0}


def _next_stock() -> str:
    _STOCK_COUNTER["n"] += 1
    return f"SBPE-{_STOCK_COUNTER['n']:04d}"


def _seed_breach(
    dealership,
    *,
    kind: str = SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
    vendor_name: str = "ACME",
    breach_days: int = 3,
    detected_at: dt.datetime | None = None,
) -> None:
    when = detected_at or timezone.now()
    vehicle = Vehicle.objects.create(
        stock_number=_next_stock(),
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    vendor = Vendor.objects.create(
        dealership=dealership,
        slug=f"v-{_STOCK_COUNTER['n']}",
        name=vendor_name,
    )
    wo = WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        vendor=vendor,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        status=WORK_ORDER_STATUS_APPROVED,
    )
    SlaBreachRecord.objects.create(
        dealership=dealership,
        work_order=wo,
        kind=kind,
        breach_days=breach_days,
        detected_at=when,
        detected_at_date=when.date(),
        vehicle_stock=vehicle.stock_number,
        vendor_name=vendor_name,
    )


class BreachPatternsEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="bp-auth")

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.get(reverse(URL_NAME))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="bp-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_allowed(self) -> None:
        user = make_user(username="bp-recon")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)


class BreachPatternsEndpointShapeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="bp-shape")
        self.user = make_user(username="bp-shape-user")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_empty_tenant_returns_zero_report(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["window_days"], 30)
        self.assertEqual(payload["report"]["total_breach_count"], 0)
        self.assertIsNone(payload["report"]["average_breach_days"])
        self.assertEqual(
            payload["report"]["top_vendors_by_breach_count"], []
        )
        self.assertEqual(payload["report"]["breaches_by_kind"], [])

    def test_response_report_shape(self) -> None:
        _seed_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            vendor_name="Alpha",
            breach_days=3,
        )
        _seed_breach(
            self.dealership,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            vendor_name="Alpha",
            breach_days=8,
        )
        response = self.client.get(reverse(URL_NAME))
        payload = response.json()
        report = payload["report"]
        self.assertEqual(report["total_breach_count"], 2)
        # (3 + 8) / 2 = 5.50 → stringified Decimal.
        self.assertEqual(report["average_breach_days"], "5.50")
        # Both breach rows attribute to Alpha → single vendor row.
        self.assertEqual(
            report["top_vendors_by_breach_count"],
            [{"vendor_name": "Alpha", "breach_count": 2}],
        )
        # Both kinds present; each with breach_count=1. Tiebreak on
        # kind string asc.
        self.assertEqual(len(report["breaches_by_kind"]), 2)
        # Kinds sorted: approved_stale < in_progress_past_eta (asc).
        kinds = [k["kind"] for k in report["breaches_by_kind"]]
        self.assertEqual(
            sorted(kinds),
            [
                SLA_BREACH_KIND_APPROVED_STALE,
                SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            ],
        )
        # Kind display labels populated.
        for k in report["breaches_by_kind"]:
            self.assertTrue(k["kind_display"])

    def test_window_days_query_arg_applied(self) -> None:
        now = timezone.now()
        _seed_breach(
            self.dealership,
            breach_days=10,
            detected_at=now - dt.timedelta(days=45),
        )
        _seed_breach(
            self.dealership,
            breach_days=3,
            detected_at=now - dt.timedelta(days=5),
        )
        # Default 30d → 1 row.
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.json()["report"]["total_breach_count"], 1)
        # 90d → both rows.
        response = self.client.get(
            reverse(URL_NAME), {"window_days": "90"}
        )
        self.assertEqual(response.json()["report"]["total_breach_count"], 2)

    def test_malformed_window_days_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"window_days": "not-int"}
        )
        self.assertEqual(response.status_code, 400)

    def test_cross_tenant_isolation(self) -> None:
        other = make_dealership(slug="bp-other-tenant")
        _seed_breach(other, vendor_name="OtherVendor", breach_days=15)
        _seed_breach(self.dealership, vendor_name="MyVendor", breach_days=2)
        response = self.client.get(reverse(URL_NAME))
        report = response.json()["report"]
        self.assertEqual(report["total_breach_count"], 1)
        self.assertEqual(
            report["top_vendors_by_breach_count"][0]["vendor_name"],
            "MyVendor",
        )
