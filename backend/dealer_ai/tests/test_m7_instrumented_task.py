"""Milestone 7 · Increment 1 (SESSION_088) — ``@instrumented_task`` tests.

Locks the behavior of :func:`dealer_ai.services.jobs.instrumented_task`:

- One ``JobRunLog`` row per invocation (created on start, updated on
  end — same row, not two).
- Status transitions ``started → succeeded`` on happy path,
  ``started → failed`` on exception.
- ``duration_ms`` populated on end, non-negative integer.
- ``args_summary`` truncated to 255 chars (matches
  ``JobRunLog.args_summary`` field width).
- ``dealership_id`` kwarg propagates to ``JobRunLog.dealership`` (bypasses
  the tenancy autofill default per resolution rule 1).
- Success path returns the task result; failure path re-raises the
  original exception.
- Programming errors (``ValueError`` etc.) are NOT in the retry set;
  transient errors (``ConnectionError`` etc.) ARE.

All tests run under ``CELERY_TASK_ALWAYS_EAGER=True`` (per M7 §5.f), so
task invocations are synchronous and the caller's transaction sees the
``JobRunLog`` writes immediately.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.models import (
    JOB_RUN_STATUS_FAILED,
    JOB_RUN_STATUS_STARTED,
    JOB_RUN_STATUS_SUCCEEDED,
    Dealership,
    JobRunLog,
)
from dealer_ai.services.jobs import instrumented_task
from dealer_ai.services.jobs.instrumentation import (
    INSTRUMENTED_TRANSIENT_ERRORS,
    _summarize_args,
    _truncate,
)


# ---------------------------------------------------------------------------
# Sample tasks (module-level so Celery's autodiscovery can register them
# and the wrapper's ``@shared_task`` composition works cleanly).
# ---------------------------------------------------------------------------


@instrumented_task(name="tests.m7.sample_success")
def _sample_success_task(a, b=1, *, dealership_id=None):
    return a + b


@instrumented_task(name="tests.m7.sample_failure")
def _sample_failure_task(*, dealership_id=None):
    raise ValueError("intentional failure for test")


@instrumented_task(name="tests.m7.sample_returns_none")
def _sample_returns_none_task():
    return None


@instrumented_task(name="tests.m7.sample_tenant_scoped")
def _sample_tenant_scoped_task(*, dealership_id):
    return f"processed for tenant {dealership_id}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class InstrumentedTaskWritesOneRow(TestCase):
    """One ``JobRunLog`` row per invocation — start row is updated in
    place, not deleted-and-replaced or duplicated."""

    def test_single_row_on_success(self):
        _sample_success_task.apply(args=(2,), kwargs={"b": 3}).get()
        rows = list(
            JobRunLog.objects.filter(task_name="tests.m7.sample_success")
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, JOB_RUN_STATUS_SUCCEEDED)

    def test_single_row_on_failure(self):
        with self.assertRaises(ValueError):
            _sample_failure_task.apply().get()
        rows = list(
            JobRunLog.objects.filter(task_name="tests.m7.sample_failure")
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, JOB_RUN_STATUS_FAILED)


class InstrumentedTaskStatusTransitions(TestCase):
    """Status ends at ``succeeded`` or ``failed`` — never leaks
    ``started`` after the task returns."""

    def test_status_ends_at_succeeded(self):
        _sample_success_task.apply(args=(1, 2)).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertEqual(row.status, JOB_RUN_STATUS_SUCCEEDED)
        self.assertNotEqual(row.status, JOB_RUN_STATUS_STARTED)

    def test_status_ends_at_failed(self):
        with self.assertRaises(ValueError):
            _sample_failure_task.apply().get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_failure")
        self.assertEqual(row.status, JOB_RUN_STATUS_FAILED)
        self.assertNotEqual(row.status, JOB_RUN_STATUS_STARTED)


class InstrumentedTaskDurationRecorded(TestCase):
    """``duration_ms`` populates on end, non-negative integer."""

    def test_duration_populated_on_success(self):
        _sample_success_task.apply(args=(1,)).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertIsNotNone(row.duration_ms)
        self.assertGreaterEqual(row.duration_ms, 0)

    def test_duration_populated_on_failure(self):
        with self.assertRaises(ValueError):
            _sample_failure_task.apply().get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_failure")
        self.assertIsNotNone(row.duration_ms)
        self.assertGreaterEqual(row.duration_ms, 0)


class InstrumentedTaskTimestamps(TestCase):
    """``started_at`` set on start; ``ended_at`` set on end; ``ended_at``
    is at or after ``started_at``."""

    def test_started_at_set(self):
        _sample_success_task.apply(args=(1,)).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertIsNotNone(row.started_at)

    def test_ended_at_after_started_at(self):
        _sample_success_task.apply(args=(1,)).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertIsNotNone(row.ended_at)
        self.assertGreaterEqual(row.ended_at, row.started_at)


class InstrumentedTaskArgsSummary(TestCase):
    """``args_summary`` records the args; truncated to 255 chars."""

    def test_args_summary_populated(self):
        _sample_success_task.apply(args=(42,), kwargs={"b": 7}).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertIn("42", row.args_summary)
        # Note: 'b': 7 shows up in kwargs= section of args_summary
        self.assertIn("'b'", row.args_summary)
        self.assertIn("7", row.args_summary)

    def test_args_summary_respects_255_char_field_limit(self):
        # Force truncation by passing a giant string. ``b`` must also
        # be a string here — the sample task body is ``a + b``, which
        # rejects mixed str+int.
        giant = "x" * 500
        _sample_success_task.apply(args=(giant,), kwargs={"b": "y"}).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertLessEqual(len(row.args_summary), 255)
        # And the truncation marker should be present when actually
        # truncated.
        self.assertTrue(row.args_summary.endswith("..."))


class InstrumentedTaskDealershipPropagation(TestCase):
    """``dealership_id`` kwarg propagates to ``JobRunLog.dealership``."""

    def test_dealership_id_populated_when_kwarg_present(self):
        tenant = Dealership.objects.create(
            name="Tenant A", slug="tenant-a"
        )
        _sample_tenant_scoped_task.apply(
            kwargs={"dealership_id": tenant.pk}
        ).get()
        row = JobRunLog.objects.get(
            task_name="tests.m7.sample_tenant_scoped"
        )
        self.assertEqual(row.dealership_id, tenant.pk)

    def test_dealership_falls_back_to_default_when_kwarg_absent(self):
        # No ``dealership_id`` kwarg → the tenancy autofill signal
        # attaches the default row (per resolution rule 3 of
        # ``_auto_attach_default_dealership``).
        _sample_returns_none_task.apply().get()
        row = JobRunLog.objects.get(
            task_name="tests.m7.sample_returns_none"
        )
        default = Dealership.objects.get(slug="default")
        self.assertEqual(row.dealership_id, default.pk)


class InstrumentedTaskReturnsResult(TestCase):
    """Success path returns the task result; failure path re-raises."""

    def test_success_returns_task_result(self):
        result = _sample_success_task.apply(args=(2,), kwargs={"b": 5}).get()
        self.assertEqual(result, 7)

    def test_success_returns_none(self):
        # None-returning tasks (e.g. side-effect-only jobs) still record
        # ``succeeded`` and return ``None``.
        result = _sample_returns_none_task.apply().get()
        self.assertIsNone(result)

    def test_failure_reraises_original_exception(self):
        # The wrapper must NOT swallow the exception (M4-M6 lesson 6:
        # no silent-swallow). CELERY_TASK_EAGER_PROPAGATES=True in
        # tests forwards the raise to ``.get()``.
        with self.assertRaisesRegex(
            ValueError, "intentional failure for test"
        ):
            _sample_failure_task.apply().get()


class InstrumentedTaskErrorMessagePopulatedOnFailure(TestCase):
    """``error_message`` non-blank on failure; blank on success."""

    def test_error_message_populated_on_failure(self):
        with self.assertRaises(ValueError):
            _sample_failure_task.apply().get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_failure")
        self.assertNotEqual(row.error_message, "")
        self.assertIn("ValueError", row.error_message)
        self.assertIn("intentional failure for test", row.error_message)

    def test_error_message_blank_on_success(self):
        _sample_success_task.apply(args=(1,)).get()
        row = JobRunLog.objects.get(task_name="tests.m7.sample_success")
        self.assertEqual(row.error_message, "")


class InstrumentedTaskRetryPolicy(TestCase):
    """Transient errors are in the retry set; programming errors are
    not."""

    def test_transient_errors_include_connection_and_timeout(self):
        # Locks the default transient-error tuple so a future edit that
        # silently narrows it (e.g. dropping OSError) surfaces here.
        self.assertIn(ConnectionError, INSTRUMENTED_TRANSIENT_ERRORS)
        self.assertIn(TimeoutError, INSTRUMENTED_TRANSIENT_ERRORS)
        self.assertIn(OSError, INSTRUMENTED_TRANSIENT_ERRORS)

    def test_programming_errors_not_in_transient_set(self):
        # ValueError / TypeError / AttributeError / AssertionError are
        # bugs — they must fail loud per M4-M6 lesson 6.
        self.assertNotIn(ValueError, INSTRUMENTED_TRANSIENT_ERRORS)
        self.assertNotIn(TypeError, INSTRUMENTED_TRANSIENT_ERRORS)
        self.assertNotIn(AttributeError, INSTRUMENTED_TRANSIENT_ERRORS)
        self.assertNotIn(AssertionError, INSTRUMENTED_TRANSIENT_ERRORS)


class InstrumentedTaskHelpersInternal(TestCase):
    """Internal helpers (``_summarize_args``, ``_truncate``) — small
    smoke tests to lock the truncation contract independently of the
    decorator's happy path."""

    def test_summarize_args_short(self):
        summary = _summarize_args(args=(1, 2), kwargs={"x": 3})
        self.assertIn("args=(1, 2)", summary)
        self.assertIn("kwargs={'x': 3}", summary)

    def test_summarize_args_truncates_to_255(self):
        summary = _summarize_args(args=("x" * 500,), kwargs={})
        self.assertLessEqual(len(summary), 255)
        self.assertTrue(summary.endswith("..."))

    def test_truncate_returns_short_input_unchanged(self):
        self.assertEqual(_truncate("hi", 10), "hi")

    def test_truncate_appends_ellipsis_when_over_limit(self):
        # The output length is bounded by max_len; the last three chars
        # of an over-limit input are the ellipsis.
        out = _truncate("x" * 100, 10)
        self.assertEqual(len(out), 10)
        self.assertTrue(out.endswith("..."))


class InstrumentedTaskCeleryRegistration(TestCase):
    """The wrapped functions are registered as Celery tasks with the
    dotted ``name`` argument passed to the decorator."""

    def test_success_task_registered_by_name(self):
        self.assertEqual(
            _sample_success_task.name, "tests.m7.sample_success"
        )

    def test_failure_task_registered_by_name(self):
        self.assertEqual(
            _sample_failure_task.name, "tests.m7.sample_failure"
        )

    def test_tenant_scoped_task_registered_by_name(self):
        self.assertEqual(
            _sample_tenant_scoped_task.name,
            "tests.m7.sample_tenant_scoped",
        )


class InstrumentedTaskRowCountIsExactlyOnePerInvocation(TestCase):
    """Two invocations of the same task produce two rows (not one, and
    not three)."""

    def test_two_invocations_two_rows(self):
        _sample_success_task.apply(args=(1,)).get()
        _sample_success_task.apply(args=(2,)).get()
        rows = list(
            JobRunLog.objects.filter(task_name="tests.m7.sample_success")
        )
        self.assertEqual(len(rows), 2)
        # Both ended at succeeded.
        for row in rows:
            self.assertEqual(row.status, JOB_RUN_STATUS_SUCCEEDED)
