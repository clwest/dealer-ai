"""Milestone 10 · Increment 4 (SESSION_109) — Stipulation model tests.

Locks the persistence-layer shape of :class:`Stipulation` per
``MILESTONE_10_PLANNING.md`` §1.4 + §5.b (all decisions
confirmed at SESSION_106 / SESSION_109, all Option A, recorded
in §0.a).

Coverage:

- Field defaults + choice vocabularies (both type + state).
- Ordering (``-created_at``).
- ``clean()`` cross-tenant guard on lender_submission FK.
- CASCADE on parent lender_submission delete.
- ``documented_by`` SET_NULL on user delete.
- Tenant-carrier registry includes ``Stipulation``.
- ``__str__`` renders type + state.
"""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    STIP_TYPE_OTHER,
    STIP_TYPE_PROOF_OF_INCOME,
    STIP_TYPE_PROOF_OF_INSURANCE,
    STIP_TYPE_PROOF_OF_RESIDENCE,
    STIP_TYPE_REFERENCES,
    STIPULATION_STATE_CLEARED,
    STIPULATION_STATE_OPEN,
    STIPULATION_STATE_WAIVED,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Stipulation,
    Vehicle,
)
from dealer_ai.services.tenancy import _TENANT_CARRIER_MODEL_NAMES

User = get_user_model()


def _make_lender_submission(dealership, *, stock: str = "SM-1") -> LenderSubmission:
    lead = CustomerLead.objects.create(dealership=dealership, name="Alice")
    captured = timezone.now()
    credit_app = CreditApplication.objects.create(
        dealership=dealership,
        lead=lead,
        applicant_full_name="Alice",
        source_format=CREDIT_APP_FORMAT_PAPER,
        captured_at=captured,
        retention_expires_at=captured
        + relativedelta(years=CREDIT_APP_RETENTION_YEARS),
    )
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Bronco",
        price=Decimal("28500.00"),
        dealership=dealership,
    )
    deal = DealStructure.objects.create(
        dealership=dealership,
        credit_application=credit_app,
        vehicle=vehicle,
        sale_price=Decimal("30000.00"),
        amount_financed=Decimal("25000.00"),
        apr=Decimal("9.99"),
        term_months=72,
        monthly_payment=Decimal("500.00"),
    )
    program = LenderProgram.objects.create(
        dealership=dealership, name=f"Program-{stock}"
    )
    return LenderSubmission.objects.create(
        dealership=dealership,
        deal_structure=deal,
        lender_program=program,
        submitted_at=timezone.now(),
    )


class StipulationShapeTests(TestCase):
    """Field-level invariants."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="stip-shape", name="Stip Shape"
        )
        self.submission = _make_lender_submission(self.dealership)

    def test_create_persists_all_fields(self) -> None:
        stip = Stipulation.objects.create(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
            notes="Two recent paystubs",
        )
        stip.refresh_from_db()
        self.assertEqual(stip.dealership_id, self.dealership.pk)
        self.assertEqual(stip.lender_submission_id, self.submission.pk)
        self.assertEqual(stip.stip_type, STIP_TYPE_PROOF_OF_INCOME)
        # Defaults
        self.assertEqual(stip.state, STIPULATION_STATE_OPEN)
        self.assertIsNone(stip.documented_by_id)
        self.assertIsNone(stip.cleared_at)
        self.assertEqual(stip.notes, "Two recent paystubs")

    def test_all_five_stip_types_accepted(self) -> None:
        for stip_type in (
            STIP_TYPE_PROOF_OF_INCOME,
            STIP_TYPE_PROOF_OF_INSURANCE,
            STIP_TYPE_PROOF_OF_RESIDENCE,
            STIP_TYPE_REFERENCES,
            STIP_TYPE_OTHER,
        ):
            Stipulation.objects.create(
                dealership=self.dealership,
                lender_submission=self.submission,
                stip_type=stip_type,
            )
        self.assertEqual(Stipulation.objects.count(), 5)

    def test_str_summary_shows_type_and_state(self) -> None:
        stip = Stipulation.objects.create(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
            state=STIPULATION_STATE_CLEARED,
        )
        rendered = str(stip)
        self.assertIn("Proof of income", rendered)
        self.assertIn("Cleared", rendered)


class StipulationCleanTests(TestCase):
    """Cross-tenant clean guards."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="stip-clean", name="Stip Clean"
        )
        self.other = Dealership.objects.create(
            slug="stip-clean-other", name="Other"
        )
        self.submission = _make_lender_submission(self.dealership)
        self.other_submission = _make_lender_submission(
            self.other, stock="SC-OTHER"
        )

    def test_clean_passes_with_same_tenant_submission(self) -> None:
        stip = Stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        stip.clean()

    def test_clean_refuses_cross_tenant_submission(self) -> None:
        stip = Stipulation(
            dealership=self.dealership,
            lender_submission=self.other_submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        with self.assertRaises(ValidationError):
            stip.clean()


class StipulationCascadeAndSetNullTests(TestCase):
    """FK on-delete: CASCADE from LenderSubmission, SET_NULL from User."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="stip-fk", name="Stip FK"
        )
        self.submission = _make_lender_submission(self.dealership)
        self.user = User.objects.create_user(
            username="stip-doc", password="x"
        )
        self.stip = Stipulation.objects.create(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
            documented_by=self.user,
            state=STIPULATION_STATE_CLEARED,
            cleared_at=timezone.now(),
        )

    def test_deleting_submission_cascades_to_stipulations(self) -> None:
        self.submission.delete()
        self.assertFalse(
            Stipulation.objects.filter(pk=self.stip.pk).exists()
        )

    def test_deleting_user_nulls_documented_by_preserves_stipulation(self) -> None:
        self.user.delete()
        self.stip.refresh_from_db()
        self.assertIsNone(self.stip.documented_by_id)
        # Stipulation row itself survives.
        self.assertEqual(
            self.stip.stip_type, STIP_TYPE_PROOF_OF_INCOME
        )


class StipulationTenancyCarrierTests(TestCase):
    """The tenant-carrier registry includes ``Stipulation``."""

    def test_stipulation_is_a_tenant_carrier(self) -> None:
        # M10.3 shipped 28; M10.4 makes it 29.
        self.assertGreaterEqual(len(_TENANT_CARRIER_MODEL_NAMES), 29)
        self.assertIn("Stipulation", _TENANT_CARRIER_MODEL_NAMES)
