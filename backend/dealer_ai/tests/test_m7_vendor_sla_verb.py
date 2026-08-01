"""Milestone 7 · Increment 4 (SESSION_091) — vendor-SLA detection verb tests.

Locks the behavior of
:func:`services.vendor_sla.detect_sla_breaches`:

- Empty tenant returns an empty report.
- In-progress past ETA is flagged with grace-day = 0 semantics.
- Approved-stale is flagged only past the 7-day threshold.
- ``venue='in_house'`` WOs are NOT scanned (scope confirmed at
  SESSION_091 open).
- ``status`` outside ``{approved, in_progress}`` is NOT scanned.
- Missing ``estimated_completion_date`` on in_progress does NOT breach
  (data-quality issue, not SLA breach).
- Missing ``approved_at`` on approved does NOT breach (data-integrity).
- Cross-tenant isolation.
- Verb emits ``logging.WARNING`` records per breach.
- ``as_of`` defaults to today; explicit ``as_of`` honored.
- Return value shape (``breach_count``, per-kind counts).
"""

from __future__ import annotations

import datetime as dt
import logging
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_IN_HOUSE,
    WORK_ORDER_VENUE_OUTSOURCED,
    Dealership,
    Vehicle,
    Vendor,
    WorkOrder,
)
from dealer_ai.services.vendor_sla import (
    APPROVED_STALE_THRESHOLD_DAYS,
    IN_PROGRESS_ETA_GRACE_DAYS,
    SlaBreach,
    SlaBreachReport,
    detect_sla_breaches,
)
from dealer_ai.services.vendor_sla.detection import (
    BREACH_KIND_APPROVED_STALE,
    BREACH_KIND_IN_PROGRESS_PAST_ETA,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_vendor(dealership: Dealership, slug: str) -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"Vendor {slug}",
        slug=slug,
    )


def _make_wo(
    *,
    dealership: Dealership,
    vehicle: Vehicle,
    vendor: Vendor,
    status: str,
    venue: str = WORK_ORDER_VENUE_OUTSOURCED,
    approved_at: dt.datetime | None = None,
    estimated_completion_date: dt.date | None = None,
) -> WorkOrder:
    """Direct ORM create — bypasses the M4.2 service so tests can pin
    exact provenance values without threading through state
    transitions."""
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_BODY,
        venue=venue,
        vendor=vendor if venue == WORK_ORDER_VENUE_OUTSOURCED else None,
        status=status,
        approved_at=approved_at,
        estimated_completion_date=estimated_completion_date,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class PolicyConstantsLocked(TestCase):
    """The three thresholds confirmed at SESSION_091 open."""

    def test_approved_stale_is_seven_days(self):
        self.assertEqual(APPROVED_STALE_THRESHOLD_DAYS, 7)

    def test_in_progress_grace_is_zero_days(self):
        self.assertEqual(IN_PROGRESS_ETA_GRACE_DAYS, 0)


class EmptyTenantReturnsEmptyReport(TestCase):
    """No WOs → no breaches, and no error."""

    def test_empty_tenant_returns_empty_report(self):
        empty = Dealership.objects.create(name="Empty", slug="empty-t")
        report = detect_sla_breaches(empty)
        self.assertIsInstance(report, SlaBreachReport)
        self.assertEqual(report.breach_count, 0)
        self.assertEqual(report.breaches, [])


class InProgressPastEtaFlagged(TestCase):
    """Rule 1 — status='in_progress' AND ETA < today."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M74-IP-ETA", self.default)
        self.vendor = _make_vendor(self.default, "ip-eta")

    def test_wo_past_eta_by_one_day_flagged(self):
        as_of = dt.date(2026, 8, 1)
        wo = _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=as_of - dt.timedelta(days=1),
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 1)
        self.assertEqual(report.in_progress_past_eta_count, 1)
        self.assertEqual(report.approved_stale_count, 0)
        breach = report.breaches[0]
        self.assertEqual(breach.kind, BREACH_KIND_IN_PROGRESS_PAST_ETA)
        self.assertEqual(breach.work_order_id, wo.pk)
        self.assertEqual(breach.breach_days, 1)

    def test_wo_at_eta_not_flagged(self):
        # ETA is TODAY → not past ETA yet under grace=0. Fires on day
        # 1 past ETA (the +1 in ``_classify_in_progress``).
        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=as_of,
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 0)

    def test_wo_before_eta_not_flagged(self):
        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=as_of + dt.timedelta(days=3),
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 0)

    def test_missing_eta_not_flagged(self):
        # In-progress WO without an ETA → not an SLA breach (data-
        # quality issue instead). See _classify_in_progress rationale.
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=None,
        )
        report = detect_sla_breaches(self.default, as_of=dt.date(2026, 8, 1))
        self.assertEqual(report.breach_count, 0)


class ApprovedStaleFlagged(TestCase):
    """Rule 2 — status='approved' AND approved_at::date < today - 7."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M74-APP", self.default)
        self.vendor = _make_vendor(self.default, "app")

    def test_wo_approved_eight_days_ago_flagged(self):
        as_of = dt.date(2026, 8, 1)
        approved_at = timezone.make_aware(
            dt.datetime.combine(
                as_of - dt.timedelta(days=8), dt.time(12, 0)
            )
        )
        wo = _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_APPROVED,
            approved_at=approved_at,
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 1)
        self.assertEqual(report.approved_stale_count, 1)
        self.assertEqual(report.in_progress_past_eta_count, 0)
        breach = report.breaches[0]
        self.assertEqual(breach.kind, BREACH_KIND_APPROVED_STALE)
        self.assertEqual(breach.work_order_id, wo.pk)
        self.assertEqual(breach.breach_days, 8)

    def test_wo_approved_at_threshold_not_flagged(self):
        # Approved exactly 7 days ago → at threshold, not past it.
        # ``<= APPROVED_STALE_THRESHOLD_DAYS`` short-circuits.
        as_of = dt.date(2026, 8, 1)
        approved_at = timezone.make_aware(
            dt.datetime.combine(
                as_of - dt.timedelta(days=7), dt.time(12, 0)
            )
        )
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_APPROVED,
            approved_at=approved_at,
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 0)

    def test_missing_approved_at_not_flagged(self):
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_APPROVED,
            approved_at=None,
        )
        report = detect_sla_breaches(self.default, as_of=dt.date(2026, 8, 1))
        self.assertEqual(report.breach_count, 0)


class TerminalAndDraftStatusesNotScanned(TestCase):
    """Completed / cancelled / draft WOs are not SLA breaches."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M74-TERM", self.default)
        self.vendor = _make_vendor(self.default, "term")

    def test_completed_wo_never_flagged(self):
        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_COMPLETED,
            estimated_completion_date=as_of - dt.timedelta(days=30),
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 0)

    def test_cancelled_wo_never_flagged(self):
        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_CANCELLED,
            estimated_completion_date=as_of - dt.timedelta(days=30),
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 0)

    def test_draft_wo_never_flagged(self):
        # A draft WO has not been approved yet — the SLA clock hasn't
        # started.
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_DRAFT,
        )
        report = detect_sla_breaches(self.default, as_of=dt.date(2026, 8, 1))
        self.assertEqual(report.breach_count, 0)


class InHouseVenueNotScanned(TestCase):
    """Scope confirmed at SESSION_091 open: outsourced only."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M74-INH", self.default)
        # In-house WOs have no vendor, so ``_make_wo`` skips it.

    def test_in_house_in_progress_past_eta_not_flagged(self):
        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=_make_vendor(self.default, "ignored"),
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            estimated_completion_date=as_of - dt.timedelta(days=10),
        )
        report = detect_sla_breaches(self.default, as_of=as_of)
        self.assertEqual(report.breach_count, 0)


class RulePrecedence(TestCase):
    """A WO that could hypothetically satisfy both rules simultaneously
    is classified under rule 1 (in_progress past ETA)."""

    def test_in_progress_wins_over_approved_stale(self):
        # A single WO can only have one status at a time — this test
        # exercises the classifier's rule-selection order via a WO
        # that is in_progress. The old approved_at is irrelevant once
        # status advanced.
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M74-PREC", default)
        vendor = _make_vendor(default, "prec")
        as_of = dt.date(2026, 8, 1)
        approved_at = timezone.make_aware(
            dt.datetime.combine(
                as_of - dt.timedelta(days=30), dt.time(12, 0)
            )
        )
        _make_wo(
            dealership=default,
            vehicle=vehicle,
            vendor=vendor,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            approved_at=approved_at,
            estimated_completion_date=as_of - dt.timedelta(days=1),
        )
        report = detect_sla_breaches(default, as_of=as_of)
        self.assertEqual(report.breach_count, 1)
        self.assertEqual(
            report.breaches[0].kind, BREACH_KIND_IN_PROGRESS_PAST_ETA
        )


class CrossTenantIsolation(TestCase):
    """A scan of tenant A does not flag or report tenant B's WOs."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.other = Dealership.objects.create(name="Other", slug="other-v")

        self.v_def = _make_vehicle("M74-XT-DEF", self.default)
        self.v_oth = _make_vehicle("M74-XT-OTH", self.other)
        self.vendor_def = _make_vendor(self.default, "xt-def")
        self.vendor_oth = _make_vendor(self.other, "xt-oth")

        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.v_def,
            vendor=self.vendor_def,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=as_of - dt.timedelta(days=5),
        )
        _make_wo(
            dealership=self.other,
            vehicle=self.v_oth,
            vendor=self.vendor_oth,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=as_of - dt.timedelta(days=99),
        )

    def test_only_target_tenant_reported(self):
        report = detect_sla_breaches(
            self.default, as_of=dt.date(2026, 8, 1)
        )
        self.assertEqual(report.breach_count, 1)
        self.assertEqual(
            report.breaches[0].dealership_id, self.default.pk
        )
        # Other tenant's much-worse breach not in this report.
        for b in report.breaches:
            self.assertNotEqual(b.dealership_id, self.other.pk)


class VerbEmitsWarningLogsPerBreach(TestCase):
    """Each breach emits a WARNING record with a structured payload."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M74-LOG", self.default)
        self.vendor = _make_vendor(self.default, "log")
        as_of = dt.date(2026, 8, 1)
        _make_wo(
            dealership=self.default,
            vehicle=self.vehicle,
            vendor=self.vendor,
            status=WORK_ORDER_STATUS_IN_PROGRESS,
            estimated_completion_date=as_of - dt.timedelta(days=3),
        )
        self.as_of = as_of

    def test_warning_emitted_per_breach(self):
        with self.assertLogs(
            "dealer_ai.vendor_sla.detection", level="WARNING"
        ) as log_ctx:
            detect_sla_breaches(self.default, as_of=self.as_of)
        # One WARNING record per breach.
        self.assertEqual(len(log_ctx.records), 1)
        record = log_ctx.records[0]
        self.assertEqual(record.levelno, logging.WARNING)
        # Structured message carries breach kind + stock number.
        message = record.getMessage()
        self.assertIn(BREACH_KIND_IN_PROGRESS_PAST_ETA, message)
        self.assertIn("M74-LOG", message)


class AsOfHandling(TestCase):
    """``as_of=None`` defaults to today; explicit ``as_of`` honored."""

    def test_defaults_to_today(self):
        default = Dealership.objects.get(slug="default")
        report = detect_sla_breaches(default)
        # ``as_of`` on the report echoes the resolved date. In tests
        # the "today" reference stays within one calendar day of the
        # invocation window.
        today = timezone.now().date()
        self.assertIn(
            report.as_of, {today - dt.timedelta(days=1), today}
        )

    def test_explicit_as_of_stamped_on_report(self):
        default = Dealership.objects.get(slug="default")
        explicit = dt.date(2025, 12, 31)
        report = detect_sla_breaches(default, as_of=explicit)
        self.assertEqual(report.as_of, explicit)


class VerbDataclassesReexported(TestCase):
    """Package facade exposes the dataclasses + constants."""

    def test_report_reexported(self):
        from dealer_ai.services.vendor_sla import SlaBreachReport as R
        from dealer_ai.services.vendor_sla.detection import (
            SlaBreachReport as D,
        )
        self.assertIs(R, D)

    def test_breach_reexported(self):
        from dealer_ai.services.vendor_sla import SlaBreach as R
        from dealer_ai.services.vendor_sla.detection import (
            SlaBreach as D,
        )
        self.assertIs(R, D)
