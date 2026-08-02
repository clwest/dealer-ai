"""Milestone 12 · Increment 5 (SESSION_125) — CollectionContact service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_CONTACT_CHANNEL_PHONE,
    BHPH_CONTACT_OUTCOME_CONTACT_MADE,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    CollectionContact,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.collection_contacts import (
    CrossTenantContactError,
    UnknownChannelError,
    UnknownOutcomeError,
    list_contacts,
    record_contact,
)


def _make_note(dealership: Dealership, stock: str = "M125-SVC") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Jetta",
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


class RecordContactTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m125-svc", name="M125 Svc"
        )
        self.other = Dealership.objects.create(
            slug="m125-svc-other", name="M125 Other"
        )
        self.note = _make_note(self.dealership, stock="M125-SVC")
        self.cross_note = _make_note(self.other, stock="M125-SVC-X")

    def test_happy_path(self) -> None:
        contact = record_contact(
            dealership=self.dealership,
            note=self.note,
            contacted_at=timezone.now(),
            channel=BHPH_CONTACT_CHANNEL_PHONE,
            outcome=BHPH_CONTACT_OUTCOME_CONTACT_MADE,
        )
        self.assertIsInstance(contact, CollectionContact)
        self.assertEqual(contact.dealership_id, self.dealership.pk)
        self.assertEqual(contact.note_id, self.note.pk)

    def test_cross_tenant_note_raises(self) -> None:
        with self.assertRaises(CrossTenantContactError):
            record_contact(
                dealership=self.dealership,
                note=self.cross_note,
                contacted_at=timezone.now(),
                channel=BHPH_CONTACT_CHANNEL_PHONE,
                outcome=BHPH_CONTACT_OUTCOME_CONTACT_MADE,
            )

    def test_unknown_channel_raises(self) -> None:
        with self.assertRaises(UnknownChannelError):
            record_contact(
                dealership=self.dealership,
                note=self.note,
                contacted_at=timezone.now(),
                channel="carrier_pigeon",
                outcome=BHPH_CONTACT_OUTCOME_CONTACT_MADE,
            )

    def test_unknown_outcome_raises(self) -> None:
        with self.assertRaises(UnknownOutcomeError):
            record_contact(
                dealership=self.dealership,
                note=self.note,
                contacted_at=timezone.now(),
                channel=BHPH_CONTACT_CHANNEL_PHONE,
                outcome="wandered_away",
            )


class ListContactsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m125-svc-list", name="M125 Svc List"
        )
        self.other = Dealership.objects.create(
            slug="m125-svc-list-other", name="M125 Other"
        )
        self.note = _make_note(self.dealership, stock="M125-SVC-LIST")
        self.cross_note = _make_note(self.other, stock="M125-SVC-LIST-X")
        for _ in range(3):
            record_contact(
                dealership=self.dealership,
                note=self.note,
                contacted_at=timezone.now(),
                channel=BHPH_CONTACT_CHANNEL_PHONE,
                outcome=BHPH_CONTACT_OUTCOME_CONTACT_MADE,
            )

    def test_returns_contacts_for_note(self) -> None:
        contacts = list_contacts(
            dealership=self.dealership, note=self.note
        )
        self.assertEqual(len(contacts), 3)

    def test_cross_tenant_returns_empty(self) -> None:
        contacts = list_contacts(
            dealership=self.dealership, note=self.cross_note
        )
        self.assertEqual(contacts, [])
