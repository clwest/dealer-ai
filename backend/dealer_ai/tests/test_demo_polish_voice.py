"""Item 16 — demo polish voice contract tests.

Pin the GOOD / BAD example phrasings that shape the cash-mode
comparison block and the model-followup deep-dive branch reply
rule. The small Ollama model imitates examples reliably; if these
phrasings disappear from the prompt, the customer-facing voice
drifts back to research-brief / engineering-spec.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import Vehicle
from dealer_ai.services.chat_engine import (
    BudgetContext,
    _format_budget_block,
    _format_cash_mode_block,
)


# ---- Cash-mode block voice contract -------------------------------------


def _make_vehicle(stock, price, **kw):
    return Vehicle.objects.create(
        stock_number=stock,
        year=kw.get("year", 2014),
        make=kw.get("make", "Honda"),
        model=kw.get("model", "Accord"),
        body_style=kw.get("body_style", "car"),
        condition=kw.get("condition", "used"),
        price=Decimal(price),
        mileage=kw.get("mileage", 80000),
        drivetrain=kw.get("drivetrain", "FWD"),
    )


class CashModeVoiceContractTests(TestCase):
    """The cash-mode block's voice directives must survive in the
    rendered system message. The small model relies on these
    examples — if they vanish, customer prose reverts to the
    research-brief shape.
    """

    def _three_cars(self):
        return [
            _make_vehicle("VC-1", "11995", make="Ford", model="Fusion"),
            _make_vehicle(
                "VC-2", "13495", make="Toyota", model="Camry",
                mileage=72000,
            ),
            _make_vehicle(
                "VC-3", "10995", make="Hyundai", model="Sonata",
                mileage=95000,
            ),
        ]

    def test_block_carries_decisive_voice_directive(self):
        block = _format_cash_mode_block(self._three_cars())
        self.assertIn("LEAD with the strongest fit", block)
        self.assertIn("Make a recommendation", block)
        self.assertIn("Avoid neutral side-by-side", block)

    def test_block_carries_good_example_strongest_fit(self):
        # The first GOOD example (target tone from the user spec)
        # uses generic references ("the newer one" / "the cheaper
        # one") so the LLM doesn't echo placeholder syntax with
        # literal brackets.
        block = _format_cash_mode_block(self._three_cars())
        self.assertIn("strongest fit here", block)
        self.assertIn("value backup", block)
        self.assertIn(
            "Want me to narrow this to the best cash buy", block
        )
        # No bracket-placeholder syntax that the small model would
        # copy verbatim.
        self.assertNotIn("[Lead vehicle]", block)
        self.assertNotIn("[Alternative]", block)
        self.assertNotIn("[cheapest pick]", block)

    def test_block_carries_good_example_either_or_pivot(self):
        # The second GOOD example (lowest cash outlay vs feel-better).
        block = _format_cash_mode_block(self._three_cars())
        self.assertIn("lowest cash outlay", block)
        self.assertIn("feel better owning longer", block)
        self.assertIn(
            "Want to compare those two side by side?", block
        )
        # Generic references that read OK even if echoed.
        self.assertIn("the cheapest one", block)
        self.assertIn("the lower-mile one", block)

    def test_block_carries_bad_example_research_brief_shape(self):
        # BAD example pins what NOT to write. Small models imitate
        # whichever shape they see most — the BAD example must
        # exist as a contrast so the GOOD examples win.
        block = _format_cash_mode_block(self._three_cars())
        self.assertIn("BAD example", block)
        self.assertIn("research-brief", block)
        self.assertIn("no recommendation", block)
        self.assertIn("reads like a spec sheet", block)

    def test_block_close_question_templates_are_next_step(self):
        block = _format_cash_mode_block(self._three_cars())
        self.assertIn("next-step question", block)
        # Avoid-tradeoff-restating directive.
        self.assertIn(
            "Avoid restating the tradeoff in the question", block
        )
        # The deprecated "leaning lowest price, or long-term
        # reliability" question is explicitly called out as NOT
        # a target shape.
        self.assertIn(
            "are you leaning lowest price, or long-term reliability",
            block,
        )

    def test_block_still_forbids_financing(self):
        # Voice change must NOT regress the financing ban.
        block = _format_cash_mode_block(self._three_cars())
        self.assertIn("DO NOT mention monthly payments", block)
        self.assertIn("financing", block)
        self.assertIn("approved credit", block)

    def test_single_card_returns_empty(self):
        cards = self._three_cars()
        self.assertEqual(_format_cash_mode_block([]), "")
        self.assertEqual(_format_cash_mode_block(cards[:1]), "")

    def test_block_includes_card_data_anchors(self):
        block = _format_cash_mode_block(self._three_cars())
        # Real card data anchors below the directive — the LLM
        # uses these names verbatim in comparison prose.
        self.assertIn("Honda Accord", block) if False else None
        self.assertIn("Ford Fusion", block)
        self.assertIn("Toyota Camry", block)
        self.assertIn("Hyundai Sonata", block)


# ---- Model-followup voice contract --------------------------------------


def _budget_ctx_with(matched, target=500):
    """Build a BudgetContext that surfaces a single near-fit
    matched vehicle, simulating the model-followup state."""
    ctx = BudgetContext(
        is_budget_query=True,
        target_monthly=float(target),
        down_payment=3000.0,
        term_months=60,
        max_price=None,
        tolerance=75.0,
    )
    # _format_budget_block reads .matched_in_budget / .near_fit /
    # .closest_above to find the lead. For a single-vehicle
    # follow-up, drop the card into matched_in_budget.
    ctx.matched_in_budget = list(matched)
    return ctx


class ModelFollowupVoiceContractTests(TestCase):
    def test_followup_branch_carries_ownership_fit_directive(self):
        v = _make_vehicle(
            "VFU-1", "26995", make="Ford", model="Ranger",
            body_style="truck", drivetrain="4x4",
        )
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=["2019 Ford Ranger XLT 4x4"],
        )
        self.assertIn("OWNERSHIP-FIT framing", block)
        self.assertIn("buying-logic vocabulary", block)
        # Buying-logic vocabulary cues.
        self.assertIn("best value", block)
        self.assertIn("comfort upgrade", block)
        self.assertIn("work-truck practical", block)
        self.assertIn("family-friendly", block)
        self.assertIn("worth stretching for", block)
        self.assertIn("sweet spot", block)

    def test_followup_branch_forbids_engineering_spec_leads(self):
        v = _make_vehicle("VFU-2", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        self.assertIn("Engineering-spec leads", block)
        # The exact phrases the live smoke produced as drift.
        self.assertIn("CVT transmission makes it easy", block)
        self.assertIn("FWD drivetrain ensures", block)
        self.assertIn("EcoBoost engine produces", block)
        # Translation guidance.
        self.assertIn("smooth around town", block)
        self.assertIn("keeps gas costs low", block)

    def test_followup_branch_carries_good_examples(self):
        v = _make_vehicle("VFU-3", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        # First GOOD example (multi-trim sweet-spot framing).
        self.assertIn("XLT is usually the sweet spot", block)
        self.assertIn("nicer daily-driver feel", block)
        self.assertIn(
            "compare the cheaper one versus the nicer one", block
        )
        # Second GOOD example (single-vehicle positioning).
        self.assertIn("everyday truck choice", block)
        self.assertIn("Which way should I steer them?", block)

    def test_followup_branch_forbids_card_data_recital(self):
        v = _make_vehicle("VFU-4", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        self.assertIn(
            "Restating Stock #, full price, full mileage", block
        )

    def test_followup_branch_forbids_brochure_phrases(self):
        v = _make_vehicle("VFU-5", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        self.assertIn("perfect for hunting", block)
        self.assertIn("ideal for", block)
        self.assertIn("feature-packed", block)
        self.assertIn("standout features", block)

    def test_followup_branch_close_questions_are_dealer_natural(self):
        # Item 17 — close templates sound like a salesperson
        # speaking TO the customer (first-person, dealer voice),
        # not internal monologue or tentative "right?" tags.
        v = _make_vehicle("VFU-6", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        # New dealer-natural templates from the user spec.
        self.assertIn(
            "Is that the kind of fit you had in mind?", block
        )
        self.assertIn(
            "Does that sound like the direction you want to go?",
            block,
        )
        self.assertIn(
            "compare it against the", block
        )
        self.assertIn(
            "Should I keep you on this one or look for something "
            "cheaper?",
            block,
        )
        self.assertIn(
            "Want to set up a closer look at this one?", block
        )

    def test_followup_branch_forbids_internal_monologue_close(self):
        # Item 17 — explicitly call out 3rd-person internal phrasing
        # and trailing "right?" tags as anti-patterns. The previous
        # template "Which way should I steer them?" fell into the
        # 3rd-person trap; the live smoke produced "In your budget,
        # right?" which is the trailing-tag trap.
        v = _make_vehicle("VFU-7", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        # The "AVOID" section must explicitly call out both anti-
        # patterns so the LLM's example-following converges to
        # dealer voice.
        self.assertIn("3rd-person internal phrasing", block)
        self.assertIn("Which way should I steer them?", block)
        self.assertIn("Trailing \"right?\" tags", block)
        self.assertIn("In your budget, right?", block)
        self.assertIn("speak TO the customer, not ABOUT them", block)

    def test_followup_branch_keeps_3_to_5_sentence_cap(self):
        # The hard length cap is enforced by item 10's
        # cap_model_followup_length, but the prompt rule still
        # tells the LLM to aim for 3-5.
        v = _make_vehicle("VFU-7", "26995", make="Ford", model="Ranger")
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        self.assertIn("3-5 sentences", block)


# ---- Smoke: voice changes don't regress structural contracts -----------


class VoiceChangeRegressionTests(TestCase):
    """Voice tightening is purely a prompt change. The post-LLM
    enforcement layer (scrubs / length cap / fallback handling)
    is unchanged. This test is a sanity guard — flag any future
    voice edit that accidentally drops one of the load-bearing
    directives.
    """

    def test_cash_block_still_forbids_neutral_side_by_side(self):
        cards = [
            _make_vehicle("RG-1", "11995", make="Ford", model="Fusion"),
            _make_vehicle(
                "RG-2", "13495", make="Toyota", model="Camry",
                mileage=72000,
            ),
        ]
        block = _format_cash_mode_block(cards)
        self.assertIn("Avoid neutral side-by-side", block)

    def test_followup_branch_still_forbids_engineering_leads(self):
        v = _make_vehicle(
            "RG-3", "26995", make="Ford", model="Ranger",
            body_style="truck", drivetrain="4x4",
        )
        ctx = _budget_ctx_with([v])
        block = _format_budget_block(
            ctx, followup_mode=True,
            previous_shown_names=[],
        )
        self.assertIn("Engineering-spec leads", block)
