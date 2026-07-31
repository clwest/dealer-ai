"""SESSION_030 pivot: Copper Canyon Auto scenario-seed contract.

Locks the shape of the demo chat sessions + leads created by
:mod:`seed_copper_canyon_scenarios` so the manager dashboard,
pipeline, and trends panels have predictable indie-shaped content
between demos.
"""

from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from dealer_ai.models import ChatSession, CustomerLead


SCENARIO_TAG = "copper_canyon_scenario"


def _seed():
    call_command("seed_copper_canyon_scenarios", stdout=StringIO())


def _reset_seed():
    call_command(
        "seed_copper_canyon_scenarios", "--reset", stdout=StringIO()
    )


class CopperCanyonScenariosSeedShape(TestCase):
    def setUp(self):
        _seed()

    def _sessions(self):
        return ChatSession.objects.filter(metadata__demo_tag=SCENARIO_TAG)

    def _leads(self):
        return CustomerLead.objects.filter(
            session__metadata__demo_tag=SCENARIO_TAG
        )

    def test_seed_creates_four_scenarios(self):
        self.assertEqual(self._sessions().count(), 4)

    def test_every_session_has_messages(self):
        for session in self._sessions():
            self.assertGreater(session.messages.count(), 0)

    def test_leads_populate_urgency_and_credit_range_mix(self):
        # The 4 scenarios span the credit and urgency shapes the
        # dashboard tries to visualize.
        leads = self._leads()
        self.assertGreaterEqual(leads.count(), 3)  # cash+no lead is 1
        credits = set(leads.values_list("credit_range", flat=True))
        urgencies = set(leads.values_list("urgency", flat=True))
        # Expect at least 2 distinct credit tiers (poor / fair /
        # excellent) and 2 distinct urgencies.
        self.assertGreaterEqual(len(credits - {""}), 2)
        self.assertGreaterEqual(len(urgencies - {""}), 2)

    def test_scenarios_reference_copper_canyon_stock(self):
        # Every interested vehicle should be a CC-* stock number from
        # the Copper Canyon inventory — no franchise-seed FF-* stock.
        for lead in self._leads():
            for veh in lead.interested_vehicles.all():
                self.assertTrue(
                    veh.stock_number.startswith("CC-"),
                    f"scenario references non-Copper Canyon stock: "
                    f"{veh.stock_number}",
                )

    def test_at_least_one_scenario_is_handed_off(self):
        # The Contacted column on the pipeline needs at least one row.
        self.assertGreaterEqual(
            self._leads().filter(handed_off=True).count(), 1
        )

    def test_at_least_one_scenario_is_open_and_immediate(self):
        # The recommended-actions card needs a HIGH-priority sales
        # signal (immediate + not handed off).
        immediate_open = self._leads().filter(
            urgency="immediate", handed_off=False
        )
        self.assertGreaterEqual(immediate_open.count(), 1)

    def test_idempotent_re_seed(self):
        first_sessions = self._sessions().count()
        first_leads = self._leads().count()
        _seed()
        self.assertEqual(self._sessions().count(), first_sessions)
        self.assertEqual(self._leads().count(), first_leads)

    def test_reset_wipes_prior_scenarios_before_reseeding(self):
        # Add a marker session that should survive if --reset is
        # scoped correctly (only touches SCENARIO_TAG rows).
        marker = ChatSession.objects.create(
            metadata={"slug": "not-a-scenario", "demo_tag": "other"}
        )
        _reset_seed()
        self.assertEqual(self._sessions().count(), 4)
        # Non-scenario marker survives.
        self.assertTrue(
            ChatSession.objects.filter(pk=marker.pk).exists()
        )

    def test_bhph_scenario_reflects_credit_challenged_shape(self):
        # The Michelle Ortiz scenario is the anchor for the BHPH /
        # in-house-financing dashboard story. Lock its shape.
        bhph = self._sessions().get(metadata__slug="bhph_weekly_suv_michelle")
        lead = self._leads().get(session=bhph)
        self.assertEqual(lead.credit_range, "poor")
        self.assertEqual(lead.urgency, "immediate")
        self.assertFalse(lead.handed_off)
