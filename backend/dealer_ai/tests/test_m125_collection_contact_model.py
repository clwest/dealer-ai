"""Milestone 12 · Increment 5 (SESSION_125) — CollectionContact model tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_CONTACT_CHANNEL_CHOICES,
    BHPH_CONTACT_CHANNEL_EMAIL,
    BHPH_CONTACT_CHANNEL_IN_PERSON,
    BHPH_CONTACT_CHANNEL_LETTER,
    BHPH_CONTACT_CHANNEL_PHONE,
    BHPH_CONTACT_CHANNEL_SMS,
    BHPH_CONTACT_OUTCOME_CHOICES,
    BHPH_CONTACT_OUTCOME_CONTACT_MADE,
    BHPH_CONTACT_OUTCOME_LEFT_MESSAGE,
    BHPH_CONTACT_OUTCOME_NO_ANSWER,
    BHPH_CONTACT_OUTCOME_REFUSED_TO_SPEAK,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    CollectionContact,
    Dealership,
    Sale,
    Vehicle,
)


def _make_note(dealership: Dealership, stock: str = "M125-1") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Passat",
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


class CollectionContactDefaultsAndOrderingTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m125-def", name="M125 Defaults"
        )
        self.note = _make_note(self.dealership, stock="M125-DEF")

    def test_defaults(self) -> None:
        contact = CollectionContact.objects.create(
            dealership=self.dealership,
            note=self.note,
            contacted_at=timezone.now(),
            channel=BHPH_CONTACT_CHANNEL_PHONE,
            outcome=BHPH_CONTACT_OUTCOME_LEFT_MESSAGE,
        )
        self.assertEqual(contact.notes, "")
        self.assertIsNone(contact.contacted_by_user)
        self.assertIsNotNone(contact.created_at)

    def test_ordering_is_reverse_contacted_at(self) -> None:
        earlier = CollectionContact.objects.create(
            dealership=self.dealership,
            note=self.note,
            contacted_at=timezone.now() - dt.timedelta(days=1),
            channel=BHPH_CONTACT_CHANNEL_PHONE,
            outcome=BHPH_CONTACT_OUTCOME_NO_ANSWER,
        )
        later = CollectionContact.objects.create(
            dealership=self.dealership,
            note=self.note,
            contacted_at=timezone.now(),
            channel=BHPH_CONTACT_CHANNEL_SMS,
            outcome=BHPH_CONTACT_OUTCOME_CONTACT_MADE,
        )
        self.assertEqual(
            list(CollectionContact.objects.all()), [later, earlier]
        )


class CollectionContactCleanAndCascadeTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m125-clean", name="M125 Clean"
        )
        self.other = Dealership.objects.create(
            slug="m125-clean-other", name="M125 Other"
        )
        self.note = _make_note(self.dealership, stock="M125-CLEAN")
        self.cross_note = _make_note(self.other, stock="M125-CLEAN-X")

    def test_clean_rejects_cross_tenant_note(self) -> None:
        contact = CollectionContact(
            dealership=self.dealership,
            note=self.cross_note,
            contacted_at=timezone.now(),
            channel=BHPH_CONTACT_CHANNEL_PHONE,
            outcome=BHPH_CONTACT_OUTCOME_NO_ANSWER,
        )
        with self.assertRaises(ValidationError) as ctx:
            contact.clean()
        self.assertIn("note", ctx.exception.message_dict)

    def test_note_delete_cascades(self) -> None:
        contact = CollectionContact.objects.create(
            dealership=self.dealership,
            note=self.note,
            contacted_at=timezone.now(),
            channel=BHPH_CONTACT_CHANNEL_PHONE,
            outcome=BHPH_CONTACT_OUTCOME_NO_ANSWER,
        )
        self.note.delete()
        self.assertFalse(
            CollectionContact.objects.filter(pk=contact.pk).exists()
        )


class CollectionContactVocabTests(TestCase):
    def test_channel_vocab_exact_five_value_set(self) -> None:
        vocab = {key for key, _ in BHPH_CONTACT_CHANNEL_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_CONTACT_CHANNEL_PHONE,
                BHPH_CONTACT_CHANNEL_LETTER,
                BHPH_CONTACT_CHANNEL_SMS,
                BHPH_CONTACT_CHANNEL_EMAIL,
                BHPH_CONTACT_CHANNEL_IN_PERSON,
            },
        )

    def test_outcome_vocab_exact_four_value_set(self) -> None:
        vocab = {key for key, _ in BHPH_CONTACT_OUTCOME_CHOICES}
        self.assertEqual(
            vocab,
            {
                BHPH_CONTACT_OUTCOME_CONTACT_MADE,
                BHPH_CONTACT_OUTCOME_LEFT_MESSAGE,
                BHPH_CONTACT_OUTCOME_NO_ANSWER,
                BHPH_CONTACT_OUTCOME_REFUSED_TO_SPEAK,
            },
        )
