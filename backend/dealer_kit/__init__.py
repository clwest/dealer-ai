"""Milestone 7 · Increment 1 (SESSION_088) — expose the Celery app.

The Django-Celery integration pattern requires importing the Celery app
at project-package load time so ``@shared_task`` decorators registered
inside app ``tasks`` modules find the running app when autodiscovery
runs. See ``celery.py`` in this package for the app instance.

Exposed as ``celery_app`` (not just ``app``) to avoid shadowing the
common ``app`` name in downstream imports.
"""

from __future__ import annotations

from .celery import app as celery_app

__all__ = ("celery_app",)
