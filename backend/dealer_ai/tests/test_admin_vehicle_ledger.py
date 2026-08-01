"""Milestone 2 · Increment 6 — admin ledger API tests.

Three endpoints under /api/dealer-ai/admin/vehicles/<stock_number>/
exposing the M2.1–M2.5 ledger surface for authorized operators:

- GET .../ledger/       — full ledger read (vehicle header +
                           acquisition | null + ordered costs +
                           totals + days_in_inventory + projected_gross).
- POST .../acquisition/ — upsert acquisition (wraps
                           services.vehicle_ledger.record_acquisition).
- POST .../costs/       — post one immutable cost row (wraps
                           services.vehicle_ledger.add_cost).

Test class map:

- Permission matrix per endpoint (6 cases each):
  - PermissionMatrixLedgerRead
  - PermissionMatrixAcquisitionUpsert
  - PermissionMatrixCostCreate
- Read scenarios:
  - ReadLedgerEmptyState
  - ReadLedgerAcquisitionOnly
  - ReadLedgerMixedActualAndEstimate
  - ReadLedgerReversingEntry
  - ReadLedgerCostOrderingIsDeterministic
  - ReadLedgerContractStability
  - ReadLedgerCrossTenantIsolation
- Acquisition upsert scenarios:
  - AcquisitionCreate
  - AcquisitionUpdate
  - AcquisitionInvalidInput
- Cost create scenarios:
  - CostCreateValid
  - CostCreateNegativeReversal
  - CostCreateInvalidInput
  - CostCreatedByAttribution
  - CostImmutableRoutes
- Security verification:
  - PublicSurfacesNeverExposeLedgerData

Tests use ``services.vehicle_ledger`` as the source of truth for
arithmetic — endpoint tests never re-derive money math the M2.2
suite already proves.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from dealer_ai.models import (
    ACQUISITION_SOURCE_CHOICES,
    CATEGORY_BODY_WORK,
    CATEGORY_DETAIL,
    CATEGORY_FLOOR_PLAN_INTEREST,
    CATEGORY_PARTS,
    CATEGORY_PHOTOGRAPHY,
    CATEGORY_TIRES,
    ROLE_ADVISOR,
    SOURCE_AUCTION,
    SOURCE_TRADE,
    Dealership,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
)
from dealer_ai.services.payment_engine import daily_floor_plan_interest
from dealer_ai.services.vehicle_ledger import (
    add_cost,
    compute_totals,
    record_acquisition,
)
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    dealer_owner_client_at_default,
    make_advisor_user,
    make_dealership,
    make_membership,
    make_user,
    sales_manager_client_at_default,
)


# ---- Shared factories ------------------------------------------------------


def _make_vehicle(stock: str, dealership: Dealership, price: Decimal = Decimal("24900.00")) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Ranger",
        price=price,
        dealership=dealership,
    )


def _seed_acquisition(vehicle: Vehicle, dealership: Dealership, *,
                      price: Decimal = Decimal("18500.00"),
                      purchase_date=None) -> VehicleAcquisition:
    acq, _ = record_acquisition(
        vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=price,
        purchase_date=purchase_date or dt.date(2026, 5, 1),
        buyer_fees=Decimal("475.00"),
        transportation_cost=Decimal("850.00"),
        title_acquisition_cost=Decimal("125.00"),
    )
    return acq


def _url_ledger(stock: str) -> str:
    return f"/api/dealer-ai/admin/vehicles/{stock}/ledger/"


def _url_acquisition(stock: str) -> str:
    return f"/api/dealer-ai/admin/vehicles/{stock}/acquisition/"


def _url_costs(stock: str) -> str:
    return f"/api/dealer-ai/admin/vehicles/{stock}/costs/"


# =============================================================================
# PERMISSION MATRIX — one class per endpoint × six standard cases
# =============================================================================


class _PermissionMatrixBase(TestCase):
    """Shared setUp for the three permission-matrix classes.

    Provisions two dealerships, a vehicle in each, and one
    authenticated client per role/tenant combination the matrix
    covers. Subclasses each hit ONE endpoint against every case.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = make_dealership(slug="matrix-other-tenant")
        self.vehicle_default = _make_vehicle("MTX-DEFAULT-1", self.default)
        self.vehicle_other = _make_vehicle("MTX-OTHER-1", self.other)

        # Six-case matrix:
        self.anon = APIClient()

        # advisor at same dealership as target vehicle (default)
        advisor_same_user, _ = make_advisor_user(
            "advisor-matrix-same", self.default,
            username="advisor-matrix-same-user",
        )
        # give the advisor an advisor-role membership too so
        # get_active_membership returns default.
        make_membership(advisor_same_user, self.default, ROLE_ADVISOR)
        self.advisor_same_client = authenticated_client(advisor_same_user)

        # advisor at wrong (other) dealership
        advisor_wrong_user, _ = make_advisor_user(
            "advisor-matrix-wrong", self.other,
            username="advisor-matrix-wrong-user",
        )
        make_membership(advisor_wrong_user, self.other, ROLE_ADVISOR)
        self.advisor_wrong_client = authenticated_client(advisor_wrong_user)

        self.sales_manager_client = sales_manager_client_at_default(
            username="mtx-sm"
        )
        self.dealer_owner_client = dealer_owner_client_at_default(
            username="mtx-owner"
        )


class PermissionMatrixLedgerRead(_PermissionMatrixBase):
    """GET .../ledger/ — six-case permission matrix."""

    def test_anonymous_gets_401_or_403(self):
        resp = self.anon.get(_url_ledger("MTX-DEFAULT-1"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_advisor_at_same_dealership_gets_403(self):
        resp = self.advisor_same_client.get(_url_ledger("MTX-DEFAULT-1"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_advisor_at_wrong_dealership_gets_403(self):
        resp = self.advisor_wrong_client.get(_url_ledger("MTX-DEFAULT-1"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sales_manager_at_same_dealership_gets_200(self):
        resp = self.sales_manager_client.get(_url_ledger("MTX-DEFAULT-1"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_dealer_owner_at_same_dealership_gets_200(self):
        resp = self.dealer_owner_client.get(_url_ledger("MTX-DEFAULT-1"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_cross_tenant_stock_number_returns_404(self):
        # Authorized user requesting a stock number that exists but
        # lives in another tenant. Same fail-closed shape as
        # AdminLeadDetailFailsClosedAcrossTenants — 404, not 200,
        # not 403 (which would leak existence).
        resp = self.sales_manager_client.get(_url_ledger("MTX-OTHER-1"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_stock_number_also_returns_404(self):
        # Identical response to the cross-tenant case → existence
        # is not leaked via differential status codes.
        resp = self.sales_manager_client.get(_url_ledger("DOES-NOT-EXIST"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class PermissionMatrixAcquisitionUpsert(_PermissionMatrixBase):
    """POST .../acquisition/ — six-case permission matrix."""

    valid_payload = {
        "source": SOURCE_AUCTION,
        "purchase_price": "18500.00",
        "purchase_date": "2026-05-01",
    }

    def test_anonymous_gets_401_or_403(self):
        resp = self.anon.post(
            _url_acquisition("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_advisor_at_same_dealership_gets_403(self):
        resp = self.advisor_same_client.post(
            _url_acquisition("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_advisor_at_wrong_dealership_gets_403(self):
        resp = self.advisor_wrong_client.post(
            _url_acquisition("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sales_manager_at_same_dealership_gets_201(self):
        resp = self.sales_manager_client.post(
            _url_acquisition("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_dealer_owner_at_same_dealership_gets_201(self):
        resp = self.dealer_owner_client.post(
            _url_acquisition("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_cross_tenant_stock_number_returns_404(self):
        resp = self.sales_manager_client.post(
            _url_acquisition("MTX-OTHER-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        # And no acquisition was created on the other-tenant vehicle.
        self.assertFalse(
            VehicleAcquisition.objects.filter(
                vehicle=self.vehicle_other
            ).exists()
        )


class PermissionMatrixCostCreate(_PermissionMatrixBase):
    """POST .../costs/ — six-case permission matrix."""

    valid_payload = {
        "category": CATEGORY_PARTS,
        "amount": "300.00",
        "incurred_at": "2026-05-15T12:00:00Z",
    }

    def test_anonymous_gets_401_or_403(self):
        resp = self.anon.post(
            _url_costs("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_advisor_at_same_dealership_gets_403(self):
        resp = self.advisor_same_client.post(
            _url_costs("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_advisor_at_wrong_dealership_gets_403(self):
        resp = self.advisor_wrong_client.post(
            _url_costs("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_sales_manager_at_same_dealership_gets_201(self):
        resp = self.sales_manager_client.post(
            _url_costs("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_dealer_owner_at_same_dealership_gets_201(self):
        resp = self.dealer_owner_client.post(
            _url_costs("MTX-DEFAULT-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_cross_tenant_stock_number_returns_404(self):
        resp = self.sales_manager_client.post(
            _url_costs("MTX-OTHER-1"),
            self.valid_payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            VehicleCost.objects.filter(vehicle=self.vehicle_other).exists()
        )


# =============================================================================
# READ ENDPOINT SCENARIOS
# =============================================================================


class ReadLedgerEmptyState(TestCase):
    """GET .../ledger/ for a vehicle with no acquisition and no
    costs — response is well-shaped, all totals ZERO, acquisition
    is null."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "READ-EMPTY", self.default, price=Decimal("22500.00")
        )
        self.client_ = sales_manager_client_at_default(username="read-empty-sm")

    def test_response_shape(self):
        resp = self.client_.get(_url_ledger("READ-EMPTY"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        # Vehicle header shape.
        self.assertEqual(data["vehicle"]["stock_number"], "READ-EMPTY")
        self.assertEqual(data["vehicle"]["price"], "22500.00")
        # Acquisition is null.
        self.assertIsNone(data["acquisition"])
        # Costs list is empty.
        self.assertEqual(data["costs"], [])
        # Totals block all "0.00".
        for field in (
            "acquisition_total",
            "flooring_total",
            "recon_total",
            "administrative_total",
            "photography_total",
            "actual_cost_total",
            "estimated_cost_total",
            "total_investment",
            "projected_total_investment",
        ):
            self.assertEqual(
                data["totals"][field], "0.00", f"totals.{field} should be 0.00"
            )
        # days_in_inventory None (no acquisition).
        self.assertIsNone(data["days_in_inventory"])
        # projected_gross = price - 0 = 22500.00.
        self.assertEqual(data["projected_gross"], "22500.00")


class ReadLedgerAcquisitionOnly(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "READ-ACQONLY", self.default, price=Decimal("24900.00")
        )
        _seed_acquisition(self.vehicle, self.default)
        self.client_ = sales_manager_client_at_default(username="read-acq-sm")

    def test_acquisition_totals_match_engine(self):
        expected = compute_totals(self.vehicle, dealership=self.default)
        resp = self.client_.get(_url_ledger("READ-ACQONLY"))
        data = resp.json()
        self.assertEqual(
            data["totals"]["acquisition_total"],
            str(expected.acquisition_total),
        )
        self.assertEqual(
            data["totals"]["total_investment"],
            str(expected.total_investment),
        )

    def test_projected_gross_hand_verified(self):
        # $24,900 asking - $19,950 acquisition ($18,500 + $475 + $850
        # + $125) = $4,950.
        resp = self.client_.get(_url_ledger("READ-ACQONLY"))
        data = resp.json()
        self.assertEqual(data["totals"]["acquisition_total"], "19950.00")
        self.assertEqual(data["projected_gross"], "4950.00")


class ReadLedgerMixedActualAndEstimate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "READ-MIXED", self.default, price=Decimal("24000.00")
        )
        _seed_acquisition(
            self.vehicle,
            self.default,
            price=Decimal("15000.00"),
            purchase_date=dt.date(2026, 5, 1),
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("300.00"),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_BODY_WORK,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
            is_estimate=False,
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_BODY_WORK,
            amount=Decimal("1200.00"),
            incurred_at=timezone.now(),
            is_estimate=True,
        )
        self.client_ = sales_manager_client_at_default(username="read-mixed-sm")

    def test_response_reflects_actual_vs_estimated_split(self):
        # Acquisition = $15,000 + $475 + $850 + $125 = $16,450.
        # Actual costs = $300 + $500 = $800.
        # Estimated = $1,200.
        # total_investment (excludes estimate) = $16,450 + $800 = $17,250.
        # projected_total_investment = $17,250 + $1,200 = $18,450.
        resp = self.client_.get(_url_ledger("READ-MIXED"))
        data = resp.json()
        self.assertEqual(data["totals"]["actual_cost_total"], "800.00")
        self.assertEqual(data["totals"]["estimated_cost_total"], "1200.00")
        self.assertEqual(data["totals"]["total_investment"], "17250.00")
        self.assertEqual(
            data["totals"]["projected_total_investment"], "18450.00"
        )

    def test_cost_projection_includes_is_estimate_flag_per_row(self):
        resp = self.client_.get(_url_ledger("READ-MIXED"))
        data = resp.json()
        estimate_flags = [c["is_estimate"] for c in data["costs"]]
        self.assertEqual(sorted(estimate_flags), [False, False, True])

    def test_cost_projection_includes_category_group_label(self):
        resp = self.client_.get(_url_ledger("READ-MIXED"))
        data = resp.json()
        for c in data["costs"]:
            self.assertIn(c["category_group"], ("recon",))


class ReadLedgerReversingEntry(TestCase):
    """A negative reversing row collapses the net; the API surfaces
    both rows and the correct net total."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("READ-REVERSAL", self.default)
        _seed_acquisition(self.vehicle, self.default)
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("500.00"),
            incurred_at=timezone.now(),
            reference="original",
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("-500.00"),
            incurred_at=timezone.now(),
            reference="reversal",
        )
        self.client_ = sales_manager_client_at_default(username="read-rev-sm")

    def test_both_rows_appear_in_costs(self):
        resp = self.client_.get(_url_ledger("READ-REVERSAL"))
        data = resp.json()
        # Two tire rows.
        tire_amounts = sorted(
            c["amount"] for c in data["costs"] if c["category"] == "tires"
        )
        self.assertEqual(tire_amounts, ["-500.00", "500.00"])

    def test_recon_total_is_zero_after_reversal(self):
        resp = self.client_.get(_url_ledger("READ-REVERSAL"))
        data = resp.json()
        self.assertEqual(data["totals"]["recon_total"], "0.00")


class ReadLedgerCostOrderingIsDeterministic(TestCase):
    """Costs come back in ascending ``incurred_at`` with ``pk``
    tie-break. Contract locked so M2.7 UI doesn't have to re-sort."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("READ-ORDER", self.default)
        _seed_acquisition(self.vehicle, self.default)
        now = timezone.now()
        # Insert in mixed date order to prove the API sorts them.
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("100"),
            incurred_at=now - dt.timedelta(days=30),
            reference="oldest",
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_DETAIL,
            amount=Decimal("100"),
            incurred_at=now,
            reference="newest",
        )
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_TIRES,
            amount=Decimal("100"),
            incurred_at=now - dt.timedelta(days=10),
            reference="middle",
        )
        self.client_ = sales_manager_client_at_default(username="read-ord-sm")

    def test_costs_come_back_ascending_by_incurred_at(self):
        resp = self.client_.get(_url_ledger("READ-ORDER"))
        data = resp.json()
        refs = [c["reference"] for c in data["costs"]]
        self.assertEqual(refs, ["oldest", "middle", "newest"])


class ReadLedgerContractStability(TestCase):
    """The JSON contract keys are stable so M2.7 can consume without
    reshaping. If a future increment renames a top-level key or
    drops a totals field, this test breaks and forces the
    conversation."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("READ-CONTRACT", self.default)
        _seed_acquisition(self.vehicle, self.default)
        self.client_ = sales_manager_client_at_default(username="read-cont-sm")

    def test_top_level_keys(self):
        resp = self.client_.get(_url_ledger("READ-CONTRACT"))
        self.assertEqual(
            set(resp.json().keys()),
            {
                "vehicle",
                "acquisition",
                "costs",
                "totals",
                "days_in_inventory",
                "projected_gross",
            },
        )

    def test_totals_keys(self):
        resp = self.client_.get(_url_ledger("READ-CONTRACT"))
        self.assertEqual(
            set(resp.json()["totals"].keys()),
            {
                "acquisition_total",
                "flooring_total",
                "recon_total",
                "administrative_total",
                "photography_total",
                "actual_cost_total",
                "estimated_cost_total",
                "total_investment",
                "projected_total_investment",
            },
        )

    def test_vehicle_header_keys(self):
        resp = self.client_.get(_url_ledger("READ-CONTRACT"))
        self.assertEqual(
            set(resp.json()["vehicle"].keys()),
            {
                "stock_number",
                "vin",
                "year",
                "make",
                "model",
                "trim",
                "price",
                "display_name",
            },
        )

    def test_all_money_fields_serialize_as_strings(self):
        resp = self.client_.get(_url_ledger("READ-CONTRACT"))
        data = resp.json()
        # Vehicle.price is a string.
        self.assertIsInstance(data["vehicle"]["price"], str)
        # Every totals field is a string.
        for value in data["totals"].values():
            self.assertIsInstance(value, str)
        # projected_gross is a string.
        self.assertIsInstance(data["projected_gross"], str)
        # Every acquisition Decimal field is a string.
        for key in ("purchase_price", "buyer_fees", "transportation_cost"):
            self.assertIsInstance(data["acquisition"][key], str)


class ReadLedgerCrossTenantIsolation(TestCase):
    """A caller at dealership A must never see data from dealership B.

    Note: ``Vehicle.stock_number`` is globally unique today (tenant-
    scoped uniqueness is deferred per Milestone 2 planning §5), so
    a "same stock number in two tenants" collision scenario cannot
    be constructed. The load-bearing invariant here — "the endpoint
    scopes reads to the caller's dealership" — is covered by:

    - ``PermissionMatrixLedgerRead.test_cross_tenant_stock_number_returns_404``
      (auth'd caller from A → B's stock → 404).
    - This class's positive test: caller from A sees ONLY A's costs
      even when B has costs on a different vehicle.
    """

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = make_dealership(slug="isolation-other")
        self.vehicle_default = _make_vehicle(
            "ISO-DEFAULT", self.default, price=Decimal("20000.00")
        )
        self.vehicle_other = _make_vehicle(
            "ISO-OTHER", self.other, price=Decimal("35000.00")
        )
        _seed_acquisition(
            self.vehicle_default,
            self.default,
            price=Decimal("15000.00"),
        )
        _seed_acquisition(
            self.vehicle_other,
            self.other,
            price=Decimal("28000.00"),
        )
        # Add costs to BOTH tenants to prove neither's totals leak
        # into the other's response.
        add_cost(
            self.vehicle_default,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("200.00"),
            incurred_at=timezone.now(),
        )
        add_cost(
            self.vehicle_other,
            dealership=self.other,
            category=CATEGORY_PARTS,
            amount=Decimal("999.99"),
            incurred_at=timezone.now(),
        )
        self.client_ = sales_manager_client_at_default(username="isolate-sm")

    def test_response_only_reflects_default_tenants_data(self):
        # Request default's vehicle — sees default's acquisition and
        # costs only.
        resp = self.client_.get(_url_ledger("ISO-DEFAULT"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["vehicle"]["price"], "20000.00")
        self.assertEqual(data["acquisition"]["purchase_price"], "15000.00")
        # Cost amounts include $200.00 (default's) but NOT $999.99
        # (the other tenant's marker).
        amounts = [c["amount"] for c in data["costs"]]
        self.assertIn("200.00", amounts)
        self.assertNotIn("999.99", amounts)


# =============================================================================
# ACQUISITION UPSERT SCENARIOS
# =============================================================================


class AcquisitionCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("ACQ-CREATE", self.default)
        self.client_ = sales_manager_client_at_default(username="acq-create-sm")

    def test_first_call_creates_returns_201_with_created_true(self):
        resp = self.client_.post(
            _url_acquisition("ACQ-CREATE"),
            {
                "source": SOURCE_AUCTION,
                "source_detail": "Manheim Phoenix",
                "purchase_price": "18500.00",
                "purchase_date": "2026-05-01",
                "buyer_fees": "475.00",
                "transportation_cost": "850.00",
                "title_acquisition_cost": "125.00",
                "notes": "Frame check passed.",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        self.assertTrue(data["created"])
        self.assertEqual(data["acquisition"]["source"], "auction")
        self.assertEqual(data["acquisition"]["source_display"], "Auction")
        self.assertEqual(data["acquisition"]["purchase_price"], "18500.00")
        # Row exists in DB.
        self.assertEqual(
            VehicleAcquisition.objects.filter(vehicle=self.vehicle).count(),
            1,
        )


class AcquisitionUpdate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("ACQ-UPDATE", self.default)
        _seed_acquisition(self.vehicle, self.default)
        self.client_ = sales_manager_client_at_default(username="acq-update-sm")

    def test_second_call_updates_returns_200_with_created_false(self):
        resp = self.client_.post(
            _url_acquisition("ACQ-UPDATE"),
            {
                "source": SOURCE_TRADE,
                "purchase_price": "17000.00",
                "purchase_date": "2026-05-15",
                "source_detail": "reclassified",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertFalse(data["created"])
        self.assertEqual(data["acquisition"]["source"], "trade")
        self.assertEqual(data["acquisition"]["purchase_price"], "17000.00")
        # Still exactly one row — upsert, never a second.
        self.assertEqual(
            VehicleAcquisition.objects.filter(vehicle=self.vehicle).count(),
            1,
        )


class AcquisitionInvalidInput(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("ACQ-INVALID", self.default)
        self.client_ = sales_manager_client_at_default(username="acq-invalid-sm")

    def test_invalid_source_choice_returns_400_with_field_error(self):
        resp = self.client_.post(
            _url_acquisition("ACQ-INVALID"),
            {
                "source": "carfax",  # not in ACQUISITION_SOURCE_CHOICES
                "purchase_price": "18500.00",
                "purchase_date": "2026-05-01",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("source", resp.json())

    def test_missing_required_field_returns_400(self):
        resp = self.client_.post(
            _url_acquisition("ACQ-INVALID"),
            {
                "source": SOURCE_AUCTION,
                # missing purchase_price + purchase_date
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        body = resp.json()
        self.assertIn("purchase_price", body)
        self.assertIn("purchase_date", body)

    def test_invalid_decimal_returns_400(self):
        resp = self.client_.post(
            _url_acquisition("ACQ-INVALID"),
            {
                "source": SOURCE_AUCTION,
                "purchase_price": "not-a-number",
                "purchase_date": "2026-05-01",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("purchase_price", resp.json())

    def test_negative_purchase_price_returns_400(self):
        # min_value=0 on the serializer field.
        resp = self.client_.post(
            _url_acquisition("ACQ-INVALID"),
            {
                "source": SOURCE_AUCTION,
                "purchase_price": "-100.00",
                "purchase_date": "2026-05-01",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("purchase_price", resp.json())

    def test_source_choices_enum_covers_all_canonical_values(self):
        # Prove every canonical source in the model constants is
        # accepted by the endpoint — locks the serializer's
        # ChoiceField against silent divergence from the model.
        for source_key, _ in ACQUISITION_SOURCE_CHOICES:
            vehicle = _make_vehicle(
                f"ACQ-INV-CHOICE-{source_key}", self.default
            )
            resp = self.client_.post(
                _url_acquisition(vehicle.stock_number),
                {
                    "source": source_key,
                    "purchase_price": "10000.00",
                    "purchase_date": "2026-05-01",
                },
                format="json",
            )
            self.assertEqual(
                resp.status_code,
                status.HTTP_201_CREATED,
                f"canonical source {source_key!r} rejected by serializer",
            )


# =============================================================================
# COST CREATE SCENARIOS
# =============================================================================


class CostCreateValid(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("COST-VALID", self.default)
        self.client_ = sales_manager_client_at_default(username="cost-valid-sm")

    def test_valid_cost_creation_returns_201_with_projection(self):
        resp = self.client_.post(
            _url_costs("COST-VALID"),
            {
                "category": CATEGORY_PARTS,
                "amount": "300.00",
                "incurred_at": "2026-05-15T12:00:00Z",
                "vendor": "Rick's Auto Parts",
                "reference": "INV-8842",
                "notes": "Front brake pads",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.json()
        cost = data["cost"]
        self.assertEqual(cost["category"], "parts")
        self.assertEqual(cost["category_display"], "Parts")
        self.assertEqual(cost["category_group"], "recon")
        self.assertEqual(cost["amount"], "300.00")
        self.assertEqual(cost["vendor"], "Rick's Auto Parts")
        self.assertFalse(cost["is_estimate"])

    def test_is_estimate_defaults_to_false(self):
        resp = self.client_.post(
            _url_costs("COST-VALID"),
            {
                "category": CATEGORY_PHOTOGRAPHY,
                "amount": "150.00",
                "incurred_at": "2026-05-15T12:00:00Z",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(resp.json()["cost"]["is_estimate"])


class CostCreateNegativeReversal(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("COST-REV", self.default)
        self.client_ = sales_manager_client_at_default(username="cost-rev-sm")

    def test_negative_amount_is_permitted(self):
        # Post original.
        r1 = self.client_.post(
            _url_costs("COST-REV"),
            {
                "category": CATEGORY_PARTS,
                "amount": "150.00",
                "incurred_at": "2026-05-15T12:00:00Z",
                "reference": "original",
            },
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        # Post reversal.
        r2 = self.client_.post(
            _url_costs("COST-REV"),
            {
                "category": CATEGORY_PARTS,
                "amount": "-150.00",
                "incurred_at": "2026-05-15T12:30:00Z",
                "reference": "REVERSAL: parts invoice",
            },
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.json()["cost"]["amount"], "-150.00")
        # Both rows exist.
        self.assertEqual(
            VehicleCost.objects.filter(vehicle=self.vehicle).count(), 2
        )


class CostCreateInvalidInput(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("COST-INV", self.default)
        self.client_ = sales_manager_client_at_default(username="cost-inv-sm")

    def test_invalid_category_returns_400_with_field_error(self):
        resp = self.client_.post(
            _url_costs("COST-INV"),
            {
                "category": "nonexistent_category",
                "amount": "100.00",
                "incurred_at": "2026-05-15T12:00:00Z",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", resp.json())

    def test_missing_required_fields_returns_400(self):
        resp = self.client_.post(
            _url_costs("COST-INV"), {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        body = resp.json()
        self.assertIn("category", body)
        self.assertIn("amount", body)
        self.assertIn("incurred_at", body)

    def test_invalid_decimal_returns_400(self):
        resp = self.client_.post(
            _url_costs("COST-INV"),
            {
                "category": CATEGORY_PARTS,
                "amount": "not-a-number",
                "incurred_at": "2026-05-15T12:00:00Z",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("amount", resp.json())

    def test_invalid_datetime_returns_400(self):
        resp = self.client_.post(
            _url_costs("COST-INV"),
            {
                "category": CATEGORY_PARTS,
                "amount": "100.00",
                "incurred_at": "not-a-date",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("incurred_at", resp.json())


class CostCreatedByAttribution(TestCase):
    """The view sets ``created_by=request.user`` — a client-supplied
    ``created_by`` in the request body must NOT override it (which
    would let an authenticated operator forge cost authorship)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("COST-ATTR", self.default)
        self.client_ = sales_manager_client_at_default(
            username="cost-attribution-author"
        )

    def test_created_by_is_the_authenticated_user(self):
        resp = self.client_.post(
            _url_costs("COST-ATTR"),
            {
                "category": CATEGORY_DETAIL,
                "amount": "85.00",
                "incurred_at": "2026-05-15T12:00:00Z",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            resp.json()["cost"]["created_by"],
            "cost-attribution-author",
        )

    def test_client_supplied_created_by_is_ignored(self):
        # Attempt to spoof authorship — extra field just gets
        # ignored by the serializer (it's not declared).
        resp = self.client_.post(
            _url_costs("COST-ATTR"),
            {
                "category": CATEGORY_DETAIL,
                "amount": "85.00",
                "incurred_at": "2026-05-15T12:00:00Z",
                "created_by": "someone-else",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            resp.json()["cost"]["created_by"],
            "cost-attribution-author",
            "created_by must come from request.user, not the body",
        )


class CostImmutableRoutes(TestCase):
    """No update / delete route in v1 — corrections are reversing
    entries. Prove by attempting PUT/PATCH/DELETE on the cost URL
    and seeing 405 (method not allowed)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("COST-IMMUT", self.default)
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("100"),
            incurred_at=timezone.now(),
        )
        self.client_ = sales_manager_client_at_default(username="cost-immut-sm")

    def test_put_on_costs_route_is_405(self):
        resp = self.client_.put(
            _url_costs("COST-IMMUT"), {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_on_costs_route_is_405(self):
        resp = self.client_.patch(
            _url_costs("COST-IMMUT"), {}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_on_costs_route_is_405(self):
        resp = self.client_.delete(_url_costs("COST-IMMUT"))
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# =============================================================================
# SECURITY VERIFICATION — no ledger data on public surfaces
# =============================================================================


class PublicSurfacesNeverExposeLedgerData(TestCase):
    """Explicit sanity that the new ledger surface does not
    accidentally leak into any public endpoint. Public routes stay
    unauthenticated and their responses do NOT include ledger fields
    (acquisition_total, total_investment, projected_gross, etc.).
    """

    _LEDGER_KEYWORDS = (
        "acquisition_total",
        "actual_cost_total",
        "estimated_cost_total",
        "total_investment",
        "projected_total_investment",
        "flooring_total",
        "recon_total",
        "administrative_total",
        "photography_total",
        "projected_gross",
        "purchase_price",
        "buyer_fees",
        "arbitration_fees",
        "transportation_cost",
        "title_acquisition_cost",
    )

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle(
            "PUBLIC-SEC", self.default, price=Decimal("22500.00")
        )
        _seed_acquisition(self.vehicle, self.default)
        add_cost(
            self.vehicle,
            dealership=self.default,
            category=CATEGORY_PARTS,
            amount=Decimal("500"),
            incurred_at=timezone.now(),
        )
        # Milestone 6 · Increment 5 (SESSION_086) — the customer-
        # facing vehicle_detail endpoint now requires both
        # ``stage=frontline`` (M5.5 test-only auto-bootstrap seeds
        # this) AND a published :class:`VehicleListing`. Publish a
        # test-fixture listing so the ledger-leakage security check
        # can actually reach the endpoint's 200 path.
        from dealer_ai.models import (
            VEHICLE_LISTING_STATUS_PUBLISHED,
            VehicleListing,
        )
        now = timezone.now()
        VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_PUBLISHED,
            body="Ledger security test fixture — published listing.",
            drafted_at=now,
            approved_at=now,
            published_at=now,
        )
        self.anon = APIClient()

    def _assert_no_ledger_keywords(self, response_body: str, url: str) -> None:
        for keyword in self._LEDGER_KEYWORDS:
            self.assertNotIn(
                keyword,
                response_body,
                f"ledger keyword {keyword!r} leaked into public endpoint {url}",
            )

    def test_vehicle_detail_public_response_has_no_ledger_data(self):
        # Public route (customer-facing per-vehicle detail).
        url = f"/api/dealer-ai/vehicles/{self.vehicle.pk}/"
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self._assert_no_ledger_keywords(resp.content.decode("utf-8"), url)

    def test_public_salespeople_response_has_no_ledger_data(self):
        url = "/api/dealer-ai/salespeople/"
        resp = self.anon.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self._assert_no_ledger_keywords(resp.content.decode("utf-8"), url)

    def test_public_onboarding_get_has_no_ledger_data(self):
        # Public branding GET (part of the customer-facing chrome).
        url = "/api/dealer-ai/onboarding/profile/"
        resp = self.anon.get(url)
        # 200 (public) — not 401.
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self._assert_no_ledger_keywords(resp.content.decode("utf-8"), url)

    def test_public_routes_remain_unauthenticated(self):
        # Belt: three sample public routes still respond 200 without
        # auth. If a future change accidentally requires auth for one,
        # this test breaks and forces the conversation.
        for url in (
            f"/api/dealer-ai/vehicles/{self.vehicle.pk}/",
            "/api/dealer-ai/salespeople/",
            "/api/dealer-ai/onboarding/profile/",
        ):
            resp = self.anon.get(url)
            self.assertEqual(
                resp.status_code,
                status.HTTP_200_OK,
                f"public endpoint {url} unexpectedly required auth: "
                f"got {resp.status_code}",
            )

    def test_default_permission_classes_remains_unset(self):
        # M1 · 4B invariant: the DRF-global default stays AllowAny.
        # Any new endpoint declares its own permission classes; the
        # M2.6 ledger endpoints do. This lock keeps future
        # additions from silently gaining a 401.
        from django.conf import settings

        rest_config = getattr(settings, "REST_FRAMEWORK", {}) or {}
        self.assertNotIn(
            "DEFAULT_PERMISSION_CLASSES",
            rest_config,
            "DEFAULT_PERMISSION_CLASSES must remain unset per "
            "AUTHENTICATION_MODEL.md §7.",
        )
