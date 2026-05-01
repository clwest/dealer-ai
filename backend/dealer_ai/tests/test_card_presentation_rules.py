"""Phase 8s/UX presentation refinement — card-deduplication contract.

Cards already render price, mileage, Stock #, features, badges, and
flex captions. The reply-rule preamble forbids the LLM from re-
rendering that data, capped at 3-5 sentences, no bullets / numbers.
These tests pin the contract for every branch of ``_format_budget_block``
that emits cards.
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from dealer_ai.models import Vehicle
from dealer_ai.services.chat_engine import (
    _CARD_PRESENTATION_PREAMBLE,
    _format_budget_block,
    build_budget_context,
)


def _make_vehicle(
    stock,
    price,
    *,
    model="F-150",
    trim="",
    drivetrain="",
    body="truck",
    condition="new",
    mileage=0,
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
        mileage=mileage,
        price=Decimal(price),
        drivetrain=drivetrain,
    )


class CardPresentationPreambleContractTests(TestCase):
    """The shared preamble carries the spec-deduplication directives;
    every card-bearing branch must include it so behavior stays
    consistent."""

    def test_preamble_carries_dedup_directives(self):
        # Single doc-level assertion — the preamble itself encodes
        # the contract.
        for clause in (
            "the cards above already show price",
            "Your job is to GUIDE ATTENTION, not re-render",
            "DO NOT quote prices",
            "ABSOLUTELY NO bulleted lists",
            "NO numbered steps",
            "NO pipe-delimited",
            "DO NOT introduce a vehicle with its Stock #",
            "DO NOT recite full feature lists",
            "3–5 sentences",
        ):
            self.assertIn(clause, _CARD_PRESENTATION_PREAMBLE)

    def _block_for(self, profile, text="$500/mo trucks"):
        return _format_budget_block(
            build_budget_context(profile, text)
        )


class BadExampleNoConcreteDollarsTests(SimpleTestCase):
    """Regression guard for the small-model contamination bug.

    The drift was that the BAD examples in the preamble contained real
    dollar figures (`$26,995`, `$517/mo`, `$25,495`, `$486/mo`). The
    small Ollama model imitated the BAD-example numbers verbatim —
    `$486/mo` showed up in customer replies for cards whose actual
    estimated payment was different. Negative directives don't beat
    concrete imitation targets on small models (BEHAVIOR_LAYER §
    "Small-Model Behavior Note").

    The fix is to keep the BAD example's *shape* (pipe-delimited spec
    dump, multiple prices in one reply) but strip its *numbers*. This
    test pins that contract: the GOOD example may carry a concrete
    payment for the lead vehicle (it teaches the desired phrasing),
    but the BAD-example region must contain only placeholders.
    """

    # Match `$1,234`, `$1234`, `$1,234.56`, `$1234.56`. Requires at
    # least one digit. Placeholders like `$XX,XXX` and `$XXX` are
    # ignored (no digits in the placeholder body).
    _CONCRETE_DOLLAR_RE = re.compile(r"\$\s*\d[\d,]*(?:\.\d+)?")

    def _bad_region(self) -> str:
        marker = "BAD examples"
        idx = _CARD_PRESENTATION_PREAMBLE.find(marker)
        self.assertNotEqual(
            idx, -1,
            "BAD examples section missing from _CARD_PRESENTATION_PREAMBLE",
        )
        return _CARD_PRESENTATION_PREAMBLE[idx:]

    def test_bad_region_has_no_concrete_dollars(self):
        region = self._bad_region()
        hits = self._CONCRETE_DOLLAR_RE.findall(region)
        self.assertEqual(
            hits, [],
            f"BAD-example region must use placeholders only — found "
            f"concrete dollar amounts {hits!r} in:\n{region}",
        )

    def test_bad_region_has_no_payment_per_mo(self):
        region = self._bad_region()
        # No `$NN/mo`, `$NN/month`, `$NN per month`, etc.
        payment_re = re.compile(
            r"\$\s*\d[\d,]*"
            r"(?:/\s*mo(?:nth)?|\s+(?:per|a)\s+month|\s+monthly)",
            re.IGNORECASE,
        )
        hits = payment_re.findall(region)
        self.assertEqual(
            hits, [],
            f"BAD-example region must not show concrete $X/mo "
            f"figures — small Ollama model has been observed "
            f"imitating them verbatim. Found: {hits!r}",
        )

    def test_bad_region_keeps_pipe_shape_signal(self):
        # Sanity: we removed the numbers but kept the shape so the
        # rule still teaches what to avoid. If this assertion fires,
        # the BAD example was over-cleaned and no longer demonstrates
        # the bullet/list/spec-dump shape the rule forbids.
        region = self._bad_region()
        self.assertIn("Here are some options", region)
        self.assertIn("$XX,XXX", region)
        self.assertIn("$XXX/mo", region)


class CardPresentationBudgetBlockTests(TestCase):
    """Per-branch presence checks — every card-bearing branch in
    ``_format_budget_block`` must include the shared preamble."""

    def _block_for(self, profile, text="$500/mo trucks"):
        return _format_budget_block(
            build_budget_context(profile, text)
        )

    def test_preamble_present_when_fit_only(self):
        _make_vehicle("FIT", "20000", drivetrain="4x4")
        block = self._block_for(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )
        self.assertIn(
            "Your job is to GUIDE ATTENTION, not re-render", block
        )
        self.assertIn("ABSOLUTELY NO bulleted lists", block)

    def test_preamble_present_when_fit_plus_stretches(self):
        _make_vehicle("FIT", "20000", drivetrain="4x4")
        _make_vehicle("OV1", "27500", drivetrain="4x4")
        _make_vehicle("OV2", "27800", drivetrain="4x4")
        block = self._block_for(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )
        self.assertIn(
            "Your job is to GUIDE ATTENTION, not re-render", block
        )

    def test_preamble_present_when_near_only(self):
        _make_vehicle("NEAR-A", "26000", drivetrain="4x4")
        _make_vehicle("NEAR-B", "26500", drivetrain="4x4")
        # Need to keep flex-options off — seed only near-fits, no overs
        # within reach. The realistic-stretch cap handles that.
        block = self._block_for(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )
        self.assertIn("Your job is to GUIDE ATTENTION", block)

    def test_preamble_present_when_single_near_no_stretch(self):
        # Single near-fit + far-over — closest_above filtered to empty
        # by the realistic-stretch cap.
        _make_vehicle("ONLY", "26000", drivetrain="4x4")
        _make_vehicle("WAY-OVER", "55000", drivetrain="4x4")
        block = self._block_for(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )
        self.assertIn("Your job is to GUIDE ATTENTION", block)

    def test_preamble_present_when_lever_flex_fires(self):
        # Strict 4WD + 4x2 alternates → flex picks layered on.
        _make_vehicle(
            "RANGER-4WD", "26995", model="Ranger", drivetrain="4x4"
        )
        _make_vehicle(
            "COLO-2WD", "25495", model="Colorado", drivetrain="RWD"
        )
        block = self._block_for(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        self.assertIn("Your job is to GUIDE ATTENTION", block)
        # Flex branch keeps the multi-lever close.
        self.assertIn("LEVER FLEX OPTIONS", block)


class NoListMarkersInRuleSectionTests(TestCase):
    """The rule section itself must not look like a bulleted list to
    the LLM. Lines starting with '- ', '* ', '• ', or '1. ' are
    instructional bullets that weaker local models have echoed
    verbatim into the customer reply."""

    def _rule_section_lines(self, profile):
        block = _format_budget_block(build_budget_context(profile, "test"))
        idx = block.find("Reply rules")
        if idx < 0:
            return []
        return block[idx:].split("\n")

    def test_lever_flex_branch_has_no_list_markers(self):
        _make_vehicle("RANGER", "26995", model="Ranger", drivetrain="4x4")
        _make_vehicle("COLO", "25495", model="Colorado", drivetrain="RWD")
        for line in self._rule_section_lines(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        ):
            stripped = line.strip()
            if not stripped:
                continue
            self.assertFalse(
                stripped.startswith(("- ", "* ", "• ")),
                f"rule line should not start with a bullet: {line!r}",
            )

    def test_near_plus_stretch_branch_has_no_list_markers(self):
        _make_vehicle("NEAR-T", "25500", drivetrain="4x4")
        _make_vehicle("OV1", "27500", drivetrain="4x4")
        _make_vehicle("OV2", "27800", drivetrain="4x4")
        for line in self._rule_section_lines(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        ):
            stripped = line.strip()
            if not stripped:
                continue
            self.assertFalse(
                stripped.startswith(("- ", "* ", "• ")),
                f"rule line should not start with a bullet: {line!r}",
            )

    def test_single_near_branch_has_no_list_markers(self):
        _make_vehicle("ONLY", "26000", drivetrain="4x4")
        _make_vehicle("WAY-OVER", "55000", drivetrain="4x4")
        for line in self._rule_section_lines(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        ):
            stripped = line.strip()
            if not stripped:
                continue
            self.assertFalse(
                stripped.startswith(("- ", "* ", "• ")),
                f"rule line should not start with a bullet: {line!r}",
            )


class RuleForbidsSpecRepetitionTests(TestCase):
    """Each card-bearing branch must explicitly forbid recital of
    spec data the cards already show."""

    def _block(self, profile):
        return _format_budget_block(build_budget_context(profile, "x"))

    def test_in_budget_branch_forbids_extra_price_recite(self):
        _make_vehicle("FIT", "20000", drivetrain="4x4")
        block = self._block(
            {
                "target_monthly_payment": 500,
                "down_payment": 0,
                "term_months": 60,
                "vehicle_type": "truck",
            }
        )
        # Preamble forbids spec dump.
        self.assertIn(
            "DO NOT quote prices, mileage, Stock #s, or feature lists",
            block,
        )

    def test_lever_flex_branch_forbids_in_budget_label_for_flex_card(self):
        _make_vehicle("RANGER", "26995", model="Ranger", drivetrain="4x4")
        _make_vehicle("COLO", "25495", model="Colorado", drivetrain="RWD")
        block = self._block(
            {
                "target_monthly_payment": 500,
                "down_payment": 3000,
                "term_months": 60,
                "vehicle_type": "truck",
                "drivetrain": "4WD",
            }
        )
        self.assertIn("DO NOT call a flex card \"in your budget\"", block)


class SentenceCapTests(TestCase):
    """The 3-5 sentence cap is the structural lever that prevents
    re-listing. It must appear in every card-bearing branch."""

    def _block(self, profile):
        return _format_budget_block(build_budget_context(profile, "x"))

    def test_cap_present_in_all_card_bearing_branches(self):
        # Build several scenarios — each block must carry the cap.
        scenarios = [
            # IN BUDGET only
            (
                [("FIT", "20000", "4x4")],
                {
                    "target_monthly_payment": 500,
                    "down_payment": 0,
                    "term_months": 60,
                    "vehicle_type": "truck",
                },
            ),
            # NEAR-FIT + flex
            (
                [
                    ("RANGER", "26995", "4x4"),
                    ("COLO", "25495", "RWD"),
                ],
                {
                    "target_monthly_payment": 500,
                    "down_payment": 3000,
                    "term_months": 60,
                    "vehicle_type": "truck",
                    "drivetrain": "4WD",
                },
            ),
            # Single near-fit, no stretches
            (
                [
                    ("ONLY", "26000", "4x4"),
                    ("WAY", "55000", "4x4"),
                ],
                {
                    "target_monthly_payment": 500,
                    "down_payment": 0,
                    "term_months": 60,
                    "vehicle_type": "truck",
                    "drivetrain": "4WD",
                },
            ),
        ]
        for seeds, profile in scenarios:
            with self.subTest(profile=profile):
                Vehicle.objects.all().delete()
                for stock, price, dt in seeds:
                    _make_vehicle(stock, price, drivetrain=dt)
                block = self._block(profile)
                self.assertIn("3–5 sentences", block)
