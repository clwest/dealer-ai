// SESSION_227 — recon-one-card. One job per finding.
//
// Composes the finding row + its DecisionRow + (once a WorkOrder
// exists) the WorkOrderCard. When no live WO exists AND the decision
// is "Must do", the card offers a one-click "Create work order"
// button that maps to the `admin-work-order-from-finding` verb.
//
// The mechanics underneath — ConditionFinding / WorkOrder /
// WorkOrderFinding — are unchanged. This card is the seam Chris
// asked for: the operator sees a job, not a decision separated from
// a form separated from a card.

import { useState } from "react";
import { Loader2, PlusCircle } from "lucide-react";

import { DecisionRow } from "@/components/recon/DecisionRow";
import { WorkOrderCard } from "@/components/recon/WorkOrderCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/lib/authFetch";
import {
  createWorkOrderFromFinding,
  type ReconDashboardFinding,
  type ReconDecision,
  type VendorCommunication,
  type WorkOrder,
} from "@/lib/api";

function _humanizeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "This action conflicts with the current state. Refresh and try again.";
    if (err.status === 400) return "Invalid input.";
    if (err.status === 404) return "Not found. Refresh the page.";
    return `Server returned ${err.status}.`;
  }
  return "Request failed.";
}

export interface JobCardProps {
  stock: string;
  finding: ReconDashboardFinding;
  workOrder: WorkOrder | null;
  reportFindings: ReconDashboardFinding[];
  activeReportId: number | null;
  canEdit: boolean;
  onDecisionRecorded: (
    finding: ReconDashboardFinding,
    decision: ReconDecision,
  ) => void;
  onWorkOrderUpdated: (wo: WorkOrder) => void;
  onWorkOrderCreated: (wo: WorkOrder) => void;
  onCommDrafted: (comm: VendorCommunication) => void;
  onFindingDiscovered: () => void;
}

export function JobCard({
  stock,
  finding,
  workOrder,
  reportFindings,
  activeReportId,
  canEdit,
  onDecisionRecorded,
  onWorkOrderUpdated,
  onWorkOrderCreated,
  onCommDrafted,
  onFindingDiscovered,
}: JobCardProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const decisionTier = finding.decision?.tier;
  const canCreateFromMustDo =
    canEdit && !workOrder && decisionTier === "must_do";
  const decisionBlockedReason = !decisionTier
    ? "Record a decision before authorizing."
    : decisionTier !== "must_do"
      ? `Decision is "${decisionTier}" — mark this job Must do before authorizing.`
      : null;

  async function _create() {
    setSaving(true);
    setError(null);
    try {
      const res = await createWorkOrderFromFinding(stock, finding.id);
      onWorkOrderCreated(res.work_order);
    } catch (err) {
      setError(_humanizeError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1 pb-2">
        <CardTitle className="text-base">
          {finding.description}
          {finding.discovered_during_work && (
            <span className="ml-2 rounded-full border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs font-normal text-blue-800">
              Found on the lift
            </span>
          )}
        </CardTitle>
        <div className="text-xs text-muted-foreground">
          Finding #{finding.id} · {finding.category} · {finding.severity}
          {finding.estimated_cost != null && (
            <span> · inspector est ${finding.estimated_cost}</span>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <DecisionRow
          stock={stock}
          finding={finding}
          canEdit={canEdit}
          onDecisionRecorded={onDecisionRecorded}
        />

        {workOrder ? (
          <div className="pt-2">
            <WorkOrderCard
              wo={workOrder}
              stock={stock}
              canEdit={canEdit}
              authorizeBlockedReason={decisionBlockedReason}
              reportFindings={reportFindings}
              activeReportId={activeReportId}
              onWorkOrderUpdated={onWorkOrderUpdated}
              onCommDrafted={onCommDrafted}
              onFindingDiscovered={onFindingDiscovered}
            />
          </div>
        ) : canCreateFromMustDo ? (
          <div className="flex items-center justify-between rounded border bg-emerald-50 p-3 text-sm text-emerald-900">
            <div>Ready to open a work order for this job.</div>
            <Button size="sm" onClick={_create} disabled={saving} className="gap-1">
              {saving ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <PlusCircle className="h-3 w-3" />
              )}
              Create work order
            </Button>
          </div>
        ) : (
          <div className="rounded border bg-muted/30 p-3 text-xs text-muted-foreground">
            {decisionTier === "should_do" &&
              "Should-do jobs don't open a work order automatically. Change to Must do when you're ready to spend."}
            {decisionTier === "wont_do" &&
              "Won't-do — no work order needed."}
            {!decisionTier &&
              "Record a decision above to move this job forward."}
          </div>
        )}

        {error && <div className="text-xs text-destructive">{error}</div>}
      </CardContent>
    </Card>
  );
}
