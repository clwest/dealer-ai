// Milestone 5 · Increment 6 (SESSION_080) — vertical timeline of
// every VehicleStageEvent returned by the M5.4 dashboard endpoint.
//
// Reverse chronological (most recent first). Each row shows:
// - from → to stages (via StageBadge)
// - trigger (manual / rule / import / bootstrap)
// - actor (username or "system")
// - entered_at (absolute + relative)
// - notes (if present)
// - rule_name (only for trigger='rule')

import type { LifecycleEvent } from "@/lib/api";
import { StageBadge } from "./StageBadge";

export interface StageTimelineProps {
  events: LifecycleEvent[];
}

function _formatWhen(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

const TRIGGER_LABELS: Record<string, string> = {
  manual: "Manual",
  rule: "Rule",
  import: "Import",
  bootstrap: "Bootstrap",
};

export function StageTimeline({ events }: StageTimelineProps) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        No stage events recorded yet.
      </p>
    );
  }
  return (
    <ol className="space-y-3 border-l-2 border-slate-200 pl-4">
      {events.map((event) => (
        <li key={event.id} className="relative">
          <span className="absolute -left-[1.35rem] top-2 h-2 w-2 rounded-full bg-slate-400" />
          <div className="flex flex-wrap items-center gap-2">
            <StageBadge stage={event.from_stage} />
            <span className="text-xs text-muted-foreground">→</span>
            <StageBadge stage={event.to_stage} />
            <span className="text-xs text-muted-foreground">
              {TRIGGER_LABELS[event.trigger] ?? event.trigger}
              {event.rule_name ? ` · ${event.rule_name}` : ""}
            </span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {_formatWhen(event.entered_at)}
            {" · "}
            {event.by ? event.by.username : "system"}
          </div>
          {event.notes && (
            <p className="mt-1 text-sm text-slate-700">{event.notes}</p>
          )}
        </li>
      ))}
    </ol>
  );
}
