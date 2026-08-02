"""Milestone 12 · Increment 1 (SESSION_121) — BhphNote model tests.

Locks the schema surface of :class:`dealer_ai.models.BhphNote` per
``MILESTONE_12_PLANNING.md`` §1.1 + §5.a Option A (recorded in §0.a).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_BIWEEKLY,
    BHPH_PAYMENT_FREQUENCY_CHOICES,
    BHPH_PAYMENT_FREQUENCY_SEMI_MONTHLY,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    SALE_FINANCE_TYPE_BHPH,
    SALE_FINANCE_TYPE_CASH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)


def _make_sale(
    dealership: Dealership,
    stock: str = "BHPH-M121",
    finance_type: str = SALE_FINANCE_TYPE_BHPH,
) -> Sale:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Camry",
        price=Decimal("12500.00"),
        dealership=dealership,
    )
    return Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("12500.00"),
        finance_type=finance_type,
        gross_realized=Decimal("1500.00"),
    )


class BhphNoteDefaultsAndOrderingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-def", name="BHPH Defaults"
        )
        self.sale_a = _make_sale(self.dealership, stock="BHPH-A")
        self.sale_b = _make_sale(self.dealership, stock="BHPH-B")

    def test_defaults(self) -> None:
        note = BhphNote.objects.create(
            dealership=self.dealership,
            sale=self.sale_a,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        self.assertEqual(note.default_grace_days, 5)
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)

    def test_ordering_is_reverse_created_at(self) -> None:
        earlier = BhphNote.objects.create(
            dealership=self.dealership,
            sale=self.sale_a,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        later = BhphNote.objects.create(
            dealership=self.dealership,
            sale=self.sale_b,
            principal_financed=Decimal("8000.00"),
            apr=Decimal("21.90"),
            term_weeks=104,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_BIWEEKLY,
            payment_amount=Decimal("160.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        self.assertEqual(list(BhphNote.objects.all()), [later, earlier])


class BhphNoteCleanTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-clean", name="BHPH Clean"
        )
        self.other = Dealership.objects.create(
            slug="bhph-clean-other", name="BHPH Other"
        )
        self.bhph_sale = _make_sale(self.dealership, stock="BHPH-CLEAN-1")
        self.cash_sale = _make_sale(
            self.dealership,
            stock="BHPH-CLEAN-CASH",
            finance_type=SALE_FINANCE_TYPE_CASH,
        )
        self.cross_sale = _make_sale(self.other, stock="BHPH-CLEAN-X")

    def test_clean_rejects_cross_tenant_sale(self) -> None:
        note = BhphNote(
            dealership=self.dealership,
            sale=self.cross_sale,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            note.clean()
        self.assertIn("sale", ctx.exception.message_dict)

    def test_clean_rejects_non_bhph_sale(self) -> None:
        note = BhphNote(
            dealership=self.dealership,
            sale=self.cash_sale,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        with self.assertRaises(ValidationError) as ctx:
            note.clean()
        self.assertIn("sale", ctx.exception.message_dict)

    def test_clean_passes_for_bhph_sale_in_tenant(self) -> None:
        note = BhphNote(
            dealership=self.dealership,
            sale=self.bhph_sale,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        note.clean()  # should not raise


class BhphNoteCascadeAndOneToOneTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="bhph-otc", name="BHPH OTO"
        )
        self.sale = _make_sale(self.dealership, stock="BHPH-OTO-1")

    def test_sale_delete_cascades_to_note(self) -> None:
        note = BhphNote.objects.create(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        self.sale.delete()
        self.assertFalse(BhphNote.objects.filter(pk=note.pk).exists())

    def test_duplicate_note_per_sale_raises_integrity_error(self) -> None:
        BhphNote.objects.create(
            dealership=self.dealership,
            sale=self.sale,
            principal_financed=Decimal("10000.00"),
            apr=Decimal("21.90"),
            term_weeks=130,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("100.00"),
            first_payment_due=dt.date(2026, 9, 1),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                BhphNote.objects.create(
                    dealership=self.dealership,
                    sale=self.sale,
                    principal_financed=Decimal("8000.00"),
                    apr=Decimal("21.90"),
                    term_weeks=104,
                    payment_frequency=BHPH_PAYMENT_FREQUENCY_BIWEEKLY,
                    payment_amount=Decimal("160.00"),
                    first_payment_due=dt.date(2026, 9, 1),
                )


class BhphNoteVocabTests(TestCase):
    def test_payment_frequency_vocab_exact_set(self) -> None:
        vocab = {key for key, _ in BHPH_PAYMENT_FREQUENCY_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_PAYMENT_FREQUENCY_WEEKLY,
                BHPH_PAYMENT_FREQUENCY_BIWEEKLY,
                BHPH_PAYMENT_FREQUENCY_SEMI_MONTHLY,
            },
        )
