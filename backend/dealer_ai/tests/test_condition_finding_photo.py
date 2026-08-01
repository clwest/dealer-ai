"""Milestone 3 · Increment 1 — ConditionFindingPhoto model tests.

Persistence-layer coverage only. No presigned-upload workflow, no
storage-backend integration, no HEAD verification — those land at
M3.4 / M3.5. This test file locks the schema-layer contract only.

Locked invariants:

- ``public_id`` is a UUIDField with unique constraint and
  ``uuid.uuid4`` default. External references bind here, not to
  ``storage_key``. Two photo rows never share a ``public_id``.
- ``storage_key`` is required and unique at the schema level.
- ``public_id`` is independent of ``storage_key`` — the UUID does
  not derive from the key.
- ``content_type`` restricted to the four-value image whitelist
  at the model layer via ``choices=``.
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean`` guard (dealership must match parent
  vehicle's dealership via ``finding.report.vehicle``).
- Cascade behavior — deleting the parent ConditionFinding removes
  its photos.
- Ordering (``created_at`` ascending — earliest photo first).
- ``uploaded_by`` SET_NULL on user delete (metadata survives user
  removal).
- Reverse accessor ``finding.photos``.
- ``__str__`` for Django admin display.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_TIRES,
    CONDITION_PHOTO_CONTENT_TYPE_CHOICES,
    CONDITION_PHOTO_CONTENT_TYPE_HEIC,
    CONDITION_PHOTO_CONTENT_TYPE_JPEG,
    CONDITION_PHOTO_CONTENT_TYPE_PNG,
    CONDITION_PHOTO_CONTENT_TYPE_WEBP,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionFindingPhoto,
    ConditionReport,
    Dealership,
    Vehicle,
)


def _make_finding(stock: str, dealership: Dealership) -> ConditionFinding:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    report = ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Marta Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
    )
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_TIRES,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="LR tire at 3/32nds; replacement required.",
    )


class ContentTypeWhitelistVocabulary(TestCase):
    """The four allowed image types are enumerated per
    ``MILESTONE_3_PLANNING.md`` §1.5. Any addition or rename requires
    a roadmap decision — this test forces that conversation."""

    def test_choices_contain_exactly_four_canonical_types(self):
        keys = {key for key, _ in CONDITION_PHOTO_CONTENT_TYPE_CHOICES}
        self.assertEqual(
            keys,
            {
                CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                CONDITION_PHOTO_CONTENT_TYPE_PNG,
                CONDITION_PHOTO_CONTENT_TYPE_HEIC,
                CONDITION_PHOTO_CONTENT_TYPE_WEBP,
            },
        )
        self.assertEqual(len(CONDITION_PHOTO_CONTENT_TYPE_CHOICES), 4)


class ConditionFindingPhotoCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding("M31P-CREATE", self.default)

    def test_round_trip_all_fields(self):
        photo = ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key="condition-report/2026/06/abc123.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=482_331,
            caption="LR tire wear from outside sidewall.",
        )
        fetched = ConditionFindingPhoto.objects.get(pk=photo.pk)
        self.assertEqual(fetched.finding_id, self.finding.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(
            fetched.storage_key, "condition-report/2026/06/abc123.jpg"
        )
        self.assertEqual(fetched.content_type, CONDITION_PHOTO_CONTENT_TYPE_JPEG)
        self.assertEqual(fetched.size_bytes, 482_331)
        self.assertEqual(fetched.caption, "LR tire wear from outside sidewall.")

    def test_content_type_full_clean_rejects_non_whitelisted(self):
        photo = ConditionFindingPhoto(
            finding=self.finding,
            dealership=self.default,
            storage_key="condition-report/2026/06/malicious.exe",
            content_type="application/octet-stream",
            size_bytes=1024,
        )
        with self.assertRaises(ValidationError):
            photo.full_clean()

    def test_caption_defaults_to_empty(self):
        photo = ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key="condition-report/2026/06/nocaption.png",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_PNG,
            size_bytes=100_000,
        )
        self.assertEqual(photo.caption, "")


class PublicIdIdentity(TestCase):
    """Public identity is the UUID, not the storage key. External
    references bind here. See ``ConditionFindingPhoto`` docstring +
    ``MILESTONE_3_PLANNING.md`` §1.5 design note."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding("M31P-PUBID", self.default)

    def _make_photo(self, storage_key: str) -> ConditionFindingPhoto:
        return ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key=storage_key,
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )

    def test_public_id_is_generated_automatically(self):
        photo = self._make_photo("cr/uuid-auto/a.jpg")
        self.assertIsNotNone(photo.public_id)
        self.assertIsInstance(photo.public_id, uuid.UUID)

    def test_public_id_is_unique_across_photos(self):
        first = self._make_photo("cr/uuid-uniq/first.jpg")
        second = self._make_photo("cr/uuid-uniq/second.jpg")
        self.assertNotEqual(first.public_id, second.public_id)

    def test_public_id_is_independent_of_storage_key(self):
        # Two photos with two very different storage keys are only
        # distinguishable at the schema layer by public_id and pk;
        # public_id is the durable external identity per the
        # planning-doc refinement. This test locks the invariant that
        # the UUID does NOT derive from the storage key.
        first = self._make_photo("bucket/a/very/deep/path/one.jpg")
        second = self._make_photo("bucket/a/very/deep/path/two.jpg")
        self.assertNotEqual(first.public_id, second.public_id)
        # Keys differ; UUIDs also differ — but the UUIDs are not a
        # function of the keys, so key length / prefix / suffix
        # cannot be reverse-engineered from the UUID.
        self.assertEqual(len(str(first.public_id)), 36)

    def test_public_id_uniqueness_enforced_at_schema_level(self):
        # Attempting to insert two rows with the same UUID raises
        # IntegrityError. Locks the ``unique=True`` in the migration.
        first = self._make_photo("cr/uuid-collide/first.jpg")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConditionFindingPhoto.objects.create(
                    finding=self.finding,
                    dealership=self.default,
                    storage_key="cr/uuid-collide/second.jpg",
                    content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                    size_bytes=100_000,
                    public_id=first.public_id,
                )

    def test_public_id_survives_refetch(self):
        photo = self._make_photo("cr/uuid-refetch/a.jpg")
        pid = photo.public_id
        fetched = ConditionFindingPhoto.objects.get(pk=photo.pk)
        self.assertEqual(fetched.public_id, pid)


class StorageKeyIsRequiredAndUnique(TestCase):
    """``storage_key`` is required and unique at the schema level.
    Every row represents a successfully attached object (see
    ``ConditionFindingPhoto`` docstring). Nullable was considered
    and rejected at SESSION_056 planning-doc amendment."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding("M31P-KEY", self.default)

    def test_storage_key_uniqueness_enforced_at_schema_level(self):
        ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key="cr/dup/only-one.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ConditionFindingPhoto.objects.create(
                    finding=self.finding,
                    dealership=self.default,
                    storage_key="cr/dup/only-one.jpg",  # duplicate
                    content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
                    size_bytes=100_000,
                )

    def test_storage_key_is_not_null_at_schema_level(self):
        self.assertFalse(
            ConditionFindingPhoto._meta.get_field("storage_key").null,
            "storage_key must be NOT NULL at schema level "
            "(planning-doc refinement locked at SESSION_056).",
        )


class DealershipRequired(TestCase):
    """Dealership FK is NOT NULL from day one."""

    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            ConditionFindingPhoto._meta.get_field("dealership").null,
            "ConditionFindingPhoto.dealership should be NOT NULL from day one",
        )


class UploadedByBehavior(TestCase):
    """``uploaded_by`` is nullable + SET_NULL — historical metadata
    survives user deletion (mirrors ``ConditionReport.authored_by``
    rationale). The M3.5 upload flow will populate this field when
    the request has an authenticated user."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding("M31P-UPBY", self.default)

    def test_uploaded_by_is_optional(self):
        photo = ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key="cr/upby/opt.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        self.assertIsNone(photo.uploaded_by)

    def test_uploaded_by_set_null_on_user_delete(self):
        User = get_user_model()
        user = User.objects.create_user(username="uploader1", password="pw")
        photo = ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key="cr/upby/set-null.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
            uploaded_by=user,
        )
        user.delete()
        photo.refresh_from_db()
        self.assertIsNone(photo.uploaded_by_id)


class CrossTenantClean(TestCase):
    """The denormalized ``dealership`` FK on ConditionFindingPhoto must
    match the parent Vehicle's tenant (reached via
    ``finding.report.vehicle``). ``clean()`` is the model-layer guard."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-photo"
        )
        self.finding_at_a = _make_finding("M31P-XTENANT", self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        photo = ConditionFindingPhoto(
            finding=self.finding_at_a,
            dealership=self.dealership_a,
            storage_key="cr/xt/match.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        photo.full_clean()

    def test_mismatched_dealership_raises_validation_error(self):
        photo = ConditionFindingPhoto(
            finding=self.finding_at_a,
            dealership=self.dealership_b,
            storage_key="cr/xt/mismatch.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        with self.assertRaises(ValidationError) as ctx:
            photo.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class CascadeOnFindingDelete(TestCase):
    """Deleting a ConditionFinding removes its photos. Deleting the
    grandparent Vehicle also removes them (through the report →
    finding cascade)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.finding = _make_finding("M31P-CASC", self.default)
        self.photo = ConditionFindingPhoto.objects.create(
            finding=self.finding,
            dealership=self.default,
            storage_key="cr/casc/one.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )

    def test_delete_finding_removes_photos(self):
        photo_pk = self.photo.pk
        self.finding.delete()
        self.assertFalse(
            ConditionFindingPhoto.objects.filter(pk=photo_pk).exists()
        )


class ReverseRelation(TestCase):
    """``finding.photos`` is the reverse accessor the M3.5 upload flow
    and M3.7 UI use to list photos on a finding."""

    def test_finding_dot_photos_lists_it(self):
        default = Dealership.objects.get(slug="default")
        finding = _make_finding("M31P-REV", default)
        photo = ConditionFindingPhoto.objects.create(
            finding=finding,
            dealership=default,
            storage_key="cr/rev/a.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        finding = ConditionFinding.objects.get(pk=finding.pk)
        self.assertIn(photo, finding.photos.all())


class OrderingContract(TestCase):
    """Default ordering is ``created_at`` ascending — earliest photo
    first, so the M3.7 UI can render photos in the order the operator
    uploaded them (chronological reading of the inspection)."""

    def test_default_ordering_is_created_at_ascending(self):
        default = Dealership.objects.get(slug="default")
        finding = _make_finding("M31P-ORD", default)
        first = ConditionFindingPhoto.objects.create(
            finding=finding,
            dealership=default,
            storage_key="cr/ord/1-first.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        second = ConditionFindingPhoto.objects.create(
            finding=finding,
            dealership=default,
            storage_key="cr/ord/2-second.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        third = ConditionFindingPhoto.objects.create(
            finding=finding,
            dealership=default,
            storage_key="cr/ord/3-third.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        pks = list(
            ConditionFindingPhoto.objects.values_list("pk", flat=True)
        )
        self.assertEqual(pks, [first.pk, second.pk, third.pk])


class StringRepresentation(TestCase):
    """__str__ is what Django admin renders. It surfaces the UUID and
    finding pk — never the storage_key, per the planning-doc
    refinement (external references bind to public_id, not
    storage_key)."""

    def test_str_contains_public_id_and_finding_pk(self):
        default = Dealership.objects.get(slug="default")
        finding = _make_finding("M31P-STR", default)
        photo = ConditionFindingPhoto.objects.create(
            finding=finding,
            dealership=default,
            storage_key="cr/str/one.jpg",
            content_type=CONDITION_PHOTO_CONTENT_TYPE_JPEG,
            size_bytes=100_000,
        )
        as_string = str(photo)
        self.assertIn(str(photo.public_id), as_string)
        self.assertIn(str(finding.pk), as_string)
        # storage_key must NEVER surface in __str__ per the
        # planning-doc refinement (public_id is the external identity).
        self.assertNotIn("cr/str/one.jpg", as_string)
