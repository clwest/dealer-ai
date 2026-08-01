"""Milestone 6 · Increment 2 (SESSION_083) — vehicle-photo storage tests.

Covers the M6.2 additions to :mod:`services.photo_storage`:

- :func:`build_canonical_vehicle_photo_key` — canonical key shape,
  slug + stock-number + UUID validation, path-traversal defense.
- :func:`parse_canonical_vehicle_photo_key` — reverse extraction of
  slug + stock + UUID; malformed keys refused.
- :func:`store_vehicle_photo` — server-side bytes-write via the
  adapter's ``put_bytes``. Content-type whitelist, size bounds,
  return shape.
- :meth:`_LocalAdapter.put_bytes` — writes bytes + sidecar file
  round-trip via :func:`get_object_metadata`.

M3.4 primitive behavior is covered by ``test_photo_storage.py``; this
file locks only the M6.2 additions.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    Dealership,
    VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
    VEHICLE_PHOTO_CONTENT_TYPE_PNG,
    Vehicle,
)
from dealer_ai.services.photo_storage import (
    InvalidContentTypeError,
    InvalidStorageKeyError,
    _LocalAdapter,
    _VEHICLE_PHOTO_MAX_BYTES,
    build_canonical_vehicle_photo_key,
    parse_canonical_vehicle_photo_key,
    store_vehicle_photo,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


class BuildCanonicalVehiclePhotoKey(TestCase):
    """Namespaced canonical key shape per SESSION_083 §1 Option A."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62KEY-BUILD", self.default)
        self.uuid = uuid.UUID("11111111-2222-3333-4444-555555555555")

    def test_key_shape_matches_option_a(self):
        key = build_canonical_vehicle_photo_key(
            dealership=self.default,
            vehicle=self.vehicle,
            photo_uuid=self.uuid,
        )
        self.assertEqual(
            key,
            "dealerships/default/vehicles/M62KEY-BUILD/"
            "photos/11111111-2222-3333-4444-555555555555/original",
        )

    def test_invalid_slug_rejected(self):
        bad = Dealership(name="Bad", slug="bad/slug")  # slash
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_vehicle_photo_key(
                dealership=bad, vehicle=self.vehicle, photo_uuid=self.uuid
            )

    def test_stock_number_with_space_rejected(self):
        """Vehicle.stock_number is a CharField — any stock number with
        a separator character would break canonical-key parsing."""
        bad_vehicle = Vehicle(
            stock_number="M62 KEY BAD",  # spaces
            year=2024,
            model="Escape",
            price=Decimal("22500.00"),
            dealership=self.default,
        )
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_vehicle_photo_key(
                dealership=self.default,
                vehicle=bad_vehicle,
                photo_uuid=self.uuid,
            )

    def test_invalid_uuid_rejected(self):
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_vehicle_photo_key(
                dealership=self.default,
                vehicle=self.vehicle,
                photo_uuid="not-a-uuid",  # type: ignore[arg-type]
            )


class ParseCanonicalVehiclePhotoKey(TestCase):
    """Reverse extraction — the M6.5 admin endpoint uses this to bind
    parsed slug + stock + uuid back to a Vehicle lookup."""

    def test_roundtrip_via_build_then_parse(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M62KEY-PARSE", default)
        photo_uuid = uuid.uuid4()
        key = build_canonical_vehicle_photo_key(
            dealership=default, vehicle=vehicle, photo_uuid=photo_uuid
        )
        parsed_slug, parsed_stock, parsed_uuid = (
            parse_canonical_vehicle_photo_key(key)
        )
        self.assertEqual(parsed_slug, "default")
        self.assertEqual(parsed_stock, "M62KEY-PARSE")
        self.assertEqual(parsed_uuid, photo_uuid)

    def test_condition_report_key_shape_refused(self):
        """M3.4 condition-report keys are structurally distinct and
        must NOT parse as vehicle-photo keys (would be a cross-domain
        confusion bug)."""
        cr_key = (
            "dealerships/default/condition-findings/"
            "11111111-2222-3333-4444-555555555555/original"
        )
        with self.assertRaises(InvalidStorageKeyError):
            parse_canonical_vehicle_photo_key(cr_key)

    def test_path_traversal_refused(self):
        with self.assertRaises(InvalidStorageKeyError):
            parse_canonical_vehicle_photo_key(
                "dealerships/default/vehicles/../../etc/passwd"
            )

    def test_non_string_input_refused(self):
        with self.assertRaises(InvalidStorageKeyError):
            parse_canonical_vehicle_photo_key(12345)  # type: ignore[arg-type]


class StoreVehiclePhoto(TestCase):
    """Server-side bytes write → adapter.put_bytes → returns key +
    metadata."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M62STORE", self.default)

    def test_returns_canonical_key_and_metadata(self):
        data = b"\x89PNG\r\n\x1a\nfake-image-body"
        key, metadata = store_vehicle_photo(
            dealership=self.default,
            vehicle=self.vehicle,
            photo_uuid=uuid.uuid4(),
            data=data,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_PNG,
        )
        self.assertRegex(
            key,
            r"^dealerships/default/vehicles/M62STORE/photos/"
            r"[0-9a-f-]+/original$",
        )
        self.assertEqual(metadata.content_type, VEHICLE_PHOTO_CONTENT_TYPE_PNG)
        self.assertEqual(metadata.size_bytes, len(data))
        self.assertTrue(metadata.exists)

    def test_head_verify_via_get_object_metadata(self):
        """After store, the local backend has an object with the same
        content-type + size — verified via the M3.4
        :func:`get_object_metadata` primitive that consumes the key."""
        data = b"jpeg body bytes"
        key, _stored = store_vehicle_photo(
            dealership=self.default,
            vehicle=self.vehicle,
            photo_uuid=uuid.uuid4(),
            data=data,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
        )
        # NOTE: get_object_metadata validates against the condition-
        # report key pattern, which our vehicle-photo key does not
        # match. Use adapter.get_object_metadata directly (same
        # underlying storage; different key namespace).
        from dealer_ai.services.photo_storage import _get_default_adapter
        adapter = _get_default_adapter()
        metadata = adapter.get_object_metadata(key)
        self.assertTrue(metadata.exists)
        self.assertEqual(metadata.content_type, VEHICLE_PHOTO_CONTENT_TYPE_JPEG)
        self.assertEqual(metadata.size_bytes, len(data))

    def test_invalid_content_type_refused(self):
        with self.assertRaises(InvalidContentTypeError):
            store_vehicle_photo(
                dealership=self.default,
                vehicle=self.vehicle,
                photo_uuid=uuid.uuid4(),
                data=b"body",
                content_type="image/heic",  # excluded per M6.1
            )

    def test_zero_byte_data_refused(self):
        with self.assertRaises(InvalidStorageKeyError):
            store_vehicle_photo(
                dealership=self.default,
                vehicle=self.vehicle,
                photo_uuid=uuid.uuid4(),
                data=b"",
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            )

    def test_oversize_data_refused(self):
        oversize = b"x" * (_VEHICLE_PHOTO_MAX_BYTES + 1)
        with self.assertRaises(InvalidStorageKeyError):
            store_vehicle_photo(
                dealership=self.default,
                vehicle=self.vehicle,
                photo_uuid=uuid.uuid4(),
                data=oversize,
                content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            )


class LocalAdapterPutBytes(TestCase):
    """The adapter-agnostic ``put_bytes`` verb reuses the same local
    sidecar-file logic as :meth:`store_local_upload`. Locked here so
    the delegation stays honest across future refactors."""

    def test_local_put_bytes_is_alias_for_store_local_upload(self):
        adapter = _LocalAdapter()
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M62PUT", default)
        key = build_canonical_vehicle_photo_key(
            dealership=default,
            vehicle=vehicle,
            photo_uuid=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        )
        data = b"content-body"
        metadata = adapter.put_bytes(
            storage_key=key,
            content_type=VEHICLE_PHOTO_CONTENT_TYPE_JPEG,
            data=data,
        )
        self.assertTrue(metadata.exists)
        self.assertEqual(metadata.size_bytes, len(data))
        # The sidecar file round-trips the content type — verify via
        # get_object_metadata.
        stored = adapter.get_object_metadata(key)
        self.assertEqual(stored.content_type, VEHICLE_PHOTO_CONTENT_TYPE_JPEG)
        self.assertEqual(stored.size_bytes, len(data))
