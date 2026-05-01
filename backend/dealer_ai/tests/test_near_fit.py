"""Phase 8f — near-fit budget matching tests.

Bug being fixed: at $500/mo with $3,000 down, the assistant was telling the
customer no trucks fit — but the seeded 2019 Ranger at $26,995 actually
estimates around $517/mo, which is only $17 over the target. That should
surface as "close to your target", not be hidden behind a narrowing question.

Three buckets:
  - fit         estimated payment <= target
  - near_fit    payment <= target + max($75, 15%)
  - over_budget anything above the near-fit ceiling
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    _classify_candidates,
    build_budget_context,
)
from dealer_ai.services.payment_engine import estimate_payment

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock, price, *, model="F-150", body="truck", condition="new"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        body_style=body,
        condition=condition,
        price=Decimal(price),
    )


# ---- _classify_candidates --------------------------------------------------


class ClassifyCandidatesTests(TestCase):
    def test_buckets_by_payment_not_price(self):
        cheap = _make_vehicle("CHEAP", "20000")  # ~$430/mo
        near = _make_vehicle("NEAR", "26995", model="Ranger")  # ~$517/mo
        mid = _make_vehicle("MID", "33495", model="Maverick")  # ~$653/mo
        far = _make_vehicle("FAR", "78000", model="F-150")  # ~$1500/mo

        in_b, near_b, over_b = _classify_candidates(
            [cheap, near, mid, far],
            target_monthly=500.0,
            down_payment=3000.0,
            term_months=60,
            tolerance=75.0,
        )

        in_ids = {v.id for v in in_b}
        near_ids = {v.id for v in near_b}
        over_ids = {v.id for v in over_b}

        self.assertIn(cheap.id, in_ids)
        self.assertIn(near.id, near_ids)
        self.assertIn(mid.id, over_ids)
        self.assertIn(far.id, over_ids)

    def test_annotations_attached_to_each_vehicle(self):
        v = _make_vehicle("ANNOT", "30000")
        in_b, near_b, over_b = _classify_candidates(
            [v],
            target_monthly=500.0,
            down_payment=3000.0,
            term_months=60,
            tolerance=75.0,
        )
        self.assertTrue(hasattr(v, "_budget_fit"))
        self.assertTrue(hasattr(v, "_estimated_payment"))
        self.assertTrue(hasattr(v, "_payment_delta"))
        self.assertIn(v._budget_fit, ("fit", "near_fit", "over_budget"))
        self.assertGreater(v._estimated_payment, 0)


# ---- build_budget_context with near-fit ------------------------------------


class BudgetContextNearFitTests(TestCase):
    def test_500_with_3k_down_finds_ranger_as_near_fit(self):
        """The exact reported scenario: $500/mo + $3,000 down should surface
        the 2019-priced Ranger at $26,995 as near-fit (~$517/mo)."""
        ranger = _make_vehicle(
            "FF-USED-104",
            "26995",
            model="Ranger",
            condition="used",
        )
        f150_used = _make_vehicle(
            "FF-USED-101",
            "48995",
            model="F-150",
            condition="certified",
        )

        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        ctx = build_budget_context(
            profile, "I want a truck for $500/month", regex_hits={}
        )

        self.assertTrue(ctx.is_budget_query)
        self.assertEqual(ctx.tolerance, 75.0)  # max($75, 15% of $500) == $75

        all_matched_ids = {
            v.id for v in (ctx.matched_in_budget + ctx.near_fit)
        }
        self.assertIn(ranger.id, all_matched_ids)
        # Ranger should land in near_fit (around $517/mo). Annotations live
        # on the fresh instance returned by build_budget_context, not on the
        # original test-fixture object.
        ranger_annotated = next(v for v in ctx.near_fit if v.id == ranger.id)
        self.assertEqual(ranger_annotated._budget_fit, "near_fit")
        self.assertGreater(ranger_annotated._payment_delta, 0)
        self.assertLess(ranger_annotated._payment_delta, 75)

        # The expensive used F-150 stays out — it's well past the near-fit cap.
        self.assertNotIn(f150_used.id, all_matched_ids)

    def test_in_budget_separated_from_near_fit(self):
        cheap = _make_vehicle("CHEAP", "20000")  # in_budget
        ranger = _make_vehicle("RANGER", "26995", model="Ranger")  # near_fit
        profile = {"target_monthly_payment": 500, "down_payment": 3000, "term_months": 60}
        ctx = build_budget_context(profile, "trucks for $500/mo")
        self.assertEqual({v.id for v in ctx.matched_in_budget}, {cheap.id})
        self.assertEqual({v.id for v in ctx.near_fit}, {ranger.id})

    def test_no_fit_no_near_fit_returns_closest_above(self):
        # Phase 8s/UX: closest_above is filtered by the realistic-stretch
        # cap (max $150 / 30% above target). At $200/mo target, that cap
        # is $150 → payment ≤ $350/mo → price ≲ $16k. Seed two overs
        # within that window so the stretches actually surface.
        _make_vehicle("EXP-A", "13500")
        _make_vehicle("EXP-B", "14000")
        profile = {"target_monthly_payment": 200, "down_payment": 0, "term_months": 60}
        ctx = build_budget_context(profile, "$200 a month")
        self.assertEqual(ctx.matched_in_budget, [])
        self.assertEqual(ctx.near_fit, [])
        self.assertGreater(len(ctx.closest_above), 0)

    def test_closest_above_fills_spare_slot_when_fits_plus_near_below_cap(self):
        """Phase 8s/UX update: when fit + near_fit < 3, closest_above
        is populated to fill the spare slots up to the multi-option cap.
        Stretches are TEXT-ONLY — they never enter matched_vehicles[],
        but they reach the LLM via the BUDGET ANALYSIS block so it has
        real anchor points for "options just above your target" framing.
        """
        _make_vehicle("OK-1", "20000")  # in_budget (1 fit)
        _make_vehicle("OK-2", "26995", model="Ranger")  # near_fit (1 near)
        # Phase 8s/UX: realistic-stretch filter caps overs at max($150,
        # 30%) above target. At $500 target with $3k down, ~$30k lands
        # roughly $565/mo → delta ~$65, well inside the $150 window.
        _make_vehicle("OK-3", "30000")  # over_budget — closest_above fills 1 slot
        profile = {"target_monthly_payment": 500, "down_payment": 3000, "term_months": 60}
        ctx = build_budget_context(profile, "$500 a month")
        # 1 fit + 1 near + 1 stretch = 3 total context options.
        self.assertEqual(len(ctx.matched_in_budget), 1)
        self.assertEqual(len(ctx.near_fit), 1)
        self.assertEqual(len(ctx.closest_above), 1)
        self.assertEqual(ctx.closest_above[0].stock_number, "OK-3")

    def test_used_inventory_included_when_no_condition_specified(self):
        _make_vehicle("NEW-T", "55000", model="F-150", condition="new")
        used_truck = _make_vehicle(
            "USED-T", "26995", model="Ranger", condition="used"
        )
        profile = {"target_monthly_payment": 500, "down_payment": 3000, "term_months": 60}
        ctx = build_budget_context(profile, "I want a truck for $500/mo")
        ids = {v.id for v in (ctx.matched_in_budget + ctx.near_fit)}
        # Used truck should appear (near-fit). New truck is over budget.
        self.assertIn(used_truck.id, ids)

    def test_explicit_new_filter_excludes_used(self):
        _make_vehicle("U-T", "26995", model="Ranger", condition="used")
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "condition": "new",
        }
        ctx = build_budget_context(profile, "new only")
        ids = {v.id for v in (ctx.matched_in_budget + ctx.near_fit)}
        self.assertNotIn("U-T", {v.stock_number for v in (ctx.matched_in_budget + ctx.near_fit)})


# ---- _format_budget_block phrasing rules ----------------------------------


class BudgetBlockFramingTests(TestCase):
    def test_near_fit_block_describes_as_close_not_exact_fit(self):
        from dealer_ai.services.chat_engine import _format_budget_block

        _make_vehicle("R-1", "26995", model="Ranger")
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        ctx = build_budget_context(profile, "$500 a month")
        block = _format_budget_block(ctx)

        # When near-fit exists, the block must instruct the LLM not to call
        # them exact fits.
        self.assertIn("close to your target", block)
        self.assertIn("NEVER call them exact fits", block)
        # Phase 8s/UX — single near-fit with no realistic stretches: the
        # soft-close lever prompt replaces the older robotic "EXACTLY ONE
        # focused narrowing question" rule. The reply still resolves to
        # exactly one question, just phrased like a salesperson.
        self.assertIn("Would you be open to adjusting one of those", block)
        self.assertIn("closest match", block)

    def test_full_fit_block_no_narrowing_question(self):
        from dealer_ai.services.chat_engine import _format_budget_block

        _make_vehicle("CHEAP-1", "20000")
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
        }
        ctx = build_budget_context(profile, "$500 a month")
        block = _format_budget_block(ctx)
        self.assertIn("IN BUDGET", block)
        self.assertIn(
            "No narrowing question is needed when in-budget options exist",
            block,
        )

    def test_no_fit_no_near_block_asks_narrowing_question(self):
        from dealer_ai.services.chat_engine import _format_budget_block

        # Phase 8s/UX: seed an over-budget vehicle that lands inside
        # the realistic-stretch cap (max $150 / 30% above target) so
        # ``closest_above`` populates and the OVER BUDGET section is
        # rendered. With promotion, the single-stretch branch fires the
        # soft-close lever rule (semantically equivalent to "exactly
        # one focused narrowing question" — the customer is still
        # asked one question to widen the search).
        _make_vehicle("EXP-1", "13500")
        profile = {
            "target_monthly_payment": 200,
            "down_payment": 0,
            "term_months": 60,
        }
        ctx = build_budget_context(profile, "$200 a month")
        block = _format_budget_block(ctx)
        # OVER BUDGET section header is present.
        self.assertIn("OVER BUDGET", block)
        # The reply rule resolves to one question via the soft close.
        self.assertIn("Would you be open to adjusting one of those", block)


# ---- ChatEngine integration -----------------------------------------------


class ChatEngineNearFitIntegrationTests(TestCase):
    def test_matched_vehicles_includes_near_fit(self):
        cheap = _make_vehicle("CHEAP", "20000")
        ranger = _make_vehicle("RANGER", "26995", model="Ranger")
        _make_vehicle("EXP", "78000")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(replies=[json_reply({}), "ok"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500 a month — what fits?")

        ids = {v.id for v in result.matched_vehicles}
        self.assertIn(cheap.id, ids)
        self.assertIn(ranger.id, ids)
        # Metadata records both buckets.
        bq = result.assistant_message.metadata.get("budget_query")
        self.assertEqual(bq["in_budget_count"], 1)
        self.assertEqual(bq["near_fit_count"], 1)
        # Per-vehicle annotations are exposed for UI badges.
        fits = bq.get("vehicle_fits") or {}
        self.assertEqual(fits[str(cheap.id)]["budget_fit"], "fit")
        self.assertEqual(fits[str(ranger.id)]["budget_fit"], "near_fit")
        self.assertGreater(fits[str(ranger.id)]["payment_delta"], 0)

    def test_serializer_exposes_budget_fit_on_matched_vehicles(self):
        """The per-turn response sent to the frontend carries the budget_fit
        annotations (annotations live on the in-memory instance for the
        duration of the request — that's enough to drive the chat-card UI)."""
        from dealer_ai.serializers import VehicleSerializer

        _make_vehicle("RANGER", "26995", model="Ranger")
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "target_monthly_payment": 500,
                        "down_payment": 3000,
                        "term_months": 60,
                    }
                ),
                "ok",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I want a truck for $500/month, I have $3,000 down."
        )

        # Serialize the matched_vehicles the same way views.send_message does.
        serialized = VehicleSerializer(result.matched_vehicles, many=True).data
        ranger_obj = next(
            v for v in serialized if v["stock_number"] == "RANGER"
        )
        self.assertEqual(ranger_obj["budget_fit"], "near_fit")
        self.assertIsNotNone(ranger_obj["estimated_payment"])
        self.assertGreater(ranger_obj["estimated_payment"], 500)
        self.assertGreater(ranger_obj["payment_delta"], 0)

        # And confirm the persisted assistant-message metadata captured the
        # same fit data so it's available later via the admin/session APIs.
        bq = result.assistant_message.metadata.get("budget_query") or {}
        fits = bq.get("vehicle_fits") or {}
        ranger_fit = next(iter(fits.values()))
        self.assertEqual(ranger_fit["budget_fit"], "near_fit")

    def test_no_fit_no_near_fit_surfaces_stretch_card_and_softclose(self):
        # Phase 8s/UX promotion: when no fit / no near-fit exist but a
        # realistic stretch (within max($150, 30%) of target) is in
        # inventory, that stretch surfaces as a card with budget_fit=
        # "over_budget", and the system prompt carries the soft-close
        # lever rule (replacing the older "exactly one focused
        # narrowing question" instruction).
        _make_vehicle("EXP-A", "13500")  # ≈ $290/mo at $200 target
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 200,
                "down_payment": 0,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(replies=[json_reply({}), "ok"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("only $200/mo")
        # The stretch is now a card, but no_fit metadata stays True
        # (no IN-BUDGET / NEAR-FIT match exists).
        self.assertEqual(
            [v.stock_number for v in result.matched_vehicles], ["EXP-A"]
        )
        self.assertEqual(
            getattr(result.matched_vehicles[0], "_budget_fit", None),
            "over_budget",
        )
        bq = result.assistant_message.metadata.get("budget_query")
        self.assertTrue(bq["no_fit"])

        # The system prompt sent to the LLM contains the soft-close
        # lever rule (one soft question, not the older robotic
        # narrowing-question phrasing).
        sent = "\n".join(
            m["content"] for m in provider.calls[-1] if m["role"] == "system"
        )
        self.assertIn(
            "Would you be open to adjusting one of those so I can show "
            "you more options?",
            sent,
        )


# ---- Sanity check on the actual seeded inventory math ----------------------


class SeededInventoryMathSanity(TestCase):
    """Cross-check: the affordability math used by the engine matches what
    payment_engine.estimate_payment computes directly. Catches drift if either
    side ever changes."""

    def test_ranger_payment_at_500_3k_60mo_is_near_fit_window(self):
        v = _make_vehicle("FF-USED-104", "26995", model="Ranger", condition="used")
        est = estimate_payment(v.price, down_payment=3000, term_months=60)
        # Should be a small overage — well within the $75 tolerance.
        self.assertLess(est.monthly_payment, 575)
        self.assertGreater(est.monthly_payment, 500)
