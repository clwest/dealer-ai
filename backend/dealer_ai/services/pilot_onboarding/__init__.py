"""Milestone 19 · Increment 1 (SESSION_154) — pilot onboarding package.

Per MILESTONE_19_PLANNING.md §5.a Option V + §5.b-§5.h (all user-
confirmed at SESSION_153 open) + §0.a M19.1 decisions (user-
confirmed at SESSION_154 open). Founder-led pilot conversion
substrate — builds the controlled path from a demo tester who says
"I want to try this with my store" to a safe, usable real-store
pilot without ad hoc database work or code edits.

Public API:

- :func:`create_pilot_dealership` — atomic create + COA seed +
  owner membership + profile populate + auto-fired checklist.
- :func:`list_pilot_dealerships` — pure read of active pilots.
- :func:`terminate_pilot` — atomic termination with
  ``archive`` or ``cleanup`` mode.
- :func:`create_prospect` — atomic create of a pre-tenant
  operator record.
- :func:`advance_prospect_state` — state machine transition.
- :func:`list_prospects` — pure read of every prospect.
- :func:`advance_step` — atomic checklist step advance with
  readiness precondition + immutability guard.
- :func:`is_pilot_ready` — pure predicate over the checklist
  ``is_ready`` flag.
- :class:`PilotInventoryImportResult` — frozen dataclass return
  contract (M19.1 stub; full body at M19.2).
- :class:`PilotAlreadyExistsError` — 409 (slug collision).
- :class:`NonPilotTerminationError` — 500 (broken invariant).
- :class:`PilotReadinessNotConfirmedError` — 409 (advance-step
  precondition).
- :class:`InvalidProspectTransitionError` — 409 (state machine).
- :class:`ConvertedRequiresDealershipError` — 409
  (conversion requires target Dealership FK).
- :class:`UnknownChecklistStepError` — 400 (unknown step slug).
- :class:`ChecklistStepAlreadyCompletedError` — 409 (immutability).

Domain-error → HTTP mapping consumed by the M19.3 endpoints.
"""

from __future__ import annotations

from .checklist import (
    ChecklistStepAlreadyCompletedError,
    UnknownChecklistStepError,
    advance_step,
    is_pilot_ready,
)
from .errors import (
    NonPilotTerminationError,
    PilotAlreadyExistsError,
    PilotReadinessNotConfirmedError,
)
from .inventory_import import (
    PilotInventoryImportResult,
    import_pilot_inventory,
)
from .prospects import (
    ConvertedRequiresDealershipError,
    InvalidProspectTransitionError,
    advance_prospect_state,
    create_prospect,
    list_prospects,
)
from .registry import (
    create_pilot_dealership,
    list_pilot_dealerships,
    terminate_pilot,
)

__all__ = [
    "ChecklistStepAlreadyCompletedError",
    "ConvertedRequiresDealershipError",
    "InvalidProspectTransitionError",
    "NonPilotTerminationError",
    "PilotAlreadyExistsError",
    "PilotInventoryImportResult",
    "PilotReadinessNotConfirmedError",
    "UnknownChecklistStepError",
    "advance_prospect_state",
    "advance_step",
    "create_pilot_dealership",
    "create_prospect",
    "import_pilot_inventory",
    "is_pilot_ready",
    "list_pilot_dealerships",
    "list_prospects",
    "terminate_pilot",
]
