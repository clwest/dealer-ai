"""Milestone 12 · Increment 7 (SESSION_127) — BHPH portfolio analytics.

Five pure aggregate verbs per ``MILESTONE_12_PLANNING.md`` §1.7 +
§5.f Option C (MVP scope locked at SESSION_121 open):

- :func:`bucket_histogram` — 7-value aging bucket counts + dollar
  totals across the portfolio for one tenant.
- :func:`cure_rate` — snapshot portfolio-health metric at MVP
  (ratio of notes currently in ``current`` bucket to all notes).
  True time-windowed cure rate defers until M12+ time-series
  storage lands.
- :func:`weighted_average_apr` — sum(principal * apr) /
  sum(principal).
- :func:`weighted_average_days_past_due` — sum(principal *
  days_past_due) / sum(principal).
- :func:`ptp_kept_ratio` — kept / (kept + broken) across
  BhphPromiseToPay rows.

All verbs are tenant-scoped (first positional argument is
``dealership``). Read-only. No DB writes. Same posture as the M8
sibling verbs.

Zero-note portfolios return ``None`` for the weighted-average
metrics (division-by-zero avoided at the caller's discretion).
"""

from __future__ import annotations

from .compute import (
    BhphAnalyticsSummary,
    BucketHistogramRow,
    bucket_histogram,
    cure_rate,
    portfolio_summary,
    ptp_kept_ratio,
    weighted_average_apr,
    weighted_average_days_past_due,
)

__all__ = [
    "BhphAnalyticsSummary",
    "BucketHistogramRow",
    "bucket_histogram",
    "cure_rate",
    "portfolio_summary",
    "ptp_kept_ratio",
    "weighted_average_apr",
    "weighted_average_days_past_due",
]
