"""Milestone 12 · Increment 5 (SESSION_125) — CollectionContact endpoints.

Two endpoints per ``MILESTONE_12_PLANNING.md`` §7 M12.5:

- ``POST /admin/bhph-notes/<pk>/contacts/`` — log a contact attempt.
- ``GET  /admin/bhph-notes/<pk>/contacts/list/`` — list per-note.

All gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``.

Domain-error → HTTP mapping:

- :class:`CrossTenantContactError` → 404 (fail-closed).
- :class:`UnknownChannelError` → 400.
- :class:`UnknownOutcomeError` → 400.
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    BHPH_CONTACT_CHANNEL_CHOICES,
    BHPH_CONTACT_OUTCOME_CHOICES,
    BhphNote,
    CollectionContact,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.collection_contacts import (
    CrossTenantContactError,
    UnknownChannelError,
    UnknownOutcomeError,
    list_contacts,
    record_contact,
)
from .services.tenancy import get_current_dealership


_M125_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_note_or_404(dealership, note_pk):
    try:
        return BhphNote.objects.filter(dealership=dealership).get(pk=note_pk)
    except BhphNote.DoesNotExist:
        return None


class ContactCreateRequestSerializer(serializers.Serializer):
    contacted_at = serializers.DateTimeField()
    channel = serializers.ChoiceField(
        choices=[key for key, _ in BHPH_CONTACT_CHANNEL_CHOICES]
    )
    outcome = serializers.ChoiceField(
        choices=[key for key, _ in BHPH_CONTACT_OUTCOME_CHOICES]
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


def _project_contact(contact: CollectionContact) -> dict:
    return {
        "id": contact.pk,
        "note_id": contact.note_id,
        "dealership_id": contact.dealership_id,
        "contacted_at": contact.contacted_at.isoformat(),
        "contacted_by_user_id": contact.contacted_by_user_id,
        "channel": contact.channel,
        "outcome": contact.outcome,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat(),
        "updated_at": contact.updated_at.isoformat(),
    }


@api_view(["POST"])
@permission_classes(_M125_PERMS)
def admin_collection_contact_create(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ContactCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        contact = record_contact(
            dealership=dealership,
            note=note,
            contacted_at=data["contacted_at"],
            channel=data["channel"],
            outcome=data["outcome"],
            contacted_by_user=request.user if request.user.is_authenticated else None,
            notes=data.get("notes", ""),
        )
    except CrossTenantContactError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except (UnknownChannelError, UnknownOutcomeError) as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"collection_contact": _project_contact(contact)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M125_PERMS)
def admin_collection_contact_list(request, pk: int):
    dealership = get_current_dealership(request)
    note = _lookup_note_or_404(dealership, pk)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    contacts = list_contacts(dealership=dealership, note=note)
    return Response(
        {
            "count": len(contacts),
            "results": [_project_contact(c) for c in contacts],
        },
        status=status.HTTP_200_OK,
    )
