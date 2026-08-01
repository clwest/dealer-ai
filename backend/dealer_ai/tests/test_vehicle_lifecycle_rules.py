"""Milestone 5 · Increment 3 (SESSION_077) — deterministic rule tests.

Coverage of the three rule evaluators added to
``dealer_ai/services/vehicle_lifecycle.py`` plus the updated
``suggest_transitions`` composition function.

Locked invariants (per SESSION_077 brief + planning §5.h
SESSION_075 refined):

Rule bodies:
- `_rule_inspection_to_recon`:
  - Fires when latest completed report has ≥1 finding at
    severity in {recommended, required, safety}.
  - Does NOT fire when there is no completed report.
  - Does NOT force recon when a completed report has only
    advisory-severity findings (or none).
  - Reads only M3 substrate; writes nothing.
- `_rule_recon_to_qc`:
  - Fires when zero open work orders remain AND every
    must_do decision is addressed by a completed WorkOrder.
  - Does NOT fire when at least one open WO remains.
  - Does NOT fire when a must_do decision has no completed
    WO coverage.
  - Does NOT fire when no completed condition report exists.
  - Fires when there are no must_do decisions and no open WOs.
- `_rule_photography_to_listing`:
  - ALWAYS returns a SuggestedTransition (never None).
  - Populates `unmet_prerequisites` with a truthful "M6 not
    shipped" note.
  - `to_stage` is `listing`; `rule_name` is
    `photography_to_listing`.

suggest_transitions composition:
- Returns [] when the vehicle has no stage row.
- Composes only the rule applicable to the current stage.
- Returns [] at stages with no applicable rule (incoming, qc,
  detail, listing, frontline, and every operational-disposition
  stage).
- inspection → inspection_to_recon (may be None).
- recon → recon_to_qc (may be None).
- photography → always the structured prerequisite.
- Cross-tenant refused.
- No `listing → frontline` rule ever fires (§5.h — manual-only
  in M5).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_REPORT_STATUS_COMPLETE,
    CONDITION_REPORT_STATUS_DRAFT,
    CONDITION_SEVERITY_ADVISORY,
    CONDITION_SEVERITY_RECOMMENDED,
    CONDITION_SEVERITY_REQUIRED,
    CONDITION_SEVERITY_SAFETY,
    ConditionFinding,
    ConditionReport,
    Dealership,
    RECON_DECISION_TIER_MUST_DO,
    RECON_DECISION_TIER_SHOULD_DO,
    ROLE_SALES_MANAGER,
    ReconDecision,
    UserDealershipRole,
    VEHICLE_STAGE_DETAIL,
    VEHICLE_STAGE_FRONTLINE,
    VEHICLE_STAGE_INCOMING,
    VEHICLE_STAGE_INSPECTION,
    VEHICLE_STAGE_LISTING,
    VEHICLE_STAGE_OFF_MARKET,
    VEHICLE_STAGE_PHOTOGRAPHY,
    VEHICLE_STAGE_QC,
    VEHICLE_STAGE_RECON,
    Vehicle,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_IN_HOUSE,
    WorkOrder,
    WorkOrderFinding,
)
from dealer_ai.services.vehicle_lifecycle import (
    CrossTenantLifecycleError,
    SuggestedTransition,
    _rule_inspection_to_recon,
    _rule_photography_to_listing,
    _rule_recon_to_qc,
    ensure_current_stage,
    suggest_transitions,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    v = Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="Escape",
        price=Decimal("22500.00"),
        dealership=dealership,
    )
    # M5.5 test-only auto-bootstrap; wipe so M5.3 rule tests
    # observe the specific stage state each test seeds.
    from ._tenancy_helpers import wipe_lifecycle_state
    return wipe_lifecycle_state(v)


def _make_report(
    vehicle: Vehicle,
    dealership: Dealership,
    *,
    status: str = CONDITION_REPORT_STATUS_COMPLETE,
) -> ConditionReport:
    kwargs = dict(
        vehicle=vehicle,
        dealership=dealership,
        inspector_name="M. Ruiz",
        inspected_at=timezone.now(),
        mileage_at_inspection=42_000,
        status=status,
    )
    if status == CONDITION_REPORT_STATUS_COMPLETE:
        kwargs["completed_at"] = timezone.now()
    return ConditionReport.objects.create(**kwargs)


def _make_finding(
    report: ConditionReport,
    dealership: Dealership,
    *,
    severity: str = CONDITION_SEVERITY_REQUIRED,
    description: str = "Finding for rule test.",
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        severity=severity,
        description=description,
    )


def _make_work_order(
    vehicle: Vehicle,
    dealership: Dealership,
    *,
    status: str = WORK_ORDER_STATUS_DRAFT,
) -> WorkOrder:
    return WorkOrder.objects.create(
        vehicle=vehicle,
        dealership=dealership,
        category=CONDITION_CATEGORY_MECHANICAL,
        venue=WORK_ORDER_VENUE_IN_HOUSE,
        status=status,
    )


def _link(wo: WorkOrder, finding: ConditionFinding, dealership: Dealership):
    return WorkOrderFinding.objects.create(
        work_order=wo, finding=finding, dealership=dealership
    )


def _make_actor(username: str, dealership: Dealership, role: str):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="pw12345678")
    UserDealershipRole.objects.create(
        user=user, dealership=dealership, role=role
    )
    return user


# ============================================================================
# _rule_inspection_to_recon
# ============================================================================


class RuleInspectionToReconFires(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M53-IR-FIRE", self.default)

    def test_fires_on_required_severity(self):
        report = _make_report(self.vehicle, self.default)
        _make_finding(report, self.default, severity=CONDITION_SEVERITY_REQUIRED)
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.to_stage, VEHICLE_STAGE_RECON)
        self.assertEqual(result.rule_name, "inspection_to_recon")

    def test_fires_on_safety_severity(self):
        report = _make_report(self.vehicle, self.default)
        _make_finding(report, self.default, severity=CONDITION_SEVERITY_SAFETY)
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNotNone(result)
        self.assertIn("safety", result.evidence)

    def test_fires_on_recommended_severity(self):
        report = _make_report(self.vehicle, self.default)
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_RECOMMENDED
        )
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNotNone(result)
        self.assertIn("recommended", result.evidence)

    def test_evidence_enumerates_actionable_finding_count(self):
        report = _make_report(self.vehicle, self.default)
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_REQUIRED
        )
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_SAFETY
        )
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_ADVISORY
        )
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNotNone(result)
        self.assertIn("2 actionable", result.evidence)


class RuleInspectionToReconRefuses(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M53-IR-NOFIRE", self.default)

    def test_no_completed_report_returns_none(self):
        # No report seeded at all.
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNone(result)

    def test_draft_report_returns_none(self):
        draft = _make_report(
            self.vehicle, self.default, status=CONDITION_REPORT_STATUS_DRAFT
        )
        _make_finding(
            draft, self.default, severity=CONDITION_SEVERITY_REQUIRED
        )
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNone(result)

    def test_completed_report_with_no_findings_returns_none(self):
        _make_report(self.vehicle, self.default)  # empty
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNone(result)

    def test_completed_report_with_only_advisory_findings_returns_none(self):
        """§5.h — completed report with no actionable findings must NOT
        be forced into recon."""
        report = _make_report(self.vehicle, self.default)
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_ADVISORY
        )
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_ADVISORY
        )
        result = _rule_inspection_to_recon(
            self.vehicle, dealership=self.default
        )
        self.assertIsNone(result)


class RuleInspectionToReconCrossTenant(TestCase):
    def test_cross_tenant_refused(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(name="Other", slug="other-ir")
        vehicle = _make_vehicle("M53-IR-XT", default)
        with self.assertRaises(CrossTenantLifecycleError):
            _rule_inspection_to_recon(vehicle, dealership=other)


# ============================================================================
# _rule_recon_to_qc
# ============================================================================


class RuleReconToQcFires(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M53-RQ-FIRE", self.default)
        self.report = _make_report(self.vehicle, self.default)

    def test_fires_when_no_must_do_and_no_open_wos(self):
        # No decisions, no work orders — technically ready for QC.
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNotNone(result)
        self.assertEqual(result.to_stage, VEHICLE_STAGE_QC)
        self.assertEqual(result.rule_name, "recon_to_qc")

    def test_fires_when_must_do_addressed_by_completed_wo(self):
        finding = _make_finding(self.report, self.default)
        ReconDecision.objects.create(
            finding=finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        wo = _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_COMPLETED
        )
        _link(wo, finding, self.default)
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNotNone(result)
        self.assertIn("must_do decision(s) covered", result.evidence)

    def test_fires_when_should_do_decision_without_wo(self):
        """A ``should_do`` (or ``wont_do``) decision does NOT block QC;
        only ``must_do`` requires completed coverage."""
        finding = _make_finding(self.report, self.default)
        ReconDecision.objects.create(
            finding=finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_SHOULD_DO,
            decided_at=timezone.now(),
        )
        # No work order at all — but the decision is should_do, so QC
        # is legitimately possible.
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNotNone(result)


class RuleReconToQcRefuses(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M53-RQ-NOFIRE", self.default)
        self.report = _make_report(self.vehicle, self.default)

    def test_open_draft_wo_blocks_qc(self):
        _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_DRAFT
        )
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNone(result)

    def test_open_approved_wo_blocks_qc(self):
        _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_APPROVED
        )
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNone(result)

    def test_open_in_progress_wo_blocks_qc(self):
        _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_IN_PROGRESS
        )
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNone(result)

    def test_completed_wo_alone_does_not_block(self):
        """A completed WO is NOT open; alone it doesn't block QC."""
        _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_COMPLETED
        )
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNotNone(result)

    def test_cancelled_wo_does_not_block(self):
        _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_CANCELLED
        )
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNotNone(result)

    def test_must_do_without_any_wo_blocks(self):
        """§5.h — must_do decision with no WO coverage blocks QC even
        when the WO queue is empty."""
        finding = _make_finding(self.report, self.default)
        ReconDecision.objects.create(
            finding=finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNone(result)

    def test_must_do_with_only_draft_wo_blocks(self):
        finding = _make_finding(self.report, self.default)
        ReconDecision.objects.create(
            finding=finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        draft_wo = _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_DRAFT
        )
        _link(draft_wo, finding, self.default)
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        # Blocked because (a) the draft WO is open AND (b) even if it
        # weren't, it's not COMPLETED.
        self.assertIsNone(result)

    def test_must_do_with_only_cancelled_wo_blocks(self):
        """A cancelled WO doesn't count as "must_do addressed" — the
        promised work never actually happened."""
        finding = _make_finding(self.report, self.default)
        ReconDecision.objects.create(
            finding=finding,
            dealership=self.default,
            tier=RECON_DECISION_TIER_MUST_DO,
            decided_at=timezone.now(),
        )
        cancelled_wo = _make_work_order(
            self.vehicle, self.default, status=WORK_ORDER_STATUS_CANCELLED
        )
        _link(cancelled_wo, finding, self.default)
        # No open WOs, but the must_do isn't covered by a completed WO.
        result = _rule_recon_to_qc(self.vehicle, dealership=self.default)
        self.assertIsNone(result)

    def test_no_completed_report_returns_none(self):
        vehicle = _make_vehicle("M53-RQ-NOREPORT", self.default)
        # No condition report at all — no basis to conclude recon is
        # done.
        result = _rule_recon_to_qc(vehicle, dealership=self.default)
        self.assertIsNone(result)


class RuleReconToQcCrossTenant(TestCase):
    def test_cross_tenant_refused(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(name="Other", slug="other-rq")
        vehicle = _make_vehicle("M53-RQ-XT", default)
        with self.assertRaises(CrossTenantLifecycleError):
            _rule_recon_to_qc(vehicle, dealership=other)


# ============================================================================
# _rule_photography_to_listing — always returns a structured prerequisite
# ============================================================================


class RulePhotographyToListingAlwaysReturnsPrerequisite(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M53-PL", self.default)

    def test_returns_suggested_transition_not_none(self):
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertIsInstance(result, SuggestedTransition)

    def test_target_is_listing(self):
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.to_stage, VEHICLE_STAGE_LISTING)

    def test_rule_name_is_photography_to_listing(self):
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertEqual(result.rule_name, "photography_to_listing")

    def test_unmet_prerequisites_populated(self):
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        self.assertGreater(len(result.unmet_prerequisites), 0)

    def test_prerequisite_mentions_m6(self):
        """Truthful language — the prerequisite cites the milestone
        that will provide the missing predicate."""
        result = _rule_photography_to_listing(
            self.vehicle, dealership=self.default
        )
        joined = " ".join(result.unmet_prerequisites)
        self.assertIn("M6", joined)


# ============================================================================
# suggest_transitions composition
# ============================================================================


class SuggestTransitionsCompositionByStage(TestCase):
    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.actor = _make_actor("st-compose", self.default, ROLE_SALES_MANAGER)

    def _seed(self, stock: str, initial: str) -> Vehicle:
        v = _make_vehicle(stock, self.default)
        ensure_current_stage(
            v, dealership=self.default, initial_stage=initial
        )
        return v

    def test_no_stage_row_returns_empty(self):
        v = _make_vehicle("M53-COMPOSE-NOSTAGE", self.default)
        # No ensure_current_stage — deliberately no stage row.
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_inspection_stage_composes_inspection_to_recon(self):
        v = self._seed("M53-COMPOSE-INSP-FIRE", VEHICLE_STAGE_INSPECTION)
        report = _make_report(v, self.default)
        _make_finding(
            report, self.default, severity=CONDITION_SEVERITY_REQUIRED
        )
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].to_stage, VEHICLE_STAGE_RECON)

    def test_inspection_stage_returns_empty_when_rule_refuses(self):
        v = self._seed("M53-COMPOSE-INSP-NOFIRE", VEHICLE_STAGE_INSPECTION)
        # No completed report — inspection_to_recon returns None.
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_recon_stage_composes_recon_to_qc(self):
        v = self._seed("M53-COMPOSE-RECON", VEHICLE_STAGE_RECON)
        # No open WOs, no must_do decisions, but a completed report
        # (otherwise recon_to_qc refuses).
        _make_report(v, self.default)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].to_stage, VEHICLE_STAGE_QC)

    def test_recon_stage_returns_empty_when_rule_refuses(self):
        v = self._seed("M53-COMPOSE-RECON-BLOCK", VEHICLE_STAGE_RECON)
        _make_work_order(
            v, self.default, status=WORK_ORDER_STATUS_IN_PROGRESS
        )
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_photography_stage_always_returns_prerequisite(self):
        v = self._seed("M53-COMPOSE-PHOTO", VEHICLE_STAGE_PHOTOGRAPHY)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].to_stage, VEHICLE_STAGE_LISTING)
        self.assertGreater(len(result[0].unmet_prerequisites), 0)

    def test_incoming_stage_returns_empty(self):
        v = self._seed("M53-COMPOSE-INC", VEHICLE_STAGE_INCOMING)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_qc_stage_returns_empty(self):
        v = self._seed("M53-COMPOSE-QC", VEHICLE_STAGE_QC)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_detail_stage_returns_empty(self):
        v = self._seed("M53-COMPOSE-DET", VEHICLE_STAGE_DETAIL)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_listing_stage_returns_empty(self):
        """§5.h — listing → frontline is manual-only in M5. No rule
        may ever fire at listing stage."""
        v = self._seed("M53-COMPOSE-LIST", VEHICLE_STAGE_LISTING)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_frontline_stage_returns_empty(self):
        v = self._seed("M53-COMPOSE-FRONT", VEHICLE_STAGE_FRONTLINE)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])

    def test_off_market_stage_returns_empty(self):
        v = self._seed("M53-COMPOSE-OFF", VEHICLE_STAGE_OFF_MARKET)
        result = suggest_transitions(v, dealership=self.default)
        self.assertEqual(result, [])


class SuggestTransitionsCrossTenant(TestCase):
    def test_cross_tenant_refused(self):
        default = Dealership.objects.get(slug="default")
        other = Dealership.objects.create(name="Other", slug="other-st")
        v = _make_vehicle("M53-COMPOSE-XT", default)
        with self.assertRaises(CrossTenantLifecycleError):
            suggest_transitions(v, dealership=other)


class NoListingToFrontlineRuleEverFires(TestCase):
    """§5.h SESSION_075 refined — no deterministic `listing →
    frontline` rule ships in M5. Locked so future edits don't
    silently add one."""

    def test_composition_at_listing_never_suggests_frontline(self):
        default = Dealership.objects.get(slug="default")
        v = _make_vehicle("M53-NORULE-LIST", default)
        ensure_current_stage(
            v, dealership=default, initial_stage=VEHICLE_STAGE_LISTING
        )
        # Set price > 0 (a plausible false trigger for a bad rule).
        v.price = Decimal("29999.00")
        v.save()
        result = suggest_transitions(v, dealership=default)
        for suggestion in result:
            self.assertNotEqual(
                suggestion.to_stage,
                VEHICLE_STAGE_FRONTLINE,
                "No M5 rule may suggest listing → frontline "
                "(§5.h — manual-only).",
            )
