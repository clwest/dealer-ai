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

from decimal import Decimal

from dealer_ai.management.commands.seed_journey_bhph_collections_workflow import (
    COLLECTOR_PASSWORD,
    COLLECTOR_USERNAME,
    FIXTURE_STOCK,
    M23_ORIG_FIXTURE_BUYER_EMAIL,
    M23_ORIG_FIXTURE_STOCK,
    M23_PAY_FIXTURE_PRINCIPAL,
    M23_PAY_FIXTURE_STOCK,
)
from dealer_ai.models import (
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_PROMISED,
    BHPH_REPO_STATE_ORDERED,
    BHPH_REPO_STATE_RECOVERED,
    CONDITION_REPORT_STATUS_COMPLETE,
    ROLE_SALES_MANAGER,
    BhphNote,
    BhphPayment,
    BhphPromiseToPay,
    CollectionContact,
    ConditionReport,
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
        # M21.2 extended the seed with a second promise in
        # ``promised`` state; the original ``broken`` promise remains.
        broken = BhphPromiseToPay.objects.filter(
            note=note, state=BHPH_PROMISE_STATE_BROKEN
        )
        self.assertEqual(broken.count(), 1)

    def test_m21_2_provisions_promised_state_promise(self) -> None:
        """M21.2 fixture — second promise in ``promised`` state so the
        journey has a clean target for the mark-broken step."""
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        promised = BhphPromiseToPay.objects.filter(
            note=note, state=BHPH_PROMISE_STATE_PROMISED
        )
        self.assertEqual(promised.count(), 1)

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
        # M21.2 extended the seed with a second repossession in
        # ``recovered`` state; the original ``ordered`` repo remains.
        ordered = Repossession.objects.filter(
            note=note, state=BHPH_REPO_STATE_ORDERED
        )
        self.assertEqual(ordered.count(), 1)

    def test_m21_2_provisions_recovered_repossession(self) -> None:
        """M21.2 fixture — second repossession pre-transitioned to
        ``recovered`` so the journey can exercise mark-re-intaked
        without a two-step transition mid-journey."""
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        recovered = Repossession.objects.filter(
            note=note, state=BHPH_REPO_STATE_RECOVERED
        )
        self.assertEqual(recovered.count(), 1)

    def test_m21_2_provisions_complete_condition_report(self) -> None:
        """M21.2 fixture — one ConditionReport in ``complete`` state
        for the fixture vehicle, referenceable by the mark-re-intaked
        step."""
        _run_seed()
        vehicle = Vehicle.objects.get(stock_number=FIXTURE_STOCK)
        reports = ConditionReport.objects.filter(
            vehicle=vehicle, status=CONDITION_REPORT_STATUS_COMPLETE
        )
        self.assertEqual(reports.count(), 1)
        report = reports.get()
        self.assertIsNotNone(report.completed_at)

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
        # M21.2 extended the fixture to two promises (broken + promised)
        # and two repossessions (ordered + recovered). The idempotency
        # guarantee still holds — counts stay stable.
        self.assertEqual(
            BhphPromiseToPay.objects.filter(note=note).count(), 2
        )
        self.assertEqual(
            CollectionContact.objects.filter(note=note).count(), 1
        )
        self.assertEqual(Repossession.objects.filter(note=note).count(), 2)
        vehicle = Vehicle.objects.get(stock_number=FIXTURE_STOCK)
        self.assertEqual(
            ConditionReport.objects.filter(vehicle=vehicle).count(), 1
        )


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


# ---------------------------------------------------------------------
# Milestone 23 · Increment 2 — origination fixture coverage.
# ---------------------------------------------------------------------


class SeedBhphCollectionsM23OriginationFixtureTests(TestCase):
    def test_m23_orig_sale_provisioned_bhph_marked_no_note(self) -> None:
        from dealer_ai.models import SALE_FINANCE_TYPE_BHPH

        _run_seed()
        sale = Sale.objects.get(
            vehicle__stock_number=M23_ORIG_FIXTURE_STOCK
        )
        self.assertEqual(sale.finance_type, SALE_FINANCE_TYPE_BHPH)
        self.assertFalse(
            BhphNote.objects.filter(sale=sale).exists(),
            "M23.2 origination fixture sale must have no attached BhphNote — "
            "the journey creates it.",
        )

    def test_m23_orig_sale_distinct_from_m20_collections_fixture(self) -> None:
        _run_seed()
        m20_sale = Sale.objects.get(
            vehicle__stock_number=FIXTURE_STOCK
        )
        m23_sale = Sale.objects.get(
            vehicle__stock_number=M23_ORIG_FIXTURE_STOCK
        )
        self.assertNotEqual(m20_sale.pk, m23_sale.pk)
        self.assertNotEqual(m20_sale.vehicle_id, m23_sale.vehicle_id)
        self.assertNotEqual(m20_sale.buyer_id, m23_sale.buyer_id)

    def test_m23_orig_buyer_uses_expected_email(self) -> None:
        _run_seed()
        buyer = CustomerLead.objects.get(email=M23_ORIG_FIXTURE_BUYER_EMAIL)
        sale = Sale.objects.get(
            vehicle__stock_number=M23_ORIG_FIXTURE_STOCK
        )
        self.assertEqual(sale.buyer_id, buyer.pk)

    def test_success_message_prints_m23_orig_sale_pk(self) -> None:
        # The M23.2 journey parses this line from stdout to know which
        # sale to originate a note against. Ensure the key format the
        # journey greps for stays stable.
        output = _run_seed()
        self.assertIn("m23_orig_sale_pk=", output)

    def test_second_invocation_does_not_duplicate_m23_orig_sale(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            Sale.objects.filter(
                vehicle__stock_number=M23_ORIG_FIXTURE_STOCK
            ).count(),
            1,
        )

    def test_seed_sweeps_note_created_against_m23_orig_sale(self) -> None:
        from dealer_ai.models import BHPH_PAYMENT_FREQUENCY_WEEKLY
        import datetime as dt

        _run_seed()
        sale = Sale.objects.get(
            vehicle__stock_number=M23_ORIG_FIXTURE_STOCK
        )
        # Simulate what the M23.2 journey does — create a note
        # against the origination fixture sale. Direct create
        # matches the seed's demo-archetype convention.
        note = BhphNote.objects.create(
            dealership=sale.dealership,
            sale=sale,
            principal_financed=Decimal("5000.00"),
            apr=Decimal("18.50"),
            term_weeks=52,
            payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
            payment_amount=Decimal("120.00"),
            first_payment_due=dt.date.today() + dt.timedelta(days=7),
        )
        self.assertTrue(
            BhphNote.objects.filter(pk=note.pk).exists(),
            "note should exist before re-seed",
        )

        _run_seed()

        # Note should have been swept; sale + fixture chain remain.
        self.assertFalse(
            BhphNote.objects.filter(pk=note.pk).exists(),
            "note should be cleared by the second seed invocation",
        )
        self.assertTrue(
            Sale.objects.filter(pk=sale.pk).exists(),
            "M23.2 origination sale itself must survive the note cleanup",
        )

    def test_reset_deletes_m23_orig_sale_chain(self) -> None:
        _run_seed()
        _run_seed("--reset")
        # After reset, the M23.2 fixture re-provisions as fresh rows.
        sales = Sale.objects.filter(
            vehicle__stock_number=M23_ORIG_FIXTURE_STOCK
        )
        self.assertEqual(sales.count(), 1)


# ---------------------------------------------------------------------
# Milestone 23 · Increment 3 — payment-intake fixture coverage.
# ---------------------------------------------------------------------


class SeedBhphCollectionsM23PaymentIntakeFixtureTests(TestCase):
    def test_m23_pay_note_provisioned_bhph_marked_no_payments(self) -> None:
        from dealer_ai.models import BhphPayment, SALE_FINANCE_TYPE_BHPH

        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=M23_PAY_FIXTURE_STOCK
        )
        self.assertEqual(note.sale.finance_type, SALE_FINANCE_TYPE_BHPH)
        self.assertFalse(
            BhphPayment.objects.filter(note=note).exists(),
            "M23.3 payment-intake fixture note must have no attached "
            "BhphPayment — the journey records the first payment.",
        )

    def test_m23_pay_note_distinct_from_m20_and_m23_orig(self) -> None:
        _run_seed()
        m20_note = BhphNote.objects.get(
            sale__vehicle__stock_number=FIXTURE_STOCK
        )
        m23_pay_note = BhphNote.objects.get(
            sale__vehicle__stock_number=M23_PAY_FIXTURE_STOCK
        )
        self.assertNotEqual(m20_note.pk, m23_pay_note.pk)
        self.assertNotEqual(m20_note.sale_id, m23_pay_note.sale_id)

    def test_m23_pay_note_has_expected_principal(self) -> None:
        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=M23_PAY_FIXTURE_STOCK
        )
        self.assertEqual(
            note.principal_financed, M23_PAY_FIXTURE_PRINCIPAL
        )

    def test_success_message_prints_m23_pay_note_pk(self) -> None:
        output = _run_seed()
        self.assertIn("m23_pay_note_pk=", output)

    def test_second_invocation_does_not_duplicate_m23_pay_note(self) -> None:
        _run_seed()
        _run_seed()
        self.assertEqual(
            BhphNote.objects.filter(
                sale__vehicle__stock_number=M23_PAY_FIXTURE_STOCK
            ).count(),
            1,
        )

    def test_seed_sweeps_payment_recorded_against_m23_pay_note(self) -> None:
        from dealer_ai.models import BHPH_PAYMENT_METHOD_CASH, BhphPayment
        from dealer_ai.services.bhph_payments.bhph_payment import (
            record_payment,
        )
        from django.utils import timezone

        _run_seed()
        note = BhphNote.objects.get(
            sale__vehicle__stock_number=M23_PAY_FIXTURE_STOCK
        )
        # Simulate what the M23.3 journey does — record a payment
        # via the M12 service verb (matches the DRF endpoint's
        # composition path).
        payment = record_payment(
            dealership=note.dealership,
            note=note,
            paid_at=timezone.now(),
            amount=Decimal("100.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        self.assertTrue(
            BhphPayment.objects.filter(pk=payment.pk).exists(),
            "payment should exist before re-seed",
        )

        _run_seed()

        # Payment should have been swept; note + fixture chain remain.
        self.assertFalse(
            BhphPayment.objects.filter(pk=payment.pk).exists(),
            "payment should be cleared by the second seed invocation",
        )
        self.assertTrue(
            BhphNote.objects.filter(pk=note.pk).exists(),
            "M23.3 fixture note must survive the payment cleanup",
        )

    def test_reset_deletes_m23_pay_note_chain(self) -> None:
        _run_seed()
        _run_seed("--reset")
        # After reset, the M23.3 fixture re-provisions as fresh rows.
        notes = BhphNote.objects.filter(
            sale__vehicle__stock_number=M23_PAY_FIXTURE_STOCK
        )
        self.assertEqual(notes.count(), 1)
