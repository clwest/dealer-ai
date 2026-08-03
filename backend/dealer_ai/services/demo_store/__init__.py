"""Milestone 18 · Increment 1 (SESSION_147) — demo-store package.

Per MILESTONE_18_PLANNING.md §5.a Option O + §5.b-§5.g (all user-
confirmed at SESSION_146 open). Validation-infrastructure package
enabling founder-led pilot testing with experienced independent-
dealer operators.

Public API:

- :func:`create_demo_store` — atomic create + archetype build.
- :func:`reset_demo_store` — atomic delete-then-rebuild
  (belt-and-suspenders guarded).
- :func:`list_demo_stores` — pure read of ``is_demo=True`` rows.
- :class:`NonDemoResetError` — broken-invariant guard.
- :class:`SuppressedOutbound` +
  :func:`suppress_if_demo` +
  :func:`is_demo_dealership` — outbound-send-boundary guard
  toolkit for future adapters (§5.g Option A).
- :class:`ScenarioSummary` — return type of archetype builders.
- :data:`SYNTHETIC_NAMES` + :func:`get_synthetic_name` — pseudonym
  roster (§5.g Option A).
- :func:`synthetic_vin` + :func:`synthetic_phone` +
  :func:`synthetic_email` — synthetic-data helpers (§5.g).

Domain-error → HTTP mapping (consumed by M18.5 endpoints):

- :class:`NonDemoResetError` — 500 (RuntimeError; never surface
  to user; signals bug that a demo-store write path was called
  against a non-demo dealership).
"""

from __future__ import annotations

from .archetypes import (
    ARCHETYPE_BUILDERS,
    ArchetypeBuilder,
    get_archetype_builder,
)
from .briefs import (
    BRIEF_ROLES,
    Brief,
    BriefNotFoundError,
    get_brief,
    list_briefs,
)
from .errors import NonDemoResetError
from .outbound_guard import (
    SuppressedOutbound,
    is_demo_dealership,
    is_outbound_enabled,
    is_pilot_dealership,
    suppress_if_demo,
    suppress_if_outbound_disabled,
)
from .registry import (
    create_demo_store,
    list_demo_stores,
    reset_demo_store,
)
from .scenario_summary import ScenarioSummary
from .synthetic_data import (
    synthetic_email,
    synthetic_phone,
    synthetic_vin,
)
from .synthetic_names import SYNTHETIC_NAMES, get_synthetic_name


__all__ = [
    "ARCHETYPE_BUILDERS",
    "ArchetypeBuilder",
    "BRIEF_ROLES",
    "Brief",
    "BriefNotFoundError",
    "NonDemoResetError",
    "SYNTHETIC_NAMES",
    "ScenarioSummary",
    "SuppressedOutbound",
    "create_demo_store",
    "get_archetype_builder",
    "get_brief",
    "get_synthetic_name",
    "is_demo_dealership",
    "is_outbound_enabled",
    "is_pilot_dealership",
    "list_briefs",
    "list_demo_stores",
    "reset_demo_store",
    "suppress_if_demo",
    "suppress_if_outbound_disabled",
    "synthetic_email",
    "synthetic_phone",
    "synthetic_vin",
]
