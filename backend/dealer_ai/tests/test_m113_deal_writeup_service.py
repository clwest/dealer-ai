"""Milestone 11 · Increment 3 (SESSION_116) — DealWriteup service tests.

Locks the three verbs in :mod:`services.deal_writeups` per
``MILESTONE_11_PLANNING.md`` §1.3 + §5.e Option A + SESSION_116 §0.a
M11.3 amendment.

Coverage:

- ``record_deal_writeup`` — happy path, minimal call defaults
  write_up_at, cross-tenant lead / vehicle raises.
- ``approve_deal_writeup`` — sets timestamp + user, idempotent
  (re-approval overwrites).
- ``hand_off_to_fandi`` — happy path creates + attaches CA, sets
  timestamp; refuses unapproved; refuses re-handoff; auto-copied
  CA notes contain writeup terms; source_format override respected.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CREDIT_APP_FORMAT_PAPER,
    CREDIT_APP_FORMAT_TABLET,
    CreditApplication,
    CustomerLead,
    Dealership,
    DealWriteup,
    Vehicle,
)
from dealer_ai.services.deal_writeups import (
    CrossTenantDealWriteupError,
    WriteupAlreadyHandedOffError,
    WriteupNotApprovedError,
    approve_deal_writeup,
    hand_off_to_fandi,
    record_deal_writeup,
)


User = get_user_model()


def _make_vehicle(dealership: Dealership, stock: str = "DWS-1") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("31000.00"),
        dealership=dealership,
    )


class RecordDealWriteupTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dws-record", name="DWS Record"
        )
        self.other = Dealership.objects.create(
            slug="dws-record-other", name="DWS Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Recorda"
        )
        self.vehicle = _make_vehicle(self.dealership)
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross"
        )
        self.cross_vehicle = _make_vehicle(self.other, "DWS-B-1")

    def test_happy_path_writes_all_fields(self) -> None:
        writeup = record_deal_writeup(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            vehicle_price=Decimal("28995.00"),
            trade_allowance=Decimal("6500.00"),
            down_payment=Decimal("2000.00"),
            monthly_payment_target=Decimal("475.00"),
            term_months_target=72,
            apr_target=Decimal("7.49"),
            notes="Customer values low monthly payment.",
        )
        self.assertEqual(writeup.vehicle_price, Decimal("28995.00"))
        self.assertEqual(writeup.term_months_target, 72)
        self.assertEqual(writeup.notes, "Customer values low monthly payment.")

    def test_minimal_defaults_write_up_at_to_now(self) -> None:
        before = timezone.now()
        writeup = record_deal_writeup(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
        )
        after = timezone.now()
        self.assertGreaterEqual(writeup.write_up_at, before)
        self.assertLessEqual(writeup.write_up_at, after)

    def test_cross_tenant_lead_raises(self) -> None:
        with self.assertRaises(CrossTenantDealWriteupError):
            record_deal_writeup(
                dealership=self.dealership,
                lead=self.cross_lead,
                vehicle=self.vehicle,
            )
        self.assertEqual(
            DealWriteup.objects.filter(dealership=self.dealership).count(), 0
        )

    def test_cross_tenant_vehicle_raises(self) -> None:
        with self.assertRaises(CrossTenantDealWriteupError):
            record_deal_writeup(
                dealership=self.dealership,
                lead=self.lead,
                vehicle=self.cross_vehicle,
            )


class ApproveDealWriteupTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dws-approve", name="DWS Approve"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="A"
        )
        self.vehicle = _make_vehicle(self.dealership, "DWS-AP-1")
        self.manager1 = User.objects.create_user(
            username="dws-mgr-1", password="x"
        )
        self.manager2 = User.objects.create_user(
            username="dws-mgr-2", password="x"
        )
        self.writeup = record_deal_writeup(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
        )

    def test_approval_sets_timestamp_and_user(self) -> None:
        result = approve_deal_writeup(
            writeup=self.writeup, approved_by_user=self.manager1
        )
        result.refresh_from_db()
        self.assertIsNotNone(result.sales_manager_approved_at)
        self.assertEqual(
            result.sales_manager_approved_by_user_id, self.manager1.id
        )

    def test_re_approval_overwrites(self) -> None:
        approve_deal_writeup(
            writeup=self.writeup, approved_by_user=self.manager1
        )
        approve_deal_writeup(
            writeup=self.writeup, approved_by_user=self.manager2
        )
        self.writeup.refresh_from_db()
        self.assertEqual(
            self.writeup.sales_manager_approved_by_user_id, self.manager2.id
        )


class HandOffToFandiTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="dws-handoff", name="DWS Handoff"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Harriet Handoff"
        )
        self.vehicle = _make_vehicle(self.dealership, "DWS-H-1")
        self.manager = User.objects.create_user(
            username="dws-h-mgr", password="x"
        )
        self.writeup = record_deal_writeup(
            dealership=self.dealership,
            lead=self.lead,
            vehicle=self.vehicle,
            vehicle_price=Decimal("28500.00"),
            monthly_payment_target=Decimal("450.00"),
            term_months_target=72,
            apr_target=Decimal("7.49"),
        )

    def _approve(self):
        approve_deal_writeup(
            writeup=self.writeup, approved_by_user=self.manager
        )
        self.writeup.refresh_from_db()

    def test_handoff_creates_ca_and_marks_writeup(self) -> None:
        self._approve()
        writeup, credit_app = hand_off_to_fandi(writeup=self.writeup)
        self.assertIsNotNone(writeup.handed_off_to_fandi_at)
        self.assertEqual(credit_app.lead_id, self.lead.id)
        self.assertEqual(credit_app.applicant_full_name, self.lead.name)
        self.assertEqual(credit_app.source_format, CREDIT_APP_FORMAT_TABLET)
        self.assertEqual(credit_app.dealership_id, self.dealership.id)
        self.assertEqual(
            CreditApplication.objects.filter(dealership=self.dealership).count(),
            1,
        )

    def test_handoff_notes_contain_writeup_terms(self) -> None:
        self._approve()
        _, credit_app = hand_off_to_fandi(writeup=self.writeup)
        self.assertIn("Vehicle price", credit_app.notes)
        self.assertIn("$28500", credit_app.notes)
        self.assertIn("Monthly payment target", credit_app.notes)
        self.assertIn("72 months", credit_app.notes)
        self.assertIn("7.49", credit_app.notes)

    def test_handoff_refuses_unapproved(self) -> None:
        with self.assertRaises(WriteupNotApprovedError):
            hand_off_to_fandi(writeup=self.writeup)
        # And no CA was created despite the failed handoff.
        self.assertEqual(
            CreditApplication.objects.filter(dealership=self.dealership).count(),
            0,
        )

    def test_handoff_refuses_re_handoff(self) -> None:
        self._approve()
        hand_off_to_fandi(writeup=self.writeup)
        self.writeup.refresh_from_db()
        with self.assertRaises(WriteupAlreadyHandedOffError):
            hand_off_to_fandi(writeup=self.writeup)
        # Still just one CA — idempotency guard held.
        self.assertEqual(
            CreditApplication.objects.filter(dealership=self.dealership).count(),
            1,
        )

    def test_handoff_source_format_override(self) -> None:
        self._approve()
        _, credit_app = hand_off_to_fandi(
            writeup=self.writeup, source_format=CREDIT_APP_FORMAT_PAPER
        )
        self.assertEqual(credit_app.source_format, CREDIT_APP_FORMAT_PAPER)
