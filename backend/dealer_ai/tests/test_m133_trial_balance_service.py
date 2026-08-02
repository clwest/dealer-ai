"""Milestone 13 · Increment 3 (SESSION_131) — trial-balance snapshot service tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EQUITY,
    GL_ACCOUNT_TYPE_EXPENSE,
    GL_ACCOUNT_TYPE_LIABILITY,
    GL_ACCOUNT_TYPE_REVENUE,
    Dealership,
    GLAccount,
)
from dealer_ai.services.accounting import (
    JournalLineInput,
    TrialBalanceComputation,
    compute_trial_balance,
    post_journal_entry,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership


def _acct(dealership: Dealership, code: str, name: str, atype: str) -> GLAccount:
    return GLAccount.objects.create(
        dealership=dealership,
        code=code,
        name=name,
        account_type=atype,
    )


class ComputeTrialBalanceTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()

    def test_empty_portfolio_returns_balanced_snapshot(self) -> None:
        # Fresh dealership post-M13.1 seed has 24 GLAccounts but no
        # postings. Per §0.a M13.3 decision 5 — empty balanced
        # snapshot, not 404.
        fresh = Dealership.objects.create(slug="tb-fresh", name="Fresh")
        seed_default_coa(fresh)
        snap = compute_trial_balance(dealership=fresh)
        self.assertIsInstance(snap, TrialBalanceComputation)
        self.assertEqual(snap.rows, ())
        self.assertEqual(snap.total_debits, Decimal("0.00"))
        self.assertEqual(snap.total_credits, Decimal("0.00"))
        self.assertTrue(snap.is_balanced)
        self.assertEqual(snap.dealership_id, fresh.pk)
        self.assertEqual(snap.dealership_slug, "tb-fresh")

    def test_dealership_with_no_seed_still_returns_balanced(self) -> None:
        # Even before COA is seeded — the aggregator only looks at
        # JournalEntryLine rows, so no seed means no lines means an
        # empty balanced snapshot.
        naked = Dealership.objects.create(slug="tb-naked", name="Naked")
        snap = compute_trial_balance(dealership=naked)
        self.assertEqual(snap.rows, ())
        self.assertTrue(snap.is_balanced)

    def test_single_two_line_posting_produces_two_rows(self) -> None:
        cash = _acct(
            self.dealership, "S133-100000", "Cash", GL_ACCOUNT_TYPE_ASSET
        )
        rev = _acct(
            self.dealership,
            "S133-400000",
            "Revenue",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        post_journal_entry(
            dealership=self.dealership,
            description="Cash sale",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("500.00")),
                JournalLineInput(account=rev, credit=Decimal("500.00")),
            ],
        )
        snap = compute_trial_balance(dealership=self.dealership)
        codes = [r.account_code for r in snap.rows]
        self.assertIn("S133-100000", codes)
        self.assertIn("S133-400000", codes)
        self.assertEqual(snap.total_debits, Decimal("500.00"))
        self.assertEqual(snap.total_credits, Decimal("500.00"))
        self.assertTrue(snap.is_balanced)

    def test_natural_balance_signs_by_account_type(self) -> None:
        cash = _acct(
            self.dealership, "S133-100001", "Cash A", GL_ACCOUNT_TYPE_ASSET
        )
        ap = _acct(
            self.dealership,
            "S133-200001",
            "A/P",
            GL_ACCOUNT_TYPE_LIABILITY,
        )
        post_journal_entry(
            dealership=self.dealership,
            description="Test posting",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("300.00")),
                JournalLineInput(account=ap, credit=Decimal("300.00")),
            ],
        )
        snap = compute_trial_balance(dealership=self.dealership)
        by_code = {r.account_code: r for r in snap.rows}
        # Asset (debit-normal): natural = debit - credit = 300 - 0 = 300
        self.assertEqual(by_code["S133-100001"].natural_balance, Decimal("300.00"))
        # Liability (credit-normal): natural = credit - debit = 300 - 0 = 300
        self.assertEqual(by_code["S133-200001"].natural_balance, Decimal("300.00"))

    def test_credit_normal_types_use_credit_minus_debit(self) -> None:
        equity = _acct(
            self.dealership,
            "S133-300000",
            "Equity",
            GL_ACCOUNT_TYPE_EQUITY,
        )
        rev = _acct(
            self.dealership,
            "S133-400001",
            "Revenue B",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        exp = _acct(
            self.dealership,
            "S133-500000",
            "Expense",
            GL_ACCOUNT_TYPE_EXPENSE,
        )
        cash = _acct(
            self.dealership,
            "S133-100002",
            "Cash B",
            GL_ACCOUNT_TYPE_ASSET,
        )
        # Balanced entry touching all four normal-balance combos.
        post_journal_entry(
            dealership=self.dealership,
            description="Multi-type posting",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("100.00")),
                JournalLineInput(account=exp, debit=Decimal("50.00")),
                JournalLineInput(account=rev, credit=Decimal("100.00")),
                JournalLineInput(account=equity, credit=Decimal("50.00")),
            ],
        )
        snap = compute_trial_balance(dealership=self.dealership)
        by_code = {r.account_code: r for r in snap.rows}
        self.assertEqual(by_code["S133-100002"].natural_balance, Decimal("100.00"))
        self.assertEqual(by_code["S133-500000"].natural_balance, Decimal("50.00"))
        self.assertEqual(by_code["S133-400001"].natural_balance, Decimal("100.00"))
        self.assertEqual(by_code["S133-300000"].natural_balance, Decimal("50.00"))

    def test_multi_line_aggregation_sums_per_account(self) -> None:
        recon = _acct(
            self.dealership,
            "S133-122000",
            "Recon",
            GL_ACCOUNT_TYPE_ASSET,
        )
        ap = _acct(
            self.dealership,
            "S133-200002",
            "A/P B",
            GL_ACCOUNT_TYPE_LIABILITY,
        )
        # Three separate postings against the same account pair.
        for amount in (Decimal("100.00"), Decimal("50.00"), Decimal("25.00")):
            post_journal_entry(
                dealership=self.dealership,
                description=f"Post {amount}",
                lines=[
                    JournalLineInput(account=recon, debit=amount),
                    JournalLineInput(account=ap, credit=amount),
                ],
            )
        snap = compute_trial_balance(dealership=self.dealership)
        by_code = {r.account_code: r for r in snap.rows}
        self.assertEqual(by_code["S133-122000"].debit_total, Decimal("175.00"))
        self.assertEqual(by_code["S133-200002"].credit_total, Decimal("175.00"))
        self.assertEqual(snap.total_debits, Decimal("175.00"))
        self.assertEqual(snap.total_credits, Decimal("175.00"))

    def test_as_of_filter_excludes_future_postings(self) -> None:
        cash = _acct(
            self.dealership,
            "S133-100003",
            "Cash C",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "S133-400002",
            "Revenue C",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        now = timezone.now()
        past = now - dt.timedelta(days=5)
        future = now + dt.timedelta(days=5)
        post_journal_entry(
            dealership=self.dealership,
            description="Past",
            posted_at=past,
            lines=[
                JournalLineInput(account=cash, debit=Decimal("10.00")),
                JournalLineInput(account=rev, credit=Decimal("10.00")),
            ],
        )
        post_journal_entry(
            dealership=self.dealership,
            description="Future",
            posted_at=future,
            lines=[
                JournalLineInput(account=cash, debit=Decimal("99.00")),
                JournalLineInput(account=rev, credit=Decimal("99.00")),
            ],
        )
        snap = compute_trial_balance(dealership=self.dealership, as_of=now)
        by_code = {r.account_code: r for r in snap.rows}
        # Only the past posting should be reflected.
        self.assertEqual(by_code["S133-100003"].debit_total, Decimal("10.00"))
        self.assertEqual(snap.as_of, now)

    def test_scoped_to_dealership(self) -> None:
        other = Dealership.objects.create(slug="tb-other", name="Other")
        seed_default_coa(other)
        our_cash = _acct(
            self.dealership,
            "S133-100004",
            "Ours",
            GL_ACCOUNT_TYPE_ASSET,
        )
        our_rev = _acct(
            self.dealership,
            "S133-400003",
            "Ours Rev",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        their_cash = _acct(other, "S133-100004", "Theirs", GL_ACCOUNT_TYPE_ASSET)
        their_rev = _acct(other, "S133-400003", "Theirs Rev", GL_ACCOUNT_TYPE_REVENUE)
        post_journal_entry(
            dealership=self.dealership,
            description="Our post",
            lines=[
                JournalLineInput(account=our_cash, debit=Decimal("10.00")),
                JournalLineInput(account=our_rev, credit=Decimal("10.00")),
            ],
        )
        post_journal_entry(
            dealership=other,
            description="Their post",
            lines=[
                JournalLineInput(account=their_cash, debit=Decimal("999.00")),
                JournalLineInput(account=their_rev, credit=Decimal("999.00")),
            ],
        )
        our_snap = compute_trial_balance(dealership=self.dealership)
        their_snap = compute_trial_balance(dealership=other)
        self.assertEqual(our_snap.total_debits, Decimal("10.00"))
        self.assertEqual(their_snap.total_debits, Decimal("999.00"))
        # Our snapshot must not include the other tenant's rows.
        our_codes = [(r.account_code, r.account_name) for r in our_snap.rows]
        self.assertIn(("S133-100004", "Ours"), our_codes)
        self.assertNotIn(("S133-100004", "Theirs"), our_codes)

    def test_rows_ordered_by_code_ascending(self) -> None:
        # Insert accounts in reverse code order — the snapshot should
        # still return them sorted ascending.
        codes = ["S133-Z", "S133-M", "S133-A"]
        for i, code in enumerate(codes):
            acct = _acct(
                self.dealership,
                code,
                f"Account {code}",
                GL_ACCOUNT_TYPE_ASSET,
            )
            rev = _acct(
                self.dealership,
                f"{code}-r",
                f"Rev {code}",
                GL_ACCOUNT_TYPE_REVENUE,
            )
            post_journal_entry(
                dealership=self.dealership,
                description=f"P{i}",
                lines=[
                    JournalLineInput(account=acct, debit=Decimal("1.00")),
                    JournalLineInput(account=rev, credit=Decimal("1.00")),
                ],
            )
        snap = compute_trial_balance(dealership=self.dealership)
        our_codes = [r.account_code for r in snap.rows if r.account_code.startswith("S133-") and not r.account_code.endswith("-r")]
        # Only asset rows we inserted, in sorted order.
        self.assertEqual(our_codes, ["S133-A", "S133-M", "S133-Z"])

    def test_reversal_produces_zero_net_balance(self) -> None:
        from dealer_ai.services.accounting import reverse_journal_entry

        cash = _acct(
            self.dealership,
            "S133-100010",
            "Cash R",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "S133-400010",
            "Rev R",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        original = post_journal_entry(
            dealership=self.dealership,
            description="Original",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("200.00")),
                JournalLineInput(account=rev, credit=Decimal("200.00")),
            ],
        )
        reverse_journal_entry(
            dealership=self.dealership,
            entry=original,
            reason="test reversal",
        )
        snap = compute_trial_balance(dealership=self.dealership)
        by_code = {r.account_code: r for r in snap.rows}
        # Post + reverse: 200 debit + 200 credit on cash → natural 0.
        self.assertEqual(by_code["S133-100010"].natural_balance, Decimal("0.00"))
        self.assertEqual(by_code["S133-400010"].natural_balance, Decimal("0.00"))
        # Balance still holds.
        self.assertTrue(snap.is_balanced)

    def test_is_balanced_true_for_all_valid_postings(self) -> None:
        # Every posting through post_journal_entry is balanced by the
        # M13.1 UnbalancedJournalEntryError guard, so the M13.3
        # aggregator always sees is_balanced=True unless there's a
        # data-integrity break. Locking the invariant.
        cash = _acct(
            self.dealership,
            "S133-100020",
            "C",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "S133-400020",
            "R",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        for amount in (Decimal("1.00"), Decimal("2.50"), Decimal("999.99")):
            post_journal_entry(
                dealership=self.dealership,
                description=f"Post {amount}",
                lines=[
                    JournalLineInput(account=cash, debit=amount),
                    JournalLineInput(account=rev, credit=amount),
                ],
            )
        snap = compute_trial_balance(dealership=self.dealership)
        self.assertTrue(snap.is_balanced)

    def test_as_of_defaults_to_now(self) -> None:
        cash = _acct(
            self.dealership,
            "S133-100030",
            "C",
            GL_ACCOUNT_TYPE_ASSET,
        )
        rev = _acct(
            self.dealership,
            "S133-400030",
            "R",
            GL_ACCOUNT_TYPE_REVENUE,
        )
        post_journal_entry(
            dealership=self.dealership,
            description="Now",
            lines=[
                JournalLineInput(account=cash, debit=Decimal("5.00")),
                JournalLineInput(account=rev, credit=Decimal("5.00")),
            ],
        )
        before = timezone.now()
        snap = compute_trial_balance(dealership=self.dealership)
        after = timezone.now()
        self.assertLessEqual(before, snap.as_of)
        self.assertGreaterEqual(after, snap.as_of)
