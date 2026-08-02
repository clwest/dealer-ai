"""Milestone 14 · Increment 1 (SESSION_134) — journal-entry list service verb tests.

Covers :func:`services.accounting.list_journal_entries` per
MILESTONE_14_PLANNING.md §7 M14.1 + §5.b Option B (filter-less list;
filter surface layers at M15+).
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_REVENUE,
    Dealership,
    GLAccount,
)
from dealer_ai.services.accounting import (
    JournalEntryListPage,
    JournalLineInput,
    list_journal_entries,
    post_journal_entry,
    reverse_journal_entry,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership


def _acct(dealership: Dealership, code: str, atype: str) -> GLAccount:
    return GLAccount.objects.create(
        dealership=dealership,
        code=code,
        name=f"Account {code}",
        account_type=atype,
    )


def _post(dealership: Dealership, cash: GLAccount, rev: GLAccount, amount: Decimal, when=None):
    return post_journal_entry(
        dealership=dealership,
        description=f"Post {amount}",
        posted_at=when,
        lines=[
            JournalLineInput(account=cash, debit=amount),
            JournalLineInput(account=rev, credit=amount),
        ],
    )


class ListJournalEntriesTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash = _acct(self.dealership, "M141S-100000", GL_ACCOUNT_TYPE_ASSET)
        self.rev = _acct(self.dealership, "M141S-400000", GL_ACCOUNT_TYPE_REVENUE)

    def test_empty_portfolio_returns_empty_page(self) -> None:
        page = list_journal_entries(dealership=self.dealership)
        self.assertIsInstance(page, JournalEntryListPage)
        self.assertEqual(page.entries, ())
        self.assertEqual(page.total_count, 0)
        self.assertEqual(page.page, 1)
        self.assertEqual(page.page_size, 25)

    def test_returns_entries_recent_first(self) -> None:
        now = timezone.now()
        older = _post(
            self.dealership, self.cash, self.rev, Decimal("10.00"),
            when=now - dt.timedelta(days=2),
        )
        newer = _post(
            self.dealership, self.cash, self.rev, Decimal("20.00"),
            when=now - dt.timedelta(days=1),
        )
        page = list_journal_entries(dealership=self.dealership)
        self.assertEqual(page.total_count, 2)
        self.assertEqual([e.pk for e in page.entries], [newer.pk, older.pk])

    def test_stable_secondary_ordering_by_id_desc(self) -> None:
        # Same posted_at → -id secondary key breaks the tie.
        when = timezone.now()
        first = _post(self.dealership, self.cash, self.rev, Decimal("1.00"), when=when)
        second = _post(self.dealership, self.cash, self.rev, Decimal("2.00"), when=when)
        third = _post(self.dealership, self.cash, self.rev, Decimal("3.00"), when=when)
        page = list_journal_entries(dealership=self.dealership)
        self.assertEqual(
            [e.pk for e in page.entries], [third.pk, second.pk, first.pk]
        )

    def test_pagination_respects_page_and_page_size(self) -> None:
        now = timezone.now()
        entries = [
            _post(
                self.dealership, self.cash, self.rev, Decimal(f"{i}.00"),
                when=now - dt.timedelta(days=i),
            )
            for i in range(1, 8)  # 7 entries total
        ]
        page1 = list_journal_entries(
            dealership=self.dealership, page=1, page_size=3
        )
        self.assertEqual(page1.total_count, 7)
        self.assertEqual(page1.page_size, 3)
        self.assertEqual(len(page1.entries), 3)
        # First page: three most recent (smallest days-ago).
        self.assertEqual(
            [e.pk for e in page1.entries],
            [entries[0].pk, entries[1].pk, entries[2].pk],
        )
        page2 = list_journal_entries(
            dealership=self.dealership, page=2, page_size=3
        )
        self.assertEqual(len(page2.entries), 3)
        self.assertEqual(
            [e.pk for e in page2.entries],
            [entries[3].pk, entries[4].pk, entries[5].pk],
        )
        page3 = list_journal_entries(
            dealership=self.dealership, page=3, page_size=3
        )
        self.assertEqual(len(page3.entries), 1)  # 7 % 3 = 1 remainder.
        self.assertEqual([e.pk for e in page3.entries], [entries[6].pk])

    def test_annotates_total_debit_per_entry(self) -> None:
        entry = _post(
            self.dealership, self.cash, self.rev, Decimal("42.00")
        )
        page = list_journal_entries(dealership=self.dealership)
        found = next(e for e in page.entries if e.pk == entry.pk)
        self.assertEqual(found.total_debit, Decimal("42.00"))

    def test_includes_reversal_entries_as_ordinary_rows(self) -> None:
        original = _post(
            self.dealership, self.cash, self.rev, Decimal("15.00"),
            when=timezone.now() - dt.timedelta(days=1),
        )
        reversal = reverse_journal_entry(
            dealership=self.dealership,
            entry=original,
            reason="Correction",
        )
        page = list_journal_entries(dealership=self.dealership)
        # Reversal is a JournalEntry with reverses_id set — appears in the list.
        self.assertEqual(page.total_count, 2)
        pks = {e.pk for e in page.entries}
        self.assertEqual(pks, {original.pk, reversal.pk})
        reversal_row = next(e for e in page.entries if e.pk == reversal.pk)
        self.assertEqual(reversal_row.reverses_id, original.pk)

    def test_tenancy_scoping_excludes_other_dealerships(self) -> None:
        other = Dealership.objects.create(slug="m141s-other", name="Other")
        seed_default_coa(other)
        other_cash = _acct(other, "M141S-OTHER-100000", GL_ACCOUNT_TYPE_ASSET)
        other_rev = _acct(other, "M141S-OTHER-400000", GL_ACCOUNT_TYPE_REVENUE)
        _post(other, other_cash, other_rev, Decimal("999.00"))
        # Post one in the default tenant.
        mine = _post(self.dealership, self.cash, self.rev, Decimal("1.00"))
        page = list_journal_entries(dealership=self.dealership)
        self.assertEqual(page.total_count, 1)
        self.assertEqual([e.pk for e in page.entries], [mine.pk])

    def test_page_beyond_range_returns_empty_but_valid(self) -> None:
        _post(self.dealership, self.cash, self.rev, Decimal("5.00"))
        page = list_journal_entries(
            dealership=self.dealership, page=99, page_size=25
        )
        self.assertEqual(page.entries, ())
        self.assertEqual(page.total_count, 1)
        self.assertEqual(page.page, 99)

    def test_returns_frozen_dataclass(self) -> None:
        page = list_journal_entries(dealership=self.dealership)
        with self.assertRaises(Exception):
            # dataclasses.FrozenInstanceError inherits from AttributeError
            # in Python 3.10+; either raise is acceptable.
            page.total_count = 999  # type: ignore[misc]
