"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote service package.

Three verbs per ``MILESTONE_12_PLANNING.md`` §7 M12.1 + §5.a Option A
(user-confirmed at SESSION_121 open, recorded in §0.a):

- :func:`record_bhph_note` — originate a BhphNote against a BHPH Sale.
  Computes ``payment_amount`` via
  :func:`services.payment_engine.bhph_note_periodic_payment` and
  persists the row. Refuses non-BHPH sales, cross-tenant sales, and
  duplicate notes per sale.
- :func:`get_bhph_note` — tenant-scoped read.
- :func:`get_payment_schedule` — pure verb returning the computed
  schedule (list of ``(due_date, amount)`` tuples). No DB writes —
  the per-payment intake entity lands at M12.2.

Domain errors:

- :class:`NonBhphSaleError` — 400 at endpoint layer (sale exists but
  ``finance_type != "bhph"``).
- :class:`CrossTenantBhphNoteError` — 404 (fail-closed).
- :class:`DuplicateBhphNoteError` — 409 (one BhphNote per Sale by
  schema; the service verb raises before the OneToOne write fails).
"""

from __future__ import annotations

from .bhph_note import (
    CrossTenantBhphNoteError,
    DuplicateBhphNoteError,
    NonBhphSaleError,
    get_bhph_note,
    get_payment_schedule,
    record_bhph_note,
)

__all__ = [
    "CrossTenantBhphNoteError",
    "DuplicateBhphNoteError",
    "NonBhphSaleError",
    "get_bhph_note",
    "get_payment_schedule",
    "record_bhph_note",
]
