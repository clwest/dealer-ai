// Manager Phase 2 / Feature C: deterministic next-action cards.
//
// Renders the `recommended_actions[]` array from /admin/pipeline/. The
// payload is computed server-side by services/pipeline.recommended_actions
// — no LLM in the recommendation logic. Each card carries priority,
// title, explanation, action_text, evidence, and an optional CTA that
// dispatches a callback the parent dashboard can route (e.g., open
// HandoffQueue filtered to a band, focus the High Intent column).

import { useState } from "react";
import { ChevronDown, ChevronUp, Megaphone } from "lucide-react";

import type { RecommendedAction, RecommendedActionCTA } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  actions: RecommendedAction[];
  onCTA?: (cta: RecommendedActionCTA, action: RecommendedAction) => void;
  onGenerateAd?: (action: RecommendedAction) => void;
}

const AD_ELIGIBLE_CATEGORIES = new Set<RecommendedAction["category"]>([
  "inventory",
  "marketing",
]);

const PRIORITY_BADGE: Record<RecommendedAction["priority"], string> = {
  high: "bg-red-100 text-red-700 border-red-300",
  medium: "bg-amber-100 text-amber-700 border-amber-300",
  low: "bg-slate-100 text-slate-600 border-slate-300",
};

const CATEGORY_TONE: Record<RecommendedAction["category"], string> = {
  inventory: "bg-blue-50 text-blue-700",
  sales: "bg-emerald-50 text-emerald-700",
  marketing: "bg-purple-50 text-purple-700",
};

const CTA_LABEL: Record<string, string> = {
  view_leads_in_band: "View leads in band",
  view_high_intent_leads: "View high-intent leads",
  view_aging_leads: "View aging leads",
};

function ActionCard({
  action,
  onCTA,
  onGenerateAd,
}: {
  action: RecommendedAction;
  onCTA?: (cta: RecommendedActionCTA, action: RecommendedAction) => void;
  onGenerateAd?: (action: RecommendedAction) => void;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const ctaLabel =
    action.cta && (CTA_LABEL[action.cta.kind] ?? "Open");
  const adEligible = AD_ELIGIBLE_CATEGORIES.has(action.category);

  return (
    <div className="flex flex-col gap-2 rounded-md border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
            PRIORITY_BADGE[action.priority],
          )}
        >
          {action.priority}
        </span>
        <span
          className={cn(
            "rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase",
            CATEGORY_TONE[action.category],
          )}
        >
          {action.category}
        </span>
      </div>

      <div className="text-sm font-semibold text-ford-ink">{action.title}</div>
      <div className="text-xs text-slate-600">{action.explanation}</div>
      <div className="text-xs font-medium text-slate-800">
        {action.action_text}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={() => setShowEvidence((v) => !v)}
          className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-700"
        >
          {showEvidence ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
          {showEvidence ? "Hide details" : "See why"}
        </button>
        <div className="flex flex-wrap items-center gap-1.5">
          {adEligible && onGenerateAd ? (
            <button
              type="button"
              onClick={() => onGenerateAd(action)}
              className="inline-flex items-center gap-1 rounded-md border border-purple-300 bg-purple-50 px-2.5 py-1 text-[11px] font-semibold text-purple-700 hover:bg-purple-100"
              title="Open the ad-copy modal — drafts only, never auto-published"
            >
              <Megaphone className="h-3 w-3" />
              Generate ad
            </button>
          ) : null}
          {action.cta ? (
            <button
              type="button"
              onClick={() =>
                action.cta && onCTA?.(action.cta, action)
              }
              className="rounded-md border border-ford-blue bg-ford-blue px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-ford-blue/90"
            >
              {ctaLabel} →
            </button>
          ) : null}
        </div>
      </div>

      {showEvidence ? (
        <pre className="overflow-x-auto rounded bg-slate-50 p-2 text-[10px] leading-tight text-slate-600">
          {JSON.stringify(action.evidence, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export default function RecommendedActions({
  actions,
  onCTA,
  onGenerateAd,
}: Props) {
  return (
    <section className="card overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-3">
        <div>
          <h2 className="text-sm font-bold text-ford-ink">
            Recommended actions
          </h2>
          <div className="text-xs text-slate-500">
            Top {actions.length} action
            {actions.length === 1 ? "" : "s"} based on current pipeline +
            inventory state.
          </div>
        </div>
      </div>

      {actions.length === 0 ? (
        <div className="px-5 py-6 text-center text-sm text-slate-500">
          All quiet — no recommended actions right now.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 px-5 py-4 md:grid-cols-2 xl:grid-cols-3">
          {actions.map((a) => (
            <ActionCard
              key={a.id}
              action={a}
              onCTA={onCTA}
              onGenerateAd={onGenerateAd}
            />
          ))}
        </div>
      )}
    </section>
  );
}
