"""Milestone 6 · Increment 5 (SESSION_086) — vehicle listing admin API.

Six DRF endpoints wrapping the M6.3 :mod:`services.vehicle_listing`
surface (five M6.3 write verbs + one GET) for the M6.5 operator UI:

- ``GET  /api/dealer-ai/admin/vehicles/<stock_number>/listing/`` —
  read the current listing (or ``null`` when none exists).
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/listing/draft/``
  — invoke :func:`services.vehicle_listing.draft_listing`.
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/listing/regenerate/``
  — invoke :func:`services.vehicle_listing.regenerate_draft`.
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/listing/approve/``
  — invoke :func:`services.vehicle_listing.approve_listing`.
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/listing/publish/``
  — invoke :func:`services.vehicle_listing.publish_listing`.
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/listing/unpublish/``
  — invoke :func:`services.vehicle_listing.unpublish_listing`.

URL shape per SESSION_086 §1 Option A user-confirmed: nested under
``/api/dealer-ai/admin/vehicles/<stock_number>/listing/``. Listing
is OneToOne with Vehicle so no per-listing external identifier is
needed at the URL layer.

Permission: shares
:class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership` with
the M4.6 / M5.4 / M6.5 photo admin surfaces.

Domain-error → HTTP mapping (per SESSION_084 M6.3 handoff):

- :class:`CrossTenantListingError` → 404 (fail-closed).
- :class:`InvalidListingTransitionError` → 409 (structural).
- :class:`ListingImmutableError` → 409 (state-forbidden operation).
- :class:`ListingScrubDroppedError` → 422 (AI safety refused).
- :class:`EmptyListingDraftError` → 422 (AI returned nothing).
- :class:`ValueError` → 400.
"""

from __future__ import annotations

from typing import Optional

from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Vehicle, VehicleListing
from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services import vehicle_listing
from .services.tenancy import get_current_dealership


_M65_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]


# ============================================================================
# Lookup helpers
# ============================================================================


def _lookup_vehicle_or_404(dealership, stock_number) -> Optional[Vehicle]:
    """Tenant-scoped lookup — same shape as M5.4."""
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _lookup_listing(vehicle) -> Optional[VehicleListing]:
    """Return the OneToOne listing for the vehicle, or ``None``."""
    return VehicleListing.objects.filter(vehicle=vehicle).first()


# ============================================================================
# Response projection
# ============================================================================


def _actor_dict(user_id, user) -> Optional[dict]:
    if user_id is None:
        return None
    return {"id": user_id, "username": user.username}


def _project_listing(listing: VehicleListing) -> dict:
    """Serialize one :class:`VehicleListing` for the operator UI."""
    return {
        "id": listing.pk,
        "vehicle_id": listing.vehicle_id,
        "status": listing.status,
        "title": listing.title,
        "body": listing.body,
        "source_provenance": listing.source_provenance,
        "drafted_by": _actor_dict(listing.drafted_by_id, listing.drafted_by),
        "drafted_at": listing.drafted_at,
        "approved_by": _actor_dict(
            listing.approved_by_id, listing.approved_by
        ),
        "approved_at": listing.approved_at,
        "published_by": _actor_dict(
            listing.published_by_id, listing.published_by
        ),
        "published_at": listing.published_at,
        "unpublished_by": _actor_dict(
            listing.unpublished_by_id, listing.unpublished_by
        ),
        "unpublished_at": listing.unpublished_at,
        "unpublished_reason": listing.unpublished_reason,
        "created_at": listing.created_at,
        "updated_at": listing.updated_at,
    }


# ============================================================================
# Error mapping
# ============================================================================


def _map_service_error(exc: Exception) -> Response:
    if isinstance(exc, vehicle_listing.CrossTenantListingError):
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(
        exc,
        (
            vehicle_listing.InvalidListingTransitionError,
            vehicle_listing.ListingImmutableError,
        ),
    ):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(
        exc,
        (
            vehicle_listing.ListingScrubDroppedError,
            vehicle_listing.EmptyListingDraftError,
        ),
    ):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if isinstance(exc, ValueError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    raise exc  # unknown → 500


# ============================================================================
# Request serializers
# ============================================================================


class ListingUnpublishRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)


# ============================================================================
# Endpoints
# ============================================================================


@api_view(["GET"])
@permission_classes(_M65_PERMS)
def admin_listing_read(request, stock_number: str):
    """GET — return the current listing for the vehicle (or ``null``
    when no listing exists yet).

    Used by the M6.5 UI on page load to render the current state
    (draft body + status + actor / timestamp history).
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = _lookup_listing(vehicle)
    return Response(
        {
            "stock_number": vehicle.stock_number,
            "listing": _project_listing(listing) if listing else None,
        }
    )


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_listing_draft(request, stock_number: str):
    """POST — invoke :func:`services.vehicle_listing.draft_listing`.

    Body: none (LLM assembles the source bundle from Vehicle + M3
    condition report + M6.2 photo count). Refused if a listing
    already exists (409).
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        listing = vehicle_listing.draft_listing(
            vehicle, dealership=dealership, drafted_by=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(
        _project_listing(listing), status=status.HTTP_201_CREATED
    )


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_listing_regenerate(request, stock_number: str):
    """POST — invoke :func:`services.vehicle_listing.regenerate_draft`.

    Refused if the listing is not in ``draft`` status (409).
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = _lookup_listing(vehicle)
    if listing is None:
        return Response(
            {"detail": "No listing exists for this vehicle yet."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        listing = vehicle_listing.regenerate_draft(
            listing, dealership=dealership, drafted_by=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_listing(listing))


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_listing_approve(request, stock_number: str):
    """POST — invoke :func:`services.vehicle_listing.approve_listing`."""
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = _lookup_listing(vehicle)
    if listing is None:
        return Response(
            {"detail": "No listing exists for this vehicle yet."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        listing = vehicle_listing.approve_listing(
            listing, dealership=dealership, approved_by=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_listing(listing))


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_listing_publish(request, stock_number: str):
    """POST — invoke :func:`services.vehicle_listing.publish_listing`.

    Publish semantics (planning §5.e): the listing becomes visible
    on ``/api/dealer-ai/showroom/vehicles/<stock_number>/``. M6 v1
    does NOT push to Facebook Marketplace / AutoTrader.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = _lookup_listing(vehicle)
    if listing is None:
        return Response(
            {"detail": "No listing exists for this vehicle yet."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        listing = vehicle_listing.publish_listing(
            listing, dealership=dealership, published_by=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_listing(listing))


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_listing_unpublish(request, stock_number: str):
    """POST — invoke :func:`services.vehicle_listing.unpublish_listing`.

    Body: ``{"reason": "..."}``. ``reason`` is required
    (nonblank) — the operator must explain the withdrawal for
    audit + downstream analytics.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    listing = _lookup_listing(vehicle)
    if listing is None:
        return Response(
            {"detail": "No listing exists for this vehicle yet."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = ListingUnpublishRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reason = serializer.validated_data["reason"]

    try:
        listing = vehicle_listing.unpublish_listing(
            listing,
            dealership=dealership,
            unpublished_by=request.user,
            reason=reason,
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_listing(listing))
