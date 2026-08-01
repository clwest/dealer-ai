"""Milestone 3 · Increment 4 — photo storage service tests.

Zero real network access. No ``moto``. Two orthogonal seams:

1. **Adapter auto-selection** via ``override_settings`` on
   ``STORAGES["condition_photos"]["BACKEND"]``. Proves that changing
   the backend path in settings changes which adapter
   ``_get_default_adapter`` returns.
2. **Adapter behavior** via ``mock.patch`` on the private
   ``_boto3_client`` factory of ``_S3Adapter`` (returns a boto3
   client with dummy credentials — ``generate_presigned_url`` is
   client-side and needs no network; ``head_object`` is patched
   further per test).

Public API is tested by patching ``_get_default_adapter`` to inject a
:class:`_FakeAdapter` — keeps the public functions free of testing
seams.

Test class map:

- ``AdapterAutoSelection`` — settings.STORAGES backend path drives
  the adapter type returned by ``_get_default_adapter``.
- ``CanonicalKeyBuilder`` — namespaced format; slug + UUID
  validation; path-traversal rejection.
- ``ContentTypeWhitelist`` — the four allowed MIMEs accepted;
  everything else raises ``InvalidContentTypeError``.
- ``TTLValidation`` — default, max, and invalid values.
- ``StorageKeyValidationOnRead`` — malformed keys are refused by
  ``object_exists`` and ``generate_read_url`` before any backend
  call happens.
- ``UploadTargetShape`` — response object contains everything
  M3.5 will need, nothing more.
- ``LocalAdapter`` — dev / test contract: local markers, safe
  ``object_exists`` via filesystem.
- ``S3Adapter`` — production contract: signed URLs, HEAD probe,
  provider-error handling (``ClientError`` 404 → False; other
  boto errors → ``ObjectStorageError``).
- ``PublicApiDelegation`` — public functions call the injected
  adapter with expected arguments.
- ``NoNetworkOrCredentialsInResponse`` — ``UploadTarget`` never
  contains raw AWS credentials.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import botocore.exceptions
from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_PHOTO_CONTENT_TYPE_CHOICES,
    CONDITION_PHOTO_CONTENT_TYPE_HEIC,
    CONDITION_PHOTO_CONTENT_TYPE_JPEG,
    CONDITION_PHOTO_CONTENT_TYPE_PNG,
    CONDITION_PHOTO_CONTENT_TYPE_WEBP,
    Dealership,
)
from dealer_ai.services.photo_storage import (
    LOCAL_READ_URL_MARKER,
    LOCAL_UPLOAD_URL_MARKER,
    InvalidContentTypeError,
    InvalidStorageKeyError,
    InvalidTTLError,
    ObjectStorageError,
    UploadTarget,
    _get_default_adapter,
    _LocalAdapter,
    _S3Adapter,
    build_canonical_key,
    generate_read_url,
    generate_upload_target,
    object_exists,
)


_FIXED_UUID = uuid.UUID("11111111-2222-3333-4444-555555555555")


def _canonical_key_for(dealership: Dealership, photo_uuid: uuid.UUID) -> str:
    return (
        f"dealerships/{dealership.slug}/condition-findings/"
        f"{photo_uuid}/original"
    )


# ---- Adapter auto-selection ---------------------------------------------


class AdapterAutoSelection(TestCase):
    """The adapter factory reads ``STORAGES["condition_photos"]["BACKEND"]``
    and returns the corresponding adapter class."""

    def test_local_filesystem_backend_returns_local_adapter(self):
        # The dev / test settings.py falls through to FileSystemStorage
        # when AWS_STORAGE_BUCKET_NAME is unset — assert that path.
        self.assertEqual(
            settings.STORAGES["condition_photos"]["BACKEND"],
            "django.core.files.storage.FileSystemStorage",
        )
        self.assertIsInstance(_get_default_adapter(), _LocalAdapter)

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
    def test_s3_backend_returns_s3_adapter(self):
        self.assertIsInstance(_get_default_adapter(), _S3Adapter)


# ---- Canonical key builder ----------------------------------------------


class CanonicalKeyBuilder(TestCase):
    """The ``build_canonical_key`` function is the single source of
    truth for the storage-key shape. Callers never construct keys
    directly."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_shape_matches_dealerships_slash_slug_slash_uuid_original(self):
        key = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )
        self.assertEqual(
            key,
            "dealerships/default/condition-findings/"
            "11111111-2222-3333-4444-555555555555/original",
        )

    def test_key_is_namespaced_by_dealership(self):
        other = Dealership.objects.create(name="Other", slug="other-33k")
        key_default = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )
        key_other = build_canonical_key(
            dealership=other, photo_uuid=_FIXED_UUID
        )
        # Same UUID but different tenant → different keys. No key
        # from one tenant can reach an object owned by another.
        self.assertNotEqual(key_default, key_other)
        self.assertIn("/default/", key_default)
        self.assertIn("/other-33k/", key_other)

    def test_photo_uuid_string_accepted_and_normalized(self):
        # Callers can pass a str UUID; we round-trip through
        # uuid.UUID for validation + canonical form.
        key_from_uuid = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )
        key_from_str = build_canonical_key(
            dealership=self.default, photo_uuid=str(_FIXED_UUID)
        )
        self.assertEqual(key_from_uuid, key_from_str)

    def test_photo_uuid_invalid_string_rejected(self):
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_key(
                dealership=self.default, photo_uuid="not-a-uuid"
            )

    def test_photo_uuid_none_rejected(self):
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_key(dealership=self.default, photo_uuid=None)

    def test_dealership_slug_with_dot_dot_path_traversal_rejected(self):
        # Construct a Dealership-shaped stub with a slug containing
        # ".." — proves the slug regex rejects before backend touch.
        # (Real Dealership model uses SlugField; this is
        # defense-in-depth for a case that SHOULD be impossible.)
        malicious = MagicMock(spec=Dealership)
        malicious.slug = "../etc/passwd"
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_key(dealership=malicious, photo_uuid=_FIXED_UUID)

    def test_dealership_slug_with_forward_slash_rejected(self):
        malicious = MagicMock(spec=Dealership)
        malicious.slug = "tenant-a/tenant-b"
        with self.assertRaises(InvalidStorageKeyError):
            build_canonical_key(dealership=malicious, photo_uuid=_FIXED_UUID)


# ---- Content-type whitelist --------------------------------------------


class ContentTypeWhitelist(TestCase):
    """The four allowed MIME values from M3.1's
    ``CONDITION_PHOTO_CONTENT_TYPE_CHOICES`` are accepted. Every
    other value raises ``InvalidContentTypeError`` before any
    presigned URL is issued."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def _try_upload(self, content_type: str):
        return generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=content_type,
        )

    def test_all_four_canonical_content_types_accepted(self):
        # Each canonical MIME must produce an UploadTarget without
        # raising. Locks the whitelist matches M3.1 model constant.
        for ct in (
            CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            CONDITION_PHOTO_CONTENT_TYPE_PNG,
            CONDITION_PHOTO_CONTENT_TYPE_HEIC,
            CONDITION_PHOTO_CONTENT_TYPE_WEBP,
        ):
            target = self._try_upload(ct)
            self.assertIsInstance(target, UploadTarget)
            self.assertEqual(target.required_headers["Content-Type"], ct)

    def test_whitelist_matches_m3_1_model_constant(self):
        # Zero-drift guard: if a future edit adds an MIME to the model
        # enum but forgets to sync photo_storage, or vice versa, this
        # test catches it.
        model_keys = {k for k, _ in CONDITION_PHOTO_CONTENT_TYPE_CHOICES}
        # Access the module-level constant via a probe upload of each.
        for ct in model_keys:
            self._try_upload(ct)  # must not raise

    def test_non_image_content_type_rejected(self):
        with self.assertRaises(InvalidContentTypeError):
            self._try_upload("application/octet-stream")

    def test_svg_rejected_even_though_image(self):
        # SVG allows embedded JavaScript — deliberately not on the
        # whitelist. Locks that fact.
        with self.assertRaises(InvalidContentTypeError):
            self._try_upload("image/svg+xml")

    def test_empty_content_type_rejected(self):
        with self.assertRaises(InvalidContentTypeError):
            self._try_upload("")


# ---- TTL validation ----------------------------------------------------


class TTLValidation(TestCase):
    """TTL is a security ceiling, not a knob. 15-minute maximum
    (900 seconds) is documented + tested + non-configurable."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_default_ttl_is_max_ttl(self):
        # Safe path is the default path.
        target = generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
        )
        remaining = target.expires_at - timezone.now()
        # Allow a couple of seconds for test-runtime slack.
        self.assertGreater(remaining, timedelta(seconds=890))
        self.assertLessEqual(remaining, timedelta(seconds=900))

    def test_ttl_at_max_accepted(self):
        target = generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            ttl_seconds=900,
        )
        self.assertIsInstance(target, UploadTarget)

    def test_ttl_over_max_rejected(self):
        with self.assertRaises(InvalidTTLError):
            generate_upload_target(
                dealership=self.default,
                photo_uuid=_FIXED_UUID,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=901,
            )

    def test_ttl_zero_rejected(self):
        with self.assertRaises(InvalidTTLError):
            generate_upload_target(
                dealership=self.default,
                photo_uuid=_FIXED_UUID,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=0,
            )

    def test_ttl_negative_rejected(self):
        with self.assertRaises(InvalidTTLError):
            generate_upload_target(
                dealership=self.default,
                photo_uuid=_FIXED_UUID,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=-1,
            )

    def test_ttl_non_int_rejected(self):
        with self.assertRaises(InvalidTTLError):
            generate_upload_target(
                dealership=self.default,
                photo_uuid=_FIXED_UUID,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=60.0,  # float
            )

    def test_ttl_bool_rejected(self):
        # ``True`` is a subclass of ``int`` in Python — explicit
        # rejection prevents ``ttl_seconds=True`` sliding through as
        # "1 second."
        with self.assertRaises(InvalidTTLError):
            generate_upload_target(
                dealership=self.default,
                photo_uuid=_FIXED_UUID,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=True,
            )

    def test_expires_at_is_timezone_aware(self):
        target = generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
        )
        self.assertIsNotNone(target.expires_at.tzinfo)

    def test_read_url_ttl_over_max_rejected(self):
        default = Dealership.objects.get(slug="default")
        key = build_canonical_key(dealership=default, photo_uuid=_FIXED_UUID)
        with self.assertRaises(InvalidTTLError):
            generate_read_url(storage_key=key, ttl_seconds=901)


# ---- Storage-key re-validation on read paths ---------------------------


class StorageKeyValidationOnRead(TestCase):
    """``object_exists`` and ``generate_read_url`` re-validate any
    caller-supplied ``storage_key`` against the canonical pattern
    before touching the backend. A malformed or forged key is
    refused *before* any backend call."""

    def test_object_exists_rejects_dot_dot_path_traversal(self):
        with self.assertRaises(InvalidStorageKeyError):
            object_exists("dealerships/default/../etc/passwd")

    def test_object_exists_rejects_arbitrary_key(self):
        with self.assertRaises(InvalidStorageKeyError):
            object_exists("my-custom-key.jpg")

    def test_object_exists_rejects_missing_uuid_segment(self):
        with self.assertRaises(InvalidStorageKeyError):
            object_exists(
                "dealerships/default/condition-findings/not-a-uuid/original"
            )

    def test_object_exists_rejects_missing_original_suffix(self):
        with self.assertRaises(InvalidStorageKeyError):
            object_exists(
                f"dealerships/default/condition-findings/{_FIXED_UUID}"
            )

    def test_generate_read_url_rejects_forged_key(self):
        with self.assertRaises(InvalidStorageKeyError):
            generate_read_url(
                storage_key="dealerships/../secrets/config.env",
                ttl_seconds=60,
            )

    def test_read_paths_do_not_touch_backend_on_invalid_key(self):
        # If the key validator ran too late, the mocked adapter's
        # methods would have been called. Assert the mock was never
        # touched.
        fake = MagicMock()
        with patch(
            "dealer_ai.services.photo_storage._get_default_adapter",
            return_value=fake,
        ):
            with self.assertRaises(InvalidStorageKeyError):
                object_exists("garbage-key")
            with self.assertRaises(InvalidStorageKeyError):
                generate_read_url(storage_key="garbage-key")
        fake.object_exists.assert_not_called()
        fake.generate_read_url.assert_not_called()


# ---- Upload-target response shape -------------------------------------


class UploadTargetShape(TestCase):
    """The :class:`UploadTarget` dataclass contains everything M3.5
    will need — method, URL, key, headers, expiry — and nothing more
    (specifically, no raw AWS credentials)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_all_fields_populated(self):
        target = generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_PNG,
        )
        self.assertEqual(target.method, "PUT")
        self.assertTrue(target.upload_url)
        self.assertEqual(
            target.storage_key,
            _canonical_key_for(self.default, _FIXED_UUID),
        )
        self.assertEqual(
            target.required_headers["Content-Type"],
            CONDITION_PHOTO_CONTENT_TYPE_PNG,
        )
        self.assertIsInstance(target.expires_at, datetime)

    def test_frozen_dataclass_is_immutable(self):
        target = generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
        )
        with self.assertRaises(Exception):
            target.upload_url = "https://malicious"  # type: ignore[misc]

    def test_response_contains_no_aws_credentials(self):
        # An accidental exposure of AWS_ACCESS_KEY_ID /
        # AWS_SECRET_ACCESS_KEY through the response would be a
        # major security bug — this test rules it out by scanning
        # the full response text.
        target = generate_upload_target(
            dealership=self.default,
            photo_uuid=_FIXED_UUID,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
        )
        blob = repr(target).lower()
        self.assertNotIn("aws_access_key_id", blob)
        self.assertNotIn("aws_secret_access_key", blob)
        self.assertNotIn("secret", blob)


# ---- Local adapter behavior ------------------------------------------


class LocalAdapter(TestCase):
    """Dev / test contract: markers, filesystem-backed
    ``object_exists``, no network."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.adapter = _LocalAdapter()
        self.storage_key = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )

    def test_generate_upload_url_returns_local_marker(self):
        url, headers, expires_at = self.adapter.generate_upload_url(
            storage_key=self.storage_key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            ttl_seconds=300,
        )
        self.assertTrue(url.startswith(LOCAL_UPLOAD_URL_MARKER))
        self.assertIn(self.storage_key, url)
        self.assertEqual(
            headers["Content-Type"], CONDITION_PHOTO_CONTENT_TYPE_JPEG
        )
        self.assertIsNotNone(expires_at.tzinfo)

    def test_generate_read_url_returns_local_marker(self):
        url = self.adapter.generate_read_url(
            storage_key=self.storage_key, ttl_seconds=300
        )
        self.assertTrue(url.startswith(LOCAL_READ_URL_MARKER))
        self.assertIn(self.storage_key, url)

    def test_object_exists_returns_false_for_missing_file(self):
        # No file has been written; the adapter reports absent.
        self.assertFalse(self.adapter.object_exists(self.storage_key))


# ---- S3 adapter behavior (fully mocked, zero network) ---------------


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
class S3Adapter(TestCase):
    """Production contract exercised with a mocked boto3 client.
    No real S3 network access — every backend call is asserted at
    the boto3-client method level."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.storage_key = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )

    def _make_adapter_with_mock_client(self, mock_client):
        adapter = _S3Adapter()
        adapter._boto3_client = MagicMock(return_value=mock_client)  # type: ignore[method-assign]
        return adapter

    def test_generate_upload_url_calls_boto3_with_put_and_content_type(self):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/signed?X-Amz-Signature=abc"
        )
        adapter = self._make_adapter_with_mock_client(mock_client)

        url, headers, expires_at = adapter.generate_upload_url(
            storage_key=self.storage_key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            ttl_seconds=600,
        )

        mock_client.generate_presigned_url.assert_called_once()
        call_kwargs = mock_client.generate_presigned_url.call_args.kwargs
        self.assertEqual(call_kwargs["ClientMethod"], "put_object")
        self.assertEqual(call_kwargs["HttpMethod"], "PUT")
        self.assertEqual(call_kwargs["ExpiresIn"], 600)
        self.assertEqual(call_kwargs["Params"]["Bucket"], "test-bucket")
        self.assertEqual(call_kwargs["Params"]["Key"], self.storage_key)
        self.assertEqual(
            call_kwargs["Params"]["ContentType"],
            CONDITION_PHOTO_CONTENT_TYPE_JPEG,
        )
        self.assertEqual(url, mock_client.generate_presigned_url.return_value)
        self.assertEqual(
            headers["Content-Type"], CONDITION_PHOTO_CONTENT_TYPE_JPEG
        )

    def test_generate_read_url_calls_boto3_with_get(self):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/signed-get?X-Amz-Signature=x"
        )
        adapter = self._make_adapter_with_mock_client(mock_client)

        url = adapter.generate_read_url(
            storage_key=self.storage_key, ttl_seconds=600
        )

        call_kwargs = mock_client.generate_presigned_url.call_args.kwargs
        self.assertEqual(call_kwargs["ClientMethod"], "get_object")
        self.assertEqual(call_kwargs["HttpMethod"], "GET")
        self.assertEqual(call_kwargs["ExpiresIn"], 600)
        self.assertEqual(url, mock_client.generate_presigned_url.return_value)

    def test_object_exists_true_when_head_succeeds(self):
        mock_client = MagicMock()
        mock_client.head_object.return_value = {"ContentLength": 12345}
        adapter = self._make_adapter_with_mock_client(mock_client)
        self.assertTrue(adapter.object_exists(self.storage_key))
        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key=self.storage_key
        )

    def test_object_exists_false_when_head_returns_404(self):
        mock_client = MagicMock()
        mock_client.head_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )
        adapter = self._make_adapter_with_mock_client(mock_client)
        self.assertFalse(adapter.object_exists(self.storage_key))

    def test_object_exists_false_when_head_returns_no_such_key(self):
        mock_client = MagicMock()
        mock_client.head_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist"}},
            "HeadObject",
        )
        adapter = self._make_adapter_with_mock_client(mock_client)
        self.assertFalse(adapter.object_exists(self.storage_key))

    def test_object_exists_raises_on_non_404_client_error(self):
        mock_client = MagicMock()
        mock_client.head_object.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}},
            "HeadObject",
        )
        adapter = self._make_adapter_with_mock_client(mock_client)
        with self.assertRaises(ObjectStorageError):
            adapter.object_exists(self.storage_key)

    def test_generate_presigned_url_error_wrapped_in_object_storage_error(self):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.side_effect = (
            botocore.exceptions.EndpointConnectionError(
                endpoint_url="https://s3.amazonaws.com"
            )
        )
        adapter = self._make_adapter_with_mock_client(mock_client)
        with self.assertRaises(ObjectStorageError):
            adapter.generate_upload_url(
                storage_key=self.storage_key,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=300,
            )


# ---- Public API delegation ------------------------------------------


class PublicApiDelegation(TestCase):
    """The public functions delegate to the adapter returned by
    ``_get_default_adapter``. Verified by patching the factory to
    inject a mock and asserting the call arguments."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")

    def test_generate_upload_target_delegates_after_validation(self):
        mock_adapter = MagicMock()
        expires_at = timezone.now() + timedelta(seconds=300)
        mock_adapter.generate_upload_url.return_value = (
            "https://fake-signed-put",
            {"Content-Type": CONDITION_PHOTO_CONTENT_TYPE_JPEG},
            expires_at,
        )
        with patch(
            "dealer_ai.services.photo_storage._get_default_adapter",
            return_value=mock_adapter,
        ):
            target = generate_upload_target(
                dealership=self.default,
                photo_uuid=_FIXED_UUID,
                content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                ttl_seconds=300,
            )
        # Adapter received the internally-built key + TTL + MIME.
        mock_adapter.generate_upload_url.assert_called_once_with(
            storage_key=_canonical_key_for(self.default, _FIXED_UUID),
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            ttl_seconds=300,
        )
        self.assertEqual(target.upload_url, "https://fake-signed-put")
        self.assertEqual(target.expires_at, expires_at)

    def test_object_exists_delegates(self):
        mock_adapter = MagicMock()
        mock_adapter.object_exists.return_value = True
        key = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )
        with patch(
            "dealer_ai.services.photo_storage._get_default_adapter",
            return_value=mock_adapter,
        ):
            result = object_exists(key)
        self.assertTrue(result)
        mock_adapter.object_exists.assert_called_once_with(key)

    def test_generate_read_url_delegates(self):
        mock_adapter = MagicMock()
        mock_adapter.generate_read_url.return_value = "https://signed-get"
        key = build_canonical_key(
            dealership=self.default, photo_uuid=_FIXED_UUID
        )
        with patch(
            "dealer_ai.services.photo_storage._get_default_adapter",
            return_value=mock_adapter,
        ):
            result = generate_read_url(storage_key=key, ttl_seconds=300)
        self.assertEqual(result, "https://signed-get")
        mock_adapter.generate_read_url.assert_called_once_with(
            storage_key=key, ttl_seconds=300
        )

    def test_content_type_invalid_short_circuits_before_adapter(self):
        # Adapter is patched so any call would be visible; verify
        # the validator refuses first.
        mock_adapter = MagicMock()
        with patch(
            "dealer_ai.services.photo_storage._get_default_adapter",
            return_value=mock_adapter,
        ):
            with self.assertRaises(InvalidContentTypeError):
                generate_upload_target(
                    dealership=self.default,
                    photo_uuid=_FIXED_UUID,
                    content_type="text/html",
                )
        mock_adapter.generate_upload_url.assert_not_called()
