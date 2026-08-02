"""Milestone 11 · Increment 6 (SESSION_119) — read-only list endpoint tests.

Locks the three M11.6 substrate additions per
``MILESTONE_11_PLANNING.md`` §0.a M11.6 addendum:

- ``GET /admin/leads/`` — extended with ``?channel=`` filter.
- ``GET /admin/test-drives/list/`` — new list endpoint.
- ``GET /admin/be-backs/list/`` — new list endpoint.

Each endpoint enforces the same
:class:`IsSalesManagerOrOwnerAtActiveDealership` gate as its M11.1-
M11.5 write sibling.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    BE_BACK_REASON_TEST_DRIVE,
    BE_BACK_STATE_NO_SHOW,
    BE_BACK_STATE_PROMISED,
    LEAD_CHANNEL_CHAT,
    LEAD_CHANNEL_WALK_IN,
    ROLE_SALES_MANAGER,
    BeBack,
    CustomerLead,
    TestDrive,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


LEAD_LIST = "dealer_ai:admin-lead-list"
TEST_DRIVE_LIST = "dealer_ai:admin-test-drive-list"
BE_BACK_LIST = "dealer_ai:admin-be-back-list"


def _client_for_dealership(dealership, username):
    user = make_user(username=username)
    make_membership(user, dealership, ROLE_SALES_MANAGER)
    return authenticated_client(user)


class LeadChannelFilterTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client = _client_for_dealership(self.dealership, "m116-lead-cf")
        CustomerLead.objects.create(
            dealership=self.dealership,
            name="Walkin Wanda",
            channel=LEAD_CHANNEL_WALK_IN,
        )
        CustomerLead.objects.create(
            dealership=self.dealership,
            name="Chatty Charlie",
            channel=LEAD_CHANNEL_CHAT,
        )

    def test_channel_filter_narrows_result_set(self) -> None:
        response = self.client.get(
            reverse(LEAD_LIST) + f"?channel={LEAD_CHANNEL_WALK_IN}"
        )
        self.assertEqual(response.status_code, 200)
        names = {row["name"] for row in response.json()["results"]}
        self.assertIn("Walkin Wanda", names)
        self.assertNotIn("Chatty Charlie", names)

    def test_channel_filter_ignores_unknown_channels(self) -> None:
        # Garbage tokens silently ignored per _apply_lead_filters
        # convention. All rows (both channels) should surface.
        response = self.client.get(
            reverse(LEAD_LIST) + "?channel=fictional_channel"
        )
        self.assertEqual(response.status_code, 200)
        # Both leads visible because the unknown filter tokens are
        # dropped, so no channel constraint is applied.
        names = {row["name"] for row in response.json()["results"]}
        self.assertIn("Walkin Wanda", names)
        self.assertIn("Chatty Charlie", names)


class TestDriveListTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client = _client_for_dealership(self.dealership, "m116-td-list")
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="TD Lead"
        )
        self.vehicle = Vehicle.objects.create(
            stock_number="M116-TD-1",
            year=2024,
            model="F-150",
            price=Decimal("38500.00"),
            dealership=self.dealership,
        )
        self.drive_now = TestDrive.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_at=timezone.now(),
        )
        self.drive_old = TestDrive.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            driven_at=timezone.now() - dt.timedelta(days=10),
        )

    def test_list_returns_projection_for_every_row(self) -> None:
        response = self.client.get(reverse(TEST_DRIVE_LIST))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 2)
        keys = {"id", "lead_id", "vehicle_id", "driven_at"}
        for row in body["results"]:
            self.assertTrue(keys.issubset(set(row.keys())))

    def test_driven_since_filter_excludes_older_rows(self) -> None:
        cutoff = (timezone.now() - dt.timedelta(days=1)).isoformat()
        from urllib.parse import urlencode

        query = urlencode({"driven_since": cutoff})
        response = self.client.get(reverse(TEST_DRIVE_LIST) + f"?{query}")
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertIn(self.drive_now.id, ids)
        self.assertNotIn(self.drive_old.id, ids)

    def test_lead_id_filter_narrows_to_lead(self) -> None:
        other_lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Other TD Lead"
        )
        TestDrive.objects.create(
            dealership=self.dealership,
            lead=other_lead,
            vehicle=self.vehicle,
            driven_at=timezone.now(),
        )
        response = self.client.get(
            reverse(TEST_DRIVE_LIST) + f"?lead_id={self.lead.id}"
        )
        self.assertEqual(response.status_code, 200)
        lead_ids = {row["lead_id"] for row in response.json()["results"]}
        self.assertEqual(lead_ids, {self.lead.id})


class BeBackListTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.client = _client_for_dealership(self.dealership, "m116-bb-list")
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="BB Lead"
        )
        self.promised = BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now(),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
            state=BE_BACK_STATE_PROMISED,
        )
        self.no_show = BeBack.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now() - dt.timedelta(days=1),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
            state=BE_BACK_STATE_NO_SHOW,
        )

    def test_list_returns_all_states_by_default(self) -> None:
        response = self.client.get(reverse(BE_BACK_LIST))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    def test_state_filter_narrows_to_promised(self) -> None:
        response = self.client.get(
            reverse(BE_BACK_LIST) + f"?state={BE_BACK_STATE_PROMISED}"
        )
        self.assertEqual(response.status_code, 200)
        ids = {row["id"] for row in response.json()["results"]}
        self.assertEqual(ids, {self.promised.id})

    def test_state_filter_ignores_garbage(self) -> None:
        response = self.client.get(reverse(BE_BACK_LIST) + "?state=maybe")
        self.assertEqual(response.status_code, 200)
        # Garbage state silently ignored → all rows visible.
        self.assertEqual(response.json()["count"], 2)
