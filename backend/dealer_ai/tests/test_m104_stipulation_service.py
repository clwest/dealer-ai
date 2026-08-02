"""Milestone 10 · Increment 4 (SESSION_109) — Stipulation service tests.

Locks the service surface of :mod:`services.f_and_i.stipulation`
per ``MILESTONE_10_PLANNING.md`` §1.4 + §7 M10.4.

Coverage:

- `record_stipulation` happy paths + cross-tenant rejection +
  unknown stip_type.
- `update_stipulation_state` state transitions with `cleared_at`
  auto-population and reset semantics; documented_by attachment;
  notes partial-update; unknown state rejection; any-to-any
  transitions allowed.
- `get_stipulation` tenant-scoped read.
- `list_stipulations_for_submission` FK filter.
"""

from __future__ import annotations

from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_RETENTION_YEARS,
    STIP_TYPE_PROOF_OF_INCOME,
    STIP_TYPE_PROOF_OF_INSURANCE,
    STIPULATION_STATE_CLEARED,
    STIPULATION_STATE_OPEN,
    STIPULATION_STATE_WAIVED,
    CreditApplication,
    CustomerLead,
    DealStructure,
    Dealership,
    LenderProgram,
    LenderSubmission,
    Vehicle,
)
from dealer_ai.services.f_and_i import (
    CrossTenantStipulationError,
    get_stipulation,
    list_stipulations_for_submission,
    record_stipulation,
    update_stipulation_state,
)

User = get_user_model()


def _make_lender_submission(dealership, *, stock: str = "SS-1") -> LenderSubmission:
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
        dealership=dealership, name=f"Prog-{stock}"
    )
    return LenderSubmission.objects.create(
        dealership=dealership,
        deal_structure=deal,
        lender_program=program,
        submitted_at=timezone.now(),
    )


class RecordStipulationTests(TestCase):
    """`record_stipulation` — happy + rejection paths."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="rs", name="Record Stip"
        )
        self.other = Dealership.objects.create(slug="rs-other", name="Other")
        self.submission = _make_lender_submission(self.dealership)
        self.other_submission = _make_lender_submission(
            self.other, stock="RS-OTHER"
        )

    def test_record_creates_open_stipulation(self) -> None:
        stip = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        self.assertEqual(stip.state, STIPULATION_STATE_OPEN)
        self.assertIsNone(stip.cleared_at)
        self.assertIsNone(stip.documented_by_id)
        self.assertEqual(stip.notes, "")

    def test_record_persists_notes(self) -> None:
        stip = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INSURANCE,
            notes="Lender listed as loss payee — need declaration page",
        )
        self.assertIn("loss payee", stip.notes)

    def test_cross_tenant_submission_raises(self) -> None:
        with self.assertRaises(CrossTenantStipulationError):
            record_stipulation(
                dealership=self.dealership,
                lender_submission=self.other_submission,
                stip_type=STIP_TYPE_PROOF_OF_INCOME,
            )

    def test_unknown_stip_type_raises(self) -> None:
        with self.assertRaises(ValueError):
            record_stipulation(
                dealership=self.dealership,
                lender_submission=self.submission,
                stip_type="tax_return",  # not in vocabulary
            )


class UpdateStipulationStateTests(TestCase):
    """`update_stipulation_state` — transitions + cleared_at auto-populate."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="uss", name="Update State"
        )
        self.submission = _make_lender_submission(self.dealership)
        self.user = User.objects.create_user(username="fandi", password="x")
        self.stip = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )

    def test_open_to_cleared_populates_cleared_at_and_documented_by(self) -> None:
        before = timezone.now()
        updated = update_stipulation_state(
            self.stip,
            new_state=STIPULATION_STATE_CLEARED,
            documented_by=self.user,
        )
        updated.refresh_from_db()
        self.assertEqual(updated.state, STIPULATION_STATE_CLEARED)
        self.assertIsNotNone(updated.cleared_at)
        self.assertGreaterEqual(updated.cleared_at, before)
        self.assertEqual(updated.documented_by_id, self.user.pk)

    def test_open_to_waived_populates_cleared_at(self) -> None:
        updated = update_stipulation_state(
            self.stip,
            new_state=STIPULATION_STATE_WAIVED,
            documented_by=self.user,
        )
        updated.refresh_from_db()
        self.assertEqual(updated.state, STIPULATION_STATE_WAIVED)
        self.assertIsNotNone(updated.cleared_at)

    def test_cleared_to_open_resets_cleared_at_to_null(self) -> None:
        # First: clear it.
        update_stipulation_state(
            self.stip,
            new_state=STIPULATION_STATE_CLEARED,
            documented_by=self.user,
        )
        self.stip.refresh_from_db()
        self.assertIsNotNone(self.stip.cleared_at)
        # Then: back to open (operator error correction).
        updated = update_stipulation_state(
            self.stip, new_state=STIPULATION_STATE_OPEN
        )
        updated.refresh_from_db()
        self.assertEqual(updated.state, STIPULATION_STATE_OPEN)
        self.assertIsNone(updated.cleared_at)

    def test_cleared_to_waived_preserves_original_cleared_at(self) -> None:
        # cleared_at should be set on the first transition and
        # not overwritten on subsequent cleared/waived transitions.
        update_stipulation_state(
            self.stip,
            new_state=STIPULATION_STATE_CLEARED,
            documented_by=self.user,
        )
        self.stip.refresh_from_db()
        original_cleared_at = self.stip.cleared_at
        # Move to waived — cleared_at should stay the same.
        update_stipulation_state(
            self.stip, new_state=STIPULATION_STATE_WAIVED
        )
        self.stip.refresh_from_db()
        self.assertEqual(self.stip.cleared_at, original_cleared_at)

    def test_notes_partial_update(self) -> None:
        update_stipulation_state(
            self.stip,
            new_state=STIPULATION_STATE_CLEARED,
            documented_by=self.user,
            notes="Received paystub via email.",
        )
        self.stip.refresh_from_db()
        self.assertEqual(self.stip.notes, "Received paystub via email.")

    def test_notes_preserved_when_omitted(self) -> None:
        # Set an initial note.
        update_stipulation_state(
            self.stip,
            new_state=STIPULATION_STATE_CLEARED,
            documented_by=self.user,
            notes="First note.",
        )
        # Update without touching notes.
        update_stipulation_state(
            self.stip, new_state=STIPULATION_STATE_WAIVED
        )
        self.stip.refresh_from_db()
        self.assertEqual(self.stip.notes, "First note.")

    def test_unknown_state_raises(self) -> None:
        with self.assertRaises(ValueError):
            update_stipulation_state(self.stip, new_state="funded")

    def test_any_to_any_transition_allowed_at_m104(self) -> None:
        # No transition constraints at M10.4 — cleared → open →
        # waived is legitimate operator behavior.
        update_stipulation_state(
            self.stip, new_state=STIPULATION_STATE_CLEARED
        )
        update_stipulation_state(
            self.stip, new_state=STIPULATION_STATE_OPEN
        )
        updated = update_stipulation_state(
            self.stip, new_state=STIPULATION_STATE_WAIVED
        )
        self.assertEqual(updated.state, STIPULATION_STATE_WAIVED)


class GetAndListStipulationTests(TestCase):
    """`get_stipulation` + `list_stipulations_for_submission`."""

    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="gls", name="Get List Stip"
        )
        self.other = Dealership.objects.create(slug="gls-other", name="Other")
        self.submission = _make_lender_submission(self.dealership)
        self.stip1 = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INCOME,
        )
        self.stip2 = record_stipulation(
            dealership=self.dealership,
            lender_submission=self.submission,
            stip_type=STIP_TYPE_PROOF_OF_INSURANCE,
        )

    def test_get_returns_matching_tenant_row(self) -> None:
        found = get_stipulation(self.stip1.pk, dealership=self.dealership)
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.stip1.pk)

    def test_get_returns_none_for_cross_tenant_pk(self) -> None:
        self.assertIsNone(
            get_stipulation(self.stip1.pk, dealership=self.other)
        )

    def test_get_returns_none_for_unknown_pk(self) -> None:
        self.assertIsNone(
            get_stipulation(999999, dealership=self.dealership)
        )

    def test_list_returns_all_stipulations_for_submission(self) -> None:
        pks = set(
            list_stipulations_for_submission(self.submission).values_list(
                "pk", flat=True
            )
        )
        self.assertEqual(pks, {self.stip1.pk, self.stip2.pk})
