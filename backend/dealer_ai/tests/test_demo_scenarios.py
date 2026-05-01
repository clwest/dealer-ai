"""Tests for the seed_demo_scenarios command + /demo/scenarios/ endpoint."""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from dealer_ai.management.commands.seed_demo_scenarios import (
    SCENARIOS,
    SCENARIO_TAG,
)
from dealer_ai.models import ChatSession, CustomerLead, Vehicle


class SeedDemoScenariosCommandTests(TestCase):
    def setUp(self):
        # Make sure demo inventory exists for vehicle lookups.
        call_command("seed_demo_vehicles", stdout=StringIO())

    def test_seeds_all_scenarios(self):
        out = StringIO()
        call_command("seed_demo_scenarios", stdout=out)
        self.assertEqual(ChatSession.objects.count(), len(SCENARIOS))
        # Each scenario in the fixture defines a lead.
        expected_leads = sum(1 for s in SCENARIOS if s.lead is not None)
        self.assertEqual(CustomerLead.objects.count(), expected_leads)
        for scenario in SCENARIOS:
            self.assertTrue(
                ChatSession.objects.filter(
                    metadata__scenario=scenario.slug
                ).exists(),
                f"scenario {scenario.slug} not seeded",
            )

    def test_idempotent_without_reset(self):
        call_command("seed_demo_scenarios", stdout=StringIO())
        first_session_count = ChatSession.objects.count()
        first_lead_count = CustomerLead.objects.count()
        call_command("seed_demo_scenarios", stdout=StringIO())
        self.assertEqual(ChatSession.objects.count(), first_session_count)
        self.assertEqual(CustomerLead.objects.count(), first_lead_count)

    def test_reset_flag_clears_and_reseeds(self):
        call_command("seed_demo_scenarios", stdout=StringIO())
        # Add an unrelated session that should be wiped on reset.
        ChatSession.objects.create(customer_name="Out-of-band")
        self.assertGreater(ChatSession.objects.count(), len(SCENARIOS))
        call_command("seed_demo_scenarios", "--reset", stdout=StringIO())
        self.assertEqual(ChatSession.objects.count(), len(SCENARIOS))

    def test_scenarios_link_real_inventory(self):
        call_command("seed_demo_scenarios", stdout=StringIO())
        for scenario in SCENARIOS:
            if not scenario.interested_stock_numbers:
                continue
            lead = CustomerLead.objects.get(
                session__metadata__scenario=scenario.slug
            )
            self.assertEqual(
                set(lead.interested_vehicles.values_list("stock_number", flat=True)),
                set(scenario.interested_stock_numbers),
            )

    def test_each_lead_has_summary_and_next_action(self):
        call_command("seed_demo_scenarios", stdout=StringIO())
        for lead in CustomerLead.objects.all():
            self.assertTrue(
                lead.conversation_summary.strip(),
                f"lead {lead.name} missing summary",
            )
            self.assertTrue(
                lead.recommended_next_action.strip(),
                f"lead {lead.name} missing next action",
            )

    def test_messages_are_backdated(self):
        call_command("seed_demo_scenarios", stdout=StringIO())
        for session in ChatSession.objects.all():
            msgs = list(session.messages.order_by("created_at"))
            self.assertGreater(len(msgs), 0)
            # First message should be earlier than the last.
            if len(msgs) > 1:
                self.assertLess(msgs[0].created_at, msgs[-1].created_at)

    def test_session_metadata_tagged(self):
        call_command("seed_demo_scenarios", stdout=StringIO())
        for session in ChatSession.objects.all():
            self.assertEqual(session.metadata.get("tag"), SCENARIO_TAG)
            self.assertIn(session.metadata.get("scenario"), {s.slug for s in SCENARIOS})

    def test_runs_seed_demo_vehicles_when_inventory_missing(self):
        Vehicle.objects.all().delete()
        out = StringIO()
        call_command("seed_demo_scenarios", stdout=out)
        # Vehicles should have been re-seeded.
        self.assertGreater(Vehicle.objects.filter(source="demo_seed").count(), 0)


class DemoLoadScenariosEndpointTests(TestCase):
    def setUp(self):
        call_command("seed_demo_vehicles", stdout=StringIO())

    def test_endpoint_seeds_scenarios(self):
        url = reverse("dealer_ai:demo-load-scenarios")
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["chat_sessions"], len(SCENARIOS))
        self.assertGreater(data["leads"], 0)

    def test_endpoint_reset_flag(self):
        # Seed once.
        url = reverse("dealer_ai:demo-load-scenarios")
        self.client.post(url, data={}, content_type="application/json")
        # Out-of-band session.
        ChatSession.objects.create(customer_name="Stray")
        # Reset.
        res = self.client.post(
            url, data={"reset": True}, content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        # Stray session should have been cleared.
        self.assertFalse(
            ChatSession.objects.filter(customer_name="Stray").exists()
        )
        self.assertEqual(ChatSession.objects.count(), len(SCENARIOS))
