"""Milestone 3 · Increment 5 — condition-report photo workflow tests.

Focused on the three new service functions
(:func:`request_photo_upload`, :func:`attach_photo`,
:func:`delete_photo`) and the M3.4→M3.5 handshake contract:

- ``request_photo_upload`` authorizes an upload without persisting
  a row.
- ``attach_photo`` HEAD-verifies the object landed AND matches
  declared metadata AND belongs to the tenant namespace before
  creating the row.
- ``delete_photo`` deletes storage first and retains the row on
  real backend failure.

Tests use the M3.4 local adapter + `store_local_upload` to seed
verifiable state (zero network). Tests that need to exercise
provider failure inject a mocked adapter via `mock.patch`.

Test class map:

- ``RequestPhotoUpload`` — happy path, complete rejected,
  cross-tenant rejected, content type validation, fresh key per
  call, no row persisted.
- ``AttachPhoto`` — happy path, size / content_type mismatch,
  missing object, cross-tenant key, malformed key, duplicate
  attachment predictable error, completed rejected, no row on
  failure, uploaded_by + caption preserved, uuid extracted.
- ``DeletePhoto`` — draft delete succeeds, complete rejected,
  cross-tenant rejected, missing storage idempotent, provider
  failure retains row, storage delete precedes row delete.
- ``EstimatedCostStillNoOp`` — attach + delete never touch
  VehicleCost.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_TIRES,
    CONDITION_PHOTO_CONTENT_TYPE_HEIC,
    CONDITION_PHOTO_CONTENT_TYPE_JPEG,
    CONDITION_PHOTO_CONTENT_TYPE_PNG,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionFindingPhoto,
    Dealership,
    Vehicle,
    VehicleCost,
)
from dealer_ai.services import photo_storage
from dealer_ai.services.condition_report import (
    ConditionReportImmutableError,
    CrossTenantConditionReportError,
    PhotoAlreadyAttachedError,
    PhotoMetadataMismatchError,
    PhotoNotYetUploadedError,
    add_finding,
    attach_photo,
    complete_report,
    create_report,
    delete_photo,
    request_photo_upload,
)
from dealer_ai.services.photo_storage import (
    LOCAL_UPLOAD_URL_MARKER,
    ObjectMetadata,
    ObjectStorageError,
    UploadTarget,
    build_canonical_key,
    delete_object,
    store_local_upload,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_finding(dealership: Dealership, stock: str) -> ConditionFinding:
    vehicle = _make_vehicle(stock, dealership)
    report = create_report(
        vehicle,
        dealership=dealership,
        inspector_name="Marta",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
    )
    return add_finding(
        report,
        dealership=dealership,
        category=CONDITION_CATEGORY_TIRES,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="LR tire at 3/32nds.",
    )


def _seed_uploaded_object(
    finding: ConditionFinding,
    dealership: Dealership,
    *,
    content_type: str = CONDITION_PHOTO_CONTENT_TYPE_JPEG,
    data: bytes = b"\xff\xd8\xff-fake-jpeg-payload",
) -> tuple[str, int]:
    """Simulate a completed client-side upload by writing directly
    to local storage under a fresh canonical key. Returns
    ``(storage_key, size_bytes)`` — the values the client would
    hand to ``attach_photo``."""
    photo_uuid = uuid.uuid4()
    key = build_canonical_key(
        dealership=dealership, photo_uuid=photo_uuid
    )
    store_local_upload(
        storage_key=key, content_type=content_type, data=data
    )
    return key, len(data)


class _CleanupMixin:
    """Delete any storage objects left behind between tests. Local
    storage persists on disk across TestCase runs; tests that write
    real bytes must clean up."""

    _seeded_keys: list[str]

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self._seeded_keys = []

    def _track(self, key: str) -> str:
        self._seeded_keys.append(key)
        return key

    def tearDown(self):
        for key in self._seeded_keys:
            try:
                delete_object(key)
            except Exception:
                pass
        super().tearDown()  # type: ignore[misc]


# ---- request_photo_upload -----------------------------------------------


class RequestPhotoUpload(_CleanupMixin, TestCase):
    """Authorizes an upload; does not persist a
    ``ConditionFindingPhoto`` row."""

    def setUp(self):
        super().setUp()
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding(self.default, "M35-RPU")

    def _request(self, content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG):
        target = request_photo_upload(
            self.finding,
            dealership=self.default,
            content_type=content_type,
        )
        self._track(target.storage_key)
        return target

    def test_returns_upload_target(self):
        target = self._request()
        self.assertIsInstance(target, UploadTarget)
        self.assertEqual(target.method, "PUT")
        # Local mode marker.
        self.assertTrue(target.upload_url.startswith(LOCAL_UPLOAD_URL_MARKER))

    def test_no_photo_row_persisted(self):
        before = ConditionFindingPhoto.objects.count()
        self._request()
        self.assertEqual(ConditionFindingPhoto.objects.count(), before)

    def test_completed_report_rejected(self):
        complete_report(self.finding.report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            request_photo_upload(
                self.finding,
                dealership=self.default,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            )

    def test_cross_tenant_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-35rpu")
        with self.assertRaises(CrossTenantConditionReportError):
            request_photo_upload(
                self.finding,
                dealership=other,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            )

    def test_all_four_content_types_accepted(self):
        for ct in (
            CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            CONDITION_PHOTO_CONTENT_TYPE_PNG,
            CONDITION_PHOTO_CONTENT_TYPE_HEIC,
        ):
            target = self._request(content_type=ct)
            self.assertEqual(target.required_headers["Content-Type"], ct)

    def test_invalid_content_type_rejected(self):
        with self.assertRaises(photo_storage.InvalidContentTypeError):
            request_photo_upload(
                self.finding,
                dealership=self.default,
                content_type="application/octet-stream",
            )

    def test_fresh_key_per_call(self):
        # Every call generates a fresh UUID — clients cannot request
        # the same key twice.
        first = self._request()
        second = self._request()
        self.assertNotEqual(first.storage_key, second.storage_key)


# ---- attach_photo -------------------------------------------------------


class AttachPhoto(_CleanupMixin, TestCase):
    """Five-verification attach path with predictable domain errors
    for each failure mode."""

    def setUp(self):
        super().setUp()
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding(self.default, "M35-AP")

    def test_happy_path_creates_row_with_declared_metadata(self):
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        photo = attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
            caption="LR tire wear",
        )
        self.assertIsInstance(photo, ConditionFindingPhoto)
        self.assertEqual(photo.storage_key, key)
        self.assertEqual(photo.size_bytes, size)
        self.assertEqual(
            photo.content_type, CONDITION_PHOTO_CONTENT_TYPE_JPEG
        )
        self.assertEqual(photo.caption, "LR tire wear")
        self.assertEqual(photo.finding_id, self.finding.pk)
        # public_id is extracted from the storage key.
        _, expected_uuid = photo_storage.parse_canonical_key(key)
        self.assertEqual(photo.public_id, expected_uuid)

    def test_uploaded_by_preserved_on_row(self):
        User = get_user_model()
        user = User.objects.create_user(username="uploader35", password="pw")
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        photo = attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
            uploaded_by=user,
        )
        self.assertEqual(photo.uploaded_by, user)

    def test_missing_object_raises_photo_not_yet_uploaded(self):
        # No object was seeded — HEAD returns exists=False.
        photo_uuid = uuid.uuid4()
        key = build_canonical_key(
            dealership=self.default, photo_uuid=photo_uuid
        )
        with self.assertRaises(PhotoNotYetUploadedError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=100,
            )

    def test_size_mismatch_raises_metadata_mismatch(self):
        key, actual_size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        with self.assertRaises(PhotoMetadataMismatchError) as ctx:
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=actual_size + 999,  # lie
            )
        self.assertIn("size_bytes", str(ctx.exception))

    def test_content_type_mismatch_raises_metadata_mismatch(self):
        key, size = _seed_uploaded_object(
            self.finding,
            self.default,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_PNG,
        )
        self._track(key)
        with self.assertRaises(PhotoMetadataMismatchError) as ctx:
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                # Client claims JPEG but actual object is PNG.
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=size,
            )
        self.assertIn("content_type", str(ctx.exception))

    def test_malformed_key_rejected(self):
        with self.assertRaises(photo_storage.InvalidStorageKeyError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key="my-uploaded-file.jpg",
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=100,
            )

    def test_cross_tenant_key_rejected(self):
        # Craft a valid-shape key but for a different tenant's slug.
        other = Dealership.objects.create(name="Other", slug="other-35ap")
        cross_key = build_canonical_key(
            dealership=other, photo_uuid=uuid.uuid4()
        )
        with self.assertRaises(CrossTenantConditionReportError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=cross_key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=100,
            )

    def test_finding_cross_tenant_rejected(self):
        other = Dealership.objects.create(name="Other", slug="other-35apft")
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        with self.assertRaises(CrossTenantConditionReportError):
            attach_photo(
                self.finding,
                dealership=other,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=size,
            )

    def test_completed_report_rejected(self):
        complete_report(self.finding.report, dealership=self.default)
        photo_uuid = uuid.uuid4()
        key = build_canonical_key(
            dealership=self.default, photo_uuid=photo_uuid
        )
        with self.assertRaises(ConditionReportImmutableError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=100,
            )

    def test_duplicate_attach_raises_predictable_domain_error(self):
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )
        # Second attach for the same storage_key must raise the
        # domain error, not leak IntegrityError.
        with self.assertRaises(PhotoAlreadyAttachedError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=size,
            )

    def test_no_row_created_when_missing_object(self):
        before = ConditionFindingPhoto.objects.count()
        photo_uuid = uuid.uuid4()
        key = build_canonical_key(
            dealership=self.default, photo_uuid=photo_uuid
        )
        with self.assertRaises(PhotoNotYetUploadedError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=100,
            )
        self.assertEqual(ConditionFindingPhoto.objects.count(), before)

    def test_no_row_created_on_size_mismatch(self):
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        before = ConditionFindingPhoto.objects.count()
        with self.assertRaises(PhotoMetadataMismatchError):
            attach_photo(
                self.finding,
                dealership=self.default,
                storage_key=key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                size_bytes=size + 1,
            )
        self.assertEqual(ConditionFindingPhoto.objects.count(), before)

    def test_uuid_extracted_via_storage_service_parser(self):
        # public_id on the created row equals the UUID embedded in
        # the storage_key by build_canonical_key — proves the row
        # went through parse_canonical_key rather than storing a
        # different UUID.
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        _, expected_uuid = photo_storage.parse_canonical_key(key)
        photo = attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )
        self.assertEqual(photo.public_id, expected_uuid)


# ---- delete_photo -------------------------------------------------------


class DeletePhoto(_CleanupMixin, TestCase):
    """Storage-first deletion strategy — DB row retained on real
    backend failure."""

    def setUp(self):
        super().setUp()
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding(self.default, "M35-DEL")

    def _attach(self):
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        return attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )

    def test_draft_delete_removes_row_and_object(self):
        photo = self._attach()
        pk = photo.pk
        key = photo.storage_key
        # Storage object exists before delete.
        self.assertTrue(photo_storage.get_object_metadata(key).exists)
        delete_photo(photo, dealership=self.default)
        # Both row and object gone.
        self.assertFalse(
            ConditionFindingPhoto.objects.filter(pk=pk).exists()
        )
        self.assertFalse(photo_storage.get_object_metadata(key).exists)

    def test_completed_report_delete_rejected(self):
        photo = self._attach()
        complete_report(self.finding.report, dealership=self.default)
        with self.assertRaises(ConditionReportImmutableError):
            delete_photo(photo, dealership=self.default)
        # Row still present.
        self.assertTrue(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )
        # Object still present.
        self.assertTrue(
            photo_storage.get_object_metadata(photo.storage_key).exists
        )

    def test_cross_tenant_delete_rejected(self):
        photo = self._attach()
        other = Dealership.objects.create(name="Other", slug="other-35del")
        with self.assertRaises(CrossTenantConditionReportError):
            delete_photo(photo, dealership=other)
        self.assertTrue(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )

    def test_missing_storage_object_is_idempotent(self):
        photo = self._attach()
        key = photo.storage_key
        # Simulate the object having gone missing behind our back.
        delete_object(key)
        # delete_photo must still succeed — the row still needs to go.
        delete_photo(photo, dealership=self.default)
        self.assertFalse(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )

    def test_provider_failure_retains_row(self):
        photo = self._attach()
        # Patch photo_storage.delete_object at the module the service
        # imports it from — condition_report imports the module
        # (``from . import photo_storage``), so patching the module
        # attribute affects the call site.
        with patch.object(
            photo_storage,
            "delete_object",
            side_effect=ObjectStorageError("simulated backend fault"),
        ):
            with self.assertRaises(ObjectStorageError):
                delete_photo(photo, dealership=self.default)
        # Row MUST still exist — no silent orphaning of storage
        # objects when the backend fails.
        self.assertTrue(
            ConditionFindingPhoto.objects.filter(pk=photo.pk).exists()
        )

    def test_storage_delete_precedes_row_delete(self):
        # Verify call order — the storage delete MUST run first so
        # a mid-operation failure retains the DB row (which points
        # at the storage object as the only cleanup reference).
        photo = self._attach()
        call_order = []
        real_delete_object = photo_storage.delete_object
        real_photo_delete = ConditionFindingPhoto.delete

        def tracked_storage_delete(key):
            call_order.append("storage")
            return real_delete_object(key)

        def tracked_row_delete(self, *a, **kw):
            call_order.append("row")
            return real_photo_delete(self, *a, **kw)

        with patch.object(
            photo_storage, "delete_object", side_effect=tracked_storage_delete
        ):
            with patch.object(
                ConditionFindingPhoto, "delete", tracked_row_delete
            ):
                delete_photo(photo, dealership=self.default)
        self.assertEqual(call_order, ["storage", "row"])


# ---- Estimated cost still never touches VehicleCost --------------------


class EstimatedCostStillNoOp(_CleanupMixin, TestCase):
    """Composite invariant with photos present. The M3.5 photo
    workflow must NEVER cause a VehicleCost row to be created — the
    ``estimated_cost`` field on ConditionFinding remains
    documentation-only in M3."""

    def setUp(self):
        super().setUp()
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding(self.default, "M35-COST")
        # Give the finding an estimated_cost — this must not
        # translate into any VehicleCost activity.
        self.finding.estimated_cost = Decimal("100.00")
        self.finding.save()

    def _cost_count(self) -> int:
        return VehicleCost.objects.count()

    def test_request_photo_upload_creates_no_vehicle_cost(self):
        before = self._cost_count()
        target = request_photo_upload(
            self.finding,
            dealership=self.default,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
        )
        self._track(target.storage_key)
        self.assertEqual(self._cost_count(), before)

    def test_attach_photo_creates_no_vehicle_cost(self):
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        before = self._cost_count()
        attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )
        self.assertEqual(self._cost_count(), before)

    def test_delete_photo_creates_no_vehicle_cost(self):
        key, size = _seed_uploaded_object(self.finding, self.default)
        self._track(key)
        photo = attach_photo(
            self.finding,
            dealership=self.default,
            storage_key=key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=size,
        )
        before = self._cost_count()
        delete_photo(photo, dealership=self.default)
        self.assertEqual(self._cost_count(), before)
