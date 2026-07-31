// Manager Phase 2: 5-column sales pipeline + demand-vs-supply panel.
//
// Reads the additive /admin/pipeline/ endpoint (see PROJECT_PIPELINE.md
// §1d). Every CustomerLead lands in exactly one column based on the
// derived stage rules in services/pipeline.py. Cards are click-through
// to the existing LeadDetailModal — no new mutation surface.
//
// Demand-vs-supply panel below the columns flags bands where open lead
// demand exceeds available inventory (mismatch tier) or is keeping
// pace under pressure (tight tier).

import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import {
  fetchAdminPipeline,
  type DemandBucket,
  type PipelineLead,
  type PipelineResponse,
  type PipelineStage,
  type PipelineStageKey,
} from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

interface Props {
  refreshKey: number;
  onCardClick: (leadId: number) => void;
  onPayloadChange?: (payload: PipelineResponse | null) => void;
}

const STAGE_DISPLAY_ORDER: PipelineStageKey[] = [
  "high_intent",
  "new",
  "needs_handoff",
  "researching",
  "contacted",
];

const STAGE_TONE: Record<PipelineStageKey, string> = {
  high_intent: "bg-red-50 text-red-700 border-red-200",
  new: "bg-amber-50 text-amber-700 border-amber-200",
  needs_handoff: "bg-slate-100 text-slate-700 border-slate-200",
  researching: "bg-blue-50 text-blue-700 border-blue-200",
  contacted: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const STAGE_BADGE_TONE: Record<PipelineStageKey, string> = {
  high_intent: "bg-red-100 text-red-700",
  new: "bg-amber-100 text-amber-700",
  needs_handoff: "bg-slate-200 text-slate-700",
  researching: "bg-blue-100 text-blue-700",
  contacted: "bg-emerald-100 text-emerald-700",
};

const TIER_TONE: Record<DemandBucket["tier"], string> = {
  mismatch: "bg-red-50 text-red-700 border-red-200",
  tight: "bg-amber-50 text-amber-700 border-amber-200",
  healthy: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const VISIBLE_CARDS_PER_COLUMN = 5;

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function urgencyShortLabel(value: string): string | null {
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
      return null;
  }
}

function LeadCard({
  lead,
  stage,
  onClick,
}: {
  lead: PipelineLead;
  stage: PipelineStageKey;
  onClick: () => void;
}) {
  const showUrgencyBadge =
    stage !== "high_intent" && stage !== "researching" && lead.urgency;
  const advisor = lead.assigned_to;
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-md border border-slate-200 bg-white p-3 text-left text-xs shadow-sm transition hover:border-brand-blue hover:shadow"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="font-semibold text-brand-ink">
            {lead.name || "Anonymous"}
          </div>
          <div className="mt-0.5 text-[11px] text-slate-500">
            {lead.phone || lead.email || "—"}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {advisor ? (
            advisor.photo_url ? (
              <img
                src={advisor.photo_url}
                alt={advisor.name}
                title={`Assigned to ${advisor.name}`}
                className="h-6 w-6 rounded-full border border-slate-200 object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                }}
              />
            ) : (
              <span
                title={`Assigned to ${advisor.name}`}
                className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700"
              >
                {advisor.name
                  .split(" ")
                  .map((p) => p[0])
                  .join("")
                  .slice(0, 2)
                  .toUpperCase()}
              </span>
            )
          ) : null}
          <div className="text-[11px] text-slate-400">
            {timeAgo(lead.created_at)}
          </div>
        </div>
      </div>

      <div className="mt-2 space-y-1">
        {lead.target_monthly_payment ? (
          <div className="text-[11px] text-slate-700">
            {formatCurrency(lead.target_monthly_payment)}/mo
            {lead.down_payment
              ? ` · ${formatCurrency(lead.down_payment)} down`
              : ""}
          </div>
        ) : null}
        {lead.interested_vehicles.length > 0 ? (
          <ul className="space-y-0.5">
            {lead.interested_vehicles.slice(0, 2).map((v) => (
              <li
                key={v.id}
                className="truncate text-[11px] text-slate-600"
                title={`${v.display_name} · ${v.stock_number}`}
              >
                {v.display_name}
              </li>
            ))}
            {lead.interested_vehicles.length > 2 ? (
              <li className="text-[10px] text-slate-400">
                +{lead.interested_vehicles.length - 2} more
              </li>
            ) : null}
          </ul>
        ) : (
          <div className="text-[10px] italic text-slate-400">
            no vehicles flagged
          </div>
        )}
      </div>

      {showUrgencyBadge ? (
        <div className="mt-2 inline-flex rounded-full border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
          {urgencyShortLabel(lead.urgency)}
        </div>
      ) : null}
    </button>
  );
}

function StageColumn({
  stage,
  onCardClick,
}: {
  stage: PipelineStage;
  onCardClick: (leadId: number) => void;
}) {
  const visible = stage.leads.slice(0, VISIBLE_CARDS_PER_COLUMN);
  const remaining = stage.count - visible.length;

  return (
    <div className="flex min-w-0 flex-col gap-2">
      <div
        className={cn(
          "flex items-center justify-between rounded-md border px-3 py-2",
          STAGE_TONE[stage.key],
        )}
      >
        <div className="text-[11px] font-bold uppercase tracking-wide">
          {stage.label}
        </div>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-bold",
            STAGE_BADGE_TONE[stage.key],
          )}
        >
          {stage.count}
        </span>
      </div>

      <div className="flex flex-col gap-2">
        {visible.length === 0 ? (
          <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-3 py-6 text-center text-[11px] text-slate-400">
            No leads in this stage
          </div>
        ) : (
          visible.map((lead) => (
            <LeadCard
              key={lead.id}
              lead={lead}
              stage={stage.key}
              onClick={() => onCardClick(lead.id)}
            />
          ))
        )}
        {remaining > 0 ? (
          <div className="px-2 py-1 text-center text-[11px] text-slate-400">
            + {remaining} more
          </div>
        ) : null}
      </div>
    </div>
  );
}

function DemandPanel({ buckets }: { buckets: DemandBucket[] }) {
  if (buckets.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-200 px-4 py-6 text-center text-sm text-slate-400">
        No open-lead demand to compare against inventory yet.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {buckets.map((b) => (
        <div
          key={b.band_label}
          className={cn(
            "flex flex-col gap-1 rounded-md border px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between",
            TIER_TONE[b.tier],
          )}
        >
          <div className="flex items-center gap-3">
            <span className="font-semibold uppercase tracking-wide">
              {b.band_label}
            </span>
            <span className="text-slate-700">
              leads {b.lead_count} · vehicles {b.vehicle_count}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] text-slate-600">
              ratio {b.ratio.toFixed(2)}×
            </span>
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 text-[11px] font-bold uppercase",
                b.tier === "mismatch"
                  ? "border-red-300 bg-white text-red-700"
                  : b.tier === "tight"
                    ? "border-amber-300 bg-white text-amber-700"
                    : "border-emerald-300 bg-white text-emerald-700",
              )}
            >
              {b.tier === "mismatch"
                ? "Mismatch"
                : b.tier === "tight"
                  ? "Tight"
                  : "Healthy"}
            </span>
          </div>
          {b.suggestion ? (
            <div className="basis-full text-[11px] italic text-slate-600 sm:basis-full">
              {b.suggestion}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export default function SalesPipeline({
  refreshKey,
  onCardClick,
  onPayloadChange,
}: Props) {
  const [data, setData] = useState<PipelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchAdminPipeline()
      .then((res) => {
        if (cancelled) return;
        setData(res);
        onPayloadChange?.(res);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Pipeline load failed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [refreshKey, onPayloadChange]);

  const stages =
    data?.stages ??
    STAGE_DISPLAY_ORDER.map((k) => ({
      key: k,
      label: k,
      count: 0,
      leads: [] as PipelineLead[],
    }));

  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
        <div>
          <h2 className="text-sm font-bold text-brand-ink">Sales pipeline</h2>
          <div className="text-xs text-slate-500">
            {data
              ? `Generated ${timeAgo(data.generated_at)}`
              : loading
                ? "Loading…"
                : "—"}
          </div>
        </div>
        {loading ? (
          <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />
        ) : null}
      </div>

      {error && (
        <div className="border-b border-red-100 bg-red-50 px-5 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 px-5 py-4 md:grid-cols-2 lg:grid-cols-5">
        {stages.map((s) => (
          <StageColumn
            key={s.key}
            stage={s as PipelineStage}
            onCardClick={onCardClick}
          />
        ))}
      </div>

      <div className="border-t border-slate-200 px-5 py-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-brand-ink">
              Demand vs supply
            </h3>
            <div className="text-xs text-slate-500">
              Open leads with a payment target vs available inventory.
              Down-payment assumption: $0.
            </div>
          </div>
          {data?.demand_vs_supply.buckets.some(
            (b) => b.tier === "mismatch",
          ) ? (
            <AlertTriangle className="h-4 w-4 text-red-500" />
          ) : null}
        </div>
        <DemandPanel buckets={data?.demand_vs_supply.buckets ?? []} />
      </div>
    </section>
  );
}
