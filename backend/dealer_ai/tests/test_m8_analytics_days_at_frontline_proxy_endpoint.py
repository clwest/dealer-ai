"""Milestone 8 · Increment 4 (SESSION_097) — days-at-frontline-proxy endpoint tests.

Shape-level auth + response shape + window arg. Full auth matrix
locked by M8.1.
"""

from __future__ import annotations

import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_RECON_MANAGER,
    StageAgingSnapshot,
    VEHICLE_STAGE_FRONTLINE,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


URL_NAME = "dealer_ai:admin-analytics-days-at-frontline-proxy"


def _snap(dealership, snapshot_at=None, vehicle_count=10, p50=4, p90=15):
    return StageAgingSnapshot.objects.create(
        dealership=dealership,
        stage=VEHICLE_STAGE_FRONTLINE,
        snapshot_at=snapshot_at or timezone.now(),
        vehicle_count=vehicle_count,
        p50_days=p50,
        p90_days=p90,
    )


class DaysAtFrontlineEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="dfe-auth")

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.get(reverse(URL_NAME))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="dfe-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_allowed(self) -> None:
        user = make_user(username="dfe-recon")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)


class DaysAtFrontlineEndpointShapeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="dfe-shape")
        self.user = make_user(username="dfe-shape-user")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_empty_window_returns_null_fields(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["window_days"], 30)
        report = payload["report"]
        self.assertEqual(report["snapshot_count"], 0)
        self.assertIsNone(report["mean_p50_days"])
        self.assertIsNone(report["mean_p90_days"])
        self.assertIsNone(report["latest_vehicle_count"])
        self.assertIsNone(report["latest_snapshot_at"])

    def test_response_report_shape(self) -> None:
        now = timezone.now()
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=1),
            vehicle_count=8,
            p50=4,
            p90=15,
        )
        _snap(
            self.dealership,
            snapshot_at=now,
            vehicle_count=12,
            p50=6,
            p90=25,
        )
        response = self.client.get(reverse(URL_NAME))
        report = response.json()["report"]
        self.assertEqual(report["snapshot_count"], 2)
        # (4 + 6) / 2 = 5.00
        self.assertEqual(report["mean_p50_days"], "5.00")
        # (15 + 25) / 2 = 20.00
        self.assertEqual(report["mean_p90_days"], "20.00")
        self.assertEqual(report["latest_vehicle_count"], 12)
        self.assertIsNotNone(report["latest_snapshot_at"])

    def test_window_days_query_arg(self) -> None:
        now = timezone.now()
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=45),
        )
        _snap(
            self.dealership,
            snapshot_at=now - dt.timedelta(days=5),
        )
        # Default 30d → 1.
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.json()["report"]["snapshot_count"], 1)
        # 90d → 2.
        response = self.client.get(reverse(URL_NAME), {"window_days": "90"})
        self.assertEqual(response.json()["report"]["snapshot_count"], 2)

    def test_malformed_window_days_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"window_days": "not-int"}
        )
        self.assertEqual(response.status_code, 400)
