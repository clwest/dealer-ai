// Milestone 5 · Increment 6 (SESSION_080) — one-click accept
// buttons for rule-suggested transitions.
//
// Renders suggested_transitions[] from the M5.4 dashboard.
// Suggestions with unmet_prerequisites are visually disabled and
// show the prerequisite text as a hint ("Waiting on M6 photo
// predicate not yet shipped."). Enabled suggestions render as a
// button; click → POST /lifecycle/transition/rule/ with rule_name.
//
// **Read-only for unauthorized roles.** The parent page passes
// `canWrite=false` to hide the buttons entirely. Even if a stale
// UI submits, the M5.2 service rejects with 403 → distinct error UX.

import { AlertTriangle, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StageBadge } from "./StageBadge";
import type { LifecycleSuggestedTransition } from "@/lib/api";

export interface SuggestedTransitionsPanelProps {
  suggestions: LifecycleSuggestedTransition[];
  canWrite: boolean;
  onAccept: (rule_name: string) => void;
  disabled?: boolean;
}

export function SuggestedTransitionsPanel({
  suggestions,
  canWrite,
  onAccept,
  disabled,
}: SuggestedTransitionsPanelProps) {
  if (suggestions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        No system-suggested transitions right now.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {suggestions.map((s) => {
        const hasPrereq = s.unmet_prerequisites.length > 0;
        return (
          <li
            key={s.rule_name}
            className="rounded-md border border-slate-200 bg-slate-50 p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-600" />
              <span className="text-sm font-medium">Advance to</span>
              <StageBadge stage={s.to_stage} />
              <span className="text-xs text-muted-foreground">
                ({s.rule_name})
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-700">{s.evidence}</p>
            {hasPrereq && (
              <div className="mt-2 flex items-start gap-2 rounded-sm border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                <AlertTriangle className="h-3.5 w-3.5 mt-0.5" />
                <div>
                  <p className="font-medium">Waiting on:</p>
                  <ul className="mt-0.5 list-inside list-disc">
                    {s.unmet_prerequisites.map((p) => (
                      <li key={p}>{p}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
            {canWrite && !hasPrereq && (
              <div className="mt-2">
                <Button
                  size="sm"
                  variant="default"
                  disabled={disabled}
                  onClick={() => onAccept(s.rule_name)}
                >
                  Accept suggestion
                </Button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
