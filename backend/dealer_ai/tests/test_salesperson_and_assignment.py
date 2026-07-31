"""Manager Phase 4: Salesperson model + lead assignment + admin endpoints."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import CustomerLead, Salesperson
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_user,
    sales_manager_client_at_default,
)


def _make_advisor(slug: str = "maria-cortez", **extra) -> Salesperson:
    defaults = {
        "name": "Maria Cortez",
        "title": "Senior Truck Specialist",
        "email": "maria@example.com",
        "phone": "(405) 555-1000",
        "photo_url": "https://example.com/maria.jpg",
        "specialties": ["F-150", "Trucks"],
        "is_active": True,
    }
    defaults.update(extra)
    return Salesperson.objects.create(slug=slug, **defaults)


def _make_lead(name: str = "Test Lead", **extra) -> CustomerLead:
    return CustomerLead.objects.create(name=name, **extra)


class SalespersonModelTests(TestCase):
    def test_unique_slug(self):
        _make_advisor(slug="dup")
        with self.assertRaises(Exception):
            _make_advisor(slug="dup", name="Other")

    def test_str_includes_inactive_marker(self):
        active = _make_advisor(slug="a", name="Active")
        inactive = _make_advisor(slug="b", name="Inactive", is_active=False)
        self.assertEqual(str(active), "Active")
        self.assertIn("inactive", str(inactive).lower())

    def test_default_ordering_active_first_then_name(self):
        b = _make_advisor(slug="b", name="Bob", is_active=False)
        a = _make_advisor(slug="a", name="Alice")
        c = _make_advisor(slug="c", name="Carol")
        ordered = list(Salesperson.objects.all())
        # Active first, then name asc; inactive last regardless of name.
        self.assertEqual(ordered, [a, c, b])


class AssignmentEndpointTests(TestCase):
    def setUp(self):
        self.client = sales_manager_client_at_default()
        self.maria = _make_advisor(slug="maria-cortez")
        self.dave = _make_advisor(
            slug="dave-okafor", name="Dave Okafor", title="New-Vehicle Advisor"
        )
        self.inactive = _make_advisor(
            slug="inactive-staff", name="Inactive Staff", is_active=False
        )
        self.lead = _make_lead(name="Casey Morales", urgency="this_week")

    def test_assign_sets_assigned_to_and_assigned_at(self):
        url = reverse("dealer_ai:admin-lead-assign", args=[self.lead.pk])
        res = self.client.post(
            url,
            data={"salesperson_id": self.maria.pk},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["assigned_to"]["slug"], "maria-cortez")
        self.assertIsNotNone(data["assigned_at"])

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.assigned_to, self.maria)
        self.assertIsNotNone(self.lead.assigned_at)

    def test_unassign_with_null_clears_fields(self):
        self.lead.assigned_to = self.maria
        self.lead.save()
        url = reverse("dealer_ai:admin-lead-assign", args=[self.lead.pk])
        res = self.client.post(
            url,
            data={"salesperson_id": None},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNone(data["assigned_to"])
        self.assertIsNone(data["assigned_at"])

    def test_reassign_overwrites_cleanly(self):
        self.lead.assigned_to = self.maria
        self.lead.save()
        url = reverse("dealer_ai:admin-lead-assign", args=[self.lead.pk])
        res = self.client.post(
            url,
            data={"salesperson_id": self.dave.pk},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["assigned_to"]["slug"], "dave-okafor")

    def test_assign_to_inactive_advisor_returns_400(self):
        url = reverse("dealer_ai:admin-lead-assign", args=[self.lead.pk])
        res = self.client.post(
            url,
            data={"salesperson_id": self.inactive.pk},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_assign_unknown_salesperson_returns_400(self):
        url = reverse("dealer_ai:admin-lead-assign", args=[self.lead.pk])
        res = self.client.post(
            url,
            data={"salesperson_id": 999_999},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_assign_unknown_lead_returns_404(self):
        url = reverse("dealer_ai:admin-lead-assign", args=[999_999])
        res = self.client.post(
            url,
            data={"salesperson_id": self.maria.pk},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_deactivating_salesperson_keeps_lead_assignment(self):
        # Phase 4 decision #1: deactivating an advisor must NOT auto-unassign.
        self.lead.assigned_to = self.maria
        self.lead.save()
        self.maria.is_active = False
        self.maria.save()
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.assigned_to, self.maria)


class SalespeopleEndpointTests(TestCase):
    def setUp(self):
        self.client = sales_manager_client_at_default()
        self.maria = _make_advisor(slug="maria-cortez")
        self.inactive = _make_advisor(
            slug="inactive-staff", name="Inactive Staff", is_active=False
        )

    def test_admin_list_includes_inactive(self):
        url = reverse("dealer_ai:admin-salespeople")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        slugs = {row["slug"] for row in res.json()["results"]}
        self.assertIn("maria-cortez", slugs)
        self.assertIn("inactive-staff", slugs)

    def test_admin_list_active_filter(self):
        url = reverse("dealer_ai:admin-salespeople")
        res = self.client.get(url + "?active=true")
        self.assertEqual(res.status_code, 200)
        slugs = {row["slug"] for row in res.json()["results"]}
        self.assertIn("maria-cortez", slugs)
        self.assertNotIn("inactive-staff", slugs)

    def test_public_list_active_only_and_no_pii(self):
        url = reverse("dealer_ai:salespeople-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        slugs = {row["slug"] for row in results}
        self.assertIn("maria-cortez", slugs)
        self.assertNotIn("inactive-staff", slugs)
        for row in results:
            self.assertNotIn("phone", row)
            self.assertNotIn("email", row)
            self.assertNotIn("bio", row)

    def test_public_detail_404_for_inactive(self):
        url = reverse(
            "dealer_ai:salespeople-detail", args=["inactive-staff"]
        )
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)


class AdvisorWorkspaceEndpointTests(TestCase):
    """Milestone 1 · Increment 4C — advisor workspace happy paths under
    real authorization. Negative-path / cross-tenant coverage lives in
    ``test_advisor_workspace_auth.py``; this class exercises the
    business behavior that must still hold once the correct advisor
    has been authorized (own leads only, inactive-advisor lifecycle).
    """

    def setUp(self):
        self.maria = _make_advisor(slug="maria-cortez")
        # Link Maria to an auth user so IsAdvisorForSlug passes for her.
        self.maria_user = make_user(username="maria")
        self.maria.user = self.maria_user
        self.maria.save(update_fields=["user"])
        self.client = authenticated_client(self.maria_user)

        self.dave = _make_advisor(slug="dave-okafor", name="Dave Okafor")
        self.open_lead = _make_lead(
            name="Open One",
            urgency="this_week",
            assigned_to=self.maria,
            handed_off=False,
        )
        self.contacted_lead = _make_lead(
            name="Contacted One",
            urgency="this_week",
            assigned_to=self.maria,
            handed_off=True,
        )
        # A lead assigned to a different advisor — must NOT show up.
        self.dave_lead = _make_lead(
            name="Dave's Lead",
            urgency="this_week",
            assigned_to=self.dave,
            handed_off=False,
        )

    def test_workspace_returns_only_assigned_leads(self):
        url = reverse("dealer_ai:advisor-workspace", args=["maria-cortez"])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["salesperson"]["slug"], "maria-cortez")
        open_names = {l["name"] for l in data["open_leads"]}
        contacted_names = {l["name"] for l in data["contacted_leads"]}
        self.assertEqual(open_names, {"Open One"})
        self.assertEqual(contacted_names, {"Contacted One"})
        self.assertNotIn("Dave's Lead", open_names | contacted_names)

    def test_workspace_deactivated_advisor_is_not_leaked_to_owners(self):
        # Under real authorization a deactivated advisor's URL is
        # indistinguishable from an unknown slug — both return 403 to
        # an authenticated caller. The pre-4C behavior returned 404
        # via slug-obscurity, which leaked existence; the new behavior
        # aligns with the "no information leakage via differential
        # status codes" invariant locked in
        # test_advisor_workspace_auth.
        from dealer_ai.models import ROLE_DEALER_OWNER, UserDealershipRole

        default = get_default_dealership()
        gone = _make_advisor(slug="gone", name="Gone", is_active=False)
        _make_lead(name="Old Lead", assigned_to=gone, handed_off=False)
        owner = make_user(username="owner-for-gone")
        UserDealershipRole.objects.create(
            user=owner, dealership=default, role=ROLE_DEALER_OWNER
        )
        client = authenticated_client(owner)
        url = reverse("dealer_ai:advisor-workspace", args=["gone"])
        res = client.get(url)
        self.assertEqual(res.status_code, 403)


class PipelinePayloadIncludesAssignedToTests(TestCase):
    def test_pipeline_lead_includes_assigned_to_field(self):
        from dealer_ai.services.pipeline import pipeline_snapshot

        maria = _make_advisor(slug="maria-cortez")
        unassigned = _make_lead(name="Unassigned Lead", urgency="this_week")
        assigned = _make_lead(
            name="Assigned Lead",
            urgency="this_week",
            assigned_to=maria,
        )
        snap = pipeline_snapshot()
        all_leads = []
        for stage in snap["stages"]:
            for l in stage["leads"]:
                all_leads.append(l)

        by_id = {l["id"]: l for l in all_leads}
        self.assertIn("assigned_to", by_id[unassigned.pk])
        self.assertIsNone(by_id[unassigned.pk]["assigned_to"])
        self.assertEqual(
            by_id[assigned.pk]["assigned_to"]["slug"], "maria-cortez"
        )
