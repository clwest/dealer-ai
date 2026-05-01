"""Phase 8s/UX — STRETCH OPTIONS in BUDGET ANALYSIS.

When the strict classification yields fewer than ``MULTI_OPTION_TOTAL_CAP``
matched vehicles (= 3), populate ``BudgetContext.closest_above`` with the
spare slots so the LLM has real anchor points for "options just above
your target" framing. Stretches are TEXT-ONLY:

- They never enter ``matched_vehicles`` (the API and the frontend cap of
  3 cards stay intact).
- They render in the BUDGET ANALYSIS block under a "STRETCH OPTIONS"
  header WITHOUT Stock #s — so the existing fabricated-inventory guard
  (Phase 8s, A3) stays strict: any Stock # the LLM cites must still be
  in ``matched_vehicles``, and stretches don't undermine that guarantee.
- Their ``_estimated_payment`` values are added to the
  ``allowed_payments`` set the post-LLM ``check_payment_consistency``
  uses, so the LLM quoting "$705/mo on the Tundra" doesn't trip drift
  detection.

Tests:
1. 0 fits + 1 near_fit + many overs → closest_above gets 2 (spare slots).
2. 1 fit + 1 near_fit + many overs → closest_above gets 1.
3. 2 fits + 0 near_fit + many overs → closest_above gets 1.
4. 1 fit + 2 near_fits + many overs → closest_above stays empty (cap reached).
5. 0 fits + 0 near_fit + many overs → closest_above stays at 3 (existing
   "no useful options" path preserved).
6. ``_format_budget_block`` includes a "STRETCH OPTIONS" header when
   ``closest_above`` is non-empty AND a near_fit exists.
7. Stretch lines do NOT contain ``Stock #`` tokens.
8. ``matched_vehicles`` returned to the API still excludes closest_above.
9. ``check_payment_consistency`` accepts a stretch payment quote without
   flagging drift (allowed_payments includes closest_above).
10. Fabricated-inventory guard still rejects any Stock # not in
    ``matched``: a model-followup style cite of a closest_above Stock #
    must fire the guard (defense in depth — the prompt tells the LLM
    not to cite stretch Stock #s, but if it disobeys, the guard catches).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    FABRICATED_INVENTORY_RESPONSE,
    MULTI_OPTION_TOTAL_CAP,
    _format_budget_block,
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
    body="truck",
    features=None,
    mileage=0,
    trim="",
    year=2025,
    drivetrain="",
):
    return Vehicle.objects.create(
        stock_number=stock,
        year=year,
        make="Ford",
        model=model,
        trim=trim,
        body_style=body,
        condition="new",
        mileage=mileage,
        price=Decimal(price),
        features=features or [],
        drivetrain=drivetrain,
    )


def _seed_truck_inventory(*, fits, near_fits, overs):
    """Seed ``fits`` / ``near_fits`` / ``overs`` truck rows at price
    points that produce the matching classification at $500/mo, $0
    down, 60-mo term, $75 tolerance.

    At those engine defaults the ceilings are roughly:
      fit       (≤ $500/mo) → price ≤ ~$23k
      near_fit  (≤ $575/mo) → price ≤ ~$26.9k
      over                  → price >  ~$26.9k

    OVER seeds intentionally sit just above the near-fit ceiling so
    they pass the realistic-stretch filter (max($150 floor, 30% of
    target) above target = $650/mo at $500 target ≈ price ≤ ~$30k).
    Tests that need *very* over-budget vehicles seed them inline.
    """
    seeds = []
    for i in range(fits):
        seeds.append(_make_vehicle(f"FIT-{i}", str(20000 + i * 200)))
    for i in range(near_fits):
        seeds.append(_make_vehicle(f"NEAR-{i}", str(25500 + i * 200)))
    for i in range(overs):
        # Sorted ascending overs so the closest-delta ones come first
        # in the over[] list (build_budget_context sorts by ascending
        # _payment_delta). Each seed lands a few dollars/month over
        # target and stays inside the $150 stretch cap.
        seeds.append(_make_vehicle(f"OVER-{i}", str(27500 + i * 300)))
    return seeds


# ---- Tests 1–5: closest_above population behaviour ------------------------


class ClosestAbovePopulationTests(TestCase):
    def setUp(self):
        self.profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
        }

    def test_one_near_fit_fills_two_spare_slots(self):
        # 0 fits + 1 near_fit + 5 overs → spare = 3 - 0 - 1 = 2.
        _seed_truck_inventory(fits=0, near_fits=1, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.matched_in_budget), 0)
        self.assertEqual(len(ctx.near_fit), 1)
        self.assertEqual(len(ctx.closest_above), 2)

    def test_one_fit_one_near_leaves_one_spare_slot(self):
        # 1 fit + 1 near + 5 overs → spare = 1.
        _seed_truck_inventory(fits=1, near_fits=1, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.matched_in_budget), 1)
        self.assertEqual(len(ctx.near_fit), 1)
        self.assertEqual(len(ctx.closest_above), 1)

    def test_two_fits_zero_near_leaves_one_spare_slot(self):
        # 2 fits + 0 near + 5 overs → fit cap is 1, so served_fits=1;
        # spare = 3 - 1 - 0 = 2.
        _seed_truck_inventory(fits=2, near_fits=0, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.matched_in_budget), 1)  # capped at 1
        self.assertEqual(len(ctx.near_fit), 0)
        self.assertEqual(len(ctx.closest_above), 2)

    def test_one_fit_two_near_fills_cap_no_stretches(self):
        # 1 fit + 2 near + 5 overs → cap reached, spare = 0.
        _seed_truck_inventory(fits=1, near_fits=2, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.matched_in_budget), 1)
        self.assertEqual(len(ctx.near_fit), 2)
        self.assertEqual(len(ctx.closest_above), 0)

    def test_no_useful_matches_still_surfaces_three_overs(self):
        # 0 fits + 0 near + 5 overs → spare = 3 (existing behaviour
        # before this patch shipped). Closest_above gets the top 3
        # closest-delta overs.
        _seed_truck_inventory(fits=0, near_fits=0, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.matched_in_budget), 0)
        self.assertEqual(len(ctx.near_fit), 0)
        self.assertEqual(len(ctx.closest_above), MULTI_OPTION_TOTAL_CAP)

    def test_closest_above_capped_when_fewer_overs_than_spare(self):
        # 0 fits + 1 near + 1 over → spare = 2 but only 1 over exists.
        _seed_truck_inventory(fits=0, near_fits=1, overs=1)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.closest_above), 1)


# ---- Tests 6–7: BUDGET ANALYSIS block rendering ---------------------------


class FormatBudgetBlockStretchSectionTests(TestCase):
    def setUp(self):
        self.profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
        }

    def test_stretch_options_header_appears_when_near_fit_and_stretches(self):
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # The new stretch header must be present when stretches are
        # surfaced alongside near-fits.
        self.assertIn("STRETCH OPTIONS", block)
        # The reply rules must mention stretches when present.
        self.assertIn("STRETCH OPTIONS", block)

    def test_stretch_lines_carry_stock_numbers(self):
        # Phase 8s/UX promotion — stretches are now matched_vehicles
        # cards (with budget_fit="over_budget" / "above target" badge),
        # so each STRETCH OPTIONS line carries the same Stock # the
        # frontend renders. The LLM may cite it; the fabricated-
        # inventory guard's allow-list now includes it naturally.
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        stretch_idx = block.find("STRETCH OPTIONS")
        self.assertGreater(stretch_idx, -1)
        rest = block[stretch_idx:]
        stretch_stock_lines = []
        for raw_line in rest.split("\n"):
            if raw_line.startswith("  · "):
                stretch_stock_lines.append(raw_line)
            elif raw_line.startswith("Reply rules"):
                break
        self.assertTrue(stretch_stock_lines, "no stretch lines rendered")
        for line in stretch_stock_lines:
            self.assertIn(
                "Stock #",
                line,
                f"stretch line is missing its Stock #: {line!r}",
            )

    def test_no_stretch_section_when_cap_reached(self):
        _seed_truck_inventory(fits=1, near_fits=2, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # STRETCH OPTIONS section is omitted when fit + near already
        # fills the cap.
        self.assertNotIn("STRETCH OPTIONS", block)


class StretchLineEnrichmentTests(TestCase):
    """The stretch-line formatter must surface concrete capability data
    (features, mileage, Stock #) so the LLM can connect a stretch to a
    real benefit instead of inventing one."""

    def test_stretch_line_includes_features_when_present(self):
        from dealer_ai.services.chat_engine import _format_stretch_line

        v = _make_vehicle(
            "STRETCH-A",
            "39995",
            model="Ranger",
            trim="Lariat 4x4",
            features=["Tow Package", "FX4 Off-Road", "Sync 4", "B&O Audio"],
            mileage=22000,
        )
        # Annotate manually as _classify_candidates would.
        v._estimated_payment = 789.0
        v._payment_delta = 289.0
        v._budget_fit = "over_budget"
        line = _format_stretch_line(v, target=500.0)
        self.assertIn("features:", line)
        self.assertIn("Tow Package", line)
        self.assertIn("FX4 Off-Road", line)
        self.assertIn("22,000 mi", line)
        # Phase 8s/UX promotion — stretches now ARE matched_vehicles
        # cards, so the Stock # is included on the line so the LLM has
        # the same shape it sees for fits / near-fits.
        self.assertIn("Stock #STRETCH-A", line)

    def test_stretch_line_omits_features_segment_when_empty(self):
        from dealer_ai.services.chat_engine import _format_stretch_line

        v = _make_vehicle("STRETCH-B", "39995", features=[], mileage=0)
        v._estimated_payment = 789.0
        v._payment_delta = 289.0
        line = _format_stretch_line(v, target=500.0)
        self.assertNotIn("features:", line)
        # Mileage of 0 should also be skipped (stock new vehicles).
        self.assertNotIn("0 mi", line)


class StretchReplyRulesUpsellTests(TestCase):
    """When near_fit + stretches coexist, the BUDGET ANALYSIS reply
    rules must instruct the LLM to frame stretches as opportunity using
    one of three upsell phrases, connect to a concrete benefit, present
    conversationally, and keep the reply short."""

    def setUp(self):
        self.profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
        }

    def test_reply_rules_include_three_upsell_phrases(self):
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # Each phrase appears so the LLM can pick one — the rule
        # explicitly tells it to choose ONE, not all three.
        self.assertIn("if you're open to stretching", block.lower())
        self.assertIn("opens up options like", block.lower())
        self.assertIn("with a little flexibility", block.lower())
        # Anti-list directive present.
        self.assertIn("conversationally", block.lower())
        # Short-reply directive present.
        self.assertIn("3–5 sentences", block)
        # Must explicitly forbid feature fabrication.
        self.assertIn("DO NOT invent features", block)

    def test_reply_rules_keep_concrete_benefit_examples(self):
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # The rule explicitly names the three benefit categories so
        # the LLM doesn't reach for vague upsell adjectives.
        self.assertIn("newer year", block.lower())
        self.assertIn("higher trim", block.lower())
        # And anchors examples to year/trim differences (not invented stats).
        self.assertIn("Lariat vs XLT", block)

    def test_old_reply_rule_unchanged_when_no_stretches(self):
        # Cap reached → STRETCH OPTIONS is absent → the older "near-fit
        # only" reply rule is rendered, NOT the new opportunity-framing
        # rule. This ensures we didn't accidentally apply opportunity
        # phrasing to flows where it'd be inappropriate.
        _seed_truck_inventory(fits=1, near_fits=2, overs=5)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        self.assertNotIn("STRETCH OPTIONS", block)
        self.assertNotIn("with a little flexibility", block.lower())


# ---- Phase 8s/UX: single near-fit, no realistic stretches ----------------


class SingleNearFitNoStretchSoftCloseTests(TestCase):
    """When the strict 4WD-truck (or any tight) search yields exactly
    one near-fit and zero realistic stretches, the LLM was closing with
    weak / misleading prompts like "want me to explore options under
    your target?" — but no under-target inventory exists. The new rule
    leads with the near-fit, names the levers (term / down / trade-in /
    higher monthly / drivetrain flexibility), and ends with a soft
    "Would you be open to adjusting one of those" close. It must NOT
    suggest under-target options."""

    def setUp(self):
        self.profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
        }

    def _seed_one_near_no_stretch(self):
        # 1 near-fit, 1 way-over (excluded by the realistic-stretch
        # cap), 0 fits → near_count == 1 and has_stretches is False.
        _make_vehicle("ONLY-NEAR", "26000", model="Ranger")  # ≈ $560/mo
        _make_vehicle("WAY-OVER", "55000", model="F-150")  # ≈ $1180/mo

    def test_rule_leads_with_closest_match_phrasing(self):
        self._seed_one_near_no_stretch()
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        # Sanity: this is the no-stretch / single-near branch.
        self.assertEqual(len(ctx.near_fit), 1)
        self.assertEqual(len(ctx.closest_above), 0)
        block = _format_budget_block(ctx)
        # Lead-in language calls the near-fit the closest real match.
        self.assertIn("closest match", block)
        # Frames as "close to your target", never as exact / in-budget.
        self.assertIn("close to your target", block)
        self.assertIn("never \"in your budget\"", block)
        self.assertIn("never \"exact fit\"", block)

    def test_rule_names_the_five_levers(self):
        self._seed_one_near_no_stretch()
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx).lower()
        # All five levers from the user spec must appear so the LLM has
        # concrete options to suggest naturally.
        self.assertIn("longer term", block)
        self.assertIn("more down", block)
        self.assertIn("trade-in", block)
        self.assertIn("slightly higher monthly", block)
        self.assertIn("flexibility on drivetrain", block)

    def test_rule_ends_with_soft_lever_close(self):
        self._seed_one_near_no_stretch()
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # Verbatim soft close.
        self.assertIn(
            "Would you be open to adjusting one of those so I can show "
            "you more options?",
            block,
        )

    def test_rule_forbids_under_target_phrasing(self):
        self._seed_one_near_no_stretch()
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # The new rule must explicitly tell the LLM not to invite the
        # customer to look "under target" when no under-target matches
        # exist. (The literal phrases \"options under your target\" and
        # \"explore options under your target\" appear inside the rule
        # itself as the things being banned — that's intentional, so
        # the LLM sees the exact phrasing it must avoid.)
        self.assertIn("DO NOT suggest \"options under your target\"", block)
        self.assertIn("under-target matches don't exist", block)
        self.assertIn("Don't promise more vehicles you can't show", block)

    def test_rule_does_not_use_old_narrowing_phrasing(self):
        # The single-near, no-stretch branch replaces the older
        # "EXACTLY ONE focused narrowing question" wording with a
        # natural soft close.
        self._seed_one_near_no_stretch()
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        self.assertNotIn("EXACTLY ONE focused narrowing question", block)

    def test_two_near_fits_keeps_legacy_rule(self):
        # Two near-fits + no stretches → legacy "near-fit only" rule.
        # The new soft-close lever language is reserved for the
        # near_count == 1 branch only.
        _make_vehicle("NEAR-A", "26000", model="Ranger")  # ≈ $560/mo
        _make_vehicle("NEAR-B", "26500", model="Ranger")  # ≈ $570/mo
        _make_vehicle("WAY-OVER", "55000", model="F-150")  # excluded
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        self.assertEqual(len(ctx.near_fit), 2)
        self.assertEqual(len(ctx.closest_above), 0)
        block = _format_budget_block(ctx)
        # Legacy rule fires — narrowing-question wording present, soft
        # close absent.
        self.assertIn("EXACTLY ONE focused narrowing question", block)
        self.assertNotIn("Would you be open to adjusting one of those", block)


class SingleStretchOnlySoftCloseTests(TestCase):
    """Phase 8s/UX promotion — strict-search single-stretch case.
    Mirrors the strict 4WD-truck reality where the only vehicle within
    the realistic-stretch cap is one over-budget truck. Lead with that
    stretch as "the closest real match" (acknowledging it's above
    target), then use the soft-close lever rule."""

    def setUp(self):
        self.profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
        }

    def _seed_one_stretch_only(self):
        # No fits, no near-fits, exactly one realistic stretch (≈$577/mo
        # → +$77 delta, inside the $150 cap). All other inventory is
        # excluded by the cap. drivetrain="4x4" so the 4WD filter the
        # intent parser extracts from "4WD trucks" doesn't strip the
        # only candidate before classification.
        _make_vehicle(
            "ONLY-STRETCH", "26995", model="Ranger", drivetrain="4x4"
        )
        _make_vehicle("WAY-OVER", "55000", model="F-150", drivetrain="4x4")

    def test_single_stretch_uses_lever_softclose_rule(self):
        self._seed_one_stretch_only()
        ctx = build_budget_context(self.profile, "$500/mo 4WD trucks")
        # Sanity: this is the no-fit / no-near / 1-stretch branch.
        self.assertEqual(len(ctx.matched_in_budget), 0)
        self.assertEqual(len(ctx.near_fit), 0)
        self.assertEqual(len(ctx.closest_above), 1)
        block = _format_budget_block(ctx)
        # Lead-in language calls the stretch the closest real match
        # while still labeling it above target.
        self.assertIn("closest match", block)
        self.assertIn("a bit above", block)
        # Lever language present.
        self.assertIn("longer term", block.lower())
        self.assertIn("flexibility on drivetrain", block.lower())
        # Soft close present.
        self.assertIn(
            "Would you be open to adjusting one of those so I can show "
            "you more options?",
            block,
        )
        # Generic explain-gap fallback NOT used.
        self.assertNotIn(
            "Reply rules: explain the gap honestly using the numbers above",
            block,
        )

    def test_single_stretch_appears_as_card(self):
        # End-to-end: matched_vehicles carries the stretch with
        # budget_fit="over_budget" so the frontend renders an "above
        # target" badge.
        self._seed_one_stretch_only()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "truck",
                    }
                ),
                "Closest 4WD truck I have.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Show me 4WD trucks for $500/mo over 60 months"
        )
        self.assertEqual(len(result.matched_vehicles), 1)
        v = result.matched_vehicles[0]
        self.assertEqual(v.stock_number, "ONLY-STRETCH")
        self.assertEqual(getattr(v, "_budget_fit", None), "over_budget")


# ---- Tests 8: matched_vehicles INCLUDES realistic stretches ---------------


class MatchedVehiclesIncludesRealisticStretchesTests(TestCase):
    """Phase 8s/UX promotion — stretches inside the realistic-stretch
    cap (max($150 floor, 30% × target)) flow into matched_vehicles[]
    so the customer sees cards for them. The total is still bounded by
    MULTI_OPTION_TOTAL_CAP=3, with stretches filling the spare slots
    after fits + near-fits."""

    def test_handle_user_message_matched_includes_closest_above(self):
        # 0 fits + 1 near_fit + 3 overs (all within the $150 cap given
        # the seeder's $27,500-base over prices) → 1 near + 2 stretches
        # = 3 cards total. NEAR-0 plus the two closest-delta overs.
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "truck",
                    }
                ),
                "Here's the closest match plus a couple of stretches.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Show me trucks for $500/mo over 60 months"
        )
        matched_stocks = {v.stock_number for v in result.matched_vehicles}
        # Total stays at the cap of 3.
        self.assertEqual(len(result.matched_vehicles), MULTI_OPTION_TOTAL_CAP)
        # Near-fit is in there.
        self.assertIn("NEAR-0", matched_stocks)
        # The two closest-delta overs (OVER-0, OVER-1) ride into matched
        # with budget_fit="over_budget".
        self.assertIn("OVER-0", matched_stocks)
        self.assertIn("OVER-1", matched_stocks)
        over_cards = [
            v for v in result.matched_vehicles if v.stock_number.startswith("OVER-")
        ]
        for v in over_cards:
            self.assertEqual(getattr(v, "_budget_fit", None), "over_budget")
            self.assertGreater(getattr(v, "_payment_delta", 0) or 0, 0)

    def test_total_cards_capped_at_three(self):
        # 0 fits + 0 near + many overs (all within cap) → 3 total cards
        # (no over-stuffing past MULTI_OPTION_TOTAL_CAP).
        _seed_truck_inventory(fits=0, near_fits=0, overs=5)
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "truck",
                    }
                ),
                "Here are the closest stretches.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Show me trucks for $500/mo over 60 months"
        )
        self.assertEqual(len(result.matched_vehicles), MULTI_OPTION_TOTAL_CAP)
        for v in result.matched_vehicles:
            self.assertEqual(getattr(v, "_budget_fit", None), "over_budget")


# ---- Test 9: payment-consistency check accepts stretch quotes -------------


class PaymentConsistencyAcceptsStretchPaymentsTests(TestCase):
    def test_stretch_payment_quote_does_not_trip_drift(self):
        # Build a synthetic context: matched has a payment of $517,
        # closest_above has a stretch payment of $705. The
        # check_payment_consistency function (called by
        # handle_user_message with allowed_payments = matched + stretch)
        # must accept BOTH numbers.
        reply = (
            "The Ranger lands at $517/mo. We also have a Tundra around "
            "$705/mo if you'd like to stretch a longer term."
        )
        # Mirror what handle_user_message builds:
        allowed_payments = [517.0, 705.0]
        drift = check_payment_consistency(
            reply,
            target_monthly=500.0,
            allowed_payments=allowed_payments,
        )
        self.assertEqual(drift, [])

    def test_stretch_payment_without_allowance_does_trip_drift(self):
        # Sanity: without the stretch payment in allowed_payments, the
        # quote logs as drift. Confirms our fix is the thing
        # accepting the value.
        reply = "We also have a Tundra around $705/mo."
        drift = check_payment_consistency(
            reply,
            target_monthly=500.0,
            allowed_payments=[517.0],
        )
        self.assertEqual(drift, [705.0])


# ---- Test 10: fabricated-inventory guard still strict ---------------------


class FabricatedInventoryGuardAcceptsRealStretchesTests(TestCase):
    """Phase 8s/UX promotion — stretches are now matched_vehicles
    cards, so their Stock #s sit in the fabricated-inventory guard's
    allow-list. An LLM citing a real stretch Stock # MUST pass; an LLM
    citing a Stock # that doesn't exist anywhere still fires the
    guard."""

    def test_llm_citing_real_stretch_stock_passes_guard(self):
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "truck",
                    }
                ),
                # OVER-0 is now a legitimate matched_vehicles card —
                # the guard must allow this citation through.
                "Stock #OVER-0 is a great stretch option.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Show me trucks for $500/mo over 60 months"
        )
        # Reply unchanged — no canned fabrication response.
        self.assertNotEqual(
            result.assistant_message.content, FABRICATED_INVENTORY_RESPONSE
        )
        meta = result.assistant_message.metadata or {}
        self.assertNotEqual(meta.get("flag"), "fabricated_inventory")

    def test_llm_citing_nonexistent_stock_still_triggers_guard(self):
        # Defense-in-depth: a Stock # that isn't in inventory at all
        # (and therefore not in matched_vehicles) still fires the
        # guard. Stretch promotion did not weaken this protection.
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "truck",
                    }
                ),
                "Try Stock #FAKE-999 instead — it lands at $705/mo.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Show me trucks for $500/mo over 60 months"
        )
        self.assertEqual(
            result.assistant_message.content, FABRICATED_INVENTORY_RESPONSE
        )
        meta = result.assistant_message.metadata or {}
        self.assertEqual(meta.get("flag"), "fabricated_inventory")
        self.assertIn("FAKE-999", meta.get("fabricated_stocks") or [])


# ---- Phase 8s/UX: realistic-stretch filter cap ----------------------------


class RealisticStretchFilterCapTests(TestCase):
    """The realistic-stretch filter caps closest_above at
    ``max(STRETCH_FLOOR_DOLLARS, target * STRETCH_PERCENT_OF_TARGET)``
    above target. This prevents the LLM from being asked to pitch a
    $1500/mo F-150 to a $500/mo customer as "stretching just a bit".
    """

    def test_500_target_cap_is_floor_dollars(self):
        # At $500/mo target, max($150, 30% × $500=$150) → $150 floor.
        # An over at $700/mo (delta $200) is excluded; an over at $620
        # (delta $120) is included.
        _make_vehicle("WAY-OVER", "32500", model="F-150")  # ≈ $700/mo
        _make_vehicle("STRETCH-OK", "28800", model="F-150")  # ≈ $620/mo
        profile = {"target_monthly_payment": 500, "down_payment": 0, "term_months": 60}
        ctx = build_budget_context(profile, "$500/mo trucks")
        stocks = {v.stock_number for v in ctx.closest_above}
        self.assertIn("STRETCH-OK", stocks)
        self.assertNotIn("WAY-OVER", stocks)

    def test_1000_target_cap_uses_30_percent(self):
        # At $1000/mo target, max($150, $300) → $300. So overs up to
        # $1300/mo qualify; $1400 does not.
        _make_vehicle("BIG-STRETCH", "60000", model="F-150")  # ≈ $1290/mo
        _make_vehicle("BIG-OVER", "65000", model="F-150")  # ≈ $1400/mo
        profile = {"target_monthly_payment": 1000, "down_payment": 0, "term_months": 60}
        ctx = build_budget_context(profile, "$1000/mo trucks")
        stocks = {v.stock_number for v in ctx.closest_above}
        self.assertIn("BIG-STRETCH", stocks)
        self.assertNotIn("BIG-OVER", stocks)

    def test_300_target_cap_clamps_at_floor(self):
        # At $300/mo target, 30% = $90 → floor of $150 wins. Overs up to
        # $450/mo qualify; $500 does not.
        _make_vehicle("SMALL-STRETCH", "20000", model="Maverick")  # ≈ $430/mo
        _make_vehicle("SMALL-OVER", "23000", model="Maverick")  # ≈ $495/mo
        profile = {"target_monthly_payment": 300, "down_payment": 0, "term_months": 60}
        ctx = build_budget_context(profile, "$300/mo")
        stocks = {v.stock_number for v in ctx.closest_above}
        self.assertIn("SMALL-STRETCH", stocks)
        self.assertNotIn("SMALL-OVER", stocks)


# ---- Phase 8s/UX: stretch-line daily / weekly reframe ---------------------


class StretchLineDailyWeeklyReframeTests(TestCase):
    """The stretch line pre-computes a per-day and per-week reframe of
    the payment delta so the LLM can drop natural prose like "about
    $5 more a day" without doing the math itself."""

    def test_stretch_line_renders_per_day_and_per_week(self):
        from dealer_ai.services.chat_engine import _format_stretch_line

        v = _make_vehicle("STRETCH-DAILY", "30000", model="F-150")
        v._estimated_payment = 620.0
        v._payment_delta = 120.0
        v._budget_fit = "over_budget"
        line = _format_stretch_line(v, target=500.0)
        # Delta block carries both reframes.
        self.assertIn("/day", line)
        self.assertIn("/week", line)
        # $120 / 30 = $4.00/day; $120 × 7 / 30 = $28/week (≈$28).
        self.assertIn("$4.00/day", line)
        self.assertIn("~$28/week", line)

    def test_stretch_line_skips_reframe_when_delta_zero(self):
        from dealer_ai.services.chat_engine import _format_stretch_line

        v = _make_vehicle("STRETCH-EQUAL", "23000", model="Maverick")
        v._estimated_payment = 500.0
        v._payment_delta = 0.0
        v._budget_fit = "fit"
        line = _format_stretch_line(v, target=500.0)
        # No positive delta → no per-day / per-week reframe added.
        self.assertNotIn("/day", line)
        self.assertNotIn("/week", line)


# ---- Phase 8s/UX: conversational sales-tone reply rule --------------------


class ConversationalReplyRuleShapeTests(TestCase):
    """The new reply rule reads like sales coaching, not a numbered
    checklist. Positive shape: signature opener, soft close, daily
    reframe instruction, "newer year / higher trim / Lariat vs XLT"
    benefit anchors. Negative shape: no step numbers, no bullets."""

    def setUp(self):
        self.profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
        }

    def test_rule_includes_signature_opener_and_soft_close(self):
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # Signature opener phrasing.
        self.assertIn("really close at about", block)
        # Soft-close phrasing.
        self.assertIn("Would that be something", block)
        # Daily-reframe instruction is explicit.
        self.assertIn("$5 more a day", block)
        # And points the LLM at the precomputed numbers, not its own math.
        self.assertIn("per-day or per-week", block.lower())

    def test_rule_does_not_contain_numbered_steps_or_bullets(self):
        _seed_truck_inventory(fits=0, near_fits=1, overs=3)
        ctx = build_budget_context(self.profile, "$500/mo trucks")
        block = _format_budget_block(ctx)
        # The earlier rule leaked "Step 1:" / "Step 2:" / numbered-list
        # scaffolding ("1. ", "2. ", "3. ") into LLM output on weaker
        # local models. The conversational rewrite must not reintroduce
        # that scaffolding.
        for marker in (
            "Step 1",
            "Step 2",
            "Step 3",
            "1. ",
            "2. ",
            "3. ",
        ):
            self.assertNotIn(marker, block)
        # No reply line within the rule starts with a list marker.
        rule_idx = block.find("Reply rules")
        self.assertGreater(rule_idx, -1)
        rule_section = block[rule_idx:]
        for raw_line in rule_section.split("\n"):
            stripped = raw_line.strip()
            if not stripped:
                continue
            self.assertFalse(
                stripped.startswith(("- ", "* ", "• ")),
                f"rule line should not start with a bullet marker: {raw_line!r}",
            )
        # And the rule itself must explicitly forbid lists / numbered
        # steps in the customer reply.
        self.assertIn("NO bulleted", block)
        self.assertIn("NO numbered steps", block)
