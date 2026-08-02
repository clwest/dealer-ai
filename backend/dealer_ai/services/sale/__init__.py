"""Milestone 9 · Increment 1 (SESSION_100) — Sale service surface.

The one place all Sale write/read verbs live. Answers the Milestone
9 Q1 + Q3-precondition questions for any Vehicle:

- *"When this vehicle sold, what did we realize on it?"*
  (:func:`record_sale` writes the row + populates
  ``gross_realized`` at write time.)
- *"Recompute this sale's gross_realized against current ledger
  state."* (:func:`gross_realized` — pure verb, never mutates.)

Layer discipline mirrors ``services.vehicle_ledger``: identity +
authorization live in the view layer; data-scoping + business
semantics live here. Every write function accepts an explicit
``dealership`` kwarg and refuses to touch a Vehicle in another
tenant (:class:`CrossTenantSaleError`).

See ``docs/roadmap/MILESTONE_9_PLANNING.md`` §1.1 + §1.4 for the
contract.
"""

from __future__ import annotations

from .computation import (
    CrossTenantSaleError,
    SaleAlreadyExistsError,
    gross_realized,
    record_sale,
)

__all__ = [
    "CrossTenantSaleError",
    "SaleAlreadyExistsError",
    "gross_realized",
    "record_sale",
]
