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


# ======================================================================
# Milestone 30 · Increment 1 (SESSION_201) — template detail endpoint.
# ======================================================================
#
# Per MILESTONE_30_PLANNING.md §5.b D1 + D6. The new endpoint
# ``admin/accounting/journal-entry-templates/<int:pk>/`` supports
# PATCH (full-replace edit) + DELETE (soft — sets is_active=False).
# No GET at M30 — the edit-mode dialog populates from the row
# already loaded via the list response.

DETAIL = "dealer_ai:admin-journal-entry-template-detail"


class TemplateDetailEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.client_ = _sm_client(username="sm-detail-tmpl-ep")
        # Seed a template to edit / delete.
        create_response = self.client_.post(
            reverse(LIST_OR_CREATE),
            {
                "name": "Detail-target rent",
                "description": "Original",
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
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.template_id = create_response.json()[
            "journal_entry_template"
        ]["id"]

    def _valid_patch_body(self, name: str = "Detail-target rent (edited)") -> dict:
        return {
            "name": name,
            "description": "Edited",
            "lines": [
                {
                    "account_id": self.rent.pk,
                    "side": "debit",
                    "amount": "4000.00",
                },
                {
                    "account_id": self.bank.pk,
                    "side": "credit",
                    "amount": "4000.00",
                },
            ],
        }

    def test_patch_returns_200_with_updated_projection(self) -> None:
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            self._valid_patch_body(),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["journal_entry_template"]
        self.assertEqual(body["id"], self.template_id)
        self.assertEqual(body["name"], "Detail-target rent (edited)")
        self.assertEqual(body["description"], "Edited")
        self.assertEqual(body["is_active"], True)
        self.assertEqual(body["lines"][0]["amount"], "4000.00")

    def test_patch_full_replace_lines(self) -> None:
        third = GLAccount.objects.create(
            dealership=self.dealership,
            code="EP30-671000",
            name="Utilities",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        body = {
            "name": "Detail-target rent",
            "description": "Now three lines",
            "lines": [
                {
                    "account_id": self.rent.pk,
                    "side": "debit",
                    "amount": "3500.00",
                },
                {
                    "account_id": third.pk,
                    "side": "debit",
                    "amount": "500.00",
                },
                {
                    "account_id": self.bank.pk,
                    "side": "credit",
                    "amount": "4000.00",
                },
            ],
        }
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            body,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body_out = response.json()["journal_entry_template"]
        self.assertEqual(body_out["line_count"], 3)

    def test_patch_missing_pk_returns_404(self) -> None:
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": 999_999}),
            self._valid_patch_body(),
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_patch_cross_tenant_returns_404(self) -> None:
        # Create a template owned by another tenant; the current
        # sales-manager client is scoped to get_default_dealership().
        other = Dealership.objects.create(
            slug="other-detail-patch", name="Other tenant"
        )
        other_template = JournalEntryTemplate.objects.create(
            dealership=other, name="Foreign", description="—"
        )
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": other_template.pk}),
            self._valid_patch_body(),
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_patch_invalid_payload_returns_400(self) -> None:
        # Populated portion doesn't balance.
        body = self._valid_patch_body()
        body["lines"][1]["amount"] = "3999.99"
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            body,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_duplicate_name_returns_409(self) -> None:
        # Seed another template with a name that PATCH will try to
        # collide with.
        second = self.client_.post(
            reverse(LIST_OR_CREATE),
            {
                "name": "Second template",
                "description": "—",
                "lines": [
                    {
                        "account_id": self.rent.pk,
                        "side": "debit",
                        "amount": "1.00",
                    },
                    {
                        "account_id": self.bank.pk,
                        "side": "credit",
                        "amount": "1.00",
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(second.status_code, 201)
        # Try to rename the original template to "Second template".
        body = self._valid_patch_body(name="Second template")
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            body,
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_patch_silently_ignores_is_active_in_body(self) -> None:
        """PATCH must not allow ``is_active`` mutation via body per
        M30.0 §5.b D5. Activation flows through DELETE (soft) or a
        future Restore verb only. Body key silently dropped."""
        body = self._valid_patch_body()
        body["is_active"] = False  # sneaky
        response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            body,
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        # is_active remains True.
        self.assertTrue(
            response.json()["journal_entry_template"]["is_active"]
        )

    def test_delete_returns_204(self) -> None:
        response = self.client_.delete(
            reverse(DETAIL, kwargs={"pk": self.template_id})
        )
        self.assertEqual(response.status_code, 204)
        # Template disappears from active-only list.
        list_response = self.client_.get(reverse(LIST_OR_CREATE))
        templates = list_response.json()["journal_entry_templates"][
            "templates"
        ]
        ids = [t["id"] for t in templates]
        self.assertNotIn(self.template_id, ids)

    def test_delete_missing_pk_returns_404(self) -> None:
        response = self.client_.delete(
            reverse(DETAIL, kwargs={"pk": 999_999})
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_cross_tenant_returns_404(self) -> None:
        other = Dealership.objects.create(
            slug="other-detail-delete", name="Other tenant"
        )
        other_template = JournalEntryTemplate.objects.create(
            dealership=other, name="Foreign", description="—"
        )
        response = self.client_.delete(
            reverse(DETAIL, kwargs={"pk": other_template.pk})
        )
        self.assertEqual(response.status_code, 404)
        # Other tenant's template still active.
        other_template.refresh_from_db()
        self.assertTrue(other_template.is_active)

    def test_delete_already_inactive_returns_204_idempotent(self) -> None:
        # First DELETE — soft-hides.
        first = self.client_.delete(
            reverse(DETAIL, kwargs={"pk": self.template_id})
        )
        self.assertEqual(first.status_code, 204)
        # Second DELETE — still 204.
        second = self.client_.delete(
            reverse(DETAIL, kwargs={"pk": self.template_id})
        )
        self.assertEqual(second.status_code, 204)

    def test_patch_advisor_denied(self) -> None:
        response = _advisor_client(username="adv-detail-tmpl").patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            self._valid_patch_body(),
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_advisor_denied(self) -> None:
        response = _advisor_client(username="adv-detail-tmpl-del").delete(
            reverse(DETAIL, kwargs={"pk": self.template_id})
        )
        self.assertEqual(response.status_code, 403)

    def test_patch_unauthenticated_denied(self) -> None:
        response = APIClient().patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            self._valid_patch_body(),
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_delete_unauthenticated_denied(self) -> None:
        response = APIClient().delete(
            reverse(DETAIL, kwargs={"pk": self.template_id})
        )
        self.assertIn(response.status_code, (401, 403))


# ======================================================================
# Milestone 31 · Increment 1 (SESSION_204) — template restore endpoint
# + list ?include_inactive fail-closed parsing.
# ======================================================================
#
# Per MILESTONE_31_PLANNING.md §5.b D1–D3 + §5.e M31.1 test spec.
# The new endpoint ``admin/accounting/journal-entry-templates/<int:pk>/restore/``
# supports POST (reactivate a soft-hidden template by setting
# is_active=True; idempotent — repeat POST on an already-active row
# returns 200 without state change and without advancing updated_at).
# The existing list endpoint gains ``?include_inactive=true`` query
# parsing (fail-closed — only literal "true" case-insensitive enables
# inactive rows). Reuses ``_M131_PERMS`` (zero-drift permission-class
# streak preserved at 31 → 32 intended at M31.1).

RESTORE = "dealer_ai:admin-journal-entry-template-restore"


class TemplateRestoreEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.client_ = _sm_client(username="sm-restore-tmpl-ep")
        # Seed a template and deactivate it via the shipped M30.1
        # DELETE verb so the Restore fixture reflects the real
        # operator lifecycle precondition (soft-hidden row).
        create_response = self.client_.post(
            reverse(LIST_OR_CREATE),
            {
                "name": "Restore-target rent",
                "description": "Original",
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
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.template_id = create_response.json()[
            "journal_entry_template"
        ]["id"]
        # Deactivate.
        delete_response = self.client_.delete(
            reverse(DETAIL, kwargs={"pk": self.template_id})
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_restore_returns_200_with_projected_row(self) -> None:
        response = self.client_.post(
            reverse(RESTORE, kwargs={"pk": self.template_id})
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["journal_entry_template"]
        self.assertEqual(body["id"], self.template_id)
        self.assertTrue(body["is_active"])
        self.assertEqual(body["name"], "Restore-target rent")
        # After Restore, the template re-appears in the default
        # active-only list.
        list_response = self.client_.get(reverse(LIST_OR_CREATE))
        ids = [
            t["id"]
            for t in list_response.json()["journal_entry_templates"][
                "templates"
            ]
        ]
        self.assertIn(self.template_id, ids)

    def test_restore_idempotent_already_active_returns_200(self) -> None:
        # First POST: state change (False → True).
        first = self.client_.post(
            reverse(RESTORE, kwargs={"pk": self.template_id})
        )
        self.assertEqual(first.status_code, 200)
        # Second POST: no state change; still 200.
        second = self.client_.post(
            reverse(RESTORE, kwargs={"pk": self.template_id})
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(
            second.json()["journal_entry_template"]["is_active"]
        )

    def test_restore_missing_pk_returns_404(self) -> None:
        response = self.client_.post(
            reverse(RESTORE, kwargs={"pk": 999_999})
        )
        self.assertEqual(response.status_code, 404)

    def test_restore_cross_tenant_returns_404(self) -> None:
        other = Dealership.objects.create(
            slug="other-restore-ep", name="Other tenant"
        )
        foreign = JournalEntryTemplate.objects.create(
            dealership=other,
            name="Foreign",
            description="—",
            is_active=False,
        )
        response = self.client_.post(
            reverse(RESTORE, kwargs={"pk": foreign.pk})
        )
        self.assertEqual(response.status_code, 404)
        # Foreign row still soft-hidden.
        foreign.refresh_from_db()
        self.assertFalse(foreign.is_active)

    def test_restore_advisor_denied(self) -> None:
        response = _advisor_client(
            username="adv-restore-tmpl-ep"
        ).post(reverse(RESTORE, kwargs={"pk": self.template_id}))
        self.assertEqual(response.status_code, 403)
        # Underlying row untouched.
        template = JournalEntryTemplate.objects.get(pk=self.template_id)
        self.assertFalse(template.is_active)

    def test_restore_unauthenticated_denied(self) -> None:
        response = APIClient().post(
            reverse(RESTORE, kwargs={"pk": self.template_id})
        )
        self.assertIn(response.status_code, (401, 403))

    def test_patch_still_cannot_mutate_is_active_after_m31(self) -> None:
        """M30.2 lesson (w) durable-asymmetry re-assertion at M31.1.

        Restore is a dedicated verb — PATCH must still silently drop
        ``is_active`` from the body even after Restore is available.
        Regression guard: prevents a future change from re-adding
        ``is_active`` to the update serializer as a shortcut."""
        # First Restore so the row is active + PATCH-editable.
        self.client_.post(reverse(RESTORE, kwargs={"pk": self.template_id}))
        # Attempt PATCH with is_active=False in body.
        body = {
            "name": "Restore-target rent",
            "description": "Edit attempted with sneaky is_active",
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
            "is_active": False,  # sneaky
        }
        patch_response = self.client_.patch(
            reverse(DETAIL, kwargs={"pk": self.template_id}),
            body,
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertTrue(
            patch_response.json()["journal_entry_template"]["is_active"]
        )


class TemplateListIncludeInactiveEndpointTests(TestCase):
    """M31.1 — fail-closed ``?include_inactive`` query-param parsing.

    Per §5.b D3: only literal ``true`` case-insensitive enables inactive
    rows. Every other value (``1``, ``yes``, empty, malformed, missing)
    resolves to active-only default so inactive templates never mix
    into the default active list.
    """

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.client_ = _sm_client(username="sm-listinactive-tmpl-ep")
        # Seed one active + one soft-hidden template.
        self.active = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Alpha (active)",
            description="—",
            is_active=True,
        )
        self.inactive = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Zeta (inactive)",
            description="—",
            is_active=False,
        )
        for template in (self.active, self.inactive):
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

    def _get_names(self, url: str) -> list[str]:
        response = self.client_.get(url)
        self.assertEqual(response.status_code, 200)
        return [
            t["name"]
            for t in response.json()["journal_entry_templates"][
                "templates"
            ]
        ]

    # ------------------------------------------------------------------
    # Opt-in — accepted spellings (case-insensitive literal "true")
    # ------------------------------------------------------------------

    def test_include_inactive_true_returns_both(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=true"
        )
        self.assertEqual(names, ["Alpha (active)", "Zeta (inactive)"])

    def test_include_inactive_TRUE_uppercase_returns_both(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=TRUE"
        )
        self.assertEqual(names, ["Alpha (active)", "Zeta (inactive)"])

    def test_include_inactive_True_titlecase_returns_both(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=True"
        )
        self.assertEqual(names, ["Alpha (active)", "Zeta (inactive)"])

    # ------------------------------------------------------------------
    # Fail-closed — every other value returns active-only
    # ------------------------------------------------------------------

    def test_include_inactive_missing_returns_active_only(self) -> None:
        names = self._get_names(reverse(LIST_OR_CREATE))
        self.assertEqual(names, ["Alpha (active)"])

    def test_include_inactive_false_returns_active_only(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=false"
        )
        self.assertEqual(names, ["Alpha (active)"])

    def test_include_inactive_1_returns_active_only(self) -> None:
        """``1`` is a common truthy sentinel; fail-closed rejects it."""
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=1"
        )
        self.assertEqual(names, ["Alpha (active)"])

    def test_include_inactive_yes_returns_active_only(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=yes"
        )
        self.assertEqual(names, ["Alpha (active)"])

    def test_include_inactive_empty_returns_active_only(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive="
        )
        self.assertEqual(names, ["Alpha (active)"])

    def test_include_inactive_malformed_returns_active_only(self) -> None:
        names = self._get_names(
            reverse(LIST_OR_CREATE) + "?include_inactive=maybe"
        )
        self.assertEqual(names, ["Alpha (active)"])
