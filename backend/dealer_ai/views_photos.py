"""Milestone 6 · Increment 5 (SESSION_086) — vehicle photo admin API.

Six DRF endpoints wrapping the M6.2 :mod:`services.photo_gallery`
surface for the M6.5 operator UI to consume:

- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/photos/`` —
  upload one photo (multipart form). Returns projected
  :class:`VehiclePhoto` metadata.
- ``GET  /api/dealer-ai/admin/vehicles/<stock_number>/photos/`` —
  list all photos for the vehicle (including marked-deleted, so
  the UI can render both galleries).
- ``POST /api/dealer-ai/admin/vehicles/<stock_number>/photos/reorder/``
  — bulk-update ``sort_order`` per an ordered list of ``public_id``
  values.
- ``POST /api/dealer-ai/admin/vehicle-photos/<uuid:public_id>/set-primary/``
  — flip the target photo's ``is_primary=True`` and clear any
  previous primary atomically.
- ``DELETE /api/dealer-ai/admin/vehicle-photos/<uuid:public_id>/`` —
  safer-direction delete (stamps ``marked_deleted_at`` +
  ``deleted_by``).
- ``POST /api/dealer-ai/admin/vehicle-photos/<uuid:public_id>/restore/``
  — reverse safer-direction delete.

URL shape per SESSION_086 §1 Option A user-confirmed:

- Vehicle-scoped operations (upload / list / reorder) nested under
  ``/api/dealer-ai/admin/vehicles/<stock_number>/photos/``.
- Photo mutations by ``public_id`` under
  ``/api/dealer-ai/admin/vehicle-photos/<uuid:public_id>/`` —
  tenant-safe external identifier from M6.2 SESSION_083 §2.

Permission: shares :class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership`
with the M4.6 / M5.4 admin surfaces. Per-photo tenant isolation is
enforced inside :mod:`services.photo_gallery` via
:class:`CrossTenantPhotoError` (mapped to HTTP 404).

Domain-error → HTTP mapping:

- :class:`CrossTenantPhotoError` → 404 (fail-closed).
- :class:`PhotoValidationError` → 400.
- :class:`PhotoAlreadyDeletedError` → 409.
- :class:`PhotoNotDeletedError` → 409.
- :class:`photo_storage.InvalidContentTypeError` → 415 (unsupported
  media type — the M6.1 3-value whitelist).
- :class:`photo_storage.InvalidStorageKeyError` → 400 (validation).
- :class:`photo_storage.ObjectStorageError` → 502 (backend fault).
"""

from __future__ import annotations

import uuid
from typing import Optional

from rest_framework import serializers, status
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Vehicle, VehiclePhoto
from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services import photo_gallery, photo_storage
from .services.tenancy import get_current_dealership


_M65_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]


# ============================================================================
# Lookup helpers
# ============================================================================


def _lookup_vehicle_or_404(dealership, stock_number) -> Optional[Vehicle]:
    """Same pattern as M5.4 ``views_lifecycle._lookup_vehicle_or_404``
    — tenant-scoped queryset so cross-tenant + nonexistent both
    surface as 404."""
    try:
        return Vehicle.objects.filter(dealership=dealership).get(
            stock_number=stock_number
        )
    except Vehicle.DoesNotExist:
        return None


def _lookup_photo_or_404(
    dealership, public_id: uuid.UUID
) -> Optional[VehiclePhoto]:
    """Tenant-scoped lookup by ``public_id``.

    Cross-tenant lookups surface as 404 (queryset scoped to
    caller's dealership). Mirrors M5.4's fail-closed posture."""
    try:
        return VehiclePhoto.objects.filter(dealership=dealership).get(
            public_id=public_id
        )
    except VehiclePhoto.DoesNotExist:
        return None


# ============================================================================
# Response projection
# ============================================================================


def _project_photo(photo: VehiclePhoto) -> dict:
    """Serialize one :class:`VehiclePhoto` for the operator UI.

    Includes a signed read URL (short-lived) so the UI can render the
    thumbnail without a separate URL request. In local-mode
    (:mod:`services.photo_storage._LocalAdapter`) the URL is a
    marker string; the UI detects the marker prefix and routes to a
    local-only debug path.
    """
    try:
        read_url = photo_storage._get_default_adapter().generate_read_url(
            storage_key=photo.storage_key, ttl_seconds=900
        )
    except photo_storage.ObjectStorageError:
        read_url = ""
    return {
        "public_id": str(photo.public_id),
        "vehicle_id": photo.vehicle_id,
        "storage_key": photo.storage_key,
        "content_type": photo.content_type,
        "width_px": photo.width_px,
        "height_px": photo.height_px,
        "sort_order": photo.sort_order,
        "is_primary": photo.is_primary,
        "caption": photo.caption,
        "read_url": read_url,
        "uploaded_by": (
            {
                "id": photo.uploaded_by_id,
                "username": photo.uploaded_by.username,
            }
            if photo.uploaded_by_id is not None
            else None
        ),
        "uploaded_at": photo.uploaded_at,
        "marked_deleted_at": photo.marked_deleted_at,
        "deleted_by": (
            {
                "id": photo.deleted_by_id,
                "username": photo.deleted_by.username,
            }
            if photo.deleted_by_id is not None
            else None
        ),
        "updated_at": photo.updated_at,
    }


# ============================================================================
# Error mapping
# ============================================================================


def _map_service_error(exc: Exception) -> Response:
    """Domain-error → HTTP mapping per M6.5 §M6.5 handoff.

    Distinct classes → distinct status codes. Mirrors the M5.4
    ``_map_service_error`` posture."""
    if isinstance(exc, photo_gallery.CrossTenantPhotoError):
        return Response(
            {"detail": "Not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if isinstance(
        exc,
        (
            photo_gallery.PhotoAlreadyDeletedError,
            photo_gallery.PhotoNotDeletedError,
        ),
    ):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, photo_storage.InvalidContentTypeError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    if isinstance(
        exc,
        (
            photo_gallery.PhotoValidationError,
            photo_storage.InvalidStorageKeyError,
        ),
    ):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if isinstance(exc, photo_storage.ObjectStorageError):
        return Response(
            {
                "detail": (
                    "Photo storage backend failed. Retry shortly; "
                    "operator support if the failure persists."
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )
    if isinstance(exc, ValueError):
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    raise exc  # unknown — re-raise so it becomes a 500


# ============================================================================
# Request serializers
# ============================================================================


class PhotoUploadRequestSerializer(serializers.Serializer):
    """Multipart upload payload. ``file`` is the image bytes; the
    other fields describe the metadata."""

    file = serializers.FileField()
    width_px = serializers.IntegerField(min_value=1)
    height_px = serializers.IntegerField(min_value=1)
    caption = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    sort_order = serializers.IntegerField(required=False, default=0)


class PhotoReorderRequestSerializer(serializers.Serializer):
    """Ordered list of photo ``public_id`` values. Position in the
    list becomes the new ``sort_order`` (0-indexed)."""

    ordered_public_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )


# ============================================================================
# Endpoints — vehicle-scoped
# ============================================================================


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@permission_classes(_M65_PERMS)
def admin_photo_upload(request, stock_number: str):
    """POST — upload one photo for the vehicle at ``stock_number``.

    Multipart form fields: ``file``, ``width_px``, ``height_px``,
    ``caption`` (optional), ``sort_order`` (optional).

    Returns 201 + projected photo metadata on success. The M6.5 UI
    typically re-fetches the gallery list after upload rather than
    threading a single-photo insert into local state.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PhotoUploadRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    upload = data["file"]

    try:
        photo = photo_gallery.upload_photo(
            vehicle,
            dealership=dealership,
            data=upload.read(),
            content_type=upload.content_type or "",
            width_px=data["width_px"],
            height_px=data["height_px"],
            caption=data.get("caption", ""),
            sort_order=data.get("sort_order", 0),
            actor=request.user,
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(
        _project_photo(photo),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes(_M65_PERMS)
def admin_photo_list(request, stock_number: str):
    """GET — list all photos for the vehicle at ``stock_number``.

    Includes marked-deleted rows so the UI can offer the "restore"
    affordance from a "recently deleted" panel. Ordered by
    ``sort_order, uploaded_at`` (matches :meth:`VehiclePhoto.Meta.ordering`).
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    photos = (
        VehiclePhoto.objects.filter(vehicle=vehicle, dealership=dealership)
        .select_related("uploaded_by", "deleted_by")
        .order_by("sort_order", "uploaded_at")
    )
    return Response(
        {
            "stock_number": vehicle.stock_number,
            "photos": [_project_photo(p) for p in photos],
        }
    )


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_photo_reorder(request, stock_number: str):
    """POST — bulk update ``sort_order`` per the caller-supplied
    ordering of ``public_id`` values.

    Rejects PKs that don't belong to the vehicle (400) — the M6.2
    service raises :class:`PhotoValidationError` which surfaces via
    :func:`_map_service_error`.
    """
    dealership = get_current_dealership(request)
    vehicle = _lookup_vehicle_or_404(dealership, stock_number)
    if vehicle is None:
        return Response(
            {"detail": "Vehicle not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = PhotoReorderRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    public_ids = serializer.validated_data["ordered_public_ids"]

    # Resolve public_ids to pks (tenant-scoped so cross-tenant
    # attempts fail here as 400 "not on this vehicle").
    photo_qs = VehiclePhoto.objects.filter(
        vehicle=vehicle,
        dealership=dealership,
        public_id__in=public_ids,
    )
    by_public_id = {str(p.public_id): p.pk for p in photo_qs}
    if len(by_public_id) != len(public_ids):
        return Response(
            {
                "detail": (
                    "One or more public_ids do not belong to this vehicle."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    ordered_pks = [by_public_id[str(pid)] for pid in public_ids]

    try:
        reordered = photo_gallery.reorder(
            vehicle,
            dealership=dealership,
            ordered_photo_pks=ordered_pks,
            actor=request.user,
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(
        {
            "stock_number": vehicle.stock_number,
            "photos": [_project_photo(p) for p in reordered],
        }
    )


# ============================================================================
# Endpoints — photo-scoped (mutation by public_id)
# ============================================================================


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_photo_set_primary(request, public_id):
    """POST — set the photo at ``public_id`` as the vehicle's primary."""
    dealership = get_current_dealership(request)
    photo = _lookup_photo_or_404(dealership, public_id)
    if photo is None:
        return Response(
            {"detail": "Photo not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        photo = photo_gallery.set_primary(
            photo, dealership=dealership, actor=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_photo(photo))


@api_view(["DELETE"])
@permission_classes(_M65_PERMS)
def admin_photo_delete(request, public_id):
    """DELETE — safer-direction delete (stamps ``marked_deleted_at``
    + ``deleted_by``; row survives, storage bytes preserved for
    later reaping).
    """
    dealership = get_current_dealership(request)
    photo = _lookup_photo_or_404(dealership, public_id)
    if photo is None:
        return Response(
            {"detail": "Photo not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        photo = photo_gallery.mark_deleted(
            photo, dealership=dealership, actor=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_photo(photo))


@api_view(["POST"])
@permission_classes(_M65_PERMS)
def admin_photo_restore(request, public_id):
    """POST — reverse safer-direction delete."""
    dealership = get_current_dealership(request)
    photo = _lookup_photo_or_404(dealership, public_id)
    if photo is None:
        return Response(
            {"detail": "Photo not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        photo = photo_gallery.restore_deleted(
            photo, dealership=dealership, actor=request.user
        )
    except Exception as exc:
        return _map_service_error(exc)

    return Response(_project_photo(photo))
