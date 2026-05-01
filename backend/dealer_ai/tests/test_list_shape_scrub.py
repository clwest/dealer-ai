"""Item 2 — bullet / pipe / numbered / markdown-heading shape scrub.

Cards already render price, mileage, Stock #, features, and badges.
The assistant prose only needs to GUIDE ATTENTION; restating that
data in bullet / pipe / numbered shapes is forbidden when cards are
present (BEHAVIOR_LAYER §"UI / Source-of-Truth Contract"). The
prompt rule alone doesn't survive on llama3.2 — the smoke run
showed scenarios 2 (multi-near) and 3 (anchor follow-up) leaking
both shapes — so this scrub is the post-generation safety net.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    LIST_SHAPE_FALLBACK,
    scrub_list_shape,
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


# ---- scrub_list_shape unit tests -----------------------------------------


class ScrubListShapeUnitTests(SimpleTestCase):
    """Pure-function coverage. Each test exercises a specific
    detection class, plus the has_cards gate, plus the fallback path.
    """

    def test_normal_prose_untouched(self):
        text = (
            "The Ranger is really close at about $517/mo. The Tundra "
            "opens up if you stretch the term a bit. Want a closer "
            "look at either?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_has_cards_false_keeps_bullets(self):
        # Help / clarifier turns may legitimately use lists when no
        # cards are showing — leave them alone.
        text = (
            "Here are some things to think about:\n"
            "* What's your monthly target?\n"
            "* New or used?\n"
            "* Drivetrain preference?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=False
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_bullet_vehicle_specs_removed(self):
        text = (
            "Here are some options:\n"
            "* 2020 Chevrolet Colorado WT 4x2 | Stock #FF-USED-406 | "
            "USED | 55,000 mi | $25,495\n"
            "* 2019 Ford Ranger XLT SuperCrew 4x4 | Stock #FF-USED-104\n"
            "Would you like a closer look?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("* 2020", cleaned)
        self.assertNotIn("* 2019", cleaned)
        self.assertNotIn("Stock #FF-USED-406", cleaned)
        self.assertIn("Here are some options:", cleaned)
        self.assertIn("Would you like a closer look?", cleaned)

    def test_pipe_delimited_rows_removed(self):
        # Two or more ` | ` separators on a line is the spec-dump
        # shape. A single ` | ` is allowed (e.g., "USB | bluetooth").
        text = (
            "Three good options today.\n"
            "Ranger | Stock #FF-USED-104 | $26,995 | $517/mo\n"
            "Tundra | Stock #FF-USED-511 | $35,995 | $609/mo\n"
            "Want me to line one up?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("FF-USED-104", cleaned)
        self.assertNotIn("FF-USED-511", cleaned)
        self.assertIn("Three good options today.", cleaned)
        self.assertIn("Want me to line one up?", cleaned)

    def test_single_pipe_in_prose_kept(self):
        # One ` | ` is allowed — e.g., "USB | bluetooth", "AM | FM".
        text = "The Ranger has USB | bluetooth audio. Want a look?"
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_markdown_bold_headings_removed(self):
        # Standalone "**Heading**" lines get dropped. Inline
        # "**bold**" mid-sentence does not.
        text = (
            "Here's a quick rundown of the Ranger.\n"
            "\n"
            "**Engine and Performance**\n"
            "It runs the 2.3L EcoBoost — punchy and efficient.\n"
            "\n"
            "**Interior and Features**\n"
            "Seats five with Sync 3. Want a closer look?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("**Engine and Performance**", cleaned)
        self.assertNotIn("**Interior and Features**", cleaned)
        self.assertIn("2.3L EcoBoost", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_inline_bold_kept(self):
        text = (
            "The Ranger has the **FX4 Off-Road** package, which is a "
            "great fit for camping. Want a look?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_numbered_lines_removed(self):
        text = (
            "Two paths forward.\n"
            "1. Look at the Ranger first.\n"
            "2. Then compare to the Tundra.\n"
            "Which sounds better?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("1. Look at the Ranger", cleaned)
        self.assertNotIn("2. Then compare", cleaned)
        self.assertIn("Two paths forward.", cleaned)
        self.assertIn("Which sounds better?", cleaned)

    def test_tab_indented_sub_bullets_removed(self):
        # Real shape from scenario 3: "\t+ Lightning Blue".
        text = (
            "Color options coming up.\n"
            "\t+ Lightning Blue (as shown)\n"
            "\t+ Agate Black Metallic\n"
            "\t+ Oxford White\n"
            "Want to keep going?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertNotIn("Lightning Blue", cleaned)
        self.assertNotIn("Agate Black", cleaned)
        self.assertIn("Want to keep going?", cleaned)

    def test_em_dash_in_prose_not_treated_as_bullet(self):
        # Em-dash sentences look superficially like bullet lines but
        # they're real prose.
        text = (
            "The Ranger — really practical for hunting trips — runs "
            "around $517/mo. Want a look?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_dashed_separator_not_treated_as_bullet(self):
        # ASCII-art separators have no content after the dashes.
        text = (
            "The Ranger is close at $517/mo.\n"
            "---\n"
            "Want a look?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        # `---` alone has no following content — not a bullet line.
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_closing_question_preserved(self):
        # Bullet rows before the question; question survives.
        text = (
            "Here are some options:\n"
            "* Ranger | Stock #FF-USED-104 | $26,995\n"
            "* Tundra | Stock #FF-USED-511 | $35,995\n"
            "Would you rather look at a longer term or flexible "
            "drivetrain?"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertFalse(fallback)
        self.assertIn(
            "Would you rather look at a longer term or flexible "
            "drivetrain?",
            cleaned,
        )

    def test_fallback_used_when_only_lists_remain(self):
        # Reply is purely bullet rows — nothing meaningful remains
        # after stripping. Fallback message takes over.
        text = (
            "* Ranger | $517/mo\n"
            "* Tundra | $609/mo\n"
            "* Maverick | $486/mo"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertTrue(fallback)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)
        # Fallback ends with a question — preserves the soft-close
        # contract.
        self.assertIn("?", cleaned)

    def test_fallback_used_when_only_short_remnant_remains(self):
        # A single-word remnant after stripping isn't a coherent
        # reply — fallback fires.
        text = (
            "Hmm.\n"
            "* Ranger | $517/mo\n"
            "* Tundra | $609/mo"
        )
        cleaned, changed, fallback = scrub_list_shape(
            text, has_cards=True
        )
        self.assertTrue(changed)
        self.assertTrue(fallback)
        self.assertEqual(cleaned, LIST_SHAPE_FALLBACK)

    def test_empty_reply_unchanged(self):
        cleaned, changed, fallback = scrub_list_shape(
            "", has_cards=True
        )
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)
        self.assertFalse(fallback)


# ---- ChatEngine integration tests ----------------------------------------


class ListShapeIntegrationTests(TestCase):
    """End-to-end coverage. Each test runs through the full
    `handle_user_message` pipeline to verify the scrub fires (or
    doesn't) and the metadata flag chain stays correct.
    """

    def _ranger_session(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        return ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )

    def test_scrub_fires_on_card_session_bullet_reply(self):
        # User-spec test #1 — bullet vehicle specs removed end-to-end.
        session = self._ranger_session()
        bullet_reply = (
            "Here are some options:\n"
            "* 2019 Ford Ranger XLT SuperCrew 4x4 | Stock #FF-USED-104 | "
            "$26,995 | est ~$517/mo (W.A.C.)\n"
            "Want a closer look?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), bullet_reply]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("* 2019 Ford Ranger", content)
        self.assertNotIn("Stock #FF-USED-104", content)
        self.assertIn("Here are some options:", content)
        self.assertIn("Want a closer look?", content)
        meta = result.assistant_message.metadata
        self.assertIn("list_shape", meta.get("scrubs", []))
        self.assertEqual(meta.get("flag"), "list_shape_scrubbed")

    def test_scrub_fires_on_pipe_delimited_reply(self):
        # User-spec test #2 — pipe-delimited rows removed end-to-end.
        session = self._ranger_session()
        pipe_reply = (
            "Three options here.\n"
            "Ranger | FF-USED-104 | $26,995 | $517/mo\n"
            "What sounds good?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), pipe_reply]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertNotIn("Ranger | FF-USED-104", content)
        self.assertNotIn("FF-USED-104", content)
        self.assertIn("What sounds good?", content)
        meta = result.assistant_message.metadata
        self.assertIn("list_shape", meta.get("scrubs", []))

    def test_normal_prose_reply_unchanged(self):
        # User-spec test #3 — clean prose passes through untouched.
        session = self._ranger_session()
        clean_reply = (
            "The Ranger is really close at about $517/mo. Want me to "
            "line one up?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), clean_reply]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        self.assertEqual(
            result.assistant_message.content, clean_reply
        )
        meta = result.assistant_message.metadata
        self.assertNotIn("list_shape", meta.get("scrubs", []))
        self.assertNotEqual(
            meta.get("flag"), "list_shape_scrubbed"
        )

    def test_no_card_reply_keeps_bullets(self):
        # User-spec test #4 — no matched_vehicles, so the scrub gate
        # blocks. Construct a session that produces a clarifier-style
        # turn without cards by sending an off-topic / vague message
        # that doesn't match any inventory.
        session = ChatSession.objects.create(extracted_profile={})
        bullet_clarifier = (
            "Happy to help — could you share:\n"
            "* What's your monthly target?\n"
            "* New or used?\n"
            "* Truck or SUV?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), bullet_clarifier]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I'm just browsing for now"
        )

        # No cards → list scrub gate blocks → bullets preserved.
        self.assertEqual(len(list(result.matched_vehicles)), 0)
        self.assertEqual(
            result.assistant_message.content, bullet_clarifier
        )
        meta = result.assistant_message.metadata
        self.assertNotIn("list_shape", meta.get("scrubs", []))

    def test_list_scrub_stacks_with_extra_payment_quote(self):
        # User-spec test #5 — both list-shape and extra-payment-quote
        # scrubs fire; flag promotes to multiple_scrubs_fired; both
        # entries in metadata.scrubs.
        session = self._ranger_session()
        bad = (
            "Two great options.\n"
            "* Ranger at $517/mo here\n"
            "The Ranger comes in at $517/mo over 60 months. Want a "
            "closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        # Bullet line gone.
        self.assertNotIn("* Ranger at $517/mo here", content)
        # First $517 (in the surviving prose sentence) preserved as
        # the lead. Total occurrences ≤ 1.
        self.assertLessEqual(content.count("$517/mo"), 1)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("list_shape", scrubs)
        self.assertIn("extra_payment_quote", scrubs)
        # Flag invariant: ≥ 2 scrubs ⇒ multiple_scrubs_fired.
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")

    def test_full_pipe_dump_falls_back_to_canned_reply(self):
        # When the LLM emits ONLY pipe-delimited rows with no real
        # prose between them, the scrub strips everything — the
        # fallback canned reply takes over.
        session = self._ranger_session()
        pipe_dump = (
            "Ranger | FF-USED-104 | $26,995 | $517/mo\n"
            "Tundra | FF-USED-511 | $35,995 | $609/mo\n"
            "Maverick | FF-USED-113 | $27,995 | $546/mo"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), pipe_dump]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        self.assertEqual(
            result.assistant_message.content, LIST_SHAPE_FALLBACK
        )
        meta = result.assistant_message.metadata
        self.assertIn("list_shape", meta.get("scrubs", []))
        self.assertTrue(meta.get("list_shape_fallback"))

    def test_internal_confusion_fallback_blocks_list_scrub(self):
        # If the higher-priority internal_confusion_fallback already
        # replaced the body with its canned reply, list scrub must
        # not fire on top of it (its canned reply has no list shape
        # anyway, but the gate is the contract).
        session = self._ranger_session()
        confused = (
            "Here's a revised response that follows the guidelines:\n"
            "* Ranger at $517/mo\n"
            "Want a look?"
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), confused]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        meta = result.assistant_message.metadata
        # Internal-confusion fallback claims the flag slot.
        self.assertEqual(
            meta.get("flag"), "internal_confusion_fallback"
        )
        # List scrub did not fire.
        self.assertNotIn("list_shape", meta.get("scrubs", []))
