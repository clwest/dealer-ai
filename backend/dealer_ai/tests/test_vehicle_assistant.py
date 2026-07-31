"""Tests for the vehicle_assistant service + vehicle detail/ask endpoints."""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services import vehicle_assistant

from ._mocks import MockLLMProvider


def _make_vehicle(stock, price, *, body="truck", model="F-150", **extra):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model=model,
        body_style=body,
        condition="new",
        price=Decimal(price),
        **extra,
    )


class AnalyzeVehicleTests(TestCase):
    def test_payment_estimates_at_three_terms(self):
        v = _make_vehicle("A-1", "60000.00")
        analysis = vehicle_assistant.analyze_vehicle(v)
        terms = [e["term_months"] for e in analysis.payment_estimates]
        self.assertEqual(terms, [60, 72, 84])
        # Longer term → smaller monthly payment.
        monthly = [e["monthly_payment"] for e in analysis.payment_estimates]
        self.assertGreater(monthly[0], monthly[1])
        self.assertGreater(monthly[1], monthly[2])

    def test_affordability_notes_baseline(self):
        v = _make_vehicle("A-1", "60000.00")
        analysis = vehicle_assistant.analyze_vehicle(v)
        # First note is the baseline @72mo no-down.
        self.assertTrue(any("72 months" in n for n in analysis.affordability_notes))
        # No down-payment note when no down provided.
        self.assertFalse(
            any("Putting $" in n for n in analysis.affordability_notes)
        )

    def test_affordability_notes_with_down_payment(self):
        v = _make_vehicle("A-1", "60000.00")
        analysis = vehicle_assistant.analyze_vehicle(
            v, profile={"down_payment": 5000}
        )
        self.assertTrue(any("Putting $5,000" in n for n in analysis.affordability_notes))

    def test_affordability_notes_warn_when_target_too_low(self):
        v = _make_vehicle("A-1", "78000.00")
        analysis = vehicle_assistant.analyze_vehicle(
            v, profile={"target_monthly_payment": 400, "down_payment": 0}
        )
        text = " ".join(analysis.affordability_notes)
        self.assertIn("meaningfully above", text)

    def test_affordability_notes_celebrate_when_target_fits(self):
        v = _make_vehicle("A-1", "32000.00")
        analysis = vehicle_assistant.analyze_vehicle(
            v, profile={"target_monthly_payment": 700, "down_payment": 2000}
        )
        text = " ".join(analysis.affordability_notes)
        self.assertIn("Good news", text)

    def test_similar_vehicles_excludes_self_and_uses_price_band(self):
        anchor = _make_vehicle("ANCHOR", "60000.00", body="truck")
        # In-band, same body style — should appear.
        in_band = _make_vehicle("INBAND", "55000.00", body="truck", model="Ranger")
        # Out of band — should not.
        _make_vehicle("FAR", "120000.00", body="truck", model="Raptor")
        # Different body style, but in price band — only fills if needed.
        _make_vehicle("OTHER", "58000.00", body="suv", model="Explorer")

        analysis = vehicle_assistant.analyze_vehicle(anchor)
        ids = [v.id for v in analysis.similar_vehicles]
        self.assertIn(in_band.id, ids)
        self.assertNotIn(anchor.id, ids)


@override_settings(DEALER_AI_DEALER_NAME="Freedom Ford")
class AnswerVehicleQuestionTests(TestCase):
    def test_uses_provider_and_returns_text(self):
        v = _make_vehicle("Q-1", "60000.00")
        provider = MockLLMProvider(replies=["Yes, this F-150 tows up to 5,000kg."])
        answer = vehicle_assistant.answer_vehicle_question(
            v, "Is this good for towing?", provider=provider
        )
        self.assertIn("F-150", answer)
        # Confirm the LLM actually got vehicle context.
        first_call = provider.calls[0]
        joined = "\n".join(m["content"] for m in first_call)
        self.assertIn("F-150", joined)
        self.assertIn("Stock #Q-1", joined)
        self.assertIn("PAYMENT MATH", joined)

    def test_empty_question_returns_prompt(self):
        v = _make_vehicle("Q-1", "60000.00")
        provider = MockLLMProvider(replies=["this should not be used"])
        answer = vehicle_assistant.answer_vehicle_question(
            v, "   ", provider=provider
        )
        self.assertIn("would you like to know", answer.lower())
        self.assertEqual(provider.calls, [])  # short-circuit before LLM

    def test_fallback_when_provider_returns_empty(self):
        v = _make_vehicle("Q-1", "60000.00")
        provider = MockLLMProvider(replies=[""])
        answer = vehicle_assistant.answer_vehicle_question(
            v, "Tell me about the warranty", provider=provider
        )
        self.assertIn("advisor from Freedom Ford", answer)

    def test_writes_to_session_when_provided(self):
        v = _make_vehicle("Q-1", "60000.00")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["Sure, here's how it tows."])
        vehicle_assistant.answer_vehicle_question(
            v,
            "Is this good for towing?",
            session=session,
            provider=provider,
        )
        msgs = list(session.messages.order_by("created_at"))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].role, "user")
        self.assertEqual(msgs[0].metadata.get("kind"), "vehicle_ask")
        self.assertEqual(msgs[0].metadata.get("vehicle_id"), v.id)
        self.assertEqual(msgs[1].role, "assistant")
        self.assertIn(v, msgs[1].matched_vehicles.all())


class VehicleDetailEndpointTests(TestCase):
    def test_returns_full_payload(self):
        v = _make_vehicle("DET-1", "60000.00")
        _make_vehicle("DET-2", "55000.00", model="Ranger")  # similar
        url = reverse("dealer_ai:vehicle-detail", args=[v.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["vehicle"]["stock_number"], "DET-1")
        self.assertEqual(len(data["payment_estimates"]), 3)
        self.assertGreater(len(data["affordability_notes"]), 0)
        # Similar should not include self.
        ids = [s["id"] for s in data["similar_vehicles"]]
        self.assertNotIn(v.id, ids)

    def test_404_for_missing_vehicle(self):
        url = reverse("dealer_ai:vehicle-detail", args=[999999])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 404)

    def test_query_params_personalize_payments(self):
        v = _make_vehicle("DET-1", "60000.00")
        url = reverse("dealer_ai:vehicle-detail", args=[v.id])
        res = self.client.get(url + "?down_payment=10000&target_monthly_payment=600")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Down payment should appear in payment estimates.
        self.assertEqual(data["payment_estimates"][0]["down_payment"], 10000)
        # Affordability notes should reference the down payment.
        text = " ".join(data["affordability_notes"])
        self.assertIn("$10,000", text)


class VehicleAskEndpointTests(TestCase):
    def setUp(self):
        # Patch the factory so the endpoint uses our mock.
        from dealer_ai.services import vehicle_assistant as va

        self._orig = va.get_llm_provider
        self._mock_provider = MockLLMProvider(
            replies=["This Ranger handles light towing well."]
        )
        va.get_llm_provider = lambda: self._mock_provider

    def tearDown(self):
        from dealer_ai.services import vehicle_assistant as va

        va.get_llm_provider = self._orig

    def test_returns_answer_and_vehicle_payload(self):
        v = _make_vehicle("ASK-1", "47000.00", model="Ranger")
        url = reverse("dealer_ai:vehicle-ask", args=[v.id])
        res = self.client.post(
            url,
            data={"question": "Is this good for towing?"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Ranger", data["answer"])
        self.assertEqual(data["vehicle"]["stock_number"], "ASK-1")
        self.assertEqual(len(data["payment_estimates"]), 3)

    def test_logs_to_session_when_session_id_provided(self):
        v = _make_vehicle("ASK-1", "47000.00", model="Ranger")
        session = ChatSession.objects.create()
        url = reverse("dealer_ai:vehicle-ask", args=[v.id])
        res = self.client.post(
            url,
            data={
                "question": "Is this a stretch on $500/month?",
                "session_id": str(session.id),
                "target_monthly_payment": 500,
                "down_payment": 0,
            },
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        msgs = list(session.messages.filter(metadata__kind="vehicle_ask"))
        self.assertEqual(len(msgs), 2)

    def test_404_for_unknown_vehicle(self):
        url = reverse("dealer_ai:vehicle-ask", args=[999999])
        res = self.client.post(
            url,
            data={"question": "anything"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_400_when_question_missing(self):
        v = _make_vehicle("ASK-1", "47000.00", model="Ranger")
        url = reverse("dealer_ai:vehicle-ask", args=[v.id])
        res = self.client.post(url, data={}, content_type="application/json")
        self.assertEqual(res.status_code, 400)


# ---- Manager Phase 4: §6.1 closure — vehicle_assistant runs the shared
# post-LLM scrub stack on the LLM's draft reply.


@override_settings(DEALER_AI_DEALER_NAME="Freedom Ford")
class VehicleAssistantPostLLMSafetyTests(TestCase):
    """Confirms PROJECT_PIPELINE.md §6.1 is closed: per-vehicle Q&A
    replies now run through ``apply_post_llm_scrubs(kind="vehicle_ask")``,
    matching the chat path's safety net."""

    def setUp(self):
        from dealer_ai.services import vehicle_assistant as va

        self._orig = va.get_llm_provider

    def tearDown(self):
        from dealer_ai.services import vehicle_assistant as va

        va.get_llm_provider = self._orig

    def _patch_provider(self, replies):
        from dealer_ai.services import vehicle_assistant as va

        provider = MockLLMProvider(replies=replies)
        va.get_llm_provider = lambda: provider
        return provider

    # The customer questions below are chosen specifically to be benign —
    # they must NOT trigger any pre-LLM guard (rate-inquiry / external-value
    # / negotiation / handoff / etc), otherwise the LLM is never called and
    # the post-LLM scrub doesn't get a chance to fire.

    def test_rate_language_scrubbed_inline(self):
        from dealer_ai.services import vehicle_assistant as va

        v = _make_vehicle("SCRUB-1", "47000.00", model="Ranger")
        provider = MockLLMProvider(
            replies=["Estimated $517/mo at 7.49% APR over 60 months."]
        )
        reply = va.answer_vehicle_question(
            v, "Tell me about this Ranger.", provider=provider
        )
        self.assertNotIn("APR", reply)
        self.assertNotIn("7.49%", reply)

    def test_dealer_cost_leak_replaced_with_guard_response(self):
        from dealer_ai.services import vehicle_assistant as va
        from dealer_ai.services.chat_engine import GUARD_RESPONSE

        v = _make_vehicle("SCRUB-2", "47000.00", model="Ranger")
        provider = MockLLMProvider(
            replies=["Our dealer cost is around $42,000 so we have wiggle room."]
        )
        reply = va.answer_vehicle_question(
            v, "What is the towing capacity?", provider=provider
        )
        self.assertEqual(reply, GUARD_RESPONSE)

    def test_negotiation_phrase_replaced_with_negotiation_response(self):
        from dealer_ai.services import vehicle_assistant as va
        from dealer_ai.services.chat_engine import NEGOTIATION_RESPONSE, _render

        v = _make_vehicle("SCRUB-3", "47000.00", model="Ranger")
        provider = MockLLMProvider(
            replies=["I can match that price for you. We can do $42,000."]
        )
        reply = va.answer_vehicle_question(
            v, "How does this Ranger compare to the F-150?", provider=provider
        )
        self.assertEqual(reply, _render(NEGOTIATION_RESPONSE))
