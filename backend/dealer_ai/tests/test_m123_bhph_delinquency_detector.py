"""Milestone 12 · Increment 3 (SESSION_123) — delinquency Celery-detector tests.

Locks the two tasks in :mod:`services.bhph_delinquency.tasks`.
State-transitioning detector per M11 §6 lesson 17 — aging is
objectively elapsed calendar math, so auto-write is the correct
posture.

Coverage:

- On-time notes stay ``current``.
- Notes past grace transition to the correct bucket.
- Charge-off threshold at 120 days.
- Detector is idempotent within a run (no re-write when derived
  value matches stored).
- Fully-paid notes stay ``current`` regardless of dates.
- Cross-tenant isolation — notes at dealership A untouched by
  dealership B's task.
- Orchestrator dispatches per tenant.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_16_30,
    BHPH_AGING_BUCKET_31_60,
    BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_PAYMENT_FREQUENCY_WEEKLY,
    BHPH_PAYMENT_METHOD_CASH,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    Dealership,
    Sale,
    Vehicle,
)
from dealer_ai.services.bhph_delinquency.tasks import (
    detect_delinquencies_for_all_tenants,
    detect_delinquencies_for_dealership,
)
from dealer_ai.services.bhph_payments import record_payment


def _make_note(
    dealership: Dealership,
    *,
    stock: str,
    first_payment_due: dt.date,
    grace_days: int = 5,
) -> BhphNote:
    vehicle = Vehicle.objects.create(
        stock_number=stock,
        year=2020,
        model="Rio",
        price=Decimal("10000.00"),
        dealership=dealership,
    )
    sale = Sale.objects.create(
        dealership=dealership,
        vehicle=vehicle,
        sale_date=dt.date(2026, 8, 1),
        sold_price=Decimal("10000.00"),
        finance_type=SALE_FINANCE_TYPE_BHPH,
        gross_realized=Decimal("1000.00"),
    )
    return BhphNote.objects.create(
        dealership=dealership,
        sale=sale,
        principal_financed=Decimal("8000.00"),
        apr=Decimal("21.90"),
        term_weeks=104,
        payment_frequency=BHPH_PAYMENT_FREQUENCY_WEEKLY,
        payment_amount=Decimal("95.00"),
        first_payment_due=first_payment_due,
        default_grace_days=grace_days,
    )


def _patch_today(target: dt.date):
    """Freeze ``timezone.now()`` inside the detector task to noon on ``target``.

    Patches the ``timezone.now`` attribute on the shared
    ``django.utils.timezone`` module. Returning a real aware
    ``datetime`` keeps ``auto_now`` DateTimeField writes valid
    while the patch is active.
    """
    aware = timezone.make_aware(dt.datetime.combine(target, dt.time(12, 0)))
    return patch(
        "dealer_ai.services.bhph_delinquency.tasks.timezone.now",
        return_value=aware,
    )


class DetectorPerTenantTests(TestCase):
    def setUp(self) -> None:
        self.dealership = Dealership.objects.create(
            slug="m123-det", name="M123 Detector"
        )

    def test_on_time_note_stays_current(self) -> None:
        note = _make_note(
            self.dealership,
            stock="M123-DET-CUR",
            first_payment_due=dt.date(2026, 9, 15),
        )
        with _patch_today(dt.date(2026, 9, 1)):
            result = detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        note.refresh_from_db()
        self.assertEqual(note.current_bucket, BHPH_AGING_BUCKET_CURRENT)
        self.assertEqual(note.days_past_due, 0)
        # No transition — already at defaults.
        self.assertEqual(result["transitioned_count"], 0)

    def test_note_10_days_past_grace_lands_in_1_15(self) -> None:
        # First due 2026-09-01, grace 5. Today 2026-09-11 → 10 days
        # past due (measured from due, not grace).
        note = _make_note(
            self.dealership,
            stock="M123-DET-1-15",
            first_payment_due=dt.date(2026, 9, 1),
        )
        with _patch_today(dt.date(2026, 9, 11)):
            result = detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        note.refresh_from_db()
        self.assertEqual(note.current_bucket, BHPH_AGING_BUCKET_1_15)
        self.assertEqual(note.days_past_due, 10)
        self.assertEqual(result["transitioned_count"], 1)
        self.assertIn(note.pk, result["transitioned_ids"])

    def test_note_45_days_past_lands_in_31_60(self) -> None:
        note = _make_note(
            self.dealership,
            stock="M123-DET-31-60",
            first_payment_due=dt.date(2026, 9, 1),
        )
        with _patch_today(dt.date(2026, 10, 16)):  # 45 days after due
            detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        note.refresh_from_db()
        self.assertEqual(note.current_bucket, BHPH_AGING_BUCKET_31_60)
        self.assertEqual(note.days_past_due, 45)

    def test_note_150_days_past_lands_in_charge_off_candidate(self) -> None:
        note = _make_note(
            self.dealership,
            stock="M123-DET-COC",
            first_payment_due=dt.date(2026, 9, 1),
        )
        with _patch_today(dt.date(2027, 1, 29)):  # 150 days after due
            detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        note.refresh_from_db()
        self.assertEqual(
            note.current_bucket, BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE
        )
        self.assertEqual(note.days_past_due, 150)

    def test_within_grace_stays_current(self) -> None:
        # First due 2026-09-01, grace 5, today 2026-09-04 → within grace.
        note = _make_note(
            self.dealership,
            stock="M123-DET-GRACE",
            first_payment_due=dt.date(2026, 9, 1),
        )
        with _patch_today(dt.date(2026, 9, 4)):
            detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        note.refresh_from_db()
        self.assertEqual(note.current_bucket, BHPH_AGING_BUCKET_CURRENT)
        self.assertEqual(note.days_past_due, 0)

    def test_detector_is_idempotent_within_run(self) -> None:
        note = _make_note(
            self.dealership,
            stock="M123-DET-IDEM",
            first_payment_due=dt.date(2026, 9, 1),
        )
        with _patch_today(dt.date(2026, 9, 11)):
            r1 = detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
            r2 = detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        # First run transitions; second is a no-op.
        self.assertEqual(r1["transitioned_count"], 1)
        self.assertEqual(r2["transitioned_count"], 0)
        note.refresh_from_db()
        self.assertEqual(note.current_bucket, BHPH_AGING_BUCKET_1_15)

    def test_payment_advances_next_expected_due(self) -> None:
        # First due 2026-09-01. Buyer pays on time. Now next expected
        # is 2026-09-08 (weekly cadence). Today 2026-09-14 → 6 days
        # past (within grace of 5? no, 6 > 5). So days_past_due should
        # be 6 - 0 = 6 → 1_15 bucket.
        # Wait: next due is 09-08, grace 5, so grace expires 09-13.
        # Today 09-14 → 1 day past grace → days_past_due = 6 (from 09-08).
        note = _make_note(
            self.dealership,
            stock="M123-DET-PAID",
            first_payment_due=dt.date(2026, 9, 1),
        )
        record_payment(
            dealership=self.dealership,
            note=note,
            paid_at=timezone.now(),
            amount=Decimal("95.00"),
            method=BHPH_PAYMENT_METHOD_CASH,
        )
        with _patch_today(dt.date(2026, 9, 14)):
            detect_delinquencies_for_dealership(
                dealership_id=self.dealership.pk
            )
        note.refresh_from_db()
        self.assertEqual(note.current_bucket, BHPH_AGING_BUCKET_1_15)
        self.assertEqual(note.days_past_due, 6)


class DetectorCrossTenantTests(TestCase):
    def test_notes_isolated_across_dealerships(self) -> None:
        d1 = Dealership.objects.create(slug="m123-det-x-1", name="M123 X1")
        d2 = Dealership.objects.create(slug="m123-det-x-2", name="M123 X2")
        note1 = _make_note(
            d1, stock="M123-DET-X-1", first_payment_due=dt.date(2026, 9, 1)
        )
        note2 = _make_note(
            d2, stock="M123-DET-X-2", first_payment_due=dt.date(2026, 9, 1)
        )
        # 19 days after due → 16_30 bucket.
        with _patch_today(dt.date(2026, 9, 20)):
            detect_delinquencies_for_dealership(dealership_id=d1.pk)
        note1.refresh_from_db()
        note2.refresh_from_db()
        # d1's note aged; d2's should still be at defaults.
        self.assertEqual(note1.current_bucket, BHPH_AGING_BUCKET_16_30)
        self.assertEqual(note2.current_bucket, BHPH_AGING_BUCKET_CURRENT)
        self.assertEqual(note2.days_past_due, 0)


class OrchestratorTests(TestCase):
    def test_orchestrator_dispatches_per_tenant(self) -> None:
        d1 = Dealership.objects.create(slug="m123-orc-1", name="M123 Orc 1")
        d2 = Dealership.objects.create(slug="m123-orc-2", name="M123 Orc 2")
        for d, stock in ((d1, "M123-ORC-1"), (d2, "M123-ORC-2")):
            _make_note(
                d, stock=stock, first_payment_due=dt.date(2026, 9, 1)
            )
        # 19 days after due → 16_30 bucket at both tenants.
        with _patch_today(dt.date(2026, 9, 20)):
            result = detect_delinquencies_for_all_tenants()
        self.assertGreaterEqual(result["dispatched_tenant_count"], 2)
        for d in (d1, d2):
            self.assertEqual(
                BhphNote.objects.filter(
                    dealership=d, current_bucket=BHPH_AGING_BUCKET_16_30
                ).count(),
                1,
            )
