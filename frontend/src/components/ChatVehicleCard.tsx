// Compact vehicle card used inside chat bubbles. Two render paths:
//
//   Path 1 — full Vehicle from message.matched_vehicles[]:
//     Title (Year Make Model Trim), short summary, scan-friendly
//     spec grid (Year / Make / Model / Miles / Drivetrain / Price),
//     features pill row, badges (budget-fit + lever-flex +
//     condition), lever-flex caption, Stock # footer.
//
//   Path 2 — parsed-only (LLM mentioned a Stock # the backend
//   didn't attach). Show the raw line text + parsed price + Stock
//   #. No spec grid (we don't have the data).
//
// Cards are the source of truth for prices, mileage, drivetrain,
// payment, and badges. Assistant prose REFERENCES the cards but
// must not restate their data — that contract is enforced server-
// side by the post-LLM scrub stack (chat_engine.py).

import {
  Calendar,
  Car,
  CircleDollarSign,
  Cog,
  Factory,
  Gauge,
} from "lucide-react";

import { cn, formatCurrency } from "@/lib/utils";
import type { Vehicle } from "@/lib/api";
import type { ParsedVehicle } from "@/lib/parseAssistantMessage";

interface Props {
  /** Parsed text-derived vehicle. Optional — when omitted, ``matched``
   *  must be supplied (cards rendered directly from
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

// Pull the first sentence from a longer description. Falls back to
// the full string if no sentence-end punctuation found. Returns ""
// for empty input so callers can short-circuit.
function firstSentence(text: string): string {
  if (!text) return "";
  const trimmed = text.trim();
  const m = trimmed.match(/^[^.!?\n]+[.!?](?=\s|$)/);
  if (m) return m[0];
  // No sentence terminator — clip to first ~140 chars at a word
  // boundary so we don't dump a paragraph.
  if (trimmed.length <= 140) return trimmed;
  const clip = trimmed.slice(0, 140);
  const lastSpace = clip.lastIndexOf(" ");
  return (lastSpace > 80 ? clip.slice(0, lastSpace) : clip) + "…";
}

// One row of the compact spec list. Pairs an icon + label with a
// scannable value. Used for the new spec grid.
function SpecRow({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-1.5 min-w-0">
      <span className="flex-none text-slate-400" aria-hidden="true">
        {icon}
      </span>
      <span className="flex-none text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <span className="min-w-0 truncate text-xs font-medium text-ford-ink">
        {value}
      </span>
    </div>
  );
}

export default function ChatVehicleCard({ parsed, matched }: Props) {
  // ----------------------------------------------------------------
  // Path 1 — full Vehicle attached to the message. Render the new
  // scan-friendly layout.
  // ----------------------------------------------------------------
  if (matched) {
    const fitBadge = budgetFitBadge(matched.budget_fit, matched.payment_delta);
    const flexBadge = leverFlexBadge(matched.lever_flex_kind);
    const summary = firstSentence(matched.description);
    const features = (matched.features ?? []).slice(0, 4);
    // Build a compact "Model + Trim" cell so the spec grid doesn't
    // have to give Trim its own row.
    const modelTrim = [matched.model, matched.trim]
      .filter(Boolean)
      .join(" ");

    return (
      <article className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        {/* Header: photo (sm) + title + price */}
        <header className="flex gap-3 p-3 sm:p-3.5">
          {matched.image_url ? (
            <img
              src={matched.image_url}
              alt=""
              className="h-16 w-20 flex-none rounded-md object-cover sm:h-20 sm:w-24"
              loading="lazy"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : (
            <div className="flex h-16 w-20 flex-none items-center justify-center rounded-md bg-slate-100 text-[10px] text-slate-400 sm:h-20 sm:w-24">
              no photo
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <h3 className="min-w-0 text-sm font-semibold leading-tight text-ford-ink sm:text-base">
                {matched.display_name}
              </h3>
              <div className="flex-none whitespace-nowrap text-base font-bold text-ford-blue sm:text-lg">
                {formatCurrency(matched.price)}
              </div>
            </div>
            {summary ? (
              <p className="mt-1 line-clamp-2 text-xs text-slate-600 sm:text-sm">
                {summary}
              </p>
            ) : null}
          </div>
        </header>

        {/* Spec grid — 2 cols on mobile, 3 on sm+ */}
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-slate-100 px-3 py-2 sm:grid-cols-3 sm:px-3.5">
          <SpecRow
            icon={<Calendar className="h-3 w-3" />}
            label="Year"
            value={matched.year}
          />
          <SpecRow
            icon={<Factory className="h-3 w-3" />}
            label="Make"
            value={matched.make}
          />
          <SpecRow
            icon={<Car className="h-3 w-3" />}
            label="Model"
            value={modelTrim || matched.model}
          />
          {matched.mileage ? (
            <SpecRow
              icon={<Gauge className="h-3 w-3" />}
              label="Miles"
              value={`${matched.mileage.toLocaleString()} mi`}
            />
          ) : null}
          {matched.drivetrain ? (
            <SpecRow
              icon={<Cog className="h-3 w-3" />}
              label="Drivetrain"
              value={matched.drivetrain}
            />
          ) : null}
          <SpecRow
            icon={<CircleDollarSign className="h-3 w-3" />}
            label="Price"
            value={formatCurrency(matched.price)}
          />
        </div>

        {/* Optional features pill row */}
        {features.length > 0 ? (
          <div className="flex flex-wrap gap-1 border-t border-slate-100 px-3 py-2 sm:px-3.5">
            {features.map((f) => (
              <span
                key={f}
                className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-600"
              >
                {f}
              </span>
            ))}
          </div>
        ) : null}

        {/* Badges + estimated payment row */}
        {(fitBadge ||
          flexBadge ||
          matched.condition ||
          matched.estimated_payment != null) && (
          <div className="flex flex-wrap items-center gap-1.5 border-t border-slate-100 px-3 py-2 sm:px-3.5">
            {fitBadge ? (
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  fitBadge.tone,
                )}
              >
                {fitBadge.label}
              </span>
            ) : null}
            {flexBadge ? (
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  flexBadge.tone,
                )}
              >
                {flexBadge.label}
              </span>
            ) : null}
            {matched.condition ? (
              <span
                className={cn(
                  "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  conditionTone[matched.condition] ??
                    "bg-slate-50 text-slate-700 border-slate-200",
                )}
              >
                {matched.condition === "certified"
                  ? "Certified"
                  : matched.condition}
              </span>
            ) : null}
            {matched.estimated_payment != null ? (
              <span className="ml-auto whitespace-nowrap text-[11px] text-slate-600">
                est ~$
                {Math.round(matched.estimated_payment).toLocaleString()}
                /mo (W.A.C.)
              </span>
            ) : null}
          </div>
        )}

        {/* Lever-flex explainer — italic clarifier when present */}
        {matched.lever_flex_explainer ? (
          <p className="border-t border-slate-100 bg-slate-50 px-3 py-1.5 text-[11px] italic text-slate-500 sm:px-3.5">
            {matched.lever_flex_explainer}
          </p>
        ) : null}

        {/* Footer: stock # de-emphasized */}
        <footer className="border-t border-slate-100 px-3 py-1.5 text-[10px] text-slate-400 sm:px-3.5">
          Stock #{matched.stock_number}
        </footer>
      </article>
    );
  }

  // ----------------------------------------------------------------
  // Path 2 — parsed-only fallback. The LLM mentioned a Stock # we
  // don't have data for; render a minimal card so the chat reads as
  // a list, not a wall of text.
  // ----------------------------------------------------------------
  if (!parsed) return null;

  return (
    <article className="rounded-md border border-slate-200 bg-white p-2.5 shadow-sm">
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
      <div className="mt-0.5 text-[10px] text-slate-400">
        Stock #{parsed.stock_number}
        {parsed.year ? ` · ${parsed.year}` : ""}
      </div>
    </article>
  );
}
