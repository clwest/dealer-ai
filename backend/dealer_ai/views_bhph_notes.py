"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote admin endpoints.

Two endpoints per ``MILESTONE_12_PLANNING.md`` §7 M12.1:

- ``POST /admin/bhph-notes/`` — originate a BhphNote against a BHPH
  Sale. Computes ``payment_amount`` via the pure amortization verb
  and persists.
- ``GET  /admin/bhph-notes/<pk>/`` — tenant-scoped retrieve.
  Includes the computed payment schedule in the response so the
  operator UI can render the amortization without a second call.

Both gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``
(M4 permission class, matches M9-M11 admin posture).

Domain-error → HTTP mapping:

- :class:`CrossTenantBhphNoteError` → 404 (fail-closed).
- :class:`NonBhphSaleError` → 400 (caller supplied a non-BHPH sale).
- :class:`DuplicateBhphNoteError` → 409 (schema invariant).
- :class:`UnknownBhphFrequencyError` → 400.
- Missing lookups in-tenant → 404.
- Serializer error → 400.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    BHPH_PAYMENT_FREQUENCY_CHOICES,
    BhphNote,
    Sale,
)
from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.bhph_notes import (
    CrossTenantBhphNoteError,
    DuplicateBhphNoteError,
    NonBhphSaleError,
    get_bhph_note,
    get_payment_schedule,
    record_bhph_note,
)
from .services.payment_engine import UnknownBhphFrequencyError
from .services.tenancy import get_current_dealership


_M121_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _lookup_sale_or_404(dealership, sale_id):
    try:
        return Sale.objects.filter(dealership=dealership).get(pk=sale_id)
    except Sale.DoesNotExist:
        return None


class BhphNoteCreateRequestSerializer(serializers.Serializer):
    sale_id = serializers.IntegerField()
    principal_financed = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    apr = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0.00")
    )
    term_weeks = serializers.IntegerField(min_value=1)
    payment_frequency = serializers.ChoiceField(
        choices=[key for key, _ in BHPH_PAYMENT_FREQUENCY_CHOICES]
    )
    first_payment_due = serializers.DateField()
    default_grace_days = serializers.IntegerField(
        required=False, min_value=0, default=5
    )


def _project_bhph_note(note: BhphNote) -> dict:
    return {
        "id": note.pk,
        "sale_id": note.sale_id,
        "dealership_id": note.dealership_id,
        "principal_financed": str(note.principal_financed),
        "apr": str(note.apr),
        "term_weeks": note.term_weeks,
        "payment_frequency": note.payment_frequency,
        "payment_amount": str(note.payment_amount),
        "first_payment_due": note.first_payment_due.isoformat(),
        "default_grace_days": note.default_grace_days,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _project_schedule(note: BhphNote) -> list[dict]:
    return [
        {"due_date": due.isoformat(), "amount": str(amount)}
        for due, amount in get_payment_schedule(note)
    ]


@api_view(["GET"])
@permission_classes(_M121_PERMS)
def admin_bhph_note_list(request):
    """List BhphNotes for the caller's tenant.

    Added at M12.7 (SESSION_127) — the M12.7 portfolio dashboard
    needs a browsable list of notes. Thin QuerySet wrapper capped
    at 100 rows (matches M11.6 admin list convention). Ordering
    matches Meta (``-created_at``).
    """
    dealership = get_current_dealership(request)
    qs = BhphNote.objects.filter(dealership=dealership)
    rows = list(qs[:100])
    return Response(
        {
            "count": len(rows),
            "results": [_project_bhph_note(note) for note in rows],
        }
    )


@api_view(["POST"])
@permission_classes(_M121_PERMS)
def admin_bhph_note_create(request):
    dealership = get_current_dealership(request)
    serializer = BhphNoteCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    sale = _lookup_sale_or_404(dealership, data["sale_id"])
    if sale is None:
        return Response(
            {"detail": "Sale not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        note = record_bhph_note(
            dealership=dealership,
            sale=sale,
            principal_financed=data["principal_financed"],
            apr=data["apr"],
            term_weeks=data["term_weeks"],
            payment_frequency=data["payment_frequency"],
            first_payment_due=data["first_payment_due"],
            default_grace_days=data.get("default_grace_days", 5),
        )
    except CrossTenantBhphNoteError:
        return Response(
            {"detail": "Parent resource not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except NonBhphSaleError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    except DuplicateBhphNoteError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_409_CONFLICT
        )
    except UnknownBhphFrequencyError as exc:
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(
        {"bhph_note": _project_bhph_note(note)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M121_PERMS)
def admin_bhph_note_retrieve(request, pk: int):
    dealership = get_current_dealership(request)
    note = get_bhph_note(pk=pk, dealership=dealership)
    if note is None:
        return Response(
            {"detail": "BhphNote not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(
        {
            "bhph_note": _project_bhph_note(note),
            "payment_schedule": _project_schedule(note),
        },
        status=status.HTTP_200_OK,
    )
