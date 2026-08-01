"""Milestone 7 · Increment 4 (SESSION_091) — vendor-SLA Celery task tests.

Locks the two Celery task shells + the Beat schedule entry:

- ``detect_sla_breaches_for_tenant`` — per-tenant scan; writes one
  ``JobRunLog`` row with ``dealership_id`` stamped; returns a
  JSON-safe dict summarizing the report.
- ``detect_sla_breaches_for_all_tenants`` — orchestrator; enqueues
  per-tenant tasks via ``.delay()``.
- ``CELERY_BEAT_SCHEDULE`` — entry firing the orchestrator at 04:00
  daily (after M7.2 02:00 and M7.3 03:00).

Runs under ``CELERY_TASK_ALWAYS_EAGER=True`` (M7.1).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    JOB_RUN_STATUS_SUCCEEDED,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    JobRunLog,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.vendor_sla.tasks import (
    DETECT_FOR_ALL_TENANTS_TASK_NAME,
    DETECT_FOR_TENANT_TASK_NAME,
    detect_sla_breaches_for_all_tenants,
    detect_sla_breaches_for_tenant,
)


def _seed_breach(dealership: Dealership, stock: str, vendor_slug: str) -> WorkOrder:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    vendor = Vendor.objects.create(
        dealership=dealership,
        name=f"Vendor {vendor_slug}",
        slug=vendor_slug,
    )
    # In-progress + ETA in the past → guaranteed breach.
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        vendor=vendor,
        status=WORK_ORDER_STATUS_IN_PROGRESS,
        estimated_completion_date=timezone.now().date() - dt.timedelta(days=5),
    )


class TaskNames(TestCase):
    """Both tasks registered under the canonical dotted names."""

    def test_per_tenant_task_name(self):
        self.assertEqual(
            detect_sla_breaches_for_tenant.name,
            DETECT_FOR_TENANT_TASK_NAME,
        )
        self.assertEqual(
            DETECT_FOR_TENANT_TASK_NAME,
            "dealer_ai.services.vendor_sla.tasks"
            ".detect_sla_breaches_for_tenant",
        )

    def test_orchestrator_task_name(self):
        self.assertEqual(
            detect_sla_breaches_for_all_tenants.name,
            DETECT_FOR_ALL_TENANTS_TASK_NAME,
        )
        self.assertEqual(
            DETECT_FOR_ALL_TENANTS_TASK_NAME,
            "dealer_ai.services.vendor_sla.tasks"
            ".detect_sla_breaches_for_all_tenants",
        )


class PerTenantTaskReturnsReportDict(TestCase):
    """The per-tenant task calls the verb and returns JSON-safe dict."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.wo = _seed_breach(self.default, "M74T-A", "vendor-a")

    def test_task_return_value_summarizes_report(self):
        result = detect_sla_breaches_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["dealership_id"], self.default.pk)
        self.assertEqual(result["dealership_slug"], "default")
        self.assertEqual(result["breach_count"], 1)
        self.assertEqual(result["in_progress_past_eta_count"], 1)
        self.assertEqual(result["approved_stale_count"], 0)
        # WO ID list is flat + serializable.
        self.assertEqual(
            result["breach_work_order_ids"], [self.wo.pk]
        )
        # as_of serialized as ISO date string.
        self.assertIsInstance(result["as_of"], str)


class PerTenantTaskWritesJobRunLog(TestCase):
    """One ``JobRunLog`` row per per-tenant invocation, stamped."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_job_run_log_row_created_with_tenant_stamp(self):
        detect_sla_breaches_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        rows = list(
            JobRunLog.objects.filter(
                task_name=DETECT_FOR_TENANT_TASK_NAME
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

    def test_explicit_as_of_iso_used(self):
        explicit = dt.date(2025, 12, 31)
        result = detect_sla_breaches_for_tenant.apply(
            kwargs={
                "dealership_id": self.default.pk,
                "as_of_iso": explicit.isoformat(),
            }
        ).get()
        self.assertEqual(result["as_of"], explicit.isoformat())

    def test_as_of_iso_none_defaults_to_today(self):
        today = timezone.now().date()
        result = detect_sla_breaches_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertIn(
            result["as_of"],
            {
                (today - dt.timedelta(days=1)).isoformat(),
                today.isoformat(),
            },
        )


class OrchestratorFansOutToAllTenants(TestCase):
    """The orchestrator enqueues one per-tenant task per Dealership."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other-orch")
        _seed_breach(self.default, "M74O-DEF", "orch-def")
        _seed_breach(self.other, "M74O-OTH", "orch-oth")

    def test_orchestrator_dispatches_per_dealership(self):
        result = detect_sla_breaches_for_all_tenants.apply().get()
        self.assertEqual(result["dispatched_tenant_count"], 2)

    def test_per_tenant_task_runs_for_each_tenant(self):
        detect_sla_breaches_for_all_tenants.apply().get()
        per_tenant_rows = list(
            JobRunLog.objects.filter(
                task_name=DETECT_FOR_TENANT_TASK_NAME
            )
        )
        # One row per tenant.
        self.assertEqual(len(per_tenant_rows), 2)
        tenant_stamps = {row.dealership_id for row in per_tenant_rows}
        self.assertEqual(
            tenant_stamps, {self.default.pk, self.other.pk}
        )


class OrchestratorWritesJobRunLog(TestCase):
    """The orchestrator invocation writes its own ``JobRunLog`` row."""

    def test_orchestrator_row_recorded(self):
        detect_sla_breaches_for_all_tenants.apply().get()
        rows = list(
            JobRunLog.objects.filter(
                task_name=DETECT_FOR_ALL_TENANTS_TASK_NAME
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, JOB_RUN_STATUS_SUCCEEDED)


class BeatScheduleEntryRegistered(TestCase):
    """The M7.4 Beat entry is present and correctly configured."""

    def test_entry_exists(self):
        self.assertIn(
            "vendor-sla-scan-daily-04-00",
            settings.CELERY_BEAT_SCHEDULE,
        )

    def test_entry_targets_orchestrator_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE[
            "vendor-sla-scan-daily-04-00"
        ]
        self.assertEqual(entry["task"], DETECT_FOR_ALL_TENANTS_TASK_NAME)

    def test_entry_schedule_is_04_00_daily(self):
        from celery.schedules import crontab

        entry = settings.CELERY_BEAT_SCHEDULE[
            "vendor-sla-scan-daily-04-00"
        ]
        schedule = entry["schedule"]
        self.assertIsInstance(schedule, crontab)
        self.assertEqual(str(schedule._orig_hour), "4")
        self.assertEqual(str(schedule._orig_minute), "0")

    def test_entry_scheduled_after_m7_3_aging_entry(self):
        # Non-overlapping window pattern: M7.4 (04:00) fires after
        # M7.3 (03:00), which fires after M7.2 (02:00).
        aging = settings.CELERY_BEAT_SCHEDULE[
            "stage-aging-snapshot-daily-03-00"
        ]["schedule"]
        sla = settings.CELERY_BEAT_SCHEDULE[
            "vendor-sla-scan-daily-04-00"
        ]["schedule"]
        self.assertLess(int(aging._orig_hour), int(sla._orig_hour))
