"""Milestone 32 · Increment 1 (SESSION_207) — DealWriteup read tests.

Locks the M32.1 read surface for the DealWriteup entity per
``MILESTONE_32_PLANNING.md`` §5.b D1 + D2.

Two new endpoints, both gated on
``IsSalesManagerOrOwnerAtActiveDealership`` (reuses M11.3
`_M113_PERMS` — zero-drift streak preserved):

- ``GET /admin/deal-writeups/list/`` — tenant-scoped list, filterable
  by ``state`` (pending/approved/handed_off, derived from timestamp
  presence) + ``lead_id``. Fail-explicit query validation — invalid
  values return 400 rather than silently unfiltering.
- ``GET /admin/deal-writeups/<int:pk>/`` — tenant-scoped read.

Coverage:

- Service ``list_deal_writeups`` — state filter matrix, lead filter,
  composition, unknown state raises ValueError.
- Service ``get_deal_writeup`` — happy path, cross-tenant, missing.
- Endpoint list — fail-explicit ``state`` matrix, fail-explicit
  ``lead_id`` matrix, permission matrix, happy path, tenant-scoped.
- Endpoint detail — happy, 404 missing, 404 cross-tenant,
  permission matrix.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Dealership,
    DealWriteup,
    Vehicle,
)
from dealer_ai.services.deal_writeups import (
    DEAL_WRITEUP_STATES,
    approve_deal_writeup,
    get_deal_writeup,
    hand_off_to_fandi,
    list_deal_writeups,
    record_deal_writeup,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)


LIST_ENDPOINT = "dealer_ai:admin-deal-writeup-list"
DETAIL_ENDPOINT = "dealer_ai:admin-deal-writeup-detail"


def _make_vehicle(dealership: Dealership, stock: str = "M32-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("40000.00"),
        dealership=dealership,
    )


def _make_writeup(
    dealership: Dealership,
    *,
    stock: str = "M32-W",
    lead_name: str = "Read Lead",
    approved: bool = False,
    handed_off: bool = False,
) -> DealWriteup:
    lead = CustomerLead.objects.create(dealership=dealership, name=lead_name)
    vehicle = _make_vehicle(dealership, stock)
    writeup = record_deal_writeup(
        dealership=dealership, lead=lead, vehicle=vehicle,
        vehicle_price=Decimal("28500.00"),
    )
    if approved or handed_off:
        approver = make_user(username=f"mgr-{stock}")
        make_membership(approver, dealership, ROLE_SALES_MANAGER)
        approve_deal_writeup(writeup=writeup, approved_by_user=approver)
    if handed_off:
        writeup, _ = hand_off_to_fandi(writeup=writeup)
    return writeup


# ---------------------------------------------------------------------------
# Service layer — list_deal_writeups
# ---------------------------------------------------------------------------


class ListDealWriteupsServiceTests(TestCase):
    def setUp(self) -> None:
        self.d = Dealership.objects.create(slug="d-list", name="D List")
        self.other = Dealership.objects.create(slug="d-list-o", name="D Other")
        self.pending = _make_writeup(self.d, stock="S-P")
        self.approved = _make_writeup(self.d, stock="S-A", approved=True)
        self.handed = _make_writeup(self.d, stock="S-H", handed_off=True)
        # Cross-tenant writeup — must never surface in `self.d` queries.
        self.cross = _make_writeup(self.other, stock="S-X", lead_name="Cross")

    def test_no_filter_returns_all_dealership_writeups(self) -> None:
        rows = list_deal_writeups(dealership=self.d)
        pks = {w.pk for w in rows}
        self.assertEqual(pks, {self.pending.pk, self.approved.pk, self.handed.pk})
        self.assertNotIn(self.cross.pk, pks)

    def test_state_pending_filters_correctly(self) -> None:
        rows = list_deal_writeups(dealership=self.d, state="pending")
        self.assertEqual([w.pk for w in rows], [self.pending.pk])

    def test_state_approved_filters_correctly(self) -> None:
        rows = list_deal_writeups(dealership=self.d, state="approved")
        self.assertEqual([w.pk for w in rows], [self.approved.pk])

    def test_state_handed_off_filters_correctly(self) -> None:
        rows = list_deal_writeups(dealership=self.d, state="handed_off")
        self.assertEqual([w.pk for w in rows], [self.handed.pk])

    def test_unknown_state_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            list_deal_writeups(dealership=self.d, state="not-a-state")

    def test_lead_filter_scopes_to_that_lead(self) -> None:
        rows = list_deal_writeups(dealership=self.d, lead=self.pending.lead)
        self.assertEqual([w.pk for w in rows], [self.pending.pk])

    def test_state_and_lead_filter_compose(self) -> None:
        # Add a second writeup on the same lead in a different state.
        vehicle2 = _make_vehicle(self.d, "S-P2")
        second = record_deal_writeup(
            dealership=self.d, lead=self.pending.lead, vehicle=vehicle2,
        )
        rows = list_deal_writeups(
            dealership=self.d, state="pending", lead=self.pending.lead,
        )
        pks = {w.pk for w in rows}
        self.assertEqual(pks, {self.pending.pk, second.pk})

    def test_ordering_is_newest_first_by_write_up_at(self) -> None:
        rows = list_deal_writeups(dealership=self.d)
        # Meta.ordering = ["-write_up_at"]; last-created first.
        self.assertEqual(
            [w.pk for w in rows],
            [self.handed.pk, self.approved.pk, self.pending.pk],
        )


# ---------------------------------------------------------------------------
# Service layer — get_deal_writeup
# ---------------------------------------------------------------------------


class GetDealWriteupServiceTests(TestCase):
    def setUp(self) -> None:
        self.d = Dealership.objects.create(slug="d-get", name="D Get")
        self.other = Dealership.objects.create(slug="d-get-o", name="D Get O")
        self.writeup = _make_writeup(self.d, stock="G-1")
        self.cross = _make_writeup(self.other, stock="G-X", lead_name="Cross")

    def test_happy_path_returns_row(self) -> None:
        row = get_deal_writeup(pk=self.writeup.pk, dealership=self.d)
        self.assertIsNotNone(row)
        self.assertEqual(row.pk, self.writeup.pk)

    def test_cross_tenant_returns_none(self) -> None:
        row = get_deal_writeup(pk=self.cross.pk, dealership=self.d)
        self.assertIsNone(row)

    def test_missing_returns_none(self) -> None:
        row = get_deal_writeup(pk=999_999, dealership=self.d)
        self.assertIsNone(row)


# ---------------------------------------------------------------------------
# Endpoint layer — GET /admin/deal-writeups/list/
# ---------------------------------------------------------------------------


class DealWriteupListEndpointAuthTests(TestCase):
    def setUp(self) -> None:
        self.d = get_default_dealership()

    def test_unauthenticated_returns_401_or_403(self) -> None:
        resp = APIClient().get(reverse(LIST_ENDPOINT))
        self.assertIn(resp.status_code, (401, 403))

    def test_no_membership_returns_403(self) -> None:
        user = make_user(username="dwl-nomem")
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 403)

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="dwl-adv")
        make_membership(user, self.d, ROLE_ADVISOR)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 403)

    def test_f_and_i_manager_forbidden(self) -> None:
        user = make_user(username="dwl-fandi")
        make_membership(user, self.d, ROLE_F_AND_I_MANAGER)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 403)

    def test_sales_manager_allowed(self) -> None:
        user = make_user(username="dwl-sm")
        make_membership(user, self.d, ROLE_SALES_MANAGER)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 200)

    def test_dealer_owner_allowed(self) -> None:
        user = make_user(username="dwl-do")
        make_membership(user, self.d, ROLE_DEALER_OWNER)
        resp = authenticated_client(user).get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 200)


class DealWriteupListEndpointFilterValidationTests(TestCase):
    """D1 fail-explicit — invalid values return 400."""

    def setUp(self) -> None:
        self.d = get_default_dealership()
        user = make_user(username="dwl-v")
        make_membership(user, self.d, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)

    def test_missing_state_returns_unfiltered(self) -> None:
        _make_writeup(self.d, stock="V-1", lead_name="V One")
        resp = self.client.get(reverse(LIST_ENDPOINT))
        self.assertEqual(resp.status_code, 200)

    def test_valid_state_pending_applies_filter(self) -> None:
        _make_writeup(self.d, stock="V-P", lead_name="V P")
        _make_writeup(self.d, stock="V-A", lead_name="V A", approved=True)
        resp = self.client.get(
            reverse(LIST_ENDPOINT), {"state": "pending"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["deal_writeups"]), 1)

    def test_invalid_state_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"state": "not-a-state"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("state", resp.json()["detail"].lower())

    def test_state_case_sensitive_returns_400(self) -> None:
        # `Pending` is not in the case-sensitive allowlist.
        resp = self.client.get(reverse(LIST_ENDPOINT), {"state": "Pending"})
        self.assertEqual(resp.status_code, 400)

    def test_state_empty_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"state": ""})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_lead_id_returns_400(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"lead_id": "abc"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("lead_id", resp.json()["detail"].lower())

    def test_nonexistent_lead_id_returns_empty_list(self) -> None:
        resp = self.client.get(reverse(LIST_ENDPOINT), {"lead_id": "999999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["deal_writeups"], [])

    def test_cross_tenant_lead_id_returns_empty_list(self) -> None:
        other = Dealership.objects.create(slug="v-other", name="V Other")
        cross_lead = CustomerLead.objects.create(
            dealership=other, name="Cross V"
        )
        resp = self.client.get(
            reverse(LIST_ENDPOINT), {"lead_id": str(cross_lead.pk)}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["deal_writeups"], [])


class DealWriteupListEndpointProjectionTests(TestCase):
    def setUp(self) -> None:
        self.d = get_default_dealership()
        user = make_user(username="dwl-p")
        make_membership(user, self.d, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)

    def test_projection_contains_expected_keys(self) -> None:
        w = _make_writeup(self.d, stock="P-1", lead_name="Proj Lead")
        resp = self.client.get(reverse(LIST_ENDPOINT))
        row = resp.json()["deal_writeups"][0]
        for key in (
            "id", "lead_id", "vehicle_id", "dealership_id",
            "vehicle_price", "write_up_at",
            "sales_manager_approved_at", "handed_off_to_fandi_at",
        ):
            self.assertIn(key, row)
        self.assertEqual(row["id"], w.pk)

    def test_returns_only_dealership_scoped_writeups(self) -> None:
        _make_writeup(self.d, stock="P-2", lead_name="Own")
        other = Dealership.objects.create(slug="p-other", name="P Other")
        _make_writeup(other, stock="P-X", lead_name="Cross Own")
        resp = self.client.get(reverse(LIST_ENDPOINT))
        self.assertEqual(len(resp.json()["deal_writeups"]), 1)


# ---------------------------------------------------------------------------
# Endpoint layer — GET /admin/deal-writeups/<pk>/
# ---------------------------------------------------------------------------


class DealWriteupDetailEndpointTests(TestCase):
    def setUp(self) -> None:
        self.d = get_default_dealership()
        self.other = Dealership.objects.create(slug="dt-o", name="Detail O")
        self.writeup = _make_writeup(self.d, stock="D-1", lead_name="Detail")
        self.cross = _make_writeup(self.other, stock="D-X", lead_name="Cross D")

        self.user = make_user(username="dwd-sm")
        make_membership(self.user, self.d, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_unauthenticated_returns_401_or_403(self) -> None:
        resp = APIClient().get(
            reverse(DETAIL_ENDPOINT, args=[self.writeup.pk])
        )
        self.assertIn(resp.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        adv = make_user(username="dwd-adv")
        make_membership(adv, self.d, ROLE_ADVISOR)
        resp = authenticated_client(adv).get(
            reverse(DETAIL_ENDPOINT, args=[self.writeup.pk])
        )
        self.assertEqual(resp.status_code, 403)

    def test_happy_path_returns_projection(self) -> None:
        resp = self.client.get(
            reverse(DETAIL_ENDPOINT, args=[self.writeup.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["deal_writeup"]["id"], self.writeup.pk)

    def test_missing_returns_404(self) -> None:
        resp = self.client.get(reverse(DETAIL_ENDPOINT, args=[999_999]))
        self.assertEqual(resp.status_code, 404)

    def test_cross_tenant_returns_404(self) -> None:
        resp = self.client.get(reverse(DETAIL_ENDPOINT, args=[self.cross.pk]))
        self.assertEqual(resp.status_code, 404)
