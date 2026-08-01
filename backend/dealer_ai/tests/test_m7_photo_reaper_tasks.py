"""Milestone 7 · Increment 5 (SESSION_092) — photo reaper Celery task tests.

Locks the two Celery task shells + the Beat schedule entry:

- ``reap_tombstoned_photos_for_tenant`` — per-tenant; writes one
  ``JobRunLog`` row stamped with the tenant; returns a JSON-safe
  dict.
- ``reap_tombstoned_photos_for_all_tenants`` — orchestrator; enqueues
  per-tenant tasks via ``.delay()``.
- ``CELERY_BEAT_SCHEDULE`` — entry firing the orchestrator at 05:00
  daily (after M7.2 02:00, M7.3 03:00, M7.4 04:00).

Runs under ``CELERY_TASK_ALWAYS_EAGER=True`` (M7.1).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    JOB_RUN_STATUS_SUCCEEDED,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    Dealership,
    JobRunLog,
    Vehicle,
    VehiclePhoto,
)
from dealer_ai.services.photo_gallery import upload_photo
from dealer_ai.services.photo_gallery.reaper import PHOTO_RETENTION_DAYS
from dealer_ai.services.photo_gallery.tasks import (
    REAP_FOR_ALL_TENANTS_TASK_NAME,
    REAP_FOR_TENANT_TASK_NAME,
    reap_tombstoned_photos_for_all_tenants,
    reap_tombstoned_photos_for_tenant,
)


_SAMPLE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-body"


def _seed_reapable_photo(
    dealership: Dealership, stock: str
) -> VehiclePhoto:
    """Create a photo tombstoned past the retention window — a
    guaranteed reaper candidate."""
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    photo = upload_photo(
        vehicle,
        dealership=dealership,
        data=_SAMPLE_BYTES,
        content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
        width_px=1920,
        height_px=1080,
    )
    photo.marked_deleted_at = timezone.now() - dt.timedelta(
        days=PHOTO_RETENTION_DAYS + 1
    )
    photo.is_primary = False
    photo.save(
        update_fields=["marked_deleted_at", "is_primary", "updated_at"]
    )
    return photo


class TaskNames(TestCase):
    """Both tasks registered under the canonical dotted names."""

    def test_per_tenant_task_name(self):
        self.assertEqual(
            reap_tombstoned_photos_for_tenant.name,
            REAP_FOR_TENANT_TASK_NAME,
        )
        self.assertEqual(
            REAP_FOR_TENANT_TASK_NAME,
            "dealer_ai.services.photo_gallery.tasks"
            ".reap_tombstoned_photos_for_tenant",
        )

    def test_orchestrator_task_name(self):
        self.assertEqual(
            reap_tombstoned_photos_for_all_tenants.name,
            REAP_FOR_ALL_TENANTS_TASK_NAME,
        )
        self.assertEqual(
            REAP_FOR_ALL_TENANTS_TASK_NAME,
            "dealer_ai.services.photo_gallery.tasks"
            ".reap_tombstoned_photos_for_all_tenants",
        )


class PerTenantTaskReturnsDict(TestCase):
    """Per-tenant task calls the verb and returns JSON-safe dict."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.photo = _seed_reapable_photo(self.default, "M75T-A")

    def test_task_return_value_shape(self):
        result = reap_tombstoned_photos_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        self.assertIsInstance(result, dict)
        self.assertEqual(result["dealership_id"], self.default.pk)
        self.assertEqual(result["dealership_slug"], "default")
        self.assertEqual(result["candidates"], 1)
        self.assertEqual(result["deleted"], 1)
        self.assertEqual(result["storage_failed"], 0)
        self.assertEqual(result["deleted_photo_ids"], [self.photo.pk])
        self.assertEqual(result["storage_failed_photo_ids"], [])
        # as_of serialized as ISO string.
        self.assertIsInstance(result["as_of"], str)


class PerTenantTaskWritesJobRunLog(TestCase):
    """One ``JobRunLog`` row per invocation, stamped with tenant."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_job_run_log_row_created(self):
        reap_tombstoned_photos_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        rows = list(
            JobRunLog.objects.filter(
                task_name=REAP_FOR_TENANT_TASK_NAME
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
        explicit = timezone.now() - dt.timedelta(hours=1)
        result = reap_tombstoned_photos_for_tenant.apply(
            kwargs={
                "dealership_id": self.default.pk,
                "as_of_iso": explicit.isoformat(),
            }
        ).get()
        self.assertEqual(result["as_of"], explicit.isoformat())

    def test_as_of_iso_none_defaults_to_now(self):
        before = timezone.now()
        result = reap_tombstoned_photos_for_tenant.apply(
            kwargs={"dealership_id": self.default.pk}
        ).get()
        after = timezone.now()
        parsed = dt.datetime.fromisoformat(result["as_of"])
        self.assertGreaterEqual(parsed, before)
        self.assertLessEqual(parsed, after)


class OrchestratorFansOutToAllTenants(TestCase):
    """The orchestrator enqueues one per-tenant task per Dealership."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other-r-orch")
        self.p_def = _seed_reapable_photo(self.default, "M75O-DEF")
        self.p_oth = _seed_reapable_photo(self.other, "M75O-OTH")

    def test_orchestrator_dispatches_per_dealership(self):
        result = reap_tombstoned_photos_for_all_tenants.apply().get()
        self.assertEqual(result["dispatched_tenant_count"], 2)

    def test_per_tenant_task_runs_for_each_tenant(self):
        reap_tombstoned_photos_for_all_tenants.apply().get()
        per_tenant_rows = list(
            JobRunLog.objects.filter(
                task_name=REAP_FOR_TENANT_TASK_NAME
            )
        )
        self.assertEqual(len(per_tenant_rows), 2)
        tenant_stamps = {row.dealership_id for row in per_tenant_rows}
        self.assertEqual(
            tenant_stamps, {self.default.pk, self.other.pk}
        )

    def test_orchestrator_causes_per_tenant_reaping(self):
        reap_tombstoned_photos_for_all_tenants.apply().get()
        # Both tenants' reapable photos are gone.
        self.assertFalse(
            VehiclePhoto.objects.filter(pk=self.p_def.pk).exists()
        )
        self.assertFalse(
            VehiclePhoto.objects.filter(pk=self.p_oth.pk).exists()
        )


class OrchestratorWritesJobRunLog(TestCase):
    """The orchestrator invocation writes its own ``JobRunLog`` row."""

    def test_orchestrator_row_recorded(self):
        reap_tombstoned_photos_for_all_tenants.apply().get()
        rows = list(
            JobRunLog.objects.filter(
                task_name=REAP_FOR_ALL_TENANTS_TASK_NAME
            )
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, JOB_RUN_STATUS_SUCCEEDED)


class BeatScheduleEntryRegistered(TestCase):
    """The M7.5 Beat entry is present and correctly configured."""

    def test_entry_exists(self):
        self.assertIn(
            "photo-tombstone-reaper-daily-05-00",
            settings.CELERY_BEAT_SCHEDULE,
        )

    def test_entry_targets_orchestrator_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE[
            "photo-tombstone-reaper-daily-05-00"
        ]
        self.assertEqual(entry["task"], REAP_FOR_ALL_TENANTS_TASK_NAME)

    def test_entry_schedule_is_05_00_daily(self):
        from celery.schedules import crontab

        entry = settings.CELERY_BEAT_SCHEDULE[
            "photo-tombstone-reaper-daily-05-00"
        ]
        schedule = entry["schedule"]
        self.assertIsInstance(schedule, crontab)
        self.assertEqual(str(schedule._orig_hour), "5")
        self.assertEqual(str(schedule._orig_minute), "0")

    def test_entry_scheduled_after_m7_4_vendor_sla(self):
        # Non-overlapping window pattern: M7.5 (05:00) fires after
        # M7.4 (04:00), which fires after M7.3 (03:00) and M7.2
        # (02:00).
        sla = settings.CELERY_BEAT_SCHEDULE[
            "vendor-sla-scan-daily-04-00"
        ]["schedule"]
        reaper = settings.CELERY_BEAT_SCHEDULE[
            "photo-tombstone-reaper-daily-05-00"
        ]["schedule"]
        self.assertLess(int(sla._orig_hour), int(reaper._orig_hour))


class AllFourM7BeatEntriesRegistered(TestCase):
    """Cumulative M7 audit: all four scheduled jobs land in the Beat
    schedule dict with the expected sequential 02:00→05:00 pattern."""

    def test_all_four_entries_present(self):
        expected_entries = {
            "floor-plan-accrual-daily-02-00": 2,
            "stage-aging-snapshot-daily-03-00": 3,
            "vendor-sla-scan-daily-04-00": 4,
            "photo-tombstone-reaper-daily-05-00": 5,
        }
        for entry_name, expected_hour in expected_entries.items():
            self.assertIn(
                entry_name,
                settings.CELERY_BEAT_SCHEDULE,
                f"M7 Beat entry {entry_name!r} not registered",
            )
            entry = settings.CELERY_BEAT_SCHEDULE[entry_name]
            self.assertEqual(
                str(entry["schedule"]._orig_hour),
                str(expected_hour),
                f"{entry_name!r} not scheduled at hour {expected_hour}",
            )
