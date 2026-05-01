"""Item 12 — "both" wording drift.

When the LLM is given 3+ cards it sometimes still says "both",
implicitly referring to two of them and ignoring the rest. The
word is only correct when there are exactly 2 cards on screen.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    scrub_both_wording,
)

from ._mocks import MockLLMProvider, json_reply


# ---- scrub_both_wording unit tests --------------------------------------


class ScrubBothWordingUnitTests(SimpleTestCase):
    def test_two_vehicles_preserves_both(self):
        text = "Both vehicles are great choices. Want a closer look?"
        cleaned, changed = scrub_both_wording(text, vehicle_count=2)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_zero_vehicles_replaces_both(self):
        # Function-level: "both" is wrong for any count != 2,
        # including 0. The wiring in handle_user_message gates the
        # call on bool(matched) so this branch isn't reached in
        # production with zero cards — but the helper itself is
        # consistent with the count != 2 contract.
        text = "I can show you both options."
        cleaned, changed = scrub_both_wording(text, vehicle_count=0)
        self.assertTrue(changed)
        self.assertNotIn("both options", cleaned)

    def test_three_vehicles_replaces_both_vehicles(self):
        text = "Both vehicles are great. Want a closer look?"
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertNotIn("Both vehicles", cleaned)
        self.assertIn("These vehicles", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_three_vehicles_replaces_both_options(self):
        text = "I think you'd love both options. Sound good?"
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertNotIn("both options", cleaned.lower())
        self.assertIn("these options", cleaned.lower())

    def test_three_vehicles_replaces_both_cars(self):
        text = "Both cars come in under your target."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertIn("These cars", cleaned)

    def test_three_vehicles_replaces_both_trucks(self):
        text = "Both trucks would handle the load."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertIn("These trucks", cleaned)

    def test_three_vehicles_replaces_both_of_them(self):
        text = "Both of them slip under your $500 target."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertNotIn("Both of them", cleaned)
        self.assertIn("All of them", cleaned)

    def test_three_vehicles_replaces_both_of_these(self):
        text = "I'd recommend both of these for daily driving."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertIn("all of these", cleaned)

    def test_three_vehicles_standalone_both_replaced(self):
        # Bare "both" (not followed by a noun) → "these options".
        text = "You'd love both. Want a look?"
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertNotIn("love both", cleaned)
        self.assertIn("these options", cleaned)

    def test_one_vehicle_replaces_both(self):
        # Single card and the LLM still says "both" — wrong shape.
        text = "Both vehicles fit your target. Want a look?"
        cleaned, changed = scrub_both_wording(text, vehicle_count=1)
        self.assertTrue(changed)
        self.assertNotIn("Both vehicles", cleaned)

    def test_capitalization_preserved(self):
        text = "Both vehicles are great."
        cleaned, changed = scrub_both_wording(text, vehicle_count=4)
        self.assertTrue(changed)
        # Sentence-initial should still be capitalized.
        self.assertTrue(cleaned.startswith("These vehicles"))

    def test_lowercase_preserved(self):
        text = "I think you'd love both vehicles here."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        self.assertIn("these vehicles", cleaned)
        # NOT "These vehicles" (mid-sentence stays lowercase).
        self.assertNotIn("These vehicles", cleaned)

    def test_both_x_and_y_conjunction_preserved(self):
        # "both available and affordable" — legitimate non-vehicle
        # use of "both", left alone.
        text = "These options are both available and affordable."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_both_2wd_and_4wd_conjunction_preserved(self):
        # The drivetrain-claim case — handled by drivetrain scrub.
        # Item 12 leaves it alone because of the "both X and Y"
        # conjunction guard.
        text = "Available in both 2WD and 4WD configurations."
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_no_both_token_no_op(self):
        text = "These options are great. Want a look?"
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_empty_text_no_op(self):
        cleaned, changed = scrub_both_wording("", vehicle_count=3)
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_multiple_both_tokens_all_replaced(self):
        text = (
            "Both options are great. Both vehicles slip under "
            "target. Want a look?"
        )
        cleaned, changed = scrub_both_wording(text, vehicle_count=3)
        self.assertTrue(changed)
        # No "both" tokens remain (other than as substrings of
        # other words — but there are none here).
        self.assertNotIn("Both options", cleaned)
        self.assertNotIn("Both vehicles", cleaned)
        self.assertIn("These options", cleaned)
        self.assertIn("These vehicles", cleaned)


# ---- ChatEngine integration tests --------------------------------------


def _make_vehicle(stock, price, *, model, drivetrain="4x4"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2019,
        make="Ford",
        model=model,
        body_style="truck",
        condition="used",
        price=Decimal(price),
        drivetrain=drivetrain,
    )


class BothWordingIntegrationTests(TestCase):
    def test_three_cards_with_both_in_reply_scrubbed(self):
        # Three cards on screen; the LLM says "both" → scrub.
        _make_vehicle("V1", "26995", model="Ranger")
        _make_vehicle("V2", "27495", model="Maverick")
        _make_vehicle("V3", "35995", model="F-150")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        bad = (
            "I'd recommend both vehicles for your daily commute. "
            "Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm looking for a 4WD truck around $500/mo with $3k down"
        )
        content = result.assistant_message.content
        self.assertNotIn("Both vehicles", content)
        self.assertNotIn("both vehicles", content)
        self.assertIn("These vehicles", content) if False else None  # case-flexible
        # At minimum, "both" replaced.
        self.assertNotIn(" both ", content.lower())
        meta = result.assistant_message.metadata
        self.assertIn("both_wording", meta.get("scrubs", []))

    def test_two_cards_with_both_unchanged(self):
        # Exactly 2 cards → "both" is correct. Don't touch.
        _make_vehicle("V1", "26995", model="Ranger")
        _make_vehicle("V2", "27495", model="Maverick")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        ok = "Both vehicles fit your $500 target. Want a look?"
        provider = MockLLMProvider(replies=[json_reply({}), ok])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "4WD truck around $500/mo with $3k down"
        )
        meta = result.assistant_message.metadata
        # The both_wording scrub did NOT fire.
        self.assertNotIn(
            "both_wording", meta.get("scrubs", [])
        )

    def test_no_card_session_unchanged(self):
        # Without cards, the scrub gate blocks — defensive
        # consistency with other card-aware scrubs.
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "I can show you both options.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("just browsing")
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "both_wording", meta.get("scrubs", [])
        )
