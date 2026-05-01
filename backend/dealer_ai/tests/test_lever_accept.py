"""Phase 8s/UX — lever-accept follow-up turns.

When the assistant offers levers (longer term / more down / trade-in /
drivetrain flexibility) and the customer responds:

  - With a specific value ("yes try 84 months", "I can do $5k down",
    "any drivetrain") → reuse the existing extract → merge → rerun
    pipeline. New cards surface; prior constraints stay intact.

  - With a numberless lever ask ("try a longer term", "I can put
    more down") → respond with a one-line clarifier asking for the
    specific value; do NOT rerun the search blindly.

  - With a bare confirmation ("yes", "ok", "sure") AFTER a turn that
    offered levers → respond with a clarifier asking which lever to
    flex; do NOT guess a default.

  - With a bare confirmation NOT preceded by a lever offer → fall
    through to existing flows (no clarifier short-circuit).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    LEVER_CLARIFIER_RESPONSE,
    MORE_DOWN_CLARIFIER_RESPONSE,
)
from dealer_ai.services.intent_parser import (
    is_bare_confirmation,
    lever_intent,
    merge_profile,
    regex_extract,
)
from dealer_ai.tests._mocks import MockLLMProvider, json_reply


# ---- Helpers ---------------------------------------------------------------


def _make_vehicle(
    stock,
    price,
    *,
    model="F-150",
    trim="",
    drivetrain="",
    year=2025,
    body="truck",
    condition="new",
    mileage=0,
):
    return Vehicle.objects.create(
        stock_number=stock,
        year=year,
        make="Ford",
        model=model,
        trim=trim,
        body_style=body,
        condition=condition,
        mileage=mileage,
        price=Decimal(price),
        drivetrain=drivetrain,
    )


def _seed_4wd_truck_pool():
    """Mirror the demo inventory's 4WD-truck shape: one cheap 4WD truck
    that lands as a near-fit at $500/$3k/60mo, plus a cluster of more
    expensive 4WD trucks that only unlock when the customer flexes a
    lever (longer term, more down)."""
    near = _make_vehicle(
        "FF-USED-104",
        "26995",
        model="Ranger",
        trim="XLT SuperCrew 4x4",
        drivetrain="4x4",
    )
    big1 = _make_vehicle(
        "FF-USED-511",
        "35995",
        model="Tundra",
        trim="Limited CrewMax 4x4",
        drivetrain="4x4",
    )
    big2 = _make_vehicle(
        "FF-USED-503",
        "39995",
        model="Ranger",
        trim="Lariat 4x4",
        drivetrain="4x4",
    )
    big3 = _make_vehicle(
        "FF-USED-505",
        "39995",
        model="1500",
        trim="Big Horn 4x4",
        drivetrain="4x4",
    )
    # 2WD/4x2 trucks the strict 4WD filter excludes — they appear when
    # the customer says "any drivetrain".
    twox = _make_vehicle(
        "FF-USED-406",
        "25495",
        model="Colorado",
        trim="WT 4x2",
        drivetrain="RWD",
    )
    return near, big1, big2, big3, twox


# ---- 1. Regex contract — lever phrasings already captured by parser -------


class LeverPhrasingRegexContractTests(TestCase):
    """The lever-accept happy path relies on regex_extract picking up
    specific lever phrasings cleanly. These tests document the contract
    so silent breakage of the parser surfaces here."""

    def test_yes_try_84_months_extracts_term(self):
        self.assertEqual(
            regex_extract("yes try 84 months").get("term_months"), 84
        )

    def test_show_me_72_month_term(self):
        self.assertEqual(
            regex_extract("show me a 72-month term").get("term_months"),
            72,
        )

    def test_let_us_do_a_longer_term_extracts_no_term(self):
        # No specific number → regex returns nothing for term. The
        # numberless-ask clarifier handles this.
        self.assertIsNone(regex_extract("let's try a longer term").get("term_months"))

    def test_more_down_phrasing_extracts(self):
        self.assertEqual(
            regex_extract("I can do $5k down").get("down_payment"), 5000
        )
        self.assertEqual(
            regex_extract("down payment of $5,000").get("down_payment"),
            5000,
        )

    def test_higher_monthly_extracts(self):
        self.assertEqual(
            regex_extract("I could go to $600/mo").get("target_monthly_payment"),
            600,
        )

    def test_strict_4wd_lock_still_works(self):
        self.assertEqual(
            regex_extract("show me 4WD trucks").get("drivetrain"), "4WD"
        )


# ---- 2. Drivetrain release patterns ---------------------------------------


class DrivetrainReleasePatternsTests(TestCase):
    def test_any_drivetrain_emits_any(self):
        self.assertEqual(
            regex_extract("any drivetrain").get("drivetrain"), "any"
        )

    def test_drop_the_4wd_emits_any(self):
        self.assertEqual(
            regex_extract("drop the 4WD").get("drivetrain"), "any"
        )
        self.assertEqual(
            regex_extract("drop 4x4").get("drivetrain"), "any"
        )

    def test_flexible_on_drivetrain_emits_any(self):
        for phrase in (
            "I'm flexible on drivetrain",
            "flexible on the drivetrain",
            "open to any drivetrain",
            "open to drivetrain",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    regex_extract(phrase).get("drivetrain"), "any"
                )

    def test_2wd_is_fine_emits_any(self):
        self.assertEqual(
            regex_extract("2WD is fine").get("drivetrain"), "any"
        )
        self.assertEqual(
            regex_extract("4x2 works too").get("drivetrain"), "any"
        )

    def test_dont_need_4wd_emits_any(self):
        self.assertEqual(
            regex_extract("don't need the 4WD").get("drivetrain"), "any"
        )

    def test_strict_fwd_phrasing_unchanged(self):
        # "FWD is fine" remains a strict FWD lock (existing semantics
        # for sedan/car shoppers — see test_fwd_phrasings in
        # test_post_llm_safety).
        self.assertEqual(
            regex_extract("FWD is fine").get("drivetrain"), "FWD"
        )

    def test_release_then_merge_overwrites_prior_lock(self):
        # The release path is meant to LOOSEN a prior 4WD lock. Merge
        # should overwrite "4WD" with "any" cleanly.
        prior = {"drivetrain": "4WD", "vehicle_type": "truck"}
        merged = merge_profile(prior, {"drivetrain": "any"})
        self.assertEqual(merged["drivetrain"], "any")
        # Other prior fields preserved.
        self.assertEqual(merged["vehicle_type"], "truck")


# ---- 3. is_bare_confirmation / lever_intent helpers -----------------------


class BareConfirmationHelperTests(TestCase):
    def test_recognizes_short_affirmations(self):
        for phrase in (
            "yes", "Yes.", "yeah", "yep", "yup",
            "sure", "ok", "okay", "Ok.", "Okay!",
            "sounds good", "alright", "all right",
            "let's try it", "let's try that",
            "yes please", "yeah please", "ok thanks",
            "sure thing",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(
                    is_bare_confirmation(phrase),
                    f"expected bare confirmation: {phrase!r}",
                )

    def test_rejects_phrases_with_specific_lever(self):
        for phrase in (
            "yes try 84 months",
            "yes 72 months",
            "ok let's do $5k down",
            "sure, I can put $5,000 down",
            "yes please show me 84-month term",
            "yes any drivetrain",
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(
                    is_bare_confirmation(phrase),
                    f"phrase has a specific lever, should not match: {phrase!r}",
                )

    def test_rejects_unrelated_chat(self):
        for phrase in (
            "what's the mileage?",
            "show me trucks",
            "who is the salesperson?",
            "no thanks",
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_bare_confirmation(phrase))


class LeverIntentHelperTests(TestCase):
    def test_longer_term_numberless(self):
        for phrase in (
            "try a longer term",
            "let's do a longer term",
            "longer term please",
            "I'd like a longer loan",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(lever_intent(phrase), "longer_term")

    def test_more_down_numberless(self):
        for phrase in (
            "I can put more down",
            "I could do more down",
            "bigger down payment",
            "larger down payment",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(lever_intent(phrase), "more_down")

    def test_returns_none_when_specific_number_present(self):
        # Phrases that already carry a number defer to regex_extract.
        for phrase in (
            "yes try 84 months",
            "let's do 72 months",
            "I can do $5k down",
            "$5,000 down",
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNone(lever_intent(phrase))

    def test_returns_none_for_bare_confirmations(self):
        self.assertIsNone(lever_intent("yes"))
        self.assertIsNone(lever_intent("sure"))


# ---- 4. End-to-end happy path ---------------------------------------------


class LeverAcceptHappyPathTests(TestCase):
    """Turn 1: 4WD truck, $500/mo, $3k down → 1 card (Ranger near-fit)
    + soft-close lever rule. Turn 2: 'yes try 84 months' → newly
    unlocked cards at term=84, all prior constraints preserved.
    """

    def setUp(self):
        _seed_4wd_truck_pool()
        self.session = ChatSession.objects.create()

    def _run_two_turn_lever_accept(self, turn2_message):
        provider = MockLLMProvider(
            replies=[
                # Turn 1 intent extraction — strict 4WD truck @ $500/$3k/60mo.
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 3000,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                # Turn 1 final reply.
                "The Ranger is the closest match — about $517/mo (W.A.C.).",
                # Turn 2 intent extraction — explicit 84-month accept.
                json_reply({"term_months": 84}),
                # Turn 2 final reply.
                "Here's what opens up at 84 months.",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        # Turn 1 — strict 4WD search produces just the Ranger.
        engine.handle_user_message(
            "I need a 4WD truck around $500 a month over 60 months "
            "with $3000 down"
        )
        # Turn 2 — accept the longer-term lever.
        return engine.handle_user_message(turn2_message), provider

    def test_turn1_surfaces_strict_4wd_plus_flex_options(self):
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 3000,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                "Closest 4WD truck plus flex options.",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message(
            "I need a 4WD truck around $500/mo with $3000 down"
        )
        # Strict 4WD near-fit always present.
        stock_to_v = {v.stock_number: v for v in result.matched_vehicles}
        self.assertIn("FF-USED-104", stock_to_v)
        ranger = stock_to_v["FF-USED-104"]
        # The Ranger is the strict near-fit — no lever-flex annotation.
        self.assertIsNone(getattr(ranger, "_lever_flex_kind", None))
        # 2WD Colorado may appear ONLY as a labeled drivetrain-flex pick.
        if "FF-USED-406" in stock_to_v:
            self.assertEqual(
                getattr(stock_to_v["FF-USED-406"], "_lever_flex_kind", None),
                "drivetrain_flex",
            )
            self.assertIn(
                "2WD",
                getattr(stock_to_v["FF-USED-406"], "_lever_flex_explainer", "")
                or "",
            )
        # Lever-offer flag set (flex options yield a multi-lever close).
        self.assertTrue(
            result.assistant_message.metadata.get("lever_offer"),
            "flex turn should mark message as a lever offer",
        )

    def test_turn2_yes_try_84_months_unlocks_more_cards(self):
        result, _ = self._run_two_turn_lever_accept("yes try 84 months")
        stocks = {v.stock_number for v in result.matched_vehicles}
        # Multiple 4WD trucks now qualify (Ranger fit, Tundra near-fit,
        # 2023 Lariat 4x4 + Ram 1500 Big Horn 4x4 stretches per the
        # lever-sensitivity table).
        self.assertGreater(
            len(result.matched_vehicles),
            1,
            "term=84 should unlock additional 4WD cards beyond the Ranger",
        )
        self.assertIn("FF-USED-104", stocks)  # Ranger still there

    def test_turn2_preserves_prior_constraints(self):
        self._run_two_turn_lever_accept("yes try 84 months")
        self.session.refresh_from_db()
        profile = self.session.extracted_profile or {}
        # Term updated to 84.
        self.assertEqual(profile.get("term_months"), 84)
        # All other prior constraints intact.
        self.assertEqual(profile.get("target_monthly_payment"), 500)
        self.assertEqual(profile.get("down_payment"), 3000)
        self.assertEqual(profile.get("vehicle_type"), "truck")
        self.assertEqual(profile.get("drivetrain"), "4WD")

    def test_turn2_max_three_cards(self):
        result, _ = self._run_two_turn_lever_accept("yes try 84 months")
        self.assertLessEqual(len(result.matched_vehicles), 3)


# ---- 5. Drivetrain-release happy path -------------------------------------


class DrivetrainReleaseHappyPathTests(TestCase):
    def setUp(self):
        _seed_4wd_truck_pool()
        self.session = ChatSession.objects.create()

    def test_any_drivetrain_clears_4wd_lock_and_surfaces_2wd(self):
        provider = MockLLMProvider(
            replies=[
                # Turn 1 — strict 4WD.
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 3000,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                "Strict 4WD reply.",
                # Turn 2 — release.
                json_reply({}),
                "Now opening up to 2WD.",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        # Turn 1 — strict 4WD pipeline always includes the Ranger.
        # Lever-flex picks (Colorado as drivetrain_flex, Tundra as
        # longer_term) may also surface; their flex annotations are
        # what make them honest. The strict near-fit is the Ranger.
        result1 = engine.handle_user_message(
            "I need a 4WD truck around $500/mo with $3000 down"
        )
        stocks_1 = {v.stock_number for v in result1.matched_vehicles}
        self.assertIn("FF-USED-104", stocks_1)
        for v in result1.matched_vehicles:
            if v.stock_number == "FF-USED-406":
                # Pre-release, the 2WD Colorado is allowed only as a
                # drivetrain-flex pick.
                self.assertEqual(
                    getattr(v, "_lever_flex_kind", None),
                    "drivetrain_flex",
                )
        # Turn 2 — drop drivetrain.
        result2 = engine.handle_user_message("any drivetrain")
        stocks = {v.stock_number for v in result2.matched_vehicles}
        # 2WD Colorado now surfaces alongside the 4WD Ranger.
        self.assertIn("FF-USED-406", stocks)
        # Profile drivetrain set to "any" (loose).
        self.session.refresh_from_db()
        self.assertEqual(
            (self.session.extracted_profile or {}).get("drivetrain"),
            "any",
        )


# ---- 6. Bare-confirmation clarifier ---------------------------------------


class BareConfirmationClarifierTests(TestCase):
    def setUp(self):
        _seed_4wd_truck_pool()
        self.session = ChatSession.objects.create()

    def test_yes_after_lever_offer_returns_clarifier(self):
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 3000,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                "Closest match.",
                # Turn 2 — should NEVER reach the LLM (clarifier short-circuit).
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        engine.handle_user_message(
            "I need a 4WD truck around $500/mo with $3000 down"
        )
        result = engine.handle_user_message("yes")
        # Canned clarifier reply.
        self.assertEqual(
            result.assistant_message.content, LEVER_CLARIFIER_RESPONSE
        )
        meta = result.assistant_message.metadata or {}
        self.assertEqual(meta.get("mode"), "lever_clarifier")
        self.assertEqual(meta.get("lever_clarifier_kind"), "bare_confirmation")
        # No cards on a clarifier turn — we haven't re-run the search.
        self.assertEqual(result.matched_vehicles, [])
        # Profile NOT mutated (no lever specified yet).
        self.session.refresh_from_db()
        profile = self.session.extracted_profile or {}
        self.assertEqual(profile.get("drivetrain"), "4WD")
        self.assertEqual(profile.get("term_months"), 60)
        # Clarifier should itself be marked as a lever offer so a
        # follow-up "yes" continues to ask, not loop into the normal
        # pipeline.
        self.assertTrue(meta.get("lever_offer"))

    def test_yes_with_no_prior_lever_offer_falls_through(self):
        # Discovery / vehicle-search turn that does NOT trigger the
        # lever-offer rule. A bare "yes" next turn should NOT short-
        # circuit to the lever clarifier — existing flows handle it.
        # (The discovery flow doesn't surface vehicles; matched stays
        # empty regardless. What we're verifying is that the clarifier
        # response is NOT what comes back.)
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Welcome! What kind of vehicle are you looking for?",
                json_reply({}),
                "Sure thing — could you share more about your budget?",
            ]
        )
        engine = ChatEngine(session=self.session, provider=provider)
        engine.handle_user_message("hi")
        result = engine.handle_user_message("yes")
        # Reply is NOT the lever clarifier — the LLM-side response runs.
        self.assertNotEqual(
            result.assistant_message.content, LEVER_CLARIFIER_RESPONSE
        )
        meta = result.assistant_message.metadata or {}
        self.assertNotEqual(meta.get("mode"), "lever_clarifier")


# ---- 7. Numberless-lever-ask clarifier ------------------------------------


class NumberlessLeverAskClarifierTests(TestCase):
    def setUp(self):
        _seed_4wd_truck_pool()
        self.session = ChatSession.objects.create()
        # Pre-load profile to simulate mid-conversation state.
        self.session.extracted_profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "vehicle_type": "truck",
            "drivetrain": "4WD",
        }
        self.session.save()

    def test_longer_term_numberless_returns_clarifier(self):
        provider = MockLLMProvider(replies=[])
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("try a longer term")
        # Canned longer-term clarifier — payload depends on current term.
        content = result.assistant_message.content
        self.assertIn("72 or 84 months", content)
        # Provider was never called (no LLM round-trips on a clarifier).
        self.assertEqual(provider.calls, [])
        meta = result.assistant_message.metadata or {}
        self.assertEqual(meta.get("mode"), "lever_clarifier")
        self.assertEqual(meta.get("lever_clarifier_kind"), "longer_term")
        # No cards.
        self.assertEqual(result.matched_vehicles, [])
        # Profile unchanged.
        self.session.refresh_from_db()
        self.assertEqual(
            (self.session.extracted_profile or {}).get("term_months"), 60
        )

    def test_more_down_numberless_returns_clarifier(self):
        provider = MockLLMProvider(replies=[])
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("I can put more down")
        self.assertEqual(
            result.assistant_message.content, MORE_DOWN_CLARIFIER_RESPONSE
        )
        meta = result.assistant_message.metadata or {}
        self.assertEqual(meta.get("lever_clarifier_kind"), "more_down")

    def test_longer_term_clarifier_redirects_at_term_84(self):
        # If the customer is already at 84 months, the clarifier should
        # not propose a longer term — redirect to a different lever.
        self.session.extracted_profile["term_months"] = 84
        self.session.save()
        provider = MockLLMProvider(replies=[])
        engine = ChatEngine(session=self.session, provider=provider)
        result = engine.handle_user_message("longer term please")
        content = result.assistant_message.content
        self.assertIn("at or beyond the practical maximum", content)
        self.assertNotIn("72 or 84", content)


# ---- 8. lever_offer metadata flag is set on the right branches -----------


class LeverOfferMetadataFlagTests(TestCase):
    """The flag drives the bare-confirmation clarifier. It must fire for
    the two single-card branches (single near-fit, single stretch) and
    NOT fire for multi-card / discovery / non-budget turns."""

    def test_flag_set_on_single_near_fit_no_stretch(self):
        # Only one 4WD truck within near-fit — the Ranger.
        _make_vehicle(
            "FF-USED-104",
            "26995",
            model="Ranger",
            trim="XLT 4x4",
            drivetrain="4x4",
        )
        # All other 4WD trucks are way over the cap (> $650/mo).
        _make_vehicle(
            "FF-USED-503",
            "55000",
            model="Ranger",
            trim="Lariat 4x4",
            drivetrain="4x4",
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 3000,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                "ok",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "4WD truck $500 over 60 months with $3000 down"
        )
        self.assertEqual(len(result.matched_vehicles), 1)
        self.assertTrue(result.assistant_message.metadata.get("lever_offer"))

    def test_flag_set_on_single_stretch_only(self):
        # No fits, no near-fits, exactly one realistic stretch (Ranger
        # at $0 down lands as over_budget within the $150 cap).
        _make_vehicle(
            "FF-USED-104",
            "26995",
            model="Ranger",
            trim="XLT 4x4",
            drivetrain="4x4",
        )
        _make_vehicle(
            "FF-USED-503",
            "55000",
            model="Ranger",
            trim="Lariat 4x4",
            drivetrain="4x4",
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 0,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                "ok",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "4WD truck $500 over 60 months with $0 down"
        )
        self.assertEqual(len(result.matched_vehicles), 1)
        self.assertEqual(
            getattr(result.matched_vehicles[0], "_budget_fit", None),
            "over_budget",
        )
        self.assertTrue(result.assistant_message.metadata.get("lever_offer"))

    def test_flag_NOT_set_on_multi_card_turn(self):
        # 1 near-fit + 2 stretches → 3 cards. This is the rich
        # opportunity branch, not a soft-close lever offer.
        _make_vehicle("NEAR", "25500", model="F-150", drivetrain="4x4")
        _make_vehicle("OV1", "27500", model="F-150", drivetrain="4x4")
        _make_vehicle("OV2", "27800", model="F-150", drivetrain="4x4")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "down_payment": 0,
                        "term_months": 60,
                        "vehicle_type": "truck",
                        "drivetrain": "4WD",
                    }
                ),
                "ok",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "4WD trucks $500 over 60 months $0 down"
        )
        self.assertGreater(len(result.matched_vehicles), 1)
        self.assertFalse(
            bool(result.assistant_message.metadata.get("lever_offer")),
            "multi-card turn should not flag as lever offer",
        )

    def test_flag_NOT_set_on_discovery_turn(self):
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Hi! What kind of vehicle?"],
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("just looking around")
        self.assertFalse(
            bool(result.assistant_message.metadata.get("lever_offer"))
        )
