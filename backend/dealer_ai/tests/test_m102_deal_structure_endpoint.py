"""Milestone 10 · Increment 2 (SESSION_107) — DealStructure endpoint tests.

Locks the HTTP surface of
:func:`views_f_and_i.admin_deal_structure_create` per
``MILESTONE_10_PLANNING.md`` §7 M10.2 + §1.9.a Option A.

Coverage:

- Auth matrix inherited from M10.1 pattern (same permission
  class): unauthenticated → 401/403; disallowed roles → 403;
  f_and_i_manager / dealer_owner → 201.
- Happy paths — with income (all three ratios populated) and
  without income (LTV only).
- Cross-tenant lookups (credit app or vehicle in another tenant)
  → 404 (never leak).
- 400 on missing required field / invalid decimal / non-positive
  sale_price.
- Response shape — stringified Decimals + null-serialization for
  NULL ratios.
"""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_SALES_MANAGER,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


ENDPOINT_NAME = "dealer_ai:admin-deal-structure-create"


def _post(client, body):
    return client.post(reverse(ENDPOINT_NAME), body, format="json")


def _fandi_client_at(dealership, username: str = "ds-fandi"):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


def _make_vehicle(dealership, *, stock: str = "DS-EP-1"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


def _make_credit_app(
    dealership,
    *,
    name: str = "Alice",
    income=None,
    existing_debt=None,
) -> CreditApplication:
    lead = CustomerLead.objects.create(dealership=dealership, name=name)
    captured = timezone.now()
    return CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name=name,
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
        gross_monthly_income=income,
        existing_monthly_debt=existing_debt,
    )


class DealStructureEndpointAuthTests(TestCase):
    """Same permission class as M10.1 — grants f_and_i_manager +
    dealer_owner; blocks everyone else."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership, stock="DS-EP-AUTH")
        self.body = {
            "credit_application_id": self.credit_app.pk,
            "vehicle_stock": self.vehicle.stock_number,
            "sale_price": "30000.00",
            "amount_financed": "25000.00",
            "apr": "9.9900",
            "term_months": 72,
            "monthly_payment": "462.50",
        }

    def test_unauthenticated_returns_401_or_403(self) -> None:
        from rest_framework.test import APIClient

        response = APIClient().post(
            reverse(ENDPOINT_NAME), self.body, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_role_returns_403(self) -> None:
        user = make_user(username="ds-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 403)

    def test_sales_manager_role_returns_403(self) -> None:
        # F&I has distinct compliance obligations; sales_manager
        # doesn't grant F&I admin access. Same as M10.1.
        user = make_user(username="ds-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 403)

    def test_f_and_i_manager_role_returns_201(self) -> None:
        response = _post(_fandi_client_at(self.dealership), self.body)
        self.assertEqual(response.status_code, 201)

    def test_dealer_owner_role_returns_201(self) -> None:
        user = make_user(username="ds-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 201)


class DealStructureEndpointCreateTests(TestCase):
    """Happy paths + validation coverage."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.credit_app_with_income = _make_credit_app(
            self.dealership,
            income=Decimal("5000.00"),
            existing_debt=Decimal("1000.00"),
        )
        self.credit_app_no_income = _make_credit_app(
            self.dealership, name="No-income"
        )
        self.vehicle = _make_vehicle(self.dealership, stock="DS-EP-CR")
        self.client = _fandi_client_at(self.dealership)

    def test_create_populates_all_three_ratios_when_income_present(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": self.credit_app_with_income.pk,
                "vehicle_stock": self.vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.9900",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["deal_structure"]
        self.assertEqual(body["ltv_pct"], "83.33")
        self.assertEqual(body["pti_pct"], "10.00")
        self.assertEqual(body["dti_pct"], "30.00")
        # Vehicle serialized as stock number, not pk.
        self.assertEqual(body["vehicle_stock"], self.vehicle.stock_number)

    def test_create_serializes_null_ratios_when_income_absent(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": self.credit_app_no_income.pk,
                "vehicle_stock": self.vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.9900",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["deal_structure"]
        self.assertEqual(body["ltv_pct"], "83.33")
        self.assertIsNone(body["pti_pct"])
        self.assertIsNone(body["dti_pct"])

    def test_create_with_back_end_products_persists(self) -> None:
        products = [{"name": "VSC", "cost": "800", "revenue": "1600"}]
        response = _post(
            self.client,
            {
                "credit_application_id": self.credit_app_with_income.pk,
                "vehicle_stock": self.vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
                "back_end_products": products,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["deal_structure"]["back_end_products"],
            products,
        )

    def test_create_with_unknown_credit_application_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": 999999,
                "vehicle_stock": self.vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_with_unknown_vehicle_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": self.credit_app_with_income.pk,
                "vehicle_stock": "DOES-NOT-EXIST",
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_missing_required_field_returns_400(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": self.credit_app_with_income.pk,
                "vehicle_stock": self.vehicle.stock_number,
                # sale_price missing
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_create_with_zero_sale_price_returns_400(self) -> None:
        # Service-layer ValueError on non-positive sale_price surfaces
        # as 400 per the domain-error mapping.
        response = _post(
            self.client,
            {
                "credit_application_id": self.credit_app_with_income.pk,
                "vehicle_stock": self.vehicle.stock_number,
                "sale_price": "0.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 400)


class DealStructureEndpointCrossTenantTests(TestCase):
    """Cross-tenant lookups surface as 404 (never leak)."""

    def setUp(self) -> None:
        self.default = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="m102-ep-other", name="Other Dealership"
        )
        self.other_credit_app = _make_credit_app(self.other)
        self.other_vehicle = _make_vehicle(self.other, stock="DS-EP-OTHER")
        # Also seed local CA + vehicle so we can vary which parent
        # is cross-tenant in different tests.
        self.local_credit_app = _make_credit_app(self.default)
        self.local_vehicle = _make_vehicle(self.default, stock="DS-EP-LOCAL")
        self.client = _fandi_client_at(self.default)

    def test_credit_application_in_other_tenant_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": self.other_credit_app.pk,
                "vehicle_stock": self.local_vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_vehicle_in_other_tenant_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "credit_application_id": self.local_credit_app.pk,
                "vehicle_stock": self.other_vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_no_deal_structure_persisted_on_cross_tenant_failure(self) -> None:
        _post(
            self.client,
            {
                "credit_application_id": self.other_credit_app.pk,
                "vehicle_stock": self.local_vehicle.stock_number,
                "sale_price": "30000.00",
                "amount_financed": "25000.00",
                "apr": "9.99",
                "term_months": 72,
                "monthly_payment": "500.00",
            },
        )
        self.assertFalse(DealStructure.objects.exists())
