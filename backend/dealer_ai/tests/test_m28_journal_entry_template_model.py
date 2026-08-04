"""Milestone 28 · Increment 1 (SESSION_195) — template model tests.

Behaviors asserted:

- Positive: JournalEntryTemplate + JournalEntryTemplateLine round-trip
  cleanly with expected ordering + defaults.
- Amount NULL posture: nullable ``amount`` is queryable and preserved
  (schema-reserved for future variable-amount templates).
- Name uniqueness per tenant: `(dealership, name)` unique constraint
  enforced at the DB layer.
- Cross-tenant guard on template line ``clean()``: rejects lines whose
  ``account`` or ``template`` belong to a different tenant. Per M28.0
  §5.b evidence-first duplication decision, this guard is duplicated
  inline (not extracted); the tests verify local ownership works.
- Cascade posture: deleting a template removes its lines. A GLAccount
  with attached template lines is PROTECTed from deletion.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EXPENSE,
    Dealership,
    GLAccount,
    JournalEntryTemplate,
    JournalEntryTemplateLine,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    rent = GLAccount.objects.create(
        dealership=dealership,
        code="MT-615000",
        name="Rent Expense",
        account_type=GL_ACCOUNT_TYPE_EXPENSE,
    )
    bank = GLAccount.objects.create(
        dealership=dealership,
        code="MT-110000",
        name="Bank — Operating",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    return rent, bank


class JournalEntryTemplateModelTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)

    def test_template_and_lines_roundtrip(self) -> None:
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Monthly rent",
            description="Rent expense — monthly",
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("3500.00"),
            memo="",
            ordering=0,
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.bank,
            side="credit",
            amount=Decimal("3500.00"),
            memo="",
            ordering=1,
        )
        reloaded = JournalEntryTemplate.objects.get(pk=template.pk)
        lines = list(reloaded.lines.all())
        self.assertEqual(len(lines), 2)
        self.assertEqual([line.side for line in lines], ["debit", "credit"])
        self.assertEqual(
            [line.amount for line in lines],
            [Decimal("3500.00"), Decimal("3500.00")],
        )
        self.assertTrue(reloaded.is_active)

    def test_amount_null_posture_preserved(self) -> None:
        """M28 does not USE nullable amount, but the schema reserves it.

        Verifying it round-trips cleanly is the guardrail against a
        future migration accidentally tightening the column.
        """
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Variable amount recipe",
            description="Future variable-amount template",
        )
        line = JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=None,
            memo="Amount entered at instantiation",
        )
        self.assertIsNone(
            JournalEntryTemplateLine.objects.get(pk=line.pk).amount
        )

    def test_name_uniqueness_per_dealership(self) -> None:
        JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Monthly rent",
            description="Rent",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                JournalEntryTemplate.objects.create(
                    dealership=self.dealership,
                    name="Monthly rent",
                    description="Duplicate name",
                )

    def test_same_name_allowed_across_tenants(self) -> None:
        other = Dealership.objects.create(
            slug="other-tmpl-name", name="Other tenant"
        )
        JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Monthly rent",
            description="Rent",
        )
        # Should succeed — uniqueness is per-tenant, not global.
        JournalEntryTemplate.objects.create(
            dealership=other,
            name="Monthly rent",
            description="Rent (other tenant)",
        )

    def test_line_cross_tenant_account_rejected(self) -> None:
        other = Dealership.objects.create(
            slug="other-tmpl-line-account", name="Other tenant"
        )
        other_account = GLAccount.objects.create(
            dealership=other,
            code="OT-999",
            name="Foreign",
            account_type=GL_ACCOUNT_TYPE_ASSET,
        )
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Cross-tenant test",
            description="—",
        )
        bad_line = JournalEntryTemplateLine(
            template=template,
            dealership=self.dealership,
            account=other_account,
            side="debit",
            amount=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            bad_line.clean()
        self.assertIn("account", ctx.exception.error_dict)

    def test_line_cross_tenant_template_rejected(self) -> None:
        other = Dealership.objects.create(
            slug="other-tmpl-line-parent", name="Other tenant"
        )
        other_template = JournalEntryTemplate.objects.create(
            dealership=other,
            name="Other tenant's template",
            description="—",
        )
        bad_line = JournalEntryTemplateLine(
            template=other_template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            bad_line.clean()
        self.assertIn("template", ctx.exception.error_dict)

    def test_delete_template_cascades_lines(self) -> None:
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Cascade test",
            description="—",
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("50.00"),
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.bank,
            side="credit",
            amount=Decimal("50.00"),
        )
        line_ids = list(
            JournalEntryTemplateLine.objects.filter(
                template=template
            ).values_list("pk", flat=True)
        )
        self.assertEqual(len(line_ids), 2)

        template.delete()
        self.assertFalse(
            JournalEntryTemplateLine.objects.filter(
                pk__in=line_ids
            ).exists()
        )

    def test_account_protected_from_delete_when_line_exists(self) -> None:
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Protect test",
            description="—",
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("10.00"),
        )
        with self.assertRaises(ProtectedError):
            self.rent.delete()

    def test_default_ordering_by_name(self) -> None:
        JournalEntryTemplate.objects.create(
            dealership=self.dealership, name="Zeta", description="—"
        )
        JournalEntryTemplate.objects.create(
            dealership=self.dealership, name="Alpha", description="—"
        )
        JournalEntryTemplate.objects.create(
            dealership=self.dealership, name="Mu", description="—"
        )
        names = list(
            JournalEntryTemplate.objects.filter(
                dealership=self.dealership
            ).values_list("name", flat=True)
        )
        # Meta.ordering = ["name"] — asc.
        self.assertEqual(names, ["Alpha", "Mu", "Zeta"])

    # ------------------------------------------------------------------
    # M29 (SESSION_198) — variable-amount model-layer coverage
    # ------------------------------------------------------------------

    def test_m29_mixed_variable_and_fixed_lines_roundtrip(self) -> None:
        """A template can hold both populated and null lines together;
        each line's amount round-trips through the ORM unchanged."""
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Mixed variable and fixed",
            description="—",
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=Decimal("500.00"),
            ordering=0,
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.bank,
            side="credit",
            amount=None,
            ordering=1,
        )
        lines = list(template.lines.all().order_by("ordering"))
        self.assertEqual(lines[0].amount, Decimal("500.00"))
        self.assertIsNone(lines[1].amount)
        self.assertEqual(lines[0].side, "debit")
        self.assertEqual(lines[1].side, "credit")

    def test_m29_fully_variable_template_two_lines_null_ok(self) -> None:
        """A fully-variable template stores two null-amount lines
        without violating any model constraint."""
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Fully variable depreciation",
            description="—",
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.rent,
            side="debit",
            amount=None,
            ordering=0,
        )
        JournalEntryTemplateLine.objects.create(
            template=template,
            dealership=self.dealership,
            account=self.bank,
            side="credit",
            amount=None,
            ordering=1,
        )
        self.assertEqual(template.lines.count(), 2)
        self.assertEqual(
            template.lines.filter(amount__isnull=True).count(), 2
        )

    # ------------------------------------------------------------------
    # M30 (SESSION_201) — auto-now updated_at guard for edit UI
    # ------------------------------------------------------------------

    def test_m30_updated_at_advances_on_save(self) -> None:
        """The M30.2 edit UI relies on the model's ``updated_at``
        auto-now field advancing when a template row is saved.
        Guardrail against a future migration accidentally
        dropping the ``auto_now`` posture."""
        template = JournalEntryTemplate.objects.create(
            dealership=self.dealership,
            name="Timestamp guardrail",
            description="Original",
        )
        original_updated_at = template.updated_at
        template.description = "Edited"
        template.save(update_fields=["description", "updated_at"])
        template.refresh_from_db()
        self.assertGreater(template.updated_at, original_updated_at)
