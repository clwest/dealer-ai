"""Milestone 28 · Increment 1 (SESSION_195) — template service verb tests.

Behaviors asserted:

- `create_journal_entry_template` happy path posts template + lines
  atomically with expected ordering and amounts.
- Refuses fewer than 2 lines (EmptyJournalEntryTemplateError → 400).
- Refuses lines with null / non-positive amount, bad ``side`` value
  (InvalidJournalEntryTemplateLineError → 400).
- Refuses cross-tenant GLAccount (CrossTenantGLAccountError → 404).
- Refuses unbalanced debit-side vs credit-side totals
  (UnbalancedJournalEntryTemplateError → 400).
- Refuses duplicate name within tenant
  (DuplicateJournalEntryTemplateNameError → 409).
- `list_journal_entry_templates` returns only active templates ordered
  by name; `include_inactive=True` opt-in surfaces inactive too.
- `get_journal_entry_template` returns None for cross-tenant or
  missing pk (fail-closed).
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
    DuplicateJournalEntryTemplateNameError,
    EmptyJournalEntryTemplateError,
    InvalidJournalEntryTemplateLineError,
    TemplateLineInput,
    UnbalancedJournalEntryTemplateError,
    create_journal_entry_template,
    get_journal_entry_template,
    list_journal_entry_templates,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    rent = GLAccount.objects.create(
        dealership=dealership,
        code="ST-615000",
        name="Rent Expense",
        account_type=GL_ACCOUNT_TYPE_EXPENSE,
    )
    bank = GLAccount.objects.create(
        dealership=dealership,
        code="ST-110000",
        name="Bank — Operating",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    return rent, bank


class CreateJournalEntryTemplateTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)

    def _valid_lines(self) -> list[TemplateLineInput]:
        return [
            TemplateLineInput(
                account=self.rent,
                side="debit",
                amount=Decimal("3500.00"),
                memo="",
                ordering=0,
            ),
            TemplateLineInput(
                account=self.bank,
                side="credit",
                amount=Decimal("3500.00"),
                memo="",
                ordering=1,
            ),
        ]

    def test_happy_path_creates_template_and_lines(self) -> None:
        template = create_journal_entry_template(
            dealership=self.dealership,
            name="Monthly rent",
            description="Rent expense — monthly",
            lines=self._valid_lines(),
        )
        self.assertIsInstance(template, JournalEntryTemplate)
        self.assertEqual(template.name, "Monthly rent")
        self.assertEqual(template.lines.count(), 2)
        lines = list(template.lines.all())
        self.assertEqual(lines[0].side, "debit")
        self.assertEqual(lines[0].amount, Decimal("3500.00"))
        self.assertEqual(lines[1].side, "credit")
        self.assertEqual(lines[1].amount, Decimal("3500.00"))

    def test_refuses_empty_lines(self) -> None:
        with self.assertRaises(EmptyJournalEntryTemplateError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Empty",
                description="—",
                lines=[],
            )

    def test_refuses_single_line(self) -> None:
        with self.assertRaises(EmptyJournalEntryTemplateError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Single line",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("100.00"),
                    )
                ],
            )

    def test_refuses_null_amount_at_m28(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Null amount",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=None,
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("100.00"),
                    ),
                ],
            )

    def test_refuses_zero_amount(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Zero",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("0.00"),
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("0.00"),
                    ),
                ],
            )

    def test_refuses_negative_amount(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Negative",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("-10.00"),
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("100.00"),
                    ),
                ],
            )

    def test_refuses_bad_side(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Bad side",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="left",  # not "debit" or "credit"
                        amount=Decimal("100.00"),
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("100.00"),
                    ),
                ],
            )

    def test_refuses_unbalanced(self) -> None:
        with self.assertRaises(UnbalancedJournalEntryTemplateError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Unbalanced",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("100.00"),
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("50.00"),
                    ),
                ],
            )

    def test_refuses_cross_tenant_account(self) -> None:
        other = Dealership.objects.create(
            slug="other-svc", name="Other tenant"
        )
        other_account = GLAccount.objects.create(
            dealership=other,
            code="OTH-999",
            name="Foreign",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        with self.assertRaises(CrossTenantGLAccountError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Cross-tenant",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=other_account,
                        side="debit",
                        amount=Decimal("100.00"),
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("100.00"),
                    ),
                ],
            )

    def test_refuses_duplicate_name(self) -> None:
        create_journal_entry_template(
            dealership=self.dealership,
            name="Rent",
            description="—",
            lines=self._valid_lines(),
        )
        with self.assertRaises(DuplicateJournalEntryTemplateNameError):
            create_journal_entry_template(
                dealership=self.dealership,
                name="Rent",
                description="Another rent",
                lines=self._valid_lines(),
            )


class ListJournalEntryTemplatesTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)

    def _seed(self, name: str, is_active: bool = True) -> JournalEntryTemplate:
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name=name,
            description="—",
            is_active=is_active,
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("10.00"),
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.bank,
            side="credit",
            amount=Decimal("10.00"),
        )
        return template

    def test_returns_active_only_by_default(self) -> None:
        self._seed("Alpha")
        self._seed("Beta", is_active=False)
        self._seed("Gamma")
        names = list(
            list_journal_entry_templates(
                dealership=self.dealership
            ).values_list("name", flat=True)
        )
        self.assertEqual(names, ["Alpha", "Gamma"])

    def test_include_inactive_opt_in(self) -> None:
        self._seed("Alpha")
        self._seed("Beta", is_active=False)
        names = list(
            list_journal_entry_templates(
                dealership=self.dealership, include_inactive=True
            ).values_list("name", flat=True)
        )
        self.assertEqual(names, ["Alpha", "Beta"])

    def test_empty_tenant_returns_empty_queryset(self) -> None:
        empty = Dealership.objects.create(
            slug="empty-svc", name="Empty tenant"
        )
        self.assertEqual(
            list_journal_entry_templates(dealership=empty).count(), 0
        )

    def test_scoped_to_tenant(self) -> None:
        self._seed("Alpha")
        other = Dealership.objects.create(
            slug="other-scope-svc", name="Other tenant"
        )
        JournalEntryTemplate.objects.create(
            dealership=other,
            name="Other's template",
            description="—",
        )
        names = list(
            list_journal_entry_templates(
                dealership=self.dealership
            ).values_list("name", flat=True)
        )
        self.assertEqual(names, ["Alpha"])


class GetJournalEntryTemplateTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.template = JournalEntryTemplate.objects.create(
            dealership=self.dealership, name="X", description="—"
        )

    def test_found_returns_template(self) -> None:
        found = get_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.assertEqual(found, self.template)

    def test_missing_pk_returns_none(self) -> None:
        self.assertIsNone(
            get_journal_entry_template(
                pk=999_999, dealership=self.dealership
            )
        )

    def test_cross_tenant_returns_none(self) -> None:
        other = Dealership.objects.create(
            slug="other-get-svc", name="Other tenant"
        )
        self.assertIsNone(
            get_journal_entry_template(
                pk=self.template.pk, dealership=other
            )
        )
