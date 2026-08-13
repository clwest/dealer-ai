"""Milestone 13 · Increment 1 (SESSION_129) — accounting endpoint tests."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
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
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-journal-entry-create"
REVERSE = "dealer_ai:admin-journal-entry-reverse"
RETRIEVE = "dealer_ai:admin-journal-entry-retrieve"


def _post(client, url, body):
    return client.post(url, body, format="json")


def _sm_client(username: str = "sm-user") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_SALES_MANAGER)
    return authenticated_client(user)


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    cash = GLAccount.objects.create(
        dealership=dealership,
        code="EP-100000",
        name="Cash",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    revenue = GLAccount.objects.create(
        dealership=dealership,
        code="EP-400000",
        name="Revenue",
        account_type=GL_ACCOUNT_TYPE_REVENUE,
    )
    return cash, revenue


class JournalEntryCreateEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash, self.revenue = _make_accounts(self.dealership)
        self.client_ = _sm_client()

    def test_post_happy_path_201(self) -> None:
        response = _post(
            self.client_,
            reverse(CREATE),
            {
                "description": "Test posting",
                "lines": [
                    {"account_id": self.cash.pk, "debit": "500.00"},
                    {
                        "account_id": self.revenue.pk,
                        "credit": "500.00",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["journal_entry"]
        self.assertEqual(len(body["lines"]), 2)
        self.assertEqual(body["description"], "Test posting")

    def test_post_unbalanced_400(self) -> None:
        response = _post(
            self.client_,
            reverse(CREATE),
            {
                "description": "Bad",
                "lines": [
                    {"account_id": self.cash.pk, "debit": "500.00"},
                    {
                        "account_id": self.revenue.pk,
                        "credit": "400.00",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_post_missing_account_404(self) -> None:
        response = _post(
            self.client_,
            reverse(CREATE),
            {
                "description": "Bogus account",
                "lines": [
                    {"account_id": 999_999, "debit": "10.00"},
                    {
                        "account_id": self.revenue.pk,
                        "credit": "10.00",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_post_cross_tenant_account_404(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-ep-a", name="Other"
        )
        other_account = GLAccount.objects.create(
            dealership=other,
            code="EP-999000",
            name="Other tenant",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        response = _post(
            self.client_,
            reverse(CREATE),
            {
                "description": "Cross-tenant",
                "lines": [
                    {"account_id": other_account.pk, "debit": "10.00"},
                    {
                        "account_id": self.revenue.pk,
                        "credit": "10.00",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_post_requires_authentication(self) -> None:
        response = _post(
            APIClient(),
            reverse(CREATE),
            {"description": "unauth", "lines": []},
        )
        self.assertIn(response.status_code, {401, 403})

    def test_post_advisor_role_forbidden(self) -> None:
        user = make_user(username="ep-advisor")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        advisor = authenticated_client(user)
        response = _post(
            advisor,
            reverse(CREATE),
            {
                "description": "Advisor try",
                "lines": [
                    {"account_id": self.cash.pk, "debit": "1.00"},
                    {
                        "account_id": self.revenue.pk,
                        "credit": "1.00",
                    },
                ],
            },
        )
        self.assertEqual(response.status_code, 403)


class JournalEntryReverseEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash, self.revenue = _make_accounts(self.dealership)
        self.client_ = _sm_client(username="ep-reverse-sm")
        self.entry = post_journal_entry(
            dealership=self.dealership,
            description="Reversible",
            lines=[
                JournalLineInput(
                    account=self.cash, debit=Decimal("100.00")
                ),
                JournalLineInput(
                    account=self.revenue, credit=Decimal("100.00")
                ),
            ],
        )

    def test_reverse_happy_path_201(self) -> None:
        response = _post(
            self.client_,
            reverse(REVERSE, args=[self.entry.pk]),
            {"reason": "Duplicate posting"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["journal_entry"]
        self.assertEqual(body["reverses_id"], self.entry.pk)
        self.assertEqual(body["reason"], "Duplicate posting")

    def test_reverse_missing_pk_404(self) -> None:
        response = _post(
            self.client_,
            reverse(REVERSE, args=[999_999]),
            {"reason": "does not exist"},
        )
        self.assertEqual(response.status_code, 404)

    def test_reverse_blank_reason_400(self) -> None:
        # DRF serializer rejects whitespace-only reason at the input
        # layer (400) before the service-layer
        # :class:`ImmutableJournalEntryError` (409) can raise. The 409
        # path is exercised directly via the service-level test at
        # ``test_m131_accounting_service.ReverseJournalEntryTests.
        # test_empty_reason_rejected`` — belt (DRF) + suspenders
        # (service verb).
        response = _post(
            self.client_,
            reverse(REVERSE, args=[self.entry.pk]),
            {"reason": "   "},
        )
        self.assertEqual(response.status_code, 400)

    def test_reverse_missing_reason_field_400(self) -> None:
        response = _post(
            self.client_,
            reverse(REVERSE, args=[self.entry.pk]),
            {},
        )
        self.assertEqual(response.status_code, 400)

    def test_reverse_duplicate_direct_reversal_409(self) -> None:
        # Regression: the same original may be directly reversed at
        # most once. Service-layer :class:`AlreadyReversedError` maps
        # to 409 CONFLICT (state error, not input error).
        first = _post(
            self.client_,
            reverse(REVERSE, args=[self.entry.pk]),
            {"reason": "First reversal"},
        )
        self.assertEqual(first.status_code, 201, first.content)

        second = _post(
            self.client_,
            reverse(REVERSE, args=[self.entry.pk]),
            {"reason": "Second direct reversal — should be rejected"},
        )
        self.assertEqual(second.status_code, 409, second.content)
        self.assertIn(
            "already been reversed", second.json()["detail"]
        )


class JournalEntryRetrieveEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash, self.revenue = _make_accounts(self.dealership)
        self.client_ = _sm_client(username="ep-get-sm")
        self.entry = post_journal_entry(
            dealership=self.dealership,
            description="Retrievable",
            lines=[
                JournalLineInput(
                    account=self.cash, debit=Decimal("1.00")
                ),
                JournalLineInput(
                    account=self.revenue, credit=Decimal("1.00")
                ),
            ],
        )

    def test_get_happy_path_200(self) -> None:
        response = self.client_.get(reverse(RETRIEVE, args=[self.entry.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journal_entry"]
        self.assertEqual(body["id"], self.entry.pk)
        self.assertEqual(len(body["lines"]), 2)

    def test_get_missing_pk_404(self) -> None:
        response = self.client_.get(reverse(RETRIEVE, args=[999_999]))
        self.assertEqual(response.status_code, 404)
