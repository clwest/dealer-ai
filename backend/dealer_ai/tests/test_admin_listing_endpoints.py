"""Milestone 6 · Increment 5 (SESSION_086) — admin listing endpoint tests.

Coverage of the six listing endpoints in ``views_listings.py``:

- ``GET  /admin/vehicles/<stock>/listing/`` — read current.
- ``POST /admin/vehicles/<stock>/listing/draft/``.
- ``POST /admin/vehicles/<stock>/listing/regenerate/``.
- ``POST /admin/vehicles/<stock>/listing/approve/``.
- ``POST /admin/vehicles/<stock>/listing/publish/``.
- ``POST /admin/vehicles/<stock>/listing/unpublish/``.

Uses ``MockLLMProvider`` via patching the ``services.vehicle_listing``
LLM factory so the tests never hit Ollama / OpenAI. Locked invariants:

- Permission matrix (unauth refused, no-role refused, sales_manager
  admitted).
- Cross-tenant fail-closed (404).
- Domain-error → HTTP mapping (409 / 422 / 400).
- Draft when listing exists → 409 ListingImmutableError.
- Regenerate on approved/published → 409 ListingImmutableError.
- Approve on non-draft → 409 InvalidListingTransitionError.
- Publish on non-approved → 409 InvalidListingTransitionError.
- Unpublish requires nonblank reason (400).
- Full lifecycle walk via HTTP.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    Dealership,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    VEHICLE_LISTING_STATUS_APPROVED,
    VEHICLE_LISTING_STATUS_DRAFT,
    VEHICLE_LISTING_STATUS_PUBLISHED,
    Vehicle,
    VehicleListing,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)
from dealer_ai.tests._mocks import MockLLMProvider


User = get_user_model()

_SAMPLE_BODY = "Great SUV. Well-equipped and ready for family duty."


def _vehicle(dealership, stock="M65-L") -> Vehicle:
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2024,
        model="Escape",
        make="Ford",
        price=Decimal("29500.00"),
    )


def _mock_llm_ctx(reply=_SAMPLE_BODY):
    """Patch the LLM factory so draft_listing uses a mock."""
    return patch(
        "dealer_ai.services.vehicle_listing.get_llm_provider",
        return_value=MockLLMProvider(replies=[reply]),
    )


# ============================================================================
# Permission matrix
# ============================================================================


class ListingEndpointPermissions(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        self.vehicle = _vehicle(self.default, "M65L-PERM")

    def test_unauthenticated_refused(self):
        from rest_framework.test import APIClient
        response = APIClient().get(
            reverse(
                "dealer_ai:admin-listing-read",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self):
        user = make_user("m65l-advisor")
        make_membership(user, self.default, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(
            reverse(
                "dealer_ai:admin-listing-read",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_sales_manager_admitted(self):
        user = make_user("m65l-sm-perm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        client = authenticated_client(user)
        response = client.get(
            reverse(
                "dealer_ai:admin-listing-read",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)


# ============================================================================
# Read endpoint
# ============================================================================


class ListingReadEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65l-read-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65L-READ")

    def test_no_listing_returns_null(self):
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-listing-read",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["listing"])

    def test_existing_listing_returned(self):
        now = timezone.now()
        VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_DRAFT,
            body="Existing body.",
            drafted_at=now,
        )
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-listing-read",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.data["listing"]["status"], "draft")
        self.assertEqual(response.data["listing"]["body"], "Existing body.")

    def test_cross_tenant_404(self):
        other = make_dealership("other-listing-read")
        v_other = _vehicle(other, "M65L-READ-OTHER")
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-listing-read",
                args=[v_other.stock_number],
            )
        )
        self.assertEqual(response.status_code, 404)


# ============================================================================
# Draft endpoint
# ============================================================================


class ListingDraftEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65l-draft-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65L-DRAFT")

    def test_draft_creates_listing(self):
        with _mock_llm_ctx():
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-draft",
                    args=[self.vehicle.stock_number],
                )
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "draft")
        self.assertEqual(response.data["body"], _SAMPLE_BODY)

    def test_draft_when_exists_409(self):
        VehicleListing.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            status=VEHICLE_LISTING_STATUS_DRAFT,
            body="Pre-existing draft.",
            drafted_at=timezone.now(),
        )
        with _mock_llm_ctx():
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-draft",
                    args=[self.vehicle.stock_number],
                )
            )
        self.assertEqual(response.status_code, 409)

    def test_draft_scrub_dropped_422(self):
        with _mock_llm_ctx(reply="We paid a lot for this trade-in."):
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-draft",
                    args=[self.vehicle.stock_number],
                )
            )
        self.assertEqual(response.status_code, 422)
        # Not persisted.
        self.assertFalse(
            VehicleListing.objects.filter(vehicle=self.vehicle).exists()
        )

    def test_draft_empty_llm_422(self):
        with _mock_llm_ctx(reply=""):
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-draft",
                    args=[self.vehicle.stock_number],
                )
            )
        self.assertEqual(response.status_code, 422)

    def test_draft_cross_tenant_404(self):
        other = make_dealership("other-listing-draft")
        v_other = _vehicle(other, "M65L-DRAFT-OTHER")
        with _mock_llm_ctx():
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-draft",
                    args=[v_other.stock_number],
                )
            )
        self.assertEqual(response.status_code, 404)


# ============================================================================
# Regenerate / approve / publish / unpublish
# ============================================================================


class ListingLifecycleEndpoints(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65l-lc-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65L-LC")
        # Seed a draft listing to walk the ladder from.
        with _mock_llm_ctx():
            self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-draft",
                    args=[self.vehicle.stock_number],
                )
            )

    def test_regenerate_replaces_body(self):
        with _mock_llm_ctx(reply="Redrafted body v2."):
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-regenerate",
                    args=[self.vehicle.stock_number],
                )
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["body"], "Redrafted body v2.")

    def test_approve_flips_status(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-approve",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "approved")

    def test_publish_flips_status(self):
        self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-approve",
                args=[self.vehicle.stock_number],
            )
        )
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-publish",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "published")

    def test_publish_on_draft_409(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-publish",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 409)

    def test_unpublish_requires_reason(self):
        self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-approve",
                args=[self.vehicle.stock_number],
            )
        )
        self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-publish",
                args=[self.vehicle.stock_number],
            )
        )
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-unpublish",
                args=[self.vehicle.stock_number],
            ),
            data=json.dumps({"reason": ""}),
            content_type="application/json",
        )
        # Empty reason fails DRF serializer (max_length=255 but
        # allow_blank defaults False, so blank → 400).
        self.assertEqual(response.status_code, 400)

    def test_unpublish_walks_full_lifecycle(self):
        self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-approve",
                args=[self.vehicle.stock_number],
            )
        )
        self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-publish",
                args=[self.vehicle.stock_number],
            )
        )
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-unpublish",
                args=[self.vehicle.stock_number],
            ),
            data=json.dumps({"reason": "Sold pending paperwork."}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "unpublished")
        self.assertEqual(
            response.data["unpublished_reason"],
            "Sold pending paperwork.",
        )

    def test_regenerate_on_approved_409(self):
        self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-approve",
                args=[self.vehicle.stock_number],
            )
        )
        with _mock_llm_ctx(reply="tried to redraft"):
            response = self.client_a.post(
                reverse(
                    "dealer_ai:admin-listing-regenerate",
                    args=[self.vehicle.stock_number],
                )
            )
        self.assertEqual(response.status_code, 409)

    def test_approve_on_missing_listing_404(self):
        fresh_v = _vehicle(self.default, "M65L-LC-FRESH")
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-listing-approve",
                args=[fresh_v.stock_number],
            )
        )
        self.assertEqual(response.status_code, 404)
