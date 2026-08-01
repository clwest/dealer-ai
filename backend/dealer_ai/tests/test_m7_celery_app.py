"""Milestone 7 · Increment 1 (SESSION_088) — Celery app + settings tests.

Verifies the ``backend/dealer_kit/celery.py`` app boots, reads settings
from the correct Django module, exposes the empty M7.1 Beat schedule,
and locks the M7 §5.f test posture (``CELERY_TASK_ALWAYS_EAGER=True``
when the test runner is active).

These tests exercise Celery's Django integration surface — the app
instance, not any user-authored task. The instrumented-decorator +
JobRunLog behavior lives in ``test_m7_instrumented_task.py``.
"""

from __future__ import annotations

from django.conf import settings
from django.test import TestCase

from dealer_kit import celery_app


class CeleryAppInstantiated(TestCase):
    """The module-level Celery app exists with the project name."""

    def test_app_name_matches_project_package(self):
        self.assertEqual(celery_app.main, "dealer_kit")


class CeleryConfigFromDjangoSettings(TestCase):
    """``config_from_object`` binds every ``CELERY_*`` setting."""

    def test_broker_url_bound_from_settings(self):
        self.assertEqual(
            celery_app.conf.broker_url,
            settings.CELERY_BROKER_URL,
        )

    def test_result_backend_bound_from_settings(self):
        self.assertEqual(
            celery_app.conf.result_backend,
            settings.CELERY_RESULT_BACKEND,
        )

    def test_broker_url_defaults_to_local_redis(self):
        # The default resolution path is
        # ``REDIS_URL env → redis://localhost:6379/0``. Prod overrides
        # via env. This test locks the default so a future settings
        # edit that silently drops the fallback surfaces as a failure.
        self.assertTrue(
            celery_app.conf.broker_url.startswith("redis://"),
            f"Expected Redis URL, got {celery_app.conf.broker_url!r}",
        )


class CeleryTestPosture(TestCase):
    """M7 §5.f — tests never depend on a running broker."""

    def test_task_always_eager_is_true_in_tests(self):
        # ``settings._is_running_tests()`` returns True under the Django
        # test runner (``sys.argv[1] == 'test'``). CELERY_TASK_ALWAYS_EAGER
        # follows that value.
        self.assertTrue(settings.CELERY_TASK_ALWAYS_EAGER)
        self.assertTrue(celery_app.conf.task_always_eager)

    def test_eager_propagates_is_true_in_tests(self):
        # ``EAGER_PROPAGATES=True`` — exceptions bubble out of task
        # invocations instead of being wrapped in ``EagerResult.failed``.
        self.assertTrue(settings.CELERY_TASK_EAGER_PROPAGATES)
        self.assertTrue(celery_app.conf.task_eager_propagates)


class CeleryBeatSchedule(TestCase):
    """The Beat schedule is a dict-typed container. Individual entries
    are asserted by the increment that owns them (M7.2 owns the
    floor-plan entry, M7.3 will own the aging-snapshot entry, etc).

    Prior to SESSION_089 (M7.2) this test asserted the empty starting
    state — that assertion held for exactly one increment (M7.1). The
    exact-shape lock now lives in each increment's own test module so
    future extensions do not need to update prior increments' tests.
    """

    def test_beat_schedule_is_dict_typed(self):
        # A ``dict`` (never ``None``) so downstream code can call
        # ``.get()`` / iterate without a guard.
        self.assertIsInstance(celery_app.conf.beat_schedule, dict)

    def test_beat_schedule_entries_have_required_shape(self):
        # Every registered entry must expose ``task`` (dotted task
        # name) + ``schedule`` (a schedule object). Any entry missing
        # these fields is a mis-registration and would fail at Beat
        # startup — surfacing it here catches the mistake earlier.
        for entry_name, entry in celery_app.conf.beat_schedule.items():
            self.assertIn(
                "task",
                entry,
                f"Beat entry {entry_name!r} missing required 'task' key",
            )
            self.assertIn(
                "schedule",
                entry,
                f"Beat entry {entry_name!r} missing required 'schedule' key",
            )

    def test_beat_scheduler_is_database_scheduler(self):
        # DB-backed scheduler per §5.f (django-celery-beat). Locks the
        # posture so an accidental settings edit reverting to the
        # in-memory ``PersistentScheduler`` surfaces here.
        self.assertEqual(
            celery_app.conf.beat_scheduler,
            "django_celery_beat.schedulers:DatabaseScheduler",
        )


class CeleryTimezoneAlignment(TestCase):
    """M7 §5.f — Celery timezone matches Django's TIME_ZONE."""

    def test_celery_timezone_matches_django(self):
        self.assertEqual(celery_app.conf.timezone, settings.TIME_ZONE)


class CelerySerializationPins(TestCase):
    """JSON-only serialization — no accidental pickle."""

    def test_task_serializer_is_json(self):
        self.assertEqual(celery_app.conf.task_serializer, "json")

    def test_result_serializer_is_json(self):
        self.assertEqual(celery_app.conf.result_serializer, "json")

    def test_accept_content_is_json_only(self):
        self.assertEqual(list(celery_app.conf.accept_content), ["json"])
