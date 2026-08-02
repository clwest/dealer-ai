"""Milestone 9 · Increment 3 (SESSION_102) — analytics extension verb + endpoint tests.

Covers the three verbs (Q3 true / Q6 gross-profit trend / Q8 true
inventory turn) + their three DRF endpoints, plus a sanity check
that the M8.4 proxy verbs still return their original shapes
after M9.3 lands (M8 §6 lesson 11 — additive extension).

Files kept in one module for the M9.3 delivery so the aggregation
family stays legible in a single file. Splits when the module
crosses ~600 lines.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_PARTS,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_CASH,
    SOURCE_AUCTION,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    Dealership,
    Sale,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
    VehicleStageEvent,
)
from dealer_ai.services.analytics import (
    gross_profit_trend,
    inventory_turn,
    vehicle_type_profitability,
    vehicle_type_recon_cost,
    days_at_frontline_proxy,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from rest_framework.test import APIClient


def _make_vehicle(
    dealership: Dealership,
    *,
    stock: str,
    make: str = "Ford",
    model: str = "F-150",
) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        make=make,
        model=model,
        price=Decimal("30000.00"),
        dealership=dealership,
    )


def _seed_sale(
    dealership: Dealership,
    *,
    stock: str,
    make: str = "Ford",
    model: str = "F-150",
    purchase_price: str = "20000.00",
    sold_price: str = "25000.00",
    sale_date: dt.date | None = None,
    add_frontline_event: bool = True,
    frontline_days_ago: int = 20,
) -> Sale:
    vehicle = _make_vehicle(dealership, stock=stock, make=make, model=model)
    VehicleAcquisition.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal(purchase_price),
        purchase_date=dt.date(2026, 5, 1),
    )
    if add_frontline_event:
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=dealership,
            from_stage=VEHICLE_STAGE_INCOMING,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now() - dt.timedelta(days=frontline_days_ago),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
    # gross_realized = sold - (purchase + actual_costs=0)
    gross = Decimal(sold_price) - Decimal(purchase_price)
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=sale_date or timezone.now().date(),
        sold_price=Decimal(sold_price),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=gross,
    )


# ---------------------------------------------------------------------------
# Q3 — vehicle_type_profitability verb
# ---------------------------------------------------------------------------


class VehicleTypeProfitabilityVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m93-vtp", name="M9.3 VTP"
        )

    def test_empty_returns_empty_list(self) -> None:
        self.assertEqual(
            vehicle_type_profitability(self.dealership), []
        )

    def test_groups_by_make_model(self) -> None:
        _seed_sale(
            self.dealership,
            stock="F150-1",
            make="Ford",
            model="F-150",
            sold_price="30000.00",
            purchase_price="24000.00",
        )
        _seed_sale(
            self.dealership,
            stock="F150-2",
            make="Ford",
            model="F-150",
            sold_price="32000.00",
            purchase_price="25000.00",
        )
        _seed_sale(
            self.dealership,
            stock="ESC-1",
            make="Ford",
            model="Escape",
            sold_price="20000.00",
            purchase_price="16000.00",
        )

        rows = vehicle_type_profitability(self.dealership)
        by_model = {(r.make, r.model): r for r in rows}
        self.assertEqual(len(rows), 2)
        # F-150: 2 sold, gross = 6,000 + 7,000 = 13,000. Sold-price
        # sum = 62,000.
        f150 = by_model[("Ford", "F-150")]
        self.assertEqual(f150.sold_count, 2)
        self.assertEqual(f150.total_sale_gross, Decimal("13000.00"))
        self.assertEqual(f150.total_sold_price, Decimal("62000.00"))
        # Escape: 1 sold, gross = 4,000.
        esc = by_model[("Ford", "Escape")]
        self.assertEqual(esc.sold_count, 1)
        self.assertEqual(esc.total_sale_gross, Decimal("4000.00"))

    def test_sorts_by_total_sale_gross_desc(self) -> None:
        _seed_sale(
            self.dealership, stock="LOW-1",
            make="Ford", model="Escape",
            sold_price="20000.00", purchase_price="19000.00",  # gross 1,000
        )
        _seed_sale(
            self.dealership, stock="HIGH-1",
            make="Ford", model="F-150",
            sold_price="35000.00", purchase_price="25000.00",  # gross 10,000
        )
        rows = vehicle_type_profitability(self.dealership)
        self.assertEqual(rows[0].model, "F-150")
        self.assertEqual(rows[1].model, "Escape")

    def test_mean_gross_pct_computed_per_vehicle(self) -> None:
        # Two sales of the same type; margin percentages: 20% + 10%.
        # Mean = 15%.
        _seed_sale(
            self.dealership, stock="PCT-1",
            sold_price="10000.00", purchase_price="8000.00",  # 20%
        )
        _seed_sale(
            self.dealership, stock="PCT-2",
            sold_price="20000.00", purchase_price="18000.00",  # 10%
        )
        rows = vehicle_type_profitability(self.dealership)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].mean_gross_pct, Decimal("15.00"))

    def test_window_filters_out_of_range_sales(self) -> None:
        old = dt.date(2026, 1, 1)
        _seed_sale(
            self.dealership, stock="OLD-1",
            sold_price="20000.00", purchase_price="15000.00",
            sale_date=old,
        )
        recent = dt.date(2026, 7, 15)
        _seed_sale(
            self.dealership, stock="NEW-1",
            sold_price="20000.00", purchase_price="15000.00",
            sale_date=recent,
        )
        rows = vehicle_type_profitability(
            self.dealership,
            window_start=dt.date(2026, 7, 1),
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].sold_count, 1)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(slug="m93-vtp-other", name="Other")
        _seed_sale(other, stock="OTH-1")
        # No sales in `self.dealership` — cross-tenant read stays empty.
        self.assertEqual(
            vehicle_type_profitability(self.dealership), []
        )


# ---------------------------------------------------------------------------
# Q6 — gross_profit_trend verb
# ---------------------------------------------------------------------------


class GrossProfitTrendVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m93-gpt", name="M9.3 GPT"
        )

    def test_empty_returns_empty_list(self) -> None:
        self.assertEqual(gross_profit_trend(self.dealership), [])

    def test_buckets_by_sale_date(self) -> None:
        d1 = timezone.now().date() - dt.timedelta(days=5)
        d2 = timezone.now().date() - dt.timedelta(days=2)
        _seed_sale(
            self.dealership, stock="D1-1",
            sold_price="10000.00", purchase_price="8000.00", sale_date=d1,
        )
        _seed_sale(
            self.dealership, stock="D1-2",
            sold_price="20000.00", purchase_price="15000.00", sale_date=d1,
        )
        _seed_sale(
            self.dealership, stock="D2-1",
            sold_price="30000.00", purchase_price="25000.00", sale_date=d2,
        )

        points = gross_profit_trend(self.dealership)
        by_date = {p.sale_date: p for p in points}
        self.assertEqual(len(points), 2)
        # d1: 2,000 + 5,000 = 7,000; d2: 5,000.
        self.assertEqual(by_date[d1].sale_count, 2)
        self.assertEqual(by_date[d1].total_gross_realized, Decimal("7000.00"))
        self.assertEqual(by_date[d2].sale_count, 1)
        self.assertEqual(by_date[d2].total_gross_realized, Decimal("5000.00"))

    def test_ordered_by_sale_date_ascending(self) -> None:
        d_old = timezone.now().date() - dt.timedelta(days=10)
        d_new = timezone.now().date() - dt.timedelta(days=2)
        _seed_sale(self.dealership, stock="NEW", sale_date=d_new)
        _seed_sale(self.dealership, stock="OLD", sale_date=d_old)
        points = gross_profit_trend(self.dealership)
        self.assertEqual([p.sale_date for p in points], [d_old, d_new])

    def test_window_days_filters_out_older_sales(self) -> None:
        # Beyond window: sold 100 days ago; inside: 30 days ago.
        outside = timezone.now().date() - dt.timedelta(days=100)
        inside = timezone.now().date() - dt.timedelta(days=30)
        _seed_sale(self.dealership, stock="OUT", sale_date=outside)
        _seed_sale(self.dealership, stock="IN", sale_date=inside)
        points = gross_profit_trend(self.dealership, window_days=60)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].sale_date, inside)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(slug="m93-gpt-other", name="Other")
        _seed_sale(other, stock="OTH-1")
        self.assertEqual(gross_profit_trend(self.dealership), [])


# ---------------------------------------------------------------------------
# Q8 — inventory_turn verb
# ---------------------------------------------------------------------------


class InventoryTurnVerbTests(TestCase):

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m93-it", name="M9.3 IT"
        )

    def test_empty_window_returns_zero_report(self) -> None:
        report = inventory_turn(self.dealership)
        self.assertEqual(report.sold_count, 0)
        self.assertIsNone(report.mean_days)
        self.assertIsNone(report.p50_days)
        self.assertIsNone(report.p90_days)

    def test_computes_days_from_frontline_to_sale(self) -> None:
        # Vehicle entered frontline 20 days ago; sold today.
        _seed_sale(
            self.dealership, stock="IT-1",
            sale_date=timezone.now().date(),
            frontline_days_ago=20,
        )
        report = inventory_turn(self.dealership)
        self.assertEqual(report.sold_count, 1)
        self.assertEqual(report.p50_days, 20)
        self.assertEqual(report.min_days, 20)
        self.assertEqual(report.max_days, 20)

    def test_percentiles_across_multi_vehicle_distribution(self) -> None:
        # Ten vehicles at days 1..10.
        for i in range(1, 11):
            _seed_sale(
                self.dealership,
                stock=f"IT-{i}",
                sale_date=timezone.now().date(),
                frontline_days_ago=i,
            )
        report = inventory_turn(self.dealership)
        self.assertEqual(report.sold_count, 10)
        # Nearest-rank p50 of [1..10]: rank = ceil(0.5 * 10) = 5 → 5.
        self.assertEqual(report.p50_days, 5)
        # p90: rank = ceil(0.9 * 10) = 9 → 9.
        self.assertEqual(report.p90_days, 9)
        self.assertEqual(report.min_days, 1)
        self.assertEqual(report.max_days, 10)

    def test_skips_sold_vehicles_without_frontline_event(self) -> None:
        _seed_sale(
            self.dealership, stock="OK",
            sale_date=timezone.now().date(),
            frontline_days_ago=5,
        )
        _seed_sale(
            self.dealership, stock="NO-EVENT",
            sale_date=timezone.now().date(),
            add_frontline_event=False,
        )
        # The test-only ``dealer_ai/tests/__init__.py`` post_save signal
        # auto-bootstraps a ``frontline`` VehicleStageEvent on every
        # Vehicle save so downstream chat/search tests see the vehicle
        # in retail inventory. For this data-quality test we need to
        # simulate a vehicle that literally has no frontline event —
        # delete the bootstrap event after seeding.
        VehicleStageEvent.objects.filter(
            vehicle__stock_number="NO-EVENT",
            to_stage=VEHICLE_STAGE_FRONTLINE,
        ).delete()
        report = inventory_turn(self.dealership)
        # NO-EVENT is skipped per data-quality docstring rule.
        self.assertEqual(report.sold_count, 1)
        self.assertEqual(report.p50_days, 5)

    def test_uses_earliest_frontline_event_on_multiple_entries(self) -> None:
        _seed_sale(
            self.dealership, stock="MULTI",
            sale_date=timezone.now().date(),
            frontline_days_ago=30,  # earliest event: 30 days ago
        )
        vehicle = Vehicle.objects.get(stock_number="MULTI")
        # A later re-entry to frontline (7 days ago).
        VehicleStageEvent.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            from_stage=VEHICLE_STAGE_INCOMING,
            to_stage=VEHICLE_STAGE_FRONTLINE,
            entered_at=timezone.now() - dt.timedelta(days=7),
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
        )
        report = inventory_turn(self.dealership)
        # Earliest reference point wins → 30 days.
        self.assertEqual(report.p50_days, 30)

    def test_window_days_filters_out_older_sales(self) -> None:
        # Very old sale should not appear.
        _seed_sale(
            self.dealership, stock="OLD",
            sale_date=timezone.now().date() - dt.timedelta(days=100),
            frontline_days_ago=105,
        )
        report = inventory_turn(self.dealership, window_days=30)
        self.assertEqual(report.sold_count, 0)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(slug="m93-it-other", name="Other")
        _seed_sale(other, stock="OTH-1", frontline_days_ago=5)
        report = inventory_turn(self.dealership)
        self.assertEqual(report.sold_count, 0)


# ---------------------------------------------------------------------------
# Endpoint tests — one representative endpoint per verb
# (auth + shape + cross-tenant + malformed-arg parity with M8.1-M8.4)
# ---------------------------------------------------------------------------


VTP_URL = "dealer_ai:admin-analytics-vehicle-type-profitability"
GPT_URL = "dealer_ai:admin-analytics-gross-profit-trend"
IT_URL = "dealer_ai:admin-analytics-inventory-turn"


class M93EndpointAuthTests(TestCase):
    """Auth + role matrix — same shape as M8.1 sibling tests."""

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m93-ep-auth")
        _seed_sale(self.dealership, stock="AUTH-1", frontline_days_ago=10)

    def test_unauthenticated_vtp_forbidden(self) -> None:
        response = APIClient().get(reverse(VTP_URL))
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_gpt_forbidden(self) -> None:
        user = make_user(username="m93-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = authenticated_client(user).get(reverse(GPT_URL))
        self.assertEqual(response.status_code, 403)

    def test_dealer_owner_it_ok(self) -> None:
        user = make_user(username="m93-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        response = authenticated_client(user).get(reverse(IT_URL))
        self.assertEqual(response.status_code, 200)


class M93EndpointBehaviorTests(TestCase):

    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m93-ep-behavior")
        self.user = make_user(username="m93-behavior")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_vtp_response_shape(self) -> None:
        _seed_sale(
            self.dealership, stock="B1", make="Ford", model="F-150",
            sold_price="30000.00", purchase_price="24000.00",
        )
        response = self.client.get(reverse(VTP_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("rows", body)
        row = body["rows"][0]
        self.assertEqual(row["make"], "Ford")
        self.assertEqual(row["model"], "F-150")
        self.assertEqual(row["sold_count"], 1)
        # Stringified Decimals.
        self.assertEqual(row["total_sale_gross"], "6000.00")
        self.assertEqual(row["total_sold_price"], "30000.00")
        self.assertIn("mean_gross_pct", row)

    def test_gpt_response_shape(self) -> None:
        sd = timezone.now().date() - dt.timedelta(days=3)
        _seed_sale(
            self.dealership, stock="GPT-1",
            sold_price="10000.00", purchase_price="8000.00", sale_date=sd,
        )
        response = self.client.get(reverse(GPT_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("window_days", body)
        self.assertIn("points", body)
        self.assertEqual(len(body["points"]), 1)
        pt = body["points"][0]
        self.assertEqual(pt["sale_date"], sd.isoformat())
        self.assertEqual(pt["sale_count"], 1)
        self.assertEqual(pt["total_gross_realized"], "2000.00")

    def test_it_response_shape(self) -> None:
        _seed_sale(
            self.dealership, stock="IT-EP-1",
            sale_date=timezone.now().date(), frontline_days_ago=10,
        )
        response = self.client.get(reverse(IT_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["window_days"], 90)
        report = body["report"]
        self.assertEqual(report["sold_count"], 1)
        self.assertEqual(report["p50_days"], 10)

    def test_it_empty_returns_nulls(self) -> None:
        response = self.client.get(reverse(IT_URL))
        self.assertEqual(response.status_code, 200)
        report = response.json()["report"]
        self.assertEqual(report["sold_count"], 0)
        self.assertIsNone(report["mean_days"])
        self.assertIsNone(report["p50_days"])

    def test_vtp_malformed_window_start_400(self) -> None:
        response = self.client.get(
            reverse(VTP_URL) + "?window_start=not-a-date"
        )
        self.assertEqual(response.status_code, 400)

    def test_gpt_malformed_window_days_400(self) -> None:
        response = self.client.get(
            reverse(GPT_URL) + "?window_days=zero"
        )
        self.assertEqual(response.status_code, 400)

    def test_it_negative_window_days_400(self) -> None:
        response = self.client.get(
            reverse(IT_URL) + "?window_days=-5"
        )
        self.assertEqual(response.status_code, 400)


class M93CrossTenantEndpointTests(TestCase):
    """Tenant B's sale must be invisible to tenant A."""

    def setUp(self) -> None:
        self.tenant_a = make_dealership(slug="m93-ep-xt-a")
        self.tenant_b = make_dealership(slug="m93-ep-xt-b")
        _seed_sale(self.tenant_b, stock="B-XT-1", frontline_days_ago=15)

        user = make_user(username="m93-xt-a")
        make_membership(user, self.tenant_a, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)

    def test_vtp_no_leak(self) -> None:
        response = self.client_a.get(reverse(VTP_URL))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rows"], [])

    def test_it_no_leak(self) -> None:
        response = self.client_a.get(reverse(IT_URL))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["report"]["sold_count"], 0)


# ---------------------------------------------------------------------------
# M8.4 proxy verbs still work — additive-extension smoke test
# ---------------------------------------------------------------------------


class M84ProxyStillWorksAfterM93Tests(TestCase):
    """Per M8 §6 lesson 11: M8.4 verb shapes are frozen at M8.4
    ship. M9.3 adds sibling true verbs; the proxies must keep their
    original return shapes. Smoke-tested here so a future refactor
    catches regression.
    """

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m93-proxy-smoke", name="Proxy Smoke"
        )
        vehicle = _make_vehicle(
            self.dealership, stock="P-1", make="Ford", model="F-150"
        )
        VehicleAcquisition.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            source=SOURCE_AUCTION,
            purchase_price=Decimal("20000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        VehicleCost.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            category=CATEGORY_PARTS,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
            is_estimate=False,
        )

    def test_vehicle_type_recon_cost_shape_unchanged(self) -> None:
        rows = vehicle_type_recon_cost(self.dealership)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # M8.4 fields present and unchanged.
        self.assertEqual(row.make, "Ford")
        self.assertEqual(row.model, "F-150")
        self.assertEqual(row.vehicle_count, 1)
        self.assertEqual(row.total_recon_cost, Decimal("500.00"))
        self.assertEqual(row.mean_recon_cost, Decimal("500.00"))
        # M9.3 must NOT have added Sale-based fields to this row.
        self.assertFalse(hasattr(row, "total_sale_gross"))

    def test_days_at_frontline_proxy_shape_unchanged(self) -> None:
        # No M7.3 snapshots seeded — empty-window sentinel expected.
        report = days_at_frontline_proxy(self.dealership)
        self.assertEqual(report.snapshot_count, 0)
        self.assertIsNone(report.mean_p50_days)
