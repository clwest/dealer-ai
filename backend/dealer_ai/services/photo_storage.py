"""Milestone 3 · Increment 4 — provider-neutral photo storage service.

The one place condition-report photo storage decisions live. Answers
one question: **how does a caller obtain private, short-lived upload
and read access to condition-report photo objects, without knowing
which storage backend is configured, and without ever generating an
insecure or path-traversal-vulnerable key?**

Public API (four functions + one dataclass):

- :func:`build_canonical_key` — deterministic key builder. The single
  source of truth for the storage-key shape. Every other function
  routes through it.
- :func:`generate_upload_target` — server-side; issues a short-lived
  presigned PUT contract for a specific dealership + photo UUID. The
  caller **never** supplies the storage key — the service generates
  it from the tenant + UUID inputs. This closes the path-traversal
  seam that would exist if untrusted callers chose keys directly.
- :func:`object_exists` — HEAD-only verification. Returns ``bool``.
  Used by M3.5's ``attach_photo`` to reject metadata for objects
  that never landed on the storage backend.
- :func:`generate_read_url` — issues a short-lived signed URL for a
  specific object. Enforces the maximum-TTL cap. Never generates a
  permanent public URL.

**No caller-supplied storage_key on upload path.** The M3.4 planning
draft envisioned callers supplying a ``storage_key`` argument to the
upload-URL issuance function. SESSION_059 spec (user) tightened this:
arbitrary caller-chosen keys are a path-traversal vector, and expose
the storage layout to consumers who shouldn't know it. As shipped,
:func:`generate_upload_target` accepts only ``dealership`` and
``photo_uuid`` (both structured, both validated); the canonical key is
computed internally by :func:`build_canonical_key`. See the planning
§7 M3.4 SHIPPED annotation for the full refinement.

Canonical key shape (locked by tests + regex validators)::

    dealerships/<dealership_slug>/condition-findings/<photo_uuid>/original

- ``dealership_slug`` — validated against a strict slug pattern.
  Dealership slug values are already SlugField-constrained at the
  model layer; this re-validates as defense-in-depth.
- ``photo_uuid`` — a canonical :class:`uuid.UUID`. Rejects any
  input that ``uuid.UUID(str(x))`` can't parse.
- ``original`` — hardcoded final segment. Reserves the door for
  future variants (``thumbnails/``, ``exif-stripped/``, etc.) that
  would land under the same UUID.

Path-traversal defense:

- The regex accepts only ``[-a-zA-Z0-9_]`` in the slug segment and
  hex + hyphens for the UUID segment. ``..``, forward slashes, or
  any other separator characters simply do not match.
- Every function that accepts ``storage_key`` (``object_exists``,
  ``generate_read_url``) re-validates the key against
  :data:`_KEY_PATTERN` at entry and raises
  :class:`InvalidStorageKeyError` on any mismatch. A caller with a
  compromised or forged key cannot reach the backend.

PUT vs POST — honest security disclosure:

As shipped, :func:`generate_upload_target` returns a presigned **PUT**
URL with a bound ``Content-Type`` header. S3 will reject any upload
whose ``Content-Type`` header does not match. That is the ONLY
condition the presigned URL enforces at upload time.

**Upload-size is NOT enforced by the presigned PUT.** A malicious
client could upload a 1 GB object under a 500-byte declared size. The
M3.5 ``attach_photo`` service will HEAD-verify the actual object size
against the client-declared value and reject mismatches. Do not claim
size enforcement here; it is deferred to M3.5's HEAD confirmation.

(Alternative: presigned POST + policy conditions can bind size at the
URL boundary, but the client shape is more complex — form-multipart
with policy JSON + signature. Kept for a possible future revisit if
M3.5's HEAD verification proves insufficient in practice.)

Adapter architecture:

- :class:`_PhotoStorageAdapter` — Protocol; every backend implements
  three methods (``generate_upload_url``, ``object_exists``,
  ``generate_read_url``).
- :class:`_S3Adapter` — production. Uses ``boto3.client("s3")``
  directly for presigned-URL generation and HEAD probes. Does not
  route through django-storages' ``S3Storage`` for URL work —
  django-storages is present as the "where do bytes live" abstraction
  for future callers (e.g. any future Django-managed file field), not
  as the URL-generation layer.
- :class:`_LocalAdapter` — dev / test. Returns explicit
  non-production URL markers (:data:`LOCAL_UPLOAD_URL_MARKER` /
  :data:`LOCAL_READ_URL_MARKER`) so consumers cannot mistake them
  for real signed URLs. Filesystem-backed ``object_exists``.

Test isolation (no ``moto``, no network):

- Adapter auto-selection tested via ``override_settings`` on
  ``STORAGES["condition_photos"]["BACKEND"]``.
- :class:`_S3Adapter` behavior tested via ``mock.patch`` of the
  private ``_boto3_client`` factory (returning a boto3 client
  constructed with dummy credentials — ``generate_presigned_url``
  is client-side and needs no network) plus ``mock.patch`` of the
  client's ``head_object`` for HEAD tests.
- Public function tests patch ``_get_default_adapter`` to inject
  a fake adapter, keeping the public API clean of test seams.

Deferred (do NOT add in M3.4):

- ``request_photo_upload`` / ``attach_photo`` / ``delete_photo``
  service functions — those land in M3.5 in
  ``services/condition_report.py`` and consume this module.
- Any ``ConditionFindingPhoto`` row creation, HEAD-verification
  workflow, or API endpoint — all M3.5+.
- Image processing (thumbnails, EXIF stripping, resizing) — every
  downstream image concern is deferred to whatever milestone first
  needs it.
- An authenticated Django download route to replace
  :data:`LOCAL_READ_URL_MARKER` in dev — M3.5 or M3.7 owns that
  routing decision.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Protocol

import boto3
import botocore.exceptions
from django.conf import settings
from django.core.files.storage import storages
from django.utils import timezone

from ..models import CONDITION_PHOTO_CONTENT_TYPE_CHOICES, Dealership

# ---- Constants ------------------------------------------------------------

# Maximum TTL for both upload and read URLs. Per RECON §13.1 the
# report is warranty-defense evidence and short-TTL signed URLs are
# the correct posture; 15 minutes gives a browser tab enough time to
# render or PUT once and nothing more.
_MAX_TTL_SECONDS = 900

# Default TTL when the caller does not supply one. Matches the max
# so the safe path is also the default path.
_DEFAULT_TTL_SECONDS = 900

# Content-type whitelist mirrors the model-layer choices constant
# from M3.1. Keeping the source of truth in the model layer avoids
# vocabulary drift between the persistence contract and the storage
# contract. Any addition or rename requires touching the model
# constant, which forces a design conversation.
_VALID_CONTENT_TYPES = frozenset(
    key for key, _ in CONDITION_PHOTO_CONTENT_TYPE_CHOICES
)

# Slug pattern for the dealership segment. Matches Django's
# SlugField semantics (``[-a-zA-Z0-9_]+``). Re-validated here as
# defense-in-depth even though slug values entering the model layer
# are already SlugField-constrained.
_SLUG_PATTERN = re.compile(r"^[-a-zA-Z0-9_]+$")

# Full canonical key pattern. Any storage_key entering
# ``object_exists`` or ``generate_read_url`` from outside this module
# is re-validated against this regex before touching a backend.
# ``..``, ``/``, and any other separator characters simply do not
# match — path traversal is impossible by construction.
_KEY_PATTERN = re.compile(
    r"^dealerships/[-a-zA-Z0-9_]+/condition-findings/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r"/original$"
)

# Local-mode URL markers. Explicitly non-URL schemes so any caller
# that hands one to a browser fails loudly instead of silently
# treating it as a real signed URL. Locked by tests.
LOCAL_UPLOAD_URL_MARKER = "local-dev-no-signature-upload"
LOCAL_READ_URL_MARKER = "local-dev-no-signature-read"


# ---- Domain errors --------------------------------------------------------


class InvalidStorageKeyError(ValueError):
    """Raised when a supplied ``storage_key`` does not match the
    canonical shape (:data:`_KEY_PATTERN`), or when the inputs to
    :func:`build_canonical_key` cannot produce a valid key.

    Distinct class so log lines and future API layers can identify
    the failure mode without string-matching an error message.
    """


class InvalidContentTypeError(ValueError):
    """Raised when ``content_type`` is not one of the four whitelisted
    MIME values from ``CONDITION_PHOTO_CONTENT_TYPE_CHOICES``.

    Enforced at the presigned-URL boundary so a malicious client
    cannot request a URL for an ``application/octet-stream`` upload.
    """


class InvalidTTLError(ValueError):
    """Raised when ``ttl_seconds`` is <= 0 or > :data:`_MAX_TTL_SECONDS`.

    The cap is documented + tested + non-configurable — TTL is a
    security ceiling, not a knob.
    """


class ObjectStorageError(RuntimeError):
    """Raised when a backend operation fails for a reason that is not
    "the object doesn't exist."

    Distinct from :class:`InvalidStorageKeyError` (client-side
    validation failure): this wraps a real backend fault — network,
    credentials, permissions, throttling. Callers should treat this
    as a transient error to surface to the operator, not as a
    "missing object" verdict.
    """


# ---- Upload-target dataclass ---------------------------------------------


@dataclass(frozen=True)
class UploadTarget:
    """Server-issued instructions for a single presigned upload.

    Every field is what the M3.5 upload flow will hand to the browser
    (or, in local mode, the dev-side upload helper) so the browser
    knows exactly how to PUT the bytes.

    Fields:

    - ``method`` — HTTP verb the client must use. Always ``"PUT"`` in
      v1 (see the module docstring for the PUT-vs-POST rationale).
    - ``upload_url`` — the URL the client PUTs to. In production, a
      real presigned S3 URL. In dev / test, the
      :data:`LOCAL_UPLOAD_URL_MARKER` prefix followed by the
      canonical storage key — the M3.5 upload flow detects the
      prefix and routes to a Django-side upload helper instead of
      attempting a browser-direct PUT.
    - ``storage_key`` — the canonical key the object will land under.
      The M3.5 upload flow persists this on the
      :class:`ConditionFindingPhoto` row **after** HEAD-verifying
      the upload landed.
    - ``required_headers`` — headers the client MUST send with the
      PUT. Includes ``Content-Type`` bound to the value passed to
      :func:`generate_upload_target`; S3 rejects PUTs that mismatch.
    - ``expires_at`` — timezone-aware :class:`datetime` at which the
      presigned URL stops being usable. Always ≤
      :data:`_MAX_TTL_SECONDS` from issuance.

    ``credentials`` are deliberately absent from every field — the
    presigned URL carries its own signature; the response never
    exposes raw ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``.
    """

    method: str
    upload_url: str
    storage_key: str
    required_headers: Mapping[str, str]
    expires_at: datetime


# ---- Adapter protocol + implementations ---------------------------------


class _PhotoStorageAdapter(Protocol):
    """Internal contract every backend adapter implements.

    Not part of the public API. Called only by the module-level
    functions after they've validated inputs. Adapters do NOT
    re-validate content type, TTL, or storage key — that's the
    module's job so the invariants live in exactly one place.
    """

    def generate_upload_url(
        self, *, storage_key: str, content_type: str, ttl_seconds: int
    ) -> tuple[str, Mapping[str, str], datetime]:
        """Return ``(upload_url, required_headers, expires_at)`` for
        a single presigned upload."""

    def object_exists(self, storage_key: str) -> bool:
        """Return ``True`` iff the object currently exists on the
        backend. Missing = ``False``; backend faults raise
        :class:`ObjectStorageError`."""

    def generate_read_url(
        self, *, storage_key: str, ttl_seconds: int
    ) -> str:
        """Return a short-lived signed read URL for the object.
        Never returns a permanent public URL."""


class _LocalAdapter:
    """Dev / test adapter — never touches S3 or any network.

    Backed by Django's ``storages["condition_photos"]`` alias which
    resolves to ``FileSystemStorage`` when
    ``AWS_STORAGE_BUCKET_NAME`` is unset. Upload / read URLs are
    explicit :data:`LOCAL_UPLOAD_URL_MARKER` /
    :data:`LOCAL_READ_URL_MARKER` markers so any caller that hands
    one to a browser fails loudly — production callers must be
    running against a real S3-configured environment.
    """

    def generate_upload_url(
        self, *, storage_key: str, content_type: str, ttl_seconds: int
    ) -> tuple[str, Mapping[str, str], datetime]:
        # The URL is a marker; the M3.5 upload flow will detect the
        # prefix and route to a Django-side upload helper. The
        # required_headers stay honest so tests can lock the shape.
        upload_url = f"{LOCAL_UPLOAD_URL_MARKER}:{storage_key}"
        headers = {"Content-Type": content_type}
        expires_at = timezone.now() + timedelta(seconds=ttl_seconds)
        return upload_url, headers, expires_at

    def object_exists(self, storage_key: str) -> bool:
        # ``storages["condition_photos"]`` returns the
        # FileSystemStorage instance rooted at
        # ``MEDIA_ROOT/condition-photos`` (per settings.py). Its
        # ``.exists()`` method is a simple ``os.path.exists`` check.
        try:
            return storages["condition_photos"].exists(storage_key)
        except OSError as exc:  # permission / IO failure — treat as backend fault
            raise ObjectStorageError(
                f"Local storage HEAD failed for {storage_key!r}: {exc}"
            ) from exc

    def generate_read_url(
        self, *, storage_key: str, ttl_seconds: int
    ) -> str:
        # Do not pretend this is a signed URL. The M3.5 or M3.7 UI
        # detects the prefix and generates its own authenticated
        # download route.
        return f"{LOCAL_READ_URL_MARKER}:{storage_key}"


class _S3Adapter:
    """Production adapter — issues real presigned URLs against S3
    (or an S3-compatible endpoint) via ``boto3``.

    Reads bucket / region / endpoint from
    ``settings.STORAGES["condition_photos"]["OPTIONS"]``. Credentials
    come from the standard AWS SDK credential chain (env, IAM role,
    etc.); this adapter never touches raw
    ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` directly.
    """

    def __init__(self) -> None:
        self._options = settings.STORAGES["condition_photos"]["OPTIONS"]
        self._bucket = self._options["bucket_name"]

    def _boto3_client(self):
        """Construct a fresh boto3 S3 client per call.

        Not cached — presigned-URL generation is cheap enough that
        client construction is not the bottleneck, and a fresh
        client per call keeps the test seam simple
        (``mock.patch`` targets this method). If profiling ever
        shows client construction dominating, add an
        ``@functools.lru_cache`` here — but not preemptively.
        """
        kwargs: dict = {
            "service_name": "s3",
            "region_name": self._options.get("region_name"),
        }
        endpoint_url = self._options.get("endpoint_url")
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        return boto3.client(**kwargs)

    def generate_upload_url(
        self, *, storage_key: str, content_type: str, ttl_seconds: int
    ) -> tuple[str, Mapping[str, str], datetime]:
        client = self._boto3_client()
        try:
            upload_url = client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": storage_key,
                    "ContentType": content_type,
                },
                ExpiresIn=ttl_seconds,
                HttpMethod="PUT",
            )
        except botocore.exceptions.BotoCoreError as exc:
            raise ObjectStorageError(
                f"Failed to issue upload URL for {storage_key!r}: {exc}"
            ) from exc
        headers = {"Content-Type": content_type}
        expires_at = timezone.now() + timedelta(seconds=ttl_seconds)
        return upload_url, headers, expires_at

    def object_exists(self, storage_key: str) -> bool:
        client = self._boto3_client()
        try:
            client.head_object(Bucket=self._bucket, Key=storage_key)
        except botocore.exceptions.ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            # S3 returns 404 for both "no such key" and "no such
            # bucket" (though the latter should never happen against
            # a configured bucket). Treat both as "does not exist."
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise ObjectStorageError(
                f"S3 HEAD failed for {storage_key!r}: {exc}"
            ) from exc
        except botocore.exceptions.BotoCoreError as exc:
            raise ObjectStorageError(
                f"S3 HEAD failed for {storage_key!r}: {exc}"
            ) from exc
        return True

    def generate_read_url(
        self, *, storage_key: str, ttl_seconds: int
    ) -> str:
        client = self._boto3_client()
        try:
            return client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": storage_key},
                ExpiresIn=ttl_seconds,
                HttpMethod="GET",
            )
        except botocore.exceptions.BotoCoreError as exc:
            raise ObjectStorageError(
                f"Failed to issue read URL for {storage_key!r}: {exc}"
            ) from exc


# ---- Adapter factory (auto-selection from settings) ---------------------


_S3_BACKEND_PATH = "storages.backends.s3.S3Storage"


def _get_default_adapter() -> _PhotoStorageAdapter:
    """Return the adapter matching the current
    ``STORAGES["condition_photos"]["BACKEND"]``.

    Tests patch this function to inject a fake adapter. Production
    code never sees the adapter type directly — every caller goes
    through the module-level public functions.
    """
    backend = settings.STORAGES["condition_photos"]["BACKEND"]
    if backend == _S3_BACKEND_PATH:
        return _S3Adapter()
    return _LocalAdapter()


# ---- Public: canonical key builder --------------------------------------


def build_canonical_key(
    *, dealership: Dealership, photo_uuid: uuid.UUID
) -> str:
    """Return the canonical storage key for a condition-report photo.

    Shape: ``dealerships/<slug>/condition-findings/<uuid>/original``.

    The only entry point that constructs a new key. Every other
    function either consumes a key it produced (``generate_upload_target``)
    or re-validates a caller-supplied key against
    :data:`_KEY_PATTERN` (``object_exists``, ``generate_read_url``).

    Raises :class:`InvalidStorageKeyError` when the dealership slug
    fails :data:`_SLUG_PATTERN` (defense-in-depth: SlugField already
    constrains slug values entering the model layer) or when
    ``photo_uuid`` cannot be parsed as a canonical UUID.
    """
    slug = getattr(dealership, "slug", None)
    if slug is None or not _SLUG_PATTERN.match(slug):
        raise InvalidStorageKeyError(
            f"Dealership slug {slug!r} does not match canonical slug "
            f"pattern {_SLUG_PATTERN.pattern!r}."
        )
    try:
        canonical_uuid = uuid.UUID(str(photo_uuid))
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidStorageKeyError(
            f"photo_uuid {photo_uuid!r} is not a valid UUID: {exc}"
        ) from exc
    return (
        f"dealerships/{slug}/condition-findings/"
        f"{canonical_uuid}/original"
    )


# ---- Public: input validators (also called internally) -----------------


def _validate_content_type(content_type: str) -> None:
    if content_type not in _VALID_CONTENT_TYPES:
        raise InvalidContentTypeError(
            f"content_type {content_type!r} is not in the M3.1 "
            f"whitelist. Valid values live in "
            f"``dealer_ai.models.CONDITION_PHOTO_CONTENT_TYPE_CHOICES``."
        )


def _validate_ttl(ttl_seconds: int) -> None:
    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
        raise InvalidTTLError(
            f"ttl_seconds must be an int, got {type(ttl_seconds).__name__}."
        )
    if ttl_seconds <= 0:
        raise InvalidTTLError(
            f"ttl_seconds must be positive, got {ttl_seconds}."
        )
    if ttl_seconds > _MAX_TTL_SECONDS:
        raise InvalidTTLError(
            f"ttl_seconds {ttl_seconds} exceeds the {_MAX_TTL_SECONDS}s "
            "maximum. Short-TTL signed URLs are the security posture; "
            "the cap is non-configurable."
        )


def _validate_storage_key(storage_key: str) -> None:
    if not isinstance(storage_key, str) or not _KEY_PATTERN.match(
        storage_key
    ):
        raise InvalidStorageKeyError(
            f"storage_key {storage_key!r} does not match the canonical "
            f"pattern. Every storage_key entering this service must "
            f"have been produced by ``build_canonical_key``."
        )


# ---- Public: upload target -----------------------------------------------


def generate_upload_target(
    *,
    dealership: Dealership,
    photo_uuid: uuid.UUID,
    content_type: str,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> UploadTarget:
    """Return an :class:`UploadTarget` a caller can hand to the
    browser (or to M3.5's local-mode upload helper) to PUT one photo.

    The service — not the caller — decides the storage key. The
    caller supplies structured inputs (:class:`Dealership` instance,
    :class:`uuid.UUID`) that :func:`build_canonical_key` composes
    into a namespaced, path-traversal-safe key.

    Enforces:

    - ``content_type`` in the four-value MIME whitelist.
    - ``ttl_seconds`` positive + ≤ :data:`_MAX_TTL_SECONDS`.
    - Canonical key shape (via :func:`build_canonical_key`).
    - PUT method with ``Content-Type`` bound in the presigned URL —
      S3 rejects any upload whose ``Content-Type`` header does not
      match. **Upload-size is NOT enforced here** — see module
      docstring; M3.5 HEAD-verifies size.

    Never embeds AWS credentials in the return value. The presigned
    URL carries its own signature; the response object is safe to
    hand to the browser as-is.
    """
    _validate_content_type(content_type)
    _validate_ttl(ttl_seconds)
    storage_key = build_canonical_key(
        dealership=dealership, photo_uuid=photo_uuid
    )
    adapter = _get_default_adapter()
    upload_url, headers, expires_at = adapter.generate_upload_url(
        storage_key=storage_key,
        content_type=content_type,
        ttl_seconds=ttl_seconds,
    )
    return UploadTarget(
        method="PUT",
        upload_url=upload_url,
        storage_key=storage_key,
        required_headers=headers,
        expires_at=expires_at,
    )


# ---- Public: object existence + read URL --------------------------------


def object_exists(storage_key: str) -> bool:
    """Return ``True`` iff the object at ``storage_key`` currently
    exists on the storage backend.

    Uses HEAD only — never downloads. Returns ``False`` for missing
    objects. Raises :class:`ObjectStorageError` for backend faults
    (network, credentials, permissions).

    Re-validates ``storage_key`` against :data:`_KEY_PATTERN` before
    touching the backend — a caller with a malformed or forged key
    can never cross into the storage layer.
    """
    _validate_storage_key(storage_key)
    adapter = _get_default_adapter()
    return adapter.object_exists(storage_key)


def generate_read_url(
    *, storage_key: str, ttl_seconds: int = _DEFAULT_TTL_SECONDS
) -> str:
    """Return a short-lived signed URL a caller can use to read the
    object at ``storage_key``.

    In production (``_S3Adapter``): a real presigned S3 GET URL,
    valid for ``ttl_seconds`` (capped at :data:`_MAX_TTL_SECONDS`).
    In dev / test (``_LocalAdapter``): a
    :data:`LOCAL_READ_URL_MARKER`-prefixed marker string that the
    M3.5 / M3.7 UI must detect and resolve through an authenticated
    Django download route. **Do not hand a local-mode read URL to a
    browser as-is.**

    Re-validates ``storage_key`` against :data:`_KEY_PATTERN` before
    touching the backend.
    """
    _validate_storage_key(storage_key)
    _validate_ttl(ttl_seconds)
    adapter = _get_default_adapter()
    return adapter.generate_read_url(
        storage_key=storage_key, ttl_seconds=ttl_seconds
    )


# ---- Public re-exports ---------------------------------------------------


__all__ = [
    "InvalidContentTypeError",
    "InvalidStorageKeyError",
    "InvalidTTLError",
    "LOCAL_READ_URL_MARKER",
    "LOCAL_UPLOAD_URL_MARKER",
    "ObjectStorageError",
    "UploadTarget",
    "build_canonical_key",
    "generate_read_url",
    "generate_upload_target",
    "object_exists",
]
