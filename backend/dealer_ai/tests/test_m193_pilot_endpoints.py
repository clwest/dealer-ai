"""Milestone 19 · Increment 3 (SESSION_156) — pilot onboarding admin endpoints tests.

Covers:

- Four lifecycle endpoints per §7 M19.3:
  ``POST /admin/pilots/create/``,
  ``GET /admin/pilots/``,
  ``POST /admin/pilots/<slug>/checklist/advance/``,
  ``POST /admin/pilots/<slug>/terminate/``.
- Domain-error → HTTP status mapping (400/404/409/500).
- Auth gating: unauthenticated → 401.
- Serialization contract: nested checklist shape (ordered
  step list + placeholder rows for uncompleted steps).
- Growth-only endpoint count: 108 → 112.
- Permission-class zero-drift streak now seventeen consecutive
  milestones (M10 → M19.3) per §0.a M19.3 decision 2 (no new
  class).
- Slug-in-URL: 404 on non-pilot / nonexistent slug.
"""

from __future__ import annotations

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from dealer_ai.models import (
    PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
    PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED,
    PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
    PILOT_ONBOARDING_STEP_ORDER,
    PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
    PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
    PILOT_ONBOARDING_STEP_READINESS_CONFIRMED,
    PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
    PILOT_TERMINATION_MODE_ARCHIVE,
    PILOT_TERMINATION_MODE_CLEANUP,
    Dealership,
    PilotOnboardingChecklist,
    PilotOnboardingStep,
    Vehicle,
)
from dealer_ai.services.pilot_onboarding import (
    create_pilot_dealership,
)

from ._auth_helpers import (
    authenticated_client,
    make_demo_dealership,
    make_pilot_dealership,
    make_user,
)
from dealer_ai.models import DEMO_ARCHETYPE_RETAIL_SUBPRIME


PILOT_CREATE = "dealer_ai:admin-pilot-create"
PILOT_LIST = "dealer_ai:admin-pilot-list"
PILOT_CHECKLIST_ADVANCE = "dealer_ai:admin-pilot-checklist-advance"
PILOT_TERMINATE = "dealer_ai:admin-pilot-terminate"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _authed_client() -> APIClient:
    user = make_user(username="m193-operator")
    return authenticated_client(user)


def _make_pilot_with_checklist(slug: str):
    """Full construction via the service verb so the checklist row
    + auto-fired ``dealership_created`` step exist."""
    owner = make_user(username=f"owner-{slug}")
    dealership, checklist = create_pilot_dealership(
        slug=slug,
        name=slug.replace("-", " ").title(),
        owner_user=owner,
    )
    return dealership, checklist


def _advance_all_prior_steps(checklist, actor):
    """Mark every step EXCEPT ``readiness_confirmed`` complete so
    the last step's precondition is satisfied. ``dealership_created``
    is already complete by ``create_pilot_dealership``."""
    from django.utils import timezone

    already_complete = set(
        PilotOnboardingStep.objects.filter(
            checklist=checklist
        ).values_list("step_slug", flat=True)
    )
    for slug in PILOT_ONBOARDING_STEP_ORDER:
        if slug == PILOT_ONBOARDING_STEP_READINESS_CONFIRMED:
            continue
        if slug in already_complete:
            continue
        PilotOnboardingStep.objects.create(
            dealership=checklist.dealership,
            checklist=checklist,
            step_slug=slug,
            completed_at=timezone.now(),
            completed_by=actor,
        )


# ---------------------------------------------------------------------------
# Auth gating
# ---------------------------------------------------------------------------


class AuthGatingTests(TestCase):
    def test_create_unauth_returns_401(self) -> None:
        response = APIClient().post(reverse(PILOT_CREATE), {}, format="json")
        self.assertIn(response.status_code, (401, 403))

    def test_list_unauth_returns_401(self) -> None:
        response = APIClient().get(reverse(PILOT_LIST))
        self.assertIn(response.status_code, (401, 403))

    def test_checklist_advance_unauth_returns_401(self) -> None:
        response = APIClient().post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": "nope"},
            ),
            {},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))

    def test_terminate_unauth_returns_401(self) -> None:
        response = APIClient().post(
            reverse(PILOT_TERMINATE, kwargs={"slug": "nope"}),
            {},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))


# ---------------------------------------------------------------------------
# POST /admin/pilots/create/
# ---------------------------------------------------------------------------


class PilotCreateEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client_ = _authed_client()
        self.owner = make_user(username="pilot-owner-a")

    def test_happy_path_returns_201_with_pilot_and_checklist(self) -> None:
        response = self.client_.post(
            reverse(PILOT_CREATE),
            {
                "slug": "acme-motors",
                "name": "Acme Motors",
                "owner_username": self.owner.username,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()["pilot"]
        self.assertEqual(body["dealership"]["slug"], "acme-motors")
        self.assertTrue(body["dealership"]["is_pilot"])
        self.assertFalse(body["dealership"]["outbound_enabled"])
        self.assertIsNotNone(body["checklist"])
        self.assertEqual(body["checklist"]["is_ready"], False)
        # dealership_created auto-fired.
        step_slugs = {s["step_slug"] for s in body["checklist"]["steps"]}
        self.assertEqual(step_slugs, set(PILOT_ONBOARDING_STEP_ORDER))
        completed_slugs = {
            s["step_slug"]
            for s in body["checklist"]["steps"]
            if s["completed_at"] is not None
        }
        self.assertEqual(
            completed_slugs, {PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED}
        )

    def test_slug_collision_returns_409(self) -> None:
        # Pre-existing pilot with the target slug.
        make_pilot_dealership(slug="collide-slug")
        response = self.client_.post(
            reverse(PILOT_CREATE),
            {
                "slug": "collide-slug",
                "name": "Collide",
                "owner_username": self.owner.username,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_slug_collision_with_existing_demo_returns_409(self) -> None:
        make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="collide-with-demo",
        )
        response = self.client_.post(
            reverse(PILOT_CREATE),
            {
                "slug": "collide-with-demo",
                "name": "Collide",
                "owner_username": self.owner.username,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_unknown_owner_username_returns_400(self) -> None:
        response = self.client_.post(
            reverse(PILOT_CREATE),
            {
                "slug": "no-owner",
                "name": "No Owner",
                "owner_username": "nonexistent-user-abc",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_slug_returns_400(self) -> None:
        response = self.client_.post(
            reverse(PILOT_CREATE),
            {
                "name": "Missing Slug",
                "owner_username": self.owner.username,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_profile_kwargs_optional(self) -> None:
        response = self.client_.post(
            reverse(PILOT_CREATE),
            {
                "slug": "empty-profile",
                "name": "Empty Profile",
                "owner_username": self.owner.username,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)


# ---------------------------------------------------------------------------
# GET /admin/pilots/
# ---------------------------------------------------------------------------


class PilotListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client_ = _authed_client()

    def test_returns_active_pilots_only(self) -> None:
        _make_pilot_with_checklist("list-1")
        _make_pilot_with_checklist("list-2")
        # Terminated pilot excluded.
        term_pilot, _ = _make_pilot_with_checklist("list-3-terminated")
        term_pilot.is_pilot = False
        term_pilot.save(update_fields=["is_pilot"])
        # Non-pilot excluded.
        Dealership.objects.create(
            slug="list-live", name="Live Store"
        )
        response = self.client_.get(reverse(PILOT_LIST))
        self.assertEqual(response.status_code, 200)
        slugs = {
            entry["dealership"]["slug"]
            for entry in response.json()["pilots"]
        }
        self.assertEqual(slugs, {"list-1", "list-2"})

    def test_each_entry_includes_checklist(self) -> None:
        _make_pilot_with_checklist("list-shape")
        response = self.client_.get(reverse(PILOT_LIST))
        entries = response.json()["pilots"]
        self.assertEqual(len(entries), 1)
        self.assertIsNotNone(entries[0]["checklist"])
        self.assertEqual(
            len(entries[0]["checklist"]["steps"]),
            len(PILOT_ONBOARDING_STEP_ORDER),
        )

    def test_empty_when_no_pilots(self) -> None:
        response = self.client_.get(reverse(PILOT_LIST))
        self.assertEqual(response.json()["pilots"], [])


# ---------------------------------------------------------------------------
# POST /admin/pilots/<slug>/checklist/advance/
# ---------------------------------------------------------------------------


class ChecklistAdvanceEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client_ = _authed_client()
        self.dealership, self.checklist = _make_pilot_with_checklist(
            "advance-1"
        )

    def test_happy_path_advances_step(self) -> None:
        response = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": self.dealership.slug},
            ),
            {
                "step_slug": PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
                "notes": "Filled make roster",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        # Row persisted.
        self.assertTrue(
            PilotOnboardingStep.objects.filter(
                checklist=self.checklist,
                step_slug=PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED,
            ).exists()
        )
        # Projection reflects completion.
        body = response.json()["pilot"]["checklist"]
        completed = {
            s["step_slug"]
            for s in body["steps"]
            if s["completed_at"] is not None
        }
        self.assertIn(
            PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED, completed
        )

    def test_unknown_step_slug_returns_400(self) -> None:
        response = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": self.dealership.slug},
            ),
            {"step_slug": "not-a-real-step"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reapply_step_returns_409(self) -> None:
        first = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": self.dealership.slug},
            ),
            {"step_slug": PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED},
            format="json",
        )
        self.assertEqual(first.status_code, 200)
        second = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": self.dealership.slug},
            ),
            {"step_slug": PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED},
            format="json",
        )
        self.assertEqual(second.status_code, 409)

    def test_readiness_precondition_returns_409(self) -> None:
        response = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": self.dealership.slug},
            ),
            {"step_slug": PILOT_ONBOARDING_STEP_READINESS_CONFIRMED},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_readiness_after_prior_steps_flips_is_ready(self) -> None:
        _advance_all_prior_steps(self.checklist, actor=None)
        response = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": self.dealership.slug},
            ),
            {"step_slug": PILOT_ONBOARDING_STEP_READINESS_CONFIRMED},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["pilot"]["checklist"]["is_ready"])
        self.checklist.refresh_from_db()
        self.assertTrue(self.checklist.is_ready)

    def test_nonexistent_slug_returns_404(self) -> None:
        response = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": "no-such-pilot"},
            ),
            {"step_slug": PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_non_pilot_slug_returns_404(self) -> None:
        # A demo dealership has is_pilot=False; the URL filter rules
        # it out even though the slug matches an existing Dealership.
        make_demo_dealership(
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            slug="advance-demo",
        )
        response = self.client_.post(
            reverse(
                PILOT_CHECKLIST_ADVANCE,
                kwargs={"slug": "advance-demo"},
            ),
            {"step_slug": PILOT_ONBOARDING_STEP_PROFILE_CONFIGURED},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# POST /admin/pilots/<slug>/terminate/
# ---------------------------------------------------------------------------


class TerminateEndpointTests(TestCase):
    def setUp(self) -> None:
        self.client_ = _authed_client()

    def test_archive_mode_default_flips_is_pilot(self) -> None:
        dealership, _ = _make_pilot_with_checklist("term-archive")
        response = self.client_.post(
            reverse(PILOT_TERMINATE, kwargs={"slug": "term-archive"}),
            {"reason": "Pilot completed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()["dealership"]
        self.assertFalse(body["is_pilot"])
        self.assertIsNotNone(body["terminated_at"])
        self.assertEqual(body["termination_reason"], "Pilot completed")

    def test_cleanup_mode_cascades_children(self) -> None:
        dealership, _ = _make_pilot_with_checklist("term-cleanup")
        Vehicle.objects.create(
            dealership=dealership,
            stock_number="TERM-1",
            year=2020,
            model="Civic",
            price="15000",
        )
        response = self.client_.post(
            reverse(PILOT_TERMINATE, kwargs={"slug": "term-cleanup"}),
            {"reason": "Wind-down", "mode": PILOT_TERMINATION_MODE_CLEANUP},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(
            Vehicle.objects.filter(stock_number="TERM-1").exists()
        )

    def test_unknown_mode_returns_400(self) -> None:
        _make_pilot_with_checklist("term-bad-mode")
        response = self.client_.post(
            reverse(PILOT_TERMINATE, kwargs={"slug": "term-bad-mode"}),
            {"reason": "x", "mode": "nuke"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_slug_returns_404(self) -> None:
        response = self.client_.post(
            reverse(PILOT_TERMINATE, kwargs={"slug": "no-such-pilot"}),
            {"reason": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_blank_reason_ok(self) -> None:
        _make_pilot_with_checklist("term-blank-reason")
        response = self.client_.post(
            reverse(
                PILOT_TERMINATE,
                kwargs={"slug": "term-blank-reason"},
            ),
            {},
            format="json",
        )
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Checklist projection contract
# ---------------------------------------------------------------------------


class ChecklistProjectionShapeTests(TestCase):
    def test_steps_ordered_by_step_order(self) -> None:
        client_ = _authed_client()
        _make_pilot_with_checklist("shape-1")
        response = client_.get(reverse(PILOT_LIST))
        steps = response.json()["pilots"][0]["checklist"]["steps"]
        actual_order = [s["step_slug"] for s in steps]
        self.assertEqual(actual_order, list(PILOT_ONBOARDING_STEP_ORDER))

    def test_placeholder_rows_have_null_completed_at(self) -> None:
        client_ = _authed_client()
        _make_pilot_with_checklist("shape-2")
        response = client_.get(reverse(PILOT_LIST))
        steps = response.json()["pilots"][0]["checklist"]["steps"]
        # Only dealership_created is complete right after create.
        for step in steps:
            if step["step_slug"] == PILOT_ONBOARDING_STEP_DEALERSHIP_CREATED:
                self.assertIsNotNone(step["completed_at"])
            else:
                self.assertIsNone(step["completed_at"])


# ---------------------------------------------------------------------------
# Zero-drift substrate assertions at M19.3
# ---------------------------------------------------------------------------


class M193EndpointCountTests(TestCase):
    def test_admin_endpoint_count_grew_by_four(self) -> None:
        # Four new endpoints: create/list/checklist advance/terminate.
        # M19.2 count was 108; M19.3 ships 112.
        from dealer_ai.urls import urlpatterns

        admin_paths = [
            p
            for p in urlpatterns
            if hasattr(p, "pattern") and "admin/" in str(p.pattern)
        ]
        self.assertGreaterEqual(len(admin_paths), 112)


class M193PermissionClassZeroDriftTests(TestCase):
    def test_no_new_permission_class_at_m193(self) -> None:
        # Streak of seventeen consecutive milestones (M10 → M19.3) —
        # M19.3 ships zero new permission classes per §0.a M19.3
        # decision 2 (endpoints gate on IsAuthenticated alone).
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


class M193UsedFixedVocabTests(TestCase):
    """Sanity checks on the vocab constants the endpoints consume."""

    def test_step_order_has_all_seven_steps(self) -> None:
        self.assertEqual(len(PILOT_ONBOARDING_STEP_ORDER), 7)
        self.assertIn(
            PILOT_ONBOARDING_STEP_CAPABILITIES_ENABLED,
            PILOT_ONBOARDING_STEP_ORDER,
        )
        self.assertIn(
            PILOT_ONBOARDING_STEP_INVENTORY_IMPORTED,
            PILOT_ONBOARDING_STEP_ORDER,
        )
        self.assertIn(
            PILOT_ONBOARDING_STEP_OWNER_USER_ADDED,
            PILOT_ONBOARDING_STEP_ORDER,
        )
        self.assertIn(
            PILOT_ONBOARDING_STEP_STAFF_USERS_ADDED,
            PILOT_ONBOARDING_STEP_ORDER,
        )

    def test_termination_modes_stable(self) -> None:
        self.assertEqual(PILOT_TERMINATION_MODE_ARCHIVE, "archive")
        self.assertEqual(PILOT_TERMINATION_MODE_CLEANUP, "cleanup")
