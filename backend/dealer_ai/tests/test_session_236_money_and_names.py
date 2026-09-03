"""SESSION_236 (TASK_names-and-money.md) guard tests.

Two properties the task locks:

- Every money value composed server-side into a stored note goes
  through :func:`services.money_format.fmt_money` — so a five-figure
  amount always renders with a thousands separator, and the handoff
  note the F&I team reads never says ``$11795.00`` again.
- APR strings render at two decimals — so the proposed-structure card
  never reads ``14.9000%`` again.

Delete the ``fmt_money`` call and this file fails.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import SimpleTestCase

from dealer_ai.services.money_format import fmt_apr, fmt_money


class FmtMoneyTests(SimpleTestCase):
    def test_five_figure_amount_has_thousands_separator(self):
        # If this fails, someone dropped the `,` in `fmt_money`. The
        # handoff note would render as `$11795.00` again — the exact
        # regression the walk called out.
        self.assertIn(",", fmt_money(Decimal("11795.00")))
        self.assertEqual(fmt_money(Decimal("11795.00")), "$11,795.00")

    def test_six_figure_amount_has_two_separators(self):
        self.assertEqual(fmt_money(Decimal("1234567.89")), "$1,234,567.89")

    def test_null_and_empty_render_as_zero(self):
        self.assertEqual(fmt_money(None), "$0.00")
        self.assertEqual(fmt_money(""), "$0.00")

    def test_negative_amount_uses_unicode_minus(self):
        self.assertTrue(fmt_money(Decimal("-500")).startswith("\u2212"))

    def test_accepts_str_int_float(self):
        self.assertEqual(fmt_money("9385"), "$9,385.00")
        self.assertEqual(fmt_money(9385), "$9,385.00")
        self.assertEqual(fmt_money(9385.5), "$9,385.50")


class FmtAprTests(SimpleTestCase):
    def test_apr_renders_at_two_decimals(self):
        # If this fails, the proposed-structure card would show
        # `14.9000%` — the exact string the walk called out.
        self.assertEqual(fmt_apr(Decimal("14.9000")), "14.90%")
        self.assertEqual(fmt_apr(Decimal("6.25")), "6.25%")

    def test_apr_null_is_em_dash(self):
        self.assertEqual(fmt_apr(None), "—")


class HandoffNoteUsesFormatterTests(SimpleTestCase):
    """The composed handoff note (M11.3) must not emit a bare Decimal
    into user-visible text. This test exercises the composer directly
    with a shaped DealWriteup stand-in — cheap and fast, and it
    catches the regression at the composer, not five layers below.
    """

    def test_handoff_note_thousands_separator(self):
        from types import SimpleNamespace

        from dealer_ai.services.deal_writeups.deal_writeup import (
            _format_handoff_notes,
        )

        stand_in = SimpleNamespace(
            pk=42,
            vehicle_price=Decimal("11795.00"),
            trade_allowance=None,
            down_payment=Decimal("1500.00"),
            monthly_payment_target=Decimal("389.00"),
            term_months_target=72,
            apr_target=Decimal("14.9000"),
            notes="",
        )
        note = _format_handoff_notes(stand_in)
        # Regression guards for the exact walk-called defects:
        self.assertNotIn("$11795.00", note)
        self.assertIn("$11,795.00", note)
        self.assertNotIn("14.9000%", note)
        self.assertIn("14.90%", note)
