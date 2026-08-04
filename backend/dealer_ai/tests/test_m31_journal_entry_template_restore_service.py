"""Milestone 31 · Increment 1 (SESSION_204) — template restore service tests.

Behaviors asserted (per MILESTONE_31_PLANNING.md §5.b D1–D2 + §5.e
M31.1 test spec):

- ``restore_journal_entry_template`` happy path flips
  ``is_active`` from False → True and returns the row.
- Repeat-Restore on an already-active row is idempotent: same row
  returned, no state change, ``updated_at`` does NOT advance.
- Returns ``None`` for cross-tenant or missing pk (endpoint layer
  maps to 404).
- Restore preserves ``name`` verbatim.
- Restore preserves ``description`` verbatim.
- Restore preserves lines — count, account, side, amount, memo,
  ordering — byte-identical before and after.
- Restore preserves ``created_at``.
- ``updated_at`` advances only on the state-change branch (False →
  True); unchanged on idempotent already-active repeat.
- Restore accepts already-active pk without raising and returns
  the projected row.

This file complements
``test_m28_journal_entry_template_service.py`` (M28.1 create /
list / get behaviors) and
``test_m30_journal_entry_template_edit_delete_service.py`` (M30.1
edit / soft-delete behaviors). Together they lock the full
lifecycle contract: create → edit → deactivate → restore.
"""

from __future__ import annotations

from decimal import Decimal
import time

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
    TemplateLineInput,
    create_journal_entry_template,
    delete_journal_entry_template,
    get_journal_entry_template,
    restore_journal_entry_template,
)
from dealer_ai.services.tenancy import get_default_dealership


def _make_accounts(dealership: Dealership) -> tuple[GLAccount, GLAccount]:
    rent = GLAccount.objects.create(
        dealership=dealership,
        code="M31-615000",
        name="Rent Expense",
        account_type=GL_ACCOUNT_TYPE_EXPENSE,
    )
    bank = GLAccount.objects.create(
        dealership=dealership,
        code="M31-110000",
        name="Bank — Operating",
        account_type=GL_ACCOUNT_TYPE_ASSET,
    )
    return rent, bank


def _snapshot_line_fields(template: JournalEntryTemplate) -> list[dict]:
    """Capture every non-derived line field for byte-identical
    before/after preservation assertions."""
    return sorted(
        [
            {
                "account_id": line.account_id,
                "side": line.side,
                "amount": line.amount,
                "memo": line.memo,
                "ordering": line.ordering,
            }
            for line in template.lines.all()
        ],
        key=lambda row: row["ordering"],
    )


class RestoreJournalEntryTemplateTests(TestCase):
    def setUp(self) -> None:
        self.dealership = get_default_dealership()
        self.rent, self.bank = _make_accounts(self.dealership)
        # Seed a template + deactivate it so the fixture reflects the
        # normal Restore precondition (soft-hidden row).
        self.template = create_journal_entry_template(
            dealership=self.dealership,
            name="Monthly rent",
            description="For Restore-target fixture",
            lines=[
                TemplateLineInput(
                    account=self.rent,
                    side="debit",
                    amount=Decimal("3500.00"),
                    memo="rent debit",
                    ordering=0,
                ),
                TemplateLineInput(
                    account=self.bank,
                    side="credit",
                    amount=Decimal("3500.00"),
                    memo="bank credit",
                    ordering=1,
                ),
            ],
        )
        self.created_at_before = self.template.created_at
        self.lines_before = _snapshot_line_fields(self.template)
        # Deactivate via the M30.1 verb so the fixture is a
        # legitimate soft-hidden row.
        delete_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.template.refresh_from_db()
        self.assertFalse(self.template.is_active)
        self.deactivated_updated_at = self.template.updated_at

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_restore_happy_path_flips_is_active_true(self) -> None:
        # Small sleep so any auto-now delta is observable.
        time.sleep(0.01)
        result = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.assertIsNotNone(result)
        assert result is not None  # type-narrow for the checker
        self.assertTrue(result.is_active)
        # DB reflects the flip.
        self.template.refresh_from_db()
        self.assertTrue(self.template.is_active)

    def test_restore_returns_the_projected_row(self) -> None:
        result = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert result is not None
        # The returned instance is the same template row.
        self.assertEqual(result.pk, self.template.pk)
        self.assertEqual(result.name, "Monthly rent")

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_repeat_restore_on_active_row_is_idempotent(self) -> None:
        # First Restore: state change False → True.
        first = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert first is not None
        self.assertTrue(first.is_active)
        # Second Restore: no state change, same row returned.
        second = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert second is not None
        self.assertEqual(second.pk, first.pk)
        self.assertTrue(second.is_active)

    def test_repeat_restore_does_not_advance_updated_at(self) -> None:
        """Idempotent Restore: updated_at unchanged on the already-active
        branch (contract per D2)."""
        # First Restore: state change False → True (updated_at advances).
        first = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert first is not None
        updated_after_first = first.updated_at
        # Second Restore: no state change; updated_at must NOT advance.
        time.sleep(0.05)  # ensure any auto-now would produce a delta
        second = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert second is not None
        self.assertEqual(second.updated_at, updated_after_first)

    def test_restore_on_never_deactivated_row_is_idempotent(self) -> None:
        """A pk that has always been active still returns the row
        cleanly (no error, no state change)."""
        # Reactivate first so we have an always-active baseline.
        always_active = create_journal_entry_template(
            dealership=self.dealership,
            name="Always active",
            description="Never touched",
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
        updated_before = always_active.updated_at
        time.sleep(0.01)
        result = restore_journal_entry_template(
            pk=always_active.pk, dealership=self.dealership
        )
        assert result is not None
        self.assertTrue(result.is_active)
        # updated_at unchanged because no save happened.
        always_active.refresh_from_db()
        self.assertEqual(always_active.updated_at, updated_before)

    # ------------------------------------------------------------------
    # Missing / cross-tenant
    # ------------------------------------------------------------------

    def test_restore_missing_pk_returns_none(self) -> None:
        result = restore_journal_entry_template(
            pk=999_999, dealership=self.dealership
        )
        self.assertIsNone(result)

    def test_restore_cross_tenant_returns_none(self) -> None:
        other = Dealership.objects.create(
            slug="other-restore-svc", name="Other tenant"
        )
        # Foreign, soft-hidden.
        foreign = JournalEntryTemplate.objects.create(
            dealership=other,
            name="Foreign",
            description="—",
            is_active=False,
        )
        result = restore_journal_entry_template(
            pk=foreign.pk, dealership=self.dealership
        )
        self.assertIsNone(result)
        # Foreign row unchanged.
        foreign.refresh_from_db()
        self.assertFalse(foreign.is_active)

    # ------------------------------------------------------------------
    # Preservation contract (D2)
    # ------------------------------------------------------------------

    def test_restore_preserves_name(self) -> None:
        restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, "Monthly rent")

    def test_restore_preserves_description(self) -> None:
        restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.template.refresh_from_db()
        self.assertEqual(
            self.template.description, "For Restore-target fixture"
        )

    def test_restore_preserves_lines_byte_identical(self) -> None:
        """Lines (count + account + side + amount + memo + ordering)
        are byte-identical before and after Restore."""
        restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.template.refresh_from_db()
        lines_after = _snapshot_line_fields(self.template)
        self.assertEqual(lines_after, self.lines_before)
        # Also confirm no row-count change on the line table.
        self.assertEqual(
            JournalEntryTemplateLine.objects.filter(
                template=self.template
            ).count(),
            2,
        )

    def test_restore_preserves_created_at(self) -> None:
        restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.template.refresh_from_db()
        self.assertEqual(self.template.created_at, self.created_at_before)

    def test_restore_advances_updated_at_only_on_state_change(self) -> None:
        """Combines the two updated_at contract halves in a single
        end-to-end trace: state-change branch DOES advance;
        idempotent branch does NOT."""
        # State-change branch.
        time.sleep(0.01)
        first = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert first is not None
        self.assertGreater(first.updated_at, self.deactivated_updated_at)
        updated_after_first = first.updated_at
        # Idempotent branch.
        time.sleep(0.05)
        second = restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        assert second is not None
        self.assertEqual(second.updated_at, updated_after_first)

    # ------------------------------------------------------------------
    # Interaction with get_journal_entry_template
    # ------------------------------------------------------------------

    def test_restored_row_is_visible_via_default_get(self) -> None:
        """After Restore, the default get (include_inactive=False)
        finds the row again — confirms the operator-facing
        active-only surface completes the round-trip."""
        # Deactivated fixture is invisible to default get.
        self.assertIsNone(
            get_journal_entry_template(
                pk=self.template.pk, dealership=self.dealership
            )
        )
        # Restore.
        restore_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        # Now visible via default get.
        visible = get_journal_entry_template(
            pk=self.template.pk, dealership=self.dealership
        )
        self.assertIsNotNone(visible)
        assert visible is not None
        self.assertTrue(visible.is_active)
