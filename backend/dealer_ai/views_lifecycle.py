"""Milestone 5 · Increment 4 — vehicle-lifecycle admin API.

Three DRF endpoints wrapping the M5.2 + M5.3 lifecycle service
surface for the M5.6 operator UI to consume:

- ``GET  /api/dealer-ai/admin/vehicles/<stock_number>/lifecycle/``
  — dashboard: current stage + recent events + suggested
  transitions + hold_reserved return-target hint.
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/lifecycle/transition/``
  — apply a manual transition.
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/lifecycle/transition/rule/``
  — accept a rule-suggested transition. Re-evaluates
  :func:`services.vehicle_lifecycle.suggest_transitions` at
  apply time and refuses (409) if the specific rule no longer
  fires (the predicate has flipped since the operator saw it).

Permission layering (per ``MILESTONE_5_PLANNING.md`` §5.f
SESSION_075 refined):

- **DRF permission class** admits the endpoint. All three
  endpoints share
  :class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
  (M4.6) — the broad admission set that also matches the
  authorized-roles for the GET surface.
- **Per-transition role authority** is enforced inside
  :func:`services.vehicle_lifecycle.advance_stage`. A
  ``recon_manager`` who successfully authenticates and gets
  admitted to the endpoint still receives HTTP 403 when
  attempting to transition into a commercial/disposition
  target (``hold_reserved`` / ``wholesale_out`` /
  ``company_use`` / ``off_market``) because the service
  raises :class:`UnauthorizedStageTransitionError`.

Domain-error → HTTP mapping (per SESSION_075 §0.a item 5;
distinct classes → distinct status codes):

- :class:`CrossTenantLifecycleError` → 404 (fail-closed).
- :class:`InvalidStageTransitionError` → 409 (structurally
  illegal).
- :class:`UnauthorizedStageTransitionError` → 403 (role
  refusal — distinct from Invalid).
- :class:`StageAlreadyCurrentError` → 409 (no-op).
- :class:`ValueError` → 400.

M5 has no AI role. This module ships no LLM integration and
no safety-stack scrub calls.
"""

from __future__ import annotations

from typing import Optional

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    VEHICLE_STAGE_CHOICES,
    VEHICLE_STAGE_TRIGGER_MANUAL,
    VEHICLE_STAGE_TRIGGER_RULE,
    Vehicle,
    VehicleStage,
    VehicleStageEvent,
)
from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services.tenancy import get_current_dealership
from .services.vehicle_lifecycle import (
    CrossTenantLifecycleError,
    InvalidStageTransitionError,
    StageAlreadyCurrentError,
    SuggestedTransition,
    UnauthorizedStageTransitionError,
    advance_stage,
    get_current_stage,
    resolve_hold_reserved_return_target,
    suggest_transitions,
)


_M54_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]

# How many recent VehicleStageEvent rows to include in the dashboard
# response. Bounded so a long-lived vehicle with many transitions
# doesn't blow up the response payload; the operator UI can add a
# "view full history" affordance in a future milestone if needed.
_RECENT_EVENT_LIMIT = 25


# ============================================================================
# Lookup helpers (tenant-scoped; 404 on cross-tenant + nonexistent)
# ============================================================================


def _lookup_vehicle_or_404(dealership, stock_number) -> Optional[Vehicle]:
    """Return the Vehicle at ``dealership`` with matching
    ``stock_number``, or ``None`` for the caller to translate into
    a 404. Cross-tenant lookups fail closed because the queryset
    is scoped to the caller's dealership."""
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


# ============================================================================
# Response projections
# ============================================================================


def _project_stage(stage: Optional[VehicleStage]) -> Optional[dict]:
    if stage is None:
        return None
    return {
        "value": stage.current_stage,
        "label": stage.get_current_stage_display(),
        "entered_at": stage.entered_at,
        "entered_by": (
            {"id": stage.entered_by_id, "username": stage.entered_by.username}
            if stage.entered_by_id is not None
            else None
        ),
        "trigger": stage.trigger,
        "last_transition_note": stage.last_transition_note,
    }


def _project_event(event: VehicleStageEvent) -> dict:
    return {
        "id": event.pk,
        "from_stage": event.from_stage,
        "to_stage": event.to_stage,
        "entered_at": event.entered_at,
        "by": (
            {"id": event.by_id, "username": event.by.username}
            if event.by_id is not None
            else None
        ),
        "trigger": event.trigger,
        "rule_name": event.rule_name,
        "notes": event.notes,
        "created_at": event.created_at,
    }


def _project_suggestion(suggestion: SuggestedTransition) -> dict:
    return {
        "to_stage": suggestion.to_stage,
        "rule_name": suggestion.rule_name,
        "evidence": suggestion.evidence,
        "unmet_prerequisites": list(suggestion.unmet_prerequisites),
    }


# ============================================================================
# Error mapping
# ============================================================================


def _map_service_error(exc: Exception) -> Response:
    """Translate an M5.2 lifecycle domain error into a DRF response.

    Distinct classes → distinct HTTP status codes per SESSION_075
    §0.a item 5. Never overload."""
    if isinstance(exc, CrossTenantLifecycleError):
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(exc, UnauthorizedStageTransitionError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_403_FORBIDDEN,
        )
    if isinstance(exc, (InvalidStageTransitionError, StageAlreadyCurrentError)):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, ValueError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    raise exc  # unknown — re-raise so it becomes a 500


# ============================================================================
# Request serializers
# ============================================================================


class LifecycleManualTransitionRequestSerializer(serializers.Serializer):
    to_stage = serializers.ChoiceField(choices=VEHICLE_STAGE_CHOICES)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class LifecycleRuleAcceptRequestSerializer(serializers.Serializer):
    rule_name = serializers.CharField(max_length=128)


# ============================================================================
# Endpoints
# ============================================================================


@api_view(["GET"])
@permission_classes(_M54_PERMS)
def admin_lifecycle_dashboard(request, stock_number: str):
    """GET dashboard for one vehicle's lifecycle state.

    Response body:
    - ``stock_number`` — echoed for client convenience.
    - ``has_stage`` — ``True`` when a ``VehicleStage`` row exists.
    - ``current_stage`` — projected stage row, or ``null`` when
      no row exists (a vehicle without a stage is a real state,
      not an error).
    - ``recent_events`` — up to the last
      :data:`_RECENT_EVENT_LIMIT` ``VehicleStageEvent`` rows in
      reverse chronological order.
    - ``suggested_transitions`` — the M5.3
      :func:`suggest_transitions` composition for the current
      stage.
    - ``hold_reserved_return_target`` — the previous
      retail-preparation stage resolved from the event log, or
      ``null`` when the vehicle isn't in ``hold_reserved`` or
      no valid target can be resolved.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        stage = get_current_stage(vehicle, dealership=dealership)
        events = list(
            VehicleStageEvent.objects.filter(
                vehicle=vehicle, dealership=dealership
            )
            .select_related("by")
            .order_by("-entered_at", "-created_at")[:_RECENT_EVENT_LIMIT]
        )
        suggestions = suggest_transitions(vehicle, dealership=dealership)
        return_target = resolve_hold_reserved_return_target(
            vehicle, dealership=dealership
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(
        {
            "stock_number": vehicle.stock_number,
            "has_stage": stage is not None,
            "current_stage": _project_stage(stage),
            "recent_events": [_project_event(e) for e in events],
            "suggested_transitions": [
                _project_suggestion(s) for s in suggestions
            ],
            "hold_reserved_return_target": return_target,
        }
    )


@api_view(["POST"])
@permission_classes(_M54_PERMS)
def admin_lifecycle_manual_transition(request, stock_number: str):
    """Apply a manual stage transition.

    Body: ``{"to_stage": "...", "notes": "..."}``.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = LifecycleManualTransitionRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        stage = advance_stage(
            vehicle,
            dealership=dealership,
            to_stage=data["to_stage"],
            actor=request.user,
            trigger=VEHICLE_STAGE_TRIGGER_MANUAL,
            notes=data.get("notes", ""),
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(
        {"current_stage": _project_stage(stage)},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes(_M54_PERMS)
def admin_lifecycle_rule_transition(request, stock_number: str):
    """Accept a rule-suggested transition.

    Body: ``{"rule_name": "..."}``.

    Re-evaluates :func:`suggest_transitions` at apply time. Refuses
    (409) if the specific rule no longer fires (the predicate has
    flipped since the operator saw the suggestion in the dashboard)
    or if the matched suggestion carries ``unmet_prerequisites``
    (e.g. ``photography_to_listing`` pending M6 photo predicate —
    the rule surfaces as a "waiting on X" hint, not an executable
    suggestion).
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = LifecycleRuleAcceptRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    rule_name = serializer.validated_data["rule_name"]

    try:
        suggestions = suggest_transitions(vehicle, dealership=dealership)
    except Exception as exc:
        return _map_service_error(exc)

    matched = next(
        (s for s in suggestions if s.rule_name == rule_name), None
    )
    if matched is None:
        return Response(
            {
                "detail": (
                    f"Rule {rule_name!r} does not currently fire for this "
                    "vehicle. It may have fired when the dashboard was "
                    "loaded but the predicate has since flipped."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )
    if matched.unmet_prerequisites:
        return Response(
            {
                "detail": (
                    f"Rule {rule_name!r} has unmet prerequisites and is "
                    "not yet executable: "
                    f"{'; '.join(matched.unmet_prerequisites)}"
                )
            },
            status=status.HTTP_409_CONFLICT,
        )

    try:
        stage = advance_stage(
            vehicle,
            dealership=dealership,
            to_stage=matched.to_stage,
            actor=request.user,
            trigger=VEHICLE_STAGE_TRIGGER_RULE,
            rule_name=matched.rule_name,
            notes=matched.evidence,
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(
        {"current_stage": _project_stage(stage)},
        status=status.HTTP_200_OK,
    )
