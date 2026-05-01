// Manager Phase 4: per-advisor "my leads" table.
//
// Compact list used by AdvisorWorkspacePage. Each row has the same shape
// as HandoffQueue's row (urgency / when / customer / target / vehicles)
// plus a "Draft follow-up" button that opens FollowUpDraftModal.
// Click on the row body opens the existing LeadDetailModal.

import { Mail, MessageSquare, Phone } from "lucide-react";

import type { AdminLead } from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface Props {
  leads: AdminLead[];
  emptyText: string;
  onRowClick: (leadId: number) => void;
  onDraftFollowUp?: (lead: AdminLead) => void;
}

const URGENCY_LABEL: Record<string, string> = {
  immediate: "Buying now",
  this_week: "This week",
  this_month: "This month",
  researching: "Researching",
};

const URGENCY_TONE: Record<string, string> = {
  immediate: "bg-red-50 text-red-700 border-red-200",
  this_week: "bg-amber-50 text-amber-700 border-amber-200",
  this_month: "bg-blue-50 text-blue-700 border-blue-200",
  researching: "bg-slate-50 text-slate-600 border-slate-200",
};

function timeAgo(iso: string | null) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function MyLeadsTable({
  leads,
  emptyText,
  onRowClick,
  onDraftFollowUp,
}: Props) {
  if (leads.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
        {emptyText}
      </div>
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-2">Urgency</th>
            <th className="px-4 py-2">Assigned</th>
            <th className="px-4 py-2">Customer</th>
            <th className="px-4 py-2">Target</th>
            <th className="px-4 py-2">Interested vehicles</th>
            <th className="px-4 py-2"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {leads.map((lead) => (
            <tr key={lead.id} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <span
                  className={cn(
                    "inline-block rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                    URGENCY_TONE[lead.urgency] ??
                      "bg-slate-50 text-slate-500 border-slate-200",
                  )}
                >
                  {URGENCY_LABEL[lead.urgency] ?? "—"}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-slate-500">
                {timeAgo(lead.assigned_at)}
              </td>
              <td
                className="cursor-pointer px-4 py-3"
                onClick={() => onRowClick(lead.id)}
              >
                <div className="font-semibold text-ford-ink">
                  {lead.name || "Anonymous"}
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                  {lead.phone ? (
                    <span className="inline-flex items-center gap-1">
                      <Phone className="h-3 w-3" />
                      {lead.phone}
                    </span>
                  ) : null}
                  {lead.email ? (
                    <span className="inline-flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {lead.email}
                    </span>
                  ) : null}
                </div>
              </td>
              <td className="px-4 py-3 text-xs">
                {lead.target_monthly_payment ? (
                  <div>
                    {formatCurrency(lead.target_monthly_payment)}/mo
                    {lead.down_payment ? (
                      <div className="text-[11px] text-slate-500">
                        {formatCurrency(lead.down_payment)} down
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </td>
              <td className="px-4 py-3 text-xs">
                {lead.interested_vehicles.length > 0 ? (
                  <ul className="space-y-0.5">
                    {lead.interested_vehicles.slice(0, 2).map((v) => (
                      <li key={v.id} className="truncate text-slate-700">
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
                  <span className="text-slate-400">none flagged</span>
                )}
              </td>
              <td className="px-4 py-3 text-right">
                {onDraftFollowUp ? (
                  <button
                    type="button"
                    onClick={() => onDraftFollowUp(lead)}
                    className="inline-flex items-center gap-1 rounded-md border border-purple-300 bg-purple-50 px-2 py-1 text-[11px] font-semibold text-purple-700 hover:bg-purple-100"
                  >
                    <MessageSquare className="h-3 w-3" />
                    Draft follow-up
                  </button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
