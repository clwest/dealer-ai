"""Milestone 11 · Increment 4 (SESSION_117) — Follow-up cadence service package.

Four verbs per ``MILESTONE_11_PLANNING.md`` §1.4 + §5.d Option A:

- :func:`start_cadence` — creates a :class:`FollowUpCadence` header
  + seeds :class:`FollowUpTask` rows from the template's offset
  schedule.
- :func:`complete_task` — pending → completed.
- :func:`skip_task` — pending → skipped.
- :func:`pause_cadence` — sets ``is_active=False``, halting future
  beat surfacing without deleting the task rows.

Domain errors:

- :class:`CrossTenantCadenceError` — 404 at endpoint layer.
- :class:`CrossTenantTaskError` — 404 at endpoint layer.
- :class:`DuplicateActiveCadenceError` — 409; a single active
  cadence per (lead, template) at any time.
- :class:`UnknownTemplateError` — 400.
- :class:`TaskAlreadyTerminalError` — 409; state-machine violation
  (a completed / skipped task cannot re-transition).

The M11.4 Celery-beat orchestrator lives in
:mod:`.tasks` (autodiscovered by ``dealer_kit/celery.py``). Its
Beat schedule entry is registered in ``dealer_kit/settings.py`` at
06:00 project-time daily.
"""

from __future__ import annotations

from .cadence import (
    CrossTenantCadenceError,
    CrossTenantTaskError,
    DuplicateActiveCadenceError,
    TaskAlreadyTerminalError,
    UnknownTemplateError,
    complete_task,
    pause_cadence,
    skip_task,
    start_cadence,
)

__all__ = [
    "CrossTenantCadenceError",
    "CrossTenantTaskError",
    "DuplicateActiveCadenceError",
    "TaskAlreadyTerminalError",
    "UnknownTemplateError",
    "complete_task",
    "pause_cadence",
    "skip_task",
    "start_cadence",
]
