"""Milestone 11 · Increment 4 (SESSION_117) — Follow-up cadence endpoints.

Five endpoints per ``MILESTONE_11_PLANNING.md`` §7 M11.4 + §1.9:

- ``POST /admin/follow-up-cadences/`` — start a cadence.
- ``POST /admin/follow-up-cadences/<pk>/pause/`` — pause.
- ``POST /admin/follow-up-tasks/<pk>/complete/`` — complete a task.
- ``POST /admin/follow-up-tasks/<pk>/skip/`` — skip a task.
- ``GET  /admin/follow-up-tasks/`` — operator work-queue with
  ``?due_before=`` + ``?state=`` filters.

All five gated on ``IsAuthenticated &
IsSalesManagerOrOwnerAtActiveDealership`` (M4 permission class,
matches M11.1/M11.2/M11.3 posture per §1.9).

Domain-error → HTTP mapping:

- :class:`CrossTenantCadenceError` → 404 (fail-closed).
- :class:`CrossTenantTaskError` → 404 (fail-closed).
- :class:`DuplicateActiveCadenceError` → 409.
- :class:`UnknownTemplateError` → 400.
- :class:`TaskAlreadyTerminalError` → 409.
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    FOLLOW_UP_TASK_STATE_CHOICES,
    FOLLOW_UP_TEMPLATE_CHOICES,
    CustomerLead,
    FollowUpCadence,
    FollowUpTask,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.follow_ups import (
    CrossTenantCadenceError,
    CrossTenantTaskError,
    DuplicateActiveCadenceError,
    TaskAlreadyTerminalError,
    UnknownTemplateError,
    complete_task,
    pause_cadence,
    skip_task,
    start_cadence,
)
from .services.tenancy import get_current_dealership


_M114_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_lead_or_404(dealership, lead_id):
    try:
        return CustomerLead.objects.filter(dealership=dealership).get(pk=lead_id)
    except CustomerLead.DoesNotExist:
        return None


def _lookup_cadence_or_404(dealership, pk):
    try:
        return FollowUpCadence.objects.filter(dealership=dealership).get(pk=pk)
    except FollowUpCadence.DoesNotExist:
        return None


def _lookup_task_or_404(dealership, pk):
    try:
        return FollowUpTask.objects.filter(dealership=dealership).get(pk=pk)
    except FollowUpTask.DoesNotExist:
        return None


class CadenceStartRequestSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()
    template = serializers.ChoiceField(
        choices=[key for key, _ in FOLLOW_UP_TEMPLATE_CHOICES]
    )
    started_at = serializers.DateTimeField(required=False, allow_null=True)


class TaskTransitionRequestSerializer(serializers.Serializer):
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_cadence(cadence: FollowUpCadence) -> dict:
    return {
        "id": cadence.pk,
        "lead_id": cadence.lead_id,
        "dealership_id": cadence.dealership_id,
        "template": cadence.template,
        "started_at": cadence.started_at.isoformat(),
        "is_active": cadence.is_active,
        "task_count": cadence.tasks.count(),
        "created_at": cadence.created_at.isoformat(),
        "updated_at": cadence.updated_at.isoformat(),
    }


def _project_task(task: FollowUpTask) -> dict:
    return {
        "id": task.pk,
        "cadence_id": task.cadence_id,
        "dealership_id": task.dealership_id,
        "due_at": task.due_at.isoformat(),
        "state": task.state,
        "completed_by_user_id": task.completed_by_user_id,
        "completed_at": (
            task.completed_at.isoformat() if task.completed_at else None
        ),
        "notes": task.notes,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


# ---- Endpoints -------------------------------------------------------------


@api_view(["POST"])
@permission_classes(_M114_PERMS)
def admin_follow_up_cadence_create(request):
    dealership = get_current_dealership(request)
    serializer = CadenceStartRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    lead = _lookup_lead_or_404(dealership, data["lead_id"])
    if lead is None:
        return Response(
            {"detail": "Lead not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        cadence = start_cadence(
            dealership=dealership,
            lead=lead,
            template=data["template"],
            started_at=data.get("started_at"),
        )
    except CrossTenantCadenceError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except UnknownTemplateError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except DuplicateActiveCadenceError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )

    return Response(
        {"cadence": _project_cadence(cadence)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes(_M114_PERMS)
def admin_follow_up_cadence_pause(request, pk: int):
    dealership = get_current_dealership(request)
    cadence = _lookup_cadence_or_404(dealership, pk)
    if cadence is None:
        return Response(
            {"detail": "Cadence not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    pause_cadence(dealership=dealership, cadence=cadence)
    cadence.refresh_from_db()
    return Response({"cadence": _project_cadence(cadence)}, status=status.HTTP_200_OK)


def _transition_endpoint(request, pk: int, *, verb):
    dealership = get_current_dealership(request)
    task = _lookup_task_or_404(dealership, pk)
    if task is None:
        return Response(
            {"detail": "Task not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = TaskTransitionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    notes = serializer.validated_data.get("notes", "")
    try:
        verb(
            dealership=dealership,
            task=task,
            completed_by_user=request.user if request.user.is_authenticated else None,
            notes=notes,
        )
    except CrossTenantTaskError:
        return Response(
            {"detail": "Task not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except TaskAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    task.refresh_from_db()
    return Response({"task": _project_task(task)}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes(_M114_PERMS)
def admin_follow_up_task_complete(request, pk: int):
    return _transition_endpoint(request, pk, verb=complete_task)


@api_view(["POST"])
@permission_classes(_M114_PERMS)
def admin_follow_up_task_skip(request, pk: int):
    return _transition_endpoint(request, pk, verb=skip_task)


_VALID_STATES = {key for key, _ in FOLLOW_UP_TASK_STATE_CHOICES}


@api_view(["GET"])
@permission_classes(_M114_PERMS)
def admin_follow_up_task_list(request):
    """Operator work-queue.

    Query params (all optional):

    - ``state`` — one of pending / completed / skipped.
    - ``due_before`` — ISO datetime; return tasks with
      ``due_at <= due_before``.
    - ``limit`` — cap results (default 50, max 200).
    """
    dealership = get_current_dealership(request)
    qs = FollowUpTask.objects.filter(dealership=dealership).select_related(
        "cadence"
    )

    state = (request.query_params.get("state") or "").strip()
    if state in _VALID_STATES:
        qs = qs.filter(state=state)

    due_before = request.query_params.get("due_before")
    if due_before:
        parsed = serializers.DateTimeField().to_internal_value(due_before)
        qs = qs.filter(due_at__lte=parsed)

    try:
        limit = int(request.query_params.get("limit") or 50)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))

    tasks = list(qs.order_by("due_at")[:limit])
    return Response(
        {
            "count": len(tasks),
            "results": [_project_task(t) for t in tasks],
        }
    )
