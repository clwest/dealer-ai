"""Milestone 7 · Increment 3 (SESSION_090) — aging-snapshot Celery task tests.

Locks the two Celery task shells + the Beat schedule entry:

- ``snapshot_stage_ages_for_tenant`` — per-tenant work; writes one
  ``JobRunLog`` row with ``dealership_id`` stamped; returns a
  JSON-safe dict.
- ``snapshot_stage_ages_for_all_tenants`` — orchestrator; enqueues
  per-tenant tasks via ``.delay()``.
- ``CELERY_BEAT_SCHEDULE`` — an entry firing the orchestrator at
  03:00 daily (one hour after the M7.2 accrual entry to avoid
  worker contention).

Runs under ``CELERY_TASK_ALWAYS_EAGER=True`` (M7.1) so task
invocations are synchronous.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    JOB_RUN_STATUS_SUCCEEDED,
    VEHICLE_STAGE_FRONTLINE,
    Dealership,
    JobRunLog,
    StageAgingSnapshot,
    Vehicle,
    VehicleStage,
)
from dealer_ai.services.lifecycle_aging.tasks import (
    SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME,
    SNAPSHOT_FOR_TENANT_TASK_NAME,
    snapshot_stage_ages_for_all_tenants,
    snapshot_stage_ages_for_tenant,
)


def _make_vehicle_in_frontline(
    stock: str, dealership: Dealership, days_ago: int
) -> Vehicle:
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    stage_row = VehicleStage.objects.get(vehicle=v)
    stage_row.current_stage = VEHICLE_STAGE_FRONTLINE
    stage_row.entered_at = timezone.now() - dt.timedelta(days=days_ago)
    stage_row.save(update_fields=("current_stage", "entered_at"))
    return v


class TaskNames(TestCase):
    """The tasks are registered under the canonical dotted names."""

    def test_per_tenant_task_name(self):
        self.assertEqual(
            snapshot_stage_ages_for_tenant.name,
            SNAPSHOT_FOR_TENANT_TASK_NAME,
        )
        self.assertEqual(
            SNAPSHOT_FOR_TENANT_TASK_NAME,
            "dealer_ai.services.lifecycle_aging.tasks"
            ".snapshot_stage_ages_for_tenant",
        )

    def test_orchestrator_task_name(self):
        self.assertEqual(
            snapshot_stage_ages_for_all_tenants.name,
            SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME,
        )
        self.assertEqual(
            SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME,
            "dealer_ai.services.lifecycle_aging.tasks"
            ".snapshot_stage_ages_for_all_tenants",
        )


class PerTenantTaskWritesSnapshots(TestCase):
    """The per-tenant task invokes the verb and persists rows."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _make_vehicle_in_frontline("M73T-A", self.default, days_ago=3)

    def test_task_writes_one_row_for_populated_stage(self):
        snapshot_stage_ages_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertEqual(
            StageAgingSnapshot.objects.filter(
                dealership=self.default,
                stage=VEHICLE_STAGE_FRONTLINE,
            ).count(),
            1,
        )

    def test_task_return_value_is_json_safe_dict(self):
        result = snapshot_stage_ages_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["dealership_id"], self.default.pk)
        self.assertEqual(result["dealership_slug"], "default")
        self.assertEqual(result["rows_written"], 1)
        self.assertIn(
            VEHICLE_STAGE_FRONTLINE, result["stages_with_vehicles"]
        )
        # snapshot_at serialized as ISO string.
        self.assertIsInstance(result["snapshot_at"], str)
        # Round-trippable back to a datetime.
        parsed = dt.datetime.fromisoformat(result["snapshot_at"])
        self.assertIsInstance(parsed, dt.datetime)


class PerTenantTaskWritesJobRunLog(TestCase):
    """One ``JobRunLog`` row per per-tenant invocation, stamped with
    ``dealership_id``."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_job_run_log_row_created_with_tenant_stamp(self):
        snapshot_stage_ages_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        rows = list(
            JobRunLog.objects.filter(
                task_name=SNAPSHOT_FOR_TENANT_TASK_NAME
            )
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.status, JOB_RUN_STATUS_SUCCEEDED)
        self.assertEqual(row.dealership_id, self.default.pk)
        self.assertIsNotNone(row.duration_ms)


class PerTenantTaskAcceptsSnapshotAtIso(TestCase):
    """The ``snapshot_at_iso`` kwarg is parsed and forwarded to the
    verb."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        _make_vehicle_in_frontline("M73T-TS", self.default, days_ago=1)

    def test_explicit_snapshot_at_iso_used(self):
        explicit = timezone.now() - dt.timedelta(hours=2)
        result = snapshot_stage_ages_for_tenant.apply(
            kwargs={
                "dealership_id": self.default.pk,
                "snapshot_at_iso": explicit.isoformat(),
            }
        ).get()
        self.assertEqual(result["snapshot_at"], explicit.isoformat())

    def test_snapshot_at_iso_none_defaults_to_now(self):
        before = timezone.now()
        result = snapshot_stage_ages_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        after = timezone.now()
        # Parseable ISO datetime within the invocation window.
        parsed = dt.datetime.fromisoformat(result["snapshot_at"])
        self.assertGreaterEqual(parsed, before)
        self.assertLessEqual(parsed, after)


class OrchestratorTaskFansOutToAllTenants(TestCase):
    """The orchestrator enqueues one per-tenant task per Dealership.
    Under ``ALWAYS_EAGER=True`` the ``.delay()`` calls resolve
    synchronously — so we can assert on the resulting per-tenant
    snapshots."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other-o")
        _make_vehicle_in_frontline("M73O-DEF", self.default, days_ago=5)
        _make_vehicle_in_frontline("M73O-OTH", self.other, days_ago=8)

    def test_orchestrator_dispatches_per_dealership(self):
        result = snapshot_stage_ages_for_all_tenants.apply().get()
        self.assertEqual(result["dispatched_tenant_count"], 2)

    def test_orchestrator_causes_per_tenant_snapshots(self):
        snapshot_stage_ages_for_all_tenants.apply().get()
        default_rows = StageAgingSnapshot.objects.filter(
            dealership=self.default
        ).count()
        other_rows = StageAgingSnapshot.objects.filter(
            dealership=self.other
        ).count()
        self.assertEqual(default_rows, 1)
        self.assertEqual(other_rows, 1)


class OrchestratorTaskWritesJobRunLog(TestCase):
    """One ``JobRunLog`` row for the orchestrator invocation, plus one
    per per-tenant dispatch."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_orchestrator_row_recorded(self):
        snapshot_stage_ages_for_all_tenants.apply().get()
        orchestrator_rows = list(
            JobRunLog.objects.filter(
                task_name=SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME
            )
        )
        self.assertEqual(len(orchestrator_rows), 1)
        self.assertEqual(
            orchestrator_rows[0].status, JOB_RUN_STATUS_SUCCEEDED
        )

    def test_per_tenant_rows_stamped_per_dispatch(self):
        snapshot_stage_ages_for_all_tenants.apply().get()
        per_tenant_rows = list(
            JobRunLog.objects.filter(
                task_name=SNAPSHOT_FOR_TENANT_TASK_NAME
            )
        )
        # One default tenant exists at test setUp; the orchestrator
        # fans out to it.
        self.assertEqual(len(per_tenant_rows), 1)
        self.assertEqual(
            per_tenant_rows[0].dealership_id, self.default.pk
        )


class BeatScheduleEntryRegistered(TestCase):
    """The M7.3 Beat entry is present with the expected schedule."""

    def test_entry_exists(self):
        self.assertIn(
            "stage-aging-snapshot-daily-03-00",
            settings.CELERY_BEAT_SCHEDULE,
        )

    def test_entry_targets_orchestrator_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE[
            "stage-aging-snapshot-daily-03-00"
        ]
        self.assertEqual(
            entry["task"], SNAPSHOT_FOR_ALL_TENANTS_TASK_NAME
        )

    def test_entry_schedule_is_03_00_daily(self):
        from celery.schedules import crontab

        entry = settings.CELERY_BEAT_SCHEDULE[
            "stage-aging-snapshot-daily-03-00"
        ]
        schedule = entry["schedule"]
        self.assertIsInstance(schedule, crontab)
        # Locked hour + minute. Celery normalizes numeric crontab
        # args; compare against str() for robustness.
        self.assertEqual(str(schedule._orig_hour), "3")
        self.assertEqual(str(schedule._orig_minute), "0")

    def test_entry_scheduled_after_m7_2_accrual_entry(self):
        # M7.3 must fire AFTER M7.2's 02:00 entry to avoid worker
        # contention. Compare the crontab hours.
        accrual = settings.CELERY_BEAT_SCHEDULE[
            "floor-plan-accrual-daily-02-00"
        ]["schedule"]
        aging = settings.CELERY_BEAT_SCHEDULE[
            "stage-aging-snapshot-daily-03-00"
        ]["schedule"]
        self.assertLess(int(accrual._orig_hour), int(aging._orig_hour))
