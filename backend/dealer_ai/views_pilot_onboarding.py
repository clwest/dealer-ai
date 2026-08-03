"""Milestone 19 · Increment 3 (SESSION_156) — pilot onboarding admin endpoints.

Per MILESTONE_19_PLANNING.md §7 M19.3 + §0.a M19.3 decisions
(user-confirmed at SESSION_156 open):

**Decision 1 — inventory-import endpoint deferred to M19.4.** M19.3
ships four lifecycle endpoints (create, list, checklist advance,
terminate). The
``POST admin/pilots/<slug>/inventory/import/`` endpoint ships with
its M19.4 frontend consumer to keep the file-upload UX + backend
receiver in one unit of review.

**Decision 2 — `IsAuthenticated` alone.** The two existing role-
gated permission classes (``IsDealerOwnerAtActiveDealership`` +
``IsSalesManagerOrOwnerAtActiveDealership``) require the caller to
hold a role at their *active* tenant. That does not fit the pilot
admin surface — at ``POST /admin/pilots/create/`` the target pilot
does not exist yet; the caller (Chris, the platform operator) has
no active-pilot-tenant to hold a role in. Rather than add a new
``IsPlatformOperator`` class and break the zero-drift streak, we
gate on ``IsAuthenticated`` and rely on the DealerKit control tenant
being the only authenticated context in practice. **Zero-drift
streak extends to seventeen consecutive milestones** (M10 → M19.3).

Domain-error → HTTP mapping (each handler catches at the boundary):

- :class:`PilotAlreadyExistsError` → 409 (slug collision).
- :class:`NonPilotTerminationError` → 500 (broken invariant).
- :class:`UnknownChecklistStepError` → 400.
- :class:`ChecklistStepAlreadyCompletedError` → 409.
- :class:`PilotReadinessNotConfirmedError` → 409.
- Nonexistent pilot slug in URL → 404 (via ``get_object_or_404``).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    PILOT_ONBOARDING_STEP_CHOICES,
    PILOT_ONBOARDING_STEP_ORDER,
    PILOT_TERMINATION_MODE_ARCHIVE,
    PILOT_TERMINATION_MODE_CHOICES,
    Dealership,
    PilotOnboardingChecklist,
    PilotOnboardingStep,
)
from .services.pilot_onboarding import (
    ChecklistStepAlreadyCompletedError,
    NonPilotTerminationError,
    PilotAlreadyExistsError,
    PilotReadinessNotConfirmedError,
    UnknownChecklistStepError,
    advance_step,
    create_pilot_dealership,
    list_pilot_dealerships,
    terminate_pilot,
)


User = get_user_model()

_M193_PERMS = [IsAuthenticated]

_VALID_STEP_SLUGS = {key for key, _ in PILOT_ONBOARDING_STEP_CHOICES}
_VALID_TERMINATION_MODES = {key for key, _ in PILOT_TERMINATION_MODE_CHOICES}


# ---------------------------------------------------------------------------
# Serializers — request bodies
# ---------------------------------------------------------------------------


class PilotCreateRequestSerializer(serializers.Serializer):
    """Body validator for ``POST /admin/pilots/create/``.

    ``owner_username`` locates an existing User row (created out-of-
    band; M19.3 does not spin up new Users). ``profile_kwargs``
    accepts any DealerOnboardingProfile fields the operator wants
    populated at create time; empty ``{}`` is fine per §5.c Option A
    (Chris fills the profile progressively via the
    ``profile_configured`` checklist step).
    """

    slug = serializers.SlugField(max_length=64)
    name = serializers.CharField(max_length=128)
    owner_username = serializers.CharField(max_length=150)
    profile_kwargs = serializers.DictField(
        child=serializers.JSONField(), required=False, default=dict
    )


class ChecklistAdvanceRequestSerializer(serializers.Serializer):
    """Body validator for ``POST /admin/pilots/<slug>/checklist/advance/``."""

    step_slug = serializers.CharField(max_length=64)
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_step_slug(self, value: str) -> str:
        if value not in _VALID_STEP_SLUGS:
            raise serializers.ValidationError(
                f"Unknown step_slug={value!r}. Valid: "
                f"{sorted(_VALID_STEP_SLUGS)!r}."
            )
        return value


class TerminateRequestSerializer(serializers.Serializer):
    """Body validator for ``POST /admin/pilots/<slug>/terminate/``."""

    reason = serializers.CharField(allow_blank=True, default="")
    mode = serializers.CharField(
        max_length=16, default=PILOT_TERMINATION_MODE_ARCHIVE
    )

    def validate_mode(self, value: str) -> str:
        if value not in _VALID_TERMINATION_MODES:
            raise serializers.ValidationError(
                f"Unknown mode={value!r}. Valid: "
                f"{sorted(_VALID_TERMINATION_MODES)!r}."
            )
        return value


# ---------------------------------------------------------------------------
# Projections — response bodies
# ---------------------------------------------------------------------------


def _project_dealership(d: Dealership) -> dict:
    return {
        "id": d.pk,
        "slug": d.slug,
        "name": d.name,
        "is_pilot": d.is_pilot,
        "is_demo": d.is_demo,
        "outbound_enabled": d.outbound_enabled,
        "terminated_at": (
            d.terminated_at.isoformat() if d.terminated_at else None
        ),
        "termination_reason": d.termination_reason,
        "created_at": d.created_at.isoformat(),
    }


def _project_step(step: PilotOnboardingStep) -> dict:
    return {
        "step_slug": step.step_slug,
        "completed_at": (
            step.completed_at.isoformat() if step.completed_at else None
        ),
        "completed_by_username": (
            step.completed_by.username if step.completed_by else None
        ),
        "notes": step.notes,
    }


def _project_checklist(checklist: PilotOnboardingChecklist) -> dict:
    """Project a checklist + its ordered step rows.

    Steps are surfaced in :data:`PILOT_ONBOARDING_STEP_ORDER` — the
    fixed vocab order — so the admin surface renders a stable
    checklist regardless of insertion order. Steps not yet completed
    are surfaced as ``None`` placeholders keyed by ``step_slug`` so
    the operator can see what's outstanding.
    """
    completed = {
        step.step_slug: step
        for step in PilotOnboardingStep.objects.filter(
            checklist=checklist
        )
    }
    steps = []
    for slug in PILOT_ONBOARDING_STEP_ORDER:
        step = completed.get(slug)
        if step is not None:
            steps.append(_project_step(step))
        else:
            steps.append(
                {
                    "step_slug": slug,
                    "completed_at": None,
                    "completed_by_username": None,
                    "notes": "",
                }
            )
    return {
        "id": checklist.pk,
        "dealership_id": checklist.dealership_id,
        "is_ready": checklist.is_ready,
        "steps": steps,
    }


def _project_pilot_with_checklist(d: Dealership) -> dict:
    """Combined pilot + checklist projection for create / detail responses."""
    checklist = PilotOnboardingChecklist.objects.filter(
        dealership=d
    ).first()
    return {
        "dealership": _project_dealership(d),
        "checklist": (
            _project_checklist(checklist) if checklist else None
        ),
    }


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes(_M193_PERMS)
def admin_pilot_create(request):
    """``POST /admin/pilots/create/``

    Create a fresh pilot dealership + attach ``owner_username`` as
    dealer_owner + fire the checklist. Refuses:

    - 400 on validation failure (missing field / unknown user).
    - 409 on slug collision (:class:`PilotAlreadyExistsError`).
    """
    body = PilotCreateRequestSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    owner_username = body.validated_data["owner_username"]
    try:
        owner_user = User.objects.get(username=owner_username)
    except User.DoesNotExist:
        return Response(
            {
                "detail": (
                    f"owner_username={owner_username!r} does not match "
                    "an existing User. Create the User out-of-band "
                    "before running create_pilot_dealership."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        dealership, _checklist = create_pilot_dealership(
            slug=body.validated_data["slug"],
            name=body.validated_data["name"],
            owner_user=owner_user,
            profile_kwargs=body.validated_data.get("profile_kwargs") or {},
            actor=request.user,
        )
    except PilotAlreadyExistsError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    return Response(
        {"pilot": _project_pilot_with_checklist(dealership)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M193_PERMS)
def admin_pilot_list(request):
    """``GET /admin/pilots/``

    Return every active pilot Dealership (``is_pilot=True`` AND
    ``terminated_at IS NULL``). Terminated pilots are excluded from
    the operator surface per M19.1 §5.h Option A posture.
    """
    pilots = list_pilot_dealerships()
    return Response(
        {
            "pilots": [
                _project_pilot_with_checklist(d) for d in pilots
            ]
        }
    )


@api_view(["POST"])
@permission_classes(_M193_PERMS)
def admin_pilot_checklist_advance(request, slug: str):
    """``POST /admin/pilots/<slug>/checklist/advance/``

    Add a :class:`PilotOnboardingStep` row for ``step_slug`` on the
    pilot's checklist. Refuses:

    - 400 on unknown ``step_slug``
      (:class:`UnknownChecklistStepError`) or validation failure.
    - 404 if the ``<slug>`` doesn't match a pilot dealership.
    - 409 on step-already-completed or readiness precondition
      violation (:class:`ChecklistStepAlreadyCompletedError`,
      :class:`PilotReadinessNotConfirmedError`).
    """
    dealership = get_object_or_404(
        Dealership, slug=slug, is_pilot=True
    )
    checklist = get_object_or_404(
        PilotOnboardingChecklist, dealership=dealership
    )
    body = ChecklistAdvanceRequestSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    try:
        advance_step(
            checklist=checklist,
            step_slug=body.validated_data["step_slug"],
            completed_by=request.user,
            notes=body.validated_data.get("notes", "") or "",
        )
    except UnknownChecklistStepError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except (
        ChecklistStepAlreadyCompletedError,
        PilotReadinessNotConfirmedError,
    ) as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    checklist.refresh_from_db()
    return Response(
        {"pilot": _project_pilot_with_checklist(dealership)}
    )


@api_view(["POST"])
@permission_classes(_M193_PERMS)
def admin_pilot_terminate(request, slug: str):
    """``POST /admin/pilots/<slug>/terminate/``

    Terminate a pilot with ``mode='archive'`` (default) or
    ``mode='cleanup'`` per §5.h Option A. Refuses:

    - 400 on unknown mode / validation failure.
    - 404 if ``<slug>`` doesn't match a pilot dealership.
    - 500 on :class:`NonPilotTerminationError` (broken-invariant
      guard — signals a routing bug at the caller).
    """
    dealership = get_object_or_404(
        Dealership, slug=slug, is_pilot=True
    )
    body = TerminateRequestSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    try:
        terminated = terminate_pilot(
            dealership=dealership,
            reason=body.validated_data.get("reason", "") or "",
            actor=request.user,
            mode=body.validated_data["mode"],
        )
    except NonPilotTerminationError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return Response(
        {"dealership": _project_dealership(terminated)}
    )
