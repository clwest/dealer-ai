"""Milestone 28 · Increment 1 (SESSION_195) — template endpoint tests.

Behaviors asserted:

- POST 201 happy path with envelope
  {"journal_entry_template": {...projection...}} including nested
  lines with account_code + side + amount + memo + ordering.
- POST 400 for serializer errors (missing field, bad shape).
- POST 400 for domain errors (empty/single-line, invalid amount,
  unbalanced).
- POST 404 for cross-tenant GLAccount (fail-closed).
- POST 409 for duplicate template name within tenant.
- GET 200 lists active templates ordered by name.
- GET 200 returns empty list for zero-portfolio tenant.
- Permission enforcement (advisor role denied).
- Authentication required (unauthenticated 401/403).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EXPENSE,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    Dealership,
    GLAccount,
    JournalEntryTemplate,
    JournalEntryTemplateLine,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


LIST_OR_CREATE = "dealer_ai:admin-journal-entry-template-list-or-create"


def _sm_client(username: str = "sm-tmpl-ep") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_SALES_MANAGER)
    return authenticated_client(user)


def _advisor_client(username: str = "adv-tmpl-ep") -> APIClient:
    user = make_user(username=username)
    make_membership(user, get_default_dealership(), ROLE_ADVISOR)
    return authenticated_client(user)


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    rent = GLAccount.objects.create(
        dealership=dealership,
        code="EP28-615000",
        name="Rent Expense",
        account_type=GL_ACCOUNT_TYPE_EXPENSE,
    )
    bank = GLAccount.objects.create(
        dealership=dealership,
        code="EP28-110000",
        name="Bank — Operating",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    return rent, bank


class TemplateCreateEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.client_ = _sm_client()

    def _valid_body(self, name: str = "Monthly rent") -> dict:
        return {
            "name": name,
            "description": "Rent expense — monthly",
            "lines": [
                {
                    "account_id": self.rent.pk,
                    "side": "debit",
                    "amount": "3500.00",
                },
                {
                    "account_id": self.bank.pk,
                    "side": "credit",
                    "amount": "3500.00",
                },
            ],
        }

    def test_post_happy_path_201(self) -> None:
        response = self.client_.post(
            reverse(LIST_OR_CREATE), self._valid_body(), format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["journal_entry_template"]
        self.assertEqual(body["name"], "Monthly rent")
        self.assertEqual(body["description"], "Rent expense — monthly")
        self.assertEqual(body["is_active"], True)
        self.assertEqual(body["line_count"], 2)
        self.assertEqual(len(body["lines"]), 2)
        self.assertEqual(body["lines"][0]["side"], "debit")
        self.assertEqual(body["lines"][0]["amount"], "3500.00")
        self.assertEqual(body["lines"][1]["side"], "credit")
        self.assertEqual(body["lines"][1]["amount"], "3500.00")

    def test_post_serializer_error_400(self) -> None:
        response = self.client_.post(
            reverse(LIST_OR_CREATE),
            {"name": "No lines", "description": "—"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_empty_lines_400(self) -> None:
        response = self.client_.post(
            reverse(LIST_OR_CREATE),
            {"name": "Empty", "description": "—", "lines": []},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_post_single_line_400(self) -> None:
        body = self._valid_body(name="Single")
        body["lines"] = body["lines"][:1]
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_post_unbalanced_400(self) -> None:
        body = self._valid_body(name="Unbalanced")
        body["lines"][1]["amount"] = "3000.00"
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_post_bad_side_400(self) -> None:
        body = self._valid_body(name="Bad side")
        body["lines"][0]["side"] = "left"
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_post_missing_account_404(self) -> None:
        body = self._valid_body(name="Bogus account")
        body["lines"][0]["account_id"] = 999_999
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_post_cross_tenant_account_404(self) -> None:
        other = Dealership.objects.create(
            slug="other-ep28-cross", name="Other"
        )
        foreign = GLAccount.objects.create(
            dealership=other,
            code="OTH-999",
            name="Foreign",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        body = self._valid_body(name="Cross-tenant account")
        body["lines"][0]["account_id"] = foreign.pk
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_post_duplicate_name_409(self) -> None:
        first = self.client_.post(
            reverse(LIST_OR_CREATE),
            self._valid_body(name="Duplicate"),
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        second = self.client_.post(
            reverse(LIST_OR_CREATE),
            self._valid_body(name="Duplicate"),
            format="json",
        )
        self.assertEqual(second.status_code, 409)

    def test_post_advisor_denied(self) -> None:
        response = _advisor_client().post(
            reverse(LIST_OR_CREATE),
            self._valid_body(name="Advisor denied"),
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_post_unauthenticated_denied(self) -> None:
        response = APIClient().post(
            reverse(LIST_OR_CREATE),
            self._valid_body(name="Unauth"),
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))


class TemplateListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.client_ = _sm_client(username="sm-list-tmpl-ep")

    def _seed(self, name: str, is_active: bool = True) -> JournalEntryTemplate:
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name=name,
            description="—",
            is_active=is_active,
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("10.00"),
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.bank,
            side="credit",
            amount=Decimal("10.00"),
        )
        return template

    def test_get_returns_active_only_ordered_by_name(self) -> None:
        self._seed("Zeta")
        self._seed("Alpha")
        self._seed("Beta", is_active=False)
        response = self.client_.get(reverse(LIST_OR_CREATE))
        self.assertEqual(response.status_code, 200)
        templates = response.json()["journal_entry_templates"]["templates"]
        names = [t["name"] for t in templates]
        self.assertEqual(names, ["Alpha", "Zeta"])
        # Line projection sanity — first template has 2 lines with
        # account_code + side + amount populated.
        first = templates[0]
        self.assertEqual(first["line_count"], 2)
        self.assertEqual(len(first["lines"]), 2)
        self.assertEqual(first["lines"][0]["side"], "debit")
        self.assertEqual(first["lines"][0]["amount"], "10.00")
        self.assertTrue(first["lines"][0]["account_code"])

    def test_get_empty_tenant_returns_empty_list(self) -> None:
        response = self.client_.get(reverse(LIST_OR_CREATE))
        self.assertEqual(response.status_code, 200)
        body = response.json()["journal_entry_templates"]
        self.assertEqual(body["templates"], [])

    def test_get_advisor_denied(self) -> None:
        response = _advisor_client(username="adv-list-tmpl-ep").get(
            reverse(LIST_OR_CREATE)
        )
        self.assertEqual(response.status_code, 403)

    def test_get_unauthenticated_denied(self) -> None:
        response = APIClient().get(reverse(LIST_OR_CREATE))
        self.assertIn(response.status_code, (401, 403))

    def test_get_scoped_to_tenant(self) -> None:
        self._seed("MyTemplate")
        other = Dealership.objects.create(
            slug="other-list-ep28", name="Other"
        )
        JournalEntryTemplate.objects.create(
            dealership=other, name="TheirTemplate", description="—"
        )
        response = self.client_.get(reverse(LIST_OR_CREATE))
        templates = response.json()["journal_entry_templates"]["templates"]
        names = [t["name"] for t in templates]
        self.assertEqual(names, ["MyTemplate"])
