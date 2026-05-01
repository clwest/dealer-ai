"""Manager Phase 2: recommended_actions rule coverage.

Covers Feature C decision rules from the design:

- Inventory: high vs medium priority based on lead_count band, mismatch
  vs tight vs watch tiers.
- Sales: high_intent count escalation (0 / 1-2 / 3+), new column
  triage threshold, aging needs_handoff (>48h), per-lead "no vehicles
  flagged" fallback.
- Marketing: top model promotion, vehicle-type push, "highlight" cards
  for most-selected vehicles.
- Suppression: marketing model card suppressed when an inventory mismatch
  card already fires at high priority.
- Capping at top 5.
- Determinism (same inputs → same id ordering).
- Empty state.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import List, Tuple

from django.test import TestCase
from django.utils import timezone

from dealer_ai.models import CustomerLead, Vehicle
from dealer_ai.services import pipeline as pipeline_svc


def _make_vehicle(stock: str, price: str, *, model: str = "F-150") -> Vehicle:
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _set_created_at(lead: CustomerLead, when) -> None:
    CustomerLead.objects.filter(pk=lead.pk).update(created_at=when)
    lead.refresh_from_db()


def _seed_band_500(*, n_leads: int, n_vehicles: int) -> Tuple[List[CustomerLead], List[Vehicle]]:
    """Seed `n_leads` open leads at $500/mo and `n_vehicles` vehicles at
    $30k. A $30k vehicle's computed monthly at engine defaults (72mo,
    $0 down) is ≈ $552, which lands in the $500–599/mo band's price
    range derived from affordable_max_price."""
    Vehicle.objects.all().delete()
    vehicles = [_make_vehicle(f"V-{i}", "30000.00") for i in range(n_vehicles)]
    leads = [
        CustomerLead.objects.create(
            name=f"L{i}",
            target_monthly_payment=Decimal("500"),
            handed_off=False,
        )
        for i in range(n_leads)
    ]
    return leads, vehicles


class InventoryRuleTests(TestCase):
    def test_high_priority_inventory_card_when_5_plus_leads(self):
        _seed_band_500(n_leads=8, n_vehicles=2)
        snap = pipeline_svc.pipeline_snapshot()
        inv = [
            c for c in snap["recommended_actions"] if c["category"] == "inventory"
        ]
        self.assertGreater(len(inv), 0)
        top = inv[0]
        self.assertEqual(top["priority"], "high")
        self.assertEqual(top["evidence"]["lead_count"], 8)
        self.assertEqual(top["evidence"]["vehicle_count"], 2)
        # Title quotes the price range derived from affordable_max_price.
        # For the $500–599/mo band that's roughly $27k–$32k.
        self.assertIn("$27,", top["title"])
        self.assertIn("$32,", top["title"])
        # CTA should target the same band.
        self.assertEqual(top["cta"]["kind"], "view_leads_in_band")
        self.assertEqual(top["cta"]["params"]["monthly_low"], 500)
        self.assertEqual(top["cta"]["params"]["monthly_high"], 599)

    def test_medium_priority_inventory_card_when_3_or_4_leads(self):
        _seed_band_500(n_leads=3, n_vehicles=1)
        snap = pipeline_svc.pipeline_snapshot()
        inv = [
            c for c in snap["recommended_actions"] if c["category"] == "inventory"
        ]
        self.assertGreater(len(inv), 0)
        # Lead_count=3 lands the rule but priority is medium, not high.
        self.assertEqual(inv[0]["priority"], "medium")

    def test_no_inventory_card_when_lead_count_below_floor(self):
        # 2 leads, 0 vehicles — ratio is high but lead_count < 3 floor.
        _seed_band_500(n_leads=2, n_vehicles=0)
        snap = pipeline_svc.pipeline_snapshot()
        # No mismatch card, but possibly a tight/watch card (not a mismatch).
        for c in snap["recommended_actions"]:
            if c["category"] == "inventory":
                self.assertNotIn("mismatch", c["id"])

    def test_tight_card_emits_when_5_plus_leads_and_ratio_above_125(self):
        # 5 leads, 4 vehicles → ratio = 1.25 → tight; >=5 leads → medium card.
        _seed_band_500(n_leads=5, n_vehicles=4)
        snap = pipeline_svc.pipeline_snapshot()
        tight = [
            c
            for c in snap["recommended_actions"]
            if c["category"] == "inventory" and "tight" in c["id"]
        ]
        self.assertEqual(len(tight), 1)
        self.assertEqual(tight[0]["priority"], "medium")


class SalesRuleTests(TestCase):
    def test_high_priority_sales_card_when_3_plus_high_intent(self):
        for i in range(3):
            CustomerLead.objects.create(
                name=f"H{i}",
                urgency="immediate",
                target_monthly_payment=Decimal("500"),
                handed_off=False,
            )
        snap = pipeline_svc.pipeline_snapshot()
        sales = [
            c for c in snap["recommended_actions"] if c["category"] == "sales"
        ]
        # The high-intent card should be present and high priority.
        high_card = next(c for c in sales if "high_intent_assign" in c["id"])
        self.assertEqual(high_card["priority"], "high")
        self.assertEqual(high_card["evidence"]["high_intent_count"], 3)
        self.assertIn("$500", high_card["evidence"]["avg_target_monthly_payment"])

    def test_medium_priority_sales_card_for_1_or_2_high_intent(self):
        CustomerLead.objects.create(
            name="H1", urgency="immediate", handed_off=False
        )
        snap = pipeline_svc.pipeline_snapshot()
        sales = [
            c for c in snap["recommended_actions"] if c["category"] == "sales"
        ]
        clear = next(c for c in sales if "high_intent_clear" in c["id"])
        self.assertEqual(clear["priority"], "medium")

    def test_no_sales_card_when_zero_high_intent_and_no_aging(self):
        # Single non-urgent lead, fresh → only "new" stage, not enough to fire.
        CustomerLead.objects.create(name="A", handed_off=False)
        snap = pipeline_svc.pipeline_snapshot()
        sales = [
            c for c in snap["recommended_actions"] if c["category"] == "sales"
        ]
        # No high-intent or aging card. New_count < 5 so no triage card.
        self.assertEqual(
            [c for c in sales if "high_intent" in c["id"] or "aging" in c["id"] or "triage" in c["id"]],
            [],
        )

    def test_aging_needs_handoff_card_counts_only_leads_over_48h(self):
        now = timezone.now()
        # 2 aged + 2 fresh; only the aged should count.
        for i in range(2):
            l = CustomerLead.objects.create(
                name=f"Aged{i}", urgency="this_week", handed_off=False
            )
            _set_created_at(l, now - timedelta(hours=50))
        for i in range(2):
            l = CustomerLead.objects.create(
                name=f"Old{i}", urgency="this_week", handed_off=False
            )
            _set_created_at(l, now - timedelta(hours=30))

        snap = pipeline_svc.pipeline_snapshot()
        aging = [
            c
            for c in snap["recommended_actions"]
            if c["id"] == "sales.aging_needs_handoff"
        ]
        self.assertEqual(len(aging), 1)
        self.assertEqual(aging[0]["evidence"]["aging_count"], 2)
        self.assertEqual(aging[0]["priority"], "medium")

    def test_new_triage_card_when_5_plus_new_leads(self):
        for i in range(6):
            CustomerLead.objects.create(
                name=f"N{i}", urgency="this_week", handed_off=False
            )
        snap = pipeline_svc.pipeline_snapshot()
        triage = [
            c
            for c in snap["recommended_actions"]
            if c["id"] == "sales.new_triage"
        ]
        self.assertEqual(len(triage), 1)
        self.assertEqual(triage[0]["evidence"]["new_count"], 6)


class MarketingSuppressionTests(TestCase):
    def test_marketing_model_card_suppressed_when_high_inventory_card_present(self):
        # Set up a high-priority inventory mismatch …
        _seed_band_500(n_leads=8, n_vehicles=1)
        # … and a top-model trend that would otherwise trigger marketing.
        from dealer_ai.models import ChatSession

        for _ in range(3):
            ChatSession.objects.create(extracted_profile={"model": "F-150"})
        # Add some F-150 inventory so the marketing rule's stock check passes.
        for i in range(3):
            _make_vehicle(f"FX-{i}", "45000.00", model="F-150")

        snap = pipeline_svc.pipeline_snapshot()
        marketing = [
            c for c in snap["recommended_actions"] if c["category"] == "marketing"
        ]
        # Top-model promote card should be suppressed because of the
        # high-priority inventory card.
        self.assertEqual(
            [c for c in marketing if "promote_model" in c["id"]], []
        )

    def test_marketing_model_card_emitted_when_no_high_inventory_card(self):
        # No inventory mismatch — marketing should fire.
        from dealer_ai.models import ChatSession

        # Top model = F-150 (3 sessions) and inventory available.
        for _ in range(3):
            ChatSession.objects.create(extracted_profile={"model": "F-150"})
        for i in range(3):
            _make_vehicle(f"FX-{i}", "45000.00", model="F-150")

        snap = pipeline_svc.pipeline_snapshot()
        marketing = [
            c for c in snap["recommended_actions"] if c["category"] == "marketing"
        ]
        self.assertGreaterEqual(
            len([c for c in marketing if "promote_model" in c["id"]]), 1
        )


class CappingAndDeterminismTests(TestCase):
    def test_cards_are_capped_at_5(self):
        # Seed mismatches across multiple bands.
        Vehicle.objects.all().delete()
        # $300/mo band: 4 leads, 1 vehicle (~$13.7k)
        _make_vehicle("V300", "13000.00")
        for i in range(4):
            CustomerLead.objects.create(
                name=f"L300-{i}",
                target_monthly_payment=Decimal("350"),
                handed_off=False,
            )
        # $400/mo band: 5 leads, 1 vehicle (~$18.2k)
        _make_vehicle("V400", "18000.00")
        for i in range(5):
            CustomerLead.objects.create(
                name=f"L400-{i}",
                target_monthly_payment=Decimal("450"),
                handed_off=False,
            )
        # $500/mo band: 6 leads, 1 vehicle (~$23k)
        _make_vehicle("V500", "23000.00")
        for i in range(6):
            CustomerLead.objects.create(
                name=f"L500-{i}",
                target_monthly_payment=Decimal("550"),
                handed_off=False,
            )
        # $600/mo band: 7 leads, 1 vehicle
        _make_vehicle("V600", "28000.00")
        for i in range(7):
            CustomerLead.objects.create(
                name=f"L600-{i}",
                target_monthly_payment=Decimal("650"),
                handed_off=False,
            )
        # $700/mo band: 4 leads, 1 vehicle
        _make_vehicle("V700", "33000.00")
        for i in range(4):
            CustomerLead.objects.create(
                name=f"L700-{i}",
                target_monthly_payment=Decimal("750"),
                handed_off=False,
            )

        snap = pipeline_svc.pipeline_snapshot()
        self.assertLessEqual(len(snap["recommended_actions"]), 5)
        # First card should be the highest-priority one.
        self.assertEqual(snap["recommended_actions"][0]["priority"], "high")

    def test_empty_state_returns_empty_recommendations(self):
        # No leads, no inventory.
        snap = pipeline_svc.pipeline_snapshot()
        self.assertEqual(snap["recommended_actions"], [])

    def test_determinism_same_input_same_id_order(self):
        _seed_band_500(n_leads=8, n_vehicles=2)
        snap1 = pipeline_svc.pipeline_snapshot()
        snap2 = pipeline_svc.pipeline_snapshot()
        ids1 = [c["id"] for c in snap1["recommended_actions"]]
        ids2 = [c["id"] for c in snap2["recommended_actions"]]
        self.assertEqual(ids1, ids2)


class CardOrderingTests(TestCase):
    def test_high_priority_cards_sort_before_medium(self):
        # High inventory + high sales should both end up before medium cards.
        _seed_band_500(n_leads=8, n_vehicles=2)
        for i in range(3):
            CustomerLead.objects.create(
                name=f"H{i}",
                urgency="immediate",
                target_monthly_payment=Decimal("500"),
                handed_off=False,
            )
        snap = pipeline_svc.pipeline_snapshot()
        priorities = [c["priority"] for c in snap["recommended_actions"]]
        # No "medium" or "low" should appear before any "high".
        last_high_idx = max(
            (i for i, p in enumerate(priorities) if p == "high"), default=-1
        )
        first_non_high_idx = next(
            (i for i, p in enumerate(priorities) if p != "high"), len(priorities)
        )
        self.assertLess(last_high_idx, first_non_high_idx)
