"""SESSION_236 — one place to render money as US text.

Task file: docs/_internal/TASK_names-and-money.md, part 2.

Every f-string in a composed note that puts a dollar into stored text
should call :func:`fmt_money` (or :func:`fmt_apr` for percents) instead
of interpolating a bare ``Decimal``. The chat / handoff / recon-note
composers all write user-visible strings — the frontend formatter cannot
touch text after it has been persisted.

The output shape matches the frontend ``formatMoney`` in
``frontend/src/lib/utils.ts``: dollar sign, comma thousands separator,
two decimal places, unicode minus for negatives.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Union

_Amount = Union[Decimal, int, float, str, None]


def fmt_money(value: _Amount) -> str:
    """Render a monetary amount as ``$1,234.56``.

    Returns ``"$0.00"`` for ``None`` / empty. Uses a unicode minus
    (``\u2212``) for negative amounts, matching the frontend helper.
    Truncates (not rounds) to two decimal places — the values in
    play are already stored on ``DecimalField(max_digits=?, decimal_places=2)``,
    so this is just a display formatter, not a rounding step.
    """
    if value is None or value == "":
        return "$0.00"
    try:
        amount = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return f"${value}"
    negative = amount < 0
    if negative:
        amount = -amount
    quantized = amount.quantize(Decimal("0.01"))
    whole, _, frac = format(quantized, "f").partition(".")
    with_commas = _add_thousands(whole)
    frac_padded = (frac or "").ljust(2, "0")[:2]
    sign = "\u2212" if negative else ""
    return f"{sign}${with_commas}.{frac_padded}"


def fmt_apr(value: _Amount, *, places: int = 2) -> str:
    """Render an APR as ``14.90%`` (two decimals by default).

    APRs are stored as :class:`Decimal` percents (``14.9000``);
    Chris's walk called out ``14.9000%`` in the proposed-structure
    card. Same shape as :func:`fmt_money` w/r/t ``None`` handling —
    returns an em dash so bare interpolation ``f"APR {fmt_apr(x)}"``
    never blows up.
    """
    if value is None or value == "":
        return "—"
    try:
        amount = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return f"{value}%"
    quantum = Decimal("1").scaleb(-places)
    return f"{amount.quantize(quantum)}%"


def _add_thousands(whole: str) -> str:
    negative = whole.startswith("-")
    body = whole[1:] if negative else whole
    if not body:
        return whole
    groups = []
    while len(body) > 3:
        groups.append(body[-3:])
        body = body[:-3]
    groups.append(body)
    joined = ",".join(reversed(groups))
    return f"-{joined}" if negative else joined
