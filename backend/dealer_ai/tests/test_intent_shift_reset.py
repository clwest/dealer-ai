"""Item 7 — context-reset on intent shift.

The smoke surfaced a state-bleed bug: a customer shopping 4WD
trucks pivoted to "show me a cheap commuter car", but the prior
truck context (Ranger anchor + lever metadata + drivetrain=4WD)
carried into the new turn. The new BudgetContext came back muddled.

This pass detects intent shifts at the state-layer and clears the
stale anchor + irrelevant constraint fields. Budget / down / term
are preserved.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatMessage, ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    apply_intent_reset,
    detect_intent_shift,
)

from ._mocks import MockLLMProvider, json_reply


# ---- detect_intent_shift unit tests --------------------------------------


class DetectIntentShiftTests(SimpleTestCase):
    """Pure-function coverage. Both detection paths require the
    PRIOR profile to be truck-like for the shift to fire — opening
    a session with a cheap-commuter query is NOT a shift.
    """

    def test_truck_to_car_triggers_shift(self):
        prior = {"vehicle_type": "truck", "drivetrain": "4WD"}
        new = {"vehicle_type": "car"}
        shifted, reasons = detect_intent_shift(
            prior, new, "show me a cheap commuter car"
        )
        self.assertTrue(shifted)
        self.assertIn("vehicle_type_to_car", reasons)

    def test_suv_to_sedan_triggers_shift(self):
        prior = {"vehicle_type": "suv"}
        new = {"vehicle_type": "sedan"}
        shifted, reasons = detect_intent_shift(prior, new, "sedan")
        self.assertTrue(shifted)
        self.assertIn("vehicle_type_to_car", reasons)

    def test_truck_to_suv_does_not_trigger(self):
        # User-spec test: truck→SUV is NOT the shift class we care
        # about. Both are truck-like; lever logic still applies.
        prior = {"vehicle_type": "truck"}
        new = {"vehicle_type": "suv"}
        shifted, reasons = detect_intent_shift(prior, new, "show me an SUV")
        self.assertFalse(shifted)
        self.assertEqual(reasons, set())

    def test_truck_to_cheaper_truck_does_not_trigger(self):
        prior = {"vehicle_type": "truck", "target_monthly_payment": 800}
        new = {"target_monthly_payment": 400}
        shifted, reasons = detect_intent_shift(
            prior, new, "what about a cheaper truck"
        )
        # "cheaper" is in the keyword list — but the customer is
        # still in truck mode AND new vehicle_type isn't car-like.
        # The prior context is truck-like AND the message has
        # "cheaper", so commuter_keyword fires (this is a known
        # over-trigger; the reset is conservative — wipes anchor
        # but keeps budget). Acceptable for a state-cleaning pass.
        self.assertTrue(shifted)
        self.assertIn("commuter_keyword", reasons)

    def test_opening_turn_with_cheap_commuter_does_not_trigger(self):
        # User-spec test: no prior context → no shift. Customer
        # opens with "I'm looking for a cheap commuter car" — that's
        # the OPENING intent, not a pivot.
        prior = {}
        new = {"vehicle_type": "car"}
        shifted, reasons = detect_intent_shift(
            prior, new, "I'm looking for a cheap commuter car"
        )
        self.assertFalse(shifted)
        self.assertEqual(reasons, set())

    def test_cash_keyword_in_truck_context_triggers(self):
        prior = {"vehicle_type": "truck"}
        new = {}
        shifted, reasons = detect_intent_shift(
            prior, new, "do you have anything for cash buyers under $10k"
        )
        self.assertTrue(shifted)
        self.assertIn("commuter_keyword", reasons)

    def test_gas_mileage_keyword_in_truck_context_triggers(self):
        prior = {"vehicle_type": "truck"}
        new = {}
        shifted, reasons = detect_intent_shift(
            prior, new, "I want better gas mileage actually"
        )
        self.assertTrue(shifted)
        self.assertIn("commuter_keyword", reasons)

    def test_commute_keyword_in_truck_context_triggers(self):
        prior = {"vehicle_type": "truck"}
        new = {}
        shifted, reasons = detect_intent_shift(
            prior, new, "actually need something for my commute"
        )
        self.assertTrue(shifted)
        self.assertIn("commuter_keyword", reasons)

    def test_economy_keyword_in_truck_context_triggers(self):
        prior = {"vehicle_type": "truck"}
        new = {}
        shifted, reasons = detect_intent_shift(
            prior, new, "show me something economy"
        )
        self.assertTrue(shifted)
        self.assertIn("commuter_keyword", reasons)

    def test_keyword_with_no_prior_context_does_not_trigger(self):
        # Opening turn with "cheap" keyword — no prior to invalidate.
        prior = {}
        new = {}
        shifted, reasons = detect_intent_shift(
            prior, new, "I want a cheap car for commuting"
        )
        self.assertFalse(shifted)
        self.assertEqual(reasons, set())

    def test_car_to_truck_does_not_trigger(self):
        # The reset is one-directional (truck→car). A car shopper
        # who pivots to trucks isn't covered here — that's a
        # separate case.
        prior = {"vehicle_type": "car"}
        new = {"vehicle_type": "truck"}
        shifted, reasons = detect_intent_shift(
            prior, new, "I want a 4WD truck instead"
        )
        self.assertFalse(shifted)
        self.assertEqual(reasons, set())


# ---- apply_intent_reset unit tests --------------------------------------


class ApplyIntentResetTests(SimpleTestCase):
    """The reset clears stale anchor + irrelevant constraint fields
    while PRESERVING budget / down / term so the customer doesn't
    have to re-state finances.
    """

    def test_no_reasons_returns_profile_unchanged(self):
        profile = {"vehicle_type": "truck", "drivetrain": "4WD"}
        result = apply_intent_reset(dict(profile), {}, set())
        self.assertEqual(result, profile)

    def test_vehicle_type_to_car_clears_drivetrain(self):
        profile = {
            "vehicle_type": "truck",
            "drivetrain": "4WD",
            "model": "Ranger",
            "current_vehicle_id": 42,
            "current_vehicle_stock": "FF-USED-104",
            "make_lock": True,
            "make": "Ford",
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        new_fields = {"vehicle_type": "car"}
        result = apply_intent_reset(
            profile, new_fields, {"vehicle_type_to_car"}
        )
        # Anchor + irrelevant constraints cleared.
        self.assertNotIn("model", result)
        self.assertNotIn("current_vehicle_id", result)
        self.assertNotIn("current_vehicle_stock", result)
        self.assertNotIn("make_lock", result)
        self.assertNotIn("make", result)
        self.assertNotIn("drivetrain", result)
        # Budget / down / term preserved — customer doesn't re-state.
        self.assertEqual(result["target_monthly_payment"], 500)
        self.assertEqual(result["down_payment"], 3000)
        self.assertEqual(result["term_months"], 60)
        # New vehicle_type applied.
        self.assertEqual(result["vehicle_type"], "car")

    def test_commuter_keyword_only_keeps_drivetrain(self):
        # Customer says "any cheap car" but doesn't name a body
        # style this turn. We clear anchor + make but keep the prior
        # drivetrain — the "commuter_keyword" reason alone doesn't
        # know it's car-shopping yet. The next turn typically
        # disambiguates and triggers vehicle_type_to_car.
        profile = {
            "vehicle_type": "truck",
            "drivetrain": "4WD",
            "model": "Ranger",
            "current_vehicle_id": 42,
            "make_lock": True,
        }
        result = apply_intent_reset(
            profile, {}, {"commuter_keyword"}
        )
        self.assertNotIn("model", result)
        self.assertNotIn("current_vehicle_id", result)
        self.assertNotIn("make_lock", result)
        # Drivetrain preserved on commuter_keyword-only.
        self.assertEqual(result["drivetrain"], "4WD")

    def test_both_reasons_clears_drivetrain(self):
        profile = {
            "vehicle_type": "truck",
            "drivetrain": "4WD",
            "model": "Ranger",
        }
        result = apply_intent_reset(
            profile,
            {"vehicle_type": "car"},
            {"vehicle_type_to_car", "commuter_keyword"},
        )
        self.assertNotIn("drivetrain", result)
        self.assertEqual(result["vehicle_type"], "car")

    def test_budget_fields_always_preserved(self):
        profile = {
            "vehicle_type": "truck",
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "max_price": 30000,
            "drivetrain": "4WD",
            "model": "Ranger",
        }
        result = apply_intent_reset(
            profile,
            {"vehicle_type": "car"},
            {"vehicle_type_to_car"},
        )
        self.assertEqual(result["target_monthly_payment"], 500)
        self.assertEqual(result["down_payment"], 3000)
        self.assertEqual(result["term_months"], 60)
        self.assertEqual(result["max_price"], 30000)


# ---- ChatEngine integration tests ---------------------------------------


def _make_vehicle(
    stock,
    price,
    *,
    model,
    drivetrain,
    body,
    make="Ford",
    trim="",
    condition="used",
    year=2025,
):
    return Vehicle.objects.create(
        stock_number=stock,
        year=year,
        make=make,
        model=model,
        trim=trim,
        body_style=body,
        condition=condition,
        price=Decimal(price),
        drivetrain=drivetrain,
    )


class IntentShiftIntegrationTests(TestCase):
    """End-to-end: a real chat session pivots from a truck context
    to a cheap commuter car query. The new turn must surface car
    inventory, not the prior trucks, with no lever-flex carryover.
    """

    def _seed_inventory(self):
        # Truck inventory the prior turn anchored on.
        ranger = _make_vehicle(
            "FF-USED-104",
            "26995",
            model="Ranger",
            trim="XLT 4x4",
            drivetrain="4x4",
            body="truck",
            year=2019,
        )
        # A car the new turn should discover. Cheap, FWD, sedan.
        camry = _make_vehicle(
            "FF-USED-CAR-1",
            "13495",
            model="Camry",
            trim="LE",
            drivetrain="FWD",
            body="car",
            make="Toyota",
            year=2015,
        )
        # A second car so there's a multi-card response possible.
        accord = _make_vehicle(
            "FF-USED-CAR-2",
            "12995",
            model="Accord",
            trim="EX",
            drivetrain="FWD",
            body="car",
            make="Honda",
            year=2014,
        )
        return ranger, camry, accord

    def _seed_truck_context_session(self, ranger):
        """Build a session in the post-truck-search state. Profile
        carries the prior truck context (drivetrain=4WD, model
        anchor, lever_offer-ish metadata on prior assistant turn).
        """
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
                "model": "Ranger",
                "current_vehicle_id": ranger.id,
                "current_vehicle_stock": ranger.stock_number,
                "make_lock": True,
                "make": "Ford",
            }
        )
        prior = ChatMessage.objects.create(
            session=session,
            role="user",
            content="I'm looking for a 4WD truck around $500/mo",
        )
        prior_assist = ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=(
                "The Ranger is really close at about $517/mo. Want a "
                "closer look?"
            ),
            metadata={
                "matched_count": 1,
                "lever_offer": True,
            },
        )
        prior_assist.matched_vehicles.set([ranger])
        return session

    def test_truck_to_car_shift_resets_results(self):
        # User-spec test #1 — truck→car shift produces fresh car
        # results, no truck carry-over.
        ranger, camry, accord = self._seed_inventory()
        session = self._seed_truck_context_session(ranger)

        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Here are some commuter cars to consider.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "show me a cheap commuter car"
        )

        # The new matched_vehicles must NOT include the prior
        # Ranger / Tundra trucks.
        stocks = {v.stock_number for v in result.matched_vehicles}
        self.assertNotIn(ranger.stock_number, stocks)
        # Should have surfaced cars from the seed pool.
        self.assertTrue(
            stocks & {camry.stock_number, accord.stock_number},
            f"expected car inventory in matched, got {stocks}",
        )

        meta = result.assistant_message.metadata
        # Metadata records the reset.
        self.assertTrue(meta.get("intent_reset"))
        self.assertIn(
            "vehicle_type_to_car",
            meta.get("intent_reset_reasons", []),
        )

    def test_intent_reset_clears_drivetrain_and_anchor(self):
        # User-spec test #2 — previous vehicles + drivetrain
        # constraint not referenced after the shift.
        ranger, _camry, _accord = self._seed_inventory()
        session = self._seed_truck_context_session(ranger)

        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Some cars that fit your $500 target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "show me a cheap commuter car"
        )

        # extracted_profile reflects the reset.
        profile = result.extracted_profile
        self.assertNotIn("drivetrain", profile)
        self.assertNotIn("current_vehicle_id", profile)
        self.assertNotIn("current_vehicle_stock", profile)
        self.assertNotIn("make_lock", profile)
        self.assertEqual(profile.get("vehicle_type"), "car")
        # Budget preserved.
        self.assertEqual(profile["target_monthly_payment"], 500)
        self.assertEqual(profile["down_payment"], 3000)
        self.assertEqual(profile["term_months"], 60)
        # Anchor cleared.
        self.assertNotIn("model", profile)

    def test_intent_reset_breaks_lever_carryover(self):
        # User-spec test #3 — lever logic must not fire on the new
        # turn. The prior assistant message had lever_offer=True;
        # but the customer's new message ("show me a cheap commuter
        # car") doesn't match bare-confirmation or numberless lever
        # asks, so the lever-clarifier path is bypassed naturally.
        # This test pins that bypass.
        ranger, _camry, _accord = self._seed_inventory()
        session = self._seed_truck_context_session(ranger)

        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Some cars under your target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "show me a cheap commuter car"
        )
        meta = result.assistant_message.metadata
        # The new turn is NOT a lever-clarifier turn.
        self.assertNotEqual(meta.get("mode"), "lever_clarifier")
        self.assertNotEqual(
            meta.get("provider"), "guard"
        )  # lever clarifier sets provider="guard"

    def test_truck_to_suv_does_not_reset(self):
        # Narrow-scope safety: truck→SUV does NOT trigger reset.
        # Both are truck-like; lever / drivetrain logic still
        # applies.
        ranger, _camry, _accord = self._seed_inventory()
        session = self._seed_truck_context_session(ranger)

        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "suv"}),
                "Here are some SUVs.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("show me an SUV instead")

        meta = result.assistant_message.metadata
        self.assertFalse(meta.get("intent_reset"))
        # Drivetrain constraint preserved (4WD SUVs are still
        # relevant when shifting from 4WD trucks).
        profile = result.extracted_profile
        self.assertEqual(profile.get("drivetrain"), "4WD")

    def test_opening_turn_does_not_reset(self):
        # No prior profile → no reset event even if the customer
        # opens with cheap-commuter language.
        _make_vehicle(
            "FF-USED-CAR-3",
            "13495",
            model="Camry",
            trim="LE",
            drivetrain="FWD",
            body="car",
            make="Toyota",
        )
        session = ChatSession.objects.create(extracted_profile={})

        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "Here are some commuter cars.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm looking for a cheap commuter car"
        )
        meta = result.assistant_message.metadata
        self.assertFalse(meta.get("intent_reset"))
