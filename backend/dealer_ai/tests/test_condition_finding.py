"""Milestone 3 · Increment 1 — ConditionFinding model tests.

Persistence-layer coverage only. No service-layer semantics
(``add_finding`` gated on report status, ``update_finding`` /
``delete_finding`` refusal on completed reports) are tested here —
those land at M3.2. Same shape as ``test_vehicle_cost.py`` from
Milestone 2.

Locked invariants:

- Category vocabulary — twelve canonical values per RECON §2.1.
- Severity vocabulary — four canonical values per RECON §2.2.
- Dealership FK NOT NULL from day one.
- Cross-tenant ``clean`` guard (dealership must match parent
  vehicle's dealership via ``report.vehicle``).
- Cascade behavior — deleting the parent ConditionReport removes
  its findings.
- ``description`` is required (RECON §2.6 prohibits AI-authored
  findings).
- ``estimated_cost`` is documentation-only Decimal, nullable, and
  does not touch any VehicleCost path.
- Ordering (severity, category, created_at).
- ``__str__`` for Django admin display.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_ACCESSORIES,
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_CHOICES,
    CONDITION_CATEGORY_COSMETIC,
    CONDITION_CATEGORY_ELECTRICAL,
    CONDITION_CATEGORY_FLUIDS,
    CONDITION_CATEGORY_GLASS,
    CONDITION_CATEGORY_INTERIOR,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_MISSING,
    CONDITION_CATEGORY_OTHER,
    CONDITION_CATEGORY_SAFETY,
    CONDITION_CATEGORY_TIRES,
    CONDITION_SEVERITY_ADVISORY,
    CONDITION_SEVERITY_CHOICES,
    CONDITION_SEVERITY_RECOMMENDED,
    CONDITION_SEVERITY_REQUIRED,
    CONDITION_SEVERITY_SAFETY,
    ConditionFinding,
    ConditionReport,
    Dealership,
    Vehicle,
    VehicleCost,
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


class CategoryChoicesVocabulary(TestCase):
    """The twelve canonical categories are enumerated in
    ``MILESTONE_3_PLANNING.md`` §1.2 and sourced from RECON §2.1
    plus one ``other`` escape hatch. Any addition or rename requires
    a roadmap decision — this test forces that conversation."""

    def test_choices_contain_exactly_twelve_canonical_categories(self):
        keys = {key for key, _ in CONDITION_CATEGORY_CHOICES}
        self.assertEqual(
            keys,
            {
                CONDITION_CATEGORY_MECHANICAL,
                CONDITION_CATEGORY_COSMETIC,
                CONDITION_CATEGORY_BODY,
                CONDITION_CATEGORY_GLASS,
                CONDITION_CATEGORY_TIRES,
                CONDITION_CATEGORY_INTERIOR,
                CONDITION_CATEGORY_FLUIDS,
                CONDITION_CATEGORY_ELECTRICAL,
                CONDITION_CATEGORY_SAFETY,
                CONDITION_CATEGORY_ACCESSORIES,
                CONDITION_CATEGORY_MISSING,
                CONDITION_CATEGORY_OTHER,
            },
        )
        self.assertEqual(len(CONDITION_CATEGORY_CHOICES), 12)


class SeverityChoicesVocabulary(TestCase):
    """The four canonical severity levels are enumerated in escalation
    order per RECON §2.2."""

    def test_choices_contain_exactly_four_canonical_severities(self):
        keys = {key for key, _ in CONDITION_SEVERITY_CHOICES}
        self.assertEqual(
            keys,
            {
                CONDITION_SEVERITY_ADVISORY,
                CONDITION_SEVERITY_RECOMMENDED,
                CONDITION_SEVERITY_REQUIRED,
                CONDITION_SEVERITY_SAFETY,
            },
        )
        self.assertEqual(len(CONDITION_SEVERITY_CHOICES), 4)

    def test_escalation_order_preserved(self):
        # The tuple order encodes escalation direction (advisory →
        # safety); dashboards and the M3.7 UI depend on this ordering
        # to render severity ladders left-to-right.
        keys = [key for key, _ in CONDITION_SEVERITY_CHOICES]
        self.assertEqual(
            keys,
            [
                CONDITION_SEVERITY_ADVISORY,
                CONDITION_SEVERITY_RECOMMENDED,
                CONDITION_SEVERITY_REQUIRED,
                CONDITION_SEVERITY_SAFETY,
            ],
        )


class ConditionFindingCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31F-CREATE", self.default)
        self.report = _make_report(self.vehicle, self.default)

    def test_round_trip_all_fields(self):
        finding = ConditionFinding.objects.create(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="LR tire at 3/32nds; replacement required.",
            estimated_cost=Decimal("165.00"),
            notes="Michelin Defender in stock.",
        )
        fetched = ConditionFinding.objects.get(pk=finding.pk)
        self.assertEqual(fetched.report_id, self.report.pk)
        self.assertEqual(fetched.dealership_id, self.default.pk)
        self.assertEqual(fetched.category, CONDITION_CATEGORY_TIRES)
        self.assertEqual(fetched.severity, CONDITION_SEVERITY_REQUIRED)
        self.assertEqual(fetched.estimated_cost, Decimal("165.00"))
        self.assertEqual(fetched.notes, "Michelin Defender in stock.")

    def test_estimated_cost_is_optional(self):
        finding = ConditionFinding.objects.create(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_ACCESSORIES,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Second key fob not present at inspection.",
        )
        self.assertIsNone(finding.estimated_cost)

    def test_category_full_clean_rejects_invalid_choice(self):
        finding = ConditionFinding(
            report=self.report,
            dealership=self.default,
            category="engine",  # not a valid choice
            severity=CONDITION_SEVERITY_REQUIRED,
            description="test",
        )
        with self.assertRaises(ValidationError):
            finding.full_clean()

    def test_severity_full_clean_rejects_invalid_choice(self):
        finding = ConditionFinding(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity="urgent",  # not a valid choice
            description="test",
        )
        with self.assertRaises(ValidationError):
            finding.full_clean()

    def test_description_required(self):
        finding = ConditionFinding(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="",
        )
        # TextField with no blank=True default rejects the empty
        # string via full_clean(). RECON §2.6 prohibits AI-authored
        # findings; the human must write the description.
        with self.assertRaises(ValidationError):
            finding.full_clean()


class EstimatedCostDoesNotPostToVehicleCost(TestCase):
    """Guard against the M3.2/M3.6 mistake of accidentally posting an
    estimate to ``VehicleCost`` when a finding is created. The M3.1
    planning doc §1.2 design note is explicit: ``estimated_cost`` is
    documentation only in M3; M4 owns the findings → work order → cost
    flow. This test locks the invariant at the persistence layer so
    future service layers cannot silently regress it."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31F-COST", self.default)
        self.report = _make_report(self.vehicle, self.default)

    def test_creating_finding_with_estimated_cost_creates_no_vehicle_cost_row(self):
        pre_cost_count = VehicleCost.objects.count()
        ConditionFinding.objects.create(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_BODY,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="Rear quarter panel needs paint blend.",
            estimated_cost=Decimal("1200.00"),
        )
        self.assertEqual(VehicleCost.objects.count(), pre_cost_count)


class DealershipRequired(TestCase):
    """Dealership FK is NOT NULL from day one."""

    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(
            ConditionFinding._meta.get_field("dealership").null,
            "ConditionFinding.dealership should be NOT NULL from day one",
        )

    def test_omitting_report_raises(self):
        default = Dealership.objects.get(slug="default")
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                ConditionFinding.objects.create(
                    dealership=default,
                    category=CONDITION_CATEGORY_MECHANICAL,
                    severity=CONDITION_SEVERITY_REQUIRED,
                    description="Orphan finding.",
                )


class CrossTenantClean(TestCase):
    """The denormalized ``dealership`` FK on ConditionFinding must
    match the parent Vehicle's tenant (reached via
    ``report.vehicle``). ``clean()`` is the model-layer guard."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-finding"
        )
        self.vehicle_at_a = _make_vehicle("M31F-XTENANT", self.dealership_a)
        self.report_at_a = _make_report(self.vehicle_at_a, self.dealership_a)

    def test_matching_dealership_passes_clean(self):
        finding = ConditionFinding(
            report=self.report_at_a,
            dealership=self.dealership_a,
            category=CONDITION_CATEGORY_INTERIOR,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Dashboard has minor sun crack.",
        )
        finding.full_clean()

    def test_mismatched_dealership_raises_validation_error(self):
        finding = ConditionFinding(
            report=self.report_at_a,
            dealership=self.dealership_b,
            category=CONDITION_CATEGORY_INTERIOR,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Dashboard has minor sun crack.",
        )
        with self.assertRaises(ValidationError) as ctx:
            finding.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class CascadeOnReportDelete(TestCase):
    """Deleting a ConditionReport removes its findings. Deleting the
    parent Vehicle also removes the findings (through the report
    cascade)."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M31F-CASC", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = ConditionFinding.objects.create(
            report=self.report,
            dealership=self.default,
            category=CONDITION_CATEGORY_GLASS,
            severity=CONDITION_SEVERITY_RECOMMENDED,
            description="Windshield chip at driver line of sight.",
        )

    def test_delete_report_removes_findings(self):
        finding_pk = self.finding.pk
        self.report.delete()
        self.assertFalse(
            ConditionFinding.objects.filter(pk=finding_pk).exists()
        )

    def test_delete_vehicle_cascades_through_report(self):
        finding_pk = self.finding.pk
        self.vehicle.delete()
        self.assertFalse(
            ConditionFinding.objects.filter(pk=finding_pk).exists()
        )


class ReverseRelation(TestCase):
    """``report.findings`` is the reverse accessor the M3.2 service and
    M3.7 UI use to list findings under a report."""

    def test_report_dot_findings_lists_it(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M31F-REV", default)
        report = _make_report(vehicle, default)
        finding = ConditionFinding.objects.create(
            report=report,
            dealership=default,
            category=CONDITION_CATEGORY_FLUIDS,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Coolant slightly low; topped off.",
        )
        report = ConditionReport.objects.get(pk=report.pk)
        self.assertIn(finding, report.findings.all())


class OrderingContract(TestCase):
    """Default ordering is (severity, category, created_at) — the
    severity column ties the operator's default view to
    'advisory → safety' left-to-right."""

    def test_default_ordering_by_severity_then_category(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M31F-ORD", default)
        report = _make_report(vehicle, default)
        ConditionFinding.objects.create(
            report=report,
            dealership=default,
            category=CONDITION_CATEGORY_SAFETY,
            severity=CONDITION_SEVERITY_SAFETY,
            description="Airbag warning light illuminated.",
        )
        ConditionFinding.objects.create(
            report=report,
            dealership=default,
            category=CONDITION_CATEGORY_ELECTRICAL,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Passenger visor LED intermittent.",
        )
        ConditionFinding.objects.create(
            report=report,
            dealership=default,
            category=CONDITION_CATEGORY_TIRES,
            severity=CONDITION_SEVERITY_REQUIRED,
            description="LR tire at 3/32nds.",
        )
        severities = [f.severity for f in ConditionFinding.objects.all()]
        # Alphabetical ordering by severity string: advisory,
        # recommended, required, safety. Locks the tuple ordering used
        # by ``ordering = (severity, category, created_at)`` in the
        # Meta class.
        self.assertEqual(
            severities,
            [
                CONDITION_SEVERITY_ADVISORY,
                CONDITION_SEVERITY_REQUIRED,
                CONDITION_SEVERITY_SAFETY,
            ],
        )


class StringRepresentation(TestCase):
    """__str__ is what Django admin renders. Locks the shape."""

    def test_str_contains_severity_category_and_stock(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M31F-STR", default)
        report = _make_report(vehicle, default)
        finding = ConditionFinding.objects.create(
            report=report,
            dealership=default,
            category=CONDITION_CATEGORY_MISSING,
            severity=CONDITION_SEVERITY_ADVISORY,
            description="Owner's manual absent.",
        )
        as_string = str(finding)
        self.assertIn("Advisory", as_string)
        self.assertIn("Missing items", as_string)
        self.assertIn("M31F-STR", as_string)
