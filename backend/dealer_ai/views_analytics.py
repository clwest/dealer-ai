"""Milestone 8 · Increment 1 (SESSION_094) — analytics admin API.

Thin HTTP shell around the tenant-scoped aggregations in
:mod:`services.analytics`. Every endpoint composes
:class:`IsAuthenticated` &
:class:`IsReconManagerSalesManagerOrOwnerAtActiveDealership` per
``MILESTONE_8_PLANNING.md`` §1.9 — advisor / porter /
f_and_i_manager / collections all receive 403.

Endpoints delegate entirely to :mod:`services.analytics`. No
business logic lives here — this module is thin translation between
HTTP and the aggregation surface. Serialization is deliberately hand-
rolled (no DRF serializers) because the aggregation return shape is a
frozen dataclass row + the mapping is trivial; a serializer class
would be pure ceremony.

Query-arg conventions:

- ``window_start`` — ISO date string (``YYYY-MM-DD``). Inclusive
  lower bound on the underlying date field. Omit / empty for "no
  lower bound."
- ``window_end`` — ISO date string. Inclusive upper bound. Omit /
  empty for "no upper bound."

Malformed dates → HTTP 400 with a specific error message.

Tenant scoping: every endpoint resolves ``dealership`` via
:func:`services.tenancy.get_current_dealership` and passes it
explicitly into the aggregation call.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .permissions import IsReconManagerSalesManagerOrOwnerAtActiveDealership
from .services import analytics as analytics_service
from .services.analytics import (
    AgingTrendPoint,
    BreachPatternReport,
    BuyerAccuracyRow,
    DaysAtFrontlineReport,
    GrossProfitPoint,
    InventoryTurnReport,
    SourcePerformanceRow,
    VehicleTypeProfitabilityRow,
    VehicleTypeReconCostRow,
    VendorPerformanceRow,
)
from .services.tenancy import get_current_dealership


_M81_PERMS = [
    IsAuthenticated & IsReconManagerSalesManagerOrOwnerAtActiveDealership
]


# ---------------------------------------------------------------------------
# Query-arg parsing
# ---------------------------------------------------------------------------


def _parse_iso_date_or_none(
    raw: Optional[str], *, field_name: str
) -> tuple[Optional[dt.date], Optional[Response]]:
    """Parse an ISO date query-arg. Empty / missing → (None, None).
    Malformed → (None, 400 Response).

    Kept out of the endpoint bodies so parsing conventions stay
    consistent across every analytics endpoint added at M8.2+.
    """
    if raw is None or raw == "":
        return None, None
    try:
        return dt.date.fromisoformat(raw), None
    except ValueError:
        return None, Response(
            {
                "detail": (
                    f"Invalid {field_name}: expected ISO date "
                    f"(YYYY-MM-DD), got {raw!r}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


# ---------------------------------------------------------------------------
# Response projections
# ---------------------------------------------------------------------------


def _project_source_row(row: SourcePerformanceRow) -> dict:
    return {
        "source": row.source,
        "source_display": row.source_display,
        "vehicle_count": row.vehicle_count,
        # Decimal → string. Preserves precision across the JSON
        # boundary; the M8.5 dashboard renders these as currency and
        # parses back to Number only when doing arithmetic (which it
        # will not do at v1).
        "total_recon_cost": str(row.total_recon_cost),
        "mean_recon_cost": str(row.mean_recon_cost),
    }


def _project_vendor_performance_row(row: VendorPerformanceRow) -> dict:
    return {
        "vendor_slug": row.vendor_slug,
        "vendor_name": row.vendor_name,
        "completed_count": row.completed_count,
        # ``None`` is a legal value — the vendor exists in the window
        # but no WO had both approved_at + completed_at populated.
        # Preserved as JSON null so the dashboard can render "—".
        "mean_completion_days": row.mean_completion_days,
        # Decimal → string for the same precision-preserving reason
        # as :func:`_project_source_row`. ``None`` stays null.
        "mean_variance_pct": (
            str(row.mean_variance_pct)
            if row.mean_variance_pct is not None
            else None
        ),
        "over_budget_count": row.over_budget_count,
    }


def _project_aging_trend_point(point: AgingTrendPoint) -> dict:
    return {
        # DRF/JSONRenderer will serialize the datetime as ISO 8601 —
        # explicit isoformat call keeps the wire shape stable
        # regardless of renderer configuration.
        "snapshot_at": point.snapshot_at.isoformat(),
        "vehicle_count": point.vehicle_count,
        "p50_days": point.p50_days,
        "p90_days": point.p90_days,
    }


def _project_vehicle_type_row(row: VehicleTypeReconCostRow) -> dict:
    return {
        "make": row.make,
        "model": row.model,
        "vehicle_count": row.vehicle_count,
        "total_recon_cost": str(row.total_recon_cost),
        "mean_recon_cost": str(row.mean_recon_cost),
    }


def _project_vehicle_type_profitability_row(
    row: VehicleTypeProfitabilityRow,
) -> dict:
    return {
        "make": row.make,
        "model": row.model,
        "sold_count": row.sold_count,
        # Decimals → strings for the same precision-preserving reason
        # as the M8 sibling projections.
        "total_sale_gross": str(row.total_sale_gross),
        "total_sold_price": str(row.total_sold_price),
        "mean_gross_pct": str(row.mean_gross_pct),
    }


def _project_gross_profit_point(point: GrossProfitPoint) -> dict:
    return {
        "sale_date": point.sale_date.isoformat(),
        "sale_count": point.sale_count,
        "total_gross_realized": str(point.total_gross_realized),
    }


def _project_inventory_turn_report(report: InventoryTurnReport) -> dict:
    return {
        "sold_count": report.sold_count,
        # ``None`` on empty-window sentinel; JSON null preserves the
        # "no signal" state distinct from "distribution happens to
        # be zero."
        "mean_days": (
            str(report.mean_days) if report.mean_days is not None else None
        ),
        "p50_days": report.p50_days,
        "p90_days": report.p90_days,
        "min_days": report.min_days,
        "max_days": report.max_days,
    }


def _project_buyer_accuracy_row(row: BuyerAccuracyRow) -> dict:
    return {
        "buyer_user_id": row.buyer_user_id,
        "buyer_display": row.buyer_display,
        "vehicle_count": row.vehicle_count,
        "work_order_count": row.work_order_count,
        # Decimals → strings for the same precision-preserving reason
        # as the M8 / M9.3 sibling projections.
        "mean_absolute_variance_pct": str(row.mean_absolute_variance_pct),
        "bias_pct": str(row.bias_pct),
    }


def _project_frontline_report(report: DaysAtFrontlineReport) -> dict:
    return {
        "snapshot_count": report.snapshot_count,
        # Decimal → string; None stays null (empty window sentinel).
        "mean_p50_days": (
            str(report.mean_p50_days)
            if report.mean_p50_days is not None
            else None
        ),
        "mean_p90_days": (
            str(report.mean_p90_days)
            if report.mean_p90_days is not None
            else None
        ),
        "latest_vehicle_count": report.latest_vehicle_count,
        "latest_snapshot_at": (
            report.latest_snapshot_at.isoformat()
            if report.latest_snapshot_at is not None
            else None
        ),
    }


def _project_breach_pattern_report(report: BreachPatternReport) -> dict:
    return {
        "total_breach_count": report.total_breach_count,
        # ``None`` when the window is empty; JSON null preserves the
        # "no signal here" semantic distinct from "average is zero."
        "average_breach_days": (
            str(report.average_breach_days)
            if report.average_breach_days is not None
            else None
        ),
        "top_vendors_by_breach_count": [
            {
                "vendor_name": v.vendor_name,
                "breach_count": v.breach_count,
            }
            for v in report.top_vendors_by_breach_count
        ],
        "breaches_by_kind": [
            {
                "kind": k.kind,
                "kind_display": k.kind_display,
                "breach_count": k.breach_count,
            }
            for k in report.breaches_by_kind
        ],
    }


def _parse_positive_int_or_default(
    raw: Optional[str], *, default: int, field_name: str
) -> tuple[Optional[int], Optional[Response]]:
    """Parse a positive-int query-arg. Empty / missing → default.
    Malformed / <=0 → 400 Response.

    Kept next to :func:`_parse_iso_date_or_none` so all query-arg
    parsing lives in one region of the module.
    """
    if raw is None or raw == "":
        return default, None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, Response(
            {
                "detail": (
                    f"Invalid {field_name}: expected positive integer, "
                    f"got {raw!r}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if value <= 0:
        return None, Response(
            {
                "detail": (
                    f"Invalid {field_name}: must be > 0, got {value}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return value, None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_recon_cost_per_source(request: Request) -> Response:
    """Q1 — recon cost per acquisition source (see
    :func:`services.analytics.recon_cost_per_source`).

    Response shape::

        {
            "rows": [
                {
                    "source": "auction",
                    "source_display": "Auction",
                    "vehicle_count": 12,
                    "total_recon_cost": "18420.75",
                    "mean_recon_cost": "1535.06"
                },
                ...
            ]
        }
    """
    dealership = get_current_dealership(request)

    window_start, err = _parse_iso_date_or_none(
        request.query_params.get("window_start"),
        field_name="window_start",
    )
    if err is not None:
        return err
    window_end, err = _parse_iso_date_or_none(
        request.query_params.get("window_end"),
        field_name="window_end",
    )
    if err is not None:
        return err

    rows = analytics_service.recon_cost_per_source(
        dealership,
        window_start=window_start,
        window_end=window_end,
    )
    return Response({"rows": [_project_source_row(r) for r in rows]})


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_vendor_performance(request: Request) -> Response:
    """Q2 + Q4 — vendor performance (see
    :func:`services.analytics.vendor_performance`).

    Response shape::

        {
            "rows": [
                {
                    "vendor_slug": "acme-body",
                    "vendor_name": "ACME Body Shop",
                    "completed_count": 12,
                    "mean_completion_days": 4,
                    "mean_variance_pct": "8.75",
                    "over_budget_count": 2
                },
                ...
            ]
        }

    ``mean_completion_days`` and ``mean_variance_pct`` are ``null``
    when no WO in the window supplies the underlying data.
    """
    dealership = get_current_dealership(request)

    window_start, err = _parse_iso_date_or_none(
        request.query_params.get("window_start"),
        field_name="window_start",
    )
    if err is not None:
        return err
    window_end, err = _parse_iso_date_or_none(
        request.query_params.get("window_end"),
        field_name="window_end",
    )
    if err is not None:
        return err

    rows = analytics_service.vendor_performance(
        dealership,
        window_start=window_start,
        window_end=window_end,
    )
    return Response(
        {"rows": [_project_vendor_performance_row(r) for r in rows]}
    )


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_stage_aging_trend(request: Request) -> Response:
    """Q5 + Q9 — per-stage aging time-series (see
    :func:`services.analytics.stage_aging_trend`).

    Query args:

    - ``stage`` — required. One of :data:`VEHICLE_STAGE_CHOICES`
      keys. Malformed → 400.
    - ``window_days`` — optional (default 30). Positive integer.

    Response shape::

        {
            "stage": "recon",
            "window_days": 30,
            "points": [
                {
                    "snapshot_at": "2026-07-15T03:00:00+00:00",
                    "vehicle_count": 12,
                    "p50_days": 4,
                    "p90_days": 11
                },
                ...
            ]
        }

    ``points`` is ordered by ``snapshot_at`` ascending (left-to-right
    time-series for the M8.5 dashboard).
    """
    dealership = get_current_dealership(request)

    stage = request.query_params.get("stage")
    if not stage:
        return Response(
            {"detail": "Missing required query arg: stage."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    window_days, err = _parse_positive_int_or_default(
        request.query_params.get("window_days"),
        default=30,
        field_name="window_days",
    )
    if err is not None:
        return err

    try:
        points = analytics_service.stage_aging_trend(
            dealership, stage, window_days=window_days
        )
    except ValueError as exc:
        # Verb raises on unknown stage key — surface as 400 rather
        # than let it become a 500 or misleading empty payload.
        return Response(
            {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
        )
    return Response(
        {
            "stage": stage,
            "window_days": window_days,
            "points": [_project_aging_trend_point(p) for p in points],
        }
    )


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_sla_breach_patterns(request: Request) -> Response:
    """Q10 — SLA-breach patterns over a rolling window (see
    :func:`services.analytics.breach_patterns`).

    Query args:

    - ``window_days`` — optional (default 30). Positive integer.

    Response shape::

        {
            "window_days": 30,
            "report": {
                "total_breach_count": 42,
                "average_breach_days": "5.17",
                "top_vendors_by_breach_count": [
                    {"vendor_name": "ACME Body Shop", "breach_count": 12},
                    ...
                ],
                "breaches_by_kind": [
                    {
                        "kind": "in_progress_past_eta",
                        "kind_display": "In progress past ETA",
                        "breach_count": 27
                    },
                    ...
                ]
            }
        }

    ``average_breach_days`` is ``null`` when the window has zero
    breaches (no signal, not average-of-zero).
    """
    dealership = get_current_dealership(request)

    window_days, err = _parse_positive_int_or_default(
        request.query_params.get("window_days"),
        default=30,
        field_name="window_days",
    )
    if err is not None:
        return err

    report = analytics_service.breach_patterns(
        dealership, window_days=window_days
    )
    return Response(
        {
            "window_days": window_days,
            "report": _project_breach_pattern_report(report),
        }
    )


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_vehicle_type_recon_cost(request: Request) -> Response:
    """Q3 proxy — recon cost per vehicle-type (see
    :func:`services.analytics.vehicle_type_recon_cost`).

    Response shape::

        {
            "rows": [
                {
                    "make": "Ford",
                    "model": "F-150",
                    "vehicle_count": 8,
                    "total_recon_cost": "12480.50",
                    "mean_recon_cost": "1560.06"
                },
                ...
            ]
        }

    See ``MILESTONE_8_PLANNING.md`` §0.a SESSION_097 for the "why
    a proxy?" rationale — true profitability blocked on M9 Sale
    substrate.
    """
    dealership = get_current_dealership(request)

    window_start, err = _parse_iso_date_or_none(
        request.query_params.get("window_start"),
        field_name="window_start",
    )
    if err is not None:
        return err
    window_end, err = _parse_iso_date_or_none(
        request.query_params.get("window_end"),
        field_name="window_end",
    )
    if err is not None:
        return err

    rows = analytics_service.vehicle_type_recon_cost(
        dealership,
        window_start=window_start,
        window_end=window_end,
    )
    return Response(
        {"rows": [_project_vehicle_type_row(r) for r in rows]}
    )


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_days_at_frontline_proxy(request: Request) -> Response:
    """Q8 proxy — days-at-frontline aggregate (see
    :func:`services.analytics.days_at_frontline_proxy`).

    Query args:

    - ``window_days`` — optional (default 30). Positive integer.

    Response shape::

        {
            "window_days": 30,
            "report": {
                "snapshot_count": 30,
                "mean_p50_days": "4.60",
                "mean_p90_days": "18.13",
                "latest_vehicle_count": 42,
                "latest_snapshot_at": "2026-08-01T03:00:00+00:00"
            }
        }

    Every field in ``report`` renders as ``null`` when
    ``snapshot_count == 0`` — the "no signal" state is distinct
    from "average is zero."
    """
    dealership = get_current_dealership(request)

    window_days, err = _parse_positive_int_or_default(
        request.query_params.get("window_days"),
        default=30,
        field_name="window_days",
    )
    if err is not None:
        return err

    report = analytics_service.days_at_frontline_proxy(
        dealership, window_days=window_days
    )
    return Response(
        {
            "window_days": window_days,
            "report": _project_frontline_report(report),
        }
    )


# ---------------------------------------------------------------------------
# Milestone 9 · Increment 3 (SESSION_102) — analytics extensions unlocking
# M8 deferrals (Q3 true / Q6 gross-profit trend / Q8 true inventory turn).
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_vehicle_type_profitability(
    request: Request,
) -> Response:
    """Q3 true — profitability per vehicle-type (see
    :func:`services.analytics.vehicle_type_profitability`).

    Sibling of :func:`admin_analytics_vehicle_type_recon_cost`
    (M8.4 proxy). Both endpoints coexist per M8 §6 lesson 11.

    Response shape::

        {
            "rows": [
                {
                    "make": "Ford",
                    "model": "F-150",
                    "sold_count": 5,
                    "total_sale_gross": "12500.00",
                    "total_sold_price": "185000.00",
                    "mean_gross_pct": "6.75"
                },
                ...
            ]
        }
    """
    dealership = get_current_dealership(request)

    window_start, err = _parse_iso_date_or_none(
        request.query_params.get("window_start"),
        field_name="window_start",
    )
    if err is not None:
        return err
    window_end, err = _parse_iso_date_or_none(
        request.query_params.get("window_end"),
        field_name="window_end",
    )
    if err is not None:
        return err

    rows = analytics_service.vehicle_type_profitability(
        dealership,
        window_start=window_start,
        window_end=window_end,
    )
    return Response(
        {
            "rows": [
                _project_vehicle_type_profitability_row(r) for r in rows
            ]
        }
    )


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_gross_profit_trend(request: Request) -> Response:
    """Q6 — daily-bucket gross-profit time series (see
    :func:`services.analytics.gross_profit_trend`).

    Query args:

    - ``window_days`` — optional (default 90). Positive integer.

    Response shape::

        {
            "window_days": 90,
            "points": [
                {
                    "sale_date": "2026-07-15",
                    "sale_count": 3,
                    "total_gross_realized": "8250.00"
                },
                ...
            ]
        }

    Points are sparse (dates with zero sales in the window are
    omitted). Empty window returns ``"points": []``.
    """
    dealership = get_current_dealership(request)

    window_days, err = _parse_positive_int_or_default(
        request.query_params.get("window_days"),
        default=90,
        field_name="window_days",
    )
    if err is not None:
        return err

    points = analytics_service.gross_profit_trend(
        dealership, window_days=window_days
    )
    return Response(
        {
            "window_days": window_days,
            "points": [_project_gross_profit_point(p) for p in points],
        }
    )


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_inventory_turn(request: Request) -> Response:
    """Q8 true — days-from-frontline-to-sale distribution (see
    :func:`services.analytics.inventory_turn`).

    Sibling of :func:`admin_analytics_days_at_frontline_proxy`
    (M8.4 proxy). Both endpoints coexist per M8 §6 lesson 11.

    Query args:

    - ``window_days`` — optional (default 90). Positive integer.

    Response shape::

        {
            "window_days": 90,
            "report": {
                "sold_count": 42,
                "mean_days": "22.31",
                "p50_days": 18,
                "p90_days": 47,
                "min_days": 3,
                "max_days": 89
            }
        }

    Every field in ``report`` (other than ``sold_count``) is
    ``null`` when ``sold_count == 0`` — the "no signal" state is
    distinct from "distribution happens to be zero."
    """
    dealership = get_current_dealership(request)

    window_days, err = _parse_positive_int_or_default(
        request.query_params.get("window_days"),
        default=90,
        field_name="window_days",
    )
    if err is not None:
        return err

    report = analytics_service.inventory_turn(
        dealership, window_days=window_days
    )
    return Response(
        {
            "window_days": window_days,
            "report": _project_inventory_turn_report(report),
        }
    )


# ---------------------------------------------------------------------------
# Milestone 9 · Increment 4 (SESSION_103) — Q7 buyer estimate accuracy.
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes(_M81_PERMS)
def admin_analytics_buyer_estimate_accuracy(
    request: Request,
) -> Response:
    """Q7 — per-buyer recon-cost estimate accuracy (see
    :func:`services.analytics.buyer_estimate_accuracy`).

    Query args:

    - ``window_days`` — optional (default 90). Positive integer.
    - ``buyer_user_id`` — optional. When present, filters to that
      buyer only (0 or 1 rows). When absent, returns all buyers
      with contributing data.

    Response shape::

        {
            "window_days": 90,
            "buyer_user_id": null,
            "rows": [
                {
                    "buyer_user_id": 42,
                    "buyer_display": "Alice Bidder",
                    "vehicle_count": 8,
                    "work_order_count": 23,
                    "mean_absolute_variance_pct": "12.50",
                    "bias_pct": "-3.25"
                },
                ...
            ]
        }

    Rows sorted by ``mean_absolute_variance_pct`` ascending (most
    accurate buyers first).
    """
    dealership = get_current_dealership(request)

    window_days, err = _parse_positive_int_or_default(
        request.query_params.get("window_days"),
        default=90,
        field_name="window_days",
    )
    if err is not None:
        return err

    buyer_raw = request.query_params.get("buyer_user_id")
    buyer_user_id: Optional[int] = None
    if buyer_raw is not None and buyer_raw != "":
        try:
            buyer_user_id = int(buyer_raw)
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": (
                        f"Invalid buyer_user_id: expected integer, "
                        f"got {buyer_raw!r}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    rows = analytics_service.buyer_estimate_accuracy(
        dealership,
        window_days=window_days,
        buyer_user_id=buyer_user_id,
    )
    return Response(
        {
            "window_days": window_days,
            "buyer_user_id": buyer_user_id,
            "rows": [_project_buyer_accuracy_row(r) for r in rows],
        }
    )
