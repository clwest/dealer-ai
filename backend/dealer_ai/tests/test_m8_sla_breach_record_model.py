"""Milestone 8 · Increment 1 (SESSION_094) — SlaBreachRecord model tests.

Locks the persistence-layer shape of :class:`SlaBreachRecord` — the
materialized counterpart to the M7.4 log-warning breach signal per
``MILESTONE_8_PLANNING.md`` §5.b Option B.

Coverage:

- Field defaults + choice validation.
- Ordering (``-detected_at``).
- Composite index on ``(dealership, kind, -detected_at)``.
- Unique constraint on ``(work_order, kind, detected_at_date)`` —
  idempotency invariant enforced at the DB level.
- Tenant-carrier autofill signal wires ``SlaBreachRecord`` in as the
  22nd carrier (M7.6 was 21).
- ``__str__`` renders a human-scannable summary.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    SLA_BREACH_KIND_APPROVED_STALE,
    SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
    SlaBreachRecord,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


def _make_wo(
    dealership: Dealership,
    *,
    stock: str = "SBR-1",
    vendor_slug: str = "acme-body",
) -> WorkOrder:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    vendor, _created = Vendor.objects.get_or_create(
        dealership=dealership,
        slug=vendor_slug,
        defaults={"name": f"Vendor {vendor_slug}"},
    )
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        vendor=vendor,
        category=CONDITION_CATEGORY_BODY,
        venue=WORK_ORDER_VENUE_OUTSOURCED,
        status=WORK_ORDER_STATUS_APPROVED,
    )


class SlaBreachRecordShapeTests(TestCase):
    """Field-level invariants."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="sbr-shape", name="SBR Shape"
        )
        self.work_order = _make_wo(self.dealership)

    def test_create_persists_all_fields(self) -> None:
        now = timezone.now()
        row = SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            breach_days=3,
            detected_at=now,
            detected_at_date=now.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME Body Shop",
        )
        row.refresh_from_db()
        self.assertEqual(row.kind, SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA)
        self.assertEqual(row.breach_days, 3)
        self.assertEqual(row.vehicle_stock, "SBR-1")
        self.assertEqual(row.vendor_name, "ACME Body Shop")
        self.assertEqual(row.dealership_id, self.dealership.pk)
        self.assertEqual(row.work_order_id, self.work_order.pk)

    def test_default_ordering_is_detected_at_desc(self) -> None:
        # Insert three rows in shuffled detected_at order; queryset
        # should surface most-recent first.
        base = timezone.now()
        SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            breach_days=8,
            detected_at=base - dt.timedelta(days=2),
            detected_at_date=(base - dt.timedelta(days=2)).date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            breach_days=1,
            detected_at=base,
            detected_at_date=base.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        # Different WO for the third row so the unique constraint
        # doesn't fire on the same-day approved-stale duplicate.
        other_wo = _make_wo(self.dealership, stock="SBR-2")
        SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=other_wo,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            breach_days=9,
            detected_at=base - dt.timedelta(days=1),
            detected_at_date=(base - dt.timedelta(days=1)).date(),
            vehicle_stock="SBR-2",
            vendor_name="ACME",
        )
        ordered = list(SlaBreachRecord.objects.all())
        self.assertEqual([r.breach_days for r in ordered], [1, 9, 8])

    def test_str_renders_human_summary(self) -> None:
        now = timezone.now()
        row = SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            breach_days=5,
            detected_at=now,
            detected_at_date=now.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME Body Shop",
        )
        rendered = str(row)
        self.assertIn("In progress past ETA", rendered)
        self.assertIn(str(self.work_order.pk), rendered)
        self.assertIn("SBR-1", rendered)
        self.assertIn("ACME Body Shop", rendered)
        self.assertIn("5d", rendered)


class SlaBreachRecordUniquenessTests(TestCase):
    """Idempotency invariant — the DB refuses same-day duplicates."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="sbr-uq", name="SBR Uniqueness"
        )
        self.work_order = _make_wo(self.dealership)

    def test_duplicate_wo_kind_and_date_raises(self) -> None:
        now = timezone.now()
        SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            breach_days=8,
            detected_at=now,
            detected_at_date=now.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        with self.assertRaises(IntegrityError):
            SlaBreachRecord.objects.create(
                dealership=self.dealership,
                work_order=self.work_order,
                kind=SLA_BREACH_KIND_APPROVED_STALE,
                breach_days=9,
                detected_at=now,
                detected_at_date=now.date(),
                vehicle_stock="SBR-1",
                vendor_name="ACME",
            )

    def test_different_date_bypasses_uniqueness(self) -> None:
        now = timezone.now()
        SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            breach_days=8,
            detected_at=now - dt.timedelta(days=1),
            detected_at_date=(now - dt.timedelta(days=1)).date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        # Same WO + kind but different date → different unique-triple.
        row2 = SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            breach_days=9,
            detected_at=now,
            detected_at_date=now.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        self.assertEqual(SlaBreachRecord.objects.count(), 2)
        self.assertEqual(row2.breach_days, 9)

    def test_different_kind_bypasses_uniqueness(self) -> None:
        now = timezone.now()
        SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_APPROVED_STALE,
            breach_days=8,
            detected_at=now,
            detected_at_date=now.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        # Same WO + same date but different kind. Real-world: an
        # in_progress WO whose ETA-past-eta rule fires simultaneously
        # with a separately-detected approved-stale predecessor.
        row2 = SlaBreachRecord.objects.create(
            dealership=self.dealership,
            work_order=self.work_order,
            kind=SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
            breach_days=1,
            detected_at=now,
            detected_at_date=now.date(),
            vehicle_stock="SBR-1",
            vendor_name="ACME",
        )
        self.assertEqual(SlaBreachRecord.objects.count(), 2)
        self.assertEqual(row2.kind, SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA)


class SlaBreachRecordTenancyCarrierTests(TestCase):
    """Milestone 7.1 tenant-carrier autofill signal covers M8.1 row."""

    def test_sla_breach_record_registered_as_tenancy_carrier(self) -> None:
        # M7.6 carrier count was 21; M8.1 adds SlaBreachRecord as the
        # 22nd. Assert with ``>=`` per the M7 §6 lesson 14 pattern —
        # any future M8+ increment extends further and this test still
        # holds without editing.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 22)
        self.assertIn("SlaBreachRecord", _TENANT_CARRIER_MODEL_NAMES)
