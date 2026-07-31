"""Integration tests for the admin/dashboard read endpoints."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import ChatMessage, ChatSession, CustomerLead, Vehicle
from dealer_ai.tests._auth_helpers import sales_manager_client_at_default


def _make_vehicle(stock="A-1", price="60000.00", model="F-150"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


class SessionDetailEndpointTests(TestCase):
    def test_returns_session_with_messages(self):
        session = ChatSession.objects.create(
            customer_name="Chris", extracted_profile={"intent": "vehicle_search"}
        )
        ChatMessage.objects.create(session=session, role="user", content="hi")
        ChatMessage.objects.create(session=session, role="assistant", content="hello")

        url = reverse("dealer_ai:chat-session-detail", args=[session.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["customer_name"], "Chris")
        self.assertEqual(data["extracted_profile"], {"intent": "vehicle_search"})
        self.assertEqual(len(data["messages"]), 2)

    def test_404_on_unknown_session(self):
        url = reverse("dealer_ai:chat-session-detail", args=[uuid4()])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)


class AdminLeadListEndpointTests(TestCase):
    def setUp(self):
        self.client = sales_manager_client_at_default()

    def test_returns_leads_with_vehicles(self):
        v = _make_vehicle()
        lead = CustomerLead.objects.create(
            name="Chris",
            target_monthly_payment=Decimal("500"),
            urgency="this_week",
        )
        lead.interested_vehicles.add(v)

        res = self.client.get(reverse("dealer_ai:admin-lead-list"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        row = data["results"][0]
        self.assertEqual(row["name"], "Chris")
        self.assertEqual(row["urgency"], "this_week")
        self.assertEqual(len(row["interested_vehicles"]), 1)
        self.assertEqual(row["interested_vehicles"][0]["stock_number"], "A-1")

    def test_limit_query_param_caps_results(self):
        for i in range(5):
            CustomerLead.objects.create(name=f"Lead {i}")
        res = self.client.get(reverse("dealer_ai:admin-lead-list") + "?limit=2")
        data = res.json()
        self.assertEqual(data["count"], 5)
        self.assertEqual(len(data["results"]), 2)

    def test_invalid_limit_falls_back_to_default(self):
        res = self.client.get(reverse("dealer_ai:admin-lead-list") + "?limit=not-a-number")
        self.assertEqual(res.status_code, 200)


class AdminChatSessionListEndpointTests(TestCase):
    def setUp(self):
        self.client = sales_manager_client_at_default()

    def test_returns_sessions_with_last_message_snippet(self):
        s = ChatSession.objects.create(
            customer_name="Chris",
            extracted_profile={"intent": "vehicle_search", "vehicle_type": "truck"},
        )
        ChatMessage.objects.create(session=s, role="user", content="show me trucks")
        ChatMessage.objects.create(
            session=s, role="assistant", content="Here are some F-150 options."
        )

        res = self.client.get(reverse("dealer_ai:admin-chat-session-list"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        row = data["results"][0]
        self.assertEqual(row["customer_name"], "Chris")
        self.assertEqual(row["message_count"], 2)
        self.assertEqual(row["last_message"]["role"], "assistant")
        self.assertIn("F-150", row["last_message"]["content"])
        self.assertEqual(row["extracted_profile"]["vehicle_type"], "truck")

    def test_handles_empty_sessions(self):
        ChatSession.objects.create()
        res = self.client.get(reverse("dealer_ai:admin-chat-session-list"))
        data = res.json()
        self.assertEqual(data["results"][0]["message_count"], 0)
        self.assertIsNone(data["results"][0]["last_message"])


class AdminTrendsEndpointTests(TestCase):
    def setUp(self):
        self.client = sales_manager_client_at_default()

    def test_returns_full_snapshot_shape(self):
        v = _make_vehicle()
        ChatSession.objects.create(
            extracted_profile={
                "intent": "vehicle_search",
                "model": "F-150",
                "vehicle_type": "truck",
            }
        )
        lead = CustomerLead.objects.create(
            name="Chris", target_monthly_payment=Decimal("500")
        )
        lead.interested_vehicles.add(v)

        res = self.client.get(reverse("dealer_ai:admin-trends"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_chat_sessions"], 1)
        self.assertEqual(data["total_leads"], 1)
        self.assertEqual(data["average_target_monthly_payment"], 500.0)
        self.assertEqual(data["top_requested_models"], [{"value": "F-150", "count": 1}])
        self.assertEqual(
            data["top_requested_vehicle_types"], [{"value": "truck", "count": 1}]
        )
        self.assertEqual(data["most_selected_vehicles"][0]["lead_count"], 1)
        self.assertEqual(len(data["recent_customer_intents"]), 1)
        self.assertEqual(data["recent_customer_intents"][0]["intent"], "vehicle_search")

    def test_empty_snapshot_renders(self):
        res = self.client.get(reverse("dealer_ai:admin-trends"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_chat_sessions"], 0)
        self.assertEqual(data["total_leads"], 0)
