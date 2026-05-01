"""Phase 8g — payment copy consistency tests.

Bug being fixed: BUDGET ANALYSIS computed $517.03/mo for the Ranger but the
inventory block re-computed $498/mo at default 72mo / $0 down, and the LLM
quoted the $498. Now the inventory block reuses the annotated payment and
a post-LLM consistency check flags any drift.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import ChatSession, Vehicle
from dealer_ai.services.chat_engine import (
    ChatEngine,
    _format_vehicle_block,
    check_payment_consistency,
    scrub_extra_payment_quotes,
    scrub_payment_drift,
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


# ---- _format_vehicle_block reuses annotation -----------------------------


class VehicleBlockUsesAnnotationTests(TestCase):
    def test_annotated_vehicle_uses_annotation_payment(self):
        v = _make_vehicle("ANN-1", "26995", model="Ranger")
        v._estimated_payment = 517.03  # what BUDGET ANALYSIS computed
        v._budget_fit = "near_fit"
        v._payment_delta = 17.03

        block = _format_vehicle_block([v], budget_mode=True)
        self.assertIn("$517", block)
        # Must NOT show the engine-default 72mo / $0-down payment for this
        # vehicle ($498ish) — that's the bug.
        self.assertNotIn("72mo @ 7.49%", block)
        # Phase 8m+: the "do not recompute" directive moved out of the
        # per-line W.A.C. parenthetical into the block header (so the LLM
        # is less likely to echo it inline with a payment). Case-insensitive
        # match is fine — what matters is the directive is present somewhere
        # in the block.
        self.assertRegex(block, r"(?i)do not recompute")
        # And it must NOT appear inside the per-vehicle line — the per-line
        # qualifier should be a clean (W.A.C.) only.
        per_line = [ln for ln in block.split("\n") if "$517" in ln]
        self.assertEqual(len(per_line), 1)
        self.assertNotIn("recompute", per_line[0].lower())
        self.assertNotIn("BUDGET ANALYSIS", per_line[0])

    def test_unannotated_vehicle_uses_default_estimate(self):
        v = _make_vehicle("UN-1", "26995", model="Ranger")
        block = _format_vehicle_block([v], budget_mode=False)
        # Default form on the keyword search path no longer leaks a rate —
        # it shows the term and the W.A.C. qualifier instead.
        self.assertIn("for 72 months", block)
        self.assertIn("W.A.C.", block)
        self.assertNotIn("7.49", block)
        self.assertNotIn("APR", block)

    def test_annotated_block_disclaimer_points_at_budget_analysis(self):
        v = _make_vehicle("ANN-2", "26995", model="Ranger")
        v._estimated_payment = 517.03
        v._budget_fit = "near_fit"
        v._payment_delta = 17.03
        block = _format_vehicle_block([v], budget_mode=True)
        self.assertIn("BUDGET ANALYSIS", block)
        self.assertIn("quote them exactly", block)


# ---- check_payment_consistency ------------------------------------------


class CheckPaymentConsistencyTests(SimpleTestCase):
    def test_no_payment_numbers_returns_empty(self):
        drift = check_payment_consistency(
            "These are some great trucks for you.",
            target_monthly=500,
            allowed_payments=[517.03],
        )
        self.assertEqual(drift, [])

    def test_matching_estimate_passes(self):
        drift = check_payment_consistency(
            "Estimated around $517/mo for the Ranger.",
            target_monthly=500,
            allowed_payments=[517.03],
        )
        self.assertEqual(drift, [])

    def test_target_payment_passes(self):
        drift = check_payment_consistency(
            "Your target is $500/month — let's see what fits.",
            target_monthly=500,
            allowed_payments=[517.03],
        )
        self.assertEqual(drift, [])

    def test_drift_flagged(self):
        # The exact reported bug: LLM quoted $498 when backend said $517.
        drift = check_payment_consistency(
            "Around $498/mo on a 72-month term.",
            target_monthly=500,
            allowed_payments=[517.03],
        )
        self.assertEqual(drift, [498.0])

    def test_per_a_month_phrasing_caught(self):
        drift = check_payment_consistency(
            "About $300 per month works.",
            target_monthly=500,
            allowed_payments=[517.03],
        )
        self.assertEqual(drift, [300.0])

    def test_close_within_tolerance_not_flagged(self):
        # $516 vs $517.03 → within $5 tolerance.
        drift = check_payment_consistency(
            "Around $516/mo.",
            target_monthly=500,
            allowed_payments=[517.03],
        )
        self.assertEqual(drift, [])

    def test_multiple_allowed_payments_any_matches(self):
        drift = check_payment_consistency(
            "Or about $720/mo for the bigger one.",
            target_monthly=500,
            allowed_payments=[517.03, 720.50],
        )
        self.assertEqual(drift, [])


# ---- ChatEngine integration --------------------------------------------


class ChatEnginePaymentConsistencyTests(TestCase):
    def test_inventory_block_sent_to_llm_uses_annotated_payment(self):
        """The bug: inventory block gave the LLM $498 (default 72mo) while
        BUDGET ANALYSIS gave $517 (60mo + $3k down). The LLM picked $498.
        Verify both blocks now agree."""
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(replies=[json_reply({}), "ack"])
        engine = ChatEngine(session=session, provider=provider)
        engine.handle_user_message("$500/mo, $3k down")

        sent = "\n".join(
            m["content"] for m in provider.calls[-1] if m["role"] == "system"
        )
        # The Ranger appears in BUDGET ANALYSIS at ~$517 — it must NOT also
        # appear in the inventory block at the engine-default $498.
        self.assertIn("$517", sent)
        self.assertNotIn("(60mo @ 7.49%)", sent)  # default-form disclosure gone
        self.assertNotIn("(72mo @ 7.49%)", sent)
        self.assertIn("BUDGET ANALYSIS", sent)
        # Both blocks discuss the same vehicle once.
        self.assertEqual(sent.count("FF-USED-104"), 2)  # once in BA, once in INV

    def test_payment_drift_flagged_when_llm_invents_lower_payment(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        # Mock LLM that hallucinates the wrong payment.
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Great match! Around $498/mo for the Ranger.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")
        bq = result.assistant_message.metadata.get("budget_query") or {}
        self.assertIn("payment_drift", bq)
        self.assertIn(498.0, bq["payment_drift"])

    def test_no_drift_flag_when_reply_uses_correct_payment(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Around $517/mo on the Ranger — close to your $500 target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")
        bq = result.assistant_message.metadata.get("budget_query") or {}
        self.assertNotIn("payment_drift", bq)

    def test_target_payment_in_reply_does_not_count_as_drift(self):
        """Quoting back the customer's own target ($500/mo) is NOT drift."""
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "I'll find what fits your $500/month target.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")
        bq = result.assistant_message.metadata.get("budget_query") or {}
        self.assertNotIn("payment_drift", bq)


# ---- scrub_payment_drift unit tests --------------------------------------


class ScrubPaymentDriftTests(SimpleTestCase):
    """Unit-level coverage for the post-detection scrub. Drift detection
    happens in `check_payment_consistency`; the scrub removes drift
    numbers from the customer-visible reply (Drift 2.a)."""

    def test_no_drift_returns_text_unchanged(self):
        text = "Around $517/mo for the Ranger."
        cleaned, changed = scrub_payment_drift(text, [])
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)

    def test_empty_text_returns_unchanged(self):
        cleaned, changed = scrub_payment_drift("", [498.0])
        self.assertEqual(cleaned, "")
        self.assertFalse(changed)

    def test_single_drift_per_mo_replaced(self):
        cleaned, changed = scrub_payment_drift(
            "Great match! Around $498/mo for the Ranger.", [498.0]
        )
        self.assertTrue(changed)
        self.assertNotIn("$498", cleaned)
        self.assertIn("the payment shown on the card", cleaned)

    def test_per_month_phrasing_replaced(self):
        cleaned, changed = scrub_payment_drift(
            "About $300 per month works.", [300.0]
        )
        self.assertTrue(changed)
        self.assertNotIn("$300", cleaned)

    def test_a_month_phrasing_replaced(self):
        cleaned, changed = scrub_payment_drift(
            "Around $498 a month for the Ranger.", [498.0]
        )
        self.assertTrue(changed)
        self.assertNotIn("$498", cleaned)

    def test_monthly_phrasing_replaced(self):
        cleaned, changed = scrub_payment_drift(
            "About $498 monthly works.", [498.0]
        )
        self.assertTrue(changed)
        self.assertNotIn("$498", cleaned)

    def test_drift_does_not_touch_other_payments(self):
        # Reply contains both a drift number ($498) and a legitimate
        # payment ($517). Only the drift one should be rewritten —
        # the scrub must NEVER blanket-strip $X/mo numbers.
        cleaned, changed = scrub_payment_drift(
            "The Ranger lands at about $517/mo, not $498/mo.",
            [498.0],
        )
        self.assertTrue(changed)
        self.assertIn("$517/mo", cleaned)
        self.assertNotIn("$498", cleaned)

    def test_multi_digit_comma_form_matches_no_comma_form(self):
        # Drift number 1498 — reply may contain $1,498 OR $1498.
        # Both must scrub.
        cleaned, changed = scrub_payment_drift(
            "About $1,498/mo for the Limited.", [1498.0]
        )
        self.assertTrue(changed)
        self.assertNotIn("$1,498", cleaned)
        cleaned2, changed2 = scrub_payment_drift(
            "About $1498/mo for the Limited.", [1498.0]
        )
        self.assertTrue(changed2)
        self.assertNotIn("$1498", cleaned2)

    def test_multiple_drift_numbers_all_replaced(self):
        cleaned, changed = scrub_payment_drift(
            "Maybe $498/mo or $486/mo for either truck.",
            [498.0, 486.0],
        )
        self.assertTrue(changed)
        self.assertNotIn("$498", cleaned)
        self.assertNotIn("$486", cleaned)
        # Replacement phrase appears twice.
        self.assertEqual(
            cleaned.count("the payment shown on the card"), 2
        )

    def test_bare_dollar_without_unit_not_scrubbed(self):
        # Out of scope for this pass — `_PAYMENT_NUMBER_RE` ignores
        # unit-less amounts, so the scrub should match. Documents the
        # known gap.
        cleaned, changed = scrub_payment_drift(
            "It's around $498 for the Ranger.", [498.0]
        )
        self.assertFalse(changed)
        self.assertEqual(cleaned, "It's around $498 for the Ranger.")


# ---- ChatEngine integration: drift no longer reaches customer ------------


class DriftReachesCustomerScrubTests(TestCase):
    """Integration coverage for Drift 2.b — the customer-visible
    `assistant_message.content` must not carry the drift number, while
    the audit trail (`metadata.budget_query.payment_drift`) preserves
    the original detection so operators can inspect it.
    """

    def test_customer_reply_no_longer_contains_drift_number(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Great match! Around $498/mo for the Ranger.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")

        # The number the LLM hallucinated must be gone from the
        # reply the customer sees.
        self.assertNotIn("$498", result.assistant_message.content)
        # Replaced with the non-numeric phrase, not another payment.
        self.assertIn(
            "the payment shown on the card",
            result.assistant_message.content,
        )

    def test_audit_trail_preserves_original_drift(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Great match! Around $498/mo for the Ranger.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")

        bq = result.assistant_message.metadata.get("budget_query") or {}
        # Drift detection still records the original number for audit.
        self.assertIn("payment_drift", bq)
        self.assertIn(498.0, bq["payment_drift"])

    def test_metadata_flag_signals_scrub_fired(self):
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "Great match! Around $498/mo for the Ranger.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")

        meta = result.assistant_message.metadata
        self.assertEqual(meta.get("flag"), "payment_drift_scrubbed")
        self.assertIn("payment_drift", meta.get("scrubs", []))

    def test_correct_payment_reply_unchanged_and_unflagged(self):
        # Sanity: when the reply is clean, the scrub doesn't fire and
        # no drift flag is set. Mirrors
        # test_no_drift_flag_when_reply_uses_correct_payment but pins
        # the customer-visible content too.
        _make_vehicle("FF-USED-104", "26995", model="Ranger")
        session = ChatSession.objects.create(
            extracted_profile={
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
            }
        )
        clean_reply = (
            "Around $517/mo on the Ranger — close to your $500 target."
        )
        provider = MockLLMProvider(
            replies=[json_reply({}), clean_reply]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down")

        self.assertEqual(result.assistant_message.content, clean_reply)
        bq = result.assistant_message.metadata.get("budget_query") or {}
        self.assertNotIn("payment_drift", bq)
        self.assertNotEqual(
            result.assistant_message.metadata.get("flag"),
            "payment_drift_scrubbed",
        )


# ---- scrub_extra_payment_quotes unit tests --------------------------------


class ScrubExtraPaymentQuotesTests(SimpleTestCase):
    """Unit coverage for the one-payment-quote rule. The cards are
    the source of truth for payments; prose may quote ONE (the lead).
    Extra ``$X/mo`` quotes that match real card payments get replaced
    with the same non-numeric phrase the drift scrub uses.

    Customer-target quotes ("your $500/mo target") are NOT extras —
    BEHAVIOR_LAYER explicitly permits echoing the customer's own
    target back at them.
    """

    ALLOWED = [517.0, 609.0, 486.0]
    TARGET = 500.0
    PHRASE = "the payment shown on the card"

    def test_no_quotes_returns_unchanged(self):
        text = "Lots of great trucks for you."
        cleaned, changed, n = scrub_extra_payment_quotes(
            text,
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(n, 0)

    def test_single_quote_returns_unchanged(self):
        # The whole point of the rule: ONE quote is allowed.
        text = "The Ranger is really close at about $517/mo."
        cleaned, changed, n = scrub_extra_payment_quotes(
            text,
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(n, 0)

    def test_two_card_quotes_first_kept_second_replaced(self):
        cleaned, changed, n = scrub_extra_payment_quotes(
            "The Ranger is at $517/mo and the Tundra is at $609/mo.",
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertTrue(changed)
        self.assertEqual(n, 1)
        self.assertIn("$517/mo", cleaned)
        self.assertNotIn("$609", cleaned)
        self.assertIn(self.PHRASE, cleaned)

    def test_three_card_quotes_first_kept_others_replaced(self):
        cleaned, changed, n = scrub_extra_payment_quotes(
            "The Ranger at $517/mo, Tundra at $609/mo, Colorado at $486/mo.",
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertTrue(changed)
        self.assertEqual(n, 2)
        self.assertIn("$517/mo", cleaned)
        self.assertNotIn("$609", cleaned)
        self.assertNotIn("$486", cleaned)
        self.assertEqual(cleaned.count(self.PHRASE), 2)

    def test_target_quote_plus_one_card_quote_unchanged(self):
        # $500/mo is the customer's target — doesn't count as extra.
        # Exactly ONE card quote ($517/mo) → no replacement.
        text = (
            "Your $500/mo target is doable — the Ranger lands at about "
            "$517/mo."
        )
        cleaned, changed, n = scrub_extra_payment_quotes(
            text,
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(n, 0)

    def test_target_between_two_card_quotes_target_untouched(self):
        cleaned, changed, n = scrub_extra_payment_quotes(
            "The Ranger at $517/mo is close to your $500/month target, "
            "and the Tundra at $609/mo opens up too.",
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertTrue(changed)
        self.assertEqual(n, 1)
        self.assertIn("$517/mo", cleaned)
        self.assertIn("$500/month", cleaned)  # target preserved
        self.assertNotIn("$609", cleaned)

    def test_drift_number_left_alone(self):
        # $498 is NOT in allowed_payments — that's drift territory and
        # `scrub_payment_drift` runs upstream. The extra-quote scrub
        # must not act on it (otherwise it would double-replace).
        text = "The Ranger at $517/mo (model said $498/mo)."
        cleaned, changed, n = scrub_extra_payment_quotes(
            text,
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertEqual(cleaned, text)
        self.assertFalse(changed)
        self.assertEqual(n, 0)

    def test_repeated_same_card_payment_first_kept_rest_replaced(self):
        cleaned, changed, n = scrub_extra_payment_quotes(
            "The Ranger at $517/mo. Yes, the Ranger at $517/mo.",
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertTrue(changed)
        self.assertEqual(n, 1)
        self.assertEqual(cleaned.count("$517/mo"), 1)

    def test_per_month_phrasing_counted(self):
        cleaned, changed, n = scrub_extra_payment_quotes(
            "The Ranger at $517 per month and the Tundra at $609/mo.",
            target_monthly=self.TARGET,
            allowed_payments=self.ALLOWED,
        )
        self.assertTrue(changed)
        self.assertEqual(n, 1)
        self.assertIn("$517 per month", cleaned)
        self.assertNotIn("$609", cleaned)


# ---- ChatEngine integration: extra-payment-quote scrub --------------------


class ExtraPaymentQuoteIntegrationTests(TestCase):
    """End-to-end coverage for the one-payment-quote rule (item 1
    follow-on to Drift 2.a). Pins the customer-visible
    ``assistant_message.content`` and the audit metadata together —
    the contract is enforced at both surfaces.

    Setup uses a single Ranger so the engine's classifier produces
    one known card payment ($517/mo for $26,995 / $500 / $3k / 60mo);
    the tests then build mocked replies that quote that number once,
    twice, or alongside drift to exercise each scrub path.
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

    def test_clean_single_payment_reply_unchanged(self):
        # User spec test #1 — one payment quote remains untouched.
        session = self._ranger_session()
        clean = (
            "The Ranger is really close at about $517/mo. Want me to "
            "line one up?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), clean])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        meta = result.assistant_message.metadata
        self.assertEqual(result.assistant_message.content, clean)
        self.assertNotIn(
            "extra_payment_quote", meta.get("scrubs", [])
        )
        self.assertNotEqual(
            meta.get("flag"), "extra_payment_quote_scrubbed"
        )

    def test_multi_card_payment_reply_keeps_lead_only(self):
        # User spec test #2 — two+ valid payment quotes get scrubbed.
        # Both quotes are the same valid card payment ($517) so the
        # extra-quote scrub fires alone (no drift).
        session = self._ranger_session()
        bad = (
            "The Ranger is at $517/mo. Yes, the Ranger comes in at "
            "$517/mo over a 60-month term. Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        # First $517/mo kept (lead); second replaced with the phrase.
        self.assertEqual(content.count("$517/mo"), 1)
        self.assertIn("the payment shown on the card", content)
        meta = result.assistant_message.metadata
        self.assertIn(
            "extra_payment_quote", meta.get("scrubs", [])
        )
        # Only this scrub fired, so the flag is its single-scrub form.
        self.assertEqual(
            meta.get("flag"), "extra_payment_quote_scrubbed"
        )

    def test_drift_and_extra_both_fire_promotes_flag(self):
        # User spec test #3 — invalid drift still uses
        # payment_drift_scrubbed, AND when an extra valid payment is
        # ALSO quoted in the same reply, both scrubs run and the
        # flag promotes to ``multiple_scrubs_fired``. Reply has
        # 1 drift ($498) + 2 valid card quotes ($517, $517) so each
        # scrub has work to do after the other one runs.
        session = self._ranger_session()
        bad = (
            "Around $498/mo on the Ranger. Actually, the Ranger is "
            "right at $517/mo, and the Ranger again at $517/mo over "
            "60 months. Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), bad])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        # Drift number gone.
        self.assertNotIn("$498", content)
        # Lead $517/mo preserved exactly once; second occurrence
        # replaced with the non-numeric phrase.
        self.assertEqual(content.count("$517/mo"), 1)
        meta = result.assistant_message.metadata
        scrubs = meta.get("scrubs", [])
        self.assertIn("payment_drift", scrubs)
        self.assertIn("extra_payment_quote", scrubs)
        # Flag invariant: ≥ 2 scrubs ⇒ multiple_scrubs_fired.
        self.assertEqual(meta.get("flag"), "multiple_scrubs_fired")
        # Audit trail preserves the original drift number.
        bq = meta.get("budget_query") or {}
        self.assertIn(498.0, bq.get("payment_drift", []))

    def test_customer_target_quote_does_not_count_as_extra(self):
        # User spec test #4 — cards/source-of-truth contract
        # preserved. The customer's own target ($500/mo) plus ONE
        # card payment ($517/mo) is permitted; nothing scrubbed.
        session = self._ranger_session()
        ok = (
            "Your $500/month target is workable — the Ranger lands "
            "right around $517/mo. Want a closer look?"
        )
        provider = MockLLMProvider(replies=[json_reply({}), ok])
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        content = result.assistant_message.content
        self.assertIn("$500/month", content)  # target preserved
        self.assertIn("$517/mo", content)     # lead card preserved
        meta = result.assistant_message.metadata
        self.assertNotIn(
            "extra_payment_quote", meta.get("scrubs", [])
        )

    def test_no_inventory_or_payment_engine_changes(self):
        # User spec test #5 — scrubs do not touch matched_vehicles,
        # cards' annotated payments, or budget classification. The
        # deterministic backend data flowing to the frontend is
        # identical regardless of what the LLM produced.
        session = self._ranger_session()
        provider = MockLLMProvider(
            replies=[
                json_reply({}),
                "The Ranger at $517/mo. Yes, the Ranger at $517/mo.",
            ]
        )
        engine = ChatEngine(session=session, provider=provider)
        result = engine.handle_user_message("$500/mo, $3k down, truck")

        # matched_vehicles still surfaces the truck with its
        # authoritative payment (scrub only touched PROSE).
        stocks = [v.stock_number for v in result.matched_vehicles]
        self.assertEqual(stocks, ["FF-USED-104"])
        for v in result.matched_vehicles:
            self.assertIsNotNone(
                getattr(v, "_estimated_payment", None)
            )
            self.assertIn(
                getattr(v, "_budget_fit", None),
                ("fit", "near_fit", "over_budget"),
            )
