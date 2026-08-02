"""Milestone 12 · Increment 7 (SESSION_127) — BHPH analytics endpoint.

Single summary endpoint per ``MILESTONE_12_PLANNING.md`` §7 M12.7 +
§0.a M12.7 decision 2 (single summary endpoint at MVP; per-metric
endpoints defer):

- ``GET /admin/bhph/analytics/summary/`` — full portfolio metric set
  in one payload.

Gated on ``IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership``
(matches M12.1-M12.6 admin posture).

Serialization is hand-rolled (no DRF serializer) — the summary
dataclass surface is small enough that a serializer class would be
pure ceremony. Money on the wire is Decimal-as-string; ratios ship as
Decimal-as-string; ``None`` values ship verbatim.
"""

from __future__ import annotations

from typing import Optional
from decimal import Decimal

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsSalesManagerOrOwnerAtActiveDealership
from .services.bhph_analytics import portfolio_summary
from .services.tenancy import get_current_dealership


_M127_PERMS = [IsAuthenticated & IsSalesManagerOrOwnerAtActiveDealership]


def _decimal_or_none(value: Optional[Decimal]) -> Optional[str]:
    return None if value is None else str(value)


@api_view(["GET"])
@permission_classes(_M127_PERMS)
def admin_bhph_analytics_summary(request):
    dealership = get_current_dealership(request)
    summary = portfolio_summary(dealership)
    return Response(
        {
            "bucket_histogram": [
                {
                    "bucket": row.bucket,
                    "note_count": row.note_count,
                    "principal_total": str(row.principal_total),
                }
                for row in summary.bucket_histogram
            ],
            "total_note_count": summary.total_note_count,
            "total_principal_financed": str(
                summary.total_principal_financed
            ),
            "cure_rate": _decimal_or_none(summary.cure_rate),
            "weighted_average_apr": _decimal_or_none(
                summary.weighted_average_apr
            ),
            "weighted_average_days_past_due": _decimal_or_none(
                summary.weighted_average_days_past_due
            ),
            "ptp_kept_ratio": _decimal_or_none(summary.ptp_kept_ratio),
        },
        status=status.HTTP_200_OK,
    )
