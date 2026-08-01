"""Milestone 7 · Increment 1 (SESSION_088) — job-runtime helpers.

Small package that hosts the cross-cutting task-runtime primitives
(:func:`instrumented_task` decorator, job-log write helpers). Kept
separate from ``services/`` domain modules so:

- Every future ``services/<domain>/tasks.py`` module can import the
  decorator without a circular import through a business-logic module.
- Test doubles for the decorator (fake time, in-memory log capture) can
  swap the whole package with ``django.test.override_settings`` or a
  ``patch`` in one place.

Public surface:

- :func:`instrumented_task` — the shared decorator wrapping every
  Celery task with structured logging + ``JobRunLog`` writes + a
  retry-on-transient-error policy.
"""

from __future__ import annotations

from .instrumentation import instrumented_task

__all__ = ("instrumented_task",)
