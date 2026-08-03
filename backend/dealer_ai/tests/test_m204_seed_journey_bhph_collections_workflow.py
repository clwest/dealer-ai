"""Milestone 20 · Increment 4 — coverage for seed_journey_bhph_collections_workflow.

Verifies:
- Fresh invocation provisions the collector user with the
  ``sales_manager`` role (matches the M12 endpoint gate), plus a
  full fixture chain (buyer + vehicle + sale + BHPH note +
  historical payment + broken promise + collection contact +
  ordered repossession).
- The seeded promise is in ``broken`` state and the seeded
  repossession is in ``ordered`` state — these are the two
  operator-actionable signals that the Playwright journey renders
  from.
- Second invocation is idempotent (no duplicate note or child
  rows).
- ``--reset`` deletes the fixture chain (including the buyer +
  vehicle + sale), preserves the collector user, and a subsequent
  seed rebuilds fresh rows.
"""

from __future__ import annotations

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from dealer_ai.management.commands.seed_journey_bhph_collections_workflow import (
    COLLECTOR_PASSWORD,
    COLLECTOR_USERNAME,
    FIXTURE_STOCK,
)
from dealer_ai.models import (
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_REPO_STATE_ORDERED,
    ROLE_SALES_MANAGER,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    CollectionContact,
    CustomerLead,
    Repossession,
    Sale,
    UserDealershipRole,
    Vehicle,
)
from dealer_ai.services.tenancy import get_default_dealership

User = get_user_model()


def _run_seed(*args: str) -> str:
    stdout = StringIO()
    call_command(
        "seed_journey_bhph_collections_workflow", *args, stdout=stdout
    )
    return stdout.getvalue()


class SeedBhphCollectionsFreshRunTests(TestCase):
    def test_provisions_collector_user_with_sales_manager_role(self) -> None:
        _run_seed()

        user = User.objects.get(username=COLLECTOR_USERNAME)
        self.assertTrue(user.is_active)

        membership = UserDealershipRole.objects.get(
            user=user, dealership=get_default_dealership()
        )
        self.assertEqual(membership.role, ROLE_SALES_MANAGER)

    def test_provisions_fixture_vehicle(self) -> None:
        _run_seed()
        Vehicle.objects.get(
            dealership=get_default_dealership(),
            stock_number=FIXTURE_STOCK,
        )

    def test_provisions_fixture_buyer(self) -> None:
        _run_seed()
        CustomerLead.objects.get(
            email="acceptance-bhph-buyer@example.com"
        )

    def test_provisions_fixture_bhph_sale(self) -> None:
        _run_seed()
        sale = Sale.objects.get(vehicle__stock_number=FIXTURE_STOCK)
        self.assertEqual(sale.finance_type, "bhph")

    def test_provisions_fixture_bhph_note(self) -> None:
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        self.assertGreater(note.payment_amount, 0)

    def test_provisions_one_historical_payment(self) -> None:
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        self.assertEqual(
            BhphPayment.objects.filter(note=note).count(), 1
        )

    def test_provisions_broken_promise(self) -> None:
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        promise = BhphPromiseToPay.objects.get(note=note)
        self.assertEqual(promise.state, BHPH_PROMISE_STATE_BROKEN)

    def test_provisions_collection_contact(self) -> None:
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        self.assertEqual(
            CollectionContact.objects.filter(note=note).count(), 1
        )

    def test_provisions_ordered_repossession(self) -> None:
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        repo = Repossession.objects.get(note=note)
        self.assertEqual(repo.state, BHPH_REPO_STATE_ORDERED)

    def test_seeded_credentials_authenticate_collector(self) -> None:
        _run_seed()
        user = User.objects.get(username=COLLECTOR_USERNAME)
        self.assertTrue(user.check_password(COLLECTOR_PASSWORD))


class SeedBhphCollectionsIdempotencyTests(TestCase):
    def test_second_invocation_does_not_duplicate_note(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            BhphNote.objects.filter(
                sale__vehicle__stock_number=FIXTURE_STOCK
            ).count(),
            1,
        )

    def test_second_invocation_does_not_duplicate_children(self) -> None:
        _run_seed()
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        self.assertEqual(
            BhphPayment.objects.filter(note=note).count(), 1
        )
        self.assertEqual(
            BhphPromiseToPay.objects.filter(note=note).count(), 1
        )
        self.assertEqual(
            CollectionContact.objects.filter(note=note).count(), 1
        )
        self.assertEqual(Repossession.objects.filter(note=note).count(), 1)


class SeedBhphCollectionsResetTests(TestCase):
    def test_reset_deletes_fixture_chain_and_re_seeds(self) -> None:
        _run_seed()
        first_note_pk = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        ).pk

        _run_seed("--reset")

        notes = BhphNote.objects.filter(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        self.assertEqual(notes.count(), 1)
        self.assertNotEqual(notes.get().pk, first_note_pk)

    def test_reset_preserves_collector_user(self) -> None:
        _run_seed()
        _run_seed("--reset")
        self.assertTrue(
            User.objects.filter(username=COLLECTOR_USERNAME).exists()
        )
