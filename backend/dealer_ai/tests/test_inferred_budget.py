"""Item 8 — weak-intent / cash-budget bootstrap.

The bug: customer says *"cheap car, good gas mileage, pay cash"* —
strong intent signals but no monthly payment / max_price → the
discovery gate fires and the customer never sees inventory.

The fix: when both a CASH signal and a COMMUTER signal are present
AND the profile has no explicit budget, soft-infer max_price=$15k
so the keyword-search path can surface inventory. Customer can
tighten on a later turn.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    _INFERRED_BUDGET_DEFAULT_MAX,
    _should_enter_discovery_mode,
    detect_cash_commuter_intent,
    infer_budget_from_intent,
)

from ._mocks import MockLLMProvider, json_reply


# ---- detect_cash_commuter_intent unit tests -----------------------------


class DetectCashCommuterIntentTests(SimpleTestCase):
    def test_pay_cash_detected(self):
        result = detect_cash_commuter_intent("I want to pay cash")
        self.assertTrue(result["cash"])

    def test_paying_cash_detected(self):
        result = detect_cash_commuter_intent(
            "looking for something I can pay cash for"
        )
        self.assertTrue(result["cash"])

    def test_cash_deal_detected(self):
        result = detect_cash_commuter_intent(
            "do you have any cash deal options"
        )
        self.assertTrue(result["cash"])

    def test_cash_buyer_detected(self):
        result = detect_cash_commuter_intent(
            "I'm a cash buyer"
        )
        self.assertTrue(result["cash"])

    def test_bare_cash_word_detected(self):
        result = detect_cash_commuter_intent(
            "cheap car cash"
        )
        self.assertTrue(result["cash"])

    def test_cheap_detected_as_commuter(self):
        result = detect_cash_commuter_intent("cheap car please")
        self.assertTrue(result["commuter"])

    def test_gas_mileage_detected_as_commuter(self):
        result = detect_cash_commuter_intent(
            "I want good gas mileage"
        )
        self.assertTrue(result["commuter"])

    def test_fuel_economy_detected_as_commuter(self):
        result = detect_cash_commuter_intent(
            "fuel economy is important"
        )
        self.assertTrue(result["commuter"])

    def test_commute_detected(self):
        result = detect_cash_commuter_intent(
            "need it for my commute"
        )
        self.assertTrue(result["commuter"])

    def test_economy_detected(self):
        result = detect_cash_commuter_intent("show me an economy car")
        self.assertTrue(result["commuter"])

    def test_neither_signal_in_truck_query(self):
        result = detect_cash_commuter_intent(
            "4WD truck around $500/mo with $3k down"
        )
        self.assertFalse(result["cash"])
        self.assertFalse(result["commuter"])

    def test_empty_text_no_signals(self):
        self.assertEqual(
            detect_cash_commuter_intent(""),
            {"cash": False, "commuter": False},
        )

    def test_combined_signals_in_one_message(self):
        result = detect_cash_commuter_intent(
            "cheap car, good gas mileage, pay cash"
        )
        self.assertTrue(result["cash"])
        self.assertTrue(result["commuter"])


# ---- infer_budget_from_intent unit tests --------------------------------


class InferBudgetFromIntentTests(SimpleTestCase):
    def test_both_signals_no_prior_budget_triggers(self):
        result = infer_budget_from_intent(
            {}, "cheap car cash"
        )
        self.assertIsNotNone(result)
        self.assertEqual(
            result["max_price"], _INFERRED_BUDGET_DEFAULT_MAX
        )
        self.assertEqual(result["vehicle_type"], "car")

    def test_only_cash_signal_does_not_trigger(self):
        result = infer_budget_from_intent(
            {}, "I'd like to pay cash"
        )
        self.assertIsNone(result)

    def test_only_commuter_signal_does_not_trigger(self):
        result = infer_budget_from_intent(
            {}, "show me a cheap car"
        )
        self.assertIsNone(result)

    def test_existing_target_monthly_blocks_inference(self):
        # The customer explicitly named a budget — don't override.
        result = infer_budget_from_intent(
            {"target_monthly_payment": 500},
            "cheap car cash",
        )
        self.assertIsNone(result)

    def test_existing_max_price_blocks_inference(self):
        result = infer_budget_from_intent(
            {"max_price": 12000},
            "cheap commuter car cash",
        )
        self.assertIsNone(result)

    def test_existing_vehicle_type_preserved(self):
        # Customer already named SUV — don't overwrite with "car".
        result = infer_budget_from_intent(
            {"vehicle_type": "suv"},
            "cheap commuter cash",
        )
        self.assertIsNotNone(result)
        # max_price still applied.
        self.assertEqual(
            result["max_price"], _INFERRED_BUDGET_DEFAULT_MAX
        )
        # vehicle_type NOT in result (so update() won't change it).
        self.assertNotIn("vehicle_type", result)

    def test_default_max_price_15000(self):
        result = infer_budget_from_intent(
            {}, "cheap car gas mileage cash"
        )
        self.assertEqual(result["max_price"], 15000.0)

    def test_custom_default_max_price(self):
        result = infer_budget_from_intent(
            {}, "cheap commuter cash",
            default_max_price=10000.0,
        )
        self.assertEqual(result["max_price"], 10000.0)


# ---- _should_enter_discovery_mode update --------------------------------


class DiscoveryGateMaxPriceTests(SimpleTestCase):
    """Item 8 — profile.max_price now blocks discovery mode so the
    inferred budget actually surfaces inventory.
    """

    def test_profile_max_price_blocks_discovery(self):
        # Without max_price the gate WOULD fire (vehicle_type
        # alone is enough to enter discovery).
        without = _should_enter_discovery_mode(
            "show me cars",
            {"vehicle_type": "car"},
            {},
        )
        self.assertTrue(without)
        # With max_price the gate is bypassed — keyword search can
        # surface inventory.
        with_max = _should_enter_discovery_mode(
            "show me cars",
            {"vehicle_type": "car", "max_price": 15000},
            {},
        )
        self.assertFalse(with_max)


# ---- ChatEngine integration tests ---------------------------------------


def _seed_cars():
    """Seed a small set of cars + a truck to ensure the inferred
    max_price actually filters out the truck."""
    Vehicle.objects.create(
        stock_number="CAR-1",
        year=2014,
        make="Honda",
        model="Accord",
        body_style="car",
        condition="used",
        price=Decimal("12995"),
        drivetrain="FWD",
    )
    Vehicle.objects.create(
        stock_number="CAR-2",
        year=2015,
        make="Toyota",
        model="Camry",
        body_style="car",
        condition="used",
        price=Decimal("13495"),
        drivetrain="FWD",
    )
    Vehicle.objects.create(
        stock_number="CAR-3",
        year=2017,
        make="Hyundai",
        model="Sonata",
        body_style="car",
        condition="used",
        price=Decimal("10995"),
        drivetrain="FWD",
    )
    # Out of budget — should NOT surface.
    Vehicle.objects.create(
        stock_number="CAR-EXP",
        year=2020,
        make="Toyota",
        model="Camry",
        body_style="car",
        condition="used",
        price=Decimal("22995"),
        drivetrain="FWD",
    )
    Vehicle.objects.create(
        stock_number="TRUCK-1",
        year=2025,
        make="Ford",
        model="F-150",
        body_style="truck",
        condition="new",
        price=Decimal("65000"),
        drivetrain="4x4",
    )


class InferredBudgetIntegrationTests(TestCase):
    def test_cheap_commuter_cash_returns_vehicles(self):
        # User-spec test #1 — "cheap commuter car cash" returns
        # vehicles instead of falling back to discovery mode.
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Here are some commuter cars.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap commuter car, good gas mileage, pay cash"
        )

        # Vehicles surfaced (not discovery mode).
        self.assertGreater(
            len(list(result.matched_vehicles)),
            0,
            "Should have surfaced car inventory under the inferred "
            "$15k ceiling.",
        )
        meta = result.assistant_message.metadata
        self.assertNotEqual(meta.get("mode"), "discovery")
        # Inferred budget metadata flag set.
        self.assertTrue(meta.get("inferred_budget"))

    def test_inferred_max_price_filters_inventory(self):
        # User-spec test #4 — cars selected are lower-price-range
        # (under the inferred $15k ceiling), pricier cars + trucks
        # excluded.
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Some commuter cars.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap commuter car, gas mileage, cash"
        )
        stocks = {v.stock_number for v in result.matched_vehicles}
        # The $22k Camry and $65k F-150 must NOT surface.
        self.assertNotIn("CAR-EXP", stocks)
        self.assertNotIn("TRUCK-1", stocks)
        # At least one of the cheap cars surfaced.
        self.assertTrue(
            stocks & {"CAR-1", "CAR-2", "CAR-3"},
            f"expected cheap cars in matched, got {stocks}",
        )

    def test_inferred_budget_persists_to_profile(self):
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Some cars under $15k.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash, fuel economy"
        )
        profile = result.extracted_profile
        # max_price persisted at the inferred default.
        self.assertEqual(profile.get("max_price"), 15000.0)
        # vehicle_type set to "car" since none was explicitly
        # named (parse_intent extracts it from "car" in text too,
        # but the inference is the safety net).
        self.assertEqual(profile.get("vehicle_type"), "car")

    def test_explicit_target_monthly_overrides_inference(self):
        # User-spec safety: an explicit budget the customer named
        # wins. The inference should NOT override.
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {"vehicle_type": "car", "target_monthly_payment": 250}
                ),
                "Some cars at $250/mo.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap commuter car cash around $250/mo"
        )
        meta = result.assistant_message.metadata
        # Inferred budget did NOT fire — explicit target wins.
        self.assertFalse(meta.get("inferred_budget"))
        # No max_price applied — the budget pipeline runs against
        # target_monthly_payment instead.
        self.assertIsNone(result.extracted_profile.get("max_price"))

    def test_single_signal_alone_does_not_infer(self):
        # User-spec safety: only "cash" → no inference. Customer
        # might say "cash" in passing without commuter intent.
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Need more info."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'd like to pay cash for an SUV"
        )
        meta = result.assistant_message.metadata
        self.assertFalse(meta.get("inferred_budget"))

    def test_discovery_mode_blocked_when_inferred(self):
        # User-spec test #3 — no generic "need more info" advice.
        # The discovery gate must NOT fire when the inferred
        # max_price is in profile.
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Cars under $15k.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash, good gas mileage"
        )
        meta = result.assistant_message.metadata
        # Mode is NOT discovery.
        self.assertNotEqual(meta.get("mode"), "discovery")
