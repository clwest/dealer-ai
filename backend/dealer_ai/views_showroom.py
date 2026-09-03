"""Milestone 6 · Increment 5 (SESSION_086) — public showroom endpoint.

Two DRF endpoints that serve the retail-gated public view of the
customer-facing marketing / showroom UI:

- ``GET /api/dealer-ai/showroom/vehicles/`` — list retail-eligible
  vehicles (``stage='frontline'``, debug stocks excluded). Added
  at SESSION_226 (TASK_walkable-demo-and-servers-up 1d) so the
  public showroom, homepage teaser and hero visuals can call the
  real backend instead of importing ``frontend/src/data/
  sampleInventory.ts``. Publish gate is NOT applied on this list —
  the operator lot on Copper Canyon's install has ~130 frontline
  units and zero VehicleListing rows (M6 publishing is deferred);
  requiring a published listing here would leave the list empty.
- ``GET /api/dealer-ai/showroom/vehicles/<stock_number>/`` — return
  a single vehicle's facts + published listing body + primary photo.
  Requires both frontline stage AND a published
  :class:`VehicleListing` (older SESSION_086 contract). Missing /
  non-visible vehicles return HTTP 404 with the truthful "not
  currently available for retail" copy per SESSION_075 §5.i.

URL segment shape per SESSION_086 §2 Option A user-confirmed:
``stock_number`` (customer-friendly URLs; matches M6.2 canonical
photo-key namespacing).

Publish semantics per planning §5.e: visibility here is the M6
definition of "published." M6 v1 does NOT push to Facebook
Marketplace / AutoTrader — that's Milestone 11+.

**No authentication required.** This is the public read surface;
customers hit it directly (via marketing links, embed frames, etc.).
The retail gate (frontline stage, plus published listing for the
detail endpoint) is the authorization — non-retail vehicles simply
do not exist for the public caller.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import DealerOnboardingProfile, VehiclePhoto
from .services.chat_engine import (
    CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY,
    customer_lookup_visible_vehicle_by_stock,
    customer_visible_vehicles,
)
from .services.payment_engine import (
    render_estimated_payment_line,
    resolve_store_payment_defaults,
)
from .services.photo_storage import (
    ObjectStorageError,
    _get_default_adapter,
)
from .services.tenancy import get_current_dealership


_SHOWROOM_LIST_MAX_LIMIT = 200
_SHOWROOM_LIST_DEFAULT_LIMIT = 48


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


def _project_showroom_row(vehicle, *, payment_defaults: dict) -> dict:
    """Public-safe list projection for one retail-eligible vehicle.

    Mirrors the shape the deleted ``frontend/src/data/
    sampleInventory.ts`` module handed to the three consumers
    (PublicShowroomPage, DealershipHomePage, Hero), so the frontend
    edit is a pure hook-swap rather than a render refactor.

    No cost data, no lifecycle stage, no operator notes — only the
    fields a shopper's browser needs. SESSION_234 (finding 31) adds
    ``estimated_payment_line`` so the card can display a payment
    figure that matches the landing-page "payment-aware" copy.
    """
    return {
        "vin": vehicle.vin or "",
        "stock_number": vehicle.stock_number,
        "year": vehicle.year,
        "make": vehicle.make,
        "model": vehicle.model,
        "trim": vehicle.trim or "",
        "condition": vehicle.condition,
        "body_style": vehicle.body_style,
        "drivetrain": vehicle.drivetrain or "",
        "fuel_type": vehicle.fuel_type or "",
        "exterior_color": vehicle.exterior_color or "",
        "mileage": vehicle.mileage,
        "price": str(vehicle.price),
        "msrp": str(vehicle.msrp) if vehicle.msrp is not None else None,
        "image_url": vehicle.image_url or "",
        "vdp_url": vehicle.url or "",
        "display_name": str(vehicle),
        "estimated_payment_line": render_estimated_payment_line(
            vehicle.price, defaults=payment_defaults
        ),
    }


def _resolve_payment_defaults(dealership) -> dict:
    """Load the tenant profile once per request so N cards do not
    trigger N profile lookups. Falls back to module defaults when no
    profile exists yet.
    """
    profile = (
        DealerOnboardingProfile.objects.filter(dealership=dealership)
        .order_by("-updated_at")
        .first()
    )
    return resolve_store_payment_defaults(profile)


@api_view(["GET"])
@permission_classes([AllowAny])
def showroom_vehicle_list(request):
    """GET — retail-eligible vehicle list for the public showroom.

    Response body:

    - ``count`` — total retail-eligible vehicles matched (before the
      limit / offset window).
    - ``limit`` / ``offset`` — echo of applied window.
    - ``results`` — list of public-safe vehicle projections.

    Query params (all optional):

    - ``q`` — case-insensitive substring match against year / make /
      model / trim / stock_number / exterior_color.
    - ``limit`` — page size (default 48, hard-capped at 200).
    - ``offset`` — page offset (default 0).

    Retail gate: ``customer_visible_vehicles()`` (frontline stage,
    debug stocks excluded). Publish requirement is intentionally NOT
    applied — see the module docstring.

    SESSION_232 addendum — scope to the resolved dealership.
    ``get_current_dealership`` walks auth → ``X-Dealership-Slug``
    header → default. Without this the showroom returned every
    store's frontline cars on a multi-store install.
    """
    dealership = get_current_dealership(request)
    qs = (
        customer_visible_vehicles()
        .filter(dealership=dealership)
        .order_by("-year", "make", "model", "pk")
    )

    query_term = (request.GET.get("q") or "").strip()
    if query_term:
        from django.db.models import Q as _Q

        qs = qs.filter(
            _Q(stock_number__icontains=query_term)
            | _Q(make__icontains=query_term)
            | _Q(model__icontains=query_term)
            | _Q(trim__icontains=query_term)
            | _Q(exterior_color__icontains=query_term)
        )

    try:
        offset = max(0, int(request.GET.get("offset", "0")))
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = int(request.GET.get("limit", _SHOWROOM_LIST_DEFAULT_LIMIT))
    except (TypeError, ValueError):
        limit = _SHOWROOM_LIST_DEFAULT_LIMIT
    limit = max(1, min(_SHOWROOM_LIST_MAX_LIMIT, limit))

    total = qs.count()
    page = list(qs[offset : offset + limit])
    payment_defaults = _resolve_payment_defaults(dealership)

    return Response(
        {
            "count": total,
            "limit": limit,
            "offset": offset,
            "results": [
                _project_showroom_row(v, payment_defaults=payment_defaults)
                for v in page
            ],
            "payment_disclaimer": payment_defaults.get("disclaimer", ""),
        }
    )


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
    # SESSION_232 addendum — scope detail lookup to the resolved
    # dealership so a stock number in one store cannot leak through
    # another store's showroom URL.
    vehicle = customer_lookup_visible_vehicle_by_stock(
        stock_number, dealership=get_current_dealership(request)
    )
    if vehicle is None:
        return Response(
            {"detail": CUSTOMER_LOOKUP_NOT_AVAILABLE_COPY},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = vehicle.listing  # OneToOne — safe by construction
    payment_defaults = _resolve_payment_defaults(vehicle.dealership)
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
            "estimated_payment_line": render_estimated_payment_line(
                vehicle.price, defaults=payment_defaults
            ),
            "payment_disclaimer": payment_defaults.get("disclaimer", ""),
        }
    )
