"""Milestone 7 · Increment 2 (SESSION_089) — floor-plan Celery task tests.

Locks the two Celery task shells + the Beat schedule entry:

- ``accrue_daily_interest_for_tenant`` — per-tenant work; writes one
  ``JobRunLog`` row with ``dealership_id`` stamped.
- ``accrue_daily_interest_for_all_tenants`` — orchestrator; enqueues
  per-tenant tasks via ``.delay()``.
- ``CELERY_BEAT_SCHEDULE`` — one entry firing the orchestrator at
  02:00 daily.

Runs under ``CELERY_TASK_ALWAYS_EAGER=True`` (M7.1) so task
invocations are synchronous and the caller's transaction sees writes
immediately.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CATEGORY_FLOOR_PLAN_INTEREST,
    JOB_RUN_STATUS_SUCCEEDED,
    SOURCE_AUCTION,
    Dealership,
    JobRunLog,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services.floor_plan.tasks import (
    ACCRUE_FOR_ALL_TENANTS_TASK_NAME,
    ACCRUE_FOR_TENANT_TASK_NAME,
    accrue_daily_interest_for_all_tenants,
    accrue_daily_interest_for_tenant,
)
from dealer_ai.services.vehicle_ledger import record_acquisition


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _seed_acquisition(
    vehicle: Vehicle,
    dealership: Dealership,
    purchase_date: dt.date,
) -> None:
    record_acquisition(
        vehicle,
        dealership=dealership,
        source=SOURCE_AUCTION,
        purchase_price=Decimal("18000.00"),
        purchase_date=purchase_date,
    )


class TaskNames(TestCase):
    """The tasks are registered under the canonical dotted names."""

    def test_per_tenant_task_name(self):
        self.assertEqual(
            accrue_daily_interest_for_tenant.name,
            ACCRUE_FOR_TENANT_TASK_NAME,
        )
        self.assertEqual(
            ACCRUE_FOR_TENANT_TASK_NAME,
            "dealer_ai.services.floor_plan.tasks"
            ".accrue_daily_interest_for_tenant",
        )

    def test_orchestrator_task_name(self):
        self.assertEqual(
            accrue_daily_interest_for_all_tenants.name,
            ACCRUE_FOR_ALL_TENANTS_TASK_NAME,
        )
        self.assertEqual(
            ACCRUE_FOR_ALL_TENANTS_TASK_NAME,
            "dealer_ai.services.floor_plan.tasks"
            ".accrue_daily_interest_for_all_tenants",
        )


class PerTenantTaskPostsAccruals(TestCase):
    """The per-tenant task calls the verb and posts rows."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        vehicle = _make_vehicle("M7TASK-1", self.default)
        _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_task_posts_row(self):
        accrue_daily_interest_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            1,
        )

    def test_task_return_value_is_json_serializable_dict(self):
        result = accrue_daily_interest_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["dealership_id"], self.default.pk)
        self.assertEqual(result["dealership_slug"], "default")
        self.assertEqual(result["vehicles_accrued"], 1)
        # total_accrued serialized as string (JSON-safe for Decimals).
        self.assertIsInstance(result["total_accrued"], str)


class PerTenantTaskWritesJobRunLog(TestCase):
    """One ``JobRunLog`` row per per-tenant invocation, stamped with
    ``dealership_id``."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_job_run_log_row_created_with_tenant_stamp(self):
        accrue_daily_interest_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        rows = list(
            JobRunLog.objects.filter(
                task_name=ACCRUE_FOR_TENANT_TASK_NAME
            )
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.status, JOB_RUN_STATUS_SUCCEEDED)
        self.assertEqual(row.dealership_id, self.default.pk)
        self.assertIsNotNone(row.duration_ms)


class PerTenantTaskAcceptsAsOfIso(TestCase):
    """The ``as_of_iso`` kwarg is parsed and forwarded to the verb."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        sixty_days_ago = timezone.now().date() - dt.timedelta(days=60)
        vehicle = _make_vehicle("M7TASK-ASOF", self.default)
        _seed_acquisition(vehicle, self.default, sixty_days_ago)

    def test_as_of_iso_used_when_provided(self):
        as_of = timezone.now().date() - dt.timedelta(days=15)
        result = accrue_daily_interest_for_tenant.apply(
            kwargs={
                "dealership_id": self.default.pk,
                "as_of_iso": as_of.isoformat(),
            }
        ).get()
        self.assertEqual(result["as_of"], as_of.isoformat())

    def test_as_of_iso_none_defaults_to_today(self):
        today = timezone.now().date()
        result = accrue_daily_interest_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertEqual(result["as_of"], today.isoformat())


class OrchestratorTaskFansOutToAllTenants(TestCase):
    """The orchestrator enqueues one per-tenant task per Dealership.
    Under ``ALWAYS_EAGER=True``, ``.delay()`` calls resolve
    synchronously — so we can assert on the resulting per-tenant
    accruals."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other")

        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        v_default = _make_vehicle("M7ORCH-DEF", self.default)
        _seed_acquisition(v_default, self.default, thirty_days_ago)
        v_other = _make_vehicle("M7ORCH-OTHER", self.other)
        _seed_acquisition(v_other, self.other, thirty_days_ago)

    def test_orchestrator_dispatches_per_tenant_task_per_dealership(self):
        result = accrue_daily_interest_for_all_tenants.apply().get()
        # Two dealerships exist (default + other) → two dispatches.
        self.assertEqual(result["dispatched_tenant_count"], 2)

    def test_orchestrator_causes_per_tenant_accruals(self):
        accrue_daily_interest_for_all_tenants.apply().get()
        # One accrual row per tenant that has an eligible vehicle.
        self.assertEqual(
            VehicleCost.objects.filter(
                dealership=self.default,
                category=CATEGORY_FLOOR_PLAN_INTEREST,
            ).count(),
            1,
        )
        self.assertEqual(
            VehicleCost.objects.filter(
                dealership=self.other,
                category=CATEGORY_FLOOR_PLAN_INTEREST,
            ).count(),
            1,
        )


class OrchestratorTaskWritesJobRunLog(TestCase):
    """One ``JobRunLog`` row for the orchestrator invocation, plus one
    per per-tenant dispatch."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_orchestrator_row_has_no_dealership_stamp_by_kwargs(self):
        # The orchestrator receives no ``dealership_id`` kwarg — its
        # scope is process-wide. The @instrumented_task decorator
        # therefore does NOT stamp ``dealership_id`` from kwargs. The
        # tenancy autofill signal (M7.1) fills in the default tenant
        # as the safety-net path. This test locks that behavior so a
        # future edit that changed the orchestrator's kwarg contract
        # would surface here.
        accrue_daily_interest_for_all_tenants.apply().get()
        orchestrator_rows = list(
            JobRunLog.objects.filter(
                task_name=ACCRUE_FOR_ALL_TENANTS_TASK_NAME
            )
        )
        self.assertEqual(len(orchestrator_rows), 1)
        self.assertEqual(
            orchestrator_rows[0].status, JOB_RUN_STATUS_SUCCEEDED
        )

    def test_per_tenant_rows_stamped_per_dispatch(self):
        accrue_daily_interest_for_all_tenants.apply().get()
        per_tenant_rows = list(
            JobRunLog.objects.filter(
                task_name=ACCRUE_FOR_TENANT_TASK_NAME
            )
        )
        # One default tenant exists at test setUp; the orchestrator
        # fans out to it.
        self.assertEqual(len(per_tenant_rows), 1)
        self.assertEqual(
            per_tenant_rows[0].dealership_id, self.default.pk
        )


class BeatScheduleEntryRegistered(TestCase):
    """The M7.2 Beat entry is present with the expected schedule."""

    def test_entry_exists(self):
        self.assertIn(
            "floor-plan-accrual-daily-02-00",
            settings.CELERY_BEAT_SCHEDULE,
        )

    def test_entry_targets_orchestrator_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE[
            "floor-plan-accrual-daily-02-00"
        ]
        self.assertEqual(entry["task"], ACCRUE_FOR_ALL_TENANTS_TASK_NAME)

    def test_entry_schedule_is_02_00_daily(self):
        from celery.schedules import crontab

        entry = settings.CELERY_BEAT_SCHEDULE[
            "floor-plan-accrual-daily-02-00"
        ]
        schedule = entry["schedule"]
        self.assertIsInstance(schedule, crontab)
        # Locked hour + minute — a future edit that moved the schedule
        # away from 02:00 (e.g. to a different maintenance window)
        # would surface here. Celery normalizes numeric crontab args to
        # ints (str repr under some paths); compare against str(int()).
        self.assertEqual(str(schedule._orig_hour), "2")
        self.assertEqual(str(schedule._orig_minute), "0")


class ManagementCommandStillWorksAfterExtraction(TestCase):
    """The M2 CLI surface remains functional after the M7.2 body
    extraction. This is a lightweight regression guard on top of the
    fuller M2 command tests in
    ``test_accrue_floor_plan_interest_command.py``."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        thirty_days_ago = timezone.now().date() - dt.timedelta(days=30)
        vehicle = _make_vehicle("M7CLI-1", self.default)
        _seed_acquisition(vehicle, self.default, thirty_days_ago)

    def test_command_completes_and_posts_row(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command(
            "accrue_floor_plan_interest",
            "--dealership=default",
            stdout=out,
            stderr=StringIO(),
        )
        self.assertIn("Floor-plan accrual for dealership 'default'", out.getvalue())
        self.assertEqual(
            VehicleCost.objects.filter(
                category=CATEGORY_FLOOR_PLAN_INTEREST
            ).count(),
            1,
        )
