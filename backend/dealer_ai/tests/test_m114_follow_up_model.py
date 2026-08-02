"""Milestone 11 · Increment 4 (SESSION_117) — FollowUpCadence + Task model tests.

Locks the schema surface of :class:`dealer_ai.models.FollowUpCadence`
and :class:`dealer_ai.models.FollowUpTask` per
``MILESTONE_11_PLANNING.md`` §1.4 + §5.d Option A.

Coverage:

- Cadence Meta ordering (``-started_at``) + defaults (``is_active``
  True).
- Cadence ``clean()`` cross-tenant guard.
- Cadence CASCADE on lead delete.
- Task Meta ordering (``due_at`` asc) + default state ``pending``.
- Task ``clean()`` cross-tenant guard.
- Task CASCADE on cadence delete.
- Task SET_NULL on completed_by_user delete.
- Template vocab exact-set + offset schedule sanity.
"""

from __future__ import annotations

import datetime as dt

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    FOLLOW_UP_TASK_STATE_PENDING,
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


User = get_user_model()


class FollowUpCadenceModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="fu-cad", name="FU Cadence"
        )
        self.other = Dealership.objects.create(
            slug="fu-cad-other", name="FU Cad Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Cara"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross Cara"
        )

    def test_defaults_is_active_true(self) -> None:
        cadence = FollowUpCadence.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
            started_at=timezone.now(),
        )
        self.assertTrue(cadence.is_active)

    def test_ordering_is_reverse_started_at(self) -> None:
        earlier = FollowUpCadence.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
            started_at=timezone.now() - dt.timedelta(days=2),
        )
        later = FollowUpCadence.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_30DAY,
            started_at=timezone.now(),
        )
        self.assertEqual(list(FollowUpCadence.objects.all()), [later, earlier])

    def test_clean_rejects_cross_tenant_lead(self) -> None:
        cadence = FollowUpCadence(
            dealership=self.dealership,
            lead=self.cross_lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
            started_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            cadence.clean()
        self.assertIn("lead", ctx.exception.message_dict)

    def test_lead_delete_cascades_cadence(self) -> None:
        cadence = FollowUpCadence.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
            started_at=timezone.now(),
        )
        self.lead.delete()
        self.assertFalse(
            FollowUpCadence.objects.filter(pk=cadence.pk).exists()
        )


class FollowUpTaskModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="fu-task", name="FU Task"
        )
        self.other = Dealership.objects.create(
            slug="fu-task-other", name="FU Task Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Terri"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross Terri"
        )
        self.cadence = FollowUpCadence.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
            started_at=timezone.now(),
        )
        self.cross_cadence = FollowUpCadence.objects.create(
            dealership=self.other,
            lead=self.cross_lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
            started_at=timezone.now(),
        )
        self.user = User.objects.create_user(
            username="fu-task-user", password="x"
        )

    def test_default_state_pending(self) -> None:
        task = FollowUpTask.objects.create(
            dealership=self.dealership,
            cadence=self.cadence,
            due_at=timezone.now() + dt.timedelta(days=1),
        )
        self.assertEqual(task.state, FOLLOW_UP_TASK_STATE_PENDING)
        self.assertIsNone(task.completed_at)
        self.assertEqual(task.notes, "")

    def test_ordering_is_due_at_asc(self) -> None:
        later = FollowUpTask.objects.create(
            dealership=self.dealership,
            cadence=self.cadence,
            due_at=timezone.now() + dt.timedelta(days=3),
        )
        earlier = FollowUpTask.objects.create(
            dealership=self.dealership,
            cadence=self.cadence,
            due_at=timezone.now() + dt.timedelta(days=1),
        )
        self.assertEqual(list(FollowUpTask.objects.all()), [earlier, later])

    def test_clean_rejects_cross_tenant_cadence(self) -> None:
        task = FollowUpTask(
            dealership=self.dealership,
            cadence=self.cross_cadence,
            due_at=timezone.now() + dt.timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as ctx:
            task.clean()
        self.assertIn("cadence", ctx.exception.message_dict)

    def test_cadence_delete_cascades_task(self) -> None:
        task = FollowUpTask.objects.create(
            dealership=self.dealership,
            cadence=self.cadence,
            due_at=timezone.now() + dt.timedelta(days=1),
        )
        self.cadence.delete()
        self.assertFalse(FollowUpTask.objects.filter(pk=task.pk).exists())

    def test_completed_by_user_delete_sets_null(self) -> None:
        task = FollowUpTask.objects.create(
            dealership=self.dealership,
            cadence=self.cadence,
            due_at=timezone.now() + dt.timedelta(days=1),
            completed_by_user=self.user,
        )
        self.user.delete()
        task.refresh_from_db()
        self.assertIsNone(task.completed_by_user)


class FollowUpTemplateVocabTests(TestCase):
    def test_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in FOLLOW_UP_TEMPLATE_CHOICES}
        self.assertEqual(
            vocab,
            {
                FOLLOW_UP_TEMPLATE_24HR,
                FOLLOW_UP_TEMPLATE_1WK,
                FOLLOW_UP_TEMPLATE_30DAY,
                FOLLOW_UP_TEMPLATE_90DAY,
                FOLLOW_UP_TEMPLATE_6MO,
                FOLLOW_UP_TEMPLATE_1YR,
            },
        )

    def test_every_template_has_offset_schedule(self) -> None:
        for key, _ in FOLLOW_UP_TEMPLATE_CHOICES:
            with self.subTest(template=key):
                self.assertIn(key, FOLLOW_UP_TEMPLATE_OFFSETS)
                self.assertGreater(len(FOLLOW_UP_TEMPLATE_OFFSETS[key]), 0)
