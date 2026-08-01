"""Milestone 4 · Increment 1 — WorkOrder + WorkOrderFinding +
WorkOrderPart model tests.

These three models form one tightly-coupled domain surface (the work
order is the parent; findings + parts hang off it), so they are
tested together in one focused file rather than three artificially
split files (per SESSION_066 brief pushback on test organization).

Persistence-layer coverage only. State transitions, attach/detach
workflow rules, part-status transition logic, and ledger integration
all land at M4.2 → M4.4 per ``MILESTONE_4_PLANNING.md`` §7.

Locked invariants (WorkOrder):

- Status + venue enum vocabularies.
- Category reuses ``CONDITION_CATEGORY_CHOICES`` (12 values) — NOT
  duplicated.
- ``venue='outsourced'`` requires a Vendor (clean guard).
- Cross-tenant Vendor rejected.
- Cross-tenant Vehicle rejected.
- ``venue='in_house'`` accepts NULL vendor (does not silently
  require one).
- Decimal cost fields.
- Provenance actor + timestamp fields remain nullable at persistence.
- No state transitions in save() / clean().
- Dealership FK NOT NULL.

Locked invariants (WorkOrderFinding):

- Many-to-many both directions.
- Unique pair (work_order, finding).
- Multiple findings per WorkOrder.
- One Finding linkable across multiple WorkOrders.
- Mismatched Vehicle rejected (cross-vehicle links prohibited).
- Cross-tenant chains rejected.
- Cascade on both parents.

Locked invariants (WorkOrderPart):

- Source-type finalized 7-value vocabulary (incl. customer_supplied).
- Status vocabulary 6 values.
- Quantity >= 1 (MinValueValidator).
- Decimal unit_cost.
- Parent tenancy match.
- Per-state timestamps persist but are NOT auto-transitioned.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import (
    CONDITION_CATEGORY_BODY,
    CONDITION_CATEGORY_CHOICES,
    CONDITION_CATEGORY_MECHANICAL,
    CONDITION_CATEGORY_TIRES,
    CONDITION_SEVERITY_REQUIRED,
    ConditionFinding,
    ConditionReport,
    Dealership,
    Vehicle,
    VehicleCost,
    Vendor,
    WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED,
    WORK_ORDER_PART_SOURCE_IN_STOCK,
    WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
    WORK_ORDER_PART_SOURCE_OEM_DEALER,
    WORK_ORDER_PART_SOURCE_ONLINE,
    WORK_ORDER_PART_SOURCE_OTHER,
    WORK_ORDER_PART_SOURCE_SALVAGE,
    WORK_ORDER_PART_SOURCE_TYPE_CHOICES,
    WORK_ORDER_PART_STATUS_BACKORDERED,
    WORK_ORDER_PART_STATUS_CHOICES,
    WORK_ORDER_PART_STATUS_INSTALLED,
    WORK_ORDER_PART_STATUS_NEEDED,
    WORK_ORDER_PART_STATUS_ORDERED,
    WORK_ORDER_PART_STATUS_RECEIVED,
    WORK_ORDER_PART_STATUS_RETURNED,
    WORK_ORDER_STATUS_APPROVED,
    WORK_ORDER_STATUS_CANCELLED,
    WORK_ORDER_STATUS_CHOICES,
    WORK_ORDER_STATUS_COMPLETED,
    WORK_ORDER_STATUS_DRAFT,
    WORK_ORDER_STATUS_IN_PROGRESS,
    WORK_ORDER_VENUE_CHOICES,
    WORK_ORDER_VENUE_IN_HOUSE,
    WORK_ORDER_VENUE_OUTSOURCED,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)


def _make_vehicle(stock: str, dealership: Dealership) -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2024,
        model="F-150",
        price=Decimal("48000.00"),
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
    report: ConditionReport,
    dealership: Dealership,
    category: str = CONDITION_CATEGORY_MECHANICAL,
    description: str = "Finding for WO test.",
) -> ConditionFinding:
    return ConditionFinding.objects.create(
        report=report,
        dealership=dealership,
        category=category,
        severity=CONDITION_SEVERITY_REQUIRED,
        description=description,
    )


def _make_vendor(
    dealership: Dealership, slug: str = "test-vendor"
) -> Vendor:
    return Vendor.objects.create(
        dealership=dealership,
        name=f"Test Vendor {slug}",
        slug=slug,
    )


# ============================================================================
# WorkOrder — enum vocabulary + structural invariants
# ============================================================================


class WorkOrderStatusVocabulary(TestCase):
    """Five canonical status values per planning §5.c. Five, not six
    (waiting_parts + scheduled deliberately rejected — see planning
    §5.c "rejected additions")."""

    def test_choices_contain_exactly_five_canonical_statuses(self):
        keys = {key for key, _ in WORK_ORDER_STATUS_CHOICES}
        self.assertEqual(
            keys,
            {
                WORK_ORDER_STATUS_DRAFT,
                WORK_ORDER_STATUS_APPROVED,
                WORK_ORDER_STATUS_IN_PROGRESS,
                WORK_ORDER_STATUS_COMPLETED,
                WORK_ORDER_STATUS_CANCELLED,
            },
        )
        self.assertEqual(len(WORK_ORDER_STATUS_CHOICES), 5)


class WorkOrderVenueVocabulary(TestCase):
    """Two canonical venue values."""

    def test_choices_contain_exactly_two_canonical_venues(self):
        keys = {key for key, _ in WORK_ORDER_VENUE_CHOICES}
        self.assertEqual(
            keys,
            {WORK_ORDER_VENUE_IN_HOUSE, WORK_ORDER_VENUE_OUTSOURCED},
        )
        self.assertEqual(len(WORK_ORDER_VENUE_CHOICES), 2)


class WorkOrderCategoryReusesConditionVocabulary(TestCase):
    """The 12-value category vocabulary is imported from
    ``CONDITION_CATEGORY_CHOICES`` — NOT duplicated into a second
    independently-maintained tuple (SESSION_066 brief enum
    discipline)."""

    def test_workorder_category_field_uses_condition_category_choices(self):
        field = WorkOrder._meta.get_field("category")
        self.assertEqual(tuple(field.choices), tuple(CONDITION_CATEGORY_CHOICES))


class WorkOrderCreate(TestCase):
    """Happy-path field-shape smokes for both venues."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41WO-CREATE", self.default)
        self.vendor = _make_vendor(self.default, slug="create-vendor")

    def test_outsourced_round_trip(self):
        wo = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=self.vendor,
            estimated_cost=Decimal("850.00"),
            authorized_cost=Decimal("900.00"),
            notes="Rear quarter blend + clear coat.",
        )
        fetched = WorkOrder.objects.get(pk=wo.pk)
        self.assertEqual(fetched.venue, WORK_ORDER_VENUE_OUTSOURCED)
        self.assertEqual(fetched.vendor_id, self.vendor.pk)
        self.assertEqual(fetched.estimated_cost, Decimal("850.00"))
        self.assertEqual(fetched.authorized_cost, Decimal("900.00"))
        self.assertIsNone(fetched.actual_cost)
        self.assertEqual(fetched.status, WORK_ORDER_STATUS_DRAFT)
        # Provenance fields all null on a fresh draft.
        self.assertIsNone(fetched.approved_at)
        self.assertIsNone(fetched.approved_by)
        self.assertIsNone(fetched.started_at)
        self.assertIsNone(fetched.completed_at)
        self.assertIsNone(fetched.cancelled_at)

    def test_in_house_round_trip_without_vendor(self):
        wo = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        wo.full_clean()  # in-house may leave vendor NULL
        self.assertIsNone(wo.vendor)


class WorkOrderStatusFullCleanRejectsInvalid(TestCase):
    def test_invalid_status_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41WO-STAT", default)
        wo = WorkOrder(
            vehicle=vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
            status="waiting_parts",  # not in vocab
        )
        with self.assertRaises(ValidationError):
            wo.full_clean()


class WorkOrderOutsourcedRequiresVendor(TestCase):
    """Planning §1.3 + §5.c invariant: outsourced work has to go
    somewhere. Model-layer clean() guard prevents corruption."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41WO-OUT", self.default)

    def test_outsourced_without_vendor_rejected(self):
        wo = WorkOrder(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            wo.full_clean()
        self.assertIn("vendor", ctx.exception.message_dict)

    def test_outsourced_with_vendor_passes(self):
        vendor = _make_vendor(self.default, slug="out-vendor")
        wo = WorkOrder(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=vendor,
        )
        wo.full_clean()


class WorkOrderCrossTenantGuards(TestCase):
    """Two cross-tenant surfaces on WorkOrder: (1) dealership vs
    vehicle.dealership; (2) dealership vs vendor.dealership."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-wo"
        )
        self.vehicle_at_a = _make_vehicle("M41WO-XT-A", self.dealership_a)
        self.vendor_at_a = _make_vendor(self.dealership_a, slug="xt-vendor-a")
        self.vendor_at_b = _make_vendor(self.dealership_b, slug="xt-vendor-b")

    def test_mismatched_vehicle_dealership_rejected(self):
        wo = WorkOrder(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_b,  # wrong tenant
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        with self.assertRaises(ValidationError) as ctx:
            wo.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)

    def test_mismatched_vendor_dealership_rejected(self):
        wo = WorkOrder(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=self.vendor_at_b,  # cross-tenant vendor
        )
        with self.assertRaises(ValidationError) as ctx:
            wo.full_clean()
        self.assertIn("vendor", ctx.exception.message_dict)

    def test_matching_all_passes(self):
        wo = WorkOrder(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            category=CONDITION_CATEGORY_BODY,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=self.vendor_at_a,
        )
        wo.full_clean()


class WorkOrderDealershipRequired(TestCase):
    def test_dealership_field_is_not_null_at_schema_level(self):
        self.assertFalse(WorkOrder._meta.get_field("dealership").null)


class WorkOrderCascadeOnVehicleDelete(TestCase):
    """Vehicle deletion cascades to work orders (M2/M3 precedent)."""

    def test_delete_vehicle_removes_work_orders(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41WO-CASC", default)
        wo = WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        pk = wo.pk
        vehicle.delete()
        self.assertFalse(WorkOrder.objects.filter(pk=pk).exists())


class WorkOrderNoLedgerSideEffects(TestCase):
    """Creating a WorkOrder must NOT post to VehicleCost. Ledger
    integration lands in M4.3."""

    def test_creating_work_order_creates_no_vehicle_cost(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41WO-NOLEDGER", default)
        vendor = _make_vendor(default, slug="noledger-vendor")
        pre_cost = VehicleCost.objects.count()
        WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_OUTSOURCED,
            vendor=vendor,
            estimated_cost=Decimal("500.00"),
        )
        self.assertEqual(VehicleCost.objects.count(), pre_cost)


# ============================================================================
# WorkOrderFinding — through table
# ============================================================================


class WorkOrderFindingLink(TestCase):
    """Many-to-many both directions with unique-pair enforcement."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41WOF-LINK", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding_1 = _make_finding(
            self.report, self.default, description="Finding 1"
        )
        self.finding_2 = _make_finding(
            self.report, self.default, description="Finding 2"
        )
        self.wo_1 = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        self.wo_2 = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_multiple_findings_per_work_order(self):
        WorkOrderFinding.objects.create(
            work_order=self.wo_1,
            finding=self.finding_1,
            dealership=self.default,
        )
        WorkOrderFinding.objects.create(
            work_order=self.wo_1,
            finding=self.finding_2,
            dealership=self.default,
        )
        linked_findings = ConditionFinding.objects.filter(
            work_order_links__work_order=self.wo_1
        )
        self.assertEqual(linked_findings.count(), 2)

    def test_single_finding_across_multiple_work_orders(self):
        WorkOrderFinding.objects.create(
            work_order=self.wo_1,
            finding=self.finding_1,
            dealership=self.default,
        )
        WorkOrderFinding.objects.create(
            work_order=self.wo_2,
            finding=self.finding_1,
            dealership=self.default,
        )
        linked_wos = WorkOrder.objects.filter(
            finding_links__finding=self.finding_1
        )
        self.assertEqual(linked_wos.count(), 2)

    def test_duplicate_pair_raises_integrity_error(self):
        WorkOrderFinding.objects.create(
            work_order=self.wo_1,
            finding=self.finding_1,
            dealership=self.default,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                WorkOrderFinding.objects.create(
                    work_order=self.wo_1,
                    finding=self.finding_1,
                    dealership=self.default,
                )


class WorkOrderFindingCrossVehicleRejected(TestCase):
    """WO on Vehicle A cannot link to a Finding from a report on
    Vehicle B — even within the same dealership. Planning §1.4
    invariant."""

    def test_cross_vehicle_link_rejected(self):
        default = Dealership.objects.get(slug="default")
        vehicle_a = _make_vehicle("M41WOF-VA-A", default)
        vehicle_b = _make_vehicle("M41WOF-VA-B", default)
        report_b = _make_report(vehicle_b, default)
        finding_on_b = _make_finding(report_b, default)
        wo_on_a = WorkOrder.objects.create(
            vehicle=vehicle_a,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        link = WorkOrderFinding(
            work_order=wo_on_a,
            finding=finding_on_b,
            dealership=default,
        )
        with self.assertRaises(ValidationError) as ctx:
            link.full_clean()
        self.assertIn("finding", ctx.exception.message_dict)


class WorkOrderFindingCrossTenantChainsRejected(TestCase):
    """Cross-tenant chains via WorkOrder side and via Finding side
    both raise."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-wof"
        )
        self.vehicle_at_a = _make_vehicle("M41WOF-XT-A", self.dealership_a)
        self.report_at_a = _make_report(self.vehicle_at_a, self.dealership_a)
        self.finding_at_a = _make_finding(self.report_at_a, self.dealership_a)
        self.wo_at_a = WorkOrder.objects.create(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_link_dealership_mismatched_to_work_order_rejected(self):
        link = WorkOrderFinding(
            work_order=self.wo_at_a,
            finding=self.finding_at_a,
            dealership=self.dealership_b,  # cross-tenant on the link
        )
        with self.assertRaises(ValidationError) as ctx:
            link.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class WorkOrderFindingCascade(TestCase):
    """Cascade both ways — deletion of parent WO removes its links;
    deletion of parent Finding removes its links."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41WOF-CASC", self.default)
        self.report = _make_report(self.vehicle, self.default)
        self.finding = _make_finding(self.report, self.default)
        self.wo = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        self.link = WorkOrderFinding.objects.create(
            work_order=self.wo,
            finding=self.finding,
            dealership=self.default,
        )

    def test_delete_work_order_removes_link(self):
        pk = self.link.pk
        self.wo.delete()
        self.assertFalse(WorkOrderFinding.objects.filter(pk=pk).exists())

    def test_delete_finding_removes_link(self):
        pk = self.link.pk
        self.finding.delete()
        self.assertFalse(WorkOrderFinding.objects.filter(pk=pk).exists())


# ============================================================================
# WorkOrderPart
# ============================================================================


class WorkOrderPartStatusVocabulary(TestCase):
    """Six canonical part-status values per planning §1.5."""

    def test_choices_contain_exactly_six_canonical_statuses(self):
        keys = {key for key, _ in WORK_ORDER_PART_STATUS_CHOICES}
        self.assertEqual(
            keys,
            {
                WORK_ORDER_PART_STATUS_NEEDED,
                WORK_ORDER_PART_STATUS_ORDERED,
                WORK_ORDER_PART_STATUS_BACKORDERED,
                WORK_ORDER_PART_STATUS_RECEIVED,
                WORK_ORDER_PART_STATUS_INSTALLED,
                WORK_ORDER_PART_STATUS_RETURNED,
            },
        )
        self.assertEqual(len(WORK_ORDER_PART_STATUS_CHOICES), 6)


class WorkOrderPartSourceTypeVocabulary(TestCase):
    """Seven canonical source-type values per SESSION_066 finalization
    (adds ``customer_supplied`` — meaningfully distinct from
    ``in_stock`` because warranty + liability differ)."""

    def test_choices_contain_exactly_seven_canonical_sources(self):
        keys = {key for key, _ in WORK_ORDER_PART_SOURCE_TYPE_CHOICES}
        self.assertEqual(
            keys,
            {
                WORK_ORDER_PART_SOURCE_OEM_DEALER,
                WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
                WORK_ORDER_PART_SOURCE_ONLINE,
                WORK_ORDER_PART_SOURCE_SALVAGE,
                WORK_ORDER_PART_SOURCE_IN_STOCK,
                WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED,
                WORK_ORDER_PART_SOURCE_OTHER,
            },
        )
        self.assertEqual(len(WORK_ORDER_PART_SOURCE_TYPE_CHOICES), 7)

    def test_customer_supplied_present(self):
        # Explicit check — this is the SESSION_066 finalization.
        keys = {key for key, _ in WORK_ORDER_PART_SOURCE_TYPE_CHOICES}
        self.assertIn(WORK_ORDER_PART_SOURCE_CUSTOMER_SUPPLIED, keys)


class WorkOrderPartCreate(TestCase):
    """Happy-path field-shape smokes."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41WOP-CREATE", self.default)
        self.wo = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_TIRES,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_round_trip_all_fields(self):
        part = WorkOrderPart.objects.create(
            work_order=self.wo,
            dealership=self.default,
            name="Michelin Defender 265/70R17",
            part_number="MICH-265-70-17",
            description="LT-rated highway tire.",
            quantity=4,
            unit_cost=Decimal("189.99"),
            status=WORK_ORDER_PART_STATUS_ORDERED,
            source_type=WORK_ORDER_PART_SOURCE_LOCAL_PARTS,
            source_name="NAPA Yuma",
            ordered_at=timezone.now().date(),
            notes="ETA Friday.",
        )
        fetched = WorkOrderPart.objects.get(pk=part.pk)
        self.assertEqual(fetched.name, "Michelin Defender 265/70R17")
        self.assertEqual(fetched.quantity, 4)
        self.assertEqual(fetched.unit_cost, Decimal("189.99"))
        self.assertEqual(fetched.status, WORK_ORDER_PART_STATUS_ORDERED)
        self.assertEqual(fetched.source_type, WORK_ORDER_PART_SOURCE_LOCAL_PARTS)
        # Per-state timestamps: ordered_at set, others still null.
        self.assertIsNotNone(fetched.ordered_at)
        self.assertIsNone(fetched.received_at)
        self.assertIsNone(fetched.installed_at)
        self.assertIsNone(fetched.returned_at)

    def test_defaults(self):
        part = WorkOrderPart.objects.create(
            work_order=self.wo,
            dealership=self.default,
            name="Random bolt",
        )
        self.assertEqual(part.quantity, 1)
        self.assertEqual(part.status, WORK_ORDER_PART_STATUS_NEEDED)
        self.assertEqual(part.source_type, WORK_ORDER_PART_SOURCE_IN_STOCK)
        self.assertIsNone(part.unit_cost)


class WorkOrderPartQuantityMustBePositive(TestCase):
    """Planning §1.5 + brief invariant: quantity is positive.
    Enforced via MinValueValidator(1) surfaced by full_clean()."""

    def setUp(self):
        self.default = Dealership.objects.get(slug="default")
        self.vehicle = _make_vehicle("M41WOP-QTY", self.default)
        self.wo = WorkOrder.objects.create(
            vehicle=self.vehicle,
            dealership=self.default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_quantity_zero_rejected(self):
        part = WorkOrderPart(
            work_order=self.wo,
            dealership=self.default,
            name="Bad qty",
            quantity=0,
        )
        with self.assertRaises(ValidationError):
            part.full_clean()

    def test_quantity_one_passes(self):
        part = WorkOrderPart(
            work_order=self.wo,
            dealership=self.default,
            name="OK qty",
            quantity=1,
        )
        part.full_clean()


class WorkOrderPartCrossTenantGuard(TestCase):
    """Dealership must match the parent WorkOrder's tenant."""

    def setUp(self):
        self.dealership_a = Dealership.objects.get(slug="default")
        self.dealership_b = Dealership.objects.create(
            name="Rivertown Motors", slug="rivertown-wop"
        )
        self.vehicle_at_a = _make_vehicle("M41WOP-XT", self.dealership_a)
        self.wo_at_a = WorkOrder.objects.create(
            vehicle=self.vehicle_at_a,
            dealership=self.dealership_a,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )

    def test_mismatched_dealership_rejected(self):
        part = WorkOrderPart(
            work_order=self.wo_at_a,
            dealership=self.dealership_b,  # cross-tenant
            name="Cross-tenant part",
        )
        with self.assertRaises(ValidationError) as ctx:
            part.full_clean()
        self.assertIn("dealership", ctx.exception.message_dict)


class WorkOrderPartCascadeOnWorkOrderDelete(TestCase):
    def test_delete_work_order_removes_parts(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41WOP-CASC", default)
        wo = WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        part = WorkOrderPart.objects.create(
            work_order=wo,
            dealership=default,
            name="Test",
        )
        pk = part.pk
        wo.delete()
        self.assertFalse(WorkOrderPart.objects.filter(pk=pk).exists())


class WorkOrderPartTimestampsNotAutoTransitioned(TestCase):
    """Per-state timestamps persist as supplied but are NOT
    auto-populated by the model layer (that is M4.4 service work).
    A part can persist with an ``installed`` status but a null
    ``installed_at`` — the model layer accepts it, service layer
    will refuse it."""

    def test_status_installed_with_null_timestamp_persists(self):
        default = Dealership.objects.get(slug="default")
        vehicle = _make_vehicle("M41WOP-TS", default)
        wo = WorkOrder.objects.create(
            vehicle=vehicle,
            dealership=default,
            category=CONDITION_CATEGORY_MECHANICAL,
            venue=WORK_ORDER_VENUE_IN_HOUSE,
        )
        part = WorkOrderPart.objects.create(
            work_order=wo,
            dealership=default,
            name="Timestamp test",
            status=WORK_ORDER_PART_STATUS_INSTALLED,
            # installed_at deliberately NOT set — model layer
            # accepts; service will enforce.
        )
        fetched = WorkOrderPart.objects.get(pk=part.pk)
        self.assertEqual(fetched.status, WORK_ORDER_PART_STATUS_INSTALLED)
        self.assertIsNone(fetched.installed_at)
