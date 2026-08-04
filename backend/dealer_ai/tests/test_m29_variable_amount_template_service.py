"""Milestone 29 · Increment 1 (SESSION_198) — variable-amount template tests.

Behaviors asserted (per MILESTONE_29_PLANNING.md §5.b D1):

- ``amount = None`` is accepted at create time as a *variable* line
  (side + GL account fixed, amount deferred to instantiation).
- Fully-variable templates (every line has ``amount = None``) balance
  trivially — both populated sums are zero.
- Mixed templates (some lines populated, some null) balance only if
  the populated (non-null) portion has debit-side sum == credit-side
  sum.
- Zero and negative populated amounts remain rejected as
  ``InvalidJournalEntryTemplateLineError``.
- ``side`` and cross-tenant guards still apply to variable lines.
- Ordering + memo + persistence semantics unchanged for variable
  lines (the model column is nullable per M28.1 migration 0050).

This file complements ``test_m28_journal_entry_template_service.py``
which continues to assert the M28.1 behaviors that M29 preserves
(fully-populated happy path, cross-tenant reject, unbalanced-populated
reject, duplicate name reject, etc.).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EXPENSE,
    Dealership,
    GLAccount,
    JournalEntryTemplate,
    JournalEntryTemplateLine,
)
from dealer_ai.services.accounting import (
    CrossTenantGLAccountError,
    InvalidJournalEntryTemplateLineError,
    TemplateLineInput,
    UnbalancedJournalEntryTemplateError,
    create_journal_entry_template,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    expense = GLAccount.objects.create(
        dealership=dealership,
        code="M29-671000",
        name="Depreciation Expense",
        account_type=GL_ACCOUNT_TYPE_EXPENSE,
    )
    contra_asset = GLAccount.objects.create(
        dealership=dealership,
        code="M29-160000",
        name="Accumulated Depreciation",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    return expense, contra_asset


class VariableAmountTemplateCreateTests(TestCase):
    """Cover the M29.1 three-state balance logic at create time."""

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.expense, self.contra_asset = _make_accounts(self.dealership)

    def test_fully_variable_template_accepted(self) -> None:
        """Both lines null — the depreciation base case."""
        template = create_journal_entry_template(
            dealership=self.dealership,
            name="Monthly depreciation",
            description="Depreciation expense per asset per period",
            lines=[
                TemplateLineInput(
                    account=self.expense, side="debit", amount=None
                ),
                TemplateLineInput(
                    account=self.contra_asset, side="credit", amount=None
                ),
            ],
        )
        self.assertIsInstance(template, JournalEntryTemplate)
        lines = list(template.lines.all())
        self.assertEqual(len(lines), 2)
        self.assertIsNone(lines[0].amount)
        self.assertIsNone(lines[1].amount)
        self.assertEqual(lines[0].side, "debit")
        self.assertEqual(lines[1].side, "credit")

    def test_null_amount_line_stores_none_not_zero(self) -> None:
        """Guard against the service coercing ``None`` to ``Decimal(0)``."""
        template = create_journal_entry_template(
            dealership=self.dealership,
            name="Null preservation",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.expense, side="debit", amount=None
                ),
                TemplateLineInput(
                    account=self.contra_asset, side="credit", amount=None
                ),
            ],
        )
        for line in template.lines.all():
            fresh = JournalEntryTemplateLine.objects.get(pk=line.pk)
            self.assertIsNone(fresh.amount)

    def test_mixed_template_with_balanced_populated_portion_accepted(
        self,
    ) -> None:
        """Fixed pair on one axis, variable pair on another — utilities
        template shape (fixed base fee + variable usage)."""
        base_fee_debit = GLAccount.objects.create(
            dealership=self.dealership,
            code="M29-UT-671001",
            name="Utilities Base Fee",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        base_fee_credit = GLAccount.objects.create(
            dealership=self.dealership,
            code="M29-UT-110001",
            name="Utilities Bank",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        template = create_journal_entry_template(
            dealership=self.dealership,
            name="Utilities monthly",
            description="Base fee fixed; usage varies",
            lines=[
                TemplateLineInput(
                    account=self.expense,
                    side="debit",
                    amount=Decimal("25.00"),
                ),
                TemplateLineInput(
                    account=self.contra_asset,
                    side="credit",
                    amount=Decimal("25.00"),
                ),
                TemplateLineInput(
                    account=base_fee_debit, side="debit", amount=None
                ),
                TemplateLineInput(
                    account=base_fee_credit, side="credit", amount=None
                ),
            ],
        )
        lines = list(template.lines.all())
        self.assertEqual(len(lines), 4)
        amounts = [line.amount for line in lines]
        self.assertIn(Decimal("25.00"), amounts)
        self.assertIn(None, amounts)

    def test_mixed_template_with_imbalanced_populated_rejected(
        self,
    ) -> None:
        """One-sided fixed amount without matching populated other-side
        is caught at create time, per §5.b D1 rationale."""
        with self.assertRaises(UnbalancedJournalEntryTemplateError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="One-sided fixed",
                description="Debit populated, credit null — unbalanced",
                lines=[
                    TemplateLineInput(
                        account=self.expense,
                        side="debit",
                        amount=Decimal("500.00"),
                    ),
                    TemplateLineInput(
                        account=self.contra_asset,
                        side="credit",
                        amount=None,
                    ),
                ],
            )

    def test_variable_line_still_rejects_zero_amount(self) -> None:
        """Zero on the populated side is invalid whether or not the
        other line is variable."""
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Zero populated",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.expense,
                        side="debit",
                        amount=Decimal("0.00"),
                    ),
                    TemplateLineInput(
                        account=self.contra_asset,
                        side="credit",
                        amount=None,
                    ),
                ],
            )

    def test_variable_line_still_rejects_negative_amount(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Negative populated",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.expense,
                        side="debit",
                        amount=Decimal("-500.00"),
                    ),
                    TemplateLineInput(
                        account=self.contra_asset,
                        side="credit",
                        amount=None,
                    ),
                ],
            )

    def test_variable_line_still_rejects_bad_side(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Bad side variable",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.expense, side="middle", amount=None
                    ),
                    TemplateLineInput(
                        account=self.contra_asset,
                        side="credit",
                        amount=None,
                    ),
                ],
            )

    def test_variable_line_still_rejects_cross_tenant_account(self) -> None:
        other = Dealership.objects.create(
            slug="other-tenant-m29",
            name="Other Dealer",
        )
        cross = GLAccount.objects.create(
            dealership=other,
            code="M29-CROSS-671000",
            name="Cross Depreciation",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        with self.assertRaises(CrossTenantGLAccountError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Cross variable",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=cross, side="debit", amount=None
                    ),
                    TemplateLineInput(
                        account=self.contra_asset,
                        side="credit",
                        amount=None,
                    ),
                ],
            )

    def test_variable_line_preserves_side_and_ordering(self) -> None:
        template = create_journal_entry_template(
            dealership=self.dealership,
            name="Ordering variable",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.expense,
                    side="debit",
                    amount=None,
                    ordering=7,
                    memo="Enter monthly amount",
                ),
                TemplateLineInput(
                    account=self.contra_asset,
                    side="credit",
                    amount=None,
                    ordering=42,
                    memo="Enter monthly amount",
                ),
            ],
        )
        lines = list(template.lines.all())
        self.assertEqual([line.side for line in lines], ["debit", "credit"])
        self.assertEqual(lines[0].memo, "Enter monthly amount")
        self.assertEqual(lines[1].memo, "Enter monthly amount")

    def test_populated_balance_still_enforced_at_zero_amount(self) -> None:
        """Mixed-with-imbalanced-populated remains an
        UnbalancedJournalEntryTemplateError even when the imbalance is
        small (e.g., $0.01 rounding-difference between two fixed lines
        plus a variable third line)."""
        third = GLAccount.objects.create(
            dealership=self.dealership,
            code="M29-VAR-500000",
            name="Additional Expense",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        with self.assertRaises(UnbalancedJournalEntryTemplateError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Rounding imbalance",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.expense,
                        side="debit",
                        amount=Decimal("100.00"),
                    ),
                    TemplateLineInput(
                        account=self.contra_asset,
                        side="credit",
                        amount=Decimal("100.01"),
                    ),
                    TemplateLineInput(
                        account=third, side="debit", amount=None
                    ),
                ],
            )

    def test_fully_populated_still_accepted_regression_guard(self) -> None:
        """Explicit regression guard — M28.1 happy path unchanged
        after the M29.1 three-state relaxation."""
        template = create_journal_entry_template(
            dealership=self.dealership,
            name="Fully fixed regression",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.expense,
                    side="debit",
                    amount=Decimal("1000.00"),
                ),
                TemplateLineInput(
                    account=self.contra_asset,
                    side="credit",
                    amount=Decimal("1000.00"),
                ),
            ],
        )
        lines = list(template.lines.all())
        self.assertEqual(lines[0].amount, Decimal("1000.00"))
        self.assertEqual(lines[1].amount, Decimal("1000.00"))
