// Manager Phase 1: handoff/triage queue panel.
//
// Filtered view of CustomerLead rows that need advisor attention.
// Reuses the existing /admin/leads/ endpoint with optional query
// params (handed_off, urgency, since, ordering=urgency). Click a row
// → existing LeadDetailModal handles drill-down + handoff action.

import { useEffect, useState } from "react";
import { AlertCircle, Inbox, RefreshCw } from "lucide-react";

import { fetchAdminLeads } from "@/lib/api";
import type { AdminLead } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { cn } from "@/lib/utils";

type Preset = "all_open" | "immediate" | "this_week" | "today";
type AssignmentFilter = "any" | "unassigned" | "assigned";

const PRESET_LABELS: Record<Preset, string> = {
  all_open: "All open",
  immediate: "Buying now",
  this_week: "This week",
  today: "Today (24h)",
};

const ASSIGNMENT_LABELS: Record<AssignmentFilter, string> = {
  any: "Any",
  unassigned: "Unassigned",
  assigned: "Assigned",
};

const URGENCY_ORDER = ["immediate", "this_week", "this_month", "researching"];

function urgencyLabel(value: string | null | undefined): string {
  switch (value) {
    case "immediate":
      return "Buying now";
    case "this_week":
      return "This week";
    case "this_month":
      return "This month";
    case "researching":
      return "Researching";
    default:
      return "—";
  }
}

function urgencyToneClass(value: string | null | undefined): string {
  switch (value) {
    case "immediate":
      return "bg-red-50 text-red-700 border-red-200";
    case "this_week":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "this_month":
      return "bg-blue-50 text-blue-700 border-blue-200";
    case "researching":
      return "bg-slate-50 text-slate-600 border-slate-200";
    default:
      return "bg-slate-50 text-slate-500 border-slate-200";
  }
}

function timeAgo(iso: string) {
  const then = new Date(iso).getTime();
  const diffMin = (Date.now() - then) / 60000;
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${Math.round(diffMin)}m ago`;
  const diffHr = diffMin / 60;
  if (diffHr < 24) return `${Math.round(diffHr)}h ago`;
  return `${Math.round(diffHr / 24)}d ago`;
}

interface Props {
  refreshKey: number;
  onRowClick: (leadId: number) => void;
}

export default function HandoffQueue({ refreshKey, onRowClick }: Props) {
  const [preset, setPreset] = useState<Preset>("all_open");
  const [assignment, setAssignment] = useState<AssignmentFilter>("any");
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const opts: Parameters<typeof fetchAdminLeads>[0] = {
      limit: 25,
      handed_off: false,
      ordering: "urgency",
    };
    if (preset === "immediate") opts.urgency = ["immediate"];
    else if (preset === "this_week")
      opts.urgency = ["immediate", "this_week"];
    else if (preset === "today") opts.since = "24h";

    fetchAdminLeads(opts)
      .then((res) => {
        if (cancelled) return;
        // Phase 4: assignment filter is applied client-side because the
        // existing /admin/leads/ endpoint doesn't expose it as a query
        // param yet. Demo-scale lists (≤200 rows) make this fine.
        let rows = res.results;
        if (assignment === "unassigned") {
          rows = rows.filter((r) => r.assigned_to == null);
        } else if (assignment === "assigned") {
          rows = rows.filter((r) => r.assigned_to != null);
        }
        setLeads(rows);
        setCount(rows.length);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Load failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [preset, assignment, refreshKey]);

  const urgentCount = leads.filter((l) => l.urgency === "immediate").length;

  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-red-50 text-red-600">
            <Inbox className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-ford-ink">
              Handoff queue
            </h2>
            <div className="text-xs text-slate-500">
              {count} open · {urgentCount} urgent
              {loading ? " · loading…" : ""}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-wrap gap-1">
            {(Object.keys(PRESET_LABELS) as Preset[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPreset(p)}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-xs font-medium transition",
                  preset === p
                    ? "border-ford-blue bg-ford-blue text-white"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
                )}
              >
                {PRESET_LABELS[p]}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Assignment
            </span>
            {(Object.keys(ASSIGNMENT_LABELS) as AssignmentFilter[]).map(
              (a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => setAssignment(a)}
                  className={cn(
                    "rounded-md border px-2 py-1 text-[11px] font-medium transition",
                    assignment === a
                      ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                      : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50",
                  )}
                >
                  {ASSIGNMENT_LABELS[a]}
                </button>
              ),
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="border-b border-red-100 bg-red-50 px-5 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Urgency</th>
              <th className="px-4 py-2">When</th>
              <th className="px-4 py-2">Customer</th>
              <th className="px-4 py-2">Target</th>
              <th className="px-4 py-2">Vehicles</th>
              <th className="px-4 py-2">Next action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!loading && leads.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center text-sm text-slate-500"
                >
                  <div className="flex flex-col items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-slate-300" />
                    <span>No leads need handoff right now.</span>
                  </div>
                </td>
              </tr>
            )}
            {loading && leads.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  <RefreshCw className="mx-auto h-4 w-4 animate-spin" />
                </td>
              </tr>
            )}
            {leads.map((lead) => (
              <tr
                key={lead.id}
                className="cursor-pointer hover:bg-slate-50"
                onClick={() => onRowClick(lead.id)}
              >
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                      urgencyToneClass(lead.urgency),
                    )}
                  >
                    {urgencyLabel(lead.urgency)}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {timeAgo(lead.created_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="font-semibold text-ford-ink">{lead.name}</div>
                  <div className="text-xs text-slate-500">
                    {lead.phone || lead.email || "—"}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {lead.target_monthly_payment ? (
                    <div>
                      {formatCurrency(lead.target_monthly_payment)}/mo
                      {lead.down_payment ? (
                        <div className="text-xs text-slate-500">
                          {formatCurrency(lead.down_payment)} down
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-3">
                  {lead.interested_vehicles.length > 0 ? (
                    <ul className="space-y-0.5">
                      {lead.interested_vehicles.slice(0, 2).map((v) => (
                        <li
                          key={v.id}
                          className="text-xs text-slate-700"
                          title={`${v.display_name} · ${v.stock_number}`}
                        >
                          {v.display_name}
                        </li>
                      ))}
                      {lead.interested_vehicles.length > 2 ? (
                        <li className="text-[11px] text-slate-400">
                          +{lead.interested_vehicles.length - 2} more
                        </li>
                      ) : null}
                    </ul>
                  ) : (
                    <span className="text-xs text-slate-400">none flagged</span>
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-slate-600">
                  {lead.recommended_next_action || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// Keep urgency-rank stable even when the backend ordering helper is
// down. (Not currently used — the queue trusts the server's
// ordering=urgency — but exported for future client-side sort needs.)
export const URGENCY_RANK_FOR_TESTS = URGENCY_ORDER;
