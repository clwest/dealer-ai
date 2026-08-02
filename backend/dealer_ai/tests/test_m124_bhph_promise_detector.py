"""Milestone 12 · Increment 4 (SESSION_124) — broken-PTP detector tests."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from dealer_ai.models import (
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PROMISE_REASON_PAYCHECK,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    BHPH_PROMISE_STATE_PROMISED,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    BhphPromiseToPay,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_promises.tasks import (
    detect_broken_promises_for_all_tenants,
    detect_broken_promises_for_dealership,
)


def _make_note(dealership: Dealership, stock: str = "M124-DET") -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Versa",
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
        principal_financed=Decimal("8000.00"),
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=dt.date(2026, 9, 1),
    )


@override_settings(BHPH_PTP_BROKEN_GRACE_HOURS=24)
class DetectorForTenantTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m124-det", name="M124 Detector"
        )
        self.note = _make_note(self.dealership, stock="M124-DET-1")

    def _mk(
        self,
        *,
        promised_at,
        state=BHPH_PROMISE_STATE_PROMISED,
    ) -> BhphPromiseToPay:
        return BhphPromiseToPay.objects.create(
            dealership=self.dealership,
            note=self.note,
            promised_at=promised_at,
            promised_amount=Decimal("95.00"),
            promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
            state=state,
        )

    def test_transitions_stale_promised_to_broken(self) -> None:
        # 30 hours past promise, grace 24 → stale.
        promise = self._mk(
            promised_at=timezone.now() - dt.timedelta(hours=30)
        )
        result = detect_broken_promises_for_dealership(
            dealership_id=self.dealership.pk
        )
        promise.refresh_from_db()
        self.assertEqual(promise.state, BHPH_PROMISE_STATE_BROKEN)
        self.assertEqual(result["transitioned_count"], 1)
        self.assertIn(promise.pk, result["transitioned_ids"])

    def test_respects_grace_period(self) -> None:
        # 12 hours past promise, grace 24 → still within grace.
        promise = self._mk(
            promised_at=timezone.now() - dt.timedelta(hours=12)
        )
        result = detect_broken_promises_for_dealership(
            dealership_id=self.dealership.pk
        )
        promise.refresh_from_db()
        self.assertEqual(promise.state, BHPH_PROMISE_STATE_PROMISED)
        self.assertEqual(result["transitioned_count"], 0)

    def test_excludes_already_kept(self) -> None:
        promise = self._mk(
            promised_at=timezone.now() - dt.timedelta(hours=30),
            state=BHPH_PROMISE_STATE_KEPT,
        )
        detect_broken_promises_for_dealership(
            dealership_id=self.dealership.pk
        )
        promise.refresh_from_db()
        self.assertEqual(promise.state, BHPH_PROMISE_STATE_KEPT)

    def test_excludes_already_broken_idempotency(self) -> None:
        promise = self._mk(
            promised_at=timezone.now() - dt.timedelta(hours=30),
            state=BHPH_PROMISE_STATE_BROKEN,
        )
        result = detect_broken_promises_for_dealership(
            dealership_id=self.dealership.pk
        )
        self.assertEqual(result["transitioned_count"], 0)
        promise.refresh_from_db()
        self.assertEqual(promise.state, BHPH_PROMISE_STATE_BROKEN)


@override_settings(BHPH_PTP_BROKEN_GRACE_HOURS=24)
class DetectorOrchestratorTests(TestCase):
    def test_orchestrator_dispatches_per_tenant(self) -> None:
        d1 = Dealership.objects.create(slug="m124-orc-1", name="M124 Orc 1")
        d2 = Dealership.objects.create(slug="m124-orc-2", name="M124 Orc 2")
        for d, stock in ((d1, "M124-ORC-1"), (d2, "M124-ORC-2")):
            note = _make_note(d, stock=stock)
            BhphPromiseToPay.objects.create(
                dealership=d,
                note=note,
                promised_at=timezone.now() - dt.timedelta(hours=30),
                promised_amount=Decimal("95.00"),
                promised_reason=BHPH_PROMISE_REASON_PAYCHECK,
                state=BHPH_PROMISE_STATE_PROMISED,
            )
        result = detect_broken_promises_for_all_tenants()
        self.assertGreaterEqual(result["dispatched_tenant_count"], 2)
        for d in (d1, d2):
            transitioned = BhphPromiseToPay.objects.filter(
                dealership=d, state=BHPH_PROMISE_STATE_BROKEN
            ).count()
            self.assertEqual(transitioned, 1)
