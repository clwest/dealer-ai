// Milestone 8 · Increment 5 (SESSION_098) — Vendor Performance tab.
//
// Wires Q2 + Q4 (vendor_performance). Table with sortable columns
// isn't shipped v1 — the default backend sort (completed_count desc)
// is the operator's default view; per-column sort waits for
// operator evidence.

import { useEffect, useState } from "react";

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
  fetchVendorPerformance,
  formatPercent,
  type VendorPerformanceRow,
} from "@/lib/analyticsApi";

export function VendorPerformanceTab() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<VendorPerformanceRow[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchVendorPerformance()
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
      title="Vendor performance"
      description="Q2 + Q4 — completed outsourced WO count, mean turnaround, cost variance vs estimate, and over-budget count per vendor."
      loadState={state}
      errorMessage={error}
    >
      {rows.length === 0 ? (
        <EmptyRows label="No completed outsourced work orders yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="py-2 pr-4 font-medium">Vendor</th>
                <th className="py-2 pr-4 font-medium">Completed</th>
                <th className="py-2 pr-4 font-medium">Mean days</th>
                <th className="py-2 pr-4 font-medium">
                  Mean |variance| %
                </th>
                <th className="py-2 font-medium">Over budget</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.vendor_slug}
                  className="border-b border-border/60"
                >
                  <td className="py-2 pr-4">{row.vendor_name}</td>
                  <td className="py-2 pr-4 tabular-nums">
                    {row.completed_count}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {row.mean_completion_days === null
                      ? "—"
                      : `${row.mean_completion_days}d`}
                  </td>
                  <td className="py-2 pr-4 tabular-nums">
                    {formatPercent(row.mean_variance_pct)}
                  </td>
                  <td className="py-2 tabular-nums">
                    {row.over_budget_count}
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
