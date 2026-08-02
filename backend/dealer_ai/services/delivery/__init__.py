"""Milestone 9 · Increment 2 (SESSION_101) — Delivery service surface.

The one place all Delivery write verbs live. Answers the Milestone 9
Q2 questions for any Sale:

- *"Start the delivery workflow for this Sale."*
  (:func:`record_delivery` creates the Delivery row with the M9.2
  checklist keys defaulted to False.)
- *"Mark a checklist item complete."*
  (:func:`update_checklist_item` toggles a single key; refuses keys
  outside the M9.2 vocabulary.)
- *"Verify insurance."* (:func:`verify_insurance` writes both the
  denormalized column + the ``insurance_verified`` checklist key
  atomically.)

Layer discipline mirrors ``services.sale``: identity + authorization
live in the view layer; data-scoping + business semantics live here.
Every write function accepts an explicit ``dealership`` kwarg and
refuses to touch a Sale in another tenant
(:class:`CrossTenantDeliveryError`).

See ``docs/roadmap/MILESTONE_9_PLANNING.md`` §1.2 for the field
contract.
"""

from __future__ import annotations

from .workflow import (
    CrossTenantDeliveryError,
    DeliveryAlreadyExistsError,
    SaleNotFoundForDeliveryError,
    UnknownChecklistKeyError,
    record_delivery,
    update_checklist_item,
    verify_insurance,
)

__all__ = [
    "CrossTenantDeliveryError",
    "DeliveryAlreadyExistsError",
    "SaleNotFoundForDeliveryError",
    "UnknownChecklistKeyError",
    "record_delivery",
    "update_checklist_item",
    "verify_insurance",
]
