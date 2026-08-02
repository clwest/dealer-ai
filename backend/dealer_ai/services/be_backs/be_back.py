"""Milestone 11 · Increment 5 (SESSION_118) — BeBack write verbs.

Three verbs per §5.g Options A / A / B.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from django.utils import timezone

from ...models import (
    BE_BACK_REASON_CHOICES,
    BE_BACK_STATE_NO_SHOW,
    BE_BACK_STATE_PROMISED,
    BE_BACK_STATE_RETURNED,
    BeBack,
    CustomerLead,
    Dealership,
)


_VALID_REASONS = {key for key, _ in BE_BACK_REASON_CHOICES}


class CrossTenantBeBackError(Exception):
    """Raised when a be-back write names a lead or be-back in another tenant."""


class UnknownReasonError(Exception):
    """Raised when ``promised_reason`` is not in the 4+1 vocab."""


class BeBackAlreadyTerminalError(Exception):
    """State-machine violation: be-back already ``returned`` / ``no_show``.

    Terminal states are final at M11.5. Silent re-transition would
    erase operator intent (who marked it done, when, returned vs
    no-show). If the operator needs to undo, a future ``reopen``
    verb can add the un-do path when the operator UI surfaces the
    need (deferred, matches M11.4 posture).
    """


def record_be_back(
    *,
    dealership: Dealership,
    lead: CustomerLead,
    promised_at: dt.datetime,
    promised_reason: str,
    notes: str = "",
) -> BeBack:
    """Persist a :class:`BeBack`.

    Refuses cross-tenant leads
    (:class:`CrossTenantBeBackError`) and unknown reasons
    (:class:`UnknownReasonError`).
    """
    if lead.dealership_id != dealership.id:
        raise CrossTenantBeBackError(
            f"CustomerLead {lead.pk} belongs to another tenant."
        )
    if promised_reason not in _VALID_REASONS:
        raise UnknownReasonError(
            f"Unknown promised_reason={promised_reason!r}. "
            f"Valid reasons: {sorted(_VALID_REASONS)!r}."
        )
    return BeBack.objects.create(
        dealership=dealership,
        lead=lead,
        promised_at=promised_at,
        promised_reason=promised_reason,
        state=BE_BACK_STATE_PROMISED,
        notes=notes or "",
    )


def _assert_same_tenant(be_back: BeBack, dealership: Dealership) -> None:
    if be_back.dealership_id != dealership.id:
        raise CrossTenantBeBackError(
            f"BeBack {be_back.pk} belongs to another tenant."
        )


def mark_returned(
    *,
    dealership: Dealership,
    be_back: BeBack,
    actual_return_at: Optional[dt.datetime] = None,
    notes: str = "",
) -> BeBack:
    """promised → returned. Defaults ``actual_return_at`` to now."""
    _assert_same_tenant(be_back, dealership)
    if be_back.state != BE_BACK_STATE_PROMISED:
        raise BeBackAlreadyTerminalError(
            f"BeBack {be_back.pk} is already in terminal state "
            f"{be_back.state!r}. Re-transition refused."
        )
    be_back.state = BE_BACK_STATE_RETURNED
    be_back.actual_return_at = (
        actual_return_at if actual_return_at is not None else timezone.now()
    )
    if notes:
        be_back.notes = notes
    be_back.save(
        update_fields=["state", "actual_return_at", "notes", "updated_at"]
    )
    return be_back


def mark_no_show(
    *,
    dealership: Dealership,
    be_back: BeBack,
    notes: str = "",
) -> BeBack:
    """promised → no_show. Called by the M11.5 Celery detector +
    exposed manually.

    Never populates ``actual_return_at`` — a no-show has no return
    timestamp by definition.
    """
    _assert_same_tenant(be_back, dealership)
    if be_back.state != BE_BACK_STATE_PROMISED:
        raise BeBackAlreadyTerminalError(
            f"BeBack {be_back.pk} is already in terminal state "
            f"{be_back.state!r}. Re-transition refused."
        )
    be_back.state = BE_BACK_STATE_NO_SHOW
    if notes:
        be_back.notes = notes
    be_back.save(update_fields=["state", "notes", "updated_at"])
    return be_back
