"""Phase 8h — W.A.C. payment language compliance tests.

The system must never state or imply a specific interest rate / APR /
financing percentage in customer-facing copy. All payment estimates carry
the W.A.C. (with approved credit) qualifier.

Coverage:
  - System blocks sent to the LLM contain no rate language
  - Pre-LLM rate-inquiry guard returns the canned compliant reply
  - Post-LLM scrub catches rate leakage from the model output
  - Seeded scenarios use W.A.C. phrasing
  - Backend payment math is unchanged (estimates still computed correctly)
"""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatMessage, ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    RATE_INQUIRY_RESPONSE,
    ChatEngine,
    _format_budget_block,
    _format_vehicle_block,
    build_budget_context,
    detect_rate_inquiry,
    scrub_rate_language,
)
from dealer_ai.services.payment_engine import estimate_payment
from dealer_ai.services.vehicle_assistant import analyze_vehicle

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock="WAC-1", price="26995", *, model="Ranger"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


# ---- detect_rate_inquiry ---------------------------------------------------


class DetectRateInquiryTests(SimpleTestCase):
    def test_flags_rate_questions(self):
        for phrase in [
            "What's the interest rate?",
            "What is the APR?",
            "What rate do I qualify for?",
            "What rate will I get?",
            "What APR can I get?",
            "Tell me the interest rate.",
            "Show me your APR.",
            "What's my rate?",
            "Quote me an interest rate please",
        ]:
            self.assertTrue(detect_rate_inquiry(phrase), msg=phrase)

    def test_does_not_flag_normal_messages(self):
        for phrase in [
            "What's the price?",
            "Show me F-150s under 65k",
            "I want a truck for $500/month",
            "What does this cost?",
            "How much down payment?",
        ]:
            self.assertFalse(detect_rate_inquiry(phrase), msg=phrase)


# ---- scrub_rate_language ---------------------------------------------------


class ScrubRateLanguageTests(SimpleTestCase):
    def test_removes_at_x_percent(self):
        cleaned, changed = scrub_rate_language(
            "Around $517/mo @ 7.49% APR for 60 months."
        )
        self.assertTrue(changed)
        self.assertNotIn("7.49%", cleaned)
        self.assertNotIn("APR", cleaned)

    def test_replaces_apr_of_x(self):
        cleaned, changed = scrub_rate_language(
            "Estimated $498/mo at an APR of 6.99%."
        )
        self.assertTrue(changed)
        self.assertNotIn("6.99%", cleaned)
        self.assertNotIn("APR", cleaned)
        self.assertIn("W.A.C.", cleaned)

    def test_replaces_interest_rate_of_x(self):
        cleaned, changed = scrub_rate_language(
            "At an interest rate of 5.5%, your payment is $400/mo."
        )
        self.assertTrue(changed)
        self.assertNotIn("5.5%", cleaned)
        self.assertNotIn("interest rate", cleaned.lower())
        self.assertIn("W.A.C.", cleaned)

    def test_no_change_when_already_compliant(self):
        text = "Estimated $517/mo for 60 months (W.A.C.)."
        cleaned, changed = scrub_rate_language(text)
        self.assertFalse(changed)
        self.assertEqual(cleaned, text)


# ---- System blocks contain no rate language -------------------------------


class SystemBlocksWACTests(TestCase):
    def test_unannotated_inventory_block_uses_wac(self):
        v = _make_vehicle()
        block = _format_vehicle_block([v], budget_mode=False)
        self.assertNotIn("%", block)
        self.assertNotIn("APR", block)
        self.assertIn("W.A.C.", block)

    def test_annotated_inventory_block_uses_wac(self):
        v = _make_vehicle()
        v._estimated_payment = 517.0
        v._budget_fit = "near_fit"
        v._payment_delta = 17.0
        block = _format_vehicle_block([v], budget_mode=True)
        self.assertNotIn("%", block)
        self.assertNotIn("APR", block.replace("APR percentage", ""))  # rules text references it
        self.assertIn("W.A.C.", block)

    def test_budget_analysis_block_does_not_leak_rate(self):
        v = _make_vehicle("BA-1", "26995")
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        ctx = build_budget_context(profile, "$500/mo, $3k down")
        block = _format_budget_block(ctx)
        # No specific percentage anywhere.
        self.assertNotRegex(block, r"\d+(?:\.\d+)?%")
        # W.A.C. anchored in the header.
        self.assertIn("W.A.C.", block)


# ---- Pre-LLM rate-inquiry guard --------------------------------------------


class RateInquiryGuardTests(TestCase):
    def test_what_apr_returns_canned_response(self):
        v = _make_vehicle(model="F-150")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["should not be used"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("What's the APR on this F-150?")
        self.assertEqual(result.assistant_message.content, RATE_INQUIRY_RESPONSE)
        self.assertEqual(
            result.assistant_message.metadata.get("flag"), "rate_inquiry"
        )
        self.assertEqual(provider.calls, [])
        # Customer still sees inventory matches alongside the refusal.
        self.assertIn(v, result.matched_vehicles)

    def test_what_rate_do_i_qualify_for_returns_canned(self):
        _make_vehicle()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["nope"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("What rate do I qualify for?")
        self.assertEqual(result.assistant_message.content, RATE_INQUIRY_RESPONSE)
        self.assertEqual(provider.calls, [])

    def test_canned_response_explains_rates_vary(self):
        self.assertIn("vary", RATE_INQUIRY_RESPONSE.lower())
        self.assertIn("dealership", RATE_INQUIRY_RESPONSE.lower())


# ---- Post-LLM scrub end-to-end --------------------------------------------


class PostLLMScrubIntegrationTests(TestCase):
    def test_assistant_reply_with_apr_gets_scrubbed_and_flagged(self):
        _make_vehicle()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Estimated $517/mo at 7.49% APR over 60 months.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me about the Ranger")
        # No rate leakage in the persisted reply.
        self.assertNotIn("7.49", result.assistant_message.content)
        self.assertNotIn("APR", result.assistant_message.content)
        # W.A.C. remains in the cleaned text.
        self.assertIn("W.A.C.", result.assistant_message.content)
        # Metadata flag set for audit.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "rate_language_scrubbed",
        )

    def test_clean_assistant_reply_passes_through_unchanged(self):
        _make_vehicle()
        session = ChatSession.objects.create()
        clean_reply = "Estimated $517/mo for 60 months (W.A.C. — with approved credit)."
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                clean_reply,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me about the Ranger")
        self.assertEqual(result.assistant_message.content, clean_reply)
        self.assertNotIn("flag", result.assistant_message.metadata)


# ---- Seed data compliance -------------------------------------------------


class SeedScenarioComplianceTests(TestCase):
    def test_seeded_scenarios_have_no_rate_percentages(self):
        # Need vehicles so seed_demo_scenarios doesn't bail.
        call_command("seed_demo_vehicles", stdout=StringIO())
        call_command("seed_demo_scenarios", stdout=StringIO())

        # Walk every assistant message and lead summary that ships with the
        # demo. None should contain a specific rate or APR percentage.
        offenders: list[str] = []
        for m in ChatMessage.objects.exclude(role="user"):
            if "%" in m.content or "APR" in m.content:
                offenders.append(f"msg #{m.id}: {m.content[:120]}")
        from dealer_ai.models import CustomerLead

        for lead in CustomerLead.objects.all():
            text = (lead.conversation_summary or "") + " " + (
                lead.recommended_next_action or ""
            )
            if "%" in text or "APR" in text:
                offenders.append(f"lead #{lead.id}: {text[:160]}")
        self.assertEqual(offenders, [], f"Rate language leaked: {offenders}")


# ---- Math is unchanged ----------------------------------------------------


class MathPreservedTests(TestCase):
    def test_estimate_payment_still_returns_apr_field_internally(self):
        # The backend still computes with an APR — we just don't surface it
        # to the customer. Internal math must remain accurate.
        est = estimate_payment(Decimal("26995"), down_payment=3000, term_months=60)
        self.assertGreater(est.monthly_payment, 500)
        self.assertLess(est.monthly_payment, 600)
        # apr is still on the dict for any internal downstream consumer that
        # needs it (e.g. dashboards). It just doesn't reach the customer.
        self.assertGreater(est.apr, 0)

    def test_analyze_vehicle_returns_three_term_estimates(self):
        v = _make_vehicle()
        analysis = analyze_vehicle(v, profile={"down_payment": 3000})
        terms = [e["term_months"] for e in analysis.payment_estimates]
        self.assertEqual(terms, [60, 72, 84])
        # Each estimate has a monthly_payment field intact.
        for e in analysis.payment_estimates:
            self.assertGreater(e["monthly_payment"], 0)
