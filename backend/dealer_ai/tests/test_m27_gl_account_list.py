"""Milestone 27 · Increment 1 (SESSION_192) — GLAccount list endpoint tests.

Guards the M27.1 substrate that the M27.2 JE-create dialog + all
future accounting workflows needing GLAccount selection consume.

Behaviors asserted:

- **Positive** — endpoint returns the current tenant's active
  chart of accounts sorted by ``code`` ASC, with the expected
  envelope shape (``{"gl_accounts": {"accounts": [...]}}``) and
  per-row projection (``id`` + ``code`` + ``name`` + ``type``).
- **Zero-balance inclusion** — accounts with no posted lines
  still appear (contrast with the trial-balance endpoint, which
  aggregates over JournalEntryLines and therefore filters
  activity).
- **Soft-hidden exclusion** — accounts with ``is_active=False``
  are omitted. This is the operator-facing soft-hide mechanism
  per the M13.1 GLAccount model contract; inactive accounts
  must never surface in a create-workflow picker.
- **Cross-tenant isolation** — another dealership's accounts do
  not leak into the current tenant's response.
- **Permission enforcement** — the endpoint reuses
  ``_M131_PERMS`` (IsAuthenticated &
  IsSalesManagerOrOwnerAtActiveDealership); an advisor-role
  membership is denied.
- **Authentication required** — an unauthenticated request is
  rejected (401 / 403 per DRF default).
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EQUITY,
    GL_ACCOUNT_TYPE_EXPENSE,
    GL_ACCOUNT_TYPE_LIABILITY,
    GL_ACCOUNT_TYPE_REVENUE,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    Dealership,
    GLAccount,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


LIST = "dealer_ai:admin-gl-account-list"


def _sm_client(username: str = "sm-user") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_SALES_MANAGER)
    return authenticated_client(user)


def _advisor_client(username: str = "advisor-user") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_ADVISOR)
    return authenticated_client(user)


def _seed_full_coa(dealership: Dealership) -> dict[str, GLAccount]:
    """Seed one account per type, ordered non-alphabetically by code
    so the sort assertion has genuine signal."""
    return {
        "revenue": GLAccount.objects.create(
            dealership=dealership,
            code="M27-400000",
            name="Revenue",
            account_type=GL_ACCOUNT_TYPE_REVENUE,
        ),
        "asset": GLAccount.objects.create(
            dealership=dealership,
            code="M27-100000",
            name="Cash — Operating",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        ),
        "expense": GLAccount.objects.create(
            dealership=dealership,
            code="M27-500000",
            name="Cost of Sales",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        ),
        "liability": GLAccount.objects.create(
            dealership=dealership,
            code="M27-200000",
            name="Accounts Payable",
            account_type=GL_ACCOUNT_TYPE_LIABILITY,
        ),
        "equity": GLAccount.objects.create(
            dealership=dealership,
            code="M27-300000",
            name="Owner Equity",
            account_type=GL_ACCOUNT_TYPE_EQUITY,
        ),
    }


class GLAccountListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.accounts = _seed_full_coa(self.dealership)
        self.client_ = _sm_client()

    def test_get_returns_envelope_shape(self) -> None:
        response = self.client_.get(reverse(LIST))
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn("gl_accounts", body)
        self.assertIn("accounts", body["gl_accounts"])
        self.assertIsInstance(body["gl_accounts"]["accounts"], list)

    def test_get_returns_active_coa_sorted_by_code(self) -> None:
        response = self.client_.get(reverse(LIST))
        accounts = response.json()["gl_accounts"]["accounts"]
        codes = [row["code"] for row in accounts]
        # Assertion: the five M27-* seeded codes appear in ASC order.
        # (The tenant may carry additional M13.1-seeded default COA
        # rows; assert relative order of the seeded slice.)
        m27_codes = [c for c in codes if c.startswith("M27-")]
        self.assertEqual(
            m27_codes,
            [
                "M27-100000",
                "M27-200000",
                "M27-300000",
                "M27-400000",
                "M27-500000",
            ],
        )

    def test_row_projection_carries_id_code_name_type(self) -> None:
        response = self.client_.get(reverse(LIST))
        accounts = response.json()["gl_accounts"]["accounts"]
        asset_row = next(
            (r for r in accounts if r["code"] == "M27-100000"), None
        )
        self.assertIsNotNone(asset_row)
        self.assertEqual(
            set(asset_row.keys()), {"id", "code", "name", "type"}
        )
        self.assertEqual(asset_row["id"], self.accounts["asset"].pk)
        self.assertEqual(asset_row["code"], "M27-100000")
        self.assertEqual(asset_row["name"], "Cash — Operating")
        self.assertEqual(asset_row["type"], GL_ACCOUNT_TYPE_ASSET)

    def test_zero_balance_accounts_are_included(self) -> None:
        # None of the M27-* seeded accounts have any posted lines.
        # If the endpoint were incorrectly activity-filtered, they
        # would be absent.
        response = self.client_.get(reverse(LIST))
        codes = {
            row["code"]
            for row in response.json()["gl_accounts"]["accounts"]
        }
        for m27_code in [
            "M27-100000",
            "M27-200000",
            "M27-300000",
            "M27-400000",
            "M27-500000",
        ]:
            self.assertIn(
                m27_code,
                codes,
                f"zero-balance account {m27_code} should appear",
            )

    def test_soft_hidden_accounts_excluded(self) -> None:
        # Soft-hide one of the seeded accounts and confirm it drops
        # out of the response while the others remain.
        self.accounts["expense"].is_active = False
        self.accounts["expense"].save(update_fields=["is_active"])
        response = self.client_.get(reverse(LIST))
        codes = {
            row["code"]
            for row in response.json()["gl_accounts"]["accounts"]
        }
        self.assertNotIn("M27-500000", codes)
        # Sibling active rows still present.
        self.assertIn("M27-100000", codes)
        self.assertIn("M27-400000", codes)

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            name="Other Dealer", slug="m27-other"
        )
        GLAccount.objects.create(
            dealership=other,
            code="M27-OTHER-999",
            name="Do Not Leak",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        response = self.client_.get(reverse(LIST))
        codes = {
            row["code"]
            for row in response.json()["gl_accounts"]["accounts"]
        }
        self.assertNotIn("M27-OTHER-999", codes)

    def test_advisor_role_forbidden(self) -> None:
        response = _advisor_client().get(reverse(LIST))
        # ``IsSalesManagerOrOwnerAtActiveDealership`` returns False for
        # an advisor membership; DRF turns that into 403.
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_rejected(self) -> None:
        response = APIClient().get(reverse(LIST))
        self.assertIn(response.status_code, (401, 403))
