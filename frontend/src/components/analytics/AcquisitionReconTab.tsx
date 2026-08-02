// Milestone 8 · Increment 5 (SESSION_098) — Acquisition & Recon Cost tab.
//
// Wires Q1 (recon per acquisition source) + Q3 proxy (recon per
// vehicle-type). Two rollup tables + one bar chart each. The proxy
// naming is deliberate — see MILESTONE_8_PLANNING.md §0.a
// SESSION_097 for why Q3 is titled "Recon Cost by Vehicle Type"
// and not "Vehicle Type Profitability" pending M9 Sale substrate.

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
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
  fetchReconCostPerSource,
  fetchVehicleTypeReconCost,
  formatMoney,
  type SourcePerformanceRow,
  type VehicleTypeReconCostRow,
} from "@/lib/analyticsApi";

export function AcquisitionReconTab() {
  return (
    <div className="flex flex-col">
      <SourceRollupSection />
      <VehicleTypeRollupSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Q1 — recon cost per acquisition source
// ---------------------------------------------------------------------------

function SourceRollupSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<SourcePerformanceRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchReconCostPerSource()
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
      title="Recon cost by acquisition source"
      description="Q1 — rolled up across all recon-category costs, committed only."
      loadState={state}
      errorMessage={error}
    >
      {rows.length === 0 ? (
        <EmptyRows label="No recon-cost history yet." />
      ) : (
        <div className="flex flex-col gap-6">
          <SourceTable rows={rows} />
          <SourceChart rows={rows} />
        </div>
      )}
    </AnalyticsSection>
  );
}

function SourceTable({ rows }: { rows: SourcePerformanceRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            <th className="py-2 pr-4 font-medium">Source</th>
            <th className="py-2 pr-4 font-medium">Vehicles</th>
            <th className="py-2 pr-4 font-medium">Total recon cost</th>
            <th className="py-2 font-medium">Mean per vehicle</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.source} className="border-b border-border/60">
              <td className="py-2 pr-4">{row.source_display}</td>
              <td className="py-2 pr-4 tabular-nums">
                {row.vehicle_count}
              </td>
              <td className="py-2 pr-4 tabular-nums">
                {formatMoney(row.total_recon_cost)}
              </td>
              <td className="py-2 tabular-nums">
                {formatMoney(row.mean_recon_cost)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SourceChart({ rows }: { rows: SourcePerformanceRow[] }) {
  const chartData = rows.map((r) => ({
    name: r.source_display,
    total: Number(r.total_recon_cost),
  }));
  return (
    <div className="h-64 w-full" data-testid="source-recon-cost-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip
            formatter={(value) =>
              typeof value === "number"
                ? formatMoney(value.toFixed(2))
                : String(value)
            }
          />
          <Bar dataKey="total" fill="hsl(var(--primary))" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Q3 proxy — recon cost per vehicle-type
// ---------------------------------------------------------------------------

function VehicleTypeRollupSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<VehicleTypeReconCostRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchVehicleTypeReconCost()
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
      title="Recon cost by vehicle type"
      description={
        // Naming is honest — this is a proxy pending M9 Sale
        // substrate (see MILESTONE_8_PLANNING.md §0.a SESSION_097).
        "Q3 proxy — mean recon cost per (make, model). True vehicle-type profitability lands with M9 Sale data."
      }
      loadState={state}
      errorMessage={error}
    >
      {rows.length === 0 ? (
        <EmptyRows label="No recon-cost history by vehicle type yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-4 font-medium">Make</th>
                <th className="py-2 pr-4 font-medium">Model</th>
                <th className="py-2 pr-4 font-medium">Vehicles</th>
                <th className="py-2 pr-4 font-medium">Total recon cost</th>
                <th className="py-2 font-medium">Mean per vehicle</th>
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
                  <td className="py-2 pr-4 tabular-nums">
                    {row.vehicle_count}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {formatMoney(row.total_recon_cost)}
                  </td>
                  <td className="py-2 tabular-nums">
                    {formatMoney(row.mean_recon_cost)}
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
