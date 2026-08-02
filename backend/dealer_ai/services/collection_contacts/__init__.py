"""Milestone 12 · Increment 5 (SESSION_125) — CollectionContact service package.

Single verb per ``MILESTONE_12_PLANNING.md`` §7 M12.5:

- :func:`record_contact` — persist a
  :class:`CollectionContact` audit row. Refuses cross-tenant notes
  (:class:`CrossTenantContactError`) and unknown channel / outcome
  values.

The paired FDCPA scrub layer lives in
:func:`services.llm_safety.apply_post_llm_scrubs` under
``kind="collection_contact"`` per §5.e Option A. This service module
handles the entity write only.

Domain errors:

- :class:`CrossTenantContactError` — 404 at endpoint layer.
- :class:`UnknownChannelError` — 400.
- :class:`UnknownOutcomeError` — 400.
"""

from __future__ import annotations

from .collection_contact import (
    CrossTenantContactError,
    UnknownChannelError,
    UnknownOutcomeError,
    list_contacts,
    record_contact,
)

__all__ = [
    "CrossTenantContactError",
    "UnknownChannelError",
    "UnknownOutcomeError",
    "list_contacts",
    "record_contact",
]
