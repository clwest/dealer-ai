"""Phase 8s/UX: model-name follow-up anchor.

When the customer references a model in the previous assistant turn's
matched_vehicles ("Tell me more about the Ranger"), the chat engine
must anchor to that specific vehicle. Bypasses build_budget_context's
body_style+model filter chain — which can return zero matches when
the LLM-extracted profile has the wrong vehicle_type for the cited
model. That regression produced "5.0L V8" hallucinations on a Ranger
follow-up because the LLM flipped vehicle_type from truck to suv and
the resulting AVAILABLE INVENTORY block went empty.

Tests covered:
1. Helper anchors to the prior-turn matched model.
2. Helper returns None when model wasn't in the prior turn.
3. Helper returns None when current turn introduces budget reframe
   (target_monthly_payment / max_price / vehicle_type).
4. End-to-end: anchor wins over LLM-emitted vehicle_type='suv' flip.
5. End-to-end: anchor persists current_vehicle_id in profile.
6. End-to-end: subsequent pronoun follow-up resolves to anchored vehicle.
7. _format_vehicle_block enriches the single-vehicle block with engine,
   drivetrain, transmission, fuel_type, description; multi-vehicle
   block omits the detail block.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatMessage, ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    _format_vehicle_block,
)
from dealer_ai.tests._mocks import MockLLMProvider, json_reply


def _make_vehicle(
    stock,
    *,
    model="Ranger",
    body="truck",
    price="26995",
    trim="XLT SuperCrew 4x4",
    engine="2.3L EcoBoost I-4",
    drivetrain="4x4",
    transmission="10-Speed Automatic",
    fuel_type="Gasoline",
    description="First-gen reborn Ranger with FX4 package — affordable midsize truck.",
    is_available=True,
):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2019,
        make="Ford",
        model=model,
        trim=trim,
        body_style=body,
        condition="used",
        mileage=73500,
        price=Decimal(price),
        engine=engine,
        drivetrain=drivetrain,
        transmission=transmission,
        fuel_type=fuel_type,
        description=description,
        is_available=is_available,
    )


def _attach_prior_turn(session, vehicles):
    """Simulate a prior assistant turn that surfaced ``vehicles``."""
    msg = ChatMessage.objects.create(
        session=session,
        role="assistant",
        content="Here are some options.",
    )
    msg.matched_vehicles.set(vehicles)
    return msg


# ---- Test 1–3: helper-level coverage ---------------------------------------


class ResolveModelFollowupVehicleHelperTests(TestCase):
    def setUp(self):
        self.ranger = _make_vehicle("FF-USED-104", model="Ranger", body="truck")
        self.colorado = _make_vehicle(
            "FF-USED-406", model="Colorado", body="truck"
        )
        self.maverick = _make_vehicle(
            "FF-USED-113", model="Maverick", body="truck"
        )
        self.session = ChatSession.objects.create()
        self.engine = ChatEngine(
            session=self.session, provider=MockLLMProvider()
        )

    def test_anchors_to_prior_matched_model(self):
        # 1. Anchor fires when prior-turn matched a model named in the
        # follow-up.
        _attach_prior_turn(
            self.session, [self.colorado, self.ranger, self.maverick]
        )
        result = self.engine._resolve_model_followup_vehicle(
            "Tell me more about the Ranger",
            {"model": "Ranger"},
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.stock_number, "FF-USED-104")

    def test_returns_none_when_model_not_in_prior_turn(self):
        # 2. Anchor doesn't fire when the model wasn't in the prior turn.
        _attach_prior_turn(self.session, [self.colorado, self.maverick])
        result = self.engine._resolve_model_followup_vehicle(
            "Tell me more about the Ranger",
            {"model": "Ranger"},
        )
        self.assertIsNone(result)

    def test_returns_none_when_no_model_in_regex_hits(self):
        _attach_prior_turn(self.session, [self.ranger])
        result = self.engine._resolve_model_followup_vehicle(
            "What about Saturday?",
            {},
        )
        self.assertIsNone(result)

    def test_returns_none_when_user_reframes_with_monthly_target(self):
        # 3a. Reframe guard — target_monthly_payment in current-turn
        # regex hits means the customer is starting a new search.
        _attach_prior_turn(self.session, [self.ranger])
        result = self.engine._resolve_model_followup_vehicle(
            "Show me Rangers around $400/mo",
            {"model": "Ranger", "target_monthly_payment": 400},
        )
        self.assertIsNone(result)

    def test_returns_none_when_user_reframes_with_max_price(self):
        # 3b. Reframe guard — max_price.
        _attach_prior_turn(self.session, [self.ranger])
        result = self.engine._resolve_model_followup_vehicle(
            "Show me Rangers under $25k",
            {"model": "Ranger", "max_price": 25000},
        )
        self.assertIsNone(result)

    def test_returns_none_when_user_reframes_with_vehicle_type(self):
        # 3c. Reframe guard — vehicle_type.
        _attach_prior_turn(self.session, [self.ranger])
        result = self.engine._resolve_model_followup_vehicle(
            "Show me an SUV like the Ranger",
            {"model": "Ranger", "vehicle_type": "suv"},
        )
        self.assertIsNone(result)

    def test_returns_none_when_anchored_vehicle_no_longer_available(self):
        # Defensive: a stale prior-turn vehicle that's been deactivated
        # since (e.g., demo reset) must not be anchored to.
        gone = _make_vehicle(
            "FF-USED-GONE", model="F-150", is_available=False
        )
        _attach_prior_turn(self.session, [gone])
        result = self.engine._resolve_model_followup_vehicle(
            "Tell me more about the F-150",
            {"model": "F-150"},
        )
        self.assertIsNone(result)


# ---- Test 4–6: end-to-end dispatch ----------------------------------------


class ModelFollowupEndToEndTests(TestCase):
    def setUp(self):
        self.ranger = _make_vehicle("FF-USED-104", model="Ranger", body="truck")
        self.colorado = _make_vehicle(
            "FF-USED-406", model="Colorado", body="truck"
        )
        self.maverick = _make_vehicle(
            "FF-USED-113", model="Maverick", body="truck"
        )

    def test_anchor_wins_over_llm_vehicle_type_flip_and_persists(self):
        # Tests 4 + 5 combined. Mock the intent-extraction LLM call to
        # return the bug-shape: vehicle_type='suv' on a Ranger
        # follow-up. The anchor must:
        #   - Route to FF-USED-104 (1 vehicle in matched_vehicles).
        #   - Persist current_vehicle_id + current_vehicle_stock in
        #     extracted_profile.
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "vehicle_type": "truck",
            },
        )
        _attach_prior_turn(
            session, [self.colorado, self.ranger, self.maverick]
        )
        provider = MockLLMProvider(
            replies=[
                # Intent extraction: LLM flips vehicle_type to suv.
                json_reply(
                    {
                        "model": "Ranger",
                        "make": "Ford",
                        "vehicle_type": "suv",
                    }
                ),
                # Assistant reply (anchor already routed to the Ranger).
                "The 2019 Ford Ranger XLT (Stock #FF-USED-104) has a "
                "2.3L EcoBoost I-4. Want a closer look?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me more about the Ranger")

        # Anchored to the specific Ranger.
        self.assertEqual(len(result.matched_vehicles), 1)
        self.assertEqual(
            result.matched_vehicles[0].stock_number, "FF-USED-104"
        )

        # current_vehicle_id + current_vehicle_stock persisted on the
        # session profile.
        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("current_vehicle_id"),
            self.ranger.id,
        )
        self.assertEqual(
            session.extracted_profile.get("current_vehicle_stock"),
            "FF-USED-104",
        )

    def test_subsequent_pronoun_followup_resolves_to_anchored_vehicle(self):
        # 6. After the model-name anchor fires, "what's the mileage on it?"
        # should still resolve to the anchored Ranger via the existing
        # pronoun-followup path.
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "vehicle_type": "truck",
            },
        )
        _attach_prior_turn(
            session, [self.colorado, self.ranger, self.maverick]
        )
        provider = MockLLMProvider(
            replies=[
                # Turn 1 intent extraction: model=Ranger.
                json_reply({"model": "Ranger", "make": "Ford"}),
                "Here's the Ranger.",
                # Turn 2 intent extraction: empty (pronoun-only).
                json_reply({}),
                "It has 73,500 miles.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)

        # Turn 1 — model anchor fires, persists current_vehicle.
        engine.handle_user_message("Tell me more about the Ranger")

        # Turn 2 — pronoun follow-up resolves to the anchored Ranger.
        result = engine.handle_user_message("What's the mileage on it?")
        self.assertEqual(len(result.matched_vehicles), 1)
        self.assertEqual(
            result.matched_vehicles[0].stock_number, "FF-USED-104"
        )

    def test_anchor_does_not_fire_on_budget_reframe(self):
        # Cross-check the helper-level reframe guard at the dispatch
        # level: when the user introduces a new monthly target, the
        # model-followup fast-path must NOT fire and the normal budget
        # pipeline runs.
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "vehicle_type": "truck",
            },
        )
        _attach_prior_turn(
            session, [self.colorado, self.ranger, self.maverick]
        )
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "model": "Ranger",
                        "make": "Ford",
                        "target_monthly_payment": 400,
                    }
                ),
                "Let me re-run at the new target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Show me Rangers around $400/mo"
        )
        # NOT routed through the followup_mode fast-path — the budget
        # pipeline must run, evidenced by budget_query metadata. Phase
        # 8s/UX: the budget pipeline now also promotes realistic
        # stretches into matched_vehicles, so the Ranger may legitimately
        # surface as a stretch card and trigger the auto-anchor on
        # len(matched)==1. That auto-anchor is a separate, expected
        # path; what this test enforces is that the model-followup
        # short-circuit did NOT bypass classification.
        bq = result.assistant_message.metadata.get("budget_query")
        self.assertIsNotNone(
            bq,
            "budget pipeline should have run (budget_query metadata "
            "missing → followup-mode fast-path was taken instead)",
        )
        self.assertEqual(bq["target_monthly"], 400.0)


# ---- Test 7: enriched single-vehicle inventory block ----------------------


class FormatVehicleBlockSingleVehicleEnrichmentTests(TestCase):
    def test_single_vehicle_block_includes_real_specs(self):
        v = _make_vehicle(
            "FF-USED-104",
            engine="2.3L EcoBoost I-4",
            drivetrain="4x4",
            transmission="10-Speed Automatic",
            fuel_type="Gasoline",
            description=(
                "First-gen reborn Ranger with FX4 package — affordable "
                "midsize truck for hunting and camping."
            ),
        )
        block = _format_vehicle_block([v])
        # The detail header tells the LLM these are real fields.
        self.assertIn("Detailed specs", block)
        # Each populated field appears.
        self.assertIn("2.3L EcoBoost I-4", block)
        self.assertIn("4x4", block)
        self.assertIn("10-Speed Automatic", block)
        self.assertIn("Gasoline", block)
        self.assertIn("First-gen reborn Ranger", block)

    def test_single_vehicle_block_omits_blank_spec_fields(self):
        # When a Vehicle has missing fields, the block must skip those
        # lines rather than write empty "Engine: " / "Fuel type: " rows.
        v = _make_vehicle(
            "SPARSE",
            engine="",
            drivetrain="",
            transmission="",
            fuel_type="",
            description="",
        )
        block = _format_vehicle_block([v])
        self.assertNotIn("Detailed specs", block)
        self.assertNotIn("Engine: ", block)
        self.assertNotIn("Drivetrain: ", block)

    def test_multi_vehicle_block_omits_detail_specs(self):
        # The detail block is single-vehicle only; multi-vehicle queries
        # keep the concise per-line format unchanged.
        v1 = _make_vehicle("V1", model="Ranger", engine="2.3L EcoBoost I-4")
        v2 = _make_vehicle("V2", model="Maverick", engine="2.5L Hybrid")
        block = _format_vehicle_block([v1, v2])
        self.assertNotIn("Detailed specs", block)
        # Both vehicles' summary lines should still appear.
        self.assertIn("V1", block)
        self.assertIn("V2", block)
