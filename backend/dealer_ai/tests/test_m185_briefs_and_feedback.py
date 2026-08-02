"""Milestone 18 · Increment 5 (SESSION_151) — briefs + feedback tests.

Covers per MILESTONE_18_PLANNING.md §7 M18.5:

- **Brief loader**: matrix test that every ``(archetype, role)``
  pair we expect has a markdown file that loads successfully;
  BriefNotFoundError fires for unknown archetype / unknown role /
  a role that this archetype doesn't ship (retail_subprime has
  no collector, etc.).
- **Brief content shape**: every loaded brief opens with a
  `# ...` H1 line + carries the standard section markers
  ("What happened before login" etc.) so tester UX is
  consistent across archetypes.
- **POST /admin/demo-store/feedback/**: 201 happy path with
  projection; 400 on validation failure; 403 on non-demo
  dealership; 403 on non-permitted role; tenancy scoping
  (each dealership only sees its own feedback).
- **CSV export end-to-end**: management-command exporter
  writes header + row content for real TesterFeedback rows.
- **Endpoint count**: DRF admin surface grows 107 → 108.
"""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    DEMO_ARCHETYPE_BHPH,
    DEMO_ARCHETYPE_FLOOR_PLANNED,
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    TESTER_FEEDBACK_CATEGORY_BUG,
    TESTER_FEEDBACK_CATEGORY_WILLINGNESS_TO_PAY,
    Dealership,
    TesterFeedback,
)
from dealer_ai.services.demo_store import (
    BRIEF_ROLES,
    Brief,
    BriefNotFoundError,
    get_brief,
    list_briefs,
)

from ._auth_helpers import (
    authenticated_client,
    make_demo_dealership,
    make_membership,
    make_user,
)


FEEDBACK_CREATE = "dealer_ai:admin-demo-store-feedback-create"


# ---------------------------------------------------------------------------
# Brief loader — list_briefs / get_brief
# ---------------------------------------------------------------------------


class BriefRoleVocabTests(TestCase):
    def test_role_vocab_exact_set(self) -> None:
        # Fixed-vocab lesson per M11-M17. Growth-only via append.
        self.assertEqual(
            set(BRIEF_ROLES),
            {
                "owner",
                "sales_manager",
                "recon",
                "accounting",
                "collector",
            },
        )


class ListBriefsTests(TestCase):
    def test_retail_subprime_lists_four_briefs(self) -> None:
        roles = list_briefs(DEMO_ARCHETYPE_RETAIL_SUBPRIME)
        self.assertEqual(
            set(roles),
            {"owner", "sales_manager", "recon", "accounting"},
        )

    def test_floor_planned_lists_four_briefs(self) -> None:
        roles = list_briefs(DEMO_ARCHETYPE_FLOOR_PLANNED)
        self.assertEqual(
            set(roles),
            {"owner", "sales_manager", "recon", "accounting"},
        )

    def test_bhph_lists_all_five_briefs(self) -> None:
        roles = list_briefs(DEMO_ARCHETYPE_BHPH)
        self.assertEqual(
            set(roles),
            {
                "owner",
                "sales_manager",
                "recon",
                "accounting",
                "collector",
            },
        )

    def test_unknown_archetype_raises(self) -> None:
        with self.assertRaises(BriefNotFoundError):
            list_briefs("nonexistent-archetype")


class GetBriefTests(TestCase):
    def test_load_every_expected_brief(self) -> None:
        # Matrix test: for each archetype, every listed role
        # should yield a loadable Brief with non-empty content.
        for archetype in (
            DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            DEMO_ARCHETYPE_FLOOR_PLANNED,
            DEMO_ARCHETYPE_BHPH,
        ):
            for role in list_briefs(archetype):
                brief = get_brief(archetype, role)
                self.assertIsInstance(brief, Brief)
                self.assertEqual(brief.archetype, archetype)
                self.assertEqual(brief.role, role)
                self.assertGreater(len(brief.content), 100)

    def test_unknown_role_raises(self) -> None:
        with self.assertRaises(BriefNotFoundError):
            get_brief(DEMO_ARCHETYPE_BHPH, "nonexistent-role")

    def test_retail_subprime_has_no_collector_brief(self) -> None:
        # retail_subprime has no active BHPH book, so no collector
        # brief. This asserts the intentional absence.
        with self.assertRaises(BriefNotFoundError):
            get_brief(DEMO_ARCHETYPE_RETAIL_SUBPRIME, "collector")

    def test_floor_planned_has_no_collector_brief(self) -> None:
        with self.assertRaises(BriefNotFoundError):
            get_brief(DEMO_ARCHETYPE_FLOOR_PLANNED, "collector")


class BriefContentShapeTests(TestCase):
    """Every loaded brief follows the standard structure."""

    STANDARD_MARKERS = (
        "What happened before login",
        "What you need to accomplish today",
        "intentionally incomplete",
        "shipped capabilities should help",
        "successful completion looks like",
        "Discoverable without a guided click path",
    )

    def test_every_brief_starts_with_h1(self) -> None:
        for archetype in (
            DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            DEMO_ARCHETYPE_FLOOR_PLANNED,
            DEMO_ARCHETYPE_BHPH,
        ):
            for role in list_briefs(archetype):
                brief = get_brief(archetype, role)
                first_line = brief.content.splitlines()[0]
                self.assertTrue(
                    first_line.startswith("# "),
                    f"Brief {archetype}/{role} missing H1 title. "
                    f"First line: {first_line!r}",
                )

    def test_every_brief_names_its_scenario_slug(self) -> None:
        for archetype in (
            DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            DEMO_ARCHETYPE_FLOOR_PLANNED,
            DEMO_ARCHETYPE_BHPH,
        ):
            for role in list_briefs(archetype):
                brief = get_brief(archetype, role)
                self.assertIn(
                    "Scenario slug:",
                    brief.content,
                    f"Brief {archetype}/{role} missing scenario slug",
                )

    def test_every_brief_contains_the_six_standard_markers(self) -> None:
        for archetype in (
            DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            DEMO_ARCHETYPE_FLOOR_PLANNED,
            DEMO_ARCHETYPE_BHPH,
        ):
            for role in list_briefs(archetype):
                brief = get_brief(archetype, role)
                for marker in self.STANDARD_MARKERS:
                    self.assertIn(
                        marker, brief.content,
                        f"Brief {archetype}/{role} missing standard "
                        f"marker: {marker!r}",
                    )

    def test_floor_planned_recon_names_the_overrun(self) -> None:
        brief = get_brief(DEMO_ARCHETYPE_FLOOR_PLANNED, "recon")
        self.assertIn("1,425", brief.content)
        self.assertIn("FP-01", brief.content)

    def test_bhph_accounting_names_the_11_00_detector(self) -> None:
        brief = get_brief(DEMO_ARCHETYPE_BHPH, "accounting")
        self.assertIn("11:00", brief.content)
        self.assertIn("posted_at", brief.content)


# ---------------------------------------------------------------------------
# POST /admin/demo-store/feedback/
# ---------------------------------------------------------------------------


def _sm_client(dealership: Dealership) -> APIClient:
    user = make_user(username=f"m185-sm-{dealership.slug}")
    make_membership(user, dealership, ROLE_SALES_MANAGER)
    return authenticated_client(user)


class FeedbackEndpointHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-feedback-demo",
        )
        self.client_ = _sm_client(self.dealership)

    def test_post_creates_row_and_returns_201_with_projection(self) -> None:
        response = self.client_.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "Alexis Testworth",
                "scenario_slug": "bhph_collector_daily_book",
                "category": TESTER_FEEDBACK_CATEGORY_WILLINGNESS_TO_PAY,
                "note": "I would pay for the promise-to-pay surface.",
                "referenced_route": "/dealer-ai-manager",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["tester_feedback"]
        self.assertEqual(body["tester_name"], "Alexis Testworth")
        self.assertEqual(body["category"], "willingness_to_pay")
        # Row persisted.
        self.assertEqual(
            TesterFeedback.objects.filter(
                dealership=self.dealership
            ).count(),
            1,
        )

    def test_post_accepts_blank_referenced_route(self) -> None:
        response = self.client_.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "Jamie Demoson",
                "scenario_slug": "off_route_feedback",
                "category": TESTER_FEEDBACK_CATEGORY_BUG,
                "note": "verbal observation during walk-through",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["tester_feedback"]
        self.assertEqual(body["referenced_route"], "")


class FeedbackEndpointGuardTests(TestCase):
    def test_missing_category_returns_400(self) -> None:
        dealership = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-guard-missing",
        )
        client = _sm_client(dealership)
        response = client.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "T",
                "scenario_slug": "s",
                "note": "n",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_category_returns_400(self) -> None:
        dealership = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-guard-bad-cat",
        )
        client = _sm_client(dealership)
        response = client.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "T",
                "scenario_slug": "s",
                "category": "not-a-real-category",
                "note": "n",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_non_demo_dealership_returns_403(self) -> None:
        # Use the migration-seeded default dealership (is_demo=False).
        from dealer_ai.services.tenancy import get_default_dealership

        real = get_default_dealership()
        self.assertFalse(real.is_demo)
        client = _sm_client(real)
        response = client.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "T",
                "scenario_slug": "s",
                "category": TESTER_FEEDBACK_CATEGORY_BUG,
                "note": "should not succeed",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("demo", response.json()["detail"].lower())

    def test_non_permitted_role_returns_403(self) -> None:
        dealership = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-guard-advisor",
        )
        advisor = make_user(username="m185-advisor")
        make_membership(advisor, dealership, ROLE_ADVISOR)
        client = authenticated_client(advisor)
        response = client.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "T",
                "scenario_slug": "s",
                "category": TESTER_FEEDBACK_CATEGORY_BUG,
                "note": "advisor role blocked",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class FeedbackTenantScopingTests(TestCase):
    def test_dealership_only_sees_own_feedback(self) -> None:
        d1 = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-scope-a",
        )
        d2 = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-scope-b",
        )
        c1 = _sm_client(d1)
        c2 = _sm_client(d2)
        c1.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "Alexis Testworth",
                "scenario_slug": "s",
                "category": TESTER_FEEDBACK_CATEGORY_BUG,
                "note": "d1 feedback",
            },
            format="json",
        )
        c2.post(
            reverse(FEEDBACK_CREATE),
            {
                "tester_name": "Jamie Demoson",
                "scenario_slug": "s",
                "category": TESTER_FEEDBACK_CATEGORY_BUG,
                "note": "d2 feedback",
            },
            format="json",
        )
        self.assertEqual(
            TesterFeedback.objects.filter(dealership=d1).count(), 1
        )
        self.assertEqual(
            TesterFeedback.objects.filter(dealership=d2).count(), 1
        )
        d1_notes = list(
            TesterFeedback.objects.filter(
                dealership=d1
            ).values_list("note", flat=True)
        )
        self.assertEqual(d1_notes, ["d1 feedback"])


# ---------------------------------------------------------------------------
# CSV export end-to-end
# ---------------------------------------------------------------------------


class CsvExportEndToEndTests(TestCase):
    def test_export_reflects_endpoint_submitted_feedback(self) -> None:
        dealership = make_demo_dealership(
            archetype=DEMO_ARCHETYPE_BHPH,
            slug="m185-export-e2e",
        )
        client = _sm_client(dealership)
        # Submit two rows via the endpoint.
        for i, category in enumerate((
            TESTER_FEEDBACK_CATEGORY_BUG,
            TESTER_FEEDBACK_CATEGORY_WILLINGNESS_TO_PAY,
        )):
            client.post(
                reverse(FEEDBACK_CREATE),
                {
                    "tester_name": f"Tester {i}",
                    "scenario_slug": f"scenario-{i}",
                    "category": category,
                    "note": f"note {i}",
                    "referenced_route": f"/route-{i}",
                },
                format="json",
            )
        # Export via CLI.
        out = StringIO()
        call_command(
            "demo_store",
            "export_feedback",
            f"--dealership={dealership.slug}",
            stdout=out,
        )
        csv_text = out.getvalue()
        self.assertIn("tester_name", csv_text)  # header
        self.assertIn("Tester 0", csv_text)
        self.assertIn("Tester 1", csv_text)
        self.assertIn("willingness_to_pay", csv_text)


# ---------------------------------------------------------------------------
# Endpoint count — DRF admin surface grows 107 → 108
# ---------------------------------------------------------------------------


class M185EndpointCountTests(TestCase):
    def test_endpoint_count_at_least_one_hundred_eight(self) -> None:
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 108)


# ---------------------------------------------------------------------------
# Zero-drift permission-class posture
# ---------------------------------------------------------------------------


class M185PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m185(self) -> None:
        # Zero-drift streak extends to fourteen consecutive
        # milestones (M10 → M18.5). Exact-set equality per lesson.
        from dealer_ai import permissions

        permission_classes = {
            name
            for name in dir(permissions)
            if not name.startswith("_")
            and name != "IsAuthenticated"
            and isinstance(getattr(permissions, name), type)
            and issubclass(
                getattr(permissions, name),
                __import__(
                    "rest_framework.permissions",
                    fromlist=["BasePermission"],
                ).BasePermission,
            )
            and getattr(permissions, name).__module__
            == "dealer_ai.permissions"
        }
        self.assertEqual(
            permission_classes,
            {
                "IsAdvisorForSlug",
                "IsDealerOwnerForAdvisorSlug",
                "IsSalesManagerOrOwnerAtActiveDealership",
                "IsReconManagerSalesManagerOrOwnerAtActiveDealership",
                "IsDealerOwnerAtActiveDealership",
                "IsFinanceManagerOrOwnerAtActiveDealership",
                "ReadOnly",
            },
        )
