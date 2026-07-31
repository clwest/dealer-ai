"""Milestone 1 · Increment 4C — advisor workspace authorization.

Focused permission-layer tests covering the six required outcomes
plus a positive control and cross-dealership isolation. Business-
behavior tests (own-leads-only, unknown-lead 404, channel validation)
live in :mod:`test_salesperson_and_assignment` and :mod:`test_follow_up`
where they belong; this module tests authorization decisions only.

Every test exercises the composed permission
``IsAuthenticated & (IsAdvisorForSlug | IsDealerOwnerForAdvisorSlug)``
declared on both ``advisor_workspace`` and ``advisor_follow_up``.
"""

from __future__ import annotations

import json

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    Salesperson,
    UserDealershipRole,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_advisor_user,
    make_dealership,
    make_membership,
    make_user,
)


class AdvisorWorkspaceAuthorization(TestCase):
    """The six required authorization outcomes on GET
    ``/api/dealer-ai/advisor/<slug>/``.
    """

    def setUp(self):
        self.dealership_a = get_default_dealership()
        self.dealership_b = make_dealership(slug="dealership-b")
        # Legitimate advisor at dealership A.
        self.advisor_user, self.advisor = make_advisor_user(
            slug="alpha-advisor",
            dealership=self.dealership_a,
            username="alpha",
        )
        # A second advisor at dealership B — target for cross-tenant
        # tests.
        self.other_advisor_user, self.other_advisor = make_advisor_user(
            slug="bravo-advisor",
            dealership=self.dealership_b,
            username="bravo",
        )
        self.url = reverse(
            "dealer_ai:advisor-workspace", args=["alpha-advisor"]
        )

    # -- ❌ Unauthenticated user ----------------------------------------

    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()  # no force_authenticate
        res = client.get(self.url)
        # DRF returns 401 or 403 for unauthenticated depending on the
        # active authentication backend; both are "unauthorized". We
        # accept either — the invariant is "not 200".
        self.assertIn(res.status_code, (401, 403))

    # -- ✅ Correct advisor assigned to the workspace -------------------

    def test_correct_advisor_is_authorized(self):
        client = authenticated_client(self.advisor_user)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["salesperson"]["slug"], "alpha-advisor")

    # -- ❌ Advisor from another dealership -----------------------------

    def test_cross_dealership_advisor_is_forbidden(self):
        # bravo-advisor is authenticated as themselves but hitting
        # alpha-advisor's workspace at dealership A.
        client = authenticated_client(self.other_advisor_user)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 403)

    # -- ✅ Dealer owner belonging to the same dealership ---------------

    def test_dealer_owner_at_same_dealership_is_authorized(self):
        owner = make_user(username="owner-a")
        make_membership(owner, self.dealership_a, ROLE_DEALER_OWNER)
        client = authenticated_client(owner)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["salesperson"]["slug"], "alpha-advisor")

    # -- ❌ Dealer owner from another dealership -----------------------

    def test_dealer_owner_at_different_dealership_is_forbidden(self):
        owner = make_user(username="owner-b")
        make_membership(owner, self.dealership_b, ROLE_DEALER_OWNER)
        client = authenticated_client(owner)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 403)

    # -- ❌ Authenticated user without appropriate relationship --------

    def test_authenticated_user_with_no_relationship_is_forbidden(self):
        # Auth alone does not grant workspace access. No salesperson
        # link, no dealer_owner membership at the target dealership.
        stranger = make_user(username="stranger")
        client = authenticated_client(stranger)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_authenticated_advisor_role_membership_alone_is_forbidden(self):
        # A membership row with role=advisor at the same dealership is
        # *not* sufficient — authorization also requires the
        # Salesperson.user link to match the URL slug. This locks the
        # layer separation: role membership is business-permission
        # infrastructure, not a per-slug authorization statement.
        curious = make_user(username="curious")
        make_membership(curious, self.dealership_a, ROLE_ADVISOR)
        client = authenticated_client(curious)
        res = client.get(self.url)
        self.assertEqual(res.status_code, 403)


class AdvisorWorkspaceAuthorizationDoesNotLeakUnknownSlugs(TestCase):
    """Unknown-slug requests must be indistinguishable from
    known-slug-but-unauthorized requests. Locks the "no information
    leakage via differential status codes" invariant.
    """

    def setUp(self):
        self.default = get_default_dealership()
        self.stranger = make_user(username="unknown-slug-stranger")

    def test_authenticated_stranger_unknown_slug_is_forbidden_not_notfound(self):
        client = authenticated_client(self.stranger)
        url = reverse("dealer_ai:advisor-workspace", args=["ghost"])
        res = client.get(url)
        # 403 (permission denied), not 404 (which would leak that the
        # slug does not exist).
        self.assertEqual(res.status_code, 403)


class AdvisorFollowUpAuthorization(TestCase):
    """The same authorization matrix applied to POST
    ``/api/dealer-ai/advisor/<slug>/lead/<lead_id>/follow-up/``.

    The endpoint's own lead-ownership 403 (data-scoping layer) is
    orthogonal — a dealer_owner may access an advisor's workspace but
    cannot draft on leads assigned to a different advisor. That
    interaction is tested here to lock the layer separation.
    """

    def setUp(self):
        # Ensure the follow-up service does not attempt a real LLM
        # call — replace the provider factory for the duration of
        # each test.
        from dealer_ai.services import follow_up as follow_up_svc
        from dealer_ai.tests._mocks import MockLLMProvider
        from dealer_ai.tests.test_follow_up import _good_drafts_json

        original = follow_up_svc.get_llm_provider
        follow_up_svc.get_llm_provider = lambda: MockLLMProvider(
            replies=[_good_drafts_json("sms")]
        )  # type: ignore[assignment]
        self.addCleanup(setattr, follow_up_svc, "get_llm_provider", original)

        self.dealership_a = get_default_dealership()
        self.dealership_b = make_dealership(slug="follow-up-b")
        self.advisor_user, self.advisor = make_advisor_user(
            slug="alpha-follow-up",
            dealership=self.dealership_a,
            username="alpha-fu",
        )
        self.other_user, self.other = make_advisor_user(
            slug="bravo-follow-up",
            dealership=self.dealership_b,
            username="bravo-fu",
        )
        self.lead = self._make_lead(assigned_to=self.advisor)
        self.url = reverse(
            "dealer_ai:advisor-follow-up",
            args=["alpha-follow-up", self.lead.pk],
        )

    def _make_lead(self, *, assigned_to: Salesperson):
        from decimal import Decimal

        from dealer_ai.models import CustomerLead

        return CustomerLead.objects.create(
            name="Casey Morales",
            urgency="this_week",
            target_monthly_payment=Decimal("500"),
            down_payment=Decimal("1000"),
            conversation_summary="wants a Ranger",
            assigned_to=assigned_to,
        )

    def _post(self, client):
        return client.post(
            self.url,
            data=json.dumps({"channel": "sms", "tone": "warm"}),
            content_type="application/json",
        )

    def test_unauthenticated_is_rejected(self):
        res = self._post(APIClient())
        self.assertIn(res.status_code, (401, 403))

    def test_correct_advisor_is_authorized(self):
        res = self._post(authenticated_client(self.advisor_user))
        self.assertEqual(res.status_code, 200)

    def test_cross_dealership_advisor_is_forbidden(self):
        res = self._post(authenticated_client(self.other_user))
        self.assertEqual(res.status_code, 403)

    def test_dealer_owner_at_same_dealership_is_authorized_when_lead_belongs(self):
        # dealer_owner + lead assigned to the advisor named in the URL
        # → permission passes AND ownership passes → 200.
        owner = make_user(username="owner-a-fu")
        make_membership(owner, self.dealership_a, ROLE_DEALER_OWNER)
        res = self._post(authenticated_client(owner))
        self.assertEqual(res.status_code, 200)

    def test_dealer_owner_at_different_dealership_is_forbidden(self):
        owner = make_user(username="owner-b-fu")
        make_membership(owner, self.dealership_b, ROLE_DEALER_OWNER)
        res = self._post(authenticated_client(owner))
        self.assertEqual(res.status_code, 403)

    def test_lead_ownership_still_enforced_for_authorized_caller(self):
        # dealer_owner authorized at the URL's dealership tries to
        # draft against a lead NOT assigned to the URL-named advisor
        # → permission passes (they may access the workspace) but the
        # view's lead-ownership check rejects the draft. Layer
        # separation: authorization ≠ data scoping.
        owner = make_user(username="owner-a-fu-cross-lead")
        make_membership(owner, self.dealership_a, ROLE_DEALER_OWNER)
        # Second advisor at dealership A; lead assigned to them, but
        # the URL targets alpha-follow-up.
        second_at_a = Salesperson.objects.create(
            dealership=self.dealership_a,
            slug="alpha-two",
            name="Alpha Two",
            is_active=True,
        )
        other_lead = self._make_lead(assigned_to=second_at_a)
        url = reverse(
            "dealer_ai:advisor-follow-up",
            args=["alpha-follow-up", other_lead.pk],
        )
        client = authenticated_client(owner)
        res = client.post(
            url,
            data=json.dumps({"channel": "sms", "tone": "warm"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)
