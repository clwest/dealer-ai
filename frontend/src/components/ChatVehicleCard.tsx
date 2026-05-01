// Compact vehicle card used inside chat bubbles. Smaller than the
// full VehicleCard (no buttons, no big image), but reuses the same
// data shape so we have one source of truth.
//
// Two render paths:
//   1. We have the full Vehicle object (from message.matched_vehicles[]
//      keyed by Stock #, OR rendered directly when the LLM didn't write
//      a Stock # but the backend attached vehicles to the message) →
//      show photo, real price, mileage, drivetrain.
//   2. We only have the parsed text (the LLM mentioned a Stock # the
//      backend didn't attach) → show the raw line text + parsed price.
//
// Either path renders inline within the assistant bubble — no buttons,
// no clipboard actions, no flagging. Click-throughs to vehicle detail
// remain on the right-side VehicleCard list, not on these chat cards.

import { Gauge, Tag } from "lucide-react";

import { cn, formatCurrency } from "@/lib/utils";
import type { Vehicle } from "@/lib/api";
import type { ParsedVehicle } from "@/lib/parseAssistantMessage";

interface Props {
  /** Parsed text-derived vehicle. Optional — when omitted, ``matched``
   *  must be supplied (Fix 2: cards rendered directly from
   *  message.matched_vehicles[] when the LLM didn't write a Stock #). */
  parsed?: ParsedVehicle;
  /** Full Vehicle row when the backend attached one with this Stock #. */
  matched?: Vehicle | null;
}

const conditionTone: Record<string, string> = {
  new: "bg-emerald-50 text-emerald-700 border-emerald-200",
  used: "bg-amber-50 text-amber-700 border-amber-200",
  certified: "bg-sky-50 text-sky-700 border-sky-200",
};

// Phase 8s/UX — budget-fit badge. Backend sets budget_fit per matched
// vehicle in budget-mode turns: "fit" / "near_fit" / "over_budget".
// "over_budget" cards are real stretches inside the realistic-stretch
// cap (max($150 floor, 30% × target)) — surface them clearly so the
// customer can tell a stretch from a near-fit at a glance.
function budgetFitBadge(
  fit: Vehicle["budget_fit"],
  delta?: number | null,
): { label: string; tone: string } | null {
  if (fit === "fit") {
    return {
      label: "In budget",
      tone: "bg-emerald-50 text-emerald-700 border-emerald-200",
    };
  }
  if (fit === "near_fit") {
    return {
      label:
        delta != null && delta > 0
          ? `Close · +$${Math.round(delta)}/mo`
          : "Close to target",
      tone: "bg-amber-50 text-amber-800 border-amber-200",
    };
  }
  if (fit === "over_budget") {
    return {
      label:
        delta != null && delta > 0
          ? `Above target · +$${Math.round(delta)}/mo`
          : "Above target",
      tone: "bg-rose-50 text-rose-700 border-rose-200",
    };
  }
  return null;
}

// Phase 8s/UX (lever-flex presentation) — second badge that appears
// alongside the budget_fit badge whenever the backend tagged this
// card as a "flex one lever" option. The kinds map to distinct
// colors so customers can scan three cards and see which is the
// strict match vs which needs which compromise. The explainer text
// (e.g. "Needs 84-mo term", "This is 2WD — flexible-drivetrain
// option") is rendered as a separate caption line below the
// est-payment row.
function leverFlexBadge(
  kind: Vehicle["lever_flex_kind"],
): { label: string; tone: string } | null {
  if (kind === "longer_term") {
    return {
      label: "Longer term",
      tone: "bg-sky-50 text-sky-700 border-sky-200",
    };
  }
  if (kind === "more_down") {
    return {
      label: "More down",
      tone: "bg-sky-50 text-sky-700 border-sky-200",
    };
  }
  if (kind === "drivetrain_flex") {
    return {
      label: "Drivetrain flex",
      tone: "bg-violet-50 text-violet-700 border-violet-200",
    };
  }
  if (kind === "stretch_payment") {
    return {
      label: "Stretch",
      tone: "bg-rose-50 text-rose-700 border-rose-200",
    };
  }
  return null;
}

export default function ChatVehicleCard({ parsed, matched }: Props) {
  // Path 1 — full Vehicle from matched_vehicles.
  if (matched) {
    const fitBadge = budgetFitBadge(matched.budget_fit, matched.payment_delta);
    const flexBadge = leverFlexBadge(matched.lever_flex_kind);
    return (
      <div className="flex gap-3 rounded-md border border-slate-200 bg-white p-2.5 shadow-sm">
        {matched.image_url ? (
          <img
            src={matched.image_url}
            alt=""
            className="h-16 w-20 flex-none rounded-md object-cover"
            loading="lazy"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div className="flex h-16 w-20 flex-none items-center justify-center rounded-md bg-slate-100 text-[10px] text-slate-400">
            no photo
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 truncate text-sm font-semibold text-ford-ink">
              {matched.display_name}
            </div>
            <div className="flex-none text-sm font-bold text-ford-blue">
              {formatCurrency(matched.price)}
            </div>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-500">
            <span>Stock #{matched.stock_number}</span>
            {fitBadge ? (
              <span
                className={cn(
                  "rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  fitBadge.tone,
                )}
              >
                {fitBadge.label}
              </span>
            ) : null}
            {flexBadge ? (
              <span
                className={cn(
                  "rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  flexBadge.tone,
                )}
              >
                {flexBadge.label}
              </span>
            ) : null}
            {matched.condition ? (
              <span
                className={cn(
                  "rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  conditionTone[matched.condition] ??
                    "bg-slate-50 text-slate-700 border-slate-200",
                )}
              >
                {matched.condition === "certified"
                  ? "Certified"
                  : matched.condition}
              </span>
            ) : null}
            {matched.mileage ? (
              <span className="inline-flex items-center gap-0.5">
                <Gauge className="h-3 w-3" />
                {matched.mileage.toLocaleString()} mi
              </span>
            ) : null}
            {matched.drivetrain ? (
              <span className="inline-flex items-center gap-0.5">
                <Tag className="h-3 w-3" />
                {matched.drivetrain}
              </span>
            ) : null}
          </div>
          {matched.estimated_payment != null ? (
            <div className="mt-1 text-[11px] text-slate-600">
              est ~${Math.round(matched.estimated_payment).toLocaleString()}
              /mo (W.A.C.)
            </div>
          ) : null}
          {matched.lever_flex_explainer ? (
            <div className="mt-0.5 text-[11px] italic text-slate-500">
              {matched.lever_flex_explainer}
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  // Path 2 — parsed-only fallback (no full Vehicle row available). We
  // still want a bordered card so the chat reads as a list, not a wall.
  if (!parsed) {
    // Defensive: caller passed neither parsed nor matched. Render
    // nothing rather than crash; the surrounding bubble keeps its
    // raw-text fallback intact.
    return null;
  }
  return (
    <div className="rounded-md border border-slate-200 bg-white p-2.5 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 truncate text-sm text-ford-ink">
          {parsed.display_text}
        </div>
        {parsed.price ? (
          <div className="flex-none text-sm font-bold text-ford-blue">
            {formatCurrency(parsed.price)}
          </div>
        ) : null}
      </div>
      <div className="mt-0.5 text-[11px] text-slate-500">
        Stock #{parsed.stock_number}
        {parsed.year ? ` · ${parsed.year}` : ""}
      </div>
    </div>
  );
}
