"""Milestone 7 · Increment 1 (SESSION_088) — ``JobRunLog`` model shape.

Locks the persistence-layer contract for :class:`dealer_ai.models.JobRunLog`:

- Fields exist with the right types + null/blank flags.
- Status enum vocabulary is the four expected values.
- ``__str__`` renders task-name + status + timestamp.
- Default ordering surfaces the most recent row first.
- The composite ``(task_name, -started_at)`` index is registered.
- ``dealership`` FK uses ``SET_NULL`` (deleting a tenant does NOT cascade
  and remove historical audit rows).

Mirrors the M5.1 shape in ``test_vehicle_stage_persistence.py`` and the
M6.1 shape in ``test_vehicle_photo_persistence.py``.
"""

from __future__ import annotations

from django.db import models
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    JOB_RUN_STATUS_CHOICES,
    JOB_RUN_STATUS_FAILED,
    JOB_RUN_STATUS_RETRIED,
    JOB_RUN_STATUS_STARTED,
    JOB_RUN_STATUS_SUCCEEDED,
    Dealership,
    JobRunLog,
)


class JobRunLogFieldShape(TestCase):
    """Field types + null/blank flags — the persistence contract."""

    def test_task_name_char_field_indexed(self):
        field = JobRunLog._meta.get_field("task_name")
        self.assertIsInstance(field, models.CharField)
        self.assertTrue(field.db_index)
        self.assertEqual(field.max_length, 255)

    def test_status_char_field_indexed_with_choices(self):
        field = JobRunLog._meta.get_field("status")
        self.assertIsInstance(field, models.CharField)
        self.assertTrue(field.db_index)
        self.assertEqual(field.max_length, 16)
        self.assertEqual(tuple(field.choices), JOB_RUN_STATUS_CHOICES)

    def test_started_at_is_datetime_not_null(self):
        field = JobRunLog._meta.get_field("started_at")
        self.assertIsInstance(field, models.DateTimeField)
        self.assertFalse(field.null)

    def test_ended_at_is_nullable_datetime(self):
        field = JobRunLog._meta.get_field("ended_at")
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_duration_ms_is_nullable_positive_integer(self):
        field = JobRunLog._meta.get_field("duration_ms")
        self.assertIsInstance(field, models.PositiveIntegerField)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_error_message_is_text_blank_default_empty(self):
        field = JobRunLog._meta.get_field("error_message")
        self.assertIsInstance(field, models.TextField)
        self.assertTrue(field.blank)
        self.assertEqual(field.default, "")

    def test_args_summary_is_char_max_255(self):
        field = JobRunLog._meta.get_field("args_summary")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 255)
        self.assertTrue(field.blank)
        self.assertEqual(field.default, "")

    def test_dealership_fk_nullable_set_null(self):
        field = JobRunLog._meta.get_field("dealership")
        self.assertIsInstance(field, models.ForeignKey)
        self.assertTrue(field.null)
        self.assertTrue(field.blank)
        # Deleting a tenant must NOT cascade and delete audit rows.
        self.assertEqual(
            field.remote_field.on_delete.__name__, "SET_NULL"
        )


class JobRunLogStatusVocabulary(TestCase):
    """The four expected status values."""

    def test_status_choices_are_the_four_expected(self):
        codes = {code for code, _label in JOB_RUN_STATUS_CHOICES}
        self.assertEqual(
            codes,
            {"started", "succeeded", "failed", "retried"},
        )

    def test_status_module_constants_match_choices(self):
        self.assertEqual(JOB_RUN_STATUS_STARTED, "started")
        self.assertEqual(JOB_RUN_STATUS_SUCCEEDED, "succeeded")
        self.assertEqual(JOB_RUN_STATUS_FAILED, "failed")
        self.assertEqual(JOB_RUN_STATUS_RETRIED, "retried")


class JobRunLogMetaContract(TestCase):
    """Default ordering + composite index."""

    def test_default_ordering_is_most_recent_first(self):
        self.assertEqual(
            tuple(JobRunLog._meta.ordering), ("-started_at",)
        )

    def test_composite_task_started_index_registered(self):
        index_names = {idx.name for idx in JobRunLog._meta.indexes}
        self.assertIn("jrl_task_started_idx", index_names)


class JobRunLogStrRepresentation(TestCase):
    """``__str__`` includes task_name, status, and started_at."""

    def test_str_includes_task_name_status_and_time(self):
        row = JobRunLog.objects.create(
            task_name="tests.m7.str",
            status=JOB_RUN_STATUS_STARTED,
            started_at=timezone.now(),
        )
        rendered = str(row)
        self.assertIn("tests.m7.str", rendered)
        self.assertIn("started", rendered)


class JobRunLogWriteReadRoundTrip(TestCase):
    """Basic ORM round-trip so a broken migration surfaces here."""

    def test_write_read_start_row(self):
        default = Dealership.objects.get(slug="default")
        now = timezone.now()
        row = JobRunLog.objects.create(
            task_name="tests.m7.roundtrip",
            status=JOB_RUN_STATUS_STARTED,
            started_at=now,
            args_summary="args=() kwargs={}",
            dealership=default,
        )
        fetched = JobRunLog.objects.get(pk=row.pk)
        self.assertEqual(fetched.task_name, "tests.m7.roundtrip")
        self.assertEqual(fetched.status, JOB_RUN_STATUS_STARTED)
        self.assertEqual(fetched.dealership_id, default.pk)
        self.assertIsNone(fetched.ended_at)
        self.assertIsNone(fetched.duration_ms)

    def test_update_to_terminal_state_preserves_start_fields(self):
        row = JobRunLog.objects.create(
            task_name="tests.m7.roundtrip.terminal",
            status=JOB_RUN_STATUS_STARTED,
            started_at=timezone.now(),
        )
        original_started_at = row.started_at
        row.status = JOB_RUN_STATUS_SUCCEEDED
        row.ended_at = timezone.now()
        row.duration_ms = 42
        row.save(update_fields=("status", "ended_at", "duration_ms"))
        row.refresh_from_db()
        # Start-time invariant per model docstring — the start row is
        # updated in place; started_at never moves.
        self.assertEqual(row.started_at, original_started_at)
        self.assertEqual(row.status, JOB_RUN_STATUS_SUCCEEDED)
        self.assertEqual(row.duration_ms, 42)


class JobRunLogFailureRowShape(TestCase):
    """A failed row carries a nonblank error_message."""

    def test_failed_row_carries_error_message(self):
        row = JobRunLog.objects.create(
            task_name="tests.m7.failed",
            status=JOB_RUN_STATUS_FAILED,
            started_at=timezone.now(),
            ended_at=timezone.now(),
            duration_ms=5,
            error_message="ValueError('boom')",
        )
        fetched = JobRunLog.objects.get(pk=row.pk)
        self.assertEqual(fetched.status, JOB_RUN_STATUS_FAILED)
        self.assertNotEqual(fetched.error_message, "")


class JobRunLogRetriedStatusValid(TestCase):
    """``retried`` is a valid terminal-for-this-attempt status."""

    def test_retried_row_saves(self):
        row = JobRunLog.objects.create(
            task_name="tests.m7.retried",
            status=JOB_RUN_STATUS_RETRIED,
            started_at=timezone.now(),
            ended_at=timezone.now(),
            duration_ms=10,
        )
        fetched = JobRunLog.objects.get(pk=row.pk)
        self.assertEqual(fetched.status, JOB_RUN_STATUS_RETRIED)


class JobRunLogDealershipSetNullOnDelete(TestCase):
    """Deleting a tenant preserves the audit row (SET_NULL)."""

    def test_delete_tenant_sets_dealership_null(self):
        tenant = Dealership.objects.create(
            name="Ephemeral", slug="ephemeral"
        )
        row = JobRunLog.objects.create(
            task_name="tests.m7.set_null",
            status=JOB_RUN_STATUS_SUCCEEDED,
            started_at=timezone.now(),
            ended_at=timezone.now(),
            duration_ms=1,
            dealership=tenant,
        )
        tenant.delete()
        row.refresh_from_db()
        self.assertIsNone(row.dealership_id)
        # Row still exists (audit history preserved).
        self.assertTrue(JobRunLog.objects.filter(pk=row.pk).exists())
