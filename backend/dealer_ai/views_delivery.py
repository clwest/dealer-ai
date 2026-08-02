"""Milestone 9 · Increment 2 (SESSION_101) — admin API for the Delivery subsystem.

Two endpoints. Both compose :class:`IsAuthenticated` &
:class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership` per
``MILESTONE_9_PLANNING.md`` §1.6 (mirrors the M4-M8 pattern).
Advisor / porter / f_and_i_manager / collections all receive 403.

- ``POST /admin/vehicles/<stock>/delivery/`` — creates the Delivery
  for the vehicle's Sale. Vehicle-scoped URL mirrors the M9.1
  Sale endpoint shape.
- ``PATCH /admin/deliveries/<id>/`` — updates delivery fields.
  Supports partial updates: ``delivery_date``,
  ``temp_tag_number``, ``notes`` (direct column writes);
  ``checklist_key`` + ``checklist_value`` (delegates to
  :func:`services.delivery.update_checklist_item`); and
  ``verify_insurance=true`` (delegates to
  :func:`services.delivery.verify_insurance`).

Delegates entirely to :mod:`services.delivery`. No business logic
lives here.

Domain-error → HTTP status mapping:

- :class:`CrossTenantDeliveryError` → 404.
- :class:`SaleNotFoundForDeliveryError` → 409 (workflow ordering).
- :class:`DeliveryAlreadyExistsError` → 409.
- :class:`UnknownChecklistKeyError` → 400.
- :class:`ValueError` → 400.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    DELIVERY_CHECKLIST_KEYS,
    Delivery,
    Vehicle,
)
from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services import delivery as delivery_service
from .services.delivery import (
    CrossTenantDeliveryError,
    DeliveryAlreadyExistsError,
    SaleNotFoundForDeliveryError,
    UnknownChecklistKeyError,
)
from .services.tenancy import get_current_dealership


_M92_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]


def _lookup_vehicle_or_404(dealership, stock_number):
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _lookup_delivery_or_404(dealership, delivery_id):
    try:
        return (
            Delivery.objects.filter(dealership=dealership)
            .select_related("sale", "sale__vehicle")
            .get(pk=delivery_id)
        )
    except Delivery.DoesNotExist:
        return None


def _project_delivery(delivery: Delivery) -> dict:
    return {
        "id": delivery.pk,
        "sale_id": delivery.sale_id,
        "vehicle_stock": delivery.sale.vehicle.stock_number,
        "delivery_date": (
            delivery.delivery_date.isoformat()
            if delivery.delivery_date
            else None
        ),
        "checklist": delivery.checklist,
        "temp_tag_number": delivery.temp_tag_number,
        "insurance_verified": delivery.insurance_verified,
        "insurance_verified_at": (
            delivery.insurance_verified_at.isoformat()
            if delivery.insurance_verified_at
            else None
        ),
        "notes": delivery.notes,
        "created_at": delivery.created_at.isoformat(),
        "updated_at": delivery.updated_at.isoformat(),
    }


class DeliveryCreateRequestSerializer(serializers.Serializer):
    """Request shape for ``POST /admin/vehicles/<stock>/delivery/``."""

    delivery_date = serializers.DateField(required=False, allow_null=True)
    temp_tag_number = serializers.CharField(
        required=False, allow_blank=True, max_length=32, default=""
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class DeliveryPatchRequestSerializer(serializers.Serializer):
    """Request shape for ``PATCH /admin/deliveries/<id>/``.

    All fields optional — every submitted key is applied; unset
    keys leave the row unchanged. At most one of
    (``checklist_key`` + ``checklist_value``) OR
    ``verify_insurance`` may be present per request; combining is
    allowed but the mutations happen sequentially in the order:
    column fields → checklist toggle → insurance verification.
    """

    delivery_date = serializers.DateField(required=False, allow_null=True)
    temp_tag_number = serializers.CharField(
        required=False, allow_blank=True, max_length=32
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    checklist_key = serializers.ChoiceField(
        choices=list(DELIVERY_CHECKLIST_KEYS), required=False
    )
    checklist_value = serializers.BooleanField(required=False)
    verify_insurance = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if "checklist_key" in attrs and "checklist_value" not in attrs:
            raise serializers.ValidationError(
                "checklist_key requires checklist_value."
            )
        if "checklist_value" in attrs and "checklist_key" not in attrs:
            raise serializers.ValidationError(
                "checklist_value requires checklist_key."
            )
        return attrs


def _lookup_delivery_by_vehicle(dealership, vehicle):
    try:
        return (
            Delivery.objects.filter(dealership=dealership, sale__vehicle=vehicle)
            .select_related("sale", "sale__vehicle")
            .get()
        )
    except Delivery.DoesNotExist:
        return None


@api_view(["GET", "POST"])
@permission_classes(_M92_PERMS)
def admin_delivery_create(request, stock_number):
    """POST: create a Delivery for the vehicle's Sale (M9.2 write).

    GET: read the Delivery for the vehicle (M9.5 read companion).
    200 with ``{"delivery": ...}`` when a Delivery exists; 404
    when the vehicle has no Delivery yet (or no Sale — which
    surfaces the same way via the join filter). Cross-tenant
    vehicle → 404. URL name preserved
    (``admin-delivery-create``); GET dispatch is additive.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        delivery = _lookup_delivery_by_vehicle(dealership, vehicle)
        if delivery is None:
            return Response(
                {"detail": "Delivery not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"delivery": _project_delivery(delivery)})

    # POST — M9.2 create path. ``dealership`` + ``vehicle`` already
    # resolved above.
    serializer = DeliveryCreateRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        delivery = delivery_service.record_delivery(
            vehicle,
            dealership=dealership,
            delivery_date=data.get("delivery_date"),
            temp_tag_number=data.get("temp_tag_number", ""),
            notes=data.get("notes", ""),
        )
    except CrossTenantDeliveryError:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except SaleNotFoundForDeliveryError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    except DeliveryAlreadyExistsError as exc:
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
        {"delivery": _project_delivery(delivery)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes(_M92_PERMS)
def admin_delivery_update(request, delivery_id):
    dealership = get_current_dealership(request)
    delivery = _lookup_delivery_or_404(dealership, delivery_id)
    if delivery is None:
        return Response(
            {"detail": "Delivery not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = DeliveryPatchRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # ---- Direct column mutations (delivery_date, temp_tag_number, notes)
    dirty_fields = []
    if "delivery_date" in data:
        delivery.delivery_date = data["delivery_date"]
        dirty_fields.append("delivery_date")
    if "temp_tag_number" in data:
        delivery.temp_tag_number = data["temp_tag_number"]
        dirty_fields.append("temp_tag_number")
    if "notes" in data:
        delivery.notes = data["notes"]
        dirty_fields.append("notes")
    if dirty_fields:
        dirty_fields.append("updated_at")
        delivery.save(update_fields=dirty_fields)

    # ---- Checklist toggle (delegates to service verb).
    if "checklist_key" in data:
        try:
            delivery = delivery_service.update_checklist_item(
                delivery,
                dealership=dealership,
                key=data["checklist_key"],
                value=data["checklist_value"],
            )
        except UnknownChecklistKeyError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except CrossTenantDeliveryError:
            return Response(
                {"detail": "Delivery not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    # ---- Insurance verification (delegates to service verb).
    if data.get("verify_insurance"):
        try:
            delivery = delivery_service.verify_insurance(
                delivery, dealership=dealership
            )
        except CrossTenantDeliveryError:
            return Response(
                {"detail": "Delivery not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    # ``select_related`` needed for the projection's
    # ``sale.vehicle.stock_number`` access — re-fetch to be safe.
    delivery = _lookup_delivery_or_404(dealership, delivery.pk)
    return Response(
        {"delivery": _project_delivery(delivery)},
        status=status.HTTP_200_OK,
    )
