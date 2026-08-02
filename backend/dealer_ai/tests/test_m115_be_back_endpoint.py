"""Milestone 11 · Increment 5 (SESSION_118) — BeBack endpoint tests."""

from __future__ import annotations

import datetime as dt

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    BE_BACK_REASON_TEST_DRIVE,
    BE_BACK_STATE_NO_SHOW,
    BE_BACK_STATE_RETURNED,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Dealership,
)
from dealer_ai.services.be_backs import record_be_back
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CREATE = "dealer_ai:admin-be-back-create"
RETURNED = "dealer_ai:admin-be-back-mark-returned"
NO_SHOW = "dealer_ai:admin-be-back-mark-no-show"


def _post(client, url, body):
    return client.post(url, body, format="json")


class BeBackCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Auth Lead"
        )
        self.body = {
            "lead_id": self.lead.pk,
            "promised_at": (timezone.now() + dt.timedelta(days=1)).isoformat(),
            "promised_reason": BE_BACK_REASON_TEST_DRIVE,
        }

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(reverse(CREATE), self.body, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="bb-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(authenticated_client(user), reverse(CREATE), self.body)
        self.assertEqual(response.status_code, 403)


class BeBackCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Happy"
        )
        self.user = make_user(username="bb-ep-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE),
            {
                "lead_id": self.lead.pk,
                "promised_at": (
                    timezone.now() + dt.timedelta(days=1)
                ).isoformat(),
                "promised_reason": BE_BACK_REASON_TEST_DRIVE,
                "notes": "Bringing wife.",
            },
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["be_back"]
        for key in (
            "id",
            "lead_id",
            "dealership_id",
            "promised_at",
            "promised_reason",
            "actual_return_at",
            "state",
            "notes",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["state"], "promised")
        self.assertIsNone(body["actual_return_at"])


class BeBackCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="bb-ep-em-other", name="BB EP EM Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.user = make_user(username="bb-ep-em")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_cross_tenant_lead_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE),
            {
                "lead_id": self.cross_lead.pk,
                "promised_at": timezone.now().isoformat(),
                "promised_reason": BE_BACK_REASON_TEST_DRIVE,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_reason_returns_400(self) -> None:
        response = _post(
            self.client,
            reverse(CREATE),
            {
                "lead_id": self.lead.pk,
                "promised_at": timezone.now().isoformat(),
                "promised_reason": "wants_espresso",
            },
        )
        self.assertEqual(response.status_code, 400)


class BeBackTransitionEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Trans"
        )
        self.user = make_user(username="bb-ep-trans")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.bb = record_be_back(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now() + dt.timedelta(days=1),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
        )

    def test_mark_returned_happy(self) -> None:
        response = _post(
            self.client,
            reverse(RETURNED, kwargs={"pk": self.bb.pk}),
            {},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["be_back"]
        self.assertEqual(body["state"], BE_BACK_STATE_RETURNED)
        self.assertIsNotNone(body["actual_return_at"])

    def test_mark_no_show_happy(self) -> None:
        response = _post(
            self.client,
            reverse(NO_SHOW, kwargs={"pk": self.bb.pk}),
            {"notes": "Did not show; auto-flagged."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["be_back"]
        self.assertEqual(body["state"], BE_BACK_STATE_NO_SHOW)
        self.assertIsNone(body["actual_return_at"])

    def test_re_transition_after_terminal_returns_409(self) -> None:
        _post(
            self.client,
            reverse(RETURNED, kwargs={"pk": self.bb.pk}),
            {},
        )
        response = _post(
            self.client,
            reverse(RETURNED, kwargs={"pk": self.bb.pk}),
            {},
        )
        self.assertEqual(response.status_code, 409)

    def test_nonexistent_be_back_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(RETURNED, kwargs={"pk": 999_999}),
            {},
        )
        self.assertEqual(response.status_code, 404)
