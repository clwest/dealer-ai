"""Milestone 18 · Increment 5 (SESSION_151) — demo-store admin endpoints.

Per MILESTONE_18_PLANNING.md §7 M18.5 + §5.e Option A. One endpoint
lands at M18.5:

- ``POST /admin/demo-store/feedback/`` — capture tester feedback
  against a demo dealership. Reuses
  ``IsSalesManagerOrOwnerAtActiveDealership`` (zero-drift streak
  extends to fourteen consecutive milestones now). Body validated
  by a DRF serializer; category vocab from
  :data:`models.TESTER_FEEDBACK_CATEGORY_CHOICES`.

**Guardrail — demo-store-only.** The endpoint refuses to accept
feedback for a Dealership where ``is_demo=False`` per §5.g +
§5.c Option A belt-and-suspenders. A non-demo submit returns 403
with a descriptive message (403 instead of 500 because the
attempted-write is a permission-shape concern for a real
operator: "you cannot submit tester feedback against a live
dealership"; RuntimeError guards inside the service layer
protect against programming bugs).
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    TESTER_FEEDBACK_CATEGORY_CHOICES,
    TesterFeedback,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.tenancy import get_current_dealership


_M185_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]

_VALID_CATEGORIES = {key for key, _ in TESTER_FEEDBACK_CATEGORY_CHOICES}


class TesterFeedbackCreateRequestSerializer(serializers.Serializer):
    """Body validator for POST /admin/demo-store/feedback/.

    All fields except ``referenced_route`` are required. The empty
    string is permitted for ``referenced_route`` — some observations
    happen off-route (verbal feedback during a session).
    """

    tester_name = serializers.CharField(max_length=64)
    scenario_slug = serializers.CharField(max_length=64)
    category = serializers.CharField(max_length=32)
    note = serializers.CharField()
    referenced_route = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate_category(self, value: str) -> str:
        if value not in _VALID_CATEGORIES:
            raise serializers.ValidationError(
                f"Unknown category {value!r}. "
                f"Valid: {sorted(_VALID_CATEGORIES)!r}."
            )
        return value


def _project_feedback(row: TesterFeedback) -> dict:
    return {
        "id": row.pk,
        "dealership_id": row.dealership_id,
        "tester_name": row.tester_name,
        "scenario_slug": row.scenario_slug,
        "category": row.category,
        "note": row.note,
        "referenced_route": row.referenced_route,
        "created_at": row.created_at.isoformat(),
    }


@api_view(["POST"])
@permission_classes(_M185_PERMS)
def admin_demo_store_feedback_create(request):
    """POST /admin/demo-store/feedback/

    Capture tester feedback for the caller's demo dealership.
    Refuses submissions against a non-demo dealership (403).

    - 201 on success with the persisted TesterFeedback projection.
    - 400 on validation failure (missing / invalid category / etc.).
    - 403 when the caller's tenant is not a demo dealership.
    - 403 on non-permitted role (falls out of the permission
      class, not this handler).
    """
    dealership = get_current_dealership(request)
    if not dealership.is_demo:
        return Response(
            {
                "detail": (
                    "TesterFeedback submissions are only accepted "
                    "against demo dealerships (Dealership.is_demo=True)."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    body = TesterFeedbackCreateRequestSerializer(data=request.data)
    body.is_valid(raise_exception=True)
    row = TesterFeedback.objects.create(
        dealership=dealership,
        tester_name=body.validated_data["tester_name"],
        scenario_slug=body.validated_data["scenario_slug"],
        category=body.validated_data["category"],
        note=body.validated_data["note"],
        referenced_route=body.validated_data.get(
            "referenced_route", ""
        ),
    )
    return Response(
        {"tester_feedback": _project_feedback(row)},
        status=status.HTTP_201_CREATED,
    )
