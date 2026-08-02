"""Milestone 12 · Increment 7 (SESSION_127) — BHPH portfolio aggregation math.

Pure. Tenant-scoped. Read-only.

Verb list per §7 M12.7 + §0.a M12.7 decisions 1-4 (as-recommended):

- :func:`bucket_histogram`
- :func:`cure_rate` (snapshot MVP)
- :func:`weighted_average_apr`
- :func:`weighted_average_days_past_due`
- :func:`ptp_kept_ratio`
- :func:`portfolio_summary` (bundles all five per §0.a decision 2)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from django.db.models import Count, Sum

from ...models import (
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_16_30,
    BHPH_AGING_BUCKET_31_60,
    BHPH_AGING_BUCKET_61_90,
    BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_AGING_BUCKET_OVER_90,
    BHPH_PROMISE_STATE_BROKEN,
    BHPH_PROMISE_STATE_KEPT,
    BhphNote,
    BhphPromiseToPay,
    Dealership,
)


_ZERO = Decimal("0.00")
_CENTS = Decimal("0.01")
_RATIO_QUANT = Decimal("0.0001")

# Bucket vocab locked in order so the histogram output is deterministic
# regardless of which buckets are populated in the DB.
_BUCKET_ORDER = (
    BHPH_AGING_BUCKET_CURRENT,
    BHPH_AGING_BUCKET_1_15,
    BHPH_AGING_BUCKET_16_30,
    BHPH_AGING_BUCKET_31_60,
    BHPH_AGING_BUCKET_61_90,
    BHPH_AGING_BUCKET_OVER_90,
    BHPH_AGING_BUCKET_CHARGE_OFF_CANDIDATE,
)


@dataclass(frozen=True)
class BucketHistogramRow:
    """One row of the portfolio aging histogram.

    Fields:

    - ``bucket`` — one of the 7-value aging vocab strings.
    - ``note_count`` — number of BhphNote rows in this bucket.
    - ``principal_total`` — sum of
      :attr:`BhphNote.principal_financed` across those notes.
      Quantized to cents.
    """

    bucket: str
    note_count: int
    principal_total: Decimal


@dataclass(frozen=True)
class BhphAnalyticsSummary:
    """Bundled M12.7 portfolio metrics for one tenant.

    ``weighted_average_apr`` / ``weighted_average_days_past_due`` /
    ``cure_rate`` / ``ptp_kept_ratio`` are ``None`` when the
    portfolio has zero eligible notes / promises (denominator is
    empty). Callers decide how to render — the summary endpoint
    ships ``None`` verbatim.
    """

    bucket_histogram: tuple[BucketHistogramRow, ...]
    total_note_count: int
    total_principal_financed: Decimal
    cure_rate: Optional[Decimal]
    weighted_average_apr: Optional[Decimal]
    weighted_average_days_past_due: Optional[Decimal]
    ptp_kept_ratio: Optional[Decimal]


def bucket_histogram(dealership: Dealership) -> tuple[BucketHistogramRow, ...]:
    """Return the 7-value aging histogram for ``dealership``.

    Always emits all seven bucket rows in vocab order — buckets with
    zero notes come back as ``BucketHistogramRow(bucket, 0,
    Decimal("0.00"))`` rather than being omitted. This lets the
    frontend render the full histogram without conditional slot
    filling.
    """
    rows_by_bucket: dict[str, dict] = {
        b: {"note_count": 0, "principal_total": _ZERO} for b in _BUCKET_ORDER
    }
    aggregated = (
        BhphNote.objects.filter(dealership=dealership)
        .values("current_bucket")
        .annotate(
            note_count=Count("id"),
            principal_total=Sum("principal_financed"),
        )
    )
    for row in aggregated:
        bucket = row["current_bucket"]
        if bucket not in rows_by_bucket:
            # Defensive: skip rows with an unrecognized bucket (would
            # only happen if a future migration adds a value the
            # analytics module hasn't been updated for).
            continue
        rows_by_bucket[bucket]["note_count"] = row["note_count"]
        rows_by_bucket[bucket]["principal_total"] = (
            row["principal_total"] or _ZERO
        ).quantize(_CENTS, rounding=ROUND_HALF_UP)
    return tuple(
        BucketHistogramRow(
            bucket=b,
            note_count=rows_by_bucket[b]["note_count"],
            principal_total=rows_by_bucket[b]["principal_total"],
        )
        for b in _BUCKET_ORDER
    )


def cure_rate(dealership: Dealership) -> Optional[Decimal]:
    """Portfolio-health snapshot: ratio of notes in ``current`` bucket.

    MVP interpretation (§0.a M12.7 decision 1): snapshot metric,
    not time-windowed. True cure rate (delinquent → current
    transitions across a window) defers until M12+ time-series
    storage lands — this snapshot answers the read-off-the-dashboard
    question "how healthy is the portfolio right now?"

    Returns ``None`` when the portfolio has zero notes (undefined
    ratio).
    """
    total = BhphNote.objects.filter(dealership=dealership).count()
    if total == 0:
        return None
    current_count = BhphNote.objects.filter(
        dealership=dealership,
        current_bucket=BHPH_AGING_BUCKET_CURRENT,
    ).count()
    return (Decimal(current_count) / Decimal(total)).quantize(
        _RATIO_QUANT, rounding=ROUND_HALF_UP
    )


def weighted_average_apr(dealership: Dealership) -> Optional[Decimal]:
    """Portfolio-weighted APR: sum(principal * apr) / sum(principal).

    Weighting by principal reflects the fact that a $30k note at 22%
    matters more than a $3k note at 22% for portfolio yield. Returns
    ``None`` when the portfolio has zero principal (undefined
    weighted average).
    """
    notes = list(
        BhphNote.objects.filter(dealership=dealership).values(
            "principal_financed", "apr"
        )
    )
    if not notes:
        return None
    total_principal = sum((n["principal_financed"] for n in notes), _ZERO)
    if total_principal == 0:
        return None
    weighted_sum = sum(
        (n["principal_financed"] * n["apr"] for n in notes), _ZERO
    )
    return (weighted_sum / total_principal).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )


def weighted_average_days_past_due(
    dealership: Dealership,
) -> Optional[Decimal]:
    """Portfolio-weighted days-past-due.

    sum(principal * days_past_due) / sum(principal). Returns
    ``None`` when the portfolio has zero principal.
    """
    notes = list(
        BhphNote.objects.filter(dealership=dealership).values(
            "principal_financed", "days_past_due"
        )
    )
    if not notes:
        return None
    total_principal = sum((n["principal_financed"] for n in notes), _ZERO)
    if total_principal == 0:
        return None
    weighted_sum = sum(
        (
            n["principal_financed"] * Decimal(n["days_past_due"])
            for n in notes
        ),
        _ZERO,
    )
    return (weighted_sum / total_principal).quantize(
        _CENTS, rounding=ROUND_HALF_UP
    )


def ptp_kept_ratio(dealership: Dealership) -> Optional[Decimal]:
    """Kept-promise ratio: kept / (kept + broken).

    ``promised`` (still-open) promises are excluded from the
    denominator — the ratio measures resolved promises only.
    Returns ``None`` when no promises have resolved (denominator is
    zero).
    """
    counts = BhphPromiseToPay.objects.filter(
        dealership=dealership,
        state__in=[BHPH_PROMISE_STATE_KEPT, BHPH_PROMISE_STATE_BROKEN],
    ).aggregate(total=Count("id"))
    total = counts["total"] or 0
    if total == 0:
        return None
    kept = BhphPromiseToPay.objects.filter(
        dealership=dealership, state=BHPH_PROMISE_STATE_KEPT
    ).count()
    return (Decimal(kept) / Decimal(total)).quantize(
        _RATIO_QUANT, rounding=ROUND_HALF_UP
    )


def portfolio_summary(dealership: Dealership) -> BhphAnalyticsSummary:
    """Bundle all five metrics into a single :class:`BhphAnalyticsSummary`.

    Consumed by the M12.7 summary endpoint per §0.a M12.7 decision 2
    (single summary endpoint at MVP; per-metric endpoints defer).
    """
    histogram = bucket_histogram(dealership)
    total_notes = sum(row.note_count for row in histogram)
    total_principal = sum(
        (row.principal_total for row in histogram), _ZERO
    ).quantize(_CENTS, rounding=ROUND_HALF_UP)
    return BhphAnalyticsSummary(
        bucket_histogram=histogram,
        total_note_count=total_notes,
        total_principal_financed=total_principal,
        cure_rate=cure_rate(dealership),
        weighted_average_apr=weighted_average_apr(dealership),
        weighted_average_days_past_due=weighted_average_days_past_due(
            dealership
        ),
        ptp_kept_ratio=ptp_kept_ratio(dealership),
    )
