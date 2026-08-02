"""Milestone 11 · Increment 1 (SESSION_114) — non-chat lead intake endpoint tests.

Locks the HTTP surface of the four :mod:`views_leads` endpoints per
``MILESTONE_11_PLANNING.md`` §7 M11.1 + §1.9.

Coverage:

- Unauthenticated → 401 / 403 on every endpoint.
- Authenticated with no dealership membership → 403.
- Authenticated with disallowed role (advisor / f_and_i_manager) → 403.
- Authenticated with allowed role (sales_manager / dealer_owner) →
  201 on success.
- Referral cross-tenant referrer_lead_id → 404 (fail-closed).
- Webhook unknown platform → 400 with ``registered_platforms`` in body.
- Serializer validation (missing ``name``) → 400.
- Response shape assertion (``lead`` dict with id / channel /
  referrer_id / dealership_id / created_at).
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    LEAD_CHANNEL_LISTING_FORM,
    LEAD_CHANNEL_PHONE,
    LEAD_CHANNEL_REFERRAL,
    LEAD_CHANNEL_WALK_IN,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_F_AND_I_MANAGER,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Dealership,
)
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


WALK_IN_ENDPOINT = "dealer_ai:admin-lead-walk-in-create"
PHONE_ENDPOINT = "dealer_ai:admin-lead-phone-create"
REFERRAL_ENDPOINT = "dealer_ai:admin-lead-referral-create"
WEBHOOK_ENDPOINT = "dealer_ai:admin-lead-webhook-create"

ALL_ENDPOINTS = (
    WALK_IN_ENDPOINT,
    PHONE_ENDPOINT,
    REFERRAL_ENDPOINT,
    WEBHOOK_ENDPOINT,
)


def _post(client, url_name, body):
    return client.post(reverse(url_name), body, format="json")


class ChannelIntakeAuthTests(TestCase):
    """Authentication + authorization gates. Covers all four endpoints."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()

    def test_unauthenticated_returns_401_or_403_on_every_endpoint(self) -> None:
        for endpoint in ALL_ENDPOINTS:
            with self.subTest(endpoint=endpoint):
                body = (
                    {"platform": "generic", "payload": {"full_name": "A"}}
                    if endpoint == WEBHOOK_ENDPOINT
                    else {"name": "Anon"}
                )
                response = APIClient().post(reverse(endpoint), body, format="json")
                self.assertIn(response.status_code, (401, 403))

    def test_authenticated_no_membership_returns_403(self) -> None:
        user = make_user(username="cinm-nomem")
        response = _post(
            authenticated_client(user), WALK_IN_ENDPOINT, {"name": "Nomem"}
        )
        self.assertEqual(response.status_code, 403)

    def _role_returns_403(self, role: str) -> None:
        user = make_user(username=f"cinm-{role}")
        make_membership(user, self.dealership, role)
        response = _post(
            authenticated_client(user), WALK_IN_ENDPOINT, {"name": "Blocked"}
        )
        self.assertEqual(response.status_code, 403)

    def test_advisor_forbidden(self) -> None:
        self._role_returns_403(ROLE_ADVISOR)

    def test_f_and_i_manager_forbidden(self) -> None:
        self._role_returns_403(ROLE_F_AND_I_MANAGER)


class ChannelIntakeHappyPathTests(TestCase):
    """201 + response-shape coverage for each endpoint under an allowed role."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.user = make_user(username="cinm-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def _assert_lead_shape(self, body: dict, *, expected_channel: str) -> dict:
        self.assertIn("lead", body)
        lead = body["lead"]
        for key in (
            "id",
            "name",
            "phone",
            "email",
            "channel",
            "referrer_id",
            "dealership_id",
            "created_at",
        ):
            self.assertIn(key, lead)
        self.assertEqual(lead["channel"], expected_channel)
        self.assertEqual(lead["dealership_id"], self.dealership.id)
        return lead

    def test_walk_in_happy_path(self) -> None:
        response = _post(
            self.client,
            WALK_IN_ENDPOINT,
            {"name": "Wanda Walkup", "phone": "555-0100"},
        )
        self.assertEqual(response.status_code, 201)
        self._assert_lead_shape(response.json(), expected_channel=LEAD_CHANNEL_WALK_IN)

    def test_phone_happy_path_under_owner_role(self) -> None:
        owner = make_user(username="cinm-owner")
        make_membership(owner, self.dealership, ROLE_DEALER_OWNER)
        response = _post(
            authenticated_client(owner),
            PHONE_ENDPOINT,
            {"name": "Pat Phoner"},
        )
        self.assertEqual(response.status_code, 201)
        self._assert_lead_shape(response.json(), expected_channel=LEAD_CHANNEL_PHONE)

    def test_referral_happy_path_with_valid_referrer(self) -> None:
        referrer = CustomerLead.objects.create(
            dealership=self.dealership, name="Referrer Ray"
        )
        response = _post(
            self.client,
            REFERRAL_ENDPOINT,
            {"name": "Referred Rachel", "referrer_lead_id": referrer.id},
        )
        self.assertEqual(response.status_code, 201)
        lead = self._assert_lead_shape(
            response.json(), expected_channel=LEAD_CHANNEL_REFERRAL
        )
        self.assertEqual(lead["referrer_id"], referrer.id)

    def test_webhook_happy_path_with_generic_platform(self) -> None:
        response = _post(
            self.client,
            WEBHOOK_ENDPOINT,
            {
                "platform": "generic",
                "payload": {
                    "full_name": "Wendy Web",
                    "phone": "555-0111",
                    "email": "wendy@example.com",
                    "message": "Interested in the F-150",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        lead = self._assert_lead_shape(
            response.json(), expected_channel=LEAD_CHANNEL_LISTING_FORM
        )
        self.assertEqual(lead["name"], "Wendy Web")


class ChannelIntakeErrorMappingTests(TestCase):
    """Domain-error → HTTP mapping coverage."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other_dealership = Dealership.objects.create(
            slug="d-cross-tenant-ref", name="D Cross"
        )
        self.user = make_user(username="cinm-em-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_referral_with_cross_tenant_referrer_returns_404(self) -> None:
        cross_referrer = CustomerLead.objects.create(
            dealership=self.other_dealership, name="Cross Referrer"
        )
        response = _post(
            self.client,
            REFERRAL_ENDPOINT,
            {
                "name": "Blocked Referral",
                "referrer_lead_id": cross_referrer.id,
            },
        )
        self.assertEqual(response.status_code, 404)
        # Fail-closed: no CustomerLead was written for the caller.
        self.assertFalse(
            CustomerLead.objects.filter(name="Blocked Referral").exists()
        )

    def test_webhook_unknown_platform_returns_400_with_registry(self) -> None:
        response = _post(
            self.client,
            WEBHOOK_ENDPOINT,
            {"platform": "autotrader", "payload": {"full_name": "X"}},
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("registered_platforms", body)
        self.assertIn("generic", body["registered_platforms"])

    def test_walk_in_missing_name_returns_400(self) -> None:
        response = _post(self.client, WALK_IN_ENDPOINT, {"phone": "555"})
        self.assertEqual(response.status_code, 400)
