"""Milestone 10 · Increment 3 (SESSION_108) — Lender service tests.

Locks the service surface of :mod:`services.f_and_i.lender`
per ``MILESTONE_10_PLANNING.md`` §1.3 + §7 M10.3.

Coverage:

- Catalog: `record_lender_program` (happy + duplicate-name
  rejection), `list_active_lender_programs` (filters
  is_active=False, orders by name).
- Submission: `record_lender_submission` (happy + cross-tenant
  deal + cross-tenant program + unknown status), status +
  terms partial update via `update_lender_submission_status`,
  `get_lender_submission` tenant scoping, and
  `list_submissions_for_deal_structure` FK filter.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from dateutil.relativedelta import relativedelta
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
from dealer_ai.services.f_and_i import (
    CrossTenantLenderSubmissionError,
    DuplicateLenderProgramError,
    get_lender_submission,
    list_active_lender_programs,
    list_submissions_for_deal_structure,
    record_lender_program,
    record_lender_submission,
    update_lender_submission_status,
)


def _make_vehicle(dealership, *, stock: str = "LSV-1") -> Vehicle:
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


def _make_deal_structure(dealership, credit_app, vehicle) -> DealStructure:
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


class RecordLenderProgramTests(TestCase):
    """`record_lender_program` — happy paths + duplicate rejection."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="rlp", name="Record Program"
        )

    def test_record_persists_row_with_defaults(self) -> None:
        program = record_lender_program(
            dealership=self.dealership,
            name="Prime Bank",
        )
        self.assertIsInstance(program, LenderProgram)
        self.assertEqual(program.name, "Prime Bank")
        self.assertEqual(program.contact, "")
        self.assertEqual(program.terms_summary, "")
        self.assertTrue(program.is_active)

    def test_record_persists_all_optional_fields(self) -> None:
        program = record_lender_program(
            dealership=self.dealership,
            name="Full Bank",
            contact="rep@fullbank.com",
            terms_summary="Prime; 84mo max",
            is_active=False,
        )
        program.refresh_from_db()
        self.assertEqual(program.contact, "rep@fullbank.com")
        self.assertEqual(program.terms_summary, "Prime; 84mo max")
        self.assertFalse(program.is_active)

    def test_duplicate_name_per_dealership_raises_typed_error(self) -> None:
        record_lender_program(dealership=self.dealership, name="Dup Bank")
        with self.assertRaises(DuplicateLenderProgramError):
            record_lender_program(
                dealership=self.dealership, name="Dup Bank"
            )

    def test_same_name_across_tenants_succeeds(self) -> None:
        other = Dealership.objects.create(slug="rlp-other", name="Other")
        record_lender_program(dealership=self.dealership, name="Cross")
        record_lender_program(dealership=other, name="Cross")
        # No exception.
        self.assertEqual(LenderProgram.objects.filter(name="Cross").count(), 2)


class ListActiveLenderProgramsTests(TestCase):
    """`list_active_lender_programs` — filter + ordering."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="lalp", name="List Active"
        )
        record_lender_program(
            dealership=self.dealership, name="Alpha Bank", is_active=True
        )
        record_lender_program(
            dealership=self.dealership, name="Bravo Bank", is_active=False
        )
        record_lender_program(
            dealership=self.dealership, name="Charlie Bank", is_active=True
        )

    def test_filters_out_inactive_programs(self) -> None:
        names = list(
            list_active_lender_programs(self.dealership).values_list(
                "name", flat=True
            )
        )
        self.assertEqual(names, ["Alpha Bank", "Charlie Bank"])

    def test_returns_empty_for_dealership_with_no_programs(self) -> None:
        empty = Dealership.objects.create(slug="lalp-empty", name="Empty")
        self.assertEqual(list(list_active_lender_programs(empty)), [])


class RecordLenderSubmissionTests(TestCase):
    """`record_lender_submission` — happy + rejection paths."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="rls", name="Record Sub"
        )
        self.other = Dealership.objects.create(slug="rls-other", name="Other")
        self.credit_app = _make_credit_app(self.dealership)
        self.other_credit_app = _make_credit_app(self.other, name="Other App")
        self.vehicle = _make_vehicle(self.dealership)
        self.other_vehicle = _make_vehicle(self.other, stock="RLS-OTHER")
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.other_deal = _make_deal_structure(
            self.other, self.other_credit_app, self.other_vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="Bank A"
        )
        self.other_program = LenderProgram.objects.create(
            dealership=self.other, name="Other Bank"
        )

    def test_record_persists_with_defaults(self) -> None:
        before = timezone.now()
        submission = record_lender_submission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
        )
        self.assertEqual(submission.status, LENDER_SUBMISSION_STATUS_PENDING)
        self.assertEqual(submission.counter_terms, {})
        self.assertEqual(submission.approval_terms, {})
        self.assertEqual(submission.notes, "")
        # submitted_at defaults to ~now.
        self.assertGreaterEqual(submission.submitted_at, before)

    def test_record_persists_explicit_status_and_terms(self) -> None:
        submitted = timezone.now()
        submission = record_lender_submission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
            submitted_at=submitted,
            status=LENDER_SUBMISSION_STATUS_APPROVED,
            approval_terms={"apr": "9.99", "term_months": 72},
            notes="Approved on first look.",
        )
        self.assertEqual(submission.submitted_at, submitted)
        self.assertEqual(submission.status, LENDER_SUBMISSION_STATUS_APPROVED)
        self.assertEqual(
            submission.approval_terms, {"apr": "9.99", "term_months": 72}
        )
        self.assertEqual(submission.notes, "Approved on first look.")

    def test_cross_tenant_deal_structure_raises(self) -> None:
        with self.assertRaises(CrossTenantLenderSubmissionError):
            record_lender_submission(
                dealership=self.dealership,
                deal_structure=self.other_deal,
                lender_program=self.program,
            )

    def test_cross_tenant_lender_program_raises(self) -> None:
        with self.assertRaises(CrossTenantLenderSubmissionError):
            record_lender_submission(
                dealership=self.dealership,
                deal_structure=self.deal,
                lender_program=self.other_program,
            )

    def test_unknown_status_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_lender_submission(
                dealership=self.dealership,
                deal_structure=self.deal,
                lender_program=self.program,
                status="funded",  # M10.5 concept, not M10.3
            )


class UpdateLenderSubmissionStatusTests(TestCase):
    """`update_lender_submission_status` — transitions + partial updates."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="ulss", name="Update Status"
        )
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.program = LenderProgram.objects.create(
            dealership=self.dealership, name="Status Bank"
        )
        self.submission = record_lender_submission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program,
        )

    def test_pending_to_approved_transition_persists(self) -> None:
        updated = update_lender_submission_status(
            self.submission,
            new_status=LENDER_SUBMISSION_STATUS_APPROVED,
            approval_terms={"apr": "9.99"},
        )
        updated.refresh_from_db()
        self.assertEqual(updated.status, LENDER_SUBMISSION_STATUS_APPROVED)
        self.assertEqual(updated.approval_terms, {"apr": "9.99"})
        # counter_terms untouched (still empty dict default).
        self.assertEqual(updated.counter_terms, {})

    def test_pending_to_counter_transition_persists(self) -> None:
        updated = update_lender_submission_status(
            self.submission,
            new_status=LENDER_SUBMISSION_STATUS_COUNTER,
            counter_terms={"apr": "12.99", "term_months": 60},
        )
        updated.refresh_from_db()
        self.assertEqual(updated.status, LENDER_SUBMISSION_STATUS_COUNTER)
        self.assertEqual(
            updated.counter_terms, {"apr": "12.99", "term_months": 60}
        )

    def test_pending_to_declined_transition_persists(self) -> None:
        updated = update_lender_submission_status(
            self.submission,
            new_status=LENDER_SUBMISSION_STATUS_DECLINED,
            notes="Debt-to-income too high.",
        )
        updated.refresh_from_db()
        self.assertEqual(updated.status, LENDER_SUBMISSION_STATUS_DECLINED)
        self.assertEqual(updated.notes, "Debt-to-income too high.")

    def test_any_to_any_transition_allowed_at_m103(self) -> None:
        # M10.3 has no transition constraint — approved → pending
        # is legitimate (operator changed their mind, error correction).
        update_lender_submission_status(
            self.submission, new_status=LENDER_SUBMISSION_STATUS_APPROVED
        )
        updated = update_lender_submission_status(
            self.submission, new_status=LENDER_SUBMISSION_STATUS_PENDING
        )
        self.assertEqual(updated.status, LENDER_SUBMISSION_STATUS_PENDING)

    def test_unknown_status_raises(self) -> None:
        with self.assertRaises(ValueError):
            update_lender_submission_status(
                self.submission, new_status="funded"
            )


class GetAndListLenderSubmissionTests(TestCase):
    """`get_lender_submission` + `list_submissions_for_deal_structure`."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="gls", name="Get List"
        )
        self.other = Dealership.objects.create(slug="gls-other", name="Other")
        self.credit_app = _make_credit_app(self.dealership)
        self.vehicle = _make_vehicle(self.dealership)
        self.deal = _make_deal_structure(
            self.dealership, self.credit_app, self.vehicle
        )
        self.program_a = LenderProgram.objects.create(
            dealership=self.dealership, name="A"
        )
        self.program_b = LenderProgram.objects.create(
            dealership=self.dealership, name="B"
        )
        self.sub_a = record_lender_submission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program_a,
        )
        self.sub_b = record_lender_submission(
            dealership=self.dealership,
            deal_structure=self.deal,
            lender_program=self.program_b,
        )

    def test_get_returns_matching_tenant_row(self) -> None:
        found = get_lender_submission(self.sub_a.pk, dealership=self.dealership)
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.sub_a.pk)

    def test_get_returns_none_for_unknown_pk(self) -> None:
        self.assertIsNone(
            get_lender_submission(999999, dealership=self.dealership)
        )

    def test_get_returns_none_for_cross_tenant_pk(self) -> None:
        self.assertIsNone(
            get_lender_submission(self.sub_a.pk, dealership=self.other)
        )

    def test_list_for_deal_returns_all_submissions(self) -> None:
        pks = set(
            list_submissions_for_deal_structure(self.deal).values_list(
                "pk", flat=True
            )
        )
        self.assertEqual(pks, {self.sub_a.pk, self.sub_b.pk})
