"""Phase 8e — term-aware narrowing question tests.

Bug being fixed: when the customer was already at a 72-month term, the
assistant asked "Would a longer term — say 72 or 84 months — be acceptable?"
which is logically wrong (72 is not longer than 72).

The fix: the BUDGET ANALYSIS block computes the next valid longer term based
on the customer's current term and instructs the LLM to use that wording, or
skip the term angle entirely when the customer is already at 84+ months.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    BudgetContext,
    ChatEngine,
    _format_budget_block,
    next_term_suggestion,
)

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock, price, *, model="F-150"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


# ---- next_term_suggestion ---------------------------------------------------


class NextTermSuggestionTests(SimpleTestCase):
    def test_under_60_offers_60_72_84(self):
        self.assertEqual(next_term_suggestion(48), "60, 72, or 84 months")

    def test_60_offers_72_or_84(self):
        self.assertEqual(next_term_suggestion(60), "72 or 84 months")

    def test_72_offers_84_only(self):
        self.assertEqual(next_term_suggestion(72), "84 months")

    def test_84_offers_nothing(self):
        self.assertIsNone(next_term_suggestion(84))

    def test_above_84_offers_nothing(self):
        self.assertIsNone(next_term_suggestion(96))


# ---- _format_budget_block at different terms -------------------------------


def _no_fit_ctx(term: int) -> BudgetContext:
    """Synthesize a 'no vehicles fit' BudgetContext at the given term."""
    return BudgetContext(
        is_budget_query=True,
        target_monthly=300.0,
        down_payment=0.0,
        term_months=term,
        max_price=13_000.0,
        matched_in_budget=[],
        closest_above=[
            Vehicle(
                stock_number="X-1",
                year=2025,
                make="Ford",
                model="F-150",
                trim="XLT",
                body_style="truck",
                condition="new",
                price=Decimal("78000"),
            )
        ],
    )


class BudgetBlockTermSuggestionTests(SimpleTestCase):
    def test_60_month_block_suggests_72_or_84(self):
        block = _format_budget_block(_no_fit_ctx(60))
        self.assertIn("72 or 84 months", block)
        self.assertNotIn("60, 72, or 84", block)

    def test_72_month_block_suggests_84_only(self):
        block = _format_budget_block(_no_fit_ctx(72))
        self.assertIn("84 months", block)
        # Critical: the buggy phrase the LLM used to echo MUST NOT appear when
        # the customer is already at 72 months.
        self.assertNotIn("72 or 84", block)
        self.assertNotIn("72 or 84 months", block)

    def test_84_month_block_does_not_offer_longer_term(self):
        block = _format_budget_block(_no_fit_ctx(84))
        self.assertIn("DO NOT suggest a longer loan term", block)
        # Must explicitly redirect to a non-term angle.
        self.assertIn("trade-in", block.lower())

    def test_above_84_block_does_not_offer_longer_term(self):
        block = _format_budget_block(_no_fit_ctx(96))
        self.assertIn("DO NOT suggest a longer loan term", block)


# ---- ChatEngine wiring — system block reaches the LLM correctly ------------


def _system_text(provider: MockLLMProvider) -> str:
    """All system messages from the most recent provider call, joined."""
    if not provider.calls:
        return ""
    return "\n".join(
        m["content"] for m in provider.calls[-1] if m["role"] == "system"
    )


class ChatEngineTermNarrowingTests(TestCase):
    def test_72_month_session_does_not_send_72_or_84_phrase(self):
        """The exact bug scenario: customer profile has term_months=72, no
        vehicle fits, so the BUDGET ANALYSIS block must say '84 months' — and
        must NOT contain the '72 or 84' wording."""
        _make_vehicle("EXP-1", "78000")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 200,
                "term_months": 72,
            }
        )
        provider = MockLLMProvider(replies=[json_reply({}), "ack"])
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("only want to spend 200 a month")

        sent = _system_text(provider)
        self.assertIn("BUDGET ANALYSIS", sent)
        self.assertIn("Term assumed: 72 months", sent)
        self.assertIn("84 months", sent)
        self.assertNotIn("72 or 84", sent)

    def test_60_month_session_sends_72_or_84_phrase(self):
        _make_vehicle("EXP-2", "78000")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 200,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(replies=[json_reply({}), "ack"])
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("only want to spend 200 a month")
        sent = _system_text(provider)
        self.assertIn("72 or 84 months", sent)

    def test_84_month_session_does_not_offer_longer_term(self):
        _make_vehicle("EXP-3", "78000")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 200,
                "term_months": 84,
            }
        )
        provider = MockLLMProvider(replies=[json_reply({}), "ack"])
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("only want to spend 200 a month")
        sent = _system_text(provider)
        self.assertIn("DO NOT suggest a longer loan term", sent)
        # No longer-term phrasing leaks through.
        self.assertNotIn("Would a longer term", sent)
