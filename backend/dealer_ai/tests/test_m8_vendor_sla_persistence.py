"""Milestone 8 · Increment 1 (SESSION_094) — M7.4 verb-extension tests.

Locks the M8.1 additive extension to
:func:`services.vendor_sla.detect_sla_breaches` — the verb now writes
one :class:`SlaBreachRecord` per detected breach in addition to the
existing ``logging.WARNING`` record.

Coverage:

- Every breach produces a row (in_progress + approved_stale kinds).
- Denormalized ``vehicle_stock`` + ``vendor_name`` populated from
  the M4 WorkOrder + Vendor at detection time.
- Idempotent — re-running the verb the same day posts zero new rows.
- Different day posts a new row (the daily-scan pattern).
- Cross-tenant — a scan of tenant A does not persist against tenant B.
- Empty tenant → zero rows written.
- Log stream still receives the WARNING (M7.4 contract preserved).
- ``breach_days`` captured matches the ``SlaBreach`` dataclass shape.
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    SLA_BREACH_KIND_APPROVED_STALE,
    SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA,
    SlaBreachRecord,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.vendor_sla import detect_sla_breaches


def _make_vehicle(dealership: Dealership, stock: str) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_vendor(
    dealership: Dealership, *, slug: str = "gp-body", name: str = "Great Plains Body"
) -> Vendor:
    return Vendor.objects.create(dealership=dealership, slug=slug, name=name)


class VerbPersistenceTests(TestCase):
    """Every M7.4 breach lands as an ``SlaBreachRecord`` row."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m8-persist", name="M8 Persist"
        )
        self.vendor = _make_vendor(self.dealership)
        self.today = dt.date(2026, 8, 15)

    def _make_in_progress_wo(
        self, *, stock: str, eta_offset_days: int
    ) -> WorkOrder:
        vehicle = _make_vehicle(self.dealership, stock)
        return WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            vendor=self.vendor,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=self.today - dt.timedelta(
                days=eta_offset_days
            ),
        )

    def _make_approved_stale_wo(
        self, *, stock: str, days_since_approval: int
    ) -> WorkOrder:
        vehicle = _make_vehicle(self.dealership, stock)
        approved_dt = timezone.make_aware(
            dt.datetime.combine(
                self.today - dt.timedelta(days=days_since_approval),
                dt.time(9, 0),
            )
        )
        return WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=self.dealership,
            vendor=self.vendor,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            status=WORK_ORDER_STATUS_APPROVED,
            approved_at=approved_dt,
        )

    def test_in_progress_breach_produces_record(self) -> None:
        wo = self._make_in_progress_wo(stock="IP-1", eta_offset_days=3)
        report = detect_sla_breaches(self.dealership, as_of=self.today)
        self.assertEqual(report.breach_count, 1)
        self.assertEqual(SlaBreachRecord.objects.count(), 1)
        row = SlaBreachRecord.objects.get()
        self.assertEqual(row.work_order_id, wo.pk)
        self.assertEqual(row.kind, SLA_BREACH_KIND_IN_PROGRESS_PAST_ETA)
        self.assertEqual(row.breach_days, 3)
        self.assertEqual(row.vehicle_stock, "IP-1")
        self.assertEqual(row.vendor_name, "Great Plains Body")
        self.assertEqual(row.dealership_id, self.dealership.pk)
        self.assertEqual(row.detected_at_date, self.today)

    def test_approved_stale_breach_produces_record(self) -> None:
        wo = self._make_approved_stale_wo(
            stock="AS-1", days_since_approval=10
        )
        report = detect_sla_breaches(self.dealership, as_of=self.today)
        self.assertEqual(report.breach_count, 1)
        self.assertEqual(SlaBreachRecord.objects.count(), 1)
        row = SlaBreachRecord.objects.get()
        self.assertEqual(row.work_order_id, wo.pk)
        self.assertEqual(row.kind, SLA_BREACH_KIND_APPROVED_STALE)
        self.assertEqual(row.breach_days, 10)

    def test_no_breach_writes_zero_rows(self) -> None:
        # Compliant WO — ETA in the future.
        self._make_in_progress_wo(stock="OK-1", eta_offset_days=-5)
        detect_sla_breaches(self.dealership, as_of=self.today)
        self.assertEqual(SlaBreachRecord.objects.count(), 0)

    def test_idempotent_same_day_rescan(self) -> None:
        self._make_in_progress_wo(stock="IP-2", eta_offset_days=2)
        detect_sla_breaches(self.dealership, as_of=self.today)
        detect_sla_breaches(self.dealership, as_of=self.today)
        detect_sla_breaches(self.dealership, as_of=self.today)
        # Same-day rescans collide on
        # (work_order, kind, detected_at_date) and get_or_create is a
        # no-op. Zero row growth after the first scan.
        self.assertEqual(SlaBreachRecord.objects.count(), 1)

    def test_different_day_adds_new_row(self) -> None:
        # Simulate the M7.4 daily Beat schedule — the same breach
        # detected on two separate calendar days should produce two
        # rows so M8.3 can see the pattern over time.
        self._make_in_progress_wo(stock="IP-3", eta_offset_days=2)
        detect_sla_breaches(self.dealership, as_of=self.today)
        detect_sla_breaches(
            self.dealership, as_of=self.today + dt.timedelta(days=1)
        )
        self.assertEqual(SlaBreachRecord.objects.count(), 2)
        # Row 2 captures the higher breach_days (one day older).
        rows = SlaBreachRecord.objects.order_by("detected_at_date")
        self.assertEqual([r.breach_days for r in rows], [2, 3])

    def test_cross_tenant_isolation(self) -> None:
        other = Dealership.objects.create(
            slug="m8-persist-other", name="M8 Persist Other"
        )
        other_vendor = _make_vendor(
            other, slug="other-body", name="Other Body"
        )
        other_vehicle = _make_vehicle(other, "OTHER-1")
        WorkOrder.objects.create(
            vehicle=other_vehicle,
            dealership=other,
            vendor=other_vendor,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=self.today - dt.timedelta(days=5),
        )
        # Also a breach for the primary tenant.
        self._make_in_progress_wo(stock="MINE-1", eta_offset_days=3)

        detect_sla_breaches(self.dealership, as_of=self.today)

        # Only the primary tenant's breach got materialized. The
        # other tenant's WO is untouched.
        rows = SlaBreachRecord.objects.all()
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.get().dealership_id, self.dealership.pk)

    def test_log_warning_still_emitted(self) -> None:
        # M7.4 contract preserved — the log stream continues to
        # receive one WARNING per breach even after the M8.1
        # materialization extension.
        self._make_in_progress_wo(stock="LOG-1", eta_offset_days=1)
        with self.assertLogs(
            "dealer_ai.vendor_sla.detection", level=logging.WARNING
        ) as caplog:
            detect_sla_breaches(self.dealership, as_of=self.today)
        self.assertTrue(
            any(
                "vendor_sla.breach kind=in_progress_past_eta" in msg
                for msg in caplog.output
            ),
            caplog.output,
        )
        # And the row still lands.
        self.assertEqual(SlaBreachRecord.objects.count(), 1)

    def test_empty_tenant_writes_nothing(self) -> None:
        detect_sla_breaches(self.dealership, as_of=self.today)
        self.assertEqual(SlaBreachRecord.objects.count(), 0)
