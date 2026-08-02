"""Milestone 10 · Increment 1 (SESSION_106) — CreditApplication endpoint tests.

Locks the HTTP surface of
:func:`views_f_and_i.admin_credit_application_create` per
``MILESTONE_10_PLANNING.md`` §7 M10.1.

Coverage:

- Unauthenticated → 401 / 403.
- Authenticated with no dealership membership → 403.
- Authenticated with disallowed role (advisor / porter /
  sales_manager / recon_manager / collections) → 403.
- Authenticated with allowed role (f_and_i_manager / dealer_owner)
  → 201 on success.
- Cross-tenant isolation — a POST for a lead / sale owned by
  tenant B never lands from a request in tenant A (surfaces as
  404, not 403).
- 400 on invalid source_format / missing required field / neither
  lead nor sale provided.
- Response shape (``credit_application`` dict with ISO-formatted
  datetimes).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_FORMAT_TABLET,
    CREDIT_APP_STATUS_RECEIVED,
    CREDIT_APP_STATUS_SUBMITTED,
    ROLE_ADVISOR,
    ROLE_COLLECTIONS,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_RECON_MANAGER,
    ROLE_SALES_MANAGER,
    SALE_FINANCE_TYPE_CASH,
    CreditApplication,
    CustomerLead,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


ENDPOINT_NAME = "dealer_ai:admin-credit-application-create"


def _post(client, body):
    return client.post(
        reverse(ENDPOINT_NAME), body, format="json"
    )


def _make_lead(dealership: Dealership, *, name: str = "Alice Applicant") -> CustomerLead:
    return CustomerLead.objects.create(dealership=dealership, name=name)


def _make_sale(dealership: Dealership, *, stock: str = "EP-1") -> Sale:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("30000.00"),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=Decimal("1500.00"),
    )


class CreditApplicationEndpointAuthTests(TestCase):
    """Authentication + authorization gates."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = _make_lead(self.dealership)
        self.body = {
            "applicant_full_name": "Alice",
            "source_format": CREDIT_APP_FORMAT_PAPER,
            "lead_id": self.lead.pk,
        }

    def test_unauthenticated_returns_401_or_403(self) -> None:
        # DRF's default for anon on a permission-denied endpoint is
        # 401 when auth classes are configured, 403 otherwise. Accept
        # either — the test locks that anon is not admitted.
        from rest_framework.test import APIClient

        response = APIClient().post(
            reverse(ENDPOINT_NAME), self.body, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_no_membership_returns_403(self) -> None:
        user = make_user(username="ep-nomembership")
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 403)

    def _role_returns_403(self, role: str) -> None:
        user = make_user(username=f"ep-{role}")
        make_membership(user, self.dealership, role)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 403)

    def test_advisor_role_returns_403(self) -> None:
        self._role_returns_403(ROLE_ADVISOR)

    def test_porter_role_returns_403(self) -> None:
        self._role_returns_403(ROLE_PORTER)

    def test_sales_manager_role_returns_403(self) -> None:
        # F&I has distinct compliance obligations (Safeguards Rule,
        # Red Flags, FCRA) that sales_manager does not carry. Lock
        # this at the endpoint layer.
        self._role_returns_403(ROLE_SALES_MANAGER)

    def test_recon_manager_role_returns_403(self) -> None:
        self._role_returns_403(ROLE_RECON_MANAGER)

    def test_collections_role_returns_403(self) -> None:
        self._role_returns_403(ROLE_COLLECTIONS)

    def test_f_and_i_manager_role_returns_201(self) -> None:
        user = make_user(username="ep-fandi")
        make_membership(user, self.dealership, ROLE_F_AND_I_MANAGER)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 201)

    def test_dealer_owner_role_returns_201(self) -> None:
        user = make_user(username="ep-owner")
        make_membership(user, self.dealership, ROLE_DEALER_OWNER)
        response = _post(authenticated_client(user), self.body)
        self.assertEqual(response.status_code, 201)


def _fandi_client_at_default(username: str = "fandi-mgr"):
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


class CreditApplicationEndpointCreateTests(TestCase):
    """Happy-path + validation coverage."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = _make_lead(self.dealership)
        self.sale = _make_sale(self.dealership)
        self.client = _fandi_client_at_default()

    def test_create_with_lead_only_returns_201_and_projected_row(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "Alice",
                "source_format": CREDIT_APP_FORMAT_TABLET,
                "lead_id": self.lead.pk,
                "applicant_ssn_last4": "1234",
                "notes": "Prime credit expected.",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("credit_application", body)
        app_dict = body["credit_application"]
        self.assertEqual(app_dict["applicant_full_name"], "Alice")
        self.assertEqual(app_dict["source_format"], CREDIT_APP_FORMAT_TABLET)
        self.assertEqual(app_dict["lead_id"], self.lead.pk)
        self.assertIsNone(app_dict["sale_id"])
        self.assertEqual(app_dict["applicant_ssn_last4"], "1234")
        self.assertEqual(app_dict["status"], CREDIT_APP_STATUS_RECEIVED)
        self.assertEqual(app_dict["notes"], "Prime credit expected.")
        # Retention datetimes are ISO-formatted strings.
        self.assertIsInstance(app_dict["captured_at"], str)
        self.assertIsInstance(app_dict["retention_expires_at"], str)

    def test_create_with_sale_only_returns_201(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "Bob",
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "sale_id": self.sale.pk,
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["credit_application"]
        self.assertIsNone(body["lead_id"])
        self.assertEqual(body["sale_id"], self.sale.pk)

    def test_create_with_explicit_status_persists(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "Carol",
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "lead_id": self.lead.pk,
                "status": CREDIT_APP_STATUS_SUBMITTED,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["credit_application"]["status"],
            CREDIT_APP_STATUS_SUBMITTED,
        )

    def test_create_without_lead_or_sale_returns_400(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "Orphan",
                "source_format": CREDIT_APP_FORMAT_PAPER,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_create_with_unknown_lead_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "Ghost",
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "lead_id": 999999,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_with_invalid_source_format_returns_400(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "Fax",
                "source_format": "fax",
                "lead_id": self.lead.pk,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_create_missing_applicant_name_returns_400(self) -> None:
        response = _post(
            self.client,
            {
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "lead_id": self.lead.pk,
            },
        )
        self.assertEqual(response.status_code, 400)


class CreditApplicationEndpointCrossTenantTests(TestCase):
    """Cross-tenant lead / sale surface as 404 (never leak)."""

    def setUp(self) -> None:
        self.default = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="m101-ep-other", name="Other Dealership"
        )
        self.other_lead = _make_lead(self.other, name="Other Lead")
        self.other_sale = _make_sale(self.other, stock="EP-OTHER")
        self.client = _fandi_client_at_default(username="fandi-cross")

    def test_lead_in_other_tenant_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "X-tenant lead",
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "lead_id": self.other_lead.pk,
            },
        )
        # 404, not 403 — never leak whether the resource exists across tenants.
        self.assertEqual(response.status_code, 404)

    def test_sale_in_other_tenant_returns_404(self) -> None:
        response = _post(
            self.client,
            {
                "applicant_full_name": "X-tenant sale",
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "sale_id": self.other_sale.pk,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_no_credit_application_persisted_on_cross_tenant_failure(self) -> None:
        _post(
            self.client,
            {
                "applicant_full_name": "X-tenant lead",
                "source_format": CREDIT_APP_FORMAT_PAPER,
                "lead_id": self.other_lead.pk,
            },
        )
        self.assertFalse(CreditApplication.objects.exists())
