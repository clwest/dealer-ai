"""Item 4 — drivetrain hallucination guard.

Cards already render the drivetrain authoritatively. The smoke run
showed the LLM emitting:

  "the Colorado is available in both front-wheel drive and four-wheel
  drive configurations"

for a Colorado card whose `Vehicle.drivetrain` is `RWD` only — the
4WD claim is fabricated. This scrub catches that class of false
attribute claim. The lever-flex GOOD-example phrasing
(*"if you're flexible on drivetrain, the Colorado slips under your
target"*) must continue to pass untouched — that's a preference
reference, not a claim about the card.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.serializers import VehicleSerializer
from dealer_ai.services.chat_engine import (
    ChatEngine,
    DRIVETRAIN_CLAIM_FALLBACK,
    customer_drivetrain_label,
    scrub_drivetrain_claims,
)

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(
    stock,
    price,
    *,
    model="F-150",
    trim="",
    drivetrain="4x4",
    body="truck",
    condition="used",
    year=2025,
):
    return Vehicle.objects.create(
        stock_number=stock,
        year=year,
        make="Ford",
        model=model,
        trim=trim,
        body_style=body,
        condition=condition,
        price=Decimal(price),
        drivetrain=drivetrain,
    )


# ---- customer_drivetrain_label unit tests --------------------------------


class CustomerDrivetrainLabelTests(SimpleTestCase):
    """Single source of truth: 4x4→4WD, RWD/4x2→2WD, FWD→FWD,
    AWD→AWD. Used by the serializer and by the scrub.
    """

    def test_four_by_four_maps_to_4wd(self):
        self.assertEqual(customer_drivetrain_label("4x4"), "4WD")

    def test_4wd_input_passes_as_4wd(self):
        # Customer-facing input shouldn't be mutated.
        self.assertEqual(customer_drivetrain_label("4WD"), "4WD")

    def test_4x2_maps_to_2wd(self):
        self.assertEqual(customer_drivetrain_label("4x2"), "2WD")

    def test_rwd_maps_to_2wd(self):
        self.assertEqual(customer_drivetrain_label("RWD"), "2WD")

    def test_fwd_passes_through(self):
        self.assertEqual(customer_drivetrain_label("FWD"), "FWD")

    def test_awd_passes_through(self):
        self.assertEqual(customer_drivetrain_label("AWD"), "AWD")

    def test_empty_returns_empty(self):
        self.assertEqual(customer_drivetrain_label(""), "")
        self.assertEqual(customer_drivetrain_label(None), "")

    def test_unknown_passes_through(self):
        self.assertEqual(customer_drivetrain_label("DUO"), "DUO")

    def test_case_insensitive_input(self):
        self.assertEqual(customer_drivetrain_label("rwd"), "2WD")
        self.assertEqual(customer_drivetrain_label("Awd"), "AWD")
        self.assertEqual(customer_drivetrain_label("4X4"), "4WD")


# ---- VehicleSerializer drivetrain field ---------------------------------


class VehicleSerializerDrivetrainTests(TestCase):
    """The serializer must expose customer-facing drivetrain so the
    frontend chip / detail modal show 4WD / 2WD / AWD / FWD.
    """

    def test_4x4_vehicle_serializes_as_4wd(self):
        v = _make_vehicle("DT-4x4", "30000", model="F-150", drivetrain="4x4")
        data = VehicleSerializer(v).data
        self.assertEqual(data["drivetrain"], "4WD")

    def test_rwd_vehicle_serializes_as_2wd(self):
        v = _make_vehicle("DT-RWD", "26000", model="Mustang", drivetrain="RWD")
        data = VehicleSerializer(v).data
        self.assertEqual(data["drivetrain"], "2WD")

    def test_fwd_vehicle_serializes_as_fwd(self):
        v = _make_vehicle("DT-FWD", "20000", model="Escape", drivetrain="FWD")
        data = VehicleSerializer(v).data
        self.assertEqual(data["drivetrain"], "FWD")

    def test_awd_vehicle_serializes_as_awd(self):
        v = _make_vehicle("DT-AWD", "32000", model="Bronco", drivetrain="AWD")
        data = VehicleSerializer(v).data
        self.assertEqual(data["drivetrain"], "AWD")

    def test_empty_drivetrain_serializes_as_empty_string(self):
        v = _make_vehicle("DT-NONE", "20000", drivetrain="")
        data = VehicleSerializer(v).data
        self.assertEqual(data["drivetrain"], "")


# ---- scrub_drivetrain_claims unit tests ---------------------------------


class ScrubDrivetrainClaimsUnitTests(SimpleTestCase):
    """Pure-function coverage. Uses lightweight stand-in objects with
    just `model` and `drivetrain` attrs — the scrub doesn't need a
    full Vehicle.
    """

    class _FakeCard:
        def __init__(self, model: str, drivetrain: str):
            self.model = model
            self.drivetrain = drivetrain

    def _ranger_4x4(self):
        return self._FakeCard("Ranger", "4x4")

    def _colorado_rwd(self):
        return self._FakeCard("Colorado", "RWD")

    def _maverick_fwd(self):
        return self._FakeCard("Maverick", "FWD")

    def _bronco_awd(self):
        return self._FakeCard("Bronco", "AWD")

    def test_no_cards_returns_unchanged(self):
        text = "The Colorado is 4WD."
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_empty_text_returns_unchanged(self):
        cleaned, changed, fallback = scrub_drivetrain_claims(
            "", matched=[self._ranger_4x4()]
        )
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_correct_drivetrain_claim_untouched(self):
        text = "The Ranger is 4x4 — perfect for off-road."
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._ranger_4x4()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertFalse(fallback)

    def test_correct_4wd_claim_for_4x4_card_untouched(self):
        # Customer-facing token "4WD" matches internal "4x4".
        text = "The Ranger is 4WD. Want a closer look?"
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._ranger_4x4()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_2wd_claim_for_rwd_card_untouched(self):
        # "2WD" is ambiguous — RWD passes.
        text = "The Colorado is 2WD. Want a closer look?"
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_2wd_claim_for_fwd_card_untouched(self):
        text = "The Maverick is 2WD. Want a closer look?"
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._maverick_fwd()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_2wd_claim_for_awd_card_stripped(self):
        # AWD is 4-driven, NOT a 2-driven match.
        text = (
            "The Bronco is great. The Bronco is 2WD only. Want a "
            "closer look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._bronco_awd()]
        )
        self.assertTrue(changed)
        self.assertNotIn("2WD only", cleaned)
        self.assertIn("Want a closer look?", cleaned)
        self.assertIn("The Bronco is great.", cleaned)

    def test_4wd_claim_for_rwd_card_stripped(self):
        # The smoke shape — "the Colorado is 4WD" is wrong.
        text = (
            "Some great options today. The Colorado is 4WD. Want a "
            "look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertTrue(changed)
        self.assertNotIn("Colorado is 4WD", cleaned)
        self.assertIn("Some great options today", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_available_in_both_2wd_and_4wd_for_rwd_card_stripped(self):
        # The exact smoke shape: "available in both X and Y
        # configurations" where Y is wrong.
        text = (
            "Three good options. The Colorado is available in both "
            "front-wheel drive and four-wheel drive configurations. "
            "Want a closer look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertTrue(changed)
        self.assertNotIn("four-wheel drive", cleaned)
        self.assertNotIn(
            "front-wheel drive and", cleaned  # whole sentence stripped
        )
        self.assertIn("Three good options", cleaned)
        self.assertIn("Want a closer look?", cleaned)

    def test_pronoun_subject_inherits_from_prior_sentence(self):
        # "It comes in both 2WD and 4WD" — pronoun referent is the
        # Colorado from the previous sentence.
        text = (
            "The Colorado is a great option. It also comes in both "
            "two-wheel drive and four-wheel drive options. Want a "
            "look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertTrue(changed)
        # The pronoun-referent sentence is stripped.
        self.assertNotIn("four-wheel drive", cleaned)
        self.assertIn("The Colorado is a great option", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_lever_flex_flexible_on_drivetrain_untouched(self):
        # Canonical lever-flex GOOD example. Must NOT trigger the
        # scrub even though "4WD" appears near "Colorado".
        text = (
            "The Ranger is really close at about $517/mo. If you're "
            "flexible on drivetrain, the Colorado slips under your "
            "target."
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text,
            matched=[self._ranger_4x4(), self._colorado_rwd()],
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_lever_flex_with_explicit_drivetrain_token_in_preference_untouched(self):
        # Even with an explicit "4WD" token in the sentence, when
        # the surrounding phrase is "flexible on", treat as
        # preference, not claim.
        text = (
            "If you're flexible on 4WD, the Colorado opens up. Want "
            "a closer look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_your_ask_phrasing_untouched(self):
        # Lever-flex caption: "(your ask: 4WD)" stays.
        text = (
            "The Colorado is 2WD — flexible-drivetrain option (your "
            "ask: 4WD)."
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_generic_drivetrain_talk_no_card_mentioned_untouched(self):
        # No specific card referenced — generic discussion is fine.
        text = (
            "4WD trucks are popular for off-roading. Want a closer "
            "look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._ranger_4x4(), self._colorado_rwd()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_multi_card_one_correct_one_false_only_false_stripped(self):
        # "the Ranger is 4WD and the Colorado is 4WD" — first half
        # is true (Ranger 4x4), second half false (Colorado RWD).
        # Whole sentence stripped because at least one claim is
        # false.
        text = (
            "Two options. The Ranger is 4WD and the Colorado is "
            "4WD. Want a look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text,
            matched=[self._ranger_4x4(), self._colorado_rwd()],
        )
        self.assertTrue(changed)
        self.assertNotIn("Colorado is 4WD", cleaned)
        self.assertIn("Two options", cleaned)
        self.assertIn("Want a look?", cleaned)

    def test_multi_card_both_correct_untouched(self):
        text = (
            "Two options. The Ranger is 4WD and the Colorado is "
            "2WD. Want a look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text,
            matched=[self._ranger_4x4(), self._colorado_rwd()],
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_drivetrain_attribute_line_stripped(self):
        # Markdown attribute line "**Drivetrain:** 4WD" for a
        # non-4x4 card.
        text = (
            "The Colorado is a great option. **Drivetrain:** 4WD. "
            "Want a closer look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertTrue(changed)
        self.assertNotIn("Drivetrain:** 4WD", cleaned)

    def test_fallback_when_only_false_claims_remain(self):
        text = (
            "The Colorado is 4WD. The Colorado is 4x4. Bronco is "
            "RWD."
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text,
            matched=[self._colorado_rwd(), self._bronco_awd()],
        )
        self.assertTrue(changed)
        self.assertTrue(fallback)
        self.assertEqual(cleaned, DRIVETRAIN_CLAIM_FALLBACK)

    def test_no_drivetrain_claim_in_text_untouched(self):
        text = (
            "The Colorado is a great option for outdoor adventures. "
            "Want a closer look?"
        )
        cleaned, changed, fallback = scrub_drivetrain_claims(
            text, matched=[self._colorado_rwd()]
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)


# ---- ChatEngine integration tests ---------------------------------------


class DrivetrainClaimIntegrationTests(TestCase):
    def _ranger_session(self):
        _make_vehicle(
            "FF-USED-104", "26995", model="Ranger", drivetrain="4x4"
        )
        return ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )

    def _colorado_session(self):
        _make_vehicle(
            "FF-USED-406", "25495", model="Colorado", drivetrain="RWD"
        )
        return ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )

    def test_integration_strip_smoke_shape(self):
        # The exact LLM output shape from the smoke run.
        session = self._colorado_session()
        bad = (
            "The Colorado is a great option. The Colorado is "
            "available in both front-wheel drive and four-wheel "
            "drive configurations. Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "$500/mo, $3k down, truck"
        )
        content = result.assistant_message.content
        self.assertNotIn("four-wheel drive", content)
        self.assertNotIn("front-wheel drive", content)
        self.assertIn("Want a closer look?", content)
        meta = result.assistant_message.metadata
        self.assertIn("drivetrain_claim", meta.get("scrubs", []))
        self.assertEqual(
            meta.get("flag"), "drivetrain_claim_scrubbed"
        )

    def test_integration_clean_reply_unchanged(self):
        session = self._ranger_session()
        clean = (
            "The Ranger is really close at about $517/mo. The "
            "Ranger is 4WD — perfect for tough terrain. Want a "
            "closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "$500/mo, $3k down, 4WD truck"
        )
        self.assertEqual(result.assistant_message.content, clean)
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "drivetrain_claim", meta.get("scrubs", [])
        )

    def test_integration_no_card_session_unchanged(self):
        # When no matched_vehicles, the gate blocks the scrub.
        session = ChatSession.objects.create(extracted_profile={})
        clarifier = (
            "Happy to help. Are you thinking 2WD or 4WD? The "
            "Colorado is available in both 2WD and 4WD on the lot "
            "currently."
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), clarifier]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("just browsing for now")
        self.assertEqual(len(list(result.matched_vehicles)), 0)
        self.assertEqual(result.assistant_message.content, clarifier)
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "drivetrain_claim", meta.get("scrubs", [])
        )

    def test_integration_lever_flex_phrasing_unchanged(self):
        # Multi-card session with a Colorado RWD and Ranger 4x4.
        # The canonical GOOD lever-flex close mentions both
        # "Colorado" and "drivetrain" but is a preference, not a
        # claim. Must pass.
        _make_vehicle(
            "FF-USED-104", "26995", model="Ranger", drivetrain="4x4"
        )
        _make_vehicle(
            "FF-USED-406", "25495", model="Colorado", drivetrain="RWD"
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        good = (
            "The Ranger is really close at about $517/mo. If you're "
            "flexible on drivetrain, the Colorado actually slips "
            "under your target. Would you rather look at a longer "
            "term or flexible drivetrain?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), good])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "4WD truck around $500/mo with $3k down"
        )
        # The lever-flex GOOD example must pass through.
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "drivetrain_claim", meta.get("scrubs", [])
        )

    def test_integration_stacks_with_list_shape(self):
        # The scrub stacks with list_shape — both fire when a
        # bullet-rendered drivetrain claim is wrong.
        session = self._colorado_session()
        bad = (
            "Here are some options:\n"
            "* The Colorado is 4WD\n"
            "Want a look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "$500/mo, $3k down, truck"
        )
        content = result.assistant_message.content
        self.assertNotIn("Colorado is 4WD", content)
        self.assertNotIn("* The Colorado", content)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("list_shape", scrubs)
        # Drivetrain claim was inside the bullet — list_shape
        # stripped it before the drivetrain scrub got there. Both
        # paths leave the customer with no false claim.
        self.assertNotIn("4WD", content)

    def test_integration_fabricated_inventory_guard_still_works(self):
        # User-spec test #7 — the existing fabricated_inventory
        # guard must still wholesale-replace when the LLM cites a
        # Stock # not in matched_vehicles. Drivetrain scrub must
        # not interfere.
        session = self._colorado_session()
        bad_stock = (
            "Try Stock #FAKE-999 instead — it lands at $705/mo."
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), bad_stock]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "$500/mo, $3k down, truck"
        )
        meta = result.assistant_message.metadata
        # Wholesale replacement won — drivetrain scrub is gated
        # behind fabricated_inventory_fired.
        self.assertEqual(
            meta.get("flag"), "fabricated_inventory"
        )
        self.assertNotIn(
            "drivetrain_claim", meta.get("scrubs", [])
        )
        self.assertNotIn("FAKE-999", result.assistant_message.content)
