// Milestone 4 · Increment 7 — one recon decision row.
//
// Renders the decision tier + notes + decided_by/decided_at
// provenance. When no decision exists yet, exposes the three-tier
// picker (must_do / should_do / wont_do) for write-role users.
//
// Per SESSION_067 reconsideration policy: the row remains editable
// via the picker as long as no linked WorkOrder has left draft
// state. The 409 response from the API in the locked case is
// surfaced to the operator as a distinct error message ("This
// decision is locked because a WorkOrder is already approved").

import { AlertOctagon, CheckCircle2, Circle, XCircle } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/authFetch";
import {
  recordReconDecision,
  RECON_DECISION_TIER_CHOICES,
  type ReconDecision,
  type ReconDashboardFinding,
} from "@/lib/api";

interface TierMeta {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  className: string;
}

const TIER_META: Record<string, TierMeta> = {
  must_do: {
    label: "Must do",
    icon: AlertOctagon,
    className: "border-red-300 bg-red-50 text-red-700",
  },
  should_do: {
    label: "Should do",
    icon: Circle,
    className: "border-amber-300 bg-amber-50 text-amber-700",
  },
  wont_do: {
    label: "Won't do",
    icon: XCircle,
    className: "border-slate-300 bg-slate-100 text-slate-600",
  },
};

function _formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) {
      return "Decision is locked — a linked WorkOrder is already approved. Cancel the WO to reconsider.";
    }
    if (err.status === 404) return "Finding not found. Refresh the page.";
    if (err.status === 400) return "Invalid decision. Please try again.";
    return `Server returned ${err.status}.`;
  }
  return "Decision request failed.";
}

export interface DecisionRowProps {
  stock: string;
  finding: ReconDashboardFinding;
  canEdit: boolean;
  onDecisionRecorded: (finding: ReconDashboardFinding, decision: ReconDecision) => void;
}

export function DecisionRow({
  stock,
  finding,
  canEdit,
  onDecisionRecorded,
}: DecisionRowProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function _recordDecision(tier: string) {
    setSaving(true);
    setError(null);
    try {
      const res = await recordReconDecision(stock, finding.id, { tier });
      onDecisionRecorded(finding, res.decision);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  const decision = finding.decision;

  return (
    <div className="flex items-start gap-3 rounded-md border bg-card p-3">
      <div className="flex-1 space-y-1">
        <div className="text-sm text-foreground">{finding.description}</div>
        <div className="text-xs text-muted-foreground">
          {finding.category} · {finding.severity}
          {finding.estimated_cost != null && (
            <span> · est ${finding.estimated_cost}</span>
          )}
        </div>
      </div>
      <div className="flex flex-col items-end gap-1">
        {decision ? (
          <>
            {(() => {
              const meta = TIER_META[decision.tier] ?? TIER_META.should_do;
              const Icon = meta.icon;
              return (
                <Badge
                  variant="outline"
                  className={cn("gap-1 text-xs font-medium", meta.className)}
                >
                  <Icon className="h-3 w-3" />
                  {meta.label}
                </Badge>
              );
            })()}
            <div className="text-xs text-muted-foreground">
              {decision.decided_by ?? "—"} · {_formatDateTime(decision.decided_at)}
            </div>
            {canEdit && (
              <div className="flex gap-1">
                {RECON_DECISION_TIER_CHOICES.filter(
                  (c) => c.value !== decision.tier,
                ).map((c) => (
                  <Button
                    key={c.value}
                    size="sm"
                    variant="ghost"
                    className="h-6 text-xs"
                    disabled={saving}
                    onClick={() => _recordDecision(c.value)}
                  >
                    → {c.label}
                  </Button>
                ))}
              </div>
            )}
          </>
        ) : canEdit ? (
          <div className="flex flex-wrap gap-1">
            {RECON_DECISION_TIER_CHOICES.map((c) => {
              const meta = TIER_META[c.value] ?? TIER_META.should_do;
              const Icon = meta.icon;
              return (
                <Button
                  key={c.value}
                  size="sm"
                  variant="outline"
                  className={cn("h-7 gap-1 text-xs", meta.className)}
                  disabled={saving}
                  onClick={() => _recordDecision(c.value)}
                >
                  <Icon className="h-3 w-3" />
                  {c.label}
                </Button>
              );
            })}
          </div>
        ) : (
          <Badge variant="outline" className="gap-1 text-xs text-muted-foreground">
            <CheckCircle2 className="h-3 w-3" />
            No decision yet
          </Badge>
        )}
        {error && (
          <div className="text-xs text-destructive">{error}</div>
        )}
      </div>
    </div>
  );
}
