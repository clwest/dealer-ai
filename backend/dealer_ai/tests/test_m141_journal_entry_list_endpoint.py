"""Milestone 14 · Increment 1 (SESSION_134) — journal-entry list endpoint tests.

Covers ``GET admin/accounting/journal-entries/list/`` per
MILESTONE_14_PLANNING.md §7 M14.1.
"""

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


LIST_URL = "dealer_ai:admin-journal-entry-list"


def _sm_client(username: str = "m141ep-sm") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_SALES_MANAGER)
    return authenticated_client(user)


def _acct(dealership: Dealership, code: str, atype: str) -> GLAccount:
    return GLAccount.objects.create(
        dealership=dealership,
        code=code,
        name=f"Account {code}",
        account_type=atype,
    )


class JournalEntryListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash = _acct(self.dealership, "M141EP-100000", GL_ACCOUNT_TYPE_ASSET)
        self.rev = _acct(self.dealership, "M141EP-400000", GL_ACCOUNT_TYPE_REVENUE)
        self.client_ = _sm_client()

    def _post(self, amount: Decimal, when=None):
        return post_journal_entry(
            dealership=self.dealership,
            description=f"Endpoint post {amount}",
            posted_at=when,
            lines=[
                JournalLineInput(account=self.cash, debit=amount),
                JournalLineInput(account=self.rev, credit=amount),
            ],
        )

    def test_get_empty_returns_200_with_empty_entries(self) -> None:
        response = self.client_.get(reverse(LIST_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journal_entries"]
        self.assertEqual(body["entries"], [])
        self.assertEqual(body["total_count"], 0)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], 25)

    def test_get_with_postings_returns_projected_rows(self) -> None:
        entry = self._post(Decimal("100.00"))
        response = self.client_.get(reverse(LIST_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journal_entries"]
        self.assertEqual(body["total_count"], 1)
        row = body["entries"][0]
        self.assertEqual(row["id"], entry.pk)
        self.assertEqual(row["description"], "Endpoint post 100.00")
        self.assertEqual(row["total_debit"], "100.00")  # Decimal-as-string.
        self.assertIsNone(row["reverses_id"])
        self.assertEqual(row["reason"], "")

    def test_pagination_via_query_params(self) -> None:
        now = timezone.now()
        for i in range(1, 6):
            self._post(Decimal(f"{i}.00"), when=now - dt.timedelta(days=i))
        response = self.client_.get(
            reverse(LIST_URL), data={"page": 2, "page_size": 2}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["journal_entries"]
        self.assertEqual(body["total_count"], 5)
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 2)
        self.assertEqual(len(body["entries"]), 2)

    def test_invalid_page_returns_400(self) -> None:
        response = self.client_.get(reverse(LIST_URL), data={"page": 0})
        self.assertEqual(response.status_code, 400)

    def test_invalid_page_size_returns_400(self) -> None:
        # Cap is 100 — 200 must reject.
        response = self.client_.get(reverse(LIST_URL), data={"page_size": 200})
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self) -> None:
        response = APIClient().get(reverse(LIST_URL))
        self.assertIn(response.status_code, {401, 403})

    def test_advisor_role_forbidden(self) -> None:
        user = make_user(username="m141ep-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        advisor = authenticated_client(user)
        response = advisor.get(reverse(LIST_URL))
        self.assertEqual(response.status_code, 403)

    def test_scoped_to_calling_dealership(self) -> None:
        other = Dealership.objects.create(slug="m141ep-other", name="Other")
        seed_default_coa(other)
        other_cash = _acct(other, "M141EP-OTHER-100000", GL_ACCOUNT_TYPE_ASSET)
        other_rev = _acct(other, "M141EP-OTHER-400000", GL_ACCOUNT_TYPE_REVENUE)
        post_journal_entry(
            dealership=other,
            description="Other tenant",
            lines=[
                JournalLineInput(account=other_cash, debit=Decimal("500.00")),
                JournalLineInput(account=other_rev, credit=Decimal("500.00")),
            ],
        )
        response = self.client_.get(reverse(LIST_URL))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journal_entries"]
        # Default-tenant caller sees no OTHER-tenant postings.
        self.assertEqual(body["total_count"], 0)

    def test_row_shape_projects_all_expected_fields(self) -> None:
        self._post(Decimal("7.00"))
        response = self.client_.get(reverse(LIST_URL))
        row = response.json()["journal_entries"]["entries"][0]
        self.assertEqual(
            set(row.keys()),
            {
                "id",
                "description",
                "posted_at",
                "posted_by_user_id",
                "posted_by_username",
                "reverses_id",
                "reason",
                "total_debit",
            },
        )
