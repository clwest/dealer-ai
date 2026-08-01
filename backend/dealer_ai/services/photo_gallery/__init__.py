"""Milestone 6 · Increment 2 (SESSION_083) — vehicle photo gallery service.

The one place vehicle-photo gallery workflow lives. Sits between the
M6.5 admin API (upload / reorder / set-primary / delete gestures) and
the persistence layer (:class:`dealer_ai.models.VehiclePhoto` +
:mod:`services.photo_storage` M6.2 extension).

Six public verbs per ``MILESTONE_6_PLANNING.md`` §1.4 (all invoked with
keyword-only ``dealership=`` for cross-tenant defense-in-depth):

- :func:`upload_photo` — writes bytes via
  :func:`photo_storage.store_vehicle_photo` and persists the
  :class:`VehiclePhoto` metadata row atomically. Fresh
  :class:`uuid.UUID` per call becomes both ``public_id`` and the
  embedded UUID in the canonical storage key.
- :func:`set_primary` — atomically flips the current-primary photo
  on the vehicle to ``is_primary=False`` and sets the target to
  ``True``. ``transaction.atomic()`` + ``select_for_update()``
  enforces "at most one primary per vehicle" without a DB
  uniqueness constraint (which would force the operator's "swap
  primary" gesture into a two-step delete-then-insert dance per
  M6.1 §1.1).
- :func:`reorder` — bulk-updates ``sort_order`` per a caller-
  supplied list of photo PKs. Rejects any PK that doesn't belong
  to the vehicle (belt-and-suspenders cross-tenant guard).
- :func:`mark_deleted` — safer-direction delete per M6 §7 lesson 7.
  Stamps ``marked_deleted_at`` + ``deleted_by``; clears the primary
  flag (a deleted photo cannot remain primary).
- :func:`restore_deleted` — reverse of :func:`mark_deleted`.
- :func:`listing_ready_count` — returns the count of non-deleted
  photos meeting the listing-ready dimension threshold. Drives the
  M6.4 ``_rule_photography_to_listing`` predicate.

**Listing-ready dimension threshold** per SESSION_083 §3 Option A
(user-confirmed): ``width_px >= 1024 AND height_px >= 768``. Sensible
retail-listing minimum; rejects thumbnails / accidental low-res
uploads.

**Listing-ready photo count** per §5.b Option C (user-confirmed at
SESSION_082): fixed at 8 for v1; per-dealer configurability deferred
to a future increment. Exposed here as a module constant for M6.4
consumption.

Domain errors (four distinct classes per M6 §6 lesson 9):

- :class:`CrossTenantPhotoError` — cross-tenant refusal at service
  entry (maps to HTTP 404 at M6.5).
- :class:`PhotoValidationError` — invalid input (bad dimensions,
  reorder PK not on vehicle, set-primary on a deleted photo).
- :class:`PhotoAlreadyDeletedError` — mark-deleted refused because
  already marked.
- :class:`PhotoNotDeletedError` — restore refused because not marked.

Storage-side errors (:class:`photo_storage.ObjectStorageError`,
:class:`photo_storage.InvalidContentTypeError`,
:class:`photo_storage.InvalidStorageKeyError`) propagate up
unchanged — the M6.5 endpoint translates them to HTTP.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from django.db import transaction
from django.utils import timezone

from ...models import (
    Dealership,
    Vehicle,
    VehiclePhoto,
)
from .. import photo_storage


# ---- Constants ------------------------------------------------------------

# Listing-ready dimension threshold per SESSION_083 §3 Option A
# (user-confirmed). Photos smaller than this on either axis do not
# count toward the M6.4 ``_rule_photography_to_listing`` predicate.
# Sensible retail-listing minimum; rejects thumbnails / accidental
# low-res uploads without blocking legitimate landscape photos.
LISTING_READY_MIN_WIDTH_PX = 1024
LISTING_READY_MIN_HEIGHT_PX = 768

# Listing-ready photo count per §5.b Option C (user-confirmed at
# SESSION_082 open). Fixed for v1; per-dealer configurable via
# ``DealerOnboardingProfile.listing_ready_photo_count`` deferred to
# a future increment. Exposed as a module constant so the M6.4 rule
# reads a single source of truth.
LISTING_READY_PHOTO_COUNT = 8


# ---- Domain errors --------------------------------------------------------


class CrossTenantPhotoError(ValueError):
    """Raised when a service call references a photo or vehicle that
    belongs to a different dealership than the requesting tenant.

    Distinct from the persistence-layer
    :meth:`VehiclePhoto.clean` cross-tenant guard: the ``clean()``
    check catches direct ORM writes that construct a row with a
    mismatched ``dealership``; this service-layer check catches
    endpoint-side attempts to operate on a photo whose parent
    vehicle belongs to a different tenant.

    Maps to HTTP 404 at the M6.5 endpoint layer (never 403 — the
    correct posture is "does not exist for this tenant" rather than
    "exists but you can't touch it").
    """


class PhotoValidationError(ValueError):
    """Raised when the caller supplies invalid inputs.

    Covers: non-positive width / height, reorder PK list that
    includes photos not belonging to the vehicle, set-primary on a
    photo whose ``marked_deleted_at`` is populated (a deleted photo
    cannot be the vehicle's primary hero).

    Maps to HTTP 400 at M6.5.
    """


class PhotoAlreadyDeletedError(ValueError):
    """Raised when :func:`mark_deleted` is called on a photo whose
    ``marked_deleted_at`` is already populated.

    Distinct from :class:`PhotoNotDeletedError` so callers can
    distinguish "already in target state" (idempotent no-op) from
    "reverse operation needs the opposite state." Maps to HTTP 409.
    """


class PhotoNotDeletedError(ValueError):
    """Raised when :func:`restore_deleted` is called on a photo whose
    ``marked_deleted_at`` is None.

    Maps to HTTP 409.
    """


# ---- Cross-tenant helpers -------------------------------------------------


def _assert_vehicle_tenant(vehicle: Vehicle, dealership: Dealership) -> None:
    """Refuse if ``vehicle.dealership_id`` mismatches ``dealership.pk``.

    Belt + suspenders across the persistence-layer ``clean()`` guard.
    The persistence guard catches ORM-level construction; this
    service-layer guard catches endpoint-side callers who look up a
    Vehicle by stock_number for the wrong tenant.
    """
    if vehicle.dealership_id != dealership.pk:
        raise CrossTenantPhotoError(
            f"Vehicle #{vehicle.pk} (stock {vehicle.stock_number!r}) "
            f"belongs to dealership_id={vehicle.dealership_id}, not "
            f"the requesting tenant #{dealership.pk} "
            f"({dealership.slug!r})."
        )


def _assert_photo_tenant(photo: VehiclePhoto, dealership: Dealership) -> None:
    """Refuse if ``photo.dealership_id`` mismatches ``dealership.pk``."""
    if photo.dealership_id != dealership.pk:
        raise CrossTenantPhotoError(
            f"VehiclePhoto #{photo.pk} ({photo.public_id}) belongs to "
            f"dealership_id={photo.dealership_id}, not the requesting "
            f"tenant #{dealership.pk} ({dealership.slug!r})."
        )


def _validate_dimensions(width_px: int, height_px: int) -> None:
    """Refuse zero / negative dimensions.

    The persistence layer uses ``PositiveIntegerField`` which rejects
    negative + zero at DB level, but re-validate here so the domain
    error is clean (``PhotoValidationError``, not
    ``django.db.utils.IntegrityError``).
    """
    if not isinstance(width_px, int) or width_px <= 0:
        raise PhotoValidationError(
            f"width_px must be a positive int, got {width_px!r}."
        )
    if not isinstance(height_px, int) or height_px <= 0:
        raise PhotoValidationError(
            f"height_px must be a positive int, got {height_px!r}."
        )


# ---- Public verb: upload_photo -------------------------------------------


def upload_photo(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    data: bytes,
    content_type: str,
    width_px: int,
    height_px: int,
    actor=None,
    sort_order: int = 0,
    caption: str = "",
) -> VehiclePhoto:
    """Persist a new photo for ``vehicle``.

    Writes the bytes to the storage backend via
    :func:`photo_storage.store_vehicle_photo`, then persists the
    :class:`VehiclePhoto` metadata row. Same fresh :func:`uuid.uuid4`
    value seeds both the row's ``public_id`` and the embedded UUID in
    the canonical storage key — the two remain bound even if the
    storage layer is later rekeyed.

    ``is_primary`` is NOT set here — the operator uses
    :func:`set_primary` explicitly. The M6.5 upload UI may bundle
    an upload + set-primary gesture at the endpoint layer for
    convenience.

    ``actor`` is persisted as ``uploaded_by``. Nullable + SET_NULL at
    the model layer.

    Raises:
    - :class:`CrossTenantPhotoError` if ``vehicle.dealership`` !=
      ``dealership``.
    - :class:`PhotoValidationError` if dimensions are non-positive.
    - :class:`photo_storage.InvalidContentTypeError` if content type
      is outside the M6.1 3-value whitelist.
    - :class:`photo_storage.InvalidStorageKeyError` if bytes are
      empty or oversize (via the storage-layer validator).
    - :class:`photo_storage.ObjectStorageError` on backend fault.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    _validate_dimensions(width_px, height_px)

    photo_uuid = uuid.uuid4()
    storage_key, _metadata = photo_storage.store_vehicle_photo(
        dealership=dealership,
        vehicle=vehicle,
        photo_uuid=photo_uuid,
        data=data,
        content_type=content_type,
    )
    photo = VehiclePhoto(
        public_id=photo_uuid,
        vehicle=vehicle,
        dealership=dealership,
        storage_key=storage_key,
        content_type=content_type,
        width_px=width_px,
        height_px=height_px,
        sort_order=sort_order,
        caption=caption,
        uploaded_by=actor,
    )
    photo.full_clean()
    photo.save()
    return photo


# ---- Public verb: set_primary --------------------------------------------


def set_primary(
    photo: VehiclePhoto,
    *,
    dealership: Dealership,
    actor=None,  # noqa: ARG001 — reserved for future audit-log wiring
) -> VehiclePhoto:
    """Atomically make ``photo`` the primary hero for its vehicle.

    Inside a single :func:`transaction.atomic` block:

    1. ``select_for_update()`` on the vehicle's current primaries
       (there should be at most one — enforced here, not at DB
       layer, per M6.1 §1.1 rationale).
    2. Clear ``is_primary`` on every other primary row.
    3. Set ``is_primary=True`` on the target photo.

    The atomic swap means an in-flight concurrent
    ``set_primary`` call blocks on the row lock; only one primary
    stays flipped when both transactions commit. Mirrors the M4.2
    :func:`WorkOrder` concurrency posture.

    Raises:
    - :class:`CrossTenantPhotoError` if photo belongs to a
      different tenant.
    - :class:`PhotoValidationError` if ``photo.marked_deleted_at``
      is set — a deleted photo cannot be the primary hero.
    """
    _assert_photo_tenant(photo, dealership)
    if photo.marked_deleted_at is not None:
        raise PhotoValidationError(
            f"Cannot set primary on VehiclePhoto #{photo.pk} — the "
            "photo is marked deleted. Restore it first "
            "(restore_deleted) or upload a fresh photo."
        )
    with transaction.atomic():
        # Lock current-primary rows on this vehicle. Excludes the
        # target photo itself in case the caller re-sets an already-
        # primary photo (idempotent no-op that still burns the lock).
        (
            VehiclePhoto.objects.select_for_update()
            .filter(vehicle=photo.vehicle_id, is_primary=True)
            .exclude(pk=photo.pk)
            .update(is_primary=False, updated_at=timezone.now())
        )
        if not photo.is_primary:
            photo.is_primary = True
            photo.save(update_fields=["is_primary", "updated_at"])
    return photo


# ---- Public verb: reorder ------------------------------------------------


def reorder(
    vehicle: Vehicle,
    *,
    dealership: Dealership,
    ordered_photo_pks: Sequence[int],
    actor=None,  # noqa: ARG001 — reserved for future audit-log wiring
) -> list[VehiclePhoto]:
    """Bulk-update ``sort_order`` on ``vehicle``'s photos per the
    caller-supplied ordering.

    ``ordered_photo_pks[0]`` gets ``sort_order=0``,
    ``ordered_photo_pks[1]`` gets 1, and so on. Photos not in the
    list are untouched — the caller is responsible for supplying the
    complete gallery ordering if it wants a full renumber.

    Rejects any PK that doesn't belong to the vehicle
    (:class:`PhotoValidationError`) — belt-and-suspenders defense
    against cross-tenant photo IDs crossing an endpoint boundary.
    Also rejects duplicate PKs (a caller bug that would produce a
    silent last-write-wins).

    Wrapped in :func:`transaction.atomic` so a partial update fails
    the whole reorder.

    Returns the reordered :class:`VehiclePhoto` rows in the
    caller-supplied order.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    if len(set(ordered_photo_pks)) != len(ordered_photo_pks):
        raise PhotoValidationError(
            "ordered_photo_pks contains duplicate PKs. Every PK "
            "must appear at most once — reorder is not a deduplicator."
        )
    photos = list(
        VehiclePhoto.objects.filter(
            vehicle=vehicle, pk__in=ordered_photo_pks
        )
    )
    if len(photos) != len(ordered_photo_pks):
        found_pks = {p.pk for p in photos}
        missing = [pk for pk in ordered_photo_pks if pk not in found_pks]
        raise PhotoValidationError(
            f"ordered_photo_pks contains PKs that do not belong to "
            f"vehicle #{vehicle.pk}: {missing}."
        )
    by_pk = {p.pk: p for p in photos}
    now = timezone.now()
    with transaction.atomic():
        for index, pk in enumerate(ordered_photo_pks):
            photo = by_pk[pk]
            photo.sort_order = index
            photo.updated_at = now
            photo.save(update_fields=["sort_order", "updated_at"])
    return [by_pk[pk] for pk in ordered_photo_pks]


# ---- Public verb: mark_deleted -------------------------------------------


def mark_deleted(
    photo: VehiclePhoto,
    *,
    dealership: Dealership,
    actor=None,
) -> VehiclePhoto:
    """Safer-direction delete: stamp ``marked_deleted_at`` +
    ``deleted_by`` rather than removing the row.

    Also clears ``is_primary`` — a deleted photo cannot be the
    vehicle's primary hero. Any customer-facing consumer that
    dereferences a vehicle's primary photo must handle the "no
    primary" case anyway (a new vehicle before any photo lands
    hits the same state).

    Storage bytes are NOT physically removed. A future
    physical-delete reaper (M6.2+ or later) processes tombstoned
    rows on operator-controlled cadence.

    Raises:
    - :class:`CrossTenantPhotoError`.
    - :class:`PhotoAlreadyDeletedError` if the photo is already
      marked deleted (distinct from a no-op so callers can
      distinguish idempotent from meaningful).
    """
    _assert_photo_tenant(photo, dealership)
    if photo.marked_deleted_at is not None:
        raise PhotoAlreadyDeletedError(
            f"VehiclePhoto #{photo.pk} ({photo.public_id}) is already "
            f"marked deleted at {photo.marked_deleted_at.isoformat()}. "
            "Restore it (restore_deleted) before re-deleting."
        )
    photo.marked_deleted_at = timezone.now()
    photo.deleted_by = actor
    photo.is_primary = False
    photo.save(
        update_fields=[
            "marked_deleted_at",
            "deleted_by",
            "is_primary",
            "updated_at",
        ]
    )
    return photo


# ---- Public verb: restore_deleted ----------------------------------------


def restore_deleted(
    photo: VehiclePhoto,
    *,
    dealership: Dealership,
    actor=None,  # noqa: ARG001 — reserved for future audit-log wiring
) -> VehiclePhoto:
    """Reverse of :func:`mark_deleted`. Clears ``marked_deleted_at``
    and ``deleted_by``. Does NOT restore the ``is_primary`` flag —
    the operator must explicitly re-elect the photo as primary via
    :func:`set_primary` if desired.

    Raises:
    - :class:`CrossTenantPhotoError`.
    - :class:`PhotoNotDeletedError` if the photo is not currently
      marked deleted.
    """
    _assert_photo_tenant(photo, dealership)
    if photo.marked_deleted_at is None:
        raise PhotoNotDeletedError(
            f"VehiclePhoto #{photo.pk} ({photo.public_id}) is not "
            "currently marked deleted. Nothing to restore."
        )
    photo.marked_deleted_at = None
    photo.deleted_by = None
    photo.save(
        update_fields=[
            "marked_deleted_at",
            "deleted_by",
            "updated_at",
        ]
    )
    return photo


# ---- Public verb: listing_ready_count ------------------------------------


def listing_ready_count(vehicle: Vehicle, *, dealership: Dealership) -> int:
    """Return the count of non-deleted photos on ``vehicle`` meeting
    the listing-ready dimension threshold
    (:data:`LISTING_READY_MIN_WIDTH_PX` +
    :data:`LISTING_READY_MIN_HEIGHT_PX`).

    Drives the M6.4 ``_rule_photography_to_listing`` predicate: the
    rule fires when this count is ≥ :data:`LISTING_READY_PHOTO_COUNT`.

    Pure read; no side effects. Cross-tenant refused via
    :func:`_assert_vehicle_tenant`.
    """
    _assert_vehicle_tenant(vehicle, dealership)
    return VehiclePhoto.objects.filter(
        vehicle=vehicle,
        marked_deleted_at__isnull=True,
        width_px__gte=LISTING_READY_MIN_WIDTH_PX,
        height_px__gte=LISTING_READY_MIN_HEIGHT_PX,
    ).count()


# ---- Public re-exports ---------------------------------------------------


__all__ = [
    "CrossTenantPhotoError",
    "LISTING_READY_MIN_HEIGHT_PX",
    "LISTING_READY_MIN_WIDTH_PX",
    "LISTING_READY_PHOTO_COUNT",
    "PhotoAlreadyDeletedError",
    "PhotoNotDeletedError",
    "PhotoValidationError",
    "listing_ready_count",
    "mark_deleted",
    "reorder",
    "restore_deleted",
    "set_primary",
    "upload_photo",
]
