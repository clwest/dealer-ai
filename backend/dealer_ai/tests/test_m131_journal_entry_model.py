"""Milestone 13 · Increment 1 (SESSION_129) — JournalEntry + line model tests."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    Dealership,
    GLAccount,
    JournalEntry,
    JournalEntryLine,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_account(dealership: Dealership, code: str, account_type=GL_ACCOUNT_TYPE_ASSET) -> GLAccount:
    return GLAccount.objects.create(
        dealership=dealership,
        code=code,
        name=f"Test {code}",
        account_type=account_type,
    )


class JournalEntryModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.account = _make_account(self.dealership, "199001")

    def test_create_journal_entry(self) -> None:
        entry = JournalEntry.objects.create(
            dealership=self.dealership,
            description="Test posting",
            posted_at=timezone.now(),
        )
        self.assertIsNone(entry.reverses_id)
        self.assertEqual(entry.reason, "")
        self.assertEqual(entry.reversed_by.count(), 0)

    def test_str_includes_description_and_posted_at(self) -> None:
        entry = JournalEntry.objects.create(
            dealership=self.dealership,
            description="Cost accrual 7/31",
            posted_at=timezone.now(),
        )
        rendered = str(entry)
        self.assertIn("Cost accrual 7/31", rendered)
        self.assertIn(str(entry.pk), rendered)

    def test_reverses_self_fk_populates_reverse_side(self) -> None:
        original = JournalEntry.objects.create(
            dealership=self.dealership,
            description="Original",
            posted_at=timezone.now(),
        )
        reversal = JournalEntry.objects.create(
            dealership=self.dealership,
            description="Reversal of original",
            posted_at=timezone.now(),
            reverses=original,
            reason="Duplicate posting",
        )
        self.assertEqual(reversal.reverses_id, original.pk)
        self.assertIn(reversal, original.reversed_by.all())

    def test_cross_tenant_reverses_rejected_by_clean(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m131b", name="Other"
        )
        original = JournalEntry.objects.create(
            dealership=other,
            description="Belongs to other tenant",
            posted_at=timezone.now(),
        )
        bad = JournalEntry(
            dealership=self.dealership,
            description="Cross-tenant reversal attempt",
            posted_at=timezone.now(),
            reverses=original,
            reason="Should fail",
        )
        with self.assertRaises(ValidationError) as cm:
            bad.full_clean()
        self.assertIn("reverses", cm.exception.message_dict)


class JournalEntryLineModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.account = _make_account(self.dealership, "199002")
        self.entry = JournalEntry.objects.create(
            dealership=self.dealership,
            description="Line-test entry",
            posted_at=timezone.now(),
        )

    def test_create_line(self) -> None:
        line = JournalEntryLine.objects.create(
            dealership=self.dealership,
            entry=self.entry,
            account=self.account,
            debit=Decimal("100.00"),
            memo="test debit",
        )
        self.assertEqual(line.debit, Decimal("100.00"))
        self.assertEqual(line.credit, Decimal("0.00"))
        self.assertIn(line, self.entry.lines.all())

    def test_cross_tenant_account_rejected_by_clean(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m131c", name="Other"
        )
        other_account = _make_account(other, "199002")
        bad_line = JournalEntryLine(
            dealership=self.dealership,
            entry=self.entry,
            account=other_account,
            debit=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError) as cm:
            bad_line.full_clean()
        self.assertIn("account", cm.exception.message_dict)

    def test_cross_tenant_entry_rejected_by_clean(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-m131d", name="Other"
        )
        other_entry = JournalEntry.objects.create(
            dealership=other,
            description="Other tenant entry",
            posted_at=timezone.now(),
        )
        bad_line = JournalEntryLine(
            dealership=self.dealership,
            entry=other_entry,
            account=self.account,
            debit=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError) as cm:
            bad_line.full_clean()
        self.assertIn("entry", cm.exception.message_dict)
