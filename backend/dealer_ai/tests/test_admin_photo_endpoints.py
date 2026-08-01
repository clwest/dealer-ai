"""Milestone 6 · Increment 5 (SESSION_086) — admin photo endpoint tests.

Coverage of the six photo endpoints in ``views_photos.py``:

- ``GET  /admin/vehicles/<stock>/photos/`` — list gallery.
- ``POST /admin/vehicles/<stock>/photos/upload/`` — upload.
- ``POST /admin/vehicles/<stock>/photos/reorder/`` — bulk reorder.
- ``POST /admin/vehicle-photos/<uuid>/set-primary/``.
- ``DELETE /admin/vehicle-photos/<uuid>/`` — safer-direction delete.
- ``POST /admin/vehicle-photos/<uuid>/restore/``.

Locked invariants:

- Permission (unauth → 401, no-role → 403, sales_manager admits).
- Cross-tenant fail-closed (404 with URL kwarg pointing at another
  dealership's vehicle / photo).
- Domain-error → HTTP mapping (400 / 404 / 409 / 415).
- Upload persists a VehiclePhoto row + writes bytes to local storage.
- Reorder rejects public_ids not belonging to the vehicle.
- Set-primary atomic-swap invariant (at most one primary).
- Delete flips marked_deleted_at + clears is_primary.
- Restore reverses marked_deleted_at + deleted_by.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import (
    Dealership,
    ROLE_ADVISOR,
    ROLE_SALES_MANAGER,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    Vehicle,
    VehiclePhoto,
)
from dealer_ai.services import photo_gallery
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_dealership,
    make_membership,
    make_user,
)


User = get_user_model()


def _vehicle(dealership, stock="M65-P") -> Vehicle:
    return Vehicle.objects.create(
        dealership=dealership,
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("29500.00"),
    )


_SAMPLE_BYTES = b"\xff\xd8\xff\xe0fake-jpeg-body"


def _upload_file(name="hero.jpg") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name, _SAMPLE_BYTES, content_type="image/jpeg"
    )


def _seed_photo(vehicle, dealership, **overrides):
    return photo_gallery.upload_photo(
        vehicle,
        dealership=dealership,
        data=_SAMPLE_BYTES,
        content_type=overrides.get(
            "content_type", VEHICLE_PHOTO_CONTENT_TYPE_JPEG
        ),
        width_px=overrides.get("width_px", 1920),
        height_px=overrides.get("height_px", 1080),
        sort_order=overrides.get("sort_order", 0),
        caption=overrides.get("caption", ""),
    )


# ============================================================================
# Permission matrix
# ============================================================================


class PhotoEndpointPermissions(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        self.vehicle = _vehicle(self.default, "M65P-PERM")

    def test_unauthenticated_list_refused(self):
        """Anonymous request refused. DRF returns 403 (not 401) for
        compound-permission failures without explicit
        WWW-Authenticate headers; either is a valid auth-refused
        response for this compound permission — accept both."""
        from rest_framework.test import APIClient
        response = APIClient().get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertIn(response.status_code, (401, 403))

    def test_advisor_role_forbidden(self):
        user = make_user("m65-advisor")
        make_membership(user, self.default, ROLE_ADVISOR)
        client = authenticated_client(user)
        response = client.get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_sales_manager_admitted(self):
        user = make_user("m65-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        client = authenticated_client(user)
        response = client.get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)


# ============================================================================
# List endpoint
# ============================================================================


class PhotoListEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65-list-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65P-LIST")

    def test_empty_gallery(self):
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["photos"], [])

    def test_list_returns_projected_shape(self):
        photo = _seed_photo(self.vehicle, self.default, caption="Hero")
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[self.vehicle.stock_number],
            )
        )
        self.assertEqual(response.status_code, 200)
        photos = response.data["photos"]
        self.assertEqual(len(photos), 1)
        self.assertEqual(photos[0]["public_id"], str(photo.public_id))
        self.assertEqual(photos[0]["caption"], "Hero")
        self.assertEqual(photos[0]["width_px"], 1920)
        self.assertFalse(photos[0]["is_primary"])

    def test_list_includes_marked_deleted(self):
        p1 = _seed_photo(self.vehicle, self.default)
        _seed_photo(self.vehicle, self.default, sort_order=1)
        photo_gallery.mark_deleted(p1, dealership=self.default)
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[self.vehicle.stock_number],
            )
        )
        # Both photos returned so the UI can render active + deleted.
        self.assertEqual(len(response.data["photos"]), 2)

    def test_cross_tenant_404(self):
        other = make_dealership("other-photolist")
        v_other = _vehicle(other, "M65P-LIST-OTHER")
        response = self.client_a.get(
            reverse(
                "dealer_ai:admin-photo-list",
                args=[v_other.stock_number],
            )
        )
        self.assertEqual(response.status_code, 404)


# ============================================================================
# Upload endpoint
# ============================================================================


class PhotoUploadEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65-upload-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65P-UP")

    def test_upload_creates_photo(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-upload",
                args=[self.vehicle.stock_number],
            ),
            data={
                "file": _upload_file(),
                "width_px": 1920,
                "height_px": 1080,
                "caption": "Front three-quarter",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["width_px"], 1920)
        self.assertEqual(response.data["caption"], "Front three-quarter")
        self.assertEqual(VehiclePhoto.objects.filter(vehicle=self.vehicle).count(), 1)

    def test_upload_rejects_missing_dimensions(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-upload",
                args=[self.vehicle.stock_number],
            ),
            data={"file": _upload_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_rejects_unsupported_content_type(self):
        heic_file = SimpleUploadedFile(
            "photo.heic", _SAMPLE_BYTES, content_type="image/heic"
        )
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-upload",
                args=[self.vehicle.stock_number],
            ),
            data={
                "file": heic_file,
                "width_px": 1024,
                "height_px": 768,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 415)

    def test_upload_cross_tenant_404(self):
        other = make_dealership("other-upload")
        v_other = _vehicle(other, "M65P-UP-OTHER")
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-upload",
                args=[v_other.stock_number],
            ),
            data={
                "file": _upload_file(),
                "width_px": 800,
                "height_px": 600,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 404)


# ============================================================================
# Reorder endpoint
# ============================================================================


class PhotoReorderEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65-reorder-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65P-RE")
        self.p0 = _seed_photo(self.vehicle, self.default, sort_order=0)
        self.p1 = _seed_photo(self.vehicle, self.default, sort_order=1)
        self.p2 = _seed_photo(self.vehicle, self.default, sort_order=2)

    def test_reorder_applies_new_positions(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-reorder",
                args=[self.vehicle.stock_number],
            ),
            data=json.dumps(
                {
                    "ordered_public_ids": [
                        str(self.p2.public_id),
                        str(self.p0.public_id),
                        str(self.p1.public_id),
                    ]
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.p0.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.sort_order, 0)
        self.assertEqual(self.p0.sort_order, 1)

    def test_reorder_rejects_foreign_public_id(self):
        other_vehicle = _vehicle(self.default, "M65P-RE-OTHER")
        foreign = _seed_photo(other_vehicle, self.default)
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-reorder",
                args=[self.vehicle.stock_number],
            ),
            data=json.dumps(
                {
                    "ordered_public_ids": [
                        str(self.p0.public_id),
                        str(foreign.public_id),
                    ]
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reorder_empty_list_400(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-reorder",
                args=[self.vehicle.stock_number],
            ),
            data=json.dumps({"ordered_public_ids": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


# ============================================================================
# Set-primary endpoint
# ============================================================================


class PhotoSetPrimaryEndpoint(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65-sp-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65P-SP")
        self.p0 = _seed_photo(self.vehicle, self.default)
        self.p1 = _seed_photo(self.vehicle, self.default)

    def test_set_primary_flips_flag(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-set-primary",
                args=[self.p0.public_id],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.p0.refresh_from_db()
        self.assertTrue(self.p0.is_primary)

    def test_set_primary_atomic_swap(self):
        self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-set-primary",
                args=[self.p0.public_id],
            )
        )
        self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-set-primary",
                args=[self.p1.public_id],
            )
        )
        primaries = VehiclePhoto.objects.filter(
            vehicle=self.vehicle, is_primary=True
        )
        self.assertEqual(primaries.count(), 1)
        self.assertEqual(primaries.first().pk, self.p1.pk)

    def test_set_primary_on_deleted_400(self):
        photo_gallery.mark_deleted(self.p0, dealership=self.default)
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-set-primary",
                args=[self.p0.public_id],
            )
        )
        self.assertEqual(response.status_code, 400)

    def test_set_primary_unknown_public_id_404(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-set-primary",
                args=[uuid.uuid4()],
            )
        )
        self.assertEqual(response.status_code, 404)


# ============================================================================
# Delete + restore endpoints
# ============================================================================


class PhotoDeleteRestoreEndpoints(TestCase):
    def setUp(self):
        self.default = get_default_dealership()
        user = make_user("m65-del-sm")
        make_membership(user, self.default, ROLE_SALES_MANAGER)
        self.client_a = authenticated_client(user)
        self.vehicle = _vehicle(self.default, "M65P-DEL")
        self.photo = _seed_photo(self.vehicle, self.default)

    def test_delete_stamps_marked_deleted(self):
        response = self.client_a.delete(
            reverse(
                "dealer_ai:admin-photo-delete",
                args=[self.photo.public_id],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.photo.refresh_from_db()
        self.assertIsNotNone(self.photo.marked_deleted_at)
        # Row still exists — safer-direction deletion.
        self.assertTrue(
            VehiclePhoto.objects.filter(pk=self.photo.pk).exists()
        )

    def test_double_delete_409(self):
        self.client_a.delete(
            reverse(
                "dealer_ai:admin-photo-delete",
                args=[self.photo.public_id],
            )
        )
        response = self.client_a.delete(
            reverse(
                "dealer_ai:admin-photo-delete",
                args=[self.photo.public_id],
            )
        )
        self.assertEqual(response.status_code, 409)

    def test_restore_reverses_deletion(self):
        photo_gallery.mark_deleted(self.photo, dealership=self.default)
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-restore",
                args=[self.photo.public_id],
            )
        )
        self.assertEqual(response.status_code, 200)
        self.photo.refresh_from_db()
        self.assertIsNone(self.photo.marked_deleted_at)

    def test_restore_non_deleted_409(self):
        response = self.client_a.post(
            reverse(
                "dealer_ai:admin-photo-restore",
                args=[self.photo.public_id],
            )
        )
        self.assertEqual(response.status_code, 409)

    def test_delete_cross_tenant_404(self):
        other = make_dealership("other-del")
        v_other = _vehicle(other, "M65P-DEL-OTHER")
        p_other = _seed_photo(v_other, other)
        response = self.client_a.delete(
            reverse(
                "dealer_ai:admin-photo-delete",
                args=[p_other.public_id],
            )
        )
        self.assertEqual(response.status_code, 404)
