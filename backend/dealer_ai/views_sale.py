"""Milestone 9 · Increment 1 (SESSION_100) — admin API for the Sale subsystem.

One endpoint. Composes :class:`IsAuthenticated` &
:class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership` per
``MILESTONE_9_PLANNING.md`` §1.6 (mirrors the M4-M8 pattern).
Advisor / porter / f_and_i_manager / collections all receive 403.

Delegates entirely to :mod:`services.sale`. No business logic
lives here — thin translation between HTTP and the service surface.

Domain-error → HTTP status mapping (matches M4-M8 conventions):

- :class:`CrossTenantSaleError` → 404 (never leak whether the
  resource exists across tenants).
- :class:`SaleAlreadyExistsError` → 409 Conflict.
- :class:`ValueError` (unknown ``finance_type``, invalid decimal,
  missing lender for non-cash) → 400.

Tenant scoping: every endpoint resolves ``dealership`` via
:func:`services.tenancy.get_current_dealership` and passes it
explicitly into service calls. Cross-tenant lookups (URL kwarg
references a vehicle owned by another dealership) surface as 404
rather than 403, matching the M2.6 / M3.6 / M4.6 fail-closed
pattern.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    SALE_FINANCE_TYPE_CHOICES,
    CustomerLead,
    Sale,
    Vehicle,
)
from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services import sale as sale_service
from .services.sale import (
    CrossTenantSaleError,
    SaleAlreadyExistsError,
)
from .services.tenancy import get_current_dealership


_M91_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]


def _lookup_vehicle_or_404(dealership, stock_number):
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _lookup_buyer_or_404(dealership, lead_id):
    try:
        return CustomerLead.objects.filter(dealership=dealership).get(
            pk=lead_id
        )
    except CustomerLead.DoesNotExist:
        return None


def _project_sale(sale: Sale) -> dict:
    return {
        "id": sale.pk,
        "vehicle_stock": sale.vehicle.stock_number,
        "buyer_id": sale.buyer_id,
        "sale_date": sale.sale_date.isoformat(),
        "sold_price": str(sale.sold_price),
        "finance_type": sale.finance_type,
        "lender_name": sale.lender_name,
        "gross_realized": str(sale.gross_realized),
        "created_at": sale.created_at.isoformat(),
        "updated_at": sale.updated_at.isoformat(),
    }


class SaleCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/vehicles/<stock>/sale/``."""

    sale_date = serializers.DateField()
    sold_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    finance_type = serializers.ChoiceField(
        choices=[key for key, _ in SALE_FINANCE_TYPE_CHOICES]
    )
    buyer_id = serializers.IntegerField(required=False, allow_null=True)
    lender_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


def _lookup_sale_or_404(dealership, vehicle):
    try:
        return (
            Sale.objects.filter(dealership=dealership, vehicle=vehicle)
            .select_related("buyer")
            .get()
        )
    except Sale.DoesNotExist:
        return None


@api_view(["GET", "POST"])
@permission_classes(_M91_PERMS)
def admin_sale_create(request, stock_number):
    """POST: create a Sale for the vehicle (M9.1 write path).

    GET: read the Sale for the vehicle (M9.5 read companion). 200
    with ``{"sale": ...}`` when the Sale exists; 404 when the
    vehicle has no Sale yet. Cross-tenant vehicle → 404 (never
    leak). URL name preserved (``admin-sale-create``) so existing
    tests + docs keep working; GET dispatch is additive.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        sale = _lookup_sale_or_404(dealership, vehicle)
        if sale is None:
            return Response(
                {"detail": "Sale not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"sale": _project_sale(sale)})

    # POST — M9.1 create path. ``dealership`` + ``vehicle`` already
    # resolved above.
    serializer = SaleCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    buyer = None
    if data.get("buyer_id") is not None:
        buyer = _lookup_buyer_or_404(dealership, data["buyer_id"])
        if buyer is None:
            return Response(
                {"detail": "Buyer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    try:
        sale = sale_service.record_sale(
            vehicle,
            dealership=dealership,
            sale_date=data["sale_date"],
            sold_price=data["sold_price"],
            finance_type=data["finance_type"],
            buyer=buyer,
            lender_name=data.get("lender_name", ""),
            # M15.1 — propagate the acting user so the sibling
            # sale-booking JournalEntry's ``posted_by_user`` FK is
            # populated and the M14.3 browser shows who booked the
            # sale.
            posted_by_user=request.user,
        )
    except CrossTenantSaleError:
        # Never leak cross-tenant existence. Same fail-closed shape
        # as M2.6 / M3.6 / M4.6.
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except SaleAlreadyExistsError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"sale": _project_sale(sale)},
        status=status.HTTP_201_CREATED,
    )
