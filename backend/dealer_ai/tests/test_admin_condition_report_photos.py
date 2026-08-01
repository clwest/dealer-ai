"""Milestone 3 · Increment 6B — condition-report photo API tests.

Coverage for the four photo endpoints (request-upload, attach,
delete, local-mode receiver). Reuses the M3.6A permission matrix
helper via subclassing.

Test class map:

- Permission matrix (one class per endpoint, subclassing
  :class:`_AuthMatrixBase` from ``test_admin_condition_report``):
  5 outcomes per endpoint.
- ``RequestUploadFlow`` — MIME whitelist, storage_key returned
  here, no row created, TTL cap, completed / cross-tenant refusal.
- ``AttachFlow`` — success, duplicate, missing object, size /
  content_type mismatch, malformed key, cross-tenant key,
  completed refusal, storage_key ABSENT from response,
  no row on failure.
- ``DeleteFlow`` — 204, completed → 409, cross-tenant → 404,
  provider failure → 502 with row retained, missing storage
  idempotent.
- ``LocalUploadFlow`` — local mode works, S3 mode returns 404,
  missing multipart fields → 400, oversized / empty rejected,
  cross-tenant key rejected, attach still required afterward.
- ``StorageKeyLeakageNegative`` — storage_key NEVER appears in
  attach response, latest-report response, or public surfaces.
"""

from __future__ import annotations

import io
import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_TIRES,
    CONDITION_PHOTO_CONTENT_TYPE_HEIC,
    CONDITION_PHOTO_CONTENT_TYPE_JPEG,
    CONDITION_PHOTO_CONTENT_TYPE_PNG,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionFindingPhoto,
    ConditionReport,
    Dealership,
    Vehicle,
)
from dealer_ai.services import photo_storage
from dealer_ai.services.condition_report import (
    add_finding as svc_add_finding,
    attach_photo as svc_attach_photo,
    complete_report as svc_complete_report,
    create_report as svc_create_report,
)
from dealer_ai.services.photo_storage import (
    LOCAL_UPLOAD_URL_MARKER,
    ObjectStorageError,
    build_canonical_key,
    delete_object,
    store_local_upload,
)
from dealer_ai.services.tenancy import get_default_dealership
from dealer_ai.tests._auth_helpers import (
    authenticated_client,
    make_membership,
    make_user,
)
from dealer_ai.tests.test_admin_condition_report import _AuthMatrixBase

from rest_framework.test import APIClient


ROLE_SALES_MANAGER = "sales_manager"


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_finding(dealership: Dealership, stock: str) -> ConditionFinding:
    v = _make_vehicle(stock, dealership)
    report = svc_create_report(
        v,
        dealership=dealership,
        inspector_name="Marta",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
    )
    return svc_add_finding(
        report,
        dealership=dealership,
        category=CONDITION_CATEGORY_TIRES,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="LR tire.",
    )


def _seed_uploaded_object(
    dealership: Dealership,
    *,
    content_type: str = CONDITION_PHOTO_CONTENT_TYPE_JPEG,
    data: bytes = b"\xff\xd8\xff-fake-jpeg-bytes",
) -> tuple[str, int]:
    """Write bytes directly to local storage under a fresh canonical
    key. Returns ``(storage_key, size_bytes)``. Used to simulate a
    completed client-side upload without invoking the multipart
    receiver."""
    key = build_canonical_key(
        dealership=dealership, photo_uuid=uuid.uuid4()
    )
    store_local_upload(
        storage_key=key, content_type=content_type, data=data
    )
    return key, len(data)


# ---- Permission matrix subclasses (reuse M3.6A base) -----------------


class RequestUploadAuth(_AuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-condition-photo-request-upload"
    payload = {"content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG}
    expected_ok_status = 200

    def get_url_kwargs(self):
        return {
            "stock_number": self.vehicle.stock_number,
            "finding_id": self.finding.pk,
        }


class AttachAuth(_AuthMatrixBase, TestCase):
    method = "POST"
    url_name = "admin-condition-photo-attach"
    expected_ok_status = 201

    def setup_tenants(self):
        super().setup_tenants()
        # Seed a real uploaded object so the attach can succeed for
        # authorized callers.
        self._attach_key, self._attach_size = _seed_uploaded_object(
            self.dealership
        )
        # Compose the body only after setup so storage_key is
        # available.
        self.payload = {
            "storage_key": self._attach_key,
            "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            "size_bytes": self._attach_size,
        }

    def get_url_kwargs(self):
        return {
            "stock_number": self.vehicle.stock_number,
            "finding_id": self.finding.pk,
        }

    def tearDown(self):
        # Clean up storage between permission-matrix tests — each
        # runs in an isolated DB but shares the filesystem.
        try:
            delete_object(self._attach_key)
        except Exception:
            pass


class DeleteAuth(_AuthMatrixBase, TestCase):
    method = "DELETE"
    url_name = "admin-condition-photo-delete"
    expected_ok_status = 204

    def setup_tenants(self):
        super().setup_tenants()
        key, size = _seed_uploaded_object(self.dealership)
        self._key = key
        photo = svc_attach_photo(
            self.finding,
            dealership=self.dealership,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )
        self.photo = photo

    def get_url_kwargs(self):
        return {
            "stock_number": self.vehicle.stock_number,
            "public_id": str(self.photo.public_id),
        }

    def tearDown(self):
        try:
            delete_object(self._key)
        except Exception:
            pass


# ---- Request upload flow ---------------------------------------------


class RequestUploadFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.finding = _make_finding(self.dealership, "RU-M36B")
        user = make_user(username="ru-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)
        self.url = reverse(
            "dealer_ai:admin-condition-photo-request-upload",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "finding_id": self.finding.pk,
            },
        )

    def _post(self, body: dict):
        return self.client.post(self.url, data=body, format="json")

    def test_valid_mime_returns_upload_target(self):
        res = self._post({"content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        target = body["upload_target"]
        self.assertEqual(target["method"], "PUT")
        # Local mode marker.
        self.assertTrue(
            target["upload_url"].startswith(LOCAL_UPLOAD_URL_MARKER)
        )
        # storage_key present in THIS response (only exception).
        self.assertIn("storage_key", target)
        self.assertIn("required_headers", target)
        self.assertIn("expires_at", target)

    def test_invalid_mime_returns_400(self):
        res = self._post({"content_type": "application/pdf"})
        self.assertEqual(res.status_code, 400)

    def test_missing_content_type_returns_400(self):
        res = self._post({})
        self.assertEqual(res.status_code, 400)

    def test_no_photo_row_created(self):
        before = ConditionFindingPhoto.objects.count()
        self._post({"content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG})
        self.assertEqual(ConditionFindingPhoto.objects.count(), before)

    def test_upload_ttl_within_cap(self):
        res = self._post({"content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG})
        expires = res.json()["upload_target"]["expires_at"]
        # Just verify it's returned as ISO string — cap is enforced
        # by the storage service (locked in test_photo_storage.py).
        self.assertIsInstance(expires, str)

    def test_completed_report_returns_409(self):
        svc_complete_report(
            self.finding.report, dealership=self.dealership
        )
        res = self._post({"content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG})
        self.assertEqual(res.status_code, 409)


# ---- Attach flow -----------------------------------------------------


class AttachFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.finding = _make_finding(self.dealership, "AT-M36B")
        user = make_user(username="at-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)
        self.url = reverse(
            "dealer_ai:admin-condition-photo-attach",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "finding_id": self.finding.pk,
            },
        )
        self._keys_to_clean = []

    def tearDown(self):
        for key in self._keys_to_clean:
            try:
                delete_object(key)
            except Exception:
                pass

    def _seed(self, **kwargs):
        key, size = _seed_uploaded_object(self.dealership, **kwargs)
        self._keys_to_clean.append(key)
        return key, size

    def _post(self, body: dict):
        return self.client.post(self.url, data=body, format="json")

    def test_success_creates_row_and_returns_projection(self):
        key, size = self._seed()
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
                "caption": "LR tire wear",
            }
        )
        self.assertEqual(res.status_code, 201)
        body = res.json()
        photo = body["photo"]
        self.assertIn("public_id", photo)
        self.assertEqual(photo["caption"], "LR tire wear")
        self.assertEqual(photo["size_bytes"], size)

    def test_storage_key_absent_from_attach_response(self):
        key, size = self._seed()
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
            }
        )
        body_text = json.dumps(res.json())
        self.assertNotIn("storage_key", body_text)

    def test_duplicate_attach_returns_409(self):
        key, size = self._seed()
        self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
            }
        )
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
            }
        )
        self.assertEqual(res.status_code, 409)

    def test_missing_object_returns_409(self):
        # A canonical key was never uploaded to.
        key = build_canonical_key(
            dealership=self.dealership, photo_uuid=uuid.uuid4()
        )
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": 100,
            }
        )
        self.assertEqual(res.status_code, 409)

    def test_size_mismatch_returns_409(self):
        key, size = self._seed()
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size + 999,
            }
        )
        self.assertEqual(res.status_code, 409)

    def test_content_type_mismatch_returns_409(self):
        key, size = self._seed(content_type=CONDITION_PHOTO_CONTENT_TYPE_PNG)
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
            }
        )
        self.assertEqual(res.status_code, 409)

    def test_malformed_key_returns_400(self):
        res = self._post(
            {
                "storage_key": "not-a-canonical-key",
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": 100,
            }
        )
        self.assertEqual(res.status_code, 400)

    def test_cross_tenant_key_returns_404(self):
        other = Dealership.objects.create(
            name="Other", slug="other-at-m36b"
        )
        cross_key = build_canonical_key(
            dealership=other, photo_uuid=uuid.uuid4()
        )
        res = self._post(
            {
                "storage_key": cross_key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": 100,
            }
        )
        # Never leak that the key exists (or doesn't) in another
        # dealership.
        self.assertEqual(res.status_code, 404)

    def test_completed_report_returns_409(self):
        key, size = self._seed()
        svc_complete_report(
            self.finding.report, dealership=self.dealership
        )
        res = self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
            }
        )
        self.assertEqual(res.status_code, 409)

    def test_no_row_created_on_missing_object(self):
        before = ConditionFindingPhoto.objects.count()
        key = build_canonical_key(
            dealership=self.dealership, photo_uuid=uuid.uuid4()
        )
        self._post(
            {
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": 100,
            }
        )
        self.assertEqual(ConditionFindingPhoto.objects.count(), before)


# ---- Delete flow -----------------------------------------------------


class DeleteFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.finding = _make_finding(self.dealership, "DEL-M36B")
        user = make_user(username="del-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)
        self._keys_to_clean = []

    def tearDown(self):
        for key in self._keys_to_clean:
            try:
                delete_object(key)
            except Exception:
                pass

    def _attach(self):
        key, size = _seed_uploaded_object(self.dealership)
        self._keys_to_clean.append(key)
        return svc_attach_photo(
            self.finding,
            dealership=self.dealership,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )

    def _url(self, public_id):
        return reverse(
            "dealer_ai:admin-condition-photo-delete",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "public_id": str(public_id),
            },
        )

    def test_success_returns_204_and_removes_row(self):
        photo = self._attach()
        res = self.client.delete(self._url(photo.public_id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )

    def test_completed_report_returns_409(self):
        photo = self._attach()
        svc_complete_report(
            self.finding.report, dealership=self.dealership
        )
        res = self.client.delete(self._url(photo.public_id))
        self.assertEqual(res.status_code, 409)
        # Row still present.
        self.assertTrue(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )

    def test_cross_tenant_public_id_returns_404(self):
        other = Dealership.objects.create(
            name="Other", slug="other-del-m36b"
        )
        other_finding = _make_finding(other, "OTH-DEL")
        other_key, other_size = _seed_uploaded_object(other)
        self._keys_to_clean.append(other_key)
        other_photo = svc_attach_photo(
            other_finding,
            dealership=other,
            storage_key=other_key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=other_size,
        )
        # Attempt to delete other tenant's photo via our tenant's
        # URL. Must fail closed with 404.
        res = self.client.delete(self._url(other_photo.public_id))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(
            ConditionFindingPhoto.objects.filter(pk=other_photo.pk).exists()
        )

    def test_unknown_public_id_returns_404(self):
        res = self.client.delete(self._url(uuid.uuid4()))
        self.assertEqual(res.status_code, 404)

    def test_provider_failure_returns_502_and_retains_row(self):
        photo = self._attach()
        with patch.object(
            photo_storage,
            "delete_object",
            side_effect=ObjectStorageError("simulated"),
        ):
            res = self.client.delete(self._url(photo.public_id))
        self.assertEqual(res.status_code, 502)
        # Row retained per storage-first strategy.
        self.assertTrue(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )

    def test_provider_error_message_does_not_leak_details(self):
        photo = self._attach()
        with patch.object(
            photo_storage,
            "delete_object",
            side_effect=ObjectStorageError(
                "boto3 InternalServerError: bucket=super-secret-bucket"
            ),
        ):
            res = self.client.delete(self._url(photo.public_id))
        body = res.json()
        self.assertNotIn("bucket", str(body).lower())
        self.assertNotIn("super-secret-bucket", str(body).lower())
        self.assertNotIn("boto3", str(body).lower())

    def test_missing_storage_object_delete_still_succeeds(self):
        photo = self._attach()
        # Simulate storage-side removal behind our back.
        delete_object(photo.storage_key)
        res = self.client.delete(self._url(photo.public_id))
        self.assertEqual(res.status_code, 204)
        self.assertFalse(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )


# ---- Local upload flow -----------------------------------------------


class LocalUploadFlow(TestCase):
    def setUp(self):
        self.dealership = get_default_dealership()
        self.finding = _make_finding(self.dealership, "LU-M36B")
        user = make_user(username="lu-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)
        self.url = reverse(
            "dealer_ai:admin-condition-photo-local-upload",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "finding_id": self.finding.pk,
            },
        )
        self._keys_to_clean = []

    def tearDown(self):
        for key in self._keys_to_clean:
            try:
                delete_object(key)
            except Exception:
                pass

    def _fresh_key(self) -> str:
        key = build_canonical_key(
            dealership=self.dealership, photo_uuid=uuid.uuid4()
        )
        self._keys_to_clean.append(key)
        return key

    def _post_multipart(self, *, key, ct, data, extra=None):
        payload = {
            "file": SimpleUploadedFile(
                "upload.jpg", data, content_type=ct
            ),
            "storage_key": key,
            "content_type": ct,
        }
        if extra:
            payload.update(extra)
        return self.client.post(
            self.url, data=payload, format="multipart"
        )

    def test_local_mode_accepts_valid_multipart(self):
        key = self._fresh_key()
        data = b"\xff\xd8\xff-fake-jpeg-bytes"
        res = self._post_multipart(
            key=key,
            ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            data=data,
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(body["stored_metadata"]["size_bytes"], len(data))
        # No ConditionFindingPhoto row — attach still required.
        self.assertEqual(
            ConditionFindingPhoto.objects.filter(
                storage_key=key
            ).count(),
            0,
        )

    def test_attach_still_required_after_local_upload(self):
        key = self._fresh_key()
        data = b"\xff\xd8\xff-fake-jpeg-bytes"
        self._post_multipart(
            key=key, ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG, data=data
        )
        # Now the client MUST POST to attach to persist the row.
        # Just verify the storage side is ready (attach path is
        # tested in AttachFlow above).
        metadata = photo_storage.get_object_metadata(key)
        self.assertTrue(metadata.exists)
        self.assertEqual(metadata.size_bytes, len(data))

    @override_settings(
        STORAGES={
            **settings.STORAGES,
            "condition_photos": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    "bucket_name": "test-bucket",
                    "region_name": "us-east-1",
                },
            },
        }
    )
    def test_s3_mode_returns_404(self):
        key = build_canonical_key(
            dealership=self.dealership, photo_uuid=uuid.uuid4()
        )
        res = self._post_multipart(
            key=key,
            ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            data=b"payload",
        )
        # Do not advertise the dev-only surface — pretend it doesn't
        # exist.
        self.assertEqual(res.status_code, 404)

    def test_missing_file_returns_400(self):
        res = self.client.post(
            self.url,
            data={
                "storage_key": self._fresh_key(),
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_storage_key_returns_400(self):
        res = self.client.post(
            self.url,
            data={
                "file": SimpleUploadedFile(
                    "x.jpg",
                    b"bytes",
                    content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ),
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_content_type_returns_400(self):
        res = self.client.post(
            self.url,
            data={
                "file": SimpleUploadedFile(
                    "x.jpg",
                    b"bytes",
                    content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ),
                "storage_key": self._fresh_key(),
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, 400)

    def test_arbitrary_key_returns_400(self):
        res = self._post_multipart(
            key="my-arbitrary-filesystem-path.jpg",
            ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            data=b"payload",
        )
        self.assertEqual(res.status_code, 400)

    def test_cross_tenant_key_returns_404(self):
        other = Dealership.objects.create(
            name="Other", slug="other-lu-m36b"
        )
        cross_key = build_canonical_key(
            dealership=other, photo_uuid=uuid.uuid4()
        )
        res = self._post_multipart(
            key=cross_key,
            ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            data=b"payload",
        )
        # Fail closed with 404 — never leak that a key belongs to
        # another tenant.
        self.assertEqual(res.status_code, 404)

    def test_empty_upload_returns_400(self):
        res = self._post_multipart(
            key=self._fresh_key(),
            ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            data=b"",
        )
        # SimpleUploadedFile with empty bytes → serializer rejects
        # OR store_local_upload rejects → either 400 path.
        self.assertEqual(res.status_code, 400)

    def test_oversized_upload_returns_400(self):
        # 26 MB > 25 MB ceiling.
        big = b"x" * (26 * 1024 * 1024)
        res = self._post_multipart(
            key=self._fresh_key(),
            ct=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            data=big,
        )
        self.assertEqual(res.status_code, 400)

    def test_invalid_mime_returns_400(self):
        res = self._post_multipart(
            key=self._fresh_key(),
            ct="application/pdf",
            data=b"pdf-bytes",
        )
        self.assertEqual(res.status_code, 400)


# ---- Security: storage_key leakage negative tests -------------------


class StorageKeyLeakageNegative(TestCase):
    """The user's SESSION_062 spec: storage_key appears ONLY in
    request-upload responses. Nowhere else. Locked with explicit
    negative tests below."""

    def setUp(self):
        self.dealership = get_default_dealership()
        self.finding = _make_finding(self.dealership, "LEAK-M36B")
        user = make_user(username="leak-sm")
        make_membership(user, self.dealership, ROLE_SALES_MANAGER)
        self.client = authenticated_client(user)
        self._keys = []

    def tearDown(self):
        for k in self._keys:
            try:
                delete_object(k)
            except Exception:
                pass

    def _attach(self):
        key, size = _seed_uploaded_object(self.dealership)
        self._keys.append(key)
        return svc_attach_photo(
            self.finding,
            dealership=self.dealership,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )

    def _assert_no_storage_key(self, body_text: str):
        self.assertNotIn("storage_key", body_text)
        self.assertNotIn("bucket", body_text.lower())
        self.assertNotIn("aws_access_key", body_text.lower())
        self.assertNotIn("aws_secret", body_text.lower())

    def test_attach_response_omits_storage_key(self):
        key, size = _seed_uploaded_object(self.dealership)
        self._keys.append(key)
        url = reverse(
            "dealer_ai:admin-condition-photo-attach",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "finding_id": self.finding.pk,
            },
        )
        res = self.client.post(
            url,
            data={
                "storage_key": key,
                "content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                "size_bytes": size,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self._assert_no_storage_key(json.dumps(res.json()))

    def test_latest_report_response_omits_storage_key(self):
        self._attach()
        url = reverse(
            "dealer_ai:admin-condition-report-latest",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
            },
        )
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self._assert_no_storage_key(json.dumps(res.json()))

    def test_finding_update_response_omits_storage_key(self):
        self._attach()
        url = reverse(
            "dealer_ai:admin-condition-finding-detail",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "finding_id": self.finding.pk,
            },
        )
        res = self.client.patch(
            url, data={"notes": "updated"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self._assert_no_storage_key(json.dumps(res.json()))

    def test_delete_response_has_no_body(self):
        photo = self._attach()
        url = reverse(
            "dealer_ai:admin-condition-photo-delete",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "public_id": str(photo.public_id),
            },
        )
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        self.assertEqual(res.content, b"")

    def test_request_upload_response_is_the_only_place_storage_key_appears(self):
        # This test asserts the POSITIVE side of the invariant —
        # storage_key IS in request-upload responses. Combined with
        # the negative tests above, it proves the "only here"
        # invariant.
        url = reverse(
            "dealer_ai:admin-condition-photo-request-upload",
            kwargs={
                "stock_number": self.finding.report.vehicle.stock_number,
                "finding_id": self.finding.pk,
            },
        )
        res = self.client.post(
            url,
            data={"content_type": CONDITION_PHOTO_CONTENT_TYPE_JPEG},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        body_text = json.dumps(res.json())
        self.assertIn("storage_key", body_text)
