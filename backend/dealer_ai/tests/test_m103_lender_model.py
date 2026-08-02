"""Milestone 10 · Increment 3 (SESSION_108) — Lender entity model tests.

Locks the persistence-layer shape of :class:`LenderProgram` and
:class:`LenderSubmission` per ``MILESTONE_10_PLANNING.md`` §1.3
(all four §1.3.a-d decisions confirmed at SESSION_108 open, all
Option A, recorded in §0.a).

Coverage:

- Field defaults + choice validation (both models).
- Unique constraint on ``(dealership, name)`` for LenderProgram.
- ``LenderSubmission.clean()`` cross-tenant guards on both
  parent FKs (deal_structure, lender_program).
- ``on_delete=PROTECT`` on the lender_program FK — deleting a
  program with submissions is refused.
- ``on_delete=CASCADE`` on the deal_structure FK — deleting the
  deal cascades to the submissions.
- Ordering (``name`` for programs, ``-submitted_at, -created_at``
  for submissions).
- Tenant-carrier registry includes both new models.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    LENDER_SUBMISSION_STATUS_APPROVED,
    LENDER_SUBMISSION_STATUS_COUNTER,
    LENDER_SUBMISSION_STATUS_DECLINED,
    LENDER_SUBMISSION_STATUS_PENDING,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Vehicle,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES


def _make_vehicle(dealership, *, stock: str = "LDR-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )


def _make_credit_app(dealership, *, name: str = "Alice") -> CreditApplication:
    lead = CustomerLead.objects.create(dealership=dealership, name=name)
    captured = timezone.now()
    return CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name=name,
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
    )


def _make_deal_structure(
    dealership, credit_app, vehicle
) -> DealStructure:
    return DealStructure.objects.create(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=Decimal("30000.00"),
        amount_financed=Decimal("25000.00"),
        apr=Decimal("9.99"),
        term_months=72,
        monthly_payment=Decimal("500.00"),
    )


class LenderProgramShapeTests(TestCase):
    """Field-level invariants for LenderProgram."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="lp-shape", name="LP Shape"
        )

    def test_create_persists_all_fields(self) -> None:
        program = LenderProgram.objects.create(
            dealership=self.dealership,
            name="ABC Bank",
            contact="rep@abcbank.com · 555-1212",
            terms_summary="Prime auto; 84mo max; 130% advance",
        )
        program.refresh_from_db()
        self.assertEqual(program.dealership_id, self.dealership.pk)
        self.assertEqual(program.name, "ABC Bank")
        self.assertEqual(program.contact, "rep@abcbank.com · 555-1212")
        self.assertIn("Prime auto", program.terms_summary)
        # Default: is_active True
        self.assertTrue(program.is_active)

    def test_is_active_defaults_true(self) -> None:
        program = LenderProgram.objects.create(
            dealership=self.dealership, name="Default Active"
        )
        self.assertTrue(program.is_active)

    def test_duplicate_name_per_dealership_raises_integrity_error(self) -> None:
        LenderProgram.objects.create(
            dealership=self.dealership, name="Duplicate"
        )
        with self.assertRaises(IntegrityError):
            LenderProgram.objects.create(
                dealership=self.dealership, name="Duplicate"
            )

    def test_same_name_across_tenants_is_allowed(self) -> None:
        # The unique constraint is per (dealership, name) — two
        # dealerships each having their own "ABC Bank" program row
        # is legitimate.
        other = Dealership.objects.create(
            slug="lp-shape-other", name="LP Other"
        )
        LenderProgram.objects.create(
            dealership=self.dealership, name="Shared Name"
        )
        LenderProgram.objects.create(dealership=other, name="Shared Name")
        # No exception.
        self.assertEqual(
            LenderProgram.objects.filter(name="Shared Name").count(), 2
        )

    def test_str_summary_shows_name_and_active_state(self) -> None:
        active = LenderProgram.objects.create(
            dealership=self.dealership, name="Active Bank"
        )
        inactive = LenderProgram.objects.create(
            dealership=self.dealership,
            name="Inactive Bank",
            is_active=False,
        )
        self.assertIn("active", str(active))
        self.assertIn("inactive", str(inactive))

    def test_ordering_is_name_ascending(self) -> None:
        LenderProgram.objects.create(dealership=self.dealership, name="Charlie")
        LenderProgram.objects.create(dealership=self.dealership, name="Alpha")
        LenderProgram.objects.create(dealership=self.dealership, name="Bravo")
        names = list(
            LenderProgram.objects.filter(dealership=self.dealership).values_list(
                "name", flat=True
            )
        )
        self.assertEqual(names, ["Alpha", "Bravo", "Charlie"])


class LenderSubmissionShapeTests(TestCase):
    """Field-level invariants for LenderSubmission."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="ls-shape", name="LS Shape"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="Shape Bank"
        )

    def test_create_persists_all_fields(self) -> None:
        submitted = timezone.now()
        submission = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=submitted,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
            counter_terms={"apr": "10.99"},
            approval_terms={"apr": "9.99", "term_months": 72},
            notes="Approved on second look.",
        )
        submission.refresh_from_db()
        self.assertEqual(submission.dealership_id, self.dealership.pk)
        self.assertEqual(submission.deal_structure_id, self.deal.pk)
        self.assertEqual(submission.lender_program_id, self.program.pk)
        self.assertEqual(submission.status, LENDER_SUBMISSION_STATUS_APPROVED)
        self.assertEqual(submission.counter_terms, {"apr": "10.99"})
        self.assertEqual(
            submission.approval_terms, {"apr": "9.99", "term_months": 72}
        )

    def test_status_defaults_to_pending(self) -> None:
        submission = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=timezone.now(),
        )
        self.assertEqual(submission.status, LENDER_SUBMISSION_STATUS_PENDING)

    def test_all_four_status_values_accepted(self) -> None:
        for status_value in (
            LENDER_SUBMISSION_STATUS_PENDING,
            LENDER_SUBMISSION_STATUS_APPROVED,
            LENDER_SUBMISSION_STATUS_COUNTER,
            LENDER_SUBMISSION_STATUS_DECLINED,
        ):
            LenderSubmission.objects.create(
                dealership=self.dealership,
                deal_structure=self.deal,
                lender_program=self.program,
                submitted_at=timezone.now(),
                status=status_value,
            )
        self.assertEqual(LenderSubmission.objects.count(), 4)

    def test_terms_default_to_empty_dict(self) -> None:
        submission = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=timezone.now(),
        )
        submission.refresh_from_db()
        self.assertEqual(submission.counter_terms, {})
        self.assertEqual(submission.approval_terms, {})

    def test_ordering_is_submitted_at_desc(self) -> None:
        earlier = timezone.now() - dt.timedelta(hours=2)
        later = timezone.now()
        older = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=earlier,
        )
        newer = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=later,
        )
        rows = list(LenderSubmission.objects.all())
        self.assertEqual(rows[0].pk, newer.pk)
        self.assertEqual(rows[1].pk, older.pk)


class LenderSubmissionCleanTests(TestCase):
    """`LenderSubmission.clean()` cross-tenant guards."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="ls-clean", name="LS Clean"
        )
        self.other = Dealership.objects.create(
            slug="ls-clean-other", name="Other"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.other_credit_app = _make_credit_app(self.other, name="Other Alice")
        self.vehicle = _make_vehicle(self.dealership)
        self.other_vehicle = _make_vehicle(self.other, stock="LDR-OTHER")
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.other_deal = _make_deal_structure(
            self.other, self.other_credit_app, self.other_vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="Clean Bank"
        )
        self.other_program = LenderProgram.objects.create(
            dealership=self.other, name="Other Bank"
        )

    def test_clean_passes_with_same_tenant_deal_and_program(self) -> None:
        submission = LenderSubmission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=timezone.now(),
        )
        submission.clean()

    def test_clean_refuses_cross_tenant_deal_structure(self) -> None:
        submission = LenderSubmission(
            dealership=self.dealership,
            deal_structure=self.other_deal,
            lender_program=self.program,
            submitted_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            submission.clean()

    def test_clean_refuses_cross_tenant_lender_program(self) -> None:
        submission = LenderSubmission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.other_program,
            submitted_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            submission.clean()


class LenderCascadeAndProtectTests(TestCase):
    """FK on-delete behavior: CASCADE for DealStructure, PROTECT for
    LenderProgram."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="ls-fk", name="LS FK"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="FK Bank"
        )
        self.submission = LenderSubmission.objects.create(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=timezone.now(),
        )

    def test_deleting_deal_structure_cascades_to_submissions(self) -> None:
        self.deal.delete()
        self.assertFalse(
            LenderSubmission.objects.filter(pk=self.submission.pk).exists()
        )

    def test_deleting_program_with_submissions_is_protected(self) -> None:
        with self.assertRaises(ProtectedError):
            self.program.delete()
        # Submission and program both survive.
        self.assertTrue(
            LenderSubmission.objects.filter(pk=self.submission.pk).exists()
        )
        self.assertTrue(
            LenderProgram.objects.filter(pk=self.program.pk).exists()
        )

    def test_deleting_program_without_submissions_succeeds(self) -> None:
        empty_program = LenderProgram.objects.create(
            dealership=self.dealership, name="Empty Bank"
        )
        empty_program.delete()
        self.assertFalse(
            LenderProgram.objects.filter(pk=empty_program.pk).exists()
        )


class LenderTenancyCarrierTests(TestCase):
    """Both new models are in the tenant-carrier registry."""

    def test_lender_program_is_a_tenant_carrier(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 27)
        self.assertIn("LenderProgram", _TENANT_CARRIER_MODEL_NAMES)

    def test_lender_submission_is_a_tenant_carrier(self) -> None:
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 28)
        self.assertIn("LenderSubmission", _TENANT_CARRIER_MODEL_NAMES)
