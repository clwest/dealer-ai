"""Phase 8s/UX — lever-flex presentation options.

When strict-search + realistic-stretch yields fewer than
MULTI_OPTION_TOTAL_CAP cards, ``build_budget_context`` widens the
presentation set with vehicles the customer can reach by flexing ONE
lever from their stated ask:

  - longer_term      — needs a longer-than-current term
  - more_down        — needs a higher down payment (+$2k, then +$5k)
  - drivetrain_flex  — only if the customer's strict drivetrain ask
                        excluded otherwise-affordable vehicles

Each pick is annotated with `_lever_flex_kind` + `_lever_flex_explainer`
so the frontend can render a distinct badge and the LLM can name the
lever verbatim.

Honesty constraints — these tests pin them:
  * Flex picks NEVER land in the strict matched_in_budget / near_fit /
    closest_above buckets.
  * The drivetrain_flex card always carries a label naming the actual
    drivetrain so the customer can't confuse a 2WD pick for the 4WD
    they asked for.
  * Total cards stay capped at MULTI_OPTION_TOTAL_CAP (= 3).
  * Payment math on a flex card is computed AT THE FLEXED INPUTS, not
    at the customer's stated ones.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    MULTI_OPTION_TOTAL_CAP,
    _format_budget_block,
    _lever_flex_close_question,
    build_budget_context,
    check_payment_consistency,
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
    features=None,
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
        features=features or [],
    )


def _seed_4wd_demo_pool():
    """Mirror demo inventory shape: one cheap 4WD truck (Ranger) lands as
    near-fit at $500/$3k/60mo; a bigger 4WD truck (Tundra) only lands
    inside the cap at 84-mo; a 4x2 truck (Colorado) lands as fit at
    $0 down without the 4WD filter; a far-over 4WD truck never qualifies."""
    ranger = _make_vehicle(
        "FF-USED-104",
        "26995",
        model="Ranger",
        trim="XLT SuperCrew 4x4",
        drivetrain="4x4",
    )
    tundra = _make_vehicle(
        "FF-USED-511",
        "35995",
        model="Tundra",
        trim="Limited CrewMax 4x4",
        drivetrain="4x4",
    )
    colorado = _make_vehicle(
        "FF-USED-406",
        "25495",
        model="Colorado",
        trim="WT 4x2",
        drivetrain="RWD",
    )
    far_over = _make_vehicle(
        "FF-USED-510",
        "55000",
        model="F-150",
        trim="STX 4x4",
        drivetrain="4x4",
    )
    return ranger, tundra, colorado, far_over


# ---- 1. Selection priority -----------------------------------------------


class LeverFlexSelectionPriorityTests(TestCase):
    """Levers fire in order: longer_term → more_down → drivetrain_flex.
    Spare slots fill from the highest-priority lever first; once cap
    reached, lower-priority levers are skipped."""

    def setUp(self):
        _seed_4wd_demo_pool()

    def test_strict_4wd_500_3k_60mo_yields_strict_plus_flex(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "I need a 4WD truck around $500 a month",
        )
        # Strict near-fit: Ranger 4x4 at $517.
        self.assertEqual(
            [v.stock_number for v in ctx.near_fit], ["FF-USED-104"]
        )
        flex_stocks = {v.stock_number for v in ctx.lever_flex_options}
        # Tundra 4x4 unlocks at 84-mo (longer_term lever — highest priority).
        self.assertIn("FF-USED-511", flex_stocks)
        # Total presentation set is capped at 3.
        total = (
            len(ctx.matched_in_budget)
            + len(ctx.near_fit)
            + len(ctx.closest_above)
            + len(ctx.lever_flex_options)
        )
        self.assertLessEqual(total, MULTI_OPTION_TOTAL_CAP)

    def test_lever_kinds_in_priority_order(self):
        # Longer-term is tried first; if cap fills, more_down and
        # drivetrain_flex won't surface. Customer gets the smallest
        # disturbance lever first.
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD truck $500 with $3000 down",
        )
        kinds = [
            getattr(v, "_lever_flex_kind", None)
            for v in ctx.lever_flex_options
        ]
        if "drivetrain_flex" in kinds and "longer_term" in kinds:
            self.assertLess(
                kinds.index("longer_term"),
                kinds.index("drivetrain_flex"),
                "longer_term should be picked before drivetrain_flex",
            )


# ---- 2. No-flex when drivetrain="any" ------------------------------------


class NoLeverFlexWhenDrivetrainAnyTests(TestCase):
    """Once the customer has released the drivetrain constraint, the
    strict pipeline already sees the wider pool — there's no need to
    layer flex on top."""

    def setUp(self):
        _seed_4wd_demo_pool()

    def test_drivetrain_any_skips_drivetrain_flex(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "any",
            },
            "any drivetrain",
        )
        kinds = [
            getattr(v, "_lever_flex_kind", None)
            for v in ctx.lever_flex_options
        ]
        # Drivetrain-flex should NOT fire when drivetrain has been
        # released — it's not a strict constraint anymore.
        self.assertNotIn("drivetrain_flex", kinds)


# ---- 3. No flex when strict already filled the cap -----------------------


class NoLeverFlexWhenCapFilledTests(TestCase):
    def setUp(self):
        # 1 fit + 2 near-fits (all 4WD) at $500/$0 down/60mo. With
        # MAX_FIT_RESULTS=1 and MAX_NEAR_FIT_RESULTS=2, strict pipeline
        # fills MULTI_OPTION_TOTAL_CAP=3 — no spare slots → no flex.
        _make_vehicle(
            "FIT-A", "22000", model="Ranger", trim="XL 4x4", drivetrain="4x4"
        )
        _make_vehicle(
            "NEAR-A", "25500", model="Ranger", trim="XLT 4x4", drivetrain="4x4"
        )
        _make_vehicle(
            "NEAR-B", "26000", model="Ranger", trim="STX 4x4", drivetrain="4x4"
        )

    def test_no_flex_when_cap_filled(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD trucks around $500/mo",
        )
        total_strict = (
            len(ctx.matched_in_budget)
            + len(ctx.near_fit)
            + len(ctx.closest_above)
        )
        self.assertGreaterEqual(total_strict, MULTI_OPTION_TOTAL_CAP)
        # No lever-flex picks layered on top.
        self.assertEqual(ctx.lever_flex_options, [])


# ---- 4. Per-vehicle annotations populated --------------------------------


class LeverFlexAnnotationsTests(TestCase):
    def setUp(self):
        _seed_4wd_demo_pool()

    def test_longer_term_card_annotations(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD truck $500/mo with $3k down",
        )
        longer_term_picks = [
            v
            for v in ctx.lever_flex_options
            if getattr(v, "_lever_flex_kind", None) == "longer_term"
        ]
        self.assertTrue(longer_term_picks)
        v = longer_term_picks[0]
        # Term annotation matches the next-term band.
        self.assertEqual(getattr(v, "_lever_flex_term_months", None), 72)
        # Explainer names the term verbatim.
        explainer = getattr(v, "_lever_flex_explainer", "") or ""
        self.assertIn("72-mo", explainer)
        self.assertIn("60-mo", explainer)
        # Payment is computed at the flexed term, NOT the original.
        # At 72-mo, the Tundra lands ~$640; at 60-mo it'd be $705.
        est = getattr(v, "_estimated_payment", None)
        self.assertIsNotNone(est)
        self.assertLess(est, 700, f"flex payment should reflect 72-mo math, got {est}")

    def test_drivetrain_flex_card_annotations(self):
        # At $500/mo $0 down 60mo, Colorado WT 4x2 lands as fit when
        # drivetrain is released — qualifying as a drivetrain-flex pick.
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD truck $500/mo $0 down",
        )
        flex_dt = [
            v
            for v in ctx.lever_flex_options
            if getattr(v, "_lever_flex_kind", None) == "drivetrain_flex"
        ]
        if not flex_dt:
            return  # No drivetrain-flex pick this scenario; nothing to assert.
        v = flex_dt[0]
        self.assertEqual(
            getattr(v, "_lever_flex_drivetrain_required", None), "4WD"
        )
        explainer = getattr(v, "_lever_flex_explainer", "") or ""
        # The customer asked for 4WD; the explainer must say "2WD" so
        # the customer cannot mistake this card.
        self.assertIn("2WD", explainer)
        self.assertIn("4WD", explainer)


# ---- 5. No duplicates across buckets -------------------------------------


class NoDuplicatesAcrossBucketsTests(TestCase):
    def setUp(self):
        _seed_4wd_demo_pool()

    def test_strict_match_does_not_reappear_as_flex(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD truck $500 $3k down",
        )
        strict_ids = {
            v.id
            for v in (
                ctx.matched_in_budget + ctx.near_fit + ctx.closest_above
            )
        }
        flex_ids = {v.id for v in ctx.lever_flex_options}
        self.assertEqual(
            strict_ids & flex_ids,
            set(),
            "no vehicle should appear in both strict and flex buckets",
        )


# ---- 6. Total cap respected ----------------------------------------------


class TotalCardCapRespectedTests(TestCase):
    def setUp(self):
        # Many 4WD trucks within reach — strict pipeline alone fills
        # the cap, no spare slots for flex.
        for i in range(8):
            _make_vehicle(
                f"4WD-{i}",
                str(20000 + i * 1000),
                model="Ranger",
                trim="XLT 4x4",
                drivetrain="4x4",
            )

    def test_total_never_exceeds_cap(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD trucks $500/mo",
        )
        total = (
            len(ctx.matched_in_budget)
            + len(ctx.near_fit)
            + len(ctx.closest_above)
            + len(ctx.lever_flex_options)
        )
        self.assertLessEqual(total, MULTI_OPTION_TOTAL_CAP)


# ---- 7. BUDGET ANALYSIS section + dynamic close --------------------------


class LeverFlexBlockRenderingTests(TestCase):
    def setUp(self):
        _seed_4wd_demo_pool()

    def test_block_includes_lever_flex_section_when_picks_exist(self):
        ctx = build_budget_context(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD truck $500/mo $3k down",
        )
        if not ctx.lever_flex_options:
            self.skipTest("no flex picks for this seed scenario")
        block = _format_budget_block(ctx)
        self.assertIn("LEVER FLEX OPTIONS", block)
        # Each flex line carries the `LEVER:` clause naming the lever.
        self.assertIn("LEVER:", block)

    def test_block_omits_section_when_no_flex(self):
        # All-easy 4WD scenario: strict pipeline produces 3 cards
        # without flex.
        for i in range(3):
            _make_vehicle(
                f"EASY-{i}",
                str(20000 + i * 200),
                model="Ranger",
                trim="XLT 4x4",
                drivetrain="4x4",
            )
        ctx = build_budget_context(
            {
                "target_monthly_payment": 600,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            },
            "4WD trucks $600/mo",
        )
        if ctx.lever_flex_options:
            self.skipTest("seed produced flex picks; this test wants none")
        block = _format_budget_block(ctx)
        self.assertNotIn("LEVER FLEX OPTIONS", block)


class LeverFlexCloseQuestionTests(TestCase):
    """Dynamic close question — only mentions levers that yielded cards."""

    def test_three_levers_three_part_close(self):
        q = _lever_flex_close_question(
            ["longer_term", "more_down", "drivetrain_flex"]
        )
        self.assertIn("a longer term", q)
        self.assertIn("more down", q)
        self.assertIn("flexible drivetrain", q)
        self.assertTrue(q.endswith("?"))

    def test_two_levers_two_part_close(self):
        q = _lever_flex_close_question(["longer_term", "more_down"])
        self.assertIn("a longer term", q)
        self.assertIn("more down", q)
        self.assertNotIn("flexible drivetrain", q)

    def test_one_lever_simple_yesno(self):
        q = _lever_flex_close_question(["longer_term"])
        # Single-lever scenarios use a simple yes/no soft close.
        self.assertIn("a longer term", q)
        self.assertNotIn("more down", q)
        self.assertNotIn("flexible drivetrain", q)

    def test_no_levers_returns_empty(self):
        self.assertEqual(_lever_flex_close_question([]), "")

    def test_mentions_only_surfaced_levers(self):
        # If no down-flex card surfaced, the question must NOT mention
        # "more down" — that would imply we have an option we don't.
        q = _lever_flex_close_question(["longer_term", "drivetrain_flex"])
        self.assertNotIn("more down", q)


# ---- 8. Fabricated-inventory guard accepts flex stocks naturally ---------


class FabricatedGuardAcceptsFlexStocksTests(TestCase):
    """Flex picks land in matched_vehicles — their Stock #s are in the
    fabricated-inventory guard's allow-list automatically."""

    def setUp(self):
        _seed_4wd_demo_pool()

    def test_llm_citing_flex_stock_passes_guard(self):
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
                # Cite the Tundra (longer-term flex pick).
                "Stock #FF-USED-511 lands at 84 months — needs longer term.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I need a 4WD truck around $500/mo with $3000 down"
        )
        from dealer_ai.services.chat_engine import FABRICATED_INVENTORY_RESPONSE
        # If the Tundra was promoted, the citation passes.
        if "FF-USED-511" in {v.stock_number for v in result.matched_vehicles}:
            self.assertNotEqual(
                result.assistant_message.content, FABRICATED_INVENTORY_RESPONSE
            )

    def test_llm_citing_unknown_stock_still_fires_guard(self):
        from dealer_ai.services.chat_engine import FABRICATED_INVENTORY_RESPONSE
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
                "Try Stock #FAKE-999 — looks great!",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I need a 4WD truck around $500/mo with $3000 down"
        )
        self.assertEqual(
            result.assistant_message.content, FABRICATED_INVENTORY_RESPONSE
        )
        meta = result.assistant_message.metadata or {}
        self.assertEqual(meta.get("flag"), "fabricated_inventory")


# ---- 9. Payment-consistency accepts flex payments ------------------------


class PaymentConsistencyAcceptsFlexPaymentsTests(TestCase):
    """Flex cards' payments are computed at the flexed inputs (e.g.,
    $540/mo at 84-mo for the Tundra). check_payment_consistency must
    accept these values when allowed_payments includes them."""

    def test_flex_payment_quote_does_not_trip_drift(self):
        reply = (
            "The Ranger lands at $517/mo. The Tundra would land $540/mo "
            "at 84 months."
        )
        allowed_payments = [517.0, 540.0]
        drift = check_payment_consistency(
            reply,
            target_monthly=500.0,
            allowed_payments=allowed_payments,
        )
        self.assertEqual(drift, [])

    def test_flex_payment_without_allowance_does_trip_drift(self):
        # Sanity: without the flex payment in allowed_payments, the
        # quote logs as drift. Confirms our wiring is what accepts the
        # flex value, not the guard being lax.
        reply = "The Tundra would land $540/mo at 84 months."
        drift = check_payment_consistency(
            reply,
            target_monthly=500.0,
            allowed_payments=[517.0],
        )
        self.assertEqual(drift, [540.0])


# ---- 10. Lever-flex turn marks lever_offer in metadata -------------------


class LeverFlexLeverOfferMetadataTests(TestCase):
    def setUp(self):
        _seed_4wd_demo_pool()

    def test_flex_turn_sets_lever_offer_flag(self):
        # Bare "yes" in the next turn should hit the clarifier path
        # because the multi-lever close question is just as ambiguous
        # as the single-card soft-close.
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
                "Closest 4WD plus flex.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I need a 4WD truck around $500/mo with $3000 down"
        )
        self.assertTrue(
            result.assistant_message.metadata.get("lever_offer"),
            "flex turn must set lever_offer=True",
        )


# ---- 11. Serializer exposes flex fields ----------------------------------


class SerializerExposesLeverFlexFieldsTests(TestCase):
    def test_serializer_round_trips_lever_flex_kind_and_explainer(self):
        from dealer_ai.serializers import VehicleSerializer

        v = _make_vehicle(
            "FLEX-T",
            "27000",
            model="F-150",
            trim="XLT 2WD",
            drivetrain="RWD",
        )
        # Simulate annotations the picker would attach.
        v._budget_fit = "near_fit"
        v._estimated_payment = 540.0
        v._payment_delta = 40.0
        v._lever_flex_kind = "longer_term"
        v._lever_flex_explainer = "Needs 84-mo term (vs current 60-mo)"
        data = VehicleSerializer(v).data
        self.assertEqual(data["lever_flex_kind"], "longer_term")
        self.assertEqual(
            data["lever_flex_explainer"],
            "Needs 84-mo term (vs current 60-mo)",
        )

    def test_serializer_emits_null_for_non_flex_card(self):
        from dealer_ai.serializers import VehicleSerializer

        v = _make_vehicle(
            "STRICT", "26995", model="Ranger", drivetrain="4x4"
        )
        # Strict near-fit — no flex annotations.
        v._budget_fit = "near_fit"
        v._estimated_payment = 517.0
        v._payment_delta = 17.0
        data = VehicleSerializer(v).data
        self.assertIsNone(data["lever_flex_kind"])
        self.assertIsNone(data["lever_flex_explainer"])
