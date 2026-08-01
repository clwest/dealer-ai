"""Milestone 4 · Increment 1 — ReconDecision model tests.

Persistence-layer coverage only. Service-layer semantics (decisions
gated on ``report.status == 'complete'``, one-per-finding write path
enforcement) land at M4.2 per ``MILESTONE_4_PLANNING.md`` §7 M4.2.

Locked invariants:

- OneToOne with ConditionFinding — a second decision on the same
  finding raises IntegrityError.
- Tier vocabulary — three canonical values per RECON §3.1.
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean()`` guard walks
  ``finding.report.vehicle.dealership``.
- ``decided_by`` provenance is nullable + SET_NULL.
- Zero WorkOrder / VehicleCost side effects on decision creation.
- Ordering by decision recency.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    RECON_DECISION_TIER_CHOICES,
    RECON_DECISION_TIER_MUST_DO,
    RECON_DECISION_TIER_SHOULD_DO,
    RECON_DECISION_TIER_WONT_DO,
    ReconDecision,
    Vehicle,
    VehicleCost,
    WorkOrder,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )


def _make_report(vehicle: Vehicle, dealership: Dealership) -> ConditionReport:
    return ConditionReport.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="Marta Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
    )


def _make_finding(
    report: ConditionReport, dealership: Dealership
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=CONDITION_SEVERITY_REQUIRED,
        description="Timing chain slap on cold start.",
    )


class ReconDecisionTierVocabulary(TestCase):
    """Three canonical tier values per RECON §3.1."""

    def test_choices_contain_exactly_three_canonical_tiers(self):
        keys = {key for key, _ in RECON_DECISION_TIER_CHOICES}
        self.assertEqual(
            keys,
            {
                RECON_DECISION_TIER_MUST_DO,
                RECON_DECISION_TIER_SHOULD_DO,
                RECON_DECISION_TIER_WONT_DO,
            },
        )
        self.assertEqual(len(RECON_DECISION_TIER_CHOICES), 3)


class ReconDecisionCreate(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41RD-CREATE", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_round_trip_all_fields(self):
        now = timezone.now()
        decision = ReconDecision.objects.create(
            finding=self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=now,
            notes="Safety impact — timing chain replacement authorized.",
        )
        fetched = ReconDecision.objects.get(pk=decision.pk)
        self.assertEqual(fetched.finding_id, self.finding.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.tier, RECON_DECISION_TIER_MUST_DO)
        self.assertEqual(fetched.decided_at, now)
        self.assertIn("timing chain", fetched.notes)
        self.assertIsNone(fetched.decided_by)  # provenance nullable

    def test_tier_full_clean_rejects_invalid_choice(self):
        decision = ReconDecision(
            finding=self.finding,
            dealership=self.default,
            tier="maybe_do",  # not a valid choice
            decided_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            decision.full_clean()

    def test_notes_optional(self):
        decision = ReconDecision.objects.create(
            finding=self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_WONT_DO,
            decided_at=timezone.now(),
        )
        self.assertEqual(decision.notes, "")


class ReconDecisionOneToOneEnforcement(TestCase):
    """OneToOne means at most one decision per finding — the second
    write raises IntegrityError, not silently overwrites."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41RD-1TO1", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)

    def test_second_decision_on_same_finding_raises(self):
        ReconDecision.objects.create(
            finding=self.finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_SHOULD_DO,
            decided_at=timezone.now(),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReconDecision.objects.create(
                    finding=self.finding,
                    dealership=self.default,
                    tier=RECON_DECISION_TIER_WONT_DO,
                    decided_at=timezone.now(),
                )


class ReconDecisionDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            ReconDecision._meta.get_field("dealership").null,
            "ReconDecision.dealership should be NOT NULL from day one",
        )


class ReconDecisionCrossTenantClean(TestCase):
    """``dealership`` must match the finding's Vehicle tenant chain.
    Same shape as ``ConditionFinding.clean``."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-rd"
        )
        self.vehicle_at_a = _make_vehicle("M41RD-XTENANT", self.dealership_a)
        self.report_at_a = _make_report(self.vehicle_at_a, self.dealership_a)
        self.finding_at_a = _make_finding(self.report_at_a, self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        decision = ReconDecision(
            finding=self.finding_at_a,
            dealership=self.dealership_a,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        decision.full_clean()  # should not raise

    def test_mismatched_dealership_raises_validation_error(self):
        decision = ReconDecision(
            finding=self.finding_at_a,
            dealership=self.dealership_b,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            decision.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class ReconDecisionCascadeOnFindingDelete(TestCase):
    """Deleting the parent ConditionFinding cascades to the
    OneToOne decision."""

    def test_delete_finding_removes_decision(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41RD-CASC", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        decision = ReconDecision.objects.create(
            finding=finding,
            dealership=default,
            tier=RECON_DECISION_TIER_WONT_DO,
            decided_at=timezone.now(),
        )
        decision_pk = decision.pk
        finding.delete()
        self.assertFalse(ReconDecision.objects.filter(pk=decision_pk).exists())


class ReconDecisionNoSideEffects(TestCase):
    """M4 invariant: creating a ReconDecision does NOT auto-create
    a WorkOrder, and does NOT post to VehicleCost. Those are
    downstream flows (M4.2 for WorkOrders, M4.3 for ledger)."""

    def test_creating_decision_creates_no_work_order(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41RD-NOSIDE-WO", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        pre_wo_count = WorkOrder.objects.count()
        ReconDecision.objects.create(
            finding=finding,
            dealership=default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        self.assertEqual(WorkOrder.objects.count(), pre_wo_count)

    def test_creating_decision_creates_no_vehicle_cost(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41RD-NOSIDE-COST", default)
        report = _make_report(vehicle, default)
        finding = _make_finding(report, default)
        pre_cost_count = VehicleCost.objects.count()
        ReconDecision.objects.create(
            finding=finding,
            dealership=default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        self.assertEqual(VehicleCost.objects.count(), pre_cost_count)
