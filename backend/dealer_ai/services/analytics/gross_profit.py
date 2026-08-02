"""Milestone 9 · Increment 3 (SESSION_102) — gross-profit trend analytics.

Q6 aggregation deferred at M8 pending the M9.1 Sale substrate.
Reads :attr:`Sale.sale_date` + :attr:`Sale.gross_realized`
(denormalized at M9.1 write time via
:func:`services.sale.record_sale`) and emits a per-day time series
across a rolling window.

**Read-only.** No verb here writes to the DB — same posture as the
M8 sibling verbs (see
:doc:`../../roadmap/MILESTONE_8_PLANNING.md` §5.a Option C,
compute-on-request v1).

**Tenant-scoped.** ``dealership`` is a required first positional
argument. The verb enforces tenant scoping in its own queryset; no
shared filter-manager layer.

**Daily-bucket time series.** Sales are grouped by
``sale_date`` (a ``DateField``, so the group-by is native — no
date-truncation of a DateTime). One point per date that had at
least one sale. Dates with zero sales in the window are omitted
(sparse series) — the operator's chart renders the gap literally.
An alternate "dense series" mode (one point per calendar day even
when zero) can land later if operator evidence surfaces need.

Source of truth: ``docs/roadmap/MILESTONE_9_PLANNING.md`` §1.5 +
§7 M9.3.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from ...models import Dealership, Sale


ZERO = Decimal("0.00")


@dataclass(frozen=True)
class GrossProfitPoint:
    """One time-series point — the aggregate gross realized on
    sales closed on one calendar day.

    Frozen because the aggregation output is immutable; callers
    should project into a serialized shape rather than mutate.

    Fields:

    - ``sale_date`` — the calendar day the sales closed on
      (:class:`datetime.date`, timezone-naive per Django's
      ``DateField`` semantics).
    - ``sale_count`` — number of sales closed on ``sale_date``.
    - ``total_gross_realized`` — sum of
      :attr:`Sale.gross_realized` across those sales. Signed
      :class:`Decimal` — negative when the day ran a net loss
      (e.g. a large below-cost wholesale disposal).
    """

    sale_date: dt.date
    sale_count: int
    total_gross_realized: Decimal


def gross_profit_trend(
    dealership: Dealership,
    *,
    window_days: int = 90,
) -> list[GrossProfitPoint]:
    """Q6 aggregation — daily-bucket gross-profit time series.

    Answers *"how has our realized gross moved over the last N
    days?"* (INVENTORY §"To Ownership" + M8 Q6 deferral). Reads
    the M9.1 :attr:`Sale.gross_realized` denormalized column
    directly so the aggregation is a straight ORM group-by-and-
    sum — no per-row ledger recomputation.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_days : int, optional
        Number of days of history to return. Default 90.
        Filters ``sale_date >= today - window_days`` where
        "today" is derived from
        :func:`django.utils.timezone.now` for tz consistency
        with M8 sibling verbs.

    Returns
    -------
    list[GrossProfitPoint]
        Points ordered by ``sale_date`` ascending — the M8.5
        dashboard's per-day trend line reads left-to-right.
        Sparse series (dates with zero sales in the window are
        omitted). Empty window (no sales at all) returns ``[]``.

    Notes
    -----
    Read-only. Reads ``Sale.gross_realized`` directly rather than
    recomputing via :func:`services.sale.gross_realized` per row
    — the M9.1 verb denormalized at write time precisely so
    aggregations stay single-query.
    """
    today = timezone.now().date()
    since = today - dt.timedelta(days=window_days)

    qs = (
        Sale.objects.filter(
            dealership=dealership,
            sale_date__gte=since,
        )
        .values("sale_date")
        .annotate(
            sale_count=Count("id"),
            total_gross_realized=Sum("gross_realized"),
        )
        .order_by("sale_date")
    )

    # Quantize to 2dp so the JSON wire shape stays consistent with
    # the M8 sibling verbs' Decimal projection (they all render as
    # ``"1234.56"``). Django's ``Sum`` returns an unquantized Decimal
    # (``Decimal("2000")``) when the underlying value has trailing
    # zeros — quantizing normalizes to ``Decimal("2000.00")``.
    return [
        GrossProfitPoint(
            sale_date=row["sale_date"],
            sale_count=row["sale_count"],
            total_gross_realized=(
                (row["total_gross_realized"] or ZERO).quantize(
                    Decimal("0.01")
                )
            ),
        )
        for row in qs
    ]
