"""Milestone 19 · Increment 1 (SESSION_154) — pilot prospect verbs.

Per MILESTONE_19_PLANNING.md §5.b Option C (user-confirmed at
SESSION_153 open) + §0.a M19.1 decision 1 (user-confirmed at
SESSION_154 open — PilotProspect is a pre-tenant operator record;
not a tenancy carrier).

Three verbs:

- :func:`create_prospect` — atomic create.
- :func:`advance_prospect_state` — state machine transition.
- :func:`list_prospects` — pure read.

**State machine** (§5.b Option C): ``prospect`` → ``qualified`` →
``converted`` OR → ``declined``. Terminal states are ``converted``
+ ``declined``. Re-transition would erase operator intent; if a
declined prospect should be revisited, a new PilotProspect row is
created.
"""

from __future__ import annotations

from typing import Optional

from django.db import transaction

from ...models import (
    PILOT_PROSPECT_STATE_CHOICES,
    PILOT_PROSPECT_STATE_CONVERTED,
    PILOT_PROSPECT_STATE_DECLINED,
    PILOT_PROSPECT_STATE_PROSPECT,
    PILOT_PROSPECT_STATE_QUALIFIED,
    Dealership,
    PilotProspect,
)


class InvalidProspectTransitionError(ValueError):
    """Raised on an illegal state-machine transition.

    Terminal states (``converted``, ``declined``) cannot be re-
    transitioned; ``prospect`` → ``converted`` skipping ``qualified``
    is also refused. Mapped to HTTP 409 at the endpoint layer.
    """


class ConvertedRequiresDealershipError(ValueError):
    """Raised when advancing to ``converted`` without a target Dealership.

    Per :class:`models.PilotProspect.clean` invariant: the
    ``converted_dealership`` FK is populated iff
    ``eligibility_state='converted'``. This error catches attempts
    to advance state without supplying the FK.
    """


_VALID_STATES = {key for key, _ in PILOT_PROSPECT_STATE_CHOICES}

# Legal transitions per §5.b Option C.
_LEGAL_TRANSITIONS: dict[str, set[str]] = {
    PILOT_PROSPECT_STATE_PROSPECT: {
        PILOT_PROSPECT_STATE_QUALIFIED,
        PILOT_PROSPECT_STATE_DECLINED,
    },
    PILOT_PROSPECT_STATE_QUALIFIED: {
        PILOT_PROSPECT_STATE_CONVERTED,
        PILOT_PROSPECT_STATE_DECLINED,
    },
    # Terminal states — no outgoing transitions.
    PILOT_PROSPECT_STATE_CONVERTED: set(),
    PILOT_PROSPECT_STATE_DECLINED: set(),
}


def create_prospect(
    *,
    contact_name: str,
    contact_email: str,
    dealer_business_name: str,
    contact_phone: str = "",
    dealer_type: str = "",
    bhph_enabled: bool = False,
    estimated_inventory_size: Optional[int] = None,
    contact_source: str = "",
    chris_notes: str = "",
    source_demo_dealership: Optional[Dealership] = None,
) -> PilotProspect:
    """Persist a fresh :class:`PilotProspect` in the initial ``prospect`` state.

    Optional ``source_demo_dealership`` points at the demo
    Dealership the prospect tested on — preserved through conversion
    so Chris can track which archetypes converted best (per §5.b
    Option C).
    """
    return PilotProspect.objects.create(
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        dealer_business_name=dealer_business_name,
        dealer_type=dealer_type,
        bhph_enabled=bhph_enabled,
        estimated_inventory_size=estimated_inventory_size,
        contact_source=contact_source,
        chris_notes=chris_notes,
        source_demo_dealership=source_demo_dealership,
        eligibility_state=PILOT_PROSPECT_STATE_PROSPECT,
    )


@transaction.atomic
def advance_prospect_state(
    *,
    prospect: PilotProspect,
    new_state: str,
    converted_dealership: Optional[Dealership] = None,
    notes_append: str = "",
) -> PilotProspect:
    """Advance ``prospect.eligibility_state`` per the M19 state machine.

    Legal transitions per §5.b Option C:

    - ``prospect`` → ``qualified`` OR ``declined``
    - ``qualified`` → ``converted`` OR ``declined``
    - Terminal (``converted``, ``declined``) has no outgoing edges.

    Advancing to ``converted`` requires ``converted_dealership`` to be
    supplied — the :class:`models.PilotProspect.clean` invariant
    enforces this at the model layer too.

    Refuses:

    - Unknown ``new_state`` — :class:`ValueError` (400).
    - Illegal transition — :class:`InvalidProspectTransitionError`
      (409).
    - ``converted`` without ``converted_dealership`` —
      :class:`ConvertedRequiresDealershipError` (409).

    ``notes_append`` is appended to ``chris_notes`` (with a blank
    line separator) so the audit trail preserves the operator's
    running commentary.
    """
    if new_state not in _VALID_STATES:
        raise ValueError(
            f"Unknown state {new_state!r}. Valid: {sorted(_VALID_STATES)!r}."
        )
    current = prospect.eligibility_state
    if new_state not in _LEGAL_TRANSITIONS.get(current, set()):
        raise InvalidProspectTransitionError(
            f"Illegal state transition {current!r} → {new_state!r}. "
            f"Legal transitions from {current!r}: "
            f"{sorted(_LEGAL_TRANSITIONS.get(current, set())) or 'none (terminal)'}."
        )
    if new_state == PILOT_PROSPECT_STATE_CONVERTED and (
        converted_dealership is None
    ):
        raise ConvertedRequiresDealershipError(
            "Advancing to 'converted' requires converted_dealership. "
            "Populate the FK with the newly-created pilot Dealership."
        )

    prospect.eligibility_state = new_state
    if new_state == PILOT_PROSPECT_STATE_CONVERTED:
        prospect.converted_dealership = converted_dealership
    if notes_append:
        prospect.chris_notes = (
            (prospect.chris_notes + "\n\n" + notes_append).strip()
            if prospect.chris_notes
            else notes_append
        )
    prospect.save()
    return prospect


def list_prospects() -> list[PilotProspect]:
    """Return every :class:`PilotProspect`, recent-first.

    Pure. Read-only. No tenant scope — the model has none per §0.a
    M19.1 decision 1. Endpoint-layer permission checks (operator
    role at the migration-seeded default dealership) prevent
    cross-operator access.
    """
    return list(PilotProspect.objects.order_by("-created_at", "-id"))
