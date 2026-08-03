"""Milestone 20 · Increment 3 — coverage for seed_journey_office_accounting_workflow.

Verifies:
- Fresh invocation seeds the default COA (if missing) + posts a
  balanced journal entry on the default dealership.
- The seeded entry has the expected shape (description tag,
  amount, two lines Dr Bank Operating / Cr Vehicle Sales Retail).
- Second invocation is idempotent (does not duplicate the entry).
- ``--reset`` deletes the seeded entry (cascades its lines) and a
  subsequent seed posts a fresh entry.
- No new users are provisioned — the accounting journey reuses the
  ``acceptance-owner`` persona from
  ``seed_journey_owner_morning_review``.

Milestone 22 · Increment 2 — extended for the M22.2 reversible-JE
fixture that the JE reversal Playwright journey targets. Covers:
- Second fixture (M22.2 tag) provisions alongside the M20.3 fixture.
- Second invocation is idempotent for BOTH fixtures.
- Any reversal targeting the M22.2 fixture gets cleared on subsequent
  seed invocations so re-runs stay reversible.
- ``--reset`` deletes both fixtures.
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_journey_office_accounting_workflow import (
    FIXTURE_AMOUNT,
    FIXTURE_CREDIT_ACCOUNT_CODE,
    FIXTURE_DEBIT_ACCOUNT_CODE,
    FIXTURE_DESCRIPTION,
    M22_REVERSIBLE_FIXTURE_AMOUNT,
    M22_REVERSIBLE_FIXTURE_DESCRIPTION,
)
from dealer_ai.models import GLAccount, JournalEntry, JournalEntryLine
from dealer_ai.services.accounting import reverse_journal_entry
from dealer_ai.services.tenancy import get_default_dealership


def _run_seed(*args: str) -> str:
    stdout = StringIO()
    call_command(
        "seed_journey_office_accounting_workflow", *args, stdout=stdout
    )
    return stdout.getvalue()


class SeedOfficeAccountingWorkflowFreshRunTests(TestCase):
    def test_default_coa_is_present_after_seed(self) -> None:
        _run_seed()
        dealership = get_default_dealership()
        self.assertTrue(
            GLAccount.objects.filter(
                dealership=dealership, code=FIXTURE_DEBIT_ACCOUNT_CODE
            ).exists()
        )
        self.assertTrue(
            GLAccount.objects.filter(
                dealership=dealership, code=FIXTURE_CREDIT_ACCOUNT_CODE
            ).exists()
        )

    def test_posts_fixture_journal_entry(self) -> None:
        _run_seed()
        entry = JournalEntry.objects.get(description=FIXTURE_DESCRIPTION)
        self.assertEqual(entry.dealership_id, get_default_dealership().pk)

    def test_journal_entry_has_two_balanced_lines(self) -> None:
        _run_seed()
        entry = JournalEntry.objects.get(description=FIXTURE_DESCRIPTION)
        lines = list(
            JournalEntryLine.objects.filter(entry=entry).order_by("pk")
        )
        self.assertEqual(len(lines), 2)

        debit_line = next(
            l for l in lines if l.debit == FIXTURE_AMOUNT
        )
        credit_line = next(
            l for l in lines if l.credit == FIXTURE_AMOUNT
        )
        self.assertEqual(debit_line.account.code, FIXTURE_DEBIT_ACCOUNT_CODE)
        self.assertEqual(
            credit_line.account.code, FIXTURE_CREDIT_ACCOUNT_CODE
        )
        self.assertEqual(debit_line.credit, Decimal("0.00"))
        self.assertEqual(credit_line.debit, Decimal("0.00"))


class SeedOfficeAccountingWorkflowIdempotencyTests(TestCase):
    def test_second_invocation_does_not_duplicate_entry(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            JournalEntry.objects.filter(
                description=FIXTURE_DESCRIPTION
            ).count(),
            1,
        )

    def test_second_invocation_reports_reuse(self) -> None:
        _run_seed()
        output = _run_seed()
        self.assertIn("reused existing journal entry", output)


class SeedOfficeAccountingWorkflowResetTests(TestCase):
    def test_reset_deletes_entry_and_re_posts_fresh(self) -> None:
        _run_seed()
        first_pk = JournalEntry.objects.get(
            description=FIXTURE_DESCRIPTION
        ).pk

        _run_seed("--reset")

        entries = JournalEntry.objects.filter(
            description=FIXTURE_DESCRIPTION
        )
        self.assertEqual(entries.count(), 1)
        self.assertNotEqual(entries.get().pk, first_pk)

    def test_reset_cascades_to_journal_entry_lines(self) -> None:
        _run_seed()
        first_entry = JournalEntry.objects.get(
            description=FIXTURE_DESCRIPTION
        )
        first_line_pks = set(
            JournalEntryLine.objects.filter(entry=first_entry)
            .values_list("pk", flat=True)
        )

        _run_seed("--reset")

        for line_pk in first_line_pks:
            self.assertFalse(
                JournalEntryLine.objects.filter(pk=line_pk).exists(),
                f"line pk={line_pk} should have been cascade-deleted",
            )


# ---------------------------------------------------------------------
# Milestone 22 · Increment 2 — reversible-JE fixture coverage.
# ---------------------------------------------------------------------


class SeedOfficeAccountingWorkflowM22ReversibleFixtureTests(TestCase):
    def test_m22_fixture_provisioned_alongside_m20_fixture(self) -> None:
        _run_seed()
        dealership = get_default_dealership()
        self.assertTrue(
            JournalEntry.objects.filter(
                dealership=dealership,
                description=M22_REVERSIBLE_FIXTURE_DESCRIPTION,
            ).exists(),
            "M22.2 reversible-JE fixture should be provisioned",
        )
        self.assertTrue(
            JournalEntry.objects.filter(
                dealership=dealership,
                description=FIXTURE_DESCRIPTION,
            ).exists(),
            "M20.3 fixture should still be provisioned alongside M22.2",
        )

    def test_m22_fixture_has_expected_amount_and_shape(self) -> None:
        _run_seed()
        entry = JournalEntry.objects.get(
            description=M22_REVERSIBLE_FIXTURE_DESCRIPTION
        )
        lines = list(
            JournalEntryLine.objects.filter(entry=entry).order_by("pk")
        )
        self.assertEqual(len(lines), 2)
        debit_line = next(
            line for line in lines if line.debit == M22_REVERSIBLE_FIXTURE_AMOUNT
        )
        credit_line = next(
            line for line in lines if line.credit == M22_REVERSIBLE_FIXTURE_AMOUNT
        )
        self.assertEqual(
            debit_line.account.code, FIXTURE_DEBIT_ACCOUNT_CODE
        )
        self.assertEqual(
            credit_line.account.code, FIXTURE_CREDIT_ACCOUNT_CODE
        )
        # Amounts differ from the M20.3 fixture so debug traces name
        # them unambiguously.
        self.assertNotEqual(
            M22_REVERSIBLE_FIXTURE_AMOUNT,
            FIXTURE_AMOUNT,
            "M22.2 fixture amount should differ from M20.3 fixture "
            "amount to keep the two visually distinct in the trial "
            "balance",
        )

    def test_second_invocation_does_not_duplicate_m22_fixture(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            JournalEntry.objects.filter(
                description=M22_REVERSIBLE_FIXTURE_DESCRIPTION
            ).count(),
            1,
        )

    def test_seed_clears_reversal_targeting_m22_fixture(self) -> None:
        _run_seed()
        dealership = get_default_dealership()
        target = JournalEntry.objects.get(
            description=M22_REVERSIBLE_FIXTURE_DESCRIPTION
        )
        # Simulate what the M22.2 journey does — post a reversal
        # targeting the fixture via the same service verb the M13.1
        # DRF endpoint composes.
        reversal = reverse_journal_entry(
            dealership=dealership,
            entry=target,
            reason="Test — verifying seed cleans up reversals",
        )
        self.assertTrue(
            JournalEntry.objects.filter(pk=reversal.pk).exists(),
            "reversal should exist before re-seed",
        )

        _run_seed()

        # Reversal should have been swept; fixture remains reversible.
        self.assertFalse(
            JournalEntry.objects.filter(pk=reversal.pk).exists(),
            "reversal should be cleared by the second seed invocation",
        )
        self.assertTrue(
            JournalEntry.objects.filter(pk=target.pk).exists(),
            "fixture entry itself must survive the reversal cleanup",
        )

    def test_reset_deletes_m22_fixture(self) -> None:
        _run_seed()
        _run_seed("--reset")
        # After reset, both fixtures re-provision as fresh rows —
        # verify the M22.2 fixture exists exactly once after reset.
        self.assertEqual(
            JournalEntry.objects.filter(
                description=M22_REVERSIBLE_FIXTURE_DESCRIPTION
            ).count(),
            1,
        )
