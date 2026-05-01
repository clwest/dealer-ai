"""Phase 8k — verify SYSTEM_PROMPT carries the conversation-flow rules."""

from __future__ import annotations

from django.test import SimpleTestCase

from dealer_ai.services.chat_engine import SYSTEM_PROMPT


class ConversationFlowPromptTests(SimpleTestCase):
    def test_prompt_warns_against_would_you_like_overuse(self):
        self.assertIn('"Would you like…"', SYSTEM_PROMPT)
        self.assertIn("repetitive", SYSTEM_PROMPT)

    def test_prompt_lists_alternative_phrasings(self):
        for phrase in [
            "Want me to",
            "I can also",
            "If you're open to",
            "We could also look at",
        ]:
            self.assertIn(phrase, SYSTEM_PROMPT)

    def test_prompt_has_context_specific_follow_up_rules(self):
        # One vehicle → highlight, no preference question.
        self.assertIn("ONE vehicle shown", SYSTEM_PROMPT)
        # Near-fit → tradeoff sentence + one narrowing question.
        self.assertIn("Near-fit", SYSTEM_PROMPT)
        self.assertIn("tradeoff", SYSTEM_PROMPT)
        # Multiple → preference question.
        self.assertIn("Multiple distinct options", SYSTEM_PROMPT)
        self.assertIn("preference question", SYSTEM_PROMPT)

    def test_prompt_caps_at_one_question_per_reply(self):
        self.assertIn("ONE question per reply", SYSTEM_PROMPT)
        self.assertIn("Vary the wording", SYSTEM_PROMPT)
