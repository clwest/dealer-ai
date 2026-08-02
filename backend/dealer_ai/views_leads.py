"""Milestone 11 · Increment 1 (SESSION_114) — non-chat lead intake endpoints.

Four write endpoints per MILESTONE_11_PLANNING.md §1.1 + §1.6 + §7 M11.1:

- ``POST /admin/leads/walk-in/``  → walk-in intake
- ``POST /admin/leads/phone/``    → phone intake
- ``POST /admin/leads/referral/`` → referral intake (with attribution FK)
- ``POST /admin/leads/webhook/``  → generic listing-platform webhook +
  adapter dispatch (§5.b Option A)

All four gate on
:class:`IsSalesManagerOrOwnerAtActiveDealership` (M4 permission class,
reused unchanged per §1.9). Every endpoint resolves ``dealership`` via
:func:`services.tenancy.get_current_dealership` and passes it
explicitly to the service verb.

Domain-error → HTTP mapping:

- :class:`UnknownWebhookPlatformError` → 400 (unknown ``platform``).
- :class:`CrossTenantReferrerError` → 404 (never leak cross-tenant
  existence, matching M2.6 / M3.6 / M4.6 / M9.1 / M10.1 convention).
- Serializer validation error → 400.

Thin translation layer — no business logic. All logic lives in
:mod:`services.leads.channel_intake`.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CustomerLead
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.leads import (
    CrossTenantReferrerError,
    UnknownWebhookPlatformError,
    record_phone_lead,
    record_referral_lead,
    record_walk_in_lead,
    record_webhook_lead,
)
from .services.leads.webhook_adapters import registered_platforms
from .services.tenancy import get_current_dealership


_M111_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


class _BaseIntakeSerializer(serializers.Serializer):
    """Shared field surface for walk-in / phone / referral write bodies.

    Mirrors the ``CustomerLead`` fields the M1 chat funnel currently
    populates from the lead form (name / phone / email / notes /
    target_monthly_payment / down_payment / trade_in / credit_range /
    urgency). ``name`` is required; everything else defaults to blank
    or None per the model column defaults.
    """

    name = serializers.CharField(max_length=128)
    phone = serializers.CharField(
        required=False, allow_blank=True, max_length=32, default=""
    )
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    target_monthly_payment = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=8,
        decimal_places=2,
        default=None,
    )
    down_payment = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=10,
        decimal_places=2,
        default=None,
    )
    trade_in = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
    credit_range = serializers.CharField(
        required=False, allow_blank=True, max_length=64, default=""
    )
    urgency = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        default="",
        choices=[key for key, _ in CustomerLead.URGENCY_CHOICES],
    )


class WalkInLeadRequestSerializer(_BaseIntakeSerializer):
    """Request shape for ``POST /admin/leads/walk-in/``."""


class PhoneLeadRequestSerializer(_BaseIntakeSerializer):
    """Request shape for ``POST /admin/leads/phone/``."""


class ReferralLeadRequestSerializer(_BaseIntakeSerializer):
    """Request shape for ``POST /admin/leads/referral/``.

    Optional ``referrer_lead_id`` names the parent CustomerLead. If
    provided but not owned by the caller's dealership, the endpoint
    returns 404.
    """

    referrer_lead_id = serializers.IntegerField(required=False, allow_null=True)


class WebhookLeadRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/leads/webhook/``.

    ``platform`` selects the adapter module in
    :mod:`services.leads.webhook_adapters`. ``payload`` is the
    platform-native envelope the adapter normalizes.
    """

    platform = serializers.CharField(max_length=64)
    payload = serializers.DictField()


def _project_lead(lead: CustomerLead) -> dict:
    """Response shape shared by every M11.1 intake endpoint.

    Kept small — just the fields the operator UI needs to confirm the
    write. Full lead detail lives at the existing
    ``/admin/lead/<id>/`` endpoint.
    """
    return {
        "id": lead.pk,
        "name": lead.name,
        "phone": lead.phone,
        "email": lead.email,
        "channel": lead.channel,
        "referrer_id": lead.referrer_id,
        "dealership_id": lead.dealership_id,
        "created_at": lead.created_at.isoformat(),
    }


# ---- Per-channel endpoints -------------------------------------------------


@api_view(["POST"])
@permission_classes(_M111_PERMS)
def admin_lead_walk_in_create(request):
    dealership = get_current_dealership(request)
    serializer = WalkInLeadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    lead = record_walk_in_lead(dealership=dealership, **data)
    return Response({"lead": _project_lead(lead)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes(_M111_PERMS)
def admin_lead_phone_create(request):
    dealership = get_current_dealership(request)
    serializer = PhoneLeadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    lead = record_phone_lead(dealership=dealership, **data)
    return Response({"lead": _project_lead(lead)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes(_M111_PERMS)
def admin_lead_referral_create(request):
    dealership = get_current_dealership(request)
    serializer = ReferralLeadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = dict(serializer.validated_data)
    referrer_lead_id = data.pop("referrer_lead_id", None)
    try:
        lead = record_referral_lead(
            dealership=dealership,
            referrer_lead_id=referrer_lead_id,
            **data,
        )
    except CrossTenantReferrerError:
        return Response(
            {"detail": "Referrer lead not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response({"lead": _project_lead(lead)}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes(_M111_PERMS)
def admin_lead_webhook_create(request):
    dealership = get_current_dealership(request)
    serializer = WebhookLeadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    try:
        lead = record_webhook_lead(
            dealership=dealership,
            platform=data["platform"],
            payload=data["payload"],
        )
    except UnknownWebhookPlatformError as exc:
        return Response(
            {
                "detail": str(exc),
                "registered_platforms": list(registered_platforms()),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({"lead": _project_lead(lead)}, status=status.HTTP_201_CREATED)
