"""Milestone 7 · Increment 3 (SESSION_090) — StageAgingSnapshot model shape.

Locks the persistence-layer contract for
:class:`dealer_ai.models.StageAgingSnapshot`:

- Fields exist with the right types + null/blank flags.
- Stage enum uses the M5 ``VEHICLE_STAGE_CHOICES`` vocabulary (no new
  stage values introduced at M7.3).
- Default ordering surfaces most-recent-first.
- Composite ``(dealership, stage, -snapshot_at)`` index registered.
- ``dealership`` FK cascades (M8 dashboards should NOT surface aging
  snapshots for deleted tenants; safer to lose the history than to
  render it under an orphaned label).
- Tenancy-carrier tuple extended 20 → 21.
"""

from __future__ import annotations

from django.db import models
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    VEHICLE_STAGE_CHOICES,
    VEHICLE_STAGE_FRONTLINE,
    Dealership,
    StageAgingSnapshot,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


class StageAgingSnapshotFieldShape(TestCase):
    """Field types + null/blank flags — the persistence contract."""

    def test_stage_char_with_vehicle_stage_choices(self):
        field = StageAgingSnapshot._meta.get_field("stage")
        self.assertIsInstance(field, models.CharField)
        self.assertEqual(field.max_length, 32)
        self.assertEqual(tuple(field.choices), VEHICLE_STAGE_CHOICES)

    def test_snapshot_at_datetime_indexed(self):
        field = StageAgingSnapshot._meta.get_field("snapshot_at")
        self.assertIsInstance(field, models.DateTimeField)
        self.assertTrue(field.db_index)
        # Not nullable — every row has a snapshot time by definition.
        self.assertFalse(field.null)

    def test_vehicle_count_is_positive_integer(self):
        field = StageAgingSnapshot._meta.get_field("vehicle_count")
        self.assertIsInstance(field, models.PositiveIntegerField)

    def test_p50_days_is_positive_integer(self):
        field = StageAgingSnapshot._meta.get_field("p50_days")
        self.assertIsInstance(field, models.PositiveIntegerField)

    def test_p90_days_is_positive_integer(self):
        field = StageAgingSnapshot._meta.get_field("p90_days")
        self.assertIsInstance(field, models.PositiveIntegerField)

    def test_dealership_fk_cascades(self):
        field = StageAgingSnapshot._meta.get_field("dealership")
        self.assertIsInstance(field, models.ForeignKey)
        # CASCADE (not SET_NULL like JobRunLog): aging snapshots have
        # no operator value once their tenant is gone.
        self.assertEqual(
            field.remote_field.on_delete.__name__, "CASCADE"
        )


class StageAgingSnapshotMetaContract(TestCase):
    """Default ordering + composite index."""

    def test_default_ordering_is_most_recent_first(self):
        self.assertEqual(
            tuple(StageAgingSnapshot._meta.ordering),
            ("-snapshot_at", "stage"),
        )

    def test_composite_tenant_stage_time_index_registered(self):
        index_names = {idx.name for idx in StageAgingSnapshot._meta.indexes}
        self.assertIn("sas_tenant_stage_time_idx", index_names)


class StageAgingSnapshotStrRepresentation(TestCase):
    """``__str__`` includes stage display, counts, and time."""

    def test_str_carries_stage_and_counts(self):
        default = Dealership.objects.get(slug="default")
        row = StageAgingSnapshot.objects.create(
            dealership=default,
            stage=VEHICLE_STAGE_FRONTLINE,
            snapshot_at=timezone.now(),
            vehicle_count=5,
            p50_days=3,
            p90_days=14,
        )
        rendered = str(row)
        self.assertIn("Frontline", rendered)
        self.assertIn("n=5", rendered)
        self.assertIn("p50=3d", rendered)
        self.assertIn("p90=14d", rendered)


class TenantCarrierExtension(TestCase):
    """M7.3 extended ``_TENANT_CARRIER_MODEL_NAMES`` 20 → 21."""

    def test_carrier_count_is_twenty_one(self):
        self.assertEqual(
            len(_TENANT_CARRIER_MODEL_NAMES),
            21,
            "Milestone 7 · Increment 3 extended the tenancy-carrier "
            "tuple from 20 → 21 (added StageAgingSnapshot).",
        )

    def test_stage_aging_snapshot_present(self):
        self.assertIn("StageAgingSnapshot", _TENANT_CARRIER_MODEL_NAMES)


class TenancyAutofillWiredForStageAgingSnapshot(TestCase):
    """The ``pre_save`` autofill signal covers ``StageAgingSnapshot``.

    Smoke test: a row saved without ``dealership=`` gets the default
    attached automatically. The verb writes ``dealership`` explicitly
    on every row, so this fallback is a safety net rather than the
    primary code path.
    """

    def test_stage_aging_snapshot_pre_save_autofills_default(self):
        default = Dealership.objects.get(slug="default")
        # Deliberately omit dealership= — the autofill safety net.
        row = StageAgingSnapshot(
            stage=VEHICLE_STAGE_FRONTLINE,
            snapshot_at=timezone.now(),
            vehicle_count=1,
            p50_days=0,
            p90_days=0,
        )
        row.save()
        row.refresh_from_db()
        self.assertEqual(row.dealership_id, default.pk)
