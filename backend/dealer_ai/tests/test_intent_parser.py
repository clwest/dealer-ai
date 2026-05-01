"""Intent extraction + profile-merge tests.

These never call a real LLM — they use MockLLMProvider with scripted JSON.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from dealer_ai.services.intent_parser import (
    PROFILE_FIELDS,
    merge_profile,
    parse_intent,
    regex_extract,
)

from ._mocks import MockLLMProvider, json_reply


class RegexExtractTests(SimpleTestCase):
    def test_extracts_monthly_payment(self):
        out = regex_extract("I'd like a truck around $500/month with $2,000 down")
        self.assertEqual(out["target_monthly_payment"], 500)
        self.assertEqual(out["down_payment"], 2000)

    def test_extracts_vehicle_type_and_intent(self):
        out = regex_extract("Show me an SUV under $40k")
        self.assertEqual(out["vehicle_type"], "suv")
        self.assertEqual(out["intent"], "vehicle_search")

    def test_detects_compare_intent(self):
        out = regex_extract("Can you compare a Maverick vs an Escape?")
        self.assertEqual(out["intent"], "compare_vehicles")
        self.assertEqual(out["model"], "Maverick")

    def test_detects_used_condition(self):
        out = regex_extract("looking for a used F-150")
        self.assertEqual(out["condition"], "used")
        self.assertEqual(out["model"], "F-150")
        self.assertEqual(out["make"], "Ford")

    def test_detects_immediate_urgency(self):
        out = regex_extract("I need something today, ready to buy")
        self.assertEqual(out["urgency"], "immediate")

    def test_empty_message_returns_empty(self):
        self.assertEqual(regex_extract(""), {})
        self.assertEqual(regex_extract("   "), {})


class ParseIntentTests(SimpleTestCase):
    def test_regex_only_when_use_llm_false(self):
        out = parse_intent("Show me trucks under $40k", use_llm=False)
        self.assertEqual(out.get("vehicle_type"), "truck")
        # No LLM call → no other fields beyond regex hits.

    def test_llm_supplements_regex(self):
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "vehicle_type": "truck",
                        "credit_range": "good",
                        "financing_interest": True,
                    }
                )
            ]
        )
        out = parse_intent(
            "Looking at trucks around $600/month with $3,000 down, my credit's solid",
            provider=provider,
        )
        # Regex wins on numeric fields.
        self.assertEqual(out["target_monthly_payment"], 600)
        self.assertEqual(out["down_payment"], 3000)
        # LLM fills in everything else.
        self.assertEqual(out["intent"], "vehicle_search")
        self.assertEqual(out["credit_range"], "good")
        self.assertTrue(out["financing_interest"])

    def test_llm_returns_garbage_does_not_break(self):
        provider = MockLLMProvider(replies=["sorry I cannot do that"])
        out = parse_intent("Show me an SUV", provider=provider)
        # Regex pass still works.
        self.assertEqual(out["vehicle_type"], "suv")

    def test_llm_returns_fenced_json_is_parsed(self):
        provider = MockLLMProvider(
            replies=["```json\n{\"intent\": \"trade_in\"}\n```"]
        )
        out = parse_intent("How much is my 2018 Escape worth?", provider=provider)
        self.assertEqual(out["intent"], "trade_in")

    def test_invalid_enum_values_dropped(self):
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "buy_a_house",  # not a valid intent
                        "urgency": "yesterday",  # not a valid urgency
                        "vehicle_type": "spaceship",  # not valid
                    }
                )
            ]
        )
        out = parse_intent("hi", provider=provider)
        self.assertNotIn("intent", out)
        self.assertNotIn("urgency", out)
        self.assertNotIn("vehicle_type", out)

    def test_only_known_fields_returned(self):
        provider = MockLLMProvider(
            replies=[json_reply({"intent": "vehicle_search", "secret": "x"})]
        )
        out = parse_intent("show me a truck", provider=provider)
        for key in out:
            self.assertIn(key, PROFILE_FIELDS)


class MergeProfileTests(SimpleTestCase):
    def test_merges_new_into_empty(self):
        merged = merge_profile({}, {"intent": "vehicle_search"})
        self.assertEqual(merged, {"intent": "vehicle_search"})

    def test_does_not_drop_existing_when_new_omits(self):
        existing = {"target_monthly_payment": 500, "vehicle_type": "truck"}
        merged = merge_profile(existing, {"intent": "compare_vehicles"})
        self.assertEqual(merged["target_monthly_payment"], 500)
        self.assertEqual(merged["vehicle_type"], "truck")
        self.assertEqual(merged["intent"], "compare_vehicles")

    def test_new_value_wins_when_provided(self):
        existing = {"target_monthly_payment": 500}
        merged = merge_profile(existing, {"target_monthly_payment": 650})
        self.assertEqual(merged["target_monthly_payment"], 650)

    def test_empty_values_in_new_do_not_overwrite(self):
        existing = {"target_monthly_payment": 500, "model": "F-150"}
        merged = merge_profile(
            existing, {"target_monthly_payment": None, "model": "", "intent": "vehicle_search"}
        )
        self.assertEqual(merged["target_monthly_payment"], 500)
        self.assertEqual(merged["model"], "F-150")
        self.assertEqual(merged["intent"], "vehicle_search")

    def test_unknown_keys_filtered(self):
        merged = merge_profile({}, {"intent": "vehicle_search", "rogue": 42})
        self.assertNotIn("rogue", merged)

    def test_none_existing_treated_as_empty(self):
        merged = merge_profile(None, {"intent": "vehicle_search"})
        self.assertEqual(merged, {"intent": "vehicle_search"})
