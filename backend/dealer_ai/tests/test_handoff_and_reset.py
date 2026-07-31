"""Tests for the handoff service, lead detail, handoff, and demo reset endpoints."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from dealer_ai.models import ChatMessage, ChatSession, CustomerLead, Vehicle
from dealer_ai.services import handoff_service
from dealer_ai.services.handoff_service import (
    build_handoff_packet,
    packet_to_text,
)

from ._mocks import MockLLMProvider


def _make_vehicle(stock="HP-1", price="60000.00", model="F-150"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


def _make_lead_with_session(**lead_kwargs) -> CustomerLead:
    session = ChatSession.objects.create(
        extracted_profile={"intent": "vehicle_search", "vehicle_type": "truck"}
    )
    ChatMessage.objects.create(
        session=session, role="user", content="Looking for an F-150"
    )
    ChatMessage.objects.create(
        session=session, role="assistant", content="Got it — here are some options."
    )
    defaults = dict(
        name="Chris D.",
        phone="(405) 555-0199",
        email="chris@example.com",
        target_monthly_payment=Decimal("500"),
        down_payment=Decimal("2000"),
        urgency="this_week",
        conversation_summary="Customer wants an F-150 around $500/mo.",
        recommended_next_action="Call same day to book a test drive.",
        session=session,
    )
    defaults.update(lead_kwargs)
    return CustomerLead.objects.create(**defaults)


# ---- handoff_service unit tests --------------------------------------------


@override_settings(DEALER_AI_DEALER_NAME="Freedom Ford")
class HandoffServiceTests(TestCase):
    def test_packet_includes_all_required_fields(self):
        v = _make_vehicle()
        lead = _make_lead_with_session()
        lead.interested_vehicles.add(v)

        provider = MockLLMProvider(replies=["Hi Chris, ready when you are."])
        packet = build_handoff_packet(lead, provider=provider)

        for key in [
            "lead_id",
            "generated_at",
            "customer",
            "interested_vehicles",
            "budget",
            "trade_in",
            "credit_range",
            "urgency",
            "urgency_label",
            "conversation_summary",
            "recommended_next_action",
            "suggested_message",
            "session_id",
        ]:
            self.assertIn(key, packet, f"missing {key}")

        self.assertEqual(packet["customer"]["name"], "Chris D.")
        self.assertEqual(packet["budget"]["target_monthly_payment"], "500.00")
        self.assertEqual(packet["budget"]["down_payment"], "2000.00")
        self.assertEqual(len(packet["interested_vehicles"]), 1)
        self.assertEqual(packet["urgency"], "this_week")
        self.assertEqual(packet["urgency_label"], "This week")
        self.assertEqual(packet["suggested_message"], "Hi Chris, ready when you are.")

    def test_suggested_message_uses_llm(self):
        lead = _make_lead_with_session()
        provider = MockLLMProvider(replies=["LLM-generated greeting."])
        packet = build_handoff_packet(lead, provider=provider)
        self.assertEqual(packet["suggested_message"], "LLM-generated greeting.")
        self.assertEqual(len(provider.calls), 1)

    def test_suggested_message_falls_back_when_llm_empty(self):
        v = _make_vehicle()
        lead = _make_lead_with_session()
        lead.interested_vehicles.add(v)
        provider = MockLLMProvider(replies=[""])
        packet = build_handoff_packet(lead, provider=provider)
        # Fallback message addresses the customer by first name.
        self.assertIn("Hi Chris", packet["suggested_message"])
        self.assertIn("Freedom Ford", packet["suggested_message"])

    def test_packet_to_text_renders_clipboard_friendly_string(self):
        v = _make_vehicle()
        lead = _make_lead_with_session()
        lead.interested_vehicles.add(v)
        provider = MockLLMProvider(replies=["See you soon."])
        packet = build_handoff_packet(lead, provider=provider)
        text = packet_to_text(packet)
        self.assertIn("Chris D.", text)
        self.assertIn("Vehicles of interest", text)
        self.assertIn("HP-1", text)
        self.assertIn("Suggested first message", text)

    def test_packet_handles_lead_without_session_or_vehicles(self):
        lead = CustomerLead.objects.create(name="Walk-in", urgency="researching")
        provider = MockLLMProvider(replies=["Hi there, no rush at all."])
        packet = build_handoff_packet(lead, provider=provider)
        self.assertEqual(packet["interested_vehicles"], [])
        self.assertIsNone(packet["session_id"])
        self.assertIsNone(packet["budget"]["target_monthly_payment"])


# ---- /admin/lead/<id>/ -----------------------------------------------------


class AdminLeadDetailEndpointTests(TestCase):
    def test_returns_lead_with_messages_and_vehicles(self):
        v = _make_vehicle()
        lead = _make_lead_with_session()
        lead.interested_vehicles.add(v)

        url = reverse("dealer_ai:admin-lead-detail", args=[lead.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["lead"]["name"], "Chris D.")
        self.assertEqual(len(data["interested_vehicles"]), 1)
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(data["session_profile"]["vehicle_type"], "truck")

    def test_404_for_unknown_lead(self):
        url = reverse("dealer_ai:admin-lead-detail", args=[999999])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_works_when_lead_has_no_session(self):
        lead = CustomerLead.objects.create(name="Walk-in")
        url = reverse("dealer_ai:admin-lead-detail", args=[lead.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["messages"], [])
        self.assertEqual(data["session_profile"], {})


# ---- /admin/lead/<id>/handoff/ ---------------------------------------------


class AdminLeadHandoffEndpointTests(TestCase):
    def setUp(self):
        # Patch get_llm_provider used inside handoff_service.
        self._orig = handoff_service.get_llm_provider
        self._mock = MockLLMProvider(replies=["Hi Chris, looking forward to chatting."])
        handoff_service.get_llm_provider = lambda: self._mock

    def tearDown(self):
        handoff_service.get_llm_provider = self._orig

    def test_returns_full_packet_and_text(self):
        v = _make_vehicle()
        lead = _make_lead_with_session()
        lead.interested_vehicles.add(v)

        url = reverse("dealer_ai:admin-lead-handoff", args=[lead.id])
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("suggested_message", data)
        self.assertIn("Hi Chris", data["suggested_message"])
        self.assertIn("text", data)
        self.assertIn("Vehicles of interest", data["text"])
        self.assertFalse(data["handed_off"])

    def test_mark_handed_off_flag_flips(self):
        lead = _make_lead_with_session()
        url = reverse("dealer_ai:admin-lead-handoff", args=[lead.id])
        res = self.client.post(
            url,
            data={"mark_handed_off": True},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["handed_off"])
        lead.refresh_from_db()
        self.assertTrue(lead.handed_off)

    def test_404_for_unknown_lead(self):
        url = reverse("dealer_ai:admin-lead-handoff", args=[999999])
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 404)


# ---- /demo/reset/ ----------------------------------------------------------


class DemoResetEndpointTests(TestCase):
    def test_clears_chat_state_and_leaves_imported_vehicles(self):
        # Demo + imported vehicle.
        Vehicle.objects.create(
            stock_number="DEMO-X",
            year=2025,
            model="F-150",
            price=Decimal("60000"),
            source="demo_seed",
        )
        imported = Vehicle.objects.create(
            stock_number="IMPORT-X",
            year=2024,
            model="Edge",
            price=Decimal("30000"),
            source="csv:dealer",
        )
        # Pre-existing conversation state.
        s = ChatSession.objects.create()
        ChatMessage.objects.create(session=s, role="user", content="hi")
        CustomerLead.objects.create(name="Chris", session=s)

        url = reverse("dealer_ai:demo-reset")
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["cleared"]["chat_sessions"], 1)
        self.assertEqual(data["cleared"]["leads"], 1)
        self.assertEqual(data["cleared"]["chat_messages"], 1)

        self.assertEqual(ChatSession.objects.count(), 0)
        self.assertEqual(CustomerLead.objects.count(), 0)
        # Imported vehicle still present.
        self.assertTrue(Vehicle.objects.filter(id=imported.id).exists())

    def test_can_skip_demo_reload(self):
        url = reverse("dealer_ai:demo-reset")
        res = self.client.post(
            url,
            data={"reload_demo_vehicles": False},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        # No demo vehicles loaded since we said no.
        self.assertEqual(
            Vehicle.objects.filter(source="demo_seed").count(), 0
        )

    def test_default_reloads_demo_vehicles(self):
        url = reverse("dealer_ai:demo-reset")
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 200)
        self.assertGreater(
            Vehicle.objects.filter(source="demo_seed").count(), 0
        )

    def test_explicit_delete_imported_drops_only_non_demo(self):
        Vehicle.objects.create(
            stock_number="IMPORT-Y",
            year=2024,
            model="Edge",
            price=Decimal("30000"),
            source="csv:dealer",
        )
        url = reverse("dealer_ai:demo-reset")
        res = self.client.post(
            url,
            data={"delete_imported_vehicles": True},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["deleted_imported_vehicles"], 1)
        # Imported vehicle gone, demo vehicles loaded.
        self.assertFalse(Vehicle.objects.filter(stock_number="IMPORT-Y").exists())
        self.assertGreater(
            Vehicle.objects.filter(source="demo_seed").count(), 0
        )
