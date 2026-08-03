"""python manage.py seed_journey_office_accounting_workflow [--reset]

Milestone 20 · Increment 3 — deterministic seed delta for the
canonical office/accounting workflow journey.

The accounting journey exercises the M17 trial-balance surface (live
compute + as-of picker + freeze into snapshot + prior-closes drill-
down). For the trial balance to have meaningful content the seed
must post at least one balanced journal entry on the default
dealership.

Reuses the ``acceptance-owner`` persona already provisioned by
``seed_journey_owner_morning_review`` (which has ``dealer_owner``
role at the default dealership — sufficient for the M13/M14/M17
accounting endpoint permission gate
``IsSalesManagerOrOwnerAtActiveDealership``). No new user is added.

Per M20 planning §5.d Option B: composes the existing
``post_journal_entry`` + ``seed_default_coa`` service verbs — no
parallel write paths.

Idempotent via a stable ``description`` on the journal entry (used
as the fixture tag). The ``--reset`` flag deletes the seeded entry
(and its lines via CASCADE) then re-posts a fresh row.
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


def _existing_entry(dealership: Dealership):
    return JournalEntry.objects.filter(
        dealership=dealership, description=FIXTURE_DESCRIPTION
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

            entry = self._provision_journal_entry(dealership)

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_journey_office_accounting_workflow OK — "
                f"dealership={dealership.slug}, "
                f"journal_entry_pk={entry.pk}, "
                f"amount={FIXTURE_AMOUNT}, "
                f"lines=Dr {FIXTURE_DEBIT_ACCOUNT_CODE} / "
                f"Cr {FIXTURE_CREDIT_ACCOUNT_CODE}."
            )
        )

    def _reset(self, dealership: Dealership) -> None:
        deleted_entries, _ = JournalEntry.objects.filter(
            dealership=dealership, description=FIXTURE_DESCRIPTION
        ).delete()
        self.stdout.write(
            f"reset: deleted {deleted_entries} journal entry row(s)."
        )

    def _provision_journal_entry(
        self, dealership: Dealership
    ) -> JournalEntry:
        existing = _existing_entry(dealership)
        if existing is not None:
            self.stdout.write(
                f"reused existing journal entry pk={existing.pk}."
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
            description=FIXTURE_DESCRIPTION,
            lines=[
                JournalLineInput(
                    account=debit_account,
                    debit=FIXTURE_AMOUNT,
                    memo="Fixture debit for M20.3 acceptance journey.",
                ),
                JournalLineInput(
                    account=credit_account,
                    credit=FIXTURE_AMOUNT,
                    memo="Fixture credit for M20.3 acceptance journey.",
                ),
            ],
        )
        self.stdout.write(f"posted journal entry pk={entry.pk}.")
        return entry
