"""Item 9 — cash-mode financing-language scrub.

When the customer signals they want to pay cash, the LLM has been
observed inserting *"Estimated monthly payment: $227/mo (W.A.C.)"*
even though no financing math applies. This scrub drops any
sentence containing financing tokens (payment quotes, "monthly
payment", "per month", "financing", "loan", "W.A.C.", X-month
term) so the customer never sees the irrelevant numbers.

Sticky: ``cash_mode`` persists in the session profile once
detected, so a follow-up turn that omits the "cash" word still
gets the scrub applied.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    LIST_SHAPE_FALLBACK,
    scrub_financing_language,
)

from ._mocks import MockLLMProvider, json_reply


# ---- scrub_financing_language unit tests --------------------------------


class ScrubFinancingLanguageUnitTests(SimpleTestCase):
    """Pure-function coverage. Drops sentences containing any
    financing token; preserves price-only / qualitative prose.
    """

    def test_no_cash_mode_returns_unchanged(self):
        text = "The Fusion is a great option at $11,995. Monthly payment $227/mo."
        cleaned, changed = scrub_financing_language(
            text, cash_mode=False
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_empty_text_returns_unchanged(self):
        cleaned, changed = scrub_financing_language(
            "", cash_mode=True
        )
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_cash_friendly_prose_untouched(self):
        text = (
            "I've got just the thing for you. The 2014 Ford Fusion "
            "is priced at $11,995. Want to take a closer look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_payment_quote_sentence_stripped(self):
        text = (
            "The Fusion is a great option at $11,995. Estimated "
            "monthly payment: $227/mo (W.A.C.). Want a closer look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("$227/mo", cleaned)
        self.assertNotIn("(W.A.C.)", cleaned)
        self.assertNotIn("monthly payment", cleaned.lower())
        # Price + close preserved.
        self.assertIn("$11,995", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_per_month_phrasing_stripped(self):
        text = (
            "The Camry runs you about $260 per month. It's priced "
            "at $13,495. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("per month", cleaned.lower())
        self.assertNotIn("$260", cleaned)
        self.assertIn("$13,495", cleaned)

    def test_financing_word_stripped(self):
        text = (
            "The Accord is a great deal at $12,995. We have "
            "financing options if you'd like. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("financing", cleaned.lower())
        self.assertIn("$12,995", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_loan_word_stripped(self):
        text = (
            "The Sonata is $10,995. We can set up a loan in 60 "
            "months. Want a closer look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("loan", cleaned.lower())
        self.assertIn("$10,995", cleaned)

    def test_wac_bare_stripped(self):
        text = (
            "The Camry is at $13,495. Estimated payment is W.A.C. "
            "Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("W.A.C.", cleaned)

    def test_wac_parenthetical_stripped(self):
        text = (
            "The Fusion is $11,995. The estimate (W.A.C. — with "
            "approved credit) lands at $227/mo. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("W.A.C.", cleaned)
        self.assertNotIn("$227", cleaned)
        self.assertIn("$11,995", cleaned)

    def test_loan_term_phrasing_stripped(self):
        text = (
            "The Civic is $13,995. Over a 60-month term that's "
            "comfortable. Want a closer look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("60-month term", cleaned)
        self.assertNotIn("comfortable", cleaned)

    def test_term_of_60_months_stripped(self):
        text = (
            "The Mazda is $11,495. Over a term of 60 months. Want "
            "a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("term of 60", cleaned)

    def test_estimated_monthly_payment_phrase_stripped(self):
        text = (
            "Sonata at $10,995. Estimated monthly payment lands "
            "around $210. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("monthly payment", cleaned.lower())
        self.assertIn("$10,995", cleaned)

    def test_only_financing_sentences_falls_back(self):
        # Reply is purely financing — fallback used.
        text = (
            "Estimated monthly payment: $227/mo. Over a 60-month "
            "term with W.A.C. financing."
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)

    def test_non_cash_mode_payment_language_preserved(self):
        # User-spec test #3 — normal finance flow unchanged.
        text = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=False
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_multiple_payment_quotes_all_stripped(self):
        # Each sentence containing a payment quote is dropped
        # wholesale. When a single sentence contains BOTH a price
        # AND a payment ("$10,995, around $210/mo"), the whole
        # sentence goes — the customer will see the price on the
        # card. Sentence-level is the safer cut than partial
        # token replacement.
        text = (
            "Three options. The Civic is $11,995. Around $227/mo. "
            "The Sonata at $10,995, around $210/mo. Want a look?"
        )
        cleaned, changed = scrub_financing_language(
            text, cash_mode=True
        )
        self.assertTrue(changed)
        self.assertNotIn("$227", cleaned)
        self.assertNotIn("$210", cleaned)
        # The Sonata price was in the same sentence as $210/mo —
        # whole sentence dropped, $10,995 goes with it.
        self.assertNotIn("$10,995", cleaned)
        # The Civic price was in its OWN sentence with no payment
        # token — survives.
        self.assertIn("$11,995", cleaned)
        self.assertIn("Want a look?", cleaned)


# ---- ChatEngine integration tests ---------------------------------------


def _seed_cars():
    Vehicle.objects.create(
        stock_number="CAR-A",
        year=2014,
        make="Honda",
        model="Accord",
        body_style="car",
        condition="used",
        price=Decimal("12995"),
        drivetrain="FWD",
    )
    Vehicle.objects.create(
        stock_number="CAR-B",
        year=2015,
        make="Toyota",
        model="Camry",
        body_style="car",
        condition="used",
        price=Decimal("13495"),
        drivetrain="FWD",
    )


class CashModeIntegrationTests(TestCase):
    """End-to-end coverage. Cash signals trigger the financing
    scrub; sticky persistence carries cash_mode across turns.
    """

    def test_cash_query_strips_payment_language(self):
        _seed_cars()
        session = ChatSession.objects.create()
        bad_reply = (
            "I've got just the thing. The Honda Accord is at "
            "$12,995. Estimated monthly payment: $227/mo (W.A.C.). "
            "Want a closer look?"
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                bad_reply,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap commuter car, gas mileage, pay cash"
        )

        content = result.assistant_message.content
        self.assertNotIn("$227/mo", content)
        self.assertNotIn("monthly payment", content.lower())
        self.assertNotIn("(W.A.C.)", content)
        # Price + close preserved.
        self.assertIn("$12,995", content)
        self.assertIn("Want a closer look?", content)

        meta = result.assistant_message.metadata
        self.assertTrue(meta.get("cash_mode"))
        self.assertIn("financing_language", meta.get("scrubs", []))

    def test_cash_mode_persists_to_profile(self):
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "The Accord at $12,995. Want a closer look?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap commuter car, fuel economy, cash"
        )
        # cash_mode flagged in profile so subsequent turns inherit
        # the financing scrub even if the customer doesn't repeat
        # the "cash" word.
        self.assertTrue(result.extracted_profile.get("cash_mode"))

    def test_cash_mode_sticky_across_turns(self):
        # Turn 1 establishes cash_mode. Turn 2 omits the cash word
        # but the financing scrub still fires because cash_mode
        # carries in profile.
        _seed_cars()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                "The Accord at $12,995. Want a look?",
                json_reply({}),
                "The Camry at $13,495. Estimated monthly: $260/mo.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("cheap car cash, gas mileage")
        # Turn 2 — no cash word in user text.
        session.refresh_from_db()
        engine2 = ChatEngine(session=session, provider=provider)
        result = engine2.handle_user_message("what about a Camry?")
        content = result.assistant_message.content
        # Financing scrub still fires from sticky profile.cash_mode.
        self.assertNotIn("$260/mo", content)
        self.assertNotIn("monthly", content.lower())
        meta = result.assistant_message.metadata
        self.assertTrue(meta.get("cash_mode"))

    def test_normal_finance_flow_unchanged(self):
        # User-spec test #3 — normal (non-cash) flow still has
        # payment language.
        Vehicle.objects.create(
            stock_number="TRUCK-A",
            year=2019,
            make="Ford",
            model="Ranger",
            body_style="truck",
            condition="used",
            price=Decimal("26995"),
            drivetrain="4x4",
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        finance_reply = (
            "The Ranger is really close at about $517/mo. Want a "
            "closer look?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), finance_reply]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm looking for a 4WD truck around $500/mo with $3k down"
        )
        # Reply preserved — no cash mode triggered.
        self.assertEqual(result.assistant_message.content, finance_reply)
        meta = result.assistant_message.metadata
        self.assertFalse(meta.get("cash_mode"))
        self.assertNotIn(
            "financing_language", meta.get("scrubs", [])
        )

    def test_only_financing_sentences_falls_back(self):
        _seed_cars()
        session = ChatSession.objects.create()
        only_fin = (
            "Estimated monthly payment is $227/mo. Over a 60-month "
            "term with W.A.C. financing."
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({"vehicle_type": "car"}),
                only_fin,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash gas mileage"
        )
        # Reply replaced with the canned fallback.
        self.assertEqual(
            result.assistant_message.content, LIST_SHAPE_FALLBACK
        )

    def test_cash_mode_stacks_with_other_scrubs(self):
        # Cash mode + bullet shape: list_shape strips the bullet,
        # then financing_language strips the payment line if any
        # remains. Both flags should appear in scrubs.
        _seed_cars()
        session = ChatSession.objects.create()
        bad = (
            "Some options:\n"
            "* Honda Accord | Stock #CAR-A | $12,995\n"
            "Estimated monthly payment: $227/mo. Want a look?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({"vehicle_type": "car"}), bad]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "cheap car cash, fuel economy"
        )
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        # list_shape stripped the bullet; financing_language
        # stripped the monthly-payment sentence.
        self.assertIn("list_shape", scrubs)
        self.assertIn("financing_language", scrubs)
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")
