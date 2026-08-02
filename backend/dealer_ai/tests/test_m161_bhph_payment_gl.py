"""Milestone 16 · Increment 1 (SESSION_143) — BHPH payment GL detector tests.

Mirror `test_m132_vehicle_cost_service.py` + `test_m132_vehicle_cost_tasks.py`
structure. Covers:

- ``detect_unposted_bhph_payments`` pure query.
- ``post_bhph_payment_journal`` happy path (2- and 3-line variants
  per §5.e Option A) + all guard classes.
- ``post_all_unposted_bhph_payments_for_dealership`` orchestrator +
  per-row failure isolation.
- Celery task wiring + name-registration constants.
- Beat-schedule 11:00 slot registration.
- Trial-balance reflection of new entries.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_ACH,
    BHPH_PAYMENT_METHOD_CASH,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPayment,
    Dealership,
    GLAccount,
    JournalEntry,
    JournalEntryLine,
    Sale,
    Vehicle,
)
from dealer_ai.services.accounting import (
    BHPH_INTEREST_INCOME_ACCOUNT_CODE,
    BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE,
    CASH_ACCOUNT_CODE,
    CrossTenantGLAccountError,
    MissingDefaultAccountError,
    UnexpectedBhphPaymentFeesError,
    compute_trial_balance,
    detect_unposted_bhph_payments,
    post_all_unposted_bhph_payments_for_dealership,
    post_bhph_payment_journal,
)
from dealer_ai.services.accounting.tasks import (
    POST_BHPH_PAYMENT_FOR_ALL_TENANTS_TASK_NAME,
    POST_BHPH_PAYMENT_FOR_TENANT_TASK_NAME,
    post_bhph_payment_journals_for_all_tenants,
    post_bhph_payment_journals_for_dealership,
)
from dealer_ai.tests._auth_helpers import make_dealership


def _make_note(
    dealership: Dealership,
    stock: str,
    principal: Decimal = Decimal("8000.00"),
) -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Sonata",
        price=Decimal("10500.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("10500.00"),
        finance_type=SALE_FINANCE_TYPE_BHPH,
        gross_realized=Decimal("1200.00"),
    )
    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=principal,
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
    )


def _make_payment(
    dealership: Dealership,
    note: BhphNote,
    *,
    amount: Decimal = Decimal("95.00"),
    principal: Decimal = Decimal("61.31"),
    interest: Decimal = Decimal("33.69"),
    fees: Decimal = Decimal("0.00"),
    method: str = BHPH_PAYMENT_METHOD_CASH,
    paid_at: dt.datetime | None = None,
) -> BhphPayment:
    """Direct-create a BhphPayment row with a pre-computed split.

    Bypasses ``record_payment`` so tests can control the split
    values precisely for zero-interest / zero-principal branches
    without engineering exotic notes.
    """
    return BhphPayment.objects.create(
        dealership=dealership,
        note=note,
        paid_at=paid_at or timezone.now(),
        amount=amount,
        method=method,
        applied_to_fees=fees,
        applied_to_interest=interest,
        applied_to_principal=principal,
    )


# ---------------------------------------------------------------------------
# detect_unposted_bhph_payments
# ---------------------------------------------------------------------------


class DetectUnpostedBhphPaymentsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m161-det")
        self.note = _make_note(self.dealership, "M161-DET")

    def test_returns_unposted_rows(self) -> None:
        p1 = _make_payment(self.dealership, self.note)
        p2 = _make_payment(
            self.dealership,
            self.note,
            paid_at=timezone.now() + dt.timedelta(days=7),
        )
        qs = detect_unposted_bhph_payments(dealership=self.dealership)
        self.assertEqual(
            set(qs.values_list("pk", flat=True)), {p1.pk, p2.pk}
        )

    def test_excludes_already_posted(self) -> None:
        posted = _make_payment(self.dealership, self.note)
        posted.posted_at = timezone.now()
        posted.save(update_fields=["posted_at"])
        qs = detect_unposted_bhph_payments(dealership=self.dealership)
        self.assertEqual(qs.count(), 0)

    def test_scoped_by_dealership(self) -> None:
        other = make_dealership(slug="m161-det-other")
        other_note = _make_note(other, "M161-DET-OTHER")
        _make_payment(other, other_note)
        qs = detect_unposted_bhph_payments(dealership=self.dealership)
        self.assertEqual(qs.count(), 0)

    def test_ordering_paid_at_then_id(self) -> None:
        # Insert out of paid_at order; expect ascending paid_at ordering.
        now = timezone.now()
        p_late = _make_payment(
            self.dealership,
            self.note,
            paid_at=now + dt.timedelta(days=7),
        )
        p_early = _make_payment(
            self.dealership,
            self.note,
            paid_at=now,
        )
        pks = list(
            detect_unposted_bhph_payments(dealership=self.dealership)
            .values_list("pk", flat=True)
        )
        self.assertEqual(pks, [p_early.pk, p_late.pk])

    def test_empty_result_for_zero_payment_tenant(self) -> None:
        # No payments recorded — zero-portfolio semantics.
        qs = detect_unposted_bhph_payments(dealership=self.dealership)
        self.assertEqual(qs.count(), 0)


# ---------------------------------------------------------------------------
# post_bhph_payment_journal — happy path branches (§5.e Option A)
# ---------------------------------------------------------------------------


class PostBhphPaymentJournalHappyPathTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m161-hp")
        self.note = _make_note(self.dealership, "M161-HP")

    def test_principal_plus_interest_posts_three_line_entry(self) -> None:
        payment = _make_payment(
            self.dealership,
            self.note,
            amount=Decimal("95.00"),
            principal=Decimal("61.31"),
            interest=Decimal("33.69"),
        )
        post_bhph_payment_journal(
            dealership=self.dealership, bhph_payment=payment
        )
        entry = JournalEntry.objects.get()
        lines = list(entry.lines.order_by("id"))
        self.assertEqual(len(lines), 3)

        cash_line, principal_line, interest_line = lines
        self.assertEqual(cash_line.account.code, CASH_ACCOUNT_CODE)
        self.assertEqual(cash_line.debit, Decimal("95.00"))
        self.assertEqual(cash_line.credit, Decimal("0.00"))
        self.assertEqual(
            principal_line.account.code,
            BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE,
        )
        self.assertEqual(principal_line.credit, Decimal("61.31"))
        self.assertEqual(principal_line.debit, Decimal("0.00"))
        self.assertEqual(
            interest_line.account.code,
            BHPH_INTEREST_INCOME_ACCOUNT_CODE,
        )
        self.assertEqual(interest_line.credit, Decimal("33.69"))
        self.assertEqual(interest_line.debit, Decimal("0.00"))

    def test_zero_interest_posts_two_line_entry(self) -> None:
        # Early payoff / principal-only payment.
        payment = _make_payment(
            self.dealership,
            self.note,
            amount=Decimal("500.00"),
            principal=Decimal("500.00"),
            interest=Decimal("0.00"),
        )
        post_bhph_payment_journal(
            dealership=self.dealership, bhph_payment=payment
        )
        entry = JournalEntry.objects.get()
        lines = list(entry.lines.order_by("id"))
        self.assertEqual(len(lines), 2)
        codes = {line.account.code for line in lines}
        self.assertEqual(
            codes,
            {CASH_ACCOUNT_CODE, BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE},
        )

    def test_zero_principal_posts_two_line_entry(self) -> None:
        # Interest-only payment (partial payment covering interest).
        payment = _make_payment(
            self.dealership,
            self.note,
            amount=Decimal("30.00"),
            principal=Decimal("0.00"),
            interest=Decimal("30.00"),
        )
        post_bhph_payment_journal(
            dealership=self.dealership, bhph_payment=payment
        )
        entry = JournalEntry.objects.get()
        lines = list(entry.lines.order_by("id"))
        self.assertEqual(len(lines), 2)
        codes = {line.account.code for line in lines}
        self.assertEqual(
            codes,
            {CASH_ACCOUNT_CODE, BHPH_INTEREST_INCOME_ACCOUNT_CODE},
        )

    def test_posted_at_denormalized_on_success(self) -> None:
        payment = _make_payment(self.dealership, self.note)
        self.assertIsNone(payment.posted_at)
        post_bhph_payment_journal(
            dealership=self.dealership, bhph_payment=payment
        )
        payment.refresh_from_db()
        self.assertIsNotNone(payment.posted_at)

    def test_entry_is_balanced_double_entry(self) -> None:
        payment = _make_payment(self.dealership, self.note)
        post_bhph_payment_journal(
            dealership=self.dealership, bhph_payment=payment
        )
        entry = JournalEntry.objects.get()
        debit_total = sum(
            (line.debit for line in entry.lines.all()),
            Decimal("0.00"),
        )
        credit_total = sum(
            (line.credit for line in entry.lines.all()),
            Decimal("0.00"),
        )
        self.assertEqual(debit_total, credit_total)
        self.assertEqual(debit_total, payment.amount)

    def test_description_carries_payment_and_note_pks(self) -> None:
        payment = _make_payment(
            self.dealership, self.note, method=BHPH_PAYMENT_METHOD_ACH
        )
        post_bhph_payment_journal(
            dealership=self.dealership, bhph_payment=payment
        )
        entry = JournalEntry.objects.get()
        self.assertIn(f"BhphPayment #{payment.pk}", entry.description)
        self.assertIn(f"note #{self.note.pk}", entry.description)
        # Method display name in description (from get_method_display).
        self.assertIn("ACH", entry.description)

    def test_posted_at_uses_supplied_timestamp(self) -> None:
        payment = _make_payment(self.dealership, self.note)
        chosen = timezone.now() - dt.timedelta(hours=3)
        post_bhph_payment_journal(
            dealership=self.dealership,
            bhph_payment=payment,
            posted_at=chosen,
        )
        payment.refresh_from_db()
        self.assertEqual(payment.posted_at, chosen)


# ---------------------------------------------------------------------------
# post_bhph_payment_journal — guards
# ---------------------------------------------------------------------------


class PostBhphPaymentJournalGuardsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m161-guards")
        self.other = make_dealership(slug="m161-guards-other")
        self.note = _make_note(self.dealership, "M161-G")
        self.other_note = _make_note(self.other, "M161-G-OTHER")

    def test_cross_tenant_payment_raises(self) -> None:
        payment = _make_payment(self.other, self.other_note)
        with self.assertRaises(CrossTenantGLAccountError):
            post_bhph_payment_journal(
                dealership=self.dealership, bhph_payment=payment
            )

    def test_missing_cash_account_raises(self) -> None:
        # Deactivate 100000 Cash on Hand so the lookup fails.
        GLAccount.objects.filter(
            dealership=self.dealership, code=CASH_ACCOUNT_CODE
        ).update(is_active=False)
        payment = _make_payment(self.dealership, self.note)
        with self.assertRaises(MissingDefaultAccountError):
            post_bhph_payment_journal(
                dealership=self.dealership, bhph_payment=payment
            )

    def test_missing_notes_receivable_raises_when_principal_nonzero(
        self,
    ) -> None:
        GLAccount.objects.filter(
            dealership=self.dealership,
            code=BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE,
        ).update(is_active=False)
        payment = _make_payment(self.dealership, self.note)
        with self.assertRaises(MissingDefaultAccountError):
            post_bhph_payment_journal(
                dealership=self.dealership, bhph_payment=payment
            )

    def test_missing_interest_account_raises_when_interest_nonzero(
        self,
    ) -> None:
        GLAccount.objects.filter(
            dealership=self.dealership,
            code=BHPH_INTEREST_INCOME_ACCOUNT_CODE,
        ).update(is_active=False)
        payment = _make_payment(self.dealership, self.note)
        with self.assertRaises(MissingDefaultAccountError):
            post_bhph_payment_journal(
                dealership=self.dealership, bhph_payment=payment
            )

    def test_nonzero_fees_raises_unexpected_fees_error(self) -> None:
        payment = _make_payment(
            self.dealership,
            self.note,
            amount=Decimal("100.00"),
            principal=Decimal("50.00"),
            interest=Decimal("40.00"),
            fees=Decimal("10.00"),
        )
        with self.assertRaises(UnexpectedBhphPaymentFeesError):
            post_bhph_payment_journal(
                dealership=self.dealership, bhph_payment=payment
            )

    def test_failed_post_does_not_denormalize_posted_at(self) -> None:
        # Missing account → post fails → posted_at stays None (atomic).
        GLAccount.objects.filter(
            dealership=self.dealership, code=CASH_ACCOUNT_CODE
        ).update(is_active=False)
        payment = _make_payment(self.dealership, self.note)
        with self.assertRaises(MissingDefaultAccountError):
            post_bhph_payment_journal(
                dealership=self.dealership, bhph_payment=payment
            )
        payment.refresh_from_db()
        self.assertIsNone(payment.posted_at)
        self.assertEqual(JournalEntry.objects.count(), 0)


# ---------------------------------------------------------------------------
# post_all_unposted_bhph_payments_for_dealership — orchestrator
# ---------------------------------------------------------------------------


class PostAllUnpostedBhphPaymentsOrchestratorTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m161-orch")
        self.note = _make_note(self.dealership, "M161-ORCH")

    def test_posts_all_unposted_rows(self) -> None:
        p1 = _make_payment(self.dealership, self.note)
        p2 = _make_payment(
            self.dealership,
            self.note,
            paid_at=timezone.now() + dt.timedelta(days=7),
        )
        result = post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(result["posted_count"], 2)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(set(result["posted_ids"]), {p1.pk, p2.pk})
        self.assertEqual(JournalEntry.objects.count(), 2)

    def test_summary_shape_matches_m132(self) -> None:
        _make_payment(self.dealership, self.note)
        result = post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(
            set(result.keys()),
            {
                "dealership_id",
                "dealership_slug",
                "as_of",
                "posted_count",
                "failed_count",
                "posted_ids",
                "failed_ids",
            },
        )
        self.assertEqual(result["dealership_id"], self.dealership.pk)
        self.assertEqual(
            result["dealership_slug"], self.dealership.slug
        )

    def test_per_row_failure_isolation(self) -> None:
        # p1 valid; p2 has non-zero fees so it raises; p3 valid.
        p1 = _make_payment(self.dealership, self.note)
        p2_bad = _make_payment(
            self.dealership,
            self.note,
            amount=Decimal("100.00"),
            principal=Decimal("60.00"),
            interest=Decimal("30.00"),
            fees=Decimal("10.00"),
            paid_at=timezone.now() + dt.timedelta(days=7),
        )
        p3 = _make_payment(
            self.dealership,
            self.note,
            paid_at=timezone.now() + dt.timedelta(days=14),
        )
        result = post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(result["posted_count"], 2)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["failed_ids"], [p2_bad.pk])
        self.assertEqual(set(result["posted_ids"]), {p1.pk, p3.pk})

    def test_idempotency_second_run_posts_nothing(self) -> None:
        _make_payment(self.dealership, self.note)
        first = post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(first["posted_count"], 1)
        second = post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(second["posted_count"], 0)
        self.assertEqual(second["failed_count"], 0)
        self.assertEqual(JournalEntry.objects.count(), 1)

    def test_zero_payments_returns_zero_summary(self) -> None:
        result = post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        self.assertEqual(result["posted_count"], 0)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(result["posted_ids"], [])


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------


class PostBhphPaymentTaskTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m161-task")
        self.note = _make_note(self.dealership, "M161-TASK")

    def test_per_tenant_task_name_matches_constant(self) -> None:
        self.assertEqual(
            POST_BHPH_PAYMENT_FOR_TENANT_TASK_NAME,
            "dealer_ai.services.accounting.tasks."
            "post_bhph_payment_journals_for_dealership",
        )

    def test_orchestrator_task_name_matches_constant(self) -> None:
        self.assertEqual(
            POST_BHPH_PAYMENT_FOR_ALL_TENANTS_TASK_NAME,
            "dealer_ai.services.accounting.tasks."
            "post_bhph_payment_journals_for_all_tenants",
        )

    def test_per_tenant_task_direct_call_posts(self) -> None:
        _make_payment(self.dealership, self.note)
        result = post_bhph_payment_journals_for_dealership(
            dealership_id=self.dealership.pk
        )
        self.assertEqual(result["posted_count"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertEqual(JournalEntry.objects.count(), 1)


class BhphPaymentOrchestratorDispatchTests(TestCase):
    def setUp(self) -> None:
        self.dealership_a = make_dealership(slug="m161-orch-dispatch-a")
        self.dealership_b = make_dealership(slug="m161-orch-dispatch-b")

    def test_orchestrator_dispatches_per_tenant(self) -> None:
        with patch(
            "dealer_ai.services.accounting.tasks."
            "post_bhph_payment_journals_for_dealership.delay"
        ) as delayed:
            result = post_bhph_payment_journals_for_all_tenants()
        self.assertGreaterEqual(result["dispatched_tenant_count"], 2)
        dispatched_ids = {
            call.kwargs["dealership_id"]
            for call in delayed.call_args_list
        }
        self.assertIn(self.dealership_a.pk, dispatched_ids)
        self.assertIn(self.dealership_b.pk, dispatched_ids)


# ---------------------------------------------------------------------------
# Beat schedule registration
# ---------------------------------------------------------------------------


class BhphPaymentBeatScheduleTests(TestCase):
    def test_11_00_slot_registered(self) -> None:
        from django.conf import settings

        schedule = settings.CELERY_BEAT_SCHEDULE
        self.assertIn(
            "accounting-bhph-payment-post-daily-11-00", schedule
        )
        entry = schedule["accounting-bhph-payment-post-daily-11-00"]
        self.assertEqual(
            entry["task"],
            POST_BHPH_PAYMENT_FOR_ALL_TENANTS_TASK_NAME,
        )
        self.assertIn(11, entry["schedule"].hour)
        self.assertIn(0, entry["schedule"].minute)

    def test_beat_schedule_has_at_least_ten_families(self) -> None:
        # >= per M9/M10/M11/M12 lesson-14 growth-only assertion posture.
        from django.conf import settings

        self.assertGreaterEqual(
            len(settings.CELERY_BEAT_SCHEDULE), 10
        )


# ---------------------------------------------------------------------------
# Trial-balance reflection
# ---------------------------------------------------------------------------


class TrialBalanceReflectsBhphPaymentsTests(TestCase):
    def setUp(self) -> None:
        self.dealership = make_dealership(slug="m161-tb")
        self.note = _make_note(self.dealership, "M161-TB")

    def test_trial_balance_shows_cash_and_interest_income_after_post(
        self,
    ) -> None:
        _make_payment(
            self.dealership,
            self.note,
            amount=Decimal("95.00"),
            principal=Decimal("61.31"),
            interest=Decimal("33.69"),
        )
        post_all_unposted_bhph_payments_for_dealership(
            dealership=self.dealership
        )
        snapshot = compute_trial_balance(dealership=self.dealership)
        by_code = {row.account_code: row for row in snapshot.rows}
        # 100000 DR side +95.00.
        self.assertEqual(
            by_code[CASH_ACCOUNT_CODE].debit_total, Decimal("95.00")
        )
        # 123000 CR side +61.31 (amortizes note receivable).
        self.assertEqual(
            by_code[BHPH_NOTES_RECEIVABLE_ACCOUNT_CODE].credit_total,
            Decimal("61.31"),
        )
        # 430000 CR side +33.69 (interest income recognition).
        self.assertEqual(
            by_code[BHPH_INTEREST_INCOME_ACCOUNT_CODE].credit_total,
            Decimal("33.69"),
        )
