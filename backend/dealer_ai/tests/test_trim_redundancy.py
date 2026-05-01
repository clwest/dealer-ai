"""Phase 8i — trim-redundancy tests.

The assistant should not launch into trim-level explanations when:
  - only ONE vehicle is shown
  - all shown vehicles are the same trim

Trim comparison is only acceptable when the matched set actually has
multiple distinct trim levels (XL vs XLT vs Lariat).
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from dealer_ai.models import Vehicle
from dealer_ai.services.chat_engine import _format_vehicle_block


def _make_vehicle(stock, trim, *, model="F-150", price="50000"):
    return Vehicle.objects.create(
        stock_number=stock,
        year=2025,
        make="Ford",
        model=model,
        trim=trim,
        body_style="truck",
        condition="new",
        price=Decimal(price),
    )


class TrimRedundancyDirectiveTests(TestCase):
    def test_single_vehicle_block_says_do_not_explain_trims(self):
        v = _make_vehicle("ONE", "XLT 4x4")
        block = _format_vehicle_block([v])
        self.assertIn("Only ONE vehicle is shown", block)
        self.assertIn("Do NOT explain or compare trim levels", block)

    def test_multiple_same_trim_block_says_no_meaningful_difference(self):
        a = _make_vehicle("A", "XLT 4x4", stock_suffix="a") if False else _make_vehicle("A1", "XLT 4x4")
        b = _make_vehicle("B1", "XLT 4x4")
        block = _format_vehicle_block([a, b])
        self.assertIn("same trim", block)
        self.assertIn("no meaningful difference", block)

    def test_multiple_distinct_trims_block_omits_no_compare_directive(self):
        a = _make_vehicle("A2", "XL")
        b = _make_vehicle("B2", "XLT 4x4")
        c = _make_vehicle("C2", "Lariat")
        block = _format_vehicle_block([a, b, c])
        # No "do not compare" / "only ONE" directive when trims actually differ.
        self.assertNotIn("Do NOT explain or compare trim levels", block)
        self.assertNotIn("All vehicles shown are the same trim", block)

    def test_blank_trims_treated_as_indistinct(self):
        a = _make_vehicle("BL1", "")
        b = _make_vehicle("BL2", "")
        block = _format_vehicle_block([a, b])
        self.assertIn("same trim", block)

    def test_one_blank_one_distinct_still_flags_redundancy_only_when_one(self):
        # Two vehicles, one with a real trim and one blank — that's two
        # distinct trim values, so the LLM is allowed to discuss the
        # difference if relevant. We only suppress when there's truly nothing
        # to compare.
        a = _make_vehicle("MIX1", "XLT")
        b = _make_vehicle("MIX2", "")
        block = _format_vehicle_block([a, b])
        self.assertNotIn("All vehicles shown are the same trim", block)
        self.assertNotIn("Only ONE vehicle is shown", block)
