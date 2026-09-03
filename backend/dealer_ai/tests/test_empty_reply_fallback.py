"""SESSION_234 (finding 45) — the empty-content fallback must NOT
pretend the model asked a clarifying question. Regression covers the
common case (no retail-visible inventory in the test DB): the reply
must acknowledge nothing lines up + offer an advisor handoff, never
re-ask for facts the customer already stated.

Full retrieval-backed happy path is exercised end-to-end via the
walkable-demo acceptance suite; seeding the lifecycle-stage machinery
required to make ``customer_visible_vehicles`` return rows would
duplicate that harness here.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.models import ChatSession
from dealer_ai.services.chat_engine import ChatEngine

from ._mocks import MockLLMProvider, json_reply


class EmptyReplyFallbackTests(TestCase):
    def test_empty_reply_never_reasks_stated_facts(self):
        # Extraction pass returns a JSON profile; the customer-facing
        # pass returns empty content (reasoning-model budget
        # starvation). Fallback must never re-ask for facts the
        # customer already stated ("size, budget, new vs used") and
        # must offer a real path forward.
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "model": "Silverado 1500",
                        "target_monthly_payment": 350,
                        "down_payment": 800,
                        "credit_range": "poor",
                    }
                ),
                "",  # customer-facing reply — empty content
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Silverados under 20k? Rough credit, $800 down."
        )

        text = result.assistant_message.content
        # Never the old re-ask template.
        self.assertNotIn("size, budget, new vs used", text)
        self.assertNotIn("could you tell me a bit more", text.lower())
        # Offers a real path forward — either names inventory OR
        # offers an advisor handoff.
        self.assertTrue(
            "advisor" in text.lower() or "lot" in text.lower(),
            f"Fallback reply did not offer a path forward: {text!r}",
        )
