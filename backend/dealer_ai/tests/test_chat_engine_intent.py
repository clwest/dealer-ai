"""Verify ChatEngine wires intent extraction into the session profile."""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.models import ChatSession
from dealer_ai.services.chat_engine import ChatEngine

from ._mocks import MockLLMProvider, json_reply


class ChatEnginePersistsExtractedProfileTests(TestCase):
    def test_first_turn_writes_profile(self):
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "vehicle_type": "truck",
                        "credit_range": "good",
                    }
                ),
                "Sounds good — here are some F-150 options.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Looking for an F-150 around $600/month with $3,000 down"
        )

        session.refresh_from_db()
        profile = session.extracted_profile
        self.assertEqual(profile["intent"], "vehicle_search")
        self.assertEqual(profile["vehicle_type"], "truck")
        self.assertEqual(profile["target_monthly_payment"], 600)
        self.assertEqual(profile["down_payment"], 3000)
        self.assertEqual(profile["model"], "F-150")
        self.assertEqual(profile["credit_range"], "good")
        # The engine returns the merged profile too.
        self.assertEqual(result.extracted_profile, profile)

    def test_second_turn_merges_without_dropping(self):
        session = ChatSession.objects.create(
            extracted_profile={
                "intent": "vehicle_search",
                "target_monthly_payment": 500,
                "vehicle_type": "truck",
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"urgency": "this_week"}),
                "Got it.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("I want to buy this week")

        session.refresh_from_db()
        profile = session.extracted_profile
        # Original fields preserved.
        self.assertEqual(profile["target_monthly_payment"], 500)
        self.assertEqual(profile["vehicle_type"], "truck")
        # New field added.
        self.assertEqual(profile["urgency"], "this_week")
