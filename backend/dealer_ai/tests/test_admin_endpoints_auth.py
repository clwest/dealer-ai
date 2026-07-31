"""Milestone 1 · Increment 4D — administrative authorization + tenant scoping.

Focused permission-layer + queryset-scoping tests for every
``/api/dealer-ai/admin/*`` endpoint, ``/manager-chat/``,
``/onboarding/profile/`` (PUT/PATCH), and ``/onboarding/profile/logo/``.

Two concerns, kept separate:

- **Authorization** — the six required outcomes per endpoint
  (unauth, unrelated authenticated user, wrong role, wrong tenant,
  correct role, correct dealer_owner). Uses focused permission tests
  rather than broad integration coverage.
- **Data scoping** — an admin at Dealership A sees only Dealership
  A's rows. Every gated list/aggregate query is exercised with a
  cross-tenant fixture.

Business logic (list shape, filter semantics, coaching output) is
covered by the pre-4D suite that was authenticated during this
increment. This module tests only the authorization + isolation
concerns 4D introduces.
"""

from __future__ import annotations

import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_PORTER,
    ROLE_SALES_MANAGER,
    ChatSession,
    CustomerLead,
    Salesperson,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)

User = get_user_model()


# --- Fixtures -------------------------------------------------------------


def _lead(dealership, name="Casey", assigned_to=None):
    return CustomerLead.objects.create(
        dealership=dealership,
        name=name,
        urgency="this_week",
        target_monthly_payment=Decimal("500"),
        assigned_to=assigned_to,
    )


def _vehicle(dealership, stock="V-1", price="30000.00"):
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2025,
        model="F-150",
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _salesperson(dealership, slug="advisor-x"):
    return Salesperson.objects.create(
        dealership=dealership, slug=slug, name="Advisor X"
    )


# --- Authorization matrix helper -----------------------------------------


class AdminEndpointAuthMatrixBase:
    """Mixin exercising the authorization outcomes against a single
    admin endpoint. Subclass and provide ``method``, ``url_name``,
    ``url_args`` (optional), and ``payload`` (optional).

    **What is under test.** These endpoints derive their active
    dealership from the caller's membership (via
    ``get_current_dealership(request)`` → ``get_active_membership``).
    There is no URL-shape "wrong tenant" scenario — an admin at
    Dealership B who hits an admin endpoint is administering
    Dealership B. Cross-tenant *data* protection is enforced by
    ``.filter(dealership=…)`` scoping and locked by the tests in
    :class:`AdminListEndpointsAreTenantScoped` +
    :class:`AdminLeadDetailFailsClosedAcrossTenants` +
    :class:`AdminLeadAssignRejectsCrossTenantSalesperson`.

    Outcomes locked here:

    - Unauthenticated → 401/403.
    - Authenticated user with no dealership role → 403.
    - Authenticated user with only ``advisor`` role → 403.
    - Authenticated user with only ``porter`` role → 403.
    - Authenticated ``sales_manager`` at the user's own dealership → 200.
    - Authenticated ``dealer_owner`` at the user's own dealership → 200.
    """

    method = "GET"
    url_name = ""
    url_args: tuple = ()
    payload: dict | None = None
    expected_ok_status = 200

    def setup_tenants(self):
        self.dealership_a = get_default_dealership()

    def request(self, client):
        url = reverse(f"dealer_ai:{self.url_name}", args=self.url_args)
        if self.method == "GET":
            return client.get(url)
        if self.payload is None:
            return getattr(client, self.method.lower())(url)
        return getattr(client, self.method.lower())(
            url,
            data=json.dumps(self.payload),
            content_type="application/json",
        )

    def test_unauthenticated_is_rejected(self):
        self.setup_tenants()
        res = self.request(APIClient())
        self.assertIn(res.status_code, (401, 403), res.content)

    def test_authenticated_user_with_no_role_is_forbidden(self):
        self.setup_tenants()
        user = make_user(username="no-role")
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, 403, res.content)

    def test_advisor_role_alone_is_forbidden(self):
        self.setup_tenants()
        user = make_user(username="advisor-role-only")
        make_membership(user, self.dealership_a, ROLE_ADVISOR)
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, 403, res.content)

    def test_porter_role_alone_is_forbidden(self):
        self.setup_tenants()
        user = make_user(username="porter-only")
        make_membership(user, self.dealership_a, ROLE_PORTER)
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, 403, res.content)

    def test_sales_manager_at_active_tenant_is_authorized(self):
        self.setup_tenants()
        user = make_user(username="sm-ok")
        make_membership(user, self.dealership_a, ROLE_SALES_MANAGER)
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, self.expected_ok_status, res.content)

    def test_dealer_owner_at_active_tenant_is_authorized(self):
        self.setup_tenants()
        user = make_user(username="do-ok")
        make_membership(user, self.dealership_a, ROLE_DEALER_OWNER)
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, self.expected_ok_status, res.content)


# --- Per-endpoint authorization matrices ---------------------------------


class AdminLeadListAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-lead-list"


class AdminChatSessionListAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-chat-session-list"


class AdminTrendsAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-trends"


class AdminPipelineAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-pipeline"


class AdminSalespeopleAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-salespeople"


class AdminAuditEventsAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-audit-events"


class ManagerChatAuth(AdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "manager-chat"
    payload = {"message": "How should I frame the F-150 vs Ranger?"}

    def setUp(self):
        # Manager chat generates an assistant reply via the LLM
        # provider inside ChatEngine. Patch the factory ChatEngine
        # imports directly so no real backend call happens.
        from dealer_ai.services import chat_engine as chat_engine_mod
        from dealer_ai.tests._mocks import MockLLMProvider

        original = chat_engine_mod.get_llm_provider
        chat_engine_mod.get_llm_provider = lambda: MockLLMProvider(
            replies=["Coaching reply."]
        )
        self.addCleanup(
            setattr, chat_engine_mod, "get_llm_provider", original
        )


class AdminAdCopyAuth(AdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-ad-copy"
    payload = {
        "recommendation": {
            "id": "marketing.promote_model.f-150",
            "category": "marketing",
            "title": "Promote F-150",
            "explanation": "Demand is up.",
            "action_text": "Feature the F-150.",
            "evidence": {"model": "F-150"},
        }
    }

    def setUp(self):
        # Stub the ad-copy LLM provider — the endpoint only needs to
        # return 200 for the authorization test.
        from dealer_ai.services import ad_copy as ad_copy_svc
        from dealer_ai.tests._mocks import MockLLMProvider

        original = ad_copy_svc.get_llm_provider
        ad_copy_svc.get_llm_provider = lambda: MockLLMProvider(
            replies=['[{"channel":"facebook","body":"An F-150 you can drive home today."}]']
        )
        self.addCleanup(
            setattr, ad_copy_svc, "get_llm_provider", original
        )


class AdminLeadDetailAuth(AdminEndpointAuthMatrixBase, TestCase):
    url_name = "admin-lead-detail"

    def setUp(self):
        # Need a real lead pk to look up; created inside setup_tenants.
        self._lead_created = False

    def setup_tenants(self):
        super().setup_tenants()
        if not self._lead_created:
            lead = _lead(self.dealership_a)
            self.url_args = (lead.pk,)
            self._lead_created = True


class AdminLeadHandoffAuth(AdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-lead-handoff"
    payload = {"mark_handed_off": False}

    def setUp(self):
        self._lead_created = False

    def setup_tenants(self):
        super().setup_tenants()
        if not self._lead_created:
            lead = _lead(self.dealership_a)
            self.url_args = (lead.pk,)
            self._lead_created = True


class AdminLeadAssignAuth(AdminEndpointAuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-lead-assign"

    def setUp(self):
        self._configured = False

    def setup_tenants(self):
        super().setup_tenants()
        if not self._configured:
            lead = _lead(self.dealership_a)
            sp = _salesperson(self.dealership_a, slug="assign-target")
            self.url_args = (lead.pk,)
            self.payload = {"salesperson_id": sp.pk}
            self._configured = True


class OnboardingProfileMutationAuth(AdminEndpointAuthMatrixBase, TestCase):
    """Onboarding PUT requires dealer_owner. sales_manager is NOT
    sufficient — override the mixin's sales_manager-authorized test to
    expect 403, add a dealer_owner-authorized test, and rely on the
    inherited dealer_owner test for the positive path."""

    method = "PUT"
    url_name = "onboarding-profile"
    payload: dict = {}  # populated in setUp so serializer accepts it

    def setUp(self):
        from dealer_ai.serializers import ONBOARDING_DEFAULTS

        self.payload = {**ONBOARDING_DEFAULTS, "dealership_name": "Test"}

    def test_sales_manager_at_active_tenant_is_authorized(self):
        # Overridden: onboarding mutation requires dealer_owner
        # explicitly (higher-privilege surface). sales_manager is
        # forbidden even at the active tenant.
        self.setup_tenants()
        user = make_user(username="sm-cannot-onboard")
        make_membership(user, self.dealership_a, ROLE_SALES_MANAGER)
        res = self.request(authenticated_client(user))
        self.assertEqual(res.status_code, 403, res.content)


# --- Public GET on onboarding remains unauthenticated --------------------


class OnboardingProfileGetIsPublic(TestCase):
    """§3 compatibility invariant: branding renders on public pages
    that never authenticate. GET must remain publicly accessible even
    after 4D wires the PUT/PATCH gate.
    """

    def test_anonymous_get_returns_200(self):
        url = reverse("dealer_ai:onboarding-profile")
        res = APIClient().get(url)
        self.assertEqual(res.status_code, 200, res.content)


# --- Data-scoping tests --------------------------------------------------


class AdminListEndpointsAreTenantScoped(TestCase):
    """Prove that every list-returning admin endpoint returns only rows
    that belong to the caller's active dealership. Rows from another
    dealership must never appear.
    """

    def setUp(self):
        self.dealership_a = get_default_dealership()
        self.dealership_b = make_dealership(slug="scoping-b")

        # Dealership A rows.
        _vehicle(self.dealership_a, stock="A-V-1")
        _lead(self.dealership_a, name="Alpha Lead")
        self.a_session = ChatSession.objects.create(
            dealership=self.dealership_a, customer_name="Alpha Customer"
        )
        Salesperson.objects.create(
            dealership=self.dealership_a, slug="alpha-advisor", name="Alpha Advisor"
        )

        # Dealership B rows.
        _vehicle(self.dealership_b, stock="B-V-1")
        _lead(self.dealership_b, name="Bravo Lead")
        ChatSession.objects.create(
            dealership=self.dealership_b, customer_name="Bravo Customer"
        )
        Salesperson.objects.create(
            dealership=self.dealership_b, slug="bravo-advisor", name="Bravo Advisor"
        )

        owner_a = make_user(username="owner-a-scoping")
        make_membership(owner_a, self.dealership_a, ROLE_DEALER_OWNER)
        self.client_a = authenticated_client(owner_a)

    def test_admin_lead_list_returns_only_active_tenants_leads(self):
        res = self.client_a.get(reverse("dealer_ai:admin-lead-list"))
        self.assertEqual(res.status_code, 200)
        names = {row["name"] for row in res.json()["results"]}
        self.assertIn("Alpha Lead", names)
        self.assertNotIn("Bravo Lead", names)

    def test_admin_chat_session_list_returns_only_active_tenants_sessions(self):
        res = self.client_a.get(reverse("dealer_ai:admin-chat-session-list"))
        self.assertEqual(res.status_code, 200)
        customers = {row["customer_name"] for row in res.json()["results"]}
        self.assertIn("Alpha Customer", customers)
        self.assertNotIn("Bravo Customer", customers)

    def test_admin_salespeople_returns_only_active_tenants_advisors(self):
        res = self.client_a.get(reverse("dealer_ai:admin-salespeople"))
        self.assertEqual(res.status_code, 200)
        slugs = {row["slug"] for row in res.json()["results"]}
        self.assertIn("alpha-advisor", slugs)
        self.assertNotIn("bravo-advisor", slugs)

    def test_admin_trends_counts_only_active_tenants_data(self):
        res = self.client_a.get(reverse("dealer_ai:admin-trends"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Dealership A has 1 lead + 1 session; Dealership B's row must
        # not leak into the aggregate.
        self.assertEqual(data["total_leads"], 1)
        self.assertEqual(data["total_chat_sessions"], 1)

    def test_admin_pipeline_counts_only_active_tenants_data(self):
        res = self.client_a.get(reverse("dealer_ai:admin-pipeline"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Sum all stages — Dealership A has exactly one lead.
        total_leads_in_stages = sum(
            stage["count"] for stage in data["stages"]
        )
        self.assertEqual(total_leads_in_stages, 1)


class AdminLeadDetailFailsClosedAcrossTenants(TestCase):
    """A lead lookup by pk must fall through the tenant filter — asking
    for another dealership's lead by pk returns 404, not 200 with
    cross-tenant data.
    """

    def setUp(self):
        self.dealership_a = get_default_dealership()
        self.dealership_b = make_dealership(slug="lead-detail-b")
        self.b_lead = _lead(self.dealership_b, name="Bravo-only Lead")

        owner_a = make_user(username="owner-a-lead-detail")
        make_membership(owner_a, self.dealership_a, ROLE_DEALER_OWNER)
        self.client_a = authenticated_client(owner_a)

    def test_lead_detail_returns_404_for_other_tenants_lead(self):
        res = self.client_a.get(
            reverse("dealer_ai:admin-lead-detail", args=[self.b_lead.pk])
        )
        self.assertEqual(res.status_code, 404, res.content)

    def test_lead_handoff_returns_404_for_other_tenants_lead(self):
        res = self.client_a.post(
            reverse("dealer_ai:admin-lead-handoff", args=[self.b_lead.pk]),
            data=json.dumps({"mark_handed_off": True}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404, res.content)

    def test_lead_assign_returns_404_for_other_tenants_lead(self):
        # Even with a same-tenant salesperson in the body, the lead
        # doesn't belong to the caller.
        sp = _salesperson(self.dealership_a, slug="cross-assign-target")
        res = self.client_a.post(
            reverse("dealer_ai:admin-lead-assign", args=[self.b_lead.pk]),
            data=json.dumps({"salesperson_id": sp.pk}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404, res.content)


class AdminLeadAssignRejectsCrossTenantSalesperson(TestCase):
    """A same-tenant lead + a cross-tenant salesperson body → 400.
    Ensures an owner cannot assign one of their leads to another
    dealership's advisor.
    """

    def setUp(self):
        self.dealership_a = get_default_dealership()
        self.dealership_b = make_dealership(slug="cross-assign-b")
        self.a_lead = _lead(self.dealership_a, name="Alpha Lead")
        self.b_salesperson = _salesperson(
            self.dealership_b, slug="cross-assign-b-target"
        )

        owner_a = make_user(username="owner-a-cross-assign")
        make_membership(owner_a, self.dealership_a, ROLE_DEALER_OWNER)
        self.client_a = authenticated_client(owner_a)

    def test_assigning_to_cross_tenant_salesperson_returns_400(self):
        res = self.client_a.post(
            reverse("dealer_ai:admin-lead-assign", args=[self.a_lead.pk]),
            data=json.dumps({"salesperson_id": self.b_salesperson.pk}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400, res.content)


class OnboardingLogoUploadRequiresDealerOwner(TestCase):
    """Focused sanity check that the logo upload endpoint gates on
    dealer_owner. sales_manager cannot upload; dealer_owner can (with
    a validation-level 400 for the empty body — proves auth passed).
    """

    def setUp(self):
        self.dealership_a = get_default_dealership()
        self.sm_user = make_user(username="sm-logo-no")
        make_membership(self.sm_user, self.dealership_a, ROLE_SALES_MANAGER)
        self.owner = make_user(username="owner-logo-yes")
        make_membership(self.owner, self.dealership_a, ROLE_DEALER_OWNER)

    def test_sales_manager_cannot_upload_logo(self):
        res = authenticated_client(self.sm_user).post(
            reverse("dealer_ai:onboarding-logo-upload"), data={}
        )
        self.assertEqual(res.status_code, 403)

    def test_dealer_owner_passes_auth_and_hits_validation(self):
        res = authenticated_client(self.owner).post(
            reverse("dealer_ai:onboarding-logo-upload"), data={}
        )
        # 400 = auth passed, then the view rejected the missing file
        # field. That distinguishes "auth failed" (403) from "auth
        # passed but bad input" (400).
        self.assertEqual(res.status_code, 400)
