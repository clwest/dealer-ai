"""Milestone 11 · Increment 4 (SESSION_117) — Follow-up service tests.

Locks the four verbs in :mod:`services.follow_ups` per
``MILESTONE_11_PLANNING.md`` §1.4 + §5.d Option A + SESSION_117 §0.a
M11.4 amendment.
"""

from __future__ import annotations

import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    FOLLOW_UP_TASK_STATE_COMPLETED,
    FOLLOW_UP_TASK_STATE_PENDING,
    FOLLOW_UP_TASK_STATE_SKIPPED,
    FOLLOW_UP_TEMPLATE_1WK,
    FOLLOW_UP_TEMPLATE_24HR,
    FOLLOW_UP_TEMPLATE_30DAY,
    FOLLOW_UP_TEMPLATE_6MO,
    FOLLOW_UP_TEMPLATE_90DAY,
    FOLLOW_UP_TEMPLATE_1YR,
    FOLLOW_UP_TEMPLATE_CHOICES,
    FOLLOW_UP_TEMPLATE_OFFSETS,
    CustomerLead,
    Dealership,
    FollowUpCadence,
    FollowUpTask,
)
from dealer_ai.services.follow_ups import (
    CrossTenantCadenceError,
    CrossTenantTaskError,
    DuplicateActiveCadenceError,
    TaskAlreadyTerminalError,
    UnknownTemplateError,
    complete_task,
    pause_cadence,
    skip_task,
    start_cadence,
)


User = get_user_model()


class StartCadenceTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="fu-svc-start", name="FU Svc Start"
        )
        self.other = Dealership.objects.create(
            slug="fu-svc-start-other", name="FU Svc Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Sarah"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross Sarah"
        )

    def test_happy_path_seeds_correct_task_count(self) -> None:
        cadence = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_30DAY,
        )
        self.assertTrue(cadence.is_active)
        expected = len(FOLLOW_UP_TEMPLATE_OFFSETS[FOLLOW_UP_TEMPLATE_30DAY])
        self.assertEqual(cadence.tasks.count(), expected)
        # All seeded tasks start pending.
        self.assertEqual(
            cadence.tasks.filter(state=FOLLOW_UP_TASK_STATE_PENDING).count(),
            expected,
        )

    def test_every_template_seeds_matching_offsets(self) -> None:
        for template, _ in FOLLOW_UP_TEMPLATE_CHOICES:
            with self.subTest(template=template):
                # Distinct lead per template so the duplicate-active
                # guard doesn't interfere.
                lead = CustomerLead.objects.create(
                    dealership=self.dealership, name=f"lead-{template}"
                )
                cadence = start_cadence(
                    dealership=self.dealership,
                    lead=lead,
                    template=template,
                )
                expected = len(FOLLOW_UP_TEMPLATE_OFFSETS[template])
                self.assertEqual(cadence.tasks.count(), expected)

    def test_cross_tenant_lead_raises(self) -> None:
        with self.assertRaises(CrossTenantCadenceError):
            start_cadence(
                dealership=self.dealership,
                lead=self.cross_lead,
                template=FOLLOW_UP_TEMPLATE_1WK,
            )
        self.assertEqual(
            FollowUpCadence.objects.filter(dealership=self.dealership).count(),
            0,
        )

    def test_unknown_template_raises(self) -> None:
        with self.assertRaises(UnknownTemplateError):
            start_cadence(
                dealership=self.dealership,
                lead=self.lead,
                template="quarterly-non-standard",
            )

    def test_duplicate_active_cadence_raises(self) -> None:
        start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        with self.assertRaises(DuplicateActiveCadenceError):
            start_cadence(
                dealership=self.dealership,
                lead=self.lead,
                template=FOLLOW_UP_TEMPLATE_1WK,
            )

    def test_pause_then_start_same_template_succeeds(self) -> None:
        c1 = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        pause_cadence(dealership=self.dealership, cadence=c1)
        c2 = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        self.assertNotEqual(c1.pk, c2.pk)


class TaskTransitionTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="fu-svc-trans", name="FU Svc Trans"
        )
        self.other = Dealership.objects.create(
            slug="fu-svc-trans-other", name="FU Svc Trans Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Timmy"
        )
        self.user = User.objects.create_user(username="fu-svc-user", password="x")
        self.cadence = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        self.task = self.cadence.tasks.first()
        # Cross-tenant fixture for guard tests.
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross Timmy"
        )
        self.cross_cadence = start_cadence(
            dealership=self.other,
            lead=self.cross_lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        self.cross_task = self.cross_cadence.tasks.first()

    def test_complete_task_transitions_state(self) -> None:
        complete_task(
            dealership=self.dealership,
            task=self.task,
            completed_by_user=self.user,
            notes="Left voicemail.",
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.state, FOLLOW_UP_TASK_STATE_COMPLETED)
        self.assertEqual(self.task.completed_by_user_id, self.user.id)
        self.assertIsNotNone(self.task.completed_at)
        self.assertEqual(self.task.notes, "Left voicemail.")

    def test_skip_task_transitions_state(self) -> None:
        skip_task(
            dealership=self.dealership,
            task=self.task,
            completed_by_user=self.user,
            notes="Customer opted out.",
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.state, FOLLOW_UP_TASK_STATE_SKIPPED)
        self.assertEqual(self.task.notes, "Customer opted out.")

    def test_terminal_task_refuses_re_transition(self) -> None:
        complete_task(
            dealership=self.dealership,
            task=self.task,
            completed_by_user=self.user,
        )
        self.task.refresh_from_db()
        with self.assertRaises(TaskAlreadyTerminalError):
            complete_task(
                dealership=self.dealership,
                task=self.task,
                completed_by_user=self.user,
            )
        with self.assertRaises(TaskAlreadyTerminalError):
            skip_task(
                dealership=self.dealership,
                task=self.task,
                completed_by_user=self.user,
            )

    def test_cross_tenant_task_raises(self) -> None:
        with self.assertRaises(CrossTenantTaskError):
            complete_task(
                dealership=self.dealership,
                task=self.cross_task,
                completed_by_user=self.user,
            )


class PauseCadenceTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="fu-svc-pause", name="FU Svc Pause"
        )
        self.other = Dealership.objects.create(
            slug="fu-svc-pause-other", name="FU Svc Pause Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Pauline"
        )
        self.cadence = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )

    def test_pause_flips_is_active(self) -> None:
        pause_cadence(dealership=self.dealership, cadence=self.cadence)
        self.cadence.refresh_from_db()
        self.assertFalse(self.cadence.is_active)

    def test_pause_idempotent(self) -> None:
        pause_cadence(dealership=self.dealership, cadence=self.cadence)
        # Second pause is a no-op that doesn't raise.
        pause_cadence(dealership=self.dealership, cadence=self.cadence)
        self.cadence.refresh_from_db()
        self.assertFalse(self.cadence.is_active)

    def test_cross_tenant_pause_raises(self) -> None:
        with self.assertRaises(CrossTenantCadenceError):
            pause_cadence(dealership=self.other, cadence=self.cadence)
