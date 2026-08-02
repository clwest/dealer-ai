"""Milestone 11 · Increment 4 (SESSION_117) — Follow-up cadence write verbs.

Four verbs backing the M11.4 entities per ``MILESTONE_11_PLANNING.md``
§1.4 + §5.d Option A.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from ...models import (
    FOLLOW_UP_TASK_STATE_COMPLETED,
    FOLLOW_UP_TASK_STATE_PENDING,
    FOLLOW_UP_TASK_STATE_SKIPPED,
    FOLLOW_UP_TEMPLATE_OFFSETS,
    CustomerLead,
    Dealership,
    FollowUpCadence,
    FollowUpTask,
)


class CrossTenantCadenceError(Exception):
    """Cross-tenant lead reference on cadence write."""


class CrossTenantTaskError(Exception):
    """Cross-tenant task reference on task-transition write."""


class DuplicateActiveCadenceError(Exception):
    """A second active cadence for the same (lead, template) pair.

    Pause the existing cadence before starting a new one, or accept
    that historical (paused / completed) cadences don't block a
    fresh start.
    """


class UnknownTemplateError(Exception):
    """Template not in :data:`FOLLOW_UP_TEMPLATE_OFFSETS`."""


class TaskAlreadyTerminalError(Exception):
    """State-machine violation: task already completed / skipped.

    Terminal states are final at M11.4. Re-transition would silently
    overwrite operator intent (who marked it done vs skipped, and
    when). If the operator needs to undo, the correct verb is a
    separate ``reopen_task`` (deferred to a follow-on increment when
    the operator UI surfaces the need).
    """


@transaction.atomic
def start_cadence(
    *,
    dealership: Dealership,
    lead: CustomerLead,
    template: str,
    started_at: Optional[dt.datetime] = None,
) -> FollowUpCadence:
    """Create a :class:`FollowUpCadence` + seed its
    :class:`FollowUpTask` rows.

    Refuses cross-tenant leads
    (:class:`CrossTenantCadenceError`).
    Refuses unknown templates
    (:class:`UnknownTemplateError`).
    Refuses a duplicate active (lead, template) pair
    (:class:`DuplicateActiveCadenceError`).

    Wrapped in ``@transaction.atomic`` so a mid-seed failure never
    leaves a header without matching task rows.
    """
    if lead.dealership_id != dealership.id:
        raise CrossTenantCadenceError(
            f"CustomerLead {lead.pk} belongs to another tenant."
        )
    if template not in FOLLOW_UP_TEMPLATE_OFFSETS:
        raise UnknownTemplateError(
            f"Unknown template {template!r}. Valid templates: "
            f"{sorted(FOLLOW_UP_TEMPLATE_OFFSETS.keys())!r}."
        )
    if FollowUpCadence.objects.filter(
        dealership=dealership,
        lead=lead,
        template=template,
        is_active=True,
    ).exists():
        raise DuplicateActiveCadenceError(
            f"An active {template!r} cadence already exists for "
            f"lead {lead.pk}. Pause the existing cadence first."
        )

    start = started_at if started_at is not None else timezone.now()
    cadence = FollowUpCadence.objects.create(
        dealership=dealership,
        lead=lead,
        template=template,
        started_at=start,
        is_active=True,
    )
    offsets = FOLLOW_UP_TEMPLATE_OFFSETS[template]
    for days_offset in offsets:
        FollowUpTask.objects.create(
            dealership=dealership,
            cadence=cadence,
            due_at=start + dt.timedelta(days=days_offset),
            state=FOLLOW_UP_TASK_STATE_PENDING,
        )
    return cadence


def _transition_task(
    *,
    task: FollowUpTask,
    dealership: Dealership,
    new_state: str,
    completed_by_user: Optional[Any],
    completed_at: Optional[dt.datetime],
    notes: str,
) -> FollowUpTask:
    if task.dealership_id != dealership.id:
        raise CrossTenantTaskError(
            f"FollowUpTask {task.pk} belongs to another tenant."
        )
    if task.state != FOLLOW_UP_TASK_STATE_PENDING:
        raise TaskAlreadyTerminalError(
            f"FollowUpTask {task.pk} is already in terminal state "
            f"{task.state!r}. Re-transition refused."
        )
    task.state = new_state
    task.completed_by_user = completed_by_user
    task.completed_at = (
        completed_at if completed_at is not None else timezone.now()
    )
    if notes:
        task.notes = notes
    task.save(
        update_fields=[
            "state",
            "completed_by_user",
            "completed_at",
            "notes",
            "updated_at",
        ]
    )
    return task


def complete_task(
    *,
    dealership: Dealership,
    task: FollowUpTask,
    completed_by_user: Optional[Any] = None,
    completed_at: Optional[dt.datetime] = None,
    notes: str = "",
) -> FollowUpTask:
    """pending → completed."""
    return _transition_task(
        task=task,
        dealership=dealership,
        new_state=FOLLOW_UP_TASK_STATE_COMPLETED,
        completed_by_user=completed_by_user,
        completed_at=completed_at,
        notes=notes,
    )


def skip_task(
    *,
    dealership: Dealership,
    task: FollowUpTask,
    completed_by_user: Optional[Any] = None,
    completed_at: Optional[dt.datetime] = None,
    notes: str = "",
) -> FollowUpTask:
    """pending → skipped. Notes strongly recommended (why skipped)."""
    return _transition_task(
        task=task,
        dealership=dealership,
        new_state=FOLLOW_UP_TASK_STATE_SKIPPED,
        completed_by_user=completed_by_user,
        completed_at=completed_at,
        notes=notes,
    )


def pause_cadence(
    *,
    dealership: Dealership,
    cadence: FollowUpCadence,
) -> FollowUpCadence:
    """Halt future beat surfacing. Pending task rows stay intact.

    Cross-tenant guard: raises :class:`CrossTenantCadenceError` if
    the cadence belongs to another tenant.

    Idempotent — pausing an already-paused cadence is a no-op that
    still returns the cadence (matches operator expectations).
    """
    if cadence.dealership_id != dealership.id:
        raise CrossTenantCadenceError(
            f"FollowUpCadence {cadence.pk} belongs to another tenant."
        )
    if cadence.is_active:
        cadence.is_active = False
        cadence.save(update_fields=["is_active", "updated_at"])
    return cadence
