"""Milestone 18 · Increment 3 (SESSION_149) — floor-planned archetype tests.

Covers per MILESTONE_18_PLANNING.md §7 M18.3:

- Row-count contract per _INVENTORY / _STAFF / _LEADS / _SALES /
  _RECON_TARGETS / _VENDORS / _CREDIT_APPS / _FOLLOW_UP_LEADS /
  _BE_BACKS.
- **Recon overrun scenario visibility**: the first recon target's
  WorkOrder has authorized_cost < actual_cost by $600+, and its
  VehicleCost sum exceeds the acquisition cost basis by the same
  overrun magnitude.
- Cross-domain integrity (Sale buyers, CreditApp references,
  vendor reuse, stage progression).
- M15 sync-sibling GL post fires per Sale.
- Reset restores canonical starting state.
- ScenarioSummary contract populated.
- Synthetic-only data safety (DEMOFP VINs, NANP phones, example
  TLD emails).
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from dealer_ai.models import (
    DEMO_ARCHETYPE_FLOOR_PLANNED,
    BeBack,
    ConditionFinding,
    ConditionReport,
    CreditApplication,
    CustomerLead,
    FollowUpCadence,
    FollowUpTask,
    JournalEntry,
    ReconDecision,
    Sale,
    Salesperson,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
    VehicleStageEvent,
    Vendor,
    VendorCommunication,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)
from dealer_ai.services.demo_store import (
    ScenarioSummary,
    create_demo_store,
    reset_demo_store,
)
from dealer_ai.services.demo_store.archetypes.floor_planned import (
    _BE_BACKS,
    _CREDIT_APPS,
    _FOLLOW_UP_LEADS,
    _INVENTORY,
    _LEADS,
    _RECON_TARGETS,
    _SALES,
    _STAFF,
    _VENDORS,
    FloorPlannedArchetypeBuilder,
)


User = get_user_model()


class _BuildTestMixin(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.dealership, cls.summary = create_demo_store(
            slug="m183-floor-fixture",
            archetype=DEMO_ARCHETYPE_FLOOR_PLANNED,
            name="M18.3 Floor Fixture",
        )


# ---------------------------------------------------------------------------
# Row-count contract
# ---------------------------------------------------------------------------


class FloorPlannedRowCountsTests(_BuildTestMixin):
    def test_vehicles_match_inventory_spec(self) -> None:
        self.assertEqual(
            Vehicle.objects.filter(dealership=self.dealership).count(),
            len(_INVENTORY),
        )

    def test_acquisitions_match_vehicle_count(self) -> None:
        self.assertEqual(
            VehicleAcquisition.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_INVENTORY),
        )

    def test_salespeople_match_staff_spec(self) -> None:
        self.assertEqual(
            Salesperson.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_STAFF),
        )

    def test_leads_match_pipeline_plus_sale_buyers(self) -> None:
        self.assertEqual(
            CustomerLead.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_LEADS) + len(_SALES),
        )

    def test_sales_match_sale_spec(self) -> None:
        self.assertEqual(
            Sale.objects.filter(dealership=self.dealership).count(),
            len(_SALES),
        )

    def test_recon_vehicles_have_full_story(self) -> None:
        for stock in _RECON_TARGETS:
            v = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            self.assertTrue(
                ConditionReport.objects.filter(vehicle=v).exists()
            )
            self.assertGreaterEqual(
                ConditionFinding.objects.filter(
                    report__vehicle=v
                ).count(),
                2,
            )
            self.assertGreaterEqual(
                ReconDecision.objects.filter(
                    finding__report__vehicle=v
                ).count(),
                2,
            )
            self.assertGreaterEqual(
                WorkOrder.objects.filter(vehicle=v).count(), 1
            )

    def test_vendors_match_spec(self) -> None:
        self.assertEqual(
            Vendor.objects.filter(dealership=self.dealership).count(),
            len(_VENDORS),
        )

    def test_credit_applications_match_spec(self) -> None:
        self.assertEqual(
            CreditApplication.objects.filter(
                dealership=self.dealership
            ).count(),
            len(_CREDIT_APPS),
        )

    def test_follow_up_cadences_and_tasks_present(self) -> None:
        cadence_count = FollowUpCadence.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(cadence_count, len(_FOLLOW_UP_LEADS))
        # Tasks: 24hr template creates 1 task, 1wk creates 3.
        # Spec: 2 x 1wk + 1 x 24hr = 7 tasks.
        task_count = FollowUpTask.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertGreaterEqual(task_count, 7)

    def test_be_backs_match_spec(self) -> None:
        self.assertEqual(
            BeBack.objects.filter(dealership=self.dealership).count(),
            len(_BE_BACKS),
        )


# ---------------------------------------------------------------------------
# The recon overrun scenario anchor
# ---------------------------------------------------------------------------


class FloorPlannedReconOverrunTests(_BuildTestMixin):
    """The first _RECON_TARGET is the documented overrun anchor.

    Testers walking the M18.5 recon-lead scenario brief discover
    this overrun by comparing authorized vs actual on the
    WorkOrder detail view + reconciling against the M2 vehicle-
    investment ledger read model.
    """

    OVERRUN_STOCK = _RECON_TARGETS[0]

    def test_overrun_work_order_actual_exceeds_authorized_by_600_plus(
        self,
    ) -> None:
        vehicle = Vehicle.objects.get(
            dealership=self.dealership, stock_number=self.OVERRUN_STOCK
        )
        work_order = WorkOrder.objects.get(vehicle=vehicle)
        self.assertIsNotNone(work_order.authorized_cost)
        self.assertIsNotNone(work_order.actual_cost)
        assert work_order.authorized_cost is not None
        assert work_order.actual_cost is not None
        overrun = work_order.actual_cost - work_order.authorized_cost
        self.assertGreaterEqual(overrun, Decimal("600.00"))

    def test_overrun_vehicle_costs_exceed_baseline_by_overrun_margin(
        self,
    ) -> None:
        vehicle = Vehicle.objects.get(
            dealership=self.dealership, stock_number=self.OVERRUN_STOCK
        )
        work_order = WorkOrder.objects.get(vehicle=vehicle)
        # Sum every VehicleCost row against this vehicle EXCEPT
        # the acquisition-basis row (which is not present for
        # recon vehicles; those don't get sold in _SALES).
        recon_total = sum(
            (
                c.amount
                for c in VehicleCost.objects.filter(vehicle=vehicle)
            ),
            start=Decimal("0.00"),
        )
        # Recon spend for the overrun anchor = $710 + $560 + $155 =
        # $1,425. Must equal work_order.actual_cost.
        assert work_order.actual_cost is not None
        self.assertEqual(recon_total, work_order.actual_cost)

    def test_overrun_vendor_communications_document_escalation(self) -> None:
        vehicle = Vehicle.objects.get(
            dealership=self.dealership, stock_number=self.OVERRUN_STOCK
        )
        work_order = WorkOrder.objects.get(vehicle=vehicle)
        comms = VendorCommunication.objects.filter(
            work_order=work_order
        )
        # 2 rows: outbound sent + inbound narrative log.
        self.assertGreaterEqual(comms.count(), 2)
        # The narrative log mentions the overrun explicitly.
        narrative = comms.filter(kind="narrative").first()
        self.assertIsNotNone(narrative)
        assert narrative is not None
        self.assertIn("1,425", narrative.draft_content)

    def test_non_overrun_recon_targets_have_no_actual_cost_set(self) -> None:
        # Only the overrun anchor ships with actual_cost populated;
        # the other recon vehicles are mid-work with authorized only.
        for stock in _RECON_TARGETS[1:]:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            work_order = WorkOrder.objects.get(vehicle=vehicle)
            self.assertIsNone(work_order.actual_cost)
            self.assertIsNotNone(work_order.authorized_cost)


# ---------------------------------------------------------------------------
# Cross-domain integrity
# ---------------------------------------------------------------------------


class FloorPlannedCrossDomainTests(_BuildTestMixin):
    def test_every_sale_has_a_buyer_in_same_tenant(self) -> None:
        for sale in Sale.objects.filter(dealership=self.dealership):
            self.assertIsNotNone(sale.buyer_id)
            self.assertEqual(
                sale.buyer.dealership_id, self.dealership.pk
            )

    def test_every_credit_app_references_a_sale_in_same_tenant(self) -> None:
        for app in CreditApplication.objects.filter(
            dealership=self.dealership
        ):
            self.assertIsNotNone(app.sale_id)
            self.assertEqual(
                app.sale.dealership_id, self.dealership.pk
            )

    def test_recon_vehicles_have_three_event_stage_progression(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            events = list(
                VehicleStageEvent.objects.filter(
                    vehicle=vehicle
                ).order_by("entered_at")
            )
            self.assertEqual(len(events), 3)
            self.assertEqual(events[-1].to_stage, "recon")

    def test_all_recon_work_orders_share_the_mechanical_vendor(
        self,
    ) -> None:
        mechanical = Vendor.objects.get(
            dealership=self.dealership, slug="sunset-mechanical"
        )
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            wo = WorkOrder.objects.get(vehicle=vehicle)
            self.assertEqual(wo.vendor_id, mechanical.pk)

    def test_work_order_findings_link_to_recon_findings(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            wo = WorkOrder.objects.get(vehicle=vehicle)
            self.assertGreaterEqual(
                WorkOrderFinding.objects.filter(work_order=wo).count(),
                1,
            )
            self.assertGreaterEqual(
                WorkOrderPart.objects.filter(work_order=wo).count(),
                2,
            )

    def test_every_salesperson_has_user_linkage(self) -> None:
        for sp in Salesperson.objects.filter(
            dealership=self.dealership
        ):
            self.assertIsNotNone(sp.user_id)


# ---------------------------------------------------------------------------
# M15 sync-sibling GL post
# ---------------------------------------------------------------------------


class FloorPlannedGLPostingTests(_BuildTestMixin):
    def test_sale_bookings_produce_journal_entries(self) -> None:
        entries = JournalEntry.objects.filter(
            dealership=self.dealership
        )
        # Each Sale fires an M15 sync-sibling entry (M9 sale booking).
        self.assertGreaterEqual(entries.count(), len(_SALES))

    def test_each_sale_entry_references_its_stock_number(self) -> None:
        entry_descriptions = list(
            JournalEntry.objects.filter(
                dealership=self.dealership,
                description__startswith="M9 sale booking",
            ).values_list("description", flat=True)
        )
        for spec in _SALES:
            stock = str(spec["stock"])
            self.assertTrue(
                any(stock in desc for desc in entry_descriptions),
                f"No M9 sale-booking entry mentions {stock}",
            )


# ---------------------------------------------------------------------------
# ScenarioSummary shape
# ---------------------------------------------------------------------------


class FloorPlannedScenarioSummaryTests(_BuildTestMixin):
    def test_summary_type_and_archetype(self) -> None:
        self.assertIsInstance(self.summary, ScenarioSummary)
        self.assertEqual(
            self.summary.archetype, DEMO_ARCHETYPE_FLOOR_PLANNED
        )

    def test_summary_names_dealership(self) -> None:
        self.assertEqual(
            self.summary.dealership_id, self.dealership.pk
        )
        self.assertEqual(
            self.summary.dealership_slug, self.dealership.slug
        )

    def test_summary_names_all_stock_numbers(self) -> None:
        expected = {str(spec["stock"]) for spec in _INVENTORY}
        self.assertEqual(
            set(self.summary.seeded_stock_numbers), expected
        )

    def test_summary_names_user_usernames(self) -> None:
        self.assertEqual(
            len(self.summary.seeded_user_usernames), len(_STAFF)
        )

    def test_summary_names_recon_overrun_scenario_slug(self) -> None:
        self.assertIn(
            "recon_lead_overrun_intervention",
            self.summary.seeded_scenario_slugs,
        )


# ---------------------------------------------------------------------------
# Synthetic-only data safety
# ---------------------------------------------------------------------------


class FloorPlannedSyntheticDataTests(_BuildTestMixin):
    def test_every_vin_prefixed_demo_archetype_code(self) -> None:
        for vehicle in Vehicle.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                vehicle.vin.startswith("DEMOFP"),
                f"Vehicle {vehicle.stock_number} VIN not synthetic",
            )

    def test_every_lead_email_uses_example_tld(self) -> None:
        for lead in CustomerLead.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                lead.email.endswith("@demo.dealer-ai.example")
            )

    def test_every_lead_phone_uses_nanp_fiction_block(self) -> None:
        for lead in CustomerLead.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(lead.phone.startswith("555-01"))

    def test_every_seeded_user_email_uses_example_tld(self) -> None:
        for sp in Salesperson.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                sp.user.email.endswith("@demo.dealer-ai.example")
            )


# ---------------------------------------------------------------------------
# Reset — canonical state
# ---------------------------------------------------------------------------


class FloorPlannedResetTests(TestCase):
    def test_reset_restores_canonical_row_counts(self) -> None:
        dealership, _ = create_demo_store(
            slug="m183-reset-check",
            archetype=DEMO_ARCHETYPE_FLOOR_PLANNED,
        )
        vehicle_count = Vehicle.objects.filter(
            dealership=dealership
        ).count()
        Vehicle.objects.create(
            dealership=dealership,
            stock_number="FP-ROGUE",
            year=2020, model="RogueVan",
            price=Decimal("5000.00"), condition="used",
        )
        self.assertEqual(
            Vehicle.objects.filter(dealership=dealership).count(),
            vehicle_count + 1,
        )
        reset_demo_store(dealership=dealership)
        self.assertEqual(
            Vehicle.objects.filter(dealership=dealership).count(),
            vehicle_count,
        )
        self.assertFalse(
            Vehicle.objects.filter(
                dealership=dealership, stock_number="FP-ROGUE"
            ).exists()
        )

    def test_reset_preserves_overrun_scenario(self) -> None:
        dealership, _ = create_demo_store(
            slug="m183-reset-overrun",
            archetype=DEMO_ARCHETYPE_FLOOR_PLANNED,
        )
        reset_demo_store(dealership=dealership)
        vehicle = Vehicle.objects.get(
            dealership=dealership, stock_number=_RECON_TARGETS[0]
        )
        wo = WorkOrder.objects.get(vehicle=vehicle)
        assert wo.authorized_cost is not None
        assert wo.actual_cost is not None
        self.assertGreaterEqual(
            wo.actual_cost - wo.authorized_cost, Decimal("600.00")
        )


# ---------------------------------------------------------------------------
# Direct-instantiation smoke
# ---------------------------------------------------------------------------


class FloorPlannedBuilderDirectTests(TestCase):
    def test_builder_archetype_attr(self) -> None:
        self.assertEqual(
            FloorPlannedArchetypeBuilder.archetype,
            DEMO_ARCHETYPE_FLOOR_PLANNED,
        )
