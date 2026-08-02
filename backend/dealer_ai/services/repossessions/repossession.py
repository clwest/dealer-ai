"""Milestone 12 · Increment 6 (SESSION_126) — Repossession verbs.

Three verbs per §7 M12.6. Three-state machine (ordered → recovered
→ re_intaked). Terminal ``re_intaked`` is final.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from ...models import (
    BHPH_REPO_STATE_ORDERED,
    BHPH_REPO_STATE_RE_INTAKED,
    BHPH_REPO_STATE_RECOVERED,
    BhphNote,
    ConditionReport,
    Dealership,
    Repossession,
)


User = get_user_model()


class CrossTenantRepossessionError(Exception):
    """Raised when a repossession write names a note / repo in another tenant."""


class CrossTenantConditionReportError(Exception):
    """Raised when the ConditionReport attached at mark_re_intaked
    does not belong to the same tenant."""


class RepossessionAlreadyTerminalError(Exception):
    """State-machine violation: repossession already ``re_intaked``.

    Terminal state is final at M12.6. Matches M11.5 / M12.4 posture.
    """


class InvalidStateTransitionError(Exception):
    """State-machine violation: attempted transition is not the next
    legal step (e.g. ordered → re_intaked without recovering first).
    """


def record_repossession(
    *,
    dealership: Dealership,
    note: BhphNote,
    ordered_at: dt.datetime,
    agent_name: str,
    ordered_by_user: Optional["User"] = None,
    notes: str = "",
) -> Repossession:
    """Issue a repossession order against ``note``.

    Refuses cross-tenant notes
    (:class:`CrossTenantRepossessionError`). Blank ``agent_name`` is
    accepted (operators sometimes issue orders before assigning the
    agent — the CharField default keeps this consistent with M9/M10
    free-text fields).
    """
    if note.dealership_id != dealership.id:
        raise CrossTenantRepossessionError(
            f"BhphNote {note.pk} belongs to another tenant."
        )
    return Repossession.objects.create(
        dealership=dealership,
        note=note,
        ordered_at=ordered_at,
        ordered_by_user=ordered_by_user,
        agent_name=agent_name,
        state=BHPH_REPO_STATE_ORDERED,
        notes=notes or "",
    )


def _assert_same_tenant(
    repo: Repossession, dealership: Dealership
) -> None:
    if repo.dealership_id != dealership.id:
        raise CrossTenantRepossessionError(
            f"Repossession {repo.pk} belongs to another tenant."
        )


def mark_recovered(
    *,
    dealership: Dealership,
    repossession: Repossession,
    recovered_at: Optional[dt.datetime] = None,
    recovery_location: str = "",
    notes: str = "",
) -> Repossession:
    """ordered → recovered.

    Populates ``recovered_at`` (defaults to now) and
    ``recovery_location``. Refuses:

    - Cross-tenant repossession
      (:class:`CrossTenantRepossessionError`).
    - Terminal ``re_intaked``
      (:class:`RepossessionAlreadyTerminalError`).
    - Non-``ordered`` starting state
      (:class:`InvalidStateTransitionError`).
    """
    _assert_same_tenant(repossession, dealership)
    if repossession.state == BHPH_REPO_STATE_RE_INTAKED:
        raise RepossessionAlreadyTerminalError(
            f"Repossession {repossession.pk} is already in terminal "
            f"state {repossession.state!r}. Re-transition refused."
        )
    if repossession.state != BHPH_REPO_STATE_ORDERED:
        raise InvalidStateTransitionError(
            f"Cannot mark recovered from state "
            f"{repossession.state!r}; must be 'ordered'."
        )
    repossession.state = BHPH_REPO_STATE_RECOVERED
    repossession.recovered_at = (
        recovered_at if recovered_at is not None else timezone.now()
    )
    if recovery_location:
        repossession.recovery_location = recovery_location
    if notes:
        repossession.notes = notes
    repossession.save(
        update_fields=[
            "state",
            "recovered_at",
            "recovery_location",
            "notes",
            "updated_at",
        ]
    )
    return repossession


def mark_re_intaked(
    *,
    dealership: Dealership,
    repossession: Repossession,
    condition_report: ConditionReport,
    notes: str = "",
) -> Repossession:
    """recovered → re_intaked.

    Ties the recovered vehicle back into the M3/M4/M5 recon
    substrate via ``intake_condition_report``. Refuses:

    - Cross-tenant repossession
      (:class:`CrossTenantRepossessionError`).
    - Cross-tenant condition report
      (:class:`CrossTenantConditionReportError`).
    - Terminal ``re_intaked``
      (:class:`RepossessionAlreadyTerminalError`).
    - Non-``recovered`` starting state
      (:class:`InvalidStateTransitionError`).
    """
    _assert_same_tenant(repossession, dealership)
    if condition_report.dealership_id != dealership.id:
        raise CrossTenantConditionReportError(
            f"ConditionReport {condition_report.pk} belongs to "
            "another tenant."
        )
    if repossession.state == BHPH_REPO_STATE_RE_INTAKED:
        raise RepossessionAlreadyTerminalError(
            f"Repossession {repossession.pk} is already in terminal "
            f"state {repossession.state!r}. Re-transition refused."
        )
    if repossession.state != BHPH_REPO_STATE_RECOVERED:
        raise InvalidStateTransitionError(
            f"Cannot mark re-intaked from state "
            f"{repossession.state!r}; must be 'recovered'."
        )
    repossession.state = BHPH_REPO_STATE_RE_INTAKED
    repossession.intake_condition_report = condition_report
    if notes:
        repossession.notes = notes
    repossession.save(
        update_fields=[
            "state",
            "intake_condition_report",
            "notes",
            "updated_at",
        ]
    )
    return repossession


def list_repossessions(
    *, dealership: Dealership, note: BhphNote
) -> list[Repossession]:
    """Tenant-scoped list of repossessions for ``note``.

    Cross-tenant note returns an empty list (fail-closed).
    """
    if note.dealership_id != dealership.id:
        return []
    return list(Repossession.objects.filter(note=note))
