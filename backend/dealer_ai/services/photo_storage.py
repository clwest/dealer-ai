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


@dataclass(frozen=True)
class ObjectMetadata:
    """Provider-neutral HEAD / stat result for a single storage object.

    Returned by :func:`get_object_metadata`. Used by M3.5's
    ``attach_photo`` to authoritatively verify what actually landed
    on the storage backend against what the client claimed:

    - ``content_type`` MUST match the value declared at
      ``request_photo_upload`` time.
    - ``size_bytes`` MUST match the value declared at
      ``attach_photo`` time.

    ``exists`` is always ``True`` for a returned instance — a missing
    object surfaces as :class:`InvalidStorageKeyError`-adjacent
    behavior (see :func:`get_object_metadata` for the exact
    contract). The field is included so callers can compose calls
    across adapters uniformly, and so future extensions (e.g.
    tombstone semantics) don't require signature changes.

    ``etag`` is intentionally NOT part of the public contract.
    S3 exposes an ETag; local FS does not. If a future caller
    genuinely needs checksum verification (as opposed to size + type
    verification), that is a separate design memo.
    """

    content_type: str
    size_bytes: int
    exists: bool


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

    def get_object_metadata(self, storage_key: str) -> ObjectMetadata:
        """Return provider-neutral HEAD metadata for a stored object.

        Missing objects surface as :class:`InvalidStorageKeyError`
        raised by :func:`get_object_metadata` (the public function)
        — adapters raise :class:`ObjectStorageError` for backend
        faults but a specific sentinel result for
        "object legitimately does not exist" so the public function
        can translate it. Adapters return ``ObjectMetadata(exists=False,
        content_type='', size_bytes=0)`` for missing objects; the
        public function decides whether to raise or return the
        sentinel."""

    def delete_object(self, storage_key: str) -> None:
        """Best-effort delete. Already-missing = success (idempotent).
        Real backend faults raise :class:`ObjectStorageError`.

        Per M3.5 delete strategy: this runs BEFORE the DB row
        deletion, so the caller can retain the row and surface the
        error if delete fails for a real reason (not "not found")."""


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

    def get_object_metadata(self, storage_key: str) -> ObjectMetadata:
        storage = storages["condition_photos"]
        try:
            if not storage.exists(storage_key):
                return ObjectMetadata(
                    content_type="", size_bytes=0, exists=False
                )
            size = storage.size(storage_key)
        except OSError as exc:
            raise ObjectStorageError(
                f"Local storage stat failed for {storage_key!r}: {exc}"
            ) from exc
        # FileSystemStorage doesn't record content type — it lives on
        # the wire, not on disk. Read from the ``.content_type``
        # sidecar file written by :meth:`store_local_upload` (see
        # its docstring for the sidecar-file rationale).
        content_type = self._read_content_type_sidecar(storage_key)
        return ObjectMetadata(
            content_type=content_type, size_bytes=size, exists=True
        )

    def delete_object(self, storage_key: str) -> None:
        storage = storages["condition_photos"]
        try:
            # ``FileSystemStorage.delete`` silently no-ops on missing
            # files (Django convention). Explicit `.exists()` guard
            # keeps behavior identical to S3's delete_object contract:
            # already-missing = success (idempotent).
            if storage.exists(storage_key):
                storage.delete(storage_key)
            # Sidecar file (see store_local_upload) — delete if
            # present, ignore if not.
            sidecar_key = self._content_type_sidecar_key(storage_key)
            if storage.exists(sidecar_key):
                storage.delete(sidecar_key)
        except OSError as exc:
            raise ObjectStorageError(
                f"Local storage delete failed for {storage_key!r}: {exc}"
            ) from exc

    # ---- Local-only helpers (not part of _PhotoStorageAdapter) --------

    def store_local_upload(
        self,
        *,
        storage_key: str,
        content_type: str,
        data: bytes,
    ) -> ObjectMetadata:
        """Write bytes directly into local ``condition_photos`` storage.

        Local-mode substitute for a real browser-to-S3 PUT. The M3.6
        API endpoint (later increment) will invoke this when it
        detects the ``LOCAL_UPLOAD_URL_MARKER`` prefix in a presigned
        "URL" returned by :func:`generate_upload_target`.

        Writes the object body to ``storage_key`` and a companion
        content-type sidecar file to ``<key>.content-type`` so
        :meth:`get_object_metadata` can round-trip the content type
        (FileSystemStorage does not record content type on disk).
        The sidecar is an implementation detail of the local adapter
        only — S3 stores content type on the object itself.
        """
        storage = storages["condition_photos"]
        from django.core.files.base import ContentFile

        try:
            # Overwrite semantics: writing to the same key twice
            # replaces the first. FileSystemStorage's default is to
            # append a suffix on collision — use `.delete()` first
            # to force replacement (idempotent write per canonical
            # key).
            if storage.exists(storage_key):
                storage.delete(storage_key)
            sidecar_key = self._content_type_sidecar_key(storage_key)
            if storage.exists(sidecar_key):
                storage.delete(sidecar_key)
            storage.save(storage_key, ContentFile(data))
            storage.save(sidecar_key, ContentFile(content_type.encode()))
        except OSError as exc:
            raise ObjectStorageError(
                f"Local storage write failed for {storage_key!r}: {exc}"
            ) from exc
        return ObjectMetadata(
            content_type=content_type,
            size_bytes=len(data),
            exists=True,
        )

    @staticmethod
    def _content_type_sidecar_key(storage_key: str) -> str:
        return f"{storage_key}.content-type"

    def _read_content_type_sidecar(self, storage_key: str) -> str:
        storage = storages["condition_photos"]
        sidecar_key = self._content_type_sidecar_key(storage_key)
        if not storage.exists(sidecar_key):
            # Object exists but sidecar missing — either the object
            # was placed by hand (dev tinkering) or store_local_upload
            # was bypassed. Return empty string so callers can detect
            # the missing sidecar via the equality check in
            # ``attach_photo`` and raise the standard mismatch error.
            return ""
        try:
            with storage.open(sidecar_key, "rb") as f:
                return f.read().decode("utf-8", errors="replace")
        except OSError as exc:
            raise ObjectStorageError(
                f"Local storage sidecar read failed for {storage_key!r}: {exc}"
            ) from exc


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

    def get_object_metadata(self, storage_key: str) -> ObjectMetadata:
        client = self._boto3_client()
        try:
            response = client.head_object(
                Bucket=self._bucket, Key=storage_key
            )
        except botocore.exceptions.ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return ObjectMetadata(
                    content_type="", size_bytes=0, exists=False
                )
            raise ObjectStorageError(
                f"S3 HEAD metadata failed for {storage_key!r}: {exc}"
            ) from exc
        except botocore.exceptions.BotoCoreError as exc:
            raise ObjectStorageError(
                f"S3 HEAD metadata failed for {storage_key!r}: {exc}"
            ) from exc
        return ObjectMetadata(
            content_type=response.get("ContentType", ""),
            size_bytes=int(response.get("ContentLength", 0)),
            exists=True,
        )

    def delete_object(self, storage_key: str) -> None:
        client = self._boto3_client()
        try:
            # S3's DeleteObject is idempotent by contract — returns 204
            # whether the key existed or not. AccessDenied etc. raise.
            client.delete_object(Bucket=self._bucket, Key=storage_key)
        except botocore.exceptions.ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchKey", "NotFound"):
                return  # already-missing = idempotent success
            raise ObjectStorageError(
                f"S3 delete failed for {storage_key!r}: {exc}"
            ) from exc
        except botocore.exceptions.BotoCoreError as exc:
            raise ObjectStorageError(
                f"S3 delete failed for {storage_key!r}: {exc}"
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


# ---- Public: canonical key parser (M3.5) ---------------------------------


# Group-captured version of _KEY_PATTERN. Anchored + named groups so
# the parser returns typed values without positional confusion.
_KEY_PATTERN_GROUPED = re.compile(
    r"^dealerships/(?P<slug>[-a-zA-Z0-9_]+)/condition-findings/"
    r"(?P<photo_uuid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"/original$"
)


def parse_canonical_key(storage_key: str) -> tuple[str, uuid.UUID]:
    """Return ``(dealership_slug, photo_uuid)`` for a canonical key.

    The only place condition-report service code should touch the key
    format. Callers that need the UUID (M3.5's ``attach_photo``) go
    through here so no regex or string-slicing lives in
    ``services/condition_report.py``.

    Raises :class:`InvalidStorageKeyError` on any mismatch — same
    defense-in-depth guard as :func:`object_exists` and
    :func:`generate_read_url` use.
    """
    if not isinstance(storage_key, str):
        raise InvalidStorageKeyError(
            f"storage_key must be a str, got {type(storage_key).__name__}."
        )
    match = _KEY_PATTERN_GROUPED.match(storage_key)
    if match is None:
        raise InvalidStorageKeyError(
            f"storage_key {storage_key!r} does not match the canonical "
            f"pattern; cannot extract dealership slug + photo UUID."
        )
    slug = match.group("slug")
    try:
        parsed_uuid = uuid.UUID(match.group("photo_uuid"))
    except (ValueError, TypeError) as exc:
        # Regex enforces the UUID shape so this should be unreachable;
        # kept for defense-in-depth if the pattern is ever loosened.
        raise InvalidStorageKeyError(
            f"storage_key {storage_key!r} carries an unparseable UUID "
            f"segment: {exc}."
        ) from exc
    return slug, parsed_uuid


# ---- Public: object metadata + delete (M3.5) -----------------------------


def get_object_metadata(storage_key: str) -> ObjectMetadata:
    """Return provider-neutral HEAD metadata for a stored object.

    Missing objects surface as an :class:`ObjectMetadata` with
    ``exists=False`` rather than a raised exception — the caller
    (M3.5's ``attach_photo``) needs to distinguish "not yet uploaded"
    from "backend fault" and raise the correct domain error.

    Re-validates ``storage_key`` against :data:`_KEY_PATTERN` before
    touching the backend.

    :class:`ObjectStorageError` still raises for real backend faults
    (auth failure, network, permissions).
    """
    _validate_storage_key(storage_key)
    adapter = _get_default_adapter()
    return adapter.get_object_metadata(storage_key)


def delete_object(storage_key: str) -> None:
    """Delete the object at ``storage_key`` from the storage backend.

    Idempotent — already-missing = success. Real backend failures
    raise :class:`ObjectStorageError`; the caller (M3.5's
    ``delete_photo``) must retain the DB row in that case so the
    storage object doesn't get silently orphaned.

    Re-validates ``storage_key`` before touching the backend.
    """
    _validate_storage_key(storage_key)
    adapter = _get_default_adapter()
    adapter.delete_object(storage_key)


# ---- Public: local-mode upload helper (dev / test only) ----------------


# Reasonable ceiling for local uploads. Real photos are typically
# 1–10 MB; HEIC can reach ~15 MB. 25 MB is a soft ceiling that flags
# runaway inputs without blocking legitimate photos. Not configurable
# in v1 — bump deliberately if operator evidence surfaces a case.
_LOCAL_UPLOAD_MAX_BYTES = 25 * 1024 * 1024


class LocalUploadNotAvailableError(RuntimeError):
    """Raised when :func:`store_local_upload` is invoked against a
    non-local adapter (i.e. production S3 mode). This is a caller
    bug — production uploads must go through the presigned PUT URL
    generated by :func:`generate_upload_target`, not through this
    helper.

    Distinct from :class:`ObjectStorageError` (backend fault): this
    is a configuration / routing error, not a storage failure.
    """


def store_local_upload(
    *,
    storage_key: str,
    content_type: str,
    data: bytes,
) -> ObjectMetadata:
    """Write ``data`` directly into the local ``condition_photos``
    storage under ``storage_key``.

    Local-mode substitute for a real browser-to-S3 PUT. The M3.6
    upload endpoint (later increment) will call this when it detects
    the :data:`LOCAL_UPLOAD_URL_MARKER` prefix in a presigned "URL."

    Requirements enforced here (defense-in-depth around whatever the
    caller checked):

    - Active adapter MUST be :class:`_LocalAdapter`
      (:class:`LocalUploadNotAvailableError` otherwise).
    - ``storage_key`` MUST match the canonical pattern.
    - ``content_type`` MUST be in the M3.1 whitelist.
    - ``len(data)`` MUST be > 0 and ≤ :data:`_LOCAL_UPLOAD_MAX_BYTES`.

    Never accepts arbitrary filesystem paths — the storage key is
    the ONLY path input, and it's regex-validated. There is no
    ``file_path=`` or ``upload_from=`` parameter and there never
    should be.
    """
    _validate_storage_key(storage_key)
    _validate_content_type(content_type)
    if not isinstance(data, (bytes, bytearray)):
        raise InvalidStorageKeyError(
            f"data must be bytes, got {type(data).__name__}."
        )
    size = len(data)
    if size == 0:
        raise InvalidStorageKeyError(
            "Refusing to store zero-byte local upload."
        )
    if size > _LOCAL_UPLOAD_MAX_BYTES:
        raise InvalidStorageKeyError(
            f"Local upload size {size} exceeds the "
            f"{_LOCAL_UPLOAD_MAX_BYTES}-byte ceiling."
        )
    adapter = _get_default_adapter()
    if not isinstance(adapter, _LocalAdapter):
        raise LocalUploadNotAvailableError(
            "store_local_upload is only available when the "
            "condition_photos storage backend is FileSystemStorage. "
            "Production uploads must use the presigned PUT URL "
            "returned by generate_upload_target."
        )
    return adapter.store_local_upload(
        storage_key=storage_key, content_type=content_type, data=bytes(data)
    )


# ---- Public re-exports ---------------------------------------------------


__all__ = [
    "InvalidContentTypeError",
    "InvalidStorageKeyError",
    "InvalidTTLError",
    "LOCAL_READ_URL_MARKER",
    "LOCAL_UPLOAD_URL_MARKER",
    "LocalUploadNotAvailableError",
    "ObjectMetadata",
    "ObjectStorageError",
    "UploadTarget",
    "build_canonical_key",
    "delete_object",
    "generate_read_url",
    "generate_upload_target",
    "get_object_metadata",
    "object_exists",
    "parse_canonical_key",
    "store_local_upload",
]
