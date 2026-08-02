"""Milestone 13 · Increment 1 (SESSION_129) — accounting service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EXPENSE,
    GL_ACCOUNT_TYPE_REVENUE,
    Dealership,
    GLAccount,
)
from dealer_ai.services.accounting import (
    DEFAULT_COA,
    CrossTenantGLAccountError,
    CrossTenantJournalEntryError,
    EmptyJournalEntryError,
    ImmutableJournalEntryError,
    InvalidJournalLineError,
    JournalLineInput,
    UnbalancedJournalEntryError,
    get_journal_entry,
    post_journal_entry,
    reverse_journal_entry,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership


def _acct(dealership: Dealership, code: str, atype=GL_ACCOUNT_TYPE_ASSET) -> GLAccount:
    return GLAccount.objects.create(
        dealership=dealership,
        code=code,
        name=f"Test {code}",
        account_type=atype,
    )


class PostJournalEntryTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash = _acct(self.dealership, "S13-100000")
        self.revenue = _acct(
            self.dealership, "S13-400000", GL_ACCOUNT_TYPE_REVENUE
        )

    def test_happy_path_balanced_two_line(self) -> None:
        entry = post_journal_entry(
            dealership=self.dealership,
            description="Cash sale",
            lines=[
                JournalLineInput(
                    account=self.cash, debit=Decimal("500.00")
                ),
                JournalLineInput(
                    account=self.revenue, credit=Decimal("500.00")
                ),
            ],
        )
        self.assertEqual(entry.lines.count(), 2)
        self.assertEqual(entry.description, "Cash sale")
        self.assertIsNotNone(entry.posted_at)

    def test_empty_lines_rejected(self) -> None:
        with self.assertRaises(EmptyJournalEntryError):
            post_journal_entry(
                dealership=self.dealership,
                description="Bad",
                lines=[],
            )

    def test_unbalanced_rejected(self) -> None:
        with self.assertRaises(UnbalancedJournalEntryError):
            post_journal_entry(
                dealership=self.dealership,
                description="Bad",
                lines=[
                    JournalLineInput(
                        account=self.cash, debit=Decimal("500.00")
                    ),
                    JournalLineInput(
                        account=self.revenue, credit=Decimal("400.00")
                    ),
                ],
            )

    def test_both_debit_and_credit_on_one_line_rejected(self) -> None:
        with self.assertRaises(InvalidJournalLineError):
            post_journal_entry(
                dealership=self.dealership,
                description="Bad",
                lines=[
                    JournalLineInput(
                        account=self.cash,
                        debit=Decimal("100.00"),
                        credit=Decimal("100.00"),
                    ),
                    JournalLineInput(
                        account=self.revenue, credit=Decimal("100.00")
                    ),
                ],
            )

    def test_both_zero_line_rejected(self) -> None:
        with self.assertRaises(InvalidJournalLineError):
            post_journal_entry(
                dealership=self.dealership,
                description="Bad",
                lines=[
                    JournalLineInput(account=self.cash),
                    JournalLineInput(
                        account=self.revenue, credit=Decimal("50.00")
                    ),
                ],
            )

    def test_negative_amount_rejected(self) -> None:
        with self.assertRaises(InvalidJournalLineError):
            post_journal_entry(
                dealership=self.dealership,
                description="Bad",
                lines=[
                    JournalLineInput(
                        account=self.cash, debit=Decimal("-1.00")
                    ),
                    JournalLineInput(
                        account=self.revenue, credit=Decimal("-1.00")
                    ),
                ],
            )

    def test_cross_tenant_account_rejected(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-svc-a", name="Other"
        )
        other_account = _acct(other, "S13-999000")
        with self.assertRaises(CrossTenantGLAccountError):
            post_journal_entry(
                dealership=self.dealership,
                description="Cross-tenant",
                lines=[
                    JournalLineInput(
                        account=other_account, debit=Decimal("10.00")
                    ),
                    JournalLineInput(
                        account=self.revenue, credit=Decimal("10.00")
                    ),
                ],
            )

    def test_multi_line_balanced(self) -> None:
        expense = _acct(
            self.dealership, "S13-500000", GL_ACCOUNT_TYPE_EXPENSE
        )
        entry = post_journal_entry(
            dealership=self.dealership,
            description="Vehicle cost accrual",
            lines=[
                JournalLineInput(
                    account=expense, debit=Decimal("200.00")
                ),
                JournalLineInput(
                    account=expense, debit=Decimal("100.00")
                ),
                JournalLineInput(
                    account=self.cash, credit=Decimal("300.00")
                ),
            ],
        )
        self.assertEqual(entry.lines.count(), 3)

    def test_explicit_posted_at_preserved(self) -> None:
        effective = timezone.now() - dt.timedelta(days=3)
        entry = post_journal_entry(
            dealership=self.dealership,
            description="Back-dated",
            posted_at=effective,
            lines=[
                JournalLineInput(
                    account=self.cash, debit=Decimal("10.00")
                ),
                JournalLineInput(
                    account=self.revenue, credit=Decimal("10.00")
                ),
            ],
        )
        self.assertEqual(entry.posted_at, effective)


class ReverseJournalEntryTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.cash = _acct(self.dealership, "S13-100001")
        self.revenue = _acct(
            self.dealership, "S13-400001", GL_ACCOUNT_TYPE_REVENUE
        )
        self.original = post_journal_entry(
            dealership=self.dealership,
            description="Original posting",
            lines=[
                JournalLineInput(
                    account=self.cash, debit=Decimal("250.00")
                ),
                JournalLineInput(
                    account=self.revenue, credit=Decimal("250.00")
                ),
            ],
        )

    def test_happy_path_reversal_swaps_debits_credits(self) -> None:
        reversal = reverse_journal_entry(
            dealership=self.dealership,
            entry=self.original,
            reason="Duplicate posting",
        )
        self.assertEqual(reversal.reverses_id, self.original.pk)
        self.assertEqual(reversal.reason, "Duplicate posting")
        # Lines swapped: what was a debit is now a credit and vice versa.
        cash_line = reversal.lines.get(account=self.cash)
        revenue_line = reversal.lines.get(account=self.revenue)
        self.assertEqual(cash_line.credit, Decimal("250.00"))
        self.assertEqual(cash_line.debit, Decimal("0.00"))
        self.assertEqual(revenue_line.debit, Decimal("250.00"))
        self.assertEqual(revenue_line.credit, Decimal("0.00"))

    def test_reversal_leaves_original_intact(self) -> None:
        reverse_journal_entry(
            dealership=self.dealership,
            entry=self.original,
            reason="fix",
        )
        self.original.refresh_from_db()
        cash_line = self.original.lines.get(account=self.cash)
        self.assertEqual(cash_line.debit, Decimal("250.00"))
        self.assertEqual(cash_line.credit, Decimal("0.00"))

    def test_empty_reason_rejected(self) -> None:
        with self.assertRaises(ImmutableJournalEntryError):
            reverse_journal_entry(
                dealership=self.dealership,
                entry=self.original,
                reason="   ",
            )

    def test_cross_tenant_target_rejected(self) -> None:
        other = Dealership.objects.create(
            slug="other-dealer-svc-b", name="Other"
        )
        with self.assertRaises(CrossTenantJournalEntryError):
            reverse_journal_entry(
                dealership=other,
                entry=self.original,
                reason="fix",
            )

    def test_reversal_of_reversal_allowed(self) -> None:
        first_reversal = reverse_journal_entry(
            dealership=self.dealership,
            entry=self.original,
            reason="Undo A",
        )
        second_reversal = reverse_journal_entry(
            dealership=self.dealership,
            entry=first_reversal,
            reason="Undo B (re-restore original)",
        )
        self.assertEqual(second_reversal.reverses_id, first_reversal.pk)
        # Line signs match the original after the double reversal.
        cash_line = second_reversal.lines.get(account=self.cash)
        self.assertEqual(cash_line.debit, Decimal("250.00"))


class GetJournalEntryTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.other = Dealership.objects.create(
            slug="other-dealer-svc-c", name="Other"
        )
        cash = _acct(self.dealership, "S13-100002")
        revenue = _acct(
            self.dealership, "S13-400002", GL_ACCOUNT_TYPE_REVENUE
        )
        self.entry = post_journal_entry(
            dealership=self.dealership,
            description="Retrievable",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("1.00")),
                JournalLineInput(account=revenue, credit=Decimal("1.00")),
            ],
        )

    def test_happy_read(self) -> None:
        got = get_journal_entry(pk=self.entry.pk, dealership=self.dealership)
        self.assertIsNotNone(got)
        self.assertEqual(got.pk, self.entry.pk)  # type: ignore[union-attr]

    def test_missing_pk_returns_none(self) -> None:
        got = get_journal_entry(pk=999_999, dealership=self.dealership)
        self.assertIsNone(got)

    def test_cross_tenant_returns_none(self) -> None:
        got = get_journal_entry(pk=self.entry.pk, dealership=self.other)
        self.assertIsNone(got)


class SeedDefaultCoaTests(TestCase):
    def test_migration_seeded_default_dealership(self) -> None:
        # Migration 0043 seeds the default dealership at apply time.
        dealership = get_default_dealership()
        codes = set(
            GLAccount.objects.filter(dealership=dealership).values_list(
                "code", flat=True
            )
        )
        expected = {code for code, _, _ in DEFAULT_COA}
        # >= (not ==) per M9/M10/M11/M12 lesson-14 posture (growth-only
        # sets — future increments may add more accounts).
        self.assertGreaterEqual(codes, expected)

    def test_seed_default_coa_new_dealership(self) -> None:
        new = Dealership.objects.create(
            slug="brand-new-dealership", name="Brand New"
        )
        created = seed_default_coa(new)
        self.assertEqual(created, len(DEFAULT_COA))
        self.assertEqual(
            GLAccount.objects.filter(dealership=new).count(),
            len(DEFAULT_COA),
        )

    def test_seed_default_coa_idempotent(self) -> None:
        new = Dealership.objects.create(
            slug="idempotent-dealership", name="Idempotent"
        )
        first = seed_default_coa(new)
        second = seed_default_coa(new)
        self.assertEqual(first, len(DEFAULT_COA))
        self.assertEqual(second, 0)
        # Row count unchanged after second call.
        self.assertEqual(
            GLAccount.objects.filter(dealership=new).count(),
            len(DEFAULT_COA),
        )
