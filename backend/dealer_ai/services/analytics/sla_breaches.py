"""Milestone 8 · Increment 3 (SESSION_096) — SLA-breach analytics.

Owns the aggregations rooted in M8.1
:class:`SlaBreachRecord` — today: Q10
(:func:`breach_patterns`). The M8.1 verb-extension writes rows
into this table on the M7.4 daily scan; this verb reads them back
as an operator-triage report.

**Read-only.** No verb here writes to the DB. Reads the already-
persisted M8.1 rows per :doc:`../../roadmap/MILESTONE_8_PLANNING.md`
§5.a Option C (hybrid, compute-on-request v1).

**Tenant-scoped.** Every verb takes ``dealership`` as a required
first positional argument.

**Top-N convention.** Vendor rollups return the top 5 vendors by
breach count (arbitrary cutoff — small enough to fit on one
dashboard tile, large enough to catch most of the meaningful
signal in a mid-sized dealer's window). Kind rollups return all
kinds (the vocabulary is small and static — 2 today).

Source of truth: ``docs/roadmap/MILESTONE_8_PLANNING.md`` §1.5 +
§7 M8.3.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.db.models import Count, Sum
from django.utils import timezone

from ...models import (
    SLA_BREACH_KIND_CHOICES,
    Dealership,
    SlaBreachRecord,
)


# Vendor rollup cutoff. Small enough to fit on one dashboard tile,
# large enough to catch most meaningful signal. Not user-configurable
# at v1; if operator evidence suggests a different cutoff, revisit.
_TOP_VENDOR_LIMIT = 5


# Precomputed lookup for the human-readable kind labels. The M8
# dashboard renders these; kept precomputed so the aggregation loop
# doesn't rebuild it per invocation.
_KIND_DISPLAY_BY_KEY: dict[str, str] = dict(SLA_BREACH_KIND_CHOICES)


ZERO = Decimal("0.00")


@dataclass(frozen=True)
class VendorBreachCount:
    """One vendor + how many breaches attributed to them in the
    window."""

    vendor_name: str
    breach_count: int


@dataclass(frozen=True)
class KindBreachCount:
    """One breach kind + how many rows of that kind in the window.

    Both fields carried explicitly — the display label is
    denormalized at aggregation time so JSON callers do not need to
    repeat the lookup.
    """

    kind: str
    kind_display: str
    breach_count: int


@dataclass(frozen=True)
class BreachPatternReport:
    """The operator-facing summary of SLA-breach patterns in a
    window.

    Frozen because the report is immutable once computed; callers
    should project into a serialized shape rather than mutate.

    Fields:

    - ``total_breach_count`` — total ``SlaBreachRecord`` rows
      matched by ``(dealership, detected_at within window)``.
    - ``average_breach_days`` — mean ``breach_days`` across those
      rows, quantized to two decimal places. ``None`` when the
      window is empty (division-by-zero guard + preserves the "no
      signal" semantic distinct from "average happens to be zero").
    - ``top_vendors_by_breach_count`` — up to five vendors sorted
      by breach count desc, tiebreak on vendor_name asc.
    - ``breaches_by_kind`` — one row per kind observed in the
      window. Vocabulary is small (2 today); every kind that
      contributed at least one row is present. Sorted by
      ``breach_count`` desc, tiebreak on ``kind`` asc.
    """

    total_breach_count: int
    average_breach_days: Optional[Decimal]
    top_vendors_by_breach_count: list[VendorBreachCount] = field(
        default_factory=list
    )
    breaches_by_kind: list[KindBreachCount] = field(default_factory=list)


def breach_patterns(
    dealership: Dealership,
    *,
    window_days: int = 30,
) -> BreachPatternReport:
    """Q10 aggregation — SLA-breach patterns over a rolling window.

    Answers *"what SLA-breach patterns emerged over the last N
    days?"* (Q10) — the M7.4 signal materialized at M8.1.

    Parameters
    ----------
    dealership : Dealership
        The tenant to aggregate. Required — single-tenant.
    window_days : int, optional
        Number of days of history. Default 30. Filters
        ``detected_at >= now - window_days``.

    Returns
    -------
    BreachPatternReport
        Structured summary — total count, average breach_days, top
        vendors, per-kind counts. Empty window produces a report
        with ``total_breach_count == 0`` and empty rollup lists;
        ``average_breach_days`` is ``None`` in that case.

    Notes
    -----
    Read-only. Reads the M8.1 ``SlaBreachRecord`` substrate — the
    verb-extension at
    :func:`services.vendor_sla.detect_sla_breaches` writes into
    this table on every scheduled scan, so the daily M7.4 Beat run
    keeps the aggregation fresh without any additional wiring.
    """
    since = timezone.now() - dt.timedelta(days=window_days)
    qs = SlaBreachRecord.objects.filter(
        dealership=dealership,
        detected_at__gte=since,
    )

    aggregate = qs.aggregate(
        total=Count("id"),
        days_total=Sum("breach_days"),
    )
    total = aggregate["total"] or 0
    days_total = aggregate["days_total"] or 0

    avg_days: Optional[Decimal]
    if total > 0:
        avg_days = (Decimal(days_total) / Decimal(total)).quantize(
            Decimal("0.01")
        )
    else:
        avg_days = None

    # Top-N vendors — one grouped query with LIMIT applied in
    # Python because the vendor cutoff is a business rule, not a
    # DB concern. The result set is small (dozens of vendors at
    # most in a real dealer's window).
    vendor_rollup_qs = (
        qs.values("vendor_name")
        .annotate(breach_count=Count("id"))
        .order_by("-breach_count", "vendor_name")
    )
    top_vendors = [
        VendorBreachCount(
            vendor_name=row["vendor_name"],
            breach_count=row["breach_count"],
        )
        for row in vendor_rollup_qs[:_TOP_VENDOR_LIMIT]
    ]

    # Per-kind rollup — vocabulary is small (2 today), so return
    # every kind that produced at least one row.
    kind_rollup_qs = (
        qs.values("kind")
        .annotate(breach_count=Count("id"))
        .order_by("-breach_count", "kind")
    )
    breaches_by_kind = []
    for row in kind_rollup_qs:
        kind_key: str = row["kind"]
        breaches_by_kind.append(
            KindBreachCount(
                kind=kind_key,
                kind_display=_KIND_DISPLAY_BY_KEY.get(kind_key, kind_key),
                breach_count=row["breach_count"],
            )
        )

    return BreachPatternReport(
        total_breach_count=total,
        average_breach_days=avg_days,
        top_vendors_by_breach_count=top_vendors,
        breaches_by_kind=breaches_by_kind,
    )
