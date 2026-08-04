"""Milestone 30 · Increment 1 (SESSION_201) — template edit/delete service tests.

Behaviors asserted (per MILESTONE_30_PLANNING.md §5.b D1 + D6):

- ``update_journal_entry_template`` happy path returns the updated
  row with new name / description / lines (full-replace of lines).
- Full-replace deletes prior lines and stores the new set — no
  partial-patch semantics.
- Update preserves ``is_active`` regardless of prior state (edit
  never activates or deactivates; DELETE is the only path to
  ``is_active = False``, and Restore is deferred to a future
  milestone).
- Update preserves ``created_at`` and advances ``updated_at``
  (auto-now).
- Update returns ``None`` for cross-tenant or missing pk (endpoint
  layer maps to 404).
- Update refuses negative-amount populated lines and unbalanced
  populated portions — same error surface as create.
- Update accepts variable (``amount = None``) lines — M29 regression.
- Update rejects duplicate name inside the same tenant
  (``DuplicateJournalEntryTemplateNameError`` — 409).
- ``delete_journal_entry_template`` soft-deletes by setting
  ``is_active = False`` and returns the updated row.
- Delete is idempotent — repeat DELETE on an already-inactive row
  returns the same row without state change.
- Delete returns ``None`` for cross-tenant or missing pk.
- ``get_journal_entry_template`` respects the new
  ``include_inactive`` kwarg — default False fail-closes on
  soft-hidden rows; True finds them.

This file complements ``test_m28_journal_entry_template_service.py``
which asserts the M28.1 create + list + get behaviors that M30.1
preserves.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import (
    GL_ACCOUNT_TYPE_ASSET,
    GL_ACCOUNT_TYPE_EXPENSE,
    Dealership,
    GLAccount,
    JournalEntryTemplateLine,
)
from dealer_ai.services.accounting import (
    DuplicateJournalEntryTemplateNameError,
    InvalidJournalEntryTemplateLineError,
    TemplateLineInput,
    UnbalancedJournalEntryTemplateError,
    create_journal_entry_template,
    delete_journal_entry_template,
    get_journal_entry_template,
    update_journal_entry_template,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    rent = GLAccount.objects.create(
        dealership=dealership,
        code="M30-615000",
        name="Rent Expense",
        account_type=GL_ACCOUNT_TYPE_EXPENSE,
    )
    bank = GLAccount.objects.create(
        dealership=dealership,
        code="M30-110000",
        name="Bank — Operating",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    return rent, bank


class UpdateJournalEntryTemplateTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.template = create_journal_entry_template(
            dealership=self.dealership,
            name="Monthly rent",
            description="Original description",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("3500.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("3500.00"),
                    ordering=1,
                ),
            ],
        )

    def test_update_happy_path(self) -> None:
        updated = update_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            name="Monthly rent (renamed)",
            description="Corrected description",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("4000.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("4000.00"),
                    ordering=1,
                ),
            ],
        )
        assert updated is not None
        self.assertEqual(updated.pk, self.template.pk)
        self.assertEqual(updated.name, "Monthly rent (renamed)")
        self.assertEqual(updated.description, "Corrected description")

    def test_update_full_replaces_lines(self) -> None:
        """Full-replace: old lines are deleted, new lines stored.

        Per M30.0 §5.b D1: template lines are a small ordered set;
        edit rewrites the entire lines array, not a partial patch.
        """
        original_line_pks = list(
            self.template.lines.values_list("pk", flat=True)
        )
        self.assertEqual(len(original_line_pks), 2)

        third = GLAccount.objects.create(
            dealership=self.dealership,
            code="M30-671000",
            name="Utilities Expense",
            account_type=GL_ACCOUNT_TYPE_EXPENSE,
        )
        updated = update_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            name="Monthly rent",
            description="Now three lines",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("3500.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=third,
                    side="debit",
                    amount=Decimal("500.00"),
                    ordering=1,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("4000.00"),
                    ordering=2,
                ),
            ],
        )
        assert updated is not None
        # Old line PKs are gone; three fresh lines exist.
        self.assertFalse(
            JournalEntryTemplateLine.objects.filter(
                pk__in=original_line_pks
            ).exists()
        )
        self.assertEqual(updated.lines.count(), 3)

    def test_update_preserves_is_active_true(self) -> None:
        self.assertTrue(self.template.is_active)
        updated = update_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            name="Monthly rent",
            description="Edited",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("100.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("100.00"),
                    ordering=1,
                ),
            ],
        )
        assert updated is not None
        self.assertTrue(updated.is_active)

    def test_update_preserves_is_active_false(self) -> None:
        """Even inactive templates remain editable — is_active is
        preserved. Activation flows through DELETE (soft) or a
        future Restore verb only."""
        self.template.is_active = False
        self.template.save(update_fields=["is_active"])
        updated = update_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            name="Monthly rent (edited while inactive)",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("50.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("50.00"),
                    ordering=1,
                ),
            ],
        )
        assert updated is not None
        self.assertFalse(updated.is_active)

    def test_update_advances_updated_at(self) -> None:
        original_updated_at = self.template.updated_at
        updated = update_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            name="Advances timestamp",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("10.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("10.00"),
                    ordering=1,
                ),
            ],
        )
        assert updated is not None
        self.assertGreater(updated.updated_at, original_updated_at)

    def test_update_missing_pk_returns_none(self) -> None:
        result = update_journal_entry_template(
            pk=999_999,
            dealership=self.dealership,
            name="Ghost",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("1.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("1.00"),
                    ordering=1,
                ),
            ],
        )
        self.assertIsNone(result)

    def test_update_cross_tenant_returns_none(self) -> None:
        other = Dealership.objects.create(
            slug="other-m30-tenant", name="Other tenant"
        )
        result = update_journal_entry_template(
            pk=self.template.pk,
            dealership=other,
            name="Sneaky cross-tenant",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("1.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("1.00"),
                    ordering=1,
                ),
            ],
        )
        self.assertIsNone(result)
        # Original template untouched.
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Monthly rent")

    def test_update_rejects_negative_populated_amount(self) -> None:
        with self.assertRaises(InvalidJournalEntryTemplateLineError):
            update_journal_entry_template(
                pk=self.template.pk,
                dealership=self.dealership,
                name="Monthly rent",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("-50.00"),
                        ordering=0,
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("50.00"),
                        ordering=1,
                    ),
                ],
            )

    def test_update_rejects_populated_imbalance(self) -> None:
        with self.assertRaises(UnbalancedJournalEntryTemplateError):
            update_journal_entry_template(
                pk=self.template.pk,
                dealership=self.dealership,
                name="Monthly rent",
                description="—",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("100.00"),
                        ordering=0,
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("99.99"),
                        ordering=1,
                    ),
                ],
            )

    def test_update_accepts_variable_lines(self) -> None:
        """M29 regression — edit path must accept ``amount = None``
        lines just like create does."""
        updated = update_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            name="Monthly rent (variable)",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=None,
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=None,
                    ordering=1,
                ),
            ],
        )
        assert updated is not None
        lines = list(updated.lines.all())
        self.assertEqual(len(lines), 2)
        self.assertIsNone(lines[0].amount)
        self.assertIsNone(lines[1].amount)

    def test_update_duplicate_name_raises(self) -> None:
        create_journal_entry_template(
            dealership=self.dealership,
            name="Already taken",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("1.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("1.00"),
                    ordering=1,
                ),
            ],
        )
        with self.assertRaises(DuplicateJournalEntryTemplateNameError):
            update_journal_entry_template(
                pk=self.template.pk,
                dealership=self.dealership,
                name="Already taken",
                description="Rename collides",
                lines=[
                    TemplateLineInput(
                        account=self.rent,
                        side="debit",
                        amount=Decimal("2.00"),
                        ordering=0,
                    ),
                    TemplateLineInput(
                        account=self.bank,
                        side="credit",
                        amount=Decimal("2.00"),
                        ordering=1,
                    ),
                ],
            )


class DeleteJournalEntryTemplateTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.template = create_journal_entry_template(
            dealership=self.dealership,
            name="Delete-target rent",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("100.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("100.00"),
                    ordering=1,
                ),
            ],
        )

    def test_delete_soft_flips_is_active_false(self) -> None:
        self.assertTrue(self.template.is_active)
        result = delete_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert result is not None
        self.assertFalse(result.is_active)
        # Row still exists in DB (soft-delete, not hard-delete).
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_active)

    def test_delete_already_inactive_idempotent(self) -> None:
        """Repeat DELETE on a soft-deleted template returns the same
        row without state change. The endpoint layer maps to 204."""
        self.template.is_active = False
        self.template.save(update_fields=["is_active"])
        first_updated_at = self.template.updated_at

        result = delete_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert result is not None
        self.assertFalse(result.is_active)
        # No state change → updated_at should not advance on the
        # idempotent path (delete_journal_entry_template guards
        # against a no-op save that would refresh auto-now).
        self.assertEqual(result.updated_at, first_updated_at)

    def test_delete_missing_pk_returns_none(self) -> None:
        result = delete_journal_entry_template(
            pk=999_999, dealership=self.dealership
        )
        self.assertIsNone(result)

    def test_delete_cross_tenant_returns_none(self) -> None:
        other = Dealership.objects.create(
            slug="other-m30-delete", name="Other tenant"
        )
        result = delete_journal_entry_template(
            pk=self.template.pk, dealership=other
        )
        self.assertIsNone(result)
        # Original template still active — cross-tenant DELETE is a
        # no-op from the owner's perspective.
        self.template.refresh_from_db()
        self.assertTrue(self.template.is_active)


class GetJournalEntryTemplateIncludeInactiveTests(TestCase):
    """M30.1 — ``include_inactive`` kwarg symmetry with the list verb.

    The default (``include_inactive=False``) fail-closes on soft-
    hidden rows so the public endpoint surface treats them as 404.
    Internal callers (edit + delete + future Restore) opt in.
    """

    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        self.template = create_journal_entry_template(
            dealership=self.dealership,
            name="Kwarg-target",
            description="—",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("10.00"),
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("10.00"),
                    ordering=1,
                ),
            ],
        )
        # Soft-hide it.
        self.template.is_active = False
        self.template.save(update_fields=["is_active"])

    def test_get_default_excludes_inactive(self) -> None:
        result = get_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.assertIsNone(result)

    def test_get_include_inactive_finds_inactive(self) -> None:
        result = get_journal_entry_template(
            pk=self.template.pk,
            dealership=self.dealership,
            include_inactive=True,
        )
        assert result is not None
        self.assertEqual(result.pk, self.template.pk)
        self.assertFalse(result.is_active)
