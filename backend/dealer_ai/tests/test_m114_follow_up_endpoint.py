"""Milestone 11 · Increment 4 (SESSION_117) — Follow-up endpoint tests.

Locks the five endpoints in :mod:`views_follow_ups` per
``MILESTONE_11_PLANNING.md`` §7 M11.4 + §1.9.
"""

from __future__ import annotations

import datetime as dt
from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from dealer_ai.models import (
    FOLLOW_UP_TASK_STATE_COMPLETED,
    FOLLOW_UP_TASK_STATE_PENDING,
    FOLLOW_UP_TASK_STATE_SKIPPED,
    FOLLOW_UP_TEMPLATE_1WK,
    FOLLOW_UP_TEMPLATE_30DAY,
    ROLE_ADVISOR,
    ROLE_DEALER_OWNER,
    ROLE_SALES_MANAGER,
    CustomerLead,
    Dealership,
    FollowUpCadence,
    FollowUpTask,
)
from dealer_ai.services.follow_ups import start_cadence
from dealer_ai.services.tenancy import get_default_dealership

from ._auth_helpers import authenticated_client, make_membership, make_user


CADENCE_CREATE = "dealer_ai:admin-follow-up-cadence-create"
CADENCE_PAUSE = "dealer_ai:admin-follow-up-cadence-pause"
TASK_LIST = "dealer_ai:admin-follow-up-task-list"
TASK_COMPLETE = "dealer_ai:admin-follow-up-task-complete"
TASK_SKIP = "dealer_ai:admin-follow-up-task-skip"


def _post(client, url, body):
    return client.post(url, body, format="json")


class CadenceCreateAuthTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Auth Lead"
        )
        self.body = {"lead_id": self.lead.pk, "template": FOLLOW_UP_TEMPLATE_1WK}

    def test_unauthenticated_returns_401_or_403(self) -> None:
        response = APIClient().post(
            reverse(CADENCE_CREATE), self.body, format="json"
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_forbidden(self) -> None:
        user = make_user(username="fu-ep-adv")
        make_membership(user, self.dealership, ROLE_ADVISOR)
        response = _post(
            authenticated_client(user), reverse(CADENCE_CREATE), self.body
        )
        self.assertEqual(response.status_code, 403)


class CadenceCreateHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Happy Lead"
        )
        self.user = make_user(username="fu-ep-sm")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_sales_manager_201_and_response_shape(self) -> None:
        response = _post(
            self.client,
            reverse(CADENCE_CREATE),
            {"lead_id": self.lead.pk, "template": FOLLOW_UP_TEMPLATE_30DAY},
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()["cadence"]
        for key in (
            "id",
            "lead_id",
            "dealership_id",
            "template",
            "started_at",
            "is_active",
            "task_count",
            "created_at",
            "updated_at",
        ):
            self.assertIn(key, body)
        self.assertTrue(body["is_active"])
        self.assertGreater(body["task_count"], 0)

    def test_dealer_owner_201(self) -> None:
        owner = make_user(username="fu-ep-owner")
        make_membership(owner, self.dealership, ROLE_DEALER_OWNER)
        response = _post(
            authenticated_client(owner),
            reverse(CADENCE_CREATE),
            {"lead_id": self.lead.pk, "template": FOLLOW_UP_TEMPLATE_1WK},
        )
        self.assertEqual(response.status_code, 201)


class CadenceCreateErrorMappingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="fu-ep-err-other", name="FU EP Err Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Local"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.user = make_user(username="fu-ep-em")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)

    def test_cross_tenant_lead_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CADENCE_CREATE),
            {
                "lead_id": self.cross_lead.pk,
                "template": FOLLOW_UP_TEMPLATE_1WK,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_duplicate_active_returns_409(self) -> None:
        _post(
            self.client,
            reverse(CADENCE_CREATE),
            {"lead_id": self.lead.pk, "template": FOLLOW_UP_TEMPLATE_1WK},
        )
        response = _post(
            self.client,
            reverse(CADENCE_CREATE),
            {"lead_id": self.lead.pk, "template": FOLLOW_UP_TEMPLATE_1WK},
        )
        self.assertEqual(response.status_code, 409)

    def test_invalid_template_returns_400(self) -> None:
        response = _post(
            self.client,
            reverse(CADENCE_CREATE),
            {"lead_id": self.lead.pk, "template": "quarterly"},
        )
        self.assertEqual(response.status_code, 400)


class CadencePauseEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Pause Lead"
        )
        self.user = make_user(username="fu-ep-pause")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        self.cadence = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )

    def test_pause_happy(self) -> None:
        response = _post(
            self.client,
            reverse(CADENCE_PAUSE, kwargs={"pk": self.cadence.pk}),
            {},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["cadence"]["is_active"])

    def test_pause_nonexistent_returns_404(self) -> None:
        response = _post(
            self.client,
            reverse(CADENCE_PAUSE, kwargs={"pk": 999_999}),
            {},
        )
        self.assertEqual(response.status_code, 404)


class TaskTransitionEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Task Lead"
        )
        self.user = make_user(username="fu-ep-task")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        cadence = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        self.task = cadence.tasks.first()

    def test_complete_task_happy(self) -> None:
        response = _post(
            self.client,
            reverse(TASK_COMPLETE, kwargs={"pk": self.task.pk}),
            {"notes": "Reached customer, scheduled test drive."},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["task"]
        self.assertEqual(body["state"], FOLLOW_UP_TASK_STATE_COMPLETED)
        self.assertEqual(body["completed_by_user_id"], self.user.id)
        self.assertIn("scheduled", body["notes"])

    def test_skip_task_happy(self) -> None:
        response = _post(
            self.client,
            reverse(TASK_SKIP, kwargs={"pk": self.task.pk}),
            {"notes": "Opted out."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["task"]["state"], FOLLOW_UP_TASK_STATE_SKIPPED
        )

    def test_terminal_re_complete_returns_409(self) -> None:
        _post(
            self.client,
            reverse(TASK_COMPLETE, kwargs={"pk": self.task.pk}),
            {},
        )
        response = _post(
            self.client,
            reverse(TASK_COMPLETE, kwargs={"pk": self.task.pk}),
            {},
        )
        self.assertEqual(response.status_code, 409)


class TaskListEndpointTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="List Lead"
        )
        self.user = make_user(username="fu-ep-list")
        make_membership(self.user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(self.user)
        start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_30DAY,
        )

    def test_task_list_default_returns_all_pending(self) -> None:
        response = self.client.get(reverse(TASK_LIST))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["count"], 0)
        for task in body["results"]:
            self.assertEqual(task["state"], FOLLOW_UP_TASK_STATE_PENDING)

    def test_task_list_state_filter(self) -> None:
        response = self.client.get(
            reverse(TASK_LIST) + f"?state={FOLLOW_UP_TASK_STATE_COMPLETED}"
        )
        self.assertEqual(response.status_code, 200)
        # No tasks completed yet — empty result.
        self.assertEqual(response.json()["count"], 0)

    def test_task_list_due_before_filter(self) -> None:
        # 5 days out — should only include tasks due in the first 5
        # days (all templates seed at least one such task). urlencode
        # the ISO string so the trailing ``+00:00`` timezone offset
        # is percent-encoded (raw ``+`` in a URL parses as a space).
        cutoff = (timezone.now() + dt.timedelta(days=5)).isoformat()
        query = urlencode({"due_before": cutoff})
        response = self.client.get(reverse(TASK_LIST) + f"?{query}")
        self.assertEqual(response.status_code, 200)
        for task in response.json()["results"]:
            due = dt.datetime.fromisoformat(task["due_at"])
            self.assertLessEqual(due, timezone.now() + dt.timedelta(days=5))
