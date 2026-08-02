"""Milestone 12 · Increment 6 (SESSION_126) — Repossession model tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_REPO_STATE_CHOICES,
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


def _make_note(dealership: Dealership, stock: str = "M126-1") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Prius",
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
        inspector_name="Post-Repo Inspector",
        inspected_at=timezone.now(),
        mileage_at_inspection=52000,
    )


class RepossessionDefaultsAndOrderingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m126-def", name="M126 Defaults"
        )
        self.note = _make_note(self.dealership, stock="M126-DEF")

    def test_defaults(self) -> None:
        repo = Repossession.objects.create(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace Recovery",
        )
        self.assertEqual(repo.state, BHPH_REPO_STATE_ORDERED)
        self.assertIsNone(repo.recovered_at)
        self.assertEqual(repo.recovery_location, "")
        self.assertIsNone(repo.intake_condition_report)
        self.assertEqual(repo.notes, "")

    def test_ordering_is_reverse_ordered_at(self) -> None:
        earlier = Repossession.objects.create(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now() - dt.timedelta(days=1),
            agent_name="Ace Recovery",
        )
        later = Repossession.objects.create(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Blitz Recovery",
        )
        self.assertEqual(list(Repossession.objects.all()), [later, earlier])


class RepossessionCleanAndCascadeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m126-clean", name="M126 Clean"
        )
        self.other = Dealership.objects.create(
            slug="m126-clean-other", name="M126 Other"
        )
        self.note = _make_note(self.dealership, stock="M126-CLEAN")
        self.cross_note = _make_note(self.other, stock="M126-CLEAN-X")

    def test_clean_rejects_cross_tenant_note(self) -> None:
        repo = Repossession(
            dealership=self.dealership,
            note=self.cross_note,
            ordered_at=timezone.now(),
            agent_name="Ace",
        )
        with self.assertRaises(ValidationError) as ctx:
            repo.clean()
        self.assertIn("note", ctx.exception.message_dict)

    def test_clean_rejects_cross_tenant_condition_report(self) -> None:
        cross_vehicle = Vehicle.objects.get(stock_number="M126-CLEAN-X")
        cross_report = _make_condition_report(self.other, cross_vehicle)
        repo = Repossession(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace",
            intake_condition_report=cross_report,
        )
        with self.assertRaises(ValidationError) as ctx:
            repo.clean()
        self.assertIn("intake_condition_report", ctx.exception.message_dict)

    def test_note_delete_cascades(self) -> None:
        repo = Repossession.objects.create(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace",
        )
        self.note.delete()
        self.assertFalse(Repossession.objects.filter(pk=repo.pk).exists())

    def test_condition_report_delete_sets_null(self) -> None:
        vehicle = Vehicle.objects.get(stock_number="M126-CLEAN")
        report = _make_condition_report(self.dealership, vehicle)
        repo = Repossession.objects.create(
            dealership=self.dealership,
            note=self.note,
            ordered_at=timezone.now(),
            agent_name="Ace",
            state=BHPH_REPO_STATE_RE_INTAKED,
            recovered_at=timezone.now(),
            intake_condition_report=report,
        )
        report.delete()
        repo.refresh_from_db()
        self.assertIsNone(repo.intake_condition_report)
        # Repo record survives — historical evidence.
        self.assertTrue(
            Repossession.objects.filter(pk=repo.pk).exists()
        )


class RepossessionVocabTests(TestCase):
    def test_state_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BHPH_REPO_STATE_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_REPO_STATE_ORDERED,
                BHPH_REPO_STATE_RECOVERED,
                BHPH_REPO_STATE_RE_INTAKED,
            },
        )
