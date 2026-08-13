"""Post-LLM safety rewrite tests.

These verify the second-stage guard that catches hallucinated sensitive
language in the model's draft reply BEFORE it is persisted or returned.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings

from dealer_ai.models import ChatMessage, ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    APPOINTMENT_REQUEST_NEEDS_VEHICLE_RESPONSE,
    EXTERNAL_VALUE_RESPONSE,
    GUARD_RESPONSE,
    HANDOFF_RESPONSE,
    IDENTITY_RESPONSE,
    IMAGE_REQUEST_NEEDS_VEHICLE_RESPONSE,
    INTERNAL_CONFUSION_FALLBACK,
    NEGOTIATION_RESPONSE,
    SYSTEM_PROMPT,
    BudgetContext,
    ChatEngine,
    _format_budget_block,
    _format_discovery_block,
    _format_vehicle_block,
    _render,
    _should_enter_discovery_mode,
    build_negotiation_response,
    detect_appointment_request,
    detect_external_value_inquiry,
    detect_handoff_request,
    detect_identity_request,
    detect_image_request,
    detect_internal_confusion,
    detect_negotiation_request,
    detect_unsafe_response,
    scrub_budget_category_labels,
    scrub_default_assumption_language,
    scrub_internal_directives,
    scrub_post_llm_override,
)

from ._mocks import MockLLMProvider, json_reply


def _make_vehicle(stock="POST-1", *, price="55000"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        model="F-150",
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


class DetectUnsafeResponseTests(TestCase):
    def test_flags_each_forbidden_phrase(self):
        for phrase in [
            "Our dealer cost is around $52,000.",
            "The dealer's cost on this truck is $50k.",
            "Invoice price for this vehicle was $60,500.",
            "Our internal cost is lower than sticker.",
            "The internal price is around $50k.",
            "Our profit margin is about 8%.",
            "There's a $2k holdback on this model.",
            "Acquisition cost was $48,000.",
            "Our wholesale cost is $44,000.",
            "We paid $45,000 for this Ford.",
            "Our cost on this F-150 was $50k.",
        ]:
            self.assertTrue(detect_unsafe_response(phrase), msg=phrase)

    def test_normal_responses_pass(self):
        for phrase in [
            "This F-150 is priced at $58,995.",
            "Our 2025 lineup includes the F-150 XLT and Lariat.",
            "Estimated monthly payment is around $1,067/mo.",
            "It's a great value at this price point.",
            "Sales can confirm real terms when you visit.",
            "",
        ]:
            self.assertFalse(detect_unsafe_response(phrase), msg=phrase)


class ChatEnginePostLLMRewriteTests(TestCase):
    def test_clean_reply_passes_through(self):
        session = ChatSession.objects.create()
        _make_vehicle()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Here are some F-150 options at $55,000.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me F-150s under 60k")

        self.assertEqual(
            result.assistant_message.content,
            "Here are some F-150 options at $55,000.",
        )
        self.assertNotIn("flag", result.assistant_message.metadata)

    def test_unsafe_reply_is_rewritten(self):
        session = ChatSession.objects.create()
        v = _make_vehicle()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Sure — our dealer cost on this F-150 is around $52,000, "
                "so we have room to come down on the sticker.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me F-150s under 60k")

        # Customer-facing reply is replaced.
        self.assertEqual(result.assistant_message.content, GUARD_RESPONSE)
        # Original is NOT persisted in the database.
        self.assertNotIn(
            "dealer cost",
            result.assistant_message.content.lower(),
        )
        # Audit flag is set.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "post_llm_safety_rewrite",
        )
        # Provider was actually invoked (this is a model-output rewrite,
        # not a pre-LLM short-circuit).
        self.assertEqual(
            result.assistant_message.metadata.get("provider"),
            provider.name,
        )
        # Vehicles still attached.
        self.assertIn(v, result.matched_vehicles)
        self.assertIn(v, result.assistant_message.matched_vehicles.all())

    def test_unsafe_reply_logs_original_for_audit(self):
        session = ChatSession.objects.create()
        _make_vehicle()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "We paid $45,000 for this F-150 so we can flex on price.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)

        with self.assertLogs(
            "dealer_ai.services.chat_engine", level=logging.WARNING
        ) as cm:
            engine.handle_user_message("Show me F-150s")

        joined = "\n".join(cm.output)
        self.assertIn("Post-LLM safety", joined)
        self.assertIn("We paid", joined)  # Original captured in server log only.

    def test_rewrite_preserves_extracted_intent_metadata(self):
        """Intent extraction is independent of the rewrite — it should still
        record what the customer asked for."""
        session = ChatSession.objects.create()
        _make_vehicle()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {"intent": "vehicle_search", "vehicle_type": "truck"}
                ),
                "Our profit margin on this truck is around 7%.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me F-150s")

        self.assertEqual(
            result.assistant_message.content, GUARD_RESPONSE
        )
        # extracted_this_turn metadata still recorded.
        extracted = result.assistant_message.metadata.get("extracted_this_turn") or {}
        self.assertEqual(extracted.get("intent"), "vehicle_search")
        # Session profile updated as it normally would.
        session.refresh_from_db()
        self.assertEqual(session.extracted_profile.get("intent"), "vehicle_search")

    def test_rewrite_does_not_fire_for_pre_guard_short_circuit(self):
        """A flagged customer message hits the pre-LLM guard and never reaches
        this code path. Confirm the assistant flag is the pre-LLM one, not
        post-LLM."""
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["irrelevant"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("What is your dealer cost?")
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "prompt_injection",
        )
        # Provider was never called → cannot have triggered post-LLM rewrite.
        self.assertEqual(provider.calls, [])


# ---- Phase 8m+: internal-directive scrub ---------------------------------


class ScrubInternalDirectivesTests(TestCase):
    """Pure-function tests for the internal-directive scrub. The LLM
    occasionally echoes prompt directives verbatim (most often the
    parenthetical that sits inline with the W.A.C. qualifier). The scrub
    strips those phrases without touching legitimate W.A.C. copy or
    payment numbers."""

    def test_strips_parenthetical_budget_analysis_leak(self):
        text = (
            "Both Rangers come in around $498/mo (W.A.C. — see BUDGET "
            "ANALYSIS for full math; DO NOT recompute), close to your "
            "target."
        )
        cleaned, changed = scrub_internal_directives(text)
        self.assertTrue(changed)
        # Customer-harmful phrases removed.
        self.assertNotIn("BUDGET ANALYSIS", cleaned)
        self.assertNotIn("DO NOT recompute", cleaned)
        self.assertNotIn("see full math", cleaned)
        # Legitimate copy preserved.
        self.assertIn("$498/mo", cleaned)
        self.assertIn("(W.A.C.)", cleaned)
        self.assertIn("close to your target", cleaned)

    def test_strips_bare_directive_phrases(self):
        for phrase in [
            "Per BUDGET ANALYSIS the Escape fits.",
            "see full math for details",
            "DO NOT recompute the payment",
            "Per the AVAILABLE INVENTORY block, three options match.",
            "Check the KNOWN CUSTOMER PROFILE for context.",
            "INTERNAL DIRECTIVE: don't say this.",
            "internal calc gives a different number",
            "the realistic max sticker is around $17,995",
            "max sticker price for that target",
        ]:
            cleaned, changed = scrub_internal_directives(phrase)
            self.assertTrue(changed, msg=f"expected scrub for: {phrase!r}")
            for forbidden in (
                "BUDGET ANALYSIS",
                "AVAILABLE INVENTORY",
                "KNOWN CUSTOMER PROFILE",
                "INTERNAL DIRECTIVE",
                "see full math",
                "DO NOT recompute",
                "internal calc",
                "max sticker",
            ):
                self.assertNotIn(
                    forbidden,
                    cleaned,
                    msg=f"forbidden {forbidden!r} still in cleaned: {cleaned!r}",
                )

    def test_clean_reply_is_unchanged(self):
        text = (
            "These two come in around $475/mo (W.A.C.) — close to your "
            "$500/month target with $3,000 down. Want me to line one up?"
        )
        cleaned, changed = scrub_internal_directives(text)
        self.assertFalse(changed)
        self.assertEqual(cleaned, text)

    def test_preserves_payment_numbers_for_consistency_check(self):
        # The scrub runs BEFORE check_payment_consistency. The payment number
        # must survive the scrub so the consistency check can still verify it.
        text = (
            "$517/mo (W.A.C. — see BUDGET ANALYSIS for full math; DO NOT "
            "recompute) on the Escape."
        )
        cleaned, changed = scrub_internal_directives(text)
        self.assertTrue(changed)
        self.assertIn("$517/mo", cleaned)


class ChatEngineInternalDirectiveScrubTests(TestCase):
    """End-to-end: the canonical bug-report scenario — a model reply that
    leaks the (W.A.C. — see BUDGET ANALYSIS for full math; DO NOT
    recompute) parenthetical — must be sanitized before the customer sees
    it, with an audit flag set on the assistant message."""

    def test_directive_leak_without_strong_confusion_signal_is_scrubbed(self):
        # Phase 8n+: replies containing "BUDGET ANALYSIS" / "guidelines" /
        # "internal directive" now trigger the wholesale internal-confusion
        # fallback rather than partial scrub. To exercise the directive
        # scrub specifically, use a leak that doesn't include any of the
        # fallback trigger phrases — here, a "do not invent payments"
        # leak.
        session = ChatSession.objects.create()
        v = _make_vehicle("RNG-1", price="26995")
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "The Ranger comes in at $475/mo (W.A.C.). do not invent "
                "payments. Want me to line one up?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        body = result.assistant_message.content

        self.assertNotIn("do not invent payments", body.lower())
        self.assertIn("$475/mo", body)
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "internal_directive_scrubbed",
        )
        self.assertIn(v, result.assistant_message.matched_vehicles.all())

    def test_strong_confusion_leak_triggers_fallback_not_scrub(self):
        # Phase 8n+: "BUDGET ANALYSIS" in the reply is a strong confusion
        # signal — wholesale fallback replaces the reply rather than
        # partial-scrub leaving half-baked sentences.
        session = ChatSession.objects.create()
        _make_vehicle("RNG-1B", price="26995")
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "The Ranger comes in at $475/mo (W.A.C. — see BUDGET "
                "ANALYSIS for full math; DO NOT recompute).",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        body = result.assistant_message.content

        self.assertNotIn("BUDGET ANALYSIS", body)
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "internal_confusion_fallback",
        )

    def test_clean_reply_does_not_set_directive_flag(self):
        session = ChatSession.objects.create()
        _make_vehicle("RNG-2", price="26995")
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "The Ranger comes in around $475/mo (W.A.C.) — that's "
                "within your target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        self.assertNotEqual(
            result.assistant_message.metadata.get("flag"),
            "internal_directive_scrubbed",
        )


class BudgetBlockDoesNotExposeMaxPriceTests(TestCase):
    """Phase 8m+ second regression: 'budget of $17,995' instead of
    '$500/month with $3k down'. Root cause was the BUDGET ANALYSIS block
    surfacing max_price as a 'realistic max sticker' line — the LLM
    echoed that figure as the customer's 'budget'. The fix removes that
    line from the LLM-visible block and reframes the budget as
    monthly+down+term."""

    def test_budget_block_omits_max_price_dollar_figure(self):
        ctx = BudgetContext(
            is_budget_query=True,
            target_monthly=500.0,
            down_payment=3000.0,
            term_months=60,
            max_price=17995.0,  # the value the LLM was echoing back.
            tolerance=75.0,
        )
        block = _format_budget_block(ctx)
        # The exact dollar figure must not appear in the LLM-visible block.
        self.assertNotIn("$17,995", block)
        self.assertNotIn("17995", block)
        # Old framing labels must not appear.
        self.assertNotIn("max sticker", block.lower())
        self.assertNotIn("realistic max", block.lower())
        # The customer-facing framing must.
        self.assertIn("$500/mo", block)
        self.assertIn("$3,000", block)
        self.assertIn("60 months", block)

    def test_budget_block_keeps_target_and_down_and_term(self):
        # Sanity: even though we dropped max_price line, the customer's
        # actual budget framing must still be in the block for the LLM
        # to anchor on.
        ctx = BudgetContext(
            is_budget_query=True,
            target_monthly=700.0,
            down_payment=5000.0,
            term_months=72,
            max_price=99999.0,
            tolerance=105.0,
        )
        block = _format_budget_block(ctx)
        self.assertIn("$700/mo", block)
        self.assertIn("$5,000", block)
        self.assertIn("72 months", block)
        self.assertNotIn("$99,999", block)


class BothScrubsCanFireTogetherTests(TestCase):
    """Edge case: a reply that contains BOTH a rate leak and a directive
    leak should get cleaned by both scrubs and earn the combined flag."""

    def test_combined_flag_when_both_scrubs_fire(self):
        session = ChatSession.objects.create()
        _make_vehicle("RNG-3", price="26995")
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                # Combined rate + directive leak WITHOUT the strong
                # confusion-fallback triggers ("BUDGET ANALYSIS" /
                # "guidelines"), so both scrubs run side by side.
                "$475/mo @ 7.49% APR (W.A.C. — do not invent payments) "
                "on the Ranger.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        body = result.assistant_message.content
        self.assertNotIn("7.49%", body)
        self.assertNotIn("APR", body)
        self.assertNotIn("do not invent payments", body.lower())
        # Phase 8m+: multiple scrubs fired → generic combined flag, with
        # the per-scrub list available in metadata.scrubs for audits.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "multiple_scrubs_fired",
        )
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertIn("rate_language", scrubs)
        self.assertIn("internal_directive", scrubs)


# ---- Phase 8m+: budget-category-label scrub -----------------------------


class ScrubBudgetCategoryLabelsTests(TestCase):
    """The system has exactly TWO categories: fit ('in your budget') and
    near_fit ('close to your target'). Invented categories like 'NEARLY IN
    BUDGET' / 'slightly above budget' must be rewritten to the canonical
    near_fit phrase."""

    def test_strips_capitalized_invented_headers(self):
        for invented in [
            "NEARLY IN BUDGET",
            "NEARLY IN YOUR BUDGET",
            "SLIGHTLY ABOVE BUDGET",
            "SLIGHTLY ABOVE YOUR BUDGET",
            "ALMOST IN BUDGET",
            "JUST ABOVE BUDGET",
            "A BIT ABOVE BUDGET",
        ]:
            text = f"## {invented}\nThe Edge is here."
            cleaned, changed = scrub_budget_category_labels(text)
            self.assertTrue(changed, msg=f"expected scrub for: {invented!r}")
            for forbidden in ("nearly", "slightly above", "almost", "just above", "a bit above", "near "):
                # The header form must not survive in any casing.
                if forbidden in invented.lower():
                    self.assertNotIn(
                        forbidden,
                        cleaned.lower(),
                        msg=f"{forbidden!r} survived in {cleaned!r}",
                    )
            self.assertIn("close to your target", cleaned.lower())

    def test_strips_inline_invented_phrases(self):
        for inline in [
            "the Edge is nearly in budget",
            "the Edge is nearly in your budget",
            "the Edge is slightly above budget",
            "the Edge is slightly above your budget",
            "the Edge is almost in budget",
            "the Edge is just above budget",
            "the Edge is a bit above budget",
            "the Edge is near budget",
            "the Edge is near your budget",
        ]:
            cleaned, changed = scrub_budget_category_labels(inline)
            self.assertTrue(changed, msg=f"expected scrub for: {inline!r}")
            self.assertNotIn("nearly", cleaned.lower())
            self.assertNotIn("slightly above", cleaned.lower())
            self.assertNotIn("almost in", cleaned.lower())
            self.assertNotIn("just above", cleaned.lower())
            self.assertNotIn("a bit above", cleaned.lower())
            self.assertIn("close to your target", cleaned.lower())

    def test_strips_internal_annotation_leakage(self):
        # The per-line `_budget_fit=fit` annotation must never leak.
        text = "The Edge | _budget_fit=near_fit | est ~$517/mo (W.A.C.)"
        cleaned, changed = scrub_budget_category_labels(text)
        self.assertTrue(changed)
        self.assertNotIn("_budget_fit", cleaned)
        self.assertIn("$517/mo", cleaned)

    def test_clean_reply_unchanged(self):
        text = (
            "The Escape fits your budget at $475/mo (W.A.C.), "
            "and the Edge is close to your target at $517/mo."
        )
        cleaned, changed = scrub_budget_category_labels(text)
        self.assertFalse(changed)
        self.assertEqual(cleaned, text)

    def test_only_near_fits_strips_in_budget_claim(self):
        # When matched set is all near_fits, "in your budget" / "within
        # your budget" / "fits your budget" are definitionally wrong and
        # must be rewritten to the canonical near_fit phrasing.
        text = "The Edge is in your budget at $517/mo."
        cleaned, changed = scrub_budget_category_labels(
            text, only_near_fits=True
        )
        self.assertTrue(changed)
        self.assertNotIn("in your budget", cleaned.lower())
        self.assertIn("close to your target", cleaned.lower())

    def test_only_near_fits_strips_within_your_budget(self):
        text = "Both vehicles fall within your budget."
        cleaned, changed = scrub_budget_category_labels(
            text, only_near_fits=True
        )
        self.assertTrue(changed)
        self.assertNotIn("within your budget", cleaned.lower())
        self.assertIn("close to your target", cleaned.lower())

    def test_mixed_pool_keeps_in_budget_claim(self):
        # When the matched set has BOTH fit and near_fit, the LLM may
        # legitimately say "the Escape is in your budget" about the fit
        # vehicle. Don't auto-rewrite in that case.
        text = "The Escape is in your budget at $475/mo."
        cleaned, changed = scrub_budget_category_labels(
            text, only_near_fits=False
        )
        self.assertFalse(changed)
        self.assertIn("in your budget", cleaned)


class FormatVehicleBlockEmitsBudgetFitLabelTests(TestCase):
    """Phase 8m+: each vehicle line in budget-mode must end with the
    `_budget_fit=fit|near_fit` annotation so the LLM has explicit per-line
    guidance, and the inventory block must include the two-categories
    INTERNAL DIRECTIVE."""

    def test_budget_mode_appends_fit_label_per_vehicle(self):
        v_fit = _make_vehicle("LBL-FIT", price="20000")
        v_fit._estimated_payment = 380.0
        v_fit._budget_fit = "fit"
        v_fit._payment_delta = -120.0

        v_near = _make_vehicle("LBL-NEAR", price="27500")
        v_near._estimated_payment = 525.0
        v_near._budget_fit = "near_fit"
        v_near._payment_delta = 25.0

        block = _format_vehicle_block([v_fit, v_near], budget_mode=True)
        # Per-line annotation present.
        fit_line = [ln for ln in block.split("\n") if "LBL-FIT" in ln][0]
        near_line = [ln for ln in block.split("\n") if "LBL-NEAR" in ln][0]
        self.assertIn("_budget_fit=fit", fit_line)
        self.assertIn("_budget_fit=near_fit", near_line)
        # Two-categories directive present.
        self.assertIn("ONLY THESE TWO CATEGORIES ARE ALLOWED", block)
        self.assertIn("nearly in budget", block)  # listed as banned

    def test_non_budget_mode_does_not_append_label_to_vehicle_line(self):
        # Outside budget mode there is no classification, so no label is
        # appended to the per-vehicle line. (The directive header uses the
        # token literally as documentation; that's fine because it is
        # explicitly tagged as INTERNAL DIRECTIVE — do NOT echo.)
        v = _make_vehicle("LBL-NB", price="20000")
        block = _format_vehicle_block([v], budget_mode=False)
        line = [ln for ln in block.split("\n") if "LBL-NB" in ln][0]
        self.assertNotIn("_budget_fit", line)


class ChatEngineCategoryLabelScrubTests(TestCase):
    """End-to-end: a model that emits invented category headers /
    'within your budget' on near-fits / etc. must produce sanitized
    customer-facing copy."""

    def _setup_engine_with_near_fit_only_match(self, model_reply: str):
        """Turn 1 has $500/mo target and a $26,000 Edge near-fit (no fits).
        At $0 down, 60mo, $26,000 estimates to ~$556/mo — delta $56 over
        target, inside the $75 near-fit tolerance. Returns
        (engine, session, vehicle, provider) ready for turn 1."""
        session = ChatSession.objects.create()
        v = Vehicle.objects.create(
            stock_number="CAT-1",
            year=2025,
            make="Ford",
            model="Edge",
            body_style="suv",
            condition="new",
            mileage=10,
            price=Decimal("26000"),
        )
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "payment_estimate",
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "suv",
                    }
                ),
                model_reply,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        return engine, session, v, provider

    def test_strips_nearly_in_budget(self):
        bad = (
            "## NEARLY IN BUDGET\n"
            "The Edge is nearly in budget at $525/mo (W.A.C.)."
        )
        engine, _, _, _ = self._setup_engine_with_near_fit_only_match(bad)
        result = engine.handle_user_message("Show me an SUV around $500/mo")
        body = result.assistant_message.content.lower()
        self.assertNotIn("nearly", body)
        self.assertNotIn("nearly in budget", body)
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertIn("category_label", scrubs)

    def test_strips_slightly_above_budget(self):
        bad = (
            "## SLIGHTLY ABOVE BUDGET\n"
            "The Edge is slightly above your budget at $525/mo (W.A.C.)."
        )
        engine, _, _, _ = self._setup_engine_with_near_fit_only_match(bad)
        result = engine.handle_user_message("Show me an SUV around $500/mo")
        body = result.assistant_message.content.lower()
        self.assertNotIn("slightly above", body)
        self.assertNotIn("slightly above budget", body)
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertIn("category_label", scrubs)

    def test_strips_within_budget_when_only_near_fits(self):
        # When the matched set is all near-fits, "within your budget" is
        # definitionally wrong and must be rewritten.
        bad = "The Edge falls within your budget at $525/mo (W.A.C.)."
        engine, _, _, _ = self._setup_engine_with_near_fit_only_match(bad)
        result = engine.handle_user_message("Show me an SUV around $500/mo")
        body = result.assistant_message.content.lower()
        self.assertNotIn("within your budget", body)
        self.assertNotIn("in your budget", body)
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertIn("category_label", scrubs)

    def test_clean_near_fit_reply_does_not_set_category_flag(self):
        good = (
            "The Edge is close to your $500/month target at $525/mo "
            "(W.A.C.). Want me to line one up?"
        )
        engine, _, _, _ = self._setup_engine_with_near_fit_only_match(good)
        result = engine.handle_user_message("Show me an SUV around $500/mo")
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertNotIn("category_label", scrubs)


# ---- Phase 8m+: external-value pre-LLM guard --------------------------


class DetectExternalValueInquiryTests(TestCase):
    """Phase 8m+: questions about Blue Book / KBB / NADA / trade-in dollar
    values must short-circuit before any LLM call so no fabricated number
    reaches the customer."""

    def test_blue_book_question_detected(self):
        for phrase in [
            "What's the Blue Book value of a 2018 Camry?",
            "What's blue book on this F-150?",
            "Looking for the Blue Book value",
            "kbb value for my truck",
            "Show me the KBB on a 2020 Edge",
            "What does NADA say my Tacoma is worth?",
            "edmunds true market value",
            "TrueCar pricing on the Bronco",
            "carfax history-based value",
            "what's BBV on a 2019 Accord",
        ]:
            self.assertTrue(
                detect_external_value_inquiry(phrase),
                msg=f"expected to detect: {phrase!r}",
            )

    def test_trade_in_value_question_detected(self):
        for phrase in [
            "What's my car worth as a trade-in?",
            "What's my truck worth?",
            "What is my SUV worth?",
            "Whats my car worth?",  # apostrophe-less typo
            "Trade-in value for my 2018 Accord?",
            "What's my trade-in worth?",
            "How much can I get for my car?",
            "How much will I get for my truck?",
            "What would I get for my trade?",
            "Appraise my vehicle",
            "What's the value of my vehicle?",
        ]:
            self.assertTrue(
                detect_external_value_inquiry(phrase),
                msg=f"expected to detect: {phrase!r}",
            )

    def test_general_trade_in_intent_not_flagged(self):
        # The customer can express interest in trading in WITHOUT asking
        # for a specific dollar value. Those workflow signals should NOT
        # trigger the external-value guard — they're handled by intent
        # extraction (`trade_in: True`) and the regular LLM path.
        for phrase in [
            "I want to trade in my old car",
            "I'm planning to trade my truck in",
            "I'd like to trade in my SUV when I buy",
        ]:
            self.assertFalse(
                detect_external_value_inquiry(phrase),
                msg=f"should NOT flag (workflow signal): {phrase!r}",
            )

    def test_normal_questions_not_flagged(self):
        for phrase in [
            "Show me trucks under $30k",
            "What can I get for $500/month?",
            "Tell me about the F-150",
            "Do you have any used SUVs?",
        ]:
            self.assertFalse(
                detect_external_value_inquiry(phrase),
                msg=f"should NOT flag: {phrase!r}",
            )


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEngineExternalValueGuardTests(TestCase):
    """End-to-end: BBV/KBB/trade-in-value questions short-circuit pre-LLM
    and never expose a fabricated dollar value to the customer."""

    def _setup(self, replies=None):
        session = ChatSession.objects.create()
        v = _make_vehicle("EV-1", price="55000")
        provider = MockLLMProvider(replies=replies or ["unused"])
        engine = ChatEngine(session=session, provider=provider)
        return engine, session, v, provider

    def test_blue_book_question_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message(
            "What's the Blue Book value of a 2018 Camry?"
        )
        self.assertEqual(
            result.assistant_message.content, _render(EXTERNAL_VALUE_RESPONSE)
        )
        # No LLM call.
        self.assertEqual(provider.calls, [])
        # Audit flag.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "external_value_inquiry",
        )

    def test_trade_in_value_question_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message("What's my trade-in worth?")
        self.assertEqual(
            result.assistant_message.content, _render(EXTERNAL_VALUE_RESPONSE)
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "external_value_inquiry",
        )

    def test_canned_response_contains_no_dollar_amounts(self):
        # The canned response must not name a specific dollar figure for
        # the customer's vehicle — that's the whole point of the guard.
        import re as _re

        # No $/numeric figure outside of the disclaimer wording.
        self.assertFalse(
            _re.search(r"\$\s*\d", EXTERNAL_VALUE_RESPONSE),
            msg=f"canned response leaks a dollar figure: {EXTERNAL_VALUE_RESPONSE!r}",
        )

    def test_canned_response_acknowledges_lack_of_data(self):
        # The response must be honest that the system doesn't have the
        # value, and offer the dealer-advisor escape hatch.
        body = EXTERNAL_VALUE_RESPONSE.lower()
        self.assertIn("don't have", body)
        self.assertIn("advisor", body)

    def test_inventory_still_attached_on_external_value_short_circuit(self):
        # Mirror the rate-inquiry guard's behavior: even though we refuse
        # the BBV question, the customer should still see real options
        # alongside the refusal.
        engine, _, v, _ = self._setup()
        result = engine.handle_user_message(
            "What's the KBB on a 2018 Camry?"
        )
        # Inventory search ran on the user text — the F-150 we created is
        # not a Camry but search_vehicles fuzzy-matches on year/keywords
        # and may or may not return it. The contract is: matched_vehicles
        # is set (possibly empty) and never errors.
        self.assertIsNotNone(result.matched_vehicles)


class SystemPromptContainsExternalDataRulesTests(TestCase):
    """Lock the SYSTEM_PROMPT contract that bans Blue Book / KBB
    fabrication, down-payment / term assumptions, and the 'best deal'
    arbitrary-pick anti-pattern."""

    def test_prompt_bans_blue_book_kbb_fabrication(self):
        prompt = SYSTEM_PROMPT.lower()
        self.assertIn("blue book", prompt)
        self.assertIn("kbb", prompt)
        # Must explicitly say "never" / "do not" near it.
        self.assertRegex(SYSTEM_PROMPT, r"(?is)NEVER\s+quote\s+Blue\s+Book")

    def test_prompt_bans_trade_in_value_fabrication(self):
        prompt = SYSTEM_PROMPT.lower()
        self.assertIn("never fabricate trade-in", prompt)

    def test_prompt_bans_assumed_down_payment_framing(self):
        # The rule is: never describe an assumed default ($0 down) as if
        # the customer chose it.
        prompt = SYSTEM_PROMPT.lower()
        self.assertIn("never assume a down payment", prompt)
        self.assertIn("assuming $0 down", prompt)

    def test_prompt_requires_2_3_options_for_best_deal(self):
        prompt = SYSTEM_PROMPT.lower()
        # "Best deal" / "best option" / "best price" with explicit 2-3 rule.
        self.assertIn("best deal", prompt)
        self.assertIn("2-3", prompt)
        # And the anti-pattern of arbitrary single pick is named.
        self.assertRegex(prompt, r"(?is)do\s+not\s+pick\s+a\s+single\s+vehicle")


class BestDealReturnsMultipleOptionsTests(TestCase):
    """Phase 8m+: when the customer asks 'what's the best deal?', the
    backend must surface multiple matched_vehicles (not a single arbitrary
    pick) so the LLM has 2-3 options to present."""

    def test_best_deal_query_returns_multiple_matched_vehicles(self):
        # Phase 8s cap: 1 fit + 2 near_fits = 3 total. Seed one fit at
        # $18k (well within budget) and two near_fits at $26k / $27.5k
        # so the cap fills out and the "best deal" query genuinely
        # produces a multi-option spread for the LLM.
        Vehicle.objects.create(
            stock_number="BD-1", year=2024, make="Ford", model="Escape",
            body_style="suv", condition="new", price=Decimal("18000"),
        )
        Vehicle.objects.create(
            stock_number="BD-2", year=2023, make="Ford", model="Escape",
            body_style="suv", condition="used", price=Decimal("26000"),
        )
        Vehicle.objects.create(
            stock_number="BD-3", year=2024, make="Ford", model="Bronco Sport",
            body_style="suv", condition="new", price=Decimal("27500"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply(
                    {
                        "intent": "vehicle_search",
                        "target_monthly_payment": 500,
                        "term_months": 60,
                        "vehicle_type": "suv",
                    }
                ),
                "Here are three good options.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "What's your best deal on an SUV around $500/mo?"
        )
        # The "best deal" query must surface multiple candidates so the
        # LLM has 2-3 options to present per the system-prompt rule.
        self.assertGreaterEqual(
            len(result.matched_vehicles),
            2,
            f"expected ≥2 matched for 'best deal' query, got {len(result.matched_vehicles)}",
        )


# ---- Phase 8m+: discovery-mode gate ------------------------------------


class ShouldEnterDiscoveryModeTests(TestCase):
    """Pure-function tests for the discovery-mode gate. The gate fires when
    the customer has expressed vehicle interest but given NO budget signal
    (no monthly target, no price range, no specific model lock) and the
    request is broad."""

    def _hits(self, text):
        from dealer_ai.services.intent_parser import regex_extract
        return regex_extract(text)

    def test_convertible_with_no_budget_enters_discovery(self):
        text = "I am looking for a convertible"
        self.assertTrue(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_convertible_with_monthly_target_does_not_enter_discovery(self):
        text = "I want a convertible under $500/month"
        self.assertFalse(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_truck_only_with_no_budget_enters_discovery(self):
        text = "I want a truck"
        self.assertTrue(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_suv_only_with_no_budget_enters_discovery(self):
        text = "Show me an SUV"
        self.assertTrue(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_specific_model_does_not_enter_discovery(self):
        text = "Tell me about the F-150"
        self.assertFalse(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_plural_model_does_not_enter_discovery(self):
        # "F-150s" must be picked up as model and bypass discovery.
        text = "Show me F-150s"
        self.assertFalse(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_dollar_price_range_does_not_enter_discovery(self):
        text = "Show me trucks under $30k"
        self.assertFalse(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_bare_kilo_price_does_not_enter_discovery(self):
        text = "Used trucks under 30k for my family"
        self.assertFalse(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )

    def test_prior_budget_in_profile_bypasses_discovery(self):
        # Follow-up turn after budget was established earlier.
        text = "Show me SUVs"
        profile = {"target_monthly_payment": 500, "term_months": 60}
        self.assertFalse(
            _should_enter_discovery_mode(text, profile, self._hits(text))
        )

    def test_drop_top_synonym_enters_discovery(self):
        text = "Looking for a drop-top"
        self.assertTrue(
            _should_enter_discovery_mode(text, {}, self._hits(text))
        )


class FormatDiscoveryBlockTests(TestCase):
    def test_block_says_do_not_recommend(self):
        block = _format_discovery_block("I want a truck", {"vehicle_type": "truck"})
        self.assertIn("DISCOVERY MODE", block)
        self.assertIn("DO NOT list vehicles", block)
        self.assertIn("1-2", block)

    def test_convertible_block_acknowledges_no_inventory(self):
        block = _format_discovery_block("I want a convertible", {})
        self.assertIn("convertible", block.lower())
        self.assertIn("do not currently have", block.lower())
        self.assertIn("Mustang", block)
        # Still asks clarifying questions before recommending.
        self.assertIn("clarifying question", block.lower())


class ChatEngineDiscoveryModeTests(TestCase):
    """End-to-end: a broad first-turn query (just a body type or
    'convertible') must NOT return vehicles — it must ask a question."""

    def _engine(self, mock_clarifying_reply: str):
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                # parse_intent JSON pass — return empty extras so only
                # regex_extract drives merging.
                json_reply({}),
                mock_clarifying_reply,
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        return engine, session, provider

    def test_convertible_first_turn_returns_no_vehicles(self):
        # Seed some vehicles to prove they would normally be returned —
        # the discovery gate must block them anyway.
        Vehicle.objects.create(
            stock_number="DM-1", year=2025, make="Ford", model="Mustang",
            body_style="car", condition="new", price=Decimal("36000"),
        )
        Vehicle.objects.create(
            stock_number="DM-2", year=2024, make="Ford", model="Bronco",
            body_style="suv", condition="new", price=Decimal("42000"),
        )
        engine, _, _ = self._engine(
            "We don't have any convertibles on the lot right now. "
            "What's your monthly target, and are you open to new or used?"
        )
        result = engine.handle_user_message("I am looking for a convertible")

        self.assertEqual(
            list(result.matched_vehicles),
            [],
            "discovery mode must not return any vehicles",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("mode"),
            "discovery",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("matched_count"), 0
        )
        self.assertEqual(
            list(result.assistant_message.matched_vehicles.all()), []
        )

    def test_truck_only_first_turn_returns_no_vehicles(self):
        Vehicle.objects.create(
            stock_number="DM-3", year=2025, make="Ford", model="F-150",
            body_style="truck", condition="new", price=Decimal("55000"),
        )
        engine, _, _ = self._engine(
            "Got it — what's your monthly target, and are you open to new or used?"
        )
        result = engine.handle_user_message("I want a truck")

        self.assertEqual(list(result.matched_vehicles), [])
        self.assertEqual(
            result.assistant_message.metadata.get("mode"), "discovery"
        )

    def test_convertible_with_monthly_target_proceeds_normally(self):
        # Once the customer gives a monthly target, the gate is bypassed
        # and the engine proceeds into the budget-mode path. Even though
        # there are no convertibles in inventory, the engine should not
        # be in discovery mode for this turn.
        Vehicle.objects.create(
            stock_number="DM-4", year=2025, make="Ford", model="Mustang",
            body_style="car", condition="new", price=Decimal("28000"),
        )
        engine, _, _ = self._engine(
            "Here are some sporty options at your $500/month target."
        )
        result = engine.handle_user_message(
            "I want a convertible under $500/month with $3k down"
        )

        # NOT in discovery mode — the customer gave a budget.
        self.assertNotEqual(
            result.assistant_message.metadata.get("mode"), "discovery"
        )

    def test_specific_model_first_turn_proceeds_normally(self):
        # A specific-model request bypasses discovery — the customer
        # wants info on that vehicle, not a budget chat.
        Vehicle.objects.create(
            stock_number="DM-5", year=2025, make="Ford", model="F-150",
            body_style="truck", condition="new", price=Decimal("55000"),
        )
        engine, _, _ = self._engine(
            "The F-150 is a great truck. Here's what we have."
        )
        result = engine.handle_user_message("Tell me about the F-150")

        self.assertNotEqual(
            result.assistant_message.metadata.get("mode"), "discovery"
        )
        # And matched_vehicles should be populated.
        self.assertGreater(len(result.matched_vehicles), 0)

    def test_followup_turn_after_budget_set_does_not_re_enter_discovery(self):
        # Turn 1: customer says "I want a truck" → discovery, asks for budget.
        # Turn 2: customer says "$500/mo with $3k down" → must EXIT discovery.
        Vehicle.objects.create(
            stock_number="DM-6", year=2025, make="Ford", model="Maverick",
            body_style="truck", condition="new", price=Decimal("23000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),  # turn 1 intent
                "What's your monthly target?",  # turn 1 reply
                json_reply({}),  # turn 2 intent
                "Here's a Maverick that fits.",  # turn 2 reply
            ]
        )
        engine = ChatEngine(session=session, provider=provider)

        turn1 = engine.handle_user_message("I want a truck")
        self.assertEqual(
            turn1.assistant_message.metadata.get("mode"), "discovery"
        )
        self.assertEqual(list(turn1.matched_vehicles), [])

        turn2 = engine.handle_user_message("$500/mo with $3k down")
        self.assertNotEqual(
            turn2.assistant_message.metadata.get("mode"), "discovery"
        )
        # Now matched_vehicles should be populated.
        self.assertGreater(len(turn2.matched_vehicles), 0)


# ---- Phase 8m+: default-assumption scrub --------------------------------


class ScrubDefaultAssumptionLanguageTests(TestCase):
    """The non-budget inventory block computes payment estimates at engine
    defaults ($0 down, 72-month term) because the customer hasn't given
    those yet. The LLM must NOT narrate those defaults as customer
    choices. This scrub is the safety net for when it does."""

    def test_strips_assuming_no_down_payment(self):
        text = "The Ranger comes in at $715/mo, assuming no down payment."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("assuming no down payment", cleaned.lower())
        self.assertIn("$715/mo", cleaned)

    def test_strips_assuming_no_money_down(self):
        text = "The Edge sits at $556/mo assuming no money down."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("assuming no money down", cleaned.lower())
        self.assertIn("$556/mo", cleaned)

    def test_strips_with_no_money_down(self):
        text = "Estimated $715/mo with no money down over 72 months."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("with no money down", cleaned.lower())
        self.assertNotIn("no money down", cleaned.lower())
        self.assertIn("$715/mo", cleaned)
        # Legitimate "over 72 months" is preserved.
        self.assertIn("72 months", cleaned)

    def test_strips_with_no_down_payment(self):
        text = "The Bronco runs $715/mo with no down payment."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("with no down payment", cleaned.lower())
        self.assertIn("$715/mo", cleaned)

    def test_strips_assuming_72_months(self):
        text = "The Bronco is around $715/mo assuming 72 months."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("assuming 72 months", cleaned.lower())
        self.assertIn("$715/mo", cleaned)

    def test_strips_assuming_72_month_term(self):
        text = "The F-150 runs $725/mo, assuming a 72-month term."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("assuming a 72-month term", cleaned.lower())
        self.assertNotIn("72-month term", cleaned.lower())
        self.assertIn("$725/mo", cleaned)

    def test_strips_default_72_month_term(self):
        text = (
            "At the default 72-month term, you would pay around $715/mo."
        )
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("default 72-month term", cleaned.lower())
        self.assertNotIn("72-month term", cleaned.lower())
        self.assertIn("$715/mo", cleaned)

    def test_strips_default_term_of_72_months(self):
        text = "The default term of 72 months puts the payment at $715/mo."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertNotIn("default term", cleaned.lower())
        self.assertIn("$715/mo", cleaned)

    def test_clean_reply_unchanged(self):
        text = (
            "Estimated $715/mo for 72 months (W.A.C.). A Dealer OS "
            "advisor can pull a real quote when you're ready."
        )
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertFalse(changed)
        self.assertEqual(cleaned, text)

    def test_legitimate_customer_specified_down_preserved(self):
        # When the customer DID say their down payment, the resulting
        # phrasing isn't an "assuming default" pattern and must survive.
        text = "You said $3k down, so estimated $556/mo for 60 months."
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertFalse(changed)
        self.assertIn("$3k down", cleaned)

    def test_acceptable_assuming_zero_down_preserved(self):
        # "assuming $0 down for this estimate" is the explicit
        # assumption-framing the system prompt allows when the customer
        # hasn't specified down. It must NOT be scrubbed.
        text = (
            "Assuming $0 down for this estimate, the payment is $556/mo."
        )
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertFalse(changed)
        self.assertIn("$0 down for this estimate", cleaned)

    def test_payment_numbers_preserved_for_consistency_check(self):
        # The scrub runs BEFORE check_payment_consistency. Payment
        # numbers must survive so the consistency check still works.
        text = (
            "The Ranger at $715/mo, assuming no down payment over the "
            "default 72-month term."
        )
        cleaned, changed = scrub_default_assumption_language(text)
        self.assertTrue(changed)
        self.assertIn("$715/mo", cleaned)


class FormatVehicleBlockNoBudgetGuidanceIsInternalTests(TestCase):
    """Phase 8m+: the non-budget inventory block must label its
    default-assumption guidance as INTERNAL DIRECTIVE so the LLM is
    explicitly told not to echo it (the per-line '$X/mo for 72 months
    (W.A.C.)' stays — it's customer-readable math, not a directive)."""

    def test_non_budget_guidance_is_marked_internal_directive(self):
        v = _make_vehicle("ND-1", price="26995")
        block = _format_vehicle_block([v], budget_mode=False)
        # Block must contain the INTERNAL DIRECTIVE marker for the
        # default-assumption guidance (so scrubs + audits can find it).
        self.assertIn("INTERNAL DIRECTIVE", block)
        # And the explicit do-not-echo phrasing should be present.
        self.assertRegex(block, r"(?i)do\s+NOT\s+echo")
        # The banned customer-facing phrases must be named in the
        # directive so the LLM knows them.
        block_lower = block.lower()
        self.assertIn("assuming no down payment", block_lower)
        self.assertIn("with no money down", block_lower)
        self.assertIn("default 72-month term", block_lower)
        self.assertIn("assuming 72 months", block_lower)

    def test_non_budget_per_line_keeps_legit_term_disclosure(self):
        # The per-vehicle line still shows "for 72 months (W.A.C. — with
        # approved credit)" — that's customer-facing math, not narrative,
        # and is NOT in the scrub patterns.
        v = _make_vehicle("ND-2", price="26995")
        block = _format_vehicle_block([v], budget_mode=False)
        per_line = [ln for ln in block.split("\n") if "ND-2" in ln][0]
        self.assertIn("72 months", per_line)
        self.assertIn("W.A.C.", per_line)


class ChatEngineDefaultAssumptionScrubTests(TestCase):
    """End-to-end: a non-budget reply that leaks 'assuming no down
    payment' / 'with no money down' / 'default 72-month term' must be
    sanitized, the audit flag set, and the matched_vehicles still
    attached."""

    def test_assuming_no_down_payment_is_scrubbed_and_flagged(self):
        v = Vehicle.objects.create(
            stock_number="DA-1", year=2025, make="Ford", model="Bronco",
            body_style="suv", condition="new", mileage=10,
            price=Decimal("38995"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search", "model": "Bronco"}),
                "We have a 2025 Bronco at $715/mo, assuming no down "
                "payment over the default 72-month term.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I drove by and saw a yellow bronco, how much is it?"
        )
        body = result.assistant_message.content.lower()

        self.assertNotIn("assuming no down payment", body)
        self.assertNotIn("default 72-month term", body)
        self.assertNotIn("72-month term", body)
        # Payment number survives the scrub.
        self.assertIn("$715/mo", result.assistant_message.content)
        # Audit signal.
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertIn("default_assumption", scrubs)
        # Vehicle still attached.
        self.assertIn(
            v, result.assistant_message.matched_vehicles.all()
        )

    def test_with_no_money_down_is_scrubbed(self):
        Vehicle.objects.create(
            stock_number="DA-2", year=2025, make="Ford", model="Ranger",
            body_style="truck", condition="new", price=Decimal("48000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search", "model": "Ranger"}),
                "The Ranger comes in at $880/mo with no money down.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me about the Ranger")
        body = result.assistant_message.content.lower()

        self.assertNotIn("with no money down", body)
        self.assertNotIn("no money down", body)
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertIn("default_assumption", scrubs)

    def test_clean_non_budget_reply_does_not_set_default_flag(self):
        Vehicle.objects.create(
            stock_number="DA-3", year=2025, make="Ford", model="Bronco",
            body_style="suv", condition="new", price=Decimal("38995"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search", "model": "Bronco"}),
                "We have a Bronco at $715/mo for 72 months (W.A.C.). "
                "An advisor can pull a real quote when you're ready.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me about the Bronco")
        scrubs = result.assistant_message.metadata.get("scrubs") or []
        self.assertNotIn("default_assumption", scrubs)


# ---- Phase 8m+: live-agent / handoff guard ------------------------------


class DetectHandoffRequestTests(TestCase):
    """Phase 8m+: requests to talk to a real person / advisor / sales rep
    must short-circuit before the LLM so it can't invent advisor names
    or simulate transfer mechanics."""

    def test_canonical_phrasings_detected(self):
        for phrase in [
            "I want to talk to a live person",
            "Can I speak to a salesperson?",
            "Can I talk to a salesperson",
            "I need a human",
            "I need a human being",
            "Can I speak to an advisor",
            "Connect me with a salesperson",
            "I want a live agent",
            "Talk to a Dealer OS advisor please",
            "I'd like to speak with someone",
            "Can I chat with a real person",
            "Have someone call me",
            "Please call me",
            "Email me",
            "Text me",
            "Can I get an advisor on the phone",
            "Book an appointment",
            "Schedule a test drive",
            "I want to schedule a call",
            "Live agent please",
            "Live person",
        ]:
            self.assertTrue(
                detect_handoff_request(phrase),
                msg=f"expected detect: {phrase!r}",
            )

    def test_identity_question_does_not_fire(self):
        # "Are you a person?" is an identity challenge (Failure 3 — out
        # of scope for this fix). It must NOT trigger the handoff guard.
        for phrase in [
            "Are you a person?",
            "Are you real?",
            "Is this a bot?",
            "Am I talking to AI?",
        ]:
            self.assertFalse(
                detect_handoff_request(phrase),
                msg=f"identity check should NOT fire: {phrase!r}",
            )

    def test_normal_questions_do_not_fire(self):
        for phrase in [
            "Show me F-150s",
            "Can I afford a Bronco?",
            "I need a truck",
            "I need someone to help me find a truck",
            "Tell me about the Mustang",
            "What's the price on the Ranger?",
            "How much down payment do I need?",
        ]:
            self.assertFalse(
                detect_handoff_request(phrase),
                msg=f"normal query should NOT fire: {phrase!r}",
            )


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class HandoffResponseShapeTests(TestCase):
    """The canned HANDOFF_RESPONSE must be honest, ask for the three
    contact-info pieces, and contain NO transfer-mechanic language or
    invented advisor names."""

    def test_response_offers_dealer_advisor_connection(self):
        # Phase 8o: identity disclosure moved to the dedicated
        # IDENTITY_RESPONSE. The handoff response is now the simpler
        # advisor-connection text.
        body = _render(HANDOFF_RESPONSE).lower()
        self.assertIn("dealer os", body)
        self.assertIn("advisor", body)

    def test_response_asks_for_name_phone_and_time(self):
        # Phase 8o: simplified to ask for name, phone, and a good time.
        # Email is no longer in the handoff response (the AI text is
        # short by design); advisors can collect email at follow-up.
        body = HANDOFF_RESPONSE.lower()
        self.assertIn("name", body)
        self.assertIn("phone", body)
        self.assertRegex(body, r"\btime\b")

    def test_response_offers_to_pass_along_to_advisor(self):
        body = HANDOFF_RESPONSE.lower()
        self.assertIn("advisor", body)

    def test_response_contains_no_transfer_mechanics(self):
        # The original bug had the LLM saying "transferring you" /
        # "connecting you" / "stay on the line". The canned response
        # must not have any of those — the AI doesn't transfer calls.
        body = HANDOFF_RESPONSE.lower()
        for forbidden in [
            "transferring",
            "transfer you",
            "connecting you",
            "putting you through",
            "stay on the line",
            "hold on",
            "please hold",
            "one moment",
            "i'll connect",
            "let me connect",
        ]:
            self.assertNotIn(
                forbidden,
                body,
                msg=f"transfer mechanic leaked: {forbidden!r}",
            )

    def test_response_contains_no_invented_advisor_names(self):
        # The original bug invented "Sarah". The canned response must
        # not have any common first-name pattern.
        for fake_name in [
            "Sarah",
            "Mike",
            "Mark",
            "John",
            "Jessica",
            "Jennifer",
            "Lisa",
            "Tom",
            "Tony",
            "Rachel",
            "Dave",
            "Steve",
        ]:
            self.assertNotIn(
                fake_name,
                HANDOFF_RESPONSE,
                msg=f"invented name leaked: {fake_name!r}",
            )

    def test_response_does_not_promise_synchronous_handoff(self):
        # The AI is asynchronous lead-capture, not real-time transfer.
        # Phrasings like "right now" / "immediately" / "in a minute"
        # would imply real-time which we can't deliver.
        body = HANDOFF_RESPONSE.lower()
        self.assertNotIn("right now", body)
        self.assertNotIn("immediately", body)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEngineHandoffGuardTests(TestCase):
    """End-to-end: handoff requests short-circuit pre-LLM, return the
    canned response, never invoke the model, and surface
    metadata.flag = 'salesperson_handoff' for the dashboard."""

    def _setup(self):
        session = ChatSession.objects.create()
        # Seed an irrelevant vehicle to confirm matched_vehicles stays
        # empty on handoff (the customer asked for a human, not browsing).
        v = _make_vehicle("HO-1", price="55000")
        provider = MockLLMProvider(replies=["unused — guard short-circuits"])
        engine = ChatEngine(session=session, provider=provider)
        return engine, session, v, provider

    def test_live_person_request_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message(
            "I want to talk to a live person"
        )
        self.assertEqual(
            result.assistant_message.content, _render(HANDOFF_RESPONSE)
        )
        self.assertEqual(provider.calls, [], "LLM must not be invoked")
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "handoff_request",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("provider"), "guard"
        )

    def test_speak_to_salesperson_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message(
            "Can I speak to a salesperson?"
        )
        self.assertEqual(
            result.assistant_message.content, _render(HANDOFF_RESPONSE)
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "handoff_request",
        )

    def test_handoff_response_has_no_fake_transfer_language(self):
        engine, _, _, _ = self._setup()
        result = engine.handle_user_message(
            "Connect me with a salesperson"
        )
        body = result.assistant_message.content.lower()
        for forbidden in [
            "transferring",
            "transfer you",
            "connecting you",
            "putting you through",
            "stay on the line",
            "please hold",
        ]:
            self.assertNotIn(
                forbidden,
                body,
                msg=f"transfer mechanic in reply: {forbidden!r}",
            )

    def test_handoff_response_has_no_invented_advisor_names(self):
        engine, _, _, _ = self._setup()
        result = engine.handle_user_message(
            "I need to talk to a real advisor"
        )
        body = result.assistant_message.content
        for fake_name in [
            "Sarah",
            "Mike",
            "Mark",
            "John",
            "Jessica",
            "Tom",
            "Steve",
            "Dave",
        ]:
            self.assertNotIn(
                fake_name,
                body,
                msg=f"invented name in reply: {fake_name!r}",
            )

    def test_handoff_does_not_attach_inventory(self):
        # The customer asked for a human, not a vehicle pitch. Reply
        # must focus the customer on providing contact info — no
        # inventory cards.
        engine, _, _, _ = self._setup()
        result = engine.handle_user_message("Can I speak to an advisor?")
        self.assertEqual(list(result.matched_vehicles), [])
        self.assertEqual(
            list(result.assistant_message.matched_vehicles.all()), []
        )
        self.assertEqual(
            result.assistant_message.metadata.get("matched_count"), 0
        )

    def test_handoff_short_circuits_before_intent_extraction(self):
        # Mirror of the rate-inquiry / external-value short-circuit
        # pattern: provider is never called, so intent extraction (which
        # uses the provider) never runs.
        engine, _, _, provider = self._setup()
        engine.handle_user_message("Have someone call me")
        self.assertEqual(provider.calls, [])

    def test_handoff_does_not_simulate_transfer(self):
        # Comprehensive transfer-mechanic check across multiple handoff
        # phrasings. Each iteration creates a fresh session (unique
        # stock numbers per call to avoid the single-DB UNIQUE constraint).
        phrases = [
            "I want to talk to a live person",
            "Connect me with a salesperson",
            "Have someone call me",
            "Schedule a call",
        ]
        for i, phrase in enumerate(phrases):
            session = ChatSession.objects.create()
            Vehicle.objects.create(
                stock_number=f"HO-LOOP-{i}",
                year=2025, make="Ford", model="F-150",
                body_style="truck", condition="new",
                price=Decimal("55000"),
            )
            provider = MockLLMProvider(replies=["unused"])
            engine = ChatEngine(session=session, provider=provider)
            result = engine.handle_user_message(phrase)
            body = result.assistant_message.content.lower()
            # No real-time / synchronous mechanics.
            self.assertNotIn("right now", body)
            self.assertNotIn("immediately", body)
            self.assertNotIn("one moment", body)
            self.assertNotIn("hold on", body)


# ---- Phase 8n: conversation control layer ----------------------------


def _seed_three_suvs(price_offset=0):
    """Helper to seed three SUVs for ordinal-reference tests."""
    v1 = Vehicle.objects.create(
        stock_number=f"P8N-V1-{price_offset}",
        year=2024, make="Ford", model="Bronco Sport",
        trim="Outer Banks", body_style="suv", condition="new",
        mileage=10, price=Decimal("38000") + price_offset,
        exterior_color="Cyber Orange",
        image_url="https://example.com/bronco-sport.jpg",
    )
    v2 = Vehicle.objects.create(
        stock_number=f"P8N-V2-{price_offset}",
        year=2023, make="Ford", model="Edge", trim="Titanium",
        body_style="suv", condition="used", mileage=22000,
        price=Decimal("31000") + price_offset,
        exterior_color="Iconic Silver",
        image_url="https://example.com/edge.jpg",
    )
    v3 = Vehicle.objects.create(
        stock_number=f"P8N-V3-{price_offset}",
        year=2024, make="Ford", model="Explorer", trim="ST-Line",
        body_style="suv", condition="new", mileage=15,
        price=Decimal("47000") + price_offset,
        exterior_color="Star White",
        image_url="https://example.com/explorer.jpg",
    )
    return v1, v2, v3


class OrdinalReferenceSetsCurrentVehicleTests(TestCase):
    """User says 'first one' / 'show me more like the first one' →
    ChatSession.extracted_profile.current_vehicle_id is set to the
    first vehicle from the prior assistant turn's matched_vehicles."""

    def test_first_one_sets_current_vehicle(self):
        v1, v2, v3 = _seed_three_suvs()
        session = ChatSession.objects.create()

        # Simulate prior turn: assistant message with three matched
        # vehicles, in the order [v1, v2, v3].
        prior = ChatMessage.objects.create(
            session=session, role="assistant",
            content="Here are three SUVs that fit.",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v1, v2, v3])

        provider = MockLLMProvider(
            replies=[json_reply({}), "Got it — sticking with that one."]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("show me more like the first one")

        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("current_vehicle_id"), v1.id
        )
        self.assertEqual(
            session.extracted_profile.get("current_vehicle_stock"),
            v1.stock_number,
        )

    def test_second_one_sets_current_to_index_1(self):
        v1, v2, v3 = _seed_three_suvs(price_offset=Decimal("100"))
        session = ChatSession.objects.create()
        prior = ChatMessage.objects.create(
            session=session, role="assistant",
            content="Three options.",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v1, v2, v3])
        provider = MockLLMProvider(
            replies=[json_reply({}), "Got it — that one."]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("Tell me about the second one")
        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("current_vehicle_id"), v2.id
        )

    def test_ordinal_out_of_range_does_not_set_current(self):
        v1, _v2, _v3 = _seed_three_suvs(price_offset=Decimal("200"))
        session = ChatSession.objects.create()
        prior = ChatMessage.objects.create(
            session=session, role="assistant",
            content="One option.",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v1])
        provider = MockLLMProvider(
            replies=[json_reply({}), "OK."]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("Tell me about the third one")
        session.refresh_from_db()
        # Out of range → no current_vehicle set from ordinal.
        self.assertIsNone(
            session.extracted_profile.get("current_vehicle_id")
        )


class SingleMatchAutoSetsCurrentVehicleTests(TestCase):
    """When a turn surfaces exactly one vehicle, the engine pins
    current_vehicle to it so the next turn can resolve 'it'."""

    def test_single_match_pins_current_vehicle(self):
        v = Vehicle.objects.create(
            stock_number="P8N-SOLO", year=2025, make="Ford",
            model="Mustang", trim="GT", body_style="car",
            condition="new", price=Decimal("48000"),
            image_url="https://example.com/mustang.jpg",
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search", "model": "Mustang"}),
                "Here's the Mustang GT — a great drive.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me a Mustang")
        # Sanity: only that one matched.
        self.assertEqual(len(result.matched_vehicles), 1)
        # Current vehicle pinned.
        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("current_vehicle_id"), v.id
        )


class PronounFollowupUsesCurrentVehicleTests(TestCase):
    """Follow-up 'mileage on it' / 'tell me more about it' must use
    the current_vehicle as the sole inventory entry — no broad
    keyword search that could surface an unrelated vehicle."""

    def test_mileage_on_it_uses_only_current_vehicle(self):
        v_current = Vehicle.objects.create(
            stock_number="P8N-CUR", year=2023, make="Ford",
            model="Bronco Sport", trim="Outer Banks", body_style="suv",
            condition="certified", mileage=12345,
            price=Decimal("38995"),
        )
        # Decoy that broad keyword search could otherwise surface.
        Vehicle.objects.create(
            stock_number="P8N-DECOY", year=2024, make="Ford",
            model="Edge", trim="Titanium", body_style="suv",
            condition="new", mileage=20, price=Decimal("42000"),
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v_current.id,
            "current_vehicle_stock": v_current.stock_number,
            "model": "Bronco Sport",
        }
        session.save()

        # Simulate a prior assistant turn surfacing v_current.
        prior = ChatMessage.objects.create(
            session=session, role="assistant",
            content="The Bronco Sport CPO is a great pick.",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v_current])

        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "It has 12,345 miles on the odometer.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("What's the mileage on it?")

        # matched_vehicles must contain ONLY the current vehicle.
        ids = [v.id for v in result.matched_vehicles]
        self.assertEqual(ids, [v_current.id])

    def test_does_not_have_awd_uses_current_vehicle(self):
        v_current = Vehicle.objects.create(
            stock_number="P8N-AWD", year=2024, make="Ford",
            model="Bronco Sport", trim="Big Bend", body_style="suv",
            condition="new", price=Decimal("36000"),
            drivetrain="AWD",
        )
        Vehicle.objects.create(
            stock_number="P8N-DECOY-2", year=2024, make="Ford",
            model="Maverick", body_style="truck", condition="new",
            price=Decimal("28000"),
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v_current.id,
            "current_vehicle_stock": v_current.stock_number,
        }
        session.save()
        prior = ChatMessage.objects.create(
            session=session, role="assistant", content="OK.",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v_current])
        provider = MockLLMProvider(
            replies=[json_reply({}), "Yes — it has AWD."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Does it have AWD?")
        ids = [v.id for v in result.matched_vehicles]
        self.assertEqual(ids, [v_current.id])

    def test_more_like_it_does_NOT_lock_to_single_vehicle(self):
        # "more like it" = expand scope, not single-vehicle Q&A.
        v_current = Vehicle.objects.create(
            stock_number="P8N-MLT", year=2024, make="Ford",
            model="Bronco Sport", body_style="suv", condition="new",
            price=Decimal("36000"),
        )
        # Sibling that broad search should be allowed to find.
        Vehicle.objects.create(
            stock_number="P8N-MLT2", year=2023, make="Ford",
            model="Bronco Sport", body_style="suv", condition="used",
            price=Decimal("32000"),
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v_current.id,
            "current_vehicle_stock": v_current.stock_number,
            "model": "Bronco Sport",
        }
        session.save()
        prior = ChatMessage.objects.create(
            session=session, role="assistant", content="One option.",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v_current])
        provider = MockLLMProvider(
            replies=[json_reply({}), "Here are similar Bronco Sports."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("show me more like it")
        # "more like" expands scope — match count > 1 is acceptable.
        # Critically, this is NOT followup_mode (which would lock to 1).
        # Allow >=1 since broad search is the path here.
        self.assertGreaterEqual(len(result.matched_vehicles), 1)


class DetectImageRequestTests(TestCase):
    def test_canonical_phrasings_detected(self):
        for phrase in [
            "Do you have pictures?",
            "send me a picture",
            "any pics?",
            "can I see a photo",
            "photos please",
            "show me what it looks like",
            "any images of the Bronco?",
        ]:
            self.assertTrue(
                detect_image_request(phrase),
                msg=f"expected detect: {phrase!r}",
            )

    def test_non_image_phrases_not_detected(self):
        for phrase in [
            "Show me F-150s",
            "Tell me more about it",
            "What's the mileage?",
            "Can I afford it?",
        ]:
            self.assertFalse(
                detect_image_request(phrase),
                msg=f"should NOT fire: {phrase!r}",
            )


class ChatEngineImageRequestGuardTests(TestCase):
    def test_image_request_with_current_vehicle_returns_image_url_no_llm(self):
        v = Vehicle.objects.create(
            stock_number="P8N-IMG-1", year=2023, make="Ford",
            model="Bronco Sport", trim="Outer Banks", body_style="suv",
            condition="certified", price=Decimal("38995"),
            image_url="https://example.com/bronco-sport.jpg",
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v.id,
            "current_vehicle_stock": v.stock_number,
        }
        session.save()
        provider = MockLLMProvider(
            replies=["LLM SHOULD NOT BE CALLED"]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Do you have pictures?")
        body = result.assistant_message.content

        # No LLM call.
        self.assertEqual(provider.calls, [])
        # Vehicle name + stock + image_url present.
        self.assertIn("Bronco Sport", body)
        self.assertIn(v.stock_number, body)
        self.assertIn("https://example.com/bronco-sport.jpg", body)
        # Audit flag.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "image_request",
        )
        # Vehicle attached for the frontend cards.
        self.assertEqual(list(result.matched_vehicles), [v])

    def test_image_request_without_current_vehicle_asks_for_clarification(self):
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("send me a picture")

        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.content,
            IMAGE_REQUEST_NEEDS_VEHICLE_RESPONSE,
        )
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "image_request_needs_vehicle",
        )
        self.assertEqual(list(result.matched_vehicles), [])

    def test_image_request_with_ordinal_resolves_then_returns_url(self):
        # User says "send me a picture of the first one" — ordinal
        # resolves to prior turn's matched_vehicles[0], guard returns
        # the image_url for that vehicle.
        v1, v2, v3 = _seed_three_suvs(price_offset=Decimal("300"))
        session = ChatSession.objects.create()
        prior = ChatMessage.objects.create(
            session=session, role="assistant", content="three options",
            metadata={"provider": "test"},
        )
        prior.matched_vehicles.set([v1, v2, v3])
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "Send me a picture of the first one"
        )
        self.assertEqual(provider.calls, [])
        self.assertIn(v1.stock_number, result.assistant_message.content)
        self.assertIn(
            v1.image_url, result.assistant_message.content
        )

    def test_image_request_with_no_image_url_says_so(self):
        v = Vehicle.objects.create(
            stock_number="P8N-NOIMG", year=2024, make="Ford",
            model="Edge", body_style="suv", condition="new",
            price=Decimal("42000"),
            image_url="",
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v.id,
            "current_vehicle_stock": v.stock_number,
        }
        session.save()
        provider = MockLLMProvider(replies=["unused"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Pictures?")
        body = result.assistant_message.content
        self.assertIn(v.stock_number, body)
        # Honest about missing photo.
        self.assertIn("advisor", body.lower())


class DetectAppointmentRequestTests(TestCase):
    def test_canonical_phrasings_detected(self):
        for phrase in [
            "Can I come see it today?",
            "Can I test drive it?",
            "Can I come in?",
            "Can I come by?",
            "Is it available today?",
            "Is it available this weekend?",
            "I'd like to come see it",
            "I want to come in",
            "test drive it tomorrow",
        ]:
            self.assertTrue(
                detect_appointment_request(phrase),
                msg=f"expected detect: {phrase!r}",
            )


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEngineAppointmentGuardTests(TestCase):
    def test_appointment_with_current_vehicle_asks_name_phone_time(self):
        v = Vehicle.objects.create(
            stock_number="P8N-APT-1", year=2023, make="Ford",
            model="Bronco Sport", trim="Outer Banks AWD",
            body_style="suv", condition="certified",
            price=Decimal("38995"),
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v.id,
            "current_vehicle_stock": v.stock_number,
        }
        session.save()
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Can I come see it today?")
        body = result.assistant_message.content.lower()

        self.assertEqual(provider.calls, [])
        # Names the specific vehicle.
        self.assertIn("bronco sport", body)
        self.assertIn(v.stock_number.lower(), body)
        # Asks for time / name / phone.
        self.assertIn("time", body)
        self.assertIn("name", body)
        self.assertIn("phone", body)
        # Audit flag.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "appointment_request",
        )

    def test_appointment_does_not_promise_availability(self):
        v = Vehicle.objects.create(
            stock_number="P8N-APT-2", year=2024, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        session.extracted_profile = {
            "current_vehicle_id": v.id,
            "current_vehicle_stock": v.stock_number,
        }
        session.save()
        provider = MockLLMProvider(replies=["unused"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Can I test drive it?")
        body = result.assistant_message.content.lower()
        # Must NOT claim it's definitely available / on the lot today.
        for forbidden in [
            "it is available",
            "it's available",
            "available today",
            "on the lot right now",
            "ready to drive",
            "pull it up front",
        ]:
            self.assertNotIn(
                forbidden,
                body,
                msg=f"availability claim leaked: {forbidden!r}",
            )

    def test_appointment_without_current_vehicle_asks_clarification(self):
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Can I come see it today?")
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.content,
            _render(APPOINTMENT_REQUEST_NEEDS_VEHICLE_RESPONSE),
        )
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "appointment_request_needs_vehicle",
        )


class DetectInternalConfusionTests(TestCase):
    def test_canonical_phrases_detected(self):
        for phrase in [
            "Per the guidelines, I can suggest...",
            "Following the internal directive about budget...",
            "Per BUDGET ANALYSIS, the Edge fits...",
            "Based on the provided guidelines...",
            "I can help you craft a response that...",
        ]:
            self.assertTrue(
                detect_internal_confusion(phrase),
                msg=f"expected detect: {phrase!r}",
            )

    def test_clean_replies_not_flagged(self):
        for phrase in [
            "Here are some great trucks for you.",
            "The Bronco Sport is at $475/mo (W.A.C.).",
            "Want me to set up a test drive?",
        ]:
            self.assertFalse(
                detect_internal_confusion(phrase),
                msg=f"should NOT fire: {phrase!r}",
            )


class ChatEngineInternalConfusionFallbackTests(TestCase):
    def test_guideline_leak_triggers_full_replacement(self):
        Vehicle.objects.create(
            stock_number="P8N-CONF-1", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Per the provided guidelines, I can help you craft a "
                "response that includes vehicle info.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        body = result.assistant_message.content

        # Whole reply replaced with the safe fallback.
        self.assertEqual(body, INTERNAL_CONFUSION_FALLBACK)
        # Audit flag.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "internal_confusion_fallback",
        )
        # Forbidden phrases gone.
        self.assertNotIn("guidelines", body.lower())
        self.assertNotIn("craft a response", body.lower())

    def test_budget_analysis_leak_triggers_fallback(self):
        Vehicle.objects.create(
            stock_number="P8N-CONF-2", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Per BUDGET ANALYSIS the F-150 fits at $1000/mo.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        self.assertEqual(
            result.assistant_message.content, INTERNAL_CONFUSION_FALLBACK
        )
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "internal_confusion_fallback",
        )

    def test_clean_reply_does_not_trigger_fallback(self):
        Vehicle.objects.create(
            stock_number="P8N-CONF-3", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "The F-150 is a popular full-size pickup at $55,000.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Show me an F-150")
        self.assertNotEqual(
            result.assistant_message.content, INTERNAL_CONFUSION_FALLBACK
        )
        self.assertNotEqual(
            result.assistant_message.metadata.get("flag"),
            "internal_confusion_fallback",
        )


# ---- Phase 8o: real-world interaction guards -----------------------------


class DetectIdentityRequestTests(TestCase):
    """Identity questions ('are you real?', 'is this a bot?') must be
    detected so the engine can return a single in-persona, honest
    disclosure instead of letting the LLM drift."""

    def test_canonical_phrasings_detected(self):
        for phrase in [
            "Are you real?",
            "are you a real person",
            "Are you a human?",
            "Are you a human being?",
            "Are you a person?",
            "Are you a robot?",
            "Are you a bot?",
            "Are you AI?",
            "Are you an AI?",
            "Is this a bot?",
            "Is this a chatbot?",
            "Is this a real person?",
            "Is this AI?",
            "Am I talking to a person?",
            "Am I talking to AI?",
            "Am I chatting with a human?",
            "You're a bot, right?",
            "you are a robot",
        ]:
            self.assertTrue(
                detect_identity_request(phrase),
                msg=f"expected detect: {phrase!r}",
            )

    def test_non_identity_phrases_not_detected(self):
        for phrase in [
            "I want to talk to a real person",  # handoff, not identity
            "I need a human",  # handoff
            "Show me F-150s",
            "Are you open today?",
            "Can I afford a Bronco?",
        ]:
            self.assertFalse(
                detect_identity_request(phrase),
                msg=f"should NOT fire: {phrase!r}",
            )


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class IdentityResponseShapeTests(TestCase):
    def test_response_identifies_as_dealer_ai(self):
        body = _render(IDENTITY_RESPONSE).lower()
        self.assertIn("dealer os", body)
        self.assertIn("ai", body)

    def test_response_offers_advisor_handoff(self):
        body = IDENTITY_RESPONSE.lower()
        self.assertIn("advisor", body)

    def test_response_does_not_pretend_to_be_human(self):
        # Honest disclosure — must not say "I'm a real person" / "human".
        body = IDENTITY_RESPONSE.lower()
        self.assertNotIn("i'm a real person", body)
        self.assertNotIn("i'm a human", body)
        self.assertNotIn("i am human", body)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEngineIdentityGuardTests(TestCase):
    def _setup(self):
        session = ChatSession.objects.create()
        v = _make_vehicle("ID-1", price="55000")
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        return engine, session, v, provider

    def test_are_you_real_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message("are you real?")
        self.assertEqual(
            result.assistant_message.content, _render(IDENTITY_RESPONSE)
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "identity_request",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("provider"), "guard"
        )

    def test_is_this_a_bot_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message("Is this a bot?")
        self.assertEqual(
            result.assistant_message.content, _render(IDENTITY_RESPONSE)
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "identity_request",
        )

    def test_identity_response_no_persona_drift(self):
        # The reply must keep the Dealer OS AI persona — not
        # become a generic "I'm an AI assistant" response.
        engine, _, _, _ = self._setup()
        result = engine.handle_user_message("Am I talking to a person?")
        body = result.assistant_message.content.lower()
        self.assertIn("dealer os", body)


class DetectNegotiationRequestTests(TestCase):
    def test_canonical_phrasings_detected(self):
        for phrase in [
            "Will you match this price?",
            "Can you match the price?",
            "Will you beat their offer?",
            "Can you beat that price?",
            "Got a better deal?",
            "Any better price?",
            "Can you do 25k?",
            "Can you do $25,000?",
            "Can you do 28k out the door?",
            "Out the door for $30,000?",
            "What's the OTD price?",
            "Any discounts?",
            "Give me a discount",
            "Can we negotiate?",
            "Is this negotiable?",
            "Lower the price",
            "Drop the price please",
            "Can you knock off $1000?",
            "Knock $500 off",
            "Any wiggle room?",
            "Make me a deal",
            "Cut me a deal",
            "What's the best you can do?",
        ]:
            self.assertTrue(
                detect_negotiation_request(phrase),
                msg=f"expected detect: {phrase!r}",
            )

    def test_browsing_phrases_not_detected(self):
        for phrase in [
            "Show me F-150s",
            "Can I afford a Bronco?",
            "What's the price on the Mustang?",
            "Are you real?",
            "Tell me about it",
            "I need a human",
            # "best deal" alone is browse-shaped (the system-prompt
            # multi-option rule handles it). Only fires for negotiation
            # when prefixed by "give me / cut me / make me".
            "Show me the best deal under $30k",
            "Show me the best price under $30k",
            "What's the best deal you have?",
        ]:
            self.assertFalse(
                detect_negotiation_request(phrase),
                msg=f"should NOT fire: {phrase!r}",
            )


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class NegotiationResponseShapeTests(TestCase):
    def test_response_acknowledges_request(self):
        body = _render(NEGOTIATION_RESPONSE).lower()
        self.assertIn("get what you're trying to do", body)

    def test_response_redirects_to_advisor(self):
        # Phase 8p: redirect target is now the named Dealer OS
        # advisor (via {dealer_name} template) rather than a generic
        # "sales advisor".
        body = _render(NEGOTIATION_RESPONSE).lower()
        self.assertIn("advisor from dealer os", body)

    def test_response_does_not_quote_numbers(self):
        # No dollar figures in the canned response.
        import re as _re
        self.assertFalse(
            _re.search(r"\$\s*\d", NEGOTIATION_RESPONSE),
            msg=f"canned response leaks a number: {NEGOTIATION_RESPONSE!r}",
        )

    def test_response_does_not_agree_to_match(self):
        body = NEGOTIATION_RESPONSE.lower()
        for forbidden in [
            "i can match",
            "i'll match",
            "we can match",
            "we'll match",
            "i can beat",
            "we can do",
            "i can knock",
            "i'll knock",
        ]:
            self.assertNotIn(
                forbidden,
                body,
                msg=f"agreement phrase leaked: {forbidden!r}",
            )

    def test_response_asks_for_contact_info(self):
        body = NEGOTIATION_RESPONSE.lower()
        # Asks for a number and a time so an advisor can reach the
        # customer.
        self.assertIn("number", body)
        self.assertIn("time", body)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEngineNegotiationGuardTests(TestCase):
    def _setup(self):
        session = ChatSession.objects.create()
        v = _make_vehicle("NEG-1", price="55000")
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        return engine, session, v, provider

    def test_will_you_match_this_price_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message("Will you match this price?")
        self.assertEqual(
            result.assistant_message.content, _render(NEGOTIATION_RESPONSE)
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "negotiation_request",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("provider"), "guard"
        )

    def test_can_you_do_25k_otd_returns_canned_response(self):
        engine, _, _, provider = self._setup()
        result = engine.handle_user_message(
            "Can you do 25k out the door?"
        )
        self.assertEqual(
            result.assistant_message.content, _render(NEGOTIATION_RESPONSE)
        )
        self.assertEqual(provider.calls, [])
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "negotiation_request",
        )

    def test_negotiation_response_does_not_attach_inventory(self):
        # The conversation needs to focus on contact capture, not
        # browsing. matched_vehicles should be empty.
        engine, _, _, _ = self._setup()
        result = engine.handle_user_message("Any discounts?")
        self.assertEqual(list(result.matched_vehicles), [])
        self.assertEqual(
            result.assistant_message.metadata.get("matched_count"), 0
        )

    def test_negotiation_short_circuits_before_intent_extraction(self):
        engine, _, _, provider = self._setup()
        engine.handle_user_message("Will you beat their offer?")
        self.assertEqual(provider.calls, [])


class ChatEngineHandoffPhase8oFlagTests(TestCase):
    """Phase 8o: handoff flag renamed from 'salesperson_handoff' to
    'handoff_request'. The canned response is also simpler — no email
    ask, no AI-identity disclosure (that moves to IDENTITY_RESPONSE)."""

    def test_flag_is_handoff_request(self):
        session = ChatSession.objects.create()
        _make_vehicle("HO-PH8O-1", price="55000")
        provider = MockLLMProvider(replies=["unused"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I want to talk to a real person"
        )
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "handoff_request",
        )

    def test_response_no_fake_names(self):
        session = ChatSession.objects.create()
        _make_vehicle("HO-PH8O-2", price="55000")
        provider = MockLLMProvider(replies=["unused"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I want to talk to a real person"
        )
        body = result.assistant_message.content
        for fake in ["Sarah", "Mike", "John", "Steve", "Tony", "Dave"]:
            self.assertNotIn(fake, body)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ScrubPostLLMOverrideTests(TestCase):
    """Wholesale-replace replies that contain forbidden negotiation /
    fake-transfer phrasings."""

    def test_match_that_price_replaced_with_negotiation(self):
        cleaned, kind = scrub_post_llm_override(
            "Yes, I can match that price for you."
        )
        self.assertEqual(kind, "negotiation")
        self.assertEqual(cleaned, _render(NEGOTIATION_RESPONSE))

    def test_we_can_do_dollar_amount_replaced_with_negotiation(self):
        cleaned, kind = scrub_post_llm_override(
            "We can do $25,000 out the door."
        )
        self.assertEqual(kind, "negotiation")
        self.assertEqual(cleaned, _render(NEGOTIATION_RESPONSE))

    def test_knock_off_replaced_with_negotiation(self):
        cleaned, kind = scrub_post_llm_override(
            "I'll knock off $2000 today."
        )
        self.assertEqual(kind, "negotiation")
        self.assertEqual(cleaned, _render(NEGOTIATION_RESPONSE))

    def test_out_the_door_for_amount_replaced_with_negotiation(self):
        cleaned, kind = scrub_post_llm_override(
            "Out the door for $28000."
        )
        self.assertEqual(kind, "negotiation")
        self.assertEqual(cleaned, _render(NEGOTIATION_RESPONSE))

    def test_connecting_you_to_name_replaced_with_handoff(self):
        cleaned, kind = scrub_post_llm_override(
            "I'm connecting you to Sarah now."
        )
        self.assertEqual(kind, "handoff")
        self.assertEqual(cleaned, _render(HANDOFF_RESPONSE))

    def test_stay_on_the_line_replaced_with_handoff(self):
        cleaned, kind = scrub_post_llm_override(
            "Stay on the line while I get someone."
        )
        self.assertEqual(kind, "handoff")
        self.assertEqual(cleaned, _render(HANDOFF_RESPONSE))

    def test_transferring_you_now_replaced_with_handoff(self):
        cleaned, kind = scrub_post_llm_override(
            "transferring you now to a sales rep"
        )
        self.assertEqual(kind, "handoff")
        self.assertEqual(cleaned, _render(HANDOFF_RESPONSE))

    def test_clean_reply_unchanged(self):
        clean = "Here's the F-150 — happy to set up a real conversation."
        cleaned, kind = scrub_post_llm_override(clean)
        self.assertIsNone(kind)
        self.assertEqual(cleaned, clean)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEnginePostLLMOverrideTests(TestCase):
    """End-to-end: when the LLM returns negotiation or fake-transfer
    text, the engine wholesale-replaces the reply with the corresponding
    guard response and sets metadata.flag = 'post_llm_override'."""

    def test_llm_negotiation_text_overridden(self):
        Vehicle.objects.create(
            stock_number="P8O-N1", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "I can match that price for you. We can do $48,000.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        # User text doesn't trigger pre-LLM negotiation guard — the
        # LLM goes off-script. Pick a benign question.
        result = engine.handle_user_message("Tell me about the F-150")
        self.assertEqual(
            result.assistant_message.content, _render(NEGOTIATION_RESPONSE)
        )
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "post_llm_override",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("override_kind"),
            "negotiation",
        )

    def test_llm_fake_transfer_text_overridden(self):
        Vehicle.objects.create(
            stock_number="P8O-H1", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Sure — I'm connecting you to Sarah right now.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me about the F-150")
        self.assertEqual(
            result.assistant_message.content, _render(HANDOFF_RESPONSE)
        )
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "post_llm_override",
        )
        self.assertEqual(
            result.assistant_message.metadata.get("override_kind"),
            "handoff",
        )
        # Sarah is gone.
        self.assertNotIn("Sarah", result.assistant_message.content)

    def test_clean_llm_reply_does_not_override(self):
        Vehicle.objects.create(
            stock_number="P8O-CL1", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({"intent": "vehicle_search"}),
                "Here's the F-150 — happy to set up a real conversation.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Tell me about the F-150")
        self.assertNotEqual(
            result.assistant_message.metadata.get("flag"),
            "post_llm_override",
        )


# ---- Phase 8o+: live bug-report phrasings -------------------------------


class NegotiationGuardLiveBugReportPhrasingsTests(TestCase):
    """The four real-world phrasings that bypassed the original Phase 8o
    regex set in live testing must now fire the negotiation guard.
    Locked here so future regex tightening can't silently re-break
    them."""

    def test_lowest_youll_take_on_a_truck_detected(self):
        self.assertTrue(
            detect_negotiation_request(
                "what's the lowest you'll take on a truck?"
            )
        )

    def test_show_trucks_and_give_best_price_detected(self):
        self.assertTrue(
            detect_negotiation_request(
                "show me trucks and give me your best price"
            )
        )

    def test_tell_me_what_you_can_do_on_price_detected(self):
        self.assertTrue(
            detect_negotiation_request(
                "stop dodging — just tell me what you can do on price"
            )
        )

    def test_what_kind_of_discounts_detected(self):
        self.assertTrue(
            detect_negotiation_request(
                "what kind of discounts do you usually give?"
            )
        )

    def test_adjacent_variants_also_detected(self):
        for phrase in [
            "what is the lowest you can do",
            "how low will you go",
            "what's the most you'll take off",
            "how low can you go on this",
            "what's your best price",
            "tell me your best price",
            "give me your best deal",
            "do you have any discounts",
            "what discounts do you offer",
            "what types of discounts are available",
            "what kinds of discounts do you have",
            "what can you do on the price",
            "what will you do on price",
            "how much will you come down",
        ]:
            self.assertTrue(
                detect_negotiation_request(phrase),
                msg=f"expected detect: {phrase!r}",
            )

    def test_browse_phrasings_still_not_detected(self):
        # The broadening must not regress browse intent.
        for phrase in [
            "show me trucks under $30k",
            "show me the lowest mileage truck",
            "show me the best deal under $30k",
            "show me the best price under $30k",
            "what's the best deal you have?",
            "show me F-150s",
            "what is the engine on this F-150",
        ]:
            self.assertFalse(
                detect_negotiation_request(phrase),
                msg=f"should NOT fire: {phrase!r}",
            )


# ---- Phase 8o+: per-vehicle endpoint pre-LLM guards ---------------------


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class VehicleAskPreLLMGuardTests(TestCase):
    """The /vehicles/<id>/ask/ path used to bypass every guard. Phase 8o+
    routes it through the same pre-LLM checks the chat path uses, so
    negotiation / identity / handoff / rate / external-value / unsafe
    questions can't slip past via the per-vehicle endpoint."""

    def _setup(self):
        from dealer_ai.services.vehicle_assistant import answer_vehicle_question
        v = Vehicle.objects.create(
            stock_number="P8O-VA-1", year=2025, make="Ford",
            model="F-150", trim="XLT", body_style="truck",
            condition="new", mileage=10, price=Decimal("55000"),
        )
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        return answer_vehicle_question, v, provider

    def test_negotiation_question_returns_context_aware_no_llm(self):
        # Phase 8p: per-vehicle endpoint pins the input vehicle as the
        # current focus, so the response references it by name.
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "what's the lowest you'll take?", provider=provider
        )
        # Core safety phrasing intact.
        self.assertIn("advisor from dealer os", reply.lower())
        self.assertIn("number and time", reply.lower())
        # Context-aware: references the focus vehicle.
        self.assertIn(v.display_name, reply)
        self.assertEqual(provider.calls, [])

    def test_negotiation_show_me_best_price_returns_context_aware(self):
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "give me your best price", provider=provider
        )
        self.assertIn("advisor from dealer os", reply.lower())
        self.assertIn(v.display_name, reply)
        self.assertEqual(provider.calls, [])

    def test_discount_question_returns_context_aware(self):
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "what kind of discounts do you usually give?",
            provider=provider,
        )
        self.assertIn("advisor from dealer os", reply.lower())
        self.assertIn(v.display_name, reply)
        self.assertEqual(provider.calls, [])

    def test_identity_question_returns_canned(self):
        from dealer_ai.services.chat_engine import IDENTITY_RESPONSE
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "are you real?", provider=provider
        )
        self.assertEqual(reply, _render(IDENTITY_RESPONSE))
        self.assertEqual(provider.calls, [])

    def test_handoff_question_returns_canned(self):
        from dealer_ai.services.chat_engine import HANDOFF_RESPONSE
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "I want to talk to a real person", provider=provider
        )
        self.assertEqual(reply, _render(HANDOFF_RESPONSE))
        self.assertEqual(provider.calls, [])

    def test_rate_inquiry_returns_canned(self):
        from dealer_ai.services.chat_engine import RATE_INQUIRY_RESPONSE
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "what's the APR I'd qualify for?", provider=provider
        )
        self.assertEqual(reply, RATE_INQUIRY_RESPONSE)
        self.assertEqual(provider.calls, [])

    def test_external_value_returns_canned(self):
        from dealer_ai.services.chat_engine import EXTERNAL_VALUE_RESPONSE
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "what's the Blue Book value of my 2018 Camry?",
            provider=provider,
        )
        self.assertEqual(reply, _render(EXTERNAL_VALUE_RESPONSE))
        self.assertEqual(provider.calls, [])

    def test_unsafe_request_returns_guard_response(self):
        from dealer_ai.services.chat_engine import GUARD_RESPONSE
        answer_vehicle_question, v, provider = self._setup()
        reply = answer_vehicle_question(
            v, "What's your dealer cost on this F-150?", provider=provider
        )
        self.assertEqual(reply, GUARD_RESPONSE)
        self.assertEqual(provider.calls, [])

    def test_clean_question_still_calls_llm(self):
        # Sanity: a normal vehicle-detail question must still go to the
        # LLM (the guards only fire on the specific patterns above).
        from dealer_ai.services.vehicle_assistant import answer_vehicle_question
        v = Vehicle.objects.create(
            stock_number="P8O-VA-2", year=2025, make="Ford",
            model="F-150", trim="XLT", body_style="truck",
            condition="new", price=Decimal("55000"),
        )
        provider = MockLLMProvider(
            replies=["The F-150 XLT has the 2.7L EcoBoost V6."]
        )
        reply = answer_vehicle_question(
            v, "what engine does it have?", provider=provider
        )
        self.assertIn("EcoBoost", reply)
        self.assertEqual(len(provider.calls), 1)

    def test_guard_logs_to_session_with_audit_flag(self):
        from dealer_ai.services.vehicle_assistant import answer_vehicle_question
        v = Vehicle.objects.create(
            stock_number="P8O-VA-3", year=2025, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["unused"])
        answer_vehicle_question(
            v, "what's the lowest you'll take?",
            provider=provider, session=session,
        )
        msgs = list(
            session.messages.filter(role="assistant").order_by("-created_at")
        )
        self.assertGreaterEqual(len(msgs), 1)
        latest = msgs[0]
        self.assertEqual(
            latest.metadata.get("flag"), "negotiation_request"
        )
        self.assertEqual(latest.metadata.get("provider"), "guard")
        # Vehicle attached so dashboards know what was being asked about.
        self.assertEqual(list(latest.matched_vehicles.all()), [v])


# ---- Phase 8p: context-aware negotiation guard --------------------------


def _safe_negotiation_assertions(testcase, reply: str):
    """Shared safety assertions for any negotiation-guard reply."""
    body = reply.lower()
    # Core safe phrasing must be present.
    testcase.assertIn("advisor from dealer os", body)
    testcase.assertRegex(body, r"\bnumber\b")
    testcase.assertRegex(body, r"\btime\b")
    # Banned: any agreement / quote / discount-authority phrasing.
    for forbidden in [
        "we can match",
        "we'll match",
        "i can match",
        "i'll match",
        "i can knock",
        "i'll knock",
        "we can do $",
        "we can drop",
        "we can come down",
        "discount of",
        "promotion",
        "rebate available",
        "out the door for $",
        "we can work with that",
        "dealer cost",
        "invoice price",
        "margin",
        "holdback",
    ]:
        testcase.assertNotIn(
            forbidden,
            body,
            msg=f"forbidden phrase leaked into negotiation reply: {forbidden!r}",
        )


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class BuildNegotiationResponseHelperTests(TestCase):
    """Pure-function tests for build_negotiation_response. Verifies it
    pulls context from session+profile and falls back to the generic
    constant when no context is available."""

    def test_no_context_returns_generic_constant(self):
        # No session, no profile.
        self.assertEqual(
            build_negotiation_response(None), _render(NEGOTIATION_RESPONSE)
        )
        # Empty session, empty profile.
        session = ChatSession.objects.create()
        self.assertEqual(
            build_negotiation_response(session, profile={}),
            _render(NEGOTIATION_RESPONSE),
        )

    def test_truck_and_500_budget_from_profile_references_both(self):
        # Profile has body=truck and target=500. Reply must mention
        # both "trucks" and "$500/month".
        profile = {
            "vehicle_type": "truck",
            "target_monthly_payment": 500,
        }
        reply = build_negotiation_response(None, profile=profile)
        self.assertIn("trucks", reply)
        self.assertIn("$500/month", reply)
        _safe_negotiation_assertions(self, reply)

    def test_4wd_truck_and_500_from_session_history_references_4WD(self):
        # The user said "4wd truck" in a recent message AND the prior
        # assistant turn matched 4x4 trucks. Reply should say "4WD".
        v = Vehicle.objects.create(
            stock_number="P8P-T1", year=2024, make="Ford",
            model="F-150", trim="XLT 4x4", body_style="truck",
            condition="new", drivetrain="4x4",
            price=Decimal("48000"),
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "vehicle_type": "truck",
                "target_monthly_payment": 500,
            }
        )
        ChatMessage.objects.create(
            session=session, role="user",
            content="I am looking for a 4wd truck for around $500 a month",
        )
        prior = ChatMessage.objects.create(
            session=session, role="assistant",
            content="Here are some 4x4 trucks.",
        )
        prior.matched_vehicles.set([v])
        reply = build_negotiation_response(session)
        self.assertIn("4WD trucks", reply)
        self.assertIn("$500/month", reply)
        _safe_negotiation_assertions(self, reply)

    def test_current_vehicle_pinned_references_vehicle_by_name(self):
        v = Vehicle.objects.create(
            stock_number="P8P-CV-1", year=2023, make="Ford",
            model="Bronco Sport", trim="Outer Banks AWD",
            body_style="suv", condition="certified",
            drivetrain="AWD", price=Decimal("38995"),
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "current_vehicle_id": v.id,
                "current_vehicle_stock": v.stock_number,
                "target_monthly_payment": 600,
            }
        )
        reply = build_negotiation_response(session)
        # Must reference the exact vehicle name.
        self.assertIn(v.display_name, reply)
        self.assertIn("$600/month", reply)
        _safe_negotiation_assertions(self, reply)

    def test_used_truck_with_no_drivetrain_hint(self):
        # condition=used + body=truck → "used trucks" (no drivetrain
        # available because no recent matched_vehicles).
        profile = {"vehicle_type": "truck", "condition": "used"}
        reply = build_negotiation_response(None, profile=profile)
        self.assertIn("used trucks", reply)
        _safe_negotiation_assertions(self, reply)

    def test_model_lock_uses_model_phrase(self):
        # profile.model wins over generic body type.
        profile = {"model": "F-150", "target_monthly_payment": 500}
        reply = build_negotiation_response(None, profile=profile)
        self.assertIn("F-150s", reply)
        self.assertIn("$500/month", reply)
        _safe_negotiation_assertions(self, reply)

    def test_budget_only_no_body_still_personalized(self):
        # Customer has set a monthly target but no body type.
        profile = {"target_monthly_payment": 700}
        reply = build_negotiation_response(None, profile=profile)
        self.assertIn("$700/month", reply)
        # Sentence falls back to "targeting payments around your..."
        self.assertIn("targeting payments", reply.lower())
        _safe_negotiation_assertions(self, reply)

    def test_response_contains_no_dollar_amounts_other_than_customer_target(self):
        # The customer's stated $/mo is the ONLY dollar figure that
        # may appear. No invented prices, no quotes, no discounts.
        profile = {
            "vehicle_type": "truck",
            "target_monthly_payment": 500,
        }
        reply = build_negotiation_response(None, profile=profile)
        import re as _re
        # Find every $ figure in the reply.
        found = _re.findall(r"\$\s*[\d,]+", reply)
        # Each should be exactly the customer's stated target.
        for fig in found:
            digits = "".join(c for c in fig if c.isdigit())
            self.assertEqual(
                int(digits), 500,
                msg=f"unexpected dollar figure in reply: {fig!r}",
            )

    def test_stale_current_vehicle_id_falls_back_gracefully(self):
        # current_vehicle_id points at a deleted vehicle → vehicle
        # label resolves to None and the helper falls through to
        # category/budget/generic.
        v = Vehicle.objects.create(
            stock_number="P8P-STALE", year=2024, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("48000"),
        )
        stale_id = v.id
        v.delete()
        session = ChatSession.objects.create(
            extracted_profile={
                "current_vehicle_id": stale_id,
                "vehicle_type": "truck",
                "target_monthly_payment": 500,
            }
        )
        reply = build_negotiation_response(session)
        # Falls through to category phrase.
        self.assertIn("trucks", reply)
        self.assertIn("$500/month", reply)
        _safe_negotiation_assertions(self, reply)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class ChatEngineNegotiationContextAwareTests(TestCase):
    """End-to-end: chat path uses build_negotiation_response so the
    canned reply references the customer's prior context."""

    def test_chat_path_uses_context_aware_helper(self):
        v = Vehicle.objects.create(
            stock_number="P8P-CHAT-1", year=2024, make="Ford",
            model="F-150", trim="XLT 4x4", body_style="truck",
            condition="new", drivetrain="4x4",
            price=Decimal("48000"),
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "vehicle_type": "truck",
                "target_monthly_payment": 500,
            }
        )
        ChatMessage.objects.create(
            session=session, role="user",
            content="I am looking for a 4wd truck for around $500 a month",
        )
        prior = ChatMessage.objects.create(
            session=session, role="assistant",
            content="Here are some 4x4 trucks.",
        )
        prior.matched_vehicles.set([v])

        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "what's the lowest you'll take on a truck?"
        )
        body = result.assistant_message.content

        # Context-aware: references the truck class + budget.
        self.assertIn("4WD trucks", body)
        self.assertIn("$500/month", body)
        # Audit flag preserved.
        self.assertEqual(
            result.assistant_message.metadata.get("flag"),
            "negotiation_request",
        )
        # No LLM.
        self.assertEqual(provider.calls, [])
        _safe_negotiation_assertions(self, body)

    def test_chat_path_no_context_returns_generic_constant(self):
        Vehicle.objects.create(
            stock_number="P8P-CHAT-2", year=2024, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("48000"),
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("Will you match this price?")
        # Empty profile → generic constant verbatim.
        self.assertEqual(
            result.assistant_message.content, _render(NEGOTIATION_RESPONSE)
        )
        self.assertEqual(provider.calls, [])

    def test_chat_path_negotiation_no_llm_under_full_context(self):
        # Even with a fully-populated session, the guard must not
        # invoke the provider.
        v = Vehicle.objects.create(
            stock_number="P8P-CHAT-3", year=2023, make="Ford",
            model="Bronco Sport", trim="Outer Banks", body_style="suv",
            condition="certified", drivetrain="AWD",
            price=Decimal("38995"),
        )
        session = ChatSession.objects.create(
            extracted_profile={
                "current_vehicle_id": v.id,
                "current_vehicle_stock": v.stock_number,
                "target_monthly_payment": 600,
            }
        )
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "what's your best price"
        )
        self.assertEqual(provider.calls, [])
        body = result.assistant_message.content
        self.assertIn(v.display_name, body)
        self.assertIn("$600/month", body)
        _safe_negotiation_assertions(self, body)


@override_settings(DEALER_AI_DEALER_NAME="Dealer OS")
class VehicleAskNegotiationContextAwareTests(TestCase):
    """End-to-end: /vehicles/<id>/ask/ negotiation guard uses the same
    helper, with the input vehicle pinned as the focus."""

    def test_vehicle_ask_negotiation_references_input_vehicle(self):
        from dealer_ai.services.vehicle_assistant import (
            answer_vehicle_question,
        )
        v = Vehicle.objects.create(
            stock_number="P8P-VA-1", year=2023, make="Ford",
            model="Bronco Sport", trim="Outer Banks AWD",
            body_style="suv", condition="certified",
            price=Decimal("38995"),
        )
        session = ChatSession.objects.create(
            extracted_profile={"target_monthly_payment": 600}
        )
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        reply = answer_vehicle_question(
            v, "what's the lowest you'll take?",
            provider=provider, session=session,
        )
        # Same context-aware helper → references the vehicle by name
        # AND the budget the session profile holds.
        self.assertIn(v.display_name, reply)
        self.assertIn("$600/month", reply)
        self.assertEqual(provider.calls, [])
        _safe_negotiation_assertions(self, reply)

    def test_vehicle_ask_negotiation_no_session_still_safe(self):
        # Stateless call (no session) — vehicle alone still anchors
        # the response.
        from dealer_ai.services.vehicle_assistant import (
            answer_vehicle_question,
        )
        v = Vehicle.objects.create(
            stock_number="P8P-VA-2", year=2024, make="Ford",
            model="F-150", body_style="truck", condition="new",
            price=Decimal("55000"),
        )
        provider = MockLLMProvider(replies=["LLM SHOULD NOT BE CALLED"])
        reply = answer_vehicle_question(
            v, "give me your best price", provider=provider,
        )
        self.assertIn(v.display_name, reply)
        self.assertEqual(provider.calls, [])
        _safe_negotiation_assertions(self, reply)


# ---- Phase 8q: drivetrain extraction + budget filtering -----------------


class DrivetrainExtractionTests(SimpleTestCase):
    """regex_extract must capture canonical drivetrain values from
    common phrasings so build_budget_context can apply them as filters."""

    def test_4wd_phrasings(self):
        from dealer_ai.services.intent_parser import regex_extract
        for phrase in [
            "I want a 4wd truck",
            "looking for a 4WD",
            "I'd like a 4-wd Ford",
            "got any 4x4 trucks?",
            "show me 4-wheel drive trucks",
            "looking for four-wheel drive",
            "4 wheel drive please",
        ]:
            self.assertEqual(
                regex_extract(phrase).get("drivetrain"),
                "4WD",
                msg=f"expected 4WD for: {phrase!r}",
            )

    def test_awd_phrasings(self):
        from dealer_ai.services.intent_parser import regex_extract
        for phrase in [
            "I want AWD",
            "AWD SUV please",
            "all-wheel drive Bronco Sport",
            "all wheel drive crossover",
        ]:
            self.assertEqual(
                regex_extract(phrase).get("drivetrain"),
                "AWD",
                msg=f"expected AWD for: {phrase!r}",
            )

    def test_rwd_phrasings(self):
        # 4x2 / 2wd / RWD all canonicalize to RWD because dealer
        # inventory tags 4x2 trucks with drivetrain="RWD".
        from dealer_ai.services.intent_parser import regex_extract
        for phrase in [
            "4x2 truck is fine",
            "2WD please",
            "rear-wheel drive",
            "RWD car",
        ]:
            self.assertEqual(
                regex_extract(phrase).get("drivetrain"),
                "RWD",
                msg=f"expected RWD for: {phrase!r}",
            )

    def test_fwd_phrasings(self):
        from dealer_ai.services.intent_parser import regex_extract
        for phrase in [
            "FWD is fine",
            "front-wheel drive Escape",
            "front wheel drive",
        ]:
            self.assertEqual(
                regex_extract(phrase).get("drivetrain"),
                "FWD",
                msg=f"expected FWD for: {phrase!r}",
            )

    def test_no_drivetrain_mention(self):
        from dealer_ai.services.intent_parser import regex_extract
        for phrase in [
            "Show me F-150s",
            "I want a truck",
            "$500/mo",
            "are you real?",
        ]:
            self.assertNotIn(
                "drivetrain",
                regex_extract(phrase),
                msg=f"unexpected drivetrain for: {phrase!r}",
            )


class DrivetrainProfilePersistenceTests(SimpleTestCase):
    """drivetrain merges into the session profile and persists across
    turns the same way model / vehicle_type do."""

    def test_drivetrain_carries_forward(self):
        from dealer_ai.services.intent_parser import (
            merge_profile, parse_intent,
        )
        # Turn 1: explicit drivetrain.
        new1 = parse_intent(
            "I am looking for a 4wd truck around $500/mo", use_llm=False
        )
        profile = merge_profile({}, new1)
        self.assertEqual(profile.get("drivetrain"), "4WD")
        # Turn 2: no drivetrain mention — must persist from prior turn.
        new2 = parse_intent("show me ones under 30k", use_llm=False)
        profile = merge_profile(profile, new2)
        self.assertEqual(profile.get("drivetrain"), "4WD")

    def test_drivetrain_can_be_overwritten(self):
        from dealer_ai.services.intent_parser import (
            merge_profile, parse_intent,
        )
        # Turn 1: 4WD.
        profile = merge_profile(
            {}, parse_intent("4wd truck", use_llm=False)
        )
        self.assertEqual(profile.get("drivetrain"), "4WD")
        # Turn 2: customer pivots to AWD.
        profile = merge_profile(
            profile, parse_intent("actually I'd prefer AWD", use_llm=False)
        )
        self.assertEqual(profile.get("drivetrain"), "AWD")


def _seed_truck_inventory_for_4wd_filter():
    """Seed a representative truck mix: a cheap 4x2, a near-budget 4x4,
    and a couple stretch 4x4 options. Mirrors the bug-report scenario."""
    cheap_4x2 = Vehicle.objects.create(
        stock_number="P8Q-T1", year=2020, make="Chevrolet",
        model="Colorado", trim="WT 4x2", body_style="truck",
        condition="used", drivetrain="RWD", mileage=55000,
        price=Decimal("25495"),
    )
    near_4x4 = Vehicle.objects.create(
        stock_number="P8Q-T2", year=2019, make="Ford",
        model="Ranger", trim="XLT SuperCrew 4x4", body_style="truck",
        condition="used", drivetrain="4x4", mileage=73500,
        price=Decimal("26995"),
    )
    stretch_4x4_a = Vehicle.objects.create(
        stock_number="P8Q-T3", year=2023, make="Ford",
        model="Ranger", trim="Lariat 4x4", body_style="truck",
        condition="certified", drivetrain="4x4", mileage=18000,
        price=Decimal("39995"),
    )
    stretch_4x4_b = Vehicle.objects.create(
        stock_number="P8Q-T4", year=2022, make="Ford",
        model="F-150", trim="STX 4x4", body_style="truck",
        condition="certified", drivetrain="4x4", mileage=35000,
        price=Decimal("42995"),
    )
    return cheap_4x2, near_4x4, stretch_4x4_a, stretch_4x4_b


class BuildBudgetContextHonorsDrivetrainTests(TestCase):
    """The bug report: customer asks for a 4WD truck at $500/mo and
    sees a 4x2 as the primary option. With the Phase 8q drivetrain
    filter, 4x2 trucks are excluded from the candidate pool when
    drivetrain='4WD' is in profile."""

    def test_4wd_filter_excludes_4x2_trucks(self):
        from dealer_ai.services.chat_engine import build_budget_context
        cheap_4x2, near_4x4, *_ = _seed_truck_inventory_for_4wd_filter()
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
            "vehicle_type": "truck",
            "drivetrain": "4WD",
        }
        ctx = build_budget_context(profile, "4wd truck $500", regex_hits={})
        all_returned = (
            ctx.matched_in_budget + ctx.near_fit + ctx.closest_above
        )
        ids = [v.id for v in all_returned]
        self.assertNotIn(
            cheap_4x2.id, ids,
            msg="4x2 truck must NOT appear when drivetrain=4WD",
        )

    def test_4wd_filter_with_no_fit_populates_closest_above(self):
        # Bug-report scenario: target=500, $0 down, 60mo. Cheapest
        # 4WD truck (Ranger XLT $26,995) computes to $577/mo — over
        # the $75 tolerance. fit=0, near=0 → closest_above must
        # populate with the 3 cheapest 4WD trucks as stretch options.
        from dealer_ai.services.chat_engine import build_budget_context
        _cheap_4x2, near_4x4, stretch_a, stretch_b = (
            _seed_truck_inventory_for_4wd_filter()
        )
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
            "vehicle_type": "truck",
            "drivetrain": "4WD",
        }
        ctx = build_budget_context(profile, "4wd truck $500", regex_hits={})
        self.assertEqual(len(ctx.matched_in_budget), 0)
        self.assertEqual(len(ctx.near_fit), 0)
        self.assertGreaterEqual(len(ctx.closest_above), 1)
        stretch_ids = {v.id for v in ctx.closest_above}
        # Cheapest 4x4 truck must be in the stretch list.
        self.assertIn(near_4x4.id, stretch_ids)
        # And every stretch option must actually be 4WD.
        for v in ctx.closest_above:
            self.assertIn(
                "4x4", (v.drivetrain or "").lower() + (v.trim or "").lower(),
                msg=f"stretch option not 4WD: {v.stock_number} drivetrain={v.drivetrain!r}",
            )

    def test_matched_vehicles_excludes_closest_above_stretches(self):
        # Critical contract: matched_vehicles (the API field driving
        # frontend cards) must NEVER include over-budget vehicles, even
        # when surfaced as stretch context for the LLM.
        from dealer_ai.services.chat_engine import build_budget_context
        _seed_truck_inventory_for_4wd_filter()
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
            "vehicle_type": "truck",
            "drivetrain": "4WD",
        }
        ctx = build_budget_context(profile, "4wd truck $500", regex_hits={})
        # matched_in_budget + near_fit is the API surface — must be empty
        # in this scenario (closest_above is internal only).
        matched = ctx.matched_in_budget + ctx.near_fit
        self.assertEqual(len(matched), 0)
        # closest_above is populated but does NOT flow into
        # matched_vehicles when build_budget_context is consumed by
        # handle_user_message.
        self.assertGreater(len(ctx.closest_above), 0)

    def test_4wd_with_more_down_creates_near_or_fit(self):
        # Realistic narrowing path 1: $3k down at 60mo brings the
        # Ranger XLT 4x4 to $517/mo — near-fit (within $75 tolerance).
        # Customer-visible payment is no longer over-budget.
        from dealer_ai.services.chat_engine import build_budget_context
        _, near_4x4, *_ = _seed_truck_inventory_for_4wd_filter()
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 3000,
            "term_months": 60,
            "vehicle_type": "truck",
            "drivetrain": "4WD",
        }
        ctx = build_budget_context(
            profile, "4wd truck $500 with $3k down", regex_hits={}
        )
        matched_ids = {
            v.id for v in (ctx.matched_in_budget + ctx.near_fit)
        }
        self.assertIn(
            near_4x4.id, matched_ids,
            msg="Ranger XLT 4x4 must surface (fit or near-fit) with $3k down",
        )

    def test_4wd_with_72mo_creates_fits(self):
        # Realistic narrowing path 2: 72mo at $0 down brings the
        # Ranger to $498/mo (right at target).
        from dealer_ai.services.chat_engine import build_budget_context
        _, near_4x4, *_ = _seed_truck_inventory_for_4wd_filter()
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 72,
            "vehicle_type": "truck",
            "drivetrain": "4WD",
        }
        ctx = build_budget_context(
            profile, "4wd truck $500 over 6 years", regex_hits={}
        )
        all_in_or_near = (
            ctx.matched_in_budget + ctx.near_fit
        )
        ids = {v.id for v in all_in_or_near}
        self.assertIn(
            near_4x4.id, ids,
            msg="Ranger XLT 4x4 should be fit/near-fit at 72mo $0 down",
        )

    def test_awd_filter_only_returns_awd_vehicles(self):
        from dealer_ai.services.chat_engine import build_budget_context
        v_awd = Vehicle.objects.create(
            stock_number="P8Q-AWD-1", year=2024, make="Ford",
            model="Bronco Sport", body_style="suv", condition="new",
            drivetrain="AWD", price=Decimal("36000"),
        )
        v_fwd = Vehicle.objects.create(
            stock_number="P8Q-FWD-1", year=2024, make="Ford",
            model="Escape", body_style="suv", condition="new",
            drivetrain="FWD", price=Decimal("32000"),
        )
        profile = {
            "target_monthly_payment": 700,
            "down_payment": 0,
            "term_months": 60,
            "vehicle_type": "suv",
            "drivetrain": "AWD",
        }
        ctx = build_budget_context(profile, "AWD SUV $700", regex_hits={})
        all_returned = (
            ctx.matched_in_budget + ctx.near_fit + ctx.closest_above
        )
        ids = [v.id for v in all_returned]
        self.assertIn(v_awd.id, ids)
        self.assertNotIn(v_fwd.id, ids)

    def test_no_drivetrain_pref_returns_full_pool(self):
        # Backward compat: when drivetrain is absent from profile, the
        # behavior is unchanged from Phase 8p — body/model/condition
        # filters apply as before, no drivetrain narrowing.
        from dealer_ai.services.chat_engine import build_budget_context
        cheap_4x2, near_4x4, *_ = _seed_truck_inventory_for_4wd_filter()
        profile = {
            "target_monthly_payment": 500,
            "down_payment": 0,
            "term_months": 60,
            "vehicle_type": "truck",
            # NO drivetrain — pre-Phase-8q behavior.
        }
        ctx = build_budget_context(profile, "$500/mo truck", regex_hits={})
        # Both the 4x2 Colorado and the 4x4 Ranger should be in the
        # candidate pool (4x2 → near-fit, 4x4 → over-budget).
        seen = {v.id for v in (
            ctx.matched_in_budget + ctx.near_fit + ctx.closest_above
        )}
        self.assertIn(cheap_4x2.id, seen)


class ChatEngine4WDBugReportEndToEndTests(TestCase):
    """End-to-end: the exact bug-report scenario through ChatEngine.
    Verifies the live behavior the user observed is fixed."""

    def test_4wd_truck_500_per_month_does_not_show_4x2_as_primary(self):
        cheap_4x2, near_4x4, stretch_a, stretch_b = (
            _seed_truck_inventory_for_4wd_filter()
        )
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Sticker for the cheapest 4WD lands at $577/mo at 60 "
                "months and $0 down — close to your $500 target. With "
                "$3k down or a 72-month term, the Ranger XLT lands "
                "right at $500. Want me to set up an advisor call?",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I am looking for a 4wd truck for around $500 a month"
        )
        # API contract: the 4x2 Colorado may appear ONLY as a labeled
        # drivetrain-flex card — never as a primary 4WD match. With
        # Phase 8s/UX lever-flex presentation, it surfaces with
        # _lever_flex_kind="drivetrain_flex" + an explainer that names
        # the compromise verbatim ("2WD") so the customer cannot
        # mistake it for 4WD. The flex annotation is the honesty
        # contract — without it the card would be a misleading match.
        cheap_4x2_card = next(
            (v for v in result.matched_vehicles if v.id == cheap_4x2.id),
            None,
        )
        if cheap_4x2_card is not None:
            self.assertEqual(
                getattr(cheap_4x2_card, "_lever_flex_kind", None),
                "drivetrain_flex",
                "4x2 Colorado must only appear with the "
                "drivetrain_flex label, never as a strict 4WD match",
            )
            self.assertIn(
                "2WD",
                getattr(cheap_4x2_card, "_lever_flex_explainer", "") or "",
            )
        # Profile carries the drivetrain capture.
        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("drivetrain"), "4WD"
        )

    def test_4wd_session_profile_persists_across_turns(self):
        # Turn 1 establishes drivetrain. Turn 2 ("show me cheaper ones")
        # has no drivetrain mention but the filter still applies.
        cheap_4x2, near_4x4, *_ = _seed_truck_inventory_for_4wd_filter()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}), "Here are some 4WD trucks.",
                json_reply({}), "Cheaper options on the way.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message(
            "I am looking for a 4wd truck for around $500 a month"
        )
        # Turn 2: no drivetrain word — should still filter to 4WD.
        result2 = engine.handle_user_message("any cheaper options?")
        # The 4x2 Colorado may surface as a labeled drivetrain-flex
        # presentation card, but the 4WD strict filter still
        # determines the primary matches. Verify the persistence by
        # asserting the 4x2 only appears with the flex label.
        for v in result2.matched_vehicles:
            if v.id == cheap_4x2.id:
                self.assertEqual(
                    getattr(v, "_lever_flex_kind", None),
                    "drivetrain_flex",
                    "drivetrain=4WD must persist across turns; the "
                    "4x2 may only appear as a labeled flex pick",
                )


# ---- Phase 8r: cash-budget extraction + max_price routing -----------------


class MaxPriceExtractionTests(SimpleTestCase):
    """regex_extract must capture max_price from explicit cash-budget
    phrasings without false-positively grabbing monthly-payment numbers."""

    def test_dollar_17000_cash_canonical_bug_report(self):
        from dealer_ai.services.intent_parser import regex_extract
        out = regex_extract(
            "I have exactly $17,000 cash. what inventory do you have "
            "for less than that?"
        )
        self.assertEqual(out.get("max_price"), 17000)

    def test_under_20k(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("under $20k").get("max_price"), 20000
        )

    def test_less_than_15000(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("less than $15,000").get("max_price"), 15000
        )

    def test_up_to_25k(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("up to $25k").get("max_price"), 25000
        )

    def test_max_30000(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("max $30,000").get("max_price"), 30000
        )
        self.assertEqual(
            regex_extract("maximum of $30k").get("max_price"), 30000
        )

    def test_budget_of_25k(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("budget of $25k").get("max_price"), 25000
        )
        self.assertEqual(
            regex_extract("cash budget of $20,000").get("max_price"),
            20000,
        )

    def test_spend_up_to(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("spend up to $22k").get("max_price"), 22000
        )

    def test_below_phrasing(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("below $18,000").get("max_price"), 18000
        )

    def test_no_more_than_phrasing(self):
        from dealer_ai.services.intent_parser import regex_extract
        self.assertEqual(
            regex_extract("no more than $25k").get("max_price"), 25000
        )

    def test_monthly_forms_do_not_capture_max_price(self):
        # Critical: "$500/mo" / "$500 per month" / "$500 a month" must
        # NOT be captured as max_price. They are target_monthly_payment.
        # The Phase 8r negative-lookahead also rejects "$500 monthly" /
        # "$500/month" — those would never have hit max_price even
        # though _MONTHLY_PATTERNS itself has gaps for bare "monthly"
        # (separate pre-existing concern, out of scope for 8r).
        from dealer_ai.services.intent_parser import regex_extract
        # These should both reject max_price AND capture monthly:
        for phrase in [
            "$500/mo",
            "$500 per month",
            "$500 a month",
            "less than $500/mo",
            "around $500 a month",
            "less than $500 per month",
        ]:
            out = regex_extract(phrase)
            self.assertNotIn(
                "max_price", out,
                msg=f"max_price must not capture monthly form: {phrase!r}",
            )
            self.assertEqual(
                out.get("target_monthly_payment"), 500,
                msg=f"target_monthly_payment expected for: {phrase!r}",
            )
        # These should reject max_price (the negative lookahead works)
        # even when monthly capture itself is gappy:
        for phrase in [
            "$500 monthly",
            "$500/month",
        ]:
            out = regex_extract(phrase)
            self.assertNotIn(
                "max_price", out,
                msg=f"max_price must not capture: {phrase!r}",
            )

    def test_down_payment_does_not_double_capture(self):
        from dealer_ai.services.intent_parser import regex_extract
        out = regex_extract("$3k down at 60 months")
        self.assertEqual(out.get("down_payment"), 3000)
        self.assertNotIn("max_price", out)

    def test_too_low_amount_rejected(self):
        # Range guard: max_price < $1,000 is treated as noise.
        from dealer_ai.services.intent_parser import regex_extract
        for phrase in [
            "less than $500",
            "under $999",
            "up to $100",
        ]:
            self.assertNotIn(
                "max_price", regex_extract(phrase),
                msg=f"sub-$1k must be rejected: {phrase!r}",
            )

    def test_max_price_persists_via_merge_profile(self):
        from dealer_ai.services.intent_parser import (
            merge_profile, parse_intent,
        )
        # Turn 1: cash budget set.
        profile = merge_profile(
            {}, parse_intent("$17,000 cash", use_llm=False)
        )
        self.assertEqual(profile.get("max_price"), 17000)
        # Turn 2: no max_price mention — must persist.
        profile = merge_profile(
            profile, parse_intent("show me used sedans", use_llm=False)
        )
        self.assertEqual(profile.get("max_price"), 17000)

    def test_max_price_can_be_overwritten(self):
        from dealer_ai.services.intent_parser import (
            merge_profile, parse_intent,
        )
        profile = merge_profile(
            {}, parse_intent("$17,000 cash", use_llm=False)
        )
        # Customer revises ceiling.
        profile = merge_profile(
            profile, parse_intent("actually under $25k", use_llm=False)
        )
        self.assertEqual(profile.get("max_price"), 25000)


class ChatEngineMaxPriceRoutingTests(TestCase):
    """End-to-end: when profile has max_price, the non-budget keyword
    search path passes it through to search_vehicles so over-budget
    vehicles never reach matched_vehicles."""

    def _seed_cash_budget_inventory(self):
        # 3 cheap vehicles ≤ $17k (real candidates) + 3 expensive ones.
        cheap_a = Vehicle.objects.create(
            stock_number="P8R-CHEAP-1", year=2014, make="Ford",
            model="Fusion", trim="SE", body_style="car",
            condition="used", price=Decimal("11995"),
        )
        cheap_b = Vehicle.objects.create(
            stock_number="P8R-CHEAP-2", year=2017, make="Hyundai",
            model="Sonata", trim="SE", body_style="car",
            condition="used", price=Decimal("10995"),
        )
        cheap_c = Vehicle.objects.create(
            stock_number="P8R-CHEAP-3", year=2017, make="Chevrolet",
            model="Equinox", trim="LT", body_style="suv",
            condition="used", price=Decimal("16995"),
        )
        expensive_a = Vehicle.objects.create(
            stock_number="P8R-EXP-1", year=2025, make="Ford",
            model="F-150", trim="XLT 4x4", body_style="truck",
            condition="new", price=Decimal("55000"),
        )
        expensive_b = Vehicle.objects.create(
            stock_number="P8R-EXP-2", year=2025, make="Ford",
            model="Maverick", trim="XLT Hybrid", body_style="truck",
            condition="new", price=Decimal("33495"),
        )
        return (cheap_a, cheap_b, cheap_c), (expensive_a, expensive_b)

    def test_canonical_bug_report_only_returns_under_17k(self):
        cheap, expensive = self._seed_cash_budget_inventory()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Here are some options at or under your $17,000 cash budget.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "I have exactly $17,000 cash. what inventory do you have "
            "for less than that?"
        )
        # Every returned vehicle must be ≤ $17,000.
        self.assertGreater(len(result.matched_vehicles), 0)
        for v in result.matched_vehicles:
            self.assertLessEqual(
                float(v.price), 17000,
                msg=f"OVER BUDGET vehicle leaked: {v.stock_number} ${v.price}",
            )
        # Profile captures max_price.
        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("max_price"), 17000
        )

    def test_under_20k_filters_correctly(self):
        cheap, expensive = self._seed_cash_budget_inventory()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Options under $20k."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "show me what you have under $20k"
        )
        for v in result.matched_vehicles:
            self.assertLessEqual(float(v.price), 20000)
        session.refresh_from_db()
        self.assertEqual(
            session.extracted_profile.get("max_price"), 20000
        )

    def test_less_than_15000_filters_correctly(self):
        cheap, expensive = self._seed_cash_budget_inventory()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Sub-$15k options."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message(
            "looking for less than $15,000"
        )
        for v in result.matched_vehicles:
            self.assertLessEqual(float(v.price), 15000)
        # Should hit the two cheap_a / cheap_b ($11,995 / $10,995),
        # but NOT the $16,995 Equinox or any expensive option.
        ids = {v.id for v in result.matched_vehicles}
        cheap_a, cheap_b, cheap_c = cheap
        expensive_a, expensive_b = expensive
        self.assertIn(cheap_a.id, ids)
        self.assertIn(cheap_b.id, ids)
        self.assertNotIn(cheap_c.id, ids)  # $16,995 over the $15k ceiling
        self.assertNotIn(expensive_a.id, ids)
        self.assertNotIn(expensive_b.id, ids)

    def test_max_price_persists_across_turns(self):
        # Turn 1 sets max_price=17000. Turn 2 has no $-mention but the
        # filter still applies to the search.
        cheap, expensive = self._seed_cash_budget_inventory()
        expensive_a, expensive_b = expensive
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[
                json_reply({}), "Cheap options.",
                json_reply({}), "Some sedans for you.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("$17,000 cash")
        result2 = engine.handle_user_message("show me sedans")
        for v in result2.matched_vehicles:
            self.assertLessEqual(float(v.price), 17000)
        ids2 = {v.id for v in result2.matched_vehicles}
        self.assertNotIn(expensive_a.id, ids2)
        self.assertNotIn(expensive_b.id, ids2)

    def test_no_max_price_returns_full_pool(self):
        # Backward-compat: queries without a cash-budget signal behave
        # exactly as before — no max_price filter applied.
        cheap, expensive = self._seed_cash_budget_inventory()
        session = ChatSession.objects.create()
        provider = MockLLMProvider(
            replies=[json_reply({}), "Here's our inventory."]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("show me what you have")
        # Returned set may include over-$17k vehicles (no ceiling).
        prices = [float(v.price) for v in result.matched_vehicles]
        self.assertGreater(max(prices), 17000)
