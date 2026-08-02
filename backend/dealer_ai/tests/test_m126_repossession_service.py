"""Milestone 12 · Increment 6 (SESSION_126) — Repossession service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_REPO_STATE_ORDERED,
    BHPH_REPO_STATE_RE_INTAKED,
    BHPH_REPO_STATE_RECOVERED,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    ConditionReport,
    Dealership,
    Repossession,
    Sale,
    Vehicle,
)
from dealer_ai.services.repossessions import (
    CrossTenantConditionReportError,
    CrossTenantRepossessionError,
    InvalidStateTransitionError,
    RepossessionAlreadyTerminalError,
    list_repossessions,
    mark_re_intaked,
    mark_recovered,
    record_repossession,
)


def _make_note(dealership: Dealership, stock: str = "M126-SVC") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Camry",
        price=Decimal("10500.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("10500.00"),
        finance_type=SALE_FINANCE_TYPE_BHPH,
        gross_realized=Decimal("1200.00"),
    )
    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=Decimal("8000.00"),
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
    )


def _make_condition_report(
    dealership: Dealership, vehicle: Vehicle
) -> ConditionReport:
    return ConditionReport.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        inspector_name="Post-Repo",
        inspected_at=timezone.now(),
        mileage_at_inspection=52000,
    )


class RecordRepossessionTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m126-svc-rec", name="M126 Svc Rec"
        )
        self.other = Dealership.objects.create(
            slug="m126-svc-rec-other", name="M126 Other"
        )
        self.note = _make_note(self.dealership, stock="M126-SVC-REC")
        self.cross_note = _make_note(self.other, stock="M126-SVC-REC-X")

    def test_happy_path(self) -> None:
        repo = record_repossession(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace Recovery",
        )
        self.assertIsInstance(repo, Repossession)
        self.assertEqual(repo.state, BHPH_REPO_STATE_ORDERED)
        self.assertEqual(repo.agent_name, "Ace Recovery")

    def test_cross_tenant_note_raises(self) -> None:
        with self.assertRaises(CrossTenantRepossessionError):
            record_repossession(
                dealership=self.dealership,
                note=self.cross_note,
                ordered_at=timezone.now(),
                agent_name="Ace Recovery",
            )


class MarkRecoveredTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m126-svc-mr", name="M126 Svc MR"
        )
        self.note = _make_note(self.dealership, stock="M126-SVC-MR")
        self.repo = record_repossession(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace",
        )

    def test_happy_path_transitions(self) -> None:
        result = mark_recovered(
            dealership=self.dealership,
            repossession=self.repo,
            recovery_location="Owner residence",
        )
        self.assertEqual(result.state, BHPH_REPO_STATE_RECOVERED)
        self.assertIsNotNone(result.recovered_at)
        self.assertEqual(result.recovery_location, "Owner residence")

    def test_default_recovered_at_uses_now(self) -> None:
        before = timezone.now()
        result = mark_recovered(
            dealership=self.dealership, repossession=self.repo
        )
        self.assertGreaterEqual(result.recovered_at, before)

    def test_terminal_re_intaked_raises(self) -> None:
        self.repo.state = BHPH_REPO_STATE_RE_INTAKED
        self.repo.recovered_at = timezone.now()
        self.repo.save()
        with self.assertRaises(RepossessionAlreadyTerminalError):
            mark_recovered(
                dealership=self.dealership, repossession=self.repo
            )

    def test_double_recovered_raises_invalid_transition(self) -> None:
        mark_recovered(
            dealership=self.dealership, repossession=self.repo
        )
        with self.assertRaises(InvalidStateTransitionError):
            mark_recovered(
                dealership=self.dealership, repossession=self.repo
            )


class MarkReIntakedTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m126-svc-mi", name="M126 Svc MI"
        )
        self.other = Dealership.objects.create(
            slug="m126-svc-mi-other", name="M126 Other"
        )
        self.note = _make_note(self.dealership, stock="M126-SVC-MI")
        self.vehicle = Vehicle.objects.get(stock_number="M126-SVC-MI")
        self.report = _make_condition_report(self.dealership, self.vehicle)
        cross_vehicle = Vehicle.objects.create(
            stock_number="M126-SVC-MI-X",
            year=2020,
            model="Corolla",
            price=Decimal("10500.00"),
            dealership=self.other,
        )
        self.cross_report = _make_condition_report(self.other, cross_vehicle)
        self.repo = record_repossession(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace",
        )
        mark_recovered(
            dealership=self.dealership, repossession=self.repo
        )

    def test_happy_path_transitions_and_attaches_report(self) -> None:
        result = mark_re_intaked(
            dealership=self.dealership,
            repossession=self.repo,
            condition_report=self.report,
        )
        self.assertEqual(result.state, BHPH_REPO_STATE_RE_INTAKED)
        self.assertEqual(
            result.intake_condition_report_id, self.report.pk
        )

    def test_cross_tenant_condition_report_raises(self) -> None:
        with self.assertRaises(CrossTenantConditionReportError):
            mark_re_intaked(
                dealership=self.dealership,
                repossession=self.repo,
                condition_report=self.cross_report,
            )

    def test_from_ordered_raises_invalid_transition(self) -> None:
        # Reset to ordered.
        self.repo.state = BHPH_REPO_STATE_ORDERED
        self.repo.recovered_at = None
        self.repo.save()
        with self.assertRaises(InvalidStateTransitionError):
            mark_re_intaked(
                dealership=self.dealership,
                repossession=self.repo,
                condition_report=self.report,
            )

    def test_already_terminal_raises(self) -> None:
        mark_re_intaked(
            dealership=self.dealership,
            repossession=self.repo,
            condition_report=self.report,
        )
        with self.assertRaises(RepossessionAlreadyTerminalError):
            mark_re_intaked(
                dealership=self.dealership,
                repossession=self.repo,
                condition_report=self.report,
            )


class ListRepossessionsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m126-svc-list", name="M126 Svc List"
        )
        self.other = Dealership.objects.create(
            slug="m126-svc-list-other", name="M126 Other"
        )
        self.note = _make_note(self.dealership, stock="M126-SVC-LIST")
        self.cross_note = _make_note(self.other, stock="M126-SVC-LIST-X")
        for _ in range(2):
            record_repossession(
                dealership=self.dealership,
                note=self.note,
                ordered_at=timezone.now(),
                agent_name="Ace",
            )

    def test_returns_repos_for_note(self) -> None:
        repos = list_repossessions(
            dealership=self.dealership, note=self.note
        )
        self.assertEqual(len(repos), 2)

    def test_cross_tenant_returns_empty(self) -> None:
        repos = list_repossessions(
            dealership=self.dealership, note=self.cross_note
        )
        self.assertEqual(repos, [])
