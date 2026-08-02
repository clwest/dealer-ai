"""Milestone 12 · Increment 6 (SESSION_126) — Repossession service package.

Three verbs per ``MILESTONE_12_PLANNING.md`` §7 M12.6 + §0.a M12.6
decisions 1-5 (as-recommended):

- :func:`record_repossession` — issue the repossession order.
- :func:`mark_recovered` — ordered → recovered. Populates
  ``recovered_at`` + ``recovery_location``.
- :func:`mark_re_intaked` — recovered → re_intaked. Requires a
  :class:`ConditionReport` reference (the vehicle re-entering the
  M4 recon substrate as a fresh inspection).

Domain errors:

- :class:`CrossTenantRepossessionError` — 404 at endpoint layer.
- :class:`CrossTenantConditionReportError` — 400.
- :class:`RepossessionAlreadyTerminalError` — 409 (state-machine
  violation; ``re_intaked`` is final).
- :class:`InvalidStateTransitionError` — 409 (attempted transition
  that isn't the next legal step; e.g. ordered → re_intaked without
  recovering first).
"""

from __future__ import annotations

from .repossession import (
    CrossTenantConditionReportError,
    CrossTenantRepossessionError,
    InvalidStateTransitionError,
    RepossessionAlreadyTerminalError,
    list_repossessions,
    mark_re_intaked,
    mark_recovered,
    record_repossession,
)

__all__ = [
    "CrossTenantConditionReportError",
    "CrossTenantRepossessionError",
    "InvalidStateTransitionError",
    "RepossessionAlreadyTerminalError",
    "list_repossessions",
    "mark_re_intaked",
    "mark_recovered",
    "record_repossession",
]
