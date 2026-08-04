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

    # ------------------------------------------------------------------
    # M29 (SESSION_198) — variable-amount endpoint coverage
    # ------------------------------------------------------------------

    def _variable_body(self, name: str = "Monthly depreciation") -> dict:
        """Fully-variable template body (both lines have amount=null)."""
        return {
            "name": name,
            "description": "Depreciation per asset per period",
            "lines": [
                {
                    "account_id": self.rent.pk,
                    "side": "debit",
                    "amount": None,
                },
                {
                    "account_id": self.bank.pk,
                    "side": "credit",
                    "amount": None,
                },
            ],
        }

    def test_post_m29_fully_variable_returns_201(self) -> None:
        response = self.client_.post(
            reverse(LIST_OR_CREATE),
            self._variable_body(),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["journal_entry_template"]
        self.assertEqual(body["line_count"], 2)
        self.assertEqual(body["lines"][0]["amount"], None)
        self.assertEqual(body["lines"][1]["amount"], None)
        self.assertEqual(body["lines"][0]["side"], "debit")
        self.assertEqual(body["lines"][1]["side"], "credit")

    def test_post_m29_mixed_populated_and_variable_returns_201(self) -> None:
        # Two-line mix: fixed $25 debit + $25 credit balances the
        # populated portion; two additional variable lines complete the
        # 4-line template (utility base fee + variable usage).
        base_debit = GLAccount.objects.create(
            dealership=self.dealership,
            code="EP29-671001",
            name="Utility Base Fee",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        base_credit = GLAccount.objects.create(
            dealership=self.dealership,
            code="EP29-110001",
            name="Utility Bank",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        body = {
            "name": "Utilities monthly",
            "description": "Fixed base + variable usage",
            "lines": [
                {
                    "account_id": self.rent.pk,
                    "side": "debit",
                    "amount": "25.00",
                },
                {
                    "account_id": self.bank.pk,
                    "side": "credit",
                    "amount": "25.00",
                },
                {
                    "account_id": base_debit.pk,
                    "side": "debit",
                    "amount": None,
                },
                {
                    "account_id": base_credit.pk,
                    "side": "credit",
                    "amount": None,
                },
            ],
        }
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        body_out = response.json()["journal_entry_template"]
        self.assertEqual(body_out["line_count"], 4)
        amounts = [line["amount"] for line in body_out["lines"]]
        self.assertIn("25.00", amounts)
        self.assertIn(None, amounts)

    def test_post_m29_mixed_with_imbalanced_populated_returns_400(
        self,
    ) -> None:
        body = {
            "name": "One-sided fixed",
            "description": "Fixed debit only — populated portion unbalanced",
            "lines": [
                {
                    "account_id": self.rent.pk,
                    "side": "debit",
                    "amount": "500.00",
                },
                {
                    "account_id": self.bank.pk,
                    "side": "credit",
                    "amount": None,
                },
            ],
        }
        response = self.client_.post(
            reverse(LIST_OR_CREATE), body, format="json"
        )
        self.assertEqual(response.status_code, 400, response.content)

    def test_get_m29_projection_returns_null_amount_for_variable_lines(
        self,
    ) -> None:
        create_response = self.client_.post(
            reverse(LIST_OR_CREATE),
            self._variable_body(name="Projection variable"),
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        list_response = self.client_.get(reverse(LIST_OR_CREATE))
        self.assertEqual(list_response.status_code, 200)
        templates = list_response.json()["journal_entry_templates"][
            "templates"
        ]
        variable = next(
            t for t in templates if t["name"] == "Projection variable"
        )
        for line in variable["lines"]:
            self.assertIsNone(line["amount"])

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
