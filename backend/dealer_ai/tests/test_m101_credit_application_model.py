"""Milestone 10 · Increment 1 (SESSION_106) — CreditApplication model tests.

Locks the persistence-layer shape of :class:`CreditApplication` per
``MILESTONE_10_PLANNING.md`` §5.a Option C + §5.e (all user-
confirmed at SESSION_106 open, recorded in §0.a).

Coverage:

- Field defaults + choice validation.
- Ordering (``-captured_at``, ``-created_at``).
- ``clean()`` — attach-shape (at least one of lead/sale) + cross-
  tenant guards (lead, sale).
- ``delete()`` retention-clock enforcement (refuses unexpired;
  allows expired).
- ``lead`` + ``sale`` SET_NULL on parent delete (retention row
  survives; the retention-clock record of record).
- Tenant-carrier autofill signal wires ``CreditApplication`` in
  as the 25th carrier (M9.2 was 24).
- ``__str__`` renders a human-scannable summary.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_ONLINE_PREQUAL,
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_FORMAT_TABLET,
    CREDIT_APP_RETENTION_YEARS,
    CREDIT_APP_STATUS_RECEIVED,
    CREDIT_APP_STATUS_SUBMITTED,
    CREDIT_APP_STATUS_WITHDRAWN,
    SALE_FINANCE_TYPE_CASH,
    CreditApplication,
    CreditApplicationRetentionActiveError,
    CustomerLead,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


def _make_lead(dealership: Dealership, *, name: str = "Alice Applicant") -> CustomerLead:
    return CustomerLead.objects.create(dealership=dealership, name=name)


def _make_sale(dealership: Dealership, *, stock: str = "CA-1") -> Sale:
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


class CreditApplicationShapeTests(TestCase):
    """Field-level invariants."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-shape", name="M10.1 Shape"
        )
        self.lead = _make_lead(self.dealership)

    def test_create_with_lead_only_persists_all_fields(self) -> None:
        captured = timezone.now()
        expires = captured + relativedelta(years=CREDIT_APP_RETENTION_YEARS)
        app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Alice Applicant",
            applicant_ssn_last4="1234",
            source_format=CREDIT_APP_FORMAT_TABLET,
            captured_at=captured,
            retention_expires_at=expires,
        )
        app.refresh_from_db()
        self.assertEqual(app.dealership_id, self.dealership.pk)
        self.assertEqual(app.lead_id, self.lead.pk)
        self.assertIsNone(app.sale_id)
        self.assertEqual(app.applicant_full_name, "Alice Applicant")
        self.assertEqual(app.applicant_ssn_last4, "1234")
        self.assertEqual(app.source_format, CREDIT_APP_FORMAT_TABLET)
        # Default status when not explicitly set.
        self.assertEqual(app.status, CREDIT_APP_STATUS_RECEIVED)
        self.assertEqual(app.notes, "")

    def test_status_choices_accept_all_three_values(self) -> None:
        captured = timezone.now()
        for status_value in (
            CREDIT_APP_STATUS_RECEIVED,
            CREDIT_APP_STATUS_SUBMITTED,
            CREDIT_APP_STATUS_WITHDRAWN,
        ):
            app = CreditApplication.objects.create(
                dealership=self.dealership,
                lead=self.lead,
                applicant_full_name=f"Applicant {status_value}",
                source_format=CREDIT_APP_FORMAT_PAPER,
                status=status_value,
                captured_at=captured,
                retention_expires_at=captured
                + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
            )
            app.refresh_from_db()
            self.assertEqual(app.status, status_value)

    def test_source_format_choices_accept_all_three_values(self) -> None:
        captured = timezone.now()
        for fmt in (
            CREDIT_APP_FORMAT_PAPER,
            CREDIT_APP_FORMAT_TABLET,
            CREDIT_APP_FORMAT_ONLINE_PREQUAL,
        ):
            app = CreditApplication.objects.create(
                dealership=self.dealership,
                lead=self.lead,
                applicant_full_name=f"Applicant {fmt}",
                source_format=fmt,
                captured_at=captured,
                retention_expires_at=captured
                + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
            )
            self.assertEqual(app.source_format, fmt)

    def test_ordering_is_captured_at_desc_then_created_at_desc(self) -> None:
        captured_early = timezone.now() - dt.timedelta(days=2)
        captured_late = timezone.now()
        expires_early = captured_early + relativedelta(
            years=CREDIT_APP_RETENTION_YEARS
        )
        expires_late = captured_late + relativedelta(
            years=CREDIT_APP_RETENTION_YEARS
        )
        # Insert older-captured row first so ordering isn't accidentally
        # insert-order.
        older = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Older",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured_early,
            retention_expires_at=expires_early,
        )
        newer = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Newer",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured_late,
            retention_expires_at=expires_late,
        )
        rows = list(CreditApplication.objects.all())
        self.assertEqual(rows[0].pk, newer.pk)
        self.assertEqual(rows[1].pk, older.pk)

    def test_str_summary_includes_applicant_name_and_status(self) -> None:
        captured = timezone.now()
        app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Bob Buyer",
            source_format=CREDIT_APP_FORMAT_ONLINE_PREQUAL,
            status=CREDIT_APP_STATUS_SUBMITTED,
            captured_at=captured,
            retention_expires_at=captured
            + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
        )
        rendered = str(app)
        self.assertIn("Bob Buyer", rendered)
        self.assertIn("Submitted", rendered)


class CreditApplicationCleanTests(TestCase):
    """`clean()` — attach-shape + cross-tenant guards."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-clean", name="M10.1 Clean"
        )
        self.other = Dealership.objects.create(
            slug="m101-clean-other", name="Other"
        )
        self.lead = _make_lead(self.dealership)
        self.other_lead = _make_lead(self.other, name="Other Alice")
        self.sale = _make_sale(self.dealership)
        self.other_sale = _make_sale(self.other, stock="CA-OTHER")
        self.captured = timezone.now()
        self.expires = self.captured + relativedelta(
            years=CREDIT_APP_RETENTION_YEARS
        )

    def test_clean_refuses_when_both_lead_and_sale_missing(self) -> None:
        app = CreditApplication(
            dealership=self.dealership,
            applicant_full_name="Orphan",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=self.captured,
            retention_expires_at=self.expires,
        )
        with self.assertRaises(ValidationError):
            app.clean()

    def test_clean_passes_with_lead_only(self) -> None:
        app = CreditApplication(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Lead Only",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=self.captured,
            retention_expires_at=self.expires,
        )
        app.clean()  # should not raise

    def test_clean_passes_with_sale_only(self) -> None:
        app = CreditApplication(
            dealership=self.dealership,
            sale=self.sale,
            applicant_full_name="Sale Only",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=self.captured,
            retention_expires_at=self.expires,
        )
        app.clean()  # should not raise

    def test_clean_passes_with_both_lead_and_sale(self) -> None:
        app = CreditApplication(
            dealership=self.dealership,
            lead=self.lead,
            sale=self.sale,
            applicant_full_name="Both",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=self.captured,
            retention_expires_at=self.expires,
        )
        app.clean()  # should not raise

    def test_clean_refuses_cross_tenant_lead(self) -> None:
        app = CreditApplication(
            dealership=self.dealership,
            lead=self.other_lead,
            applicant_full_name="Cross-tenant lead",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=self.captured,
            retention_expires_at=self.expires,
        )
        with self.assertRaises(ValidationError):
            app.clean()

    def test_clean_refuses_cross_tenant_sale(self) -> None:
        app = CreditApplication(
            dealership=self.dealership,
            sale=self.other_sale,
            applicant_full_name="Cross-tenant sale",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=self.captured,
            retention_expires_at=self.expires,
        )
        with self.assertRaises(ValidationError):
            app.clean()


class CreditApplicationDeleteRetentionTests(TestCase):
    """`delete()` retention-clock enforcement per §5.e."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-del", name="M10.1 Delete"
        )
        self.lead = _make_lead(self.dealership)

    def test_delete_refuses_when_retention_window_is_open(self) -> None:
        captured = timezone.now()
        expires = captured + relativedelta(years=CREDIT_APP_RETENTION_YEARS)
        app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Fresh",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured,
            retention_expires_at=expires,
        )
        with self.assertRaises(CreditApplicationRetentionActiveError):
            app.delete()
        # Row still exists.
        self.assertTrue(
            CreditApplication.objects.filter(pk=app.pk).exists()
        )

    def test_delete_allowed_after_retention_expires(self) -> None:
        # Simulate an app whose retention window closed a day ago.
        captured = timezone.now() - relativedelta(
            years=CREDIT_APP_RETENTION_YEARS
        ) - dt.timedelta(days=1)
        expires = timezone.now() - dt.timedelta(days=1)
        app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Expired",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured,
            retention_expires_at=expires,
        )
        app.delete()
        self.assertFalse(
            CreditApplication.objects.filter(pk=app.pk).exists()
        )

    def test_delete_edge_case_exact_moment_of_expiry_is_allowed(self) -> None:
        # ``retention_expires_at`` set to *now* — the model's check is
        # ``timezone.now() < retention_expires_at`` (strict less-than).
        # By the time delete() runs, ``timezone.now()`` has advanced,
        # so the delete should succeed.
        captured = timezone.now() - relativedelta(
            years=CREDIT_APP_RETENTION_YEARS
        )
        expires = timezone.now()
        app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            applicant_full_name="Edge",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured,
            retention_expires_at=expires,
        )
        # Not asserting on the delete itself — the delta between
        # ``expires`` and delete-time is microseconds and always positive.
        app.delete()
        self.assertFalse(
            CreditApplication.objects.filter(pk=app.pk).exists()
        )


class CreditApplicationParentDeletionTests(TestCase):
    """`SET_NULL` behavior when parent lead or sale is deleted."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m101-parent", name="M10.1 Parent"
        )
        self.lead = _make_lead(self.dealership)
        self.sale = _make_sale(self.dealership)
        captured = timezone.now() - relativedelta(
            years=CREDIT_APP_RETENTION_YEARS + 1
        )
        expires = timezone.now() - dt.timedelta(days=1)
        # Use already-expired retention so any incidental deletes in
        # this test class don't fail on the retention guard.
        self.app = CreditApplication.objects.create(
            dealership=self.dealership,
            lead=self.lead,
            sale=self.sale,
            applicant_full_name="Multi-attach",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured,
            retention_expires_at=expires,
        )

    def test_lead_deletion_nulls_lead_fk_preserves_row(self) -> None:
        self.lead.delete()
        self.app.refresh_from_db()
        self.assertIsNone(self.app.lead_id)
        # Sale FK preserved.
        self.assertEqual(self.app.sale_id, self.sale.pk)

    def test_sale_deletion_nulls_sale_fk_preserves_row(self) -> None:
        # Sale.delete() cascades to Vehicle only via the OneToOne;
        # the app row should survive with lead FK intact.
        self.sale.delete()
        self.app.refresh_from_db()
        self.assertIsNone(self.app.sale_id)
        self.assertEqual(self.app.lead_id, self.lead.pk)


class CreditApplicationTenancyCarrierTests(TestCase):
    """The tenant-carrier registry includes ``CreditApplication``."""

    def test_credit_application_is_25th_tenant_carrier(self) -> None:
        # M9.2 shipped 24; M10.1 makes it 25.
        self.assertEqual(len(_TENANT_CARRIER_MODEL_NAMES), 25)
        self.assertIn("CreditApplication", _TENANT_CARRIER_MODEL_NAMES)

    def test_autofill_signal_attaches_default_dealership(self) -> None:
        # No ``dealership=`` on create — the pre_save signal should
        # attach the migration-seeded default.
        lead = CustomerLead.objects.create(name="Autofill Lead")
        captured = timezone.now()
        app = CreditApplication.objects.create(
            # dealership omitted — pre_save should fill.
            lead=lead,
            applicant_full_name="Autofill",
            source_format=CREDIT_APP_FORMAT_PAPER,
            captured_at=captured,
            retention_expires_at=captured
            + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
        )
        app.refresh_from_db()
        self.assertIsNotNone(app.dealership_id)
