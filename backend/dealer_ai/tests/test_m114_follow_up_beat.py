"""Milestone 11 · Increment 4 (SESSION_117) — Follow-up Celery-beat integration tests.

Locks the two orchestrator tasks in :mod:`services.follow_ups.tasks`
per ``MILESTONE_11_PLANNING.md`` §1.4 + §7 M11.4. Task execution runs
synchronously here because ``CELERY_TASK_ALWAYS_EAGER=True`` is set
in test settings.

Coverage:

- Per-tenant surfacer counts pending tasks whose ``due_at <= now``
  and whose parent cadence ``is_active=True``.
- Per-tenant surfacer excludes tasks whose parent cadence is paused
  (``is_active=False``) — pause halts beat visibility.
- Per-tenant surfacer excludes tasks in terminal states (completed
  / skipped) — even if due date is in the past.
- Per-tenant surfacer excludes future tasks (``due_at > now``).
- Beat surfacer does **not** transition state (SESSION_117 §0.a
  M11.4 decision 3) — pending tasks remain pending after
  surfacing.
- Orchestrator dispatches one per-tenant task per Dealership row.
"""

from __future__ import annotations

import datetime as dt

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    FOLLOW_UP_TASK_STATE_COMPLETED,
    FOLLOW_UP_TASK_STATE_PENDING,
    FOLLOW_UP_TEMPLATE_1WK,
    CustomerLead,
    Dealership,
    FollowUpTask,
)
from dealer_ai.services.follow_ups import (
    complete_task,
    pause_cadence,
    start_cadence,
)
from dealer_ai.services.follow_ups.tasks import (
    surface_due_follow_up_tasks_for_all_tenants,
    surface_due_follow_up_tasks_for_tenant,
)


class SurfaceForTenantTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="fu-beat", name="FU Beat"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Beater"
        )
        self.cadence = start_cadence(
            dealership=self.dealership,
            lead=self.lead,
            template=FOLLOW_UP_TEMPLATE_1WK,
        )
        # Backdate one task so it is due now.
        self.due_task = self.cadence.tasks.first()
        self.due_task.due_at = timezone.now() - dt.timedelta(hours=1)
        self.due_task.save(update_fields=["due_at"])
        # The remaining tasks are in the future (as seeded).

    def test_surfacer_counts_only_due_pending_tasks(self) -> None:
        result = surface_due_follow_up_tasks_for_tenant(
            dealership_id=self.dealership.pk
        )
        # Exactly one task is backdated + pending; the other seeded
        # tasks are due in the future.
        self.assertEqual(result["due_count"], 1)
        self.assertEqual(result["dealership_id"], self.dealership.pk)

    def test_surfacer_does_not_transition_state(self) -> None:
        surface_due_follow_up_tasks_for_tenant(
            dealership_id=self.dealership.pk
        )
        self.due_task.refresh_from_db()
        self.assertEqual(self.due_task.state, FOLLOW_UP_TASK_STATE_PENDING)

    def test_surfacer_excludes_paused_cadence_tasks(self) -> None:
        pause_cadence(dealership=self.dealership, cadence=self.cadence)
        result = surface_due_follow_up_tasks_for_tenant(
            dealership_id=self.dealership.pk
        )
        self.assertEqual(result["due_count"], 0)

    def test_surfacer_excludes_completed_tasks(self) -> None:
        complete_task(
            dealership=self.dealership,
            task=self.due_task,
        )
        result = surface_due_follow_up_tasks_for_tenant(
            dealership_id=self.dealership.pk
        )
        self.assertEqual(result["due_count"], 0)


class SurfaceForAllTenantsOrchestratorTests(TestCase):
    def setUp(self) -> None:
        # Use a distinct slug so the default-dealership fixture isn't
        # polluted by tests that need a clean count.
        self.d1 = Dealership.objects.create(slug="fu-orc-1", name="Orc 1")
        self.d2 = Dealership.objects.create(slug="fu-orc-2", name="Orc 2")
        for d in (self.d1, self.d2):
            lead = CustomerLead.objects.create(dealership=d, name=f"lead-{d.slug}")
            cadence = start_cadence(
                dealership=d,
                lead=lead,
                template=FOLLOW_UP_TEMPLATE_1WK,
            )
            task = cadence.tasks.first()
            task.due_at = timezone.now() - dt.timedelta(hours=1)
            task.save(update_fields=["due_at"])

    def test_orchestrator_dispatches_per_tenant(self) -> None:
        # The orchestrator's return value counts all Dealership rows
        # (there is at least the default + the two we made). Assert
        # it saw the two we made without locking on the exact total
        # (other test-tenants may exist per M9 §6 lesson 14 / M10
        # lesson 12: >= not ==).
        result = surface_due_follow_up_tasks_for_all_tenants()
        self.assertGreaterEqual(result["dispatched_tenant_count"], 2)
        # Because CELERY_TASK_ALWAYS_EAGER=True, each dispatched
        # per-tenant task ran synchronously. Verify both our tenants
        # have their one due task still pending (surfacer is read-
        # only).
        for d in (self.d1, self.d2):
            due = FollowUpTask.objects.filter(
                dealership=d,
                state=FOLLOW_UP_TASK_STATE_PENDING,
                due_at__lte=timezone.now(),
            ).count()
            self.assertEqual(due, 1)
