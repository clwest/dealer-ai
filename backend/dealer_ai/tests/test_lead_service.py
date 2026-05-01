"""End-to-end test for lead creation with summary + next-action generation."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatMessage, ChatSession, CustomerLead, Vehicle
from dealer_ai.services.lead_service import create_lead_from_session

from ._mocks import MockLLMProvider


def _make_vehicle(stock="FF-T-001", price="65000.00", model="F-150"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        trim="XLT",
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _seed_session_with_chat(profile=None):
    session = ChatSession.objects.create(extracted_profile=profile or {})
    ChatMessage.objects.create(
        session=session,
        role="user",
        content="I want a truck around $500/month with $2,000 down",
    )
    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content="Got it — looking at F-150 XLT and Maverick Hybrid options.",
    )
    return session


class CreateLeadFromSessionTests(TestCase):
    def test_persists_lead_with_form_fields(self):
        session = _seed_session_with_chat(
            profile={
                "intent": "vehicle_search",
                "vehicle_type": "truck",
                "target_monthly_payment": 500,
                "down_payment": 2000,
            }
        )
        v = _make_vehicle()

        provider = MockLLMProvider(replies=["The customer wants a truck."])
        lead = create_lead_from_session(
            session=session,
            payload={
                "name": "Chris D.",
                "phone": "(405) 555-0199",
                "email": "chris@example.com",
                "target_monthly_payment": 500,
                "down_payment": 2000,
                "trade_in": "2018 Escape, ~75,000 miles",
                "credit_range": "good",
                "urgency": "this_week",
                "interested_vehicles": [v.id],
            },
            provider=provider,
        )

        lead.refresh_from_db()
        self.assertEqual(lead.name, "Chris D.")
        self.assertEqual(lead.phone, "(405) 555-0199")
        self.assertEqual(lead.email, "chris@example.com")
        self.assertEqual(lead.target_monthly_payment, Decimal("500"))
        self.assertEqual(lead.down_payment, Decimal("2000"))
        self.assertEqual(lead.urgency, "this_week")
        self.assertEqual(lead.credit_range, "good")
        self.assertIn(v, lead.interested_vehicles.all())

    def test_summary_generated_from_llm(self):
        session = _seed_session_with_chat()
        provider = MockLLMProvider(
            replies=["The customer is shopping for a truck near $500/month."]
        )
        lead = create_lead_from_session(
            session=session,
            payload={
                "name": "Chris D.",
                "target_monthly_payment": 500,
                "interested_vehicles": [],
            },
            provider=provider,
        )
        self.assertIn("truck", lead.conversation_summary.lower())
        # Provider was actually called (not skipped).
        self.assertEqual(len(provider.calls), 1)

    def test_summary_falls_back_when_llm_empty(self):
        session = _seed_session_with_chat()
        provider = MockLLMProvider(replies=[""])
        lead = create_lead_from_session(
            session=session,
            payload={
                "name": "Chris D.",
                "target_monthly_payment": 500,
                "down_payment": 2000,
                "trade_in": "2018 Escape",
                "urgency": "this_week",
                "interested_vehicles": [],
            },
            provider=provider,
        )
        # Fallback summary mentions the customer name and budget.
        self.assertIn("Chris D.", lead.conversation_summary)
        self.assertIn("500", lead.conversation_summary)

    def test_recommended_next_action_for_immediate_urgency(self):
        session = _seed_session_with_chat()
        provider = MockLLMProvider(replies=["summary"])
        lead = create_lead_from_session(
            session=session,
            payload={
                "name": "Chris D.",
                "urgency": "immediate",
                "interested_vehicles": [],
            },
            provider=provider,
        )
        self.assertIn("1 hour", lead.recommended_next_action)

    def test_recommended_next_action_flags_unrealistic_budget(self):
        session = _seed_session_with_chat()
        v = _make_vehicle(price="78000.00")  # Lariat-ish
        provider = MockLLMProvider(replies=["summary"])
        lead = create_lead_from_session(
            session=session,
            payload={
                "name": "Chris D.",
                "target_monthly_payment": 400,
                "down_payment": 0,
                "urgency": "this_month",
                "interested_vehicles": [v.id],
            },
            provider=provider,
        )
        # Should warn about budget mismatch.
        self.assertIn("$78,000", lead.recommended_next_action)
        self.assertIn("realistic", lead.recommended_next_action)

    def test_handoff_message_appended_to_chat(self):
        session = _seed_session_with_chat()
        provider = MockLLMProvider(replies=["summary"])
        create_lead_from_session(
            session=session,
            payload={"name": "Chris D.", "interested_vehicles": []},
            provider=provider,
        )
        handoff = session.messages.filter(role="system").last()
        self.assertIsNotNone(handoff)
        self.assertIn("LEAD CAPTURED", handoff.content)
        self.assertIn("Chris D.", handoff.content)

    def test_session_lead_created_flag_flipped(self):
        session = _seed_session_with_chat()
        self.assertFalse(session.lead_created)
        provider = MockLLMProvider(replies=["summary"])
        create_lead_from_session(
            session=session,
            payload={"name": "Chris D.", "interested_vehicles": []},
            provider=provider,
        )
        session.refresh_from_db()
        self.assertTrue(session.lead_created)

    def test_lead_form_data_merged_into_extracted_profile(self):
        session = _seed_session_with_chat(profile={"intent": "vehicle_search"})
        provider = MockLLMProvider(replies=["summary"])
        create_lead_from_session(
            session=session,
            payload={
                "name": "Chris D.",
                "target_monthly_payment": 600,
                "credit_range": "good",
                "urgency": "this_week",
                "trade_in": "2018 Escape",
                "interested_vehicles": [],
            },
            provider=provider,
        )
        session.refresh_from_db()
        profile = session.extracted_profile
        self.assertEqual(profile["target_monthly_payment"], 600)
        self.assertEqual(profile["credit_range"], "good")
        self.assertEqual(profile["urgency"], "this_week")
        self.assertTrue(profile["trade_in"])
        # Existing field preserved.
        self.assertEqual(profile["intent"], "vehicle_search")

    def test_works_without_session(self):
        provider = MockLLMProvider(replies=["summary"])
        lead = create_lead_from_session(
            session=None,
            payload={"name": "Walk-in Customer", "interested_vehicles": []},
            provider=provider,
        )
        self.assertEqual(CustomerLead.objects.count(), 1)
        self.assertIsNone(lead.session)
