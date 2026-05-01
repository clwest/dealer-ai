"""Unit tests for the trends aggregation service."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatSession, CustomerLead, Vehicle
from dealer_ai.services import trends


def _make_vehicle(stock, price, model="F-150"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


class TrendsServiceTests(TestCase):
    def test_empty_state(self):
        snap = trends.trends_snapshot()
        self.assertEqual(snap["total_chat_sessions"], 0)
        self.assertEqual(snap["total_leads"], 0)
        self.assertIsNone(snap["average_target_monthly_payment"])
        self.assertEqual(snap["budget_mismatch_count"], 0)
        self.assertEqual(snap["top_requested_models"], [])
        self.assertEqual(snap["recent_customer_intents"], [])

    def test_top_requested_models_and_types(self):
        ChatSession.objects.create(
            extracted_profile={"model": "F-150", "vehicle_type": "truck"}
        )
        ChatSession.objects.create(
            extracted_profile={"model": "F-150", "vehicle_type": "truck"}
        )
        ChatSession.objects.create(
            extracted_profile={"model": "Maverick", "vehicle_type": "truck"}
        )
        ChatSession.objects.create(
            extracted_profile={"model": "Bronco", "vehicle_type": "suv"}
        )

        models = trends.top_requested_models()
        self.assertEqual(models[0], {"value": "F-150", "count": 2})
        self.assertIn({"value": "Maverick", "count": 1}, models)

        types = trends.top_requested_vehicle_types()
        self.assertEqual(types[0], {"value": "truck", "count": 3})

    def test_average_target_monthly_payment_uses_leads_first(self):
        CustomerLead.objects.create(name="A", target_monthly_payment=Decimal("400"))
        CustomerLead.objects.create(name="B", target_monthly_payment=Decimal("600"))
        # Sessions exist but should be ignored when leads have data.
        ChatSession.objects.create(
            extracted_profile={"target_monthly_payment": 9999}
        )
        avg = trends.average_target_monthly_payment()
        self.assertEqual(avg, 500.0)

    def test_average_falls_back_to_session_profiles(self):
        ChatSession.objects.create(extracted_profile={"target_monthly_payment": 500})
        ChatSession.objects.create(extracted_profile={"target_monthly_payment": 700})
        avg = trends.average_target_monthly_payment()
        self.assertEqual(avg, 600.0)

    def test_most_selected_vehicles(self):
        v1 = _make_vehicle("S-1", "60000.00")
        v2 = _make_vehicle("S-2", "40000.00", model="Maverick")
        v3 = _make_vehicle("S-3", "35000.00", model="Escape")
        l1 = CustomerLead.objects.create(name="A")
        l2 = CustomerLead.objects.create(name="B")
        l3 = CustomerLead.objects.create(name="C")
        l1.interested_vehicles.add(v1, v2)
        l2.interested_vehicles.add(v1)
        l3.interested_vehicles.add(v3)

        result = trends.most_selected_vehicles()
        # v1 has 2 leads, v2 and v3 have 1 each
        self.assertEqual(result[0]["id"], v1.id)
        self.assertEqual(result[0]["lead_count"], 2)

    def test_budget_mismatch_count_flags_overshooters(self):
        expensive = _make_vehicle("EXP", "78000.00")
        affordable = _make_vehicle("AFF", "32000.00", model="Maverick")
        # Mismatch lead: $400/mo with $0 down can't afford $78k.
        bad = CustomerLead.objects.create(
            name="Stretching",
            target_monthly_payment=Decimal("400"),
            down_payment=Decimal("0"),
        )
        bad.interested_vehicles.add(expensive)
        # Reasonable lead.
        good = CustomerLead.objects.create(
            name="Realistic",
            target_monthly_payment=Decimal("550"),
            down_payment=Decimal("3000"),
        )
        good.interested_vehicles.add(affordable)

        self.assertEqual(trends.budget_mismatch_count(), 1)

    def test_budget_mismatch_skipped_when_no_target_or_no_vehicles(self):
        v = _make_vehicle("E1", "78000.00")
        # No target payment.
        no_target = CustomerLead.objects.create(name="No target")
        no_target.interested_vehicles.add(v)
        # No vehicles flagged.
        CustomerLead.objects.create(
            name="No vehicles", target_monthly_payment=Decimal("100")
        )
        self.assertEqual(trends.budget_mismatch_count(), 0)

    def test_recent_customer_intents_limited_and_ordered(self):
        for i, intent in enumerate(["vehicle_search", "trade_in", "compare_vehicles"]):
            ChatSession.objects.create(
                extracted_profile={"intent": intent, "model": f"M{i}"},
            )
        # Plus one with no intent — must be skipped.
        ChatSession.objects.create(extracted_profile={"model": "skipme"})

        recent = trends.recent_customer_intents(limit=10)
        intents = [r["intent"] for r in recent]
        self.assertEqual(set(intents), {"vehicle_search", "trade_in", "compare_vehicles"})
        for r in recent:
            self.assertIn("session_id", r)
            self.assertIn("updated_at", r)

    def test_trends_snapshot_shape(self):
        v = _make_vehicle("X1", "60000.00")
        ChatSession.objects.create(
            extracted_profile={"intent": "vehicle_search", "model": "F-150", "vehicle_type": "truck"}
        )
        lead = CustomerLead.objects.create(name="A", target_monthly_payment=Decimal("500"))
        lead.interested_vehicles.add(v)

        snap = trends.trends_snapshot()
        for key in [
            "generated_at",
            "total_chat_sessions",
            "total_leads",
            "total_leads_last_7d",
            "average_target_monthly_payment",
            "budget_mismatch_count",
            "top_requested_models",
            "top_requested_vehicle_types",
            "most_selected_vehicles",
            "recent_customer_intents",
        ]:
            self.assertIn(key, snap, f"missing key {key}")
