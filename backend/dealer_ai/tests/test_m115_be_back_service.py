"""Milestone 11 · Increment 5 (SESSION_118) — BeBack service tests.

Locks the three verbs in :mod:`services.be_backs` per
``MILESTONE_11_PLANNING.md`` §1.5 + §5.g Options A / A / B.
"""

from __future__ import annotations

import datetime as dt

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BE_BACK_REASON_BRING_CO_SIGNER,
    BE_BACK_REASON_TEST_DRIVE,
    BE_BACK_STATE_NO_SHOW,
    BE_BACK_STATE_PROMISED,
    BE_BACK_STATE_RETURNED,
    BeBack,
    CustomerLead,
    Dealership,
)
from dealer_ai.services.be_backs import (
    BeBackAlreadyTerminalError,
    CrossTenantBeBackError,
    UnknownReasonError,
    mark_no_show,
    mark_returned,
    record_be_back,
)


class RecordBeBackTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bb-svc-rec", name="BB Svc Rec"
        )
        self.other = Dealership.objects.create(
            slug="bb-svc-rec-other", name="BB Svc Rec Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Rec"
        )
        self.cross_lead = CustomerLead.objects.create(
            dealership=self.other, name="Cross Rec"
        )

    def test_happy_path_sets_promised_state(self) -> None:
        promised_at = timezone.now() + dt.timedelta(days=1)
        bb = record_be_back(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=promised_at,
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
            notes="Says he'll bring wife.",
        )
        self.assertEqual(bb.state, BE_BACK_STATE_PROMISED)
        self.assertEqual(bb.promised_reason, BE_BACK_REASON_TEST_DRIVE)
        self.assertEqual(bb.notes, "Says he'll bring wife.")
        self.assertIsNone(bb.actual_return_at)

    def test_cross_tenant_lead_raises(self) -> None:
        with self.assertRaises(CrossTenantBeBackError):
            record_be_back(
                dealership=self.dealership,
                lead=self.cross_lead,
                promised_at=timezone.now(),
                promised_reason=BE_BACK_REASON_TEST_DRIVE,
            )
        self.assertEqual(
            BeBack.objects.filter(dealership=self.dealership).count(), 0
        )

    def test_unknown_reason_raises(self) -> None:
        with self.assertRaises(UnknownReasonError):
            record_be_back(
                dealership=self.dealership,
                lead=self.lead,
                promised_at=timezone.now(),
                promised_reason="wants_espresso",
            )


class MarkReturnedTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bb-svc-ret", name="BB Svc Ret"
        )
        self.other = Dealership.objects.create(
            slug="bb-svc-ret-other", name="BB Svc Ret Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Rita"
        )
        self.bb = record_be_back(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now() + dt.timedelta(days=1),
            promised_reason=BE_BACK_REASON_TEST_DRIVE,
        )

    def test_happy_path_transitions_state_and_defaults_time(self) -> None:
        before = timezone.now()
        mark_returned(dealership=self.dealership, be_back=self.bb)
        after = timezone.now()
        self.bb.refresh_from_db()
        self.assertEqual(self.bb.state, BE_BACK_STATE_RETURNED)
        self.assertGreaterEqual(self.bb.actual_return_at, before)
        self.assertLessEqual(self.bb.actual_return_at, after)

    def test_cross_tenant_raises(self) -> None:
        with self.assertRaises(CrossTenantBeBackError):
            mark_returned(dealership=self.other, be_back=self.bb)

    def test_terminal_raises(self) -> None:
        mark_returned(dealership=self.dealership, be_back=self.bb)
        self.bb.refresh_from_db()
        with self.assertRaises(BeBackAlreadyTerminalError):
            mark_returned(dealership=self.dealership, be_back=self.bb)
        with self.assertRaises(BeBackAlreadyTerminalError):
            mark_no_show(dealership=self.dealership, be_back=self.bb)


class MarkNoShowTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bb-svc-ns", name="BB Svc NS"
        )
        self.other = Dealership.objects.create(
            slug="bb-svc-ns-other", name="BB Svc NS Other"
        )
        self.lead = CustomerLead.objects.create(
            dealership=self.dealership, name="Nick"
        )
        self.bb = record_be_back(
            dealership=self.dealership,
            lead=self.lead,
            promised_at=timezone.now() - dt.timedelta(hours=6),
            promised_reason=BE_BACK_REASON_BRING_CO_SIGNER,
        )

    def test_happy_path_transitions_state_leaves_return_null(self) -> None:
        mark_no_show(dealership=self.dealership, be_back=self.bb)
        self.bb.refresh_from_db()
        self.assertEqual(self.bb.state, BE_BACK_STATE_NO_SHOW)
        self.assertIsNone(self.bb.actual_return_at)

    def test_cross_tenant_raises(self) -> None:
        with self.assertRaises(CrossTenantBeBackError):
            mark_no_show(dealership=self.other, be_back=self.bb)

    def test_terminal_raises(self) -> None:
        mark_no_show(dealership=self.dealership, be_back=self.bb)
        self.bb.refresh_from_db()
        with self.assertRaises(BeBackAlreadyTerminalError):
            mark_no_show(dealership=self.dealership, be_back=self.bb)
