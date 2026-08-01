// Milestone 3 · Increment 7 — completion banner.
//
// Signals to the operator that a report is complete + immutable.
// Deliberately not "disabled controls only" — the status shift
// should be visually LOCKED, not merely quiet, so operators are
// never surprised by refused edits (M3.7 spec:
// "Completed reports should look different, not merely become
// disabled").
//
// Draft state does NOT render this banner. Only complete state.

import { Lock, CheckCircle2 } from "lucide-react";

function formatDateTime(iso: string): string {
  const asDate = new Date(iso);
  if (Number.isNaN(asDate.getTime())) return iso;
  return asDate.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function CompletionBanner({
  completedAt,
  authoredBy,
}: {
  completedAt: string;
  authoredBy: string | null;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100">
          <CheckCircle2
            className="h-5 w-5 text-emerald-700"
            aria-hidden="true"
          />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-1.5 text-sm font-semibold text-emerald-900">
            <Lock className="h-3.5 w-3.5" aria-hidden="true" />
            Report complete — locked
          </div>
          <p className="mt-1 text-xs text-emerald-800">
            Completed on {formatDateTime(completedAt)}
            {authoredBy ? ` by ${authoredBy}` : ""}. This report is
            the durable inspection record and cannot be edited.
            To capture additional findings, author a new report.
          </p>
        </div>
      </div>
    </div>
  );
}
