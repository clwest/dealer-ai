"""Milestone 8 · Increment 3 (SESSION_096) — stage-aging-trend endpoint tests.

Shape-level auth check + response shape + query-arg semantics.
Full auth matrix locked by M8.1 endpoint tests.
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
    VEHICLE_STAGE_RECON,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


URL_NAME = "dealer_ai:admin-analytics-stage-aging-trend"


def _seed_snapshot(
    dealership,
    *,
    stage: str = VEHICLE_STAGE_RECON,
    snapshot_at: dt.datetime | None = None,
    vehicle_count: int = 5,
    p50: int = 3,
    p90: int = 14,
) -> None:
    StageAgingSnapshot.objects.create(
        dealership=dealership,
        stage=stage,
        snapshot_at=snapshot_at or timezone.now(),
        vehicle_count=vehicle_count,
        p50_days=p50,
        p90_days=p90,
    )


class StageAgingTrendEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="sag-auth")

    def test_unauthenticated_forbidden(self) -> None:
        client = APIClient()
        response = client.get(
            reverse(URL_NAME), {"stage": VEHICLE_STAGE_RECON}
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="sag-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(
            reverse(URL_NAME), {"stage": VEHICLE_STAGE_RECON}
        )
        self.assertEqual(response.status_code, 403)

    def test_recon_manager_allowed(self) -> None:
        user = make_user(username="sag-recon")
        make_membership(user, self.dealership, ROLE_RECON_MANAGER)
        client = authenticated_client(user)
        response = client.get(
            reverse(URL_NAME), {"stage": VEHICLE_STAGE_RECON}
        )
        self.assertEqual(response.status_code, 200)


class StageAgingTrendEndpointShapeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="sag-shape")
        self.user = make_user(username="sag-shape-user")
        make_membership(self.user, self.dealership, ROLE_RECON_MANAGER)
        self.client = authenticated_client(self.user)

    def test_missing_stage_returns_400(self) -> None:
        response = self.client.get(reverse(URL_NAME))
        self.assertEqual(response.status_code, 400)
        self.assertIn("stage", response.json()["detail"])

    def test_unknown_stage_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"stage": "not-a-stage"}
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_window_days_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME),
            {"stage": VEHICLE_STAGE_RECON, "window_days": "not-int"},
        )
        self.assertEqual(response.status_code, 400)

    def test_zero_window_days_returns_400(self) -> None:
        response = self.client.get(
            reverse(URL_NAME),
            {"stage": VEHICLE_STAGE_RECON, "window_days": "0"},
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_tenant_returns_empty_points(self) -> None:
        response = self.client.get(
            reverse(URL_NAME), {"stage": VEHICLE_STAGE_RECON}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["stage"], VEHICLE_STAGE_RECON)
        self.assertEqual(payload["window_days"], 30)
        self.assertEqual(payload["points"], [])

    def test_response_point_shape(self) -> None:
        _seed_snapshot(
            self.dealership, vehicle_count=7, p50=4, p90=18
        )
        response = self.client.get(
            reverse(URL_NAME), {"stage": VEHICLE_STAGE_RECON}
        )
        payload = response.json()
        self.assertEqual(len(payload["points"]), 1)
        point = payload["points"][0]
        self.assertIn("snapshot_at", point)
        self.assertEqual(point["vehicle_count"], 7)
        self.assertEqual(point["p50_days"], 4)
        self.assertEqual(point["p90_days"], 18)
