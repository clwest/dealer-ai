"""Milestone 12 · Increment 7 (SESSION_127) — BHPH analytics endpoint tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


SUMMARY = "dealer_ai:admin-bhph-analytics-summary"


def _make_note(dealership: Dealership, stock: str = "M127-EP") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Rio",
        price=Decimal("10500.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("10500.00"),
        finance_type=SALE_FINANCE_TYPE_BHPH,
        gross_realized=Decimal("1200.00"),
    )
    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=Decimal("8000.00"),
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
        current_bucket=BHPH_AGING_BUCKET_CURRENT,
    )


class AnalyticsSummaryAuthTests(TestCase):
    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().get(reverse(SUMMARY))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        dealership = get_default_dealership()
        user = make_user(username="m127-ep-adv")
        make_membership(user, dealership, ROLE_ADVISOR)
        response = authenticated_client(user).get(reverse(SUMMARY))
        self.assertEqual(response.status_code, 403)


class AnalyticsSummaryHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.user = make_user(username="m127-ep-hp")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_empty_portfolio_returns_null_metrics(self) -> None:
        response = self.client.get(reverse(SUMMARY))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_note_count"], 0)
        self.assertEqual(payload["total_principal_financed"], "0.00")
        self.assertIsNone(payload["cure_rate"])
        self.assertIsNone(payload["weighted_average_apr"])
        self.assertIsNone(payload["weighted_average_days_past_due"])
        self.assertIsNone(payload["ptp_kept_ratio"])
        self.assertEqual(len(payload["bucket_histogram"]), 7)

    def test_populated_portfolio_returns_totals(self) -> None:
        _make_note(self.dealership, stock="M127-EP-1")
        _make_note(self.dealership, stock="M127-EP-2")
        response = self.client.get(reverse(SUMMARY))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_note_count"], 2)
        self.assertEqual(
            payload["total_principal_financed"], "16000.00"
        )
        self.assertEqual(payload["cure_rate"], "1.0000")
        self.assertEqual(payload["weighted_average_apr"], "21.90")

    def test_histogram_row_shape(self) -> None:
        _make_note(self.dealership, stock="M127-EP-HR")
        response = self.client.get(reverse(SUMMARY))
        payload = response.json()
        row = payload["bucket_histogram"][0]
        for key in ("bucket", "note_count", "principal_total"):
            self.assertIn(key, row)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="m127-ep-x", name="M127 X"
        )
        _make_note(other, stock="M127-EP-X-1")
        response = self.client.get(reverse(SUMMARY))
        payload = response.json()
        self.assertEqual(payload["total_note_count"], 0)
