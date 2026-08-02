"""Milestone 11 · Increment 5 (SESSION_118) — BeBack service package.

Three verbs per ``MILESTONE_11_PLANNING.md`` §1.5 + §5.g Options A /
A / B (recorded in §0.a at SESSION_118 open):

- :func:`record_be_back` — customer promises to return.
- :func:`mark_returned` — promised → returned.
- :func:`mark_no_show` — promised → no_show. Called by the M11.5
  Celery detector when the grace period elapses, also exposed as
  an operator-triggered endpoint.

Domain errors:

- :class:`CrossTenantBeBackError` — 404 at endpoint layer.
- :class:`UnknownReasonError` — 400 (reason not in the 4+1 vocab).
- :class:`BeBackAlreadyTerminalError` — 409 (state-machine
  violation; terminal states are final).
"""

from __future__ import annotations

from .be_back import (
    BeBackAlreadyTerminalError,
    CrossTenantBeBackError,
    UnknownReasonError,
    mark_no_show,
    mark_returned,
    record_be_back,
)

__all__ = [
    "BeBackAlreadyTerminalError",
    "CrossTenantBeBackError",
    "UnknownReasonError",
    "mark_no_show",
    "mark_returned",
    "record_be_back",
]
