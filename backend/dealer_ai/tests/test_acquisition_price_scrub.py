"""Milestone 2 · Increment 5 — acquisition-price scrub tests.

Defense-in-depth against internal cost / investment figures leaking
into customer-facing AI output.

**Relationship to the pre-existing dealer-cost detector.** Some
cost-ownership phrases ("we paid", "our cost") are already caught
by ``chat_engine._RESPONSE_FORBIDDEN_PATTERNS`` — the wholesale-
rewrite class that returns ``dropped_reason="dealer_cost_safety"``.
Because ``apply_post_llm_scrubs`` runs the wholesale-rewrite check
first, those phrases short-circuit before the acquisition-price
scrub ever runs. That precedence is CORRECT — a wholesale rewrite
is a stronger safety response than a partial scrub, and locking
the precedence keeps the safety stack's ordering guarantees intact
(the SESSION_051 brief explicitly required this).

The M2.5 scrub therefore adds coverage for cost-ownership phrases
NOT in ``_RESPONSE_FORBIDDEN_PATTERNS``:

- "we're in it for $X" / "we are in it for $X"
- "we've got $X in this vehicle" / "we have $X in the unit"
- "purchase price was $X" / "purchase price of $X"
- "our purchase price"
- "acquired for $X" / "acquired at $X"
- "total investment $X" / "our total investment is $X"
- "our investment in this <vehicle-word>"
- "floor plan interest" / "floor-plan interest"
- "we spent $X on recon" / "spent $X on reconditioning"
- "recon costs were $X" / "reconditioning expenses of $X"

Two responsibilities held equal:

1. **Positive** — every phrase family unique to this scrub triggers
   ``acquisition_price`` in ``scrubs_fired``.
2. **Negative** — a broad legitimate-customer-language corpus does
   NOT trigger the scrub. This is the load-bearing part per the
   SESSION_051 brief: "a scrub that damages valid pricing language
   breaks the product today."

Also verified:

- Precedence: existing wholesale rewrites (dealer-cost, negotiation)
  still fire first and short-circuit the pipeline.
- The scrub's redundant patterns for "we paid" / "our cost" are
  defensive — they will never fire under current conditions but
  document the M2.5 scrub's coverage intent so a future session
  that loosens ``_RESPONSE_FORBIDDEN_PATTERNS`` gets automatic
  defense-in-depth.
- Text-only guarantee: ``_scrub_acquisition_price`` makes zero DB
  queries.
"""

from __future__ import annotations

from django.test import TestCase

from dealer_ai.services.llm_safety import (
    _scrub_acquisition_price,
    apply_post_llm_scrubs,
)

ALL_KINDS = ("chat", "vehicle_ask", "ad", "follow_up")


# ---- Positive: phrase families unique to the acquisition_price scrub -----


class PositivePhraseFamilies(TestCase):
    """Each phrase family from planning §1.5 that is NOT already
    caught by ``_RESPONSE_FORBIDDEN_PATTERNS`` (dealer-cost
    wholesale rewrite) should trigger the acquisition_price partial
    scrub."""

    def _assert_scrub_fired(self, text: str, kind: str = "chat") -> str:
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind=kind)
        # Must not be a wholesale drop; acquisition_price is a
        # partial scrub only.
        self.assertIsNone(
            dropped,
            f"unexpected wholesale drop for {text!r}: {dropped!r}",
        )
        self.assertIn(
            "acquisition_price",
            scrubs,
            f"acquisition_price scrub did NOT fire on {text!r} "
            f"(scrubs_fired={scrubs}, cleaned={cleaned!r})",
        )
        return cleaned

    # --- "in it for" family --------------------------------------------

    def test_we_are_in_it_for(self):
        cleaned = self._assert_scrub_fired(
            "We are in it for $19,550 including transport."
        )
        self.assertNotIn("$19,550", cleaned)

    def test_were_in_it_for_contraction(self):
        cleaned = self._assert_scrub_fired(
            "We're in it for $19,550 total on this piece."
        )
        self.assertNotIn("$19,550", cleaned)

    def test_were_in_this_for(self):
        # "in this for" variant.
        cleaned = self._assert_scrub_fired(
            "We're in this for $17,200 all-in."
        )
        self.assertNotIn("$17,200", cleaned)

    # --- "we've got $X in" family --------------------------------------

    def test_weve_got_in_this_vehicle(self):
        cleaned = self._assert_scrub_fired(
            "We've got $20,300 in this vehicle already."
        )
        self.assertNotIn("$20,300", cleaned)

    def test_we_have_in_the_unit(self):
        cleaned = self._assert_scrub_fired(
            "We have $16,750 in the unit today."
        )
        self.assertNotIn("$16,750", cleaned)

    def test_weve_got_in_this_truck(self):
        cleaned = self._assert_scrub_fired(
            "We've got $18,000 in this truck between acquisition and recon."
        )
        self.assertNotIn("$18,000", cleaned)

    # --- "purchase price" family ---------------------------------------

    def test_purchase_price_was(self):
        cleaned = self._assert_scrub_fired(
            "The purchase price was $18,000 at the auction."
        )
        self.assertNotIn("$18,000", cleaned)

    def test_purchase_price_of(self):
        cleaned = self._assert_scrub_fired(
            "The purchase price of $18,000 covered the initial buy."
        )
        self.assertNotIn("$18,000", cleaned)

    def test_our_purchase_price_any_tense(self):
        cleaned = self._assert_scrub_fired(
            "Our purchase price is $17,500 on this piece."
        )
        self.assertNotIn("$17,500", cleaned)

    def test_our_purchase_price_no_amount(self):
        # Ownership language even without an explicit amount is a
        # cost-leakage signal.
        self._assert_scrub_fired(
            "Our purchase price won't be shared publicly."
        )

    # --- "acquired for/at" family --------------------------------------

    def test_acquired_for(self):
        cleaned = self._assert_scrub_fired(
            "We acquired this for $12,900 back in May."
        )
        self.assertNotIn("$12,900", cleaned)

    def test_acquired_at(self):
        cleaned = self._assert_scrub_fired(
            "Acquired at $9,200 last month."
        )
        self.assertNotIn("$9,200", cleaned)

    def test_acquired_the_vehicle(self):
        cleaned = self._assert_scrub_fired(
            "Acquired the vehicle for $14,800 in a wholesale deal."
        )
        self.assertNotIn("$14,800", cleaned)

    # --- "total investment" family -------------------------------------

    def test_total_investment_is(self):
        cleaned = self._assert_scrub_fired(
            "Our total investment is $22,000 across acquisition and recon."
        )
        self.assertNotIn("$22,000", cleaned)

    def test_total_investment_bare_amount(self):
        cleaned = self._assert_scrub_fired(
            "Total investment $21,030 on this Ranger."
        )
        self.assertNotIn("$21,030", cleaned)

    def test_total_investment_of(self):
        cleaned = self._assert_scrub_fired(
            "Total investment of $19,475 makes this a strong margin unit."
        )
        self.assertNotIn("$19,475", cleaned)

    # --- "our investment in this" family --------------------------------

    def test_our_investment_in_this_vehicle_no_amount(self):
        # No dollar amount — verbal framing alone is the signal.
        self._assert_scrub_fired(
            "Our investment in this vehicle drives our pricing decisions."
        )

    def test_our_investment_in_the_piece_with_amount(self):
        cleaned = self._assert_scrub_fired(
            "Our investment in the piece is $19,475 to date."
        )
        self.assertNotIn("$19,475", cleaned)

    # --- "floor plan interest" family -----------------------------------

    def test_floor_plan_interest_bare(self):
        # No dollar figure — the term itself is 100% internal.
        cleaned = self._assert_scrub_fired(
            "Floor plan interest is accruing daily on aged inventory."
        )
        self.assertNotIn("Floor plan interest", cleaned)
        self.assertNotIn("floor plan interest", cleaned)

    def test_floor_plan_interest_with_amount(self):
        cleaned = self._assert_scrub_fired(
            "The floor-plan interest of $387.74 lands next week."
        )
        self.assertNotIn("$387.74", cleaned)

    def test_floor_plan_interest_hyphenated_variant(self):
        cleaned = self._assert_scrub_fired(
            "Floor-plan interest totals $500 for the month."
        )
        self.assertNotIn("$500", cleaned)

    # --- "spent on recon" family ----------------------------------------

    def test_we_spent_on_recon(self):
        cleaned = self._assert_scrub_fired(
            "We spent $850 on recon before listing this truck."
        )
        self.assertNotIn("$850", cleaned)

    def test_spent_on_reconditioning(self):
        cleaned = self._assert_scrub_fired(
            "Spent $1,240 on reconditioning to bring it up to standard."
        )
        self.assertNotIn("$1,240", cleaned)

    def test_recon_costs_were(self):
        cleaned = self._assert_scrub_fired(
            "Recon costs were $920 on this SUV."
        )
        self.assertNotIn("$920", cleaned)

    def test_reconditioning_expenses_of(self):
        cleaned = self._assert_scrub_fired(
            "Reconditioning expenses of $640 covered brakes and tires."
        )
        self.assertNotIn("$640", cleaned)


# ---- Positive: variants (capitalization / punctuation / etc) --------------


class PositiveVariants(TestCase):
    """Capitalization, punctuation, contractions, spacing — the
    scrub is case-insensitive and tolerant of common variants.

    Uses phrase families unique to acquisition_price (not "we paid"
    or "our cost" which pre-existing wholesale rewrite catches
    first)."""

    def _assert_fires(self, text: str) -> None:
        _, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertIsNone(dropped)
        self.assertIn(
            "acquisition_price",
            scrubs,
            f"scrub did not fire on variant: {text!r}",
        )

    def test_all_caps_variant(self):
        self._assert_fires("PURCHASE PRICE WAS $18,000 AT THE AUCTION.")

    def test_title_case_variant(self):
        self._assert_fires("Total Investment Is $22,000 On This Truck.")

    def test_mixed_case_variant(self):
        self._assert_fires("wE'rE iN iT fOr $19,550 total.")

    def test_comma_inside_amount(self):
        self._assert_fires("We're in it for $19,550 total.")

    def test_amount_without_thousand_separator(self):
        self._assert_fires("We're in it for $19550 total.")

    def test_amount_with_decimal(self):
        self._assert_fires("Floor plan interest of $387.74 accrued.")

    def test_amount_without_dollar_sign(self):
        # Pattern matches with optional $ so bare-number leakage
        # still fires.
        self._assert_fires("Total investment 22000 on this SUV.")

    def test_extra_whitespace_between_dollar_and_amount(self):
        self._assert_fires("Total investment $ 22,000 on this SUV.")


# ---- Positive: multiple leakages in one response --------------------------


class PositiveMultipleLeakagesInOneResponse(TestCase):
    def test_multiple_acquisition_price_phrases_all_stripped(self):
        # Both phrases are acquisition_price patterns (NOT the
        # wholesale-rewrite "we paid" / "our cost" phrases).
        text = (
            "We acquired this for $12,900 back in May. "
            "Our total investment is $21,030 including recon. "
            "The vehicle is priced at $24,900."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertIsNone(dropped)
        self.assertIn("acquisition_price", scrubs)
        # Both internal-cost figures gone.
        self.assertNotIn("$12,900", cleaned)
        self.assertNotIn("$21,030", cleaned)
        # Legitimate customer-facing price survives.
        self.assertIn("$24,900", cleaned)


# ---- Positive: fires for every currently-supported kind -------------------


class PositiveFiresForEveryKind(TestCase):
    """Ledger leakage is equally wrong on every current output kind."""

    _PHRASE = "Total investment $22,000 on this truck."

    def test_fires_on_chat_kind(self):
        _, scrubs, _ = apply_post_llm_scrubs(self._PHRASE, kind="chat")
        self.assertIn("acquisition_price", scrubs)

    def test_fires_on_vehicle_ask_kind(self):
        _, scrubs, _ = apply_post_llm_scrubs(self._PHRASE, kind="vehicle_ask")
        self.assertIn("acquisition_price", scrubs)

    def test_fires_on_ad_kind(self):
        _, scrubs, _ = apply_post_llm_scrubs(self._PHRASE, kind="ad")
        self.assertIn("acquisition_price", scrubs)

    def test_fires_on_follow_up_kind(self):
        _, scrubs, _ = apply_post_llm_scrubs(self._PHRASE, kind="follow_up")
        self.assertIn("acquisition_price", scrubs)


# ---- Positive: remaining response is coherent -----------------------------


class PositiveCoherentRemainder(TestCase):
    """After the scrub fires, the rest of the response should still
    read cleanly — no double spaces, no orphan punctuation."""

    def test_replacement_leaves_no_double_space(self):
        text = "Purchase price was $18,000. Priced at $24,900."
        cleaned, _, _ = apply_post_llm_scrubs(text, kind="chat")
        self.assertNotIn("  ", cleaned)

    def test_replacement_leaves_no_orphan_space_before_period(self):
        text = "Our total investment is $22,000."
        cleaned, _, _ = apply_post_llm_scrubs(text, kind="chat")
        self.assertNotIn(" .", cleaned)
        self.assertNotIn(" ,", cleaned)


# ---- Precedence: existing wholesale rewrites still win --------------------


class PrecedencePreservedForExistingWholesaleRewrites(TestCase):
    """The pre-existing ``_RESPONSE_FORBIDDEN_PATTERNS`` (dealer-
    cost family) fires FIRST via ``detect_unsafe_response`` and
    short-circuits the pipeline. Phrases like "we paid" and "our
    cost" are covered by that older wholesale rewrite; the
    acquisition-price scrub NEVER runs on them under current
    conditions.

    Locking this precedence explicitly per SESSION_051 brief:
    "preserve existing precedence."
    """

    def test_we_paid_phrase_triggers_dealer_cost_wholesale_rewrite(self):
        text = "We paid $18,500 for this truck at auction."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        # Wholesale rewrite fires and short-circuits — text unchanged,
        # scrubs list empty.
        self.assertEqual(dropped, "dealer_cost_safety")
        self.assertEqual(scrubs, [])
        self.assertEqual(cleaned, text)

    def test_our_cost_phrase_triggers_dealer_cost_wholesale_rewrite(self):
        text = "Our cost on this SUV was $22,000."
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertEqual(dropped, "dealer_cost_safety")
        self.assertEqual(scrubs, [])
        self.assertEqual(cleaned, text)

    def test_dealer_cost_wins_over_acquisition_price_when_both_present(self):
        # Text contains BOTH a dealer-cost wholesale-rewrite phrase
        # AND an acquisition_price-family phrase. Wholesale rewrite
        # wins.
        text = (
            "Our dealer cost is about $52,000. Total investment "
            "is $55,000 including recon."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertEqual(dropped, "dealer_cost_safety")
        self.assertEqual(scrubs, [])
        self.assertEqual(cleaned, text)

    def test_negotiation_wholesale_rewrite_still_wins(self):
        # Negotiation phrase + acquisition_price phrase — negotiation
        # wholesale rewrite wins.
        text = (
            "I can match that price for you at $48,000. Total "
            "investment is $45,000 on this piece."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertEqual(dropped, "post_llm_override:negotiation")
        self.assertEqual(scrubs, [])
        self.assertEqual(cleaned, text)

    def test_rate_language_scrub_still_fires_alongside(self):
        # Non-wholesale text — rate_language partial + acquisition_price
        # partial both fire.
        text = (
            "Estimated $450/mo at 7.49% APR over 60 months. Total "
            "investment $18,500 on this truck."
        )
        cleaned, scrubs, dropped = apply_post_llm_scrubs(text, kind="chat")
        self.assertIsNone(dropped)
        self.assertIn("rate_language", scrubs)
        self.assertIn("acquisition_price", scrubs)
        self.assertNotIn("7.49%", cleaned)
        self.assertNotIn("$18,500", cleaned)


# ---- Negative corpus: legitimate customer language MUST NOT trigger -------


class NegativeCorpusLegitimateCustomerLanguage(TestCase):
    """The load-bearing part of the increment. Any of these firing
    would break real chat / vehicle_ask / ad / follow_up flows.

    Each case checks: ``acquisition_price`` NOT in ``scrubs_fired``
    for every current kind. Customer-facing dollar amounts survive
    unchanged where they should.
    """

    def _assert_scrub_did_not_fire(
        self, text: str, expected_dollars: tuple = ()
    ) -> None:
        for kind in ALL_KINDS:
            cleaned, scrubs, dropped = apply_post_llm_scrubs(
                text, kind=kind
            )
            self.assertNotIn(
                "acquisition_price",
                scrubs,
                f"acquisition_price fired incorrectly on kind={kind} "
                f"for text: {text!r}\ncleaned={cleaned!r}",
            )
            for amount in expected_dollars:
                # Skip amounts other scrubs may legitimately remove
                # (e.g. invented_promotion on ad/follow_up).
                if kind in ("ad", "follow_up") and "invented_promotion" in scrubs:
                    continue
                self.assertIn(
                    amount,
                    cleaned,
                    f"customer-facing amount {amount!r} was removed "
                    f"on kind={kind} for text: {text!r} → {cleaned!r}",
                )

    def test_asking_price(self):
        self._assert_scrub_did_not_fire(
            "This truck is asking $18,500 today.",
            expected_dollars=("$18,500",),
        )

    def test_priced_at(self):
        self._assert_scrub_did_not_fire(
            "The 2024 Ranger is priced at $24,900 out the door.",
            expected_dollars=("$24,900",),
        )

    def test_sale_price(self):
        self._assert_scrub_did_not_fire(
            "The sale price is $22,750 including all fees.",
            expected_dollars=("$22,750",),
        )

    def test_monthly_payment(self):
        # "$450/mo at 7.49% APR" would trip rate_language, so we
        # test the payment phrasing alone.
        self._assert_scrub_did_not_fire(
            "Your monthly payment is around $450 based on your target.",
            expected_dollars=("$450",),
        )

    def test_down_payment(self):
        self._assert_scrub_did_not_fire(
            "A $2,000 down payment brings the monthly payment down.",
            expected_dollars=("$2,000",),
        )

    def test_zero_down(self):
        # "$0 down" is caught by invented_promotion on ad/follow_up
        # kinds but MUST NOT be caught by acquisition_price on any
        # kind.
        for kind in ALL_KINDS:
            _, scrubs, _ = apply_post_llm_scrubs("$0 down today.", kind=kind)
            self.assertNotIn("acquisition_price", scrubs)

    def test_save_amount(self):
        for kind in ALL_KINDS:
            _, scrubs, _ = apply_post_llm_scrubs(
                "Save $1,000 on your next purchase.", kind=kind
            )
            self.assertNotIn("acquisition_price", scrubs)

    def test_trade_value(self):
        self._assert_scrub_did_not_fire(
            "Your estimated trade value is around $8,500 based on recent comps.",
            expected_dollars=("$8,500",),
        )

    def test_budget(self):
        self._assert_scrub_did_not_fire(
            "Your budget is around $20,000 — here are some options.",
            expected_dollars=("$20,000",),
        )

    def test_discount(self):
        self._assert_scrub_did_not_fire(
            "There's a $500 discount available on select models today.",
            expected_dollars=("$500",),
        )

    def test_apr_and_taxes(self):
        # APR itself trips rate_language scrub; we're only checking
        # that acquisition_price doesn't overreach.
        for kind in ALL_KINDS:
            _, scrubs, _ = apply_post_llm_scrubs(
                "Figure in about $2,500 in fees and taxes on this purchase.",
                kind=kind,
            )
            self.assertNotIn("acquisition_price", scrubs)

    def test_warranty_price(self):
        self._assert_scrub_did_not_fire(
            "The extended warranty costs $1,200 for 3 years / 36,000 miles.",
            expected_dollars=("$1,200",),
        )

    def test_product_pricing(self):
        self._assert_scrub_did_not_fire(
            "The GAP product is $795 and the T&W package is $499.",
            expected_dollars=("$795", "$499"),
        )

    def test_affordability_language(self):
        self._assert_scrub_did_not_fire(
            "This F-150 fits well within your $22,000 budget.",
            expected_dollars=("$22,000",),
        )

    def test_customer_asks_about_price(self):
        self._assert_scrub_did_not_fire(
            "What's the asking price on the blue F-150?"
        )

    def test_customer_bring_this_amount(self):
        self._assert_scrub_did_not_fire(
            "Bring $2,500 to cover the down payment plus doc fees.",
            expected_dollars=("$2,500",),
        )

    def test_registration_fee_paid_on_behalf(self):
        # "We paid $500 to the DMV on your behalf" — a legitimate
        # disclosure about a customer bill. NOTE: this DOES trigger
        # the pre-existing dealer_cost_safety wholesale rewrite
        # (which catches "we paid" generically). We only assert
        # that acquisition_price doesn't fire — the wholesale
        # rewrite is out of M2.5's scope but its behavior is
        # correct.
        for kind in ALL_KINDS:
            _, scrubs, _ = apply_post_llm_scrubs(
                "We paid $500 to the DMV on your behalf for your registration.",
                kind=kind,
            )
            self.assertNotIn("acquisition_price", scrubs)

    def test_our_current_pricing_phrase_survives(self):
        # "our current pricing" is a replacement phrase the scrub
        # itself uses — it must not trigger a re-match if it appears
        # in the input.
        self._assert_scrub_did_not_fire(
            "Our current pricing on this F-150 reflects the market.",
        )

    def test_the_warranty_costs(self):
        # "costs" is a verb here (not "our cost"). Must not fire.
        self._assert_scrub_did_not_fire(
            "The bumper-to-bumper warranty costs $1,200 over 36 months.",
            expected_dollars=("$1,200",),
        )

    def test_customer_facing_investment_phrase(self):
        # "Your investment in reliability" is customer-side framing —
        # our scrub anchors on "OUR investment" specifically to
        # avoid this false-positive family.
        self._assert_scrub_did_not_fire(
            "Your investment in reliability starts with a good used vehicle."
        )

    def test_purchase_price_is_customer_facing(self):
        # "Purchase price IS $X" could be customer-facing sticker
        # phrasing — the scrub deliberately does NOT match "is",
        # only "was" and "of". Locks that boundary.
        self._assert_scrub_did_not_fire(
            "The purchase price is $18,500 for the 2024 F-150.",
            expected_dollars=("$18,500",),
        )


# ---- Public-signature stability ------------------------------------------


class PublicSignatureUnchanged(TestCase):
    """``apply_post_llm_scrubs`` still returns the same three-tuple
    shape and accepts the same ``kind`` values it did pre-M2.5."""

    def test_return_shape_is_three_tuple(self):
        result = apply_post_llm_scrubs("Hello world.", kind="chat")
        self.assertEqual(len(result), 3)
        cleaned, scrubs, dropped = result
        self.assertIsInstance(cleaned, str)
        self.assertIsInstance(scrubs, list)
        self.assertIsNone(dropped)

    def test_all_four_kinds_still_accepted(self):
        for kind in ALL_KINDS:
            cleaned, scrubs, dropped = apply_post_llm_scrubs(
                "Hello world.", kind=kind
            )
            self.assertEqual(cleaned, "Hello world.")
            self.assertEqual(scrubs, [])
            self.assertIsNone(dropped)

    def test_empty_input_still_short_circuits(self):
        cleaned, scrubs, dropped = apply_post_llm_scrubs("", kind="chat")
        self.assertEqual(cleaned, "")
        self.assertEqual(scrubs, [])
        self.assertIsNone(dropped)


# ---- Determinism + no side effects ---------------------------------------


class DeterministicAndSideEffectFree(TestCase):
    def test_identical_input_produces_identical_output(self):
        text = "Total investment $22,000 on this truck."
        first = apply_post_llm_scrubs(text, kind="chat")
        second = apply_post_llm_scrubs(text, kind="chat")
        self.assertEqual(first, second)

    def test_scrub_is_pure_no_db_access(self):
        # Text-only guarantee: ``_scrub_acquisition_price`` itself
        # must not touch the DB. Call the scrub directly (not through
        # ``apply_post_llm_scrubs`` which also invokes
        # ``get_dealer_profile()`` for the indie-prohibited gate).
        text = "Total investment $22,000 on this truck."
        with self.assertNumQueries(0):
            _scrub_acquisition_price(text)
