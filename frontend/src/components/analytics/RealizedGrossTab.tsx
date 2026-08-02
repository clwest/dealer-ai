// Milestone 9 · Increment 5 (SESSION_104) — Realized Gross tab.
//
// Fifth tab on /dealer-ai-analytics/. Wires the four "true" M9
// aggregations that closed M8 deferrals:
//
//   Q3 true — vehicle-type profitability (rollup table)
//   Q6      — gross-profit trend (per-day line chart)
//   Q8 true — days-from-frontline-to-sale (summary card)
//   Q7      — per-buyer estimate accuracy (rank table)
//
// Per §0.a SESSION_104 Decision A: Q7 bundles into this tab rather
// than shipping as a sixth dedicated tab. All four cuts answer
// "who / what produced the profit and how efficiently" — grouping
// keeps the operator's mental model tight.

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  AnalyticsSection,
  EmptyRows,
  type LoadState,
} from "@/components/analytics/AnalyticsSection";
import {
  ForbiddenError,
  UnauthenticatedError,
} from "@/lib/authFetch";
import {
  fetchBuyerEstimateAccuracy,
  fetchGrossProfitTrend,
  fetchInventoryTurn,
  fetchVehicleTypeProfitability,
  formatMoney,
  formatPercent,
  formatShortDate,
  type BuyerAccuracyRow,
  type GrossProfitPoint,
  type InventoryTurnReport,
  type VehicleTypeProfitabilityRow,
} from "@/lib/analyticsApi";

export function RealizedGrossTab() {
  return (
    <div className="flex flex-col">
      <VehicleTypeProfitabilitySection />
      <GrossProfitTrendSection />
      <InventoryTurnSection />
      <BuyerAccuracyRankSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Q3 true — vehicle-type profitability
// ---------------------------------------------------------------------------

function VehicleTypeProfitabilitySection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<VehicleTypeProfitabilityRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchVehicleTypeProfitability()
      .then((data) => {
        if (cancelled) return;
        setRows(data.rows);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof UnauthenticatedError || err instanceof ForbiddenError) {
          setState("forbidden");
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AnalyticsSection
      title="Vehicle-type profitability"
      description="Q3 — realized gross rolled up per (make, model). Sold vehicles only."
      loadState={state}
      errorMessage={error}
    >
      {rows.length === 0 ? (
        <EmptyRows label="No sales in the window yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-4 font-medium">Make</th>
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 pr-4 font-medium">Sold</th>
                <th className="py-2 pr-4 font-medium">Total gross</th>
                <th className="py-2 pr-4 font-medium">Total sold price</th>
                <th className="py-2 font-medium">Mean gross %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={`${row.make}-${row.model}`}
                  className="border-b border-border/60"
                >
                  <td className="py-2 pr-4">{row.make}</td>
                  <td className="py-2 pr-4">{row.model}</td>
                  <td className="py-2 pr-4 tabular-nums">{row.sold_count}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {formatMoney(row.total_sale_gross)}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {formatMoney(row.total_sold_price)}
                  </td>
                  <td className="py-2 tabular-nums">
                    {formatPercent(row.mean_gross_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AnalyticsSection>
  );
}

// ---------------------------------------------------------------------------
// Q6 — gross-profit trend
// ---------------------------------------------------------------------------

function GrossProfitTrendSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [points, setPoints] = useState<GrossProfitPoint[]>([]);
  const [windowDays, setWindowDays] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchGrossProfitTrend()
      .then((data) => {
        if (cancelled) return;
        setPoints(data.points);
        setWindowDays(data.window_days);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof UnauthenticatedError || err instanceof ForbiddenError) {
          setState("forbidden");
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const chartData = points.map((p) => ({
    date: formatShortDate(p.sale_date),
    total: Number(p.total_gross_realized),
    count: p.sale_count,
  }));

  return (
    <AnalyticsSection
      title="Gross-profit trend"
      description={
        windowDays > 0
          ? `Q6 — daily-bucket time series over the last ${windowDays} days. Sparse — days with zero sales are omitted.`
          : "Q6 — daily-bucket time series over the rolling window."
      }
      loadState={state}
      errorMessage={error}
    >
      {points.length === 0 ? (
        <EmptyRows label="No sales in the window yet." />
      ) : (
        <div className="h-64 w-full" data-testid="gross-profit-trend-chart">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value) =>
                  typeof value === "number"
                    ? formatMoney(value.toFixed(2))
                    : String(value)
                }
              />
              <Line
                type="monotone"
                dataKey="total"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </AnalyticsSection>
  );
}

// ---------------------------------------------------------------------------
// Q8 true — inventory turn
// ---------------------------------------------------------------------------

function InventoryTurnSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<InventoryTurnReport | null>(null);
  const [windowDays, setWindowDays] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchInventoryTurn()
      .then((data) => {
        if (cancelled) return;
        setReport(data.report);
        setWindowDays(data.window_days);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof UnauthenticatedError || err instanceof ForbiddenError) {
          setState("forbidden");
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AnalyticsSection
      title="Inventory turn (days-to-sale)"
      description={
        windowDays > 0
          ? `Q8 — days from first frontline entry to sale, across the last ${windowDays} days.`
          : "Q8 — days from first frontline entry to sale."
      }
      loadState={state}
      errorMessage={error}
    >
      {report === null || report.sold_count === 0 ? (
        <EmptyRows label="No sold vehicles with frontline history in the window." />
      ) : (
        <div
          className="grid grid-cols-2 gap-4 md:grid-cols-3"
          data-testid="inventory-turn-summary"
        >
          <StatCard label="Sold vehicles" value={String(report.sold_count)} />
          <StatCard
            label="Mean days"
            value={report.mean_days ?? "—"}
          />
          <StatCard
            label="Median (p50)"
            value={report.p50_days !== null ? String(report.p50_days) : "—"}
          />
          <StatCard
            label="p90"
            value={report.p90_days !== null ? String(report.p90_days) : "—"}
          />
          <StatCard
            label="Min"
            value={report.min_days !== null ? String(report.min_days) : "—"}
          />
          <StatCard
            label="Max"
            value={report.max_days !== null ? String(report.max_days) : "—"}
          />
        </div>
      )}
    </AnalyticsSection>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Q7 — buyer estimate accuracy
// ---------------------------------------------------------------------------

function BuyerAccuracyRankSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<BuyerAccuracyRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchBuyerEstimateAccuracy()
      .then((data) => {
        if (cancelled) return;
        setRows(data.rows);
        setState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof UnauthenticatedError || err instanceof ForbiddenError) {
          setState("forbidden");
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
          setState("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AnalyticsSection
      title="Buyer estimate accuracy"
      description="Q7 — per-buyer recon-cost estimate accuracy on their acquisitions. Most accurate buyers ranked first."
      loadState={state}
      errorMessage={error}
    >
      {rows.length === 0 ? (
        <EmptyRows label="No buyer data in the window yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-4 font-medium">Buyer</th>
                <th className="py-2 pr-4 font-medium">Vehicles</th>
                <th className="py-2 pr-4 font-medium">Work orders</th>
                <th className="py-2 pr-4 font-medium">Mean abs. variance</th>
                <th className="py-2 font-medium">Bias</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.buyer_user_id}
                  className="border-b border-border/60"
                >
                  <td className="py-2 pr-4">{row.buyer_display}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {row.vehicle_count}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {row.work_order_count}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {formatPercent(row.mean_absolute_variance_pct)}
                  </td>
                  <td className="py-2 tabular-nums">
                    {formatPercent(row.bias_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AnalyticsSection>
  );
}
