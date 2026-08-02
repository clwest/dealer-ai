// Milestone 8 · Increment 5 (SESSION_098) — SLA Breach Patterns tab.
//
// Wires Q10 (breach_patterns). Two mini charts (top vendors bar +
// kind distribution) + one scorecard for average breach days.

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
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
  fetchSlaBreachPatterns,
  type BreachPatternReport,
} from "@/lib/analyticsApi";

const KIND_COLORS = ["hsl(var(--primary))", "hsl(var(--destructive))"];

export function SlaBreachTab() {
  const [state, setState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<BreachPatternReport | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    fetchSlaBreachPatterns()
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
      title="SLA breach patterns"
      description="Q10 — SLA breaches over the last 30 days: top vendors, kind distribution, average days past SLA."
      loadState={state}
      errorMessage={error}
    >
      {report === null || report.total_breach_count === 0 ? (
        <EmptyRows label="No SLA breaches in the window." />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Scorecard
              label="Total breaches"
              value={String(report.total_breach_count)}
            />
            <Scorecard
              label="Avg days past SLA"
              value={
                report.average_breach_days === null
                  ? "—"
                  : `${report.average_breach_days}d`
              }
            />
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <TopVendorsChart report={report} />
            <KindDistributionChart report={report} />
          </div>
        </div>
      )}
    </AnalyticsSection>
  );
}

function Scorecard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">
        {value}
      </div>
    </div>
  );
}

function TopVendorsChart({ report }: { report: BreachPatternReport }) {
  const data = report.top_vendors_by_breach_count.map((v) => ({
    name: v.vendor_name,
    breaches: v.breach_count,
  }));
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium">Top vendors by breach count</h3>
      <div className="h-56" data-testid="top-vendors-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11 }}
              width={120}
            />
            <Tooltip />
            <Bar dataKey="breaches" fill="hsl(var(--primary))" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function KindDistributionChart({ report }: { report: BreachPatternReport }) {
  const data = report.breaches_by_kind.map((k) => ({
    name: k.kind_display,
    value: k.breach_count,
  }));
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium">Breaches by kind</h3>
      <div className="h-56" data-testid="kind-distribution-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              outerRadius={80}
              label={(entry) => `${entry.name} (${entry.value})`}
            >
              {data.map((_, idx) => (
                <Cell
                  key={idx}
                  fill={KIND_COLORS[idx % KIND_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
