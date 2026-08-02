"""Milestone 13 · Increment 3 (SESSION_131) — trial-balance endpoint tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_REVENUE,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    Dealership,
    GLAccount,
)
from dealer_ai.services.accounting import (
    JournalLineInput,
    post_journal_entry,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


TB_URL = "dealer_ai:admin-trial-balance"


def _sm_client(username: str = "tb-sm") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_SALES_MANAGER)
    return authenticated_client(user)


def _acct(dealership: Dealership, code: str, name: str, atype: str) -> GLAccount:
    return GLAccount.objects.create(
        dealership=dealership,
        code=code,
        name=name,
        account_type=atype,
    )


class TrialBalanceEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client_ = _sm_client()

    def test_get_empty_returns_200_balanced(self) -> None:
        response = self.client_.get(reverse(TB_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["trial_balance"]
        self.assertEqual(body["rows"], [])
        self.assertEqual(body["total_debits"], "0.00")
        self.assertEqual(body["total_credits"], "0.00")
        self.assertTrue(body["is_balanced"])

    def test_get_with_postings_returns_rows(self) -> None:
        cash = _acct(
            self.dealership,
            "TBEP-100000",
            "Cash",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "TBEP-400000",
            "Revenue",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        post_journal_entry(
            dealership=self.dealership,
            description="Sale",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("250.00")),
                JournalLineInput(account=rev, credit=Decimal("250.00")),
            ],
        )
        response = self.client_.get(reverse(TB_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["trial_balance"]
        self.assertEqual(body["total_debits"], "250.00")
        self.assertEqual(body["total_credits"], "250.00")
        self.assertTrue(body["is_balanced"])
        codes = {r["account_code"] for r in body["rows"]}
        self.assertIn("TBEP-100000", codes)
        self.assertIn("TBEP-400000", codes)

    def test_as_of_query_parameter_respected(self) -> None:
        cash = _acct(
            self.dealership,
            "TBEP-100001",
            "Cash",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "TBEP-400001",
            "Revenue",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        past = timezone.now() - dt.timedelta(days=10)
        future = timezone.now() + dt.timedelta(days=10)
        post_journal_entry(
            dealership=self.dealership,
            description="Old",
            posted_at=past,
            lines=[
                JournalLineInput(account=cash, debit=Decimal("10.00")),
                JournalLineInput(account=rev, credit=Decimal("10.00")),
            ],
        )
        post_journal_entry(
            dealership=self.dealership,
            description="New",
            posted_at=future,
            lines=[
                JournalLineInput(account=cash, debit=Decimal("500.00")),
                JournalLineInput(account=rev, credit=Decimal("500.00")),
            ],
        )
        response = self.client_.get(
            reverse(TB_URL),
            data={"as_of": timezone.now().isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["trial_balance"]
        # Only the past posting should count.
        self.assertEqual(body["total_debits"], "10.00")

    def test_invalid_as_of_returns_400(self) -> None:
        response = self.client_.get(reverse(TB_URL), data={"as_of": "not-a-date"})
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self) -> None:
        response = APIClient().get(reverse(TB_URL))
        self.assertIn(response.status_code, {401, 403})

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="tb-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        advisor = authenticated_client(user)
        response = advisor.get(reverse(TB_URL))
        self.assertEqual(response.status_code, 403)

    def test_scoped_to_calling_dealership(self) -> None:
        other = Dealership.objects.create(slug="tb-other-ep", name="Other")
        seed_default_coa(other)
        # Post in the OTHER tenant.
        other_cash = _acct(
            other, "TBEP-100002", "Other Cash", GL_ACCOUNT_TYPE_ASSET
        )
        other_rev = _acct(
            other, "TBEP-400002", "Other Rev", GL_ACCOUNT_TYPE_REVENUE
        )
        post_journal_entry(
            dealership=other,
            description="Other tenant sale",
            lines=[
                JournalLineInput(account=other_cash, debit=Decimal("999.00")),
                JournalLineInput(account=other_rev, credit=Decimal("999.00")),
            ],
        )
        # Default-tenant caller should not see the OTHER tenant's postings.
        response = self.client_.get(reverse(TB_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["trial_balance"]
        self.assertEqual(body["total_debits"], "0.00")

    def test_row_shape_projects_all_expected_fields(self) -> None:
        cash = _acct(
            self.dealership,
            "TBEP-100003",
            "Cash Shape",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "TBEP-400003",
            "Rev Shape",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        post_journal_entry(
            dealership=self.dealership,
            description="Shape",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("42.00")),
                JournalLineInput(account=rev, credit=Decimal("42.00")),
            ],
        )
        response = self.client_.get(reverse(TB_URL))
        body = response.json()["trial_balance"]
        row = next(r for r in body["rows"] if r["account_code"] == "TBEP-100003")
        self.assertEqual(
            set(row.keys()),
            {
                "account_code",
                "account_name",
                "account_type",
                "debit_total",
                "credit_total",
                "natural_balance",
            },
        )
        self.assertEqual(row["account_type"], "asset")
        self.assertEqual(row["natural_balance"], "42.00")
