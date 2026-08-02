"""Milestone 13 · Increment 2 (SESSION_130) — M2 cost reconciliation Celery task tests."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_PARTS,
    Dealership,
    JournalEntry,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.accounting import seed_default_coa
from dealer_ai.services.accounting.tasks import (
    POST_FOR_ALL_TENANTS_TASK_NAME,
    POST_FOR_TENANT_TASK_NAME,
    post_vehicle_cost_journals_for_all_tenants,
    post_vehicle_cost_journals_for_dealership,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_vehicle_and_cost(
    dealership: Dealership, stock: str, amount: Decimal
) -> VehicleCost:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Test",
        price=Decimal("10000.00"),
        dealership=dealership,
    )
    return VehicleCost.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CATEGORY_PARTS,
        amount=amount,
        incurred_at=timezone.now(),
    )


class PostForDealershipTaskTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()

    def test_task_name_matches_registered_constant(self) -> None:
        self.assertEqual(
            POST_FOR_TENANT_TASK_NAME,
            "dealer_ai.services.accounting.tasks."
            "post_vehicle_cost_journals_for_dealership",
        )

    def test_direct_call_posts_and_returns_summary(self) -> None:
        _make_vehicle_and_cost(
            self.dealership, "M132-TASK-1", Decimal("22.00")
        )
        result = post_vehicle_cost_journals_for_dealership(
            dealership_id=self.dealership.pk
        )
        self.assertEqual(result["posted_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["dealership_id"], self.dealership.pk)
        self.assertEqual(JournalEntry.objects.count(), 1)


class PostForAllTenantsOrchestratorTests(TestCase):
    def setUp(self) -> None:
        self.dealership_a = get_default_dealership()
        self.dealership_b = Dealership.objects.create(
            slug="orch-tenant-b", name="B"
        )
        seed_default_coa(self.dealership_b)

    def test_orchestrator_task_name_matches_registered_constant(self) -> None:
        self.assertEqual(
            POST_FOR_ALL_TENANTS_TASK_NAME,
            "dealer_ai.services.accounting.tasks."
            "post_vehicle_cost_journals_for_all_tenants",
        )

    def test_orchestrator_dispatches_per_tenant(self) -> None:
        with patch(
            "dealer_ai.services.accounting.tasks."
            "post_vehicle_cost_journals_for_dealership.delay"
        ) as delayed:
            result = post_vehicle_cost_journals_for_all_tenants()
        self.assertGreaterEqual(result["dispatched_tenant_count"], 2)
        dispatched_ids = {
            call.kwargs["dealership_id"]
            for call in delayed.call_args_list
        }
        self.assertIn(self.dealership_a.pk, dispatched_ids)
        self.assertIn(self.dealership_b.pk, dispatched_ids)

    def test_orchestrator_handles_zero_tenants_gracefully(self) -> None:
        # Delete non-default tenants so the orchestrator sees only the
        # default dealership row (Dealership can't be empty — the
        # tenancy substrate requires the "default" row).
        Dealership.objects.exclude(slug="default").delete()
        with patch(
            "dealer_ai.services.accounting.tasks."
            "post_vehicle_cost_journals_for_dealership.delay"
        ) as delayed:
            result = post_vehicle_cost_journals_for_all_tenants()
        self.assertEqual(result["dispatched_tenant_count"], 1)
        self.assertEqual(delayed.call_count, 1)


class BeatScheduleRegistrationTests(TestCase):
    def test_10_00_slot_registered(self) -> None:
        from django.conf import settings

        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn("accounting-vehicle-cost-post-daily-10-00", schedule)
        entry = schedule["accounting-vehicle-cost-post-daily-10-00"]
        self.assertEqual(
            entry["task"],
            POST_FOR_ALL_TENANTS_TASK_NAME,
        )
        # crontab schedules expose ``hour`` as a set of ints; guard
        # against the format changing under us.
        self.assertIn(10, entry["schedule"].hour)
        self.assertIn(0, entry["schedule"].minute)

    def test_beat_schedule_has_at_least_nine_families(self) -> None:
        # >= per M9/M10/M11/M12 lesson-14 growth-only assertion posture.
        from django.conf import settings

        self.assertGreaterEqual(
            len(settings.CELERY_BEAT_SCHEDULE), 9
        )
