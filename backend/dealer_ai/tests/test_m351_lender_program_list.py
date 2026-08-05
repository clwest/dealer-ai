"""Milestone 35 · Increment 1 (SESSION_217) — LenderProgram list
endpoint tests.

Locks the M35.1 D4 backend surface per
``MILESTONE_35_PLANNING.md`` §5.b D4 + §5.e M35.1.

One new endpoint gated on
``IsFinanceManagerOrOwnerAtActiveDealership`` (reuses M10.7 class
— zero-drift streak preserved at 38 → 39):

- ``GET /admin/lender-programs/list/`` — tenant-scoped list of
  active LenderPrograms. Narrow ``{id, name}`` projection.

Coverage:

- Permission matrix — five negative cases + two positive.
- Empty-tenant case (returns empty list, not 404).
- N-programs case (returns all active programs in name-ascending
  order per model Meta ordering).
- Active-only filter (inactive programs excluded).
- Narrow projection (only ``id`` + ``name``; NO ``contact`` /
  ``terms_summary`` / ``is_active`` / ``created_at`` /
  ``updated_at`` fields).
- Cross-tenant guard (other tenant's active programs excluded).
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_PORTER,
    ROLE_SALES_MANAGER,
    Dealership,
    LenderProgram,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


LIST_ENDPOINT = "dealer_ai:admin-lender-program-list"


def _fandi_client_at(dealership: Dealership, username: str) -> APIClient:
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_F_AND_I_MANAGER)
    return authenticated_client(user)


# ---------------------------------------------------------------------------
# Endpoint layer — auth matrix
# ---------------------------------------------------------------------------


class LenderProgramListEndpointAuthTests(TestCase):
    """Same permission class as M10.3 create (``_M101_PERMS``) —
    grants ``f_and_i_manager`` + ``dealer_owner``; blocks everyone
    else. Zero-drift streak preserved (38 → 39 at M35.1 close)."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        LenderProgram.objects.create(dealership=self.d, name="Auth Bank")
        self.url = reverse(LIST_ENDPOINT)

    def test_unauthenticated_returns_401_or_403(self) -> None:
        resp = APIClient().get(self.url)
        self.assertIn(resp.status_code, (401, 403))

    def test_no_membership_returns_403(self) -> None:
        user = make_user(username="lpl-nomem")
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_advisor_returns_403(self) -> None:
        user = make_user(username="lpl-adv")
        make_membership(user, self.d, ROLE_ADVISOR)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_sales_manager_returns_403(self) -> None:
        # F&I-gated; sales_manager does NOT grant F&I admin access.
        user = make_user(username="lpl-sm")
        make_membership(user, self.d, ROLE_SALES_MANAGER)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_porter_returns_403(self) -> None:
        user = make_user(username="lpl-porter")
        make_membership(user, self.d, ROLE_PORTER)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_f_and_i_manager_returns_200(self) -> None:
        resp = _fandi_client_at(self.d, "lpl-fandi").get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_dealer_owner_returns_200(self) -> None:
        user = make_user(username="lpl-owner")
        make_membership(user, self.d, ROLE_DEALER_OWNER)
        resp = authenticated_client(user).get(self.url)
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Endpoint layer — behavior + projection shape
# ---------------------------------------------------------------------------


class LenderProgramListEndpointBehaviorTests(TestCase):
    """Endpoint returns tenant-scoped active programs with narrow
    ``{id, name}`` projection. Per M35.1 D4 + §4.8 blocking-finding
    resolution."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        self.client = _fandi_client_at(self.d, "lpl-behavior")
        self.url = reverse(LIST_ENDPOINT)

    def test_empty_tenant_returns_empty_list_not_404(self) -> None:
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("lender_programs", body)
        self.assertEqual(body["lender_programs"], [])

    def test_n_programs_returned_in_name_ascending_order(self) -> None:
        # Meta.ordering = ("name",) — matches shipped
        # list_active_lender_programs verb.
        LenderProgram.objects.create(dealership=self.d, name="Chase")
        LenderProgram.objects.create(dealership=self.d, name="Ally")
        LenderProgram.objects.create(dealership=self.d, name="Bank of America")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        names = [p["name"] for p in resp.json()["lender_programs"]]
        self.assertEqual(names, ["Ally", "Bank of America", "Chase"])

    def test_inactive_programs_excluded(self) -> None:
        LenderProgram.objects.create(
            dealership=self.d, name="Live Bank", is_active=True
        )
        LenderProgram.objects.create(
            dealership=self.d, name="Dead Bank", is_active=False
        )
        resp = self.client.get(self.url)
        names = [p["name"] for p in resp.json()["lender_programs"]]
        self.assertEqual(names, ["Live Bank"])

    def test_narrow_projection_shape_id_and_name_only(self) -> None:
        """Per D4 + _project_lender_program_selector docstring: NO
        exposure of contact / terms_summary / is_active /
        created_at / updated_at. Extra exposure would falsely
        broaden the Lender Fit Recommendations blocker scope."""
        LenderProgram.objects.create(
            dealership=self.d,
            name="Narrow Bank",
            contact="555-1234",
            terms_summary="Test terms",
            is_active=True,
        )
        resp = self.client.get(self.url)
        row = resp.json()["lender_programs"][0]
        self.assertEqual(set(row.keys()), {"id", "name"})
        self.assertEqual(row["name"], "Narrow Bank")
        self.assertIsInstance(row["id"], int)

    def test_cross_tenant_programs_excluded(self) -> None:
        other = Dealership.objects.create(
            slug="lpl-other", name="Other Dealership"
        )
        LenderProgram.objects.create(dealership=self.d, name="Own Bank")
        LenderProgram.objects.create(dealership=other, name="Other Bank")
        resp = self.client.get(self.url)
        names = [p["name"] for p in resp.json()["lender_programs"]]
        self.assertEqual(names, ["Own Bank"])
