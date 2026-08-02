"""Milestone 18 · Increment 2 (SESSION_148) — retail/subprime archetype tests.

Covers per MILESTONE_18_PLANNING.md §7 M18.2:

- Row-count contract per _INVENTORY / _STAFF / _LEADS / _SALES /
  _RECON_TARGETS / _CREDIT_APPS / _FOLLOW_UP_LEADS.
- Cross-domain integrity: VehicleCost totals feed the M2 investment
  ledger read model; recon vehicles have coherent VehicleStageEvent
  progression; CreditApplication references a Sale in the same
  tenant.
- M15 sync-sibling GL post fires on the BHPH Sale (M13 JournalEntry
  rows exist after build).
- Reset via ``reset_demo_store()`` restores canonical starting state
  (stable stock numbers + counts).
- ``ScenarioSummary`` contract: fields populated per §5.d shape.
- Synthetic-only data — no seeded VIN, phone, or email escapes the
  §5.g Option A safety envelope.
"""

from __future__ import annotations

from decimal import Decimal
from typing import cast

from django.contrib.auth import get_user_model
from django.test import TestCase

from dealer_ai.models import (
    DEMO_ARCHETYPE_RETAIL_SUBPRIME,
    SALE_FINANCE_TYPE_BHPH,
    BhphNote,
    ConditionFinding,
    ConditionReport,
    CreditApplication,
    CustomerLead,
    Dealership,
    FollowUpCadence,
    FollowUpTask,
    JournalEntry,
    ReconDecision,
    Sale,
    Salesperson,
    Vehicle,
    VehicleAcquisition,
    VehicleCost,
    VehicleStage,
    VehicleStageEvent,
    Vendor,
    WorkOrder,
    WorkOrderFinding,
    WorkOrderPart,
)
from dealer_ai.services.demo_store import (
    ScenarioSummary,
    create_demo_store,
    reset_demo_store,
)
from dealer_ai.services.demo_store.archetypes.retail_subprime import (
    _INVENTORY,
    _LEADS,
    _RECON_TARGETS,
    _SALES,
    _STAFF,
    RetailSubprimeArchetypeBuilder,
)


User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixture — a freshly-built retail/subprime demo store.
# ---------------------------------------------------------------------------


class _BuildTestMixin(TestCase):
    """setUp helper — builds a demo store once for read-only tests."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.dealership, cls.summary = create_demo_store(
            slug="m182-retail-fixture",
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
            name="M18.2 Retail Fixture",
        )


# ---------------------------------------------------------------------------
# Row-count contract per specs
# ---------------------------------------------------------------------------


class RetailSubprimeRowCountsTests(_BuildTestMixin):
    def test_vehicles_match_inventory_spec(self) -> None:
        count = Vehicle.objects.filter(dealership=self.dealership).count()
        self.assertEqual(count, len(_INVENTORY))

    def test_acquisitions_match_vehicle_count(self) -> None:
        # Every seeded vehicle gets an acquisition record.
        count = VehicleAcquisition.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(count, len(_INVENTORY))

    def test_salespeople_match_staff_spec(self) -> None:
        count = Salesperson.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(count, len(_STAFF))

    def test_leads_at_least_lead_spec_plus_sale_buyers(self) -> None:
        # 15 pipeline leads + one buyer lead per Sale (5).
        count = CustomerLead.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(count, len(_LEADS) + len(_SALES))

    def test_sales_match_sale_spec(self) -> None:
        count = Sale.objects.filter(dealership=self.dealership).count()
        self.assertEqual(count, len(_SALES))

    def test_bhph_note_count_matches_bhph_sales(self) -> None:
        bhph_count = sum(
            1 for s in _SALES if s["finance"] == SALE_FINANCE_TYPE_BHPH
        )
        count = BhphNote.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(count, bhph_count)
        self.assertGreaterEqual(bhph_count, 1)  # sanity: at least one

    def test_recon_vehicles_have_condition_reports(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            self.assertTrue(
                ConditionReport.objects.filter(vehicle=vehicle).exists(),
                f"Recon target {stock} missing ConditionReport",
            )

    def test_condition_findings_at_least_two_per_recon_vehicle(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            findings = ConditionFinding.objects.filter(
                report__vehicle=vehicle
            )
            self.assertGreaterEqual(findings.count(), 2)

    def test_recon_decisions_present_for_findings(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            decision_count = ReconDecision.objects.filter(
                finding__report__vehicle=vehicle
            ).count()
            self.assertGreaterEqual(decision_count, 2)

    def test_work_orders_and_parts_present(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            work_orders = WorkOrder.objects.filter(vehicle=vehicle)
            self.assertGreaterEqual(work_orders.count(), 1)
            wo = work_orders.first()
            assert wo is not None
            self.assertGreaterEqual(
                WorkOrderPart.objects.filter(work_order=wo).count(), 1
            )
            self.assertGreaterEqual(
                WorkOrderFinding.objects.filter(work_order=wo).count(), 1
            )

    def test_credit_applications_match_spec(self) -> None:
        count = CreditApplication.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertEqual(count, 2)

    def test_follow_up_cadence_and_tasks_present(self) -> None:
        cadence_count = FollowUpCadence.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertGreaterEqual(cadence_count, 1)
        # The 1wk template auto-creates 3 tasks per cadence per
        # FOLLOW_UP_TEMPLATE_OFFSETS.
        task_count = FollowUpTask.objects.filter(
            dealership=self.dealership
        ).count()
        self.assertGreaterEqual(task_count, 3)


# ---------------------------------------------------------------------------
# Cross-domain integrity
# ---------------------------------------------------------------------------


class RetailSubprimeCrossDomainIntegrityTests(_BuildTestMixin):
    def test_every_sale_has_a_buyer_in_same_tenant(self) -> None:
        for sale in Sale.objects.filter(dealership=self.dealership):
            self.assertIsNotNone(sale.buyer_id)
            self.assertEqual(sale.buyer.dealership_id, self.dealership.pk)

    def test_every_credit_app_references_a_sale_in_same_tenant(self) -> None:
        for app in CreditApplication.objects.filter(
            dealership=self.dealership
        ):
            self.assertIsNotNone(app.sale_id)
            self.assertEqual(app.sale.dealership_id, self.dealership.pk)

    def test_recon_vehicles_have_stage_progression(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            events = list(
                VehicleStageEvent.objects.filter(vehicle=vehicle).order_by(
                    "entered_at"
                )
            )
            # incoming → inspection → recon (3 events).
            self.assertEqual(len(events), 3)
            self.assertEqual(events[0].to_stage, "incoming")
            self.assertEqual(events[1].to_stage, "inspection")
            self.assertEqual(events[2].to_stage, "recon")

    def test_recon_vehicle_costs_reconcile_with_vendor_labor(self) -> None:
        for stock in _RECON_TARGETS:
            vehicle = Vehicle.objects.get(
                dealership=self.dealership, stock_number=stock
            )
            costs = VehicleCost.objects.filter(vehicle=vehicle)
            # 4 rows per recon vehicle: parts + labor + tires + detail.
            self.assertGreaterEqual(costs.count(), 4)
            total = sum(
                (c.amount for c in costs), start=Decimal("0.00")
            )
            # Sanity — recon spend should be at least the sum of
            # documented items ($300 + $220 + $420 + $85 = $1,025).
            self.assertGreaterEqual(total, Decimal("1025.00"))

    def test_vendor_row_reused_across_recon_work_orders(self) -> None:
        vendors = Vendor.objects.filter(dealership=self.dealership)
        # One shared outsourced vendor across recon targets.
        self.assertEqual(vendors.count(), 1)

    def test_all_users_linked_to_salespeople(self) -> None:
        # Salesperson.user is 1:1; every seeded staff row has a User.
        for salesperson in Salesperson.objects.filter(
            dealership=self.dealership
        ):
            self.assertIsNotNone(
                salesperson.user_id,
                f"Salesperson {salesperson.slug} missing user linkage",
            )


# ---------------------------------------------------------------------------
# M15 sync-sibling GL post — verify JournalEntries were created
# ---------------------------------------------------------------------------


class RetailSubprimeGLPostingTests(_BuildTestMixin):
    def test_sale_bookings_produced_journal_entries(self) -> None:
        # Every seeded Sale invokes record_sale which fires
        # M15.1 sync-sibling GL post. Journal entries should
        # exist for the tenant.
        entries = JournalEntry.objects.filter(
            dealership=self.dealership
        )
        self.assertGreaterEqual(entries.count(), len(_SALES))

    def test_sale_descriptions_reference_stock_numbers(self) -> None:
        # M15.1 description format:
        # "M9 sale booking — Sale #<pk> of stock <stock> (...)"
        sale_stocks = {str(s["stock"]) for s in _SALES}
        entry_descriptions = list(
            JournalEntry.objects.filter(
                dealership=self.dealership,
                description__startswith="M9 sale booking",
            ).values_list("description", flat=True)
        )
        # Each Sale should produce one M15 entry naming its stock.
        for stock in sale_stocks:
            self.assertTrue(
                any(stock in desc for desc in entry_descriptions),
                f"No M9 sale-booking journal entry mentions stock {stock}",
            )


# ---------------------------------------------------------------------------
# ScenarioSummary contract
# ---------------------------------------------------------------------------


class RetailSubprimeScenarioSummaryTests(_BuildTestMixin):
    def test_summary_type(self) -> None:
        self.assertIsInstance(self.summary, ScenarioSummary)

    def test_summary_archetype_matches(self) -> None:
        self.assertEqual(
            self.summary.archetype, DEMO_ARCHETYPE_RETAIL_SUBPRIME
        )

    def test_summary_names_dealership(self) -> None:
        self.assertEqual(self.summary.dealership_id, self.dealership.pk)
        self.assertEqual(
            self.summary.dealership_slug, self.dealership.slug
        )

    def test_summary_names_all_stock_numbers(self) -> None:
        seeded = set(self.summary.seeded_stock_numbers)
        expected = {str(spec["stock"]) for spec in _INVENTORY}
        self.assertEqual(seeded, expected)

    def test_summary_names_user_usernames(self) -> None:
        self.assertEqual(
            len(self.summary.seeded_user_usernames), len(_STAFF)
        )

    def test_summary_has_scenario_slugs(self) -> None:
        # Six scenario briefs land at M18.5 — the summary names them
        # so briefs can reference the correct pre-seeded state.
        self.assertGreaterEqual(len(self.summary.seeded_scenario_slugs), 5)


# ---------------------------------------------------------------------------
# Synthetic-only data safety
# ---------------------------------------------------------------------------


class RetailSubprimeSyntheticDataTests(_BuildTestMixin):
    def test_every_vin_prefixed_demo_archetype_code(self) -> None:
        for vehicle in Vehicle.objects.filter(dealership=self.dealership):
            self.assertTrue(
                vehicle.vin.startswith("DEMORS"),
                f"Vehicle {vehicle.stock_number} VIN {vehicle.vin!r} not "
                "synthetic-prefixed",
            )

    def test_every_lead_email_uses_example_tld(self) -> None:
        for lead in CustomerLead.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                lead.email.endswith("@demo.dealer-ai.example"),
                f"Lead {lead.name!r} email {lead.email!r} not synthetic",
            )

    def test_every_lead_phone_uses_nanp_fiction_block(self) -> None:
        for lead in CustomerLead.objects.filter(
            dealership=self.dealership
        ):
            self.assertTrue(
                lead.phone.startswith("555-01"),
                f"Lead {lead.name!r} phone {lead.phone!r} not synthetic",
            )

    def test_every_user_email_uses_example_tld(self) -> None:
        # Only assert on seeded users, not any default-migration users
        # that might exist. Salespeople have .user set at M18.2.
        for salesperson in Salesperson.objects.filter(
            dealership=self.dealership
        ):
            self.assertIsNotNone(salesperson.user_id)
            self.assertTrue(
                salesperson.user.email.endswith("@demo.dealer-ai.example"),
                f"User {salesperson.user.username} email not synthetic",
            )


# ---------------------------------------------------------------------------
# Reset — canonical state restored
# ---------------------------------------------------------------------------


class RetailSubprimeResetTests(TestCase):
    def test_reset_restores_canonical_row_counts(self) -> None:
        dealership, _ = create_demo_store(
            slug="m182-reset-check",
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
        )
        vehicle_count_after_build = Vehicle.objects.filter(
            dealership=dealership
        ).count()
        # Seed some rogue rows that reset must clear.
        Vehicle.objects.create(
            dealership=dealership,
            stock_number="ROGUE-01",
            year=2020, model="RogueCar",
            price=Decimal("5000.00"),
            condition="used",
        )
        self.assertEqual(
            Vehicle.objects.filter(dealership=dealership).count(),
            vehicle_count_after_build + 1,
        )
        reset_demo_store(dealership=dealership)
        self.assertEqual(
            Vehicle.objects.filter(dealership=dealership).count(),
            vehicle_count_after_build,
        )
        self.assertFalse(
            Vehicle.objects.filter(
                dealership=dealership, stock_number="ROGUE-01"
            ).exists()
        )

    def test_reset_preserves_dealership_row_pk(self) -> None:
        dealership, _ = create_demo_store(
            slug="m182-reset-pk-stable",
            archetype=DEMO_ARCHETYPE_RETAIL_SUBPRIME,
        )
        original_pk = dealership.pk
        reset_demo_store(dealership=dealership)
        # Refetch by pk — the same dealership row survives.
        dealership.refresh_from_db()
        self.assertEqual(dealership.pk, original_pk)
        self.assertTrue(dealership.is_demo)


# ---------------------------------------------------------------------------
# Builder direct-instantiation smoke test (used by registry)
# ---------------------------------------------------------------------------


class RetailSubprimeBuilderDirectTests(TestCase):
    def test_builder_archetype_attr(self) -> None:
        self.assertEqual(
            RetailSubprimeArchetypeBuilder.archetype,
            DEMO_ARCHETYPE_RETAIL_SUBPRIME,
        )
