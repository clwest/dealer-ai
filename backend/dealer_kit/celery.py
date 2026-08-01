"""Milestone 7 · Increment 1 (SESSION_088) — Celery application instance.

Wires the Celery app to Django settings per the standard Django-Celery
pattern (Celery docs "First steps with Django"). Owns three things:

1. **App instantiation** — one module-level :class:`celery.Celery`
   instance named after the Django project package (``"dealer_kit"``).
2. **Django settings binding** — the app pulls every ``CELERY_*``
   setting from :mod:`django.conf.settings` at import time via
   :meth:`celery.Celery.config_from_object` with the ``CELERY``
   namespace.
3. **Autodiscovery** — installed apps are scanned for a ``tasks``
   submodule (``dealer_ai.tasks`` today; future ``services/**/tasks.py``
   modules once the M7.2-M7.5 job bodies land) so job authors register
   tasks without editing this file.

**Broker.** Redis per §5.a Option A (user-confirmed at SESSION_088
open). URL sourced from :attr:`django.conf.settings.CELERY_BROKER_URL`
which resolves the ``REDIS_URL`` env var with a
``redis://localhost:6379/0`` fallback for local development.

**Test posture.** ``CELERY_TASK_ALWAYS_EAGER`` is set inside
:mod:`dealer_kit.settings` when the Django test runner is active
(mirrors the M5.5 test-only signal-registration pattern). This module
does not gate anything on ``sys.argv`` — the setting is authoritative.

**No Beat schedule entries in M7.1.** The
``CELERY_BEAT_SCHEDULE`` setting is an empty dict. Scheduled job
bodies land in M7.2-M7.5; each increment appends its own entry.

Source of truth: ``docs/roadmap/MILESTONE_7_PLANNING.md`` §1.1 +
§7 M7.1.
"""

from __future__ import annotations

import os

from celery import Celery

# Standard Django-Celery bootstrap: point Celery at the Django settings
# module so ``config_from_object`` finds every ``CELERY_*`` key. The
# fallback matches ``manage.py`` / ``wsgi.py`` / ``asgi.py`` — a mismatch
# here would cause the Celery worker to read a different settings module
# than the web process, which is exactly the "silent divergence" the
# M4-M6 lesson-2 ("backend-first architecture") warns against.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dealer_kit.settings")

app = Celery("dealer_kit")

# Pull every ``CELERY_*`` key from Django settings under the ``CELERY``
# namespace. E.g. ``CELERY_BROKER_URL`` in settings.py binds to
# ``app.conf.broker_url``. This is the Celery-recommended pattern for
# Django integration and keeps configuration in one place
# (settings.py — same file operators already edit for every other
# knob).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover ``tasks`` submodules under each installed Django app.
# M7.1 registers no tasks; M7.2-M7.5 will land ``services/<domain>/tasks.py``
# (or module-level ``dealer_ai/tasks.py``) modules discovered here.
# Any app in ``INSTALLED_APPS`` that ships a ``tasks`` submodule at
# import time is picked up without further wiring.
app.autodiscover_tasks()
