"""Milestone 12 · Increment 5 (SESSION_125) — CollectionContact verbs."""

from __future__ import annotations

import datetime as dt
from typing import Optional

from django.contrib.auth import get_user_model

from ...models import (
    BHPH_CONTACT_CHANNEL_CHOICES,
    BHPH_CONTACT_OUTCOME_CHOICES,
    BhphNote,
    CollectionContact,
    Dealership,
)


_VALID_CHANNELS = {key for key, _ in BHPH_CONTACT_CHANNEL_CHOICES}
_VALID_OUTCOMES = {key for key, _ in BHPH_CONTACT_OUTCOME_CHOICES}

User = get_user_model()


class CrossTenantContactError(Exception):
    """Raised when a contact write names a note in another tenant."""


class UnknownChannelError(Exception):
    """Raised when ``channel`` is not in the 5-value vocab."""


class UnknownOutcomeError(Exception):
    """Raised when ``outcome`` is not in the 4-value vocab."""


def record_contact(
    *,
    dealership: Dealership,
    note: BhphNote,
    contacted_at: dt.datetime,
    channel: str,
    outcome: str,
    contacted_by_user: Optional["User"] = None,
    notes: str = "",
) -> CollectionContact:
    """Persist a :class:`CollectionContact` audit row.

    Refuses:

    - Cross-tenant note (:class:`CrossTenantContactError`).
    - Unknown channel (:class:`UnknownChannelError`).
    - Unknown outcome (:class:`UnknownOutcomeError`).
    """
    if note.dealership_id != dealership.id:
        raise CrossTenantContactError(
            f"BhphNote {note.pk} belongs to another tenant."
        )
    if channel not in _VALID_CHANNELS:
        raise UnknownChannelError(
            f"Unknown channel={channel!r}. "
            f"Valid: {sorted(_VALID_CHANNELS)!r}."
        )
    if outcome not in _VALID_OUTCOMES:
        raise UnknownOutcomeError(
            f"Unknown outcome={outcome!r}. "
            f"Valid: {sorted(_VALID_OUTCOMES)!r}."
        )
    return CollectionContact.objects.create(
        dealership=dealership,
        note=note,
        contacted_at=contacted_at,
        contacted_by_user=contacted_by_user,
        channel=channel,
        outcome=outcome,
        notes=notes or "",
    )


def list_contacts(
    *, dealership: Dealership, note: BhphNote
) -> list[CollectionContact]:
    """Tenant-scoped list of contacts for ``note``.

    Cross-tenant note returns an empty list (fail-closed).
    """
    if note.dealership_id != dealership.id:
        return []
    return list(CollectionContact.objects.filter(note=note))
