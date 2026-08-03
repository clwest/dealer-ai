"""python manage.py seed_journey_office_accounting_workflow [--reset]

Milestone 20 · Increment 3 — deterministic seed delta for the
canonical office/accounting workflow journey.

Milestone 22 · Increment 2 — extended additively per M22 §5.g Option A
with a second fixture entry (``[M22.2-office-je-reversal] ...``)
that the M22.2 JE reversal Playwright journey targets. On each seed
invocation, any reversal entry that targets the M22.2 fixture is
deleted so the fixture stays reversible across suite re-runs — the
journey posts exactly one reversal against a fresh original each run.

The accounting journeys exercise:
- The M17 trial-balance surface (live compute + as-of picker + freeze
  into snapshot + prior-closes drill-down) — covered by the M20.3
  ``accounting_workflow.spec.ts`` journey using the M20.3 fixture entry.
- The M13.1 JE reversal workflow (JE detail → open dialog → fill reason
  → confirm → verify reversal linkage) — covered by the M22.2
  ``accounting_je_reversal.spec.ts`` journey using the M22.2 fixture
  entry.

Reuses the ``acceptance-owner`` persona already provisioned by
``seed_journey_owner_morning_review`` (which has ``dealer_owner``
role at the default dealership — sufficient for the M13/M14/M17
accounting endpoint permission gate
``IsSalesManagerOrOwnerAtActiveDealership``). No new user is added.

Per M20 planning §5.d Option B: composes the existing
``post_journal_entry`` + ``seed_default_coa`` service verbs — no
parallel write paths.

Idempotent via stable ``description`` values on each fixture entry
(used as fixture tags). The ``--reset`` flag deletes both seeded
entries (and their lines + any reversals via CASCADE) then re-posts
fresh rows.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from dealer_ai.models import Dealership, GLAccount, JournalEntry
from dealer_ai.services.accounting import (
    JournalLineInput,
    post_journal_entry,
    seed_default_coa,
)
from dealer_ai.services.tenancy import get_default_dealership


# Stable description acts as fixture tag — the journal entry created
# by this seed always uses this exact string, so subsequent seed
# invocations detect + reuse the existing row.
FIXTURE_DESCRIPTION = (
    "[M20.3-office-accounting-workflow] Fixture posting to give the "
    "trial-balance surface non-zero content for the acceptance journey."
)

# The seeded entry is a small balanced posting: cash in from a
# vehicle sale. Debit Bank Operating, credit Vehicle Sales — Retail.
FIXTURE_AMOUNT = Decimal("100.00")
FIXTURE_DEBIT_ACCOUNT_CODE = "110000"  # Bank — Operating (asset)
FIXTURE_CREDIT_ACCOUNT_CODE = "400000"  # Vehicle Sales — Retail (revenue)


# M22.2 additive fixture — a distinct balanced entry the JE reversal
# journey targets. Larger amount than the M20.3 fixture so the two
# postings are unambiguously separate in the trial-balance view (and
# so debug traces name them clearly).
M22_REVERSIBLE_FIXTURE_DESCRIPTION = (
    "[M22.2-office-je-reversal] Fixture entry the M22 JE reversal "
    "journey posts a reversal against; seed drops any pre-existing "
    "reversal targeting this row so re-runs stay idempotent."
)
M22_REVERSIBLE_FIXTURE_AMOUNT = Decimal("250.00")


def _existing_entry(dealership: Dealership, description: str = FIXTURE_DESCRIPTION):
    return JournalEntry.objects.filter(
        dealership=dealership, description=description
    ).order_by("pk").first()


class Command(BaseCommand):
    help = (
        "Seed the default COA + one balanced journal entry on the "
        "default dealership so the M20.3 office/accounting workflow "
        "acceptance journey has non-zero trial-balance content."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete the seeded journal entry (cascades to its "
                "lines) before re-posting a fresh entry."
            ),
        )

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            dealership = get_default_dealership()
            new_accounts = seed_default_coa(dealership)
            if new_accounts:
                self.stdout.write(
                    f"seeded {new_accounts} new COA account(s)."
                )

            if options["reset"]:
                self._reset(dealership)

            entry = self._provision_journal_entry(
                dealership,
                description=FIXTURE_DESCRIPTION,
                amount=FIXTURE_AMOUNT,
                memo_tag="M20.3",
            )
            reversible = self._provision_journal_entry(
                dealership,
                description=M22_REVERSIBLE_FIXTURE_DESCRIPTION,
                amount=M22_REVERSIBLE_FIXTURE_AMOUNT,
                memo_tag="M22.2",
            )
            # Drop any reversal targeting the M22.2 fixture so re-runs
            # keep it reversible. The M20.3 fixture is never reversed
            # by any shipped journey; skip cleanup there.
            deleted_reversals = self._drop_reversals_targeting(reversible)
            if deleted_reversals:
                self.stdout.write(
                    f"cleared {deleted_reversals} pre-existing "
                    f"reversal(s) targeting the M22.2 fixture."
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_office_accounting_workflow OK — "
                f"dealership={dealership.slug}, "
                f"m20_entry_pk={entry.pk} (amount={FIXTURE_AMOUNT}), "
                f"m22_reversible_pk={reversible.pk} "
                f"(amount={M22_REVERSIBLE_FIXTURE_AMOUNT}), "
                f"lines=Dr {FIXTURE_DEBIT_ACCOUNT_CODE} / "
                f"Cr {FIXTURE_CREDIT_ACCOUNT_CODE}."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        deleted_entries, _ = JournalEntry.objects.filter(
            dealership=dealership,
            description__in=(
                FIXTURE_DESCRIPTION,
                M22_REVERSIBLE_FIXTURE_DESCRIPTION,
            ),
        ).delete()
        self.stdout.write(
            f"reset: deleted {deleted_entries} journal entry row(s)."
        )

    def _drop_reversals_targeting(self, target: JournalEntry) -> int:
        # Reversal entries carry ``reverses_id = target.pk``. Deleting
        # them cascades their lines. Idempotent on suite re-runs where
        # the previous journey run posted a reversal.
        deleted, _ = JournalEntry.objects.filter(
            dealership=target.dealership, reverses_id=target.pk
        ).delete()
        return deleted

    def _provision_journal_entry(
        self,
        dealership: Dealership,
        description: str,
        amount: Decimal,
        memo_tag: str,
    ) -> JournalEntry:
        existing = _existing_entry(dealership, description)
        if existing is not None:
            self.stdout.write(
                f"reused existing journal entry pk={existing.pk} "
                f"({memo_tag} fixture)."
            )
            return existing

        debit_account = GLAccount.objects.get(
            dealership=dealership, code=FIXTURE_DEBIT_ACCOUNT_CODE
        )
        credit_account = GLAccount.objects.get(
            dealership=dealership, code=FIXTURE_CREDIT_ACCOUNT_CODE
        )
        entry = post_journal_entry(
            dealership=dealership,
            description=description,
            lines=[
                JournalLineInput(
                    account=debit_account,
                    debit=amount,
                    memo=f"Fixture debit for {memo_tag} acceptance journey.",
                ),
                JournalLineInput(
                    account=credit_account,
                    credit=amount,
                    memo=f"Fixture credit for {memo_tag} acceptance journey.",
                ),
            ],
        )
        self.stdout.write(
            f"posted journal entry pk={entry.pk} ({memo_tag} fixture)."
        )
        return entry
