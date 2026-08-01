"""Milestone 6 · Increment 5 (SESSION_086) — public showroom endpoint.

One DRF endpoint that serves the retail-gated public view of a
single vehicle for the customer-facing marketing / showroom UI:

- ``GET /api/dealer-ai/showroom/vehicles/<stock_number>/`` — return
  vehicle facts + published listing body + primary photo URL. Only
  vehicles that are ``stage='frontline'`` AND have a published
  :class:`VehicleListing` are visible. Missing / non-visible
  vehicles return HTTP 404 with the truthful "not currently
  available for retail" copy per SESSION_075 §5.i.

URL segment shape per SESSION_086 §2 Option A user-confirmed:
``stock_number`` (customer-friendly URLs; matches M6.2 canonical
photo-key namespacing).

Publish semantics per planning §5.e: visibility here is the M6
definition of "published." M6 v1 does NOT push to Facebook
Marketplace / AutoTrader — that's Milestone 11+.

**No authentication required.** This is the public read surface;
customers hit it directly (via marketing links, embed frames, etc.).
The retail gate (frontline + published listing) is the authorization
— non-retail vehicles simply do not exist for the public caller.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import VehiclePhoto
from .services.chat_engine import (
    CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY,
    customer_lookup_visible_vehicle_by_stock,
)
from .services.photo_storage import (
    ObjectStorageError,
    _get_default_adapter,
)


def _project_primary_photo(vehicle) -> dict | None:
    """Return the primary photo's signed read URL + dimensions, or
    ``None`` when the vehicle has no primary photo.

    Missing storage-side signing (backend fault) falls through to
    ``None`` rather than raising — the showroom page should render
    the vehicle facts even when the image path is transiently
    unavailable.
    """
    primary = (
        VehiclePhoto.objects.filter(
            vehicle=vehicle,
            is_primary=True,
            marked_deleted_at__isnull=True,
        )
        .first()
    )
    if primary is None:
        return None
    try:
        read_url = _get_default_adapter().generate_read_url(
            storage_key=primary.storage_key, ttl_seconds=900
        )
    except ObjectStorageError:
        read_url = ""
    return {
        "public_id": str(primary.public_id),
        "read_url": read_url,
        "width_px": primary.width_px,
        "height_px": primary.height_px,
        "caption": primary.caption,
    }


def _project_gallery(vehicle, *, limit: int = 20) -> list:
    """Return signed read URLs for up to ``limit`` non-deleted photos,
    ordered by ``sort_order, uploaded_at`` (matches
    :meth:`VehiclePhoto.Meta.ordering`)."""
    adapter = _get_default_adapter()
    projected: list[dict] = []
    photos = (
        VehiclePhoto.objects.filter(
            vehicle=vehicle, marked_deleted_at__isnull=True
        )
        .order_by("sort_order", "uploaded_at")[:limit]
    )
    for photo in photos:
        try:
            read_url = adapter.generate_read_url(
                storage_key=photo.storage_key, ttl_seconds=900
            )
        except ObjectStorageError:
            read_url = ""
        projected.append(
            {
                "public_id": str(photo.public_id),
                "read_url": read_url,
                "width_px": photo.width_px,
                "height_px": photo.height_px,
                "caption": photo.caption,
                "is_primary": photo.is_primary,
                "sort_order": photo.sort_order,
            }
        )
    return projected


@api_view(["GET"])
@permission_classes([AllowAny])
def showroom_vehicle_detail(request, stock_number: str):
    """GET — return the public showroom view of one vehicle.

    Response body (on success):

    - ``stock_number`` — echoed.
    - ``vehicle`` — public-safe subset of Vehicle fields
      (no internal cost data, no inspector notes, no recon tiers).
    - ``listing`` — the published listing's ``title`` + ``body``.
    - ``primary_photo`` — signed read URL for the hero photo (or
      ``null``).
    - ``gallery`` — signed read URLs for up to 20 non-deleted
      photos ordered by ``sort_order``.
    - ``price`` — vehicle price.

    On refusal (vehicle not found OR not retail-gated OR listing
    not published): HTTP 404 with the truthful
    :data:`CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY` per SESSION_075 §5.i.
    """
    vehicle = customer_lookup_visible_vehicle_by_stock(stock_number)
    if vehicle is None:
        return Response(
            {"detail": CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = vehicle.listing  # OneToOne — safe by construction
    return Response(
        {
            "stock_number": vehicle.stock_number,
            "vehicle": {
                "year": vehicle.year,
                "make": getattr(vehicle, "make", "") or "",
                "model": vehicle.model,
                "trim": getattr(vehicle, "trim", "") or "",
                "body_style": getattr(vehicle, "body_style", "") or "",
                "condition": getattr(vehicle, "condition", "") or "",
                "mileage": getattr(vehicle, "mileage", None),
                "vin_last_6": (
                    (getattr(vehicle, "vin", "") or "")[-6:]
                    if getattr(vehicle, "vin", "")
                    else ""
                ),
            },
            "listing": {
                "title": listing.title,
                "body": listing.body,
                "published_at": listing.published_at,
            },
            "primary_photo": _project_primary_photo(vehicle),
            "gallery": _project_gallery(vehicle),
            "price": vehicle.price,
        }
    )
