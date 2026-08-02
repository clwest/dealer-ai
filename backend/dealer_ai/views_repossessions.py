"""Milestone 12 · Increment 6 (SESSION_126) — Repossession endpoints.

Four endpoints per ``MILESTONE_12_PLANNING.md`` §7 M12.6:

- ``POST /admin/bhph-notes/<pk>/repossessions/`` — record.
- ``GET  /admin/bhph-notes/<pk>/repossessions/list/`` — list per-note.
- ``POST /admin/bhph-repossessions/<pk>/mark-recovered/`` — transition.
- ``POST /admin/bhph-repossessions/<pk>/mark-re-intaked/`` — transition
  (accepts ``condition_report_id``).

Gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``.

Domain-error → HTTP mapping:

- :class:`CrossTenantRepossessionError` → 404 (fail-closed).
- :class:`CrossTenantConditionReportError` → 400.
- :class:`RepossessionAlreadyTerminalError` → 409 (state machine).
- :class:`InvalidStateTransitionError` → 409 (state machine).
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    BhphNote,
    ConditionReport,
    Repossession,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.repossessions import (
    CrossTenantConditionReportError,
    CrossTenantRepossessionError,
    InvalidStateTransitionError,
    RepossessionAlreadyTerminalError,
    list_repossessions,
    mark_re_intaked,
    mark_recovered,
    record_repossession,
)
from .services.tenancy import get_current_dealership


_M126_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_note_or_404(dealership, note_pk):
    try:
        return BhphNote.objects.filter(dealership=dealership).get(pk=note_pk)
    except BhphNote.DoesNotExist:
        return None


def _lookup_repossession_or_404(dealership, pk):
    try:
        return Repossession.objects.filter(dealership=dealership).get(pk=pk)
    except Repossession.DoesNotExist:
        return None


def _lookup_condition_report_or_404(dealership, pk):
    try:
        return ConditionReport.objects.filter(dealership=dealership).get(pk=pk)
    except ConditionReport.DoesNotExist:
        return None


class RepossessionCreateRequestSerializer(serializers.Serializer):
    ordered_at = serializers.DateTimeField()
    agent_name = serializers.CharField(max_length=255)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class RecoveredRequestSerializer(serializers.Serializer):
    recovered_at = serializers.DateTimeField(
        required=False, allow_null=True
    )
    recovery_location = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class ReIntakedRequestSerializer(serializers.Serializer):
    condition_report_id = serializers.IntegerField()
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_repossession(repo: Repossession) -> dict:
    return {
        "id": repo.pk,
        "note_id": repo.note_id,
        "dealership_id": repo.dealership_id,
        "ordered_at": repo.ordered_at.isoformat(),
        "ordered_by_user_id": repo.ordered_by_user_id,
        "agent_name": repo.agent_name,
        "recovered_at": (
            repo.recovered_at.isoformat() if repo.recovered_at else None
        ),
        "recovery_location": repo.recovery_location,
        "intake_condition_report_id": repo.intake_condition_report_id,
        "state": repo.state,
        "notes": repo.notes,
        "created_at": repo.created_at.isoformat(),
        "updated_at": repo.updated_at.isoformat(),
    }


@api_view(["POST"])
@permission_classes(_M126_PERMS)
def admin_repossession_create(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = RepossessionCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        repo = record_repossession(
            dealership=dealership,
            note=note,
            ordered_at=data["ordered_at"],
            agent_name=data["agent_name"],
            ordered_by_user=(
                request.user if request.user.is_authenticated else None
            ),
            notes=data.get("notes", ""),
        )
    except CrossTenantRepossessionError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {"repossession": _project_repossession(repo)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M126_PERMS)
def admin_repossession_list(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    repos = list_repossessions(dealership=dealership, note=note)
    return Response(
        {
            "count": len(repos),
            "results": [_project_repossession(r) for r in repos],
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(_M126_PERMS)
def admin_repossession_mark_recovered(request, pk: int):
    dealership = get_current_dealership(request)
    repo = _lookup_repossession_or_404(dealership, pk)
    if repo is None:
        return Response(
            {"detail": "Repossession not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = RecoveredRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        mark_recovered(
            dealership=dealership,
            repossession=repo,
            recovered_at=serializer.validated_data.get("recovered_at"),
            recovery_location=serializer.validated_data.get(
                "recovery_location", ""
            ),
            notes=serializer.validated_data.get("notes", ""),
        )
    except RepossessionAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except InvalidStateTransitionError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    repo.refresh_from_db()
    return Response(
        {"repossession": _project_repossession(repo)},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(_M126_PERMS)
def admin_repossession_mark_re_intaked(request, pk: int):
    dealership = get_current_dealership(request)
    repo = _lookup_repossession_or_404(dealership, pk)
    if repo is None:
        return Response(
            {"detail": "Repossession not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = ReIntakedRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    condition_report = _lookup_condition_report_or_404(
        dealership, serializer.validated_data["condition_report_id"]
    )
    if condition_report is None:
        return Response(
            {"detail": "ConditionReport not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    try:
        mark_re_intaked(
            dealership=dealership,
            repossession=repo,
            condition_report=condition_report,
            notes=serializer.validated_data.get("notes", ""),
        )
    except CrossTenantConditionReportError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except RepossessionAlreadyTerminalError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except InvalidStateTransitionError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    repo.refresh_from_db()
    return Response(
        {"repossession": _project_repossession(repo)},
        status=status.HTTP_200_OK,
    )
