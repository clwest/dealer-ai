"""Milestone 10 · Increment 1 (SESSION_106) — CreditApplication service tests.

Locks the service surface of :mod:`services.f_and_i` per
``MILESTONE_10_PLANNING.md`` §7 M10.1.

Coverage:

- :func:`compute_retention_expires_at` — pure verb; adds
  CREDIT_APP_RETENTION_YEARS years to captured_at.
- :func:`record_credit_application` — happy paths (lead only,
  sale only, both) and rejection paths (attach-shape, cross-tenant
  lead, cross-tenant sale, unknown source_format, unknown status).
- :func:`get_credit_application` — tenant-scoped read; returns
  None on unknown pk and cross-tenant pk (never raises, never
  leaks).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_FORMAT_TABLET,
    CREDIT_APP_RETENTION_YEARS,
    CREDIT_APP_STATUS_RECEIVED,
    CREDIT_APP_STATUS_SUBMITTED,
    SALE_FINANCE_TYPE_CASH,
    CreditApplication,
    CustomerLead,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    CrossTenantCreditApplicationError,
    compute_retention_expires_at,
    get_credit_application,
    record_credit_application,
)


class ComputeRetentionExpiresAtTests(TestCase):
    """Pure retention-clock verb."""

    def test_adds_seven_years(self) -> None:
        captured = timezone.make_aware(dt.datetime(2026, 8, 1, 12, 0, 0))
        expected = timezone.make_aware(dt.datetime(2033, 8, 1, 12, 0, 0))
        self.assertEqual(
            compute_retention_expires_at(captured), expected
        )

    def test_handles_leap_day_capture(self) -> None:
        # Feb 29 2024 (leap year) + 7 years = Feb 28 2031 (non-leap).
        # ``relativedelta`` rolls back to the last day of the target
        # month rather than raising, which is the well-defined
        # standard behavior we want.
        captured = timezone.make_aware(dt.datetime(2024, 2, 29, 10, 0, 0))
        expires = compute_retention_expires_at(captured)
        self.assertEqual(expires.year, 2024 + CREDIT_APP_RETENTION_YEARS)
        self.assertEqual(expires.month, 2)
        # Feb 2031 has 28 days.
        self.assertEqual(expires.day, 28)

    def test_pure_verb_returns_same_value_every_call(self) -> None:
        captured = timezone.now()
        a = compute_retention_expires_at(captured)
        b = compute_retention_expires_at(captured)
        self.assertEqual(a, b)


def _make_lead(dealership: Dealership, *, name: str = "Alice Applicant") -> CustomerLead:
    return CustomerLead.objects.create(dealership=dealership, name=name)


def _make_sale(dealership: Dealership, *, stock: str = "SVC-1") -> Sale:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("30000.00"),
        finance_type=SALE_FINANCE_TYPE_CASH,
        gross_realized=Decimal("1500.00"),
    )


class RecordCreditApplicationHappyPathTests(TestCase):
    """`record_credit_application` — happy paths."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-svc-happy", name="M10.1 Svc Happy"
        )
        self.lead = _make_lead(self.dealership)
        self.sale = _make_sale(self.dealership)

    def test_record_with_lead_only(self) -> None:
        before = timezone.now()
        app = record_credit_application(
            dealership=self.dealership,
            applicant_full_name="Lead Only",
            source_format=CREDIT_APP_FORMAT_TABLET,
            lead=self.lead,
        )
        self.assertIsInstance(app, CreditApplication)
        self.assertEqual(app.lead_id, self.lead.pk)
        self.assertIsNone(app.sale_id)
        # Defaults applied.
        self.assertEqual(app.status, CREDIT_APP_STATUS_RECEIVED)
        self.assertEqual(app.applicant_ssn_last4, "")
        self.assertEqual(app.notes, "")
        # Retention window populated from captured_at (which
        # defaulted to now, so is within a second of ``before``).
        self.assertGreaterEqual(app.captured_at, before)
        expected_expires = compute_retention_expires_at(app.captured_at)
        self.assertEqual(app.retention_expires_at, expected_expires)

    def test_record_with_sale_only(self) -> None:
        app = record_credit_application(
            dealership=self.dealership,
            applicant_full_name="Sale Only",
            source_format=CREDIT_APP_FORMAT_PAPER,
            sale=self.sale,
        )
        self.assertIsNone(app.lead_id)
        self.assertEqual(app.sale_id, self.sale.pk)

    def test_record_with_both_lead_and_sale(self) -> None:
        app = record_credit_application(
            dealership=self.dealership,
            applicant_full_name="Both",
            source_format=CREDIT_APP_FORMAT_PAPER,
            lead=self.lead,
            sale=self.sale,
            status=CREDIT_APP_STATUS_SUBMITTED,
            applicant_ssn_last4="9999",
            notes="Under review at ABC Bank.",
        )
        self.assertEqual(app.lead_id, self.lead.pk)
        self.assertEqual(app.sale_id, self.sale.pk)
        self.assertEqual(app.status, CREDIT_APP_STATUS_SUBMITTED)
        self.assertEqual(app.applicant_ssn_last4, "9999")
        self.assertEqual(app.notes, "Under review at ABC Bank.")

    def test_record_respects_explicit_captured_at(self) -> None:
        captured = timezone.make_aware(dt.datetime(2026, 6, 15, 9, 30, 0))
        app = record_credit_application(
            dealership=self.dealership,
            applicant_full_name="Backdated",
            source_format=CREDIT_APP_FORMAT_PAPER,
            lead=self.lead,
            captured_at=captured,
        )
        self.assertEqual(app.captured_at, captured)
        self.assertEqual(
            app.retention_expires_at,
            captured + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
        )


class RecordCreditApplicationRejectionTests(TestCase):
    """`record_credit_application` — rejection paths."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-svc-rej", name="M10.1 Svc Rej"
        )
        self.other = Dealership.objects.create(
            slug="m101-svc-rej-other", name="Other"
        )
        self.lead = _make_lead(self.dealership)
        self.other_lead = _make_lead(self.other, name="Other Alice")
        self.sale = _make_sale(self.dealership)
        self.other_sale = _make_sale(self.other, stock="SVC-OTHER")

    def test_neither_lead_nor_sale_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            record_credit_application(
                dealership=self.dealership,
                applicant_full_name="Orphan",
                source_format=CREDIT_APP_FORMAT_PAPER,
            )

    def test_cross_tenant_lead_raises(self) -> None:
        with self.assertRaises(CrossTenantCreditApplicationError):
            record_credit_application(
                dealership=self.dealership,
                applicant_full_name="Cross-tenant lead",
                source_format=CREDIT_APP_FORMAT_PAPER,
                lead=self.other_lead,
            )

    def test_cross_tenant_sale_raises(self) -> None:
        with self.assertRaises(CrossTenantCreditApplicationError):
            record_credit_application(
                dealership=self.dealership,
                applicant_full_name="Cross-tenant sale",
                source_format=CREDIT_APP_FORMAT_PAPER,
                sale=self.other_sale,
            )

    def test_unknown_source_format_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_credit_application(
                dealership=self.dealership,
                applicant_full_name="Bad format",
                source_format="fax",  # not in the vocabulary
                lead=self.lead,
            )

    def test_unknown_status_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_credit_application(
                dealership=self.dealership,
                applicant_full_name="Bad status",
                source_format=CREDIT_APP_FORMAT_PAPER,
                status="approved",  # deferred to M10.3
                lead=self.lead,
            )


class GetCreditApplicationTests(TestCase):
    """`get_credit_application` — tenant-scoped read verb."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-svc-get", name="M10.1 Svc Get"
        )
        self.other = Dealership.objects.create(
            slug="m101-svc-get-other", name="Other"
        )
        self.lead = _make_lead(self.dealership)
        self.app = record_credit_application(
            dealership=self.dealership,
            applicant_full_name="Findable",
            source_format=CREDIT_APP_FORMAT_PAPER,
            lead=self.lead,
        )

    def test_returns_row_for_matching_tenant(self) -> None:
        found = get_credit_application(self.app.pk, dealership=self.dealership)
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.app.pk)

    def test_returns_none_for_unknown_pk(self) -> None:
        self.assertIsNone(
            get_credit_application(999999, dealership=self.dealership)
        )

    def test_returns_none_for_cross_tenant_pk(self) -> None:
        # App belongs to self.dealership; caller asks as ``self.other``.
        self.assertIsNone(
            get_credit_application(self.app.pk, dealership=self.other)
        )
