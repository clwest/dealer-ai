// Milestone 8 · Increment 5 (SESSION_098) — Lifecycle Aging tab.
//
// Wires Q5 + Q9 (stage_aging_trend) + Q8 (days_at_frontline_proxy).
// Per-stage trend chart with a stage selector + a frontline
// scorecard tile. Stage vocabulary matches VEHICLE_STAGE_CHOICES.

import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
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
  fetchDaysAtFrontlineProxy,
  fetchStageAgingTrend,
  formatSnapshotAt,
  type AgingTrendPoint,
  type DaysAtFrontlineReport,
} from "@/lib/analyticsApi";

// Stage vocabulary — matches VEHICLE_STAGE_CHOICES on the backend
// verbatim. If a stage is added at M5+, add it here (server rejects
// unknown values with 400, so the frontend selector must stay in
// sync). The M7.3 snapshot job persists per-stage snapshots for
// stages that actually have vehicles; empty stages simply produce
// no points.
const STAGE_OPTIONS = [
  { value: "incoming", label: "Incoming" },
  { value: "inspection", label: "Inspection" },
  { value: "recon", label: "Recon" },
  { value: "qc", label: "QC" },
  { value: "detail", label: "Detail" },
  { value: "photography", label: "Photography" },
  { value: "listing", label: "Listing" },
  { value: "frontline", label: "Frontline" },
  { value: "wholesale_out", label: "Wholesale out" },
  { value: "hold_reserved", label: "Hold / reserved" },
  { value: "company_use", label: "Company use" },
  { value: "off_market", label: "Off market" },
] as const;

export function LifecycleAgingTab() {
  return (
    <div className="flex flex-col">
      <FrontlineScorecardSection />
      <StageAgingTrendSection />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Q8 proxy — days-at-frontline scorecard
// ---------------------------------------------------------------------------

function FrontlineScorecardSection() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<DaysAtFrontlineReport | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchDaysAtFrontlineProxy()
      .then((data) => {
        if (cancelled) return;
        setReport(data.report);
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
      title="Days at frontline (proxy)"
      description="Q8 proxy — mean p50 / p90 days-in-stage across the last 30 days of M7.3 snapshots. True inventory-turn lands with M9 Sale data."
      loadState={state}
      errorMessage={error}
    >
      {report === null || report.snapshot_count === 0 ? (
        <EmptyRows label="No frontline snapshots in the window yet — M7.3 snapshot job may not have populated data yet." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Scorecard label="Snapshots" value={String(report.snapshot_count)} />
          <Scorecard
            label="Mean p50"
            value={report.mean_p50_days === null ? "—" : `${report.mean_p50_days}d`}
          />
          <Scorecard
            label="Mean p90"
            value={report.mean_p90_days === null ? "—" : `${report.mean_p90_days}d`}
          />
          <Scorecard
            label="Latest vehicles"
            value={
              report.latest_vehicle_count === null
                ? "—"
                : String(report.latest_vehicle_count)
            }
            caption={
              report.latest_snapshot_at
                ? `as of ${formatSnapshotAt(report.latest_snapshot_at)}`
                : undefined
            }
          />
        </div>
      )}
    </AnalyticsSection>
  );
}

function Scorecard({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption?: string;
}) {
  return (
    <div className="rounded-md border border-border bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">
        {value}
      </div>
      {caption ? (
        <div className="mt-0.5 text-[11px] text-muted-foreground">
          {caption}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Q5 + Q9 — stage aging trend
// ---------------------------------------------------------------------------

function StageAgingTrendSection() {
  const [stage, setStage] = useState<string>("recon");
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [points, setPoints] = useState<AgingTrendPoint[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchStageAgingTrend(stage)
      .then((data) => {
        if (cancelled) return;
        setPoints(data.points);
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
  }, [stage]);

  return (
    <AnalyticsSection
      title="Stage aging trend"
      description="Q5 + Q9 — days-in-stage p50 + p90 over the last 30 days of M7.3 snapshots. Switch stages to trend a different lifecycle bucket."
      loadState={state}
      errorMessage={error}
    >
      <div className="flex flex-col gap-4">
        <label className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Stage:</span>
          <select
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            aria-label="Lifecycle stage"
          >
            {STAGE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>

        {points.length === 0 ? (
          <EmptyRows label={`No snapshots for the "${stage}" stage in the window.`} />
        ) : (
          <div
            className="h-64 w-full"
            data-testid={`stage-aging-trend-chart-${stage}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={points.map((p) => ({
                  x: formatSnapshotAt(p.snapshot_at),
                  p50: p.p50_days,
                  p90: p.p90_days,
                  count: p.vehicle_count,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis dataKey="x" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="p50" stroke="hsl(var(--primary))" />
                <Line type="monotone" dataKey="p90" stroke="hsl(var(--destructive))" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </AnalyticsSection>
  );
}
